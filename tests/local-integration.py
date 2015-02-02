#!/usr/bin/env python

import os
import pwd

from nose.tools import *

import carlcm

c = carlcm.Context()

def test_packages():
    try: c.shell('apt-get remove -y dtrx 2>&1 >>/dev/null', quiet=True)
    except: pass
    eq_(c.package('dtrx'), True)
    eq_(c.package('dtrx'), False)

def test_users():
    try: c.shell('userdel carl', quiet=True)
    except: pass
    try: c.shell('rm -rf /home/carl', quiet=True)
    except: pass
    eq_(c.user('carl'), True)
    eq_(c.user('carl'), False)
    eq_(os.stat('/home/carl').st_uid, pwd.getpwnam('carl').pw_uid)

def test_groups():
    try: c.shell('groupdel carltest', quiet=True)
    except: pass
    try: c.shell('userdel carl', quiet=True)
    except: pass
    try: c.shell('rm -rf /home/carl', quiet=True)
    except: pass
    eq_(c.group('carltest'), True)
    eq_(c.group('carltest'), False)
    eq_(c.user('carl'), True)
    eq_(c.user('carl', groups=['carltest']), True)
    eq_(c.user('carl', groups=['carltest']), False)
