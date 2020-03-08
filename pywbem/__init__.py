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

# The config namespace is imported as a sub-namespace to make the config
# variables accessible directly via their defining namespace. Importing
# them into the pywbem namespace would duplicate their names and thus
# would cause changes to the config variables not to be visible in their
# original namespace.
from . import config  # noqa: F401

from ._utils import *  # noqa: F403,F401
from ._cim_types import *  # noqa: F403,F401
from ._cim_constants import *  # noqa: F403,F401
from ._cim_operations import *  # noqa: F403,F401
from ._nocasedict import *  # noqa: F403,F401
from ._cim_obj import *  # noqa: F403,F401
from ._tupleparse import *  # noqa: F403,F401
from ._cim_http import *  # noqa: F403,F401
from ._exceptions import *  # noqa: F403,F401
from ._mof_compiler import *  # noqa: F403,F401
from ._valuemapping import *  # noqa: F403,F401
from ._server import *  # noqa: F403,F401
from ._subscription_manager import *  # noqa: F403,F401
from ._listener import *  # noqa: F403,F401
from ._recorder import *  # noqa: F403,F401
from ._statistics import *  # noqa: F403,F401
from ._logging import *  # noqa: F403,F401
from ._warnings import *  # noqa: F403,F401 pylint: disable=redefined-builtin

from ._version import __version__  # noqa: F401

# Establish compatibility with old module names:
from . import _cim_types as cim_types  # noqa: F401
from . import _cim_constants as cim_constants  # noqa: F401
from . import _cim_operations as cim_operations  # noqa: F401
from . import _cim_obj as cim_obj  # noqa: F401
from . import _tupleparse as tupleparse  # noqa: F401
from . import _cim_http as cim_http  # noqa: F401
from . import _exceptions as exceptions  # noqa: F401
from . import _mof_compiler as mof_compiler  # noqa: F401
from . import _cim_xml as cim_xml  # noqa: F401
from . import _tupletree as tupletree  # noqa: F401
sys.modules['pywbem.cim_types'] = cim_types
sys.modules['pywbem.cim_constants'] = cim_constants
sys.modules['pywbem.cim_operations'] = cim_operations
sys.modules['pywbem.cim_obj'] = cim_obj
sys.modules['pywbem.tupleparse'] = tupleparse
sys.modules['pywbem.cim_http'] = cim_http
sys.modules['pywbem.exceptions'] = exceptions
sys.modules['pywbem.mof_compiler'] = mof_compiler
sys.modules['pywbem.cim_xml'] = cim_xml
sys.modules['pywbem.tupletree'] = tupletree

_python_m = sys.version_info[0]  # pylint: disable=invalid-name
_python_n = sys.version_info[1]  # pylint: disable=invalid-name

# Keep these Python versions in sync with setup.py
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
