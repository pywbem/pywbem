#!/usr/bin/env python

"""
Test _exceptions module.
"""

import pytest

# pylint: disable=wrong-import-position, wrong-import-order, invalid-name
# pylint: disable=redefined-builtin
from ...utils import import_installed
pywbem = import_installed('pywbem')
from pywbem import Error, ConnectionError, AuthError, HTTPError, TimeoutError, \
    ParseError, CIMXMLParseError, XMLParseError, HeaderParseError, \
    VersionError, CIMError, ModelError, ListenerError, \
    ListenerCertificateError, ListenerPortError, ListenerPromptError, \
    CIMInstance  # noqa: E402
# pylint: enable=wrong-import-position, wrong-import-order, invalid-name
# pylint: enable=redefined-builtin

# pylint: disable=enable=wrong-import-position, wrong-import-order, invalid-name

# {"blah: 0} instead of dict(blah=0)  would be faster but same functionality
# pylint: disable=use-dict-literal

# Test connection ID used for showing connection information in exception
# messages
TEST_CONN_ID = 'fake-conn-id'

# The expected connection information in exception messages
TEST_CONN_STR = f'Connection id: {TEST_CONN_ID}'
TEST_CONN_STR_NONE = 'Connection id: None'


def _assert_subscription(exc):
    """
    Test the exception defined by exc for required args.
    """

    # Access by subscription is only supported in Python 2:
    try:
        _ = exc[:]
    except TypeError:
        pass
    else:
        assert False, "Access by slice did not fail in Python 3"
    for i, _ in enumerate(exc.args):
        try:
            _ = exc[i]  # noqa: F841
        except TypeError:
            pass
        else:
            assert False, "Access by index did not fail in Python 3"


def _assert_connection(exc, conn_id_kwarg, exp_conn_str):
    """
    Test the exception defined by exc for connection related information.
    """
    exp_conn_id = conn_id_kwarg.get('conn_id', None)
    assert exc.conn_id is exp_conn_id
    assert exc.conn_str == exp_conn_str


@pytest.fixture(params=[
    # The exception classes with only 'message' as a positional argument,
    # along with a tuple of names of keyword arguments the class supports.
    (
        Error,
        ('conn_id',),
    ),
    (
        ConnectionError,
        ('conn_id',),
    ),
    (
        AuthError,
        ('conn_id',),
    ),
    (
        TimeoutError,
        ('conn_id',),
    ),
    (
        ParseError,
        ('conn_id', 'request_data', 'response_data'),
    ),
    (
        CIMXMLParseError,
        ('conn_id', 'request_data', 'response_data'),
    ),
    (
        XMLParseError,
        ('conn_id', 'request_data', 'response_data'),
    ),
    (
        HeaderParseError,
        ('conn_id', 'request_data', 'response_data'),
    ),
    (
        VersionError,
        ('conn_id',),
    ),
    (
        ModelError,
        ('conn_id',),
    ),
    (
        ListenerError,
        tuple(),
    ),
    (
        ListenerCertificateError,
        tuple(),
    ),
    (
        ListenerPortError,
        tuple(),
    ),
    (
        ListenerPromptError,
        tuple(),
    ),
], scope='module')
def message_exception_info(request):
    """
    Fixture representing variations of exception classes with only 'message'
    as a positional argument,

    Returns a tuple of:
    * Exception class.
    * tuple with names of keyword arguments supported by the exception.
    """
    return request.param


@pytest.fixture(params=[
    # message init argument for the exception classes
    None,
    '',
    'foo',
], scope='module')
def message_arg(request):
    """
    Fixture representing variations of the 'message' init argument for
    exception classes.

    Returns directly the message argument.
    """
    return request.param


@pytest.fixture(params=[
    # Tuple of (conn_id_kwarg, exp_conn_str)
    ({}, TEST_CONN_STR_NONE),
    (dict(conn_id=None), TEST_CONN_STR_NONE),
    (dict(conn_id=TEST_CONN_ID), TEST_CONN_STR),
], scope='module')
def conn_info(request):
    """
    Fixture representing variations for the conn_id keyword argument for all
    exception classes, and the corresponding expected connection info string.

    Returns a tuple of:
    * conn_id_kwarg: dict with the 'conn_id' keyword argument. May be empty.
    * exp_conn_str: Expected connection info string.
    """
    return request.param


@pytest.fixture(params=[
    # Tuple of (request_data_kwarg, exp_request_data)
    ({}, None),
    (dict(request_data=None), None),
    (dict(request_data=b'<CIM/>'), b'<CIM/>'),
], scope='module')
def request_data_info(request):
    """
    Fixture representing variations for the request_data keyword argument for
    some of the exception classes, and the expected request_data attribute.

    Returns a tuple of:
    * request_data_kwarg: dict with the 'request_data' keyword argument. May be
      empty.
    * exp_request_data: Expected request_data attribute value.
    """
    return request.param


@pytest.fixture(params=[
    # Tuple of (response_data_kwarg, exp_request_data)
    ({}, None),
    (dict(response_data=None), None),
    (dict(response_data=b'<CIM/>'), b'<CIM/>'),
], scope='module')
def response_data_info(request):
    """
    Fixture representing variations for the response_data keyword argument for
    some of the exception classes, and the expected response_data attribute.

    Returns a tuple of:
    * response_data_kwarg: dict with the 'response_data' keyword argument.
      May be empty.
    * exp_response_data: Expected response_data attribute value.
    """
    return request.param


def test_message_init(
        message_exception_info, message_arg, conn_info, request_data_info,
        response_data_info):
    # pylint: disable=redefined-outer-name
    """
    Test the initialization of exception classes with 'message' as the only
    positional argument.
    """
    exception_class, kwargs_names = message_exception_info
    conn_id_kwarg, exp_conn_str = conn_info
    request_data_kwarg, exp_request_data = request_data_info
    response_data_kwarg, exp_response_data = response_data_info

    kwargs = {}
    if 'conn_id' in kwargs_names:
        kwargs.update(conn_id_kwarg)
    if 'request_data' in kwargs_names:
        kwargs.update(request_data_kwarg)
    if 'response_data' in kwargs_names:
        kwargs.update(response_data_kwarg)

    # The code to be tested
    exc = exception_class(message_arg, **kwargs)

    # exc has no len()
    assert len(exc.args) == 1
    assert exc.args[0] == message_arg

    if 'request_data' in kwargs_names:
        assert exc.request_data == exp_request_data
    if 'response_data' in kwargs_names:
        assert exc.response_data == exp_response_data

    if 'conn_id' in kwargs_names:
        _assert_connection(exc, conn_id_kwarg, exp_conn_str)
    _assert_subscription(exc)


@pytest.fixture(params=[
    # The init arguments for the HTTPError exception class:
    # (status, reason, cimerror=None, cimdetails={})
    # Note: cimerror is the CIMError HTTP header field
    (200, 'OK'),
    (404, 'Not Found', 'instance xyz not found'),
    (404, 'Not Found', 'instance xyz not found', {'foo': 'bar'}),
], scope='module')
def httperror_args(request):
    """
    Fixture representing variations of positional init arguments for the
    HTTPError exception class.

    Returns a tuple of positional arguments for initializing a HTTPError
    exception object.
    """
    return request.param


def test_httperror(
        httperror_args, conn_info, request_data_info, response_data_info):
    # pylint: disable=redefined-outer-name
    """
    Test HTTPError exception class.
    """

    conn_id_kwarg, exp_conn_str = conn_info
    request_data_kwarg, exp_request_data = request_data_info
    response_data_kwarg, exp_response_data = response_data_info

    kwargs = {}
    kwargs.update(conn_id_kwarg)
    kwargs.update(request_data_kwarg)
    kwargs.update(response_data_kwarg)

    exc = HTTPError(*httperror_args, **kwargs)

    assert exc.status == httperror_args[0]
    assert exc.reason == httperror_args[1]
    if len(httperror_args) < 3:
        assert exc.cimerror is None  # default value
    else:
        assert exc.cimerror == httperror_args[2]
    if len(httperror_args) < 4:
        assert exc.cimdetails == {}  # default value (set in init)
    else:
        assert exc.cimdetails == httperror_args[3]

    assert exc.args[0] == exc.status
    assert exc.args[1] == exc.reason
    assert exc.args[2] == exc.cimerror
    assert exc.args[3] == exc.cimdetails
    assert len(exc.args) == 4

    assert exc.request_data == exp_request_data
    assert exc.response_data == exp_response_data

    _assert_connection(exc, conn_id_kwarg, exp_conn_str)
    _assert_subscription(exc)


@pytest.fixture(params=[
    # The CIM status codes for the CIMError exception class:
    # (code, name)
    # Note: We don't test the exact default description text.
    # Note: name = None means that the status code is invalid.
    (0, None),
    (1, 'CIM_ERR_FAILED'),
    (2, 'CIM_ERR_ACCESS_DENIED'),
    (3, 'CIM_ERR_INVALID_NAMESPACE'),
    (4, 'CIM_ERR_INVALID_PARAMETER'),
    (5, 'CIM_ERR_INVALID_CLASS'),
    (6, 'CIM_ERR_NOT_FOUND'),
    (7, 'CIM_ERR_NOT_SUPPORTED'),
    (8, 'CIM_ERR_CLASS_HAS_CHILDREN'),
    (9, 'CIM_ERR_CLASS_HAS_INSTANCES'),
    (10, 'CIM_ERR_INVALID_SUPERCLASS'),
    (11, 'CIM_ERR_ALREADY_EXISTS'),
    (12, 'CIM_ERR_NO_SUCH_PROPERTY'),
    (13, 'CIM_ERR_TYPE_MISMATCH'),
    (14, 'CIM_ERR_QUERY_LANGUAGE_NOT_SUPPORTED'),
    (15, 'CIM_ERR_INVALID_QUERY'),
    (16, 'CIM_ERR_METHOD_NOT_AVAILABLE'),
    (17, 'CIM_ERR_METHOD_NOT_FOUND'),
    (18, None),
    (19, None),
    (20, 'CIM_ERR_NAMESPACE_NOT_EMPTY'),
    (21, 'CIM_ERR_INVALID_ENUMERATION_CONTEXT'),
    (22, 'CIM_ERR_INVALID_OPERATION_TIMEOUT'),
    (23, 'CIM_ERR_PULL_HAS_BEEN_ABANDONED'),
    (24, 'CIM_ERR_PULL_CANNOT_BE_ABANDONED'),
    (25, 'CIM_ERR_FILTERED_ENUMERATION_NOT_SUPPORTED'),
    (26, 'CIM_ERR_CONTINUATION_ON_ERROR_NOT_SUPPORTED'),
    (27, 'CIM_ERR_SERVER_LIMITS_EXCEEDED'),
    (28, 'CIM_ERR_SERVER_IS_SHUTTING_DOWN'),
    (29, None),
    (30, None),
], scope='module')
def status_tuple(request):
    """
    Fixture representing variations of CIM status codes for initializing a
    CIMError exception class.

    Returns a tuple of positional arguments for initializing a CIMError
    exception object.
    """
    return request.param


@pytest.fixture(params=[
    None,
    [],
    [CIMInstance('CIM_Err')],
    [CIMInstance('CIM_Err1'), CIMInstance('CIM_Err2')],
], scope='module')
def error_instances(request):
    """
    Fixture representing variations of the list of instances that can be
    set on a CIMError exception.

    Returns a list of CIMInstance objects, or None.
    """
    return request.param


def test_cimerror_1(status_tuple, conn_info):
    # pylint: disable=redefined-outer-name
    """
    Test CIMError exception class with just status_code as input.
    """

    status_code, status_code_name = status_tuple
    conn_id_kwarg, exp_conn_str = conn_info

    invalid_code_name = f'Invalid status code {status_code}'
    invalid_code_desc = f'Invalid status code {status_code}'

    exc = CIMError(status_code, **conn_id_kwarg)

    assert exc.status_code == status_code
    if status_code_name is None:
        assert exc.status_description == invalid_code_desc
        assert exc.status_code_name == invalid_code_name
    else:
        assert isinstance(exc.status_description, str)
        assert exc.status_code_name == status_code_name

    assert exc.args[0] == exc.status_code
    assert exc.args[1] is None
    assert exc.args[2] is None
    assert len(exc.args) == 3

    _assert_connection(exc, conn_id_kwarg, exp_conn_str)
    _assert_subscription(exc)


def test_cimerror_2(status_tuple, conn_info):
    # pylint: disable=redefined-outer-name
    """
    Test CIMError exception class with status_code and description as input.
    """

    status_code, status_code_name = status_tuple
    conn_id_kwarg, exp_conn_str = conn_info

    invalid_code_name = f'Invalid status code {status_code}'
    input_desc = 'foo'

    exc = CIMError(status_code, input_desc, **conn_id_kwarg)

    assert exc.status_code == status_code
    assert exc.status_description == input_desc
    if status_code_name is None:
        assert exc.status_code_name == invalid_code_name
    else:
        assert exc.status_code_name == status_code_name

    assert exc.args[0] == exc.status_code
    assert exc.args[1] == input_desc
    assert exc.args[2] is None
    assert len(exc.args) == 3

    _assert_connection(exc, conn_id_kwarg, exp_conn_str)
    _assert_subscription(exc)


def test_cimerror_3(status_tuple, error_instances, conn_info):
    # pylint: disable=redefined-outer-name
    """
    Test CIMError exception class with status_code and instances as input.
    """

    status_code, status_code_name = status_tuple
    conn_id_kwarg, exp_conn_str = conn_info

    exc = CIMError(status_code, instances=error_instances, **conn_id_kwarg)

    assert exc.status_code == status_code
    if status_code_name is not None:
        assert exc.status_code_name == status_code_name

    assert exc.args[2] == error_instances
    assert len(exc.args) == 3

    _assert_connection(exc, conn_id_kwarg, exp_conn_str)
    _assert_subscription(exc)


@pytest.fixture(params=[
    # The exception classes for which the ParseError test should be done:
    ParseError,
    CIMXMLParseError,
    XMLParseError,
], scope='module')
def parseerror_class(request):
    """
    Fixture representing variations of the ParseError exception classes.

    Returns the exception class.
    """
    return request.param


@pytest.fixture(params=[
    # The init arguments for the ParseError exception class:
    # (message,)
    (None,),
    ('',),
    ('ill-formed XML',),
], scope='module')
def parseerror_args(request):
    """
    Fixture representing variations of positional init arguments for the
    ParseError exception class.

    Returns a tuple of positional arguments for initializing a ParseError
    exception object.
    """
    return request.param


def test_parseerror(parseerror_class, parseerror_args, conn_info):
    # pylint: disable=redefined-outer-name
    """
    Test ParseError exception class (and subclasses).
    """

    conn_id_kwarg, exp_conn_str = conn_info
    message = parseerror_args[0]

    exc = parseerror_class(*parseerror_args, **conn_id_kwarg)

    assert exc.args[0] == message
    assert len(exc.args) == 1

    _assert_connection(exc, conn_id_kwarg, exp_conn_str)
    _assert_subscription(exc)
