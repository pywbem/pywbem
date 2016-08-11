#
# (C) Copyright 2004,2006 Hewlett-Packard Development Company, L.P.
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
#

"""
The **pywbem** package provides a WBEM client, written in pure Python.
It supports Python 2 and Python 3.
"""

# There are submodules, but clients shouldn't need to know about them.
# Importing just this module is enough.
# These are explicitly safe for 'import *'

from __future__ import absolute_import

import sys

from .cim_types import *
from .cim_constants import *
from .cim_operations import *
from .cim_obj import *
from .tupleparse import *
from .cim_http import *
from .exceptions import *
from ._server import *
from ._subscription_manager import *
from ._listener import *
from ._recorder import *
from .config import *

from ._version import __version__

_python_m = sys.version_info[0]
_python_n = sys.version_info[1]
if _python_m == 2 and _python_n < 6:
    raise RuntimeError('On Python 2, PyWBEM requires Python 2.6 or higher')
elif _python_m == 3 and _python_n < 4:
    raise RuntimeError('On Python 3, PyWBEM requires Python 3.4 or higher')

