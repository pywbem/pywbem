"""
Test CIM-XML parsing routines in tupleparse.py.
"""

from __future__ import absolute_import

import pytest

from pywbem import tupletree, tupleparse
from pywbem import CIMInstance, CIMInstanceName, CIMClass, CIMClassName, \
    CIMProperty, CIMMethod, CIMParameter, CIMQualifier, \
    CIMDateTime, Uint8, Sint8, Uint16, Sint16, Uint32, Sint32, Uint64, Sint64, \
    Real32, Real64, ParseError
import pytest_extensions


# Note: These roundtrip testcases cover only typical situations. The full set
# of possibilities including invalid input is tested in the XMl testcases (see
# testcases_tupleparse_xml).
testcases_tupleparse_roundtrip = [

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
                properties=[
                    CIMProperty('Pstring', value=None, type='string',
                                propagated=False),
                    CIMProperty('Puint8', value=Uint8(0),
                                propagated=False),
                    CIMProperty('Puint8array', value=[Uint8(1), Uint8(2)],
                                propagated=False),
                    CIMProperty('Pref', value=CIMInstanceName('CIM_Bar'),
                                propagated=False),
                ],
            ),
        ),
        None, None, True
    ),
    (
        "CIMInstance with path",
        dict(
            obj=CIMInstance(
                'CIM_Foo',
                properties=[
                    CIMProperty('InstanceID', value='1234', type='string',
                                propagated=False),
                ],
                path=CIMInstanceName(
                    'CIM_Foo',
                    [('InstanceID', '1234')],
                )
            ),
        ),
        None, None, True
    ),

    # CIMClass tests
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
                        propagated=False,
                        qualifiers=[
                            CIMQualifier('Key', True, overridable=False),
                            CIMQualifier('Aggregate', True, overridable=False),
                            CIMQualifier('Max', Uint32(1)),
                        ]
                    ),
                    CIMProperty(
                        'Child', None, type='reference',
                        reference_class='CIM_Collection',
                        propagated=False,
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
            obj=CIMProperty('Spotty', 'Foot', propagated=False),
        ),
        None, None, True
    ),
    (
        "CIMProperty with uint16 typed value",
        dict(
            obj=CIMProperty('Age', Uint16(32), propagated=False),
        ),
        None, None, True
    ),
    (
        "CIMProperty with empty string typed value",
        dict(
            obj=CIMProperty('Foo', '', type='string', propagated=False),
        ),
        None, None, True
    ),
    (
        "CIMProperty with None string typed value",
        dict(
            obj=CIMProperty('Foo', None, type='string', propagated=False),
        ),
        None, None, True
    ),
    (
        "CIMProperty with qualifier",
        dict(
            obj=CIMProperty(
                'Age', None, type='uint16',
                propagated=False,
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
            obj=CIMProperty('Foo', ['a', 'b', 'c'], propagated=False),
        ),
        None, None, True
    ),
    (
        "CIMProperty with None string array typed value",
        dict(
            obj=CIMProperty('Foo', None, type='string', is_array=True,
                            propagated=False),
        ),
        None, None, True
    ),
    (
        "CIMProperty with uint8 array typed value and qualifiers",
        dict(
            obj=CIMProperty(
                'Foo', [Uint8(x) for x in [1, 2, 3]],
                propagated=False,
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
            obj=CIMProperty('Foo', None, type='reference', propagated=False),
        ),
        None, None, True
    ),
    (
        "CIMProperty with reference typed value",
        dict(
            obj=CIMProperty(
                'Foo',
                CIMInstanceName('CIM_Foo'),
                propagated=False,
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
                propagated=False,
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
                    properties=[
                        CIMProperty('one', Uint8(1), propagated=False),
                        CIMProperty('two', Uint8(2), propagated=False),
                    ],
                ),
                propagated=False,
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
                        properties=[
                            CIMProperty('one', Uint8(1), propagated=False),
                            CIMProperty('two', Uint8(2), propagated=False),
                        ],
                    ),
                ],
                propagated=False,
            ),
        ),
        None, None, True
    ),

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
    testcases_tupleparse_roundtrip)
@pytest_extensions.test_function
def test_tupleparse_roundtrip(
        desc, kwargs, exp_exc_types, exp_warn_types, condition):
    """
    Test tupleparse parsing based upon roundtrip between CIM objects and their
    CIM-XML.

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


# Note: These XML testcases cover the full set of possibilities for each
# CIM-XML element, including invalid input.
testcases_tupleparse_xml = [

    # Each testcase tuple has these items:
    # * desc: Short testcase description.
    # * kwargs: Input arguments for test function, as a dict:
    #   * xml_str: Input CIM-XML string.
    #   * exp_result: Expected parsing result.
    # * exp_exc_types: Expected exception type(s), or None.
    # * exp_warn_types: Expected warning type(s), or None.
    # * condition: Boolean condition for testcase to run, or 'pdb' for
    #   debugger

    # General tests with invalidities
    (
        "Ill-formed XML (missing closing bracket on end element)",
        dict(
            xml_str='<HOST>abc</HOST',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "Ill-formed XML (missing slash on end element)",
        dict(
            xml_str='<HOST>abc<HOST>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "Ill-formed XML (missing opening bracket on end element)",
        dict(
            xml_str='<HOST>abc/HOST>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "Ill-formed XML (missing closing bracket on begin element)",
        dict(
            xml_str='<HOSTabc</HOST>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "Ill-formed XML (missing opening bracket on begin element)",
        dict(
            xml_str='HOST>abc</HOST>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "Ill-formed XML (non-matching end element)",
        dict(
            xml_str='<HOST>abc</HOST2>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "Ill-formed XML (no end element)",
        dict(
            xml_str='<HOST>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "Ill-formed XML (no begin element)",
        dict(
            xml_str='</HOST>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "Ill-formed XML (missing closing bracket in short form)",
        dict(
            xml_str='<HOST/',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "Ill-formed XML (missing opening bracket in short form)",
        dict(
            xml_str='HOST/>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "Ill-formed XML (missing =value on attribute)",
        dict(
            xml_str='<NAMESPACE NAME/>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "Ill-formed XML (missing value on attribute)",
        dict(
            xml_str='<NAMESPACE NAME=/>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "Ill-formed XML (missing double quotes around value on attribute)",
        dict(
            xml_str='<NAMESPACE NAME=abc/>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "Verify that single quoted attr values work (see XML spec AttValue)",
        dict(
            xml_str='<NAMESPACE NAME=\'abc\'/>',
            exp_result=u'abc',
        ),
        None, None, True
    ),
    (
        "Invalid element in CIM-XML",
        dict(
            xml_str=''
            '<FOO></FOO>',
            exp_result=None,
        ),
        ParseError, None, True
    ),

    # KEYVALUE tests with general invalidities
    (
        "KEYVALUE with invalid child element VALUETYPE",
        dict(
            xml_str=''
            '<KEYVALUE><VALUETYPE></VALUETYPE></KEYVALUE>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "KEYVALUE with invalid child element KEYVALUE",
        dict(
            xml_str=''
            '<KEYVALUE><KEYVALUE></KEYVALUE></KEYVALUE>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "KEYVALUE with invalid attribute KEYVALUE",
        dict(
            xml_str=''
            '<KEYVALUE KEYVALUE="bla"></KEYVALUE>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "KEYVALUE with invalid value for attribute VALUETYPE",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="bla"></KEYVALUE>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "KEYVALUE with invalid value for attribute TYPE",
        dict(
            xml_str=''
            '<KEYVALUE TYPE="bla"></KEYVALUE>',
            exp_result=None,
        ),
        ParseError, None, True
    ),

    # KEYVALUE tests without VALUETYPE and without TYPE
    (
        "KEYVALUE without VALUETYPE or TYPE (empty string, short form)",
        dict(
            xml_str=''
            '<KEYVALUE/>',
            exp_result=u'',
        ),
        None, None, True
    ),
    (
        "KEYVALUE without VALUETYPE or TYPE (empty string)",
        dict(
            xml_str=''
            '<KEYVALUE></KEYVALUE>',
            exp_result=u'',
        ),
        None, None, True
    ),
    (
        "KEYVALUE without VALUETYPE or TYPE (WS string)",
        dict(
            xml_str=''
            '<KEYVALUE>  </KEYVALUE>',
            exp_result=u'  ',
        ),
        None, None, True
    ),
    (
        "KEYVALUE without VALUETYPE or TYPE (ASCII string)",
        dict(
            xml_str=''
            '<KEYVALUE>abc</KEYVALUE>',
            exp_result=u'abc',
        ),
        None, None, True
    ),
    (
        "KEYVALUE without VALUETYPE or TYPE (ASCII string with whitespace)",
        dict(
            xml_str=''
            '<KEYVALUE> a  b c </KEYVALUE>',
            exp_result=u' a  b c ',
        ),
        None, None, True
    ),
    (
        "KEYVALUE without VALUETYPE or TYPE (non-ASCII string)",
        dict(
            xml_str=b''
            b'<KEYVALUE>\xC3\xA9</KEYVALUE>',
            exp_result=u'\u00E9',  # LATIN SMALL LETTER E WITH ACUTE
        ),
        None, None, True
    ),
    (
        "KEYVALUE without VALUETYPE or TYPE (decimal as string)",
        dict(
            xml_str=''
            '<KEYVALUE>42</KEYVALUE>',
            exp_result=u'42',
        ),
        None, None, True
    ),
    (
        "KEYVALUE without VALUETYPE or TYPE (decimal as string with whitesp.)",
        dict(
            xml_str=''
            '<KEYVALUE> 42 </KEYVALUE>',
            exp_result=u' 42 ',
        ),
        None, None, True
    ),
    (
        "KEYVALUE without VALUETYPE or TYPE (float as string)",
        dict(
            xml_str=''
            '<KEYVALUE>42.1</KEYVALUE>',
            exp_result=u'42.1',
        ),
        None, None, True
    ),
    (
        "KEYVALUE without VALUETYPE or TYPE (float as string with whitesp.)",
        dict(
            xml_str=''
            '<KEYVALUE> 42.1 </KEYVALUE>',
            exp_result=u' 42.1 ',
        ),
        None, None, True
    ),
    (
        "KEYVALUE without VALUETYPE or TYPE (true as string)",
        dict(
            xml_str=''
            '<KEYVALUE>true</KEYVALUE>',
            exp_result=u'true',
        ),
        None, None, True
    ),
    (
        "KEYVALUE without VALUETYPE or TYPE (false as string)",
        dict(
            xml_str=''
            '<KEYVALUE>false</KEYVALUE>',
            exp_result=u'false',
        ),
        None, None, True
    ),
    (
        "KEYVALUE without VALUETYPE or TYPE (true as string with whitespace)",
        dict(
            xml_str=''
            '<KEYVALUE> true </KEYVALUE>',
            exp_result=u' true ',
        ),
        None, None, True
    ),
    (
        "KEYVALUE without VALUETYPE or TYPE (datetime string)",
        dict(
            xml_str=''
            '<KEYVALUE>20140924193040.654321+120</KEYVALUE>',
            exp_result=u'20140924193040.654321+120',
        ),
        None, None, True
    ),

    # KEYVALUE tests without VALUETYPE but with TYPE string
    (
        "KEYVALUE without VALUETYPE and TYPE that is generally valid but "
        "not allowed with the default VALUETYPE",
        dict(
            xml_str=''
            '<KEYVALUE TYPE="uint8"></KEYVALUE>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "KEYVALUE without VALUETYPE with TYPE string (ASCII string)",
        dict(
            xml_str=''
            '<KEYVALUE TYPE="string">abc</KEYVALUE>',
            exp_result=u'abc',
        ),
        None, None, True
    ),
    (
        "KEYVALUE without VALUETYPE with TYPE string (ASCII string with WS)",
        dict(
            xml_str=''
            '<KEYVALUE TYPE="string"> a  b c </KEYVALUE>',
            exp_result=u' a  b c ',
        ),
        None, None, True
    ),
    (
        "KEYVALUE without VALUETYPE with TYPE string (non-ASCII string)",
        dict(
            xml_str=b''
            b'<KEYVALUE TYPE="string">\xC3\xA9</KEYVALUE>',
            exp_result=u'\u00E9',  # LATIN SMALL LETTER E WITH ACUTE
        ),
        None, None, True
    ),
    (
        "KEYVALUE without VALUETYPE with TYPE string (non-UCS-2 char)",
        dict(
            # U+010142: GREEK ACROPHONIC ATTIC ONE DRACHMA
            xml_str=b''
            b'<KEYVALUE TYPE="string">\xF0\x90\x85\x82</KEYVALUE>',
            exp_result=u'\U00010142',
        ),
        None, None, True
    ),
    (
        "KEYVALUE without VALUETYPE with TYPE string (decimal as string)",
        dict(
            xml_str=''
            '<KEYVALUE TYPE="string">42</KEYVALUE>',
            exp_result=u'42',
        ),
        None, None, True
    ),
    (
        "KEYVALUE without VALUETYPE with TYPE string (decimal as str with WS)",
        dict(
            xml_str=''
            '<KEYVALUE TYPE="string"> 42 </KEYVALUE>',
            exp_result=u' 42 ',
        ),
        None, None, True
    ),
    (
        "KEYVALUE without VALUETYPE with TYPE string (float as string)",
        dict(
            xml_str=''
            '<KEYVALUE TYPE="string">42.1</KEYVALUE>',
            exp_result=u'42.1',
        ),
        None, None, True
    ),
    (
        "KEYVALUE without VALUETYPE with TYPE string (float as string with WS)",
        dict(
            xml_str=''
            '<KEYVALUE TYPE="string"> 42.1 </KEYVALUE>',
            exp_result=u' 42.1 ',
        ),
        None, None, True
    ),
    (
        "KEYVALUE without VALUETYPE with TYPE string (true as string)",
        dict(
            xml_str=''
            '<KEYVALUE TYPE="string">true</KEYVALUE>',
            exp_result=u'true',
        ),
        None, None, True
    ),
    (
        "KEYVALUE without VALUETYPE with TYPE string (false as string)",
        dict(
            xml_str=''
            '<KEYVALUE TYPE="string">false</KEYVALUE>',
            exp_result=u'false',
        ),
        None, None, True
    ),
    (
        "KEYVALUE without VALUETYPE with TYPE string (true as string with WS)",
        dict(
            xml_str=''
            '<KEYVALUE TYPE="string"> true </KEYVALUE>',
            exp_result=u' true ',
        ),
        None, None, True
    ),
    (
        "KEYVALUE without VALUETYPE with TYPE string (datetime string)",
        dict(
            xml_str=''
            '<KEYVALUE TYPE="string">20140924193040.654321+120</KEYVALUE>',
            exp_result=u'20140924193040.654321+120',
        ),
        None, None, True
    ),

    # KEYVALUE tests without VALUETYPE but with TYPE char16
    (
        "KEYVALUE without VALUETYPE with TYPE char16 (invalid empty char)",
        dict(
            xml_str=''
            '<KEYVALUE TYPE="char16"></KEYVALUE>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "KEYVALUE without VALUETYPE with TYPE char16 (invalid two chars)",
        dict(
            xml_str=''
            '<KEYVALUE TYPE="char16">ab</KEYVALUE>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "KEYVALUE without VALUETYPE with TYPE char16 (WS char)",
        dict(
            xml_str=''
            '<KEYVALUE TYPE="char16"> </KEYVALUE>',
            exp_result=u' ',
        ),
        None, None, True
    ),
    (
        "KEYVALUE without VALUETYPE with TYPE char16 (ASCII char)",
        dict(
            xml_str=''
            '<KEYVALUE TYPE="char16">a</KEYVALUE>',
            exp_result=u'a',
        ),
        None, None, True
    ),
    (
        "KEYVALUE without VALUETYPE with TYPE char16 (non-ASCII UCS-2 char)",
        dict(
            xml_str=b''
            b'<KEYVALUE TYPE="char16">\xC3\xA9</KEYVALUE>',
            exp_result=u'\u00E9',  # LATIN SMALL LETTER E WITH ACUTE
        ),
        None, None, True
    ),
    (
        "KEYVALUE without VALUETYPE with TYPE char16 (non-UCS-2 char)",
        dict(
            # U+010142: GREEK ACROPHONIC ATTIC ONE DRACHMA
            xml_str=b''
            b'<KEYVALUE TYPE="char16">\xF0\x90\x85\x82</KEYVALUE>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "KEYVALUE without VALUETYPE with TYPE char16 (decimal as string)",
        dict(
            xml_str=''
            '<KEYVALUE TYPE="char16">4</KEYVALUE>',
            exp_result=u'4',
        ),
        None, None, True
    ),

    # KEYVALUE tests without VALUETYPE but with TYPE datetime
    (
        "KEYVALUE without VALUETYPE with TYPE datetime (empty string)",
        dict(
            xml_str=''
            '<KEYVALUE TYPE="datetime"></KEYVALUE>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "KEYVALUE without VALUETYPE with TYPE datetime (WS char)",
        dict(
            xml_str=''
            '<KEYVALUE TYPE="datetime"> </KEYVALUE>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "KEYVALUE without VALUETYPE with TYPE datetime (ASCII char)",
        dict(
            xml_str=''
            '<KEYVALUE TYPE="datetime">a</KEYVALUE>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "KEYVALUE without VALUETYPE with TYPE datetime (decimal as string)",
        dict(
            xml_str=''
            '<KEYVALUE TYPE="datetime">4</KEYVALUE>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "KEYVALUE without VALUETYPE with TYPE datetime (point in time string)",
        dict(
            xml_str=''
            '<KEYVALUE TYPE="datetime">20140924193040.654321+120</KEYVALUE>',
            exp_result=CIMDateTime('20140924193040.654321+120'),
        ),
        None, None, True
    ),
    (
        "KEYVALUE without VALUETYPE with TYPE datetime (interval string)",
        dict(
            xml_str=''
            '<KEYVALUE TYPE="datetime">00000183132542.234567:000</KEYVALUE>',
            exp_result=CIMDateTime('00000183132542.234567:000'),
        ),
        None, None, True
    ),

    # KEYVALUE tests with VALUETYPE string and TYPE string
    (
        "KEYVALUE with VALUETYPE string and TYPE that is generally valid but "
        "not allowed with that VALUETYPE",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="string" TYPE="uint8"></KEYVALUE>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "KEYVALUE with VALUETYPE string and TYPE string (empty string)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="string" TYPE="string"></KEYVALUE>',
            exp_result=u'',
        ),
        None, None, True
    ),
    (
        "KEYVALUE with VALUETYPE string and TYPE string (WS string)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="string" TYPE="string">  </KEYVALUE>',
            exp_result=u'  ',
        ),
        None, None, True
    ),
    (
        "KEYVALUE with VALUETYPE string and TYPE string (ASCII string)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="string" TYPE="string">abc</KEYVALUE>',
            exp_result=u'abc',
        ),
        None, None, True
    ),

    # KEYVALUE tests with VALUETYPE string and TYPE char16
    (
        "KEYVALUE with VALUETYPE string and TYPE char16 (invalid empty char)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="string" TYPE="char16"></KEYVALUE>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "KEYVALUE with VALUETYPE string and TYPE char16 (invalid two chars)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="string" TYPE="char16">ab</KEYVALUE>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "KEYVALUE with VALUETYPE string and TYPE char16 (WS char)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="string" TYPE="char16"> </KEYVALUE>',
            exp_result=u' ',
        ),
        None, None, True
    ),
    (
        "KEYVALUE with VALUETYPE string and TYPE char16 (ASCII char)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="string" TYPE="char16">a</KEYVALUE>',
            exp_result=u'a',
        ),
        None, None, True
    ),

    # KEYVALUE tests with VALUETYPE string and TYPE datetime
    (
        "KEYVALUE with VALUETYPE string and TYPE datetime (empty string)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="string" TYPE="datetime"></KEYVALUE>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "KEYVALUE with VALUETYPE string and TYPE datetime (point in time)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="string"'
            ' TYPE="datetime">20140924193040.654321+120</KEYVALUE>',
            exp_result=CIMDateTime('20140924193040.654321+120'),
        ),
        None, None, True
    ),

    # KEYVALUE tests with VALUETYPE boolean but without TYPE
    (
        "KEYVALUE with VALUETYPE boolean without TYPE (empty string)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="boolean"></KEYVALUE>',
            exp_result=None,
        ),
        None, None, True
    ),
    (
        "KEYVALUE with VALUETYPE boolean without TYPE (WS string)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="boolean">  </KEYVALUE>',
            exp_result=None,
        ),
        None, None, True
    ),
    (
        "KEYVALUE with VALUETYPE boolean without TYPE (ASCII string)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="boolean">abc</KEYVALUE>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "KEYVALUE with VALUETYPE boolean without TYPE (1 as string)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="boolean">1</KEYVALUE>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "KEYVALUE with VALUETYPE boolean without TYPE (0 as string)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="boolean">0</KEYVALUE>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "KEYVALUE with VALUETYPE boolean without TYPE (true as string)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="boolean">true</KEYVALUE>',
            exp_result=True,
        ),
        None, None, True
    ),
    (
        "KEYVALUE with VALUETYPE boolean without TYPE (false as string)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="boolean">false</KEYVALUE>',
            exp_result=False,
        ),
        None, None, True
    ),
    (
        "KEYVALUE with VALUETYPE boolean without TYPE (true as string with WS)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="boolean"> true </KEYVALUE>',
            exp_result=True,
        ),
        None, None, True
    ),
    (
        "KEYVALUE with VALUETYPE boolean without TYPE (false as str with WS)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="boolean"> false </KEYVALUE>',
            exp_result=False,
        ),
        None, None, True
    ),
    (
        "KEYVALUE with VALUETYPE boolean without TYPE (tRuE as string)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="boolean">tRuE</KEYVALUE>',
            exp_result=True,
        ),
        None, None, True
    ),
    (
        "KEYVALUE with VALUETYPE boolean without TYPE (fAlSe as string)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="boolean">fAlSe</KEYVALUE>',
            exp_result=False,
        ),
        None, None, True
    ),

    # KEYVALUE tests with VALUETYPE boolean and with TYPE boolean
    (
        "KEYVALUE with VALUETYPE boolean with TYPE boolean (empty string)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="boolean" TYPE="boolean"></KEYVALUE>',
            exp_result=None,
        ),
        None, None, True
    ),
    (
        "KEYVALUE with VALUETYPE boolean with TYPE boolean (WS string)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="boolean" TYPE="boolean">  </KEYVALUE>',
            exp_result=None,
        ),
        None, None, True
    ),
    (
        "KEYVALUE with VALUETYPE boolean with TYPE boolean (ASCII string)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="boolean" TYPE="boolean">abc</KEYVALUE>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "KEYVALUE with VALUETYPE boolean with TYPE boolean (1 as string)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="boolean" TYPE="boolean">1</KEYVALUE>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "KEYVALUE with VALUETYPE boolean with TYPE boolean (0 as string)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="boolean" TYPE="boolean">0</KEYVALUE>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "KEYVALUE with VALUETYPE boolean with TYPE boolean (true as string)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="boolean" TYPE="boolean">true</KEYVALUE>',
            exp_result=True,
        ),
        None, None, True
    ),
    (
        "KEYVALUE with VALUETYPE boolean with TYPE boolean (false as string)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="boolean" TYPE="boolean">false</KEYVALUE>',
            exp_result=False,
        ),
        None, None, True
    ),
    (
        "KEYVALUE with VALUETYPE boolean with TYPE boolean (true with WS)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="boolean" TYPE="boolean"> true </KEYVALUE>',
            exp_result=True,
        ),
        None, None, True
    ),
    (
        "KEYVALUE with VALUETYPE boolean with TYPE boolean (false with WS)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="boolean" TYPE="boolean"> false </KEYVALUE>',
            exp_result=False,
        ),
        None, None, True
    ),
    (
        "KEYVALUE with VALUETYPE boolean with TYPE boolean (tRuE as string)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="boolean" TYPE="boolean">tRuE</KEYVALUE>',
            exp_result=True,
        ),
        None, None, True
    ),
    (
        "KEYVALUE with VALUETYPE boolean with TYPE boolean (fAlSe as string)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="boolean" TYPE="boolean">fAlSe</KEYVALUE>',
            exp_result=False,
        ),
        None, None, True
    ),

    # KEYVALUE tests with VALUETYPE numeric but without TYPE
    (
        "KEYVALUE with VALUETYPE numeric without TYPE (empty string)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="numeric"></KEYVALUE>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "KEYVALUE with VALUETYPE numeric without TYPE (WS string)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="numeric">  </KEYVALUE>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "KEYVALUE with VALUETYPE numeric without TYPE (ASCII string)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="numeric">abc</KEYVALUE>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "KEYVALUE with VALUETYPE numeric without TYPE (decimal string 0)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="numeric">0</KEYVALUE>',
            exp_result=0,
        ),
        None, None, True
    ),
    (
        "KEYVALUE with VALUETYPE numeric without TYPE (decimal string 42)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="numeric">42</KEYVALUE>',
            exp_result=42,
        ),
        None, None, True
    ),
    (
        "KEYVALUE with VALUETYPE numeric without TYPE (decimal string -42)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="numeric">-42</KEYVALUE>',
            exp_result=-42,
        ),
        None, None, True
    ),
    (
        "KEYVALUE with VALUETYPE numeric without TYPE (decimal string that "
        "exceeds Python 2 positive int limit but not uint64)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="numeric">9223372036854775808</KEYVALUE>',
            exp_result=9223372036854775808,
        ),
        None, None, True
    ),
    (
        "KEYVALUE with VALUETYPE numeric without TYPE (decimal string that "
        "exceeds Python 2 negative int limit and also sint64)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="numeric">-9223372036854775809</KEYVALUE>',
            exp_result=-9223372036854775809,
        ),
        None, None, True
    ),
    (
        "KEYVALUE with VALUETYPE numeric without TYPE (decimal string that "
        "exceeds Python 2 positive int limit and also uint64)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="numeric">18446744073709551616</KEYVALUE>',
            exp_result=18446744073709551616,
        ),
        None, None, True
    ),
    (
        "KEYVALUE with VALUETYPE numeric without TYPE (hex string 0xA0)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="numeric">0xA0</KEYVALUE>',
            exp_result=160,
        ),
        None, None, True
    ),
    (
        "KEYVALUE with VALUETYPE numeric without TYPE (hex string 0Xa0)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="numeric">0Xa0</KEYVALUE>',
            exp_result=160,
        ),
        None, None, True
    ),
    (
        "KEYVALUE with VALUETYPE numeric without TYPE (hex string -0xA0)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="numeric">-0xA0</KEYVALUE>',
            exp_result=-160,
        ),
        None, None, True
    ),
    (
        "KEYVALUE with VALUETYPE numeric without TYPE (hex string +0xA0)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="numeric">+0xA0</KEYVALUE>',
            exp_result=160,
        ),
        None, None, True
    ),
    (
        "KEYVALUE with VALUETYPE numeric without TYPE (hex string that "
        "exceeds Python 2 positive int limit but not uint64)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="numeric">0x8000000000000000</KEYVALUE>',
            exp_result=9223372036854775808,
        ),
        None, None, True
    ),
    (
        "KEYVALUE with VALUETYPE numeric without TYPE (hex string that "
        "exceeds Python 2 negative int limit and also sint64)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="numeric">-0x8000000000000001</KEYVALUE>',
            exp_result=-9223372036854775809,
        ),
        None, None, True
    ),
    (
        "KEYVALUE with VALUETYPE numeric without TYPE (hex string that "
        "exceeds Python 2 positive int limit and also uint64)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="numeric">0x10000000000000000</KEYVALUE>',
            exp_result=18446744073709551616,
        ),
        None, None, True
    ),
    (
        "KEYVALUE with VALUETYPE numeric without TYPE (float string 42.0)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="numeric">42.0</KEYVALUE>',
            exp_result=42.0,
        ),
        None, None, True
    ),
    (
        "KEYVALUE with VALUETYPE numeric without TYPE (float string .0)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="numeric">.0</KEYVALUE>',
            exp_result=0.0,
        ),
        None, None, True
    ),
    (
        "KEYVALUE with VALUETYPE numeric without TYPE (float string -.1e-12)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="numeric">-.1e-12</KEYVALUE>',
            exp_result=-0.1E-12,
        ),
        None, None, True
    ),
    (
        "KEYVALUE with VALUETYPE numeric without TYPE (float string .1E12)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="numeric">.1e12</KEYVALUE>',
            exp_result=0.1E+12,
        ),
        None, None, True
    ),
    (
        "KEYVALUE with VALUETYPE numeric without TYPE (float string +.1e+12)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="numeric">.1e12</KEYVALUE>',
            exp_result=0.1E+12,
        ),
        None, None, True
    ),

    # KEYVALUE tests with VALUETYPE numeric and TYPE (sintNN/uintNN/realNN)
    (
        "KEYVALUE with VALUETYPE numeric and TYPE uint32 and numeric value "
        "with invalid decimal digits",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="numeric" TYPE="uint32">9a</KEYVALUE>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "KEYVALUE with VALUETYPE numeric and TYPE uint8 and numeric value that "
        "exceeds the data type limit",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="numeric" TYPE="uint8">1234</KEYVALUE>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "KEYVALUE with VALUETYPE numeric and TYPE uint8 (empty string)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="numeric" TYPE="uint8"></KEYVALUE>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "KEYVALUE with VALUETYPE numeric and TYPE sint64 (WS string)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="numeric" TYPE="sint64">  </KEYVALUE>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "KEYVALUE with VALUETYPE numeric and TYPE real32 (ASCII string)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="numeric" TYPE="real32">abc</KEYVALUE>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "KEYVALUE with VALUETYPE numeric and TYPE uint8 (decimal string 0)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="numeric" TYPE="uint8">0</KEYVALUE>',
            exp_result=Uint8(0),
        ),
        None, None, True
    ),
    (
        "KEYVALUE with VALUETYPE numeric and TYPE uint16 (decimal string 42)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="numeric" TYPE="uint16">42</KEYVALUE>',
            exp_result=Uint16(42),
        ),
        None, None, True
    ),
    (
        "KEYVALUE with VALUETYPE numeric and TYPE sint16 (decimal string -42)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="numeric" TYPE="sint16">-42</KEYVALUE>',
            exp_result=Sint16(-42),
        ),
        None, None, True
    ),
    (
        "KEYVALUE with VALUETYPE numeric and TYPE uint8 (decimal max neg.)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="numeric" TYPE="uint8">0</KEYVALUE>',
            exp_result=Uint8(0),
        ),
        None, None, True
    ),
    (
        "KEYVALUE with VALUETYPE numeric and TYPE uint8 (decimal max pos.)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="numeric" TYPE="uint8">255</KEYVALUE>',
            exp_result=Uint8(255),
        ),
        None, None, True
    ),
    (
        "KEYVALUE with VALUETYPE numeric and TYPE uint16 (decimal max neg.)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="numeric" TYPE="uint16">0</KEYVALUE>',
            exp_result=Uint16(0),
        ),
        None, None, True
    ),
    (
        "KEYVALUE with VALUETYPE numeric and TYPE uint16 (decimal max pos.)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="numeric" TYPE="uint16">65535</KEYVALUE>',
            exp_result=Uint16(65535),
        ),
        None, None, True
    ),
    (
        "KEYVALUE with VALUETYPE numeric and TYPE uint32 (decimal max neg.)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="numeric" TYPE="uint32">0</KEYVALUE>',
            exp_result=Uint32(0),
        ),
        None, None, True
    ),
    (
        "KEYVALUE with VALUETYPE numeric and TYPE uint32 (decimal max pos.)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="numeric" TYPE="uint32">4294967295</KEYVALUE>',
            exp_result=Uint32(4294967295),
        ),
        None, None, True
    ),
    (
        "KEYVALUE with VALUETYPE numeric and TYPE uint64 (decimal max neg.)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="numeric" TYPE="uint64">0</KEYVALUE>',
            exp_result=Uint64(0),
        ),
        None, None, True
    ),
    (
        "KEYVALUE with VALUETYPE numeric and TYPE uint64 (decimal max pos., "
        "exceeds Python 2 positive int limit but not uint64)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="numeric"'
            ' TYPE="uint64">18446744073709551615</KEYVALUE>',
            exp_result=Uint64(18446744073709551615),
        ),
        None, None, True
    ),
    (
        "KEYVALUE with VALUETYPE numeric and TYPE sint8 (decimal max neg.)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="numeric" TYPE="sint8">-128</KEYVALUE>',
            exp_result=Sint8(-128),
        ),
        None, None, True
    ),
    (
        "KEYVALUE with VALUETYPE numeric and TYPE sint8 (decimal max pos.)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="numeric" TYPE="sint8">127</KEYVALUE>',
            exp_result=Sint8(127),
        ),
        None, None, True
    ),
    (
        "KEYVALUE with VALUETYPE numeric and TYPE sint16 (decimal max neg.)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="numeric" TYPE="sint16">-32768</KEYVALUE>',
            exp_result=Sint16(-32768),
        ),
        None, None, True
    ),
    (
        "KEYVALUE with VALUETYPE numeric and TYPE sint16 (decimal max pos.)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="numeric" TYPE="sint16">32767</KEYVALUE>',
            exp_result=Sint16(32767),
        ),
        None, None, True
    ),
    (
        "KEYVALUE with VALUETYPE numeric and TYPE sint32 (decimal max neg.)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="numeric"'
            ' TYPE="sint32">-2147483648</KEYVALUE>',
            exp_result=Sint32(-2147483648),
        ),
        None, None, True
    ),
    (
        "KEYVALUE with VALUETYPE numeric and TYPE sint32 (decimal max pos.)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="numeric" TYPE="sint32">2147483647</KEYVALUE>',
            exp_result=Sint32(2147483647),
        ),
        None, None, True
    ),
    (
        "KEYVALUE with VALUETYPE numeric and TYPE sint64 (decimal max neg., "
        "exceeds Python 2 negative int limit but not sint64)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="numeric"'
            ' TYPE="sint64">-9223372036854775808</KEYVALUE>',
            exp_result=Sint64(-9223372036854775808),
        ),
        None, None, True
    ),
    (
        "KEYVALUE with VALUETYPE numeric and TYPE sint64 (decimal max pos., "
        "exceeds Python 2 positive int limit but not sint64)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="numeric"'
            ' TYPE="sint64">9223372036854775807</KEYVALUE>',
            exp_result=Sint64(9223372036854775807),
        ),
        None, None, True
    ),
    (
        "KEYVALUE with VALUETYPE numeric and TYPE sint64 (decimal max neg., "
        "exceeds Python 2 negative int limit and also sint64)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="numeric"'
            ' TYPE="sint64">-9223372036854775809</KEYVALUE>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "KEYVALUE with VALUETYPE numeric and TYPE uint32 (hex string 0xA0)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="numeric" TYPE="uint32">0xA0</KEYVALUE>',
            exp_result=Uint32(160),
        ),
        None, None, True
    ),
    (
        "KEYVALUE with VALUETYPE numeric and TYPE uint32 (hex string 0Xa0)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="numeric" TYPE="uint32">0Xa0</KEYVALUE>',
            exp_result=Uint32(160),
        ),
        None, None, True
    ),
    (
        "KEYVALUE with VALUETYPE numeric and TYPE sint32 (hex string -0xA0)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="numeric" TYPE="sint32">-0xA0</KEYVALUE>',
            exp_result=Sint32(-160),
        ),
        None, None, True
    ),
    (
        "KEYVALUE with VALUETYPE numeric and TYPE uint32 (hex string +0xA0)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="numeric" TYPE="uint32">+0xA0</KEYVALUE>',
            exp_result=Uint32(160),
        ),
        None, None, True
    ),
    (
        "KEYVALUE with VALUETYPE numeric and TYPE uint64 (hex string, "
        "exceeds Python 2 positive int limit but not uint64)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="numeric"'
            ' TYPE="uint64">0x8000000000000000</KEYVALUE>',
            exp_result=Uint64(9223372036854775808),
        ),
        None, None, True
    ),
    (
        "KEYVALUE with VALUETYPE numeric and TYPE sint64 (hex string, "
        "exceeds Python 2 negative int limit and also sint64)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="numeric"'
            ' TYPE="sint64">-0x8000000000000001</KEYVALUE>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "KEYVALUE with VALUETYPE numeric and TYPE real32 (float str 42.0)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="numeric" TYPE="real32">42.0</KEYVALUE>',
            exp_result=Real32(42.0),
        ),
        None, None, True
    ),
    (
        "KEYVALUE with VALUETYPE numeric and TYPE real64 (float str .0)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="numeric" TYPE="real64">.0</KEYVALUE>',
            exp_result=Real64(0.0),
        ),
        None, None, True
    ),
    (
        "KEYVALUE with VALUETYPE numeric and TYPE real32 (float str -.1e-12)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="numeric" TYPE="real32">-.1e-12</KEYVALUE>',
            exp_result=Real32(-0.1E-12),
        ),
        None, None, True
    ),
    (
        "KEYVALUE with VALUETYPE numeric and TYPE real32 (float str .1E12)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="numeric" TYPE="real32">.1e12</KEYVALUE>',
            exp_result=Real32(0.1E+12),
        ),
        None, None, True
    ),
    (
        "KEYVALUE with VALUETYPE numeric and TYPE real32 (float str +.1e+12)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="numeric" TYPE="real32">.1e12</KEYVALUE>',
            exp_result=Real32(0.1E+12),
        ),
        None, None, True
    ),

    # KEYBINDING tests
    (
        "KEYBINDING with invalid extra child element",
        dict(
            xml_str=''
            '<KEYBINDING NAME="Foo">'
            '  <KEYVALUE></KEYVALUE>'
            '  <XXX></XXX>'
            '</KEYBINDING>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "KEYBINDING with invalid text content",
        dict(
            xml_str=''
            '<KEYBINDING NAME="Foo">'
            '  <KEYVALUE></KEYVALUE>'
            '  xxx'
            '</KEYBINDING>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "KEYBINDING with invalid extra attribute",
        dict(
            xml_str=''
            '<KEYBINDING NAME="Foo" XXX="bla">'
            '  <KEYVALUE></KEYVALUE>'
            '</KEYBINDING>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "KEYBINDING with missing required attribute NAME",
        dict(
            xml_str=''
            '<KEYBINDING>'
            '  <KEYVALUE></KEYVALUE>'
            '</KEYBINDING>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "KEYBINDING with KEYVALUE child (normal case)",
        dict(
            xml_str=''
            '<KEYBINDING NAME="Foo">'
            '  <KEYVALUE>a</KEYVALUE>'
            '</KEYBINDING>',
            exp_result={u'Foo': u'a'},
        ),
        None, None, True
    ),
    (
        "KEYBINDING with KEYVALUE child (empty name)",
        dict(
            xml_str=''
            '<KEYBINDING NAME="">'
            '  <KEYVALUE>a</KEYVALUE>'
            '</KEYBINDING>',
            exp_result={u'': u'a'},
        ),
        None, None, True
    ),
    (
        "KEYBINDING with VALUE.REFERENCE child (normal case)",
        dict(
            xml_str=''
            '<KEYBINDING NAME="Foo">'
            '  <VALUE.REFERENCE>'
            '    <INSTANCENAME CLASSNAME="CIM_Foo"/>'
            '  </VALUE.REFERENCE>'
            '</KEYBINDING>',
            exp_result={u'Foo': CIMInstanceName('CIM_Foo')},
        ),
        None, None, True
    ),

    # TODO: VALUE tests

    # VALUE.ARRAY tests
    (
        "VALUE.ARRAY with invalid kind of child element as first item",
        dict(
            xml_str=''
            '<VALUE.ARRAY>'
            '  <XXX></XXX>'
            '  <VALUE>a</VALUE>'
            '</VALUE.ARRAY>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "VALUE.ARRAY with invalid kind of child element as second item",
        dict(
            xml_str=''
            '<VALUE.ARRAY>'
            '  <VALUE>a</VALUE>'
            '  <XXX></XXX>'
            '</VALUE.ARRAY>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "VALUE.ARRAY with invalid text content",
        dict(
            xml_str=''
            '<VALUE.ARRAY>'
            '  <VALUE>a</VALUE>'
            '  xxx'
            '</VALUE.ARRAY>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "VALUE.ARRAY with invalid extra attribute",
        dict(
            xml_str=''
            '<VALUE.ARRAY XXX="bla">'
            '  <VALUE>a</VALUE>'
            '</VALUE.ARRAY>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "VALUE.ARRAY that is empty",
        dict(
            xml_str=''
            '<VALUE.ARRAY>'
            '</VALUE.ARRAY>',
            exp_result=[
            ],
        ),
        None, None, True
    ),
    (
        "VALUE.ARRAY with one item (string value)",
        dict(
            xml_str=''
            '<VALUE.ARRAY>'
            '  <VALUE>a</VALUE>'
            '</VALUE.ARRAY>',
            exp_result=[
                u'a',
            ],
        ),
        None, None, True
    ),
    (
        "VALUE.ARRAY with two items (string value)",
        dict(
            xml_str=''
            '<VALUE.ARRAY>'
            '  <VALUE>a</VALUE>'
            '  <VALUE>b</VALUE>'
            '</VALUE.ARRAY>',
            exp_result=[
                u'a',
                u'b',
            ],
        ),
        None, None, True
    ),
    (
        "VALUE.ARRAY with one item (string that is numeric value)",
        dict(
            xml_str=''
            '<VALUE.ARRAY>'
            '  <VALUE>42</VALUE>'
            '</VALUE.ARRAY>',
            exp_result=[
                u'42',
            ],
        ),
        None, None, True
    ),
    (
        "VALUE.ARRAY with one item (string that is boolean keyword)",
        dict(
            xml_str=''
            '<VALUE.ARRAY>'
            '  <VALUE>TRUE</VALUE>'
            '</VALUE.ARRAY>',
            exp_result=[
                u'TRUE',
            ],
        ),
        None, None, True
    ),
    (
        # TODO 1/18 AM: Enable once VALUE.NULL is supported.
        "VALUE.ARRAY with one VALUE.NULL item",
        dict(
            xml_str=''
            '<VALUE.ARRAY>'
            '  <VALUE.NULL/>'
            '</VALUE.ARRAY>',
            exp_result=[
                None,
            ],
        ),
        None, None, False
    ),
    (
        # TODO 1/18 AM: Enable once VALUE.NULL is supported.
        "VALUE.ARRAY with a VALUE.NULL item and a string item",
        dict(
            xml_str=''
            '<VALUE.ARRAY>'
            '  <VALUE.NULL/>'
            '  <VALUE>a</VALUE>'
            '</VALUE.ARRAY>',
            exp_result=[
                None,
                u'a',
            ],
        ),
        None, None, False
    ),
    (
        # TODO 1/18 AM: Enable once VALUE.NULL is supported.
        "VALUE.ARRAY with VALUE.NULL, string, VALUE.NULL items",
        dict(
            xml_str=''
            '<VALUE.ARRAY>'
            '  <VALUE.NULL/>'
            '  <VALUE>a</VALUE>'
            '  <VALUE.NULL/>'
            '</VALUE.ARRAY>',
            exp_result=[
                None,
                u'a',
                None,
            ],
        ),
        None, None, False
    ),

    # TODO: VALUE.REFERENCE tests

    # VALUE.REFARRAY tests
    (
        "VALUE.REFARRAY with invalid extra child element",
        dict(
            xml_str=''
            '<VALUE.REFARRAY>'
            '  <VALUE.REFERENCE>'
            '    <INSTANCENAME CLASSNAME="CIM_Foo"/>'
            '  </VALUE.REFERENCE>'
            '  <XXX></XXX>'
            '</VALUE.REFARRAY>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "VALUE.REFARRAY with invalid text content",
        dict(
            xml_str=''
            '<VALUE.REFARRAY>'
            '  <VALUE.REFERENCE>'
            '    <INSTANCENAME CLASSNAME="CIM_Foo"/>'
            '  </VALUE.REFERENCE>'
            '  xxx'
            '</VALUE.REFARRAY>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "VALUE.REFARRAY with invalid extra attribute",
        dict(
            xml_str=''
            '<VALUE.REFARRAY XXX="bla">'
            '  <VALUE.REFERENCE>'
            '    <INSTANCENAME CLASSNAME="CIM_Foo"/>'
            '  </VALUE.REFERENCE>'
            '</VALUE.REFARRAY>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "VALUE.REFARRAY that is empty",
        dict(
            xml_str=''
            '<VALUE.REFARRAY>'
            '</VALUE.REFARRAY>',
            exp_result=[
            ],
        ),
        None, None, True
    ),
    (
        "VALUE.REFARRAY with one item",
        dict(
            xml_str=''
            '<VALUE.REFARRAY>'
            '  <VALUE.REFERENCE>'
            '    <INSTANCENAME CLASSNAME="CIM_Foo"/>'
            '  </VALUE.REFERENCE>'
            '</VALUE.REFARRAY>',
            exp_result=[
                CIMInstanceName('CIM_Foo'),
            ],
        ),
        None, None, True
    ),
    (
        "VALUE.REFARRAY with two items",
        dict(
            xml_str=''
            '<VALUE.REFARRAY>'
            '  <VALUE.REFERENCE>'
            '    <INSTANCENAME CLASSNAME="CIM_Foo"/>'
            '  </VALUE.REFERENCE>'
            '  <VALUE.REFERENCE>'
            '    <INSTANCENAME CLASSNAME="CIM_Bar"/>'
            '  </VALUE.REFERENCE>'
            '</VALUE.REFARRAY>',
            exp_result=[
                CIMInstanceName('CIM_Foo'),
                CIMInstanceName('CIM_Bar'),
            ],
        ),
        None, None, True
    ),
    (
        # TODO 1/18 AM: Enable once VALUE.NULL is supported.
        "VALUE.REFARRAY with one VALUE.NULL item",
        dict(
            xml_str=''
            '<VALUE.REFARRAY>'
            '  <VALUE.NULL/>'
            '</VALUE.REFARRAY>',
            exp_result=[
                None,
            ],
        ),
        None, None, False
    ),
    (
        # TODO 1/18 AM: Enable once VALUE.NULL is supported.
        "VALUE.REFARRAY with a VALUE.NULL item and a reference item",
        dict(
            xml_str=''
            '<VALUE.REFARRAY>'
            '  <VALUE.NULL/>'
            '  <VALUE.REFERENCE>'
            '    <INSTANCENAME CLASSNAME="CIM_Foo"/>'
            '  </VALUE.REFERENCE>'
            '</VALUE.REFARRAY>',
            exp_result=[
                None,
                CIMInstanceName('CIM_Foo'),
            ],
        ),
        None, None, False
    ),
    (
        # TODO 1/18 AM: Enable once VALUE.NULL is supported.
        "VALUE.REFARRAY with VALUE.NULL, reference, VALUE.NULL items",
        dict(
            xml_str=''
            '<VALUE.REFARRAY>'
            '  <VALUE.NULL/>'
            '  <VALUE.REFERENCE>'
            '    <INSTANCENAME CLASSNAME="CIM_Foo"/>'
            '  </VALUE.REFERENCE>'
            '  <VALUE.NULL/>'
            '</VALUE.REFARRAY>',
            exp_result=[
                None,
                CIMInstanceName('CIM_Foo'),
                None,
            ],
        ),
        None, None, False
    ),

    # TODO: VALUE.NULL tests (once supported)

    # VALUE.OBJECT tests
    (
        "VALUE.OBJECT with invalid extra child element",
        dict(
            xml_str=''
            '<VALUE.OBJECT>'
            '  <INSTANCE CLASSNAME="CIM_Foo"/>'
            '  <XXX></XXX>'
            '</VALUE.OBJECT>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "VALUE.OBJECT with invalid child element instead",
        dict(
            xml_str=''
            '<VALUE.OBJECT>'
            '  <XXX></XXX>'
            '</VALUE.OBJECT>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "VALUE.OBJECT with invalid text content",
        dict(
            xml_str=''
            '<VALUE.OBJECT>'
            '  <INSTANCE CLASSNAME="CIM_Foo"/>'
            '  xxx'
            '</VALUE.OBJECT>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "VALUE.OBJECT with invalid extra attribute",
        dict(
            xml_str=''
            '<VALUE.OBJECT XXX="bla">'
            '  <INSTANCE CLASSNAME="CIM_Foo"/>'
            '</VALUE.OBJECT>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "VALUE.OBJECT with missing child",
        dict(
            xml_str=''
            '<VALUE.OBJECT>'
            '</VALUE.OBJECT>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "VALUE.OBJECT with INSTANCE (normal case)",
        dict(
            xml_str=''
            '<VALUE.OBJECT>'
            '  <INSTANCE CLASSNAME="CIM_Foo"/>'
            '</VALUE.OBJECT>',
            exp_result=(  # tupletree
                'VALUE.OBJECT',
                {},
                CIMInstance('CIM_Foo'),
            ),
        ),
        None, None, True
    ),
    (
        "VALUE.OBJECT with CLASS (normal case)",
        dict(
            xml_str=''
            '<VALUE.OBJECT>'
            '  <CLASS NAME="CIM_Foo"/>'
            '</VALUE.OBJECT>',
            exp_result=(  # tupletree
                'VALUE.OBJECT',
                {},
                CIMClass('CIM_Foo'),
            ),
        ),
        None, None, True
    ),

    # VALUE.NAMEDINSTANCE tests
    (
        "VALUE.NAMEDINSTANCE with invalid extra child element",
        dict(
            xml_str=''
            '<VALUE.NAMEDINSTANCE>'
            '  <INSTANCENAME CLASSNAME="CIM_Foo">'
            '    <KEYBINDING NAME="Name">'
            '      <KEYVALUE>Foo</KEYVALUE>'
            '    </KEYBINDING>'
            '  </INSTANCENAME>'
            '  <INSTANCE CLASSNAME="CIM_Foo"/>'
            '  <XXX></XXX>'
            '</VALUE.NAMEDINSTANCE>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "VALUE.NAMEDINSTANCE with invalid text content",
        dict(
            xml_str=''
            '<VALUE.NAMEDINSTANCE>'
            '  <INSTANCENAME CLASSNAME="CIM_Foo">'
            '    <KEYBINDING NAME="Name">'
            '      <KEYVALUE>Foo</KEYVALUE>'
            '    </KEYBINDING>'
            '  </INSTANCENAME>'
            '  <INSTANCE CLASSNAME="CIM_Foo"/>'
            '  xxx'
            '</VALUE.NAMEDINSTANCE>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "VALUE.NAMEDINSTANCE with invalid extra attribute",
        dict(
            xml_str=''
            '<VALUE.NAMEDINSTANCE XXX="bla">'
            '  <INSTANCENAME CLASSNAME="CIM_Foo">'
            '    <KEYBINDING NAME="Name">'
            '      <KEYVALUE>Foo</KEYVALUE>'
            '    </KEYBINDING>'
            '  </INSTANCENAME>'
            '  <INSTANCE CLASSNAME="CIM_Foo"/>'
            '</VALUE.NAMEDINSTANCE>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "VALUE.NAMEDINSTANCE with missing child INSTANCENAME",
        dict(
            xml_str=''
            '<VALUE.NAMEDINSTANCE>'
            '  <INSTANCE CLASSNAME="CIM_Foo"/>'
            '</VALUE.NAMEDINSTANCE>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "VALUE.NAMEDINSTANCE with missing child INSTANCE",
        dict(
            xml_str=''
            '<VALUE.NAMEDINSTANCE>'
            '  <INSTANCENAME CLASSNAME="CIM_Foo">'
            '    <KEYBINDING NAME="Name">'
            '      <KEYVALUE>Foo</KEYVALUE>'
            '    </KEYBINDING>'
            '  </INSTANCENAME>'
            '</VALUE.NAMEDINSTANCE>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "VALUE.NAMEDINSTANCE with children in incorrect order",
        dict(
            xml_str=''
            '<VALUE.NAMEDINSTANCE>'
            '  <INSTANCE CLASSNAME="CIM_Foo"/>'
            '  <INSTANCENAME CLASSNAME="CIM_Foo">'
            '    <KEYBINDING NAME="Name">'
            '      <KEYVALUE>Foo</KEYVALUE>'
            '    </KEYBINDING>'
            '  </INSTANCENAME>'
            '</VALUE.NAMEDINSTANCE>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "VALUE.NAMEDINSTANCE (normal case)",
        dict(
            xml_str=''
            '<VALUE.NAMEDINSTANCE>'
            '  <INSTANCENAME CLASSNAME="CIM_Foo">'
            '    <KEYBINDING NAME="Name">'
            '      <KEYVALUE>Foo</KEYVALUE>'
            '    </KEYBINDING>'
            '  </INSTANCENAME>'
            '  <INSTANCE CLASSNAME="CIM_Foo"/>'
            '</VALUE.NAMEDINSTANCE>',
            exp_result=CIMInstance(
                'CIM_Foo',
                path=CIMInstanceName(
                    'CIM_Foo',
                    [('Name', 'Foo')],
                ),
            ),
        ),
        None, None, True
    ),

    # VALUE.INSTANCEWITHPATH tests
    (
        "VALUE.INSTANCEWITHPATH with invalid extra child element",
        dict(
            xml_str=''
            '<VALUE.INSTANCEWITHPATH>'
            '  <INSTANCEPATH>'
            '    <NAMESPACEPATH>'
            '      <HOST>woot.com</HOST>'
            '      <LOCALNAMESPACEPATH>'
            '        <NAMESPACE NAME="foo"/>'
            '      </LOCALNAMESPACEPATH>'
            '    </NAMESPACEPATH>'
            '    <INSTANCENAME CLASSNAME="CIM_Foo">'
            '      <KEYBINDING NAME="Name">'
            '        <KEYVALUE>Foo</KEYVALUE>'
            '      </KEYBINDING>'
            '    </INSTANCENAME>'
            '  </INSTANCEPATH>'
            '  <INSTANCE CLASSNAME="CIM_Foo"/>'
            '  <XXX></XXX>'
            '</VALUE.INSTANCEWITHPATH>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "VALUE.INSTANCEWITHPATH with invalid text content",
        dict(
            xml_str=''
            '<VALUE.INSTANCEWITHPATH>'
            '  <INSTANCEPATH>'
            '    <NAMESPACEPATH>'
            '      <HOST>woot.com</HOST>'
            '      <LOCALNAMESPACEPATH>'
            '        <NAMESPACE NAME="foo"/>'
            '      </LOCALNAMESPACEPATH>'
            '    </NAMESPACEPATH>'
            '    <INSTANCENAME CLASSNAME="CIM_Foo">'
            '      <KEYBINDING NAME="Name">'
            '        <KEYVALUE>Foo</KEYVALUE>'
            '      </KEYBINDING>'
            '    </INSTANCENAME>'
            '  </INSTANCEPATH>'
            '  <INSTANCE CLASSNAME="CIM_Foo"/>'
            '  xxx'
            '</VALUE.INSTANCEWITHPATH>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "VALUE.INSTANCEWITHPATH with invalid extra attribute",
        dict(
            xml_str=''
            '<VALUE.INSTANCEWITHPATH XXX="bla">'
            '  <INSTANCEPATH>'
            '    <NAMESPACEPATH>'
            '      <HOST>woot.com</HOST>'
            '      <LOCALNAMESPACEPATH>'
            '        <NAMESPACE NAME="foo"/>'
            '      </LOCALNAMESPACEPATH>'
            '    </NAMESPACEPATH>'
            '    <INSTANCENAME CLASSNAME="CIM_Foo">'
            '      <KEYBINDING NAME="Name">'
            '        <KEYVALUE>Foo</KEYVALUE>'
            '      </KEYBINDING>'
            '    </INSTANCENAME>'
            '  </INSTANCEPATH>'
            '  <INSTANCE CLASSNAME="CIM_Foo"/>'
            '</VALUE.INSTANCEWITHPATH>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "VALUE.INSTANCEWITHPATH with missing child INSTANCEPATH",
        dict(
            xml_str=''
            '<VALUE.INSTANCEWITHPATH>'
            '  <INSTANCE CLASSNAME="CIM_Foo"/>'
            '</VALUE.INSTANCEWITHPATH>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "VALUE.INSTANCEWITHPATH with missing child INSTANCE",
        dict(
            xml_str=''
            '<VALUE.INSTANCEWITHPATH>'
            '  <INSTANCEPATH>'
            '    <NAMESPACEPATH>'
            '      <HOST>woot.com</HOST>'
            '      <LOCALNAMESPACEPATH>'
            '        <NAMESPACE NAME="foo"/>'
            '      </LOCALNAMESPACEPATH>'
            '    </NAMESPACEPATH>'
            '    <INSTANCENAME CLASSNAME="CIM_Foo">'
            '      <KEYBINDING NAME="Name">'
            '        <KEYVALUE>Foo</KEYVALUE>'
            '      </KEYBINDING>'
            '    </INSTANCENAME>'
            '  </INSTANCEPATH>'
            '</VALUE.INSTANCEWITHPATH>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "VALUE.INSTANCEWITHPATH with children in incorrect order",
        dict(
            xml_str=''
            '<VALUE.INSTANCEWITHPATH>'
            '  <INSTANCE CLASSNAME="CIM_Foo"/>'
            '  <INSTANCEPATH>'
            '    <NAMESPACEPATH>'
            '      <HOST>woot.com</HOST>'
            '      <LOCALNAMESPACEPATH>'
            '        <NAMESPACE NAME="foo"/>'
            '      </LOCALNAMESPACEPATH>'
            '    </NAMESPACEPATH>'
            '    <INSTANCENAME CLASSNAME="CIM_Foo">'
            '      <KEYBINDING NAME="Name">'
            '        <KEYVALUE>Foo</KEYVALUE>'
            '      </KEYBINDING>'
            '    </INSTANCENAME>'
            '  </INSTANCEPATH>'
            '</VALUE.INSTANCEWITHPATH>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "VALUE.INSTANCEWITHPATH (normal case)",
        dict(
            xml_str=''
            '<VALUE.INSTANCEWITHPATH>'
            '  <INSTANCEPATH>'
            '    <NAMESPACEPATH>'
            '      <HOST>woot.com</HOST>'
            '      <LOCALNAMESPACEPATH>'
            '        <NAMESPACE NAME="foo"/>'
            '      </LOCALNAMESPACEPATH>'
            '    </NAMESPACEPATH>'
            '    <INSTANCENAME CLASSNAME="CIM_Foo">'
            '      <KEYBINDING NAME="Name">'
            '        <KEYVALUE>Foo</KEYVALUE>'
            '      </KEYBINDING>'
            '    </INSTANCENAME>'
            '  </INSTANCEPATH>'
            '  <INSTANCE CLASSNAME="CIM_Foo"/>'
            '</VALUE.INSTANCEWITHPATH>',
            exp_result=CIMInstance(
                'CIM_Foo',
                path=CIMInstanceName(
                    'CIM_Foo',
                    [('Name', 'Foo')],
                    namespace='foo',
                    host='woot.com',
                ),
            ),
        ),
        None, None, True
    ),

    # VALUE.NAMEDOBJECT tests
    (
        "VALUE.NAMEDOBJECT with invalid extra child element",
        dict(
            xml_str=''
            '<VALUE.NAMEDOBJECT>'
            '  <CLASS NAME="CIM_Foo"/>'
            '  <XXX></XXX>'
            '</VALUE.NAMEDOBJECT>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "VALUE.NAMEDOBJECT with invalid text content",
        dict(
            xml_str=''
            '<VALUE.NAMEDOBJECT>'
            '  <CLASS NAME="CIM_Foo"/>'
            '  xxx'
            '</VALUE.NAMEDOBJECT>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "VALUE.NAMEDOBJECT with invalid extra attribute",
        dict(
            xml_str=''
            '<VALUE.NAMEDOBJECT XXX="bla">'
            '  <CLASS NAME="CIM_Foo"/>'
            '</VALUE.NAMEDOBJECT>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "VALUE.NAMEDOBJECT with missing children",
        dict(
            xml_str=''
            '<VALUE.NAMEDOBJECT>'
            '</VALUE.NAMEDOBJECT>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "VALUE.NAMEDOBJECT for instance with missing INSTANCENAME child",
        dict(
            xml_str=''
            '<VALUE.NAMEDOBJECT>'
            '  <INSTANCE CLASSNAME="CIM_Foo"/>'
            '</VALUE.NAMEDOBJECT>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "VALUE.NAMEDOBJECT for instance with missing INSTANCE child",
        dict(
            xml_str=''
            '<VALUE.NAMEDOBJECT>'
            '  <INSTANCENAME CLASSNAME="CIM_Foo">'
            '    <KEYBINDING NAME="Name">'
            '      <KEYVALUE>Foo</KEYVALUE>'
            '    </KEYBINDING>'
            '  </INSTANCENAME>'
            '</VALUE.NAMEDOBJECT>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "VALUE.NAMEDOBJECT for instance (normal case)",
        dict(
            xml_str=''
            '<VALUE.NAMEDOBJECT>'
            '  <INSTANCENAME CLASSNAME="CIM_Foo">'
            '    <KEYBINDING NAME="Name">'
            '      <KEYVALUE>Foo</KEYVALUE>'
            '    </KEYBINDING>'
            '  </INSTANCENAME>'
            '  <INSTANCE CLASSNAME="CIM_Foo"/>'
            '</VALUE.NAMEDOBJECT>',
            exp_result=(  # tupletree
                'VALUE.NAMEDOBJECT',
                {},
                CIMInstance(
                    'CIM_Foo',
                    path=CIMInstanceName(
                        'CIM_Foo',
                        [('Name', 'Foo')],
                    ),
                ),
            ),
        ),
        None, None, True
    ),
    (
        "VALUE.NAMEDOBJECT for class (normal case)",
        dict(
            xml_str=''
            '<VALUE.NAMEDOBJECT>'
            '  <CLASS NAME="CIM_Foo"/>'
            '</VALUE.NAMEDOBJECT>',
            exp_result=(  # tupletree
                'VALUE.NAMEDOBJECT',
                {},
                CIMClass('CIM_Foo'),
            ),
        ),
        None, None, True
    ),

    # VALUE.OBJECTWITHLOCALPATH tests
    (
        "VALUE.OBJECTWITHLOCALPATH with invalid extra child element",
        dict(
            xml_str=''
            '<VALUE.OBJECTWITHLOCALPATH>'
            '  <LOCALCLASSPATH>'
            '    <LOCALNAMESPACEPATH>'
            '      <NAMESPACE NAME="foo"/>'
            '    </LOCALNAMESPACEPATH>'
            '    <CLASSNAME NAME="CIM_Foo"/>'
            '  </LOCALCLASSPATH>'
            '  <CLASS NAME="CIM_Foo"/>'
            '  <XXX></XXX>'
            '</VALUE.OBJECTWITHLOCALPATH>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "VALUE.OBJECTWITHLOCALPATH with invalid text content",
        dict(
            xml_str=''
            '<VALUE.OBJECTWITHLOCALPATH>'
            '  <LOCALCLASSPATH>'
            '    <LOCALNAMESPACEPATH>'
            '      <NAMESPACE NAME="foo"/>'
            '    </LOCALNAMESPACEPATH>'
            '    <CLASSNAME NAME="CIM_Foo"/>'
            '  </LOCALCLASSPATH>'
            '  <CLASS NAME="CIM_Foo"/>'
            '  xxx'
            '</VALUE.OBJECTWITHLOCALPATH>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "VALUE.OBJECTWITHLOCALPATH with invalid extra attribute",
        dict(
            xml_str=''
            '<VALUE.OBJECTWITHLOCALPATH XXX="bla">'
            '  <LOCALCLASSPATH>'
            '    <LOCALNAMESPACEPATH>'
            '      <NAMESPACE NAME="foo"/>'
            '    </LOCALNAMESPACEPATH>'
            '    <CLASSNAME NAME="CIM_Foo"/>'
            '  </LOCALCLASSPATH>'
            '  <CLASS NAME="CIM_Foo"/>'
            '</VALUE.OBJECTWITHLOCALPATH>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "VALUE.OBJECTWITHLOCALPATH with missing children",
        dict(
            xml_str=''
            '<VALUE.OBJECTWITHLOCALPATH>'
            '</VALUE.OBJECTWITHLOCALPATH>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "VALUE.OBJECTWITHLOCALPATH for instance with missing LOCALINSTANCEPATH "
        "child",
        dict(
            xml_str=''
            '<VALUE.OBJECTWITHLOCALPATH>'
            '  <INSTANCE CLASSNAME="CIM_Foo"/>'
            '</VALUE.OBJECTWITHLOCALPATH>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "VALUE.OBJECTWITHLOCALPATH for instance with missing INSTANCE child",
        dict(
            xml_str=''
            '<VALUE.OBJECTWITHLOCALPATH>'
            '  <LOCALINSTANCEPATH>'
            '    <LOCALNAMESPACEPATH>'
            '      <NAMESPACE NAME="foo"/>'
            '    </LOCALNAMESPACEPATH>'
            '    <INSTANCENAME CLASSNAME="CIM_Foo">'
            '      <KEYBINDING NAME="Name">'
            '        <KEYVALUE>Foo</KEYVALUE>'
            '      </KEYBINDING>'
            '    </INSTANCENAME>'
            '  </LOCALINSTANCEPATH>'
            '</VALUE.OBJECTWITHLOCALPATH>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "VALUE.OBJECTWITHLOCALPATH for instance (normal case)",
        dict(
            xml_str=''
            '<VALUE.OBJECTWITHLOCALPATH>'
            '  <LOCALINSTANCEPATH>'
            '    <LOCALNAMESPACEPATH>'
            '      <NAMESPACE NAME="foo"/>'
            '    </LOCALNAMESPACEPATH>'
            '    <INSTANCENAME CLASSNAME="CIM_Foo">'
            '      <KEYBINDING NAME="Name">'
            '        <KEYVALUE>Foo</KEYVALUE>'
            '      </KEYBINDING>'
            '    </INSTANCENAME>'
            '  </LOCALINSTANCEPATH>'
            '  <INSTANCE CLASSNAME="CIM_Foo"/>'
            '</VALUE.OBJECTWITHLOCALPATH>',
            exp_result=(  # tupletree
                'VALUE.OBJECTWITHLOCALPATH',
                {},
                # returned as instance with path
                CIMInstance(
                    'CIM_Foo',
                    path=CIMInstanceName(
                        'CIM_Foo',
                        [('Name', 'Foo')],
                        namespace='foo',
                    ),
                ),
            ),
        ),
        None, None, True
    ),
    (
        "VALUE.OBJECTWITHLOCALPATH for class (normal case)",
        dict(
            xml_str=''
            '<VALUE.OBJECTWITHLOCALPATH>'
            '  <LOCALCLASSPATH>'
            '    <LOCALNAMESPACEPATH>'
            '      <NAMESPACE NAME="foo"/>'
            '    </LOCALNAMESPACEPATH>'
            '    <CLASSNAME NAME="CIM_Foo"/>'
            '  </LOCALCLASSPATH>'
            '  <CLASS NAME="CIM_Foo"/>'
            '</VALUE.OBJECTWITHLOCALPATH>',
            exp_result=(  # tupletree
                'VALUE.OBJECTWITHLOCALPATH',
                {},
                (  # returned as tuple (classpath, class)
                    CIMClassName(
                        'CIM_Foo',
                        namespace='foo',
                    ),
                    CIMClass(
                        'CIM_Foo',
                    ),
                ),
            ),
        ),
        None, None, True
    ),

    # VALUE.OBJECTWITHPATH tests
    (
        "VALUE.OBJECTWITHPATH with invalid extra child element",
        dict(
            xml_str=''
            '<VALUE.OBJECTWITHPATH>'
            '  <CLASSPATH>'
            '    <NAMESPACEPATH>'
            '      <HOST>woot.com</HOST>'
            '      <LOCALNAMESPACEPATH>'
            '        <NAMESPACE NAME="foo"/>'
            '      </LOCALNAMESPACEPATH>'
            '    </NAMESPACEPATH>'
            '    <CLASSNAME NAME="CIM_Foo"/>'
            '  </CLASSPATH>'
            '  <CLASS NAME="CIM_Foo"/>'
            '  <XXX></XXX>'
            '</VALUE.OBJECTWITHPATH>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "VALUE.OBJECTWITHPATH with invalid text content",
        dict(
            xml_str=''
            '<VALUE.OBJECTWITHPATH>'
            '  <CLASSPATH>'
            '    <NAMESPACEPATH>'
            '      <HOST>woot.com</HOST>'
            '      <LOCALNAMESPACEPATH>'
            '        <NAMESPACE NAME="foo"/>'
            '      </LOCALNAMESPACEPATH>'
            '    </NAMESPACEPATH>'
            '    <CLASSNAME NAME="CIM_Foo"/>'
            '  </CLASSPATH>'
            '  <CLASS NAME="CIM_Foo"/>'
            '  xxx'
            '</VALUE.OBJECTWITHPATH>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "VALUE.OBJECTWITHPATH with invalid extra attribute",
        dict(
            xml_str=''
            '<VALUE.OBJECTWITHPATH XXX="bla">'
            '  <CLASSPATH>'
            '    <NAMESPACEPATH>'
            '      <HOST>woot.com</HOST>'
            '      <LOCALNAMESPACEPATH>'
            '        <NAMESPACE NAME="foo"/>'
            '      </LOCALNAMESPACEPATH>'
            '    </NAMESPACEPATH>'
            '    <CLASSNAME NAME="CIM_Foo"/>'
            '  </CLASSPATH>'
            '  <CLASS NAME="CIM_Foo"/>'
            '</VALUE.OBJECTWITHPATH>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "VALUE.OBJECTWITHPATH with missing children",
        dict(
            xml_str=''
            '<VALUE.OBJECTWITHPATH>'
            '</VALUE.OBJECTWITHPATH>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "VALUE.OBJECTWITHPATH for instance with missing INSTANCEPATH child",
        dict(
            xml_str=''
            '<VALUE.OBJECTWITHPATH>'
            '  <INSTANCE CLASSNAME="CIM_Foo"/>'
            '</VALUE.OBJECTWITHPATH>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "VALUE.OBJECTWITHPATH for instance with missing INSTANCE child",
        dict(
            xml_str=''
            '<VALUE.OBJECTWITHPATH>'
            '  <INSTANCEPATH>'
            '    <NAMESPACEPATH>'
            '      <HOST>woot.com</HOST>'
            '      <LOCALNAMESPACEPATH>'
            '        <NAMESPACE NAME="foo"/>'
            '      </LOCALNAMESPACEPATH>'
            '    </NAMESPACEPATH>'
            '    <INSTANCENAME CLASSNAME="CIM_Foo">'
            '      <KEYBINDING NAME="Name">'
            '        <KEYVALUE>Foo</KEYVALUE>'
            '      </KEYBINDING>'
            '    </INSTANCENAME>'
            '  </INSTANCEPATH>'
            '</VALUE.OBJECTWITHPATH>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "VALUE.OBJECTWITHPATH for instance with incorrectly ordered children",
        dict(
            xml_str=''
            '<VALUE.OBJECTWITHPATH>'
            '  <INSTANCE CLASSNAME="CIM_Foo"/>'
            '  <INSTANCEPATH>'
            '    <NAMESPACEPATH>'
            '      <HOST>woot.com</HOST>'
            '      <LOCALNAMESPACEPATH>'
            '        <NAMESPACE NAME="foo"/>'
            '      </LOCALNAMESPACEPATH>'
            '    </NAMESPACEPATH>'
            '    <INSTANCENAME CLASSNAME="CIM_Foo">'
            '      <KEYBINDING NAME="Name">'
            '        <KEYVALUE>Foo</KEYVALUE>'
            '      </KEYBINDING>'
            '    </INSTANCENAME>'
            '  </INSTANCEPATH>'
            '</VALUE.OBJECTWITHPATH>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "VALUE.OBJECTWITHPATH for instance (normal case)",
        dict(
            xml_str=''
            '<VALUE.OBJECTWITHPATH>'
            '  <INSTANCEPATH>'
            '    <NAMESPACEPATH>'
            '      <HOST>woot.com</HOST>'
            '      <LOCALNAMESPACEPATH>'
            '        <NAMESPACE NAME="foo"/>'
            '      </LOCALNAMESPACEPATH>'
            '    </NAMESPACEPATH>'
            '    <INSTANCENAME CLASSNAME="CIM_Foo">'
            '      <KEYBINDING NAME="Name">'
            '        <KEYVALUE>Foo</KEYVALUE>'
            '      </KEYBINDING>'
            '    </INSTANCENAME>'
            '  </INSTANCEPATH>'
            '  <INSTANCE CLASSNAME="CIM_Foo"/>'
            '</VALUE.OBJECTWITHPATH>',
            exp_result=(  # tupletree
                'VALUE.OBJECTWITHPATH',
                {},
                # returned as instance with path
                CIMInstance(
                    'CIM_Foo',
                    path=CIMInstanceName(
                        'CIM_Foo',
                        [('Name', 'Foo')],
                        namespace='foo',
                        host='woot.com',
                    ),
                ),
            ),
        ),
        None, None, True
    ),
    (
        "VALUE.OBJECTWITHPATH for class with missing CLASSPATH child",
        dict(
            xml_str=''
            '<VALUE.OBJECTWITHPATH>'
            '  <CLASS NAME="CIM_Foo"/>'
            '</VALUE.OBJECTWITHPATH>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "VALUE.OBJECTWITHPATH for class with missing CLASS child",
        dict(
            xml_str=''
            '<VALUE.OBJECTWITHPATH>'
            '  <CLASSPATH>'
            '    <NAMESPACEPATH>'
            '      <HOST>woot.com</HOST>'
            '      <LOCALNAMESPACEPATH>'
            '        <NAMESPACE NAME="foo"/>'
            '      </LOCALNAMESPACEPATH>'
            '    </NAMESPACEPATH>'
            '    <CLASSNAME NAME="CIM_Foo"/>'
            '  </CLASSPATH>'
            '</VALUE.OBJECTWITHPATH>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "VALUE.OBJECTWITHPATH for class with incorrectly ordered children",
        dict(
            xml_str=''
            '<VALUE.OBJECTWITHPATH>'
            '  <CLASS NAME="CIM_Foo"/>'
            '  <CLASSPATH>'
            '    <NAMESPACEPATH>'
            '      <HOST>woot.com</HOST>'
            '      <LOCALNAMESPACEPATH>'
            '        <NAMESPACE NAME="foo"/>'
            '      </LOCALNAMESPACEPATH>'
            '    </NAMESPACEPATH>'
            '    <CLASSNAME NAME="CIM_Foo"/>'
            '  </CLASSPATH>'
            '</VALUE.OBJECTWITHPATH>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "VALUE.OBJECTWITHPATH for class (normal case)",
        dict(
            xml_str=''
            '<VALUE.OBJECTWITHPATH>'
            '  <CLASSPATH>'
            '    <NAMESPACEPATH>'
            '      <HOST>woot.com</HOST>'
            '      <LOCALNAMESPACEPATH>'
            '        <NAMESPACE NAME="foo"/>'
            '      </LOCALNAMESPACEPATH>'
            '    </NAMESPACEPATH>'
            '    <CLASSNAME NAME="CIM_Foo"/>'
            '  </CLASSPATH>'
            '  <CLASS NAME="CIM_Foo"/>'
            '</VALUE.OBJECTWITHPATH>',
            exp_result=(  # tupletree
                'VALUE.OBJECTWITHPATH',
                {},
                (  # returned as tuple (classpath, class)
                    CIMClassName(
                        'CIM_Foo',
                        namespace='foo',
                        host='woot.com',
                    ),
                    CIMClass(
                        'CIM_Foo',
                    ),
                ),
            ),
        ),
        None, None, True
    ),

    # NAMESPACE tests
    (
        "NAMESPACE with invalid extra child element",
        dict(
            xml_str=''
            '<NAMESPACE NAME="a">'
            '  <XXX></XXX>'
            '</NAMESPACE>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "NAMESPACE with invalid text content",
        dict(
            xml_str=''
            '<NAMESPACE NAME="a">'
            '  xxx'
            '</NAMESPACE>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "NAMESPACE with invalid extra attribute",
        dict(
            xml_str=''
            '<NAMESPACE NAME="a" XXX="bla">'
            '</NAMESPACE>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "NAMESPACE with missing required attribute NAME",
        dict(
            xml_str=''
            '<NAMESPACE>'
            '</NAMESPACE>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "NAMESPACE with NAME (normal case, short form)",
        dict(
            xml_str=''
            '<NAMESPACE NAME="foo"/>',
            exp_result=u'foo',
        ),
        None, None, True
    ),
    (
        "NAMESPACE with NAME (normal case, long form)",
        dict(
            xml_str=''
            '<NAMESPACE NAME="foo">'
            '</NAMESPACE>',
            exp_result=u'foo',
        ),
        None, None, True
    ),
    (
        "NAMESPACE with NAME using non-ASCII UCS-2 characters",
        dict(
            xml_str=b''
            b'<NAMESPACE NAME="\xC3\xA9"/>',
            exp_result=u'\u00E9',  # LATIN SMALL LETTER E WITH ACUTE
        ),
        None, None, True
    ),
    (
        "NAMESPACE with NAME using non-UCS-2 characters",
        dict(
            xml_str=b''
            b'<NAMESPACE NAME="\xF0\x90\x85\x82"/>',
            exp_result=u'\U00010142',  # GREEK ACROPHONIC ATTIC ONE DRACHMA
        ),
        None, None, True
    ),

    # LOCALNAMESPACEPATH tests
    (
        "LOCALNAMESPACEPATH with invalid extra child element",
        dict(
            xml_str=''
            '<LOCALNAMESPACEPATH>'
            '  <NAMESPACE NAME="a"/>'
            '  <XXX></XXX>'
            '</LOCALNAMESPACEPATH>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "LOCALNAMESPACEPATH with invalid text content",
        dict(
            xml_str=''
            '<LOCALNAMESPACEPATH>'
            '  <NAMESPACE NAME="a"/>'
            '  xxx'
            '</LOCALNAMESPACEPATH>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "LOCALNAMESPACEPATH with invalid extra attribute",
        dict(
            xml_str=''
            '<LOCALNAMESPACEPATH XXX="bla">'
            '</LOCALNAMESPACEPATH>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "LOCALNAMESPACEPATH with no component (empty)",
        dict(
            xml_str=''
            '<LOCALNAMESPACEPATH>'
            '</LOCALNAMESPACEPATH>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "LOCALNAMESPACEPATH with one component",
        dict(
            xml_str=''
            '<LOCALNAMESPACEPATH>'
            '  <NAMESPACE NAME="foo"/>'
            '</LOCALNAMESPACEPATH>',
            exp_result=u'foo',
        ),
        None, None, True
    ),
    (
        "LOCALNAMESPACEPATH with two components",
        dict(
            xml_str=''
            '<LOCALNAMESPACEPATH>'
            '  <NAMESPACE NAME="foo"/>'
            '  <NAMESPACE NAME="bar"/>'
            '</LOCALNAMESPACEPATH>',
            exp_result=u'foo/bar',
        ),
        None, None, True
    ),

    # HOST tests
    (
        "HOST with invalid child element",
        dict(
            xml_str=''
            '<HOST>woot.com<X>/</HOST>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "HOST with invalid attribute",
        dict(
            xml_str=''
            '<HOST X="x">woot.com</HOST>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "HOST (DNS host name without port)",
        dict(
            xml_str=''
            '<HOST>woot.com</HOST>',
            exp_result=u'woot.com',
        ),
        None, None, True
    ),
    (
        "HOST (DNS host name with port)",
        dict(
            xml_str=''
            '<HOST>woot.com:1234</HOST>',
            exp_result=u'woot.com:1234',
        ),
        None, None, True
    ),
    (
        "HOST (short host name without port)",
        dict(
            xml_str=''
            '<HOST>woot</HOST>',
            exp_result=u'woot',
        ),
        None, None, True
    ),
    (
        "HOST (IPv4 address without port)",
        dict(
            xml_str=''
            '<HOST>10.11.12.13</HOST>',
            exp_result=u'10.11.12.13',
        ),
        None, None, True
    ),
    (
        "HOST (IPv4 address with port)",
        dict(
            xml_str=''
            '<HOST>10.11.12.13:1</HOST>',
            exp_result=u'10.11.12.13:1',
        ),
        None, None, True
    ),
    (
        "HOST (IPv6 address without port)",
        dict(
            xml_str=''
            '<HOST>[ff::aa]</HOST>',
            exp_result=u'[ff::aa]',
        ),
        None, None, True
    ),
    (
        "HOST (IPv6 address with port)",
        dict(
            xml_str=''
            '<HOST>[ff::aa]:1234</HOST>',
            exp_result=u'[ff::aa]:1234',
        ),
        None, None, True
    ),

    # NAMESPACEPATH tests
    (
        "NAMESPACEPATH with invalid extra child element",
        dict(
            xml_str=''
            '<NAMESPACEPATH>'
            '  <HOST>woot.com</HOST>'
            '  <LOCALNAMESPACEPATH>'
            '    <NAMESPACE NAME="foo"/>'
            '  </LOCALNAMESPACEPATH>'
            '  <XXX></XXX>'
            '</NAMESPACEPATH>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "NAMESPACEPATH with invalid text content",
        dict(
            xml_str=''
            '<NAMESPACEPATH>'
            '  <HOST>woot.com</HOST>'
            '  <LOCALNAMESPACEPATH>'
            '    <NAMESPACE NAME="foo"/>'
            '  </LOCALNAMESPACEPATH>'
            '  xxx'
            '</NAMESPACEPATH>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "NAMESPACEPATH with invalid extra attribute",
        dict(
            xml_str=''
            '<NAMESPACEPATH XXX="bla">'
            '  <HOST>woot.com</HOST>'
            '  <LOCALNAMESPACEPATH>'
            '    <NAMESPACE NAME="foo"/>'
            '  </LOCALNAMESPACEPATH>'
            '</NAMESPACEPATH>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "NAMESPACEPATH with missing child HOST",
        dict(
            xml_str=''
            '<NAMESPACEPATH>'
            '  <LOCALNAMESPACEPATH>'
            '    <NAMESPACE NAME="foo"/>'
            '  </LOCALNAMESPACEPATH>'
            '</NAMESPACEPATH>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "NAMESPACEPATH with missing child LOCALNAMESPACEPATH",
        dict(
            xml_str=''
            '<NAMESPACEPATH>'
            '  <HOST>woot.com</HOST>'
            '</NAMESPACEPATH>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "NAMESPACEPATH with children in incorrect order",
        dict(
            xml_str=''
            '<NAMESPACEPATH>'
            '  <LOCALNAMESPACEPATH>'
            '    <NAMESPACE NAME="foo"/>'
            '  </LOCALNAMESPACEPATH>'
            '  <HOST>woot.com</HOST>'
            '</NAMESPACEPATH>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "NAMESPACEPATH (normal case)",
        dict(
            xml_str=''
            '<NAMESPACEPATH>'
            '  <HOST>woot.com</HOST>'
            '  <LOCALNAMESPACEPATH>'
            '    <NAMESPACE NAME="foo"/>'
            '  </LOCALNAMESPACEPATH>'
            '</NAMESPACEPATH>',
            exp_result=(u'woot.com', u'foo'),
        ),
        None, None, True
    ),

    # CLASSNAME tests
    (
        "CLASSNAME with invalid extra child element",
        dict(
            xml_str=''
            '<CLASSNAME NAME="a">'
            '  <XXX></XXX>'
            '</CLASSNAME>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "CLASSNAME with invalid text content",
        dict(
            xml_str=''
            '<CLASSNAME NAME="a">'
            '  xxx'
            '</CLASSNAME>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "CLASSNAME with invalid extra attribute",
        dict(
            xml_str=''
            '<CLASSNAME NAME="a" XXX="bla">'
            '</CLASSNAME>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "CLASSNAME with missing required attribute NAME",
        dict(
            xml_str=''
            '<CLASSNAME>'
            '</CLASSNAME>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "CLASSNAME with NAME (normal case, short form)",
        dict(
            xml_str=''
            '<CLASSNAME NAME="CIM_Foo"/>',
            exp_result=CIMClassName('CIM_Foo'),
        ),
        None, None, True
    ),
    (
        "CLASSNAME with NAME (normal case, long form)",
        dict(
            xml_str=''
            '<CLASSNAME NAME="CIM_Foo">'
            '</CLASSNAME>',
            exp_result=CIMClassName('CIM_Foo'),
        ),
        None, None, True
    ),
    (
        "CLASSNAME with NAME using non-ASCII UCS-2 characters",
        dict(
            xml_str=b''
            b'<CLASSNAME NAME="CIM_Foo\xC3\xA9"/>',
            exp_result=CIMClassName(u'CIM_Foo\u00E9'),
        ),
        None, None, True
    ),
    (
        "CLASSNAME with NAME using non-UCS-2 characters",
        dict(
            xml_str=b''
            b'<CLASSNAME NAME="CIM_Foo\xF0\x90\x85\x82"/>',
            exp_result=CIMClassName(u'CIM_Foo\U00010142'),
        ),
        None, None, True
    ),

    # LOCALCLASSPATH tests
    (
        "LOCALCLASSPATH with invalid extra child element",
        dict(
            xml_str=''
            '<LOCALCLASSPATH>'
            '  <LOCALNAMESPACEPATH>'
            '    <NAMESPACE NAME="foo"/>'
            '  </LOCALNAMESPACEPATH>'
            '  <CLASSNAME NAME="CIM_Foo"/>'
            '  <XXX></XXX>'
            '</LOCALCLASSPATH>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "LOCALCLASSPATH with invalid text content",
        dict(
            xml_str=''
            '<LOCALCLASSPATH>'
            '  <LOCALNAMESPACEPATH>'
            '    <NAMESPACE NAME="foo"/>'
            '  </LOCALNAMESPACEPATH>'
            '  <CLASSNAME NAME="CIM_Foo"/>'
            '  xxx'
            '</LOCALCLASSPATH>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "LOCALCLASSPATH with invalid extra attribute",
        dict(
            xml_str=''
            '<LOCALCLASSPATH XXX="bla">'
            '  <LOCALNAMESPACEPATH>'
            '    <NAMESPACE NAME="foo"/>'
            '  </LOCALNAMESPACEPATH>'
            '  <CLASSNAME NAME="CIM_Foo"/>'
            '</LOCALCLASSPATH>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "LOCALCLASSPATH with missing child LOCALNAMESPACEPATH",
        dict(
            xml_str=''
            '<LOCALCLASSPATH>'
            '  <CLASSNAME NAME="CIM_Foo"/>'
            '</LOCALCLASSPATH>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "LOCALCLASSPATH with missing child CLASSNAME",
        dict(
            xml_str=''
            '<LOCALCLASSPATH>'
            '  <LOCALNAMESPACEPATH>'
            '    <NAMESPACE NAME="foo"/>'
            '  </LOCALNAMESPACEPATH>'
            '</LOCALCLASSPATH>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "LOCALCLASSPATH with children in incorrect order",
        dict(
            xml_str=''
            '<LOCALCLASSPATH>'
            '  <CLASSNAME NAME="CIM_Foo"/>'
            '  <LOCALNAMESPACEPATH>'
            '    <NAMESPACE NAME="foo"/>'
            '  </LOCALNAMESPACEPATH>'
            '</LOCALCLASSPATH>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "LOCALCLASSPATH (normal case)",
        dict(
            xml_str=''
            '<LOCALCLASSPATH>'
            '  <LOCALNAMESPACEPATH>'
            '    <NAMESPACE NAME="foo"/>'
            '  </LOCALNAMESPACEPATH>'
            '  <CLASSNAME NAME="CIM_Foo"/>'
            '</LOCALCLASSPATH>',
            exp_result=CIMClassName(
                'CIM_Foo',
                namespace='foo',
            ),
        ),
        None, None, True
    ),

    # CLASSPATH tests
    (
        "CLASSPATH with invalid extra child element",
        dict(
            xml_str=''
            '<CLASSPATH>'
            '  <NAMESPACEPATH>'
            '    <HOST>woot.com</HOST>'
            '    <LOCALNAMESPACEPATH>'
            '      <NAMESPACE NAME="foo"/>'
            '    </LOCALNAMESPACEPATH>'
            '  </NAMESPACEPATH>'
            '  <CLASSNAME NAME="CIM_Foo"/>'
            '  <XXX></XXX>'
            '</CLASSPATH>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "CLASSPATH with invalid text content",
        dict(
            xml_str=''
            '<CLASSPATH>'
            '  <NAMESPACEPATH>'
            '    <HOST>woot.com</HOST>'
            '    <LOCALNAMESPACEPATH>'
            '      <NAMESPACE NAME="foo"/>'
            '    </LOCALNAMESPACEPATH>'
            '  </NAMESPACEPATH>'
            '  <CLASSNAME NAME="CIM_Foo"/>'
            '  xxx'
            '</CLASSPATH>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "CLASSPATH with invalid extra attribute",
        dict(
            xml_str=''
            '<CLASSPATH XXX="bla">'
            '  <NAMESPACEPATH>'
            '    <HOST>woot.com</HOST>'
            '    <LOCALNAMESPACEPATH>'
            '      <NAMESPACE NAME="foo"/>'
            '    </LOCALNAMESPACEPATH>'
            '  </NAMESPACEPATH>'
            '  <CLASSNAME NAME="CIM_Foo"/>'
            '</CLASSPATH>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "CLASSPATH with missing child NAMESPACEPATH",
        dict(
            xml_str=''
            '<CLASSPATH>'
            '  <CLASSNAME NAME="CIM_Foo"/>'
            '</CLASSPATH>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "CLASSPATH with missing child CLASSNAME",
        dict(
            xml_str=''
            '<CLASSPATH>'
            '  <NAMESPACEPATH>'
            '    <HOST>woot.com</HOST>'
            '    <LOCALNAMESPACEPATH>'
            '      <NAMESPACE NAME="foo"/>'
            '    </LOCALNAMESPACEPATH>'
            '  </NAMESPACEPATH>'
            '</CLASSPATH>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "CLASSPATH with children in incorrect order",
        dict(
            xml_str=''
            '<CLASSPATH>'
            '  <CLASSNAME NAME="CIM_Foo"/>'
            '  <NAMESPACEPATH>'
            '    <HOST>woot.com</HOST>'
            '    <LOCALNAMESPACEPATH>'
            '      <NAMESPACE NAME="foo"/>'
            '    </LOCALNAMESPACEPATH>'
            '  </NAMESPACEPATH>'
            '</CLASSPATH>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "CLASSPATH (normal case)",
        dict(
            xml_str=''
            '<CLASSPATH>'
            '  <NAMESPACEPATH>'
            '    <HOST>woot.com</HOST>'
            '    <LOCALNAMESPACEPATH>'
            '      <NAMESPACE NAME="foo"/>'
            '    </LOCALNAMESPACEPATH>'
            '  </NAMESPACEPATH>'
            '  <CLASSNAME NAME="CIM_Foo"/>'
            '</CLASSPATH>',
            exp_result=CIMClassName(
                'CIM_Foo',
                namespace='foo',
                host='woot.com',
            ),
        ),
        None, None, True
    ),

    # INSTANCENAME tests
    (
        "INSTANCENAME with invalid extra child element",
        dict(
            xml_str=''
            '<INSTANCENAME CLASSNAME="Foo">'
            '  <XXX></XXX>'
            '</INSTANCENAME>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "INSTANCENAME with invalid text content",
        dict(
            xml_str=''
            '<INSTANCENAME CLASSNAME="Foo">'
            '  xxx'
            '</INSTANCENAME>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "INSTANCENAME with invalid extra attribute",
        dict(
            xml_str=''
            '<INSTANCENAME CLASSNAME="Foo" XXX="bla">'
            '</INSTANCENAME>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "INSTANCENAME with missing required attribute CLASSNAME",
        dict(
            xml_str=''
            '<INSTANCENAME>'
            '</INSTANCENAME>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "INSTANCENAME without keys (= singleton instance of a keyless class)",
        dict(
            xml_str=''
            '<INSTANCENAME CLASSNAME="CIM_Foo">'
            '</INSTANCENAME>',
            exp_result=CIMInstanceName('CIM_Foo'),
        ),
        None, None, True
    ),
    (
        "INSTANCENAME without keys (short form)",
        dict(
            xml_str=''
            '<INSTANCENAME CLASSNAME="CIM_Foo"/>',
            exp_result=CIMInstanceName('CIM_Foo'),
        ),
        None, None, True
    ),
    (
        "INSTANCENAME with KEYBINDING for two string keys",
        dict(
            xml_str=''
            '<INSTANCENAME CLASSNAME="CIM_Foo">'
            '  <KEYBINDING NAME="Name">'
            '    <KEYVALUE VALUETYPE="string">Foo</KEYVALUE>'
            '  </KEYBINDING>'
            '  <KEYBINDING NAME="Chicken">'
            '    <KEYVALUE VALUETYPE="string">Ham</KEYVALUE>'
            '  </KEYBINDING>'
            '</INSTANCENAME>',
            exp_result=CIMInstanceName(
                'CIM_Foo',
                [('Name', 'Foo'), ('Chicken', 'Ham')],
            ),
        ),
        None, None, True
    ),
    (
        "INSTANCENAME with KEYBINDING for various typed keys",
        dict(
            xml_str=''
            '<INSTANCENAME CLASSNAME="CIM_Foo">'
            '  <KEYBINDING NAME="Name">'
            '    <KEYVALUE VALUETYPE="string">Foo</KEYVALUE>'
            '  </KEYBINDING>'
            '  <KEYBINDING NAME="Number">'
            '    <KEYVALUE VALUETYPE="numeric">42</KEYVALUE>'
            '  </KEYBINDING>'
            '  <KEYBINDING NAME="Boolean">'
            '    <KEYVALUE VALUETYPE="boolean">FALSE</KEYVALUE>'
            '  </KEYBINDING>'
            '  <KEYBINDING NAME="Ref">'
            '    <VALUE.REFERENCE>'
            '      <INSTANCENAME CLASSNAME="CIM_Bar"/>'
            '    </VALUE.REFERENCE>'
            '  </KEYBINDING>'
            '</INSTANCENAME>',
            exp_result=CIMInstanceName(
                'CIM_Foo',
                [('Name', 'Foo'),
                 ('Number', 42),
                 ('Boolean', False),
                 ('Ref', CIMInstanceName('CIM_Bar'))],
            ),
        ),
        None, None, True
    ),
    # TODO 1/18 AM: Enable this test once there is support for unnamed keys
    # (
    #     "INSTANCENAME with KEYVALUE for one key (= key value without name)",
    #     dict(
    #         xml_str=''
    #         '<INSTANCENAME CLASSNAME="CIM_Foo">'
    #       '    <KEYVALUE VALUETYPE="string">Foo</KEYVALUE>'
    #         '</INSTANCENAME>',
    #         exp_result=CIMInstanceName(
    #             'CIM_Foo',
    #             [(None, 'Foo')],
    #         ),
    #     ),
    #     None, None, True
    # ),
    (
        "INSTANCENAME with KEYVALUE for two string keys (invalid)",
        dict(
            xml_str=''
            '<INSTANCENAME CLASSNAME="CIM_Foo">'
            '  <KEYVALUE VALUETYPE="string">Foo</KEYVALUE>'
            '  <KEYVALUE VALUETYPE="string">Bar</KEYVALUE>'
            '</INSTANCENAME>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    # TODO 1/18 AM: Enable this test once there is support for unnamed keys
    # (
    #     "INSTANCENAME with VALUE.REFERENCE for one reference key (= key "
    #     "value without name)",
    #     dict(
    #         xml_str=''
    #         '<INSTANCENAME CLASSNAME="CIM_Foo">'
    #         '  <VALUE.REFERENCE>'
    #         '    <INSTANCENAME CLASSNAME="CIM_Bar"/>'
    #         '  </VALUE.REFERENCE>'
    #         '</INSTANCENAME>',
    #         exp_result=CIMInstanceName(
    #             'CIM_Foo',
    #             [(None, CIMInstanceName('CIM_Bar'))],
    #         ),
    #     ),
    #     None, None, True
    # ),
    (
        "INSTANCENAME with VALUE.REFERENCE for two reference keys (invalid)",
        dict(
            xml_str=''
            '<INSTANCENAME CLASSNAME="CIM_Foo">'
            '  <VALUE.REFERENCE>'
            '    <INSTANCENAME CLASSNAME="CIM_Bar"/>'
            '  </VALUE.REFERENCE>'
            '  <VALUE.REFERENCE>'
            '    <INSTANCENAME CLASSNAME="CIM_Baz"/>'
            '  </VALUE.REFERENCE>'
            '</INSTANCENAME>',
            exp_result=None,
        ),
        ParseError, None, True
    ),

    # LOCALINSTANCEPATH tests
    (
        "LOCALINSTANCEPATH with invalid extra child element",
        dict(
            xml_str=''
            '<LOCALINSTANCEPATH>'
            '  <LOCALNAMESPACEPATH>'
            '    <NAMESPACE NAME="foo"/>'
            '  </LOCALNAMESPACEPATH>'
            '  <INSTANCENAME CLASSNAME="CIM_Foo">'
            '    <KEYBINDING NAME="Name">'
            '      <KEYVALUE>Foo</KEYVALUE>'
            '    </KEYBINDING>'
            '  </INSTANCENAME>'
            '  <XXX></XXX>'
            '</LOCALINSTANCEPATH>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "LOCALINSTANCEPATH with invalid text content",
        dict(
            xml_str=''
            '<LOCALINSTANCEPATH>'
            '  <LOCALNAMESPACEPATH>'
            '    <NAMESPACE NAME="foo"/>'
            '  </LOCALNAMESPACEPATH>'
            '  <INSTANCENAME CLASSNAME="CIM_Foo">'
            '    <KEYBINDING NAME="Name">'
            '      <KEYVALUE>Foo</KEYVALUE>'
            '    </KEYBINDING>'
            '  </INSTANCENAME>'
            '  xxx'
            '</LOCALINSTANCEPATH>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "LOCALINSTANCEPATH with invalid extra attribute",
        dict(
            xml_str=''
            '<LOCALINSTANCEPATH XXX="bla">'
            '  <LOCALNAMESPACEPATH>'
            '    <NAMESPACE NAME="foo"/>'
            '  </LOCALNAMESPACEPATH>'
            '  <INSTANCENAME CLASSNAME="CIM_Foo">'
            '    <KEYBINDING NAME="Name">'
            '      <KEYVALUE>Foo</KEYVALUE>'
            '    </KEYBINDING>'
            '  </INSTANCENAME>'
            '</LOCALINSTANCEPATH>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "LOCALINSTANCEPATH with missing child LOCALNAMESPACEPATH",
        dict(
            xml_str=''
            '<LOCALINSTANCEPATH>'
            '  <INSTANCENAME CLASSNAME="CIM_Foo">'
            '    <KEYBINDING NAME="Name">'
            '      <KEYVALUE>Foo</KEYVALUE>'
            '    </KEYBINDING>'
            '  </INSTANCENAME>'
            '</LOCALINSTANCEPATH>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "LOCALINSTANCEPATH with missing child INSTANCENAME",
        dict(
            xml_str=''
            '<LOCALINSTANCEPATH>'
            '  <LOCALNAMESPACEPATH>'
            '    <NAMESPACE NAME="foo"/>'
            '  </LOCALNAMESPACEPATH>'
            '</LOCALINSTANCEPATH>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "LOCALINSTANCEPATH with children in incorrect order",
        dict(
            xml_str=''
            '<LOCALINSTANCEPATH>'
            '  <INSTANCENAME CLASSNAME="CIM_Foo">'
            '    <KEYBINDING NAME="Name">'
            '      <KEYVALUE>Foo</KEYVALUE>'
            '    </KEYBINDING>'
            '  </INSTANCENAME>'
            '  <LOCALNAMESPACEPATH>'
            '    <NAMESPACE NAME="foo"/>'
            '  </LOCALNAMESPACEPATH>'
            '</LOCALINSTANCEPATH>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "LOCALINSTANCEPATH (normal case)",
        dict(
            xml_str=''
            '<LOCALINSTANCEPATH>'
            '  <LOCALNAMESPACEPATH>'
            '    <NAMESPACE NAME="foo"/>'
            '  </LOCALNAMESPACEPATH>'
            '  <INSTANCENAME CLASSNAME="CIM_Foo">'
            '    <KEYBINDING NAME="Name">'
            '      <KEYVALUE>Foo</KEYVALUE>'
            '    </KEYBINDING>'
            '  </INSTANCENAME>'
            '</LOCALINSTANCEPATH>',
            exp_result=CIMInstanceName(
                'CIM_Foo',
                [('Name', 'Foo')],
                namespace='foo',
            ),
        ),
        None, None, True
    ),

    # INSTANCEPATH tests
    (
        "INSTANCEPATH with invalid extra child element",
        dict(
            xml_str=''
            '<INSTANCEPATH>'
            '  <NAMESPACEPATH>'
            '    <HOST>woot.com</HOST>'
            '    <LOCALNAMESPACEPATH>'
            '      <NAMESPACE NAME="foo"/>'
            '    </LOCALNAMESPACEPATH>'
            '  </NAMESPACEPATH>'
            '  <INSTANCENAME CLASSNAME="CIM_Foo">'
            '    <KEYBINDING NAME="Name">'
            '      <KEYVALUE>Foo</KEYVALUE>'
            '    </KEYBINDING>'
            '  </INSTANCENAME>'
            '  <XXX></XXX>'
            '</INSTANCEPATH>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "INSTANCEPATH with invalid text content",
        dict(
            xml_str=''
            '<INSTANCEPATH>'
            '  <NAMESPACEPATH>'
            '    <HOST>woot.com</HOST>'
            '    <LOCALNAMESPACEPATH>'
            '      <NAMESPACE NAME="foo"/>'
            '    </LOCALNAMESPACEPATH>'
            '  </NAMESPACEPATH>'
            '  <INSTANCENAME CLASSNAME="CIM_Foo">'
            '    <KEYBINDING NAME="Name">'
            '      <KEYVALUE>Foo</KEYVALUE>'
            '    </KEYBINDING>'
            '  </INSTANCENAME>'
            '  xxx'
            '</INSTANCEPATH>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "INSTANCEPATH with invalid extra attribute",
        dict(
            xml_str=''
            '<INSTANCEPATH XXX="bla">'
            '  <NAMESPACEPATH>'
            '    <HOST>woot.com</HOST>'
            '    <LOCALNAMESPACEPATH>'
            '      <NAMESPACE NAME="foo"/>'
            '    </LOCALNAMESPACEPATH>'
            '  </NAMESPACEPATH>'
            '  <INSTANCENAME CLASSNAME="CIM_Foo">'
            '    <KEYBINDING NAME="Name">'
            '      <KEYVALUE>Foo</KEYVALUE>'
            '    </KEYBINDING>'
            '  </INSTANCENAME>'
            '</INSTANCEPATH>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "INSTANCEPATH with missing child NAMESPACEPATH",
        dict(
            xml_str=''
            '<INSTANCEPATH>'
            '  <INSTANCENAME CLASSNAME="CIM_Foo">'
            '    <KEYBINDING NAME="Name">'
            '      <KEYVALUE>Foo</KEYVALUE>'
            '    </KEYBINDING>'
            '  </INSTANCENAME>'
            '</INSTANCEPATH>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "INSTANCEPATH with missing child INSTANCENAME",
        dict(
            xml_str=''
            '<INSTANCEPATH>'
            '  <NAMESPACEPATH>'
            '    <HOST>woot.com</HOST>'
            '    <LOCALNAMESPACEPATH>'
            '      <NAMESPACE NAME="foo"/>'
            '    </LOCALNAMESPACEPATH>'
            '  </NAMESPACEPATH>'
            '</INSTANCEPATH>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "INSTANCEPATH with children in incorrect order",
        dict(
            xml_str=''
            '<INSTANCEPATH>'
            '  <INSTANCENAME CLASSNAME="CIM_Foo">'
            '    <KEYBINDING NAME="Name">'
            '      <KEYVALUE>Foo</KEYVALUE>'
            '    </KEYBINDING>'
            '  </INSTANCENAME>'
            '  <NAMESPACEPATH>'
            '    <HOST>woot.com</HOST>'
            '    <LOCALNAMESPACEPATH>'
            '      <NAMESPACE NAME="foo"/>'
            '    </LOCALNAMESPACEPATH>'
            '  </NAMESPACEPATH>'
            '</INSTANCEPATH>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "INSTANCEPATH (normal case)",
        dict(
            xml_str=''
            '<INSTANCEPATH>'
            '  <NAMESPACEPATH>'
            '    <HOST>woot.com</HOST>'
            '    <LOCALNAMESPACEPATH>'
            '      <NAMESPACE NAME="foo"/>'
            '    </LOCALNAMESPACEPATH>'
            '  </NAMESPACEPATH>'
            '  <INSTANCENAME CLASSNAME="CIM_Foo">'
            '    <KEYBINDING NAME="Name">'
            '      <KEYVALUE>Foo</KEYVALUE>'
            '    </KEYBINDING>'
            '  </INSTANCENAME>'
            '</INSTANCEPATH>',
            exp_result=CIMInstanceName(
                'CIM_Foo',
                [('Name', 'Foo')],
                namespace='foo',
                host='woot.com',
            ),
        ),
        None, None, True
    ),

    # OBJECTPATH tests
    (
        "OBJECTPATH with invalid extra child element",
        dict(
            xml_str=''
            '<OBJECTPATH>'
            '  <CLASSPATH>'
            '    <NAMESPACEPATH>'
            '      <HOST>woot.com</HOST>'
            '      <LOCALNAMESPACEPATH>'
            '        <NAMESPACE NAME="foo"/>'
            '      </LOCALNAMESPACEPATH>'
            '    </NAMESPACEPATH>'
            '    <CLASSNAME NAME="CIM_Foo"/>'
            '  </CLASSPATH>'
            '  <XXX></XXX>'
            '</OBJECTPATH>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "OBJECTPATH with invalid text content",
        dict(
            xml_str=''
            '<OBJECTPATH>'
            '  <CLASSPATH>'
            '    <NAMESPACEPATH>'
            '      <HOST>woot.com</HOST>'
            '      <LOCALNAMESPACEPATH>'
            '        <NAMESPACE NAME="foo"/>'
            '      </LOCALNAMESPACEPATH>'
            '    </NAMESPACEPATH>'
            '    <CLASSNAME NAME="CIM_Foo"/>'
            '  </CLASSPATH>'
            '  xxx'
            '</OBJECTPATH>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "OBJECTPATH with invalid extra attribute",
        dict(
            xml_str=''
            '<OBJECTPATH XXX="bla">'
            '  <CLASSPATH>'
            '    <NAMESPACEPATH>'
            '      <HOST>woot.com</HOST>'
            '      <LOCALNAMESPACEPATH>'
            '        <NAMESPACE NAME="foo"/>'
            '      </LOCALNAMESPACEPATH>'
            '    </NAMESPACEPATH>'
            '    <CLASSNAME NAME="CIM_Foo"/>'
            '  </CLASSPATH>'
            '</OBJECTPATH>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "OBJECTPATH with missing child",
        dict(
            xml_str=''
            '<OBJECTPATH>'
            '</OBJECTPATH>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "OBJECTPATH with INSTANCEPATH (normal case)",
        dict(
            xml_str=''
            '<OBJECTPATH>'
            '  <INSTANCEPATH>'
            '    <NAMESPACEPATH>'
            '      <HOST>woot.com</HOST>'
            '      <LOCALNAMESPACEPATH>'
            '        <NAMESPACE NAME="foo"/>'
            '      </LOCALNAMESPACEPATH>'
            '    </NAMESPACEPATH>'
            '    <INSTANCENAME CLASSNAME="CIM_Foo">'
            '      <KEYBINDING NAME="Name">'
            '        <KEYVALUE>Foo</KEYVALUE>'
            '      </KEYBINDING>'
            '    </INSTANCENAME>'
            '  </INSTANCEPATH>'
            '</OBJECTPATH>',
            exp_result=(  # tupletree
                'OBJECTPATH',
                {},
                CIMInstanceName(
                    'CIM_Foo',
                    [('Name', 'Foo')],
                    namespace='foo',
                    host='woot.com',
                ),
            ),
        ),
        None, None, True
    ),
    (
        "OBJECTPATH with CLASSPATH (normal case)",
        dict(
            xml_str=''
            '<OBJECTPATH>'
            '  <CLASSPATH>'
            '    <NAMESPACEPATH>'
            '      <HOST>woot.com</HOST>'
            '      <LOCALNAMESPACEPATH>'
            '        <NAMESPACE NAME="foo"/>'
            '      </LOCALNAMESPACEPATH>'
            '    </NAMESPACEPATH>'
            '    <CLASSNAME NAME="CIM_Foo"/>'
            '  </CLASSPATH>'
            '</OBJECTPATH>',
            exp_result=(  # tupletree
                'OBJECTPATH',
                {},
                CIMClassName(
                    'CIM_Foo',
                    namespace='foo',
                    host='woot.com',
                ),
            ),
        ),
        None, None, True
    ),

    # INSTANCE tests
    (
        "INSTANCE with invalid child element",
        dict(
            xml_str=''
            '<INSTANCE CLASSNAME="CIM_Foo">'
            '  <XXX></XXX>'
            '</INSTANCE>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "INSTANCE with invalid text content",
        dict(
            xml_str=''
            '<INSTANCE CLASSNAME="CIM_Foo">'
            '  xxx'
            '</INSTANCE>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "INSTANCE with invalid extra attribute",
        dict(
            xml_str=''
            '<INSTANCE CLASSNAME="CIM_Foo" XXX="bla">'
            '</INSTANCE>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "INSTANCE with children in incorrect order (tolerated)",
        dict(
            xml_str=''
            '<INSTANCE CLASSNAME="CIM_Foo">'
            '  <PROPERTY NAME="Pstring" TYPE="string"/>'
            '  <QUALIFIER NAME="Association" TYPE="boolean"/>'
            '</INSTANCE>',
            exp_result=CIMInstance(
                'CIM_Foo',
                properties=[
                    CIMProperty('Pstring', type='string', value=None,
                                propagated=False),
                ],
                # TODO 1/18 AM: Enable once instance qualifiers supported
                # qualifiers=[
                #     CIMQualifier('Association', value=None, type='boolean'),
                # ],
            ),
        ),
        None, None, True
    ),
    (
        "INSTANCE without qualifiers or properties",
        dict(
            xml_str=''
            '<INSTANCE CLASSNAME="CIM_Foo">'
            '</INSTANCE>',
            exp_result=CIMInstance('CIM_Foo'),
        ),
        None, None, True
    ),
    (
        "INSTANCE with xml:lang attribute",
        dict(
            xml_str=''
            '<INSTANCE CLASSNAME="CIM_Foo" xml:lang="en_us">'
            '</INSTANCE>',
            exp_result=CIMInstance('CIM_Foo'),
        ),
        None, None, False  # TODO 1/18 AM: Enable once xml:lang supported
    ),
    (
        "INSTANCE with properties",
        dict(
            xml_str=''
            '<INSTANCE CLASSNAME="CIM_Foo">'
            '  <PROPERTY NAME="Pstring" TYPE="string"/>'
            '  <PROPERTY.ARRAY NAME="Puint8array" TYPE="uint8"/>'
            '  <PROPERTY.REFERENCE NAME="Pref"/>'
            '</INSTANCE>',
            exp_result=CIMInstance(
                'CIM_Foo',
                properties=[
                    CIMProperty('Pstring', type='string', value=None,
                                propagated=False),
                    CIMProperty('Puint8array', type='uint8', value=None,
                                is_array=True, propagated=False),
                    CIMProperty('Pref', type='reference', value=None,
                                propagated=False),
                ],
            ),
        ),
        None, None, True
    ),
    (
        "INSTANCE with two QUALIFIER children",
        dict(
            xml_str=''
            '<INSTANCE CLASSNAME="CIM_Foo">'
            '  <QUALIFIER NAME="Association" TYPE="boolean"/>'
            '  <QUALIFIER NAME="Abstract" TYPE="boolean"/>'
            '</INSTANCE>',
            exp_result=CIMInstance(
                'CIM_Foo',
                # TODO 1/18 AM: Enable once instance qualifiers supported
                # qualifiers=[
                #     CIMQualifier('Association', value=None, type='boolean'),
                #     CIMQualifier('Abstract', value=None, type='boolean'),
                # ],
                properties=[],
            ),
        ),
        None, None, True
    ),
    (
        "INSTANCE with one QUALIFIER and one PROPERTY child",
        dict(
            xml_str=''
            '<INSTANCE CLASSNAME="CIM_Foo">'
            '  <QUALIFIER NAME="Association" TYPE="boolean"/>'
            '  <PROPERTY NAME="Pstring" TYPE="string"/>'
            '</INSTANCE>',
            exp_result=CIMInstance(
                'CIM_Foo',
                # TODO 1/18 AM: Enable once instance qualifiers supported
                # qualifiers=[
                #     CIMQualifier('Association', value=None, type='boolean'),
                # ],
                properties=[
                    CIMProperty('Pstring', type='string', value=None,
                                propagated=False),
                ],
            ),
        ),
        None, None, True
    ),
    (
        "INSTANCE with one QUALIFIER and one PROPERTY.ARRAY child",
        dict(
            xml_str=''
            '<INSTANCE CLASSNAME="CIM_Foo">'
            '  <QUALIFIER NAME="Association" TYPE="boolean"/>'
            '  <PROPERTY.ARRAY NAME="Puint8array" TYPE="uint8"/>'
            '</INSTANCE>',
            exp_result=CIMInstance(
                'CIM_Foo',
                # TODO 1/18 AM: Enable once instance qualifiers supported
                # qualifiers=[
                #     CIMQualifier('Association', value=None, type='boolean'),
                # ],
                properties=[
                    CIMProperty('Puint8array', type='uint8', value=None,
                                is_array=True, propagated=False),
                ],
            ),
        ),
        None, None, True
    ),
    (
        "INSTANCE with one QUALIFIER and one PROPERTY.REFERENCE child",
        dict(
            xml_str=''
            '<INSTANCE CLASSNAME="CIM_Foo">'
            '  <QUALIFIER NAME="Association" TYPE="boolean"/>'
            '  <PROPERTY.REFERENCE NAME="Pref"/>'
            '</INSTANCE>',
            exp_result=CIMInstance(
                'CIM_Foo',
                # TODO 1/18 AM: Enable once instance qualifiers supported
                # qualifiers=[
                #     CIMQualifier('Association', value=None, type='boolean'),
                # ],
                properties=[
                    CIMProperty('Pref', type='reference', value=None,
                                propagated=False),
                ],
            ),
        ),
        None, None, True
    ),

    # CLASS tests
    (
        "CLASS with invalid child element",
        dict(
            xml_str=''
            '<CLASS NAME="CIM_Foo">'
            '  <XXX></XXX>'
            '</CLASS>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "CLASS with invalid text content",
        dict(
            xml_str=''
            '<CLASS NAME="CIM_Foo">'
            '  xxx'
            '</CLASS>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "CLASS with invalid extra attribute",
        dict(
            xml_str=''
            '<CLASS NAME="CIM_Foo" XXX="bla">'
            '</CLASS>',
            exp_result=None,
        ),
        ParseError, None, True
    ),
    (
        "CLASS without qualifiers, properties or methods",
        dict(
            xml_str=''
            '<CLASS NAME="CIM_Foo">'
            '</CLASS>',
            exp_result=CIMClass('CIM_Foo'),
        ),
        None, None, True
    ),
    (
        "CLASS with superclass",
        dict(
            xml_str=''
            '<CLASS NAME="CIM_Foo" SUPERCLASS="CIM_Bar">'
            '</CLASS>',
            exp_result=CIMClass('CIM_Foo', superclass='CIM_Bar'),
        ),
        None, None, True
    ),
    (
        "CLASS with qualifiers and properties",
        dict(
            xml_str=''
            '<CLASS NAME="CIM_Foo">'
            '  <QUALIFIER NAME="Association" TYPE="boolean"/>'
            '  <QUALIFIER NAME="Abstract" TYPE="boolean"/>'
            '  <PROPERTY NAME="Pstring" TYPE="string"/>'
            '  <PROPERTY.ARRAY NAME="Puint8array" TYPE="uint8"/>'
            '  <PROPERTY.REFERENCE NAME="Pref"/>'
            '</CLASS>',
            exp_result=CIMClass(
                'CIM_Foo',
                qualifiers=[
                    CIMQualifier('Association', value=None, type='boolean'),
                    CIMQualifier('Abstract', value=None, type='boolean'),
                ],
                properties=[
                    CIMProperty('Pstring', type='string', value=None,
                                propagated=False),
                    CIMProperty('Puint8array', type='uint8', value=None,
                                is_array=True, propagated=False),
                    CIMProperty('Pref', type='reference', value=None,
                                propagated=False),
                ],
            ),
        ),
        None, None, True
    ),
    (
        "CLASS with qualifiers and methods",
        dict(
            xml_str=''
            '<CLASS NAME="CIM_Foo">'
            '  <QUALIFIER NAME="Association" TYPE="boolean"/>'
            '  <QUALIFIER NAME="Abstract" TYPE="boolean"/>'
            '  <METHOD NAME="Muint32" TYPE="uint32"/>'
            '  <METHOD NAME="Mstring" TYPE="string"/>'
            '</CLASS>',
            exp_result=CIMClass(
                'CIM_Foo',
                qualifiers=[
                    CIMQualifier('Association', value=None, type='boolean'),
                    CIMQualifier('Abstract', value=None, type='boolean'),
                ],
                methods=[
                    CIMMethod('Muint32', return_type='uint32',
                              propagated=False),
                    CIMMethod('Mstring', return_type='string',
                              propagated=False),
                ],
            ),
        ),
        None, None, True
    ),
    (
        "CLASS with qualifiers, properties and methods",
        dict(
            xml_str=''
            '<CLASS NAME="CIM_Foo">'
            '  <QUALIFIER NAME="Association" TYPE="boolean"/>'
            '  <QUALIFIER NAME="Abstract" TYPE="boolean"/>'
            '  <PROPERTY NAME="Pstring" TYPE="string"/>'
            '  <PROPERTY.ARRAY NAME="Puint8array" TYPE="uint8"/>'
            '  <PROPERTY.REFERENCE NAME="Pref"/>'
            '  <METHOD NAME="Muint32" TYPE="uint32"/>'
            '  <METHOD NAME="Mstring" TYPE="string"/>'
            '</CLASS>',
            exp_result=CIMClass(
                'CIM_Foo',
                qualifiers=[
                    CIMQualifier('Association', value=None, type='boolean'),
                    CIMQualifier('Abstract', value=None, type='boolean'),
                ],
                properties=[
                    CIMProperty('Pstring', type='string', value=None,
                                propagated=False),
                    CIMProperty('Puint8array', type='uint8', value=None,
                                is_array=True, propagated=False),
                    CIMProperty('Pref', type='reference', value=None,
                                propagated=False),
                ],
                methods=[
                    CIMMethod('Muint32', return_type='uint32',
                              propagated=False),
                    CIMMethod('Mstring', return_type='string',
                              propagated=False),
                ],
            ),
        ),
        None, None, True
    ),

    # TODO (EXTEND): PROPERTY tests
    (
        "PROPERTY with string typed value",
        dict(
            xml_str=''
            '<PROPERTY NAME="Spotty" TYPE="string">'
            '  <VALUE>Foot</VALUE>'
            '</PROPERTY>',
            exp_result=CIMProperty('Spotty', 'Foot', propagated=False),
        ),
        None, None, True
    ),
    (
        "PROPERTY with uint16 typed value",
        dict(
            xml_str=''
            '<PROPERTY NAME="Age" TYPE="uint16">'
            '  <VALUE>32</VALUE>'
            '</PROPERTY>',
            exp_result=CIMProperty('Age', Uint16(32), propagated=False),
        ),
        None, None, True
    ),
    (
        "PROPERTY with empty string typed value",
        dict(
            xml_str=''
            '<PROPERTY NAME="Foo" TYPE="string">'
            '  <VALUE></VALUE>'
            '</PROPERTY>',
            exp_result=CIMProperty('Foo', '', type='string', propagated=False),
        ),
        None, None, True
    ),
    (
        "PROPERTY with None string typed value",
        dict(
            xml_str=''
            '<PROPERTY NAME="Foo" TYPE="string"/>',
            exp_result=CIMProperty('Foo', None, type='string',
                                   propagated=False),
        ),
        None, None, True
    ),
    (
        "PROPERTY with qualifier",
        dict(
            xml_str=''
            '<PROPERTY NAME="Age" TYPE="uint16">'
            '  <QUALIFIER NAME="Key" TYPE="boolean">'
            '    <VALUE>TRUE</VALUE>'
            '  </QUALIFIER>'
            '</PROPERTY>',
            exp_result=CIMProperty(
                'Age', None, type='uint16',
                propagated=False,
                qualifiers=[
                    CIMQualifier('Key', True),
                ]
            ),
        ),
        None, None, True
    ),
    (
        "PROPERTY with embedded instance",
        dict(
            xml_str=''
            '<PROPERTY EmbeddedObject="instance" NAME="Foo" TYPE="string">'
            '  <VALUE>'
            '    &lt;INSTANCE CLASSNAME=&quot;Foo_Class&quot;&gt;'
            '      &lt;PROPERTY NAME=&quot;one&quot; TYPE=&quot;uint8&quot;&gt;'
            '        &lt;VALUE&gt;1&lt;/VALUE&gt;'
            '      &lt;/PROPERTY&gt;'
            '      &lt;PROPERTY NAME=&quot;two&quot; TYPE=&quot;uint8&quot;&gt;'
            '        &lt;VALUE&gt;2&lt;/VALUE&gt;'
            '      &lt;/PROPERTY&gt;'
            '    &lt;/INSTANCE&gt;'
            '  </VALUE>'
            '</PROPERTY>',
            exp_result=CIMProperty(
                'Foo',
                CIMInstance(
                    'Foo_Class',
                    properties=[
                        CIMProperty('one', Uint8(1), propagated=False),
                        CIMProperty('two', Uint8(2), propagated=False),
                    ],
                ),
                propagated=False,
            ),
        ),
        None, None, True
    ),

    # TODO (EXTEND): PROPERTY.ARRAY tests
    (
        "PROPERTY.ARRAY with string array typed value",
        dict(
            xml_str=''
            '<PROPERTY.ARRAY NAME="Foo" TYPE="string">'
            '  <VALUE.ARRAY>'
            '    <VALUE>a</VALUE>'
            '    <VALUE>b</VALUE>'
            '    <VALUE>c</VALUE>'
            '  </VALUE.ARRAY>'
            '</PROPERTY.ARRAY>',
            exp_result=CIMProperty(
                'Foo', ['a', 'b', 'c'],
                propagated=False,
            ),
        ),
        None, None, True
    ),
    (
        "PROPERTY.ARRAY with None string array typed value",
        dict(
            xml_str=''
            '<PROPERTY.ARRAY NAME="Foo" TYPE="string"/>',
            exp_result=CIMProperty(
                'Foo', None, type='string', is_array=True,
                propagated=False,
            ),
        ),
        None, None, True
    ),
    (
        "PROPERTY.ARRAY with uint8 array typed value and qualifiers",
        dict(
            xml_str=''
            '<PROPERTY.ARRAY NAME="Foo" TYPE="uint8">'
            '  <QUALIFIER NAME="Key" TYPE="boolean">'
            '    <VALUE>TRUE</VALUE>'
            '  </QUALIFIER>'
            '  <VALUE.ARRAY>'
            '    <VALUE>1</VALUE>'
            '    <VALUE>2</VALUE>'
            '    <VALUE>3</VALUE>'
            '  </VALUE.ARRAY>'
            '</PROPERTY.ARRAY>',
            exp_result=CIMProperty(
                'Foo', [Uint8(x) for x in [1, 2, 3]],
                propagated=False,
                qualifiers=[
                    CIMQualifier('Key', True),
                ]
            ),
        ),
        None, None, True
    ),
    (
        "PROPERTY.ARRAY with embedded instances",
        dict(
            xml_str=''
            '<PROPERTY.ARRAY EmbeddedObject="instance" NAME="Foo" '
            ' TYPE="string">'
            '  <VALUE.ARRAY>'
            '    <VALUE>'
            '      &lt;INSTANCE CLASSNAME=&quot;Foo_Class&quot;&gt;'
            '        &lt;PROPERTY NAME=&quot;one&quot; '
            '         TYPE=&quot;uint8&quot;&gt;'
            '          &lt;VALUE&gt;1&lt;/VALUE&gt;'
            '        &lt;/PROPERTY&gt;'
            '        &lt;PROPERTY NAME=&quot;two&quot; '
            '         TYPE=&quot;uint8&quot;&gt;'
            '          &lt;VALUE&gt;2&lt;/VALUE&gt;'
            '        &lt;/PROPERTY&gt;'
            '      &lt;/INSTANCE&gt;'
            '    </VALUE>'
            '  </VALUE.ARRAY>'
            '</PROPERTY.ARRAY>',
            exp_result=CIMProperty(
                'Foo',
                [
                    CIMInstance(
                        'Foo_Class',
                        properties=[
                            CIMProperty('one', Uint8(1), propagated=False),
                            CIMProperty('two', Uint8(2), propagated=False),
                        ],
                    ),
                ],
                propagated=False,
            ),
        ),
        None, None, True
    ),

    # TODO (EXTEND): PROPERTY.REFERENCE tests
    (
        "PROPERTY.REFERENCE with value None",
        dict(
            xml_str=''
            '<PROPERTY.REFERENCE NAME="Foo"/>',
            exp_result=CIMProperty(
                'Foo', None, type='reference',
                propagated=False,
            ),
        ),
        None, None, True
    ),
    (
        "PROPERTY.REFERENCE with value",
        dict(
            xml_str=''
            '<PROPERTY.REFERENCE NAME="Foo">'
            '  <VALUE.REFERENCE>'
            '    <INSTANCENAME CLASSNAME="CIM_Foo"/>'
            '  </VALUE.REFERENCE>'
            '</PROPERTY.REFERENCE>',
            exp_result=CIMProperty(
                'Foo',
                CIMInstanceName('CIM_Foo'),
                propagated=False,
            ),
        ),
        None, None, True
    ),
    (
        "PROPERTY.REFERENCE with value and qualifiers",
        dict(
            xml_str=''
            '<PROPERTY.REFERENCE NAME="Foo">'
            '  <QUALIFIER NAME="Key" TYPE="boolean">'
            '    <VALUE>TRUE</VALUE>'
            '  </QUALIFIER>'
            '  <VALUE.REFERENCE>'
            '    <INSTANCENAME CLASSNAME="CIM_Foo"/>'
            '  </VALUE.REFERENCE>'
            '</PROPERTY.REFERENCE>',
            exp_result=CIMProperty(
                'Foo',
                CIMInstanceName('CIM_Foo'),
                propagated=False,
                qualifiers=[
                    CIMQualifier('Key', True),
                ]
            ),
        ),
        None, None, True
    ),

    # TODO (EXTEND): PARAMETER tests
    (
        "PARAMETER with string typed value",
        dict(
            xml_str=''
            '<PARAMETER NAME="Param" TYPE="string"/>',
            exp_result=CIMParameter('Param', 'string'),
        ),
        None, None, True
    ),
    (
        "PARAMETER with string typed value and qualifiers",
        dict(
            xml_str=''
            '<PARAMETER NAME="Param" TYPE="string">'
            '  <QUALIFIER NAME="Key" TYPE="boolean">'
            '    <VALUE>TRUE</VALUE>'
            '  </QUALIFIER>'
            '</PARAMETER>',
            exp_result=CIMParameter(
                'Param', 'string',
                qualifiers=[
                    CIMQualifier('Key', True),
                ]
            ),
        ),
        None, None, True
    ),

    # TODO (EXTEND): PARAMETER.REFERENCE tests
    (
        "PARAMETER.REFERENCE without value",
        dict(
            xml_str=''
            '<PARAMETER.REFERENCE NAME="RefParam"/>',
            exp_result=CIMParameter('RefParam', 'reference'),
        ),
        None, None, True
    ),
    (
        "PARAMETER.REFERENCE with reference class",
        dict(
            xml_str=''
            '<PARAMETER.REFERENCE NAME="RefParam" REFERENCECLASS="CIM_Foo"/>',
            exp_result=CIMParameter(
                'RefParam', 'reference', reference_class='CIM_Foo'
            ),
        ),
        None, None, True
    ),
    (
        "PARAMETER.REFERENCE with reference class and qualifiers",
        dict(
            xml_str=''
            '<PARAMETER.REFERENCE NAME="RefParam" REFERENCECLASS="CIM_Foo">'
            '  <QUALIFIER NAME="Key" TYPE="boolean">'
            '    <VALUE>TRUE</VALUE>'
            '  </QUALIFIER>'
            '</PARAMETER.REFERENCE>',
            exp_result=CIMParameter(
                'RefParam', 'reference',
                reference_class='CIM_Foo',
                qualifiers=[
                    CIMQualifier('Key', True),
                ]
            ),
        ),
        None, None, True
    ),

    # TODO (EXTEND): PARAMETER.ARRAY tests
    (
        "PARAMETER.ARRAY string typed",
        dict(
            xml_str=''
            '<PARAMETER.ARRAY NAME="Array" TYPE="string"/>',
            exp_result=CIMParameter('Array', 'string', is_array=True),
        ),
        None, None, True
    ),
    (
        "PARAMETER.ARRAY fixed array",
        dict(
            xml_str=''
            '<PARAMETER.ARRAY ARRAYSIZE="10" NAME="Array" TYPE="string"/>',
            exp_result=CIMParameter(
                'Array', 'string', is_array=True, array_size=10
            ),
        ),
        None, None, True
    ),
    (
        "PARAMETER.ARRAY fixed array with qualifiers",
        dict(
            xml_str=''
            '<PARAMETER.ARRAY ARRAYSIZE="10" NAME="Array" TYPE="string">'
            '  <QUALIFIER NAME="Key" TYPE="boolean">'
            '    <VALUE>TRUE</VALUE>'
            '  </QUALIFIER>'
            '</PARAMETER.ARRAY>',
            exp_result=CIMParameter(
                'Array', 'string', is_array=True, array_size=10,
                qualifiers=[
                    CIMQualifier('Key', True),
                ]
            ),
        ),
        None, None, True
    ),

    # TODO (EXTEND): PARAMETER.REFARRAY tests
    (
        "PARAMETER.REFARRAY",
        dict(
            xml_str=''
            '<PARAMETER.REFARRAY NAME="RefArray"/>',
            exp_result=CIMParameter('RefArray', 'reference', is_array=True),
        ),
        None, None, True
    ),
    (
        "PARAMETER.REFARRAY with reference class",
        dict(
            xml_str=''
            '<PARAMETER.REFARRAY NAME="RefArray" '
            ' REFERENCECLASS="CIM_Foo"/>',
            exp_result=CIMParameter(
                'RefArray', 'reference', is_array=True,
                reference_class='CIM_Foo'
            ),
        ),
        None, None, True
    ),
    (
        "PARAMETER.REFARRAY fixed size with reference class",
        dict(
            xml_str=''
            '<PARAMETER.REFARRAY ARRAYSIZE="10" NAME="RefArray" '
            ' REFERENCECLASS="CIM_Foo"/>',
            exp_result=CIMParameter(
                'RefArray', 'reference', is_array=True, array_size=10,
                reference_class='CIM_Foo'
            ),
        ),
        None, None, True
    ),
    (
        "PARAMETER.REFARRAY fixed size with reference class and qualifiers",
        dict(
            xml_str=''
            '<PARAMETER.REFARRAY ARRAYSIZE="10" NAME="RefArray" '
            ' REFERENCECLASS="CIM_Foo">'
            '  <QUALIFIER NAME="Key" TYPE="boolean">'
            '    <VALUE>TRUE</VALUE>'
            '  </QUALIFIER>'
            '</PARAMETER.REFARRAY>',
            exp_result=CIMParameter(
                'RefArray', 'reference', is_array=True, array_size=10,
                reference_class='CIM_Foo',
                qualifiers=[
                    CIMQualifier('Key', True),
                ]
            ),
        ),
        None, None, True
    ),

    # TODO: METHOD tests

    # TODO: SCOPE tests

    # TODO: QUALIFIER tests

    # TODO: QUALIFIER.DECLARATION tests

    # TODO: EMBEDDEDOBJECT tests

    # TODO: IPARAMVALUE tests

    # TODO: PARAMVALUE tests

    # TODO: EXPPARAMVALUE tests

    # TODO: RETURNVALUE tests

    # TODO: IRETURNVALUE tests

    # TODO: IMETHODCALL tests

    # TODO: IMETHODRESPONSE tests

    # TODO: METHODCALL tests

    # TODO: METHODRESPONSE tests

    # TODO: EXPMETHODCALL tests

    # TODO: EXPMETHODRESPONSE tests

    # TODO: MESSAGE tests

    # TODO: SIMPLEREQ tests

    # TODO: SIMPLERSP tests

    # TODO: MULTIREQ tests

    # TODO: MULTIRSP tests

    # TODO: SIMPLEEXPREQ tests

    # TODO: SIMPLEEXPRSP tests

    # TODO: MULTIEXPREQ tests

    # TODO: MULTIEXPRSP tests

]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    testcases_tupleparse_xml)
@pytest_extensions.test_function
def test_tupleparse_xml(
        desc, kwargs, exp_exc_types, exp_warn_types, condition):
    """
    Test tupleparse parsing, based upon a CIM-XML string as input.

    The input CIM-XML string is parsed and the result is compared with an
    expected result.
    """

    xml_str = kwargs['xml_str']  # Byte string or unicode string
    exp_result = kwargs['exp_result']

    # This way to create a tuple tree is also used in _imethodcall() etc.
    tt = tupletree.xml_to_tupletree_sax(xml_str, 'Test-XML')

    # The code to be tested
    result = tupleparse.parse_any(tt)

    assert result == exp_result, "Input CIM-XML:\n%s" % xml_str
