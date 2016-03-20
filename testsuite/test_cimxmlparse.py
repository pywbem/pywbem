#!/usr/bin/env python
#
# Test XML parsing routines.
#
# These tests check that we don't lose any information by converting
# an object to XML then parsing it again.  The round trip should
# produce an object that is identical to the one we started with.
#

import unittest

from pywbem import cimxml_parse
from pywbem import CIMInstance, CIMInstanceName, CIMProperty, CIMQualifier, \
                   Uint8, Uint32


class RoundTripTest(unittest.TestCase):

    def _run_single(self, obj):

        # Convert object to xml

        xml = obj.tocimxml().toxml()

        # Parse back to an object

        p = cimxml_parse.parse_any(xml)

        # Assert that the before and after objects should be equal

        self.assertEqual(obj, p,
                         '\nbefore: %s\nafter:  %s' %\
                         (xml, p.tocimxml().toxml()))

class RawXMLTest(unittest.TestCase):

    def _run_single(self, xml, obj):

        # Parse raw XML to an object

        p = cimxml_parse.parse_any(xml)

        # Assert XML parses to particular Python object

        self.assertEqual(obj, p,
                         '\nbefore: %s\nafter:  %s' %\
                         (xml, p))

class ParseXMLKeyvalue(RawXMLTest):

    def test_all(self):

        self._run_single(
            '<KEYVALUE VALUETYPE="string">1234</KEYVALUE>',
            '1234')

        self._run_single(
            '<KEYVALUE VALUETYPE="numeric">1234</KEYVALUE>',
            1234)

        # XXX: At the moment we don't worry about the TYPE attribute,
        # only that it parses correctly.

        self._run_single(
            '<KEYVALUE TYPE="uint32" VALUETYPE="numeric">1234</KEYVALUE>',
            1234)

        self._run_single(
            '<KEYVALUE VALUETYPE="boolean">true</KEYVALUE>',
            True)

class ParseXMLInstancename(RawXMLTest):

    def test_all(self):

        self._run_single(
            '<INSTANCENAME CLASSNAME="CIM_Foo"/>',
            CIMInstanceName('CIM_Foo'))

        self._run_single(
            '<INSTANCENAME CLASSNAME="CIM_Foo"><KEYBINDING NAME="InstanceID">'
            '<KEYVALUE VALUETYPE="string">1234</KEYVALUE></KEYBINDING>'
            '</INSTANCENAME>',
            CIMInstanceName('CIM_Foo', {'InstanceID': '1234'}))

        # XXX: single KEYVALUE form not supported

        self._run_single(
            '<INSTANCENAME CLASSNAME="CIM_Foo"><KEYBINDING NAME="Ref">'
            '<VALUE.REFERENCE><INSTANCENAME CLASSNAME="CIM_Bar">'
            '<KEYBINDING NAME="InstanceID"><KEYVALUE VALUETYPE="string">'
            '1234</KEYVALUE></KEYBINDING></INSTANCENAME></VALUE.REFERENCE>'
            '</KEYBINDING></INSTANCENAME>',
            CIMInstanceName(
                'CIM_Foo',
                {'Ref': CIMInstanceName('CIM_Bar', {'InstanceID': '1234'})}))

class ParseXMLValue(RawXMLTest):

    def test_all(self):

        self._run_single(
            '<VALUE>1234</VALUE>',
            '1234')

        # TODO: empty string
        # TODO: null string

class ParseXMLValueArray(RawXMLTest):

    def test_all(self):

        self._run_single(
            '<VALUE.ARRAY><VALUE>1234</VALUE><VALUE>5678</VALUE>'
            '</VALUE.ARRAY>',
            ['1234', '5678'])

class ParseXMLQualifier(RawXMLTest):

    def test_all(self):

        self._run_single(
            '<QUALIFIER NAME="ASSOCIATION" TYPE="boolean"><VALUE>TRUE</VALUE>'
            '</QUALIFIER>',
            CIMQualifier('ASSOCIATION', True))

        self._run_single(
            '<QUALIFIER NAME="Age" TYPE="uint32"><VALUE>1234</VALUE>'
            '</QUALIFIER>',
            CIMQualifier('Age', Uint32(1234)))

        self._run_single(
            '<QUALIFIER NAME="List" TYPE="uint8"><VALUE.ARRAY><VALUE>1</VALUE>'
            '<VALUE>2</VALUE><VALUE>3</VALUE><VALUE>4</VALUE></VALUE.ARRAY>'
            '</QUALIFIER>',
            CIMQualifier('List', [Uint8(i) for i in [1, 2, 3, 4]]))


class ParseXMLProperty(RawXMLTest):

    def test_all(self):

        self._run_single(
            '<PROPERTY NAME="Foo" TYPE="uint32"></PROPERTY>',
            CIMProperty('Foo', None, type='uint32'))

        self._run_single(
            '<PROPERTY NAME="Foo" TYPE="uint32"><VALUE>1234</VALUE>'
            '</PROPERTY>',
            CIMProperty('Foo', Uint32(1234)))

        self._run_single(
            '<PROPERTY NAME="Foo" TYPE="uint32">'
            '<QUALIFIER NAME="ASSOCIATION" TYPE="boolean">'
            '<VALUE>TRUE</VALUE></QUALIFIER><VALUE>1234</VALUE></PROPERTY>',
            CIMProperty(
                'Foo',
                Uint32(1234),
                qualifiers={'ASSOCIATION':
                            CIMQualifier('ASSOCIATION', True)}))

class ParseRoundtripInstance(RoundTripTest):

    def test_all(self):

        self._run_single(CIMInstance('CIM_Foo'))
        self._run_single(CIMInstance('CIM_Foo', {'InstanceID': '1234'}))


if __name__ == '__main__':
    unittest.main()
