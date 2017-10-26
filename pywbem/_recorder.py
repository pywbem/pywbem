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

try:
    from collections import OrderedDict  # pylint: disable=import-error
except ImportError:
    from ordereddict import OrderedDict  # pylint: disable=import-error

from datetime import datetime, timedelta
import logging
import yaml
from yaml.representer import RepresenterError
import six

from .cim_obj import CIMInstance, CIMInstanceName, CIMClass, CIMClassName, \
    CIMProperty, CIMMethod, CIMParameter, CIMQualifier, \
    CIMQualifierDeclaration, NocaseDict
from .cim_types import CIMInt, CIMFloat, CIMDateTime
from .exceptions import CIMError
from ._logging import PywbemLoggers, LOG_OPS_CALLS_NAME, LOG_HTTP_NAME
from .config import DEFAULT_MAX_LOG_ENTRY_SIZE

if six.PY2:
    import codecs  # pylint: disable=wrong-import-order


__all__ = ['BaseOperationRecorder', 'TestClientRecorder',
           'LogOperationRecorder',
           'OpArgs', 'OpResult', 'HttpRequest', 'HttpResponse']

if six.PY2:
    _Longint = long  # noqa: F821
else:
    _Longint = int

OpArgsTuple = namedtuple("OpArgsTuple", ["method", "args"])


def _represent_ordereddict(dump, tag, mapping, flow_style=None):
    """PyYAML representer function for OrderedDict.
    This is needed for yaml.safe_dump() to support OrderedDict.

    Courtesy:
    http://blog.elsdoerfer.name/2012/07/26/make-pyyaml-output-an-ordereddict/
    """
    value = []
    node = yaml.MappingNode(tag, value, flow_style=flow_style)
    if dump.alias_key is not None:
        dump.represented_objects[dump.alias_key] = node
    best_style = True
    if hasattr(mapping, 'items'):
        mapping = mapping.items()
    for item_key, item_value in mapping:
        node_key = dump.represent_data(item_key)
        node_value = dump.represent_data(item_value)
        if not (isinstance(node_key, yaml.ScalarNode) and
                not node_key.style):
                    best_style = False    # pylint: disable=bad-indentation
        if not (isinstance(node_value, yaml.ScalarNode) and
                not node_value.style):
                    best_style = False    # pylint: disable=bad-indentation
        value.append((node_key, node_value))
    if flow_style is None:
        if dump.default_flow_style is not None:
            node.flow_style = dump.default_flow_style
        else:
            node.flow_style = best_style
    return node


yaml.SafeDumper.add_representer(
    OrderedDict,
    lambda dumper, value:
    _represent_ordereddict(dumper, u'tag:yaml.org,2002:map', value))


# Some monkey-patching for better diagnostics:
def _represent_undefined(self, data):
    """Raises flag for objects that cannot be represented"""
    raise RepresenterError("cannot represent an object: %s of type: %s; "
                           "yaml_representers: %r, "
                           "yaml_multi_representers: %r" %
                           (data, type(data), self.yaml_representers.keys(),
                            self.yaml_multi_representers.keys()))


yaml.SafeDumper.represent_undefined = _represent_undefined


class OpArgs(OpArgsTuple):
    """
    A named tuple representing the name and input arguments of the invocation
    of a :class:`~pywbem.WBEMConnection` method, with the following named fields
    and attributes:

    Attributes:

      method (:term:`unicode string`):
        Name of the :class:`~pywbem.WBEMConnection` method.

      args (:class:`py:dict`):
        Dictionary of input arguments (both positional and keyword-based).
    """
    __slots__ = ()

    def __repr__(self):
        return "OpArgs(method={s.method!r}, args={s.args!r})".format(s=self)


OpResultTuple = namedtuple("OpResultTuple", ["ret", "exc"])


class OpResult(OpResultTuple):
    """
    A named tuple representing the result of the invocation of a
    :class:`~pywbem.WBEMConnection` method, with the following named fields
    and attributes:

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


HttpRequestTuple = namedtuple("HttpRequestTuple",
                              ["version", "url", "target", "method", "headers",
                               "payload"])


class HttpRequest(HttpRequestTuple):
    """
    A named tuple representing the HTTP request sent by the WBEM client, with
    the following named fields and attributes:

    Attributes:

      version (:term:`number`):
        HTTP version from the request line (10 for HTTP/1.0, 11 for HTTP/1.1).

      url (:term:`unicode string`):
        URL of the WBEM server (e.g. 'https://myserver.acme.com:15989').

      target (:term:`unicode string`):
        Target URL segment as stated in request line (e.g. '/cimom').

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
        return "HttpRequest(version={s.version!r}, url={s.url!r}, " \
               "target={s.target!r}, method={s.method!r}, " \
               "headers={s.headers!r}, payload={s.payload!r})" \
               .format(s=self)


HttpResponseTuple = namedtuple("HttpResponseTuple",
                               ["version", "status", "reason", "headers",
                                "payload"])


class HttpResponse(HttpResponseTuple):
    """
    A named tuple representing the HTTP response received by the WBEM client,
    with the following named fields and attributes:

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
    # pylint: disable=too-many-instance-attributes
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
    method of the operation recorder object to be called, if the recorder is
    enabled.

    The operation recorder is by default enabled, and can be disabled and
    re-enabled using the :meth:`~pywbem.BaseOperationRecorder.disable` and
    :meth:`~pywbem.BaseOperationRecorder.enable` methods, respectively.
    This can be used to temporarily pause the recorder.
    """

    def __init__(self):
        self._enabled = True
        self._conn_id = None
        self.reset()

    def enable(self):
        """Enable the recorder."""
        self._enabled = True

    def disable(self):
        """Disable the recorder."""
        self._enabled = False

    @property
    def enabled(self):
        """Indicate whether the recorder is enabled."""
        return self._enabled

    @staticmethod
    def open_file(filename, file_mode='w'):
        """
        A static convience function that performs the open of the recorder file
        correctly for different versions of python.  This covers the
        issue where the file should be opened in text mode but that is
        done differently in python 2 and python 3

        Parameters:

          filename(:term:`string`):
            Name of the file where the recorder output will be written

          file_mode(:term:`string`):
            Optional file mode.  The default is 'w' which overwrites any
            existing file.  if 'a' is used, the data is appended to any
            existing file.

        Example::

            recorder = TestClientRecorder(
                BaseOperationRecorder.open_file('recorder.log'))
        """
        if six.PY2:
            # Open with codecs to define text mode
            return codecs.open(filename, mode=file_mode, encoding='utf-8')

        return open(filename, file_mode, encoding='utf8')

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
    An Operation Recorder that logs the information to a set of named logs.
    This recorder uses two named logs:

    LOG_OPS_CALLS_NAME - Logger for cim_operations method calls and responses

    LOG_HTTP_NAME - Logger for http_requests and responses

    This also implements a method to log information on each connection.

    All logging calls are at the debug level.
    """
    def __init__(self, max_log_entry_size=None):
        """
        Creates the the loggers and sets the max_log_size for each if
        the input parameter max_log_entry_size is not `None`.

        Parameters: (:term:`integer`)

          max_log_entry_size(:term:`integer`)
            The maximum size of each log entry. This is primarily to limit
            response sizes since they could be enormous.
            If `None`, no size limit and the full request or response is logged.
        """
        super(LogOperationRecorder, self).__init__()

        # compute max entry size for each logger
        max_sz = max_log_entry_size if max_log_entry_size \
            else DEFAULT_MAX_LOG_ENTRY_SIZE

        self.opslogger = logging.getLogger(LOG_OPS_CALLS_NAME)
        ops_logger_info = PywbemLoggers.get_logger_info(LOG_OPS_CALLS_NAME)
        opsdetaillevel = ops_logger_info[0] if ops_logger_info else None

        self.ops_max_log_size = max_sz if opsdetaillevel == 'min'  \
            else None

        self.httplogger = logging.getLogger(LOG_HTTP_NAME)
        http_logger_info = PywbemLoggers.get_logger_info(LOG_HTTP_NAME)
        httpdetaillevel = http_logger_info[0] if http_logger_info else None
        self.http_max_log_size = max_sz if httpdetaillevel == 'min' \
            else None

    def stage_wbem_connection(self, wbem_connection):
        """
        Log connection information. This includes the connection id
        that should remain throught the life of the connection.
        """
        self._conn_id = wbem_connection.conn_id

        if self.enabled:
            self.opslogger.debug('Connection:%s %r', self._conn_id,
                                 wbem_connection)

    def stage_pywbem_args(self, method, **kwargs):
        """
        Log request method and all args.
        Normally called before the cmd is executed to record request
        parameters.
        This method does not limit size of log record.
        """
        # pylint: disable=attribute-defined-outside-init
        self._pywbem_method = method
        if self.enabled and self.opslogger.isEnabledFor(logging.DEBUG):
            # Order kwargs.  Note that this is done automatically starting
            # with python 3.6
            kwstr = ', '.join([('{0}={1!r}'.format(key, kwargs[key]))
                               for key in sorted(six.iterkeys(kwargs))])

            self.opslogger.debug('Request:%s %s(%s)', self._conn_id, method,
                                 kwstr)

    def stage_pywbem_result(self, ret, exc):
        """
        Log result return or exception parameter. This function allows
        setting maximum size on the result parameter logged because response
        information can be very large
        .
        """
        def format_result(ret, max_len):
            """ format ret as repr while clipping it to max_len if
                max_len is not None.
            """
            result = '{0!r}'.format(ret)
            if max_len and (len(result) > max_len):
                result = (result[:max_len] + '...')
            return result

        if self.enabled and self.opslogger.isEnabledFor(logging.DEBUG):
            if exc:  # format exception
                result = format_result(
                    '%s(%s)' % (exc.__class__.__name__, exc),
                    self.ops_max_log_size)
            else:    # format result
                # test if type is tuple (subclass of tuple but not type tuple)
                # pylint: disable=unidiomatic-typecheck
                if isinstance(ret, tuple) and \
                        type(ret) is not tuple:  # pylint: disable=C0123
                    try:    # test if field instances or paths
                        rtn_data = ret.instances
                        data_str = 'instances'
                    except AttributeError:
                        rtn_data = ret.paths
                        data_str = 'paths'
                    rtn_data = format_result(rtn_data, self.ops_max_log_size)

                    try:    # test for query_result_class
                        qrc = ', query_result_class=%s' % ret.query_result_class
                    except AttributeError:
                        qrc = ""

                    result = "{0.__name__}(context={1}, eos={2}{3}, {4}={5})" \
                        .format(type(ret), ret.context, ret.eos, qrc,
                                data_str, rtn_data)
                else:
                    result = format_result(ret, self.ops_max_log_size)

            return_type = 'Exception' if exc else 'Return'

            self.opslogger.debug('%s:%s %s(%s)', return_type, self._conn_id,
                                 self._pywbem_method,
                                 result)

    def stage_http_request(self, conn_id, version, url, target, method, headers,
                           payload):
        """Log request HTTP information including url, headers, etc."""
        if self.enabled and self.httplogger.isEnabledFor(logging.DEBUG):
            # pylint: disable=attribute-defined-outside-init
            # if Auth header, mask data
            if 'Authorization' in headers:
                authtype, cred = headers['Authorization'].split(' ')
                headers['Authorization'] = '%s %s' % (authtype, 'X' * len(cred))

            header_str = ' '.join('{0}:{1!r}'.format(k, v)
                                  for k, v in headers.items())

            self.httplogger.debug('Request:%s %s %s %s %s %s\n    %s',
                                  conn_id, method, target, version, url,
                                  header_str, payload)

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
        if self.enabled and self.httplogger.isEnabledFor(logging.DEBUG):
            if self._http_response_headers:
                header_str = \
                    ' '.join('{0}:{1!r}'.format(k, v)
                             for k, v in self._http_response_headers.items())
            else:
                header_str = ''

            # format the payload possibly with max size limit
            payload = '%r' % payload.decode('utf-8')
            if self.http_max_log_size and \
                    (len(payload) > self.http_max_log_size):
                payload = (payload[:self.http_max_log_size] + '...')

            self.httplogger.debug('Response:%s %s:%s %s %s\n    %s',
                                  self._http_response_conn_id,
                                  self._http_response_status,
                                  self._http_response_reason,
                                  self._http_response_version,
                                  header_str,
                                  payload)

    def record_staged(self):
        """Not used for logging"""
        pass

    def record(self, pywbem_args, pywbem_result, http_request, http_response):
        """Not used for logging"""
        pass


class TestClientRecorder(BaseOperationRecorder):
    """
    An operation recorder that generates test cases for each recorded
    operation. The test cases are in the YAML format suitable for the
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

            Since there are differences between python 2 and 3 in opening
            files in text mode, the static method
            :meth:`~pywbem.BaseOperationRecorder.open_file`
            can be used to open the file or python 2/3 compatible open::

              from io import open
                  f = open('blah.log', encoding='utf-8')

        Example::

          recorder = TestClientRecorder(
              BaseOperationRecorder.open_file('recorder.log'))
        """
        super(TestClientRecorder, self).__init__()
        self._fp = fp

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

        # The file is open in text mode, so we produce a unicode string
        data = yaml.safe_dump(testcases, encoding=None, allow_unicode=True,
                              default_flow_style=False, indent=4)
        data = data.replace('\n\n', '\n')  # YAML dump duplicates newlines
        self._fp.write(data)
        self._fp.flush()

    def toyaml(self, obj):
        """
        Convert any allowable input argument to or return value from an
        operation method to an object that is ready for serialization into
        test_client yaml format.
        """

        # namedtuple is subclass of tuple so it is instance of tuple but
        # not type tuple. Cvt to dictionary and cvt dict to yaml.
        # pylint: disable=unidiomatic-typecheck
        if isinstance(obj, tuple) and type(obj) is not tuple:
            ret_dict = obj._asdict()
            return self.toyaml(ret_dict)
        if isinstance(obj, (list, tuple)):
            ret = []
            # This does not handle namedtuple
            for item in obj:
                ret.append(self.toyaml(item))
            return ret
        elif isinstance(obj, (dict, NocaseDict)):
            ret_dict = OrderedDict()
            for key in obj.keys():  # get keys in original case
                ret_dict[key] = self.toyaml(obj[key])
            return ret_dict
        elif obj is None:
            return obj
        elif isinstance(obj, six.binary_type):
            return obj.decode("utf-8")
        elif isinstance(obj, six.text_type):
            return obj
        elif isinstance(obj, CIMInt):
            return _Longint(obj)
        elif isinstance(obj, (bool, int)):
            # TODO ks jun 17 should the above be six.integertypes???
            # The check for int must be after CIMInt, because CIMInt is int.
            return obj
        elif isinstance(obj, CIMFloat):
            return float(obj)
        elif isinstance(obj, CIMDateTime):
            return str(obj)
        elif isinstance(obj, datetime):
            return CIMDateTime(obj)
        elif isinstance(obj, timedelta):
            return CIMDateTime(obj)
        elif isinstance(obj, CIMInstance):
            ret_dict = OrderedDict()
            ret_dict['pywbem_object'] = 'CIMInstance'
            ret_dict['classname'] = self.toyaml(obj.classname)
            ret_dict['properties'] = self.toyaml(obj.properties)
            ret_dict['path'] = self.toyaml(obj.path)
            return ret_dict
        elif isinstance(obj, CIMInstanceName):
            ret_dict = OrderedDict()
            ret_dict['pywbem_object'] = 'CIMInstanceName'
            ret_dict['classname'] = self.toyaml(obj.classname)
            ret_dict['namespace'] = self.toyaml(obj.namespace)
            ret_dict['keybindings'] = self.toyaml(obj.keybindings)
            return ret_dict
        elif isinstance(obj, CIMClass):
            ret_dict = OrderedDict()
            ret_dict['pywbem_object'] = 'CIMClass'
            ret_dict['classname'] = self.toyaml(obj.classname)
            ret_dict['superclass'] = self.toyaml(obj.superclass)
            ret_dict['properties'] = self.toyaml(obj.properties)
            ret_dict['methods'] = self.toyaml(obj.methods)
            ret_dict['qualifiers'] = self.toyaml(obj.qualifiers)
            return ret_dict
        elif isinstance(obj, CIMClassName):
            ret_dict = OrderedDict()
            ret_dict['pywbem_object'] = 'CIMClassName'
            ret_dict['classname'] = self.toyaml(obj.classname)
            ret_dict['host'] = self.toyaml(obj.host)
            ret_dict['namespace'] = self.toyaml(obj.namespace)
            return ret_dict
        elif isinstance(obj, CIMProperty):
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
        elif isinstance(obj, CIMMethod):
            ret_dict = OrderedDict()
            ret_dict['pywbem_object'] = 'CIMMethod'
            ret_dict['name'] = self.toyaml(obj.name)
            ret_dict['return_type'] = self.toyaml(obj.return_type)
            ret_dict['class_origin'] = self.toyaml(obj.class_origin)
            ret_dict['propagated'] = self.toyaml(obj.propagated)
            ret_dict['parameters'] = self.toyaml(obj.parameters)
            ret_dict['qualifiers'] = self.toyaml(obj.qualifiers)
            return ret_dict
        elif isinstance(obj, CIMParameter):
            ret_dict = OrderedDict()
            ret_dict['pywbem_object'] = 'CIMParameter'
            ret_dict['name'] = self.toyaml(obj.name)
            ret_dict['type'] = self.toyaml(obj.type)
            ret_dict['reference_class'] = self.toyaml(obj.reference_class)
            ret_dict['is_array'] = self.toyaml(obj.is_array)
            ret_dict['array_size'] = self.toyaml(obj.array_size)
            ret_dict['qualifiers'] = self.toyaml(obj.qualifiers)
            return ret_dict
        elif isinstance(obj, CIMQualifier):
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
        elif isinstance(obj, CIMQualifierDeclaration):
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
        else:
            raise TypeError("Invalid type in TestClientRecorder.toyaml(): "
                            "%s %s" % (obj.__class__.__name__, type(obj)))
