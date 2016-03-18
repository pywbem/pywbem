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

"""Representations of CIM objects, and a case-insensitive dictionary.

In general we try to map CIM objects directly into Python primitives,
except when that is not possible or would be ambiguous.  For example,
CIM class names are simply Python strings, but a class path is
represented as a special Python object.

These objects can also be mapped back into CIM-XML, by their `tocimxml()`
method which returns a CIM-XML string.
"""
from __future__ import print_function
# This module is meant to be safe for 'import *'.

import re
from datetime import datetime, timedelta
import six
if six.PY2:
    # pylint: disable=wrong-import-order
    from __builtin__ import type as builtin_type
else:
    # pylint: disable=wrong-import-order
    from builtins import type as builtin_type

from . import cim_xml
from .cim_types import _CIMComparisonMixin, type_from_name, \
                       cimtype, atomic_to_cim_xml, CIMType, \
                       CIMDateTime, Uint8, Sint8, Uint16, Sint16, Uint32, \
                       Sint32, Uint64, Sint64, Real32, Real64

__all__ = ['CIMClassName', 'CIMProperty', 'CIMInstanceName', 'CIMInstance',
           'CIMClass', 'CIMMethod', 'CIMParameter', 'CIMQualifier',
           'CIMQualifierDeclaration', 'tocimxml', 'tocimobj']

DEFAULT_INDENT = 7

# pylint: disable=too-many-lines
class NocaseDict(object):
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

          * If one positional argument of sequence type is provided, the items
            in that sequence must be tuples of key and value, respectively.
            The key/value pairs will be put into the new dictionary (without
            copying them).

          * If one positional argument of dictionary (mapping) or `NocaseDict`
            type is provided, its key/value pairs are put into the new
            dictionary (without copying them).

          * Otherwise, `TypeError` is raised.

        After that, any provided keyword arguments are put into the so
        initialized dictionary as key/value pairs (without copying them).
        """

        self._data = {}

        # Step 1: Initialize from at most one positional argument
        if len(args) == 1:
            if isinstance(args[0], list):
                # Initialize from sequence object
                for item in args[0]:
                    self[item[0]] = item[1]
            elif isinstance(args[0], dict):
                # Initialize from mapping object
                self.update(args[0])
            elif isinstance(args[0], NocaseDict):
                # Initialize from another NocaseDict object
                self._data = args[0]._data.copy() # pylint: disable=protected-access
            elif args[0] is None:
                # Leave empty
                pass
            else:
                raise TypeError(
                    "Invalid type for NocaseDict initialization: %s" %\
                    repr(args[0]))
        elif len(args) > 1:
            raise TypeError(
                "Too many positional arguments for NocaseDict initialization: "\
                "%s" % repr(args))

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
            raise KeyError('Key %s not found in %r' % (key, self))

    def __setitem__(self, key, value):
        """
        Invoked when assigning a value for a key using `d[key] = val`.

        The key is looked up case-insensitively. If the key does not exist,
        it is added with the new value. Otherwise, its value is overwritten
        with the new value.

        Raises `TypeError` if the specified key does not have string type.
        """
        if not isinstance(key, six.string_types):
            raise TypeError('NocaseDict key %s must be string type, ' \
                            'but is %s' %  (key, builtin_type(key)))
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
            raise KeyError('Key %s not found in %r' % (key, self))

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
        if not key in self:
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
        Invoked when using `repr(d)`.

        The representation hides the implementation data structures and shows
        a dictionary that can be used for the constructor.
        """
        items = ', '.join([('%r: %r' % (key, value))
                           for key, value in self.iteritems()])
        return 'NocaseDict({%s})' % items

    def update(self, *args, **kwargs):
        """
        Update the dictionary from sequences of key/value pairs provided in any
        positional arguments, and from key/value pairs provided in any keyword
        arguments. The key/value pairs are not copied.

        Each positional argument can be:

          * an object with a method `items()` that returns an iterable of
            tuples containing key and value.

          * an object without such a method, that is an iterable of tuples
            containing key and value.

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
        result._data = self._data.copy() # pylint: disable=protected-access
        return result

    def __eq__(self, other):
        """
        Invoked when two dictionaries are compared with the `==` operator.

        The comparison is based on matching key/value pairs.
        The keys are looked up case-insensitively.
        """
        for key, self_value in self.iteritems():
            if not key in other:
                return False
            other_value = other[key]
            try:
                if not self_value == other_value:
                    return False
            except TypeError:
                return False # not comparable -> considered not equal
        return len(self) == len(other)

    def __ne__(self, other):
        """
        Invoked when two dictionaries are compared with the `!=` operator.

        Implemented by delegating to the `==` operator.
        """
        return not self == other

    def __lt__(self, other):
        """
        Invoked when two dictionaries are compared with the `<` operator.

        `self` is less than `other`, if:
          * a key in `self` is not in `other`, or
          * the value for a key in `self` is less than the value for that key
            in `other`, or
          * `self` has less key/value pairs than `other`.

        The keys are looked up case-insensitively.
        """
        for key, self_value in self.iteritems():
            if not key in other:
                return True
            other_value = other[key]
            try:
                if self_value < other_value:
                    return True
            except TypeError:
                return True # not comparable -> return arbitrary result
        return len(self) - len(other)

    def __gt__(self, other):
        """
        Invoked when two dictionaries are compared with the `>` operator.

        Implemented by delegating to the `<` operator.
        """
        return other < self

    def __ge__(self, other):
        """
        Invoked when two dictionaries are compared with the `>=` operator.

        Implemented by delegating to the `>` and `==` operators.
        """
        return (self > other) or (self == other)

    def __le__(self, other):
        """
        Invoked when two dictionaries are compared with the `<=` operator.

        Implemented by delegating to the `<` and `==` operators.
        """
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
            return intended[0] # the default
        elif actual in intended:
            return actual
        else:
            raise ValueError(msg + ", but specifies %s=%r (must be one of %r)"\
                             % (name, actual, intended))
    else:
        if actual == unspecified:
            return intended
        elif actual == intended:
            return actual
        else:
            raise ValueError(msg + ", but specifies %s=%r (must be %r)"\
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
    if lower_name1 < lower_name2:
        return -1
    else:
        return 1

def cmpitem(item1, item2):
    """
    Compare two items (CIM values, or other attributes of CIM objects).

    One or both of the items may be `None`, and `None` is considered the lowest
    possible value.

    The implementation delegates to the '==' and '<' operators of the
    item datatypes.

    If value1 == value2, 0 is returned.
    If value1 < value2, -1 is returned.
    Otherwise, +1 is returned.
    """
    if item1 is None and item2 is None:
        return 0
    if item1 is None:
        return -1
    if item2 is None:
        return 1
    if item1 == item2:
        return 0
    try:
        if item1 < item2:
            return -1
        else:
            return 1
    except TypeError:
        return -1  # if non-orderable, return arbitrary result

def _convert_unicode(obj):
    """
    Convert the input object into a Unicode string (`unicode`for Python 2,
    and `str` for Python 3).

    If the input object already is a Unicode string, it is simply returned.
    If the input object is a byte string, it is decoded using UTF-8.
    Otherwise, the input object is translated into its string representation.
    """
    if isinstance(obj, six.text_type):
        return obj
    if isinstance(obj, six.binary_type):
        return obj.decode("utf-8")
    return six.text_type(obj)

def _ensure_unicode(obj):
    """
    Return the input object, ensuring that a byte string is decoded into a
    Unicode string (`unicode`for Python 2, and `str` for Python 3).

    If the input object is a byte string, it is decoded using UTF-8.
    Otherwise, the input object is simply returned.
    """
    if isinstance(obj, six.binary_type):
        return obj.decode("utf-8")
    return obj

def _convert_bytes(obj):
    """
    Convert the input object into a byte string (`str`for Python 2, and `bytes`
    for Python 3).

    If the input object already is a byte string, it is simply returned.
    If the input object is a Unicode string, it is encoded using UTF-8.
    Otherwise, the input object is translated into its string representation.
    """
    if isinstance(obj, six.binary_type):
        return obj
    if isinstance(obj, six.text_type):
        return obj.encode("utf-8")
    return six.binary_type(obj)

def _ensure_bytes(obj):
    """
    Return the input object, ensuring that a Unicode string is decoded into a
    byte string (`str`for Python 2, and `bytes` for Python 3).

    If the input object is a Unicode string, it is encoded using UTF-8.
    Otherwise, the input object is simply returned.
    """
    if isinstance(obj, six.text_type):
        return obj.encode("utf-8")
    return obj

def _makequalifiers(qualifiers, indent):
    """Return a MOF fragment for a NocaseDict of qualifiers."""

    if len(qualifiers) == 0:
        return ''

    return '[%s]' % ',\n '.ljust(indent+2).\
        join([q.tomof(indent) for q in sorted(qualifiers.values())])

def mofstr(strvalue, indent=7, maxline=80):
    """Converts the input string value to a MOF literal string value, including
    the surrounding double quotes.

    In doing so, all characters that have MOF escape characters (except for
    single quotes) are escaped by adding a leading backslash (\\), if not yet
    present. This conditional behavior is needed for WBEM servers that return
    the MOF escape sequences in their CIM-XML representation of any strings,
    instead of converting them to the binary characters as required by the CIM
    standards.

    Single quotes do not need to be escaped because the returned literal
    string uses double quotes.

    After escaping, the string is broken into multiple lines, for better
    readability. The maximum line size is specified via the ``maxline``
    argument. The indentation for any spilled over lines (i.e. not the first
    line) is specified via the ``indent`` argument.
    """

    # escape \n, \r, \t, \f, \b
    escaped_str = strvalue.replace("\n", "\\n").replace("\r", "\\r").\
                  replace("\t", "\\t").replace("\f", "\\f").replace("\b", "\\b")

    # escape double quote (") if not already escaped.
    # TODO: Add support for two consecutive double quotes ("").
    escaped_str = re.sub(r'([^\\])"', r'\1\\"', escaped_str)

    # escape special case of a single double quote (")
    escaped_str = re.sub(r'^"$', r'\"', escaped_str)

    # escape backslash (\) not followed by any of: nrtfb"'
    escaped_str = re.sub(r'\\([^nrtfb"\'])', r'\\\1', escaped_str)

    # escape special case of a single backslash (\)
    escaped_str = re.sub(r'^\\$', r'\\\\', escaped_str)

    # Break into multiple strings for better readability
    blankfind = maxline - indent - 2
    indent_str = ' '.ljust(indent, ' ')
    ret_str_list = list()
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
                    splitpos = blankfind-1
                ret_str_list.append('"' + escaped_str[0:splitpos+1] + '"')
                escaped_str = escaped_str[splitpos+1:]

    ret_str = ('\n'+indent_str).join(ret_str_list)
    return ret_str

def moftype(cim_type, refclass):
    """Converts a CIM type name to MOF syntax."""

    if cim_type == 'reference':
        _moftype = refclass + " REF"
    else:
        _moftype = cim_type

    return _moftype


class CIMClassName(_CIMComparisonMixin):
    """
    A CIM class path.

    A CIM class path references a CIM class in a namespace in a WBEM server.
    Namespace and WBEM server may be unknown.

    :Ivariables:

      ...
        All parameters of `__init__` are set as instance variables.
    """

    def __init__(self, classname, host=None, namespace=None):
        """
        Initialize the `CIMClassName` object.

        :Parameters:

          classname : Unicode string or UTF-8 encoded byte string
            Name of the referenced class.

          host : Unicode string or UTF-8 encoded byte string
            Optional: URL of the WBEM server that contains the CIM namespace
            of this class path.

            If `None`, the class path will not specify a WBEM server.

            Default: `None`.

          namespace : Unicode string or UTF-8 encoded byte string
            Optional: Name of the CIM namespace that contains the referenced
            class.

            If `None`, the class path will not specify a CIM namespace.

            Default: `None`.

        :Raises:
          :raise TypeError:
          :raise ValueError:
        """

        # Make sure we process Unicode strings
        classname = _ensure_unicode(classname)
        host = _ensure_unicode(host)
        namespace = _ensure_unicode(namespace)

        if not isinstance(classname, six.string_types):
            raise TypeError(
                "classname argument has an invalid type: %s "\
                "(expected string)" % builtin_type(classname))

        # TODO: There are some odd restrictions on what a CIM
        # classname can look like (i.e must start with a
        # non-underscore and only one underscore per classname).

        self.classname = classname
        self.host = host
        self.namespace = namespace

    def copy(self):
        """Return a copy the CIMClassName object"""

        return CIMClassName(self.classname, host=self.host,
                            namespace=self.namespace)

    def _cmp(self, other):
        """
        Comparator function for two `CIMClassName` objects.

        The comparison is based on the `host`, `namespace`, and `classname`
        attributes of the `CIMClassName` objects, in descending precedence.

        All of them are compared case-insensitively.

        Raises `TypeError', if the `other` object is not a `CIMProperty`
        object.
        """
        if self is other:
            return 0
        if not isinstance(other, CIMClassName):
            raise TypeError("other must be CIMClassName, but is: %s" %\
                            type(other))
        return (cmpname(self.host, other.host) or
                cmpname(self.namespace, other.namespace) or
                cmpname(self.classname, other.classname))

    def __str__(self):
        """ Return readable string representing path"""

        ret_str = ''

        if self.host is not None:
            ret_str += '//%s/' % self.host

        if self.namespace is not None:
            ret_str += '%s:' % self.namespace

        ret_str += self.classname

        return ret_str

    def __repr__(self):
        """ Return String representing path in form name=value"""

        rep = '%s(classname=%r' % (self.__class__.__name__, self.classname)

        if self.host is not None:
            rep += ', host=%r' % self.host

        if self.namespace is not None:
            rep += ', namespace=%r' % self.namespace

        rep += ')'

        return rep

    def tocimxml(self):
        """
        Convert the CIMClassName object to CIM/XML consistent with
        DMTF DSP-0200 format and return the resulting XML
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


# pylint: disable=too-many-statements,too-many-instance-attributes
class CIMProperty(_CIMComparisonMixin):
    """
    Defines a CIM property including cim type, value, and possibly
    qualifiers.

    The property can be used in a CIM instance (as part of a
    `CIMInstance` object) or in a CIM class (as part of a
    `CIMClass` object).

    For properties in CIM instances:

      * The `value` instance variable is the actual value of the property.
      * Qualifiers are not allowed.

    For properties in CIM classes:

      * The `value` instance variable is the default value for the property.
      * Qualifiers are allowed.

    Scalar (=non-array) properties may have a value of NULL (= `None`), any
    primitive CIM type, reference type, and string type with embedded instance
    or embedded object.

    Array properties may be Null or may have elements with a value of NULL, any
    primitive CIM type, and string type with embedded instance or embedded
    object. Reference types are not allowed in property arrays in CIM, as per
    DMTF DSP0004.

    :Ivariables:

      ...
        All parameters of `__init__` are set as instance variables.
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
        Initialize the `CIMProperty` object.

        This function infers optional arguments that are not specified (for
        example, it infers `type` from the Python type of `value` and other
        information). If the specified arguments are inconsistent, an
        exception is raised. If an optional argument is needed for some reason,
        an exception is raised.

        :Parameters:

          name : Unicode string or UTF-8 encoded byte string
            Name of the property. Must not be `None`.

          value
            Value of the property (interpreted as actual value when the
            property object is used in an instance, and as default value when
            it is used in a class).
            For valid types for CIM values, see `cim_types`.

          type : Unicode string or UTF-8 encoded byte string
            Name of the CIM type of the property (e.g. `'uint8'`).
            `None` means that the argument is unspecified, causing the
            corresponding instance variable to be inferred. An exception is
            raised if it cannot be inferred.

          class_origin : Unicode string or UTF-8 encoded byte string
            The CIM class origin of the property (the name
            of the most derived class that defines or overrides the property in
            the class hierarchy of the class owning the property).
            `None` means that class origin information is not available.

          array_size : `int`
            The size of the array property, for fixed-size arrays.
            `None` means that the array property has variable size.

          propagated : Unicode string or UTF-8 encoded byte string
            The CIM *propagated* attribute of the property (the effective value
            of the `Propagated` qualifier of the property, which is a string
            that specifies the name of the source property from which the
            property value should be propagated).
            `None` means that propagation information is not available.

          is_array : `bool`
            A boolean indicating whether the property is an array (`True`) or a
            scalar (`False`).
            `None` means that the argument is unspecified, causing the
            corresponding instance variable to be inferred from the `value`
            parameter, and if that is `None` it defaults to `False` (scalar).

          reference_class : Unicode string or UTF-8 encoded byte string
            The name of the referenced class, for reference properties.
            `None` means that the argument is unspecified, causing the
            corresponding instance variable  to be inferred. An exception is
            raised if it cannot be inferred.

          qualifiers : `dict` or `NocaseDict`
            A dictionary specifying CIM qualifier values.
            The dictionary keys must be the qualifier names. The dictionary
            values must be `CIMQualifier` objects specifying the qualifier
            values.
            `None` means that there are no qualifier values. In all cases,
            the `qualifiers` instance variable will be a `NocaseDict` object.

          embedded_object : Unicode string or UTF-8 encoded byte string
            A string value indicating the kind of
            embedded object represented by the property value. The following
            values are defined for this argument:
            `'instance'`: The property is declared with the
            `EmbeddedInstance` qualifier, indicating that the property
            value is an embedded instance of a known class name (or Null).
            `'object'`: The property is declared with the
            `EmbeddedObject` qualifier, indicating that the property
            value is an embedded object (instance or class) of which the
            class name is not known (or Null).
            `None` means that the argument is unspecified, causing the
            corresponding instance variable to be inferred. An exception is
            raised if it cannot be inferred.

        Examples:

          * `CIMProperty("MyString", "abc")`
            -> a string property
          * `CIMProperty("MyNum", 42, "uint8")`
            -> a uint8 property
          * `CIMProperty("MyNum", Uint8(42))`
            -> a uint8 property
          * `CIMProperty("MyNumArray", [1,2,3], "uint8")`
            -> a uint8 array property
          * `CIMProperty("MyRef", CIMInstanceName(...))`
            -> a reference property
          * `CIMProperty("MyEmbObj", CIMClass(...))`
            -> an embedded object property containing a class
          * `CIMProperty("MyEmbObj", CIMInstance(...),
            embedded_object='object')`
            -> an embedded object property containing an instance
          * `CIMProperty("MyEmbInst", CIMInstance(...))`
            -> an embedded instance property
          * `CIMProperty("MyString", None, "string")`
            -> a string property that is Null
          * `CIMProperty("MyNum", None, "uint8")`
            -> a uint8 property that is Null
          * `CIMProperty("MyRef", None, reference_class="MyClass")`
            -> a reference property that is Null
          * `CIMProperty("MyEmbObj", None, embedded_object='object')`
            -> an embedded object property that is Null
          * `CIMProperty("MyEmbInst", None, embedded_object='instance')`
            -> an embedded instance property that is Null

        :Raises:
          :raise TypeError:
          :raise ValueError:
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
            raise ValueError('Property %r specifies an invalid ' \
                             'embedded_object=%r' % (name, embedded_object))

        if is_array not in (None, True, False):
            raise ValueError('Property %r specifies an invalid ' \
                             'is_array=%r' % (name, is_array))

        # Set up is_array

        if isinstance(value, (list, tuple)):
            is_array = _intended_value(
                True, None, is_array, 'is_array',
                'Property %r has a value that is an array (%s)' % \
                (name, builtin_type(value)))
        elif value is not None: # Scalar value
            is_array = _intended_value(
                False, None, is_array, 'is_array',
                'Property %r has a value that is a scalar (%s)' % \
                (name, builtin_type(value)))
        else: # Null value
            if is_array is None:
                is_array = False # For compatibility with old default

        if not is_array and array_size is not None:
            raise ValueError('Scalar property %r specifies array_size=%r ' \
                             '(must be None)' % (name, array_size))

        # Determine type, embedded_object, and reference_class attributes.
        # Make sure value is CIM-typed.

        if is_array: # Array property
            if reference_class is not None:
                raise ValueError(
                    'Array property %r cannot specify reference_class' % name)
            elif value is None or len(value) == 0 or value[0] is None:
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
                        'Cannot infer type of array property %r that is ' \
                        'Null, empty, or has Null as its first element' % \
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
                value = [CIMDateTime(val) if val is not None
                         and not isinstance(val, CIMDateTime)
                         else val for val in value]
                msg = 'Array property %r specifies CIM type %r' % (name, type_)
                embedded_object = _intended_value(
                    None, None, embedded_object, 'embedded_object', msg)
            elif type_ is None:
                # Determine simple type from (non-Null) value
                type_ = cimtype(value[0])
                msg = 'Array property %r contains simple typed values ' \
                      'with no CIM type specified' % name
                embedded_object = _intended_value(
                    None, None, embedded_object, 'embedded_object', msg)
            else: # type is specified and value (= entire array) is not Null
                # Make sure the array elements are of the corresponding Python
                # type.
                value = [type_from_name(type_)(val) if val is not None
                         else val for val in value]
                msg = 'Array property %r contains simple typed values ' \
                        'and specifies CIM type %r' % (name, type_)
                embedded_object = _intended_value(
                    None, None, embedded_object, 'embedded_object', msg)
        else: # Scalar property
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
                    dummy_type_obj = type_from_name(type_)
                else:
                    raise ValueError('Cannot infer type of simple ' \
                                     'property %r that is Null' % name)
            elif isinstance(value, CIMInstanceName):
                msg = 'Property %r has a CIMInstanceName value with ' \
                        'classname=%r' % (name, value.classname)
                reference_class = _intended_value(
                    value.classname, None, reference_class, 'reference_class',
                    msg)
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
                msg = 'Property %r specifies CIM type %r' % (name, type_)
                embedded_object = _intended_value(
                    None, None, embedded_object, 'embedded_object', msg)
                reference_class = _intended_value(
                    None, None, reference_class, 'reference_class', msg)
            elif type_ is None:
                # Determine simple type from (non-Null) value
                type_ = cimtype(value)
                msg = 'Property %r has a simple typed value ' \
                      'with no CIM type specified' % name
                embedded_object = _intended_value(
                    None, None, embedded_object, 'embedded_object', msg)
                reference_class = _intended_value(
                    None, None, reference_class, 'reference_class', msg)
            else: # type is specified and value is not Null
                # Make sure the value is of the corresponding Python type.
                _type_obj = type_from_name(type_)
                value = _type_obj(value)  # pylint: disable=redefined-variable-type
                msg = 'Property %r has a simple typed value ' \
                        'and specifies CIM type %r' % (name, type_)
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

    def copy(self):
        """ Return a copy of the CIMProperty object"""

        return CIMProperty(self.name,
                           self.value,
                           type=self.type,
                           class_origin=self.class_origin,
                           array_size=self.array_size,
                           propagated=self.propagated,
                           is_array=self.is_array,
                           reference_class=self.reference_class,
                           qualifiers=self.qualifiers.copy())

    def __repr__(self):
        """ Return a string repesenting the CIMProperty in
            name=value form for each attribute of the CIMProperty
        """

        return '%s(name=%r, value=%r, type=%r, class_origin=%r, ' \
               'array_size=%r, propagated=%r, is_array=%r, ' \
               'reference_class=%r, qualifiers=%r, embedded_object=%r)' % \
               (self.__class__.__name__, self.name, self.value, self.type,
                self.class_origin, self.array_size, self.propagated,
                self.is_array, self.reference_class, self.qualifiers,
                self.embedded_object)

    def tocimxml(self):
        """ Return the string with CIM/XML form of the CIMProperty object using
            the representation defined in DSP0200
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
                value = cim_xml.VALUE(value) # pylint: disable=redefined-variable-type

            return cim_xml.PROPERTY(
                self.name,
                self.type,
                value,
                class_origin=self.class_origin,
                propagated=self.propagated,
                qualifiers=[q.tocimxml() for q in self.qualifiers.values()],
                embedded_object=self.embedded_object)

    def _cmp(self, other):
        """
        Comparator function for two `CIMProperty` objects.

        The comparison is based on the `name`, `value`, `type`,
        `reference_class`, `is_array`, `array_size`, `propagated`,
        `class_origin`, and `qualifiers` instance attributes, in descending
        precedence.

        The `name` and `reference_class` attributes are compared
        case-insensitively.

        Raises `TypeError', if the `other` object is not a `CIMProperty`
        object.
        """
        if self is other:
            return 0
        if not isinstance(other, CIMProperty):
            raise TypeError("other must be CIMProperty, but is: %s" %\
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


class CIMInstanceName(_CIMComparisonMixin):
    """
    A CIM instance path (aka *instance name*).

    A CIM instance path references a CIM instance in a namespace in a WBEM
    server.
    Namespace and WBEM server may be unknown.

    This object can be used like a dictionary to retrieve the key bindings.

    :Ivariables:

      ...
        All parameters of `__init__` are set as instance variables.
    """

    def __init__(self, classname, keybindings=None, host=None, namespace=None):
        """
        Initialize the `CIMInstanceName` object.

        :Parameters:

          classname : Unicode string or UTF-8 encoded byte string
            Name of the creation class of the referenced instance.

          keybindings : `dict` or `NocaseDict`
            Optional: Dictionary of key bindings, specifying key properties
            that identify the referenced instance.
            The dictionary must contain one item for each key property, where:

            - its key is the property name.
            - its value is the property value, as a CIM typed value as
              described in `cim_types`.

            If `None`, an empty dictionary of key bindings will be created.

            Default: `None`.

          host : Unicode string or UTF-8 encoded byte string
            Optional: URL of the WBEM server that contains the CIM namespace
            of this instance path.

            If `None`, the instance path will not specify a WBEM server.

            Default: `None`.

          namespace : Unicode string or UTF-8 encoded byte string
            Optional: Name of the CIM namespace that contains the referenced
            instance.

            If `None`, the instance path will not specify a CIM namespace.

            Default: `None`.

        :Raises:
          :raise TypeError:
          :raise ValueError:
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

    def copy(self):
        """ Return a copy of the CIMInstanceName object """

        result = CIMInstanceName(self.classname)
        result.keybindings = self.keybindings.copy()
        result.host = self.host
        result.namespace = self.namespace

        return result

    def _cmp(self, other):
        """
        Comparator function for two `CIMInstanceName` objects.

        The comparison is based on the `host`, `namespace`, `classname`,
        and `keybindings`, instance attributes, in descending precedence.

        The `host` and `namespace` and `classname` attributes are compared
        case-insensitively.

        Raises `TypeError', if the `other` object is not a `CIMInstanceName`
        object.
        """
        if self is other:
            return 0
        if not isinstance(other, CIMInstanceName):
            raise TypeError("other must be CIMInstanceName, but is: %s" %\
                            type(other))
        return (cmpname(self.host, other.host) or
                cmpname(self.namespace, other.namespace) or
                cmpname(self.classname, other.classname) or
                cmpitem(self.keybindings, other.keybindings))

    def __str__(self):
        """ Return string representation of CIMClassname in
            readable format
        """

        ret_str = ''

        if self.host is not None:
            ret_str += '//%s/' % self.host

        if self.namespace is not None:
            ret_str += '%s:' % self.namespace

        ret_str += '%s.' % self.classname

        for key, value in self.keybindings.items():

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
        """ return string of CIMClassName in name=value form"""

        rep = '%s(classname=%r, keybindings=%r' % \
            (self.__class__.__name__, self.classname, self.keybindings)

        if self.host is not None:
            rep += ', host=%r' % self.host

        if self.namespace is not None:
            rep += ', namespace=%r' % self.namespace

        rep += ')'

        return rep

    # A whole bunch of dictionary methods that map to the equivalent
    # operation on self.keybindings.

    def __getitem__(self, key):
        return self.keybindings[key]

    def __contains__(self, key):
        return key in self.keybindings

    def __delitem__(self, key):
        del self.keybindings[key]

    def __setitem__(self, key, value):
        self.keybindings[key] = value

    def __len__(self):
        """Return number of keybindings"""
        return len(self.keybindings)

    def has_key(self, key):
        """Return boolean. True if `key` is in keybindings"""
        return key in self.keybindings

    def keys(self):
        """Return list of keys in keybindings"""
        return self.keybindings.keys()

    def values(self):
        """Return keybinding values"""
        return self.keybindings.values()

    def items(self):
        return self.keybindings.items()

    def iterkeys(self):
        return self.keybindings.iterkeys()

    def itervalues(self):
        return self.keybindings.itervalues()

    def iteritems(self):
        return self.keybindings.iteritems()

    def update(self, *args, **kwargs):
        self.keybindings.update(*args, **kwargs)

    def get(self, key, default=None):
        """
        Get the value of a specific key property, or the specified
        default value if a key binding with that name does not exist.
        """
        return self.keybindings.get(key, default)

    # pylint: disable=too-many-branches
    def tocimxml(self):
        """Generate a CIM-XML representation of the instance name (class name
        and key bindings)."""

        if isinstance(self.keybindings, str):

            # This cannot happen; self.keybindings is always a NocaseDict:
            raise TypeError("Unexpected: keybindings has string type: %s" % \
                            repr(self.keybindings))

            # TODO: Remove this old code after verifying that it works.
            # #Class with single key string property
            # instancename_xml = cim_xml.INSTANCENAME(
            #     self.classname,
            #     cim_xml.KEYVALUE(self.keybindings, 'string'))

        # Note: The CIM types are derived from the built-in types,
        # so we cannot use isinstance() for this test.
        # pylint: disable=unidiomatic-typecheck
        elif builtin_type(self.keybindings) in six.integer_types + (float,):

            # This cannot happen; self.keybindings is always a NocaseDict:
            raise TypeError("Unexpected: keybindings has numeric type: %s" % \
                            repr(self.keybindings))

            # TODO: Remove this old code after verifying that it works.
            # # Class with single key numeric property
            # instancename_xml = cim_xml.INSTANCENAME(
            #     self.classname,
            #     cim_xml.KEYVALUE(str(self.keybindings), 'numeric'))

        elif isinstance(self.keybindings, NocaseDict):

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
                    # Numeric CIM types derive from int, long or float.
                    # Note: int is a subtype of bool, but bool is already
                    # tested further up.
                    type_ = 'numeric'
                    value = str(key_bind[1])
                elif isinstance(key_bind[1], six.string_types):
                    type_ = 'string'
                    value = _ensure_unicode(key_bind[1])
                else:
                    raise TypeError('Invalid keybinding type for keybinding '\
                            '%s: %s' % (key_bind[0], builtin_type(key_bind[1])))

                kbs.append(cim_xml.KEYBINDING(
                    key_bind[0],
                    cim_xml.KEYVALUE(value, type_)))

            instancename_xml = cim_xml.INSTANCENAME(self.classname, kbs)

        else:

            # This cannot happen; self.keybindings is always a NocaseDict:
            raise TypeError("Unexpected: keybindings has type: %s" % \
                            repr(self.keybindings))

            # TODO: Remove this old code after verifying that it works.
            # # Value reference
            # instancename_xml = cim_xml.INSTANCENAME(
            #     self.classname,
            #     cim_xml.VALUE_REFERENCE(self.keybindings.tocimxml()))

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

class CIMInstance(_CIMComparisonMixin):
    """
    A CIM instance, optionally including its instance path.

    This object can be used like a dictionary to retrieve the property values.

    :Ivariables:

      ...
        All parameters of `__init__` are set as instance variables.
    """

    # pylint: disable=too-many-arguments
    def __init__(self, classname, properties={}, qualifiers={},
                 path=None, property_list=None):
        """
        Initialize the `CIMInstance` object.

        :Parameters:

          classname : Unicode string or UTF-8 encoded byte string
            Name of the creation class of the instance.

          properties : `dict` or `NocaseDict`
            Optional: Dictionary of properties, specifying property values of
            the instance.
            The dictionary must contain one item for each property, where:

            - its key is the property name.
            - its value is a `CIMProperty` object representing the property
              value.

          qualifiers : `dict` or `NocaseDict`
            Optional: Dictionary of qualifier values of the instance.
            Note that CIM-XML has deprecated the presence of qualifier values
            on CIM instances.

          path : `CIMInstanceName`
            Optional: Instance path of the instance.

            If `None`, the instance is not addressable or the instance path is
            unknown or not needed.

            Default: `None`.

          property_list : list of Unicode strings or UTF-8 encoded byte strings
            Optional: List of property names for use by some operations on this
            object.

        :Raises:
          :raise TypeError:
          :raise ValueError:
        """

        self.classname = _ensure_unicode(classname)
        self.qualifiers = NocaseDict(qualifiers)
        # TODO: Add support for accepting qualifiers as plain dict
        self.path = path
        if property_list is not None:
            self.property_list = [_ensure_unicode(x).lower() \
                for x in property_list]
        else:
            self.property_list = None

        # Assign initialised property values and run through
        # __setitem__ to enforce CIM types for each property.

        self.properties = NocaseDict()
        for key, value in properties.items():
            self.__setitem__(key, value)

    def update(self, *args, **kwargs):
        """D.update(E, **F) -> None.

        Update D from E and F: for k in E: D[k] = E[k]
        (if E has keys else: for (k, v) in E: D[k] = v)
        then: for k in F: D[k] = F[k] """

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
        """Update property values iff the property previously exists.

        Update D from E and F: for k in E: D[k] = E[k]
        (if E has keys else: for (k, v) in E: D[k] = v)
        then: for k in F: D[k] = F[k]

        Like update, but properties that are not already present in the
        instance are skipped. """

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

    def copy(self):
        """ Return copy of the CIMInstance object"""

        result = CIMInstance(self.classname)
        result.properties = self.properties.copy()
        result.qualifiers = self.qualifiers.copy()
        result.path = (self.path is not None and \
                       [self.path.copy()] or [None])[0]

        return result

    def _cmp(self, other):
        """
        Comparator function for two `CIMInstance` objects.

        The comparison is based on the `classname`, `path`, `properties`,
        and `qualifiers` instance attributes, in descending precedence.

        The `classname` attribute is compared case-insensitively.

        Raises `TypeError', if the `other` object is not a `CIMInstance`
        object.
        """
        if self is other:
            return 0
        if not isinstance(other, CIMInstance):
            raise TypeError("other must be CIMInstance, but is: %s" %\
                            type(other))
        return (cmpname(self.classname, other.classname) or
                cmpitem(self.path, other.path) or
                cmpitem(self.properties, other.properties) or
                cmpitem(self.qualifiers, other.qualifiers))

    def __repr__(self):
        """
            Return string for CIMInstance in name=value form. Note
            that it does not
            show all the properties and qualifiers because they're
            just too big.
        """

        return '%s(classname=%r, path=%r, ...)' % \
            (self.__class__.__name__, self.classname, self.path)

    # A whole bunch of dictionary methods that map to the equivalent
    # operation on self.properties.

    def __contains__(self, key):
        """Test if argument key is one of the properteis"""
        return key in self.properties

    def __getitem__(self, key):
        """Return the property with key"""
        return self.properties[key].value

    def __delitem__(self, key):
        del self.properties[key]

    def __len__(self):
        """ Return number of properties"""

        return len(self.properties)

    def has_key(self, key):
        """ Return boolean True if there is a key property"""

        return key in self.properties

    def keys(self):
        """return keys for properties in instance"""
        return self.properties.keys()

    def values(self):
        return [v.value for v in self.properties.values()]

    def items(self):
        """ return key and value for property.items"""
        return [(key, v.value) for key, v in self.properties.items()]

    def iterkeys(self):
        return self.properties.iterkeys()

    def itervalues(self):
        """ Iterate through properties returning value"""
        for _, val in self.properties.iteritems():
            yield val.value

    def iteritems(self):
        """ Iterate through properties returing key, value tuples"""
        for key, val in self.properties.iteritems():
            yield (key, val.value)

    def __setitem__(self, key, value):

        # Don't let anyone set integer or float values.  You must use
        # a subclass from the cim_type module.

        # Note: The CIM types are derived from the built-in types,
        # so we cannot use isinstance() for this test.
        # pylint: disable=unidiomatic-typecheck
        if builtin_type(value) in six.integer_types + (float,):
            raise TypeError(
                "Type of numeric value for a property must be a CIM type, "\
                "but is %s" % builtin_type(value))

        if self.property_list is not None and key.lower() not in \
                self.property_list:
            if self.path is not None and key not in self.path.keybindings:
                return
        # Convert value to appropriate PyWBEM type

        if isinstance(value, CIMProperty):
            val = value
        else:
            val = CIMProperty(key, value)

        self.properties[key] = val
        if self.path is not None and key in self.path.keybindings:
            self.path[key] = val.value

    def get(self, key, default=None):
        """
        Get the value of a specific property, or the specified default
        value if a property with that name does not exist.
        """
        prop = self.properties.get(key, None)
        return default if prop is None else prop.value

    def tocimxml(self):
        """ Return string with CIM/XML representing this CIMInstance.
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

    def tomof(self, indent=DEFAULT_INDENT):
        """ Return string representing the MOF definition of this
            CIMInstance.
        """
        def _prop2mof(type_, value, indent_lvl=DEFAULT_INDENT):
            """ Return a string representing the MOF definition of
                a single property defined by the type and value
                arguments.
                :param type_:  CIMType of the property
                :param value: value corresponsing to this type
            """
            if value is None:
                val = 'NULL'
            elif isinstance(value, list):
                val = '{'
                for i, item in enumerate(value):
                    if i > 0:
                        val += ', '
                    val += _prop2mof(type_, item, indent_lvl=indent_lvl)
                val += '}'
            elif type_ == 'string':
                val = mofstr(value, indent=indent_lvl)
            else:
                val = str(value)
            return val

        # Create temp indent remove one level
        indent_str = ' '.ljust(indent, ' ')
        out_indent = indent_str[:(indent - DEFAULT_INDENT)]

        ret_str = out_indent + 'instance of %s {\n' % self.classname
        for prop in self.properties.values():
            if prop.embedded_object is not None:
                # convert the instance in this property
                ret_str += prop.value.tomof(indent=(indent + DEFAULT_INDENT))
            else:
                # output this property indented to return string
                ret_str += '%s%s = %s;\n' % (indent_str, prop.name,
                                             _prop2mof(prop.type,
                                                       prop.value,
                                                       indent_lvl=indent))
        ret_str += (out_indent + '};\n')
        return ret_str


class CIMClass(_CIMComparisonMixin):
    """
    Create an instance of CIMClass, a CIM class with classname,
    properties, methods, qualifiers, and superclass name.

    :Ivariables:

      ...
        All parameters of `__init__` are set as instance variables.
    """

    # pylint: disable=too-many-arguments
    def __init__(self, classname, properties={}, methods={},
                 superclass=None, qualifiers={}):
        """
        Initialize the `CIMClass` object.

        Initialize instance variables containing the arguments provided
        for the CIMClass including classname, properties, class
        qualifiers, methods, and the superclass
        """
        self.classname = _ensure_unicode(classname)
        self.properties = NocaseDict(properties)
        self.qualifiers = NocaseDict(qualifiers)
        self.methods = NocaseDict(methods)
        self.superclass = _ensure_unicode(superclass)

    def copy(self):
        """ Return a copy of the CIMClass object"""
        result = CIMClass(self.classname)
        result.properties = self.properties.copy()
        result.methods = self.methods.copy()
        result.superclass = self.superclass
        result.qualifiers = self.qualifiers.copy()

        return result

    def __repr__(self):
        """ Return string containing the CIMClass data in
            name=value form"""

        return "%s(classname=%r, ...)" % (self.__class__.__name__,
                                          self.classname)

    def _cmp(self, other):
        """
        Comparator function for two `CIMClass` objects.

        The comparison is based on the `classname`, `superclass`, `qualifiers`,
        `properties` and `methods` instance attributes, in descending
        precedence.

        The `classname` and `superclass` attributes are compared
        case-insensitively.

        Raises `TypeError', if the `other` object is not a `CIMClass`
        object.
        """
        if self is other:
            return 0
        if not isinstance(other, CIMClass):
            raise TypeError("other must be CIMClass, but is: %s" %\
                            type(other))
        return (cmpname(self.classname, other.classname) or
                cmpname(self.superclass, other.superclass) or
                cmpitem(self.qualifiers, other.qualifiers) or
                cmpitem(self.properties, other.properties) or
                cmpitem(self.methods, other.methods))

    def tocimxml(self):
        """ Return string with CIM/XML representation of the CIMClass"""

        return cim_xml.CLASS(
            self.classname,
            properties=[p.tocimxml() for p in self.properties.values()],
            methods=[m.tocimxml() for m in self.methods.values()],
            qualifiers=[q.tocimxml() for q in self.qualifiers.values()],
            superclass=self.superclass)

    def tomof(self):
        """ Return string with MOF representation of the CIMClass"""

        # Class definition

        ret_str = '   %s\n' % _makequalifiers(self.qualifiers, 4)

        ret_str += 'class %s ' % self.classname

        # Superclass

        if self.superclass is not None:
            ret_str += ': %s ' % self.superclass

        ret_str += '{\n'

        # Properties

        for prop_val in self.properties.values():
            if prop_val.is_array and prop_val.array_size is not None:
                array_str = "[%s]" % prop_val.array_size
            else:
                array_str = ''
            ret_str += '\n'
            ret_str += '      %s\n' % (_makequalifiers(prop_val.qualifiers, 7))
            ret_str += '   %s %s%s;\n' % (moftype(prop_val.type,
                                                  prop_val.reference_class),
                                          prop_val.name, array_str)

        # Methods

        for method in self.methods.values():
            ret_str += '\n'
            ret_str += '   %s\n' % method.tomof()

        ret_str += '};\n'

        return ret_str

class CIMMethod(_CIMComparisonMixin):
    """
    A CIM method.

    :Ivariables:

      ...
        All parameters of `__init__` are set as instance variables.
    """

    # pylint: disable=too-many-arguments
    def __init__(self, methodname, return_type=None, parameters={},
                 class_origin=None, propagated=False, qualifiers={}):
        """
        Initialize the `CIMMethod` object.

        TODO: add description
        """
        self.name = _ensure_unicode(methodname)
        self.return_type = _ensure_unicode(return_type)
        self.parameters = NocaseDict(parameters)
        self.class_origin = _ensure_unicode(class_origin)
        self.propagated = _ensure_unicode(propagated)
        self.qualifiers = NocaseDict(qualifiers)

    def copy(self):
        """ Return copy of the CIMMethod object"""

        result = CIMMethod(self.name,
                           return_type=self.return_type,
                           class_origin=self.class_origin,
                           propagated=self.propagated)

        result.parameters = self.parameters.copy()
        result.qualifiers = self.qualifiers.copy()

        return result

    def tocimxml(self):
        """ Return string containing CIM/XML representation of CIMMethod
            object
        """

        return cim_xml.METHOD(
            self.name,
            parameters=[p.tocimxml() for p in self.parameters.values()],
            return_type=self.return_type,
            class_origin=self.class_origin,
            propagated=self.propagated,
            qualifiers=[q.tocimxml() for q in self.qualifiers.values()])

    def __repr__(self):
        return '%s(name=%r, return_type=%r, ...)' % \
               (self.__class__.__name__, self.name, self.return_type)

    def _cmp(self, other):
        """
        Comparator function for two `CIMMethod` objects.

        The comparison is based on the `name`, `qualifiers`, `parameters`,
        `return_type`, `class_origin` and `propagated` instance attributes,
        in descending precedence.

        The `name` attribute is compared case-insensitively.

        Raises `TypeError', if the `other` object is not a `CIMMethod`
        object.
        """
        if self is other:
            return 0
        if not isinstance(other, CIMMethod):
            raise TypeError("other must be CIMMethod, but is: %s" %\
                            type(other))
        return (cmpname(self.name, other.name) or
                cmpitem(self.qualifiers, other.qualifiers) or
                cmpitem(self.parameters, other.parameters) or
                cmpitem(self.return_type, other.return_type) or
                cmpitem(self.class_origin, other.class_origin) or
                cmpitem(self.propagated, other.propagated))

    def tomof(self):
        """ Return string MOF representation of the CIMMethod object"""
        ret_str = ''

        ret_str += '      %s\n' % (_makequalifiers(self.qualifiers, 7))

        if self.return_type is not None:
            ret_str += '%s ' % moftype(self.return_type, None)
            # CIM-XML does not support methods returning reference types
            # (the CIM architecture does).

        ret_str += '%s(\n' % (self.name)
        ret_str += ',\n'.join(
            ['       '+p.tomof() for p in self.parameters.values()])
        ret_str += ');\n'

        return ret_str

class CIMParameter(_CIMComparisonMixin):
    """
    A CIM parameter.

    :Ivariables:

      ...
        All parameters of `__init__` are set as instance variables.
    """
     # pylint: disable=too-many-arguments
    def __init__(self, name, type, reference_class=None, is_array=None,
                 array_size=None, qualifiers={}, value=None):
        # pylint: disable=redefined-builtin
        """
        Initialize the `CIMParameter` object.

        TODO: add description
        """

        type_ = type  # Minimize usage of the builtin 'type'

        self.name = _ensure_unicode(name)
        self.type = _ensure_unicode(type_)
        self.reference_class = _ensure_unicode(reference_class)
        self.is_array = is_array
        self.array_size = array_size
        self.qualifiers = NocaseDict(qualifiers)
        self.value = _ensure_unicode(value)

    def copy(self):
        """ return copy of the CIMParameter object"""
        result = CIMParameter(self.name,
                              self.type,
                              reference_class=self.reference_class,
                              is_array=self.is_array,
                              array_size=self.array_size,
                              value=self.value)

        result.qualifiers = self.qualifiers.copy()

        return result

    def __repr__(self):

        return '%s(name=%r, type=%r, reference_class=%r, is_array=%r, ...)' % \
               (self.__class__.__name__, self.name, self.type,
                self.reference_class, self.is_array)

    def _cmp(self, other):
        """
        Comparator function for two `CIMParameter` objects.

        The comparison is based on the `name`, `type`, `reference_class`,
        `is_array`, `array_size`, `qualifiers` and `value` instance attributes,
        in descending precedence.

        The `name` attribute is compared case-insensitively.

        Raises `TypeError', if the `other` object is not a `CIMParameter`
        object.
        """
        if self is other:
            return 0
        if not isinstance(other, CIMParameter):
            raise TypeError("other must be CIMParameter, but is: %s" %\
                            type(other))
        return (cmpname(self.name, other.name) or
                cmpitem(self.type, other.type) or
                cmpname(self.reference_class, other.reference_class) or
                cmpitem(self.is_array, other.is_array) or
                cmpitem(self.array_size, other.array_size) or
                cmpitem(self.qualifiers, other.qualifiers) or
                cmpitem(self.value, other.value))

    def tocimxml(self):
        """ Return String containing CIM/XML representation of
            the CIMParameter
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

    def tomof(self):
        """ Return string with MOF representation of CIMParameter"""
        if self.is_array and self.array_size is not None:
            array_str = "[%s]" % self.array_size
        else:
            array_str = ''
        rtn_str = '\n'
        rtn_str += '         %s\n' % (_makequalifiers(self.qualifiers, 10))
        rtn_str += '      %s %s%s' % (moftype(self.type, self.reference_class),
                                      self.name, array_str)
        return rtn_str

# pylint: disable=too-many-instance-attributes
class CIMQualifier(_CIMComparisonMixin):
    """
    A CIM qualifier value.

    A qualifier represents metadata on a class, method, property, etc., and
    specifies information such as a documentation string or whether a property
    is a key.

    :Ivariables:

      ...
        All parameters of `__init__` are set as instance variables.
    """
    #pylint: disable=too-many-arguments
    def __init__(self, name, value, type=None, propagated=None,
                 overridable=None, tosubclass=None, toinstance=None,
                 translatable=None):
        # pylint: disable=redefined-builtin
        """
        Initialize the `CIMQualifier` object.

        TODO: add description
        """

        type_ = type  # Minimize usage of the builtin 'type'

        self.name = _ensure_unicode(name)
        self.type = _ensure_unicode(type_)
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

                if len(value) == 0:
                    raise TypeError(
                        'Empty qualifier array "%s" must have a type' % name)

                self.type = cimtype(value[0])

            else:

                # Determine type for regular value

                self.type = cimtype(value)

        # Don't let anyone set integer or float values.  You must use
        # a subclass from the cim_type module.

        # Note: The CIM types are derived from the built-in types,
        # so we cannot use isinstance() for this test.
        # pylint: disable=unidiomatic-typecheck
        if builtin_type(value) in six.integer_types + (float,):
            raise TypeError(
                "Type of numeric value for a qualifier must be a CIM type, "\
                "but is %s" % builtin_type(value))

        self.value = value

    def copy(self):
        """ Return copy of CIMQualifier object"""

        return CIMQualifier(self.name,
                            self.value,
                            type=self.type,
                            propagated=self.propagated,
                            overridable=self.overridable,
                            tosubclass=self.tosubclass,
                            toinstance=self.toinstance,
                            translatable=self.translatable)

    def __repr__(self):
        return "%s(name=%r, value=%r, type=%r, ...)" % \
               (self.__class__.__name__, self.name, self.value, self.type)

    def _cmp(self, other):
        """
        Comparator function for two `CIMQualifier` objects.

        The comparison is based on the `name`, `type`, `value`, `propagated`,
        `overridable`, `tosubclass`, `toinstance`, `translatable` instance
        attributes, in descending precedence.

        The `name` attribute is compared case-insensitively.

        Raises `TypeError', if the `other` object is not a `CIMQualifier`
        object.
        """
        if self is other:
            return 0
        if not isinstance(other, CIMQualifier):
            raise TypeError("other must be CIMQualifier, but is: %s" %\
                            type(other))
        return (cmpname(self.name, other.name) or
                cmpitem(self.type, other.type) or
                cmpitem(self.value, other.value) or
                cmpitem(self.propagated, other.propagated) or
                cmpitem(self.overridable, other.overridable) or
                cmpitem(self.tosubclass, other.tosubclass) or
                cmpitem(self.toinstance, other.toinstance) or
                cmpitem(self.translatable, other.translatable))

    def tocimxml(self):
        """ Return CIM/XML string representing CIMQualifier"""
        value = None

        if isinstance(self.value, list):
            value = cim_xml.VALUE_ARRAY([cim_xml.VALUE(v) for v in self.value])
        elif self.value is not None:
            # pylint: disable=redefined-variable-type
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

    def tomof(self, indent=7):
        """ Return string representing CIMQualifier in MOF format"""

        def valstr(value):
            """ Return string representing value argument."""
            if isinstance(value, six.string_types):
                return mofstr(value, indent)
            return str(value)

        if isinstance(self.value, list):
            return '%s {' % self.name + \
                   ', '.join([valstr(val) for val in self.value]) + '}'

        return '%s (%s)' % (self.name, valstr(self.value))

#pylint: disable=too-many-instance-attributes
class CIMQualifierDeclaration(_CIMComparisonMixin):
    """
    A CIM qualifier type.

    A qualifier type is the declaration of a qualifier.

    :Ivariables:

      ...
        All parameters of `__init__` are set as instance variables.
    """

    # TODO: Scope and qualifier flavors

    # pylint: disable=too-many-arguments
    def __init__(self, name, type, value=None, is_array=False,
                 array_size=None, scopes={},
                 overridable=None, tosubclass=None, toinstance=None,
                 translatable=None):
        # pylint: disable=redefined-builtin
        """
        Initialize the `CIMQualifierDeclaration` object.

        TODO: add description
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

    def copy(self):
        """ Copy the CIMQualifierDeclaration"""

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

    def __repr__(self):
        """ Return String of CIMQualifierDeclaration in form name=value"""

        return "%s(name=%r, type=%r, is_array=%r, ...)" % \
            (self.__class__.__name__, self.name, self.type, self.is_array)

    def _cmp(self, other):
        """
        Comparator function for two `CIMQualifierDeclaration` objects.

        The comparison is based on the `name`, `type`, `value`, `is_array`,
        `array_size`, `scopes`, `overridable`, `tosubclass`, `toinstance`,
        `translatable` instance attributes, in descending precedence.

        The `name` attribute is compared case-insensitively.

        Raises `TypeError', if the `other` object is not a
        `CIMQualifierDeclaration` object.
        """
        if self is other:
            return 0
        if not isinstance(other, CIMQualifierDeclaration):
            raise TypeError("other must be CIMQualifierDeclaration, "\
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

    def tocimxml(self):
        """
        Return string with CIM/XML representation of CIMQualifierDeclaration
        based on DMTF DSP0200 representation
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

    def tomof(self):
        """ Return MOF representation of CIMQualifierDeclaration"""

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
        mof += ',\n    '
        mof += 'Scope('
        mof += ', '.join([x.lower() for x, y in self.scopes.items() if y]) + ')'
        if not self.overridable and not self.tosubclass \
                and not self.toinstance and not self.translatable:
            mof += ';'
            return mof
        mof += ',\n    Flavor('
        mof += self.overridable and 'EnableOverride' or 'DisableOverride'
        mof += ', '
        mof += self.tosubclass and 'ToSubclass' or 'Restricted'
        if self.toinstance:
            mof += ', ToInstance'
        if self.translatable:
            mof += ', Translatable'
        mof += ');'
        return mof

def tocimxml(value):
    """Convert an arbitrary object to CIM xml.  Works with cim_obj
    objects and builtin types."""

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
        if value:
            return cim_xml.VALUE('TRUE')
        else:
            return cim_xml.VALUE('FALSE')

    # List of values

    if isinstance(value, list):
        return cim_xml.VALUE_ARRAY(list(map(tocimxml, value)))

    raise ValueError("Can't convert %s (%s) to CIM XML" % \
                     (value, builtin_type(value)))

#pylint: disable=too-many-locals,too-many-return-statements,too-many-branches
def tocimobj(type_, value):
    """Convert a CIM type and a string value into an appropriate
       CIM builtin type.
       :return: value converted from value argument using type
       argument.
       :exception: ValueError if type and value string do not match
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
        return value

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
        raise ValueError('CIMType char16 not handled')

    # Datetime

    if type_ == 'datetime':
        return CIMDateTime(value)

    # REF
    def partition(str_arg, seq):
        """ partition(str_arg, sep) -> (head, sep, tail)

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
            return (str_arg[:idx], seq, str_arg[idx+len(seq):])

    if type_ == 'reference': # pylint: disable=too-many-nested-blocks
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
                if head.count('"') == 1: # quoted string contains comma
                    tmp, sep, tail = partition(tail, '"')
                    head = '%s,%s' % (head, tmp)
                    tail = partition(tail, ',')[2]
                head = head.strip()
                key, sep, val = partition(head, '=')
                if sep:
                    cl_name, s, k = partition(key, '.')
                    if s:
                        if cl_name != classname:
                            raise ValueError('Invalid object path: "%s"' % \
                                             value)
                        key = k
                    val = val.strip()
                    if val[0] == '"' and val[-1] == '"':
                        val = val.strip('"')
                    else:
                        if val.lower() in ('true', 'false'):
                            val = val.lower() == 'true'
                        elif val.isdigit():
                            val = int(val)   # pylint: disable=R0204
                        else:
                            try:
                                val = float(val)
                            except ValueError:
                                try:
                                    val = CIMDateTime(val)
                                except ValueError:
                                    raise ValueError('Invalid key binding: %s'\
                                            % val)


                    key_bindings[key] = val
            return CIMInstanceName(classname, host=host, namespace=nm_space,
                                   keybindings=key_bindings)
        else:
            raise ValueError('Invalid reference value: "%s"' % value)

    raise ValueError('Invalid CIM type: "%s"' % type_)


def byname(nlist):
    """Convert a list of named objects into a map indexed by name"""
    return dict([(x.name, x) for x in nlist])
