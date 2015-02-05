
from stat import S_ISDIR

import fake_filesystem
from nose.tools import *
from mock import Mock, MagicMock, call

import carlcm

c = None

class TestCarlCMContext(object):

    def setup(self):
        self.fs = fake_filesystem.FakeFilesystem()
        self.os = fake_filesystem.FakeOsModule(self.fs)
        self.open = fake_filesystem.FakeFileOpen(self.fs)
        global c
        c = carlcm.Context(fake_os=self.os, fake_open=self.open)
        c._cmd = Mock()
        c._cmd_quiet = Mock()
        c._group_name_to_gid = Mock()
        c._user_name_to_uid = Mock()
        c._user_home = Mock()
        with self.open('existingfile', 'wb') as f:
            f.write('asdf')
        self.os.mkdir('existingdir')
        self.os.chmod('existingdir', 0712)
        self.os.chown('existingdir', 37, 75)

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
        eq_(c.mkdir('existingdir'), False)

    def test_mkdir_simple_not_exists(self):
        eq_(self.os.path.isdir('/path'), False)
        eq_(c.mkdir('/path'), True)
        eq_(self.os.path.isdir('/path'), True)

    def test_mkdir_complex_not_exists(self):
        eq_(self.os.path.isdir('/pa/th'), False)
        eq_(c.mkdir('/pa/th'), True)
        eq_(self.os.path.isdir('/pa/th'), True)

    def test__apply_permissions_matched_num(self):
        eq_(c._apply_permissions('existingdir', 37, 75, '712'), False)

    def test__apply_permissions_unmatched_uid(self):
        eq_(c._apply_permissions('existingdir', 38, 75, '712'), True)
        eq_(self.os.stat('existingdir').st_uid, 38)

    def test__apply_permissions_unmatched_gid(self):
        eq_(c._apply_permissions('existingdir', 37, 76, '712'), True)
        eq_(self.os.stat('existingdir').st_gid, 76)

    def test__apply_permissions_unmatched_mode(self):
        eq_(c._apply_permissions('existingdir', 37, 76, '715'), True)
        eq_(self.os.stat('existingdir').st_mode & 0777, 0715)

    def test_file_already_exists_and_equal_src_data(self):
        eq_(c.file('existingfile', src_data='asdf'), False)

    def test_file_already_exists_and_equal_src_path(self):
        with self.open('src', 'wb') as f: f.write('asdf')
        eq_(c.file('existingfile', src_path='src'), False)

    def test_file_already_exists_and_unequal_src_data(self):
        eq_(c.file('existingfile', src_data='ff'), True)
        eq_(self.open('existingfile', 'rb').read(), 'ff')

    def test_file_already_exists_and_unequal_src_path(self):
        with self.open('src', 'wb') as f: f.write('ff')
        eq_(c.file('existingfile', src_path='src'), True)
        eq_(self.open('existingfile', 'rb').read(), 'ff')

    def test_file_new_src_data(self):
        eq_(c.file('/file.txt', src_data='asdf'), True)
        eq_(self.open('/file.txt', 'rb').read(), 'asdf')

    def test_file_new_src_path_subdir(self):
        with self.open('file.txt', 'wb') as f: f.write('asdf')
        eq_(c.file('dir/subdir/', src_path='file.txt'), True)
        eq_(self.open('dir/subdir/file.txt', 'rb').read(), 'asdf')

    def test_line_in_file_exists(self):
        c.file('f', src_data='asdf\n')
        eq_(c.line_in_file('f', 'blah'), True)
        eq_(self.open('f', 'rb').read(), 'asdf\nblah\n')

    def test_line_in_file_exists_and_matches(self):
        c.file('f', src_data='asdf\n')
        eq_(c.line_in_file('f', 'asdf'), False)
        eq_(self.open('f', 'rb').read(), 'asdf\n')

    def test_line_in_file_exists_no_newline(self):
        c.file('f', src_data='asdf')
        eq_(c.line_in_file('f', 'blah'), True)
        eq_(self.open('f', 'rb').read(), 'asdf\nblah\n')

    def test_line_in_file_absent_match(self):
        c.file('f', src_data='asdf\n')
        eq_(c.line_in_file('f', 'asdf', state='absent'), True)
        eq_(self.open('f', 'rb').read(), '\n')

    def test_line_in_file_absent_nomatch(self):
        c.file('f', src_data='asdf\n')
        eq_(c.line_in_file('f', 'fasdf', state='absent'), False)
        eq_(self.open('f', 'rb').read(), 'asdf\n')

    def test_line_in_file_regexp_match(self):
        c.file('f', src_data='asdf')
        eq_(c.line_in_file('f', regexp='^as', line='blah'), True)
        eq_(self.open('f', 'rb').read(), 'blah\n')

    def test_line_in_file_regexp_match_equal(self):
        c.file('f', src_data='asdf\n')
        eq_(c.line_in_file('f', regexp='^as', line='asdf'), False)
        eq_(self.open('f', 'rb').read(), 'asdf\n')

    def test_line_in_file_regexp_nomatch(self):
        eq_(c.line_in_file('existingfile', regexp='^bl', line='blah'), True)
        eq_(self.open('existingfile', 'rb').read(), 'asdf\nblah\n')

    def test_line_in_file_regexp_absent_match(self):
        c.file('f', src_data='asdf\n')
        eq_(c.line_in_file('f', regexp='^as', state='absent'), True)
        eq_(self.open('f', 'rb').read(), '\n')

    def test_line_in_file_regexp_absent_nomatch(self):
        c.file('f', src_data='asdf\n')
        eq_(c.line_in_file('f', regexp='^b', state='absent'), False)
        eq_(self.open('f', 'rb').read(), 'asdf\n')

    @raises(ValueError)
    def test_line_in_file_file_nonexistent(self):
        c.line_in_file('nonexistentfile', regexp='^bl', line='blah')

    def test_template_new_src_data(self):
        eq_(c.template('/file.txt', src_data='{{ x }}df', x='as'), True)
        eq_(self.open('/file.txt', 'rb').read(), 'asdf')

    def test_template_new_src_path(self):
        with self.open('src.j2', 'wb') as f: f.write('{{ x }}df')
        eq_(c.template('/file.txt', src_path='src.j2', x='as'), True)
        eq_(self.open('/file.txt', 'rb').read(), 'asdf')

    def test_template_match_src_data(self):
        eq_(c.template('existingfile', src_data='{{ x }}df', x='as'), False)

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
        eq_(c.mkdir('existingdir', triggers='t6'), False)
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
        c._group_name_to_gid = Mock(side_effect=[76])
        c._user_name_to_uid = Mock(side_effect=[None, 31])
        eq_(c.user('jessie'), True)
        c._user_name_to_uid.assert_has_calls([call('jessie'), call('jessie')])
        c._cmd_quiet.assert_called_once_with(['useradd', '-U', 'jessie'])
        eq_(self.os.path.isdir('/home/jessie'), True)
        eq_(self.os.stat('/home/jessie').st_mode & 0777, 0755)
        eq_(self.os.stat('/home/jessie').st_uid, 31)
        eq_(self.os.stat('/home/jessie').st_gid, 76)

    def test_user_new_homeless(self):
        c._user_name_to_uid.return_value = None
        eq_(c.user('jessie', home=False), True)
        c._cmd_quiet.assert_called_once_with(['useradd', '-M', '-U', 'jessie'])
        eq_(self.os.path.isdir('/home/jessie'), False)

    def test_user_new_homed(self):
        c._user_name_to_uid.return_value = None
        c._user_home.return_value = '/var/jessie'
        c._group_name_to_gid = Mock(side_effect=[76])
        c._user_name_to_uid = Mock(side_effect=[None, 31])
        eq_(c.user('jessie', home='/var/jessie'), True)
        c._user_name_to_uid.assert_has_calls([call('jessie'), call('jessie')])
        c._cmd_quiet.assert_called_once_with(['useradd', '-d', '/var/jessie',
                                              '-U', 'jessie'])
        eq_(self.os.path.isdir('/home/jessie'), False)
        eq_(self.os.path.isdir('/var/jessie'), True)
        eq_(self.os.stat('/var/jessie').st_mode & 0777, 0755)
        eq_(self.os.stat('/var/jessie').st_uid, 31)
        eq_(self.os.stat('/var/jessie').st_gid, 76)
    """
    TODO!
    def test_user_exists_authorized_keys(self):
        c._user_name_to_uid.return_value = 1002
        eq_(c.group('jessie', authorized_keys=['blahblah']), False)
        c._cmd_quiet.assert_has_calls([])
    """
    def test_user_groups_unchanged(self):
        c._user_name_to_uid.return_value = 1003
        c._cmd_quiet.side_effect = ['jessie : jessie admins wheel gamers\n']
        eq_(c.user('jessie', home=False, groups=['wheel', 'admins', 'gamers']), False)
        c._cmd_quiet.assert_has_calls([call(['groups', 'jessie'])])

    def test_user_groups_changed(self):
        c._user_name_to_uid.return_value = 1003
        c._cmd_quiet.side_effect = ['jessie : jessie admins devs docker\n',
                                    None, None, None, None]
        eq_(c.user('jessie', home=False, groups=['wheel', 'admins', 'gamers']), True)
        c._cmd_quiet.assert_has_calls([call(['groups', 'jessie']),
                                       call(['gpasswd', '-a', 'jessie', 'gamers']),
                                       call(['gpasswd', '-a', 'jessie', 'wheel']),
                                       call(['gpasswd', '-d', 'jessie', 'devs']),
                                       call(['gpasswd', '-d', 'jessie', 'docker'])])
