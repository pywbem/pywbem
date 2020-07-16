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
Class ``NocaseList`` is a list implementation with case-insensitive but
case-preserving items.

Whenever items of the list are looked up by value or item values are
compared, that is done case-insensitively. Whenever the value of list items
is returned, they have the lexical case that was originally specified.

It is used for lists of case-insensitive items such as namespaces returned
by the pywbem mock support.

Users of pywbem will notice ``NocaseList`` objects only as a result of pywbem
functions. Users cannot create ``NocaseList`` objects.

Except for the case-insensitivity of its items, it behaves like the built-in
:class:`py:list`. Therefore, ``NocaseList`` is not described in detail in this
documentation.
"""

# This module is meant to be safe for 'import *'.

from __future__ import print_function, absolute_import

__all__ = []


def lc_list(lst):
    """
    Return a lower-cased list from the input list.
    """
    result = list()
    for value in lst:
        result.append(value.lower())
    return result


class NocaseList(list):
    """
    A case-insensitive, but case-preserving, list.

    Whenever items of the list are looked up by value or item values are
    compared, that is done case-insensitively. Whenever the value of list items
    is returned, they have the lexical case that was originally specified.

    The list items must support the `lower()` method.

    The implementation maintains a second list with the lower-cased items of
    the inherited list, and maintains both lists to be in sync.
    """

    def __init__(self, iterable=()):
        """
        Initialize the new list from an existing iterable.
        """
        super(NocaseList, self).__init__(iterable)

        # A list with the same items as the original list, except they are in
        # lower case.
        self._lc_list = lc_list(self)

    # __repr__(): The inherited method is used.

    # __getattribute__(): The inherited method is used.

    # __getitem__(): The inherited method is used.

    def __setitem__(self, index, value):
        """
        Invoked when assigning a value for an item at an index using
        `lst[index] = val`.
        """
        super(NocaseList, self).__setitem__(index, value)
        self._lc_list[index] = value.lower()

    def __delitem__(self, index):
        """
        Invoked when deleting an item at an index using `del lst[index]`.
        """
        super(NocaseList, self).__delitem__(index)
        del self._lc_list[index]

    # __iter__(): The inherited method is used.

    def __contains__(self, value):
        """
        Invoked when determining whether a specific value is in the list
        using `value in lst`.
        Looks up the value case-insensitively.
        """
        return value.lower() in self._lc_list

    # __sizeof__(): The inherited method is used.

    def __add__(self, value):
        """
        Invoked for `list + value`.
        Return a shallow copy of the list, with the new value appended.
        """
        lst = self.copy()
        lst.append(value)
        return lst

    def __iadd__(self, value):
        """
        Invoked for `list += value`.
        Append the value to the list and return itself.

        Note: It is unusual that the method has to return self, but it was
        verified that this is necessary.
        """
        self.append(value)
        return self

    def __mul__(self, number):
        """
        Invoked for `list * number`.
        Return a shallow copy of the list, that is the list times number.
        """
        lst = NocaseList()
        for _ in range(0, number):
            lst.extend(self)
        return lst

    def __rmul__(self, number):
        """
        Invoked for `number * list`.
        Return a shallow copy of the list, that is the list times number.
        """
        lst = self * number  # Use __mul__()
        return lst

    def __imul__(self, number):
        """
        Invoked for `list *= number`.
        Extends the list by itself times number and return itself.

        Note: It is unusual that the method has to return self, but it was
        verified that this is necessary.
        """
        lst = self * number  # Use __mul__()
        return lst

    def __reversed__(self):
        """
        Invoked for `reversed(list)`.
        Returns a shallow copy of the list that has its items reversed.
        """
        lst = self.copy()
        lst.reverse()
        return lst

    def __eq__(self, other):
        """
        Invoked when two lists are compared with the `==` operator.
        When list item values are compared during this process, this is done
        case-insensitively.
        """
        if isinstance(other, NocaseList):
            other = other._lc_list
        else:
            other = lc_list(other)
        return self._lc_list == other

    def __ne__(self, other):
        """
        Invoked when two lists are compared with the `!=` operator.
        When list item values are compared during this process, this is done
        case-insensitively.
        """
        if isinstance(other, NocaseList):
            other = other._lc_list
        else:
            other = lc_list(other)
        return self._lc_list != other

    def __gt__(self, other):
        """
        Invoked when two lists are compared with the `>` operator.
        When list item values are compared during this process, this is done
        case-insensitively.
        """
        if isinstance(other, NocaseList):
            other = other._lc_list
        else:
            other = lc_list(other)
        return self._lc_list > other

    def __lt__(self, other):
        """
        Invoked when two lists are compared with the `<` operator.
        When list item values are compared during this process, this is done
        case-insensitively.
        """
        if isinstance(other, NocaseList):
            other = other._lc_list
        else:
            other = lc_list(other)
        return self._lc_list < other

    def __ge__(self, other):
        """
        Invoked when two lists are compared with the `>=` operator.
        When list item values are compared during this process, this is done
        case-insensitively.
        """
        if isinstance(other, NocaseList):
            other = other._lc_list
        else:
            other = lc_list(other)
        return self._lc_list >= other

    def __le__(self, other):
        """
        Invoked when two lists are compared with the `<=` operator.
        When list item values are compared during this process, this is done
        case-insensitively.
        """
        if isinstance(other, NocaseList):
            other = other._lc_list
        else:
            other = lc_list(other)
        return self._lc_list <= other

    def count(self, value):
        """
        Return the number of times the value occurs (case-insensitively) in the
        list.
        """
        return self._lc_list.count(value.lower())

    def copy(self):
        """
        Return a shallow copy of the list.
        """
        return NocaseList(self)

    def clear(self):
        """
        Remove all items from the list (and return None).

        Note: This method was introduced in Python 3.
        """
        super(NocaseList, self).clear()
        self._lc_list.clear()

    def index(self, value, start=0, stop=9223372036854775807):
        """
        Return the index of the first item that is (case-insensitively) equal
        to value.

        Raises ValueError if the value is (case-insensitively) not present.
        """
        return self._lc_list.index(value.lower(), start, stop)

    def append(self, value):
        """
        Append the value as a new item to the end of the list (and return None).
        """
        super(NocaseList, self).append(value)
        self._lc_list.append(value.lower())

    def extend(self, iterable):
        """
        Extend the list by the items in the iterable (and return None).
        """
        super(NocaseList, self).extend(iterable)
        for value in iterable:
            self._lc_list.append(value.lower())

    def insert(self, index, value):
        """
        Insert a new item with value before the item at index (and return None).
        """
        super(NocaseList, self).insert(index, value)
        self._lc_list.insert(index, value.lower())

    def pop(self, index=-1):
        """
        Return the item at an index and also remove it from the list.
        """
        self._lc_list.pop(index)
        return super(NocaseList, self).pop(index)

    def remove(self, value):
        """
        Remove the first item from the list where its value is
        (case-insensitively) equal to the specified value (and return None).
        """
        self._lc_list.remove(value.lower())
        super(NocaseList, self).remove(value)

    def reverse(self):
        """
        Reverse the list in place (and return None).
        """
        super(NocaseList, self).reverse()
        self._lc_list = lc_list(self)

    def sort(self, key=None, reverse=False):
        """
        Sort the list in place (and return None). The sort is stable, in that
        the order of two (case-insensitively) equal elements is maintained.

        By default, the list is sorted in ascending order of its (lower-cased)
        item values. If a key function is given, it is applied once to each
        (lower-cased) list item and the list is sorted in ascending or
        descending order of their key function values.

        The reverse flag can be set to sort in descending order.
        """

        def lower_key(value):
            """Key function used for sorting"""
            if key:
                return key(value.lower())
            return value.lower()

        super(NocaseList, self).sort(key=lower_key, reverse=reverse)
        self._lc_list = lc_list(self)
