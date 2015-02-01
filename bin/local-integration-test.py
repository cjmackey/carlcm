#!/usr/bin/env python

import carlcm

c = carlcm.Context()

print 'package, should be true', c.package('dtrx')
print 'package, should be false', c.package('dtrx')

print 'user, should be true', c.user('carl')
print 'user, should be false', c.user('carl')

c.group('carltest')
print 'usergroup, should be true', c.user('carl', groups=['carltest'])
c.shell('ls -lah /home')
print 'usergroup, should be false', c.user('carl', groups=['carltest'])
c.shell('groups carl')
c.shell('ls -lah /home')
c.shell('userdel carl')
c.shell('rm -rf /home/carl')
c.shell('apt-get remove -y dtrx 2>&1 >>/dev/null')
