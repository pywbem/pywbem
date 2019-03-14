#
# (C) Copyright 2003-2005 Hewlett-Packard Development Company, L.P.
# (C) Copyright 2006-2007 Novell, Inc.
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
# Author: Tim Potter <tpot@hp.com>
# Author: Martin Pool <mbp@hp.com>
# Author: Bart Whiteley <bwhiteley@suse.de>
# Author: Ross Peoples <ross.peoples@gmail.com>
#

'''
Send HTTP/HTTPS requests to a WBEM server.

This module does not know anything about the fact that the data being
transferred in the HTTP request and response is CIM-XML.  It is up to the
caller to provide CIM-XML formatted input data and interpret the result data
as CIM-XML.
'''

from __future__ import print_function, absolute_import

import re
import os
import sys
import errno
import socket
import getpass
from stat import S_ISSOCK
import platform
import base64
import threading
from datetime import datetime
import warnings

import six
from six.moves import http_client as httplib
from six.moves import urllib

from .cim_obj import CIMClassName, CIMInstanceName
from .exceptions import ConnectionError, AuthError, TimeoutError, HTTPError
from ._warnings import ToleratedServerIssueWarning
from ._utils import _ensure_unicode, _ensure_bytes, _format

_ON_RTD = os.environ.get('READTHEDOCS', None) == 'True'

if six.PY2 and not _ON_RTD:  # RTD has no swig to install M2Crypto
    # pylint: disable=wrong-import-order
    from M2Crypto import SSL           # pylint: disable=wrong-import-position
    from M2Crypto.Err import SSLError  # pylint: disable=wrong-import-position
    _HAVE_M2CRYPTO = True
    # pylint: disable=invalid-name
    SocketErrors = (socket.error, socket.sslerror)
else:
    import ssl as SSL                  # pylint: disable=wrong-import-position
    # pylint: disable=wrong-import-position
    from ssl import SSLError, CertificateError
    _HAVE_M2CRYPTO = False
    # pylint: disable=invalid-name
    SocketErrors = (socket.error,)

__all__ = ['DEFAULT_CA_CERT_PATHS']


def create_pywbem_ssl_context():
    """ Create an SSL context based on what is commonly accepted as the
        required limitations. This code attempts to create the same context for
        Python 2 and Python 3 except for the ciphers
        This list is based on what is currently defined in the Python SSL
        module create_default_context function
        This includes:

            * Disallow SSLV2 and SSLV3
            * Allow TLSV1 TLSV1.1, TLSV1.2
            * No compression
            * Single DH Use and Single ECDH use
        cacerts info is set independently so is not part of our context setter.
    """

    if six.PY2:
        context = SSL.Context('sslv23')
        # Many of the flags are not in the M2Crypto source so they were taken
        # from OpenSSL SSL.h module as flags.
        SSL.context.set_options(SSL.SSL_OP_NO_SSLv2 |
                                0x02000000 |  # OP_NO_SSLV3
                                0x00020000 |  # OP_NO_COMPRESSION
                                0x00100000 |  # OP_SINGLE_DH_USE
                                0x00400000 |  # OP_CIPHER_SERVER_PREFERENCE
                                0x00080000)   # OP_SINGLE_ECDH_USE
    else:
        # The choice for the Python SSL module is whether to use the
        # create_default directly and possibly have different limits depending
        # on which version of Python you use or to set the attributes
        # directly based on a currently used SSL
        context = SSL.create_default_context(purpose=SSL.Purpose.CLIENT_AUTH)

        # Variable settings per SSL create_default_context. These are what
        # the function above sets for Python 3.4
        # context = SSLContext(PROTOCOL_SSLv23)
        # context.options |= OP_NO_SSLv2
        # context.options |= OP_NO_SSLv3
        # context.options |= getattr(SSL, "OP_NO_COMPRESSION", 0)
        # context.options |= getattr(SSL, "OP_CIPHER_SERVER_PREFERENCE", 0)
        # context.options |= getattr(SSL, "OP_SINGLE_DH_USE", 0)
        # context.options |= getattr(SSL, "OP_SINGLE_ECDH_USE", 0)
        # context.set_ciphers(_RESTRICTED_SERVER_CIPHERS)

    return context


DEFAULT_PORT_HTTP = 5988        # default port for http
DEFAULT_PORT_HTTPS = 5989       # default port for https


#: Default directory paths to be used when the `ca_certs` parameter of
#: :class:`~pywbem.WBEMConnection` is `None`. The first existing directory is
#: used as a default for that parameter.
#: Note that these default directory paths only work on some Linux
#: distributions.
DEFAULT_CA_CERT_PATHS = \
    ['/etc/pki/ca-trust/extracted/openssl/ca-bundle.trust.crt',
     '/etc/ssl/certs', '/etc/ssl/certificates']


def get_default_ca_cert_paths():
    """Return the list of default certificate paths defined for this
       system environment. This is the list of directories that
       should be searched to find a directory that contains
       certificates possibly suitable for the ssl ca_certs parameter
       in SSL connections.
    """
    return DEFAULT_CA_CERT_PATHS


class HTTPTimeout(object):  # pylint: disable=too-few-public-methods
    """HTTP timeout class that is a context manager (for use by 'with'
    statement).

    Usage:

      ::

        with HTTPTimeout(timeout, http_conn, conn_id):
            ... operations using http_conn ...

    If the timeout expires, the socket of the HTTP connection is shut down.
    Once the http operations return as a result of that or for other reasons,
    the exit handler of this class raises a :exc:`~pywbem.TimeoutError`
    exception in the thread that executed the ``with`` statement.
    """

    def __init__(self, timeout, http_conn, conn_id=None):
        """Initialize the HTTPTimeout object.

        :Parameters:

          timeout (:term:`number`):
            Timeout in seconds, `None` means no timeout.

          http_conn (`httplib.HTTPBaseConnection` or subclass):
            The connection that is to be stopped when the timeout expires.

          conn_id (:term:`connection id`): Connection ID of the WBEM connection
            in whose context the error happened. `None` if the error did not
            happen in context of any connection, or if the connection context
            was not known.
        """

        self._timeout = timeout
        self._http_conn = http_conn
        self._conn_id = conn_id

        # time in seconds after which a retry of socket shutdown is scheduled
        # if the socket is not yet connected when timeout expires
        self._retrytime = 5

        self._timer = None      # the timer object
        self._ts1 = None        # timestamp when timer was started
        self._shutdown = None   # flag indicating timer handler shutdown socket
        return

    def __enter__(self):
        if self._timeout is not None:
            self._timer = threading.Timer(self._timeout,
                                          HTTPTimeout.timer_expired, [self])
            self._timer.start()
            self._ts1 = datetime.now()
        self._shutdown = False
        return

    def __exit__(self, exc_type, exc_value, traceback):
        if self._timeout is not None:
            self._timer.cancel()
            if self._shutdown:
                # If the timer handler has shut down the socket, we
                # want to make that known, and override any other
                # exceptions that may be pending.
                ts2 = datetime.now()
                duration = ts2 - self._ts1
                duration_sec = (float(duration.microseconds) / 1000000) + \
                    duration.seconds + (duration.days * 24 * 3600)
                raise TimeoutError(
                    _format("The client timed out and closed the socket "
                            "after {0:.0f} s.", duration_sec),
                    conn_id=self._conn_id)
        return False  # re-raise any other exceptions

    def timer_expired(self):
        """
        This method is invoked in context of the timer thread, so we cannot
        directly throw exceptions (we can, but they would be in the wrong
        thread), so instead we shut down the socket of the connection.
        When the timeout happens in early phases of the connection setup,
        there is no socket object on the HTTP connection yet, in that case
        we retry after the retry duration, indefinitely.
        So we do not guarantee in all cases that the overall operation times
        out after the specified timeout.
        """
        if self._http_conn.sock is not None:
            self._shutdown = True
            self._http_conn.sock.shutdown(socket.SHUT_RDWR)
        else:
            # Retry after the retry duration
            self._timer.cancel()
            self._timer = threading.Timer(self._retrytime,
                                          HTTPTimeout.timer_expired, [self])
            self._timer.start()


def parse_url(url, allow_defaults=True):
    """Return a tuple (`host`, `port`, `ssl`) from the URL specified in the
    `url` parameter.

    The returned `ssl` item is a boolean indicating the use of SSL, and is
    recognized from the URL scheme (http vs. https). If none of these schemes
    is specified in the URL, the returned value defaults to False
    (non-SSL/http).

    The returned `port` item is the port number, as an integer. If there is
    no port number specified in the URL, the returned value defaults to 5988
    for non-SSL/http, and to 5989 for SSL/https.

    The returned `host` item is the host portion of the URL, as a string.
    The host portion may be specified in the URL as a short or long host name,
    dotted IPv4 address, or bracketed IPv6 address with or without zone index
    (aka scope ID). An IPv6 address is converted from the RFC6874 URI syntax
    to the RFC4007 text representation syntax before being returned, by
    removing the brackets and converting the zone index (if present) from
    "-eth0" to "%eth0".

    Examples for valid URLs can be found in the test program
    `tests/unittest/pywbem/test_cim_http.py`.

    Parameters:

      url:

      allow_defaults - If `True` (default) allow defaults for scheme and
        port. If `False`, raise exception for invalid or missing scheme or
        port.

    Returns:

      tuple of (`host`, `port`, `ssl`)

    Raises:

      ValueError: Exception raised if allow_defaults = False and either
        scheme or port are invalid or missing
    """

    default_ssl = False             # default SSL use (for no or unknown scheme)

    # Look for scheme.
    matches = re.match(r"^(https?)://(.*)$", url, re.I)
    _scheme = None
    if matches:
        _scheme = matches.group(1).lower()
        hostport = matches.group(2)
        ssl = (_scheme == 'https')
    else:
        if not allow_defaults:
            raise ValueError(
                _format("URL {0!A} invalid scheme component", url))
        # The URL specified no scheme (or a scheme other than the expected
        # schemes, but we don't check)
        ssl = default_ssl
        hostport = url

    # Remove trailing path segments, if any.
    # Having URL components other than just slashes (e.g. '#' or '?') is not
    # allowed (but we don't check).
    result = hostport.find("/")
    if result >= 0:
        hostport = hostport[0:result]

    # Look for port.
    # This regexp also works for (colon-separated) IPv6 addresses, because they
    # must be bracketed in a URL.
    matches = re.search(r":([0-9]+)$", hostport)
    if matches:
        host = hostport[0:matches.start(0)]
        port = int(matches.group(1))
    else:
        if not allow_defaults:
            raise ValueError(
                _format("URL {0!A} invalid host/port component", url))
        host = hostport
        port = DEFAULT_PORT_HTTPS if ssl else DEFAULT_PORT_HTTP

    # Reformat IPv6 addresses from RFC6874 URI syntax to RFC4007 text
    # representation syntax:
    #   - Remove the brackets.
    #   - Convert the zone index (aka scope ID) from "-eth0" to "%eth0".
    # Note on the regexp below: The first group needs the '?' after '.+' to
    # become non-greedy; in greedy mode, the optional second group would never
    # be matched.
    matches = re.match(r"^\[(.+?)(?:-(.+))?\]$", host)
    if matches:
        # It is an IPv6 address
        host = matches.group(1)
        if matches.group(2) is not None:
            # The zone index is present
            host += "%" + matches.group(2)

    return host, port, ssl


def get_default_ca_certs():
    """
    Try to find out system path with ca certificates. This path is cached and
    returned. If no path is found out, None is returned.
    """
    # pylint: disable=protected-access
    if not hasattr(get_default_ca_certs, '_path'):
        for path in get_default_ca_cert_paths():
            if os.path.exists(path):
                get_default_ca_certs._path = path
                break
        else:
            get_default_ca_certs._path = None
    return get_default_ca_certs._path


# pylint: disable=too-many-branches,too-many-statements,too-many-arguments
def wbem_request(url, data, creds, cimxml_headers=None, debug=False, x509=None,
                 verify_callback=None, ca_certs=None,
                 no_verification=False, timeout=None, recorders=None,
                 conn_id=None):
    # pylint: disable=too-many-arguments,unused-argument
    # pylint: disable=too-many-locals
    """
    Send an HTTP or HTTPS request to a WBEM server and return the response.

    This function uses Python's built-in `httplib` module.

    Parameters:

      url (:term:`string`):
        URL of the WBEM server (e.g. ``"https://10.11.12.13:6988"``).
        For details, see the `url` parameter of
        :meth:`~pywbem.WBEMConnection.__init__`.

      data (:term:`string`):
        The CIM-XML formatted data to be sent as a request to the WBEM server.

      creds:
        Credentials for authenticating with the WBEM server.
        For details, see the `creds` parameter of
        :meth:`~pywbem.WBEMConnection.__init__`.

      cimxml_headers (:term:`py:iterable` of tuple(string,string)):
        Where each tuple contains: header name, header value.

        CIM-XML extension header fields for the request. The header value
        is a string (unicode or binary) that is not encoded, and the two-step
        encoding required by DSP0200 is performed inside of this function.

        A value of `None` is treated like an empty iterable.

      debug (:class:`py:bool`):
        Boolean indicating whether to create debug information (ignored).

      x509:
        Used for HTTPS with certificates.
        For details, see the `x509` parameter of
        :meth:`~pywbem.WBEMConnection.__init__`.

      verify_callback:
        Used for HTTPS with certificates but only for python 2. Ignored with
        python 3 since the  python 3 ssl implementation does not implement
        any callback mechanism so setting this variable gains the
        user nothing.

        For details, see the `verify_callback` parameter of
        :meth:`~pywbem.WBEMConnection.__init__`.

      ca_certs:
        Used for HTTPS with certificates.
        For details, see the `ca_certs` parameter of
        :meth:`~pywbem.WBEMConnection.__init__`.

      no_verification:
        Used for HTTPS with certificates.
        For details, see the `no_verification` parameter of
        :meth:`~pywbem.WBEMConnection.__init__`.

      timeout (:term:`number`):
        Timeout in seconds, for requests sent to the server. If the server did
        not respond within the timeout duration, the socket for the connection
        will be closed, causing a :exc:`~pywbem.TimeoutError` to be raised.
        A value of `None` means there is no timeout.
        A value of `0` means the timeout is very short, and does not really
        make any sense.
        Note that not all situations can be handled within this timeout, so
        for some issues, this method may take longer to raise an exception.

      recorders (List of :class:`~pywbem.BaseOperationRecorder`):
        List of enabled operation recorders, into which the HTTP request and
        HTTP response will be staged as attributes.

      conn_id (:term:`string`)
        string that uniquely defines a connection.  Used as part of any
        logs created.

    Returns:

        Tuple containing:

            The CIM-XML formatted response data from the WBEM server, as a
            :term:`byte string` object.

            The server response time in seconds as floating point number if
            this data was received from the server. If no data returned
            from server `None` is returned.

    Raises:

        :exc:`~pywbem.AuthError`
        :exc:`~pywbem.ConnectionError`
        :exc:`~pywbem.TimeoutError`
        :exc:`~pywbem.HTTPError`
    """

    class HTTPBaseConnection:  # pylint: disable=no-init
        """ Common base for specific connection classes. Implements
            the send method
        """
        # pylint: disable=too-few-public-methods
        def send(self, strng):
            """
            A copy of `httplib.HTTPConnection.send()`, with these fixes:

            * We fix the problem that the connection gets closed upon error
              32 (EPIPE), by not doing that (If the connection gets closed,
              getresponse() fails). This problem was reported as Python issue
              #5542, and the same fix we do here was integrated into Python
              2.7 and 3.1 or 3.2, but not into Python 2.6 (so we still need
              our fix here).

            * Ensure that the data are bytes, not unicode.
            """
            # NOTE: The attributes come from the httplib mixins in the
            # subclasses so the disable=no-member hides worthless warnings.
            if self.sock is None:  # pylint: disable=no-member
                if self.auto_open:  # pylint: disable=no-member
                    self.connect()  # pylint: disable=no-member
                else:
                    # We raise the same httplib exception the original function
                    # raises. Our caller will handle it.
                    raise httplib.NotConnected()
            if self.debuglevel > 0:  # pylint: disable=no-member
                print(_format("send: {0!A}", strng))
            blocksize = 8192
            if hasattr(strng, 'read') and not isinstance(strng, list):
                if self.debuglevel > 0:  # pylint: disable=no-member
                    print("sendIng a read()able")
                data = strng.read(blocksize)
                while data:
                    # pylint: disable=no-member
                    self.sock.sendall(_ensure_bytes(data))
                    data = strng.read(blocksize)
            else:
                # For unknown reasons, the pylint disable must be on same line:
                self.sock.sendall(_ensure_bytes(strng))  # noqa: E501 pylint: disable=no-member

    class HTTPConnection(HTTPBaseConnection, httplib.HTTPConnection):
        """ Execute client connection without ssl using httplib. """
        def __init__(self, host, port=None, timeout=None):
            # Note: We do not use strict=True in the following call, because it
            # is not clear what side effects that would have, and if no status
            # line comes back we'll certainly find out about that.
            httplib.HTTPConnection.__init__(self, host=host, port=port,
                                            timeout=timeout)

    class HTTPSConnection(HTTPBaseConnection, httplib.HTTPSConnection):
        """ Execute client connection with ssl using httplib."""
        # pylint: disable=R0913,too-many-arguments
        def __init__(self, host, port=None, key_file=None, cert_file=None,
                     ca_certs=None, verify_callback=None, timeout=None):
            # Note: We do not use strict=True in the following call, because it
            # is not clear what side effects that would have, and if no status
            # line comes back we'll certainly find out about that.
            httplib.HTTPSConnection.__init__(self, host=host, port=port,
                                             key_file=key_file,
                                             cert_file=cert_file,
                                             timeout=timeout)
            self.ca_certs = ca_certs
            self.verify_callback = verify_callback
            # issue 297: Verify_callback is  not used in py 3
            if verify_callback is not None and six.PY3:
                warnings.warn("The 'verify_callback' parameter was specified "
                              "on WBEMConnection() but is not used on "
                              "Python 3", UserWarning)

        def connect(self):
            # pylint: disable=too-many-branches
            """Connect to a host on a given (SSL) port."""

            # Connect for M2Crypto ssl package
            if _HAVE_M2CRYPTO:
                # Calling httplib.HTTPSConnection.connect(self) does not work
                # because of its ssl.wrap_socket() call. So we copy the code of
                # that connect() method modulo the ssl.wrap_socket() call.

                # Another change is that we do not pass the timeout value
                # on to the socket call, because that does not work with
                # M2Crypto.

                if sys.version_info[0:2] >= (2, 7):
                    # the source_address parameter was added in Python 2.7
                    self.sock = socket.create_connection(
                        (self.host, self.port), None, self.source_address)
                else:
                    self.sock = socket.create_connection(
                        (self.host, self.port), None)

                # Removed code for tunneling support.

                # End of code from httplib.HTTPSConnection.connect(self).

                ctx = SSL.Context('sslv23')

                if self.cert_file:
                    ctx.load_cert(self.cert_file, keyfile=self.key_file)
                if self.ca_certs:
                    ctx.set_verify(
                        SSL.verify_peer | SSL.verify_fail_if_no_peer_cert,
                        depth=9, callback=verify_callback)
                    if os.path.isdir(self.ca_certs):
                        ctx.load_verify_locations(capath=self.ca_certs)
                    else:
                        ctx.load_verify_locations(cafile=self.ca_certs)
                try:
                    self.sock = SSL.Connection(ctx, self.sock)

                    # Below is a body of SSL.Connection.connect() method
                    # except for the first line (socket connection).

                    # Removed code for tunneling support.

                    # Setting the timeout on the input socket does not work
                    # with M2Crypto, with such a timeout set it calls a
                    # different low level function (nbio instead of bio)
                    # that does not work. The symptom is that reading the
                    # response returns None.
                    # Therefore, we set the timeout at the level of the outer
                    # M2Crypto socket object.
                    # pylint: disable=using-constant-test

                    if self.timeout is not None:
                        self.sock.set_socket_read_timeout(
                            SSL.timeout(self.timeout))
                        self.sock.set_socket_write_timeout(
                            SSL.timeout(self.timeout))

                    self.sock.addr = (self.host, self.port)
                    self.sock.setup_ssl()
                    self.sock.set_connect_state()
                    ret = self.sock.connect_ssl()
                    if self.ca_certs:
                        check = getattr(self.sock, 'postConnectionCheck',
                                        self.sock.clientPostConnectionCheck)
                        if check is not None:
                            if not check(self.sock.get_peer_cert(), self.host):
                                raise ConnectionError(
                                    'SSL error: post connection check failed',
                                    conn_id=conn_id)
                    return ret

                except (SSLError, SSL.SSLError,
                        SSL.Checker.SSLVerificationError) as arg:
                    raise ConnectionError(
                        _format("SSL error {0}: {1}", arg.__class__, arg),
                        conn_id=conn_id)

            # Connect using Python SSL module
            else:
                # Setup the socket context

                # Note: PROTOCOL_SSLv23 allows talking to servers with TLS but
                # not with SSL. For details, see the table in
                # https://docs.python.org/3/library/ssl.html#ssl.wrap_socket
                # Within the defined set of protocol versions, SSLv23 selects
                # the highest protocol version that both client and server
                # support.
                # Issue #893: Consider the use of default_context()
                ctx = SSL.SSLContext(SSL.PROTOCOL_SSLv23)

                if self.cert_file:
                    ctx.load_cert(self.cert_file, keyfile=self.key_file)
                if self.ca_certs:
                    # We need to use CERT_REQUIRED to require that the server
                    # certificate is being validated by the client (against the
                    # certificates in ca_certs).
                    ctx.verify_mode = SSL.CERT_REQUIRED
                    if os.path.isdir(self.ca_certs):
                        ctx.load_verify_locations(capath=self.ca_certs)
                    else:
                        ctx.load_verify_locations(cafile=self.ca_certs)
                    ctx.check_hostname = True
                else:
                    ctx.check_hostname = False
                    ctx.verify_mode = SSL.CERT_NONE

                # setup the socket
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(self.timeout)

                try:
                    self.sock = ctx.wrap_socket(sock,
                                                server_hostname=self.host)
                    return self.sock.connect((self.host, self.port))

                except SSLError as arg:
                    raise ConnectionError(
                        _format("SSL error {0}: {1}", arg.__class__, arg),
                        conn_id=conn_id)
                except CertificateError as arg:
                    raise ConnectionError(
                        _format("SSL certificate error {0}: {1}",
                                arg.__class__, arg),
                        conn_id=conn_id)

    class FileHTTPConnection(HTTPBaseConnection, httplib.HTTPConnection):
        """Execute client connection based on a unix domain socket. """

        def __init__(self, uds_path):
            httplib.HTTPConnection.__init__(self, host='localhost')
            self.uds_path = uds_path

        def connect(self):
            try:
                socket_af = socket.AF_UNIX
            except AttributeError:
                raise ConnectionError(
                    _format("file URLs not supported on {0} platform due to "
                            "missing AF_UNIX support", platform.system()),
                    conn_id=conn_id)
            self.sock = socket.socket(socket_af, socket.SOCK_STREAM)
            self.sock.connect(self.uds_path)

    if not cimxml_headers:
        cimxml_headers = []

    host, port, use_ssl = parse_url(_ensure_unicode(url))

    key_file = None
    cert_file = None

    if use_ssl and x509 is not None:
        cert_file = x509.get('cert_file')
        key_file = x509.get('key_file')

    local_auth_header = None

    # Make sure the data parameter is converted to a UTF-8 encoded byte string.
    # This is important because according to RFC2616, the Content-Length HTTP
    # header must be measured in Bytes (and the Content-Type header will
    # indicate UTF-8).
    data = _ensure_bytes(data)

    data = b'<?xml version="1.0" encoding="utf-8" ?>\n' + data

    # Note that certs get passed even if ca_certs is None and
    # no_verification=False
    if not no_verification and ca_certs is None:
        ca_certs = get_default_ca_certs()
    elif no_verification:
        ca_certs = None

    local = False
    svr_resp_time = None
    if use_ssl:
        client = HTTPSConnection(host=host,
                                 port=port,
                                 key_file=key_file,
                                 cert_file=cert_file,
                                 ca_certs=ca_certs,
                                 verify_callback=verify_callback,
                                 timeout=timeout)
    else:
        if url.startswith('http'):
            client = HTTPConnection(host=host, port=port, timeout=timeout)
        else:
            if url.startswith('file:'):
                url_ = url[5:]
            else:
                url_ = url
            try:
                status = os.stat(url_)
                if S_ISSOCK(status.st_mode):
                    client = FileHTTPConnection(url_)
                    local = True
                else:
                    raise ConnectionError(
                        _format("File URL is not a socket: {0!A}", url),
                        conn_id=conn_id)
            except OSError as exc:
                raise ConnectionError(
                    _format("Error with file URL {0!A}: {1}", url, exc),
                    conn_id=conn_id)

    locallogin = None
    if host in ('localhost', 'localhost6', '127.0.0.1', '::1'):
        local = True
    if local:
        try:
            locallogin = getpass.getuser()
        except (KeyError, ImportError):
            locallogin = None

    method = 'POST'
    target = '/cimom'

    if recorders:
        for recorder in recorders:
            recorder.stage_http_request(conn_id, 11, url, target, method,
                                        dict(cimxml_headers), data)

            # We want clean response data when an exception is raised before
            # the HTTP response comes in:
            recorder.stage_http_response1(conn_id, None, None, None, None)
            recorder.stage_http_response2(None)

    with HTTPTimeout(timeout, client, conn_id):

        try_limit = 5  # Number of tries with authentication challenges.

        for num_tries in range(0, try_limit):  # pylint: disable=unused-variable

            client.putrequest(method, target)

            standard_headers = [
                ('Content-type', 'application/xml; charset="utf-8"'),
                ('Content-length', str(len(data))),
            ]
            if local_auth_header:
                standard_headers.append(local_auth_header)
            elif creds is not None:
                auth = _format("{0}:{1}", creds[0], creds[1])
                auth64 = _ensure_unicode(base64.b64encode(
                    _ensure_bytes(auth))).replace('\n', '')
                standard_headers.append(
                    ('Authorization', 'Basic {0}'.format(auth64)))
            elif locallogin is not None:
                standard_headers.append(
                    ('PegasusAuthorization', 'Local "{0}"'.format(locallogin)))

            # Note: RFC2616 does not permit the use percent-escaping for
            # the standard header fields. It allows octets (except CTL) for
            # the field values. DSP0200 requires the use of UTF-8 encoding
            # followed by percent-encoding for its extension headers.
            # Therefore, we don't encode the standard headers but do encode
            # the CIM-XML extension headers.
            for n, v in standard_headers:
                client.putheader(n, v)
            for n, v in cimxml_headers:
                v = _ensure_unicode(v)
                v = urllib.parse.quote(v)
                client.putheader(n, v)

            try:

                # See RFC 2616 section 8.2.2
                # An http server is allowed to send back an error (presumably
                # a 401), and close the connection without reading the entire
                # request.  A server may do this to protect itself from a DoS
                # attack.
                #
                # If the server closes the connection during our send(), we
                # will either get a socket exception 104 (ECONNRESET:
                # connection reset), or a socket exception 32 (EPIPE: broken
                # pipe).  In either case, thanks to our fixed HTTPConnection
                # classes, we'll still be able to retrieve the response so
                # that we can read and respond to the authentication challenge.
                try:
                    # endheaders() is the first method in this sequence that
                    # actually sends something to the server (using send()).
                    client.endheaders()
                    client.send(data)
                except SocketErrors as exc:
                    if exc.args[0] == errno.ECONNRESET:
                        warnings.warn("Ignoring socket error ECONNRESET "
                                      "(connection reset), continuing with "
                                      "reading the response.",
                                      ToleratedServerIssueWarning,
                                      stacklevel=2)
                        # continue with reading response
                    elif exc.args[0] == errno.EPIPE:
                        warnings.warn("Ignoring socket error EPIPE "
                                      "(broken pipe), continuing with "
                                      "reading the response.",
                                      ToleratedServerIssueWarning,
                                      stacklevel=2)
                        # continue with reading response
                    else:
                        raise

                response = client.getresponse()

                # Attempt to get the optional response time header sent from
                # the server
                svr_resp_time = response.getheader(
                    'WBEMServerResponseTime', None)
                if svr_resp_time:
                    try:
                        # convert to float and map from microsec to sec.
                        svr_resp_time = float(svr_resp_time) / 1000000
                    except ValueError:
                        pass

                if recorders:
                    for recorder in recorders:
                        recorder.stage_http_response1(
                            conn_id,
                            response.version,
                            response.status,
                            response.reason,
                            dict(response.getheaders()))

                if response.status != 200:
                    if response.status == 401:
                        if not local:
                            raise AuthError(response.reason, conn_id=conn_id)
                        auth_chal = response.getheader('WWW-Authenticate', '')
                        if 'openwbem' in response.getheader('Server', ''):
                            if 'OWLocal' not in auth_chal:
                                try:
                                    uid = os.getuid()
                                except AttributeError:
                                    raise AuthError(
                                        _format(
                                            "OWLocal authorization for "
                                            "OpenWbem server not supported on "
                                            "{0} platform due to missing "
                                            "os.getuid()", platform.system()),
                                        conn_id=conn_id)
                                local_auth_header = (
                                    'Authorization',
                                    'OWLocal uid="{0}"'.format(uid))
                                continue  # with next retry
                            else:
                                try:
                                    nonce_idx = auth_chal.index('nonce=')
                                    nonce_begin = auth_chal.index('"',
                                                                  nonce_idx)
                                    nonce_end = auth_chal.index('"',
                                                                nonce_begin + 1)
                                    nonce = auth_chal[nonce_begin + 1:nonce_end]
                                    cookie_idx = auth_chal.index('cookiefile=')
                                    cookie_begin = auth_chal.index('"',
                                                                   cookie_idx)
                                    cookie_end = auth_chal.index(
                                        '"', cookie_begin + 1)
                                    cookie_file = auth_chal[
                                        cookie_begin + 1: cookie_end]
                                    file_hndl = open(cookie_file, 'r')
                                    cookie = file_hndl.read().strip()
                                    file_hndl.close()
                                    local_auth_header = (
                                        'Authorization',
                                        'OWLocal nonce="{0}", cookie="{1}"'.
                                        format(nonce, cookie))
                                    continue  # with next retry
                                # pylint: disable=broad-except
                                except Exception as exc:
                                    local_auth_header = None
                                    warnings.warn(
                                        _format(
                                            "Exception in OpenWBEM auth "
                                            "challenge processing: {0} "
                                            "(retrying - this was attempt "
                                            "{1} of {2})",
                                            exc, num_tries + 1, try_limit),
                                        ToleratedServerIssueWarning,
                                        stacklevel=2)
                                    continue  # with next retry
                        elif 'Local' in auth_chal:
                            try:
                                beg = auth_chal.index('"') + 1
                                end = auth_chal.rindex('"')
                                if end > beg:
                                    _file = auth_chal[beg:end]
                                    file_hndl = open(_file, 'r')
                                    cookie = file_hndl.read().strip()
                                    file_hndl.close()
                                    local_auth_header = (
                                        'PegasusAuthorization',
                                        'Local "{0}:{1}:{2}"'.
                                        format(locallogin, _file, cookie))
                                    continue  # with next retry
                            except ValueError:
                                pass
                        raise AuthError(response.reason, conn_id=conn_id)

                    cimerror_hdr = response.getheader('CIMError', None)
                    if cimerror_hdr is not None:
                        cimdetails = {}
                        pgdetails_hdr = response.getheader('PGErrorDetail',
                                                           None)
                        if pgdetails_hdr is not None:
                            # pylint: disable=too-many-function-args
                            cimdetails['PGErrorDetail'] = \
                                urllib.parse.unquote(pgdetails_hdr)
                        raise HTTPError(response.status, response.reason,
                                        cimerror_hdr, cimdetails,
                                        conn_id=conn_id)

                    raise HTTPError(response.status, response.reason,
                                    conn_id=conn_id)

                body = response.read()

                if recorders:
                    for recorder in recorders:
                        recorder.stage_http_response2(body)

            except httplib.BadStatusLine as exc:
                # Background: BadStatusLine is documented to be raised only
                # when strict=True is used (that is not the case here).
                # However, httplib currently raises BadStatusLine also
                # independent of strict when a keep-alive connection times out
                # (e.g. because the server went down).
                # See https://bugs.python.org/issue8450.
                # In Python 3.5, this case is raised as a new
                # httplib.RemoteDisconnected exception, which is also still
                # a BadStatusLine exception with an empty line.
                if exc.line is None or exc.line.strip().strip("'") in \
                        ('', 'None'):
                    # TODO 4/2018 AM Enable retry logic. For unknown reasons,
                    #   retrying causes testclient test case SocketError104 to
                    #   fail. Also, retrying needs to be tested with a real
                    #   WBEM server.
                    if False:  # pylint: disable=using-constant-test
                        warnings.warn(
                            _format("The server closed the connection without "
                                    "returning any response (retrying - this "
                                    "was attempt {0} of {1} at {2})",
                                    num_tries + 1, try_limit, datetime.now()),
                            ToleratedServerIssueWarning,
                            stacklevel=2)
                        continue  # with next retry
                    else:
                        raise ConnectionError(
                            "The server closed the connection without "
                            "returning any response",
                            conn_id=conn_id)
                else:
                    raise ConnectionError(
                        _format("The server returned a bad HTTP status line: "
                                "{0!A}", exc.line),
                        conn_id=conn_id)
            except httplib.IncompleteRead as exc:
                raise ConnectionError(
                    _format("HTTP incomplete read: {0}", exc),
                    conn_id=conn_id)
            except httplib.NotConnected as exc:
                raise ConnectionError(
                    _format("HTTP not connected: {0}", exc),
                    conn_id=conn_id)
            except httplib.HTTPException as exc:
                # Base class for all httplib exceptions
                raise ConnectionError(
                    _format("HTTP error: {0}", exc),
                    conn_id=conn_id)
            except SocketErrors as exc:
                raise ConnectionError(
                    _format("Socket error: {0}", exc),
                    conn_id=conn_id)

            # Operation was successful
            break

    return body, svr_resp_time


def get_cimobject_header(obj):
    """
    Return the value for the CIM-XML extension header field 'CIMObject', using
    the given object.

    This function implements the rules defined in DSP0200 section 6.3.7
    "CIMObject". The format of the CIMObject value is similar but not identical
    to a local WBEM URI (one without namespace type and authority), as defined
    in DSP0207.

    One difference is that DSP0207 requires a leading slash for a local WBEM
    URI, e.g. '/root/cimv2:CIM_Class.k=1', while the CIMObject value has no
    leading slash, e.g. 'root/cimv2:CIM_Class.k=1'.

    Another difference is that the CIMObject value for instance paths has
    provisions for an instance path without keys, while WBEM URIs do not have
    that. Pywbem does not support that.
    """

    # Local namespace path
    if isinstance(obj, six.string_types):
        return obj

    # Local class path
    if isinstance(obj, CIMClassName):
        return obj.to_wbem_uri(format='cimobject')

    # Local instance path
    if isinstance(obj, CIMInstanceName):
        return obj.to_wbem_uri(format='cimobject')

    raise TypeError(
        _format("Invalid object type {0} to generate CIMObject header value "
                "from", type(obj)))
