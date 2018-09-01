
Pywbem - A WBEM client
**********************

Pywbem is a WBEM client, written in pure Python. It supports Python 2 and
Python 3.

A WBEM client allows issuing operations to a WBEM server, using the CIM
operations over HTTP (CIM-XML) protocol defined in the DMTF standards
:term:`DSP0200` and :term:`DSP0201`.
The CIM/WBEM infrastructure is used for a wide variety of systems
management tasks supported by systems running WBEM servers.
See :term:`WBEM Standards` for more information about WBEM.

This package is based on the idea that a good WBEM client should be easy to use
and not necessarily require a large amount of programming knowledge. It is
suitable for a large range of tasks from simply poking around to writing web
and GUI applications.

The general pywbem web site is: https://pywbem.github.io/pywbem/index.html.

.. toctree::
   :maxdepth: 2
   :numbered:

   intro.rst
   concepts.rst
   tutorial.rst
   client.rst
   server.rst
   indication.rst
   compiler.rst
   utilities.rst
   mocksupport.rst
   development.rst
   appendix.rst
   changes.rst
