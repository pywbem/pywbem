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

from ._cim_constants import _statuscode2name, _statuscode2string

# This module is meant to be safe for 'import *'.

__all__ = ['Error', 'ConnectionError', 'AuthError', 'HTTPError', 'TimeoutError',
           'VersionError', 'ParseError', 'CIMXMLParseError', 'XMLParseError',
           'CIMError', 'ModelError']


class Error(Exception):
    """
    Base class for pywbem specific exceptions.
    """

    def __init__(self, *args, **kwargs):
        """
        Parameters:

          conn_id (:term:`connection id`): Must be a keyword argument.
            Connection ID of the connection in whose context the error
            happened. Omitted or `None` if the error did not happen in context
            of any connection, or if the connection context was not known.

          *args :
            Any other positional arguments are passed to :exc:`py:Exception`.

          **kwargs :
            Any other keyword arguments are passed to :exc:`py:Exception`.
        """
        if 'conn_id' in kwargs:
            conn_id = kwargs['conn_id']
            del kwargs['conn_id']
        else:
            conn_id = None
        super(Error, self).__init__(*args, **kwargs)
        self._conn_id = conn_id

    @property
    def conn_id(self):
        """
        :term:`connection id`: Connection ID of the connection in whose context
        the error happened.

        `None` if the error did not happen in context
        of any connection, or if the connection context was not known.
        """
        return self._conn_id

    @property
    def conn_str(self):
        """
        :term:`unicode string`: String that identifies the connection in
        exception messages.
        """
        ret_str = "Connection id: {0}".format(self.conn_id)
        return ret_str


class ConnectionError(Error):
    """
    This exception indicates a problem with the connection to the WBEM
    server. A retry may or may not succeed.
    Derived from :exc:`~pywbem.Error`.
    """
    pass


class AuthError(Error):
    """
    This exception indicates an authentication error with the WBEM server,
    either during TLS/SSL handshake, or during HTTP-level authentication.
    Derived from :exc:`~pywbem.Error`.
    """
    pass


class HTTPError(Error):
    """
    This exception indicates that the WBEM server returned an HTTP response
    with a bad HTTP status code. Derived from :exc:`~pywbem.Error`.

    The `args` instance variable is a `tuple (status, reason, cimerror,
    cimdetails)`.

    The `message` instance variable is not set.

    Occurrence of this exception nearly always indicates an issue with the
    WBEM server.
    """

    def __init__(self, status, reason, cimerror=None, cimdetails=None,
                 conn_id=None):
        """
        Parameters:

          status (:term:`integer`): HTTP status code (e.g. 500).

          reason (:term:`string`): HTTP reason phrase (e.g.
            "Internal Server Error").

          cimerror (:term:`string`): Value of the `CIMError` HTTP header field,
            if present. `None`, otherwise.

          cimdetails (dict): Dictionary with CIMOM-specific header
            fields with details about the situation reported in the `CIMError`
            header field.

            * Key: header field name (e.g. `PGErrorDetail`)
            * Value: header field value (i.e. text message)

            Passing `None` will result in an empty dictionary.

          conn_id (:term:`connection id`): Connection ID of the connection in
            whose context the error happened. `None` if the error did not
            happen in context of any connection, or if the connection context
            was not known.

        :ivar args: A tuple (status, reason, cimerror, cimdetails) set from the
            corresponding init arguments.
        """
        if cimdetails is None:
            cimdetails = {}
        super(HTTPError, self).__init__(
            status, reason, cimerror, cimdetails, conn_id=conn_id)

    @property
    def status(self):
        """
        :term:`integer`: HTTP status code.

        Example: 500

        See :term:`RFC2616` for a list of HTTP status codes and reason phrases.
        """
        return self.args[0]

    @property
    def reason(self):
        """
        :term:`string`: HTTP reason phrase.

        Example: "Internal Server Error"

        See :term:`RFC2616` for a list of HTTP status codes and reason phrases.
        """
        return self.args[1]

    @property
    def cimerror(self):
        """
        :term:`string`: Value of `CIMError` HTTP header field in response, if
        present.

        `None`, otherwise.

        See :term:`DSP0200` for a list of values.
        """
        return self.args[2]

    @property
    def cimdetails(self):
        """
        dict: CIMOM-specific details on the situation reported in the `CIMError`
        header field.

        The value is a dictionary with:

        * Key: header field name (e.g. `PGErrorDetail`).
        * Value: header field value.
        """
        return self.args[3]

    def __str__(self):
        ret_str = "{0} ({1})".format(self.status, self.reason)
        if self.cimerror is not None:
            ret_str += ", CIMError: {0}".format(self.cimerror)
        for key in self.cimdetails:
            ret_str += ", {0}: {1}".format(key, self.cimdetails[key])
        return ret_str


class TimeoutError(Error):
    """
    This exception indicates that the client timed out waiting for the WBEM
    server. Derived from :exc:`~pywbem.Error`.
    """
    pass


class ParseError(Error):
    """
    This exception indicates a parsing error with the CIM-XML operation
    response the pywbem client received, or with the CIM-XML indication
    request the pywbem listener received.

    Derived from :exc:`~pywbem.Error`.

    This class supports attaching the CIM-XML request and response data in
    properties :attr:`~pywbem.ParseError.request_data` and
    :attr:`~pywbem.ParseError.response_data`, respectively. When exceptions
    of this class are raised by pywbem, these properties will always be
    set.

    The CIM-XML response data is part of the `str()` representation of the
    exception.

    This exception is a base class for two more specific exceptions:

    * :exc:`~pywbem.CIMXMLParseError` - Issue at the CIM-XML level (e.g. NAME
      attribute missing on CLASS element)
    * :exc:`~pywbem.XMLParseError` - Issue at the XML level (e.g. ill-formed
      XML)

    Occurrence of this exception nearly always indicates an issue with the
    WBEM server.
    """

    def __init__(self, message, conn_id=None):
        """
        Parameters:

          message (:term:`string`): Error message (will be put into `args[0]`).

          conn_id (:term:`connection id`): Connection ID of the connection in
            whose context the error happened. `None` if the error did not
            happen in context of any connection, or if the connection context
            was not known.
        """
        super(ParseError, self).__init__(message, conn_id=conn_id)
        self._request_data = None
        self._response_data = None

    @property
    def request_data(self):
        """
        :term:`string`: CIM-XML request data (unformatted).
        """
        return self._request_data

    @request_data.setter
    def request_data(self, request_data):
        """Setter method; for a description see the getter method."""
        self._request_data = request_data

    @property
    def response_data(self):
        """
        :term:`string`: CIM-XML response data (unformatted).
        """
        return self._response_data

    @response_data.setter
    def response_data(self, response_data):
        """Setter method; for a description see the getter method."""
        self._response_data = response_data

    def __str__(self):
        error_str = super(ParseError, self).__str__()
        ret_str = "{0}\nCIM-XML response: {1}". \
            format(error_str, self.response_data)
        return ret_str


class CIMXMLParseError(ParseError):
    """
    This exception indicates a specific kind of :exc:`~pywbem.ParseError`
    that is an issue at the CIM-XML level.

    Example: 'NAME' attribute missing on 'CLASS' element.

    Occurrence of this exception nearly always indicates an issue with the
    WBEM server.
    """
    pass


class XMLParseError(ParseError):
    """
    This exception indicates a specific kind of :exc:`~pywbem.ParseError`
    that is an issue at the XML level.

    Example: Ill-formed XML.

    Occurrence of this exception nearly always indicates an issue with the
    WBEM server.
    """
    pass


class VersionError(Error):
    """
    This exception indicates an unsupported CIM, DTD or protocol version
    with the CIM-XML response returned by the WBEM server, or in the CIM-XML
    request sent by the WBEM listener. Derived from :exc:`~pywbem.Error`.
    """
    pass


class CIMError(Error):
    """
    This exception indicates that the WBEM server returned an error response
    with a CIM status code. Derived from :exc:`~pywbem.Error`.

    Accessing the CIM status code of a :class:`CIMError` object:

      In Python 2, any :exc:`~py:exceptions.Exception` object can be accessed
      by index and slice and will delegate such access to its
      :attr:`~py:exceptions.BaseException.args` instance variable. In Python 3,
      that ability has been removed.

      In pywbem 0.9, the :attr:`~pywbem.CIMError.status_code` and
      :attr:`~pywbem.CIMError.status_description` properties were added.

      Therefore, the following approach is not recommended, because it does not
      work on Python 3::

          except CIMError as exc:
              status_code = exc[0]

      The following approach works for pywbem 0.7 or newer::

          except CIMError as exc:
              status_code = exc.args[0]

      The following approach is recommended when using pywbem 0.9 or newer::

          except CIMError as exc:
              status_code = exc.status_code
    """

    # pylint: disable=super-init-not-called
    def __init__(self, status_code, status_description=None, instances=None,
                 conn_id=None):
        """
        Parameters:

          status_code (:term:`integer`): Numeric CIM status code.

          status_description (:term:`string`): CIM status description text
            returned by the server, representing a human readable message
            describing the error. `None`, if the server did not return
            a description text.

          instances (list of :class:`~pywbem.CIMInstance`): List of CIM
            instances returned by the WBEM server in the error response, that
            provide more details on the error. `None` if there are no such
            instances.

          conn_id (:term:`connection id`): Connection ID of the connection in
            whose context the error happened. `None` if the error did not
            happen in context of any connection, or if the connection context
            was not known.

        :ivar args: A tuple (status_code, status_description) set from the
            corresponding init arguments.
        """
        super(CIMError, self).__init__(
            status_code, status_description, instances, conn_id=conn_id)

    @property
    def status_code(self):
        """
        :term:`integer`: Numeric CIM status code.

        *New in pywbem 0.9.*

        Example: 5

        See :ref:`CIM status codes` for constants defining the numeric CIM
        status code values."""
        return self.args[0]

    @property
    def status_code_name(self):
        """
        :term:`string`: Symbolic name of the CIM status code.

        Example: "CIM_ERR_INVALID_CLASS"

        *New in pywbem 0.9.*

        If the CIM status code is invalid, the string
        "Invalid status code <status_code>" is returned."""
        return _statuscode2name(self.status_code)

    @property
    def status_description(self):
        """
        :term:`string`: CIM status description text returned by the server,
        representing a human readable message describing the error.

        *New in pywbem 0.9.*

        Example: "The specified class does not exist."

        If the server did not return a description, a short default text for
        the CIM status code is returned. If the CIM status code is invalid,
        the string "Invalid status code <status_code>" is returned.
        """
        return self.args[1] or _statuscode2string(self.status_code)

    @property
    def instances(self):
        """
        List of :class:`~pywbem.CIMInstance`: CIM instances returned by the
        WBEM server in the error response, that provide more details on the
        error.

        *New in pywbem 0.13.*

        `None` if there are no such instances.
        """
        return self.args[2]

    def __str__(self):
        inst_str = " ({0} instances)".format(len(self.instances)) \
            if self.instances else ""
        ret_str = "{0} ({1}): {2}{3}".format(
            self.status_code, self.status_code_name, self.status_description,
            inst_str)
        return ret_str


class ModelError(Error):
    """
    This exception indicates an error with the model implemented by the WBEM
    server, that was detected by the pywbem client.

    Examples are mismatches in data types of CIM elements (properties, methods,
    parameters) between classes and instances, CIM elements that appear in
    instances without being declared in classes, or violations of requirements
    defined in advertised management profiles.

    Derived from :exc:`~pywbem.Error`.
    """
    pass
