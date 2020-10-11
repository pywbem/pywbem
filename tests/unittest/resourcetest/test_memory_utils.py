"""
Test for memory_utils module.
"""

from __future__ import absolute_import, print_function

import sys
import struct
import collections
from collections import deque
import pytest
import pywbem

from ..utils.pytest_extensions import simplified_test_function
from ...resourcetest import memory_utils
from ...resourcetest.memory_utils import total_sizeof


class EmptyClass(object):
    # pylint: disable=too-few-public-methods
    "Empty class for determining size of its objects"
    pass


EC_OBJ = EmptyClass()

SIZE_NONE = sys.getsizeof(None)
SIZE_INT = sys.getsizeof(42)
SIZE_STR = sys.getsizeof('')
SIZE_TUPLE = sys.getsizeof(tuple())
SIZE_LIST = sys.getsizeof(list())
SIZE_DICT = sys.getsizeof(dict())
SIZE_SET = sys.getsizeof(set())
SIZE_FSET = sys.getsizeof(frozenset())
SIZE_DEQUE = sys.getsizeof(collections.deque())
SIZE_CLASS = sys.getsizeof(EC_OBJ)
SIZE_CLASS_DICT = sys.getsizeof(EC_OBJ.__dict__)
SIZE_REF = struct.calcsize('P')


TESTCASES_TOTAL_SIZEOF = [

    # Testcases for total_sizeof()

    # Each list item is a testcase tuple with these items:
    # * desc: Short testcase description.
    # * kwargs: Keyword arguments for the test function:
    #   * obj: Input object for total_sizeof().
    #   * exp_size: Expected size, i.e. result of total_sizeof().
    # * exp_exc_types: Expected exception type(s), or None.
    # * exp_warn_types: Expected warning type(s), or None.
    # * condition: Boolean condition for testcase to run, or 'pdb' for debugger

    (
        "Test None",
        dict(
            obj=None,
            exp_size=SIZE_NONE,
        ),
        None, None, True
    ),
    (
        "Test int",
        dict(
            obj=2020,
            exp_size=SIZE_INT,
        ),
        None, None, True
    ),

    (
        "Test empty string",
        dict(
            obj='',
            exp_size=SIZE_STR,
        ),
        None, None, 'debug'
    ),
    (
        "Test string with one char",
        dict(
            obj='C',
            exp_size=SIZE_STR + 1,
        ),
        None, None, True
    ),
    (
        "Test string with two chars",
        dict(
            obj='CD',
            exp_size=SIZE_STR + 2,
        ),
        None, None, True
    ),

    (
        "Test empty tuple",
        dict(
            obj=tuple(),
            exp_size=SIZE_TUPLE,
        ),
        None, None, True
    ),
    (
        "Test tuple with one int item",
        dict(
            obj=(2000,),
            exp_size=SIZE_TUPLE + 1 * (SIZE_REF + SIZE_INT),
        ),
        None, None, True
    ),
    (
        "Test tuple with two int items",
        dict(
            obj=(2000, 2001),
            exp_size=SIZE_TUPLE + 2 * (SIZE_REF + SIZE_INT),
        ),
        None, None, True
    ),

    (
        "Test empty list",
        dict(
            obj=list(),
            exp_size=SIZE_LIST,
        ),
        None, None, True
    ),
    (
        "Test list with one int item",
        dict(
            obj=[2000],
            exp_size=SIZE_LIST + 1 * (SIZE_REF + SIZE_INT),
        ),
        None, None, True
    ),
    (
        "Test list with two int items",
        dict(
            obj=[2000, 2001],
            exp_size=SIZE_LIST + 2 * (SIZE_REF + SIZE_INT),
        ),
        None, None, True
    ),

    (
        "Test empty dict",
        dict(
            obj=dict(),
            exp_size=SIZE_DICT,
        ),
        None, None, 'debug'
    ),
    (
        "Test dict with one int/int item",
        dict(
            obj={2000: 2001},
            exp_size=SIZE_DICT + 2 * SIZE_INT,
        ),
        None, None, True
    ),
    (
        "Test dict with two int/int items",
        dict(
            obj={2000: 2001, 2002: 2003},
            exp_size=SIZE_DICT + 4 * SIZE_INT,
        ),
        None, None, True
    ),

    (
        "Test empty set",
        dict(
            obj=set(),
            exp_size=SIZE_SET,
        ),
        None, None, True
    ),
    (
        "Test empty frozenset",
        dict(
            obj=frozenset(),
            exp_size=SIZE_FSET,
        ),
        None, None, True
    ),
    (
        "Test empty deque",
        dict(
            obj=deque(),
            exp_size=SIZE_DEQUE,
        ),
        None, None, True
    ),

    (
        "Test CIMQualifier with string type and value None",
        dict(
            obj=pywbem.CIMQualifier('Q1', type='string', value=None),
            exp_size=(
                SIZE_CLASS +        # CIMQualifier class
                SIZE_DICT - 88 +    # __dict__ for attrs; TODO: Clarify -88
                SIZE_STR + 5 + SIZE_STR + 2 +  # attr _name='Q1'
                SIZE_STR + 5 + SIZE_STR + 6 +  # attr _type='string'
                SIZE_STR + 6 + SIZE_NONE +     # attr _value=None
                SIZE_STR + 11 + SIZE_REF +     # attr _propagated=None
                SIZE_STR + 12 + SIZE_REF +     # attr _overridable=None
                SIZE_STR + 11 + SIZE_REF +     # attr _tosubclass=None
                SIZE_STR + 11 + SIZE_REF +     # attr _toinstance=None
                SIZE_STR + 13 + SIZE_REF       # attr _translatable=None
            ),
        ),
        None, None, 'debug'
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_TOTAL_SIZEOF)
@simplified_test_function
def test_total_sizeof(testcase, obj, exp_size):
    """
    Test function for total_sizeof().
    """

    if testcase.condition == 'debug':
        print("\nDebug: Testcase: {}".format(testcase.desc))
        memory_utils.DEBUG = True

    # The code to be tested
    size = total_sizeof(obj)

    if testcase.condition == 'debug':
        memory_utils.DEBUG = False

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None

    if testcase.condition == 'debug':
        print("Debug: Object size: actual={}, expected={}".
              format(size, exp_size))
    else:
        assert size == exp_size
