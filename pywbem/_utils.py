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
Utility functions for pywbem, with no use of other pywbem submodules.
"""

# This module is meant to be safe for 'import *'.

from __future__ import print_function, absolute_import

import re
import inspect
from string import Formatter
import six
try:
    from builtins import ascii
except ImportError:  # py2
    from future_builtins import ascii
try:
    from collections.abc import Mapping, Set, MutableSequence, Sequence
except ImportError:  # py2
    from collections import Mapping, Set, MutableSequence, Sequence

__all__ = []


def _ensure_unicode(obj):
    """
    If the input object is a string, make sure it is returned as a
    :term:`unicode string`, as follows:

    * If the input object already is a :term:`unicode string`, it is returned
      unchanged.
    * If the input string is a :term:`byte string`, it is decoded using UTF-8.
    * Otherwise, the input object was not a string and is returned unchanged.
    """
    if isinstance(obj, six.binary_type):
        return obj.decode("utf-8")
    return obj


def _ensure_bytes(obj):
    """
    If the input object is a string, make sure it is returned as a
    :term:`byte string`, as follows:

    * If the input object already is a :term:`byte string`, it is returned
      unchanged.
    * If the input string is a :term:`unicode string`, it is encoded using
      UTF-8.
    * Otherwise, the input object was not a string and is returned unchanged.
    """
    if isinstance(obj, six.text_type):
        return obj.encode("utf-8")
    return obj


def _ensure_bool(obj):
    """
    If the input object is not `None`, convert it to a :class:`py:bool`.
    If the input object is `None`, return it unchanged.
    """
    if obj is not None:
        obj = bool(obj)
    return obj


def _to_unicode(obj):
    """
    Convert the input binary string to a :term:`unicode string`.
    The input object must be a byte string.
    Use this if there is a previous test about the string type.
    """
    return obj.decode("utf-8")


def _to__bytes(obj):
    """
    Convert the input binary string to a :term:`byte string`.
    The input object must be a unicode string.
    Use this if there is a previous test about the string type.
    """
    return obj.encode("utf-8")


def _hash_name(name):
    """
    Hash a CIM name, case-insensitively.

    The name may be `None`.
    """
    if name is None:
        return hash(None)
    return hash(name.lower())


def _hash_item(item):
    """
    Hash an item (CIM value, CIM object), by delegating to its hash function.

    The item may be `None`.
    """
    if isinstance(item, list):
        item = tuple(item)
    return hash(item)


def _hash_dict(dict_):
    """
    Hash a NocaseDict object, by delegating to its hash function.

    The item may be `None`.
    """
    return hash(dict_)


def _stacklevel_above_module(mod_name):
    """
    Return the stack level (with 1 = caller of this function) of the first
    caller that is not defined in the specified module (e.g. "pywbem._cim_obj").

    The returned stack level can be used directly by the caller of this
    function as an argument for the stacklevel parameter of warnings.warn().
    """
    stacklevel = 2  # start with caller of our caller
    frame = inspect.stack()[stacklevel][0]  # stack() level is 0-based
    while True:
        if frame.f_globals.get('__name__', None) != mod_name:
            break
        stacklevel += 1
        frame = frame.f_back
    del frame
    return stacklevel


def _ascii2(value):
    """
    A variant of the `ascii()` built-in function known from Python 3 that:

    (1) ensures ASCII-only output, and
    (2) produces a nicer formatting for use in exception and warning messages
        and other human consumption.

    This function calls `ascii()` and post-processes its output as follows:

    * For unicode strings, a leading 'u' is stripped (u'xxx' becomes 'xxx'),
      if present.

    * For byte strings, a leading 'b' is stripped (b'xxx' becomes 'xxx'),
      if present.

    * For unicode strings, non-ASCII Unicode characters in the range U+0000 to
      U+00FF are represented as '/u00hh' instead of the confusing '/xhh'
      ('/' being a backslash, 'hh' being a 2-digit hex number).

    This function correctly handles values of collection types such as list,
    tuple, dict, and set, by producing the usual Python representation string
    for them. If the type is not the standard Python type (i.e. OrderedDict
    instead of dict), the type name is also shown in the result.

    Returns:
      str: ASCII string
    """

    if isinstance(value, Mapping):
        # NocaseDict in current impl. is not a Mapping; it uses
        # its own repr() implementation (via ascii(), called further down)
        items = [_ascii2(k) + ": " + _ascii2(v)
                 for k, v in six.iteritems(value)]
        item_str = "{" + ", ".join(items) + "}"
        if value.__class__.__name__ == 'dict':
            return item_str
        return "{0}({1})".format(value.__class__.__name__, item_str)

    if isinstance(value, Set):
        items = [_ascii2(v) for v in value]
        item_str = "{" + ", ".join(items) + "}"
        if value.__class__.__name__ == 'set':
            return item_str
        return "{0}({1})".format(value.__class__.__name__, item_str)

    if isinstance(value, MutableSequence):
        items = [_ascii2(v) for v in value]
        item_str = "[" + ", ".join(items) + "]"
        if value.__class__.__name__ == 'list':
            return item_str
        return "{0}({1})".format(value.__class__.__name__, item_str)

    if isinstance(value, Sequence) and \
            not isinstance(value, (six.text_type, six.binary_type)):
        items = [_ascii2(v) for v in value]
        if len(items) == 1:
            item_str = "(" + ", ".join(items) + ",)"
        else:
            item_str = "(" + ", ".join(items) + ")"
        if value.__class__.__name__ == 'tuple':
            return item_str
        return "{0}({1})".format(value.__class__.__name__, item_str)

    if isinstance(value, six.text_type):

        ret = ascii(value)  # returns type str in py2 and py3
        if ret.startswith('u'):
            ret = ret[1:]

        # Convert /xhh into /u00hh.
        # The two look-behind patterns address at least some of the cases that
        # should not be converted: Up to 5 backslashes in repr() result are
        # handled correctly. The failure that happens starting with 6
        # backslashes and even numbers of backslashes above that is not
        # dramatic: The /xhh is converted to /u00hh even though it shouldn't.
        ret = re.sub(r'(?<![^\\]\\)(?<![^\\]\\\\\\)\\x([0-9a-fA-F]{2})',
                     r'\\u00\1', ret)

    elif isinstance(value, six.binary_type):
        ret = ascii(value)  # returns type str in py2 and py3
        if ret.startswith('b'):
            ret = ret[1:]

    elif isinstance(value, (six.integer_types, float)):
        # str() on Python containers calls repr() on the items. PEP 3140
        # that attempted to fix that, has been rejected. See
        # https://www.python.org/dev/peps/pep-3140/.
        # We don't want to make that same mistake, and because ascii() calls
        # repr(), we call str() on the items explicitly. This makes a
        # difference for example for all pywbem.CIMInt values.
        ret = str(value)

    else:
        ret = ascii(value)  # returns type str in py2 and py3

    return ret


class _Ascii2Formatter(Formatter):
    """
    A class derived from `string.Formatter` that supports the conversion
    specifier 'A' to use the `_ascii2()` function (see there for details).

    Note that `string.Formatter` lacks some features of the built-in `format()`
    and `str.format()`` functions. Known are these deficiencies:

    * No unnamed replacements '{}'. Use positional {0} or keyword {f} instead.
    """

    def convert_field(self, value, conversion):
        """
        do any conversion on the resulting object
        """
        if conversion is None:  # pylint: disable=no-else-return
            return value
        elif conversion == 's':
            return str(value)
        elif conversion == 'r':
            return repr(value)
        elif conversion == 'a':
            return ascii(value)
        elif conversion == 'A':
            return _ascii2(value)
        raise ValueError(
            "Unknown conversion specifier {0!s}".format(conversion))


_ASCII2_FORMATTER = _Ascii2Formatter()


def _format(format_str, *args, **kwargs):
    """
    Return a formatted string, similar to the built-in `format()` function,
    except that it supports the conversion specifier 'A' to use the `_ascii2()`
    function (see there for details).
    """
    return _ASCII2_FORMATTER.format(format_str, *args, **kwargs)


# Pattern for DSP0004 binaryValue; group(1) is value without trailing B
BINARY_VALUE = re.compile(
    r'^([+\-]?(?:[0-1]+))B$',
    flags=(re.UNICODE | re.IGNORECASE))

# Pattern for DSP0004 octalValue
OCTAL_VALUE = re.compile(
    r'^[+\-]?0(?:[1-7]*)$',
    flags=(re.UNICODE))

# Pattern for DSP0004 decimalValue
DECIMAL_VALUE = re.compile(
    r'^[+\-]?(?:0|[1-9][0-9]*)$',
    flags=(re.UNICODE))

# Pattern for DSP0004 hexValue
HEX_VALUE = re.compile(
    r'^[+\-]?0X(?:[0-9A-F]+)$',
    flags=(re.UNICODE | re.IGNORECASE))

# Pattern for DSP0004 realValue (extended by INF, -INF, NAN)
REAL_VALUE = re.compile(
    r'^(?:[+\-]?[0-9]*\.[0-9]+(?:E[+\-]?[0-9]+)?|INF|-INF|NAN)$',
    flags=(re.UNICODE | re.IGNORECASE))


def _integerValue_to_int(value_str):
    """
    Convert a value string that conforms to DSP0004 `integerValue`, into
    the corresponding integer and return it. The returned value has Python
    type `int`, or in Python 2, type `long` if needed.

    Note that DSP0207 and DSP0004 only allow US-ASCII decimal digits. However,
    the Python `int()` function supports all Unicode decimal digits (e.g.
    US-ASCII digits, ARABIC-INDIC digits, superscripts, subscripts) and raises
    `ValueError` for non-decimal digits (e.g. Kharoshthi digits).
    Therefore, the match patterns explicitly check for US-ASCII digits, and
    the `int()` function should never raise `ValueError`.

    Returns `None` if the value string does not conform to `integerValue`.
    """
    m = BINARY_VALUE.match(value_str)
    if m:
        value = int(m.group(1), 2)
    elif OCTAL_VALUE.match(value_str):
        value = int(value_str, 8)
    elif DECIMAL_VALUE.match(value_str):
        value = int(value_str)
    elif HEX_VALUE.match(value_str):
        value = int(value_str, 16)
    else:
        value = None
    return value


def _realValue_to_float(value_str):
    """
    Convert a value string that conforms to DSP0004 `realValue`, into
    the corresponding float and return it.

    The special values 'INF', '-INF', and 'NAN' are supported.

    Note that the Python `float()` function supports a superset of input
    formats compared to the `realValue` definition in DSP0004. For example,
    "1." is allowed for `float()` but not for `realValue`. In addition, it
    has the same support for Unicode decimal digits as `int()`.
    Therefore, the match patterns explicitly check for US-ASCII digits, and
    the `float()` function should never raise `ValueError`.

    Returns None if the value string does not conform to `realValue`.
    """
    if REAL_VALUE.match(value_str):
        value = float(value_str)
    else:
        value = None
    return value
