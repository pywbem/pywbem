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

"""
Definition of the package version, and check for supported Python versions.
"""

from ._version_scm import version, version_tuple

__all__ = ['__version__', '__version_tuple__']

#: The full version of this package including any development levels, as a
#: :term:`string`.
#:
#: Possible formats for this version string are:
#:
#: * "M.N.Pa1.dev7+g1234567": A not yet released version M.N.P
#: * "M.N.P": A released version M.N.P
__version__ = version

#: The full version of this package including any development levels, as a
#: tuple of version items, converted to integer where possible.
#:
#: Possible formats for this version string are:
#:
#: * (M, N, P, 'a1', 'dev7', 'g1234567'): A not yet released version M.N.P
#: * (M, N, P): A released version M.N.P
__version_tuple__ = version_tuple
