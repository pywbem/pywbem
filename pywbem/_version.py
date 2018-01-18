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

# A note on the approach for importing pbr and invoking its VersionInfo():
# The documentation shows the __version__ variable defined below. For
# unknown reasons, the variable is not shown in the documentation when
# VersionInfo() is invoked without specifying a module path. Also, just
# importing pbr does not work because of the way the pbr package makes its
# submodules available.

import pbr.version


#: The full version of this package including any development levels, as a
#: :term:`string`.
#:
#: Possible formats for this version string are:
#:
#: * "M.N.P.devNNN": Development level NNN of a not yet released assumed M.N.P
#:   version
#: * "M.N.P": A released M.N.P version
__version__ = pbr.version.VersionInfo('pywbem').release_string()
