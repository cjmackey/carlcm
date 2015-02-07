
from stat import S_ISDIR, S_IMODE

import fake_filesystem
from nose.tools import *
from mock import Mock, MagicMock, call

import carlcm

c = None

class TestCarlCMContext(object):

    def setup(self):
        global c
        c = carlcm.MockContext()
        self.open = c.open
        self.os = c.os
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
        eq_(S_IMODE(self.os.stat('existingdir').st_mode), 0715)

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

    def test__groupadd_cmd(self):
        eq_(c._groupadd_cmd('agroup'), ['groupadd', 'agroup'])
        eq_(c._groupadd_cmd('agroup', gid=45), ['groupadd', '-g', '45', 'agroup'])

    def test__useradd_cmd(self):
        eq_(c._useradd_cmd('auser'), ['useradd', '-U', 'auser'])
        eq_(c._useradd_cmd('auser', gid=45), ['useradd', '-g', '45', '-U', 'auser'])
        eq_(c._useradd_cmd('auser', uid=45), ['useradd', '-u', '45', '-U', 'auser'])
        eq_(c._useradd_cmd('auser', home=False), ['useradd', '-M', '-U', 'auser'])
        eq_(c._useradd_cmd('auser', home='/var/auser'), ['useradd', '-d', '/var/auser', '-U', 'auser'])
        eq_(c._useradd_cmd('auser', shell='/bin/zsh'), ['useradd', '-s', '/bin/zsh', '-U', 'auser'])
        eq_(c._useradd_cmd('auser', comment='blah'), ['useradd', '-c', 'blah', '-U', 'auser'])

    def test_group_exists(self):
        c.groups += [{'name':'group', 'id': 1003}]
        eq_(c.group('group'), False)

    def test_group_new(self):
        eq_(c.group('group'), True)
        eq_(c.groups[1], {'name':'group', 'id': 1000})

    def test_group_new_with_gid(self):
        eq_(c.group('group', gid=74), True)
        eq_(c.groups[1], {'name':'group', 'id': 74})

    def test_user_exists(self):
        c.users += [{'name':'jessie', 'id':1002, 'home':None}]
        eq_(c.user('jessie', home=False), False)

    def test_user_new(self):
        eq_(c.user('jessie'), True)
        eq_(c.users[1]['name'], 'jessie')
        eq_(c.users[1]['groups'], ['jessie'])
        eq_(c.groups[1]['name'], 'jessie')
        eq_(self.os.path.isdir('/home/jessie'), True)
        eq_(S_IMODE(self.os.stat('/home/jessie').st_mode), 0755)
        eq_(self.os.stat('/home/jessie').st_uid, 1000)
        eq_(self.os.stat('/home/jessie').st_gid, 1000)

    def test_user_new_homeless(self):
        eq_(c.user('jessie', home=False), True)
        eq_(self.os.path.isdir('/home/jessie'), False)

    def test_user_new_homed(self):
        eq_(c.user('jessie', home='/var/jessie', uid=31, gid=76, home_mode='750'), True)
        eq_(self.os.path.isdir('/home/jessie'), False)
        eq_(self.os.path.isdir('/var/jessie'), True)
        eq_(S_IMODE(self.os.stat('/var/jessie').st_mode), 0750)
        eq_(self.os.stat('/var/jessie').st_uid, 31)
        eq_(self.os.stat('/var/jessie').st_gid, 76)

    def test_user_new_grouped(self):
        eq_(c.user('jessie', groups=['agroup', 'bgroup']), True)
        eq_(c.users[1]['name'], 'jessie')
        eq_(c.users[1]['groups'], ['agroup', 'bgroup', 'jessie'])

    def test_user_authorized_keys(self):
        eq_(c.user('jessie', authorized_keys='ssh-rsa blah== blah@blah'), True)
        eq_(c._read_file('/home/jessie/.ssh/authorized_keys'),
            'ssh-rsa blah== blah@blah')
        eq_(S_IMODE(self.os.stat('/home/jessie/.ssh').st_mode), 0700)
        eq_(S_IMODE(self.os.stat('/home/jessie/.ssh/authorized_keys').st_mode), 0600)
        eq_(c.user('jessie', authorized_keys=['ssh-rsa blah== blah@blah']), False)
        eq_(c.user('jessie', authorized_keys=None), False)
        eq_(c.user('jessie', authorized_keys='x'), True)
        eq_(c._read_file('/home/jessie/.ssh/authorized_keys'), 'x')
        eq_(c.user('jessie', authorized_keys=['a','b','c']), True)
        eq_(c._read_file('/home/jessie/.ssh/authorized_keys'), 'a\nb\nc')

    @raises(AssertionError)
    def test_user_authorized_keys_homeless(self):
        c.user('jessie', authorized_keys='ssh-rsa blah== blah@blah', home=False)

    def test_user_groups_unchanged(self):
        c.users += [{'name':'jessie', 'id':1000,
                     'groups':['wheel', 'admins', 'gamers', 'jessie']}]
        eq_(c.user('jessie', home=False, groups=['wheel', 'admins', 'gamers']), False)

    def test_user_groups_changed(self):
        c.users += [{'name':'jessie', 'id':1000,
                     'groups':['devs', 'admins', 'gamers', 'jessie']}]
        eq_(c.user('jessie', home=False, groups=['wheel', 'admins', 'gamers']), True)
        eq_(c.users[1]['groups'], ['admins', 'gamers', 'jessie', 'wheel'])

    def test_current_packages(self):
        c._cmd_quiet.side_effect = ['''
Desired=Unknown/Install/Remove/Purge/Hold
| Status=Not/Inst/Conf-files/Unpacked/halF-conf/Half-inst/trig-aWait/Trig-pend
|/ Err?=(none)/Reinst-required (Status,Err: uppercase=bad)
||/ Name                                                  Version                                             Architecture Description
+++-=====================================================-===================================================-============-===============================================================================
ii  ack-grep                                              2.12-1                                              all          grep-like program specifically for large source trees
ii  acpid                                                 1:2.0.21-1ubuntu2                                   amd64        Advanced Configuration and Power Interface event daemon
''']
        eq_(c.current_packages(), {'ack-grep':'2.12-1','acpid':'1:2.0.21-1ubuntu2'})
        eq_(c.current_packages(), {'ack-grep':'2.12-1','acpid':'1:2.0.21-1ubuntu2'})
        c._cmd_quiet.assert_has_calls([call(['dpkg', '-l'])])

    def test_packages_new(self):
        c.current_packages = Mock(return_value={})
        eq_(c.packages(['ack-grep', 'acpid']), True)
        c._cmd_quiet.assert_called_once_with(['apt-get', 'install', '-y', 'ack-grep', 'acpid'])

    def test_packages_present(self):
        c.current_packages = Mock(return_value={'ack-grep':'2.12-1','acpid':'1:2.0.21-1ubuntu2'})
        eq_(c.packages(['ack-grep', 'acpid']), False)
        c._cmd_quiet.assert_has_calls([])

    def test_packages_mixed(self):
        c.current_packages = Mock(return_value={'ack-grep':'2.12-1'})
        eq_(c.packages(['ack-grep', 'acpid']), True)
        c._cmd_quiet.assert_called_once_with(['apt-get', 'install', '-y', 'acpid'])

    def test_download_new(self):
        c.mock_urls['http://blah.com/blah.txt'] = 'asdf\n'
        eq_(c.download('/blah.txt', 'http://blah.com/blah.txt'), True)
        eq_(c._read_file('/blah.txt'), 'asdf\n')

    def test_download_new_hash_match(self):
        c.mock_urls['http://blah.com/blah.txt'] = 'asdf\n'
        eq_(c.download('/blah.txt', 'http://blah.com/blah.txt',
                       md5='2b00042f7481c7b056c4b410d28f33cf'), True)
        eq_(c._read_file('/blah.txt'), 'asdf\n')

    @raises(AssertionError)
    def test_download_new_hash_mismatch(self):
        c.mock_urls['http://blah.com/blah.txt'] = 'asdf\n'
        c.download('/blah.txt', 'http://blah.com/blah.txt',
                   md5='2b10042f7481c7b056c4b410d28f33cf')

    def test_download_exists(self):
        # NOTE: doesn't even download!
        c._write_file('/blah.txt', 'asdf\n')
        eq_(c.download('/blah.txt', 'http://blah.com/blah.txt'), False)
        eq_(c._read_file('/blah.txt'), 'asdf\n')

    def test_download_exists_hash_match(self):
        c._write_file('/blah.txt', 'asdf\n')
        eq_(c.download('/blah.txt', 'http://blah.com/blah.txt',
                       md5='2b00042f7481c7b056c4b410d28f33cf'), False)

    def test_download_exists_hash_mismatch(self):
        c.mock_urls['http://blah.com/blah.txt'] = 'asdf\n'
        c._write_file('/blah.txt', 'asdff\n')
        eq_(c.download('/blah.txt', 'http://blah.com/blah.txt',
                       md5='2b00042f7481c7b056c4b410d28f33cf'), True)
        eq_(c._read_file('/blah.txt'), 'asdf\n')
