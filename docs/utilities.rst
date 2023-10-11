
.. _`WBEM utility commands`:

WBEM utility commands
=====================

The pywbem package provides a number of WBEM utility commands.
They are all implemented as pure-Python scripts.

These commands are installed into the Python script directory and should
therefore automatically be available in the command search path.

..index:: pair; MOF, compiler
..index:: single; MOF compiler

The following commands are provided:

* :ref:`mof_compiler`

  A MOF compiler that takes MOF files as input and updates the CIM repository
  of a WBEM server with the result.

Versions of pywbem before 1.0.0 provided a command ``wbemcli`` as an
interactive command line environment. It is recommended to use the
``pywbemcli`` command from the
`pywbemtools package on Pypi <https://pypi.org/project/pywbemtools/>`_
as a replacement.



.. _`mof_compiler`:

mof_compiler
------------

The ``mof_compiler`` command compiles MOF files and updates the CIM repository
of a WBEM server with the result.

If the compiler fails, any changes made to the CIM repository in the WBEM server
as part of the current compilation are rolled back. A limitation is that
changes to qualifier declarations are not yet rolled back (see issue #990).

The compiler provides a dry-run mode that simulates the compilation but does not
change the CIM repository in the WBEM server.

Here is the help text of the command:

.. include:: mof_compiler.help.txt
   :literal:
   :code: text
