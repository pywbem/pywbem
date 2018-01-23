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
via an argument of its constructor. For example, the :class:`~pywbem.CIMClass`
constructor has an argument named ``properties`` that allows specifying the
properties of the class.

Once the parent CIM object exists, each list of child elements can be modified
via a settable attribute. For example, the :class:`~pywbem.CIMClass` class has
a :attr:`~pywbem.CIMClass.properties` attribute for its list of properties.

For such attributes and constructor arguments that specify lists of child
objects, pywbem supports a number of different ways the child objects can be
specified.

Some of these ways preserve the order of child objects and some don't.

This section uses properties in classes as an example, but it applies to all
kinds of child objects in CIM objects.

The possible input objects for the ``properties`` constructor argument
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


.. _`NocaseDict`:

NocaseDict
----------

Class ``NocaseDict`` is a dictionary implementation with case-insensitive but
case-preserving keys, and with preservation of the order of its items.

It is used for lists of child objects of CIM objects (e.g. the list of CIM
properties in a CIM class, or the list of CIM parameters in a CIM method).

Users of pywbem will notice ``NocaseDict`` objects only as a result of pywbem
functions. Users cannot create ``NocaseDict`` objects.

Except for the case-insensitivity of its keys, it behaves like the built-in
:class:`~py:collections.OrderedDict`. Therefore, ``NocaseDict`` is not
described in detail in this documentation.

Deprecated: In v0.9.0, support for comparing two ``NocaseDict`` instances with
the ``>``, ``>``, ``<=``, ``>=`` operators has been deprecated.
"""  # noqa: E501
# pylint: enable=line-too-long
# Note: When used before module docstrings, Pylint scopes the disable statement
#       to the whole rest of the file, so we need an enable statement.

# This module is meant to be safe for 'import *'.

from __future__ import print_function, absolute_import

import sys
import inspect
import warnings
from copy import copy
import traceback
import re
try:
    from collections import OrderedDict
except ImportError:
    from ordereddict import OrderedDict
from xml.dom.minidom import Element

import six

from . import cim_xml
from .config import DEBUG_WARNING_ORIGIN
from .cim_types import _CIMComparisonMixin, type_from_name, cimtype, \
    atomic_to_cim_xml, CIMType, CIMDateTime, Uint8, Sint8, Uint16, Sint16, \
    Uint32, Sint32, Uint64, Sint64, Real32, Real64, number_types, CIMInt, \
    CIMFloat, _Longint

if six.PY2:
    # pylint: disable=wrong-import-order
    from __builtin__ import type as builtin_type
else:
    # pylint: disable=wrong-import-order
    from builtins import type as builtin_type  # pylint: disable=import-error

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
    r'(?://([\w.:@\[\]]*))?'  # authority
    r'(?:/|^/?)(\w+(?:/\w+)*)?'  # namespace name (leading slash optional)
    r':(\w*)$',  # class name
    flags=re.UNICODE)
WBEM_URI_INSTANCEPATH_REGEXP = re.compile(
    r'^(?:([\w\-]+):)?'  # namespace type (URI scheme)
    r'(?://([\w.:@\[\]]*))?'  # authority
    r'(?:/|^/?)(\w+(?:/\w+)*)?'  # namespace name (leading slash optional)
    r':(\w*)'  # class name
    r'\.(.+)$',  # key bindings
    flags=re.UNICODE)

# For parsing the key bindings using a regexp, we just distinguish the
# differently quoted forms. The exact types of the key values are determined
# lateron:
_KB_NOT_QUOTED = r'[^,"\'\\]+'
_KB_SINGLE_QUOTED = r"'(?:[^'\\]|\\.)*'"
_KB_DOUBLE_QUOTED = r'"(?:[^"\\]|\\.)*"'
_KB_VAL = r'(?:%s|%s|%s)' % \
    (_KB_NOT_QUOTED, _KB_SINGLE_QUOTED, _KB_DOUBLE_QUOTED)

# To get all repetitions, capture a repeated group instead of repeating a
# capturing group: https://www.regular-expressions.info/captureall.html
WBEM_URI_KEYBINDINGS_REGEXP = re.compile(
    r'^(\w+=%s)((?:,\w+=%s)*)$' % (_KB_VAL, _KB_VAL),
    flags=(re.UNICODE | re.IGNORECASE))

WBEM_URI_KB_FINDALL_REGEXP = re.compile(
    r',\w+=%s' % _KB_VAL,
    flags=(re.UNICODE | re.IGNORECASE))

# Pattern for DSP0004 decimalValue
DECIMAL_VALUE = re.compile(
    r'^[+\-]?(?:0|[1-9][0-9]*)$',
    flags=(re.UNICODE))

# Pattern for DSP0004 realValue (extended by INF, -INF, NAN)
REAL_VALUE = re.compile(
    r'^(?:[+\-]?[0-9]*\.[0-9]+(?:E[+\-]?[0-9]+)?|INF|-INF|NAN)$',
    flags=(re.UNICODE | re.IGNORECASE))

# Valid namespace types (URI schemes) for WBEM URI parsing
WBEM_URI_NAMESPACE_TYPES = [
    'http', 'https',
    'cimxml-wbem', 'cimxml-wbems',
]


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
        Initialize the new dictionary from input arguments.
        This happens in two steps:

        In the first step, an initial set of items is added to the new
        dictionary, from the positional argument(s):

          * If no positional argument is provided, or if one argument with the
            value `None` is provided, the new dictionary will be empty in this
            step.

          * If one positional argument of tuple or list type is provided, the
            items in that iterable must be tuples of key and value. These
            key/value pairs will be added to the new dictionary without copying
            them, preserving their order in the list.

          * If one positional argument of dictionary kind (dict, OrderedDict,
            NocaseDict) is provided, its key/value pairs are added to the new
            dictionary without copying them, preserving their order in case of
            OrderedDict or NocaseDict. Because dict types inherently do not
            preserve order, the resulting order of items in the new dictionary
            will be arbitrary in that case.

          * Otherwise, `TypeError` is raised.

        In the second step, the new dictionary is updated from any provided
        keyword arguments, without copying them, for each keyword argument
        using its name as a key and its value as a value. Note that Python
        before version 3.6 uses standard dict objects for passing keyword
        arguments, so the resulting order of items in the new dictionary will
        be arbitrary. From Python 3.6 on, keyword arguments will be passed
        in the order specified, so they will be added to the new dictionary
        in the order specified, from left to right.

        Summary w.r.t. preservation of item order: In order to preserve the
        order of items used to initialize a new NocaseDict object, only the
        following approaches can be used across all Python versions supported
        by pywbem:

        * Passing a list or a tuple of key/value pairs as a single positional
          argument.
        * Passing an OrderedDict or NocaseDict object as a single positional
          argument.

        A UserWarning will be issued if the provided constructor arguments will
        cause the order of provided items not to be preserved when adding them
        to the new dictionary.
        """

        # The internal dictionary, with lower case keys. An item in this dict
        # is the tuple (original key, value).
        self._data = OrderedDict()

        # Step 1: Initialize from at most one positional argument
        if len(args) == 1:
            arg = args[0]
            if isinstance(arg, (list, tuple)):
                # Initialize from iterable of: tuple(key,value), or object
                try:
                    # This is used for iterables:
                    iterator = arg.items()
                except AttributeError:
                    # This is used for dictionaries:
                    iterator = arg
                for item in iterator:
                    try:
                        key = item.name
                        value = item
                    except AttributeError:
                        key, value = item
                    self[key] = value
            elif isinstance(arg, (OrderedDict, NocaseDict)):
                # Initialize from OrderedDict/NocaseDict object
                self.update(arg)
            elif isinstance(arg, dict):
                # Initialize from dict object
                if len(arg) > 1:
                    warnings.warn("Initializing a pywbem.NocaseDict object "
                                  "from %s will not preserve order of items" %
                                  type(arg), UserWarning,
                                  stacklevel=_stacklevel_above_module(__name__))
                self.update(arg)
            elif arg is None:
                # Leave empty
                pass
            else:
                raise TypeError(
                    "Invalid type for NocaseDict initialization: %s (%s)" %
                    (arg.__class__.__name__, type(arg)))
        elif len(args) > 1:
            raise TypeError(
                "Too many positional arguments for NocaseDict initialization: "
                "%s (1 allowed)" % len(args))

        # Step 2: Add any keyword arguments
        if len(kwargs) > 1 and sys.version_info[0:2] <= (3, 6):
            warnings.warn("Initializing a pywbem.NocaseDict object from "
                          "keyword arguments before Python 3.6 will not "
                          "preserve order of items",
                          UserWarning,
                          stacklevel=_stacklevel_above_module(__name__))
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
        case, preserving the original order of items.
        """
        for item in six.iteritems(self._data):
            yield item[1][0]

    def itervalues(self):
        """
        Return an iterator through the dictionary values, preserving the
        original order of items.
        """
        for item in six.iteritems(self._data):
            yield item[1][1]

    def iteritems(self):
        """
        Return an iterator through the dictionary items, where each item is a
        tuple of its original key and its value, preserving the original order
        of items.
        """
        for item in six.iteritems(self._data):
            yield item[1]

    def __iter__(self):
        """
        *New in pywbem 0.8.*

        Invoked when iterating through the dictionary using `for key in d`.

        The returned keys have their original case, and preserve the original
        order of items.
        """
        return self.iterkeys()

    # Other stuff

    def __repr__(self):
        """
        Return a string representation of the
        `NocaseDict`_ object that is suitable for
        debugging.

        The order of dictionary items in the result is the preserved order of
        adding or deleting items.
        """
        items = ', '.join(['(%r, %r)' % (key, value)
                           for key, value in self.iteritems()])
        return 'NocaseDict([%s])' % items

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

    def __ordering_deprecated(self):
        """Function to issue deprecation warning for ordered comparisons
        """
        msg = "Ordering comparisons involving %s objects are deprecated." % \
            self.__class__.__name__
        if DEBUG_WARNING_ORIGIN:
            msg += "\nTraceback:\n" + ''.join(traceback.format_stack())
        warnings.warn(msg, DeprecationWarning,
                      stacklevel=_stacklevel_above_module(__name__))

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

    def __hash__(self):
        """
        Hash this NocaseDict object, case-insensitively w.r.t. to its keys.

        Background: In order to compare sets of objects, the objects must be
        hashable (See https://docs.python.org/2/glossary.html#term-hashable).
        The condition from that definition that is not satisfied by the
        default hash function of objects (which is based on id()), is that
        hashable objects which compare equal must have the same hash value.
        This method ensures that that condition is satisfied.
        """
        fs = frozenset([(key, self._data[key][1]) for key in self._data])
        return hash(fs)


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
    in pywbem v0.9.0.

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
    # TODO 01/18 AM Could compare hash(dict) for better perf
    #      That requires more unicode cleanliness (test_clienti.py fails)
    if dict1 == dict2:
        return 0
    return 1


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


def _qualifiers_tomof(qualifiers, indent, maxline=MAX_MOF_LINE):
    """
    Return a MOF fragment with the qualifier values, including the surrounding
    square brackets. The qualifiers are ordered by their name.

    Return empty string if no qualifiers.

    Normally multiline output and may fold qualifiers into multiple lines.

    The order of qualifiers is preserved.

    Parameters:

      qualifiers (NocaseDict): Qualifiers to format.

      indent (:term:`integer`): Number of spaces to indent each line of
        the returned string, counted to the opening bracket in the first line.

    Returns:

      :term:`unicode string`: MOF fragment.
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
        * :term:`unicode string`: MOF fragment.
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
            "Endless loop in mofstr() with state: " \
            "mof_str=%r, value=%r, avl_len=%s, end_space=%s, split_pos=%s" % \
            (u''.join(mof), value, avl_len, end_space, split_pos)

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
        * :term:`unicode string`: MOF fragment.
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

    raise ValueError("Cannot fit value %r onto new MOF line, missing %s "
                     "characters" % (value, len(value) - avl_len))


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
    Return a MOF fragment representing a scalar CIM-typed value.

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
        * :term:`unicode string`: MOF fragment.
        * new line_pos
    """  # noqa: E501

    if value is None:
        return mofval(u'NULL', indent, maxline, line_pos, end_space)
    elif type == 'string':
        if isinstance(value, six.string_types):
            return mofstr(value, indent, maxline, line_pos, end_space,
                          avoid_splits)
        elif isinstance(value, (CIMInstance, CIMClass)):
            # embedded instance or class
            return mofstr(value.tomof(), indent, maxline, line_pos, end_space,
                          avoid_splits)
        else:
            raise TypeError("Scalar value of CIM type %r has invalid Python "
                            "type %s for conversion to a MOF string" %
                            (type, builtin_type(value)))
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
            "Scalar value of CIM type %r has invalid Python type %s for " \
            "conversion to a MOF string" % (type, builtin_type(value))
        val = repr(value)
        return mofval(val, indent, maxline, line_pos, end_space)


def _value_tomof(
        value, type, indent=0, maxline=MAX_MOF_LINE, line_pos=0, end_space=0,
        avoid_splits=False):
    # pylint: disable=redefined-builtin
    """
    Return a MOF fragment representing a CIM-typed value (scalar or array).

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
        * :term:`unicode string`: MOF fragment.
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


def _stacklevel_above_module(mod_name):
    """
    Return the stack level (with 1 = caller of this function) of the first
    caller that is not defined in the specified module (e.g. "pywbem.cim_obj").

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


def _cim_keybinding(key, value):
    """
    Return a keybinding value, from dict item input (key+value).

    The returned value will be a CIM-typed value, except if it was provided as
    Python number type (in which case it will remain that type).

    Invalid types or values cause TypeError or ValueError to be raised.
    """

    if key is None:
        raise ValueError("Invalid keybinding name: None")

    if isinstance(value, CIMProperty):
        if value.name.lower() != key.lower():
            raise ValueError("Invalid keybinding name: CIMProperty.name must "
                             "be dictionary key %s, but is %s" %
                             (key, value.name))
        return copy(value.value)

    if value is None:
        return None

    if isinstance(value, (six.text_type, six.binary_type)):
        return _ensure_unicode(value)

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
        raise TypeError("Value of keybinding %s cannot be an "
                        "embedded object: %s" % (key, type(value)))

    if isinstance(value, list):
        raise TypeError("Value of keybinding %s cannot be a list" % key)

    raise TypeError("Value of keybinding %s has an invalid type: %s" %
                    (key, type(value)))


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
            raise ValueError("CIMProperty.name must be dictionary key "
                             "%s, but is %s" % (key, value.name))
        prop = value
    else:
        # We no longer check for the common error to set CIM numeric values as
        # Python number types, because that is done in the CIMProperty
        # constructor.
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

    if not isinstance(value, CIMProperty):
        raise TypeError("Property must be a CIMProperty object, but is: %s" %
                        type(value))

    if value.name.lower() != key.lower():
        raise ValueError("CIMProperty.name must be dictionary key %s, but is "
                         "%s" % (key, value.name))

    return value


def _cim_method(key, value):
    """
    Return a CIMMethod object, from dict item input (key+value), after
    performing some checks.

    The input value must be a CIMMethod object, which is returned.
    """

    if key is None:
        raise ValueError("Method name must not be None")

    if not isinstance(value, CIMMethod):
        raise TypeError("Method must be a CIMMethod object, but is: %s" %
                        type(value))

    if value.name.lower() != key.lower():
        raise ValueError("CIMMethod.name must be dictionary key %s, but is "
                         "%s" % (key, value.name))

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
            raise ValueError("CIMQualifier.name must be dictionary key "
                             "%s, but is %s" % (key, value.name))
        qual = value
    else:
        # We no longer check for the common error to set CIM numeric values as
        # Python number types, because that is done in the CIMQualifier
        # constructor.
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
            same-named attribute in the ``CIMInstanceName`` object will also be
            `None`.

            The lexical case of the string is preserved. Object comparison and
            hash value calculation are performed case-insensitively.

          namespace (:term:`string`):
            Name of the CIM namespace containing the referenced instance.

            `None` means that the namespace is unspecified, and the
            same-named attribute in the ``CIMInstanceName`` object will also be
            `None`.

            The lexical case of the string is preserved. Object comparison and
            hash value calculation are performed case-insensitively.

        Raises:

          ValueError: An error in the provided argument values.
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
        :term:`unicode string`: Name of the creation class of the referenced
        instance.

        Will not be `None`.

        This attribute is settable. For details, see the description of the
        same-named constructor parameter.
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
        `NocaseDict`_: Keybindings of the instance path (that is, the key
        property values of the referenced instance).

        Will not be `None`.

        Each dictionary item specifies one keybinding, with:

        * key (:term:`unicode string`): Keybinding name. Its lexical case was
          preserved.

        * value (:term:`CIM data type` or :term:`number`): Keybinding value.

        The order of keybindings in the instance path is preserved.

        This attribute is settable; setting it will cause the current
        keybindings to be replaced with the new keybindings. For details, see
        the description of the same-named constructor parameter.

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
        one by using the entire ``CIMInstanceName`` object like a dictionary.
        Again, the provided input value must be specified as a
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
                    raise TypeError("Input object for keybindings has "
                                    "invalid item in iterable: %r" % item)
                self.keybindings[key] = _cim_keybinding(key, value)

    @property
    def namespace(self):
        """
        :term:`unicode string`: Name of the CIM namespace containing the
        referenced instance.

        `None` means that the namespace is unspecified.

        This attribute is settable. For details, see the description of the
        same-named constructor parameter.
        """
        return self._namespace

    @namespace.setter
    def namespace(self, namespace):
        """Setter method; for a description see the getter method."""
        # pylint: disable=attribute-defined-outside-init
        self._namespace = _ensure_unicode(namespace)

    @property
    def host(self):
        """
        :term:`unicode string`: Host and optionally port of the WBEM server
        containing the CIM namespace of the referenced instance.

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
        if not isinstance(other, CIMInstanceName):
            raise TypeError("other must be CIMInstanceName, but is: %s" %
                            type(other))
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
        Return a WBEM URI string of the CIM instance path represented by the
        :class:`~pywbem.CIMInstanceName` object.

        The returned WBEM URI string is in the historical format returned by
        :meth:`~pywbem.CIMInstanceName.to_wbem_uri`.

        For new code, it is recommended that the standard format is used; it
        is returned by :meth:`~pywbem.CIMInstanceName.to_wbem_uri` as the
        default format.

        Examples (for the historical format):

        * With authority and namespace::

            //acme.com/cimv2/test:CIM_RegisteredProfile.InstanceID="acme.1"

        * Without authority but with namespace::

            cimv2/test:CIM_RegisteredProfile.InstanceID="acme.1"

        * Without authority and without namespace::

            CIM_RegisteredProfile.InstanceID="acme.1"
        """
        return self.to_wbem_uri(format='historical')

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
        *New in pywbem 0.8.*

        Return the value of the keybinding with name `key`, or a default
        value if a keybinding with that name does not exist.
        """
        return self.keybindings.get(key, default)

    def keys(self):
        """
        Return a copied list of the keybinding names (in their original
        lexical case).

        The order of keybindings is preserved.
        """
        return self.keybindings.keys()

    def values(self):
        """
        Return a copied list of the keybinding values.

        The order of keybindings is preserved.
        """
        return self.keybindings.values()

    def items(self):
        """
        Return a copied list of the keybindings, where each item is a tuple
        of its keybinding name (in the original lexical case) and its value.

        The order of keybindings is preserved.
        """
        return self.keybindings.items()

    def iterkeys(self):
        """
        Iterate through the keybinding names (in their original lexical case).

        The order of keybindings is preserved.
        """
        return self.keybindings.iterkeys()

    def itervalues(self):
        """
        Iterate through the keybinding values.

        The order of keybindings is preserved.
        """
        return self.keybindings.itervalues()

    def iteritems(self):
        """
        Iterate through the keybindings, where each item is a tuple of the
        keybinding name (in the original lexical case) and the keybinding
        value.

        The order of keybindings is preserved.
        """
        return self.keybindings.iteritems()

    # pylint: disable=too-many-branches
    def tocimxml(self):
        """
        Return the CIM-XML representation of the
        :class:`~pywbem.CIMInstanceName` object,
        as an instance of an appropriate subclass of :term:`Element`.

        The returned CIM-XML representation is consistent with :term:`DSP0201`.

        The order of keybindings is preserved.
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

            if isinstance(value, bool):
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
            elif isinstance(value, six.string_types):
                type_ = 'string'
                value = _ensure_unicode(value)
            else:
                # Double check the type of the keybindings, because they can be
                # set individually.
                raise TypeError('Keybinding %s has invalid type: %s' %
                                (key, builtin_type(value)))

            kbs.append(cim_xml.KEYBINDING(
                key, cim_xml.KEYVALUE(value, type_)))

        instancename_xml = cim_xml.INSTANCENAME(self.classname, kbs)

        if self.namespace is not None:

            localnsp = cim_xml.LOCALNAMESPACEPATH(
                [cim_xml.NAMESPACE(ns)
                 for ns in self.namespace.split('/')])

            if self.host is not None:

                # Instancename + namespace + host = INSTANCEPATH

                return cim_xml.INSTANCEPATH(
                    cim_xml.NAMESPACEPATH(cim_xml.HOST(self.host), localnsp),
                    instancename_xml)

            # Instancename + namespace = LOCALINSTANCEPATH

            return cim_xml.LOCALINSTANCEPATH(localnsp, instancename_xml)

        # Just Instancename = INSTANCENAME

        return instancename_xml

    def tocimxmlstr(self, indent=None):
        """
        *New in pywbem 0.9.*

        Return the CIM-XML representation of the
        :class:`~pywbem.CIMInstanceName` object, as a :term:`unicode string`.

        The returned CIM-XML representation is consistent with :term:`DSP0201`.

        The order of keybindings is preserved.

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
                raise ValueError("WBEM URI has a char16 keybinding with an "
                                 "incorrect length: %s=%r" % (key, val))
            return cimval

        if val.lower() in ('true', 'false'):
            # The key value must be CIM type:
            # * boolean (see booleanValue in DSP00004)
            cimval = val.lower() == 'true'
            return cimval

        if DECIMAL_VALUE.match(val):
            # The key value must be one of the integer CIM types:
            # * uintNN, sintNN (see decimalValue in DSP00004)

            # For integer keybindings in an untyped WBEM URI, it is not
            # possible to detect the exact CIM data type. Therefore, pywbem
            # stores the value as a Python int type (or long in Python 2,
            # if needed).

            # Note that DSP0207 only allows only US-ASCII 0-9 for decimal
            # numbers. The int() function supports all decimal Unicode
            # digits (e.g. US-ASCII 0-9, ARABIC-INDIC digits, superscripts,
            # or subscripts) and raises ValueError for non-decimal digits
            # (e.g. Kharoshthi digits).

            # Therefore, the decimalValue format has been checked explicitly,
            # and an error in the int() function is not expected.

            cimval = int(val)  # returns long if needed
            return cimval

        if REAL_VALUE.match(val):
            # The key value must be one of the real CIM types:
            # * realNN (see realValue in DSP00004)

            # For real/float keybindings in an untyped WBEM URI, it is not
            # possible to detect the exact CIM data type. Therefore, pywbem
            # stores the value as a Python float type.

            # The float() function supports a superset of input formats
            # compared to the realValue definition in DSP0004 (for example,
            # "1." is allowed for float() but not for realValue), plus it
            # has the same support for decimal Unicode digits as int().
            # Therefore, the US-ASCII 0-9 digits have been checked explicitly,
            # and an error in the int() function is not expected.

            # Therefore, the realValue format has been checked explicitly,
            # and an error in the float() function is not expected.

            # Note that the special values 'INF', '-INF', and 'NAN' are
            # also covered by Python float().

            cimval = float(val)
            return cimval

        # At this point, all CIM types have been processed, except:
        # * datetime, without quotes (see datetimeValue in DSP0207)

        # DSP0207 requires double quotes around datetime strings, but because
        # earlier versions of pywbem supported them without double quotes,
        # pywbem continues to support that, but issues a warning.

        try:
            cimval = CIMDateTime(val)
        except ValueError:
            raise ValueError("WBEM URI has invalid value format in a "
                             "keybinding: %s=%r" % (key, val))

        warnings.warn("Tolerating datetime value without surrounding double "
                      "quotes in WBEM URI keybinding: %s=%r" % (key, val),
                      UserWarning)
        return cimval

    @staticmethod
    def from_wbem_uri(wbem_uri):
        # pylint: disable=line-too-long
        """
        *New in pywbem 0.12.*

        Return a new :class:`~pywbem.CIMInstanceName` object from the specified
        WBEM URI string.

        The WBEM URI string must be a CIM instance path in untyped WBEM URI
        format, as defined in :term:`DSP0207`, with these extensions:

        * DSP0207 restricts the namespace types (URI schemes) to be one of
          ``http``, ``https``, ``cimxml-wbem``, or ``cimxml-wbems``. Pywbem
          tolerates any namespace type, but issues a :exc:`py:UserWarning` if
          it is not one of the namespace types defined in DSP0207.

        * DSP0207 requires a slash before the namespace name. For local WBEM
          URIs (no namespace type, no authority), that slash is the first
          character of the WBEM URI. For historical reasons, pywbem tolerates a
          missing leading slash for local WBEM URIs. Note that pywbem requires
          the slash (consistent with DSP0207) when the WBEM URI is not local.

        * DSP0207 requires datetime values in keybindings to be surrounded by
          double quotes. For historical reasons, pywbem tolerates datetime
          values that are not surrounded by double quotes, but issues a
          :exc:`py:UserWarning`.

        * DSP0207 does not allow the special float values INF, -INF, and NaN
          in WBEM URIs (according to realValue in DSP0004). However, the
          CIM-XML protocol supports representation of these special values,
          so to be on the safe side, pywbem supports these special values as
          keybindings in WBEM URIs.

        Keybindings that are references are supported, recursively.

        CIM instance paths in the typed WBEM URI format defined in DSP0207
        are not supported.

        The untyped WBEM URI format defined in DSP0207 has the following
        limitations when interpreting a WBEM URI string:

        * It cannot distinguish string-typed keys with a value that is a
          datetime value from datetime-typed keys with such a value. Pywbem
          treats such values as datetime-typed keys.

        * It cannot distinguish string-typed keys with a value that is a
          WBEM URI from reference-typed keys with such a value. Pywbem
          treats such values as reference-typed keys.

        Examples::

            https://jdd:test@acme.com:5989/cimv2/test:CIM_RegisteredProfile.InstanceID="acme.1"
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
            raise ValueError("Invalid format for an instance path in "
                             "WBEM URI: %r" % wbem_uri)

        ns_type = m.group(1) or None
        if ns_type and ns_type.lower() not in WBEM_URI_NAMESPACE_TYPES:
            warnings.warn("Tolerating unknown namespace type in WBEM URI: %r" %
                          wbem_uri, UserWarning)

        host = m.group(2) or None
        namespace = m.group(3) or None
        classname = m.group(4) or None
        keybindings_str = m.group(5) or None

        m = WBEM_URI_KEYBINDINGS_REGEXP.match(keybindings_str)
        if m is None:
            raise ValueError("WBEM URI has an invalid format for its "
                             "keybindings: %r" % keybindings_str)

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
            assert sep, "kb_assign=%r" % kb_assign

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
        Return the untyped WBEM URI of the CIM instance path represented
        by the :class:`~pywbem.CIMInstanceName` object.

        The returned WBEM URI contains its components as follows:

        * it does not contain a namespace type (URI scheme).
        * it contains an authority component according to the
          :attr:`~pywbem.CIMInstanceName.host` attribute, if that is not
          `None`. Othwerise, it does not contain the authority component.
        * it contains a namespace component according to the
          :attr:`~pywbem.CIMInstanceName.namespace` attribute, if that is not
          `None`. Othwerise, it does not contain the namespace component.
        * it contains a class name component according to the
          :attr:`~pywbem.CIMInstanceName.classname` attribute.
        * it contains keybindings according to the
          :attr:`~pywbem.CIMInstanceName.keybindings` attribute, with the
          order of keybindings preserved, and the lexical case of keybinding
          names preserved.

        :term:`DSP0004` defines instance paths without a concept of order in
        their keybindings, and that keybinding names in instance paths match
        case-insensitively. Because the WBEM URI string returned by this method
        preserves the order of keybindings (relative to how the keybindings
        were first added to this object) and because the lexical case of the
        keybinding names is also preserved, equality of WBEM URIs should *not*
        be determined by comparing the returned WBEM URI strings. Instead,
        compare :class:`~pywbem.CIMInstanceName` objects using the ``==``
        operator, which performs the comparison at the logical level required
        by DSP0004. If you have WBEM URI strings without the corresponding
        :class:`~pywbem.CIMInstanceName` object, such an object can be created
        by using the static method
        :meth:`~pywbem.CIMInstanceName.from_wbem_uri`.

        Parameters:

          format (:term:`string`): Format for the generated WBEM URI string,
            using one of the following values:

            * ``"standard"`` - Standard format that is conformant to untyped
              WBEM URIs for instance paths defined in :term:`DSP0207`.

            * ``"cimobject"`` - Format for the `CIMObject` header field in
              CIM-XML messages for representing instance paths (used
              internally, see :term:`DSP0200`).

            * ``"historical"`` - Historical format for WBEM URIs (used by
              :meth:`~pywbem.CIMInstanceName.__str__`; should not be used by
              new code). The historical format has the following differences to
              the standard format:

              - If the authority component is not present, the slash after the
                authority is also omitted. In the standard format, that slash
                is always present.

              - If the namespace component is not present, the colon after the
                namespace is also omitted. In the standard format, that colon
                is always present.

        Examples for the standard format:

        * With authority and namespace::

            //acme.com/cimv2/test:CIM_RegisteredProfile.InstanceID="acme.1"

        * Without authority but with namespace::

            /cimv2/test:CIM_RegisteredProfile.InstanceID="acme.1"

        * Without authority and without namespace::

            /:CIM_RegisteredProfile.InstanceID="acme.1"

        Returns:

          :term:`unicode string`: Untyped WBEM URI of the CIM instance path,
          in the specified format.

        Raises:

          TypeError: Invalid type in keybindings
        """

        ret = []

        if self.host is not None:
            ret.append('//')
            ret.append(self.host)

        if self.host is not None or format == 'standard':
            ret.append('/')

        if self.namespace is not None:
            ret.append(self.namespace)

        if self.namespace is not None or format in ('standard', 'cimobject'):
            ret.append(':')

        ret.append(self.classname)

        ret.append('.')
        for key, value in self.keybindings.iteritems():

            ret.append(key)
            ret.append('=')

            if isinstance(value, bool):
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
                ret.append(value.to_wbem_uri().
                           replace('\\', '\\\\').
                           replace('"', '\\"'))
                ret.append('"')
            elif isinstance(value, CIMDateTime):
                # datetime
                ret.append('"')
                ret.append(str(value))
                ret.append('"')
            elif isinstance(value, six.string_types):
                # string, char16
                ret.append('"')
                ret.append(value.
                           replace('\\', '\\\\').
                           replace('"', '\\"'))
                ret.append('"')
            else:
                raise TypeError("Invalid type %s in keybinding value: %s=%r" %
                                (type(value), key, value))
            ret.append(',')

        del ret[-1]

        return _ensure_unicode(''.join(ret))


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

          qualifiers (:term:`qualifiers input object`):
            The qualifiers for the instance.

            Note that :term:`DSP0200` has deprecated the presence of qualifiers
            on CIM instances.

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

            **Deprecated:** This parameter has been deprecated in pywbem
            0.12.0. Set only the desired properties on the object, instead of
            working with this property filter.

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
        :term:`unicode string`: Name of the creation class of the instance.

        Will not be `None`.

        This attribute is settable. For details, see the description of the
        same-named constructor parameter.
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
        `NocaseDict`_: Properties of the CIM instance.

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
        constructor parameter. Note that the property value may be specified as
        a :term:`CIM data type` or as a :class:`~pywbem.CIMProperty` object.

        The CIM property values can also be accessed and manipulated one by one
        because the attribute value is a modifiable dictionary. In that case,
        the provided input value must be a :class:`~pywbem.CIMProperty`
        object::

            inst = CIMInstance(...)
            p1 = CIMProperty('p1', ...)  # must be CIMProperty

            inst.properties['p1'] = p1  # Set "p1" to p1 (add if needed)
            p1 = inst.properties['p1']  # Access "p1"
            del inst.properties['p1']  # Delete "p1" from the instance

        In addition, the CIM properties can be accessed and manipulated one by
        one by using the entire :class:`~pywbem.CIMInstance` object like a
        dictionary. In that case, the provided input value may be specified as
        a :term:`CIM data type` or as a :class:`~pywbem.CIMProperty` object::

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
                    raise TypeError("Input object for properties has "
                                    "invalid item in iterable: %r" % item)
                self.__setitem__(key, value)

    @property
    def qualifiers(self):
        """
        `NocaseDict`_: Qualifiers of the CIM instance.

        Will not be `None`.

        Each dictionary item specifies one qualifier value, with:

        * key (:term:`unicode string`): Qualifier name. Its lexical case was
          preserved.

        * value (:class:`~pywbem.CIMQualifier`): Qualifier value.

        The order of qualifiers in the CIM instance is preserved.

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
                    raise TypeError("Input object for qualifiers has "
                                    "invalid item in iterable: %r" % item)
                self.qualifiers[key] = _cim_qualifier(key, value)

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
        self._path = copy(path)  # It is modified by the properties setter

        # We perform this check after the initialization to avoid errors
        # in test tools that show the object with repr().
        assert isinstance(path, CIMInstanceName) or path is None

    @property
    def property_list(self):
        """
        :term:`py:list` of :term:`unicode string`: List of property names for
        use as a filter by some operations on the instance. The property names
        are in lower case.

        `None` means that the properties are not filtered.

        This attribute is settable. For details, see the description of the
        same-named constructor parameter.

        **Deprecated:** This attribute has been deprecated in pywbem v0.12.0.
        Set only the desired properties on the object, instead of working with
        this property filter.
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
        if not isinstance(other, CIMInstance):
            raise TypeError("other must be CIMInstance, but is: %s" %
                            type(other))
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

        # The property_list attribute has been deprecated in pywbem 0.12.0.
        # It is used to ignore the setting of properties under certain
        # conditions. Note that the purpose of these conditions is unclear,
        # given the code below (whose logic is unchanged since at least as far
        # back as pywbem 0.7.0): For instances that do not have a path set,
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
        Return a boolean indicating whether the instance has a property with
        name `key`.
        """
        return key in self.properties

    def get(self, key, default=None):
        """
        *New in pywbem 0.8.*

        Return the value of the property with name `key`, or a default value if
        a property with that name does not exist.
        """
        prop = self.properties.get(key, None)
        return default if prop is None else prop.value

    def keys(self):
        """
        Return a copied list of the property names (in their original lexical
        case).

        The order of properties is preserved.
        """
        return self.properties.keys()

    def values(self):
        """
        Return a copied list of the property values.

        The order of properties is preserved.
        """
        return [v.value for v in self.properties.values()]

    def items(self):
        """
        Return a copied list of the properties, where each item is a tuple
        of the property name (in the original lexical case) and the property
        value.

        The order of properties is preserved.
        """
        return [(key, v.value) for key, v in self.properties.items()]

    def iterkeys(self):
        """
        Iterate through the property names (in their original lexical
        case).

        The order of properties is preserved.
        """
        return self.properties.iterkeys()

    def itervalues(self):
        """
        Iterate through the property values.

        The order of properties is preserved.
        """
        for _, val in self.properties.iteritems():
            yield val.value

    def iteritems(self):
        """
        Iterate through the property names (in their original lexical case).

        The order of properties is preserved.
        """
        for key, val in self.properties.iteritems():
            yield (key, val.value)

    def tocimxml(self):
        """
        Return the CIM-XML representation of the
        :class:`~pywbem.CIMInstance` object,
        as an instance of an appropriate subclass of :term:`Element`.

        The returned CIM-XML representation is consistent with :term:`DSP0201`.

        The order of properties and qualifiers is preserved.
        """

        # The items in the self.properties dictionary are required to be
        # CIMProperty objects and that is ensured when initializing a
        # CIMInstance object and when setting the entire self.properties
        # attribute. However, even though the items in the dictionary are
        # required to be CIMProperty objects, the user technically can set
        # them to anything.
        # Before pywbem v0.12.0, the dictionary items were converted to
        # CIMProperty objects. This was only done for properties of
        # CIMinstance, but not for any other CIM object attribute.
        # In v0.12.0, this conversion was removed because it worked only for
        # bool and string types anyway. Because that conversion had been
        # implemented, we still check that the items are CIMProperty objects.
        for key, value in self.properties.items():
            if not isinstance(value, CIMProperty):
                raise TypeError("Property %s has invalid type: %s "
                                "(must be CIMProperty)" %
                                (key, builtin_type(value)))

        instance_xml = cim_xml.INSTANCE(
            self.classname,
            properties=[p.tocimxml() for p in self.properties.values()],
            qualifiers=[q.tocimxml() for q in self.qualifiers.values()])

        if self.path is None:
            return instance_xml

        return cim_xml.VALUE_NAMEDINSTANCE(
            self.path.tocimxml(),
            instance_xml)

    def tocimxmlstr(self, indent=None):
        """
        *New in pywbem 0.9.*

        Return the CIM-XML representation of the
        :class:`~pywbem.CIMInstance` object, as a :term:`unicode string`.

        The returned CIM-XML representation is consistent with :term:`DSP0201`.

        The order of properties and qualifiers is preserved.

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

    def tomof(self, indent=0, maxline=MAX_MOF_LINE):
        """
        Return a MOF string with the instance specification represented by
        the :class:`~pywbem.CIMInstance` object.

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
            pywbem 0.12.0. A value other than 0 causes a deprecation warning to
            be issued. Othwerise, the parameter is ignored and the returned MOF
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
            same-named attribute in the ``CIMClassName`` object will also be
            `None`.

            The lexical case of the string is preserved. Object comparison and
            hash value calculation are performed case-insensitively.

          namespace (:term:`string`):
            Name of the CIM namespace containing the referenced class.

            `None` means that the namespace is unspecified, and the
            same-named attribute in the ``CIMClassName`` object will also be
            `None`.

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
        :term:`unicode string`: Class name of the referenced class.

        Will not be `None`.

        This attribute is settable. For details, see the description of the
        same-named constructor parameter.
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
        self._namespace = _ensure_unicode(namespace)

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
        self._host = _ensure_unicode(host)

    def copy(self):
        """
        Return a copy the :class:`~pywbem.CIMClassName` object.
        """
        return CIMClassName(self.classname, host=self.host,
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
        if not isinstance(other, CIMClassName):
            raise TypeError("other must be CIMClassName, but is: %s" %
                            type(other))
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
        Return a WBEM URI string of the CIM class path represented by the
        :class:`~pywbem.CIMClassName` object.

        The returned WBEM URI string is in the historical format returned by
        :meth:`~pywbem.CIMClassName.to_wbem_uri`.

        For new code, it is recommended that the standard format is used; it
        is returned by :meth:`~pywbem.CIMClassName.to_wbem_uri` as the default
        format.

        If you want to access the class name, use the
        :attr:`~pywbem.CIMClassName.classname` attribute, instead of relying
        on the coincidence that the historical format of a WBEM URI without
        authority and namespace happens to be the class name.

        Examples (for the historical format):

        * With authority and namespace::

            //acme.com/cimv2/test:CIM_RegisteredProfile

        * Without authority but with namespace::

            cimv2/test:CIM_RegisteredProfile

        * Without authority and without namespace::

            CIM_RegisteredProfile
        """
        return self.to_wbem_uri(format='historical')

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
        *New in pywbem 0.9.*

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

    @staticmethod
    def from_wbem_uri(wbem_uri):
        """
        *New in pywbem 0.12.*

        Return a new :class:`~pywbem.CIMClassName` object from the specified
        WBEM URI string.

        The WBEM URI string must be a CIM class path in untyped WBEM URI
        format, as defined in :term:`DSP0207`, with these extensions:

        * DSP0207 restricts the namespace types (URI schemes) to be one of
          ``http``, ``https``, ``cimxml-wbem``, or ``cimxml-wbems``. Pywbem
          tolerates any namespace type, but issues a :exc:`py:UserWarning` if
          it is not one of the namespace types defined in DSP0207.

        * DSP0207 requires a slash before the namespace name. For local WBEM
          URIs (no namespace type, no authority), that slash is the first
          character of the WBEM URI. For historical reasons, pywbem tolerates a
          missing leading slash for local WBEM URIs. Note that pywbem requires
          the slash (consistent with DSP0207) when the WBEM URI is not local.

        CIM class paths in the typed WBEM URI format defined in DSP0207
        are not supported.

        Examples::

            https://jdd:test@acme.com:5989/cimv2/test:CIM_RegisteredProfile
            http://acme.com/root/cimv2:CIM_ComputerSystem
            http:/root/cimv2:CIM_ComputerSystem
            /root/cimv2:CIM_ComputerSystem
            root/cimv2:CIM_ComputerSystem
            /:CIM_ComputerSystem
            :CIM_ComputerSystem

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
            raise ValueError("Invalid format for a class path in "
                             "WBEM URI: %r" % wbem_uri)

        ns_type = m.group(1) or None
        if ns_type and ns_type.lower() not in WBEM_URI_NAMESPACE_TYPES:
            warnings.warn("Tolerating unknown namespace type in WBEM URI: %r" %
                          wbem_uri, UserWarning)

        host = m.group(2) or None
        namespace = m.group(3) or None
        classname = m.group(4) or None

        obj = CIMClassName(
            classname=classname,
            host=host,
            namespace=namespace)

        return obj

    def to_wbem_uri(self, format='standard'):
        # pylint: disable=redefined-builtin
        """
        Return the untyped WBEM URI of the CIM class path represented by the
        :class:`~pywbem.CIMClassName` object.

        The returned WBEM URI contains its components as follows:

        * it does not contain a namespace type (URI scheme).
        * it contains an authority component according to the
          :attr:`~pywbem.CIMClassName.host` attribute, if that is not
          `None`. Othwerise, it does not contain the authority component.
        * it contains a namespace component according to the
          :attr:`~pywbem.CIMClassName.namespace` attribute, if that is not
          `None`. Othwerise, it does not contain the namespace component.
        * it contains a class name component according to the
          :attr:`~pywbem.CIMClassName.classname` attribute.

        Parameters:

          format (:term:`string`): Format for the generated WBEM URI string,
            using one of the following values:

            * ``"standard"`` - Standard format that is conformant to untyped
              WBEM URIs for class paths defined in :term:`DSP0207`.

            * ``"cimobject"`` - Format for the `CIMObject` header field in
              CIM-XML messages for representing class paths (used
              internally, see :term:`DSP0200`).

            * ``"historical"`` - Historical format for WBEM URIs (used by
              :meth:`~pywbem.CIMClassName.__str__`; should not be used by
              new code). The historical format has the following differences to
              the standard format:

              - If the authority component is not present, the slash after the
                authority is also omitted. In the standard format, that slash
                is always present.

              - If the namespace component is not present, the colon after the
                namespace is also omitted. In the standard format, that colon
                is always present.

        Examples for the standard format:

        * With authority and namespace::

            //acme.com/cimv2/test:CIM_RegisteredProfile

        * Without authority but with namespace::

            /cimv2/test:CIM_RegisteredProfile

        * Without authority and without namespace::

            /:CIM_RegisteredProfile

        Returns:

          :term:`unicode string`: Untyped WBEM URI of the CIM class path,
          in the specified format.
        """

        ret = []

        if self.host is not None:
            ret.append('//')
            ret.append(self.host)

        if self.host is not None or format == 'standard':
            ret.append('/')

        if self.namespace is not None:
            ret.append(self.namespace)

        if self.namespace is not None or format in ('standard', 'cimobject'):
            ret.append(':')

        ret.append(self.classname)

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
            same-named attribute in the ``CIMClass`` object will also be
            `None`.

            The lexical case of the string is preserved. Object comparison and
            hash value calculation are performed case-insensitively.

          qualifiers (:term:`qualifiers input object`):
            The qualifiers for the class.

          path (:class:`~pywbem.CIMClassName`):
            *New in pywbem 0.11.*

            Class path for the class.

            The provided object will be stored in the ``CIMClass`` object
            (no copy is made).

            `None` means that the instance path is unspecified, and the
            same-named attribute in the ``CIMClass`` object will also be
            `None`.

            This parameter has been added in pywbem v0.11.0 as a convenience
            for the user in order so that ``CIMClass`` objects can be
            self-contained w.r.t. their class path.

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
        :term:`unicode string`: Class name of the CIM class.

        Will not be `None`.

        This attribute is settable. For details, see the description of the
        same-named constructor parameter.
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
        self._superclass = _ensure_unicode(superclass)

    @property
    def properties(self):
        """
        `NocaseDict`_: Properties (declarations) of the CIM class.

        Will not be `None`.

        Each dictionary item specifies one property declaration, with:

        * key (:term:`unicode string`): Property name. Its lexical case was
          preserved.

        * value (:class:`~pywbem.CIMProperty`): Property declaration.

        The order of properties in the CIM class is preserved.

        This attribute is settable; setting it will cause the current CIM
        properties to be replaced with the new properties. For details, see
        the description of the same-named constructor parameter.

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
                    raise TypeError("Input object for properties has "
                                    "invalid item in iterable: %r" % item)
                self.properties[key] = _cim_property_decl(key, value)

    @property
    def methods(self):
        """
        `NocaseDict`_: Methods (declarations) of the CIM class.

        Will not be `None`.

        Each dictionary item specifies one method, with:

        * key (:term:`unicode string`): Method name. Its lexical case was
          preserved.

        * value (:class:`~pywbem.CIMMethod`): Method declaration.

        The order of methods in the CIM class is preserved.

        This attribute is settable; setting it will cause the current CIM
        methods to be replaced with the new methods. For details, see
        the description of the same-named constructor parameter.

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
                    raise TypeError("Input object for methods has "
                                    "invalid item in iterable: %r" % item)
                self.methods[key] = _cim_method(key, value)

    @property
    def qualifiers(self):
        """
        `NocaseDict`_: Qualifiers (qualifier values) of the CIM class.

        Will not be `None`.

        Each dictionary item specifies one qualifier value, with:

        * key (:term:`unicode string`): Qualifier name. Its lexical case was
          preserved.

        * value (:class:`~pywbem.CIMQualifier`): Qualifier value.

        The order of qualifiers in the CIM class is preserved.

        This attribute is settable; setting it will cause the current
        qualifiers to be replaced with the new qualifiers. For details, see
        the description of the same-named constructor parameter.

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
                    raise TypeError("Input object for qualifiers has "
                                    "invalid item in iterable: %r" % item)
                self.qualifiers[key] = _cim_qualifier(key, value)

    @property
    def path(self):
        """
        *New in pywbem 0.11.*

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
        if not isinstance(other, CIMClass):
            raise TypeError("other must be CIMClass, but is: %s" %
                            type(other))
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
        Return a short string representation of the
        :class:`~pywbem.CIMClass` object for human consumption.
    """

        return '%s(classname=%r, ...)' % \
               (self.__class__.__name__, self.classname)

    def __repr__(self):
        """
        Return a string representation of the :class:`~pywbem.CIMClass`
        object that is suitable for debugging.

        The order of properties, method and qualifiers will be preserved in
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

        The order of properties, methods, parameters, and qualifiers is
        preserved.

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
        *New in pywbem 0.9.*

        Return the CIM-XML representation of the
        :class:`~pywbem.CIMClass` object, as a :term:`unicode string`.

        The returned CIM-XML representation is consistent with :term:`DSP0201`.

        The order of properties, methods, parameters, and qualifiers is
        preserved.

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

    def tomof(self, maxline=MAX_MOF_LINE):
        """
        Return a MOF string with the class definition represented by the
        :class:`~pywbem.CIMClass` object.

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
        The constructor infers optional parameters that are not specified (for
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
            Value of the property (interpreted as actual value when
            representing a property value, and as default value for property
            declarations).

            `None` means that the property is Null, and the same-named
            attribute in the ``CIMProperty`` object will also be `None`.

            The specified value will be converted to a :term:`CIM data type`
            using the rules documented in the description of
            :func:`~pywbem.cimvalue`, taking into account the `type` parameter.

          type (:term:`string`):
            Name of the CIM data type of the property (e.g. ``"uint8"``).

            `None` will cause the type to be inferred from the `value`
            parameter, raising `ValueError` if it cannot be inferred (for
            example when `value` is `None` or a Python integer).

          class_origin (:term:`string`):
            The CIM class origin of the property (the name
            of the most derived class that defines or overrides the property in
            the class hierarchy of the class owning the property).

            `None` means that class origin information is not available, and
            the same-named attribute in the ``CIMProperty`` object will also be
            `None`.

            The lexical case of the string is preserved. Object comparison and
            hash value calculation are performed case-insensitively.

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

            `None` means that it is unspecified whether the property is an
            array, and the same-named attribute in the
            ``CIMProperty`` object will be inferred from the
            `value` parameter. If the `value` parameter is `None`, a scalar is
            assumed.

          reference_class (:term:`string`):
            For reference properties, the name of the class referenced by the
            property, as declared in the class defining the property (for both,
            property declarations in CIM classes, and property values in CIM
            instances).

            `None` means that the referenced class is unspecified, and the
            same-named attribute in the ``CIMProperty`` object will also be
            `None`.

            The lexical case of the string is preserved. Object comparison and
            hash value calculation are performed case-insensitively.

            Note: Prior to pywbem v0.11.0, the corresponding attribute was
            inferred from the creation class name of a referenced instance.
            This was incorrect and has been fixed in v0.11.0.

          qualifiers (:term:`qualifiers input object`):
            The qualifiers for the property declaration. Has no meaning for
            property values.

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

        element_txt = "property %r" % name

        if type is None:
            type = _infer_type(value, element_txt)

        if is_array is None:
            is_array = _infer_is_array(value)

        _check_array_parms(is_array, array_size, value, element_txt)

        if embedded_object is None:
            embedded_object = _infer_embedded_object(value)

        if embedded_object is not None:
            _check_embedded_object(embedded_object, type, value, element_txt)

        if reference_class is not None:
            if is_array:
                raise ValueError("Property %r specifies reference_class "
                                 "%r but is an array property" %
                                 (name, reference_class))
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
        self._name = _ensure_unicode(name)

        # We perform this check after the initialization to avoid errors
        # in test tools that show the object with repr().
        if name is None:
            raise ValueError("CIMProperty 'name' parameter must not be None")

    @property
    def value(self):
        """
        :term:`CIM data type`: Value of the property (interpreted as actual
        value when representing a property value, and as default value for
        property declarations).

        `None` means that the value is Null.

        This attribute is settable. For details, see the description of the
        same-named constructor parameter.
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
        self._type = _ensure_unicode(type)

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
        self._reference_class = _ensure_unicode(reference_class)

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
        self._embedded_object = _ensure_unicode(embedded_object)

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
        self._is_array = _ensure_bool(is_array)

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
        self._class_origin = _ensure_unicode(class_origin)

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
        self._propagated = _ensure_bool(propagated)

    @property
    def qualifiers(self):
        """
        `NocaseDict`_: Qualifiers (qualifier values) of the property
        declaration.

        Will not be `None`.

        Each dictionary item specifies one qualifier value, with:

        * key (:term:`unicode string`): Qualifier name. Its lexical case was
          preserved.

        * value (:class:`~pywbem.CIMQualifier`): Qualifier value.

        The order of qualifiers in the property is preserved.

        This attribute is settable; setting it will cause the current
        qualifiers to be replaced with the new qualifiers. For details, see
        the description of the same-named constructor parameter.

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
                    raise TypeError("Input object for qualifiers has "
                                    "invalid item in iterable: %r" % item)
                self.qualifiers[key] = _cim_qualifier(key, value)

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

        The order of qualifiers will be preserved in the result.
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

        The order of qualifiers is preserved.
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
        *New in pywbem 0.9.*

        Return the CIM-XML representation of the
        :class:`~pywbem.CIMProperty` object, as a :term:`unicode string`.

        The returned CIM-XML representation is consistent with :term:`DSP0201`.

        The order of qualifiers is preserved.

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

    def tomof(
            self, is_instance=True, indent=0, maxline=MAX_MOF_LINE, line_pos=0):
        """
        *New in pywbem 0.9.*

        Return a MOF fragment with the property definition (for use in a CIM
        class) or property value (for use in a CIM instance) represented by the
        :class:`~pywbem.CIMProperty` object.

        Even though pywbem supports qualifiers on :class:`~pywbem.CIMProperty`
        objects that are used as property values within an instance, the
        returned MOF string for property values in instances does not contain
        any qualifier values.

        The order of qualifiers is preserved.

        Parameters:

          is_instance (bool): If True, return MOF for a property value in a CIM
            instance. Else, return MOF for a property definition in a CIM
            class.

          indent (:term:`integer`): Number of spaces to indent each line of
            the returned string, counted in the line with the property name.

        Returns:

          :term:`unicode string`: MOF fragment.
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
                if val_str[0] != '\n':
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
        if not isinstance(other, CIMProperty):
            raise TypeError("other must be CIMProperty, but is: %s" %
                            type(other))
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

            The lexical case of the string is preserved. Object comparison and
            hash value calculation are performed case-insensitively.

            Deprecated: This argument has been named `methodname` before
            v0.9.0. Using `methodname` as a named argument still works,
            but has been deprecated in v0.9.0.

          return_type (:term:`string`):
            Name of the CIM data type of the method return type
            (e.g. ``"uint32"``).

            Must not be `None` or ``"reference"``.

            Support for void return types: Pywbem also does not support void
            return types, consistent with the CIM architecture and MOF syntax
            (see :term:`DSP0004`).
            As a side note, the CIM-XML protocol (see :term:`DSP0200` and
            :term:`DSP0201`) is able to represent method declarations and
            method invocations with void return types.

            Support for reference return types: Pywbem does not support
            reference return types of methods.
            The CIM architecture and MOF syntax support reference return types.
            The CIM-XML protocol supports the invocation of methods with
            reference return types, but it does not support the representation
            of class declarations with methods that have reference return
            types. As a result, it is not possible to create such classes in a
            WBEM server using the CIM-XML protocol. For consistency, pywbem
            does not support reference return types, not even for method
            invocations.

            Support for array return types: Pywbem does not support array
            return types of methods, consistent with the CIM architecture,
            MOF syntax and the CIM-XML protocol.

          parameters (:term:`parameters input object`):
            Parameter declarations for the method.

          class_origin (:term:`string`):
            The CIM class origin of the method (the name
            of the most derived class that defines or overrides the method in
            the class hierarchy of the class owning the method).

            `None` means that class origin information is not available, and
            the same-named attribute in the ``CIMMethod`` object will also be
            `None`.

            The lexical case of the string is preserved. Object comparison and
            hash value calculation are performed case-insensitively.

          propagated (:class:`py:bool`):
            If not `None`, indicates whether the method has been propagated
            from a superclass to this class.

            `None` means that propagation information is not available, and the
            same-named attribute in the ``CIMMethod`` object will also be
            `None`.

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
        self._name = _ensure_unicode(name)

        # We perform this check after the initialization to avoid errors
        # in test tools that show the object with repr().
        if name is None:
            raise ValueError("CIMMethod 'name' parameter must not be None")

    @property
    def return_type(self):
        """
        :term:`unicode string`: Name of the CIM data type of the method return
        type (e.g. ``"uint32"``).

        Will not be `None` or ``"reference"``.

        This attribute is settable. For details, see the description of the
        same-named constructor parameter.
        """
        return self._return_type

    @return_type.setter
    def return_type(self, return_type):
        """Setter method; for a description see the getter method."""

        # pylint: disable=attribute-defined-outside-init
        self._return_type = _ensure_unicode(return_type)

        # We perform this check after the initialization to avoid errors
        # in test tools that show the object with repr().
        if return_type is None:
            raise ValueError('return_type must not be None')
        if return_type.lower() == 'reference':
            raise ValueError('return_type must not be "reference"')

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
        self._class_origin = _ensure_unicode(class_origin)

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
        self._propagated = _ensure_bool(propagated)

    @property
    def parameters(self):
        """
        `NocaseDict`_: Parameters of the method.

        Will not be `None`.

        Each dictionary item specifies one parameter, with:

        * key (:term:`unicode string`): Parameter name. Its lexical case was
          preserved.

        * value (:class:`~pywbem.CIMParameter`): Parameter declaration.

        The order of parameters in the method is preserved.

        This attribute is settable; setting it will cause the current
        parameters to be replaced with the new parameters. For details, see
        the description of the same-named constructor parameter.

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
                    raise TypeError("Input object for parameters has "
                                    "invalid item in iterable: %r" % item)
                self.parameters[key] = value

    @property
    def qualifiers(self):
        """
        `NocaseDict`_: Qualifiers (qualifier values) of the method.

        Will not be `None`.

        Each dictionary item specifies one qualifier value, with:

        * key (:term:`unicode string`): Qualifier name. Its lexical case was
          preserved.

        * value (:class:`~pywbem.CIMQualifier`): Qualifier value.

        The order of qualifiers in the method is preserved.

        This attribute is settable; setting it will cause the current
        qualifiers to be replaced with the new qualifiers. For details, see
        the description of the same-named constructor parameter.

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
                    raise TypeError("Input object for qualifiers has "
                                    "invalid item in iterable: %r" % item)
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
        if not isinstance(other, CIMMethod):
            raise TypeError("other must be CIMMethod, but is: %s" %
                            type(other))
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
        Return a short string representation of the
        :class:`~pywbem.CIMMethod` object for human consumption.
        """
        return '%s(name=%r, return_type=%r, ...)' % \
               (self.__class__.__name__, self.name, self.return_type)

    def __repr__(self):
        """
        Return a string representation of the :class:`~pywbem.CIMMethod`
        object that is suitable for debugging.

        The order of parameters and qualifiers will be preserved in the
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

        The order of parameters and qualifiers is preserved.
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
        *New in pywbem 0.9.*

        Return the CIM-XML representation of the
        :class:`~pywbem.CIMMethod` object, as a :term:`unicode string`.

        The returned CIM-XML representation is consistent with :term:`DSP0201`.

        The order of parameters and qualifiers is preserved.

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

    def tomof(self, indent=0, maxline=MAX_MOF_LINE):
        """
        Return a MOF fragment with the method definition represented by the
        :class:`~pywbem.CIMMethod` object.

        The order of parameters and qualifiers is preserved.

        Parameters:

          indent (:term:`integer`): Number of spaces to indent each line of
            the returned string, counted in the line with the method name.

        Returns:

          :term:`unicode string`: MOF fragment.
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
        The constructor stores the input parameters as-is and does
        not infer unspecified parameters from the others
        (like :class:`~pywbem.CIMProperty` does).

        Parameters:

          name (:term:`string`):
            Name of the parameter.

            Must not be `None`.

            The lexical case of the string is preserved. Object comparison and
            hash value calculation are performed case-insensitively.

          type (:term:`string`):
            Name of the CIM data type of the parameter (e.g. ``"uint8"``).

            Must not be `None`.

          reference_class (:term:`string`):
            For reference parameters, the name of the class referenced by the
            parameter, as declared in the class defining the method.

            `None` means that the referenced class is unspecified, and the
            same-named attribute in the ``CIMParameter`` object will also be
            `None`.

            The lexical case of the string is preserved. Object comparison and
            hash value calculation are performed case-insensitively.

          is_array (:class:`py:bool`):
            A boolean indicating whether the parameter is an array (`True`) or a
            scalar (`False`).

            `None` means that it is unspecified whether the parameter is an
            array, and the same-named attribute in the
            ``CIMParameter`` object will be inferred from the
            `value` parameter. If the `value` parameter is `None`, a scalar is
            assumed.

          array_size (:term:`integer`):
            The size of the array parameter, for fixed-size arrays.

            `None` means that the array parameter has variable size, and the
            same-named attribute in the ``CIMParameter`` object will also be
            `None`.

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
            attribute in the ``CIMParameter`` object to be inferred from
            the parameter value (i.e. the `value` parameter). An exception is
            raised if it cannot be inferred.
        """

        # We use the respective setter methods:
        self.name = name

        element_txt = "parameter %r" % name

        if is_array is None:
            is_array = _infer_is_array(value)
        _check_array_parms(is_array, array_size, value, element_txt)

        if embedded_object is None:
            embedded_object = _infer_embedded_object(value)

        if embedded_object is not None:
            _check_embedded_object(embedded_object, type, value, element_txt)

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
        self._name = _ensure_unicode(name)

        # We perform this check after the initialization to avoid errors
        # in test tools that show the object with repr().
        if name is None:
            raise ValueError("CIMParameter 'name' parameter must not be None")

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
        self._type = _ensure_unicode(type)

        # We perform this check after the initialization to avoid errors
        # in test tools that show the object with repr().
        if type is None:
            raise ValueError("CIMParameter 'type' parameter must not be None")

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
        self._reference_class = _ensure_unicode(reference_class)

    @property
    def is_array(self):
        """
        :class:`py:bool`: A boolean indicating whether the parameter is an array
        (`True`) or a scalar (`False`).

        `None` means that it is unspecified whether the parameter is an array.

        This attribute is settable. For details, see the description of the
        same-named constructor parameter.
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

        Will not be `None`.

        Each dictionary item specifies one qualifier value, with:

        * key (:term:`unicode string`): Qualifier name. Its lexical case was
          preserved.

        * value (:class:`~pywbem.CIMQualifier`): Qualifier value.

        The order of qualifiers in the parameter is preserved.

        This attribute is settable; setting it will cause the current
        qualifiers to be replaced with the new qualifiers. For details, see
        the description of the same-named constructor parameter.

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
                    raise TypeError("Input object for qualifiers has "
                                    "invalid item in iterable: %r" % item)
                self.qualifiers[key] = _cim_qualifier(key, value)

    @property
    def value(self):
        """
        The value of the CIM method parameter for the method invocation.
        Has no meaning for parameter declarations.

        This attribute is settable. For details, see the description of the
        same-named constructor parameter.
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
        object represented by the parameter value.
        Has no meaning for parameter declarations.

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
        same-named constructor parameter.
        """
        return self._embedded_object

    @embedded_object.setter
    def embedded_object(self, embedded_object):
        """Setter method; for a description see the getter method."""
        # pylint: disable=attribute-defined-outside-init
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
        if not isinstance(other, CIMParameter):
            raise TypeError("other must be CIMParameter, but is: %s" %
                            type(other))
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

        The order of qualifiers will be preserved in the result.
        """
        return '%s(name=%r, type=%r, ' \
               'reference_class=%r, ' \
               'is_array=%r, array_size=%r, ' \
               'qualifiers=%r, value=%r, ' \
               'embedded_object=%r)' % \
               (self.__class__.__name__, self.name, self.type,
                self.reference_class,
                self.is_array, self.array_size,
                self.qualifiers, self.value,
                self.embedded_object)

    def copy(self):
        """
        Return a copy of the :class:`~pywbem.CIMParameter` object.
        """
        result = CIMParameter(self.name,
                              self.type,
                              reference_class=self.reference_class,
                              is_array=self.is_array,
                              array_size=self.array_size,
                              value=self.value,
                              embedded_object=self.embedded_object)

        result.qualifiers = self.qualifiers.copy()

        return result

    def tocimxml(self, as_value=False):
        """
        Return the CIM-XML representation of the :class:`~pywbem.CIMParameter`
        object, either as a parameter declaration for use in a method
        declaration, or as a parameter value for use in a method invocation.

        The CIM-XML representation is consistent with :term:`DSP0201`.

        Parameters:

          as_value (bool): If `True`, return the object as a parameter value.
            Otherwise, return the object as a parameter declaration.

        Returns:

            The CIM-XML representation of the object, as an appropriate
            subclass of :term:`Element`.
        """

        if as_value:

            value = self.value

            if value is None:
                pass

            elif self.is_array:

                if self.type == 'reference':
                    val_array = []
                    for v in value:
                        if v is None:
                            val_array.append(cim_xml.VALUE_NULL())
                        else:
                            val_array.append(
                                cim_xml.VALUE_REFERENCE(v.tocimxml()))
                    value = cim_xml.VALUE_REFARRAY(val_array)

                else:
                    val_array = []
                    for v in value:
                        if v is None:
                            val_array.append(cim_xml.VALUE_NULL())
                        elif self.embedded_object is not None:
                            val_array.append(
                                cim_xml.VALUE(v.tocimxml().toxml()))
                        else:
                            val_array.append(
                                cim_xml.VALUE(atomic_to_cim_xml(v)))
                    value = cim_xml.VALUE_ARRAY(val_array)

            else:
                # scalar
                if self.type == 'reference':
                    value = cim_xml.VALUE_REFERENCE(value.tocimxml())
                elif self.embedded_object is not None:
                    value = cim_xml.VALUE(value.tocimxml().toxml())
                else:
                    value = cim_xml.VALUE(atomic_to_cim_xml(value))

            return cim_xml.PARAMVALUE(
                self.name,
                value,
                paramtype=self.type,
                embedded_object=self.embedded_object)

        else:

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

    def tocimxmlstr(self, indent=None, as_value=False):
        """
        *New in pywbem 0.9.*

        Return the CIM-XML representation of the :class:`~pywbem.CIMParameter`
        object, either as a parameter declaration for use in a method
        declaration, or as a parameter value for use in a method invocation.

        The returned CIM-XML representation is consistent with :term:`DSP0201`.

        The order of qualifiers is preserved.

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
        Return a MOF fragment with the parameter definition represented by the
        :class:`~pywbem.CIMParameter` object.

        The object is always interpreted as a parameter declaration; so the
        :attr:`~pywbem.CIMParameter.value` and
        :attr:`~pywbem.CIMParameter.embedded_object` attributes are ignored.

        The order of qualifiers is preserved.

        Parameters:

          indent (:term:`integer`): Number of spaces to indent each line of
            the returned string, counted in the line with the parameter name.

        Returns:

          :term:`unicode string`: MOF fragment.
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
        The constructor infers optional parameters that are not specified (for
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
            attribute in the ``CIMQualifier`` object will also be `None`.

            The specified value will be converted to a :term:`CIM data type`
            using the rules documented in the description of
            :func:`~pywbem.cimvalue`, taking into account the `type` parameter.

          type (:term:`string`):
            Name of the CIM data type of the qualifier (e.g. ``"uint8"``).

            `None` will cause the type to be inferred from the `value`
            parameter, raising `ValueError` if it cannot be inferred (for
            example when `value` is `None` or a Python integer).

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

        element_txt = "qualifier %r" % name

        if type is None:
            type = _infer_type(value, element_txt)

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
        self._name = _ensure_unicode(name)

        # We perform this check after the initialization to avoid errors
        # in test tools that show the object with repr().
        if name is None:
            raise ValueError("CIMQualifier 'name' parameter must not be None")

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
        self._type = _ensure_unicode(type)

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
        self._value = cimvalue(value, self.type)

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
        same-named constructor parameter.
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
        same-named constructor parameter.
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
        same-named constructor parameter.
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
        same-named constructor parameter.
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
            value = cim_xml.VALUE_ARRAY(
                [cim_xml.VALUE(atomic_to_cim_xml(v)) for v in self.value])
        elif self.value is not None:
            # used as VALUE.ARRAY and the as VALUE
            value = cim_xml.VALUE(atomic_to_cim_xml(self.value))

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
        *New in pywbem 0.9.*

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

    def tomof(self, indent=MOF_INDENT, maxline=MAX_MOF_LINE, line_pos=0):
        """
        Return a MOF fragment with the qualifier value represented by the
        :class:`~pywbem.CIMQualifier` object.

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

          :term:`unicode string`: MOF fragment.
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
        if val_str[0] != '\n':
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
          specification :TERM:`DSP0200`

    Because `None` is allowed as a value for the flavors attributes in
    constructing a CIMQualifierDeclaration, the user must insure that any
    flavor which has the value `None` is set to its default value if required
    for subsequent processing.

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
    ordered_scopes = ["CLASS", "ASSOCIATION", "INDICATION",
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

          value (:term:`CIM data type` or other suitable types):
            Default value of the qualifier.

            `None` means a default value of Null, and the same-named attribute
            in the ``CIMQualifierDeclaration`` object will also be `None`.

            The specified value will be converted to a :term:`CIM data type`
            using the rules documented in the description of
            :func:`~pywbem.cimvalue`, taking into account the `type` parameter.

          is_array (:class:`py:bool`):
            A boolean indicating whether the qualifier is an array (`True`) or
            a scalar (`False`).

            `None` means that it is unspecified whether the qualifier is an
            array, and the same-named attribute in the
            ``CIMQualifierDeclaration`` object will be inferred from the
            `value` parameter. If the `value` parameter is `None`, a scalar is
            assumed.

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

        # We use the respective setter methods:
        self.name = name

        element_txt = "qualifier declaration %r" % name

        if is_array is None:
            is_array = _infer_is_array(value)

        _check_array_parms(is_array, array_size, value, element_txt)

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
        self._name = _ensure_unicode(name)

        # We perform this check after the initialization to avoid errors
        # in test tools that show the object with repr().
        if name is None:
            raise ValueError("CIMQualifierDeclaration 'name' parameter must "
                             "not be None")

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
        self._type = _ensure_unicode(type)

        # We perform this check after the initialization to avoid errors
        # in test tools that show the object with repr().
        if type is None:
            raise ValueError("CIMQualifierDeclaration 'type' parameter must "
                             "not be None")

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
        self._value = cimvalue(value, self.type)

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
        self._is_array = _ensure_bool(is_array)

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

        * key (:term:`unicode string`): Scope name, in upper case.

        * value (:class:`py:bool`): Scope value, specifying whether the
          qualifier has that scope (i.e. can be applied to a CIM element of
          that kind).

        Valid scope names are "CLASS", "ASSOCIATION", "INDICATION",
        "PROPERTY", "REFERENCE", "METHOD", "PARAMETER", and "ANY".

        Will not be `None`.

        This attribute is settable. For details, see the description of the
        same-named constructor parameter.
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
        same-named constructor parameter.
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
        same-named constructor parameter.
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
        same-named constructor parameter.
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
        if not isinstance(other, CIMQualifierDeclaration):
            raise TypeError("other must be CIMQualifierDeclaration, "
                            "but is: %s" % type(other))
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
        *New in pywbem 0.9.*

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

    def tomof(self, maxline=MAX_MOF_LINE):
        """
        Return a MOF string with the qualifier type declaration represented by
        the :class:`~pywbem.CIMQualifierDeclaration` object.

        The returned MOF string conforms to the ``qualifierDeclaration``
        ABNF rule defined in :term:`DSP0004`.

        Qualifier flavors are included in the returned MOF string only when
        the information is available (i.e. the value of the corresponding
        attribute is not `None`).

        Because DSP0004 does not support instance qualifiers, and thus does not
        define a flavor keyword for the
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
        for scope in self.ordered_scopes:
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
    Return the CIM-XML representation of the input value, as an
    :term:`Element` object.

    The returned CIM-XML representation is consistent with :term:`DSP0201`.

    Parameters:

      value (:term:`CIM object`, :term:`CIM data type`, :term:`number`, :class:`py:datetime`, or tuple/list thereof):
        The input value. May be `None`.

    Returns:

      The CIM-XML representation of the specified value, as an object of an
      appropriate subclass of :term:`Element`.
    """  # noqa: E501

    if isinstance(value, (tuple, list)):
        return cim_xml.VALUE_ARRAY([tocimxml(v) for v in value])

    if hasattr(value, 'tocimxml'):
        return value.tocimxml()

    return cim_xml.VALUE(atomic_to_cim_xml(value))


def tocimxmlstr(value, indent=None):
    """
    *New in pywbem 0.9.*

    Return the CIM-XML representation of the CIM object or CIM data type,
    as a :term:`unicode string`.

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
            raise TypeError("Type of indent must be string or integer, "
                            "but is: %s" % type(indent))
        xml_str = xml_elem.toprettyxml(indent=indent)
    # xml_str is a unicode string if required based upon its content.
    return _ensure_unicode(xml_str)


# Note: The new cimvalue() function introduced in pywbem v0.12.0 is now used
# internally in the CIM object classes, instead of tocimobj(). However,
# tocimobj() is still used internally in the tupleparser, plus it is part of
# the public API.
# TODO 12/16 AM #904: Migr. remaining uses of tocimobj() to cimvalue() and depr.
#
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

    Raises:

        ValueError: Input cannot be converted to defined CIMValue type or
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

    if type_ == 'reference':  # pylint: disable=too-many-nested-blocks
        # pylint: disable=too-many-return-statements,too-many-branches

        # Note: This doesn't handle double-quoting, as in refs to refs. Example:
        # r'ex_composedof.composer="ex_sampleClass.label1=9921,' +
        #  'label2=\"SampleLabel\"",component="ex_sampleClass.label1=0121,' +
        #  'label2=\"Component\""')

        if isinstance(value, (CIMInstanceName, CIMClassName)):
            return value
        elif isinstance(value, six.string_types):
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
                    head = '%s,%s' % (head, tmp)
                    tail = _partition(tail, ',')[2]
                head = head.strip()
                key, sep, val = _partition(head, '=')
                if sep:
                    cl_name, s, k = _partition(key, '.')
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


def cimvalue(value, type):
    # pylint: disable=redefined-builtin
    """
    *New in pywbem 0.12.*

    Return a :term:`CIM data type` representing the specified value in the
    specified CIM type.

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
        if isinstance(value, CIMInstanceName):
            return value
        if isinstance(value, six.string_types):
            return CIMInstanceName.from_wbem_uri(value)
        raise TypeError("Input value has invalid type for a CIM reference: "
                        "%r" % value)

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


def _infer_type(value, element_txt):
    """
    Infer the CIM type name of the value, based upon its Python type.
    """

    if value is None:
        raise ValueError("Cannot infer CIM type of %s from its value when "
                         "the value is None" % element_txt)

    try:
        return cimtype(value)
    except TypeError as exc:
        raise ValueError("Cannot infer CIM type of %s from its value: %s" %
                         (element_txt, exc))


def _infer_is_array(value):
    """
    Infer whether the value is an array, based upon its Python type.

    A value of None defaults to be considered a scalar.
    """

    if value is None:
        return False

    return isinstance(value, list)


def _check_array_parms(is_array, array_size, value, element_txt):
    """
    Check whether array-related parameters are ok.
    """

    assert is_array is not None
    # _infer_is_array() ensures that, and is supposed to be called

    if array_size and not is_array:
        raise ValueError("The array_size parameter of %s is %r but "
                         "the is_array parameter is False." %
                         (element_txt, array_size))

    if value is not None:
        value_is_array = isinstance(value, (list, tuple))
        if not is_array and value_is_array:
            raise ValueError("The is_array parameter of %s is False but "
                             "value %r is an array." %
                             (element_txt, value))
        if is_array and not value_is_array:
            raise ValueError("The is_array parameter of %s is True but "
                             "value %r is not an array." %
                             (element_txt, value))


def _infer_embedded_object(value):
    """
    Infer CIMProperty.embedded_object from the CIM value.
    """

    if value is None:
        # The default behavior is to assume that a value of None is not
        # an embedded object. If the user wants that, they must specify
        # the embedded_object parameter.
        return None

    if isinstance(value, list):
        if not value:
            # The default behavior is to assume that an empty array value
            # is not an embedded object. If the user wants that, they must
            # specify the embedded_object parameter.
            return None
        value = value[0]

    if isinstance(value, CIMInstance):
        # The default behavior is to produce 'instance', although 'object'
        # would also be valid.
        return 'instance'

    if isinstance(value, CIMClass):
        return 'object'

    return None


def _check_embedded_object(embedded_object, type, value, element_txt):
    # pylint: disable=redefined-builtin
    """
    Check whether embedded-object-related parameters are ok.
    """

    if embedded_object not in ('instance', 'object'):
        raise ValueError("%s specifies an invalid value for embedded_object: "
                         "%r (must be 'instance' or 'object')" %
                         (element_txt, embedded_object))

    if type != 'string':
        raise ValueError("%s specifies embedded_object %r but its CIM type is "
                         "invalid: %r (must be 'string')" %
                         (element_txt, embedded_object, type))

    if value is not None:
        if isinstance(value, list):
            if value:
                v0 = value[0]  # Check the first array element
                if v0 is not None and \
                        not isinstance(v0, (CIMInstance, CIMClass)):
                    raise ValueError("Array %s specifies embedded_object %r "
                                     "but the Python type of its first array "
                                     "value is invalid: %s (must be "
                                     "CIMInstance or CIMClass)" %
                                     (element_txt, embedded_object,
                                      builtin_type(v0)))
        else:
            if not isinstance(value, (CIMInstance, CIMClass)):
                raise ValueError("%s specifies embedded_object %r but the "
                                 "Python type of its value is invalid: %s "
                                 "(must be CIMInstance or CIMClass)" %
                                 (element_txt, embedded_object,
                                  builtin_type(value)))


def byname(nlist):
    """
    Convert a list of named objects into a map indexed by name
    """
    return dict([(x.name, x) for x in nlist])
