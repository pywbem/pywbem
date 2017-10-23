#!/usr/bin/env python

"""
Test exceptions module.
"""

from __future__ import absolute_import, print_function

import six
import pytest

from pywbem import Error, ConnectionError, AuthError, HTTPError, TimeoutError,\
    ParseError, VersionError, CIMError


def _assert_subscription(exc):
    """Test the exception defined by exc for required args"""
    # Access by subscription is only supported in Python 2:
    if six.PY2:
        assert exc[:] == exc.args
        for i, _ in enumerate(exc.args):
            assert exc[i] == exc.args[i]
            assert exc[i:] == exc.args[i:]
            assert exc[0:i] == exc.args[0:i]
    else:
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


# The exception classes for which the simple test should be done:
@pytest.fixture(params=[
    Error, ConnectionError, AuthError, TimeoutError, ParseError, VersionError
], scope='module')
def simple_class(request):
    """Return request.param as defined by the fixture. Representing
       the exception classes.
    """
    return request.param


# The init arguments for the simple exception classes:
@pytest.fixture(params=[
    (),
    ('foo',),
    ('foo', 42),
], scope='module')
def simple_args(request):
    """Return request.param defined by the pytest.fixture
       representing arguments for the exception class
    """
    return request.param


def test_simple(simple_class, simple_args):
    """Test exceptions classes and arguments using the
      testfixtures.
    """
    # pylint: disable=redefined-outer-name

    exc = simple_class(*simple_args)

    # exc has no len()
    assert len(exc.args) == len(simple_args)
    for i, _ in enumerate(simple_args):
        assert exc.args[i] == simple_args[i]
        assert exc.args[i:] == simple_args[i:]
        assert exc.args[0:i] == simple_args[0:i]
        assert exc.args[:] == simple_args[:]

    _assert_subscription(exc)


# The init arguments for the HTTPError exception class:
@pytest.fixture(params=[
    # (status, reason, cimerror=None, cimdetails={})
    (200, 'OK'),
    (404, 'Not Found', 'instance xyz not found'),
    (404, 'Not Found', 'instance xyz not found', 'foo'),
], scope='module')
def httperror_args(request):
    """Returns init arguments for the HTTPError exception class as
       pytest.fixture
    """
    return request.param


def test_httperror(httperror_args):  # pylint: disable=redefined-outer-name
    """Test httperror arguments from test fixture"""
    exc = HTTPError(*httperror_args)

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

    _assert_subscription(exc)


# The CIM status codes for the CIMError exception class:
@pytest.fixture(params=[
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
    """pytest.fixture returns status codes for CIMError
       exception
    """
    return request.param


def test_cimerror_1(status_tuple):  # pylint: disable=redefined-outer-name
    """Test cimerror"""
    status_code = status_tuple[0]
    status_code_name = status_tuple[1]

    invalid_code_name = 'Invalid status code %s' % status_code
    invalid_code_desc = 'Invalid status code %s' % status_code

    exc = CIMError(status_code)

    assert exc.status_code == status_code
    if status_code_name is None:
        assert exc.status_description == invalid_code_desc
        assert exc.status_code_name == invalid_code_name
    else:
        assert isinstance(exc.status_description, six.string_types)
        assert exc.status_code_name == status_code_name

    assert exc.args[0] == exc.status_code
    assert exc.args[1] is None
    assert len(exc.args) == 2

    _assert_subscription(exc)


def test_cimerror_2(status_tuple):  # pylint: disable=redefined-outer-name
    """Test cimerror status tuple from date in status-tuple fixture"""

    status_code = status_tuple[0]
    status_code_name = status_tuple[1]

    invalid_code_name = 'Invalid status code %s' % status_code

    input_desc = 'foo'

    exc = CIMError(status_code, input_desc)

    assert exc.status_code == status_code
    assert exc.status_description == input_desc
    if status_code_name is None:
        assert exc.status_code_name == invalid_code_name
    else:
        assert exc.status_code_name == status_code_name

    assert exc.args[0] == exc.status_code
    assert exc.args[1] == input_desc
    assert len(exc.args) == 2

    _assert_subscription(exc)
