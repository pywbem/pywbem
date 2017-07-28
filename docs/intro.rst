
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

Pywbem is a pure Python package that can be installed from PyPi or from
its `Git repository`_ by the usual means for installing Python packages.

.. _Git repository: https://github.com/pywbem/pywbem

Some of the Python packages used by pywbem have dependencies on operating
system packages. These operating system packages must be installed before the
pywbem Python package can be installed. For details, see
`Prerequisite operating system packages`_.

Pywbem also has dependencies on other Python packages. These Python packages
will be automatically installed when installing pywbem using any of the
approaches shown below:

* Install the latest released version of pywbem (assuming the OS-level
  prerequisites are already established):

  .. code-block:: bash

      $ pip install pywbem

* Install the latest development version of pywbem (assuming the OS-level
  prerequisites are already established):

  .. code-block:: bash

      $ pip install git+https://github.com/pywbem/pywbem.git@master

These examples install pywbem and its prerequisite Python packages into the
currently active Python environment. By default, the system Python environment
is active. This is probably the right choice if you just want to use the
scripts that come with pywbem. In that case, you need to use `sudo` with the
commands shown above, and your Linux userid needs to be authorized accordingly.
If your intention is to write code against the pywbem APIs, installation into
a `virtual Python environment`_ is recommended).

.. _virtual Python environment: http://docs.python-guide.org/en/latest/dev/virtualenvs/

The command syntax above is shown for Linux, but works in similar ways on
Windows and OS-X.

In case of trouble with the installation, see the :ref:`Troubleshooting`
section.

You can verify that pywbem, its dependent Python packages and its dependent
OS-level packages are installed correctly by importing the package into
Python (using the Python environment you installed pywbem to):

.. code-block:: bash

    $ python -c "import pywbem; print('ok')"
    ok


.. _`Prerequisite operating system packages`:

Prerequisite operating system packages
--------------------------------------

Some of the Python packages used by pywbem have dependencies on operating
system packages. These operating system packages must be installed before the
pywbem Python package can be installed. This section describes how that can be
done, and documents these packages.

* For pywbem 0.11 and higher: Use ``pywbem_os_setup.sh``

  In this approach, a standalone shell script that installs the OS-level
  prerequisites is downloaded and executed.

  * The shell script needs the Python ``distro`` package installed in the
    current Python environment. If your current Python environment is a virtual
    Python environment, the shell script will install the ``distro`` package
    automatically.

    If your current Python environment is the system Python, the shell script
    does not automatically install that Python package, in order not to modify
    the system Python, and leaves that to you (including the decision whether
    to switch to a virtual Python environment and then to simply re-run the
    shell script).

  * Download the :download:`pywbem_os_setup.sh </pywbem_os_setup.sh>` shell
    script for the pywbem version you want to install, and execute that
    script:

    .. code-block:: bash

        $ ./pywbem_os_setup.sh

    The script uses ``sudo`` under the covers, so your userid needs to have
    sudo permission.

* For pywbem 0.8 to 0.10: Use ``setup.py install_os``

  In this approach, the pywbem source archive is downloaded and its
  ``setup.py`` script is executed with a pywbem-specific command
  ``install_os``.

  This approach still should work for pywbem versions higher than 0.10, but
  should not be used anymore.

  The examples are shown for pywbem version 0.8.1.

  * Download the pywbem source archive from Pypi using Pip:

    .. code-block:: bash

        $ pip download --no-deps --no-binary :all: pywbem==0.8.1

    The ability to download packages was introduced in Pip 8.0. When using an
    older Pip version, you can download the pywbem source archive from its Git
    repository:

    .. code-block:: bash

        $ curl -o pywbem-0.8.1.tar.gz -L https://github.com/pywbem/pywbem/blob/master/dist/pywbem-0.8/pywbem-0.8.1.tar.gz

    Of course, you can also download it manually from Pypi. Note that only the
    source archive (``*.tar.gz``) has the capability we use here; the binary
    archive (``*.whl``) does not have that capability.

  * Extract the pywbem source archive and run the ``install_os`` command of
    ``setup.py``:

    .. code-block:: bash

        $ tar -xzf pywbem-0.8.1.tar.gz
        $ cd pywbem-0.8.1
        $ python setup.py install_os

    The ``install_os`` command uses ``sudo`` under the covers, so your userid
    needs to have sudo permission.

    The M2Crypto Python package used by pywbem needs Swig to be installed.
    The ``install_os`` command attempts to install Swig. If no suitable version
    of Swig can be installed, the source archive of Swig is downloaded, and
    its build prerequisites are installed, and Swig is built. This is only
    necessary on very old operating systems.

* For pywbem before 0.8: Install the required packages manually, based upon
  the table shown below.

For manual installation of the prerequisite operating system packages, or for
including pywbem in distributions, the following table lists the packages and
their version requirements for the Linux distributions that are supported
by the scripts:

+----------------------------+---------------------+--------------------------+
| Distributions              | Package name        | Version requirements     |
+============================+=====================+==========================+
| RedHat, CentOS, Fedora     | openssl-devel       | >=1.0.1                  |
|                            +---------------------+--------------------------+
|                            | gcc-c++             | >=4.4                    |
|                            +---------------------+--------------------------+
|                            | python-devel        | for Python 2.6, 2.7      |
|                            +---------------------+--------------------------+
|                            | python3{N}u-devel   | for Python 3.{N} from IUS|
|                            |                     | community (python3{N}u)  |
|                            +---------------------+--------------------------+
|                            | python3{N}-devel    | for Python 3.{N} not from|
|                            |                     | IUS (python3{N})         |
|                            +---------------------+--------------------------+
|                            | swig                | >=2.0                    |
+----------------------------+---------------------+--------------------------+
| Ubuntu, Debian, LinuxMint  | libssl-dev          | >=1.0.1                  |
|                            +---------------------+--------------------------+
|                            | g++                 | >=4.4                    |
|                            +---------------------+--------------------------+
|                            | python-dev          | for Python 2.6, 2.7      |
|                            +---------------------+--------------------------+
|                            | python3-dev         | for Python 3.4 - 3.6     |
|                            +---------------------+--------------------------+
|                            | swig                | >=2.0                    |
+----------------------------+---------------------+--------------------------+
| SLES, OpenSUSE             | openssl-devel       | >=1.0.1                  |
|                            +---------------------+--------------------------+
|                            | gcc-c++             | >=4.4                    |
|                            +---------------------+--------------------------+
|                            | python-devel        | for Python 2.6, 2.7      |
|                            +---------------------+--------------------------+
|                            | python3-devel       | for Python 3.4 - 3.6     |
|                            +---------------------+--------------------------+
|                            | swig                | >=2.0                    |
+----------------------------+---------------------+--------------------------+

On some distributions, the ``swig`` package is not available in the required
version. In such cases, it can be built from its sources, as follows:

1. Install the ``pcre-devel`` package (RedHat etc. and SLES etc.) or the
   ``libpcre3`` and ``libpcre3-dev`` packages (Ubuntu etc.).

2. Download the swig source archive and unpack it::

       $ wget -q -O swig-2.0.12.tar.gz http://sourceforge.net/projects/swig/files/swig/swig-2.0.12/swig-2.0.12.tar.gz/download
       $ tar -xf swig-2.0.12.tar.gz

3. Configure and build it::

       $ cd swig-2.0.12
       $ ./configure --prefix=/usr
       $ make swig

4. Install it::

       $ sudo make install

5. Verify its version::

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



