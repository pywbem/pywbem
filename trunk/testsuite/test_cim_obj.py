#!/usr/bin/env python

"""
Test CIM objects (e.g. `CIMInstance`).

Ideally this file would completely describe the Python interface to
CIM objects.  If a particular data structure or Python property is
not implemented here, then it is not officially supported by PyWBEM.
Any breaking of backwards compatibility of new development should be
picked up here.

Note that class `NocaseDict` is tested in test_nocasedict.py.
"""

import re
import inspect
import os.path
from datetime import timedelta, datetime

from pywbem import cim_obj, cim_types
from pywbem import CIMInstance, CIMInstanceName, CIMClass, CIMClassName, \
                   CIMProperty, CIMMethod, CIMParameter, CIMQualifier, \
                   Uint8, Uint16, Uint32, Uint64, \
                   Sint8, Sint16, Sint32, Sint64,\
                   Real32, Real64, CIMDateTime, NocaseDict

from comfychair import main, TestCase, NotRunError
from validate import validate_xml

class ValidateTest(TestCase):
    """
    A base class for test cases that need validation against CIM-XML.
    """

    def validate(self, obj, root_elem=None):
        """
        Convert a CIM object to its CIM-XML and validate that using the CIM-XML
        DTD.

        Raises a test failure if the validation fails.

        Arguments:
          * `obj`: The CIM object to be validated (e.g. a `CIMInstance` object)
          * `root_elem`: The expected XML root element of the CIM-XML
            representing the CIM object. `None` means that no test for an
            expected XML root element will happen.
        """
        global _MODULE_PATH # pylint: disable=global-variable-not-assigned
        xml = obj.tocimxml().toxml()
        self.log('Required XML root element: %s\nGenerated CIM-XML: %s' % \
                 (root_elem, xml))
        self.assert_(validate_xml(xml,
                                  dtd_directory=os.path.relpath(_MODULE_PATH),
                                  root_elem=root_elem),
                     'XML validation failed')

class DictTest(TestCase):
    """
    A base class for test cases that need to run a test against a dictionary
    interface, such as class `CIMInstance` that provides a dictionary interface
    for its properties.

    Note that the expected dictionary content upon input is hard coded at this
    point:
        obj['Chicken'] = 'Ham'
        obj['Beans'] = 42
    """

    def runtest_dict(self, obj):
        """
        Run the test against dictionary interfaces.

        Raises a test failure if the test fails.

        Arguments:

          * `obj`: The CIM object to be tested (e.g. `CIMInstance`).
        """

        # Test __getitem__

        self.assert_equal(obj['Chicken'], 'Ham')
        self.assert_equal(obj['Beans'], 42)

        self.assert_equal(obj['chickeN'], 'Ham')
        self.assert_equal(obj['beanS'], 42)

        try:
            dummy_val = obj['Cheepy']
        except KeyError:
            pass
        else:
            self.log("Object: %r" % obj)
            self.fail('KeyError not thrown when accessing undefined key '
                      '\'Cheepy\'')

        # Test __setitem__

        obj['tmp'] = 'tmp'
        self.assert_equal(obj['Tmp'], 'tmp')

        # Test has_key

        self.assert_(obj.has_key('tmP'))

        # Test __delitem__

        del obj['tMp']
        self.assert_(not obj.has_key('tmp'))

        # Test __len__

        self.assert_equal(len(obj), 2)

        # Test keys

        keys = obj.keys()
        self.assert_('Chicken' in keys and 'Beans' in keys)
        self.assert_equal(len(keys), 2)

        # Test values

        values = obj.values()
        self.assert_('Ham' in values and 42 in values)
        self.assert_equal(len(values), 2)

        # Test items

        items = obj.items()
        self.assert_(('Chicken', 'Ham') in items and
                     ('Beans', 42) in items)
        self.assert_equal(len(items), 2)

        # Test iterkeys

        keys = list(obj.iterkeys())
        self.assert_('Chicken' in keys and 'Beans' in keys)
        self.assert_equal(len(keys), 2)

        # Test itervalues

        values = list(obj.itervalues())
        self.assert_('Ham' in values and 42 in values)
        self.assert_equal(len(values), 2)

        # Test iteritems

        items = list(obj.iteritems())
        self.assert_(('Chicken', 'Ham') in items and
                     ('Beans', 42) in items)
        self.assert_equal(len(items), 2)

        # Test in

        self.assert_('Chicken' in obj and 'Beans' in obj)

        # Test get

        self.assert_equal(obj.get('Chicken'), 'Ham')
        self.assert_equal(obj.get('Beans'), 42)

        self.assert_equal(obj.get('chickeN'), 'Ham')
        self.assert_equal(obj.get('beanS'), 42)

        try:
            default_value = 'NoValue'
            invalid_propname = 'Cheepy'
            self.assert_equal(obj.get(invalid_propname, default_value),
                              default_value)
        except Exception as exc:
            self.log("Object: %r" % obj)
            self.fail('%s thrown in exception-free get() when accessing '
                      'undefined key %s' % \
                      (exc.__class__.__name__, invalid_propname))

        # Test update

        obj.update({'One':'1', 'Two': '2'})
        self.assert_equal(obj['one'], '1')
        self.assert_equal(obj['two'], '2')
        self.assert_equal(obj['Chicken'], 'Ham')
        self.assert_equal(obj['Beans'], 42)
        self.assert_equal(len(obj), 4)

        obj.update({'Three':'3', 'Four': '4'}, [('Five', '5')])
        self.assert_equal(obj['three'], '3')
        self.assert_equal(obj['four'], '4')
        self.assert_equal(obj['five'], '5')
        self.assert_equal(len(obj), 7)

        obj.update([('Six', '6')], Seven='7', Eight='8')
        self.assert_equal(obj['six'], '6')
        self.assert_equal(obj['seven'], '7')
        self.assert_equal(obj['eight'], '8')
        self.assert_equal(len(obj), 10)

        obj.update(Nine='9', Ten='10')
        self.assert_equal(obj['nine'], '9')
        self.assert_equal(obj['ten'], '10')
        self.assert_equal(obj['Chicken'], 'Ham')
        self.assert_equal(obj['Beans'], 42)
        self.assert_equal(len(obj), 12)

        del obj['one'], obj['two']
        del obj['three'], obj['four'], obj['five']
        del obj['six'], obj['seven'], obj['eight']
        del obj['nine'], obj['ten']
        self.assert_equal(len(obj), 2)

###############################################################################
# CIMInstanceName
###############################################################################

class _CIMInstanceNameTestCase(TestCase):
    """Base class for CIMInstanceName test cases, adding assertion methods."""

    def _assert_obj(self, obj, classname, keybindings, host=None,
                    namespace=None):
        """
        Verify the attributes of the CIMInstanceName object in `obj` against
        expected values passed as the remaining arguments.
        """
        self.assert_equal(obj.classname, classname, "classname attribute")
        self.assert_equal(obj.keybindings, keybindings, "keybindings attribute")
        self.assert_equal(obj.host, host, "host attribute")
        self.assert_equal(obj.namespace, namespace, "namespace attribute")

class InitCIMInstanceName(_CIMInstanceNameTestCase):
    """
    Test the initialization of `CIMInstanceName` objects, and that their data
    attributes have the values that were passed to the constructor.

    Constructor arguments:
        def __init__(self, classname, keybindings=None, host=None,
                     namespace=None):

    Note that the order of the arguments `host` and `namespace` in the
    constructor is swapped compared to their optionality, for historical
    reasons.

    Instance attributes of the resulting object:
      * `classname`: Class name
      * `keybindings`: NocaseDict dictionary with CIMProperty objects as values
      * `host`: Server IP address or host name, possibly including port
      * `namespace`: CIM namespace
    """

    def runtest(self):

        # Initialize with class name only

        obj = CIMInstanceName('CIM_Foo')
        self._assert_obj(obj, 'CIM_Foo', {})

        obj = CIMInstanceName(classname='CIM_Foo')
        self._assert_obj(obj, 'CIM_Foo', {})

        # Initialize with key bindings dictionary in addition

        kb = {'Name': 'Foo', 'Chicken': 'Ham'}

        obj = CIMInstanceName('CIM_Foo', kb)
        self._assert_obj(obj, 'CIM_Foo', kb)

        obj = CIMInstanceName('CIM_Foo', keybindings=kb)
        self._assert_obj(obj, 'CIM_Foo', kb)

        kb = NocaseDict({'Name': 'Foo', 'Chicken': 'Ham'})

        obj = CIMInstanceName('CIM_Foo', kb)
        self._assert_obj(obj, 'CIM_Foo', kb)

        kb = {'Name': 'Foo',
              'Number': 42,
              'Boolean': False,
              'Ref': CIMInstanceName('CIM_Bar')}

        obj = CIMInstanceName('CIM_Foo', kb)
        self._assert_obj(obj, 'CIM_Foo', kb)

        # Initialize with namespace in addition

        kb = {'InstanceID': '1234'}

        obj = CIMInstanceName('CIM_Foo', kb, None, 'root/cimv2')
        self._assert_obj(obj, 'CIM_Foo', kb, None, 'root/cimv2')

        obj = CIMInstanceName('CIM_Foo', kb, namespace='root/cimv2')
        self._assert_obj(obj, 'CIM_Foo', kb, None, 'root/cimv2')

        # Initialize with host in addition

        obj = CIMInstanceName('CIM_Foo', kb,
                              'woot.com', 'root/cimv2')
        self._assert_obj(obj, 'CIM_Foo', kb, 'woot.com', 'root/cimv2')

        obj = CIMInstanceName('CIM_Foo', kb,
                              namespace='root/cimv2', host='woot.com')
        self._assert_obj(obj, 'CIM_Foo', kb, 'woot.com', 'root/cimv2')

class CopyCIMInstanceName(_CIMInstanceNameTestCase):
    """
    Test the copy() method of `CIMInstanceName` objects.

    The basic idea is to modify the copy, and to verify that the original is
    still the same.
    """

    def runtest(self):

        i = CIMInstanceName('CIM_Foo',
                            keybindings={'InstanceID': '1234'},
                            host='woot.com',
                            namespace='root/cimv2')

        c = i.copy()

        self.assert_equal(i, c)

        c.classname = 'CIM_Bar'
        c.keybindings = NocaseDict({'InstanceID': '5678'})
        c.host = None
        c.namespace = None

        self._assert_obj(i, 'CIM_Foo', {'InstanceID': '1234'},
                         'woot.com', 'root/cimv2')

class CIMInstanceNameAttrs(_CIMInstanceNameTestCase):
    """
    Test that the public data attributes of `CIMInstanceName` objects can be
    accessed and modified.
    """

    def runtest(self):

        kb = {'Chicken': 'Ham', 'Beans': 42}

        obj = CIMInstanceName('CIM_Foo',
                              kb,
                              namespace='root/cimv2',
                              host='woot.com')

        self._assert_obj(obj, 'CIM_Foo', kb,
                         'woot.com', 'root/cimv2')

        kb = {'InstanceID': '5678'}

        obj.classname = 'CIM_Bar'
        obj.keybindings = kb
        obj.host = 'woom.com'
        obj.namespace = 'root/interop'

        self._assert_obj(obj, 'CIM_Bar', kb,
                         'woom.com', 'root/interop')

class CIMInstanceNameDict(DictTest):
    """
    Test the dictionary interface of `CIMInstanceName` objects.
    """

    def runtest(self):

        kb = {'Chicken': 'Ham', 'Beans': 42}
        obj = CIMInstanceName('CIM_Foo', kb)

        self.runtest_dict(obj)

class CIMInstanceNameEquality(TestCase):
    """
    Test the equality comparison of `CIMInstanceName` objects.
    """

    def runtest(self):

        # Basic equality tests

        self.assert_equal(CIMInstanceName('CIM_Foo'),
                          CIMInstanceName('CIM_Foo'))

        self.assert_notequal(CIMInstanceName('CIM_Foo', {'Cheepy': 'Birds'}),
                             CIMInstanceName('CIM_Foo'))

        self.assert_equal(CIMInstanceName('CIM_Foo', {'Cheepy': 'Birds'}),
                          CIMInstanceName('CIM_Foo', {'Cheepy': 'Birds'}))

        # Class name should be case insensitive

        self.assert_equal(CIMInstanceName('CIM_Foo'),
                          CIMInstanceName('ciM_foO'))

        # Key bindings should be case insensitive

        self.assert_equal(CIMInstanceName('CIM_Foo', {'Cheepy': 'Birds'}),
                          CIMInstanceName('CIM_Foo', {'cheepy': 'Birds'}))

        self.assert_notequal(CIMInstanceName('CIM_Foo', {'Cheepy': 'Birds'}),
                             CIMInstanceName('CIM_Foo', {'cheepy': 'birds'}))

        # Test a bunch of different key binding types

        obj1 = CIMInstanceName('CIM_Foo', {'Name': 'Foo',
                                           'Boolean': False,
                                           'Number': 42,
                                           'Ref': CIMInstanceName('CIM_Bar')})

        obj2 = CIMInstanceName('CIM_Foo', {'Name': 'Foo',
                                           'Number': 42,
                                           'Boolean': False,
                                           'Ref': CIMInstanceName('CIM_Bar')})

        self.assert_equal(obj1, obj2)

        # Test that key binding types are not confused in comparisons

        self.assert_notequal(CIMInstanceName('CIM_Foo', {'Foo': '42'}),
                             CIMInstanceName('CIM_Foo', {'Foo': 42}))

        self.assert_notequal(CIMInstanceName('CIM_Foo', {'Bar': True}),
                             CIMInstanceName('CIM_Foo', {'Bar': 'TRUE'}))

        # Host name should be case insensitive

        self.assert_equal(CIMInstanceName('CIM_Foo', host='woot.com'),
                          CIMInstanceName('CIM_Foo', host='Woot.Com'))

        # Namespace should be case insensitive

        self.assert_equal(CIMInstanceName('CIM_Foo', namespace='root/cimv2'),
                          CIMInstanceName('CIM_Foo', namespace='Root/CIMv2'))

class CIMInstanceNameCompare(TestCase):
    """
    Test the ordering comparison of `CIMInstanceName` objects.
    """

    def runtest(self):
        # TODO Implement ordering comparison test for CIMInstanceName
        raise NotRunError("unimplemented")

class CIMInstanceNameSort(TestCase):
    """
    Test the sorting of `CIMInstanceName` objects.
    """

    def runtest(self):
        # TODO Implement sorting test for CIMInstanceName
        raise NotRunError("unimplemented")

class CIMInstanceNameString(TestCase):
    """
    Test the string representation functions of `CIMInstanceName` objects.
    """

    def runtest(self):

        obj = CIMInstanceName('CIM_Foo', {'Name': 'Foo', 'Secret': 42})

        # The str() method generates output with class name and
        # key bindings:
        #    CIM_Foo.Secret=42,Name="Foo"

        s = str(obj)

        # We need to tolerate different orders of the key bindings
        self.assert_re_match(r'^CIM_Foo\.', s)
        self.assert_re_search('Secret=42', s)
        self.assert_re_search('Name="Foo"', s)

        s = s.replace('CIM_Foo.', '')
        s = s.replace('Secret=42', '')
        s = s.replace('Name="Foo"', '')

        self.assert_(s == ',')

        # Test repr() function contains slightly more verbose
        # output, but we're not too concerned about the format:
        #    CIMInstanceName(classname='CIM_Foo', \
        #        keybindings=NocaseDict({'Secret': 42, 'Name': 'Foo'}))

        r = repr(obj)

        self.assert_re_match(r"^CIMInstanceName\(", r)
        self.assert_re_search('classname=[\'"]CIM_Foo[\'"]', r)
        self.assert_re_search('keybindings=', r)
        self.assert_re_search('[\'"]Secret[\'"]: 42', r)
        self.assert_re_search('[\'"]Name[\'"]: [\'"]Foo[\'"]', r)

        # Test str() with namespace

        obj = CIMInstanceName('CIM_Foo', {'InstanceID': '1234'},
                              namespace='root/InterOp')

        self.assert_equal(str(obj), 'root/InterOp:CIM_Foo.InstanceID="1234"')

        # Test str() with host and namespace

        obj = CIMInstanceName('CIM_Foo', {'InstanceID': '1234'},
                              host='woot.com',
                              namespace='root/InterOp')

        self.assert_equal(str(obj),
                          '//woot.com/root/InterOp:CIM_Foo.InstanceID="1234"')

class CIMInstanceNameToXML(ValidateTest):
    """
    Test that valid CIM-XML is generated for `CIMInstanceName` objects.
    """

    def runtest(self):

        # XML root elements for CIM-XML representations of CIMInstanceName
        root_elem_CIMInstanceName_plain = 'INSTANCENAME'
        root_elem_CIMInstanceName_namespace = 'LOCALINSTANCEPATH'
        root_elem_CIMInstanceName_host = 'INSTANCEPATH'

        self.validate(CIMInstanceName('CIM_Foo'),
                      root_elem_CIMInstanceName_plain)

        self.validate(CIMInstanceName('CIM_Foo',
                                      {'Cheepy': 'Birds'}),
                      root_elem_CIMInstanceName_plain)

        self.validate(CIMInstanceName('CIM_Foo',
                                      {'Name': 'Foo',
                                       'Number': 42,
                                       'Boolean': False,
                                       'Ref': CIMInstanceName('CIM_Bar')}),
                      root_elem_CIMInstanceName_plain)

        self.validate(CIMInstanceName('CIM_Foo',
                                      namespace='root/cimv2'),
                      root_elem_CIMInstanceName_namespace)

        self.validate(CIMInstanceName('CIM_Foo',
                                      host='woot.com',
                                      namespace='root/cimv2'),
                      root_elem_CIMInstanceName_host)

###############################################################################
# CIMInstance
###############################################################################

class InitCIMInstance(TestCase):
    """
    Test the initialization of `CIMInstance` objects, and that their instance
    attributes have the values that were passed to the constructor.

    Constructor arguments:
        def __init__(self, classname, properties={}, qualifiers={},
                     path=None, property_list=None):

    Instance attributes of the resulting object:
      * `classname`: Class name
      * `properties`: NocaseDict dictionary with CIMProperty objects as values
      * `qualifiers`: NocaseDict dictionary with CIMQualifier objects as values
      * `path`: CIMInstanceName object with instance path, optional
      * `property_list`: TODO Understand this argument

    On properties: We are testing a reasonably full range of input variations,
    because there is processing of the provided properties in
    `CIMInstance.__init__`.

    On qualifiers: The full range of input variations is not tested, because
    we know that the input argument is just turned into a `NocaseDict` and
    otherwise left unchanged, so the full range testing is expected to be done
    in the test cases for `CIMQualifier`.
    """

    def runtest(self):

        # Initialize with class name only

        obj = CIMInstance('CIM_Foo')

        self.assert_equal(obj.classname, 'CIM_Foo')
        self.assert_equal(obj.properties, {})
        self.assert_equal(obj.qualifiers, {})
        self.assert_equal(obj.path, None)
        self.assert_equal(obj.property_list, None)

        obj = CIMInstance(classname='CIM_Foo')

        self.assert_equal(obj.classname, 'CIM_Foo')
        self.assert_equal(obj.properties, {})
        self.assert_equal(obj.qualifiers, {})
        self.assert_equal(obj.path, None)
        self.assert_equal(obj.property_list, None)

        # Initialize with properties of all valid non-array, non-ref types

        props_input = {}
        props_input[1] = {
            'S1': b'Ham',
            'S2': u'H\u00E4m', # U+00E4 = lower case a umlaut
            'B': True,
            'UI8': Uint8(42),
            'UI16': Uint16(4216),
            'UI32': Uint32(4232),
            'UI64': Uint64(4264),
            'SI8': Sint8(-42),
            'SI16': Sint16(-4216),
            'SI32': Sint32(-4232),
            'SI64': Sint64(-4264),
            'R32': Real32(42.0),
            'R64': Real64(42.64),
            'DTP': CIMDateTime(datetime(2014, 9, 22, 10, 49, 20, 524789)),
            'DTI': CIMDateTime(timedelta(10, 49, 20)),
        }
        props_input[2] = NocaseDict(props_input[1])
        props_input[3] = {
            'S1': CIMProperty(name='S1', type='string',
                              value=b'Ham', is_array=False),
            'S2': CIMProperty(name='S2', type='string',
                              value=u'H\u00E4m', is_array=False), # a umlaut
            'B': CIMProperty(name='B', type='boolean',
                             value=True, is_array=False),
            'UI8': CIMProperty(name='UI8', type='uint8',
                               value=Uint8(42), is_array=False),
            'UI16': CIMProperty(name='UI16', type='uint16',
                                value=Uint16(4216), is_array=False),
            'UI32': CIMProperty(name='UI32', type='uint32',
                                value=Uint32(4232), is_array=False),
            'UI64': CIMProperty(name='UI64', type='uint64',
                                value=Uint64(4264), is_array=False),
            'SI8': CIMProperty(name='SI8', type='sint8',
                               value=Sint8(-42), is_array=False),
            'SI16': CIMProperty(name='SI16', type='sint16',
                                value=Sint16(-4216), is_array=False),
            'SI32': CIMProperty(name='SI32', type='sint32',
                                value=Sint32(-4232), is_array=False),
            'SI64': CIMProperty(name='SI64', type='sint64',
                                value=Sint64(-4264), is_array=False),
            'R32': CIMProperty(name='R32', type='real32',
                               value=Real32(42.0), is_array=False),
            'R64': CIMProperty(name='R64', type='real64',
                               value=Real64(42.64), is_array=False),
            'DTP': CIMProperty(name='DTP', type='datetime',
                               value=CIMDateTime(datetime(2014, 9, 22, 10, 49,
                                                          20, 524789)),
                               is_array=False),
            'DTI': CIMProperty(name='DTI', type='datetime',
                               value=CIMDateTime(timedelta(10, 49, 20)),
                               is_array=False),
        }
        props_input[4] = NocaseDict(props_input[3])
        props_obj = props_input[4] # for all kinds of input

        for i in props_input:

            obj = CIMInstance('CIM_Foo', props_input[i])

            self.assert_equal(obj.classname, 'CIM_Foo')
            self.assert_equal(obj.properties, props_obj)
            self.assert_equal(obj.qualifiers, {})
            self.assert_equal(obj.path, None)
            self.assert_equal(obj.property_list, None)

            obj = CIMInstance('CIM_Foo', properties=props_input[i])

            self.assert_equal(obj.classname, 'CIM_Foo')
            self.assert_equal(obj.properties, props_obj)
            self.assert_equal(obj.qualifiers, {})
            self.assert_equal(obj.path, None)
            self.assert_equal(obj.property_list, None)

        # Check that initialization with Python integer and floating point
        # values is rejected

        num_values = [42, 42L, 42.1]
        for num_value in num_values:
            try:
                inst = CIMInstance('CIM_Foo',
                                   properties={'Age': CIMProperty('Age',
                                                                  num_value)})
            except TypeError:
                pass
            else:
                self.log('Instance properties: %r' % inst.properties)
                self.fail('TypeError not raised for invalid value %s '
                          '(type %s) for property of unspecified type' % \
                          (num_value, type(num_value)))

        # Check that initialization with string values for boolean types
        # is rejected
        if False: # TODO Re-enable this test once this check is implemented
            try:
                inst = CIMInstance('CIM_Foo',
                                   properties={'Old':
                                               CIMProperty('Old',
                                                           type='boolean',
                                                           value='TRUE')})
            except TypeError:
                pass
            else:
                self.log('Instance properties: %r' % inst.properties)
                self.fail('TypeError not raised for invalid value \'TRUE\' '
                          '(type string) for property of type boolean')

        # Initialize with some qualifiers

        quals_input = {}
        # TODO Add tests for qualifiers as plain dict, once supported
        #      e.g. quals_input = {'Key': True}
        quals_input[1] = {'Key': CIMQualifier('Key', True)}
        quals_input[2] = NocaseDict(quals_input[1])
        quals_obj = quals_input[2] # for all kinds of input

        for i in quals_input:

            obj = CIMInstance('CIM_Foo', {}, quals_input[i])

            self.assert_equal(obj.classname, 'CIM_Foo')
            self.assert_equal(obj.properties, {})
            self.assert_equal(obj.qualifiers, quals_obj)
            self.assert_equal(obj.path, None)
            self.assert_equal(obj.property_list, None)

            obj = CIMInstance('CIM_Foo', qualifiers=quals_input[i])

            self.assert_equal(obj.classname, 'CIM_Foo')
            self.assert_equal(obj.properties, {})
            self.assert_equal(obj.qualifiers, quals_obj)
            self.assert_equal(obj.path, None)
            self.assert_equal(obj.property_list, None)

        # Initialize with key properties and path

        kb = {'InstanceID': '1234'}
        props_input = kb
        props_obj = NocaseDict(
            {'InstanceID': CIMProperty(name='InstanceID', type='string',
                                       value='1234', is_array=False)})
        path_input = CIMInstanceName('CIM_Foo', kb)
        path_obj = path_input

        obj = CIMInstance('CIM_Foo', props_input, {}, path_input)

        self.assert_equal(obj.classname, 'CIM_Foo')
        self.assert_equal(obj.properties, props_obj)
        self.assert_equal(obj.qualifiers, {})
        self.assert_equal(obj.path, path_obj)
        self.assert_equal(obj.property_list, None)

        obj = CIMInstance('CIM_Foo', props_input, path=path_input)

        self.assert_equal(obj.classname, 'CIM_Foo')
        self.assert_equal(obj.properties, props_obj)
        self.assert_equal(obj.qualifiers, {})
        self.assert_equal(obj.path, path_obj)
        self.assert_equal(obj.property_list, None)

        # Note: Tests for initializing CIMInstance with property_list are
        #       handled in class CIMInstancePropertyList.

class CopyCIMInstance(TestCase):
    """
    Test the copy() method of `CIMInstance` objects.

    The basic idea is to modify the copy, and to verify that the original is
    still the same.
    """

    def runtest(self):

        # TODO Add tests for CIMInstance property_list argument

        i = CIMInstance('CIM_Foo',
                        properties={'Name': 'Foo', 'Chicken': 'Ham'},
                        qualifiers={'Key': CIMQualifier('Key', True)},
                        path=CIMInstanceName('CIM_Foo', {'Name': 'Foo'}))

        c = i.copy()

        self.assert_equal(i, c)

        c.classname = 'CIM_Bar'
        c.properties = {'InstanceID': '5678'}
        c.qualifiers = {}
        c.path = None

        self.assert_equal(i.classname, 'CIM_Foo')
        self.assert_equal(i['Name'], 'Foo')
        self.assert_equal(i.qualifiers['Key'], CIMQualifier('Key', True))
        self.assert_equal(i.path, CIMInstanceName('CIM_Foo', {'Name': 'Foo'}))

        # Test copy when path is None

        i = CIMInstance('CIM_Foo',
                        properties={'Name': 'Foo', 'Chicken': 'Ham'},
                        qualifiers={'Key': CIMQualifier('Key', True)},
                        path=None)

        c = i.copy()

        self.assert_equal(i, c)

        c.classname = 'CIM_Bar'
        c.properties = {'InstanceID': '5678'}
        c.qualifiers = {}
        c.path = CIMInstanceName('CIM_Foo', {'Name': 'Foo'})

        self.assert_equal(i.classname, 'CIM_Foo')
        self.assert_equal(i['Name'], 'Foo')
        self.assert_equal(i.qualifiers['Key'], CIMQualifier('Key', True))
        self.assert_equal(i.path, None)

class CIMInstanceAttrs(TestCase):
    """
    Test that the public data attributes of `CIMInstance` objects can be
    accessed and modified.
    """

    def runtest(self):

        props = {'Chicken': CIMProperty('Chicken', 'Ham'),
                 'Number': CIMProperty('Number', Uint32(42))}
        quals = {'Key': CIMQualifier('Key', True)}
        path = CIMInstanceName('CIM_Foo', {'Chicken': 'Ham'})

        obj = CIMInstance('CIM_Foo',
                          properties=props,
                          qualifiers=quals,
                          path=path)

        self.assert_equal(obj.classname, 'CIM_Foo')
        self.assert_equal(obj.properties, props)
        self.assert_equal(obj.qualifiers, quals)
        self.assert_equal(obj.path, path)

        props = {'Foo': CIMProperty('Foo', 'Bar')}
        quals = {'Min': CIMQualifier('Min', Uint32(42))}
        path = CIMInstanceName('CIM_Bar', {'Foo': 'Bar'})

        obj.classname = 'CIM_Bar'
        obj.properties = props
        obj.qualifiers = quals
        obj.path = path

        self.assert_equal(obj.classname, 'CIM_Bar')
        self.assert_equal(obj.properties, props)
        self.assert_equal(obj.qualifiers, quals)
        self.assert_equal(obj.path, path)

class CIMInstanceDict(DictTest):
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
            self.log('Instance properties: %r' % obj.properties)
            self.fail('TypeError not raised for invalid value 43 '
                      '(type int) for property of unspecified type')

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
                                         qualifiers={'Key':
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

        self.assert_equal(
            CIMInstance('CIM_Foo',
                        {'Null': CIMProperty('Null', None, type='string')}),
            CIMInstance('CIM_Foo',
                        {'Null': CIMProperty('Null', None, type='string')}))

        self.assert_notequal(
            CIMInstance('CIM_Foo',
                        {'Null': CIMProperty('Null', None, type='string')}),
            CIMInstance('CIM_Foo',
                        {'Null': CIMProperty('Null', '')}))

        self.assert_notequal(
            CIMInstance('CIM_Foo',
                        {'Null': CIMProperty('Null', None, type='uint32')}),
            CIMInstance('CIM_Foo',
                        {'Null': CIMProperty('Null', Uint32(0))}))

        # Mix of CIMProperty and native Python types

        self.assert_equal(
            CIMInstance('CIM_Foo',
                        {'string': 'string',
                         'uint8': Uint8(0),
                         'uint8array': [Uint8(1), Uint8(2)],
                         'ref': CIMInstanceName('CIM_Bar')}),
            CIMInstance('CIM_Foo',
                        {'string': CIMProperty('string', 'string'),
                         'uint8': CIMProperty('uint8', Uint8(0)),
                         'uint8Array': CIMProperty('uint8Array',
                                                   [Uint8(1), Uint8(2)]),
                         'ref': CIMProperty('ref',
                                            CIMInstanceName('CIM_Bar'))})
            )

class CIMInstanceCompare(TestCase):
    """
    Test the ordering comparison of `CIMInstance` objects.
    """

    def runtest(self):
        # TODO Implement ordering comparison test for CIMInstance
        raise NotRunError("unimplemented")

class CIMInstanceSort(TestCase):
    """
    Test the sorting of `CIMInstance` objects.
    """

    def runtest(self):
        # TODO Implement sorting test for CIMInstance
        raise NotRunError("unimplemented")

class CIMInstanceString(TestCase):
    """
    Test the string representation functions of `CIMInstance` objects.
    """

    def runtest(self):

        obj = CIMInstance('CIM_Foo', {'Name': 'Spottyfoot',
                                      'Ref1': CIMInstanceName('CIM_Bar')})

        # The str() and repr() methods generate output with class name and
        # maybe no further details:
        #    CIMInstance(classname='CIM_Foo', ...)

        s = str(obj)

        self.assert_re_match(r"^CIMInstance\(", s)
        self.assert_re_search('classname=[\'"]CIM_Foo[\'"]', s)
        self.assert_equal(s.find('Name'), -1)
        self.assert_equal(s.find('Ref1'), -1)

        r = repr(obj)

        self.assert_re_match(r"^CIMInstance\(", r)
        self.assert_re_search('classname=[\'"]CIM_Foo[\'"]', r)
        self.assert_equal(r.find('Name'), -1)
        self.assert_equal(r.find('Ref1'), -1)

class CIMInstanceToXML(ValidateTest):
    """
    Test that valid CIM-XML is generated for `CIMInstance` objects.
    """

    def runtest(self):

        # XML root elements for CIM-XML representations of CIMInstance
        root_elem_CIMInstance_noname = 'INSTANCE'
        root_elem_CIMInstance_withname = 'VALUE.NAMEDINSTANCE'

        # Simple instances, no properties

        self.validate(CIMInstance('CIM_Foo'),
                      root_elem_CIMInstance_noname)

        # Path

        self.validate(CIMInstance('CIM_Foo',
                                  {'InstanceID': '1234'},
                                  path=CIMInstanceName(
                                      'CIM_Foo',
                                      {'InstanceID': '1234'})),
                      root_elem_CIMInstance_withname)

        # Multiple properties and qualifiers

        self.validate(CIMInstance('CIM_Foo',
                                  {'Spotty': 'Foot',
                                   'Age': Uint32(42)},
                                  qualifiers={'Key':
                                              CIMQualifier('Key', True)}),
                      root_elem_CIMInstance_noname)

        # Test every numeric property type

        for t in [Uint8, Uint16, Uint32, Uint64, Sint8, Sint16, Sint32, Sint64,
                  Real32, Real64]:
            self.validate(CIMInstance('CIM_Foo',
                                      {'Number': t(42)}),
                          root_elem_CIMInstance_noname)

        # Other property types

        self.validate(CIMInstance('CIM_Foo',
                                  {'Value': False}),
                      root_elem_CIMInstance_noname)

        self.validate(CIMInstance('CIM_Foo',
                                  {'Now': CIMDateTime.now()}),
                      root_elem_CIMInstance_noname)

        self.validate(CIMInstance('CIM_Foo',
                                  {'Now': timedelta(60)}),
                      root_elem_CIMInstance_noname)

        self.validate(CIMInstance('CIM_Foo',
                                  {'Ref': CIMInstanceName('CIM_Eep',
                                                          {'Foo': 'Bar'})}),
                      root_elem_CIMInstance_noname)

        # Array types.  Can't have an array of references

        for t in [Uint8, Uint16, Uint32, Uint64, Sint8, Sint16, Sint32, Sint64,
                  Real32, Real64]:

            self.validate(CIMInstance('CIM_Foo',
                                      {'Number': [t(42), t(43)]}),
                          root_elem_CIMInstance_noname)

        self.validate(CIMInstance('CIM_Foo',
                                  {'Now': [CIMDateTime.now(),
                                           CIMDateTime.now()]}),
                      root_elem_CIMInstance_noname)

        self.validate(CIMInstance('CIM_Foo',
                                  {'Then': [timedelta(60),
                                            timedelta(61)]}),
                      root_elem_CIMInstance_noname)

        # Null properties.  Can't have a NULL property reference.

        obj = CIMInstance('CIM_Foo')

        obj.properties['Cheepy'] = CIMProperty('Cheepy', None, type='string')
        obj.properties['Date'] = CIMProperty('Date', None, type='datetime')
        obj.properties['Bool'] = CIMProperty('Bool', None, type='boolean')

        for t in ['uint8', 'uint16', 'uint32', 'uint64', 'sint8', 'sint16',
                  'sint32', 'sint64', 'real32', 'real64']:
            obj.properties[t] = CIMProperty(t, None, type=t)

        self.validate(obj, root_elem_CIMInstance_noname)

        # Null property arrays.  Can't have arrays of NULL property
        # references.

        obj = CIMInstance('CIM_Foo')

        obj.properties['Cheepy'] = CIMProperty(
            'Cheepy', None, type='string', is_array=True)

        obj.properties['Date'] = CIMProperty(
            'Date', None, type='datetime', is_array=True)

        obj.properties['Bool'] = CIMProperty(
            'Bool', None, type='boolean', is_array=True)

        for t in ['uint8', 'uint16', 'uint32', 'uint64', 'sint8', 'sint16',
                  'sint32', 'sint64', 'real32', 'real64']:
            obj.properties[t] = CIMProperty(t, None, type=t, is_array=True)

        self.validate(obj, root_elem_CIMInstance_noname)

class CIMInstanceToMOF(TestCase):
    """
    Test that valid MOF is generated for `CIMInstance` objects.
    """

    def runtest(self):

        i = CIMInstance('CIM_Foo',
                        {'MyString': 'string',
                         'MyUint8': Uint8(0),
                         'MyUint8array': [Uint8(1), Uint8(2)],
                         'MyRef': CIMInstanceName('CIM_Bar')})

        imof = i.tomof()

        # Result (with unpredictable order of properties):
        #   instance of CIM_Foo {
        #       MyString = "string";
        #       MyRef = "CIM_Bar";
        #       MyUint8array = {1, 2};
        #       MyUint8 = 0;
        #   };

        self.log("Instance: %r\nGenerated MOF: %r" % (i, imof))
        m = re.match(
            r"^\s*instance\s+of\s+CIM_Foo\s*\{"
            r"(?:\s*(\w+)\s*=\s*.*;){4,4}" # just match the general syntax
            r"\s*\}\s*;\s*$", imof)
        if m is None:
            self.fail("Invalid MOF generated ")

class CIMInstanceUpdatePath(TestCase):
    """
    Test updating key and non-key properties of `CIMInstance` objects.
    """

    def runtest(self):

        iname = CIMInstanceName('CIM_Foo', namespace='root/cimv2',
                                keybindings={'k1': None, 'k2': None})

        i = CIMInstance('CIM_Foo', path=iname)

        i['k1'] = 'key1'
        self.assert_equal(i['k1'], 'key1')
        self.assert_('k1' in i)
        self.assert_equal(i.path['k1'], 'key1') # also updates the path

        i['k2'] = 'key2'
        self.assert_equal(i['k2'], 'key2')
        self.assert_('k2' in i)
        self.assert_equal(i.path['k2'], 'key2') # also updates the path

        i['p1'] = 'prop1'
        self.assert_equal(len(i.path.keybindings), 2)
        self.assert_('p1' not in i.path) # no key, does not update the path

class CIMInstancePropertyList(TestCase):
    """
    Test updating key and non-key properties of `CIMInstance` objects, with
    property list.
    """

    def runtest(self):

        iname = CIMInstanceName('CIM_Foo', namespace='root/cimv2',
                                keybindings={'k1': None, 'k2': None})

        i = CIMInstance('CIM_Foo', path=iname, property_list=['P1', 'P2'])

        self.assert_equal(i.property_list, ['p1', 'p2'])

        i['k1'] = 'key1'
        self.assert_equal(i['k1'], 'key1')
        self.assert_('k1' in i)
        self.assert_equal(i.path['k1'], 'key1') # also updates the path

        i['k2'] = 'key2'
        self.assert_equal(i['k2'], 'key2')
        self.assert_('k2' in i)
        self.assert_equal(i.path['k2'], 'key2') # also updates the path

        i['p1'] = 'prop1'
        self.assert_equal(i['p1'], 'prop1')
        self.assert_('p1' in i)
        self.assert_equal(len(i.path.keybindings), 2)
        self.assert_('p1' not in i.path)

        i['p2'] = 'prop2'
        self.assert_equal(i['p2'], 'prop2')
        self.assert_('p2' in i)
        self.assert_equal(len(i.path.keybindings), 2)
        self.assert_('p2' not in i.path)

        i['p3'] = 'prop3'
        self.assert_('p3' not in i) # the effect of property list

class CIMInstanceUpdateExisting(TestCase):
    """
    Test the update_existing() method of `CIMInstance` objects.

    There is also a test for update_existing() on `CIMInstanceName` objects.
    """

    def runtest(self):

        i = CIMInstance('CIM_Foo',
                        {'string': 'string',
                         'uint8': Uint8(0),
                         'uint8array': [Uint8(1), Uint8(2)],
                         'ref': CIMInstanceName('CIM_Bar')})

        self.assert_equal(i['string'], 'string')

        i.update_existing({'one': '1', 'string': '_string_'})
        self.assert_('one' not in i)
        self.assert_equal(i['string'], '_string_')
        try:
            i['one']
        except KeyError:
            pass
        else:
            self.fail('KeyError not thrown')
        self.assert_equal(i['uint8'], 0)

        i.update_existing([('Uint8', 1), ('one', 1)])
        self.assert_equal(i['uint8'], 1)
        self.assert_('one' not in i)

        i.update_existing(one=1, uint8=2)
        self.assert_('one' not in i)
        self.assert_equal(i['uint8'], 2)
        self.assert_(isinstance(i['uint8'], Uint8))
        self.assert_equal(i['uint8'], Uint8(2))
        self.assert_equal(i['uint8'], 2)

        i.update_existing(Uint8Array=[3, 4, 5], foo=[1, 2])
        self.assert_('foo' not in i)
        self.assert_equal(i['uint8array'], [3, 4, 5])
        self.assert_(isinstance(i['uint8array'][0], Uint8))

        name = CIMInstanceName('CIM_Foo',
                               keybindings={'string':'STRING', 'one':'1'})

        i.update_existing(name)
        self.assert_('one' not in i)
        self.assert_equal(i['string'], 'STRING')

###############################################################################
# CIMProperty
# Note: The term "old constructor implementation" used in some comments refers
# to the CIMProperty.__init__() implementation of pywbem 0.7.0.
###############################################################################

class _CIMPropertyTestCase(TestCase):
    """Base class for CIMProperty test cases, adding assertion methods."""

    def _assert_obj(self, obj, name, value, type=None,
                    class_origin=None, array_size=None, propagated=None,
                    is_array=False, reference_class=None, qualifiers=None,
                    embedded_object=None):
        """
        Verify the attributes of the CIMProperty object in `obj` against
        expected values passed as the remaining arguments.
        """
        self.assert_equal(obj.name, name, "name attribute")
        self.assert_equal(obj.value, value, "value attribute")
        self.assert_equal(obj.type, type, "type attribute")
        self.assert_equal(obj.class_origin, class_origin,
                          "class_origin attribute")
        self.assert_equal(obj.array_size, array_size, "array_size attribute")
        self.assert_equal(obj.propagated, propagated, "propagated attribute")
        self.assert_equal(obj.is_array, is_array, "is_array attribute")
        self.assert_equal(obj.reference_class, reference_class,
                          "reference_class attribute")
        self.assert_equal(obj.qualifiers, NocaseDict(qualifiers),
                          "qualifiers attribute")
        self.assert_equal(obj.embedded_object, embedded_object,
                          "embedded_object attribute")

class InitCIMProperty(_CIMPropertyTestCase):
    """
    Test the initialization of `CIMProperty` objects, and that their instance
    attributes have the expected values.

    On qualifiers: The full range of input variations is not tested, because
    we know that the input argument is just turned into a `NocaseDict` and
    otherwise left unchanged, so the full range testing is expected to be done
    in the test cases for `CIMQualifier`.
    """

    _INT_TYPES = ['uint8', 'uint16', 'uint32', 'uint64',
                  'sint8', 'sint16', 'sint32', 'sint64']
    _REAL_TYPES = ['real32', 'real64']

    def runtest(self):

        quals = {'Key': CIMQualifier('Key', True)}

        # Initialization to CIM string type

        p = CIMProperty('Spotty', 'Foot')
        self._assert_obj(p, 'Spotty', 'Foot', 'string')

        p = CIMProperty(name='Spotty', value='Foot')
        self._assert_obj(p, 'Spotty', 'Foot', 'string')

        p = CIMProperty('Spotty', 'Foot', 'string')
        self._assert_obj(p, 'Spotty', 'Foot', 'string')

        p = CIMProperty('Spotty', 'Foot', type='string')
        self._assert_obj(p, 'Spotty', 'Foot', 'string')

        p = CIMProperty('Spotty', None, type='string')
        self._assert_obj(p, 'Spotty', None, 'string')

        p = CIMProperty(u'Name', u'Brad')
        self._assert_obj(p, u'Name', u'Brad', 'string')

        p = CIMProperty('Spotty', 'Foot', qualifiers=quals)
        self._assert_obj(p, 'Spotty', 'Foot', 'string', qualifiers=quals)

        p = CIMProperty('Spotty', None, 'string', qualifiers=quals)
        self._assert_obj(p, 'Spotty', None, 'string', qualifiers=quals)

        # Initialization to CIM integer and real types

        p = CIMProperty('Age', Uint16(32))
        self._assert_obj(p, 'Age', 32, 'uint16')

        p = CIMProperty('Age', Uint16(32), 'uint16')
        self._assert_obj(p, 'Age', 32, 'uint16')

        p = CIMProperty('Age', Real32(32.0))
        self._assert_obj(p, 'Age', 32.0, 'real32')

        p = CIMProperty('Age', Real32(32.0), 'real32')
        self._assert_obj(p, 'Age', 32.0, 'real32')

        for type_ in InitCIMProperty._INT_TYPES + InitCIMProperty._REAL_TYPES:

            p = CIMProperty('Age', 32, type_)
            self._assert_obj(p, 'Age', 32, type_)

            p = CIMProperty('Age', None, type_)
            self._assert_obj(p, 'Age', None, type_)

        for type_ in InitCIMProperty._REAL_TYPES:

            p = CIMProperty('Age', 32.0, type_)
            self._assert_obj(p, 'Age', 32.0, type_)

        # Initialization to CIM boolean type

        p = CIMProperty('Aged', True)
        self._assert_obj(p, 'Aged', True, 'boolean')

        p = CIMProperty('Aged', True, 'boolean')
        self._assert_obj(p, 'Aged', True, 'boolean')

        p = CIMProperty('Aged', False)
        self._assert_obj(p, 'Aged', False, 'boolean')

        p = CIMProperty('Aged', False, 'boolean')
        self._assert_obj(p, 'Aged', False, 'boolean')

        p = CIMProperty('Aged', None, 'boolean')
        self._assert_obj(p, 'Aged', None, 'boolean')

        # Initialization to CIM datetime type

        timedelta_1 = timedelta(days=12345678, hours=22, minutes=44,
                                seconds=55, microseconds=654321)
        cim_datetime_1 = '12345678224455.654321:000'

        # This test failed in the old constructor implementation, because the
        # timedelta object was not converted to a CIMDateTime object.
        p = CIMProperty('Age', timedelta_1)
        self._assert_obj(p, 'Age', CIMDateTime(cim_datetime_1), 'datetime')

        # This test failed in the old constructor implementation, because the
        # timedelta object was not converted to a CIMDateTime object.
        p = CIMProperty('Age', timedelta_1, 'datetime')
        self._assert_obj(p, 'Age', CIMDateTime(cim_datetime_1), 'datetime')

        p = CIMProperty('Age', CIMDateTime(timedelta_1))
        self._assert_obj(p, 'Age', CIMDateTime(cim_datetime_1), 'datetime')

        p = CIMProperty('Age', CIMDateTime(timedelta_1), 'datetime')
        self._assert_obj(p, 'Age', CIMDateTime(cim_datetime_1), 'datetime')

        # This test failed in the old constructor implementation, because the
        # datetime formatted string was not converted to a CIMDateTime object.
        p = CIMProperty('Age', cim_datetime_1, 'datetime')
        self._assert_obj(p, 'Age', CIMDateTime(cim_datetime_1), 'datetime')

        p = CIMProperty('Age', CIMDateTime(cim_datetime_1))
        self._assert_obj(p, 'Age', CIMDateTime(cim_datetime_1), 'datetime')

        p = CIMProperty('Age', CIMDateTime(cim_datetime_1), 'datetime')
        self._assert_obj(p, 'Age', CIMDateTime(cim_datetime_1), 'datetime')

        datetime_2 = datetime(year=2014, month=9, day=24, hour=19, minute=30,
                              second=40, microsecond=654321,
                              tzinfo=cim_types.MinutesFromUTC(120))
        cim_datetime_2 = '20140924193040.654321+120'

        # This test failed in the old constructor implementation, because the
        # datetime object was not converted to a CIMDateTime object.
        p = CIMProperty('Age', datetime_2)
        self._assert_obj(p, 'Age', CIMDateTime(cim_datetime_2), 'datetime')

        # This test failed in the old constructor implementation, because the
        # datetime object was not converted to a CIMDateTime object.
        p = CIMProperty('Age', datetime_2, 'datetime')
        self._assert_obj(p, 'Age', CIMDateTime(cim_datetime_2), 'datetime')

        p = CIMProperty('Age', CIMDateTime(datetime_2))
        self._assert_obj(p, 'Age', CIMDateTime(cim_datetime_2), 'datetime')

        p = CIMProperty('Age', CIMDateTime(datetime_2), 'datetime')
        self._assert_obj(p, 'Age', CIMDateTime(cim_datetime_2), 'datetime')

        # This test failed in the old constructor implementation, because the
        # datetime formatted string was not converted to a CIMDateTime object.
        p = CIMProperty('Age', cim_datetime_2, 'datetime')
        self._assert_obj(p, 'Age', CIMDateTime(cim_datetime_2), 'datetime')

        p = CIMProperty('Age', CIMDateTime(cim_datetime_2))
        self._assert_obj(p, 'Age', CIMDateTime(cim_datetime_2), 'datetime')

        p = CIMProperty('Age', CIMDateTime(cim_datetime_2), 'datetime')
        self._assert_obj(p, 'Age', CIMDateTime(cim_datetime_2), 'datetime')

        # Reference properties

        p = CIMProperty('Foo', None, 'reference')
        self._assert_obj(p, 'Foo', None, 'reference', reference_class=None)

        # This test failed in the old constructor implementation, because the
        # reference_class argument was required to be provided for references.
        p = CIMProperty('Foo', CIMInstanceName('CIM_Foo'))
        self._assert_obj(p, 'Foo', CIMInstanceName('CIM_Foo'), 'reference',
                         reference_class='CIM_Foo')

        # This test failed in the old constructor implementation, because the
        # reference_class argument was required to be provided for references.
        p = CIMProperty('Foo', CIMInstanceName('CIM_Foo'), 'reference')
        self._assert_obj(p, 'Foo', CIMInstanceName('CIM_Foo'), 'reference',
                         reference_class='CIM_Foo')

        # This test failed in the old constructor implementation, because the
        # reference_class argument was required to be provided for references.
        p = CIMProperty('Foo', CIMInstanceName('CIM_Foo'),
                        qualifiers=quals)
        self._assert_obj(p, 'Foo', CIMInstanceName('CIM_Foo'), 'reference',
                         reference_class='CIM_Foo', qualifiers=quals)

        # This test failed in the old constructor implementation, because the
        # reference_class argument was required to be provided for references.
        p = CIMProperty('Foo', CIMInstanceName('CIM_Foo'), 'reference',
                        qualifiers=quals)
        self._assert_obj(p, 'Foo', CIMInstanceName('CIM_Foo'), 'reference',
                         reference_class='CIM_Foo', qualifiers=quals)

        p = CIMProperty('Foo', CIMInstanceName('CIM_Foo'),
                        reference_class='CIM_Foo')
        self._assert_obj(p, 'Foo', CIMInstanceName('CIM_Foo'), 'reference',
                         reference_class='CIM_Foo')

        p = CIMProperty('Foo', CIMInstanceName('CIM_Foo'), 'reference',
                        reference_class='CIM_Foo')
        self._assert_obj(p, 'Foo', CIMInstanceName('CIM_Foo'), 'reference',
                         reference_class='CIM_Foo')

        p = CIMProperty('Foo', CIMInstanceName('CIM_Foo'),
                        reference_class='CIM_Foo', qualifiers=quals)
        self._assert_obj(p, 'Foo', CIMInstanceName('CIM_Foo'), 'reference',
                         reference_class='CIM_Foo', qualifiers=quals)

        p = CIMProperty('Foo', CIMInstanceName('CIM_Foo'), 'reference',
                        reference_class='CIM_Foo', qualifiers=quals)
        self._assert_obj(p, 'Foo', CIMInstanceName('CIM_Foo'), 'reference',
                         reference_class='CIM_Foo', qualifiers=quals)

        # Initialization to CIM embedded object / instance

        # This test failed in the old constructor implementation, because the
        # type argument was required to be provided for embedded objects.
        p = CIMProperty('Bar', None, embedded_object='object')
        self._assert_obj(p, 'Bar', None, 'string', embedded_object='object')

        p = CIMProperty('Bar', None, 'string', embedded_object='object')
        self._assert_obj(p, 'Bar', None, 'string', embedded_object='object')

        ec = CIMClass('CIM_Bar')

        p = CIMProperty('Bar', ec)
        self._assert_obj(p, 'Bar', ec, 'string', embedded_object='object')

        # This test failed in the old constructor implementation, because the
        # embedded_object attribute was not implied from the value argument if
        # the type argument was also provided.
        p = CIMProperty('Bar', ec, 'string')
        self._assert_obj(p, 'Bar', ec, 'string', embedded_object='object')

        p = CIMProperty('Bar', ec, embedded_object='object')
        self._assert_obj(p, 'Bar', ec, 'string', embedded_object='object')

        p = CIMProperty('Bar', ec, 'string', embedded_object='object')
        self._assert_obj(p, 'Bar', ec, 'string', embedded_object='object')

        ei = CIMInstance('CIM_Bar')

        # This test failed in the old constructor implementation, because the
        # embedded_object argument value of 'object' was changed to 'instance'
        # when a CIMInstance typed value was provided.
        p = CIMProperty('Bar', ei, embedded_object='object')
        self._assert_obj(p, 'Bar', ei, 'string', embedded_object='object')

        p = CIMProperty('Bar', ei, 'string', embedded_object='object')
        self._assert_obj(p, 'Bar', ei, 'string', embedded_object='object')

        p = CIMProperty('Bar', ei)
        self._assert_obj(p, 'Bar', ei, 'string', embedded_object='instance')

        # This test failed in the old constructor implementation, because the
        # embedded_object attribute was not implied from the value argument if
        # the type argument was also provided.
        p = CIMProperty('Bar', ei, 'string')
        self._assert_obj(p, 'Bar', ei, 'string', embedded_object='instance')

        p = CIMProperty('Bar', ei, embedded_object='instance')
        self._assert_obj(p, 'Bar', ei, 'string', embedded_object='instance')

        p = CIMProperty('Bar', ei, 'string', embedded_object='instance')
        self._assert_obj(p, 'Bar', ei, 'string', embedded_object='instance')

        # Check that initialization with Null without specifying a type is
        # rejected

        try:
            CIMProperty('Spotty', None)
        except (ValueError, TypeError):
            pass
        else:
            self.fail('ValueError or TypeError not raised')

        # Check that initialization with Python integer and floating point
        # values without specifying a type is rejected

        for val in [42, 42L, 42.0]:
            try:
                CIMProperty('Age', val)
            except TypeError:
                pass
            else:
                self.fail('TypeError not raised')

        # Arrays of CIM string and numeric types

        p = CIMProperty('Foo', None, 'string', is_array=True)
        self._assert_obj(p, 'Foo', None, 'string', is_array=True)

        p = CIMProperty('Foo', [], 'string')
        self._assert_obj(p, 'Foo', [], 'string', is_array=True)

        p = CIMProperty('Foo', [], 'string', is_array=True)
        self._assert_obj(p, 'Foo', [], 'string', is_array=True)

        p = CIMProperty('Foo', [None], 'string')
        self._assert_obj(p, 'Foo', [None], 'string', is_array=True)

        p = CIMProperty('Foo', [None], 'string', is_array=True)
        self._assert_obj(p, 'Foo', [None], 'string', is_array=True)

        p = CIMProperty('Foo', [Uint8(x) for x in [1, 2, 3]])
        self._assert_obj(p, 'Foo', [Uint8(x) for x in [1, 2, 3]],
                         'uint8', is_array=True)

        p = CIMProperty('Foo', [Uint8(x) for x in [1, 2, 3]], is_array=True)
        self._assert_obj(p, 'Foo', [Uint8(x) for x in [1, 2, 3]],
                         'uint8', is_array=True)

        p = CIMProperty('Foo', [Uint8(x) for x in [1, 2, 3]], type='uint8')
        self._assert_obj(p, 'Foo', [Uint8(x) for x in [1, 2, 3]],
                         'uint8', is_array=True)

        p = CIMProperty('Foo', [Uint8(x) for x in [1, 2, 3]], qualifiers=quals)
        self._assert_obj(p, 'Foo', [Uint8(x) for x in [1, 2, 3]],
                         'uint8', is_array=True, qualifiers=quals)

        # Arrays of CIM boolean type

        p = CIMProperty('Aged', [True])
        self._assert_obj(p, 'Aged', [True], 'boolean', is_array=True)

        p = CIMProperty('Aged', [False, True], 'boolean')
        self._assert_obj(p, 'Aged', [False, True], 'boolean', is_array=True)

        p = CIMProperty('Aged', [None], 'boolean')
        self._assert_obj(p, 'Aged', [None], 'boolean', is_array=True)

        p = CIMProperty('Aged', [], 'boolean')
        self._assert_obj(p, 'Aged', [], 'boolean', is_array=True)

        # Arrays of CIM datetime type

        timedelta_1 = timedelta(days=12345678, hours=22, minutes=44,
                                seconds=55, microseconds=654321)
        cim_datetime_1 = '12345678224455.654321:000'

        # This test failed in the old constructor implementation, because the
        # timedelta object was not converted to a CIMDateTime object.
        p = CIMProperty('Age', [timedelta_1])
        self._assert_obj(p, 'Age', [CIMDateTime(cim_datetime_1)], 'datetime',
                         is_array=True)
    
        # This test failed in the old constructor implementation, because the
        # timedelta object was not converted to a CIMDateTime object.
        p = CIMProperty('Age', [timedelta_1], 'datetime')
        self._assert_obj(p, 'Age', [CIMDateTime(cim_datetime_1)], 'datetime',
                         is_array=True)

        p = CIMProperty('Age', [CIMDateTime(timedelta_1)])
        self._assert_obj(p, 'Age', [CIMDateTime(cim_datetime_1)], 'datetime',
                         is_array=True)

        p = CIMProperty('Age', [CIMDateTime(timedelta_1)], 'datetime')
        self._assert_obj(p, 'Age', [CIMDateTime(cim_datetime_1)], 'datetime',
                         is_array=True)

        # This test failed in the old constructor implementation, because the
        # datetime formatted string was not converted to a CIMDateTime object.
        p = CIMProperty('Age', [cim_datetime_1], 'datetime')
        self._assert_obj(p, 'Age', [CIMDateTime(cim_datetime_1)], 'datetime',
                         is_array=True)

        p = CIMProperty('Age', [CIMDateTime(cim_datetime_1)])
        self._assert_obj(p, 'Age', [CIMDateTime(cim_datetime_1)], 'datetime',
                         is_array=True)

        p = CIMProperty('Age', [CIMDateTime(cim_datetime_1)], 'datetime')
        self._assert_obj(p, 'Age', [CIMDateTime(cim_datetime_1)], 'datetime',
                         is_array=True)

        p = CIMProperty('Age', [None], 'datetime')
        self._assert_obj(p, 'Age', [None], 'datetime', is_array=True)

        datetime_2 = datetime(year=2014, month=9, day=24, hour=19, minute=30,
                              second=40, microsecond=654321,
                              tzinfo=cim_types.MinutesFromUTC(120))
        cim_datetime_2 = '20140924193040.654321+120'

        # This test failed in the old constructor implementation, because the
        # datetime object was not converted to a CIMDateTime object.
        p = CIMProperty('Age', [datetime_2])
        self._assert_obj(p, 'Age', [CIMDateTime(cim_datetime_2)], 'datetime',
                         is_array=True)

        # This test failed in the old constructor implementation, because the
        # datetime object was not converted to a CIMDateTime object.
        p = CIMProperty('Age', [datetime_2], 'datetime')
        self._assert_obj(p, 'Age', [CIMDateTime(cim_datetime_2)], 'datetime',
                         is_array=True)

        p = CIMProperty('Age', [CIMDateTime(datetime_2)])
        self._assert_obj(p, 'Age', [CIMDateTime(cim_datetime_2)], 'datetime',
                         is_array=True)

        p = CIMProperty('Age', [CIMDateTime(datetime_2)], 'datetime')
        self._assert_obj(p, 'Age', [CIMDateTime(cim_datetime_2)], 'datetime',
                         is_array=True)

        # This test failed in the old constructor implementation, because the
        # datetime formatted string was not converted to a CIMDateTime object.
        p = CIMProperty('Age', [cim_datetime_2], 'datetime')
        self._assert_obj(p, 'Age', [CIMDateTime(cim_datetime_2)], 'datetime',
                         is_array=True)

        p = CIMProperty('Age', [CIMDateTime(cim_datetime_2)])
        self._assert_obj(p, 'Age', [CIMDateTime(cim_datetime_2)], 'datetime',
                         is_array=True)

        p = CIMProperty('Age', [CIMDateTime(cim_datetime_2)], 'datetime')
        self._assert_obj(p, 'Age', [CIMDateTime(cim_datetime_2)], 'datetime',
                         is_array=True)

        # Arrays of reference properties are not allowed in CIM v2.

        # Arrays of CIM embedded objects / instances

        # This test failed in the old constructor implementation, because the
        # first array element was used for defaulting the type, without
        # checking for None.
        p = CIMProperty('Bar', [None], embedded_object='object')
        self._assert_obj(p, 'Bar', [None], 'string', embedded_object='object',
                         is_array=True)

        p = CIMProperty('Bar', [None], 'string', embedded_object='object')
        self._assert_obj(p, 'Bar', [None], 'string', embedded_object='object',
                         is_array=True)

        # This test failed in the old constructor implementation, because the
        # type of the empty array could not be defaulted from the
        # embedded_object argument.
        p = CIMProperty('Bar', [], embedded_object='object')
        self._assert_obj(p, 'Bar', [], 'string', embedded_object='object',
                         is_array=True)

        p = CIMProperty('Bar', [], 'string', embedded_object='object')
        self._assert_obj(p, 'Bar', [], 'string', embedded_object='object',
                         is_array=True)

        ec = CIMClass('CIM_Bar')

        p = CIMProperty('Bar', [ec])
        self._assert_obj(p, 'Bar', [ec], 'string', embedded_object='object',
                         is_array=True)

        # This test failed in the old constructor implementation, because the
        # embedded_object attribute was not implied from the value argument if
        # the type argument was also provided.
        p = CIMProperty('Bar', [ec], 'string')
        self._assert_obj(p, 'Bar', [ec], 'string', embedded_object='object',
                         is_array=True)

        p = CIMProperty('Bar', [ec], embedded_object='object')
        self._assert_obj(p, 'Bar', [ec], 'string', embedded_object='object',
                         is_array=True)

        p = CIMProperty('Bar', [ec], 'string', embedded_object='object')
        self._assert_obj(p, 'Bar', [ec], 'string', embedded_object='object',
                         is_array=True)

        ei = CIMInstance('CIM_Bar')

        # This test failed in the old constructor implementation, because the
        # embedded_object argument value of 'object' was changed to 'instance'
        # when a CIMInstance typed value was provided.
        p = CIMProperty('Bar', [ei], embedded_object='object')
        self._assert_obj(p, 'Bar', [ei], 'string', embedded_object='object',
                         is_array=True)

        p = CIMProperty('Bar', [ei], 'string', embedded_object='object')
        self._assert_obj(p, 'Bar', [ei], 'string', embedded_object='object',
                         is_array=True)

        p = CIMProperty('Bar', [ei])
        self._assert_obj(p, 'Bar', [ei], 'string', embedded_object='instance',
                         is_array=True)

        # This test failed in the old constructor implementation, because the
        # embedded_object attribute was not implied from the value argument if
        # the type argument was also provided.
        p = CIMProperty('Bar', [ei], 'string')
        self._assert_obj(p, 'Bar', [ei], 'string', embedded_object='instance',
                         is_array=True)

        p = CIMProperty('Bar', [ei], embedded_object='instance')
        self._assert_obj(p, 'Bar', [ei], 'string', embedded_object='instance',
                         is_array=True)

        p = CIMProperty('Bar', [ei], 'string', embedded_object='instance')
        self._assert_obj(p, 'Bar', [ei], 'string', embedded_object='instance',
                         is_array=True)

        # Check that initialization with array being Null, array being empty,
        # or first array element being Null without specifying a type is
        # rejected

        for val in [None, [], [None], [None, "abc"]]:

            try:
                CIMProperty('Foo', val, is_array=True)
            except (ValueError, TypeError):
                pass
            else:
                self.fail('ValueError or TypeError not raised')

        for val in [[], [None], [None, "abc"]]:

            try:
                CIMProperty('Foo', val)
            except (ValueError, TypeError):
                pass
            else:
                self.fail('ValueError or TypeError not raised')

        # Check that initialization of array elements with Python integer and
        # floating point values without specifying a type is rejected

        for val in [[1, 2, 3], [1.0, 2.0]]:
            try:
                CIMProperty('Foo', val)
            except (ValueError, TypeError):
                pass
            else:
                self.fail('ValueError or TypeError not raised')

class CopyCIMProperty(_CIMPropertyTestCase):

    def runtest(self):

        p = CIMProperty('Spotty', 'Foot')
        c = p.copy()

        self.assert_equal(p, c)

        c.name = '1234'
        c.value = '1234'
        c.qualifiers = {'Key': CIMQualifier('Value', True)}

        self._assert_obj(p, 'Spotty', 'Foot', type='string', qualifiers={})

class CIMPropertyAttrs(_CIMPropertyTestCase):

    def runtest(self):

        # Attributes for single-valued property

        obj = CIMProperty('Spotty', 'Foot')
        self._assert_obj(obj, 'Spotty', 'Foot', type='string')

        # Attributes for array property

        v = [Uint8(x) for x in [1, 2, 3]]
        obj = CIMProperty('Foo', v)
        self._assert_obj(obj, 'Foo', v, type='uint8', is_array=True)

        # Attributes for property reference

        # This test failed in the old constructor implementation, because the
        # reference_class argument was required to be provided for references.
        v = CIMInstanceName('CIM_Bar')
        obj = CIMProperty('Foo', v)
        self._assert_obj(obj, 'Foo', v, type='reference',
                         reference_class='CIM_Bar')

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
                                         qualifiers={'Key':
                                                     CIMQualifier('Key',
                                                                  True)}))

        # Compare property arrays

        self.assert_equal(
            CIMProperty('Array', None, 'uint8', is_array=True),
            CIMProperty('array', None, 'uint8', is_array=True))

        self.assert_equal(
            CIMProperty('Array', [Uint8(x) for x in [1, 2, 3]]),
            CIMProperty('Array', [Uint8(x) for x in [1, 2, 3]]))

        self.assert_notequal(
            CIMProperty('Array', [Uint8(x) for x in [1, 2, 3]]),
            CIMProperty('Array', [Uint16(x) for x in [1, 2, 3]]))

        self.assert_notequal(
            CIMProperty('Array', [Uint8(x) for x in [1, 2, 3]]),
            CIMProperty('Array', [Uint16(x) for x in [1, 2, 3]],
                        qualifiers={'Key': CIMQualifier('Key', True)}))

        # Compare property references

        self.assert_equal(
            CIMProperty('Foo', CIMInstanceName('CIM_Foo')),
            CIMProperty('Foo', CIMInstanceName('CIM_Foo')))

        self.assert_equal(
            CIMProperty('Foo', CIMInstanceName('CIM_Foo')),
            CIMProperty('foo', CIMInstanceName('CIM_Foo')))

        self.assert_notequal(
            CIMProperty('Foo', CIMInstanceName('CIM_Foo')),
            CIMProperty('foo', None, type='reference'))

        self.assert_notequal(
            CIMProperty('Foo', CIMInstanceName('CIM_Foo')),
            CIMProperty('Foo', CIMInstanceName('CIM_Foo'),
                        qualifiers={'Key': CIMQualifier('Key', True)}))

class CIMPropertyCompare(TestCase):

    def runtest(self):
        raise NotRunError("unimplemented")

class CIMPropertySort(TestCase):

    def runtest(self):
        raise NotRunError("unimplemented")

class CIMPropertyString(TestCase):

    def runtest(self):

        r = repr(CIMProperty('Spotty', 'Foot', type='string'))

        self.assert_re_match('^CIMProperty', r)

class CIMPropertyToXML(ValidateTest):
    """Test valid XML is generated for various CIMProperty objects."""

    def runtest(self):

        # XML root elements for CIM-XML representations of CIMProperty
        root_elem_CIMProperty_single = 'PROPERTY'
        root_elem_CIMProperty_array = 'PROPERTY.ARRAY'
        root_elem_CIMProperty_ref = 'PROPERTY.REFERENCE'

        # Single-valued ordinary properties

        self.validate(CIMProperty('Spotty', None, type='string'),
                      root_elem_CIMProperty_single)

        self.validate(CIMProperty(u'Name', u'Brad'),
                      root_elem_CIMProperty_single)

        self.validate(CIMProperty('Age', Uint16(32)),
                      root_elem_CIMProperty_single)

        self.validate(CIMProperty('Age', Uint16(32),
                                  qualifiers={'Key':
                                              CIMQualifier('Key', True)}),
                      root_elem_CIMProperty_single)

        # Array properties

        self.validate(CIMProperty('Foo', None, 'string', is_array=True),
                      root_elem_CIMProperty_array)

        self.validate(CIMProperty('Foo', [], 'string'),
                      root_elem_CIMProperty_array)

        self.validate(CIMProperty('Foo', [Uint8(x) for x in [1, 2, 3]]),
                      root_elem_CIMProperty_array)

        self.validate(CIMProperty('Foo', [Uint8(x) for x in [1, 2, 3]],
                                  qualifiers={'Key': CIMQualifier('Key',
                                                                  True)}),
                      root_elem_CIMProperty_array)

        # Reference properties

        self.validate(CIMProperty('Foo', None, type='reference'),
                      root_elem_CIMProperty_ref)

        self.validate(CIMProperty('Foo', CIMInstanceName('CIM_Foo')),
                      root_elem_CIMProperty_ref)

        self.validate(CIMProperty('Foo',
                                  CIMInstanceName('CIM_Foo'),
                                  qualifiers={'Key': CIMQualifier('Key',
                                                                  True)}),
                      root_elem_CIMProperty_ref)

###############################################################################
# CIMQualifier
###############################################################################

class InitCIMQualifier(TestCase):
    """Test initialising a CIMQualifier object."""

    def runtest(self):

        CIMQualifier('Revision', '2.7.0', 'string')
        CIMQualifier('RevisionList', ['1', '2', '3'], propagated=False)
        CIMQualifier('Null', None, 'string')

class CopyCIMQualifier(TestCase):

    def runtest(self):

        q = CIMQualifier('Revision', '2.7.0', 'string')
        c = q.copy()

        self.assert_equal(q, c)

        c.name = 'Fooble'
        c.value = 'eep'

        self.assert_equal(q.name, 'Revision')

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
                         propagated=False)

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

        self.assert_notequal(CIMQualifier('Null', None, type='string'),
                             CIMQualifier('Null', ''))

class CIMQualifierCompare(TestCase):

    def runtest(self):
        raise NotRunError("unimplemented")

class CIMQualifierSort(TestCase):

    def runtest(self):
        raise NotRunError("unimplemented")

class CIMQualifierString(TestCase):

    def runtest(self):

        s = str(CIMQualifier('RevisionList', ['1', '2', '3'],
                             propagated=False))

        self.assert_re_search('RevisionList', s)

class CIMQualifierToXML(ValidateTest):

    def runtest(self):

        # XML root elements for CIM-XML representations of CIMQualifier
        root_elem_CIMQualifier = 'QUALIFIER'

        self.validate(CIMQualifier('Spotty', 'Foot'),
                      root_elem_CIMQualifier)

        self.validate(CIMQualifier('Revision', Real32(2.7)),
                      root_elem_CIMQualifier)

        self.validate(CIMQualifier('RevisionList',
                                   [Uint16(x) for x in 1, 2, 3],
                                   propagated=False),
                      root_elem_CIMQualifier)

###############################################################################
# CIMClassName
###############################################################################

# TODO Add testcases for CIMClassName

###############################################################################
# CIMClass
###############################################################################

class InitCIMClass(TestCase):

    def runtest(self):

        # Initialise with classname, superclass

        CIMClass('CIM_Foo')
        CIMClass('CIM_Foo', superclass='CIM_Bar')

        # Initialise with properties

        CIMClass('CIM_Foo', properties={'InstanceID':
                                        CIMProperty('InstanceID', None,
                                                    type='string')})

        # Initialise with methods

        CIMClass('CIM_Foo', methods={'Delete': CIMMethod('Delete')})

        # Initialise with qualifiers

        CIMClass('CIM_Foo', qualifiers={'Key': CIMQualifier('Key', True)})

class CopyCIMClass(TestCase):

    def runtest(self):

        c = CIMClass('CIM_Foo',
                     methods={'Delete': CIMMethod('Delete')},
                     qualifiers={'Key': CIMQualifier('Value', True)})

        co = c.copy()

        self.assert_equal(c, co)

        co.classname = 'CIM_Bar'
        del co.methods['Delete']
        del co.qualifiers['Key']

        self.assert_equal(c.classname, 'CIM_Foo')
        self.assert_(c.methods['Delete'])
        self.assert_(c.qualifiers['Key'])

class CIMClassAttrs(TestCase):

    def runtest(self):

        obj = CIMClass('CIM_Foo', superclass='CIM_Bar')

        self.assert_equal(obj.classname, 'CIM_Foo')
        self.assert_equal(obj.superclass, 'CIM_Bar')
        self.assert_equal(obj.properties, {})
        self.assert_equal(obj.qualifiers, {})
        self.assert_equal(obj.methods, {})
        self.assert_equal(obj.qualifiers, {})

class CIMClassEquality(TestCase):

    def runtest(self):

        self.assert_equal(CIMClass('CIM_Foo'), CIMClass('CIM_Foo'))
        self.assert_equal(CIMClass('CIM_Foo'), CIMClass('cim_foo'))

        self.assert_notequal(CIMClass('CIM_Foo', superclass='CIM_Bar'),
                             CIMClass('CIM_Foo'))

        properties = {'InstanceID':
                      CIMProperty('InstanceID', None,
                                  type='string')}

        methods = {'Delete': CIMMethod('Delete')}

        qualifiers = {'Key': CIMQualifier('Key', True)}

        self.assert_notequal(CIMClass('CIM_Foo'),
                             CIMClass('CIM_Foo', properties=properties))

        self.assert_notequal(CIMClass('CIM_Foo'),
                             CIMClass('CIM_Foo', methods=methods))

        self.assert_notequal(CIMClass('CIM_Foo'),
                             CIMClass('CIM_Foo', qualifiers=qualifiers))

        self.assert_equal(CIMClass('CIM_Foo', superclass='CIM_Bar'),
                          CIMClass('CIM_Foo', superclass='cim_bar'))

class CIMClassCompare(TestCase):

    def runtest(self):
        raise NotRunError("unimplemented")

class CIMClassSort(TestCase):

    def runtest(self):
        raise NotRunError("unimplemented")

class CIMClassString(TestCase):

    def runtest(self):

        s = str(CIMClass('CIM_Foo'))
        self.assert_re_search('CIM_Foo', s)

class CIMClassToXML(ValidateTest):

    def runtest(self):

        # XML root elements for CIM-XML representations of CIMClass
        root_elem_CIMClass = 'CLASS'

        self.validate(CIMClass('CIM_Foo'),
                      root_elem_CIMClass)

        self.validate(CIMClass('CIM_Foo', superclass='CIM_Bar'),
                      root_elem_CIMClass)

        self.validate(CIMClass('CIM_Foo',
                               properties={'InstanceID':
                                           CIMProperty('InstanceID', None,
                                                       type='string')}),
                      root_elem_CIMClass)

        self.validate(CIMClass('CIM_Foo',
                               methods={'Delete': CIMMethod('Delete')}),
                      root_elem_CIMClass)

        self.validate(CIMClass('CIM_Foo',
                               qualifiers={'Key': CIMQualifier('Key', True)}),
                      root_elem_CIMClass)

class CIMClassToMOF(TestCase):

    def runtest(self):

        c = CIMClass(
            'CIM_Foo',
            properties={'InstanceID': CIMProperty('InstanceID', None,
                                                  type='string')})

        c.tomof()

###############################################################################
# CIMMethod
###############################################################################

class InitCIMMethod(TestCase):

    def runtest(self):

        CIMMethod('FooMethod', 'uint32')

        CIMMethod('FooMethod', 'uint32',
                  parameters={'Param1': CIMParameter('Param1', 'uint32'),
                              'Param2': CIMParameter('Param2', 'string')})

        CIMMethod('FooMethod', 'uint32',
                  parameters={'Param1': CIMParameter('Param1', 'uint32'),
                              'Param2': CIMParameter('Param2', 'string')},
                  qualifiers={'Key': CIMQualifier('Key', True)})

class CopyCIMMethod(TestCase):

    def runtest(self):

        m = CIMMethod('FooMethod', 'uint32',
                      parameters={'P1': CIMParameter('P1', 'uint32'),
                                  'P2': CIMParameter('P2', 'string')},
                      qualifiers={'Key': CIMQualifier('Key', True)})

        c = m.copy()

        self.assert_equal(m, c)

        c.name = 'BarMethod'
        c.return_type = 'string'
        del c.parameters['P1']
        del c.qualifiers['Key']

        self.assert_equal(m.name, 'FooMethod')
        self.assert_equal(m.return_type, 'uint32')
        self.assert_(m.parameters['P1'])
        self.assert_(m.qualifiers['Key'])

class CIMMethodAttrs(TestCase):

    def runtest(self):

        m = CIMMethod('FooMethod', 'uint32',
                      parameters={'Param1': CIMParameter('Param1', 'uint32'),
                                  'Param2': CIMParameter('Param2', 'string')})

        self.assert_equal(m.name, 'FooMethod')
        self.assert_equal(m.return_type, 'uint32')
        self.assert_equal(len(m.parameters), 2)
        self.assert_equal(m.qualifiers, {})

class CIMMethodEquality(TestCase):

    def runtest(self):

        self.assert_equal(CIMMethod('FooMethod', 'uint32'),
                          CIMMethod('FooMethod', 'uint32'))

        self.assert_equal(CIMMethod('FooMethod', 'uint32'),
                          CIMMethod('fooMethod', 'uint32'))

        self.assert_notequal(CIMMethod('FooMethod', 'uint32'),
                             CIMMethod('FooMethod', 'uint32',
                                       qualifiers={'Key': CIMQualifier('Key',
                                                                       True)}))

class CIMMethodCompare(TestCase):

    def runtest(self):
        raise NotRunError("unimplemented")

class CIMMethodSort(TestCase):

    def runtest(self):
        raise NotRunError("unimplemented")

class CIMMethodString(TestCase):

    def runtest(self):

        s = str(CIMMethod('FooMethod', 'uint32'))

        self.assert_re_search('FooMethod', s)
        self.assert_re_search('uint32', s)

class CIMMethodToXML(ValidateTest):

    def runtest(self):

        # XML root elements for CIM-XML representations of CIMMethod
        root_elem_CIMMethod = 'METHOD'

        self.validate(CIMMethod('FooMethod', 'uint32'),
                      root_elem_CIMMethod)

        self.validate(
            CIMMethod('FooMethod', 'uint32',
                      parameters={'Param1': CIMParameter('Param1', 'uint32'),
                                  'Param2': CIMParameter('Param2', 'string')},
                      qualifiers={'Key': CIMQualifier('Key', True)}),
            root_elem_CIMMethod)

###############################################################################
# CIMParameter
###############################################################################

class InitCIMParameter(TestCase):

    def runtest(self):

        # Single-valued parameters

        CIMParameter('Param1', 'uint32')
        CIMParameter('Param2', 'string')
        CIMParameter('Param2', 'string',
                     qualifiers={'Key': CIMQualifier('Key', True)})

        # Array parameters

        CIMParameter('ArrayParam', 'uint32', is_array=True)
        CIMParameter('ArrayParam', 'uint32', is_array=True, array_size=10)
        CIMParameter('ArrayParam', 'uint32', is_array=True, array_size=10,
                     qualifiers={'Key': CIMQualifier('Key', True)})

        # Reference parameters

        CIMParameter('RefParam', 'reference', reference_class='CIM_Foo')
        CIMParameter('RefParam', 'reference', reference_class='CIM_Foo',
                     qualifiers={'Key': CIMQualifier('Key', True)})

        # Refarray parameters

        CIMParameter('RefArrayParam', 'reference', is_array=True)
        CIMParameter('RefArrayParam', 'reference', reference_class='CIM_Foo',
                     is_array=True)
        CIMParameter('RefArrayParam', 'reference', is_array=True,
                     reference_class='CIM_Foo', array_size=10)
        CIMParameter('RefArrayParam', 'reference', is_array=True,
                     reference_class='CIM_Foo', array_size=10,
                     qualifiers={'Key': CIMQualifier('Key', True)})

class CopyCIMParameter(TestCase):

    def runtest(self):

        p = CIMParameter('RefParam', 'reference',
                         reference_class='CIM_Foo',
                         qualifiers={'Key': CIMQualifier('Key', True)})

        c = p.copy()

        self.assert_equal(p, c)

        c.name = 'Fooble'
        c.type = 'string'
        c.reference_class = None
        del c.qualifiers['Key']

        self.assert_equal(p.name, 'RefParam')
        self.assert_equal(p.type, 'reference')
        self.assert_equal(p.reference_class, 'CIM_Foo')
        self.assert_(p.qualifiers['Key'])

class CIMParameterAttrs(TestCase):

    def runtest(self):

        # Single-valued parameters

        p = CIMParameter('Param1', 'string')

        self.assert_equal(p.name, 'Param1')
        self.assert_equal(p.type, 'string')
        self.assert_equal(p.qualifiers, {})

        # Array parameters

        p = CIMParameter('ArrayParam', 'uint32', is_array=True)

        self.assert_equal(p.name, 'ArrayParam')
        self.assert_equal(p.type, 'uint32')
        self.assert_equal(p.array_size, None)
        self.assert_equal(p.qualifiers, {})

        # Reference parameters

        p = CIMParameter('RefParam', 'reference', reference_class='CIM_Foo')

        self.assert_equal(p.name, 'RefParam')
        self.assert_equal(p.reference_class, 'CIM_Foo')
        self.assert_equal(p.qualifiers, {})

        # Reference array parameters

        p = CIMParameter('RefArrayParam', 'reference',
                         reference_class='CIM_Foo', is_array=True,
                         array_size=10)

        self.assert_equal(p.name, 'RefArrayParam')
        self.assert_equal(p.reference_class, 'CIM_Foo')
        self.assert_equal(p.array_size, 10)
        self.assert_equal(p.is_array, True)
        self.assert_equal(p.qualifiers, {})

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
                                          qualifiers={'Key':
                                                      CIMQualifier('Key',
                                                                   True)}))

        # Array parameters

        self.assert_equal(
            CIMParameter('ArrayParam', 'uint32', is_array=True),
            CIMParameter('ArrayParam', 'uint32', is_array=True))

        self.assert_equal(
            CIMParameter('ArrayParam', 'uint32', is_array=True),
            CIMParameter('arrayParam', 'uint32', is_array=True))

        self.assert_notequal(
            CIMParameter('ArrayParam', 'uint32', is_array=True),
            CIMParameter('ArrayParam', 'string', is_array=True))

        self.assert_notequal(
            CIMParameter('ArrayParam', 'uint32', is_array=True),
            CIMParameter('ArrayParam', 'string', is_array=True,
                         array_size=10))

        self.assert_notequal(
            CIMParameter('ArrayParam', 'uint32', is_array=True),
            CIMParameter('ArrayParam', 'uint32', is_array=True,
                         qualifiers={'Key': CIMQualifier('Key', True)}))

        # Reference parameters

        self.assert_equal(CIMParameter('RefParam', 'reference',
                                       reference_class='CIM_Foo'),
                          CIMParameter('RefParam', 'reference',
                                       reference_class='CIM_Foo'))

        self.assert_equal(CIMParameter('RefParam', 'reference',
                                       reference_class='CIM_Foo'),
                          CIMParameter('refParam', 'reference',
                                       reference_class='CIM_Foo'))

        self.assert_equal(CIMParameter('RefParam', 'reference',
                                       reference_class='CIM_Foo'),
                          CIMParameter('refParam', 'reference',
                                       reference_class='CIM_foo'))

        self.assert_notequal(CIMParameter('RefParam', 'reference',
                                          reference_class='CIM_Foo'),
                             CIMParameter('RefParam', 'reference',
                                          reference_class='CIM_Bar'))

        self.assert_notequal(CIMParameter('RefParam', 'reference',
                                          reference_class='CIM_Foo'),
                             CIMParameter('RefParam', 'reference',
                                          reference_class='CIM_Foo',
                                          qualifiers=
                                          {'Key': CIMQualifier('Key', True)}))

        # Reference array parameters

        self.assert_equal(CIMParameter('ArrayParam', 'reference',
                                       reference_class='CIM_Foo',
                                       is_array=True),
                          CIMParameter('ArrayParam', 'reference',
                                       reference_class='CIM_Foo',
                                       is_array=True))

        self.assert_equal(CIMParameter('ArrayParam', 'reference',
                                       reference_class='CIM_Foo',
                                       is_array=True),
                          CIMParameter('arrayparam', 'reference',
                                       reference_class='CIM_Foo',
                                       is_array=True))

        self.assert_notequal(CIMParameter('ArrayParam', 'reference',
                                          reference_class='CIM_Foo',
                                          is_array=True),
                             CIMParameter('arrayParam', 'reference',
                                          reference_class='CIM_foo',
                                          is_array=True,
                                          array_size=10))

        self.assert_notequal(CIMParameter('ArrayParam', 'reference',
                                          reference_class='CIM_Foo',
                                          is_array=True),
                             CIMParameter('ArrayParam', 'reference',
                                          reference_class='CIM_Foo',
                                          is_array=True,
                                          qualifiers={'Key':
                                                      CIMQualifier('Key',
                                                                   True)}))

class CIMParameterCompare(TestCase):

    def runtest(self):
        raise NotRunError("unimplemented")

class CIMParameterSort(TestCase):

    def runtest(self):
        raise NotRunError("unimplemented")

class CIMParameterString(TestCase):

    def runtest(self):

        s = str(CIMParameter('Param1', 'uint32'))

        self.assert_re_search('Param1', s)
        self.assert_re_search('uint32', s)

class CIMParameterToXML(ValidateTest):

    def runtest(self):

        # XML root elements for CIM-XML representations of CIMParameter
        root_elem_CIMParameter_single = 'PARAMETER'
        root_elem_CIMParameter_array = 'PARAMETER.ARRAY'
        root_elem_CIMParameter_ref = 'PARAMETER.REFERENCE'
        root_elem_CIMParameter_refarray = 'PARAMETER.REFARRAY'

        # Single-valued parameters

        self.validate(CIMParameter('Param1', 'uint32'),
                      root_elem_CIMParameter_single)

        self.validate(CIMParameter('Param1', 'string',
                                   qualifiers={'Key': CIMQualifier('Key',
                                                                   True)}),
                      root_elem_CIMParameter_single)

        # Array parameters

        self.validate(CIMParameter('ArrayParam', 'uint32', is_array=True),
                      root_elem_CIMParameter_array)

        self.validate(CIMParameter('ArrayParam', 'uint32', is_array=True,
                                   array_size=10),
                      root_elem_CIMParameter_array)

        self.validate(CIMParameter('ArrayParam', 'uint32', is_array=True,
                                   array_size=10,
                                   qualifiers={'Key': CIMQualifier('Key',
                                                                   True)}),
                      root_elem_CIMParameter_array)

        # Reference parameters

        self.validate(CIMParameter('RefParam', 'reference',
                                   reference_class='CIM_Foo',
                                   qualifiers={'Key':
                                               CIMQualifier('Key', True)}),
                      root_elem_CIMParameter_ref)

        # Reference array parameters

        self.validate(CIMParameter('RefArrayParam', 'reference',
                                   is_array=True),
                      root_elem_CIMParameter_refarray)

        self.validate(CIMParameter('RefArrayParam', 'reference',
                                   reference_class='CIM_Foo',
                                   is_array=True),
                      root_elem_CIMParameter_refarray)

        self.validate(CIMParameter('RefArrayParam', 'reference',
                                   reference_class='CIM_Foo',
                                   is_array=True,
                                   array_size=10),
                      root_elem_CIMParameter_refarray)

        self.validate(CIMParameter('RefArrayParam', 'reference',
                                   reference_class='CIM_Foo',
                                   is_array=True,
                                   qualifiers={'Key':
                                               CIMQualifier('Key', True)}),
                      root_elem_CIMParameter_refarray)

###############################################################################
# CIMQualifierDeclaration
###############################################################################

class InitCIMQualifierDeclaration(TestCase):
    pass

class CopyCIMQualifierDeclaration(TestCase):
    pass

class CIMQualifierDeclarationAttrs(TestCase):
    pass

class CIMQualifierDeclarationEquality(TestCase):
    # pylint: disable=invalid-name
    pass

class CIMQualifierDeclarationCompare(TestCase):
    # pylint: disable=invalid-name
    pass

class CIMQualifierDeclarationSort(TestCase):
    pass

class CIMQualifierDeclarationString(TestCase):
    pass

class CIMQualifierDeclarationToXML(TestCase):
    pass

###############################################################################
# ToCIMObj
###############################################################################

class ToCIMObj(TestCase):

    def runtest(self):
        path = cim_obj.tocimobj(
            'reference',
            "Acme_OS.Name=\"acmeunit\",SystemName=\"UnixHost\"")
        self.assert_(isinstance(path, CIMInstanceName))
        self.assert_equal(path.classname, 'Acme_OS')
        self.assert_equal(path['Name'], 'acmeunit')
        self.assert_equal(path['SystemName'], 'UnixHost')
        self.assert_equal(len(path.keybindings), 2)
        self.assert_(path.namespace is None)
        self.assert_(path.host is None)

        path = cim_obj.tocimobj(
            'reference',
            "Acme_User.uid=33,OSName=\"acmeunit\"," \
            "SystemName=\"UnixHost\"")
        self.assert_(isinstance(path, CIMInstanceName))
        self.assert_(path.namespace is None)
        self.assert_(path.host is None)
        self.assert_equal(path.classname, 'Acme_User')
        self.assert_equal(path['uid'], 33)
        self.assert_equal(path['OSName'], 'acmeunit')
        self.assert_equal(path['SystemName'], 'UnixHost')
        self.assert_equal(len(path.keybindings), 3)

        path = cim_obj.tocimobj(
            'reference',
            'HTTP://CIMOM_host/root/CIMV2:CIM_Disk.key1="value1"')
        self.assert_(isinstance(path, CIMInstanceName))
        self.assert_equal(path.namespace, 'root/CIMV2')
        self.assert_equal(path.host, 'CIMOM_host')
        self.assert_equal(path.classname, 'CIM_Disk')
        self.assert_equal(path['key1'], 'value1')
        self.assert_equal(len(path.keybindings), 1)

        path = cim_obj.tocimobj(
            'reference',
            "ex_sampleClass.label1=9921,label2=8821")
        self.assert_(isinstance(path, CIMInstanceName))
        self.assert_(path.namespace is None)
        self.assert_(path.host is None)
        self.assert_equal(path.classname, 'ex_sampleClass')
        self.assert_equal(path['label1'], 9921)
        self.assert_equal(path['label2'], 8821)
        self.assert_equal(len(path.keybindings), 2)

        path = cim_obj.tocimobj('reference', "ex_sampleClass")
        self.assert_(isinstance(path, CIMClassName))
        self.assert_(path.namespace is None)
        self.assert_(path.host is None)
        self.assert_equal(path.classname, 'ex_sampleClass')

        path = cim_obj.tocimobj(
            'reference',
            '//./root/default:LogicalDisk.SystemName="acme",' \
            'LogicalDisk.Drive="C"')
        self.assert_(isinstance(path, CIMInstanceName))
        self.assert_equal(path.namespace, 'root/default')
        self.assert_equal(path.host, '.')
        self.assert_equal(path.classname, 'LogicalDisk')
        self.assert_equal(path['SystemName'], 'acme')
        self.assert_equal(path['Drive'], 'C')
        self.assert_equal(len(path.keybindings), 2)

        path = cim_obj.tocimobj(
            'reference',
            "X.key1=\"John Smith\",key2=33.3")
        self.assert_(isinstance(path, CIMInstanceName))
        self.assert_(path.namespace is None)
        self.assert_(path.host is None)
        self.assert_equal(path.classname, 'X')
        self.assert_equal(path['key1'], 'John Smith')
        self.assert_equal(path['key2'], 33.3)


        path = cim_obj.tocimobj(
            'reference',
            "//./root/default:NetworkCard=2")
        # TODO How should pywbem deal with a single, unnamed, keybinding?
        #self.assert_(isinstance(path, CIMInstanceName))
        #self.assert_equal(path.namespace, 'root/default')
        #self.assert_equal(path.host, '.')
        #self.assert_equal(path.classname, 'NetworkCard')

#################################################################
# MofStr - test cases for mofstr()
#################################################################

class MofStr(TestCase):

    def runtest_single(self, in_value, exp_value):    
        '''
        Test function for single invocation of mofstr()
        '''

        ret_value = cim_obj.mofstr(in_value)

        self.assert_equal(ret_value, exp_value)

    def runtest(self):
        '''
        Run all tests for mofstr().
        '''

        self.runtest_single('',       '""')
        self.runtest_single('\\',     '"\\\\"')
        self.runtest_single('"',      '"\\""')
        self.runtest_single('a"b',    '"a\\"b"')
        # TODO: Enable the following test, once "" is supported.
        #self.runtest_single('a""b',   '"a\\"\\"b"')
        self.runtest_single("'",      '"\'"')
        self.runtest_single("a'b",    '"a\'b"')
        self.runtest_single("a''b",   '"a\'\'b"')
        self.runtest_single("\\'",    '"\\\'"')
        self.runtest_single('\\"',    '"\\""')
        self.runtest_single('\r\n\t\b\f', '"\\r\\n\\t\\b\\f"')
        self.runtest_single('\\r\\n\\t\\b\\f', '"\\r\\n\\t\\b\\f"')
        self.runtest_single('\\_\\+\\v\\h\\j', '"\\_\\+\\v\\h\\j"')
        self.runtest_single('a',      '"a"')
        self.runtest_single('a b',    '"a b"')
        self.runtest_single(' b',     '" b"')
        self.runtest_single('a ',     '"a "')
        self.runtest_single(' ',      '" "')

        #                    |0                                                                     |71
        self.runtest_single('the big brown fox jumps over a big brown fox jumps over a big brown f jumps over a big brown fox',\
                           '"the big brown fox jumps over a big brown fox jumps over a big brown f "\n       '+\
                           '"jumps over a big brown fox"')
        self.runtest_single('the big brown fox jumps over a big brown fox jumps over a big brown fo jumps over a big brown fox',\
                           '"the big brown fox jumps over a big brown fox jumps over a big brown fo "\n       '+\
                           '"jumps over a big brown fox"')
        self.runtest_single('the big brown fox jumps over a big brown fox jumps over a big brown fox jumps over a big brown fox',\
                           '"the big brown fox jumps over a big brown fox jumps over a big brown "\n       '+\
                           '"fox jumps over a big brown fox"')
        self.runtest_single('the big brown fox jumps over a big brown fox jumps over a big brown foxx jumps over a big brown fox',\
                           '"the big brown fox jumps over a big brown fox jumps over a big brown "\n       '+\
                           '"foxx jumps over a big brown fox"')
        self.runtest_single('the big brown fox jumps over a big brown fox jumps over a big brown foxxx jumps over a big brown fox',\
                           '"the big brown fox jumps over a big brown fox jumps over a big brown "\n       '+\
                           '"foxxx jumps over a big brown fox"')
        self.runtest_single('the_big_brown_fox_jumps_over_a_big_brown_fox_jumps_over_a_big_brown_fox_jumps_over a big brown fox',\
                           '"the_big_brown_fox_jumps_over_a_big_brown_fox_jumps_over_a_big_brown_fox"\n       '+\
                           '"_jumps_over a big brown fox"')
        self.runtest_single('the big brown fox jumps over a big brown fox jumps over a big brown fox_jumps_over_a_big_brown_fox',\
                           '"the big brown fox jumps over a big brown fox jumps over a big brown "\n       '+\
                           '"fox_jumps_over_a_big_brown_fox"')

        return 0


###############################################################################
# Main function
###############################################################################

tests = [ # pylint: disable=invalid-name

    ###########################################################################
    # Property and qualifier classes
    ###########################################################################

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

    ###########################################################################
    # Instance and instance name classes
    ###########################################################################

    # CIMInstanceName

    InitCIMInstanceName,
    CopyCIMInstanceName,
    CIMInstanceNameAttrs,
    CIMInstanceNameDict,
    CIMInstanceNameEquality,
    CIMInstanceNameCompare,
    CIMInstanceNameSort,
    CIMInstanceNameString,
    CIMInstanceNameToXML,

    # CIMInstance

    InitCIMInstance,
    CopyCIMInstance,
    CIMInstanceAttrs,
    CIMInstanceDict,
    CIMInstanceEquality,
    CIMInstanceCompare,
    CIMInstanceSort,
    CIMInstanceString,
    CIMInstanceToXML,
    CIMInstanceToMOF,
    CIMInstanceUpdateExisting,
    CIMInstanceUpdatePath,
    CIMInstancePropertyList,

    ###########################################################################
    # Schema classes
    ###########################################################################

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

    # TODO Invoke tests for CIMClassName, once written

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

    # Others
    ToCIMObj,
    MofStr,

    ]

# Determine the directory where this module is located. This must be done
# before comfychair gets control, because it changes directories.
_MODULE_PATH = os.path.abspath(os.path.dirname(inspect.getfile(ValidateTest)))

if __name__ == '__main__':
    main(tests)
