#!/bin env python

import sys
import subprocess

print('Removing pbr package on Python 2.6 if installed, see pywbem issue #26')
if sys.version_info[0:2] == (2,6):
    try:
        import pbr
        print('Removing installed pbr package on this Python 2.6')
        print('pip uninstall -y pbr')
        rc = subprocess.call(['pip', 'uninstall', '-y', 'pbr'])
    except ImportError:
        print('pbr package is not installed on this Python 2.6')
else:
    print('Not changing pbr package on this Python %s.%s' %\
          (sys.version_info[0], sys.version_info[1]))

