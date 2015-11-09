ToDo list for PyWBEM
====================

For version 0.8.0
-----------------

* Have the documentation published online, instead of including it in the
  distribution archive.

* Test the client, its installation, and particularly the M2Crypto
  installation on a number of operating system environments.
  
* Fix bugs reported in GitHub issue tracker.

For versions after 0.8.0
------------------------

* Improve unit testing of the MOF compiler (so that the compiler bug on GitHub
  would have been found).

* Add more testcases for the client test.

* Add a test environment so that pywbem has a standard set of tests that could
  be run against any server that provides a defined test profile.

* Set up a review & CI environment (Gerrit/Jenkins).

* Single definition of version. Currently, the version is duplicated between
  pywbem/__init__.py and setup.py.

* Add support for pull operations.

* Improve wbemcli script (complete function, documented).

* Add support for CIM-RS protocol.

* Convert documentation to Sphinx.

* Add other source code tools (MOF conversion, etc.).
