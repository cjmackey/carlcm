
from .instance_role import InstanceRole

class Example(InstanceRole):

    def main(self, context):
        super(Example, self).main(context)
        context.package('nginx')
        context.mkdir('/usr/share/nginx/html')
        context.file('/etc/nginx/sites-available/default', src_data='''
server {
        listen   80 default;
        server_name  localhost;

        location / {
                root   /usr/share/nginx/html;
                index  index.html index.htm;
        }
}
''', triggers='nginx')
        context.file('/usr/share/nginx/html/index.html', src_data='''
<html>
<body>
Hello World!
</body>
</html>
''')
        context.cmd(['service', 'nginx', 'reload'], triggered_by='nginx')
        return
