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
import base64
import ssl
import six
from six.moves import urllib
import requests
from requests.packages import urllib3

from ._cim_obj import CIMClassName, CIMInstanceName
from ._cim_constants import DEFAULT_URL_SCHEME, DEFAULT_URL_PORT_HTTP, \
    DEFAULT_URL_PORT_HTTPS
from ._exceptions import ConnectionError, AuthError, TimeoutError, HTTPError, \
    HeaderParseError  # pylint: disable=redefined-builtin
from ._utils import _ensure_unicode, _ensure_bytes, _format

__all__ = []

_ON_RTD = os.environ.get('READTHEDOCS', None) == 'True'

HTTP_CONNECT_TIMEOUT = 10        # HTTP connect timeout in seconds

# Regexp pattern for an entire URL, with parsing items:
# (1) scheme (optional)
# (2) host (required) - may contain brackets and colons for IPv6 addresses
# (3) port (optional)
# (4) trailing path segments (optional)
URL_PATTERN = re.compile(
    r'^(?:(.*?)://)?([^/]+?)(?::([^:\[\]\-/]+?))?(/.*)?$')

# Regexp pattern for the host of a URL in (bracketed) RFC6874 URI format,
# with parsing items:
# (1) host (required)
# (2) zone ID (optional)
URL_IPV6_URI_PATTERN = re.compile(r'^\[(.+?)(?:[\-%](.+))?\]$')

# Regexp pattern for the host of a URL in (unbracketed) RFC4007 text format,
# with parsing items:
# (1):(2) host (required)
# (3) zone ID (optional)
URL_IPV6_TEXT_PATTERN = re.compile(r'^([^\[\]]*?):([^\[\]]*?)(?:%([^\[\]]+))?$')


def parse_url(url, allow_defaults=True):
    """
    Return a tuple (`scheme`, `hostport`, `url`) from the URL specified in the
    input URL.

    In the input URL, the host portion may be specified as a short or long
    host name, dotted IPv4 address, bracketed IPv6 address in the RFC6874 URI
    syntax, or unbracketed IPv6 address in the RFC4007 text syntax. In either
    format, IPv6 addresses may optionally have a zone index (aka scope ID),
    delimited with '-' or '%'.

    The returned `scheme` item is the normalized scheme portion of the input
    URL, as a unicode string. It is always in lower case. If not specified, it
    defaults to DEFAULT_URL_SCHEME. Only 'http' and 'https' are supported
    schemes, and ValueError is raised for invalid schemes.

    The returned `hostport` item is the normalized host and port number of the
    input URL in the format '{host}:{port}', as a unicode string.
    IPv6 addresses are always represented in (and converted to) RFC6874 URI
    syntax. If there is no port number specified in the input URL, the port
    in the returned `hostport` item defaults to DEFAULT_URL_PORT_HTTP or
    DEFAULT_URL_PORT_HTTP, dependent on the scheme.
    The returned `hostport` item should be used as the 'host' portion of CIM
    namespace paths.

    The returned `url` item is the normalized input URL, constructed from
    the returned `scheme` and `hostport` items.

    Defaults are only applied if allow_defaults=True. Otherwise, missing
    components cause ValueError to be raised.

    ValueError is raised in addition for invalid URLs or portions thereof.

    Examples for valid URLs can be found in the test program
    `tests/unittest/pywbem/test_cim_http.py`.

    Parameters:

      url (string): Input URL.

      allow_defaults (bool): If `True` allow defaults for scheme and
        port. If `False`, raise ValueError for missing scheme or port.

    Returns:

      tuple of (`scheme`, `hostport`, `url`)

    Raises:

      ValueError: Component missing (when allow_defaults = False)
      ValueError: Invalid URL
    """

    url = _ensure_unicode(url)

    m = URL_PATTERN.match(url)
    if not m:
        raise ValueError(
            _format("Invalid URL {0!A}", url))

    scheme = m.group(1)
    if not scheme:
        if not allow_defaults:
            raise ValueError(
                _format("Scheme component missing in URL {0!A}", url))
        scheme = DEFAULT_URL_SCHEME
    scheme = scheme.lower()
    if scheme not in ('http', 'https'):
        raise ValueError(
            _format("Unsupported scheme {0!A} in URL {1!A}", scheme, url))

    port = m.group(3)
    if not port:
        if not allow_defaults:
            raise ValueError(
                _format("Port component missing in URL {0!A}", url))
        if scheme == 'http':
            port = DEFAULT_URL_PORT_HTTP
        else:
            assert scheme == 'https'
            port = DEFAULT_URL_PORT_HTTPS
    try:
        port = int(port)
    except ValueError:
        raise ValueError(
            _format("Invalid port number {0!A} in URL {1!A}", port, url))

    host = m.group(2)
    assert host is not None  # This is guaranteed by the URL_PATTERN

    # Normalize the host for IPv6 addresses.
    m = URL_IPV6_URI_PATTERN.match(host)
    if m:
        # It is an IPv6 address in RFC6874 URI syntax
        _host = m.group(1)
        _zone_index = m.group(2)
        if _zone_index is not None:
            host = '[{0}-{1}]'.format(_host, _zone_index)
        else:
            host = '[{0}]'.format(_host)
    else:
        m = URL_IPV6_TEXT_PATTERN.match(host)
        if m:
            # It is an IPv6 address in RFC4007 text syntax
            _host = '{0}:{1}'.format(m.group(1), m.group(2))
            _zone_index = m.group(3)
            if _zone_index is not None:
                host = '[{0}-{1}]'.format(_host, _zone_index)
            else:
                host = '[{0}]'.format(_host)

    hostport = u'{0}:{1}'.format(host, port)
    url = u'{0}://{1}'.format(scheme, hostport)

    return scheme, hostport, url


def request_exc_message(exc, conn):
    """
    Return a reasonable exception message from a requests exception.

    The approach is to dig deep to the original reason, if the original
    exception is present, skipping irrelevant exceptions such as
    `urllib3.exceptions.MaxRetryError`, and eliminating useless object
    representations such as the connection pool object in
    `urllib3.exceptions.NewConnectionError`.

    Parameters:
      exc (requests.exceptions.RequestException): Exception
      conn (WBEMConnection): Connection that was used.

    Returns:
      string: A reasonable exception message from the specified exception.
    """
    if exc.args:
        if isinstance(exc.args[0], Exception):
            org_exc = exc.args[0]
            if isinstance(org_exc, urllib3.exceptions.MaxRetryError):
                reason_exc = org_exc.reason
                message = str(reason_exc)
            else:
                message = str(org_exc.args[0])
        else:
            message = str(exc.args[0])

        # Eliminate useless object repr at begin of the message
        m = re.match(r'^(\(<[^>]+>, \'(.*)\'\)|<[^>]+>: (.*))$', message)
        if m:
            message = m.group(2) or m.group(3)
    else:
        message = ""

    if conn.scheme == 'https':
        message = message + \
            "; OpenSSL version used: {}".format(ssl.OPENSSL_VERSION)

    return message


def wbem_request(conn, req_data, cimxml_headers):
    """
    Send an HTTP or HTTPS request to a WBEM server and return the response.

    Parameters:

      conn (:class:`~pywbem.WBEMConnection`):
        WBEM connection to be used.

      req_data (:term:`string`):
        The CIM-XML formatted data to be sent as a request to the WBEM server.

      cimxml_headers (:term:`py:iterable` of tuple(string,string)):
        Where each tuple contains: header name, header value.

        CIM-XML extension header fields for the request. The header value
        is a string (unicode or binary) that is not encoded, and the two-step
        encoding required by DSP0200 is performed inside of this function.

        A value of `None` is treated like an empty iterable.

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

    if cimxml_headers is None:
        cimxml_headers = []

    target = '/cimom'
    target_url = '{}{}'.format(conn.url, target)

    # Make sure the data parameter is converted to a UTF-8 encoded byte string.
    # This is important because according to RFC2616, the Content-Length HTTP
    # header must be measured in Bytes (and the Content-Type header will
    # indicate UTF-8).
    req_body = _ensure_bytes(req_data)
    req_body = b'<?xml version="1.0" encoding="utf-8" ?>\n' + req_body

    req_headers = {
        'Content-type': 'application/xml; charset="utf-8"',
        'Content-length': '{}'.format(len(req_body)),
    }
    req_headers.update(dict(cimxml_headers))

    if conn.creds is not None:
        auth = '{0}:{1}'.format(conn.creds[0], conn.creds[1])
        auth64 = _ensure_unicode(base64.b64encode(
            _ensure_bytes(auth))).replace('\n', '')
        req_headers['Authorization'] = 'Basic {0}'.format(auth64)

    if conn.operation_recorders:
        for recorder in conn.operation_recorders:
            recorder.stage_http_request(
                conn.conn_id, 11, conn.url, target, 'POST',
                dict(cimxml_headers), req_body)

            # We want clean response data when an exception is raised before
            # the HTTP response comes in:
            recorder.stage_http_response1(conn.conn_id, None, None, None, None)
            recorder.stage_http_response2(None)

    try:
        resp = conn.session.post(
            target_url, data=req_body, headers=req_headers,
            timeout=(HTTP_CONNECT_TIMEOUT, conn.timeout))
    except requests.exceptions.SSLError as exc:
        msg = request_exc_message(exc, conn)
        raise ConnectionError(msg, conn_id=conn.conn_id)
    except requests.exceptions.ConnectionError as exc:
        msg = request_exc_message(exc, conn)
        raise ConnectionError(msg, conn_id=conn.conn_id)
    except (requests.exceptions.ReadTimeout, requests.exceptions.RetryError) \
            as exc:
        msg = request_exc_message(exc, conn)
        raise TimeoutError(msg, conn_id=conn.conn_id)
    except requests.exceptions.RequestException as exc:
        msg = request_exc_message(exc, conn)
        raise ConnectionError(msg, conn_id=conn.conn_id)

    # Get the optional response time header
    svr_resp_time = resp.headers.get('WBEMServerResponseTime', None)
    if svr_resp_time is not None:
        try:
            # convert to float and map from microsec to sec.
            svr_resp_time = float(svr_resp_time) / 1000000
        except ValueError:
            pass

    if conn.operation_recorders:
        for recorder in conn.operation_recorders:
            recorder.stage_http_response1(
                conn.conn_id,
                resp.raw.version,
                resp.status_code,
                resp.reason,
                resp.headers)

    if resp.status_code != 200:

        if resp.status_code == 401:

            msg = "WBEM server returned HTTP status {0} ({1}).". \
                format(resp.status_code, resp.reason)

            # According to RFC2016/2017, the server must include a
            # WWW-Authenticate header in the response when returning 401.
            # Pywbem treats this header as optional.

            # According to RFC2016/2017, the value of that header must be a
            # comma-separated list of auth schemes, where the Basic
            # auth scheme typically looks like:
            #    Basic realm="somerealm"
            # Some data points of Basic auth schemes that have been observed:
            #    Basic "hostname:port"
            # Pywbem attempts to accomodate all of that.

            server_auths = resp.headers.get('WWW-Authenticate', None)
            if server_auths:
                server_auths = server_auths.split(',')
            else:
                server_auths = []
            server_auths = [sa.split(' ')[0] for sa in server_auths]
            if 'Basic' not in server_auths:
                # If client and server do not have a commonly supported
                # HTTP auth scheme, that is a more severe issue before it
                # even gets to things like invalid credentials or permissions.
                msg += _format(
                    " Server does not support HTTP authentication scheme "
                    "'Basic' supported by pywbem, but only {0!A}.",
                    ', '.join(server_auths))
            else:
                msg += _format(
                    " This is most likely an issue with userid/password, but "
                    "for servers that implement resource access control it "
                    "might also be an issue with the permissions of the "
                    "userid.")
            raise AuthError(msg, conn_id=conn.conn_id)

        cimerror_hdr = resp.headers.get('CIMError', None)
        cimdetails = {}
        if cimerror_hdr is not None:
            pgdetails_hdr = resp.headers.get('PGErrorDetail', None)
            if pgdetails_hdr is not None:
                cimdetails['PGErrorDetail'] = \
                    urllib.parse.unquote(pgdetails_hdr)
        raise HTTPError(
            resp.status_code, resp.reason, cimerror_hdr, cimdetails,
            conn_id=conn.conn_id, request_data=req_body)

    # status code 200
    resp_content_type = resp.headers.get('Content-type', None)
    if resp_content_type is not None and \
            not resp_content_type.startswith('application/xml'):
        raise HeaderParseError(
            "pywbem detected invalid content-type in HTTP response: {}".
            format(resp_content_type),
            conn_id=conn.conn_id, request_data=req_body,
            response_data=resp.text)

    resp_body = resp.content

    if conn.operation_recorders:
        for recorder in conn.operation_recorders:
            recorder.stage_http_response2(resp_body)

    return resp_body, svr_resp_time


def max_repr(text, max_len=1000):
    """
    Return the input text as a Python string representation (i.e. using repr())
    that is limited to a maximum length.
    """
    if text is None:
        text_repr = 'None'
    elif len(text) > max_len:
        text_repr = repr(text[0:max_len]) + '...'
    else:
        text_repr = repr(text)
    return text_repr


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
