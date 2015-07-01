
import json

from nose.tools import *
from mock import Mock, MagicMock, call

import carlcm

c = None

class TestCarlCMConsulTests(object):

    def setup(self):
        global c
        c = carlcm.MockConfigurationManager()

    def test_server_config(self):
        m = carlcm.ConsulModule(mode='server')
        d = m._server_config()
        eq_(d['server'], True)
        eq_(d.get('ui_dir'), None)
        m = carlcm.ConsulModule(mode='server', webui=True)
        d = m._server_config()
        eq_(d['server'], True)
        eq_(d.get('ui_dir'), "/opt/consul/0.4.1/web/dist")
        eq_(d['addresses']['http'], '0.0.0.0')

    def test_module_server(self):
        m = carlcm.ConsulModule(mode='server')
        m._acquire_consul = Mock()
        m._acquire_webui = Mock()
        c.packages = Mock()
        c.add_modules(m)
        c.run_modules()
        eq_(c.users[1]['name'], 'consul')
        eq_(c.os.path.isfile('/etc/init/consul.conf'), True)

    def test_module_server(self):
        m = carlcm.ConsulModule(mode='client')
        m._acquire_consul = Mock()
        m._acquire_webui = Mock()
        c.packages = Mock()
        c.add_modules(m)
        c.run_modules()
        eq_(c.users[1]['name'], 'consul')
        eq_(c.os.path.isfile('/etc/init/consul.conf'), True)
        conf = json.loads(c.open('/etc/consul.d/config.json').read())
        eq_(conf['server'], False)
