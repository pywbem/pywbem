#!/usr/bin/env python
# -*- coding: utf-8 -*-
 
"""mof_compiler.py script.

For details, see the `pywbem.mof_compiler` module.
"""

import sys 
from pywbem.mof_compiler import main
 
if __name__ == '__main__':
    import pywbem.mof_compiler as mc
    print("Debug: mof_compiler script: mof_compiler module in: %s" % mc.__file__)
    print("Debug: mof_compiler script: module path: %r" % sys.path)
    rc = main()
    sys.exit(rc)
