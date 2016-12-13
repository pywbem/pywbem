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
    from collections import OrderedDict
except ImportError:
    from ordereddict import OrderedDict
from datetime import datetime, timedelta
import yaml
import six

from .cim_obj import CIMInstance, CIMInstanceName, CIMClass, CIMClassName, \
    CIMProperty, CIMMethod, CIMParameter, CIMQualifier, \
    CIMQualifierDeclaration, NocaseDict
from .cim_types import CIMInt, CIMFloat, CIMDateTime
from .exceptions import CIMError

__all__ = ['BaseOperationRecorder', 'TestClientRecorder',
           'OpArgs', 'OpResult', 'HttpRequest', 'HttpResponse']

if six.PY2:
    _Longint = long  # noqa: F821
else:
    _Longint = int

OpArgs_tuple = namedtuple("OpArgs_tuple", ["method", "args"])


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


class OpArgs(OpArgs_tuple):
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


OpResult_tuple = namedtuple("OpResult_tuple", ["ret", "exc"])


class OpResult(OpResult_tuple):
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


HttpRequest_tuple = namedtuple("HttpRequest_tuple",
                               ["version", "url", "target", "method", "headers",
                                "payload"])


class HttpRequest(HttpRequest_tuple):
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


HttpResponse_tuple = namedtuple("HttpResponse_tuple",
                                ["version", "status", "reason", "headers",
                                 "payload"])


class HttpResponse(HttpResponse_tuple):
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

    def reset(self):
        """Reset all the attributes in the class"""
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

    def stage_pywbem_args(self, method, **kwargs):
        self._pywbem_method = method
        self._pywbem_args = kwargs

    def stage_pywbem_result(self, ret, exc):
        self._pywbem_result_ret = ret
        self._pywbem_result_exc = exc

    def stage_http_request(self, version, url, target, method, headers,
                           payload):
        self._http_request_version = version
        self._http_request_url = url
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
            tc_pywbem_response['result'] = self.toyaml(pywbem_result.ret)
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
                              default_flow_style=False)
        data = data.replace('\n\n', '\n')  # YAML dump duplicates newlines

        self._fp.write(data)
        self._fp.flush()

    def toyaml(self, obj):
        """
        Convert any allowable input argument to or return value from an
        operation method to an object that is ready for serialization into
        test_client yaml format.
        """
        if isinstance(obj, (list, tuple)):
            ret = []
            for item in obj:
                ret.append(self.toyaml(item))
            return ret
        elif isinstance(obj, (dict, NocaseDict)):
            ret = OrderedDict()
            for key in obj:
                ret[key] = self.toyaml(obj[key])
            return ret
        elif obj is None:
            return obj
        elif isinstance(obj, six.binary_type):
            return obj.decode("utf-8")
        elif isinstance(obj, six.text_type):
            return obj
        elif isinstance(obj, CIMInt):
            return _Longint(obj)
        elif isinstance(obj, (bool, int)):
            # The check for int must be after CIMInt, because CIMInt is int.
            return obj
        elif isinstance(obj, CIMFloat):
            return float(obj)
        elif isinstance(obj, CIMDateTime):
            return str(obj)
        elif isinstance(obj, (datetime, timedelta)):
            return CIMDateTime(obj)
        elif isinstance(obj, CIMInstance):
            ret = OrderedDict()
            ret['pywbem_object'] = 'CIMInstance'
            ret['classname'] = self.toyaml(obj.classname)
            ret['properties'] = self.toyaml(obj.properties)
            ret['path'] = self.toyaml(obj.path)
            return ret
        elif isinstance(obj, CIMInstanceName):
            ret = OrderedDict()
            ret['pywbem_object'] = 'CIMInstanceName'
            ret['classname'] = self.toyaml(obj.classname)
            ret['namespace'] = self.toyaml(obj.namespace)
            ret['keybindings'] = self.toyaml(obj.keybindings)
            return ret
        elif isinstance(obj, CIMClass):
            ret = OrderedDict()
            ret['pywbem_object'] = 'CIMClass'
            ret['classname'] = self.toyaml(obj.classname)
            ret['superclass'] = self.toyaml(obj.superclass)
            ret['properties'] = self.toyaml(obj.properties)
            ret['methods'] = self.toyaml(obj.methods)
            ret['qualifiers'] = self.toyaml(obj.qualifiers)
            return ret
        elif isinstance(obj, CIMClassName):
            ret = OrderedDict()
            ret['pywbem_object'] = 'CIMClassName'
            ret['classname'] = self.toyaml(obj.classname)
            ret['host'] = self.toyaml(obj.host)
            ret['namespace'] = self.toyaml(obj.namespace)
            return ret
        elif isinstance(obj, CIMProperty):
            ret = OrderedDict()
            ret['pywbem_object'] = 'CIMProperty'
            ret['name'] = self.toyaml(obj.name)
            ret['value'] = self.toyaml(obj.value)
            ret['type'] = self.toyaml(obj.type)
            ret['reference_class'] = self.toyaml(obj.reference_class)
            ret['embedded_object'] = self.toyaml(obj.embedded_object)
            ret['is_array'] = self.toyaml(obj.is_array)
            ret['array_size'] = self.toyaml(obj.array_size)
            ret['class_origin'] = self.toyaml(obj.class_origin)
            ret['propagated'] = self.toyaml(obj.propagated)
            ret['qualifiers'] = self.toyaml(obj.qualifiers)
            return ret
        elif isinstance(obj, CIMMethod):
            ret = OrderedDict()
            ret['pywbem_object'] = 'CIMMethod'
            ret['name'] = self.toyaml(obj.name)
            ret['return_type'] = self.toyaml(obj.return_type)
            ret['class_origin'] = self.toyaml(obj.class_origin)
            ret['propagated'] = self.toyaml(obj.propagated)
            ret['parameters'] = self.toyaml(obj.parameters)
            ret['qualifiers'] = self.toyaml(obj.qualifiers)
            return ret
        elif isinstance(obj, CIMParameter):
            ret = OrderedDict()
            ret['pywbem_object'] = 'CIMParameter'
            ret['name'] = self.toyaml(obj.name)
            ret['type'] = self.toyaml(obj.type)
            ret['reference_class'] = self.toyaml(obj.reference_class)
            ret['is_array'] = self.toyaml(obj.is_array)
            ret['array_size'] = self.toyaml(obj.array_size)
            ret['qualifiers'] = self.toyaml(obj.qualifiers)
            return ret
        elif isinstance(obj, CIMQualifier):
            ret = OrderedDict()
            ret['pywbem_object'] = 'CIMQualifier'
            ret['name'] = self.toyaml(obj.name)
            ret['value'] = self.toyaml(obj.value)
            ret['type'] = self.toyaml(obj.type)
            ret['propagated'] = self.toyaml(obj.propagated)
            ret['tosubclass'] = self.toyaml(obj.tosubclass)
            ret['toinstance'] = self.toyaml(obj.toinstance)
            ret['overridable'] = self.toyaml(obj.overridable)
            ret['translatable'] = self.toyaml(obj.translatable)
            return ret
        elif isinstance(obj, CIMQualifierDeclaration):
            ret = OrderedDict()
            ret['pywbem_object'] = 'CIMQualifierDeclaration'
            ret['name'] = self.toyaml(obj.name)
            ret['type'] = self.toyaml(obj.type)
            ret['value'] = self.toyaml(obj.value)
            ret['is_array'] = self.toyaml(obj.is_array)
            ret['array_size'] = self.toyaml(obj.array_size)
            ret['scopes'] = self.toyaml(obj.scopes)
            ret['tosubclass'] = self.toyaml(obj.tosubclass)
            ret['toinstance'] = self.toyaml(obj.toinstance)
            ret['overridable'] = self.toyaml(obj.overridable)
            ret['translatable'] = self.toyaml(obj.translatable)
            return ret
        else:
            raise TypeError("Invalid type in TestClientRecorder.toyaml(): "
                            "%s %s" % (obj.__class__.__name__, type(obj)))
