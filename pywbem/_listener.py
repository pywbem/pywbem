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
*New in pywbem 0.9 as experimental and finalized in 0.10.*

The :class:`~pywbem.WBEMListener` class provides a thread-based WBEM listener
service that can receive CIM indications from multiple WBEM servers and that
calls registered callback functions to deliver the received indications.

Examples
--------

The following example creates and runs a listener::

    import sys
    import logging
    from socket import getfqdn
    from pywbem import WBEMListener

    def process_indication(indication, host):
        '''This function gets called when an indication is received.'''

        print("Received CIM indication from {host}: {ind!r}". \\
            format(host=host, ind=indication))

    def main():

        # Configure logging of the listener via the Python root logger
        logging.basicConfig(filename='listener.log', level=logging.WARNING,
            format='%(asctime)s - %(levelname)s - %(message)s)

        certkeyfile = 'listener.pem'

        listener = WBEMListener(host=getfqdn()
                                http_port=5988,
                                https_port=5989,
                                certfile=certkeyfile,
                                keyfile=certkeyfile)
        listener.add_callback(process_indication)

        try:
            listener.start()

            # process_indication() will be called for each received indication

            ... # wait for some condition to end listening

        finally:
            listener.stop()

Alternative code using the class as a context manager::

    with WBEMListener(...) as listener:
        listener.add_callback(process_indication)
        listener.start()

        # process_indication() will be called for each received indication

        ... # wait for some condition to end listening

    # listener.stop() has been called automatically

See the example in section :ref:`WBEMSubscriptionManager` for an example of
using a listener in combination with a subscription manager.

Another listener example is in the script ``examples/listen.py`` (when you
clone the GitHub pywbem/pywbem project). It is an interactive Python shell that
creates a listener and displays any indications it receives, in MOF format.


.. _`Logging in the listener`:

Logging in the listener
-----------------------

Each :class:`~pywbem.WBEMListener` object has its own separate Python logger
object with the name:

  `'pywbem.listener.{id}'`

where `{id}` is a string that is unique for each :class:`~pywbem.WBEMListener`
object within the Python process.

The :attr:`~pywbem.WBEMListener.logger` property of a
:class:`~pywbem.WBEMListener` object provides access to that Python logger
object, if needed.

The listener will log any indications it receives and any responses it sends
back to the indication sender, at the :attr:`py:logging.INFO` logging level.

In addition, it will log errors at the :attr:`py:logging.ERROR` logging level.

Since Python 2.7, the Python root logger will by default (i.e. when not being
configured) print log records of logging level :attr:`py:logging.WARNING` or
greater to `sys.stderr`. So the indication and response interactions will not
be printed by default, but any errors logged at the :attr:`py:logging.ERROR`
logging level will be printed by default.

Pywbem adds a null handler to the logger named `'pywbem'`, in order to prevent
the "No handlers could be found for logger ..." warning.
This follows best practices recommended in `Configuring logging for a library
<https://docs.python.org/2/howto/logging.html#configuring-logging-for-a-library>`_
and in several articles, for example in `this article
<http://pieces.openpolitics.com/2012/04/python-logging-best-practices/>`_.
Because this warning is no longer issued on Python 3.4 and higher, pywbem
adds a null handler only on Python 2.6 and 2.7.


.. _`WBEMListener class`:

WBEMListener class
------------------
"""

import sys
import errno
import re
import logging
import ssl
import threading
import six
from six.moves import BaseHTTPServer
from six.moves import socketserver
from six.moves import http_client

from . import _cim_xml
from ._version import __version__
from ._cim_obj import CIMInstance
from ._cim_constants import CIM_ERR_NOT_SUPPORTED, CIM_ERR_INVALID_PARAMETER, \
    _statuscode2name
from ._tupleparse import TupleParser
from ._tupletree import xml_to_tupletree_sax
from ._exceptions import CIMXMLParseError, XMLParseError, VersionError
from ._utils import _format

# CIM-XML protocol related versions implemented by the WBEM listener.
# These are returned in export message responses.
IMPLEMENTED_CIM_VERSION = '2.0'
IMPLEMENTED_DTD_VERSION = '2.4'
IMPLEMENTED_PROTOCOL_VERSION = '1.4'

# CIM-XML protocol related versions supported by the WBEM listener
# These are checked in export message requests.
SUPPORTED_DTD_VERSION_PATTERN = r'2\.\d+'
SUPPORTED_DTD_VERSION_STR = '2.x'
SUPPORTED_PROTOCOL_VERSION_PATTERN = r'1\.\d+'
SUPPORTED_PROTOCOL_VERSION_STR = '1.x'

# Pattern for findall() for header values that are a list of tokens with
# quality values (see RFC2616). The pattern does not verify conformance
# to the valid characters for tokens, but does its job in parsing tokens
# and q values.
TOKEN_QUALITY_FINDALL_PATTERN = re.compile(
    r'([^;, ]+)'
    r'(?:; *q=([01](?:\.[0-9]*)?))?'
    r'(?:, *)?')
TOKEN_CHARSET_FINDALL_PATTERN = re.compile(
    r'([^;, ]+)'
    r'(?:; *charset="?([^";, ]*)"?)?'
    r'(?:, *)?')

__all__ = ['WBEMListener', 'callback_interface']


class ThreadedHTTPServer(socketserver.ThreadingMixIn,
                         BaseHTTPServer.HTTPServer):
    """Defines an HTTPServer class for indication reception"""
    pass


class ListenerRequestHandler(BaseHTTPServer.BaseHTTPRequestHandler):
    """
    A request handler for the standard Python HTTP server, with a handler
    method for the HTTP POST method, that acts as a WBEM listener.
    """

    def invalid_method(self):
        """
        Handle invalid HTTP methods by sending HTTP status 405 "Method Not
        Allowed" back to the server. See DSP0200 for details on this.
        """
        self.send_http_error(405, headers=[('Allow', 'POST')])

    # pylint: disable=invalid-name
    def do_OPTIONS(self):
        """Invalid method for listener"""
        self.invalid_method()

    # pylint: disable=invalid-name
    def do_HEAD(self):
        """Invalid method for listener"""
        self.invalid_method()

    # pylint: disable=invalid-name
    def do_GET(self):
        """Invalid method for listener"""
        self.invalid_method()

    # pylint: disable=invalid-name
    def do_PUT(self):
        """Invalid method for listener"""
        self.invalid_method()

    # pylint: disable=invalid-name
    def do_PATCH(self):
        """Invalid method for listener"""
        self.invalid_method()

    # pylint: disable=invalid-name
    def do_DELETE(self):
        """Invalid method for listener"""
        self.invalid_method()

    # pylint: disable=invalid-name
    def do_TRACE(self):
        """Invalid method for listener"""
        self.invalid_method()

    # pylint: disable=invalid-name
    def do_CONNECT(self):
        """Invalid method for listener"""
        self.invalid_method()

    # pylint: disable=invalid-name
    def do_M_POST(self):
        """Invalid method for listener"""
        self.invalid_method()

    # pylint: disable=invalid-name
    def do_POST(self):
        """
        This method will be called for each POST request to one of the
        listener ports.

        It parses the CIM-XML export message and delivers the contained
        CIM indication to the stored listener object.
        """

        # Accept header check described in DSP0200
        accept = self.headers.get('Accept', 'text/xml')
        if accept not in ('text/xml', 'application/xml', '*/*'):
            self.send_http_error(
                406, 'header-mismatch',
                _format("Invalid Accept header value: {0} (need text/xml, "
                        "application/xml or */*)", accept))
            return

        # Accept-Charset header check described in DSP0200
        accept_charset = self.headers.get('Accept-Charset', 'UTF-8')
        tq_list = re.findall(TOKEN_QUALITY_FINDALL_PATTERN, accept_charset)
        found = False
        if tq_list is not None:
            for token, quality in tq_list:
                if token.lower() in ('utf-8', '*'):
                    found = True
                    break
        if not found:
            self.send_http_error(
                406, 'header-mismatch',
                _format("Invalid Accept-Charset header value: {0} "
                        "(need UTF-8 or *)", accept_charset))
            return

        # Accept-Encoding header check described in DSP0200
        accept_encoding = self.headers.get('Accept-Encoding', 'Identity')
        tq_list = re.findall(TOKEN_QUALITY_FINDALL_PATTERN, accept_encoding)
        identity_acceptable = False
        identity_found = False
        if tq_list is not None:
            for token, quality in tq_list:
                quality = 1 if quality == '' else float(quality)
                if token.lower() == 'identity':
                    identity_found = True
                    if quality > 0:
                        identity_acceptable = True
                    break
            if not identity_found:
                for token, quality in tq_list:
                    quality = 1 if quality == '' else float(quality)
                    if token == '*' and quality > 0:
                        identity_acceptable = True
                        break
        if not identity_acceptable:
            self.send_http_error(
                406, 'header-mismatch',
                _format("Invalid Accept-Encoding header value: {0} "
                        "(need Identity to be acceptable)", accept_encoding))
            return

        # Accept-Language header check described in DSP0200.
        # Ignored, because this WBEM listener does not support multiple
        # languages, and hence any language is allowed to be returned.

        # Accept-Range header check described in DSP0200
        accept_range = self.headers.get('Accept-Range', None)
        if accept_range is not None:
            self.send_http_error(
                406, 'header-mismatch',
                _format("Accept-Range header is not permitted {0}",
                        accept_range))
            return

        # Content-Type header check described in DSP0200
        content_type = self.headers.get('Content-Type', None)
        if content_type is None:
            self.send_http_error(
                406, 'header-mismatch',
                "Content-Type header is required")
            return
        tc_list = re.findall(TOKEN_CHARSET_FINDALL_PATTERN, content_type)
        found = False
        if tc_list is not None:
            for token, charset in tc_list:
                if token.lower() in ('text/xml', 'application/xml') and \
                   (charset == '' or charset.lower() == 'utf-8'):
                    found = True
                    break
        if not found:
            self.send_http_error(
                406, 'header-mismatch',
                _format("Invalid Content-Type header value: {0} "
                        "(need text/xml or application/xml with "
                        "charset=utf-8 or empty)",
                        content_type))
            return

        # Content-Encoding header check described in DSP0200
        content_encoding = self.headers.get('Content-Encoding', 'identity')
        if content_encoding.lower() != 'identity':
            self.send_http_error(
                406, 'header-mismatch',
                _format("Invalid Content-Encoding header value: {0}"
                        "(listener supports only identity)",
                        content_encoding))
            return

        # Content-Language header check described in DSP0200.
        # Ignored, because this WBEM listener does not support multiple
        # languages, and hence any language is allowed in the request.

        # The following headers are ignored. They are not allowed to be used
        # by servers, but listeners are not required to reject them:
        # Content-Range, Expires, If-Range, Range.

        # Start processing the request
        content_len = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_len)

        try:
            msgid, methodname, params = self.parse_export_request(body)
        except (CIMXMLParseError, XMLParseError) as exc:
            self.send_http_error(400, "request-not-well-formed", str(exc))
            return
        except VersionError as exc:
            if str(exc).startswith("DTD"):
                self.send_http_error(400, "unsupported-dtd-version",
                                     str(exc))
            elif str(exc).startswith("Protocol"):
                self.send_http_error(400, "unsupported-protocol-version",
                                     str(exc))
            else:
                self.send_http_error(400, "unsupported-version", str(exc))
            return

        if methodname == 'ExportIndication':

            if len(params) != 1 or 'NewIndication' not in params:
                self.send_error_response(
                    msgid, methodname, CIM_ERR_INVALID_PARAMETER,
                    _format("Expecting one parameter NewIndication, got {0!A}",
                            params.keys()))
                return

            indication_inst = params['NewIndication']

            if not isinstance(indication_inst, CIMInstance):
                self.send_error_response(
                    msgid, methodname, CIM_ERR_INVALID_PARAMETER,
                    _format("NewIndication parameter is not a CIM instance, "
                            "but {0!A}", indication_inst))
                return
            # server.listener created in WBEMListener.start function
            self.server.listener.deliver_indication(indication_inst,
                                                    self.client_address[0])

            self.send_success_response(msgid, methodname)

        else:
            self.send_error_response(
                msgid, methodname, CIM_ERR_NOT_SUPPORTED,
                _format("Unknown export method: {0!A}", methodname))

    def send_http_error(self, http_code, cim_error=None,
                        cim_error_details=None, headers=None):
        """
        Send an HTTP response back to the WBEM server that indicates
        an error at the HTTP level.
        """
        self.send_response(http_code, http_client.responses.get(http_code, ''))
        self.send_header("CIMExport", "MethodResponse")
        if cim_error is not None:
            self.send_header("CIMError", cim_error)
        if cim_error_details is not None:
            self.send_header("CIMErrorDetails", cim_error_details)
        if headers is not None:
            for header, value in headers:
                self.send_header(header, value)
        self.end_headers()
        self.log('%s: HTTP status %s; CIMError: %s, CIMErrorDetails: %s',
                 (self._get_log_prefix(), http_code, cim_error,
                  cim_error_details),
                 logging.WARNING)

    def send_error_response(self, msgid, methodname, status_code, status_desc,
                            error_insts=None):
        """Send a CIM-XML response message back to the WBEM server that
        indicates error."""

        resp_xml = _cim_xml.CIM(
            _cim_xml.MESSAGE(
                _cim_xml.SIMPLEEXPRSP(
                    _cim_xml.EXPMETHODRESPONSE(
                        methodname,
                        _cim_xml.ERROR(
                            str(status_code),
                            status_desc,
                            error_insts),
                        ),  # noqa: E123
                    ),  # noqa: E123
                msgid, IMPLEMENTED_PROTOCOL_VERSION),
            IMPLEMENTED_CIM_VERSION, IMPLEMENTED_DTD_VERSION)

        resp_body = '<?xml version="1.0" encoding="utf-8" ?>\n' + \
                    resp_xml.toxml()

        if isinstance(resp_body, six.text_type):
            resp_body = resp_body.encode("utf-8")

        http_code = 200
        self.send_response(http_code, http_client.responses.get(http_code, ''))
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(resp_body)))
        self.send_header("CIMExport", "MethodResponse")
        self.end_headers()
        self.wfile.write(resp_body)
        self.log('%s: HTTP status %s; CIM error response: %s: %s',
                 (self._get_log_prefix(), http_code,
                  _statuscode2name(status_code), status_desc),
                 logging.WARNING)

    def send_success_response(self, msgid, methodname):
        """Send a CIM-XML response message back to the WBEM server that
        indicates success."""

        resp_xml = _cim_xml.CIM(
            _cim_xml.MESSAGE(
                _cim_xml.SIMPLEEXPRSP(
                    _cim_xml.EXPMETHODRESPONSE(
                        methodname),
                    ),  # noqa: E123
                msgid, IMPLEMENTED_PROTOCOL_VERSION),
            IMPLEMENTED_CIM_VERSION, IMPLEMENTED_DTD_VERSION)
        resp_body = '<?xml version="1.0" encoding="utf-8" ?>\n' + \
                    resp_xml.toxml()

        if isinstance(resp_body, six.text_type):
            resp_body = resp_body.encode("utf-8")

        http_code = 200
        self.send_response(http_code, http_client.responses.get(http_code, ''))
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(resp_body)))
        self.send_header("CIMExport", "MethodResponse")
        self.end_headers()
        self.wfile.write(resp_body)

    @staticmethod
    def parse_export_request(request_str):
        """Parse a CIM-XML export request message, and return
        a tuple(msgid, methodname, params).
        """

        # Parse the XML into a tuple tree (may raise CIMXMLParseError or
        # XMLParseError):

        tt_ = xml_to_tupletree_sax(request_str, "CIM-XML export request")
        tp = TupleParser()
        tup_tree = tp.parse_cim(tt_)

        # Check the tuple tree

        if tup_tree[0] != 'CIM':
            raise CIMXMLParseError(
                _format("Expecting CIM element, got {0}", tup_tree[0]))
        dtd_version = tup_tree[1]['DTDVERSION']
        if not re.match(SUPPORTED_DTD_VERSION_PATTERN, dtd_version):
            raise VersionError(
                _format("DTD version {0} not supported. Supported versions "
                        "are: {1!A}",
                        dtd_version, SUPPORTED_DTD_VERSION_STR))
        tup_tree = tup_tree[2]

        if tup_tree[0] != 'MESSAGE':
            raise CIMXMLParseError(
                _format("Expecting MESSAGE element, got {0}", tup_tree[0]))
        msgid = tup_tree[1]['ID']
        protocol_version = tup_tree[1]['PROTOCOLVERSION']
        if not re.match(SUPPORTED_PROTOCOL_VERSION_PATTERN, protocol_version):
            raise VersionError(
                _format("Protocol version {0} not supported. "
                        "Supported versions are: {1!A}",
                        protocol_version, SUPPORTED_PROTOCOL_VERSION_STR))
        tup_tree = tup_tree[2]

        if tup_tree[0] != 'SIMPLEEXPREQ':
            raise CIMXMLParseError(
                _format("Expecting SIMPLEEXPREQ element, got {0}",
                        tup_tree[0]))
        tup_tree = tup_tree[2]

        if tup_tree[0] != 'EXPMETHODCALL':
            raise CIMXMLParseError(
                _format("Expecting EXPMETHODCALL element, got {0}",
                        tup_tree[0]))

        methodname = tup_tree[1]['NAME']
        params = {}
        for name, obj in tup_tree[2]:
            params[name] = obj

        return (msgid, methodname, params)

    def log(self, format_, args, level=logging.INFO):
        """
        This function is called for anything that needs to get logged.
        It logs to the logger of this listener.

        It is not defined in the standard handler class; our version
        has an additional `level` argument that allows to control the
        logging level in the standard Python logging support.

        Another difference is that the variable arguments are passed
        in as a tuple.
        """
        self.server.listener.logger.log(level, format_, *args)

    # pylint: disable=redefined-builtin
    def log_message(self, format, *args):
        """
        In the standard handler class, this function is called for anything
        that needs to get logged (e.g. from :meth:`log_request`).

        We override it in order to use our own log function.
        """
        self.log(format, args, logging.INFO)

    def log_request(self, code='-', size='-'):
        #  pylint: disable=unused-argument
        """
        This function is called during :meth:`send_response`.

        We override it to get a little more information logged in a somewhat
        better format.  We do not use the size  method argument.
        """
        self.log('%s: HTTP status %s',
                 (self._get_log_prefix(), code),
                 logging.INFO)

    def _get_log_prefix(self):
        """Return the prefix components for a log entry"""
        return _format("{0} {1} from {2}",
                       self.request_version, self.command,
                       self.client_address[0])

    def version_string(self):
        """
        Overrides the inherited method to add the pywbem listener version.
        """
        return _format("pywbem-listener/{0} {1} {2} ",
                       __version__, self.server_version, self.sys_version)


# pylint: disable=too-many-instance-attributes
class WBEMListener(object):
    """
    *New in pywbem 0.9 as experimental and finalized in 0.10.*

    A WBEM listener.

    The listener supports starting and stopping threads that listen for
    CIM-XML ExportIndication messages using HTTP and/or HTTPS, and that pass
    any received indications on to registered callback functions.

    The listener must be stopped in order to free the TCP/IP port it listens
    on. Using this class as a context manager ensures that the listener is
    stopped when leaving the context manager scope.
    """

    def __init__(self, host, http_port=None, https_port=None,
                 certfile=None, keyfile=None):
        """
        Parameters:

          host (:term:`string`):
            IP address or host name at which this listener can be reached.

          http_port (:term:`string` or :term:`integer`):
            HTTP port at which this listener can be reached. Note that at
            least one port (HTTP or HTTPS) must be set.

            `None` means not to set up a port for HTTP.

          https_port (:term:`string` or :term:`integer`):
            HTTPS port at which this listener can be reached.

            `None` means not to set up a port for HTTPS.

          certfile (:term:`string`):
            File path of certificate file to be used as server certificate
            during SSL/TLS handshake when creating the secure HTTPS connection.

            It is valid for the certificate file to contain a private key; the
            server certificate sent during SSL/TLS handshake is sent without
            the private key.

            `None` means not to use a server certificate file. Setting up a port
            for HTTPS requires specifying a certificate file.

          keyfile (:term:`string`):
            File path of private key file to be used by the server during
            SSL/TLS handshake when creating the secure HTTPS connection.

            It is valid to specify a certificate file that contains a private
            key.

            `None` means not to use a private key file. Setting up a port
            for HTTPS requires specifying a private key file.
        """

        self._host = host

        if isinstance(http_port, six.integer_types):
            self._http_port = int(http_port)  # Convert Python 2 long to int
        elif isinstance(http_port, six.string_types):
            self._http_port = int(http_port)
        elif http_port is None:
            self._http_port = http_port
        else:
            raise TypeError(
                _format("Invalid type for http_port: {0}", type(http_port)))

        if isinstance(https_port, six.integer_types):
            self._https_port = int(https_port)  # Convert Python 2 long to int
        elif isinstance(https_port, six.string_types):
            self._https_port = int(https_port)
        elif https_port is None:
            self._https_port = https_port
        else:
            raise TypeError(
                _format("Invalid type for https_port: {0}", type(https_port)))

        if self._https_port is not None:
            if certfile is None:
                raise ValueError("https_port requires certfile")
            self._certfile = certfile
            if keyfile is None:
                raise ValueError("https_port requires keyfile")
            self._keyfile = keyfile
        else:
            self._certfile = None
            self._keyfile = None

        if self._http_port is None and self._https_port is None:
            raise ValueError("Listener requires at least one active port")

        self._http_server = None  # ThreadedHTTPServer for HTTP
        self._http_thread = None  # Thread for HTTP
        self._https_server = None  # ThreadedHTTPServer for HTTPS
        self._https_thread = None  # Thread for HTTPS

        self._logger = logging.getLogger(
            _format("pywbem.listener.{0}", id(self)))

        self._callbacks = []  # Registered callback functions

    def __str__(self):
        """
        Return a representation of the :class:`~pywbem.WBEMListener` object
        with a subset of its attributes.
        """
        return _format(
            "WBEMListener("
            "_host={s._host!A}, "
            "_http_port={s._http_port!A}, "
            "_https_port={s._https_port!A}, "
            "...)",
            s=self)

    def __repr__(self):
        """
        Return a representation of the :class:`~pywbem.WBEMListener` object
        with all attributes, that is suitable for debugging.
        """
        return _format(
            "WBEMListener("
            "_host={s._host!A}, "
            "_http_port={s._http_port!A}, "
            "_https_port={s._https_port!A}, "
            "_certfile={s._certfile!A}, "
            "_keyfile={s._keyfile!A}, "
            "_logger={s._logger!A}, "
            "_callbacks={s._callbacks!A})",
            s=self)

    def __enter__(self):
        """
        *New in pywbem 0.12.*

        Enter method when the class is used as a context manager.

        Returns the listener object.
        """
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """
        *New in pywbem 0.12.*

        Exit method when the class is used as a context manager.

        Stops the listener by calling :meth:`~pywbem.WBEMListener.stop`.
        """
        self.stop()
        return False  # re-raise any exceptions

    @property
    def host(self):
        """
        :term:`string`: IP address or host name at which this listener can be
        reached.
        """
        return self._host

    @property
    def http_port(self):
        """
        :term:`integer`: HTTP port at which this listener can be reached.

        `None` means there is no port set up for HTTP.
        """
        return self._http_port

    @property
    def https_port(self):
        """
        :term:`integer`: HTTPS port at which this listener can be reached.

        `None` means there is no port set up for HTTPS.
        """
        return self._https_port

    @property
    def http_started(self):
        """
        :class:`py:bool`: Boolean indicating whether the listener is started
        for the HTTP port.

        If no port is set up for HTTP, `False` is returned.

        *New in pywbem 0.12.*
        """
        return self._http_server is not None

    @property
    def https_started(self):
        """
        :class:`py:bool`: Boolean indicating whether the listener is started
        for the HTTPS port.

        If no port is set up for HTTPS, `False` is returned.

        *New in pywbem 0.12.*
        """
        return self._https_server is not None

    @property
    def certfile(self):
        """
        :term:`string`: File path of the certificate file used as server
        certificate during SSL/TLS handshake when creating the secure HTTPS
        connection.

        `None` means there is no certificate file being used (that is, no port
        is set up for HTTPS).
        """
        return self._certfile

    @property
    def keyfile(self):
        """
        :term:`string`: File path of the private key file used by the server
        during SSL/TLS handshake when creating the secure HTTPS connection.

        `None` means there is no certificate file being used (that is, no port
        is set up for HTTPS).
        """
        return self._keyfile

    @property
    def logger(self):
        """
        :class:`py:logging.Logger`: Logger object for this listener.

        Each listener object has its own separate logger object with the name:

          `'pywbem.listener.{id}'`

        where `{id}` is a unique string for each listener object.

        Users of the listener should not look up the logger object by name, but
        should use this property to get to it.
        """
        return self._logger

    def start(self):
        """
        Start the WBEM listener threads, if they are not yet running.

        A thread serving CIM-XML over HTTP is started if an HTTP port was
        specified for the listener.
        A thread serving CIM-XML over HTTPS is started if an HTTPS
        port was specified for the listener.

        These server threads will handle the ExportIndication export message
        described in :term:`DSP0200` and they will invoke the registered
        callback functions for any received CIM indications.

        The listener must be stopped again in order to free the TCP/IP port it
        listens on. The listener can be stopped explicitly using the
        :meth:`~pywbem.WBEMListener.stop` method. The listener will be
        automatically stopped when the main thread terminates (i.e. when the
        Python process terminates), or when :class:`~pywbem.WBEMListener`
        is used as a context manager when leaving its scope.

        Raises:

          :exc:`~py:exceptions.OSError`:
            with :attr:`~OSError.errno` =
            :data:`py:errno.EADDRINUSE` when the WBEM listener port is already
            in use.
        """

        if self._http_port:
            if not self._http_server:
                try:
                    server = ThreadedHTTPServer((self._host, self._http_port),
                                                ListenerRequestHandler)
                except Exception as exc:
                    # Linux+py2: socket.error; Linux+py3: OSError;
                    # Windows does not raise any exception.
                    if getattr(exc, 'errno', None) == errno.EADDRINUSE:
                        # Reraise with improved error message
                        msg = _format("WBEM listener port {0} already in use",
                                      self._http_port)
                        exc_type = OSError
                        six.reraise(exc_type, exc_type(errno.EADDRINUSE, msg),
                                    sys.exc_info()[2])
                    raise

                # pylint: disable=attribute-defined-outside-init
                server.listener = self
                thread = threading.Thread(target=server.serve_forever)
                thread.daemon = True  # Exit server thread upon main thread exit
                self._http_server = server
                self._http_thread = thread
                thread.start()
        else:
            # Just in case someone changed self._http_port after init...
            self._http_server = None
            self._http_thread = None

        if self._https_port:
            if not self._https_server:
                try:
                    server = ThreadedHTTPServer((self._host, self._https_port),
                                                ListenerRequestHandler)
                except Exception as exc:
                    # Linux+py2: socket.error; Linux+py3: OSError;
                    # Windows does not raise any exception.
                    if getattr(exc, 'errno', None) == errno.EADDRINUSE:
                        # Reraise with improved error message
                        msg = _format("WBEM listener port {0} already in use",
                                      self._http_port)
                        exc_type = OSError
                        six.reraise(exc_type, exc_type(errno.EADDRINUSE, msg),
                                    sys.exc_info()[2])
                    raise

                # pylint: disable=attribute-defined-outside-init
                server.listener = self

                try:
                    try:
                        # PROTOCOL_TLS was introduced in Py 2.7.13
                        ssl_protocol = ssl.PROTOCOL_TLS
                    except AttributeError:
                        # Alias for PROTOCOL_TLS and deprecated in Py 2.7.13
                        ssl_protocol = ssl.PROTOCOL_SSLv23
                    # SSLContext was introduced in Python 2.7.9
                    ctx = ssl.SSLContext(ssl_protocol)
                    ctx.options |= ssl.OP_NO_SSLv2
                    ctx.options |= ssl.OP_NO_SSLv3
                    ctx.load_cert_chain(
                        certfile=self._certfile,
                        keyfile=self._keyfile)
                    server.socket = ctx.wrap_socket(
                        server.socket,
                        server_side=True)
                except AttributeError:
                    # Fall back to deprecated ssl.wrap_socket() before Py 2.7.9
                    server.socket = ssl.wrap_socket(
                        server.socket,
                        certfile=self._certfile,
                        keyfile=self._keyfile,
                        server_side=True)

                thread = threading.Thread(target=server.serve_forever)
                thread.daemon = True  # Exit server thread upon main thread exit
                self._https_server = server
                self._https_thread = thread
                thread.start()
        else:
            # Just in case someone changed self._https_port after init...
            self._https_server = None
            self._https_thread = None

    def stop(self):
        """
        Stop the WBEM listener threads, if they are running.
        """

        # Stopping the server will cause its `serve_forever()` method
        # to return, which will cause the server thread to terminate.
        # TODO: Describe how the processing threads terminate.

        if self._http_server:
            self._http_server.shutdown()
            self._http_server.server_close()
            self._http_server = None
            self._http_thread = None

        if self._https_server:
            self._https_server.shutdown()
            self._https_server.server_close()
            self._https_server = None
            self._https_thread = None

    def deliver_indication(self, indication, host):
        """
        This function is called by the listener threads for each received
        indication. It is not supposed to be called by the user.

        It delivers the indication to all callback functions that have been
        added to the listener.

        If a callback function raises any exception this is logged as an error
        using the listener logger and the next registered callback function is
        called.

        Parameters:

          indication (:class:`~pywbem.CIMInstance`):
            Representation of the CIM indication to be delivered.

          host (:term:`string`):
            Host name or IP address of WBEM server sending the indication.
        """
        for callback in self._callbacks:
            try:
                callback(indication, host)
            except Exception as exc:  # pylint: disable=broad-except
                self.logger.log(logging.ERROR, "Indication delivery callback "
                                "function raised %s: %s",
                                exc.__class__.__name__, exc)

    def add_callback(self, callback):
        """
        Add a callback function to the listener.

        The callback function will be called for each indication this listener
        receives from any WBEM server.

        If the callback function is already known to the listener, it will not
        be added.

        Parameters:

          callback (:func:`~pywbem.callback_interface`):
            Callable that is being called for each CIM indication that is
            received while the listener threads are running.
        """
        if callback not in self._callbacks:
            self._callbacks.append(callback)


def callback_interface(indication, host):
    # pylint: disable=unused-argument
    """
    *New in pywbem 0.9 as experimental and finalized in 0.10.*

    Interface of a callback function that is provided by the user of the API
    and that will be called by the listener for each received CIM indication.

    Parameters:

      indication (:class:`~pywbem.CIMInstance`):
        Representation of the CIM indication that has been received.
        Its `path` attribute is `None`.

      host (:term:`string`):
        Host name or IP address of WBEM server sending the indication.

    Raises:

        Exception: If a callback function raises any exception this is logged
          as an error using the listener logger and the next registered
          callback function is called.
    """
    raise NotImplementedError
