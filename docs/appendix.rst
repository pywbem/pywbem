
.. _`Appendix`:

Appendix
========

This section contains information that is referenced from other sections,
and that does not really need to be read in sequence.


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
      a callable object; for example a function, a class (calling it returns a
      new object of the class), or an object with a :meth:`~py:object.__call__`
      method.

   DeprecationWarning
      a standard Python warning that indicates a deprecated functionality.
      See section :ref:`Deprecation policy` and the standard Python module
      :mod:`py:warnings` for details.

   Element
      class ``xml.dom.minidom.Element``. Its methods are described in section
      :ref:`py:dom-element-objects` of module :mod:`py:xml.dom`, with
      minidom specifics described in section :ref:`py:minidom-objects` of
      module :mod:`py:xml.dom.minidom`.

   CIM data type
      one of the types listed in :ref:`CIM data types`.

   CIM object
      one of the types listed in :ref:`CIM objects`.


.. _`Troubleshooting`:

Troubleshooting
---------------

Here are some trouble shooting hints for the installation of pywbem.

AttributeError for NullHandler during mkvirtualenv on Python 2.6
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If the `mkvirtualenv` command fails on Python 2.6 with this error::

    File "/usr/lib/python2.6/site-packages/stevedore/__init__.py", line 23,
      in <module> LOG.addHandler(logging.NullHandler())
    AttributeError: 'module' object has no attribute 'NullHandler'

then the `stevedore` PyPI package is too recent(!) The owners of that
package spent effort to remove the previously existing Python 2.6 support in
some steps, starting with stevedore v1.10.

The solution is to use stevedore v1.9. Note that for virtualenvwrapper to use
it, it must be installed into the system Python:

    $ sudo pip install stevedore==1.9

TypeError about StreamHandler argument 'stream' during mkvirtualenv on Python 2.6
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If the `mkvirtualenv` command fails on Python 2.6 with this error::

    File "/usr/lib/python2.6/site-packages/virtualenvwrapper/hook_loader.py",
      line 101, in main
    console = logging.StreamHandler(stream=sys.stderr)
    TypeError: __init__() got an unexpected keyword argument 'stream'

then the `virtualenvwrapper` PyPI package is too old. As of its released
version v4.7.1, a fix for that is in the master branch of its repository and
has not been released yet.

While a new version of `virtualenvwrapper` with the fix is not yet released,
a solution is to clone the `virtualenvwrapper` repository and to install it
from its working directory. Note that it must be installed into the system
Python::

    $ git clone https://bitbucket.org/dhellmann/virtualenvwrapper.git virtualenvwrapper
    $ cd virtualenvwrapper
    $ sudo python setup.py install

Swig error 'Unrecognized option -builtin' during M2Crypto install
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

On Python 2.x, pywbem uses the `M2Crypto` package from PyPI and installs it
during its own installation. The M2Crypto package invokes the Swig tool during
its installation. If the version of Swig is too old, the invocation of Swig
fails with::

    swig error : Unrecognized option -builtin

The solution is to use Swig v2.0 or higher.

The pywbem setup script checks the version of Swig and installs a newer version
of Swig, or if not available builds Swig from its sources (while automatically
installing any further OS-level prerequisites needed for building Swig).

gcc does not find Python.h while installing M2Crypto
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

On Python 2.x, pywbem uses the `M2Crypto` package from PyPI and installs it
during its own installation. The M2Crypto package invokes the Swig tool during
its installation. Swig invokes the gcc compiler on source code it produces.
That source code needs the Python.h header file.

If the invocation of gcc fails with::

    SWIG/_m2crypto_wrap.c:127:20: fatal error: Python.h: No such file or directory

then you do not have the Python.h header file available.

The installation of pywbem with OS-level prereqs (see :ref:`Installation`)
installs the necessary Python SDK package for C/C++ (or displays its package
name). On RHEL, the missing package is `python-dev`.
For more details, see :ref:`Prerequisite operating system packages`.

.. _'Glossary`:

Glossary
--------

.. glossary::

   dynamic indication filter
   dynamic filter
      An indication filter in a WBEM server whose life cycle is managed by a
      client.
      See :term:`DSP1054` for an authoritative definition and for details.

   static indication filter
   static filter
      An indication filter in a WBEM server that pre-exists and whose life
      cycle cannot be managed by a client.
      See :term:`DSP1054` for an authoritative definition and for details.


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

   DSP0212
      `DMTF DSP0212, Filter Query Language, Version 1.0.1 <http://www.dmtf.org/standards/published_documents/DSP0212_1.0.1.pdf>`_

   DSP1033
      `DMTF DSP1033, Profile Registration Profile, Version 1.1 <http://www.dmtf.org/standards/published_documents/DSP1033_1.1.pdf>`_

   DSP1054
      `DMTF DSP1054, Indications Profile, Version 1.2 <http://www.dmtf.org/standards/published_documents/DSP1054_1.2.pdf>`_

   X.509
      `ITU-T X.509, Information technology - Open Systems Interconnection - The Directory: Public-key and attribute certificate frameworks <http://www.itu.int/rec/T-REC-X.509/en>`_

   RFC2616
      `IETF RFC2616, Hypertext Transfer Protocol -- HTTP/1.1, June 1999 <https://tools.ietf.org/html/rfc2616>`_

   RFC2617
      `IETF RFC2617, HTTP Authentication: Basic and Digest Access Authentication, June 1999 <https://tools.ietf.org/html/rfc2617>`_

   RFC3986
      `IETF RFC3986, Uniform Resource Identifier (URI): Generic Syntax, January 2005 <https://tools.ietf.org/html/rfc3986>`_

   RFC6874
      `IETF RFC6874, Representing IPv6 Zone Identifiers in Address Literals and Uniform Resource Identifiers, February 2013 <https://tools.ietf.org/html/rfc6874>`_

   WBEM Standards
      `DMTF WBEM Standards <http://www.dmtf.org/standards/wbem>`_

   Python Glossary
      * `Python 2.7 Glossary <https://docs.python.org/2.7/glossary.html>`_
      * `Python 3.4 Glossary <https://docs.python.org/3.4/glossary.html>`_
