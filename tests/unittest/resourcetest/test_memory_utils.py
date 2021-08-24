"""
Test for memory_utils module.
"""

from __future__ import absolute_import, print_function

import sys
import struct
from collections import deque
import pytest
import pywbem

from ..utils.pytest_extensions import simplified_test_function
from ...resourcetest import memory_utils
from ...resourcetest.memory_utils import total_sizeof

# pypy's implementation of sys.getsizeof() raises TypeError
try:
    sys.getsizeof(None)
except TypeError:
    ENABLE_TESTS = False
else:
    ENABLE_TESTS = True

if ENABLE_TESTS:

    class EmptyClass(object):
        # pylint: disable=too-few-public-methods
        "Empty class for determining size of its objects"
        pass

    def size_obj(obj):
        """
        Size of the input object, using the same size calculation function as
        used in memory_utils.total_sizeof().
        """
        return sys.getsizeof(obj)

    SIZE_REF = struct.calcsize('P')  # pylint: disable=no-member

    TESTCASES_TOTAL_SIZEOF = [

        # Testcases for total_sizeof()

        # Each list item is a testcase tuple with these items:
        # * desc: Short testcase description.
        # * kwargs: Keyword arguments for the test function:
        #   * obj: Input object for total_sizeof().
        #   * exp_size: Expected size, i.e. result of total_sizeof().
        # * exp_exc_types: Expected exception type(s), or None.
        # * exp_warn_types: Expected warning type(s), or None.
        # * condition: Boolean condition for testcase to run, or 'pdb' for
        #     debugger

        (
            "Test None",
            dict(
                obj=None,
                exp_size=size_obj(None),
            ),
            None, None, True
        ),
        (
            "Test int",
            dict(
                obj=2020,
                exp_size=size_obj(2020),
            ),
            None, None, True
        ),

        (
            "Test empty string",
            dict(
                obj='',
                exp_size=size_obj(''),
            ),
            None, None, True
        ),
        (
            "Test string with one char",
            dict(
                obj='C',
                exp_size=size_obj('C'),
            ),
            None, None, True
        ),
        (
            "Test string with two chars",
            dict(
                obj='CD',
                exp_size=size_obj('CD'),
            ),
            None, None, True
        ),
        (
            "Test unicode string with two chars",
            dict(
                obj=u'CD',
                exp_size=size_obj(u'CD'),
            ),
            None, None, True
        ),
        (
            "Test binary string with two chars",
            dict(
                obj=b'CD',
                exp_size=size_obj(b'CD'),
            ),
            None, None, True
        ),

        (
            "Test empty tuple",
            dict(
                obj=tuple(),
                exp_size=size_obj(tuple()),
            ),
            None, None, True
        ),
        (
            "Test tuple with one int item",
            dict(
                obj=(2000,),
                exp_size=size_obj((42,)) + size_obj(42),
            ),
            None, None, True
        ),
        (
            "Test tuple with two int items",
            dict(
                obj=(2000, 2001),
                exp_size=size_obj((42, 43)) + 2 * size_obj(42),
            ),
            None, None, True
        ),

        (
            "Test empty list",
            dict(
                obj=[],
                exp_size=size_obj([]),
            ),
            None, None, True
        ),
        (
            "Test list with one int item",
            dict(
                obj=[2000],
                exp_size=size_obj([42]) + size_obj(42),
            ),
            None, None, True
        ),
        (
            "Test list with two int items",
            dict(
                obj=[2000, 2001],
                exp_size=size_obj([42, 43]) + 2 * size_obj(42),
            ),
            None, None, True
        ),

        (
            "Test empty dict",
            dict(
                obj={},
                exp_size=size_obj({}),
            ),
            None, None, True
        ),
        (
            "Test dict with one int/int item",
            dict(
                obj={2000: 2001},
                exp_size=size_obj({42: 43}) + 2 * size_obj(42),
            ),
            None, None, True
        ),
        (
            "Test dict with two int/int items",
            dict(
                obj={2000: 2001, 2002: 2003},
                exp_size=size_obj({42: 43, 44: 45}) + 4 * size_obj(42),
            ),
            None, None, True
        ),

        (
            "Test empty set",
            dict(
                obj=set(),
                exp_size=size_obj(set()),
            ),
            None, None, True
        ),
        (
            "Test empty frozenset",
            dict(
                obj=frozenset(),
                exp_size=size_obj(frozenset()),
            ),
            None, None, True
        ),
        (
            "Test empty deque",
            dict(
                obj=deque(),
                exp_size=size_obj(deque()),
            ),
            None, None, True
        ),

        (
            "Test CIMQualifier object (slotted)",
            dict(
                obj=pywbem.CIMQualifier('Q1', type='string', value=None),
                exp_size=(
                    # Note: None is a shared object. total_sizeof() counts the
                    # first None object, and counts the remaining ones as
                    # references.
                    # Note: This is a slotted object, so there is no __dict__
                    # and the size of the slots are already contained in the
                    # size of the object.
                    size_obj(pywbem.CIMQualifier(
                        'Q1', type='string', value=None)) +
                    size_obj(u'Q1') +  # _name
                    size_obj(u'string') +  # _type
                    size_obj(None) +  # _value (first None object)
                    SIZE_REF +  # _propagated
                    SIZE_REF +  # _overridable
                    SIZE_REF +  # _tosubclass
                    SIZE_REF +  # _toinstance
                    SIZE_REF  # _translatable
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

        assert size == exp_size
