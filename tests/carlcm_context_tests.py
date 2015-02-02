from nose.tools import *
from mock import Mock, MagicMock, call

import carlcm

c = None

class TestCarlCMContext(object):

    def setup(self):
        global c
        c = carlcm.Context()
        c._cmd = Mock()
        c._cmd_quiet = Mock()
        c._isdir = Mock()
        c._isfile = Mock()
        c._mkdir_1 = Mock()
        c._read_file = Mock()
        c._write_file = Mock()
        c._touch = Mock()
        c._chmod = Mock()
        c._chown = Mock()
        c._stat = Mock()
        c._group_name_to_gid = Mock()
        c._user_name_to_uid = Mock()
        c._user_home = Mock()

    def test_cmd(self):
        eq_(c.cmd(['pwd']), True)
        c._cmd.assert_called_once_with(['pwd'])

    def test_cmd_quiet(self):
        eq_(c.cmd(['pwd'], quiet=True), True)
        c._cmd_quiet.assert_called_once_with(['pwd'])

    def test_shell(self):
        c.cmd = Mock(return_value=True)
        eq_(c.shell('pwd'), True)
        c.cmd.assert_called_once_with('pwd', shell=True)

    def test_mkdir_already_exists(self):
        c._isdir.return_value=True
        eq_(c.mkdir('/path'), False)
        c._isdir.assert_called_once_with('/path')

    def test_mkdir_simple_not_exists(self):
        c._isdir.side_effect=[False, True]
        c._isfile.return_value=False
        eq_(c.mkdir('/path'), True)
        c._isdir.assert_has_calls([call('/path'), call('/')])
        c._isfile.assert_called_once_with('/path')
        c._mkdir_1.assert_called_once_with('/path')

    def test_mkdir_complex_not_exists(self):
        c._isdir.side_effect=[False, False, True]
        c._isfile.return_value=False
        eq_(c.mkdir('/pa/th'), True)
        c._isdir.assert_has_calls([call('/pa/th'), call('/pa'), call('/')])
        c._isfile.assert_has_calls([call('/pa/th'), call('/pa')])
        c._mkdir_1.assert_has_calls([call('/pa'), call('/pa/th')])

    def test__apply_permissions_matched_num(self):
        st = Mock(st_mode=0712, st_uid=37, st_gid=75)
        c._stat.return_value = st
        eq_(c._apply_permissions('path', 37, 75, '712'), False)
        c._chmod.assert_has_calls([])
        c._chown.assert_has_calls([])

    def test__apply_permissions_unmatched_num(self):
        st = Mock(st_mode=0712, st_uid=37, st_gid=75)
        c._stat.return_value = st
        eq_(c._apply_permissions('path', 37, 76, '712'), True)
        c._chmod.assert_has_calls([])
        c._chown.assert_has_calls([call('path', 37, 76)])

    def test_file_already_exists_and_equal_src_data(self):
        c._isfile.return_value=True
        c._read_file.return_value='asdf'
        eq_(c.file('/file.txt', src_data='asdf'), False)
        c._isfile.assert_called_once_with('/file.txt')
        c._read_file.assert_called_once_with('/file.txt')
        c._write_file.assert_calls([])

    def test_file_already_exists_and_equal_src_path(self):
        c._isfile.return_value=True
        c._read_file.return_value='asdf'
        eq_(c.file('/file.txt', src_path='/asdf'), False)
        c._isfile.assert_called_once_with('/file.txt')
        c._read_file.assert_has_calls([call('/file.txt'), call('/asdf')])
        c._write_file.assert_calls([])

    def test_file_already_exists_and_unequal_src_data(self):
        c._isfile.return_value=True
        c._read_file.return_value='fasdf'
        eq_(c.file('/file.txt', src_data='asdf'), True)
        c._isfile.assert_called_once_with('/file.txt')
        c._read_file.assert_called_once_with('/file.txt')
        c._write_file.assert_called_once_with('/file.txt', 'asdf')

    def test_file_already_exists_and_unequal_src_path(self):
        c._isfile.return_value=True
        c._read_file.side_effect=['fasdf', 'asdf']
        eq_(c.file('/file.txt', src_path='/asdf'), True)
        c._isfile.assert_called_once_with('/file.txt')
        c._read_file.assert_has_calls([call('/file.txt'), call('/asdf')])
        c._write_file.assert_called_once_with('/file.txt', 'asdf')

    def test_file_new_src_data(self):
        c._isfile.return_value = False
        c._read_file.return_value = ''
        c._mkdir = Mock()
        eq_(c.file('/file.txt', src_data='asdf'), True)
        c._isfile.assert_called_once_with('/file.txt')
        c._touch.assert_called_once_with('/file.txt')
        c._read_file.assert_called_once_with('/file.txt')
        c._write_file.assert_called_once_with('/file.txt', 'asdf')

    def test_file_new_src_path_subdir(self):
        c._isfile.return_value = False
        c._read_file.side_effect = ['', 'asdf']
        c._mkdir = Mock()
        eq_(c.file('/', src_path='file.txt'), True)
        c._isfile.assert_called_once_with('/file.txt')
        c._touch.assert_called_once_with('/file.txt')
        c._read_file.assert_has_calls([call('/file.txt'), call('file.txt')])
        c._write_file.assert_called_once_with('/file.txt', 'asdf')

    def test_template_new_src_data(self):
        c._isfile.return_value = True
        c._read_file.return_value = ''
        eq_(c.template('/file.txt', src_data='{{ x }}df', x='as'), True)
        c._write_file.assert_called_once_with('/file.txt', 'asdf')

    def test_template_new_src_path(self):
        c._isfile.return_value = True
        c._read_file.side_effect = ['{{ x }}df', '']
        eq_(c.template('/file.txt', src_path='asdf.j2', x='as'), True)
        c._read_file.assert_has_calls([call('asdf.j2'), call('/file.txt')])
        c._write_file.assert_called_once_with('/file.txt', 'asdf')

    def test_template_match_src_data(self):
        c._isfile.return_value = True
        c._read_file.return_value = 'asdf'
        eq_(c.template('/file.txt', src_data='{{ x }}df', x='as'), False)
        c._write_file.assert_has_calls([])

    def test_triggers(self):
        eq_(c.cmd([], triggered_by='t1'), False)
        eq_(c.cmd([], triggers='t1'), True)
        eq_(c.cmd([], triggered_by='t1'), True)
        eq_(c.cmd([], triggered_by=['t1', 't2']), True)
        eq_(c.cmd([], triggered_by=['t2', 't3']), False)
        eq_(c.cmd([], triggers=['t2','t3']), True)
        eq_(c.cmd([], triggered_by=['t3']), True)
        eq_(c.cmd([], triggered_by='t4', triggers='t5'), False)
        eq_(c.cmd([], triggered_by='t5'), False)
        c._isdir.return_value=True
        eq_(c.mkdir('/path', triggers='t6'), False)
        eq_(c.cmd([], triggered_by='t6'), False)

    def test_group_exists(self):
        c._group_name_to_gid.return_value = 1003
        eq_(c.group('group'), False)
        c._group_name_to_gid.assert_called_once_with('group')
        c._cmd_quiet.assert_has_calls([])

    def test_group_new(self):
        c._group_name_to_gid.return_value = None
        eq_(c.group('group'), True)
        c._group_name_to_gid.assert_called_once_with('group')
        c._cmd_quiet.assert_called_once_with(['groupadd', 'group'])

    def test_group_new_with_gid(self):
        c._group_name_to_gid.return_value = None
        eq_(c.group('group', gid=74), True)
        c._group_name_to_gid.assert_called_once_with('group')
        c._cmd_quiet.assert_called_once_with(['groupadd', '-g', '74', 'group'])

    def test_user_exists(self):
        c._user_name_to_uid.return_value = 1002
        eq_(c.group('jessie'), False)
        c._cmd_quiet.assert_has_calls([])

    def test_user_new(self):
        c._user_name_to_uid.return_value = None
        c._user_home.return_value = '/home/jessie'
        c._mkdir = Mock()
        c._apply_permissions = Mock()
        eq_(c.user('jessie'), True)
        c._user_name_to_uid.assert_called_once_with('jessie')
        c._cmd_quiet.assert_called_once_with(['useradd', '-U', 'jessie'])
        c._mkdir.assert_called_once_with('/home/jessie')
        c._apply_permissions.assert_called_once_with('/home/jessie', 'jessie',
                                                     'jessie', '755')

    def test_user_new_homeless(self):
        c._user_name_to_uid.return_value = None
        eq_(c.user('jessie', home=False), True)
        c._cmd_quiet.assert_called_once_with(['useradd', '-M', '-U', 'jessie'])

    def test_user_new_homed(self):
        c._user_name_to_uid.return_value = None
        c._user_home.return_value = '/var/jessie'
        c._mkdir = Mock()
        c._apply_permissions = Mock()
        eq_(c.user('jessie', home='/var/jessie'), True)
        c._cmd_quiet.assert_called_once_with(['useradd', '-d', '/var/jessie',
                                              '-U', 'jessie'])
        c._mkdir.assert_called_once_with('/var/jessie')
        c._apply_permissions.assert_called_once_with('/var/jessie', 'jessie',
                                                     'jessie', '755')
    '''
    TODO!
    def test_user_exists_authorized_keys(self):
        c._user_name_to_uid.return_value = 1002
        eq_(c.group('jessie', authorized_keys=['blahblah']), False)
        c._cmd_quiet.assert_has_calls([])
    '''
    def test_user_groups_unchanged(self):
        c._user_name_to_uid.return_value = 1003
        c._cmd_quiet.side_effect = ['jessie : jessie admins wheel gamers\n']
        eq_(c.user('jessie', groups=['wheel', 'admins', 'gamers']), False)
        c._cmd_quiet.assert_has_calls([call(['groups', 'jessie'])])

    def test_user_groups_changed(self):
        c._user_name_to_uid.return_value = 1003
        c._cmd_quiet.side_effect = ['jessie : jessie admins devs docker\n',
                                    None, None, None, None]
        eq_(c.user('jessie', groups=['wheel', 'admins', 'gamers']), True)
        c._cmd_quiet.assert_has_calls([call(['groups', 'jessie']),
                                       call(['gpasswd', '-a', 'jessie', 'gamers']),
                                       call(['gpasswd', '-a', 'jessie', 'wheel']),
                                       call(['gpasswd', '-d', 'jessie', 'devs']),
                                       call(['gpasswd', '-d', 'jessie', 'docker'])])
