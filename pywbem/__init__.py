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
The ``pywbem`` package provides a WBEM client library and some WBEM utility
commands, all written in pure Python.

A WBEM client library allows issuing operations to a WBEM server, using
the CIM operations over HTTP (CIM-XML) protocol defined in the DMTF standards
DSP0200 and DSP0201. See http://www.dmtf.org/standards/wbem for information
about WBEM and for these standards.

This package is based on the idea that a good WBEM client should be easy to use
and not necessarily require a large amount of programming knowledge. It is
suitable for a large range of tasks from simply poking around to writing web
and GUI applications.

WBEM client library
-------------------

Class `WBEMConnection` is the main class of the WBEM client library and is a
good starting point to understand the WBEM client API.

Importing the ``pywbem`` package causes some names from its sub-modules to
be folded into the package namespace.
For example, class `WBEMConnection` is defined in the `cim_operations`
sub-module and is folded into the package namespace::

    import pywbem
    conn = pywbem.WBEMConnection(...)

it can also be used from its sub-module::

    from pywbem.cim_operations import WBEMConnection
    conn = WBEMConnection(...)

Using the symbol from the package namespace is preferred; but both forms are
supported.

Not all public symbols from all sub-modules of the ``pywbem`` package are part
of the external API of the WBEM client library. The external API generally
consists of the symbols in the ``pywbem`` package namespace, and the
corresponding symbols in its sub-modules.

Consumers of this package that use other symbols than those from the external
API are at the risk of suffering from incompatible changes in future versions
of this package.

The Epydoc documentation tool that is used to produce these web pages does
not list all symbols that are folded into the package namespace, unfortunately
(as you can see, it lists only the variables, not including `__version__`).
It does however honor the ``__all__`` variable defining the exported symbols
in each sub-module, and shows only those exported symbols in the documentation
that is generated for the sub-modules. In other words, the symbols that
you can see in the generated documentation for a sub-module is exactly
what is part of the external API.

The external API of the WBEM client library consists of the following symbols:

* All symbols exported by the ``pywbem`` package, which are:

  - `__version__` (string) - Version of the ``pywbem`` package.

  - The symbols exported from the sub-modules in the remainder of this list,
    folded into the ``pywbem`` package namespace.

* All symbols exported by the `cim_operations` module.

* All symbols exported by the `cim_constants` module.

* All symbols exported by the `cim_types` module.

* All symbols exported by the `cim_obj` module.

* All symbols exported by the `tupleparse` module.

* All symbols exported by the `cim_http` module.

WBEM utility commands
---------------------

This package provides the following commands (implemented as Python scripts):

* ``mof_compiler`` : A MOF compiler.

  It has a pluggable interface for the MOF repository. The default
  implementation of that interface uses a WBEM server as its MOF repository.
  It uses the `mof_compiler` module that can also be used by Python programs
  that need to compile MOF.

  Invoke with ``--help`` for help.

  The external API of the MOF compiler consists of the following symbols:

  - All symbols exported by the `mof_compiler` module. This includes the
    plug interface for the MOF repository.

* ``wbemcli`` : A WBEM client CLI.

  It is currently implemented as an interactive shell, and is expected to morph
  into a full fledged command line utility in the future.

  Invoke with ``--help`` for help, or see the `wbemcli` module.

  The WBEM client CLI does not have an external API on its own; it is for the
  most part a consumer of the `WBEMConnection` class.

These commands are installed into the Python script directory and should
therefore be available in the command search path.

Experimental components
-----------------------

This package contains some components that are considered experimental at
this point:

* `cim_provider` :   Module for writing CIM providers in Python.

* `cim_provider2` :  Another module for writing CIM providers in Python.

* `twisted_client` : An experimental alternative WBEM client library that uses
  the Python `twisted` package.

These components are included in this package, but they are not covered in the
generated documentation, at this point.

WBEM Listener (``irecv``)
-------------------------

The PYWBEM Client project on GitHub (https://github.com/pywbem/pywbem)
contains the ``irecv`` package in addition to the ``pywbem`` package. The
``irecv`` package is a WBEM listener (indication receiver) and is considered
experimental at this point.

It is not included in this package or in the generated documentation, at this
point.

You can get it by accessing the
`irecv directory <https://github.com/pywbem/pywbem/tree/master/irecv>`_
of the PyWBEM Client project on GitHub.

Version
-------

For the current version of the ``pywbem`` package, see the `NEWS <NEWS.txt>`_
file. Its version can also be retrieved from the `pywbem.__version__`
attribute (as a string).

Changes
-------

The change log is in the `NEWS <NEWS.txt>`_ file.

Compatibility
-------------

The ``pywbem`` package is supported in these environments:

* on Windows, with Python 2.6, 2.7, 3.4, 3.5, and higher 3.x

* on Linux, with Python 2.6, 2.7, 3.4, 3.5, and higher 3.x

OS X has simply not been tested and is therefore not listed, above.
You are welcome to try it out and report any issues.
"""

# There are submodules, but clients shouldn't need to know about them.
# Importing just this module is enough.
# These are explicitly safe for 'import *'

import sys

from .cim_types import *
from .cim_constants import *
from .cim_operations import *
from .cim_obj import *
from .tupleparse import *
from .cim_http import *

# Version of the pywbem package
# !!! Keep in sync with version stated in module docstring, above !!!
# !!! Keep in sync with version in ../setup.py !!!
# Possible formats are:
#   M.N.Udev   : During development of future M.N.U release
#   M.N.UrcX   : Release candidate X of future M.N.U release
#   M.N.U      : The final M.N.U release
__version__ = '0.8.4'

_python_m = sys.version_info[0]
_python_n = sys.version_info[1]
if _python_m == 2 and _python_n < 6:
    raise RuntimeError('On Python 2, PyWBEM requires Python 2.6 or higher')
elif _python_m == 3 and _python_n < 4:
    raise RuntimeError('On Python 3, PyWBEM requires Python 3.4 or higher')

