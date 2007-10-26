#! /usr/bin/python

#
# (C) Copyright 2003, 2004 Hewlett-Packard Development Company, L.P.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#   
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#   
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
#

# Author: Tim Potter <tpot@hp.com>

"""
Subclasses of builtin Python types to remember CIM types.  This is
necessary as we need to remember whether an integer property is a
uint8, uint16, uint32 etc, while still being able to treat it as a
integer.
"""

class CIMType:
    """Base type for all CIM types."""

# CIM integer types

class CIMInt(CIMType, long):
    def __init__(self, arg, base, cimtype):
        int.__init__(self, arg, base)
        self.cimtype = cimtype

class Uint8(CIMInt):
    def __init__(self, arg, base = 0):
        CIMInt.__init__(self, arg, base, 'uint8')

class Sint8(CIMInt):
    def __init__(self, arg, base = 0):
        CIMInt.__init__(self, arg, base, 'sint8')

class Uint16(CIMInt):
    def __init__(self, arg, base = 0):
        CIMInt.__init__(self, arg, base, 'uint16')

class Sint16(CIMInt):
    def __init__(self, arg, base = 0):
        CIMInt.__init__(self, arg, base, 'sint16')

class Uint32(CIMInt):
    def __init__(self, arg, base = 0):
        CIMInt.__init__(self, arg, base, 'uint32')

class Sint32(CIMInt):
    def __init__(self, arg, base = 0):
        CIMInt.__init__(self, arg, base, 'sint32')

class Uint64(CIMInt):
    def __init__(self, arg, base = 0):
        CIMInt.__init__(self, arg, base, 'uint64')

class Sint64(CIMInt):
    def __init__(self, arg, base = 0):
        CIMInt.__init__(self, arg, base, 'sint64')

# CIM float types

class CIMFloat(CIMType, float):
    def __init__(self, arg, cimtype):
        float.__init__(self, arg)
        self.cimtype = cimtype

class Real32(CIMFloat):
    def __init__(self, arg):
        CIMFloat.__init__(self, arg, 'real32')

class Real64(CIMFloat):
    def __init__(self, arg):
        CIMFloat.__init__(self, arg, 'real64')

def cimtype(obj):
    """Return the CIM type name of an object as a string.  For a list, the
    type is the type of the first element as CIM arrays must be
    homogeneous."""
    
    if isinstance(obj, CIMType):
        return obj.cimtype

    if isinstance(obj, bool):
        return 'boolean'

    if isinstance(obj, (str, unicode)):
        return 'string'

    if isinstance(obj, list):
        return cimtype(obj[0])

    raise TypeError("Invalid CIM type for %s" % obj)


def atomic_to_cim_xml(obj):
    """Convert an atomic type to CIM external form"""
    if isinstance(obj, bool):
        if obj:
            return "true"
        else:
            return "false"
    else:
        return unicode(obj)
    
