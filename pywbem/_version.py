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

Note: The package version is not defined here, but determined dynamically by
the `pbr` package from Git information.
"""

import sys
import pbr.version

__all__ = ['__version__']

#: The full version of this package including any development levels, as a
#: :term:`string`.
#:
#: Possible formats for this version string are:
#:
#: * "M.N.P.devD": Development level D of a not yet released assumed M.N.P
#:   version
#: * "M.N.P": A released M.N.P version
__version__ = pbr.version.VersionInfo('pywbem').release_string()

# Check supported Python versions
_PYTHON_M = sys.version_info[0]
_PYTHON_N = sys.version_info[1]
if _PYTHON_M == 2 and _PYTHON_N < 6:
    raise RuntimeError('On Python 2, pywbem requires Python 2.6 or higher')
elif _PYTHON_M == 3 and _PYTHON_N < 4:
    raise RuntimeError('On Python 3, pywbem requires Python 3.4 or higher')
