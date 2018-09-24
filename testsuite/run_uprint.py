#!/usr/bin/env python
"""
Python script for testing the internal _uprint() function with destination
stdout, in a Python environment that is as close as possible to what a pywbem
user uses.

Specifically, because py.test captures stdout, this program should not run
under py.test (unless there is a separate shell in between this program and
py.test).

If the _uprint() function succeeds, the script exits with exit code 0, and
some test strings have been written to stdout.

Otherwise, the script exits with an exit code other than 0, and an error
message has been written to stderr (and possibly stdout).

This test script can be invoked with a command line argument that determines
the test case that is run:

* run_uprint.py small - Some small sets of selected characters from ASCII,
  UCS-2 and UCS-4.
* run_uprint.py ucs2 - All Unicode characters in UCS-2 (U+0000 to U+FFFF).
  Very long output!!
* run_uprint.py all - All Unicode characters in UCS-4 (U+0000 to U+10FFFF).
  This works for both narrow and wide Python builds.
  Very very long output!!

This script can also be invoked with a second argument to select a different
way to output the test string (e.g. normal print(), or raising an exception).
That is for manually figuring out the behavior for non-ASCII test strings.
"""

from __future__ import absolute_import, print_function
import sys
import locale
import six
import traceback
from pywbem_mock._wbemconnection_mock import _uprint

MAX_UNICODE_CP = 0x10FFFF  # Highest defined Unicode code point
MAX_UCS2_CP = 0xFFFF  # Highest Unicode code point in UCS-4
SURROGATE_MIN_CP = 0xD800  # Lowest surrogate code point
SURROGATE_MAX_CP = 0xDFFF  # Highest surrogate code point


def unichr2(ord):
    """
    Like Python's built-in unichr(), just that it works for the entire
    Unicode character set in both narrow and wide Python builds, and with
    both Python 2 and Python 3.

    Returns None for surrogsate code points.
    """
    if ord >= SURROGATE_MIN_CP and ord <= SURROGATE_MAX_CP:
        return None
    if sys.maxunicode == MAX_UNICODE_CP:
        # wide build
        return six.unichr(ord)
    elif ord <= MAX_UCS2_CP:
        # narrow build, low range
        return six.unichr(ord)
    else:
        # narrow build, high range.
        # Python 2 narrow builds store unicode characters internally as
        # UTF-16. The unichr() function however only supports the low range.
        # Literals can be used to create characters in the high range (both
        # with high-range literals and with surrogates).
        # This implementation produces a unicode literal with surrogates
        # and evaluates that to c reate the unicode character.
        # Conversion of high range code points to UTF-16 surrogates:
        # Subtract 0x010000 from the code point, then take the high ten bits
        # of the result and add 0xD800 to get the first surrogate (in range
        # 0xD800-0xDBFF). Take the low ten bits of the result and add 0xDC00
        # to get the second surrogate (in range 0xDC00-0xDFFF).
        offset = ord - MAX_UCS2_CP - 1
        surr1 = (offset >> 10) + 0xD800
        surr2 = (offset & 0b1111111111) + 0xDC00
        lit = u'u"\\u%04X\\u%04X"' % (surr1, surr2)
        uchr = eval(lit)
        return uchr


def print_debug_info():
    print("Debug: sys.stdout: isatty=%r, encoding=%r" %
          (sys.stdout.isatty(), getattr(sys.stdout, 'encoding', None)),
          file=sys.stderr)
    print("Debug: locale.getpreferredencoding()=%r" %
          locale.getpreferredencoding(),
          file=sys.stderr)
    print("Debug: sys.getfilesystemencoding()=%r" %
          sys.getfilesystemencoding(),
          file=sys.stderr)


def run_uprint(text):
    try:
        _uprint(None, text)
    except Exception as exc:
        print("Error: %s raised by: _uprint(None, %r)" %
              (exc.__class__.__name__, text),
              file=sys.stderr)
        print_debug_info()
        sys.stderr.flush()
        raise


def run_print(text):
    try:
        print(text)
    except Exception as exc:
        print("Error: %s raised by: print(%r)" %
              (exc.__class__.__name__, text),
              file=sys.stderr)
        print_debug_info()
        sys.stderr.flush()
        raise


def run_raise(text):
    raise ValueError(text)


def run_catch_print_exc(text):
    try:
        raise ValueError(text)
    except Exception:
        try:
            traceback.print_exc(file=sys.stderr)
        except Exception as exc:
            print("Error: %s raised when printing caught ValueError(%r)\n"
                  "       exception using traceback.print_exc()" %
                  (exc.__class__.__name__, text),
                  file=sys.stderr)
            print_debug_info()
            sys.stderr.flush()
            raise


def run_catch_print(text):
    try:
        raise ValueError(text)
    except Exception as exc1:
        try:
            print(exc1, file=sys.stderr)
        except Exception as exc:
            print("Error: %s raised when printing caught ValueError(%r)\n"
                  "       exception using print(exc)" %
                  (exc.__class__.__name__, text),
                  file=sys.stderr)
            print_debug_info()
            sys.stderr.flush()
            raise


def mode_small(run_func):
    mode_small_ascii_byte(run_func)
    mode_small_ascii(run_func)
    mode_small_latin(run_func)
    mode_small_cyrillic(run_func)
    mode_small_chinese(run_func)
    mode_small_musical(run_func)
    mode_small_emoticons(run_func)


def mode_small_ascii_byte(run_func):
    test_string = b'ASCII-byte: H e l l o'
    run_func(test_string)


def mode_small_ascii(run_func):
    test_string = u'ASCII-unicode: H e l l o'
    run_func(test_string)


def mode_small_latin(run_func):
    test_string = u'UCS-2 Latin-1: ' \
        u'\u00E0 \u00E1 \u00E2 \u00F9 \u00FA \u00FB'
    run_func(test_string)


def mode_small_cyrillic(run_func):
    test_string = u'UCS-2 Cyrillic: ' \
        u'\u041F \u0440 \u0438 \u0432 \u0435 \u0442'
    run_func(test_string)


def mode_small_chinese(run_func):
    test_string = u'UCS-2 Chinese: ' \
        u'\u6C2E \u6C22 \u94A0 \u6CB8 \u98DF \u70F9 \u6797'
    run_func(test_string)


def mode_small_musical(run_func):
    test_string = u'UCS-4 Musical: ' \
        u'\U0001D122 \U0001D11E \U0001D106 \U0001D107'
    run_func(test_string)


def mode_small_emoticons(run_func):
    test_string = u'UCS-4 Emoticons: ' \
        u'\U0001F600 \U0001F607 \U0001F60E \U0001F627'
    run_func(test_string)


def mode_ucs2(run_func):
    for cp in six.moves.xrange(0, MAX_UCS2_CP):
        cp_char = unichr2(cp)
        test_string = u'U+%06X: %s' % (cp, cp_char)
        run_func(test_string)


def mode_all(run_func):
    for cp in six.moves.xrange(0, MAX_UNICODE_CP):
        cp_char = unichr2(cp)
        test_string = u'U+%06X: %s' % (cp, cp_char)
        run_func(test_string)


def main():
    """Main routine"""

    if len(sys.argv) > 1:
        mode = sys.argv[1]
    else:
        mode = 'small'

    if len(sys.argv) > 2:
        run = sys.argv[2]
    else:
        run = 'uprint'

    mode_func = globals().get('mode_' + mode, None)
    if not mode_func:
        modes = [s[5:] for s in globals().keys() if s.startswith('mode_')]
        print("Error: Invalid mode: %s; valid are: %s" %
              (mode, ', '.join(sorted(modes))),
              file=sys.stderr)
        sys.stderr.flush()
        sys.exit(2)

    run_func = globals().get('run_' + run, None)
    if not run_func:
        runs = [s[4:] for s in globals().keys() if s.startswith('run_')]
        print("Error: Invalid run: %s; valid are: %s" %
              (run, ', '.join(sorted(runs))),
              file=sys.stderr)
        sys.stderr.flush()
        sys.exit(2)

    mode_func(run_func)


if __name__ == '__main__':
    main()
