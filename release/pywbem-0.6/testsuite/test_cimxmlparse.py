#!/usr/bin/python
#
# Test XML parsing routines.
#
# These tests check that we don't lose any information by converting
# an object to XML then parsing it again.  The round trip should
# produce an object that is identical to the one we started with.
#

from comfychair import main, TestCase
from pywbem import *

from pywbem.cimxml_parse import parse_any

class RoundTripTest(TestCase):

    def test(self, obj):

        # Convert object to xml

        xml = obj.tocimxml().toxml()
        self.log('before: %s' % xml)

        # Parse back to an object

        p = parse_any(xml)
        self.log('after:  %s' % p.tocimxml().toxml())

        # Assert that the before and after objects should be equal
        
        self.assert_equal(obj, p)

class RawXMLTest(TestCase):

    def test(self, xml, obj):

        # Parse raw XML to an object

        self.log('before: %s' % xml)
        p = parse_any(xml)
        self.log('after: %s' % p)

        # Assert XML parses to particular Python object

        self.assert_equal(obj, p)

class ParseXMLKeyvalue(RawXMLTest):

    def runtest(self):

        self.test(
            '<KEYVALUE VALUETYPE="string">1234</KEYVALUE>',
            '1234')

        self.test(
            '<KEYVALUE VALUETYPE="numeric">1234</KEYVALUE>',
            1234)

        # XXX: At the moment we don't worry about the TYPE attribute,
        # only that it parses correctly.

        self.test(
            '<KEYVALUE TYPE="uint32" VALUETYPE="numeric">1234</KEYVALUE>',
            1234)

        self.test(
            '<KEYVALUE VALUETYPE="boolean">true</KEYVALUE>',
            True)

class ParseXMLInstancename(RawXMLTest):

    def runtest(self):

        self.test(
            '<INSTANCENAME CLASSNAME="CIM_Foo"/>',
            CIMInstanceName('CIM_Foo'))

        self.test(
            '<INSTANCENAME CLASSNAME="CIM_Foo"><KEYBINDING NAME="InstanceID">'
            '<KEYVALUE VALUETYPE="string">1234</KEYVALUE></KEYBINDING>'
            '</INSTANCENAME>',
            CIMInstanceName('CIM_Foo', {'InstanceID': '1234'}))

        # XXX: single KEYVALUE form not supported

        self.test(
            '<INSTANCENAME CLASSNAME="CIM_Foo"><KEYBINDING NAME="Ref">'
            '<VALUE.REFERENCE><INSTANCENAME CLASSNAME="CIM_Bar">'
            '<KEYBINDING NAME="InstanceID"><KEYVALUE VALUETYPE="string">'
            '1234</KEYVALUE></KEYBINDING></INSTANCENAME></VALUE.REFERENCE>'
            '</KEYBINDING></INSTANCENAME>',
            CIMInstanceName(
            'CIM_Foo',
            {'Ref': CIMInstanceName('CIM_Bar', {'InstanceID': '1234'})}))

class ParseXMLValue(RawXMLTest):

    def runtest(self):

        self.test(
            '<VALUE>1234</VALUE>',
            '1234')

        # TODO: empty string
        # TODO: null string

class ParseXMLValueArray(RawXMLTest):

    def runtest(self):

        self.test(
            '<VALUE.ARRAY><VALUE>1234</VALUE><VALUE>5678</VALUE>'
            '</VALUE.ARRAY>',
            ['1234', '5678'])

class ParseXMLQualifier(RawXMLTest):

    def runtest(self):

        self.test(
            '<QUALIFIER NAME="ASSOCIATION" TYPE="boolean"><VALUE>TRUE</VALUE>'
            '</QUALIFIER>',
            CIMQualifier('ASSOCIATION', True))

        self.test(
            '<QUALIFIER NAME="Age" TYPE="uint32"><VALUE>1234</VALUE>'
            '</QUALIFIER>',
            CIMQualifier('Age', Uint32(1234)))

        self.test(
            '<QUALIFIER NAME="List" TYPE="uint8"><VALUE.ARRAY><VALUE>1</VALUE>'
            '<VALUE>2</VALUE><VALUE>3</VALUE><VALUE>4</VALUE></VALUE.ARRAY>'
            '</QUALIFIER>',
            CIMQualifier('List', [Uint8(i) for i in [1, 2, 3, 4]]))


class ParseXMLProperty(RawXMLTest):

    def runtest(self):

        self.test(
            '<PROPERTY NAME="Foo" TYPE="uint32"></PROPERTY>',
            CIMProperty('Foo', None, type = 'uint32'))

        self.test(
            '<PROPERTY NAME="Foo" TYPE="uint32"><VALUE>1234</VALUE>'
            '</PROPERTY>',
            CIMProperty('Foo', Uint32(1234)))

        self.test(
            '<PROPERTY NAME="Foo" TYPE="uint32">'
            '<QUALIFIER NAME="ASSOCIATION" TYPE="boolean">'
            '<VALUE>TRUE</VALUE></QUALIFIER><VALUE>1234</VALUE></PROPERTY>',
            CIMProperty(
                'Foo',
                 Uint32(1234),
                qualifiers = {'ASSOCIATION':
                              CIMQualifier('ASSOCIATION', True)}))

class ParseRoundtripInstance(RoundTripTest):

    def runtest(self):

        self.test(CIMInstance('CIM_Foo'))
        self.test(CIMInstance('CIM_Foo', {'InstanceID': '1234'}))

#################################################################
# Main function
#################################################################

tests = [

    # Parse specific bits of XML

    ParseXMLKeyvalue,
    ParseXMLInstancename,
    ParseXMLValue,
    ParseXMLValueArray,
    ParseXMLQualifier,
    ParseXMLProperty,

    # Round trip tests
    
    ParseRoundtripInstance,
    
    ]

if __name__ == '__main__':
    main(tests)
