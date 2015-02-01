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

    def test_cmd(self):
        eq_(c.cmd(['pwd']), True)
        c._cmd.assert_called_once_with(['pwd'])

    def test_cmd_quiet(self):
        eq_(c.cmd(['pwd'], quiet=True), True)
        c._cmd_quiet.assert_called_once_with(['pwd'])

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
