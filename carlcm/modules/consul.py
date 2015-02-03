'''

Installs Consul.

If webui is True, it will enable the web ui, visible at 'http://localhost:8500/ui'

'''

from .base import BaseModule

# TODO: tls
# https://www.digitalocean.com/community/tutorials/how-to-secure-consul-with-tls-encryption-on-ubuntu-14-04

class ConsulModule(BaseModule):

    def __init__(self, encrypt, mode='client', servers=None, webui=False,
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
        context.user('consul', home='/var/consul', random_password=True)
        self._acquire_consul(context)
        if self.webui:
            self._acquire_webui(context)

        context.file('/etc/consul.d/server/config.json',
                     src_data=self._server_config(), triggers='consul')
        context.file('/etc/consul.d/client/config.json',
                     src_data=self._client_config(), triggers='consul')
        context.file('/etc/init/consul.conf',
                     src_data=self._upstart_conf(), triggers='consul')

        context.shell('service consul restart', triggered_by='consul')

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

    def _server_config(self):
        d = {'server':True, 'datacenter':self.datacenter,
             'data_dir':'/var/consul', 'encrypt': self.encrypt,
             'log_level':'INFO', 'enable_syslog':True,
             'bootstrap_expect': self.bootstrap_expect}
        if self.webui:
            d["ui_dir"] = "/opt/consul/0.4.1/web/dist"
        if self.servers:
            # TODO: check if we need to eliminate ourselves from the list?
            d["start_join"] = self.servers
        return d

    def _client_config(self):
        d = self._server_config()
        del d['bootstrap_expect']
        d['server'] = False
        return d

    def _upstart_conf(self):
        s = ''
        s += 'description "Consul %s process"\n\n' % self.mode
        s += 'start on (local-filesystems and net-device-up IFACE=eth0)\n'
        s += 'stop on runlevel [!12345]\n\n'
        s += 'respawn\n\n'
        s += 'setuid consul\nsetgid consul\n\n'
        s += 'exec /opt/consul/0.4.1/consul agent -config-dir /etc/consul.d/%s\n' % self.mode
        return s
