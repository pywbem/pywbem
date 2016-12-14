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

Note that the pywbem source file defining these variables should not be changed
by the user. Instead, the technique shown in the example above should be used to
modify the configuration variables.

Note: Due to limitations of the documentatin tooling, the following
configuration variables are shown in the ``pywbem.config`` namespace. However,
they should be used from the ``pywbem`` namespace.
"""

# This module is meant to be safe for 'import *'.

__all__ = ['ENFORCE_INTEGER_RANGE', 'DEFAULT_ITER_MAXOBJECTCOUNT']

#: Enforce the allowable value range for CIM integer types (e.g.
#: :class:`~pywbem.Uint8`). For details, see the :class:`~pywbem.CIMInt` base
#: class.
#:
#: * True (default): Pywbem enforces the allowable value range; Assigning
#:   values out of range causes :exc:`~py:exceptions.ValueError` to be raised.
#: * False: Pywbem does not enforce the allowable value range; Assigning values
#:   out of range works in pywbem. Note that a WBEM server may or may not
#:   reject such out-of-range values.
ENFORCE_INTEGER_RANGE = True

#: Default setting for the MaxObjectCount attribute for all of the
#: WBEMConnection:Iter... operations.
#: If this attribute is not specified on a request such as
#: IterEnumerateInstance this value will be used as the value for
#: MaxObjectCount.
#: Note that this does not necessarily optimize the performance of these
#: operations.

DEFAULT_ITER_MAXOBJECTCOUNT = 1000
