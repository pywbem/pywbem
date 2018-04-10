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
Pywbem is a WBEM client, written in pure Python.
It supports Python 2 and Python 3.
"""

# There are submodules, but clients shouldn't need to know about them.
# Importing just this module is enough.
# These are explicitly safe for 'import *'

from __future__ import absolute_import

import sys
import logging

from .cim_types import *  # noqa: F403,F401
from .cim_constants import *  # noqa: F403,F401
from .cim_operations import *  # noqa: F403,F401
from .cim_obj import *  # noqa: F403,F401
from .tupleparse import *  # noqa: F403,F401
from .cim_http import *  # noqa: F403,F401
from .exceptions import *  # noqa: F403,F401
from .mof_compiler import *  # noqa: F403,F401
from ._valuemapping import *  # noqa: F403,F401
from ._server import *  # noqa: F403,F401
from ._subscription_manager import *  # noqa: F403,F401
from ._listener import *  # noqa: F403,F401
from ._recorder import *  # noqa: F403,F401
from .config import *  # noqa: F403,F401
from ._statistics import *  # noqa: F403,F401
from ._logging import *  # noqa: F403,F401

from ._version import __version__  # noqa: F401

_python_m = sys.version_info[0]  # pylint: disable=invalid-name
_python_n = sys.version_info[1]  # pylint: disable=invalid-name
if _python_m == 2 and _python_n < 6:
    raise RuntimeError('On Python 2, pywbem requires Python 2.6 or higher')
elif _python_m == 3 and _python_n < 4:
    raise RuntimeError('On Python 3, pywbem requires Python 3.4 or higher')

# On Python 2, add a NullHandler to suppress the warning "No handlers could be
# found for logger ...".
if _python_m == 2:
    try:  # Python 2.7+ includes logging.NullHandler
        from logging import NullHandler
    except ImportError:
        class NullHandler(logging.Handler):
            """Implement logging NullHandler for Python 2.6"""
            def emit(self, record):
                pass
    logging.getLogger('pywbem').addHandler(NullHandler())
