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

from pywbem.tupletree import xml_to_tupletree
from pywbem.tupleparse import parse_any

class TupleTest(TestCase):

    def test(self, obj):

        # Convert object to xml

        xml = obj.tocimxml().toxml()
        self.log('before: %s' % xml)

        # Parse back to an object

        result = parse_any(xml_to_tupletree(xml))
        self.log('after:  %s' % result.tocimxml().toxml())

        # Assert that the before and after objects should be equal
        
        self.assert_equal(obj, result)

class RawXMLTest(TestCase):

    def test(self, xml, obj):

        # Parse raw XML to an object

        result = parse_any(xml_to_tupletree(xml))
        self.log('parsed XML: %s' % result)

        # Assert XML parses to particular Python object

        self.assert_equal(obj, result)

class ParseCIMInstanceName(TupleTest):
    """Test parsing of CIMInstanceName objects."""
           
    def runtest(self):

        self.test(CIMInstanceName('CIM_Foo'))

        self.test(CIMInstanceName('CIM_Foo',
                                  {'Name': 'Foo',
                                   'Chicken': 'Ham'}))

        self.test(
            CIMInstanceName('CIM_Foo', {'Name': 'Foo',
                                        'Number': 42,
                                        'Boolean': False,
                                        'Ref': CIMInstanceName('CIM_Bar')}))

        self.test(
            CIMInstanceName('CIM_Foo', {'Name': 'Foo'},
                            namespace = 'root/cimv2'))

        self.test(
            CIMInstanceName('CIM_Foo', {'Name': 'Foo'},
                            host = 'woot.com',
                            namespace = 'root/cimv2'))

class ParseCIMInstance(TupleTest):
    """Test parsing of CIMInstance objects."""
    
    def runtest(self):

        self.test(CIMInstance('CIM_Foo'))

        self.test(
            CIMInstance(
            'CIM_Foo',
            {'string': 'string',
             'uint8': Uint8(0),
             'uint8array': [Uint8(1), Uint8(2)],
             'ref': CIMInstanceName('CIM_Bar')}))

        self.test(
            CIMInstance('CIM_Foo',
                        {'InstanceID': '1234'},
                        path = CIMInstanceName('CIM_Foo',
                                               {'InstanceID': '1234'})))
        
class ParseCIMClass(TupleTest):
    """Test parsing of CIMClass objects."""

    def runtest(self):

        self.test(CIMClass('CIM_Foo'))
        self.test(CIMClass('CIM_Foo', superclass = 'CIM_bar'))

        self.test(CIMClass(
            'CIM_CollectionInSystem',
            qualifiers = {'ASSOCIATION':
                          CIMQualifier('ASSOCIATION', True,
                                       overridable = False),

                          'Aggregation':
                          CIMQualifier('Aggregation', True,
                                       overridable = False),
                          'Version':
                          CIMQualifier('Version', '2.6.0',
                                       tosubclass = False,
                                       translatable = False),
                          'Description':
                          CIMQualifier('Description',
                                       'CIM_CollectionInSystem is an association used to establish a parent-child relationship between a collection and an \'owning\' System such as an AdminDomain or ComputerSystem. A single collection should not have both a CollectionInOrganization and a CollectionInSystem association.',
                                       translatable = True)},
            properties = {'Parent':
                          CIMProperty(
                            'Parent', None, type = 'reference',
                            reference_class = 'CIM_System',
                            qualifiers = {'Key':
                                          CIMQualifier('Key', True,
                                                       overridable = False),
                                          'Aggregate':
                                          CIMQualifier('Aggregate', True,
                                                       overridable = False),
                                          'Max':
                                          CIMQualifier('Max', Uint32(1))}),
                          'Child':
                          CIMProperty(
                              'Child', None, type = 'reference',
                              reference_class = 'CIM_Collection',
                              qualifiers = {'Key':
                                            CIMQualifier('Key', True,
                                                         overridable = False)}
                              )
                          }
            ))
         
class ParseCIMProperty(TupleTest):
    """Test parsing of CIMProperty objects."""

    def runtest(self):

        # Single-valued properties

        self.test(CIMProperty('Spotty', 'Foot'))
        self.test(CIMProperty('Age', Uint16(32)))
        self.test(CIMProperty('Foo', '', type = 'string'))
        self.test(CIMProperty('Foo', None, type = 'string'))
        self.test(CIMProperty('Age', None, type = 'uint16',
                              qualifiers = {'Key': CIMQualifier('Key', True)}))

        # Property arrays

        self.test(CIMProperty('Foo', ['a', 'b', 'c']))
        self.test(CIMProperty('Foo', None, type = 'string', is_array = True))
        self.test(CIMProperty('Foo', [Uint8(x) for x in [1, 2, 3]],
                              qualifiers = {'Key': CIMQualifier('Key', True)}))

        # Reference properties
                              
        self.test(CIMProperty('Foo', None, type = 'reference'))
        self.test(CIMProperty('Foo', CIMInstanceName('CIM_Foo')))
        self.test(CIMProperty('Foo', CIMInstanceName('CIM_Foo'),
                              qualifiers = {'Key': CIMQualifier('Key', True)}))

        # EmbeddedObject properties

	inst = CIMInstance('Foo_Class', 
                     {'one':Uint8(1), 'two':Uint8(2)})
	self.test(CIMProperty('Foo', inst))
	self.test(CIMProperty('Foo', [inst]))
                              
        
class ParseCIMParameter(TupleTest):
    """Test parsing of CIMParameter objects."""

    def runtest(self):

        # Single-valued parameters

        self.test(CIMParameter('Param', 'string'))

        self.test(CIMParameter('Param', 'string',
                               qualifiers =
                               {'Key': CIMQualifier('Key', True)}))

        # Reference parameters

        self.test(CIMParameter('RefParam', 'reference'))

        self.test(CIMParameter('RefParam', 'reference',
                               reference_class = 'CIM_Foo'))

        self.test(CIMParameter('RefParam', 'reference',
                               reference_class = 'CIM_Foo',
                               qualifiers =
                               {'Key': CIMQualifier('Key', True)}))

        # Array parameters

        self.test(CIMParameter('Array', 'string', is_array = True))

        self.test(CIMParameter('Array', 'string', is_array = True,
                               array_size = 10))

        self.test(CIMParameter('Array', 'string', is_array = True,
                               array_size = 10,
                               qualifiers =
                               {'Key': CIMQualifier('Key', True)}))

        # Reference array parameters

        self.test(CIMParameter('RefArray', 'reference', is_array = True))

        self.test(CIMParameter('RefArray', 'reference', is_array = True,
                               reference_class = 'CIM_Foo'))

        self.test(CIMParameter('RefArray', 'reference', is_array = True,
                               reference_class = 'CIM_Foo',
                               array_size = 10))
        
        self.test(CIMParameter('RefArray', 'reference', is_array = True,
                               reference_class = 'CIM_Foo',
                               array_size = 10,
                               qualifiers =
                               {'Key': CIMQualifier('Key', True)}))

        
class ParseXMLKeyValue(RawXMLTest):

    def runtest(self):

        self.test(
            '<KEYVALUE VALUETYPE="numeric">1234</KEYVALUE>',
            1234)

        self.test(
            '<KEYVALUE TYPE="uint32" VALUETYPE="numeric">1234</KEYVALUE>',
            1234)

#################################################################
# Main function
#################################################################

tests = [

    # "Round trip" parsing functions

    ParseCIMInstanceName,
    ParseCIMInstance,
    ParseCIMClass,
    ParseCIMProperty,
    ParseCIMParameter,

    # Parse specific bits of XML

    ParseXMLKeyValue,
    
    ]

if __name__ == '__main__':
    main(tests)
