
.. _`Introduction`:

Introduction
============

.. _`Components in the package`:

Components in the package
-------------------------

The **pywbem** PyPI package provides the following components:

* WBEM client library

  The WBEM client library provides an API for issuing WBEM operations to a
  WBEM server, using the CIM operations over HTTP (CIM-XML) protocol defined
  in the DMTF standards :term:`DSP0200` and :term:`DSP0201`.

  See :ref:`WBEM client library API` for a description of the API.

* WBEM listener

  The WBEM listener waits for indications (i.e. events) emitted by a WBEM
  server using the CIM-XML protocol. It provides an API for applications to
  subscribe to such indications.

  See :ref:`WBEM listener API` for a description of the API.

* WBEM utility commands

  * :ref:`mof_compiler` - A MOF compiler that takes MOF files as input and
    creates, updates or removes CIM instances, classes or qualifier types in a
    CIM repository.

    See :term:`DSP0004` for a description of MOF (Managed Object Format).

    The MOF compiler has an API for using it from within a program.

    By default, the CIM repository used by the MOF compiler is in a WBEM
    server. The MOF compiler API provides for plugging in your own CIM
    repository the compiler can work against.

    See :ref:`MOF compiler API` for a description of the API.

  * :ref:`wbemcli` - A WBEM command line interface that provides an interactive
    Python environment for issuing WBEM operations to a WBEM server.

.. _`Compatibility`:

Compatibility
-------------

The ``pywbem`` PyPI package is supported in these environments:

* on Windows, with Python 2.6, 2.7, 3.4, 3.5, and higher 3.x

* on Linux, with Python 2.6, 2.7, 3.4, 3.5, and higher 3.x

OS X has not been tested and is therefore not listed, above. You are welcome to
try it out and `report any issues <https://github.com/pywbem/pywbem/issues>`_.

.. _'Special type names`:

Special type names
------------------

This documentation uses a few special terms to refer to Python types:

.. glossary::

   string
      a :term:`unicode string` or a :term:`byte string`

   unicode string
      a Unicode string type (:func:`unicode <py2:unicode>` in
      Python 2, and :class:`py3:str` in Python 3)

   byte string
      a byte string type (:class:`py2:str` in Python 2, and
      :class:`py3:bytes` in Python 3). Unless otherwise
      indicated, byte strings in pywbem are always UTF-8 encoded.

   number
      one of the number types :class:`py:int`, :class:`py2:long` (Python 2
      only), or :class:`py:float`.

   integer
      one of the integer types :class:`py:int` or :class:`py2:long` (Python 2
      only).

   callable
      a type for callable objects (e.g. a function, calling a class returns a
      new instance, instances are callable if they have a
      :meth:`~py:object.__call__` method).

   Element
      class ``xml.dom.minidom.Element``. Its methods are described in section
      :ref:`py:dom-element-objects` of module :mod:`py:xml.dom`, with
      minidom specifics described in section :ref:`py:minidom-objects` of
      module :mod:`py:xml.dom.minidom`.

   CIM data type
      one of the types listed in :ref:`CIM data types`.

   CIM object
      one of the types listed in :ref:`CIM objects`.

.. _`References`:

References
----------

.. glossary::

   DSP0004
      `DMTF DSP0004, CIM Infrastructure, Version 2.8 <http://www.dmtf.org/standards/published_documents/DSP0004_2.8.pdf>`_

   DSP0200
      `DMTF DSP0200, CIM Operations over HTTP, Version 1.4 <http://www.dmtf.org/standards/published_documents/DSP0200_1.4.pdf>`_

   DSP0201
      `DMTF DSP0201, Representation of CIM in XML, Version 2.4 <http://www.dmtf.org/standards/published_documents/DSP0201_2.4.pdf>`_

   DSP0207
      `DMTF DSP0207, WBEM URI Mapping, Version 1.0 <http://www.dmtf.org/standards/published_documents/DSP0207_1.0.pdf>`_

   X.509
      `ITU-T X.509, Information technology - Open Systems Interconnection - The Directory: Public-key and attribute certificate frameworks <http://www.itu.int/rec/T-REC-X.509/en>`_

   RFC3986
      `IETF RFC3986, Uniform Resource Identifier (URI): Generic Syntax, January 2005 <https://tools.ietf.org/html/rfc3986>`_

   RFC6874
      `IETF RFC6874, Representing IPv6 Zone Identifiers in Address Literals and Uniform Resource Identifiers, February 2013 <https://tools.ietf.org/html/rfc6874>`_
