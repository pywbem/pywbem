"""
Test CIM-XML parsing routines in _tupleparse.py.
"""

from __future__ import absolute_import

import pytest
from packaging.version import parse as parse_version

from ..utils.pytest_extensions import simplified_test_function

# pylint: disable=wrong-import-position, wrong-import-order, invalid-name
from ...utils import import_installed
pywbem = import_installed('pywbem')
from pywbem import _tupletree, _tupleparse  # noqa: E402
from pywbem import CIMInstance, CIMInstanceName, CIMClass, CIMClassName, \
    CIMProperty, CIMMethod, CIMParameter, CIMQualifier, \
    CIMQualifierDeclaration, \
    CIMDateTime, Uint8, Sint8, Uint16, Sint16, Uint32, Sint32, Uint64, Sint64, \
    Real32, Real64, XMLParseError, CIMXMLParseError, \
    ToleratedServerIssueWarning, MissingKeybindingsWarning, \
    CIMVersionError, DTDVersionError, ProtocolVersionError, \
    __version__  # noqa: E402
# pylint: enable=wrong-import-position, wrong-import-order, invalid-name

# Tuple with pywbem version info (M, N, P), without any dev version.
# Can be used in testcase conditions for version specific tests.
# Note for dev versions (e.g. '0.15.0.dev12'):
# - Before 0.15.0, dev versions of an upcoming version always showed
#   the next patch version, which was not always the intended next version.
# - Starting with 0.15.0, dev versions of an upcoming version always show the
#   intended next version.
# pylint: disable=invalid-name
version_info = parse_version(__version__).release


def qualifier_default_attrs(**overriding_attrs):
    """
    Return a kwargs dict with the CIM-XML default values for the `propagated`
    and flavor attributes of CIMQualifier, updated by the specified overriding
    values for these attributes.
    """
    attrs = dict(
        propagated=False,
        tosubclass=True,
        overridable=True,
        translatable=False,
        toinstance=False,
    )
    attrs.update(overriding_attrs)
    return attrs


def qualifier_declaration_default_attrs(**overriding_attrs):
    """
    Return a kwargs dict with the CIM-XML default values for the flavor
    attributes of CIMQualifierDeclaration, updated by the specified overriding
    values for these attributes.
    """
    attrs = dict(
        tosubclass=True,
        overridable=True,
        translatable=False,
        toinstance=False,
    )
    attrs.update(overriding_attrs)
    return attrs


# Note: These roundtrip testcases cover only typical situations. The full set
# of possibilities including invalid input is tested in the XMl testcases (see
# TESTCASES_TUPLEPARSE_XML).
TESTCASES_TUPLEPARSE_ROUNDTRIP = [

    # Testcases for roundtrip obj -> cim-xml -> obj

    # Each list item is a testcase tuple with these items:
    # * desc: Short testcase description.
    # * kwargs: Keyword arguments for the test function:
    #   * obj: Input CIM object.
    # * exp_exc_types: Expected exception type(s), or None.
    # * exp_warn_types: Expected warning type(s), or None.
    # * condition: Boolean condition for testcase to run, or 'pdb' for debugger

    # CIMInstanceName tests
    (
        "CIMInstanceName with just classname",
        dict(
            obj=CIMInstanceName('CIM_Foo'),
        ),
        None, MissingKeybindingsWarning, True
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
                keybindings=[
                    ('Name', 'Foo'),
                    ('Number', Uint8(42)),
                    ('Boolean', False),
                    ('Ref', CIMInstanceName('CIM_Bar')),
                ],
            ),
        ),
        None, MissingKeybindingsWarning, True  # for the inner ref
    ),
    (
        "CIMInstanceName with keybindings and namespace",
        dict(
            obj=CIMInstanceName(
                'CIM_Foo',
                keybindings=[('Name', 'Foo')],
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
                keybindings=[('Name', 'Foo')],
                host='woot.com',
                namespace='root/cimv2',
            ),
        ),
        None, None, True
    ),
    (
        "CIMInstanceName with keybinding that is a reference to an instance "
        "with a string key",
        dict(
            obj=CIMInstanceName(
                'CIM_Foo',
                keybindings=[
                    ('Ref', CIMInstanceName(
                        'CIM_Bar',
                        keybindings=[('Name', 'Foo')],
                    )),
                ],
                host='woot.com',
                namespace='root/cimv2',
            ),
        ),
        None, None, True
    ),
    (
        "CIMInstanceName with keybinding that is a reference to an instance "
        "without keys",
        dict(
            obj=CIMInstanceName(
                'CIM_Foo',
                keybindings=[
                    ('Ref', CIMInstanceName(
                        'CIM_Bar',
                        keybindings=[],
                    )),
                ],
                host='woot.com',
                namespace='root/cimv2',
            ),
        ),
        None, MissingKeybindingsWarning, True  # for the inner ref
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
        None, MissingKeybindingsWarning, True
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
                    CIMQualifier(
                        'ASSOCIATION', True,
                        **qualifier_default_attrs(overridable=False)
                    ),
                    CIMQualifier(
                        'Aggregation', True,
                        **qualifier_default_attrs(overridable=False)
                    ),
                    CIMQualifier(
                        'Version', '2.6.0',
                        **qualifier_default_attrs(translatable=True)
                    ),
                    CIMQualifier(
                        'Description',
                        'CIM_CollectionInSystem is an association '
                        'used to establish a parent-child '
                        'relationship between a collection and an '
                        '\'owning\' System such as an AdminDomain or '
                        'ComputerSystem. A single collection should '
                        'not have both a CollectionInOrganization '
                        'and a CollectionInSystem association.',
                        **qualifier_default_attrs(translatable=True)
                    ),
                ],
                properties=[
                    CIMProperty(
                        'Parent', None, type='reference',
                        reference_class='CIM_System',
                        propagated=False,
                        qualifiers=[
                            CIMQualifier(
                                'Key', True,
                                **qualifier_default_attrs(overridable=False)
                            ),
                            CIMQualifier(
                                'Aggregate', True,
                                **qualifier_default_attrs(overridable=False)
                            ),
                            CIMQualifier(
                                'Max', Uint32(1),
                                **qualifier_default_attrs()
                            ),
                        ]
                    ),
                    CIMProperty(
                        'Child', None, type='reference',
                        reference_class='CIM_Collection',
                        propagated=False,
                        qualifiers=[
                            CIMQualifier(
                                'Key', True,
                                **qualifier_default_attrs(overridable=False)
                            ),
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
                    CIMQualifier('Qual', True,
                                 **qualifier_default_attrs()),
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
                    CIMQualifier('Qual', True,
                                 **qualifier_default_attrs()),
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
        None, MissingKeybindingsWarning, True
    ),
    (
        "CIMProperty with reference typed value and qualifiers",
        dict(
            obj=CIMProperty(
                'Foo',
                CIMInstanceName('CIM_Foo'),
                propagated=False,
                qualifiers=[
                    CIMQualifier('Qual', True,
                                 **qualifier_default_attrs()),
                ]
            ),
        ),
        None, MissingKeybindingsWarning, True
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
            obj=CIMParameter('Parm', 'string'),
        ),
        None, None, True
    ),
    (
        "CIMParameter with string typed value and qualifiers",
        dict(
            obj=CIMParameter(
                'Param', 'string',
                qualifiers=[
                    CIMQualifier('Qual', True,
                                 **qualifier_default_attrs()),
                ]
            ),
        ),
        None, None, True
    ),

    # Reference parameters
    (
        "CIMParameter with reference typed value",
        dict(
            obj=CIMParameter('RefParm', 'reference'),
        ),
        None, None, True
    ),
    (
        "CIMParameter with reference typed value and ref class",
        dict(
            obj=CIMParameter(
                'RefParm', 'reference',
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
                'RefParm', 'reference',
                reference_class='CIM_Foo',
                qualifiers=[
                    CIMQualifier('Qual', True,
                                 **qualifier_default_attrs()),
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
                    CIMQualifier('Qual', True,
                                 **qualifier_default_attrs()),
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
                    CIMQualifier('Qual', True,
                                 **qualifier_default_attrs()),
                ]
            ),
        ),
        None, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_TUPLEPARSE_ROUNDTRIP)
@simplified_test_function
def test_tupleparse_roundtrip(testcase, obj):
    """
    Test tupleparse parsing based upon roundtrip between CIM objects and their
    CIM-XML.

    The input CIM object is converted to a CIM-XML string, which is then
    parsed and the resulting CIM object is compared with the original
    object.
    """

    xml_str = obj.tocimxml().toxml()
    tt = _tupletree.xml_to_tupletree_sax(xml_str, 'Test-XML')

    tp = _tupleparse.TupleParser()

    # The code to be tested
    parsed_obj = tp.parse_any(tt)

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None

    assert parsed_obj == obj, "CIM-XML of input obj:\n%s" % xml_str


# Note: These XML testcases cover the full set of possibilities for each
# CIM-XML element, including invalid input.
TESTCASES_TUPLEPARSE_XML = [

    # Testcases for _tupleparse

    # Each list item is a testcase tuple with these items:
    # * desc: Short testcase description.
    # * kwargs: Keyword arguments for the test function:
    #   * xml_str: Input CIM-XML string.
    #   * exp_result: Expected parsing result.
    # * exp_exc_types: Expected exception type(s), or None.
    # * exp_warn_types: Expected warning type(s), or None.
    # * condition: Boolean condition for testcase to run, or 'pdb' for debugger

    # General tests with invalidities
    (
        "Ill-formed XML (missing closing bracket on end element)",
        dict(
            xml_str='<HOST>abc</HOST',
            exp_result=None,
        ),
        XMLParseError, None, True
    ),
    (
        "Ill-formed XML (missing slash on end element)",
        dict(
            xml_str='<HOST>abc<HOST>',
            exp_result=None,
        ),
        XMLParseError, None, True
    ),
    (
        "Ill-formed XML (missing opening bracket on end element)",
        dict(
            xml_str='<HOST>abc/HOST>',
            exp_result=None,
        ),
        XMLParseError, None, True
    ),
    (
        "Ill-formed XML (missing closing bracket on begin element)",
        dict(
            xml_str='<HOSTabc</HOST>',
            exp_result=None,
        ),
        XMLParseError, None, True
    ),
    (
        "Ill-formed XML (missing opening bracket on begin element)",
        dict(
            xml_str='HOST>abc</HOST>',
            exp_result=None,
        ),
        XMLParseError, None, True
    ),
    (
        "Ill-formed XML (non-matching end element)",
        dict(
            xml_str='<HOST>abc</HOST2>',
            exp_result=None,
        ),
        XMLParseError, None, True
    ),
    (
        "Ill-formed XML (no end element)",
        dict(
            xml_str='<HOST>',
            exp_result=None,
        ),
        XMLParseError, None, True
    ),
    (
        "Ill-formed XML (no begin element)",
        dict(
            xml_str='</HOST>',
            exp_result=None,
        ),
        XMLParseError, None, True
    ),
    (
        "Ill-formed XML (missing closing bracket in short form)",
        dict(
            xml_str='<HOST/',
            exp_result=None,
        ),
        XMLParseError, None, True
    ),
    (
        "Ill-formed XML (missing opening bracket in short form)",
        dict(
            xml_str='HOST/>',
            exp_result=None,
        ),
        XMLParseError, None, True
    ),
    (
        "Ill-formed XML (missing =value on attribute)",
        dict(
            xml_str='<NAMESPACE NAME/>',
            exp_result=None,
        ),
        XMLParseError, None, True
    ),
    (
        "Ill-formed XML (missing value on attribute)",
        dict(
            xml_str='<NAMESPACE NAME=/>',
            exp_result=None,
        ),
        XMLParseError, None, True
    ),
    (
        "Ill-formed XML (missing double quotes around value on attribute)",
        dict(
            xml_str='<NAMESPACE NAME=abc/>',
            exp_result=None,
        ),
        XMLParseError, None, True
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
        "Use of empty attribute value",
        dict(
            xml_str='<NAMESPACE NAME=""/>',
            exp_result=u'',
        ),
        None, None, True
    ),
    (
        "Invalid top-level element",
        dict(
            xml_str=''
            '<XXX/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),

    # CIM tests:
    #
    #   <!ELEMENT CIM (MESSAGE | DECLARATION)>
    #   <!ATTLIST CIM
    #       CIMVERSION CDATA #REQUIRED
    #       DTDVERSION CDATA #REQUIRED>
    (
        "CIM with invalid child element",
        dict(
            xml_str=''
            '<CIM CIMVERSION="2.8" DTDVERSION="2.4">'
            '  <DECLARATION>'
            '    <DECLGROUP>'
            '      <QUALIFIER.DECLARATION NAME="Qual" TYPE="string"/>'
            '    </DECLGROUP>'
            '  </DECLARATION>'
            '  <XXX/>'
            '</CIM>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "CIM with invalid attribute",
        dict(
            xml_str=''
            '<CIM CIMVERSION="2.8" DTDVERSION="2.4" XXX="bla">'
            '  <DECLARATION>'
            '    <DECLGROUP>'
            '      <QUALIFIER.DECLARATION NAME="Qual" TYPE="string"/>'
            '    </DECLGROUP>'
            '  </DECLARATION>'
            '</CIM>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "CIM with invalid value for attribute CIMVERSION 'foo'",
        dict(
            xml_str=''
            '<CIM CIMVERSION="foo" DTDVERSION="2.4">'
            '  <DECLARATION>'
            '    <DECLGROUP>'
            '      <QUALIFIER.DECLARATION NAME="Qual" TYPE="string"/>'
            '    </DECLGROUP>'
            '  </DECLARATION>'
            '</CIM>',
            exp_result=None,
        ),
        CIMVersionError, None, True
    ),
    (
        "CIM with invalid value for attribute CIMVERSION '1.0'",
        dict(
            xml_str=''
            '<CIM CIMVERSION="1.0" DTDVERSION="2.4">'
            '  <DECLARATION>'
            '    <DECLGROUP>'
            '      <QUALIFIER.DECLARATION NAME="Qual" TYPE="string"/>'
            '    </DECLGROUP>'
            '  </DECLARATION>'
            '</CIM>',
            exp_result=None,
        ),
        CIMVersionError, None, True
    ),
    (
        "CIM with invalid value for attribute DTDVERSION 'foo'",
        dict(
            xml_str=''
            '<CIM CIMVERSION="2.8" DTDVERSION="foo">'
            '  <DECLARATION>'
            '    <DECLGROUP>'
            '      <QUALIFIER.DECLARATION NAME="Qual" TYPE="string"/>'
            '    </DECLGROUP>'
            '  </DECLARATION>'
            '</CIM>',
            exp_result=None,
        ),
        DTDVersionError, None, True
    ),
    (
        "CIM with invalid value for attribute DTDVERSION '1.0'",
        dict(
            xml_str=''
            '<CIM CIMVERSION="2.8" DTDVERSION="1.0">'
            '  <DECLARATION>'
            '    <DECLGROUP>'
            '      <QUALIFIER.DECLARATION NAME="Qual" TYPE="string"/>'
            '    </DECLGROUP>'
            '  </DECLARATION>'
            '</CIM>',
            exp_result=None,
        ),
        DTDVersionError, None, True
    ),
    (
        "CIM with DECLARATION child element (minimal case)",
        dict(
            xml_str=''
            '<CIM CIMVERSION="2.8" DTDVERSION="2.4">'
            '  <DECLARATION>'
            '    <DECLGROUP>'
            '      <QUALIFIER.DECLARATION NAME="Qual" TYPE="string"/>'
            '    </DECLGROUP>'
            '  </DECLARATION>'
            '</CIM>',
            exp_result=(
                u'CIM',
                {u'CIMVERSION': u'2.8', u'DTDVERSION': u'2.4'},
                (
                    u'DECLARATION',
                    {},
                    (
                        u'DECLGROUP',
                        {},
                        CIMQualifierDeclaration(
                            'Qual', value=None, type='string',
                            **qualifier_declaration_default_attrs())
                    ),
                ),
            ),
        ),
        None, None, True
    ),
    (
        "CIM with MESSAGE child element (minimal case)",
        dict(
            xml_str=''
            '<CIM CIMVERSION="2.8" DTDVERSION="2.4">'
            '  <MESSAGE ID="42" PROTOCOLVERSION="1.4">'
            '    <SIMPLEREQ>'
            '      <IMETHODCALL NAME="M1">'
            '        <LOCALNAMESPACEPATH>'
            '          <NAMESPACE NAME="foo"/>'
            '        </LOCALNAMESPACEPATH>'
            '      </IMETHODCALL>'
            '    </SIMPLEREQ>'
            '  </MESSAGE>'
            '</CIM>',
            exp_result=(
                u'CIM',
                {u'CIMVERSION': u'2.8', u'DTDVERSION': u'2.4'},
                (
                    u'MESSAGE',
                    {u'ID': u'42', u'PROTOCOLVERSION': u'1.4'},
                    (
                        u'SIMPLEREQ',
                        {},
                        (
                            u'IMETHODCALL', {u'NAME': u'M1'}, u'foo', []
                        ),
                    ),
                ),
            ),
        ),
        None, None, True
    ),

    # DECLARATION tests:
    #
    #   <!ELEMENT DECLARATION ( DECLGROUP | DECLGROUP.WITHNAME |
    #                           DECLGROUP.WITHPATH )+>
    #
    # Note: Pywbem only supports the DECLGROUP child, at this point.
    (
        "DECLARATION with invalid child element",
        dict(
            xml_str=''
            '<DECLARATION>'
            '  <DECLGROUP>'
            '    <QUALIFIER.DECLARATION NAME="Qual" TYPE="string"/>'
            '  </DECLGROUP>'
            '  <XXX/>'
            '</DECLARATION>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "DECLARATION with invalid attribute",
        dict(
            xml_str=''
            '<DECLARATION XXX="bla">'
            '  <DECLGROUP>'
            '    <QUALIFIER.DECLARATION NAME="Qual" TYPE="string"/>'
            '  </DECLGROUP>'
            '</DECLARATION>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "DECLARATION with DECLGROUP child element (minimal case)",
        dict(
            xml_str=''
            '<DECLARATION>'
            '  <DECLGROUP>'
            '    <QUALIFIER.DECLARATION NAME="Qual" TYPE="string"/>'
            '  </DECLGROUP>'
            '</DECLARATION>',
            exp_result=(
                u'DECLARATION',
                {},
                (
                    u'DECLGROUP',
                    {},
                    CIMQualifierDeclaration(
                        'Qual', value=None, type='string',
                        **qualifier_declaration_default_attrs())
                ),
            ),
        ),
        None, None, True
    ),

    # DECLGROUP tests:
    #
    #   <!ELEMENT DECLGROUP ( (LOCALNAMESPACEPATH|NAMESPACEPATH)?,
    #                         QUALIFIER.DECLARATION*, VALUE.OBJECT* )>
    #
    # Note: Pywbem only supports the QUALIFIER.DECLARATION and VALUE.OBJECT
    #       children, and with a multiplicity of 1, at this point.
    (
        "DECLGROUP with invalid child element",
        dict(
            xml_str=''
            '<DECLGROUP>'
            '  <QUALIFIER.DECLARATION NAME="Qual" TYPE="string"/>'
            '  <XXX/>'
            '</DECLGROUP>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "DECLGROUP with invalid attribute",
        dict(
            xml_str=''
            '<DECLGROUP XXX="bla">'
            '  <QUALIFIER.DECLARATION NAME="Qual" TYPE="string"/>'
            '</DECLGROUP>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "DECLGROUP with QUALIFIER.DECLARATION child element (minimal case)",
        dict(
            xml_str=''
            '<DECLGROUP>'
            '  <QUALIFIER.DECLARATION NAME="Qual" TYPE="string"/>'
            '</DECLGROUP>',
            exp_result=(
                u'DECLGROUP',
                {},
                CIMQualifierDeclaration(
                    'Qual', value=None, type='string',
                    **qualifier_declaration_default_attrs())
            ),
        ),
        None, None, True
    ),
    (
        "DECLGROUP with VALUE.OBJECT child element (minimal case)",
        dict(
            xml_str=''
            '<DECLGROUP>'
            '  <VALUE.OBJECT>'
            '    <INSTANCE CLASSNAME="CIM_Foo"/>'
            '  </VALUE.OBJECT>'
            '</DECLGROUP>',
            exp_result=(
                u'DECLGROUP',
                {},
                (
                    u'VALUE.OBJECT',
                    {},
                    CIMInstance('CIM_Foo'),
                ),
            ),
        ),
        None, None, True
    ),

    # DECLGROUP.WITHNAME tests: Parsing this element is not implemented
    (
        "DECLGROUP.WITHNAME (not implemented)",
        dict(
            xml_str=''
            '<DECLGROUP.WITHNAME/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),

    # DECLGROUP.WITHPATH tests: Parsing this element is not implemented
    (
        "DECLGROUP.WITHPATH (not implemented)",
        dict(
            xml_str=''
            '<DECLGROUP.WITHPATH/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),

    # KEYVALUE tests:
    #
    #   <!ELEMENT KEYVALUE (#PCDATA)>
    #   <!ATTLIST KEYVALUE
    #       VALUETYPE (string | boolean | numeric) "string"
    #       %CIMType;    #IMPLIED>  # DTD <2.4
    #       %CIMType;    #REQUIRED>  # DTD >=2.4

    # KEYVALUE tests with general invalidities
    (
        "KEYVALUE with invalid child element",
        dict(
            xml_str=''
            '<KEYVALUE>'
            '  <XXX/>'
            '</KEYVALUE>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "KEYVALUE with invalid attribute",
        dict(
            xml_str=''
            '<KEYVALUE XXX="bla">a</KEYVALUE>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "KEYVALUE with invalid value for attribute VALUETYPE",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="bla">a</KEYVALUE>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "KEYVALUE with invalid value for attribute TYPE",
        dict(
            xml_str=''
            '<KEYVALUE TYPE="bla">a</KEYVALUE>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),

    # KEYVALUE tests without VALUETYPE (defaults to string) and without TYPE
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
        "KEYVALUE without VALUETYPE and TYPE='' (empty string)",
        dict(
            xml_str=''
            '<KEYVALUE TYPE=""></KEYVALUE>',
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
        "KEYVALUE without VALUETYPE and TYPE='' (decimal as string)",
        dict(
            xml_str=''
            '<KEYVALUE TYPE="">42</KEYVALUE>',
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
        "KEYVALUE without VALUETYPE and TYPE='' (true as string)",
        dict(
            xml_str=''
            '<KEYVALUE TYPE="">true</KEYVALUE>',
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

    # KEYVALUE tests without VALUETYPE (defaults to string) but with TYPE string
    (
        "KEYVALUE without VALUETYPE and contradicting TYPE uint8",
        dict(
            xml_str=''
            '<KEYVALUE TYPE="uint8">42</KEYVALUE>',
            exp_result=Uint8(42),
        ),
        None, None, True
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

    # KEYVALUE tests without VALUETYPE (defaults to string) but with TYPE char16
    (
        "KEYVALUE without VALUETYPE with TYPE char16 (invalid empty char)",
        dict(
            xml_str=''
            '<KEYVALUE TYPE="char16"></KEYVALUE>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "KEYVALUE without VALUETYPE with TYPE char16 (invalid two chars)",
        dict(
            xml_str=''
            '<KEYVALUE TYPE="char16">ab</KEYVALUE>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
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
        CIMXMLParseError, None, True
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

    # KEYVALUE tests without VALUETYPE (def. to string) but with TYPE datetime
    (
        "KEYVALUE without VALUETYPE with TYPE datetime (empty string)",
        dict(
            xml_str=''
            '<KEYVALUE TYPE="datetime"></KEYVALUE>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "KEYVALUE without VALUETYPE with TYPE datetime (WS char)",
        dict(
            xml_str=''
            '<KEYVALUE TYPE="datetime"> </KEYVALUE>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "KEYVALUE without VALUETYPE with TYPE datetime (ASCII char)",
        dict(
            xml_str=''
            '<KEYVALUE TYPE="datetime">a</KEYVALUE>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "KEYVALUE without VALUETYPE with TYPE datetime (decimal as string)",
        dict(
            xml_str=''
            '<KEYVALUE TYPE="datetime">4</KEYVALUE>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
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
        "KEYVALUE with VALUETYPE string and contradicting TYPE uint8",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="string" TYPE="uint8">42</KEYVALUE>',
            exp_result=Uint8(42),
        ),
        None, None, True
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
        CIMXMLParseError, None, True
    ),
    (
        "KEYVALUE with VALUETYPE string and TYPE char16 (invalid two chars)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="string" TYPE="char16">ab</KEYVALUE>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
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
        CIMXMLParseError, None, True
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
        None, ToleratedServerIssueWarning, True
    ),
    (
        "KEYVALUE with VALUETYPE boolean without TYPE (WS string)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="boolean">  </KEYVALUE>',
            exp_result=None,
        ),
        None, ToleratedServerIssueWarning, True
    ),
    (
        "KEYVALUE with VALUETYPE boolean without TYPE (ASCII string)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="boolean">abc</KEYVALUE>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "KEYVALUE with VALUETYPE boolean without TYPE (1 as string)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="boolean">1</KEYVALUE>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "KEYVALUE with VALUETYPE boolean without TYPE (0 as string)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="boolean">0</KEYVALUE>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
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
        None, ToleratedServerIssueWarning, True
    ),
    (
        "KEYVALUE with VALUETYPE boolean with TYPE boolean (WS string)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="boolean" TYPE="boolean">  </KEYVALUE>',
            exp_result=None,
        ),
        None, ToleratedServerIssueWarning, True
    ),
    (
        "KEYVALUE with VALUETYPE boolean with TYPE boolean (ASCII string)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="boolean" TYPE="boolean">abc</KEYVALUE>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "KEYVALUE with VALUETYPE boolean with TYPE boolean (1 as string)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="boolean" TYPE="boolean">1</KEYVALUE>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "KEYVALUE with VALUETYPE boolean with TYPE boolean (0 as string)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="boolean" TYPE="boolean">0</KEYVALUE>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
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
        CIMXMLParseError, None, True
    ),
    (
        "KEYVALUE with VALUETYPE numeric without TYPE (WS string)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="numeric">  </KEYVALUE>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "KEYVALUE with VALUETYPE numeric without TYPE (ASCII string)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="numeric">abc</KEYVALUE>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
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
        CIMXMLParseError, None, True
    ),
    (
        "KEYVALUE with VALUETYPE numeric and TYPE uint8 and numeric value that "
        "exceeds the data type limit",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="numeric" TYPE="uint8">1234</KEYVALUE>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "KEYVALUE with VALUETYPE numeric and TYPE uint8 (empty string)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="numeric" TYPE="uint8"></KEYVALUE>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "KEYVALUE with VALUETYPE numeric and TYPE sint64 (WS string)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="numeric" TYPE="sint64">  </KEYVALUE>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "KEYVALUE with VALUETYPE numeric and TYPE real32 (ASCII string)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="numeric" TYPE="real32">abc</KEYVALUE>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
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
        CIMXMLParseError, None, True
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
        CIMXMLParseError, None, True
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

    # KEYBINDING tests:
    #
    #   <!ELEMENT KEYBINDING (KEYVALUE | VALUE.REFERENCE)>
    #   <!ATTLIST KEYBINDING
    #       %CIMName;>
    (
        "KEYBINDING with invalid child element",
        dict(
            xml_str=''
            '<KEYBINDING NAME="Foo">'
            '  <KEYVALUE>a</KEYVALUE>'
            '  <XXX/>'
            '</KEYBINDING>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "KEYBINDING with invalid text content",
        dict(
            xml_str=''
            '<KEYBINDING NAME="Foo">'
            '  <KEYVALUE>a</KEYVALUE>'
            '  xxx'
            '</KEYBINDING>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "KEYBINDING with invalid attribute",
        dict(
            xml_str=''
            '<KEYBINDING NAME="Foo" XXX="bla">'
            '  <KEYVALUE>a</KEYVALUE>'
            '</KEYBINDING>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "KEYBINDING with missing required attribute NAME",
        dict(
            xml_str=''
            '<KEYBINDING>'
            '  <KEYVALUE>a</KEYVALUE>'
            '</KEYBINDING>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "KEYBINDING with two KEYVALUE children (invalid)",
        dict(
            xml_str=''
            '<KEYBINDING NAME="Foo">'
            '  <KEYVALUE>a</KEYVALUE>'
            '  <KEYVALUE>a</KEYVALUE>'
            '</KEYBINDING>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "KEYBINDING with NAME using ASCII characters",
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
        "KEYBINDING with NAME using non-ASCII UCS-2 characters",
        dict(
            xml_str=b''
            b'<KEYBINDING NAME="Foo\xC3\xA9">'
            b'  <KEYVALUE>a</KEYVALUE>'
            b'</KEYBINDING>',
            exp_result={u'Foo\u00E9': u'a'},
        ),
        None, None, True
    ),
    (
        "KEYBINDING with NAME using non-UCS-2 characters",
        dict(
            xml_str=b''
            b'<KEYBINDING NAME="Foo\xF0\x90\x85\x82">'
            b'  <KEYVALUE>a</KEYVALUE>'
            b'</KEYBINDING>',
            exp_result={u'Foo\U00010142': u'a'},
        ),
        None, None, True
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
        "KEYBINDING with two VALUE.REFERENCE children (invalid)",
        dict(
            xml_str=''
            '<KEYBINDING NAME="Foo">'
            '  <VALUE.REFERENCE>'
            '    <INSTANCENAME CLASSNAME="CIM_Foo"/>'
            '  </VALUE.REFERENCE>'
            '  <VALUE.REFERENCE>'
            '    <INSTANCENAME CLASSNAME="CIM_Foo"/>'
            '  </VALUE.REFERENCE>'
            '</KEYBINDING>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
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
        None, MissingKeybindingsWarning, True
    ),

    # VALUE tests:
    #
    #   <!ELEMENT VALUE (#PCDATA)>
    (
        "VALUE with invalid child element",
        dict(
            xml_str=''
            '<VALUE>'
            '  <XXX/>'
            '</VALUE>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "VALUE with invalid attribute",
        dict(
            xml_str=''
            '<VALUE XXX="bla"/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "VALUE with ASCII string",
        dict(
            xml_str=''
            '<VALUE>abc</VALUE>',
            exp_result=u'abc',
        ),
        None, None, True
    ),
    (
        "VALUE with ASCII string with WS",
        dict(
            xml_str=''
            '<VALUE> a  b  c </VALUE>',
            exp_result=u' a  b  c ',
        ),
        None, None, True
    ),
    (
        "VALUE with non-ASCII UCS-2 string",
        dict(
            xml_str=b''
            b'<VALUE>\xC3\xA9</VALUE>',
            exp_result=u'\u00E9',  # LATIN SMALL LETTER E WITH ACUTE
        ),
        None, None, True
    ),
    (
        "VALUE with non-UCS-2 string",
        dict(
            xml_str=b''
            b'<VALUE>\xF0\x90\x85\x82</VALUE>',
            exp_result=u'\U00010142',  # GREEK ACROPHONIC ATTIC ONE DRACHMA
        ),
        None, None, True
    ),

    # VALUE.ARRAY tests:
    #
    #   <!ELEMENT VALUE.ARRAY (VALUE | VALUE.NULL)*>
    (
        "VALUE.ARRAY with invalid child element",
        dict(
            xml_str=''
            '<VALUE.ARRAY>'
            '  <XXX/>'
            '</VALUE.ARRAY>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "VALUE.ARRAY with invalid child element before valid VALUE",
        dict(
            xml_str=''
            '<VALUE.ARRAY>'
            '  <XXX/>'
            '  <VALUE>a</VALUE>'
            '</VALUE.ARRAY>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "VALUE.ARRAY with invalid child element after valid VALUE",
        dict(
            xml_str=''
            '<VALUE.ARRAY>'
            '  <VALUE>a</VALUE>'
            '  <XXX/>'
            '</VALUE.ARRAY>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
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
        CIMXMLParseError, None, True
    ),
    (
        "VALUE.ARRAY with invalid attribute",
        dict(
            xml_str=''
            '<VALUE.ARRAY XXX="bla">'
            '  <VALUE>a</VALUE>'
            '</VALUE.ARRAY>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "VALUE.ARRAY that is empty",
        dict(
            xml_str=''
            '<VALUE.ARRAY/>',
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
        None, None, True
    ),
    (
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
        None, None, True
    ),
    (
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
        None, None, True
    ),

    # VALUE.REFERENCE tests:
    #
    #   <!ELEMENT VALUE.REFERENCE (CLASSPATH | LOCALCLASSPATH | CLASSNAME |
    #                              INSTANCEPATH | LOCALINSTANCEPATH |
    #                              INSTANCENAME)>
    (
        "VALUE.REFERENCE with invalid child element",
        dict(
            xml_str=''
            '<VALUE.REFERENCE>'
            '  <INSTANCENAME CLASSNAME="CIM_Foo"/>'
            '  <XXX/>'
            '</VALUE.REFERENCE>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "VALUE.REFERENCE with invalid text content",
        dict(
            xml_str=''
            '<VALUE.REFERENCE>'
            '  <INSTANCENAME CLASSNAME="CIM_Foo"/>'
            '  xxx'
            '</VALUE.REFERENCE>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "VALUE.REFERENCE with invalid attribute",
        dict(
            xml_str=''
            '<VALUE.REFERENCE XXX="bla">'
            '  <INSTANCENAME CLASSNAME="CIM_Foo"/>'
            '</VALUE.REFERENCE>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "VALUE.REFERENCE with missing child element",
        dict(
            xml_str=''
            '<VALUE.REFERENCE/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "VALUE.REFERENCE with two INSTANCENAME children (invalid)",
        dict(
            xml_str=''
            '<VALUE.REFERENCE>'
            '  <INSTANCENAME CLASSNAME="CIM_Foo"/>'
            '  <INSTANCENAME CLASSNAME="CIM_Foo"/>'
            '</VALUE.REFERENCE>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "VALUE.REFERENCE with ref value that is a INSTANCENAME",
        dict(
            xml_str=''
            '<VALUE.REFERENCE>'
            '  <INSTANCENAME CLASSNAME="CIM_Foo"/>'
            '</VALUE.REFERENCE>',
            exp_result=CIMInstanceName('CIM_Foo'),
        ),
        None, MissingKeybindingsWarning, True
    ),
    (
        "VALUE.REFERENCE with two LOCALINSTANCEPATH children (invalid)",
        dict(
            xml_str=''
            '<VALUE.REFERENCE>'
            '  <LOCALINSTANCEPATH>'
            '    <LOCALNAMESPACEPATH>'
            '      <NAMESPACE NAME="foo"/>'
            '    </LOCALNAMESPACEPATH>'
            '    <INSTANCENAME CLASSNAME="CIM_Foo"/>'
            '  </LOCALINSTANCEPATH>'
            '  <LOCALINSTANCEPATH>'
            '    <LOCALNAMESPACEPATH>'
            '      <NAMESPACE NAME="foo"/>'
            '    </LOCALNAMESPACEPATH>'
            '    <INSTANCENAME CLASSNAME="CIM_Foo"/>'
            '  </LOCALINSTANCEPATH>'
            '</VALUE.REFERENCE>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "VALUE.REFERENCE with ref value that is a LOCALINSTANCEPATH",
        dict(
            xml_str=''
            '<VALUE.REFERENCE>'
            '  <LOCALINSTANCEPATH>'
            '    <LOCALNAMESPACEPATH>'
            '      <NAMESPACE NAME="foo"/>'
            '    </LOCALNAMESPACEPATH>'
            '    <INSTANCENAME CLASSNAME="CIM_Foo"/>'
            '  </LOCALINSTANCEPATH>'
            '</VALUE.REFERENCE>',
            exp_result=CIMInstanceName('CIM_Foo', namespace='foo'),
        ),
        None, MissingKeybindingsWarning, True
    ),
    (
        "VALUE.REFERENCE with two INSTANCEPATH children (invalid)",
        dict(
            xml_str=''
            '<VALUE.REFERENCE>'
            '  <INSTANCEPATH>'
            '    <NAMESPACEPATH>'
            '      <HOST>woot.com</HOST>'
            '      <LOCALNAMESPACEPATH>'
            '        <NAMESPACE NAME="foo"/>'
            '      </LOCALNAMESPACEPATH>'
            '    </NAMESPACEPATH>'
            '    <INSTANCENAME CLASSNAME="CIM_Foo"/>'
            '  </INSTANCEPATH>'
            '  <INSTANCEPATH>'
            '    <NAMESPACEPATH>'
            '      <HOST>woot.com</HOST>'
            '      <LOCALNAMESPACEPATH>'
            '        <NAMESPACE NAME="foo"/>'
            '      </LOCALNAMESPACEPATH>'
            '    </NAMESPACEPATH>'
            '    <INSTANCENAME CLASSNAME="CIM_Foo"/>'
            '  </INSTANCEPATH>'
            '</VALUE.REFERENCE>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "VALUE.REFERENCE with ref value that is a INSTANCEPATH",
        dict(
            xml_str=''
            '<VALUE.REFERENCE>'
            '  <INSTANCEPATH>'
            '    <NAMESPACEPATH>'
            '      <HOST>woot.com</HOST>'
            '      <LOCALNAMESPACEPATH>'
            '        <NAMESPACE NAME="foo"/>'
            '      </LOCALNAMESPACEPATH>'
            '    </NAMESPACEPATH>'
            '    <INSTANCENAME CLASSNAME="CIM_Foo"/>'
            '  </INSTANCEPATH>'
            '</VALUE.REFERENCE>',
            exp_result=CIMInstanceName(
                'CIM_Foo', namespace='foo', host='woot.com',
            ),
        ),
        None, MissingKeybindingsWarning, True
    ),
    (
        "VALUE.REFERENCE with two CLASSNAME children (invalid)",
        dict(
            xml_str=''
            '<VALUE.REFERENCE>'
            '  <CLASSNAME NAME="CIM_Foo"/>'
            '  <CLASSNAME NAME="CIM_Foo"/>'
            '</VALUE.REFERENCE>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "VALUE.REFERENCE with ref value that is a CLASSNAME",
        dict(
            xml_str=''
            '<VALUE.REFERENCE>'
            '  <CLASSNAME NAME="CIM_Foo"/>'
            '</VALUE.REFERENCE>',
            exp_result=CIMClassName('CIM_Foo'),
        ),
        None, None, False
    ),
    (
        "VALUE.REFERENCE with two LOCALCLASSPATH children (invalid)",
        dict(
            xml_str=''
            '<VALUE.REFERENCE>'
            '  <LOCALCLASSPATH>'
            '    <LOCALNAMESPACEPATH>'
            '      <NAMESPACE NAME="foo"/>'
            '    </LOCALNAMESPACEPATH>'
            '    <CLASSNAME NAME="CIM_Foo"/>'
            '  </LOCALCLASSPATH>'
            '  <LOCALCLASSPATH>'
            '    <LOCALNAMESPACEPATH>'
            '      <NAMESPACE NAME="foo"/>'
            '    </LOCALNAMESPACEPATH>'
            '    <CLASSNAME NAME="CIM_Foo"/>'
            '  </LOCALCLASSPATH>'
            '</VALUE.REFERENCE>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "VALUE.REFERENCE with ref value that is a LOCALCLASSPATH",
        dict(
            xml_str=''
            '<VALUE.REFERENCE>'
            '  <LOCALCLASSPATH>'
            '    <LOCALNAMESPACEPATH>'
            '      <NAMESPACE NAME="foo"/>'
            '    </LOCALNAMESPACEPATH>'
            '    <CLASSNAME NAME="CIM_Foo"/>'
            '  </LOCALCLASSPATH>'
            '</VALUE.REFERENCE>',
            exp_result=CIMClassName('CIM_Foo', namespace='foo'),
        ),
        None, None, False
    ),
    (
        "VALUE.REFERENCE with two CLASSPATH children (invalid)",
        dict(
            xml_str=''
            '<VALUE.REFERENCE>'
            '  <CLASSPATH>'
            '    <NAMESPACEPATH>'
            '      <HOST>woot.com</HOST>'
            '      <LOCALNAMESPACEPATH>'
            '        <NAMESPACE NAME="foo"/>'
            '      </LOCALNAMESPACEPATH>'
            '    </NAMESPACEPATH>'
            '    <CLASSNAME NAME="CIM_Foo"/>'
            '  </CLASSPATH>'
            '  <CLASSPATH>'
            '    <NAMESPACEPATH>'
            '      <HOST>woot.com</HOST>'
            '      <LOCALNAMESPACEPATH>'
            '        <NAMESPACE NAME="foo"/>'
            '      </LOCALNAMESPACEPATH>'
            '    </NAMESPACEPATH>'
            '    <CLASSNAME NAME="CIM_Foo"/>'
            '  </CLASSPATH>'
            '</VALUE.REFERENCE>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "VALUE.REFERENCE with ref value that is a CLASSPATH",
        dict(
            xml_str=''
            '<VALUE.REFERENCE>'
            '  <CLASSPATH>'
            '    <NAMESPACEPATH>'
            '      <HOST>woot.com</HOST>'
            '      <LOCALNAMESPACEPATH>'
            '        <NAMESPACE NAME="foo"/>'
            '      </LOCALNAMESPACEPATH>'
            '    </NAMESPACEPATH>'
            '    <CLASSNAME NAME="CIM_Foo"/>'
            '  </CLASSPATH>'
            '</VALUE.REFERENCE>',
            exp_result=CIMClassName(
                'CIM_Foo', namespace='foo', host='woot.com',
            ),
        ),
        None, None, False
    ),

    # VALUE.REFARRAY tests:
    #
    #   <!ELEMENT VALUE.REFARRAY (VALUE.REFERENCE | VALUE.NULL)*>
    (
        "VALUE.REFARRAY with invalid child element",
        dict(
            xml_str=''
            '<VALUE.REFARRAY>'
            '  <VALUE.REFERENCE>'
            '    <INSTANCENAME CLASSNAME="CIM_Foo"/>'
            '  </VALUE.REFERENCE>'
            '  <XXX/>'
            '</VALUE.REFARRAY>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
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
        CIMXMLParseError, None, True
    ),
    (
        "VALUE.REFARRAY with invalid attribute",
        dict(
            xml_str=''
            '<VALUE.REFARRAY XXX="bla">'
            '  <VALUE.REFERENCE>'
            '    <INSTANCENAME CLASSNAME="CIM_Foo"/>'
            '  </VALUE.REFERENCE>'
            '</VALUE.REFARRAY>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "VALUE.REFARRAY that is empty",
        dict(
            xml_str=''
            '<VALUE.REFARRAY/>',
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
        None, MissingKeybindingsWarning, True
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
        None, MissingKeybindingsWarning, True
    ),
    (
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
        None, None, True
    ),
    (
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
        None, MissingKeybindingsWarning, True
    ),
    (
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
        None, MissingKeybindingsWarning, True
    ),

    # VALUE.NULL tests:
    #
    #   <!ELEMENT VALUE.NULL EMPTY>
    (
        "VALUE.NULL with invalid child element",
        dict(
            xml_str=''
            '<VALUE.NULL>'
            '  <XXX/>'
            '</VALUE.NULL>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "VALUE.NULL with invalid text content",
        dict(
            xml_str=''
            '<VALUE.NULL>'
            '  xxx'
            '</VALUE.NULL>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "VALUE.NULL with invalid attribute",
        dict(
            xml_str=''
            '<VALUE.NULL XXX="bla"/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "VALUE.NULL (normal case)",
        dict(
            xml_str=''
            '<VALUE.NULL/>',
            exp_result=None,
        ),
        None, None, True
    ),

    # VALUE.OBJECT tests:
    #
    #   <!ELEMENT VALUE.OBJECT (CLASS | INSTANCE)>
    (
        "VALUE.OBJECT with invalid child element",
        dict(
            xml_str=''
            '<VALUE.OBJECT>'
            '  <XXX/>'
            '</VALUE.OBJECT>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "VALUE.OBJECT with invalid child element after valid INSTANCE",
        dict(
            xml_str=''
            '<VALUE.OBJECT>'
            '  <INSTANCE CLASSNAME="CIM_Foo"/>'
            '  <XXX/>'
            '</VALUE.OBJECT>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
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
        CIMXMLParseError, None, True
    ),
    (
        "VALUE.OBJECT with invalid attribute",
        dict(
            xml_str=''
            '<VALUE.OBJECT XXX="bla">'
            '  <INSTANCE CLASSNAME="CIM_Foo"/>'
            '</VALUE.OBJECT>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "VALUE.OBJECT with missing child",
        dict(
            xml_str=''
            '<VALUE.OBJECT/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "VALUE.OBJECT with two INSTANCE children (invalid)",
        dict(
            xml_str=''
            '<VALUE.OBJECT>'
            '  <INSTANCE CLASSNAME="CIM_Foo"/>'
            '  <INSTANCE CLASSNAME="CIM_Foo"/>'
            '</VALUE.OBJECT>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
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
        "VALUE.OBJECT with two CLASS children (invalid)",
        dict(
            xml_str=''
            '<VALUE.OBJECT>'
            '  <CLASS NAME="CIM_Foo"/>'
            '  <CLASS NAME="CIM_Foo"/>'
            '</VALUE.OBJECT>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
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

    # VALUE.NAMEDINSTANCE tests:
    #
    #   <!ELEMENT VALUE.NAMEDINSTANCE (INSTANCENAME, INSTANCE)>
    (
        "VALUE.NAMEDINSTANCE with invalid child element",
        dict(
            xml_str=''
            '<VALUE.NAMEDINSTANCE>'
            '  <INSTANCENAME CLASSNAME="CIM_Foo">'
            '    <KEYBINDING NAME="Name">'
            '      <KEYVALUE>Foo</KEYVALUE>'
            '    </KEYBINDING>'
            '  </INSTANCENAME>'
            '  <INSTANCE CLASSNAME="CIM_Foo"/>'
            '  <XXX/>'
            '</VALUE.NAMEDINSTANCE>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
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
        CIMXMLParseError, None, True
    ),
    (
        "VALUE.NAMEDINSTANCE with invalid attribute",
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
        CIMXMLParseError, None, True
    ),
    (
        "VALUE.NAMEDINSTANCE with missing children",
        dict(
            xml_str=''
            '<VALUE.NAMEDINSTANCE/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
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
        CIMXMLParseError, None, True
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
        CIMXMLParseError, None, True
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
        CIMXMLParseError, None, True
    ),
    (
        "VALUE.NAMEDINSTANCE with two INSTANCENAME children (invalid)",
        dict(
            xml_str=''
            '<VALUE.NAMEDINSTANCE>'
            '  <INSTANCENAME CLASSNAME="CIM_Foo">'
            '    <KEYBINDING NAME="Name">'
            '      <KEYVALUE>Foo</KEYVALUE>'
            '    </KEYBINDING>'
            '  </INSTANCENAME>'
            '  <INSTANCENAME CLASSNAME="CIM_Foo">'
            '    <KEYBINDING NAME="Name">'
            '      <KEYVALUE>Foo</KEYVALUE>'
            '    </KEYBINDING>'
            '  </INSTANCENAME>'
            '  <INSTANCE CLASSNAME="CIM_Foo"/>'
            '</VALUE.NAMEDINSTANCE>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "VALUE.NAMEDINSTANCE with two INSTANCE children (invalid)",
        dict(
            xml_str=''
            '<VALUE.NAMEDINSTANCE>'
            '  <INSTANCENAME CLASSNAME="CIM_Foo">'
            '    <KEYBINDING NAME="Name">'
            '      <KEYVALUE>Foo</KEYVALUE>'
            '    </KEYBINDING>'
            '  </INSTANCENAME>'
            '  <INSTANCE CLASSNAME="CIM_Foo"/>'
            '  <INSTANCE CLASSNAME="CIM_Foo"/>'
            '</VALUE.NAMEDINSTANCE>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
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

    # VALUE.INSTANCEWITHPATH tests:
    #
    #   <!ELEMENT VALUE.INSTANCEWITHPATH (INSTANCEPATH, INSTANCE)>
    (
        "VALUE.INSTANCEWITHPATH with invalid child element",
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
            '  <XXX/>'
            '</VALUE.INSTANCEWITHPATH>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
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
        CIMXMLParseError, None, True
    ),
    (
        "VALUE.INSTANCEWITHPATH with invalid attribute",
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
        CIMXMLParseError, None, True
    ),
    (
        "VALUE.INSTANCEWITHPATH with missing children",
        dict(
            xml_str=''
            '<VALUE.INSTANCEWITHPATH/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
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
        CIMXMLParseError, None, True
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
        CIMXMLParseError, None, True
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
        CIMXMLParseError, None, True
    ),
    (
        "VALUE.INSTANCEWITHPATH with two INSTANCEPATH children (invalid)",
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
        CIMXMLParseError, None, True
    ),
    (
        "VALUE.INSTANCEWITHPATH with two INSTANCE children (invalid)",
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
            '  <INSTANCE CLASSNAME="CIM_Foo"/>'
            '</VALUE.INSTANCEWITHPATH>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
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

    # VALUE.NAMEDOBJECT tests:
    #
    #   <!ELEMENT VALUE.NAMEDOBJECT (CLASS | (INSTANCENAME, INSTANCE))>
    (
        "VALUE.NAMEDOBJECT with invalid child element",
        dict(
            xml_str=''
            '<VALUE.NAMEDOBJECT>'
            '  <CLASS NAME="CIM_Foo"/>'
            '  <XXX/>'
            '</VALUE.NAMEDOBJECT>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
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
        CIMXMLParseError, None, True
    ),
    (
        "VALUE.NAMEDOBJECT with invalid attribute",
        dict(
            xml_str=''
            '<VALUE.NAMEDOBJECT XXX="bla">'
            '  <CLASS NAME="CIM_Foo"/>'
            '</VALUE.NAMEDOBJECT>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "VALUE.NAMEDOBJECT with missing children",
        dict(
            xml_str=''
            '<VALUE.NAMEDOBJECT/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
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
        CIMXMLParseError, None, True
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
        CIMXMLParseError, None, True
    ),
    (
        "VALUE.NAMEDOBJECT for instance with two INSTANCENAME children "
        "(invalid)",
        dict(
            xml_str=''
            '<VALUE.NAMEDOBJECT>'
            '  <INSTANCENAME CLASSNAME="CIM_Foo">'
            '    <KEYBINDING NAME="Name">'
            '      <KEYVALUE>Foo</KEYVALUE>'
            '    </KEYBINDING>'
            '  </INSTANCENAME>'
            '  <INSTANCENAME CLASSNAME="CIM_Foo">'
            '    <KEYBINDING NAME="Name">'
            '      <KEYVALUE>Foo</KEYVALUE>'
            '    </KEYBINDING>'
            '  </INSTANCENAME>'
            '  <INSTANCE CLASSNAME="CIM_Foo"/>'
            '</VALUE.NAMEDOBJECT>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "VALUE.NAMEDOBJECT for instance with two INSTANCE children "
        "(invalid)",
        dict(
            xml_str=''
            '<VALUE.NAMEDOBJECT>'
            '  <INSTANCENAME CLASSNAME="CIM_Foo">'
            '    <KEYBINDING NAME="Name">'
            '      <KEYVALUE>Foo</KEYVALUE>'
            '    </KEYBINDING>'
            '  </INSTANCENAME>'
            '  <INSTANCE CLASSNAME="CIM_Foo"/>'
            '  <INSTANCE CLASSNAME="CIM_Foo"/>'
            '</VALUE.NAMEDOBJECT>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
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
        "VALUE.NAMEDOBJECT for class with two CLASS children (invalid)",
        dict(
            xml_str=''
            '<VALUE.NAMEDOBJECT>'
            '  <CLASS NAME="CIM_Foo"/>'
            '  <CLASS NAME="CIM_Foo"/>'
            '</VALUE.NAMEDOBJECT>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
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

    # VALUE.OBJECTWITHLOCALPATH tests:
    #
    #   <!ELEMENT VALUE.OBJECTWITHLOCALPATH ((LOCALCLASSPATH, CLASS) |
    #                                       (LOCALINSTANCEPATH, INSTANCE))>
    (
        "VALUE.OBJECTWITHLOCALPATH with invalid child element",
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
            '  <XXX/>'
            '</VALUE.OBJECTWITHLOCALPATH>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
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
        CIMXMLParseError, None, True
    ),
    (
        "VALUE.OBJECTWITHLOCALPATH with invalid attribute",
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
        CIMXMLParseError, None, True
    ),
    (
        "VALUE.OBJECTWITHLOCALPATH with missing children",
        dict(
            xml_str=''
            '<VALUE.OBJECTWITHLOCALPATH/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
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
        CIMXMLParseError, None, True
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
        CIMXMLParseError, None, True
    ),
    (
        "VALUE.OBJECTWITHLOCALPATH for instance with two LOCALINSTANCEPATH "
        "children (invalid)",
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
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "VALUE.OBJECTWITHLOCALPATH for instance with two INSTANCE "
        "children (invalid)",
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
            '  <INSTANCE CLASSNAME="CIM_Foo"/>'
            '</VALUE.OBJECTWITHLOCALPATH>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
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
        "VALUE.OBJECTWITHLOCALPATH for class with two LOCALCLASSPATH children "
        "(invalid)",
        dict(
            xml_str=''
            '<VALUE.OBJECTWITHLOCALPATH>'
            '  <LOCALCLASSPATH>'
            '    <LOCALNAMESPACEPATH>'
            '      <NAMESPACE NAME="foo"/>'
            '    </LOCALNAMESPACEPATH>'
            '    <CLASSNAME NAME="CIM_Foo"/>'
            '  </LOCALCLASSPATH>'
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
        CIMXMLParseError, None, True
    ),
    (
        "VALUE.OBJECTWITHLOCALPATH for class with two CLASS children "
        "(invalid)",
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
            '  <CLASS NAME="CIM_Foo"/>'
            '</VALUE.OBJECTWITHLOCALPATH>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
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
                        path=CIMClassName(
                            'CIM_Foo',
                            namespace='foo',
                        ),
                    ),
                ),
            ),
        ),
        None, None, True
    ),

    # VALUE.OBJECTWITHPATH tests:
    #
    #   <!ELEMENT VALUE.OBJECTWITHPATH ((CLASSPATH, CLASS) |
    #                                   (INSTANCEPATH, INSTANCE))>
    (
        "VALUE.OBJECTWITHPATH with invalid child element",
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
            '  <XXX/>'
            '</VALUE.OBJECTWITHPATH>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
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
        CIMXMLParseError, None, True
    ),
    (
        "VALUE.OBJECTWITHPATH with invalid attribute",
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
        CIMXMLParseError, None, True
    ),
    (
        "VALUE.OBJECTWITHPATH with missing children",
        dict(
            xml_str=''
            '<VALUE.OBJECTWITHPATH/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
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
        CIMXMLParseError, None, True
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
        CIMXMLParseError, None, True
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
        CIMXMLParseError, None, True
    ),
    (
        "VALUE.OBJECTWITHPATH for instance with two INSTANCEPATH children "
        "(invalid)",
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
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "VALUE.OBJECTWITHPATH for instance with two INSTANCE children "
        "(invalid)",
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
            '  <INSTANCE CLASSNAME="CIM_Foo"/>'
            '</VALUE.OBJECTWITHPATH>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
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
        CIMXMLParseError, None, True
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
        CIMXMLParseError, None, True
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
        CIMXMLParseError, None, True
    ),
    (
        "VALUE.OBJECTWITHPATH for class with two CLASSPATH children (invalid)",
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
        CIMXMLParseError, None, True
    ),
    (
        "VALUE.OBJECTWITHPATH for class with two CLASS children (invalid)",
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
            '  <CLASS NAME="CIM_Foo"/>'
            '</VALUE.OBJECTWITHPATH>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
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
                        path=CIMClassName(
                            'CIM_Foo',
                            namespace='foo',
                            host='woot.com',
                        ),
                    ),
                ),
            ),
        ),
        None, None, True
    ),

    # NAMESPACE tests:
    #
    #   <!ELEMENT NAMESPACE EMPTY>
    #   <!ATTLIST NAMESPACE
    #       %CIMName;>
    (
        "NAMESPACE with invalid child element",
        dict(
            xml_str=''
            '<NAMESPACE NAME="a">'
            '  <XXX/>'
            '</NAMESPACE>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
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
        CIMXMLParseError, None, True
    ),
    (
        "NAMESPACE with invalid attribute",
        dict(
            xml_str=''
            '<NAMESPACE NAME="a" XXX="bla"/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "NAMESPACE with missing required attribute NAME",
        dict(
            xml_str=''
            '<NAMESPACE/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "NAMESPACE with NAME using ASCII characters",
        dict(
            xml_str=''
            '<NAMESPACE NAME="foo"/>',
            exp_result=u'foo',
        ),
        None, None, True
    ),
    (
        "NAMESPACE with NAME using non-ASCII UCS-2 characters",
        dict(
            xml_str=b''
            b'<NAMESPACE NAME="foo\xC3\xA9"/>',
            exp_result=u'foo\u00E9',
        ),
        None, None, True
    ),
    (
        "NAMESPACE with NAME using non-UCS-2 characters",
        dict(
            xml_str=b''
            b'<NAMESPACE NAME="foo\xF0\x90\x85\x82"/>',
            exp_result=u'foo\U00010142',
        ),
        None, None, True
    ),

    # LOCALNAMESPACEPATH tests:
    #
    #   <!ELEMENT LOCALNAMESPACEPATH (NAMESPACE+)>
    (
        "LOCALNAMESPACEPATH with invalid child element",
        dict(
            xml_str=''
            '<LOCALNAMESPACEPATH>'
            '  <NAMESPACE NAME="a"/>'
            '  <XXX/>'
            '</LOCALNAMESPACEPATH>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
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
        CIMXMLParseError, None, True
    ),
    (
        "LOCALNAMESPACEPATH with invalid attribute",
        dict(
            xml_str=''
            '<LOCALNAMESPACEPATH XXX="bla"/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "LOCALNAMESPACEPATH with no component (empty)",
        dict(
            xml_str=''
            '<LOCALNAMESPACEPATH/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
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

    # HOST tests:
    #
    #   <!ELEMENT HOST (#PCDATA)>
    (
        "HOST with invalid child element",
        dict(
            xml_str=''
            '<HOST>woot.com<XXX/></HOST>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "HOST with invalid attribute",
        dict(
            xml_str=''
            '<HOST XXX="bla">woot.com</HOST>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
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

    # NAMESPACEPATH tests:
    #
    #   <!ELEMENT NAMESPACEPATH (HOST, LOCALNAMESPACEPATH)>
    (
        "NAMESPACEPATH with invalid child element",
        dict(
            xml_str=''
            '<NAMESPACEPATH>'
            '  <HOST>woot.com</HOST>'
            '  <LOCALNAMESPACEPATH>'
            '    <NAMESPACE NAME="foo"/>'
            '  </LOCALNAMESPACEPATH>'
            '  <XXX/>'
            '</NAMESPACEPATH>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
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
        CIMXMLParseError, None, True
    ),
    (
        "NAMESPACEPATH with invalid attribute",
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
        CIMXMLParseError, None, True
    ),
    (
        "NAMESPACEPATH with missing children",
        dict(
            xml_str=''
            '<NAMESPACEPATH/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
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
        CIMXMLParseError, None, True
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
        CIMXMLParseError, None, True
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
        CIMXMLParseError, None, True
    ),
    (
        "NAMESPACEPATH with two HOST children (invalid)",
        dict(
            xml_str=''
            '<NAMESPACEPATH>'
            '  <HOST>woot.com</HOST>'
            '  <HOST>woot.com</HOST>'
            '  <LOCALNAMESPACEPATH>'
            '    <NAMESPACE NAME="foo"/>'
            '  </LOCALNAMESPACEPATH>'
            '</NAMESPACEPATH>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "NAMESPACEPATH with two LOCALNAMESPACEPATH children (invalid)",
        dict(
            xml_str=''
            '<NAMESPACEPATH>'
            '  <HOST>woot.com</HOST>'
            '  <LOCALNAMESPACEPATH>'
            '    <NAMESPACE NAME="foo"/>'
            '  </LOCALNAMESPACEPATH>'
            '  <LOCALNAMESPACEPATH>'
            '    <NAMESPACE NAME="foo"/>'
            '  </LOCALNAMESPACEPATH>'
            '</NAMESPACEPATH>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
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

    # CLASSNAME tests:
    #
    #   <!ELEMENT CLASSNAME EMPTY>
    #   <!ATTLIST CLASSNAME
    #       %CIMName;>
    (
        "CLASSNAME with invalid child element",
        dict(
            xml_str=''
            '<CLASSNAME NAME="a">'
            '  <XXX/>'
            '</CLASSNAME>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
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
        CIMXMLParseError, None, True
    ),
    (
        "CLASSNAME with invalid attribute",
        dict(
            xml_str=''
            '<CLASSNAME NAME="a" XXX="bla"/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "CLASSNAME with missing required attribute NAME",
        dict(
            xml_str=''
            '<CLASSNAME/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "CLASSNAME with NAME using ASCII characters",
        dict(
            xml_str=''
            '<CLASSNAME NAME="CIM_Foo"/>',
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

    # LOCALCLASSPATH tests:
    #
    #   <!ELEMENT LOCALCLASSPATH (LOCALNAMESPACEPATH, CLASSNAME)>
    (
        "LOCALCLASSPATH with invalid child element",
        dict(
            xml_str=''
            '<LOCALCLASSPATH>'
            '  <LOCALNAMESPACEPATH>'
            '    <NAMESPACE NAME="foo"/>'
            '  </LOCALNAMESPACEPATH>'
            '  <CLASSNAME NAME="CIM_Foo"/>'
            '  <XXX/>'
            '</LOCALCLASSPATH>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
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
        CIMXMLParseError, None, True
    ),
    (
        "LOCALCLASSPATH with invalid attribute",
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
        CIMXMLParseError, None, True
    ),
    (
        "LOCALCLASSPATH with missing children",
        dict(
            xml_str=''
            '<LOCALCLASSPATH/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
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
        CIMXMLParseError, None, True
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
        CIMXMLParseError, None, True
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
        CIMXMLParseError, None, True
    ),
    (
        "LOCALCLASSPATH with two LOCALNAMESPACEPATH children (invalid)",
        dict(
            xml_str=''
            '<LOCALCLASSPATH>'
            '  <LOCALNAMESPACEPATH>'
            '    <NAMESPACE NAME="foo"/>'
            '  </LOCALNAMESPACEPATH>'
            '  <LOCALNAMESPACEPATH>'
            '    <NAMESPACE NAME="foo"/>'
            '  </LOCALNAMESPACEPATH>'
            '  <CLASSNAME NAME="CIM_Foo"/>'
            '</LOCALCLASSPATH>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "LOCALCLASSPATH with two CLASSNAME children (invalid)",
        dict(
            xml_str=''
            '<LOCALCLASSPATH>'
            '  <LOCALNAMESPACEPATH>'
            '    <NAMESPACE NAME="foo"/>'
            '  </LOCALNAMESPACEPATH>'
            '  <CLASSNAME NAME="CIM_Foo"/>'
            '  <CLASSNAME NAME="CIM_Foo"/>'
            '</LOCALCLASSPATH>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
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

    # CLASSPATH tests:
    #
    #   <!ELEMENT CLASSPATH (NAMESPACEPATH, CLASSNAME)>
    (
        "CLASSPATH with invalid child element",
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
            '  <XXX/>'
            '</CLASSPATH>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
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
        CIMXMLParseError, None, True
    ),
    (
        "CLASSPATH with invalid attribute",
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
        CIMXMLParseError, None, True
    ),
    (
        "CLASSPATH with missing children",
        dict(
            xml_str=''
            '<CLASSPATH/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
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
        CIMXMLParseError, None, True
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
        CIMXMLParseError, None, True
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
        CIMXMLParseError, None, True
    ),
    (
        "CLASSPATH with two NAMESPACEPATH children (invalid)",
        dict(
            xml_str=''
            '<CLASSPATH>'
            '  <NAMESPACEPATH>'
            '    <HOST>woot.com</HOST>'
            '    <LOCALNAMESPACEPATH>'
            '      <NAMESPACE NAME="foo"/>'
            '    </LOCALNAMESPACEPATH>'
            '  </NAMESPACEPATH>'
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
        CIMXMLParseError, None, True
    ),
    (
        "CLASSPATH with two CLASSNAME children (invalid)",
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
            '  <CLASSNAME NAME="CIM_Foo"/>'
            '</CLASSPATH>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
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

    # INSTANCENAME tests:
    #
    #   <!ELEMENT INSTANCENAME (KEYBINDING* | KEYVALUE? |
    #                           VALUE.REFERENCE?)>
    #   <!ATTLIST INSTANCENAME
    #       %ClassName;>
    (
        "INSTANCENAME with invalid child element",
        dict(
            xml_str=''
            '<INSTANCENAME CLASSNAME="Foo">'
            '  <XXX/>'
            '</INSTANCENAME>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
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
        CIMXMLParseError, None, True
    ),
    (
        "INSTANCENAME with invalid attribute",
        dict(
            xml_str=''
            '<INSTANCENAME CLASSNAME="Foo" XXX="bla"/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "INSTANCENAME with missing required attribute CLASSNAME",
        dict(
            xml_str=''
            '<INSTANCENAME/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "INSTANCENAME with empty CLASSNAME",
        dict(
            xml_str=b''
            b'<INSTANCENAME CLASSNAME=""/>',
            exp_result=CIMInstanceName(''),
        ),
        None, MissingKeybindingsWarning, True
    ),
    (
        "INSTANCENAME with CLASSNAME using ASCII characters",
        dict(
            xml_str=''
            '<INSTANCENAME CLASSNAME="CIM_Foo"/>',
            exp_result=CIMInstanceName('CIM_Foo'),
        ),
        None, MissingKeybindingsWarning, True
    ),
    (
        "INSTANCENAME with CLASSNAME using non-ASCII UCS-2 characters",
        dict(
            xml_str=b''
            b'<INSTANCENAME CLASSNAME="CIM_Foo\xC3\xA9"/>',
            exp_result=CIMInstanceName(u'CIM_Foo\u00E9'),
        ),
        None, MissingKeybindingsWarning, True
    ),
    (
        "INSTANCENAME with CLASSNAME using non-UCS-2 characters",
        dict(
            xml_str=b''
            b'<INSTANCENAME CLASSNAME="CIM_Foo\xF0\x90\x85\x82"/>',
            exp_result=CIMInstanceName(u'CIM_Foo\U00010142'),
        ),
        None, MissingKeybindingsWarning, True
    ),
    (
        "INSTANCENAME with KEYBINDING for one string key",
        dict(
            xml_str=''
            '<INSTANCENAME CLASSNAME="CIM_Foo">'
            '  <KEYBINDING NAME="Name">'
            '    <KEYVALUE VALUETYPE="string">Foo</KEYVALUE>'
            '  </KEYBINDING>'
            '</INSTANCENAME>',
            exp_result=CIMInstanceName(
                'CIM_Foo',
                [('Name', 'Foo')],
            ),
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
        None, MissingKeybindingsWarning, True
    ),
    (
        "INSTANCENAME with KEYBINDING for INSTANCEPATH",
        dict(
            xml_str=''
            '<INSTANCENAME CLASSNAME="CIM_Foo">'
            '  <KEYBINDING NAME="Ref">'
            '    <VALUE.REFERENCE>'
            '      <INSTANCEPATH>'
            '        <NAMESPACEPATH>'
            '          <HOST>woot.com</HOST>'
            '          <LOCALNAMESPACEPATH>'
            '            <NAMESPACE NAME="foo"/>'
            '          </LOCALNAMESPACEPATH>'
            '        </NAMESPACEPATH>'
            '        <INSTANCENAME CLASSNAME="CIM_Foo">'
            '          <KEYBINDING NAME="Name">'
            '            <KEYVALUE>Foo</KEYVALUE>'
            '          </KEYBINDING>'
            '        </INSTANCENAME>'
            '      </INSTANCEPATH>'
            '    </VALUE.REFERENCE>'
            '  </KEYBINDING>'
            '</INSTANCENAME>',
            exp_result=CIMInstanceName(
                'CIM_Foo',
                keybindings=[
                    ('Ref', CIMInstanceName(
                        'CIM_Foo',
                        keybindings=[('Name', 'Foo')],
                        namespace='foo',
                        host='woot.com',
                    )),
                ],
            ),
        ),
        None, None, True
    ),
    (
        "INSTANCENAME with KEYBINDING for LOCALINSTANCEPATH",
        dict(
            xml_str=''
            '<INSTANCENAME CLASSNAME="CIM_Foo">'
            '  <KEYBINDING NAME="Ref">'
            '    <VALUE.REFERENCE>'
            '      <LOCALINSTANCEPATH>'
            '        <LOCALNAMESPACEPATH>'
            '          <NAMESPACE NAME="foo"/>'
            '        </LOCALNAMESPACEPATH>'
            '        <INSTANCENAME CLASSNAME="CIM_Foo">'
            '          <KEYBINDING NAME="Name">'
            '            <KEYVALUE>Foo</KEYVALUE>'
            '          </KEYBINDING>'
            '        </INSTANCENAME>'
            '      </LOCALINSTANCEPATH>'
            '    </VALUE.REFERENCE>'
            '  </KEYBINDING>'
            '</INSTANCENAME>',
            exp_result=CIMInstanceName(
                'CIM_Foo',
                keybindings=[
                    ('Ref', CIMInstanceName(
                        'CIM_Foo',
                        keybindings=[('Name', 'Foo')],
                        namespace='foo',
                    )),
                ],
            ),
        ),
        None, None, True
    ),
    (
        "INSTANCENAME with KEYBINDING for INSTANCENAME",
        dict(
            xml_str=''
            '<INSTANCENAME CLASSNAME="CIM_Foo">'
            '  <KEYBINDING NAME="Ref">'
            '    <VALUE.REFERENCE>'
            '      <INSTANCENAME CLASSNAME="CIM_Foo">'
            '        <KEYBINDING NAME="Name">'
            '          <KEYVALUE>Foo</KEYVALUE>'
            '        </KEYBINDING>'
            '      </INSTANCENAME>'
            '    </VALUE.REFERENCE>'
            '  </KEYBINDING>'
            '</INSTANCENAME>',
            exp_result=CIMInstanceName(
                'CIM_Foo',
                keybindings=[
                    ('Ref', CIMInstanceName(
                        'CIM_Foo',
                        keybindings=[('Name', 'Foo')],
                    )),
                ],
            ),
        ),
        None, None, True
    ),
    (
        "INSTANCENAME with KEYBINDING for CLASSPATH (invalid)",
        # Note: While VALUE.REFERENCE allows for a CLASSPATH child (e.g. for
        # use in reference-typed method parameters, DSP0004 requires that
        # reference keys reference only instances (section 7.7.5).
        dict(
            xml_str=''
            '<INSTANCENAME CLASSNAME="CIM_Foo">'
            '  <KEYBINDING NAME="Ref">'
            '    <VALUE.REFERENCE>'
            '      <CLASSPATH>'
            '        <NAMESPACEPATH>'
            '          <HOST>woot.com</HOST>'
            '          <LOCALNAMESPACEPATH>'
            '            <NAMESPACE NAME="foo"/>'
            '          </LOCALNAMESPACEPATH>'
            '        </NAMESPACEPATH>'
            '        <CLASSNAME NAME="CIM_Foo"/>'
            '      </CLASSPATH>'
            '    </VALUE.REFERENCE>'
            '  </KEYBINDING>'
            '</INSTANCENAME>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "INSTANCENAME with KEYBINDING for LOCALCLASSPATH (invalid)",
        # Note: While VALUE.REFERENCE allows for a LOCALCLASSPATH child (e.g.
        # for use in reference-typed method parameters, DSP0004 requires that
        # reference keys reference only instances (section 7.7.5).
        dict(
            xml_str=''
            '<INSTANCENAME CLASSNAME="CIM_Foo">'
            '  <KEYBINDING NAME="Ref">'
            '    <VALUE.REFERENCE>'
            '      <LOCALCLASSPATH>'
            '        <LOCALNAMESPACEPATH>'
            '          <NAMESPACE NAME="foo"/>'
            '        </LOCALNAMESPACEPATH>'
            '        <CLASSNAME NAME="CIM_Foo"/>'
            '      </LOCALCLASSPATH>'
            '    </VALUE.REFERENCE>'
            '  </KEYBINDING>'
            '</INSTANCENAME>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "INSTANCENAME with KEYBINDING for CLASSNAME (invalid)",
        # Note: While VALUE.REFERENCE allows for a CLASSNAME child (e.g. for
        # use in reference-typed method parameters, DSP0004 requires that
        # reference keys reference only instances (section 7.7.5).
        dict(
            xml_str=''
            '<INSTANCENAME CLASSNAME="CIM_Foo">'
            '  <KEYBINDING NAME="Ref">'
            '    <VALUE.REFERENCE>'
            '      <CLASSNAME NAME="CIM_Foo"/>'
            '    </VALUE.REFERENCE>'
            '  </KEYBINDING>'
            '</INSTANCENAME>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "INSTANCENAME with KEYVALUE for one key (unnamed key)",
        dict(
            xml_str=''
            '<INSTANCENAME CLASSNAME="CIM_Foo">'
            '  <KEYVALUE VALUETYPE="string">Foo</KEYVALUE>'
            '</INSTANCENAME>',
            exp_result=CIMInstanceName(
                'CIM_Foo',
                [(None, 'Foo')],
            ),
        ),
        None, None, True
    ),
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
        CIMXMLParseError, None, True
    ),
    (
        "INSTANCENAME without child elements (no keys)",
        dict(
            xml_str=''
            '<INSTANCENAME CLASSNAME="CIM_Foo"/>',
            exp_result=CIMInstanceName(
                'CIM_Foo',
            ),
        ),
        None, MissingKeybindingsWarning, True
    ),
    (
        "INSTANCENAME with VALUE.REFERENCE for CLASSNAME (invalid)",
        # Note: While VALUE.REFERENCE allows for a CLASSNAME child (e.g. for
        # use in reference-typed method parameters, DSP0004 requires that
        # reference keys reference only instances (section 7.7.5).
        dict(
            xml_str=''
            '<INSTANCENAME CLASSNAME="CIM_Foo">'
            '  <VALUE.REFERENCE>'
            '    <CLASSNAME NAME="CIM_Foo"/>'
            '  </VALUE.REFERENCE>'
            '</INSTANCENAME>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "INSTANCENAME with VALUE.REFERENCE for one ref. key (unnamed key)",
        dict(
            xml_str=''
            '<INSTANCENAME CLASSNAME="CIM_Foo">'
            '  <VALUE.REFERENCE>'
            '    <INSTANCENAME CLASSNAME="CIM_Bar"/>'
            '  </VALUE.REFERENCE>'
            '</INSTANCENAME>',
            exp_result=CIMInstanceName(
                'CIM_Foo',
                [(None, CIMInstanceName('CIM_Bar'))],
            ),
        ),
        None, MissingKeybindingsWarning, True
    ),
    (
        "INSTANCENAME with VALUE.REFERENCE for one reference key that "
        "references an instance that has one string key",
        dict(
            xml_str=''
            '<INSTANCENAME CLASSNAME="CIM_Foo">'
            '  <VALUE.REFERENCE>'
            '    <INSTANCENAME CLASSNAME="CIM_Bar"/>'
            '  </VALUE.REFERENCE>'
            '</INSTANCENAME>',
            exp_result=CIMInstanceName(
                'CIM_Foo',
                [(None, CIMInstanceName('CIM_Bar'))],
            ),
        ),
        None, MissingKeybindingsWarning, True
    ),
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
        CIMXMLParseError, None, True
    ),

    # LOCALINSTANCEPATH tests:
    #
    #   <!ELEMENT LOCALINSTANCEPATH (LOCALNAMESPACEPATH, INSTANCENAME)>
    (
        "LOCALINSTANCEPATH with invalid child element",
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
            '  <XXX/>'
            '</LOCALINSTANCEPATH>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
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
        CIMXMLParseError, None, True
    ),
    (
        "LOCALINSTANCEPATH with invalid attribute",
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
        CIMXMLParseError, None, True
    ),
    (
        "LOCALINSTANCEPATH with missing children",
        dict(
            xml_str=''
            '<LOCALINSTANCEPATH/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
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
        CIMXMLParseError, None, True
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
        CIMXMLParseError, None, True
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
        CIMXMLParseError, None, True
    ),
    (
        "LOCALINSTANCEPATH with two LOCALNAMESPACEPATH children (invalid)",
        dict(
            xml_str=''
            '<LOCALINSTANCEPATH>'
            '  <LOCALNAMESPACEPATH>'
            '    <NAMESPACE NAME="foo"/>'
            '  </LOCALNAMESPACEPATH>'
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
        CIMXMLParseError, None, True
    ),
    (
        "LOCALINSTANCEPATH with two INSTANCENAME children (invalid)",
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
            '  <INSTANCENAME CLASSNAME="CIM_Foo">'
            '    <KEYBINDING NAME="Name">'
            '      <KEYVALUE>Foo</KEYVALUE>'
            '    </KEYBINDING>'
            '  </INSTANCENAME>'
            '</LOCALINSTANCEPATH>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
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

    # INSTANCEPATH tests:
    #
    #   <!ELEMENT INSTANCEPATH (NAMESPACEPATH, INSTANCENAME)>
    (
        "INSTANCEPATH with invalid child element",
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
            '  <XXX/>'
            '</INSTANCEPATH>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
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
        CIMXMLParseError, None, True
    ),
    (
        "INSTANCEPATH with invalid attribute",
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
        CIMXMLParseError, None, True
    ),
    (
        "INSTANCEPATH with missing children",
        dict(
            xml_str=''
            '<INSTANCEPATH/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
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
        CIMXMLParseError, None, True
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
        CIMXMLParseError, None, True
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
        CIMXMLParseError, None, True
    ),
    (
        "INSTANCEPATH with two NAMESPACEPATH children (invalid)",
        dict(
            xml_str=''
            '<INSTANCEPATH>'
            '  <NAMESPACEPATH>'
            '    <HOST>woot.com</HOST>'
            '    <LOCALNAMESPACEPATH>'
            '      <NAMESPACE NAME="foo"/>'
            '    </LOCALNAMESPACEPATH>'
            '  </NAMESPACEPATH>'
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
        CIMXMLParseError, None, True
    ),
    (
        "INSTANCEPATH with two INSTANCENAME children (invalid)",
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
            '  <INSTANCENAME CLASSNAME="CIM_Foo">'
            '    <KEYBINDING NAME="Name">'
            '      <KEYVALUE>Foo</KEYVALUE>'
            '    </KEYBINDING>'
            '  </INSTANCENAME>'
            '</INSTANCEPATH>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
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

    # OBJECTPATH tests:
    #
    #   <!ELEMENT OBJECTPATH (INSTANCEPATH | CLASSPATH)>
    (
        "OBJECTPATH with invalid child element",
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
            '  <XXX/>'
            '</OBJECTPATH>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
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
        CIMXMLParseError, None, True
    ),
    (
        "OBJECTPATH with invalid attribute",
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
        CIMXMLParseError, None, True
    ),
    (
        "OBJECTPATH with missing child",
        dict(
            xml_str=''
            '<OBJECTPATH/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "OBJECTPATH with two INSTANCEPATH children (invalid)",
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
            exp_result=None,
        ),
        CIMXMLParseError, None, True
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
        "OBJECTPATH with two CLASSPATH children (invalid)",
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
        CIMXMLParseError, None, True
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

    # INSTANCE tests:
    #
    #   <!ELEMENT INSTANCE (QUALIFIER*, (PROPERTY | PROPERTY.ARRAY |
    #                                    PROPERTY.REFERENCE)*)>
    #   <!ATTLIST INSTANCE
    #       %ClassName;
    #       xml:lang NMTOKEN #IMPLIED>
    (
        "INSTANCE with invalid child element",
        dict(
            xml_str=''
            '<INSTANCE CLASSNAME="CIM_Foo">'
            '  <XXX/>'
            '</INSTANCE>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
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
        CIMXMLParseError, None, True
    ),
    (
        "INSTANCE with invalid attribute",
        dict(
            xml_str=''
            '<INSTANCE CLASSNAME="CIM_Foo" XXX="bla"/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
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
                qualifiers=[
                    CIMQualifier('Association', value=None, type='boolean',
                                 **qualifier_default_attrs()),
                ],
            ),
        ),
        None, None, True
    ),
    (
        "INSTANCE with missing required attribute CLASSNAME",
        dict(
            xml_str=''
            '<INSTANCE/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "INSTANCE with CLASSNAME using ASCII characters",
        dict(
            xml_str=''
            '<INSTANCE CLASSNAME="CIM_Foo"/>',
            exp_result=CIMInstance('CIM_Foo'),
        ),
        None, None, True
    ),
    (
        "INSTANCE with CLASSNAME using non-ASCII UCS-2 characters",
        dict(
            xml_str=b''
            b'<INSTANCE CLASSNAME="CIM_Foo\xC3\xA9"/>',
            exp_result=CIMInstance(u'CIM_Foo\u00E9'),
        ),
        None, None, True
    ),
    (
        "INSTANCE with CLASSNAME using non-UCS-2 characters",
        dict(
            xml_str=b''
            b'<INSTANCE CLASSNAME="CIM_Foo\xF0\x90\x85\x82"/>',
            exp_result=CIMInstance(u'CIM_Foo\U00010142'),
        ),
        None, None, True
    ),
    (
        "INSTANCE without qualifiers or properties",
        dict(
            xml_str=''
            '<INSTANCE CLASSNAME="CIM_Foo"/>',
            exp_result=CIMInstance('CIM_Foo'),
        ),
        None, None, True
    ),
    (
        "INSTANCE with xml:lang attribute",
        dict(
            xml_str=''
            '<INSTANCE CLASSNAME="CIM_Foo" xml:lang="en_us"/>',
            exp_result=CIMInstance('CIM_Foo'),
        ),
        None, None, True
    ),
    (
        "INSTANCE with reference property with INSTANCENAME",
        dict(
            xml_str=''
            '<INSTANCE CLASSNAME="CIM_Foo">'
            '  <PROPERTY.REFERENCE NAME="Foo">'
            '    <VALUE.REFERENCE>'
            '      <INSTANCENAME CLASSNAME="CIM_Bar"/>'
            '    </VALUE.REFERENCE>'
            '  </PROPERTY.REFERENCE>'
            '</INSTANCE>',
            exp_result=CIMInstance(
                'CIM_Foo',
                properties=[
                    CIMProperty('Foo', value=CIMInstanceName('CIM_Bar'),
                                propagated=False),
                ],
            ),
        ),
        None, MissingKeybindingsWarning, True
    ),
    (
        "INSTANCE with reference property with CLASSNAME (valid)",
        dict(
            xml_str=''
            '<INSTANCE CLASSNAME="CIM_Foo">'
            '  <PROPERTY.REFERENCE NAME="Foo">'
            '    <VALUE.REFERENCE>'
            '      <CLASSNAME NAME="CIM_Bar"/>'
            '    </VALUE.REFERENCE>'
            '  </PROPERTY.REFERENCE>'
            '</INSTANCE>',
            exp_result=CIMInstance(
                'CIM_Foo',
                properties=[
                    CIMProperty('Foo', type='reference',
                                value=CIMClassName('CIM_Bar'),
                                propagated=False),
                ],
            ),
        ),
        None, None, True
    ),
    (
        "INSTANCE with reference property with INSTANCENAME with keybindings "
        "CLASSNAME (invalid)",
        # Note: While VALUE.REFERENCE allows for a CLASSNAME child (e.g. for
        # use in reference-typed method parameters, DSP0004 requires that
        # reference keys reference only instances (section 7.7.5).
        dict(
            xml_str=''
            '<INSTANCE CLASSNAME="CIM_Foo">'
            '  <PROPERTY.REFERENCE NAME="Foo">'
            '    <VALUE.REFERENCE>'
            '      <INSTANCENAME CLASSNAME="CIM_Bar">'
            '        <KEYBINDING NAME="Ref">'
            '          <VALUE.REFERENCE>'
            '            <CLASSNAME NAME="CIM_Boo"/>'
            '          </VALUE.REFERENCE>'
            '        </KEYBINDING>'
            '      </INSTANCENAME>'
            '    </VALUE.REFERENCE>'
            '  </PROPERTY.REFERENCE>'
            '</INSTANCE>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "INSTANCE with some properties",
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
                qualifiers=[
                    CIMQualifier('Association', value=None, type='boolean',
                                 **qualifier_default_attrs()),
                    CIMQualifier('Abstract', value=None, type='boolean',
                                 **qualifier_default_attrs()),
                ],
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
                qualifiers=[
                    CIMQualifier('Association', value=None, type='boolean',
                                 **qualifier_default_attrs()),
                ],
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
                qualifiers=[
                    CIMQualifier('Association', value=None, type='boolean',
                                 **qualifier_default_attrs()),
                ],
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
                qualifiers=[
                    CIMQualifier('Association', value=None, type='boolean',
                                 **qualifier_default_attrs()),
                ],
                properties=[
                    CIMProperty('Pref', type='reference', value=None,
                                propagated=False),
                ],
            ),
        ),
        None, None, True
    ),

    # CLASS tests:
    #
    #   <!ELEMENT CLASS (QUALIFIER*, (PROPERTY | PROPERTY.ARRAY |
    #                                 PROPERTY.REFERENCE)*, METHOD*)>
    #   <!ATTLIST CLASS
    #       %CIMName;
    #       %SuperClass;>
    (
        "CLASS with invalid child element",
        dict(
            xml_str=''
            '<CLASS NAME="CIM_Foo">'
            '  <XXX/>'
            '</CLASS>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
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
        CIMXMLParseError, None, True
    ),
    (
        "CLASS with invalid attribute",
        dict(
            xml_str=''
            '<CLASS NAME="CIM_Foo" XXX="bla"/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "CLASS with missing required attribute NAME",
        dict(
            xml_str=''
            '<CLASS/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "CLASS with NAME using ASCII characters",
        dict(
            xml_str=''
            '<CLASS NAME="CIM_Foo"/>',
            exp_result=CIMClass('CIM_Foo'),
        ),
        None, None, True
    ),
    (
        "CLASS with NAME using non-ASCII UCS-2 characters",
        dict(
            xml_str=b''
            b'<CLASS NAME="CIM_Foo\xC3\xA9"/>',
            exp_result=CIMClass(u'CIM_Foo\u00E9'),
        ),
        None, None, True
    ),
    (
        "CLASS with NAME using non-UCS-2 characters",
        dict(
            xml_str=b''
            b'<CLASS NAME="CIM_Foo\xF0\x90\x85\x82"/>',
            exp_result=CIMClass(u'CIM_Foo\U00010142'),
        ),
        None, None, True
    ),
    (
        "CLASS without qualifiers, properties or methods",
        dict(
            xml_str=''
            '<CLASS NAME="CIM_Foo"/>',
            exp_result=CIMClass('CIM_Foo'),
        ),
        None, None, True
    ),
    (
        "CLASS with superclass",
        dict(
            xml_str=''
            '<CLASS NAME="CIM_Foo" SUPERCLASS="CIM_Bar"/>',
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
                    CIMQualifier('Association', value=None, type='boolean',
                                 **qualifier_default_attrs()),
                    CIMQualifier('Abstract', value=None, type='boolean',
                                 **qualifier_default_attrs()),
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
                    CIMQualifier('Association', value=None, type='boolean',
                                 **qualifier_default_attrs()),
                    CIMQualifier('Abstract', value=None, type='boolean',
                                 **qualifier_default_attrs()),
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
                    CIMQualifier('Association', value=None, type='boolean',
                                 **qualifier_default_attrs()),
                    CIMQualifier('Abstract', value=None, type='boolean',
                                 **qualifier_default_attrs()),
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

    # PROPERTY tests:
    #
    #   <!ELEMENT PROPERTY (QUALIFIER*, VALUE?)>
    #   <!ATTLIST PROPERTY
    #       %CIMName;
    #       %CIMType;              #REQUIRED
    #       %ClassOrigin;
    #       %Propagated;
    #       %EmbeddedObject;
    #       xml:lang NMTOKEN #IMPLIED>
    (
        "PROPERTY with invalid child element",
        dict(
            xml_str=''
            '<PROPERTY NAME="Foo" TYPE="string">'
            '  <XXX/>'
            '</PROPERTY>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PROPERTY with invalid text content",
        dict(
            xml_str=''
            '<PROPERTY NAME="Foo" TYPE="string">'
            '  xxx'
            '</PROPERTY>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PROPERTY with invalid attribute",
        dict(
            xml_str=''
            '<PROPERTY NAME="Foo" TYPE="string" XXX="bla"/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PROPERTY with children in incorrect order (tolerated)",
        dict(
            xml_str=''
            '<PROPERTY NAME="Foo" TYPE="string">'
            '  <VALUE>abc</VALUE>'
            '  <QUALIFIER NAME="Qual" TYPE="boolean"/>'
            '</PROPERTY>',
            exp_result=CIMProperty(
                'Foo', type='string', value='abc',
                propagated=False,
                qualifiers=[
                    CIMQualifier('Qual', value=None, type='boolean',
                                 **qualifier_default_attrs()),
                ],
            ),
        ),
        None, None, True
    ),
    (
        "PROPERTY with missing required attribute NAME",
        dict(
            xml_str=''
            '<PROPERTY TYPE="string"/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PROPERTY with NAME using ASCII characters",
        dict(
            xml_str=''
            '<PROPERTY NAME="Foo" TYPE="string"/>',
            exp_result=CIMProperty('Foo', value=None, type='string',
                                   propagated=False),
        ),
        None, None, True
    ),
    (
        "PROPERTY with NAME using non-ASCII UCS-2 characters",
        dict(
            xml_str=b''
            b'<PROPERTY NAME="Foo\xC3\xA9" TYPE="string"/>',
            exp_result=CIMProperty(u'Foo\u00E9', value=None, type='string',
                                   propagated=False),
        ),
        None, None, True
    ),
    (
        "PROPERTY with NAME using non-UCS-2 characters",
        dict(
            xml_str=b''
            b'<PROPERTY NAME="Foo\xF0\x90\x85\x82" TYPE="string"/>',
            exp_result=CIMProperty(u'Foo\U00010142', value=None, type='string',
                                   propagated=False),
        ),
        None, None, True
    ),
    (
        "PROPERTY with xml:lang attribute",
        dict(
            xml_str=''
            '<PROPERTY NAME="Foo" TYPE="string" xml:lang="en_us"/>',
            exp_result=CIMProperty('Foo', value=None, type='string',
                                   propagated=False),
        ),
        None, None, True
    ),
    (
        "PROPERTY with CLASSORIGIN and PROPAGATED attributes",
        dict(
            xml_str=''
            '<PROPERTY NAME="Foo" TYPE="string" CLASSORIGIN="CIM_Foo"'
            ' PROPAGATED="true"/>',
            exp_result=CIMProperty('Foo', value=None, type='string',
                                   class_origin='CIM_Foo', propagated=True),
        ),
        None, None, True
    ),
    (
        "PROPERTY with missing required attribute TYPE",
        dict(
            xml_str=''
            '<PROPERTY NAME="Foo"/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PROPERTY with invalid attribute TYPE 'foo'",
        dict(
            xml_str=''
            '<PROPERTY NAME="Foo" TYPE="foo"/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PROPERTY with two VALUE children (invalid)",
        dict(
            xml_str=''
            '<PROPERTY NAME="Foo" TYPE="string">'
            '  <VALUE>abc</VALUE>'
            '  <VALUE>abc</VALUE>'
            '</PROPERTY>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PROPERTY with string typed value that is None",
        dict(
            xml_str=''
            '<PROPERTY NAME="Foo" TYPE="string"/>',
            exp_result=CIMProperty('Foo', None, type='string',
                                   propagated=False),
        ),
        None, None, True
    ),
    (
        "PROPERTY with string typed value that is empty",
        dict(
            xml_str=''
            '<PROPERTY NAME="Foo" TYPE="string">'
            '  <VALUE></VALUE>'
            '</PROPERTY>',
            exp_result=CIMProperty('Foo', value='', type='string',
                                   propagated=False),
        ),
        None, None, True
    ),
    (
        "PROPERTY with string typed value with ASCII characters",
        dict(
            xml_str=''
            '<PROPERTY NAME="Spotty" TYPE="string">'
            '  <VALUE>Foot</VALUE>'
            '</PROPERTY>',
            exp_result=CIMProperty('Spotty', value='Foot', type='string',
                                   propagated=False),
        ),
        None, None, True
    ),
    (
        "PROPERTY with string typed value with non-ASCII UCS-2 characters",
        dict(
            xml_str=b''
            b'<PROPERTY NAME="Spotty" TYPE="string">'
            b'  <VALUE>\xC3\xA9</VALUE>'
            b'</PROPERTY>',
            exp_result=CIMProperty('Spotty', value=u'\u00E9', type='string',
                                   propagated=False),
        ),
        None, None, True
    ),
    (
        "PROPERTY with string typed value with non-UCS-2 characters",
        dict(
            xml_str=b''
            b'<PROPERTY NAME="Spotty" TYPE="string">'
            b'  <VALUE>\xF0\x90\x85\x82</VALUE>'
            b'</PROPERTY>',
            exp_result=CIMProperty('Spotty', value=u'\U00010142', type='string',
                                   propagated=False),
        ),
        None, None, True
    ),
    (
        "PROPERTY with char16 typed value that is None",
        dict(
            xml_str=''
            '<PROPERTY NAME="Foo" TYPE="char16"/>',
            exp_result=CIMProperty('Foo', value=None, type='char16',
                                   propagated=False),
        ),
        None, None, True
    ),
    (
        "PROPERTY with char16 typed value with ASCII character",
        dict(
            xml_str=''
            '<PROPERTY NAME="Spotty" TYPE="char16">'
            '  <VALUE>F</VALUE>'
            '</PROPERTY>',
            exp_result=CIMProperty('Spotty', value='F', type='char16',
                                   propagated=False),
        ),
        None, None, True
    ),
    (
        "PROPERTY with char16 typed value with non-ASCII UCS-2 character",
        dict(
            xml_str=b''
            b'<PROPERTY NAME="Spotty" TYPE="char16">'
            b'  <VALUE>\xC3\xA9</VALUE>'
            b'</PROPERTY>',
            exp_result=CIMProperty('Spotty', value=u'\u00E9', type='char16',
                                   propagated=False),
        ),
        None, None, True
    ),
    (
        "PROPERTY with char16 typed value with non-UCS-2 character",
        dict(
            xml_str=b''
            b'<PROPERTY NAME="Spotty" TYPE="char16">'
            b'  <VALUE>\xF0\x90\x85\x82</VALUE>'
            b'</PROPERTY>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PROPERTY with uint8 typed value that is None",
        dict(
            xml_str=''
            '<PROPERTY NAME="Foo" TYPE="uint8"/>',
            exp_result=CIMProperty('Foo', value=None, type='uint8',
                                   propagated=False),
        ),
        None, None, True
    ),
    (
        "PROPERTY with uint8 typed value (decimal value)",
        dict(
            xml_str=''
            '<PROPERTY NAME="Age" TYPE="uint8">'
            '  <VALUE>42</VALUE>'
            '</PROPERTY>',
            exp_result=CIMProperty('Age', Uint8(42), propagated=False),
        ),
        None, None, True
    ),
    (
        "PROPERTY with uint8 typed value (decimal value with plus)",
        dict(
            xml_str=''
            '<PROPERTY NAME="Age" TYPE="uint8">'
            '  <VALUE>+42</VALUE>'
            '</PROPERTY>',
            exp_result=CIMProperty('Age', Uint8(42), propagated=False),
        ),
        None, None, True
    ),
    (
        "PROPERTY with uint8 typed value (hex value)",
        dict(
            xml_str=''
            '<PROPERTY NAME="Age" TYPE="uint8">'
            '  <VALUE>0x42</VALUE>'
            '</PROPERTY>',
            exp_result=CIMProperty('Age', Uint8(0x42), propagated=False),
        ),
        None, None, True
    ),
    (
        "PROPERTY with uint8 typed value (hex value with 0X in upper case)",
        dict(
            xml_str=''
            '<PROPERTY NAME="Age" TYPE="uint8">'
            '  <VALUE>0X42</VALUE>'
            '</PROPERTY>',
            exp_result=CIMProperty('Age', Uint8(0x42), propagated=False),
        ),
        None, None, True
    ),
    (
        "PROPERTY with uint8 typed value (hex value with plus)",
        dict(
            xml_str=''
            '<PROPERTY NAME="Age" TYPE="uint8">'
            '  <VALUE>+0x42</VALUE>'
            '</PROPERTY>',
            exp_result=CIMProperty('Age', Uint8(0x42), propagated=False),
        ),
        None, None, True
    ),
    (
        "PROPERTY with uint8 typed value (decimal value with WS)",
        dict(
            xml_str=''
            '<PROPERTY NAME="Age" TYPE="uint8">'
            '  <VALUE>  42  </VALUE>'
            '</PROPERTY>',
            exp_result=CIMProperty('Age', Uint8(42), propagated=False),
        ),
        None, None, True
    ),
    (
        "PROPERTY with uint8 typed value (invalid value: just WS)",
        dict(
            xml_str=''
            '<PROPERTY NAME="Age" TYPE="uint8">'
            '  <VALUE>  </VALUE>'
            '</PROPERTY>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PROPERTY with uint8 typed value (invalid value: empty)",
        dict(
            xml_str=''
            '<PROPERTY NAME="Age" TYPE="uint8">'
            '  <VALUE></VALUE>'
            '</PROPERTY>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PROPERTY with uint8 typed value (invalid value: letters)",
        dict(
            xml_str=''
            '<PROPERTY NAME="Age" TYPE="uint8">'
            '  <VALUE>abc</VALUE>'
            '</PROPERTY>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PROPERTY with uint8 typed value (minimum)",
        dict(
            xml_str=''
            '<PROPERTY NAME="Age" TYPE="uint8">'
            '  <VALUE>0</VALUE>'
            '</PROPERTY>',
            exp_result=CIMProperty('Age', Uint8(0), propagated=False),
        ),
        None, None, True
    ),
    (
        "PROPERTY with uint8 typed value (below minimum)",
        dict(
            xml_str=''
            '<PROPERTY NAME="Age" TYPE="uint8">'
            '  <VALUE>-1</VALUE>'
            '</PROPERTY>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PROPERTY with uint8 typed value (maximum)",
        dict(
            xml_str=''
            '<PROPERTY NAME="Age" TYPE="uint8">'
            '  <VALUE>255</VALUE>'
            '</PROPERTY>',
            exp_result=CIMProperty('Age', Uint8(255), propagated=False),
        ),
        None, None, True
    ),
    (
        "PROPERTY with uint8 typed value (above maximum)",
        dict(
            xml_str=''
            '<PROPERTY NAME="Age" TYPE="uint8">'
            '  <VALUE>256</VALUE>'
            '</PROPERTY>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PROPERTY with uint16 typed value that is None",
        dict(
            xml_str=''
            '<PROPERTY NAME="Foo" TYPE="uint16"/>',
            exp_result=CIMProperty('Foo', value=None, type='uint16',
                                   propagated=False),
        ),
        None, None, True
    ),
    (
        "PROPERTY with uint16 typed value (maximum)",
        dict(
            xml_str=''
            '<PROPERTY NAME="Age" TYPE="uint16">'
            '  <VALUE>65535</VALUE>'
            '</PROPERTY>',
            exp_result=CIMProperty('Age', Uint16(65535), propagated=False),
        ),
        None, None, True
    ),
    (
        "PROPERTY with uint32 typed value that is None",
        dict(
            xml_str=''
            '<PROPERTY NAME="Foo" TYPE="uint32"/>',
            exp_result=CIMProperty('Foo', value=None, type='uint32',
                                   propagated=False),
        ),
        None, None, True
    ),
    (
        "PROPERTY with uint32 typed value (maximum)",
        dict(
            xml_str=''
            '<PROPERTY NAME="Age" TYPE="uint32">'
            '  <VALUE>4294967295</VALUE>'
            '</PROPERTY>',
            exp_result=CIMProperty('Age', Uint32(4294967295), propagated=False),
        ),
        None, None, True
    ),
    (
        "PROPERTY with uint64 typed value that is None",
        dict(
            xml_str=''
            '<PROPERTY NAME="Foo" TYPE="uint64"/>',
            exp_result=CIMProperty('Foo', value=None, type='uint64',
                                   propagated=False),
        ),
        None, None, True
    ),
    (
        "PROPERTY with uint64 typed value (maximum)",
        dict(
            xml_str=''
            '<PROPERTY NAME="Age" TYPE="uint64">'
            '  <VALUE>18446744073709551615</VALUE>'
            '</PROPERTY>',
            exp_result=CIMProperty('Age', Uint64(18446744073709551615),
                                   propagated=False),
        ),
        None, None, True
    ),
    (
        "PROPERTY with sint8 typed value that is None",
        dict(
            xml_str=''
            '<PROPERTY NAME="Foo" TYPE="sint8"/>',
            exp_result=CIMProperty('Foo', value=None, type='sint8',
                                   propagated=False),
        ),
        None, None, True
    ),
    (
        "PROPERTY with sint8 typed value (minimum)",
        dict(
            xml_str=''
            '<PROPERTY NAME="Age" TYPE="sint8">'
            '  <VALUE>-128</VALUE>'
            '</PROPERTY>',
            exp_result=CIMProperty('Age', Sint8(-128), propagated=False),
        ),
        None, None, True
    ),
    (
        "PROPERTY with sint8 typed value (below minimum)",
        dict(
            xml_str=''
            '<PROPERTY NAME="Age" TYPE="sint8">'
            '  <VALUE>-129</VALUE>'
            '</PROPERTY>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PROPERTY with sint8 typed value (maximum)",
        dict(
            xml_str=''
            '<PROPERTY NAME="Age" TYPE="sint8">'
            '  <VALUE>127</VALUE>'
            '</PROPERTY>',
            exp_result=CIMProperty('Age', Sint8(127), propagated=False),
        ),
        None, None, True
    ),
    (
        "PROPERTY with sint8 typed value (above maximum)",
        dict(
            xml_str=''
            '<PROPERTY NAME="Age" TYPE="sint8">'
            '  <VALUE>128</VALUE>'
            '</PROPERTY>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PROPERTY with sint16 typed value that is None",
        dict(
            xml_str=''
            '<PROPERTY NAME="Foo" TYPE="sint16"/>',
            exp_result=CIMProperty('Foo', value=None, type='sint16',
                                   propagated=False),
        ),
        None, None, True
    ),
    (
        "PROPERTY with sint16 typed value (maximum)",
        dict(
            xml_str=''
            '<PROPERTY NAME="Age" TYPE="sint16">'
            '  <VALUE>32767</VALUE>'
            '</PROPERTY>',
            exp_result=CIMProperty('Age', Sint16(32767), propagated=False),
        ),
        None, None, True
    ),
    (
        "PROPERTY with sint32 typed value that is None",
        dict(
            xml_str=''
            '<PROPERTY NAME="Foo" TYPE="sint32"/>',
            exp_result=CIMProperty('Foo', value=None, type='sint32',
                                   propagated=False),
        ),
        None, None, True
    ),
    (
        "PROPERTY with sint32 typed value (maximum)",
        dict(
            xml_str=''
            '<PROPERTY NAME="Age" TYPE="sint32">'
            '  <VALUE>2147483647</VALUE>'
            '</PROPERTY>',
            exp_result=CIMProperty('Age', Sint32(2147483647), propagated=False),
        ),
        None, None, True
    ),
    (
        "PROPERTY with sint64 typed value that is None",
        dict(
            xml_str=''
            '<PROPERTY NAME="Foo" TYPE="sint64"/>',
            exp_result=CIMProperty('Foo', value=None, type='sint64',
                                   propagated=False),
        ),
        None, None, True
    ),
    (
        "PROPERTY with sint64 typed value (maximum)",
        dict(
            xml_str=''
            '<PROPERTY NAME="Age" TYPE="sint64">'
            '  <VALUE>9223372036854775807</VALUE>'
            '</PROPERTY>',
            exp_result=CIMProperty('Age', Sint64(9223372036854775807),
                                   propagated=False),
        ),
        None, None, True
    ),
    (
        "PROPERTY with real32 typed value that is None",
        dict(
            xml_str=''
            '<PROPERTY NAME="Foo" TYPE="real32"/>',
            exp_result=CIMProperty('Foo', value=None, type='real32',
                                   propagated=False),
        ),
        None, None, True
    ),
    (
        "PROPERTY with real32 typed value (42.0)",
        dict(
            xml_str=''
            '<PROPERTY NAME="Age" TYPE="real32">'
            '  <VALUE>42.0</VALUE>'
            '</PROPERTY>',
            exp_result=CIMProperty('Age', Real32(42.0), propagated=False),
        ),
        None, None, True
    ),
    (
        "PROPERTY with real32 typed value (.0)",
        dict(
            xml_str=''
            '<PROPERTY NAME="Age" TYPE="real32">'
            '  <VALUE>.0</VALUE>'
            '</PROPERTY>',
            exp_result=CIMProperty('Age', Real32(0.0), propagated=False),
        ),
        None, None, True
    ),
    (
        "PROPERTY with real32 typed value (-.1e-12)",
        dict(
            xml_str=''
            '<PROPERTY NAME="Age" TYPE="real32">'
            '  <VALUE>-.1e-12</VALUE>'
            '</PROPERTY>',
            exp_result=CIMProperty('Age', Real32(-0.1E-12), propagated=False),
        ),
        None, None, True
    ),
    (
        "PROPERTY with real32 typed value (.1E12)",
        dict(
            xml_str=''
            '<PROPERTY NAME="Age" TYPE="real32">'
            '  <VALUE>.1E12</VALUE>'
            '</PROPERTY>',
            exp_result=CIMProperty('Age', Real32(0.1E+12), propagated=False),
        ),
        None, None, True
    ),
    (
        "PROPERTY with real32 typed value (+.1e+12)",
        dict(
            xml_str=''
            '<PROPERTY NAME="Age" TYPE="real32">'
            '  <VALUE>+.1e+12</VALUE>'
            '</PROPERTY>',
            exp_result=CIMProperty('Age', Real32(0.1E+12), propagated=False),
        ),
        None, None, True
    ),
    (
        "PROPERTY with real64 typed value that is None",
        dict(
            xml_str=''
            '<PROPERTY NAME="Foo" TYPE="real64"/>',
            exp_result=CIMProperty('Foo', value=None, type='real64',
                                   propagated=False),
        ),
        None, None, True
    ),
    (
        "PROPERTY with real64 typed value (+.1e+12)",
        dict(
            xml_str=''
            '<PROPERTY NAME="Age" TYPE="real64">'
            '  <VALUE>+.1e+12</VALUE>'
            '</PROPERTY>',
            exp_result=CIMProperty('Age', Real64(0.1E+12), propagated=False),
        ),
        None, None, True
    ),
    (
        "PROPERTY with datetime typed value that is None",
        dict(
            xml_str=''
            '<PROPERTY NAME="Foo" TYPE="datetime"/>',
            exp_result=CIMProperty('Foo', value=None, type='datetime',
                                   propagated=False),
        ),
        None, None, True
    ),
    (
        "PROPERTY with datetime typed value (point in time)",
        dict(
            xml_str=''
            '<PROPERTY NAME="Age" TYPE="datetime">'
            '  <VALUE>20140924193040.654321+120</VALUE>'
            '</PROPERTY>',
            exp_result=CIMProperty(
                'Age', CIMDateTime('20140924193040.654321+120'),
                propagated=False),
        ),
        None, None, True
    ),
    (
        "PROPERTY with datetime typed value (interval)",
        dict(
            xml_str=''
            '<PROPERTY NAME="Age" TYPE="datetime">'
            '  <VALUE>00000183132542.234567:000</VALUE>'
            '</PROPERTY>',
            exp_result=CIMProperty(
                'Age', CIMDateTime('00000183132542.234567:000'),
                propagated=False),
        ),
        None, None, True
    ),
    (
        "PROPERTY with EmbeddedObject=instance and value that is None",
        dict(
            xml_str=''
            '<PROPERTY EmbeddedObject="instance" NAME="Foo" TYPE="string"/>',
            exp_result=CIMProperty(
                'Foo', value=None, type='string',
                embedded_object='instance', propagated=False,
            ),
        ),
        None, None, True
    ),
    (
        "PROPERTY with EMBEDDEDOBJECT=instance, value that is None",
        dict(
            xml_str=''
            '<PROPERTY EMBEDDEDOBJECT="instance" NAME="Foo" TYPE="string"/>',
            exp_result=CIMProperty(
                'Foo', value=None, type='string',
                embedded_object='instance', propagated=False,
            ),
        ),
        None, None, True
    ),
    (
        "PROPERTY with EmbeddedObject=instance and invalid value",
        dict(
            xml_str=''
            '<PROPERTY EmbeddedObject="instance" NAME="Foo" TYPE="string">'
            '  <VALUE>'
            '    &lt;PROPERTY NAME=&quot;one&quot; TYPE=&quot;uint8&quot;&gt;'
            '      &lt;VALUE&gt;1&lt;/VALUE&gt;'
            '    &lt;/PROPERTY&gt;'
            '  </VALUE>'
            '</PROPERTY>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PROPERTY with EmbeddedObject=instance and instance value",
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
                embedded_object='instance',
                propagated=False,
            ),
        ),
        None, None, True
    ),
    (
        "PROPERTY with EmbeddedObject=object and value that is None",
        dict(
            xml_str=''
            '<PROPERTY EmbeddedObject="object" NAME="Foo" TYPE="string"/>',
            exp_result=CIMProperty(
                'Foo', value=None, type='string',
                embedded_object='object', propagated=False,
            ),
        ),
        None, None, True
    ),
    (
        "PROPERTY with EmbeddedObject=object and invalid value",
        dict(
            xml_str=''
            '<PROPERTY EmbeddedObject="object" NAME="Foo" TYPE="string">'
            '  <VALUE>'
            '    &lt;PROPERTY NAME=&quot;one&quot; TYPE=&quot;uint8&quot;&gt;'
            '      &lt;VALUE&gt;1&lt;/VALUE&gt;'
            '    &lt;/PROPERTY&gt;'
            '  </VALUE>'
            '</PROPERTY>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PROPERTY with EmbeddedObject=object and instance value",
        dict(
            xml_str=''
            '<PROPERTY EmbeddedObject="object" NAME="Foo" TYPE="string">'
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
                embedded_object='object',
                propagated=False,
            ),
        ),
        None, None, True
    ),
    (
        "PROPERTY with EmbeddedObject=object and class value",
        dict(
            xml_str=''
            '<PROPERTY EmbeddedObject="object" NAME="Foo" TYPE="string">'
            '  <VALUE>'
            '    &lt;CLASS NAME=&quot;Foo_Class&quot;&gt;'
            '      &lt;PROPERTY NAME=&quot;one&quot; TYPE=&quot;uint8&quot;&gt;'
            '        &lt;VALUE&gt;1&lt;/VALUE&gt;'
            '      &lt;/PROPERTY&gt;'
            '      &lt;PROPERTY NAME=&quot;two&quot; TYPE=&quot;uint8&quot;&gt;'
            '        &lt;VALUE&gt;2&lt;/VALUE&gt;'
            '      &lt;/PROPERTY&gt;'
            '    &lt;/CLASS&gt;'
            '  </VALUE>'
            '</PROPERTY>',
            exp_result=CIMProperty(
                'Foo',
                CIMClass(
                    'Foo_Class',
                    properties=[
                        CIMProperty('one', Uint8(1), propagated=False),
                        CIMProperty('two', Uint8(2), propagated=False),
                    ],
                ),
                embedded_object='object',
                propagated=False,
            ),
        ),
        None, None, True
    ),
    (
        "PROPERTY with qualifier but no value (NULL)",
        dict(
            xml_str=''
            '<PROPERTY NAME="Age" TYPE="uint16">'
            '  <QUALIFIER NAME="Qual" TYPE="boolean">'
            '    <VALUE>TRUE</VALUE>'
            '  </QUALIFIER>'
            '</PROPERTY>',
            exp_result=CIMProperty(
                'Age', None, type='uint16',
                propagated=False,
                qualifiers=[
                    CIMQualifier('Qual', True,
                                 **qualifier_default_attrs()),
                ]
            ),
        ),
        None, None, True
    ),
    (
        "PROPERTY with qualifier and value",
        dict(
            xml_str=''
            '<PROPERTY NAME="Foo" TYPE="string">'
            '  <QUALIFIER NAME="Qual" TYPE="boolean"/>'
            '  <VALUE>abc</VALUE>'
            '</PROPERTY>',
            exp_result=CIMProperty(
                'Foo', type='string', value='abc',
                propagated=False,
                qualifiers=[
                    CIMQualifier('Qual', value=None, type='boolean',
                                 **qualifier_default_attrs()),
                ],
            ),
        ),
        None, None, True
    ),

    # PROPERTY.ARRAY tests:
    #
    #   <!ELEMENT PROPERTY.ARRAY (QUALIFIER*, VALUE.ARRAY?)>
    #   <!ATTLIST PROPERTY.ARRAY
    #       %CIMName;
    #       %CIMType;              #REQUIRED
    #       %ArraySize;
    #       %ClassOrigin;
    #       %Propagated;
    #       %EmbeddedObject;
    #       xml:lang NMTOKEN #IMPLIED>
    (
        "PROPERTY.ARRAY with invalid child element",
        dict(
            xml_str=''
            '<PROPERTY.ARRAY NAME="Foo" TYPE="string">'
            '  <XXX/>'
            '</PROPERTY.ARRAY>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PROPERTY.ARRAY with invalid text content",
        dict(
            xml_str=''
            '<PROPERTY.ARRAY NAME="Foo" TYPE="string">'
            '  xxx'
            '</PROPERTY.ARRAY>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PROPERTY.ARRAY with invalid attribute",
        dict(
            xml_str=''
            '<PROPERTY.ARRAY NAME="Foo" TYPE="string" XXX="bla"/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PROPERTY.ARRAY with children in incorrect order (tolerated)",
        dict(
            xml_str=''
            '<PROPERTY.ARRAY NAME="Foo" TYPE="string">'
            '  <VALUE.ARRAY/>'
            '  <QUALIFIER NAME="Qual" TYPE="boolean"/>'
            '</PROPERTY.ARRAY>',
            exp_result=CIMProperty(
                'Foo', value=[], type='string', propagated=False,
                qualifiers=[
                    CIMQualifier('Qual', value=None, type='boolean',
                                 **qualifier_default_attrs()),
                ],
            ),
        ),
        None, None, True
    ),
    (
        "PROPERTY.ARRAY with missing required attribute NAME",
        dict(
            xml_str=''
            '<PROPERTY.ARRAY TYPE="string"/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PROPERTY.ARRAY with two VALUE.ARRAY children (invalid)",
        dict(
            xml_str=''
            '<PROPERTY.ARRAY NAME="Foo" TYPE="string">'
            '  <VALUE.ARRAY>'
            '    <VALUE>b</VALUE>'
            '  </VALUE.ARRAY>'
            '  <VALUE.ARRAY>'
            '    <VALUE>b</VALUE>'
            '  </VALUE.ARRAY>'
            '</PROPERTY.ARRAY>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PROPERTY.ARRAY with NAME using ASCII characters",
        dict(
            xml_str=''
            '<PROPERTY.ARRAY NAME="Foo" TYPE="string"/>',
            exp_result=CIMProperty(
                'Foo', value=None, type='string', is_array=True,
                propagated=False,
            ),
        ),
        None, None, True
    ),
    (
        "PROPERTY.ARRAY with NAME using non-ASCII UCS-2 characters",
        dict(
            xml_str=b''
            b'<PROPERTY.ARRAY NAME="Foo\xC3\xA9" TYPE="string"/>',
            exp_result=CIMProperty(
                u'Foo\u00E9', value=None, type='string', is_array=True,
                propagated=False,
            ),
        ),
        None, None, True
    ),
    (
        "PROPERTY.ARRAY with NAME using non-UCS-2 characters",
        dict(
            xml_str=b''
            b'<PROPERTY.ARRAY NAME="Foo\xF0\x90\x85\x82" TYPE="string"/>',
            exp_result=CIMProperty(
                u'Foo\U00010142', value=None, type='string', is_array=True,
                propagated=False,
            ),
        ),
        None, None, True
    ),
    (
        "PROPERTY.ARRAY with xml:lang attribute",
        dict(
            xml_str=''
            '<PROPERTY.ARRAY NAME="Foo" TYPE="string" xml:lang="en_us"/>',
            exp_result=CIMProperty(
                'Foo', value=None, type='string', is_array=True,
                propagated=False,
            ),
        ),
        None, None, True
    ),
    (
        "PROPERTY.ARRAY with CLASSORIGIN and PROPAGATED attributes",
        dict(
            xml_str=''
            '<PROPERTY.ARRAY NAME="Foo" TYPE="string" CLASSORIGIN="CIM_Foo"'
            ' PROPAGATED="true"/>',
            exp_result=CIMProperty(
                'Foo', value=None, type='string', is_array=True,
                class_origin='CIM_Foo', propagated=True
            ),
        ),
        None, None, True
    ),
    (
        "PROPERTY.ARRAY fixed array",
        dict(
            xml_str=''
            '<PROPERTY.ARRAY NAME="Foo" TYPE="string" ARRAYSIZE="10"/>',
            exp_result=CIMProperty(
                'Foo', value=None, type='string', is_array=True, array_size=10,
                propagated=False
            ),
        ),
        None, None, True
    ),
    (
        "PROPERTY.ARRAY with missing required attribute TYPE",
        dict(
            xml_str=''
            '<PROPERTY.ARRAY NAME="Foo"/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PROPERTY.ARRAY with invalid attribute TYPE 'foo'",
        dict(
            xml_str=''
            '<PROPERTY.ARRAY NAME="Foo" TYPE="foo"/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PROPERTY.ARRAY with string array typed value that is None",
        dict(
            xml_str=''
            '<PROPERTY.ARRAY NAME="Foo" TYPE="string"/>',
            exp_result=CIMProperty(
                'Foo', value=None, type='string', is_array=True,
                propagated=False,
            ),
        ),
        None, None, True
    ),
    (
        "PROPERTY.ARRAY with string array typed value that is empty",
        dict(
            xml_str=''
            '<PROPERTY.ARRAY NAME="Foo" TYPE="string">'
            '  <VALUE.ARRAY>'
            '  </VALUE.ARRAY>'
            '</PROPERTY.ARRAY>',
            exp_result=CIMProperty(
                'Foo', value=[], type='string', is_array=True,
                propagated=False,
            ),
        ),
        None, None, True
    ),
    (
        "PROPERTY.ARRAY with string array typed value and 3 items",
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
                'Foo', value=['a', 'b', 'c'], type='string', is_array=True,
                propagated=False,
            ),
        ),
        None, None, True
    ),
    (
        "PROPERTY.ARRAY with string array typed value and some NULL items",
        dict(
            xml_str=''
            '<PROPERTY.ARRAY NAME="Foo" TYPE="string">'
            '  <VALUE.ARRAY>'
            '    <VALUE.NULL/>'
            '    <VALUE>b</VALUE>'
            '    <VALUE.NULL/>'
            '  </VALUE.ARRAY>'
            '</PROPERTY.ARRAY>',
            exp_result=CIMProperty(
                'Foo', value=[None, 'b', None], type='string', is_array=True,
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
            '  <QUALIFIER NAME="Qual" TYPE="boolean">'
            '    <VALUE>TRUE</VALUE>'
            '  </QUALIFIER>'
            '  <VALUE.ARRAY>'
            '    <VALUE>1</VALUE>'
            '    <VALUE>2</VALUE>'
            '    <VALUE>3</VALUE>'
            '  </VALUE.ARRAY>'
            '</PROPERTY.ARRAY>',
            exp_result=CIMProperty(
                'Foo', value=[Uint8(x) for x in [1, 2, 3]], type='uint8',
                is_array=True, propagated=False,
                qualifiers=[
                    CIMQualifier('Qual', True,
                                 **qualifier_default_attrs()),
                ]
            ),
        ),
        None, None, True
    ),
    (
        "PROPERTY.ARRAY with EmbeddedObject=instance and value that is None",
        dict(
            xml_str=''
            '<PROPERTY.ARRAY EmbeddedObject="instance" NAME="Foo"'
            ' TYPE="string"/>',
            exp_result=CIMProperty(
                'Foo', value=None, type='string', is_array=True,
                embedded_object='instance', propagated=False,
            ),
        ),
        None, None, True
    ),
    (
        "PROPERTY.ARRAY with EMBEDDEDOBJECT=instance and value that is None",
        dict(
            xml_str=''
            '<PROPERTY.ARRAY EMBEDDEDOBJECT="instance" NAME="Foo"'
            ' TYPE="string"/>',
            exp_result=CIMProperty(
                'Foo', value=None, type='string', is_array=True,
                embedded_object='instance', propagated=False,
            ),
        ),
        None, None, True
    ),
    (
        "PROPERTY.ARRAY with EmbeddedObject=instance and item that is NULL",
        dict(
            xml_str=''
            '<PROPERTY.ARRAY EmbeddedObject="instance" NAME="Foo"'
            ' TYPE="string">'
            '  <VALUE.ARRAY>'
            '    <VALUE.NULL/>'
            '  </VALUE.ARRAY>'
            '</PROPERTY.ARRAY>',
            exp_result=CIMProperty(
                'Foo', value=[None], type='string', is_array=True,
                embedded_object='instance', propagated=False,
            ),
        ),
        None, None, True
    ),
    (
        "PROPERTY.ARRAY with EmbeddedObject=instance and invalid item "
        "(mismatched tag)",
        dict(
            xml_str=''
            '<PROPERTY.ARRAY EmbeddedObject="instance" NAME="Foo"'
            ' TYPE="string">'
            '  <VALUE.ARRAY>'
            '    <VALUE>'
            '      &lt;PROPERTY.ARRAY NAME=&quot;one&quot; '
            '       TYPE=&quot;uint8&quot;&gt;'
            '        &lt;VALUE&gt;1&lt;/VALUE&gt;'
            '      &lt;/PROPERTY&gt;'
            '    </VALUE>'
            '  </VALUE.ARRAY>'
            '</PROPERTY.ARRAY>',
            exp_result=None,
        ),
        XMLParseError, None, True
    ),
    (
        "PROPERTY.ARRAY with EmbeddedObject=instance and instance item",
        dict(
            xml_str=''
            '<PROPERTY.ARRAY EmbeddedObject="instance" NAME="Foo"'
            ' TYPE="string">'
            '  <VALUE.ARRAY>'
            '    <VALUE>'
            '      &lt;INSTANCE CLASSNAME=&quot;Foo_Class&quot;&gt;'
            '        &lt;PROPERTY NAME=&quot;one&quot;'
            '         TYPE=&quot;uint8&quot;&gt;'
            '          &lt;VALUE&gt;1&lt;/VALUE&gt;'
            '        &lt;/PROPERTY&gt;'
            '        &lt;PROPERTY NAME=&quot;two&quot;'
            '         TYPE=&quot;uint8&quot;&gt;'
            '          &lt;VALUE&gt;2&lt;/VALUE&gt;'
            '        &lt;/PROPERTY&gt;'
            '      &lt;/INSTANCE&gt;'
            '    </VALUE>'
            '  </VALUE.ARRAY>'
            '</PROPERTY.ARRAY>',
            exp_result=CIMProperty(
                'Foo',
                value=[
                    CIMInstance(
                        'Foo_Class',
                        properties=[
                            CIMProperty('one', Uint8(1), propagated=False),
                            CIMProperty('two', Uint8(2), propagated=False),
                        ],
                    ),
                ],
                embedded_object='instance', is_array=True,
                propagated=False,
            ),
        ),
        None, None, True
    ),
    (
        "PROPERTY.ARRAY with EmbeddedObject=object and value that is None",
        dict(
            xml_str=''
            '<PROPERTY.ARRAY EmbeddedObject="object" NAME="Foo"'
            ' TYPE="string"/>',
            exp_result=CIMProperty(
                'Foo', value=None, type='string', is_array=True,
                embedded_object='object', propagated=False,
            ),
        ),
        None, None, True
    ),
    (
        "PROPERTY.ARRAY with EmbeddedObject=object and item that is NULL",
        dict(
            xml_str=''
            '<PROPERTY.ARRAY EmbeddedObject="object" NAME="Foo"'
            ' TYPE="string">'
            '  <VALUE.ARRAY>'
            '    <VALUE.NULL/>'
            '  </VALUE.ARRAY>'
            '</PROPERTY.ARRAY>',
            exp_result=CIMProperty(
                'Foo', value=[None], type='string', is_array=True,
                embedded_object='object', propagated=False,
            ),
        ),
        None, None, True
    ),
    (
        "PROPERTY.ARRAY with EmbeddedObject=object and invalid item",
        dict(
            xml_str=''
            '<PROPERTY.ARRAY EmbeddedObject="object" NAME="Foo" TYPE="string">'
            '  <VALUE.ARRAY>'
            '    <VALUE>'
            '      &lt;PROPERTY NAME=&quot;one&quot; TYPE=&quot;uint8&quot;&gt;'
            '        &lt;VALUE&gt;1&lt;/VALUE&gt;'
            '      &lt;/PROPERTY&gt;'
            '    </VALUE>'
            '  </VALUE.ARRAY>'
            '</PROPERTY.ARRAY>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PROPERTY.ARRAY with EmbeddedObject=object and instance item",
        dict(
            xml_str=''
            '<PROPERTY.ARRAY EmbeddedObject="object" NAME="Foo" TYPE="string">'
            '  <VALUE.ARRAY>'
            '    <VALUE>'
            '      &lt;INSTANCE CLASSNAME=&quot;Foo_Class&quot;&gt;'
            '        &lt;PROPERTY NAME=&quot;one&quot;'
            '         TYPE=&quot;uint8&quot;&gt;'
            '          &lt;VALUE&gt;1&lt;/VALUE&gt;'
            '        &lt;/PROPERTY&gt;'
            '        &lt;PROPERTY NAME=&quot;two&quot;'
            '         TYPE=&quot;uint8&quot;&gt;'
            '          &lt;VALUE&gt;2&lt;/VALUE&gt;'
            '        &lt;/PROPERTY&gt;'
            '      &lt;/INSTANCE&gt;'
            '    </VALUE>'
            '  </VALUE.ARRAY>'
            '</PROPERTY.ARRAY>',
            exp_result=CIMProperty(
                'Foo',
                value=[
                    CIMInstance(
                        'Foo_Class',
                        properties=[
                            CIMProperty('one', Uint8(1), propagated=False),
                            CIMProperty('two', Uint8(2), propagated=False),
                        ],
                    ),
                ],
                embedded_object='object', is_array=True,
                propagated=False,
            ),
        ),
        None, None, True
    ),
    (
        "PROPERTY.ARRAY with EmbeddedObject=object and class item",
        dict(
            xml_str=''
            '<PROPERTY.ARRAY EmbeddedObject="object" NAME="Foo" TYPE="string">'
            '  <VALUE.ARRAY>'
            '    <VALUE>'
            '      &lt;CLASS NAME=&quot;Foo_Class&quot;&gt;'
            '        &lt;PROPERTY NAME=&quot;one&quot;'
            '         TYPE=&quot;uint8&quot;&gt;'
            '          &lt;VALUE&gt;1&lt;/VALUE&gt;'
            '        &lt;/PROPERTY&gt;'
            '        &lt;PROPERTY NAME=&quot;two&quot;'
            '         TYPE=&quot;uint8&quot;&gt;'
            '          &lt;VALUE&gt;2&lt;/VALUE&gt;'
            '        &lt;/PROPERTY&gt;'
            '      &lt;/CLASS&gt;'
            '    </VALUE>'
            '  </VALUE.ARRAY>'
            '</PROPERTY.ARRAY>',
            exp_result=CIMProperty(
                'Foo',
                value=[
                    CIMClass(
                        'Foo_Class',
                        properties=[
                            CIMProperty('one', Uint8(1), propagated=False),
                            CIMProperty('two', Uint8(2), propagated=False),
                        ],
                    ),
                ],
                embedded_object='object', is_array=True,
                propagated=False,
            ),
        ),
        None, None, True
    ),

    # PROPERTY.REFERENCE tests:
    #
    #   <!ELEMENT PROPERTY.REFERENCE (QUALIFIER*, (VALUE.REFERENCE)?)>
    #   <!ATTLIST PROPERTY.REFERENCE
    #       %CIMName;
    #       %ReferenceClass;
    #       %ClassOrigin;
    #       %Propagated;>
    (
        "PROPERTY.REFERENCE with invalid child element",
        dict(
            xml_str=''
            '<PROPERTY.REFERENCE NAME="Foo">'
            '  <XXX/>'
            '</PROPERTY.REFERENCE>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PROPERTY.REFERENCE with invalid text content",
        dict(
            xml_str=''
            '<PROPERTY.REFERENCE NAME="Foo">'
            '  xxx'
            '</PROPERTY.REFERENCE>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PROPERTY.REFERENCE with invalid attribute",
        dict(
            xml_str=''
            '<PROPERTY.REFERENCE NAME="Foo" XXX="bla"/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PROPERTY.REFERENCE with children in incorrect order (tolerated)",
        dict(
            xml_str=''
            '<PROPERTY.REFERENCE NAME="Foo">'
            '  <VALUE.REFERENCE>'
            '    <INSTANCENAME CLASSNAME="CIM_Foo"/>'
            '  </VALUE.REFERENCE>'
            '  <QUALIFIER NAME="Qual" TYPE="boolean"/>'
            '</PROPERTY.REFERENCE>',
            exp_result=CIMProperty(
                'Foo',
                value=CIMInstanceName('CIM_Foo'),
                propagated=False,
                qualifiers=[
                    CIMQualifier('Qual', value=None, type='boolean',
                                 **qualifier_default_attrs()),
                ],
            ),
        ),
        None, MissingKeybindingsWarning, True
    ),
    (
        "PROPERTY.REFERENCE with missing required attribute NAME",
        dict(
            xml_str=''
            '<PROPERTY.REFERENCE/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PROPERTY.REFERENCE with two VALUE.REFERENCE children (invalid)",
        dict(
            xml_str=''
            '<PROPERTY.REFERENCE NAME="Foo">'
            '  <VALUE.REFERENCE>'
            '    <INSTANCENAME CLASSNAME="CIM_Foo"/>'
            '  </VALUE.REFERENCE>'
            '  <VALUE.REFERENCE>'
            '    <INSTANCENAME CLASSNAME="CIM_Foo"/>'
            '  </VALUE.REFERENCE>'
            '</PROPERTY.REFERENCE>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PROPERTY.REFERENCE with NAME using ASCII characters",
        dict(
            xml_str=''
            '<PROPERTY.REFERENCE NAME="Foo"/>',
            exp_result=CIMProperty(
                'Foo', value=None, type='reference',
                propagated=False,
            ),
        ),
        None, None, True
    ),
    (
        "PROPERTY.REFERENCE with NAME using non-ASCII UCS-2 characters",
        dict(
            xml_str=b''
            b'<PROPERTY.REFERENCE NAME="Foo\xC3\xA9"/>',
            exp_result=CIMProperty(
                u'Foo\u00E9', value=None, type='reference',
                propagated=False,
            ),
        ),
        None, None, True
    ),
    (
        "PROPERTY.REFERENCE with NAME using non-UCS-2 characters",
        dict(
            xml_str=b''
            b'<PROPERTY.REFERENCE NAME="Foo\xF0\x90\x85\x82"/>',
            exp_result=CIMProperty(
                u'Foo\U00010142', value=None, type='reference',
                propagated=False,
            ),
        ),
        None, None, True
    ),
    (
        "PROPERTY.REFERENCE with CLASSORIGIN and PROPAGATED attributes",
        dict(
            xml_str=''
            '<PROPERTY.REFERENCE NAME="Foo" CLASSORIGIN="CIM_Foo"'
            ' PROPAGATED="true"/>',
            exp_result=CIMProperty(
                'Foo', value=None, type='reference',
                class_origin='CIM_Foo', propagated=True),
        ),
        None, None, True
    ),
    (
        "PROPERTY.REFERENCE with value that is None",
        dict(
            xml_str=''
            '<PROPERTY.REFERENCE NAME="Foo"/>',
            exp_result=CIMProperty(
                'Foo', value=None, type='reference', propagated=False),
        ),
        None, None, True
    ),
    (
        "PROPERTY.REFERENCE with ref value that is a INSTANCENAME",
        dict(
            xml_str=''
            '<PROPERTY.REFERENCE NAME="Foo">'
            '  <VALUE.REFERENCE>'
            '    <INSTANCENAME CLASSNAME="CIM_Foo"/>'
            '  </VALUE.REFERENCE>'
            '</PROPERTY.REFERENCE>',
            exp_result=CIMProperty(
                'Foo',
                value=CIMInstanceName('CIM_Foo'),
                propagated=False,
            ),
        ),
        None, MissingKeybindingsWarning, True
    ),
    (
        "PROPERTY.REFERENCE with ref value that is a LOCALINSTANCEPATH",
        dict(
            xml_str=''
            '<PROPERTY.REFERENCE NAME="Foo">'
            '  <VALUE.REFERENCE>'
            '    <LOCALINSTANCEPATH>'
            '      <LOCALNAMESPACEPATH>'
            '        <NAMESPACE NAME="foo"/>'
            '      </LOCALNAMESPACEPATH>'
            '      <INSTANCENAME CLASSNAME="CIM_Foo"/>'
            '    </LOCALINSTANCEPATH>'
            '  </VALUE.REFERENCE>'
            '</PROPERTY.REFERENCE>',
            exp_result=CIMProperty(
                'Foo',
                value=CIMInstanceName('CIM_Foo', namespace='foo'),
                propagated=False,
            ),
        ),
        None, MissingKeybindingsWarning, True
    ),
    (
        "PROPERTY.REFERENCE with ref value that is a INSTANCEPATH",
        dict(
            xml_str=''
            '<PROPERTY.REFERENCE NAME="Foo">'
            '  <VALUE.REFERENCE>'
            '    <INSTANCEPATH>'
            '      <NAMESPACEPATH>'
            '        <HOST>woot.com</HOST>'
            '        <LOCALNAMESPACEPATH>'
            '          <NAMESPACE NAME="foo"/>'
            '        </LOCALNAMESPACEPATH>'
            '      </NAMESPACEPATH>'
            '      <INSTANCENAME CLASSNAME="CIM_Foo"/>'
            '    </INSTANCEPATH>'
            '  </VALUE.REFERENCE>'
            '</PROPERTY.REFERENCE>',
            exp_result=CIMProperty(
                'Foo',
                value=CIMInstanceName(
                    'CIM_Foo', namespace='foo', host='woot.com',
                ),
                propagated=False,
            ),
        ),
        None, MissingKeybindingsWarning, True
    ),
    (
        "PROPERTY.REFERENCE with ref value that is a CLASSNAME (not used)",
        dict(
            xml_str=''
            '<PROPERTY.REFERENCE NAME="Foo">'
            '  <VALUE.REFERENCE>'
            '    <CLASSNAME NAME="CIM_Foo"/>'
            '  </VALUE.REFERENCE>'
            '</PROPERTY.REFERENCE>',
            exp_result=CIMProperty(
                'Foo', type='reference',
                value=CIMClassName('CIM_Foo'),
                propagated=False,
            ),
        ),
        None, None, True
    ),
    (
        "PROPERTY.REFERENCE with ref value that is a LOCALCLASSPATH (not used)",
        dict(
            xml_str=''
            '<PROPERTY.REFERENCE NAME="Foo">'
            '  <VALUE.REFERENCE>'
            '    <LOCALCLASSPATH>'
            '      <LOCALNAMESPACEPATH>'
            '        <NAMESPACE NAME="foo"/>'
            '      </LOCALNAMESPACEPATH>'
            '      <CLASSNAME NAME="CIM_Foo"/>'
            '    </LOCALCLASSPATH>'
            '  </VALUE.REFERENCE>'
            '</PROPERTY.REFERENCE>',
            exp_result=CIMProperty(
                'Foo', type='reference',
                value=CIMClassName('CIM_Foo', namespace='foo'),
                propagated=False,
            ),
        ),
        None, None, True
    ),
    (
        "PROPERTY.REFERENCE with ref value that is a CLASSPATH (not used)",
        dict(
            xml_str=''
            '<PROPERTY.REFERENCE NAME="Foo">'
            '  <VALUE.REFERENCE>'
            '    <CLASSPATH>'
            '      <NAMESPACEPATH>'
            '        <HOST>woot.com</HOST>'
            '        <LOCALNAMESPACEPATH>'
            '          <NAMESPACE NAME="foo"/>'
            '        </LOCALNAMESPACEPATH>'
            '      </NAMESPACEPATH>'
            '      <CLASSNAME NAME="CIM_Foo"/>'
            '    </CLASSPATH>'
            '  </VALUE.REFERENCE>'
            '</PROPERTY.REFERENCE>',
            exp_result=CIMProperty(
                'Foo', type='reference',
                value=CIMClassName(
                    'CIM_Foo', namespace='foo', host='woot.com',
                ),
                propagated=False,
            ),
        ),
        None, None, False
    ),
    (
        "PROPERTY.REFERENCE with value and qualifiers",
        dict(
            xml_str=''
            '<PROPERTY.REFERENCE NAME="Foo">'
            '  <QUALIFIER NAME="Qual" TYPE="boolean">'
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
                    CIMQualifier('Qual', True,
                                 **qualifier_default_attrs()),
                ]
            ),
        ),
        None, MissingKeybindingsWarning, True
    ),
    (
        "PROPERTY.REFERENCE that is None and with qualifiers",
        dict(
            xml_str=''
            '<PROPERTY.REFERENCE NAME="Foo">'
            '  <QUALIFIER NAME="Qual" TYPE="boolean">'
            '    <VALUE>TRUE</VALUE>'
            '  </QUALIFIER>'
            '</PROPERTY.REFERENCE>',
            exp_result=CIMProperty(
                'Foo', type='reference',
                value=None,
                propagated=False,
                qualifiers=[
                    CIMQualifier('Qual', True,
                                 **qualifier_default_attrs()),
                ]
            ),
        ),
        None, None, True
    ),

    # PARAMETER tests:
    #
    #   <!ELEMENT PARAMETER (QUALIFIER*)>
    #   <!ATTLIST PARAMETER
    #       %CIMName;
    #       %CIMType;              #REQUIRED>
    (
        "PARAMETER with invalid child element",
        dict(
            xml_str=''
            '<PARAMETER NAME="Parm" TYPE="string">'
            '  <XXX/>'
            '</PARAMETER>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PARAMETER with invalid text content",
        dict(
            xml_str=''
            '<PARAMETER NAME="Parm" TYPE="string">'
            '  xxx'
            '</PARAMETER>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PARAMETER with invalid attribute",
        dict(
            xml_str=''
            '<PARAMETER NAME="Parm" TYPE="string" XXX="bla"/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PARAMETER with missing required attribute NAME",
        dict(
            xml_str=''
            '<PARAMETER TYPE="string"/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PARAMETER with NAME using ASCII characters",
        dict(
            xml_str=''
            '<PARAMETER NAME="Parm" TYPE="string"/>',
            exp_result=CIMParameter('Parm', type='string'),
        ),
        None, None, True
    ),
    (
        "PARAMETER with NAME using non-ASCII UCS-2 characters",
        dict(
            xml_str=b''
            b'<PARAMETER NAME="Parm\xC3\xA9" TYPE="string"/>',
            exp_result=CIMParameter(u'Parm\u00E9', type='string'),
        ),
        None, None, True
    ),
    (
        "PARAMETER with NAME using non-UCS-2 characters",
        dict(
            xml_str=b''
            b'<PARAMETER NAME="Parm\xF0\x90\x85\x82" TYPE="string"/>',
            exp_result=CIMParameter(u'Parm\U00010142', type='string'),
        ),
        None, None, True
    ),
    (
        "PARAMETER with missing required attribute TYPE",
        dict(
            xml_str=''
            '<PARAMETER NAME="Parm"/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PARAMETER with invalid attribute TYPE 'foo'",
        dict(
            xml_str=''
            '<PARAMETER NAME="Parm" TYPE="foo"/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PARAMETER of type string",
        dict(
            xml_str=''
            '<PARAMETER NAME="Parm" TYPE="string"/>',
            exp_result=CIMParameter('Parm', type='string'),
        ),
        None, None, True
    ),
    (
        "PARAMETER of type char16",
        dict(
            xml_str=''
            '<PARAMETER NAME="Parm" TYPE="char16"/>',
            exp_result=CIMParameter('Parm', type='char16'),
        ),
        None, None, True
    ),
    (
        "PARAMETER of type boolean",
        dict(
            xml_str=''
            '<PARAMETER NAME="Parm" TYPE="boolean"/>',
            exp_result=CIMParameter('Parm', type='boolean'),
        ),
        None, None, True
    ),
    (
        "PARAMETER of type uint8",
        dict(
            xml_str=''
            '<PARAMETER NAME="Parm" TYPE="uint8"/>',
            exp_result=CIMParameter('Parm', type='uint8'),
        ),
        None, None, True
    ),
    (
        "PARAMETER of type uint16",
        dict(
            xml_str=''
            '<PARAMETER NAME="Parm" TYPE="uint16"/>',
            exp_result=CIMParameter('Parm', type='uint16'),
        ),
        None, None, True
    ),
    (
        "PARAMETER of type uint32",
        dict(
            xml_str=''
            '<PARAMETER NAME="Parm" TYPE="uint32"/>',
            exp_result=CIMParameter('Parm', type='uint32'),
        ),
        None, None, True
    ),
    (
        "PARAMETER of type uint64",
        dict(
            xml_str=''
            '<PARAMETER NAME="Parm" TYPE="uint64"/>',
            exp_result=CIMParameter('Parm', type='uint64'),
        ),
        None, None, True
    ),
    (
        "PARAMETER of type sint8",
        dict(
            xml_str=''
            '<PARAMETER NAME="Parm" TYPE="sint8"/>',
            exp_result=CIMParameter('Parm', type='sint8'),
        ),
        None, None, True
    ),
    (
        "PARAMETER of type sint16",
        dict(
            xml_str=''
            '<PARAMETER NAME="Parm" TYPE="sint16"/>',
            exp_result=CIMParameter('Parm', type='sint16'),
        ),
        None, None, True
    ),
    (
        "PARAMETER of type sint32",
        dict(
            xml_str=''
            '<PARAMETER NAME="Parm" TYPE="sint32"/>',
            exp_result=CIMParameter('Parm', type='sint32'),
        ),
        None, None, True
    ),
    (
        "PARAMETER of type sint64",
        dict(
            xml_str=''
            '<PARAMETER NAME="Parm" TYPE="sint64"/>',
            exp_result=CIMParameter('Parm', type='sint64'),
        ),
        None, None, True
    ),
    (
        "PARAMETER of type real32",
        dict(
            xml_str=''
            '<PARAMETER NAME="Parm" TYPE="real32"/>',
            exp_result=CIMParameter('Parm', type='real32'),
        ),
        None, None, True
    ),
    (
        "PARAMETER of type real64",
        dict(
            xml_str=''
            '<PARAMETER NAME="Parm" TYPE="real64"/>',
            exp_result=CIMParameter('Parm', type='real64'),
        ),
        None, None, True
    ),
    (
        "PARAMETER of type datetime",
        dict(
            xml_str=''
            '<PARAMETER NAME="Parm" TYPE="datetime"/>',
            exp_result=CIMParameter('Parm', type='datetime'),
        ),
        None, None, True
    ),
    (
        "PARAMETER of type reference",
        dict(
            xml_str=''
            '<PARAMETER NAME="Parm" TYPE="reference"/>',
            exp_result=CIMParameter('Parm', type='reference'),
        ),
        None, None, True
        # TODO 1/18 AM: Should this not be rejected as invalid type?
    ),
    (
        "PARAMETER with two qualifiers",
        dict(
            xml_str=''
            '<PARAMETER NAME="Parm" TYPE="string">'
            '  <QUALIFIER NAME="Qual2" TYPE="boolean">'
            '    <VALUE>TRUE</VALUE>'
            '  </QUALIFIER>'
            '  <QUALIFIER NAME="Qual1" TYPE="boolean">'
            '    <VALUE>FALSE</VALUE>'
            '  </QUALIFIER>'
            '</PARAMETER>',
            exp_result=CIMParameter(
                'Parm', type='string',
                qualifiers=[
                    CIMQualifier('Qual2', True,
                                 **qualifier_default_attrs()),
                    CIMQualifier('Qual1', False,
                                 **qualifier_default_attrs()),
                ]
            ),
        ),
        None, None, True
    ),

    # PARAMETER.REFERENCE tests:
    #
    #   <!ELEMENT PARAMETER.REFERENCE (QUALIFIER*)>
    #   <!ATTLIST PARAMETER.REFERENCE
    #       %CIMName;
    #       %ReferenceClass;>
    (
        "PARAMETER.REFERENCE with invalid child element",
        dict(
            xml_str=''
            '<PARAMETER.REFERENCE NAME="Parm">'
            '  <XXX/>'
            '</PARAMETER.REFERENCE>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PARAMETER.REFERENCE with invalid text content",
        dict(
            xml_str=''
            '<PARAMETER.REFERENCE NAME="Parm">'
            '  xxx'
            '</PARAMETER.REFERENCE>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PARAMETER.REFERENCE with invalid attribute",
        dict(
            xml_str=''
            '<PARAMETER.REFERENCE NAME="Parm" XXX="bla"/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PARAMETER.REFERENCE with missing required attribute NAME",
        dict(
            xml_str=''
            '<PARAMETER.REFERENCE/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PARAMETER.REFERENCE with NAME using ASCII characters",
        dict(
            xml_str=''
            '<PARAMETER.REFERENCE NAME="Parm"/>',
            exp_result=CIMParameter('Parm', type='reference'),
        ),
        None, None, True
    ),
    (
        "PARAMETER.REFERENCE with NAME using non-ASCII UCS-2 characters",
        dict(
            xml_str=b''
            b'<PARAMETER.REFERENCE NAME="Parm\xC3\xA9"/>',
            exp_result=CIMParameter(u'Parm\u00E9', type='reference'),
        ),
        None, None, True
    ),
    (
        "PARAMETER.REFERENCE with NAME using non-UCS-2 characters",
        dict(
            xml_str=b''
            b'<PARAMETER.REFERENCE NAME="Parm\xF0\x90\x85\x82"/>',
            exp_result=CIMParameter(u'Parm\U00010142', type='reference'),
        ),
        None, None, True
    ),
    (
        "PARAMETER.REFERENCE with reference class",
        dict(
            xml_str=''
            '<PARAMETER.REFERENCE NAME="Parm" REFERENCECLASS="CIM_Foo"/>',
            exp_result=CIMParameter(
                'Parm', type='reference', reference_class='CIM_Foo'
            ),
        ),
        None, None, True
    ),
    (
        "PARAMETER.REFERENCE with two qualifiers",
        dict(
            xml_str=''
            '<PARAMETER.REFERENCE NAME="Parm" REFERENCECLASS="CIM_Foo">'
            '  <QUALIFIER NAME="Qual2" TYPE="boolean">'
            '    <VALUE>TRUE</VALUE>'
            '  </QUALIFIER>'
            '  <QUALIFIER NAME="Qual1" TYPE="boolean">'
            '    <VALUE>FALSE</VALUE>'
            '  </QUALIFIER>'
            '</PARAMETER.REFERENCE>',
            exp_result=CIMParameter(
                'Parm', type='reference', reference_class='CIM_Foo',
                qualifiers=[
                    CIMQualifier('Qual2', True,
                                 **qualifier_default_attrs()),
                    CIMQualifier('Qual1', False,
                                 **qualifier_default_attrs()),
                ]
            ),
        ),
        None, None, True
    ),

    # PARAMETER.ARRAY tests:
    #
    #   <!ELEMENT PARAMETER.ARRAY (QUALIFIER*)>
    #   <!ATTLIST PARAMETER.ARRAY
    #       %CIMName;
    #       %CIMType;              #REQUIRED
    #       %ArraySize;>
    (
        "PARAMETER.ARRAY with invalid child element",
        dict(
            xml_str=''
            '<PARAMETER.ARRAY NAME="Parm" TYPE="string">'
            '  <XXX/>'
            '</PARAMETER.ARRAY>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PARAMETER.ARRAY with invalid text content",
        dict(
            xml_str=''
            '<PARAMETER.ARRAY NAME="Parm" TYPE="string">'
            '  xxx'
            '</PARAMETER.ARRAY>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PARAMETER.ARRAY with invalid attribute",
        dict(
            xml_str=''
            '<PARAMETER.ARRAY NAME="Parm" TYPE="string" XXX="bla"/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PARAMETER.ARRAY with missing required attribute NAME",
        dict(
            xml_str=''
            '<PARAMETER.ARRAY TYPE="string"/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PARAMETER.ARRAY with NAME using ASCII characters",
        dict(
            xml_str=''
            '<PARAMETER.ARRAY NAME="Parm" TYPE="string"/>',
            exp_result=CIMParameter('Parm', type='string', is_array=True),
        ),
        None, None, True
    ),
    (
        "PARAMETER.ARRAY with NAME using non-ASCII UCS-2 characters",
        dict(
            xml_str=b''
            b'<PARAMETER.ARRAY NAME="Parm\xC3\xA9" TYPE="string"/>',
            exp_result=CIMParameter(
                u'Parm\u00E9', type='string', is_array=True),
        ),
        None, None, True
    ),
    (
        "PARAMETER.ARRAY with NAME using non-UCS-2 characters",
        dict(
            xml_str=b''
            b'<PARAMETER.ARRAY NAME="Parm\xF0\x90\x85\x82" TYPE="string"/>',
            exp_result=CIMParameter(
                u'Parm\U00010142', type='string', is_array=True),
        ),
        None, None, True
    ),
    (
        "PARAMETER.ARRAY fixed array",
        dict(
            xml_str=''
            '<PARAMETER.ARRAY ARRAYSIZE="10" NAME="Parm" TYPE="string"/>',
            exp_result=CIMParameter(
                'Parm', type='string', is_array=True, array_size=10
            ),
        ),
        None, None, True
    ),
    (
        "PARAMETER.ARRAY with missing required attribute TYPE",
        dict(
            xml_str=''
            '<PARAMETER.ARRAY NAME="Parm"/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PARAMETER.ARRAY with invalid attribute TYPE 'foo'",
        dict(
            xml_str=''
            '<PARAMETER.ARRAY NAME="Parm" TYPE="foo"/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PARAMETER.ARRAY of type string",
        dict(
            xml_str=''
            '<PARAMETER.ARRAY NAME="Parm" TYPE="string"/>',
            exp_result=CIMParameter('Parm', type='string', is_array=True),
        ),
        None, None, True
    ),
    (
        "PARAMETER.ARRAY of type char16",
        dict(
            xml_str=''
            '<PARAMETER.ARRAY NAME="Parm" TYPE="char16"/>',
            exp_result=CIMParameter('Parm', type='char16', is_array=True),
        ),
        None, None, True
    ),
    (
        "PARAMETER.ARRAY of type boolean",
        dict(
            xml_str=''
            '<PARAMETER.ARRAY NAME="Parm" TYPE="boolean"/>',
            exp_result=CIMParameter('Parm', type='boolean', is_array=True),
        ),
        None, None, True
    ),
    (
        "PARAMETER.ARRAY of type uint8",
        dict(
            xml_str=''
            '<PARAMETER.ARRAY NAME="Parm" TYPE="uint8"/>',
            exp_result=CIMParameter('Parm', type='uint8', is_array=True),
        ),
        None, None, True
    ),
    (
        "PARAMETER.ARRAY of type uint16",
        dict(
            xml_str=''
            '<PARAMETER.ARRAY NAME="Parm" TYPE="uint16"/>',
            exp_result=CIMParameter('Parm', type='uint16', is_array=True),
        ),
        None, None, True
    ),
    (
        "PARAMETER.ARRAY of type uint32",
        dict(
            xml_str=''
            '<PARAMETER.ARRAY NAME="Parm" TYPE="uint32"/>',
            exp_result=CIMParameter('Parm', type='uint32', is_array=True),
        ),
        None, None, True
    ),
    (
        "PARAMETER.ARRAY of type uint64",
        dict(
            xml_str=''
            '<PARAMETER.ARRAY NAME="Parm" TYPE="uint64"/>',
            exp_result=CIMParameter('Parm', type='uint64', is_array=True),
        ),
        None, None, True
    ),
    (
        "PARAMETER.ARRAY of type sint8",
        dict(
            xml_str=''
            '<PARAMETER.ARRAY NAME="Parm" TYPE="sint8"/>',
            exp_result=CIMParameter('Parm', type='sint8', is_array=True),
        ),
        None, None, True
    ),
    (
        "PARAMETER.ARRAY of type sint16",
        dict(
            xml_str=''
            '<PARAMETER.ARRAY NAME="Parm" TYPE="sint16"/>',
            exp_result=CIMParameter('Parm', type='sint16', is_array=True),
        ),
        None, None, True
    ),
    (
        "PARAMETER.ARRAY of type sint32",
        dict(
            xml_str=''
            '<PARAMETER.ARRAY NAME="Parm" TYPE="sint32"/>',
            exp_result=CIMParameter('Parm', type='sint32', is_array=True),
        ),
        None, None, True
    ),
    (
        "PARAMETER.ARRAY of type sint64",
        dict(
            xml_str=''
            '<PARAMETER.ARRAY NAME="Parm" TYPE="sint64"/>',
            exp_result=CIMParameter('Parm', type='sint64', is_array=True),
        ),
        None, None, True
    ),
    (
        "PARAMETER.ARRAY of type real32",
        dict(
            xml_str=''
            '<PARAMETER.ARRAY NAME="Parm" TYPE="real32"/>',
            exp_result=CIMParameter('Parm', type='real32', is_array=True),
        ),
        None, None, True
    ),
    (
        "PARAMETER.ARRAY of type real64",
        dict(
            xml_str=''
            '<PARAMETER.ARRAY NAME="Parm" TYPE="real64"/>',
            exp_result=CIMParameter('Parm', type='real64', is_array=True),
        ),
        None, None, True
    ),
    (
        "PARAMETER.ARRAY of type datetime",
        dict(
            xml_str=''
            '<PARAMETER.ARRAY NAME="Parm" TYPE="datetime"/>',
            exp_result=CIMParameter('Parm', type='datetime', is_array=True),
        ),
        None, None, True
    ),
    (
        "PARAMETER.ARRAY with two qualifiers",
        dict(
            xml_str=''
            '<PARAMETER.ARRAY NAME="Parm" TYPE="string">'
            '  <QUALIFIER NAME="Qual2" TYPE="boolean">'
            '    <VALUE>TRUE</VALUE>'
            '  </QUALIFIER>'
            '  <QUALIFIER NAME="Qual1" TYPE="boolean">'
            '    <VALUE>FALSE</VALUE>'
            '  </QUALIFIER>'
            '</PARAMETER.ARRAY>',
            exp_result=CIMParameter(
                'Parm', type='string', is_array=True,
                qualifiers=[
                    CIMQualifier('Qual2', True,
                                 **qualifier_default_attrs()),
                    CIMQualifier('Qual1', False,
                                 **qualifier_default_attrs()),
                ]
            ),
        ),
        None, None, True
    ),

    # PARAMETER.REFARRAY tests:
    #
    #   <!ELEMENT PARAMETER.REFARRAY (QUALIFIER*)>
    #   <!ATTLIST PARAMETER.REFARRAY
    #       %CIMName;
    #       %ReferenceClass;
    #       %ArraySize;>
    (
        "PARAMETER.REFARRAY with invalid child element",
        dict(
            xml_str=''
            '<PARAMETER.REFARRAY NAME="Parm">'
            '  <XXX/>'
            '</PARAMETER.REFARRAY>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PARAMETER.REFARRAY with invalid text content",
        dict(
            xml_str=''
            '<PARAMETER.REFARRAY NAME="Parm">'
            '  xxx'
            '</PARAMETER.REFARRAY>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PARAMETER.REFARRAY with invalid attribute",
        dict(
            xml_str=''
            '<PARAMETER.REFARRAY NAME="Parm" XXX="bla"/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PARAMETER.REFARRAY with missing required attribute NAME",
        dict(
            xml_str=''
            '<PARAMETER.REFARRAY/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PARAMETER.REFARRAY with NAME using ASCII characters",
        dict(
            xml_str=''
            '<PARAMETER.REFARRAY NAME="Parm"/>',
            exp_result=CIMParameter('Parm', type='reference', is_array=True),
        ),
        None, None, True
    ),
    (
        "PARAMETER.REFARRAY with NAME using non-ASCII UCS-2 characters",
        dict(
            xml_str=b''
            b'<PARAMETER.REFARRAY NAME="Parm\xC3\xA9"/>',
            exp_result=CIMParameter(
                u'Parm\u00E9', type='reference', is_array=True),
        ),
        None, None, True
    ),
    (
        "PARAMETER.REFARRAY with NAME using non-UCS-2 characters",
        dict(
            xml_str=b''
            b'<PARAMETER.REFARRAY NAME="Parm\xF0\x90\x85\x82"/>',
            exp_result=CIMParameter(
                u'Parm\U00010142', type='reference', is_array=True),
        ),
        None, None, True
    ),
    (
        "PARAMETER.REFARRAY with reference class",
        dict(
            xml_str=''
            '<PARAMETER.REFARRAY NAME="Parm" REFERENCECLASS="CIM_Foo"/>',
            exp_result=CIMParameter(
                'Parm', type='reference', is_array=True,
                reference_class='CIM_Foo'
            ),
        ),
        None, None, True
    ),
    (
        "PARAMETER.REFARRAY with fixed size",
        dict(
            xml_str=''
            '<PARAMETER.REFARRAY NAME="Array" ARRAYSIZE="10"/>',
            exp_result=CIMParameter(
                'Array', type='reference', is_array=True, array_size=10,
            ),
        ),
        None, None, True
    ),
    (
        "PARAMETER.REFARRAY with two qualifiers",
        dict(
            xml_str=''
            '<PARAMETER.REFARRAY NAME="Parm">'
            '  <QUALIFIER NAME="Qual2" TYPE="boolean">'
            '    <VALUE>TRUE</VALUE>'
            '  </QUALIFIER>'
            '  <QUALIFIER NAME="Qual1" TYPE="boolean">'
            '    <VALUE>FALSE</VALUE>'
            '  </QUALIFIER>'
            '</PARAMETER.REFARRAY>',
            exp_result=CIMParameter(
                'Parm', type='reference', is_array=True,
                qualifiers=[
                    CIMQualifier('Qual2', True,
                                 **qualifier_default_attrs()),
                    CIMQualifier('Qual1', False,
                                 **qualifier_default_attrs()),
                ],
            ),
        ),
        None, None, True
    ),

    # METHOD tests:
    #
    #   <!ELEMENT METHOD (QUALIFIER*, (PARAMETER | PARAMETER.REFERENCE |
    #                                  PARAMETER.ARRAY |
    #                                  PARAMETER.REFARRAY)*)>
    #   <!ATTLIST METHOD
    #       %CIMName;
    #       %CIMType;              #IMPLIED
    #       %ClassOrigin;
    #       %Propagated;>
    (
        "METHOD with invalid child element",
        dict(
            xml_str=''
            '<METHOD NAME="Foo" TYPE="string">'
            '  <XXX/>'
            '</METHOD>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "METHOD with invalid text content",
        dict(
            xml_str=''
            '<METHOD NAME="Foo" TYPE="string">'
            '  xxx'
            '</METHOD>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "METHOD with invalid attribute",
        dict(
            xml_str=''
            '<METHOD NAME="Foo" TYPE="string" XXX="bla"/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "METHOD with children in incorrect order (tolerated)",
        dict(
            xml_str=''
            '<METHOD NAME="Foo" TYPE="string">'
            '  <PARAMETER NAME="Parm1" TYPE="uint32"/>'
            '  <QUALIFIER NAME="Qual" TYPE="boolean"/>'
            '</METHOD>',
            exp_result=CIMMethod(
                'Foo', return_type='string',
                propagated=False,
                qualifiers=[
                    CIMQualifier('Qual', value=None, type='boolean',
                                 **qualifier_default_attrs()),
                ],
                parameters=[
                    CIMParameter('Parm1', type='uint32'),
                ],
            ),
        ),
        None, None, True
    ),
    (
        "METHOD with missing required attribute NAME",
        dict(
            xml_str=''
            '<METHOD TYPE="string"/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "METHOD with NAME using ASCII characters",
        dict(
            xml_str=''
            '<METHOD NAME="Foo" TYPE="string"/>',
            exp_result=CIMMethod('Foo', return_type='string',
                                 propagated=False),
        ),
        None, None, True
    ),
    (
        "METHOD with NAME using non-ASCII UCS-2 characters",
        dict(
            xml_str=b''
            b'<METHOD NAME="Foo\xC3\xA9" TYPE="string"/>',
            exp_result=CIMMethod(u'Foo\u00E9', return_type='string',
                                 propagated=False),
        ),
        None, None, True
    ),
    (
        "METHOD with NAME using non-UCS-2 characters",
        dict(
            xml_str=b''
            b'<METHOD NAME="Foo\xF0\x90\x85\x82" TYPE="string"/>',
            exp_result=CIMMethod(u'Foo\U00010142', return_type='string',
                                 propagated=False),
        ),
        None, None, True
    ),
    (
        "METHOD with CLASSORIGIN and PROPAGATED attributes",
        dict(
            xml_str=''
            '<METHOD NAME="Foo" TYPE="string" CLASSORIGIN="CIM_Foo"'
            ' PROPAGATED="true"/>',
            exp_result=CIMMethod('Foo', return_type='string',
                                 class_origin='CIM_Foo', propagated=True),
        ),
        None, None, True
    ),
    (
        "METHOD without attribute TYPE (void return type)",
        dict(
            xml_str=''
            '<METHOD NAME="Foo"/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "METHOD with invalid attribute TYPE 'foo'",
        dict(
            xml_str=''
            '<METHOD NAME="Foo" TYPE="foo"/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "METHOD with two qualifiers",
        dict(
            xml_str=''
            '<METHOD NAME="Age" TYPE="uint16">'
            '  <QUALIFIER NAME="Qual2" TYPE="boolean">'
            '    <VALUE>TRUE</VALUE>'
            '  </QUALIFIER>'
            '  <QUALIFIER NAME="Qual1" TYPE="boolean">'
            '    <VALUE>FALSE</VALUE>'
            '  </QUALIFIER>'
            '</METHOD>',
            exp_result=CIMMethod(
                'Age', return_type='uint16',
                propagated=False,
                qualifiers=[
                    CIMQualifier('Qual2', True,
                                 **qualifier_default_attrs()),
                    CIMQualifier('Qual1', False,
                                 **qualifier_default_attrs()),
                ]
            ),
        ),
        None, None, True
    ),
    (
        "METHOD with multiple parameters of different kind (in opposite order "
        "of declaration in DTD, and decreasing order of names)",
        dict(
            xml_str=''
            '<METHOD NAME="Age" TYPE="uint16">'
            '  <PARAMETER.REFARRAY NAME="Parm4" REFERENCECLASS="CIM_Foo"/>'
            '  <PARAMETER.ARRAY NAME="Parm3" TYPE="uint32"/>'
            '  <PARAMETER.REFERENCE NAME="Parm2" REFERENCECLASS="CIM_Foo"/>'
            '  <PARAMETER NAME="Parm1" TYPE="uint32"/>'
            '</METHOD>',
            exp_result=CIMMethod(
                'Age', return_type='uint16',
                propagated=False,
                parameters=[
                    CIMParameter('Parm4', type='reference', is_array=True,
                                 reference_class='CIM_Foo'),
                    CIMParameter('Parm3', type='uint32', is_array=True),
                    CIMParameter('Parm2', type='reference',
                                 reference_class='CIM_Foo'),
                    CIMParameter('Parm1', type='uint32'),
                ],
            ),
        ),
        None, None, True
    ),
    (
        "METHOD with one qualifier and one parameter",
        dict(
            xml_str=''
            '<METHOD NAME="Age" TYPE="uint16">'
            '  <QUALIFIER NAME="Qual" TYPE="boolean">'
            '    <VALUE>TRUE</VALUE>'
            '  </QUALIFIER>'
            '  <PARAMETER NAME="Parm" TYPE="uint32"/>'
            '</METHOD>',
            exp_result=CIMMethod(
                'Age', return_type='uint16',
                propagated=False,
                qualifiers=[
                    CIMQualifier('Qual', True,
                                 **qualifier_default_attrs()),
                ],
                parameters=[
                    CIMParameter('Parm', type='uint32'),
                ],
            ),
        ),
        None, None, True
    ),

    # SCOPE tests:
    #
    #   <!ELEMENT SCOPE EMPTY>
    #   <!ATTLIST SCOPE
    #       CLASS (true | false) "false"
    #       ASSOCIATION (true | false) "false"
    #       REFERENCE (true | false) "false"
    #       PROPERTY (true | false) "false"
    #       METHOD (true | false) "false"
    #       PARAMETER (true | false) "false"
    #       INDICATION (true | false) "false"
    (
        "SCOPE with invalid child element",
        dict(
            xml_str=''
            '<SCOPE>'
            '  <XXX/>'
            '</SCOPE>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "SCOPE with invalid text content",
        dict(
            xml_str=''
            '<SCOPE>'
            '  xxx'
            '</SCOPE>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "SCOPE with invalid attribute",
        dict(
            xml_str=''
            '<SCOPE XXX="bla"/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "SCOPE with boolean attribute 'true' (lower case)",
        dict(
            xml_str=''
            '<SCOPE CLASS="true"/>',
            exp_result={
                u'CLASS': True,
            },
        ),
        None, None, True
    ),
    (
        "SCOPE with boolean attribute 'TrUe' (mixed case)",
        dict(
            xml_str=''
            '<SCOPE CLASS="TrUe"/>',
            exp_result={
                u'CLASS': True,
            },
        ),
        None, None, True
    ),
    (
        "SCOPE with boolean attribute 'TRUE' (upper case)",
        dict(
            xml_str=''
            '<SCOPE CLASS="TrUe"/>',
            exp_result={
                u'CLASS': True,
            },
        ),
        None, None, True
    ),
    (
        "SCOPE with boolean attribute 'false' (lower case)",
        dict(
            xml_str=''
            '<SCOPE CLASS="false"/>',
            exp_result={
                u'CLASS': False,
            },
        ),
        None, None, True
    ),
    (
        "SCOPE with boolean attribute 'FaLsE' (mixed case)",
        dict(
            xml_str=''
            '<SCOPE CLASS="FaLsE"/>',
            exp_result={
                u'CLASS': False,
            },
        ),
        None, None, True
    ),
    (
        "SCOPE with boolean attribute 'FALSE' (upper case)",
        dict(
            xml_str=''
            '<SCOPE CLASS="FALSE"/>',
            exp_result={
                u'CLASS': False,
            },
        ),
        None, None, True
    ),
    (
        "SCOPE with invalid boolean attribute",
        dict(
            xml_str=''
            '<SCOPE CLASS="XXX"/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "SCOPE with invalid empty boolean attribute",
        dict(
            xml_str=''
            '<SCOPE CLASS=""/>',
            exp_result=None,
        ),
        CIMXMLParseError, ToleratedServerIssueWarning, True
    ),
    (
        "SCOPE with all supported scope attributes with different values",
        dict(
            xml_str=''
            '<SCOPE'
            ' REFERENCE="true"'
            ' CLASS="true"'
            ' ASSOCIATION="false"'
            ' PROPERTY="false"'
            ' PARAMETER="false"'
            ' INDICATION="true"'
            ' METHOD="true"'
            '/>',
            exp_result={
                u'CLASS': True,
                u'ASSOCIATION': False,
                u'REFERENCE': True,
                u'PROPERTY': False,
                u'METHOD': True,
                u'PARAMETER': False,
                u'INDICATION': True,
            },
        ),
        None, None, True
    ),

    # QUALIFIER tests:
    #
    #   <!ELEMENT QUALIFIER (VALUE | VALUE.ARRAY)>
    #   <!ATTLIST QUALIFIER
    #       %CIMName;
    #       %CIMType;              #REQUIRED
    #       %Propagated;
    #       %QualifierFlavor;
    #       xml:lang NMTOKEN #IMPLIED>
    (
        "QUALIFIER with invalid child element",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="string">'
            '  <XXX/>'
            '</QUALIFIER>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "QUALIFIER with invalid text content",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="string">'
            '  xxx'
            '</QUALIFIER>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "QUALIFIER with invalid attribute",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="string" XXX="bla"/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "QUALIFIER with missing required attribute NAME",
        dict(
            xml_str=''
            '<QUALIFIER TYPE="string"/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "QUALIFIER with two VALUE children (invalid)",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="string">'
            '  <VALUE>abc</VALUE>'
            '  <VALUE>abc</VALUE>'
            '</QUALIFIER>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "QUALIFIER with two VALUE.ARRAY children (invalid)",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="string">'
            '  <VALUE.ARRAY/>'
            '  <VALUE.ARRAY/>'
            '</QUALIFIER>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "QUALIFIER with NAME using ASCII characters",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="string"/>',
            exp_result=CIMQualifier(
                'Qual', value=None, type='string',
                **qualifier_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER with NAME using non-ASCII UCS-2 characters",
        dict(
            xml_str=b''
            b'<QUALIFIER NAME="Qual\xC3\xA9" TYPE="string"/>',
            exp_result=CIMQualifier(
                u'Qual\u00E9', value=None, type='string',
                **qualifier_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER with NAME using non-UCS-2 characters",
        dict(
            xml_str=b''
            b'<QUALIFIER NAME="Qual\xF0\x90\x85\x82" TYPE="string"/>',
            exp_result=CIMQualifier(
                u'Qual\U00010142', value=None, type='string',
                **qualifier_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER with xml:lang attribute",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="string" xml:lang="en_us"/>',
            exp_result=CIMQualifier(
                'Qual', value=None, type='string',
                **qualifier_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER with OVERRIDABLE attribute (true)",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="string" OVERRIDABLE="true"/>',
            exp_result=CIMQualifier(
                'Qual', value=None, type='string',
                **(qualifier_default_attrs(overridable=True))
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER with OVERRIDABLE attribute (TrUe)",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="string" OVERRIDABLE="TrUe"/>',
            exp_result=CIMQualifier(
                'Qual', value=None, type='string',
                **(qualifier_default_attrs(overridable=True))
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER with OVERRIDABLE attribute (false)",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="string" OVERRIDABLE="false"/>',
            exp_result=CIMQualifier(
                'Qual', value=None, type='string',
                **(qualifier_default_attrs(overridable=False))
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER with OVERRIDABLE attribute (FaLsE)",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="string" OVERRIDABLE="FaLsE"/>',
            exp_result=CIMQualifier(
                'Qual', value=None, type='string',
                **(qualifier_default_attrs(overridable=False))
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER with TOSUBCLASS attribute (true)",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="string" TOSUBCLASS="true"/>',
            exp_result=CIMQualifier(
                'Qual', value=None, type='string',
                **(qualifier_default_attrs(tosubclass=True))
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER with TOSUBCLASS attribute (TrUe)",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="string" TOSUBCLASS="TrUe"/>',
            exp_result=CIMQualifier(
                'Qual', value=None, type='string',
                **(qualifier_default_attrs(tosubclass=True))
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER with TOSUBCLASS attribute (false)",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="string" TOSUBCLASS="false"/>',
            exp_result=CIMQualifier(
                'Qual', value=None, type='string',
                **(qualifier_default_attrs(tosubclass=False))
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER with TOSUBCLASS attribute (FaLsE)",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="string" TOSUBCLASS="FaLsE"/>',
            exp_result=CIMQualifier(
                'Qual', value=None, type='string',
                **(qualifier_default_attrs(tosubclass=False))
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER with TOINSTANCE attribute (true)",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="string" TOINSTANCE="true"/>',
            exp_result=CIMQualifier(
                'Qual', value=None, type='string',
                **(qualifier_default_attrs(toinstance=True))
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER with TOINSTANCE attribute (TrUe)",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="string" TOINSTANCE="TrUe"/>',
            exp_result=CIMQualifier(
                'Qual', value=None, type='string',
                **(qualifier_default_attrs(toinstance=True))
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER with TOINSTANCE attribute (false)",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="string" TOINSTANCE="false"/>',
            exp_result=CIMQualifier(
                'Qual', value=None, type='string',
                **(qualifier_default_attrs(toinstance=False))
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER with TOINSTANCE attribute (FaLsE)",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="string" TOINSTANCE="FaLsE"/>',
            exp_result=CIMQualifier(
                'Qual', value=None, type='string',
                **(qualifier_default_attrs(toinstance=False))
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER with TRANSLATABLE attribute (true)",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="string" TRANSLATABLE="true"/>',
            exp_result=CIMQualifier(
                'Qual', value=None, type='string',
                **(qualifier_default_attrs(translatable=True))
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER with TRANSLATABLE attribute (TrUe)",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="string" TRANSLATABLE="TrUe"/>',
            exp_result=CIMQualifier(
                'Qual', value=None, type='string',
                **(qualifier_default_attrs(translatable=True))
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER with TRANSLATABLE attribute (false)",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="string" TRANSLATABLE="false"/>',
            exp_result=CIMQualifier(
                'Qual', value=None, type='string',
                **(qualifier_default_attrs(translatable=False))
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER with TRANSLATABLE attribute (FaLsE)",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="string" TRANSLATABLE="FaLsE"/>',
            exp_result=CIMQualifier(
                'Qual', value=None, type='string',
                **(qualifier_default_attrs(translatable=False))
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER with PROPAGATED attribute (true)",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="string" PROPAGATED="true"/>',
            exp_result=CIMQualifier(
                'Qual', value=None, type='string',
                **(qualifier_default_attrs(propagated=True))
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER with PROPAGATED attribute (TrUe)",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="string" PROPAGATED="TrUe"/>',
            exp_result=CIMQualifier(
                'Qual', value=None, type='string',
                **(qualifier_default_attrs(propagated=True))
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER with PROPAGATED attribute (false)",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="string" PROPAGATED="false"/>',
            exp_result=CIMQualifier(
                'Qual', value=None, type='string',
                **(qualifier_default_attrs(propagated=False))
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER with PROPAGATED attribute (FaLsE)",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="string" PROPAGATED="FaLsE"/>',
            exp_result=CIMQualifier(
                'Qual', value=None, type='string',
                **(qualifier_default_attrs(propagated=False))
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER with missing required attribute TYPE",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual"/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "QUALIFIER with invalid attribute TYPE 'foo'",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="foo"/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "QUALIFIER with boolean typed value None",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="boolean"/>',
            exp_result=CIMQualifier(
                'Qual', value=None, type='boolean',
                **qualifier_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER with boolean typed simple value",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="boolean">'
            '  <VALUE>true</VALUE>'
            '</QUALIFIER>',
            exp_result=CIMQualifier(
                'Qual', value=True, type='boolean',
                **qualifier_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER with boolean typed array value (empty)",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="boolean">'
            '  <VALUE.ARRAY/>'
            '</QUALIFIER>',
            exp_result=CIMQualifier(
                'Qual', value=[], type='boolean',
                **qualifier_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER with string typed value None",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="string"/>',
            exp_result=CIMQualifier(
                'Qual', value=None, type='string',
                **qualifier_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER with string typed simple value",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="string">'
            '  <VALUE>abc</VALUE>'
            '</QUALIFIER>',
            exp_result=CIMQualifier(
                'Qual', value='abc', type='string',
                **qualifier_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER with string typed array value (empty)",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="string">'
            '  <VALUE.ARRAY/>'
            '</QUALIFIER>',
            exp_result=CIMQualifier(
                'Qual', value=[], type='string',
                **qualifier_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER with char16 typed value None",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="char16"/>',
            exp_result=CIMQualifier(
                'Qual', value=None, type='char16',
                **qualifier_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER with char16 typed simple value",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="char16">'
            '  <VALUE>a</VALUE>'
            '</QUALIFIER>',
            exp_result=CIMQualifier(
                'Qual', value='a', type='char16',
                **qualifier_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER with char16 typed array value (empty)",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="char16">'
            '  <VALUE.ARRAY/>'
            '</QUALIFIER>',
            exp_result=CIMQualifier(
                'Qual', value=[], type='char16',
                **qualifier_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER with uint8 typed value None",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="uint8"/>',
            exp_result=CIMQualifier(
                'Qual', value=None, type='uint8',
                **qualifier_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER with uint8 typed simple value",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="uint8">'
            '  <VALUE>42</VALUE>'
            '</QUALIFIER>',
            exp_result=CIMQualifier(
                'Qual', value=42, type='uint8',
                **qualifier_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER with uint8 typed array value (empty)",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="uint8">'
            '  <VALUE.ARRAY/>'
            '</QUALIFIER>',
            exp_result=CIMQualifier(
                'Qual', value=[], type='uint8',
                **qualifier_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER with uint16 typed value None",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="uint16"/>',
            exp_result=CIMQualifier(
                'Qual', value=None, type='uint16',
                **qualifier_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER with uint16 typed simple value",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="uint16">'
            '  <VALUE>42</VALUE>'
            '</QUALIFIER>',
            exp_result=CIMQualifier(
                'Qual', value=42, type='uint16',
                **qualifier_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER with uint16 typed array value (empty)",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="uint16">'
            '  <VALUE.ARRAY/>'
            '</QUALIFIER>',
            exp_result=CIMQualifier(
                'Qual', value=[], type='uint16',
                **qualifier_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER with uint32 typed value None",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="uint32"/>',
            exp_result=CIMQualifier(
                'Qual', value=None, type='uint32',
                **qualifier_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER with uint32 typed simple value",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="uint32">'
            '  <VALUE>42</VALUE>'
            '</QUALIFIER>',
            exp_result=CIMQualifier(
                'Qual', value=42, type='uint32',
                **qualifier_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER with uint32 typed array value (empty)",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="uint32">'
            '  <VALUE.ARRAY/>'
            '</QUALIFIER>',
            exp_result=CIMQualifier(
                'Qual', value=[], type='uint32',
                **qualifier_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER with uint64 typed value None",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="uint64"/>',
            exp_result=CIMQualifier(
                'Qual', value=None, type='uint64',
                **qualifier_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER with uint64 typed simple value",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="uint64">'
            '  <VALUE>42</VALUE>'
            '</QUALIFIER>',
            exp_result=CIMQualifier(
                'Qual', value=42, type='uint64',
                **qualifier_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER with uint64 typed array value (empty)",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="uint64">'
            '  <VALUE.ARRAY/>'
            '</QUALIFIER>',
            exp_result=CIMQualifier(
                'Qual', value=[], type='uint64',
                **qualifier_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER with sint8 typed value None",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="sint8"/>',
            exp_result=CIMQualifier(
                'Qual', value=None, type='sint8',
                **qualifier_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER with sint8 typed simple value",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="sint8">'
            '  <VALUE>42</VALUE>'
            '</QUALIFIER>',
            exp_result=CIMQualifier(
                'Qual', value=42, type='sint8',
                **qualifier_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER with sint8 typed array value (empty)",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="sint8">'
            '  <VALUE.ARRAY/>'
            '</QUALIFIER>',
            exp_result=CIMQualifier(
                'Qual', value=[], type='sint8',
                **qualifier_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER with sint16 typed value None",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="sint16"/>',
            exp_result=CIMQualifier(
                'Qual', value=None, type='sint16',
                **qualifier_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER with sint16 typed simple value",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="sint16">'
            '  <VALUE>42</VALUE>'
            '</QUALIFIER>',
            exp_result=CIMQualifier(
                'Qual', value=42, type='sint16',
                **qualifier_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER with sint16 typed array value (empty)",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="sint16">'
            '  <VALUE.ARRAY/>'
            '</QUALIFIER>',
            exp_result=CIMQualifier(
                'Qual', value=[], type='sint16',
                **qualifier_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER with sint32 typed value None",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="sint32"/>',
            exp_result=CIMQualifier(
                'Qual', value=None, type='sint32',
                **qualifier_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER with sint32 typed simple value",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="sint32">'
            '  <VALUE>42</VALUE>'
            '</QUALIFIER>',
            exp_result=CIMQualifier(
                'Qual', value=42, type='sint32',
                **qualifier_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER with sint32 typed array value (empty)",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="sint32">'
            '  <VALUE.ARRAY/>'
            '</QUALIFIER>',
            exp_result=CIMQualifier(
                'Qual', value=[], type='sint32',
                **qualifier_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER with sint64 typed value None",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="sint64"/>',
            exp_result=CIMQualifier(
                'Qual', value=None, type='sint64',
                **qualifier_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER with sint64 typed simple value",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="sint64">'
            '  <VALUE>42</VALUE>'
            '</QUALIFIER>',
            exp_result=CIMQualifier(
                'Qual', value=42, type='sint64',
                **qualifier_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER with sint64 typed array value (empty)",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="sint64">'
            '  <VALUE.ARRAY/>'
            '</QUALIFIER>',
            exp_result=CIMQualifier(
                'Qual', value=[], type='sint64',
                **qualifier_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER with real32 typed value None",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="real32"/>',
            exp_result=CIMQualifier(
                'Qual', value=None, type='real32',
                **qualifier_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER with real32 typed simple value",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="real32">'
            '  <VALUE>42</VALUE>'
            '</QUALIFIER>',
            exp_result=CIMQualifier(
                'Qual', value=42.0, type='real32',
                **qualifier_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER with real32 typed array value (empty)",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="real32">'
            '  <VALUE.ARRAY/>'
            '</QUALIFIER>',
            exp_result=CIMQualifier(
                'Qual', value=[], type='real32',
                **qualifier_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER with real64 typed value None",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="real64"/>',
            exp_result=CIMQualifier(
                'Qual', value=None, type='real64',
                **qualifier_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER with real64 typed simple value",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="real64">'
            '  <VALUE>42</VALUE>'
            '</QUALIFIER>',
            exp_result=CIMQualifier(
                'Qual', value=42.0, type='real64',
                **qualifier_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER with real64 typed array value (empty)",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="real64">'
            '  <VALUE.ARRAY/>'
            '</QUALIFIER>',
            exp_result=CIMQualifier(
                'Qual', value=[], type='real64',
                **qualifier_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER with datetime typed value None",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="datetime"/>',
            exp_result=CIMQualifier(
                'Qual', value=None, type='datetime',
                **qualifier_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER with datetime typed simple value",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="datetime">'
            '  <VALUE>20140924193040.654321+120</VALUE>'
            '</QUALIFIER>',
            exp_result=CIMQualifier(
                'Qual', value='20140924193040.654321+120', type='datetime',
                **qualifier_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER with datetime typed array value (empty)",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="datetime">'
            '  <VALUE.ARRAY/>'
            '</QUALIFIER>',
            exp_result=CIMQualifier(
                'Qual', value=[], type='datetime',
                **qualifier_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER with reference typed value None",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="reference"/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "QUALIFIER with reference typed simple value 'foo'",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="reference">'
            '  <VALUE>foo</VALUE>'
            '</QUALIFIER>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),

    # QUALIFIER.DECLARATION tests:
    #
    #   <!ELEMENT QUALIFIER.DECLARATION (SCOPE?, (VALUE | VALUE.ARRAY)?)>
    #   <!ATTLIST QUALIFIER.DECLARATION
    #       %CIMName;
    #       %CIMType;               #REQUIRED
    #       ISARRAY    (true|false) #IMPLIED
    #       %ArraySize;
    #       %QualifierFlavor;>
    (
        "QUALIFIER.DECLARATION with invalid child element",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="string">'
            '  <XXX/>'
            '</QUALIFIER.DECLARATION>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "QUALIFIER.DECLARATION with invalid text content",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="string">'
            '  xxx'
            '</QUALIFIER.DECLARATION>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "QUALIFIER.DECLARATION with invalid attribute",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="string" XXX="bla"/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "QUALIFIER.DECLARATION with invalid ISARRAY attribute",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="string"'
            ' ISARRAY="xxx"/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "QUALIFIER.DECLARATION with invalid OVERRIDABLE attribute",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="string"'
            ' OVERRIDABLE="xxx"/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "QUALIFIER.DECLARATION with invalid TOSUBCLASS attribute",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="string"'
            ' TOSUBCLASS="xxx"/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "QUALIFIER.DECLARATION with invalid TOINSTANCE attribute",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="string"'
            ' TOINSTANCE="xxx"/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "QUALIFIER.DECLARATION with invalid TRANSLATABLE attribute",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="string"'
            ' TRANSLATABLE="xxx"/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "QUALIFIER.DECLARATION with missing required attribute NAME",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION TYPE="string"/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "QUALIFIER.DECLARATION with two VALUE children (invalid)",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="boolean">'
            '  <VALUE>true</VALUE>'
            '  <VALUE>true</VALUE>'
            '</QUALIFIER.DECLARATION>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "QUALIFIER.DECLARATION with two VALUE.ARRAY children (invalid)",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="boolean" ISARRAY="true">'
            '  <VALUE.ARRAY/>'
            '  <VALUE.ARRAY/>'
            '</QUALIFIER.DECLARATION>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "QUALIFIER.DECLARATION with NAME using ASCII characters",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="string"/>',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=None, type='string',
                **qualifier_declaration_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with NAME using non-ASCII UCS-2 characters",
        dict(
            xml_str=b''
            b'<QUALIFIER.DECLARATION NAME="Qual\xC3\xA9" TYPE="string"/>',
            exp_result=CIMQualifierDeclaration(
                u'Qual\u00E9', value=None, type='string',
                **qualifier_declaration_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with NAME using non-UCS-2 characters",
        dict(
            xml_str=b''
            b'<QUALIFIER.DECLARATION NAME="Qual\xF0\x90\x85\x82"'
            b' TYPE="string"/>',
            exp_result=CIMQualifierDeclaration(
                u'Qual\U00010142', value=None, type='string',
                **qualifier_declaration_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION fixed array",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="string" ARRAYSIZE="10"'
            ' ISARRAY="true"/>',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=None, type='string',
                is_array=True, array_size=10,
                **qualifier_declaration_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION array value with ISARRAY=True",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="string"'
            ' ISARRAY="True"/>',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=None, type='string', is_array=True,
                **qualifier_declaration_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION simple value with explicit ISARRAY=False",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="string"'
            ' ISARRAY="False"/>',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=None, type='string', is_array=False,
                **qualifier_declaration_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION simple value without ISARRAY (default False)",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="string"/>',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=None, type='string', is_array=False,
                **qualifier_declaration_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with OVERRIDABLE attribute (true)",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="string"'
            ' OVERRIDABLE="true"/>',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=None, type='string',
                **qualifier_declaration_default_attrs(overridable=True)
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with OVERRIDABLE attribute (TrUe)",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="string"'
            ' OVERRIDABLE="TrUe"/>',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=None, type='string',
                **qualifier_declaration_default_attrs(overridable=True)
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with OVERRIDABLE attribute (false)",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="string"'
            ' OVERRIDABLE="false"/>',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=None, type='string',
                **qualifier_declaration_default_attrs(overridable=False)
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with OVERRIDABLE attribute (FaLsE)",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="string"'
            ' OVERRIDABLE="FaLsE"/>',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=None, type='string',
                **qualifier_declaration_default_attrs(overridable=False)
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with TOSUBCLASS attribute (true)",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="string"'
            ' TOSUBCLASS="true"/>',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=None, type='string',
                **qualifier_declaration_default_attrs(tosubclass=True)
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with TOSUBCLASS attribute (TrUe)",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="string"'
            ' TOSUBCLASS="TrUe"/>',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=None, type='string',
                **qualifier_declaration_default_attrs(tosubclass=True)
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with TOSUBCLASS attribute (false)",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="string"'
            ' TOSUBCLASS="false"/>',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=None, type='string',
                **qualifier_declaration_default_attrs(tosubclass=False)
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with TOSUBCLASS attribute (FaLsE)",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="string"'
            ' TOSUBCLASS="FaLsE"/>',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=None, type='string',
                **qualifier_declaration_default_attrs(tosubclass=False)
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with TOINSTANCE attribute (true)",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="string"'
            ' TOINSTANCE="true"/>',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=None, type='string',
                **qualifier_declaration_default_attrs(toinstance=True)
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with TOINSTANCE attribute (TrUe)",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="string"'
            ' TOINSTANCE="TrUe"/>',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=None, type='string',
                **qualifier_declaration_default_attrs(toinstance=True)
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with TOINSTANCE attribute (false)",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="string"'
            ' TOINSTANCE="false"/>',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=None, type='string',
                **qualifier_declaration_default_attrs(toinstance=False)
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with TOINSTANCE attribute (FaLsE)",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="string"'
            ' TOINSTANCE="FaLsE"/>',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=None, type='string',
                **qualifier_declaration_default_attrs(toinstance=False)
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with TRANSLATABLE attribute (true)",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="string"'
            ' TRANSLATABLE="true"/>',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=None, type='string',
                **qualifier_declaration_default_attrs(translatable=True)
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with TRANSLATABLE attribute (TrUe)",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="string"'
            ' TRANSLATABLE="TrUe"/>',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=None, type='string',
                **qualifier_declaration_default_attrs(translatable=True)
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with TRANSLATABLE attribute (false)",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="string"'
            ' TRANSLATABLE="false"/>',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=None, type='string',
                **qualifier_declaration_default_attrs(translatable=False)
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with TRANSLATABLE attribute (FaLsE)",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="string"'
            ' TRANSLATABLE="FaLsE"/>',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=None, type='string',
                **qualifier_declaration_default_attrs(translatable=False)
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with missing required attribute TYPE",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual"/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "QUALIFIER.DECLARATION with invalid TYPE 'foo'",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="foo"/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "QUALIFIER.DECLARATION with boolean typed default value None",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="boolean"/>',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=None, type='boolean',
                **qualifier_declaration_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with boolean typed simple default value",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="boolean">'
            '  <VALUE>true</VALUE>'
            '</QUALIFIER.DECLARATION>',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=True, type='boolean',
                **qualifier_declaration_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with boolean typed simple default value 'foo' "
        "(invalid)",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="boolean">'
            '  <VALUE>foo</VALUE>'
            '</QUALIFIER.DECLARATION>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "QUALIFIER.DECLARATION with boolean typed array default value None",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="boolean" ISARRAY="true">'
            '</QUALIFIER.DECLARATION>',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=None, type='boolean', is_array=True,
                **qualifier_declaration_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with boolean typed array default value (empty)",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="boolean" ISARRAY="true">'
            '  <VALUE.ARRAY/>'
            '</QUALIFIER.DECLARATION>',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=[], type='boolean', is_array=True,
                **qualifier_declaration_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with string typed default value None",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="string"/>',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=None, type='string',
                **qualifier_declaration_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with string typed simple default value",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="string">'
            '  <VALUE>abc</VALUE>'
            '</QUALIFIER.DECLARATION>',
            exp_result=CIMQualifierDeclaration(
                'Qual', value='abc', type='string',
                **qualifier_declaration_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with string typed array default value (empty)",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="string" ISARRAY="true">'
            '  <VALUE.ARRAY/>'
            '</QUALIFIER.DECLARATION>',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=[], type='string', is_array=True,
                **qualifier_declaration_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with string typed array default value None",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="string" ISARRAY="true"/>',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=None, type='string', is_array=True,
                **qualifier_declaration_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with char16 typed default value None",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="char16"/>',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=None, type='char16',
                **qualifier_declaration_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with char16 typed simple default value",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="char16">'
            '  <VALUE>a</VALUE>'
            '</QUALIFIER.DECLARATION>',
            exp_result=CIMQualifierDeclaration(
                'Qual', value='a', type='char16',
                **qualifier_declaration_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with char16 typed simple default value 'foo' "
        "(invalid)",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="char16">'
            '  <VALUE>foo</VALUE>'
            '</QUALIFIER.DECLARATION>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "QUALIFIER.DECLARATION with char16 typed array default value None",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="char16" ISARRAY="true"/>',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=None, type='char16', is_array=True,
                **qualifier_declaration_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with char16 typed array default value (empty)",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="char16" ISARRAY="true">'
            '  <VALUE.ARRAY/>'
            '</QUALIFIER.DECLARATION>',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=[], type='char16', is_array=True,
                **qualifier_declaration_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with uint8 typed default value None",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="uint8"/>',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=None, type='uint8',
                **qualifier_declaration_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with uint8 typed simple default value",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="uint8">'
            '  <VALUE>42</VALUE>'
            '</QUALIFIER.DECLARATION>',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=42, type='uint8',
                **qualifier_declaration_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with uint8 typed simple default value 'foo' "
        "(invalid)",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="uint8">'
            '  <VALUE>foo</VALUE>'
            '</QUALIFIER.DECLARATION>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "QUALIFIER.DECLARATION with uint8 typed array default value None",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="uint8" ISARRAY="true"/>',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=None, type='uint8', is_array=True,
                **qualifier_declaration_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with uint8 typed array default value (empty)",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="uint8" ISARRAY="true">'
            '  <VALUE.ARRAY/>'
            '</QUALIFIER.DECLARATION>',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=[], type='uint8', is_array=True,
                **qualifier_declaration_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with uint16 typed default value None",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="uint16"/>',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=None, type='uint16',
                **qualifier_declaration_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with uint16 typed simple default value",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="uint16">'
            '  <VALUE>42</VALUE>'
            '</QUALIFIER.DECLARATION>',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=42, type='uint16',
                **qualifier_declaration_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with uint16 typed simple default value 'foo' "
        "(invalid)",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="uint16">'
            '  <VALUE>foo</VALUE>'
            '</QUALIFIER.DECLARATION>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "QUALIFIER.DECLARATION with uint16 typed array default value None",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="uint16" ISARRAY="true"/>',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=None, type='uint16', is_array=True,
                **qualifier_declaration_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with uint16 typed array default value (empty)",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="uint16" ISARRAY="true">'
            '  <VALUE.ARRAY/>'
            '</QUALIFIER.DECLARATION>',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=[], type='uint16', is_array=True,
                **qualifier_declaration_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with uint32 typed default value None",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="uint32"/>',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=None, type='uint32',
                **qualifier_declaration_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with uint32 typed simple default value",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="uint32">'
            '  <VALUE>42</VALUE>'
            '</QUALIFIER.DECLARATION>',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=42, type='uint32',
                **qualifier_declaration_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with uint32 typed simple default value 'foo' "
        "(invalid)",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="uint32">'
            '  <VALUE>foo</VALUE>'
            '</QUALIFIER.DECLARATION>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "QUALIFIER.DECLARATION with uint32 typed array default value None",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="uint32" ISARRAY="true"/>',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=None, type='uint32', is_array=True,
                **qualifier_declaration_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with uint32 typed array default value (empty)",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="uint32" ISARRAY="true">'
            '  <VALUE.ARRAY/>'
            '</QUALIFIER.DECLARATION>',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=[], type='uint32', is_array=True,
                **qualifier_declaration_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with uint64 typed default value None",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="uint64"/>',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=None, type='uint64',
                **qualifier_declaration_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with uint64 typed simple default alue",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="uint64">'
            '  <VALUE>42</VALUE>'
            '</QUALIFIER.DECLARATION>',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=42, type='uint64',
                **qualifier_declaration_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with uint64 typed simple default value 'foo' "
        "(invalid)",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="uint64">'
            '  <VALUE>foo</VALUE>'
            '</QUALIFIER.DECLARATION>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "QUALIFIER.DECLARATION with uint64 typed array default value None",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="uint64" ISARRAY="true"/>',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=None, type='uint64', is_array=True,
                **qualifier_declaration_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with uint64 typed array default value (empty)",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="uint64" ISARRAY="true">'
            '  <VALUE.ARRAY/>'
            '</QUALIFIER.DECLARATION>',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=[], type='uint64', is_array=True,
                **qualifier_declaration_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with sint8 typed default value None",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="sint8"/>',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=None, type='sint8',
                **qualifier_declaration_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with sint8 typed simple default value",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="sint8">'
            '  <VALUE>42</VALUE>'
            '</QUALIFIER.DECLARATION>',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=42, type='sint8',
                **qualifier_declaration_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with sint8 typed simple default value 'foo' "
        "(invalid)",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="sint8">'
            '  <VALUE>foo</VALUE>'
            '</QUALIFIER.DECLARATION>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "QUALIFIER.DECLARATION with sint8 typed array default value None",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="sint8" ISARRAY="true"/>',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=None, type='sint8', is_array=True,
                **qualifier_declaration_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with sint8 typed array default value (empty)",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="sint8" ISARRAY="true">'
            '  <VALUE.ARRAY/>'
            '</QUALIFIER.DECLARATION>',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=[], type='sint8', is_array=True,
                **qualifier_declaration_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with sint16 typed default value None",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="sint16"/>',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=None, type='sint16',
                **qualifier_declaration_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with sint16 typed simple default value",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="sint16">'
            '  <VALUE>42</VALUE>'
            '</QUALIFIER.DECLARATION>',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=42, type='sint16',
                **qualifier_declaration_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with sint16 typed simple default value 'foo' "
        "(invalid)",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="sint16">'
            '  <VALUE>foo</VALUE>'
            '</QUALIFIER.DECLARATION>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "QUALIFIER.DECLARATION with sint16 typed array default value None",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="sint16" ISARRAY="true"/>',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=None, type='sint16', is_array=True,
                **qualifier_declaration_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with sint16 typed array default value (empty)",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="sint16" ISARRAY="true">'
            '  <VALUE.ARRAY/>'
            '</QUALIFIER.DECLARATION>',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=[], type='sint16', is_array=True,
                **qualifier_declaration_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with sint32 typed default value None",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="sint32"/>',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=None, type='sint32',
                **qualifier_declaration_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with sint32 typed simple default value",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="sint32">'
            '  <VALUE>42</VALUE>'
            '</QUALIFIER.DECLARATION>',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=42, type='sint32',
                **qualifier_declaration_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with sint32 typed simple default value 'foo' "
        "(invalid)",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="sint32">'
            '  <VALUE>foo</VALUE>'
            '</QUALIFIER.DECLARATION>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "QUALIFIER.DECLARATION with sint32 typed array default value None",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="sint32" ISARRAY="true"/>',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=None, type='sint32', is_array=True,
                **qualifier_declaration_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with sint32 typed array default value (empty)",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="sint32" ISARRAY="true">'
            '  <VALUE.ARRAY/>'
            '</QUALIFIER.DECLARATION>',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=[], type='sint32', is_array=True,
                **qualifier_declaration_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with sint64 typed default value None",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="sint64"/>',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=None, type='sint64',
                **qualifier_declaration_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with sint64 typed simple default value",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="sint64">'
            '  <VALUE>42</VALUE>'
            '</QUALIFIER.DECLARATION>',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=42, type='sint64',
                **qualifier_declaration_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with sint64 typed simple default value 'foo' "
        "(invalid)",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="sint64">'
            '  <VALUE>foo</VALUE>'
            '</QUALIFIER.DECLARATION>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "QUALIFIER.DECLARATION with sint64 typed array default value None",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="sint64" ISARRAY="true"/>',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=None, type='sint64', is_array=True,
                **qualifier_declaration_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with sint64 typed array default value (empty)",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="sint64" ISARRAY="true">'
            '  <VALUE.ARRAY/>'
            '</QUALIFIER.DECLARATION>',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=[], type='sint64', is_array=True,
                **qualifier_declaration_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with real32 typed default value None",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="real32"/>',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=None, type='real32',
                **qualifier_declaration_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with real32 typed simple default value",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="real32">'
            '  <VALUE>42</VALUE>'
            '</QUALIFIER.DECLARATION>',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=42.0, type='real32',
                **qualifier_declaration_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with real32 typed simple default value 'foo' "
        "(invalid)",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="real32">'
            '  <VALUE>foo</VALUE>'
            '</QUALIFIER.DECLARATION>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "QUALIFIER.DECLARATION with real32 typed array default value None",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="real32" ISARRAY="true"/>',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=None, type='real32', is_array=True,
                **qualifier_declaration_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with real32 typed array default value (empty)",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="real32" ISARRAY="true">'
            '  <VALUE.ARRAY/>'
            '</QUALIFIER.DECLARATION>',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=[], type='real32', is_array=True,
                **qualifier_declaration_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with real64 typed default value None",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="real64"/>',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=None, type='real64',
                **qualifier_declaration_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with real64 typed simple default value",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="real64">'
            '  <VALUE>42</VALUE>'
            '</QUALIFIER.DECLARATION>',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=42.0, type='real64',
                **qualifier_declaration_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with real64 typed simple default value 'foo' "
        "(invalid)",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="real64">'
            '  <VALUE>foo</VALUE>'
            '</QUALIFIER.DECLARATION>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "QUALIFIER.DECLARATION with real64 typed array default value None",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="real64" ISARRAY="true"/>',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=None, type='real64', is_array=True,
                **qualifier_declaration_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with real64 typed array default value (empty)",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="real64" ISARRAY="true">'
            '  <VALUE.ARRAY/>'
            '</QUALIFIER.DECLARATION>',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=[], type='real64', is_array=True,
                **qualifier_declaration_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with datetime typed default value None",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="datetime"/>',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=None, type='datetime',
                **qualifier_declaration_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with datetime typed simple default value",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="datetime">'
            '  <VALUE>20140924193040.654321+120</VALUE>'
            '</QUALIFIER.DECLARATION>',
            exp_result=CIMQualifierDeclaration(
                'Qual', value='20140924193040.654321+120', type='datetime',
                **qualifier_declaration_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with datetime typed simple default value 'foo' "
        "(invalid)",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="datetime">'
            '  <VALUE>foo</VALUE>'
            '</QUALIFIER.DECLARATION>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "QUALIFIER.DECLARATION with datetime typed array default value None",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="datetime"'
            ' ISARRAY="true"/>',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=None, type='datetime', is_array=True,
                **qualifier_declaration_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with datetime typed array default value (empty)",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="datetime" ISARRAY="true">'
            '  <VALUE.ARRAY/>'
            '</QUALIFIER.DECLARATION>',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=[], type='datetime', is_array=True,
                **qualifier_declaration_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with reference typed default value None "
        "(invalid type)",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="reference"/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "QUALIFIER.DECLARATION with reference typed simple default value 'foo' "
        "(invalid type)",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="reference">'
            '  <VALUE>foo</VALUE>'
            '</QUALIFIER.DECLARATION>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "QUALIFIER.DECLARATION with empty SCOPE",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="string">'
            '  <SCOPE/>'
            '</QUALIFIER.DECLARATION>',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=None, type='string',
                **qualifier_declaration_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with class SCOPE",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="string">'
            '  <SCOPE CLASS="true"/>'
            '</QUALIFIER.DECLARATION>',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=None, type='string',
                scopes={'CLASS': True},
                **qualifier_declaration_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with two SCOPE children (invalid)",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="string">'
            '  <SCOPE/>'
            '  <SCOPE/>'
            '</QUALIFIER.DECLARATION>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),

    # MESSAGE tests:
    #
    #   <!ELEMENT MESSAGE (SIMPLEREQ | MULTIREQ | SIMPLERSP | MULTIRSP |
    #                      SIMPLEEXPREQ | MULTIEXPREQ | SIMPLEEXPRSP |
    #                      MULTIEXPRSP)
    #   <!ATTLIST MESSAGE
    #       ID CDATA #REQUIRED
    #       PROTOCOLVERSION CDATA #REQUIRED>
    (
        "MESSAGE with invalid child element",
        dict(
            xml_str=''
            '<MESSAGE ID="42" PROTOCOLVERSION="1.4" XXX="bla">'
            '  <SIMPLEREQ>'
            '    <IMETHODCALL NAME="M1">'
            '      <LOCALNAMESPACEPATH>'
            '        <NAMESPACE NAME="foo"/>'
            '      </LOCALNAMESPACEPATH>'
            '    </IMETHODCALL>'
            '  </SIMPLEREQ>'
            '  <XXX/>'
            '</MESSAGE>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "MESSAGE with invalid attribute",
        dict(
            xml_str=''
            '<MESSAGE ID="42" PROTOCOLVERSION="1.4" XXX="bla">'
            '  <SIMPLEREQ>'
            '    <IMETHODCALL NAME="M1">'
            '      <LOCALNAMESPACEPATH>'
            '        <NAMESPACE NAME="foo"/>'
            '      </LOCALNAMESPACEPATH>'
            '    </IMETHODCALL>'
            '  </SIMPLEREQ>'
            '</MESSAGE>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "MESSAGE with missing attribute ID (invalid)",
        dict(
            xml_str=''
            '<MESSAGE PROTOCOLVERSION="1.4">'
            '  <SIMPLEREQ>'
            '    <IMETHODCALL NAME="M1">'
            '      <LOCALNAMESPACEPATH>'
            '        <NAMESPACE NAME="foo"/>'
            '      </LOCALNAMESPACEPATH>'
            '    </IMETHODCALL>'
            '  </SIMPLEREQ>'
            '</MESSAGE>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "MESSAGE with missing attribute PROTOCOLVERSION (invalid)",
        dict(
            xml_str=''
            '<MESSAGE ID="42">'
            '  <SIMPLEREQ>'
            '    <IMETHODCALL NAME="M1">'
            '      <LOCALNAMESPACEPATH>'
            '        <NAMESPACE NAME="foo"/>'
            '      </LOCALNAMESPACEPATH>'
            '    </IMETHODCALL>'
            '  </SIMPLEREQ>'
            '</MESSAGE>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "MESSAGE with PROTOCOLVERSION version 'foo' (invalid)",
        dict(
            xml_str=''
            '<MESSAGE ID="42" PROTOCOLVERSION="foo">'
            '  <SIMPLEREQ>'
            '    <IMETHODCALL NAME="M1">'
            '      <LOCALNAMESPACEPATH>'
            '        <NAMESPACE NAME="foo"/>'
            '      </LOCALNAMESPACEPATH>'
            '    </IMETHODCALL>'
            '  </SIMPLEREQ>'
            '</MESSAGE>',
            exp_result=None,
        ),
        ProtocolVersionError, None, True
    ),
    (
        "MESSAGE with PROTOCOLVERSION version '2.4' (invalid)",
        dict(
            xml_str=''
            '<MESSAGE ID="42" PROTOCOLVERSION="2.4">'
            '  <SIMPLEREQ>'
            '    <IMETHODCALL NAME="M1">'
            '      <LOCALNAMESPACEPATH>'
            '        <NAMESPACE NAME="foo"/>'
            '      </LOCALNAMESPACEPATH>'
            '    </IMETHODCALL>'
            '  </SIMPLEREQ>'
            '</MESSAGE>',
            exp_result=None,
        ),
        ProtocolVersionError, None, True
    ),
    (
        "MESSAGE with missing child (invalid)",
        dict(
            xml_str=''
            '<MESSAGE ID="42" PROTOCOLVERSION="1.4">'
            '</MESSAGE>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "MESSAGE with SIMPLEREQ child element",
        dict(
            xml_str=''
            '<MESSAGE ID="42" PROTOCOLVERSION="1.4">'
            '  <SIMPLEREQ>'
            '    <IMETHODCALL NAME="M1">'
            '      <LOCALNAMESPACEPATH>'
            '        <NAMESPACE NAME="foo"/>'
            '      </LOCALNAMESPACEPATH>'
            '    </IMETHODCALL>'
            '  </SIMPLEREQ>'
            '</MESSAGE>',
            exp_result=(
                u'MESSAGE',
                {u'ID': u'42', u'PROTOCOLVERSION': u'1.4'},
                (
                    u'SIMPLEREQ',
                    {},
                    (
                        u'IMETHODCALL', {u'NAME': u'M1'}, u'foo', []
                    ),
                ),
            ),
        ),
        None, None, True
    ),
    (
        "MESSAGE with two SIMPLEREQ child elements (invalid)",
        dict(
            xml_str=''
            '<MESSAGE ID="42" PROTOCOLVERSION="1.4">'
            '  <SIMPLEREQ>'
            '    <IMETHODCALL NAME="M1">'
            '      <LOCALNAMESPACEPATH>'
            '        <NAMESPACE NAME="foo"/>'
            '      </LOCALNAMESPACEPATH>'
            '    </IMETHODCALL>'
            '  </SIMPLEREQ>'
            '  <SIMPLEREQ>'
            '    <IMETHODCALL NAME="M2">'
            '      <LOCALNAMESPACEPATH>'
            '        <NAMESPACE NAME="foo"/>'
            '      </LOCALNAMESPACEPATH>'
            '    </IMETHODCALL>'
            '  </SIMPLEREQ>'
            '</MESSAGE>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "MESSAGE with SIMPLERSP child element",
        dict(
            xml_str=''
            '<MESSAGE ID="42" PROTOCOLVERSION="1.4">'
            '  <SIMPLERSP>'
            '    <IMETHODRESPONSE NAME="M1">'
            '      <IRETURNVALUE/>'
            '    </IMETHODRESPONSE>'
            '  </SIMPLERSP>'
            '</MESSAGE>',
            exp_result=(
                u'MESSAGE',
                {u'ID': u'42', u'PROTOCOLVERSION': u'1.4'},
                (
                    u'SIMPLERSP',
                    {},
                    (
                        'IMETHODRESPONSE', {'NAME': 'M1'},
                        [
                            ('IRETURNVALUE', {}, []),
                        ],
                    ),
                ),
            ),
        ),
        None, None, True
    ),
    (
        "MESSAGE with two SIMPLERSP child elements (invalid)",
        dict(
            xml_str=''
            '<MESSAGE ID="42" PROTOCOLVERSION="1.4">'
            '  <SIMPLERSP>'
            '    <IMETHODRESPONSE NAME="M1">'
            '      <IRETURNVALUE/>'
            '    </IMETHODRESPONSE>'
            '  </SIMPLERSP>'
            '  <SIMPLERSP>'
            '    <IMETHODRESPONSE NAME="M2">'
            '      <IRETURNVALUE/>'
            '    </IMETHODRESPONSE>'
            '  </SIMPLERSP>'
            '</MESSAGE>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "MESSAGE with SIMPLEEXPREQ child element",
        dict(
            xml_str=''
            '<MESSAGE ID="42" PROTOCOLVERSION="1.4">'
            '  <SIMPLEEXPREQ>'
            '    <EXPMETHODCALL NAME="M1"/>'
            '  </SIMPLEEXPREQ>'
            '</MESSAGE>',
            exp_result=(
                u'MESSAGE',
                {u'ID': u'42', u'PROTOCOLVERSION': u'1.4'},
                (
                    u'SIMPLEEXPREQ',
                    {},
                    (u'EXPMETHODCALL', {u'NAME': u'M1'}, []),
                ),
            ),
        ),
        None, None, True
    ),
    (
        "MESSAGE with two SIMPLEEXPREQ child elements (invalid)",
        dict(
            xml_str=''
            '<MESSAGE ID="42" PROTOCOLVERSION="1.4">'
            '  <SIMPLEEXPREQ>'
            '    <EXPMETHODCALL NAME="M1"/>'
            '  </SIMPLEEXPREQ>'
            '  <SIMPLEEXPREQ>'
            '    <EXPMETHODCALL NAME="M2"/>'
            '  </SIMPLEEXPREQ>'
            '</MESSAGE>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "MESSAGE with MULTIREQ child element (not implemented)",
        dict(
            xml_str=''
            '<MESSAGE ID="42" PROTOCOLVERSION="1.4">'
            '  <MULTIREQ/>'
            '</MESSAGE>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "MESSAGE with MULTIRSP child element (not implemented)",
        dict(
            xml_str=''
            '<MESSAGE ID="42" PROTOCOLVERSION="1.4">'
            '  <MULTIRSP/>'
            '</MESSAGE>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "MESSAGE with MULTIEXPREQ child element (not implemented)",
        dict(
            xml_str=''
            '<MESSAGE ID="42" PROTOCOLVERSION="1.4">'
            '  <MULTIEXPREQ/>'
            '</MESSAGE>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "MESSAGE with MULTIEXPRSP child element (not implemented)",
        dict(
            xml_str=''
            '<MESSAGE ID="42" PROTOCOLVERSION="1.4">'
            '  <MULTIEXPRSP/>'
            '</MESSAGE>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "MESSAGE with SIMPLEEXPRSP child element (not implemented)",
        dict(
            xml_str=''
            '<MESSAGE ID="42" PROTOCOLVERSION="1.4">'
            '  <SIMPLEEXPRSP/>'
            '</MESSAGE>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),

    # SIMPLEREQ tests:
    #
    #   <!ELEMENT SIMPLEREQ (IMETHODCALL | METHODCALL)>
    (
        "SIMPLEREQ with invalid child element",
        dict(
            xml_str=''
            '<SIMPLEREQ>'
            '  <XXX/>'
            '</SIMPLEREQ>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "SIMPLEREQ with invalid attribute",
        dict(
            xml_str=''
            '<SIMPLEREQ XXX="bla">'
            '  <IMETHODCALL NAME="M1">'
            '    <LOCALNAMESPACEPATH>'
            '      <NAMESPACE NAME="foo"/>'
            '    </LOCALNAMESPACEPATH>'
            '  </IMETHODCALL>'
            '</SIMPLEREQ>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "SIMPLEREQ with missing child (invalid)",
        dict(
            xml_str=''
            '<SIMPLEREQ>'
            '</SIMPLEREQ>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "SIMPLEREQ with minimal child elements",
        dict(
            xml_str=''
            '<SIMPLEREQ>'
            '  <IMETHODCALL NAME="M1">'
            '    <LOCALNAMESPACEPATH>'
            '      <NAMESPACE NAME="foo"/>'
            '    </LOCALNAMESPACEPATH>'
            '  </IMETHODCALL>'
            '</SIMPLEREQ>',
            exp_result=(
                u'SIMPLEREQ',
                {},
                (u'IMETHODCALL', {u'NAME': u'M1'}, u'foo', []),
            ),
        ),
        None, None, True
    ),
    (
        "SIMPLEREQ of GetClass Request",
        dict(
            xml_str=''
            '<SIMPLEREQ>'
            '  <IMETHODCALL NAME="GetClass">'
            '    <LOCALNAMESPACEPATH>'
            '      <NAMESPACE NAME="root"/>'
            '      <NAMESPACE NAME="cimv2"/>'
            '    </LOCALNAMESPACEPATH>'
            '    <IPARAMVALUE NAME="ClassName">'
            '      <CLASSNAME NAME="CIM_ComputerSystem"/>'
            '    </IPARAMVALUE>'
            '    <IPARAMVALUE NAME="PropertyList">'
            '      <VALUE.ARRAY>'
            '        <VALUE>PowerManagementCapabilities</VALUE>'
            '      </VALUE.ARRAY>'
            '    </IPARAMVALUE>'
            '    <IPARAMVALUE NAME="LocalOnly">'
            '      <VALUE>FALSE</VALUE>'
            '    </IPARAMVALUE>'
            '  </IMETHODCALL>'
            '</SIMPLEREQ>',
            exp_result=(u'SIMPLEREQ',
                        {},
                        (u'IMETHODCALL',
                         {u'NAME': u'GetClass'},
                         u'root/cimv2',
                         [(u'ClassName',
                           CIMClassName(classname='CIM_ComputerSystem',
                                        namespace=None, host=None)),
                          (u'PropertyList', [u'PowerManagementCapabilities']),
                          (u'LocalOnly', False)])),
        ),
        None, None, True
    ),
    (
        "SIMPLEREQ with two IMETHODCALL children (invalid)",
        dict(
            xml_str=''
            '<SIMPLEREQ>'
            '  <IMETHODCALL NAME="GetClass">'
            '    <LOCALNAMESPACEPATH>'
            '      <NAMESPACE NAME="root"/>'
            '      <NAMESPACE NAME="cimv2"/>'
            '    </LOCALNAMESPACEPATH>'
            '    <IPARAMVALUE NAME="ClassName">'
            '      <CLASSNAME NAME="CIM_ComputerSystem"/>'
            '    </IPARAMVALUE>'
            '    <IPARAMVALUE NAME="PropertyList">'
            '      <VALUE.ARRAY>'
            '        <VALUE>PowerManagementCapabilities</VALUE>'
            '      </VALUE.ARRAY>'
            '    </IPARAMVALUE>'
            '    <IPARAMVALUE NAME="LocalOnly">'
            '      <VALUE>FALSE</VALUE>'
            '    </IPARAMVALUE>'
            '  </IMETHODCALL>'
            '  <IMETHODCALL NAME="GetClass">'
            '    <LOCALNAMESPACEPATH>'
            '      <NAMESPACE NAME="root"/>'
            '      <NAMESPACE NAME="cimv2"/>'
            '    </LOCALNAMESPACEPATH>'
            '    <IPARAMVALUE NAME="ClassName">'
            '      <CLASSNAME NAME="CIM_ComputerSystem"/>'
            '    </IPARAMVALUE>'
            '    <IPARAMVALUE NAME="PropertyList">'
            '      <VALUE.ARRAY>'
            '        <VALUE>PowerManagementCapabilities</VALUE>'
            '      </VALUE.ARRAY>'
            '    </IPARAMVALUE>'
            '    <IPARAMVALUE NAME="LocalOnly">'
            '      <VALUE>FALSE</VALUE>'
            '    </IPARAMVALUE>'
            '  </IMETHODCALL>'
            '</SIMPLEREQ>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "SIMPLEREQ invalid, BLAHBLAH for IMETHODCALL (mismatched tag)",
        dict(
            xml_str=''
            '<SIMPLEREQ><BLAHBLAH NAME="GetClass">'
            '<LOCALNAMESPACEPATH><NAMESPACE NAME="root"/>'
            '<NAMESPACE NAME="cimv2"/></LOCALNAMESPACEPATH>'
            '<IPARAMVALUE NAME="ClassName">'
            '<CLASSNAME NAME="CIM_ComputerSystem"/>'
            '</IPARAMVALUE>'
            '<IPARAMVALUE NAME="PropertyList">'
            '<VALUE.ARRAY><VALUE>PowerManagementCapabilities</VALUE>'
            '</VALUE.ARRAY>'
            '</IPARAMVALUE><IPARAMVALUE NAME="LocalOnly">'
            '<VALUE>FALSE</VALUE>'
            '</IPARAMVALUE></IMETHODCALL></SIMPLEREQ>',
            exp_result=None,
        ),
        XMLParseError, None, True
    ),

    # SIMPLEEXPREQ tests:
    #
    #   <!ELEMENT SIMPLEEXPREQ (EXPMETHODCALL)>
    (
        "SIMPLEEXPREQ with invalid child element",
        dict(
            xml_str=''
            '<SIMPLEEXPREQ>'
            '  <XXX/>'
            '</SIMPLEEXPREQ>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "SIMPLEEXPREQ with invalid attribute",
        dict(
            xml_str=''
            '<SIMPLEEXPREQ XXX="bla">'
            '  <EXPMETHODCALL NAME="M1">'
            '  </EXPMETHODCALL>'
            '</SIMPLEEXPREQ>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "SIMPLEEXPREQ with missing child (invalid)",
        dict(
            xml_str=''
            '<SIMPLEEXPREQ>'
            '</SIMPLEEXPREQ>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "SIMPLEEXPREQ with minimal child elements",
        dict(
            xml_str=''
            '<SIMPLEEXPREQ>'
            '  <EXPMETHODCALL NAME="M1">'
            '  </EXPMETHODCALL>'
            '</SIMPLEEXPREQ>',
            exp_result=(
                u'SIMPLEEXPREQ',
                {},
                (u'EXPMETHODCALL', {u'NAME': u'M1'}, []),
            ),
        ),
        None, None, True
    ),
    (
        "SIMPLEEXPREQ with two EXPMETHODCALL children (invalid)",
        dict(
            xml_str=''
            '<SIMPLEEXPREQ>'
            '  <EXPMETHODCALL NAME="M1">'
            '  </EXPMETHODCALL>'
            '  <EXPMETHODCALL NAME="M2">'
            '  </EXPMETHODCALL>'
            '</SIMPLEEXPREQ>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),

    # SIMPLERSP tests:
    #
    #   <!ELEMENT SIMPLERSP (METHODRESPONSE | IMETHODRESPONSE)>
    (
        "SIMPLERSP with invalid child element",
        dict(
            xml_str=''
            '<SIMPLERSP>'
            '  <XXX/>'
            '</SIMPLERSP>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "SIMPLERSP with invalid attribute",
        dict(
            xml_str=''
            '<SIMPLERSP XXX="bla">'
            '  <METHODRESPONSE NAME="M1">'
            '  </METHODRESPONSE>'
            '</SIMPLERSP>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "SIMPLERSP with missing child (invalid)",
        dict(
            xml_str=''
            '<SIMPLERSP>'
            '</SIMPLERSP>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "SIMPLERSP with METHODRESPONSE child",
        dict(
            xml_str=''
            '<SIMPLERSP>'
            '  <METHODRESPONSE NAME="M1">'
            '    <RETURNVALUE PARAMTYPE="string"/>'
            '  </METHODRESPONSE>'
            '</SIMPLERSP>',
            exp_result=(
                u'SIMPLERSP',
                {},
                (
                    'METHODRESPONSE', {'NAME': 'M1'},
                    [
                        ('RETURNVALUE', {'PARAMTYPE': 'string'}, None),
                    ],
                ),
            ),
        ),
        None, None, True
    ),
    (
        "SIMPLERSP with two METHODRESPONSE children (invalid)",
        dict(
            xml_str=''
            '<SIMPLERSP>'
            '  <METHODRESPONSE NAME="M1">'
            '    <RETURNVALUE PARAMTYPE="string"/>'
            '  </METHODRESPONSE>'
            '  <METHODRESPONSE NAME="M2">'
            '    <RETURNVALUE PARAMTYPE="string"/>'
            '  </METHODRESPONSE>'
            '</SIMPLERSP>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "SIMPLERSP with IMETHODRESPONSE child",
        dict(
            xml_str=''
            '<SIMPLERSP>'
            '  <IMETHODRESPONSE NAME="M1">'
            '    <IRETURNVALUE/>'
            '  </IMETHODRESPONSE>'
            '</SIMPLERSP>',
            exp_result=(
                u'SIMPLERSP',
                {},
                (
                    'IMETHODRESPONSE', {'NAME': 'M1'},
                    [
                        ('IRETURNVALUE', {}, []),
                    ],
                ),
            ),
        ),
        None, None, True
    ),
    (
        "SIMPLERSP with two IMETHODRESPONSE children (invalid)",
        dict(
            xml_str=''
            '<SIMPLERSP>'
            '  <IMETHODRESPONSE NAME="M1">'
            '    <IRETURNVALUE/>'
            '  </IMETHODRESPONSE>'
            '  <IMETHODRESPONSE NAME="M2">'
            '    <IRETURNVALUE/>'
            '  </IMETHODRESPONSE>'
            '</SIMPLERSP>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),

    # SIMPLEEXPRSP tests: Parsing this element is not implemented
    (
        "SIMPLEEXPRSP (not implemented)",
        dict(
            xml_str=''
            '<SIMPLEEXPRSP/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),

    # MULTIREQ tests: Parsing this element is not implemented
    (
        "MULTIREQ (not implemented)",
        dict(
            xml_str=''
            '<MULTIREQ/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),

    # MULTIEXPREQ tests: Parsing this element is not implemented
    (
        "MULTIEXPREQ (not implemented)",
        dict(
            xml_str=''
            '<MULTIEXPREQ/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),

    # MULTIRSP tests: Parsing this element is not implemented
    (
        "MULTIRSP (not implemented)",
        dict(
            xml_str=''
            '<MULTIRSP/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),

    # MULTIEXPRSP tests: Parsing this element is not implemented
    (
        "MULTIEXPRSP (not implemented)",
        dict(
            xml_str=''
            '<MULTIEXPRSP/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),

    # METHODCALL tests:
    #
    #   <!ELEMENT METHODCALL ((LOCALCLASSPATH | LOCALINSTANCEPATH),
    #                         PARAMVALUE*)>
    #   <!ATTLIST METHODCALL
    #       %CIMName;>
    (
        "METHODCALL with class path and a few parameters",
        dict(
            xml_str=''
            '<METHODCALL NAME="SendTestIndicationsCount">'
            '  <LOCALCLASSPATH>'
            '    <LOCALNAMESPACEPATH>'
            '      <NAMESPACE NAME="test"/>'
            '      <NAMESPACE NAME="TestProvider"/>'
            '    </LOCALNAMESPACEPATH>'
            '    <CLASSNAME NAME="Test_IndicationProviderClass"/>'
            '  </LOCALCLASSPATH>'
            '  <PARAMVALUE NAME="indicationSendCount" PARAMTYPE="uint32">'
            '    <VALUE>0</VALUE>'
            '  </PARAMVALUE>'
            '  <PARAMVALUE NAME="indicationDropCount" PARAMTYPE="uint32">'
            '    <VALUE>42</VALUE>'
            '  </PARAMVALUE>'
            '  <PARAMVALUE NAME="optionalP1"/>'
            '</METHODCALL>',
            exp_result=(u'METHODCALL',
                        {u'NAME': u'SendTestIndicationsCount'},
                        CIMClassName(classname='Test_IndicationProviderClass',
                                     namespace='test/TestProvider', host=None),
                        [(u'indicationSendCount', u'uint32', u'0'),
                         (u'indicationDropCount', u'uint32', u'42'),
                         (u'optionalP1', None, None)]),
        ),
        None, None, True
    ),
    (
        "METHODCALL with LOCALCLASSPATH child element",
        dict(
            xml_str=''
            '<METHODCALL NAME="M1">'
            '  <LOCALCLASSPATH>'
            '    <LOCALNAMESPACEPATH>'
            '      <NAMESPACE NAME="foo"/>'
            '    </LOCALNAMESPACEPATH>'
            '    <CLASSNAME NAME="CIM_Foo"/>'
            '  </LOCALCLASSPATH>'
            '</METHODCALL>',
            exp_result=(
                u'METHODCALL',
                {u'NAME': u'M1'},
                CIMClassName(classname='CIM_Foo', namespace='foo'),
                [],
            ),
        ),
        None, None, True
    ),
    (
        "METHODCALL with two LOCALCLASSPATH child elements (invalid)",
        dict(
            xml_str=''
            '<METHODCALL NAME="M1">'
            '  <LOCALCLASSPATH>'
            '    <LOCALNAMESPACEPATH>'
            '      <NAMESPACE NAME="foo"/>'
            '    </LOCALNAMESPACEPATH>'
            '    <CLASSNAME NAME="CIM_Foo"/>'
            '  </LOCALCLASSPATH>'
            '  <LOCALCLASSPATH>'
            '    <LOCALNAMESPACEPATH>'
            '      <NAMESPACE NAME="foo"/>'
            '    </LOCALNAMESPACEPATH>'
            '    <CLASSNAME NAME="CIM_Bar"/>'
            '  </LOCALCLASSPATH>'
            '</METHODCALL>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "METHODCALL with instance path and a few parameters",
        dict(
            xml_str=''
            '<METHODCALL NAME="SendTestIndicationsCount">'
            '  <LOCALINSTANCEPATH>'
            '    <LOCALNAMESPACEPATH>'
            '      <NAMESPACE NAME="test"/>'
            '      <NAMESPACE NAME="TestProvider"/>'
            '    </LOCALNAMESPACEPATH>'
            '    <INSTANCENAME CLASSNAME="Test_IndicationProviderClass"/>'
            '  </LOCALINSTANCEPATH>'
            '  <PARAMVALUE NAME="indicationSendCount" PARAMTYPE="uint32">'
            '    <VALUE>0</VALUE>'
            '  </PARAMVALUE>'
            '  <PARAMVALUE NAME="indicationDropCount" PARAMTYPE="uint32">'
            '    <VALUE>42</VALUE>'
            '  </PARAMVALUE>'
            '  <PARAMVALUE NAME="optionalP1"/>'
            '</METHODCALL>',
            exp_result=(u'METHODCALL',
                        {u'NAME': u'SendTestIndicationsCount'},
                        CIMInstanceName(
                            classname='Test_IndicationProviderClass',
                            namespace='test/TestProvider', host=None),
                        [(u'indicationSendCount', u'uint32', u'0'),
                         (u'indicationDropCount', u'uint32', u'42'),
                         (u'optionalP1', None, None)]),
        ),
        None, MissingKeybindingsWarning, True
    ),
    (
        "METHODCALL with LOCALINSTANCEPATH child element",
        dict(
            xml_str=''
            '<METHODCALL NAME="M1">'
            '  <LOCALINSTANCEPATH>'
            '    <LOCALNAMESPACEPATH>'
            '      <NAMESPACE NAME="foo"/>'
            '    </LOCALNAMESPACEPATH>'
            '    <INSTANCENAME CLASSNAME="CIM_Foo"/>'
            '  </LOCALINSTANCEPATH>'
            '</METHODCALL>',
            exp_result=(
                u'METHODCALL',
                {u'NAME': u'M1'},
                CIMInstanceName(classname='CIM_Foo', namespace='foo'),
                [],
            ),
        ),
        None, MissingKeybindingsWarning, True
    ),
    (
        "METHODCALL with two LOCALINSTANCEPATH child elements (invalid)",
        dict(
            xml_str=''
            '<METHODCALL NAME="M1">'
            '  <LOCALINSTANCEPATH>'
            '    <LOCALNAMESPACEPATH>'
            '      <NAMESPACE NAME="foo"/>'
            '    </LOCALNAMESPACEPATH>'
            '    <INSTANCENAME CLASSNAME="CIM_Foo"/>'
            '  </LOCALINSTANCEPATH>'
            '  <LOCALINSTANCEPATH>'
            '    <LOCALNAMESPACEPATH>'
            '      <NAMESPACE NAME="foo"/>'
            '    </LOCALNAMESPACEPATH>'
            '    <INSTANCENAME CLASSNAME="CIM_Bar"/>'
            '  </LOCALINSTANCEPATH>'
            '</METHODCALL>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "METHODCALL with missing NAME attribute (invalid)",
        dict(
            xml_str=''
            '<METHODCALL>'
            '  <LOCALCLASSPATH>'
            '    <LOCALNAMESPACEPATH>'
            '      <NAMESPACE NAME="test"/>'
            '      <NAMESPACE NAME="TestProvider"/>'
            '    </LOCALNAMESPACEPATH>'
            '    <CLASSNAME NAME="Test_IndicationProviderClass"/>'
            '  </LOCALCLASSPATH>'
            '  <PARAMVALUE NAME="indicationSendCount" PARAMTYPE="uint32">'
            '    <VALUE>0</VALUE>'
            '  </PARAMVALUE>'
            '  <PARAMVALUE NAME="indicationDropCount" PARAMTYPE="uint32">'
            '    <VALUE>42</VALUE>'
            '  </PARAMVALUE>'
            '  <PARAMVALUE NAME="optionalP1"/>'
            '</METHODCALL>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "METHODCALL with missing path (invalid)",
        dict(
            xml_str=''
            '<METHODCALL NAME="SendTestIndicationsCount">'
            '  <PARAMVALUE NAME="indicationSendCount" PARAMTYPE="uint32">'
            '    <VALUE>0</VALUE>'
            '  </PARAMVALUE>'
            '  <PARAMVALUE NAME="indicationDropCount" PARAMTYPE="uint32">'
            '    <VALUE>42</VALUE>'
            '  </PARAMVALUE>'
            '  <PARAMVALUE NAME="optionalP1"/>'
            '</METHODCALL>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "METHODCALL with IPARMVALUE in place of PARAMVALUE (invalid)",
        dict(
            xml_str=''
            '<METHODCALL NAME="SendTestIndicationsCount">'
            '  <LOCALCLASSPATH>'
            '    <LOCALNAMESPACEPATH>'
            '      <NAMESPACE NAME="test"/>'
            '      <NAMESPACE NAME="TestProvider"/>'
            '    </LOCALNAMESPACEPATH>'
            '    <CLASSNAME NAME="Test_IndicationProviderClass"/>'
            '  </LOCALCLASSPATH>'
            '  <IPARAMVALUE NAME="indicationSendCount" PARAMTYPE="uint32">'
            '    <VALUE>0</VALUE>'
            '  </IPARAMVALUE>'
            '  <PARAMVALUE NAME="indicationDropCount" PARAMTYPE="uint32">'
            '    <VALUE>42</VALUE>'
            '  </PARAMVALUE>'
            '  <PARAMVALUE NAME="optionalP1"/>'
            '</METHODCALL>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),

    # METHODRESPONSE tests:
    #
    #   <!ELEMENT METHODRESPONSE (ERROR | (RETURNVALUE?, PARAMVALUE*))>
    #   <!ATTLIST METHODRESPONSE
    #       %CIMName;>
    (
        "METHODRESPONSE with invalid child element",
        dict(
            xml_str=''
            '<METHODRESPONSE NAME="M1">'
            '  <XXX/>'
            '</METHODRESPONSE>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "METHODRESPONSE with invalid attribute",
        dict(
            xml_str=''
            '<METHODRESPONSE NAME="M1" XXX="bla">'
            '</METHODRESPONSE>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "METHODRESPONSE with missing NAME attribute",
        dict(
            xml_str=''
            '<METHODRESPONSE>'
            '</METHODRESPONSE>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "METHODRESPONSE with ERROR child",
        dict(
            xml_str=''
            '<METHODRESPONSE NAME="M1">'
            '  <ERROR CODE="5"/>'
            '</METHODRESPONSE>',
            exp_result=(
                'METHODRESPONSE', {'NAME': 'M1'},
                [
                    ('ERROR', {'CODE': '5'}, []),
                ],
            ),
        ),
        None, None, True
    ),
    (
        "METHODRESPONSE with two ERROR children "
        "(overall invalid, but valid at this level)",
        dict(
            xml_str=''
            '<METHODRESPONSE NAME="M1">'
            '  <ERROR CODE="5"/>'
            '  <ERROR CODE="6"/>'
            '</METHODRESPONSE>',
            exp_result=(
                'METHODRESPONSE', {'NAME': 'M1'},
                [
                    ('ERROR', {'CODE': '5'}, []),
                    ('ERROR', {'CODE': '6'}, []),
                ],
            ),
        ),
        None, None, True
    ),
    (
        "METHODRESPONSE with RETURNVALUE child",
        dict(
            xml_str=''
            '<METHODRESPONSE NAME="M1">'
            '  <RETURNVALUE PARAMTYPE="string"/>'
            '</METHODRESPONSE>',
            exp_result=(
                'METHODRESPONSE', {'NAME': 'M1'},
                [
                    ('RETURNVALUE', {'PARAMTYPE': 'string'}, None),
                ],
            ),
        ),
        None, None, True
    ),
    (
        "METHODRESPONSE with two RETURNVALUE children "
        "(overall invalid, but valid at this level)",
        dict(
            xml_str=''
            '<METHODRESPONSE NAME="M1">'
            '  <RETURNVALUE PARAMTYPE="string"/>'
            '  <RETURNVALUE PARAMTYPE="string"/>'
            '</METHODRESPONSE>',
            exp_result=(
                'METHODRESPONSE', {'NAME': 'M1'},
                [
                    ('RETURNVALUE', {'PARAMTYPE': 'string'}, None),
                    ('RETURNVALUE', {'PARAMTYPE': 'string'}, None),
                ],
            ),
        ),
        None, None, True
    ),
    (
        "METHODRESPONSE with PARAMVALUE child",
        dict(
            xml_str=''
            '<METHODRESPONSE NAME="M1">'
            '  <PARAMVALUE NAME="P1"/>'
            '</METHODRESPONSE>',
            exp_result=(
                'METHODRESPONSE', {'NAME': 'M1'},
                [
                    ('P1', None, None),
                ],
            ),
        ),
        None, None, True
    ),
    (
        "METHODRESPONSE with two PARAMVALUE children (valid)",
        dict(
            xml_str=''
            '<METHODRESPONSE NAME="M1">'
            '  <PARAMVALUE NAME="P1"/>'
            '  <PARAMVALUE NAME="P2"/>'
            '</METHODRESPONSE>',
            exp_result=(
                'METHODRESPONSE', {'NAME': 'M1'},
                [
                    ('P1', None, None),
                    ('P2', None, None),
                ],
            ),
        ),
        None, None, True
    ),
    (
        "METHODRESPONSE with RETURNVALUE and two PARAMVALUE children (valid)",
        dict(
            xml_str=''
            '<METHODRESPONSE NAME="M1">'
            '  <RETURNVALUE PARAMTYPE="string"/>'
            '  <PARAMVALUE NAME="P1"/>'
            '  <PARAMVALUE NAME="P2"/>'
            '</METHODRESPONSE>',
            exp_result=(
                'METHODRESPONSE', {'NAME': 'M1'},
                [
                    ('RETURNVALUE', {'PARAMTYPE': 'string'}, None),
                    ('P1', None, None),
                    ('P2', None, None),
                ],
            ),
        ),
        None, None, True
    ),
    (
        "METHODRESPONSE with ERROR child and PARAMVALUE child "
        "(overall invalid, but valid at this level)",
        dict(
            xml_str=''
            '<METHODRESPONSE NAME="M1">'
            '  <ERROR CODE="5"/>'
            '  <PARAMVALUE NAME="P1"/>'
            '</METHODRESPONSE>',
            exp_result=(
                'METHODRESPONSE', {'NAME': 'M1'},
                [
                    ('ERROR', {'CODE': '5'}, []),
                    ('P1', None, None),
                ],
            ),
        ),
        None, None, True
    ),
    (
        "METHODRESPONSE with ERROR child and RETURNVALUE child "
        "(overall invalid, but valid at this level)",
        dict(
            xml_str=''
            '<METHODRESPONSE NAME="M1">'
            '  <ERROR CODE="5"/>'
            '  <RETURNVALUE PARAMTYPE="string"/>'
            '</METHODRESPONSE>',
            exp_result=(
                'METHODRESPONSE', {'NAME': 'M1'},
                [
                    ('ERROR', {'CODE': '5'}, []),
                    ('RETURNVALUE', {'PARAMTYPE': 'string'}, None),
                ],
            ),
        ),
        None, None, True
    ),

    # PARAMVALUE tests:
    #
    #   <!ELEMENT PARAMVALUE (VALUE | VALUE.REFERENCE | VALUE.ARRAY |
    #                         VALUE.REFARRAY | CLASSNAME | INSTANCENAME |
    #                         CLASS | INSTANCE | VALUE.NAMEDINSTANCE)?>
    #   <!ATTLIST PARAMVALUE
    #       %CIMName;
    #       %ParamType;  #IMPLIED
    #       %EmbeddedObject;>
    (
        "PARAMVALUE with invalid child element",
        dict(
            xml_str=''
            '<PARAMVALUE NAME="P1">'
            '  <XXX/>'
            '</PARAMVALUE>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PARAMVALUE with invalid attribute",
        dict(
            xml_str=''
            '<PARAMVALUE NAME="P1" XXX="bla">'
            '</PARAMVALUE>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PARAMVALUE without value child (value None)",
        dict(
            xml_str=''
            '<PARAMVALUE NAME="P1">'
            '</PARAMVALUE>',
            exp_result=(u'P1', None, None),
        ),
        None, None, True
    ),
    (
        "PARAMVALUE without PARAMTYPE",
        dict(
            xml_str=''
            '<PARAMVALUE NAME="EnumerationContext">'
            '  <VALUE>z8vmi13hjvfyf9v71gbz----------------</VALUE>'
            '</PARAMVALUE>',
            exp_result=(u'EnumerationContext',
                        None,
                        u'z8vmi13hjvfyf9v71gbz----------------'),
        ),
        None, None, True
    ),
    (
        "PARAMVALUE with PARAMTYPE",
        dict(
            xml_str=''
            '<PARAMVALUE NAME="EnumerationContext" PARAMTYPE="string">'
            '  <VALUE>z8vmi13hjvfyf9v71gbz----------------</VALUE>'
            '</PARAMVALUE>',
            exp_result=(u'EnumerationContext',
                        u'string',
                        u'z8vmi13hjvfyf9v71gbz----------------'),
        ),
        None, None, True
    ),
    (
        "PARAMVALUE with TYPE and no PARAMTYPE",
        dict(
            xml_str=''
            '<PARAMVALUE NAME="EnumerationContext" TYPE="string">'
            '  <VALUE>z8vmi13hjvfyf9v71gbz----------------</VALUE>'
            '</PARAMVALUE>',
            exp_result=(u'EnumerationContext',
                        u'string',
                        u'z8vmi13hjvfyf9v71gbz----------------'),
        ),
        None, None, True
    ),
    (
        "PARAMVALUE with both TYPE and PARAMTYPE",
        dict(
            xml_str=''
            '<PARAMVALUE NAME="EnumerationContext" '
            'PARAMTYPE="string" TYPE="boolean">'
            '  <VALUE>z8vmi13hjvfyf9v71gbz----------------</VALUE>'
            '</PARAMVALUE>',
            exp_result=(u'EnumerationContext',
                        u'string',
                        u'z8vmi13hjvfyf9v71gbz----------------'),
        ),
        None, None, True
    ),
    (
        "PARAMVALUE with two VALUE children (invalid)",
        dict(
            xml_str=''
            '<PARAMVALUE NAME="P1">'
            '  <VALUE>abc</VALUE>'
            '  <VALUE>abc</VALUE>'
            '</PARAMVALUE>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PARAMVALUE without TYPE/PARAMTYPE and with VALUE child",
        dict(
            xml_str=''
            '<PARAMVALUE NAME="P1">'
            '  <VALUE>abc</VALUE>'
            '</PARAMVALUE>',
            exp_result=(u'P1', None, 'abc'),
        ),
        None, None, True
    ),
    (
        "PARAMVALUE with two VALUE.REFERENCE children (invalid)",
        dict(
            xml_str=''
            '<PARAMVALUE NAME="P1">'
            '  <VALUE.REFERENCE>'
            '    <INSTANCENAME CLASSNAME="CIM_Foo"/>'
            '  </VALUE.REFERENCE>'
            '  <VALUE.REFERENCE>'
            '    <INSTANCENAME CLASSNAME="CIM_Foo"/>'
            '  </VALUE.REFERENCE>'
            '</PARAMVALUE>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PARAMVALUE without TYPE/PARAMTYPE and with VALUE.REFERENCE child",
        dict(
            xml_str=''
            '<PARAMVALUE NAME="P1">'
            '  <VALUE.REFERENCE>'
            '    <INSTANCENAME CLASSNAME="CIM_Foo"/>'
            '  </VALUE.REFERENCE>'
            '</PARAMVALUE>',
            exp_result=(u'P1',
                        None,
                        CIMInstanceName('CIM_Foo')),
        ),
        None, MissingKeybindingsWarning, True
    ),
    (
        "PARAMVALUE with two VALUE.ARRAY children (invalid)",
        dict(
            xml_str=''
            '<PARAMVALUE NAME="P1">'
            '  <VALUE.ARRAY>'
            '  </VALUE.ARRAY>'
            '  <VALUE.ARRAY>'
            '  </VALUE.ARRAY>'
            '</PARAMVALUE>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PARAMVALUE without TYPE/PARAMTYPE and with empty VALUE.ARRAY child",
        dict(
            xml_str=''
            '<PARAMVALUE NAME="P1">'
            '  <VALUE.ARRAY>'
            '  </VALUE.ARRAY>'
            '</PARAMVALUE>',
            exp_result=(u'P1',
                        None,
                        []),
        ),
        None, None, True
    ),
    (
        "PARAMVALUE with two VALUE.REFARRAY children (invalid)",
        dict(
            xml_str=''
            '<PARAMVALUE NAME="P1">'
            '  <VALUE.REFARRAY>'
            '  </VALUE.REFARRAY>'
            '  <VALUE.REFARRAY>'
            '  </VALUE.REFARRAY>'
            '</PARAMVALUE>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PARAMVALUE without TYPE/PARAMTYPE and with empty VALUE.REFARRAY child",
        dict(
            xml_str=''
            '<PARAMVALUE NAME="P1">'
            '  <VALUE.REFARRAY>'
            '  </VALUE.REFARRAY>'
            '</PARAMVALUE>',
            exp_result=(u'P1',
                        None,
                        []),
        ),
        None, None, True
    ),
    (
        "PARAMVALUE with two CLASSNAME children (invalid)",
        dict(
            xml_str=''
            '<PARAMVALUE NAME="P1">'
            '  <CLASSNAME NAME="CIM_Foo"/>'
            '  <CLASSNAME NAME="CIM_Foo"/>'
            '</PARAMVALUE>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PARAMVALUE without TYPE/PARAMTYPE and with empty CLASSNAME child",
        dict(
            xml_str=''
            '<PARAMVALUE NAME="P1">'
            '  <CLASSNAME NAME="CIM_Foo"/>'
            '</PARAMVALUE>',
            exp_result=(u'P1',
                        None,
                        CIMClassName('CIM_Foo')),
        ),
        None, None, True
    ),
    (
        "PARAMVALUE with two INSTANCENAME children (invalid)",
        dict(
            xml_str=''
            '<PARAMVALUE NAME="P1">'
            '  <INSTANCENAME CLASSNAME="CIM_Foo"/>'
            '  <INSTANCENAME CLASSNAME="CIM_Foo"/>'
            '</PARAMVALUE>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PARAMVALUE without TYPE/PARAMTYPE and with empty INSTANCENAME child",
        dict(
            xml_str=''
            '<PARAMVALUE NAME="P1">'
            '  <INSTANCENAME CLASSNAME="CIM_Foo"/>'
            '</PARAMVALUE>',
            exp_result=(u'P1',
                        None,
                        CIMInstanceName('CIM_Foo')),
        ),
        None, MissingKeybindingsWarning, True
    ),
    (
        "PARAMVALUE with two CLASS children (invalid)",
        dict(
            xml_str=''
            '<PARAMVALUE NAME="P1">'
            '  <CLASS NAME="CIM_Foo"/>'
            '  <CLASS NAME="CIM_Foo"/>'
            '</PARAMVALUE>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PARAMVALUE without TYPE/PARAMTYPE and with empty CLASS child",
        dict(
            xml_str=''
            '<PARAMVALUE NAME="P1">'
            '  <CLASS NAME="CIM_Foo"/>'
            '</PARAMVALUE>',
            exp_result=(u'P1',
                        None,
                        CIMClass('CIM_Foo')),
        ),
        None, None, True
    ),
    (
        "PARAMVALUE with two INSTANCE children (invalid)",
        dict(
            xml_str=''
            '<PARAMVALUE NAME="P1">'
            '  <INSTANCE CLASSNAME="CIM_Foo"/>'
            '  <INSTANCE CLASSNAME="CIM_Foo"/>'
            '</PARAMVALUE>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PARAMVALUE without TYPE/PARAMTYPE and with empty INSTANCE child",
        dict(
            xml_str=''
            '<PARAMVALUE NAME="P1">'
            '  <INSTANCE CLASSNAME="CIM_Foo"/>'
            '</PARAMVALUE>',
            exp_result=(u'P1',
                        None,
                        CIMInstance('CIM_Foo')),
        ),
        None, None, True
    ),
    (
        "PARAMVALUE with two VALUE.NAMEDINSTANCE children (invalid)",
        dict(
            xml_str=''
            '<PARAMVALUE NAME="P1">'
            '  <VALUE.NAMEDINSTANCE>'
            '    <INSTANCENAME CLASSNAME="CIM_Foo"/>'
            '    <INSTANCE CLASSNAME="CIM_Foo"/>'
            '  </VALUE.NAMEDINSTANCE>'
            '  <VALUE.NAMEDINSTANCE>'
            '    <INSTANCENAME CLASSNAME="CIM_Foo"/>'
            '    <INSTANCE CLASSNAME="CIM_Foo"/>'
            '  </VALUE.NAMEDINSTANCE>'
            '</PARAMVALUE>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PARAMVALUE without TYPE/PARAMTYPE and with VALUE.NAMEDINSTANCE "
        "child",
        dict(
            xml_str=''
            '<PARAMVALUE NAME="P1">'
            '  <VALUE.NAMEDINSTANCE>'
            '    <INSTANCENAME CLASSNAME="CIM_Foo"/>'
            '    <INSTANCE CLASSNAME="CIM_Foo"/>'
            '  </VALUE.NAMEDINSTANCE>'
            '</PARAMVALUE>',
            exp_result=(u'P1',
                        None,
                        CIMInstance(
                            'CIM_Foo',
                            path=CIMInstanceName(
                                'CIM_Foo',
                            ),
                        ))
        ),
        None, MissingKeybindingsWarning, True
    ),

    # RETURNVALUE tests:
    #
    #   <!ELEMENT RETURNVALUE (VALUE | VALUE.REFERENCE)?>
    #   <!ATTLIST RETURNVALUE
    #       %EmbeddedObject;
    #       %ParamType;       #IMPLIED>
    (
        "RETURNVALUE with invalid child element",
        dict(
            xml_str=''
            '<RETURNVALUE>'
            '  <XXX/>'
            '</RETURNVALUE>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "RETURNVALUE with invalid attribute",
        dict(
            xml_str=''
            '<RETURNVALUE XXX="bla">'
            '</RETURNVALUE>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "RETURNVALUE with simple PARAMTYPE and zero",
        dict(
            xml_str=''
            '<RETURNVALUE PARAMTYPE="sint32">'
            '<VALUE>0</VALUE>'
            '</RETURNVALUE>',
            exp_result=(u'RETURNVALUE', {u'PARAMTYPE': u'sint32'}, u'0'),
        ),
        None, None, True
    ),
    (
        "RETURNVALUE with simple PARAMTYPE and nonzero value",
        dict(
            xml_str=''
            '<RETURNVALUE PARAMTYPE="sint32">'
            '<VALUE>1</VALUE>'
            '</RETURNVALUE>',
            exp_result=(u'RETURNVALUE', {u'PARAMTYPE': u'sint32'}, u'1'),
        ),
        None, None, True
    ),
    (
        "RETURNVALUE with simple PARAMTYPE and embeddedobject",
        dict(
            xml_str=''
            '<RETURNVALUE PARAMTYPE="string" EmbeddedObject="instance">'
            '<VALUE>&lt;CLASS NAME="PyWBEM_Address" SUPERCLASS="PyWBEM_Object"'
            '&gt;&lt;PROPERTY NAME="Street" TYPE="string"&gt;'
            '&lt;VALUE&gt;Default Street&lt;/VALUE&gt;&lt;/PROPERTY&gt;'
            '&lt;PROPERTY NAME="Town" TYPE="string"&gt;'
            '&lt;VALUE&gt;Default Town&lt;/VALUE&gt;'
            '&lt;/PROPERTY&gt;&lt;/CLASS&gt;</VALUE></RETURNVALUE>',
            exp_result=(u'RETURNVALUE',
                        {u'EmbeddedObject': u'instance',
                         u'PARAMTYPE': u'string'},
                        CIMClass(
                            classname='PyWBEM_Address',
                            superclass='PyWBEM_Object',
                            properties=[
                                CIMProperty(
                                    name='Street', value='Default Street',
                                    type='string', reference_class=None,
                                    embedded_object=None, propagated=False,
                                    is_array=False, array_size=None),
                                CIMProperty(
                                    name='Town',
                                    value='Default Town',
                                    type='string', reference_class=None,
                                    embedded_object=None, propagated=False,
                                    is_array=False, array_size=None)],
                            path=None)),
        ),
        None, None, True
    ),
    (
        "RETURNVALUE with simple PARAMTYPE and EMBEDDEDOBJECT",
        dict(
            xml_str=''
            '<RETURNVALUE PARAMTYPE="string" EMBEDDEDOBJECT="instance">'
            '<VALUE>&lt;CLASS NAME="PyWBEM_Address" SUPERCLASS="PyWBEM_Object"'
            '&gt;&lt;PROPERTY NAME="Street" TYPE="string"&gt;'
            '&lt;VALUE&gt;Default Street&lt;/VALUE&gt;'
            '&lt;/PROPERTY&gt;&lt;PROPERTY NAME="Town" TYPE="string"&gt;'
            '&lt;VALUE&gt;Default Town&lt;/VALUE&gt;'
            '&lt;/PROPERTY&gt;&lt;/CLASS&gt;</VALUE></RETURNVALUE>',
            exp_result=(u'RETURNVALUE',
                        {u'EMBEDDEDOBJECT': u'instance',
                         u'PARAMTYPE': u'string'},
                        CIMClass(
                            classname='PyWBEM_Address',
                            superclass='PyWBEM_Object',
                            properties=[
                                CIMProperty(
                                    name='Street', value='Default Street',
                                    type='string', reference_class=None,
                                    embedded_object=None, propagated=False,
                                    is_array=False, array_size=None),
                                CIMProperty(
                                    name='Town', value='Default Town',
                                    type='string', reference_class=None,
                                    embedded_object=None, propagated=False,
                                    is_array=False, array_size=None)],
                            path=None)),
        ),
        None, None, True
    ),
    (
        "RETURNVALUE with simple PARAMTYPE and invalid value. passes",
        dict(
            xml_str=''
            '<RETURNVALUE PARAMTYPE="sint32">'
            '<VALUE>hi</VALUE>'
            '</RETURNVALUE>',
            exp_result=(u'RETURNVALUE', {u'PARAMTYPE': u'sint32'}, u'hi'),
        ),
        None, None, True
    ),
    (
        "RETURNVALUE with simple PARAMTYPE and nonzero value",
        dict(
            xml_str=''
            '<RETURNVALUE PARAMTYPE="sint32">'
            '<VALUE>1</VALUE>'
            '</RETURNVALUE>',
            exp_result=(u'RETURNVALUE', {u'PARAMTYPE': u'sint32'}, u'1'),
        ),
        None, None, True
    ),
    (
        "RETURNVALUE with two VALUE children (invalid)",
        dict(
            xml_str=''
            '<RETURNVALUE PARAMTYPE="sint32">'
            '  <VALUE>1</VALUE>'
            '  <VALUE>1</VALUE>'
            '</RETURNVALUE>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "RETURNVALUE with two VALUE.REFERENCE children (invalid)",
        dict(
            xml_str=''
            '<RETURNVALUE>'
            '  <VALUE.REFERENCE>'
            '    <INSTANCENAME CLASSNAME="CIM_Foo"/>'
            '  </VALUE.REFERENCE>'
            '  <VALUE.REFERENCE>'
            '    <INSTANCENAME CLASSNAME="CIM_Foo"/>'
            '  </VALUE.REFERENCE>'
            '</RETURNVALUE>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "RETURNVALUE with VALUE.REFERENCE (normal case)",
        dict(
            xml_str=''
            '<RETURNVALUE>'
            '  <VALUE.REFERENCE>'
            '    <INSTANCENAME CLASSNAME="CIM_Foo"/>'
            '  </VALUE.REFERENCE>'
            '</RETURNVALUE>',
            exp_result=(u'RETURNVALUE',
                        {},
                        CIMInstanceName(classname='CIM_Foo')),
        ),
        None, MissingKeybindingsWarning, True
    ),
    (
        "RETURNVALUE with VALUE.REFERENCE and missing end tag",
        dict(
            xml_str=''
            '<RETURNVALUE PARAMTYPEX="sint32">'
            '<VALUE.REFERENCE>'
            '<INSTANCENAME CLASSNAME="PyWBEM_Person">'
            '<KEYBINDING NAME="CreationClassName">'
            '<KEYVALUE VALUETYPE="string">PyWBEM_Person</KEYVALUE>'
            '</KEYBINDING>'
            '<KEYBINDING NAME="Name">'
            '<KEYVALUE VALUETYPE="string">Alice</KEYVALUE>'
            '</KEYBINDING>'
            '</INSTANCENAME>'
            '</VALUE.REFERENCE>',
            exp_result=None,
        ),
        XMLParseError, None, True
    ),

    # EXPMETHODCALL tests:
    #
    #   <!ELEMENT EXPMETHODCALL (EXPPARAMVALUE*)>
    #   <!ATTLIST EXPMETHODCALL
    #       %CIMName;>
    (
        "EXPMETHODCALL with invalid child element",
        dict(
            xml_str=''
            '<EXPMETHODCALL NAME="M1">'
            '  <XXX/>'
            '</EXPMETHODCALL>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "EXPMETHODCALL with invalid attribute",
        dict(
            xml_str=''
            '<EXPMETHODCALL NAME="M1" XXX="bla">'
            '</EXPMETHODCALL>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "EXPMETHODCALL with missing NAME attribute (invalid)",
        dict(
            xml_str=''
            '<EXPMETHODCALL>'
            '</EXPMETHODCALL>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "EXPMETHODCALL with one EXPPARAMVALUE child",
        dict(
            xml_str=''
            '<EXPMETHODCALL NAME="M1">'
            '  <EXPPARAMVALUE NAME="P1"/>'
            '</EXPMETHODCALL>',
            exp_result=(
                u'EXPMETHODCALL',
                {u'NAME': u'M1'},
                [
                    (u'P1', None),
                ],
            ),
        ),
        None, None, True
    ),
    (
        "EXPMETHODCALL with two EXPPARAMVALUE children (valid)",
        dict(
            xml_str=''
            '<EXPMETHODCALL NAME="M1">'
            '  <EXPPARAMVALUE NAME="P1"/>'
            '  <EXPPARAMVALUE NAME="P2"/>'
            '</EXPMETHODCALL>',
            exp_result=(
                u'EXPMETHODCALL',
                {u'NAME': u'M1'},
                [
                    (u'P1', None),
                    (u'P2', None),
                ],
            ),
        ),
        None, None, True
    ),

    # EXPMETHODRESPONSE tests: Parsing this element is not implemented
    (
        "EXPMETHODRESPONSE (not implemented)",
        dict(
            xml_str=''
            '<EXPMETHODRESPONSE/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),

    # EXPPARAMVALUE tests:
    #
    #   <!ELEMENT EXPPARAMVALUE (INSTANCE?)>
    #   <!ATTLIST EXPPARAMVALUE
    #       %CIMName;>
    (
        "EXPPARAMVALUE with invalid child element",
        dict(
            xml_str=''
            '<EXPPARAMVALUE NAME="P1">'
            '  <XXX/>'
            '</EXPPARAMVALUE>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "EXPPARAMVALUE with invalid attribute",
        dict(
            xml_str=''
            '<EXPPARAMVALUE NAME="P1" XXX="bla">'
            '</EXPPARAMVALUE>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "EXPPARAMVALUE with missing NAME attribute (invalid)",
        dict(
            xml_str=''
            '<EXPPARAMVALUE>'
            '</EXPPARAMVALUE>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "EXPPARAMVALUE with no children (minimal case)",
        dict(
            xml_str=''
            '<EXPPARAMVALUE NAME="P1">'
            '</EXPPARAMVALUE>',
            exp_result=(u'P1', None),
        ),
        None, None, True
    ),
    (
        "EXPPARAMVALUE with INSTANCE child",
        dict(
            xml_str=''
            '<EXPPARAMVALUE NAME="P1">'
            '  <INSTANCE CLASSNAME="CIM_Foo"/>'
            '</EXPPARAMVALUE>',
            exp_result=(u'P1', CIMInstance('CIM_Foo')),
        ),
        None, None, True
    ),
    (
        "EXPPARAMVALUE with two INSTANCE children (invalid)",
        dict(
            xml_str=''
            '<EXPPARAMVALUE NAME="P1">'
            '  <INSTANCE CLASSNAME="CIM_Foo"/>'
            '  <INSTANCE CLASSNAME="CIM_Bar"/>'
            '</EXPPARAMVALUE>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),

    # IMETHODCALL tests:
    #
    #   <!ELEMENT IMETHODCALL (LOCALNAMESPACEPATH, IPARAMVALUE*)>
    #   <!ATTLIST IMETHODCALL
    #      %CIMName;>
    (
        "IMETHODCALL with invalid child element",
        dict(
            xml_str=''
            '<IMETHODCALL NAME="M1">'
            '  <XXX/>'
            '</IMETHODCALL>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "IMETHODCALL with invalid attribute",
        dict(
            xml_str=''
            '<IMETHODCALL NAME="M1" XXX="bla">'
            '  <LOCALNAMESPACEPATH>'
            '    <NAMESPACE NAME="foo"/>'
            '  </LOCALNAMESPACEPATH>'
            '</IMETHODCALL>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "IMETHODCALL with missing NAME attribute",
        dict(
            xml_str=''
            '<IMETHODCALL>'
            '  <LOCALNAMESPACEPATH>'
            '    <NAMESPACE NAME="foo"/>'
            '  </LOCALNAMESPACEPATH>'
            '</IMETHODCALL>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "IMETHODCALL with missing LOCALNAMESPACEPATH child element",
        dict(
            xml_str=''
            '<IMETHODCALL NAME="M1">'
            '</IMETHODCALL>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "IMETHODCALL for GetClass with missing LOCALNAMESPACEPATH (invalid)",
        dict(
            xml_str=''
            '<IMETHODCALL NAME="GetClass">'
            '  <IPARAMVALUE NAME="ClassName">'
            '    <CLASSNAME NAME="CIM_ComputerSystem"/>'
            '  </IPARAMVALUE>'
            '</IMETHODCALL>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "IMETHODCALL for GetClass with two LOCALNAMESPACEPATH children "
        "(invalid)",
        dict(
            xml_str=''
            '<IMETHODCALL NAME="GetClass">'
            '  <LOCALNAMESPACEPATH>'
            '    <NAMESPACE NAME="root"/>'
            '    <NAMESPACE NAME="cimv2"/>'
            '  </LOCALNAMESPACEPATH>'
            '  <LOCALNAMESPACEPATH>'
            '    <NAMESPACE NAME="root"/>'
            '    <NAMESPACE NAME="cimv2"/>'
            '  </LOCALNAMESPACEPATH>'
            '  <IPARAMVALUE NAME="ClassName">'
            '    <CLASSNAME NAME="CIM_ComputerSystem"/>'
            '  </IPARAMVALUE>'
            '</IMETHODCALL>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "IMETHODCALL with minimal child elements",
        dict(
            xml_str=''
            '<IMETHODCALL NAME="M1">'
            '  <LOCALNAMESPACEPATH>'
            '    <NAMESPACE NAME="foo"/>'
            '  </LOCALNAMESPACEPATH>'
            '</IMETHODCALL>',
            exp_result=(
                u'IMETHODCALL',
                {u'NAME': u'M1'},
                u'foo',
                [],
            ),
        ),
        None, None, True
    ),
    (
        "IMETHODCALL for GetClass (normal case)",
        dict(
            xml_str=''
            '<IMETHODCALL NAME="GetClass">'
            '  <LOCALNAMESPACEPATH>'
            '    <NAMESPACE NAME="root"/>'
            '    <NAMESPACE NAME="cimv2"/>'
            '  </LOCALNAMESPACEPATH>'
            '  <IPARAMVALUE NAME="ClassName">'
            '    <CLASSNAME NAME="CIM_ComputerSystem"/>'
            '  </IPARAMVALUE>'
            '  <IPARAMVALUE NAME="PropertyList">'
            '    <VALUE.ARRAY>'
            '      <VALUE>PowerManagementCapabilities</VALUE>'
            '    </VALUE.ARRAY>'
            '  </IPARAMVALUE>'
            '  <IPARAMVALUE NAME="LocalOnly">'
            '    <VALUE>FALSE</VALUE>'
            '  </IPARAMVALUE>'
            '</IMETHODCALL>',
            exp_result=(u'IMETHODCALL',
                        {u'NAME': u'GetClass'},
                        u'root/cimv2',
                        [(u'ClassName',
                          CIMClassName(classname='CIM_ComputerSystem',
                                       namespace=None, host=None)),
                         (u'PropertyList', [u'PowerManagementCapabilities']),
                         (u'LocalOnly', False)]),
        ),
        None, None, True
    ),

    # IMETHODRESPONSE tests:
    #
    #   <!ELEMENT IMETHODRESPONSE (ERROR | (IRETURNVALUE?, PARAMVALUE*))>
    #   <!ATTLIST IMETHODRESPONSE
    #       %CIMName;>
    (
        "IMETHODRESPONSE with invalid child element",
        dict(
            xml_str=''
            '<IMETHODRESPONSE NAME="M1">'
            '  <XXX/>'
            '</IMETHODRESPONSE>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "IMETHODRESPONSE with invalid attribute",
        dict(
            xml_str=''
            '<IMETHODRESPONSE NAME="M1" XXX="bla">'
            '</IMETHODRESPONSE>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "IMETHODRESPONSE with missing NAME attribute",
        dict(
            xml_str=''
            '<IMETHODRESPONSE>'
            '</IMETHODRESPONSE>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "IMETHODRESPONSE with ERROR child",
        dict(
            xml_str=''
            '<IMETHODRESPONSE NAME="M1">'
            '  <ERROR CODE="5"/>'
            '</IMETHODRESPONSE>',
            exp_result=(
                'IMETHODRESPONSE', {'NAME': 'M1'},
                [
                    ('ERROR', {'CODE': '5'}, []),
                ],
            ),
        ),
        None, None, True
    ),
    (
        "IMETHODRESPONSE with two ERROR children "
        "(overall invalid, but valid at this level)",
        dict(
            xml_str=''
            '<IMETHODRESPONSE NAME="M1">'
            '  <ERROR CODE="5"/>'
            '  <ERROR CODE="6"/>'
            '</IMETHODRESPONSE>',
            exp_result=(
                'IMETHODRESPONSE', {'NAME': 'M1'},
                [
                    ('ERROR', {'CODE': '5'}, []),
                    ('ERROR', {'CODE': '6'}, []),
                ],
            ),
        ),
        None, None, True
    ),
    (
        "IMETHODRESPONSE with IRETURNVALUE child",
        dict(
            xml_str=''
            '<IMETHODRESPONSE NAME="M1">'
            '  <IRETURNVALUE/>'
            '</IMETHODRESPONSE>',
            exp_result=(
                'IMETHODRESPONSE', {'NAME': 'M1'},
                [
                    ('IRETURNVALUE', {}, []),
                ],
            ),
        ),
        None, None, True
    ),
    (
        "IMETHODRESPONSE with two IRETURNVALUE children "
        "(overall invalid, but valid at this level)",
        dict(
            xml_str=''
            '<IMETHODRESPONSE NAME="M1">'
            '  <IRETURNVALUE/>'
            '  <IRETURNVALUE/>'
            '</IMETHODRESPONSE>',
            exp_result=(
                'IMETHODRESPONSE', {'NAME': 'M1'},
                [
                    ('IRETURNVALUE', {}, []),
                    ('IRETURNVALUE', {}, []),
                ],
            ),
        ),
        None, None, True
    ),
    (
        "IMETHODRESPONSE with PARAMVALUE child",
        dict(
            xml_str=''
            '<IMETHODRESPONSE NAME="M1">'
            '  <PARAMVALUE NAME="P1"/>'
            '</IMETHODRESPONSE>',
            exp_result=(
                'IMETHODRESPONSE', {'NAME': 'M1'},
                [
                    ('P1', None, None),
                ],
            ),
        ),
        None, None, True
    ),
    (
        "IMETHODRESPONSE with two PARAMVALUE children (valid)",
        dict(
            xml_str=''
            '<IMETHODRESPONSE NAME="M1">'
            '  <PARAMVALUE NAME="P1"/>'
            '  <PARAMVALUE NAME="P2"/>'
            '</IMETHODRESPONSE>',
            exp_result=(
                'IMETHODRESPONSE', {'NAME': 'M1'},
                [
                    ('P1', None, None),
                    ('P2', None, None),
                ],
            ),
        ),
        None, None, True
    ),
    (
        "IMETHODRESPONSE with IRETURNVALUE and two PARAMVALUE children (valid)",
        dict(
            xml_str=''
            '<IMETHODRESPONSE NAME="M1">'
            '  <IRETURNVALUE/>'
            '  <PARAMVALUE NAME="P1"/>'
            '  <PARAMVALUE NAME="P2"/>'
            '</IMETHODRESPONSE>',
            exp_result=(
                'IMETHODRESPONSE', {'NAME': 'M1'},
                [
                    ('IRETURNVALUE', {}, []),
                    ('P1', None, None),
                    ('P2', None, None),
                ],
            ),
        ),
        None, None, True
    ),
    (
        "IMETHODRESPONSE with ERROR child and PARAMVALUE child "
        "(overall invalid, but valid at this level)",
        dict(
            xml_str=''
            '<IMETHODRESPONSE NAME="M1">'
            '  <ERROR CODE="5"/>'
            '  <PARAMVALUE NAME="P1"/>'
            '</IMETHODRESPONSE>',
            exp_result=(
                'IMETHODRESPONSE', {'NAME': 'M1'},
                [
                    ('ERROR', {'CODE': '5'}, []),
                    ('P1', None, None),
                ],
            ),
        ),
        None, None, True
    ),
    (
        "IMETHODRESPONSE with ERROR child and IRETURNVALUE child "
        "(overall invalid, but valid at this level)",
        dict(
            xml_str=''
            '<IMETHODRESPONSE NAME="M1">'
            '  <ERROR CODE="5"/>'
            '  <IRETURNVALUE/>'
            '</IMETHODRESPONSE>',
            exp_result=(
                'IMETHODRESPONSE', {'NAME': 'M1'},
                [
                    ('ERROR', {'CODE': '5'}, []),
                    ('IRETURNVALUE', {}, []),
                ],
            ),
        ),
        None, None, True
    ),

    # IPARAMVALUE tests:
    #
    #   <!ELEMENT IPARAMVALUE (VALUE | VALUE.ARRAY | VALUE.REFERENCE |
    #                         INSTANCENAME | CLASSNAME |
    #                         QUALIFIER.DECLARATION |
    #                         CLASS | INSTANCE | VALUE.NAMEDINSTANCE)?>
    #   <!ATTLIST IPARAMVALUE
    #       %CIMName;>
    (
        "IPARAMVALUE with invalid child element",
        dict(
            xml_str=''
            '<IPARAMVALUE NAME="P1">'
            '  <VALUE/>'
            '  <XXX/>'
            '</IPARAMVALUE>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "IPARAMVALUE with invalid attribute",
        dict(
            xml_str=''
            '<IPARAMVALUE NAME="P1" XXX="bla">'
            '  <VALUE/>'
            '</IPARAMVALUE>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "IPARAMVALUE with missing NAME attribute (invalid)",
        dict(
            xml_str=''
            '<IPARAMVALUE>'
            '  <VALUE/>'
            '</IPARAMVALUE>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "IPARAMVALUE with VALUE child that has a boolean value FALSE",
        dict(
            xml_str=''
            '<IPARAMVALUE NAME="LocalOnly">'
            '  <VALUE>FALSE</VALUE>'
            '</IPARAMVALUE>',
            exp_result=(u'LocalOnly', False),
        ),
        None, None, True
    ),
    (
        "IPARAMVALUE with VALUE child that has a boolean value TRUE",
        dict(
            xml_str=''
            '<IPARAMVALUE NAME="LocalOnly">'
            '  <VALUE>TRUE</VALUE>'
            '</IPARAMVALUE>',
            exp_result=(u'LocalOnly', True),
        ),
        None, None, True
    ),
    (
        "IPARAMVALUE with VALUE.ARRAY child with two integers (become strings)",
        dict(
            xml_str=''
            '<IPARAMVALUE NAME="ARRAYINT">'
            '  <VALUE.ARRAY>'
            '    <VALUE>1</VALUE>'
            '    <VALUE>2</VALUE>'
            '  </VALUE.ARRAY>'
            '</IPARAMVALUE>',
            exp_result=(u'ARRAYINT', [u'1', u'2']),
        ),
        None, None, True
    ),
    (
        "IPARAMVALUE with two VALUE children (invalid)",
        dict(
            xml_str=''
            '<IPARAMVALUE NAME="LocalOnly">'
            '  <VALUE>FALSE</VALUE>'
            '  <VALUE>FALSE</VALUE>'
            '</IPARAMVALUE>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "IPARAMVALUE with VALUE.REFERENCE child",
        dict(
            xml_str=''
            '<IPARAMVALUE NAME="P1">'
            '  <VALUE.REFERENCE>'
            '    <CLASSNAME NAME="CIM_Foo"/>'
            '  </VALUE.REFERENCE>'
            '</IPARAMVALUE>',
            exp_result=(u'P1', CIMClassName('CIM_Foo')),
        ),
        None, None, True
    ),
    (
        "IPARAMVALUE with two VALUE.REFERENCE children (invalid)",
        dict(
            xml_str=''
            '<IPARAMVALUE NAME="P1">'
            '  <VALUE.REFERENCE>'
            '    <CLASSNAME NAME="CIM_Foo"/>'
            '  </VALUE.REFERENCE>'
            '  <VALUE.REFERENCE>'
            '    <CLASSNAME NAME="CIM_Bar"/>'
            '  </VALUE.REFERENCE>'
            '</IPARAMVALUE>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "IPARAMVALUE with INSTANCENAME child",
        dict(
            xml_str=''
            '<IPARAMVALUE NAME="P1">'
            '  <INSTANCENAME CLASSNAME="CIM_Foo"/>'
            '</IPARAMVALUE>',
            exp_result=(u'P1', CIMInstanceName("CIM_Foo")),
        ),
        None, MissingKeybindingsWarning, True
    ),
    (
        "IPARAMVALUE with two INSTANCENAME children (invalid)",
        dict(
            xml_str=''
            '<IPARAMVALUE NAME="P1">'
            '  <INSTANCENAME CLASSNAME="CIM_Foo"/>'
            '  <INSTANCENAME CLASSNAME="CIM_Bar"/>'
            '</IPARAMVALUE>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "IPARAMVALUE with CLASSNAME child",
        dict(
            xml_str=''
            '<IPARAMVALUE NAME="P1">'
            '  <CLASSNAME NAME="CIM_Foo"/>'
            '</IPARAMVALUE>',
            exp_result=(u'P1', CIMClassName("CIM_Foo")),
        ),
        None, None, True
    ),
    (
        "IPARAMVALUE with two CLASSNAME children (invalid)",
        dict(
            xml_str=''
            '<IPARAMVALUE NAME="P1">'
            '  <CLASSNAME NAME="CIM_Foo"/>'
            '  <CLASSNAME NAME="CIM_Bar"/>'
            '</IPARAMVALUE>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "IPARAMVALUE with VALUE.NAMEDINSTANCE child",
        dict(
            xml_str=''
            '<IPARAMVALUE NAME="P1">'
            '  <VALUE.NAMEDINSTANCE>'
            '    <INSTANCENAME CLASSNAME="CIM_Foo"/>'
            '    <INSTANCE CLASSNAME="CIM_Foo"/>'
            '  </VALUE.NAMEDINSTANCE>'
            '</IPARAMVALUE>',
            exp_result=(
                u'P1',
                CIMInstance(
                    'CIM_Foo',
                    path=CIMInstanceName('CIM_Foo'),
                ),
            ),
        ),
        None, MissingKeybindingsWarning, True
    ),
    (
        "IPARAMVALUE with two VALUE.NAMEDINSTANCE children (invalid)",
        dict(
            xml_str=''
            '<IPARAMVALUE NAME="P1">'
            '  <VALUE.NAMEDINSTANCE>'
            '    <INSTANCENAME CLASSNAME="CIM_Foo"/>'
            '    <INSTANCE CLASSNAME="CIM_Foo"/>'
            '  </VALUE.NAMEDINSTANCE>'
            '  <VALUE.NAMEDINSTANCE>'
            '    <INSTANCENAME CLASSNAME="CIM_Bar"/>'
            '    <INSTANCE CLASSNAME="CIM_Bar"/>'
            '  </VALUE.NAMEDINSTANCE>'
            '</IPARAMVALUE>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "IPARAMVALUE with CLASS child",
        dict(
            xml_str=''
            '<IPARAMVALUE NAME="P1">'
            '  <CLASS NAME="CIM_Foo"/>'
            '</IPARAMVALUE>',
            exp_result=(u'P1', CIMClass('CIM_Foo')),
        ),
        None, None, True
    ),
    (
        "IPARAMVALUE with two CLASS children (invalid)",
        dict(
            xml_str=''
            '<IPARAMVALUE NAME="P1">'
            '  <CLASS NAME="CIM_Foo"/>'
            '  <CLASS NAME="CIM_Bar"/>'
            '</IPARAMVALUE>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "IPARAMVALUE with INSTANCE child",
        dict(
            xml_str=''
            '<IPARAMVALUE NAME="P1">'
            '  <INSTANCE CLASSNAME="CIM_Foo"/>'
            '</IPARAMVALUE>',
            exp_result=(u'P1', CIMInstance('CIM_Foo')),
        ),
        None, None, True
    ),
    (
        "IPARAMVALUE with two INSTANCE children (invalid)",
        dict(
            xml_str=''
            '<IPARAMVALUE NAME="P1">'
            '  <INSTANCE CLASSNAME="CIM_Foo"/>'
            '  <INSTANCE CLASSNAME="CIM_Bar"/>'
            '</IPARAMVALUE>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "IPARAMVALUE with QUALIFIER.DECLARATION child",
        dict(
            xml_str=''
            '<IPARAMVALUE NAME="P1">'
            '  <QUALIFIER.DECLARATION NAME="Qual" TYPE="string"/>'
            '</IPARAMVALUE>',
            exp_result=(
                u'P1',
                CIMQualifierDeclaration(
                    'Qual', value=None, type='string',
                    **qualifier_declaration_default_attrs()
                ),
            ),
        ),
        None, None, True
    ),
    (
        "IPARAMVALUE with two QUALIFIER.DECLARATION children (invalid)",
        dict(
            xml_str=''
            '<IPARAMVALUE NAME="P1">'
            '  <QUALIFIER.DECLARATION NAME="Qual" TYPE="string"/>'
            '  <QUALIFIER.DECLARATION NAME="Qua2" TYPE="string"/>'
            '</IPARAMVALUE>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),

    # IRETURNVALUE tests:
    #
    #   <!ELEMENT IRETURNVALUE (CLASSNAME* | INSTANCENAME* | VALUE* |
    #                           VALUE.OBJECTWITHPATH* |
    #                           VALUE.OBJECTWITHLOCALPATH* |
    #                           VALUE.OBJECT* | OBJECTPATH* |
    #                           QUALIFIER.DECLARATION* | VALUE.ARRAY? |
    #                           VALUE.REFERENCE? | CLASS* | INSTANCE* |
    #                           INSTANCEPATH* | VALUE.NAMEDINSTANCE* |
    #                           VALUE.INSTANCEWITHPATH*)>
    (
        "IRETURNVALUE with invalid child element",
        dict(
            xml_str=''
            '<IRETURNVALUE>'
            '  <XXX/>'
            '</IRETURNVALUE>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "IRETURNVALUE with invalid attribute",
        dict(
            xml_str=''
            '<IRETURNVALUE XXX="bla"/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "IRETURNVALUE with two different children (invalid)",
        dict(
            xml_str=''
            '<IRETURNVALUE>'
            '  <VALUE>abc</VALUE>'
            '  <CLASSNAME NAME="CIM_Foo"/>'
            '</IRETURNVALUE>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "IRETURNVALUE with no children (valid)",
        dict(
            xml_str=''
            '<IRETURNVALUE>'
            '</IRETURNVALUE>',
            exp_result=(u'IRETURNVALUE', {}, []),
        ),
        None, None, True
    ),
    (
        "IRETURNVALUE with one VALUE child that is a string",
        dict(
            xml_str=''
            '<IRETURNVALUE>'
            '  <VALUE>abc</VALUE>'
            '</IRETURNVALUE>',
            exp_result=(u'IRETURNVALUE', {}, [u'abc']),
        ),
        None, None, True
    ),
    (
        "IRETURNVALUE with two VALUE children that are strings (text, number)",
        dict(
            xml_str=''
            '<IRETURNVALUE>'
            '  <VALUE>abc</VALUE>'
            '  <VALUE>42</VALUE>'
            '</IRETURNVALUE>',
            exp_result=(u'IRETURNVALUE', {}, [u'abc', u'42']),
        ),
        None, None, True
    ),
    (
        "IRETURNVALUE with one VALUE.ARRAY child",
        dict(
            xml_str=''
            '<IRETURNVALUE>'
            '  <VALUE.ARRAY/>'
            '</IRETURNVALUE>',
            exp_result=(u'IRETURNVALUE', {}, [[]]),
        ),
        None, None, True
    ),
    (
        "IRETURNVALUE with two VALUE.ARRAY children "
        "(overall invalid, but valid at this level)",
        dict(
            xml_str=''
            '<IRETURNVALUE>'
            '  <VALUE.ARRAY/>'
            '  <VALUE.ARRAY/>'
            '</IRETURNVALUE>',
            exp_result=(u'IRETURNVALUE', {}, [[], []]),
        ),
        None, None, True
    ),
    (
        "IRETURNVALUE with one VALUE.REFERENCE child",
        dict(
            xml_str=''
            '<IRETURNVALUE>'
            '  <VALUE.REFERENCE>'
            '    <CLASSNAME NAME="CIM_Foo"/>'
            '  </VALUE.REFERENCE>'
            '</IRETURNVALUE>',
            exp_result=(
                u'IRETURNVALUE', {},
                [
                    CIMClassName('CIM_Foo'),
                ]
            ),
        ),
        None, None, True
    ),
    (
        "IRETURNVALUE with two VALUE.REFERENCE children "
        "(overall invalid, but valid at this level)",
        dict(
            xml_str=''
            '<IRETURNVALUE>'
            '  <VALUE.REFERENCE>'
            '    <CLASSNAME NAME="CIM_Foo"/>'
            '  </VALUE.REFERENCE>'
            '  <VALUE.REFERENCE>'
            '    <CLASSNAME NAME="CIM_Bar"/>'
            '  </VALUE.REFERENCE>'
            '</IRETURNVALUE>',
            exp_result=(
                u'IRETURNVALUE', {},
                [
                    CIMClassName('CIM_Foo'),
                    CIMClassName('CIM_Bar'),
                ]
            ),
        ),
        None, None, True
    ),
    (
        "IRETURNVALUE with one OBJECTPATH child",
        dict(
            xml_str=''
            '<IRETURNVALUE>'
            '  <OBJECTPATH>'
            '    <CLASSPATH>'
            '      <NAMESPACEPATH>'
            '        <HOST>woot.com</HOST>'
            '        <LOCALNAMESPACEPATH>'
            '          <NAMESPACE NAME="foo"/>'
            '        </LOCALNAMESPACEPATH>'
            '      </NAMESPACEPATH>'
            '      <CLASSNAME NAME="CIM_Foo"/>'
            '    </CLASSPATH>'
            '  </OBJECTPATH>'
            '</IRETURNVALUE>',
            exp_result=(
                u'IRETURNVALUE', {},
                [
                    (
                        u'OBJECTPATH', {},
                        CIMClassName(
                            'CIM_Foo',
                            namespace='foo',
                            host='woot.com',
                        ),
                    ),
                ],
            ),
        ),
        None, None, True
    ),
    (
        "IRETURNVALUE with one OBJECTPATH child",
        dict(
            xml_str=''
            '<IRETURNVALUE>'
            '  <OBJECTPATH>'
            '    <CLASSPATH>'
            '      <NAMESPACEPATH>'
            '        <HOST>woot.com</HOST>'
            '        <LOCALNAMESPACEPATH>'
            '          <NAMESPACE NAME="foo"/>'
            '        </LOCALNAMESPACEPATH>'
            '      </NAMESPACEPATH>'
            '      <CLASSNAME NAME="CIM_Foo"/>'
            '    </CLASSPATH>'
            '  </OBJECTPATH>'
            '  <OBJECTPATH>'
            '    <CLASSPATH>'
            '      <NAMESPACEPATH>'
            '        <HOST>woot.com</HOST>'
            '        <LOCALNAMESPACEPATH>'
            '          <NAMESPACE NAME="foo"/>'
            '        </LOCALNAMESPACEPATH>'
            '      </NAMESPACEPATH>'
            '      <CLASSNAME NAME="CIM_Bar"/>'
            '    </CLASSPATH>'
            '  </OBJECTPATH>'
            '</IRETURNVALUE>',
            exp_result=(
                u'IRETURNVALUE', {},
                [
                    (
                        u'OBJECTPATH', {},
                        CIMClassName(
                            'CIM_Foo',
                            namespace='foo',
                            host='woot.com',
                        ),
                    ),
                    (
                        u'OBJECTPATH', {},
                        CIMClassName(
                            'CIM_Bar',
                            namespace='foo',
                            host='woot.com',
                        ),
                    ),
                ],
            ),
        ),
        None, None, True
    ),
    (
        "IRETURNVALUE with one INSTANCEPATH child",
        dict(
            xml_str=''
            '<IRETURNVALUE>'
            '  <INSTANCEPATH>'
            '    <NAMESPACEPATH>'
            '      <HOST>woot.com</HOST>'
            '      <LOCALNAMESPACEPATH>'
            '        <NAMESPACE NAME="foo"/>'
            '      </LOCALNAMESPACEPATH>'
            '    </NAMESPACEPATH>'
            '    <INSTANCENAME CLASSNAME="CIM_Foo"/>'
            '  </INSTANCEPATH>'
            '</IRETURNVALUE>',
            exp_result=(
                u'IRETURNVALUE', {},
                [
                    CIMInstanceName(
                        'CIM_Foo',
                        namespace='foo',
                        host='woot.com',
                    ),
                ],
            ),
        ),
        None, MissingKeybindingsWarning, True
    ),
    (
        "IRETURNVALUE with two INSTANCEPATH children (valid)",
        dict(
            xml_str=''
            '<IRETURNVALUE>'
            '  <INSTANCEPATH>'
            '    <NAMESPACEPATH>'
            '      <HOST>woot.com</HOST>'
            '      <LOCALNAMESPACEPATH>'
            '        <NAMESPACE NAME="foo"/>'
            '      </LOCALNAMESPACEPATH>'
            '    </NAMESPACEPATH>'
            '    <INSTANCENAME CLASSNAME="CIM_Foo"/>'
            '  </INSTANCEPATH>'
            '  <INSTANCEPATH>'
            '    <NAMESPACEPATH>'
            '      <HOST>woot.com</HOST>'
            '      <LOCALNAMESPACEPATH>'
            '        <NAMESPACE NAME="foo"/>'
            '      </LOCALNAMESPACEPATH>'
            '    </NAMESPACEPATH>'
            '    <INSTANCENAME CLASSNAME="CIM_Bar"/>'
            '  </INSTANCEPATH>'
            '</IRETURNVALUE>',
            exp_result=(
                u'IRETURNVALUE', {},
                [
                    CIMInstanceName(
                        'CIM_Foo',
                        namespace='foo',
                        host='woot.com',
                    ),
                    CIMInstanceName(
                        'CIM_Bar',
                        namespace='foo',
                        host='woot.com',
                    ),
                ],
            ),
        ),
        None, MissingKeybindingsWarning, True
    ),
    (
        "IRETURNVALUE with one CLASSNAME child",
        dict(
            xml_str=''
            '<IRETURNVALUE>'
            '  <CLASSNAME NAME="CIM_Foo"/>'
            '</IRETURNVALUE>',
            exp_result=(u'IRETURNVALUE', {},
                        [CIMClassName('CIM_Foo')]),
        ),
        None, None, True
    ),
    (
        "IRETURNVALUE with two CLASSNAME children (valid)",
        dict(
            xml_str=''
            '<IRETURNVALUE>'
            '  <CLASSNAME NAME="CIM_Foo"/>'
            '  <CLASSNAME NAME="CIM_Bar"/>'
            '</IRETURNVALUE>',
            exp_result=(u'IRETURNVALUE', {},
                        [CIMClassName('CIM_Foo'), CIMClassName('CIM_Bar')]),
        ),
        None, None, True
    ),
    (
        "IRETURNVALUE with one INSTANCENAME child",
        dict(
            xml_str=''
            '<IRETURNVALUE>'
            '  <INSTANCENAME CLASSNAME="CIM_Foo"/>'
            '</IRETURNVALUE>',
            exp_result=(u'IRETURNVALUE', {},
                        [CIMInstanceName('CIM_Foo')]),
        ),
        None, MissingKeybindingsWarning, True
    ),
    (
        "IRETURNVALUE with two INSTANCENAME children (valid)",
        dict(
            xml_str=''
            '<IRETURNVALUE>'
            '  <INSTANCENAME CLASSNAME="CIM_Foo"/>'
            '  <INSTANCENAME CLASSNAME="CIM_Bar"/>'
            '</IRETURNVALUE>',
            exp_result=(u'IRETURNVALUE', {},
                        [CIMInstanceName('CIM_Foo'),
                         CIMInstanceName('CIM_Bar')]),
        ),
        None, MissingKeybindingsWarning, True
    ),
    (
        "IRETURNVALUE with one VALUE.OBJECTWITHPATH child",
        dict(
            xml_str=''
            '<IRETURNVALUE>'
            '  <VALUE.OBJECTWITHPATH>'
            '    <CLASSPATH>'
            '      <NAMESPACEPATH>'
            '        <HOST>woot.com</HOST>'
            '        <LOCALNAMESPACEPATH>'
            '          <NAMESPACE NAME="foo"/>'
            '        </LOCALNAMESPACEPATH>'
            '      </NAMESPACEPATH>'
            '      <CLASSNAME NAME="CIM_Foo"/>'
            '    </CLASSPATH>'
            '    <CLASS NAME="CIM_Foo"/>'
            '  </VALUE.OBJECTWITHPATH>'
            '</IRETURNVALUE>',
            exp_result=(
                u'IRETURNVALUE', {},
                [
                    (
                        u'VALUE.OBJECTWITHPATH', {},
                        (
                            CIMClassName(
                                'CIM_Foo',
                                namespace='foo',
                                host='woot.com',
                            ),
                            CIMClass(
                                'CIM_Foo',
                                path=CIMClassName(
                                    'CIM_Foo',
                                    namespace='foo',
                                    host='woot.com',
                                ),
                            ),
                        ),
                    ),
                ],
            ),
        ),
        None, None, True
    ),
    (
        "IRETURNVALUE with two VALUE.OBJECTWITHPATH children (valid)",
        dict(
            xml_str=''
            '<IRETURNVALUE>'
            '  <VALUE.OBJECTWITHPATH>'
            '    <CLASSPATH>'
            '      <NAMESPACEPATH>'
            '        <HOST>woot.com</HOST>'
            '        <LOCALNAMESPACEPATH>'
            '          <NAMESPACE NAME="foo"/>'
            '        </LOCALNAMESPACEPATH>'
            '      </NAMESPACEPATH>'
            '      <CLASSNAME NAME="CIM_Foo"/>'
            '    </CLASSPATH>'
            '    <CLASS NAME="CIM_Foo"/>'
            '  </VALUE.OBJECTWITHPATH>'
            '  <VALUE.OBJECTWITHPATH>'
            '    <CLASSPATH>'
            '      <NAMESPACEPATH>'
            '        <HOST>woot.com</HOST>'
            '        <LOCALNAMESPACEPATH>'
            '          <NAMESPACE NAME="foo"/>'
            '        </LOCALNAMESPACEPATH>'
            '      </NAMESPACEPATH>'
            '      <CLASSNAME NAME="CIM_Bar"/>'
            '    </CLASSPATH>'
            '    <CLASS NAME="CIM_Bar"/>'
            '  </VALUE.OBJECTWITHPATH>'
            '</IRETURNVALUE>',
            exp_result=(
                u'IRETURNVALUE', {},
                [
                    (
                        u'VALUE.OBJECTWITHPATH', {},
                        (
                            CIMClassName(
                                'CIM_Foo',
                                namespace='foo',
                                host='woot.com',
                            ),
                            CIMClass(
                                'CIM_Foo',
                                path=CIMClassName(
                                    'CIM_Foo',
                                    namespace='foo',
                                    host='woot.com',
                                ),
                            ),
                        ),
                    ),
                    (
                        u'VALUE.OBJECTWITHPATH', {},
                        (
                            CIMClassName(
                                'CIM_Bar',
                                namespace='foo',
                                host='woot.com',
                            ),
                            CIMClass(
                                'CIM_Bar',
                                path=CIMClassName(
                                    'CIM_Bar',
                                    namespace='foo',
                                    host='woot.com',
                                ),
                            ),
                        ),
                    ),
                ],
            ),
        ),
        None, None, True
    ),
    (
        "IRETURNVALUE with one VALUE.OBJECTWITHLOCALPATH child",
        dict(
            xml_str=''
            '<IRETURNVALUE>'
            '  <VALUE.OBJECTWITHLOCALPATH>'
            '    <LOCALCLASSPATH>'
            '      <LOCALNAMESPACEPATH>'
            '        <NAMESPACE NAME="foo"/>'
            '      </LOCALNAMESPACEPATH>'
            '      <CLASSNAME NAME="CIM_Foo"/>'
            '    </LOCALCLASSPATH>'
            '    <CLASS NAME="CIM_Foo"/>'
            '  </VALUE.OBJECTWITHLOCALPATH>'
            '</IRETURNVALUE>',
            exp_result=(
                u'IRETURNVALUE', {},
                [
                    (
                        u'VALUE.OBJECTWITHLOCALPATH', {},
                        (
                            CIMClassName(
                                'CIM_Foo',
                                namespace='foo',
                            ),
                            CIMClass(
                                'CIM_Foo',
                                path=CIMClassName(
                                    'CIM_Foo',
                                    namespace='foo',
                                ),
                            ),
                        ),
                    ),
                ],
            ),
        ),
        None, None, True
    ),
    (
        "IRETURNVALUE with two VALUE.OBJECTWITHLOCALPATH children (valid)",
        dict(
            xml_str=''
            '<IRETURNVALUE>'
            '  <VALUE.OBJECTWITHLOCALPATH>'
            '    <LOCALCLASSPATH>'
            '      <LOCALNAMESPACEPATH>'
            '        <NAMESPACE NAME="foo"/>'
            '      </LOCALNAMESPACEPATH>'
            '      <CLASSNAME NAME="CIM_Foo"/>'
            '    </LOCALCLASSPATH>'
            '    <CLASS NAME="CIM_Foo"/>'
            '  </VALUE.OBJECTWITHLOCALPATH>'
            '  <VALUE.OBJECTWITHLOCALPATH>'
            '    <LOCALCLASSPATH>'
            '      <LOCALNAMESPACEPATH>'
            '        <NAMESPACE NAME="foo"/>'
            '      </LOCALNAMESPACEPATH>'
            '      <CLASSNAME NAME="CIM_Bar"/>'
            '    </LOCALCLASSPATH>'
            '    <CLASS NAME="CIM_Bar"/>'
            '  </VALUE.OBJECTWITHLOCALPATH>'
            '</IRETURNVALUE>',
            exp_result=(
                u'IRETURNVALUE', {},
                [
                    (
                        u'VALUE.OBJECTWITHLOCALPATH', {},
                        (
                            CIMClassName(
                                'CIM_Foo',
                                namespace='foo',
                            ),
                            CIMClass(
                                'CIM_Foo',
                                path=CIMClassName(
                                    'CIM_Foo',
                                    namespace='foo',
                                ),
                            ),
                        ),
                    ),
                    (
                        u'VALUE.OBJECTWITHLOCALPATH', {},
                        (
                            CIMClassName(
                                'CIM_Bar',
                                namespace='foo',
                            ),
                            CIMClass(
                                'CIM_Bar',
                                path=CIMClassName(
                                    'CIM_Bar',
                                    namespace='foo',
                                ),
                            ),
                        ),
                    ),
                ],
            ),
        ),
        None, None, True
    ),
    (
        "IRETURNVALUE with one VALUE.INSTANCEWITHPATH child",
        dict(
            xml_str=''
            '<IRETURNVALUE>'
            '  <VALUE.INSTANCEWITHPATH>'
            '    <INSTANCEPATH>'
            '      <NAMESPACEPATH>'
            '        <HOST>woot.com</HOST>'
            '        <LOCALNAMESPACEPATH>'
            '          <NAMESPACE NAME="foo"/>'
            '        </LOCALNAMESPACEPATH>'
            '      </NAMESPACEPATH>'
            '      <INSTANCENAME CLASSNAME="CIM_Foo"/>'
            '    </INSTANCEPATH>'
            '    <INSTANCE CLASSNAME="CIM_Foo"/>'
            '  </VALUE.INSTANCEWITHPATH>'
            '</IRETURNVALUE>',
            exp_result=(
                u'IRETURNVALUE', {},
                [
                    CIMInstance(
                        'CIM_Foo',
                        path=CIMInstanceName(
                            'CIM_Foo',
                            namespace='foo',
                            host='woot.com',
                        ),
                    ),
                ],
            ),
        ),
        None, MissingKeybindingsWarning, True
    ),
    (
        "IRETURNVALUE with two VALUE.INSTANCEWITHPATH children (valid)",
        dict(
            xml_str=''
            '<IRETURNVALUE>'
            '  <VALUE.INSTANCEWITHPATH>'
            '    <INSTANCEPATH>'
            '      <NAMESPACEPATH>'
            '        <HOST>woot.com</HOST>'
            '        <LOCALNAMESPACEPATH>'
            '          <NAMESPACE NAME="foo"/>'
            '        </LOCALNAMESPACEPATH>'
            '      </NAMESPACEPATH>'
            '      <INSTANCENAME CLASSNAME="CIM_Foo"/>'
            '    </INSTANCEPATH>'
            '    <INSTANCE CLASSNAME="CIM_Foo"/>'
            '  </VALUE.INSTANCEWITHPATH>'
            '  <VALUE.INSTANCEWITHPATH>'
            '    <INSTANCEPATH>'
            '      <NAMESPACEPATH>'
            '        <HOST>woot.com</HOST>'
            '        <LOCALNAMESPACEPATH>'
            '          <NAMESPACE NAME="foo"/>'
            '        </LOCALNAMESPACEPATH>'
            '      </NAMESPACEPATH>'
            '      <INSTANCENAME CLASSNAME="CIM_Bar"/>'
            '    </INSTANCEPATH>'
            '    <INSTANCE CLASSNAME="CIM_Bar"/>'
            '  </VALUE.INSTANCEWITHPATH>'
            '</IRETURNVALUE>',
            exp_result=(
                u'IRETURNVALUE', {},
                [
                    CIMInstance(
                        'CIM_Foo',
                        path=CIMInstanceName(
                            'CIM_Foo',
                            namespace='foo',
                            host='woot.com',
                        ),
                    ),
                    CIMInstance(
                        'CIM_Bar',
                        path=CIMInstanceName(
                            'CIM_Bar',
                            namespace='foo',
                            host='woot.com',
                        ),
                    ),
                ],
            ),
        ),
        None, MissingKeybindingsWarning, True
    ),
    (
        "IRETURNVALUE with one VALUE.NAMEDINSTANCE child",
        dict(
            xml_str=''
            '<IRETURNVALUE>'
            '  <VALUE.NAMEDINSTANCE>'
            '    <INSTANCENAME CLASSNAME="CIM_Foo"/>'
            '    <INSTANCE CLASSNAME="CIM_Foo"/>'
            '  </VALUE.NAMEDINSTANCE>'
            '</IRETURNVALUE>',
            exp_result=(
                u'IRETURNVALUE', {},
                [
                    CIMInstance(
                        'CIM_Foo',
                        path=CIMInstanceName('CIM_Foo'),
                    ),
                ],
            ),
        ),
        None, MissingKeybindingsWarning, True
    ),
    (
        "IRETURNVALUE with two VALUE.NAMEDINSTANCE children (valid)",
        dict(
            xml_str=''
            '<IRETURNVALUE>'
            '  <VALUE.NAMEDINSTANCE>'
            '    <INSTANCENAME CLASSNAME="CIM_Foo"/>'
            '    <INSTANCE CLASSNAME="CIM_Foo"/>'
            '  </VALUE.NAMEDINSTANCE>'
            '  <VALUE.NAMEDINSTANCE>'
            '    <INSTANCENAME CLASSNAME="CIM_Bar"/>'
            '    <INSTANCE CLASSNAME="CIM_Bar"/>'
            '  </VALUE.NAMEDINSTANCE>'
            '</IRETURNVALUE>',
            exp_result=(
                u'IRETURNVALUE', {},
                [
                    CIMInstance(
                        'CIM_Foo',
                        path=CIMInstanceName('CIM_Foo'),
                    ),
                    CIMInstance(
                        'CIM_Bar',
                        path=CIMInstanceName('CIM_Bar'),
                    ),
                ],
            ),
        ),
        None, MissingKeybindingsWarning, True
    ),
    (
        "IRETURNVALUE with one VALUE.OBJECT child",
        dict(
            xml_str=''
            '<IRETURNVALUE>'
            '  <VALUE.OBJECT>'
            '    <CLASS NAME="CIM_Foo"/>'
            '  </VALUE.OBJECT>'
            '</IRETURNVALUE>',
            exp_result=(
                u'IRETURNVALUE', {},
                [
                    (u'VALUE.OBJECT', {}, CIMClass('CIM_Foo')),
                ],
            ),
        ),
        None, None, True
    ),
    (
        "IRETURNVALUE with two VALUE.OBJECT children (valid)",
        dict(
            xml_str=''
            '<IRETURNVALUE>'
            '  <VALUE.OBJECT>'
            '    <CLASS NAME="CIM_Foo"/>'
            '  </VALUE.OBJECT>'
            '  <VALUE.OBJECT>'
            '    <CLASS NAME="CIM_Bar"/>'
            '  </VALUE.OBJECT>'
            '</IRETURNVALUE>',
            exp_result=(
                u'IRETURNVALUE', {},
                [
                    (u'VALUE.OBJECT', {}, CIMClass('CIM_Foo')),
                    (u'VALUE.OBJECT', {}, CIMClass('CIM_Bar')),
                ],
            ),
        ),
        None, None, True
    ),
    (
        "IRETURNVALUE with one CLASS child",
        dict(
            xml_str=''
            '<IRETURNVALUE>'
            '  <CLASS NAME="CIM_Foo"/>'
            '</IRETURNVALUE>',
            exp_result=(
                u'IRETURNVALUE', {},
                [
                    CIMClass('CIM_Foo'),
                ],
            ),
        ),
        None, None, True
    ),
    (
        "IRETURNVALUE with two CLASS children (valid)",
        dict(
            xml_str=''
            '<IRETURNVALUE>'
            '  <CLASS NAME="CIM_Foo"/>'
            '  <CLASS NAME="CIM_Bar"/>'
            '</IRETURNVALUE>',
            exp_result=(
                u'IRETURNVALUE', {},
                [
                    CIMClass('CIM_Foo'),
                    CIMClass('CIM_Bar'),
                ],
            ),
        ),
        None, None, True
    ),
    (
        "IRETURNVALUE with one INSTANCE child",
        dict(
            xml_str=''
            '<IRETURNVALUE>'
            '  <INSTANCE CLASSNAME="CIM_Foo"/>'
            '</IRETURNVALUE>',
            exp_result=(
                u'IRETURNVALUE', {},
                [
                    CIMInstance('CIM_Foo'),
                ],
            ),
        ),
        None, None, True
    ),
    (
        "IRETURNVALUE with two INSTANCE children (valid)",
        dict(
            xml_str=''
            '<IRETURNVALUE>'
            '  <INSTANCE CLASSNAME="CIM_Foo"/>'
            '  <INSTANCE CLASSNAME="CIM_Bar"/>'
            '</IRETURNVALUE>',
            exp_result=(
                u'IRETURNVALUE', {},
                [
                    CIMInstance('CIM_Foo'),
                    CIMInstance('CIM_Bar'),
                ],
            ),
        ),
        None, None, True
    ),
    (
        "IRETURNVALUE with one QUALIFIER.DECLARATION child",
        dict(
            xml_str=''
            '<IRETURNVALUE>'
            '  <QUALIFIER.DECLARATION NAME="Qual" TYPE="string"/>'
            '</IRETURNVALUE>',
            exp_result=(
                u'IRETURNVALUE', {},
                [
                    CIMQualifierDeclaration(
                        'Qual', value=None, type='string',
                        **qualifier_declaration_default_attrs()
                    ),
                ],
            ),
        ),
        None, None, True
    ),
    (
        "IRETURNVALUE with two QUALIFIER.DECLARATION children (valid)",
        dict(
            xml_str=''
            '<IRETURNVALUE>'
            '  <QUALIFIER.DECLARATION NAME="Qual" TYPE="string"/>'
            '  <QUALIFIER.DECLARATION NAME="Qua2" TYPE="string"/>'
            '</IRETURNVALUE>',
            exp_result=(
                u'IRETURNVALUE', {},
                [
                    CIMQualifierDeclaration(
                        'Qual', value=None, type='string',
                        **qualifier_declaration_default_attrs()
                    ),
                    CIMQualifierDeclaration(
                        'Qua2', value=None, type='string',
                        **qualifier_declaration_default_attrs()
                    ),
                ],
            ),
        ),
        None, None, True
    ),

    # ERROR tests:
    #
    #   <!ELEMENT ERROR (INSTANCE*)>
    #   <!ATTLIST ERROR
    #       CODE CDATA #REQUIRED
    #       DESCRIPTION CDATA #IMPLIED>
    (
        "ERROR with invalid child element",
        dict(
            xml_str=''
            '<ERROR>'
            '  <XXX/>'
            '</ERROR>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "ERROR with invalid attribute",
        dict(
            xml_str=''
            '<ERROR XXX="bla"/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "ERROR with CODE attribute (minimal case)",
        dict(
            xml_str=''
            '<ERROR CODE="5"/>',
            exp_result=(u'ERROR', {u'CODE': u'5'}, []),
        ),
        None, None, True
    ),
    (
        "ERROR with CODE and DESCRIPTION attributes",
        dict(
            xml_str=''
            '<ERROR CODE="5" DESCRIPTION="bla"/>',
            exp_result=(u'ERROR', {u'CODE': u'5', u'DESCRIPTION': u'bla'}, []),
        ),
        None, None, True
    ),
    (
        "ERROR with CODE attribute and INSTANCE child",
        dict(
            xml_str=''
            '<ERROR CODE="5">'
            '  <INSTANCE CLASSNAME="CIM_Foo"/>'
            '</ERROR>',
            exp_result=(
                u'ERROR', {u'CODE': u'5'},
                [
                    CIMInstance('CIM_Foo'),
                ]
            ),
        ),
        None, None, True
    ),
    (
        "ERROR with CODE attribute and two INSTANCE children (valid)",
        dict(
            xml_str=''
            '<ERROR CODE="5">'
            '  <INSTANCE CLASSNAME="CIM_Foo"/>'
            '  <INSTANCE CLASSNAME="CIM_Bar"/>'
            '</ERROR>',
            exp_result=(
                u'ERROR', {u'CODE': u'5'},
                [
                    CIMInstance('CIM_Foo'),
                    CIMInstance('CIM_Bar'),
                ]
            ),
        ),
        None, None, True
    ),

    # CORRELATOR tests: Parsing this element is not implemented
    (
        "CORRELATOR (not implemented)",
        dict(
            xml_str=''
            '<CORRELATOR/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_TUPLEPARSE_XML)
@simplified_test_function
def test_tupleparse_xml(testcase, xml_str, exp_result):
    """
    Test tupleparse parsing, based upon a CIM-XML string as input.

    The input CIM-XML string is parsed and the result is compared with an
    expected result.
    """

    # This way to create a tuple tree is also used in _imethodcall() etc.
    tt = _tupletree.xml_to_tupletree_sax(xml_str, 'Test-XML')

    tp = _tupleparse.TupleParser()

    # The code to be tested
    result = tp.parse_any(tt)

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None

    assert result == exp_result, "Input CIM-XML:\n%s" % xml_str
