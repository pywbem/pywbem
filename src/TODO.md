ToDo list for PyWBEM
====================

All new ideas should be described as issues on GitHub, and not on this list.

This list has some old items, but also some newer items that should be moved
to GitHub (and deleted here):

* Add a test environment so that pywbem has a standard set of tests that could
  be run against any server that provides a defined test profile.

* Update tutorial and add more usage examples.

* Set up a code review & CI environment (Gerrit/Jenkins).

* Single definition of version. Currently, the version is duplicated between
  `pywbem/__init__.py` and `setup.py`.

* Improve wbemcli script (complete function, documented).

* Rewrite XML parser to use xml.sax instead of xml.dom to
  avoid resource usage issues when parsing large XML requests and
  responses.

* Add support for CIM-RS protocol.

* Add support for WS-Management protocol.

* Add a CIM indication listener.

* Add other source code tools (MOF conversion, etc.).

