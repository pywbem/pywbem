
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

   CIM namespace
      an object that is accessible through a WBEM server and is a naming
      space for CIM classes, CIM instances and CIM qualifier declarations.
      The namespace is a component of other elements like namespace path used
      to access objects in the WBEM server.

   NocaseList
      A case-insensitive list class provided by the
      `nocaselist package <https://pypi.org/project/nocaselist/>`_.

   interop namespace
      A :term:`CIM namespace`  is the interop namespace if it has one of the
      following names: DMTF definition; ('interop', 'root/interop') pywbem
      implementation; ('interop', 'root/interop', 'root/PG_Interop'),
      Only one interop namespace is allowed in a WBEM Server. The interop
      namespace contains CIM classes that the client needs to discover
      characteristics of the WBEM server (namespaces, coniguration of server
      components like indications) and the registered profiles implemented by
      that server.

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

        If the WBEM server requires the TYPE attribute on KEYVALUE elements to
        be set in operation requests, this can be achieved by specifying the
        keybinding value as :term:`CIM data type` (either directly, or via
        a :class:`~pywbem.CIMProperty` object).

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

   provider
      An element of a WBEM server that responds to requests for selected
      classes. A WBEM server normally contains a main provider that may
      interface with a CIM respository and provides responses to client
      requests for which no specific provider is defined and providers which
      providers that allow specialized responses for selected classes and
      request types (communicate with managed components) or manipulate the
      objects being managed.

      NOTE: In the SNIA terminology, a provider may also be a complete
      WBEM server implementation.

   user-defined provider
      A :term:provider that can be defined independently of the WBEM server
      and attached dynamically to the WBEM server.  In pywbem, user-defined
      providers can be defined as subclasses of specific default provider
      types and attached to the server by registering them with the
      connection.

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

This section describes some trouble shooting hints for the installation and
execution of pywbem.

Installation fails with "invalid command 'bdist_wheel'"
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. index:: pair; installation fail: invalid command
.. index:: pair; troubleshooting: "invalid command 'bdist_wheel'"

The installation of some Python packages requires the Python "wheel" package.
If that package is not installed in the current Python environment, the
installation will fail with the following (or similar) symptom::

    python setup.py bdist_wheel
    usage: setup.py [global_opts] cmd1 [cmd1_opts] [cmd2 [cmd2_opts] ...]
    or: setup.py --help [cmd1 cmd2 ...]
    or: setup.py --help-commands
    or: setup.py cmd --help
    error: invalid command 'bdist_wheel'

To fix this, install the Python "wheel" package::

    pip install wheel


.. _`Issues with pywbem verson 1.7+, Urllib3 package version 2, and SSL`:

Issues with pywbem verson 1.7+, Urllib3 package version 2, and SSL
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. _`Overview of the changes and issues`:

Overview of the changes and issues
""""""""""""""""""""""""""""""""""

.. index:: pair; troubleshooting: OpenSSL
.. index:: pair; SSL: OpenSSL
.. index:: pair; UNSUPPORTED_PROTOCOL: OpenSSL

Pywbem version 1.7 expanded the urllib3 package version requirement to include
urllib3 version >= 2.0. Note that urllib3 version 2.0 was allowed with previous
version of pywbem only because the package version requirements did not pin
urllib version to < 2.0.

The urlib3 package version requirements in requirements.txt are::

      urllib3>=1.26.18; python_version >= '3.7'  (pywbem 1.7.0)

previously::

      urllib3>=1.26.18,<2.0.0; python_version >= '3.7' (pywbem 1.6.x)


The urllib3 Python package version 2.0 made a significant number of changes
including the following list that can be potentially non-compatible:

* Urllib3 >= 2.0 limits the minimum OpenSSL version >= 1.1.1. Note that
  Python 3.10 also limits the minimum OpenSSL version >= 1.1.1.

* Urllib3 >= 2.0 changes the default minimum TLS version to TLS 1.2 (previously
  was TLS 1.0), the default minimum defined for OpenSSL 1.1.1.

* Urllib3 >= 2.0 removed support for LibreSSL, WolfSSL and other non OpenSSL
  implementations.  Multiple operating systems including: macOS and BSD use
  LibreSSL as the TLS/SSL implementation. LibreSSL support however, was
  restored to urllib3 in version 2.0.3.

* Urllib3 >= 2.0 changed the minimum version for Python to Python 3.7.

* Urllib3 >= 2.0 removed the default set of TLS ciphers, instead now urllib3
  uses the list of ciphers configured by the system.

This means that pywbem exceptions can occur during installation, update of pywbem
or the underlying platform because:

* Level of minimum TLS protocol support depends on the Python Version and the
  SSL implementation version.

* SSL compatibility issues can happen with new pywbem installations on some
  platforms or updates to the OS platforms or to pywbem.

Pywbem uses the requests dependent package which uses the urllib3 package which
uses the  Python openssl module to communicate with OpenSSL; neither pywbem nor the
requests package pins the urllib3 package to versions below version 2.0. This
is a function of the SSL implementation and urllib3 package version.

Python version 3.10+ already requires OpenSSL version 1.1.1 or higher
independent of the use of urllib3 version 2.0+ and pywbem version 1.6 allowed
urllib3 version 2.0+ simply because it was released before that urllib3 version
was released.

Because of this pywbem change to allow urllib3 >= 2.0, Warnings, Exceptions,
etc. can occur in the process of:

* pywbem package installation
* pywbem package update ( ie. updating urllib3)
* Update to use a different version of Python, ex. Python 3.6 to a newer Python version
* OS update which changes the SSL implementation version
* Pywbem attempting to communicate with a WBEM server where the server may
  not implement the new TLS version requirement.

The following documents present more information on this change to urllib3 and
the issues and possible corrections:

* PYTHONPEP644_

* `Urllib3 migration guide <https://urllib3.readthedocs.io/en/stable/v2-migration-guide.html>`_

* `macOS issues with Urllib3 - urllib3 issue 3024 <https://github.com/urllib3/urllib3/issues/3020>`_

* `urllib3 issue 2168, Drop support for OpenSSL\<1.1.1 <https://github.com/urllib3/urllib3/issues/2168>`_

The current version and implementation  of the SSL library can be determined
as follows::

  $ python -c "import ssl; print(ssl.OPENSSL_VERSION)"
  OpenSSL 1.1.1  7 Feb 2023

or::

  $ python -c "import ssl; print(ssl.OPENSSL_VERSION)"
  LibreSSL 2.8.3

OpenSSL version can be directly determined from OpenSSL as follows::

    $ openssl version
    OpenSSL 3.0.2 15 Mar 2022 (Library: OpenSSL 3.0.2 15 Mar 2022)

The current urllib3 installed version can be determined with pip::

  $ pip list | grep urllib3
  urllib3                       2.2.1

The server TLS version can be verified with the OpenSSL CLI tool::

    openssl s_client -connect localhost:15989 -XXXX

    where: XXXX is tls1_1, tls1_2
    and a certificate is returned if the corresponding TLS version is valid.

The following subsections define specific issues that can occur with this
change and proposed solutions.

* :ref:`NotOpenSSLWarning: urllib3 v2.0 only supports OpenSSL 1.1.1+`
* :ref:`ConnectionError raised with [SSL] EC lib`
* :ref:`ConnectionError raised with [SSL: UNSUPPORTED_PROTOCOL]`
* :ref:`ImportError urllib3 v2.0 only supports OpenSSL 1.1.1+`

.. _PYTHONPEP644: Python PEP 644 – Require OpenSSL 1.1.1 or newer <https://peps.python.org/pep-0644/>


.. _`NotOpenSSLWarning: urllib3 v2.0 only supports OpenSSL 1.1.1+`:

NotOpenSSLWarning: urllib3 v2.0 only supports OpenSSL 1.1.1+
""""""""""""""""""""""""""""""""""""""""""""""""""""""""""""

.. index:: pair; installation fail: NotOpenSSLWarning
.. index:: pair; troubleshooting: NotOpenSSLWarning

This issue may be caused by the urllib3 package update to version 2.0
in pywbem version 1.7.0. In this case it is probably that the local environment
includes a version of OpenSSL less than 1.1.1 The best options is to
reinstall urllib3 < 2.0


.. _`ConnectionError raised with [SSL] EC lib`:

ConnectionError raised with [SSL] EC lib
""""""""""""""""""""""""""""""""""""""""
.. index:: pair: installation failure; ConnectionError raises with

Using pywbem on Python 3.5 with OpenSSL 1.0.1e-fips against an IBM DS8000
raised the following exception::

    pywbem.exceptions.ConnectionError: SSL error <class 'ssl.SSLError'>:
      [SSL] EC lib (_ssl.c:728)

This error indicates that OpenSSL on the client side cannot deal with the
cipher used by the server side. This was fixed by upgrading OpenSSL on the
client OS to version 1.1.1.

.. _`ConnectionError raised with [SSL: UNSUPPORTED_PROTOCOL]`:

ConnectionError raised with [SSL: UNSUPPORTED_PROTOCOL]
"""""""""""""""""""""""""""""""""""""""""""""""""""""""

.. index:: pair; troubleshooting: OpenSSL
.. index:: pair; SSL: OpenSSL
.. index:: pair; UNSUPPORTED_PROTOCOL: OpenSSL

On newer versions of the operating system running the pywbem client,
communication with the WBEM server may fail with::

    pywbem.exceptions.ConnectionError: SSL error <class 'ssl.SSLError'>:
      [SSL: UNSUPPORTED_PROTOCOL] unsupported protocol (_ssl.c:1056)

This error indicates that OpenSSL and the WBEM server do not agree about which
SSL/TLS protocol level to use.

This can also happened after an upgrade of the client OS to Debian buster using
Python 3.7, with OpenSSL 1.1.1d. Debian buster includes OpenSSL 1.1.1d and
increased its security settings to require at least TLS 1.2 (see
https://stackoverflow.com/a/53065682/1424462).

Pywbem specifies SSL parameters such that the highest SSL/TLS protocol version
is used that both the client and server support. Pywbem does not put any
additional SSL restrictions on top of Python or the SSL libraries.

This error means that the WBEM server side does not yet support
TLS 1.2 or higher or that the SSL library used by pywbem does not support
TLS 1.2.

This issue can be corrected by:

1. If the current version of urllib3 is less than 2.0, update the version
   of urllib3 (ex. ``pip install --upgrade  --upgrade-strategy eager
   urllib3``). Since the pywbem install does not force an eager update of
   packages, if a valid previous version of urllib3 exists it will not be
   upgraded to 2.0+ in the re-installation of pywbem.

2. If the current version of urllib3 is greater than 2.0, the previous version
   of urllib3 (ex. version 1.26.5) can be installed with, for example::

    $ pip install urllib3 < 2.0

3. Adding TLS 1.2 support to the WBEM server side (preferred) or owering the
   minimum TLS level OpenSSL requires on the client side (which lowers
   security). The latter can be done  with OpenSSL by changing the
   ``MinProtocol`` parameter in the OpenSSL config file on the client OS
   (typically ``/etc/ssl/openssl.cnf`` on Linux and OS-X,
   and ``C:\OpenSSL-Win64\openssl.cnf`` on Windows).

   At the end of the file set::

        [system_default_sect]
        MinProtocol = TLSv1.2
        CipherString = DEFAULT@SECLEVEL=2


.. _`ImportError urllib3 v2.0 only supports OpenSSL 1.1.1+`:

ImportError urllib3 v2.0 only supports OpenSSL 1.1.1+
"""""""""""""""""""""""""""""""""""""""""""""""""""""

.. index:: single LibreSSL
.. index:: pair; troubleshooting: OpenSSL
.. index:: pair; troubleshooting: LibreSSL
.. index:: LibreSSL macOS
.. index:: pair; ImportError urllib3: OpenSSL


Upgrading Python packages, with a Python that does not support
OpenSSL 1.1.1 or higher or other SSL implementations, causes an ImportError
exception raised by urllib3 such as:

    ImportError: urllib3 v2.0 only supports OpenSSL 1.1.1+, currently the ‘ssl’ module is compiled with LibreSSL 2.8.3.
    See: https://github.com/urllib3/urllib3/issues/2168

This can happen for example on macOS with the system Python of macOS as the
basis for a Python virtual environment and installing pywbem into that virtual
environment, which typically installs the latest available versions of
dependent packages, and thus may install urllib3 with a version 2.0 or later.

The ImportError exception message shows the name and version of the underlying
SSL library the Python 'ssl' module is using. On most Python systems, that is a
statically linked SSL library, so just installing OpenSSL 1.1.1 or higher does
not address the issue.

At least up to macOS Ventura, Apple compiles the system Python with LibreSSL.
As long as that does not change, you cannot use the system Python of macOS with
urllib3>=2.0; also not as a basis for Python virtual environments.

There are basically two options on how this issue can be addressed:

* Use a Python version that uses OpenSSL 1.1.1 or higher. That is the case
  for the CPython reference implementation version 3.7 or higher. CPython can
  either be downloaded from https://www.python.org/downloads/macos/ or
  installed using a third party package installer for macOS, such as Homebrew.

* Pin the urllib3 package to stay below version 2.0 when on Python 3.7 or
  higher, by specifying in the package dependencies, e.g. in the
  requirements.txt file::

    urllib3>=1.26.5,<2.0; python_version >= '3.7'

    The minimum version of urllib3 should be at least what the
    minimum-constraints.txt file of the 'pywbem' project specifies as a minimum,
    for the 'pywbem' version.

    Note that pinning a dependent package prevents installing security
    fixes, which is important for a network related package such as urllib3, so
    this option should not be the preferred one.

.. _`Install fails, Externally-managed-environment error`:

Install fails, Externally-managed-environment error
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. index:: pair: troubleshooting; Externally-managed-environment error
.. index:: pair: installation failure; Externally-managed-environment error

This error is caused by the OS distribution adopting the changes defined by
`Python PEP 668`_ (Marking Python base environments as “externally managed”)
which sets configuration information so that pip (version 23.0+) will only
install packages that are not part of the OS distibution into virtual
environments and will not install them into any of the system Python
directories. This forces the separation of user packages from OS distribution
installed packages.

On newer versions of some operating systems (Ex. Ubuntu 23.04, Debian 12, etc.)
installed from the OS distribution, you may get an error message such as the
following which indicates that pip refused to install a package::

.. code-block:: text

    error: externally-managed-environment

    × This environment is externally managed . . .
    . . .


The best solution to this issue is to ``always`` install pywbem into a virtual
environment as recommended in the pywbem :ref:`Installation` documentation.

There are alernatives to allow installation of pywbem into the system Python
directories if required including:


* Create or modify a `pip configuration file`_ to include the statement:

  .. code-block:: text

    [global]
    break-system-packages = true

* Set an environment variable BREAK_SYSTEM_PACKAGES before installing pywbem
  since environment variables can be used to define pip command line options.

* Remove the flag file that pip uses to enable the limiting behavior. See
  `Python PEP 668`_ ("Marking Python base environments as “externally managed")
  which would be most logical in the case of installation into a container such
  as Docker.

See `pywbem issue 3080 <https://github.com/pywbem/pywbem/issues/3080>`_ for
more information about this issue.

.. _Python PEP 668: https://peps.python.org/pep-0668/
.. _pip configuration file: https://pip.pypa.io/en/stable/topics/configuration/


.. _`Losing indications when sent from OpenPegasus server`:

Losing indications when sent from OpenPegasus server
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. index:: pair: troubleshooting; indication listener
.. index:: pair: losing indications; indication listener


If there is a case where the pywbem listener appears to be losing indications
sent from at least the OpenPegasus server, this may be due to timeout/retry
settings issues between the WBEM server and pywbem listener.

OpenPegasus has two configuration settings that can impact sending indications:

1. **maxIndicationDeliveryRetryAttempts** (Default 3 seconds)

   If set to a positive integer, value defines the number of times
   indication service will enable the reliableIndication feature
   and try to deliver an indication to a particular listener destination.
   This does not effect the original delivery attempt. A value of 0
   disables reliable indication feature completely, and cimserver will
   deliver the indication once.

2. **minIndicationDeliveryRetryInterval** (Default: 30 seconds).

   If set to a positive integer, this value defines the minimal time interval
   in seconds for the indication service to wait before retrying to deliver an
   indication to a listener destination that previously failed. Cimserver may
   take longer due to QoS or other processing.

Together these configuration variables try to insure that indications will be
delivered. If there is an issue sending any single indication it is put into
a delay queue for the destination along with any suceeding indications that
are created for the same destination.  After the timeout defined by the
configuration variable **minIndicationDeliveryRetryInterval**, OpenPegasus
attempts to send the indication again. It repeats this process the number of
times determined by the **maxIndicationDeliveryRetryAttempts** configuration
variable.

Thus, as a default after receiving anything but a successful response from the
listener OpenPegasus waits 30 seconds and retries. It repeats this process
3 times before discarding the indication.

As noted in pywbem issue https://github.com/pywbem/pywbem/issues/3022 tests
with OpenPegasus under high indication loading have indicated that occasionally
the WBEM server receives a zero length response immediately after sending the
indication. This is treated as
an error and the retry process is started.  If any timeouts or time checks in the
listener, (ex. very short times in tests between received indications) these
timeouts could be interpreted as lost indications when, in fact, OpenPegasus
will wait 30 seconds and then retry the indication that the server thought
had failed.

This was the case with testing against local OpenPegasus Docker containers where
the WBEM server was requested to deliver a fixed number of indications as fast
as possible but the test listener set a timeout of 3 seonds with no indication
received to indicate that the delivery has stopped before all requested
indications had been delivered. However the delay was simply waiting 30 seconds
delay before resending the failed indications.  Setting the
OpenPegasus WBEM server to different timeout times can correct this problem
(ex. delay 2 seconds, retry attempts 5 for local testing).

The OpenPegasus configuration variables can be set with the OpenPegasus ``cimconfig`` command
line utility  either when the server is running or stopped.

See the OpenPegasus documenation or OpenPegasus ``cimconfig --help`` for
detailed information on the command parameters for setting these configuation
variables.


.. _`Base classes`:

Base classes
------------

Some bases classes are included in this documentation in order to provide the
descriptions for inherited methods and properties that are referenced from the
summary tables in other class descriptions.

.. autoclass:: pywbem._exceptions._RequestExceptionMixin
    :members:
    :special-members:
    :exclude-members: __init__,__weakref__
    :autosummary:

.. autoclass:: pywbem._exceptions._ResponseExceptionMixin
    :members:
    :special-members:
    :exclude-members: __init__,__weakref__
    :autosummary:

.. autoclass:: pywbem._cim_types._CIMComparisonMixin
    :members:
    :special-members:
    :exclude-members: __init__,__weakref__
    :autosummary:

.. autoclass:: pywbem_mock.BaseRepository
    :members:
    :special-members:
    :exclude-members: __init__,__weakref__
    :autosummary:

.. autoclass:: pywbem_mock.BaseObjectStore
    :members:
    :special-members:
    :exclude-members: __init__,__weakref__
    :autosummary:

.. autoclass:: pywbem_mock.BaseProvider
    :members:
    :special-members:
    :exclude-members: __init__,__weakref__
    :autosummary:


.. _`Glossary`:

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
      * `Python 3.5 Glossary <https://docs.python.org/3.5/glossary.html>`_
