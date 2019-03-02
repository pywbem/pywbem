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
#

"""
Class ``NocaseDict`` is a dictionary implementation with case-insensitive but
case-preserving keys, and with preservation of the order of its items.

It is used for lists of child objects of CIM objects (e.g. the list of CIM
properties in a CIM class, or the list of CIM parameters in a CIM method).

Users of pywbem will notice ``NocaseDict`` objects only as a result of pywbem
functions. Users cannot create ``NocaseDict`` objects.

Except for the case-insensitivity of its keys, it behaves like the built-in
:class:`~py:collections.OrderedDict`. Therefore, ``NocaseDict`` is not
described in detail in this documentation.

Deprecated: In pywbem 0.9, support for comparing two ``NocaseDict`` instances
with the ``>``, ``>``, ``<=``, ``>=`` operators has been deprecated.
"""

# This module is meant to be safe for 'import *'.

from __future__ import print_function, absolute_import

import sys
import warnings
import traceback
try:
    from collections import OrderedDict
except ImportError:
    from ordereddict import OrderedDict

import six

from ._utils import _stacklevel_above_module, _format
from .config import DEBUG_WARNING_ORIGIN

__all__ = []


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

        A UserWarning will be issued if the provided init parameters will
        cause the order of provided items not to be preserved when adding them
        to the new dictionary.
        """

        # The internal dictionary, with lower case keys. An item in this dict
        # is the tuple (original key, value).
        self._data = OrderedDict()

        # Flag indicating whether unnamed keys (a key of `None`) is allowed.
        # Can be set to allow unnamed keys.
        self.allow_unnamed_keys = False

        # In by far the most cases, NocaseDict objects are created without
        # any init parameters.

        # Step 1: Add a single positional argument
        if args:
            if len(args) > 1:
                raise TypeError(
                    _format("Too many positional arguments for NocaseDict "
                            "initialization: {0} (1 allowed)", len(args)))
            arg = args[0]
            if isinstance(arg, (list, tuple)):
                # Initialize from tuple/list of key/value pairs or CIM objects
                for item in arg:
                    try:
                        # CIM object
                        key = item.name
                        value = item
                    except AttributeError:
                        # key, value pair
                        key, value = item
                    self[key] = value
            elif isinstance(arg, (OrderedDict, NocaseDict)):
                # Initialize from OrderedDict/NocaseDict object
                self.update(arg)
            elif isinstance(arg, dict):
                # Initialize from dict object
                if len(arg) > 1:
                    warnings.warn(
                        _format("Initializing a pywbem.NocaseDict object "
                                "from {0} will not preserve order of items",
                                type(arg)),
                        UserWarning,
                        stacklevel=_stacklevel_above_module(__name__))
                self.update(arg)
            elif arg is None:
                # Leave empty
                pass
            else:
                raise TypeError(
                    _format("Invalid type for NocaseDict initialization: "
                            "{0} ({1})", arg.__class__.__name__, type(arg)))

        # Step 2: Add any keyword arguments
        if kwargs:
            if len(kwargs) > 1 and sys.version_info[0:2] < (3, 7):
                warnings.warn("Initializing a pywbem.NocaseDict object from "
                              "keyword arguments before Python 3.7 will not "
                              "preserve order of items",
                              UserWarning,
                              stacklevel=_stacklevel_above_module(__name__))
            self.update(kwargs)

    # Basic accessor and settor methods

    def _real_key(self, key):
        """
        Return the normalized key to be used for the internal dictionary,
        from the input key.
        """
        if key is not None:
            try:
                return key.lower()
            except AttributeError:
                raise TypeError(
                    _format("NocaseDict key {0!A} must be a string, "
                            "but is {1}", key, type(key)))

        if self.allow_unnamed_keys:
            return None

        raise TypeError(
            _format("NocaseDict key None (unnamed key) is not "
                    "allowed for this object"))

    def __getitem__(self, key):
        """
        Invoked when retrieving the value for a key, using `val = d[key]`.

        The key is looked up case-insensitively. Raises `KeyError` if the
        specified key does not exist. Note that __setitem__() ensures that
        only string typed keys will exist, so the key type is not tested here
        and specifying non-string typed keys will simply lead to a KeyError.
        """
        k = self._real_key(key)
        try:
            return self._data[k][1]
        except KeyError:
            raise KeyError(_format("Key {0!A} not found", key))

    def __setitem__(self, key, value):
        """
        Invoked when assigning a value for a key using `d[key] = val`.

        The key is looked up case-insensitively. If the key does not exist,
        it is added with the new value. Otherwise, its value is overwritten
        with the new value.

        Raises `TypeError` if the specified key does not have string type.
        """
        k = self._real_key(key)
        self._data[k] = (key, value)

    def __delitem__(self, key):
        """
        Invoked when deleting a key/value pair using `del d[key]`.

        The key is looked up case-insensitively. Raises `KeyError` if the
        specified key does not exist. Note that __setitem__() ensures that
        only string typed keys will exist, so the key type is not tested here
        and specifying non-string typed keys will simply lead to a KeyError.
        """
        k = self._real_key(key)
        try:
            del self._data[k]
        except KeyError:
            raise KeyError(_format("Key {0!A} not found", key))

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
        k = self._real_key(key)
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

        The lexical case of the keys in the result is the preserved lexical
        case.
        """
        items = [_format("{0!A}: {1!A}", key, value)
                 for key, value in self.iteritems()]
        items_str = ', '.join(items)
        return "{0.__class__.__name__}({{{1}}})".format(self, items_str)

    def update(self, *args, **kwargs):
        """
        Update the dictionary from key/value pairs. If an item for a key
        exists in the dictionary, its value is updated. If an item for a key
        does not exist, it is added to the dictionary at the end.
        The provided keys and values are stored in the dictionary without
        being copied.

        Each positional argument can be:

          * an object with a method `items()` that returns an
            :term:`py:iterable` of tuples containing key and value.

          * an object without such a method, that is an :term:`py:iterable` of
            tuples containing key and value.

        Each keyword argument is a key/value pair.

        The updates are performed first for the positional arguments in the
        iteration order of their iterables, and then for the keyword arguments.
        Note that before Python 3.4, keyword arguments are passed to this
        method as a standard dict, so the order of updates for the keyword
        arguments is not preserved.
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
        Return a copy of the dictionary.

        This is a middle-deep copy; the copy is independent of the original in
        all attributes that have mutable types except for:

        * The values in the dictionary

        Note that the Python functions :func:`py:copy.copy` and
        :func:`py:copy.deepcopy` can be used to create completely shallow or
        completely deep copies of objects of this class.
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
        # Issue #1062: Could compare hash values for better performance
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
        msg = _format("Ordering comparisons involving {0} objects are "
                      "deprecated.", self.__class__.__name__)
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
        fs = frozenset([(k, self._data[k][1]) for k in self._data])
        return hash(fs)
