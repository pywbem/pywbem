'''A pure-Python library for performing operations using the WBEM
management protocol.'''

#
# (C) Copyright 2004 Hewlett-Packard Development Company, L.P.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as
# published by the Free Software Foundation; version 2 of the License.
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

import mof_compiler
mof_compiler._build()

# Get package version from __init__.py 
init_py = os.path.abspath(os.path.join(os.path.dirname(sys.argv[0]),
                                                       '__init__.py'))
execfile(init_py) # defines __version__

args = {'name': 'pywbem',
        'author': 'Tim Potter',
        'author_email': 'tpot@hp.com',
        'description': 'Python WBEM client library',
        'long_description': __doc__,
        'platforms': ['any'],
        'url': 'http://pywbem.sf.net/',
        'version': __version__,
        'license': 'LGPLv2',
        'packages': ['pywbem'],
        # Make packages in root dir appear in pywbem module
        'package_dir': {'pywbem': ''}, 
        # Make extensions in root dir appear in pywbem module
        'ext_package': 'pywbem',
        }

setup(**args)
