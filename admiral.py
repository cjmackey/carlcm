
import json
import os

import boto
import boto.ec2
import boto.iam


region = 'us-west-2'

policies = {
    'counselor': {
        "Statement":[{
            "Effect":"Allow",
            "Action":["s3:*", "ec2:*"],
            "Resource":["*"]}]
    }
}

ec2 = boto.ec2.connect_to_region(region)
iam = boto.connect_iam()

def role_and_profile(name):
    iam_role(name)
    instance_profile(name, name)

def iam_role(name, policy_name='managedpolicy'):
    policy = json.dumps(policies[name], sort_keys=True, indent=4, separators=(',', ': '))
    try: role = iam.get_role(name)
    except boto.exception.BotoServerError: role = None
    if role is None:
        iam.create_role(name)
        role = iam.get_role(name)
    # ...someday, maybe support for multiple policies via iam.list_role_policies()
    iam.put_role_policy(name, policy_name, policy)

def instance_profile(name, role_name=None):
    try: profile = iam.get_instance_profile(name)
    except boto.exception.BotoServerError: profile = None
    if profile is None:
        iam.create_instance_profile(name)
        profile = iam.get_instance_profile(name)
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
        iam.remove_role_from_instance_profile(name, roles['member']['role_name'])
    if should_add:
        iam.add_role_to_instance_profile(name, role_name)

    if role_name is not None and len(roles) != 0:
        should_add = True

def security_group(name, description):
    try: group = ec2.get_all_security_groups(groupnames=[name])[0]
    except boto.exception.EC2ResponseError: group = None
    if group is None:
        ec2.create_security_group(name, description)
        group = ec2.get_all_security_groups(groupnames=[name])[0]
    return group
'''
# ubuntu 14.04 cloudinit http://cloud-images.ubuntu.com/releases/14.04/release-20150209.1/
ec2.run_instances(image_id='ami-870a2fb7', key_name='carl-ssh-2015-02-14', user_data='#!/bin/bash\nsudo apt-get update\nsudo apt-get install -y python-dev python-setuptools\nsudo easy_install pip\nsudo pip install boto\nsudo pip install carlcm\n/usr/local/bin/carlcm-counselor 3', security_group_ids=['sg-233a1f46', 'sg-c03a1fa5'], subnet_id='subnet-7af8590d', instance_type='t2.micro', instance_profile_name='counselor')
'''

def get_instances():
    return reduce(lambda a, b: a + b, [a.instances for a in ec2.get_all_reservations()], [])

def ensure_council():
    count = 3
    g1 = security_group('counselor', 'Security Group for Council').id
    g2 = security_group('counseled', 'Security Group for Instances Following to Council').id
    role_and_profile('counselor')
    insts = get_instances()
    counselors = [i for i in insts if 'counselor' in [g.name for g in i.groups]]
    counselors = [i for i in counselors if i.state in ['running', 'pending']]
    is_bootstrap = (len(counselors) == 0)
    user_data = '''#!/bin/bash
sudo apt-get update
sudo apt-get install -y python-dev python-setuptools
sudo easy_install pip
sudo pip install boto
sudo pip install carlcm
sudo /usr/local/bin/carlcm-counselor 3'''
    if is_bootstrap:
        user_data += ' bootstrap'
    user_data += '\n\n'
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
        ec2.run_instances(**d)
    return

if __name__ == '__main__':
    #role_and_profile('counselor')
    #security_group('counselor', 'Security Group for Counselor')
    #security_group('counseled', 'Security Group for Instances in the Cluster')
    security_group('natvpn', 'Security Group for NAT/VPN Instances')
    ensure_council()
