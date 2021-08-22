
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
**Experimental:** *New in pywbem 0.9 as experimental.*

Operation recorder interface and implementations.
"""

from __future__ import print_function, absolute_import
import io
from collections import namedtuple
try:
    from collections import OrderedDict
except ImportError:
    from ordereddict import OrderedDict  # pylint: disable=import-error
from datetime import datetime, timedelta
import logging

import six
import yaml
import yamlloader

from ._nocasedict import NocaseDict
from ._cim_obj import CIMInstance, CIMInstanceName, CIMClass, CIMClassName, \
    CIMProperty, CIMMethod, CIMParameter, CIMQualifier, \
    CIMQualifierDeclaration
from ._cim_types import CIMInt, CIMFloat, CIMDateTime
from ._exceptions import CIMError
from ._logging import LOGGER_API_CALLS_NAME, LOGGER_HTTP_NAME
from ._utils import _ensure_unicode, _format


__all__ = ['BaseOperationRecorder', 'TestClientRecorder',
           'LogOperationRecorder',
           'OpArgs', 'OpResult', 'HttpRequest', 'HttpResponse']

if six.PY2:
    # pylint: disable=invalid-name, undefined-variable
    _Longint = long  # noqa: F821
else:
    # pylint: disable=invalid-name
    _Longint = int

OpArgsTuple = namedtuple("OpArgsTuple", ["method", "args"])


class OpArgs(OpArgsTuple):
    """
    A named tuple representing the name and input arguments of the invocation
    of a :class:`~pywbem.WBEMConnection` method.

    **Experimental:** *New in pywbem 0.9 as experimental.*

    Attributes:

      ~OpArgs.method (:term:`unicode string`):
        Name of the :class:`~pywbem.WBEMConnection` method.

      ~OpArgs.args (:class:`py:dict`):
        Dictionary of input arguments (both positional and keyword-based).
    """
    __slots__ = ()

    def __repr__(self):
        return _format(
            "OpArgs("
            "method={s.method!A}, "
            "args={s.args!A})",
            s=self)


OpResultTuple = namedtuple("OpResultTuple", ["ret", "exc"])


class OpResult(OpResultTuple):
    """
    A named tuple representing the result of the invocation of a
    :class:`~pywbem.WBEMConnection` method.

    **Experimental:** *New in pywbem 0.9 as experimental.*

    Attributes:

      ~OpResult.ret (:class:`py:object`):
        Return value, if the method returned.
        `None`, if the method raised an exception.

        Note that `None` may be a legitimate return value, so the test for
        exceptions should be done based upon the :attr:`exc` variable.

      ~OpResult.exc (:exc:`~py:exceptions.Exception`):
        Exception object, if the method raised an exception.
        `None`, if the method returned.
    """
    __slots__ = ()

    def __repr__(self):
        return _format(
            "OpResult("
            "ret={s.ret!A}, "
            "exc={s.exc!A})",
            s=self)


HttpRequestTuple = namedtuple("HttpRequestTuple",
                              ["version", "url", "target", "method", "headers",
                               "payload"])


class HttpRequest(HttpRequestTuple):
    """
    A named tuple representing the HTTP request sent by the WBEM client.

    **Experimental:** *New in pywbem 0.9 as experimental.*

    Attributes:

      ~HttpRequest.version (:term:`number`):
        HTTP version from the request line (10 for HTTP/1.0, 11 for HTTP/1.1).

      ~HttpRequest.url (:term:`unicode string`):
        URL of the WBEM server (e.g. 'https://myserver.acme.com:15989').

      ~HttpRequest.target (:term:`unicode string`):
        Target URL segment as stated in request line (e.g. '/cimom').

      ~HttpRequest.method (:term:`unicode string`):
        HTTP method as stated in the request line (e.g. "POST").

      ~HttpRequest.headers (:class:`py:dict`):
        A dictionary of all HTTP header fields:

        * key (:term:`unicode string`): Name of the header field
        * value (:term:`unicode string`): Value of the header field

      ~HttpRequest.payload (:term:`unicode string`):
        HTTP payload, i.e. the CIM-XML string.
    """
    __slots__ = ()

    def __repr__(self):
        return _format(
            "HttpRequest("
            "version={s.version!A}, "
            "url={s.url!A}, "
            "target={s.target!A}, "
            "method={s.method!A}, "
            "headers={s.headers!A}, "
            "payload={s.payload!A})",
            s=self)


HttpResponseTuple = namedtuple("HttpResponseTuple",
                               ["version", "status", "reason", "headers",
                                "payload"])


class HttpResponse(HttpResponseTuple):
    """
    A named tuple representing the HTTP response received by the WBEM client.

    **Experimental:** *New in pywbem 0.9 as experimental.*

    Attributes:

      ~HttpResponse.version (:term:`number`):
        HTTP version from the response line (10 for HTTP/1.0, 11 for HTTP/1.1).

      ~HttpResponse.status (:term:`number`):
        HTTP status code from the response line (e.g. 200).

      ~HttpResponse.reason (:term:`unicode string`):
        HTTP reason phrase from the response line (e.g. "OK").

      ~HttpResponse.headers (:class:`py:dict`):
        A dictionary of all HTTP header fields:

        * key (:term:`unicode string`): Name of the header field
        * value (:term:`unicode string`): Value of the header field

      ~HttpResponse.payload (:term:`unicode string`):
        HTTP payload, i.e. the CIM-XML string.
    """
    __slots__ = ()

    def __repr__(self):
        return _format(
            "HttpResponse("
            "version={s.version!A}, "
            "status={s.status!A}, "
            "reason={s.reason!A}, "
            "headers={s.headers!A}, "
            "payload={s.payload!A})",
            s=self)


class BaseOperationRecorder(object):
    # pylint: disable=too-many-instance-attributes
    """
    Abstract base class defining the interface to an operation recorder,
    that records the WBEM operations executed in a connection to a WBEM
    server.

    **Experimental:** *New in pywbem 0.9 as experimental.*

    An operation recorder can be added to a connection via the
    :meth:`~pywbem.WBEMConnection.add_operation_recorder` method. The operation
    recorders of a connection can be retrieved via the
    :attr:`~pywbem.WBEMConnection.operation_recorders` property.

    Each operation that is executed on a connection will cause the
    :meth:`record` method of those operation recorders of the connection to be
    called, that are enabled.

    After being added to a connection, an operation recorder is enabled. It can
    be disabled and re-enabled using the
    :meth:`~pywbem.BaseOperationRecorder.disable` and
    :meth:`~pywbem.BaseOperationRecorder.enable` methods, respectively.
    This can be used to temporarily pause the recorder.
    """

    def __init__(self):
        self._enabled = True
        self._conn_id = None
        self.reset()

    def copy(self):
        """
        *New in pywbem 1.3.*

        Abstract: Return a deep copy of the object with internal state reset.
        """
        raise NotImplementedError  # Must be implemented by subclasses

    def enable(self):
        """
        Enable the recorder.

        *New in pywbem 0.10.*
        """
        self._enabled = True

    def disable(self):
        """
        Disable the recorder.

        *New in pywbem 0.10.*
        """
        self._enabled = False

    @property
    def enabled(self):
        """
        Indicate whether the recorder is enabled.

        *New in pywbem 0.10.*
        """
        return self._enabled

    @staticmethod
    def open_file(filename, file_mode='w'):
        """
        A static convenience function that performs the open of the recorder
        file correctly for different versions of Python.

        *New in pywbem 0.10.*

        This covers the issue where the file should be opened in text mode but
        that is done differently in Python 2 and Python 3.

        The returned file-like object must be closed by the caller.

        Parameters:

          filename(:term:`string`):
            Name of the file where the recorder output will be written

          file_mode(:term:`string`):
            Optional file mode.  The default is 'w' which overwrites any
            existing file.  if 'a' is used, the data is appended to any
            existing file.

        Returns:

          File-like object.

        Example::

            recorder = TestClientRecorder(...)
            recorder_file = recorder.open_file('recorder.log')

            . . . # Perform WBEM operations using the recorder

            recorder_file.close()
        """
        # pylint: disable=consider-using-with
        return io.open(filename, file_mode, encoding='utf-8')

    def reset(self, pull_op=None):
        """Reset all the attributes in the class. This also allows setting
        the pull_op attribute that defines whether the operation is to be
        a traditional or pull operation.
        This does NOT reset _conn.id as that exists through the life of
        the connection.
        """
        self._pywbem_method = None
        self._pywbem_args = None

        self._pywbem_result_ret = None
        self._pywbem_result_exc = None

        self._http_request_version = None
        self._http_request_url = None
        self._http_request_target = None
        self._http_request_method = None
        self._http_request_headers = None
        self._http_request_payload = None

        self._http_response_version = None
        self._http_response_status = None
        self._http_response_reason = None
        self._http_response_headers = None
        self._http_response_payload = None
        self._pull_op = pull_op

    def stage_wbem_connection(self, wbem_connection):
        """
        Stage information about the connection. Used only by
        LogOperationRecorder.
        """
        pass

    def stage_pywbem_args(self, method, **kwargs):
        """
        Set requst method and all args.
        Normally called before the cmd is executed to record request
        parameters
        """
        # pylint: disable=attribute-defined-outside-init
        self._pywbem_method = method
        self._pywbem_args = kwargs

    def stage_pywbem_result(self, ret, exc):
        """ Set Result return info or exception info"""
        # pylint: disable=attribute-defined-outside-init
        self._pywbem_result_ret = ret
        self._pywbem_result_exc = exc

    def stage_http_request(self, conn_id, version, url, target, method, headers,
                           payload):
        """Set request HTTP information including url, headers, etc."""
        # pylint: disable=attribute-defined-outside-init
        self._http_request_version = version
        self._http_request_conn_id = conn_id
        self._http_request_url = url
        self._http_request_target = target
        self._http_request_method = method
        self._http_request_headers = headers
        self._http_request_payload = payload

    # pylint: disable=unused-argument
    def stage_http_response1(self, conn_id, version, status, reason, headers):
        """Set response http info including headers, status, etc.
           conn_id unused here. Used in log"""
        # pylint: disable=attribute-defined-outside-init
        self._http_response_version = version
        self._http_response_status = status
        self._http_response_reason = reason
        self._http_response_headers = headers

    def stage_http_response2(self, payload):
        """Stage second part of http response, the payload"""
        # pylint: disable=attribute-defined-outside-init
        self._http_response_payload = payload

    def record_staged(self):
        """Encode staged information on request and result to output"""
        if self.enabled:
            pwargs = OpArgs(
                self._pywbem_method,
                self._pywbem_args)
            pwresult = OpResult(
                self._pywbem_result_ret,
                self._pywbem_result_exc)
            httpreq = HttpRequest(
                self._http_request_version,
                self._http_request_url,
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

        This function is called only when the recorder is enabled, i.e. it
        does not need to check for recorder enablement.

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

            `None`, if no HTTP request had been sent (e.g. because an exception
            was raised before getting there).

          http_response (:class:`~pywbem.HttpResponse`):
            The HTTP response received by the :class:`~pywbem.WBEMConnection`
            method that is recorded.

            `None`, if no HTTP response had been received (e.g. because an
            exception was raised before getting there).
        """
        raise NotImplementedError


class LogOperationRecorder(BaseOperationRecorder):
    """
    A recorder that logs certain aspects of the WBEM operations driven by
    pywbem users to Python loggers.

    **Experimental:** *New in pywbem 0.11 and redesigned in pywbem 0.12 as
    experimental.*

    This recorder supports two Python loggers:

    * API logger (Python logger name: `'pywbem.api'`) - Logs API calls and
      returns, for the :class:`~pywbem.WBEMConnection` methods that drive WBEM
      operations (see :ref:`WBEM operations`). This logs the API parameters and
      results, including CIM objects/exceptions. It also logs the creation of
      :class:`~pywbem.WBEMConnection` objects to capture connection information
      in order to determine the connection to which a particular log record
      belongs.

    * HTTP logger (Python logger name: `'pywbem.http'`) - Logs HTTP requests
      and responses between the pywbem client and WBEM server. This logs the
      HTTP request data and response data including HTTP headers and CIM-XML
      payload.

    All logging calls are at the :attr:`py:logging.DEBUG` logging level.
    """
    def __init__(self, conn_id, detail_levels=None):
        """
        Parameters:

          conn_id (:term:`connection id`):
            String that represents an id for a particular connection
            that is used to build the name of each logger. The logger names
            are uniqueqly idenfified by the conn_id suffix to the logger name
            (ex.pywbem.ops.1-2343) so that each WBEMConnection could be
            logged with a separate logger.

          detail_levels (:class:`py:dict`):
            Dictionary identifying the detail level for one or both of
            the loggers.
            Key: Simple logger name (e.g. 'api').
            Value: Detail level, either a string from
            :data:`~pywbem._logging.LOG_DETAIL_LEVELS`, or an integer that
            specifies the maximum size of each log record.
        """
        super(LogOperationRecorder, self).__init__()

        self._conn_id = conn_id

        self.detail_levels = {}

        # logging only occurs if the corresponding detail level is not None
        self.api_detail_level = None
        self.http_detail_level = None
        self.api_maxlen = None
        self.http_maxlen = None
        self.set_detail_level(detail_levels)

        # build name for logger for this connection
        if conn_id:
            self.apilogger = logging.getLogger(
                _format("{0}.{1}", LOGGER_API_CALLS_NAME, conn_id))
            self.httplogger = logging.getLogger(
                _format("{0}.{1}", LOGGER_HTTP_NAME, conn_id))
        else:
            self.apilogger = logging.getLogger(LOGGER_API_CALLS_NAME)
            self.httplogger = logging.getLogger(LOGGER_HTTP_NAME)

    def copy(self):
        """
        *New in pywbem 1.3.*

        Return a deep copy of the object with internal state reset.

        The user-specifiable attributes of the object are deep-copied, and all
        other internal state (e.g. staged operations) is reset.
        """
        cpy = LogOperationRecorder(
            conn_id=self._conn_id,
            detail_levels=self.detail_levels,
        )  # init makes copies of mutable parameters
        return cpy

    def set_detail_level(self, detail_levels):
        """
        Sets the detail levels from the input dictionary in detail_levels.

        The input dictionary is copied.
        """
        if detail_levels is None:
            return

        self.detail_levels = dict(detail_levels)  # dict is mutable, so we copy
        if 'api' in detail_levels:
            self.api_detail_level = detail_levels['api']
        if 'http' in detail_levels:
            self.http_detail_level = detail_levels['http']
        if isinstance(self.api_detail_level, int):
            self.api_maxlen = self.api_detail_level
        if isinstance(self.http_detail_level, int):
            self.http_maxlen = self.http_detail_level

    def stage_wbem_connection(self, wbem_connection):
        """
        Log connection information. This includes the connection id (conn_id)
        that is output with the log entry. This entry is logged if either
        http or api loggers are enable. It honors both the logger and
        detail level of either api logger if defined or http logger if defined.
        If the api logger does not exist, the output shows this as an http
        loggger output since we do not want to create an api logger for this
        specific output
        """
        self._conn_id = wbem_connection.conn_id

        if self.enabled:
            if self.api_detail_level is not None:
                logger = self.apilogger
                detail_level = self.api_detail_level
                max_len = self.api_maxlen
            elif self.http_detail_level is not None:
                logger = self.httplogger
                detail_level = self.http_detail_level
                max_len = self.http_maxlen
            else:
                return

            if logger.isEnabledFor(logging.DEBUG):
                conn_data = str(wbem_connection) if detail_level == 'summary' \
                    else repr(wbem_connection)

                if max_len and (len(conn_data) > max_len):
                    conn_data = conn_data[:max_len] + '...'
                logger.debug('Connection:%s %s', self._conn_id, conn_data)

    def stage_pywbem_args(self, method, **kwargs):
        """
        Log request method and all args.
        Normally called before the cmd is executed to record request
        parameters.
        This method does not support the summary detail_level because
        that seems to add little info to the log that is not also in the
        response.
        """
        # pylint: disable=attribute-defined-outside-init
        self._pywbem_method = method
        if self.enabled and self.api_detail_level is not None and \
                self.apilogger.isEnabledFor(logging.DEBUG):

            # Order kwargs.  Note that this is done automatically starting
            # with python 3.6
            kwstr = ', '.join([('{0}={1!r}'.format(key, kwargs[key]))
                               for key in sorted(six.iterkeys(kwargs))])

            if self.api_maxlen and (len(kwstr) > self.api_maxlen):
                kwstr = kwstr[:self.api_maxlen] + '...'
            # pylint: disable=bad-continuation
            self.apilogger.debug('Request:%s %s(%s)', self._conn_id, method,
                                 kwstr)

    def stage_pywbem_result(self, ret, exc):
        """
        Log result return or exception parameter. This method provides varied
        type of formatting based on the detail_level parameter and the
        data in ret.
        """
        def format_result(ret, max_len):
            """ format ret as repr while clipping it to max_len if
                max_len is not None.
            """
            # Format the 'summary' and 'paths' detail_levels
            if self.api_detail_level == 'summary':  # pylint: disable=R1705
                if isinstance(ret, list):
                    if ret:
                        ret_type = type(ret[0]).__name__ if ret else ""
                        return _format("list of {0}; count={1}",
                                       ret_type, len(ret))
                    return "Empty"

                ret_type = type(ret).__name__
                if hasattr(ret, 'classname'):
                    name = ret.classname
                elif hasattr(ret, 'name'):
                    name = ret.name
                else:
                    name = ""
                return _format("{0} {1}", ret_type, name)

            elif self.api_detail_level == 'paths':
                if isinstance(ret, list):
                    if ret:
                        if hasattr(ret[0], 'path'):
                            result_fmt = ', '.join(
                                [_format("{0!A}", str(p.path)) for p in ret])
                        else:
                            result_fmt = _format("{0!A}", ret)
                    else:
                        result_fmt = ''
                else:
                    if hasattr(ret, 'path'):
                        result_fmt = _format("{0!A}", str(ret.path))
                    else:
                        result_fmt = _format("{0!A}", ret)

            else:
                result_fmt = _format("{0!A}", ret)

            if max_len and (len(result_fmt) > max_len):
                result_fmt = result_fmt[:max_len] + '...'
            return result_fmt

        if self.enabled and self.api_detail_level is not None and \
                self.apilogger.isEnabledFor(logging.DEBUG):
            if exc:  # format exception
                # exceptions are always either all or reduced length
                result = format_result(
                    _format("{0}({1})", exc.__class__.__name__, exc),
                    self.api_maxlen)

                return_type = 'Exception'

            else:    # format result
                # test if type is tuple (subclass of tuple but not type tuple)
                qrc = ""
                # format open/pull response
                # pylint: disable=unidiomatic-typecheck
                if isinstance(ret, tuple) and type(ret) is not tuple:
                    try:    # test if field instances or paths
                        rtn_data = ret.instances
                        data_str = 'instances'
                    except AttributeError:
                        rtn_data = ret.paths
                        data_str = 'paths'

                    try:    # test for query_result_class
                        qrc = _format(
                            ", query_result_class={0}",
                            ret.query_result_class)
                    except AttributeError:
                        pass

                    result = _format(
                        "{0}(context={1}, eos={2}{3}, {4}={5})",
                        type(ret).__name__, ret.context, ret.eos, qrc,
                        data_str, format_result(rtn_data, self.api_maxlen))

                # format enumerate response except not open/pull
                elif isinstance(ret, list):
                    try:    # test for query_result_class
                        qrc = _format(
                            ", query_result_class={0}",
                            ret.query_result_class)
                    except AttributeError:
                        pass
                    ret_fmtd = format_result(ret, self.api_maxlen)
                    result = _format("{0}{1}", qrc, ret_fmtd)

                # format single return object
                else:
                    result = format_result(ret, self.api_maxlen)

                return_type = 'Return'

            self.apilogger.debug('%s:%s %s(%s)', return_type, self._conn_id,
                                 self._pywbem_method, result)

    def stage_http_request(self, conn_id, version, url, target, method, headers,
                           payload):
        """Log request HTTP information including url, headers, etc."""
        if self.enabled and self.http_detail_level is not None and \
                self.httplogger.isEnabledFor(logging.DEBUG):
            # pylint: disable=attribute-defined-outside-init
            # if Auth header, mask data
            if 'Authorization' in headers:
                authtype, cred = headers['Authorization'].split(' ')
                headers['Authorization'] = _format(
                    "{0} {1}", authtype, 'X' * len(cred))

            header_str = ' '.join('{0}:{1!r}'.format(k, v)
                                  for k, v in headers.items())
            if self.http_detail_level == 'summary':
                upayload = ""
            elif isinstance(payload, six.binary_type):
                upayload = payload.decode('utf-8')
            else:
                upayload = payload
            if self.http_maxlen and (len(payload) > self.http_maxlen):
                upayload = upayload[:self.http_maxlen] + '...'
            upayload = repr(upayload)
            if upayload.startswith("u'"):
                upayload = upayload[1:]
            self.httplogger.debug('Request:%s %s %s %s %s %s %s',
                                  conn_id, method, target, version, url,
                                  header_str, upayload)

    def stage_http_response1(self, conn_id, version, status, reason, headers):
        """Set response http info including headers, status, etc. """
        # pylint: disable=attribute-defined-outside-init
        self._http_response_version = version
        self._http_response_status = status
        self._http_response_reason = reason
        self._http_response_headers = headers
        self._http_response_conn_id = conn_id

    def stage_http_response2(self, payload):
        """Log complete http response, including response1 and payload"""

        # required because http code uses sending all None to reset
        # parameters. We ignore that
        if not self._http_response_version and not payload:
            return
        if self.enabled and self.http_detail_level is not None and \
                self.httplogger.isEnabledFor(logging.DEBUG):
            if self._http_response_headers:
                header_str = \
                    ' '.join('{0}:{1!r}'.format(k, v)
                             for k, v in self._http_response_headers.items())
            else:
                header_str = ''

            if self.http_detail_level == 'summary':
                upayload = ""
            elif self.http_maxlen and (len(payload) > self.http_maxlen):
                upayload = (_ensure_unicode(payload[:self.http_maxlen]) +
                            '...')
            else:
                upayload = _ensure_unicode(payload)
            upayload = repr(upayload)
            if upayload.startswith("u'"):
                upayload = upayload[1:]

            self.httplogger.debug('Response:%s %s:%s %s %s %s',
                                  self._http_response_conn_id,
                                  self._http_response_status,
                                  self._http_response_reason,
                                  self._http_response_version,
                                  header_str, upayload)

    def record_staged(self):
        """
        Not used for logging. The logs are output in the various
        stage... methods methods
        """
        pass

    def record(self, pywbem_args, pywbem_result, http_request, http_response):
        """Not used for logging"""
        pass


class TestClientRecorder(BaseOperationRecorder):
    """
    An operation recorder that generates test cases for each recorded
    operation.

    **Experimental:** *New in pywbem 0.9 as experimental.*

    The test cases are in the YAML format suitable for the
    `test_client` unit test module of the pywbem project.
    """

    # HTTP header fields to exclude when creating the testcase
    # (in lower case)
    EXCLUDE_REQUEST_HEADERS = [
        'authorization',
        'content-length',
        'content-type',
    ]
    EXCLUDE_RESPONSE_HEADERS = [
        'content-length',
        'content-type',
    ]

    # Dummy server URL and credentials for use in generated test case
    TESTCASE_URL = 'http://acme.com:80'
    TESTCASE_USER = 'username'
    TESTCASE_PASSWORD = 'password'

    def __init__(self, fp):
        """
        Parameters:

          fp (file):
            An open file that each test case will be written to.  This file
            should have been opened in text mode.

            Since there are differences between Python 2 and 3 in opening
            files in text mode, the static method
            :meth:`~pywbem.BaseOperationRecorder.open_file`
            can be used to open the file.

            Alternatively, the Python 2/3 compatible :func:`py:io.open` can be
            used.

        Examples::

          recorder = TestClientRecorder(
              BaseOperationRecorder.open_file('recorder.log'))

          recorder = TestClientRecorder(
              io.open('recorder.log', mode='w', encoding='utf-8')
        """
        super(TestClientRecorder, self).__init__()
        self._fp = fp

    def copy(self):
        """
        *New in pywbem 1.3.*

        Return a copy of the object with internal state reset and reusing the
        file-like object.

        The attribute for the `fp` init parameter is reused by the returned
        object without copying it, and any other internal state (e.g. staged
        operations) is reset.
        """
        cpy = TestClientRecorder(fp=self._fp)
        return cpy

    def record(self, pywbem_args, pywbem_result, http_request, http_response):
        """
        Function that records the invocation of a single
        :class:`~pywbem.WBEMConnection` method, by appending a corresponding
        test case to the file.

        Parameters: See :meth:`pywbem.BaseOperationRecorder.record`.
        """

        testcase = OrderedDict()
        testcase['name'] = pywbem_args.method
        testcase['description'] = 'Generated by TestClientRecorder'

        tc_pywbem_request = OrderedDict()
        tc_pywbem_request['url'] = TestClientRecorder.TESTCASE_URL
        tc_pywbem_request['creds'] = [TestClientRecorder.TESTCASE_USER,
                                      TestClientRecorder.TESTCASE_PASSWORD]
        tc_pywbem_request['namespace'] = 'root/cimv2'
        tc_pywbem_request['timeout'] = 10
        tc_pywbem_request['debug'] = False
        tc_operation = OrderedDict()
        tc_operation['pywbem_method'] = pywbem_args.method
        for arg_name in pywbem_args.args:
            tc_operation[arg_name] = self.toyaml(pywbem_args.args[arg_name])
        tc_pywbem_request['operation'] = tc_operation
        testcase['pywbem_request'] = tc_pywbem_request

        tc_pywbem_response = OrderedDict()
        if pywbem_result.ret is not None:
            yaml_txt = 'pullresult' if self._pull_op else 'result'
            tc_pywbem_response[yaml_txt] = self.toyaml(pywbem_result.ret)

        if pywbem_result.exc is not None:
            exc = pywbem_result.exc
            if isinstance(exc, CIMError):
                tc_pywbem_response['cim_status'] = self.toyaml(exc.status_code)
            else:
                tc_pywbem_response['exception'] = self.toyaml(
                    exc.__class__.__name__)
        testcase['pywbem_response'] = tc_pywbem_response

        tc_http_request = OrderedDict()
        if http_request is not None:
            tc_http_request['verb'] = http_request.method
            tc_http_request['url'] = TestClientRecorder.TESTCASE_URL
            if http_request.target:
                tc_http_request['url'] += http_request.target
            tc_request_headers = OrderedDict()
            if http_request.headers is not None:
                for hdr_name in http_request.headers:
                    if hdr_name.lower() not in \
                       TestClientRecorder.EXCLUDE_REQUEST_HEADERS:
                        tc_request_headers[hdr_name] = \
                            http_request.headers[hdr_name]
            tc_http_request['headers'] = tc_request_headers
            if http_request.payload is not None:
                data = http_request.payload.decode('utf-8')
                data = data.replace('><', '>\n<').strip()
            else:
                data = None
            tc_http_request['data'] = data
        testcase['http_request'] = tc_http_request

        tc_http_response = OrderedDict()
        if http_response is not None:
            tc_http_response['status'] = http_response.status
            tc_response_headers = OrderedDict()
            if http_response.headers is not None:
                for hdr_name in http_response.headers:
                    if hdr_name.lower() not in \
                       TestClientRecorder.EXCLUDE_RESPONSE_HEADERS:
                        tc_response_headers[hdr_name] = \
                            http_response.headers[hdr_name]
            tc_http_response['headers'] = tc_response_headers
            if http_response.payload is not None:
                data = http_response.payload.decode('utf-8')
                data = data.replace('><', '>\n<').strip()
            else:
                data = None
            tc_http_response['data'] = data
        else:
            tc_http_response['exception'] = "# Change this to a callback " \
                                            "function that causes this " \
                                            "condition."
        testcase['http_response'] = tc_http_response

        testcases = []
        testcases.append(testcase)

        # The file is open in text mode, so we produce a unicode string by
        # setting encoding=None and allow_unicode=True.
        data = yaml.dump(
            testcases, encoding=None, allow_unicode=True,
            default_flow_style=False, indent=4,
            Dumper=yamlloader.ordereddict.CSafeDumper)

        data = data.replace('\n\n', '\n')  # YAML dump duplicates newlines
        self._fp.write(data)
        self._fp.flush()

    def toyaml(self, obj):
        """
        Convert any allowable input argument to or return value from an
        operation method to an object that is ready for serialization into
        test_client yaml format.
        """

        # pylint: disable=unidiomatic-typecheck
        if isinstance(obj, tuple) and type(obj) is not tuple:
            # Handle namedtuple objects.
            # Because collections.namedtuple() is a factory function and there
            # is no common superclass for the generated namedtuple types other
            # than tuple itself, the detection of this case is somewhat
            # creative: The namedtuple object is an instance of tuple but does
            # not have type tuple.
            # In order to record the tuple item names, namedtuple objects are
            # converted to a dictionary first.
            ret_dict = obj._asdict()
            return self.toyaml(ret_dict)
        if isinstance(obj, (list, tuple)):
            # Note that namedtuple objects are handeled above.
            ret = []
            for item in obj:
                ret.append(self.toyaml(item))
            return ret
        if isinstance(obj, (dict, NocaseDict)):
            ret_dict = OrderedDict()
            for key in obj.keys():  # get keys in original case
                ret_dict[key] = self.toyaml(obj[key])
            return ret_dict
        if obj is None:
            return obj
        if isinstance(obj, six.binary_type):
            return obj.decode("utf-8")
        if isinstance(obj, six.text_type):
            return obj
        if isinstance(obj, bool):
            # The check for bool must be before any integer checks, because
            # bool is a subclass of int in Python.
            return obj
        if isinstance(obj, CIMInt):
            # CIMInt is _Longint and therefore may exceed the value range of
            # int in Python 2. Therefore, we convert it to _Longint.
            return _Longint(obj)
        if isinstance(obj, six.integer_types):
            # This case must be after CIMInt, because CIMInt is _Longint and
            # would match a long value in Python 2.
            # We don't convert six.integer_types to _Longint, because the value
            # fits into the provided type, and there is no need to convert it.
            # Note that in Python 2 (where that would make a difference), int
            # and long do not inherit from each other, so it is likely best if
            # we just don't convert.
            return obj
        if isinstance(obj, CIMFloat):
            return float(obj)
        if isinstance(obj, CIMDateTime):
            return str(obj)
        if isinstance(obj, datetime):
            return CIMDateTime(obj)
        if isinstance(obj, timedelta):
            return CIMDateTime(obj)
        if isinstance(obj, CIMInstance):
            ret_dict = OrderedDict()
            ret_dict['pywbem_object'] = 'CIMInstance'
            ret_dict['classname'] = self.toyaml(obj.classname)
            ret_dict['properties'] = self.toyaml(obj.properties)
            ret_dict['qualifiers'] = self.toyaml(obj.qualifiers)
            ret_dict['path'] = self.toyaml(obj.path)
            return ret_dict
        if isinstance(obj, CIMInstanceName):
            ret_dict = OrderedDict()
            ret_dict['pywbem_object'] = 'CIMInstanceName'
            ret_dict['classname'] = self.toyaml(obj.classname)
            ret_dict['namespace'] = self.toyaml(obj.namespace)
            ret_dict['host'] = self.toyaml(obj.host)
            ret_dict['keybindings'] = self.toyaml(obj.keybindings)
            return ret_dict
        if isinstance(obj, CIMClass):
            ret_dict = OrderedDict()
            ret_dict['pywbem_object'] = 'CIMClass'
            ret_dict['classname'] = self.toyaml(obj.classname)
            ret_dict['superclass'] = self.toyaml(obj.superclass)
            ret_dict['properties'] = self.toyaml(obj.properties)
            ret_dict['methods'] = self.toyaml(obj.methods)
            ret_dict['qualifiers'] = self.toyaml(obj.qualifiers)
            ret_dict['path'] = self.toyaml(obj.path)
            return ret_dict
        if isinstance(obj, CIMClassName):
            ret_dict = OrderedDict()
            ret_dict['pywbem_object'] = 'CIMClassName'
            ret_dict['classname'] = self.toyaml(obj.classname)
            ret_dict['host'] = self.toyaml(obj.host)
            ret_dict['namespace'] = self.toyaml(obj.namespace)
            return ret_dict
        if isinstance(obj, CIMProperty):
            ret_dict = OrderedDict()
            ret_dict['pywbem_object'] = 'CIMProperty'
            ret_dict['name'] = self.toyaml(obj.name)
            ret_dict['value'] = self.toyaml(obj.value)
            ret_dict['type'] = self.toyaml(obj.type)
            ret_dict['reference_class'] = self.toyaml(obj.reference_class)
            ret_dict['embedded_object'] = self.toyaml(obj.embedded_object)
            ret_dict['is_array'] = self.toyaml(obj.is_array)
            ret_dict['array_size'] = self.toyaml(obj.array_size)
            ret_dict['class_origin'] = self.toyaml(obj.class_origin)
            ret_dict['propagated'] = self.toyaml(obj.propagated)
            ret_dict['qualifiers'] = self.toyaml(obj.qualifiers)
            return ret_dict
        if isinstance(obj, CIMMethod):
            ret_dict = OrderedDict()
            ret_dict['pywbem_object'] = 'CIMMethod'
            ret_dict['name'] = self.toyaml(obj.name)
            ret_dict['return_type'] = self.toyaml(obj.return_type)
            ret_dict['class_origin'] = self.toyaml(obj.class_origin)
            ret_dict['propagated'] = self.toyaml(obj.propagated)
            ret_dict['parameters'] = self.toyaml(obj.parameters)
            ret_dict['qualifiers'] = self.toyaml(obj.qualifiers)
            return ret_dict
        if isinstance(obj, CIMParameter):
            ret_dict = OrderedDict()
            ret_dict['pywbem_object'] = 'CIMParameter'
            ret_dict['name'] = self.toyaml(obj.name)
            ret_dict['type'] = self.toyaml(obj.type)
            ret_dict['reference_class'] = self.toyaml(obj.reference_class)
            ret_dict['embedded_object'] = self.toyaml(obj.embedded_object)
            ret_dict['is_array'] = self.toyaml(obj.is_array)
            ret_dict['array_size'] = self.toyaml(obj.array_size)
            ret_dict['qualifiers'] = self.toyaml(obj.qualifiers)
            return ret_dict
        if isinstance(obj, CIMQualifier):
            ret_dict = OrderedDict()
            ret_dict['pywbem_object'] = 'CIMQualifier'
            ret_dict['name'] = self.toyaml(obj.name)
            ret_dict['value'] = self.toyaml(obj.value)
            ret_dict['type'] = self.toyaml(obj.type)
            ret_dict['propagated'] = self.toyaml(obj.propagated)
            ret_dict['tosubclass'] = self.toyaml(obj.tosubclass)
            ret_dict['toinstance'] = self.toyaml(obj.toinstance)
            ret_dict['overridable'] = self.toyaml(obj.overridable)
            ret_dict['translatable'] = self.toyaml(obj.translatable)
            return ret_dict
        if isinstance(obj, CIMQualifierDeclaration):
            ret_dict = OrderedDict()
            ret_dict['pywbem_object'] = 'CIMQualifierDeclaration'
            ret_dict['name'] = self.toyaml(obj.name)
            ret_dict['type'] = self.toyaml(obj.type)
            ret_dict['value'] = self.toyaml(obj.value)
            ret_dict['is_array'] = self.toyaml(obj.is_array)
            ret_dict['array_size'] = self.toyaml(obj.array_size)
            ret_dict['scopes'] = self.toyaml(obj.scopes)
            ret_dict['tosubclass'] = self.toyaml(obj.tosubclass)
            ret_dict['toinstance'] = self.toyaml(obj.toinstance)
            ret_dict['overridable'] = self.toyaml(obj.overridable)
            ret_dict['translatable'] = self.toyaml(obj.translatable)
            return ret_dict

        raise TypeError(
            _format("Invalid type in TestClientRecorder.toyaml(): {0} {1}",
                    obj.__class__.__name__, type(obj)))
