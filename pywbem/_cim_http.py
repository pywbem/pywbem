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


import re
import os
import base64
import ssl
import warnings
import urllib
import requests
from requests.packages import urllib3

from ._cim_obj import CIMClassName, CIMInstanceName
from ._cim_constants import DEFAULT_URL_SCHEME, DEFAULT_URL_PORT_HTTP, \
    DEFAULT_URL_PORT_HTTPS
from ._exceptions import ConnectionError, AuthError, TimeoutError, HTTPError, \
    HeaderParseError  # pylint: disable=redefined-builtin
from ._utils import _ensure_unicode, _ensure_bytes, _format
from ._warnings import RequestExceptionWarning

__all__ = []

_ON_RTD = os.environ.get('READTHEDOCS', None) == 'True'

# Debug the behavior of requests/urllib3 exceptions. This is only meant to be
# used by pywbem developers.
DEBUG_EXCEPTIONS = False

# HTTP connect timeout in seconds as float or int.
# This value is recognized in exception messages by comparing the value, so it
# should be a value that is unlikely to be used by users. It is rounded to
# integer precicion when shown in any messages.
HTTP_CONNECT_TIMEOUT = 9.99

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
            host = f'[{_host}-{_zone_index}]'
        else:
            host = f'[{_host}]'
    else:
        m = URL_IPV6_TEXT_PATTERN.match(host)
        if m:
            # It is an IPv6 address in RFC4007 text syntax
            _host = f'{m.group(1)}:{m.group(2)}'
            _zone_index = m.group(3)
            if _zone_index is not None:
                host = f'[{_host}-{_zone_index}]'
            else:
                host = f'[{_host}]'

    hostport = f'{host}:{port}'
    url = f'{scheme}://{hostport}'

    return scheme, hostport, url


def pywbem_requests_exception(exc, conn):
    """
    Return the pywbem exception to be used for re-raising a requests exception.
    """

    assert isinstance(exc, requests.exceptions.RequestException)

    message = exc.args[0]

    # Handle the case where requests puts an urllib3 exception into the
    # first argument, instead of a message.
    if isinstance(message, urllib3.exceptions.HTTPError):
        return pywbem_urllib3_exception(message, conn)

    if not isinstance(message, str):
        warnings.warn(
            f"requests exception {type(exc)} has a {type(message)} object "
            "as args[0] - converting to string",
            RequestExceptionWarning, 1)
        message = str(message)

    if isinstance(exc, requests.exceptions.SSLError):
        message = exc_message_amended(message, conn)
        new_exc = ConnectionError(message, conn_id=conn.conn_id)
        new_exc.__cause__ = None
        return new_exc

    if isinstance(exc, requests.exceptions.ReadTimeout):
        new_exc = TimeoutError(message, conn_id=conn.conn_id)
        new_exc.__cause__ = None
        return new_exc

    if isinstance(exc, requests.exceptions.RetryError):
        new_exc = TimeoutError(message, conn_id=conn.conn_id)
        new_exc.__cause__ = None
        return new_exc

    new_exc = ConnectionError(message, conn_id=conn.conn_id)
    new_exc.__cause__ = None
    return new_exc


def pywbem_urllib3_exception(exc, conn):
    """
    Return the pywbem exception to be used for re-raising a urllib3 exception.

    The urllib3.exceptions.MaxRetryError needs special treatment. It is
    used as follows, with the specified messages:

    - no target port:
      urllib3 version < 2.0

      HTTPSConnectionPool(host='localhost', port=5989): Max retries exceeded
      with url: /cimom (Caused by NewConnectionError('<urllib3.connection.
      HTTPSConnection object at 0x1105eaa30>: Failed to establish a new
      connection: [Errno 61] Connection refused'))

      urllib3 version >= 2.0

      WBEMConnection(url='localhost', certs= . . .): Max retries exceeded
      with url: /cimom (NewConnectionError('<urllib3.connection.
      HTTPSConnection object at 0x1105eaa30>: Failed to establish a new
      connection: [Errno 61] Connection refused'))

      TODO: Fix the item above.  Not sure if HTTPS Connection object.

    - port handled by paused container:

      urllib3.exceptions.MaxRetryError, with message: HTTPSConnectionPool(
      host='localhost', port=5989): Max retries exceeded with url: /cimom
      (Caused by ReadTimeoutError("HTTPSConnectionPool(host='localhost',
      port=5989): Read timed out. (read timeout=9.99)"))

      Note, the read timeout value is HTTP_CONNECT_TIMEOUT.

    - operation exceeded the timeout:

      urllib3 version < 2.0

      HTTPSConnectionPool(host='localhost', port=5989): Max retries exceeded
      with url: /cimom (Caused by ReadTimeoutError("HTTPSConnectionPool(
      host='localhost', port=5989): Read timed out. (read timeout=15)"))

      urllib3 version >= 2.0

      WBEMConnection(url='localhost', certs= . . .): Max retries exceeded
      with url: /cimom (Caused by ReadTimeoutError("HTTPSConnectionPool(
      host='localhost', port=5989): Read timed out. (read timeout=15)"))

    - server is stopped during operation and read retry = 0:

      HTTPSConnectionPool(host='localhost', port=5989): Max retries exceeded
      with url: /cimom (Caused by ProtocolError('Connection aborted.',
      RemoteDisconnected('Remote end closed connection without response')))

    - server is stopped during operation and read retry > 0:

      HTTPSConnectionPool(host='localhost', port=5989): Max retries exceeded
      with url: /cimom (Caused by SSLError(SSLEOFError(8, 'EOF occurred in
      violation of protocol (_ssl.c:1129)')))
    """
    assert isinstance(exc, urllib3.exceptions.HTTPError)

    message = exc.args[0]
    if not isinstance(message, str):
        warnings.warn(
            f"urllib3 exception {type(exc)} has a {type(message)} object "
            "as args[0] - converting to string",
            RequestExceptionWarning, 1)
        message = str(message)

    if isinstance(exc, urllib3.exceptions.MaxRetryError):

        # Get back to the "caused by" exception
        m = re.search(r'\(Caused by ([A-Za-z]+)\((.*)\)\)$', message)
        if m:
            exc_name = m.group(1)
            exc_message = m.group(2)
            if exc_message.startswith('"'):
                exc_message = exc_message.strip('"')
            elif exc_message.startswith("'"):
                exc_message = exc_message.strip("'")

        # Define pattern for search to remove unnecary info
            # Urllib3 ver 2, NewConnectionError will have WBEMConnection as
            # exc_message rather than ConnectionPool
            if re.search("^WBEMConnection(.*)$", exc_message):
                pattern = r'^WBEMConnection\(url=.*, creds=.*\): (.*)$'
            else:
                pattern = r'^HTTPS?ConnectionPool\(host=.*, port=.*\): (.*)$'
            # Remove unnecessary information from the message
            m = re.search(pattern, exc_message)
            if m:
                exc_message = m.group(1)
            else:
                m = re.search(r'^<[^>]+>[,:] (.*)$', exc_message)
                if m:
                    exc_message = m.group(1)
        else:
            warnings.warn(
                "urllib3 exception MaxRetryError does not match the "
                f"'Caused by' pattern: {message!r} - re-raising it directly",
                RequestExceptionWarning, 1)
            exc_name = exc.__class__.__name__
            exc_message = message

        if exc_name == 'ReadTimeoutError':
            m = re.search(r'\(read timeout=([0-9\.]+)\)', exc_message)
            if m:
                read_timeout = float(m.group(1))
                if read_timeout == HTTP_CONNECT_TIMEOUT:
                    exc_message = (
                        f"Could not send request to {conn.url} within "
                        f"{read_timeout:.0f} sec")
                    new_exc = ConnectionError(exc_message, conn_id=conn.conn_id)
                    new_exc.__cause__ = None
                    return new_exc

            # The operation timed out. We convert the not so meaningful
            # message "Read timed out. (read timeout=15)" to a message about
            # the operation.
            m = re.search(r'^Read timed out', exc_message)
            if m:
                exc_message = (
                    f"No response received from {conn.url} within "
                    f"{conn.timeout} sec")

            new_exc = TimeoutError(exc_message, conn_id=conn.conn_id)
            new_exc.__cause__ = None
            return new_exc

        if exc_name == 'NewConnectionError':
            new_exc = ConnectionError(exc_message, conn_id=conn.conn_id)
            new_exc.__cause__ = None
            return new_exc

        if exc_name == 'ProtocolError':
            new_exc = ConnectionError(exc_message, conn_id=conn.conn_id)
            new_exc.__cause__ = None
            return new_exc

        new_exc = ConnectionError(exc_message, conn_id=conn.conn_id)
        new_exc.__cause__ = None
        return new_exc

    new_exc = ConnectionError(message, conn_id=conn.conn_id)
    new_exc.__cause__ = None
    return new_exc


def exc_message_amended(message, conn):
    """
    Return the exception message, amended with additional text:

    * If the connection is HTTPS, the OpenSSL version is added.
    """
    if conn.scheme == 'https':
        message = message + \
            f"; OpenSSL version used: {ssl.OPENSSL_VERSION}"
    return message


def debug_exc(exc):
    """Debug: Return a debug message for the exception"""
    arg_strings = [
        f"exception: {type(exc)}",
        # f"dir(exc)={dir(exc)}",
        # f"dir(exc.request)={dir(exc.request)}",
        # f"dir(exc.response)={dir(exc.response)}",
    ]
    for i, arg in enumerate(exc.args):
        arg_strings.append(f"arg[{i}] ({type(arg)}) = {arg}")
    message = "; ".join(arg_strings)
    return message


def wbem_request(conn, req_data, cimxml_headers, target_type='server'):
    """
    Send an HTTP or HTTPS request to a WBEM server or WBEM listener and return
    the response.

    Parameters:

      conn (:class:`~pywbem.WBEMConnection`):
        WBEM connection to be used.

      req_data (:term:`string`):
        The CIM-XML formatted data to be sent as a request to the WBEM server
        or WBEM listener.

      cimxml_headers (:term:`py:iterable` of tuple(string,string)):
        Where each tuple contains: header name, header value.

        CIM-XML extension header fields for the request. The header value
        is a string (unicode or binary) that is not encoded, and the two-step
        encoding required by DSP0200 is performed inside of this function.

        A value of `None` is treated like an empty iterable.

      target_type (:term:`string`): Target type: 'server' or 'listener'.

    Returns:

        Tuple containing:

            The CIM-XML formatted response data from the WBEM server or
            WBEM listener, as a :term:`byte string` object.

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

    if target_type == 'server':
        target = '/cimom'
    else:
        target = ''
    target_url = f'{conn.url}{target}'

    # Make sure the data parameter is converted to a UTF-8 encoded byte string.
    # This is important because according to RFC2616, the Content-Length HTTP
    # header must be measured in Bytes (and the Content-Type header will
    # indicate UTF-8).
    req_body = _ensure_bytes(req_data)
    req_body = b'<?xml version="1.0" encoding="utf-8" ?>\n' + req_body

    req_headers = {
        'Content-type': 'application/xml; charset="utf-8"',
        'Content-length': f'{len(req_body)}',
    }
    req_headers.update(dict(cimxml_headers))

    if target_type == 'server' and conn.creds is not None:
        auth = f'{conn.creds[0]}:{conn.creds[1]}'
        auth64 = _ensure_unicode(base64.b64encode(
            _ensure_bytes(auth))).replace('\n', '')
        req_headers['Authorization'] = f'Basic {auth64}'

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
        try:
            if DEBUG_EXCEPTIONS:
                print("Debug: pywbem wbem_request: Calling session.post() "
                      f"with timeout=(connect={HTTP_CONNECT_TIMEOUT}, "
                      f"read={conn.timeout}) for {cimxml_headers[1][1]} on "
                      f"{cimxml_headers[2][1]} with "
                      f"{conn.session.adapters['https://'].max_retries}")
            resp = conn.session.post(
                target_url, data=req_body, headers=req_headers,
                timeout=(HTTP_CONNECT_TIMEOUT, conn.timeout))
        except Exception as _exc:
            if DEBUG_EXCEPTIONS:
                print("Debug: pywbem wbem_request: session.post() raised: "
                      f"{debug_exc(_exc)}")
            raise
    except requests.exceptions.RequestException as exc:
        raise pywbem_requests_exception(exc, conn)
    except urllib3.exceptions.HTTPError as exc:
        warnings.warn(
            f"requests raised an urllib3 exception {type(exc)} directly",
            RequestExceptionWarning, 1)
        raise pywbem_urllib3_exception(exc, conn)

    if target_type == 'server':
        # Get the optional response time header
        svr_resp_time = resp.headers.get('WBEMServerResponseTime', None)
        if svr_resp_time is not None:
            try:
                # convert to float and map from microsec to sec.
                svr_resp_time = float(svr_resp_time) / 1000000
            except ValueError:
                pass
    else:
        svr_resp_time = None

    if conn.operation_recorders:
        for recorder in conn.operation_recorders:
            recorder.stage_http_response1(
                conn.conn_id,
                resp.raw.version,
                resp.status_code,
                resp.reason,
                resp.headers)

    if resp.status_code != 200:

        if target_type == 'server' and resp.status_code == 401:

            msg = (f"WBEM server returned HTTP status {resp.status_code} "
                   f"({resp.reason}).")

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
            # For WBEM listeners, this header will never be there
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
            not resp_content_type.startswith('application/xml') and \
            not resp_content_type.startswith('text/xml'):
        raise HeaderParseError(
            "WBEM server returned invalid Content-type header: "
            f"{resp_content_type!r}",
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
    if isinstance(obj, str):
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
