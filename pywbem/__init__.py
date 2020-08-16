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
It supports Python 2.7 and Python 3.
Python 2.7 support has been deprecated with pywbem 1.0.0.
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
from ._exceptions import *  # noqa: F403,F401 pylint: disable=redefined-builtin
from ._warnings import *  # noqa: F403,F401 pylint: disable=redefined-builtin
from ._cim_types import *  # noqa: F403,F401
from ._cim_constants import *  # noqa: F403,F401
from ._cim_operations import *  # noqa: F403,F401
from ._nocasedict import *  # noqa: F403,F401
from ._cim_obj import *  # noqa: F403,F401
from ._tupleparse import *  # noqa: F403,F401
from ._cim_http import *  # noqa: F403,F401
from ._mof_compiler import *  # noqa: F403,F401
from ._valuemapping import *  # noqa: F403,F401
from ._server import *  # noqa: F403,F401
from ._subscription_manager import *  # noqa: F403,F401
from ._listener import *  # noqa: F403,F401
from ._recorder import *  # noqa: F403,F401
from ._statistics import *  # noqa: F403,F401
from ._logging import *  # noqa: F403,F401
from ._features import *  # noqa: F403,F401
from ._units import *  # noqa: F403,F401

from ._version import __version__  # noqa: F401

_python_m = sys.version_info[0]  # pylint: disable=invalid-name
_python_n = sys.version_info[1]  # pylint: disable=invalid-name

# Keep these Python versions in sync with setup.py
if _python_m == 2 and _python_n < 7:
    raise RuntimeError('On Python 2, pywbem requires Python 2.7 or higher')
if _python_m == 2 and _python_n == 7:
    import warnings
    warnings.warn(
        "Pywbem support for Python 2.7 is deprecated and will be removed in "
        "a future version",
        DeprecationWarning, 2)
if _python_m == 3 and _python_n < 4:
    raise RuntimeError('On Python 3, pywbem requires Python 3.4 or higher')
if _python_m == 3 and _python_n == 4:
    import warnings
    warnings.warn(
        "Pywbem support for Python 3.4 is deprecated and will be removed in "
        "a future version",
        DeprecationWarning, 2)

# On Python 2, add a NullHandler to suppress the warning "No handlers could be
# found for logger ...".
if _python_m == 2:
    from logging import NullHandler
    logging.getLogger('pywbem').addHandler(NullHandler())
