"""
Test the _nocasedict module.
"""

from __future__ import absolute_import

import pytest

from ..utils.pytest_extensions import simplified_test_function

# pylint: disable=wrong-import-position, wrong-import-order, invalid-name
from ...utils import import_installed
pywbem = import_installed('pywbem')
from pywbem._nocasedict import NocaseDict  # noqa: E402
# pylint: enable=wrong-import-position, wrong-import-order, invalid-name


TESTCASES_NOCASEDICT_UNNAMEDKEYS = [

    # Testcases for NocaseDict.__setitem__() and others

    # Each list item is a testcase tuple with these items:
    # * desc: Short testcase description.
    # * kwargs: Keyword arguments for the test function:
    #   * allow: Boolean controlling whether to allow unnamed keys.
    #   * key: Key to be used for the test.
    # * exp_exc_types: Expected exception type(s), or None.
    # * exp_warn_types: Expected warning type(s), or None.
    # * condition: Boolean condition for testcase to run, or 'pdb' for debugger

    (
        "Unnamed key with unnamed keys not allowed (error)",
        dict(
            allow=False,
            key=None,
        ),
        ValueError, None, True
    ),
    (
        "Unnamed key with unnamed keys allowed",
        dict(
            allow=True,
            key=None,
        ),
        None, None, True
    ),
    (
        "String key with unnamed keys not allowed",
        dict(
            allow=False,
            key='Dog',
        ),
        None, None, True
    ),
    (
        "String key with unnamed keys allowed",
        dict(
            allow=True,
            key='Dog',
        ),
        None, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_NOCASEDICT_UNNAMEDKEYS)
@simplified_test_function
def test_NocaseDict_unnamedkeys_getitem(testcase, allow, key):
    """
    Test function for NocaseDict.__getitem__() for unnamed keys
    """

    obj = NocaseDict()

    # This is not a very practical use, but necessary to test the function
    obj.allow_unnamed_keys = True
    obj[key] = 'foo'  # Uses __setitem__()
    obj.allow_unnamed_keys = allow

    # The code to be tested
    _ = obj[key]

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_NOCASEDICT_UNNAMEDKEYS)
@simplified_test_function
def test_NocaseDict_unnamedkeys_setitem(testcase, allow, key):
    """
    Test function for NocaseDict.__setitem__() for unnamed keys
    """

    obj = NocaseDict()
    obj.allow_unnamed_keys = allow

    # The code to be tested
    obj[key] = 'foo'

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None

    assert key in obj  # Uses __contains__()


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_NOCASEDICT_UNNAMEDKEYS)
@simplified_test_function
def test_NocaseDict_unnamedkeys_delitem(testcase, allow, key):
    """
    Test function for NocaseDict.__delitem__() for unnamed keys
    """

    obj = NocaseDict()

    # This is not a very practical use, but necessary to test the function
    obj.allow_unnamed_keys = True
    obj[key] = 'foo'  # Uses __setitem__()
    obj.allow_unnamed_keys = allow

    # The code to be tested
    del obj[key]

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None

    assert key not in obj  # Uses __contains__()


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_NOCASEDICT_UNNAMEDKEYS)
@simplified_test_function
def test_NocaseDict_unnamedkeys_contains(testcase, allow, key):
    """
    Test function for NocaseDict.__contains__() for unnamed keys
    """

    obj = NocaseDict()

    # This is not a very practical use, but necessary to test the function
    obj.allow_unnamed_keys = True
    obj[key] = 'foo'  # Uses __setitem__()
    obj.allow_unnamed_keys = allow

    # The code to be tested
    assert key in obj

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_NOCASEDICT_UNNAMEDKEYS)
@simplified_test_function
def test_NocaseDict_unnamedkeys_pop(testcase, allow, key):
    """
    Test function for NocaseDict.pop() for unnamed keys
    """

    obj = NocaseDict()

    # This is not a very practical use, but necessary to test the function
    obj.allow_unnamed_keys = True
    obj[key] = 'foo'  # Uses __setitem__()
    obj.allow_unnamed_keys = allow

    # The code to be tested
    _ = obj.pop(key)

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None

    assert key not in obj  # Uses __contains__()
