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
The external API of the WBEM client library is defined by the symbols that
are exported from the ``pywbem`` Python package and its sub-modules via their
``__all__`` variables. Public symbols that are not listed in the
``__all__`` variables, as well as any private symbols are not part of the
external API of the WBEM client library.

Consumers of this package that use other symbols than those from the external
API are at the risk of suffering from incompatible changes in future versions
of this package.

The external API is completely available in the ``pywbem`` namespace. That
is the only namespace that needs to be imported by users of the API. The
sub-modules do not need to be imported; but their external symbols are still
available for compatibility.

This documentation describes the symbols of the ``pywbem`` namespace,
and it is recommended to use its symbols and not those of the sub-modules.

The WBEM client API consists of the following elements:

* `Package version`_ - Provides access to the version of the ``pywbem``
  package.
* `CIM operations`_ - Class :class:`WBEMConnection` is the main class of the
  WBEM client library and its methods invoke CIM operations against a WBEM
  server.
* `CIM objects`_ - Python objects for CIM instances, classes, properties, etc.
  that are used by the CIM operations as input or output.
* `CIM data types`_ - Python objects for representing CIM data types (actually
  their values).
* `CIM status codes`_ - CIM status codes returned by failing CIM operations.
* `Exceptions`_ - Exceptions specific to pywbem that may be raised.

Package version
---------------

The package version can be accessed by programs using the following variable.

For tooling reasons, this variable is currently shown as
``pywbem._version.__version__``, but users should access it as
``pywbem.__version__``.

.. autodata:: pywbem._version.__version__

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

from ._version import __version__

if sys.version_info < (2, 6, 0):
    raise RuntimeError('PyWBEM requires Python 2.6.0 or higher')
