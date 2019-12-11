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
import requests
import ssl
import six
from six.moves import urllib
from requests.packages import urllib3

from .cim_obj import CIMClassName, CIMInstanceName
from .exceptions import ConnectionError, AuthError, TimeoutError, HTTPError
from ._utils import _ensure_unicode, _ensure_bytes, _format

__all__ = ['DEFAULT_CA_CERT_PATHS']

_ON_RTD = os.environ.get('READTHEDOCS', None) == 'True'

# HTTP connect timeout in seconds
HTTP_CONNECT_TIMEOUT = 10

# Max number of HTTP connect retries
HTTP_CONNECT_RETRIES = 3

# Backoff factor for retries
HTTP_RETRY_BACKOFF_FACTOR = 0.1

# HTTP read timeout in seconds
HTTP_READ_TIMEOUT = 300

# Max number of HTTP read retries
HTTP_READ_RETRIES = 3

# Max number of HTTP redirects
HTTP_MAX_REDIRECTS = 5


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


def first_existing_path(paths):
    """
    Return the first existing path from the specified list of paths
    or single path. This path is cached and returned.
    If no path exists, None is returned.

    The path may refer to a file or a directory (or symlink to them).
    """
    # pylint: disable=protected-access
    if not hasattr(first_existing_path, '_path'):
        if isinstance(paths, six.string_types):
            paths = [paths]
        for path in paths:
            if os.path.exists(path):
                first_existing_path._path = path
                break
        else:
            first_existing_path._path = None
    return first_existing_path._path


# TODO: Using this class causes:
# ValueError("check_hostname requires server_hostname")
class DefaultCertsAdapter(requests.adapters.HTTPAdapter):
    """
    Transport adapter for requests that uses the system-provided SSL
    certificates.
    """

    def init_poolmanager(self, *args, **kwargs):
        ssl_context = ssl.create_default_context()
        ssl_context.load_default_certs()
        kwargs['ssl_context'] = ssl_context
        return super(DefaultCertsAdapter, self). \
            init_poolmanager(*args, **kwargs)


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


def request_exc_message(exc):
    """
    Return a reasonable exception message from a
    :exc:`request.exceptions.RequestException` exception.

    The approach is to dig deep to the original reason, if the original
    exception is present, skipping irrelevant exceptions such as
    `urllib3.exceptions.MaxRetryError`, and eliminating useless object
    representations such as the connection pool object in
    `urllib3.exceptions.NewConnectionError`.

    Parameters:
      exc (:exc:`~request.exceptions.RequestException`): Exception

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
    message = message + "; OpenSSL version used: {}".format(ssl.OPENSSL_VERSION)
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

    # if conn.creds:
    #     session.auth = conn.creds  # creates Authentication Basic header

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
        msg = request_exc_message(exc)
        raise ConnectionError(msg, conn_id=conn.conn_id)
    except requests.exceptions.ConnectionError as exc:
        msg = request_exc_message(exc)
        raise ConnectionError(msg, conn_id=conn.conn_id)
    except (requests.exceptions.ReadTimeout, requests.exceptions.RetryError) \
            as exc:
        msg = request_exc_message(exc)
        raise TimeoutError(msg, conn_id=conn.conn_id)
    except requests.exceptions.RequestException as exc:
        msg = request_exc_message(exc)
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
            raise AuthError(resp.reason, conn_id=conn.conn_id)
        cimerror_hdr = resp.headers.get('CIMError', None)
        if cimerror_hdr is not None:
            cimdetails = {}
            pgdetails_hdr = resp.headers.get('PGErrorDetail', None)
            if pgdetails_hdr is not None:
                cimdetails['PGErrorDetail'] = \
                    urllib.parse.unquote(pgdetails_hdr)
            raise HTTPError(resp.status_code, resp.reason,
                            cimerror_hdr, cimdetails, conn_id=conn.conn_id)
        raise HTTPError(resp.status_code, resp.reason, conn_id=conn.conn_id)

    # status code 200
    resp_content_type = resp.headers.get('Content-type', None)
    if resp_content_type is not None and \
            not resp_content_type.startswith('application/xml'):
        raise HTTPError(
            "Unknown content type in HTTP response: {}. "
            "Content (max.1000, decoded using {}): {}".
            format(resp_content_type, resp.encoding,
                   max_repr(resp.text, 1000)))

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
