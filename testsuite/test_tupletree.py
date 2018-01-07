#!/usr/bin/env python
"""
    Test to compare results of DOM tupletree implementation with the
    sax implementation
"""
import os
import xml
import pytest
import unittest
import pprint
import six
from pkg_resources import resource_filename

from pywbem import tupletree, ParseError

pp = pprint.PrettyPrinter(indent=4)  # pylint: disable=invalid-name

test_tuple = (u'CIM',  # pylint: disable=invalid-name
              {u'CIMVERSION': u'2.0', u'DTDVERSION': u'2.0'},
              [(u'MESSAGE',
                {u'ID': u'1001', u'PROTOCOLVERSION': u'1.0'},
                [u'\n',
                 (u'SIMPLERSP',
                  {},
                  [(u'IMETHODRESPONSE',
                    {u'NAME': u'Associators'},
                    [(u'IRETURNVALUE',
                      {},
                      [u'\n    \n',
                       (u'VALUE.OBJECTWITHPATH',
                        {},
                        [u'\n',
                         (u'INSTANCEPATH',
                          {},
                          [u'\n',
                           (u'NAMESPACEPATH',
                            {},
                            [u'\n',
                             (u'HOST',
                              {},
                              [u'10.10.10.10'],
                              None),
                             u'\n',
                             (u'LOCALNAMESPACEPATH',
                              {},
                              [u'\n',
                               (u'NAMESPACE',
                                {u'NAME': u'root'},
                                [],
                                None),
                               u'\n',
                               (u'NAMESPACE',
                                {u'NAME': u'emc'},
                                [],
                                None),
                               u'\n'],
                              None),
                             u'\n'],
                            None),
                           u'\n',
                           (u'INSTANCENAME',
                            {u'CLASSNAME': u'Symm_StorageVolume'},
                            [u'\n',
                             (u'KEYBINDING',
                              {u'NAME': u'CreationClassName'},
                              [(u'KEYVALUE',
                                {u'TYPE': u'string',
                                 u'VALUETYPE': u'string'},
                                [u'Symm_StorageVolume'],
                                None)],
                              None),
                             u'\n',
                             (u'KEYBINDING',
                              {u'NAME': u'DeviceID'},
                              [(u'KEYVALUE',
                                {u'TYPE': u'string',
                                 u'VALUETYPE': u'string'},
                                [u'00000'],
                                None)],
                              None),
                             u'\n',
                             (u'KEYBINDING',
                              {u'NAME': u'SystemCreationClassName'},
                              [(u'KEYVALUE',
                                {u'TYPE': u'string',
                                 u'VALUETYPE': u'string'},
                                [u'Symm_StorageSystem'],
                                None)],
                              None),
                             u'\n',
                             (u'KEYBINDING',
                              {u'NAME': u'SystemName'},
                              [(u'KEYVALUE',
                                {u'TYPE': u'string',
                                 u'VALUETYPE': u'string'},
                                [u'SYMMETRIX-+-000194900000'],
                                None)],
                              None),
                             u'\n'],
                            None),
                           u'\n'],
                          None),
                         u'\n',
                         (u'INSTANCE',
                          {u'CLASSNAME': u'Symm_StorageVolume'},
                          [u'\n',
                           (u'PROPERTY',
                            {u'NAME': u'Usage',
                             u'TYPE': u'uint16'},
                            [(u'VALUE',
                              {},
                              [u'3'],
                              None),
                             u'\n'],
                            None),
                           u'\n'],
                          None),
                         u'\n'],
                        None),
                       u'\n\n'],
                      None)],
                    None)],
                  None)],
                None)],
              None)


# The following was originally the pywbem parser.  Now it is uses simply
# as a check on the sax parser.  Therefore, this code was moved from
# tupletree.py to here for the tests. Nov 2016. Note that this code is
# referenced from other code in the attic so we might not want to eliminate
# in completely.
def dom_to_tupletree(node):
    """Convert a DOM object to a pyRXP-style tuple tree.

    Each element is a 4-tuple of (NAME, ATTRS, CONTENTS, None).

    Very nice for processing complex nested trees.
    """

    if node.nodeType == node.DOCUMENT_NODE:
        # boring; pop down one level
        return dom_to_tupletree(node.firstChild)
    assert node.nodeType == node.ELEMENT_NODE

    name = node.nodeName
    attrs = {}
    contents = []

    for child in node.childNodes:
        if child.nodeType == child.ELEMENT_NODE:
            contents.append(dom_to_tupletree(child))
        elif child.nodeType == child.TEXT_NODE:
            assert isinstance(child.nodeValue, six.string_types), \
                "text node %s is not a string %r" % child
            contents.append(child.nodeValue)
        elif child.nodeType == child.CDATA_SECTION_NODE:
            contents.append(child.nodeValue)
        else:
            raise RuntimeError("can't handle %r" % child)

    for i in range(node.attributes.length):
        attr_node = node.attributes.item(i)
        attrs[attr_node.nodeName] = attr_node.nodeValue

    # XXX: Cannot handle comments, cdata, processing instructions, etc.

    # it's so easy in retrospect!
    return (name, attrs, contents, None)


def xml_to_tupletree(xml_string):
    """
    Parse XML straight into tupletree.
    Uses the minidom to parse xml_string int a dom object.
    This is part of the old obsolete dom code
    """
    dom_xml = xml.dom.minidom.parseString(xml_string)
    return dom_to_tupletree(dom_xml)


class TestTupleTreeRegression(unittest.TestCase):
    """Setup the TupleTree tests"""
    def setUp(self):
        self.data_dir = resource_filename(__name__, 'tupletree_ok')
        # pylint: disable=unused-variable
        for path, dirs, files in os.walk(self.data_dir):
            self.filenames = [os.path.join(path, f) for f in files]

    def test_to_tupletree(self):
        """
        SAX parsing replicates DOM parsing to the tupletree.

        This test compares the input xml compiled with the dom and sax.

        """
        for fn in self.filenames:
            with open(fn, 'rb') as fh:
                xml_str = fh.read()
            tree_dom = xml_to_tupletree(xml_str)
            tree_sax = tupletree.xml_to_tupletree_sax(xml_str, 'Test XML')
            self.assertEqual(tree_dom, tree_sax,
                             'SAX and DOM not equal for %s:\n%s,\n%s'
                             % (fn, pp.pformat(tree_sax), pp.pformat(tree_dom)))


class TestTupleTreeError(unittest.TestCase):
    """Base class for Testing Tuple tree errors. Does setUp and common
       method to test
    """
    def setUp(self):
        """Unittest setUp"""
        self.data_dir = resource_filename(__name__, 'tupletree_error')

    def test_to_tupletree_error(self):
        """SAX parsing generates errors."""
        filename = os.path.join(self.data_dir, 'Associators_error.xml')
        with open(filename, 'rb') as fh:
            xml_str = fh.read()
            self.assertRaises(ParseError,
                              tupletree.xml_to_tupletree_sax,
                              xml_str, 'Test XML')


class TestTupleTreeSax(unittest.TestCase):
    """Class to execute SaxTupleTree tests"""
    def test_xml_to_tupletree_sax(self):
        """
        XML to tupletree with SAX is accurate.

        This test compares data to the test_tuple variable in this file.
        """
        data_dir = resource_filename(__name__, 'tupletree_ok')
        path = os.path.join(data_dir, 'Associators_StorageVolume_small.xml')
        with open(path, 'rb') as fh:
            xml_str = fh.read()
        tree_sax = tupletree.xml_to_tupletree_sax(xml_str, 'Test XML')
        self.assertEqual(test_tuple, tree_sax,
                         'Test tuple and SAX not equal for %s:\n%s,\n%s'
                         % (path, pp.pformat(tree_sax), pp.pformat(tree_sax)))


class Test_check_invalid_utf8_sequences(object):
    """Tests for check_invalid_utf8_sequences()"""

    testcases = [
        # Each testcase has these items:
        # * desc: Short testcase description.
        # * utf8_string: Input string for the function.
        # * exp_exc_type: Expected exception type, or None if expecting success.
        # * condition: Condition for testcase to run.

        # General cases
        (
            "Incorrect type of input string",
            u'<V>ab</V>',
            TypeError, True
        ),

        # Good cases
        (
            "Good case without special chars",
            b'<V>a</V>',
            None, True
        ),
        (
            "Good case with U+0009 (TAB), U+000A (NL), U+000D (CR) chars",
            b'<V>a\x09b\x0Ac\x0Dd</V>',
            None, True
        ),
        (
            "Good case with U+0350 char (in UTF-8)",
            b'<V>a\xCD\x90b</V>',
            None, True
        ),
        (
            "Good case with U+2013 char (in UTF-8)",
            b'<V>a\xE2\x80\x93b</V>',
            None, True
        ),
        (
            "Good case with U+10122 char (in UTF-8)",
            b'<V>a\xF0\x90\x84\xA2b</V>',
            None, True
        ),

        # Correctly encoded but ill-formed UTF-8
        (
            "Ill-formed UTF-8 using surrogate U+D800,U+DD22 "
            "(in otherwise correctly encoded UTF-8)",
            b'<V>a\xED\xA0\x80\xED\xB4\xA2b</V>',
            ParseError, True
        ),
        (
            "Ill-formed UTF-8 using surrogates U+D800,U+DD22 and U+D800,U+DD23 "
            "(in otherwise correctly encoded UTF-8)",
            b'<V>a\xED\xA0\x80\xED\xB4\xA2b\xED\xA0\x80\xED\xB4\xA3</V>',
            ParseError, True
        ),

        # Incorrectly encoded UTF-8
        (
            "Incorrectly encoded UTF-8 with 1-byte sequence",
            b'<V>a\x80b</V>',
            ParseError, True
        ),
        (
            "Incorrectly encoded UTF-8 with 2-byte sequence "
            "with missing second byte",
            b'<V>a\xC0',
            ParseError, True
        ),
        (
            "Incorrectly encoded UTF-8 with 2-byte sequence "
            "with incorrect 2nd byte",
            b'<V>a\xC0b</V>',
            ParseError, True
        ),
        (
            "Incorrectly encoded UTF-8 with 4-byte sequence "
            "with incorrect 3rd byte",
            b'<V>a\xF1\x80abc</V>',
            ParseError, True
        ),
        (
            "Incorrectly encoded UTF-8 with 4-byte sequence "
            "with incorrect 3rd byte that is an incorrect new start",
            b'<V>a\xF1\x80\xFFbc</V>',
            ParseError, True
        ),
        (
            "Incorrectly encoded UTF-8 with 4-byte sequence "
            "with incorrect 3rd byte that is a correct new start",
            b'<V>a\xF1\x80\xC2\x81c</V>',
            ParseError, True
        ),
    ]

    @pytest.mark.parametrize(
        "desc, utf8_string, exp_exc_type, condition",
        testcases
    )
    def test_check_invalid_utf8_sequences(
            self, desc, utf8_string, exp_exc_type, condition):

        if not condition:
            pytest.skip("Condition for test case not met")

        if exp_exc_type is None:

            unicode_string = tupletree.check_invalid_utf8_sequences(
                utf8_string, "Test XML")

            assert isinstance(unicode_string, six.text_type)
            utf8_string_u = utf8_string.decode('utf-8')
            assert unicode_string == utf8_string_u

        else:
            with pytest.raises(exp_exc_type):

                tupletree.check_invalid_utf8_sequences(utf8_string, "Test XML")


class Test_check_invalid_xml_chars(object):
    """Tests for check_invalid_xml_chars()"""

    testcases = [
        # Each testcase has these items:
        # * desc: Short testcase description.
        # * xml_string: Input string for the function.
        # * exp_exc_type: Expected exception type, or None if expecting success.
        # * condition: Condition for testcase to run.

        # General cases
        (
            "Incorrect type of input string",
            b'<V>ab</V>',
            TypeError, True
        ),

        # Good cases
        (
            "Good case without special chars",
            u'<V>a</V>',
            None, True
        ),
        (
            "Good case with U+0009 (TAB), U+000A (NL), U+000D (CR) chars",
            u'<V>a\u0009b\u000Ac\u000Dd</V>',
            None, True
        ),
        (
            "Good case with U+0350 char",
            u'<V>a\u0350b</V>',
            None, True
        ),
        (
            "Good case with U+2013 char",
            u'<V>a\u2013b</V>',
            None, True
        ),
        (
            "Good case with U+10122 char",
            u'<V>a\u010122b</V>',
            None, True
        ),

        # Invalid XML characters
        (
            "Invalid XML char U+0008 (BEL)",
            u'<V>a\u0008b</V>',
            ParseError, True
        ),
        (
            "Invalid XML char U+0000",
            u'<V>a\u0000b</V>',
            ParseError, True
        ),
        (
            "Invalid XML chars U+0001 ... U+0008",
            u'<V>a\u0001b\u0002c\u0003d\u0004e\u0005f\u0006g\u0007h\u0008i</V>',
            ParseError, True
        ),
        (
            "Invalid XML chars U+000B ... U+000C",
            u'<V>a\u000Bb\u000Cc</V>',
            ParseError, True
        ),
        (
            "Invalid XML chars U+000E ... U+0015",
            u'<V>a\u000Eb\u000Fc\u0010d\u0011e\u0012f\u0013g\u0014h\u0015i</V>',
            ParseError, True
        ),
        (
            "Invalid XML chars U+0016 ... U+001D",
            u'<V>a\u0016b\u0017c\u0018d\u0019e\u001Af\u001Bg\u001Ch\u001Di</V>',
            ParseError, True
        ),
        (
            "Invalid XML chars U+001E ... U+001F",
            u'<V>a\u001Eb\u001Fc</V>',
            ParseError, True
        ),
    ]

    @pytest.mark.parametrize(
        "desc, xml_string, exp_exc_type, condition",
        testcases
    )
    def test_check_invalid_xml_chars(
            self, desc, xml_string, exp_exc_type, condition):

        if not condition:
            pytest.skip("Condition for test case not met")

        if exp_exc_type is None:

            tupletree.check_invalid_xml_chars(xml_string, "Test XML")

        else:
            with pytest.raises(exp_exc_type):

                tupletree.check_invalid_xml_chars(xml_string, "Test XML")


if __name__ == '__main__':
    unittest.main()
