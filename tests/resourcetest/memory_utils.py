"""
Utility functions for memory size of objects.
"""

import sys
import itertools
import struct
import collections

DEBUG = False  # Print debug messages in total_sizeof()


def _dict_iter(dict_):
    """
    Return flat iterable of dict keys and values.
    """
    return itertools.chain.from_iterable(dict_.items())


def total_sizeof(obj, iters=None):
    """
    Return the memory size in Bytes of an object and all of its attributes.
    For collections that do not expose their items as attributes, the size
    of the items is also accounted for.

    A number of built-in collection classes that do not expose their items as
    attributes are recognized automatically:

        tuple
        list
        collections.deque
        dict
        set
        frozenset

    Items returned by dictionary view classes are intentionally not accounted
    for, because they are accounted on the dictionary object.

    Additional collection classes can be specified with the 'iters' parameter.
    That is only needed for collection classes that are not derived from the
    automatically recognized collection classes and that do not expose their
    items as attributes. Note that this excludes most if not all user-defined
    collection classes written in pure Python.

    Parameters:

      obj (object): The object whose size is to be returned.

      iters (dict): Iteration functions for additional collections.
        Key is the collection class, value is a function or bound method that
        takes an object of the collection class (or subclass thereof) as a
        single argument, and iterates over its items.

        Example::

            iters = {
                SomeContainerClass: iter,
                OtherContainerClass: OtherContainerClass.get_elements,
            }

    Original idea from https://code.activestate.com/recipes/577504/
    """

    def _debug_enter():
        """
        Do things needed when entering sizeof().
        """
        if DEBUG:
            nesting[0] += 1

    def _debug_leave():
        """
        Do things needed when leaving sizeof().
        """
        if DEBUG:
            nesting[0] -= 1

    def _debug_msg(msg, obj, size):
        """
        Print debug message about the progress of determining the object size.
        """
        if DEBUG:
            o_str = repr(obj) if isinstance(obj, (str, bool, int)) else ''
            print("Debug: {}: {} {} object {} at {}: {}".
                  format(nesting[0], msg, type(obj), o_str, id(obj),
                         size if size is not None else ''))

    # Built-in collection types where the collection items do not show up in
    # attributes.
    all_iters = collections.OrderedDict([
        (tuple, iter),
        (list, iter),
        (dict, _dict_iter),
        (collections.deque, iter),
        (set, iter),
        (frozenset, iter),
    ])

    # Additionally provided iteration functions take precedence
    if iters:
        all_iters.update(iters)

    seen = set()  # Track which objects have already been seen

    default_size = sys.getsizeof(0)
    ref_size = struct.calcsize('P')  # pylint: disable=no-member

    if DEBUG:
        nesting = [0]

    def sizeof(o):
        # pylint: disable=invalid-name
        """
        Return total size of the object.
        """
        _debug_enter()

        if id(o) in seen:
            # Do not double count the same object, but account for referencing
            # the object
            s = ref_size
            _debug_msg("Size of reference to already seen", o, s)
            _debug_leave()
            return s
        seen.add(id(o))

        # Size of the object without its attributes or collection items
        s = sys.getsizeof(o, default_size)
        _debug_msg("Base size of", o, s)

        # Add size of collection items, recursively
        for cls, iterfunc in all_iters.items():
            if isinstance(o, cls):
                _debug_msg("Calculating size of collection items of", o, None)
                ds = sum(map(sizeof, iterfunc(o)))
                s += ds
                _debug_msg("Adding size of collection items of", o, ds)
                break

        # Add size of slotted attributes, recursively
        if getattr(o, '__slots__', None):
            _debug_msg("Calculating size of slotted attributes of", o, None)
            ds = sum(sizeof(getattr(o, attr_name))
                     for attr_name in o.__slots__ if hasattr(o, attr_name))
            s += ds
            _debug_msg("Adding size of slotted attributes of", o, ds)

        # Add size of non-slotted attributes, recursively
        if getattr(o, '__dict__', None):
            _debug_msg("Calculating size of non-slotted attributes of", o, None)
            ds = sizeof(o.__dict__)
            s += ds
            _debug_msg("Adding size of non-slotted attributes of", o, ds)

        _debug_leave()
        return s

    return sizeof(obj)
