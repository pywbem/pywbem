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
_tupletree - Convert XML DOM objects to and from tuple trees.

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

The ATTRS are a name-value dictionary of element attributes, not preserving
order.

The CONTENTS is a list of child elements, preserving order.

The fourth element is reserved.
"""

# NOTE: The original dom based parsers have been replaced with a sax parser
#       in Nov. 2016. The dom tupletree code is in the file
#       tests/unittest/pywbem/test_tupletree.py

from __future__ import absolute_import

import xml.sax
import re
import sys
import six

from ._exceptions import XMLParseError
from ._utils import _format, _ensure_bytes

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
        # Note: attrs is a SAX Attributes object which implements a subset of
        # dictionary methods, but does not preserve order. So this handler
        # cannot preserve attribute order, because it is already lost when it
        # gets control.
        if self.element:
            self.elements.append(self.element)
        attr_dict = {}  # No order preservation possible, see note above
        for k, v in attrs.items():
            attr_dict[k] = v
        element = (name, attr_dict, [])
        if self.element:
            self.element[2].append(element)
        self.element = element

    def endElement(self, name):
        if self.elements:
            self.element = self.elements.pop()

    def characters(self, content):
        children = self.element[2]  # mutable list
        # If the last node is a character node, append the content to it.
        # Otherwise, append a new character node with the content.
        if children and isinstance(children[-1], six.text_type):
            children[-1] += content
        else:
            children.append(content)


def xml_to_tupletree_sax(xml_string, meaning, conn_id=None):
    """
    Parse an XML string into tupletree with SAX parser.

    Parses the string using the class CIMContentHandler and
    returns the root element. As a SAX parser it uses minimal
    memory.

    This is a replacement for the previous parser (xml_to_tuple)
    which used the dom parser.

    Parameters:

      xml_string (:term:`string`): A unicode string (when called for embedded
        objects) or UTF-8 encoded byte string (when called for CIM-XML
        replies) containing the XML to be parsed.

      meaning (:term:`string`):
        Short text with meaning of the XML string, for messages in exceptions.

      conn_id (:term:`connection id`): Connection ID to be used in any
        exceptions that may be raised.

    Returns:

      tupletree tuple with parsed XML tree

    Raises:

      pywbem.XMLParseError: Error detected by SAX parser or UTF-8/XML checkers
    """

    handler = CIMContentHandler()

    # The following conversion to a byte string is required for two reasons:
    # 1. xml.sax.parseString() raises UnicodeEncodeError for unicode strings
    #    that contain any non-ASCII characters (despite its Python 2.7
    #    documentation which states that would be supported).
    # 2. The SAX parser in Python 2.6 and 3.4 (pywbem does not support 3.1 -
    #    3.3) does not accept unicode strings, raising:
    #      SAXParseException: "<unknown>:1:1: not well-formed (invalid token)"
    #    or:
    #      TypeError: 'str' does not support the buffer interface
    xml_string = _ensure_bytes(xml_string)

    try:
        xml.sax.parseString(xml_string, handler, None)
    except xml.sax.SAXParseException as exc:

        # xml.sax.parse() is documented to only raise SAXParseException. In
        # earlier versions of this code, xml.sax.parseString() has been found
        # to raise UnicodeEncodeError when unicode strings were passed, but
        # that is no longer done, so that exception is no longer caught.
        # Other exception types are unexpected and will perculate upwards.

        # Traceback of the exception that was caught
        org_tb = sys.exc_info()[2]

        # Improve quality of exception info (the check...() functions may
        # raise XMLParseError):
        _chk_str = check_invalid_utf8_sequences(xml_string, meaning, conn_id)
        check_invalid_xml_chars(_chk_str, meaning, conn_id)

        # If the checks above pass, re-raise the SAX exception info, with its
        # original traceback info:
        lineno, colno, new_colno, line = get_failing_line(xml_string, str(exc))
        if lineno is not None:
            marker_line = ' ' * (new_colno - 1) + '^'
            xml_msg = _format(
                "Line {0} column {1} of XML string (as binary UTF-8 string):\n"
                "{2}\n"
                "{3}",
                lineno, colno, line, marker_line)
        else:
            xml_msg = _format(
                "XML string (as binary UTF-8 string):\n"
                "{0}",
                line)

        pe = XMLParseError(
            _format("XML parsing error encountered in {0}: {1}\n{2}\n",
                    meaning, exc, xml_msg),
            conn_id=conn_id)
        six.reraise(type(pe), pe, org_tb)  # ignore this call in traceback!

    return handler.root


def truncate_line(line, colno, max_before, max_after):
    """
    Truncate the line (binary string) so that left of the 1-based colno
    poasition there are at most max_before characters, and right of the
    colno position there are at most max_after characters.
    If truncated, '...' is added before or after to indicate the truncation.
    Returns a tuple (truncated line, new position)
    """
    line_len = len(line)
    new_colno = colno
    truncated_after = False
    truncated_before = False
    len_after = line_len - colno
    if len_after > max_after:
        truncated_after = True
        line = line[:colno + max_after]
    len_before = colno - 1
    if len_before > max_before:
        truncated_before = True
        line = line[len_before - max_before:]
        new_colno -= len_before - max_before
    line = _format("{0!A}", line)
    new_colno += 1  # the leading single quote
    if truncated_before:
        line = '...' + line
        new_colno += 3
    if truncated_after:
        line = line + '...'
    return line, new_colno


def get_failing_line(xml_string, exc_msg):
    """
    Extract the failing line from the XML string, as indicated by the
    line/column information in the exception message.

    Returns a tuple (lineno, colno, new_pos, line), where lineno and colno
    and marker_pos may be None.
    """
    max_before = 500  # max characters before reported position
    max_after = 500  # max characters after reported position
    max_unknown = 1000  # max characters when position cannot be determined
    assert isinstance(xml_string, six.binary_type)
    m = re.search(r':(\d+):(\d+):', exc_msg)
    if not m:
        xml_string, _ = truncate_line(xml_string, 1, 0, max_unknown - 1)
        return None, None, None, xml_string
    lineno = int(m.group(1))
    colno = int(m.group(2))
    if not xml_string.endswith(b'\n'):
        xml_string += b'\n'
    xml_lines = xml_string.splitlines()
    if len(xml_lines) < lineno:
        # This really should not happen; it means the line parsing went wrong
        # or SAX reported incorrect lines. We do not particularly care for
        # this case and simply truncate the string.
        xml_string, _ = truncate_line(xml_string, 1, 0, max_unknown - 1)
        return None, None, None, xml_string
    line = xml_lines[lineno - 1]
    line, new_pos = truncate_line(line, colno, max_before, max_after)
    return lineno, colno, new_pos, line


# Patterns for check_invalid_utf8_sequences()
_ILL_FORMED_UTF8_RE = re.compile(
    b'(\xED[\xA0-\xBF][\x80-\xBF])')    # U+D800...U+DFFF


def check_invalid_utf8_sequences(utf8_string, meaning, conn_id=None):
    """
    Examine a UTF-8 encoded string and raise a `pywbem.XMLParseError` exception
    if the string contains invalid UTF-8 sequences (incorrectly encoded or
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

      conn_id (:term:`connection id`): Connection ID to be used in any
        exceptions that may be raised.

    Returns:

      :term:`unicode string`: The input string, converted to Unicode.

    Raises:

      TypeError: Invoked with incorrect Python object type for `utf8_xml`.

      pywbem.XMLParseError: `utf8_xml` contains invalid UTF-8 sequences.

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
        That is the case in both Python 2 and Python 3.

    (4) In Python 2, the `unicode.encode()` and `str.decode()` methods
        successfully translate surrogate code points back and forth for
        encoding UTF-8, tolerating invalid surrogate sequences.

        For example, ``b'\\xed\\xb0\\x80'.decode("utf-8") = u'\\udc00'``.

        In Python 3, the `str.encode()` and `bytes.decode()` methods raise
        UnicodeEncodeError / UnicodeDecodeError for invalid surrogate
        sequences. However, the `codecs.encode()` and `codecs.decode()`
        methods have an error handler 'surrogatepass' which tolerates
        invalid surrogate sequences.

    (5) Because Python 2 supports the encoding and decoding of UTF-8 sequences
        also for the surrogate code points, the "narrow" Unicode build of
        Python 2 can be (mis-)used to transport each surrogate unit separately
        encoded in (ill-formed) UTF-8.

        For example, code point U+10122 can be (illegally) created from a
        sequence of code points U+D800,U+DD22 represented in UTF-8:

          ``b'\\xED\\xA0\\x80\\xED\\xB4\\xA2'.decode("utf-8") = u'\\U00010122'``

        while the correct UTF-8 sequence for this code point is:

          ``u'\\U00010122'.encode("utf-8") = b'\\xf0\\x90\\x84\\xa2'``
    """

    context_before = 16    # number of chars to print before any bad chars
    context_after = 16     # number of chars to print after any bad chars

    try:
        assert isinstance(utf8_string, six.binary_type)
    except AssertionError:
        raise TypeError(
            _format("utf8_string parameter is not a byte string, but has "
                    "type {0}", type(utf8_string)))

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
        exc_txt = _format("Ill-formed (surrogate) UTF-8 Byte sequences found "
                          "in {0}:", meaning)
        for (ifs_pos, ifs_seq) in ifs_list:
            exc_txt += "\n  At offset {0}:".format(ifs_pos)
            for ifs_ord in six.iterbytes(ifs_seq):
                exc_txt += " 0x{0:02X}".format(ifs_ord)
            cpos1 = max(ifs_pos - context_before, 0)
            cpos2 = min(ifs_pos + context_after, len(utf8_string))
            exc_txt += _format(", CIM-XML snippet: {0!A}",
                               utf8_string[cpos1:cpos2])
        raise XMLParseError(exc_txt, conn_id=conn_id)

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

        exc_txt = "Incorrectly encoded UTF-8 Byte sequences found in {0}". \
            format(meaning)
        exc_txt += "\n  At offset {0}:".format(_p1)
        ies_seq = utf8_string[_p1:_p2 + 1]
        for ies_ord in six.iterbytes(ies_seq):
            exc_txt += " 0x{0:02X}".format(ies_ord)
        cpos1 = max(_p1 - context_before, 0)
        cpos2 = min(_p2 + context_after, len(utf8_string))
        exc_txt += _format(", CIM-XML snippet: {0!A}",
                           utf8_string[cpos1:cpos2])
        raise XMLParseError(exc_txt, conn_id=conn_id)

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


def check_invalid_xml_chars(xml_string, meaning, conn_id=None):
    """
    Examine an XML string and raise a `pywbem.XMLParseError` exception if the
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

      conn_id (:term:`connection id`): Connection ID to be used in any
        exceptions that may be raised.

    Raises:

      TypeError: Invoked with incorrect Python object type for `xml_string`.

      pywbem.XMLParseError: `xml_string` contains invalid XML characters.

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

    try:
        assert isinstance(xml_string, six.text_type)
    except AssertionError:
        raise TypeError(
            _format("xml_string parameter is not a unicode string, but has "
                    "type {0}", type(xml_string)))

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
        exc_txt = "Invalid XML characters found in {0}:".format(meaning)
        for (ixc_pos, ixc_char) in ixc_list:
            cpos1 = max(ixc_pos - context_before, 0)
            cpos2 = min(ixc_pos + context_after, len(xml_string))
            exc_txt += _format("\n  At offset {0}: U+{1:04X}, "
                               "CIM-XML snippet: {2!A}",
                               ixc_pos, ord(ixc_char), xml_string[cpos1:cpos2])
        raise XMLParseError(exc_txt, conn_id=conn_id)
