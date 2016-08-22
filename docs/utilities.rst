
.. _`WBEM utility commands`:

WBEM utility commands
=====================

The pywbem package provides a number of WBEM utility commands.
They are all implemented as pure-Python scripts.

These commands are installed into the Python script directory and should
therefore automatically be available in the command search path.

The following commands are provided:

* :ref:`mof_compiler`

  A MOF compiler that takes MOF files as input and creates, updates or
  removes CIM instances, classes or qualifier types in a CIM repository.

* :ref:`wbemcli`

  A WBEM command line interface that provides an interactive Python
  environment for issuing WBEM operations to a WBEM server.

.. _`mof_compiler`:

mof_compiler
------------

The ``mof_compiler`` command is a MOF compiler. It compiles MOF files, and
updates the repository of a WBEM server with the result.

The MOF compiler can also be invoked from programs via the
:ref:`MOF compiler API`.

The MOF compiler has a pluggable interface for the CIM repository. The default
implementation of that interface uses a WBEM server as its repository.
The plug interface is also described in the :ref:`MOF compiler API`.

Here is the help text of the command:

.. include:: mof_compiler.help.txt
   :literal:

.. _`wbemcli`:

wbemcli
-------

The ``wbemcli`` command is a WBEM client command line interface (CLI). It is
implemented as an interactive shell.

The WBEM client CLI does not have an external API on its own; it is for the
most part a consumer of the :ref:`WBEM client library API`.

Here is the help text of the command:

.. include:: wbemcli.help.txt
   :literal:

