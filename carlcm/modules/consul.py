'''

Installs Consul.

If webui is True, it will enable the web ui, visible at 'http://localhost:8500/ui'

'''

from .base import BaseModule

# TODO: tls
# https://www.digitalocean.com/community/tutorials/how-to-secure-consul-with-tls-encryption-on-ubuntu-14-04

# TODO: configurable consul version number?

# TODO: figure out how to put service definitions into this
# http://www.consul.io/docs/agent/services.html
# also, changing service definitions should only send a SIGHUP, not restart the process
# ...maybe service definitions should be available at the Module level, so there's no race between consul and other modules' instantiations

class ConsulModule(BaseModule):

    def __init__(self, encrypt=None, mode='client', servers=None, webui=False,
                 datacenter=None, bootstrap_expect=1):
        assert mode in ['client', 'server']
        self.mode = mode
        self.servers = servers
        self.webui = webui
        self.datacenter = datacenter or 'dc1'
        self.encrypt = encrypt
        self.bootstrap_expect = bootstrap_expect

    def packages(self):
        return ['unzip']

    def main(self, context):
        context.user('consul', home='/var/consul', home_mode='750')
        self._acquire_consul(context)
        if self.webui:
            self._acquire_webui(context)

        if self.mode == 'server':
            config_json = self._server_config()
        else:
            config_json = self._client_config()

        context.file('/etc/consul.d/config.json',
                     owner='root', group='consul', mode='640',
                     json_data=config_json, triggers='consul')
        context.file('/etc/init/consul.conf',
                     data=self._upstart_conf(), triggers='consul-restart')

        context.shell('service consul restart', triggered_by='consul-restart')
        context.shell('service consul reload', triggered_by='consul')

    def _acquire_consul(self, context):
        is_new = context.download('/opt/consul/0.4.1/consul.zip',
                                  'https://dl.bintray.com/mitchellh/consul/0.4.1_linux_amd64.zip',
                                  sha256sum='2cf6e59edf348c3094c721eb77436e8c789afa2c35e6e3123a804edfeb1744ac')
        if is_new:
            context.cmd(['unzip', '/opt/consul/0.4.1/consul.zip', '-d', '/opt/consul/0.4.1/'], quiet=True)

    def _acquire_webui(self, context):
        context.mkdir('/opt/consul/0.4.1/web', owner='consul', group='consul')
        ui_is_new = context.download('/opt/consul/0.4.1/web/web.zip',
                                     'https://dl.bintray.com/mitchellh/consul/0.4.1_web_ui.zip',
                                     sha256sum='e02929ed44f5392cadd5513bdc60b7ab7363d1670d59e64d2422123229962fa0')
        if ui_is_new:
            context.cmd(['unzip', '/opt/consul/0.4.1/web/web.zip', '-d', '/opt/consul/0.4.1/web/'], quiet=True)

    def _common_config(self):
        d = {'datacenter':self.datacenter,
             'data_dir':'/var/consul',
             'log_level':'INFO', 'enable_syslog':True}
        if self.encrypt is not None:
            d['encrypt'] = encrypt
        if self.webui:
            d["ui_dir"] = "/opt/consul/0.4.1/web/dist"
            d["client_addr"] = "127.0.0.1"
            d["addresses"] = {
                "dns": "127.0.0.1",
                "http": "0.0.0.0",
                "rpc": "127.0.0.1"
            }
        if self.servers:
            # TODO: check if we need to eliminate ourselves from the list?
            d["start_join"] = self.servers
        return d

    def _server_config(self):
        d = self._common_config()
        d['bootstrap_expect'] = self.bootstrap_expect
        d['server'] = True
        return d

    def _client_config(self):
        d = self._server_config()
        d['server'] = False
        return d

    def _upstart_conf(self):
        s = ''
        s += 'description "Consul %s process"\n\n' % self.mode
        s += 'start on (local-filesystems and net-device-up IFACE=eth0)\n'
        s += 'stop on runlevel [!12345]\n\n'
        s += 'respawn\n\n'
        s += 'setuid consul\nsetgid consul\n\n'
        s += 'exec /opt/consul/0.4.1/consul agent -config-dir /etc/consul.d\n'
        return s
