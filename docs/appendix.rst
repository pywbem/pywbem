
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

This section describes some trouble shooting hints for the installation of
pywbem.

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


.. index:: pair; troubleshooting: OpenSSL
.. index:: pair; installation fail: OpenSSL

NotOpenSSLWarning: urllib3 v2.0 only supports OpenSSL 1.1.1+
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. index:: pair; installation fail: NotOpenSSLWarning
.. index:: pair; troubleshooting: NotOpenSSLWarning

This issue is probably caused by the dependent Python package urllib3 update to
version 2.0 in pywbem version 1.7.0. In this case probably the local OS
environment includes a version of OpenSSL less than 2.0 or another SSL
implementation.

See :ref:`ConnectionError raised with SSL UNSUPPORTED_PROTOCOL` for
more information.


.. _ConnectionError raised with SSL UNSUPPORTED_PROTOCOL:

ConnectionError raised with SSL UNSUPPORTED_PROTOCOL
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. index:: pair; troubleshooting: OpenSSL
.. index:: pair; SSL: OpenSSL
.. index:: single LibreSSL
.. index:: single: TLS
.. index:: pair; UNSUPPORTED_PROTOCOL: OpenSSL

On newer versions of the operating system running the pywbem client,
communication with the WBEM server may fail with an exception similar to::

    pywbem.exceptions.ConnectionError: SSL error <class 'ssl.SSLError'>:
      [SSL: UNSUPPORTED_PROTOCOL] unsupported protocol (_ssl.c:1056)

This error means that the WBEM server side SSL implementation does not yet support
TLS 1.2 or higher or that the SSL library (OpenSSL or LibreSSL) used
by pywbem does not support TLS 1.2 and the other side requires TLS >= 1.2.

See the Python document
`https://peps.python.org/pep-0644/ <PEP 644 – Require OpenSSL 1.1.1 or newer>`_
for more information on Python and OpenSSL version 1.1.1.

In pywbem version 1.7.0 the urllib3 configuration version limit was modified to
allow urllib3 package versions >= 2.0.  These new versions of urllib3 include backward
incompatible changes including:

* Support limiting the minimum TLS version to >= 1.2 (i.e OpenSSL version >= 1.1.1). If
  the version of OpenSSL is less than 1.1.1, this SSLError will occur with the
  initial request to the WBEM Server.
* Limit the SSL library implementations to just OpenSSL and some versions of
  LibreSSL.  The  version 2.0+ urllib3 implementation does not support any
  other implementations of SSL.

This also happens after an upgrade of the client OS to Debian buster
using Python 3.7, with OpenSSL 1.1.1d.

This is an error that is created by the SSL library (normally OpenSSL or
LibreSSL) and handed back up to the SSL module of Python which hands it up to
pywbem. The error indicates that OpenSSL and the WBEM server do not agree about
which SSL/TLS protocol level to use.

Pywbem specifies SSL parameters such that the highest SSL/TLS protocol version
is used that both the client and server support. Pywbem itself does not put any
additional TLS version restrictions on top of SSL library.

Debian buster includes OpenSSL 1.1.1d and increased its security settings to
require at least TLS 1.2 (see `https://stackoverflow.com/a/53065682/1424462`).

This issue can possibly be corrected by:

1. If the current version of urllib3 is less than 2.0 (``pip list``), update
   the version of urllib3 (ex. ``pip install --upgrade  --upgrade-strategy
   eager urllib3``). to a later version. This is required because pip install
   does not force an eager update of packages; if a valid previous version (
   i.e. any version in the range defined by the dev-requirements.txt file) of
   urllib3 exists it will not be upgraded to 2.0+ in the reinstallation of
   pywbem.

2. If the current version of urllib3 is greater than 2.0, the previous version
   of urllib3 (ex. version 1.26.5) can be installed (ex. ``pip install
   urllib3<2.0``).

3. Adding TLS 1.2 support to the WBEM server side (preferred) or lowering the
   minimum TLS level required on the client side (which lowers security). With
   OpenSSL the latter can be done by changing the ``MinProtocol`` parameter in
   the OpenSSL config file on the client OS (typically ``/etc/ssl/openssl.cnf``
   on Linux and OS-X, and ``C:\OpenSSL-Win64\openssl.cnf`` on Windows).

   At the end of the file there is::

        [system_default_sect]
        MinProtocol = TLSv1.2
        CipherString = DEFAULT@SECLEVEL=2

4. If the issue is the use of LibreSSL (ex. MacOS) as the OS level SSL
   implementation, the issue may be that urllib3 before version 2.0.3 did not
   support LibreSSL.  See `urllib3 issue <https://github.com/urllib3/urllib3/issues/3020>`_
   for discussion of this issue.


ConnectionError raised with [SSL] EC lib
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. index:: pair: installation failure; ConnectionError raises with

Using pywbem on Python 3.5 with OpenSSL 1.0.1e-fips against an IBM DS8000
raised the following exception::

    pywbem.exceptions.ConnectionError: SSL error <class 'ssl.SSLError'>:
      [SSL] EC lib (_ssl.c:728)

This is an error that is created by the OpenSSL library and handed back up to
the SSL module of Python which hands it up to pywbem. The error indicates that
OpenSSL on the client side cannot deal with the cipher used by the server
side. This was fixed by upgrading OpenSSL on the client OS to version 1.1.1.

.. _`Install fails, Externally-managed-environment error`:

Install fails, Externally-managed-environment error
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. index:: pair: troubleshooting; Externally-managed-environment error
.. index:: pair: installation failure; Externally-managed-environment error

This error is caused by the OS distribution adopting the changes defined by
`Python PEP 668`_ (Marking Python base environments as “externally managed”)
which sets configuration information so that pip (version 23.0+) will only
install packages that are not part of the OS distibution into virtual
environments and will not install them into any of the system python
directories. This forces the separation of user packages from OS distribution
installed packages.

On newer versions of some operating systems (Ex. Ubuntu 23.04, Debian 12, etc.)
installed from the OS distribution, you may get an error message such as the
following which indicates that pip refused to install a package:

.. code-block:: text

        error: externally-managed-environment

    × This environment is externally managed . . .
    . . .


The best solution to this issue is to ``always`` install pywbem into a virtual
environment as recommended in the pywbem installation.

There are alernatives to allow installation of pywbem into the system python
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
