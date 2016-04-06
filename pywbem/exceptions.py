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
The following exceptions are pywbem specific exceptions that can be raised at
the WBEM client library API.
"""

# This module is meant to be safe for 'import *'.

__all__ = ['Error', 'ConnectionError', 'AuthError', 'TimeoutError',
           'ParseError', 'CIMError']

class Error(Exception):
    """Base class for pywbem specific exceptions."""
    pass

class ConnectionError(Error):
    """This exception indicates a problem with the connection to the WBEM
    server. A retry may or may not succeed. Derived from
    :exc:`~pywbem.Error`."""
    pass

class AuthError(Error):
    """This exception indicates an authentication error with the WBEM server.
    Derived from :exc:`~pywbem.Error`."""
    pass

class TimeoutError(Error):
    """This exception indicates that the client timed out waiting for the WBEM
    server. Derived from :exc:`~pywbem.Error`."""
    pass

class ParseError(Error):
    """This exception indicates a parsing error with the CIM-XML response
    returned by the WBEM server. Derived from :exc:`~pywbem.Error`."""
    pass

class CIMError(Error):
    """
    This exception indicates that the WBEM server returned an error response
    with a CIM status code. Derived from :exc:`~pywbem.Error`.

    The exception value is a `tuple(error_code, description, exception_obj)`,
    with:

      * error_code (number):
        Numeric CIM status code.
        See :ref:`CIM status codes` for constants defining the numeric CIM
        status code values.

      * description (:term:`unicode string` or :term:`byte string`):
        CIM status description text returned by the server, representing a
        human readable message describing the error.

      * exception_obj (exception):
        The underlying exception object that caused this exception to be
        raised, or `None`. Will always be `None`, currently.
    """
    pass

