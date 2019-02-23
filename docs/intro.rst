
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

  * :ref:`wbemcli`

    A WBEM client in the form of a shell that provides an interactive Python
    environment for issuing WBEM operations to a WBEM server.


.. _`Installation`:

Installation
------------

Pywbem is a pure Python package and therefore does not have a dependency on
operating system packages in addition to Python itself. However, some of the
Python packages used by pywbem have dependencies on additional operating system
packages for their installation. Also, on some platforms, manual post-processing
steps are needed, such as setting up environment variables.

This section describes the complete installation of pywbem with all steps
including prerequisite operating system packages and manual post-processing
steps, for users of pywbem. As a user of pywbem, you can import the pywbem
Python package into your programs, and/or you can run the :ref:`WBEM utility
commands` that come with pywbem.

If you want to contribute to the pywbem project, you need to set up a
development and test environment for pywbem. That has a larger set of OS-level
prerequisites and its setup is described in chapter :ref:`Development`.

A note on the ``pywbem_os_setup.sh`` script that is used for installation on
some platforms: That script installs the Python ``distro`` package into the
active Python environment. If your active Python environment is a virtual
Python environment, that package will obviously be installed into that virtual
environment. If your active Python environment is the system Python
environment, that package will be installed into the system Python, but as a
local package for the current user. So it is not visible in the system Python
of other users, but still visible in the system Python of the current user.
This is done in order not to pollute the system Python installation with
additional Python packages that are not known at the OS-level package manager
(e.g. ``yum`` on RedHat) and thus may be considered a maintenance problem.


.. _`Supported environments`:

Supported environments
^^^^^^^^^^^^^^^^^^^^^^

Pywbem is supported in these environments:

* Operating Systems: Linux, Windows (native, and with UNIX-like environments),
  OS-X

* Python: 2.6, 2.7, 3.4, and higher

* WBEM servers: Any WBEM server that conforms to the DMTF specifications listed
  in :ref:`Standards conformance`. WBEM servers supporting older versions of
  these standards are also supported, but may have limitations.
  See :ref:`WBEM servers` for more details.

Limitations:

* On Windows (native), pywbem is not supported on Python 2.6, because the
  M2Crypto package does not support Python 2.6.

Announcement of removal of Python 2.6 support:

* The Python Software Foundation has stopped supporting Python 2.6 with the
  2.6.9 release in october 2013. Since then, many Python package projects have
  continued releasing versions for Python 2.6, and so has pywbem. In 2017 and
  2018, a number of Python package projects have actively removed support for
  Python 2.6 and it has become an increasingly difficult task for pywbem to
  keep supporting Python 2.6. For this reason, Python 2.6 support will be
  removed from pywbem in its future 1.0.0 version.


.. _`Installing to Linux`:

Installing to Linux
^^^^^^^^^^^^^^^^^^^

* Prerequisites:

  - The Python environment into which you want to install must be the current
    Python environment, and must have at least the following Python packages
    installed:

    - setuptools
    - wheel (<0.30.0 on Python 2.6)
    - pip

* Download the ``pywbem_os_setup.sh`` script from one of these sources:

  - :download:`pywbem_os_setup.sh <../pywbem_os_setup.sh>` on this site

  - `pywbem_os_setup.sh <https://raw.githubusercontent.com/pywbem/pywbem/master/pywbem_os_setup.sh>`_
    on the `master` branch of the pywbem Git repository

  That script installs OS-level prerequisite packages needed by pywbem.

* Execute the ``pywbem_os_setup.sh`` script:

  .. code-block:: bash

      $ ./pywbem_os_setup.sh

  The script uses ``sudo`` under the covers to invoke the OS-level package
  manager for your Linux distribution (e.g. ``yum`` on the RedHat family), so
  the current userid needs to have sudo permission.

  On older Linux versions, the Swig utility may not be available in the
  required version. In that case, the ``pywbem_os_setup.sh`` script will report
  that as an issue and one option on how to proceed is to build Swig yourself
  as described in :ref:`Building Swig`, and then to repeat execution of the
  ``pywbem_os_setup.sh`` script.

  In case the script reports that your Linux distribution is not supported by
  the script, you can still try to find out what the corresponding OS-level
  packages are on your Linux distribution and install them manually. The script
  will list the names and versions of the OS-level packages for RedHat in that
  case, and you would need to find out what the corresponding packages are
  on your desired Linux distribution. If you were able to find these packages,
  please `open an issue <https://github.com/pywbem/pywbem/issues>`_ so we can
  add support for that Linux distribution to the script.

* Only on Python 2.6 on Linux Debian family systems with multi-architecture
  support (e.g. Ubuntu 16.04 and higher):

  Perform the following workaround to make the multi-architecture header files
  of OpenSSL available in a compatible way (the example is for x86_64 systems):

  .. code-block:: bash

      $ sudo ln -s /usr/include/x86_64-linux-gnu/openssl/opensslconf.h /usr/include/openssl/opensslconf.h

  Background: One of the packages needed by pywbem on Python 2 is ``M2Crypto``.
  During its own installation as a Python package, ``M2Crypto`` needs the
  OpenSSL header files. On Linux Debian family systems with multi-architecture
  support, the structure of OpenSSL header files changed incompatibly (compared
  to earlier versions of these distributions). The installation of ``M2Crypto``
  tries to accomodate that incompatibility by detecting multi-architecture
  support, but on Python 2.6 the interface for that was not yet supported. As a
  result, the OpenSSL header files are not found. The workaround established in
  this step makes the OpenSSL header files available in a compatible way, so
  that the ``M2Crypto`` installation finds them.

* Install pywbem (and its prerequisite Python packages) into the active Python
  environment:

  .. code-block:: bash

      $ pip install pywbem


.. _`Installing to OS-X`:

Installing to OS-X
^^^^^^^^^^^^^^^^^^

* Prerequisites:

  - The Python environment into which you want to install must be the current
    Python environment, and must have at least the following Python packages
    installed:

    - setuptools
    - wheel (<0.30.0 on Python 2.6)
    - pip

* Download the ``pywbem_os_setup.sh`` script from one of these sources:

  - :download:`pywbem_os_setup.sh <../pywbem_os_setup.sh>` on this site
  - `pywbem_os_setup.sh <https://raw.githubusercontent.com/pywbem/pywbem/master/pywbem_os_setup.sh>`_
    on the `master` branch of the pywbem Git repository

  That script installs OS-level prerequisite packages needed by pywbem.

* Execute the ``pywbem_os_setup.sh`` script:

  .. code-block:: bash

      $ ./pywbem_os_setup.sh

  The script uses ``sudo`` under the covers to invoke ``brew`` (Homebrew
  project) to install OS-level packages, so the current userid needs to have
  sudo permission.

* Only on Python 2 on newer OS-X releases:

  The ``pywbem_os_setup.sh`` script installs the ``openssl`` package needed by
  the ``M2Crypto`` Python package. On newer OS-X releases, you may see a notice
  that the ``openssl`` package is "not linked" because the TLS implementation
  provided with OS-X is available. In that case, you need to set up the
  following environment variables for use by the pywbem package installation
  described in the next step:

  .. code-block:: bash

      $ openssl_dir=$(brew --prefix openssl)
      $ export LDFLAGS="-L$openssl_dir/lib $LDFLAGS"
      $ export CFLAGS="-I$openssl_dir/include $CFLAGS"
      $ export SWIG_FEATURES="-I$openssl_dir/include $SWIG_FEATURES"

* Install pywbem (and its prerequisite Python packages) into the active Python
  environment:

  .. code-block:: bash

      $ pip install pywbem


.. _`Installing to native Windows`:

Installing to native Windows
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This section describes the installation of pywbem into a *native Windows
environment*. That is an environment where the Windows command processor is
used to run any commands. Tools from UNIX-like environments may or may not be
present in the PATH.

* Prerequisites:

  - The Python environment into which you want to install must be the active
    Python environment, and must have at least the following Python packages
    installed:

    - setuptools
    - wheel
    - pip

  - Windows command prompt in administrator mode.

* Download the ``pywbem_os_setup.bat`` script from one of these sources:

  - :download:`pywbem_os_setup.bat <../pywbem_os_setup.bat>` on this site

  - `pywbem_os_setup.bat <https://raw.githubusercontent.com/pywbem/pywbem/master/pywbem_os_setup.bat>`_
    on the `master` branch of the pywbem Git repository

* Execute the ``pywbem_os_setup.bat`` script in a Windows command prompt in
  administrator mode:

  .. code-block:: bash

     > pywbem_os_setup.bat

  This script checks whether the commands needed for installing and using
  pywbem are available in the PATH. If not, it installs them via the
  `Chocolatey package manager`_.

  The following commands are needed for installing and using pywbem:

  * ``swig``
  * ``curl``
  * ``grep``
  * ``chmod``
  * ``tar``

  These commands can be made available in the PATH via a UNIX-like environment
  such as `CygWin`_, `MSYS2`_, Babun, or Gow. If they are not all available in
  the PATH, the `Chocolatey package manager`_ must be installed and its
  ``choco`` command must be available in the PATH.

  This script will also install the ``M2Crypto`` Python package into the active
  Python environment, so it must be run with the desired Python environment
  active.

  This script will also download and install Win32 OpenSSL from
  https://slproweb.com/products/Win32OpenSSL.html.

* Install pywbem (and its other prerequisite Python packages) into the active
  Python environment by running in a Windows command prompt in administrator
  mode:

  .. code-block:: bash

     > pip install pywbem

.. _`Chocolatey package manager`: https://chocolatey.org/

.. _`CygWin`: https://cygwin.org/

.. _`MSYS2`: https://www.msys2.org/


.. _`Installing to a UNIX-like environment under Windows`:

Installing to a UNIX-like environment under Windows
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This section describes the installation of pywbem into a *UNIX-like environment
under Windows* (such as `CygWin`_, `MSYS2`_, Babun, or Gow). That is an
environment where the UNIX/Linux shell of the UNIX-like environment (such as
``bash`` or ``sh``) is used to run any commands.

Note that Unix-like environments on Windows bring their own Python, so in such
an environment, you install into that Python, and not into the Python of
Windows.

* Prerequisites:

  - The Python environment into which you want to install must be the current
    Python environment, and must have at least the following Python packages
    installed:

    - setuptools
    - wheel (<0.30.0 on Python 2.6)
    - pip

  - Prerequisite OS-level packages must be available in the UNIX-like
    environment.

    For CygWin, these packages can be installed using the CygWin setup
    program and are listed in
    :ref:`Prerequisite operating system packages for install`.

    For other UNIX-like environments, we did not compile a list of the required
    packages. If you can help out here by providing the package names, please
    tell us by `opening an issue <https://github.com/pywbem/pywbem/issues>`_).

* Install pywbem (and its other prerequisite Python packages) into the active
  Python environment, by running in the UNIX/Linux shell of the UNIX-like
  environment:

  .. code-block:: bash

      $ pip install pywbem

  If the Swig compilation during installation of ``M2Crypto`` fails, there may
  be components of the UNIX-like environment missing (see first item).


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

The following table lists the prerequisite operating system packages along with
their version requirements for installing and running pywbem, for the
supported operating systems and Linux distributions. This list is for
reference only, because the installation steps in the previous sections already
take care of getting these packages installed.

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
| Windows (native)         | None               |                      |       |
+--------------------------+--------------------+----------------------+-------+
| Windows (CygWin)         | openssl-devel      |                      | py2   |
|                          +--------------------+----------------------+-------+
|                          | python2-devel      |                      | py2   |
|                          +--------------------+----------------------+-------+
|                          | gcc-g++            |                      | py2   |
|                          +--------------------+----------------------+-------+
|                          | swig               |                      | py2   |
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

       $ wget -q -O swig-2.0.12.tar.gz https://sourceforge.net/projects/swig/files/swig/swig-2.0.12/swig-2.0.12.tar.gz/download
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
