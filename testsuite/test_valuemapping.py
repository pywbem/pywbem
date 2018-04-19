#!/usr/bin/env python
"""
    Test ValueMapping class
"""

from __future__ import absolute_import

import re
import pytest
from mock import Mock

from pywbem import CIMClass, CIMProperty, CIMMethod, CIMParameter, \
    CIMQualifier, WBEMServer, WBEMConnection, ValueMapping
from pywbem.cim_types import type_from_name

CLASSNAME = 'C1'
NAMESPACE = 'ns'
PROPNAME = 'p1'
METHNAME = 'm1'
PARMNAME = 'p1'


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


@pytest.fixture(params=[
    'property',
    'method',
    'parameter',
], scope='module')
def element_kind(request):
    """Fixture for all kinds of CIM elements supporting ValueMapping"""
    return request.param


@pytest.fixture(params=[
    'server',
    'conn',
], scope='module')
def server_arg(request):
    """Fixture for the server parameter of ValueMapping"""
    return request.param


class Test_ValueMapping(object):
    """
    All tests for ValueMapping class.
    """

    def setup_method(self):
        """Setup WBEMConnection and WBEMSErver"""
        # pylint: disable=attribute-defined-outside-init
        self.conn = WBEMConnection('dummy')
        # pylint: disable=attribute-defined-outside-init
        self.server = WBEMServer(self.conn)

    def setup_for_property(self, server, type_, valuemap, values):
        """
        Return a new ValueMapping object that is set up for a CIM property
        with the specified data type and valuemap and values qualifiers.
        """
        test_prop = CIMProperty(PROPNAME, value=None, type=type_)
        if valuemap is not None:
            test_prop.qualifiers['ValueMap'] = \
                CIMQualifier('ValueMap', valuemap, 'string')
        if values is not None:
            test_prop.qualifiers['Values'] = \
                CIMQualifier('Values', values, 'string')
        test_class = CIMClass(CLASSNAME)
        test_class.properties[PROPNAME] = test_prop
        self.conn.GetClass = Mock(return_value=test_class)

        vm = ValueMapping.for_property(server, NAMESPACE, CLASSNAME, PROPNAME)
        return vm

    def setup_for_method(self, server, type_, valuemap, values):
        """
        Return a new ValueMapping object that is set up for a CIM method
        with the specified data type and valuemap and values qualifiers.
        """
        test_meth = CIMMethod(METHNAME, return_type=type_)
        if valuemap is not None:
            test_meth.qualifiers['ValueMap'] = \
                CIMQualifier('ValueMap', valuemap, 'string')
        if values is not None:
            test_meth.qualifiers['Values'] = \
                CIMQualifier('Values', values, 'string')
        test_class = CIMClass(CLASSNAME)
        test_class.methods[METHNAME] = test_meth
        self.conn.GetClass = Mock(return_value=test_class)

        vm = ValueMapping.for_method(server, NAMESPACE, CLASSNAME, METHNAME)
        return vm

    def setup_for_parameter(self, server, type_, valuemap, values):
        """
        Return a new ValueMapping object that is set up for a CIM parameter
        with the specified data type and valuemap and values qualifiers.
        """
        test_parm = CIMParameter(PARMNAME, type=type_)
        if valuemap is not None:
            test_parm.qualifiers['ValueMap'] = \
                CIMQualifier('ValueMap', valuemap, 'string')
        if values is not None:
            test_parm.qualifiers['Values'] = \
                CIMQualifier('Values', values, 'string')
        test_meth = CIMMethod(METHNAME, return_type='string')
        test_meth.parameters[PARMNAME] = test_parm
        test_class = CIMClass(CLASSNAME)
        test_class.methods[METHNAME] = test_meth
        self.conn.GetClass = Mock(return_value=test_class)

        vm = ValueMapping.for_parameter(server, NAMESPACE, CLASSNAME, METHNAME,
                                        PARMNAME)
        return vm

    def setup_for_element(self, element_kind, server_arg, type_, valuemap,
                          values):
        # pylint: disable=redefined-outer-name
        """
        Return a new ValueMapping object that is set up for a CVIM element of
        the specified kind, with the specified data type and valuemap and
        values qualifiers.
        """
        server = getattr(self, server_arg)
        setup_func_name = 'setup_for_%s' % element_kind
        setup_func = getattr(self, setup_func_name)

        vm = setup_func(server, type_, valuemap, values)

        return vm

    @staticmethod
    def assertOutsideValueMap(vm, value):
        """
        Test vm.tovalues Exception
        """
        with pytest.raises(ValueError) as exc_info:
            vm.tovalues(value)
        exc = exc_info.value
        exc_msg = str(exc)
        assert re.match("Element value outside of the set defined by "
                        "ValueMap.*", exc_msg) is not None

    def test_empty(self, element_kind, server_arg, integer_type):
        # pylint: disable=redefined-outer-name
        """Test empty ValueMapping"""
        valuemap = []
        values = []

        vm = self.setup_for_element(element_kind, server_arg, integer_type,
                                    valuemap, values)

        self.assertOutsideValueMap(vm, 0)

    def test_attrs_property(self, server_arg, integer_type):
        # pylint: disable=redefined-outer-name
        """Test attributes of ValueMapping for a CIM property"""
        valuemap = ['42']
        values = ['forty-two']

        vm = self.setup_for_element('property', server_arg, integer_type,
                                    valuemap, values)

        assert vm.conn is self.conn

        assert vm.namespace == NAMESPACE
        assert vm.classname == CLASSNAME
        assert vm.propname == PROPNAME
        assert vm.methodname is None
        assert vm.parametername is None

        prop = vm.element
        assert isinstance(prop, CIMProperty)
        assert prop.name == PROPNAME
        assert prop.type == integer_type

    def test_attrs_method(self, server_arg, integer_type):
        # pylint: disable=redefined-outer-name
        """Test attributes of ValueMapping for a CIM method"""
        valuemap = ['42']
        values = ['forty-two']

        vm = self.setup_for_element('method', server_arg, integer_type,
                                    valuemap, values)

        assert vm.conn is self.conn

        assert vm.namespace == NAMESPACE
        assert vm.classname == CLASSNAME
        assert vm.propname is None
        assert vm.methodname == METHNAME
        assert vm.parametername is None

        meth = vm.element
        assert isinstance(meth, CIMMethod)
        assert meth.name == METHNAME
        assert meth.return_type == integer_type

    def test_attrs_parameter(self, server_arg, integer_type):
        # pylint: disable=redefined-outer-name
        """Test attributes of ValueMapping for a CIM parameter"""
        valuemap = ['42']
        values = ['forty-two']

        vm = self.setup_for_element('parameter', server_arg, integer_type,
                                    valuemap, values)

        assert vm.conn is self.conn

        assert vm.namespace == NAMESPACE
        assert vm.classname == CLASSNAME
        assert vm.propname is None
        assert vm.methodname == METHNAME
        assert vm.parametername == PARMNAME

        parm = vm.element
        assert isinstance(parm, CIMParameter)
        assert parm.name == PARMNAME
        assert parm.type == integer_type

    def test_repr(self, element_kind, server_arg, integer_type):
        # pylint: disable=redefined-outer-name
        """Test ValueMapping.__repr__()"""
        valuemap = ['1']
        values = ['one']

        vm = self.setup_for_element(element_kind, server_arg, integer_type,
                                    valuemap, values)

        r = repr(vm)

        assert re.match(r'^ValueMapping\(', r)

        exp_conn = '_conn=%r' % vm._conn
        assert exp_conn in r

        exp_namespace = '_namespace=%r' % vm._namespace
        assert exp_namespace in r

        exp_classname = '_classname=%r' % vm._classname
        assert exp_classname in r

        exp_propname = '_propname=%r' % vm._propname
        assert exp_propname in r

        exp_methodname = '_methodname=%r' % vm._methodname
        assert exp_methodname in r

        exp_parametername = '_parametername=%r' % vm._parametername
        assert exp_parametername in r

        exp_element_obj = '_element_obj=%r' % vm._element_obj
        assert exp_element_obj in r

        # We don't check the internal data attributes.

    def test_invalid_valuemap_format(self, element_kind, server_arg,
                                     integer_type):
        # pylint: disable=redefined-outer-name
        """Test invalid ValueMap format"""
        valuemap = ['0x0']
        values = ['zero']

        with pytest.raises(Exception) as exc_info:
            self.setup_for_element(element_kind, server_arg, integer_type,
                                   valuemap, values)
        exc = exc_info.value
        assert isinstance(exc, ValueError)
        assert exc.args[0].startswith('Invalid ValueMap entry')

    def test_invalid_element_type(self, element_kind, server_arg):
        # pylint: disable=redefined-outer-name
        """Test invalid type for the element"""
        valuemap = ['0']
        values = ['zero']

        with pytest.raises(Exception) as exc_info:
            self.setup_for_element(element_kind, server_arg, 'string',
                                   valuemap, values)
        exc = exc_info.value
        assert isinstance(exc, TypeError)
        assert exc.args[0].startswith('The CIM element is not integer-typed')

    def test_invalid_tovalues_type(self, element_kind, server_arg,
                                   integer_type):
        # pylint: disable=redefined-outer-name
        """Test tovalues() with invalid type"""
        valuemap = ['0']
        values = ['zero']

        vm = self.setup_for_element(element_kind, server_arg, integer_type,
                                    valuemap, values)

        with pytest.raises(Exception) as exc_info:
            vm.tovalues('0')
        exc = exc_info.value
        assert isinstance(exc, TypeError)
        assert exc.args[0].startswith('Element value is not an integer type')

    def test_no_values_qualifier(self, element_kind, server_arg, integer_type):
        # pylint: disable=redefined-outer-name
        """Test element without Values qualifier"""
        valuemap = ['0']
        values = None

        with pytest.raises(Exception) as exc_info:
            self.setup_for_element(element_kind, server_arg, integer_type,
                                   valuemap, values)
        exc = exc_info.value
        assert isinstance(exc, ValueError)
        assert exc.args[0].startswith('No Values qualifier defined')

    def test_valuemap_default(self, element_kind, server_arg, integer_type):
        # pylint: disable=redefined-outer-name
        """Test default if no ValueMap qualifier is defined"""
        valuemap = None
        values = ['zero', 'one', 'two']

        vm = self.setup_for_element(element_kind, server_arg, integer_type,
                                    valuemap, values)

        self.assertOutsideValueMap(vm, -1)
        assert vm.tovalues(0) == 'zero'
        assert vm.tovalues(1) == 'one'
        assert vm.tovalues(2) == 'two'
        self.assertOutsideValueMap(vm, 3)

    def test_zero(self, element_kind, server_arg, integer_type):
        # pylint: disable=redefined-outer-name
        """Test valuemap with value 0"""
        valuemap = ['0']
        values = ['zero']

        vm = self.setup_for_element(element_kind, server_arg, integer_type,
                                    valuemap, values)

        assert vm.tovalues(0) == 'zero'
        self.assertOutsideValueMap(vm, 1)

    def test_one(self, element_kind, server_arg, integer_type):
        # pylint: disable=redefined-outer-name
        """Test valuemap with value 1"""
        valuemap = ['1']
        values = ['one']

        vm = self.setup_for_element(element_kind, server_arg, integer_type,
                                    valuemap, values)

        self.assertOutsideValueMap(vm, 0)
        assert vm.tovalues(1) == 'one'
        self.assertOutsideValueMap(vm, 2)

    def test_one_cimtype(self, element_kind, server_arg, integer_type):
        # pylint: disable=redefined-outer-name
        """Test valuemap with value cimtype(1)"""
        valuemap = ['1']
        values = ['one']

        vm = self.setup_for_element(element_kind, server_arg, integer_type,
                                    valuemap, values)

        cimtype = type_from_name(integer_type)
        assert vm.tovalues(cimtype(1)) == 'one'

    def test_singles(self, element_kind, server_arg, integer_type):
        # pylint: disable=redefined-outer-name
        """Test valuemap with multiple non-range values"""
        valuemap = ['0', '1', '9']
        values = ['zero', 'one', 'nine']

        vm = self.setup_for_element(element_kind, server_arg, integer_type,
                                    valuemap, values)

        assert vm.tovalues(0) == 'zero'
        assert vm.tovalues(1) == 'one'
        self.assertOutsideValueMap(vm, 2)
        self.assertOutsideValueMap(vm, 8)
        assert vm.tovalues(9) == 'nine'
        self.assertOutsideValueMap(vm, 10)

    def test_singles_ranges(self, element_kind, server_arg, integer_type):
        # pylint: disable=redefined-outer-name
        """Test valuemap with ranges"""
        valuemap = ['0', '1', '2..4', '..6', '7..', '9']
        values = ['zero', 'one', 'two-four', 'five-six', 'seven-eight', 'nine']

        vm = self.setup_for_element(element_kind, server_arg, integer_type,
                                    valuemap, values)

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

    def test_unclaimed(self, element_kind, server_arg, integer_type):
        # pylint: disable=redefined-outer-name
        """Test valuemap with unclaimed marker '..'"""
        valuemap = ['..']
        values = ['unclaimed']

        vm = self.setup_for_element(element_kind, server_arg, integer_type,
                                    valuemap, values)

        assert vm.tovalues(0) == 'unclaimed'
        assert vm.tovalues(1) == 'unclaimed'
        assert vm.tovalues(2) == 'unclaimed'

    def test_singles_ranges_unclaimed(self, element_kind, server_arg,
                                      integer_type):
        # pylint: disable=redefined-outer-name
        """Test valuemap with combination of singles, ranges, unclaimed"""
        valuemap = ['0', '1', '2..4', '..6', '7..', '9', '..']
        values = ['zero', 'one', 'two-four', 'five-six', 'seven-eight', 'nine',
                  'unclaimed']

        vm = self.setup_for_element(element_kind, server_arg, integer_type,
                                    valuemap, values)

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

    def test_singles_ranges_unclaimed2(self, element_kind, server_arg,
                                       integer_type):
        # pylint: disable=redefined-outer-name
        """Test singles, ranges, unclaimed"""
        valuemap = ['0', '2..4', '..6', '7..', '9', '..']
        values = ['zero', 'two-four', 'five-six', 'seven-eight', 'nine',
                  'unclaimed']

        vm = self.setup_for_element(element_kind, server_arg, integer_type,
                                    valuemap, values)

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

    def test_min_max_single(self, element_kind, server_arg, integer_type):
        # pylint: disable=redefined-outer-name
        """Test valuemap with single min and max values of integer type"""

        minvalue = type_from_name(integer_type).minvalue
        maxvalue = type_from_name(integer_type).maxvalue

        valuemap = []
        valuemap.append(str(minvalue))
        valuemap.append(str(maxvalue))

        values = []
        for v in valuemap:
            values.append('val %s' % v)

        vm = self.setup_for_element(element_kind, server_arg, integer_type,
                                    valuemap, values)

        self.assertOutsideValueMap(vm, minvalue - 1)
        assert vm.tovalues(minvalue) == values[0]
        self.assertOutsideValueMap(vm, minvalue + 1)

        self.assertOutsideValueMap(vm, maxvalue - 1)
        assert vm.tovalues(maxvalue) == values[1]
        self.assertOutsideValueMap(vm, maxvalue + 1)

    def test_min_max_closed_range(self, element_kind, server_arg, integer_type):
        # pylint: disable=redefined-outer-name
        """Test valuemap with closed range of min and max of integer type"""

        minvalue = type_from_name(integer_type).minvalue
        maxvalue = type_from_name(integer_type).maxvalue

        valuemap = []
        valuemap.append('%s..%s' % (minvalue, minvalue + 2))
        valuemap.append('%s..%s' % (maxvalue - 2, maxvalue))

        values = []
        for v in valuemap:
            values.append('val %s' % v)

        vm = self.setup_for_element(element_kind, server_arg, integer_type,
                                    valuemap, values)

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

    def test_min_max_open_range1(self, element_kind, server_arg, integer_type):
        # pylint: disable=redefined-outer-name
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

        vm = self.setup_for_element(element_kind, server_arg, integer_type,
                                    valuemap, values)

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

    def test_min_max_open_range2(self, element_kind, server_arg, integer_type):
        # pylint: disable=redefined-outer-name
        """Test valuemap with open range 2 of min and max of integer type"""

        minvalue = type_from_name(integer_type).minvalue
        maxvalue = type_from_name(integer_type).maxvalue

        valuemap = []
        valuemap.append('..%s' % (minvalue + 2))
        valuemap.append('%s..' % (maxvalue - 2))

        values = []
        for v in valuemap:
            values.append('val %s' % v)

        vm = self.setup_for_element(element_kind, server_arg, integer_type,
                                    valuemap, values)

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
