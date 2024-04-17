#!/usr/bin/env python
"""
Test cases for _tupletree module and Unicode/XML check functions.
"""

import xml
import re

import pytest

# pylint: disable=wrong-import-position, wrong-import-order, invalid-name
from ...utils import import_installed
pywbem = import_installed('pywbem')
from pywbem import _tupletree, ParseError  # noqa: E402
# pylint: enable=wrong-import-position, wrong-import-order, invalid-name


# The following was originally the pywbem parser.  Now it is used simply as a
# check on the SAX parser.  Therefore, this code was moved from _tupletree.py to
# here for the tests. Note that this code is referenced from other code in the
# attic so we might not want to eliminate it completely.

def dom_to_tupletree(node):
    """
    Convert a DOM object to a pyRXP-style tuple tree.

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
            assert isinstance(child.nodeValue, str), \
                "text node %s is not a string %r" % child
            contents.append(child.nodeValue)
        elif child.nodeType == child.CDATA_SECTION_NODE:
            contents.append(child.nodeValue)
        else:
            raise RuntimeError("can't handle %r" % child)

    for i in range(node.attributes.length):
        attr_node = node.attributes.item(i)
        attrs[attr_node.nodeName] = attr_node.nodeValue

    # TODO: Cannot handle comments, cdata, processing instructions, etc.

    # it's so easy in retrospect!
    return (name, attrs, contents)


def xml_to_tupletree(xml_string):
    """
    Parse XML straight into tupletree.
    Uses the minidom to parse xml_string int a dom object.
    This is part of the old obsolete dom code
    """
    dom_xml = xml.dom.minidom.parseString(xml_string)
    return dom_to_tupletree(dom_xml)


class Test_xml_to_tupletree_sax:
    # pylint: disable=too-few-public-methods
    """
    Exhaustive tests for _tupletree.xml_to_tupletree_sax(), with inline input
    XML and expected tupletrees (for success) or exceptions (for failures).

    A comparison with the result of the previously implemented DOM based
    pywbem parser ensures that the SAX parsing is compatible.
    """

    testcases = [
        # Each testcase has these items:
        # * desc: Short testcase description.
        # * xml_string: XML string to be parsed, as unicode string.
        # * exp_tupletree: Expected tupletree parse result,
        #   or None if expecting failure.
        # * exp_exc_type: Expected exception type,
        #   or None if expecting success.
        # * exp_exc_msg_pattern: Expected pattern in exception message,
        #   or None if expecting success.
        # * condition: Condition for testcase to run.

        # General good cases
        (
            "One-line XML string with one empty element",
            '<?xml version="1.0" encoding="utf-8" ?>'
            '<TEXT></TEXT>',
            ('TEXT',
             {},
             []),
            None, None,
            True
        ),
        (
            "One-line XML string with one empty element, short form",
            '<?xml version="1.0" encoding="utf-8" ?>'
            '<TEXT/>',
            ('TEXT',
             {},
             []),
            None, None,
            True
        ),
        (
            "One-line XML string with one element with ASCII text",
            '<?xml version="1.0" encoding="utf-8" ?>'
            '<TEXT>foo</TEXT>',
            ('TEXT',
             {},
             ['foo']),
            None, None,
            True
        ),
        (
            "One-line XML string with one element with non-ASCII UCS-2 text",
            '<?xml version="1.0" encoding="utf-8" ?>'
            '<TEXT>\u00e8</TEXT>',
            ('TEXT',
             {},
             ['\u00e8']),
            None, None,
            True
        ),
        (
            "One-line XML string with one element with non-UCS-2 text",
            '<?xml version="1.0" encoding="utf-8" ?>'
            '<TEXT>\U00010142</TEXT>',  # GREEK ACROPHONIC ATTIC ONE DRACHMA
            ('TEXT',
             {},
             ['\U00010142']),
            None, None,
            True
        ),
        (
            "One-line XML string with one element with one attribute",
            '<?xml version="1.0" encoding="utf-8" ?>'
            '<TEXT ATTR="foo">bar</TEXT>',
            ('TEXT',
             {'ATTR': 'foo'},
             ['bar']),
            None, None,
            True
        ),
        (
            "One-line XML string with one element with two attributes",
            '<?xml version="1.0" encoding="utf-8" ?>'
            '<TEXT ATTR1="foo1" ATTR2="foo2">bar</TEXT>',
            ('TEXT',
             {'ATTR1': 'foo1', 'ATTR2': 'foo2'},
             ['bar']),
            None, None,
            True
        ),
        (
            "One-line XML string with two elements and two attributes",
            '<?xml version="1.0" encoding="utf-8" ?>'
            '<TEXT1 ATTR1="foo1"><TEXT2 ATTR2="foo2">bar</TEXT2></TEXT1>',
            ('TEXT1',
             {'ATTR1': 'foo1'},
             [('TEXT2',
               {'ATTR2': 'foo2'},
               ['bar'])]),
            None, None,
            True
        ),

        # Multi-line good cases
        (
            "Multi-line XML string, text without newline",
            '<?xml version="1.0" encoding="utf-8" ?>\n'
            '<TEXT1 ATTR1="foo1">\n'
            '<TEXT2 ATTR2="foo2">bar</TEXT2>\n'
            '</TEXT1>',
            ('TEXT1',
             {'ATTR1': 'foo1'},
             ['\n',
              ('TEXT2',
               {'ATTR2': 'foo2'},
               ['bar']),
              '\n']),
            None, None,
            True
        ),
        (
            "Multi-line XML string, text with newlines",
            '<?xml version="1.0" encoding="utf-8" ?>\n'
            '<TEXT1 ATTR1="foo1">\n'
            '<TEXT2 ATTR2="foo2">\n'
            'bar\n'
            '</TEXT2>\n'
            '</TEXT1>',
            ('TEXT1',
             {'ATTR1': 'foo1'},
             ['\n',
              ('TEXT2',
               {'ATTR2': 'foo2'},
               ['\nbar\n']),
              '\n']),
            None, None,
            True
        ),

        # General failure cases
        (
            "Empty XML string",
            '',
            None,
            ParseError, "XML parsing error.*no element found",
            True
        ),
        (
            "Just the XML prolog",
            '<?xml version="1.0" encoding="utf-8" ?>',
            None,
            ParseError, "XML parsing error.*no element found",
            True
        ),
        (
            "Start element without end element",
            '<?xml version="1.0" encoding="utf-8" ?>'
            '<ELEM>',
            None,
            ParseError, "XML parsing error.*no element found",
            True
        ),
        (
            "End element misses trailing angle bracket",
            '<?xml version="1.0" encoding="utf-8" ?>'
            '<ELEM>abc</ELEM',
            None,
            ParseError, "XML parsing error.*unclosed token",
            True
        ),
        (
            "End element misses leading angle bracket",
            '<?xml version="1.0" encoding="utf-8" ?>'
            '<ELEM>abc/ELEM>',
            None,
            ParseError, "XML parsing error.*no element found",
            True
        ),
        (
            "Start element misses trailing angle bracket",
            '<?xml version="1.0" encoding="utf-8" ?>'
            '<ELEM</ELEM>',
            None,
            ParseError, "XML parsing error.*not well-formed",
            True
        ),
        (
            "Start element misses leading angle bracket",
            '<?xml version="1.0" encoding="utf-8" ?>'
            'ELEM></ELEM>',
            None,
            ParseError, "XML parsing error.*syntax error",
            True
        ),

        # Failure cases with line number checking
        (
            "Failing multi-line XML string with failure in line 3",
            '<?xml version="1.0" encoding="utf-8" ?>\n'
            '<ELEM1>\n'
            '<ELEM2</ELEM2>\n'
            '<ELEM1>\n',
            None,
            ParseError,
            "XML parsing error.*not well-formed.*"
            "Line 3 column 6 of XML string.*"
            "<ELEM2</ELEM2>",
            True
        ),

        # Failure cases with non-ASCII chars
        (
            "Failing XML string with non-ASCII attribute value",
            '<?xml version="1.0" encoding="utf-8" ?>'
            '<ELEM1 ATTR1="\u00e8"></ELEM2>',
            None,
            ParseError,
            "XML parsing error.*mismatched tag.*"
            "Line 1 column 58 of XML string.*"
            r'<ELEM1 ATTR1="\\xc3\\xa8"></ELEM2>',
            True
        ),

        # CIM-XML cases
        (
            "CIM-XML response with MESSAGE end element missing "
            "(former Associators_error.xml file)",
            '<?xml version="1.0" encoding="utf-8" ?>\n'
            '<CIM CIMVERSION="2.0" DTDVERSION="2.0">\n'
            '  <MESSAGE ID="1001" PROTOCOLVERSION="1.0">\n'
            '    <SIMPLERSP>\n'
            '      <IMETHODRESPONSE NAME="Associators">\n'
            '        <IRETURNVALUE>\n'
            '        </IRETURNVALUE>\n'
            '      </IMETHODRESPONSE>\n'
            '    </SIMPLERSP>\n'
            '</CIM>\n',
            None,
            ParseError, "XML parsing error.*mismatched tag",
            True
        ),
        (
            "CIM-XML response from Associators operation "
            "(former Associators_Empty.xml)",
            '<?xml version="1.0" encoding="utf-8" ?>\n'
            '<CIM CIMVERSION="2.0" DTDVERSION="2.0">\n'
            '  <MESSAGE ID="1001" PROTOCOLVERSION="1.0">\n'
            '    <SIMPLERSP>\n'
            '      <IMETHODRESPONSE NAME="Associators">\n'
            '        <IRETURNVALUE>\n'
            '        </IRETURNVALUE>\n'
            '      </IMETHODRESPONSE>\n'
            '    </SIMPLERSP>\n'
            '  </MESSAGE>\n'
            '</CIM>\n',
            ('CIM',
             {'CIMVERSION': '2.0', 'DTDVERSION': '2.0'},
             ['\n  ',
              ('MESSAGE',
               {'ID': '1001', 'PROTOCOLVERSION': '1.0'},
               ['\n    ',
                ('SIMPLERSP',
                 {},
                 ['\n      ',
                  ('IMETHODRESPONSE',
                   {'NAME': 'Associators'},
                   ['\n        ',
                    ('IRETURNVALUE',
                     {},
                     ['\n        ']),
                    '\n      ']),
                  '\n    ']),
                '\n  ']),
              '\n']),
            None, None,
            True
        ),
        (
            "CIM-XML response from Associators operation "
            "(former Associators_StorageVolume_small.xml)",
            '<?xml version="1.0" encoding="utf-8" ?>\n'
            '<CIM CIMVERSION="2.0" DTDVERSION="2.0"><MESSAGE ID="1001" '
            'PROTOCOLVERSION="1.0">\n'
            '<SIMPLERSP><IMETHODRESPONSE NAME="Associators"><IRETURNVALUE>\n'
            '    \n'
            '<VALUE.OBJECTWITHPATH>\n'
            '<INSTANCEPATH>\n'
            '<NAMESPACEPATH>\n'
            '<HOST>10.10.10.10</HOST>\n'
            '<LOCALNAMESPACEPATH>\n'
            '<NAMESPACE NAME="root"/>\n'
            '<NAMESPACE NAME="emc"/>\n'
            '</LOCALNAMESPACEPATH>\n'
            '</NAMESPACEPATH>\n'
            '<INSTANCENAME CLASSNAME="Symm_StorageVolume">\n'
            '<KEYBINDING NAME="CreationClassName"><KEYVALUE '
            'VALUETYPE="string" TYPE="string">Symm_StorageVolume</KEYVALUE>'
            '</KEYBINDING>\n'
            '<KEYBINDING NAME="DeviceID"><KEYVALUE VALUETYPE="string" '
            'TYPE="string">00000</KEYVALUE></KEYBINDING>\n'
            '<KEYBINDING NAME="SystemCreationClassName"><KEYVALUE '
            'VALUETYPE="string" TYPE="string">Symm_StorageSystem</KEYVALUE>'
            '</KEYBINDING>\n'
            '<KEYBINDING NAME="SystemName"><KEYVALUE VALUETYPE="string" '
            'TYPE="string">SYMMETRIX-+-000194900000</KEYVALUE></KEYBINDING>\n'
            '</INSTANCENAME>\n'
            '</INSTANCEPATH>\n'
            '<INSTANCE CLASSNAME="Symm_StorageVolume">\n'
            '<PROPERTY NAME="Usage" TYPE="uint16"><VALUE>3</VALUE>\n'
            '</PROPERTY>\n'
            '</INSTANCE>\n'
            '</VALUE.OBJECTWITHPATH>\n'
            '\n'
            '</IRETURNVALUE></IMETHODRESPONSE></SIMPLERSP></MESSAGE></CIM>\n',
            ('CIM',
             {'CIMVERSION': '2.0', 'DTDVERSION': '2.0'},
             [('MESSAGE',
               {'ID': '1001', 'PROTOCOLVERSION': '1.0'},
               ['\n',
                ('SIMPLERSP',
                 {},
                 [('IMETHODRESPONSE',
                   {'NAME': 'Associators'},
                   [('IRETURNVALUE',
                     {},
                     ['\n    \n',
                      ('VALUE.OBJECTWITHPATH',
                       {},
                       ['\n',
                        ('INSTANCEPATH',
                         {},
                         ['\n',
                          ('NAMESPACEPATH',
                           {},
                           ['\n',
                            ('HOST',
                             {},
                             ['10.10.10.10']),
                            '\n',
                            ('LOCALNAMESPACEPATH',
                             {},
                             ['\n',
                              ('NAMESPACE',
                               {'NAME': 'root'},
                               []),
                              '\n',
                              ('NAMESPACE',
                               {'NAME': 'emc'},
                               []),
                              '\n']),
                            '\n']),
                          '\n',
                          ('INSTANCENAME',
                           {'CLASSNAME': 'Symm_StorageVolume'},
                           ['\n',
                            ('KEYBINDING',
                             {'NAME': 'CreationClassName'},
                             [('KEYVALUE',
                               {'TYPE': 'string',
                                'VALUETYPE': 'string'},
                               ['Symm_StorageVolume'])]),
                            '\n',
                            ('KEYBINDING',
                             {'NAME': 'DeviceID'},
                             [('KEYVALUE',
                               {'TYPE': 'string',
                                'VALUETYPE': 'string'},
                               ['00000'])]),
                            '\n',
                            ('KEYBINDING',
                             {'NAME': 'SystemCreationClassName'},
                             [('KEYVALUE',
                               {'TYPE': 'string',
                                'VALUETYPE': 'string'},
                               ['Symm_StorageSystem'])]),
                            '\n',
                            ('KEYBINDING',
                             {'NAME': 'SystemName'},
                             [('KEYVALUE',
                               {'TYPE': 'string',
                                'VALUETYPE': 'string'},
                               ['SYMMETRIX-+-000194900000'])]),
                            '\n']),
                          '\n']),
                        '\n',
                        ('INSTANCE',
                         {'CLASSNAME': 'Symm_StorageVolume'},
                         ['\n',
                          ('PROPERTY',
                           {'NAME': 'Usage',
                            'TYPE': 'uint16'},
                           [('VALUE',
                             {},
                             ['3']),
                            '\n']),
                          '\n']),
                        '\n']),
                      '\n\n'])])])])]),
            None, None,
            True
        ),
    ]

    @pytest.mark.parametrize(
        "desc, xml_string, exp_tupletree, exp_exc_type, exp_exc_msg_pattern, "
        "condition",
        testcases
    )
    @pytest.mark.parametrize(
        "encoding",
        ['unicode', 'bytes']
    )
    def test_xml_to_tupletree_sax(
            self, encoding, desc, xml_string, exp_tupletree, exp_exc_type,
            exp_exc_msg_pattern, condition):
        # pylint: disable=no-self-use,unused-argument
        """
        Test xml_to_tupletree_sax() against expected results and against
        DOM parser results.
        """

        if not condition:
            pytest.skip("Condition for test case not met")

        assert isinstance(xml_string, str)
        if encoding == 'bytes':
            xml_string = xml_string.encode("utf-8")
        else:
            assert encoding == 'unicode'

        if exp_exc_type is None:

            act_tupletree = _tupletree.xml_to_tupletree_sax(
                xml_string, 'Test XML')

            # Compare against expected result
            assert act_tupletree == exp_tupletree

            if encoding == 'bytes':
                # Compare against result from previously used DOM parser
                dom_tupletree = xml_to_tupletree(xml_string)
                assert act_tupletree == dom_tupletree

        else:
            with pytest.raises(exp_exc_type) as exec_info:

                _tupletree.xml_to_tupletree_sax(xml_string, 'Test XML')

            if exp_exc_msg_pattern:
                exc = exec_info.value
                exc_msg = str(exc)
                one_line_exc_msg = exc_msg.replace('\n', '\\n')
                assert re.search(exp_exc_msg_pattern, one_line_exc_msg), \
                    "Unexpected exception message:\n" + exc_msg


class Test_get_failing_line:
    # pylint: disable=too-few-public-methods
    """Tests for _tupletree.get_failing_line()"""

    testcases = [
        # Each testcase has these items:
        # * desc: Short testcase description.
        # * xml_string: Input XML string for the function.
        # * exc_msg: Input exception message for the function.
        # * exp_result: Expected result tuple, or None if expecting failure.
        # * exp_exc_type: Expected exception type, or None if expecting success.
        # * condition: Condition for testcase to run.

        # General cases
        (
            "Short one line XML string, parseable exception message",
            b'<V>ab</V>',
            ":1:2: some message",
            (1, 2, 3, "'<V>ab</V>'"),
            None, True
        ),
        (
            "Short 2 line XML string, parseable exception message",
            b'<V>ab</V>\n'
            b'<X>ab</X>\n',
            ":2:2: some message",
            (2, 2, 3, "'<X>ab</X>'"),
            None, True
        ),
        (
            "Short 2 line XML string, non-parseable exception message",
            b'<V>ab</V>\n'
            b'<X>ab</X>\n',
            "(2:2) some message",
            (None, None, None, "'<V>ab</V>\\n<X>ab</X>\\n'"),
            None, True
        ),
        (
            "Short 2 line XML string, parseable exception message for line 3",
            b'<V>ab</V>\n'
            b'<X>ab</X>\n',
            ":3:2: some message",
            (None, None, None, "'<V>ab</V>\\n<X>ab</X>\\n'"),
            None, True
        ),
        (
            "Empty XML, parseable exception message for line 1",
            b'',
            ":1:1: empty string",
            (1, 1, 2, "''"),
            None, True
        ),
        (
            "Empty line with newline XML, parseable exc. message for line 1",
            b'\n',
            ":1:1: empty string",
            (1, 1, 2, "''"),
            None, True
        ),

        # Exceeding chars after colno, with 0 chars before colno
        (
            "XML with 0/x/500 chars",
            b'b' * 0 + b'x' + b'a' * 500,
            ":1:1: empty string",
            (1, 1, 2, "'" + 'b' * 0 + 'x' + 'a' * 500 + "'"),
            None, True
        ),
        (
            "XML with 0/x/501 chars",
            b'b' * 0 + b'x' + b'a' * 501,
            ":1:1: empty string",
            (1, 1, 2, "'" + 'b' * 0 + 'x' + 'a' * 500 + "'" + '...'),
            None, True
        ),

        # Exceeding chars after colno, with 5 chars before colno
        (
            "XML with 5/x/500 chars",
            b'b' * 5 + b'x' + b'a' * 500,
            ":1:6: empty string",
            (1, 6, 7, "'" + 'b' * 5 + 'x' + 'a' * 500 + "'"),
            None, True
        ),
        (
            "XML with 5/x/501 chars",
            b'b' * 5 + b'x' + b'a' * 501,
            ":1:6: empty string",
            (1, 6, 7, "'" + 'b' * 5 + 'x' + 'a' * 500 + "'" + '...'),
            None, True
        ),

        # Exceeding chars before colno, with 0 chars after colno
        (
            "XML with 500/x/0 chars",
            b'b' * 500 + b'x' + b'a' * 0,
            ":1:501: empty string",
            (1, 501, 502, "'" + 'b' * 500 + 'x' + 'a' * 0 + "'"),
            None, True
        ),
        (
            "XML with 501/x/0 chars",
            b'b' * 501 + b'x' + b'a' * 0,
            ":1:502: empty string",
            (1, 502, 505, '...' + "'" + 'b' * 500 + 'x' + 'a' * 0 + "'"),
            None, True
        ),

        # Exceeding chars before colno, with 5 chars after colno
        (
            "XML with 500/x/5 chars",
            b'b' * 500 + b'x' + b'a' * 5,
            ":1:501: empty string",
            (1, 501, 502, "'" + 'b' * 500 + 'x' + 'a' * 5 + "'"),
            None, True
        ),
        (
            "XML with 501/x/5 chars",
            b'b' * 501 + b'x' + b'a' * 5,
            ":1:502: empty string",
            (1, 502, 505, '...' + "'" + 'b' * 500 + 'x' + 'a' * 5 + "'"),
            None, True
        ),

        # Exceeding chars before and after colno
        (
            "XML with 500/x/500 chars",
            b'b' * 500 + b'x' + b'a' * 500,
            ":1:501: empty string",
            (1, 501, 502, "'" + 'b' * 500 + 'x' + 'a' * 500 + "'"),
            None, True
        ),
        (
            "XML with 501/x/501 chars",
            b'b' * 501 + b'x' + b'a' * 501,
            ":1:502: empty string",
            (1, 502, 505, '...' + "'" + 'b' * 500 + 'x' + 'a' * 500 + "'" +
             '...'),
            None, True
        ),

    ]

    @pytest.mark.parametrize(
        "desc, xml_string, exc_msg, exp_result, exp_exc_type, condition",
        testcases
    )
    def test_get_failing_line(
            self, desc, xml_string, exc_msg, exp_result, exp_exc_type,
            condition):
        # pylint: disable=no-self-use,unused-argument
        """Tests for _tupletree.get_failing_line()"""

        if not condition:
            pytest.skip("Condition for test case not met")

        if exp_exc_type is None:

            act_result = _tupletree.get_failing_line(xml_string, exc_msg)

            assert isinstance(act_result, tuple)
            assert act_result == exp_result

        else:
            with pytest.raises(exp_exc_type):

                _tupletree.get_failing_line(xml_string, exc_msg)


class Test_check_invalid_utf8_sequences:
    # pylint: disable=too-few-public-methods
    """
    Tests for _tupletree.check_invalid_utf8_sequences()
    """

    testcases = [
        # Each testcase has these items:
        # * desc: Short testcase description.
        # * utf8_string: Input string for the function.
        # * exp_exc_type: Expected exception type, or None if expecting success.
        # * condition: Condition for testcase to run.

        # General cases
        (
            "Incorrect type of input string",
            '<V>ab</V>',
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
        # pylint: disable=no-self-use
        """
        Tests for _tupletree.check_invalid_utf8_sequences()
        """

        if not condition:
            pytest.skip("Condition for test case not met")

        if exp_exc_type is None:

            unicode_string = _tupletree.check_invalid_utf8_sequences(
                utf8_string, desc)

            assert isinstance(unicode_string, str), desc
            utf8_string_u = utf8_string.decode('utf-8')
            assert unicode_string == utf8_string_u, desc

        else:
            with pytest.raises(exp_exc_type):

                _tupletree.check_invalid_utf8_sequences(utf8_string, desc)


class Test_check_invalid_xml_chars:
    # pylint: disable=too-few-public-methods
    """
    Tests for _tupletree.check_invalid_xml_chars()
    """

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
            '<V>a</V>',
            None, True
        ),
        (
            "Good case with U+0009 (TAB), U+000A (NL), U+000D (CR) chars",
            '<V>a\u0009b\u000Ac\u000Dd</V>',
            None, True
        ),
        (
            "Good case with U+0350 char",
            '<V>a\u0350b</V>',
            None, True
        ),
        (
            "Good case with U+2013 char",
            '<V>a\u2013b</V>',
            None, True
        ),
        (
            "Good case with U+10122 char",
            '<V>a\u010122b</V>',
            None, True
        ),

        # Invalid XML characters
        (
            "Invalid XML char U+0008 (BEL)",
            '<V>a\u0008b</V>',
            ParseError, True
        ),
        (
            "Invalid XML char U+0000",
            '<V>a\u0000b</V>',
            ParseError, True
        ),
        (
            "Invalid XML chars U+0001 ... U+0008",
            '<V>a\u0001b\u0002c\u0003d\u0004e\u0005f\u0006g\u0007h\u0008i</V>',
            ParseError, True
        ),
        (
            "Invalid XML chars U+000B ... U+000C",
            '<V>a\u000Bb\u000Cc</V>',
            ParseError, True
        ),
        (
            "Invalid XML chars U+000E ... U+0015",
            '<V>a\u000Eb\u000Fc\u0010d\u0011e\u0012f\u0013g\u0014h\u0015i</V>',
            ParseError, True
        ),
        (
            "Invalid XML chars U+0016 ... U+001D",
            '<V>a\u0016b\u0017c\u0018d\u0019e\u001Af\u001Bg\u001Ch\u001Di</V>',
            ParseError, True
        ),
        (
            "Invalid XML chars U+001E ... U+001F",
            '<V>a\u001Eb\u001Fc</V>',
            ParseError, True
        ),
    ]

    @pytest.mark.parametrize(
        "desc, xml_string, exp_exc_type, condition",
        testcases
    )
    def test_check_invalid_xml_chars(
            self, desc, xml_string, exp_exc_type, condition):
        # pylint: disable=no-self-use
        """
        Tests for _tupletree.check_invalid_xml_chars()
        """

        if not condition:
            pytest.skip("Condition for test case not met")

        if exp_exc_type is None:

            _tupletree.check_invalid_xml_chars(xml_string, desc)

        else:
            with pytest.raises(exp_exc_type):

                _tupletree.check_invalid_xml_chars(xml_string, desc)
