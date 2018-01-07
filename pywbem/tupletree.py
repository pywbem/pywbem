#
# (C) Copyright 2003,2004 Hewlett-Packard Development Company, L.P.
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
#
# Author: Martin Pool <mbp@hp.com>
# Author: Ross Peoples <ross.peoples@gmail.com>
#

"""
tupletree - Convert XML DOM objects to and from tuple trees.

DOM is the standard in-memory representation of XML documents, but it
is very cumbersome for some types of processing where XML encodes
object structures rather than text documents.  Direct mapping to Python
classes may not be a good match either.

tupletrees may be created from an in-memory DOM using
dom_to_tupletree(), or from a string using xml_to_tupletree().

Since the Python XML libraries deal mostly with Unicode strings they
are also returned here.  If plain Strings are passed in they will be
converted by xmldom.

Each node of the tuple tree is a Python 4-tuple, corresponding to an
XML Element (i.e. <tag>):

  (NAME, ATTRS, CONTENTS, None)

The NAME is the name of the element.

The ATTRS are a name-value hash of element attributes.

The CONTENTS is a list of child elements.

The fourth element is reserved.
"""

# NOTE: The original dom based parsers have been replaced with a sax parser
#       in Nov. 2016. The dom tupletree code is in the file
#       testsuite/test_tupletree.py

from __future__ import absolute_import

import xml.sax
import re
import sys
import six

from .exceptions import ParseError

__all__ = []


class CIMContentHandler(xml.sax.ContentHandler):
    """SAX handler for CIM XML.

    Similar to dom_to_tupletree, the handler creates a tree of tuples,
    where the elements are the XML element name, the attributes, and the
    children.

    The handler pushes and pops the list of elements, building the child
    list as it goes.

    The end result is that the root node is left in the list and available
    as the root attribute of the object.
    """

    def __init__(self):
        xml.sax.ContentHandler.__init__(self)
        self.root = None
        self.elements = []
        self.element = []

    def startDocument(self):
        assert self.elements == []

    def endDocument(self):
        assert self.elements == []
        self.root = self.element

    def startElement(self, name, attrs):
        if self.element:
            self.elements.append(self.element)
        # Avoid dict comprehension to support python2.6.
        attr_dict = {}
        for k, v in attrs.items():
            attr_dict[k] = v
        element = (name, attr_dict, list(), None)
        if self.element:
            self.element[2].append(element)
        self.element = element

    def endElement(self, name):
        if self.elements:
            self.element = self.elements.pop()

    def characters(self, content):
        if self.element[2]:
            try:
                re.match(r'\s+', self.element[2][-1])
            except TypeError:
                pass
            else:
                ws = self.element[2].pop()
                content = '%s%s' % (ws, content)
        self.element[2].append(content)


def xml_to_tupletree_sax(xml_string, meaning):
    """
    Parse an XML string into tupletree with SAX parser.

    Parses the string using the class CIMContentHandler and
    returns the root element. As a SAX parser it uses minimal
    memory.

    This is a replacement for the previous parser (xml_to_tuple)
    which used the dom parser.

    Parameters:

      xml_string (:term:`string`): A unicode string (when called for embedded
        objects) or byte string (when called for CIM-XML replies) containing
        the XML to be parsed.

      meaning (:term:`string`):
        Short text with meaning of the XML string, for messages in exceptions.

    Returns:
      tupletree tuple with parsed XML tree

    Raises:
      pywbem.ParseError: Error detected by SAX parser or UTF-8/XML checkers
    """

    handler = CIMContentHandler()

    # The following conversion to a byte string is required because the SAX
    # parser in Python 2.6 and 3.4 (pywbem does not support 3.1 - 3.3) does not
    # accept unicode strings, raising:
    #   SAXParseException: "<unknown>:1:1: not well-formed (invalid token)"
    # or:
    #   TypeError: 'str' does not support the buffer interface
    if sys.version_info[0:2] in ((2, 6), (3, 4)):
        if isinstance(xml_string, six.text_type):
            xml_string = xml_string.encode("utf-8")

    try:
        xml.sax.parseString(xml_string, handler, None)
    except (xml.sax.SAXParseException, UnicodeEncodeError) as exc:

        # xml.sax.parse() is documented to only raise SAXParseException, and
        # xml.sax.parseString() in addition has been found to raise
        # UnicodeEncodeError, so only those are caught. Other exception types
        # are unexpected and will perculate upwards.

        # Traceback of the exception that was caught
        org_tb = sys.exc_info()[2]

        # Improve quality of exception info (the check...() functions may
        # raise ParseError):
        if isinstance(xml_string, six.binary_type):
            xml_string = check_invalid_utf8_sequences(xml_string, meaning)
        check_invalid_xml_chars(xml_string, meaning)

        # If the checks above pass, re-raise the SAX exception info, with its
        # original traceback info:
        pe = ParseError("SAXParseException raised when parsing %s: %s" %
                        (meaning, exc))
        six.reraise(type(pe), pe, org_tb)  # ignore this call in traceback!

    return handler.root


# Patterns for check_invalid_utf8_sequences()
_ILL_FORMED_UTF8_RE = re.compile(
    b'(\xED[\xA0-\xBF][\x80-\xBF])')    # U+D800...U+DFFF


def check_invalid_utf8_sequences(utf8_string, meaning):
    """
    Examine a UTF-8 encoded string and raise a `pywbem.ParseError` exception if
    the string contains invalid UTF-8 sequences (incorrectly encoded or
    ill-formed).

    This function works in both "wide" and "narrow" Unicode builds of Python
    and supports the full range of Unicode characters from U+0000 to U+10FFFF.

    This function is used to improve the error information raised from Python's
    `xml.dom.minidom` and `xml.sax` packages and should be called only after
    having catched an `ExpatError` from `xml.dom.minidom` or a
    `SAXParseException` from `xml.sax` .

    Parameters:

      utf8_string (:term:`byte string`):
        The UTF-8 encoded XML string to be examined.

      meaning (:term:`string`):
        Short text with meaning of the XML string, for messages in exceptions.

    Returns:

      :term:`unicode string`: The input string, converted to Unicode.

    Raises:

      TypeError: Invoked with incorrect Python object type for `utf8_xml`.

      :class:`~pywbem.ParseError: `utf8_xml` contains invalid UTF-8 sequences.

    Notes on Unicode support in Python:

    (1) For internally representing Unicode characters in the unicode type, a
        "wide" Unicode build of Python uses UTF-32, while a "narrow" Unicode
        build uses UTF-16. The difference is visible to Python programs for
        Unicode characters assigned to code points above U+FFFF: The "narrow"
        build uses 2 characters (a surrogate pair) for them, while the "wide"
        build uses just 1 character. This affects all position- and
        length-oriented functions, such as `len()` or string slicing.

    (2) In a "wide" Unicode build of Python, the Unicode characters assigned to
        code points U+10000 to U+10FFFF are represented directly (using code
        points U+10000 to U+10FFFF) and the surrogate code points
        U+D800...U+DFFF are never used; in a "narrow" Unicode build of Python,
        the Unicode characters assigned to code points U+10000 to U+10FFFF are
        represented using pairs of the surrogate code points U+D800...U+DFFF.

    Notes on the Unicode code points U+D800...U+DFFF ("surrogate code points"):

    (1) These code points have no corresponding Unicode characters assigned,
        because they are reserved for surrogates in the UTF-16 encoding.

    (2) The UTF-8 encoding can technically represent the surrogate code points.
        ISO/IEC 10646 defines that a UTF-8 sequence containing the surrogate
        code points is ill-formed, but it is technically possible that such a
        sequence is in a UTF-8 encoded XML string.

    (3) The Python escapes ``\\u`` and ``\\U`` used in literal strings can
        represent the surrogate code points (as well as all other code points,
        regardless of whether they are assigned to Unicode characters).

    (4) The Python `encode()` and `decode()` functions successfully
        translate the surrogate code points back and forth for encoding UTF-8.

        For example, ``b'\\xed\\xb0\\x80'.decode("utf-8") = u'\\udc00'``.

    (5) Because Python supports the encoding and decoding of UTF-8 sequences
        also for the surrogate code points, the "narrow" Unicode build of
        Python can be (mis-)used to transport each surrogate unit separately
        encoded in (ill-formed) UTF-8.

        For example, code point U+10122 can be (illegally) created from a
        sequence of code points U+D800,U+DD22 represented in UTF-8:

          ``b'\\xED\\xA0\\x80\\xED\\xB4\\xA2'.decode("utf-8") = u'\\U00010122'``

        while the correct UTF-8 sequence for this code point is:

          ``u'\\U00010122'.encode("utf-8") = b'\\xf0\\x90\\x84\\xa2'``
    """

    context_before = 16    # number of chars to print before any bad chars
    context_after = 16     # number of chars to print after any bad chars

    if not isinstance(utf8_string, six.binary_type):
        raise TypeError("utf8_string parameter is not a byte string, "
                        "but has type %s" % type(utf8_string))

    # Check for ill-formed UTF-8 sequences. This needs to be done
    # before the str type gets decoded to unicode, because afterwards
    # surrogates produced from ill-formed UTF-8 cannot be distinguished from
    # legally produced surrogates (for code points above U+FFFF).
    ifs_list = list()
    for m in _ILL_FORMED_UTF8_RE.finditer(utf8_string):
        ifs_pos = m.start(1)
        ifs_seq = m.group(1)
        ifs_list.append((ifs_pos, ifs_seq))
    if ifs_list:
        exc_txt = "Ill-formed (surrogate) UTF-8 Byte sequences found in %s:" %\
                  meaning
        for (ifs_pos, ifs_seq) in ifs_list:
            exc_txt += "\n  At offset %d:" % ifs_pos
            for ifs_ord in six.iterbytes(ifs_seq):
                exc_txt += " 0x%02X" % ifs_ord
            cpos1 = max(ifs_pos - context_before, 0)
            cpos2 = min(ifs_pos + context_after, len(utf8_string))
            exc_txt += ", CIM-XML snippet: %r" % utf8_string[cpos1:cpos2]
        raise ParseError(exc_txt)

    # Check for incorrectly encoded UTF-8 sequences.
    # @ibm.13@ Simplified logic (removed loop).
    try:
        utf8_string_u = utf8_string.decode("utf-8")
    except UnicodeDecodeError as exc:
        # Only raised for incorrectly encoded UTF-8 sequences; technically
        # correct sequences that are ill-formed (e.g. representing surrogates)
        # do not cause this exception to be raised.
        # If more than one incorrectly encoded sequence is present, only
        # information about the first one is returned in the exception object.
        # Also, the stated reason (in _msg) is not always correct.

        # pylint: disable=unbalanced-tuple-unpacking
        unused_codec, unused_str, _p1, _p2, unused_msg = exc.args

        exc_txt = "Incorrectly encoded UTF-8 Byte sequences found in %s" %\
                  meaning
        exc_txt += "\n  At offset %d:" % _p1
        ies_seq = utf8_string[_p1:_p2 + 1]
        for ies_ord in six.iterbytes(ies_seq):
            exc_txt += " 0x%02X" % ies_ord
        cpos1 = max(_p1 - context_before, 0)
        cpos2 = min(_p2 + context_after, len(utf8_string))
        exc_txt += ", CIM-XML snippet: %r" % utf8_string[cpos1:cpos2]
        raise ParseError(exc_txt)

    return utf8_string_u


# Patterns for check_invalid_xml_chars()
if len(u'\U00010122') == 2:
    # This is a "narrow" Unicode build of Python (the normal case).
    _ILLEGAL_XML_CHARS_RE = re.compile(
        u'([\u0000-\u0008\u000B-\u000C\u000E-\u001F\uFFFE\uFFFF])')
else:
    # This is a "wide" Unicode build of Python.
    _ILLEGAL_XML_CHARS_RE = re.compile(
        u'([\u0000-\u0008\u000B-\u000C\u000E-\u001F\uD800-\uDFFF\uFFFE\uFFFF])')


def check_invalid_xml_chars(xml_string, meaning):
    """
    Examine an XML string and raise a `pywbem.ParseError` exception if the
    string contains characters that cannot legally be represented as XML
    characters.

    This function is used to improve the error information raised from Python's
    `xml.dom.minidom` and `xml.sax` packages and should be called only after
    having catched an `ExpatError` from `xml.dom.minidom` or a
    `SAXParseException` from `xml.sax` .

    Parameters:

      xml_string (:term:`unicode string`):
        The XML string to be examined.

      meaning (:term:`string`):
        Short text with meaning of the XML string, for messages in exceptions.

    Raises:

      TypeError: Invoked with incorrect Python object type for `xml_string`.

      :class:`~pywbem.ParseError: `xml_string` contains invalid XML characters.

    Notes on XML characters:

    (1) The legal XML characters are defined in W3C XML 1.0 (Fith Edition):

          ::

            Char ::= #x9 | #xA | #xD | [#x20-#xD7FF] | [#xE000-#xFFFD] |
                     [#x10000-#x10FFFF]

        These are the code points of Unicode characters using a non-surrogate
        representation.
    """

    context_before = 16    # number of chars to print before any bad chars
    context_after = 16     # number of chars to print after any bad chars

    if not isinstance(xml_string, six.text_type):
        raise TypeError("xml_string parameter is not a unicode string, "
                        "but has type %s" % type(xml_string))

    # Check for Unicode characters that cannot legally be represented as XML
    # characters.
    ixc_list = list()
    last_ixc_pos = -2
    for m in _ILLEGAL_XML_CHARS_RE.finditer(xml_string):
        ixc_pos = m.start(1)
        ixc_char = m.group(1)
        if ixc_pos > last_ixc_pos + 1:
            ixc_list.append((ixc_pos, ixc_char))
        last_ixc_pos = ixc_pos
    if ixc_list:
        exc_txt = "Invalid XML characters found in %s:" % meaning
        for (ixc_pos, ixc_char) in ixc_list:
            cpos1 = max(ixc_pos - context_before, 0)
            cpos2 = min(ixc_pos + context_after, len(xml_string))
            exc_txt += "\n  At offset %d: U+%04X, CIM-XML snippet: %r" % \
                (ixc_pos, ord(ixc_char), xml_string[cpos1:cpos2])
        raise ParseError(exc_txt)
