#!/usr/bin/env python

"""
Test _warnings module.
"""

import pytest

# pylint: disable=wrong-import-position, wrong-import-order, invalid-name
# pylint: disable=redefined-builtin
from ...utils import import_installed
pywbem = import_installed('pywbem')
from pywbem import Warning, ToleratedServerIssueWarning, \
    ToleratedSchemaIssueWarning, MissingKeybindingsWarning, \
    OldNameFilterWarning, OldNameDestinationWarning  # noqa: E402
# pylint: enable=wrong-import-position, wrong-import-order, invalid-name
# pylint: enable=redefined-builtin

# Literal form {"blah: 0} faster than dict(blah=0) but same functionality
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
    # The warning classes for which the simple test should be done:
    Warning,
    ToleratedServerIssueWarning,
    ToleratedSchemaIssueWarning,
    MissingKeybindingsWarning,
    OldNameFilterWarning,
    OldNameDestinationWarning,
], scope='module')
def simple_class(request):
    """
    Fixture representing variations of the simple warning classes.

    Returns the warning class.
    """
    return request.param


@pytest.fixture(params=[
    # Tuple of positional init arguments for the simple warning classes
    (),
    ('',),
    ('foo',),
    ('foo', 42),
], scope='module')
def simple_args(request):
    """
    Fixture representing variations of positional init arguments for the simple
    warning classes.

    Returns a tuple of positional arguments for initializing a warning object.
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
    warning classes, and the corresponding expected connection info string.

    Returns a tuple of:
    * conn_id_kwarg: dict with the 'conn_id' keyword argument. May be empty.
    * exp_conn_str: Expected connection info string.
    """
    return request.param


def test_simple(simple_class, simple_args, conn_info):
    # pylint: disable=redefined-outer-name
    """
    Test the simple warning classes.

    Note, the Python `Warning` class is derived from the `Exception` class and
    thus can be treated like exception classes.
    """

    conn_id_kwarg, exp_conn_str = conn_info

    exc = simple_class(*simple_args, **conn_id_kwarg)

    # exc has no len()
    assert len(exc.args) == len(simple_args)
    for i, _ in enumerate(simple_args):
        # pylint: disable=unnecessary-list-index-lookup
        assert exc.args[i] == simple_args[i]
        assert exc.args[i:] == simple_args[i:]
        assert exc.args[0:i] == simple_args[0:i]
        assert exc.args[:] == simple_args[:]

    _assert_connection(exc, conn_id_kwarg, exp_conn_str)
    _assert_subscription(exc)
