
from ..internal_utils import *

from .meta_role import MetaRole

class InstanceRole(MetaRole):

    def name_base(self):
        return self.environment_name + '-' + camel_to_hyphen(self.__class__.__name__)

    def security_groups(self):
        return [self.name_base()]

    def iam_role(self):
        return self.name_base()

    def name(self, num):
        return self.name_base() + '-%04i' % num

    def user_data(self):
        return '''#!/bin/bash
sudo apt-get update
sudo apt-get install -y python-setuptools
sudo easy_install pip
sudo pip install carlcm
sudo carlcm-run-role '%s' '%s'
''' % (self.import_name(), self.environment_name)

    def instances(self, context):
        insts = context.aws._get_instances()
        sg = self.name_base()
        return [i for i in insts if sg in [g.name for g in i.groups]]

    def next_name(self, context, instances=None):
        instances = instances or self.instances(context)
        names = set([i.tags.get('Name') for i in instances])
        for i in xrange(1, 1000):
            if self.name(i) in names:
                continue
            return self.name(i)
        raise Exception('more than 1000 instances!')

    def launch_one(self, context):
        d = {
            'image_id': 'ami-870a2fb7',
            'key_name': 'carl-ssh-2015-02-14',
            'user_data': self.user_data(),
            'subnet_id': 'subnet-7af8590d',
            'instance_type': 't2.micro',
            'min_count': 1,
            'max_count': 1,
        }
        name = self.next_name(context)
        context.launch_instance(name, security_groups=self.security_groups(), iam_role=self.iam_role(), **d)

    def cluster(self, context):

        for sg in self.security_groups():
            context.security_group(sg, sg)

        if self.iam_role():
            context.iam_role_and_profile(self.iam_role())

        instances = self.instances(context)
        if len(instances) < self.min_count:
            for i in xrange(self.min_count - len(instances)):
                self.launch_one(context)

        return
