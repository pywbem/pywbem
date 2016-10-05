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

from .cim_constants import _statuscode2name, _statuscode2string

# This module is meant to be safe for 'import *'.

__all__ = ['Error', 'ConnectionError', 'AuthError', 'HTTPError', 'TimeoutError',
           'VersionError', 'ParseError', 'CIMError']


class Error(Exception):
    """Base class for pywbem specific exceptions."""
    pass


class ConnectionError(Error):
    """This exception indicates a problem with the connection to the WBEM
    server. A retry may or may not succeed. Derived from
    :exc:`~pywbem.Error`."""
    pass


class AuthError(Error):
    """This exception indicates an authentication error with the WBEM server,
    either during TLS/SSL handshake, or during HTTP-level authentication.
    Derived from :exc:`~pywbem.Error`."""
    pass


class HTTPError(Error):
    """
    This exception indicates that the WBEM server returned an HTTP response
    with a bad HTTP status code. Derived from :exc:`~pywbem.Error`.

    The `args` instance variable is a `tuple(status, reason, cimerror,
    cimdetails)`.

    The `message` instance variable is not set.
    """

    # pylint: disable=super-init-not-called
    def __init__(self, status, reason, cimerror=None, cimdetails=None):
        """
        Parameters:

          status (:term:`number`): HTTP status code (e.g. 500).

          reason (:term:`string`): HTTP reason phrase (e.g.
            'Internal Server Error').

          cimerror (:term:`string`): Value of the `CIMError` header field,
            if present. `None`, otherwise.

          cimdetails (dict): Dictionary with CIMOM-specific header
            fields with details about the situation reported in the `CIMError`
            header field.

            * Key: header field name (e.g. `PGErrorDetail`)
            * Value: header field value (i.e. text message)

            Passing `None` will result in an empty dictionary.
        """
        if cimdetails is None:
            cimdetails = {}
        self.args = (status, reason, cimerror, cimdetails)

    @property
    def status(self):
        """HTTP status code (e.g. 500), as a :term:`number`.

        See :term:`RFC2616` for a list of HTTP status codes and reason phrases.
        """
        return self.args[0]

    @property
    def reason(self):
        """HTTP reason phrase (e.g. 'Internal Server Error'), as a
        :term:`string`.

        See :term:`RFC2616` for a list of HTTP status codes and reason phrases.
        """
        return self.args[1]

    @property
    def cimerror(self):
        """Value of `CIMError` header field in response, if present, as a
        :term:`string`. `None`, otherwise.

        See :term:`DSP0200` for a list of values.
        """
        return self.args[2]

    @property
    def cimdetails(self):
        """CIMOM-specific details on the situation reported in the `CIMError`
        header field, as a dictionary:

        * Key: header field name (e.g. `PGErrorDetail`).
        * Value: header field value.
        """
        return self.args[3]

    def __str__(self):
        ret_str = "%s (%s)" % (self.status, self.reason)
        if self.cimerror is not None:
            ret_str += ", CIMError: %s" % self.cimerror
        for key in self.cimdetails:
            ret_str += ", %s: %s" % (key, self.cimdetails[key])
        return ret_str


class TimeoutError(Error):
    """This exception indicates that the client timed out waiting for the WBEM
    server. Derived from :exc:`~pywbem.Error`."""
    pass


class ParseError(Error):
    """This exception indicates a parsing error with the CIM-XML response
    returned by the WBEM server, or in the CIM-XML request sent by the WBEM
    listener. Derived from :exc:`~pywbem.Error`."""
    pass


class VersionError(Error):
    """This exception indicates an unsupported CIM, DTD or protocol version
    with the CIM-XML response returned by the WBEM server, or in the CIM-XML
    request sent by the WBEM listener. Derived from :exc:`~pywbem.Error`."""
    pass


class CIMError(Error):
    """
    This exception indicates that the WBEM server returned an error response
    with a CIM status code. Derived from :exc:`~pywbem.Error`.

    In Python 2, any :class:`py:Exception` object can be accessed by index
    and slice and will delegate such access to its :attr:`Exception.args`
    instance variable. In Python 3, that ability has been removed.

    In its version 0.9, pywbem has added the
    :attr:`~pywbem.CIMError.status_code` and
    :attr:`~pywbem.CIMError.status_description` properties.

    With all these variations, the following approach for accessesing the CIM
    status code a :class:`CIMError` object works for all pywbem versions since
    0.7.0 and for Python 2 and 3::

        except CIMError as exc:
            status_code = exc.args[0]

    The following approach is recommended when using pywbem 0.9 or newer, and
    it works for Python 2 and 3::

        except CIMError as exc:
            status_code = exc.status_code

    The following approach is limited to Python 2 and will not work on
    Python 3, and is therefore not recommended::

        except CIMError as exc:
            status_code = exc[0]
    """

    # pylint: disable=super-init-not-called
    def __init__(self, status_code, status_description=None):
        """
        Parameters:

          status_code (number): Numeric CIM status code.

          status_description (:term:`string`): CIM status description text
            returned by the server, representing a human readable message
            describing the error. `None`, if the server did not return
            a description text.

        :ivar args: A tuple(status_code, status_description) set from the
              corresponding init arguments.
        """
        self.args = (status_code, status_description)

    @property
    def status_code(self):
        """Numeric CIM status code.

        See :ref:`CIM status codes` for constants defining the numeric CIM
        status code values."""
        return self.args[0]

    @property
    def status_code_name(self):
        """Symbolic name of the CIM status code.

        If the CIM status code is invalid, the string
        ``"Invalid status code <code>"`` is returned."""
        return _statuscode2name(self.status_code)

    @property
    def status_description(self):
        """CIM status description text returned by the server, representing a
        human readable message describing the error.

        If the server did not return a description, a short default text for
        the CIM status code is returned. If the CIM status code is invalid,
        the string ``"Invalid status code <code>"`` is returned.

        Note that ``args[1]`` is always the ``status_description`` init
        argument, without defaulting it to a standard text in case of `None`.
        """
        return self.args[1] or _statuscode2string(self.status_code)

    def __str__(self):
        return "%s: %s" % (self.status_code, self.status_description)
