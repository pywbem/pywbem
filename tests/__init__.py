"""
All tests for pywbem.

There are different kinds of tests, organized by subdirectory:

* unittest: Module-level tests.
* functiontest: Mock the client at the HTTP level and execute operations
  against the WBEMConnection class.
* end2endtest: Run against a real WBEM server.
* manualtest: Some scripts that are typically run against real WBEM servers.

In addition, the following subdirectories exist that do not contain tests:

* dtd: The DMTF CIM-XML DTD, used by some CIM-XML related unit tests.
* schema: DMTF CIM Schema, used by some MOF compiler related unit tests.
* server_definitions: Definitions of real WBEM servers to test against,
  used by end2end tests.
* profiles: Definition of attributes of DMTF management profiles, used by
  some testcases in end2end tests.
"""

import os
from .utils import import_installed
pywbem = import_installed('pywbem')  # pylint: disable=invalid-name

print(f"Testing pywbem version {pywbem.__version__} from "
      f"{os.path.dirname(pywbem.__file__)}")
