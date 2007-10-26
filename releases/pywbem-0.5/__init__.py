# Package init file for pywbem

#
# (C) Copyright 2004 Hewlett-Packard Development Company, L.P.
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
#         Martin Pool <mbp@hp.com>

"""pywbem - WBEM client bindings for Python.

WBEM is the Web-Based Enterprise Management protocol.  A kind of
distributed object protocol for managing diverse systems.

Using WBEM you a client program can discover detailed or summary
information about managed objects such as processors, disks, software
packages and processes.  The client does not need any a-priori
knowledge of the objects being managed because the server provides a
lot of descriptive metadata.

WBEM natively deals with objects represented in CIM (Common
Information Model), a "heavy" OO style that feels like Java.  This
library provides a mapping from CIM to a "lighter" style which is
easier to use in Python.

Despite this, the representation in Python is such that no information
is lost.  Python can be transformed to and from XML and the same
objects will be returned.

This library also provides routines to translate from Python CIM
objects to and from the CIM-XML format used on the network.

The following CIM types have corresponding Python classes:

    CIMClassName
    CIMInstanceName
    CIMInstance
    CIMClass
    CIMMethod
    Qualifier

The following CIM atomics are represented as Python types that
subclass the corresponding Python atomic types.  (In other words, you
can treat a Uint16 as a Python integer, but you must explicitly
convert to a CIM type when going in the other direction.)

    Uint8, Sint8
    Uint16, Sint16
    Uint32, Sint32
    Uint64, Sint64
    Real32, Real64

Booleans are just booleans.    

"""

# There are submodules, but clients shouldn't need to know about them.
# Importing just this module is enough.

# These are explicitly safe for 'import *'

from cim_types import *
from cim_constants import *
from cim_operations import *
from cim_obj import *
from tupleparse import ParseError
