#
# (C) Copyright 2003-2005 Hewlett-Packard Development Company, L.P.
# (C) Copyright 2006-2007 Novell, Inc. 
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as
# published by the Free Software Foundation; either version 2 of the
# License.
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

'''
This module implements CIM operations over HTTP.

This module should not know anything about the fact that the data
being transferred is XML.  It is up to the caller to format the input
data and interpret the result.
'''

import sys, string, re, os, socket, pwd
from stat import S_ISSOCK
import cim_obj
from types import StringTypes

class Error(Exception):
    """This exception is raised when a transport error occurs."""
    pass

class AuthError(Error):
    """This exception is raised when an authentication error (401) occurs."""
    pass

def parse_url(url):
    """Return a tuple of (host, port, ssl) from the URL parameter.
    The returned port defaults to 5988 if not specified.  SSL supports
    defaults to False if not specified."""

    host = url                          # Defaults
    port = 5988
    ssl = False

    if re.match("https", url):          # Set SSL if specified
        ssl = True
        port = 5989

    m = re.search("^https?://", url)    # Eat protocol name
    if m:
        host = url[len(m.group(0)):]

    s = string.split(host, ":")         # Set port number
    if len(s) != 1:
        host = s[0]
        port = int(s[1])

    return host, port, ssl

def wbem_request(url, data, creds, headers = [], debug = 0, x509 = None,
                 verify_callback = None):
    """Send XML data over HTTP to the specified url. Return the
    response in XML.  Uses Python's build-in httplib.  x509 may be a
    dictionary containing the location of the SSL certificate and key
    files."""

    import httplib, base64, urllib

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
            httplib.HTTPConnection.__init__(self, host, port, strict)
    
    class HTTPSConnection(HTTPBaseConnection, httplib.HTTPSConnection):
        def __init__(self, host, port=None, key_file=None, cert_file=None, 
                     strict=None):
            httplib.HTTPSConnection.__init__(self, host, port, key_file, 
                                             cert_file, strict)
    
    class FileHTTPConnection(HTTPBaseConnection, httplib.HTTPConnection):
        def __init__(self, uds_path):
            httplib.HTTPConnection.__init__(self, 'localhost')
            self.uds_path = uds_path
        def connect(self):
            self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self.sock.connect(self.uds_path)

    host, port, ssl = parse_url(url)

    key_file = None
    cert_file = None

    if ssl:

        if x509 is not None:
            cert_file = x509.get('cert_file')
            key_file = x509.get('key_file')

        if verify_callback is not None:
            try:
                from OpenSSL import SSL
                ctx = SSL.Context(SSL.SSLv3_METHOD)
                ctx.set_verify(SSL.VERIFY_PEER, verify_callback)
                # Add the key and certificate to the session
                if cert_file is not None and key_file is not None:
                  ctx.use_certificate_file(cert_file)
                  ctx.use_privatekey_file(key_file)
                s = SSL.Connection(ctx, socket.socket(socket.AF_INET,
                                                      socket.SOCK_STREAM))
                s.connect((host, port))
                s.do_handshake()
                s.shutdown()
                s.close()
            except socket.error, arg:
                raise Error("Socket error: %s" % (arg,))
            except socket.sslerror, arg:
                raise Error("SSL error: %s" % (arg,))

    numTries = 0
    localAuthHeader = None
    tryLimit = 5

    data = '<?xml version="1.0" encoding="utf-8" ?>\n' + data

    local = False
    if ssl:
        h = HTTPSConnection(host, port = port, key_file = key_file,
                                            cert_file = cert_file)
    else:
        if url.startswith('http'):
            h = HTTPConnection(host, port = port)
        else:
            if url.startswith('file:'):
                url = url[5:]
            try:
                s = os.stat(url)
                if S_ISSOCK(s.st_mode):
                    h = FileHTTPConnection(url)
                    local = True
                else:
                    raise Error('Invalid URL')
            except OSError:
                raise Error('Invalid URL')

    locallogin = None
    if host in ('localhost', '127.0.0.1'):
        local = True
    if local:
        uid = os.getuid()
        try:
            locallogin = pwd.getpwuid(uid)[0]
        except KeyError:
            locallogin = None
    while numTries < tryLimit:
        numTries = numTries + 1

        h.putrequest('POST', '/cimom')

        h.putheader('Content-type', 'application/xml; charset="utf-8"')
        h.putheader('Content-length', len(data))
        if localAuthHeader is not None:
            h.putheader(*localAuthHeader)
        elif creds is not None: 
            h.putheader('Authorization', 'Basic %s' %
                    base64.encodestring('%s:%s' % (creds[0], creds[1])).replace('\n',''))
        elif locallogin is not None:
            h.putheader('PegasusAuthorization', 'Local "%s"' % locallogin)

        for hdr in headers:
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
            body = response.read()
    
            if response.status != 200:
                if response.status == 401:
                    if numTries >= tryLimit:
                        raise AuthError(response.reason)
                    if not local:
                        raise AuthError(response.reason)
                    authChal = response.getheader('WWW-Authenticate', '')
                    if 'openwbem' in response.getheader('Server', ''):
                        if 'OWLocal' not in authChal:
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
                                localAuthHeader = ('Authorization',
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
                                localAuthHeader = ('PegasusAuthorization',
                                    'Local "%s:%s:%s"' % \
                                            (locallogin, file, cookie))
                                continue
                        except ValueError:
                            pass

                    raise AuthError(response.reason)
                if response.getheader('CIMError', None) is not None and \
                   response.getheader('PGErrorDetail', None) is not None:
                    import urllib
                    raise Error(
                        'CIMError: %s: %s' %
                        (response.getheader('CIMError'),
                         urllib.unquote(response.getheader('PGErrorDetail'))))
                raise Error('HTTP error: %s' % response.reason)
    
        except httplib.BadStatusLine, arg:
            raise Error("The web server returned a bad status line: '%s'" % arg)
        except socket.error, arg:
            raise Error("Socket error: %s" % (arg,))
        except socket.sslerror, arg:
            raise Error("SSL error: %s" % (arg,))

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
