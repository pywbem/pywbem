"""
Test CIM-XML parsing routines in tupleparse.py.
"""

from __future__ import absolute_import

import pytest

from pywbem import tupletree, tupleparse
from pywbem import CIMInstance, CIMInstanceName, CIMClass, CIMProperty, \
    CIMParameter, CIMQualifier, Uint8, Uint16, Uint32
import pytest_extensions


testcases_CIMXML_Roundtrip_Parsing = [

    # Each testcase tuple has these items:
    # * desc: Short testcase description.
    # * kwargs: Input arguments for test function, as a dict:
    #   * obj: Input CIM object.
    # * exp_exc_types: Expected exception type(s), or None.
    # * exp_warn_types: Expected warning type(s), or None.
    # * condition: Boolean condition for testcase to run, or 'pdb' for
    #   debugger

    # CIMInstanceName tests
    (
        "CIMInstanceName with just classname",
        dict(
            obj=CIMInstanceName('CIM_Foo'),
        ),
        None, None, True
    ),
    (
        "CIMInstanceName with two string keybindings",
        dict(
            obj=CIMInstanceName(
                'CIM_Foo',
                [('Name', 'Foo'), ('Chicken', 'Ham')],
            ),
        ),
        None, None, True
    ),
    (
        "CIMInstanceName with keybindings of various types",
        dict(
            obj=CIMInstanceName(
                'CIM_Foo',
                [('Name', 'Foo'),
                 ('Number', Uint8(42)),
                 ('Boolean', False),
                 ('Ref', CIMInstanceName('CIM_Bar'))],
            ),
        ),
        None, None, True
    ),
    (
        "CIMInstanceName with keybindings and namespace",
        dict(
            obj=CIMInstanceName(
                'CIM_Foo',
                [('Name', 'Foo')],
                namespace='root/cimv2',
            ),
        ),
        None, None, True
    ),
    (
        "CIMInstanceName with keybindings, namespace and host",
        dict(
            obj=CIMInstanceName(
                'CIM_Foo',
                [('Name', 'Foo')],
                host='woot.com',
                namespace='root/cimv2',
            ),
        ),
        None, None, True
    ),

    # CIMInstance tests
    (
        "CIMInstance with just classname",
        dict(
            obj=CIMInstance('CIM_Foo'),
        ),
        None, None, True
    ),
    (
        "CIMInstance with classname and properties of various types",
        dict(
            obj=CIMInstance(
                'CIM_Foo',
                [('Pstring', 'string'),
                 ('Puint8', Uint8(0)),
                 ('Puint8array', [Uint8(1), Uint8(2)]),
                 ('Pref', CIMInstanceName('CIM_Bar'))],
            ),
        ),
        None, None, True
    ),
    (
        "CIMInstance with path",
        dict(
            obj=CIMInstance(
                'CIM_Foo',
                [('InstanceID', '1234')],
                path=CIMInstanceName(
                    'CIM_Foo',
                    [('InstanceID', '1234')],
                )
            ),
        ),
        None, None, True
    ),

    # CIMClass tests
    # TODO 2/16 KS: Add tests for more complete class.
    (
        "CIMClass with just classname",
        dict(
            obj=CIMClass('CIM_Foo'),
        ),
        None, None, True
    ),
    (
        "CIMClass with classname and superclass",
        dict(
            obj=CIMClass('CIM_Foo', superclass='CIM_Bar'),
        ),
        None, None, True
    ),
    (
        "CIMClass with qualifiers and properties",
        dict(
            obj=CIMClass(
                'CIM_CollectionInSystem',
                qualifiers=[
                    CIMQualifier('ASSOCIATION', True, overridable=False),
                    CIMQualifier('Aggregation', True, overridable=False),
                    CIMQualifier('Version', '2.6.0', tosubclass=False,
                                 translatable=False),
                    CIMQualifier('Description',
                                 'CIM_CollectionInSystem is an association '
                                 'used to establish a parent-child '
                                 'relationship between a collection and an '
                                 '\'owning\' System such as an AdminDomain or '
                                 'ComputerSystem. A single collection should '
                                 'not have both a CollectionInOrganization '
                                 'and a CollectionInSystem association.',
                                 translatable=True),
                ],
                properties=[
                    CIMProperty(
                        'Parent', None, type='reference',
                        reference_class='CIM_System',
                        qualifiers=[
                            CIMQualifier('Key', True, overridable=False),
                            CIMQualifier('Aggregate', True, overridable=False),
                            CIMQualifier('Max', Uint32(1)),
                        ]
                    ),
                    CIMProperty(
                        'Child', None, type='reference',
                        reference_class='CIM_Collection',
                        qualifiers=[
                            CIMQualifier('Key', True, overridable=False),
                        ]
                    ),
                ],
            ),
        ),
        None, None, True
    ),

    # Single-valued properties
    (
        "CIMProperty with string typed value",
        dict(
            obj=CIMProperty('Spotty', 'Foot'),
        ),
        None, None, True
    ),
    (
        "CIMProperty with uint16 typed value",
        dict(
            obj=CIMProperty('Age', Uint16(32)),
        ),
        None, None, True
    ),
    (
        "CIMProperty with empty string typed value",
        dict(
            obj=CIMProperty('Foo', '', type='string'),
        ),
        None, None, True
    ),
    (
        "CIMProperty with None string typed value",
        dict(
            obj=CIMProperty('Foo', None, type='string'),
        ),
        None, None, True
    ),
    (
        "CIMProperty with qualifier",
        dict(
            obj=CIMProperty(
                'Age', None, type='uint16',
                qualifiers=[
                    CIMQualifier('Key', True),
                ]
            ),
        ),
        None, None, True
    ),

    # Property arrays
    (
        "CIMProperty with string array typed value",
        dict(
            obj=CIMProperty('Foo', ['a', 'b', 'c']),
        ),
        None, None, True
    ),
    (
        "CIMProperty with None string array typed value",
        dict(
            obj=CIMProperty('Foo', None, type='string', is_array=True),
        ),
        None, None, True
    ),
    (
        "CIMProperty with uint8 array typed value and qualifiers",
        dict(
            obj=CIMProperty(
                'Foo', [Uint8(x) for x in [1, 2, 3]],
                qualifiers=[
                    CIMQualifier('Key', True),
                ]
            ),
        ),
        None, None, True
    ),

    # Reference properties
    (
        "CIMProperty with reference typed value None",
        dict(
            obj=CIMProperty('Foo', None, type='reference'),
        ),
        None, None, True
    ),
    (
        "CIMProperty with reference typed value",
        dict(
            obj=CIMProperty(
                'Foo',
                CIMInstanceName('CIM_Foo')
            ),
        ),
        None, None, True
    ),
    (
        "CIMProperty with reference typed value and qualifiers",
        dict(
            obj=CIMProperty(
                'Foo',
                CIMInstanceName('CIM_Foo'),
                qualifiers=[
                    CIMQualifier('Key', True),
                ]
            ),
        ),
        None, None, True
    ),

    # EmbeddedObject properties
    (
        "CIMProperty with embedded instance",
        dict(
            obj=CIMProperty(
                'Foo',
                CIMInstance(
                    'Foo_Class',
                    [('one', Uint8(1)),
                     ('two', Uint8(2))],
                ),
            ),
        ),
        None, None, True
    ),
    (
        "CIMProperty with array of embedded instance",
        dict(
            obj=CIMProperty(
                'Foo',
                [
                    CIMInstance(
                        'Foo_Class',
                        [('one', Uint8(1)),
                         ('two', Uint8(2))],
                    ),
                ]
            ),
        ),
        None, None, True
    ),

    # TODO 2/16 KS: Extend for all data types.
    # Single-valued parameters
    (
        "CIMParameter with string typed value",
        dict(
            obj=CIMParameter('Param', 'string'),
        ),
        None, None, True
    ),
    (
        "CIMParameter with string typed value and qualifiers",
        dict(
            obj=CIMParameter(
                'Param', 'string',
                qualifiers=[
                    CIMQualifier('Key', True),
                ]
            ),
        ),
        None, None, True
    ),

    # Reference parameters
    (
        "CIMParameter with reference typed value",
        dict(
            obj=CIMParameter('RefParam', 'reference'),
        ),
        None, None, True
    ),
    (
        "CIMParameter with reference typed value and ref class",
        dict(
            obj=CIMParameter(
                'RefParam', 'reference',
                reference_class='CIM_Foo'
            ),
        ),
        None, None, True
    ),
    (
        "CIMParameter with reference typed value and ref class and "
        "qualifiers",
        dict(
            obj=CIMParameter(
                'RefParam', 'reference',
                reference_class='CIM_Foo',
                qualifiers=[
                    CIMQualifier('Key', True),
                ]
            ),
        ),
        None, None, True
    ),

    # TODO 2/16 KS: Extend for all data types.
    # Array parameters
    (
        "CIMParameter with string array typed value",
        dict(
            obj=CIMParameter('Array', 'string', is_array=True),
        ),
        None, None, True
    ),
    (
        "CIMParameter with string foxed array typed value",
        dict(
            obj=CIMParameter('Array', 'string', is_array=True, array_size=10),
        ),
        None, None, True
    ),
    (
        "CIMParameter with string foxed array typed value and qualifiers",
        dict(
            obj=CIMParameter(
                'Array', 'string', is_array=True, array_size=10,
                qualifiers=[
                    CIMQualifier('Key', True),
                ]
            ),
        ),
        None, None, True
    ),

    # Reference array parameters
    (
        "CIMParameter with reference array typed value",
        dict(
            obj=CIMParameter('RefArray', 'reference', is_array=True),
        ),
        None, None, True
    ),
    (
        "CIMParameter with reference array typed value and ref class",
        dict(
            obj=CIMParameter(
                'RefArray', 'reference', is_array=True,
                reference_class='CIM_Foo'
            ),
        ),
        None, None, True
    ),
    (
        "CIMParameter with reference fixed array typed value and ref class",
        dict(
            obj=CIMParameter(
                'RefArray', 'reference', is_array=True, array_size=10,
                reference_class='CIM_Foo'
            ),
        ),
        None, None, True
    ),
    (
        "CIMParameter with reference fixed array typed value and ref class "
        "and qualifiers",
        dict(
            obj=CIMParameter(
                'RefArray', 'reference', is_array=True, array_size=10,
                reference_class='CIM_Foo',
                qualifiers=[
                    CIMQualifier('Key', True),
                ]
            ),
        ),
        None, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    testcases_CIMXML_Roundtrip_Parsing)
@pytest_extensions.test_function
def test_CIMXML_Roundtrip_Parsing(
        desc, kwargs, exp_exc_types, exp_warn_types, condition):
    """
    Test CIM-XML roundtrip parsing of CIM objects.

    The input CIM object is converted to a CIM-XML string, which is then
    parsed and the resulting CIM object is compared with the original
    object.
    """

    obj = kwargs['obj']

    xml_str = obj.tocimxml().toxml()
    tt = tupletree.xml_to_tupletree_sax(xml_str, 'Test-XML')

    # The code to be tested
    parsed_obj = tupleparse.parse_any(tt)

    assert parsed_obj == obj, "CIM-XML of input obj:\n%s" % xml_str


testcases_CIMXML_Parsing = [

    # Each testcase tuple has these items:
    # * desc: Short testcase description.
    # * kwargs: Input arguments for test function, as a dict:
    #   * xml_str: Input CIM-XML string.
    #   * exp_result: Expected parsing result.
    # * exp_exc_types: Expected exception type(s), or None.
    # * exp_warn_types: Expected warning type(s), or None.
    # * condition: Boolean condition for testcase to run, or 'pdb' for
    #   debugger

    # KEYVALUE tests
    (
        "KEYVALUE with numeric value as decimal 1234",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="numeric">1234</KEYVALUE>',
            exp_result=1234,
        ),
        None, None, True
    ),
    (
        "KEYVALUE with TYPE uint32 and numeric value as decimal 1234",
        dict(
            xml_str=''
            '<KEYVALUE TYPE="uint32" VALUETYPE="numeric">1234</KEYVALUE>',
            exp_result=1234,
        ),
        None, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    testcases_CIMXML_Parsing)
@pytest_extensions.test_function
def test_CIMXML_Parsing(
        desc, kwargs, exp_exc_types, exp_warn_types, condition):
    """
    Test parsing of CIM-XML string.

    The input CIM-XML string is parsed and the result is compared with an
    expected result.
    """

    xml_str = kwargs['xml_str']
    exp_result = kwargs['exp_result']

    tt = tupletree.xml_to_tupletree_sax(xml_str, 'Test-XML')

    # The code to be tested
    result = tupleparse.parse_any(tt)

    assert result == exp_result, "Input CIM-XML:\n%s" % xml_str
