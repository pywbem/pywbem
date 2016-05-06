Installation of PyWBEM Client
=============================

The PyWBEM Client can be installed quite easily by running its standard Python
setup script (`setup.py`) with the `install` command, or by using `pip install`
(which also invokes the setup script).

As of PyWBEM Client v0.8, the setup script has support for installing its
prerequisites. This includes installing Python packages and OS-level packages,
and it includes the usual install mode and development mode.

OS-level prerequisites are installed using new setup.py commands `install_os`
(for the usual install mode) and `develop_os` (for development mode). These
commands perform the installation for a number of well-known Linux
distributions, using `sudo` under the covers (so your userid needs to be
authorized for `sudo`, if you run these commands). For other Linux
distributions and operating systems, these setup.py commands just display the
names of the OS-level
packages that would be needed on RHEL, leaving it to the user to
translate the package names to the actual system, and to establish the
prerequisites. This approach is compatible with PyPI because `pip install`
invokes `setup.py install` but not the new commands. It is also compatible
with packaging PyWBEM into OS-level Python packages, for the same reason.
This approach is also compatible with 
[virtual Python environments](http://docs.python-guide.org/en/latest/dev/virtualenvs/)
because `sudo` is invoked under the covers for installing the OS-level
packages, so you can still invoke setup.py without sudo for targeting the
current virtual Python environment.

Examples
--------

* Install latest version from PyPI into the current virtual Python:

      pip install pywbem

  If the OS-level prerequisites are not yet satisfied, then this command
  will fail. You can then perform this sequence of commands to get the
  the OS-level prerequisites installed in addition:

      pip download pywbem
      tar -xf pywbem-*.tar.gz
      cd pywbem-*
      python setup.py install_os install

  Note that you do not need to use 'sudo' in the command line, because you
  want to install the Python packages into the current virtual Python. The
  OS-level packages are installed by invoking 'sudo' under the covers.

  The OS-level prerequisites will be installed to the system, and the Python
  prerequisites along with PyWBEM itself will be installed into the current
  virtual Python environment.

* Install latest version from PyPI into the system Python:

      sudo pip install pywbem

  If the OS-level prerequisites are not yet satisfied, then this command
  will fail. You can then perform this sequence of commands to get the
  the OS-level prerequisites installed in addition:

      pip download pywbem
      tar -xf pywbem-*.tar.gz
      cd pywbem-*
      sudo python setup.py install_os install

  The OS-level prerequisites will be installed to the system, and the Python
  prerequisites along with PyWBEM itself will be installed into the system
  Python environment.

* Install the latest development version from GitHub into the current
  virtual Python, installing OS-level prerequisites as needed:

      git clone git@github.com:pywbem/pywbem.git pywbem
      cd pywbem
      python setup.py install_os install

* Install from a particular distribution archive on GitHub into the current
  virtual Python, installing OS-level prerequisites as needed:

      wget https://github.com/pywbem/pywbem/blob/master/dist/pywbem-0.8/pywbem-0.8.3.tar.gz
      tar -xf pywbem-0.8.3.tar.gz
      cd pywbem-0.8.3
      python setup.py install_os install

* The installation of PyWBEM in development mode is supported as
  well:

      git clone git@github.com:pywbem/pywbem.git pywbem
      cd pywbem
      make develop

  This will install additional OS-level and Python packages that are needed
  for development and test of PyWBEM.

The command syntax above is shown for Linux, but this works the same way on
Windows and on other operating systems supported by Python.

Test of the installation
------------------------

To test that PyWBEM is sucessfully installed, start up a Python interpreter and
try to import the pywbem module:

    python -c "import pywbem"

If you do not see any error messages after the import command, PyWBEM has been
sucessfully installed and its Python dependencies are available.

If you have installed in development mode, you can run the test suite:

    make test

