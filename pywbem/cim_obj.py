#
# (C) Copyright 2003-2007 Hewlett-Packard Development Company, L.P.
# (C) Copyright 2006-2007 Novell, Inc.
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
# Author: Tim Potter <tpot@hp.com>
# Author: Martin Pool <mbp@hp.com>
# Author: Bart Whiteley <bwhiteley@suse.de>
# Author: Ross Peoples <ross.peoples@gmail.com>
#

# pylint: disable=line-too-long
"""
CIM objects are local representations of CIM instances, classes, properties,
etc., as Python objects. They are used as input to and output from WBEM
operations:

==========================================  ==========================================================================
CIM object                                  Purpose
==========================================  ==========================================================================
:class:`~pywbem.CIMInstanceName`            Instance path of a CIM instance
:class:`~pywbem.CIMInstance`                CIM instance
:class:`~pywbem.CIMClassName`               Name of a CIM class, optionally with class path
:class:`~pywbem.CIMClass`                   CIM class
:class:`~pywbem.CIMProperty`                CIM property, both as property value in a CIM instance and as property
                                            declaration in a CIM class
:class:`~pywbem.CIMMethod`                  CIM method declaration in a CIM class
:class:`~pywbem.CIMParameter`               CIM parameter, both as a parameter value in a method invocation and as a
                                            parameter declaration in a CIM method declaration in a CIM class
:class:`~pywbem.CIMQualifier`               CIM qualifier value
:class:`~pywbem.CIMQualifierDeclaration`    CIM qualifier type/declaration
==========================================  ==========================================================================


.. _`Putting CIM objects in sets`:

Putting CIM objects in sets
---------------------------

Using sets for holding the result of :ref:`WBEM operations` is not uncommon,
because that allows comparison of results without regard to the (undefined)
order in which the objects are returned.

:ref:`CIM objects` are mutable and :term:`unchanged-hashable`. This requires
some caution when putting them in sets, or using them in any other way that
relies on their hash values.

The caution that is needed is that the public attributes, and therefore the
state of the CIM objects, must not change as long as they are a member of a
set, or used in any other way that relies on their hash values.

The following example shows what happens if a CIM object is modified while
being a member of a set:

::

    import pywbem

    s = set()

    # Create CIM object c1 and show its identity and hash value:
    c1 = pywbem.CIMClass('C')
    print(id(c1), hash(c1))  # (140362966049680, -7623128493967117119)

    # Add c1 to the set and verify the set content:
    s.add(c1)
    print([id(c) for c in s])  # [140362966049680]

    # Modify the c1 object; it now has changed its hash value:
    c1.superclass = 'B'
    print(id(c1), hash(c1))  # (140362966049680, 638672161836520435)

    # Create a CIM object c2 with the same attribute values as c1, and show
    # that they compare equal and that c2 has the same hash value as c1 now has:
    c2 = pywbem.CIMClass('C', superclass='B')
    print(c1 == c2)  # True
    print(id(c2), hash(c2))  # (140362970983696, 638672161836520435)

    # Add c2 to the set and verify the set content:
    s.add(c2)
    print([id(c) for c in s])  # [140362966049680, 140362970983696] !!

At the end, the set contains both objects even though they have the same hash
value. This is not what one would expect from
:ref:`set types <py:types-set>`.

The reason is that at the time the object c1 was added to the set, it had a
different hash value, and the set uses the hash value it found at insertion
time of its member for identifying the object. When the second object is added,
it finds it has a yet unknown hash value, and adds it.

While the set type in this particular Python implementation was able to still
look up the first member object even though its hash value has changed
meanwhile, other collection types or other Python implementations may not be as
forgiving and may not even be able to look up the object once its hash value
has changed.

Therefore, always make sure that the public attributes of CIM objects that are
put into a set remain unchanged while the object is in the set. The same
applies to any other usage of CIM objects that relies on their hash values.


.. _`Order of CIM child objects`:

Order of CIM child objects
--------------------------

:ref:`CIM objects` have zero or more lists of child objects. For example, a CIM
class (the parent object) has a list of CIM properties, CIM methods and CIM
qualifiers (the child objects).

In pywbem, the parent CIM object allows initializing each list of child objects
via an init parameter. For example, the :class:`~pywbem.CIMClass` init method
has a parameter named ``properties`` that allows specifying the CIM properties
of the CIM class.

Once the parent CIM object exists, each list of child objects can be modified
via a settable attribute. For example, the :class:`~pywbem.CIMClass` class has
a :attr:`~pywbem.CIMClass.properties` attribute for its list of CIM properties.

For such attributes and init parameters that specify lists of child
objects, pywbem supports a number of different ways the child objects can be
specified.

Some of these ways preserve the order of child objects and some don't.

This section uses CIM properties in CIM classes as an example, but it applies
to all kinds of child objects in CIM objects.

The possible input objects for the ``properties`` init parameter
and for the :attr:`~pywbem.CIMClass.properties` attribute of
:class:`~pywbem.CIMClass` is described in the type
:term:`properties input object`, and must be one of these objects:

* iterable of :class:`~pywbem.CIMProperty`
* iterable of tuple(key, value)
* :class:`~py:collections.OrderedDict` with key and value
* :class:`py:dict` with key and value (will not preserve order)

The keys are always the property names, and the values are always
:class:`~pywbem.CIMProperty` objects (at least when initializing classes).

Even though the :class:`~py:collections.OrderedDict` class preserves the order
of its items, intializing the dictionary with keyword arguments causes the
order of items to be lost before the dictionary is even initialized (before
Python 3.6). The only way to initialize a dictionary without loosing order of
items is by providing a list of tuples(key,value).

The following examples work but loose the order of properties in the class:

::

    # Examples where order of properties in class is not as specified:


    # Using an OrderedDict object, initialized with keyword arguments
    # (before Python 3.6):

    c1_props = OrderedDict(
        Prop1=CIMProperty('Prop1', value='abc'),
        Prop2=CIMProperty('Prop2', value=None, type='string'),
    )


    # Using a dict object, initialized with keyword arguments (This time
    # specified using key:value notation):

    c1_props = {
        'Prop1': CIMProperty('Prop1', value='abc'),
        'Prop2': CIMProperty('Prop2', value=None, type='string'),
    }


    # Using a dict object, initialized with list of tuple(key,value):

    c1_props = dict([
        ('Prop1', CIMProperty('Prop1', value='abc')),
        ('Prop2', CIMProperty('Prop2', value=None, type='string')),
    ])


    # Any of the above objects can be used to initialize the class properties:

    c1 = CIMClass('CIM_Foo', properties=c1_props)

The following examples all preserve the order of properties in the class:

::

    # Examples where order of properties in class is as specified:


    # Using a list of CIMProperty objects (starting with pywbem 0.12):

    c1_props = [
        CIMProperty('Prop1', value='abc'),
        CIMProperty('Prop2', value=None, type='string'),
    ]


    # Using an OrderedDict object, initialized with list of tuple(key,value):

    c1_props = OrderedDict([
        ('Prop1', CIMProperty('Prop1', value='abc')),
        ('Prop2', CIMProperty('Prop2', value=None, type='string')),
    ])


    # Using a list of tuple(key,value):

    c1_props = [
        ('Prop1', CIMProperty('Prop1', value='abc')),
        ('Prop2', CIMProperty('Prop2', value=None, type='string')),
    ]


    # Any of the above objects can be used to initialize the class properties:

    c1 = CIMClass('CIM_Foo', properties=c1_props)
"""  # noqa: E501
# pylint: enable=line-too-long
# Note: When used before module docstrings, Pylint scopes the disable statement
#       to the whole rest of the file, so we need an enable statement.

# This module is meant to be safe for 'import *'.

from __future__ import print_function, absolute_import

import warnings
import copy as copy_
import traceback
import re
try:
    from collections import OrderedDict
except ImportError:
    from ordereddict import OrderedDict
from xml.dom.minidom import Element
try:
    from builtins import type as builtin_type
except ImportError:  # py2
    from __builtin__ import type as builtin_type
import six

from . import cim_xml
from .config import DEBUG_WARNING_ORIGIN, SEND_VALUE_NULL
from . import config
from .cim_types import _CIMComparisonMixin, type_from_name, cimtype, \
    atomic_to_cim_xml, CIMType, CIMDateTime, Uint8, Sint8, Uint16, Sint16, \
    Uint32, Sint32, Uint64, Sint64, Real32, Real64, number_types, CIMInt, \
    CIMFloat, _Longint
from ._nocasedict import NocaseDict
from ._utils import _stacklevel_above_module, _ensure_unicode, _ensure_bool, \
    _hash_name, _hash_item, _hash_dict, _format, _integerValue_to_int, \
    _realValue_to_float, _to_unicode

__all__ = ['CIMClassName', 'CIMProperty', 'CIMInstanceName', 'CIMInstance',
           'CIMClass', 'CIMMethod', 'CIMParameter', 'CIMQualifier',
           'CIMQualifierDeclaration', 'tocimxml', 'tocimxmlstr', 'tocimobj',
           'cimvalue']

# Constants for MOF formatting output
MOF_INDENT = 3
MAX_MOF_LINE = 80

# Patterns for WBEM URI parsing, consistent with DSP0207, except that for a
# local WBEM URI (no namespace type, no authority), the leading slash required
# by DSP0207 is optional for pywbem.
WBEM_URI_CLASSPATH_REGEXP = re.compile(
    r'^(?:([\w\-]+):)?'  # namespace type (URI scheme)
    r'(?://([\w.:@\[\]]*))?'  # authority (host)
    r'(?:/|^/?)(\w+(?:/\w+)*)?'  # namespace name (leading slash optional)
    r'(?::|^:?)(\w+)$',  # class name (leading colon optional)
    flags=re.UNICODE)
WBEM_URI_INSTANCEPATH_REGEXP = re.compile(
    r'^(?:([\w\-]+):)?'  # namespace type (URI scheme)
    r'(?://([\w.:@\[\]]*))?'  # authority (host)
    r'(?:/|^/?)(\w+(?:/\w+)*)?'  # namespace name (leading slash optional)
    r'(?::|^:?)(\w+)'  # class name (leading colon optional)
    r'\.(.+)$',  # key bindings
    flags=re.UNICODE)

# For parsing the key bindings using a regexp, we just distinguish the
# differently quoted forms. The exact types of the key values are determined
# lateron:
_KB_NOT_QUOTED = r'[^,"\'\\]+'
_KB_SINGLE_QUOTED = r"'(?:[^'\\]|\\.)*'"
_KB_DOUBLE_QUOTED = r'"(?:[^"\\]|\\.)*"'
_KB_VAL = r'(?:{0}|{1}|{2})'.format(
    _KB_NOT_QUOTED, _KB_SINGLE_QUOTED, _KB_DOUBLE_QUOTED)

# To get all repetitions, capture a repeated group instead of repeating a
# capturing group: https://www.regular-expressions.info/captureall.html
WBEM_URI_KEYBINDINGS_REGEXP = re.compile(
    # pylint: disable=duplicate-string-formatting-argument
    r'^(\w+={0})((?:,\w+={1})*)$'.format(_KB_VAL, _KB_VAL),
    flags=(re.UNICODE | re.IGNORECASE))

WBEM_URI_KB_FINDALL_REGEXP = re.compile(
    r',\w+={0}'.format(_KB_VAL),
    flags=(re.UNICODE | re.IGNORECASE))

# Valid namespace types (URI schemes) for WBEM URI parsing
WBEM_URI_NAMESPACE_TYPES = [
    'http', 'https',
    'cimxml-wbem', 'cimxml-wbems',
]

# CIM data type names, used for checking
ALL_CIMTYPES = set([
    'boolean',
    'string',
    'char16',
    'datetime',
    'uint8',
    'uint16',
    'uint32',
    'uint64',
    'sint8',
    'sint16',
    'sint32',
    'sint64',
    'real32',
    'real64',
    'reference',
])


def cmpname(name1, name2):
    """
    Compare two CIM names for equality and ordering.

    The comparison is performed case-insensitively.

    One or both of the items may be `None`, and `None` is considered the lowest
    possible value.

    The implementation delegates to the '==' and '<' operators of the
    name datatypes.

    If name1 == name2, 0 is returned.
    If name1 < name2, -1 is returned.
    Otherwise, +1 is returned.
    """
    if name1 is None and name2 is None:
        return 0
    if name1 is None:
        return -1
    if name2 is None:
        return 1
    lower_name1 = name1.lower()
    lower_name2 = name2.lower()
    if lower_name1 == lower_name2:
        return 0
    return -1 if lower_name1 < lower_name2 else 1


def cmpitem(item1, item2):
    """
    Compare two items (CIM values, CIM objects) for equality (not for
    ordering).

    Note: Support for comparing the order of the items has been removed
    in pywbem 0.9.

    One or both of the items may be `None`.

    Returns:
        0 if the objects are equal.
        1 if the objects are not equal.
    """
    if item1 is None and item2 is None:
        return 0
    if item1 is None or item2 is None:
        return 1
    if item1 == item2:
        return 0
    return 1


def cmpdict(dict1, dict2):
    """
    Compare two NocaseDict objects for equality (not for ordering).

    The comparison is performed case-insensitively w.r.t. to the dictionary
    keys.

    One or both of the items may be `None`.

    Returns:
        0 if the objects are equal.
        1 if the objects are not equal.
    """
    if dict1 is None and dict2 is None:
        return 0
    if dict1 is None or dict2 is None:
        return 1
    if dict1 == dict2:
        return 0
    return 1


def _qualifiers_tomof(qualifiers, indent, maxline=MAX_MOF_LINE):
    """
    Return a MOF string with the qualifier values, including the surrounding
    square brackets. The qualifiers are ordered by their name.

    Return empty string if no qualifiers.

    Normally multiline output and may fold qualifiers into multiple lines.

    The order of qualifiers is preserved.

    Parameters:

      qualifiers (NocaseDict): Qualifiers to format.

      indent (:term:`integer`): Number of spaces to indent each line of
        the returned string, counted to the opening bracket in the first line.

    Returns:

      :term:`unicode string`: MOF string.
    """

    if not qualifiers:
        return u''

    mof = []

    mof.append(_indent_str(indent))
    mof.append(u'[')
    line_pos = indent + 1

    mof_quals = []
    for q in qualifiers.itervalues():
        mof_quals.append(q.tomof(indent + 1 + MOF_INDENT, maxline, line_pos))
    delim = ',\n' + _indent_str(indent + 1)
    mof.append(delim.join(mof_quals))

    mof.append(u']\n')

    return u''.join(mof)


def _indent_str(indent):
    """
    Return a MOF indent pad unicode string from the indent integer variable
    that defines number of spaces to indent. Used to format MOF output.
    """
    return u''.ljust(indent, u' ')


def _mof_escaped(strvalue):
    # Note: This is a raw docstring because it shows many backslashes, and
    # that avoids having to double them.
    r"""
    Return a MOF-escaped string from the input string.

    Parameters:

      strvalue (:term:`unicode string`): The string value. Must not be `None`.
        Special characters must not be backslash-escaped.

    Details on backslash-escaping:

    `DSP0004` defines that the character repertoire for MOF string constants
    is the entire repertoire for the CIM string datatype. That is, the entire
    Unicode character repertoire except for U+0000.

    The only character for which `DSP0004` requires the use of a MOF escape
    sequence in a MOF string constant, is the double quote (because a MOF
    string constant is enclosed in double quotes).

    `DSP0004` defines MOF escape sequences for several more characters, but it
    does not require their use in MOF. For example, it is valid for a MOF
    string constant to contain the (unescaped) characters U+000D (newline) or
    U+0009 (horizontal tab), and others.

    Processing the MOF escape sequences as unescaped characters may not be
    supported by MOF-related tools, and therefore this function plays it safe
    and uses the MOF escape sequences defined in `DSP0004` as much as possible.
    The following table shows the MOF escape sequences defined in `DSP0004`
    and whether they are used (i.e. generated) by this function:

    ========== ==== ===========================================================
    MOF escape Used Character
    sequence
    ========== ==== ===========================================================
    \b         yes  U+0008: Backspace
    \t         yes  U+0009: Horizontal tab
    \n         yes  U+000A: Line feed
    \f         yes  U+000C: Form feed
    \r         yes  U+000D: Carriage return
    \"         yes  U+0022: Double quote (") (required to be used)
    \'         yes  U+0027: Single quote (')
    \\         yes  U+005C: Backslash (\)
    \x<hex>    (1)  U+<hex>: Any UCS-2 character, where <hex> is one to four
                      hex digits, representing its UCS code position (this form
                      is limited to the UCS-2 character repertoire)
    \X<hex>    no   U+<hex>: Any UCS-2 character, where <hex> is one to four
                      hex digits, representing its UCS code position (this form
                      is limited to the UCS-2 character repertoire)
    ========== ==== ===========================================================

    (1) Yes, for all other characters in the so called "control range"
        U+0001..U+001F.
    """

    escaped_str = strvalue

    # Escape backslash (\)
    escaped_str = escaped_str.replace('\\', '\\\\')

    # Escape \b, \t, \n, \f, \r
    # Note, the Python escape sequences happen to be the same as in MOF
    escaped_str = escaped_str.\
        replace('\b', '\\b').\
        replace('\t', '\\t').\
        replace('\n', '\\n').\
        replace('\f', '\\f').\
        replace('\r', '\\r')

    # Escape remaining control characters (U+0001...U+001F), skipping
    # U+0008, U+0009, U+000A, U+000C, U+000D that are already handled.
    # We hard code it to be faster, plus we can easily skip already handled
    # chars.
    # The generic code would be (not skipping already handled chars):
    #     for cp in range(1, 32):
    #         c = six.unichr(cp)
    #         esc = '\\x{0:04X}'.format(cp)
    #         escaped_str = escaped_str.replace(c, esc)
    escaped_str = escaped_str.\
        replace(u'\u0001', '\\x0001').\
        replace(u'\u0002', '\\x0002').\
        replace(u'\u0003', '\\x0003').\
        replace(u'\u0004', '\\x0004').\
        replace(u'\u0005', '\\x0005').\
        replace(u'\u0006', '\\x0006').\
        replace(u'\u0007', '\\x0007').\
        replace(u'\u000B', '\\x000B').\
        replace(u'\u000E', '\\x000E').\
        replace(u'\u000F', '\\x000F').\
        replace(u'\u0010', '\\x0010').\
        replace(u'\u0011', '\\x0011').\
        replace(u'\u0012', '\\x0012').\
        replace(u'\u0013', '\\x0013').\
        replace(u'\u0014', '\\x0014').\
        replace(u'\u0015', '\\x0015').\
        replace(u'\u0016', '\\x0016').\
        replace(u'\u0017', '\\x0017').\
        replace(u'\u0018', '\\x0018').\
        replace(u'\u0019', '\\x0019').\
        replace(u'\u001A', '\\x001A').\
        replace(u'\u001B', '\\x001B').\
        replace(u'\u001C', '\\x001C').\
        replace(u'\u001D', '\\x001D').\
        replace(u'\u001E', '\\x001E').\
        replace(u'\u001F', '\\x001F')

    # Escape single and double quote
    escaped_str = escaped_str.replace('"', '\\"')
    escaped_str = escaped_str.replace("'", "\\'")

    return escaped_str


def mofstr(value, indent=MOF_INDENT, maxline=MAX_MOF_LINE, line_pos=0,
           end_space=0, avoid_splits=False, quote_char=u'"'):
    """
    Low level function that returns the MOF representation of a string value
    (i.e. a value that can be split into multiple parts, for example a string,
    reference or datetime typed value).

    The function performs the backslash-escaping of characters in the string
    (for details, see function _mof_escaped()), handles the splitting into
    multiple string parts if the current line does not have sufficient space
    left, and surrounds the string parts (or the entire string, if it ends up
    having only one part) with the specified quote characters.

    The strategy for starting new lines and for splitting the string into parts
    is:

    * If the string fits into the current line, it is output.
    * If the 'avoid_splits' flag is set, a new line is generating. If the
      string fits onto the new line, it is output. Otherwise, the string is
      split into parts and these are output starting with the new line,
      generating additional new lines as needed.
    * If the 'avoid_splits' flag is not set, the string is split into parts and
      these are output starting with the current line, generating new lines as
      needed.
    * Strings are first tried to split after the rightmost space character that
      would still make it fit onto the line, and only if there is no space
      character in that range, the string is split at a non-space position.

    Parameters:

      value (:term:`unicode string`): The string value. Must not be `None`.
        Special characters must not be backslash-escaped.

      indent (:term:`integer`): Number of spaces to indent any new lines that
        are generated.

      maxline (:term:`integer`): Maximum line length for the generated MOF.

      line_pos (:term:`integer`): Length of content already on the current
        line.

      end_space (:term:`integer`): Length of space to be left free on the last
        line.

      avoid_splits (bool): Avoid splits at the price of starting a new line
        instead of using the current line.

      quote_char (:term:`unicode string`): Character to be used for surrounding
        the string parts with. For CIM string typed values, this must be a
        double quote (the default), and for CIM char16 typed values, this must
        be a single quote.

    Returns:

      tuple of
        * :term:`unicode string`: MOF string.
        * new line_pos
    """

    assert isinstance(value, six.text_type)

    value = _mof_escaped(value)

    quote_len = 2  # length of the quotes surrounding a string part
    new_line = u'\n' + _indent_str(indent)

    mof = []

    while True:

        # Prepare safety check for endless loops
        saved_value = value

        avl_len = maxline - line_pos - quote_len

        # Decide whether to start a new line
        if len(value) > avl_len - end_space:
            if avoid_splits or avl_len < 0:
                # Start a new line
                mof.append(new_line)
                line_pos = indent
                avl_len = maxline - indent - quote_len
            else:
                # Find last fitting blank
                blank_pos = value.rfind(u' ', 0, avl_len)
                if blank_pos < 0:
                    # We cannot split at a blank -> start a new line
                    mof.append(new_line)
                    line_pos = indent
                    avl_len = maxline - indent - quote_len

        # Check whether the entire string fits (that is a last line, then)
        if len(value) <= avl_len - end_space:
            mof.append(quote_char)
            mof.append(value)
            mof.append(quote_char)
            line_pos += quote_len + len(value)
            break

        # Split the string and output the next part
        split_pos = value.rfind(u' ', 0, avl_len)
        if split_pos < 0:
            # We have to split within a word
            split_pos = avl_len - 1
        part_value = value[0:split_pos + 1]
        value = value[split_pos + 1:]
        mof.append(quote_char)
        mof.append(part_value)
        mof.append(quote_char)
        line_pos += quote_len + len(part_value)

        if value == u'':
            break

        # A safety check for endless loops
        assert value != saved_value, \
            _format("Endless loop in mofstr() with state: "
                    "mof_str={0!A}, value={1!A}, avl_len={2}, end_space={3}, "
                    "split_pos={4}",
                    u''.join(mof), value, avl_len, end_space, split_pos)

    mof_str = u''.join(mof)
    return mof_str, line_pos


def mofval(value, indent=MOF_INDENT, maxline=MAX_MOF_LINE, line_pos=0,
           end_space=0):
    """
    Low level function that returns the MOF representation of a non-string
    value (i.e. a value that cannot not be split into multiple parts, for
    example a numeric or boolean value).

    If the MOF representation of the value does not fit into the remaining
    space of the current line, it is put into a new line, considering the
    specified indentation. If it also does not fit on the remaining space of
    the new line, ValueError is raised.

    Parameters:

      value (:term:`unicode string`): The non-string value. Must not be `None`.

      indent (:term:`integer`): Number of spaces to indent any new lines that
        are generated.

      maxline (:term:`integer`): Maximum line length for the generated MOF.

      line_pos (:term:`integer`): Length of content already on the current
        line.

      end_space (:term:`integer`): Length of space to be left free on the last
        line.

    Returns:

      tuple of
        * :term:`unicode string`: MOF string.
        * new line_pos

    Raises:

      ValueError: The value does not fit onto an entire new line.
    """

    assert isinstance(value, six.text_type)

    # Check for output on current line
    avl_len = maxline - line_pos - end_space
    if len(value) <= avl_len:
        line_pos += len(value)
        return value, line_pos

    # Check for output on new line
    avl_len = maxline - indent - end_space
    if len(value) <= avl_len:
        mof_str = u'\n' + _indent_str(indent) + value
        line_pos = indent + len(value)
        return mof_str, line_pos

    raise ValueError(
        _format("Cannot fit value {0!A} onto new MOF line, missing {1} "
                "characters", value, len(value) - avl_len))


def moftype(cim_type, refclass):
    """
    Converts a CIM data type name to MOF syntax.
    """

    return (refclass + ' REF') if cim_type == 'reference' else cim_type


def _scalar_value_tomof(
        value, type, indent=0, maxline=MAX_MOF_LINE, line_pos=0, end_space=0,
        avoid_splits=False):
    # pylint: disable=line-too-long,redefined-builtin
    """
    Return a MOF string representing a scalar CIM-typed value.

    `None` is returned as 'NULL'.

    Parameters:

      value (:term:`CIM data type`, :term:`number`, :class:`~pywbem.CIMInstance`, :class:`~pywbem.CIMClass`):
        The scalar CIM-typed value. May be `None`.

        Must not be an array/list/tuple. Must not be a :ref:`CIM object` other
        than those listed.

      type (string): CIM data type name.

      indent (:term:`integer`): Number of spaces to indent any new lines that
        are generated.

      maxline (:term:`integer`): Maximum line length for the generated MOF.

      line_pos (:term:`integer`): Length of content already on the current
        line.

      end_space (:term:`integer`): Length of space to be left free on the last
        line.

      avoid_splits (bool): Avoid splits at the price of starting a new line
        instead of using the current line.

    Returns:

      tuple of
        * :term:`unicode string`: MOF string.
        * new line_pos
    """  # noqa: E501

    if value is None:
        return mofval(u'NULL', indent, maxline, line_pos, end_space)

    if type == 'string':  # pylint: disable=no-else-raise
        if isinstance(value, six.string_types):
            return mofstr(value, indent, maxline, line_pos, end_space,
                          avoid_splits)

        if isinstance(value, (CIMInstance, CIMClass)):
            # embedded instance or class
            return mofstr(value.tomof(), indent, maxline, line_pos, end_space,
                          avoid_splits)
        raise TypeError(
            _format("Scalar value of CIM type {0} has invalid Python type "
                    "type {1} for conversion to a MOF string",
                    type, builtin_type(value)))

    elif type == 'char16':
        return mofstr(value, indent, maxline, line_pos, end_space, avoid_splits,
                      quote_char=u"'")
    elif type == 'boolean':
        val = u'true' if value else u'false'
        return mofval(val, indent, maxline, line_pos, end_space)
    elif type == 'datetime':
        val = six.text_type(value)
        return mofstr(val, indent, maxline, line_pos, end_space, avoid_splits)
    elif type == 'reference':
        val = value.to_wbem_uri()
        return mofstr(val, indent, maxline, line_pos, end_space, avoid_splits)
    elif isinstance(value, (CIMFloat, CIMInt, int, _Longint)):
        val = six.text_type(value)
        return mofval(val, indent, maxline, line_pos, end_space)
    else:
        assert isinstance(value, float), \
            _format("Scalar value of CIM type {0} has invalid Python type {1} "
                    "for conversion to a MOF string",
                    type, builtin_type(value))
        val = repr(value)
        return mofval(val, indent, maxline, line_pos, end_space)


def _value_tomof(
        value, type, indent=0, maxline=MAX_MOF_LINE, line_pos=0, end_space=0,
        avoid_splits=False):
    # pylint: disable=redefined-builtin
    """
    Return a MOF string representing a CIM-typed value (scalar or array).

    In case of an array, the array items are separated by comma, but the
    surrounding curly braces are not added.

    Parameters:

      value (CIM-typed value or list of CIM-typed values): The value.

      indent (:term:`integer`): Number of spaces to indent any new lines that
        are generated.

      maxline (:term:`integer`): Maximum line length for the generated MOF.

      line_pos (:term:`integer`): Length of content already on the current
        line.

      end_space (:term:`integer`): Length of space to be left free on the last
        line.

      avoid_splits (bool): Avoid splits at the price of starting a new line
        instead of using the current line.

    Returns:

      tuple of
        * :term:`unicode string`: MOF string.
        * new line_pos
    """

    if isinstance(value, list):

        mof = []

        for i, v in enumerate(value):

            if i > 0:
                # Assume we would add comma and space as separator
                line_pos += 2

            val_str, line_pos = _scalar_value_tomof(
                v, type, indent, maxline, line_pos, end_space + 2, avoid_splits)

            if i > 0:
                # Add the actual separator
                mof.append(u',')
                if val_str[0] != '\n':
                    mof.append(u' ')
                else:
                    # Adjust by the space we did not need
                    line_pos -= 1

            mof.append(val_str)

        mof_str = u''.join(mof)

    else:
        mof_str, line_pos = _scalar_value_tomof(
            value, type, indent, maxline, line_pos, end_space, avoid_splits)

    return mof_str, line_pos


def _cim_keybinding(key, value):
    """
    Return a keybinding value, from dict item input (key+value).
    Key may be None (for unnamed keys).

    The returned value will be a CIM-typed value, except if it was provided as
    Python number type (in which case it will remain that type).

    Invalid types or values cause TypeError or ValueError to be raised.
    """

    if key is not None and isinstance(value, CIMProperty):
        if value.name.lower() != key.lower():
            raise ValueError(
                _format("Invalid keybinding name: CIMProperty.name must be "
                        "dictionary key {0!A}, but is {1!A}",
                        key, value.name))
        return copy_.copy(value.value)

    if value is None:
        return None

    if isinstance(value, six.text_type):
        return value

    if isinstance(value, six.binary_type):
        return _to_unicode(value)

    if isinstance(value, (bool, CIMInstanceName, CIMType)):
        return value

    # pylint: disable=unidiomatic-typecheck
    if builtin_type(value) in number_types:
        # Note: The CIM data types are derived from the built-in types, so we
        # cannot use isinstance() for this test.

        # Ideally, pywbem won't accept keybinding values specified as Python
        # number typed values, but require a CIM data type (e.g. Uint32 or
        # Real32).
        # However, there are two reasons for continuing to allow that:
        # * It was allowed in earlier versions of pywbem.
        # * Parsing the (untyped) WBEM URI of an instance path, results in
        #   int or float values without size, and the size information
        #   to automatically convert that into numeric CIM data types is
        #   not available.
        return value

    if isinstance(value, (CIMClass, CIMInstance)):
        raise TypeError(
            _format("Value of keybinding {0!A} cannot be an embedded object: "
                    "{1}", key, type(value)))

    if isinstance(value, list):
        raise TypeError(
            _format("Value of keybinding {0!A} cannot be a list", key))

    raise TypeError(
        _format("Value of keybinding {0!A} has an invalid type: {1}",
                key, type(value)))


def _cim_property_value(key, value):
    """
    Return a CIMProperty object for representing a property value, from dict
    item input (key+value), after performing some checks.

    If the input value is a CIMProperty object, it is returned.

    Otherwise, a new CIMProperty object is created from the input value, and
    returned.
    """

    if key is None:
        raise ValueError("Property name must not be None")

    if isinstance(value, CIMProperty):
        if value.name.lower() != key.lower():
            raise ValueError(
                _format("CIMProperty.name must be dictionary key {0!A}, but is"
                        "{1!A}", key, value.name))
        prop = value
    else:
        # We no longer check for the common error to set CIM numeric values as
        # Python number types, because that is done in the CIMProperty
        # init method.
        prop = CIMProperty(key, value)

    return prop


def _cim_property_decl(key, value):
    """
    Return a CIMProperty object for representing a property declaration, from
    dict item input (key+value), after performing some checks.

    The input value must be a CIMProperty object, which is returned.
    """

    if key is None:
        raise ValueError("Property name must not be None")

    try:
        assert isinstance(value, CIMProperty)
    except AssertionError:
        raise TypeError(
            _format("Property must be a CIMProperty object, but is: {0}",
                    type(value)))

    if value.name.lower() != key.lower():
        raise ValueError(
            _format("CIMProperty.name must be dictionary key {0!A}, but is "
                    "{1!A}", key, value.name))

    return value


def _cim_method(key, value):
    """
    Return a CIMMethod object, from dict item input (key+value), after
    performing some checks.

    The input value must be a CIMMethod object, which is returned.
    """

    if key is None:
        raise ValueError("Method name must not be None")

    try:
        assert isinstance(value, CIMMethod)
    except AssertionError:
        raise TypeError(
            _format("Method must be a CIMMethod object, but is: {0}",
                    type(value)))

    if value.name.lower() != key.lower():
        raise ValueError(
            _format("CIMMethod.name must be dictionary key {0!A}, but is ",
                    "{1!A}", key, value.name))

    return value


def _cim_qualifier(key, value):
    """
    Return a CIMQualifier object, from dict item input (key+value), after
    performing some checks.

    If the input value is a CIMQualifier object, it is returned.

    Otherwise, a new CIMQualifier object is created from the input value, and
    returned.
    """

    if key is None:
        raise ValueError("Qualifier name must not be None")

    if isinstance(value, CIMQualifier):
        if value.name.lower() != key.lower():
            raise ValueError(
                _format("CIMQualifier.name must be dictionary key {0!A}, but "
                        "is {1!A}", key, value.name))
        qual = value
    else:
        # We no longer check for the common error to set CIM numeric values as
        # Python number types, because that is done in the CIMQualifier
        # init method.
        qual = CIMQualifier(key, value)

    return qual


class CIMInstanceName(_CIMComparisonMixin):
    """
    A CIM instance path (aka *CIM instance name*).

    A CIM instance path references a CIM instance in a CIM namespace in a WBEM
    server. Namespace and WBEM server may be unspecified.

    Two objects of this class compare equal if their public attributes compare
    equal. Objects of this class are :term:`unchanged-hashable`, with the hash
    value being based on its public attributes. Therefore, objects of this
    class can be used as members in a set (or as dictionary keys) only during
    periods in which their public attributes remain unchanged.
    """

    def __init__(self, classname, keybindings=None, host=None, namespace=None):
        # pylint: disable=line-too-long
        """
        Parameters:

          classname (:term:`string`):
            Name of the creation class of the referenced instance.

            Must not be `None`.

            The lexical case of the string is preserved. Object comparison and
            hash value calculation are performed case-insensitively.

          keybindings (:term:`keybindings input object`):
            Keybindings for the instance path (that is, the key property values
            of the referenced instance).

          host (:term:`string`):
            Host and optionally port of the WBEM server containing the CIM
            namespace of the referenced instance.

            The format of the string must be:

            ``host[:port]``

            The host can be specified in any of the usual formats:

            * a short or fully qualified DNS hostname
            * a literal (= dotted) IPv4 address
            * a literal IPv6 address, formatted as defined in :term:`RFC3986`
              with the extensions for zone identifiers as defined in
              :term:`RFC6874`, supporting ``-`` (minus) for the delimiter
              before the zone ID string, as an additional choice to ``%25``.

            `None` means that the WBEM server is unspecified, and the
            :attr:`~pywbem.CIMInstanceName.host` attribute
            will also be `None`.

            The lexical case of the string is preserved. Object comparison and
            hash value calculation are performed case-insensitively.

          namespace (:term:`string`):
            Name of the CIM namespace containing the referenced instance.

            `None` means that the namespace is unspecified, and the
            :attr:`~pywbem.CIMInstanceName.namespace` attribute
            will also be `None`.

            Leading and trailing slash characters will be stripped.
            The lexical case of the string is preserved. Object comparison and
            hash value calculation are performed case-insensitively.

        Raises:

          ValueError: An error in the provided argument values.
          ValueError: A keybinding value is `None` and the config variable
            IGNORE_NULL_KEY_VALUE is `False`
          TypeError: An error in the provided argument types.
        """  # noqa: E501

        # We use the respective setter methods:
        self.classname = classname
        self.keybindings = keybindings
        self.namespace = namespace
        self.host = host

    @property
    def classname(self):
        """
        :term:`unicode string`: Class name of this CIM instance path,
        identifying the creation class of the referenced instance.

        Will not be `None`.

        This attribute is settable. For details, see the description of the
        same-named init parameter of
        :class:`this class <pywbem.CIMInstanceName>`.
        """
        return self._classname

    @classname.setter
    def classname(self, classname):
        """Setter method; for a description see the getter method."""

        # pylint: disable=attribute-defined-outside-init
        self._classname = _ensure_unicode(classname)

        # We perform this check after the initialization to avoid errors
        # in test tools that show the object with repr().
        if classname is None:
            raise ValueError("Class name in instance path must not be None")

    @property
    def keybindings(self):
        """
        `NocaseDict`_: Keybindings of this CIM instance path,
        identifying the key properties of the referenced instance.

        Will not be `None`.

        Each dictionary item specifies one keybinding, with:

        * key (:term:`unicode string`): Keybinding name. Its lexical case was
          preserved.

        * value (:term:`CIM data type` or :term:`number`): Keybinding value.
          If the config variable IGNORE_NULL_KEY_VALUE is True, `None` is
          allowed as a key value.

        The order of keybindings in the instance path is preserved.

        The keybinding name may be `None` in objects of this class that are
        created by pywbem, in the special case a WBEM server has returned an
        instance path with an unnamed keybinding (i.e. a KEYVALUE or
        VALUE.REFERENCE element without a parent KEYBINDINGS element). This is
        allowed as per :term:`DSP0201`. When creating objects of this class, it
        is not allowed to specify unnamed keybindings, i.e. the keybinding name
        must not be `None`.

        This attribute is settable; setting it will cause the current
        keybindings to be replaced with the new keybindings. For details, see
        the description of the same-named init parameter of
        :class:`this class <pywbem.CIMInstanceName>`.

        The keybindings can also be accessed and manipulated one by one
        because the attribute value is a modifiable dictionary. The provided
        input value must be specified as a :term:`CIM data type` or as
        :term:`number`::

            instpath = CIMInstanceName(...)
            v1 = "abc"  # must be a CIM data type or Python number type

            instpath.keybindings['k1'] = v1  # Set "k1" to v1 (add if needed)
            v1 = instpath.keybindings['k1']  # Access value of "k1"
            del instpath.keybindings['k1']  # Delete "k1" from the inst. path

        In addition, the keybindings can be accessed and manipulated one by
        one by using the entire :class:`~pywbem.CIMInstanceName` object like a
        dictionary. Again, the provided input value must be specified as a
        :term:`CIM data type` or as :term:`number`::

            instpath = CIMInstanceName(...)
            v2 = 42  # must be a CIM data type or Python number type

            instpath['k2'] = v2  # Set "k2" to v2 (add if needed)
            v2 = instpath['k2']  # Access value of "k2"
            del instpath['k2']  # Delete "k2" from the instance path
        """
        return self._keybindings

    @keybindings.setter
    def keybindings(self, keybindings):
        """Setter method; for a description see the getter method."""
        # pylint: disable=attribute-defined-outside-init
        self._keybindings = NocaseDict()
        self._keybindings.allow_unnamed_keys = True
        if keybindings:
            try:
                # This is used for iterables:
                iterator = keybindings.items()
            except AttributeError:
                # This is used for dictionaries:
                iterator = keybindings
            for item in iterator:
                if isinstance(item, CIMProperty):
                    key = item.name
                    value = item
                elif isinstance(item, tuple):
                    key, value = item
                else:
                    raise TypeError(
                        _format("Input object for keybindings has invalid "
                                "item in iterable: {0!A}", item))
                if value is None and \
                        config.IGNORE_NULL_KEY_VALUE is False:
                    raise ValueError(
                        _format("CIMInstance keybinding {0!A} key {1!A} value "
                                "value is 'None' which is not allowed unless "
                                "unless 'IGNORE_NULL_KEY_VALUE' is True.",
                                keybindings, key))
                self.keybindings[key] = _cim_keybinding(key, value)

    @property
    def namespace(self):
        """
        :term:`unicode string`: Namespace name of this CIM instance path,
        identifying the namespace of the referenced instance.

        `None` means that the namespace is unspecified.

        This attribute is settable. For details, see the description of the
        same-named init parameter of
        :class:`this class <pywbem.CIMInstanceName>`.
        """
        return self._namespace

    @namespace.setter
    def namespace(self, namespace):
        """Setter method; for a description see the getter method."""
        # pylint: disable=attribute-defined-outside-init
        self._namespace = _ensure_unicode(namespace)
        if self._namespace is not None:
            # In Python 3, a byte string cannot be stripped by a unicode char
            # Therefore, the stripping needs to be done after the unicode
            # conversion.
            self._namespace = self._namespace.strip('/')

    @property
    def host(self):
        """
        :term:`unicode string`: Host and optionally port
        of this CIM instance path,
        identifying the WBEM server of the referenced instance.

        For details about the string format, see the same-named init parameter
        of :class:`this class <pywbem.CIMInstanceName>`.

        `None` means that the host and port are unspecified.

        This attribute is settable. For details, see the description of the
        same-named init parameter.
        """
        return self._host

    @host.setter
    def host(self, host):
        """Setter method; for a description see the getter method."""
        # pylint: disable=attribute-defined-outside-init
        self._host = _ensure_unicode(host)

    def _cmp(self, other):
        """
        Comparator function for two :class:`~pywbem.CIMInstanceName` objects.

        The comparison is based on their public attributes, in descending
        precedence:

        * `host`
        * `namespace`
        * `classname`
        * `keybindings`

        The comparison takes into account any case insensitivities described
        for these attributes.

        Raises `TypeError', if the `other` object is not a
        :class:`~pywbem.CIMInstanceName` object.
        """
        if self is other:
            return 0
        try:
            assert isinstance(other, CIMInstanceName)
        except AssertionError:
            raise TypeError(
                _format("other must be CIMInstanceName, but is: {0}",
                        type(other)))
        return (cmpname(self.host, other.host) or
                cmpname(self.namespace, other.namespace) or
                cmpname(self.classname, other.classname) or
                cmpdict(self.keybindings, other.keybindings))

    def __hash__(self):
        """
        Return a hash value based on the public attributes of this class, taking
        into account any case insensitivities described for these attributes.
        This approach causes this class to be :term:`unchanged-hashable`.
        """
        hashes = (
            _hash_name(self.host),
            _hash_name(self.namespace),
            _hash_name(self.classname),
            _hash_dict(self.keybindings),
        )
        return hash(hashes)

    def __str__(self):
        """
        Return the WBEM URI string of this CIM instance path.

        The returned WBEM URI string is in the historical format returned by
        :meth:`~pywbem.CIMInstanceName.to_wbem_uri`.

        For new code, it is recommended that the standard format is used; it
        is returned by :meth:`~pywbem.CIMInstanceName.to_wbem_uri` as the
        default format.

        Examples (for the historical format):

        * With host and namespace::

            //acme.com/cimv2/test:CIM_RegisteredProfile.InstanceID="acme.1"

        * Without host but with namespace::

            cimv2/test:CIM_RegisteredProfile.InstanceID="acme.1"

        * Without host and without namespace::

            CIM_RegisteredProfile.InstanceID="acme.1"
        """
        return self.to_wbem_uri(format='historical')

    def __repr__(self):
        """
        Return a string representation of this CIM instance path,
        that is suitable for debugging.

        The key bindings will be ordered by their names in the result.
        """

        return _format(
            "CIMInstanceName("
            "classname={s.classname!A}, "
            "keybindings={s.keybindings!A}, "
            "namespace={s.namespace!A}, "
            "host={s.host!A})",
            s=self)

    def __contains__(self, key):
        return key in self.keybindings

    def __getitem__(self, key):
        return self.keybindings[key]

    def __setitem__(self, key, value):
        self.keybindings[key] = value

    def __delitem__(self, key):
        del self.keybindings[key]

    def __len__(self):
        return len(self.keybindings)

    def __iter__(self):
        return six.iterkeys(self.keybindings)

    def copy(self):
        """
        Return a new :class:`~pywbem.CIMInstanceName` object that is a copy
        of this CIM instance path.

        This is a middle-deep copy; any mutable types in attributes except the
        following are copied, so besides these exceptions, modifications of the
        original object will not affect the returned copy, and vice versa. The
        following mutable types are not copied and are therefore shared between
        original and copy:

        * Any mutable object types (see :ref:`CIM data types`) in the
          :attr:`~pywbem.CIMInstanceName.keybindings` dictionary (but not the
          dictionary object itself)

        Note that the Python functions :func:`py:copy.copy` and
        :func:`py:copy.deepcopy` can be used to create completely shallow or
        completely deep copies of objects of this class.
        """
        return CIMInstanceName(
            self.classname,
            keybindings=self.keybindings,  # setter copies
            host=self.host,
            namespace=self.namespace)

    def update(self, *args, **kwargs):
        """
        Update the keybindings of this CIM instance path.

        Existing keybindings will be updated, and new keybindings will be
        added.

        Parameters:

           *args (list):
             Keybindings for updating the keybindings of the instance path,
             specified as positional arguments. Each positional argument must
             be a tuple (key, value), where key and value are described for
             setting the :attr:`~pywbem.CIMInstanceName.keybindings` property.

           **kwargs (dict):
             Keybindings for updating the keybindings of the instance path,
             specified as keyword arguments. The name and value of the keyword
             arguments are described as key and value for setting the
             :attr:`~pywbem.CIMInstanceName.keybindings` property.
        """
        self.keybindings.update(*args, **kwargs)

    def has_key(self, key):
        """
        Return a boolean indicating whether this CIM instance path has a
        particular keybinding.

        Parameters:

          key (:term:`string`):
            Name of the keybinding (in any lexical case).

        Returns:
          :class:`py:bool`: Boolean indicating whether this CIM instance path
          has the keybinding.
        """
        return key in self.keybindings

    def get(self, key, default=None):
        """
        Return the value of a particular keybinding of this CIM instance path,
        or a default value.

        *New in pywbem 0.8.*

        Parameters:

          key (:term:`string`):
            Name of the keybinding (in any lexical case).

          default (:term:`CIM data type`):
            Default value that is returned if a keybinding with the specified
            name does not exist in the instance path.

        Returns:
          :term:`CIM data type`: Value of the keybinding, or the default value.
        """
        return self.keybindings.get(key, default)

    def keys(self):
        """
        Return a copied list of the keybinding names of this CIM instance path.

        The keybinding names have their original lexical case.

        The order of keybindings is preserved.
        """
        return self.keybindings.keys()

    def values(self):
        """
        Return a copied list of the keybinding values
        of this CIM instance path.

        The order of keybindings is preserved.
        """
        return self.keybindings.values()

    def items(self):
        """
        Return a copied list of the keybinding names and values
        of this CIM instance path.

        Each item in the returned list is a tuple of keybinding name (in the
        original lexical case) and keybinding value.

        The order of keybindings is preserved.
        """
        return self.keybindings.items()

    def iterkeys(self):
        """
        Iterate through the keybinding names of this CIM instance path.

        The keybinding names have their original lexical case.

        The order of keybindings is preserved.
        """
        return self.keybindings.iterkeys()

    def itervalues(self):
        """
        Iterate through the keybinding values of this CIM instance path.

        The order of keybindings is preserved.
        """
        return self.keybindings.itervalues()

    def iteritems(self):
        """
        Iterate through the keybinding names and values
        of this CIM instance path.

        Each iteration item is a tuple of the keybinding name (in the original
        lexical case) and the keybinding value.

        The order of keybindings is preserved.
        """
        return self.keybindings.iteritems()

    # pylint: disable=too-many-branches
    def tocimxml(self, ignore_host=False, ignore_namespace=False):
        """
        Return the CIM-XML representation of this CIM instance path,
        as an object of an appropriate subclass of :term:`Element`.

        If the instance path has no namespace specified or if
        `ignore_namespace` is `True`, the returned CIM-XML representation is an
        `INSTANCENAME` element consistent with :term:`DSP0201`.

        Otherwise, if the instance path has no host specified or if
        `ignore_host` is `True`, the returned CIM-XML representation is a
        `LOCALINSTANCEPATH` element consistent with :term:`DSP0201`.

        Otherwise, the returned CIM-XML representation is a
        `INSTANCEPATH` element consistent with :term:`DSP0201`.

        The order of keybindings in the returned CIM-XML representation is
        preserved from the :class:`~pywbem.CIMInstanceName` object.

        Parameters:

          ignore_host (:class:`py:bool`): Ignore the host of the
            instance path, even if a host is specified.

          ignore_namespace (:class:`py:bool`): Ignore the namespace and host of
            the instance path, even if a namespace and/or host is specified.

        Returns:

          The CIM-XML representation, as an object of an appropriate subclass
          of :term:`Element`.
        """

        kbs = []

        # We no longer check that the keybindings is a NocaseDict because we
        # ensure that in the keybindings() property setter method.

        for key, value in self.keybindings.items():

            # Keybindings can be integers, booleans, strings or references.
            # References can only by instance names.

            if isinstance(value, CIMInstanceName):
                kbs.append(cim_xml.KEYBINDING(
                    key, cim_xml.VALUE_REFERENCE(value.tocimxml())))
                continue

            if isinstance(value, six.text_type):
                type_ = 'string'
            elif isinstance(value, six.binary_type):
                type_ = 'string'
                value = _to_unicode(value)
            elif isinstance(value, bool):
                # Note: Bool is a subtype of int, therefore bool is tested
                # before int.
                type_ = 'boolean'
                if value:
                    value = 'TRUE'
                else:
                    value = 'FALSE'
            elif isinstance(value, number_types):
                # Numeric CIM data types derive from Python number types.
                type_ = 'numeric'
                value = str(value)
            else:
                # Double check the type of the keybindings, because they can be
                # set individually.
                raise TypeError(
                    _format("Keybinding {0!A} has invalid type: {1}",
                            key, builtin_type(value)))

            kbs.append(cim_xml.KEYBINDING(
                key, cim_xml.KEYVALUE(value, type_)))

        instancename_xml = cim_xml.INSTANCENAME(self.classname, kbs)

        if self.namespace is None or ignore_namespace:
            return instancename_xml

        localnsp_xml = cim_xml.LOCALNAMESPACEPATH(
            [cim_xml.NAMESPACE(ns)
             for ns in self.namespace.split('/')])

        if self.host is None or ignore_host:
            return cim_xml.LOCALINSTANCEPATH(localnsp_xml, instancename_xml)

        return cim_xml.INSTANCEPATH(
            cim_xml.NAMESPACEPATH(cim_xml.HOST(self.host), localnsp_xml),
            instancename_xml)

    def tocimxmlstr(self, indent=None, ignore_host=False,
                    ignore_namespace=False):
        """
        Return the CIM-XML representation of this CIM instance path,
        as a :term:`unicode string`.

        *New in pywbem 0.9.*

        For the returned CIM-XML representation, see
        :meth:`~pywbem.CIMInstanceName.tocimxml`.

        Parameters:

          indent (:term:`string` or :term:`integer`):
            `None` indicates that a single-line version of the XML should be
            returned, without any whitespace between the XML elements.

            Other values indicate that a prettified, multi-line version of the
            XML should be returned. A string value specifies the indentation
            string to be used for each level of nested XML elements. An integer
            value specifies an indentation string of so many blanks.

          ignore_host (:class:`py:bool`): Ignore the host of the
            instance path, even if a host is specified.

          ignore_namespace (:class:`py:bool`): Ignore the namespace and host of
            the instance path, even if a namespace and/or host is specified.

        Returns:

            The CIM-XML representation of the value, as a
            :term:`unicode string`.
        """
        xml_elem = self.tocimxml(ignore_host, ignore_namespace)
        return tocimxmlstr(xml_elem, indent)

    @staticmethod
    def _kbstr_to_cimval(key, val):
        """
        Convert a keybinding value string as found in a WBEM URI into a
        CIM object or CIM data type, and return it.
        """

        if val[0] == '"' and val[-1] == '"':
            # A double quoted key value. This could be any of these CIM types:
            # * string (see stringValue in DSP00004)
            # * datetime (see datetimeValue in DSP0207)
            # * reference (see referenceValue in DSP0207)

            # Note: The actual definition of referenceValue is missing in
            # DSP0207, see issue #929. Pywbem implements:
            # referenceValue = WBEM-URI-UntypedInstancePath.

            # Note: The definition of stringValue in DSP0004 allows multiple
            # quoted parts (as in MOF), see issue #931. Pywbem implements only
            # a single quoted part.

            # We use slicing instead of strip() for removing the surrounding
            # double quotes, because there could be an escaped double quote
            # before the terminating double quote.
            cimval = val[1:-1]

            # Unescape the backslash-escaped string value
            cimval = re.sub(r'\\(.)', r'\1', cimval)

            # Try all possibilities. Note that this means that string-typed
            # properties that happen to contain a datetime value will be
            # converted to datetime, and string-typed properties that happen to
            # contain a reference value will be converted to a reference.
            # This is a general limitation of untyped WBEM URIs as defined in
            # DSP0207 and cannot be solved by using a different parsing logic.
            try:
                cimval = CIMInstanceName.from_wbem_uri(cimval)
            except ValueError:
                try:
                    cimval = CIMDateTime(cimval)
                except ValueError:
                    cimval = _ensure_unicode(cimval)
            return cimval

        if val[0] == "'" and val[-1] == "'":
            # A single quoted key value. This must be CIM type:
            # * char16 (see charValue in DSP00004)

            # Note: The definition of charValue in DSP0004 allows for integer
            # numbers in addition to single quoted strings, see issue #932.
            # Pywbem implements only single quoted strings.

            cimval = val[1:-1]
            cimval = re.sub(r'\\(.)', r'\1', cimval)
            cimval = _ensure_unicode(cimval)
            if len(cimval) != 1:
                raise ValueError(
                    _format("WBEM URI has a char16 keybinding with an "
                            "incorrect length: {0!A}={1!A}", key, val))
            return cimval

        if val.lower() in ('true', 'false'):
            # The key value must be CIM type:
            # * boolean (see booleanValue in DSP00004)
            cimval = val.lower() == 'true'
            return cimval

        # Try CIM types uint<NN> or sint<NN> (see integerValue in DSP00004).
        # * For integer keybindings in an untyped WBEM URI, it is
        #   not possible to detect the exact CIM data type. Therefore, pywbem
        #   stores the value as a Python int type (or long in Python 2,
        #   if needed).
        cimval = _integerValue_to_int(val)
        if cimval is not None:
            return cimval

        # Try CIM types real32/64 (see realValue in DSP00004).
        # * For real/float keybindings in an untyped WBEM URI, it is not
        #   possible to detect the exact CIM data type. Therefore, pywbem
        #   stores the value as a Python float type.
        cimval = _realValue_to_float(val)
        if cimval is not None:
            return cimval

        # Try datetime types.
        # At this point, all CIM types have been processed, except:
        # * datetime, without quotes (see datetimeValue in DSP0207)
        # DSP0207 requires double quotes around datetime strings, but because
        # earlier versions of pywbem supported them without double quotes,
        # pywbem continues to support that, but issues a warning.
        try:
            cimval = CIMDateTime(val)
        except ValueError:
            raise ValueError(
                _format("WBEM URI has invalid value format in a keybinding: "
                        "{0!A}={1!A}", key, val))

        warnings.warn(
            _format("Tolerating datetime value without surrounding double "
                    "quotes in WBEM URI keybinding: {0!A}={1!A}", key, val),
            UserWarning)
        return cimval

    @staticmethod
    def from_wbem_uri(wbem_uri):
        # pylint: disable=line-too-long
        """
        Return a new :class:`~pywbem.CIMInstanceName` object from the specified
        WBEM URI string.

        *New in pywbem 0.12.*

        The WBEM URI string must be a CIM instance path in untyped WBEM URI
        format, as defined in :term:`DSP0207`, with these extensions:

        * :term:`DSP0207` restricts the namespace types (URI schemes) to be one
          of ``http``, ``https``, ``cimxml-wbem``, or ``cimxml-wbems``. Pywbem
          tolerates any namespace type, but issues a
          :exc:`~py:exceptions.UserWarning` if it is not one of
          the namespace types defined in :term:`DSP0207`.

        * :term:`DSP0207` requires a slash before the namespace name. For local
          WBEM URIs (no namespace type, no authority), that slash is the first
          character of the WBEM URI. For historical reasons, pywbem tolerates a
          missing leading slash for local WBEM URIs. Note that pywbem requires
          the slash (consistent with :term:`DSP0207`) when the WBEM URI is not
          local.

        * :term:`DSP0207` requires a colon before the class name. For
          historical reasons, pywbem tolerates a missing colon before the class
          name, if it would have been the first character of the string.

        * :term:`DSP0207` requires datetime values in keybindings to be
          surrounded by double quotes. For historical reasons, pywbem tolerates
          datetime values that are not surrounded by double quotes, but issues
          a :exc:`~py:exceptions.UserWarning`.

        * :term:`DSP0207` does not allow the special float values INF, -INF,
          and NaN in WBEM URIs (according to realValue in :term:`DSP0004`).
          However, the CIM-XML protocol supports representation of these
          special values, so to be on the safe side, pywbem supports these
          special values as keybindings in WBEM URIs.

        Keybindings that are references are supported, recursively.

        CIM instance paths in the typed WBEM URI format defined in
        :term:`DSP0207` are not supported.

        The untyped WBEM URI format defined in :term:`DSP0207` has the
        following limitations when interpreting a WBEM URI string:

        * It cannot distinguish string-typed keys with a value that is a
          datetime value from datetime-typed keys with such a value. Pywbem
          treats such values as datetime-typed keys.

        * It cannot distinguish string-typed keys with a value that is a
          WBEM URI from reference-typed keys with such a value. Pywbem
          treats such values as reference-typed keys.

        Examples::

            https://jdd:test@acme.com:5989/cimv2/test:CIM_RegisteredProfile.InstanceID="acme.1"
            //jdd:test@acme.com:5989/cimv2/test:CIM_RegisteredProfile.InstanceID="acme.1"
            /cimv2/test:CIM_RegisteredProfile.InstanceID="acme.1"
            cimv2/test:CIM_RegisteredProfile.InstanceID="acme.1"
            /:CIM_RegisteredProfile.InstanceID="acme.1"
            :CIM_RegisteredProfile.InstanceID="acme.1"
            CIM_RegisteredProfile.InstanceID="acme.1"
            http://acme.com/root/cimv2:CIM_ComputerSystem.CreationClassName="ACME_CS",Name="sys1"
            /:CIM_SubProfile.Main="/:CIM_RegisteredProfile.InstanceID=\"acme.1\"",Sub="/:CIM_RegisteredProfile.InstanceID=\"acme.2\""

        Parameters:

          wbem_uri (:term:`string`):
            WBEM URI for an instance path.

        Returns:

          :class:`~pywbem.CIMInstanceName`: The instance path created from the
          specified WBEM URI string.

        Raises:

          ValueError: Invalid WBEM URI format for an instance path. This
            includes typed WBEM URIs.
        """

        m = WBEM_URI_INSTANCEPATH_REGEXP.match(wbem_uri)
        if m is None:
            raise ValueError(
                _format("Invalid format for an instance path in WBEM URI: "
                        "{0!A}", wbem_uri))

        ns_type = m.group(1) or None
        if ns_type and ns_type.lower() not in WBEM_URI_NAMESPACE_TYPES:
            warnings.warn(
                _format("Tolerating unknown namespace type in WBEM URI: {0!A}",
                        wbem_uri),
                UserWarning)

        host = m.group(2) or None
        namespace = m.group(3) or None
        classname = m.group(4) or None
        assert classname is not None  # should be ensured by regexp
        keybindings_str = m.group(5) or None

        m = WBEM_URI_KEYBINDINGS_REGEXP.match(keybindings_str)
        if m is None:
            raise ValueError(
                _format("WBEM URI has an invalid format for its keybindings: "
                        "{0!A}", keybindings_str))

        if m.group(1):
            kb_assigns = [m.group(1)]

        if m.group(2):
            for s in WBEM_URI_KB_FINDALL_REGEXP.findall(m.group(2)):
                if s[0] == ',':
                    s = s[1:]
                kb_assigns.append(s)

        keybindings = {}
        for kb_assign in kb_assigns:
            key, sep, val = _partition(kb_assign, '=')

            # the regexp ensures that it's there:
            assert sep, \
                _format("separator missing in kb_assign: {0!A}", kb_assign)

            keybindings[key] = CIMInstanceName._kbstr_to_cimval(key, val)

        obj = CIMInstanceName(
            classname=classname,
            host=host,
            namespace=namespace,
            keybindings=keybindings)

        return obj

    def to_wbem_uri(self, format='standard'):
        # pylint: disable=redefined-builtin
        """
        Return the (untyped) WBEM URI string of this CIM instance path.

        The returned WBEM URI contains its components as follows:

        * it does not contain a namespace type (URI scheme).
        * it contains an authority (host) component according to the
          :attr:`~pywbem.CIMInstanceName.host` attribute, if that is not
          `None`. Otherwise, it does not contain the authority component.
        * it contains a namespace component according to the
          :attr:`~pywbem.CIMInstanceName.namespace` attribute, if that is not
          `None`. Otherwise, it does not contain the namespace component.
        * it contains a class name component according to the
          :attr:`~pywbem.CIMInstanceName.classname` attribute.
        * it contains keybindings according to the
          :attr:`~pywbem.CIMInstanceName.keybindings` attribute, with the
          order of keybindings preserved, and the lexical case of keybinding
          names preserved (except when using the format "canonical").

        Note that when you do not want some of these components to show up
        in the resulting WBEM URI string, you can set them to `None` before
        calling this method.

        Except when using the format "canonical", this method should not be
        used to compare instance paths for equality: :term:`DSP0004` defines
        defines several components of an instance path to be compared case
        insensitively, including the names of keybindings. In addition, it
        defines that the order of keybindings in instance paths does not matter
        for the comparison. All WBEM URI formats returned by this method except
        for the format "canonical" return a WBEM URI string that preserves the
        order of keybindings (relative to how the keybindings were first added
        to the :class:`~pywbem.CIMInstanceName` object) and that preserves the
        lexical case of any components. Therefore, two instance paths that are
        considered equal according to :term:`DSP0004` may not have equal WBEM
        URI strings as returned by this method.

        Instead, equality of instance paths represented by
        :class:`~pywbem.CIMInstanceName` objects should be determined by using
        the ``==`` operator, which performs the comparison conformant to
        :term:`DSP0004`. If you have WBEM URI strings without the
        corresponding :class:`~pywbem.CIMInstanceName` object, such an object
        can be created by using the static method
        :meth:`~pywbem.CIMInstanceName.from_wbem_uri`.

        Parameters:

          format (:term:`string`): Format for the generated WBEM URI string,
            using one of the following values:

            * ``"standard"`` - Standard format that is conformant to untyped
              WBEM URIs for instance paths defined in :term:`DSP0207`.

            * ``"canonical"`` - Like ``"standard"``, except that the following
              items have been converted to lower case: host, namespace,
              classname, and the names of any keybindings, and except that the
              order of keybindings is in lexical order of the (lower-cased)
              keybinding names.
              This format guarantees that two instance paths that are
              considered equal according to :term:`DSP0004` result in equal
              WBEM URI strings. Therefore, the returned WBEM URI is suitable to
              be used as a key in dictionaries of CIM instances.

            * ``"cimobject"`` - Format for the `CIMObject` header field in
              CIM-XML messages for representing instance paths (used
              internally, see :term:`DSP0200`).

            * ``"historical"`` - Historical format for WBEM URIs (used by
              :meth:`~pywbem.CIMInstanceName.__str__`; should not be used by
              new code). The historical format has the following differences to
              the standard format:

              - If the host component is not present, the slash after the
                host is also omitted. In the standard format, that slash
                is always present.

              - If the namespace component is not present, the colon after the
                namespace is also omitted. In the standard format, that colon
                is always present.

            Keybindings that are references use the specified format
            recursively.

        Examples:

        * With host and namespace, standard format::

            //ACME.com/cimv2/Test:CIM_RegisteredProfile.InstanceID="Acme.1"

        * With host and namespace, canonical format::

            //acme.com/cimv2/test:cim_registeredprofile.instanceid="Acme.1"

        * Without host but with namespace, standard format::

            /cimv2/Test:CIM_RegisteredProfile.InstanceID="Acme.1"

        * Without host but with namespace, canonical format::

            /cimv2/test:cim_registeredprofile.instanceid="Acme.1"

        * Without host and without namespace, standard format::

            /:CIM_RegisteredProfile.InstanceID="Acme.1"

        Returns:

          :term:`unicode string`: Untyped WBEM URI of the CIM instance path,
          in the specified format.

        Raises:

          TypeError: Invalid type in keybindings
          ValueError: Invalid format
        """

        ret = []

        def case(str_):
            """Return the string in the correct lexical case for the format."""
            if format == 'canonical':
                str_ = str_.lower()
            return str_

        def case_sorted(keys):
            """Return the keys in the correct order for the format."""
            if format == 'canonical':
                case_keys = [case(k) for k in keys]
                keys = sorted(case_keys)
            return keys

        if format not in ('standard', 'canonical', 'cimobject', 'historical'):
            raise ValueError(
                _format("Invalid format argument: {0}", format))

        if self.host is not None and format != 'cimobject':
            # The CIMObject format assumes there is no host component
            ret.append('//')
            ret.append(case(self.host))

        if self.host is not None or format not in ('cimobject', 'historical'):
            ret.append('/')

        if self.namespace is not None:
            ret.append(case(self.namespace))

        if self.namespace is not None or format != 'historical':
            ret.append(':')

        ret.append(case(self.classname))

        ret.append('.')

        for key in case_sorted(self.keybindings.iterkeys()):
            value = self.keybindings[key]

            ret.append(key)
            ret.append('=')

            if isinstance(value, six.string_types):
                # string, char16
                ret.append('"')
                ret.append(value.
                           replace('\\', '\\\\').
                           replace('"', '\\"'))
                ret.append('"')
            elif isinstance(value, bool):
                # boolean
                # Note that in Python a bool is an int, so test for bool first
                ret.append(str(value).upper())
            elif isinstance(value, (CIMFloat, float)):
                # realNN
                # Since Python 2.7 and Python 3.1, repr() prints float numbers
                # with the shortest representation that does not change its
                # value. When needed, it shows up to 17 significant digits,
                # which is the precision needed to round-trip double precision
                # IEE-754 floating point numbers between decimal and binary
                # without loss.
                ret.append(repr(value))
            elif isinstance(value, (CIMInt, int, _Longint)):
                # intNN
                ret.append(str(value))
            elif isinstance(value, CIMInstanceName):
                # reference
                ret.append('"')
                ret.append(value.to_wbem_uri(format=format).
                           replace('\\', '\\\\').
                           replace('"', '\\"'))
                ret.append('"')
            elif isinstance(value, CIMDateTime):
                # datetime
                ret.append('"')
                ret.append(str(value))
                ret.append('"')
            else:
                raise TypeError(
                    _format("Invalid type {0} in keybinding value: {1!A}={2!A}",
                            type(value), key, value))
            ret.append(',')

        del ret[-1]

        return _ensure_unicode(''.join(ret))

    @staticmethod
    def from_instance(class_, instance, namespace=None, host=None,
                      strict=False):
        """
        Return a new :class:`~pywbem.CIMInstanceName` object from the key
        property values in a CIM instance and the key property definitions in a
        CIM class.

        If the `strict` parameter is `False`, and a property value does not
        exist in the `instance` that entry is not included in the constructed
        CIMInstanceName

        If the `strict` parameter is `True` all key properties in the `class_`
        must exist in the `instance` or a ValueError exception is raised.

        Parameters:

            `class_` (:class:`~pywbem.CIMClass`):
                The CIM class with the key properties.

                In strict mode, that class  and the instance must contain all
                key properties that are required to create the
                :class:`~pywbem.CIMInstanceName` object. Thus, for example, if
                the class were retrieved from a server, generally, the
                `LocalOnly` parameter in the request should be `False` to
                assure that superclass properties are retrieved and
                `IncludeQualifiers` parameter should be set to `True` to assure
                that qualifiers are retrieved.

                In non-strict mode, that class and instance may have missing
                key properties. Any missing key properties will result in
                missing key bindings in the created
                :class:`~pywbem.CIMInstanceName` object.

                The specified class does not need to be the creation class of
                the instance. Thus, it could be a superclass as long as it has
                the required key properties.

            instance (:class:`~pywbem.CIMInstance`):
                The CIM instance with the key property values.

            namespace (:term:`string`):
                Namespace to include in the created
                :class:`~pywbem.CIMInstanceName` or `None`.

            host (:term:`string`):
                Host name to include in created
                :class:`~pywbem.CIMInstanceName` or `None`.

            strict (:class:`py:bool`):
                Strict mode (see description of `class_` parameter).

        Returns:

            :class:`~pywbem.CIMInstanceName`:
                :class:`~pywbem.CIMInstanceName` built from the key properties
                in the `class_` parameter using the key property values in the
                `instance` parameter.

        Raises:

          ValueError: The `strict` attribute is `True` and a key property does
            not exist in the instance.
        """
        keybindings = NocaseDict()

        for prop in class_.properties:
            if 'key' in class_.properties[prop].qualifiers:
                pname = class_.properties[prop].name  # get original name

                if prop in instance:
                    keybindings[pname] = instance[prop]
                else:
                    if strict:
                        raise ValueError(
                            _format("Key property {0!A} of class {1!A} missing "
                                    "in instance.", pname, class_.classname))

        return CIMInstanceName(class_.classname,
                               keybindings,
                               namespace=namespace,
                               host=host)


class CIMInstance(_CIMComparisonMixin):
    """
    A representation of a CIM instance in a CIM namespace in a WBEM server,
    optionally including its instance path.

    Two objects of this class compare equal if their public attributes compare
    equal. Objects of this class are :term:`unchanged-hashable`, with the hash
    value being based on its public attributes. Therefore, objects of this
    class can be used as members in a set (or as dictionary keys) only during
    periods in which their public attributes remain unchanged.
    """

    # pylint: disable=too-many-arguments
    def __init__(self, classname, properties=None, qualifiers=None,
                 path=None, property_list=None):
        """
        Parameters:

          classname (:term:`string`):
            Name of the creation class for the instance.

            Must not be `None`.

            The lexical case of the string is preserved. Object comparison and
            hash value calculation are performed case-insensitively.

          properties (:term:`properties input object`):
            The property values for the instance.

            If the specified path has keybindings that correspond to these
            properties, the values of these keybindings will be updated to
            match the property values.

          qualifiers (:term:`qualifiers input object`):
            The qualifiers for the instance.

            Note that :term:`DSP0200` has deprecated the presence of qualifiers
            on CIM instances.

          path (:class:`~pywbem.CIMInstanceName`):
            Instance path for the instance.

            The provided object will be copied before being stored in the
            :class:`~pywbem.CIMInstance` object.

            If this path has keybindings that correspond to the specified
            properties, the values of the keybindings in (the copy of) this
            path will be updated to match the property values.

            `None` means that the instance path is unspecified, and the
            :attr:`~pywbem.CIMInstance.path` attribute
            will also be `None`.

          property_list (:term:`py:iterable` of :term:`string`):
            **Deprecated:** List of property names for use as a filter by some
            operations on the instance.

            This parameter has been deprecated in pywbem 0.12.
            Set only the desired properties on the object, instead of
            working with this property filter.

            The property names may have any lexical case.

            A copy of the provided iterable will be stored in the
            :class:`~pywbem.CIMInstance` object, and the property names will be
            converted to lower case.

            `None` means that the properties are not filtered, and the
            :attr:`~pywbem.CIMInstance.property_list` attribute
            will also be `None`.

        Raises:

          ValueError: classname is `None`, a property or qualifier name is
            `None`, or a property or qualifier name does not match its
            dictionary key.
          TypeError: a numeric Python type was used for a property or qualifier
            value.
        """

        # We use the respective setter methods:
        self.classname = classname
        self.path = path
        self.property_list = property_list
        self.properties = properties  # Depends on path & property_list set
        self.qualifiers = qualifiers

    @property
    def classname(self):
        """
        :term:`unicode string`: Name of the creation class
        of this CIM instance.

        Will not be `None`.

        This attribute is settable. For details, see the description of the
        same-named init parameter of
        :class:`this class <pywbem.CIMInstance>`.
        """
        return self._classname

    @classname.setter
    def classname(self, classname):
        """Setter method; for a description see the getter method."""

        # pylint: disable=attribute-defined-outside-init
        self._classname = _ensure_unicode(classname)

        # We perform this check after the initialization to avoid errors
        # in test tools that show the object with repr().
        if classname is None:
            raise ValueError("Class name in instance must not be None")

    @property
    def properties(self):
        """
        `NocaseDict`_: Properties of this CIM instance.

        Will not be `None`.

        Each dictionary item specifies one property value, with:

        * key (:term:`unicode string`): Property name. Its lexical case was
          preserved.

        * value (:class:`~pywbem.CIMProperty`): Property value.

        The order of properties in the CIM instance is preserved.

        This attribute is settable; setting it will cause the current CIM
        properties to be replaced with the new properties, and will also cause
        the values of corresponding keybindings in the instance path (if set)
        to be updated. For details, see the description of the same-named
        init parameter. Note that the property value may be specified as
        a :term:`CIM data type` or as a :class:`~pywbem.CIMProperty` object.

        The CIM property values can also be accessed and manipulated one by one
        because the attribute value is a modifiable dictionary. In that case,
        the provided input value must be a :class:`~pywbem.CIMProperty`
        object. A corresponding keybinding in the instance path (if set) will
        not (!) be updated in this case::

            inst = CIMInstance(...)
            p1 = CIMProperty('p1', ...)  # must be CIMProperty

            inst.properties['p1'] = p1  # Set "p1" to p1 (add if needed)
            p1 = inst.properties['p1']  # Access "p1"
            del inst.properties['p1']  # Delete "p1" from the instance

        In addition, the CIM properties can be accessed and manipulated one by
        one by using the entire :class:`~pywbem.CIMInstance` object like a
        dictionary. In that case, the provided input value may be specified as
        a :term:`CIM data type` or as a :class:`~pywbem.CIMProperty` object.
        The value of a corresponding keybinding in the instance path (if set)
        will be updated to the new property value::

            inst = CIMInstance(...)
            p2 = Uint32(...)  # may be CIM data type or CIMProperty

            inst['p2'] = p2  # Set "p2" to p2 (add if needed)
            p2 = inst['p2']  # Access "p2"
            del inst['p2']  # Delete "p2" from the instance
        """
        return self._properties

    @properties.setter
    def properties(self, properties):
        """Setter method; for a description see the getter method."""
        # We make sure that the dictionary is a NocaseDict object, and that the
        # property values are CIMProperty objects:
        # pylint: disable=attribute-defined-outside-init
        self._properties = NocaseDict()
        if properties:
            try:
                # This is used for iterables:
                iterator = properties.items()
            except AttributeError:
                # This is used for dictionaries:
                iterator = properties
            for item in iterator:
                if isinstance(item, CIMProperty):
                    key = item.name
                    value = item
                elif isinstance(item, tuple):
                    key, value = item
                else:
                    raise TypeError(
                        _format("Input object for properties has invalid item "
                                "in iterable: {0!A}", item))
                self.__setitem__(key, value)

    @property
    def qualifiers(self):
        """
        `NocaseDict`_: Qualifiers (qualifier values) of this CIM instance.

        Will not be `None`.

        Each dictionary item specifies one qualifier value, with:

        * key (:term:`unicode string`): Qualifier name. Its lexical case was
          preserved.

        * value (:class:`~pywbem.CIMQualifier`): Qualifier value.

        The order of qualifiers in the CIM instance is preserved.

        This attribute is settable; setting it will cause the current
        qualifiers to be replaced with the new qualifiers. For details, see
        the description of the same-named init parameter of
        :class:`this class <pywbem.CIMInstance>`.

        The qualifier values can also be accessed and manipulated one by one
        because the attribute value is a modifiable dictionary.

        Note that :term:`DSP0200` has deprecated the presence of qualifier
        values on CIM instances.
        """
        return self._qualifiers

    @qualifiers.setter
    def qualifiers(self, qualifiers):
        """Setter method; for a description see the getter method."""
        # We make sure that the dictionary is a NocaseDict object, and that the
        # property values are CIMQualifier objects:
        # pylint: disable=attribute-defined-outside-init
        self._qualifiers = NocaseDict()
        if qualifiers:
            try:
                # This is used for iterables:
                iterator = qualifiers.items()
            except AttributeError:
                # This is used for dictionaries:
                iterator = qualifiers
            for item in iterator:
                if isinstance(item, CIMQualifier):
                    key = item.name
                    value = item
                elif isinstance(item, tuple):
                    key, value = item
                else:
                    raise TypeError(
                        _format("Input object for qualifiers has invalid item "
                                "in iterable: {0!A}", item))
                self.qualifiers[key] = _cim_qualifier(key, value)

    @property
    def path(self):
        """
        :class:`~pywbem.CIMInstanceName`: Instance path of this CIM instance.

        `None` means that the instance path is unspecified.

        This attribute is settable. For details, see the description of the
        same-named init parameter of
        :class:`this class <pywbem.CIMInstance>`.
        """
        return self._path

    @path.setter
    def path(self, path):
        """Setter method; for a description see the getter method."""

        # pylint: disable=attribute-defined-outside-init
        if path is None:
            self._path = None
        else:
            # The provided path is deep copied because its keybindings may be
            # updated when setting properties (in __setitem__()).
            self._path = path.copy()

            # We perform this check after the initialization to avoid errors
            # in test tools that show the object with repr().
            assert isinstance(path, CIMInstanceName)

    @property
    def property_list(self):
        """
        :term:`py:list` of :term:`unicode string`: **Deprecated:** List of
        property names for use as a filter by some operations on
        this CIM instance.

        This attribute has been deprecated in pywbem 0.12.
        Set only the desired properties on the object, instead of working with
        this property filter.

        The property names are specified in lower case.

        `None` means that the properties are not filtered.

        This attribute is settable. For details, see the description of the
        same-named init parameter of
        :class:`this class <pywbem.CIMInstance>`.
        """
        return self._property_list

    @property_list.setter
    def property_list(self, property_list):
        """Setter method; for a description see the getter method."""
        if property_list is not None:
            msg = "The 'property_list' init parameter and attribute of " \
                "CIMInstance is deprecated; Set only the desired properties " \
                "instead."
            if DEBUG_WARNING_ORIGIN:
                msg += "\nTraceback:\n" + ''.join(traceback.format_stack())
            warnings.warn(msg, DeprecationWarning,
                          stacklevel=_stacklevel_above_module(__name__))

            property_list = [_ensure_unicode(x).lower()
                             for x in property_list]
        # pylint: disable=attribute-defined-outside-init
        self._property_list = property_list

    def _cmp(self, other):
        """
        Comparator function for two :class:`~pywbem.CIMInstance` objects.

        The comparison is based on some of their public attributes, in
        descending precedence:

        * `classname`
        * `path`
        * `properties`
        * `qualifiers`

        The comparison takes into account any case insensitivities described
        for these attributes.

        The following public attributes are not utilized for the comparison:

        * `property_list`
        """
        if self is other:
            return 0
        try:
            assert isinstance(other, CIMInstance)
        except AssertionError:
            raise TypeError(
                _format("other must be CIMInstance, but is: {0}",
                        type(other)))
        return (cmpname(self.classname, other.classname) or
                cmpitem(self.path, other.path) or
                cmpdict(self.properties, other.properties) or
                cmpdict(self.qualifiers, other.qualifiers))

    def __hash__(self):
        """
        Return a hash value based on the same public attributes of this class
        as used for equality comparison, taking into account any case
        insensitivities described for these attributes.
        This approach causes this class to be :term:`unchanged-hashable`.
        """
        hashes = (
            _hash_name(self.classname),
            _hash_item(self.path),
            _hash_dict(self.properties),
            _hash_dict(self.qualifiers),
        )
        return hash(hashes)

    def __str__(self):
        """
        Return a short string representation of this CIM instance,
        for human consumption.
        """
        return _format(
            "CIMInstance("
            "classname={s.classname!A}, "
            "path={s.path!A}, ...)",
            s=self)

    def __repr__(self):
        """
        Return a string representation of this CIM instance,
        that is suitable for debugging.

        The properties and qualifiers will be ordered by their names in the
        result.
        """
        return _format(
            "CIMInstance("
            "classname={s.classname!A}, "
            "path={s.path!A}, "
            "properties={s.properties!A}, "
            "property_list={s.property_list!A}, "
            "qualifiers={s.qualifiers!A})",
            s=self)

    def __contains__(self, key):
        return key in self.properties

    def __getitem__(self, key):
        return self.properties[key].value

    def __setitem__(self, key, value):

        # The property_list attribute has been deprecated in pywbem 0.12.
        # It is used to ignore the setting of properties under certain
        # conditions. Note that the purpose of these conditions is unclear,
        # given the code below (whose logic is unchanged since at least as far
        # back as pywbem 0.7): For instances that do not have a path set,
        # the property_list is effectively disabled. Nevertheless, the logic
        # has been kept in place because the property_list feature may be
        # removed anyway in a future release of pywbem.
        if self.property_list is not None and \
                key.lower() not in self.property_list and \
                self.path is not None and \
                key not in self.path.keybindings:
            return

        prop = _cim_property_value(key, value)
        self.properties[key] = prop
        if self.path is not None and key in self.path.keybindings:
            self.path[key] = prop.value

    def __delitem__(self, key):
        del self.properties[key]

    def __len__(self):
        return len(self.properties)

    def __iter__(self):
        return six.iterkeys(self.properties)

    def copy(self):
        """
        Return a new :class:`~pywbem.CIMInstance` object that is a copy
        of this CIM instance.

        This is a middle-deep copy; any mutable types in attributes except the
        following are copied, so besides these exceptions, modifications of the
        original object will not affect the returned copy, and vice versa. The
        following mutable types are not copied and are therefore shared between
        original and copy:

        * The :class:`~pywbem.CIMProperty` objects in the
          :attr:`~pywbem.CIMInstance.properties` dictionary (but not the
          dictionary object itself)
        * The :class:`~pywbem.CIMQualifier` objects in the
          :attr:`~pywbem.CIMInstance.qualifiers` dictionary (but not the
          dictionary object itself)

        Note that the Python functions :func:`py:copy.copy` and
        :func:`py:copy.deepcopy` can be used to create completely shallow or
        completely deep copies of objects of this class.
        """
        result = CIMInstance(
            self.classname,
            properties=self.properties,  # setter copies
            qualifiers=self.qualifiers)  # setter copies

        # The path is set after the init method, because the init method
        # would overwrite the values of keybindings that have corresponding
        # properties. In order to be consistent with the behavior of the
        # original version of pywbem (0.7.0), this copy() method preserves
        # the provided input path.
        result.path = self.path  # setter copies deep

        return result

    def update(self, *args, **kwargs):
        """
        Update the properties of this CIM instance.

        Existing properties will be updated, and new properties will be added.

        Parameters:

           *args (list):
             Properties for updating the properties of the instance, specified
             as positional arguments. Each positional argument must be a tuple
             (key, value), where key and value are described for setting the
             :attr:`~pywbem.CIMInstance.properties` property.

           **kwargs (dict):
             Properties for updating the properties of the instance, specified
             as keyword arguments. The name and value of the keyword arguments
             are described as key and value for setting the
             :attr:`~pywbem.CIMInstance.properties` property.
        """

        for mapping in args:
            if hasattr(mapping, 'items'):
                for key, value in mapping.items():
                    self[key] = value
            else:
                for (key, value) in mapping:
                    self[key] = value
        for key, value in kwargs.items():
            self[key] = value

    def update_existing(self, *args, **kwargs):
        """
        Update already existing properties of this CIM instance.

        Existing properties will be updated, and new properties will be
        ignored without further notice.

        Parameters:

           *args (list):
             Properties for updating the properties of the instance, specified
             as positional arguments. Each positional argument must be a tuple
             (key, value), where key and value are described for setting the
             :attr:`~pywbem.CIMInstance.properties` property.

           **kwargs (dict):
             Properties for updating the properties of the instance, specified
             as keyword arguments. The name and value of the keyword arguments
             are described as key and value for setting the
             :attr:`~pywbem.CIMInstance.properties` property.
        """

        for mapping in args:
            if hasattr(mapping, 'items'):
                for key, value in mapping.items():
                    try:
                        prop = self.properties[key]
                    except KeyError:
                        continue
                    prop.value = value
            else:
                for (key, value) in mapping:
                    try:
                        prop = self.properties[key]
                    except KeyError:
                        continue
                    prop.value = value
        for key, value in kwargs.items():
            try:
                prop = self.properties[key]
            except KeyError:
                continue
            prop.value = value

    def has_key(self, key):
        """
        Return a boolean indicating whether this CIM instance has a particular
        property.

        Parameters:

          key (:term:`string`):
            Name of the property (in any lexical case).

        Returns:
          :class:`py:bool`: Boolean indicating whether the instance has the
          property.
        """
        return key in self.properties

    def get(self, key, default=None):
        """
        Return the value of a particular property of this CIM instance,
        or a default value.

        *New in pywbem 0.8.*

        Parameters:

          key (:term:`string`):
            Name of the property (in any lexical case).

          default (:term:`CIM data type`):
            Default value that is returned if a property with the specified
            name does not exist in the instance.

        Returns:
          :term:`CIM data type`: Value of the property, or the default value.
        """
        prop = self.properties.get(key, None)
        return default if prop is None else prop.value

    def keys(self):
        """
        Return a copied list of the property names of this CIM instance.

        The property names have their original lexical case.

        The order of properties is preserved.
        """
        return self.properties.keys()

    def values(self):
        """
        Return a copied list of the property values of this CIM instance.

        The order of properties is preserved.
        """
        return [v.value for v in self.properties.values()]

    def items(self):
        """
        Return a copied list of the property names and values
        of this CIM instance.

        Each item in the returned list is a tuple of property name (in the
        original lexical case) and property value.

        The order of properties is preserved.
        """
        return [(key, v.value) for key, v in self.properties.items()]

    def iterkeys(self):
        """
        Iterate through the property names of this CIM instance.

        The property names have their original lexical case.

        The order of properties is preserved.
        """
        return self.properties.iterkeys()

    def itervalues(self):
        """
        Iterate through the property values of this CIM instance.

        The order of properties is preserved.
        """
        for _, val in self.properties.iteritems():
            yield val.value

    def iteritems(self):
        """
        Iterate through the property names and values of this CIM instance.

        Each iteration item is a tuple of the property name (in the original
        lexical case) and the property value.

        The order of properties is preserved.
        """
        for key, val in self.properties.iteritems():
            yield (key, val.value)

    def tocimxml(self, ignore_path=False):
        """
        Return the CIM-XML representation of this CIM instance,
        as an object of an appropriate subclass of :term:`Element`.

        If the instance has no instance path specified or if `ignore_path` is
        `True`, the returned CIM-XML representation is an `INSTANCE` element
        consistent with :term:`DSP0201`. This is the required element for
        representing embedded instances.

        Otherwise, if the instance path of the instance has no namespace
        specified, the returned CIM-XML representation is an
        `VALUE.NAMEDINSTANCE` element consistent with :term:`DSP0201`.

        Otherwise, if the instance path of the instance has no host specified,
        the returned CIM-XML representation is a
        `VALUE.OBJECTWITHLOCALPATH` element consistent with :term:`DSP0201`.

        Otherwise, the returned CIM-XML representation is a
        `VALUE.INSTANCEWITHPATH` element consistent with :term:`DSP0201`.

        The order of properties and qualifiers in the returned CIM-XML
        representation is preserved from the :class:`~pywbem.CIMInstance`
        object.

        Parameters:

          ignore_path (:class:`py:bool`): Ignore the path of the instance, even
            if a path is specified.

        Returns:

          The CIM-XML representation, as an object of an appropriate subclass
          of :term:`Element`.
        """

        # The items in the self.properties dictionary are required to be
        # CIMProperty objects and that is ensured when initializing a
        # CIMInstance object and when setting the entire self.properties
        # attribute. However, even though the items in the dictionary are
        # required to be CIMProperty objects, the user technically can set
        # them to anything.
        # Before pywbem 0.12, the dictionary items were converted to
        # CIMProperty objects. This was only done for properties of
        # CIMinstance, but not for any other CIM object attribute.
        # In pywbem 0.12, this conversion was removed because it worked only
        # for bool and string types anyway. Because that conversion had been
        # implemented, we still check that the items are CIMProperty objects.
        for key, value in self.properties.items():
            try:
                assert isinstance(value, CIMProperty)
            except AssertionError:
                raise TypeError(
                    _format("Property {0!A} has invalid type: {1} (must be "
                            "CIMProperty)", key, builtin_type(value)))

        instance_xml = cim_xml.INSTANCE(
            self.classname,
            properties=[p.tocimxml() for p in self.properties.values()],
            qualifiers=[q.tocimxml() for q in self.qualifiers.values()])

        if self.path is None or ignore_path:
            return instance_xml

        if self.path.namespace is None:
            return cim_xml.VALUE_NAMEDINSTANCE(
                self.path.tocimxml(),
                instance_xml)

        if self.path.host is None:
            return cim_xml.VALUE_OBJECTWITHLOCALPATH(
                self.path.tocimxml(),
                instance_xml)

        return cim_xml.VALUE_INSTANCEWITHPATH(
            self.path.tocimxml(),
            instance_xml)

    def tocimxmlstr(self, indent=None, ignore_path=False):
        """
        Return the CIM-XML representation of this CIM instance,
        as a :term:`unicode string`.

        *New in pywbem 0.9.*

        For the returned CIM-XML representation, see
        :meth:`~pywbem.CIMInstance.tocimxml`.

        Parameters:

          indent (:term:`string` or :term:`integer`):
            `None` indicates that a single-line version of the XML should be
            returned, without any whitespace between the XML elements.

            Other values indicate that a prettified, multi-line version of the
            XML should be returned. A string value specifies the indentation
            string to be used for each level of nested XML elements. An integer
            value specifies an indentation string of so many blanks.

          ignore_path (:class:`py:bool`): Ignore the path of the instance, even
            if a path is specified.

        Returns:

            The CIM-XML representation of the object, as a
            :term:`unicode string`.
        """
        xml_elem = self.tocimxml(ignore_path)
        return tocimxmlstr(xml_elem, indent)

    def tomof(self, indent=0, maxline=MAX_MOF_LINE):
        """
        Return a MOF string with the specification of this CIM instance.

        The returned MOF string conforms to the ``instanceDeclaration``
        ABNF rule defined in :term:`DSP0004`, with the following limitations:

        * Pywbem does not support instance aliases, so the returned MOF string
          does not define an alias name for the instance.

        * Even though pywbem supports qualifiers on
          :class:`~pywbem.CIMInstance` objects, and on
          :class:`~pywbem.CIMProperty` objects that are used as property values
          within an instance, the returned MOF string does not contain
          any qualifier values on the instance or on its property values.

        The order of properties and qualifiers is preserved.

        Parameters:

          indent (:term:`integer`): This parameter has been deprecated in
            pywbem 0.12. A value other than 0 causes a deprecation warning to
            be issued. Otherwise, the parameter is ignored and the returned MOF
            instance specification is not indented.

        Returns:

          :term:`unicode string`: MOF string.
        """

        if indent != 0:
            msg = "The 'indent' parameter of CIMInstance.tomof() is " \
                "deprecated."
            if DEBUG_WARNING_ORIGIN:
                msg += "\nTraceback:\n" + ''.join(traceback.format_stack())
            warnings.warn(msg, DeprecationWarning,
                          stacklevel=_stacklevel_above_module(__name__))

        mof = []

        mof.append(u'instance of ')
        mof.append(self.classname)

        mof.append(u' {\n')

        for p in self.properties.itervalues():
            mof.append(p.tomof(True, MOF_INDENT, maxline))

        mof.append(u'};\n')

        return u''.join(mof)

    @staticmethod
    def from_class(klass, namespace=None,
                   property_values=None,
                   include_missing_properties=True,
                   include_path=True, include_class_origin=False):
        """
        Return a new :class:`~pywbem.CIMInstance` object from specified key
        property values and from the key property definitions in a class.

        The properties in the returned instance do not have any qualifiers.

        Parameters:

          klass (:class:`~pywbem.CIMClass`):
            CIMClass from which the instance will be constructed.  This class
            must include qualifiers and should include properties from any
            superclasses in the model insure it includes all properties that
            are to be built into the instance, in particular any key properties
            if the `include+path` parameter is `True`. See
            :meth:`~pywbem.CIMInstanceName.from_class` for further requirements
            on the class.

          namespace (:term:`string`):
            Namespace to be included in the path component of the returned
            CIMInstance if `include_path` parameter is `True`.

          property_values (:class:`py:dict` or `NocaseDict`_):
            Dictionary containing name/value pairs where the names are the
            names of properties in the class and the properties are the
            property values to be set into the instance properties. The values
            must match the type defined for the property in the class. If a
            property is in the property_values dictionary but not in the class
            a ValueError exception is raised. Not all properties in the class
            need to be defined in `property_values`.

          include_missing_properties (:class:`py:bool`):
            Determines if properties not in the `property_values` parameter are
            included in the instance.

            If `True` all properties from the class are included in the new
            instance including those not defined in `property_values` parameter
            with with the default value defined in the class if one is defined,
            or otherwise None".

            If `False` only properties in the `property_values` parameter are
            included in the new instance.

         include_class_origin (:class:`py:bool`):
            Determines if class origin information from the class is included
            in the returned instance.

            If `None` or `False`, class origin information is not included.

            If `True`, class origin information is included.

          include_path (:class:`py:bool`:):
            Controls creation of a path element in the new instance.

            If `True` a :class:`~pywbem.CIMInstanceName` path is created from
            the key properties in the new instance and inserted
            into the new instance based on properties in the new instance.

            All properties with key qualifier in the class defined by the
            `klass` parameter must exist in the new instance and have non-null
            values or the path creation fails with a ValueError exception.

            If `None` or `False` no path element is created and the new
            instance is returned with the path element `None`.

        Returns:

          :class:`~pywbem.CIMInstance`:

            A CIM instance created from `klass` and `property_values`
            parameters with the defined properties and optionally the path
            component set.

            No qualifiers are included in the returned instance and the
            existence of the class origin attribute depends on the
            `include_class_origin` parameter.

            All other attributes of each property are the same as the
            corresponding class property.

        Raises:

           ValueError: Conflicts between the class properties and
           `property_values` parameter or the instance does
           not include all key properties defined in the class.

           TypeError: Mismatch between types of the property values in
           `property_values` parameter and the property type in the
           corresponding class property
        """
        class_name = klass.classname
        inst = CIMInstance(class_name)

        if property_values is None:
            property_values = NocaseDict()
        # if not a NoCaseDict, map the input to NoCaseDict
        if not isinstance(property_values, NocaseDict):
            if isinstance(property_values, dict):
                ncd = NocaseDict()
                ncd.update(property_values)
                property_values = ncd
            else:
                raise TypeError(
                    _format("property_values param must be a dictionary. "
                            "Type is {0}", type(property_values)))
        for pname in property_values:
            if pname not in klass.properties:
                raise ValueError(
                    _format("Property name {0!A} in property_values param but "
                            "not in class {1!A}", pname, class_name))
        for cp in klass.properties.values():
            co = cp.class_origin if include_class_origin else None

            if cp.name in property_values:
                ip = CIMProperty(cp.name, property_values[cp.name],
                                 type=cp.type,
                                 class_origin=co,
                                 array_size=cp.array_size,
                                 propagated=cp.propagated,
                                 is_array=cp.is_array,
                                 reference_class=cp.reference_class,
                                 qualifiers=OrderedDict(),
                                 embedded_object=cp.embedded_object)
                inst[ip.name] = ip
            else:
                if include_missing_properties:
                    cpc = cp.copy()
                    cpc.class_origin = co
                    cpc.qualifiers = OrderedDict()
                    inst[cp.name] = cpc

        if include_path:
            # Uses strict so all key properties in klass must exist in
            # the instance or a ValueError is generated by from_instance
            inst.path = CIMInstanceName.from_instance(klass, inst, namespace,
                                                      strict=True)
        return inst


class CIMClassName(_CIMComparisonMixin):
    """
    A CIM class path (aka *CIM class name*).

    A CIM class path references a CIM class in a CIM namespace in a WBEM
    server. Namespace and WBEM server may be unspecified.

    Two objects of this class compare equal if their public attributes compare
    equal. Objects of this class are :term:`unchanged-hashable`, with the hash
    value being based on its public attributes. Therefore, objects of this
    class can be used as members in a set (or as dictionary keys) only during
    periods in which their public attributes remain unchanged.
    """

    def __init__(self, classname, host=None, namespace=None):
        """
        Parameters:

          classname (:term:`string`):
            Class name of the referenced class.

            Must not be `None`.

            The lexical case of the string is preserved. Object comparison and
            hash value calculation are performed case-insensitively.

          host (:term:`string`):
            Host and optionally port of the WBEM server containing the CIM
            namespace of the referenced class.

            The format of the string must be:

            ``host[:port]``

            The host can be specified in any of the usual formats:

            * a short or fully qualified DNS hostname
            * a literal (= dotted) IPv4 address
            * a literal IPv6 address, formatted as defined in :term:`RFC3986`
              with the extensions for zone identifiers as defined in
              :term:`RFC6874`, supporting ``-`` (minus) for the delimiter
              before the zone ID string, as an additional choice to ``%25``.

            `None` means that the WBEM server is unspecified, and the
            :attr:`~pywbem.CIMClassName.host` attribute
            will also be `None`.

            The lexical case of the string is preserved. Object comparison and
            hash value calculation are performed case-insensitively.

          namespace (:term:`string`):
            Name of the CIM namespace containing the referenced class.

            `None` means that the namespace is unspecified, and the
            :attr:`~pywbem.CIMClassName.namespace` attribute
            will also be `None`.

            Leading and trailing slash characters will be stripped.
            The lexical case of the string is preserved. Object comparison and
            hash value calculation are performed case-insensitively.

        Raises:

          ValueError: classname is `None`.
        """

        # We use the respective setter methods:
        self.classname = classname
        self.namespace = namespace
        self.host = host

    @property
    def classname(self):
        """
        :term:`unicode string`: Class name of this CIM class path,
        identifying the referenced class.

        Will not be `None`.

        This attribute is settable. For details, see the description of the
        same-named init parameter of
        :class:`this class <pywbem.CIMClassName>`.
        """
        return self._classname

    @classname.setter
    def classname(self, classname):
        """Setter method; for a description see the getter method."""

        # DSP0004 defines a certain format of CIM class names, but we don't
        # check that in pywbem because we don't parse the class name anywhere.
        # Also, some WBEM servers implement special classes that deviate from
        # that format.

        # pylint: disable=attribute-defined-outside-init
        self._classname = _ensure_unicode(classname)

        # We perform this check after the initialization to avoid errors
        # in test tools that show the object with repr().
        if classname is None:
            raise ValueError("Class name in class path must not be None")

    @property
    def namespace(self):
        """
        :term:`unicode string`: Namespace name of this CIM class path,
        identifying the namespace of the referenced class.

        `None` means that the namespace is unspecified.

        This attribute is settable. For details, see the description of the
        same-named init parameter of
        :class:`this class <pywbem.CIMClassName>`.
        """
        return self._namespace

    @namespace.setter
    def namespace(self, namespace):
        """Setter method; for a description see the getter method."""
        # pylint: disable=attribute-defined-outside-init
        self._namespace = _ensure_unicode(namespace)
        if self._namespace is not None:
            # In Python 3, a byte string cannot be stripped by a unicode char
            # Therefore, the stripping needs to be done after the unicode
            # conversion.
            self._namespace = self._namespace.strip('/')

    @property
    def host(self):
        """
        :term:`unicode string`: Host and optionally port
        of this CIM class path,
        identifying the WBEM server of the referenced class.

        For details about the string format, see the same-named init parameter
        of :class:`this class <pywbem.CIMClassName>`.

        `None` means that the host and port are unspecified.

        This attribute is settable. For details, see the description of the
        same-named init parameter.
        """
        return self._host

    @host.setter
    def host(self, host):
        """Setter method; for a description see the getter method."""
        # pylint: disable=attribute-defined-outside-init
        self._host = _ensure_unicode(host)

    def copy(self):
        """
        Return a new :class:`~pywbem.CIMClassName` object that is a copy
        of this CIM class path.

        Objects of this class have no mutable types in any attributes, so
        modifications of the original object will not affect the returned copy,
        and vice versa.

        Note that the Python functions :func:`py:copy.copy` and
        :func:`py:copy.deepcopy` can be used to create completely shallow or
        completely deep copies of objects of this class.
        """
        return CIMClassName(
            self.classname,
            host=self.host,
            namespace=self.namespace)

    def _cmp(self, other):
        """
        Comparator function for two :class:`~pywbem.CIMClassName` objects.

        The comparison is based on their public attributes, in descending
        precedence:

        * `host`
        * `namespace`
        * `classname`

        The comparison takes into account any case insensitivities described
        for these attributes.
        """
        if self is other:
            return 0
        try:
            assert isinstance(other, CIMClassName)
        except AssertionError:
            raise TypeError(
                _format("other must be CIMClassName, but is: {0}",
                        type(other)))
        return (cmpname(self.host, other.host) or
                cmpname(self.namespace, other.namespace) or
                cmpname(self.classname, other.classname))

    def __hash__(self):
        """
        Return a hash value based on the public attributes of this class, taking
        into account any case insensitivities described for these attributes.
        This approach causes this class to be :term:`unchanged-hashable`.
        """
        hashes = (
            _hash_name(self.host),
            _hash_name(self.namespace),
            _hash_name(self.classname),
        )
        return hash(hashes)

    def __str__(self):
        """
        Return a WBEM URI string of this CIM class path.

        The returned WBEM URI string is in the historical format returned by
        :meth:`~pywbem.CIMClassName.to_wbem_uri`.

        For new code, it is recommended that the standard format is used; it
        is returned by :meth:`~pywbem.CIMClassName.to_wbem_uri` as the default
        format.

        If you want to access the class name, use the
        :attr:`~pywbem.CIMClassName.classname` attribute, instead of relying
        on the coincidence that the historical format of a WBEM URI without
        host and namespace happens to be the class name.

        Examples (for the historical format):

        * With host and namespace::

            //acme.com/cimv2/test:CIM_RegisteredProfile

        * Without host but with namespace::

            cimv2/test:CIM_RegisteredProfile

        * Without host and without namespace::

            CIM_RegisteredProfile
        """
        return self.to_wbem_uri(format='historical')

    def __repr__(self):
        """
        Return a string representation of this CIM class path,
        that is suitable for debugging.
        """
        return _format(
            "CIMClassName("
            "classname={s.classname!A}, "
            "namespace={s.namespace!A}, "
            "host={s.host!A})",
            s=self)

    def tocimxml(self, ignore_host=False, ignore_namespace=False):
        """
        Return the CIM-XML representation of this CIM class path,
        as an object of an appropriate subclass of :term:`Element`.

        If the class path has no namespace specified or if
        `ignore_namespace` is `True`, the returned CIM-XML representation is a
        `CLASSNAME` element consistent with :term:`DSP0201`.

        Otherwise, if the class path has no host specified or if
        `ignore_host` is `True`, the returned CIM-XML representation is a
        `LOCALCLASSPATH` element consistent with :term:`DSP0201`.

        Otherwise, the returned CIM-XML representation is a
        `CLASSPATH` element consistent with :term:`DSP0201`.

        Parameters:

          ignore_host (:class:`py:bool`): Ignore the host of the
            class path, even if a host is specified.

          ignore_namespace (:class:`py:bool`): Ignore the namespace and host of
            the class path, even if a namespace and/or host is specified.

        Returns:

          The CIM-XML representation, as an object of an appropriate subclass
          of :term:`Element`.
        """

        classname_xml = cim_xml.CLASSNAME(self.classname)

        if self.namespace is None or ignore_namespace:
            return classname_xml

        localnsp_xml = cim_xml.LOCALNAMESPACEPATH(
            [cim_xml.NAMESPACE(ns)
             for ns in self.namespace.split('/')])

        if self.host is None or ignore_host:
            return cim_xml.LOCALCLASSPATH(localnsp_xml, classname_xml)

        return cim_xml.CLASSPATH(
            cim_xml.NAMESPACEPATH(cim_xml.HOST(self.host), localnsp_xml),
            classname_xml)

    def tocimxmlstr(self, indent=None, ignore_host=False,
                    ignore_namespace=False):
        """
        Return the CIM-XML representation of this CIM class path,
        as a :term:`unicode string`.

        *New in pywbem 0.9.*

        For the returned CIM-XML representation, see
        :meth:`~pywbem.CIMClassName.tocimxml`.

        Parameters:

          indent (:term:`string` or :term:`integer`):
            `None` indicates that a single-line version of the XML should be
            returned, without any whitespace between the XML elements.

            Other values indicate that a prettified, multi-line version of the
            XML should be returned. A string value specifies the indentation
            string to be used for each level of nested XML elements. An integer
            value specifies an indentation string of so many blanks.

          ignore_host (:class:`py:bool`): Ignore the host of the
            class path, even if a host is specified.

          ignore_namespace (:class:`py:bool`): Ignore the namespace and host of
            the class path, even if a namespace and/or host is specified.

        Returns:

            The CIM-XML representation of the object, as a
            :term:`unicode string`.
        """
        xml_elem = self.tocimxml(ignore_host, ignore_namespace)
        return tocimxmlstr(xml_elem, indent)

    @staticmethod
    def from_wbem_uri(wbem_uri):
        """
        Return a new :class:`~pywbem.CIMClassName` object from the specified
        WBEM URI string.

        *New in pywbem 0.12.*

        The WBEM URI string must be a CIM class path in untyped WBEM URI
        format, as defined in :term:`DSP0207`, with these extensions:

        * :term:`DSP0207` restricts the namespace types (URI schemes) to be one
          of ``http``, ``https``, ``cimxml-wbem``, or ``cimxml-wbems``. Pywbem
          tolerates any namespace type, but issues a
          :exc:`~py:exceptions.UserWarning` if it is not one of
          the namespace types defined in :term:`DSP0207`.

        * :term:`DSP0207` requires a slash before the namespace name. For local
          WBEM URIs (no namespace type, no authority), that slash is the first
          character of the WBEM URI. For historical reasons, pywbem tolerates a
          missing leading slash for local WBEM URIs. Note that pywbem requires
          the slash (consistent with :term:`DSP0207`) when the WBEM URI is not
          local.

        * :term:`DSP0207` requires a colon before the class name. For
          historical reasons, pywbem tolerates a missing colon before the class
          name, if it would have been the first character of the string.

        CIM class paths in the typed WBEM URI format defined in :term:`DSP0207`
        are not supported.

        Examples::

            https://jdd:test@acme.com:5989/cimv2/test:CIM_RegisteredProfile
            http://acme.com/root/cimv2:CIM_ComputerSystem
            http:/root/cimv2:CIM_ComputerSystem
            /root/cimv2:CIM_ComputerSystem
            root/cimv2:CIM_ComputerSystem
            /:CIM_ComputerSystem
            :CIM_ComputerSystem
            CIM_ComputerSystem

        Parameters:

          wbem_uri (:term:`string`):
            WBEM URI for a class path.

        Returns:

          :class:`~pywbem.CIMClassName`: The class path created from the
          specified WBEM URI string.

        Raises:

          ValueError: Invalid WBEM URI format for a class path. This includes
            typed WBEM URIs.
        """

        m = WBEM_URI_CLASSPATH_REGEXP.match(wbem_uri)
        if m is None:
            raise ValueError(
                _format("Invalid format for a class path in WBEM URI: {0!A}",
                        wbem_uri))

        ns_type = m.group(1) or None
        if ns_type and ns_type.lower() not in WBEM_URI_NAMESPACE_TYPES:
            warnings.warn(
                _format("Tolerating unknown namespace type in WBEM URI: {0!A}",
                        wbem_uri),
                UserWarning)

        host = m.group(2) or None
        namespace = m.group(3) or None
        classname = m.group(4) or None
        assert classname is not None  # should be ensured by regexp

        obj = CIMClassName(
            classname=classname,
            host=host,
            namespace=namespace)

        return obj

    def to_wbem_uri(self, format='standard'):
        # pylint: disable=redefined-builtin
        """
        Return the (untyped) WBEM URI string of this CIM class path.

        The returned WBEM URI contains its components as follows:

        * it does not contain a namespace type (URI scheme).
        * it contains an authority (host) component according to the
          :attr:`~pywbem.CIMClassName.host` attribute, if that is not
          `None`. Otherwise, it does not contain the authority component.
        * it contains a namespace component according to the
          :attr:`~pywbem.CIMClassName.namespace` attribute, if that is not
          `None`. Otherwise, it does not contain the namespace component.
        * it contains a class name component according to the
          :attr:`~pywbem.CIMClassName.classname` attribute.

        Note that when you do not want some of these components to show up
        in the resulting WBEM URI string, you can set them to `None` before
        calling this method.

        Except when using the format "canonical", this method should not be
        used to compare class paths for equality: :term:`DSP0004` defines
        several components of a class path to be compared case insensitively.
        All WBEM URI formats returned by this method except for the format
        "canonical" return a WBEM URI string that preserves the lexical case of
        any components. Therefore, two class paths that are considered equal
        according to :term:`DSP0004` may not have equal WBEM URI strings as
        as returned by this method.

        Instead, equality of class paths represented by
        :class:`~pywbem.CIMClassName` objects should be determined by using
        the ``==`` operator, which performs the comparison conformant to
        :term:`DSP0004`. If you have WBEM URI strings without the
        corresponding :class:`~pywbem.CIMClassName` object, such an object
        can be created by using the static method
        :meth:`~pywbem.CIMClassName.from_wbem_uri`.

        Parameters:

          format (:term:`string`): Format for the generated WBEM URI string,
            using one of the following values:

            * ``"standard"`` - Standard format that is conformant to untyped
              WBEM URIs for class paths defined in :term:`DSP0207`.

            * ``"canonical"`` - Like ``"standard"``, except that the following
              items have been converted to lower case: host, namespace, and
              classname.
              This format guarantees that two class paths that are
              considered equal according to :term:`DSP0004` result in equal
              WBEM URI strings. Therefore, the returned WBEM URI is suitable to
              be used as a key in dictionaries of CIM classes.

            * ``"cimobject"`` - Format for the `CIMObject` header field in
              CIM-XML messages for representing class paths (used
              internally, see :term:`DSP0200`).

            * ``"historical"`` - Historical format for WBEM URIs (used by
              :meth:`~pywbem.CIMClassName.__str__`; should not be used by
              new code). The historical format has the following differences to
              the standard format:

              - If the host component is not present, the slash after the
                host is also omitted. In the standard format, that slash
                is always present.

              - If the namespace component is not present, the colon after the
                namespace is also omitted. In the standard format, that colon
                is always present.

        Examples:

        * With host and namespace, standard format::

            //ACME.com/cimv2/Test:CIM_RegisteredProfile

        * With host and namespace, canonical format::

            //acme.com/cimv2/test:cim_registeredprofile

        * Without host but with namespace, standard format::

            /cimv2/Test:CIM_RegisteredProfile

        * Without host but with namespace, canonical format::

            /cimv2/test:cim_registeredprofile

        * Without host and without namespace, standard format::

            /:CIM_RegisteredProfile

        Returns:

          :term:`unicode string`: Untyped WBEM URI of the CIM class path,
          in the specified format.

        Raises:

          ValueError: Invalid format
        """

        def case(str_):
            """Return the string in the correct lexical case for the format."""
            if format == 'canonical':
                str_ = str_.lower()
            return str_

        if format not in ('standard', 'canonical', 'cimobject', 'historical'):
            raise ValueError(
                _format("Invalid format argument: {0}", format))

        ret = []

        if self.host is not None and format != 'cimobject':
            # The CIMObject format assumes there is no host component
            ret.append('//')
            ret.append(case(self.host))

        if self.host is not None or format not in ('cimobject', 'historical'):
            ret.append('/')

        if self.namespace is not None:
            ret.append(case(self.namespace))

        if self.namespace is not None or format != 'historical':
            ret.append(':')

        ret.append(case(self.classname))

        return _ensure_unicode(''.join(ret))


class CIMClass(_CIMComparisonMixin):
    """
    A representation of a CIM class in a CIM namespace in a WBEM server,
    optionally including its class path.

    Two objects of this class compare equal if their public attributes compare
    equal. Objects of this class are :term:`unchanged-hashable`, with the hash
    value being based on its public attributes. Therefore, objects of this
    class can be used as members in a set (or as dictionary keys) only during
    periods in which their public attributes remain unchanged.
    """

    # pylint: disable=too-many-arguments
    def __init__(self, classname, properties=None, methods=None,
                 superclass=None, qualifiers=None, path=None):
        """
        Parameters:

          classname (:term:`string`):
            Class name of the class.

            Must not be `None`.

            The lexical case of the string is preserved. Object comparison and
            hash value calculation are performed case-insensitively.

          properties (:term:`properties input object`):
            The property declarations for the class.

          methods (:term:`methods input object`):
            The method declarations for the class.

          superclass (:term:`string`):
            Name of the superclass for the class.

            `None` means that the class is a top-level class, and the
            :attr:`~pywbem.CIMClassName.superclass` attribute
            will also be `None`.

            The lexical case of the string is preserved. Object comparison and
            hash value calculation are performed case-insensitively.

          qualifiers (:term:`qualifiers input object`):
            The qualifiers for the class.

          path (:class:`~pywbem.CIMClassName`):
            Class path for the class.

            *New in pywbem 0.11.*

            The provided object will be copied before being stored in the
            :class:`~pywbem.CIMClass` object.

            `None` means that the instance path is unspecified, and the
            :attr:`~pywbem.CIMClass.path` attribute
            will also be `None`.

            This parameter has been added in pywbem 0.11 as a convenience
            for the user in order so that :class:`~pywbem.CIMClass` objects can
            be self-contained w.r.t. their class path.

        Raises:

          ValueError: classname is `None`, a property, method or qualifier name
            is `None`, or a property, method or qualifier name does not match
            its dictionary key.
          TypeError: a numeric Python type was used for a qualifier value.
        """

        # We use the respective setter methods:
        self.classname = classname
        self.superclass = superclass
        self.path = path
        self.properties = properties
        self.methods = methods
        self.qualifiers = qualifiers

    @property
    def classname(self):
        """
        :term:`unicode string`: Class name of this CIM class.

        Will not be `None`.

        This attribute is settable. For details, see the description of the
        same-named init parameter of
        :class:`this class <pywbem.CIMClass>`.
        """
        return self._classname

    @classname.setter
    def classname(self, classname):
        """Setter method; for a description see the getter method."""

        # DSP0004 defines a certain format of CIM class names, but we don't
        # check that in pywbem because we don't parse the class name anywhere.
        # Also, some WBEM servers implement special classes that deviate from
        # that format.

        # pylint: disable=attribute-defined-outside-init
        self._classname = _ensure_unicode(classname)

        # We perform this check after the initialization to avoid errors
        # in test tools that show the object with repr().
        if classname is None:
            raise ValueError("Class name in class must not be None")

    @property
    def superclass(self):
        """
        :term:`unicode string`: Class name of the superclass of this CIM class.

        `None` means that the class is a top-level class.

        This attribute is settable. For details, see the description of the
        same-named init parameter of
        :class:`this class <pywbem.CIMClass>`.
        """
        return self._superclass

    @superclass.setter
    def superclass(self, superclass):
        """Setter method; for a description see the getter method."""
        # pylint: disable=attribute-defined-outside-init
        self._superclass = _ensure_unicode(superclass)

    @property
    def properties(self):
        """
        `NocaseDict`_: Properties (declarations) of this CIM class.

        Will not be `None`.

        Each dictionary item specifies one property declaration, with:

        * key (:term:`unicode string`): Property name. Its lexical case was
          preserved.

        * value (:class:`~pywbem.CIMProperty`): Property declaration.

        The order of properties in the CIM class is preserved.

        This attribute is settable; setting it will cause the current CIM
        properties to be replaced with the new properties. For details, see
        the description of the same-named init parameter of
        :class:`this class <pywbem.CIMClass>`.

        The CIM properties can also be accessed and manipulated one by one
        because the attribute value is a modifiable dictionary. The provided
        input value must be a :class:`~pywbem.CIMProperty` object::

            cls = CIMClass(...)
            p1 = CIMProperty('p1', ...)  # must be a CIMProperty

            cls.properties['p1'] = p1  # Set "p1" to p1 (add if needed)
            p1 = cls.properties['p1']  # Access "p1"
            del cls.properties['p1']  # Delete "p1" from the class
        """
        return self._properties

    @properties.setter
    def properties(self, properties):
        """Setter method; for a description see the getter method."""
        # We make sure that the dictionary is a NocaseDict object, and that the
        # property values are CIMProperty objects:
        # pylint: disable=attribute-defined-outside-init
        self._properties = NocaseDict()
        if properties:
            try:
                # This is used for iterables:
                iterator = properties.items()
            except AttributeError:
                # This is used for dictionaries:
                iterator = properties
            for item in iterator:
                if isinstance(item, CIMProperty):
                    key = item.name
                    value = item
                elif isinstance(item, tuple):
                    key, value = item
                else:
                    raise TypeError(
                        _format("Input object for properties has invalid item "
                                "in iterable: {0!A}", item))
                self.properties[key] = _cim_property_decl(key, value)

    @property
    def methods(self):
        """
        `NocaseDict`_: Methods (declarations) of this CIM class.

        Will not be `None`.

        Each dictionary item specifies one method, with:

        * key (:term:`unicode string`): Method name. Its lexical case was
          preserved.

        * value (:class:`~pywbem.CIMMethod`): Method declaration.

        The order of methods in the CIM class is preserved.

        This attribute is settable; setting it will cause the current CIM
        methods to be replaced with the new methods. For details, see
        the description of the same-named init parameter of
        :class:`this class <pywbem.CIMClass>`.

        The CIM methods can also be accessed and manipulated one by one
        because the attribute value is a modifiable dictionary. The provided
        input value must be a :class:`~pywbem.CIMMethod` object::

            cls = CIMClass(...)
            m1 = CIMMethod('m1', ...)  # must be a CIMMethod

            cls.methods['m1'] = m1  # Set "m1" to m1 (add if needed)
            m1 = cls.methods['m1']  # Access "m1"
            del cls.methods['m1']  # Delete "m1" from the class
        """
        return self._methods

    @methods.setter
    def methods(self, methods):
        """Setter method; for a description see the getter method."""
        # We make sure that the dictionary is a NocaseDict object, and that the
        # property values are CIMMethod objects:
        # pylint: disable=attribute-defined-outside-init
        self._methods = NocaseDict()
        if methods:
            try:
                # This is used for iterables:
                iterator = methods.items()
            except AttributeError:
                # This is used for dictionaries:
                iterator = methods
            for item in iterator:
                if isinstance(item, CIMMethod):
                    key = item.name
                    value = item
                elif isinstance(item, tuple):
                    key, value = item
                else:
                    raise TypeError(
                        _format("Input object for methods has invalid item in "
                                "iterable: {0!A}", item))
                self.methods[key] = _cim_method(key, value)

    @property
    def qualifiers(self):
        """
        `NocaseDict`_: Qualifiers (qualifier values) of this CIM class.

        Will not be `None`.

        Each dictionary item specifies one qualifier value, with:

        * key (:term:`unicode string`): Qualifier name. Its lexical case was
          preserved.

        * value (:class:`~pywbem.CIMQualifier`): Qualifier value.

        The order of qualifiers in the CIM class is preserved.

        This attribute is settable; setting it will cause the current
        qualifiers to be replaced with the new qualifiers. For details, see
        the description of the same-named init parameter of
        :class:`this class <pywbem.CIMClass>`.

        The qualifier values can also be accessed and manipulated one by one
        because the attribute value is a modifiable dictionary. The provided
        input value may be specified as a :term:`CIM data type` or as a
        :class:`~pywbem.CIMQualifier` object::

            cls = CIMClass(...)
            q1 = Uint32(...)  # may be CIM data type or CIMQualifier

            cls.qualifiers['q1'] = q1  # Set "q1" to q1 (add if needed)
            q1 = cls.qualifiers['q1']  # Access "q1"
            del cls.qualifiers['q1']  # Delete "q1" from the class
        """
        return self._qualifiers

    @qualifiers.setter
    def qualifiers(self, qualifiers):
        """Setter method; for a description see the getter method."""
        # We make sure that the dictionary is a NocaseDict object, and that the
        # property values are CIMQualifier objects:
        # pylint: disable=attribute-defined-outside-init
        self._qualifiers = NocaseDict()
        if qualifiers:
            try:
                # This is used for iterables:
                iterator = qualifiers.items()
            except AttributeError:
                # This is used for dictionaries:
                iterator = qualifiers
            for item in iterator:
                if isinstance(item, CIMQualifier):
                    key = item.name
                    value = item
                elif isinstance(item, tuple):
                    key, value = item
                else:
                    raise TypeError(
                        _format("Input object for qualifiers has invalid item "
                                "in iterable: {0!A}", item))
                self.qualifiers[key] = _cim_qualifier(key, value)

    @property
    def path(self):
        """
        :class:`~pywbem.CIMClassName`: Class path of this CIM class.

        *New in pywbem 0.11.*

        `None` means that the class path is unspecified.

        This attribute has been added in pywbem 0.11 as a convenience
        for the user in order so that :class:`~pywbem.CIMClass` objects can
        be self-contained w.r.t. their class path.

        This attribute will be set in in any :class:`~pywbem.CIMClass`
        objects returned by :class:`~pywbem.WBEMConnection` methods, based
        on information in the response from the WBEM server.

        This attribute is settable. For details, see the description of the
        same-named init parameter of
        :class:`this class <pywbem.CIMClass>`.
        """
        return self._path

    @path.setter
    def path(self, path):
        """Setter method; for a description see the getter method."""

        # pylint: disable=attribute-defined-outside-init
        self._path = copy_.copy(path)

        # The provided path is shallow copied; it does not have any attributes
        # with mutable types.

        # We perform this check after the initialization to avoid errors
        # in test tools that show the object with repr().
        assert isinstance(path, CIMClassName) or path is None

    def _cmp(self, other):
        """
        Comparator function for two :class:`~pywbem.CIMClass` objects.

        The comparison is based on their public attributes, in descending
        precedence:

        * `classname`
        * `superclass`
        * `qualifiers`
        * `properties`
        * `methods`
        * `path`

        The comparison takes into account any case insensitivities described
        for these attributes.
        """
        if self is other:
            return 0
        try:
            assert isinstance(other, CIMClass)
        except AssertionError:
            raise TypeError(
                _format("other must be CIMClass, but is: {0}", type(other)))
        return (cmpname(self.classname, other.classname) or
                cmpname(self.superclass, other.superclass) or
                cmpdict(self.qualifiers, other.qualifiers) or
                cmpdict(self.properties, other.properties) or
                cmpdict(self.methods, other.methods) or
                cmpitem(self.path, other.path))

    def __hash__(self):
        """
        Return a hash value based on the public attributes of this class, taking
        into account any case insensitivities described for these attributes.
        This approach causes this class to be :term:`unchanged-hashable`.
        """
        hashes = (
            _hash_name(self.classname),
            _hash_name(self.superclass),
            _hash_dict(self.qualifiers),
            _hash_dict(self.properties),
            _hash_dict(self.methods),
            _hash_item(self.path),
        )
        return hash(hashes)

    def __str__(self):
        """
        Return a short string representation of this CIM class,
        for human consumption.
        """
        return _format(
            "CIMClass("
            "classname={s.classname!A}, ...)",
            s=self)

    def __repr__(self):
        """
        Return a string representation of this CIM class,
        that is suitable for debugging.

        The order of properties, method and qualifiers will be preserved in
        the result.
        """
        return _format(
            "CIMClass("
            "classname={s.classname!A}, "
            "superclass={s.superclass!A}, "
            "properties={s.properties!A}, "
            "methods={s.methods!A}, "
            "qualifiers={s.qualifiers!A}, "
            "path={s.path!A})",
            s=self)

    def copy(self):
        """
        Return a new :class:`~pywbem.CIMClass` object that is a copy
        of this CIM class.

        This is a middle-deep copy; any mutable types in attributes except the
        following are copied, so besides these exceptions, modifications of the
        original object will not affect the returned copy, and vice versa. The
        following mutable types are not copied and are therefore shared between
        original and copy:

        * The :class:`~pywbem.CIMProperty` objects in the
          :attr:`~pywbem.CIMClass.properties` dictionary (but not the
          dictionary object itself)
        * The :class:`~pywbem.CIMMethod` objects in the
          :attr:`~pywbem.CIMClass.methods` dictionary (but not the dictionary
          object itself)
        * The :class:`~pywbem.CIMQualifier` objects in the
          :attr:`~pywbem.CIMClass.qualifiers` dictionary (but not the
          dictionary object itself)

        Note that the Python functions :func:`py:copy.copy` and
        :func:`py:copy.deepcopy` can be used to create completely shallow or
        completely deep copies of objects of this class.
        """
        return CIMClass(
            self.classname,
            properties=self.properties,  # setter copies
            methods=self.methods,  # setter copies
            superclass=self.superclass,
            qualifiers=self.qualifiers,  # setter copies
            path=self.path)  # setter copies

    def tocimxml(self):
        """
        Return the CIM-XML representation of this CIM class,
        as an object of an appropriate subclass of :term:`Element`.

        The returned CIM-XML representation is a `CLASS` element
        consistent with :term:`DSP0201`. This is the required element for
        representing embedded classes.

        If the class has a class path specified, it will be ignored.

        The order of properties, methods, parameters, and qualifiers in the
        returned CIM-XML representation is preserved from the
        :class:`~pywbem.CIMClass` object.

        Returns:

          The CIM-XML representation, as an object of an appropriate subclass
          of :term:`Element`.
        """
        return cim_xml.CLASS(
            self.classname,
            properties=[p.tocimxml() for p in self.properties.values()],
            methods=[m.tocimxml() for m in self.methods.values()],
            qualifiers=[q.tocimxml() for q in self.qualifiers.values()],
            superclass=self.superclass)

    def tocimxmlstr(self, indent=None):
        """
        Return the CIM-XML representation of this CIM class,
        as a :term:`unicode string`.

        *New in pywbem 0.9.*

        For the returned CIM-XML representation, see
        :meth:`~pywbem.CIMClass.tocimxml`.

        Parameters:

          indent (:term:`string` or :term:`integer`):
            `None` indicates that a single-line version of the XML should be
            returned, without any whitespace between the XML elements.

            Other values indicate that a prettified, multi-line version of the
            XML should be returned. A string value specifies the indentation
            string to be used for each level of nested XML elements. An integer
            value specifies an indentation string of so many blanks.

        Returns:

            The CIM-XML representation of the object, as a
            :term:`unicode string`.
        """
        xml_elem = self.tocimxml()
        return tocimxmlstr(xml_elem, indent)

    def tomof(self, maxline=MAX_MOF_LINE):
        """
        Return a MOF string with the declaration of this CIM class.

        The returned MOF string conforms to the ``classDeclaration``
        ABNF rule defined in :term:`DSP0004`.

        The order of properties, methods, parameters, and qualifiers is
        preserved.

        The :attr:`~pywbem.CIMClass.path` attribute of this object will not be
        included in the returned MOF string.

        Consistent with that, class path information is not included in the
        returned MOF string.

        Returns:

          :term:`unicode string`: MOF string.
        """

        mof = []

        mof.append(_qualifiers_tomof(self.qualifiers, MOF_INDENT, maxline))

        mof.append(u'class ')
        mof.append(self.classname)
        mof.append(u' ')

        if self.superclass is not None:
            mof.append(u': ')
            mof.append(self.superclass)
            mof.append(u' ')

        mof.append(u'{\n')

        for p in self.properties.itervalues():
            mof.append(u'\n')
            mof.append(p.tomof(False, MOF_INDENT, maxline))

        for m in self.methods.itervalues():
            mof.append(u'\n')
            mof.append(m.tomof(MOF_INDENT, maxline))

        mof.append(u'\n};\n')

        return u''.join(mof)


# pylint: disable=too-many-statements,too-many-instance-attributes
class CIMProperty(_CIMComparisonMixin):
    """
    A CIM property (value or declaration).

    This object can be used in a :class:`~pywbem.CIMInstance` object for
    representing a property value, or in a :class:`~pywbem.CIMClass` object
    for representing a property declaration.

    For property values in CIM instances:

      * The `value` attribute is the actual value of the property.
      * Qualifiers are not allowed.

    For property declarations in CIM classes:

      * The `value` attribute is the default value of the property
        declaration.
      * Qualifiers are allowed.

    Scalar (=non-array) properties may have a value of NULL (= `None`), any
    primitive CIM data type, reference type, and string type with embedded
    instance or embedded object.

    Array properties may be Null or may have elements with a value of NULL, any
    primitive CIM data type, and string type with embedded instance or embedded
    object. Reference types are not allowed in property arrays in CIM, as per
    :term:`DSP0004`.

    Two objects of this class compare equal if their public attributes compare
    equal. Objects of this class are :term:`unchanged-hashable`, with the hash
    value being based on its public attributes. Therefore, objects of this
    class can be used as members in a set (or as dictionary keys) only during
    periods in which their public attributes remain unchanged.
    """

    # pylint: disable=too-many-statements
    def __init__(self, name, value, type=None,
                 class_origin=None, array_size=None, propagated=None,
                 is_array=None, reference_class=None, qualifiers=None,
                 embedded_object=None):
        # pylint: disable=redefined-builtin,too-many-arguments,too-many-branches
        # pylint: disable=too-many-statements,too-many-instance-attributes
        """
        The init method infers optional parameters that are not specified (for
        example, it infers `type` from the Python type of `value` and other
        information). If the specified parameters are inconsistent, an
        exception is raised. If an optional parameter is needed for some
        reason, an exception is raised.

        Parameters:

          name (:term:`string`):
            Name of the property.

            Must not be `None`.

            The lexical case of the string is preserved. Object comparison and
            hash value calculation are performed case-insensitively.

          value (:term:`CIM data type` or other suitable types):
            Value of the property.

            The property value is interpreted as an actual property value when
            the CIM property is used in a CIM instance, and as default value
            when the CIM property is used in a CIM class.

            `None` means that the property is Null, and the same-named
            attribute in the :class:`~pywbem.CIMProperty` object will also be
            `None`.

            The specified value will be converted to a :term:`CIM data type`
            using the rules documented in the description of
            :func:`~pywbem.cimvalue`, taking into account the `type` parameter.

          type (:term:`string`):
            Name of the CIM data type of the property (e.g. ``"uint8"``).

            `None` will cause the type to be inferred from the `value`
            parameter, raising :exc:`~py:exceptions.ValueError` if it cannot be
            inferred (for example when `value` is `None` or a Python integer).

            :exc:`~py:exceptions.ValueError` is raised if the type is not a
            valid CIM data type (see :ref:`CIM data types`).

          class_origin (:term:`string`):
            The CIM class origin of the property (the name
            of the most derived class that defines or overrides the property in
            the class hierarchy of the class owning the property).

            `None` means that class origin information is not available, and
            :attr:`~pywbem.CIMProperty.class_origin` attribute
            will also be `None`.

            The lexical case of the string is preserved. Object comparison and
            hash value calculation are performed case-insensitively.

          array_size (:term:`integer`):
            The size of the array property, for fixed-size arrays.

            `None` means that the array property has variable size, and
            :attr:`~pywbem.CIMProperty.array_size` attribute
            will also be `None`.

          propagated (:class:`py:bool`):
            If not `None`, specifies whether the property declaration has been
            propagated from a superclass, or the property value has been
            propagated from the creation class.

            `None` means that propagation information is not available, and
            :attr:`~pywbem.CIMProperty.propagated` attribute
            will also be `None`.

          is_array (:class:`py:bool`):
            A boolean indicating whether the property is an array (`True`) or a
            scalar (`False`).

            If `None`, the :attr:`~pywbem.CIMProperty.is_array` attribute
            will be inferred from the `value` parameter.
            If the `value` parameter is `None`, a scalar is assumed.

          reference_class (:term:`string`):
            For reference properties, the name of the class referenced by the
            property, or `None` indicating that the referenced class is
            unspecified.

            For non-reference properties, must be `None`.

            The lexical case of the string is preserved. Object comparison and
            hash value calculation are performed case-insensitively.

            Note: Prior to pywbem 0.11, the corresponding attribute was
            inferred from the creation class name of a referenced instance.
            This was incorrect and has been fixed in pywbem 0.11.

          qualifiers (:term:`qualifiers input object`):
            The qualifiers for the property declaration. Has no meaning for
            property values.

          embedded_object (:term:`string`):
            A string value indicating the kind of embedded object represented
            by the property value. Has no meaning for property declarations.

            For details about the possible values, see the corresponding
            attribute.

            `None` means that the value is unspecified, causing the same-named
            attribute in the :class:`~pywbem.CIMProperty` object to be
            inferred. An exception is raised if it cannot be inferred.

            `False` means the property value is not an embedded object, and
            is stored as `None`.

        Examples:

        ::

            # a string property:
            CIMProperty("MyString", "abc")

            # a uint8 property:
            CIMProperty("MyNum", 42, "uint8")

            # a uint8 property:
            CIMProperty("MyNum", Uint8(42))

            # a uint8 array property:
            CIMProperty("MyNumArray", [1, 2, 3], "uint8")

            # a reference property:
            CIMProperty("MyRef", CIMInstanceName("Foo"))

            # an embedded object property containing a class:
            CIMProperty("MyEmbObj", CIMClass("Foo"))

            # an embedded object property containing an instance:
            CIMProperty("MyEmbObj", CIMInstance("Foo"),
                        embedded_object="object")

            # an embedded instance property:
            CIMProperty("MyEmbInst", CIMInstance("Foo"))

            # a string property that is Null:
            CIMProperty("MyString", None, "string")

            # a uint8 property that is Null:
            CIMProperty("MyNum", None, "uint8")

            # a reference property that is Null:
            CIMProperty("MyRef", None, "reference", reference_class="MyClass")

            # an embedded object property that is Null:
            CIMProperty("MyEmbObj", None, "string", embedded_object="object")

            # an embedded instance property that is Null:
            CIMProperty("MyEmbInst", None, "string",
                        embedded_object="instance")
        """

        # We use the respective setter methods:
        self.name = name

        if type is None:
            type = _infer_type(value, "property", name)

        if is_array is None:
            is_array = _infer_is_array(value)
        else:
            # For performance reasons, we check only if not inferred.
            # This leaves the incorrect combination of is_array=False and
            # array_size=5 undetected, which seems acceptable because
            # array_size is ignored anyway when is_array=False.
            _check_array_parms(is_array, array_size, value, "property", name)

        if embedded_object is None:
            embedded_object = _infer_embedded_object(value)

        if embedded_object:
            _check_embedded_object(embedded_object, type, value,
                                   "property", name)

        if reference_class is not None:
            if is_array:
                raise ValueError(
                    _format("Property {0!A} specifies reference_class {1!A} "
                            "but is an array property",
                            name, reference_class))
            # The check for valid types of the input value will be performed
            # in the value setter.

        # We use the respective setter methods:
        self.type = type
        self.value = value  # value setter relies on self.type being set
        self.class_origin = class_origin
        self.array_size = array_size
        self.propagated = propagated
        self.is_array = is_array
        self.reference_class = reference_class
        self.qualifiers = qualifiers
        self.embedded_object = embedded_object

    @property
    def name(self):
        """
        :term:`unicode string`: Name of this CIM property.

        Will not be `None`.

        This attribute is settable. For details, see the description of the
        same-named init parameter of
        :class:`this class <pywbem.CIMProperty>`.
        """
        return self._name

    @name.setter
    def name(self, name):
        """Setter method; for a description see the getter method."""

        # pylint: disable=attribute-defined-outside-init
        self._name = _ensure_unicode(name)

        # We perform this check after the initialization to avoid errors
        # in test tools that show the object with repr().
        if name is None:
            raise ValueError("CIMProperty 'name' parameter must not be None")

    @property
    def value(self):
        """
        :term:`CIM data type`: Value of this CIM property.

        The property value is interpreted as an actual property value when this
        CIM property is used in a CIM instance, and as default value when this
        CIM property is used in a CIM class.

        `None` means that the value is Null.

        This attribute is settable. For details, see the description of the
        same-named init parameter of
        :class:`this class <pywbem.CIMProperty>`.
        """
        return self._value

    @value.setter
    def value(self, value):
        """Setter method; for a description see the getter method."""
        # pylint: disable=attribute-defined-outside-init
        self._value = cimvalue(value, self.type)

    @property
    def type(self):
        """
        :term:`unicode string`: Name of the CIM data type of this CIM property.

        Example: ``"uint8"``

        Will not be `None`.

        This attribute is settable. For details, see the description of the
        same-named init parameter of
        :class:`this class <pywbem.CIMProperty>`.
        """
        return self._type

    @type.setter
    def type(self, type):
        # pylint: disable=redefined-builtin
        """Setter method; for a description see the getter method."""

        type = _ensure_unicode(type)

        # We perform this check after the initialization to avoid errors
        # in test tools that show the object with repr().
        if type not in ALL_CIMTYPES:
            raise ValueError(
                _format("Invalid CIM type: {0}", type))

        # pylint: disable=attribute-defined-outside-init
        self._type = type

    @property
    def reference_class(self):
        """
        :term:`unicode string`: The name of the class referenced by this CIM
        reference property.

        Will be `None` for non-reference properties or if the referenced class
        is unspecified in reference properties.

        Note that in CIM instances returned from a WBEM server, :term:`DSP0201`
        recommends this attribute not to be set. For CIM classes returned from
        a WBEM server, :term:`DSP0201` requires this attribute to be set.

        This attribute is settable. For details, see the description of the
        same-named init parameter of
        :class:`this class <pywbem.CIMProperty>`.
        """
        return self._reference_class

    @reference_class.setter
    def reference_class(self, reference_class):
        """Setter method; for a description see the getter method."""
        # pylint: disable=attribute-defined-outside-init
        self._reference_class = _ensure_unicode(reference_class)

    @property
    def embedded_object(self):
        """
        :term:`unicode string`: A string value indicating the kind of embedded
        object represented by this CIM property value.

        Has no meaning for CIM property declarations.

        The following values are defined for this parameter:

        * ``"instance"``: The property is declared with the
          ``EmbeddedInstance`` qualifier, indicating that the property
          value is an embedded instance of the class specified as the value
          of the ``EmbeddedInstance`` qualifier.
          The property value must be a :class:`~pywbem.CIMInstance` object,
          or `None`.
        * ``"object"``: The property is declared with the
          ``EmbeddedObject`` qualifier, indicating that the property
          value is an embedded object (instance or class) of which the
          class name is not known.
          The property value must be a :class:`~pywbem.CIMInstance` or
          :class:`~pywbem.CIMClass` object, or `None`.
        * `None`, for properties not representing embedded objects.

        This attribute is settable. For details, see the description of the
        same-named init parameter of
        :class:`this class <pywbem.CIMProperty>`.
        """
        return self._embedded_object

    @embedded_object.setter
    def embedded_object(self, embedded_object):
        """Setter method; for a description see the getter method."""
        # pylint: disable=attribute-defined-outside-init
        if embedded_object is False:
            self._embedded_object = None
        else:
            self._embedded_object = _ensure_unicode(embedded_object)

    @property
    def is_array(self):
        """
        :class:`py:bool`: Boolean indicating that this CIM property
        is an array (as opposed to a scalar).

        Will not be `None`.

        This attribute is settable. For details, see the description of the
        same-named init parameter of
        :class:`this class <pywbem.CIMProperty>`.
        """
        return self._is_array

    @is_array.setter
    def is_array(self, is_array):
        """Setter method; for a description see the getter method."""
        # pylint: disable=attribute-defined-outside-init
        self._is_array = _ensure_bool(is_array)

    @property
    def array_size(self):
        """
        :term:`integer`: The size of the fixed-size array of this CIM property.

        `None` means that the array has variable size, or that the
        property is a scalar.

        This attribute is settable. For details, see the description of the
        same-named init parameter of
        :class:`this class <pywbem.CIMProperty>`.
        """
        return self._array_size

    @array_size.setter
    def array_size(self, array_size):
        """Setter method; for a description see the getter method."""
        # pylint: disable=attribute-defined-outside-init
        self._array_size = array_size

    @property
    def class_origin(self):
        """
        :term:`unicode string`: The class origin of this CIM property,
        identifying the most derived class that defines or overrides the
        property in the class hierarchy of the class owning the property.

        `None` means that class origin information is not available.

        This attribute is settable. For details, see the description of the
        same-named init parameter of
        :class:`this class <pywbem.CIMProperty>`.
        """
        return self._class_origin

    @class_origin.setter
    def class_origin(self, class_origin):
        """Setter method; for a description see the getter method."""
        # pylint: disable=attribute-defined-outside-init
        self._class_origin = _ensure_unicode(class_origin)

    @property
    def propagated(self):
        """
        :class:`py:bool`: Boolean indicating that the property declaration
        has been propagated from a superclass, or that the property value has
        been propagated from the creation class.

        `None` means that propagation information is not available.

        This attribute is settable. For details, see the description of the
        same-named init parameter of
        :class:`this class <pywbem.CIMProperty>`.
        """
        return self._propagated

    @propagated.setter
    def propagated(self, propagated):
        """Setter method; for a description see the getter method."""
        # pylint: disable=attribute-defined-outside-init
        self._propagated = _ensure_bool(propagated)

    @property
    def qualifiers(self):
        """
        `NocaseDict`_: Qualifiers (qualifier values) of this CIM property
        declaration.

        Will not be `None`.

        Each dictionary item specifies one qualifier value, with:

        * key (:term:`unicode string`): Qualifier name. Its lexical case was
          preserved.

        * value (:class:`~pywbem.CIMQualifier`): Qualifier value.

        The order of qualifiers in the property is preserved.

        This attribute is settable; setting it will cause the current
        qualifiers to be replaced with the new qualifiers. For details, see
        the description of the same-named init parameter of
        :class:`this class <pywbem.CIMProperty>`.

        The qualifier values can also be accessed and manipulated one by one
        because the attribute value is a modifiable dictionary. The provided
        input value may be specified as a :term:`CIM data type` or as a
        :class:`~pywbem.CIMQualifier` object::

            prop = CIMProperty(...)
            q1 = CIMQualifier('q1', ...) # may be CIM data type or CIMQualifier

            prop.qualifiers['q1'] = q1  # Set "q1" to q1 (add if needed)
            q1 = prop.qualifiers['q1']  # Access "q1"
            del prop.qualifiers['q1']  # Delete "q1" from the class
        """
        return self._qualifiers

    @qualifiers.setter
    def qualifiers(self, qualifiers):
        """Setter method; for a description see the getter method."""
        # We make sure that the dictionary is a NocaseDict object, and that the
        # property values are CIMQualifier objects:
        # pylint: disable=attribute-defined-outside-init
        self._qualifiers = NocaseDict()
        if qualifiers:
            try:
                # This is used for iterables:
                iterator = qualifiers.items()
            except AttributeError:
                # This is used for dictionaries:
                iterator = qualifiers
            for item in iterator:
                if isinstance(item, CIMQualifier):
                    key = item.name
                    value = item
                elif isinstance(item, tuple):
                    key, value = item
                else:
                    raise TypeError(
                        _format("Input object for qualifiers has invalid item "
                                "in iterable: {0!A}", item))
                self.qualifiers[key] = _cim_qualifier(key, value)

    def copy(self):
        """
        Return a new :class:`~pywbem.CIMProperty` object that is a copy
        of this CIM property.

        This is a middle-deep copy; any mutable types in attributes except the
        following are copied, so besides these exceptions, modifications of the
        original object will not affect the returned copy, and vice versa. The
        following mutable types are not copied and are therefore shared between
        original and copy:

        * The :class:`~pywbem.CIMQualifier` objects in the
          :attr:`~pywbem.CIMProperty.qualifiers` dictionary (but not the
          dictionary object itself)

        Note that the Python functions :func:`py:copy.copy` and
        :func:`py:copy.deepcopy` can be used to create completely shallow or
        completely deep copies of objects of this class.
        """
        return CIMProperty(
            self.name,
            self.value,
            type=self.type,
            class_origin=self.class_origin,
            array_size=self.array_size,
            propagated=self.propagated,
            is_array=self.is_array,
            reference_class=self.reference_class,
            qualifiers=self.qualifiers)  # setter copies

    def __str__(self):
        """
        Return a short string representation of this CIM property,
        for human consumption.
        """
        return _format(
            "CIMProperty("
            "name={s.name!A}, "
            "value={s.value!A}, "
            "type={s.type!A}, "
            "reference_class={s.reference_class!A}, "
            "embedded_object={s.embedded_object!A}, "
            "is_array={s.is_array!A}, ...)",
            s=self)

    def __repr__(self):
        """
        Return a string representation of this CIM property,
        that is suitable for debugging.

        The order of qualifiers will be preserved in the result.
        """
        return _format(
            "CIMProperty("
            "name={s.name!A}, "
            "value={s.value!A}, "
            "type={s.type!A}, "
            "reference_class={s.reference_class!A}, "
            "embedded_object={s.embedded_object!A}, "
            "is_array={s.is_array!A}, "
            "array_size={s.array_size!A}, "
            "class_origin={s.class_origin!A}, "
            "propagated={s.propagated!A}, "
            "qualifiers={s.qualifiers!A})",
            s=self)

    def tocimxml(self):
        """
        Return the CIM-XML representation of this CIM property,
        as an object of an appropriate subclass of :term:`Element`.

        The returned CIM-XML representation is a `PROPERTY`,
        `PROPERTY.REFERENCE`, or `PROPERTY.ARRAY` element dependent on the
        property type, and consistent with :term:`DSP0201`. Note that
        array properties cannot be of reference type.

        The order of qualifiers in the returned CIM-XML representation is
        preserved from the :class:`~pywbem.CIMProperty` object.

        Returns:

          The CIM-XML representation, as an object of an appropriate subclass
          of :term:`Element`.
        """

        qualifiers = [q.tocimxml() for q in self.qualifiers.values()]

        if self.is_array:  # pylint: disable=no-else-return
            assert self.type != 'reference'

            if self.value is None:
                value_xml = None
            else:
                array_xml = []
                for v in self.value:
                    if v is None:
                        if SEND_VALUE_NULL:
                            array_xml.append(cim_xml.VALUE_NULL())
                        else:
                            array_xml.append(cim_xml.VALUE(None))
                    elif self.embedded_object is not None:
                        assert isinstance(v, (CIMInstance, CIMClass))
                        array_xml.append(cim_xml.VALUE(v.tocimxml().toxml()))
                    else:
                        array_xml.append(cim_xml.VALUE(atomic_to_cim_xml(v)))
                value_xml = cim_xml.VALUE_ARRAY(array_xml)

            return cim_xml.PROPERTY_ARRAY(
                self.name,
                self.type,
                value_xml,
                self.array_size,
                self.class_origin,
                self.propagated,
                embedded_object=self.embedded_object,
                qualifiers=qualifiers)

        elif self.type == 'reference':  # scalar

            if self.value is None:
                value_xml = None
            else:
                value_xml = cim_xml.VALUE_REFERENCE(self.value.tocimxml())

            return cim_xml.PROPERTY_REFERENCE(
                self.name,
                value_xml,
                reference_class=self.reference_class,
                class_origin=self.class_origin,
                propagated=self.propagated,
                qualifiers=qualifiers)

        else:  # scalar non-reference

            if self.value is None:
                value_xml = None
            else:
                if self.embedded_object is not None:
                    assert isinstance(self.value, (CIMInstance, CIMClass))
                    value_xml = cim_xml.VALUE(self.value.tocimxml().toxml())
                else:
                    value_xml = cim_xml.VALUE(atomic_to_cim_xml(self.value))

            return cim_xml.PROPERTY(
                self.name,
                self.type,
                value_xml,
                class_origin=self.class_origin,
                propagated=self.propagated,
                embedded_object=self.embedded_object,
                qualifiers=qualifiers)

    def tocimxmlstr(self, indent=None):
        """
        Return the CIM-XML representation of this CIM property,
        as a :term:`unicode string`.

        *New in pywbem 0.9.*

        For the returned CIM-XML representation, see
        :meth:`~pywbem.CIMProperty.tocimxml`.

        Parameters:

          indent (:term:`string` or :term:`integer`):
            `None` indicates that a single-line version of the XML should be
            returned, without any whitespace between the XML elements.

            Other values indicate that a prettified, multi-line version of the
            XML should be returned. A string value specifies the indentation
            string to be used for each level of nested XML elements. An integer
            value specifies an indentation string of so many blanks.

        Returns:

            The CIM-XML representation of the object, as a
            :term:`unicode string`.
        """
        xml_elem = self.tocimxml()
        return tocimxmlstr(xml_elem, indent)

    def tomof(
            self, is_instance=True, indent=0, maxline=MAX_MOF_LINE, line_pos=0):
        """
        Return a MOF string with the declaration of this CIM property for use
        in a CIM class, or the specification of this CIM property for use in a
        CIM instance.

        *New in pywbem 0.9.*

        Even though pywbem supports qualifiers on :class:`~pywbem.CIMProperty`
        objects that are used as property values within an instance, the
        returned MOF string for property values in instances does not contain
        any qualifier values.

        The order of qualifiers is preserved.

        Parameters:

          is_instance (bool): If `True`, return MOF for a property value in a
            CIM instance. Else, return MOF for a property definition in a CIM
            class.

          indent (:term:`integer`): Number of spaces to indent each line of
            the returned string, counted in the line with the property name.

        Returns:

          :term:`unicode string`: MOF string.
        """

        mof = []

        if is_instance:
            # Property value in an instance

            mof.append(_indent_str(indent))
            mof.append(self.name)

        else:
            # Property declaration in a class

            if self.qualifiers:
                mof.append(_qualifiers_tomof(self.qualifiers,
                                             indent + MOF_INDENT, maxline))

            mof.append(_indent_str(indent))
            mof.append(moftype(self.type, self.reference_class))
            mof.append(u' ')
            mof.append(self.name)

            if self.is_array:
                mof.append(u'[')
                if self.array_size is not None:
                    mof.append(six.text_type(self.array_size))
                mof.append(u']')

        # Generate the property value (nearly common for property values and
        # property declarations).

        if self.value is not None or is_instance:
            mof.append(u' =')

            if isinstance(self.value, list):
                mof.append(u' {')
                mof_str = u''.join(mof)
                line_pos = len(mof_str) - mof_str.rfind('\n') - 1
                # Assume in line_pos that the extra space would be needed
                val_str, line_pos = _value_tomof(
                    self.value, self.type, indent + MOF_INDENT, maxline,
                    line_pos + 1, 1, True)
                # Empty arrays are represented as val_str=''
                if val_str and val_str[0] != '\n':
                    # The extra space was actually needed
                    mof.append(u' ')
                else:
                    # Adjust by the extra space that was not needed
                    line_pos -= 1
                mof.append(val_str)
                mof.append(u' }')

            else:
                mof_str = u''.join(mof)
                line_pos = len(mof_str) - mof_str.rfind('\n') - 1
                # Assume in line_pos that the extra space would be needed
                val_str, line_pos = _value_tomof(
                    self.value, self.type, indent + MOF_INDENT, maxline,
                    line_pos + 1, 1, True)
                # Scalars cannot be represented as val_str=''
                if val_str[0] != '\n':
                    # The extra space was actually needed
                    mof.append(u' ')
                else:
                    # Adjust by the extra space that was not needed
                    line_pos -= 1
                mof.append(val_str)

        mof.append(';\n')

        return u''.join(mof)

    def _cmp(self, other):
        """
        Comparator function for two :class:`~pywbem.CIMProperty` objects.

        The comparison is based on their public attributes, in descending
        precedence:

        * `name`
        * `value`
        * `type`
        * `reference_class`
        * `embedded_object`
        * `is_array`
        * `array_size`
        * `propagated`
        * `class_origin`
        * `qualifiers`

        The comparison takes into account any case insensitivities described
        for these attributes.

        Raises `TypeError', if the `other` object is not a
        :class:`~pywbem.CIMProperty` object.
        """
        if self is other:
            return 0
        try:
            assert isinstance(other, CIMProperty)
        except AssertionError:
            raise TypeError(
                _format("other must be CIMProperty, but is: {0}", type(other)))
        return (cmpname(self.name, other.name) or
                cmpitem(self.value, other.value) or
                cmpitem(self.type, other.type) or
                cmpname(self.reference_class, other.reference_class) or
                cmpitem(self.embedded_object, other.embedded_object) or
                cmpitem(self.is_array, other.is_array) or
                cmpitem(self.array_size, other.array_size) or
                cmpitem(self.propagated, other.propagated) or
                cmpname(self.class_origin, other.class_origin) or
                cmpdict(self.qualifiers, other.qualifiers))

    def __hash__(self):
        """
        Return a hash value based on the public attributes of this class, taking
        into account any case insensitivities described for these attributes.
        This approach causes this class to be :term:`unchanged-hashable`.
        """
        hashes = (
            _hash_name(self.name),
            _hash_item(self.value),
            _hash_item(self.type),
            _hash_name(self.reference_class),
            _hash_item(self.embedded_object),
            _hash_item(self.is_array),
            _hash_item(self.array_size),
            _hash_item(self.propagated),
            _hash_name(self.class_origin),
            _hash_dict(self.qualifiers),
        )
        return hash(hashes)


class CIMMethod(_CIMComparisonMixin):
    """
    A method (declaration) in a CIM class.

    Two objects of this class compare equal if their public attributes compare
    equal. Objects of this class are :term:`unchanged-hashable`, with the hash
    value being based on its public attributes. Therefore, objects of this
    class can be used as members in a set (or as dictionary keys) only during
    periods in which their public attributes remain unchanged.
    """

    # pylint: disable=too-many-arguments
    def __init__(self, name=None, return_type=None, parameters=None,
                 class_origin=None, propagated=None, qualifiers=None,
                 methodname=None):
        """
        The init method stores the input parameters as-is and does not infer
        unspecified parameters from the others (like
        :class:`~pywbem.CIMProperty` does).

        Parameters:

          name (:term:`string`):
            **Deprecated:** Name of this CIM method (just the method name,
            without class name or parenthesis).

            This argument has been named `methodname` before pywbem 0.9.
            Using `methodname` as a named argument still works, but has been
            deprecated in pywbem 0.9.

            Must not be `None`.

            The lexical case of the string is preserved. Object comparison and
            hash value calculation are performed case-insensitively.

          return_type (:term:`string`):
            Name of the CIM data type of the method return type
            (e.g. ``"uint32"``).

            Must not be `None` or ``"reference"``.

            :exc:`~py:exceptions.ValueError` is raised if the type is `None`,
            ``"reference"``, or not a valid CIM data type (see
            :ref:`CIM data types`).

            Support for void return types: Pywbem also does not support void
            return types, consistent with the CIM architecture and MOF syntax
            (see :term:`DSP0004`). Note that void return types could be
            represented in CIM-XML (see :term:`DSP0201`).

            Support for reference return types: Pywbem does not support
            reference return types of methods. The CIM architecture and MOF
            syntax support reference return types, and the CIM-XML protocol
            supports the invocation of methods with reference return types.
            However, CIM-XML does not support the representation of class
            declarations with methods that have reference return types.

            Support for array return types: Pywbem does not support array
            return types of methods, consistent with the CIM architecture,
            MOF syntax and CIM-XML.

          parameters (:term:`parameters input object`):
            Parameter declarations for the method.

          class_origin (:term:`string`):
            The CIM class origin of the method (the name
            of the most derived class that defines or overrides the method in
            the class hierarchy of the class owning the method).

            `None` means that class origin information is not available, and
            the :attr:`~pywbem.CIMMethod.class_origin` attribute
            will also be `None`.

            The lexical case of the string is preserved. Object comparison and
            hash value calculation are performed case-insensitively.

          propagated (:class:`py:bool`):
            If not `None`, specifies whether the method has been
            propagated from a superclass.

            `None` means that propagation information is not available, and the
            the :attr:`~pywbem.CIMMethod.propagated` attribute
            will also be `None`.

          qualifiers (:term:`qualifiers input object`):
            The qualifiers for the method.
        """

        if methodname is not None:
            msg = "The 'methodname' init parameter and attribute of " \
                "CIMMethod is deprecated; use 'name' instead."
            if DEBUG_WARNING_ORIGIN:
                msg += "\nTraceback:\n" + ''.join(traceback.format_stack())
            warnings.warn(msg, DeprecationWarning,
                          stacklevel=_stacklevel_above_module(__name__))

            if name is not None:
                raise ValueError("CIMMethod 'name' and 'methodname' "
                                 "parameters cannot be specified both")
            name = methodname

        # We use the respective setter methods:
        self.name = name
        self.return_type = return_type
        self.parameters = parameters
        self.class_origin = class_origin
        self.propagated = propagated
        self.qualifiers = qualifiers

    @property
    def name(self):
        """
        :term:`unicode string`: Name of this CIM method.

        Will not be `None`.

        This attribute is settable. For details, see the description of the
        same-named init parameter of
        :class:`this class <pywbem.CIMMethod>`.
        """
        return self._name

    @name.setter
    def name(self, name):
        """Setter method; for a description see the getter method."""

        # pylint: disable=attribute-defined-outside-init
        self._name = _ensure_unicode(name)

        # We perform this check after the initialization to avoid errors
        # in test tools that show the object with repr().
        if name is None:
            raise ValueError("CIMMethod 'name' parameter must not be None")

    @property
    def return_type(self):
        """
        :term:`unicode string`: Name of the CIM data type of the return type of
        this CIM method.

        Example: ``"uint32"``

        Will not be `None` or ``"reference"``.

        This attribute is settable. For details, see the description of the
        same-named init parameter of
        :class:`this class <pywbem.CIMMethod>`.
        """
        return self._return_type

    @return_type.setter
    def return_type(self, return_type):
        """Setter method; for a description see the getter method."""

        return_type = _ensure_unicode(return_type)

        # We perform this check after the initialization to avoid errors
        # in test tools that show the object with repr().
        if return_type not in ALL_CIMTYPES:
            raise ValueError(
                _format("Invalid CIM type: {0}", return_type))
        if return_type == 'reference':
            raise ValueError("Method cannot have a reference return type")

        # pylint: disable=attribute-defined-outside-init
        self._return_type = return_type

    @property
    def class_origin(self):
        """
        :term:`unicode string`: The class origin of this CIM method,
        identifying the most derived class that defines or overrides the
        method in the class hierarchy of the class owning the method.

        `None` means that class origin information is not available.

        This attribute is settable. For details, see the description of the
        same-named init parameter of
        :class:`this class <pywbem.CIMMethod>`.
        """
        return self._class_origin

    @class_origin.setter
    def class_origin(self, class_origin):
        """Setter method; for a description see the getter method."""
        # pylint: disable=attribute-defined-outside-init
        self._class_origin = _ensure_unicode(class_origin)

    @property
    def propagated(self):
        """
        :class:`py:bool`: Boolean indicating that this CIM method has been
        propagated from a superclass.

        `None` means that propagation information is not available.

        This attribute is settable. For details, see the description of the
        same-named init parameter of
        :class:`this class <pywbem.CIMMethod>`.
        """
        return self._propagated

    @propagated.setter
    def propagated(self, propagated):
        """Setter method; for a description see the getter method."""
        # pylint: disable=attribute-defined-outside-init
        self._propagated = _ensure_bool(propagated)

    @property
    def parameters(self):
        """
        `NocaseDict`_: Parameters of this CIM method.

        Will not be `None`.

        Each dictionary item specifies one parameter, with:

        * key (:term:`unicode string`): Parameter name. Its lexical case was
          preserved.

        * value (:class:`~pywbem.CIMParameter`): Parameter declaration.

        The order of parameters in the method is preserved.

        This attribute is settable; setting it will cause the current
        parameters to be replaced with the new parameters. For details, see
        the description of the same-named init parameter of
        :class:`this class <pywbem.CIMMethod>`.

        The parameters can also be accessed and manipulated one by one
        because the attribute value is a modifiable dictionary. The provided
        input value must be a :class:`~pywbem.CIMParameter` object::

            meth = CIMMethod(...)
            p1 = CIMParameter('p1', ...)  # must be a CIMParameter

            meth.parameters['p1'] = p1  # Set "p1" to p1 (add if needed)
            p1 = meth.parameters['p1']  # Access "p1"
            del meth.parameters['p1']  # Delete "p1" from the class
        """
        return self._parameters

    @parameters.setter
    def parameters(self, parameters):
        """Setter method; for a description see the getter method."""
        # pylint: disable=attribute-defined-outside-init
        self._parameters = NocaseDict()
        if parameters:
            try:
                # This is used for iterables:
                iterator = parameters.items()
            except AttributeError:
                # This is used for dictionaries:
                iterator = parameters
            for item in iterator:
                if isinstance(item, CIMParameter):
                    key = item.name
                    value = item
                elif isinstance(item, tuple):
                    key, value = item
                else:
                    raise TypeError(
                        _format("Input object for parameters has invalid item "
                                "in iterable: {0!A}", item))
                self.parameters[key] = value

    @property
    def qualifiers(self):
        """
        `NocaseDict`_: Qualifiers (qualifier values) of this CIM method.

        Will not be `None`.

        Each dictionary item specifies one qualifier value, with:

        * key (:term:`unicode string`): Qualifier name. Its lexical case was
          preserved.

        * value (:class:`~pywbem.CIMQualifier`): Qualifier value.

        The order of qualifiers in the method is preserved.

        This attribute is settable; setting it will cause the current
        qualifiers to be replaced with the new qualifiers. For details, see
        the description of the same-named init parameter of
        :class:`this class <pywbem.CIMMethod>`.

        The qualifier values can also be accessed and manipulated one by one
        because the attribute value is a modifiable dictionary. The provided
        input value may be specified as a :term:`CIM data type` or as a
        :class:`~pywbem.CIMQualifier` object::

            meth = CIMMethod(...)
            q1 = "..."  # may be CIM data type or CIMQualifier

            meth.qualifiers['q1'] = q1  # Set "q1" to q1 (add if needed)
            q1 = meth.qualifiers['q1']  # Access "q1"
            del meth.qualifiers['q1']  # Delete "q1" from the class
        """
        return self._qualifiers

    @qualifiers.setter
    def qualifiers(self, qualifiers):
        """Setter method; for a description see the getter method."""
        # We make sure that the dictionary is a NocaseDict object, and that the
        # property values are CIMQualifier objects:
        # pylint: disable=attribute-defined-outside-init
        self._qualifiers = NocaseDict()
        if qualifiers:
            try:
                # This is used for iterables:
                iterator = qualifiers.items()
            except AttributeError:
                # This is used for dictionaries:
                iterator = qualifiers
            for item in iterator:
                if isinstance(item, CIMQualifier):
                    key = item.name
                    value = item
                elif isinstance(item, tuple):
                    key, value = item
                else:
                    raise TypeError(
                        _format("Input object for qualifiers has invalid item "
                                "in iterable: {0!A}", item))
                self.qualifiers[key] = _cim_qualifier(key, value)

    def _cmp(self, other):
        """
        Comparator function for two :class:`~pywbem.CIMMethod` objects.

        The comparison is based on their public attributes, in descending
        precedence:

        * `name`
        * `qualifiers`
        * `parameters`
        * `return_type`
        * `class_origin`
        * `propagated`

        The comparison takes into account any case insensitivities described
        for these attributes.
        """
        if self is other:
            return 0
        try:
            assert isinstance(other, CIMMethod)
        except AssertionError:
            raise TypeError(
                _format("other must be CIMMethod, but is: {0}", type(other)))
        return (cmpname(self.name, other.name) or
                cmpdict(self.qualifiers, other.qualifiers) or
                cmpdict(self.parameters, other.parameters) or
                cmpitem(self.return_type, other.return_type) or
                cmpname(self.class_origin, other.class_origin) or
                cmpitem(self.propagated, other.propagated))

    def __hash__(self):
        """
        Return a hash value based on the public attributes of this class, taking
        into account any case insensitivities described for these attributes.
        This approach causes this class to be :term:`unchanged-hashable`.
        """
        hashes = (
            _hash_name(self.name),
            _hash_dict(self.qualifiers),
            _hash_dict(self.parameters),
            _hash_item(self.return_type),
            _hash_name(self.class_origin),
            _hash_item(self.propagated),
        )
        return hash(hashes)

    def __str__(self):
        """
        Return a short string representation of this CIM method,
        for human consumption.
        """
        return _format(
            "CIMMethod("
            "name={s.name!A}, "
            "return_type={s.return_type!A}, ...)",
            s=self)

    def __repr__(self):
        """
        Return a string representation of this CIM method,
        that is suitable for debugging.

        The order of parameters and qualifiers will be preserved in the
        result.
        """
        return _format(
            "CIMMethod("
            "name={s.name!A}, "
            "return_type={s.return_type!A}, "
            "class_origin={s.class_origin!A}, "
            "propagated={s.propagated!A}, "
            "parameters={s.parameters!A}, "
            "qualifiers={s.qualifiers!A})",
            s=self)

    def copy(self):
        """
        Return a new :class:`~pywbem.CIMMethod` object that is a copy
        of this CIM method.

        This is a middle-deep copy; any mutable types in attributes except the
        following are copied, so besides these exceptions, modifications of the
        original object will not affect the returned copy, and vice versa. The
        following mutable types are not copied and are therefore shared between
        original and copy:

        * The :class:`~pywbem.CIMParameter` objects in the
          :attr:`~pywbem.CIMMethod.parameters` dictionary (but not the
          dictionary object itself)
        * The :class:`~pywbem.CIMQualifier` objects in the
          :attr:`~pywbem.CIMMethod.qualifiers` dictionary (but not the
          dictionary object itself)

        Note that the Python functions :func:`py:copy.copy` and
        :func:`py:copy.deepcopy` can be used to create completely shallow or
        completely deep copies of objects of this class.
        """
        return CIMMethod(
            self.name,
            return_type=self.return_type,
            class_origin=self.class_origin,
            propagated=self.propagated,
            parameters=self.parameters,  # setter copies
            qualifiers=self.qualifiers)  # setter copies

    def tocimxml(self):
        """
        Return the CIM-XML representation of this CIM method,
        as an object of an appropriate subclass of :term:`Element`.

        The returned CIM-XML representation is a `METHOD` element consistent
        with :term:`DSP0201`.

        The order of parameters and qualifiers in the returned CIM-XML
        representation is preserved from the :class:`~pywbem.CIMMethod` object.

        Returns:

          The CIM-XML representation, as an object of an appropriate subclass
          of :term:`Element`.
        """
        return cim_xml.METHOD(
            self.name,
            parameters=[p.tocimxml() for p in self.parameters.values()],
            return_type=self.return_type,
            class_origin=self.class_origin,
            propagated=self.propagated,
            qualifiers=[q.tocimxml() for q in self.qualifiers.values()])

    def tocimxmlstr(self, indent=None):
        """
        Return the CIM-XML representation of this CIM method,
        as a :term:`unicode string`.

        *New in pywbem 0.9.*

        For the returned CIM-XML representation, see
        :meth:`~pywbem.CIMMethod.tocimxml`.

        Parameters:

          indent (:term:`string` or :term:`integer`):
            `None` indicates that a single-line version of the XML should be
            returned, without any whitespace between the XML elements.

            Other values indicate that a prettified, multi-line version of the
            XML should be returned. A string value specifies the indentation
            string to be used for each level of nested XML elements. An integer
            value specifies an indentation string of so many blanks.

        Returns:

            The CIM-XML representation of the object, as a
            :term:`unicode string`.
        """
        xml_elem = self.tocimxml()
        return tocimxmlstr(xml_elem, indent)

    def tomof(self, indent=0, maxline=MAX_MOF_LINE):
        """
        Return a MOF string with the declaration of this CIM method for use in
        a CIM class declaration.

        The order of parameters and qualifiers is preserved.

        Parameters:

          indent (:term:`integer`): Number of spaces to indent each line of
            the returned string, counted in the line with the method name.

        Returns:

          :term:`unicode string`: MOF string.
        """

        mof = []

        if self.qualifiers:
            mof.append(_qualifiers_tomof(self.qualifiers, indent + MOF_INDENT,
                                         maxline))

        mof.append(_indent_str(indent))
        # return_type is ensured not to be None or reference
        mof.append(moftype(self.return_type, None))
        mof.append(u' ')
        mof.append(self.name)

        if self.parameters.values():
            mof.append(u'(\n')

            mof_parms = []
            for p in self.parameters.itervalues():
                mof_parms.append(p.tomof(indent + MOF_INDENT, maxline))
            mof.append(u',\n'.join(mof_parms))

            mof.append(u');\n')
        else:
            mof.append(u'();\n')

        return u''.join(mof)


class CIMParameter(_CIMComparisonMixin):
    """
    A CIM parameter (value or declaration).

    This object can be used as parameter value in the
    :meth:`~pywbem.WBEMConnection.InvokeMethod` operation, and as a parameter
    declaration in a :class:`~pywbem.CIMMethod` object.

    For parameter values in method invocations:

      * The `value` attribute is the actual value of the parameter.
      * Qualifiers are not allowed.

    For parameter declarations in method declarations:

      * The `value` attribute is ignored.
      * Qualifiers are allowed.

    Scalar (=non-array) parameters and items in array parameters may have a
    value of NULL (= `None`), any primitive CIM data type, reference type, or
    string type with embedded instance or embedded object.

    Two objects of this class compare equal if their public attributes compare
    equal. Objects of this class are :term:`unchanged-hashable`, with the hash
    value being based on its public attributes. Therefore, objects of this
    class can be used as members in a set (or as dictionary keys) only during
    periods in which their public attributes remain unchanged.
    """

    # pylint: disable=too-many-arguments
    def __init__(self, name, type, reference_class=None, is_array=None,
                 array_size=None, qualifiers=None, value=None,
                 embedded_object=None):
        # pylint: disable=redefined-builtin
        """
        The init method stores the input parameters as-is and does
        not infer unspecified parameters from the others
        (like :class:`~pywbem.CIMProperty` does).

        Parameters:

          name (:term:`string`):
            Name of this CIM parameter.

            Must not be `None`.

            The lexical case of the string is preserved. Object comparison and
            hash value calculation are performed case-insensitively.

          type (:term:`string`):
            Name of the CIM data type of this CIM parameter.

            Example: ``"uint8"``

            Must not be `None`.

            :exc:`~py:exceptions.ValueError` is raised if the type is `None` or
            not a valid CIM data type (see :ref:`CIM data types`).

          reference_class (:term:`string`):
            For reference parameters, the name of the class referenced by the
            parameter, or `None` indicating that the referenced class is
            unspecified.

            For non-reference parameters, must be `None`.

            The lexical case of the string is preserved. Object comparison and
            hash value calculation are performed case-insensitively.

          is_array (:class:`py:bool`):
            A boolean indicating whether the parameter is an array (`True`) or a
            scalar (`False`).

            If `None`, the
            :attr:`~pywbem.CIMParameter.is_array` attribute
            will be inferred from the `value` parameter.
            If the `value` parameter is `None`, a scalar is assumed.

          array_size (:term:`integer`):
            The size of the array parameter, for fixed-size arrays.

            `None` means that the array parameter has variable size, and the
            :attr:`~pywbem.CIMParameter.array_size` attribute
            will also be `None`.

          qualifiers (:term:`qualifiers input object`):
            The qualifiers for the parameter.

          value:
            The value of the CIM method parameter for the method invocation.
            Has no meaning for parameter declarations.

            The specified value will be converted to a :term:`CIM data type`
            using the rules documented in the description of
            :func:`~pywbem.cimvalue`, taking into account the `type` parameter.

          embedded_object (:term:`string`):
            A string value indicating the kind of embedded object represented
            by the parameter value (i.e. the `value` parameter). Has no meaning
            for parameter declarations.

            For details about the possible values, see the corresponding
            attribute.

            `None` means that the value is unspecified, causing the same-named
            attribute in the :class:`~pywbem.CIMParameter` object to be
            inferred from the parameter value (i.e. the `value` parameter). An
            exception is raised if it cannot be inferred.

            `False` means the parameter value is not an embedded object, and
            is stored as `None`.
        """

        # We use the respective setter methods:
        self.name = name

        if is_array is None:
            is_array = _infer_is_array(value)
        else:
            # For performance reasons, we check only if not inferred.
            # This leaves the incorrect combination of is_array=False and
            # array_size=5 undetected, which seems acceptable because
            # array_size is ignored anyway when is_array=False.
            _check_array_parms(is_array, array_size, value, "parameter", name)

        if embedded_object is None:
            embedded_object = _infer_embedded_object(value)

        if embedded_object:
            _check_embedded_object(embedded_object, type, value,
                                   "parameter", name)

        # We use the respective setter methods:
        self.type = type
        self.reference_class = reference_class
        self.is_array = is_array
        self.array_size = array_size
        self.qualifiers = qualifiers
        self.value = value  # value setter relies on self.type being set
        self.embedded_object = embedded_object

    @property
    def name(self):
        """
        :term:`unicode string`: Name of this CIM parameter.

        Will not be `None`.

        This attribute is settable. For details, see the description of the
        same-named init parameter of
        :class:`this class <pywbem.CIMParameter>`.
        """
        return self._name

    @name.setter
    def name(self, name):
        """Setter method; for a description see the getter method."""

        # pylint: disable=attribute-defined-outside-init
        self._name = _ensure_unicode(name)

        # We perform this check after the initialization to avoid errors
        # in test tools that show the object with repr().
        if name is None:
            raise ValueError("CIMParameter 'name' parameter must not be None")

    @property
    def type(self):
        """
        :term:`unicode string`: Name of the CIM data type of this CIM
        parameter.

        Example: ``"uint8"``

        Will not be `None`.

        This attribute is settable. For details, see the description of the
        same-named init parameter of
        :class:`this class <pywbem.CIMParameter>`.
        """
        return self._type

    @type.setter
    def type(self, type):
        # pylint: disable=redefined-builtin
        """Setter method; for a description see the getter method."""

        type = _ensure_unicode(type)

        # We perform this check after the initialization to avoid errors
        # in test tools that show the object with repr().
        if type not in ALL_CIMTYPES:
            raise ValueError(
                _format("Invalid CIM type: {0}", type))

        # pylint: disable=attribute-defined-outside-init
        self._type = type

    @property
    def reference_class(self):
        """
        :term:`unicode string`: The name of the class referenced by this CIM
        reference parameter.

        Will be `None` for non-reference parameters or if the referenced class
        is unspecified in reference parameters.

        This attribute is settable. For details, see the description of the
        same-named init parameter of
        :class:`this class <pywbem.CIMParameter>`.
        """
        return self._reference_class

    @reference_class.setter
    def reference_class(self, reference_class):
        """Setter method; for a description see the getter method."""
        # pylint: disable=attribute-defined-outside-init
        self._reference_class = _ensure_unicode(reference_class)

    @property
    def is_array(self):
        """
        :class:`py:bool`: Boolean indicating that this CIM parameter
        is an array (as opposed to a scalar).

        Will not be `None`.

        This attribute is settable. For details, see the description of the
        same-named init parameter of
        :class:`this class <pywbem.CIMParameter>`.
        """
        return self._is_array

    @is_array.setter
    def is_array(self, is_array):
        """Setter method; for a description see the getter method."""
        # pylint: disable=attribute-defined-outside-init
        self._is_array = _ensure_bool(is_array)

    @property
    def array_size(self):
        """
        :term:`integer`: The size of the fixed-size array of this CIM
        parameter.

        `None` means that the array has variable size, or that the
        parameter is a scalar.

        This attribute is settable. For details, see the description of the
        same-named init parameter of
        :class:`this class <pywbem.CIMParameter>`.
        """
        return self._array_size

    @array_size.setter
    def array_size(self, array_size):
        """Setter method; for a description see the getter method."""
        # pylint: disable=attribute-defined-outside-init
        self._array_size = array_size

    @property
    def qualifiers(self):
        """
        `NocaseDict`_: Qualifiers (qualifier values) of this CIM parameter.

        Will not be `None`.

        Each dictionary item specifies one qualifier value, with:

        * key (:term:`unicode string`): Qualifier name. Its lexical case was
          preserved.

        * value (:class:`~pywbem.CIMQualifier`): Qualifier value.

        The order of qualifiers in the parameter is preserved.

        This attribute is settable; setting it will cause the current
        qualifiers to be replaced with the new qualifiers. For details, see
        the description of the same-named init parameter of
        :class:`this class <pywbem.CIMParameter>`.

        The qualifier values can also be accessed and manipulated one by one
        because the attribute value is a modifiable dictionary. The provided
        input value may be specified as a :term:`CIM data type` or as a
        :class:`~pywbem.CIMQualifier` object::

            parm = CIMParameter(...)
            q1 = True  # may be CIM data type or CIMQualifier

            parm.qualifiers['q1'] = q1  # Set "q1" to q1 (add if needed)
            q1 = parm.qualifiers['q1']  # Access "q1"
            del parm.qualifiers['q1']  # Delete "q1" from the class
        """
        return self._qualifiers

    @qualifiers.setter
    def qualifiers(self, qualifiers):
        """Setter method; for a description see the getter method."""
        # We make sure that the dictionary is a NocaseDict object, and that the
        # property values are CIMQualifier objects:
        # pylint: disable=attribute-defined-outside-init
        self._qualifiers = NocaseDict()
        if qualifiers:
            try:
                # This is used for iterables:
                iterator = qualifiers.items()
            except AttributeError:
                # This is used for dictionaries:
                iterator = qualifiers
            for item in iterator:
                if isinstance(item, CIMQualifier):
                    key = item.name
                    value = item
                elif isinstance(item, tuple):
                    key, value = item
                else:
                    raise TypeError(
                        _format("Input object for qualifiers has invalid item "
                                "in iterable: {0!A}", item))
                self.qualifiers[key] = _cim_qualifier(key, value)

    @property
    def value(self):
        """
        The value of this CIM parameter for the method invocation.

        Has no meaning for parameter declarations.

        This attribute is settable. For details, see the description of the
        same-named init parameter of
        :class:`this class <pywbem.CIMParameter>`.
        """
        return self._value

    @value.setter
    def value(self, value):
        """Setter method; for a description see the getter method."""
        # pylint: disable=attribute-defined-outside-init
        self._value = cimvalue(value, self.type)

    @property
    def embedded_object(self):
        """
        :term:`unicode string`: A string value indicating the kind of embedded
        object represented by this CIM parameter value.

        Has no meaning for CIM parameter declarations.

        The following values are defined for this parameter:

        * ``"instance"``: The parameter is declared with the
          ``EmbeddedInstance`` qualifier, indicating that the parameter
          value is an embedded instance of the class specified as the value
          of the ``EmbeddedInstance`` qualifier.
          The property value must be a :class:`~pywbem.CIMInstance` object,
          or `None`.
        * ``"object"``: The parameter is declared with the
          ``EmbeddedObject`` qualifier, indicating that the parameter
          value is an embedded object (instance or class) of which the
          class name is not known.
          The parameter value must be a :class:`~pywbem.CIMInstance` or
          :class:`~pywbem.CIMClass` object, or `None`.
        * `None`, for parameters not representing embedded objects.

        This attribute is settable. For details, see the description of the
        same-named init parameter of
        :class:`this class <pywbem.CIMParameter>`.
        """
        return self._embedded_object

    @embedded_object.setter
    def embedded_object(self, embedded_object):
        """Setter method; for a description see the getter method."""
        # pylint: disable=attribute-defined-outside-init
        if embedded_object is False:
            self._embedded_object = None
        else:
            self._embedded_object = _ensure_unicode(embedded_object)

    def _cmp(self, other):
        """
        Comparator function for two :class:`~pywbem.CIMParameter` objects.

        The comparison is based on their public attributes, in descending
        precedence:

        * `name`
        * `type`
        * `reference_class`
        * `is_array`
        * `array_size`
        * `qualifiers`
        * `value`
        * `embedded_object`

        The comparison takes into account any case insensitivities described
        for these attributes.

        Raises `TypeError', if the `other` object is not a
        :class:`~pywbem.CIMParameter` object.
        """

        if self is other:
            return 0
        try:
            assert isinstance(other, CIMParameter)
        except AssertionError:
            raise TypeError(
                _format("other must be CIMParameter, but is: {0}",
                        type(other)))
        return (cmpname(self.name, other.name) or
                cmpitem(self.type, other.type) or
                cmpname(self.reference_class, other.reference_class) or
                cmpitem(self.is_array, other.is_array) or
                cmpitem(self.array_size, other.array_size) or
                cmpdict(self.qualifiers, other.qualifiers) or
                cmpitem(self.value, other.value) or
                cmpitem(self.embedded_object, other.embedded_object))

    def __hash__(self):
        """
        Return a hash value based on the public attributes of this class, taking
        into account any case insensitivities described for these attributes.
        This approach causes this class to be :term:`unchanged-hashable`.
        """
        hashes = (
            _hash_name(self.name),
            _hash_item(self.type),
            _hash_name(self.reference_class),
            _hash_item(self.is_array),
            _hash_item(self.array_size),
            _hash_dict(self.qualifiers),
            _hash_item(self.value),
            _hash_item(self.embedded_object),
        )
        return hash(hashes)

    def __str__(self):
        """
        Return a short string representation of this CIM parameter,
        for human consumption.
        """
        return _format(
            "CIMParameter("
            "name={s.name!A}, "
            "type={s.type!A}, "
            "reference_class={s.reference_class!A}, "
            "is_array={s.is_array!A}, ...)",
            s=self)

    def __repr__(self):
        """
        Return a string representation of this CIM parameter,
        that is suitable for debugging.

        The order of qualifiers will be preserved in the result.
        """
        return _format(
            "CIMParameter("
            "name={s.name!A}, "
            "type={s.type!A}, "
            "reference_class={s.reference_class!A}, "
            "is_array={s.is_array!A}, "
            "array_size={s.array_size!A}, "
            "qualifiers={s.qualifiers!A}, "
            "value={s.value!A}, "
            "embedded_object={s.embedded_object!A})",
            s=self)

    def copy(self):
        """
        Return a new :class:`~pywbem.CIMParameter` object that is a copy
        of this CIM parameter.

        This is a middle-deep copy; any mutable types in attributes except the
        following are copied, so besides these exceptions, modifications of the
        original object will not affect the returned copy, and vice versa. The
        following mutable types are not copied and are therefore shared between
        original and copy:

        * The :class:`~pywbem.CIMQualifier` objects in the
          :attr:`~pywbem.CIMParameter.qualifiers` dictionary (but not the
          dictionary object itself)

        Note that the Python functions :func:`py:copy.copy` and
        :func:`py:copy.deepcopy` can be used to create completely shallow or
        completely deep copies of objects of this class.
        """
        return CIMParameter(
            self.name,
            self.type,
            reference_class=self.reference_class,
            is_array=self.is_array,
            array_size=self.array_size,
            value=self.value,
            embedded_object=self.embedded_object,
            qualifiers=self.qualifiers)  # setter copies

    def tocimxml(self, as_value=False):
        """
        Return the CIM-XML representation of this CIM parameter,
        as an object of an appropriate subclass of :term:`Element`.

        The returned CIM-XML representation can be created
        either as a parameter declaration for use in a method declaration,
        or as a parameter value for use in a method invocation.

        If a parameter value is to be returned, the returned CIM-XML
        representation is a `PARAMVALUE` element with child elements dependent
        on the parameter type, and consistent with :term:`DSP0201`.

        If a parameter declaration is to be returned, the returned CIM-XML
        representation is a `PARAMETER`, `PARAMETER.REFERENCE`,
        `PARAMETER.ARRAY`, or `PARAMETER.REFARRAY` element dependent on the
        parameter type, and consistent with :term:`DSP0201`.

        The order of qualifiers in the returned CIM-XML representation of a
        parameter declaration is preserved from the
        :class:`~pywbem.CIMParameter` object.

        Parameters:

          as_value (bool): If `True`, return the object as a parameter value.
            Otherwise, return the object as a parameter declaration.

        Returns:

          The CIM-XML representation, as an object of an appropriate subclass
          of :term:`Element`.
        """

        if as_value:  # pylint: disable=no-else-return

            if self.value is None:
                value_xml = None

            elif self.is_array:
                if self.type == 'reference':

                    array_xml = []
                    for v in self.value:
                        if v is None:
                            if SEND_VALUE_NULL:
                                array_xml.append(cim_xml.VALUE_NULL())
                            else:
                                array_xml.append(cim_xml.VALUE(None))
                        else:
                            array_xml.append(
                                cim_xml.VALUE_REFERENCE(v.tocimxml()))
                    value_xml = cim_xml.VALUE_REFARRAY(array_xml)

                else:  # array non-reference

                    array_xml = []
                    for v in self.value:
                        if v is None:
                            if SEND_VALUE_NULL:
                                array_xml.append(cim_xml.VALUE_NULL())
                            else:
                                array_xml.append(cim_xml.VALUE(None))
                        elif self.embedded_object is not None:
                            array_xml.append(
                                cim_xml.VALUE(v.tocimxml().toxml()))
                        else:
                            array_xml.append(
                                cim_xml.VALUE(atomic_to_cim_xml(v)))
                    value_xml = cim_xml.VALUE_ARRAY(array_xml)

            else:  # scalar

                if self.type == 'reference':
                    value_xml = cim_xml.VALUE_REFERENCE(self.value.tocimxml())
                elif self.embedded_object is not None:
                    value_xml = cim_xml.VALUE(self.value.tocimxml().toxml())
                else:
                    value_xml = cim_xml.VALUE(atomic_to_cim_xml(self.value))

            return cim_xml.PARAMVALUE(
                self.name,
                value_xml,
                paramtype=self.type,
                embedded_object=self.embedded_object)

        else:  # as declaration

            qualifiers = [q.tocimxml() for q in self.qualifiers.values()]

            if self.is_array:  # pylint: disable=no-else-return

                if self.array_size is None:
                    array_size = None
                else:
                    array_size = str(self.array_size)

                if self.type == 'reference':
                    return cim_xml.PARAMETER_REFARRAY(
                        self.name,
                        self.reference_class,
                        array_size,
                        qualifiers=qualifiers)

                # For non-reference array types:
                return cim_xml.PARAMETER_ARRAY(
                    self.name,
                    self.type,
                    array_size,
                    qualifiers=qualifiers)

            else:  # scalar

                if self.type == 'reference':
                    return cim_xml.PARAMETER_REFERENCE(
                        self.name,
                        self.reference_class,
                        qualifiers=qualifiers)

                # For non-reference types:
                return cim_xml.PARAMETER(
                    self.name,
                    self.type,
                    qualifiers=qualifiers)

    def tocimxmlstr(self, indent=None, as_value=False):
        """
        Return the CIM-XML representation of this CIM parameter,
        as a :term:`unicode string`.

        *New in pywbem 0.9.*

        The returned CIM-XML representation can be created
        either as a parameter declaration for use in a method declaration,
        or as a parameter value for use in a method invocation.

        For the returned CIM-XML representation, see
        :meth:`~pywbem.CIMParameter.tocimxml`.

        Parameters:

          indent (:term:`string` or :term:`integer`):
            `None` indicates that a single-line version of the XML should be
            returned, without any whitespace between the XML elements.

            Other values indicate that a prettified, multi-line version of the
            XML should be returned. A string value specifies the indentation
            string to be used for each level of nested XML elements. An integer
            value specifies an indentation string of so many blanks.

          as_value (bool): If `True`, return the object as a parameter value.
            Otherwise, return the object as a parameter declaration.

        Returns:

            The CIM-XML representation of the object, as a
            :term:`unicode string`.
        """
        xml_elem = self.tocimxml(as_value)
        return tocimxmlstr(xml_elem, indent)

    def tomof(self, indent=0, maxline=MAX_MOF_LINE):
        """
        Return a MOF string with the declaration of this CIM parameter for use
        in a CIM method declaration.

        The object is always interpreted as a parameter declaration; so the
        :attr:`~pywbem.CIMParameter.value` and
        :attr:`~pywbem.CIMParameter.embedded_object` attributes are ignored.

        The order of qualifiers is preserved.

        Parameters:

          indent (:term:`integer`): Number of spaces to indent each line of
            the returned string, counted in the line with the parameter name.

        Returns:

          :term:`unicode string`: MOF string.
        """

        mof = []

        if self.qualifiers:
            mof.append(_qualifiers_tomof(self.qualifiers, indent + MOF_INDENT,
                                         maxline))

        mof.append(_indent_str(indent))
        mof.append(moftype(self.type, self.reference_class))
        mof.append(u' ')
        mof.append(self.name)

        if self.is_array:
            mof.append(u'[')
            if self.array_size is not None:
                mof.append(six.text_type(self.array_size))
            mof.append(u']')

        return u''.join(mof)


# pylint: disable=too-many-instance-attributes
class CIMQualifier(_CIMComparisonMixin):
    """
    A CIM qualifier value.

    A qualifier represents metadata on a class, method, property, etc., and
    specifies information such as a documentation string or whether a property
    is a key.

    :class:`~pywbem.CIMQualifier` objects can be used to represent the qualifier
    values that are specified on a CIM element (e.g. on a CIM class). In that
    case, the :attr:`propagated` property is always `False`, and the effective
    values of applicable but unspecified qualifiers need to be determined by
    users, by considering the default value of the corresponding qualifier type,
    the propagation and override flavors of the qualifier, and the qualifier
    values that have been specified in the class ancestry of the CIM element in
    question.

    :class:`~pywbem.CIMQualifier` objects can also be used to represent the
    effective values of all applicable qualifiers on a CIM element, including
    those that have not been specified, e.g. in the MOF declaration of the CIM
    element. In this case, the :class:`CIMQualifier` objects for qualifier
    values that are specified in MOF represent the specified values, and their
    :attr:`propagated` property is `False`. The :class:`CIMQualifier` objects
    for qualifier values that are not specified in MOF represent the effective
    values, and their :attr:`propagated` property is `True`.

    Whether a set of :class:`CIMQualifier` objects on a CIM object represents
    just the specified qualifiers or all applicable qualifiers needs to be known
    from the context.

    :class:`~pywbem.CIMQualifier` has properties that represent qualifier
    flavors (:attr:`tosubclass`, :attr:`toinstance`, :attr:`overridable`, and
    :attr:`translatable`). If any of these flavor properties is not `None`, the
    qualifier value represented by the :class:`~pywbem.CIMQualifier` object
    implicitly defines a qualifier type. Implicitly defined qualifier types have
    been deprecated in :term:`DSP0004`. The implicitly defined qualifier type is
    conceptual and is not materialized as a
    :class:`~pywbem.CIMQualifierDeclaration` object.

    Two objects of this class compare equal if their public attributes compare
    equal. Objects of this class are :term:`unchanged-hashable`, with the hash
    value being based on its public attributes. Therefore, objects of this
    class can be used as members in a set (or as dictionary keys) only during
    periods in which their public attributes remain unchanged.
    """

    # pylint: disable=too-many-arguments
    def __init__(self, name, value, type=None, propagated=None,
                 overridable=None, tosubclass=None, toinstance=None,
                 translatable=None):
        # pylint: disable=redefined-builtin
        """
        The init method infers optional parameters that are not specified (for
        example, it infers `type` from the Python type of `value` and other
        information). If the specified parameters are inconsistent, an
        exception is raised. If an optional parameter is needed for some reason,
        an exception is raised.

        Parameters:

          name (:term:`string`):
            Name of the qualifier.

            Must not be `None`.

            The lexical case of the string is preserved. Object comparison and
            hash value calculation are performed case-insensitively.

          value (:term:`CIM data type` or other suitable types):
            Value of the qualifier.

            `None` means that the qualifier is Null, and the same-named
            attribute in the :class:`~pywbem.CIMQualifier` object will also be
            `None`.

            The specified value will be converted to a :term:`CIM data type`
            using the rules documented in the description of
            :func:`~pywbem.cimvalue`, taking into account the `type` parameter.

          type (:term:`string`):
            Name of the CIM data type of the qualifier (e.g. ``"uint8"``).

            `None` will cause the type to be inferred from the `value`
            parameter, raising :exc:`~py:exceptions.ValueError` if it cannot be
            inferred (for example when `value` is `None` or a Python integer).

            :exc:`~py:exceptions.ValueError` is raised if the type is not a
            valid CIM data type (see :ref:`CIM data types`).

          propagated (:class:`py:bool`):
            If not `None`, specifies whether the qualifier value has been
            propagated from a superclass.

            `None` means that this information is not available, and the
            :attr:`~pywbem.CIMQualifier.propagated` attribute
            will also be `None`.

          overridable (:class:`py:bool`):
            If not `None`, specifies whether the qualifier value is overridable
            in subclasses.

            `None` means that this information is not available, and the
            :attr:`~pywbem.CIMQualifier.overridable` attribute
            will also be `None`.

          tosubclass (:class:`py:bool`):
            If not `None`, specifies whether the qualifier value propagates
            to subclasses.

            `None` means that this information is not available, and the
            :attr:`~pywbem.CIMQualifier.tosubclass` attribute
            will also be `None`.

          toinstance (:class:`py:bool`):
            If not `None`, specifies whether the qualifier value propagates
            to instances.

            `None` means that this information is not available, and the
            :attr:`~pywbem.CIMQualifier.toinstance` attribute
            will also be `None`.

            Note that :term:`DSP0200` has deprecated the presence of qualifier
            values on CIM instances.

          translatable (:class:`py:bool`):
            If not `None`, specifies whether the qualifier is translatable.

            `None` means that this information is not available, and the
            :attr:`~pywbem.CIMQualifier.translatable` attribute
            will also be `None`.

        Examples:

        ::

            # a string qualifier:
            CIMQualifier("MyString", "abc")

            # a uint8 qualifier:
            CIMQualifier("MyNum", 42, "uint8")

            # a uint8 qualifier:
            CIMQualifier("MyNum", Uint8(42))

            # a uint8 array qualifier:
            CIMQualifier("MyNumArray", [1, 2, 3], "uint8")

            # a string qualifier that is Null:
            CIMQualifier("MyString", None, "string")

            # a uint8 qualifier that is Null:
            CIMQualifier("MyNum", None, "uint8")
        """

        # We use the respective setter methods:
        self.name = name

        if type is None:
            type = _infer_type(value, "qualifier", name)

        # We use the respective setter methods:
        self.type = type
        self.value = value  # value setter relies on self.type being set
        self.propagated = propagated
        self.overridable = overridable
        self.tosubclass = tosubclass
        self.toinstance = toinstance
        self.translatable = translatable

    @property
    def name(self):
        """
        :term:`unicode string`: Name of this CIM qualifier.

        Will not be `None`.

        This attribute is settable. For details, see the description of the
        same-named init parameter of
        :class:`this class <pywbem.CIMQualifier>`.
        """
        return self._name

    @name.setter
    def name(self, name):
        """Setter method; for a description see the getter method."""

        # pylint: disable=attribute-defined-outside-init
        self._name = _ensure_unicode(name)

        # We perform this check after the initialization to avoid errors
        # in test tools that show the object with repr().
        if name is None:
            raise ValueError("CIMQualifier 'name' parameter must not be None")

    @property
    def type(self):
        """
        :term:`unicode string`: Name of the CIM data type of this CIM
        qualifier.

        Example: ``"uint8"``

        Will not be `None`.

        This attribute is settable. For details, see the description of the
        same-named init parameter of
        :class:`this class <pywbem.CIMQualifier>`.
        """
        return self._type

    @type.setter
    def type(self, type):
        # pylint: disable=redefined-builtin
        """Setter method; for a description see the getter method."""

        type = _ensure_unicode(type)

        # We perform this check after the initialization to avoid errors
        # in test tools that show the object with repr().
        if type not in ALL_CIMTYPES:
            raise ValueError(
                _format("Invalid CIM type: {0}", type))

        # pylint: disable=attribute-defined-outside-init
        self._type = type

    @property
    def value(self):
        """
        :term:`CIM data type`: Value of this CIM qualifier.

        `None` means that the value is Null.

        For CIM data types string and char16, this attribute will be a
        :term:`unicode string`, even when specified as a :term:`byte string`.

        This attribute is settable. For details, see the description of the
        same-named init parameter of
        :class:`this class <pywbem.CIMQualifier>`.
        """
        return self._value

    @value.setter
    def value(self, value):
        """Setter method; for a description see the getter method."""
        # pylint: disable=attribute-defined-outside-init
        self._value = cimvalue(value, self.type)

    @property
    def propagated(self):
        """
        :class:`py:bool`: Boolean indicating that the qualifier value has been
        propagated from a superclass.

        `None` means that propagation information is not available.

        This attribute is settable. For details, see the description of the
        same-named init parameter of
        :class:`this class <pywbem.CIMQualifier>`.
        """
        return self._propagated

    @propagated.setter
    def propagated(self, propagated):
        """Setter method; for a description see the getter method."""
        # pylint: disable=attribute-defined-outside-init
        self._propagated = _ensure_bool(propagated)

    @property
    def tosubclass(self):
        """
        :class:`py:bool`: If not `None`, causes an implicit qualifier type to
        be defined for this qualifier that has the specified flavor.

        If `True`, specifies the ToSubclass flavor (the qualifier value
        propagates to subclasses); if `False` specifies the Restricted flavor
        (the qualifier values does not propagate to subclasses).

        `None` means that this information is not available.

        This attribute is settable. For details, see the description of the
        same-named init parameter of
        :class:`this class <pywbem.CIMQualifier>`.
        """
        return self._tosubclass

    @tosubclass.setter
    def tosubclass(self, tosubclass):
        """Setter method; for a description see the getter method."""
        # pylint: disable=attribute-defined-outside-init
        self._tosubclass = _ensure_bool(tosubclass)

    @property
    def toinstance(self):
        """
        :class:`py:bool`: If not `None`, causes an implicit qualifier type to
        be defined for this qualifier that has the specified flavor.

        If `True` specifies the ToInstance flavor(the qualifier value
        propagates to instances. If `False`, specifies that qualifier values
        do not propagate to instances. There is no flavor corresponding to
        `toinstance=False`.

        `None` means that this information is not available.

        Note that :term:`DSP0200` has deprecated the presence of qualifier
        values on CIM instances.

        This attribute is settable. For details, see the description of the
        same-named init parameter of
        :class:`this class <pywbem.CIMQualifier>`.
        """
        return self._toinstance

    @toinstance.setter
    def toinstance(self, toinstance):
        """Setter method; for a description see the getter method."""
        # pylint: disable=attribute-defined-outside-init
        self._toinstance = _ensure_bool(toinstance)

    @property
    def overridable(self):
        """
        :class:`py:bool`: If not `None`, causes an implicit qualifier type to
        be defined for this qualifier that has the specified flavor.

        If `True`, specifies the  EnableOverride flavor(the qualifier value is
        overridable in subclasses); if `False` specifies the DisableOverride
        flavor(the qualifier value is not overridable in subclasses).

        `None` means that this information is not available.

        This attribute is settable. For details, see the description of the
        same-named init parameter of
        :class:`this class <pywbem.CIMQualifier>`.
        """
        return self._overridable

    @overridable.setter
    def overridable(self, overridable):
        """Setter method; for a description see the getter method."""
        # pylint: disable=attribute-defined-outside-init
        self._overridable = _ensure_bool(overridable)

    @property
    def translatable(self):
        """
        :class:`py:bool`: If not `None`, causes an implicit qualifier type to
        be defined for this qualifier that has the specified flavor.

        If `True`, specifies the Translatable flavor (the qualifier is
        translatable); if `False` specifies that the qualfier is
        not translatable. There is no flavor corresponding to
        translatable=False.

        `None` means that this information is not available.

        This attribute is settable. For details, see the description of the
        same-named init parameter of
        :class:`this class <pywbem.CIMQualifier>`.
        """
        return self._translatable

    @translatable.setter
    def translatable(self, translatable):
        """Setter method; for a description see the getter method."""
        # pylint: disable=attribute-defined-outside-init
        self._translatable = _ensure_bool(translatable)

    def _cmp(self, other):
        """
        Comparator function for two :class:`~pywbem.CIMQualifier` objects.

        The comparison is based on their public attributes, in descending
        precedence:

        * `name`
        * `type`
        * `value`
        * `propagated`
        * `overridable`
        * `tosubclass`
        * `toinstance`
        * `translatable`

        The comparison takes into account any case insensitivities described
        for these attributes.
        """
        if self is other:
            return 0
        try:
            assert isinstance(other, CIMQualifier)
        except AssertionError:
            raise TypeError(
                _format("other must be CIMQualifier, but is: {0}",
                        type(other)))
        return (cmpname(self.name, other.name) or
                cmpitem(self.type, other.type) or
                cmpitem(self.value, other.value) or
                cmpitem(self.propagated, other.propagated) or
                cmpitem(self.overridable, other.overridable) or
                cmpitem(self.tosubclass, other.tosubclass) or
                cmpitem(self.toinstance, other.toinstance) or
                cmpitem(self.translatable, other.translatable))

    def __hash__(self):
        """
        Return a hash value based on the public attributes of this class, taking
        into account any case insensitivities described for these attributes.
        This approach causes this class to be :term:`unchanged-hashable`.
        """
        hashes = (
            _hash_name(self.name),
            _hash_item(self.type),
            _hash_item(self.value),
            _hash_item(self.propagated),
            _hash_item(self.overridable),
            _hash_item(self.tosubclass),
            _hash_item(self.toinstance),
            _hash_item(self.translatable),
        )
        return hash(hashes)

    def __str__(self):
        """
        Return a short string representation of this CIM qualifier,
        for human consumption.
        """
        return _format(
            "CIMQualifier("
            "name={s.name!A}, "
            "value={s.value!A}, "
            "type={s.type!A}, ...)",
            s=self)

    def __repr__(self):
        """
        Return a string representation of this CIM qualifier,
        that is suitable for debugging.
        """
        return _format(
            "CIMQualifier("
            "name={s.name!A}, "
            "value={s.value!A}, "
            "type={s.type!A}, "
            "tosubclass={s.tosubclass!A}, "
            "overridable={s.overridable!A}, "
            "translatable={s.translatable!A}, "
            "toinstance={s.toinstance!A}, "
            "propagated={s.propagated!A})",
            s=self)

    def copy(self):
        """
        Return a new :class:`~pywbem.CIMQualifier` object that is a copy
        of this CIM qualifier.

        Objects of this class have no mutable types in any attributes, so
        modifications of the original object will not affect the returned copy,
        and vice versa.

        Note that the Python functions :func:`py:copy.copy` and
        :func:`py:copy.deepcopy` can be used to create completely shallow or
        completely deep copies of objects of this class.
        """
        return CIMQualifier(
            self.name,
            self.value,
            type=self.type,
            propagated=self.propagated,
            overridable=self.overridable,
            tosubclass=self.tosubclass,
            toinstance=self.toinstance,
            translatable=self.translatable)

    def tocimxml(self):
        """
        Return the CIM-XML representation of this CIM qualifier,
        as an object of an appropriate subclass of :term:`Element`.

        The returned CIM-XML representation is a `QUALIFIER` element consistent
        with :term:`DSP0201`.

        Returns:

          The CIM-XML representation, as an object of an appropriate subclass
          of :term:`Element`.
        """

        if self.value is None:
            value_xml = None

        elif isinstance(self.value, (tuple, list)):
            array_xml = []
            for v in self.value:
                if v is None:
                    if SEND_VALUE_NULL:
                        array_xml.append(cim_xml.VALUE_NULL())
                    else:
                        array_xml.append(cim_xml.VALUE(None))
                else:
                    array_xml.append(cim_xml.VALUE(atomic_to_cim_xml(v)))
            value_xml = cim_xml.VALUE_ARRAY(array_xml)

        else:
            value_xml = cim_xml.VALUE(atomic_to_cim_xml(self.value))

        return cim_xml.QUALIFIER(self.name,
                                 self.type,
                                 value_xml,
                                 propagated=self.propagated,
                                 overridable=self.overridable,
                                 tosubclass=self.tosubclass,
                                 toinstance=self.toinstance,
                                 translatable=self.translatable)

    def tocimxmlstr(self, indent=None):
        """
        Return the CIM-XML representation of this CIM qualifier,
        as a :term:`unicode string`.

        *New in pywbem 0.9.*

        For the returned CIM-XML representation, see
        :meth:`~pywbem.CIMQualifier.tocimxml`.

        Parameters:

          indent (:term:`string` or :term:`integer`):
            `None` indicates that a single-line version of the XML should be
            returned, without any whitespace between the XML elements.

            Other values indicate that a prettified, multi-line version of the
            XML should be returned. A string value specifies the indentation
            string to be used for each level of nested XML elements. An integer
            value specifies an indentation string of so many blanks.

        Returns:

            The CIM-XML representation of the object, as a
            :term:`unicode string`.
        """
        xml_elem = self.tocimxml()
        return tocimxmlstr(xml_elem, indent)

    def tomof(self, indent=MOF_INDENT, maxline=MAX_MOF_LINE, line_pos=0):
        """
        Return a MOF string with the specification of this CIM qualifier
        as a qualifier value.

        The items of array values are tried to keep on the same line. If the
        generated line would exceed the maximum MOF line length, the value is
        split into multiple lines, on array item boundaries, and/or within long
        strings on word boundaries.

        If a string value (of a scalar value, or of an array item) is split
        into multiple lines, the first line of the value is put onto a line on
        its own.

        Parameters:

          indent (:term:`integer`): For a multi-line result, the number of
            spaces to indent each line except the first line (on which the
            qualifier name appears). For a single-line result, ignored.

        Returns:

          :term:`unicode string`: MOF string.
        """

        mof = []

        mof.append(self.name)
        mof.append(u' ')

        if isinstance(self.value, list):
            mof.append(u'{')
        else:
            mof.append(u'(')

        line_pos += len(u''.join(mof))
        # Assume in line_pos that the extra space would be needed
        val_str, line_pos = _value_tomof(
            self.value, self.type, indent, maxline, line_pos + 1, 3, True)
        # Empty arrays are represented as val_str=''
        if val_str and val_str[0] != '\n':
            # The extra space was actually needed
            mof.append(u' ')
        else:
            # Adjust by the extra space that was not needed
            line_pos -= 1
        mof.append(val_str)

        if isinstance(self.value, list):
            mof.append(u' }')
        else:
            mof.append(u' )')

        mof_str = u''.join(mof)
        return mof_str


# pylint: disable=too-many-instance-attributes
class CIMQualifierDeclaration(_CIMComparisonMixin):
    """
    A CIM qualifier type is the declaration of a qualifier and defines the
    attributes of qualifier name, qualifier type, value, scopes, and flavors
    for the qualifier.

    The scope of a qualifer determines the kinds of schema elements on which
    it can be specified.

    Value specifies the default value for the qualifier.

    Flavors specify certain characteristics of the qualifier such as its
    value propagation from the ancestry of the qualified element and its
    translatability.

    Flavors attributes must be specifically set on construction of the
    :class:`CIMQualifierDeclaration` or they will be set to `None`. This
    differs from the DMTF specification :term:`DSP0004` where default values
    are defined as follows:

        - Has the EnableOverride flavor;  ``overridable = True``

        - Has the ToSubClass flavor;  ``tosubclass = True``

        - Does not have theTranslatable flavor; ``translatable = False``

        - Does not have ToInstance flavor;  ``toinstance = False.``
          Not defined in :term:`DSP0004` and deprecated in the DMTF protocol
          specification :term:`DSP0200`

    Because `None` is allowed as a value for the flavors attributes in
    constructing a :class:`CIMQualifierDeclaration`, the user must insure that
    any flavor which has the value `None` is set to its default value if
    required for subsequent processing.

    The pywbem MOF compiler supplies all of the flavor values so that
    those which were not specified in the MOF are set to the DMTF defined
    default values.

    Two objects of this class compare equal if their public attributes compare
    equal. Objects of this class are :term:`unchanged-hashable`, with the hash
    value being based on its public attributes. Therefore, objects of this
    class can be used as members in a set (or as dictionary keys) only during
    periods in which their public attributes remain unchanged.
    """

    # Order of scopes when externalizing the qualifier declaration
    _ordered_scopes = ["CLASS", "ASSOCIATION", "INDICATION",
                       "PROPERTY", "REFERENCE", "METHOD", "PARAMETER",
                       "ANY"]

    # pylint: disable=too-many-arguments
    def __init__(self, name, type, value=None, is_array=False,
                 array_size=None, scopes=None,
                 overridable=None, tosubclass=None, toinstance=None,
                 translatable=None):
        # pylint: disable=redefined-builtin
        """
        Parameters:

          name (:term:`string`):
            Name of the qualifier.

            Must not be `None`.

            The lexical case of the string is preserved. Object comparison and
            hash value calculation are performed case-insensitively.

          type (:term:`string`):
            Name of the CIM data type of the qualifier (e.g. ``"uint8"``).

            Must not be `None`.

            :exc:`~py:exceptions.ValueError` is raised if the type is `None` or
            not a valid CIM data type (see :ref:`CIM data types`).

          value (:term:`CIM data type` or other suitable types):
            Default value of the qualifier.

            `None` means a default value of Null, and the
            :attr:`~pywbem.CIMQualifierDeclaration.value` attribute
            will also be `None`.

            The specified value will be converted to a :term:`CIM data type`
            using the rules documented in the description of
            :func:`~pywbem.cimvalue`, taking into account the `type` parameter.

          is_array (:class:`py:bool`):
            A boolean indicating whether the qualifier is an array (`True`) or
            a scalar (`False`).

            If `None`, the
            :attr:`~pywbem.CIMQualifierDeclaration.is_array` attribute
            will be inferred from the `value` parameter.
            If the `value` parameter is `None`, a scalar is assumed.

          array_size (:term:`integer`):
            The size of the array qualifier, for fixed-size arrays.

            `None` means that the array qualifier has variable size, and the
            :attr:`~pywbem.CIMQualifierDeclaration.array_size` attribute
            will also be `None`.

          scopes (:class:`py:dict` or `NocaseDict`_):
            Scopes of the qualifier.

            A shallow copy of the provided dictionary will be stored in the
            :class:`~pywbem.CIMQualifierDeclaration` object.

            Each dictionary item specifies one scope value, with:

            * key (:term:`string`): Scope name, in upper case.

              Must not be `None`.

            * value (:class:`py:bool`): Scope value, specifying whether the
              qualifier has that scope (i.e. can be applied to a CIM element of
              that kind).

            Valid scope names are "CLASS", "ASSOCIATION", "REFERENCE",
            "PROPERTY", "METHOD", "PARAMETER", "INDICATION", and "ANY".

            `None` is interpreted as an empty set of scopes.

            For details about the dictionary items, see the corresponding
            attribute.

          overridable (:class:`py:bool`):
            If not `None`, defines the flavor that defines whether the
            qualifier value is overridable in subclasses.

            `None` means that this information is not available, and the
            :attr:`~pywbem.CIMQualifierDeclaration.overridable` attribute
            will also be `None`.

          tosubclass (:class:`py:bool`):
            If not `None`, specifies the flavor that defines whether the
            qualifier value propagates to subclasses.

            `None` means that this information is not available, and the
            :attr:`~pywbem.CIMQualifierDeclaration.tosubclass` attribute
            will also be `None`.

          toinstance (:class:`py:bool`):
            If not `None`, specifies the flavor that defines whether the
            qualifier value propagates to instances.

            `None` means that this information is not available, and the
            :attr:`~pywbem.CIMQualifierDeclaration.toinstance` attribute
            will also be `None`.

            Note that :term:`DSP0200` has deprecated the presence of qualifier
            values on CIM instances and this flavor is not defined in
            :term:`DSP0004`

          translatable (:class:`py:bool`):
            If not `None`, specifies  the flavor that defines whether the
            qualifier is translatable.

            `None` means that this information is not available, and the
            :attr:`~pywbem.CIMQualifierDeclaration.translatable` attribute
            will also be `None`.
        """

        # We use the respective setter methods:
        self.name = name

        if is_array is None:
            is_array = _infer_is_array(value)
        else:
            # For performance reasons, we check only if not inferred.
            # This leaves the incorrect combination of is_array=False and
            # array_size=5 undetected, which seems acceptable because
            # array_size is ignored anyway when is_array=False.
            _check_array_parms(is_array, array_size, value,
                               "qualifier declaration", name)

        # We use the respective setter methods:
        self.type = type
        self.value = value  # value setter relies on self.type being set
        self.is_array = is_array
        self.array_size = array_size
        self.scopes = scopes
        self.overridable = overridable
        self.tosubclass = tosubclass
        self.toinstance = toinstance
        self.translatable = translatable

    @property
    def name(self):
        """
        :term:`unicode string`: Name of this CIM qualifier type.

        Will not be `None`.

        This attribute is settable. For details, see the description of the
        same-named init parameter of
        :class:`this class <pywbem.CIMQualifierDeclaration>`.
        """
        return self._name

    @name.setter
    def name(self, name):
        """Setter method; for a description see the getter method."""

        # pylint: disable=attribute-defined-outside-init
        self._name = _ensure_unicode(name)

        # We perform this check after the initialization to avoid errors
        # in test tools that show the object with repr().
        if name is None:
            raise ValueError("CIMQualifierDeclaration 'name' parameter must "
                             "not be None")

    @property
    def type(self):
        """
        :term:`unicode string`: Name of the CIM data type of this CIM
        qualifier type.

        Example: ``"uint8"``.

        Will not be `None`.

        This attribute is settable. For details, see the description of the
        same-named init parameter of
        :class:`this class <pywbem.CIMQualifierDeclaration>`.
        """
        return self._type

    @type.setter
    def type(self, type):
        # pylint: disable=redefined-builtin
        """Setter method; for a description see the getter method."""

        type = _ensure_unicode(type)

        # We perform this check after the initialization to avoid errors
        # in test tools that show the object with repr().
        if type not in ALL_CIMTYPES:
            raise ValueError(
                _format("Invalid CIM type: {0}", type))

        # pylint: disable=attribute-defined-outside-init
        self._type = type

    @property
    def value(self):
        """
        :term:`CIM data type`: Default value of this CIM qualifier type.

        `None` means that the value is Null.

        For CIM data types string and char16, this attribute will be a
        :term:`unicode string`, even when specified as a :term:`byte string`.

        This attribute is settable. For details, see the description of the
        same-named init parameter of
        :class:`this class <pywbem.CIMQualifierDeclaration>`.
        """
        return self._value

    @value.setter
    def value(self, value):
        """Setter method; for a description see the getter method."""
        # pylint: disable=attribute-defined-outside-init
        self._value = cimvalue(value, self.type)

    @property
    def is_array(self):
        """
        :class:`py:bool`: Boolean indicating that this CIM qualifier type
        is an array (as opposed to a scalar).

        Will not be `None`.

        This attribute is settable. For details, see the description of the
        same-named init parameter of
        :class:`this class <pywbem.CIMQualifierDeclaration>`.
        """
        return self._is_array

    @is_array.setter
    def is_array(self, is_array):
        """Setter method; for a description see the getter method."""
        # pylint: disable=attribute-defined-outside-init
        self._is_array = _ensure_bool(is_array)

    @property
    def array_size(self):
        """
        :term:`integer`: The size of the fixed-size array of this CIM qualifier
        type.

        `None` means that the array has variable size (or that the
        qualifier type is not an array).

        This attribute is settable. For details, see the description of the
        same-named init parameter of
        :class:`this class <pywbem.CIMQualifierDeclaration>`.
        """
        return self._array_size

    @array_size.setter
    def array_size(self, array_size):
        """Setter method; for a description see the getter method."""
        # pylint: disable=attribute-defined-outside-init
        self._array_size = array_size

    @property
    def scopes(self):
        """
        `NocaseDict`_: Scopes of this CIM qualifier type.

        Each dictionary item specifies one scope value, with:

        * key (:term:`unicode string`): Scope name, in upper case.

        * value (:class:`py:bool`): Scope value, specifying whether the
          qualifier has that scope (i.e. can be applied to a CIM element of
          that kind).

        Valid scope names are "CLASS", "ASSOCIATION", "INDICATION",
        "PROPERTY", "REFERENCE", "METHOD", "PARAMETER", and "ANY".

        Will not be `None`.

        This attribute is settable. For details, see the description of the
        same-named init parameter of
        :class:`this class <pywbem.CIMQualifierDeclaration>`.
        """
        return self._scopes

    @scopes.setter
    def scopes(self, scopes):
        """Setter method; for a description see the getter method."""
        # pylint: disable=attribute-defined-outside-init
        self._scopes = NocaseDict(scopes)

    @property
    def tosubclass(self):
        """
        :class:`py:bool`: If `True` specifies the ToSubclass flavor (the
        qualifier value propagates to subclasses); if `False` specifies the
        Restricted flavor (the qualifier value does not propagate to
        subclasses).

        `None` means that this information is not available.

        This attribute is settable. For details, see the description of the
        same-named init parameter of
        :class:`this class <pywbem.CIMQualifierDeclaration>`.
        """
        return self._tosubclass

    @tosubclass.setter
    def tosubclass(self, tosubclass):
        """Setter method; for a description see the getter method."""
        # pylint: disable=attribute-defined-outside-init
        self._tosubclass = _ensure_bool(tosubclass)

    @property
    def toinstance(self):
        """
        :class:`py:bool`: If `True`, specifies the ToInstance flavor. This
        flavor specifies that the qualifier value propagates to instances. If
        `False`, specifies that qualifier values do not propagate to instances.
        There is no flavor corresponding to `toinstance=False`.

        `None` means that this information is not available.

        Note that :term:`DSP0200` has deprecated the presence of qualifier
        values on CIM instances.

        This attribute is settable. For details, see the description of the
        same-named init parameter of
        :class:`this class <pywbem.CIMQualifierDeclaration>`.
        """
        return self._toinstance

    @toinstance.setter
    def toinstance(self, toinstance):
        """Setter method; for a description see the getter method."""
        # pylint: disable=attribute-defined-outside-init
        self._toinstance = _ensure_bool(toinstance)

    @property
    def overridable(self):
        """
        :class:`py:bool`: If `True`, specifies the  EnableOverride flavor (the
        qualifier value is overridable in subclasses); if `False` specifies the
        DisableOverride flavor (the qualifier value is not overridable in
        subclasses).

        `None` means that this information is not available.

        This attribute is settable. For details, see the description of the
        same-named init parameter of
        :class:`this class <pywbem.CIMQualifierDeclaration>`.
        """
        return self._overridable

    @overridable.setter
    def overridable(self, overridable):
        """Setter method; for a description see the getter method."""
        # pylint: disable=attribute-defined-outside-init
        self._overridable = _ensure_bool(overridable)

    @property
    def translatable(self):
        """
        :class:`py:bool`: If `True`, specifies the Translatable flavor. This
        flavor specifies that the qualifier is translatable. If `False`,
        specifies that the qualfier is not translatable. There is no flavor
        corresponding to `translatable=False`.

        `None` means that this information is not available.

        This attribute is settable. For details, see the description of the
        same-named init parameter of
        :class:`this class <pywbem.CIMQualifierDeclaration>`.
        """
        return self._translatable

    @translatable.setter
    def translatable(self, translatable):
        """Setter method; for a description see the getter method."""
        # pylint: disable=attribute-defined-outside-init
        self._translatable = _ensure_bool(translatable)

    def _cmp(self, other):
        """
        Comparator function for two :class:`~pywbem.CIMQualifierDeclaration`
        objects.

        The comparison is based on their public attributes, in descending
        precedence:

        * `name`
        * `type`
        * `value`
        * `is_array`
        * `array_size`
        * `scopes`
        * `overridable`
        * `tosubclass`
        * `toinstance`
        * `translatable`

        The comparison takes into account any case insensitivities described
        for these attributes.
        """
        if self is other:
            return 0
        try:
            assert isinstance(other, CIMQualifierDeclaration)
        except AssertionError:
            raise TypeError(
                _format("other must be CIMQualifierDeclaration, but is: {0}",
                        type(other)))
        return (cmpname(self.name, other.name) or
                cmpitem(self.type, other.type) or
                cmpitem(self.value, other.value) or
                cmpitem(self.is_array, other.is_array) or
                cmpitem(self.array_size, other.array_size) or
                cmpdict(self.scopes, other.scopes) or
                cmpitem(self.overridable, other.overridable) or
                cmpitem(self.tosubclass, other.tosubclass) or
                cmpitem(self.toinstance, other.toinstance) or
                cmpitem(self.translatable, other.translatable))

    def __hash__(self):
        """
        Return a hash value based on the public attributes of this class, taking
        into account any case insensitivities described for these attributes.
        This approach causes this class to be :term:`unchanged-hashable`.
        """
        hashes = (
            _hash_name(self.name),
            _hash_item(self.type),
            _hash_item(self.value),
            _hash_item(self.is_array),
            _hash_item(self.array_size),
            _hash_dict(self.scopes),
            _hash_item(self.overridable),
            _hash_item(self.tosubclass),
            _hash_item(self.toinstance),
            _hash_item(self.translatable),
        )
        return hash(hashes)

    def __str__(self):
        """
        Return a short string representation of this CIM qualifier type,
        for human consumption.
        """
        return _format(
            "CIMQualifierDeclaration("
            "name={s.name!A}, "
            "value={s.value!A}, "
            "type={s.type!A}, "
            "is_array={s.is_array!A}, ...)",
            s=self)

    def __repr__(self):
        """
        Return a string representation of this CIM qualifier type,
        that is suitable for debugging.

        The scopes will be ordered by their names in the result.
        """
        return _format(
            "CIMQualifierDeclaration("
            "name={s.name!A}, "
            "value={s.value!A}, "
            "type={s.type!A}, "
            "is_array={s.is_array!A}, "
            "array_size={s.array_size!A}, "
            "scopes={s.scopes!A}, "
            "tosubclass={s.tosubclass!A}, "
            "overridable={s.overridable!A}, "
            "translatable={s.translatable!A}, "
            "toinstance={s.toinstance!A})",
            s=self)

    def copy(self):
        """
        Return a new :class:`~pywbem.CIMQualifierDeclaration` object
        that is a copy of this CIM qualifier type.

        Objects of this class have no mutable types in any attributes, so
        modifications of the original object will not affect the returned copy,
        and vice versa.

        Note that the Python functions :func:`py:copy.copy` and
        :func:`py:copy.deepcopy` can be used to create completely shallow or
        completely deep copies of objects of this class.
        """
        return CIMQualifierDeclaration(
            self.name,
            self.type,
            value=self.value,
            is_array=self.is_array,
            array_size=self.array_size,
            scopes=self.scopes,  # setter copies
            overridable=self.overridable,
            tosubclass=self.tosubclass,
            toinstance=self.toinstance,
            translatable=self.translatable)

    def tocimxml(self):
        """
        Return the CIM-XML representation of this CIM qualifier type,
        as an object of an appropriate subclass of :term:`Element`.

        The returned CIM-XML representation is a `QUALIFIER.DECLARATION`
        element consistent with :term:`DSP0201`.

        Returns:

          The CIM-XML representation, as an object of an appropriate subclass
          of :term:`Element`.
        """

        if self.value is None:
            value_xml = None

        elif isinstance(self.value, (tuple, list)):
            array_xml = []
            for v in self.value:
                if v is None:
                    if SEND_VALUE_NULL:
                        array_xml.append(cim_xml.VALUE_NULL())
                    else:
                        array_xml.append(cim_xml.VALUE(None))
                else:
                    array_xml.append(cim_xml.VALUE(atomic_to_cim_xml(v)))
            value_xml = cim_xml.VALUE_ARRAY(array_xml)

        else:
            value_xml = cim_xml.VALUE(atomic_to_cim_xml(self.value))

        return cim_xml.QUALIFIER_DECLARATION(self.name,
                                             self.type,
                                             value_xml,
                                             is_array=self.is_array,
                                             array_size=self.array_size,
                                             qualifier_scopes=self.scopes,
                                             overridable=self.overridable,
                                             tosubclass=self.tosubclass,
                                             toinstance=self.toinstance,
                                             translatable=self.translatable)

    def tocimxmlstr(self, indent=None):
        """
        Return the CIM-XML representation of this CIM qualifier type,
        as a :term:`unicode string`.

        *New in pywbem 0.9.*

        For the returned CIM-XML representation, see
        :meth:`~pywbem.CIMQualifierDeclaration.tocimxml`.

        Parameters:

          indent (:term:`string` or :term:`integer`):
            `None` indicates that a single-line version of the XML should be
            returned, without any whitespace between the XML elements.

            Other values indicate that a prettified, multi-line version of the
            XML should be returned. A string value specifies the indentation
            string to be used for each level of nested XML elements. An integer
            value specifies an indentation string of so many blanks.

        Returns:

            The CIM-XML representation of the object, as a
            :term:`unicode string`.
        """
        xml_elem = self.tocimxml()
        return tocimxmlstr(xml_elem, indent)

    def tomof(self, maxline=MAX_MOF_LINE):
        """
        Return a MOF string with the declaration of this CIM qualifier type.

        The returned MOF string conforms to the ``qualifierDeclaration``
        ABNF rule defined in :term:`DSP0004`.

        Qualifier flavors are included in the returned MOF string only when
        the information is available (i.e. the value of the corresponding
        attribute is not `None`).

        Because :term:`DSP0004` does not support instance qualifiers, and thus
        does not define a flavor keyword for the
        :attr:`~pywbem.CIMQualifierDeclaration.toinstance` attribute, that
        flavor is not included in the returned MOF string.

        Returns:

          :term:`unicode string`: MOF string.
        """

        mof = []

        mof.append(u'Qualifier ')
        mof.append(self.name)
        mof.append(u' : ')
        mof.append(self.type)

        if self.is_array:
            mof.append(u'[')
            if self.array_size is not None:
                mof.append(six.text_type(self.array_size))
            mof.append(u']')

        if self.value is not None:

            mof.append(u' = ')

            if isinstance(self.value, list):
                mof.append(u'{ ')

            mof_str = u''.join(mof)
            line_pos = len(mof_str) - mof_str.rfind('\n') - 1
            val_str, line_pos = _value_tomof(
                self.value, self.type, MOF_INDENT, maxline, line_pos, 3, False)
            mof.append(val_str)

            if isinstance(self.value, list):
                mof.append(u' }')

        mof.append(u',\n')
        mof.append(_indent_str(MOF_INDENT + 1))
        mof.append(u'Scope(')
        mof_scopes = []
        for scope in self._ordered_scopes:
            if self.scopes.get(scope, False):
                mof_scopes.append(scope.lower())
        mof.append(u', '.join(mof_scopes))
        mof.append(u')')

        # toinstance flavor not included here because not part of DSP0004
        mof_flavors = []

        if self.overridable is True:
            mof_flavors.append('EnableOverride')
        elif self.overridable is False:
            mof_flavors.append('DisableOverride')

        if self.tosubclass is True:
            mof_flavors.append('ToSubclass')
        elif self.tosubclass is False:
            mof_flavors.append('Restricted')

        if self.translatable:
            mof_flavors.append('Translatable')

        if mof_flavors:
            mof.append(u',\n')
            mof.append(_indent_str(MOF_INDENT + 1))
            mof.append(u'Flavor(')
            mof.append(u', '.join(mof_flavors))
            mof.append(u')')

        mof.append(u';\n')

        return u''.join(mof)


def tocimxml(value):
    # pylint: disable=line-too-long
    """
    Return the CIM-XML representation of the input object,
    as an object of an appropriate subclass of :term:`Element`.

    The returned CIM-XML representation is consistent with :term:`DSP0201`.

    Parameters:

      value (:term:`CIM object`, :term:`CIM data type`, :term:`number`, :class:`py:datetime.datetime`, or tuple/list thereof):
        The input object.

        Specifying `None` has been deprecated in pywbem 0.12.

    Returns:

      The CIM-XML representation, as an object of an appropriate subclass of
      :term:`Element`.
    """  # noqa: E501

    if isinstance(value, (tuple, list)):
        array_xml = []
        for v in value:
            if v is None:
                if SEND_VALUE_NULL:
                    array_xml.append(cim_xml.VALUE_NULL())
                else:
                    array_xml.append(cim_xml.VALUE(None))
            else:
                array_xml.append(cim_xml.VALUE(atomic_to_cim_xml(v)))
        value_xml = cim_xml.VALUE_ARRAY(array_xml)
        return value_xml

    if hasattr(value, 'tocimxml'):
        return value.tocimxml()

    if value is None:
        warnings.warn("A value of None for pywbem.tocimxml() has been "
                      "deprecated.",
                      DeprecationWarning, stacklevel=2)

    return cim_xml.VALUE(atomic_to_cim_xml(value))


def tocimxmlstr(value, indent=None):
    """
    Return the CIM-XML representation of the CIM object or CIM data type,
    as a :term:`unicode string`.

    *New in pywbem 0.9.*

    The returned CIM-XML representation is consistent with :term:`DSP0201`.

    Parameters:

      value (:term:`CIM object` or :term:`CIM data type` or :term:`Element`):
        The CIM object or CIM data type to be converted to CIM-XML, or an
        :term:`Element` object that already is the CIM-XML representation.

      indent (:term:`string` or :term:`integer`):
        `None` indicates that a single-line version of the XML should be
        returned, without any whitespace between the XML elements.

        Other values indicate that a prettified, multi-line version of the XML
        should be returned. A string value specifies the indentation string to
        be used for each level of nested XML elements. An integer value
        specifies an indentation string of so many blanks.

    Returns:

        The CIM-XML representation of the value, as a :term:`unicode string`.
    """

    if isinstance(value, Element):
        xml_elem = value
    else:
        xml_elem = tocimxml(value)

    if indent is None:
        xml_str = xml_elem.toxml()
    else:
        if isinstance(indent, six.string_types):
            pass  # use indent, as specified
        elif isinstance(indent, six.integer_types):
            indent = ' ' * indent
        else:
            raise TypeError(
                _format("Type of indent must be string or integer, but is: {0}",
                        type(indent)))
        xml_str = xml_elem.toprettyxml(indent=indent)
    # xml_str is a unicode string if required based upon its content.
    return _ensure_unicode(xml_str)


# pylint: disable=too-many-locals,too-many-return-statements,too-many-branches
def tocimobj(type_, value):
    """
    **Deprecated:** Return a CIM object representing the specified value and
    type.

    This function has been deprecated in pywbem 0.13. Use
    :func:`~pywbem.cimvalue` instead.

    Parameters:

      `type_` (:term:`string`):
        The CIM data type name for the CIM object. See :ref:`CIM data types`
        for valid type names.

        If `value` is a list, `type_` must specify the CIM data type name of
        an item in the list.

      value (:term:`CIM data type` and some others, see description):
        The value to be represented as a CIM object.

        In addition to the Python types listed in :ref:`CIM data types`, the
        following Python types are supported for this parameter:

        * `None`: The returned object will be `None`.

        * If `type_` specifies one of the CIM integer data types:

          - :term:`integer`
          - :term:`string`. The string must represent a decimal number

        * If `type_` specifies the CIM boolean data type:

          - :term:`string`. The string must be ``'true'`` or ``'false'`` in any
            lexical case

        * If `type_` specifies the CIM datetime data type:

          - All input types of :class:`~pywbem.CIMDateTime`

        * If `type_` specifies the CIM reference data type:

          - :term:`string`. The string must be an untyped WBEM URI representing
            an instance path (see :term:`DSP0207`)

    Returns:

        A :term:`CIM data type` object, representing the specified value and
        type.

    Raises:

        ValueError: Input cannot be converted to defined CIM value type, or
          invalid CIM data type name.
    """

    if value is None or type_ is None:
        return None

    if type_ != 'string' and isinstance(value, six.string_types) and not value:
        return None

    # Lists of values

    if isinstance(value, list):
        return [tocimobj(type_, x) for x in value]

    # Boolean type

    if type_ == 'boolean':
        if isinstance(value, bool):
            return value

        if isinstance(value, six.string_types):
            if value.lower() == 'true':
                return True

            if value.lower() == 'false':
                return False
        raise ValueError(
            _format("Invalid boolean value: {0!A}", value))

    # String type

    if type_ == 'string':
        return _ensure_unicode(value)

    # Integer types

    if type_ == 'uint8':
        return Uint8(value)

    if type_ == 'sint8':
        return Sint8(value)

    if type_ == 'uint16':
        return Uint16(value)

    if type_ == 'sint16':
        return Sint16(value)

    if type_ == 'uint32':
        return Uint32(value)

    if type_ == 'sint32':
        return Sint32(value)

    if type_ == 'uint64':
        return Uint64(value)

    if type_ == 'sint64':
        return Sint64(value)

    # Real types

    if type_ == 'real32':
        return Real32(value)

    if type_ == 'real64':
        return Real64(value)

    # Char16

    if type_ == 'char16':
        return _ensure_unicode(value)

    # Datetime

    if type_ == 'datetime':
        return CIMDateTime(value)

    # REF

    if type_ == 'reference':  # pylint: disable=too-many-nested-blocks
        # pylint: disable=too-many-return-statements,too-many-branches

        # Note: This doesn't handle double-quoting, as in refs to refs. Example:
        # r'ex_composedof.composer="ex_sampleClass.label1=9921,' +
        #  'label2=\"SampleLabel\"",component="ex_sampleClass.label1=0121,' +
        #  'label2=\"Component\""')

        if isinstance(value, (CIMInstanceName, CIMClassName)):
            return value

        # pylint: disable=no-else-return
        if isinstance(value, six.string_types):
            nm_space = host = None
            head, sep, tail = _partition(value, '//')
            if sep and head.find('"') == -1:
                # we have a namespace type
                head, sep, tail = _partition(tail, '/')
                host = head
            else:
                tail = head
            head, sep, tail = _partition(tail, ':')
            if sep:
                nm_space = head
            else:
                tail = head
            head, sep, tail = _partition(tail, '.')
            if not sep:
                return CIMClassName(head, host=host, namespace=nm_space)
            classname = head
            key_bindings = {}
            while tail:
                head, sep, tail = _partition(tail, ',')
                if head.count('"') == 1:  # quoted string contains comma
                    tmp, sep, tail = _partition(tail, '"')
                    head = '{0},{1}'.format(head, tmp)
                    tail = _partition(tail, ',')[2]
                head = head.strip()
                key, sep, val = _partition(head, '=')
                if sep:
                    cl_name, s, k = _partition(key, '.')
                    if s:
                        if cl_name != classname:
                            raise ValueError(
                                _format("Invalid object path: {0!A}", value))
                        key = k
                    val = val.strip()
                    if val[0] == '"' and val[-1] == '"':
                        val = val.strip('"')
                    else:
                        if val.lower() in ('true', 'false'):
                            val = val.lower() == 'true'
                        elif val.isdigit():
                            val = int(val)
                        else:
                            try:
                                val = float(val)
                            except ValueError:
                                try:
                                    val = CIMDateTime(val)
                                except ValueError:
                                    raise ValueError(
                                        _format("Invalid key binding: {0!A}",
                                                val))

                    key_bindings[key] = val
            return CIMInstanceName(classname, host=host, namespace=nm_space,
                                   keybindings=key_bindings)
        else:
            raise ValueError(
                _format("Invalid reference value: {0!A}", value))

    raise ValueError(
        _format("Invalid CIM data type name: {0!A}", type_))


def cimvalue(value, type):
    # pylint: disable=redefined-builtin
    """
    Return a :term:`CIM data type` representing the specified value in the
    specified CIM type.

    *New in pywbem 0.12.*

    This function guarantees that the returned object is a valid
    :term:`CIM data type`. If the input parameters are not sufficient to
    construct a CIM data type, an exception is raised.

    If the provided value is already a CIM data type (or `None`), the input
    value is returned.

    Otherwise, the value is converted to a CIM data type as described below.

    If the provided value is a list, a new list is returned with this function
    being invoked recursively on the items of the input list.

    Embedded objects and embedded instances are not handled by this function.

    Parameters:

      `type` (:term:`string`):
        The CIM data type name for the CIM object. See :ref:`CIM data types`
        for valid type names.

        If `value` is a list, `type` must specify the CIM data type name of
        an item in the list.

      value (:term:`CIM data type` and other suitable types):
        The value to be represented as a CIM object.

        If `None`, the returned object will be `None`.

        The following other suitable types are supported (in addition to the
        respective :term:`CIM data type`):

        * If `type` is ``'string'`` or ``'char16'``:

          - Objects of type :term:`byte string`; they will be converted to
            :term:`unicode string`.

        * If `type` specifies one of the CIM integer data types (e.g.
          ``'uint8'``):

          - Any object supported as an init parameter for :class:`py:int` or
            :class:`py2:long` (Python 2 only). This includes :term:`string`
            values with decimal integer numbers.
            If the value is not supported, `ValueError` will be raised.

        * If `type` specifies one of the CIM float data types (e.g.
          ``'real32'``):

          - Any object supported as an init parameter for :class:`py:float`.
            This includes :term:`string` values with decimal integer or float
            numbers.
            If the value is not supported, `ValueError` will be raised.

        * If `type` is ``'boolean'``:

          - Any object. The value is converted to bool using the standard
            Python truth testing procedure.

        * If `type` is ``'datetime'``:

          - Any object supported as an init parameter for
            :class:`~pywbem.CIMDateTime` .

        * If `type` is ``'reference'``:

          - :term:`string`. The string must be an untyped WBEM URI representing
            an instance path (see :term:`DSP0207`).
          - :class:`~pywbem.CIMInstanceName`. An instance path.
          - :class:`~pywbem.CIMClassName`. A class path.

    Returns:

        A :term:`CIM data type` object, representing the specified value and
        type.

    Raises:

        ValueError: An input parameter has an invalid value.
        TypeError: An input parameter has an invalid Python type.
    """

    if value is None:
        return None

    if type is None:
        # The following may raise TypeError or ValueError. This ensures that
        # Python number typed values cannot be provided without specifing
        # their CIM type.
        type = cimtype(value)

    # Arrays
    if isinstance(value, list):
        return [cimvalue(v, type) for v in value]

    # Boolean type
    if type == 'boolean':
        return bool(value)

    # String and char16 types
    if type in ('string', 'char16'):
        return _ensure_unicode(value)

    # REF type
    if type == 'reference':
        if isinstance(value, (CIMInstanceName, CIMClassName)):
            return value
        if isinstance(value, six.string_types):
            return CIMInstanceName.from_wbem_uri(value)
        raise TypeError(
            _format("Input value has invalid type for a CIM reference: {0!A}",
                    value))

    # Other types (integers, floats, datetime)
    type_obj = type_from_name(type)  # Raises ValueError if invalid type
    if isinstance(value, type_obj):
        return value
    return type_obj(value)


def _partition(str_arg, sep):
    """
    _partition(str_arg, sep) -> (head, sep, tail)

    Searches for the first occurrence of the separator sep in str_arg, and
    returns the, part before it, the separator itself, and the part after it.

    If the separator is not found, returns str_arg and two empty strings.
    """
    try:
        return str_arg.partition(sep)
    except AttributeError:
        try:
            idx = str_arg.index(sep)
        except ValueError:
            return (str_arg, '', '')
        return (str_arg[:idx], sep, str_arg[idx + len(sep):])


def _infer_type(value, element_kind, element_name):
    """
    Infer the CIM type name of the value, based upon its Python type.
    """

    if value is None:
        raise ValueError(
            _format("Cannot infer CIM type of {0} {1!A} from its value when "
                    "the value is None", element_kind, element_name))

    try:
        return cimtype(value)
    except TypeError as exc:
        raise ValueError(
            _format("Cannot infer CIM type of {0} {1!A} from its value: {2!A}",
                    element_kind, element_name, exc))


def _infer_is_array(value):
    """
    Infer whether the value is an array, based upon its Python type.

    A value of None defaults to be considered a scalar.
    """

    if value is None:
        return False

    return isinstance(value, list)


def _check_array_parms(is_array, array_size, value, element_kind,
                       element_name):
    # pylint: disable=unused-argument
    # The array_size argument is unused.
    """
    Check whether array-related parameters are ok.
    """

    # The following case has been disabled because it cannot happen given
    # how this check function is used:
    # if array_size and is_array is False:
    #     raise ValueError(
    #         _format("The array_size parameter of {0} {1!A} is {2!A} but the "
    #                 "is_array parameter is False.",
    #                 element_kind, element_name, array_size))

    if value is not None:
        value_is_array = isinstance(value, (list, tuple))
        if not is_array and value_is_array:
            raise ValueError(
                _format("The is_array parameter of {0} {1!A} is False but "
                        "value {2!A} is an array.",
                        element_kind, element_name, value))
        if is_array and not value_is_array:
            raise ValueError(
                _format("The is_array parameter of {0} {1!A} is True but "
                        "value {2!A} is not an array.",
                        element_kind, element_name, value))


def _infer_embedded_object(value):
    """
    Infer CIMProperty/CIMParameter.embedded_object from the CIM value.
    """

    if value is None:
        # The default behavior is to assume that a value of None is not
        # an embedded object. If the user wants that, they must specify
        # the embedded_object parameter.
        return False

    if isinstance(value, list):
        if not value:
            # The default behavior is to assume that an empty array value
            # is not an embedded object. If the user wants that, they must
            # specify the embedded_object parameter.
            return False
        value = value[0]

    if isinstance(value, CIMInstance):
        # The default behavior is to produce 'instance', although 'object'
        # would also be valid.
        return 'instance'

    if isinstance(value, CIMClass):
        return 'object'

    return False


def _check_embedded_object(embedded_object, type, value, element_kind,
                           element_name):
    # pylint: disable=redefined-builtin
    """
    Check whether embedded-object-related parameters are ok.
    """

    if embedded_object not in ('instance', 'object'):
        raise ValueError(
            _format("{0} {1!A} specifies an invalid value for "
                    "embedded_object: {2!A} (must be 'instance' or 'object')",
                    element_kind, element_name, embedded_object))

    if type != 'string':
        raise ValueError(
            _format("{0} {1!A} specifies embedded_object {2!A} but its CIM "
                    "type is invalid: {3!A} (must be 'string')",
                    element_kind, element_name, embedded_object, type))

    if value is not None:
        if isinstance(value, list):
            if value:
                v0 = value[0]  # Check the first array element
                if v0 is not None and \
                        not isinstance(v0, (CIMInstance, CIMClass)):
                    raise ValueError(
                        _format("Array {0} {1!A} specifies embedded_object "
                                "{2!A} but the Python type of its first array "
                                "value is invalid: {3} (must be CIMInstance "
                                "or CIMClass)",
                                element_kind, element_name, embedded_object,
                                builtin_type(v0)))
        else:
            if not isinstance(value, (CIMInstance, CIMClass)):
                raise ValueError(
                    _format("{0} {1!A} specifies embedded_object {2!A} but "
                            "the Python type of its value is invalid: {3} "
                            "(must be CIMInstance or CIMClass)",
                            element_kind, element_name, embedded_object,
                            builtin_type(value)))


def byname(nlist):
    """
    **Deprecated:** Convert a list of named objects into an ordered dictionary
    indexed by name.

    This function is internal and has been deprecated in pywbem 0.12.
    """
    warnings.warn("The internal byname() function has been deprecated, with "
                  "no replacement.", DeprecationWarning,
                  stacklevel=_stacklevel_above_module(__name__))
    return OrderedDict([(x.name, x) for x in nlist])
