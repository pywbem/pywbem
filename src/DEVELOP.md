Development of PyWBEM
=====================

This document provides some hints when you want to participate in the
development of PyWBEM. You can ignore it when you just want to use the PyWBEM
client package and program against it.

First, create a local clone of the PyWBEM Git repository:

    git clone git@github.com:pywbem/pywbem.git
    cd pywbem

It is strongly recommended to use a
[virtual Python environment](http://docs.python-guide.org/en/latest/dev/virtualenvs/)
for each version of Python supported by PyWBEM:

    mkvirtualenv -p python2.6 pywbem26
    mkvirtualenv -p python2.7 pywbem27

As of PyWBEM v0.8.0, its setup script (setup.py) establishes any
prerequisites for development of PyWBEM when invoked with the "develop" command:

    cd src
    python setup.py develop

This needs to be repeated in each of the remaining virtual Python environments
that were set up for PyWBEM (these commands should be seen in conjunction with
the commands shown above, which were running the "develop" command in the
pywbem27 environment):

    workon pywbem26
    python setup.py develop

PyWBEM also provides a makefile. Invoking make without arguments will print
the possible make targets:

    make

    makefile for pywbem
    Package version will be: 0.8.0-dev
    Valid targets are:
      build    - Build the distribution archive: ../dist/pywbem-0.8.0/pywbem-0.8.0-dev.zip
      buildwin - (On 64-bit Windows) Build the Windows installable: ../dist/pywbem-0.8.0/pywbem-0.8.0-dev.win-amd64.exe
      check    - Run PyLint on sources
      install  - build + install the distribution archive using "python setup.py install"
      develop  - prepare the development environment by installing prerequisites
      test     - install + run unit tests
      upload   - build + upload the distribution archive to PyPI
      clean    - Remove any temporary files
      clobber  - clean + remove any build products
      all      - build + check + test + install + clean (that is, no upload!)

Testing PyWBEM
--------------

PyWBEM has some amount of unit test cases. Invoke `make test` to build and
install PyWBEM and to run the unit test cases on the current operating system
and the current Python environment.

Any help in completing the unit test cases is very welcome. If you feel like
helping, search for occurrences of `TODO` in the Python source files in
directory `src/testsuite`.

How to submit code to PyWBEM
----------------------------

The number of committers in the PyWBEM GitHub project is small and should stay
small. If you are not a committer but want to submit code, you have two
choices:

* Patch file:

  Work in your local Git clone, and once you are done, create a patch file
  reflecting your changes. Attach the patch file to an issue in the
  [issue tracker](https://github.com/pywbem/pywbem/issues).
  The commit level (in the PyWBEM project on GitHub, not in your local Git
  clone) for which the patch file is intended should be indicated in a
  comment on the issue.

* Pull request:

  Create a fork of the PyWBEM project (anywhere you have a public Git server),
  develop and commit your changes there, and once you are done, create a pull
  request targeting the PyWBEM project on GitHub
  ([https://github.com/pywbem/pywbem](https://github.com/pywbem/pywbem)).
  Again, there should be an issue in the
  [issue tracker](https://github.com/pywbem/pywbem/issues)
  that is resolved by the pull request, and a comment to the issue should
  mention the name of the pull request.

Troubleshooting
---------------

As a PyWBEM developer, you may work on the development environment and not
everything may work right all the time. Here is a list of things that have
gone wrong in the past, and how to resolve them.

These issues should not occur for users of PyWBEM, because the PyWBEM setup
script (setup.py) takes care of them.

* Error when installing M2Crypto (e.g. as part of installing PyWBEM):

  unable to execute swig: No such file or directory

  Root cause: This error occurs when M2Crypto is installed as part of the PyWBEM
  installation, and the `swig` command is not available.

  Solution: Install Swig (Linux: package `swig`). The M2Crypto
  installation requires at least Swig version 2.0. If your operating
  system does not provide for such a version, download and build Swig 2.0.
  Note that this is done automatically by the "develop" and "install" commands
  of the setup script of PyWBEM.

* Error when installing M2Crypto (e.g. as part of installing PyWBEM):

  swig error : Unrecognized option -builtin

  Root cause: This error occurs when M2Crypto is installed as part of the PyWBEM
  installation, and the version of `swig` is not sufficient. The M2Crypto
  installation requires at least Swig version 2.0.

  Solution: Update your version of Swig to at least 2.0. If your operating
  system does not provide for such a version, download and build Swig 2.0.
  Note that this is done automatically by the "develop" and "install" commands
  of the setup script of PyWBEM.

* Error when building Swig:

  configure: error: Cannot find pcre-config script from PCRE (Perl Compatible
  Regular Expressions) library package.

  Root cause: The PCRE development package is not installed.

  Solution: Install the PCRE development package:

      sudo yum install pcre-devel         # if RedHat-based
      sudo apt-get install pcre-devel     # if Debian-based
      sudo zypper install pcre-devel      # if SUSE-based

* Error when installing M2Crypto (e.g. as part of installing PyWBEM):

  SWIG/_m2crypto.i:31: Error: Unable to find 'openssl/opensslv.h'<br/>
  SWIG/_m2crypto.i:45: Error: Unable to find 'openssl/safestack.h'<br/>
  SWIG/_evp.i:12: Error: Unable to find 'openssl/opensslconf.h'<br/>
  SWIG/_ec.i:7: Error: Unable to find 'openssl/opensslconf.h'

  Root cause: The OpenSSL development package is not installed.

  Solution: Install the OpenSSL development package:

      sudo yum install openssl-devel      # if RedHat-based
      sudo apt-get install libssl-devel   # if Debian-based
      sudo zypper install openssl-devel   # if SUSE-based

* Note that installing PyWBEM to the system Python invokes the M2Crypto build
  also under root permissions, so the new Swig version needs to be available
  via the PATH of root, in this case.

  Verify that the new version is available both for your userid and for root:

      swig -version
      sudo swig -version
