#!/bin/bash

# time vagrant up

# time vagrant ssh -c 'sudo apt-get update'

time vagrant ssh -c 'sudo rm -rf /opt/carlcm && sudo cp -r /vagrant /opt/carlcm && ls /opt/carlcm && cd /opt/carlcm && sudo apt-get install -y python-pip python-dev && sudo pip install nose && sudo pip install jinja2 && sudo pip install mock && sudo pip install coverage && sudo python setup.py install && sudo bin/test.sh && sudo nosetests tests/local-integration.py && sudo python tests/local-modules.py'
