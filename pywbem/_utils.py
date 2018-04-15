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


# This module is meant to be safe for 'import *'.

from __future__ import print_function, absolute_import

import inspect
import six

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
