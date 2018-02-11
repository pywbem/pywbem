
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

The development environment is pretty easy to set up.

Besides having a supported operating system with a supported Python version
(see :ref:`Supported environments`), it is recommended that you set up a
`virtual Python environment`_.

.. _virtual Python environment: http://docs.python-guide.org/en/latest/dev/virtualenvs/

Then, with a virtual Python environment active, clone the Git repo of this
project and prepare the development environment with ``make develop``:

::

    $ git clone git@github.com:pywbem/pywbem.git
    $ cd pywbem
    $ make develop

This will install all prerequisites the package needs to run, as well as all
prerequisites that you need for development.

Generally, this project uses Make to do things in the currently active
Python environment. The command ``make help`` (or just ``make``) displays a
list of valid Make targets and a short description of what each target does.


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
pywbem package at http://pywbem.readthedocs.io/

This page is automatically updated whenever the Git repo for this package
changes the branch from which this documentation is built.

In order to build the documentation locally from the Git work directory, issue:

::

    $ make builddoc

The top-level document to open with a web browser will be
``build_doc/html/docs/index.html``.


.. _`Testing`:

Testing
-------

To run unit tests in the currently active Python environment, issue one of
these example commands:

::

    $ make test                                              # Run all unit tests
    $ PYTHONPATH=. py.test testsuite/test_cim_obj.py -s      # Run only this test source file
    $ PYTHONPATH=. py.test InitCIMInstanceName -s            # Run only this test class
    $ PYTHONPATH=. py.test -k InitCIMInstanceName or Bla -s  # py.test -k expressions are possible

Invoke ``py.test --help`` for details on the expression syntax of its ``-k``
option.

To run the unit tests and some more commands that verify the project is in good
shape in all supported Python environments, use Tox:

::

    $ tox                              # Run all tests on all supported Python versions
    $ tox -e py27                      # Run all tests on Python 2.7


.. _`Updating the DMTF MOF Test Schema`:

Updating the DMTF MOF Test Schema
---------------------------------

Pywbem uses DMTF CIM Schemas in its CI testing.  The schema used is stored in
the form received from the DMTF in the directory ``testsuite/schema`` and is
expanded and compiled in ``testsuite/test_mof_compiler.py`` as part of the
tests.

Since the DMTF regularly updates the schema, the pywbem project tries to stay
up-to-date with the current schema. At the same time, earlier schemas can be
used for testing also by changing the definitions for the dmtf schema to be
tested.

The schema used for testing can be modified by modifying the test file:

::

    testsuite/dmtf_mof_schema_def.py

Detailed information on this process is in ``testsuite/dmtf_mof_schema_def.py``

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
