#!/usr/bin/env python

import os
import sys


module_name = sys.argv[1]
environment_name = sys.argv[2]
print module_name
carlcm_dir = os.path.realpath(os.path.join(os.path.dirname(os.path.realpath(__file__)), '..'))
sys.path.insert(0, carlcm_dir)
print sys.path

__import__(module_name)
py_module = sys.modules[module_name]
name = py_module.__name__.split('.')[-1]
classname = ''.join([a.capitalize() for a in name.split('_')])
role = py_module.__getattribute__(classname)(environment_name)

import carlcm

context = carlcm.Context()

role.main(context)
