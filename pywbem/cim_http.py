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
from __future__ import print_function
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
import six
from six.moves import http_client as httplib
from six.moves import urllib

from .cim_obj import CIMClassName, CIMInstanceName, _ensure_unicode, \
                    _ensure_bytes

if six.PY2:
    from M2Crypto import SSL
    from M2Crypto.Err import SSLError
    _HAVE_M2CRYPTO = True
    #pylint: disable=invalid-name
    SocketErrors = (socket.error, socket.sslerror)
else:
    import ssl as SSL                  # pylint: disable=wrong-import-position
    from ssl import SSLError, CertificateError # pylint: disable=wrong-import-position
    _HAVE_M2CRYPTO = False
    #pylint: disable=invalid-name
    SocketErrors = (socket.error,)

__all__ = ['Error', 'ConnectionError', 'AuthError', 'TimeoutError']

class Error(Exception):
    """Exception base class for catching any HTTP transport related errors."""
    pass

class ConnectionError(Error):
    """This exception is raised when there is a problem with the connection
    to the server. A retry may or may not succeed."""
    pass

class AuthError(Error):
    """This exception is raised when an authentication error (401) occurs."""
    pass

class TimeoutError(Error):
    """This exception is raised when the client times out."""
    pass


DEFAULT_PORT_HTTP = 5988        # default port for http
DEFAULT_PORT_HTTPS = 5989       # default port for https

#TODO 5/16 ks This is a linux based set of defaults.
DEFAULT_CA_CERT_PATHS = \
     ['/etc/pki/ca-trust/extracted/openssl/ca-bundle.trust.crt', \
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
        with HTTPTimeout(timeout, http_conn):
            ... operations using http_conn ...

    If the timeout expires, the socket of the HTTP connection is shut down.
    Once the http operations return as a result of that or for other reasons,
    the exit handler of this class raises a `cim_http.Error` exception in the
    thread that executed the ``with`` statement.
    """

    def __init__(self, timeout, http_conn):
        """Initialize the HTTPTimeout object.

        :Parameters:

          timeout : number
            Timeout in seconds, ``None`` means no timeout.

          http_conn : `httplib.HTTPBaseConnection` (or subclass)
            The connection that is to be stopped when the timeout expires.
        """

        self._timeout = timeout
        self._http_conn = http_conn
        self._retrytime = 5     # time in seconds after which a retry of the
                                # socket shutdown is scheduled if the socket
                                # is not yet on the connection when the
                                # timeout expires initially.
        self._timer = None      # the timer object
        self._ts1 = None        # timestamp when timer was started
        self._shutdown = None   # flag indicating that the timer handler has
                                # shut down the socket
        return

    def __enter__(self):
        if self._timeout != None:
            self._timer = threading.Timer(self._timeout,
                                          HTTPTimeout.timer_expired, [self])
            self._timer.start()
            self._ts1 = datetime.now()
        self._shutdown = False
        return

    def __exit__(self, exc_type, exc_value, traceback):
        if self._timeout != None:
            self._timer.cancel()
            if self._shutdown:
                # If the timer handler has shut down the socket, we
                # want to make that known, and override any other
                # exceptions that may be pending.
                ts2 = datetime.now()
                duration = ts2 - self._ts1
                duration_sec = float(duration.microseconds)/1000000 +\
                               duration.seconds + duration.days*24*3600
                raise TimeoutError("The client timed out and closed the "\
                                   "socket after %.0fs." % duration_sec)
        return False # re-raise any other exceptions

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
        if self._http_conn.sock != None:
            self._shutdown = True
            self._http_conn.sock.shutdown(socket.SHUT_RDWR)
        else:
            # Retry after the retry duration
            self._timer.cancel()
            self._timer = threading.Timer(self._retrytime,
                                          HTTPTimeout.timer_expired, [self])
            self._timer.start()

def parse_url(url):
    """Return a tuple of ``(host, port, ssl)`` from the URL specified in the
    ``url`` parameter.

    The returned ``ssl`` item is a boolean indicating the use of SSL, and is
    recognized from the URL scheme (http vs. https). If none of these schemes
    is specified in the URL, the returned value defaults to False
    (non-SSL/http).

    The returned ``port`` item is the port number, as an integer. If there is
    no port number specified in the URL, the returned value defaults to 5988
    for non-SSL/http, and to 5989 for SSL/https.

    The returned ``host`` item is the host portion of the URL, as a string.
    The host portion may be specified in the URL as a short or long host name,
    dotted IPv4 address, or bracketed IPv6 address with or without zone index
    (aka scope ID). An IPv6 address is converted from the RFC6874 URI syntax
    to the RFC4007 text representation syntax before being returned, by
    removing the brackets and converting the zone index (if present) from
    "-eth0" to "%eth0".

    Examples for valid URLs can be found in the test program
    `testsuite/test_cim_http.py`.
    """

    default_ssl = False             # default SSL use (for no or unknown scheme)

    # Look for scheme.
    matches = re.match(r"^(https?)://(.*)$", url, re.I)
    if matches:
        _scheme = matches.group(1).lower()
        hostport = matches.group(2)
        ssl = (_scheme == 'https')
    else:
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
        if matches.group(2) != None:
            # The zone index is present
            host += "%" + matches.group(2)

    return host, port, ssl

def get_default_ca_certs():
    """
    Try to find out system path with ca certificates. This path is cached and
    returned. If no path is found out, None is returned.
    """
    if not hasattr(get_default_ca_certs, '_path'):
        for path in get_default_ca_cert_paths():
            if os.path.exists(path):
                get_default_ca_certs._path = path
                break
        else:
            get_default_ca_certs._path = None
    return get_default_ca_certs._path

# pylint: disable=too-many-branches,too-many-statements,too-many-arguments
def wbem_request(url, data, creds, headers=[], debug=0, x509=None,
                 verify_callback=None, ca_certs=None,
                 no_verification=False, timeout=None):
    # pylint: disable=too-many-arguments,unused-argument
    # pylint: disable=too-many-locals
    """
    Send an HTTP or HTTPS request to a WBEM server and return the response.

    This function uses Python's built-in `httplib` module.

    :Parameters:

      url : Unicode string or UTF-8 encoded byte string
        URL of the WBEM server (e.g. ``"https://10.11.12.13:6988"``).
        For details, see the ``url`` parameter of
        `WBEMConnection.__init__`.

      data : Unicode string or UTF-8 encoded byte string
        The CIM-XML formatted data to be sent as a request to the WBEM server.

      creds
        Credentials for authenticating with the WBEM server.
        For details, see the ``creds`` parameter of
        `WBEMConnection.__init__`.

      headers : list of Unicode strings or UTF-8 encoded byte strings
        List of HTTP header fields to be added to the request, in addition to
        the standard header fields such as ``Content-type``,
        ``Content-length``, and ``Authorization``.

      debug : ``bool``
        Boolean indicating whether to create debug information.

      x509
        Used for HTTPS with certificates.
        For details, see the ``x509`` parameter of
        `WBEMConnection.__init__`.

      verify_callback
        Used for HTTPS with certificates.
        For details, see the ``verify_callback`` parameter of
        `WBEMConnection.__init__`.

      ca_certs
        Used for HTTPS with certificates.
        For details, see the ``ca_certs`` parameter of
        `WBEMConnection.__init__`.

      no_verification
        Used for HTTPS with certificates.
        For details, see the ``no_verification`` parameter of
        `WBEMConnection.__init__`.

      timeout : number
        Timeout in seconds, for requests sent to the server. If the server did
        not respond within the timeout duration, the socket for the connection
        will be closed, causing a `TimeoutError` to be raised.
        A value of ``None`` means there is no timeout.
        A value of ``0`` means the timeout is very short, and does not really
        make any sense.
        Note that not all situations can be handled within this timeout, so
        for some issues, this method may take longer to raise an exception.

    :Returns:
      The CIM-XML formatted response data from the WBEM server, as a `unicode`
      object.

    :Raises:
      :raise AuthError:
      :raise ConnectionError:
      :raise TimeoutError:
    """

    class HTTPBaseConnection:        # pylint: disable=no-init
        """ Common base for specific connection classes. Implements
            the send method
        """
        # pylint: disable=old-style-class,too-few-public-methods
        def send(self, strng):
            """
            A copy of httplib.HTTPConnection.send(), with these fixes:

            * We fix the problem that the connection gets closed upon error
              32 (EPIPE), by not doing that (If the connection gets closed,
              getresponse() fails). This problem was reported as Python issue
              #5542, and the same fix we do here was integrated into Python
              2.7 and 3.1 or 3.2, but not into Python 2.6 (so we still need
              our fix here).

            * Ensure that the data are bytes, not unicode.
              TODO 2016-05 AM: Ensuring bytes at this level can only be a
                               quick fix. Figure out a better approach.
            """
            if self.sock is None:
                if self.auto_open:
                    self.connect()
                else:
                    raise httplib.NotConnected()
            if self.debuglevel > 0:
                print("send: %r" % strng)
            blocksize = 8192
            if hasattr(strng, 'read') and not isinstance(strng, array):
                if self.debuglevel > 0:
                    print("sendIng a read()able")
                data = strng.read(blocksize)
                while data:
                    self.sock.sendall(_ensure_bytes(data))
                    data = strng.read(blocksize)
            else:
                self.sock.sendall(_ensure_bytes(strng))

    class HTTPConnection(HTTPBaseConnection, httplib.HTTPConnection):
        """ Execute client connection without ssl using httplib. """
        def __init__(self, host, port=None, timeout=None):
            # TODO AM: Should we set strict=True in the following call, for PY2?
            httplib.HTTPConnection.__init__(self, host=host, port=port,
                                            timeout=timeout)

    class HTTPSConnection(HTTPBaseConnection, httplib.HTTPSConnection):
        """ Execute client connection with ssl using httplib."""
        # pylint: disable=R0913,too-many-arguments
        def __init__(self, host, port=None, key_file=None, cert_file=None,
                     ca_certs=None, verify_callback=None, timeout=None):
            # TODO AM: Should we set strict=True in the following call, for PY2?
            httplib.HTTPSConnection.__init__(self, host=host, port=port,
                                             key_file=key_file,
                                             cert_file=cert_file,
                                             timeout=timeout)
            self.ca_certs = ca_certs
            self.verify_callback = verify_callback

        def connect(self):
            # pylint: disable=too-many-branches
            """Connect to a host on a given (SSL) port."""

            ## Connect for M2Crypto ssl package
            if _HAVE_M2CRYPTO:
                # Calling httplib.HTTPSConnection.connect(self) does not work
                # because of its ssl.wrap_socket() call. So we copy the code of
                # that connect() method modulo the ssl.wrap_socket() call.

                # Another change is that we do not pass the timeout value
                # on to the socket call, because that does not work with
                # M2Crypto.


                if sys.version_info[0:2] >= (2, 7):
                    # the source_address argument was added in 2.7
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
                    if False:
                        # TODO 2/16 AM: Currently disabled, figure out how to
                        #               reenable.
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
                                    'SSL error: post connection check failed')
                    return ret

                # TODO 2/16 AM: Verify whether the additional exceptions
                #               in the M2Crypto code can
                #               really be omitted:
                #               Err.SSLError, SSL.SSLError, SSL.Checker.
                #               WrongHost,
                #               SSLTimeoutError
                except SSLError as arg:
                    raise ConnectionError(
                        "SSL error %s: %s" % (arg.__class__, arg))

            # Connect using Python SSL module
            else:
                # Setup the socket context
                # TODO ks 4/16: confirm that we cannot use the default_context()
                # Selects the highest protocol version that both the
                # client and server support (SSLV23)
                ctx = SSL.SSLContext(SSL.PROTOCOL_SSLv23)

                # TODO ks 4/16: Is there a use for the CERT_OPTIONAL mode
                if self.cert_file:
                    ctx.load_cert(self.cert_file, keyfile=self.key_file)
                if self.ca_certs:
                    # CERT_REQUIRED validates server certificate:
                    # against certificates in ca_certs
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
                        "SSL error %s: %s" % (arg.__class__, arg))
                except CertificateError as arg:
                    raise ConnectionError(
                        "SSL certificate error %s: %s" % (arg.__class__, arg))

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
                    'file URLs not supported on %s platform due '\
                    'to missing AF_UNIX support' % platform.system())
            self.sock = socket.socket(socket_af, socket.SOCK_STREAM)
            self.sock.connect(self.uds_path)

    host, port, use_ssl = parse_url(_ensure_unicode(url))

    key_file = None
    cert_file = None

    if use_ssl and x509 is not None:
        cert_file = x509.get('cert_file')
        key_file = x509.get('key_file')

    num_tries = 0
    local_auth_header = None
    try_limit = 5

    # Make sure the data argument is converted to a UTF-8 encoded byte string.
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
            client = HTTPConnection(host=host,  # pylint: disable=redefined-variable-type
                                    port=port,
                                    timeout=timeout)
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
                    raise ConnectionError('File URL is not a socket: %s' % url)
            except OSError as exc:
                raise ConnectionError('Error with file URL %s: %s' % (url, exc))

    locallogin = None
    if host in ('localhost', 'localhost6', '127.0.0.1', '::1'):
        local = True
    if local:
        try:
            locallogin = getpass.getuser()
        except (KeyError, ImportError):
            locallogin = None

    with HTTPTimeout(timeout, client):

        while num_tries < try_limit:
            num_tries = num_tries + 1

            client.putrequest('POST', '/cimom')

            client.putheader('Content-type',
                             'application/xml; charset="utf-8"')
            client.putheader('Content-length', str(len(data)))
            if local_auth_header is not None:
                # The following pylint stmt disables a false positive, see
                # https://github.com/PyCQA/pylint/issues/701
                # TODO 3/16 AM: Track resolution of this Pylint bug.
                # pylint: disable=not-an-iterable
                client.putheader(*local_auth_header)
            elif creds is not None:
                auth = '%s:%s' % (creds[0], creds[1])
                auth64 = _ensure_unicode(base64.b64encode(
                    _ensure_bytes(auth))).replace('\n', '')
                client.putheader('Authorization', 'Basic %s' % auth64)
            elif locallogin is not None:
                client.putheader('PegasusAuthorization',
                                 'Local "%s"' % locallogin)

            for hdr in headers:
                hdr = _ensure_unicode(hdr)
                hdr_pieces = [x.strip() for x in hdr.split(':', 1)]
                client.putheader(urllib.parse.quote(hdr_pieces[0]),
                                 urllib.parse.quote(hdr_pieces[1]))

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
                        if debug:
                            print("Debug: Ignoring socket error ECONNRESET " \
                                  "(connection reset) returned by server.")
                    elif exc.args[0] == errno.EPIPE:
                        if debug:
                            print("Debug: Ignoring socket error EPIPE " \
                                  "(broken pipe) returned by server.")
                    else:
                        raise ConnectionError("Socket error: %s" % exc)

                response = client.getresponse()

                if response.status != 200:
                    if response.status == 401:
                        if num_tries >= try_limit:
                            raise AuthError(response.reason)
                        if not local:
                            raise AuthError(response.reason)
                        auth_chal = response.getheader('WWW-Authenticate', '')
                        if 'openwbem' in response.getheader('Server', ''):
                            if 'OWLocal' not in auth_chal:
                                try:
                                    uid = os.getuid()
                                except AttributeError:
                                    raise ConnectionError(
                                        "OWLocal authorization for OpenWbem "\
                                        "server not supported on %s platform "\
                                        "due to missing os.getuid()" % \
                                        platform.system())
                                local_auth_header = ('Authorization',
                                                     'OWLocal uid="%d"' % uid)
                                continue
                            else:
                                try:
                                    nonce_idx = auth_chal.index('nonce=')
                                    nonce_begin = auth_chal.index('"',
                                                                  nonce_idx)
                                    nonce_end = auth_chal.index('"',
                                                                nonce_begin+1)
                                    nonce = auth_chal[nonce_begin+1:nonce_end]
                                    cookie_idx = auth_chal.index('cookiefile=')
                                    cookie_begin = auth_chal.index('"',
                                                                   cookie_idx)
                                    cookie_end = auth_chal.index(
                                        '"', cookie_begin+1)
                                    cookie_file = auth_chal[
                                        cookie_begin+1:cookie_end]
                                    file_hndl = open(cookie_file, 'r')
                                    cookie = file_hndl.read().strip()
                                    file_hndl.close()
                                    local_auth_header = (
                                        'Authorization',
                                        'OWLocal nonce="%s", cookie="%s"' % \
                                        (nonce, cookie))
                                    continue
                                except Exception as exc:
                                    if debug:
                                        print("Debug: Ignoring exception %s " \
                                              "in OpenWBEM auth challenge " \
                                              "processing." % exc)
                                    local_auth_header = None
                                    continue
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
                                        'Local "%s:%s:%s"' % \
                                        (locallogin, _file, cookie))
                                    continue
                            except ValueError:
                                pass
                        raise AuthError(response.reason)

                    cimerror_hdr = response.getheader('CIMError', None)
                    if cimerror_hdr is not None:
                        exc_str = 'CIMError: %s' % cimerror_hdr
                        pgerrordetail_hdr = response.getheader('PGErrorDetail',
                                                               None)
                        if pgerrordetail_hdr is not None:
                            #pylint: disable=too-many-function-args
                            exc_str += ', PGErrorDetail: %s' %\
                                urllib.parse.unquote(pgerrordetail_hdr)
                        raise ConnectionError(exc_str)

                    raise ConnectionError('HTTP error: %s' % response.reason)

                body = response.read()

            except httplib.BadStatusLine as exc:
                # Background: BadStatusLine is documented to be raised only
                # when strict=True is used (that is not the case here).
                # However, httplib currently raises BadStatusLine also
                # independent of strict when a keep-alive connection times out
                # (e.g. because the server went down).
                # See http://bugs.python.org/issue8450.
                if exc.line is None or exc.line.strip().strip("'") in \
                                       ('', 'None'):
                    raise ConnectionError("The server closed the "\
                        "connection without returning any data, or the "\
                        "client timed out")
                else:
                    raise ConnectionError("The server returned a bad "\
                        "HTTP status line: %r" % exc.line)
            except httplib.IncompleteRead as exc:
                raise ConnectionError("HTTP incomplete read: %s" % exc)
            except httplib.NotConnected as exc:
                raise ConnectionError("HTTP not connected: %s" % exc)
            except SocketErrors as exc:
                raise ConnectionError("Socket error: %s" % exc)

            break

    return body


def get_object_header(obj):
    """Return the HTTP header required to make a CIM operation request
    using the given object.  Return None if the object does not need
    to have a header."""

    # Local namespacepath

    if isinstance(obj, six.string_types):
        return 'CIMObject: %s' % obj

    # CIMLocalClassPath

    if isinstance(obj, CIMClassName):
        return 'CIMObject: %s:%s' % (obj.namespace, obj.classname)

    # CIMInstanceName with namespace

    if isinstance(obj, CIMInstanceName) and obj.namespace is not None:
        return 'CIMObject: %s' % obj

    raise TypeError('Don\'t know how to generate HTTP headers for %s' % obj)
