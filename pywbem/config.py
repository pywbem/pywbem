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

Note: Due to limitations of the documentation tooling, the following
configuration variables are shown in the ``pywbem.config`` namespace. However,
they should be used from the ``pywbem`` namespace.
"""

# This module is meant to be safe for 'import *'.

__all__ = ['ENFORCE_INTEGER_RANGE', 'DEFAULT_ITER_MAXOBJECTCOUNT',
           'SEND_VALUE_NULL']

#: Enforce the allowable value range for CIM integer types (e.g.
#: :class:`~pywbem.Uint8`). For details, see the :class:`~pywbem.CIMInt` base
#: class.
#:
#: * True (default): Pywbem enforces the allowable value range; Assigning
#:   values out of range causes :exc:`~py:exceptions.ValueError` to be raised.
#: * False: Pywbem does not enforce the allowable value range; Assigning values
#:   out of range works in pywbem. Note that a WBEM server may or may not
#:   reject such out-of-range values.
#:
#: *New in pywbem 0.9.*
ENFORCE_INTEGER_RANGE = True

#: Default setting for the MaxObjectCount attribute for all of the
#: :class:`~pywbem.WBEMConnection`:Iter... operations.
#: If this attribute is not specified on a request such as
#: :meth:`~pywbem.WBEMConnection.IterEnumerateInstances`, this value will be
#: used as the value for MaxObjectCount.
#: Note that this does not necessarily optimize the performance of these
#: operations.
#:
#: *New in pywbem 0.10 as experimental and finalized in 0.12.*
DEFAULT_ITER_MAXOBJECTCOUNT = 1000

#: Add a stack traceback to the message text of most warnings issued by pywbem.
#: This allows identifying which code originated the warning.
DEBUG_WARNING_ORIGIN = False

#: Backwards compatibility option controlling the use of `VALUE.NULL` for
#: representing NULL entries in array values in CIM-XML requests sent to WBEM
#: servers.
#:
#: :term:`DSP0201` requires the use of `VALUE.NULL` for representing NULL
#: entries in array values since its version 2.2 (released 01/2007). Pywbem
#: added support for using `VALUE.NULL` in CIM-XML requests in its version
#: 0.12. In case a WBEM server has not implemented support for `VALUE.NULL`,
#: this config option can be used to disable the use of `VALUE.NULL` as a
#: means for backwards compatibility with such WBEM servers.
#:
#: Note that the config option only influences the behavior of pywbem for
#: using `VALUE.NULL` in CIM-XML requests sent to a WBEM server. Regardless of
#: the config option, pywbem will always support `VALUE.NULL` in CIM-XML
#: responses the pywbem client receives from a WBEM server, and in CIM-XML
#: requests the pywbem listener receives from a WBEM server.
#:
#: * True (default): Pywbem uses `VALUE.NULL` in CIM-XML requests for
#:   representing NULL entries in array values.
#: * False: Pywbem uses `VALUE` with an empty value in CIM-XML requests for
#:   representing NULL entries in array values.
#:
#: *New in pywbem 0.12.*
SEND_VALUE_NULL = True
