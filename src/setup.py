#
# (C) Copyright 2004 Hewlett-Packard Development Company, L.P.
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
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
#

"""
A pure-Python library for performing operations using the WBEM
management protocol.
"""

import sys
import os
from distutils.core import setup

# Build the lex/yacc table .py files
from pywbem import mof_compiler
mof_compiler._build()

# Get package version from __init__.py
init_py = os.path.abspath(os.path.join(
        os.path.dirname(sys.argv[0]), 'pywbem/__init__.py'))
init_globals = {}
execfile(init_py, init_globals) # defines __version__

args = {
    'name': 'pywbem',
    'author': 'Tim Potter',
    'author_email': 'tpot@hp.com',
    'description': 'Python WBEM client library',
    'long_description': __doc__,
    'platforms': ['any'],
    'url': 'http://sourceforge.net/projects/pywbem/',
    'version': init_globals['__version__'],
    'license': 'LGPLv2',
    'packages': ['pywbem'],
    'package_data': {
        'pywbem': [
            'docs/*',
            'NEWS',
            'LICENSE.txt',
        ]
    },
    'scripts': [
        'pywbem/wbemcli.py',
        'pywbem/mof_compiler.py',
    ],
    'classifiers' : [
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: GNU Lesser General Public License v2 or later (LGPLv2+)',
        'Operating System :: POSIX :: Linux',
        'Operating System :: Microsoft :: Windows',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Topic :: Software Development',
        'Topic :: System :: Systems Administration',
    ],
}

setup(**args)
