
import json
import time

import boto
import boto.ec2
import boto.iam
import boto.utils
import consul

from .action_module import ActionModule

class Aws(ActionModule):

    def __init__(self, context=None, region=None, ec2=None, iam=None, in_ec2=False):
        self.context = context
        self.in_ec2 = in_ec2
        self.ec2 = ec2
        self.iam = iam
        self.meta = {}
        self.region = region
        self._connect()

    def _connect(self):
        if self.in_ec2:
            self.meta = boto.utils.get_instance_metadata()
        if self.region is None:
            if self.in_ec2:
                self.region = self.meta['hostname'].split('.')[1]
            else:
                self.region = 'us-west-2'

        self.ec2 = self.ec2 or boto.ec2.connect_to_region(self.region)
        self.iam = self.iam or boto.connect_iam()
        assert self.ec2
        assert self.iam

    def iam_role_and_profile(self, name):
        self.iam_role(name)
        self.instance_profile(name, name)

    def iam_role(self, name, policy_name='managedpolicy', policy_data={}):
        if type(policy_data) != str:
            policy_data = json.dumps(policy_data, sort_keys=True, indent=4, separators=(',', ': '))
        try: role = self.iam.get_role(name)
        except boto.exception.BotoServerError: role = None
        if role is None:
            self.iam.create_role(name)
            time.sleep(1)
            role = self.iam.get_role(name)
        # ...someday, maybe support for multiple policies via iam.list_role_policies()
        self.iam.put_role_policy(name, policy_name, policy_data)

    def instance_profile(self, name, role_name=None):
        '''
        If role_name is None, ensure the instance profile has no role
        associated with it, otherwise, the appropriate role.
        '''
        try: profile = self.iam.get_instance_profile(name)
        except boto.exception.BotoServerError: profile = None
        if profile is None:
            self.iam.create_instance_profile(name)
            time.sleep(1)
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
        try: group = self.ec2.get_all_security_groups(groupnames=[name])[0]
        except boto.exception.EC2ResponseError: group = None
        if group is None:
            self.ec2.create_security_group(name, description)
            group = self.ec2.get_all_security_groups(groupnames=[name])[0]
            return True
        # TODO: permissions on group? Or maybe have that separately?
        return False

    def _get_security_group(self, name):
        return self.ec2.get_all_security_groups(groupnames=[name])[0]

    def _security_group_id(self, name):
        return self._get_security_group(name).id

    def launch_instance(self, name, security_groups, iam_role=None, **kwargs):
        insts = self._get_instances()
        if len([i for i in insts if i.tags.get('Name') == name and i.state != 'terminated']) > 0:
            raise Exception('An instance with the name "%s" already exists!' % (name))
        if type(security_groups) == str:
            security_groups = [security_groups]
        security_group_ids = []
        for sg in security_groups:
            if len(sg) == 11 and sg[:3] == 'sg-':
                security_group_ids.append(sg)
            else:
                security_group_ids.append(self._security_group_id(sg))
        kwargs['security_group_ids'] = security_group_ids
        kwargs['min_count'] = kwargs.get('min_count', 1)
        kwargs['max_count'] = kwargs.get('max_count', 1)
        if iam_role is not None:
            kwargs['instance_profile_name'] = iam_role
        kwargs['image_id'] = kwargs.get('image_id', 'ami-870a2fb7')

        reservation = self.ec2.run_instances(**kwargs)
        # TODO: loop 'til the instances are available in the api, due to eventual consistency?
        self.ec2.create_tags([inst.id for inst in reservation.instances],
                        {'Name': name})
        return True

    def _get_instances(self):
        return reduce(lambda a, b: a + b, [a.instances for a in self.ec2.get_all_reservations()], [])
