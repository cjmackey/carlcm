
from .base import BaseModule

class ExampleModule(BaseModule):

    def packages(self):
        return ['htop', 'dtrx', 'ack-grep']

    def main(self, context):
        context.user('carl')
        context.file('/home/carl/example.txt', src_data='hello carl\n',
                     owner='carl', group='carl')
