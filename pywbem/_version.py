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

# There are submodules, but clients shouldn't need to know about them.
# Importing just this module is enough.
# These are explicitly safe for 'import *'

"""
Version of the pywbem package.
"""

import sys


#: Version of the pywbem package, as a :term:`string`.
#:
#: Possible formats for the version string are:
#:
#: * "M.N.U.dev0": During development of future M.N.U release (not released to
#:   PyPI)
#: * "M.N.U.rcX": Release candidate X of future M.N.U release (not released to
#:   PyPI)
#: * "M.N.U": The final M.N.U release
__version__ = '0.12.0.dev0'

# Check supported Python versions
_PYTHON_M = sys.version_info[0]
_PYTHON_N = sys.version_info[1]
if _PYTHON_M == 2 and _PYTHON_N < 6:
    raise RuntimeError('On Python 2, pywbem requires Python 2.6 or higher')
elif _PYTHON_M == 3 and _PYTHON_N < 4:
    raise RuntimeError('On Python 3, pywbem requires Python 3.4 or higher')
