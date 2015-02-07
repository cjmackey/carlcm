
import errno
import filecmp
import grp
import hashlib
import json
import os as real_os
import pwd
import re
import shutil
from stat import S_IMODE, S_ISDIR
import subprocess
import urllib

import fake_filesystem
from mock import Mock

class Context(object):
    '''
    Most methods return True if something was modified, and False otherwise
    '''
    def __init__(self, _os=None, _open=None):
        self.os = _os or real_os
        self.open = _open or open
        self.triggers = set()
        self.package_cache = None
        self.modules = []

    def _before(self, triggered_by):
        '''
        If this returns True, we should skip the run
        '''
        if triggered_by is None:
            return False
        if type(triggered_by) == str:
            triggered_by = [triggered_by]
        return len(set(triggered_by).intersection(self.triggers)) == 0

    def _after(self, is_new, triggers):
        bad_triggers_message = Exception('triggers must be None, a string, or a list of strings')
        if triggers is None:
            return is_new
        if type(triggers) == str:
            triggers = [triggers]
        if hasattr(triggers, '__iter__'):
            for trigger in triggers:
                if type(trigger) != str:
                    raise bad_triggers_message
        else:
            raise bad_triggers_message
        if is_new:
            self.triggers = self.triggers.union(set(triggers))
        return is_new

    def shell(self, cmd, **kwargs):
        return self.cmd(cmd, shell=True, **kwargs)

    def _cmd_quiet(self, *args, **kwargs):
        return subprocess.check_output(*args, **kwargs)

    def _cmd(self, *args, **kwargs):
        return subprocess.check_call(*args, **kwargs)

    def _cmd_in(self, cmd, stdin, **kwargs):
        proc=subprocess.Popen(cmd,
                              stdin=subprocess.PIPE,
                              stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT,
                              **kwargs)
        proc.stdin.write(str(stdin))
        proc.stdin.flush()
        stdout, stderr = proc.communicate()
        return stdout

    def current_packages(self):
        if self.package_cache is not None:
            return self.package_cache
        s = self._cmd_quiet(['dpkg', '-l'])
        d = {}
        for line in [l.strip().split() for l in s.split("\n") if l.strip()[:2] == 'ii']:
            if len(line) >= 3:
                d[line[1]] = line[2]
        self.package_cache = d
        return d

    def package_manager_update(self, triggers=None, triggered_by=None):
        if self._before(triggered_by): return False
        self._cmd_quiet(['apt-get', 'update'])
        return self._after(True, triggers)

    def package(self, package, **kwargs):
        return self.packages([package], **kwargs)

    def packages(self, packages, triggers=None, triggered_by=None):
        if self._before(triggered_by): return False
        new_packages = [p for p in packages if p not in self.current_packages()]
        if len(new_packages) > 0:
            old_env = self.os.getenv('DEBIAN_FRONTEND', None)
            self.os.environ['DEBIAN_FRONTEND'] = 'noninteractive'
            self._cmd_quiet(['apt-get', 'install', '-y'] + sorted(new_packages))
            if old_env:
                self.os.environ['DEBIAN_FRONTEND'] = old_env
            else:
                del self.os.environ['DEBIAN_FRONTEND']
            self.package_cache = None
        return self._after(len(new_packages) > 0, triggers)

    def cmd(self, cmd, quiet=False, triggers=None, triggered_by=None, **kwargs):
        if self._before(triggered_by): return False
        if quiet:
            self._cmd_quiet(cmd, **kwargs)
        else:
            self._cmd(cmd, **kwargs)
        return self._after(True, triggers)

    def _mkdir(self, d):
        """
        Based on http://code.activestate.com/recipes/82465-a-friendly-mkdir/
        """
        d = self.os.path.realpath(d)
        id = self.os.path.isdir(d)
        if id:
            return False
        elif self.os.path.isfile(d):
            raise OSError("file exists: " % d)
        else:
            h, t = self.os.path.split(d)
            if h: self._mkdir(h)
            if t: self.os.mkdir(d)
        return True

    def _user_name_to_uid(self, user):
        try:
            return pwd.getpwnam(user).pw_uid
        except KeyError:
            return None
    def _group_name_to_gid(self, group):
        try:
            return grp.getgrnam(group).gr_gid
        except KeyError:
            return None
    def _user_home(self, user):
        try:
            return pwd.getpwnam(user).pw_dir
        except KeyError:
            return None

    def _apply_permissions(self, path, owner, group, mode):
        stat = self.os.stat(path)
        matched = True
        if mode is not None:
            if type(mode) == str:
                mode = int(mode, 8)
            self.os.chmod(path, mode)
            if S_IMODE(stat.st_mode) != mode:
                matched = False
        if owner is not None or group is not None:
            owner = owner or -1
            group = group or -1
            if type(owner) == str:
                owner = self._user_name_to_uid(owner)
                if owner is None:
                    raise ValueError('no such user!')
            if type(group) == str:
                group = self._group_name_to_gid(group)
                if group is None:
                    raise ValueError('no such group!')
            self.os.chown(path, owner, group)
            if owner >= 0 and stat.st_uid != owner or group >= 0 and stat.st_gid != group:
                matched = False
        return not matched

    def mkdir(self, path, owner=None, group=None, mode=None,
              triggers=None, triggered_by=None):
        if self._before(triggered_by): return False
        path = self.os.path.realpath(path)
        is_new = self._mkdir(path)
        perm_change = self._apply_permissions(path, owner, group, mode)
        return self._after(is_new or perm_change, triggers)

    def _touch(self, path):
        self._mkdir(self.os.path.dirname(path))
        with self.open(path, 'a') as f:
            f.write('')

    def _read_file(self, path):
        return self.open(path, 'rb').read()

    def _write_file(self, path, data):
        with self.open(path, 'wb') as f:
            f.truncate()
            f.write(data)

    def _urlretrieve(self, url, path):
        urllib.urlretrieve(url, path)

    def _hash_file(self, path, hash_algo):
        m = hashlib.new(hash_algo)
        with self.open(path, 'rb') as f:
            while True:
                s = f.read(4096)
                m.update(s)
                if len(s) <= 0:
                    break
        return m.hexdigest()

    def download(self, path, url,
                 owner=None, group=None, mode=None,
                 triggers=None, triggered_by=None, **kwargs):
        # NOTE: this downloads in-place currently, which is not great
        # for sanctity of the file.

        # Also... right now, if you don't pass a hash, it will only
        # download once, and never check again.  Is that desired?
        # Should it always download and compare the file?
        if self._before(triggered_by): return False
        file_new = not self.os.path.isfile(path)
        if file_new:
            self._touch(path)
        perm_change = self._apply_permissions(path, owner, group, mode)
        if not file_new:
            for a, k in [(a, a+s) for a in hashlib.algorithms for s in ['','sum']]:
                if k in kwargs:
                    file_new = file_new or self._hash_file(path, a) != kwargs[k]

        if file_new:
            self._urlretrieve(url, path)
            for a, k in [(a, a+s) for a in hashlib.algorithms for s in ['','sum']]:
                if k in kwargs:
                    assert self._hash_file(path, a) == kwargs[k]
        return self._after(perm_change or file_new, triggers)

    def file(self, dest_path, src_path=None, src_data=None,
             owner=None, group=None, mode=None,
             triggers=None, triggered_by=None):
        # NOTE: this writes the file in-place currently, which is not
        # great for the stability of reads to that file.
        assert bool(src_path is not None) != bool(src_data is not None)
        if self._before(triggered_by): return False
        if dest_path[-1:] == '/' and src_path:
            _, tail = self.os.path.split(src_path)
            dest_path += tail
        dest_path = self.os.path.realpath(dest_path)
        file_existed = self.os.path.isfile(dest_path)
        if not file_existed:
            self._touch(dest_path)
        perm_change = self._apply_permissions(dest_path, owner, group, mode)
        old_contents = self._read_file(dest_path)
        if type(src_data) is dict:
            src_data = json.dumps(src_data, sort_keys=True,
                                  indent=4, separators=(',', ': ')) + '\n'
        if src_path is not None:
            src_data = self._read_file(src_path)
        contents_match = src_data == old_contents
        if not contents_match:
            self._write_file(dest_path, src_data)
        return self._after(perm_change or not (file_existed and contents_match), triggers)

    def template(self, dest_path, src_path=None, src_data=None,
                 template_parameters=None, engine='jinja2',
                 triggers=None, triggered_by=None, **kwargs):
        if engine == 'jinja2':
            return self.jinja2(dest_path, src_path, src_data, template_parameters,
                               triggers, triggered_by, **kwargs)
        raise ValueError('no matching template engine!')

    def jinja2(self, dest_path, src_path=None, src_data=None,
               owner=None, group=None, mode=None,
               template_parameters=None, triggers=None, triggered_by=None, **kwargs):
        import jinja2
        if self._before(triggered_by): return False
        template_parameters = template_parameters or {}
        for k, v in kwargs.items():
            template_parameters[k] = template_parameters.get(k, v)
        if src_path is not None and src_data is None:
            src_data = self._read_file(src_path)
        # todo: also pass perms
        return self.file(dest_path = dest_path,
                         owner=owner, group=group, mode=mode,
                         src_data = jinja2.Template(src_data).render(template_parameters),
                         triggers = triggers)

    def _groupadd_cmd(self, groupname, gid=None):
        cmd = ['groupadd']
        if gid is not None:
            cmd += ['-g', str(gid)]
        cmd += [groupname]
        return cmd

    def _groupadd(self, groupname, gid=None):
        self._cmd_quiet(self._groupadd_cmd(groupname, gid))

    def group(self, groupname, gid=None, triggers=None, triggered_by=None):
        if self._before(triggered_by): return False
        group_existed = bool(self._group_name_to_gid(groupname))
        if not group_existed:
            self._groupadd(groupname, gid)
        return self._after(not group_existed, triggers)

    def _useradd_cmd(self, username, home=True, uid=None, gid=None,
                     groups=None, shell=None, comment=None):
        cmd = ['useradd']
        if home is not True:
            if home is False:
                cmd += ['-M']
            elif type(home) is str:
                cmd += ['-d', home]
            else:
                raise ValueError('errrrrr')
        if uid is not None:
            cmd += ['-u', str(uid)]
        if gid is not None:
            cmd += ['-g', str(gid)]
        if shell is not None:
            cmd += ['-s', str(shell)]
        if comment is not None:
            cmd += ['-c', str(comment)]
        cmd += ['-U', username]
        return cmd

    def _useradd(self, username, home=True, uid=None, gid=None,
                 groups=None, shell=None, comment=None):
        self._cmd_quiet(self._useradd_cmd(username, home, uid, gid,
                                          groups, shell, comment))

    def _user_groups(self, username):
        gs = self._cmd_quiet(['groups', username])
        return sorted(gs.split(':')[-1].strip().split())

    def _add_user_to_group(self, username, groupname):
        self._cmd_quiet(['gpasswd', '-a', username, groupname])
    def _remove_user_from_group(self, username, groupname):
        self._cmd_quiet(['gpasswd', '-d', username, groupname])

    def authorized_keys(self, user, authorized_keys, triggers=None, triggered_by=None):
        if self._before(triggered_by): return False
        if type(authorized_keys) is list:
            authorized_keys = '\n'.join(authorized_keys)
        home = self._user_home(user)
        if home is None:
            raise AssertionError(user + ' has no home, but authorized_keys was specified!')
        ssh_dir = self.os.path.join(home, '.ssh')
        self.mkdir(ssh_dir, owner=user, group=user, mode=0700)
        filename = self.os.path.join(ssh_dir, 'authorized_keys')
        changed = self.file(filename, src_data = authorized_keys,
                            owner=user, group=user, mode=0600)
        return self._after(changed, triggers)

    def user(self, username, password=None, encrypted_password=None,
             authorized_keys=None,
             home=True, home_mode='755', uid=None, gid=None, groups=None, shell=None,
             comment=None, random_password=False, triggers=None, triggered_by=None):
        '''
        http://serverfault.com/questions/367559/
        echo "P4sSw0rD" | openssl passwd -1 -stdin
        '''
        if self._before(triggered_by): return False
        user_existed = bool(self._user_name_to_uid(username))
        if not user_existed:
            self._useradd(username, home, uid, gid,
                          groups, shell, comment)
        home_changed = False
        home_perm_changed = False
        if home is not False:
            _home = self._user_home(username)
            home_changed = self._mkdir(_home)
            home_perm_changed = self._apply_permissions(_home, username, username, home_mode)

        changing_groups = False
        if groups:
            gs = self._user_groups(username)
            existing_groups = set(self._user_groups(username)) - set([username])
            changing_groups = existing_groups != set(groups)
            for group in sorted(list(set(groups) - set(existing_groups))):
                self._add_user_to_group(username, group)
            for group in sorted(list(set(existing_groups) - set(groups))):
                self._remove_user_from_group(username, group)

        # TODO: need to be able to check if the password was the same or not
        if random_password:
            password = real_os.urandom(20).encode('hex')
        if password is not None:
            self._cmd_in(['chpasswd'], username + ':' + password + '\n')
        if encrypted_password is not None:
            self._cmd_in(['chpasswd', '-e'], username + ':' + encrypted_password + '\n')

        changed_auth_keys = False
        if authorized_keys is not None:
            changed_auth_keys = self.authorized_keys(username, authorized_keys)
        return self._after(not user_existed or home_changed or home_perm_changed or changing_groups or changed_auth_keys, triggers)

    def line_in_file(self, path, line=None, regexp=None, state='present',
                     enforce_trailing_newline=True,
                     triggers=None, triggered_by=None):
        if self._before(triggered_by): return False
        if not self.os.path.isfile(path):
            raise ValueError('path %s is not a file!' % path)
        assert state in ['present', 'absent']
        if state == 'present': assert line is not None
        if state == 'absent': assert bool(regexp is not None) != bool(line is not None)
        if type(regexp) is str:
            regexp = re.compile(regexp)
        data = self._read_file(path)
        lines = data.split('\n')
        line_ix = None
        if regexp is not None:
            for ix in xrange(len(lines)):
                if regexp.search(lines[ix]):
                    line_ix = ix
        if line_ix is None:
            for ix in xrange(len(lines)):
                if lines[ix] == line:
                    line_ix = ix
        if state == 'present':
            assert line is not None
            if line_ix is None:
                line_ix = len(lines)
                if len(lines) > 0 and lines[-1] == '':
                    line_ix -= 1
            assert line_ix <= len(lines)
            if line_ix == len(lines):
                lines += ['']
            lines[line_ix] = line
        if state == 'absent' and line_ix is not None:
            lines = lines[:line_ix] + lines[line_ix+1:]
        data2 = '\n'.join(lines)
        if enforce_trailing_newline and (len(data2) == 0 or data2[-1] != '\n'):
            data2 += '\n'
        return self.file(path, src_data=data2)

    def add_modules(self, *args):
        self.modules += args
        return self

    def run_modules(self):
        packages = []
        for module in self.modules:
            packages += module.packages()
        # TODO: change the package format to allow inclusion of versions... somehow
        self.packages(packages)
        for module in self.modules:
            module.main(self)
        return self

# TODO: rsync, git repo, apt sources, apt keys, ssh authorized_keys, cron

class MockContext(Context):
    def __init__(self, fs=None, users=None, groups=None):
        self.fs = fs or fake_filesystem.FakeFilesystem()
        self.users = users or [{'name':'root', 'id':0,
                                'groups':['root'], 'home':'/root'}]
        self.groups = groups or [{'name':'root', 'id':0}]
        self.mock_urls = {}
        self._cmd = Mock()
        self._cmd_quiet = Mock()
        Context.__init__(self,
                         _os=fake_filesystem.FakeOsModule(self.fs),
                         _open=fake_filesystem.FakeFileOpen(self.fs))
    def _cmd(self):
        assert False
    def _cmd_quiet(self):
        assert False
    def _cmd_in(self):
        assert False
    def _user_home(self, user):
        return [x for x in self.users if x['name'] == user][0].get('home')
    def _user_groups(self, user):
        return [x for x in self.users if x['name'] == user][0].get('groups', [])
    def _user_name_to_uid(self, user):
        try: return [x for x in self.users if x['name'] == user][0]['id']
        except IndexError: return None
    def _group_name_to_gid(self, group):
        try: return [x for x in self.groups if x['name'] == group][0]['id']
        except IndexError: return None
    def _next_id(self, arr):
        i = 1000
        for item in arr:
            i = max(item['id'] + 1, i)
        return i

    def _groupadd(self, groupname, gid=None):
        gid = gid or self._next_id(self.groups)
        if len([x for x in self.groups if x['id'] == gid]) > 0:
            raise Exception('gid already taken!')
        self.groups += [{'name':groupname, 'id': gid}]

    def _useradd(self, username, home=True, uid=None, gid=None,
                 groups=None, shell=None, comment=None):
        uid = uid or self._next_id(self.groups)
        if len([x for x in self.users if x['id'] == uid]) > 0:
            raise Exception('uid already taken!')
        user = {'name':username, 'id':uid, 'comment':comment, 'shell':shell,
                'home':'/home/'+username, 'groups':[username]}
        if home is not True:
            if home is False:
                user['home'] = None
            elif type(home) is str:
                user['home'] = home
            else:
                raise ValueError('errrrrr')
        self.users += [user]
        self._groupadd(username, gid)

    def _add_user_to_group(self, username, groupname):
        user = [x for x in self.users if x['name'] == username][0]
        user['groups'] = sorted(list(set(user['groups'] + [groupname])))

    def _remove_user_from_group(self, username, groupname):
        user = [x for x in self.users if x['name'] == username][0]
        user['groups'] = sorted(list(set(user['groups']) - set([groupname])))

    def _urlretrieve(self, url, path):
        self._write_file(path, self.mock_urls[url])
