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
Operation recorder interface and implementations.
"""

from __future__ import print_function, absolute_import
from collections import namedtuple
import yaml


__all__ = ['BaseOperationRecorder', 'TestClientRecorder',
           'OpArgs', 'OpResult', 'HttpRequest', 'HttpResponse']


OpArgs_tuple = namedtuple("OpArgs_tuple", ["method", "args"])

class OpArgs(OpArgs_tuple):
    """
    A named tuple representing the name and input arguments of the invocation
    of a :class:`~pywbem.WBEMConnection` method, with the following named fields
    and instance variables:

    Attributes:

      method (:term:`unicode string`):
        Name of the :class:`~pywbem.WBEMConnection` method.

      args (:class:`py:dict`):
        Dictionary of input arguments (both positional and keyword-based).
    """
    __slots__ = ()

    def __repr__(self):
        return "OpArgs(method={s.method!r}, args={s.args!r})".format(s=self)


OpResult_tuple = namedtuple("OpResult_tuple", ["ret", "exc"])

class OpResult(OpResult_tuple):
    """
    A named tuple representing the result of the invocation of a
    :class:`~pywbem.WBEMConnection` method, with the following named fields
    and instance variables:

    Attributes:

      ret (:class:`py:object`):
        Return value, if the method returned.
        `None`, if the method raised an exception.

        Note that `None` may be a legitimate return value, so the test for
        exceptions should be done based upon the :attr:`exc` variable.

      exc (:exc:`~py:exceptions.Exception`):
        Exception object, if the method raised an exception.
        `None`, if the method returned.
    """
    __slots__ = ()

    def __repr__(self):
        return "OpResult(ret={s.ret!r}, exc={s.exc!r})".format(s=self)


HttpRequest_tuple = namedtuple("HttpRequest_tuple",
                               ["version", "target", "method", "headers",
                                "payload"])

class HttpRequest(HttpRequest_tuple):
    """
    A named tuple representing the HTTP request sent by the WBEM client, with
    the following named fields and instance variables:

    Attributes:

      version (:term:`number`):
        HTTP version from the request line (10 for HTTP/1.0, 11 for HTTP/1.1).

      target (:term:`unicode string`):
        Target URL as stated in request line.

      method (:term:`unicode string`):
        HTTP method as stated in the request line (e.g. "POST").

      headers (:class:`py:dict`):
        A dictionary of all HTTP header fields:

        * key (:term:`unicode string`): Name of the header field
        * value (:term:`unicode string`): Value of the header field

      payload (:term:`unicode string`):
        HTTP payload, i.e. the CIM-XML string.
    """
    __slots__ = ()

    def __repr__(self):
        return "HttpRequest(version={s.version!r}, target={s.target!r}, " \
               "method={s.method!r}, headers={s.headers!r}, " \
               "payload={s.payload!r})".format(s=self)


HttpResponse_tuple = namedtuple("HttpResponse_tuple",
                               ["version", "status", "reason", "headers",
                                "payload"])

class HttpResponse(HttpResponse_tuple):
    """
    A named tuple representing the HTTP response received by the WBEM client,
    with the following named fields and instance variables:

    Attributes:

      version (:term:`number`):
        HTTP version from the response line (10 for HTTP/1.0, 11 for HTTP/1.1).

      status (:term:`number`):
        HTTP status code from the response line (e.g. 200).

      reason (:term:`unicode string`):
        HTTP reason phrase from the response line (e.g. "OK").

      headers (:class:`py:dict`):
        A dictionary of all HTTP header fields:

        * key (:term:`unicode string`): Name of the header field
        * value (:term:`unicode string`): Value of the header field

      payload (:term:`unicode string`):
        HTTP payload, i.e. the CIM-XML string.
    """
    __slots__ = ()

    def __repr__(self):
        return "HttpResponse(version={s.version!r}, status={s.status!r}, " \
               "reason={s.reason!r}, headers={s.headers!r}, " \
               "payload={s.payload!r})".format(s=self)


class BaseOperationRecorder(object):
    """
    Abstract base class defining the interface to an operation recorder,
    that records the WBEM operations executed in a connection to a WBEM
    server.

    An operation recorder can be registered by setting the
    :attr:`~pywbem.WBEMConnection.operation_recorder` instance
    attribute of the :class:`~pywbem.WBEMConnection` object to an
    object of a subclass of this base class.

    When an operation recorder is registered on a connection, each operation
    that is executed on the connection will cause the :meth:`record`
    method of the operation recorder object to be called.
    """

    def __init__(self):
        self.reset()

    def reset(self):
        self._pywbem_method = None
        self._pywbem_args = None

        self._pywbem_result_ret = None
        self._pywbem_result_exc = None

        self._http_request_version = None
        self._http_request_target = None
        self._http_request_method = None
        self._http_request_headers = None
        self._http_request_payload = None

        self._http_response_version = None
        self._http_response_status = None
        self._http_response_reason = None
        self._http_response_headers = None
        self._http_response_payload = None

    def stage_pywbem_args(self, method, **kwargs):
        self._pywbem_method = method
        self._pywbem_args = kwargs

    def stage_pywbem_result(self, ret, exc):
        self._pywbem_result_ret = ret
        self._pywbem_result_exc = exc

    def stage_http_request(self, version, target, method, headers, payload):
        self._http_request_version = version
        self._http_request_target = target
        self._http_request_method = method
        self._http_request_headers = headers
        self._http_request_payload = payload

    def stage_http_response1(self, version, status, reason, headers):
        self._http_response_version = version
        self._http_response_status = status
        self._http_response_reason = reason
        self._http_response_headers = headers

    def stage_http_response2(self, payload):
        self._http_response_payload = payload

    def record_staged(self):
        pwargs = OpArgs(
            self._pywbem_method,
            self._pywbem_args)
        pwresult = OpResult(
            self._pywbem_result_ret,
            self._pywbem_result_exc)
        httpreq = HttpRequest(
            self._http_request_version,
            self._http_request_target,
            self._http_request_method,
            self._http_request_headers,
            self._http_request_payload)
        httpresp = HttpResponse(
            self._http_response_version,
            self._http_response_status,
            self._http_response_reason,
            self._http_response_headers,
            self._http_response_payload)
        self.record(pwargs, pwresult, httpreq, httpresp)

    def record(self, pywbem_args, pywbem_result, http_request, http_response):
        """
        Function that is called to record a single WBEM operation, i.e. the
        invocation of a single :class:`~pywbem.WBEMConnection` method.

        Parameters:

          pywbem_args (:class:`~pywbem.OpArgs`):
            The name and input arguments of the :class:`~pywbem.WBEMConnection`
            method that is recorded.

          pywbem_result (:class:`~pywbem.OpResult`):
            The result (return value or exception) of the
            :class:`~pywbem.WBEMConnection` method that is recorded.

          http_request (:class:`~pywbem.HttpRequest`):
            The HTTP request sent by the :class:`~pywbem.WBEMConnection` method
            that is recorded.

          http_response (:class:`~pywbem.HttpResponse`):
            The HTTP response received by the :class:`~pywbem.WBEMConnection`
            method that is recorded.
        """
        raise NotImplementedError


class TestClientRecorder(BaseOperationRecorder):
    """
    An operation recorder that generates test cases for each recorded
    operation. The test cases are in the YAML format suitable for the
    `test_client` unit test module of the pywbem project.
    """

    def __init__(self, fp):
        """
        Parameters:

        fp (file):
          An open file that each test case will be written to.
        """
        super(TestClientRecorder, self).__init__()
        self._fp = fp

    def record(self, pywbem_args, pywbem_result, http_request, http_response):
        """
        Function that records the invocation of a single
        :class:`~pywbem.WBEMConnection` method, by appending a corresponding
        test case to the file.

        Parameters: See :meth:`pywbem.BaseOperationRecorder.record`.

        TODO: Implement this method.
        """

        self._fp.write("Debug: Recording operation %s with:\n" \
                       "  args: %s\n" \
                       "  result: %s\n" \
                       "  request: %s\n" \
                       "  response: %s\n" \
                       % (pywbem_args.method,
                          repr(pywbem_args.args),
                          repr(pywbem_result),
                          repr(http_request),
                          repr(http_response)))

