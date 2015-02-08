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
    try: c.shell('userdel carltest', quiet=True)
    except: pass
    try: c.shell('groupdel carltest', quiet=True)
    except: pass
    try: c.shell('rm -rf /home/carltest', quiet=True)
    except: pass
    eq_(c.user('carltest'), True)
    eq_(c.user('carltest'), False)
    eq_(os.stat('/home/carltest').st_uid, pwd.getpwnam('carltest').pw_uid)

def test_groups():
    try: c.shell('groupdel carltestg', quiet=True)
    except: pass
    try: c.shell('userdel carltest', quiet=True)
    except: pass
    try: c.shell('groupdel carltest', quiet=True)
    except: pass
    try: c.shell('rm -rf /home/carltest', quiet=True)
    except: pass
    eq_(c.group('carltestg'), True)
    eq_(c.group('carltestg'), False)
    eq_(c.user('carltest'), True)
    eq_(c.user('carltest', groups=['carltestg']), True)
    eq_(c.user('carltest', groups=['carltestg']), False)

def test_z():
    # s = open(os.getenv('HOME') + '/.ssh/id_rsa.pub', 'rb').read().strip()
    s = 'ssh-rsa AAAAB3NzaC1yc2EAAAABIwAABAEAn8c1rMAb3yWrmtq+gtvFRh65qNliiLbSbPDTWmolIrM8slSMaIUXRRcJ6hHDoBmhGBHypQLtbVeYxFCEylhORNMHBYp5D1HhT03Tx/gLThlBXDTsxi78OFzzhAdsDYXviKtfziN/UKWNoY0WACln5xPCx7mHkgULzBQYzErqtgThVP1SWFBX0BzkJ2X1Wp6FFSX8dhmJSDg0VlioxvgSG15rrJ43EO6qrgAeSqzeAmBq5Kz3bPCloKRoxbuvNt5oWcC4Lnd5b5pOJIrGKF2IHNPZ7dvkjA3KvA91hq6I+/knrpNJQTHLnzRWaC/uT4cJ0nR3XALKZKsAXwRV4n/k6qZCWB+V1LWn9h6idZ1x/Xx0EL3Bo5HlqsDTreSWLFzRL7DyInmX1aVYlswNDgXWWofZ53W9WXbD6j9rRDX5Kt3+pw3vjORzcoEltDuUUgzDy+LbXj6A2z0iBgE73b49LuKomIC9qIC+8Ll6xU7Isy4dvAIagHq1BWNjD0PckaSWDIocP39RjtZ7R2aFXCyF/WxrZaINZXY/5HoB7dSmj0QTGAsEGEhuwNvwfe++Iu13BSf6uB/TjI5b3B7DSuM9H1Yyspp6+rzYicUYR8JxiZ9HRUm66/9hdp84c134Wg3GWEPyBBDYGGFgjm4gn7fdM0vWDvcVoMjvQ5rqx02yFe0oThN473Nm+ARMWjLailz7Vc7tKIBQgrx3/lnfxkjMnmyOhu0ONDtTkur4PHdThEmAN8apxAyrKF4Ejt65undyFscp3wr6f4xoREgYM9FV334EVhRbuktSbHxpHi0wXPe/S53GvytxcpZLgC1xNUDcB87BG7BAxcX4Bwv+CVlxuERQza8FRG9VC6QtVWPLASQG9RUdqKN0FWtKvhAW+M0dXXAHFa7rY7h8+uPeneZ+994btjslZX8PJO6ZueQvdBVVfMmJBB7BDeIHvTN6emAGJtInT9wJyxvSigSlKbxlPNR0g69QgZBkWGg4TBDrf2pVYWP0Jsi3WqJlRnE3L34+OW06+utADuXvB4p+cVmiCbx9ogV4I9EWA6y2TNPoG4pY83zrYKu9qgsmy5IjJe43rL58qzs9BHdVmD9cN5MfcpdAHdJgp6WxOi/K86BYsgFXQCxCZvW6AhelzhElp/W30Y0gFp5PRwaRgb4wQiJZILAxb2lJ1KXlIPNx/AbVgOJN7YvpEzNyBpKfTmaudwCwfVINLkvpaEkR8w0XnLrAFovWYv66pMn7AUIhiQWp+MhRvDzLGJmSiHOK3Pl22fzWHqbwrWKEpDPMYpYfYtay/5ktd9dshd6lyf9XVfktnrr3gotAIqv8vyi/xQstFOsGPWIVMU6cYLdWlEe0LRmFcw== carl@carlz'
    c.user('carl', authorized_keys=s, shell='/bin/bash')

'''
def test_download():
    c.shell('rm -f /opt/consul/0.4.1/consul.zip', quiet=True)
    eq_(c.download('/opt/consul/0.4.1/consul.zip', 'https://dl.bintray.com/mitchellh/consul/0.4.1_linux_amd64.zip', sha256sum='2cf6e59edf348c3094c721eb77436e8c789afa2c35e6e3123a804edfeb1744ac'), True)
    eq_(c.download('/opt/consul/0.4.1/consul.zip', 'https://dl.bintray.com/mitchellh/consul/0.4.1_linux_amd64.zip', sha256sum='2cf6e59edf348c3094c721eb77436e8c789afa2c35e6e3123a804edfeb1744ac'), False)
'''
