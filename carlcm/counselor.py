
import json
import os
import subprocess
import time

class Counselor(object):

    def __init__(self, region=None, ec2=None, iam=None, in_ec2=False):
        import boto
        import boto.ec2
        import boto.iam
        import consul

        if in_ec2:
            import boto.utils
            self.meta = boto.utils.get_instance_metadata()
        if region is None:
            if in_ec2:
                self.region = self.meta['hostname'].split('.')[1]
            else:
                self.region = 'us-west-2'
        else:
            self.region = region

        self.policies = {
            'counselor': {
                "Statement":[{
                    "Effect":"Allow",
                    "Action":["s3:*", "ec2:*"],
                "Resource":["*"]}]
            }
        }
        self.ec2 = ec2 or boto.ec2.connect_to_region(self.region)
        self.iam = iam or boto.connect_iam()
        assert self.ec2
        assert self.iam

    def role_and_profile(self, name):
        self.iam_role(name)
        self.instance_profile(name, name)

    def iam_role(self, name, policy_name='managedpolicy'):
        import boto
        policy = json.dumps(self.policies[name], sort_keys=True, indent=4, separators=(',', ': '))
        try: role = self.iam.get_role(name)
        except boto.exception.BotoServerError: role = None
        if role is None:
            self.iam.create_role(name)
            role = self.iam.get_role(name)
        # ...someday, maybe support for multiple policies via iam.list_role_policies()
        self.iam.put_role_policy(name, policy_name, policy)

    def instance_profile(self, name, role_name=None):
        import boto
        try: profile = self.iam.get_instance_profile(name)
        except boto.exception.BotoServerError: profile = None
        if profile is None:
            self.iam.create_instance_profile(name)
            profile = self.iam.get_instance_profile(name)
        roles = profile['get_instance_profile_response']['get_instance_profile_result']['instance_profile']['roles']
        should_add = False
        should_remove = False
        if role_name is None:
            if len(roles) != 0:
                should_remove = True
        if role_name is not None:
            if len(roles) == 0:
                should_add = True
            elif roles['member']['role_name'] != role_name:
                should_remove = True
                should_add = True
        if should_remove:
            self.iam.remove_role_from_instance_profile(name, roles['member']['role_name'])
        if should_add:
            self.iam.add_role_to_instance_profile(name, role_name)

        if role_name is not None and len(roles) != 0:
            should_add = True

    def security_group(self, name, description):
        import boto
        try: group = self.ec2.get_all_security_groups(groupnames=[name])[0]
        except boto.exception.EC2ResponseError: group = None
        if group is None:
            self.ec2.create_security_group(name, description)
            group = self.ec2.get_all_security_groups(groupnames=[name])[0]
        return group

    def get_instances(self):
        return reduce(lambda a, b: a + b, [a.instances for a in self.ec2.get_all_reservations()], [])

    def ensure_council(self):
        count = 3
        g1 = self.security_group('counselor', 'Security Group for Council').id
        g2 = self.security_group('counseled', 'Security Group for Instances Following to Council').id
        self.role_and_profile('counselor')
        insts = self.get_instances()
        counselors = [i for i in insts if 'counselor' in [g.name for g in i.groups]]
        counselors = [i for i in counselors if i.state in ['running', 'pending']]
        is_bootstrap = (len(counselors) == 0)
        user_data = '''#!/bin/bash
sudo apt-get update
sudo apt-get install -y python-dev python-setuptools
sudo easy_install pip
sudo pip install boto
sudo pip install python-consul
sudo pip install carlcm
sudo /usr/local/bin/carlcm-counselor %i''' % (count)
        if is_bootstrap:
            user_data += ' bootstrap'
        user_data += '\n'
        num_to_launch = count - len(counselors)
        d = {
            'image_id': 'ami-870a2fb7',
            'key_name': 'carl-ssh-2015-02-14',
            'user_data': user_data,
            'security_group_ids': [g1, g2],
            'subnet_id': 'subnet-7af8590d',
            'instance_type': 't2.micro',
            'instance_profile_name': 'counselor',
            'min_count': num_to_launch,
            'max_count': num_to_launch,
        }
        if num_to_launch > 0:
            self.ec2.run_instances(**d)
        return

    def ensure_local(self, count=1, is_bootstrap=False, context=None):
        from .configuration_manager import ConfigurationManager
        from .modules import ConsulModule

        is_bootstrap = (is_bootstrap is True or is_bootstrap == 'bootstrap')

        instances = self.get_instances()

        counselors = [i for i in instances if 'counselor' in [g.name for g in i.groups]]
        counselors = [i for i in counselors if i.state in ['running', 'pending']]
        counselors = [i for i in counselors if i.private_ip_address != self.meta['local-ipv4']]
        counselor_ips = sorted([i.private_ip_address for i in counselors if i.private_ip_address])

        if is_bootstrap and all([self.meta['local-ipv4'] < ip for ip in counselor_ips]):
            counselor_ips = None

        c = ConfigurationManager()
        if context is not None:
            c = context

        c.add_modules(ConsulModule(mode='server', webui=True, bootstrap_expect=count, servers=counselor_ips))

        c.run_modules()

        if is_bootstrap:
            for i in xrange(100):
                time.sleep(5)
                try: subprocess.check_output(['service', 'consul', 'start'])
                except: pass
