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
"""

# This module is meant to be safe for 'import *'.

from __future__ import print_function, absolute_import

from nocasedict import NocaseDict as _NocaseDict
from nocasedict import HashableMixin, KeyableByMixin


# Used as default value for parameters to detect that they have not been
# specified as an argument. Must match the definition in nocasedict package.
_OMITTED = object()


class NocaseDict(HashableMixin, KeyableByMixin('name'), _NocaseDict):
    """
    NocaseDict class using nocasedict.NocaseDict, adding the following
    functionality:

    * hashability via nocasedict.HashableMixin

    * keyability by attribute 'name' via nocasedict.KeyableByMixin('name')

    * the ability to allow or disallow (by default) unnamed keys via a public
      'allow_unnamed_keys' attribute
    """

    def __init__(self, *args, **kwargs):
        super(NocaseDict, self).__init__(*args, **kwargs)
        self.allow_unnamed_keys = False

    def _check_unnamed_key(self, key):
        """
        Reject unnamed keys if not allowed.
        """
        if key is None and not self.allow_unnamed_keys:
            raise ValueError("Key None (unnamed key) is not allowed for this "
                             "object")

    # The following methods must be all those that take a key parameter

    def __getitem__(self, key):
        self._check_unnamed_key(key)
        return super(NocaseDict, self).__getitem__(key)

    def __setitem__(self, key, value):
        self._check_unnamed_key(key)
        return super(NocaseDict, self).__setitem__(key, value)

    def __delitem__(self, key):
        self._check_unnamed_key(key)
        return super(NocaseDict, self).__delitem__(key)

    def __contains__(self, key):
        self._check_unnamed_key(key)
        return super(NocaseDict, self).__contains__(key)

    def pop(self, key, default=_OMITTED):
        self._check_unnamed_key(key)
        return super(NocaseDict, self).pop(key, default)
