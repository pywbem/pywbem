#!/usr/bin/env python
"""
    Test ValueMapping class
"""

from __future__ import absolute_import

import re
import unittest
from mock import Mock

from pywbem import CIMClass, CIMProperty, CIMQualifier, Uint8, WBEMServer, \
    WBEMConnection, ValueMapping

CLASSNAME = 'C1'
NAMESPACE = 'ns'
PROPNAME = 'p1'


class TestAll(unittest.TestCase):
    """
    Unittest TestClass for ValueMapping. Does setup for tests.
    """

    def setUp(self):
        """Setup WBEMConnection and WBEMSErver"""
        self.conn = WBEMConnection('dummy')
        self.server = WBEMServer(self.conn)

    def setup_for_property(self, valuemap, values):
        """
        Set up a test class with a ValueMap/Values qualified property,
        and mock the GetClass() method to return that test class.
        """
        test_prop = CIMProperty(PROPNAME, None, 'uint8')
        test_prop.qualifiers['ValueMap'] = \
            CIMQualifier('ValueMap', valuemap, 'string')
        test_prop.qualifiers['Values'] = \
            CIMQualifier('Values', values, 'string')
        test_class = CIMClass(CLASSNAME)
        test_class.properties[PROPNAME] = test_prop
        self.conn.GetClass = Mock(return_value=test_class)

    def assertOutsideValueMap(self, vm, value):
        """
        Test vm.tovalues Exception
        """
        try:
            vm.tovalues(value)
        except ValueError as exc:
            if re.match("Element value outside of the set defined by "
                        "ValueMap.*", str(exc)) is None:
                self.fail("ValueError has unexpected text: %s" % str(exc))
        else:
            self.fail("ValueError was not raised.")

    def test_empty(self):
        """Test empty ValueMapping"""
        valuemap = []
        values = []
        self.setup_for_property(valuemap, values)

        vm = ValueMapping.for_property(self.server, NAMESPACE, CLASSNAME,
                                       PROPNAME)

        self.assertOutsideValueMap(vm, 0)

    def test_zero(self):
        """Test value map with value zero"""
        valuemap = ['0']
        values = ['zero']
        self.setup_for_property(valuemap, values)

        vm = ValueMapping.for_property(self.server, NAMESPACE, CLASSNAME,
                                       PROPNAME)

        self.assertEqual(vm.tovalues(0), 'zero')
        self.assertOutsideValueMap(vm, 1)

    def test_one(self):
        """Test valuemap with value 1"""
        valuemap = ['1']
        values = ['one']
        self.setup_for_property(valuemap, values)

        vm = ValueMapping.for_property(self.server, NAMESPACE, CLASSNAME,
                                       PROPNAME)

        self.assertOutsideValueMap(vm, 0)
        self.assertEqual(vm.tovalues(1), 'one')
        self.assertOutsideValueMap(vm, 2)

    def test_one_cimtype(self):
        """test valuemap for property"""
        valuemap = ['1']
        values = ['one']
        self.setup_for_property(valuemap, values)

        vm = ValueMapping.for_property(self.server, NAMESPACE, CLASSNAME,
                                       PROPNAME)

        self.assertEqual(vm.tovalues(Uint8(1)), 'one')

    def test_singles(self):
        """Test valuemap for property with multiple values"""
        valuemap = ['0', '1', '9']
        values = ['zero', 'one', 'nine']
        self.setup_for_property(valuemap, values)

        vm = ValueMapping.for_property(self.server, NAMESPACE, CLASSNAME,
                                       PROPNAME)

        self.assertEqual(vm.tovalues(0), 'zero')
        self.assertEqual(vm.tovalues(1), 'one')
        self.assertOutsideValueMap(vm, 2)
        self.assertOutsideValueMap(vm, 8)
        self.assertEqual(vm.tovalues(9), 'nine')
        self.assertOutsideValueMap(vm, 10)

    def test_singles_ranges(self):
        """Test valuemap with ranges in valuemap"""
        valuemap = ['0', '1', '2..4', '..6', '7..', '9']
        values = ['zero', 'one', 'two-four', 'five-six', 'seven-eight', 'nine']
        self.setup_for_property(valuemap, values)

        vm = ValueMapping.for_property(self.server, NAMESPACE, CLASSNAME,
                                       PROPNAME)

        self.assertEqual(vm.tovalues(0), 'zero')
        self.assertEqual(vm.tovalues(1), 'one')
        self.assertEqual(vm.tovalues(2), 'two-four')
        self.assertEqual(vm.tovalues(3), 'two-four')
        self.assertEqual(vm.tovalues(4), 'two-four')
        self.assertEqual(vm.tovalues(5), 'five-six')
        self.assertEqual(vm.tovalues(6), 'five-six')
        self.assertEqual(vm.tovalues(7), 'seven-eight')
        self.assertEqual(vm.tovalues(8), 'seven-eight')
        self.assertEqual(vm.tovalues(9), 'nine')
        self.assertOutsideValueMap(vm, 10)

    def test_unclaimed(self):
        """Test with valuemap '..'"""
        valuemap = ['..']
        values = ['unclaimed']
        self.setup_for_property(valuemap, values)

        vm = ValueMapping.for_property(self.server, NAMESPACE, CLASSNAME,
                                       PROPNAME)

        self.assertEqual(vm.tovalues(0), 'unclaimed')
        self.assertEqual(vm.tovalues(1), 'unclaimed')
        self.assertEqual(vm.tovalues(2), 'unclaimed')

    def test_singles_ranges_unclaimed(self):
        """Test combination of singles, ranges, unclaimed"""
        valuemap = ['0', '1', '2..4', '..6', '7..', '9', '..']
        values = ['zero', 'one', 'two-four', 'five-six', 'seven-eight', 'nine',
                  'unclaimed']
        self.setup_for_property(valuemap, values)

        vm = ValueMapping.for_property(self.server, NAMESPACE, CLASSNAME,
                                       PROPNAME)

        self.assertEqual(vm.tovalues(0), 'zero')
        self.assertEqual(vm.tovalues(1), 'one')
        self.assertEqual(vm.tovalues(2), 'two-four')
        self.assertEqual(vm.tovalues(3), 'two-four')
        self.assertEqual(vm.tovalues(4), 'two-four')
        self.assertEqual(vm.tovalues(5), 'five-six')
        self.assertEqual(vm.tovalues(6), 'five-six')
        self.assertEqual(vm.tovalues(7), 'seven-eight')
        self.assertEqual(vm.tovalues(8), 'seven-eight')
        self.assertEqual(vm.tovalues(9), 'nine')
        self.assertEqual(vm.tovalues(10), 'unclaimed')
        self.assertEqual(vm.tovalues(11), 'unclaimed')

    def test_singles_ranges_unclaimed2(self):
        """Test singles, ranges, unclaimed"""
        valuemap = ['0', '2..4', '..6', '7..', '9', '..']
        values = ['zero', 'two-four', 'five-six', 'seven-eight', 'nine',
                  'unclaimed']
        self.setup_for_property(valuemap, values)

        vm = ValueMapping.for_property(self.server, NAMESPACE, CLASSNAME,
                                       PROPNAME)

        self.assertEqual(vm.tovalues(0), 'zero')
        self.assertEqual(vm.tovalues(1), 'unclaimed')  # '..' fills this gap
        self.assertEqual(vm.tovalues(2), 'two-four')
        self.assertEqual(vm.tovalues(3), 'two-four')
        self.assertEqual(vm.tovalues(4), 'two-four')
        self.assertEqual(vm.tovalues(5), 'five-six')
        self.assertEqual(vm.tovalues(6), 'five-six')
        self.assertEqual(vm.tovalues(7), 'seven-eight')
        self.assertEqual(vm.tovalues(8), 'seven-eight')
        self.assertEqual(vm.tovalues(9), 'nine')
        self.assertEqual(vm.tovalues(10), 'unclaimed')
        self.assertEqual(vm.tovalues(11), 'unclaimed')


if __name__ == '__main__':
    unittest.main()
