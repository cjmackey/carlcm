
import jinja2

from .action_module import ActionModule

class Core(ActionModule):

    def mkdir(self, path, owner=None, group=None, mode=None):
        path = self.context.os.path.realpath(path)
        is_new = self.context._mkdir(path)
        perm_change = self.context._apply_permissions(path, owner, group, mode)
        return is_new or perm_change
