
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

   connection id
      a string (:term:`string`) that uniquely identifies each
      :class:`pywbem.WBEMConnection` object created. The connection id is
      immutable and is accessible from
      :attr:`pywbem.WBEMConnection.conn_id`. It is included in of each log
      record created for pywbem log output and may be used to correlate pywbem
      log records for a single connection.

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

   hashable
      a hashable object. Hashability requires an object not only to be able to
      produce a hash value with the :func:`py:hash` function, but in addition
      that objects that are equal (as per the ``==`` operator) produce equal
      hash values, and that the produced hash value remains unchanged across
      the lifetime of the object. See `term "hashable"
      <https://docs.python.org/3/glossary.html#term-hashable>`_
      in the Python glossary, although the definition there is not very crisp.
      A more exhaustive discussion of these requirements is in
      `"What happens when you mess with hashing in Python"
      <https://www.asmeurer.com/blog/posts/what-happens-when-you-mess-with-hashing-in-python/>`_
      by Aaron Meurer.

   unchanged-hashable
      an object that is :term:`hashable` with the exception that its hash value
      may change over the lifetime of the object. Therefore, it is hashable
      only for periods in which its hash value remains unchanged.
      :ref:`CIM objects` are examples of unchanged-hashable objects in pywbem.

   DeprecationWarning
      a standard Python warning that indicates a deprecated functionality.
      See section :ref:`Deprecation and compatibility policy` and the standard
      Python module :mod:`py:warnings` for details.

   Element
      class ``xml.dom.minidom.Element``. Its methods are described in section
      :ref:`py:dom-element-objects` of module :mod:`py:xml.dom`, with
      minidom specifics described in section :ref:`py:minidom-objects` of
      module :mod:`py:xml.dom.minidom`.

   CIM data type
      one of the types listed in :ref:`CIM data types`.

   CIM object
      one of the types listed in :ref:`CIM objects`.

   keybindings input object
      a Python object used as input for initializing an ordered list of
      keybindings in a parent object (i.e. a :class:`~pywbem.CIMInstanceName`
      object).

      `None` will result in an an empty list of keybindings.

      Otherwise, the type of the input object must be one of:

      * iterable of :class:`~pywbem.CIMProperty`
      * iterable of tuple(key, value)
      * :class:`~py:collections.OrderedDict` with key and value
      * :class:`py:dict` with key and value (will not preserve order)

      with the following definitions for key and value:

      * key (:term:`string`):
        Keybinding name.

        Must not be `None`.

        The lexical case of the string is preserved. Object comparison
        and hash value calculation are performed case-insensitively.

      * value (:term:`CIM data type` or :term:`number` or :class:`~pywbem.CIMProperty`):
        Keybinding value.

        If specified as :term:`CIM data type` or :term:`number`, the provided
        object will be stored unchanged as the keybinding value.

        If specified as a :class:`~pywbem.CIMProperty` object, its `name`
        attribute must match the key (case insensitively), and a copy of its
        value (a :term:`CIM data type`) will be stored as the keybinding value.

        `None` for the keybinding value will be stored unchanged.

      The order of keybindings in the parent object is preserved if the input
      object is an iterable or a :class:`~py:collections.OrderedDict` object,
      but not when it is a :class:`py:dict` object.

      The resulting set of keybindings in the parent object is independent of
      the input object (except for unmutable objects), so that subsequent
      modifications of the input object by the caller do not affect the parent
      object.

   methods input object
      a Python object used as input for initializing an ordered list of
      methods represented as :class:`~pywbem.CIMMethod` objects in a parent
      object that is a :class:`~pywbem.CIMClass`.

      `None` will result in an an empty list of methods.

      Otherwise, the type of the input object must be one of:

      * iterable of :class:`~pywbem.CIMMethod`
      * iterable of tuple(key, value)
      * :class:`~py:collections.OrderedDict` with key and value
      * :class:`py:dict` with key and value (will not preserve order)

      with the following definitions for key and value:

      * key (:term:`string`):
        Method name.

        Must not be `None`.

        The lexical case of the string is preserved. Object comparison
        and hash value calculation are performed case-insensitively.

      * value (:class:`~pywbem.CIMMethod`):
        Method declaration.

        Must not be `None`.

        The `name` attribute of the :class:`~pywbem.CIMMethod` object must
        match the key (case insensitively).

        The provided object is stored in the parent object without making a
        copy of it.

      The order of methods in the parent object is preserved if the input
      object is an iterable or a :class:`~py:collections.OrderedDict` object,
      but not when it is a :class:`py:dict` object.

      The resulting set of methods in the parent object is independent of the
      input collection object, but consists of the same
      :class:`~pywbem.CIMMethod` objects that were provided in the input
      collection. Therefore, a caller must be careful to not accidentally
      modify the provided :class:`~pywbem.CIMMethod` objects.

   parameters input object
      a Python object used as input for initializing an ordered list of
      parameters represented as :class:`~pywbem.CIMParameter` objects in a
      parent object that is a :class:`~pywbem.CIMMethod`.

      `None` will result in an an empty list of parameters.

      Otherwise, the type of the input object must be one of:

      * iterable of :class:`~pywbem.CIMParameter`
      * iterable of tuple(key, value)
      * :class:`~py:collections.OrderedDict` with key and value
      * :class:`py:dict` with key and value (will not preserve order)

      with the following definitions for key and value:

      * key (:term:`string`):
        Parameter name.

        Must not be `None`.

        The lexical case of the string is preserved. Object comparison
        and hash value calculation are performed case-insensitively.

      * value (:class:`~pywbem.CIMParameter`):
        Parameter (declaration).

        Must not be `None`.

        The `name` attribute of the :class:`~pywbem.CIMParameter` object must
        match the key (case insensitively).

        The provided object is stored in the parent object without making a
        copy of it.

      The order of parameters in the parent object is preserved if the input
      object is an iterable or a :class:`~py:collections.OrderedDict` object,
      but not when it is a :class:`py:dict` object.

      The resulting set of parameters in the parent object is independent of
      the input collection object, but consists of the same
      :class:`~pywbem.CIMParameter` objects that were provided in the input
      collection. Therefore, a caller must be careful to not accidentally
      modify the provided :class:`~pywbem.CIMParameter` objects.

   properties input object
      a Python object used as input for initializing an ordered list of
      properties represented as :class:`~pywbem.CIMProperty` objects, in a
      parent object.

      The :class:`~pywbem.CIMProperty` objects represent property values when
      the parent object is a :class:`~pywbem.CIMInstance`, and property
      declarations when the parent object is a :class:`~pywbem.CIMClass`.

      `None` will result in an an empty list of properties.

      Otherwise, the type of the input object must be one of:

      * iterable of :class:`~pywbem.CIMProperty`
      * iterable of tuple(key, value)
      * :class:`~py:collections.OrderedDict` with key and value
      * :class:`py:dict` with key and value (will not preserve order)

      with the following definitions for key and value:

      * key (:term:`string`):
        Property name.

        Must not be `None`.

        The lexical case of the string is preserved. Object comparison
        and hash value calculation are performed case-insensitively.

      * value (:term:`CIM data type` or :class:`~pywbem.CIMProperty`):
        Property (value or declaration).

        Must not be `None`.

        :class:`~pywbem.CIMProperty` objects can be used as input for both
        property values and property declarations. :term:`CIM data type`
        objects can only be used for property values.

        If specified as a :term:`CIM data type`, a new
        :class:`~pywbem.CIMProperty` object will be created from the provided
        value, inferring its CIM data type from the provided value.

        If specified as a :class:`~pywbem.CIMProperty` object, its `name`
        attribute must match the key (case insensitively), and the provided
        object is stored in the parent object without making a copy of it.

      The order of properties in the parent object is preserved if the input
      object is an iterable or a :class:`~py:collections.OrderedDict` object,
      but not when it is a :class:`py:dict` object.

      The resulting set of properties in the parent object is independent of
      the input collection object, but consists of the same
      :class:`~pywbem.CIMProperty` objects that were provided in the input
      collection. Therefore, a caller must be careful to not accidentally
      modify the provided :class:`~pywbem.CIMProperty` objects.

   qualifiers input object
      a Python object used as input for initializing an ordered list of
      qualifiers represented as :class:`~pywbem.CIMQualifier` objects in a
      parent object (e.g. in a :class:`~pywbem.CIMClass` object).

      `None` will result in an an empty list of qualifiers.

      Otherwise, the type of the input object must be one of:

      * iterable of :class:`~pywbem.CIMQualifier`
      * iterable of tuple(key, value)
      * :class:`~py:collections.OrderedDict` with key and value
      * :class:`py:dict` with key and value (will not preserve order)

      with the following definitions for key and value:

      * key (:term:`string`):
        Qualifier name.

        Must not be `None`.

        The lexical case of the string is preserved. Object comparison
        and hash value calculation are performed case-insensitively.

      * value (:term:`CIM data type` or :class:`~pywbem.CIMQualifier`):
        Qualifier (value).

        Must not be `None`.

        If specified as a :term:`CIM data type`, a new
        :class:`~pywbem.CIMQualifier` object will be created from the provided
        value, inferring its CIM data type from the provided value.

        If specified as a :class:`~pywbem.CIMQualifier` object, its `name`
        attribute must match the key (case insensitively), and the provided
        object is stored in the parent object without making a copy of it.

      The order of qualifiers in the parent object is preserved if the input
      object is an iterable or a :class:`~py:collections.OrderedDict` object,
      but not when it is a :class:`py:dict` object.

      The resulting set of qualifiers in the parent object is independent of
      the input collection object, but consists of the same
      :class:`~pywbem.CIMQualifier` objects that were provided in the input
      collection. Therefore, a caller must be careful to not accidentally
      modify the provided :class:`~pywbem.CIMQualifier` objects.


.. _`Profile advertisement methodologies`:

Profile advertisement methodologies
-----------------------------------

This section briefly explains the profile advertisement methodologies defined
by DMTF. A full description can be found in :term:`DSP1033`.

These methodologies describe how a client can discover the central instances
of a management profile. Discovering the central instances through a management
profile is the recommended approach for clients, over simply enumerating a CIM
class of choice. The reason is that this approach enables clients to work
seamlessly with different server implementations, even when they have
implemented a different set of management profiles.

DMTF defines three profile advertisement methodologies in :term:`DSP1033`:

* GetCentralInstances methodology (new in :term:`DSP1033` 1.1)
* Central class methodology
* Scoping class methodology

At this point, the GetCentralInstances methodology has not widely been
implemented, but pywbem supports it nevertheless.

All three profile advertisement methodologies start from the
`CIM_RegisteredProfile` instance that identifies the management profile, by
means of registered organisation, registered name, and registered version.

It is important to understand that the `CIM_RegisteredProfile` instance not
only identifies the management profile, but represents a particular use of the
management profile within its scoping profiles. For an autonomous profile,
there are no scoping profiles, so in that case, there is only one use of the
autonomous profile in a server. However, component profiles do have scoping
profiles, and it is well possible that a component profile is used multiple
times in a server, in different scoping contexts. If that is the case, and if
discovery of central instances using any of the profile advertisement
methodologies is supposed to work, then each such use of the profile needs to
have its own separate `CIM_RegisteredProfile` instance, because each such
use of the profile will also have its own separate set of central instances.

Unfortunately, neither the DMTF standards nor the SMI-S standards are clear
about that requirement, and so there are plenty of implementations that
share a single `CIM_RegisteredProfile` instance identifying a particular
component profile, for multiple distinct uses of the profile by its scoping
profiles. In such a case, the profile advertisement methodologies will
not be able to distinguish the distinct sets of central instances alone,
and other means need to be used to distinguish them.

It is also important to understand that the choice which profile advertisement
methodology to implement, is done by the WBEM server side. Therefore, a WBEM
client such as pywbem needs to support all methodologies and needs to try them
one by one until one succeeds. Pywbem tries the three methodologies in the
order listed above.

In the *GetCentralInstances methodology*, the `CIM_RegisteredProfile` instance
has a CIM method named `GetCentralInstances` that returns the instance paths
of the central instances of the use of the profile.

In the *central class methodology*, the `CIM_RegisteredProfile` instance
is associated directly with the set of central instances of the use of the
profile, via a `CIM_ElementConformsToProfile` association.

In the *scoping class methodology*, the `CIM_RegisteredProfile` instance
is not associated directly with the set of central instances of the use of the
profile, but delegates that to its scoping profile.
The client navigates up to the `CIM_RegisteredProfile` instance representing
the (use of the) scoping profile, looks up its central instances, and
from each of those, navigates down along the reversed scoping path to the
central instances of the profile in question. The scoping path of a component
profile describes the traversal across associations and ordinary classes from
the central class to the scoping class of the profile. This profile
advertisement methodology is obviously the most complex one of the three.

Pywbem encapsulates the complexity and choice of these methodologies into
a single invocation of an easy-to use method
:meth:`~pywbem.WBEMServer.get_central_instances`.

Profile implementations in a WBEM server are not entirely free when making a
choice of which methodology to implement:

* Autonomous profiles in a WBEM server must implement the central class
  methodology, and may in addition implement the new GetCentralInstances
  methodology.

  Note that the scoping class methodology falls together with the
  central class methodology for autonomous profiles, because their scoping
  class is also their central class.

* Component profiles in a WBEM server may implement the central class
  methodology and the new GetCentralInstances methodology, and must support the
  scoping class methodology.

  Note that implementing the scoping class methodology in a WBEM server
  requires implementing the classes and associations of the scoping path,
  which are usually mandatory anyway. So while the scoping class methodology
  is more complex to use for clients than the central class methodology, it is
  easier to implement for servers.

Use of the scoping class methodology by a client requires knowing the central
class, scoping class and scoping path defined by the component profile.

:term:`DSP1001` requires that conformant autonomous profiles specify a central
class, and that conformant component profiles specify a central class, scoping
class and a scoping path.

Older DMTF component profiles and older SNIA subprofiles do not always specify
scoping class and scoping path. In such cases, the scoping class and scoping
path can often be determined from the class diagram in the specification for
the profile.
Many times, CIM_System or CIM_ComputerSystem is the scoping class.


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
For more details, see
:ref:`Prerequisite operating system packages for development`.

Installation fails with "invalid command 'bdist_wheel'"
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The installation of M2Crypto and probably other Python packages requires the
Python "wheel" package. If that package is not installed in the current Python
environment, the installation will fail with the following (or similar)
symptom::

    Creating library build\temp.win-amd64-2.7\Release\SWIG_m2crypto.lib and object build\temp.win- amd64-2.7\Release\SWIG_m2crypto.exp
    python setup.py bdist_wheel
    usage: setup.py [global_opts] cmd1 [cmd1_opts] [cmd2 [cmd2_opts] ...]
    or: setup.py --help [cmd1 cmd2 ...]
    or: setup.py --help-commands
    or: setup.py cmd --help
    error: invalid command 'bdist_wheel'

To fix this, install the Python "wheel" package::

    pip install wheel


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
      `DMTF DSP0004, CIM Infrastructure, Version 2.8 <https://www.dmtf.org/standards/published_documents/DSP0004_2.8.pdf>`_

   DSP0200
      `DMTF DSP0200, CIM Operations over HTTP, Version 1.4 <https://www.dmtf.org/standards/published_documents/DSP0200_1.4.pdf>`_

   DSP0201
      `DMTF DSP0201, Representation of CIM in XML, Version 2.4 <https://www.dmtf.org/standards/published_documents/DSP0201_2.4.pdf>`_

   DSP0207
      `DMTF DSP0207, WBEM URI Mapping, Version 1.0 <https://www.dmtf.org/standards/published_documents/DSP0207_1.0.pdf>`_

   DSP0212
      `DMTF DSP0212, Filter Query Language, Version 1.0.1 <https://www.dmtf.org/standards/published_documents/DSP0212_1.0.1.pdf>`_

   DSP1001
      `DMTF DSP1001, Management Profile Specification Usage Guide, Version 1.1 <https://www.dmtf.org/standards/published_documents/DSP1001_1.1.pdf>`_

   DSP1033
      `DMTF DSP1033, Profile Registration Profile, Version 1.1 <https://www.dmtf.org/standards/published_documents/DSP1033_1.1.pdf>`_

   DSP1054
      `DMTF DSP1054, Indications Profile, Version 1.2 <https://www.dmtf.org/standards/published_documents/DSP1054_1.2.pdf>`_

   DSP1092
      `DMTF DSP1092, WBEM Server Profile, Version 1.0 <https://www.dmtf.org/standards/published_documents/DSP1092_1.0.pdf>`_

   X.509
      `ITU-T X.509, Information technology - Open Systems Interconnection - The Directory: Public-key and attribute certificate frameworks <https://www.itu.int/rec/T-REC-X.509/en>`_

   RFC2616
      `IETF RFC2616, Hypertext Transfer Protocol -- HTTP/1.1, June 1999 <https://tools.ietf.org/html/rfc2616>`_

   RFC2617
      `IETF RFC2617, HTTP Authentication: Basic and Digest Access Authentication, June 1999 <https://tools.ietf.org/html/rfc2617>`_

   RFC3986
      `IETF RFC3986, Uniform Resource Identifier (URI): Generic Syntax, January 2005 <https://tools.ietf.org/html/rfc3986>`_

   RFC6874
      `IETF RFC6874, Representing IPv6 Zone Identifiers in Address Literals and Uniform Resource Identifiers, February 2013 <https://tools.ietf.org/html/rfc6874>`_

   WBEM Standards
      `DMTF WBEM Standards <https://www.dmtf.org/standards/wbem>`_

   Python Glossary
      * `Python 2.7 Glossary <https://docs.python.org/2.7/glossary.html>`_
      * `Python 3.4 Glossary <https://docs.python.org/3.4/glossary.html>`_
