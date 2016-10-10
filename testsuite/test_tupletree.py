import os
import xml
import unittest
from pkg_resources import resource_filename
import pprint

from pywbem import tupletree

pp = pprint.PrettyPrinter(indent=4)

test_tuple = (u'CIM',
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


class TestTupleTreeRegression(unittest.TestCase):

    def setUp(self):
        self.data_dir = resource_filename(__name__, 'tupletree_ok')
        for path, dirs, files in os.walk(self.data_dir):
            self.filenames = [os.path.join(path, f) for f in files]

    def test_to_tupletree(self):
        """SAX parsing replicates DOM parsing to the tupletree."""
        for fn in self.filenames:
            with open(fn, 'rb') as fh:
                xml_str = fh.read()
            tree_dom = tupletree.xml_to_tupletree(xml_str)
            tree_sax = tupletree.xml_to_tupletree_sax(xml_str)
            self.assertEqual(tree_dom, tree_sax,
                             'SAX and DOM not equal for %s:\n%s,\n%s'
                             % (fn, pp.pformat(tree_sax), pp.pformat(tree_dom)))


class TestTupleTreeError(unittest.TestCase):

    def setUp(self):
        self.data_dir = resource_filename(__name__, 'tupletree_error')

    def test_to_tupletree_error(self):
        """SAX parsing generates errors."""
        filename = os.path.join(self.data_dir, 'Associators_error.xml')
        with open(filename, 'rb') as fh:
            xml_str = fh.read()
            self.assertRaises(xml.sax.SAXParseException,
                              tupletree.xml_to_tupletree_sax, xml_str)


class TestTupleTreeSax(unittest.TestCase):

    def test_xml_to_tupletree_sax(self):
        """XML to tupletree with SAX is accurate."""
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
