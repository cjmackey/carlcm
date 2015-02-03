
import errno
import filecmp
import grp
import json
import os
import pwd
import shutil
from stat import S_IMODE
import subprocess
import urllib

class Context(object):
    '''
    Most methods return True if something was modified, and False otherwise
    '''
    def __init__(self):
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
            old_env = os.getenv('DEBIAN_FRONTEND', None)
            os.environ['DEBIAN_FRONTEND'] = 'noninteractive'
            self._cmd_quiet(['apt-get', 'install', '-y'] + sorted(new_packages))
            if old_env:
                os.environ['DEBIAN_FRONTEND'] = old_env
            else:
                del os.environ['DEBIAN_FRONTEND']
            self.package_cache = None
        return self._after(len(new_packages) > 0, triggers)

    def cmd(self, cmd, quiet=False, triggers=None, triggered_by=None, **kwargs):
        if self._before(triggered_by): return False
        if quiet:
            self._cmd_quiet(cmd, **kwargs)
        else:
            self._cmd(cmd, **kwargs)
        return self._after(True, triggers)

    def _isfile(self, f):
        return os.path.isfile(f)

    def _mkdir_1(self, d):
        return os.mkdir(d)

    def _mkdir(self, d):
        """
        Based on http://code.activestate.com/recipes/82465-a-friendly-mkdir/
        """
        d = os.path.realpath(d)
        id = self._isdir(d)
        if id:
            return False
        elif self._isfile(d):
            raise OSError("file exists: " % d)
        else:
            h, t = os.path.split(d)
            if h: self._mkdir(h)
            if t: self._mkdir_1(d)
        return True

    def _chmod(self, path, mode):
        os.chmod(path, mode)
    def _chown(self, path, owner, group):
        os.chown(path, owner, group)
    def _stat(self, path):
        return os.stat(path)
    def _user_name_to_uid(self, user):
        uid = None
        try:
            uid = pwd.getpwnam(user).pw_uid
        except KeyError: pass
        if uid is None and user == 'root':
            uid = 0
        return uid
    def _group_name_to_gid(self, group):
        try:
            return grp.getgrnam(group).gr_gid
        except KeyError:
            if group == 'root':
                return 0
            return None
    def _user_home(self, user):
        return pwd.getpwnam(user).pw_dir

    def _apply_permissions(self, path, owner, group, mode):
        stat = self._stat(path)
        matched = True
        if mode is not None:
            if type(mode) == str:
                mode = int(mode, 8)
            self._chmod(path, mode)
            if S_IMODE(stat.st_mode) != mode:
                matched = False
        if owner is not None or group is not None:
            owner = owner or -1
            group = group or -1
            if type(owner) == str:
                owner = self._user_name_to_uid(owner)
                if owner is None:
                    raise Exception('no such user!')
            if type(group) == str:
                group = self._group_name_to_gid(group)
                if group is None:
                    raise Exception('no such group!')
            self._chown(path, owner, group)
            if owner >= 0 and stat.st_uid != owner or group >= 0 and stat.st_gid != group:
                matched = False
        return not matched

    def _isdir(self, path):
        return os.path.isdir(path)

    def mkdir(self, path, owner=None, group=None, mode=None,
              triggers=None, triggered_by=None):
        if self._before(triggered_by): return False
        path = os.path.realpath(path)
        is_new = self._mkdir(path)
        perm_change = self._apply_permissions(path, owner, group, mode)
        return self._after(is_new or perm_change, triggers)

    def _touch(self, path):
        self._mkdir(os.path.dirname(path))
        with open(path, 'a'):
            os.utime(path, None)

    def _read_file(self, path):
        return open(path, 'rb').read()

    def _write_file(self, path, data):
        with open(path, 'wb') as f:
            f.truncate()
            f.write(data)

    def download(self, path, url,
                 sha1sum=None, sha256sum=None,
                 owner=None, group=None, mode=None,
                 triggers=None, triggered_by=None):
        # NOTE: this downloads in-place currently, which is not great
        # for sanctity of the file.

        # Also... right now, if you don't pass sha1sum, it will only
        # download once, and never check again.  Is that desired?
        # Should it always download and compare the file?
        if self._before(triggered_by): return False
        file_new = not self._isfile(path)
        if file_new:
            self._touch(path)
        perm_change = self._apply_permissions(path, owner, group, mode)
        if not file_new:
            if sha1sum is not None:
                file_new = self._cmd_quiet(['sha1sum', path]).strip().split()[0] != sha1sum
            if sha256sum is not None:
                file_new = self._cmd_quiet(['sha256sum', path]).strip().split()[0] != sha256sum
        if file_new:
            urllib.urlretrieve(url, path)
            if sha1sum is not None:
                assert self._cmd_quiet(['sha1sum', path]).strip().split()[0] == sha1sum
            if sha256sum is not None:
                assert self._cmd_quiet(['sha256sum', path]).strip().split()[0] == sha256sum
        return self._after(perm_change or file_new, triggers)

    def file(self, dest_path, src_path=None, src_data=None,
             owner=None, group=None, mode=None,
             triggers=None, triggered_by=None):
        # NOTE: this writes the file in-place currently, which is not
        # great for the stability of reads to that file.
        assert bool(src_path) != bool(src_data)
        if self._before(triggered_by): return False
        if dest_path[-1:] == '/' and src_path:
            _, tail = os.path.split(src_path)
            dest_path += tail
        dest_path = os.path.realpath(dest_path)
        file_existed = self._isfile(dest_path)
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
                         src_data = jinja2.Template(src_data).render(template_parameters),
                         triggers = triggers)

    def group(self, groupname, gid=None, triggers=None, triggered_by=None):
        if self._before(triggered_by): return False
        group_existed = bool(self._group_name_to_gid(groupname))
        if not group_existed:
            cmd = ['groupadd']
            if gid is not None:
                cmd += ['-g', str(gid)]
            cmd += [groupname]
            self._cmd_quiet(cmd)
        return self._after(not group_existed, triggers)

    def user(self, username, password=None, encrypted_password=None,
             home=True, home_mode='755', uid=None, gid=None, groups=None, shell=None,
             comment=None, random_password=False, triggers=None, triggered_by=None):
        '''
        http://serverfault.com/questions/367559/
        echo "P4sSw0rD" | openssl passwd -1 -stdin
        '''
        if self._before(triggered_by): return False
        user_existed = bool(self._user_name_to_uid(username))
        if not user_existed:
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
            self._cmd_quiet(cmd)
        home_changed = False
        home_perm_changed = False
        if home is not False:
            _home = self._user_home(username)
            home_changed = self._mkdir(_home)
            home_perm_changed = self._apply_permissions(_home, username, username, home_mode)

        changing_groups = False
        if groups:
            gs = self._cmd_quiet(['groups', username])
            existing_groups = set(gs.split(':')[-1].strip().split()) - set([username])
            changing_groups = set(existing_groups) != set(groups)
            for group in sorted(list(set(groups) - set(existing_groups))):
                self._cmd_quiet(['gpasswd', '-a', username, group])
            for group in sorted(list(set(existing_groups) - set(groups))):
                self._cmd_quiet(['gpasswd', '-d', username, group])

        # TODO: need to be able to check if the password was the same or not
        if random_password:
            password = os.urandom(20).encode('hex')
        if password is not None:
            self._cmd_in(['chpasswd'], username + ':' + password + '\n')
        if encrypted_password is not None:
            self._cmd_in(['chpasswd', '-e'], username + ':' + encrypted_password + '\n')

        return self._after(not user_existed or home_changed or home_perm_changed or changing_groups, triggers)

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

# TODO: rsync, line in file, git repo, apt sources, apt keys
