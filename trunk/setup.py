'''A pure-Python library for performing operations using the WBEM
management protocol.'''

#
# (C) Copyright 2004 Hewlett-Packard Development Company, L.P.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as
# published by the Free Software Foundation; either version 2 of the
# License, or (at your option) any later version.
#   
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#   
# You should have received a copy of the GNU Lesser General Public
# License along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
#

# Author: Tim Potter <tpot@hp.com>

from distutils.core import setup, Extension
import sys, string, os
import shutil

for file in ['pywbem.mofparsetab.py', 'mofparsetab.py', 'mofparsetab.pyc',
             'pywbem.moflextab.py', 'moflextab.py', 'moflextab.py']:
    try:
        os.unlink(file)
    except OSError:
        pass

import mof_compiler
mof_compiler._build()
shutil.move('pywbem.mofparsetab.py', 'mofparsetab.py')
shutil.move('pywbem.moflextab.py', 'moflextab.py')

args = {'name': 'pywbem',
        'author': 'Tim Potter',
        'author_email': 'tpot@hp.com',
        'description': 'Python WBEM client library',
        'long_description': __doc__,
        'platforms': ['any'],
        'url': 'http://pywbem.sf.net/',
        'version': '0.6.20080204.1',
        'license': 'LGPLv2',
        'packages': ['pywbem'],
        # Make packages in root dir appear in pywbem module
        'package_dir': {'pywbem': ''}, 
        # Make extensions in root dir appear in pywbem module
        'ext_package': 'pywbem',
        }

setup(**args)
