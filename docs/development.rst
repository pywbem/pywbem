
.. _`Development`:

Development
===========

This section only needs to be read by developers of the pywbem package.
People that want to make a fix or develop some extension, and people that
want to test the project are also considered developers for the purpose of
this section.


.. _`Repository`:

Repository
----------

The repository for pywbem is on GitHub:

https://github.com/pywbem/pywbem


.. _`Setting up the development environment`:

Setting up the development environment
--------------------------------------

It is recommended to use Linux as the development environment for pywbem.
OS-X should work as well, but Windows requires a number of manual setup steps.

1. Clone the Git repo of this project and switch to its working directory:

   .. code-block:: bash

        $ git clone git@github.com:pywbem/pywbem.git
        $ cd pywbem

2. It is recommended that you set up a `virtual Python environment`_.
   Have the virtual Python environment active for all remaining steps.

3. Install pywbem and its prerequisites for installing and running it
   as described in :ref:`Installation`.
   This will install Python packages into the active Python environment,
   and OS-level packages.

4. On Windows, perform the setup steps described in
   :ref:`Manual setup on Windows`. On Linux and OS-X, the corresponding
   setup is performed automatically as part of the next step.

5. Install the prerequsites for pywbem development.
   This will install Python packages into the active Python environment,
   and OS-level packages:

   .. code-block:: bash

        $ make develop

6. This project uses Make to do things in the currently active Python
   environment. The command:

   .. code-block:: bash

        $ make

   displays a list of valid Make targets and a short description of what each
   target does.

.. _virtual Python environment: https://docs.python-guide.org/en/latest/dev/virtualenvs/


.. _`Manual setup on Windows`:

Manual setup on Windows
^^^^^^^^^^^^^^^^^^^^^^^

For development of pywbem, it is recommended to use one of the Unix-like
environments on Windows (such as CygWin, MinGW, Babun, or Gow). The pywbem
tests that run on the Appveyor CI use CygWin.

Note that Unix-like environments on Windows bring their own Python, so double
check that the active Python environment is the one you want to install to.

The development environment needs the ``xmllint`` utility and the ``lxml``
Python package.

The ``lxml`` Python package for Windows meanwhile comes as a binary wheel
archive that includes all of its dependencies, so it has no additional
dependencies you would need to take care about.

The ``xmllint`` utility is part of CygWin and likely also part of the other
Unix-like environments.


.. _`Prerequisite operating system packages for development`:

Prerequisite operating system packages for development
------------------------------------------------------

The following table lists the prerequisite operating system packages along with
their version requirements for development of pywbem, for the supported
operating systems and Linux distributions.

The prerequisite operating system packages for installing and running pywbem
are also needed for development, and can be found in section
:ref:`Prerequisite operating system packages for install`.

This section is just for information. These packages will be installed as part
of the steps described in :ref:`Setting up the development environment`.

+--------------------------+--------------------+----------------------+-------+
| Op.system / Distribution | Package name       | Version requirements | Notes |
+==========================+====================+======================+=======+
| Linux RedHat family      |                    |                      |       |
| (RHEL, CentOS, Fedora)   |                    |                      |       |
+--------------------------+--------------------+----------------------+-------+
| Linux Debian family      |                    |                      |       |
| (Ubuntu, Debian,         |                    |                      |       |
| LinuxMint)               |                    |                      |       |
+--------------------------+--------------------+----------------------+-------+
| Linux SUSE family        |                    |                      |       |
| (SLES, openSUSE)         |                    |                      |       |
+--------------------------+--------------------+----------------------+-------+
| OS-X                     |                    |                      |       |
+--------------------------+--------------------+----------------------+-------+
| Windows                  | xmllint            |                      |       |
+--------------------------+--------------------+----------------------+-------+


.. _`Building the documentation`:

Building the documentation
--------------------------

The ReadTheDocs (RTD) site is used to publish the documentation for the
pywbem package at https://pywbem.readthedocs.io/

This page is automatically updated whenever the Git repo for this package
changes the branch from which this documentation is built.

In order to build the documentation locally from the Git work directory,
execute:

::

    $ make builddoc

The top-level document to open with a web browser will be
``build_doc/html/docs/index.html``.


.. _`Testing`:

.. # Keep the tests/README file in sync with this 'Testing' section.

Testing
-------


All of the following `make` commands run the tests in the currently active
Python environment. Depending on how the `pywbem` package is installed in that
Python environment, either the `pywbem` and `pywbem_mock` directories in the
main repository directory are used, or the installed `pywbem` package.
The test case files and any utility functions they use are always used from
the `tests` directory in the main repository directory.

The `tests` directory has the following subdirectory structure:

::

    tests
     +-- unittest            Unit tests
     |    +-- utils               Utility functions used by unit tests
     |    +-- pywbem              Unit tests for the pywbem package
     |    +-- pywbem_mock         Unit tests for the pywbem_mock package
     |    +-- unittest_utils      Unit tests for tests/unittest/utils
     |    +-- functiontest        Unit tests for tests/functiontest
     |    +-- end2endtest_utils   Unit tests for tests/end2endtest/utils
     |    +-- servers             Unit tests for tests/servers
     +-- functiontest        Function tests
     +-- end2endtest         End2end tests
     |    +-- utils               Utility functions used by end2end tests
     +-- manualtest          Manual tests
     +-- server_definitions  WBEM server definition file used by some tests and module
     |                         for accessing it
     +-- profiles            Simple definitions of management profiles used by some tests
     +-- schema              The CIM schema MOF files used by some MOF tests
     +-- dtd                 The CIM DTD file used by some CIM-XML validation tests

There are multiple types of tests in pywbem:

1. Unit tests and function tests

   These tests do not require any WBEM server to be available, and the tests
   validate their results automatically.

   The distinction between unit tests and function tests as used in pywbem is
   that function tests exercise the entire pywbem client component or entire
   pywbem scripts, while unit tests exercise single modules.

   They are run by executing:

   ::

       $ make test

   Test execution can be modified by a number of environment variables, as
   documented in the make help (execute `make help`).

2. End2end tests

   These tests are run against one or more WBEM servers, and the tests validate
   their results automatically.

   They are run by preparing a server definition file:

   ::

       tests/server_definitions/server_definition_file.yml

   from the provided example, and by executing:

   ::

       $ make end2end

   Again, test execution can be modified by a number of environment variables,
   as documented in the make help (execute `make help`).

3. Manual tests

   There are several Python scripts and shell scripts that can be run manually.
   The results need to be validated manually.

   These scripts are in the directory:

   ::

       tests/manualtest/

   and are executed by simply invoking them from within the main directory
   of the repository, e.g.:

   ::

       tests/manualtest/run_cim_operations.py

   Some of the scripts support a `--help` option that informs about their
   usage.

   The `run_cim_operations.py` script needs a particular MOF file loaded in the
   repository of the WBEM server that is used for the test. This can be done
   using the MOF compiler of pywbem:

   ::

       $ mof_compiler -s <target_url> tests/unittest/pywbem/test.mof

To run the unit and function tests in all supported Python environments, the
Tox tool can be used. It creates the necessary virtual Python environments and
executes `make test` (i.e. the unit and function tests) in each of them.

For running Tox, it does not matter which Python environment is currently
active, as long as the Python `tox` package is installed in it:

::

    $ tox                              # Run tests on all supported Python versions
    $ tox -e py27                      # Run tests on Python 2.7


.. _`Updating the DMTF MOF Test Schema`:

Updating the DMTF MOF Test Schema
---------------------------------

Pywbem uses DMTF CIM Schemas in its CI testing.  The schema used is stored in
the form received from the DMTF in the directory ``tests/schema`` and is
expanded and compiled as part of the unit tests.

Since the DMTF regularly updates the schema, the pywbem project tries to stay
up-to-date with the current schema. At the same time, earlier schemas can be
used for testing also by changing the definitions for the dmtf schema to be
tested.

The schema used for testing can be modified by modifying the test file:

::

    tests/unittest/utils/dmtf_mof_schema_def.py


.. _`Developing Ipython Notebooks`:

Developing PyWBEM Ipython Documentation Notebooks
-------------------------------------------------

The pywbem developers are using ipython notebooks to demonstrate the use of
pywbem.  Today we generally have one notebook per operation or group of
operations including definition of the operation, references back to the
pywbem documentation, and one or more examples  (hopefully examples that
will actually execute against a wbem server)

These can easily be extended or supplemented using a local ipython or
jupyter server by:

1. Install ipython or Jupyter software using pip or pip3. The notebook server
may be installed as root or within a python virtual environment. For example:

::

   $ sudo pip install ipython
   or
   $ sudo pip3 install ipython
   or
   $ sudo pip install jupyter

The notebook server may be installed as root or within a python virtual
environment.

2. Start the local ipython/jupyter notebook server in the notebook directory
(`pywbem/docs/notebooks`) referencing that directory in the command line
call:

::

  $ ipython notebook docs/notebooks
  or
  $ jupyter notebook docs/notebooks

This will start the local ipython/juypter notebook server and on the first page
displayed in your web browser all existing pywbem ipython notebooks will be
available for editing. New ones can be created using the commands on that
ipython server web page.

New and changed notebooks must go through the same contribution process as other
components of pywbem to be integrated into the github repository.

.. _`Contributing`:

Contributing
------------

Third party contributions to this project are welcome!

In order to contribute, create a `Git pull request`_, considering this:

.. _Git pull request: https://help.github.com/articles/using-pull-requests/

* Test is required.
* Each commit should only contain one "logical" change.
* A "logical" change should be put into one commit, and not split over multiple
  commits.
* Large new features should be split into stages.
* The commit message should not only summarize what you have done, but explain
  why the change is useful.
* The commit message must follow the format explained below.

What comprises a "logical" change is subject to sound judgement. Sometimes, it
makes sense to produce a set of commits for a feature (even if not large).
For example, a first commit may introduce a (presumably) compatible API change
without exploitation of that feature. With only this commit applied, it should
be demonstrable that everything is still working as before. The next commit may
be the exploitation of the feature in other components.

For further discussion of good and bad practices regarding commits, see:

* `OpenStack Git Commit Good Practice`_
* `How to Get Your Change Into the Linux Kernel`_

.. _OpenStack Git Commit Good Practice: https://wiki.openstack.org/wiki/GitCommitMessages
.. _How to Get Your Change Into the Linux Kernel: https://www.kernel.org/doc/Documentation/SubmittingPatches


.. _`Core Development Team`:

Core Development Team
---------------------

Anyone can contribute to pywbem via pull requests as described in the previous
section.

The pywbem project has a core development team that holds regular web conferences
and that is using Slack for offline communication, on the Slack workspace:
https://pywbem.slack.com.

The web conference and the Slack workspace are by invitation, and if you want
to participate in the core team, please
`open an issue <https://github.com/pywbem/pywbem/issues>`_ to let us know.
