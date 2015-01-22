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
#

'''
Send HTTP/HTTPS requests to a WBEM server.

This module does not know anything about the fact that the data being
transferred in the HTTP request and response is CIM-XML.  It is up to the
caller to provide CIM-XML formatted input data and interpret the result data
as CIM-XML.
'''

import string
import re
import os
import sys
import socket
import getpass
from stat import S_ISSOCK
from types import StringTypes
import platform
import httplib
import base64
import urllib
import threading
from datetime import timedelta, datetime

from M2Crypto import SSL, Err

from pywbem import cim_obj

__all__ = ['Error', 'AuthError', 'wbem_request', 'get_object_header']

class Error(Exception):
    """This exception is raised when a transport error occurs."""
    pass

class AuthError(Error):
    """This exception is raised when an authentication error (401) occurs."""
    pass

class ConnectionError(Error):
    """This exception is raised when a connection-related problem occurs,
    where a retry might make sense."""
    pass

class TimeoutError(Error):
    """This exception is raised when the client timeout is exceeded."""
    pass

class HTTPTimeout (object):
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
        self._retrytime = 10    # time in seconds after which a retry of the
                                # socket shutdown is scheduled if the socket
                                # is not yet on the connection when the
                                # timeout expires initially.
        self._timer = None
        self._ts1 = None
        self._expired = None
        return

    def __enter__(self):
        if self._timeout != None:
            self._timer = threading.Timer(self._timeout,
                                          HTTPTimeout.timer_expired, [self])
            self._timer.start()
            self._ts1 = datetime.now()
        self._expired = False
        return

    def __exit__(self, exc_type, exc_value, traceback):
        if self._timeout != None:
            self._timer.cancel()
            if self._expired:
                ts2 = datetime.now()
                duration = ts2 - self._ts1
                duration_sec = float(duration.microseconds)/1000000 +\
                               duration.seconds + duration.days*24*3600
                raise TimeoutError("Timeout error: Client timed out after "\
                                   "%.0fs." % duration_sec)
        return False # re-raise any other exceptions

    def timer_expired(self):
        """
        This method is invoked in context of the timer thread, so we cannot
        directly throw exceptions (we can, but they would be in the wrong
        thread), so instead we cause the socket of the connection to shut down.
        """
        self._expired = True
        if self._http_conn.sock != None:
            # Timer expired, shutting down socket of HTTP connection.
            self._http_conn.sock.shutdown(socket.SHUT_RDWR)
        else:
            # Timer expired, no socket yet on HTTP connection to shut down,
            # so we retry. This should only happen with very short timeouts,
            # so retrying should not hurt, timewise.
            self._timer.cancel()
            self._timer = threading.Timer(self._retrytime,
                                          HTTPTimeout.timer_expired, [self])
            self._timer.start()
        return

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

    default_port_http  = 5988       # default port for http
    default_port_https = 5989       # default port for https
    default_ssl        = False      # default SSL use (for no or unknown scheme)

    # Look for scheme.
    m = re.match(r"^(https?)://(.*)$", url, re.I)
    if m:
        _scheme = m.group(1).lower()
        hostport = m.group(2)
        if _scheme == 'https':
            ssl = True
        else: # will be 'http'
            ssl = False
    else:
        # The URL specified no scheme (or a scheme other than the expected
        # schemes, but we don't check)
        ssl = default_ssl
        hostport = url

    # Remove trailing path segments, if any.
    # Having URL components other than just slashes (e.g. '#' or '?') is not
    # allowed (but we don't check).
    m = hostport.find("/")
    if m >= 0:
        hostport = hostport[0:m]

    # Look for port.
    # This regexp also works for (colon-separated) IPv6 addresses, because they
    # must be bracketed in a URL.
    m = re.search(r":([0-9]+)$", hostport)
    if m:
        host = hostport[0:m.start(0)]
        port = int(m.group(1))
    else:
        host = hostport
        port = default_port_https if ssl else default_port_http

    # Reformat IPv6 addresses from RFC6874 URI syntax to RFC4007 text
    # representation syntax:
    #   - Remove the brackets.
    #   - Convert the zone index (aka scope ID) from "-eth0" to "%eth0".
    # Note on the regexp below: The first group needs the '?' after '.+' to
    # become non-greedy; in greedy mode, the optional second group would never
    # be matched.
    m = re.match(r"^\[(.+?)(?:-(.+))?\]$", host)
    if m:
        # It is an IPv6 address
        host = m.group(1)
        if m.group(2) != None:
            # The zone index is present
            host += "%" + m.group(2)

    return host, port, ssl

def get_default_ca_certs():
    """
    Try to find out system path with ca certificates. This path is cached and
    returned. If no path is found out, None is returned.
    """
    if not hasattr(get_default_ca_certs, '_path'):
        for path in (
                '/etc/pki/ca-trust/extracted/openssl/ca-bundle.trust.crt',
                '/etc/ssl/certs',
                '/etc/ssl/certificates'):
            if os.path.exists(path):
                get_default_ca_certs._path = path
                break
        else:
            get_default_ca_certs._path = None
    return get_default_ca_certs._path

def wbem_request(url, data, creds, headers=[], debug=0, x509=None,
                 verify_callback=None, ca_certs=None,
                 no_verification=False, timeout=None):
    """
    Send an HTTP or HTTPS request to a WBEM server and return the response.

    This function uses Python's built-in `httplib` module.

    :Parameters:

      url : `unicode` or UTF-8 encoded `str`
        URL of the WBEM server (e.g. ``"https://10.11.12.13:6988"``).
        For details, see the ``url`` parameter of
        `WBEMConnection.__init__`.

      data : `unicode` or UTF-8 encoded `str`
        The CIM-XML formatted data to be sent as a request to the WBEM server.

      creds
        Credentials for authenticating with the WBEM server.
        For details, see the ``creds`` parameter of
        `WBEMConnection.__init__`.

      headers : list of `unicode` or UTF-8 encoded `str`
        List of HTTP header fields to be added to the request, in addition to
        the standard header fields such as ``Content-type``,
        ``Content-length``, and ``Authorization``.

      debug : ``bool``
        Boolean indicating whether to create debug information.
        Not currently used.

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

    :Returns:
      The CIM-XML formatted response data from the WBEM server, as a `unicode`
      object.

    :Raises:
      :raise Error:
      :raise AuthError:
    """

    class HTTPBaseConnection:
        def send(self, str):
            """ Same as httplib.HTTPConnection.send(), except we don't
            check for sigpipe and close the connection.  If the connection
            gets closed, getresponse() fails.
            """

            if self.sock is None:
                if self.auto_open:
                    self.connect()
                else:
                    raise httplib.NotConnected()
            if self.debuglevel > 0:
                print "send:", repr(str)
            self.sock.sendall(str)

    class HTTPConnection(HTTPBaseConnection, httplib.HTTPConnection):
        def __init__(self, host, port=None, strict=None):
            httplib.HTTPConnection.__init__(self, host, port, strict, timeout)

    class HTTPSConnection(HTTPBaseConnection, httplib.HTTPSConnection):
        def __init__(self, host, port=None, key_file=None, cert_file=None,
                     strict=None, ca_certs=None, verify_callback=None):
            httplib.HTTPSConnection.__init__(self, host, port, key_file,
                                             cert_file, strict, timeout)
            self.ca_certs = ca_certs
            self.verify_callback = verify_callback

        def connect(self):
            "Connect to a host on a given (SSL) port."

            # Calling httplib.HTTPSConnection.connect(self) does not work
            # because of its ssl.wrap_socket() call. So we copy the code of
            # that connect() method modulo the ssl.wrap_socket() call:
            if sys.version_info[0:2] == [2, 7]:
                self.sock = socket.create_connection((self.host, self.port),
                                                     self.timeout,
                                                     self.source_address)
            else: # 2.6
                self.sock = socket.create_connection((self.host, self.port),
                                                     self.timeout)
            if self._tunnel_host:
                self._tunnel()
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
                # except for the first line (socket connection). We want to
                # preserve tunneling ability.
                self.sock.addr = (self.host, self.port)
                self.sock.setup_ssl()
                self.sock.set_connect_state()
                ret = self.sock.connect_ssl()
                if self.ca_certs:
                    check = getattr(self.sock, 'postConnectionCheck',
                                    self.sock.clientPostConnectionCheck)
                    if check is not None:
                        if not check(self.sock.get_peer_cert(), self.host):
                            raise Error('SSL error: post connection check '\
                                        'failed')
                return ret
            except (Err.SSLError, SSL.SSLError, SSL.Checker.WrongHost), arg:
                # This will include SSLTimeoutError (it subclasses SSLError)
                raise Error("SSL error %s: %s" % (str(arg.__class__), arg))

    class FileHTTPConnection(HTTPBaseConnection, httplib.HTTPConnection):

        def __init__(self, uds_path):
            httplib.HTTPConnection.__init__(self, 'localhost')
            self.uds_path = uds_path

        def connect(self):
            try:
                socket_af = socket.AF_UNIX
            except AttributeError:
                raise Error('file URL not supported on %s platform due '\
                        'to missing AF_UNIX support' % platform.system())
            self.sock = socket.socket(socket_af, socket.SOCK_STREAM)
            self.sock.connect(self.uds_path)

    host, port, use_ssl = parse_url(url)

    key_file = None
    cert_file = None

    if use_ssl and x509 is not None:
        cert_file = x509.get('cert_file')
        key_file = x509.get('key_file')

    numTries = 0
    localAuthHeader = None
    tryLimit = 5

    # Make sure the data argument is converted to a UTF-8 encoded str object.
    # This is important because according to RFC2616, the Content-Length HTTP
    # header must be measured in Bytes (and the Content-Type header will
    # indicate UTF-8).
    if isinstance(data, unicode):
        data = data.encode('utf-8')

    data = '<?xml version="1.0" encoding="utf-8" ?>\n' + data

    if not no_verification and ca_certs is None:
        ca_certs = get_default_ca_certs()
    elif no_verification:
        ca_certs = None

    local = False
    if use_ssl:
        h = HTTPSConnection(host,
                            port=port,
                            key_file=key_file,
                            cert_file=cert_file,
                            ca_certs=ca_certs,
                            verify_callback=verify_callback,
                            timeout=timeout)
    else:
        if url.startswith('http'):
            h = HTTPConnection(host,
                               port=port,
                               timeout=timeout)
        else:
            if url.startswith('file:'):
                url = url[5:]
            try:
                s = os.stat(url)
                if S_ISSOCK(s.st_mode):
                    h = FileHTTPConnection(url)
                    local = True
                else:
                    raise Error('Invalid URL: %s' % url)
            except OSError:
                raise Error('Invalid URL: %s' % url)

    locallogin = None
    if host in ('localhost', 'localhost6', '127.0.0.1', '::1'):
        local = True
    if local:
        try:
            locallogin = getpass.getuser()
        except (KeyError, ImportError):
            locallogin = None

    with HTTPTimeout(timeout, h):

        while numTries < tryLimit:
            numTries = numTries + 1

            h.putrequest('POST', '/cimom')

            h.putheader('Content-type', 'application/xml; charset="utf-8"')
            h.putheader('Content-length', str(len(data)))
            if localAuthHeader is not None:
                h.putheader(*localAuthHeader)
            elif creds is not None:
                h.putheader('Authorization', 'Basic %s' %
                            base64.encodestring(
                                '%s:%s' %
                                (creds[0], creds[1])).replace('\n', ''))
            elif locallogin is not None:
                h.putheader('PegasusAuthorization', 'Local "%s"' % locallogin)

            for hdr in headers:
                if isinstance(hdr, unicode):
                    hdr = hdr.encode('utf-8')
                s = map(lambda x: string.strip(x), string.split(hdr, ":", 1))
                h.putheader(urllib.quote(s[0]), urllib.quote(s[1]))

            try:
                # See RFC 2616 section 8.2.2
                # An http server is allowed to send back an error (presumably
                # a 401), and close the connection without reading the entire
                # request.  A server may do this to protect itself from a DoS
                # attack.
                #
                # If the server closes the connection during our h.send(), we
                # will either get a socket exception 104 (TCP RESET), or a
                # socket exception 32 (broken pipe).  In either case, thanks
                # to our fixed HTTPConnection classes, we'll still be able to
                # retrieve the response so that we can read and respond to the
                # authentication challenge.
                h.endheaders()
                try:
                    h.send(data)
                except socket.error, arg:
                    if arg[0] != 104 and arg[0] != 32:
                        raise

                response = h.getresponse()

                if response.status != 200:
                    if response.status == 401:
                        if numTries >= tryLimit:
                            raise AuthError(response.reason)
                        if not local:
                            raise AuthError(response.reason)
                        authChal = response.getheader('WWW-Authenticate', '')
                        if 'openwbem' in response.getheader('Server', ''):
                            if 'OWLocal' not in authChal:
                                try:
                                    uid = os.getuid()
                                except AttributeError:
                                    raise Error("OWLocal authorization for "\
                                            "openwbem server not supported "\
                                            "on %s platform due to missing "\
                                            "os.getuid()" % platform.system())
                                localAuthHeader = ('Authorization',
                                                   'OWLocal uid="%d"' % uid)
                                continue
                            else:
                                try:
                                    nonceIdx = authChal.index('nonce=')
                                    nonceBegin = authChal.index('"', nonceIdx)
                                    nonceEnd = authChal.index('"', nonceBegin+1)
                                    nonce = authChal[nonceBegin+1:nonceEnd]
                                    cookieIdx = authChal.index('cookiefile=')
                                    cookieBegin = authChal.index('"', cookieIdx)
                                    cookieEnd = authChal.index('"', cookieBegin+1)
                                    cookieFile = authChal[cookieBegin+1:cookieEnd]
                                    f = open(cookieFile, 'r')
                                    cookie = f.read().strip()
                                    f.close()
                                    localAuthHeader = (
                                        'Authorization',
                                        'OWLocal nonce="%s", cookie="%s"' % \
                                        (nonce, cookie))
                                    continue
                                except:
                                    localAuthHeader = None
                                    continue
                        elif 'Local' in authChal:
                            try:
                                beg = authChal.index('"') + 1
                                end = authChal.rindex('"')
                                if end > beg:
                                    file = authChal[beg:end]
                                    fo = open(file, 'r')
                                    cookie = fo.read().strip()
                                    fo.close()
                                    localAuthHeader = (
                                        'PegasusAuthorization',
                                        'Local "%s:%s:%s"' % \
                                        (locallogin, file, cookie))
                                    continue
                            except ValueError:
                                pass

                        raise AuthError(response.reason)
                    if response.getheader('CIMError', None) is not None and \
                       response.getheader('PGErrorDetail', None) is not None:
                        raise Error(
                            'CIMError: %s: %s' %
                            (response.getheader('CIMError'),
                             urllib.unquote(response.getheader(
                                                            'PGErrorDetail'))))
                    raise Error('HTTP error: %s' % response.reason)

                body = response.read()

            except httplib.BadStatusLine, arg:
                # Background: BadStatusLine is documented to be raised only
                # when strict=True is used (that is not the case here).
                # However, httplib currently raises BadStatusLine also
                # independent of strict when a keep-alive connection times out
                # (e.g. because the server went down).
                # See http://bugs.python.org/issue8450.
                # On how to detect this: A connection timeout definitely causes
                # arg==None, but it is not clear whether other situations could
                # also cause arg==None.
                if arg.line.strip().strip("'") == '':
                    raise ConnectionError("Connection error: The CIM server "\
                                          "closed the connection without "\
                                          "returning any data, or the client "\
                                          "timed out")
                else:
                    raise Error("HTTP error: The CIM server returned a bad "\
                                "HTTP status line: '%s'" % arg.line)
            except httplib.IncompleteRead, arg:
                raise ConnectionError("Connection error: HTTP incomplete "\
                                      "read: %s" % arg)
            except httplib.NotConnected, arg:
                raise ConnectionError("Connection error: HTTP not "\
                                      "connected: %s" % arg)
            except socket.error, arg:
                raise ConnectionError("Connection error: Socket error %s" %arg)
            except socket.sslerror, arg:
                raise ConnectionError("Connection error: SSL error %s" % arg)

            break

    return body


def get_object_header(obj):
    """Return the HTTP header required to make a CIM operation request
    using the given object.  Return None if the object does not need
    to have a header."""

    # Local namespacepath

    if isinstance(obj, StringTypes):
        return 'CIMObject: %s' % obj

    # CIMLocalClassPath

    if isinstance(obj, cim_obj.CIMClassName):
        return 'CIMObject: %s:%s' % (obj.namespace, obj.classname)

    # CIMInstanceName with namespace

    if isinstance(obj, cim_obj.CIMInstanceName) and obj.namespace is not None:
        return 'CIMObject: %s' % obj

    raise TypeError('Don\'t know how to generate HTTP headers for %s' % obj)
