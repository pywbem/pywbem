#!/usr/bin/env python
#
# Build the LEX/YACC table modules for the MOF compiler, in the PyWBEM
# installation directory. The installation directory is used by removing
# the directory of this script from the Python module search path.

import sys
import os
from pprint import pprint

myname = os.path.basename(sys.argv[0])

DEBUG = False   # Enable to get debug info
VERBOSE = True  # TODO: Pass as command line option


def env_info():
    print(f"{myname}: Platform: {sys.platform}")
    print(f"{myname}: Python executable: {sys.executable}")
    print(f"{myname}: Python version: {sys.version}")
    print(f"{myname}: Python module search path:")
    pprint(sys.path)


def main():

    if VERBOSE:
        print(f"{myname}: Rebuilding the pywbem LEX/YACC table modules, "
              "if needed")

    # We want to build the table modules in the target install directory.
    #
    # The _mof_compiler._build() function builds them in the directory where
    # the _mof_compiler module was imported from.
    #
    # This script runs in the directory where the distribution archive has
    # been unpacked to (or during development in the git repo work directory),
    # where the pywbem package is directly available as a subdirectory.
    #
    # Therefore, we need to remove the directory of this script from the Python
    # module search path before importing the _mof_compiler module, in order to
    # import it from the target install directory.
    if VERBOSE:
        print(f"{myname}: Ensuring to build in pywbem install directory")
    my_abs_path = os.path.dirname(os.path.abspath(sys.argv[0]))
    removals = []
    for i, p in enumerate(sys.path):
        abs_p = os.path.abspath(p)
        if abs_p == my_abs_path:
            if DEBUG:
                print(f"{myname}: Debug: Removing from module search path: "
                      f"{abs_p}")
            removals.append(i)
    for i in reversed(removals):
        del sys.path[i]
    if DEBUG:
        print(f"{myname}: Debug: Resulting module search path:")
        pprint(sys.path)

    try:
        import pywbem
        if DEBUG:
            print(f"{myname}: Debug: Pywbem package successfully imported "
                  f"from: {pywbem.__file__}")
    except ImportError as exc:
        print(f"{myname}: Error: Import of pywbem package failed: {exc}")
        env_info()
        return 1

    from pywbem import _mof_compiler
    try:
        _mof_compiler._build(verbose=True)
    except Exception as exc:
        print(f"{myname}: Error: Rebuilding the pywbem LEX/YACC table modules "
              "failed: {exc}")
        env_info()
        return 1

    if VERBOSE:
        print(f"{myname}: Successfully rebuilt the pywbem LEX/YACC table "
              "modules, if needed")
    return 0

if __name__ == '__main__':
    sys.exit(main())
