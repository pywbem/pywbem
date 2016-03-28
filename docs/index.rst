
pywbem version |version|
************************

Overview
========

The **pywbem** PyPI package provides a WBEM client, written in pure Python.

This package is based on the idea that a good WBEM client should be easy to use
and not necessarily require a large amount of programming knowledge. It is
suitable for a large range of tasks from simply poking around to writing web
and GUI applications.

Components in the package
-------------------------

The **pywbem** PyPI package provides the following components:

* a WBEM client library

  The WBEM client library provides an API for issuing operations to a WBEM
  server, using the CIM operations over HTTP (CIM-XML) protocol defined in the
  DMTF standards DSP0200 and DSP0201. See http://www.dmtf.org/standards/wbem
  for information about WBEM and these standards.

  See `WBEM client library API`_ for a description of the API.

* a WBEM listener

  The WBEM listener waits for indications (i.e. events) emitted by a WBEM
  server and provides an API for applications to register for indications.

  See `WBEM listener API`_ for a description of the API.

* WBEM utility commands

  * `mof_compiler`_ - Takes MOF files as input and creates the CIM elements
    defined in them in a WBEM server.

  * `wbemcli`_ - Provides an interactive Python environment for invoking CIM
    operations on a WBEM server.

Changes
-------

The change log is in the `NEWS <NEWS.md>`_ file.

Compatibility
-------------

The ``pywbem`` PyPI package is supported in these environments:

* on Windows, with Python 2.6, 2.7, 3.4, 3.5, and higher 3.x

* on Linux, with Python 2.6, 2.7, 3.4, 3.5, and higher 3.x

OS X has not been tested and is therefore not listed, above.
You are welcome to try it out andi
[report any issues](https://github.com/pywbem/pywbem/issues).

Special type names
------------------

This documentation uses a few special type names:

==================  ===========================================================
Type name           Meaning
==================  ===========================================================
_`unicode string`   a Unicode string type (:func:`unicode <py2:unicode>` in
                    Python 2, and :class:`py3:str` in Python 3)
_`byte string`      a byte string type (:class:`py2:str` in Python 2, and
                    :class:`py3:bytes` in Python 3). Unless otherwise
                    indicated, byte strings in pywbem are always UTF-8 encoded.
_`CIM data type`    one of the types listed in `CIM data types`_.
_`CIM object`       one of the types listed in `CIM objects`_.
==================  ===========================================================

WBEM client library API
=======================

.. automodule:: pywbem

CIM operations
--------------

.. automodule:: pywbem.cim_operations

.. autoclass:: pywbem.WBEMConnection
   :members:
   :special-members: __repr__ __str__

CIM objects
-----------

.. automodule:: pywbem.cim_obj

CIMInstanceName
^^^^^^^^^^^^^^^

.. autoclass:: pywbem.CIMInstanceName
   :members:
   :special-members: __repr__ __str__

CIMInstance
^^^^^^^^^^^

.. autoclass:: pywbem.CIMInstance
   :members:
   :special-members: __repr__ __str__

CIMClassName
^^^^^^^^^^^^

.. autoclass:: pywbem.CIMClassName
   :members:
   :special-members: __repr__ __str__

CIMClass
^^^^^^^^

.. autoclass:: pywbem.CIMClass
   :members:
   :special-members: __repr__ __str__

CIMProperty
^^^^^^^^^^^

.. autoclass:: pywbem.CIMProperty
   :members:
   :special-members: __repr__ __str__

CIMMethod
^^^^^^^^^

.. autoclass:: pywbem.CIMMethod
   :members:
   :special-members: __repr__ __str__

CIMParameter
^^^^^^^^^^^^

.. autoclass:: pywbem.CIMParameter
   :members:
   :special-members: __repr__ __str__

CIMQualifier
^^^^^^^^^^^^

.. autoclass:: pywbem.CIMQualifier
   :members:
   :special-members: __repr__ __str__

CIMQualifierDeclaration
^^^^^^^^^^^^^^^^^^^^^^^

.. autoclass:: pywbem.CIMQualifierDeclaration
   :members:
   :special-members: __repr__ __str__

Conversion functions
^^^^^^^^^^^^^^^^^^^^

This section describes conversion functions that may be useful for purposes
such as debugging.

.. autofunction:: pywbem.tocimxml

.. autofunction:: pywbem.tocimobj

CIM data types
--------------

.. automodule:: pywbem.cim_types

.. autoclass:: pywbem.CIMType
   :members:
   :special-members: __repr__

.. autoclass:: pywbem.CIMDateTime
   :members:
   :special-members: __repr__ __str__

.. autoclass:: pywbem.MinutesFromUTC
   :members:

.. autoclass:: pywbem.CIMInt
   :members:

.. autoclass:: pywbem.Uint8
   :members:

.. autoclass:: pywbem.Sint8
   :members:

.. autoclass:: pywbem.Uint16
   :members:

.. autoclass:: pywbem.Sint16
   :members:

.. autoclass:: pywbem.Uint32
   :members:

.. autoclass:: pywbem.Sint32
   :members:

.. autoclass:: pywbem.Uint64
   :members:

.. autoclass:: pywbem.Sint64
   :members:

.. autoclass:: pywbem.CIMFloat
   :members:

.. autoclass:: pywbem.Real32
   :members:

.. autoclass:: pywbem.Real64
   :members:

CIM status codes
----------------

.. automodule:: pywbem.cim_constants
   :members:

Exceptions
----------

.. autoclass:: pywbem.Error

.. autoclass:: pywbem.CIMError

.. autoclass:: pywbem.AuthError

.. autoclass:: pywbem.ConnectionError

.. autoclass:: pywbem.TimeoutError

.. autoclass:: pywbem.ParseError

MOF compiler API
================

.. automodule:: pywbem.mof_compiler
   :members:

WBEM listener API
=================

.. # TODO: This description should be moved into the irecv module once
.. #       it is included in this documentation.

The ``irecv`` Python package is a WBEM listener (indication receiver) and is
considered experimental at this point.

At this point, it is not included in the **pywbem** PyPI package, and not
covered in this documentation.

You can get it by accessing the
`irecv directory <https://github.com/pywbem/pywbem/tree/master/irecv>`_
of the PyWBEM Client project on GitHub.

WBEM utility commands
=====================

The **pywbem** PyPI package provides a number of WBEM utility commands.
They are all implemented as pure-Python scripts.

These commands are installed into the Python script directory and should
therefore be available in the command search path.

mof_compiler
------------

A MOF compiler. It compiles MOF files, and updates the repository of a WBEM
server with the result.

Invoke ``mof_compiler --help`` for a detailed help message.

.. # TODO: Replace the hint to invoke with --help by including an automatically
.. #       generated help output. Auto-generate it in the makefile.

The MOF compiler can also be invoked from programs via the `MOF compiler API`_.

The MOF compiler has a pluggable interface for the MOF repository. The default
implementation of that interface uses a WBEM server as its MOF repository.
The plug interface is also described in the `MOF compiler API`_.

wbemcli
-------

A WBEM client CLI.

It is currently implemented as an interactive shell, and is expected to morph
into a full fledged command line utility in the future.

Invoke ``wbemcli --help`` for a detailed help message.

.. # TODO: Replace the hint to invoke with --help by including an automatically
.. #       generated help output. Auto-generate it in the makefile.

The WBEM client CLI does not have an external API on its own; it is for the
most part a consumer of the `WBEM client library API`_.

