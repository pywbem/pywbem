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
    print("%s: Platform: %s" % (myname, sys.platform))
    print("%s: Python executable: %s" % (myname, sys.executable))
    print("%s: Python version: %s" % (myname, sys.version))
    print("%s: Python module search path:" % myname)
    pprint(sys.path)


def main():

    if VERBOSE:
        print("%s: Rebuilding the pywbem LEX/YACC table modules, if needed" % \
              myname)

    # We want to build the table modules in the target install directory.
    #
    # The mof_compiler._build() function builds them in the directory where
    # the mof_compiler module was imported from.
    #
    # This script runs in the directory where the distribution archive has
    # been unpacked to (or during development in the git repo work directory),
    # where the pywbem package is directly available as a subdirectory.
    #
    # Therefore, we need to remove the directory of this script from the Python
    # module search path before importing the mof_compiler module, in order to
    # import it from the target install directory.
    if VERBOSE:
        print("%s: Ensuring to build in pywbem install directory" % myname)
    my_abs_path = os.path.dirname(os.path.abspath(sys.argv[0]))
    removals = []
    for i, p in enumerate(sys.path):
        abs_p = os.path.abspath(p)
        if abs_p == my_abs_path:
            if DEBUG:
                print("%s: Debug: Removing from module search path: %s" % \
                      (myname, abs_p))
            removals.append(i)
    for i in reversed(removals):
        del sys.path[i]
    if DEBUG:
        print("%s: Debug: Resulting module search path:" % myname)
        pprint(sys.path)

    try:
        import pywbem
        if DEBUG:
            print("%s: Debug: Pywbem package successfully imported from: %s" % \
                  (myname, pywbem.__file__))
    except ImportError as exc:
        print("%s: Error: Import of pywbem package failed: %s" % (myname, exc))
        env_info()
        return 1

    from pywbem import mof_compiler
    try:
        mof_compiler._build(verbose=True)
    except Exception as exc:
        print("%s: Error: Rebuilding the pywbem LEX/YACC table modules " \
              "failed: %s" % (myname, exc))
        env_info()
        return 1

    if VERBOSE:
        print("%s: Successfully rebuilt the pywbem LEX/YACC table modules, "
              "if needed" % myname)
    return 0

if __name__ == '__main__':
    sys.exit(main())
