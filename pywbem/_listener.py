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

        logging.basicConfig(stream=sys.stderr, level=logging.WARNING,
            format='%(asctime)s - %(levelname)s - %(message)s)

        certkeyfile = 'listener.pem'

        url1 = 'http://server1'
        conn1 = WBEMConnection(url1)
        server1 = WBEMServer(conn1)
        server1.determine_interop_ns()

        url2 = 'http://server2'
        conn2 = WBEMConnection(url2)
        server2 = WBEMServer(conn2)
        server2.validate_interop_ns('root/PG_InterOp')

        my_listener = WBEMListener(host=getfqdn()
                                http_port=5988,
                                https_port=5989,
                                certfile=certkeyfile,
                                keyfile=certkeyfile)
        my_listener.add_callback(process_indication)
        listener.start()

            # listener runs until executable terminated
            # or listener.stop()

See the example in section :ref:`WBEMSubscriptionManager` for an example of
using a listener in combination with a subscription manager.

Another listener example is in the script ``examples/listen.py`` (when you
clone the GitHub pywbem/pywbem project). It is an interactive Python shell that
creates a listener and displays any indications it receives, in MOF format.
"""

import re
import logging
try:  # Python 2.7+
    from logging import NullHandler
except ImportError:
    class NullHandler(logging.Handler):
        """Implement logging NullHandler for python 2.6"""
        def emit(self, record):
            pass
    logging.NullHandler = NullHandler
import ssl
from xml.parsers.expat import ExpatError
from xml.sax import SAXParseException
import threading
import six
from six.moves import BaseHTTPServer
from six.moves import socketserver
from six.moves import http_client

from . import cim_xml
from ._version import __version__
from .cim_obj import CIMInstance, _ensure_unicode
from .cim_operations import check_utf8_xml_chars
from .cim_constants import CIM_ERR_NOT_SUPPORTED, CIM_ERR_INVALID_PARAMETER, \
    _statuscode2name
from .tupleparse import parse_cim
from .tupletree import xml_to_tupletree_sax
from .exceptions import ParseError, VersionError


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
            self.send_http_error(406, 'header-mismatch',
                                 'Invalid Accept header value: %s '
                                 '(need text/xml, application/xml or */*)' %
                                 accept)
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
            self.send_http_error(406, 'header-mismatch',
                                 'Invalid Accept-Charset header value: %s '
                                 '(need UTF-8 or *)' %
                                 accept_charset)
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
            self.send_http_error(406, 'header-mismatch',
                                 'Invalid Accept-Encoding header value: %s '
                                 '(need Identity to be acceptable)' %
                                 accept_encoding)
            return

        # Accept-Language header check described in DSP0200.
        # Ignored, because this WBEM listener does not support multiple
        # languages, and hence any language is allowed to be returned.

        # Accept-Range header check described in DSP0200
        accept_range = self.headers.get('Accept-Range', None)
        if accept_range is not None:
            self.send_http_error(406, 'header-mismatch',
                                 'Accept-Range header is not permitted %s' %
                                 accept_range)
            return

        # Content-Type header check described in DSP0200
        content_type = self.headers.get('Content-Type', None)
        if content_type is None:
            self.send_http_error(406, 'header-mismatch',
                                 'Content-Type header is required')
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
            self.send_http_error(406, 'header-mismatch',
                                 'Invalid Content-Type header value: %s '
                                 '(need text/xml or application/xml with '
                                 'charset=utf-8 or empty)' %
                                 content_type)
            return

        # Content-Encoding header check described in DSP0200
        content_encoding = self.headers.get('Content-Encoding', 'identity')
        if content_encoding.lower() != 'identity':
            self.send_http_error(406, 'header-mismatch',
                                 'Invalid Content-Encoding header value: '
                                 '%s (listener supports only identity)' %
                                 content_encoding)
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
        except ParseError as exc:
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
                self.send_error_response(msgid, methodname,
                                         CIM_ERR_INVALID_PARAMETER,
                                         'Expecting one parameter '
                                         'NewIndication, got %s' %
                                         ','.join(params.keys()))
                return

            indication_inst = params['NewIndication']

            if not isinstance(indication_inst, CIMInstance):
                self.send_error_response(msgid, methodname,
                                         CIM_ERR_INVALID_PARAMETER,
                                         'NewIndication parameter is not '
                                         'a CIM instance, but %r' %
                                         indication_inst)
                return
            # server.listener created in WBEMListener.start function
            self.server.listener.deliver_indication(indication_inst,
                                                    self.client_address[0])

            self.send_success_response(msgid, methodname)

        else:
            self.send_error_response(msgid, methodname,
                                     CIM_ERR_NOT_SUPPORTED,
                                     'Unknown export method: %s' % methodname)

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
        self.log('%s: HTTP status %s; CIMError: %s, '
                 'CIMErrorDetails: %s',
                 (self._get_log_prefix(), http_code, cim_error,
                  cim_error_details),
                 logging.WARNING)

    def send_error_response(self, msgid, methodname, status_code, status_desc,
                            error_insts=None):
        """Send a CIM-XML response message back to the WBEM server that
        indicates error."""

        resp_xml = cim_xml.CIM(
            cim_xml.MESSAGE(
                cim_xml.SIMPLEEXPRSP(
                    cim_xml.EXPMETHODRESPONSE(
                        methodname,
                        cim_xml.ERROR(
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

        resp_xml = cim_xml.CIM(
            cim_xml.MESSAGE(
                cim_xml.SIMPLEEXPRSP(
                    cim_xml.EXPMETHODRESPONSE(
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

        try:
            tup_tree = parse_cim(xml_to_tupletree_sax(request_str))
        except ParseError as exc:
            msg = str(exc)
            parsing_error = True
        except SAXParseException as exc:
            msg = str(exc)
            parsing_error = True
        except ExpatError as exc:
            # This is raised e.g. when XML numeric entity references of
            # invalid XML characters are used (e.g. '&#0;').
            # str(exc) is: "{message}, line {X}, offset {Y}"
            xml_lines = _ensure_unicode(request_str).splitlines()
            if len(xml_lines) >= exc.lineno:
                parsed_line = xml_lines[exc.lineno - 1]
            else:
                parsed_line = "<error: Line number indicated in " \
                              "ExpatError out of range: %s " \
                              "(only %s lines in XML)>" % \
                              (exc.lineno, len(xml_lines))
            msg = "ExpatError %s: %s: %r" % \
                  (str(exc.code), str(exc), parsed_line)
            parsing_error = True
        else:
            parsing_error = False

        if parsing_error:
            # Here we just improve the quality of the exception information,
            # so we do this only if it already has failed. Because the check
            # function we invoke catches more errors than minidom.parseString,
            # we call it also when debug is turned on.
            try:
                check_utf8_xml_chars(request_str, "CIM-XML export message")
            except ParseError:
                raise
            raise ParseError(msg)  # data from previous exception

        # Parse response

        if tup_tree[0] != 'CIM':
            raise ParseError('Expecting CIM element, got %s' %
                             tup_tree[0])
        dtd_version = tup_tree[1]['DTDVERSION']
        if not re.match(SUPPORTED_DTD_VERSION_PATTERN, dtd_version):
            raise VersionError('DTD version %s not supported. '
                               'Supported versions are: %s' %
                               (dtd_version, SUPPORTED_DTD_VERSION_STR))
        tup_tree = tup_tree[2]

        if tup_tree[0] != 'MESSAGE':
            raise ParseError('Expecting MESSAGE element, got %s' %
                             tup_tree[0])
        msgid = tup_tree[1]['ID']
        protocol_version = tup_tree[1]['PROTOCOLVERSION']
        if not re.match(SUPPORTED_PROTOCOL_VERSION_PATTERN, protocol_version):
            raise VersionError('Protocol version %s not supported. '
                               'Supported versions are: %s' %
                               (protocol_version,
                                SUPPORTED_PROTOCOL_VERSION_STR))
        tup_tree = tup_tree[2]

        if tup_tree[0] != 'SIMPLEEXPREQ':
            raise ParseError('Expecting SIMPLEEXPREQ element, got %s' %
                             tup_tree[0])
        tup_tree = tup_tree[2]

        if tup_tree[0] != 'EXPMETHODCALL':
            raise ParseError('Expecting EXPMETHODCALL element, '
                             'got %s' % tup_tree[0])

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

    def log_message(self, format_, *args):
        """
        In the standard handler class, this function is called for anything
        that needs to get logged (e.g. from :meth:`log_request`).

        We override it in order to use our own log function.
        """
        self.log(format_, args, logging.INFO)

    def log_request(self, code='-', size='-'):
        """
        This function is called during :meth:`send_response`.

        We override it to get a little more information logged in a somewhat
        better format.
        """
        self.log('%s: HTTP status %s',
                 (self._get_log_prefix(), code),
                 logging.INFO)

    def _get_log_prefix(self):
        """Return the prefix components for a log entry"""
        return '%s %s from %s' % \
               (self.request_version, self.command, self.client_address[0])

    def version_string(self):
        """
        Overrides the inherited method to add the pywbem listener version.
        """
        return 'pywbem-listener/%s %s %s ' % \
            (__version__, self.server_version, self.sys_version)


# pylint: disable=too-many-instance-attributes
class WBEMListener(object):
    """
    A WBEM listener.

    The listener supports starting and stopping threads that listen for
    CIM-XML ExportIndication messages using HTTP and/or HTTPS, and that pass
    any received indications on to registered callback functions.
    """

    def __init__(self, host, http_port=None, https_port=None,
                 certfile=None, keyfile=None):
        """
        Parameters:

          host (:term:`string`):
            IP address or host name this listener can be reached at.

          http_port (:term:`string` or :term:`integer`):
            HTTP port this listener can be reached at. Note that at least one
            port (HTTP or HTTPS) must be set

            `None` means not to set up a port for HTTP.

          https_port (:term:`string` or :term:`integer`):
            HTTPS port this listener can be reached at.

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
            raise TypeError("Invalid type for http_port: %s" %
                            type(http_port))

        if isinstance(https_port, six.integer_types):
            self._https_port = int(https_port)  # Convert Python 2 long to int
        elif isinstance(https_port, six.string_types):
            self._https_port = int(https_port)
        elif https_port is None:
            self._https_port = https_port
        else:
            raise TypeError("Invalid type for https_port: %s" %
                            type(https_port))

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
            ValueError('Listener requires at least one active port')

        self._http_server = None  # ThreadedHTTPServer for HTTP
        self._http_thread = None  # Thread for HTTP
        self._https_server = None  # ThreadedHTTPServer for HTTPS
        self._https_thread = None  # Thread for HTTPS

        self._logger = logging.getLogger('pywbem.listener.%s' % id(self))
        self._logger.addHandler(logging.NullHandler())

        self._callbacks = []  # Registered callback functions

    def __repr__(self):
        """
        Return a representation of the :class:`~pywbem.WBEMListener` object
        with all attributes, that is suitable for debugging.
        """
        return "%s(host=%r, http_port=%s, https_port=%s, " \
               "certfile=%r, keyfile=%r, logger=%r, _callbacks=%r)" % \
               (self.__class__.__name__, self.host, self.http_port,
                self.https_port, self.certfile, self.keyfile, self.logger,
                self._callbacks)

    @property
    def host(self):
        """The IP address or host name this listener can be reached at,
        as a :term:`string`."""
        return self._host

    @property
    def http_port(self):
        """
        The HTTP port this listener can be reached at, as an :term:`integer`.

        `None` means there is no port set up for HTTP.
        """
        return self._http_port

    @property
    def https_port(self):
        """
        The HTTPS port this listener can be reached at, as an :term:`integer`.

        `None` means there is no port set up for HTTPS.
        """
        return self._https_port

    @property
    def certfile(self):
        """
        The file path of the certificate file used as server certificate
        during SSL/TLS handshake when creating the secure HTTPS connection.

        `None` means there is no certificate file being used (that is, no port
        is set up for HTTPS).
        """
        return self._certfile

    @property
    def keyfile(self):
        """
        The file path of the private key file used by the server during
        SSL/TLS handshake when creating the secure HTTPS connection.

        `None` means there is no certificate file being used (that is, no port
        is set up for HTTPS).
        """
        return self._keyfile

    @property
    def logger(self):
        """
        The logger object for this listener.

        Each listener object has its own separate logger object that is
        created via :func:`py:logging.getLogger`.

        The name of this logger object is:

          ``pywbem.listener.{id}``

        where ``{id}`` is the :func:`id` value of the listener object. Users
        of the listener should not look up the logger object by name, but
        should use this property to get to it.

        By default, this logger uses the :class:`~py:logging.NullHandler` log
        handler, and its log level is :attr:`~py:logging.NOTSET`. This causes
        this logger not to emit any log messages and to propagate them to the
        Python root logger.

        The behavior of this logger can be changed by invoking its methods
        (see :class:`py:logging.Logger`). The behavior of the root logger can
        for example be configured using :func:`py:logging.basicConfig`::

            import sys
            import logging

            logging.basicConfig(stream=sys.stderr, level=logging.WARNING,
                format='%(asctime)s - %(levelname)s - %(message)s')
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

        These server threads can be stopped using the
        :meth:`~pywbem.WBEMListener.stop` method.
        They will be automatically stopped when the main thread terminates.
        """

        if self._http_port:
            if not self._http_server:
                server = ThreadedHTTPServer((self._host, self._http_port),
                                            ListenerRequestHandler)

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
                server = ThreadedHTTPServer((self._host, self._https_port),
                                            ListenerRequestHandler)

                # pylint: disable=attribute-defined-outside-init
                server.listener = self
                server.socket = ssl.wrap_socket(server.socket,
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
