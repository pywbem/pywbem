
pywbem version |version|
************************

Overview
========

The **pywbem** PyPI package provides a WBEM client, written in pure Python.
It supports Python 2 and Python 3.

This package is based on the idea that a good WBEM client should be easy to use
and not necessarily require a large amount of programming knowledge. It is
suitable for a large range of tasks from simply poking around to writing web
and GUI applications.

This is the API documentation of the **pywbem** PyPI package. Its general web
site is: http://pywbem.github.io/pywbem/index.html.

Components in the package
-------------------------

The **pywbem** PyPI package provides the following components:

* a WBEM client library

  The WBEM client library provides an API for issuing WBEM operations to a WBEM
  server, using the CIM operations over HTTP (CIM-XML) WBEM protocol defined in
  the DMTF standards `DSP0200`_ and `DSP0201`_.
  See http://www.dmtf.org/standards/wbem  for information about WBEM and these
  standards.

  See `WBEM client library API`_ for a description of the API.

* a WBEM listener

  The WBEM listener waits for indications (i.e. events) emitted by a WBEM
  server and provides an API for applications to register for indications.

  See `WBEM listener API`_ for a description of the API.

* WBEM utility commands

  * `mof_compiler`_ - Takes MOF files as input and creates the CIM elements
    defined in them in a WBEM server.

  * `wbemcli`_ - Provides an interactive Python environment for issuing
    operations to a WBEM server.

Changes
-------

The change log is in the `pywbem/NEWS.md <NEWS.md>`_ file.

Compatibility
-------------

The ``pywbem`` PyPI package is supported in these environments:

* on Windows, with Python 2.6, 2.7, 3.4, 3.5, and higher 3.x

* on Linux, with Python 2.6, 2.7, 3.4, 3.5, and higher 3.x

OS X has not been tested and is therefore not listed, above. You are welcome to
try it out and `report any issues <https://github.com/pywbem/pywbem/issues>`_.

Special type names
------------------

This documentation uses a few special terms to refer to Python types:

==================  ===========================================================
Type term           Meaning
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

WBEM operations
---------------

.. automodule:: pywbem.cim_operations

.. autoclass:: pywbem.WBEMConnection
   :members:
   :special-members: __str__, __repr__

.. # TODO: Requesting all members (by means of :members: without a list
.. # of members) causes the internal methods imethodcall() and methodcall()
.. # also to be generated. However, specifying a list of members in order
.. # to exclude these two methods causes the special members also not to be
.. # shown. It seems the least evil at this point to have both shown,
.. # and to document that the two low-level functions are not part of the
.. # external API.
.. # List of members to specify for :members: (once it works):
.. #         EnumerateInstanceNames, EnumerateInstances, GetInstance,
.. #         ModifyInstance, CreateInstance, DeleteInstance, AssociatorNames,
.. #         Associators, ReferenceNames, References, InvokeMethod,
.. #         ExecQuery, EnumerateClassNames, EnumerateClasses, GetClass,
.. #         ModifyClass, CreateClass, DeleteClass, EnumerateQualifiers,
.. #         GetQualifier, SetQualifier, DeleteQualifier

CIM objects
-----------

.. automodule:: pywbem.cim_obj

CIMInstanceName
^^^^^^^^^^^^^^^

.. autoclass:: pywbem.CIMInstanceName
   :members:
   :special-members: __str__, __repr__

CIMInstance
^^^^^^^^^^^

.. autoclass:: pywbem.CIMInstance
   :members:
   :special-members: __str__, __repr__

CIMClassName
^^^^^^^^^^^^

.. autoclass:: pywbem.CIMClassName
   :members:
   :special-members: __str__, __repr__

CIMClass
^^^^^^^^

.. autoclass:: pywbem.CIMClass
   :members:
   :special-members: __str__, __repr__

CIMProperty
^^^^^^^^^^^

.. autoclass:: pywbem.CIMProperty
   :members:
   :special-members: __str__, __repr__

CIMMethod
^^^^^^^^^

.. autoclass:: pywbem.CIMMethod
   :members:
   :special-members: __str__, __repr__

CIMParameter
^^^^^^^^^^^^

.. autoclass:: pywbem.CIMParameter
   :members:
   :special-members: __str__, __repr__

CIMQualifier
^^^^^^^^^^^^

.. autoclass:: pywbem.CIMQualifier
   :members:
   :special-members: __str__, __repr__

CIMQualifierDeclaration
^^^^^^^^^^^^^^^^^^^^^^^

.. autoclass:: pywbem.CIMQualifierDeclaration
   :members:
   :special-members: __str__, __repr__

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
   :special-members: __str__, __repr__

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

.. autoclass:: pywbem.mof_compiler.MOFCompiler
   :members:
   :special-members: __str__, __repr__

.. autoclass:: pywbem.mof_compiler.MOFParseError
   :members:
   :special-members: __str__, __repr__

.. autoclass:: pywbem.mof_compiler.BaseRepositoryConnection
   :members:
   :special-members: __str__, __repr__

.. autoclass:: pywbem.mof_compiler.MOFWBEMConnection
   :members:
   :special-members: __str__, __repr__

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

.. include:: mof_compiler.help.txt
 	 :literal:

The MOF compiler can also be invoked from programs via the `MOF compiler API`_.

The MOF compiler has a pluggable interface for the MOF repository. The default
implementation of that interface uses a WBEM server as its MOF repository.
The plug interface is also described in the `MOF compiler API`_.

wbemcli
-------

A WBEM client CLI.

It is implemented as an interactive shell.

.. include:: wbemcli.help.txt
 	 :literal:

The WBEM client CLI does not have an external API on its own; it is for the
most part a consumer of the `WBEM client library API`_.

References
==========

* _`DSP0004`:
  `DMTF DSP0004, CIM Infrastructure, Version 2.8 <http://www.dmtf.org/standards/published_documents/DSP0004_2.8.pdf>`_
* _`DSP0200`:
  `DMTF DSP0200, CIM Operations over HTTP, Version 1.4 <http://www.dmtf.org/standards/published_documents/DSP0200_1.4.pdf>`_
* _`DSP0201`:
  `DMTF DSP0201, Representation of CIM in XML, Version 2.4 <http://www.dmtf.org/standards/published_documents/DSP0201_2.4.pdf>`_
* _`DSP0207`:
  `DMTF DSP0207, WBEM URI Mapping, Version 1.0 <http://www.dmtf.org/standards/published_documents/DSP0207_1.0.pdf>`_
* _`X.509`:
  `ITU-T X.509, Information technology - Open Systems Interconnection - The Directory: Public-key and attribute certificate frameworks <http://www.itu.int/rec/T-REC-X.509/en>`_

