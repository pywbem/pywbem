#!/usr/bin/env python
"""
Python script for testing the internal _uprint() function with destination
stdout, in a Python environment that is as close as possible to what a pywbem
user uses.

Specifically, because py.test captures stdout, this program should not run
under py.test (unless there is a separate shell in between this program and
py.test).

If the _uprint() function succeeds, the script exits with exit code 0, and a
test string has been written to stdout.

Otherwise, the script exits with an exit code other than 0, and an error
message has been written to stderr (and possibly stdout).

This test script can be invoked with a command line argument that determines
the test case that is run:

* run_uprint.py small - A small string of selected unicode characters
* run_uprint.py ucs2 - All Unicode characters in UCS-2 (U+0000 to U+FFFF)
* run_uprint.py all - All Unicode characters up to the max character supported
  by the Python build that is used. A wide build supports up to U+10FFFF. A
  narrow build supports up to U+FFFF. If the Python build supports less than
  U+10FFFF, an info message is written to stderr, but this does not cause the
  test to fail.
"""

from __future__ import absolute_import, print_function
import sys
import locale
import six
from pywbem_mock._wbemconnection_mock import _uprint

DEBUG = False


def main():
    """Main routine"""

    if len(sys.argv) > 1:
        mode = sys.argv[1]  # 'small', 'ucs2', 'all'
    else:
        mode = 'small'

    if DEBUG:
        print("Debug: mode=%s; sys.stdout: isatty=%r, encoding=%r" %
              (mode, sys.stdout.isatty(),
               getattr(sys.stdout, 'encoding', None)),
              file=sys.stderr)
        print("Debug: sys.getfilesystemencoding=%r "
              "locale.getpreferredencoding=%r" %
              (sys.getfilesystemencoding(), locale.getpreferredencoding()),
              file=sys.stderr)

    if mode == 'small':
        test_string = u'\u212b \u0420 \u043e \u0441 \u0441 \u0438 \u044f \u00e0'
        _uprint(None, test_string)
    elif mode == 'ucs2':
        for cp in six.moves.xrange(0, 0xFFFF):
            test_string = six.unichr(cp)
            _uprint(None, test_string)
    elif mode == 'all':
        test_string = u''
        if sys.maxunicode < 0x10FFFF:
            print("Info: Testing Unicode range of only up to U+%.6X "
                  "(out of U+10FFFF)" % sys.maxunicode,
                  file=sys.stderr)
        for cp in six.moves.xrange(0, sys.maxunicode):
            test_string = six.unichr(cp)
            _uprint(None, test_string)


if __name__ == '__main__':
    main()
