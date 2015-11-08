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

# Package version - Keep in sync with pywbem/__init__.py!
_version = '0.8.0-dev'

import sys
import os
# We use setuptools and make sure it is there:
try:
    import setuptools    
except ImportError:
    import ez_setup
    ez_setup.use_setuptools() # Download and install latest version from PyPI
    import setuptools    
from setuptools import setup

args = {
    'name': 'pywbem',
    'author': 'Tim Potter',
    'author_email': 'tpot@hp.com',
    'description': 'Python WBEM client library',
    'long_description': __doc__,
    'platforms': ['any'],
    'url': 'https://github.com/pywbem/pywbem',
    'version': _version,
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
    'install_requires': [
        # These dependencies will be installed as a site package.
        # They are not useable by this setup script, if they are eggs (because
        # their path is added to a .pth file which is parsed only at Python
        # startup time).
        #'M2Crypto>=0.22.6',
        'M2Crypto',
    ],
    # Temporary fix: Use our own fork of M2Crypto with fixes for installation issues.
    # This only seems to work if no version is specified in its install_requires entry.
    'dependency_links': [
        "git+https://github.com/pywbem/m2crypto@amfix2#egg=M2Crypto"
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

