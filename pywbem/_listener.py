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
The `WBEM listener API`_ provides functionality for managing subscriptions for
indications from one or more WBEM servers, and implements a thread-based WBEM
listener service.

.. note::

   At this point, the WBEM listener API is experimental.

Examples
--------

The following example code subscribes for a CIM alert indication
on two WBEM servers and registers a callback function for indication
delivery:

::

    import sys
    import logging
    from socket import getfqdn
    from pywbem import WBEMConnection, WBEMListener, WBEMServer

    def process_indication(indication, host):
        '''This function gets called when an indication is received.'''
        print("Received CIM indication from {host}: {ind!r}". \\
            format(host=host, ind=indication))

    def main():

        logging.basicConfig(stream=sys.stderr, level=logging.WARNING)

        certkeyfile = 'listener.pem'

        url1 = 'http://server1'
        conn1 = WBEMConnection(url1)
        server1 = WBEMServer(conn1)
        server1.determine_interop_ns()

        url2 = 'http://server2'
        conn2 = WBEMConnection(url2)
        server2 = WBEMServer(conn2)
        server2.validate_interop_ns('root/PG_InterOp')

        listener = WBEMListener(host=getfqdn()
                                http_port=5988,
                                https_port=5989,
                                certfile=certkeyfile,
                                keyfile=certkeyfile)
        listener.add_callback(process_indication)
        listener.add_server(server1)
        listener.add_server(server2)
        listener.start()

        # Subscribe for a static filter of a given name
        filter1_paths = listener.get_filters(url1)
        for fp in filter1_paths:
            if fp.keybindings['Name'] == \\
               "DMTF:Indications:GlobalAlertIndicationFilter":
                listener.add_subscription(url1, fp)
                break

        # Create a dynamic alert indication filter and subscribe for it
        filter2_path = listener.add_dynamic_filter(
            url2,
            query_language="DMTF:CQL"
            query="SELECT * FROM CIM_AlertIndication " \\
                  "WHERE OwningEntity = 'DMTF' " \\
                  "AND MessageID LIKE 'SVPC0123|SVPC0124|SVPC0125'")
        listener.add_subscription(url2, filter2_path)

Another more practical example is in the script ``examples/listen.py``
(when you clone the GitHub pywbem/pywbem project).
It is an interactive Python shell that creates a WBEM listener and displays
any indications it receives, in MOF format.
"""

import os
import sys
import re
import time
from socket import getfqdn
import six
from six.moves import BaseHTTPServer
from six.moves import socketserver
from six.moves import http_client
import threading
import logging
import ssl
from xml.dom import minidom
from xml.parsers.expat import ExpatError

from . import cim_xml
from ._server import WBEMServer
from ._version import __version__
from .cim_obj import CIMInstance, CIMInstanceName, _ensure_unicode
from .cim_operations import check_utf8_xml_chars
from .cim_constants import CIM_ERR_FAILED, CIM_ERR_NOT_SUPPORTED, \
                           CIM_ERR_INVALID_PARAMETER, _statuscode2name
from .tupleparse import parse_cim
from .tupletree import dom_to_tupletree
from .exceptions import ParseError, VersionError

DEFAULT_LISTENER_PORT_HTTP = 5988
DEFAULT_LISTENER_PORT_HTTPS = 5989
DEFAULT_QUERY_LANGUAGE = 'WQL'

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
    r'([^;, ]+)' \
    r'(?:; *q=([01](?:\.[0-9]*)?))?' \
    r'(?:, *)?')
TOKEN_CHARSET_FINDALL_PATTERN = re.compile(
    r'([^;, ]+)' \
    r'(?:; *charset="?([^";, ]*)"?)?' \
    r'(?:, *)?')

__all__ = ['WBEMListener', 'callback_interface']


class ThreadedHTTPServer(socketserver.ThreadingMixIn,
                         BaseHTTPServer.HTTPServer):
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

    def do_OPTIONS(self):
        self.invalid_method()

    def do_HEAD(self):
        self.invalid_method()

    def do_GET(self):
        self.invalid_method()

    def do_PUT(self):
        self.invalid_method()

    def do_PATCH(self):
        self.invalid_method()

    def do_DELETE(self):
        self.invalid_method()

    def do_TRACE(self):
        self.invalid_method()

    def do_CONNECT(self):
        self.invalid_method()

    def do_M_POST(self):
        self.invalid_method()

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
                                 'Invalid Accept header value: %s ' \
                                 '(need text/xml, application/xml or */*)' % \
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
                                 'Invalid Accept-Charset header value: %s ' \
                                 '(need UTF-8 or *)' % \
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
                                 'Invalid Accept-Encoding header value: %s ' \
                                 '(need Identity to be acceptable)' % \
                                 accept_encoding)
            return

        # Accept-Language header check described in DSP0200.
        # Ignored, because this WBEM listener does not support multiple
        # languages, and hence any language is allowed to be returned.

        # Accept-Range header check described in DSP0200
        accept_range = self.headers.get('Accept-Range', None)
        if accept_range is not None:
            self.send_http_error(406, 'header-mismatch',
                                 'Accept-Range header is not permitted %s' % \
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
                                 'Invalid Content-Type header value: %s ' \
                                 '(need text/xml or application/xml with ' \
                                 'charset=utf-8 or empty)' % \
                                 content_type)
            return

        # Content-Encoding header check described in DSP0200
        content_encoding = self.headers.get('Content-Encoding', 'identity')
        if content_encoding.lower() != 'identity':
            self.send_http_error(406, 'header-mismatch',
                                 'Invalid Content-Encoding header value: ' \
                                 '%s (listener supports only identity)' % \
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
                self.send_http_error(400, "unsupported-dtd-version", str(exc))
            elif str(exc).startswith("Protocol"):
                self.send_http_error(400, "unsupported-protocol-version", str(exc))
            else:
                self.send_http_error(400, "unsupported-version", str(exc))
            return

        if methodname == 'ExportIndication':

            if len(params) != 1 or 'NewIndication' not in params:
                self.send_error_response(msgid, methodname,
                                         CIM_ERR_INVALID_PARAMETER,
                                         'Expecting one parameter ' \
                                         'NewIndication, got %s' % \
                                         ','.join(params.keys()))
                return

            indication_inst = params['NewIndication']

            if not isinstance(indication_inst, CIMInstance):
                self.send_error_response(msgid, methodname,
                                         CIM_ERR_INVALID_PARAMETER,
                                         'NewIndication parameter is not a CIM ' \
                                         'instance, but %r' % indication_inst)
                return

            self.server.listener._deliver_indication(indication_inst,
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
        self.log('%s: HTTP status %s; CIMError: %s, ' \
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
                        ),
                    ),
                msgid, IMPLEMENTED_PROTOCOL_VERSION),
            IMPLEMENTED_CIM_VERSION, IMPLEMENTED_DTD_VERSION)

        resp_body = resp_xml.toxml()
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
                    ),
                msgid, IMPLEMENTED_PROTOCOL_VERSION),
            IMPLEMENTED_CIM_VERSION, IMPLEMENTED_DTD_VERSION)

        resp_body = resp_xml.toxml()
        if isinstance(resp_body, six.text_type):
            resp_body = resp_body.encode("utf-8")

        http_code = 200
        self.send_response(http_code, http_client.responses.get(http_code, ''))
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(resp_body)))
        self.send_header("CIMExport", "MethodResponse")
        self.end_headers()
        self.wfile.write(resp_body)

    def parse_export_request(self, request_str):
        """Parse a CIM-XML export request message, and return
        a tuple(msgid, methodname, params).
        """

        try:
            request_dom = minidom.parseString(request_str)
        except ParseError as exc:
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
            raise ParseError(msg) # data from previous exception

        # Parse response

        tup_tree = parse_cim(dom_to_tupletree(request_dom))

        if tup_tree[0] != 'CIM':
            raise ParseError('Expecting CIM element, got %s' % \
                             tup_tree[0])
        dtd_version = tup_tree[1]['DTDVERSION']
        if not re.match(SUPPORTED_DTD_VERSION_PATTERN, dtd_version):
            raise VersionError('DTD version %s not supported. ' \
                               'Supported versions are: %s' % \
                               (dtd_version, SUPPORTED_DTD_VERSION_STR))
        tup_tree = tup_tree[2]

        if tup_tree[0] != 'MESSAGE':
            raise ParseError('Expecting MESSAGE element, got %s' % \
                             tup_tree[0])
        msgid = tup_tree[1]['ID']
        protocol_version = tup_tree[1]['PROTOCOLVERSION']
        if not re.match(SUPPORTED_PROTOCOL_VERSION_PATTERN, protocol_version):
            raise VersionError('Protocol version %s not supported. ' \
                               'Supported versions are: %s' % \
                               (protocol_version,
                                SUPPORTED_PROTOCOL_VERSION_STR))
        tup_tree = tup_tree[2]

        if tup_tree[0] != 'SIMPLEEXPREQ':
            raise ParseError('Expecting SIMPLEEXPREQ element, got %s' % \
                             tup_tree[0])
        tup_tree = tup_tree[2]

        if tup_tree[0] != 'EXPMETHODCALL':
            raise ParseError('Expecting EXPMETHODCALL element, ' \
                             'got %s' % tup_tree[0])

        methodname = tup_tree[1]['NAME']
        params = {}
        for name, obj in tup_tree[2]:
            params[name] = obj

        return (msgid, methodname, params)

    def log(self, format, args, level=logging.INFO):
        """
        This function is called for anything that needs to get logged.
        It logs to the logger of this listener.

        It is not defined in the standard handler class; our version
        has an additional `level` argument that allows to control the
        logging level in the standard Python logging support.

        Another difference is that the variable arguments are passed
        in as a tuple.
        """
        self.server.listener.logger.log(level, format, *args)

    def log_message(self, format, *args):
        """
        In the standard handler class, this function is called for anything
        that needs to get logged (e.g. from :meth:`log_request`).

        We override it in order to use our own log function.
        """
        self.log(format, args, logging.INFO)

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
        return '%s %s from %s' % \
               (self.request_version, self.command, self.client_address[0])

    def version_string(self):
        """
        Overrides the inherited method to add the pywbem listener version.
        """
        return 'PyWBEM-Listener/%s %s %s ' % \
            (__version__, self.server_version, self.sys_version)



class WBEMListener(object):
    """
    A WBEM listener.

    The listener supports starting and stopping threads that listen for
    DeliverIndication CIM-XML export messages using HTTP and/or HTTPS,
    and that pass any received indications on to registered callback
    functions.

    The listener also supports the management of subscriptions for CIM
    indications from one or more WBEM servers, including the creation and
    deletion of the necessary listener, filter and subscription instances in
    the WBEM servers.

    This class uses Python logging which needs to be configured by the user
    (see the :attr:`logger` property).
    """

    def __init__(self, host, http_port=DEFAULT_LISTENER_PORT_HTTP,
                 https_port=DEFAULT_LISTENER_PORT_HTTPS,
                 certfile=None, keyfile=None):
        """
        Parameters:

          host (:term:`string`):
            IP address or host name this listener can be reached at.

          http_port (:term:`string` or :term:`integer`):
            HTTP port this listener can be reached at.

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
            raise TypeError("Invalid type for http_port: %s" % \
                            type(http_port))

        if isinstance(https_port, six.integer_types):
            self._https_port = int(https_port)  # Convert Python 2 long to int
        elif isinstance(https_port, six.string_types):
            self._https_port = int(https_port)
        elif https_port is None:
            self._https_port = https_port
        else:
            raise TypeError("Invalid type for https_port: %s" % \
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

        self._http_server = None
        self._http_thread = None
        self._https_server = None
        self._https_thread = None

        self._logger = logging.getLogger('pywbem.listener.%s' % id(self))

        # The following dictionaries have the WBEM server URL as a key.
        self._servers = {}
        self._subscription_paths = {}
        self._dynamic_filter_paths = {}
        self._destination_path = {}

        self._callbacks = []

    def __repr__(self):
        """
        Return a representation of the :class:`~pywbem.WBEMListener` object
        with all properties and instance variables that is suitable for
        debugging.
        """
        return "%s(host=%r, http_port=%s, https_port=%s, " \
               "certfile=%r, keyfile=%r, logger=%r, _servers=%r, " \
               "_subscription_paths=%r, _dynamic_filter_paths=%r, " \
               "_destination_path=%r, _callbacks=%r)" % \
               (self.__class__.__name__, self.host, self.http_port,
                self.https_port, self.certfile, self.keyfile, self.logger,
                self._servers, self._subscription_paths,
                self._dynamic_filter_paths, self._destination_path,
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
        created via :func:`py:logging.getLogger` and is not further configured.
        As a result, this logger by default propagates its logging actions
        up to the Python root logger.

        The behavior of this logger can be changed by invoking its methods (see
        :class:`py:logging.Logger`), or by global configuration via
        :func:`py:logging.basicConfig`.

        Note that the logger needs to be set up before using the listener
        object. Missing to set up the logger typically results in a message:

        ::

            No handlers could be found for logger "pywbem.listener.NNN"

        One way to set up the logger is to use the
        :func:`py:logging.basicConfig` function, for example:

        ::

            import sys
            import logging

            logging.basicConfig(stream=sys.stderr, level=logging.WARNING)
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

        These server threads can be stopped using the :meth:`stop` method.
        They will be automatically stopped when the main thread terminates.
        """

        if self._http_port:
            if not self._http_server:
                server = ThreadedHTTPServer((self._host, self._http_port),
                                            ListenerRequestHandler)
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

    def add_server(self, server):
        """
        Add a WBEM server to the listener and register the listener with the
        server by creating an indication listener instance referencing this
        listener in the Interop namespace of the server.

        Parameters:

          server (:class:`~pywbem.WBEMServer`):
            The WBEM server.

        Returns:

            :term:`string`: The URL of the WBEM server.

        Raises:

            Exceptions raised by :class:`~pywbem.WBEMConnection`.
        """

        if not isinstance(server, WBEMServer):
            raise TypeError("server argument of add_server() must be a " \
                            "WBEMServer object")
        if server.url in self._servers:
            raise ValueError("WBEM server already known by listener: %s" % \
                             server.url)

        # We let the WBEM server use HTTP or HTTPS dependent on whether we
        # contact it using HTTP or HTTPS.
        if server.conn.url.lower().startswith('http'):
            scheme = 'http'
            port = self.http_port
        elif server.conn.url.lower().startswith('https'):
            scheme = 'https'
            port = self.https_port
        else:
            raise ValueError("Invalid scheme in server URL: %s" % \
                             server.conn.url)

        dest_url = '%s://%s:%s' % (scheme, self.host, port)
        dest_path = _create_destination(server, dest_url)

        self._servers[server.url] = server
        self._subscription_paths[server.url] = []
        self._dynamic_filter_paths[server.url] = []
        self._destination_path[server.url] = dest_path

        return server.url

    def remove_server(self, server_url):
        """
        Remove a WBEM server from the listener and unregister the listener
        from the server by deleting all indication subscriptions, dynamic
        indication filters and listener destinations in the server that were
        created by this listener.

        Parameters:

          server_url (:term:`string`):
            The URL of the WBEM server.

        Raises:

            Exceptions raised by :class:`~pywbem.WBEMConnection`.
        """

        if server_url not in self._servers:
            raise ValueError("WBEM server not known by listener: %s" % \
                             server_url)
        server = self._servers[server_url]

        # Delete any instances we recorded to be cleaned up

        if server_url in self._subscription_paths:
            paths = self._subscription_paths[server_url]
            for i, path in enumerate(paths):
                server.conn.DeleteInstance(path)
            del self._subscription_paths[server_url]

        if server_url in self._dynamic_filter_paths:
            paths = self._dynamic_filter_paths[server_url]
            for i, path in enumerate(paths):
                server.conn.DeleteInstance(path)
            del self._dynamic_filter_paths[server_url]

        if server_url in self._destination_path:
            path = self._destination_path[server_url]
            server.conn.DeleteInstance(path)
            del self._destination_path[server_url]

        # Remove server from this listener
        del self._servers[server_url]

    def add_dynamic_filter(self, server_url, source_namespace, query,
                           query_language=DEFAULT_QUERY_LANGUAGE):
        """
        Add a dynamic indication filter to a WBEM server, by creating an
        indication filter instance in the Interop namespace of the server.

        Dynamic indication filters are those that are created by clients.
        Indication filters that pre-exist in the WBEM server are termed
        *static indication filters* and cannot be created or deleted by
        clients. See :term:`DSP1054` for details about indication filters.

        Parameters:

          server_url (:term:`string`):
            The URL of the WBEM server.

          source_namespace (:term:`string`):
            Source namespace of the indication filter.

          query (:term:`string`):
            Filter query in the specified query language.

          query_language (:term:`string`):
            Query language for the specified filter query.

            Examples: 'WQL', 'DMTF:CQL'.

        Returns:

            :class:`~pywbem.CIMInstanceName`: The instance path of the
            indication filter instance.

        Raises:

            Exceptions raised by :class:`~pywbem.WBEMConnection`.
        """
        if server_url not in self._servers:
            raise ValueError("WBEM server not known by listener: %s" % \
                             server_url)
        server = self._servers[server_url]
        filter_path = _create_filter(server, source_namespace, query,
                                     query_language)
        self._dynamic_filter_paths[server_url].append(filter_path)
        return filter_path

    def remove_dynamic_filter(self, server_url, filter_path):
        """
        Remove a dynamic indication filter from a WBEM server, by deleting an
        indication filter instance in the WBEM server.

        The indication filter must be a dynamic indication filter that has been
        created by this listener, and there must not exist any subscriptions
        referencing the filter.

        Parameters:

          server_url (:term:`string`):
            The URL of the WBEM server.

          filter_path (:class:`~pywbem.CIMInstanceName`):
            Instance path of the indication filter instance in the WBEM
            server.

        Raises:

            Exceptions raised by :class:`~pywbem.WBEMConnection`.
        """
        if server_url not in self._servers:
            raise ValueError("WBEM server not known by listener: %s" % \
                             server_url)
        server = self._servers[server_url]
        if server_url in self._dynamic_filter_paths:
            paths = self._dynamic_filter_paths[server_url]
            for i, path in enumerate(paths):
                if path == filter_path:
                    server.conn.DeleteInstance(path)
                    del paths[i]
                    break

    def get_dynamic_filters(self, server_url):
        """
        Return the dynamic indication filters in a WBEM server that have been
        created by this listener.

        Parameters:

          server_url (:term:`string`):
            The URL of the WBEM server.

        Returns:

            List of :class:`~pywbem.CIMInstanceName`: The dynamic indication
            filter instance paths.

        Raises:

            Exceptions raised by :class:`~pywbem.WBEMConnection`.
        """
        if server_url not in self._servers:
            raise ValueError("WBEM server not known by listener: %s" % \
                             server_url)
        return self._dynamic_filter_paths[server_url]

    def get_filters(self, server_url):
        """
        Return all (dynamic and static) indication filters in a WBEM server.

        Parameters:

          server_url (:term:`string`):
            The URL of the WBEM server.

        Returns:

          List of :class:`~pywbem.CIMInstanceName`: The indication filter
          instance paths.

        Raises:

            Exceptions raised by :class:`~pywbem.WBEMConnection`.
        """
        if server_url not in self._servers:
            raise ValueError("WBEM server not known by listener: %s" % \
                             server_url)
        server = self._servers[server_url]
        return server.conn.EnumerateInstanceNames('CIM_IndicationFilter',
                                                  namespace=server.interop_ns)

    def add_subscription(self, server_url, filter_path):
        """
        Add a subscription to a WBEM server for particular set of indications
        defined by an indication filter, by creating an indication subscription
        instance in the Interop namespace of the server, that links the
        specified indication filter with the listener destination in the
        server that references this listener.

        The indication filter can be a dynamic filter created specifically for
        this listener via :meth:`add_dynamic_filter`, or a static filter that
        pre-exists in the WBEM server. Filters defined in the WBEM server can
        be retrieved via :meth:`get_filters`.

        Upon successful return of this method, the subscription is active.

        Parameters:

          server_url (:term:`string`):
            The URL of the WBEM server.

          filter_path (:class:`~pywbem.CIMInstanceName`):
            Instance path of the indication filter instance in the WBEM
            server that specifies the indications to be sent.

        Returns:

            :class:`~pywbem.CIMInstanceName`: Instance path of the indication
            subscription instance.

        Raises:

            Exceptions raised by :class:`~pywbem.WBEMConnection`.
        """
        if server_url not in self._servers:
            raise ValueError("WBEM server not known by listener: %s" % \
                             server_url)
        server = self._servers[server_url]
        dest_path = self._destination_path[server_url]
        sub_path = _create_subscription(server, dest_path, filter_path)
        self._subscription_paths[server_url].append(sub_path)
        return sub_path

    def remove_subscription(self, server_url, sub_path):
        """
        Remove an indication subscription from a WBEM server, by deleting an
        indication subscription instance in the server.

        Parameters:

          server_url (:term:`string`):
            The URL of the WBEM server.

          sub_path (:class:`~pywbem.CIMInstanceName`):
            Instance path of the indication subscription instance in the WBEM
            server.

        Raises:

            Exceptions raised by :class:`~pywbem.WBEMConnection`.
        """
        if server_url not in self._servers:
            raise ValueError("WBEM server not known by listener: %s" % \
                             server_url)
        server = self._servers[server_url]
        if server_url in self._subscription_paths:
            sub_paths = self._subscription_paths[server_url]
            for i, path in enumerate(sub_paths):
                if path == sub_path:
                    server.conn.DeleteInstance(path)
                    del sub_paths[i]
                    break

    def get_subscriptions(self, server_url):
        """
        Return the indication subscriptions in a WBEM server that have been
        created by this listener.

        Parameters:

          server_url (:term:`string`):
            The URL of the WBEM server.

        Returns:

            List of :class:`~pywbem.CIMInstanceName`: The indication
            subscription instance paths.

        Raises:

            Exceptions raised by :class:`~pywbem.WBEMConnection`.
        """
        if server_url not in self._servers:
            raise ValueError("WBEM server not known by listener: %s" % \
                             server_url)
        return self._subscription_paths[server_url]

    def _deliver_indication(self, indication, host):
        """
        This function is called by the listener threads for each received
        indication.

        It delivers the indication to all callback functions that have been
        added to the listener.

        Parameters:

          indication (pywbem.CIMIndication):
            Representation of the CIM indication to be delivered.

          host (:term:`string`):
            Host name or IP address of WBEM server sending the indication.
        """
        for callback in self._callbacks:
            callback(indication, host)

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


def _create_destination(server, dest_url):
    """
    Create a listener destination instance in the Interop namespace of a
    WBEM server and return its instance path.

    Parameters:

      server (:class:`~pywbem.WBEMServer`):
        Identifies the WBEM server.

      dest_url (:term:`string`):
        URL of the listener that is used by the WBEM server to send any
        indications to.

        The URL scheme (e.g. http/https) determines whether the WBEM server
        uses HTTP or HTTPS for sending the indication. Host and port in the
        URL specify the target location to be used by the WBEM server.

    Returns:

        :class:`~pywbem.CIMInstanceName`: The instance path of the created
        instance.

    Raises:

        Exceptions raised by :class:`~pywbem.WBEMConnection`.
    """

    classname = 'CIM_ListenerDestinationCIMXML'

    dest_path = CIMInstanceName(classname)
    dest_path.classname = classname
    dest_path.namespace = server.interop_ns

    dest_inst = CIMInstance(classname)
    dest_inst.path = dest_path
    dest_inst['CreationClassName'] = classname
    dest_inst['SystemCreationClassName'] = 'CIM_ComputerSystem'
    dest_inst['SystemName'] = getfqdn()
    dest_inst['Name'] = 'cimlistener%d' % time.time()
    dest_inst['Destination'] = dest_url

    dest_path = server.conn.CreateInstance(dest_inst)
    return dest_path

def _create_filter(server, source_namespace, query, query_language):
    """
    Create a dynamic indication filter instance in the Interop namespace
    of a WBEM server and return its instance path.

    Parameters:

      server (:class:`~pywbem.WBEMServer`):
        Identifies the WBEM server.

      source_namespace (:term:`string`):
        Source namespace of the indication filter.

      query (:term:`string`):
        Filter query in the specified query language.

      query_language (:term:`string`):
        Query language for the specified filter query.

        Examples: 'WQL', 'DMTF:CQL'.

    Returns:

        :class:`~pywbem.CIMInstanceName`: The instance path of the created
        instance.

    Raises:

        Exceptions raised by :class:`~pywbem.WBEMConnection`.
    """

    classname = 'CIM_IndicationFilter'

    filter_path = CIMInstanceName(classname)
    filter_path.classname = classname
    filter_path.namespace = server.interop_ns

    filter_inst = CIMInstance(classname)
    filter_inst.path = filter_path
    filter_inst['CreationClassName'] = classname
    filter_inst['SystemCreationClassName'] = 'CIM_ComputerSystem'
    filter_inst['SystemName'] = getfqdn()
    filter_inst['Name'] = 'cimfilter%d' % time.time()
    filter_inst['SourceNamespace'] = source_namespace
    filter_inst['Query'] = query
    filter_inst['QueryLanguage'] = query_language

    filter_path = server.conn.CreateInstance(filter_inst)
    return filter_path

def _create_subscription(server, dest_path, filter_path):
    """
    Create an indication subscription instance in the Interop namespace of
    a WBEM server and return its instance path.

    Parameters:

      server (:class:`~pywbem.WBEMServer`):
        Identifies the WBEM server.

      dest_path (:class:`~pywbem.CIMInstanceName`):
        Instance path of the listener destination instance in the WBEM
        server that references this listener.

      filter_path (:class:`~pywbem.CIMInstanceName`):
        Instance path of the indication filter instance in the WBEM
        server that specifies the indications to be sent.

    Returns:

        :class:`~pywbem.CIMInstanceName`: The instance path of the created
        instance.

    Raises:

        Exceptions raised by :class:`~pywbem.WBEMConnection`.
    """

    classname = 'CIM_IndicationSubscription'

    sub_path = CIMInstanceName(classname)
    sub_path.classname = classname
    sub_path.namespace = server.interop_ns

    sub_inst = CIMInstance(classname)
    sub_inst.path = sub_path
    sub_inst['Filter'] = filter_path
    sub_inst['Handler'] = dest_path

    sub_path = server.conn.CreateInstance(sub_inst)
    return sub_path


def callback_interface(indication, host):
    # pylint: disable=unused-argument
    """
    Interface of a function that is provided by the user of the API and
    that will be called by the listener for each received CIM indication.

    Parameters:

      indication (:class:`~pywbem.CIMInstance`):
        Representation of the CIM indication that has been received.
        Its `path` component is not set.

      host (:term:`string`):
        Host name or IP address of WBEM server sending the indication.

    Raises:
      TBD
    """
    raise NotImplementedError

