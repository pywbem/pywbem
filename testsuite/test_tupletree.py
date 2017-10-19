#!/usr/bin/env python
"""
    Test to compare results of DOM tupletree implementation with the
    sax implementation
"""
import os
import xml
import unittest
import pprint
import six
from pkg_resources import resource_filename

from pywbem import tupletree

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
            tree_sax = tupletree.xml_to_tupletree_sax(xml_str)
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
            self.assertRaises(xml.sax.SAXParseException,
                              tupletree.xml_to_tupletree_sax, xml_str)


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
        tree_sax = tupletree.xml_to_tupletree_sax(xml_str)
        self.assertEqual(test_tuple, tree_sax,
                         'Test tuple and SAX not equal for %s:\n%s,\n%s'
                         % (path, pp.pformat(tree_sax), pp.pformat(tree_sax)))


if __name__ == '__main__':
    unittest.main()
