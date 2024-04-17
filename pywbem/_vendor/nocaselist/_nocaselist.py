"""
This module provides class NocaseList.
"""

from __future__ import print_function, absolute_import

import sys
import os

__all__ = ['NocaseList']

if sys.version_info[0] == 2:
    # pylint: disable=undefined-variable
    _INTEGER_TYPES = (long, int)  # noqa: F821
else:
    _INTEGER_TYPES = (int,)

# This env var is set when building the docs. It causes the methods
# that are supposed to exist only in a particular Python version, not to be
# removed, so they appear in the docs.
BUILDING_DOCS = os.environ.get('BUILDING_DOCS', False)


class NocaseList(list):
    # pylint: disable=line-too-long
    """
    A case-insensitive and case-preserving list.

    The list is case-insensitive: Whenever items of the list are looked up by
    value or item values are compared, that is done case-insensitively. The
    case-insensitivity is defined by performing the lookup or comparison on the
    result of the :meth:`__casefold__` method on the on list items.
    `None` is allowed as a list value and will not be case folded.

    The list is case-preserving: Whenever the value of list items is returned,
    they have the lexical case that was originally specified when adding
    or updating the item.

    Except for the case-insensitivity of its items, it behaves like, and is
    in fact derived from, the built-in :class:`py:list` class in order to
    facilitate type checks.

    The implementation maintains a second list with the casefolded items of
    the inherited list, and ensures that both lists are in sync.

    The list supports serialization via the Python :mod:`py:pickle` module.
    To save space and time, only the originally cased list is serialized.
    """  # noqa E401
    # pylint: enable=line-too-long

    # Methods not implemented:
    #
    # * __getattribute__(self, name): The method inherited from object is used;
    #   no reason to have a different implementation.
    #
    # * __sizeof__(self): The method inherited from list is used; no reason
    #   to have a different implementation.
    #
    # __repr__(): The method inherited from list is used; no reason
    #   to have a different implementation.
    #
    # __getitem__(): The method inherited from list is used; no reason
    #   to have a different implementation.
    #
    # __iter__(): The method inherited from list is used; no reason
    #   to have a different implementation.

    def __init__(self, iterable=()):
        """
        Initialize the list with the items in the specified iterable.
        """
        super(NocaseList, self).__init__(iterable)

        # The _casefolded_list attribute is a list with the same items as the
        # original (inherited) list, except they are casefolded using the
        # __casefold__() method.

        # The following is an optimization based on the assumption that in
        # many cases, casefolding the input list is more expensive than
        # copying it (plus the overhead to check that).
        if isinstance(iterable, NocaseList):
            try:
                # pylint: disable=protected-access
                self._casefolded_list = iterable._casefolded_list.copy()
            except AttributeError:  # No copy() on Python 2
                self._casefolded_list = self._new_casefolded_list(self)
        else:
            self._casefolded_list = self._new_casefolded_list(self)

    def _new_casefolded_list(self, lst):
        """
        Return a casefolded list from the input list.
        """
        result = []
        for value in lst:
            result.append(self._casefolded_value(value))
        return result

    def _casefolded_value(self, value):
        """
        This method returns the casefolded value and handles the case of value
        being `None`.
        """
        if value is None:
            return None
        return self.__casefold__(value)

    @staticmethod
    def __casefold__(value):
        """
        This method implements the case-insensitive behavior of the class.

        It returns a case-insensitive form of the input value by calling a
        "casefold method" on the value. The input value will not be `None`.

        The casefold method called by this method is :meth:`py2:str.lower` on
        Python 2, and on Python 3 it is :meth:`py:str.casefold`, falling back
        to :meth:`py:bytes.lower` if it does not exist.

        This method can be overridden by users in order to change the
        case-insensitive behavior of the class.
        See :ref:`Overriding the default casefold method` for details.

        Parameters:
          value (str or unicode or bytes): Input value. Will not be `None`.

        Returns:
          str or unicode or bytes: Case-insensitive form of the input value.

        Raises:
          AttributeError: The value does not have the casefold method.
        """
        try:
            return value.casefold()
        except AttributeError:
            # Either Python 2, or Python 3 and a byte string key
            return value.lower()

    def __getstate__(self):
        """
        Called when pickling the object, see :meth:`py:object.__getstate__`.

        In order to save space and time, only the list with the originally
        cased items is saved, but not the second list with the casefolded
        items.

        On Python 2, the 'pickle' module does not call :meth:`__setstate__`,
        so this optimzation has only be implemented for Python 3.
        """
        # This copies the state of the inherited list even though it is
        # not visible in self.__dict__.
        state = self.__dict__.copy()
        del state['_casefolded_list']
        return state

    def __setstate__(self, state):
        """
        Called when unpickling the object, see :meth:`py:object.__setstate__`.

        On Python 2, the 'pickle' module does not call this method, so this
        optimzation has only be implemented for Python 3.
        """
        self.__dict__.update(state)
        self._casefolded_list = self._new_casefolded_list(self)

    def __setitem__(self, index, value):
        """
        Update the value of the item at an existing index in the list.

        Invoked using ``ncl[index] = value``.

        Raises:
          AttributeError: The value does not have the casefold method.
        """
        super(NocaseList, self).__setitem__(index, value)
        self._casefolded_list[index] = self._casefolded_value(value)

    def __delitem__(self, index):
        """
        Delete an item at an existing index from the list.

        Invoked using ``del ncl[index]``.
        """
        super(NocaseList, self).__delitem__(index)
        del self._casefolded_list[index]

    def __contains__(self, value):
        """
        Return a boolean indicating whether the list contains at least one
        item with the value, by looking it up case-insensitively.

        Invoked using ``value in ncl``.

        Raises:
          AttributeError: The value does not have the casefold method.
        """
        return self._casefolded_value(value) in self._casefolded_list

    def __add__(self, other):
        """
        Return a new :class:`NocaseList` object that contains the items from
        the left hand operand (``self``) and the items from the right hand
        operand (``other``).

        The right hand operand (``other``) must be an instance of
        :class:`py:list` (including :class:`NocaseList`) or :class:`py:tuple`.
        The operands are not changed.

        Invoked using e.g. ``ncl + other``

        Raises:
          TypeError: The other iterable is not a list or tuple
        """
        if not isinstance(other, (list, tuple)):
            raise TypeError(
                "Can only concatenate list or tuple (not {t}) to NocaseList".
                format(t=type(other)))
        lst = self.copy()
        lst.extend(other)
        return lst

    def __iadd__(self, other):
        """
        Extend the left hand operand (``self``) by the items from the right
        hand operand (``other``).

        The ``other`` parameter must be an iterable but is otherwise not
        restricted in type. Thus, if it is a string, the characters of the
        string are added as distinct items to the list.

        Invoked using ``ncl += other``.
        """
        # Note: It is unusual that the method has to return self, but it was
        # verified that this is necessary.
        self.extend(other)
        return self

    def __mul__(self, number):
        """
        Return a new :class:`NocaseList` object that contains the items from
        the left hand operand (``self``) as many times as specified by the right
        hand operand (``number``).

        A number <= 0 causes the returned list to be empty.

        The left hand operand (``self``) is not changed.

        Invoked using ``ncl * number``.
        """
        if not isinstance(number, _INTEGER_TYPES):
            raise TypeError(
                "Cannot multiply NocaseList by non-integer of type {t}".
                format(t=type(number)))
        lst = NocaseList()
        for _ in range(0, number):
            lst.extend(self)
        return lst

    def __rmul__(self, number):
        """
        Return a new :class:`NocaseList` object that contains the items from
        the right hand operand (``self``) as many times as specified by the left
        hand operand (``number``).

        A number <= 0 causes the returned list to be empty.

        The right hand operand (``self``) is not changed.

        Invoked using ``number * ncl``.
        """
        lst = self * number  # Delegates to __mul__()
        return lst

    def __imul__(self, number):
        """
        Change the left hand operand (``self``) so that it contains the items
        from the original left hand operand (``self``) as many times as
        specified by the right hand operand (``number``).

        A number <= 0 will empty the left hand operand.

        Invoked using ``ncl *= number``.
        """
        # Note: It is unusual that the method has to return self, but it was
        # verified that this is necessary.
        if not isinstance(number, _INTEGER_TYPES):
            raise TypeError(
                "Cannot multiply NocaseList by non-integer of type {t}".
                format(t=type(number)))
        if number <= 0:
            del self[:]
            del self._casefolded_list[:]
        else:
            self_items = list(self)
            for _ in range(0, number - 1):
                self.extend(self_items)
        return self

    def __reversed__(self):
        """
        Return a shallow copy of the list that has its items reversed in order.

        Invoked using ``reversed(ncl)``.
        """
        lst = self.copy()
        lst.reverse()
        return lst

    def __eq__(self, other):
        """
        Return a boolean indicating whether the list and the other list are
        equal, by comparing corresponding list items case-insensitively.

        The other list may be a :class:`NocaseList` object or any other
        iterable. In all cases, the comparison takes place case-insensitively.

        Invoked using e.g. ``ncl == other``.

        Raises:
          AttributeError: A value in the other list does not have the casefold
            method.
        """
        if isinstance(other, NocaseList):
            other = other._casefolded_list  # pylint: disable=protected-access
        else:
            other = self._new_casefolded_list(other)
        return self._casefolded_list == other

    def __ne__(self, other):
        """
        Return a boolean indicating whether the list and the other list are
        not equal, by comparing corresponding list items case-insensitively.

        The other list may be a :class:`NocaseList` object or any other
        iterable. In all cases, the comparison takes place case-insensitively.

        Invoked using e.g. ``ncl != other``.

        Raises:
          AttributeError: A value in the other list does not have the casefold
            method.
        """
        if isinstance(other, NocaseList):
            other = other._casefolded_list  # pylint: disable=protected-access
        else:
            other = self._new_casefolded_list(other)
        return self._casefolded_list != other

    def __gt__(self, other):
        """
        Return a boolean indicating whether the list is greater than the other
        list, by comparing corresponding list items case-insensitively.

        The other list may be a :class:`NocaseList` object or any other
        iterable. In all cases, the comparison takes place case-insensitively.

        Invoked using e.g. ``ncl > other``.

        Raises:
          AttributeError: A value in the other list does not have the casefold
            method.
        """
        if isinstance(other, NocaseList):
            other = other._casefolded_list  # pylint: disable=protected-access
        else:
            other = self._new_casefolded_list(other)
        return self._casefolded_list > other

    def __lt__(self, other):
        """
        Return a boolean indicating whether the list is less than the other
        list, by comparing corresponding list items case-insensitively.

        The other list may be a :class:`NocaseList` object or any other
        iterable. In all cases, the comparison takes place case-insensitively.

        Invoked using e.g. ``ncl < other``.

        Raises:
          AttributeError: A value in the other list does not have the casefold
            method.
        """
        if isinstance(other, NocaseList):
            other = other._casefolded_list  # pylint: disable=protected-access
        else:
            other = self._new_casefolded_list(other)
        return self._casefolded_list < other

    def __ge__(self, other):
        """
        Return a boolean indicating whether the list is greater than or
        equal to the other list, by comparing corresponding list items
        case-insensitively.

        The other list may be a :class:`NocaseList` object or any other
        iterable. In all cases, the comparison takes place case-insensitively.

        Invoked using e.g. ``ncl >= other``.

        Raises:
          AttributeError: A value in the other list does not have the casefold
            method.
        """
        if isinstance(other, NocaseList):
            other = other._casefolded_list  # pylint: disable=protected-access
        else:
            other = self._new_casefolded_list(other)
        return self._casefolded_list >= other

    def __le__(self, other):
        """
        Return a boolean indicating whether the list is less than or
        equal to the other list, by comparing corresponding list items
        case-insensitively.

        The other list may be a :class:`NocaseList` object or any other
        iterable. In all cases, the comparison takes place case-insensitively.

        Invoked using e.g. ``ncl <= other``.

        Raises:
          AttributeError: A value in the other list does not have the casefold
            method.
        """
        if isinstance(other, NocaseList):
            other = other._casefolded_list  # pylint: disable=protected-access
        else:
            other = self._new_casefolded_list(other)
        return self._casefolded_list <= other

    def count(self, value):
        """
        Return the number of times the specified value occurs in the list,
        comparing the value and the list items case-insensitively.

        Raises:
          AttributeError: The value does not have the casefold method.
        """
        return self._casefolded_list.count(self._casefolded_value(value))

    def copy(self):
        """
        Return a shallow copy of the list.

        Note: This method is supported on Python 2 and Python 3, even though
        the built-in list class only supports it on Python 3.
        """
        return NocaseList(self)

    def clear(self):
        """
        Remove all items from the list (and return None).

        Note: This method is supported on Python 2 and Python 3, even though
        the built-in list class only supports it on Python 3.
        """
        try:
            super(NocaseList, self).clear()
            self._casefolded_list.clear()
        except AttributeError:
            del self[:]
            del self._casefolded_list[:]

    def index(self, value, start=0, stop=9223372036854775807):
        """
        Return the index of the first item that is equal to the specified
        value, comparing the value and the list items case-insensitively.

        The search is limited to the index range defined by the specified
        ``start`` and ``stop`` parameters, whereby ``stop`` is the index
        of the first item after the search range.

        Raises:
          AttributeError: The value does not have the casefold method.
          ValueError: No such item is found.
        """
        return self._casefolded_list.index(
            self._casefolded_value(value), start, stop)

    def append(self, value):
        """
        Append the specified value as a new item to the end of the list
        (and return None).

        Raises:
          AttributeError: The value does not have the casefold method.
        """
        super(NocaseList, self).append(value)
        self._casefolded_list.append(self._casefolded_value(value))

    def extend(self, iterable):
        """
        Extend the list by the items in the specified iterable
        (and return None).

        Raises:
          AttributeError: A value in the iterable does not have the casefold
            method.
        """
        super(NocaseList, self).extend(iterable)
        # The following is a circumvention for a behavior of the 'pickle' module
        # that during unpickling may call this method on an object that has
        # been created with __new__() without calling __init__().
        try:
            for value in iterable:
                self._casefolded_list.append(self._casefolded_value(value))
        except AttributeError:
            self._casefolded_list = self._new_casefolded_list(self)

    def insert(self, index, value):
        """
        Insert a new item with specified value before the item at the specified
        index (and return None).

        Raises:
          AttributeError: The value does not have the casefold method.
        """
        super(NocaseList, self).insert(index, value)
        self._casefolded_list.insert(index, self._casefolded_value(value))

    def pop(self, index=-1):
        """
        Return the value of the item at the specified index and also remove it
        from the list.
        """
        self._casefolded_list.pop(index)
        return super(NocaseList, self).pop(index)

    def remove(self, value):
        """
        Remove the first item from the list whose value is equal to the
        specified value (and return None), comparing the value and the list
        items case-insensitively.

        Raises:
          AttributeError: The value does not have the casefold method.
        """
        self._casefolded_list.remove(self._casefolded_value(value))
        super(NocaseList, self).remove(value)

    def reverse(self):
        """
        Reverse the items in the list in place (and return None).
        """
        super(NocaseList, self).reverse()
        self._casefolded_list = self._new_casefolded_list(self)

    def sort(self, key=None, reverse=False):
        """
        Sort the items in the list in place (and return None).

        The sort is stable, in that the order of two (case-insensitively) equal
        elements is maintained.

        By default, the list is sorted in ascending order of its casefolded
        item values. If a key function is given, it is applied once to each
        casefolded list item and the list is sorted in ascending or
        descending order of their key function values.

        The ``reverse`` flag can be set to sort in descending order.
        """

        def casefolded_key(value):
            """Key function used for sorting"""
            # The function cannot raise AttributeError due to missing casefold
            # method, because the list items have been verified for that when
            # adding them to the list.
            if key:
                return key(self._casefolded_value(value))
            return self._casefolded_value(value)

        super(NocaseList, self).sort(key=casefolded_key, reverse=reverse)
        self._casefolded_list = self._new_casefolded_list(self)


# Remove methods that should only be present in a particular Python version.
# If the documentation is being built, the methods are not removed in order to
# show them in the documentation.
if sys.version_info[0] == 2 and not BUILDING_DOCS:
    del NocaseList.__setstate__
    del NocaseList.__getstate__
