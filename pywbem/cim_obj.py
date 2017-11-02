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
:class:`~pywbem.CIMParameter`               CIM parameter in a CIM method declaration in a CIM class
:class:`~pywbem.CIMQualifier`               CIM qualifier value
:class:`~pywbem.CIMQualifierDeclaration`    CIM qualifier type/declaration
==========================================  ==========================================================================

.. _`NocaseDict`:

NocaseDict
----------

Class ``NocaseDict`` is a dictionary implementation with case-insensitive but
case-preserving keys. It is used for sets of named CIM elements (e.g. CIM
properties in an instance or class, or CIM parameters in a method).

Except for the case-insensitivity of its keys, it behaves like the built-in
:class:`py:dict`. Therefore, ``NocaseDict`` is not described in detail in this
documentation.

Deprecated: In v0.9.0, support for comparing two ``NocaseDict`` instances with
the ``>``, ``>``, ``<=``, ``>=`` operators has been deprecated.
"""  # noqa: E501
# pylint: enable=line-too-long
# Note: When used before module docstrings, Pylint scopes the disable statement
#       to the whole rest of the file, so we need an enable statement.

# This module is meant to be safe for 'import *'.

from __future__ import print_function, absolute_import

from datetime import datetime, timedelta
import warnings

import six

from . import cim_xml
from .cim_types import _CIMComparisonMixin, type_from_name, cimtype, \
    atomic_to_cim_xml, CIMType, CIMDateTime, Uint8, Sint8, Uint16, Sint16, \
    Uint32, Sint32, Uint64, Sint64, Real32, Real64

if six.PY2:
    # pylint: disable=wrong-import-order
    from __builtin__ import type as builtin_type
else:
    # pylint: disable=wrong-import-order
    from builtins import type as builtin_type  # pylint: disable=import-error

__all__ = ['CIMClassName', 'CIMProperty', 'CIMInstanceName', 'CIMInstance',
           'CIMClass', 'CIMMethod', 'CIMParameter', 'CIMQualifier',
           'CIMQualifierDeclaration', 'tocimxml', 'tocimxmlstr', 'tocimobj']

# Constants for MOF formatting output
MOF_INDENT = 4
MAX_MOF_LINE = 79   # use 79 because comma separator sometimes runs over


class NocaseDict(object):
    # pylint: disable=too-many-lines
    """
    Yet another implementation of a case-insensitive dictionary.

    Whenever keys are looked up, that is done case-insensitively. Whenever
    keys are returned, they are returned with the lexical case that was
    originally specified.

    In addition to the methods listed, the dictionary supports:

      * Retrieval of values based on key: `val = d[key]`

      * Assigning values for a key: `d[key] = val`

      * Deleting a key/value pair: `del d[key]`

      * Equality comparison (`==`, `!=`)

      * Ordering comparison (`<`, `<=`, `>=`, `>`)

      * Containment test: `key in d`

      * For loops: `for key in d`

      * Determining length: `len(d)`
    """

    def __init__(self, *args, **kwargs):
        """
        Initialize the new dictionary from at most one positional argument and
        optionally from additional keyword arguments.

        Initialization happens in two steps, first from the positional
        argument:

          * If no positional argument is provided, or if one argument with the
            value None is provided, the new dictionary will be left empty in
            this step.

          * If one positional argument of tuple or list type is provided, the
            items in that iterable must be tuples of key and value,
            respectively. The key/value pairs will be put into the new
            dictionary (without copying them).

          * If one positional argument of dictionary (mapping) or
            `NocaseDict`_ type is provided, its key/value
            pairs are put into the new dictionary (without copying them).

          * Otherwise, `TypeError` is raised.

        After that, any provided keyword arguments are put into the so
        initialized dictionary as key/value pairs (without copying them).
        """

        self._data = {}

        # Step 1: Initialize from at most one positional argument
        if len(args) == 1:
            if isinstance(args[0], (list, tuple)):
                # Initialize from iterable of tuple(key,value)
                for item in args[0]:
                    self[item[0]] = item[1]
            elif isinstance(args[0], dict):
                # Initialize from dict/mapping object
                self.update(args[0])
            elif isinstance(args[0], NocaseDict):
                # Initialize from another NocaseDict object
                # pylint: disable=protected-access
                self._data = args[0]._data.copy()
            elif args[0] is None:
                # Leave empty
                pass
            else:
                raise TypeError(
                    "Invalid type for NocaseDict initialization: %s (%s)" %
                    (args[0].__class__.__name__, type(args[0])))
        elif len(args) > 1:
            raise TypeError(
                "Too many positional arguments for NocaseDict initialization: "
                "%s (1 allowed)" % len(args))

        # Step 2: Add any keyword arguments
        self.update(kwargs)

    # Basic accessor and settor methods

    def __getitem__(self, key):
        """
        Invoked when retrieving the value for a key, using `val = d[key]`.

        The key is looked up case-insensitively. Raises `KeyError` if the
        specified key does not exist. Note that __setitem__() ensures that
        only string typed keys will exist, so the key type is not tested here
        and specifying non-string typed keys will simply lead to a KeyError.
        """
        k = key
        if isinstance(key, six.string_types):
            k = k.lower()
        try:
            return self._data[k][1]
        except KeyError:
            raise KeyError('Key %r not found' % key)

    def __setitem__(self, key, value):
        """
        Invoked when assigning a value for a key using `d[key] = val`.

        The key is looked up case-insensitively. If the key does not exist,
        it is added with the new value. Otherwise, its value is overwritten
        with the new value.

        Raises `TypeError` if the specified key does not have string type.
        """
        if not isinstance(key, six.string_types):
            raise TypeError('NocaseDict key %s must be string type, '
                            'but is %s' % (key, builtin_type(key)))
        k = key.lower()
        self._data[k] = (key, value)

    def __delitem__(self, key):
        """
        Invoked when deleting a key/value pair using `del d[key]`.

        The key is looked up case-insensitively. Raises `KeyError` if the
        specified key does not exist. Note that __setitem__() ensures that
        only string typed keys will exist, so the key type is not tested here
        and specifying non-string typed keys will simply lead to a KeyError.
        """
        k = key
        if isinstance(key, six.string_types):
            k = k.lower()
        try:
            del self._data[k]
        except KeyError:
            raise KeyError('Key %r not found' % key)

    def __len__(self):
        """
        Invoked when determining the number of key/value pairs in the
        dictionary using `len(d)`.
        """
        return len(self._data)

    def __contains__(self, key):
        """
        Invoked when determining whether a specific key is in the dictionary
        using `key in d`.

        The key is looked up case-insensitively.
        """
        k = key
        if isinstance(key, six.string_types):
            k = k.lower()
        return k in self._data

    def get(self, key, default=None):
        """
        Get the value for a specific key, or the specified default value if
        the key does not exist.

        The key is looked up case-insensitively.
        """
        try:
            return self[key]
        except KeyError:
            return default

    def setdefault(self, key, default):
        """
        Assign the specified default value for a specific key if the key did
        not exist and return the value for the key.

        The key is looked up case-insensitively.
        """
        if key not in self:
            self[key] = default
        return self[key]

    # Other accessor expressed in terms of iterators

    def keys(self):
        """
        Return a copied list of the dictionary keys, in their original case.
        """
        return list(self.iterkeys())

    def values(self):
        """
        Return a copied list of the dictionary values.
        """
        return list(self.itervalues())

    def items(self):
        """
        Return a copied list of the dictionary items, where each item is a
        tuple of its original key and its value.
        """
        return list(self.iteritems())

    # Iterators

    def iterkeys(self):
        """
        Return an iterator through the dictionary keys in their original
        case.
        """
        for item in six.iteritems(self._data):
            yield item[1][0]

    def itervalues(self):
        """
        Return an iterator through the dictionary values.
        """
        for item in six.iteritems(self._data):
            yield item[1][1]

    def iteritems(self):
        """
        Return an iterator through the dictionary items, where each item is a
        tuple of its original key and its value.
        """
        for item in six.iteritems(self._data):
            yield item[1]

    def __iter__(self):
        """
        Invoked when iterating through the dictionary using `for key in d`.

        The returned keys have their original case.
        """
        return six.iterkeys(self._data)

    # Other stuff

    def __repr__(self):
        """
        Return a string representation of the
        `NocaseDict`_ object that is suitable for
        debugging.

        The order of dictionary items in the result will be sorted by keys.
        """
        items = ', '.join([('%r: %r' % (key, self[key]))
                           for key in sorted(self.iterkeys())])
        return 'NocaseDict({%s})' % items

    def update(self, *args, **kwargs):
        """
        Update the dictionary from sequences of key/value pairs provided in any
        positional arguments, and from key/value pairs provided in any keyword
        arguments. The key/value pairs are not copied.

        Each positional argument can be:

          * an object with a method `items()` that returns an
            :term:`py:iterable` of tuples containing key and value.

          * an object without such a method, that is an :term:`py:iterable` of
            tuples containing key and value.

        Each keyword argument is a key/value pair.
        """
        for mapping in args:
            if hasattr(mapping, 'items'):
                for key, value in mapping.items():
                    self[key] = value
            else:
                for key, value in mapping:
                    self[key] = value
        for key, value in kwargs.items():
            self[key] = value

    def clear(self):
        """
        Remove all items from the dictionary.
        """
        self._data.clear()

    def popitem(self):
        """
        This function does nothing.

        In a standard mapping implementation, it would remove and return an
        arbitrary item from the dictionary.

        TODO: Why does popitem() do nothing; was it simply not implemented?
        """
        pass

    def copy(self):
        """
        Return a shallow copy of the dictionary (i.e. the keys and values are
        not copied).
        """
        result = NocaseDict()
        result._data = self._data.copy()  # pylint: disable=protected-access
        return result

    def __eq__(self, other):
        """
        Invoked when two dictionaries are compared with the `==` operator.

        The comparison is based on matching key/value pairs.
        The keys are looked up case-insensitively.
        """
        for key, self_value in self.iteritems():
            if key not in other:
                return False
            other_value = other[key]
            try:
                if not self_value == other_value:
                    return False
            except TypeError:
                return False  # not comparable -> considered not equal
        return len(self) == len(other)

    def __ne__(self, other):
        """
        Invoked when two dictionaries are compared with the `!=` operator.

        Implemented by delegating to the `==` operator.
        """
        return not self == other

    @staticmethod
    def __ordering_deprecated():
        """Function to issue deprecation warning for ordered comparisons
        """

        warnings.warn(
            "Ordering comparisons for pywbem.NocaseDict are deprecated",
            DeprecationWarning)

    def __lt__(self, other):
        self.__ordering_deprecated()
        # Delegate to the underlying standard dictionary. This will result in
        # a case sensitive comparison, but that will be better than the faulty
        # algorithm that was used before. It will raise TypeError "unorderable
        # types" in Python 3.
        return self._data < other._data  # pylint: disable=protected-access

    def __gt__(self, other):
        """
        Invoked when two dictionaries are compared with the `>` operator.

        Implemented by delegating to the `<` operator.
        """
        self.__ordering_deprecated()
        return other < self

    def __ge__(self, other):
        """
        Invoked when two dictionaries are compared with the `>=` operator.

        Implemented by delegating to the `>` and `==` operators.
        """
        self.__ordering_deprecated()
        return (self > other) or (self == other)

    def __le__(self, other):
        """
        Invoked when two dictionaries are compared with the `<=` operator.

        Implemented by delegating to the `<` and `==` operators.
        """
        self.__ordering_deprecated()
        return (self < other) or (self == other)


def _intended_value(intended, unspecified, actual, name, msg):
    """
    Return the intended value if the actual value is unspecified or has
    the intended value already, and otherwise raise a ValueError with the
    specified error message.

    Arguments:

      * `intended`: The intended value, or sequence of values. The first
        item in the sequence will act as the intended value, the others
        are also valid values.
      * `unspecified`: A value indicating 'unspecified' (usually `None`).
      * `actual`: The actual value.
      * `name`: The name of the attribute that this is about, for use in the
        exception message.
      * `msg`: A context setting message, for use in the exception message.
    """

    if isinstance(intended, (tuple, list)):
        if actual == unspecified:
            return intended[0]  # the default
        elif actual in intended:
            return actual
        else:
            raise ValueError(msg + ", but specifies %s=%r (must be one of %r)"
                             % (name, actual, intended))
    else:
        if actual == unspecified:
            return intended
        elif actual == intended:
            return actual
        else:
            raise ValueError(msg + ", but specifies %s=%r (must be %r)"
                             % (name, actual, intended))


def cmpname(name1, name2):
    """
    Compare two CIM names, case-insensitively.

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
    Compare two items (CIM values, CIM objects, or NocaseDict objects) for
    unequality.

    Note: Support for comparing the order of the items has been removed
    in pywbem v0.9.0.

    One or both of the items may be `None`.

    The implementation uses the '==' operator of the item datatypes.

    If value1 == value2, 0 is returned.
    If value1 != value2, 1 is returned.
    """
    if item1 is None and item2 is None:
        return 0
    if item1 is None or item2 is None:
        return 1
    if item1 == item2:
        return 0
    return 1


def _convert_unicode(obj):
    """
    Make sure the input object is returned as a :term:`unicode string`, as
    follows:

    * If the input object already is a :term:`unicode string`, it is returned
      unchanged.
    * If the input object is a :term:`byte string`, it is decoded using UTF-8.
    * Otherwise, the input object is translated into its :term:`unicode string`
      representation (this causes its `__str__()` or `__unicode__()` method to
      be invoked).
    """
    if isinstance(obj, six.text_type):
        return obj
    if isinstance(obj, six.binary_type):
        return obj.decode("utf-8")
    return six.text_type(obj)


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
    # TODO: Find out whether this function is used for non-string types at all
    return obj


def _convert_bytes(obj):
    """
    Make sure the input object is returned as a :term:`byte string`, as
    follows:

    * If the input object already is a :term:`byte string`, it is returned
      unchanged.
    * If the input object is a :term:`unicode string`, it is encoded using
      UTF-8.
    * Otherwise, the input object is translated into its :term:`byte string`
      representation (this causes its `__str__()` or `__bytes__()` method to
      be invoked).
    """
    if isinstance(obj, six.binary_type):
        return obj
    if isinstance(obj, six.text_type):
        return obj.encode("utf-8")
    return six.binary_type(obj)


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
    # TODO: Find out whether this function is used for non-string types at all
    return obj


def _makequalifiers(qualifiers, indent):
    """
    Return a MOF fragment for a NocaseDict of qualifiers indented the
    number of spaces defined by indent. Return empty string if no qualifiers.
    Normally multiline output and may fold qualifiers into multiple lines.

    Parameters:

      qualifiers (list): List of qualifiers to format.

      indent (:term:`integer`): Indent level for this set of qualifiers.
    """
    if not qualifiers:
        return ''
    qual_list = [q.tomof(indent + 2) for q in sorted(qualifiers.values())]
    qual_str = ',\n '.ljust(indent + 2).join(qual_list)
    return '%s[%s]' % (_indent_str(indent), qual_str)


def _indent_str(indent):
    """
    Return a MOF indent pad string from the indent integer variable
    that defines number of spaces to indent. Used to format MOF output
    """
    return ' '.ljust(indent, ' ')


def mofstr(strvalue, indent=MOF_INDENT, maxline=MAX_MOF_LINE):
    # Note: This is a raw docstring because it shows many backslashes, and
    # that avoids having to double them.
    r"""
    Convert the string in `strvalue` into a MOF string constant
    (i.e. a string literal), including the surrounding double quotes, and
    return that result.

    The input string must be a :term:`unicode string`, and the returned MOF
    string constant is also a :term:`unicode string`.

    This function handles MOF escaping and breaking the string into multiple
    lines according to the `maxline` and `indent` parameters.

    `DSP0004` defines that the character repertoire for MOF string constants
    is the entire repertoire for the CIM string datatype. That is, the entire
    Unicode character repertoire except for U+0000.

    The only character for which DSP0004 requires the use of a MOF escape
    sequence in a MOF string constant, is the double quote (because a MOF
    string constant is enclosed in double quotes).

    DSP0004 defines MOF escape sequences for several more characters, but it
    does not require their use in MOF. For example, it is valid for a MOF
    string constant to contain the (unescaped) characters U+000D (newline) or
    U+0009 (horizontal tab), and others.

    Processing the MOF escape sequences as unescaped characters may not be
    supported by MOF-related tools, and therefore this function plays it safe
    and uses the MOF escape sequences defined in DSP0004 as much as possible.
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

    This function does not tolerate that the input string already contains
    MOF escape sequences (it did so before v0.9, but that created more
    problems than it solved).

    After escaping, the string is broken into multiple lines, for better
    readability. The maximum line size is specified via the `maxline`
    parameter. The indentation for any spilled over lines (i.e. not the first
    line) is specified via the `indent` parameter.
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
    #         esc = '\\x%04X' % cp
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

    # Break into multiple strings for better readability
    blankfind = maxline - indent - 2
    _is = _indent_str(indent)
    ret_str_list = list()
    # TODO does not account for the extra char that may be appended
    # to line (ex. comma). Improvement would to be to test last line
    # for one char less than max line length and adjust. To get
    # around this, we set max line length default to 79 ks Mar 2016
    if escaped_str == '':
        ret_str_list.append('""')
    else:
        while escaped_str != '':
            if len(escaped_str) <= blankfind:
                ret_str_list.append('"' + escaped_str + '"')
                escaped_str = ''
            else:
                splitpos = escaped_str.rfind(' ', 0, blankfind)
                if splitpos < 0:
                    splitpos = blankfind - 1
                ret_str_list.append('"' + escaped_str[0:splitpos + 1] + '"')
                escaped_str = escaped_str[splitpos + 1:]

    ret_str = ('\n' + _is).join(ret_str_list)
    return ret_str


def moftype(cim_type, refclass):
    """
    Converts a CIM data type name to MOF syntax.
    """

    return (refclass + ' REF') if cim_type == 'reference' else cim_type


class CIMInstanceName(_CIMComparisonMixin):
    """
    A CIM instance path (aka *CIM instance name*).

    A CIM instance path references a CIM instance in a CIM namespace in a WBEM
    server. Namespace and WBEM server may be unspecified.
    """

    def __init__(self, classname, keybindings=None, host=None, namespace=None):
        """
        Parameters:

          classname (:term:`string`):
            Name of the creation class of the referenced instance.

            Must not be `None`.

          keybindings (:class:`py:dict` or `NocaseDict`_):
            Keybindings for the instance path (that is, the key property values
            of the referenced instance).

            A a shallow copy of the provided dictionary will be stored in the
            ``CIMInstanceName`` object.

            Each dictionary item specifies one keybinding, with:

            * key (:term:`string`):
              Keybinding name. Lexical case is preserved. Must not be `None`.
            * value (:term:`CIM data type`):
              Keybinding value.
              Note that numeric Python types (``int``, ``float``) are not valid
              CIM data types.

            `None` is interpreted as an empty set of keybindings.

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
            same-named attribute in the ``CIMInstanceName`` object will also be
            `None`.

          namespace (:term:`string`):
            Name of the CIM namespace containing the referenced instance.

            `None` means that the namespace is unspecified, and the
            same-named attribute in the ``CIMInstanceName`` object will also be
            `None`.
        """

        # Make sure we process Unicode strings
        classname = _ensure_unicode(classname)
        host = _ensure_unicode(host)
        namespace = _ensure_unicode(namespace)

        if classname is None:
            raise ValueError('Instance path must have a class name')

        self.classname = classname
        self.keybindings = NocaseDict(keybindings)
        self.host = host
        self.namespace = namespace

    @property
    def classname(self):
        """
        :term:`unicode string`: Name of the creation class of the referenced
        instance.

        Will not be `None`.

        This attribute is settable. For details, see the description of the
        same-named constructor parameter,
        except that the provided value must be a :term:`unicode string`.
        """
        return self._classname

    @classname.setter
    def classname(self, classname):
        """Setter method; for a description see the getter method."""
        # pylint: disable=attribute-defined-outside-init
        self._classname = classname

    @property
    def keybindings(self):
        """
        `NocaseDict`_: Keybindings of the instance path (that is, the key
        property values of the referenced instance).

        Each dictionary item specifies one keybinding, with:

        * key (:term:`unicode string`): Keybinding name. Its lexical case was
          preserved.
        * value (:term:`CIM data type`): Keybinding value.

        Will not be `None`.

        This attribute is settable; setting it will cause the current
        keybindings to be replaced with the new keybindings.
        The provided value must be a `NocaseDict`_ object. For details, see the
        description of the same-named constructor parameter,
        except that the dictionary key must be a :term:`unicode string`.

        The keybindings can also be accessed and manipulated one by one
        because the attribute value is a modifiable dictionary::

            instpath = CIMInstanceName(...)
            v1 = "abc"  # must be a CIM data type

            instpath.keybindings['k1'] = v1  # Set "k1" to v1 (add if needed)
            v1 = instpath.keybindings['k1']  # Access value of "k1"
            del instpath.keybindings['k1']  # Delete "k1" from the inst. path

        In addition, the keybindings can be accessed and manipulated one by
        one by using the entire ``CIMInstanceName`` object like a dictionary::

            instpath = CIMInstanceName(...)
            v2 = Uint32(...)  # must be a CIM data type

            instpath['k2'] = v2  # Set "k2" to v2 (add if needed)
            v2 = instpath['k2']  # Access value of "k2"
            del instpath['k2']  # Delete "k2" from the instance path
        """
        return self._keybindings

    @keybindings.setter
    def keybindings(self, keybindings):
        """Setter method; for a description see the getter method."""
        # pylint: disable=attribute-defined-outside-init
        self._keybindings = keybindings

    @property
    def namespace(self):
        """
        :term:`unicode string`: Name of the CIM namespace containing the
        referenced instance.

        `None` means that the namespace is unspecified.

        This attribute is settable. For details, see the description of the
        same-named constructor parameter,
        except that the provided value must be a :term:`unicode string`.
        """
        return self._namespace

    @namespace.setter
    def namespace(self, namespace):
        """Setter method; for a description see the getter method."""
        # pylint: disable=attribute-defined-outside-init
        self._namespace = namespace

    @property
    def host(self):
        """
        :term:`unicode string`: Host and optionally port of the WBEM server
        containing the CIM namespace of the referenced instance.

        For details about the string format, see the same-named constructor
        parameter.

        `None` means that the host and port are unspecified.

        This attribute is settable. For details, see the description of the
        same-named constructor parameter,
        except that the provided value must be a :term:`unicode string`.
        """
        return self._host

    @host.setter
    def host(self, host):
        """Setter method; for a description see the getter method."""
        # pylint: disable=attribute-defined-outside-init
        self._host = host

    def _cmp(self, other):
        """
        Comparator function for two :class:`~pywbem.CIMInstanceName` objects.

        The comparison is based on the `host`, `namespace`, `classname`,
        and `keybindings`, instance attributes, in descending precedence.

        The `host` and `namespace` and `classname` attributes are compared
        case-insensitively.

        Raises `TypeError', if the `other` object is not a
        :class:`~pywbem.CIMInstanceName` object.
        """
        if self is other:
            return 0
        if not isinstance(other, CIMInstanceName):
            raise TypeError("other must be CIMInstanceName, but is: %s" %
                            type(other))
        return (cmpname(self.host, other.host) or
                cmpname(self.namespace, other.namespace) or
                cmpname(self.classname, other.classname) or
                cmpitem(self.keybindings, other.keybindings))

    def __str__(self):
        """
        Return the untyped WBEM URI of the CIM instance path represented
        by the :class:`~pywbem.CIMInstanceName` object.

        The returned WBEM URI is consistent with :term:`DSP0207`.

        The key properties in the returned WBEM URI will be ordered by their
        names.
        """

        ret_str = ''

        if self.host is not None:
            ret_str += '//%s/' % self.host

        if self.namespace is not None:
            ret_str += '%s:' % self.namespace

        ret_str += '%s.' % self.classname

        for key in sorted(self.keybindings.iterkeys()):
            value = self.keybindings[key]

            ret_str += '%s=' % key

            if isinstance(value, (six.integer_types, bool, float)):
                ret_str += str(value)
            elif isinstance(value, CIMInstanceName):
                ret_str += '"%s"' % str(value).replace('\\', '\\\\').replace(
                    '"', '\\"')
            else:
                ret_str += '"%s"' % value

            ret_str += ','

        return ret_str[:-1]

    def __repr__(self):
        """
        Return a string representation of the
        :class:`~pywbem.CIMInstanceName` object that is suitable for
        debugging.

        The key bindings will be ordered by their names in the result.
        """

        return '%s(classname=%r, keybindings=%r, ' \
               'namespace=%r, host=%r)' % \
               (self.__class__.__name__, self.classname, self.keybindings,
                self.namespace, self.host)

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
        Return a copy of the :class:`~pywbem.CIMInstanceName` object.
        """

        result = CIMInstanceName(self.classname)
        result.keybindings = self.keybindings.copy()
        result.host = self.host
        result.namespace = self.namespace

        return result

    def update(self, *args, **kwargs):
        """
        Add the positional arguments and keyword arguments to the keybindings,
        updating the values of those that already exist.
        """
        self.keybindings.update(*args, **kwargs)

    def has_key(self, key):
        """
        Return a boolean indicating whether the instance path has a
        keybinding with name `key`.
        """
        return key in self.keybindings

    def get(self, key, default=None):
        """
        Return the value of the keybinding with name `key`, or a default
        value if a keybinding with that name does not exist.
        """
        return self.keybindings.get(key, default)

    def keys(self):
        """
        Return a copied list of the keybinding names (in their original
        lexical case).
        """
        return self.keybindings.keys()

    def values(self):
        """
        Return a copied list of the keybinding values.
        """
        return self.keybindings.values()

    def items(self):
        """
        Return a copied list of the keybindings, where each item is a tuple
        of its keybinding name (in the original lexical case) and its value.
        """
        return self.keybindings.items()

    def iterkeys(self):
        """
        Iterate through the keybinding names (in their original lexical case).i
        """
        return self.keybindings.iterkeys()

    def itervalues(self):
        """
        Iterate through the keybinding values.
        """
        return self.keybindings.itervalues()

    def iteritems(self):
        """
        Iterate through the keybindings, where each item is a tuple of the
        keybinding name (in the original lexical case) and the keybinding
        value.
        """
        return self.keybindings.iteritems()

    # pylint: disable=too-many-branches
    def tocimxml(self):
        """
        Return the CIM-XML representation of the
        :class:`~pywbem.CIMInstanceName` object,
        as an instance of an appropriate subclass of :term:`Element`.

        The returned CIM-XML representation is consistent with :term:`DSP0201`.
        """

        if not isinstance(self.keybindings, NocaseDict):
            raise TypeError("keybindings must be a NocaseDict but is: %r" %
                            self.keybindings)

        kbs = []

        for key_bind in self.keybindings.items():

            # Keybindings can be integers, booleans, strings or
            # value references.

            if hasattr(key_bind[1], 'tocimxml'):
                kbs.append(cim_xml.KEYBINDING(
                    key_bind[0],
                    cim_xml.VALUE_REFERENCE(key_bind[1].tocimxml())))
                continue

            if isinstance(key_bind[1], bool):
                type_ = 'boolean'
                if key_bind[1]:
                    value = 'TRUE'
                else:
                    value = 'FALSE'
            elif isinstance(key_bind[1], six.integer_types + (float,)):
                # Numeric CIM data types derive from int, long or float.
                # Note: int is a subtype of bool, but bool is already
                # tested further up.
                type_ = 'numeric'
                value = str(key_bind[1])
            elif isinstance(key_bind[1], six.string_types):
                type_ = 'string'
                value = _ensure_unicode(key_bind[1])
            else:
                raise TypeError('Invalid keybinding type for keybinding '
                                '%s: %s' %
                                (key_bind[0], builtin_type(key_bind[1])))

            kbs.append(cim_xml.KEYBINDING(
                key_bind[0],
                cim_xml.KEYVALUE(value, type_)))

        instancename_xml = cim_xml.INSTANCENAME(self.classname, kbs)

        # Instance name plus namespace = LOCALINSTANCEPATH

        if self.host is None and self.namespace is not None:
            return cim_xml.LOCALINSTANCEPATH(
                cim_xml.LOCALNAMESPACEPATH(
                    [cim_xml.NAMESPACE(ns)
                     for ns in self.namespace.split('/')]),
                instancename_xml)

        # Instance name plus host and namespace = INSTANCEPATH

        if self.host is not None and self.namespace is not None:
            return cim_xml.INSTANCEPATH(
                cim_xml.NAMESPACEPATH(
                    cim_xml.HOST(self.host),
                    cim_xml.LOCALNAMESPACEPATH([
                        cim_xml.NAMESPACE(ns)
                        for ns in self.namespace.split('/')])),
                instancename_xml)

        # Just a regular INSTANCENAME

        return instancename_xml

    def tocimxmlstr(self, indent=None):
        """
        Return the CIM-XML representation of the
        :class:`~pywbem.CIMInstanceName` object, as a :term:`unicode string`.

        The returned CIM-XML representation is consistent with :term:`DSP0201`.

        Parameters:

          indent (:term:`string` or :term:`integer`):
            `None` indicates that a single-line version of the XML should be
            returned, without any whitespace between the XML elements.

            Other values indicate that a prettified, multi-line version of the
            XML should be returned. A string value specifies the indentation
            string to be used for each level of nested XML elements. An integer
            value specifies an indentation string of so many blanks.

        Returns:

            The CIM-XML representation of the value, as a
            :term:`unicode string`.
        """
        return tocimxmlstr(self, indent)


class CIMInstance(_CIMComparisonMixin):
    """
    A representation of a CIM instance in a CIM namespace in a WBEM server,
    optionally including its instance path.
    """

    # pylint: disable=too-many-arguments
    def __init__(self, classname, properties=None, qualifiers=None,
                 path=None, property_list=None):
        """
        Parameters:

          classname (:term:`string`):
            Name of the creation class for the instance.

            Must not be `None`.

          properties (:class:`py:dict` or `NocaseDict`_):
            Properties for the instance.

            A shallow copy of the provided dictionary will be stored in the
            ``CIMInstance`` object.

            Each dictionary item specifies one property value, with:

            * key (:term:`string`):
              Property name. Lexical case is preserved. Must not be `None`.
            * value (:term:`CIM data type` or :class:`~pywbem.CIMProperty`):
              Property value.
              If specified as a :term:`CIM data type`, a new
              :class:`~pywbem.CIMProperty` object will be created from it,
              and the new object will be stored in the ``CIMInstance`` object.
              If specified as a :class:`~pywbem.CIMProperty` object, its `name`
              attribute must be equal (case insensitively) to the dictionary
              key, and the provided object will be stored in the
              ``CIMInstance`` object (no copy is made).

            `None` is interpreted as an empty set of properties.

          qualifiers (:class:`py:dict` or `NocaseDict`_):
            Qualifiers for the instance.

            A shallow copy of the provided dictionary will be stored in the
            ``CIMInstance`` object.

            Each dictionary item specifies one qualifier value, with:

            * key (:term:`string`):
              Qualifier name. Lexical case is preserved. Must not be `None`.
            * value (:class:`~pywbem.CIMQualifier`):
              Qualifier value.
              The `name` attribute of the provided object must be equal (case
              insensitively) to the dictionary key, and the provided object
              will be stored in the ``CIMInstance`` object (no copy is made).

            `None` is interpreted as an empty set of qualifiers.

            Note that :term:`DSP0200` has deprecated the presence of qualifier
            values on CIM instances.

          path (:class:`~pywbem.CIMInstanceName`):
            Instance path for the instance.

            The provided object will be stored in the ``CIMInstance`` object
            (no copy is made).

            `None` means that the instance path is unspecified, and the
            same-named attribute in the ``CIMInstance`` object will also be
            `None`.

          property_list (:term:`py:iterable` of :term:`string`):
            List of property names for use as a filter by some operations on
            the instance. The property names may have any lexical case.

            A copy of the provided iterable will be stored in the
            ``CIMInstance`` object, and the property names will be converted to
            lower case.

            `None` means that the properties are not filtered, and the
            same-named attribute in the ``CIMInstance`` object will also be
            `None`.
        """

        self.classname = _ensure_unicode(classname)
        self.qualifiers = NocaseDict(qualifiers)
        # TODO: Add support for accepting qualifiers as plain dict
        self.path = path
        if property_list is not None:
            self.property_list = [_ensure_unicode(x).lower()
                                  for x in property_list]
        else:
            self.property_list = None

        # Assign initialised property values and run through
        # __setitem__ to enforce CIM data types for each property.

        self.properties = NocaseDict()
        if properties:
            for key, value in properties.items():
                self.__setitem__(key, value)

    @property
    def classname(self):
        """
        :term:`unicode string`: Name of the creation class of the instance.

        Will not be `None`.

        This attribute is settable. For details, see the description of the
        same-named constructor parameter,
        except that the provided value must be a :term:`unicode string`.
        """
        return self._classname

    @classname.setter
    def classname(self, classname):
        """Setter method; for a description see the getter method."""
        # pylint: disable=attribute-defined-outside-init
        self._classname = classname

    @property
    def properties(self):
        """
        `NocaseDict`_: Properties of the CIM instance.

        Each dictionary item specifies one property value, with:

        * key (:term:`unicode string`): Property name. Its lexical case was
          preserved.
        * value (:class:`~pywbem.CIMProperty`): Property value.

        Will not be `None`.

        This attribute is settable; setting it will cause the current CIM
        properties to be replaced with the new properties, and will also cause
        the values of corresponding keybindings in the instance path (if set)
        to be updated. For details, see the description of the same-named
        constructor parameter. Note that the property value may be specified as
        a :term:`CIM data type` or as a :class:`~pywbem.CIMProperty` object.

        The CIM property values can also be accessed and manipulated one by one
        because the attribute value is a modifiable dictionary. In that case,
        the provided input value must be a :class:`~pywbem.CIMProperty`
        object::

            inst = CIMInstance(...)
            p1 = CIMProperty('p1', ...)

            inst.properties['p1'] = p1  # Set "p1" to p1 (add if needed)
            p1 = inst.properties['p1']  # Access "p1"
            del inst.properties['p1']  # Delete "p1" from the instance

        In addition, the CIM properties can be accessed and manipulated one by
        one by using the entire :class:`~pywbem.CIMInstance` object like a
        dictionary. Again, the provided input value must be a
        :class:`~pywbem.CIMProperty` object in this case::

            inst = CIMInstance(...)
            p2 = CIMProperty('p2', ...)

            inst['p2'] = p2  # Set "p2" to p2 (add if needed)
            p2 = inst['p2']  # Access "p2"
            del inst['p2']  # Delete "p2" from the instance
        """
        return self._properties

    @properties.setter
    def properties(self, properties):
        """Setter method; for a description see the getter method."""
        # pylint: disable=attribute-defined-outside-init
        self._properties = properties

    @property
    def qualifiers(self):
        """
        `NocaseDict`_: Qualifiers of the CIM instance.

        Each dictionary item specifies one qualifier value, with:

        * key (:term:`string`): Qualifier name. Its lexical case was
          preserved.
        * value (:class:`~pywbem.CIMQualifier`): Qualifier value.

        Will not be `None`.

        This attribute is settable; setting it will cause the current
        qualifiers to be replaced with the new qualifiers. For details, see
        the description of the same-named constructor parameter.

        The qualifier values can also be accessed and manipulated one by one
        because the attribute value is a modifiable dictionary.

        Note that :term:`DSP0200` has deprecated the presence of qualifier
        values on CIM instances.
        """
        return self._qualifiers

    @qualifiers.setter
    def qualifiers(self, qualifiers):
        """Setter method; for a description see the getter method."""
        # pylint: disable=attribute-defined-outside-init
        self._qualifiers = qualifiers

    @property
    def path(self):
        """
        :class:`~pywbem.CIMInstanceName`: Instance path of the instance.

        `None` means that the instance path is unspecified.

        This attribute is settable. For details, see the description of the
        same-named constructor parameter.
        """
        return self._path

    @path.setter
    def path(self, path):
        """Setter method; for a description see the getter method."""
        # pylint: disable=attribute-defined-outside-init
        self._path = path

    @property
    def property_list(self):
        """
        :term:`py:list` of :term:`unicode string`: List of property names for
        use as a filter by some operations on the instance. The property names
        are in lower case.

        `None` means that the properties are not filtered.

        This attribute is settable. For details, see the description of the
        same-named constructor parameter.
        """
        return self._property_list

    @property_list.setter
    def property_list(self, property_list):
        """Setter method; for a description see the getter method."""
        # pylint: disable=attribute-defined-outside-init
        self._property_list = property_list

    def _cmp(self, other):
        """
        Comparator function for two :class:`~pywbem.CIMInstance` objects.

        The comparison is based on the `classname`, `path`, `properties`,
        and `qualifiers` instance attributes, in descending precedence.

        The `classname` attribute is compared case-insensitively.
        """
        if self is other:
            return 0
        if not isinstance(other, CIMInstance):
            raise TypeError("other must be CIMInstance, but is: %s" %
                            type(other))
        return (cmpname(self.classname, other.classname) or
                cmpitem(self.path, other.path) or
                cmpitem(self.properties, other.properties) or
                cmpitem(self.qualifiers, other.qualifiers))

    def __str__(self):
        """
        Return a short string representation of the
        :class:`~pywbem.CIMInstance` object for human consumption.
        """

        return '%s(classname=%r, path=%r, ...)' % \
               (self.__class__.__name__, self.classname, self.path)

    def __repr__(self):
        """
        Return a string representation of the :class:`~pywbem.CIMInstance`
        object that is suitable for debugging.

        The properties and qualifiers will be ordered by their names in the
        result.
        """

        return '%s(classname=%r, path=%r, ' \
               'properties=%r, property_list=%r, ' \
               'qualifiers=%r)' % \
               (self.__class__.__name__, self.classname, self.path,
                self.properties, self.property_list,
                self.qualifiers)

    def __contains__(self, key):
        return key in self.properties

    def __getitem__(self, key):
        return self.properties[key].value

    def __setitem__(self, key, value):

        # Don't let anyone set integer or float values.  You must use
        # a subclass from the cim_type module.

        # Note: The CIM data types are derived from the built-in types,
        # so we cannot use isinstance() for this test.
        # pylint: disable=unidiomatic-typecheck
        if builtin_type(value) in six.integer_types + (float,):
            raise TypeError(
                "Type of numeric value for a property must be a "
                "CIM data type, but is %s" % builtin_type(value))

        if self.property_list is not None and key.lower() not in \
                self.property_list:
            if self.path is not None and key not in self.path.keybindings:
                return

        # Convert value to appropriate pywbem type
        if isinstance(value, CIMProperty):
            val = value
        else:
            val = CIMProperty(key, value)

        self.properties[key] = val
        if self.path is not None and key in self.path.keybindings:
            self.path[key] = val.value

    def __delitem__(self, key):
        del self.properties[key]

    def __len__(self):
        return len(self.properties)

    def __iter__(self):
        return six.iterkeys(self.properties)

    def copy(self):
        """
        Return copy of the :class:`~pywbem.CIMInstance` object.
        """

        result = CIMInstance(self.classname)
        result.properties = self.properties.copy()
        result.qualifiers = self.qualifiers.copy()
        result.path = (self.path is not None and
                       [self.path.copy()] or [None])[0]

        return result

    def update(self, *args, **kwargs):
        """
        Add the positional arguments and keyword arguments to the properties,
        updating the values of those that already exist.
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
        Update the values of already existing properties from the positional
        arguments and keyword arguments.
        """

        for mapping in args:
            if hasattr(mapping, 'items'):
                for key, value in mapping.items():
                    try:
                        prop = self.properties[key]
                    except KeyError:
                        continue
                    prop.value = tocimobj(prop.type, value)
            else:
                for (key, value) in mapping:
                    try:
                        prop = self.properties[key]
                    except KeyError:
                        continue
                    prop.value = tocimobj(prop.type, value)
        for key, value in kwargs.items():
            try:
                prop = self.properties[key]
            except KeyError:
                continue
            prop.value = tocimobj(prop.type, value)

    def has_key(self, key):
        """
        Return a boolean indicating whether the instance has a property with
        name `key`.
        """
        return key in self.properties

    def get(self, key, default=None):
        """
        Return the value of the property with name `key`, or a default value if
        a property with that name does not exist.
        """
        prop = self.properties.get(key, None)
        return default if prop is None else prop.value

    def keys(self):
        """
        Return a copied list of the property names (in their original lexical
        case).
        """
        return self.properties.keys()

    def values(self):
        """
        Return a copied list of the property values.
        """
        return [v.value for v in self.properties.values()]

    def items(self):
        """
        Return a copied list of the properties, where each item is a tuple
        of the property name (in the original lexical case) and the property
        value.
    """
        return [(key, v.value) for key, v in self.properties.items()]

    def iterkeys(self):
        """
        Iterate through the property names (in their original lexical
        case).
    """
        return self.properties.iterkeys()

    def itervalues(self):
        """
    Iterate through the property values.
    """
        for _, val in self.properties.iteritems():
            yield val.value

    def iteritems(self):
        """
        Iterate through the property names (in their original lexical case).
        """
        for key, val in self.properties.iteritems():
            yield (key, val.value)

    def tocimxml(self):
        """
        Return the CIM-XML representation of the
        :class:`~pywbem.CIMInstance` object,
        as an instance of an appropriate subclass of :term:`Element`.

        The returned CIM-XML representation is consistent with :term:`DSP0201`.
        """

        props = []

        for key, value in self.properties.items():

            # Value has already been converted into a CIM object
            # property type (e.g for creating null property values).

            if isinstance(value, CIMProperty):
                props.append(value)
                continue

            props.append(CIMProperty(key, value))

        instance_xml = cim_xml.INSTANCE(
            self.classname,
            properties=[p.tocimxml() for p in props],
            qualifiers=[q.tocimxml() for q in self.qualifiers.values()])

        if self.path is None:
            return instance_xml

        return cim_xml.VALUE_NAMEDINSTANCE(self.path.tocimxml(),
                                           instance_xml)

    def tocimxmlstr(self, indent=None):
        """
        Return the CIM-XML representation of the
        :class:`~pywbem.CIMInstance` object, as a :term:`unicode string`.

        The returned CIM-XML representation is consistent with :term:`DSP0201`.

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
        return tocimxmlstr(self, indent)

    def tomof(self, indent=0):
        """
        Return a :term:`unicode string` that is a MOF fragment with the
        instance specification represented by the :class:`~pywbem.CIMInstance`
        object.

        Parameters:

          indent (:term:`integer`):
              Number of spaces the initial line of the output is indented.
        """

        ret_str = 'instance of %s {\n' % self.classname
        for prop in self.properties.values():
            ret_str += prop.tomof(True, (indent + MOF_INDENT))

        ret_str += '};\n'
        return ret_str


class CIMClassName(_CIMComparisonMixin):
    """
    A CIM class path (aka *CIM class name*).

    A CIM class path references a CIM class in a CIM namespace in a WBEM
    server. Namespace and WBEM server may be unspecified.
    """

    def __init__(self, classname, host=None, namespace=None):
        """
        Parameters:

          classname (:term:`string`):
            Class name of the referenced class.

            Must not be `None`.

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
            same-named attribute in the ``CIMClassName`` object will also be
            `None`.

          namespace (:term:`string`):
            Name of the CIM namespace containing the referenced class.

            `None` means that the namespace is unspecified, and the
            same-named attribute in the ``CIMClassName`` object will also be
            `None`.
        """

        # Make sure we process Unicode strings
        classname = _ensure_unicode(classname)
        host = _ensure_unicode(host)
        namespace = _ensure_unicode(namespace)

        if not isinstance(classname, six.string_types):
            raise TypeError(
                "classname argument has an invalid type: %s "
                "(expected string)" % builtin_type(classname))

        # DSP0004 defines a certain format of CIM class names, but we don't
        # check that in pywbem because we don't parse the class name anywhere.
        # Also, some WBEM servers implement special classes that deviate from
        # that format.

        self.classname = classname
        self.host = host
        self.namespace = namespace

    @property
    def classname(self):
        """
        :term:`unicode string`: Class name of the referenced class.

        Will not be `None`.

        This attribute is settable. For details, see the description of the
        same-named constructor parameter.
        """
        return self._classname

    @classname.setter
    def classname(self, classname):
        """Setter method; for a description see the getter method."""
        # pylint: disable=attribute-defined-outside-init
        self._classname = classname

    @property
    def namespace(self):
        """
        :term:`unicode string`: Name of the CIM namespace containing the
        referenced class.

        `None` means that the namespace is unspecified.

        This attribute is settable. For details, see the description of the
        same-named constructor parameter.
        """
        return self._namespace

    @namespace.setter
    def namespace(self, namespace):
        """Setter method; for a description see the getter method."""
        # pylint: disable=attribute-defined-outside-init
        self._namespace = namespace

    @property
    def host(self):
        """
        :term:`unicode string`: Host and optionally port of the WBEM server
        containing the CIM namespace of the referenced class.

        For details about the string format, see the same-named constructor
        parameter.

        `None` means that the host and port are unspecified.

        This attribute is settable. For details, see the description of the
        same-named constructor parameter.
        """
        return self._host

    @host.setter
    def host(self, host):
        """Setter method; for a description see the getter method."""
        # pylint: disable=attribute-defined-outside-init
        self._host = host

    def copy(self):
        """
        Return a copy the :class:`~pywbem.CIMClassName` object.
        """
        return CIMClassName(self.classname, host=self.host,
                            namespace=self.namespace)

    def _cmp(self, other):
        """
        Comparator function for two :class:`~pywbem.CIMClassName` objects.

        The comparison is based on the `host`, `namespace`, and `classname`
        attributes of the :class:`~pywbem.CIMClassName` objects, in descending
        precedence.

        All of them are compared case-insensitively.
        """
        if self is other:
            return 0
        if not isinstance(other, CIMClassName):
            raise TypeError("other must be CIMClassName, but is: %s" %
                            type(other))
        return (cmpname(self.host, other.host) or
                cmpname(self.namespace, other.namespace) or
                cmpname(self.classname, other.classname))

    def __str__(self):
        """
        Return the untyped WBEM URI of the CIM class path represented by the
        :class:`~pywbem.CIMClassName` object.

        The returned WBEM URI is consistent with :term:`DSP0207`.
        """

        ret_str = ''

        if self.host is not None:
            ret_str += '//%s/' % self.host

        if self.namespace is not None:
            ret_str += '%s:' % self.namespace

        ret_str += self.classname

        return ret_str

    def __repr__(self):
        """
        Return a string representation of the :class:`~pywbem.CIMClassName`
        object that is suitable for debugging.
        """
        return '%s(classname=%r, namespace=%r, ' \
               'host=%r)' % \
               (self.__class__.__name__, self.classname, self.namespace,
                self.host)

    def tocimxml(self):
        """
        Return the CIM-XML representation of the
        :class:`~pywbem.CIMClassName` object,
        as an instance of an appropriate subclass of :term:`Element`.

        The returned CIM-XML representation is consistent with :term:`DSP0201`.
        """

        classname = cim_xml.CLASSNAME(self.classname)

        if self.namespace is not None:

            localnsp = cim_xml.LOCALNAMESPACEPATH(
                [cim_xml.NAMESPACE(ns)
                 for ns in self.namespace.split('/')])

            if self.host is not None:

                # Classname + namespace + host = CLASSPATH

                return cim_xml.CLASSPATH(
                    cim_xml.NAMESPACEPATH(cim_xml.HOST(self.host), localnsp),
                    classname)

            # Classname + namespace = LOCALCLASSPATH

            return cim_xml.LOCALCLASSPATH(localnsp, classname)

        # Just classname = CLASSNAME

        return cim_xml.CLASSNAME(self.classname)

    def tocimxmlstr(self, indent=None):
        """
        Return the CIM-XML representation of the
        :class:`~pywbem.CIMClassName` object, as a :term:`unicode string`.

        The returned CIM-XML representation is consistent with :term:`DSP0201`.

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
        return tocimxmlstr(self, indent)


class CIMClass(_CIMComparisonMixin):
    """
    A representation of a CIM class in a CIM namespace in a WBEM server,
    optionally including its class path.
    """

    # pylint: disable=too-many-arguments
    def __init__(self, classname, properties=None, methods=None,
                 superclass=None, qualifiers=None, path=None):
        """
        Parameters:

          classname (:term:`string`):
            Class name of the class.

            Must not be `None`.

          properties (:class:`py:dict` or `NocaseDict`_):
            Properties (declarations) for the class.

            A shallow copy of the provided dictionary will be stored in the
            ``CIMClass`` object.

            Each dictionary item specifies one property, with:

            * key (:term:`string`):
              Property name. Lexical case is preserved. Must not be `None`.
            * value (:class:`~pywbem.CIMProperty`):
              Property declaration.
              The `name` attribute of the provided object must be equal (case
              insensitively) to the dictionary key, and the provided object
              will be stored in the ``CIMClass`` object (no copy is made).

            `None` is interpreted as an empty set of properties.

          methods (:class:`py:dict` or `NocaseDict`_):
            Method declarations for the class.

            A shallow copy of the provided dictionary will be stored in the
            ``CIMClass`` object.

            Each dictionary item specifies one method (declaration), with:

            * key (:term:`string`):
              Method name. Lexical case is preserved. Must not be `None`.
            * value (:class:`~pywbem.CIMMethod`):
              Method declaration.
              The `name` attribute of the provided object must be equal (case
              insensitively) to the dictionary key, and the provided object
              will be stored in the ``CIMClass`` object (no copy is made).

            `None` is interpreted as an empty set of methods.

          superclass (:term:`string`):
            Name of the superclass for the class.

            `None` means that the class is a top-level class, and the
            same-named attribute in the ``CIMClass`` object will also be
            `None`.

          qualifiers (:class:`py:dict` or `NocaseDict`_):
            Qualifier values for the class.

            A shallow copy of the provided dictionary will be stored in the
            ``CIMClass`` object.

            Each dictionary item specifies one qualifier value, with:

            * key (:term:`string`):
              Qualifier name. Lexical case is preserved. Must not be `None`.
            * value (:class:`~pywbem.CIMQualifier`):
              Qualifier value.
              The `name` attribute of the provided object must be equal (case
              insensitively) to the dictionary key, and the provided object
              will be stored in the ``CIMClass`` object (no copy is made).

            `None` is interpreted as an empty set of qualifiers.

          path (:class:`~pywbem.CIMClassName`):
            Class path for the class.

            The provided object will be stored in the ``CIMClass`` object
            (no copy is made).

            `None` means that the instance path is unspecified, and the
            same-named attribute in the ``CIMClass`` object will also be
            `None`.

            This parameter has been added in pywbem v0.11.0 as a convenience
            for the user in order so that ``CIMClass`` objects can be
            self-contained w.r.t. their class path.
        """

        self.classname = _ensure_unicode(classname)
        self.properties = NocaseDict(properties)
        self.methods = NocaseDict(methods)
        self.superclass = _ensure_unicode(superclass)
        self.qualifiers = NocaseDict(qualifiers)
        self.path = path

    @property
    def classname(self):
        """
        :term:`unicode string`: Class name of the CIM class.

        Will not be `None`.

        This attribute is settable. For details, see the description of the
        same-named constructor parameter.
        """
        return self._classname

    @classname.setter
    def classname(self, classname):
        """Setter method; for a description see the getter method."""
        # pylint: disable=attribute-defined-outside-init
        self._classname = classname

    @property
    def superclass(self):
        """
        :term:`unicode string`: Class name of the superclass of the CIM class.

        `None` means that the class is a top-level class.

        This attribute is settable. For details, see the description of the
        same-named constructor parameter.
        """
        return self._superclass

    @superclass.setter
    def superclass(self, superclass):
        """Setter method; for a description see the getter method."""
        # pylint: disable=attribute-defined-outside-init
        self._superclass = superclass

    @property
    def properties(self):
        """
        `NocaseDict`_: Properties (declarations) of the CIM class.

        Each dictionary item specifies one property, with:

        * key (:term:`unicode string`): Property name. Its lexical case was
          preserved.
        * value (:class:`~pywbem.CIMProperty`): Property declaration.

        Will not be `None`.

        This attribute is settable; setting it will cause the current CIM
        properties to be replaced with the new properties. For details, see
        the description of the same-named constructor parameter.

        The CIM properties can also be accessed and manipulated one by one
        because the attribute value is a modifiable dictionary::

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
        # pylint: disable=attribute-defined-outside-init
        self._properties = properties

    @property
    def methods(self):
        """
        `NocaseDict`_: Methods (declarations) of the CIM class.

        Each dictionary item specifies one method, with:

        * key (:term:`unicode string`): Method name. Its lexical case was
          preserved.
        * value (:class:`~pywbem.CIMMethod`): Method declaration.

        Will not be `None`.

        This attribute is settable; setting it will cause the current CIM
        methods to be replaced with the new methods. For details, see
        the description of the same-named constructor parameter.

        The CIM methods can also be accessed and manipulated one by one
        because the attribute value is a modifiable dictionary::

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
        # pylint: disable=attribute-defined-outside-init
        self._methods = methods

    @property
    def qualifiers(self):
        """
        `NocaseDict`_: Qualifiers (qualifier values) of the CIM class.

        Each dictionary item specifies one qualifier, with:

        * key (:term:`string`): Qualifier name. Its lexical case was
          preserved.
        * value (:class:`~pywbem.CIMQualifier`): Qualifier value.

        Will not be `None`.

        This attribute is settable; setting it will cause the current
        qualifiers to be replaced with the new qualifiers. For details, see
        the description of the same-named constructor parameter.

        The qualifier values can also be accessed and manipulated one by one
        because the attribute value is a modifiable dictionary::

            cls = CIMClass(...)
            q1 = CIMQualifier('q1', ...)  # must be a CIMQualifier

            cls.qualifiers['q1'] = q1  # Set "q1" to q1 (add if needed)
            q1 = cls.qualifiers['q1']  # Access "q1"
            del cls.qualifiers['q1']  # Delete "q1" from the class
        """
        return self._qualifiers

    @qualifiers.setter
    def qualifiers(self, qualifiers):
        """Setter method; for a description see the getter method."""
        # pylint: disable=attribute-defined-outside-init
        self._qualifiers = qualifiers

    @property
    def path(self):
        """
        :class:`~pywbem.CIMClassName`: Class path of the CIM class.

        `None` means that the class path is unspecified.

        This attribute has been added in pywbem v0.11.0 as a convenience
        for the user in order so that :class:`~pywbem.CIMClass` objects can
        be self-contained w.r.t. their class path.

        This attribute will be set in in any :class:`~pywbem.CIMClass`
        objects returned by :class:`~pywbem.WBEMConnection` methods, based
        on information in the response from the WBEM server.

        This attribute is settable. For details, see the description of the
        same-named constructor parameter.
        """
        return self._path

    @path.setter
    def path(self, path):
        """Setter method; for a description see the getter method."""
        # pylint: disable=attribute-defined-outside-init
        self._path = path

    def _cmp(self, other):
        """
        Comparator function for two :class:`~pywbem.CIMClass` objects.

        The comparison is based on the `classname`, `superclass`, `qualifiers`,
        `properties`, `methods` and `path` instance attributes, in descending
        precedence.

        The `classname` and `superclass` attributes are compared
        case-insensitively.
        """
        if self is other:
            return 0
        if not isinstance(other, CIMClass):
            raise TypeError("other must be CIMClass, but is: %s" %
                            type(other))
        return (cmpname(self.classname, other.classname) or
                cmpname(self.superclass, other.superclass) or
                cmpitem(self.qualifiers, other.qualifiers) or
                cmpitem(self.properties, other.properties) or
                cmpitem(self.methods, other.methods) or
                cmpitem(self.path, other.path))

    def __str__(self):
        """
        Return a short string representation of the
        :class:`~pywbem.CIMClass` object for human consumption.
    """

        return '%s(classname=%r, ...)' % \
               (self.__class__.__name__, self.classname)

    def __repr__(self):
        """
        Return a string representation of the :class:`~pywbem.CIMClass`
        object that is suitable for debugging.

        The properties, method and qualifiers will be ordered by their names in
        the result.
        """

        return '%s(classname=%r, superclass=%r, ' \
               'properties=%r, methods=%r, qualifiers=%r, ' \
               'path=%r)' % \
               (self.__class__.__name__, self.classname, self.superclass,
                self.properties, self.methods, self.qualifiers,
                self.path)

    def copy(self):
        """
        Return a copy of the :class:`~pywbem.CIMClass` object.
        """
        result = CIMClass(self.classname)
        result.properties = self.properties.copy()
        result.methods = self.methods.copy()
        result.superclass = self.superclass
        result.qualifiers = self.qualifiers.copy()
        result.path = (self.path is not None and
                       [self.path.copy()] or [None])[0]

        return result

    def tocimxml(self):
        """
        Return the CIM-XML representation of the
        :class:`~pywbem.CIMClass` object,
        as an instance of an appropriate subclass of :term:`Element`.

        The returned CIM-XML representation is consistent with :term:`DSP0201`.

        The :attr:`~pywbem.CIMClass.path` attribute of this object will not be
        included in the returned CIM-XML representation.
        """
        return cim_xml.CLASS(
            self.classname,
            properties=[p.tocimxml() for p in self.properties.values()],
            methods=[m.tocimxml() for m in self.methods.values()],
            qualifiers=[q.tocimxml() for q in self.qualifiers.values()],
            superclass=self.superclass)

    def tocimxmlstr(self, indent=None):
        """
        Return the CIM-XML representation of the
        :class:`~pywbem.CIMClass` object, as a :term:`unicode string`.

        The returned CIM-XML representation is consistent with :term:`DSP0201`.

        The :attr:`~pywbem.CIMClass.path` attribute of this object will not be
        included in the returned CIM-XML representation.

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
        return tocimxmlstr(self, indent)

    def tomof(self):
        """
        Return a :term:`unicode string` that is a MOF fragment with the
        class definition represented by the :class:`~pywbem.CIMClass`
        object.

        The :attr:`~pywbem.CIMClass.path` attribute of this object will not be
        included in the returned MOF string.
        """

        indent = MOF_INDENT

        # Qualifiers definition or empty line
        ret_str = '%s\n' % (_makequalifiers(self.qualifiers,
                                            indent))

        ret_str += 'class %s ' % self.classname

        # Superclass

        if self.superclass is not None:
            ret_str += ': %s ' % self.superclass

        ret_str += '{\n'

        # Properties; indent one level from class definition

        for prop_val in self.properties.values():

            ret_str += prop_val.tomof(False, indent)

        # Methods, indent one level from class definition
        for method in self.methods.values():
            ret_str += '\n%s' % method.tomof(indent)

        ret_str += '};\n'

        return ret_str


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
    """

    # pylint: disable=too-many-statements
    def __init__(self, name, value, type=None,
                 class_origin=None, array_size=None, propagated=None,
                 is_array=None, reference_class=None, qualifiers=None,
                 embedded_object=None):
        # pylint: disable=redefined-builtin,too-many-arguments,too-many-branches
        # pylint: disable=too-many-statements,too-many-instance-attributes
        # pylint: disable=too-many-instance-attributes
        """
        The constructor infers optional parameters that are not specified (for
        example, it infers `type` from the Python type of `value` and other
        information). If the specified parameters are inconsistent, an
        exception is raised. If an optional parameter is needed for some
        reason, an exception is raised.

        Parameters:

          name (:term:`string`):
            Name of the property.

            Must not be `None`.

          value (:term:`CIM data type`):
            Value of the property (interpreted as actual value when
            representing a property value, and as default value for property
            declarations).

            `None` means that the property is Null, and the same-named
            attribute in the ``CIMProperty`` object will also be `None`.

          type (:term:`string`):
            Name of the CIM data type of the property (e.g. ``"uint8"``).

            `None` means that the parameter is unspecified, causing the
            same-named attribute in the ``CIMProperty`` object to be inferred.
            An exception is raised if it cannot be inferred.

          class_origin (:term:`string`):
            The CIM class origin of the property (the name
            of the most derived class that defines or overrides the property in
            the class hierarchy of the class owning the property).

            `None` means that class origin information is not available, and
            the same-named attribute in the ``CIMProperty`` object will also be
            `None`.

          array_size (:term:`integer`):
            The size of the array property, for fixed-size arrays.

            `None` means that the array property has variable size, and
            the same-named attribute in the ``CIMProperty`` object will also be
            `None`.

          propagated (:class:`py:bool`):
            If not `None`, indicates whether the property declaration has been
            propagated from a superclass to this class, or the property value
            has been propagated from the creation class to this instance (the
            latter is not really used).

            `None` means that propagation information is not available, and
            the same-named attribute in the ``CIMProperty`` object will also be
            `None`.

          is_array (:class:`py:bool`):
            A boolean indicating whether the property is an array (`True`) or a
            scalar (`False`).

            `None` means that the parameter is unspecified, causing the
            same-named attribute in the ``CIMProperty`` object to be inferred
            from the `value` parameter, and if that is `None` it defaults to
            `False` (scalar).

          reference_class (:term:`string`):
            For reference properties, the name of the class referenced by the
            property, as declared in the class defining the property (for both,
            property declarations in CIM classes, and property values in CIM
            instances).

            `None` means that the referenced class is unspecified, and the
            same-named attribute in the ``CIMProperty`` object will also be
            `None`.

            Note: Prior to pywbem v0.11.0, the corresponding attribute was
            inferred from the creation class name of a referenced instance.
            This was incorrect and has been fixed in v0.11.0.

          qualifiers (:class:`py:dict` or `NocaseDict`_):
            Qualifier values for the property declaration. Has no meaning for
            property values.

            A shallow copy of the provided dictionary will be stored in the
            ``CIMProperty`` object.

            Each dictionary item specifies one qualifier value, with:

            * key (:term:`string`):
              Qualifier name. Lexical case is preserved. Must not be `None`.
            * value (:class:`~pywbem.CIMQualifier`):
              Qualifier value.
              The `name` attribute of the provided object must be equal (case
              insensitively) to the dictionary key, and the provided object
              will be stored in the ``CIMProperty`` object (no copy is made).

            `None` is interpreted as an empty set of qualifiers.

          embedded_object (:term:`string`):
            A string value indicating the kind of embedded object represented
            by the property value. Has no meaning for property declarations.

            For details about the possible values, see the corresponding
            attribute.

            `None` means that the value is unspecified, causing the same-named
            attribute in the ``CIMProperty`` object to be inferred. An
            exception is raised if it cannot be inferred.

        Examples:

        ::

            # a string property:
            CIMProperty("MyString", "abc")

            # a uint8 property:
            CIMProperty("MyNum", 42, "uint8")

            # a uint8 property:
            CIMProperty("MyNum", Uint8(42))

            # a uint8 array property:
            CIMProperty("MyNumArray", [1,2,3], "uint8")

            # a reference property:
            CIMProperty("MyRef", CIMInstanceName(...))

            # an embedded object property containing a class:
            CIMProperty("MyEmbObj", CIMClass(...))

            # an embedded object property containing an instance:
            CIMProperty("MyEmbObj", CIMInstance(...), embedded_object="object")

            # an embedded instance property:
            CIMProperty("MyEmbInst", CIMInstance(...))

            # a string property that is Null:
            CIMProperty("MyString", None, "string")

            # a uint8 property that is Null:
            CIMProperty("MyNum", None, "uint8")

            # a reference property that is Null:
            CIMProperty("MyRef", None, reference_class="MyClass")

            # an embedded object property that is Null:
            CIMProperty("MyEmbObj", None, embedded_object="object")

            # an embedded instance property that is Null:
            CIMProperty("MyEmbInst", None, embedded_object="instance")
        """

        type_ = type  # Minimize usage of the builtin 'type'

        # Make sure we process Unicode strings
        name = _ensure_unicode(name)
        type_ = _ensure_unicode(type_)
        value = _ensure_unicode(value)
        class_origin = _ensure_unicode(class_origin)
        propagated = _ensure_unicode(propagated)
        reference_class = _ensure_unicode(reference_class)
        embedded_object = _ensure_unicode(embedded_object)

        # Check `name`

        if name is None:
            raise ValueError('Property must have a name')

        # General checks:

        if embedded_object not in (None, 'instance', 'object'):
            raise ValueError('Property %r specifies an invalid '
                             'embedded_object=%r' % (name, embedded_object))

        if is_array not in (None, True, False):
            raise ValueError('Property %r specifies an invalid '
                             'is_array=%r' % (name, is_array))

        # Set up is_array

        if isinstance(value, (list, tuple)):
            is_array = _intended_value(
                True, None, is_array, 'is_array',
                'Property %r has a value that is an array (%s)' %
                (name, builtin_type(value)))
        elif value is not None:  # Scalar value
            is_array = _intended_value(
                False, None, is_array, 'is_array',
                'Property %r has a value that is a scalar (%s)' %
                (name, builtin_type(value)))
        else:  # Null value
            if is_array is None:
                is_array = False  # For compatibility with old default

        if not is_array and array_size is not None:
            raise ValueError('Scalar property %r specifies array_size=%r '
                             '(must be None)' % (name, array_size))

        # Determine type, embedded_object, and reference_class attributes.
        # Make sure value is CIM-typed.

        if is_array:  # Array property
            if reference_class is not None:
                raise ValueError(
                    'Array property %r cannot specify reference_class' % name)
            elif not value or value[0] is None:
                # Cannot infer from value, look at embedded_object and type
                if embedded_object == 'instance':
                    msg = 'Array property %r contains embedded instances' % name
                    type_ = _intended_value('string', None, type_, 'type', msg)
                elif embedded_object == 'object':
                    msg = 'Array property %r contains embedded objects' % name
                    type_ = _intended_value('string', None, type_, 'type', msg)
                elif type_ is not None:
                    # Leave type as specified, but check it for validity
                    dummy_type_obj = type_from_name(type_)
                else:
                    raise ValueError(
                        'Cannot infer type of array property %r that is '
                        'Null, empty, or has Null as its first element' %
                        name)
            elif isinstance(value[0], CIMInstance):
                msg = 'Array property %r contains CIMInstance values' % name
                type_ = _intended_value('string', None, type_, 'type', msg)
                embedded_object = _intended_value(
                    ('instance', 'object'), None, embedded_object,
                    'embedded_object', msg)
            elif isinstance(value[0], CIMClass):
                msg = 'Array property %r contains CIMClass values' % name
                type_ = _intended_value('string', None, type_, 'type', msg)
                embedded_object = _intended_value(
                    'object', None, embedded_object, 'embedded_object', msg)
            elif isinstance(value[0], (datetime, timedelta)):
                value = [CIMDateTime(val) if val is not None
                         else val for val in value]
                msg = 'Array property %r contains datetime or timedelta ' \
                      'values' % name
                type_ = _intended_value('datetime', None, type_, 'type', msg)
                embedded_object = _intended_value(
                    None, None, embedded_object, 'embedded_object', msg)
            elif type_ == 'datetime':
                value = [CIMDateTime(val) if val is not None and
                         not isinstance(val, CIMDateTime)
                         else val for val in value]
                msg = 'Array property %r specifies CIM data type %r' % \
                      (name, type_)
                embedded_object = _intended_value(
                    None, None, embedded_object, 'embedded_object', msg)
            elif type_ is None:
                # Determine simple type from (non-Null) value
                type_ = cimtype(value[0])
                msg = 'Array property %r contains simple typed values ' \
                      'with no CIM data type specified' % name
                embedded_object = _intended_value(
                    None, None, embedded_object, 'embedded_object', msg)
            else:  # type is specified and value (= entire array) is not Null
                # Make sure the array elements are of the corresponding Python
                # type.
                value = [type_from_name(type_)(val) if val is not None
                         else val for val in value]
                msg = 'Array property %r contains simple typed values ' \
                      'and specifies CIM data type %r' % (name, type_)
                embedded_object = _intended_value(
                    None, None, embedded_object, 'embedded_object', msg)
        else:  # Scalar property
            if value is None:
                # Try to infer from embedded_object, reference_class, and type
                if embedded_object == 'instance':
                    msg = 'Property %r contains embedded instance' % name
                    type_ = _intended_value('string', None, type_, 'type', msg)
                    reference_class = _intended_value(
                        None, None, reference_class, 'reference_class', msg)
                elif embedded_object == 'object':
                    msg = 'Property %r contains embedded object' % name
                    type_ = _intended_value('string', None, type_, 'type', msg)
                    reference_class = _intended_value(
                        None, None, reference_class, 'reference_class', msg)
                elif reference_class is not None:
                    msg = 'Property %r is a reference' % name
                    embedded_object = _intended_value(
                        None, None, embedded_object, 'embedded_object', msg)
                    type_ = _intended_value(
                        'reference', None, type_, 'type', msg)
                elif type_ is not None:
                    # Leave type as specified, but check it for validity
                    dummy_type_obj = type_from_name(type_)  # noqa: F841
                else:
                    raise ValueError('Cannot infer type of simple '
                                     'property %r that is Null' % name)
            elif isinstance(value, CIMInstanceName):
                msg = 'Property %r has a CIMInstanceName value with ' \
                      'classname=%r' % (name, value.classname)
                # Note that value.classname is the creation class of the
                # referenced instance, while reference_class is the declared
                # class. Therefore, we cannot default reference_class to
                # value.classname and instead just use reference_class
                # as specified.
                type_ = _intended_value('reference', None, type_, 'type', msg)
                embedded_object = _intended_value(
                    None, None, embedded_object, 'embedded_object', msg)
            elif isinstance(value, CIMInstance):
                msg = 'Property %r has a CIMInstance value' % name
                type_ = _intended_value('string', None, type_, 'type', msg)
                embedded_object = _intended_value(
                    ('instance', 'object'), None, embedded_object,
                    'embedded_object', msg)
                reference_class = _intended_value(
                    None, None, reference_class, 'reference_class', msg)
            elif isinstance(value, CIMClass):
                msg = 'Property %r has a CIMClass value' % name
                type_ = _intended_value('string', None, type_, 'type', msg)
                embedded_object = _intended_value(
                    'object', None, embedded_object, 'embedded_object', msg)
                reference_class = _intended_value(
                    None, None, reference_class, 'reference_class', msg)
            elif isinstance(value, (datetime, timedelta)):
                value = CIMDateTime(value)
                msg = 'Property %r has a datetime or timedelta value' % name
                type_ = _intended_value('datetime', None, type_, 'type', msg)
                embedded_object = _intended_value(
                    None, None, embedded_object, 'embedded_object', msg)
                reference_class = _intended_value(
                    None, None, reference_class, 'reference_class', msg)
            elif type_ == 'datetime':
                if not isinstance(value, CIMDateTime):
                    value = CIMDateTime(value)
                msg = 'Property %r specifies CIM data type %r' % (name, type_)
                embedded_object = _intended_value(
                    None, None, embedded_object, 'embedded_object', msg)
                reference_class = _intended_value(
                    None, None, reference_class, 'reference_class', msg)
            elif type_ is None:
                # Determine simple type from (non-Null) value
                type_ = cimtype(value)
                msg = 'Property %r has a simple typed value ' \
                      'with no CIM data type specified' % name
                embedded_object = _intended_value(
                    None, None, embedded_object, 'embedded_object', msg)
                reference_class = _intended_value(
                    None, None, reference_class, 'reference_class', msg)
            else:  # type is specified and value is not Null
                # Make sure the value is of the corresponding Python type.
                _type_obj = type_from_name(type_)
                value = _type_obj(value)
                msg = 'Property %r has a simple typed value ' \
                      'and specifies CIM data type %r' % (name, type_)
                embedded_object = _intended_value(
                    None, None, embedded_object, 'embedded_object', msg)
                reference_class = _intended_value(
                    None, None, reference_class, 'reference_class', msg)

        # Initialize members
        self.name = name
        self.value = value
        self.type = type_
        self.class_origin = class_origin
        self.array_size = array_size
        self.propagated = propagated
        self.is_array = is_array
        self.reference_class = reference_class
        self.qualifiers = NocaseDict(qualifiers)
        self.embedded_object = embedded_object

    @property
    def name(self):
        """
        :term:`unicode string`: Name of the property.

        Will not be `None`.

        This attribute is settable. For details, see the description of the
        same-named constructor parameter.
        """
        return self._name

    @name.setter
    def name(self, name):
        """Setter method; for a description see the getter method."""
        # pylint: disable=attribute-defined-outside-init
        self._name = name

    @property
    def value(self):
        """
        :term:`CIM data type`: Value of the property (interpreted as actual
        value when representing a property value, and as default value for
        property declarations).

        `None` means that the value is Null.

        For CIM data types string and char16, this attribute will be a
        :term:`unicode string`, even when specified as a :term:`byte string`
        in the constructor.

        This attribute is settable. For details, see the description of the
        same-named constructor parameter.
        """
        return self._value

    @value.setter
    def value(self, value):
        """Setter method; for a description see the getter method."""
        # pylint: disable=attribute-defined-outside-init
        self._value = value

    @property
    def type(self):
        """
        :term:`unicode string`: Name of the CIM data type of the property
        (e.g. ``"uint8"``).

        Will not be `None`.

        This attribute is settable. For details, see the description of the
        same-named constructor parameter.
        """
        return self._type

    @type.setter
    def type(self, type):
        # pylint: disable=redefined-builtin
        """Setter method; for a description see the getter method."""
        # pylint: disable=attribute-defined-outside-init
        self._type = type

    @property
    def reference_class(self):
        """
        :term:`unicode string`:

        For reference properties, the name of the class referenced by the
        property, as declared in the class defining the property (for both,
        property declarations in CIM classes, and property values in CIM
        instances).
        `None` means that the referenced class is unspecified.

        For non-reference properties, will be `None`.

        Note that in CIM instances returned from a WBEM server, DSP0201
        recommends this attribute not to be set. For CIM classes returned from
        a WBEM server, DSP0201 requires this attribute to be set.

        This attribute is settable. For details, see the description of the
        same-named constructor parameter.
        """
        return self._reference_class

    @reference_class.setter
    def reference_class(self, reference_class):
        """Setter method; for a description see the getter method."""
        # pylint: disable=attribute-defined-outside-init
        self._reference_class = reference_class

    @property
    def embedded_object(self):
        """
        :term:`unicode string`: A string value indicating the kind of embedded
        object represented by the property value.

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
        same-named constructor parameter.
        """
        return self._embedded_object

    @embedded_object.setter
    def embedded_object(self, embedded_object):
        """Setter method; for a description see the getter method."""
        # pylint: disable=attribute-defined-outside-init
        self._embedded_object = embedded_object

    @property
    def is_array(self):
        """
        :class:`py:bool`: A boolean indicating whether the property is an array
        (`True`) or a scalar (`False`).

        Will not be `None`.

        This attribute is settable. For details, see the description of the
        same-named constructor parameter.
        """
        return self._is_array

    @is_array.setter
    def is_array(self, is_array):
        """Setter method; for a description see the getter method."""
        # pylint: disable=attribute-defined-outside-init
        self._is_array = is_array

    @property
    def array_size(self):
        """
        :term:`integer`: The size of the array property, for fixed-size arrays.

        `None` means that the array property has variable size, or that it is
        not an array.

        This attribute is settable. For details, see the description of the
        same-named constructor parameter.
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
        :term:`unicode string`: The CIM class origin of the property (the name
        of the most derived class that defines or overrides the property in
        the class hierarchy of the class owning the property).

        `None` means that class origin information is not available.

        This attribute is settable. For details, see the description of the
        same-named constructor parameter.
        """
        return self._class_origin

    @class_origin.setter
    def class_origin(self, class_origin):
        """Setter method; for a description see the getter method."""
        # pylint: disable=attribute-defined-outside-init
        self._class_origin = class_origin

    @property
    def propagated(self):
        """
        :class:`py:bool`: If not `None`, indicates whether the property
        declaration has been propagated from a superclass to this class, or the
        property value has been propagated from the creation class to this
        instance (the latter is not really used).

        `None` means that propagation information is not available.

        This attribute is settable. For details, see the description of the
        same-named constructor parameter.
        """
        return self._propagated

    @propagated.setter
    def propagated(self, propagated):
        """Setter method; for a description see the getter method."""
        # pylint: disable=attribute-defined-outside-init
        self._propagated = propagated

    @property
    def qualifiers(self):
        """
        `NocaseDict`_: Qualifiers (qualifier values) of the property
        declaration.

        Each dictionary item specifies one qualifier, with:

        * key (:term:`string`): Qualifier name. Its lexical case was
          preserved.
        * value (:class:`~pywbem.CIMQualifier`): Qualifier value.

        Will not be `None`.

        This attribute is settable; setting it will cause the current
        qualifiers to be replaced with the new qualifiers. For details, see
        the description of the same-named constructor parameter.

        The qualifier values can also be accessed and manipulated one by one
        because the attribute value is a modifiable dictionary::

            prop = CIMProperty(...)
            q1 = CIMQualifier('q1', ...)  # must be a CIMQualifier

            prop.qualifiers['q1'] = q1  # Set "q1" to q1 (add if needed)
            q1 = prop.qualifiers['q1']  # Access "q1"
            del prop.qualifiers['q1']  # Delete "q1" from the class
        """
        return self._qualifiers

    @qualifiers.setter
    def qualifiers(self, qualifiers):
        """Setter method; for a description see the getter method."""
        # pylint: disable=attribute-defined-outside-init
        self._qualifiers = qualifiers

    def copy(self):
        """
        Return a copy of the :class:`~pywbem.CIMProperty` object.
        """
        return CIMProperty(self.name,
                           self.value,
                           type=self.type,
                           class_origin=self.class_origin,
                           array_size=self.array_size,
                           propagated=self.propagated,
                           is_array=self.is_array,
                           reference_class=self.reference_class,
                           qualifiers=self.qualifiers.copy())

    def __str__(self):
        """
        Return a short string representation of the
        :class:`~pywbem.CIMProperty` object for human consumption.
        """
        return '%s(name=%r, value=%r, type=%r, ' \
               'reference_class=%r, embedded_object=%r, ' \
               'is_array=%r, ...)' % \
               (self.__class__.__name__, self.name, self.value, self.type,
                self.reference_class, self.embedded_object,
                self.is_array)

    def __repr__(self):
        """
        Return a string representation of the :class:`~pywbem.CIMProperty`
        object that is suitable for debugging.

        The qualifiers will be ordered by their names in the result.
        """
        return '%s(name=%r, value=%r, type=%r, ' \
               'reference_class=%r, embedded_object=%r, ' \
               'is_array=%r, array_size=%r, ' \
               'class_origin=%r, propagated=%r, ' \
               'qualifiers=%r)' % \
               (self.__class__.__name__, self.name, self.value, self.type,
                self.reference_class, self.embedded_object,
                self.is_array, self.array_size,
                self.class_origin, self.propagated,
                self.qualifiers)

    def tocimxml(self):
        """
        Return the CIM-XML representation of the
        :class:`~pywbem.CIMProperty` object,
        as an instance of an appropriate subclass of :term:`Element`.

        The returned CIM-XML representation is consistent with :term:`DSP0201`.
        """

        if self.is_array:

            value = self.value
            if value is not None:
                if value:
                    if self.embedded_object is not None:
                        value = [v.tocimxml().toxml() for v in value]
                value = cim_xml.VALUE_ARRAY(
                    [cim_xml.VALUE(
                        atomic_to_cim_xml(v)) for v in value])

            return cim_xml.PROPERTY_ARRAY(
                self.name,
                self.type,
                value,
                self.array_size,
                self.class_origin,
                self.propagated,
                qualifiers=[q.tocimxml() for q in self.qualifiers.values()],
                embedded_object=self.embedded_object)

        elif self.type == 'reference':

            value_reference = None
            if self.value is not None:
                value_reference = cim_xml.VALUE_REFERENCE(self.value.tocimxml())

            return cim_xml.PROPERTY_REFERENCE(
                self.name,
                value_reference,
                reference_class=self.reference_class,
                class_origin=self.class_origin,
                propagated=self.propagated,
                qualifiers=[q.tocimxml() for q in self.qualifiers.values()])

        else:
            value = self.value
            if value is not None:
                if self.embedded_object is not None:
                    value = value.tocimxml().toxml()
                else:
                    value = atomic_to_cim_xml(value)
                value = cim_xml.VALUE(value)

            return cim_xml.PROPERTY(
                self.name,
                self.type,
                value,
                class_origin=self.class_origin,
                propagated=self.propagated,
                qualifiers=[q.tocimxml() for q in self.qualifiers.values()],
                embedded_object=self.embedded_object)

    def tocimxmlstr(self, indent=None):
        """
        Return the CIM-XML representation of the
        :class:`~pywbem.CIMProperty` object, as a :term:`unicode string`.

        The returned CIM-XML representation is consistent with :term:`DSP0201`.

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
        return tocimxmlstr(self, indent)

    def _scalar_value2mof(self, value_, indent):
        """
        Private function to map provided value to string for MOF output.
        Used by :meth:`tomof`.

        Parameters:

          value_ (:term:`CIM data type`): Value to be mapped to string for MOF
            output.

          indent (:term:`integer`): Number of spaces to indent the initial
            line of the generated MOF.
        """

        if self.type == 'string':
            if self.embedded_object is not None:
                # TODO ks 8/16 do special formatting for this so output
                # sort of looks like mof, not just a string with lfs
                val_ = value_.tomof()
            else:
                val_ = value_
            _mof = mofstr(val_, indent=indent)
        elif self.type == 'datetime':
            _mof = '"%s"' % str(value_)
        else:
            _mof = str(value_)
        return _mof

    def _array_val2mof(self, indent, fold):
        """
        Output array of values either on single line or one line per value.
        Used by :meth:`tomof`.

        Parameters:

          indent (:term:`integer`): Number of spaces to indent the initiali
            line of the generated MOF.

          fold (bool): If True, format as instance MOF. Else, format as class
            MOF.
        """
        mof_ = ''

        sep = ', ' if not fold else ',\n' + _indent_str(indent)
        for i, val_ in enumerate(self.value):
            if i > 0:
                mof_ += sep
            mof_ += self._scalar_value2mof(val_, indent)
        return mof_

    def tomof(self, is_instance=True, indent=0):
        """
        Return a string representing the MOF definition of a single property.

        Parameters:

          is_instance (bool): If True, format as instance MOF. Else, format as
            class MOF.

          indent (:term:`integer`): Number of spaces to indent the initial
            line of the generated MOF.
        """

        if is_instance:
            # is an instance; set name
            mof = '%s%s = ' % (_indent_str(indent), self.name)
        else:   # is a class; set type, name, array info
            if self.is_array:
                if self.array_size is not None:
                    array_str = "[%s]" % self.array_size
                else:
                    array_str = "[]"
            else:
                array_str = ''

            mof = '\n'
            if self.qualifiers:
                mof += '%s\n' % ((_makequalifiers(self.qualifiers,
                                                  (indent + MOF_INDENT))))

            mof += '%s%s %s%s' % (_indent_str(indent),
                                  moftype(self.type,
                                          self.reference_class),
                                  self.name, array_str)

        # set the value into the mof
        if self.value is None:
            if is_instance:
                mof += 'NULL'
        elif self.is_array:
            mof += ' = {'
            # output as single line if within width limits
            arr_str = self._array_val2mof(indent, False)
            # If too large, redo with on array element per line
            if len(arr_str) > (MAX_MOF_LINE - indent):
                arr_str = '\n' + _indent_str(indent + MOF_INDENT)
                arr_str += self._array_val2mof((indent + MOF_INDENT), True)
            mof += arr_str + '}'
        else:
            if not is_instance:
                mof += ' = '
            mof += self._scalar_value2mof(self.value, indent)

        mof += ';\n'
        return mof

    def _cmp(self, other):
        """
        Comparator function for two :class:`~pywbem.CIMProperty` objects.

        The comparison is based on the `name`, `value`, `type`,
        `reference_class`, `is_array`, `array_size`, `propagated`,
        `class_origin`, and `qualifiers` instance attributes, in descending
        precedence.

        The `name` and `reference_class` attributes are compared
        case-insensitively.

        Raises `TypeError', if the `other` object is not a
        :class:`~pywbem.CIMProperty` object.
        """
        if self is other:
            return 0
        if not isinstance(other, CIMProperty):
            raise TypeError("other must be CIMProperty, but is: %s" %
                            type(other))
        return (cmpname(self.name, other.name) or
                cmpitem(self.value, other.value) or
                cmpitem(self.type, other.type) or
                cmpname(self.reference_class, other.reference_class) or
                cmpitem(self.is_array, other.is_array) or
                cmpitem(self.array_size, other.array_size) or
                cmpitem(self.propagated, other.propagated) or
                cmpitem(self.class_origin, other.class_origin) or
                cmpitem(self.qualifiers, other.qualifiers))


class CIMMethod(_CIMComparisonMixin):
    """
    A method (declaration) in a CIM class.
    """

    # pylint: disable=too-many-arguments
    def __init__(self, name=None, return_type=None, parameters=None,
                 class_origin=None, propagated=False, qualifiers=None,
                 methodname=None):
        """
        The constructor stores the input parameters as-is and does not infer
        unspecified parameters from the others (like
        :class:`~pywbem.CIMProperty` does).

        Parameters:

          name (:term:`string`):
            Name of the method (just the method name, without class name
            or parenthesis).

            Must not be `None`.

            Deprecated: This argument has been named `methodname` before
            v0.9.0. Using `methodname` as a named argument still works,
            but has been deprecated in v0.9.0.

          return_type (:term:`string`):
            Name of the CIM data type of the method return type
            (e.g. ``"uint32"``).

            Must not be `None`.

          parameters (:class:`py:dict` or `NocaseDict`_):
            Parameter declarations for the method.

            A shallow copy of the provided dictionary will be stored in the
            ``CIMMethod`` object.

            Each dictionary item specifies one parameter declaration, with:

            * key (:term:`string`):
              Parameter name. Lexical case is preserved. Must not be `None`.
            * value (:class:`~pywbem.CIMParameter`):
              Parameter value.
              The `name` attribute of the provided object must be equal (case
              insensitively) to the dictionary key, and the provided object
              will be stored in the ``CIMMethod`` object (no copy is made).

            `None` is interpreted as an empty set of parameters.

          class_origin (:term:`string`):
            The CIM class origin of the method (the name
            of the most derived class that defines or overrides the method in
            the class hierarchy of the class owning the method).

            `None` means that class origin information is not available, and
            the same-named attribute in the ``CIMMethod`` object will also be
            `None`.

          propagated (:class:`py:bool`):
            If not `None`, indicates whether the method has been propagated
            from a superclass to this class.

            `None` means that propagation information is not available, and the
            same-named attribute in the ``CIMMethod`` object will also be
            `None`.

          qualifiers (:class:`py:dict` or `NocaseDict`_):
            Qualifier values for the method.

            A shallow copy of the provided dictionary will be stored in the
            ``CIMMethod`` object.

            Each dictionary item specifies one qualifier value, with:

            * key (:term:`string`):
              Qualifier name. Lexical case is preserved. Must not be `None`.
            * value (:class:`~pywbem.CIMQualifier`):
              Qualifier value.
              The `name` attribute of the provided object must be equal (case
              insensitively) to the dictionary key, and the provided object
              will be stored in the ``CIMMethod`` object (no copy is made).

            `None` is interpreted as an empty set of qualifiers.
        """
        if methodname is not None:
            warnings.warn("methodname is deprecated; use name instead",
                          DeprecationWarning)
            if name is not None:
                raise TypeError("name and methodname cannot be specified both")
            name = methodname
        if name is None:
            raise TypeError("name must not be None")
        self.name = _ensure_unicode(name)
        self.return_type = _ensure_unicode(return_type)
        self.parameters = NocaseDict(parameters)
        self.class_origin = _ensure_unicode(class_origin)
        # TODO: Propagated is bool; _ensure_unicode() is unnecessary
        self.propagated = _ensure_unicode(propagated)
        self.qualifiers = NocaseDict(qualifiers)

        # Check valid `return_type`
        if return_type is None:
            raise ValueError('return_type must not be None')

    @property
    def name(self):
        """
        :term:`unicode string`: Name of the method.

        Will not be `None`.

        This attribute is settable. For details, see the description of the
        same-named constructor parameter.
        """
        return self._name

    @name.setter
    def name(self, name):
        """Setter method; for a description see the getter method."""
        # pylint: disable=attribute-defined-outside-init
        self._name = name

    @property
    def return_type(self):
        """
        :term:`unicode string`: Name of the CIM data type of the method return
        type (e.g. ``"uint32"``).

        Will not be `None`. Note that void return types of
        methods are not supported in CIM.

        This attribute is settable. For details, see the description of the
        same-named constructor parameter.
        """
        return self._return_type

    @return_type.setter
    def return_type(self, return_type):
        """Setter method; for a description see the getter method."""
        # pylint: disable=attribute-defined-outside-init
        self._return_type = return_type

    @property
    def class_origin(self):
        """
        :term:`unicode string`: The CIM class origin of the method (the name
        of the most derived class that defines or overrides the method in
        the class hierarchy of the class owning the method).

        `None` means that class origin information is not available.

        This attribute is settable. For details, see the description of the
        same-named constructor parameter.
        """
        return self._class_origin

    @class_origin.setter
    def class_origin(self, class_origin):
        """Setter method; for a description see the getter method."""
        # pylint: disable=attribute-defined-outside-init
        self._class_origin = class_origin

    @property
    def propagated(self):
        """
        :class:`py:bool`: If not `None`, indicates whether the method has been
        propagated from a superclass to this class.

        `None` means that propagation information is not available.

        This attribute is settable. For details, see the description of the
        same-named constructor parameter.
        """
        return self._propagated

    @propagated.setter
    def propagated(self, propagated):
        """Setter method; for a description see the getter method."""
        # pylint: disable=attribute-defined-outside-init
        self._propagated = propagated

    @property
    def parameters(self):
        """
        `NocaseDict`_: Parameters of the method.

        Each dictionary item specifies one parameter, with:

        * key (:term:`string`): Parameter name. Its lexical case was
          preserved.
        * value (:class:`~pywbem.CIMParameter`): Parameter declaration.

        Will not be `None`.

        This attribute is settable; setting it will cause the current
        parameters to be replaced with the new parameters. For details, see
        the description of the same-named constructor parameter.

        The parameters can also be accessed and manipulated one by one
        because the attribute value is a modifiable dictionary::

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
        self._parameters = parameters

    @property
    def qualifiers(self):
        """
        `NocaseDict`_: Qualifiers (qualifier values) of the method.

        Each dictionary item specifies one qualifier, with:

        * key (:term:`string`): Qualifier name. Its lexical case was
          preserved.
        * value (:class:`~pywbem.CIMQualifier`): Qualifier value.

        Will not be `None`.

        This attribute is settable; setting it will cause the current
        qualifiers to be replaced with the new qualifiers. For details, see
        the description of the same-named constructor parameter.

        The qualifier values can also be accessed and manipulated one by one
        because the attribute value is a modifiable dictionary::

            meth = CIMMethod(...)
            q1 = CIMQualifier('q1', ...)  # must be a CIMQualifier

            meth.qualifiers['q1'] = q1  # Set "q1" to q1 (add if needed)
            q1 = meth.qualifiers['q1']  # Access "q1"
            del meth.qualifiers['q1']  # Delete "q1" from the class
        """
        return self._qualifiers

    @qualifiers.setter
    def qualifiers(self, qualifiers):
        """Setter method; for a description see the getter method."""
        # pylint: disable=attribute-defined-outside-init
        self._qualifiers = qualifiers

    def _cmp(self, other):
        """
        Comparator function for two :class:`~pywbem.CIMMethod` objects.

        The comparison is based on the `name`, `qualifiers`, `parameters`,
        `return_type`, `class_origin` and `propagated` instance attributes,
        in descending precedence.

        The `name` attribute is compared case-insensitively.
        """
        if self is other:
            return 0
        if not isinstance(other, CIMMethod):
            raise TypeError("other must be CIMMethod, but is: %s" %
                            type(other))
        return (cmpname(self.name, other.name) or
                cmpitem(self.qualifiers, other.qualifiers) or
                cmpitem(self.parameters, other.parameters) or
                cmpitem(self.return_type, other.return_type) or
                cmpitem(self.class_origin, other.class_origin) or
                cmpitem(self.propagated, other.propagated))

    def __str__(self):
        """
        Return a short string representation of the
        :class:`~pywbem.CIMMethod` object for human consumption.
        """
        return '%s(name=%r, return_type=%r, ...)' % \
               (self.__class__.__name__, self.name, self.return_type)

    def __repr__(self):
        """
        Return a string representation of the :class:`~pywbem.CIMMethod`
        object that is suitable for debugging.

        The parameters and qualifiers will be ordered by their names in the
        result.
        """
        return '%s(name=%r, return_type=%r, ' \
               'class_origin=%r, propagated=%r, ' \
               'parameters=%r, qualifiers=%r)' % \
               (self.__class__.__name__, self.name, self.return_type,
                self.class_origin, self.propagated,
                self.parameters, self.qualifiers)

    def copy(self):
        """
        Return a copy of the :class:`~pywbem.CIMMethod` object.
        """
        result = CIMMethod(self.name,
                           return_type=self.return_type,
                           class_origin=self.class_origin,
                           propagated=self.propagated)

        result.parameters = self.parameters.copy()
        result.qualifiers = self.qualifiers.copy()

        return result

    def tocimxml(self):
        """
        Return the CIM-XML representation of the
        :class:`~pywbem.CIMMethod` object,
        as an instance of an appropriate subclass of :term:`Element`.

        The returned CIM-XML representation is consistent with :term:`DSP0201`.
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
        Return the CIM-XML representation of the
        :class:`~pywbem.CIMMethod` object, as a :term:`unicode string`.

        The returned CIM-XML representation is consistent with :term:`DSP0201`.

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
        return tocimxmlstr(self, indent)

    def tomof(self, indent):
        """
        Return a :term:`unicode string` that is a MOF fragment with the
        method definition represented by the :class:`~pywbem.CIMMethod`
        object.
        """

        ret_str = ''

        if self.qualifiers:
            ret_str += '%s\n' % (_makequalifiers(self.qualifiers,
                                                 (indent + MOF_INDENT)))
        # TODO is None allowed for return type.
        ret_str += _indent_str(indent)
        if self.return_type is not None:
            ret_str += '%s ' % moftype(self.return_type, None)
            # TODO CIM-XML does not support methods returning reference
            # types(the CIM architecture does).

        if self.parameters.values():
            ret_str += '%s(\n' % (self.name)
            ret_str += ',\n'.join([
                p.tomof(indent + MOF_INDENT)
                for p in self.parameters.values()])
            ret_str += ');\n'
        else:
            ret_str += '%s();\n' % (self.name)

        return ret_str


class CIMParameter(_CIMComparisonMixin):
    """
    A CIM parameter in a method (declaration).
    """

    # pylint: disable=too-many-arguments
    def __init__(self, name, type, reference_class=None, is_array=None,
                 array_size=None, qualifiers=None, value=None):
        # pylint: disable=redefined-builtin
        """
        The constructor stores the input parameters as-is and does
        not infer unspecified parameters from the others
        (like :class:`~pywbem.CIMProperty` does).

        Parameters:

          name (:term:`string`):
            Name of the parameter.

            Must not be `None`.

          type (:term:`string`):
            Name of the CIM data type of the parameter (e.g. ``"uint8"``).

            Must not be `None`.

          reference_class (:term:`string`):
            For reference parameters, the name of the class referenced by the
            parameter, as declared in the class defining the method.

            `None` means that the referenced class is unspecified, and the
            same-named attribute in the ``CIMParameter`` object will also be
            `None`.

          is_array (:class:`py:bool`):
            A boolean indicating whether the parameter is an array (`True`) or a
            scalar (`False`).

            `None` means that it is unspecified whether the parameter is an
            array, and the same-named attribute in the ``CIMParameter`` object
            will also be `None`.

          array_size (:term:`integer`):
            The size of the array parameter, for fixed-size arrays.

            `None` means that the array parameter has variable size, and the
            same-named attribute in the ``CIMParameter`` object will also be
            `None`.

          qualifiers (:class:`py:dict` or `NocaseDict`_):
            Qualifier values for the parameter.

            A shallow copy of the provided dictionary will be stored in the
            ``CIMParameter`` object.

            Each dictionary item specifies one qualifier value, with:

            * key (:term:`string`):
              Qualifier name. Lexical case is preserved. Must not be `None`.
            * value (:class:`~pywbem.CIMQualifier`):
              Qualifier value.
              The `name` attribute of the provided object must be equal (case
              insensitively) to the dictionary key, and the provided object
              will be stored in the ``CIMParameter`` object (no copy is made).

            `None` is interpreted as an empty set of qualifiers.

          value:
            Deprecated: Because the object represents a parameter declaration,
            this parameter does not make any sense. Specifying a value other
            than `None` will issue a :term:`DeprecationWarning`.
        """

        type_ = type  # Minimize usage of the builtin 'type'

        self.name = _ensure_unicode(name)
        self.type = _ensure_unicode(type_)
        self.reference_class = _ensure_unicode(reference_class)
        self.is_array = is_array
        self.array_size = array_size
        self.qualifiers = NocaseDict(qualifiers)
        if value is not None:
            warnings.warn(
                "The value parameter of CIMParameter is deprecated",
                DeprecationWarning)
        self._value = value

    @property
    def name(self):
        """
        :term:`unicode string`: Name of the parameter.

        Will not be `None`.

        This attribute is settable. For details, see the description of the
        same-named constructor parameter.
        """
        return self._name

    @name.setter
    def name(self, name):
        """Setter method; for a description see the getter method."""
        # pylint: disable=attribute-defined-outside-init
        self._name = name

    @property
    def type(self):
        """
        :term:`unicode string`: Name of the CIM data type of the parameter
        (e.g. ``"uint8"``).

        Will not be `None`.

        This attribute is settable. For details, see the description of the
        same-named constructor parameter.
        """
        return self._type

    @type.setter
    def type(self, type):
        # pylint: disable=redefined-builtin
        """Setter method; for a description see the getter method."""
        # pylint: disable=attribute-defined-outside-init
        self._type = type

    @property
    def reference_class(self):
        """
        :term:`unicode string`:

        For reference parameters, the name of the class referenced by the
        parameter, as declared in the class defining the parameter.
        `None` means that the referenced class is unspecified.

        For non-reference parameters, will be `None`.

        This attribute is settable. For details, see the description of the
        same-named constructor parameter.
        """
        return self._reference_class

    @reference_class.setter
    def reference_class(self, reference_class):
        """Setter method; for a description see the getter method."""
        # pylint: disable=attribute-defined-outside-init
        self._reference_class = reference_class

    @property
    def is_array(self):
        """
        :class:`py:bool`: A boolean indicating whether the parameter is an array
        (`True`) or a scalar (`False`).

        Will not be `None`.

        This attribute is settable. For details, see the description of the
        same-named constructor parameter.
        """
        return self._is_array

    @is_array.setter
    def is_array(self, is_array):
        """Setter method; for a description see the getter method."""
        # pylint: disable=attribute-defined-outside-init
        self._is_array = is_array

    @property
    def array_size(self):
        """
        :term:`integer`: The size of the array parameter, for fixed-size
        arrays.

        `None` means that the array parameter has variable size, or that it is
        not an array.

        This attribute is settable. For details, see the description of the
        same-named constructor parameter.
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
        `NocaseDict`_: Qualifiers (qualifier values) of the parameter.

        Each dictionary item specifies one qualifier, with:

        * key (:term:`string`): Qualifier name. Its lexical case was
          preserved.
        * value (:class:`~pywbem.CIMQualifier`): Qualifier value.

        Will not be `None`.

        This attribute is settable; setting it will cause the current
        qualifiers to be replaced with the new qualifiers. For details, see
        the description of the same-named constructor parameter.

        The qualifier values can also be accessed and manipulated one by one
        because the attribute value is a modifiable dictionary::

            parm = CIMParameter(...)
            q1 = CIMQualifier('q1', ...)  # must be a CIMQualifier

            parm.qualifiers['q1'] = q1  # Set "q1" to q1 (add if needed)
            q1 = parm.qualifiers['q1']  # Access "q1"
            del parm.qualifiers['q1']  # Delete "q1" from the class
        """
        return self._qualifiers

    @qualifiers.setter
    def qualifiers(self, qualifiers):
        """Setter method; for a description see the getter method."""
        # pylint: disable=attribute-defined-outside-init
        self._qualifiers = qualifiers

    @property
    def value(self):
        """
        Deprecated: Because the object represents a parameter declaration,
        this attribute does not make any sense. Accessing it will issue
        a :term:`DeprecationWarning`.
        """
        warnings.warn(
            "The value attribute of CIMParameter is deprecated",
            DeprecationWarning)
        return self._value

    @value.setter
    def value(self, value):
        """Setter method; for a description see the getter method."""
        warnings.warn(
            "The value attribute of CIMParameter is deprecated",
            DeprecationWarning)
        # pylint: disable=attribute-defined-outside-init
        self._value = value

    def _cmp(self, other):
        """
        Comparator function for two :class:`~pywbem.CIMParameter` objects.

        The comparison is based on the `name`, `type`, `reference_class`,
        `is_array`, `array_size`, `qualifiers` and `value` instance attributes,
        in descending precedence.

        The `name` attribute is compared case-insensitively.

        Raises `TypeError', if the `other` object is not a
        :class:`~pywbem.CIMParameter` object.
        """

        if self is other:
            return 0
        if not isinstance(other, CIMParameter):
            raise TypeError("other must be CIMParameter, but is: %s" %
                            type(other))
        return (cmpname(self.name, other.name) or
                cmpitem(self.type, other.type) or
                cmpname(self.reference_class, other.reference_class) or
                cmpitem(self.is_array, other.is_array) or
                cmpitem(self.array_size, other.array_size) or
                cmpitem(self.qualifiers, other.qualifiers) or
                cmpitem(self.value, other.value))

    def __str__(self):
        """
        Return a short string representation of the
        :class:`~pywbem.CIMParameter` object for human consumption.
        """
        return '%s(name=%r, type=%r, ' \
               'reference_class=%r, ' \
               'is_array=%r, ...)' % \
               (self.__class__.__name__, self.name, self.type,
                self.reference_class,
                self.is_array)

    def __repr__(self):
        """
        Return a string representation of the :class:`~pywbem.CIMParameter`
        object that is suitable for debugging.

        The qualifiers will be ordered by their names in the result.
        """
        return '%s(name=%r, type=%r, ' \
               'reference_class=%r, ' \
               'is_array=%r, array_size=%r, ' \
               'qualifiers=%r)' % \
               (self.__class__.__name__, self.name, self.type,
                self.reference_class,
                self.is_array, self.array_size,
                self.qualifiers)

    def copy(self):
        """
        Return a copy of the :class:`~pywbem.CIMParameter` object.
        """
        result = CIMParameter(self.name,
                              self.type,
                              reference_class=self.reference_class,
                              is_array=self.is_array,
                              array_size=self.array_size,
                              value=self.value)

        result.qualifiers = self.qualifiers.copy()

        return result

    def tocimxml(self):
        """
        Return the CIM-XML representation of the
        :class:`~pywbem.CIMParameter` object,
        as an instance of an appropriate subclass of :term:`Element`.

        The returned CIM-XML representation is consistent with :term:`DSP0201`.
        """
        if self.type == 'reference':

            if self.is_array:

                array_size = None

                if self.array_size is not None:
                    array_size = str(self.array_size)

                return cim_xml.PARAMETER_REFARRAY(
                    self.name,
                    self.reference_class,
                    array_size,
                    qualifiers=[q.tocimxml()
                                for q in self.qualifiers.values()])

            else:

                return cim_xml.PARAMETER_REFERENCE(
                    self.name,
                    self.reference_class,
                    qualifiers=[q.tocimxml()
                                for q in self.qualifiers.values()])

        elif self.is_array:

            array_size = None

            if self.array_size is not None:
                array_size = str(self.array_size)

            return cim_xml.PARAMETER_ARRAY(
                self.name,
                self.type,
                array_size,
                qualifiers=[q.tocimxml() for q in self.qualifiers.values()])

        else:

            return cim_xml.PARAMETER(
                self.name,
                self.type,
                qualifiers=[q.tocimxml() for q in self.qualifiers.values()])

    def tocimxmlstr(self, indent=None):
        """
        Return the CIM-XML representation of the
        :class:`~pywbem.CIMParameter` object, as a :term:`unicode string`.

        The returned CIM-XML representation is consistent with :term:`DSP0201`.

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
        return tocimxmlstr(self, indent)

    def tomof(self, indent):
        """
        Return a :term:`unicode string` that is a MOF fragment with the
        parameter definition represented by the :class:`~pywbem.CIMParameter`
        object.

        Parameters:
            indent (:term:`integer`): Number of spaces to indent each parameter
        """

        if self.is_array:
            if self.array_size is not None:
                array_str = "[%s]" % self.array_size
            else:
                array_str = "[]"
        else:
            array_str = ''

        rtn_str = ''
        if self.qualifiers:
            rtn_str = '%s\n' % (_makequalifiers(self.qualifiers,
                                                indent + 2))
        rtn_str += '%s%s %s%s' % (_indent_str(indent),
                                  moftype(self.type, self.reference_class),
                                  self.name, array_str)
        return rtn_str


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
    """

    # pylint: disable=too-many-arguments
    def __init__(self, name, value, type=None, propagated=None,
                 overridable=None, tosubclass=None, toinstance=None,
                 translatable=None):
        # pylint: disable=redefined-builtin
        """
        The constructor infers optional parameters that are not specified (for
        example, it infers `type` from the Python type of `value` and other
        information). If the specified parameters are inconsistent, an
        exception is raised. If an optional parameter is needed for some reason,
        an exception is raised.

        Parameters:

          name (:term:`string`):
            Name of the qualifier.

            Must not be `None`.

          value (:term:`CIM data type`):
            Value of the qualifier.

            `None` means that the qualifier is Null, and the same-named
            attribute in the ``CIMQualifier`` object will also be `None`.

          type (:term:`string`):
            Name of the CIM data type of the qualifier (e.g. ``"uint8"``).

            `None` means that the parameter is unspecified, causing the
            same-named attribute in the ``CIMQualifier`` object to be inferred.
            An exception is raised if it cannot be inferred.

          propagated (:class:`py:bool`):
            If not `None`, specifies whether the qualifier value has been
            propagated from a superclass to this class.

            `None` means that this information is not available, and the
            same-named attribute in the ``CIMQualifier`` object will also be
            `None`.

          overridable (:class:`py:bool`):
            If not `None`, specifies whether the qualifier value is overridable
            in subclasses.

            `None` means that this information is not available, and the
            same-named attribute in the ``CIMQualifier`` object will also be
            `None`.

          tosubclass (:class:`py:bool`):
            If not `None`, specifies whether the qualifier value propagates
            to subclasses.

            `None` means that this information is not available, and the
            same-named attribute in the ``CIMQualifier`` object will also be
            `None`.

          toinstance (:class:`py:bool`):
            If not `None`, specifies whether the qualifier value propagates
            to instances.

            `None` means that this information is not available, and the
            same-named attribute in the ``CIMQualifier`` object will also be
            `None`.

            Note that :term:`DSP0200` has deprecated the presence of qualifier
            values on CIM instances.

          translatable (:class:`py:bool`):
            If not `None`, specifies whether the qualifier is translatable.

            `None` means that this information is not available, and the
            same-named attribute in the ``CIMQualifier`` object will also be
            `None`.
        """

        type_ = type  # Minimize usage of the builtin 'type'

        self.name = _ensure_unicode(name)
        self.type = _ensure_unicode(type_)
        # TODO: Propagated is bool; _ensure_unicode() is unnecessary
        self.propagated = _ensure_unicode(propagated)
        self.overridable = overridable
        self.tosubclass = tosubclass
        self.toinstance = toinstance
        self.translatable = translatable

        # Determine type of value if not specified

        if type is None:

            # Can't work out what is going on if type and value are
            # both not set.

            if value is None:
                raise TypeError('Null qualifier "%s" must have a type' % name)

            if isinstance(value, list):

                # Determine type for list value

                if not value:
                    raise TypeError(
                        'Empty qualifier array "%s" must have a type' % name)

                self.type = cimtype(value[0])

            else:

                # Determine type for regular value

                self.type = cimtype(value)

        # Don't let anyone set integer or float values.  You must use
        # a subclass from the cim_type module.

        # Note: The CIM data types are derived from the built-in types,
        # so we cannot use isinstance() for this test.
        # pylint: disable=unidiomatic-typecheck
        if builtin_type(value) in six.integer_types + (float,):
            raise TypeError(
                "Type of numeric value for a qualifier must be a "
                "CIM data type, but is %s" % builtin_type(value))

        self.value = value

    @property
    def name(self):
        """
        :term:`unicode string`: Name of the qualifier.

        Will not be `None`.

        This attribute is settable. For details, see the description of the
        same-named constructor parameter.
        """
        return self._name

    @name.setter
    def name(self, name):
        """Setter method; for a description see the getter method."""
        # pylint: disable=attribute-defined-outside-init
        self._name = name

    @property
    def value(self):
        """
        :term:`CIM data type`: Value of the qualifier.

        `None` means that the value is Null.

        For CIM data types string and char16, this attribute will be a
        :term:`unicode string`, even when specified as a :term:`byte string`
        in the constructor.

        This attribute is settable. For details, see the description of the
        same-named constructor parameter.
        """
        return self._value

    @value.setter
    def value(self, value):
        """Setter method; for a description see the getter method."""
        # pylint: disable=attribute-defined-outside-init
        self._value = value

    @property
    def type(self):
        """
        :term:`unicode string`: Name of the CIM data type of the qualifier
        (e.g. ``"uint8"``).

        Will not be `None`.

        This attribute is settable. For details, see the description of the
        same-named constructor parameter.
        """
        return self._type

    @type.setter
    def type(self, type):
        # pylint: disable=redefined-builtin
        """Setter method; for a description see the getter method."""
        # pylint: disable=attribute-defined-outside-init
        self._type = type

    @property
    def propagated(self):
        """
        :class:`py:bool`: Indicates whether the qualifier value has been
        propagated from a superclass to this class.

        `None` means that propagation information is not available.

        This attribute is settable. For details, see the description of the
        same-named constructor parameter.
        """
        return self._propagated

    @propagated.setter
    def propagated(self, propagated):
        """Setter method; for a description see the getter method."""
        # pylint: disable=attribute-defined-outside-init
        self._propagated = propagated

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
        same-named constructor parameter.
        """
        return self._tosubclass

    @tosubclass.setter
    def tosubclass(self, tosubclass):
        """Setter method; for a description see the getter method."""
        # pylint: disable=attribute-defined-outside-init
        self._tosubclass = tosubclass

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
        same-named constructor parameter.
        """
        return self._toinstance

    @toinstance.setter
    def toinstance(self, toinstance):
        """Setter method; for a description see the getter method."""
        # pylint: disable=attribute-defined-outside-init
        self._toinstance = toinstance

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
        same-named constructor parameter.
        """
        return self._overridable

    @overridable.setter
    def overridable(self, overridable):
        """Setter method; for a description see the getter method."""
        # pylint: disable=attribute-defined-outside-init
        self._overridable = overridable

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
        same-named constructor parameter.
        """
        return self._translatable

    @translatable.setter
    def translatable(self, translatable):
        """Setter method; for a description see the getter method."""
        # pylint: disable=attribute-defined-outside-init
        self._translatable = translatable

    def _cmp(self, other):
        """
        Comparator function for two :class:`~pywbem.CIMQualifier` objects.

        The comparison is based on the `name`, `type`, `value`, `propagated`,
        `overridable`, `tosubclass`, `toinstance`, `translatable` instance
        attributes, in descending precedence.

        The `name` attribute is compared case-insensitively.
        """
        if self is other:
            return 0
        if not isinstance(other, CIMQualifier):
            raise TypeError("other must be CIMQualifier, but is: %s" %
                            type(other))
        return (cmpname(self.name, other.name) or
                cmpitem(self.type, other.type) or
                cmpitem(self.value, other.value) or
                cmpitem(self.propagated, other.propagated) or
                cmpitem(self.overridable, other.overridable) or
                cmpitem(self.tosubclass, other.tosubclass) or
                cmpitem(self.toinstance, other.toinstance) or
                cmpitem(self.translatable, other.translatable))

    def __str__(self):
        """
        Return a short string representation of the
        :class:`~pywbem.CIMQualifier` object for human consumption.
        """
        return "%s(name=%r, value=%r, type=%r, ...)" % \
               (self.__class__.__name__, self.name, self.value, self.type)

    def __repr__(self):
        """
        Return a string representation of the :class:`~pywbem.CIMQualifier`
        object that is suitable for debugging.
        """
        return '%s(name=%r, value=%r, type=%r, ' \
               'tosubclass=%r, overridable=%r, translatable=%r, ' \
               'toinstance=%r, propagated=%r)' % \
               (self.__class__.__name__, self.name, self.value, self.type,
                self.tosubclass, self.overridable, self.translatable,
                self.toinstance, self.propagated)

    def copy(self):
        """
        Return a copy of the :class:`~pywbem.CIMQualifier` object.
        """
        return CIMQualifier(self.name,
                            self.value,
                            type=self.type,
                            propagated=self.propagated,
                            overridable=self.overridable,
                            tosubclass=self.tosubclass,
                            toinstance=self.toinstance,
                            translatable=self.translatable)

    def tocimxml(self):
        """
        Return the CIM-XML representation of the
        :class:`~pywbem.CIMQualifier` object,
        as an instance of an appropriate subclass of :term:`Element`.

        The returned CIM-XML representation is consistent with :term:`DSP0201`.
        """

        value = None

        if isinstance(self.value, list):
            value = cim_xml.VALUE_ARRAY([cim_xml.VALUE(v) for v in self.value])
        elif self.value is not None:
            # used as VALUE.ARRAY and the as VALUE
            value = cim_xml.VALUE(self.value)

        return cim_xml.QUALIFIER(self.name,
                                 self.type,
                                 value,
                                 propagated=self.propagated,
                                 overridable=self.overridable,
                                 tosubclass=self.tosubclass,
                                 toinstance=self.toinstance,
                                 translatable=self.translatable)

    def tocimxmlstr(self, indent=None):
        """
        Return the CIM-XML representation of the
        :class:`~pywbem.CIMQualifier` object, as a :term:`unicode string`.

        The returned CIM-XML representation is consistent with :term:`DSP0201`.

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
        return tocimxmlstr(self, indent)

    def tomof(self, indent=MOF_INDENT):
        """
        Return a :term:`unicode string` that is a MOF fragment with the
        qualifier value represented by the :class:`~pywbem.CIMQualifier`
        object.

        Parameters:
            indent (:term:`integer`): Number of spaces to indent the second and
              subsequent lines of a multi-line result. The first line is not
              indented.
        """

        def valstr(value):
            """
            Return a string that is the MOF literal representing a value.
            """
            if isinstance(value, six.string_types):
                return mofstr(value, indent)
            return str(value)

        if isinstance(self.value, list):
            line_pos = indent + len(self.name) + 4
            values = ''
            for i, val in enumerate(self.value):
                if i != 0:
                    values += ','
                nextval = valstr(val)
                if (line_pos + len(nextval) + 3) > MAX_MOF_LINE:
                    sep = '\n' + _indent_str(indent)
                    line_pos = len(_indent_str(indent)) + 4
                else:
                    sep = ' '

                line_pos += (len(nextval) + 2)
                values += sep + nextval

            mof = '%s {%s%s' % (self.name, values, '}')

        else:
            val = valstr(self.value)
            if len(val) + indent + 4 >= MAX_MOF_LINE:
                mof = '%s (\n%s%s)' % (self.name, _indent_str(indent),
                                       val)
            else:
                mof = '%s (%s)' % (self.name, val)
        return mof


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
          specification :TERM:`DSP0200`

    Because `None` is allowed as a value for the flavors attributes in
    constructing a CIMQualifierDeclaration, the user must insure that any
    flavor which has the value `None` is set to its default value if required
    for subsequent processing.

    The pywbem MOF compiler supplies all of the flavor values so that
    those which were not specified in the MOF are set to the DMTF defined
    default values.
    """

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

          type (:term:`string`):
            Name of the CIM data type of the qualifier (e.g. ``"uint8"``).

            Must not be `None`.

          value (:term:`CIM data type`):
            Default value of the qualifier.

            `None` means a default value of Null, and the same-named attribute
            in the ``CIMQualifierDeclaration`` object will also be `None`.

          is_array (:class:`py:bool`):
            A boolean indicating whether the qualifier is an array (`True`) or
            a scalar (`False`).

            Must not be `None`.

          array_size (:term:`integer`):
            The size of the array qualifier, for fixed-size arrays.

            `None` means that the array qualifier has variable size, and the
            same-named attribute in the ``CIMQualifierDeclaration`` object will
            also be `None`.

          scopes (:class:`py:dict` or `NocaseDict`_):
            Scopes of the qualifier.

            A shallow copy of the provided dictionary will be stored in the
            ``CIMQualifierDeclaration`` object.

            Each dictionary item specifies one scope value, with:

            * key (:term:`string`): Scope name, in upper case. Must not be
              `None`.
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
            same-named attribute in the ``CIMQualifierDeclaration`` object will
            also be `None`.

          tosubclass (:class:`py:bool`):
            If not `None`, specifies the flavor that defines whether the
            qualifier value propagates to subclasses.

            `None` means that this information is not available, and the
            same-named attribute in the ``CIMQualifierDeclaration`` object will
            also be `None`.

          toinstance (:class:`py:bool`):
            If not `None`, specifies the flavor that defines whether the
            qualifier value propagates to instances.

            `None` means that this information is not available, and the
            same-named attribute in the ``CIMQualifierDeclaration`` object will
            also be `None`.

            Note that :term:`DSP0200` has deprecated the presence of qualifier
            values on CIM instances and this flavor is not defined in
            :term:`DSP0004`

          translatable (:class:`py:bool`):
            If not `None`, specifies  the flavor that defines whether the
            qualifier is translatable.

            `None` means that this information is not available, and the
            same-named attribute in the ``CIMQualifierDeclaration`` object will
            also be `None`.
        """

        type_ = type  # Minimize usage of the builtin 'type'

        self.name = _ensure_unicode(name)
        self.type = _ensure_unicode(type_)
        self.value = _ensure_unicode(value)
        self.is_array = is_array
        self.array_size = array_size
        self.scopes = NocaseDict(scopes)
        self.overridable = overridable
        self.tosubclass = tosubclass
        self.toinstance = toinstance
        self.translatable = translatable
        if is_array is None:
            raise ValueError('None not allowed for is_array')
        if array_size and not is_array:
            raise ValueError('QualifierDeclaration array_size allowed only '
                             'when is_array is True.')
        if isinstance(value, list) and not is_array:
            raise ValueError('QualifierDeclaration is_array is False and '
                             'value is a list.')
        elif is_array and value is not None and not isinstance(value, list):
            raise ValueError('QualifierDeclaration is_array is True but '
                             'value is scalar')

    @property
    def name(self):
        """
        :term:`unicode string`: Name of the qualifier.

        Will not be `None`.

        This attribute is settable. For details, see the description of the
        same-named constructor parameter.
        """
        return self._name

    @name.setter
    def name(self, name):
        """Setter method; for a description see the getter method."""
        # pylint: disable=attribute-defined-outside-init
        self._name = name

    @property
    def type(self):
        """
        :term:`unicode string`: Name of the CIM data type of the qualifier
        (e.g. ``"uint8"``).

        Will not be `None`.

        This attribute is settable. For details, see the description of the
        same-named constructor parameter.
        """
        return self._type

    @type.setter
    def type(self, type):
        # pylint: disable=redefined-builtin
        """Setter method; for a description see the getter method."""
        # pylint: disable=attribute-defined-outside-init
        self._type = type

    @property
    def value(self):
        """
        :term:`CIM data type`: Default value of the qualifier.

        `None` means that the value is Null.

        For CIM data types string and char16, this attribute will be a
        :term:`unicode string`, even when specified as a :term:`byte string`
        in the constructor.

        This attribute is settable. For details, see the description of the
        same-named constructor parameter.
        """
        return self._value

    @value.setter
    def value(self, value):
        """Setter method; for a description see the getter method."""
        # pylint: disable=attribute-defined-outside-init
        self._value = value

    @property
    def is_array(self):
        """
        :class:`py:bool`: A boolean indicating whether the qualifier is an
        array (`True`) or a scalar (`False`).

        Will not be `None`.

        This attribute is settable. For details, see the description of the
        same-named constructor parameter.
        """
        return self._is_array

    @is_array.setter
    def is_array(self, is_array):
        """Setter method; for a description see the getter method."""
        # pylint: disable=attribute-defined-outside-init
        self._is_array = is_array

    @property
    def array_size(self):
        """
        :term:`integer`: The size of the array qualifier, for fixed-size
        arrays.

        `None` means that the array qualifier has variable size, or that it is
        not an array.

        This attribute is settable. For details, see the description of the
        same-named constructor parameter.
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
        `NocaseDict`_: Scopes of the qualifier.

        Each dictionary item specifies one scope value, with:

        * key (:term:`string`): Scope name, in upper case.
        * value (:class:`py:bool`): Scope value, specifying whether the
          qualifier has that scope (i.e. can be applied to a CIM element of
          that kind).

        Valid scope names are "CLASS", "ASSOCIATION", "REFERENCE",
        "PROPERTY", "METHOD", "PARAMETER", "INDICATION", and "ANY".

        Will not be `None`.

        This attribute is settable. For details, see the description of the
        same-named constructor parameter.
        """
        return self._scopes

    @scopes.setter
    def scopes(self, scopes):
        """Setter method; for a description see the getter method."""
        # pylint: disable=attribute-defined-outside-init
        self._scopes = scopes

    @property
    def tosubclass(self):
        """
        :class:`py:bool`: If `True` specifies the ToSubclass flavor(the
        qualifier value propagates to subclasses); if `False` specifies the
        Restricted flavor(the qualifier value does not propagate to
        subclasses).

        `None` means that this information is not available.

        This attribute is settable. For details, see the description of the
        same-named constructor parameter.
        """
        return self._tosubclass

    @tosubclass.setter
    def tosubclass(self, tosubclass):
        """Setter method; for a description see the getter method."""
        # pylint: disable=attribute-defined-outside-init
        self._tosubclass = tosubclass

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
        same-named constructor parameter.
        """
        return self._toinstance

    @toinstance.setter
    def toinstance(self, toinstance):
        """Setter method; for a description see the getter method."""
        # pylint: disable=attribute-defined-outside-init
        self._toinstance = toinstance

    @property
    def overridable(self):
        """
        :class:`py:bool`: If `True`, specifies the  EnableOverride flavor (the
        qualifier value is overridable in subclasses); if `False` specifies the
        DisableOverride flavor (the qualifier value is not overridable in
        subclasses).

        `None` means that this information is not available.

        This attribute is settable. For details, see the description of the
        same-named constructor parameter.
        """
        return self._overridable

    @overridable.setter
    def overridable(self, overridable):
        """Setter method; for a description see the getter method."""
        # pylint: disable=attribute-defined-outside-init
        self._overridable = overridable

    @property
    def translatable(self):
        """
        :class:`py:bool`: If `True`, specifies the Translatable flavor. This
        flavor specifies that the qualifier is translatable. If `False`,
        specifies that the qualfier is not translatable. There is no flavor
        corresponding to `translatable=False`.

        `None` means that this information is not available.

        This attribute is settable. For details, see the description of the
        same-named constructor parameter.
        """
        return self._translatable

    @translatable.setter
    def translatable(self, translatable):
        """Setter method; for a description see the getter method."""
        # pylint: disable=attribute-defined-outside-init
        self._translatable = translatable

    def _cmp(self, other):
        """
        Comparator function for two :class:`~pywbem.CIMQualifierDeclaration`
        objects.

        The comparison is based on the `name`, `type`, `value`, `is_array`,
        `array_size`, `scopes`, `overridable`, `tosubclass`, `toinstance`,
        `translatable` instance attributes, in descending precedence.

        The `name` attribute is compared case-insensitively.
        """
        if self is other:
            return 0
        if not isinstance(other, CIMQualifierDeclaration):
            raise TypeError("other must be CIMQualifierDeclaration, "
                            "but is: %s" % type(other))
        return (cmpname(self.name, other.name) or
                cmpitem(self.type, other.type) or
                cmpitem(self.value, other.value) or
                cmpitem(self.is_array, other.is_array) or
                cmpitem(self.array_size, other.array_size) or
                cmpitem(self.scopes, other.scopes) or
                cmpitem(self.overridable, other.overridable) or
                cmpitem(self.tosubclass, other.tosubclass) or
                cmpitem(self.toinstance, other.toinstance) or
                cmpitem(self.translatable, other.translatable))

    def __str__(self):
        """
        Return a short string representation of the
        :class:`~pywbem.CIMQualifierDeclaration` object for human
        consumption.
        """
        return '%s(name=%r, value=%r, type=%r, ' \
               'is_array=%r, ...)' % \
               (self.__class__.__name__, self.name, self.value, self.type,
                self.is_array)

    def __repr__(self):
        """
        Return a string representation of the
        :class:`~pywbem.CIMQualifierDeclaration` object that is suitable for
        debugging.

        The scopes will be ordered by their names in the result.
        """
        return '%s(name=%r, value=%r, type=%r, ' \
               'is_array=%r, array_size=%r, ' \
               'scopes=%r, tosubclass=%r, overridable=%r, ' \
               'translatable=%r, toinstance=%r)' % \
               (self.__class__.__name__, self.name, self.value, self.type,
                self.is_array, self.array_size,
                self.scopes, self.tosubclass, self.overridable,
                self.translatable, self.toinstance)

    def copy(self):
        """
        Return a copy the :class:`~pywbem.CIMQualifierDeclaration` object.
        """
        return CIMQualifierDeclaration(self.name,
                                       self.type,
                                       value=self.value,
                                       is_array=self.is_array,
                                       array_size=self.array_size,
                                       scopes=self.scopes,
                                       overridable=self.overridable,
                                       tosubclass=self.tosubclass,
                                       toinstance=self.toinstance,
                                       translatable=self.translatable)

    def tocimxml(self):
        """
        Return the CIM-XML representation of the
        :class:`~pywbem.CIMQualifierDeclaration` object,
        as an instance of an appropriate subclass of :term:`Element`.

        The returned CIM-XML representation is consistent with :term:`DSP0201`.
        """
        return cim_xml.QUALIFIER_DECLARATION(self.name,
                                             self.type,
                                             self.value,
                                             is_array=self.is_array,
                                             array_size=self.array_size,
                                             qualifier_scopes=self.scopes,
                                             overridable=self.overridable,
                                             tosubclass=self.tosubclass,
                                             toinstance=self.toinstance,
                                             translatable=self.translatable)

    def tocimxmlstr(self, indent=None):
        """
        Return the CIM-XML representation of the
        :class:`~pywbem.CIMQualifierDeclaration` object, as a
        :term:`unicode string`.

        The returned CIM-XML representation is consistent with :term:`DSP0201`.

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
        return tocimxmlstr(self, indent)

    def tomof(self):
        """
        Return a :term:`unicode string` that is a MOF fragment with the
        qualifier type represented by the
        :class:`~pywbem.CIMQualifierDeclaration` object.
        """
        mof = 'Qualifier %s : %s' % (self.name, self.type)
        if self.is_array:
            mof += '['
            if self.array_size is not None:
                mof += str(self.array_size)
            mof += ']'
        if self.value is not None:
            if isinstance(self.value, list):
                mof += ' = {'
                mof += ', '.join([atomic_to_cim_xml(
                    tocimobj(self.type, x)) for x in self.value])
                mof += '}'
            else:
                mof += ' = %s' % atomic_to_cim_xml(
                    tocimobj(self.type, self.value))

        mof += ',\n%sScope(' % _indent_str(MOF_INDENT)
        mof += ', '.join([x.lower() for x, y in self.scopes.items() if y]) + ')'
        # toinstance flavor not included here because not part of DSP0004
        if not self.overridable and not self.tosubclass \
                and not self.translatable:
            mof += ';'
            return mof

        mof += ',\n%sFlavor(' % _indent_str(MOF_INDENT)
        mof += self.overridable and 'EnableOverride' or 'DisableOverride'
        mof += ', '
        mof += self.tosubclass and 'ToSubclass' or 'Restricted'
        if self.translatable:
            mof += ', Translatable'
        mof += ');'
        return mof


def tocimxml(value):
    """
    Return the CIM-XML representation of the CIM object or CIM data type,
    as an :term:`Element` object.

    The returned CIM-XML representation is consistent with :term:`DSP0201`.

    Parameters:

      value (:term:`CIM object` or :term:`CIM data type`):
        The value.

    Returns:

        The CIM-XML representation of the specified value,
        as an instance of an appropriate subclass of :term:`Element`.

        The returned CIM-XML representation is consistent with :term:`DSP0201`.
    """

    # Python cim_obj object

    if hasattr(value, 'tocimxml'):
        return value.tocimxml()

    # CIMType or builtin type

    if isinstance(value, (CIMType, int, six.text_type)):
        return cim_xml.VALUE(six.text_type(value))

    if isinstance(value, six.binary_type):
        return cim_xml.VALUE(_ensure_unicode(value))

    # TODO: Verify whether this is a bug to have this test after the one for
    #       int. Bool is a subtype of int, so bool probably matches in the test
    #       above.
    if isinstance(value, bool):
        return cim_xml.VALUE('TRUE') if value else cim_xml.VALUE('FALSE')

    # Iterable of values

    try:
        return cim_xml.VALUE_ARRAY([tocimxml(v) for v in value])
    except TypeError:
        raise ValueError("Can't convert %s (%s) to CIM XML" %
                         (value, builtin_type(value)))


def tocimxmlstr(value, indent=None):
    """
    Return the CIM-XML representation of the CIM object or CIM data type,
    as a :term:`unicode string`.

    The returned CIM-XML representation is consistent with :term:`DSP0201`.

    Parameters:

      value (:term:`CIM object` or :term:`CIM data type`):
        The CIM object or CIM data type to be converted to CIM-XML.

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
    xml_elem = tocimxml(value)
    if indent is None:
        xml_str = xml_elem.toxml()
    else:
        if isinstance(indent, six.string_types):
            pass  # use indent, as specified
        elif isinstance(indent, six.integer_types):
            indent = ' ' * indent
        else:
            raise TypeError("Type of indent must be string or integer, "
                            "but is: %s" % type(indent))
        xml_str = xml_elem.toprettyxml(indent=indent)
    # xml_str is a unicode string if required based upon its content.
    return _ensure_unicode(xml_str)


# pylint: disable=too-many-locals,too-many-return-statements,too-many-branches
def tocimobj(type_, value):
    """
    Return a CIM object representing the specified value and
    type.

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

    Exceptions:
        ValueError - Input cannot be converted to defined CIMValue type or
            invalid CIMDatatype name.
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
        elif isinstance(value, six.string_types):
            if value.lower() == 'true':
                return True
            elif value.lower() == 'false':
                return False
        raise ValueError('Invalid boolean value: "%s"' % value)

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
    def partition(str_arg, seq):
        """
        partition(str_arg, sep) -> (head, sep, tail)

        Searches for the separator sep in str_arg, and returns the,
        part before it the separator itself, and the part after it.
        If the separator is not found, returns str_arg and two empty
        strings.
        """
        try:
            return str_arg.partition(seq)
        except AttributeError:
            try:
                idx = str_arg.index(seq)
            except ValueError:
                return (str_arg, '', '')
            return (str_arg[:idx], seq, str_arg[idx + len(seq):])

    if type_ == 'reference':  # pylint: disable=too-many-nested-blocks
        # pylint: disable=too-many-return-statements,too-many-branches
        # TODO doesn't handle double-quoting, as in refs to refs.  Example:
        # r'ex_composedof.composer="ex_sampleClass.label1=9921,' +
        #  'label2=\"SampleLabel\"",component="ex_sampleClass.label1=0121,' +
        #  'label2=\"Component\""')

        if isinstance(value, (CIMInstanceName, CIMClassName)):
            return value
        elif isinstance(value, six.string_types):
            nm_space = host = None
            head, sep, tail = partition(value, '//')
            if sep and head.find('"') == -1:
                # we have a namespace type
                head, sep, tail = partition(tail, '/')
                host = head
            else:
                tail = head
            head, sep, tail = partition(tail, ':')
            if sep:
                nm_space = head
            else:
                tail = head
            head, sep, tail = partition(tail, '.')
            if not sep:
                return CIMClassName(head, host=host, namespace=nm_space)
            classname = head
            key_bindings = {}
            while tail:
                head, sep, tail = partition(tail, ',')
                if head.count('"') == 1:  # quoted string contains comma
                    tmp, sep, tail = partition(tail, '"')
                    head = '%s,%s' % (head, tmp)
                    tail = partition(tail, ',')[2]
                head = head.strip()
                key, sep, val = partition(head, '=')
                if sep:
                    cl_name, s, k = partition(key, '.')
                    if s:
                        if cl_name != classname:
                            raise ValueError('Invalid object path: "%s"' %
                                             value)
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
                                    raise ValueError('Invalid key binding: %s'
                                                     % val)

                    key_bindings[key] = val
            return CIMInstanceName(classname, host=host, namespace=nm_space,
                                   keybindings=key_bindings)
        else:
            raise ValueError('Invalid reference value: "%s"' % value)

    raise ValueError('Invalid CIM data type name: "%s"' % type_)


def byname(nlist):
    """
    Convert a list of named objects into a map indexed by name
    """
    return dict([(x.name, x) for x in nlist])
