
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

    def cmd(self, cmd, quiet=False, triggers=None, triggered_by=None, **kwargs):
        if self._before(triggered_by): return False
        if quiet:
            subprocess.check_output(cmd, **kwargs)
        else:
            subprocess.check_call(cmd, **kwargs)
        return self._after(True, triggers)

    def _mkdir(self, d):
        """
        Based on http://code.activestate.com/recipes/82465-a-friendly-mkdir/
        """
        d = os.path.realpath(d)
        if os.path.isdir(d):
            return False
        elif os.path.isfile(d):
            raise OSError("file exists: " % d)
        else:
            h, t = os.path.split(d)
            if h: self._mkdir(h)
            if t: os.mkdir(d)
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

    def mkdir(self, path, owner=None, group=None, mode=None, triggers=None, triggered_by=None):
        if self._before(triggered_by): return False
        path = os.path.realpath(path)
        is_new = not os.path.isdir(path)
        if is_new:
            self._mkdir(path)
            # subprocess.check_output(['mkdir', '-p', path])
        self._apply_permissions(path, owner, group, mode)
        return self._after(is_new, triggers)

    def file(self, dest_path, src_path=None, src_data=None, triggers=None, triggered_by=None):
        if self._before(triggered_by): return False
        if dest_path[-1:] == '/' and src_path:
            _, tail = os.path.split(src_path)
            dest_path += tail
        dest_path = os.path.realpath(dest_path)
        file_exists = os.path.isfile(dest_path)
        does_match = False
        if not file_exists: # mkdir and touch it!
            self._mkdir(os.path.dirname(dest_path))
            with open(dest_path, 'a'):
                os.utime(dest_path, None)
        # todo: perms
        if src_data is not None:
            file_len = os.stat(dest_path).st_size
            if file_len == len(src_data):
                dest_data = open(dest_path, 'rb').read()
                if dest_data == src_data:
                    does_match = True
            if not does_match:
                with open(dest_path, 'wb') as f:
                    f.write(src_data)
        elif src_path is not None:
            does_match = filecmp.cmp(dest_path, src_path)
            if not does_match:
                shutil.copyfile(src_path, dest_path)
        return self._after(not (file_exists and does_match), triggers)

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
            src_data = open(src_path, 'rb').read()
        # todo: also pass perms
        return self.file(dest_path = dest_path,
                         src_data = jinja2.Template(src_data).render(template_parameters),
                         triggers = triggers)

    # TODO: rsync, line in file, git repo, user, group, user_complete, group_complete
