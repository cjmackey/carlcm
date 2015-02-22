
def mkdir(self, path, owner=None, group=None, mode=None):
    path = self.os.path.realpath(path)
    is_new = self._mkdir(path)
    perm_change = self._apply_permissions(path, owner, group, mode)
    return is_new or perm_change
