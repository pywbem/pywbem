
.. _`WBEM utility commands`:

WBEM utility commands
=====================

The **pywbem** PyPI package provides a number of WBEM utility commands.
They are all implemented as pure-Python scripts.

These commands are installed into the Python script directory and should
therefore be available in the command search path.

.. _`mof_compiler`:

mof_compiler
------------

A MOF compiler. It compiles MOF files, and updates the repository of a WBEM
server with the result.

.. include:: mof_compiler.help.txt
   :literal:

The MOF compiler can also be invoked from programs via the
:ref:`MOF compiler API`.

The MOF compiler has a pluggable interface for the MOF repository. The default
implementation of that interface uses a WBEM server as its MOF repository.
The plug interface is also described in the :ref:`MOF compiler API`.

.. _`wbemcli`:

wbemcli
-------

A WBEM client CLI. It is implemented as an interactive shell.

.. include:: wbemcli.help.txt
   :literal:

The WBEM client CLI does not have an external API on its own; it is for the
most part a consumer of the :ref:`WBEM client library API`.

