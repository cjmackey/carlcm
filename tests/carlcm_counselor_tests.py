
import json

from nose.tools import *
from mock import Mock, MagicMock, call
#from moto import mock_ec2, mock_iam, mock_s3

import carlcm

c = None

class TestCounselor(object):

    def setup(self):
        global c
        c = carlcm.Counselor(ec2=Mock(), iam=Mock())

    #@mock_ec2
    #@mock_iam
    #@mock_s3
    def test_ensure_local(self):
        c.get_instances = Mock(return_value=[])

        context = carlcm.MockContext()
        context.packages = Mock()
        context.download = Mock()
        c.ensure_local(context=context)

    def test_iam_role_exists(self):
        c.iam.get_role = Mock(return_value=True)
        c.iam.put_role_policy = Mock()
        c.iam_role('counselor')
        policy = json.dumps(c.policies['counselor'], sort_keys=True, indent=4, separators=(',', ': '))

        c.iam.put_role_policy.assert_has_calls([call('counselor', 'managedpolicy', policy)])
