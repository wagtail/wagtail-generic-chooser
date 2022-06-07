#!/usr/bin/env python

import os
import sys

from django.core.management import execute_from_command_line

os.environ['DJANGO_SETTINGS_MODULE'] = 'tests.settings'
execute_from_command_line([sys.argv[0], 'test'] + sys.argv[1:])
