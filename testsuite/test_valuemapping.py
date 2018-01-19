#!/usr/bin/env python
"""
    Test ValueMapping class
"""

from __future__ import absolute_import

import re
import pytest
from mock import Mock

from pywbem import CIMClass, CIMProperty, CIMQualifier, WBEMServer, \
    WBEMConnection, ValueMapping
from pywbem.cim_types import type_from_name

CLASSNAME = 'C1'
NAMESPACE = 'ns'
PROPNAME = 'p1'


@pytest.fixture(params=[
    'uint8',
    'uint16',
    'uint32',
    'uint64',
    'sint8',
    'sint16',
    'sint32',
    'sint64',
], scope='module')
def integer_type(request):
    """Fixture for all CIM integer data type names"""
    return request.param


class Test_ValueMapping(object):
    """
    All tests for ValueMapping class.
    """

    def setup_method(self):
        """Setup WBEMConnection and WBEMSErver"""
        self.conn = WBEMConnection('dummy')
        self.server = WBEMServer(self.conn)

    def setup_for_property(self, valuemap, values, type='uint8'):
        """
        Set up a test class with a ValueMap/Values qualified property,
        and mock the GetClass() method to return that test class.

        type is the name of the CIM data type (e.g. 'uint8').
        """
        test_prop = CIMProperty(PROPNAME, None, type)
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
        with pytest.raises(ValueError) as exc_info:
            vm.tovalues(value)
        exc = exc_info.value
        exc_msg = str(exc)
        assert re.match("Element value outside of the set defined by "
                        "ValueMap.*", exc_msg) is not None

    def test_empty(self, integer_type):
        """Test empty ValueMapping"""
        valuemap = []
        values = []
        self.setup_for_property(valuemap, values, integer_type)

        vm = ValueMapping.for_property(self.server, NAMESPACE, CLASSNAME,
                                       PROPNAME)

        self.assertOutsideValueMap(vm, 0)

    def test_zero(self, integer_type):
        """Test value map with value zero"""
        valuemap = ['0']
        values = ['zero']
        self.setup_for_property(valuemap, values, integer_type)

        vm = ValueMapping.for_property(self.server, NAMESPACE, CLASSNAME,
                                       PROPNAME)

        assert vm.tovalues(0) == 'zero'
        self.assertOutsideValueMap(vm, 1)

    def test_one(self, integer_type):
        """Test valuemap with value 1"""
        valuemap = ['1']
        values = ['one']
        self.setup_for_property(valuemap, values, integer_type)

        vm = ValueMapping.for_property(self.server, NAMESPACE, CLASSNAME,
                                       PROPNAME)

        self.assertOutsideValueMap(vm, 0)
        assert vm.tovalues(1) == 'one'
        self.assertOutsideValueMap(vm, 2)

    def test_one_cimtype(self, integer_type):
        """test valuemap for property"""
        valuemap = ['1']
        values = ['one']
        self.setup_for_property(valuemap, values, integer_type)

        vm = ValueMapping.for_property(self.server, NAMESPACE, CLASSNAME,
                                       PROPNAME)

        cimtype = type_from_name(integer_type)
        assert vm.tovalues(cimtype(1)) == 'one'

    def test_singles(self, integer_type):
        """Test valuemap for property with multiple values"""
        valuemap = ['0', '1', '9']
        values = ['zero', 'one', 'nine']
        self.setup_for_property(valuemap, values, integer_type)

        vm = ValueMapping.for_property(self.server, NAMESPACE, CLASSNAME,
                                       PROPNAME)

        assert vm.tovalues(0) == 'zero'
        assert vm.tovalues(1) == 'one'
        self.assertOutsideValueMap(vm, 2)
        self.assertOutsideValueMap(vm, 8)
        assert vm.tovalues(9) == 'nine'
        self.assertOutsideValueMap(vm, 10)

    def test_singles_ranges(self, integer_type):
        """Test valuemap with ranges in valuemap"""
        valuemap = ['0', '1', '2..4', '..6', '7..', '9']
        values = ['zero', 'one', 'two-four', 'five-six', 'seven-eight', 'nine']
        self.setup_for_property(valuemap, values, integer_type)

        vm = ValueMapping.for_property(self.server, NAMESPACE, CLASSNAME,
                                       PROPNAME)

        assert vm.tovalues(0) == 'zero'
        assert vm.tovalues(1) == 'one'
        assert vm.tovalues(2) == 'two-four'
        assert vm.tovalues(3) == 'two-four'
        assert vm.tovalues(4) == 'two-four'
        assert vm.tovalues(5) == 'five-six'
        assert vm.tovalues(6) == 'five-six'
        assert vm.tovalues(7) == 'seven-eight'
        assert vm.tovalues(8) == 'seven-eight'
        assert vm.tovalues(9) == 'nine'
        self.assertOutsideValueMap(vm, 10)

    def test_unclaimed(self, integer_type):
        """Test with valuemap '..'"""
        valuemap = ['..']
        values = ['unclaimed']
        self.setup_for_property(valuemap, values, integer_type)

        vm = ValueMapping.for_property(self.server, NAMESPACE, CLASSNAME,
                                       PROPNAME)

        assert vm.tovalues(0) == 'unclaimed'
        assert vm.tovalues(1) == 'unclaimed'
        assert vm.tovalues(2) == 'unclaimed'

    def test_singles_ranges_unclaimed(self, integer_type):
        """Test combination of singles, ranges, unclaimed"""
        valuemap = ['0', '1', '2..4', '..6', '7..', '9', '..']
        values = ['zero', 'one', 'two-four', 'five-six', 'seven-eight', 'nine',
                  'unclaimed']
        self.setup_for_property(valuemap, values, integer_type)

        vm = ValueMapping.for_property(self.server, NAMESPACE, CLASSNAME,
                                       PROPNAME)

        assert vm.tovalues(0) == 'zero'
        assert vm.tovalues(1) == 'one'
        assert vm.tovalues(2) == 'two-four'
        assert vm.tovalues(3) == 'two-four'
        assert vm.tovalues(4) == 'two-four'
        assert vm.tovalues(5) == 'five-six'
        assert vm.tovalues(6) == 'five-six'
        assert vm.tovalues(7) == 'seven-eight'
        assert vm.tovalues(8) == 'seven-eight'
        assert vm.tovalues(9) == 'nine'
        assert vm.tovalues(10) == 'unclaimed'
        assert vm.tovalues(11) == 'unclaimed'

    def test_singles_ranges_unclaimed2(self, integer_type):
        """Test singles, ranges, unclaimed"""
        valuemap = ['0', '2..4', '..6', '7..', '9', '..']
        values = ['zero', 'two-four', 'five-six', 'seven-eight', 'nine',
                  'unclaimed']
        self.setup_for_property(valuemap, values, integer_type)

        vm = ValueMapping.for_property(self.server, NAMESPACE, CLASSNAME,
                                       PROPNAME)

        assert vm.tovalues(0) == 'zero'
        assert vm.tovalues(1) == 'unclaimed'  # '..' fills this gap
        assert vm.tovalues(2) == 'two-four'
        assert vm.tovalues(3) == 'two-four'
        assert vm.tovalues(4) == 'two-four'
        assert vm.tovalues(5) == 'five-six'
        assert vm.tovalues(6) == 'five-six'
        assert vm.tovalues(7) == 'seven-eight'
        assert vm.tovalues(8) == 'seven-eight'
        assert vm.tovalues(9) == 'nine'
        assert vm.tovalues(10) == 'unclaimed'
        assert vm.tovalues(11) == 'unclaimed'

    def test_min_max_single(self, integer_type):
        """Test valuemap with single min and max values of integer type"""

        minvalue = type_from_name(integer_type).minvalue
        maxvalue = type_from_name(integer_type).maxvalue

        valuemap = []
        valuemap.append(str(minvalue))
        valuemap.append(str(maxvalue))

        values = []
        for v in valuemap:
            values.append('val %s' % v)

        self.setup_for_property(valuemap, values, integer_type)

        vm = ValueMapping.for_property(self.server, NAMESPACE, CLASSNAME,
                                       PROPNAME)

        self.assertOutsideValueMap(vm, minvalue - 1)
        assert vm.tovalues(minvalue) == values[0]
        self.assertOutsideValueMap(vm, minvalue + 1)

        self.assertOutsideValueMap(vm, maxvalue - 1)
        assert vm.tovalues(maxvalue) == values[1]
        self.assertOutsideValueMap(vm, maxvalue + 1)

    def test_min_max_closed_range(self, integer_type):
        """Test valuemap with closed range of min and max of integer type"""

        minvalue = type_from_name(integer_type).minvalue
        maxvalue = type_from_name(integer_type).maxvalue

        valuemap = []
        valuemap.append('%s..%s' % (minvalue, minvalue + 2))
        valuemap.append('%s..%s' % (maxvalue - 2, maxvalue))

        values = []
        for v in valuemap:
            values.append('val %s' % v)

        self.setup_for_property(valuemap, values, integer_type)

        vm = ValueMapping.for_property(self.server, NAMESPACE, CLASSNAME,
                                       PROPNAME)

        self.assertOutsideValueMap(vm, minvalue - 1)
        assert vm.tovalues(minvalue) == values[0]
        assert vm.tovalues(minvalue + 1) == values[0]
        assert vm.tovalues(minvalue + 2) == values[0]
        self.assertOutsideValueMap(vm, minvalue + 3)

        self.assertOutsideValueMap(vm, maxvalue - 3)
        assert vm.tovalues(maxvalue - 2) == values[1]
        assert vm.tovalues(maxvalue - 1) == values[1]
        assert vm.tovalues(maxvalue) == values[1]
        self.assertOutsideValueMap(vm, maxvalue + 1)

    def test_min_max_open_range1(self, integer_type):
        """Test valuemap with open range 1 of min and max of integer type"""

        minvalue = type_from_name(integer_type).minvalue
        maxvalue = type_from_name(integer_type).maxvalue

        valuemap = []
        valuemap.append('%s' % minvalue)
        valuemap.append('..%s' % (minvalue + 2))
        valuemap.append('%s..' % (maxvalue - 2))
        valuemap.append('%s' % maxvalue)

        values = []
        for v in valuemap:
            values.append('val %s' % v)

        self.setup_for_property(valuemap, values, integer_type)

        vm = ValueMapping.for_property(self.server, NAMESPACE, CLASSNAME,
                                       PROPNAME)

        self.assertOutsideValueMap(vm, minvalue - 1)
        assert vm.tovalues(minvalue) == values[0]
        assert vm.tovalues(minvalue + 1) == values[1]
        assert vm.tovalues(minvalue + 2) == values[1]
        self.assertOutsideValueMap(vm, minvalue + 3)

        self.assertOutsideValueMap(vm, maxvalue - 3)
        assert vm.tovalues(maxvalue - 2) == values[2]
        assert vm.tovalues(maxvalue - 1) == values[2]
        assert vm.tovalues(maxvalue) == values[3]
        self.assertOutsideValueMap(vm, maxvalue + 1)

    def test_min_max_open_range2(self, integer_type):
        """Test valuemap with open range 2 of min and max of integer type"""

        minvalue = type_from_name(integer_type).minvalue
        maxvalue = type_from_name(integer_type).maxvalue

        valuemap = []
        valuemap.append('..%s' % (minvalue + 2))
        valuemap.append('%s..' % (maxvalue - 2))

        values = []
        for v in valuemap:
            values.append('val %s' % v)

        self.setup_for_property(valuemap, values, integer_type)

        vm = ValueMapping.for_property(self.server, NAMESPACE, CLASSNAME,
                                       PROPNAME)

        self.assertOutsideValueMap(vm, minvalue - 1)
        assert vm.tovalues(minvalue) == values[0]
        assert vm.tovalues(minvalue + 1) == values[0]
        assert vm.tovalues(minvalue + 2) == values[0]
        self.assertOutsideValueMap(vm, minvalue + 3)

        self.assertOutsideValueMap(vm, maxvalue - 3)
        assert vm.tovalues(maxvalue - 2) == values[1]
        assert vm.tovalues(maxvalue - 1) == values[1]
        assert vm.tovalues(maxvalue) == values[1]
        self.assertOutsideValueMap(vm, maxvalue + 1)
