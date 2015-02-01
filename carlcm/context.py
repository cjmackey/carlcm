
import errno
import filecmp
import grp
import os
import pwd
import shutil
import subprocess

class Context(object):
    '''
    Most methods return True if something was modified, and False otherwise
    '''
    def __init__(self):
        self.triggers = set()

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
        bad_triggers_message = 'triggers must be None, a string, or a list of strings'
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
        print 'isdir', d, id
        if id:
            return False
        elif self._isfile(d):
            raise OSError("file exists: " % d)
        else:
            h, t = os.path.split(d)
            print 'split', h, t
            if h: self._mkdir(h)
            if t: self._mkdir_1(d)
        return True

    def _apply_permissions(self, path, owner, group, mode):
        if mode is not None:
            if type(mode) == str:
                mode = int(mode, 8)
            os.chmod(path, mode)
        if owner is not None or group is not None:
            owner = owner or -1
            group = group or -1
            if type(owner) == str: owner = pwd.getpwnam(owner).pw_uid
            if type(group) == str: group = grp.getgrnam(group).gr_gid
            os.chown(path, owner, group)
        # TODO: make it so we track whether we changed things or not
        return

    def _isdir(self, path):
        return os.path.isdir(path)

    def mkdir(self, path, owner=None, group=None, mode=None, triggers=None, triggered_by=None):
        if self._before(triggered_by): return False
        path = os.path.realpath(path)
        is_new = self._mkdir(path)
            # subprocess.check_output(['mkdir', '-p', path])
        self._apply_permissions(path, owner, group, mode)
        return self._after(is_new, triggers)

    def _touch(self, path):
        self._mkdir(os.path.dirname(path))
        with open(path, 'a'):
            os.utime(path, None)

    def _read_file(self, path):
        return open(path, 'rb').read()

    def _write_file(self, path, data):
        with open(path, 'wb') as f:
            f.write(data)

    def file(self, dest_path, src_path=None, src_data=None, triggers=None, triggered_by=None):
        assert bool(src_path) != bool(src_data)
        if self._before(triggered_by): return False
        if dest_path[-1:] == '/' and src_path:
            _, tail = os.path.split(src_path)
            dest_path += tail
        dest_path = os.path.realpath(dest_path)
        file_existed = self._isfile(dest_path)
        if not file_existed: # mkdir and touch it!
            self._touch(dest_path)
        # TODO: perms
        old_contents = self._read_file(dest_path)
        if src_path is not None:
            src_data = self._read_file(src_path)
        if type(src_data) is dict:
            # TODO: json comparison before writing
            pass
        else:
            contents_match = src_data == old_contents
        if not contents_match:
            self._write_file(dest_path, src_data)
        return self._after(not (file_existed and contents_match), triggers)

    def template(self, dest_path, src_path=None, src_data=None, template_parameters=None, triggers=None, triggered_by=None, engine='jinja2', **kwargs):
        if engine == 'jinja2':
            return self.jinja2(dest_path, src_path, src_data, template_parameters, triggers, triggered_by, **kwargs)
        raise 'no matching template engine!'
    def jinja2(self, dest_path, src_path=None, src_data=None, template_parameters=None, triggers=None, triggered_by=None, **kwargs):
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
        try:
            grp.getgrnam(groupname)
            group_existed = True
        except KeyError:
            group_existed = False
        if not group_existed:
            cmd = ['groupadd']
            if gid is not None:
                cmd += ['-g', str(gid)]
            cmd += [groupname]
            subprocess.check_output(cmd)
        return self._after(not group_existed, triggers)

    def user(self, username, password=None, hashed_password=None, home=None, uid=None, gid=None, groups=None, shell=None, comment=None, triggers=None, triggered_by=None):
        '''
        http://serverfault.com/questions/367559/how-to-add-a-user-without-knowing-the-encrypted-form-of-the-password
        echo "P4sSw0rD" | openssl passwd -1 -stdin
        '''
        groups = groups or []
        try:
            pwd.getpwnam(username)
            user_existed = True
        except KeyError:
            user_existed = False
        if not user_existed:
            cmd = ['useradd']
            if home is False:
                cmd += ['-M']
            elif type(home) is str:
                cmd += ['-d', home]
            else:
                raise 'errrrrr'
            if uid is not None:
                cmd += ['-u', str(uid)]
            if gid is not None:
                cmd += ['-g', str(gid)]
            if shell is not None:
                cmd += ['-s', str(shell)]
            if comment is not None:
                cmd += ['-c', str(comment)]
            cmd += ['-U', username]
            subprocess.check_output(cmd)

        existing_groups = set(subprocess.check_output(['groups', username]).split(':')[-1].strip().split()) - set([username])
        changing_groups = set(existing_groups) == set(groups)
        for group in sorted(list(set(groups) - set(existing_groups))):
            subprocess.check_output(['gpasswd', '-a', username, group])
        for group in sorted(list(set(existing_groups) - set(groups))):
            subprocess.check_output(['gpasswd', '-d', username, group])

        if password is not None:
            # TODO: check that the password matches somehow?
            # from http://stackoverflow.com/questions/4688441/how-can-i-set-a-users-password-in-linux-from-a-python-script
            proc=subprocess.Popen(['passwd', 'test'],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            proc.stdin.write(str(password) + '\n')
            proc.stdin.write(str(password))
            proc.stdin.flush()
            stdout,stderr = proc.communicate()
        if hashed_password is not None:
            # TODO!
            # maybe chpasswd?
            pass

#passwd --stdin username
        return self._after(not user_existed or changing_groups, triggers)

    # TODO: rsync, line in file, git repo, user, group, user_complete, group_complete, apt