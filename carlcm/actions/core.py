
from .action_module import ActionModule

class Core(ActionModule):

    def mkdir(self, context, path, owner=None, group=None, mode=None):
        path = context.os.path.realpath(path)
        is_new = context._mkdir(path)
        perm_change = context._apply_permissions(path, owner, group, mode)
        return is_new or perm_change
