
.. _`Introduction`:

Introduction
============

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

    A MOF compiler that takes MOF files as input and creates, updates or
    removes CIM instances, classes or qualifier types in a CIM repository.

    See :term:`DSP0004` for a description of MOF (Managed Object Format).

    By default, the CIM repository used by the MOF compiler is in a WBEM
    server. The :ref:`MOF compiler API` provides for plugging in your own CIM
    repository the compiler can work against.

  * :ref:`wbemcli`

    A WBEM command line interface that provides an interactive Python
    environment for issuing WBEM operations to a WBEM server.


.. _`Installation`:

Installation
------------

Pywbem is a pure Python package and therefore does not have a dependency on
operating system packages in addition to Python itself. However, some of the
Python packages used by pywbem have dependencies on additional operating system
packages for their installation. These additional operating system packages
must be installed before the pywbem Python package can be installed.

For some environments, post-processing steps are necessary such as setting up
environment variables.

This section describes the complete installation of pywbem with all steps for
each of the supported operating systems and Linux distributions
(see `Supported environments`_ for a list of those), for installing and running
pywbem.

The setup of a development and test environment for pywbem is not covered in
this section, but in chapter :ref:`Development`.

Since pywbem 0.11, the installation of prerequisite operating system packages
can be performed by invoking the ``pywbem_os_setup.sh`` script provided by the
pywbem project. That script supports the following operating systems and
Linux distributions:

* Linux RedHat family (RHEL, CentOS, Fedora)
* Linux Debian family (Ubuntu, Debian)
* Linux SUSE family (SLES, openSUSE)
* OS-X

That script does not support Windows, so a manual setup of the prerequisite
packages is described for Windows.

For operating systems and Linux distributions not supported by the script, it
displays the list of packages that would be needed for the Linux RedHat family,
the expectation being that this can be translated into packages of your desired
operating system or Linux distribution.
If you like to see an additional operating system or Linux distribution
supported by the script,
`open an issue <https://github.com/pywbem/pywbem/issues>`_
and provide the corresponding list of package names for that environment.

The ``pywbem_os_setup.sh`` script installs the Python ``distro`` package into
the active Python environment. If your active Python environment is the
system Python environment, that package will be installed as a local package
for the current user.


.. _`Installing to Linux`:

Installing to Linux
^^^^^^^^^^^^^^^^^^^

* Download the ``pywbem_os_setup.sh`` script from one of these sources:

  - :download:`pywbem_os_setup.sh <../pywbem_os_setup.sh>` on this documentation site

  - `pywbem_os_setup.sh <https://raw.githubusercontent.com/pywbem/pywbem/master/pywbem_os_setup.sh>`_
    on master branch of pywbem repo

* Execute the script:

  .. code-block:: bash

      $ ./pywbem_os_setup.sh

  The script uses ``sudo`` under the covers, so your userid needs to have
  sudo permission.

  If Swig cannot be installed in the required version, you can build it
  yourself as described in :ref:`Building Swig`.

* In case the script reports that your Linux distribution is not supported for
  automatic installation of the prerequisite operating system packages, you
  can still try to find out what the corresponding packages are on your Linux
  distribution and install them manually. If you do, please
  `open an issue <https://github.com/pywbem/pywbem/issues>`_ so we can add
  support for that Linux distribution.

* On Linux Debian family systems with multi-architecture support (e.g. Ubuntu
  16.04), the structure of openssl header files needed by M2Crypto changed
  incompatibly. M2Crypto tries to accomodate that incompatbility by detecting
  multi-architecture support, but on Python 2.6 the interface for that was not
  yet supported. As a result, the openssl header files are not found during
  M2Crypto installation with Python 2.6.

  The following quickfix makes the multi-architecture header files available
  in a compatible way on such systems:

  .. code-block:: bash

      $ sudo ln -s /usr/include/x86_64-linux-gnu/openssl/opensslconf.h /usr/include/openssl/opensslconf.h

* Install pywbem (and its prerequisite Python packages) into the active Python
  environment:

  .. code-block:: bash

      $ pip install pywbem


.. _`Installing to OS-X`:

Installing to OS-X
^^^^^^^^^^^^^^^^^^

* Download the ``pywbem_os_setup.sh`` script from one of these sources:

  - :download:`pywbem_os_setup.sh </pywbem_os_setup.sh>` on this documentation site
  - `pywbem_os_setup.sh <https://raw.githubusercontent.com/pywbem/pywbem/master/pywbem_os_setup.sh>`_
    on master branch of pywbem repo

* Execute the script:

  .. code-block:: bash

      $ ./pywbem_os_setup.sh

  The script uses ``sudo`` under the covers, so your userid needs to have
  sudo permission.

  The script uses the ``brew`` command (Homebrew project) to install packages.

* With Python 2, the script installs the ``openssl`` package needed by the
  M2Crypto Python package. On newer OS-X releases, you may see a notice that
  the ``openssl`` package is "not linked" because the TLS implementation
  provided with OS-X is available. In that case, you need to set up the
  following environment variables for use by the pywbem package installation:

  .. code-block:: bash

      $ openssl_dir=$(brew --prefix openssl)
      $ export LDFLAGS="-L$openssl_dir/lib $LDFLAGS"
      $ export CFLAGS="-I$openssl_dir/include $CFLAGS"
      $ export SWIG_FEATURES="-I$openssl_dir/include $SWIG_FEATURES"

* Install pywbem (and its prerequisite Python packages) into the active Python
  environment:

  .. code-block:: bash

      $ pip install pywbem


.. _`Installing to Windows`:

Installing to Windows
^^^^^^^^^^^^^^^^^^^^^

The pywbem tests that run on the Appveyor CI use CygWin, but you should be able
to use plain Windows or any Unix-like environment on Windows (such as
CygWin, MinGW, Babun, or Gow).

Note that Unix-like environments on Windows bring their own Python, so double
check that the active Python environment is the one you want to install to.

Some of the steps described below depend on the bit size of the active Python
environment. You can detect that bit size as follows:

.. code-block:: bash

    > python -c "import ctypes; print(ctypes.sizeof(ctypes.c_void_p)*8)"
    64

* Install the Windows build of M2Crypto into the active Python environment:

  For a 32-bit Python environment:

  .. code-block:: bash

      > pip install M2CryptoWin32

  For a 64-bit Python environment:

  .. code-block:: bash

      > pip install M2CryptoWin64

  Note that these Python packages are binary builds and therefore do not invoke
  Swig at their installation time. Therefore, there are no prerequisite
  OS-level packages to install.

* Install pywbem (and its prerequisite Python packages) into the active
  Python environment:

  .. code-block:: bash

      > pip install pywbem


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

.. _virtual Python environment: http://docs.python-guide.org/en/latest/dev/virtualenvs/

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
is released on `PyPI`_. This section describes how dofferent versions of pywbem
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

      $ pip install git+https://github.com/pywbem/pywbem.git@master

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

The following table lists the prerequisite operating system packages along with
their version requirements for installing and running pywbem, for the
supported operating systems and Linux distributions.

The prerequisite operating system packages for developing pywbem are not listed
in this table; you can find them in section
:ref:`Prerequisite operating system packages for development`.

+--------------------------+--------------------+----------------------+-------+
| Op.system / Distribution | Package name       | Version requirements | Notes |
+==========================+====================+======================+=======+
| Linux RedHat family      | openssl-devel      | >=1.0.1              | py2   |
| (RHEL, CentOS, Fedora)   +--------------------+----------------------+-------+
|                          | python-devel       | for your Python 2.x  | py2   |
|                          +--------------------+----------------------+-------+
|                          | gcc-c++            | >=4.4                | py2   |
|                          +--------------------+----------------------+-------+
|                          | swig               | >=2.0                | py2   |
+--------------------------+--------------------+----------------------+-------+
| Linux Debian family      | libssl-dev         | >=1.0.1              | py2   |
| (Ubuntu, Debian,         +--------------------+----------------------+-------+
| LinuxMint)               | python-dev         | for your Python 2.x  | py2   |
|                          +--------------------+----------------------+-------+
|                          | g++                | >=4.4                | py2   |
|                          +--------------------+----------------------+-------+
|                          | swig               | >=2.0                | py2   |
+--------------------------+--------------------+----------------------+-------+
| Linux SUSE family        | openssl-devel      | >=1.0.1              | py2   |
| (SLES, openSUSE)         +--------------------+----------------------+-------+
|                          | python-devel       | for your Python 2.x  | py2   |
|                          +--------------------+----------------------+-------+
|                          | gcc-c++            | >=4.4                | py2   |
|                          +--------------------+----------------------+-------+
|                          | swig               | >=2.0                | py2   |
+--------------------------+--------------------+----------------------+-------+
| OS-X                     | openssl            | >=1.0.1              | py2   |
|                          +--------------------+----------------------+-------+
|                          | gcc                | >=4.4                | py2   |
|                          +--------------------+----------------------+-------+
|                          | swig               | >=2.0                | py2   |
+--------------------------+--------------------+----------------------+-------+
| Windows                  | None               |                      |       |
+--------------------------+--------------------+----------------------+-------+

Notes:

* py2: Only needed with Python 2 (not needed with Python 3).


.. _`Building Swig`:

Building Swig
^^^^^^^^^^^^^

The installation of M2Crypto needs the Swig utility (e.g. ``swig`` package
on RedHat). On some Linux distributions, the Swig utility is not available in
the required version. In such cases, it can be built from its sources, as
follows:

1. Install the PCRE development packages:

   * ``pcre-devel`` package on Linux RedHat and SUSE families
   * ``libpcre3`` and ``libpcre3-dev`` packages on Linux Debian family

2. Download the source archive of Swig version 2.0 or higher, and unpack it.
   For example, using Swig version 2.0.12::

       $ wget -q -O swig-2.0.12.tar.gz http://sourceforge.net/projects/swig/files/swig/swig-2.0.12/swig-2.0.12.tar.gz/download
       $ tar -xf swig-2.0.12.tar.gz

3. Configure and build Swig::

       $ cd swig-2.0.12
       $ ./configure --prefix=/usr
       $ make swig

4. Install Swig (for all users of the system)::

       $ sudo make install

5. Verify the installation and the version of Swig::

       $ swig -version
       SWIG Version 2.0.12


.. _`Package version`:

Package version
---------------

The version of the pywbem package can be accessed by programs using the
``pywbem.__version__`` variable:

.. autodata:: pywbem._version.__version__

Note: For tooling reasons, the variable is shown as
``pywbem._version.__version__``, but it should be used as
``pywbem.__version__``.


.. _`Compatibility`:
.. _`Supported environments`:

Supported environments
----------------------

Pywbem is supported in these environments:

* Operating Systems: Linux, Windows, OS-X
* Python: 2.6, 2.7, 3.4, 3.5, 3.6

Limitations:

* On Windows, pywbem is not supported on Python 2.6, because M2Crypto in the
  M2CryptoWin32/64 package does not support Python 2.6.

* On Windows, pywbem has not been tested on 64-bit versions of Python, because
  the libxslt etc. development packages needed to install lxml that are used
  do not provide the link libraries in the format needed by lxml. Because
  lxml is only used for development and test of pywbem, just running pywbem on
  64-bit versions of Windows may or may not work.


.. _`Standards conformance`:

Standards conformance
---------------------

Pywbem conforms to the following CIM and WBEM standards, in the version
specified when following the links to the standards:

* The supported WBEM protocol is CIM-XML; it conforms to :term:`DSP0200` and
  :term:`DSP0201`.

* The CIM-XML representation of :ref:`CIM objects` as produced by their
  ``tocimxml()`` and ``tocimxmlstr()`` methods conforms to :term:`DSP0201`.

* The MOF as produced by the ``tomof()`` methods on :ref:`CIM objects` and as
  parsed by the MOF compiler conforms to :term:`DSP0004`.

  Limitations:

  - Several `issues in the MOF compiler
    <https://github.com/pywbem/pywbem/issues?utf8=%E2%9C%93&q=is%3Aissue+is%3Aopen+MOF>`_.

* The implemented CIM metamodel (e.g. in the :ref:`CIM objects`) conforms to
  :term:`DSP0004`.

* The WBEM URIs produced by the :meth:`pywbem.CIMInstanceName.__str__` and
  :meth:`pywbem.CIMClassName.__str__` methods conform to :term:`DSP0207`.

* The mechanisms for discovering the Interop namespace of a WBEM server and the
  management profiles advertised by a WBEM server and their central instances
  in the :ref:`WBEM server API` conform to :term:`DSP1033`.

* The mechanisms for subscribing for CIM indications in the
  :ref:`WBEM indication API` conform to :term:`DSP1054`.


.. _`Deprecation policy`:

Deprecation policy
------------------

Since its v0.7.0, Pywbem attempts to be as backwards compatible as possible.

However, in an attempt to clean up some of its history, and in order to prepare
for future additions, the Python namespaces visible to users of pywbem need to
be cleaned up.

Also, occasionally functionality needs to be retired, because it is flawed and
a better but incompatible replacement has emerged.

In pywbem, such changes are done by deprecating existing functionality, without
removing it. The deprecated functionality is still supported throughout new
minor releases. Eventually, a new major release will break compatibility and
will remove the deprecated functionality.

In order to prepare users of pywbem for that, deprecation of functionality is
stated in the API documentation, and is made visible at runtime by issuing
Python warnings of type ``DeprecationWarning`` (see the Python
:mod:`py:warnings` module).

Since Python 2.7, ``DeprecationWarning`` messages are suppressed by default.
They can be shown for example in any of these ways:

* By specifying the Python command line option: ``-W default``
* By invoking Python with the environment variable: ``PYTHONWARNINGS=default``

It is recommended that users of the pywbem package run their test code with
``DeprecationWarning`` messages being shown, so they become aware of any use of
deprecated functionality.

Here is a summary of the deprecation and compatibility policy used by pywbem,
by release type:

* New update release (M.N.U -> M.N.U+1): No new deprecations; fully backwards
  compatible.
* New minor release (M.N.U -> M.N+1.0): New deprecations may be added; as
  backwards compatible as possible.
* New major release (M.N.U -> M+1.0.0): Deprecated functionality may get
  removed; backwards compatibility may be broken.

Compatibility is always seen from the perspective of the user of pywbem, so a
backwards compatible new pywbem release means that the user can safely upgrade
to that new release without encountering compatibility issues.


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

Pywbem supports communication with any WBEM server that conforms to the
DMTF specifications. See section  :ref:`Standards conformance`.

Server Specific Features
^^^^^^^^^^^^^^^^^^^^^^^^

There are some specific non-specification features that are included in
pywbem for support of WBEM server specific features including:

1. OpenWBEM server - includes support for an authentication extension
(OWLocal password-less local authorization) that is part of the OpenWBEM server.

2. OpenPegasus - includes support for the special interop namespace that may
be used in some OpenPegasus implements `root/PG_InterOp`. Most implementations
have moved to supporting the standard namespace (`interop`, 'root/interop') but
for backward compatibility, this old interop namespace name was included in
the table of namespaces that are searched by the
`WBEMServer.get_interop_namespace()` method).

3. OpenPegasus - Supports a mixed-case attribute name `EmbeddedObject` in XML
responses that was defined in error in some old versions of OpenPegasus
in addtion to the correct upper case.

4. Supports a specific Unix Domain Socket call (the name of the domanin socket)
for multiple different servers as subclasses of WBEMConnection including:

* OpenPegasus PegasusUDSConnection
* OpenWBEM - OpenWBEMUDSConnection
* SFCB(Small Footprint CIM Broker) - SFCBUDSConnection

WBEM Server Testing
^^^^^^^^^^^^^^^^^^^

Today the pywbem project tests primarily against current versions of the
OpenPegasus WBEM server because that server is available to the project.

These tests are captured in the testsuite run_cimoperations.py. Note that
generally the tests that are server specific only run against the defined
server so that there are a number of tests that run only against the
OpenPegasus server. This includes some tests that use specific providers
in the OpenPegasus server to set up tests such as indication tests.



