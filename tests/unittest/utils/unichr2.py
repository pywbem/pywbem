"""
unichr2() utility function for pywbem testing.
"""

from __future__ import absolute_import, print_function

import sys
import six

SURROGATE_MIN_CP = 0xD800  # Lowest surrogate code point
SURROGATE_MAX_CP = 0xDFFF  # Highest surrogate code point
MAX_UNICODE_CP = 0x10FFFF  # Highest defined Unicode code point
MAX_UCS2_CP = 0xFFFF  # Highest Unicode code point in UCS-4


def unichr2(cp):
    """
    Like Python's built-in unichr(), just that it works for the entire
    Unicode character set in both narrow and wide Python builds, and with
    both Python 2 and Python 3.

    Returns None for surrogsate code points.
    """
    if cp >= SURROGATE_MIN_CP and cp <= SURROGATE_MAX_CP:
        return None

    if sys.maxunicode == MAX_UNICODE_CP:
        # wide build
        return six.unichr(cp)

    if cp <= MAX_UCS2_CP:
        # narrow build, low range
        return six.unichr(cp)

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
    offset = cp - MAX_UCS2_CP - 1
    surr1 = (offset >> 10) + 0xD800
    surr2 = (offset & 0b1111111111) + 0xDC00
    lit = u'u"\\u%04X\\u%04X"' % (surr1, surr2)
    uchr = eval(lit)  # pylint: disable=eval-used
    return uchr
