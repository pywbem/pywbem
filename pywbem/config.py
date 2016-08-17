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
Pywbem supports a very limited number of configuration variables that influence
certain specific behavior.

These configuration variables are read by pywbem only after its modules have
been loaded, so they can be modified by the user directly after importing
pywbem. For example:

::

    import pywbem
    pywbem.ENFORCE_INTEGER_RANGE = False

Note that the source file defining these variables should not be changed by the
user. Instead, use the technique described above to modify the configuration
variables.

Note: Due to limitations of the documentatin tooling, the following
configuration variables are shown in the ``pywbem.config`` namespace. However,
they should be used from the ``pywbem`` namespace.
"""

# This module is meant to be safe for 'import *'.

__all__ = ['ENFORCE_INTEGER_RANGE']

#: Enforce the value range in CIM integer types (e.g. :class:`~pywbem.Uint8`).
#: For details, see the :class:`~pywbem.CIMInt` base class.
#:
#: * True (default): Enforce the value range; Assigning values out of range
#:   causes :exc:`~py:exceptions.ValueError` to be raised.
#: * False: Do not enforce the value range; Assigning values out of range
#:   works.
ENFORCE_INTEGER_RANGE = True

