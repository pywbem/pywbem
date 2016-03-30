#!/usr/bin/env python
#
# Build the LEX/YACC table modules for the MOF compiler, in the PyWBEM
# installation directory. The installation directory is used by removing
# the directory of this script from the Python module search path.

import sys
import os

myname = os.path.basename(sys.argv[0])

DEBUG = False

def main():

    my_abs_path = os.path.dirname(os.path.abspath(sys.argv[0]))
    for p in sys.path:
        abs_p = os.path.abspath(p)
        if abs_p == my_abs_path:
            if DEBUG:
                print('%s: Debug: Removing from module search path: %s' % \
                      (myname, abs_p))
            sys.path.remove(p)

    if DEBUG:
        from pprint import pprint
        print('%s: Debug: Current module search path:' % myname)
        pprint(sys.path)

    try:
        import pywbem
        from pywbem import mof_compiler
        if DEBUG:
            print('%s: Debug: pywbem imported from: %s' % \
                  (myname, pywbem.__file__))
    except ImportError as exc:
        print('%s: Error: Import of pywbem package failed: %s' % \
              (myname, exc))
        return 1

    try:
        mof_compiler._build(verbose=True)
    except Exception as exc:
        print('%s: Error: Build of LEX/YACC table modules failed: %s' % \
              (myname, exc))
        return 1

    return 0

if __name__ == '__main__':
    sys.exit(main())
