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
PyWBEM provides a WBEM client library and some related utilities, written in
pure Python.

The WBEM client library allows issuing operations to a WBEM server, using
the CIM operations over HTTP (CIM-XML) protocol defined in the DMTF standards
DSP0200 and DSP0201. See http://www.dmtf.org/standards/wbem for information
about WBEM.

It is based on the idea that a good WBEM client should be easy to use and not
necessarily require a large amount of programming knowledge. It is suitable for
a large range of tasks from simply poking around to writing web and GUI
applications.

* `WBEMConnection` :  Main class of the WBEM client library and a good starting
  point to read about it.

The WBEM-related utilities included in this package are:

* `mof_compiler` :   Script for compiling MOF files, can also be used as a
  module.

* `cim_provider` :   Module for writing CIM providers in Python.

* `cim_provider2` :  Another module for writing CIM providers in Python.

* `twisted_client` : An experimental alternative WBEM client library that uses
  the Python `twisted` package.

* `wbemcli` :  Script providing a WBEM client CLI as an interactive shell.

Importing the `pywbem` package causes a subset of symbols from its sub-modules
to be folded into the target namespace.

The use of these folded symbols is shown for the example of class
`WBEMConnection`:

.. code:: python

    import pywbem
    conn = pywbem.WBEMConnection(...)

or:

.. code:: python

    from pywbem import WBEMConnection
    conn = WBEMConnection(...)

or (less preferred):

.. code:: python

    from pywbem import *
    conn = WBEMConnection(...)

The folded symbols' origin symbols in the sub-modules are also considered part
of the public interface of the `pywbem` package.

Programs using sub-modules that are not part of the WBEM client library, or
specific symbols that are not folded into the target namespace of the `pywbem`
package need to import the respective sub-modules explicitly.

The use of such sub-modules is shown for the example of class
`cim_provider.CIMProvider`:

.. code:: python

    from pywbem import cim_provider
    provider = cim_provider.CIMProvider(...)

or:

.. code:: python

    from pywbem.cim_provider import CIMProvider
    provider = CIMProvider(...)

or:

.. code:: python

    import pywbem.cim_provider
    provider = pywbem.cim_provider.CIMProvider(...)

Version
-------

This version of PyWBEM is 0.8.0-dev.

The version number follows the conventions of semantic versioning (see
http://semver.org/):

 * M.N.U-dev  : During development of future M.N.U release
 * M.N.U-rc.1 : Release candidate 1 of future M.N.U release
 * M.N.U      : The final M.N.U release

When creating correspondingly versioned RPM packages, the hyphen (-) after
the M.N.U version needs to be replaced by a tilde (~) to cause RPM to correctly
treat the preliminary versions to be younger than the final version.

Changes
-------

The change log is in the `NEWS <../NEWS>`_ file.

Compatibility
-------------

PyWBEM has been tested with Python 2.7 on Windows and Linux, and with Python
2.6 on Linux (due to a restriction of the `M2Crypto` package on Windows).

Python 2.6 is the minimum version of Python that is supported.

Python 3 is not yet supported.

Contributing
------------

PyWBEM is on SourceForge (http://sourceforge.net/projects/pywbem/). Bug
reports and discussion on the mailing list are welcome.

License
-------

PyWBEM is licensed with GNU LGPL v2.
See the `LICENSE.txt <../LICENSE.txt>`_ file.
"""

# Version of the pywbem package
# !!! Keep in sync with version stated in module docstring, above !!!
# Possible formats are:
#   M.N.U-dev  : During development of future M.N.U release
#   M.N.U-rc.1 : Release candidate 1 of future M.N.U release
#   M.N.U      : The final M.N.U release
__version__ = '0.8.0-dev'

# There are submodules, but clients shouldn't need to know about them.
# Importing just this module is enough.

# These are explicitly safe for 'import *'

from pywbem.cim_types import *
from pywbem.cim_constants import *
from pywbem.cim_operations import *
from pywbem.cim_obj import *
from pywbem.tupleparse import ParseError
from pywbem.cim_http import Error, ConnectionError, AuthError, TimeoutError

import sys
if sys.version_info < (2,6,0):
    raise RuntimeError('PyWBEM requires Python 2.6.0 or higher')
