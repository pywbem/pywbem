#!/usr/bin/env python
#

"""
Test XML parsing routines.

These tests check that we don't lose any information by converting
an object to XML then parsing it again.  The round trip should
produce an object that is identical to the one we started with.
"""
import unittest
import pytest

from pywbem import tupletree, tupleparse
from pywbem import CIMInstance, CIMInstanceName, CIMClass, \
                   CIMProperty, CIMParameter, CIMQualifier, \
                   Uint8, Uint16, Uint32


class TupleTest(unittest.TestCase):

    def _run_single(self, obj):

        # Convert object to xml

        xml = obj.tocimxml().toxml()

        # Parse back to an object

        result = tupleparse.parse_any(tupletree.xml_to_tupletree(xml))

        # Assert that the before and after objects should be equal

        self.assertEqual(obj, result,
                         'before: %s\nafter:  %s' %\
                         (xml, result.tocimxml().toxml()))

class RawXMLTest(unittest.TestCase):

    def _run_single(self, xml, obj):

        # Parse raw XML to an object

        result = tupleparse.parse_any(tupletree.xml_to_tupletree(xml))

        # Assert XML parses to particular Python object

        self.assertEqual(obj, result,
                         'parsed XML: %s' % result)

class ParseCIMInstanceName(TupleTest):
    """Test parsing of CIMInstanceName objects."""

    def test_all(self):

        self._run_single(CIMInstanceName('CIM_Foo'))

        self._run_single(CIMInstanceName('CIM_Foo',
                                         {'Name': 'Foo',
                                          'Chicken': 'Ham'}))

        self._run_single(
            CIMInstanceName('CIM_Foo', {'Name': 'Foo',
                                        'Number': 42,
                                        'Boolean': False,
                                        'Ref': CIMInstanceName('CIM_Bar')}))

        self._run_single(
            CIMInstanceName('CIM_Foo', {'Name': 'Foo'},
                            namespace='root/cimv2'))

        self._run_single(
            CIMInstanceName('CIM_Foo', {'Name': 'Foo'},
                            host='woot.com',
                            namespace='root/cimv2'))

class ParseCIMInstance(TupleTest):
    """Test parsing of CIMInstance objects."""

    def test_all(self):

        self._run_single(CIMInstance('CIM_Foo'))

        self._run_single(
            CIMInstance(
                'CIM_Foo',
                {'string': 'string',
                 'uint8': Uint8(0),
                 'uint8array': [Uint8(1), Uint8(2)],
                 'ref': CIMInstanceName('CIM_Bar')}))

        self._run_single(
            CIMInstance('CIM_Foo',
                        {'InstanceID': '1234'},
                        path=CIMInstanceName('CIM_Foo',
                                             {'InstanceID': '1234'})))

# TODO: 2/8/16: ks: Create test for more complete class
class ParseCIMClass(TupleTest):
    """Test parsing of CIMClass objects."""

    def test_all(self):

        self._run_single(CIMClass('CIM_Foo'))
        self._run_single(CIMClass('CIM_Foo', superclass='CIM_bar'))

        self._run_single(CIMClass(
            'CIM_CollectionInSystem',
            qualifiers={'ASSOCIATION':
                        CIMQualifier('ASSOCIATION', True,
                                     overridable=False),

                        'Aggregation':
                        CIMQualifier('Aggregation', True,
                                     overridable=False),
                        'Version':
                        CIMQualifier('Version', '2.6.0',
                                     tosubclass=False,
                                     translatable=False),
                        'Description':
                        CIMQualifier('Description',
                                     'CIM_CollectionInSystem is an ' \
                                     'association used to establish a ' \
                                     'parent-child relationship between a ' \
                                     'collection and an \'owning\' System ' \
                                     'such as an AdminDomain or '\
                                     'ComputerSystem. A single collection '\
                                     'should not have both a ' \
                                     'CollectionInOrganization and a ' \
                                     'CollectionInSystem association.',
                                     translatable=True)},
            properties={'Parent':
                        CIMProperty(
                            'Parent', None, type='reference',
                            reference_class='CIM_System',
                            qualifiers={'Key':
                                        CIMQualifier('Key', True,
                                                     overridable=False),
                                        'Aggregate':
                                        CIMQualifier('Aggregate', True,
                                                     overridable=False),
                                        'Max':
                                        CIMQualifier('Max', Uint32(1))}),
                        'Child':
                        CIMProperty(
                            'Child', None, type='reference',
                            reference_class='CIM_Collection',
                            qualifiers={'Key':
                                        CIMQualifier('Key', True,
                                                     overridable=False)}
                            )
                       }
            ))

# TODO extend to all property data types
class ParseCIMProperty(TupleTest):
    """Test parsing of CIMProperty objects."""

    def test_all(self):

        # Single-valued properties

        self._run_single(CIMProperty('Spotty', 'Foot'))
        self._run_single(CIMProperty('Age', Uint16(32)))
        self._run_single(CIMProperty('Foo', '', type='string'))
        self._run_single(CIMProperty('Foo', None, type='string'))
        self._run_single(CIMProperty('Age', None, type='uint16',
                                     qualifiers={'Key': CIMQualifier('Key',
                                                                     True)}))

        # Property arrays

        self._run_single(CIMProperty('Foo', ['a', 'b', 'c']))
        self._run_single(CIMProperty('Foo', None, type='string', is_array=True))
        self._run_single(CIMProperty('Foo', [Uint8(x) for x in [1, 2, 3]],
                                     qualifiers={'Key': CIMQualifier('Key',
                                                                     True)}))

        # Reference properties

        self._run_single(CIMProperty('Foo', None, type='reference'))
        self._run_single(CIMProperty('Foo', CIMInstanceName('CIM_Foo')))
        self._run_single(CIMProperty('Foo', CIMInstanceName('CIM_Foo'),
                                     qualifiers={'Key': CIMQualifier('Key',
                                                                     True)}))

        # EmbeddedObject properties

        inst = CIMInstance('Foo_Class',
                           {'one': Uint8(1), 'two': Uint8(2)})
        self._run_single(CIMProperty('Foo', inst))
        self._run_single(CIMProperty('Foo', [inst]))

# TODO: Feb/16: ks: Extend for all data types
class ParseCIMParameter(TupleTest):
    """Test parsing of CIMParameter objects."""

    def test_all(self):

        # Single-valued parameters

        self._run_single(CIMParameter('Param', 'string'))

        self._run_single(CIMParameter('Param', 'string',
                                      qualifiers={'Key': CIMQualifier('Key',
                                                                      True)}))

        # Reference parameters

        self._run_single(CIMParameter('RefParam', 'reference'))

        self._run_single(CIMParameter('RefParam', 'reference',
                                      reference_class='CIM_Foo'))

        self._run_single(CIMParameter('RefParam', 'reference',
                                      reference_class='CIM_Foo',
                                      qualifiers={'Key': CIMQualifier('Key',
                                                                      True)}))

        # Array parameters

        self._run_single(CIMParameter('Array', 'string', is_array=True))

        self._run_single(CIMParameter('Array', 'string', is_array=True,
                                      array_size=10))

        self._run_single(CIMParameter('Array', 'string', is_array=True,
                                      array_size=10,
                                      qualifiers={'Key': CIMQualifier('Key',
                                                                      True)}))

        # Reference array parameters

        self._run_single(CIMParameter('RefArray', 'reference',
                                      is_array=True))

        self._run_single(CIMParameter('RefArray', 'reference',
                                      is_array=True,
                                      reference_class='CIM_Foo'))

        self._run_single(CIMParameter('RefArray', 'reference',
                                      is_array=True,
                                      reference_class='CIM_Foo',
                                      array_size=10))

        self._run_single(CIMParameter('RefArray', 'reference',
                                      is_array=True,
                                      reference_class='CIM_Foo',
                                      array_size=10,
                                      qualifiers={'Key': CIMQualifier('Key',
                                                                      True)}))


class ParseXMLKeyValue(RawXMLTest):

    def test_all(self):

        self._run_single(
            '<KEYVALUE VALUETYPE="numeric">1234</KEYVALUE>',
            1234)

        self._run_single(
            '<KEYVALUE TYPE="uint32" VALUETYPE="numeric">1234</KEYVALUE>',
            1234)


if __name__ == '__main__':
    unittest.main()
