#
# (C) Copyright 2003-2005 Hewlett-Packard Development Company, L.P.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#   
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#   
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
#

# Author: Tim Potter <tpot@hp.com>
# Author: Martin Pool <mbp@hp.com>

'''
This module implements CIM operations over HTTP.

This module should not know anything about the fact that the data
being transferred is XML.  It is up to the caller to format the input
data and interpret the result.
'''

import sys, string, re, os, socket
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

    host, port, ssl = parse_url(url)

    if ssl:

        if x509 is not None:
            cert_file = x509.get('cert_file')
            key_file = x509.get('key_file', cert_file)
        else:
            cert_file = None
            key_file = None

        if verify_callback is not None:
            try:
                from OpenSSL import SSL
                ctx = SSL.Context(SSL.SSLv3_METHOD)
                ctx.set_verify(SSL.VERIFY_PEER, verify_callback)
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
        h = httplib.HTTPSConnection(host, port = port, key_file = key_file,
                                    cert_file = cert_file)
    else:
        h = httplib.HTTPConnection(host, port = port)

    data = '<?xml version="1.0" encoding="utf-8" ?>\n' + data

    h.putrequest('POST', '/cimom')

    h.putheader('Content-type', 'application/xml')
    h.putheader('Content-length', len(data))
    h.putheader('Authorization', 'Basic %s' %
                base64.encodestring('%s:%s' % (creds[0], creds[1]))[:-1])

    for hdr in headers:
        s = map(lambda x: string.strip(x), string.split(hdr, ":", 1))
        h.putheader(urllib.quote(s[0]), urllib.quote(s[1]))

    try:
        h.endheaders()
        h.send(data)

        response = h.getresponse()

        if response.status != 200:
            if response.status == 401:
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

    return response.read()


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
