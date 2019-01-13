"""
Test the _nocasedict module.
"""

from __future__ import absolute_import

import sys
import re
import six
try:
    from collections import OrderedDict
except ImportError:
    from ordereddict import OrderedDict
import pytest

from pywbem._nocasedict import NocaseDict
from pywbem._utils import _format

from ..utils.pytest_extensions import simplified_test_function


class NonComparable(object):
    # pylint: disable=too-few-public-methods
    """
    Class that raises TypeError when comparing its objects for equality or
    when hashing its objects.
    """

    def __eq__(self, other):
        raise TypeError("Cannot compare %s to %s" % (type(self), type(other)))

    def __ne__(self, other):
        raise TypeError("Cannot compare %s to %s" % (type(self), type(other)))

    def __hash__(self):
        raise TypeError("Cannot hash %s" % type(self))


TESTCASES_NOCASEDICT_INIT = [

    # Testcases for NocaseDict.__init__() / ncd=NocaseDict()

    # Each list item is a testcase tuple with these items:
    # * desc: Short testcase description.
    # * kwargs: Keyword arguments for the test function:
    #   * init_args: Tuple of positional arguments to NocaseDict().
    #   * init_kwargs: Dict of keyword arguments to NocaseDict().
    #   * exp_dict: Expected resulting dictionary, as OrderedDict.
    # * exp_exc_types: Expected exception type(s), or None.
    # * exp_warn_types: Expected warning type(s), or None.
    # * condition: Boolean condition for testcase to run, or 'pdb' for debugger

    # Empty NocaseDict
    (
        "Empty dict from no args",
        dict(
            init_args=(),
            init_kwargs={},
            exp_dict=OrderedDict(),
            verify_order=True,
        ),
        None, None, True
    ),
    (
        "Empty dict from None as positional arg",
        dict(
            init_args=(None,),
            init_kwargs={},
            exp_dict=OrderedDict(),
            verify_order=True,
        ),
        None, None, True
    ),
    (
        "Empty dict from empty list as positional arg",
        dict(
            init_args=(list(),),
            init_kwargs={},
            exp_dict=OrderedDict(),
            verify_order=True,
        ),
        None, None, True
    ),
    (
        "Empty dict from empty tuple as positional arg",
        dict(
            init_args=(tuple(),),
            init_kwargs={},
            exp_dict=OrderedDict(),
            verify_order=True,
        ),
        None, None, True
    ),
    (
        "Empty dict from empty dict as positional arg",
        dict(
            init_args=(dict(),),
            init_kwargs={},
            exp_dict=OrderedDict(),
            verify_order=True,
        ),
        None, None, True
    ),
    (
        "Empty dict from empty NocaseDict as positional arg",
        dict(
            init_args=(NocaseDict(),),
            init_kwargs={},
            exp_dict=OrderedDict(),
            verify_order=True,
        ),
        None, None, True
    ),

    # Non-empty NocaseDict
    (
        "Dict from list as positional arg",
        dict(
            init_args=([('Dog', 'Cat'), ('Budgie', 'Fish')],),
            init_kwargs={},
            exp_dict=OrderedDict([('Dog', 'Cat'), ('Budgie', 'Fish')]),
            verify_order=True,
        ),
        None, None, True
    ),
    (
        "Dict from tuple as positional arg",
        dict(
            init_args=((('Dog', 'Cat'), ('Budgie', 'Fish')),),
            init_kwargs={},
            exp_dict=OrderedDict([('Dog', 'Cat'), ('Budgie', 'Fish')]),
            verify_order=True,
        ),
        None, None, True
    ),
    (
        "Dict from dict as positional arg",
        dict(
            init_args=({'Dog': 'Cat', 'Budgie': 'Fish'},),
            init_kwargs={},
            exp_dict=OrderedDict([('Dog', 'Cat'), ('Budgie', 'Fish')]),
            verify_order=False,
        ),
        None, UserWarning, True
    ),
    (
        "Dict from keyword args",
        dict(
            init_args=(),
            init_kwargs={'Dog': 'Cat', 'Budgie': 'Fish'},
            exp_dict=OrderedDict([('Dog', 'Cat'), ('Budgie', 'Fish')]),
            verify_order=False,
        ),
        None, UserWarning if sys.version_info[0:2] < (3, 7) else None, True
    ),
    (
        "Dict from list as positional arg and keyword args",
        dict(
            init_args=([('Dog', 'Cat')],),
            init_kwargs={'Budgie': 'Fish'},
            exp_dict=OrderedDict([('Dog', 'Cat'), ('Budgie', 'Fish')]),
            verify_order=True,
        ),
        None, None, True
    ),
    (
        "Dict from tuple as positional arg and keyword args",
        dict(
            init_args=((('Dog', 'Cat'),),),
            init_kwargs={'Budgie': 'Fish'},
            exp_dict=OrderedDict([('Dog', 'Cat'), ('Budgie', 'Fish')]),
            verify_order=True,
        ),
        None, None, True
    ),
    (
        "Dict from dict as positional arg and keyword args",
        dict(
            init_args=({'Dog': 'Cat'},),
            init_kwargs={'Budgie': 'Fish'},
            exp_dict=OrderedDict([('Dog', 'Cat'), ('Budgie', 'Fish')]),
            verify_order=True,
        ),
        None, None, True
    ),

    # Error cases
    (
        "String type as positional arg",
        dict(
            init_args=('illegal',),
            init_kwargs={},
            exp_dict=None,
            verify_order=None,
        ),
        TypeError, None, True
    ),
    (
        "Two positional args",
        dict(
            init_args=(list(), list()),
            init_kwargs={},
            exp_dict=None,
            verify_order=None,
        ),
        TypeError, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_NOCASEDICT_INIT)
@simplified_test_function
def test_NocaseDict_init(testcase,
                         init_args, init_kwargs, exp_dict, verify_order):
    """
    Test function for NocaseDict.__init__() / ncd=NocaseDict()
    """

    # The code to be tested
    act_dict = NocaseDict(*init_args, **init_kwargs)

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None

    # The verification below also uses some NocaseDict features, but that is
    # unavoidable if we want to work through the public interface:

    act_items = []
    for key in act_dict:  # Uses NocaseDict iteration
        act_value = act_dict[key]  # Uses NocaseDict getitem
        assert key in exp_dict, "Unexpected extra key %r" % key
        exp_value = exp_dict[key]
        assert act_value == exp_value, "Unexpected value at key %r" % key
        act_items.append((key, act_value))

    exp_items = []
    for key in exp_dict:
        exp_value = exp_dict[key]
        # Next line uses NocaseDict contains:
        assert key in act_dict, "Unexpected missing key %r" % key
        act_value = act_dict[key]  # Uses NocaseDict getitem
        assert act_value == exp_value, "Unexpected value at key %r" % key
        exp_items.append((key, exp_value))

    if verify_order:
        assert act_items == exp_items, "Unexpected order of items"


TESTCASES_NOCASEDICT_GETITEM = [

    # Testcases for NocaseDict.__getitem__() / ncd[key]

    # Each list item is a testcase tuple with these items:
    # * desc: Short testcase description.
    # * kwargs: Keyword arguments for the test function:
    #   * obj: NocaseDict object to be used for the test.
    #   * key: Key to be used for the test.
    #   * exp_value: Expected value for the key.
    # * exp_exc_types: Expected exception type(s), or None.
    # * exp_warn_types: Expected warning type(s), or None.
    # * condition: Boolean condition for testcase to run, or 'pdb' for debugger

    # Empty NocaseDict
    (
        "Empty dict, with None key (invalid type)",
        dict(
            obj=NocaseDict(),
            key=None,
            exp_value=None,
        ),
        TypeError, None, True
    ),
    (
        "Empty dict, with integer key (invalid type)",
        dict(
            obj=NocaseDict(),
            key=1234,
            exp_value=None,
        ),
        TypeError, None, True
    ),
    (
        "Empty dict, with empty string key (not found)",
        dict(
            obj=NocaseDict(),
            key='',
            exp_value=None,
        ),
        KeyError, None, True
    ),
    (
        "Empty dict, with non-empty key (not found)",
        dict(
            obj=NocaseDict(),
            key='Dog',
            exp_value=None,
        ),
        KeyError, None, True
    ),

    # Non-empty NocaseDict
    (
        "Non-empty dict, with None key (invalid type)",
        dict(
            obj=NocaseDict([('Dog', 'Cat'), ('Budgie', 'Fish')]),
            key=None,
            exp_value=None,
        ),
        TypeError, None, True
    ),
    (
        "Non-empty dict, with empty string key (not found)",
        dict(
            obj=NocaseDict([('Dog', 'Cat'), ('Budgie', 'Fish')]),
            key='',
            exp_value=None,
        ),
        KeyError, None, True
    ),
    (
        "Non-empty dict, with non-empty non-existing key (not found)",
        dict(
            obj=NocaseDict([('Dog', 'Cat'), ('Budgie', 'Fish')]),
            key='invalid',
            exp_value=None,
        ),
        KeyError, None, True
    ),
    (
        "Non-empty dict, with existing key in original case",
        dict(
            obj=NocaseDict([('Dog', 'Cat'), ('Budgie', 'Fish')]),
            key='Dog',
            exp_value='Cat',
        ),
        None, None, True
    ),
    (
        "Non-empty dict, with existing key in non-original upper case",
        dict(
            obj=NocaseDict([('Dog', 'Cat'), ('Budgie', 'Fish')]),
            key='DOG',
            exp_value='Cat',
        ),
        None, None, True
    ),
    (
        "Non-empty dict, with existing key in non-original lower case",
        dict(
            obj=NocaseDict([('Dog', 'Cat'), ('Budgie', 'Fish')]),
            key='dog',
            exp_value='Cat',
        ),
        None, None, True
    ),
    (
        "Non-empty dict, with existing key in non-original mixed case",
        dict(
            obj=NocaseDict([('Dog', 'Cat'), ('Budgie', 'Fish')]),
            key='doG',
            exp_value='Cat',
        ),
        None, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_NOCASEDICT_GETITEM)
@simplified_test_function
def test_NocaseDict_getitem(testcase,
                            obj, key, exp_value):
    """
    Test function for NocaseDict.__getitem__() / ncd[key]
    """

    # The code to be tested
    act_value = obj[key]

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None

    assert act_value == exp_value, "Unexpected value at key %r" % key


TESTCASES_NOCASEDICT_SETITEM = [

    # Testcases for NocaseDict.__setitem__() / ncd[key]=value

    # Each list item is a testcase tuple with these items:
    # * desc: Short testcase description.
    # * kwargs: Keyword arguments for the test function:
    #   * obj: NocaseDict object to be used for the test.
    #   * key: Key to be used for the test.
    #   * value: New value and expected value to be used for the test.
    # * exp_exc_types: Expected exception type(s), or None.
    # * exp_warn_types: Expected warning type(s), or None.
    # * condition: Boolean condition for testcase to run, or 'pdb' for debugger

    # Empty NocaseDict
    (
        "Empty dict, with None key (invalid type)",
        dict(
            obj=NocaseDict(),
            key=None,
            value=None,
        ),
        TypeError, None, True
    ),
    (
        "Empty dict, with integer key (invalid type)",
        dict(
            obj=NocaseDict(),
            key=1234,
            value=None,
        ),
        TypeError, None, True
    ),
    (
        "Empty dict, with empty string key",
        dict(
            obj=NocaseDict(),
            key='',
            value='Newbie',
        ),
        None, None, True
    ),
    (
        "Empty dict, with non-empty key",
        dict(
            obj=NocaseDict(),
            key='Dog',
            value='Kitten',
        ),
        None, None, True
    ),

    # Non-empty NocaseDict
    (
        "Non-empty dict, with None key (invalid type)",
        dict(
            obj=NocaseDict([('Dog', 'Cat'), ('Budgie', 'Fish')]),
            key=None,
            value='Kitten',
        ),
        TypeError, None, True
    ),
    (
        "Non-empty dict, with empty string key",
        dict(
            obj=NocaseDict([('Dog', 'Cat'), ('Budgie', 'Fish')]),
            key='',
            value='Newbie',
        ),
        None, None, True
    ),
    (
        "Non-empty dict, with non-empty non-existing key",
        dict(
            obj=NocaseDict([('Dog', 'Cat'), ('Budgie', 'Fish')]),
            key='newkey',
            value='Newbie',
        ),
        None, None, True
    ),
    (
        "Non-empty dict, with existing key in original case",
        dict(
            obj=NocaseDict([('Dog', 'Cat'), ('Budgie', 'Fish')]),
            key='Dog',
            value='Kitten',
        ),
        None, None, True
    ),
    (
        "Non-empty dict, with existing key in non-original upper case",
        dict(
            obj=NocaseDict([('Dog', 'Cat'), ('Budgie', 'Fish')]),
            key='DOG',
            value='Kitten',
        ),
        None, None, True
    ),
    (
        "Non-empty dict, with existing key in non-original lower case",
        dict(
            obj=NocaseDict([('Dog', 'Cat'), ('Budgie', 'Fish')]),
            key='dog',
            value='Kitten',
        ),
        None, None, True
    ),
    (
        "Non-empty dict, with existing key in non-original mixed case",
        dict(
            obj=NocaseDict([('Dog', 'Cat'), ('Budgie', 'Fish')]),
            key='doG',
            value='Kitten',
        ),
        None, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_NOCASEDICT_SETITEM)
@simplified_test_function
def test_NocaseDict_setitem(testcase, obj, key, value):
    """
    Test function for NocaseDict.__setitem__() / ncd[key]=value
    """

    # The code to be tested
    obj[key] = value

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None

    # The verification below also uses some NocaseDict features, but that is
    # unavoidable if we want to work through the public interface:

    act_value = obj[key]  # Uses NocaseDIct getitem

    assert act_value == value, "Unexpected value at key %r" % key


TESTCASES_NOCASEDICT_DELITEM = [

    # Testcases for NocaseDict.__delitem__() / del ncd[key]

    # Each list item is a testcase tuple with these items:
    # * desc: Short testcase description.
    # * kwargs: Keyword arguments for the test function:
    #   * obj: NocaseDict object to be used for the test.
    #   * key: Key to be used for the test.
    # * exp_exc_types: Expected exception type(s), or None.
    # * exp_warn_types: Expected warning type(s), or None.
    # * condition: Boolean condition for testcase to run, or 'pdb' for debugger

    # Empty NocaseDict
    (
        "Empty dict, with None key (invalid type)",
        dict(
            obj=NocaseDict(),
            key=None,
        ),
        TypeError, None, True
    ),
    (
        "Empty dict, with integer key (invalid type)",
        dict(
            obj=NocaseDict(),
            key=1234,
        ),
        TypeError, None, True
    ),
    (
        "Empty dict, with empty string key (not found)",
        dict(
            obj=NocaseDict(),
            key='',
        ),
        KeyError, None, True
    ),
    (
        "Empty dict, with non-empty key (not found)",
        dict(
            obj=NocaseDict(),
            key='Dog',
        ),
        KeyError, None, True
    ),

    # Non-empty NocaseDict
    (
        "Non-empty dict, with None key (invalid type)",
        dict(
            obj=NocaseDict([('Dog', 'Cat'), ('Budgie', 'Fish')]),
            key=None,
        ),
        TypeError, None, True
    ),
    (
        "Non-empty dict, with empty non-existing string key (not found)",
        dict(
            obj=NocaseDict([('Dog', 'Cat'), ('Budgie', 'Fish')]),
            key='',
        ),
        KeyError, None, True
    ),
    (
        "Non-empty dict, with non-empty non-existing key (not found)",
        dict(
            obj=NocaseDict([('Dog', 'Cat'), ('Budgie', 'Fish')]),
            key='invalid',
        ),
        KeyError, None, True
    ),
    (
        "Non-empty dict, with existing key in original case",
        dict(
            obj=NocaseDict([('Dog', 'Cat'), ('Budgie', 'Fish')]),
            key='Dog',
        ),
        None, None, True
    ),
    (
        "Non-empty dict, with existing key in non-original upper case",
        dict(
            obj=NocaseDict([('Dog', 'Cat'), ('Budgie', 'Fish')]),
            key='DOG',
        ),
        None, None, True
    ),
    (
        "Non-empty dict, with existing key in non-original lower case",
        dict(
            obj=NocaseDict([('Dog', 'Cat'), ('Budgie', 'Fish')]),
            key='dog',
        ),
        None, None, True
    ),
    (
        "Non-empty dict, with existing key in non-original mixed case",
        dict(
            obj=NocaseDict([('Dog', 'Cat'), ('Budgie', 'Fish')]),
            key='doG',
        ),
        None, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_NOCASEDICT_DELITEM)
@simplified_test_function
def test_NocaseDict_delitem(testcase, obj, key):
    """
    Test function for NocaseDict.__delitem__() / del ncd[key]
    """

    # The code to be tested
    del obj[key]

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None

    # The verification below also uses some NocaseDict features, but that is
    # unavoidable if we want to work through the public interface:

    with pytest.raises(KeyError):
        # The following line uses NocaseDict getitem
        obj[key]  # pylint: disable=pointless-statement


TESTCASES_NOCASEDICT_LEN = [

    # Testcases for NocaseDict.__len__() / len(ncd)

    # Each list item is a testcase tuple with these items:
    # * desc: Short testcase description.
    # * kwargs: Keyword arguments for the test function:
    #   * obj: NocaseDict object to be used for the test.
    #   * exp_len: Expected len() value.
    # * exp_exc_types: Expected exception type(s), or None.
    # * exp_warn_types: Expected warning type(s), or None.
    # * condition: Boolean condition for testcase to run, or 'pdb' for debugger

    (
        "Empty dict",
        dict(
            obj=NocaseDict(),
            exp_len=0,
        ),
        None, None, True
    ),
    (
        "Dict with two items",
        dict(
            obj=NocaseDict([('Dog', 'Cat'), ('Budgie', 'Fish')]),
            exp_len=2,
        ),
        None, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_NOCASEDICT_LEN)
@simplified_test_function
def test_NocaseDict_len(testcase, obj, exp_len):
    """
    Test function for NocaseDict.__len__() / len(ncd)
    """

    # The code to be tested
    act_len = len(obj)

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None

    assert act_len == exp_len


TESTCASES_NOCASEDICT_CONTAINS = [

    # Testcases for NocaseDict.__contains__() / key in ncd

    # Each list item is a testcase tuple with these items:
    # * desc: Short testcase description.
    # * kwargs: Keyword arguments for the test function:
    #   * obj: NocaseDict object to be used for the test.
    #   * key: Key to be used for the test.
    #   * exp_result: Expected result (bool).
    # * exp_exc_types: Expected exception type(s), or None.
    # * exp_warn_types: Expected warning type(s), or None.
    # * condition: Boolean condition for testcase to run, or 'pdb' for debugger

    # Empty NocaseDict
    (
        "Empty dict, with None key (invalid type)",
        dict(
            obj=NocaseDict(),
            key=None,
            exp_result=None,
        ),
        TypeError, None, True
    ),
    (
        "Empty dict, with integer key (invalid type)",
        dict(
            obj=NocaseDict(),
            key=1234,
            exp_result=None,
        ),
        TypeError, None, True
    ),
    (
        "Empty dict, with empty string key (not found)",
        dict(
            obj=NocaseDict(),
            key='',
            exp_result=False,
        ),
        None, None, True
    ),
    (
        "Empty dict, with non-empty key (not found)",
        dict(
            obj=NocaseDict(),
            key='Dog',
            exp_result=False,
        ),
        None, None, True
    ),

    # Non-empty NocaseDict
    (
        "Non-empty dict, with None key (invalid type)",
        dict(
            obj=NocaseDict([('Dog', 'Cat'), ('Budgie', 'Fish')]),
            key=None,
            exp_result=None,
        ),
        TypeError, None, True
    ),
    (
        "Non-empty dict, with empty non-existing string key (not found)",
        dict(
            obj=NocaseDict([('Dog', 'Cat'), ('Budgie', 'Fish')]),
            key='',
            exp_result=False,
        ),
        None, None, True
    ),
    (
        "Non-empty dict, with non-empty non-existing key (not found)",
        dict(
            obj=NocaseDict([('Dog', 'Cat'), ('Budgie', 'Fish')]),
            key='invalid',
            exp_result=False,
        ),
        None, None, True
    ),
    (
        "Non-empty dict, with existing key in original case",
        dict(
            obj=NocaseDict([('Dog', 'Cat'), ('Budgie', 'Fish')]),
            key='Dog',
            exp_result=True,
        ),
        None, None, True
    ),
    (
        "Non-empty dict, with existing key in non-original upper case",
        dict(
            obj=NocaseDict([('Dog', 'Cat'), ('Budgie', 'Fish')]),
            key='DOG',
            exp_result=True,
        ),
        None, None, True
    ),
    (
        "Non-empty dict, with existing key in non-original lower case",
        dict(
            obj=NocaseDict([('Dog', 'Cat'), ('Budgie', 'Fish')]),
            key='dog',
            exp_result=True,
        ),
        None, None, True
    ),
    (
        "Non-empty dict, with existing key in non-original mixed case",
        dict(
            obj=NocaseDict([('Dog', 'Cat'), ('Budgie', 'Fish')]),
            key='doG',
            exp_result=True,
        ),
        None, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_NOCASEDICT_CONTAINS)
@simplified_test_function
def test_NocaseDict_contains(testcase, obj, key, exp_result):
    """
    Test function for NocaseDict.__contains__() / key in ncd
    """

    # The code to be tested
    act_result = key in obj

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None

    assert act_result == exp_result, "Unexpected result at key %r" % key


TESTCASES_NOCASEDICT_GET = [

    # Testcases for NocaseDict.get()

    # Each list item is a testcase tuple with these items:
    # * desc: Short testcase description.
    # * kwargs: Keyword arguments for the test function:
    #   * obj: NocaseDict object to be used for the test.
    #   * key: Key to be used for the test.
    #   * default: Default value to be used for the test, or None to not pass.
    #   * exp_value: Expected value at the key.
    # * exp_exc_types: Expected exception type(s), or None.
    # * exp_warn_types: Expected warning type(s), or None.
    # * condition: Boolean condition for testcase to run, or 'pdb' for debugger

    # Empty NocaseDict
    (
        "Empty dict, with None key (invalid type)",
        dict(
            obj=NocaseDict(),
            key=None,
            default=None,
            exp_value=None,
        ),
        TypeError, None, True
    ),
    (
        "Empty dict, with integer key (invalid type)",
        dict(
            obj=NocaseDict(),
            key=1234,
            default=None,
            exp_value=None,
        ),
        TypeError, None, True
    ),
    (
        "Empty dict, with empty string key (defaulted without default)",
        dict(
            obj=NocaseDict(),
            key='',
            default=None,
            exp_value=None,
        ),
        None, None, True
    ),
    (
        "Empty dict, with empty string key (defaulted to a value)",
        dict(
            obj=NocaseDict(),
            key='',
            default='Newbie',
            exp_value='Newbie',
        ),
        None, None, True
    ),
    (
        "Empty dict, with non-empty key (defaulted without default)",
        dict(
            obj=NocaseDict(),
            key='Dog',
            default=None,
            exp_value=None,
        ),
        None, None, True
    ),
    (
        "Empty dict, with non-empty key (defaulted to a value)",
        dict(
            obj=NocaseDict(),
            key='Dog',
            default='Kitten',
            exp_value='Kitten',
        ),
        None, None, True
    ),

    # Non-empty NocaseDict
    (
        "Non-empty dict, with None key (invalid type)",
        dict(
            obj=NocaseDict([('Dog', 'Cat'), ('Budgie', 'Fish')]),
            key=None,
            default=None,
            exp_value=None,
        ),
        TypeError, None, True
    ),
    (
        "Non-empty dict, with empty string key (defaulted without default)",
        dict(
            obj=NocaseDict([('Dog', 'Cat'), ('Budgie', 'Fish')]),
            key='',
            default=None,
            exp_value=None,
        ),
        None, None, True
    ),
    (
        "Non-empty dict, with empty string key (defaulted to a value)",
        dict(
            obj=NocaseDict([('Dog', 'Cat'), ('Budgie', 'Fish')]),
            key='',
            default='Newbie',
            exp_value='Newbie',
        ),
        None, None, True
    ),
    (
        "Non-empty dict, with non-empty non-existing key (defaulted without "
        "default)",
        dict(
            obj=NocaseDict([('Dog', 'Cat'), ('Budgie', 'Fish')]),
            key='invalid',
            default=None,
            exp_value=None,
        ),
        None, None, True
    ),
    (
        "Non-empty dict, with non-empty non-existing key (defaulted to a "
        "value)",
        dict(
            obj=NocaseDict([('Dog', 'Cat'), ('Budgie', 'Fish')]),
            key='invalid',
            default='Newbie',
            exp_value='Newbie',
        ),
        None, None, True
    ),
    (
        "Non-empty dict, with existing key in original case (no default)",
        dict(
            obj=NocaseDict([('Dog', 'Cat'), ('Budgie', 'Fish')]),
            key='Dog',
            default=None,
            exp_value='Cat',
        ),
        None, None, True
    ),
    (
        "Non-empty dict, with existing key in original case (with default)",
        dict(
            obj=NocaseDict([('Dog', 'Cat'), ('Budgie', 'Fish')]),
            key='Dog',
            default='Newbie',
            exp_value='Cat',
        ),
        None, None, True
    ),
    (
        "Non-empty dict, with existing key in mixed case (no default)",
        dict(
            obj=NocaseDict([('Dog', 'Cat'), ('Budgie', 'Fish')]),
            key='doG',
            default=None,
            exp_value='Cat',
        ),
        None, None, True
    ),
    (
        "Non-empty dict, with existing key in mixed case (with default)",
        dict(
            obj=NocaseDict([('Dog', 'Cat'), ('Budgie', 'Fish')]),
            key='doG',
            default='Newbie',
            exp_value='Cat',
        ),
        None, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_NOCASEDICT_GET)
@simplified_test_function
def test_NocaseDict_get(testcase, obj, key, default, exp_value):
    """
    Test function for NocaseDict.get()
    """

    # The code to be tested
    if default is None:
        act_value = obj.get(key)
    else:
        act_value = obj.get(key, default)

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None

    assert act_value == exp_value, "Unexpected value at key %r with " \
                                   "default %r" % (key, default)


TESTCASES_NOCASEDICT_SETDEFAULT = [

    # Testcases for NocaseDict.setdefault()

    # Each list item is a testcase tuple with these items:
    # * desc: Short testcase description.
    # * kwargs: Keyword arguments for the test function:
    #   * obj: NocaseDict object to be used for the test.
    #   * key: Key to be used for the test.
    #   * default: Default value to be used for the test (None is passed).
    #   * exp_value: Expected value at the key.
    # * exp_exc_types: Expected exception type(s), or None.
    # * exp_warn_types: Expected warning type(s), or None.
    # * condition: Boolean condition for testcase to run, or 'pdb' for debugger

    # Empty NocaseDict
    (
        "Empty dict, with None key (invalid type)",
        dict(
            obj=NocaseDict(),
            key=None,
            default=None,
            exp_value=None,
        ),
        TypeError, None, True
    ),
    (
        "Empty dict, with integer key (invalid type)",
        dict(
            obj=NocaseDict(),
            key=1234,
            default=None,
            exp_value=None,
        ),
        TypeError, None, True
    ),
    (
        "Empty dict, with empty string key (defaulted without default)",
        dict(
            obj=NocaseDict(),
            key='',
            default=None,
            exp_value=None,
        ),
        None, None, True
    ),
    (
        "Empty dict, with empty string key (defaulted to a value)",
        dict(
            obj=NocaseDict(),
            key='',
            default='Newbie',
            exp_value='Newbie',
        ),
        None, None, True
    ),
    (
        "Empty dict, with non-empty key (defaulted without default)",
        dict(
            obj=NocaseDict(),
            key='Dog',
            default=None,
            exp_value=None,
        ),
        None, None, True
    ),
    (
        "Empty dict, with non-empty key (defaulted to a value)",
        dict(
            obj=NocaseDict(),
            key='Dog',
            default='Kitten',
            exp_value='Kitten',
        ),
        None, None, True
    ),

    # Non-empty NocaseDict
    (
        "Non-empty dict, with None key (invalid type)",
        dict(
            obj=NocaseDict([('Dog', 'Cat'), ('Budgie', 'Fish')]),
            key=None,
            default=None,
            exp_value=None,
        ),
        TypeError, None, True
    ),
    (
        "Non-empty dict, with empty string key (defaulted without default)",
        dict(
            obj=NocaseDict([('Dog', 'Cat'), ('Budgie', 'Fish')]),
            key='',
            default=None,
            exp_value=None,
        ),
        None, None, True
    ),
    (
        "Non-empty dict, with empty string key (defaulted to a value)",
        dict(
            obj=NocaseDict([('Dog', 'Cat'), ('Budgie', 'Fish')]),
            key='',
            default='Newbie',
            exp_value='Newbie',
        ),
        None, None, True
    ),
    (
        "Non-empty dict, with non-empty non-existing key (defaulted without "
        "default)",
        dict(
            obj=NocaseDict([('Dog', 'Cat'), ('Budgie', 'Fish')]),
            key='invalid',
            default=None,
            exp_value=None,
        ),
        None, None, True
    ),
    (
        "Non-empty dict, with non-empty non-existing key (defaulted to a "
        "value)",
        dict(
            obj=NocaseDict([('Dog', 'Cat'), ('Budgie', 'Fish')]),
            key='invalid',
            default='Newbie',
            exp_value='Newbie',
        ),
        None, None, True
    ),
    (
        "Non-empty dict, with existing key in original case (no default)",
        dict(
            obj=NocaseDict([('Dog', 'Cat'), ('Budgie', 'Fish')]),
            key='Dog',
            default=None,
            exp_value='Cat',
        ),
        None, None, True
    ),
    (
        "Non-empty dict, with existing key in original case (with default)",
        dict(
            obj=NocaseDict([('Dog', 'Cat'), ('Budgie', 'Fish')]),
            key='Dog',
            default='Newbie',
            exp_value='Cat',
        ),
        None, None, True
    ),
    (
        "Non-empty dict, with existing key in mixed case (no default)",
        dict(
            obj=NocaseDict([('Dog', 'Cat'), ('Budgie', 'Fish')]),
            key='doG',
            default=None,
            exp_value='Cat',
        ),
        None, None, True
    ),
    (
        "Non-empty dict, with existing key in mixed case (with default)",
        dict(
            obj=NocaseDict([('Dog', 'Cat'), ('Budgie', 'Fish')]),
            key='doG',
            default='Newbie',
            exp_value='Cat',
        ),
        None, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_NOCASEDICT_SETDEFAULT)
@simplified_test_function
def test_NocaseDict_setdefault(testcase, obj, key, default, exp_value):
    """
    Test function for NocaseDict.setdefault()
    """

    # The code to be tested
    act_value = obj.setdefault(key, default)

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None

    assert act_value == exp_value, "Unexpected value at key %r with " \
                                   "default %r" % (key, default)


TESTCASES_NOCASEDICT_ITEMS = [

    # Testcases for NocaseDict.keys(), values(), items()

    # Each list item is a testcase tuple with these items:
    # * desc: Short testcase description.
    # * kwargs: Keyword arguments for the test function:
    #   * obj: NocaseDict object to be used for the test.
    #   * exp_items: List with expected items (key,value) in expected order.
    # * exp_exc_types: Expected exception type(s), or None.
    # * exp_warn_types: Expected warning type(s), or None.
    # * condition: Boolean condition for testcase to run, or 'pdb' for debugger

    (
        "Empty dict",
        dict(
            obj=NocaseDict(),
            exp_items=[],
        ),
        None, None, True
    ),
    (
        "Dict with two items",
        dict(
            obj=NocaseDict([('Dog', 'Cat'), ('Budgie', 'Fish')]),
            exp_items=[('Dog', 'Cat'), ('Budgie', 'Fish')],
        ),
        None, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_NOCASEDICT_ITEMS)
@simplified_test_function
def test_NocaseDict_keys(testcase, obj, exp_items):
    """
    Test function for NocaseDict.keys()
    """

    # The code to be tested
    act_keys = obj.keys()

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None

    exp_keys = [item[0] for item in exp_items]
    assert act_keys == exp_keys


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_NOCASEDICT_ITEMS)
@simplified_test_function
def test_NocaseDict_values(testcase, obj, exp_items):
    """
    Test function for NocaseDict.values()
    """

    # The code to be tested
    act_values = obj.values()

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None

    exp_values = [item[1] for item in exp_items]
    assert act_values == exp_values


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_NOCASEDICT_ITEMS)
@simplified_test_function
def test_NocaseDict_items(testcase, obj, exp_items):
    """
    Test function for NocaseDict.items()
    """

    # The code to be tested
    act_items = obj.items()

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None

    assert act_items == exp_items


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_NOCASEDICT_ITEMS)
@simplified_test_function
def test_NocaseDict_iterkeys(testcase, obj, exp_items):
    """
    Test function for NocaseDict.iterkeys()
    """

    # The code to be tested
    act_keys = []
    for key in obj.iterkeys():
        act_keys.append(key)

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None

    exp_keys = [item[0] for item in exp_items]
    assert act_keys == exp_keys


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_NOCASEDICT_ITEMS)
@simplified_test_function
def test_NocaseDict_itervalues(testcase, obj, exp_items):
    """
    Test function for NocaseDict.itervalues()
    """

    # The code to be tested
    act_values = []
    for value in obj.itervalues():
        act_values.append(value)

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None

    exp_values = [item[1] for item in exp_items]
    assert act_values == exp_values


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_NOCASEDICT_ITEMS)
@simplified_test_function
def test_NocaseDict_iteritems(testcase, obj, exp_items):
    """
    Test function for NocaseDict.iteritemss()
    """

    # The code to be tested
    act_items = []
    for item in obj.iteritems():
        act_items.append(item)

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None

    assert act_items == exp_items


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_NOCASEDICT_ITEMS)
@simplified_test_function
def test_NocaseDict_iter(testcase, obj, exp_items):
    """
    Test function for NocaseDict.__iter__() / for key in ncd
    """

    # The code to be tested
    act_items = []
    for key in obj:
        value = obj[key]
        act_items.append((key, value))

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None

    assert act_items == exp_items


TESTCASES_NOCASEDICT_REPR = [

    # Testcases for NocaseDict.__repr__() / repr(ncd)

    # Each list item is a testcase tuple with these items:
    # * desc: Short testcase description.
    # * kwargs: Keyword arguments for the test function:
    #   * obj: NocaseDict object to be used for the test.
    # * exp_exc_types: Expected exception type(s), or None.
    # * exp_warn_types: Expected warning type(s), or None.
    # * condition: Boolean condition for testcase to run, or 'pdb' for debugger

    (
        "Empty dict",
        dict(
            obj=NocaseDict(),
        ),
        None, None, True
    ),
    (
        "Dict with two items",
        dict(
            obj=NocaseDict([('Dog', 'Cat'), ('Budgie', 'Fish')]),
        ),
        None, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_NOCASEDICT_REPR)
@simplified_test_function
def test_NocaseDict_repr(testcase, obj):
    """
    Test function for NocaseDict.__repr__() / repr(ncd)
    """

    # The code to be tested
    result = repr(obj)

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None

    assert re.match(r'^NocaseDict\(.*\)$', result)

    # Note: This only tests for existence of each item, not for excess items
    # or representing the correct order.
    for item in obj.items():
        exp_item_result = _format("{0!A}: {1!A}", *item)
        assert exp_item_result in result


TESTCASES_NOCASEDICT_UPDATE = [

    # Testcases for NocaseDict.update()

    # Each list item is a testcase tuple with these items:
    # * desc: Short testcase description.
    # * kwargs: Keyword arguments for the test function:
    #   * obj: NocaseDict object to be used for the test.
    #   * args: List of positional args for update().
    #   * kwargs: Dict of keyword args for update().
    #   * exp_obj: Expected NocaseDict after being updated.
    # * exp_exc_types: Expected exception type(s), or None.
    # * exp_warn_types: Expected warning type(s), or None.
    # * condition: Boolean condition for testcase to run, or 'pdb' for debugger

    # Empty NocaseDict
    (
        "Empty dict, with empty update args + kwargs",
        dict(
            obj=NocaseDict(),
            args=[],
            kwargs={},
            exp_obj=NocaseDict(),
        ),
        None, None, True
    ),
    (
        "Empty dict, with integer key in update args (invalid type)",
        dict(
            obj=NocaseDict(),
            args=[[(1234, 'Invalid')]],
            kwargs={},
            exp_obj=None,
        ),
        TypeError, None, True
    ),
    (
        "Empty dict, with integer key in update kwargs (invalid type)",
        dict(
            obj=NocaseDict(),
            args=[],
            kwargs={1234: 'Invalid'},
            exp_obj=None,
        ),
        TypeError, None, True
    ),
    (
        "Empty dict, with empty string key in update args+items",
        dict(
            obj=NocaseDict(),
            args=[OrderedDict([('', 'Cat')])],
            kwargs={},
            exp_obj=NocaseDict([('', 'Cat')]),
        ),
        None, None, True
    ),
    (
        "Empty dict, with empty string key in update args+iter",
        dict(
            obj=NocaseDict(),
            args=[[('', 'Cat')]],
            kwargs={},
            exp_obj=NocaseDict([('', 'Cat')]),
        ),
        None, None, True
    ),
    (
        "Empty dict, with empty string key in update kwargs",
        dict(
            obj=NocaseDict(),
            args=[],
            kwargs={'': 'Cat'},
            exp_obj=NocaseDict([('', 'Cat')]),
        ),
        None, None, True
    ),
    (
        "Empty dict, with non-empty string key in update args+items",
        dict(
            obj=NocaseDict(),
            args=[OrderedDict([('Dog', 'Cat')])],
            kwargs={},
            exp_obj=NocaseDict([('Dog', 'Cat')]),
        ),
        None, None, True
    ),
    (
        "Empty dict, with non-empty string key in update args+iter",
        dict(
            obj=NocaseDict(),
            args=[[('Dog', 'Cat')]],
            kwargs={},
            exp_obj=NocaseDict([('Dog', 'Cat')]),
        ),
        None, None, True
    ),
    (
        "Empty dict, with non-empty string key in update kwargs",
        dict(
            obj=NocaseDict(),
            args=[],
            kwargs={'Dog': 'Cat'},
            exp_obj=NocaseDict([('Dog', 'Cat')]),
        ),
        None, None, True
    ),

    # Non-empty NocaseDict, insert new value
    (
        "Non-empty dict, with integer key in update args (invalid type)",
        dict(
            obj=NocaseDict([('Dog', 'Cat'), ('Budgie', 'Fish')]),
            args=[[(1234, 'Invalud')]],
            kwargs={},
            exp_obj=None,
        ),
        TypeError, None, True
    ),
    (
        "Non-empty dict, with integer key in update kwargs (invalid type)",
        dict(
            obj=NocaseDict([('Dog', 'Cat'), ('Budgie', 'Fish')]),
            args=[],
            kwargs={1234: 'Invalid'},
            exp_obj=None,
        ),
        TypeError, None, True
    ),
    (
        "Non-empty dict, with new empty string key in update args+items",
        dict(
            obj=NocaseDict([('Dog', 'Cat'), ('Budgie', 'Fish')]),
            args=[OrderedDict([('', 'Newbie')])],
            kwargs={},
            exp_obj=NocaseDict([('Dog', 'Cat'), ('Budgie', 'Fish'),
                                ('', 'Newbie')]),
        ),
        None, None, True
    ),
    (
        "Non-empty dict, with new empty string key in update args+iter",
        dict(
            obj=NocaseDict([('Dog', 'Cat'), ('Budgie', 'Fish')]),
            args=[[('', 'Newbie')]],
            kwargs={},
            exp_obj=NocaseDict([('Dog', 'Cat'), ('Budgie', 'Fish'),
                                ('', 'Newbie')]),
        ),
        None, None, True
    ),
    (
        "Non-empty dict, with new empty string key in update kwargs",
        dict(
            obj=NocaseDict([('Dog', 'Cat'), ('Budgie', 'Fish')]),
            args=[],
            kwargs={'': 'Newbie'},
            exp_obj=NocaseDict([('Dog', 'Cat'), ('Budgie', 'Fish'),
                                ('', 'Newbie')]),
        ),
        None, None, True
    ),
    (
        "Non-empty dict, with new non-empty string key in update args+items",
        dict(
            obj=NocaseDict([('Dog', 'Cat'), ('Budgie', 'Fish')]),
            args=[OrderedDict([('New', 'Newbie')])],
            kwargs={},
            exp_obj=NocaseDict([('Dog', 'Cat'), ('Budgie', 'Fish'),
                                ('New', 'Newbie')]),
        ),
        None, None, True
    ),
    (
        "Non-empty dict, with new non-empty string key in update args+iter",
        dict(
            obj=NocaseDict([('Dog', 'Cat'), ('Budgie', 'Fish')]),
            args=[[('New', 'Newbie')]],
            kwargs={},
            exp_obj=NocaseDict([('Dog', 'Cat'), ('Budgie', 'Fish'),
                                ('New', 'Newbie')]),
        ),
        None, None, True
    ),
    (
        "Non-empty dict, with new non-empty string key in update kwargs",
        dict(
            obj=NocaseDict([('Dog', 'Cat'), ('Budgie', 'Fish')]),
            args=[],
            kwargs={'New': 'Newbie'},
            exp_obj=NocaseDict([('Dog', 'Cat'), ('Budgie', 'Fish'),
                                ('New', 'Newbie')]),
        ),
        None, None, True
    ),

    # Non-empty NocaseDict, update value of existing key
    (
        "Non-empty dict, updating at existing key in org. case via args+items",
        dict(
            obj=NocaseDict([('Dog', 'Cat'), ('Budgie', 'Fish')]),
            args=[OrderedDict([('Dog', 'Kitten')])],
            kwargs={},
            exp_obj=NocaseDict([('Dog', 'Kitten'), ('Budgie', 'Fish')]),
        ),
        None, None, True
    ),
    (
        "Non-empty dict, updating at existing key in org. case via args+iter",
        dict(
            obj=NocaseDict([('Dog', 'Cat'), ('Budgie', 'Fish')]),
            args=[[('Dog', 'Kitten')]],
            kwargs={},
            exp_obj=NocaseDict([('Dog', 'Kitten'), ('Budgie', 'Fish')]),
        ),
        None, None, True
    ),
    (
        "Non-empty dict, updating at existing key in org. case via kwargs",
        dict(
            obj=NocaseDict([('Dog', 'Cat'), ('Budgie', 'Fish')]),
            args=[],
            kwargs={'Dog': 'Kitten'},
            exp_obj=NocaseDict([('Dog', 'Kitten'), ('Budgie', 'Fish')]),
        ),
        None, None, True
    ),
    (
        "Non-empty dict, updating at existing key in mixed case via args+items",
        dict(
            obj=NocaseDict([('Dog', 'Cat'), ('Budgie', 'Fish')]),
            args=[OrderedDict([('doG', 'Kitten')])],
            kwargs={},
            exp_obj=NocaseDict([('Dog', 'Kitten'), ('Budgie', 'Fish')]),
        ),
        None, None, True
    ),
    (
        "Non-empty dict, updating at existing key in mixed case via args+iter",
        dict(
            obj=NocaseDict([('Dog', 'Cat'), ('Budgie', 'Fish')]),
            args=[[('doG', 'Kitten')]],
            kwargs={},
            exp_obj=NocaseDict([('Dog', 'Kitten'), ('Budgie', 'Fish')]),
        ),
        None, None, True
    ),
    (
        "Non-empty dict, updating at existing key in mixed case via kwargs",
        dict(
            obj=NocaseDict([('Dog', 'Cat'), ('Budgie', 'Fish')]),
            args=[],
            kwargs={'doG': 'Kitten'},
            exp_obj=NocaseDict([('Dog', 'Kitten'), ('Budgie', 'Fish')]),
        ),
        None, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_NOCASEDICT_UPDATE)
@simplified_test_function
def test_NocaseDict_update(testcase,
                           obj, args, kwargs, exp_obj):
    """
    Test function for NocaseDict.update()
    """

    # The code to be tested
    obj.update(*args, **kwargs)

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None

    # The verification below also uses some NocaseDict features, but that is
    # unavoidable if we want to work through the public interface:

    assert obj == exp_obj  # Uses NocaseDict equality


TESTCASES_NOCASEDICT_CLEAR = [

    # Testcases for NocaseDict.clear()

    # Each list item is a testcase tuple with these items:
    # * desc: Short testcase description.
    # * kwargs: Keyword arguments for the test function:
    #   * obj: NocaseDict object to be used for the test.
    # * exp_exc_types: Expected exception type(s), or None.
    # * exp_warn_types: Expected warning type(s), or None.
    # * condition: Boolean condition for testcase to run, or 'pdb' for debugger

    (
        "Empty dict",
        dict(
            obj=NocaseDict(),
        ),
        None, None, True
    ),
    (
        "Dict with two items",
        dict(
            obj=NocaseDict([('Dog', 'Cat'), ('Budgie', 'Fish')]),
        ),
        None, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_NOCASEDICT_CLEAR)
@simplified_test_function
def test_NocaseDict_clear(testcase, obj):
    """
    Test function for NocaseDict.clear()
    """

    # The code to be tested
    obj.clear()

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None

    # The verification below also uses some NocaseDict features, but that is
    # unavoidable if we want to work through the public interface:

    # The following line uses NocaseDict len
    assert len(obj) == 0  # pylint: disable=len-as-condition


TESTCASES_NOCASEDICT_COPY = [

    # Testcases for NocaseDict.copy()

    # Each list item is a testcase tuple with these items:
    # * desc: Short testcase description.
    # * kwargs: Keyword arguments for the test function:
    #   * obj: NocaseDict object to be used for the test.
    #   * test_key: Key for testing that copy is a copy, or None to skip.
    #   * test_value: Value for testing that copy is a copy.
    # * exp_exc_types: Expected exception type(s), or None.
    # * exp_warn_types: Expected warning type(s), or None.
    # * condition: Boolean condition for testcase to run, or 'pdb' for debugger

    (
        "Empty dict",
        dict(
            obj=NocaseDict(),
            test_key=None,
            test_value=None,
        ),
        None, None, True
    ),
    (
        "Dict with two items",
        dict(
            obj=NocaseDict([('Dog', 'Cat'), ('Budgie', 'Fish')]),
            test_key='Dog',
            test_value='Kitten',
        ),
        None, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_NOCASEDICT_COPY)
@simplified_test_function
def test_NocaseDict_copy(testcase,
                         obj, test_key, test_value):
    """
    Test function for NocaseDict.copy()
    """

    # The code to be tested
    obj_copy = obj.copy()

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None

    # The verification below also uses some NocaseDict features, but that is
    # unavoidable if we want to work through the public interface:

    assert obj_copy == obj  # Uses NocaseDict equality

    # Verify that the copy is a copy
    if test_key is not None:
        org_value = obj[test_key]  # Uses NocaseDict get
        obj_copy[test_key] = test_value  # Uses NocaseDict set
        now_value = obj[test_key]  # Uses NocaseDict get
        assert now_value == org_value


TESTCASES_NOCASEDICT_EQUAL_HASH = [

    # Testcases for NocaseDict.__hash__(), __eq__(), __ne__()

    # Each list item is a testcase tuple with these items:
    # * desc: Short testcase description.
    # * kwargs: Keyword arguments for the test function:
    #   * obj1: NocaseDict object #1 to use.
    #   * obj2: NocaseDict object #2 to use.
    #   * exp_obj_equal: Expected equality of the objects.
    # * exp_exc_types: Expected exception type(s), or None.
    # * exp_warn_types: Expected warning type(s), or None.
    # * condition: Boolean condition for testcase to run, or 'pdb' for debugger

    (
        "Empty dictionary",
        dict(
            obj1=NocaseDict([]),
            obj2=NocaseDict([]),
            exp_obj_equal=True,
        ),
        None, None, True
    ),
    (
        "One item, keys and values equal",
        dict(
            obj1=NocaseDict([('k1', 'v1')]),
            obj2=NocaseDict([('k1', 'v1')]),
            exp_obj_equal=True,
        ),
        None, None, True
    ),
    (
        "One item, keys equal, values different",
        dict(
            obj1=NocaseDict([('k1', 'v1')]),
            obj2=NocaseDict([('k1', 'v1_x')]),
            exp_obj_equal=False,
        ),
        None, None, True
    ),
    (
        "One item, keys different, values equal",
        dict(
            obj1=NocaseDict([('k1', 'v1')]),
            obj2=NocaseDict([('k2', 'v1')]),
            exp_obj_equal=False,
        ),
        None, None, True
    ),
    (
        "One item, keys equal, values both None",
        dict(
            obj1=NocaseDict([('k1', None)]),
            obj2=NocaseDict([('k1', None)]),
            exp_obj_equal=True,
        ),
        None, None, True
    ),
    (
        "One item, keys different lexical case, values equal",
        dict(
            obj1=NocaseDict([('K1', 'v1')]),
            obj2=NocaseDict([('k1', 'v1')]),
            exp_obj_equal=True,
        ),
        None, None, True
    ),
    (
        "Two equal items, in same order",
        dict(
            obj1=NocaseDict([('k1', 'v1'), ('k2', 'v2')]),
            obj2=NocaseDict([('k1', 'v1'), ('k2', 'v2')]),
            exp_obj_equal=True,
        ),
        None, None, True
    ),
    (
        "Two items, keys different lexical case, in same order",
        dict(
            obj1=NocaseDict([('K1', 'v1'), ('k2', 'v2')]),
            obj2=NocaseDict([('k1', 'v1'), ('K2', 'v2')]),
            exp_obj_equal=True,
        ),
        None, None, True
    ),
    (
        "Two equal items, in different order",
        dict(
            obj1=NocaseDict([('k1', 'v1'), ('k2', 'v2')]),
            obj2=NocaseDict([('k2', 'v2'), ('k1', 'v1')]),
            exp_obj_equal=True,
        ),
        None, None, True
    ),
    (
        "Two items, keys different lexical case, in different order",
        dict(
            obj1=NocaseDict([('k1', 'v1'), ('K2', 'v2')]),
            obj2=NocaseDict([('k2', 'v2'), ('K1', 'v1')]),
            exp_obj_equal=True,
        ),
        None, None, True
    ),
    (
        "Comparing unicode value with bytes value",
        dict(
            obj1=NocaseDict([('k1', b'v1')]),
            obj2=NocaseDict([('k2', u'v2')]),
            exp_obj_equal=False,
        ),
        None, None, True
    ),
    (
        "Matching unicode key with string key",
        dict(
            obj1=NocaseDict([('k1', 'v1')]),
            obj2=NocaseDict([(u'k2', 'v2')]),
            exp_obj_equal=False,
        ),
        None, None, True
    ),
    (
        "Higher key missing",
        dict(
            obj1=NocaseDict([('Budgie', 'Fish'), ('Dog', 'Cat')]),
            obj2=NocaseDict([('Budgie', 'Fish')]),
            exp_obj_equal=False,
        ),
        None, None, True
    ),
    (
        "Lower key missing",
        dict(
            obj1=NocaseDict([('Budgie', 'Fish'), ('Dog', 'Cat')]),
            obj2=NocaseDict([('Dog', 'Cat')]),
            exp_obj_equal=False,
        ),
        None, None, True
    ),
    (
        "First non-matching key is less. But longer size!",
        dict(
            obj1=NocaseDict([('Budgie', 'Fish'), ('Dog', 'Cat')]),
            obj2=NocaseDict([('Budgie', 'Fish'), ('Curly', 'Snake'),
                             ('Cozy', 'Dog')]),
            exp_obj_equal=False,
        ),
        None, None, True
    ),
    (
        "Only non-matching keys that are less. But longer size!",
        dict(
            obj1=NocaseDict([('Budgie', 'Fish'), ('Dog', 'Cat')]),
            obj2=NocaseDict([('Alf', 'F'), ('Anton', 'S'), ('Aussie', 'D')]),
            exp_obj_equal=False,
        ),
        None, None, True
    ),
    (
        "First non-matching key is greater. But shorter size!",
        dict(
            obj1=NocaseDict([('Budgie', 'Fish'), ('Dog', 'Cat')]),
            obj2=NocaseDict([('Budgio', 'Fish')]),
            exp_obj_equal=False,
        ),
        None, None, True
    ),
    (
        "Only non-matching keys that are greater. But shorter size!",
        dict(
            obj1=NocaseDict([('Budgie', 'Fish'), ('Dog', 'Cat')]),
            obj2=NocaseDict([('Zoe', 'F')]),
            exp_obj_equal=False,
        ),
        None, None, True
    ),
    (
        "Same size. First non-matching key is less",
        dict(
            obj1=NocaseDict([('Budgie', 'Fish'), ('Dog', 'Cat')]),
            obj2=NocaseDict([('Budgie', 'Fish'), ('Curly', 'Snake')]),
            exp_obj_equal=False,
        ),
        None, None, True
    ),
    (
        "Same size. Only non-matching keys that are less",
        dict(
            obj1=NocaseDict([('Budgie', 'Fish'), ('Dog', 'Cat')]),
            obj2=NocaseDict([('Alf', 'F'), ('Anton', 'S')]),
            exp_obj_equal=False,
        ),
        None, None, True
    ),
    (
        "Same size. Only non-matching keys that are greater",
        dict(
            obj1=NocaseDict([('Budgie', 'Fish'), ('Dog', 'Cat')]),
            obj2=NocaseDict([('Zoe', 'F'), ('Zulu', 'S')]),
            exp_obj_equal=False,
        ),
        None, None, True
    ),
    (
        "Same size, only matching keys. First non-matching value is less",
        dict(
            obj1=NocaseDict([('Budgie', 'Fish'), ('Dog', 'Cat')]),
            obj2=NocaseDict([('Budgie', 'Fish'), ('Dog', 'Car')]),
            exp_obj_equal=False,
        ),
        None, None, True
    ),
    (
        "Same size, only matching keys. First non-matching value is greater",
        dict(
            obj1=NocaseDict([('Budgie', 'Fish'), ('Dog', 'Cat')]),
            obj2=NocaseDict([('Budgie', 'Fish'), ('Dog', 'Caz')]),
            exp_obj_equal=False,
        ),
        None, None, True
    ),
]

TESTCASES_NOCASEDICT_EQUAL = [

    # Testcases for NocaseDict.__eq__(), __ne__()

    # Each list item is a testcase tuple with these items:
    # * desc: Short testcase description.
    # * kwargs: Keyword arguments for the test function:
    #   * obj1: NocaseDict object #1 to use.
    #   * obj2: NocaseDict object #2 to use.
    #   * exp_obj_equal: Expected equality of the objects.
    # * exp_exc_types: Expected exception type(s), or None.
    # * exp_warn_types: Expected warning type(s), or None.
    # * condition: Boolean condition for testcase to run, or 'pdb' for debugger

    (
        "A value raises TypeError when compared (and equal still succeeds)",
        dict(
            obj1=NocaseDict([('Budgie', 'Fish'), ('Dog', 'Cat')]),
            obj2=NocaseDict([('Budgie', NonComparable()), ('Dog', 'Cat')]),
            exp_obj_equal=False,
        ),
        None, None, True
    ),
]

TESTCASES_NOCASEDICT_HASH = [

    # Testcases for NocaseDict.__hash__() / hash(ncd)

    # Each list item is a testcase tuple with these items:
    # * desc: Short testcase description.
    # * kwargs: Keyword arguments for the test function:
    #   * obj1: NocaseDict object #1 to use.
    #   * obj2: NocaseDict object #2 to use.
    #   * exp_obj_equal: Expected equality of the objects.
    # * exp_exc_types: Expected exception type(s), or None.
    # * exp_warn_types: Expected warning type(s), or None.
    # * condition: Boolean condition for testcase to run, or 'pdb' for debugger

    (
        "A value raises TypeError when compared (and hash fails)",
        dict(
            obj1=NocaseDict([('Budgie', 'Fish'), ('Dog', 'Cat')]),
            obj2=NocaseDict([('Budgie', NonComparable()), ('Dog', 'Cat')]),
            exp_obj_equal=False,
        ),
        TypeError, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_NOCASEDICT_EQUAL_HASH + TESTCASES_NOCASEDICT_EQUAL)
@simplified_test_function
def test_NocaseDict_eq(testcase,
                       obj1, obj2, exp_obj_equal):
    """
    Test function for NocaseDict.__eq__() / ncd1==ncd2
    """

    # Double check they are different objects
    assert id(obj1) != id(obj2)

    # The code to be tested
    eq1 = (obj1 == obj2)
    eq2 = (obj2 == obj1)

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None

    assert eq1 == exp_obj_equal
    assert eq2 == exp_obj_equal


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_NOCASEDICT_EQUAL_HASH + TESTCASES_NOCASEDICT_EQUAL)
@simplified_test_function
def test_NocaseDict_ne(testcase,
                       obj1, obj2, exp_obj_equal):
    """
    Test function for NocaseDict.__ne__() / ncd1!=ncd2
    """

    # Double check they are different objects
    assert id(obj1) != id(obj2)

    # The code to be tested
    ne1 = (obj1 != obj2)
    ne2 = (obj2 != obj1)

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None

    assert ne1 != exp_obj_equal
    assert ne2 != exp_obj_equal


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_NOCASEDICT_EQUAL_HASH + TESTCASES_NOCASEDICT_HASH)
@simplified_test_function
def test_NocaseDict_hash(testcase,
                         obj1, obj2, exp_obj_equal):
    """
    Test function for NocaseDict.__hash__() / hash(ncd)
    """

    # Double check they are different objects
    assert id(obj1) != id(obj2)

    # The code to be tested
    hash1 = hash(obj1)
    hash2 = hash(obj2)

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None

    if exp_obj_equal:
        assert hash1 == hash2
    else:
        assert hash1 != hash2


TESTCASES_NOCASEDICT_ORDERING = [

    # Testcases for NocaseDict.__le__(), __lt__(), __ge__(), __gt__() / ord.ops

    # Each list item is a testcase tuple with these items:
    # * desc: Short testcase description.
    # * kwargs: Keyword arguments for the test function:
    #   * obj1: NocaseDict object #1 to be used.
    #   * obj2: NocaseDict object #2 to be used.
    #   * op: Order comparison operator to be used, as a string (e.g. '>')
    #   * exp_result: Expected result of the comparison, or None.
    # * exp_exc_types: Expected exception type(s), or None.
    # * exp_warn_types: Expected warning type(s), or None.
    # * condition: Boolean condition for testcase to run, or 'pdb' for debugger

    # Empty dicts
    (
        "Empty dicts with >",
        dict(
            obj1=NocaseDict(),
            obj2=NocaseDict(),
            op='>',
            exp_result=False,
        ),
        TypeError if six.PY3 else None, DeprecationWarning, True
    ),
    (
        "Empty dicts with >=",
        dict(
            obj1=NocaseDict(),
            obj2=NocaseDict(),
            op='>=',
            exp_result=True,
        ),
        TypeError if six.PY3 else None, DeprecationWarning, True
    ),
    (
        "Empty dicts with <",
        dict(
            obj1=NocaseDict(),
            obj2=NocaseDict(),
            op='<',
            exp_result=False,
        ),
        TypeError if six.PY3 else None, DeprecationWarning, True
    ),
    (
        "Empty dicts with <=",
        dict(
            obj1=NocaseDict(),
            obj2=NocaseDict(),
            op='<=',
            exp_result=True,
        ),
        TypeError if six.PY3 else None, DeprecationWarning, True
    ),

    # Equal dicts
    (
        "Equal dicts with >",
        dict(
            obj1=NocaseDict([('Budgie', 'Fish'), ('Dog', 'Cat')]),
            obj2=NocaseDict([('Budgie', 'Fish'), ('Dog', 'Cat')]),
            op='>',
            exp_result=False,
        ),
        TypeError if six.PY3 else None, DeprecationWarning, True
    ),
    (
        "Equal dicts with >=",
        dict(
            obj1=NocaseDict([('Budgie', 'Fish'), ('Dog', 'Cat')]),
            obj2=NocaseDict([('Budgie', 'Fish'), ('Dog', 'Cat')]),
            op='>=',
            exp_result=True,
        ),
        TypeError if six.PY3 else None, DeprecationWarning, True
    ),
    (
        "Equal dicts with <",
        dict(
            obj1=NocaseDict([('Budgie', 'Fish'), ('Dog', 'Cat')]),
            obj2=NocaseDict([('Budgie', 'Fish'), ('Dog', 'Cat')]),
            op='<',
            exp_result=False,
        ),
        TypeError if six.PY3 else None, DeprecationWarning, True
    ),
    (
        "Equal dicts with <=",
        dict(
            obj1=NocaseDict([('Budgie', 'Fish'), ('Dog', 'Cat')]),
            obj2=NocaseDict([('Budgie', 'Fish'), ('Dog', 'Cat')]),
            op='<=',
            exp_result=True,
        ),
        TypeError if six.PY3 else None, DeprecationWarning, True
    ),

    # Dicts that compare less (obj1 < obj2)
    (
        "Less-comparing dicts with >",
        dict(
            obj1=NocaseDict([('Budgie', 'Fish')]),
            obj2=NocaseDict([('Budgie', 'Fish'), ('Dog', 'Cat')]),
            op='>',
            exp_result=False,
        ),
        TypeError if six.PY3 else None, DeprecationWarning, True
    ),
    (
        "Less-comparing dicts with >=",
        dict(
            obj1=NocaseDict([('Budgie', 'Fish')]),
            obj2=NocaseDict([('Budgie', 'Fish'), ('Dog', 'Cat')]),
            op='>=',
            exp_result=False,
        ),
        TypeError if six.PY3 else None, DeprecationWarning, True
    ),
    (
        "Less-comparing dicts with <",
        dict(
            obj1=NocaseDict([('Budgie', 'Fish')]),
            obj2=NocaseDict([('Budgie', 'Fish'), ('Dog', 'Cat')]),
            op='<',
            exp_result=True,
        ),
        TypeError if six.PY3 else None, DeprecationWarning, True
    ),
    (
        "Less-comparing dicts with <=",
        dict(
            obj1=NocaseDict([('Budgie', 'Fish')]),
            obj2=NocaseDict([('Budgie', 'Fish'), ('Dog', 'Cat')]),
            op='<=',
            exp_result=True,
        ),
        TypeError if six.PY3 else None, DeprecationWarning, True
    ),

    # Dicts that compare greater (obj1 > obj2)
    (
        "Greater-comparing dicts with >",
        dict(
            obj1=NocaseDict([('Budgie', 'Fish'), ('Dog', 'Cat')]),
            obj2=NocaseDict([('Budgie', 'Fish')]),
            op='>',
            exp_result=True,
        ),
        TypeError if six.PY3 else None, DeprecationWarning, True
    ),
    (
        "Greater-comparing dicts with >=",
        dict(
            obj1=NocaseDict([('Budgie', 'Fish'), ('Dog', 'Cat')]),
            obj2=NocaseDict([('Budgie', 'Fish')]),
            op='>=',
            exp_result=True,
        ),
        TypeError if six.PY3 else None, DeprecationWarning, True
    ),
    (
        "Greater-comparing dicts with <",
        dict(
            obj1=NocaseDict([('Budgie', 'Fish'), ('Dog', 'Cat')]),
            obj2=NocaseDict([('Budgie', 'Fish')]),
            op='<',
            exp_result=False,
        ),
        TypeError if six.PY3 else None, DeprecationWarning, True
    ),
    (
        "Greater-comparing dicts with <=",
        dict(
            obj1=NocaseDict([('Budgie', 'Fish'), ('Dog', 'Cat')]),
            obj2=NocaseDict([('Budgie', 'Fish')]),
            op='<=',
            exp_result=False,
        ),
        TypeError if six.PY3 else None, DeprecationWarning, True
    ),

    # Note: More subtle cases of less- or greater-comparing dicts are not
    # tested because the ordering comparison for NocaseDict is deprecated.
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_NOCASEDICT_ORDERING)
@simplified_test_function
def test_NocaseDict_ordering(testcase,
                             obj1, obj2, op, exp_result):
    """
    Test function for NocaseDict.__le__(), __lt__(), __ge__(), __gt__() / ord.
    """

    comp_str = 'obj1 %s obj2' % op

    # Double check they are different objects
    assert id(obj1) != id(obj2)

    # The code to be tested
    result = eval(comp_str)  # pylint: disable=eval-used

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None

    assert result == exp_result


def test_unnamed_keys():
    """
    Test function for unnamed keys (key=None). This can be allowed in the
    NocaseDict via an undocumented attribute `allow_unnamed_keys`.
    """

    dic = NocaseDict()
    dic.allow_unnamed_keys = True

    dic[None] = 'a'
    assert None in dic
    assert len(dic) == 1

    a_val = dic[None]
    assert a_val == 'a'

    del dic[None]
    assert None not in dic
    assert not dic
