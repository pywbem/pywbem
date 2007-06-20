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

args = {'name': 'pywbem',
        'author': 'Tim Potter',
        'author_email': 'tpot@hp.com',
        'description': 'Python WBEM client library',
        'long_description': __doc__,
        'platforms': ['any'],
        'url': 'http://pywbem.sf.net/',
        'version': '0.5.20070612.1',
        'license': 'LGPL',
        'packages': ['pywbem'],
        # Make packages in root dir appear in pywbem module
        'package_dir': {'pywbem': ''}, 
        # Make extensions in root dir appear in pywbem module
        'ext_package': 'pywbem',
        }

setup(**args)
