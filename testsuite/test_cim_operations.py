#!/usr/bin/env python
#

"""
Test functions in cim_operations
"""
from __future__ import print_function
import unittest

from pywbem.cim_operations import check_utf8_xml_chars, ParseError

#################################################################
# Test check_utf8_xml_chars function
#################################################################

# pylint: disable=invalid-name
class Test_check_utf8_xml_chars(unittest.TestCase):
    """Test various inputs to the check_utf8_xml_chars function"""

    def setUp(self):
        self.VERBOSE = False

    def _run_single(self, utf8_xml, expected_ok):
        """Run single test from test_all. Executes the check...
           function and catches exceptions
        """
        if self.VERBOSE:
            print('utf8_xml %s type %s ' % (utf8_xml, type(utf8_xml)))
        try:
            check_utf8_xml_chars(utf8_xml, "Test XML")
        except ParseError as exc:
            if self.VERBOSE:
                print("Verify manually: Input XML: %r, ParseError: %s" %\
                      (utf8_xml, exc))
            self.assertFalse(expected_ok,
                             "ParseError unexpectedly raised: %s" % exc)
        else:
            self.assertTrue(expected_ok,
                            "ParseError unexpectedly not raised.")

    def test_all(self):
        """ Test cases. Each case tests a particular utf8 xml string"""

        # good cases
        self._run_single(b'<V>a</V>', True)
        self._run_single(b'<V>a\tb\nc\rd</V>', True)
        self._run_single(b'<V>a\x09b\x0Ac\x0Dd</V>', True)
        self._run_single(b'<V>a\xCD\x90b</V>', True)             # U+350
        self._run_single(b'<V>a\xE2\x80\x93b</V>', True)         # U+2013
        self._run_single(b'<V>a\xF0\x90\x84\xA2b</V>', True)     # U+10122

        # invalid XML characters
        if self.VERBOSE:
            print("From here on, the only expected exception is ParseError "\
                  "for invalid XML characters...")
        self._run_single(b'<V>a\bb</V>', False)
        self._run_single(b'<V>a\x08b</V>', False)
        self._run_single(b'<V>a\x00b</V>', False)
        self._run_single(b'<V>a\x01b</V>', False)
        self._run_single(b'<V>a\x1Ab</V>', False)
        self._run_single(b'<V>a\x1Ab\x1Fc</V>', False)

        # correctly encoded but ill-formed UTF-8
        if self.VERBOSE:
            print("From here on, the only expected exception is ParseError "\
                  "for ill-formed UTF-8 Byte sequences...")
        # combo of U+D800,U+DD22:
        self._run_single(b'<V>a\xED\xA0\x80\xED\xB4\xA2b</V>', False)
        # combo of U+D800,U+DD22 and combo of U+D800,U+DD23:
        # pylint: disable=line-too-long
        self._run_single(b'<V>a\xED\xA0\x80\xED\xB4\xA2b\xED\xA0\x80\xED\xB4\xA3</V>',
                         False)

        # incorrectly encoded UTF-8
        if self.VERBOSE:
            print("From here on, the only expected exception is ParseError "\
                  "for invalid UTF-8 Byte sequences...")
        # incorrect 1-byte sequence:
        self._run_single(b'<V>a\x80b</V>', False)
        # 2-byte sequence with missing second byte:
        self._run_single(b'<V>a\xC0', False)
        # 2-byte sequence with incorrect 2nd byte
        self._run_single(b'<V>a\xC0b</V>', False)
        # 4-byte sequence with incorrect 3rd byte:
        self._run_single(b'<V>a\xF1\x80abc</V>', False)
        # 4-byte sequence with incorrect 3rd byte that is an incorr. new start:
        self._run_single(b'<V>a\xF1\x80\xFFbc</V>', False)
        # 4-byte sequence with incorrect 3rd byte that is an correct new start:
        self._run_single(b'<V>a\xF1\x80\xC2\x81c</V>', False)


if __name__ == '__main__':
    unittest.main()

