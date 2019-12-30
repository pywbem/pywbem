
.. _`Introduction`:

Introduction
============

.. contents:: Chapter Contents
   :depth: 2


.. _`Functionality`:

Functionality
-------------

Pywbem supports the following functionality:

* :ref:`WBEM client library API`

  This API supports issuing WBEM operations to a WBEM server, using the CIM
  operations over HTTP (CIM-XML) protocol defined in the DMTF standards
  :term:`DSP0200` and :term:`DSP0201`.

* :ref:`WBEM server API`

  This API encapsulates certain functionality of a WBEM server for use by a
  WBEM client application, such as determining the Interop namespace of the
  server, or the management profiles advertised by the server.

* :ref:`WBEM indication API`

  This API supports starting and stopping a WBEM listener that waits for
  indications (i.e. events) emitted by a WBEM server using the CIM-XML
  protocol. The API also supports managing subscriptions for such indications.

* :ref:`MOF compiler API`

  This API provides for invoking the MOF compiler and for plugging in your own
  CIM repository into the MOF compiler.

* :ref:`WBEM utility commands`

  Pywbem includes a few utility commands:

  * :ref:`mof_compiler`

    A MOF compiler that takes MOF files as input and updates the CIM repository
    of a WBEM server with the result. See :term:`DSP0004` for a definition of
    MOF.


.. _`Supported environments`:

Supported environments
----------------------

Pywbem is supported in these environments:

* Operating Systems: Linux, OS-X, native Windows, UNIX-like environments
  under Windows (such as `CygWin`_, MSYS2, Babun, or Gow).

* Python: 2.7, 3.4, and higher

* WBEM servers: Any WBEM server that conforms to the DMTF specifications listed
  in :ref:`Standards conformance`. WBEM servers supporting older versions of
  these standards are also supported, but may have limitations.
  See :ref:`WBEM servers` for more details.

.. _`CygWin`: https://cygwin.org/


.. _`Installation`:

Installation
------------

Pywbem is a pure Python package and therefore does not have a dependency on
operating system packages in addition to Python itself.

* Prerequisites:

  - The Python environment into which you want to install must be the current
    Python environment, and must have at least the following Python packages
    installed:

    - setuptools
    - wheel
    - pip

* Install pywbem (and its prerequisite Python packages) into the active Python
  environment:

  .. code-block:: bash

      $ pip install pywbem

  This will also install any prerequisite Python packages.

  Since version 1.0.0, pywbem has no more OS-level prerequisite packages.

If you want to contribute to the pywbem project, you need to set up a
development and test environment for pywbem. That has a larger set of Python
package prerequisites and also OS-level prerequisites. Its setup is described
in chapter :ref:`Development`.


.. _`Installing into a different Python environment`:

Installing into a different Python environment
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The examples in the previous sections install pywbem and its prerequisite
Python packages using the Pip utility. By default, Pip installs these packages
into the currently active Python environment. That can be the system Python, or
a virtual Python. The commands shown above did not detail this, but this
section does.

If you just want to use the scripts that come with pywbem, and want them to be
always available without having to think about activating virtual Python
environments, then installation of pywbem into the system Python environment
is probably the right choice for you. If your intention is to write code
against the pywbem APIs, installation into a `virtual Python environment`_ is
recommended.

.. _virtual Python environment: https://docs.python-guide.org/en/latest/dev/virtualenvs/

An additional dimension is Python 2 vs. Python 3:

* On systems where Python 2 is the default, the ``python`` and ``pip`` commands
  operate on Python 2. There may be ``python3`` and ``pip3`` commands that
  operate on Python 3.

* On some newer systems (e.g. Ubuntu 17.04), Python 3 is the default. In that
  case, the ``python`` and ``pip`` commands operate on Python 3. There may be
  ``python2`` and ``pip2`` commands that operate on Python 2.

For simplicity, the following examples show only the default commands.

* To install pywbem into the currently active virtual Python environment (e.g.
  ``myenv``), issue:

  .. code-block:: bash

      (myenv)$ pip install pywbem

* To install pywbem for only the current user into the currently active system
  Python environment, issue:

  .. code-block:: bash

      $ pip install --user pywbem

  This installs the Python packages in a directory under the home directory of
  the current user and therefore does not require sudo permissions nor does
  it modify the system Python environment seen by other users.

* To install pywbem for all users into the currently active system Python
  environment, issue:

  .. code-block:: bash

      $ sudo pip install pywbem

  This installs the Python packages into a directory of the system Python
  installation and therefore requires sudo permissions.

  Be aware that this may replace the content of existing packages when a
  package version is updated. Such updated packages as well as any newly
  installed packages are not known by your operating system installer, so the
  knowledge of your operating system installer is now out of sync with the
  actual set of packages in the system Python.

  Therefore, this approach is not recommended and you should apply this
  approach only after you have thought about how you would maintain these
  Python packages in the future.


.. _`Installing a different version of pywbem`:

Installing a different version of pywbem
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The examples in the previous sections install the latest version of pywbem that
is released on `PyPI`_. This section describes how different versions of pywbem
can be installed.

* To install the latest version of pywbem that is released on PyPI, issue:

  .. code-block:: bash

      $ pip install pywbem

* To install an older released version of pywbem, Pip supports specifying a
  version requirement. The following example installs pywbem version 0.10.0
  from PyPI:

  .. code-block:: bash

      $ pip install pywbem==0.10.0

* If you need to get a certain new functionality or a new fix of pywbem that is
  not yet part of a version released to PyPI, Pip supports installation from a
  Git repository. The following example installs pywbem from the current code
  level in the master branch of the `pywbem Git repository`_:

  .. code-block:: bash

      $ pip install git+https://github.com/pywbem/pywbem.git@master#egg=pywbem

.. _pywbem Git repository: https://github.com/pywbem/pywbem

.. _PyPI: https://pypi.python.org/pypi


.. _`Verifying the installation`:

Verifying the installation
^^^^^^^^^^^^^^^^^^^^^^^^^^

You can verify that pywbem is installed correctly by importing the package into
Python (using the Python environment you installed pywbem to):

.. code-block:: bash

    $ python -c "import pywbem; print('ok')"
    ok

In case of trouble with the installation, see the :ref:`Troubleshooting`
section.


.. _`Prerequisite operating system packages for install`:

Prerequisite operating system packages for install
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The installation of pywbem before its version 1.0.0 required certain operating
system packages. Version 1.0.0 of pywbem has no more dependencies on
specific operating system packages (other than Python).

Note that the development of pywbem still requires a number of operating
system packages. See :ref:`Setting up the development environment` for details.


.. _`Package version`:

Package version
---------------

Since pywbem 0.8.1, the version of the pywbem package can be accessed by
programs using the ``pywbem.__version__`` variable:

.. autodata:: pywbem._version.__version__

Note: For tooling reasons, the variable is shown as
``pywbem._version.__version__``, but it should be used as
``pywbem.__version__``.

From earlier versions of pywbem, pywbem 0.7.0 was the only version released to
Pypi, and most likely also the only version that was packaged as an operating
system package into Linux distributions.

The following shell command can be used to determine the version of pywbem, for
all versions that were released to Pypi, and independently of whether pywbem
was installed as an operating system package or as a Python package::

    python -c "\
    import pywbem, os, subprocess; \
    fs=os.path.join(os.path.dirname(pywbem.__file__),'setup.py'); \
    vs=subprocess.check_output(['python',fs,'--version']).strip() \
    if os.path.exists(fs) else None; \
    v=getattr(pywbem, '__version__', vs if vs else '0.7.0-assumed'); \
    print(v) \
    "

.. _`Version dependent features`:

Version dependent features
--------------------------

.. automodule:: pywbem._features
   :members:


.. _`Standards conformance`:

Standards conformance
---------------------

The pywbem client and pywbem indication listener conform to the following
CIM and WBEM standards, in the version specified when following the links
to the standards:

* The implementation of the CIM-XML protocol in pywbem (client and
  listener) conforms to :term:`DSP0200` and :term:`DSP0201`.

  Limitations:

  - The mock support of pywbem (see :ref:`Mock support`) does not support the
    ``ModifyClass`` operation. Note that in its implementation of the CIM-XML
    protocol, pywbem does support the ``ModifyClass`` operation.

  - The ``EnumerationCount`` operation is not supported by pywbem. That
    operation is optional for WBEM servers to support, and is hard to
    implement reasonably.

  - Multi-requests are not supported by pywbem. This is not a functional
    limitation though, because the use of multi-requests is entirely
    determined by the client: If a client does not use multi-requests,
    the server does not use multi-responses.

  - :term:`DSP0201` version 2.4 introduced the requirement that the TYPE
    attribute of the KEYVALUE element must be set. The KEYVALUE element is used
    to represent keys in instance names, for example when the CreateInstance
    operation returns an instance name from the WBEM server, or when the
    DeleteInstance operation sends an instance name to the WBEM server.
    In operation requests sent to the WBEM server, pywbem sets the TYPE
    attribute of the KEYVALUE element for key properties of CIM types string
    and boolean, as required by DSP0201 version 2.4. For key properties with
    numeric CIM types, pywbem does not set the TYPE attribute of the KEYVALUE
    element in operation requests. This conforms to DSP0201 before version 2.4,
    but not to version 2.4. This is not expected to cause problems however,
    because WBEM servers that implement DSP0201 version 2.4 very likely will
    tolerate clients that conform to earlier versions. In operation responses
    received from the WBEM server, pywbem tolerates an absent TYPE attribute
    in KEYVALUE elements in order to accomodate WBEM servers that implement
    DSP0201 before version 2.4.

  Notes:

  - The CIM-XML representation as defined in :term:`DSP0201` supports CIM
    methods that have a void return type. However, the CIM architecture
    defined in :term:`DSP0004` does not support that, and neither does pywbem.

  - The CIM-XML representation as defined in :term:`DSP0201` supports
    references to CIM classes. However, the CIM architecture defined in
    :term:`DSP0004` does not support that, and neither does pywbem.

* The CIM-XML representation of :ref:`CIM objects` as produced by their
  ``tocimxml()`` and ``tocimxmlstr()`` methods conforms to the representations
  for these objects as defined in :term:`DSP0201`.

  Limitations:

  - The `xml:lang` attribute supported by :term:`DSP0201` on some CIM-XML
    elements that can have string values is tolerated in the CIM-XML received
    by pywbem, but is ignored and is not represented on the corresponding
    :ref:`CIM objects`.

* The capabilities of :ref:`CIM objects` conform to the CIM architecture as
  defined in :term:`DSP0004`.

* The MOF as produced by the ``tomof()`` methods on :ref:`CIM objects` and as
  parsed by the MOF compiler conforms to the MOF syntax as defined in
  :term:`DSP0004`.

  Limitations:

  - The pywbem MOF compiler has the restriction that CIM instances specified in
    MOF that have an alias must have key properties that are either initialized
    in the instance, or have non-NULL default values (issue #1079).

  - The pywbem MOF compiler has the restriction that an alias must be defined
    before it is used. In the MOF syntax defined in :term:`DSP0004`, no such
    restriction exists (issue #1078).

  - The pywbem MOF compiler does not roll back changes to qualifier
    declarations when it aborts (issue #990).

* The WBEM URIs produced by the ``to_wbem_uri()`` methods of
  :class:`~pywbem.CIMInstanceName` and :class:`~pywbem.CIMClassName` conform to
  the WBEM URI syntax as defined in :term:`DSP0207`.

  Note that the ``__str__()`` methods of these two classes produce strings that
  are similar but not conformant to :term:`DSP0207`, for historical reasons.

* The mechanisms for discovering the Interop namespace of a WBEM server and the
  management profiles advertised by a WBEM server and their central instances
  in the :ref:`WBEM server API` conform to :term:`DSP1033`.

* The mechanisms for subscribing for CIM indications in the
  :ref:`WBEM indication API` conform to :term:`DSP1054`.


.. _`Deprecation and compatibility policy`:

Deprecation and compatibility policy
------------------------------------

Since version 0.7.0, pywbem attempts to be as backwards compatible as
possible.

Compatibility of pywbem is always seen from the perspective of the user of the
pywbem APIs or pywbem utility commands. Thus, a backwards compatible new
version of pywbem means that a user can safely upgrade to that new version
without encountering compatibility issues for their code using the pywbem APIs
or for their scripts using the pywbem utility commands.

Having said that, there is always the possibility that even a bug fix changes
some behavior a user was dependent upon. Over time, the pywbem project has put
automated regression testing in place that tests the behavior at the APIs,
but such compatibility issues cannot be entirely excluded.

Pywbem uses the rules of `Semantic Versioning 2.0.0`_ for compatibility
between versions, and for deprecations. The public interface that is subject to
the semantic versioning rules and specificically to its compatibility rules are
the various pywbem APIs described in this documentation, and the command line
interface of the pywbem utility commands.

.. _Semantic Versioning 2.0.0: https://semver.org/spec/v2.0.0.html

Occasionally functionality needs to be retired, because it is flawed and a
better but incompatible replacement has emerged. In pywbem, such changes are
done by deprecating existing functionality, without removing it immediately.
The deprecated functionality is still supported at least throughout new minor
or update releases within the same major release. Eventually, a new major
release may break compatibility by removing deprecated functionality.

Any changes at the pywbem APIs or utility commands that do introduce
incompatibilities as defined above, are described in the :ref:`Change log`.

Deprecation of functionality at the pywbem APIs or utility commands is
communicated to the users in multiple ways:

* It is described in the documentation of the API or utility command

* It is mentioned in the change log.

* It is raised at runtime by issuing Python warnings of type
  ``DeprecationWarning`` (see the Python :mod:`py:warnings` module).

Since Python 2.7, ``DeprecationWarning`` messages are suppressed by default.
They can be shown for example in any of these ways:

* By specifying the Python command line option: ``-W default``
* By invoking Python with the environment variable: ``PYTHONWARNINGS=default``

It is recommended that users of the pywbem package run their test code with
``DeprecationWarning`` messages being shown, so they become aware of any use of
deprecated functionality.

Here is a summary of the deprecation and compatibility policy used by pywbem,
by release type:

* New update release (M.N.U -> M.N.U+1): No new deprecations; no new
  functionality; backwards compatible.
* New minor release (M.N.U -> M.N+1.0): New deprecations may be added;
  functionality may be extended; backwards compatible.
* New major release (M.N.U -> M+1.0.0): Deprecated functionality may get
  removed; functionality may be extended or changed; backwards compatibility
  may be broken.


.. _'Python namespaces`:

Python namespaces
-----------------

The external APIs of pywbem are defined by the symbols in the ``pywbem``
namespace. That is the only Python namespace that needs to be imported by
users.

With pywbem versions prior to v0.8, it was common for users to import the
sub-modules of pywbem (e.g. ``pywbem.cim_obj``). The sub-modules that existed
prior to v0.8 are still available for compatibility reasons.
Starting with v0.8, the ``pywbem`` namespace was cleaned up, and not all public
symbols available in the sub-module namespaces are available in the ``pywbem``
namespace anymore. The symbols in the sub-module namespaces are still available
for compatibility, including those that are no longer available in the
``pywbem`` namespace. However, any use of symbols from the sub-module namespaces
is deprecated starting with v0.8, and you should assume that a future version of
pywbem will remove them. If you miss any symbol you were used to use, please
`open an issue <https://github.com/pywbem/pywbem/issues>`_.

New sub-modules added since pywbem v0.8 have a leading underscore in their name
in order to document that they are considered an implementation detail and that
they should not be imported by users.

With pywbem versions prior to v0.11, the :ref:`MOF compiler API` was only
available in the ``pywbem.mof_compiler`` namespace. Starting with pywbem
version v0.11, it is also available in the ``pywbem`` namespace and should be
used from there.

This documentation describes only the external APIs of pywbem, and omits any
internal symbols and any sub-modules.


.. _`Configuration variables`:

Configuration variables
-----------------------

.. automodule:: pywbem.config
      :members:


.. _`WBEM Servers`:

WBEM servers
------------

Server-specific features
^^^^^^^^^^^^^^^^^^^^^^^^

Pywbem supports the following features of some specific WBEM servers that are
additions to the DMTF standards:

1. `OpenPegasus <https://collaboration.opengroup.org/pegasus/>`_

   - Pywbem supports the Interop namespace ``root/PG_InterOp`` that is specific
     to OpenPegasus. OpenPegasus also supports the standard Interop namespaces
     (``interop``, ``root/interop``) but for backwards compatibility with
     earlier versions of OpenPegasus, pywbem supports this old Interop
     namespace, for example in its Interop namespace determination whose result
     is exposed in the :attr:`pywbem.WBEMServer.interop_ns` property.

   - Pywbem supports the upper-case variant ``EMBEDDEDOBJECT`` of the respective
     CIM-XML attribute that is specific to some releases of OpenPegasus, in
     addition to the mixed-case variant ``EmbeddedObject`` that is defined in the
     :term:`DSP0201` standard and that is also supported by OpenPegasus. Older
     releases of OpenPegasus supported only the upper-case variant.

   - Pywbem supports a connection to an OpenPegasus server using Unix Domain
     Sockets through its :class:`~pywbem.PegasusUDSConnection` subclass of
     :class:`~pywbem.WBEMConnection`.

2. `SFCB (Small Footprint CIM Broker) <https://sourceforge.net/projects/sblim/files/sblim-sfcb/>`_

   - Pywbem supports a connection to an SFCB server using Unix Domain
     Sockets through its :class:`~pywbem.SFCBUDSConnection` subclass of
     :class:`~pywbem.WBEMConnection`.

3. `OpenWBEM <https://sourceforge.net/projects/openwbem/>`_

   - Pywbem supports the `OWlocal` authentication extension of OpenWBEM, which
     is a password-less local authorization.

   - Pywbem supports a connection to an OpenWBEM server using Unix Domain
     Sockets through its :class:`~pywbem.OpenWBEMUDSConnection` subclass of
     :class:`~pywbem.WBEMConnection`.


WBEM server testing
^^^^^^^^^^^^^^^^^^^

Today the pywbem project tests primarily against current versions of the
OpenPegasus WBEM server because that server is available to the project.

These tests are captured in the test script ``run_cimoperations.py``. Note that
generally those tests that are server-specific only run against the defined
server so that there are a number of tests that run only against the
OpenPegasus server. This includes some tests that use specific providers
in the OpenPegasus server to set up tests such as indication tests.
