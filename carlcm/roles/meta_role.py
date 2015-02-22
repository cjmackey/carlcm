
class MetaRole(object):
    name = 'metarole'

    min_count = 1
    max_count = 1

    def __init__(self, environment_name):
        self.environment_name = environment_name

    def gather_information(self):
        '''
        Gathers information about the role from the Consul servers.
        Used before running cluster().
        '''
        return

    def cluster(self, context):
        '''
        Set up and/or maintain the cluster of instances/containers/whatever.
        '''
        return

    def main(self, context):
        '''
        Code that runs on the machine to set up the role.
        '''
        return
