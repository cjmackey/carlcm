#!/usr/bin/env python

import os

import carlcm

script_dir = os.path.dirname(os.path.realpath(__file__))
test_dir = os.path.join(script_dir, 'test/sandbox')

os.chdir(script_dir)

c = carlcm.Context()

c.mkdir(test_dir + '/a/b/c/d')

assert c.cmd(['rm', '-r', test_dir], triggers='test-trigger-1')
assert c.cmd(['echo', 'echo-test'])
assert c.cmd(['echo', 'quiet-echo-test'], quiet=True)
assert c.shell('echo blah >> /dev/null')

assert c.file(test_dir + '/file-tests/src-data-test', src_data='blah')
assert not c.file(test_dir + '/file-tests/src-data-test', src_data='blah', triggers='test-trigger-2')
assert c.file(test_dir + '/file-tests/src-path-test', 'carlcm.py')
assert not c.file(test_dir + '/file-tests/src-path-test', 'carlcm.py')
assert  c.file(test_dir + '/file-tests/src-path-with-slash-test/', 'carlcm.py')
assert not c.file(test_dir + '/file-tests/src-path-with-slash-test/', 'carlcm.py')

assert c.file(test_dir + '/trigger-tests/1', src_data='blah1', triggered_by='test-trigger-1')
assert not c.file(test_dir + '/trigger-tests/2', src_data='blah2', triggered_by='test-trigger-2')

assert c.template(test_dir + '/template-tests/1', src_path='test/example-template.j2', x='hello template')
assert not c.template(test_dir + '/template-tests/1', src_path='test/example-template.j2', x='hello template')

assert c.mkdir(test_dir + '/permission-test-dir', 'carl', 'carltest', '721')
