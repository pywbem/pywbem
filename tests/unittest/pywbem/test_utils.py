#!/usr/bin/env python
"""
Tests for _utils module
"""

from __future__ import absolute_import

import platform
try:
    from collections import OrderedDict
except ImportError:
    from ordereddict import OrderedDict
import unicodedata
import random
import pytest
import six

from ..utils.unichr2 import unichr2
from ..utils.pytest_extensions import simplified_test_function

# pylint: disable=wrong-import-position, wrong-import-order, invalid-name
from ...utils import import_installed
pywbem = import_installed('pywbem')
from pywbem._utils import _ascii2, _format, _integerValue_to_int  # noqa: E402
from pywbem._cim_obj import NocaseDict  # noqa: E402
# pylint: enable=wrong-import-position, wrong-import-order, invalid-name

# Indicates whether binary strings are supported for the format string of
# _ascii2()
BYTE_FORMAT_SUPPORTED = six.PY2 or platform.python_implementation() == 'PyPy'

TESTCASES_ASCII2 = [

    # Testcases for _ascii2()

    # Each list item is a testcase tuple with these items:
    # * desc: Short testcase description.
    # * kwargs: Keyword arguments for the test function:
    #   * value: Input value (e.g. string).
    #   * exp_result: Expected result of _ascii2().
    # * exp_exc_types: Expected exception type(s), or None.
    # * exp_warn_types: Expected warning type(s), or None.
    # * condition: Boolean condition for testcase to run, or 'pdb' for debugger

    (
        "None",
        dict(
            value=None,
            exp_result="None",
        ),
        None, None, True
    ),
    (
        "Integer",
        dict(
            value=42,
            exp_result="42",
        ),
        None, None, True
    ),
    (
        "Unicode string, empty",
        dict(
            value=u'',
            exp_result="''",
        ),
        None, None, True
    ),
    (
        "Byte string, empty",
        dict(
            value=b'',
            exp_result="''",
        ),
        None, None, True
    ),
    (
        "Unicode string, ASCII",
        dict(
            value=u'abc',
            exp_result="'abc'",
        ),
        None, None, True
    ),
    (
        "Byte string, ASCII",
        dict(
            value=b'bla',
            exp_result="'bla'",
        ),
        None, None, True
    ),
    (
        "Unicode string, printable UCS-2 char below U+00FF",
        dict(
            value=u'\u00E0',
            exp_result="'\\u00e0'",
        ),
        None, None, True
    ),
    (
        "Unicode string, printable UCS-2 char above U+00FF",
        dict(
            value=u'\u041F',
            exp_result="'\\u041f'",
        ),
        None, None, True
    ),
    (
        "Unicode string, printable UCS-4 char",
        dict(
            value=u'\U0001D122',
            exp_result="'\\U0001d122'",
        ),
        None, None, True
    ),
    (
        "Unicode string, multiple printable UCS-2 chars below U+00FF",
        dict(
            value=u'\u00E0\u00E1\u00E2',
            exp_result="'\\u00e0\\u00e1\\u00e2'",
        ),
        None, None, True
    ),
    (
        "Unicode string, multiple printable UCS-2 chars above U+00FF",
        dict(
            value=u'\u041F\u0440\u6C2E',
            exp_result="'\\u041f\\u0440\\u6c2e'",
        ),
        None, None, True
    ),
    (
        "Unicode string, multiple printable UCS-4 chars",
        dict(
            value=u'\U0001D122\U0001D11E\U0001D106',
            exp_result="'\\U0001d122\\U0001d11e\\U0001d106'",
        ),
        None, None, True
    ),
    (
        "Unicode string, one backslash escape and rest of UCS-2 char",
        dict(
            value=u'\\xE0',
            exp_result="'\\\\xE0'",
        ),
        None, None, True
    ),
    (
        "Unicode string, one backslash escape and UCS-2 char",
        dict(
            value=u'\\\u00E0',
            exp_result="'\\\\\\u00e0'",
        ),
        None, None, True
    ),
    (
        "Unicode string, two backslash escapes and rest of UCS-2 char",
        dict(
            value=u'\\\\xE0',
            exp_result="'\\\\\\\\xE0'",
        ),
        None, None, True
    ),
    (
        "Unicode string, two backslash escapes and UCS-2 char",
        dict(
            value=u'\\\\\u00E0',
            exp_result="'\\\\\\\\\\u00e0'",
        ),
        None, None, True
    ),
    (
        "List of strings",
        dict(
            value=['a', 'b'],
            exp_result="['a', 'b']",
        ),
        None, None, True
    ),
    (
        "Tuple of strings",
        dict(
            value=('a', 'b'),
            exp_result="('a', 'b')",
        ),
        None, None, True
    ),
    (
        "Set of strings",
        dict(
            value=set(['a']),
            exp_result="{'a'}",
        ),
        None, None, True
    ),
    (
        "Dict of strings",
        dict(
            value={'a': 1},
            exp_result="{'a': 1}",
        ),
        None, None, True
    ),
    (
        "OrderedDict of strings",
        dict(
            value=OrderedDict([('a', 1), ('b', 2)]),
            exp_result="OrderedDict({'a': 1, 'b': 2})",
        ),
        None, None, True
    ),
    (
        "NocaseDict of strings",
        dict(
            value=NocaseDict([('a', 1), ('b', 2)]),
            exp_result="NocaseDict({'a': 1, 'b': 2})",
        ),
        None, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_ASCII2)
@simplified_test_function
def test_ascii2(testcase, value, exp_result):
    """
    Test function for _ascii2().
    """

    # The code to be tested
    act_result = _ascii2(value)

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None

    assert type(act_result) is type(exp_result)
    assert act_result == exp_result


TESTCASES_FORMAT_FIXED = [

    # Testcases for _format() with fixed data

    # Each list item is a testcase tuple with these items:
    # * desc: Short testcase description.
    # * kwargs: Keyword arguments for the test function:
    #   * format_str: Format string to be used for _format().
    #   * format_args: List of positional args to be used for _format().
    #   * format_kwargs: Dict of keyword args to be used for _format().
    #   * exp_result: Expected result of _format().
    # * exp_exc_types: Expected exception type(s), or None.
    # * exp_warn_types: Expected warning type(s), or None.
    # * condition: Boolean condition for testcase to run, or 'pdb' for debugger

    (
        "Unicode format string, empty",
        dict(
            format_str=u"",
            format_args=[],
            format_kwargs={},
            exp_result="",
        ),
        None, None, True
    ),
    (
        "Byte format string, empty",
        dict(
            format_str=b"",
            format_args=[],
            format_kwargs={},
            exp_result="",
        ),
        None if BYTE_FORMAT_SUPPORTED else TypeError, None, True
    ),
    (
        "Format string, empty",
        dict(
            format_str="",
            format_args=[],
            format_kwargs={},
            exp_result="",
        ),
        None, None, True
    ),
    (
        "Unicode format string without conversion and unicode string ASCII",
        dict(
            format_str=u"{0}",
            format_args=[u"abc"],
            format_kwargs={},
            exp_result=u"abc",
        ),
        None, None, True
    ),
    (
        "Byte format string without conversion and unicode string ASCII",
        dict(
            format_str=b"{0}",
            format_args=[u"abc"],
            format_kwargs={},
            exp_result=u"abc",
        ),
        None if BYTE_FORMAT_SUPPORTED else TypeError, None, True
    ),
    (
        "Format string without conversion and unicode string ASCII",
        dict(
            format_str="{0}",
            format_args=[u"abc"],
            format_kwargs={},
            exp_result=u"abc",
        ),
        None, None, True
    ),
    (
        "Unicode format string without conversion and byte string ASCII",
        dict(
            format_str=u"{0}",
            format_args=[b"abc"],
            format_kwargs={},
            exp_result="abc" if six.PY2 else "b'abc'",
        ),
        None, None, True
    ),
    (
        "Byte format string without conversion and byte string ASCII",
        dict(
            format_str=b"{0}",
            format_args=[b"abc"],
            format_kwargs={},
            exp_result="abc" if six.PY2 else "b'abc'",
        ),
        None if BYTE_FORMAT_SUPPORTED else TypeError, None, True
    ),
    (
        "Format string without conversion and byte string ASCII",
        dict(
            format_str="{0}",
            format_args=[b"abc"],
            format_kwargs={},
            exp_result="abc" if six.PY2 else "b'abc'",
        ),
        None, None, True
    ),
    (
        "Unicode format string with 's' and byte string ASCII",
        dict(
            format_str=u"{0!s}",
            format_args=[b"abc"],
            format_kwargs={},
            exp_result="abc" if six.PY2 else "b'abc'",
        ),
        None, None, True
    ),
    (
        "Unicode format string with 's' and unicode string ASCII",
        dict(
            format_str=u"{0!s}",
            format_args=[u"abc"],
            format_kwargs={},
            exp_result="abc",
        ),
        None, None, True
    ),
    (
        "Format string with 'r' and byte string ASCII",
        dict(
            format_str="{0!r}",
            format_args=[b"abc"],
            format_kwargs={},
            exp_result="'abc'" if six.PY2 else "b'abc'",
        ),
        None, None, True
    ),
    (
        "Format string with 'r' and unicode string ASCII",
        dict(
            format_str="{0!r}",
            format_args=[u"abc"],
            format_kwargs={},
            exp_result="u'abc'" if six.PY2 else "'abc'",
        ),
        None, None, True
    ),
    (
        "Format string with 'a' and byte string ASCII",
        dict(
            format_str="{0!a}",
            format_args=[b"abc"],
            format_kwargs={},
            exp_result="'abc'" if six.PY2 else "b'abc'",
        ),
        None, None, True
    ),
    (
        "Format string with 'a' and unicode string ASCII",
        dict(
            format_str="{0!a}",
            format_args=[u"abc"],
            format_kwargs={},
            exp_result="u'abc'" if six.PY2 else "'abc'",
        ),
        None, None, True
    ),
    (
        "Format string with 'A' and byte string ASCII",
        dict(
            format_str="{0!A}",
            format_args=[b"abc"],
            format_kwargs={},
            exp_result="'abc'",
        ),
        None, None, True
    ),
    (
        "Format string with 'A' and unicode string ASCII",
        dict(
            format_str="{0!A}",
            format_args=[u"abc"],
            format_kwargs={},
            exp_result="'abc'",
        ),
        None, None, True
    ),
    (
        "Format string with 'A' and unicode string UCS-2 below U+0100",
        dict(
            format_str="{0!A}",
            format_args=[u"a\u00E0b"],
            format_kwargs={},
            exp_result="'a\\u00e0b'",
        ),
        None, None, True
    ),
    (
        "Format string with 'A' and unicode string UCS-2 above U+00FF",
        dict(
            format_str="{0!A}",
            format_args=[u"a\u0412b"],
            format_kwargs={},
            exp_result="'a\\u0412b'",
        ),
        None, None, True
    ),
    (
        "Format string with 'A' and unicode string UCS-4 above U+FFFF",
        dict(
            format_str="{0!A}",
            format_args=[u"a\U0001D122b"],
            format_kwargs={},
            exp_result="'a\\U0001d122b'",
        ),
        None, None, True
    ),
    (
        "Format string with 'A' and list of strings",
        dict(
            format_str="{0!A}",
            format_args=[['a', 'b']],
            format_kwargs={},
            exp_result="['a', 'b']",
        ),
        None, None, True
    ),
    (
        "Format string with 'A' and tuple of strings",
        dict(
            format_str="{0!A}",
            format_args=[('a', 'b')],
            format_kwargs={},
            exp_result="('a', 'b')",
        ),
        None, None, True
    ),
    (
        "Format string with 'A' and set of strings",
        dict(
            format_str="{0!A}",
            format_args=[set(['a'])],
            format_kwargs={},
            exp_result="{'a'}",
        ),
        None, None, True
    ),
    (
        "Format string with 'A' and dict of strings",
        dict(
            format_str="{0!A}",
            format_args=[{'a': 1}],
            format_kwargs={},
            exp_result="{'a': 1}",
        ),
        None, None, True
    ),
    (
        "Format string with 'A' and OrderedDict of strings",
        dict(
            format_str="{0!A}",
            format_args=[OrderedDict([('a', 1), ('b', 2)])],
            format_kwargs={},
            exp_result="OrderedDict({'a': 1, 'b': 2})",
        ),
        None, None, True
    ),
    (
        "Format string with 'A' and NocaseDict of strings",
        dict(
            format_str="{0!A}",
            format_args=[NocaseDict([('a', 1), ('b', 2)])],
            format_kwargs={},
            exp_result="NocaseDict({'a': 1, 'b': 2})",
        ),
        None, None, True
    ),
    (
        "Format string with invalid conversion specifier",
        dict(
            format_str="{0!x}",
            format_args=["abc"],
            format_kwargs={},
            exp_result=None,
        ),
        ValueError, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_FORMAT_FIXED)
@simplified_test_function
def test_format_fixed(testcase, format_str, format_args, format_kwargs,
                      exp_result):
    """
    Test function for _format() with fixed data.
    """

    # The code to be tested
    act_result = _format(format_str, *format_args, **format_kwargs)

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None

    assert type(act_result) is type(exp_result)
    assert act_result == exp_result


UNICODE_CP_LIST = [
    0x000a, 0x0020, 0x0022, 0x0027, 0x005c, 0x00e0, 0x0412, 0x0001d122,
]
UNICODE_CP_LIST.extend(random.sample(six.moves.range(0, 0x10ffff), 100))


@pytest.fixture(params=UNICODE_CP_LIST, scope='module')
def unicode_cp(request):
    """
    Fixture representing variations of Unicode code points.

    Some code points are always in the result, and some random code points
    are added to the result.

    Returns an integer that is the Unicode code point.
    """
    return request.param


def test_format_random(unicode_cp):
    # pylint: disable=redefined-outer-name
    """
    Test _format() with a random set of Unicode code points.
    """

    unicode_char = unichr2(unicode_cp)
    if unicode_char is None:
        pytest.skip("Random Unicode code point U+%06X is a surrogate" %
                    unicode_cp)

    cat = unicodedata.category(unicode_char)
    if cat in ('Cn', 'Cc', 'Cs'):
        pytest.skip("Random Unicode code point U+%06X has category: %s" %
                    (unicode_cp, cat))

    # The code to be tested
    act_result = _format("{0!A}", unicode_char)

    # Construct the expected formatting result. Note that the result is
    # ASCII-only in all cases.
    if unicode_cp < 0x7F:
        if unicode_char == "'":
            # The standard ascii() function that is used generates a
            # backslash-escaped representation, but avoids that if possible
            # like in this case, where the single quote can remain unescaped
            # if the whole string is enclosed in double quotes.
            exp_result = '"\'"'
        elif unicode_char == '\\':
            # The standard ascii() function that is used generates a
            # backslash-escaped representation, so backslash itself needs
            # to be doubled.
            exp_result = "'\\\\'"
        else:
            exp_result = "'{0}'".format(unicode_char)
    elif unicode_cp < 0x10000:
        exp_result = "'\\u{0:04x}'".format(unicode_cp)
    else:
        exp_result = "'\\U{0:08x}'".format(unicode_cp)

    # pylint: disable=unidiomatic-typecheck
    assert type(act_result) is type(exp_result)
    assert act_result == exp_result


TESTCASES_INTEGER_VALUE_TO_INT = [

    # Testcases for _integerValue_to_int()

    # Each list item is a testcase tuple with these items:
    # * desc: Short testcase description.
    # * kwargs: Keyword arguments for the test function:
    #   * value_str: Input string value.
    #   * exp_result: Expected result of _integerValue_to_int().
    # * exp_exc_types: Expected exception type(s), or None.
    # * exp_warn_types: Expected warning type(s), or None.
    # * condition: Boolean condition for testcase to run, or 'pdb' for debugger

    # Test variations of zero
    (
        "Binary value '0b'",
        dict(
            value='0b',
            exp_result=0,
        ),
        None, None, True
    ),
    (
        "Binary value '0B'",
        dict(
            value='0B',
            exp_result=0,
        ),
        None, None, True
    ),
    (
        "Decimal / octal value '0'",
        dict(
            value='0',
            exp_result=0,
        ),
        None, None, True
    ),
    (
        "Hexadecimal value '0x0'",
        dict(
            value='0x0',
            exp_result=0,
        ),
        None, None, True
    ),
    (
        "Hexadecimal value '0X0'",
        dict(
            value='0X0',
            exp_result=0,
        ),
        None, None, True
    ),

    # Test variations of a single digit positive number
    (
        "Binary value '1b'",
        dict(
            value='1b',
            exp_result=1,
        ),
        None, None, True
    ),
    (
        "Binary value '1B'",
        dict(
            value='1B',
            exp_result=1,
        ),
        None, None, True
    ),
    (
        "Decimal value '1'",
        dict(
            value='1',
            exp_result=1,
        ),
        None, None, True
    ),
    (
        "Octal value '01'",
        dict(
            value='01',
            exp_result=1,
        ),
        None, None, True
    ),
    (
        "Hexadecimal value '0x1'",
        dict(
            value='0x1',
            exp_result=1,
        ),
        None, None, True
    ),
    (
        "Hexadecimal value '0X1'",
        dict(
            value='0X1',
            exp_result=1,
        ),
        None, None, True
    ),

    # Test variations of a single digit positive number
    (
        "Binary value '-1b'",
        dict(
            value='-1b',
            exp_result=-1,
        ),
        None, None, True
    ),
    (
        "Binary value '-1B'",
        dict(
            value='-1B',
            exp_result=-1,
        ),
        None, None, True
    ),
    (
        "Decimal value '-1'",
        dict(
            value='-1',
            exp_result=-1,
        ),
        None, None, True
    ),
    (
        "Octal value '-01'",
        dict(
            value='-01',
            exp_result=-1,
        ),
        None, None, True
    ),
    (
        "Hexadecimal value '-0x1'",
        dict(
            value='-0x1',
            exp_result=-1,
        ),
        None, None, True
    ),
    (
        "Hexadecimal value '-0X1'",
        dict(
            value='-0X1',
            exp_result=-1,
        ),
        None, None, True
    ),

    # Test correct base of conversion
    (
        "Binary value '1101b'",
        dict(
            value='1101b',
            exp_result=13,
        ),
        None, None, True
    ),
    (
        "Decimal value '123'",
        dict(
            value='123',
            exp_result=123,
        ),
        None, None, True
    ),
    (
        "Octal value '017'",
        dict(
            value='017',
            exp_result=15,
        ),
        None, None, True
    ),
    (
        "Hexadecimal value '0x1F'",
        dict(
            value='0x1F',
            exp_result=31,
        ),
        None, None, True
    ),
    (
        "Hexadecimal value '0X1f'",
        dict(
            value='0X1f',
            exp_result=31,
        ),
        None, None, True
    ),

    # Test invalid digits for the representation
    (
        "Binary value '1102b'",
        dict(
            value='1102b',
            exp_result=None,
        ),
        None, None, True
    ),
    (
        "Decimal value '12A'",
        dict(
            value='12A',
            exp_result=None,
        ),
        None, None, True
    ),
    (
        "Octal value '018'",
        dict(
            value='018',
            exp_result=None,
        ),
        None, None, True
    ),
    (
        "Hexadecimal value '0x1G'",
        dict(
            value='0x1G',
            exp_result=None,
        ),
        None, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_INTEGER_VALUE_TO_INT)
@simplified_test_function
def test_integerValue_to_int(testcase, value, exp_result):
    """
    Test function for _integerValue_to_int().
    """

    # The code to be tested
    act_result = _integerValue_to_int(value)

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None

    assert type(act_result) is type(exp_result)
    assert act_result == exp_result
