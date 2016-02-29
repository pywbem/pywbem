#!/bin env python

import sys
import subprocess

if sys.version_info[0:2] == (2,6):
    print('Removing pbr package on Python 2.6 (see pywbem issue #26)')
    print('pip uninstall -y pbr')
    rc = subprocess.call(['pip', 'uninstall', '-y', 'pbr'])
else:
    print('Keeping pbr package on Python %s.%s (see pywbem issue #26)' %\
          (sys.version_info[0], sys.version_info[1]))
    rc = 0

sys.exit(rc)

