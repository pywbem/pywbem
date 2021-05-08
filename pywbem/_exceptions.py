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

import six
from ._cim_constants import _statuscode2name, _statuscode2string

# This module is meant to be safe for 'import *'.

__all__ = ['Error', 'ConnectionError', 'AuthError', 'HTTPError', 'TimeoutError',
           'VersionError', 'ParseError', 'CIMVersionError', 'DTDVersionError',
           'ProtocolVersionError', 'CIMXMLParseError', 'XMLParseError',
           'HeaderParseError', 'CIMError', 'ModelError',
           'ListenerError', 'ListenerCertificateError',
           'ListenerPortError', 'ListenerPromptError']


class _RequestExceptionMixin(object):
    # pylint: disable=too-few-public-methods
    """
    An internal mixin class for pywbem specific exceptions that provides the
    ability to store the CIM-XML request string in the exception.

    *New in pywbem 1.0.*

    Derived classes using this mixin class need to specify it before the base
    error class.
    """

    def __init__(self, *args, **kwargs):
        """
        Parameters:

          *args :
            Any other positional arguments are passed on to the next superclass.

          **kwargs :
            Any other keyword arguments are passed on to the next superclass.

          request_data (:term:`string`):
            CIM-XML request string. Omitted or `None` means the exception does
            not store a CIM-XML request.
            Must be specified as a keyword argument; if specified it will be
            removed from the keyword arguments that are passed on.
        """
        if 'request_data' in kwargs:
            request_data = kwargs['request_data']
            del kwargs['request_data']
        else:
            request_data = None
        self.request_data = request_data
        super(_RequestExceptionMixin, self).__init__(*args, **kwargs)

    @property
    def request_data(self):
        """
        :term:`string`: CIM-XML request string (settable).
        `None` if the exception does not store a CIM-XML request.
        """
        return self._request_data

    @request_data.setter
    def request_data(self, request_data):
        """Setter method; for a description see the getter method."""
        self._request_data = request_data


class _ResponseExceptionMixin(object):
    # pylint: disable=too-few-public-methods
    """
    Mixin class into pywbem specific exceptions that provides the ability to
    store the CIM-XML response string in the exception.

    *New in pywbem 1.0.*

    Derived classes using this mixin class need to specify it before the base
    error class.
    """

    def __init__(self, *args, **kwargs):
        """
        Parameters:

          *args :
            Any other positional arguments are passed on to the next superclass.

          **kwargs :
            Any other keyword arguments are passed on to the next superclass.

          response_data (:term:`string`):
            CIM-XML response string. Omitted or `None` means the exception does
            not store a CIM-XML response.
            Must be specified as a keyword argument; if specified it will be
            removed from the keyword arguments that are passed on.
        """
        if 'response_data' in kwargs:
            response_data = kwargs['response_data']
            del kwargs['response_data']
        else:
            response_data = None
        self.response_data = response_data
        super(_ResponseExceptionMixin, self).__init__(*args, **kwargs)

    @property
    def response_data(self):
        """
        :term:`string`: CIM-XML response string (settable).
        `None` if the exception does not store a CIM-XML response.
        """
        return self._response_data

    @response_data.setter
    def response_data(self, response_data):
        """Setter method; for a description see the getter method."""
        self._response_data = response_data


class Error(Exception):
    """
    Abstract base class for pywbem client specific exceptions.
    """

    def __init__(self, *args, **kwargs):
        """
        Parameters:

          *args :
            Any other positional arguments are passed to :exc:`py:Exception`.

          conn_id (:term:`connection id`):
            Connection ID of the connection in whose context the error
            happened. Omitted or `None` if the error did not happen in context
            of any connection, or if the connection context was not known.
            Must be specified as a keyword argument.
        """
        if 'conn_id' in kwargs:
            conn_id = kwargs['conn_id']
            del kwargs['conn_id']
        else:
            conn_id = None
        self._conn_id = conn_id
        # The Python Exception class cannot be initialized with keyword args
        assert not kwargs, str(kwargs)
        super(Error, self).__init__(*args)

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
    # pylint: disable=redefined-builtin
    """
    This exception indicates a problem with the connection to the WBEM
    server. A retry may or may not succeed.

    Derived from :exc:`~pywbem.Error`.
    """

    def __init__(self, message, conn_id=None):
        """
        Parameters:

          message (:term:`string`): Error message (will be put into `args[0]`).

          conn_id (:term:`connection id`):
            Connection ID of the connection in whose context the error happened.
            Omitted or `None` if the error did not happen in context of any
            connection, or if the connection context was not known.

        :ivar args: A tuple (message, ) set from the corresponding init
            arguments.
        """
        assert message is None or isinstance(message, six.string_types), \
            str(type(message))
        super(ConnectionError, self).__init__(message, conn_id=conn_id)


class AuthError(Error):
    """
    This exception indicates an authentication error with the WBEM server,
    either during TLS/SSL handshake, or during HTTP-level authentication.

    Derived from :exc:`~pywbem.Error`.
    """

    def __init__(self, message, conn_id=None):
        """
        Parameters:

          message (:term:`string`): Error message (will be put into `args[0]`).

          conn_id (:term:`connection id`):
            Connection ID of the connection in whose context the error happened.
            Omitted or `None` if the error did not happen in context of any
            connection, or if the connection context was not known.

        :ivar args: A tuple (message, ) set from the corresponding init
            arguments.
        """
        assert message is None or isinstance(message, six.string_types), \
            str(type(message))
        super(AuthError, self).__init__(message, conn_id=conn_id)


class HTTPError(_RequestExceptionMixin, _ResponseExceptionMixin, Error):
    """
    This exception indicates that the WBEM server returned an HTTP response
    with a bad HTTP status code.

    Derived from :exc:`~pywbem.Error`.

    The `args` instance variable is a `tuple (status, reason, cimerror,
    cimdetails)`.

    The `message` instance variable is not set.

    Occurrence of this exception nearly always indicates an issue with the
    WBEM server.
    """

    def __init__(self, status, reason, cimerror=None, cimdetails=None,
                 conn_id=None, request_data=None, response_data=None):
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

          request_data (:term:`string`): CIM-XML request string.
            `None` means the exception does not store a CIM-XML request.

          response_data (:term:`string`): CIM-XML response string.
            `None` means the exception does not store a CIM-XML response.

        :ivar args: A tuple (status, reason, cimerror, cimdetails) set from the
            corresponding init arguments.
        """
        if cimdetails is None:
            cimdetails = {}
        super(HTTPError, self).__init__(
            status, reason, cimerror, cimdetails, conn_id=conn_id,
            request_data=request_data, response_data=response_data)

    @property
    def status(self):
        """
        :term:`integer`: HTTP status code.

        Example: 500

        See :term:`RFC2616` for a list of HTTP status codes and reason phrases.
        """
        # Note: The reporting of unsubscriptable-object seems to be a false
        # positive in Pylint, see https://github.com/PyCQA/pylint/issues/1498
        return self.args[0]  # pylint: disable=unsubscriptable-object

    @property
    def reason(self):
        """
        :term:`string`: HTTP reason phrase.

        Example: "Internal Server Error"

        See :term:`RFC2616` for a list of HTTP status codes and reason phrases.
        """
        return self.args[1]  # pylint: disable=unsubscriptable-object

    @property
    def cimerror(self):
        """
        :term:`string`: Value of `CIMError` HTTP header field in response, if
        present.

        `None`, otherwise.

        See :term:`DSP0200` for a list of values.
        """
        return self.args[2]  # pylint: disable=unsubscriptable-object

    @property
    def cimdetails(self):
        """
        dict: CIMOM-specific details on the situation reported in the `CIMError`
        header field.

        The value is a dictionary with:

        * Key: header field name (e.g. `PGErrorDetail`).
        * Value: header field value.
        """
        return self.args[3]  # pylint: disable=unsubscriptable-object

    def __str__(self):
        ret_str = "{0} ({1})".format(self.status, self.reason)
        if self.cimerror is not None:
            ret_str += ", CIMError: {0}".format(self.cimerror)
        for key in self.cimdetails:
            ret_str += ", {0}: {1}".format(key, self.cimdetails[key])
        return ret_str


class TimeoutError(Error):
    # pylint: disable=redefined-builtin
    """
    This exception indicates that the client timed out waiting for the WBEM
    server.

    Derived from :exc:`~pywbem.Error`.
    """

    def __init__(self, message, conn_id=None):
        """
        Parameters:

          message (:term:`string`): Error message (will be put into `args[0]`).

          conn_id (:term:`connection id`):
            Connection ID of the connection in whose context the error happened.
            Omitted or `None` if the error did not happen in context of any
            connection, or if the connection context was not known.

        :ivar args: A tuple (message, ) set from the corresponding init
            arguments.
        """
        assert message is None or isinstance(message, six.string_types), \
            str(type(message))
        super(TimeoutError, self).__init__(message, conn_id=conn_id)


class ParseError(_RequestExceptionMixin, _ResponseExceptionMixin, Error):
    """
    This exception is a base class for exceptions that indicate a parsing
    error with the CIM-XML operation response the pywbem client received, or
    with the CIM-XML indication request the pywbem listener received.

    Derived from :exc:`~pywbem.Error`.

    The CIM-XML response data is part of the `str()` representation of the
    exception.

    This exception is a base class for more specific exceptions:

    * :exc:`~pywbem.CIMXMLParseError` - Issue at the CIM-XML level (e.g. NAME
      attribute missing on CLASS element)
    * :exc:`~pywbem.XMLParseError` - Issue at the XML level (e.g. ill-formed
      XML)
    * :exc:`~pywbem.HeaderParseError` - Issue with HTTP headers (e.g. invalid
      content-type header)

    Occurrence of this exception nearly always indicates an issue with the
    WBEM server.
    """

    def __init__(self, message, conn_id=None, request_data=None,
                 response_data=None):
        """
        Parameters:

          message (:term:`string`): Error message (will be put into `args[0]`).

          conn_id (:term:`connection id`): Connection ID of the connection in
            whose context the error happened. `None` if the error did not
            happen in context of any connection, or if the connection context
            was not known.

          request_data (:term:`string`): CIM-XML request string.
            `None` means the exception does not store a CIM-XML request.

          response_data (:term:`string`): CIM-XML response string.
            `None` means the exception does not store a CIM-XML response.

        :ivar args: A tuple (message, ) set from the corresponding init
            argument.
        """
        assert message is None or isinstance(message, six.string_types), \
            str(type(message))
        super(ParseError, self).__init__(
            message, conn_id=conn_id, request_data=request_data,
            response_data=response_data)

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


class HeaderParseError(ParseError):
    """
    This exception indicates a specific kind of :exc:`~pywbem.ParseError`
    that is an issue with an HTTP header.

    Example: Invalid content-type.

    Occurrence of this exception nearly always indicates an issue with the
    WBEM server.
    """
    pass


class VersionError(Error):
    """
    This exception is a base class for exceptions that indicate an unsupported
    CIM, DTD or protocol version with the CIM-XML response returned by the
    WBEM server, or in the CIM-XML request sent by the WBEM listener.

    Derived from :exc:`~pywbem.Error`.

    This exception is a base class for more specific exceptions:

    * :exc:`~pywbem.CIMVersionError` - Unsupported CIM infrastructure version
      (CIMVERSION attribute) at the CIM-XML level.
    * :exc:`~pywbem.DTDVersionError` - Unsupported DTD version
      (DTDVERSION attribute) at the CIM-XML level.
    * :exc:`~pywbem.ProtocolVersionError` - Unsupported CIM operations over
      HTTP protocol version (PROTOCOLVERSION attribute) at the CIM-XML level.
    """

    def __init__(self, message, conn_id=None):
        """
        Parameters:

          message (:term:`string`): Error message (will be put into `args[0]`).

          conn_id (:term:`connection id`):
            Connection ID of the connection in whose context the error happened.
            Omitted or `None` if the error did not happen in context of any
            connection, or if the connection context was not known.

        :ivar args: A tuple (message, ) set from the corresponding init
            argument.
        """
        assert message is None or isinstance(message, six.string_types), \
            str(type(message))
        super(VersionError, self).__init__(message, conn_id=conn_id)


class CIMVersionError(VersionError):
    """
    This exception indicates an unsupported CIM infrastructure version
    (CIMVERSION attribute) at the CIM-XML level.

    Pywbem supports only CIM infrastructure version 2.x, corresponding to
    :term:`DSP0004` version 2.x.
    """
    pass


class DTDVersionError(VersionError):
    """
    This exception indicates an unsupported DTD version
    (DTDVERSION attribute) at the CIM-XML level.

    Pywbem supports only CIM-XML DTD version 2.x, corresponding to
    :term:`DSP0201` version 2.x.
    """
    pass


class ProtocolVersionError(VersionError):
    """
    This exception indicates an unsupported CIM operations over HTTP
    protocol version (PROTOCOLVERSION attribute) at the CIM-XML level.

    Pywbem supports only CIM operations over HTTP version 1.x, corresponding to
    :term:`DSP0200` version 1.x.
    """
    pass


class CIMError(_RequestExceptionMixin, Error):
    """
    This exception indicates that the WBEM server returned an error response
    with a CIM status code.

    Derived from :exc:`~pywbem.Error`.

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
                 conn_id=None, request_data=None):
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

          request_data (:term:`string`): CIM-XML request string.
            `None` means the exception does not store a CIM-XML request.

        :ivar args: A tuple (status_code, status_description, instances) set
            from the corresponding init arguments.
        """
        super(CIMError, self).__init__(
            status_code, status_description, instances, conn_id=conn_id,
            request_data=request_data)

    @property
    def status_code(self):
        """
        :term:`integer`: Numeric CIM status code.

        *New in pywbem 0.9.*

        Example: 5

        See :ref:`CIM status codes` for constants defining the numeric CIM
        status code values."""
        return self.args[0]  # pylint: disable=unsubscriptable-object

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
        desc = self.args[1]  # pylint: disable=unsubscriptable-object
        return desc or _statuscode2string(self.status_code)

    @property
    def instances(self):
        """
        List of :class:`~pywbem.CIMInstance`: CIM instances returned by the
        WBEM server in the error response, that provide more details on the
        error.

        *New in pywbem 0.13.*

        `None` if there are no such instances.
        """
        return self.args[2]  # pylint: disable=unsubscriptable-object

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

    Derived from :exc:`~pywbem.Error`.

    Examples are mismatches in data types of CIM elements (properties, methods,
    parameters) between classes and instances, CIM elements that appear in
    instances without being declared in classes, or violations of requirements
    defined in advertised management profiles.
    """

    def __init__(self, message, conn_id=None):
        """
        Parameters:

          message (:term:`string`): Error message (will be put into `args[0]`).

          conn_id (:term:`connection id`):
            Connection ID of the connection in whose context the error happened.
            Omitted or `None` if the error did not happen in context of any
            connection, or if the connection context was not known.

        :ivar args: A tuple (message, ) set from the corresponding init
            argument.
        """
        assert message is None or isinstance(message, six.string_types), \
            str(type(message))
        super(ModelError, self).__init__(message, conn_id=conn_id)


class ListenerError(Exception):
    """
    Abstract base class for exceptions raised by the pywbem listener (i.e.
    class :class:`~pywbem.WBEMListener`).

    *New in pywbem 1.3.*

    Derived from :exc:`Exception`.
    """

    def __init__(self, message):
        """
        Parameters:

          message (:term:`string`): Error message (will be put into `args[0]`).

        :ivar args: A tuple (message, ) set from the corresponding init
            argument.
        """
        assert message is None or isinstance(message, six.string_types), \
            str(type(message))
        super(ListenerError, self).__init__(message)


class ListenerCertificateError(ListenerError):
    """
    This exception indicates an error with the certificate file or its
    private key file when using HTTPS.

    *New in pywbem 1.3.*

    Derived from :exc:`~pywbem.ListenerError`.

    This includes bad format of the files, file not found, permission errors
    when accessing the files, or an invalid password for the private key file.
    """
    pass


class ListenerPortError(ListenerError):
    """
    This exception indicates that the port for the pywbem listener is already
    in use.

    *New in pywbem 1.3.*

    Derived from :exc:`~pywbem.ListenerError`.
    """
    pass


class ListenerPromptError(ListenerError):
    """
    This exception indicates that the prompt for the password of the private
    key file of the pywbem listener was interrupted or ended.

    *New in pywbem 1.3.*

    Derived from :exc:`~pywbem.ListenerError`.
    """
    pass
