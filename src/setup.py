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

def import_setuptools(min_version="17.0"):
    """Import the `setuptools` package.

    If it is not previously installed, or if it is installed but does not have
    the at least the specified minimum version, it is downloaded from PyPI
    and installed into the current Python environment (system or virtual
    environment), replacing a possibly existing version.

    This function requires ez_setup.py to be in the current directory or ini
    the Python module path.

    As of 10/2014, this article is a good overview on the various distribution
    packages for Python: http://stackoverflow.com/a/14753678.

    Parameters:
    * min_version: (string) The minimum required version of `setuptools`,
      e.g. "17.0".
    """

    install_setuptools = False
    try:
        import setuptools    
    except ImportError:
        install_setuptools = True
    else:
        if setuptools.__version__.split(".") < min_version.split("."):
            install_setuptools = True

    if install_setuptools:
        # Download and install from PyPI
        import ez_setup
        ez_setup.use_setuptools(version=min_version)

    import setuptools    

import sys
import os
import_setuptools()
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

