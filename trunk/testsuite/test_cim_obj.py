#!/usr/bin/python
#
# Test CIM object interface.
#
# Ideally this file would completely describe the Python interface to
# CIM objects.  If a particular data structure or Python property is
# not implemented here, then it is not officially supported by PyWBEM.
# Any breaking of backwards compatibility of new development should be
# picked up here.
#

from datetime import timedelta

from comfychair import main, TestCase, NotRunError
from pywbem import *
from validate import validate_xml

class ValidateTest(TestCase):

    def validate(self, obj):
        """Run a CIM XML fragment through the validator."""
        self.log(obj.tocimxml().toxml())
        assert(validate_xml(obj.tocimxml().toxml(), dtd_directory = '../..'))

class DictTest(TestCase):

    def runtest_dict(self, obj):

        # Test __getitem__

        self.assert_(obj['Chicken'] == 'Ham')
        self.assert_(obj['Beans'] == 42)

        try:
            obj['Cheepy']
        except KeyError:
            pass
        else:
            self.fail('KeyError not thrown')

        # Test __setitem__

        obj['tmp'] = 'tmp'
        self.assert_(obj['tmp'] == 'tmp')

        # Test has_key

        self.assert_(obj.has_key('tmp'))

        # Test __delitem__

        del(obj['tmp'])
        self.assert_(not obj.has_key('tmp'))

        # Test __len__

        self.assert_(len(obj) == 2)

        # Test keys

        keys = obj.keys()
        self.assert_('Chicken' in keys and 'Beans' in keys)
        self.assert_(len(keys) == 2)

        # Test values

        values = obj.values()
        self.assert_('Ham' in values and 42 in values)
        self.assert_(len(values) == 2)
        
        # Test items

        items = obj.items()
        self.assert_(('Chicken', 'Ham') in items and
                     ('Beans', 42) in items)
        self.assert_(len(items) == 2)

        # Test iterkeys

        keys = list(obj.iterkeys())
        self.assert_('Chicken' in keys and 'Beans' in keys)
        self.assert_(len(keys) == 2)

        # Test itervalues

        values = list(obj.itervalues())
        self.assert_('Ham' in values and 42 in values)
        self.assert_(len(values) == 2)
        
        # Test iteritems

        items = list(obj.iteritems())
        self.assert_(('Chicken', 'Ham') in items and
                     ('Beans', 42) in items)
        self.assert_(len(items) == 2)

        # Test update

        obj.update({'One':'1', 'Two': '2'})
        self.assert_(obj['one'] == '1')
        self.assert_(obj['two'] == '2')
        self.assert_(obj['Chicken'] == 'Ham')
        obj.update({'Three':'3', 'Four': '4'},[('Five', '5')])
        self.assert_(obj['three'] == '3')
        self.assert_(obj['four'] == '4')
        self.assert_(obj['five'] == '5')
        obj.update([('Six', '6')], Seven='7', Eight='8')
        self.assert_(obj['six'] == '6')
        self.assert_(obj['seven'] == '7')
        self.assert_(obj['eight'] == '8')
        obj.update(Nine='9', Ten='10')
        self.assert_(obj['nine'] == '9')
        self.assert_(obj['ten'] == '10')
        self.assert_(obj['Chicken'] == 'Ham')


#################################################################
# CIMInstanceName
#################################################################

class InitCIMInstanceName(TestCase):
    """A CIMInstanceName can be initialised with just a classname, or a
    classname and dict of keybindings."""

    def runtest(self):

        # Initialise with classname only

        obj = CIMInstanceName('CIM_Foo')
        self.assert_(len(obj.keys()) == 0)

        # Initialise with keybindings dict

        obj = CIMInstanceName('CIM_Foo', {'Name': 'Foo', 'Chicken': 'Ham'})
        self.assert_(len(obj.keys()) == 2)

        obj = CIMInstanceName('CIM_Foo',
                              NocaseDict({'Name': 'Foo', 'Chicken': 'Ham'}))
        self.assert_(len(obj.keys()) == 2)

        # Initialise with all possible keybindings types

        obj = CIMInstanceName('CIM_Foo', {'Name': 'Foo',
                                          'Number': 42,
                                          'Boolean': False,
                                          'Ref': CIMInstanceName('CIM_Bar')})

        self.assert_(len(obj.keys()) == 4)

        # Initialise with namespace

        obj = CIMInstanceName('CIM_Foo',
                              {'InstanceID': '1234'},
                              namespace = 'root/cimv2')

        # Initialise with host and namespace

        obj = CIMInstanceName('CIM_Foo',
                              {'InstanceID': '1234'},
                              host = 'woot.com',
                              namespace = 'root/cimv2')

class CopyCIMInstanceName(TestCase):

    def runtest(self):

        i = CIMInstanceName('CIM_Foo',
                            keybindings = {'InstanceID': '1234'},
                              host = 'woot.com',
                              namespace = 'root/cimv2')

        c = i.copy()

        self.assert_equal(i, c)

        c.classname = 'CIM_Bar'
        c.keybindings = NocaseDict({'InstanceID': '5678'})
        c.host = None
        c.namespace = None

        self.assert_(i.classname == 'CIM_Foo')
        self.assert_(i.keybindings['InstanceID'] == '1234')
        self.assert_(i.host == 'woot.com')
        self.assert_(i.namespace == 'root/cimv2')

class CIMInstanceNameAttrs(TestCase):
    """Valid attributes for CIMInstanceName are 'classname' and
    'keybindings'."""

    def runtest(self):

        kb = {'Chicken': 'Ham', 'Beans': 42}

        obj = CIMInstanceName('CIM_Foo', kb)

        self.assert_(obj.classname == 'CIM_Foo')
        self.assert_(obj.keybindings == kb)
        self.assert_(obj.host == None)
        self.assert_(obj.namespace == None)

class CIMInstanceNameDictInterface(DictTest):
    """Test the Python dictionary interface for CIMInstanceName."""

    def runtest(self):

        kb = {'Chicken': 'Ham', 'Beans': 42}
        obj = CIMInstanceName('CIM_Foo', kb)

        self.runtest_dict(obj)

class CIMInstanceNameEquality(TestCase):
    """Test comparing CIMInstanceName objects."""

    def runtest(self):

        # Basic equality tests

        self.assert_equal(CIMInstanceName('CIM_Foo'),
                          CIMInstanceName('CIM_Foo'))

        self.assert_notequal(CIMInstanceName('CIM_Foo', {'Cheepy': 'Birds'}),
                             CIMInstanceName('CIM_Foo'))

        self.assert_equal(CIMInstanceName('CIM_Foo', {'Cheepy': 'Birds'}),
                          CIMInstanceName('CIM_Foo', {'Cheepy': 'Birds'}))

        # Classname should be case insensitive

        self.assert_equal(CIMInstanceName('CIM_Foo'),
                          CIMInstanceName('cim_foo'))

        # NocaseDict should implement case insensitive keybinding names

        self.assert_equal(CIMInstanceName('CIM_Foo', {'Cheepy': 'Birds'}),
                          CIMInstanceName('CIM_Foo', {'cheepy': 'Birds'}))

        self.assert_notequal(CIMInstanceName('CIM_Foo', {'Cheepy': 'Birds'}),
                             CIMInstanceName('CIM_Foo', {'cheepy': 'birds'}))

        # Test a bunch of different keybinding types

        obj1 = CIMInstanceName('CIM_Foo', {'Name': 'Foo',
                                           'Number': 42,
                                           'Boolean': False,
                                           'Ref':
                                           CIMInstanceName('CIM_Bar')})

        obj2 = CIMInstanceName('CIM_Foo', {'Name': 'Foo',
                                           'Number': 42,
                                           'Boolean': False,
                                           'Ref':
                                           CIMInstanceName('CIM_Bar')})

        self.assert_equal(obj1, obj2)

        # Test keybinding types are not confused in comparisons

        self.assert_notequal(CIMInstanceName('CIM_Foo', {'Foo': '42'}),
                             CIMInstanceName('CIM_Foo', {'Foo': 42}))

        self.assert_notequal(CIMInstanceName('CIM_Foo', {'Bar': True}),
                             CIMInstanceName('CIM_Foo', {'Bar': 'TRUE'}))

        # Test hostname is case insensitive

        self.assert_equal(CIMInstanceName('CIM_Foo', host = 'woot.com'),
                          CIMInstanceName('CIM_Foo', host = 'Woot.Com'))

class CIMInstanceNameCompare(TestCase):

    def runtest(self):
        raise NotRunError

class CIMInstanceNameSort(TestCase):

    def runtest(self):
        raise NotRunError

class CIMInstanceNameString(TestCase):
    """Test string representation functions for CIMInstanceName
    objects."""

    def runtest(self):

        obj = CIMInstanceName('CIM_Foo', {'Name': 'Foo', 'Secret': 42})

        # Test str() method generates output with classname and
        # keybindings: e.g CIM_Foo.Secret=42,Name="Foo"

        s = str(obj)
        
        self.assert_re_match('^CIM_Foo\.', s)
        self.assert_re_search('Secret=42', s)
        self.assert_re_search('Name="Foo"', s)

        s = s.replace('CIM_Foo.', '')
        s = s.replace('Secret=42', '')
        s = s.replace('Name="Foo"', '')

        self.assert_(s == ',')

        # Test repr() function contains slightly more verbose
        # output, but we're not too concerned about the format.
        #
        # CIMInstanceName(classname='CIM_Foo', \
        #     keybindings=NocaseDict({'Secret': 42, 'Name': 'Foo'}))
        
        r = repr(obj)

        self.assert_re_match('^CIMInstanceName\(classname=\'CIM_Foo\'', r)
        self.assert_re_search('keybindings=', r)
        self.assert_re_search('\'Secret\': 42', r)
        self.assert_re_search('\'Name\': \'Foo\'', r)

        # Test str() with namespace

        obj = CIMInstanceName('CIM_Foo', {'InstanceID': '1234'},
                              namespace = 'root/InterOp')

        self.assert_equal(str(obj), 'root/InterOp:CIM_Foo.InstanceID="1234"')

        # Test str() with host and namespace

        obj = CIMInstanceName('CIM_Foo', {'InstanceID': '1234'},
                              host = 'woot.com',
                              namespace = 'root/InterOp')

        self.assert_equal(str(obj),
                          '//woot.com/root/InterOp:CIM_Foo.InstanceID="1234"')

class CIMInstanceNameToXML(ValidateTest):
    """Test valid XML is generated for various CIMInstanceName objects."""

    def runtest(self):        

        self.validate(CIMInstanceName('CIM_Foo'))

        self.validate(CIMInstanceName('CIM_Foo', {'Cheepy': 'Birds'}))

        self.validate(CIMInstanceName(
            'CIM_Foo', {'Name': 'Foo',
                        'Number': 42,
                        'Boolean': False,
                        'Ref': CIMInstanceName('CIM_Bar')}))

        self.validate(CIMInstanceName('CIM_Foo', namespace = 'root/cimv2'))

        self.validate(CIMInstanceName('CIM_Foo',
                                      host = 'woot.com',
                                      namespace = 'root/cimv2'))

#################################################################
# CIMInstance
#################################################################

class InitCIMInstance(TestCase):
    """CIMInstance objects can be initialised in a similar manner to
    CIMInstanceName, i.e classname only, or a list of properties."""

    def runtest(self):

        # Initialise with classname only

        obj = CIMInstance('CIM_Foo')

        # Initialise with keybindings dict

        obj = CIMInstance('CIM_Foo', {'Name': 'Foo', 'Chicken': 'Ham'})
        self.assert_(len(obj.keys()) == 2)

        obj = CIMInstance('CIM_Foo',
                          NocaseDict({'Name': 'Foo', 'Chicken': 'Ham'}))
        self.assert_(len(obj.keys()) == 2)

        # Check that CIM type checking is done for integer and
        # floating point property values

        try:
            obj = CIMInstance('CIM_Foo', {'Number': 42})
        except TypeError:
            pass
        else:
            self.fail('TypeError not raised')

        obj = CIMInstance('CIM_Foo', {'Foo': Uint32(42),
                                      'Bar': Real32(42.0)})

        # Initialise with qualifiers

        obj = CIMInstance('CIM_Foo',
                          qualifiers = {'Key': CIMQualifier('Key', True)})

        # Initialise with path

        obj = CIMInstance('CIM_Foo',
                          {'InstanceID': '1234'},
                          path = CIMInstanceName('CIM_Foo',
                                                 {'InstanceID': '1234'}))

class CopyCIMInstance(TestCase):

    def runtest(self):

        i = CIMInstance('CIM_Foo',
                        properties = {'Name': 'Foo', 'Chicken': 'Ham'},
                        qualifiers = {'Key': 'Value'},
                        path = CIMInstanceName('CIM_Foo', {'Name': 'Foo'}))

        c = i.copy()

        self.assert_equal(i, c)

        c.classname = 'CIM_Bar'
        c.properties = {'InstanceID': '5678'}
        c.qualifiers = {}
        c.path = None

        self.assert_(i.classname == 'CIM_Foo')
        self.assert_(i['Name'] == 'Foo')
        self.assert_(i.qualifiers['Key'] == 'Value')
        self.assert_(i.path == CIMInstanceName('CIM_Foo', {'Name': 'Foo'}))

        # Test copy when path is None

        i = CIMInstance('CIM_Foo',
                        properties = {'Name': 'Foo', 'Chicken': 'Ham'},
                        qualifiers = {'Key': 'Value'},
                        path = None)

        self.assert_(i == i.copy())

class CIMInstanceAttrs(TestCase):
    """Valid attributes for CIMInstance are 'classname' and
    'keybindings'."""

    def runtest(self):

        props = {'Chicken': 'Ham', 'Number': Uint32(42)}

        obj = CIMInstance('CIM_Foo', props,
                          qualifiers = {'Key': CIMQualifier('Key', True)},
                          path = CIMInstanceName('CIM_Foo',
                                                 {'Chicken': 'Ham'}))

        self.assert_(obj.classname == 'CIM_Foo')

        self.assert_(obj.properties)
        self.assert_(obj.qualifiers)
        self.assert_(obj.path)

class CIMInstanceDictInterface(DictTest):
    """Test the Python dictionary interface for CIMInstance."""

    def runtest(self):

        props = {'Chicken': 'Ham', 'Beans': Uint32(42)}
        obj = CIMInstance('CIM_Foo', props)

        self.runtest_dict(obj)

        # Test CIM type checking

        try:
            obj['Foo'] = 43
        except TypeError:
            pass
        else:
            self.fail('TypeError not raised')

        obj['Foo'] = Uint32(43)

class CIMInstanceEquality(TestCase):
    """Test comparing CIMInstance objects."""

    def runtest(self):

        # Basic equality tests

        self.assert_equal(CIMInstance('CIM_Foo'),
                          CIMInstance('CIM_Foo'))

        self.assert_notequal(CIMInstance('CIM_Foo', {'Cheepy': 'Birds'}),
                             CIMInstance('CIM_Foo'))

        # Classname should be case insensitive

        self.assert_equal(CIMInstance('CIM_Foo'),
                          CIMInstance('cim_foo'))

        # NocaseDict should implement case insensitive keybinding names

        self.assert_equal(CIMInstance('CIM_Foo', {'Cheepy': 'Birds'}),
                          CIMInstance('CIM_Foo', {'cheepy': 'Birds'}))

        self.assert_notequal(CIMInstance('CIM_Foo', {'Cheepy': 'Birds'}),
                             CIMInstance('CIM_Foo', {'cheepy': 'birds'}))

        # Qualifiers

        self.assert_notequal(CIMInstance('CIM_Foo'),
                             CIMInstance('CIM_Foo',
                                         qualifiers = {'Key':
                                                       CIMQualifier('Key',
                                                                    True)}))

        # Path

        self.assert_notequal(CIMInstance('CIM_Foo'),
                             CIMInstance('CIM_Foo', {'Cheepy': 'Birds'}))

        # Reference properties

        self.assert_equal(CIMInstance('CIM_Foo',
                                      {'Ref1': CIMInstanceName('CIM_Bar')}),
                          CIMInstance('CIM_Foo',
                                      {'Ref1': CIMInstanceName('CIM_Bar')}))

        # Null properties

        self.assert_notequal(
            CIMInstance('CIM_Foo',
                        {'Null': CIMProperty('Null', None, type = 'string')}),
            CIMInstance('CIM_Foo',
                        {'Null': CIMProperty('Null', '')}))

        self.assert_notequal(
            CIMInstance('CIM_Foo',
                        {'Null': CIMProperty('Null', None, type = 'uint32')}),
            CIMInstance('CIM_Foo',
                        {'Null': CIMProperty('Null', Uint32(0))}))

        # Mix of CIMProperty and native Python types

        self.assert_equal(
            CIMInstance(
              'CIM_Foo',
              {'string': 'string',
               'uint8': Uint8(0),
               'uint8array': [Uint8(1), Uint8(2)],
               'ref': CIMInstanceName('CIM_Bar')}),
            CIMInstance(
              'CIM_Foo',
              {'string': CIMProperty('string', 'string'),
               'uint8': CIMProperty('uint8', Uint8(0)),
               'uint8Array': CIMProperty('uint8Array', [Uint8(1), Uint8(2)]),
               'ref': CIMProperty('ref', CIMInstanceName('CIM_Bar'))})
            )

class CIMInstanceCompare(TestCase):

    def runtest(self):
        raise NotRunError

class CIMInstanceSort(TestCase):

    def runtest(self):
        raise NotRunError

class CIMInstanceString(TestCase):
    """Test string representation functions for CIMInstance objects."""
    
    def runtest(self):

        obj = CIMInstance('CIM_Foo', {'Name': 'Spottyfoot',
                                      'Ref1': CIMInstanceName('CIM_Bar')})

        s = str(obj)

        self.assert_re_search('classname=\'CIM_Foo\'', s)
        self.assert_(s.find('Name') == -1)
        self.assert_(s.find('Ref1') == -1)

        r = repr(obj)

        self.assert_re_search('classname=\'CIM_Foo\'', r)
        self.assert_(r.find('Name') == -1)
        self.assert_(r.find('Ref1') == -1)

class CIMInstanceToXML(ValidateTest):
    """Test valid XML is generated for various CIMInstance objects."""

    def runtest(self):

        # Simple instances, no properties

        self.validate(CIMInstance('CIM_Foo'))

        # Path

        self.validate(CIMInstance('CIM_Foo',
                          {'InstanceID': '1234'},
                          path = CIMInstanceName('CIM_Foo',
                                                 {'InstanceID': '1234'})))

        # Multiple properties and qualifiers
        
        self.validate(CIMInstance('CIM_Foo', {'Spotty': 'Foot',
                                              'Age': Uint32(42)},
                                  qualifiers = {'Key':
                                                CIMQualifier('Key', True)}))

        # Test every numeric property type

        for t in [Uint8, Uint16, Uint32, Uint64, Sint8, Sint16, Sint32, Sint64,
                  Real32, Real64]:
            self.validate(CIMInstance('CIM_Foo', {'Number': t(42)}))

        # Other property types

        self.validate(CIMInstance('CIM_Foo', {'Value': False}))

        self.validate(CIMInstance('CIM_Foo', {'Now': CIMDateTime.now()}))
        self.validate(CIMInstance('CIM_Foo', {'Now': timedelta(60)}))

        self.validate(CIMInstance('CIM_Foo',
                                  {'Ref': CIMInstanceName('CIM_Eep',
                                                          {'Foo': 'Bar'})}))
        
        # Array types.  Can't have an array of references

        for t in [Uint8, Uint16, Uint32, Uint64, Sint8, Sint16, Sint32, Sint64,
                  Real32, Real64]:
            
            self.validate(CIMInstance('CIM_Foo', {'Number': [t(42), t(43)]}))

        self.validate(CIMInstance('CIM_Foo',
                                  {'Now': [CIMDateTime.now(), CIMDateTime.now()]}))

        self.validate(CIMInstance('CIM_Foo',
                                  {'Then': [timedelta(60), timedelta(61)]}))

        # Null properties.  Can't have a NULL property reference.

        obj = CIMInstance('CIM_Foo')

        obj.properties['Cheepy'] = CIMProperty('Cheepy', None, type = 'string')
        obj.properties['Date'] = CIMProperty('Date', None, type = 'datetime')
        obj.properties['Bool'] = CIMProperty('Bool', None, type = 'boolean')

        for t in ['uint8', 'uint16', 'uint32', 'uint64', 'sint8', 'sint16',
                  'sint32', 'sint64', 'real32', 'real64']:
            obj.properties[t] = CIMProperty(t, None, type = t)
            
        self.validate(obj)

        # Null property arrays.  Can't have arrays of NULL property
        # references.

        obj = CIMInstance('CIM_Foo')

        obj.properties['Cheepy'] = CIMProperty(
            'Cheepy', None, type = 'string', is_array = True)

        obj.properties['Date'] = CIMProperty(
            'Date', None, type = 'datetime', is_array = True)
        
        obj.properties['Bool'] = CIMProperty(
            'Bool', None, type = 'boolean', is_array = True)

        for t in ['uint8', 'uint16', 'uint32', 'uint64', 'sint8', 'sint16',
                  'sint32', 'sint64', 'real32', 'real64']:
            obj.properties[t] = CIMProperty(t, None, type = t, is_array = True)
            
        self.validate(obj)        

class CIMInstanceToMOF(TestCase):

    def runtest(self):

        i = CIMInstance(
            'CIM_Foo',
            {'string': 'string',
             'uint8': Uint8(0),
             'uint8array': [Uint8(1), Uint8(2)],
             'ref': CIMInstanceName('CIM_Bar')})

        i.tomof()

class CIMInstanceUpdateExisting(TestCase):

    def runtest(self):
        i = CIMInstance(
            'CIM_Foo',
            {'string': 'string',
             'uint8': Uint8(0),
             'uint8array': [Uint8(1), Uint8(2)],
             'ref': CIMInstanceName('CIM_Bar')})

        self.assert_(i['string'] == 'string')
        i.update_existing({'one': '1', 'string': '_string_'})
        self.assert_('one' not in i)
        self.assert_(i['string'] == '_string_')
        try:
            i['one']
        except KeyError:
            pass
        else:
            self.fail('KeyError not thrown')
        self.assert_(i['uint8'] == 0)
        i.update_existing([('Uint8', 1), ('one', 1)])
        self.assert_(i['uint8'] == 1)
        self.assert_('one' not in i)
        i.update_existing(one=1, uint8=2)
        self.assert_('one' not in i)
        self.assert_(i['uint8'] == 2)
        self.assert_(isinstance(i['uint8'], Uint8))
        self.assert_(i['uint8'] == Uint8(2))
        self.assert_(i['uint8'] == 2)
        i.update_existing(Uint8Array=[3,4,5], foo=[1,2])
        self.assert_('foo' not in i)
        self.assert_(i['uint8array'] == [3,4,5])
        self.assert_(isinstance(i['uint8array'][0], Uint8))
        name = CIMInstanceName('CIM_Foo', keybindings={'string':'STRING',
                                                       'one':'1'})
        i.update_existing(name)
        self.assert_('one' not in i)
        self.assert_(i['string'] == 'STRING')


#################################################################
# CIMProperty
#################################################################

class InitCIMProperty(TestCase):

    def runtest(self):

        # Basic CIMProperty initialisations

        CIMProperty('Spotty', 'Foot', type = 'string')
        CIMProperty('Spotty', None, type = 'string')
        CIMProperty(u'Name', u'Brad')
        CIMProperty('Age', Uint16(32))
        CIMProperty('Age', None, 'uint16')
            
        # Must specify a type when value is None

        try:
            CIMProperty('Spotty', None)
        except TypeError:
            pass
        else:
            self.fail('TypeError not raised')

        # Numeric types must have CIM types

        try:
            CIMProperty('Age', 42)
        except TypeError:
            pass
        else:
            self.fail('TypeError not raised')

        # Qualifiers

        CIMProperty('Spotty', 'Foot',
                    qualifiers = {'Key': CIMQualifier('Key', True)})

        # Simple arrays

        CIMProperty('Foo', None, 'string')
        CIMProperty('Foo', [Uint8(x) for x in [1, 2, 3]])
        CIMProperty('Foo', [Uint8(x) for x in [1, 2, 3]],
                    qualifiers = {'Key': CIMQualifier('Key', True)})

        # Must specify type for empty property array

        try:
            CIMProperty('Foo', [])
        except TypeError:
            pass
        else:
            self.fail('TypeError not raised')

        # Numeric property value arrays must be a CIM type

        try:
            CIMProperty('Foo', [1, 2, 3])
        except TypeError:
            pass
        else:
            self.fail('TypeError not raised')
    
        # Property references

        CIMProperty('Foo', None, type = 'reference')
        CIMProperty('Foo', CIMInstanceName('CIM_Foo'))
        CIMProperty('Foo', CIMInstanceName('CIM_Foo'),
                    qualifiers = {'Key': CIMQualifier('Key', True)})

class CopyCIMProperty(TestCase):

    def runtest(self):

        p = CIMProperty('Spotty', 'Foot')
        c = p.copy()

        self.assert_equal(p, c)

        c.name = '1234'
        c.value = '1234'
        c.qualifiers = {'Key': CIMQualifier('Value', True)}

        self.assert_(p.name == 'Spotty')
        self.assert_(p.value == 'Foot')
        self.assert_(p.qualifiers == {})

class CIMPropertyAttrs(TestCase):

    def runtest(self):

        # Attributes for single-valued property

        obj = CIMProperty('Spotty', 'Foot', type = 'string')
        
        self.assert_(obj.name == 'Spotty')
        self.assert_(obj.value == 'Foot')
        self.assert_(obj.type == 'string')
        self.assert_(obj.qualifiers == {})

        # Attributes for array property

        v = [Uint8(x) for x in [1, 2, 3]]

        obj = CIMProperty('Foo', v)

        self.assert_(obj.name == 'Foo')
        self.assert_(obj.value == v)
        self.assert_(obj.type == 'uint8')
        self.assert_(obj.qualifiers == {})

        # Attributes for property reference

        v = CIMInstanceName('CIM_Foo')

        obj = CIMProperty('Foo', v, reference_class = 'CIM_Bar')

        self.assert_(obj.name == 'Foo')
        self.assert_(obj.value == v)
        self.assert_(obj.type == 'reference')
        self.assert_(obj.reference_class == 'CIM_Bar')
        self.assert_(obj.qualifiers == {})
        
class CIMPropertyEquality(TestCase):

    def runtest(self):

        # Compare single-valued properties

        self.assert_equal(CIMProperty('Spotty', None, 'string'),
                          CIMProperty('Spotty', None, 'string'))

        self.assert_notequal(CIMProperty('Spotty', '', 'string'),
                             CIMProperty('Spotty', None, 'string'))

        self.assert_equal(CIMProperty('Spotty', 'Foot'),
                          CIMProperty('Spotty', 'Foot'))

        self.assert_notequal(CIMProperty('Spotty', 'Foot'),
                             CIMProperty('Spotty', Uint32(42)))

        self.assert_equal(CIMProperty('Spotty', 'Foot'),
                          CIMProperty('spotty', 'Foot'))

        self.assert_notequal(CIMProperty('Spotty', 'Foot'),
                             CIMProperty('Spotty', 'Foot',
                                         qualifiers =
                                         {'Key':
                                          CIMQualifier('Key', True)}))

        # Compare property arrays

        self.assert_equal(
            CIMProperty('Array', None, 'uint8', is_array = True),
            CIMProperty('array', None, 'uint8', is_array = True))

        self.assert_equal(
            CIMProperty('Array', [Uint8(x) for x in [1, 2, 3]]),
            CIMProperty('Array', [Uint8(x) for x in [1, 2, 3]]))

        self.assert_notequal(
            CIMProperty('Array', [Uint8(x) for x in [1, 2, 3]]),
            CIMProperty('Array', [Uint16(x) for x in [1, 2, 3]]))

        self.assert_notequal(
            CIMProperty('Array', [Uint8(x) for x in [1, 2, 3]]),
            CIMProperty('Array', [Uint16(x) for x in [1, 2, 3]],
                        qualifiers = {'Key': CIMQualifier('Key', True)}))

        # Compare property references

        self.assert_equal(
            CIMProperty('Foo', CIMInstanceName('CIM_Foo')),
            CIMProperty('Foo', CIMInstanceName('CIM_Foo')))
        
        self.assert_equal(
            CIMProperty('Foo', CIMInstanceName('CIM_Foo')),
            CIMProperty('foo', CIMInstanceName('CIM_Foo')))

        self.assert_notequal(
            CIMProperty('Foo', CIMInstanceName('CIM_Foo')),
            CIMProperty('foo', None, type = 'reference'))

        self.assert_notequal(
            CIMProperty('Foo', CIMInstanceName('CIM_Foo')),
            CIMProperty('Foo', CIMInstanceName('CIM_Foo'),
                        qualifiers =
                        {'Key': CIMQualifier('Key', True)}))        

class CIMPropertyCompare(TestCase):

    def runtest(self):
        raise NotRunError

class CIMPropertySort(TestCase):

    def runtest(self):
        raise NotRunError

class CIMPropertyString(TestCase):

    def runtest(self):

        r = repr(CIMProperty('Spotty', 'Foot', type = 'string'))

        self.assert_re_match('^CIMProperty', r)

class CIMPropertyToXML(ValidateTest):
    """Test valid XML is generated for various CIMProperty objects."""

    def runtest(self):

        # Single-valued properties

        self.validate(CIMProperty('Spotty', None, type = 'string'))
        self.validate(CIMProperty(u'Name', u'Brad'))
        self.validate(CIMProperty('Age', Uint16(32)))
        self.validate(CIMProperty('Age', Uint16(32),
                                  qualifiers = {'Key':
                                                CIMQualifier('Key', True)}))

        # Array properties

        self.validate(CIMProperty('Foo', None, 'string', is_array = True))
        self.validate(CIMProperty('Foo', [], 'string'))
        self.validate(CIMProperty('Foo', [Uint8(x) for x in [1, 2, 3]]))

        self.validate(CIMProperty(
            'Foo', [Uint8(x) for x in [1, 2, 3]],
            qualifiers = {'Key': CIMQualifier('Key', True)}))

        # Reference properties

        self.validate(CIMProperty('Foo', None, type = 'reference'))
        self.validate(CIMProperty('Foo', CIMInstanceName('CIM_Foo')))

        self.validate(CIMProperty(
            'Foo',
            CIMInstanceName('CIM_Foo'),
            qualifiers = {'Key': CIMQualifier('Key', True)}))        

#################################################################
# CIMQualifier
#################################################################

class InitCIMQualifier(TestCase):
    """Test initialising a CIMQualifier object."""

    def runtest(self):

        CIMQualifier('Revision', '2.7.0', 'string')
        CIMQualifier('RevisionList', ['1', '2', '3'], propagated = False)
        CIMQualifier('Null', None, 'string')
        
class CopyCIMQualifier(TestCase):

    def runtest(self):

        q = CIMQualifier('Revision', '2.7.0', 'string')
        c = q.copy()

        self.assert_equal(q, c)

        c.name = 'Fooble'
        c.value = 'eep'
        
        self.assert_(q.name == 'Revision')

class CIMQualifierAttrs(TestCase):
    """Test attributes of CIMQualifier object."""

    def runtest(self):

        q = CIMQualifier('Revision', '2.7.0')

        self.assert_equal(q.name, 'Revision')
        self.assert_equal(q.value, '2.7.0')

        self.assert_equal(q.propagated, None)
        self.assert_equal(q.overridable, None)
        self.assert_equal(q.tosubclass, None)
        self.assert_equal(q.toinstance, None)
        self.assert_equal(q.translatable, None)

        q = CIMQualifier('RevisionList',
                         [Uint8(x) for x in [1, 2, 3]],
                         propagated = False)

        self.assert_equal(q.name, 'RevisionList')
        self.assert_equal(q.value, [1, 2, 3])
        self.assert_equal(q.propagated, False)

class CIMQualifierEquality(TestCase):
    """Compare CIMQualifier objects."""

    def runtest(self):

        self.assert_equal(CIMQualifier('Spotty', 'Foot'),
                          CIMQualifier('Spotty', 'Foot'))

        self.assert_equal(CIMQualifier('Spotty', 'Foot'),
                          CIMQualifier('spotty', 'Foot'))

        self.assert_notequal(CIMQualifier('Spotty', 'Foot'),
                             CIMQualifier('Spotty', 'foot'))

        self.assert_notequal(CIMQualifier('Null', None, type = 'string'),
                             CIMQualifier('Null', ''))

class CIMQualifierCompare(TestCase):

    def runtest(self):
        raise NotRunError

class CIMQualifierSort(TestCase):

    def runtest(self):
        raise NotRunError

class CIMQualifierString(TestCase):

    def runtest(self):

        s = str(CIMQualifier('RevisionList', ['1', '2', '3'],
                             propagated = False))

        self.assert_re_search('RevisionList', s)
        
class CIMQualifierToXML(ValidateTest):

    def runtest(self):

        self.validate(CIMQualifier('Spotty', 'Foot'))
        self.validate(CIMQualifier('Revision', Real32(2.7)))

        self.validate(CIMQualifier('RevisionList',
                                   [Uint16(x) for x in 1, 2, 3],
                                   propagated = False))

#################################################################
# CIMClass
#################################################################

class InitCIMClass(TestCase):

    def runtest(self):

        # Initialise with classname, superclass

        CIMClass('CIM_Foo')
        CIMClass('CIM_Foo', superclass = 'CIM_Bar')

        # Initialise with properties

        CIMClass('CIM_Foo', properties = {'InstanceID':
                                          CIMProperty('InstanceID', None,
                                                      type = 'string')})

        # Initialise with methods

        CIMClass('CIM_Foo', methods = {'Delete': CIMMethod('Delete')})

        # Initialise with qualifiers

        CIMClass('CIM_Foo', qualifiers = {'Key': CIMQualifier('Key', True)})

class CopyCIMClass(TestCase):

    def runtest(self):

        c = CIMClass('CIM_Foo',
                     methods = {'Delete': CIMMethod('Delete')},
                     qualifiers = {'Key': CIMQualifier('Value', True)})

        co = c.copy()

        self.assert_equal(c, co)

        co.classname = 'CIM_Bar'
        del(co.methods['Delete'])
        del(co.qualifiers['Key'])

        self.assert_(c.classname == 'CIM_Foo')
        self.assert_(c.methods['Delete'])
        self.assert_(c.qualifiers['Key'])

class CIMClassAttrs(TestCase):

    def runtest(self):

        obj = CIMClass('CIM_Foo', superclass =  'CIM_Bar')

        self.assert_(obj.classname == 'CIM_Foo')
        self.assert_(obj.superclass == 'CIM_Bar')
        self.assert_(obj.properties == {})
        self.assert_(obj.qualifiers == {})
        self.assert_(obj.methods == {})
        self.assert_(obj.qualifiers == {})

class CIMClassEquality(TestCase):

    def runtest(self):

        self.assert_equal(CIMClass('CIM_Foo'), CIMClass('CIM_Foo'))
        self.assert_equal(CIMClass('CIM_Foo'), CIMClass('cim_foo'))

        self.assert_notequal(CIMClass('CIM_Foo', superclass = 'CIM_Bar'),
                             CIMClass('CIM_Foo'))

        properties = {'InstanceID':
                      CIMProperty('InstanceID', None,
                                  type = 'string')}

        methods = {'Delete': CIMMethod('Delete')}

        qualifiers = {'Key': CIMQualifier('Key', True)}

        self.assert_notequal(CIMClass('CIM_Foo'),
                             CIMClass('CIM_Foo', properties = properties))

        self.assert_notequal(CIMClass('CIM_Foo'),
                             CIMClass('CIM_Foo', methods = methods))
        
        self.assert_notequal(CIMClass('CIM_Foo'),
                             CIMClass('CIM_Foo', qualifiers = qualifiers))

        self.assert_equal(CIMClass('CIM_Foo', superclass = 'CIM_Bar'),
                          CIMClass('CIM_Foo', superclass = 'cim_bar'))

class CIMClassCompare(TestCase):

    def runtest(self):
        raise NotRunError

class CIMClassSort(TestCase):

    def runtest(self):
        raise NotRunError

class CIMClassString(TestCase):

    def runtest(self):

        s = str(CIMClass('CIM_Foo'))
        self.assert_re_search('CIM_Foo', s)

class CIMClassToXML(ValidateTest):

    def runtest(self):

        self.validate(CIMClass('CIM_Foo'))
        self.validate(CIMClass('CIM_Foo', superclass = 'CIM_Bar'))
        
        self.validate(
            CIMClass(
                'CIM_Foo',
                properties = {'InstanceID': CIMProperty('InstanceID', None,
                                                        type = 'string')}))

        self.validate(
            CIMClass(
                'CIM_Foo',
                methods = {'Delete': CIMMethod('Delete')}))


        self.validate(
            CIMClass(
                'CIM_Foo',
                qualifiers = {'Key': CIMQualifier('Key', True)}))

class CIMClassToMOF(TestCase):

    def runtest(self):

        c = CIMClass(
            'CIM_Foo',
            properties = {'InstanceID': CIMProperty('InstanceID', None,
                                                    type = 'string')})

        c.tomof()

#################################################################
# CIMMethod
#################################################################

class InitCIMMethod(TestCase):

    def runtest(self):

        CIMMethod('FooMethod', 'uint32')

        CIMMethod('FooMethod', 'uint32',
                  parameters = {'Param1': CIMParameter('Param1', 'uint32'),
                                'Param2': CIMParameter('Param2', 'string')})

        CIMMethod('FooMethod', 'uint32',
                  parameters = {'Param1': CIMParameter('Param1', 'uint32'),
                                'Param2': CIMParameter('Param2', 'string')},
                  qualifiers = {'Key': CIMQualifier('Key', True)})

class CopyCIMMethod(TestCase):

    def runtest(self):

        m = CIMMethod('FooMethod', 'uint32',
                      parameters = {'P1': CIMParameter('P1', 'uint32'),
                                    'P2': CIMParameter('P2', 'string')},
                      qualifiers = {'Key': CIMQualifier('Key', True)})

        c = m.copy()

        self.assert_equal(m, c)

        c.name = 'BarMethod'
        c.return_type = 'string'
        del(c.parameters['P1'])
        del(c.qualifiers['Key'])

        self.assert_(m.name == 'FooMethod')
        self.assert_(m.return_type == 'uint32')
        self.assert_(m.parameters['P1'])
        self.assert_(m.qualifiers['Key'])

class CIMMethodAttrs(TestCase):

    def runtest(self):

        m = CIMMethod('FooMethod', 'uint32',
                      parameters = {'Param1': CIMParameter('Param1', 'uint32'),
                                    'Param2': CIMParameter('Param2', 'string')}
                      )

        self.assert_(m.name == 'FooMethod')
        self.assert_(m.return_type == 'uint32')
        self.assert_(len(m.parameters) == 2)
        self.assert_(m.qualifiers == {})

class CIMMethodEquality(TestCase):

    def runtest(self):

        self.assert_equal(CIMMethod('FooMethod', 'uint32'),
                          CIMMethod('FooMethod', 'uint32'))

        self.assert_equal(CIMMethod('FooMethod', 'uint32'),
                          CIMMethod('fooMethod', 'uint32'))
        
        self.assert_notequal(CIMMethod('FooMethod', 'uint32'),
                             CIMMethod('FooMethod', 'uint32',
                                       qualifiers =
                                       {'Key': CIMQualifier('Key', True)}))

class CIMMethodCompare(TestCase):

    def runtest(self):
        raise NotRunError

class CIMMethodSort(TestCase):

    def runtest(self):
        raise NotRunError

class CIMMethodString(TestCase):

    def runtest(self):

        s = str(CIMMethod('FooMethod', 'uint32'))

        self.assert_re_search('FooMethod', s)
        self.assert_re_search('uint32', s)

class CIMMethodToXML(ValidateTest):

    def runtest(self):

        self.validate(CIMMethod('FooMethod', 'uint32'))

        self.validate(
            CIMMethod('FooMethod', 'uint32',
                      parameters =
                      {'Param1': CIMParameter('Param1', 'uint32'),
                       'Param2': CIMParameter('Param2', 'string')},
                      qualifiers =
                      {'Key': CIMQualifier('Key', True)}))

#################################################################
# CIMParameter
#################################################################

class InitCIMParameter(TestCase):

    def runtest(self):

        # Single-valued parameters

        CIMParameter('Param1', 'uint32')
        CIMParameter('Param2', 'string')
        CIMParameter('Param2', 'string',
                     qualifiers = {'Key': CIMQualifier('Key', True)})

        # Array parameters

        CIMParameter('ArrayParam', 'uint32', is_array = True)
        CIMParameter('ArrayParam', 'uint32', is_array = True, array_size = 10)
        CIMParameter('ArrayParam', 'uint32', is_array = True, array_size = 10,
                     qualifiers = {'Key': CIMQualifier('Key', True)})

        # Reference parameters
        
        CIMParameter('RefParam', 'reference', reference_class = 'CIM_Foo')
        CIMParameter('RefParam', 'reference', reference_class = 'CIM_Foo',
                     qualifiers = {'Key': CIMQualifier('Key', True)})

        # Refarray parameters

        CIMParameter('RefArrayParam', 'reference', is_array = True)
        CIMParameter('RefArrayParam', 'reference', reference_class = 'CIM_Foo',
                     is_array = True)
        CIMParameter('RefArrayParam', 'reference', is_array = True,
                     reference_class = 'CIM_Foo', array_size = 10)
        CIMParameter('RefArrayParam', 'reference', is_array = True,
                     reference_class = 'CIM_Foo', array_size = 10,
                     qualifiers = {'Key': CIMQualifier('Key', True)})

class CopyCIMParameter(TestCase):

    def runtest(self):

        p = CIMParameter('RefParam', 'reference',
                         reference_class = 'CIM_Foo',
                         qualifiers = {'Key': CIMQualifier('Key', True)})

        c = p.copy()

        self.assert_equal(p, c)

        c.name = 'Fooble'
        c.type = 'string'
        c.reference_class = None
        del(c.qualifiers['Key'])

        self.assert_(p.name == 'RefParam')
        self.assert_(p.type == 'reference')
        self.assert_(p.reference_class == 'CIM_Foo')
        self.assert_(p.qualifiers['Key'])

class CIMParameterAttrs(TestCase):

    def runtest(self):

        # Single-valued parameters

        p = CIMParameter('Param1', 'string')

        self.assert_(p.name == 'Param1')
        self.assert_(p.type == 'string')
        self.assert_(p.qualifiers == {})

        # Array parameters

        p = CIMParameter('ArrayParam', 'uint32', is_array = True)

        self.assert_(p.name == 'ArrayParam')
        self.assert_(p.type == 'uint32')
        self.assert_(p.array_size == None)
        self.assert_(p.qualifiers == {})

        # Reference parameters

        p = CIMParameter('RefParam', 'reference', reference_class = 'CIM_Foo')

        self.assert_(p.name == 'RefParam')
        self.assert_(p.reference_class == 'CIM_Foo')
        self.assert_(p.qualifiers == {})

        # Reference array parameters

        p = CIMParameter('RefArrayParam', 'reference',
                         reference_class = 'CIM_Foo', is_array = True,
                         array_size = 10)

        self.assert_(p.name == 'RefArrayParam')
        self.assert_(p.reference_class == 'CIM_Foo')
        self.assert_(p.array_size == 10)
        self.assert_(p.is_array == True)
        self.assert_(p.qualifiers == {})
        
class CIMParameterEquality(TestCase):

    def runtest(self):

        # Single-valued parameters

        self.assert_equal(CIMParameter('Param1', 'uint32'),
                          CIMParameter('Param1', 'uint32'))

        self.assert_equal(CIMParameter('Param1', 'uint32'),
                          CIMParameter('param1', 'uint32'))

        self.assert_notequal(CIMParameter('Param1', 'uint32'),
                             CIMParameter('param1', 'string'))

        self.assert_notequal(CIMParameter('Param1', 'uint32'),
                             CIMParameter('param1', 'uint32',
                                          qualifiers =
                                          {'Key': CIMQualifier('Key', True)}))

        # Array parameters

        self.assert_equal(
            CIMParameter('ArrayParam', 'uint32', is_array = True),
            CIMParameter('ArrayParam', 'uint32', is_array = True))

        self.assert_equal(
            CIMParameter('ArrayParam', 'uint32', is_array = True),
            CIMParameter('arrayParam', 'uint32', is_array = True))

        self.assert_notequal(
            CIMParameter('ArrayParam', 'uint32', is_array = True),
            CIMParameter('ArrayParam', 'string', is_array = True))

        self.assert_notequal(
            CIMParameter('ArrayParam', 'uint32', is_array = True),
            CIMParameter('ArrayParam', 'string', is_array = True,
                         array_size = 10))

        self.assert_notequal(
            CIMParameter('ArrayParam', 'uint32', is_array = True),
            CIMParameter('ArrayParam', 'uint32', is_array = True,
                         qualifiers = {'Key': CIMQualifier('Key', True)}))

        # Reference parameters

        self.assert_equal(CIMParameter('RefParam', 'reference',
                                       reference_class = 'CIM_Foo'),
                          CIMParameter('RefParam', 'reference',
                                       reference_class = 'CIM_Foo'))
        
        self.assert_equal(CIMParameter('RefParam', 'reference',
                                       reference_class = 'CIM_Foo'),
                          CIMParameter('refParam', 'reference',
                                       reference_class = 'CIM_Foo'))

        self.assert_equal(CIMParameter('RefParam', 'reference',
                                       reference_class = 'CIM_Foo'),
                          CIMParameter('refParam', 'reference',
                                       reference_class = 'CIM_foo'))

        self.assert_notequal(CIMParameter('RefParam', 'reference',
                                          reference_class = 'CIM_Foo'),
                             CIMParameter('RefParam', 'reference',
                                          reference_class = 'CIM_Bar'))

        self.assert_notequal(CIMParameter('RefParam', 'reference',
                                          reference_class = 'CIM_Foo'),
                             CIMParameter('RefParam', 'reference',
                                          reference_class = 'CIM_Foo',
                                          qualifiers =
                                          {'Key': CIMQualifier('Key', True)}))

        # Reference array parameters

        self.assert_equal(CIMParameter('ArrayParam', 'reference',
                                       reference_class = 'CIM_Foo',
                                       is_array = True),
                          CIMParameter('ArrayParam', 'reference',
                                       reference_class = 'CIM_Foo',
                                       is_array = True))

        self.assert_equal(CIMParameter('ArrayParam', 'reference',
                                       reference_class = 'CIM_Foo',
                                       is_array = True),
                          CIMParameter('arrayparam', 'reference',
                                       reference_class = 'CIM_Foo',
                                       is_array = True))

        self.assert_notequal(CIMParameter('ArrayParam', 'reference',
                                          reference_class = 'CIM_Foo',
                                          is_array = True),
                             CIMParameter('arrayParam', 'reference',
                                          reference_class = 'CIM_foo',
                                          is_array = True,
                                          array_size = 10))

        self.assert_notequal(CIMParameter('ArrayParam', 'reference',
                                          reference_class ='CIM_Foo',
                                          is_array = True),
                             CIMParameter('ArrayParam', 'reference',
                                          reference_class = 'CIM_Foo',
                                          is_array = True,
                                          qualifiers =
                                          {'Key': CIMQualifier('Key', True)}))

class CIMParameterCompare(TestCase):

    def runtest(self):
        raise NotRunError

class CIMParameterSort(TestCase):

    def runtest(self):
        raise NotRunError

class CIMParameterString(TestCase):

    def runtest(self):

        s = str(CIMParameter('Param1', 'uint32'))

        self.assert_re_search('Param1', s)
        self.assert_re_search('uint32', s)

class CIMParameterToXML(ValidateTest):

    def runtest(self):

        # Single-valued parameters

        self.validate(CIMParameter('Param1', 'uint32'))

        self.validate(CIMParameter('Param1', 'string',
                                   qualifiers =
                                   {'Key': CIMQualifier('Key', True)}))

        # Array parameters

        self.validate(CIMParameter('ArrayParam', 'uint32', is_array = True))

        self.validate(CIMParameter('ArrayParam', 'uint32', is_array = True,
                                   array_size = 10))

        self.validate(CIMParameter(
            'ArrayParam', 'uint32', is_array = True, array_size = 10,
            qualifiers = {'Key': CIMQualifier('Key', True)}))        

        # Reference parameters

        self.validate(CIMParameter('RefParam', 'reference',
                                   reference_class = 'CIM_Foo',
                                   qualifiers = {'Key':
                                                 CIMQualifier('Key', True)}))

        # Reference array parameters

        self.validate(CIMParameter('RefArrayParam', 'reference',
                                   is_array = True))

        self.validate(CIMParameter('RefArrayParam', 'reference',
                                   reference_class = 'CIM_Foo',
                                   is_array = True))

        self.validate(CIMParameter('RefArrayParam', 'reference',
                                   reference_class = 'CIM_Foo',
                                   is_array = True,
                                   array_size = 10))

        self.validate(CIMParameter('RefArrayParam', 'reference',
                                   reference_class = 'CIM_Foo',
                                   is_array = True,
                                   qualifiers = {'Key':
                                                 CIMQualifier('Key', True)}))

#################################################################
# CIMQualifierDeclaration
#################################################################

class InitCIMQualifierDeclaration(TestCase):
    pass

class CopyCIMQualifierDeclaration(TestCase):
    pass

class CIMQualifierDeclarationAttrs(TestCase):
    pass

class CIMQualifierDeclarationEquality(TestCase):
    pass

class CIMQualifierDeclarationCompare(TestCase):
    pass

class CIMQualifierDeclarationSort(TestCase):
    pass

class CIMQualifierDeclarationString(TestCase):
    pass

class CIMQualifierDeclarationToXML(TestCase):
    pass

#################################################################
# ToCIMObj
#################################################################

class ToCIMObj(TestCase):

    def runtest(self):
        path = tocimobj('reference',
                "Acme_OS.Name=\"acmeunit\",SystemName=\"UnixHost\"")
        self.assert_(isinstance(path, CIMInstanceName))
        self.assert_equal(path.classname, 'Acme_OS')
        self.assert_equal(path['Name'], 'acmeunit')
        self.assert_equal(path['SystemName'], 'UnixHost')
        self.assert_equal(len(path.keybindings), 2)
        self.assert_(path.namespace is None)
        self.assert_(path.host is None)

        path = tocimobj('reference',
                "Acme_User.uid=33,OSName=\"acmeunit\",SystemName=\"UnixHost\"")
        self.assert_(isinstance(path, CIMInstanceName))
        self.assert_(path.namespace is None)
        self.assert_(path.host is None)
        self.assert_equal(path.classname, 'Acme_User')
        self.assert_equal(path['uid'], 33)
        self.assert_equal(path['OSName'], 'acmeunit')
        self.assert_equal(path['SystemName'], 'UnixHost')
        self.assert_equal(len(path.keybindings), 3)

        path = tocimobj('reference',
                'HTTP://CIMOM_host/root/CIMV2:CIM_Disk.key1="value1"')
        self.assert_(isinstance(path, CIMInstanceName))
        self.assert_equal(path.namespace, 'root/CIMV2')
        self.assert_equal(path.host, 'CIMOM_host')
        self.assert_equal(path.classname, 'CIM_Disk')
        self.assert_equal(path['key1'], 'value1')
        self.assert_equal(len(path.keybindings), 1)

        path = tocimobj('reference', "ex_sampleClass.label1=9921,label2=8821")
        self.assert_(isinstance(path, CIMInstanceName))
        self.assert_(path.namespace is None)
        self.assert_(path.host is None)
        self.assert_equal(path.classname, 'ex_sampleClass')
        self.assert_equal(path['label1'], 9921)
        self.assert_equal(path['label2'], 8821)
        self.assert_equal(len(path.keybindings), 2)

        path = tocimobj('reference', "ex_sampleClass")
        self.assert_(isinstance(path, CIMClassName))
        self.assert_(path.namespace is None)
        self.assert_(path.host is None)
        self.assert_equal(path.classname, 'ex_sampleClass')

        path = tocimobj('reference',
         '//./root/default:LogicalDisk.SystemName="acme",LogicalDisk.Drive="C"')
        self.assert_(isinstance(path, CIMInstanceName))
        self.assert_equal(path.namespace, 'root/default')
        self.assert_equal(path.host, '.')
        self.assert_equal(path.classname, 'LogicalDisk')
        self.assert_equal(path['SystemName'], 'acme')
        self.assert_equal(path['Drive'], 'C')
        self.assert_equal(len(path.keybindings), 2)

        path = tocimobj('reference', "X.key1=\"John Smith\",key2=33.3")
        self.assert_(isinstance(path, CIMInstanceName))
        self.assert_(path.namespace is None)
        self.assert_(path.host is None)
        self.assert_equal(path.classname, 'X')
        self.assert_equal(path['key1'], 'John Smith')
        self.assert_equal(path['key2'], 33.3)


        path = tocimobj('reference', "//./root/default:NetworkCard=2")
        # TODO: how should pywbem deal with a single, unnamed, keybinding? 
        #self.assert_(isinstance(path, CIMInstanceName))
        #self.assert_equal(path.namespace, 'root/default')
        #self.assert_equal(path.host, '.')
        #self.assert_equal(path.classname, 'NetworkCard')

#################################################################
# Main function
#################################################################

tests = [

    #############################################################
    # Property and qualifier classes
    #############################################################

    # CIMProperty

    InitCIMProperty,
    CopyCIMProperty,
    CIMPropertyAttrs,
    CIMPropertyEquality,
    CIMPropertyCompare,
    CIMPropertySort,
    CIMPropertyString,
    CIMPropertyToXML,
    
    # CIMQualifier

    InitCIMQualifier,
    CopyCIMQualifier,
    CIMQualifierAttrs,
    CIMQualifierEquality,
    CIMQualifierCompare,
    CIMQualifierSort,
    CIMQualifierString,
    CIMQualifierToXML,
    
    #############################################################
    # Instance and instance name classes
    #############################################################

    # CIMInstanceName

    InitCIMInstanceName,
    CopyCIMInstanceName,
    CIMInstanceNameAttrs,
    CIMInstanceNameDictInterface,
    CIMInstanceNameEquality,
    CIMInstanceNameCompare,
    CIMInstanceNameSort,
    CIMInstanceNameString,
    CIMInstanceNameToXML,

    # CIMInstance

    InitCIMInstance,
    CopyCIMInstance,
    CIMInstanceAttrs,
    CIMInstanceDictInterface,
    CIMInstanceEquality,
    CIMInstanceCompare,
    CIMInstanceSort,
    CIMInstanceString,
    CIMInstanceToXML,
    CIMInstanceToMOF,
    CIMInstanceUpdateExisting,

    #############################################################
    # Schema classes
    #############################################################

    # CIMClass

    InitCIMClass,
    CopyCIMClass,
    CIMClassAttrs,
    CIMClassEquality,
    CIMClassCompare,
    CIMClassSort,
    CIMClassString,
    CIMClassToXML,
    CIMClassToMOF,

    # TODO: CIMClassName

    # CIMMethod

    InitCIMMethod,
    CopyCIMMethod,
    CIMMethodAttrs,
    CIMMethodEquality,
    CIMMethodCompare,
    CIMMethodSort,
    CIMMethodString,
    CIMMethodToXML,

    # CIMParameter

    InitCIMParameter,
    CopyCIMParameter,
    CIMParameterAttrs,
    CIMParameterEquality,
    CIMParameterCompare,
    CIMParameterSort,
    CIMParameterString,
    CIMParameterToXML,

    # CIMQualifierDeclaration

    InitCIMQualifierDeclaration,
    CopyCIMQualifierDeclaration,
    CIMQualifierDeclarationAttrs,
    CIMQualifierDeclarationEquality,
    CIMQualifierDeclarationCompare,
    CIMQualifierDeclarationSort,
    CIMQualifierDeclarationString,
    CIMQualifierDeclarationToXML,

    # tocimobj
    
    ToCIMObj,

    ]

if __name__ == '__main__':
    main(tests)
