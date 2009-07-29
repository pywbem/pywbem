# Package init file for pywbem

#
# (C) Copyright 2004,2006 Hewlett-Packard Development Company, L.P.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as
# published by the Free Software Foundation; version 2 of the License.
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
#         Martin Pool <mbp@hp.com>

"""pywbem - WBEM client bindings for Python.

PyWBEM is a Python library for making CIM operations over HTTP using
the CIM-XML protocol.  It is based on the idea that a good WBEM
client should be easy to use and not necessarily require a large
amount of programming knowlege.  PyWBEM is suitable for a large range
of tasks from simply poking around to writing web and GUI
applications.

"""

# There are submodules, but clients shouldn't need to know about them.
# Importing just this module is enough.

# These are explicitly safe for 'import *'

from cim_types import *
from cim_constants import *
from cim_operations import *
from cim_obj import *
from tupleparse import ParseError

