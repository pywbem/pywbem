#!/usr/bin/env python
"""
    Test ValueMapping class
"""

import re
from unittest.mock import Mock

import pytest

# pylint: disable=wrong-import-position, wrong-import-order, invalid-name
from ...utils import import_installed
pywbem = import_installed('pywbem')
from pywbem import CIMClass, CIMProperty, CIMMethod, CIMParameter, \
    CIMQualifier, WBEMServer, WBEMConnection, ValueMapping, \
    ModelError  # noqa: E402
from pywbem._cim_types import type_from_name  # noqa: E402
# pylint: enable=wrong-import-position, wrong-import-order, invalid-name


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
    False,
    True,
], scope='module')
def is_array(request):
    """Fixture controlling whether the CIM element is scalar or array"""
    return request.param


@pytest.fixture(params=[
    'server',
    'conn',
], scope='module')
def server_arg(request):
    """Fixture for the server parameter of ValueMapping"""
    return request.param


class Test_ValueMapping:
    """
    All tests for ValueMapping class.
    """

    def setup_method(self):
        """Setup WBEMConnection and WBEMSErver"""
        # pylint: disable=attribute-defined-outside-init
        self.conn = WBEMConnection('dummy')
        # pylint: disable=attribute-defined-outside-init
        self.server = WBEMServer(self.conn)

    def setup_for_property(self, server, integer_type, is_array,
                           valuemap, values, values_default=None):
        # pylint: disable=redefined-outer-name
        """
        Return a new ValueMapping object that is set up for a CIM property
        with the specified data type and valuemap and values qualifiers.
        """
        test_prop = CIMProperty(PROPNAME, value=None, type=integer_type,
                                is_array=is_array)
        if valuemap is not None:
            test_prop.qualifiers['ValueMap'] = \
                CIMQualifier('ValueMap', valuemap, 'string')
        if values is not None:
            test_prop.qualifiers['Values'] = \
                CIMQualifier('Values', values, 'string')
        test_class = CIMClass(CLASSNAME)
        test_class.properties[PROPNAME] = test_prop
        self.conn.GetClass = Mock(return_value=test_class)

        vm = ValueMapping.for_property(
            server, NAMESPACE, CLASSNAME, PROPNAME, values_default)
        return vm

    def setup_for_method(self, server, integer_type, is_array,
                         valuemap, values, values_default=None):
        # pylint: disable=redefined-outer-name
        """
        Return a new ValueMapping object that is set up for a CIM method
        with the specified data type and valuemap and values qualifiers.
        """
        if is_array:
            pytest.skip("CIM methods cannot return arrays")
        test_meth = CIMMethod(METHNAME, return_type=integer_type)
        if valuemap is not None:
            test_meth.qualifiers['ValueMap'] = \
                CIMQualifier('ValueMap', valuemap, 'string')
        if values is not None:
            test_meth.qualifiers['Values'] = \
                CIMQualifier('Values', values, 'string')
        test_class = CIMClass(CLASSNAME)
        test_class.methods[METHNAME] = test_meth
        self.conn.GetClass = Mock(return_value=test_class)

        vm = ValueMapping.for_method(
            server, NAMESPACE, CLASSNAME, METHNAME, values_default)
        return vm

    def setup_for_parameter(self, server, integer_type, is_array,
                            valuemap, values, values_default=None):
        # pylint: disable=redefined-outer-name
        """
        Return a new ValueMapping object that is set up for a CIM parameter
        with the specified data type and valuemap and values qualifiers.
        """
        test_parm = CIMParameter(PARMNAME, type=integer_type, is_array=is_array)
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
                                        PARMNAME, values_default)
        return vm

    def setup_for_element(self, element_kind, server_arg, integer_type,
                          is_array, valuemap, values, values_default=None):
        # pylint: disable=redefined-outer-name
        """
        Return a new ValueMapping object that is set up for a CVIM element of
        the specified kind, with the specified data type and valuemap and
        values qualifiers.
        """
        server = getattr(self, server_arg)
        setup_func_name = f'setup_for_{element_kind}'
        setup_func = getattr(self, setup_func_name)

        vm = setup_func(server, integer_type, is_array, valuemap, values,
                        values_default)

        return vm

    @staticmethod
    def assertOutsideValueMap(vm, value):
        """
        Test vm.tovalues() Exception
        """
        with pytest.raises(ValueError) as exc_info:
            vm.tovalues(value)
        exc = exc_info.value
        exc_msg = str(exc)
        assert re.match(".*outside of the set defined by its ValueMap "
                        "qualifier.*", exc_msg) is not None

    @staticmethod
    def assertOutsideValues(vm, value):
        """
        Test vm.tobinary() Exception
        """
        with pytest.raises(ValueError) as exc_info:
            vm.tobinary(value)
        exc = exc_info.value
        exc_msg = str(exc)
        assert re.match(".*outside of the set defined by its Values "
                        "qualifier.*", exc_msg) is not None

    def test_empty(self, element_kind, server_arg, integer_type, is_array):
        # pylint: disable=redefined-outer-name
        """Test empty ValueMapping"""
        valuemap = []
        values = []

        vm = self.setup_for_element(element_kind, server_arg, integer_type,
                                    is_array, valuemap, values)

        self.assertOutsideValueMap(vm, 0)
        self.assertOutsideValues(vm, 'x')

    def test_attrs_property(self, server_arg, integer_type, is_array):
        # pylint: disable=redefined-outer-name
        """Test attributes of ValueMapping for a CIM property"""
        valuemap = ['42']
        values = ['forty-two']

        vm = self.setup_for_element('property', server_arg, integer_type,
                                    is_array, valuemap, values)

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

    def test_attrs_method(self, server_arg, integer_type, is_array):
        # pylint: disable=redefined-outer-name
        """Test attributes of ValueMapping for a CIM method"""
        valuemap = ['42']
        values = ['forty-two']

        vm = self.setup_for_element('method', server_arg, integer_type,
                                    is_array, valuemap, values)

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

    def test_attrs_parameter(self, server_arg, integer_type, is_array):
        # pylint: disable=redefined-outer-name
        """Test attributes of ValueMapping for a CIM parameter"""
        valuemap = ['42']
        values = ['forty-two']

        vm = self.setup_for_element('parameter', server_arg, integer_type,
                                    is_array, valuemap, values)

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

    def test_repr(self, element_kind, server_arg, integer_type, is_array):
        # pylint: disable=redefined-outer-name
        """Test ValueMapping.__repr__()"""
        valuemap = ['1']
        values = ['one']

        vm = self.setup_for_element(element_kind, server_arg, integer_type,
                                    is_array, valuemap, values)

        r = repr(vm)

        assert re.match(r'^ValueMapping\(', r)

        # pylint: disable=protected-access

        exp_conn = f'_conn={vm._conn!r}'
        assert exp_conn in r

        exp_namespace = f'_namespace={vm._namespace!r}'
        assert exp_namespace in r

        exp_classname = f'_classname={vm._classname!r}'
        assert exp_classname in r

        exp_propname = f'_propname={vm._propname!r}'
        assert exp_propname in r

        exp_methodname = f'_methodname={vm._methodname!r}'
        assert exp_methodname in r

        exp_parametername = f'_parametername={vm._parametername!r}'
        assert exp_parametername in r

        exp_element_obj = f'_element_obj={vm._element_obj!r}'
        assert exp_element_obj in r

        # We don't check the internal data attributes.

    def test_invalid_valuemap_format(self, element_kind, server_arg,
                                     integer_type, is_array):
        # pylint: disable=redefined-outer-name
        """Test invalid ValueMap format"""
        valuemap = ['0x']
        values = ['zero']

        with pytest.raises(Exception) as exc_info:
            self.setup_for_element(element_kind, server_arg, integer_type,
                                   is_array, valuemap, values)
        exc = exc_info.value
        assert isinstance(exc, ModelError)
        exc_msg = exc.args[0]
        assert re.match(".*has an invalid integer representation in a "
                        "ValueMap entry.*",
                        exc_msg) is not None

    def test_invalid_element_type(self, element_kind, server_arg, is_array):
        # pylint: disable=redefined-outer-name
        """Test invalid type for the element"""
        valuemap = ['0']
        values = ['zero']

        with pytest.raises(Exception) as exc_info:
            self.setup_for_element(element_kind, server_arg, 'string',
                                   is_array, valuemap, values)
        exc = exc_info.value
        assert isinstance(exc, ModelError)
        exc_msg = exc.args[0]
        assert re.match(".*is not integer-typed.*",
                        exc_msg) is not None

    def test_invalid_tovalues_type(self, element_kind, server_arg,
                                   integer_type, is_array):
        # pylint: disable=redefined-outer-name
        """Test tovalues() with invalid type"""
        valuemap = ['0']
        values = ['zero']

        vm = self.setup_for_element(element_kind, server_arg, integer_type,
                                    is_array, valuemap, values)

        with pytest.raises(Exception) as exc_info:
            vm.tovalues('0')
        exc = exc_info.value
        assert isinstance(exc, TypeError)
        exc_msg = exc.args[0]
        assert re.match(".*is not integer-typed.*",
                        exc_msg) is not None

    def test_invalid_tobinary_type(self, element_kind, server_arg,
                                   integer_type, is_array):
        # pylint: disable=redefined-outer-name
        """Test tobinary() with invalid type"""
        valuemap = ['0']
        values = ['zero']

        vm = self.setup_for_element(element_kind, server_arg, integer_type,
                                    is_array, valuemap, values)

        with pytest.raises(Exception) as exc_info:
            vm.tobinary(0)
        exc = exc_info.value
        assert isinstance(exc, TypeError)
        exc_msg = exc.args[0]
        assert re.match(".*is not string-typed.*",
                        exc_msg) is not None

    def test_no_values_qualifier(self, element_kind, server_arg, integer_type,
                                 is_array):
        # pylint: disable=redefined-outer-name
        """Test element without Values qualifier"""
        valuemap = ['0']
        values = None

        with pytest.raises(Exception) as exc_info:
            self.setup_for_element(element_kind, server_arg, integer_type,
                                   is_array, valuemap, values)
        exc = exc_info.value
        assert isinstance(exc, ValueError)
        exc_msg = exc.args[0]
        assert re.match(".*has no Values qualifier defined.*",
                        exc_msg) is not None

    def test_valuemap_default(self, element_kind, server_arg, integer_type,
                              is_array):
        # pylint: disable=redefined-outer-name
        """Test default if no ValueMap qualifier is defined"""
        valuemap = None
        exp_valuemap = [0, 1, 2]
        values = ['zero', 'one', 'two']

        vm = self.setup_for_element(element_kind, server_arg, integer_type,
                                    is_array, valuemap, values)

        self.assertOutsideValueMap(vm, -1)
        assert vm.tovalues(0) == 'zero'
        assert vm.tovalues(1) == 'one'
        assert vm.tovalues(2) == 'two'
        self.assertOutsideValueMap(vm, 3)

        self.assertOutsideValues(vm, 'x')
        assert vm.tobinary('zero') == 0
        assert vm.tobinary('one') == 1
        assert vm.tobinary('two') == 2

        exp_items = list(zip(exp_valuemap, values))
        items = []
        for item in vm.items():
            items.append(item)
        assert items == exp_items

    def test_zero(self, element_kind, server_arg, integer_type, is_array):
        # pylint: disable=redefined-outer-name
        """Test valuemap with value 0"""
        valuemap = ['0']
        exp_valuemap = [0]
        values = ['zero']

        vm = self.setup_for_element(element_kind, server_arg, integer_type,
                                    is_array, valuemap, values)

        assert vm.tovalues(0) == 'zero'
        self.assertOutsideValueMap(vm, 1)

        self.assertOutsideValues(vm, 'x')
        assert vm.tobinary('zero') == 0

        exp_items = list(zip(exp_valuemap, values))
        items = []
        for item in vm.items():
            items.append(item)
        assert items == exp_items

    def test_one(self, element_kind, server_arg, integer_type, is_array):
        # pylint: disable=redefined-outer-name
        """Test valuemap with value 1"""
        valuemap = ['1']
        exp_valuemap = [1]
        values = ['one']

        vm = self.setup_for_element(element_kind, server_arg, integer_type,
                                    is_array, valuemap, values)

        self.assertOutsideValueMap(vm, 0)
        assert vm.tovalues(1) == 'one'
        self.assertOutsideValueMap(vm, 2)

        self.assertOutsideValues(vm, 'x')
        assert vm.tobinary('one') == 1

        exp_items = list(zip(exp_valuemap, values))
        items = []
        for item in vm.items():
            items.append(item)
        assert items == exp_items

    def test_tovalues_with_cimtype(self, element_kind, server_arg,
                                   integer_type, is_array):
        # pylint: disable=redefined-outer-name
        """Test tovalues() with argument of CIM type"""
        valuemap = ['1']
        values = ['one']

        vm = self.setup_for_element(element_kind, server_arg, integer_type,
                                    is_array, valuemap, values)

        cimtype = type_from_name(integer_type)
        assert vm.tovalues(cimtype(1)) == 'one'

    def test_tobinary_with_unicode(self, element_kind, server_arg,
                                   integer_type, is_array):
        # pylint: disable=redefined-outer-name
        """Test tobinary() with argument unicode string"""
        valuemap = ['1']
        values = ['one']

        vm = self.setup_for_element(element_kind, server_arg, integer_type,
                                    is_array, valuemap, values)

        assert vm.tobinary('one') == 1

    def test_singles(self, element_kind, server_arg, integer_type,
                     is_array):
        # pylint: disable=redefined-outer-name
        """Test valuemap with multiple non-range values"""
        valuemap = ['0', '1', '9']
        exp_valuemap = [0, 1, 9]
        values = ['zero', 'one', 'nine']

        vm = self.setup_for_element(element_kind, server_arg, integer_type,
                                    is_array, valuemap, values)

        assert vm.tovalues(0) == 'zero'
        assert vm.tovalues(1) == 'one'
        self.assertOutsideValueMap(vm, 2)
        self.assertOutsideValueMap(vm, 8)
        assert vm.tovalues(9) == 'nine'
        self.assertOutsideValueMap(vm, 10)

        self.assertOutsideValues(vm, 'x')
        assert vm.tobinary('zero') == 0
        assert vm.tobinary('one') == 1
        assert vm.tobinary('nine') == 9

        exp_items = list(zip(exp_valuemap, values))
        items = []
        for item in vm.items():
            items.append(item)
        assert items == exp_items

    def test_singles_ranges(self, element_kind, server_arg, integer_type,
                            is_array):
        # pylint: disable=redefined-outer-name
        """Test valuemap with ranges"""
        valuemap = ['0', '1', '2..4', '..6', '7..', '9']
        exp_valuemap = [0, 1, (2, 4), (5, 6), (7, 8), 9]
        values = ['zero', 'one', 'two-four', 'five-six', 'seven-eight', 'nine']

        vm = self.setup_for_element(element_kind, server_arg, integer_type,
                                    is_array, valuemap, values)

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

        self.assertOutsideValues(vm, 'x')
        assert vm.tobinary('zero') == 0
        assert vm.tobinary('one') == 1
        assert vm.tobinary('two-four') == (2, 4)
        assert vm.tobinary('five-six') == (5, 6)
        assert vm.tobinary('seven-eight') == (7, 8)
        assert vm.tobinary('nine') == 9

        exp_items = list(zip(exp_valuemap, values))
        items = []
        for item in vm.items():
            items.append(item)
        assert items == exp_items

    def test_unclaimed(self, element_kind, server_arg, integer_type,
                       is_array):
        # pylint: disable=redefined-outer-name
        """Test valuemap with unclaimed marker '..'"""
        valuemap = ['..']
        exp_valuemap = [None]
        values = ['unclaimed']

        vm = self.setup_for_element(element_kind, server_arg, integer_type,
                                    is_array, valuemap, values)

        assert vm.tovalues(0) == 'unclaimed'
        assert vm.tovalues(1) == 'unclaimed'
        assert vm.tovalues(2) == 'unclaimed'

        assert vm.tobinary('unclaimed') is None

        exp_items = list(zip(exp_valuemap, values))
        items = []
        for item in vm.items():
            items.append(item)
        assert items == exp_items

    def test_singles_ranges_unclaimed(self, element_kind, server_arg,
                                      integer_type, is_array):
        # pylint: disable=redefined-outer-name
        """Test valuemap with combination of singles, ranges, unclaimed"""
        valuemap = ['0', '1', '2..4', '..6', '7..', '9', '..']
        exp_valuemap = [0, 1, (2, 4), (5, 6), (7, 8), 9, None]
        values = ['zero', 'one', 'two-four', 'five-six', 'seven-eight', 'nine',
                  'unclaimed']

        vm = self.setup_for_element(element_kind, server_arg, integer_type,
                                    is_array, valuemap, values)

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

        assert vm.tobinary('zero') == 0
        assert vm.tobinary('one') == 1
        assert vm.tobinary('two-four') == (2, 4)
        assert vm.tobinary('five-six') == (5, 6)
        assert vm.tobinary('seven-eight') == (7, 8)
        assert vm.tobinary('nine') == 9
        assert vm.tobinary('unclaimed') is None

        exp_items = list(zip(exp_valuemap, values))
        items = []
        for item in vm.items():
            items.append(item)
        assert items == exp_items

    def test_singles_ranges_unclaimed2(self, element_kind, server_arg,
                                       integer_type, is_array):
        # pylint: disable=redefined-outer-name
        """Test singles, ranges, unclaimed"""
        valuemap = ['0', '2..4', '..6', '7..', '9', '..']
        exp_valuemap = [0, (2, 4), (5, 6), (7, 8), 9, None]
        values = ['zero', 'two-four', 'five-six', 'seven-eight', 'nine',
                  'unclaimed']

        vm = self.setup_for_element(element_kind, server_arg, integer_type,
                                    is_array, valuemap, values)

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

        assert vm.tobinary('zero') == 0
        assert vm.tobinary('two-four') == (2, 4)
        assert vm.tobinary('five-six') == (5, 6)
        assert vm.tobinary('seven-eight') == (7, 8)
        assert vm.tobinary('nine') == 9
        assert vm.tobinary('unclaimed') is None

        exp_items = list(zip(exp_valuemap, values))
        items = []
        for item in vm.items():
            items.append(item)
        assert items == exp_items

    def test_min_max_single(self, element_kind, server_arg, integer_type,
                            is_array):
        # pylint: disable=redefined-outer-name
        """Test valuemap with single min and max values of integer type"""

        minvalue = type_from_name(integer_type).minvalue
        maxvalue = type_from_name(integer_type).maxvalue

        valuemap = []
        valuemap.append(str(minvalue))
        valuemap.append(str(maxvalue))

        exp_valuemap = [minvalue, maxvalue]

        values = []
        for v in valuemap:
            values.append(f'val {v}')

        vm = self.setup_for_element(element_kind, server_arg, integer_type,
                                    is_array, valuemap, values)

        self.assertOutsideValueMap(vm, minvalue - 1)
        assert vm.tovalues(minvalue) == values[0]
        self.assertOutsideValueMap(vm, minvalue + 1)

        self.assertOutsideValueMap(vm, maxvalue - 1)
        assert vm.tovalues(maxvalue) == values[1]
        self.assertOutsideValueMap(vm, maxvalue + 1)

        self.assertOutsideValues(vm, 'x')
        assert vm.tobinary(values[0]) == minvalue
        assert vm.tobinary(values[1]) == maxvalue

        exp_items = list(zip(exp_valuemap, values))
        items = []
        for item in vm.items():
            items.append(item)
        assert items == exp_items

    def test_min_max_closed_ranges(self, element_kind, server_arg,
                                   integer_type, is_array):
        # pylint: disable=redefined-outer-name
        """Test valuemap with two closed ranges at min and max of int type"""

        minvalue = type_from_name(integer_type).minvalue
        maxvalue = type_from_name(integer_type).maxvalue

        valuemap = []
        valuemap.append(f'{minvalue}..{minvalue + 2}')
        valuemap.append(f'{maxvalue - 2}..{maxvalue}')

        exp_valuemap = [(minvalue, minvalue + 2), (maxvalue - 2, maxvalue)]

        values = []
        for v in valuemap:
            values.append(f'val {v}')

        vm = self.setup_for_element(element_kind, server_arg, integer_type,
                                    is_array, valuemap, values)

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

        self.assertOutsideValues(vm, 'x')
        assert vm.tobinary(values[0]) == (minvalue, minvalue + 2)
        assert vm.tobinary(values[1]) == (maxvalue - 2, maxvalue)

        exp_items = list(zip(exp_valuemap, values))
        items = []
        for item in vm.items():
            items.append(item)
        assert items == exp_items

    def test_min_max_open_range1(self, element_kind, server_arg, integer_type,
                                 is_array):
        # pylint: disable=redefined-outer-name
        """Test valuemap with open range 1 of min and max of integer type"""

        minvalue = type_from_name(integer_type).minvalue
        maxvalue = type_from_name(integer_type).maxvalue

        valuemap = []
        valuemap.append(f'{minvalue}')
        valuemap.append(f'..{minvalue + 2}')
        valuemap.append(f'{maxvalue - 2}..')
        valuemap.append(f'{maxvalue}')

        exp_valuemap = [minvalue, (minvalue + 1, minvalue + 2),
                        (maxvalue - 2, maxvalue - 1), maxvalue]

        values = []
        for v in valuemap:
            values.append(f'val {v}')

        vm = self.setup_for_element(element_kind, server_arg, integer_type,
                                    is_array, valuemap, values)

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

        self.assertOutsideValues(vm, 'x')
        assert vm.tobinary(values[0]) == minvalue
        assert vm.tobinary(values[1]) == (minvalue + 1, minvalue + 2)
        assert vm.tobinary(values[2]) == (maxvalue - 2, maxvalue - 1)
        assert vm.tobinary(values[3]) == maxvalue

        exp_items = list(zip(exp_valuemap, values))
        items = []
        for item in vm.items():
            items.append(item)
        assert items == exp_items

    def test_min_max_open_range2(self, element_kind, server_arg, integer_type,
                                 is_array):
        # pylint: disable=redefined-outer-name
        """Test valuemap with open range 2 of min and max of integer type"""

        minvalue = type_from_name(integer_type).minvalue
        maxvalue = type_from_name(integer_type).maxvalue

        valuemap = []
        valuemap.append(f'..{minvalue + 2}')
        valuemap.append(f'{maxvalue - 2}..')

        exp_valuemap = [(minvalue, minvalue + 2),
                        (maxvalue - 2, maxvalue)]

        values = []
        for v in valuemap:
            values.append(f'val {v}')

        vm = self.setup_for_element(element_kind, server_arg, integer_type,
                                    is_array, valuemap, values)

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

        self.assertOutsideValues(vm, 'x')
        assert vm.tobinary(values[0]) == (minvalue, minvalue + 2)
        assert vm.tobinary(values[1]) == (maxvalue - 2, maxvalue)

        exp_items = list(zip(exp_valuemap, values))
        items = []
        for item in vm.items():
            items.append(item)
        assert items == exp_items

    testcases_integer_representations = [
        # Each testcase has these items:
        # * desc: Short testcase description.
        # * integer_type: CIM type name of the ValueMap element.
        # * values_str_list: Input Values array.
        # * valuemap_str_list: Input ValueMap array with string represent.
        # * exp_valuemap_list: Expected valuemap array with integer values,
        #   or None if expecting failure.
        # * exp_exc_type: Expected exception type,
        #   or None if expecting success.
        # * exp_exc_msg_pattern: Expected pattern in exception message,
        #   or None if expecting success.
        # * condition: Condition for testcase to run.

        # General good cases
        (
            "Decimal integer values",
            "sint8",
            ['a', 'b', 'c'],
            ['0', '42', '-42'],
            [0, 42, -42],
            None, None,
            True
        ),
        (
            "Binary integer values",
            "sint8",
            ['a', 'b', 'c'],
            ['0b', '101B', '-111b'],
            [0, 5, -7],
            None, None,
            True
        ),
        (
            "Octal integer values",
            "sint8",
            ['a', 'b', 'c'],
            ['0', '017', '-011'],
            [0, 15, -9],
            None, None,
            True
        ),
        (
            "Hexadecimal integer values",
            "sint8",
            ['a', 'b', 'c'],
            ['0', '0x1F', '-0X0b'],
            [0, 31, -11],
            None, None,
            True
        ),
        (
            "Invalid integer value",
            "sint8",
            ['a'],
            ['B'],
            None,
            ModelError, None,
            True
        ),
    ]

    @pytest.mark.parametrize(
        "desc, integer_type, values_str_list, valuemap_str_list, "
        "exp_valuemap_list, exp_exc_type, exp_exc_msg_pattern, condition",
        testcases_integer_representations
    )
    def test_integer_representations(
            self, desc, integer_type, is_array, values_str_list,
            valuemap_str_list, exp_valuemap_list, exp_exc_type,
            exp_exc_msg_pattern, condition):
        # pylint: disable=redefined-outer-name,unused-argument
        """Test tobinary() in valuemap with different integer represent."""

        if not condition:
            pytest.skip("Condition for test case not met")

        if exp_exc_type is None:
            vm = self.setup_for_element('property', 'conn', integer_type,
                                        is_array, valuemap_str_list,
                                        values_str_list)
            for i, values_str in enumerate(values_str_list):
                exp_valuemap = exp_valuemap_list[i]
                valuemap = vm.tobinary(values_str)
                assert valuemap == exp_valuemap
        else:
            with pytest.raises(exp_exc_type) as exec_info:
                vm = self.setup_for_element('property', 'conn', integer_type,
                                            is_array, valuemap_str_list,
                                            values_str_list)
            if exp_exc_msg_pattern:
                exc = exec_info.value
                exc_msg = str(exc)
                one_line_exc_msg = exc_msg.replace('\n', '\\n')
                assert re.search(exp_exc_msg_pattern, one_line_exc_msg), \
                    "Unexpected exception message:\n" + exc_msg

    @pytest.mark.parametrize(
        "element_value",
        [
            [1, 2],
            (1, 2),
        ]
    )
    def test_tovalues_multiple_values(
            self, element_value, element_kind, server_arg, integer_type,
            is_array):
        # pylint: disable=redefined-outer-name
        """Test tovalues() with multiple element values"""
        valuemap = ['1', '2']
        values = ['one', 'two']

        vm = self.setup_for_element(element_kind, server_arg, integer_type,
                                    is_array, valuemap, values)
        result = vm.tovalues(element_value)
        assert result == ['one', 'two']

    def test_tovalues_none(
            self, element_kind, server_arg, integer_type, is_array):
        # pylint: disable=redefined-outer-name
        """Test tovalues() with element value of None"""
        valuemap = ['1', '2']
        values = ['one', 'two']

        vm = self.setup_for_element(element_kind, server_arg, integer_type,
                                    is_array, valuemap, values)
        result = vm.tovalues(None)
        assert result is None

    @pytest.mark.parametrize(
        "valuemap, values, values_default, exp_exc, exp_values",
        [
            (
                ['1'],
                ['one', 'two'],
                None,
                ModelError,
                None,
            ),
            (
                ['1'],
                ['one', 'two'],
                'foo',
                None,
                ['one'],
            ),
            (
                ['1', '2'],
                ['one'],
                None,
                ModelError,
                None,
            ),
            (
                ['1', '2'],
                ['one'],
                'foo',
                None,
                ['one', 'foo'],
            ),
            (
                [],
                ['one'],
                None,
                ModelError,
                None,
            ),
            (
                [],
                ['one'],
                'foo',
                None,
                [],
            ),
            (
                ['1'],
                [],
                None,
                ModelError,
                None,
            ),
            (
                ['1'],
                [],
                'foo',
                None,
                ['foo'],
            ),
        ]
    )
    def test_tovalues_different_sizes(
            self, valuemap, values, values_default, exp_exc, exp_values,
            element_kind, server_arg, integer_type, is_array):
        # pylint: disable=redefined-outer-name
        """Test tovalues() with differently sized ValueMap/Values"""
        if exp_exc:
            with pytest.raises(exp_exc):
                vm = self.setup_for_element(
                    element_kind, server_arg, integer_type, is_array, valuemap,
                    values, values_default)
        else:
            vm = self.setup_for_element(
                element_kind, server_arg, integer_type, is_array, valuemap,
                values, values_default)
            defaulted_values = []
            for v in valuemap:
                value = vm.tovalues(int(v))
                defaulted_values.append(value)
            assert defaulted_values == exp_values
