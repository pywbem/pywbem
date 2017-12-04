"""
Test CIM objects (e.g. `CIMInstance`).

Ideally this file would completely describe the Python interface to
CIM objects.  If a particular data structure or Python property is
not implemented here, then it is not officially supported by PyWBEM.
Any breaking of backwards compatibility of new development should be
picked up here.

Note that class `NocaseDict` is tested in test_nocasedict.py.
"""

from __future__ import absolute_import, print_function

# Allows use of lots of single character variable names.
# pylint: disable=invalid-name,missing-docstring,too-many-statements
# pylint: disable=too-many-lines,no-self-use
import re
import inspect
import os.path
from datetime import timedelta, datetime
import unittest2 as unittest  # we use assertRaises(exc) introduced in py27

import pytest
import six

from pywbem import cim_obj, cim_types, __version__
from pywbem import CIMInstance, CIMInstanceName, CIMClass, CIMClassName, \
    CIMProperty, CIMMethod, CIMParameter, CIMQualifier, \
    CIMQualifierDeclaration, Uint8, Uint16, Uint32, \
    Uint64, Sint8, Sint16, Sint32, Sint64, Real32, Real64, CIMDateTime
from pywbem.cim_obj import NocaseDict
from pywbem.cim_types import _Longint

try:
    from pywbem import cimvalue
except ImportError:
    pass

from validate import validate_xml
from unittest_extensions import RegexpMixin, CIMObjectMixin

unimplemented = pytest.mark.skipif(True, reason="test not implemented")

# Controls whether the new behavior for CIM objects in 0.12.0 is checked.
CHECK_0_12_0 = (__version__.split('.') > ['0', '11', '0'])

print("Debug: CHECK_0_12_0 = %s, __version__ = %s" %
      (CHECK_0_12_0, __version__))


class ValidationTestCase(unittest.TestCase):
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
        global _MODULE_PATH  # pylint: disable=global-variable-not-assigned
        xml_str = obj.tocimxml().toxml()
        self.assertTrue(
            validate_xml(xml_str,
                         dtd_directory=os.path.relpath(_MODULE_PATH),
                         root_elem=root_elem),
            'DTD validation of CIM-XML for %s object failed\n'
            '  Required XML root element: %s\n'
            '  Generated CIM-XML: %s' % (type(obj), root_elem, xml_str))

        xml_str2 = obj.tocimxmlstr()
        self.assertTrue(isinstance(xml_str2, six.text_type),
                        'XML string returned by tocimxmlstr() is not '
                        'a unicode type, but: %s' % type(xml_str2))
        self.assertEqual(xml_str2, xml_str,
                         'XML string returned by tocimxmlstr() is not '
                         'equal to tocimxml().toxml().')

        xml_pretty_str = obj.tocimxml().toprettyxml(indent='    ')
        xml_pretty_str2 = obj.tocimxmlstr(indent='    ')
        self.assertTrue(isinstance(xml_pretty_str2, six.text_type),
                        'XML string returned by tocimxmlstr() is not '
                        'a unicode type, but: %s' % type(xml_pretty_str2))
        self.assertEqual(xml_pretty_str2, xml_pretty_str,
                         'XML string returned by tocimxmlstr(indent) is not '
                         'equal to tocimxml().toprettyxml(indent).')

        xml_pretty_str = obj.tocimxml().toprettyxml(indent='  ')
        xml_pretty_str2 = obj.tocimxmlstr(indent=2)
        self.assertTrue(isinstance(xml_pretty_str2, six.text_type),
                        'XML string returned by tocimxmlstr() is not '
                        'a unicode type, but: %s' % type(xml_pretty_str2))
        self.assertEqual(xml_pretty_str2, xml_pretty_str,
                         'XML string returned by tocimxmlstr(indent) is not '
                         'equal to tocimxml().toprettyxml(indent).')


def swapcase2(text):
    """Returns text, where every other character has been changed to swap
    its lexical case. For strings that contain at least one letter, the
    returned string is guaranteed to be different from the input string."""
    text_cs = ''
    i = 0
    for c in text:
        if i % 2 != 0:
            c = c.swapcase()
        text_cs += c
        i += 1
    return text_cs


class DictionaryTestCase(unittest.TestCase):
    """
    A base class for test cases that need to run a test against a dictionary
    interface, such as class `CIMInstance` that provides a dictionary interface
    for its properties.
    """
    # pylint: disable=too-many-branches
    def runtest_dict(self, obj, exp_dict):
        """
        Treat obj as a dict and run dictionary tests, and compare the
        dict content with exp_dict.

        Raises a test failure if the test fails.

        Arguments:

          * `obj`: The dictionary-like CIM object to be tested
            (e.g. `CIMInstance`).
          * `exp_dict`: The expected content of the dictionary.
        """

        # Test __getitem__()

        for key in exp_dict:
            self.assertEqual(obj[key], exp_dict[key])
            self.assertEqual(obj[swapcase2(key)], exp_dict[key])

        try:
            dummy_val = obj['Cheepy']  # noqa: F841
        except KeyError:
            pass
        else:
            self.fail('KeyError not thrown when accessing undefined key '
                      '\'Cheepy\'\n'
                      'Object: %r' % obj)

        # Test __setitem__()

        new_key = 'tmp'
        new_value = 'tmp_value'

        obj[new_key] = new_value

        self.assertEqual(obj[new_key], new_value)
        self.assertEqual(obj[swapcase2(new_key)], new_value)

        # Test has_key()

        self.assertTrue(obj.has_key(new_key))  # noqa: W601
        self.assertTrue(obj.has_key(swapcase2(new_key)))  # noqa: W601

        # Test __delitem__()

        del obj[swapcase2(new_key)]

        self.assertTrue(not obj.has_key(new_key))  # noqa: W601
        self.assertTrue(not obj.has_key(swapcase2(new_key)))  # noqa: W601

        # Test __len__()

        self.assertEqual(len(obj), len(exp_dict))

        # Test keys()

        keys = obj.keys()
        self.assertEqual(len(keys), 2)

        for key in exp_dict:
            self.assertTrue(key in keys)

        # Test values()

        values = obj.values()
        self.assertEqual(len(values), 2)

        for key in exp_dict:
            self.assertTrue(exp_dict[key] in values)

        # Test items()

        items = obj.items()
        self.assertEqual(len(items), 2)

        for key in exp_dict:
            self.assertTrue((key, exp_dict[key]) in items)

        # Test iterkeys()

        self.assertEqual(len(list(obj.iterkeys())), 2)

        for key in exp_dict:
            self.assertTrue(key in obj.iterkeys())

        # Test itervalues()

        self.assertEqual(len(list(obj.itervalues())), 2)

        for key in exp_dict:
            self.assertTrue(exp_dict[key] in obj.itervalues())

        # Test iteritems()

        self.assertEqual(len(list(obj.iteritems())), 2)

        for key in exp_dict:
            self.assertTrue((key, exp_dict[key]) in obj.iteritems())

        # Test in as test -> __getitem__()

        for key in exp_dict:
            self.assertTrue(key in obj)

        # Test in as iteration -> __iter__()

        for key in obj:
            value = obj[key]
            self.assertTrue(value, exp_dict[key])

        # Test get()

        for key in exp_dict:
            self.assertEqual(obj.get(key), exp_dict[key])
            self.assertEqual(obj.get(swapcase2(key)), exp_dict[key])

        try:
            default_value = 'NoValue'
            invalid_propname = 'Cheepy'
            self.assertEqual(obj.get(invalid_propname, default_value),
                             default_value)
        except Exception as exc:  # pylint: disable=broad-except
            self.fail('%s thrown in exception-free get() when accessing '
                      'undefined key %s\n'
                      'Object: %r' %
                      (exc.__class__.__name__, invalid_propname, obj))

        # Test update()

        obj.update({'One': '1', 'Two': '2'})
        self.assertEqual(obj['one'], '1')
        self.assertEqual(obj['two'], '2')
        for key in exp_dict:
            self.assertEqual(obj[key], exp_dict[key])
        self.assertEqual(len(obj), 4)

        obj.update({'Three': '3', 'Four': '4'}, [('Five', '5')])
        self.assertEqual(obj['three'], '3')
        self.assertEqual(obj['four'], '4')
        self.assertEqual(obj['five'], '5')
        self.assertEqual(len(obj), 7)

        obj.update([('Six', '6')], Seven='7', Eight='8')
        self.assertEqual(obj['six'], '6')
        self.assertEqual(obj['seven'], '7')
        self.assertEqual(obj['eight'], '8')
        self.assertEqual(len(obj), 10)

        obj.update(Nine='9', Ten='10')
        self.assertEqual(obj['nine'], '9')
        self.assertEqual(obj['ten'], '10')
        self.assertEqual(obj['Chicken'], 'Ham')
        self.assertEqual(obj['Beans'], 42)
        self.assertEqual(len(obj), 12)

        del obj['one'], obj['two']
        del obj['three'], obj['four'], obj['five']
        del obj['six'], obj['seven'], obj['eight']
        del obj['nine'], obj['ten']
        self.assertEqual(len(obj), 2)


class Test_CIMInstanceName_init(object):
    """
    Test the initialization of `CIMInstanceName` objects and the resulting
    attributes.

    Note that the order of the arguments `host` and `namespace` in the
    constructor is swapped compared to their optionality, for historical
    reasons (i.e. `namespace` should not be omitted if `host` is present).
    """

    # Defaults to expect for attributes when not specified in testcase
    default_exp_attrs = dict(
        keybindings=NocaseDict(),
        host=None,
        namespace=None,
    )

    datetime1_dt = datetime(2014, 9, 22, 10, 49, 20, 524789)
    datetime1_obj = CIMDateTime(datetime1_dt)

    timedelta1_td = timedelta(183, (13 * 60 + 25) * 60 + 42, 234567)
    timedelta1_obj = CIMDateTime(timedelta1_td)

    testcases_succeeds = [
        # Testcases for test_succeeds(); each testcase has these items:
        # * desc: Short testcase description.
        # * kwargs: Dict of keyword arguments for __init__().
        # * exp_attrs: Dict of expected attributes of resulting object.
        # * exp_warn_type: Expected warning type.
        # * condition: Condition for testcase to run.

        (
            "Verify that binary classname is converted to unicode",
            dict(classname=b'CIM_Foo'),
            dict(classname=u'CIM_Foo'),
            None, True
        ),
        (
            "Verify that unicode classname remains unicode",
            dict(classname=u'CIM_Foo'),
            dict(classname=u'CIM_Foo'),
            None, True
        ),
        (
            "Verify keybinding with binary string value",
            dict(
                classname='CIM_Foo',
                keybindings=dict(K1=b'Ham')),
            dict(
                classname=u'CIM_Foo',
                keybindings=NocaseDict(K1=u'Ham' if CHECK_0_12_0 else b'Ham')),
            None, True
        ),
        (
            "Verify keybinding with unicode string value",
            dict(
                classname='CIM_Foo',
                keybindings=dict(K1=u'H\u00E4m')),  # lower case a umlaut
            dict(
                classname=u'CIM_Foo',
                keybindings=NocaseDict(K1=u'H\u00E4m')),
            None, True
        ),
        (
            "Verify keybinding with boolean True value",
            dict(
                classname='CIM_Foo',
                keybindings=dict(K1=True)),
            dict(
                classname=u'CIM_Foo',
                keybindings=NocaseDict(K1=True)),
            None, True
        ),
        (
            "Verify keybinding with boolean False value",
            dict(
                classname='CIM_Foo',
                keybindings=dict(K1=False)),
            dict(
                classname=u'CIM_Foo',
                keybindings=NocaseDict(K1=False)),
            None, True
        ),
        (
            "Verify keybinding with int value (before v0.12.0)",
            dict(
                classname='CIM_Foo',
                keybindings=dict(K1=42)),
            dict(
                classname=u'CIM_Foo',
                keybindings=NocaseDict(K1=42)),
            None, not CHECK_0_12_0
        ),
        (
            "Verify keybinding with int value (with DeprecationWarning "
            "since v0.12.0)",
            dict(
                classname='CIM_Foo',
                keybindings=dict(K1=42)),
            dict(
                classname=u'CIM_Foo',
                keybindings=NocaseDict(K1=42)),
            DeprecationWarning, CHECK_0_12_0
        ),
        (
            "Verify keybinding with Uint8 value",
            dict(
                classname='CIM_Foo',
                keybindings=dict(K1=Uint8(42))),
            dict(
                classname=u'CIM_Foo',
                keybindings=NocaseDict(K1=42)),
            None, True
        ),
        (
            "Verify keybinding with Uint16 value",
            dict(
                classname='CIM_Foo',
                keybindings=dict(K1=Uint16(4216))),
            dict(
                classname=u'CIM_Foo',
                keybindings=NocaseDict(K1=4216)),
            None, True
        ),
        (
            "Verify keybinding with Uint32 value",
            dict(
                classname='CIM_Foo',
                keybindings=dict(K1=Uint32(4232))),
            dict(
                classname=u'CIM_Foo',
                keybindings=NocaseDict(K1=4232)),
            None, True
        ),
        (
            "Verify keybinding with Uint64 value",
            dict(
                classname='CIM_Foo',
                keybindings=dict(K1=Uint64(4264))),
            dict(
                classname=u'CIM_Foo',
                keybindings=NocaseDict(K1=4264)),
            None, True
        ),
        (
            "Verify keybinding with Sint8 value",
            dict(
                classname='CIM_Foo',
                keybindings=dict(K1=Sint8(-42))),
            dict(
                classname=u'CIM_Foo',
                keybindings=NocaseDict(K1=-42)),
            None, True
        ),
        (
            "Verify keybinding with Sint16 value",
            dict(
                classname='CIM_Foo',
                keybindings=dict(K1=Sint16(-4216))),
            dict(
                classname=u'CIM_Foo',
                keybindings=NocaseDict(K1=-4216)),
            None, True
        ),
        (
            "Verify keybinding with Sint32 value",
            dict(
                classname='CIM_Foo',
                keybindings=dict(K1=Sint32(-4232))),
            dict(
                classname=u'CIM_Foo',
                keybindings=NocaseDict(K1=-4232)),
            None, True
        ),
        (
            "Verify keybinding with Sint64 value",
            dict(
                classname='CIM_Foo',
                keybindings=dict(K1=Sint64(-4264))),
            dict(
                classname=u'CIM_Foo',
                keybindings=NocaseDict(K1=-4264)),
            None, True
        ),
        (
            "Verify keybinding with float value (before v0.12.0)",
            dict(
                classname='CIM_Foo',
                keybindings=dict(K1=42.1)),
            dict(
                classname=u'CIM_Foo',
                keybindings=NocaseDict(K1=42.1)),
            None, not CHECK_0_12_0
        ),
        (
            "Verify keybinding with float value (with DeprecationWarning "
            "since v0.12.0)",
            dict(
                classname='CIM_Foo',
                keybindings=dict(K1=42.1)),
            dict(
                classname=u'CIM_Foo',
                keybindings=NocaseDict(K1=42.1)),
            DeprecationWarning, CHECK_0_12_0
        ),
        (
            "Verify keybinding with Real32 value",
            dict(
                classname='CIM_Foo',
                keybindings=dict(K1=Real32(-42.32))),
            dict(
                classname=u'CIM_Foo',
                keybindings=NocaseDict(K1=-42.32)),
            None, True
        ),
        (
            "Verify keybinding with Real64 value",
            dict(
                classname='CIM_Foo',
                keybindings=dict(K1=Real64(-42.64))),
            dict(
                classname=u'CIM_Foo',
                keybindings=NocaseDict(K1=-42.64)),
            None, True
        ),
        (
            "Verify keybinding with datetime value",
            dict(
                classname='CIM_Foo',
                keybindings=dict(K1=datetime1_obj)),
            dict(
                classname=u'CIM_Foo',
                keybindings=NocaseDict(K1=datetime1_obj)),
            None, True
        ),
        (
            "Verify keybinding with timedelta value",
            dict(
                classname='CIM_Foo',
                keybindings=dict(K1=timedelta1_obj)),
            dict(
                classname=u'CIM_Foo',
                keybindings=NocaseDict(K1=timedelta1_obj)),
            None, True
        ),
        (
            "Verify keybinding with CIMProperty (of arbitrary type and value)",
            # Note: The full range of possible input values and types for
            # CIMProperty objects is tested in CIMProperty testcases.
            dict(
                classname='CIM_Foo',
                keybindings=dict(K1=CIMProperty('K1', value='Ham'))),
            dict(
                classname=u'CIM_Foo',
                keybindings=NocaseDict(K1=u'Ham')),
            None, CHECK_0_12_0
        ),
        (
            "Verify two keybindings",
            dict(
                classname='CIM_Foo',
                keybindings=dict(K1='Ham', K2=42)),
            dict(
                classname=u'CIM_Foo',
                keybindings=NocaseDict(K1=u'Ham', K2=42)),
            None, True
        ),
        (
            "Verify case insensitivity of keybinding names",
            dict(
                classname='CIM_Foo',
                keybindings=dict(Key1='Ham')),
            dict(
                classname=u'CIM_Foo',
                keybindings=NocaseDict(kEY1=u'Ham')),
            None, True
        ),
        (
            "Verify that binary namespace is converted to unicode",
            dict(
                classname='CIM_Foo',
                namespace=b'root/cimv2'),
            dict(
                classname=u'CIM_Foo',
                namespace=u'root/cimv2'),
            None, True
        ),
        (
            "Verify that unicode namespace remains unicode",
            dict(
                classname='CIM_Foo',
                namespace=u'root/cimv2'),
            dict(
                classname=u'CIM_Foo',
                namespace=u'root/cimv2'),
            None, True
        ),
        (
            "Verify that binary host is converted to unicode",
            dict(
                classname='CIM_Foo',
                namespace='root/cimv2',
                host=b'woot.com'),
            dict(
                classname=u'CIM_Foo',
                namespace=u'root/cimv2',
                host=u'woot.com'),
            None, True
        ),
        (
            "Verify that unicode host remains unicode",
            dict(
                classname='CIM_Foo',
                namespace='root/cimv2',
                host=u'woot.com'),
            dict(
                classname=u'CIM_Foo',
                namespace=u'root/cimv2',
                host=u'woot.com'),
            None, True
        ),
    ]

    testcases_fails = [
        # Testcases for test_fails(); each testcase has these items:
        # * desc: Short testcase description.
        # * kwargs: Dict of keyword arguments for __init__().
        # * exp_exc_type: Expected exception type.
        # * condition: Condition for testcase to run.

        (
            "Verify that classname None fails",
            dict(classname=None),
            ValueError,
            True
        ),
        (
            "Verify that keybinding with name None fails (with TypeError "
            "before v0.12.0",
            dict(
                classname='CIM_Foo',
                keybindings={None: 'abc'}),
            TypeError,
            not CHECK_0_12_0
        ),
        (
            "Verify that keybinding with name None fails (with ValueError "
            "since v0.12.0",
            dict(
                classname='CIM_Foo',
                keybindings={None: 'abc'}),
            ValueError,
            CHECK_0_12_0
        ),
        (
            "Verify that keybinding with inconsistent name fails",
            dict(
                classname='CIM_Foo',
                keybindings=dict(K1=CIMProperty('K1_X', value='Ham'))),
            ValueError,
            CHECK_0_12_0
        ),
    ]

    def test_pos_args(self):
        # pylint: disable=unused-argument
        """Test position of arguments in `CIMInstanceName.__init__()`."""

        # The code to be tested
        obj = CIMInstanceName(
            'CIM_Foo',
            dict(P1=True),
            'woot.com',
            'cimv2')

        assert obj.classname == u'CIM_Foo'
        assert obj.keybindings == NocaseDict(P1=True)
        assert obj.host == u'woot.com'
        assert obj.namespace == u'cimv2'

    @pytest.mark.parametrize(
        "desc, kwargs, exp_attrs, exp_warn_type, condition",
        testcases_succeeds
    )
    def test_succeeds(self, desc, kwargs, exp_attrs, exp_warn_type, condition):
        # pylint: disable=unused-argument
        """All tests for initializing `CIMInstanceName` objects that succeed."""

        if condition:

            exp_classname = exp_attrs['classname']
            exp_keybindings = exp_attrs.get(
                'keybindings', self.default_exp_attrs['keybindings'])
            exp_host = exp_attrs.get(
                'host', self.default_exp_attrs['host'])
            exp_namespace = exp_attrs.get(
                'namespace', self.default_exp_attrs['namespace'])

            if exp_warn_type is None:

                # The code to be tested
                obj = CIMInstanceName(**kwargs)

            else:
                with pytest.warns(exp_warn_type):

                    # The code to be tested
                    obj = CIMInstanceName(**kwargs)

            assert obj.classname == exp_classname
            assert type(obj.classname) is type(exp_classname)

            assert obj.keybindings == exp_keybindings
            assert type(obj.keybindings) is type(exp_keybindings)

            assert obj.host == exp_host
            assert type(obj.host) is type(exp_host)

            assert obj.namespace == exp_namespace
            assert type(obj.namespace) is type(exp_namespace)

    @pytest.mark.parametrize("desc, kwargs, exp_exc_type, condition",
                             testcases_fails)
    def test_fails(self, desc, kwargs, exp_exc_type, condition):
        # pylint: disable=unused-argument
        """All tests for initializing `CIMInstanceName` objects that fail."""

        if condition:

            with pytest.raises(exp_exc_type):

                # The code to be tested
                CIMInstanceName(**kwargs)


class CopyCIMInstanceName(unittest.TestCase, CIMObjectMixin):
    """
    Test the copy() method of `CIMInstanceName` objects.

    The basic idea is to modify the copy, and to verify that the original is
    still the same.
    """

    def test_all(self):

        i = CIMInstanceName('CIM_Foo',
                            keybindings={'InstanceID': '1234'},
                            host='woot.com',
                            namespace='root/cimv2')

        c = i.copy()

        self.assertEqual(i, c)

        c.classname = 'CIM_Bar'
        c.keybindings = NocaseDict({'InstanceID': '5678'})
        c.host = None
        c.namespace = None

        self.assertCIMInstanceName(i, 'CIM_Foo', {'InstanceID': '1234'},
                                   'woot.com', 'root/cimv2')


class CIMInstanceNameAttrs(unittest.TestCase, CIMObjectMixin):
    """
    Test that the public data attributes of `CIMInstanceName` objects can be
    accessed and modified.
    """

    def test_all(self):

        kb = {'Chicken': 'Ham', 'Beans': 42}

        obj = CIMInstanceName('CIM_Foo',
                              kb,
                              namespace='root/cimv2',
                              host='woot.com')

        self.assertCIMInstanceName(obj, 'CIM_Foo', kb,
                                   'woot.com', 'root/cimv2')

        # Check that attributes can be modified

        kb2 = {
            'NameU': u'Foo',
            'NameB': b'Bar',
            'NumUi8': Uint8(42),
            'NumUi16': Uint16(43),
            'NumUi32': Uint32(44),
            'NumUi64': Uint64(45),
            'NumSi8': Sint8(-42),
            'NumSi16': Sint16(-43),
            'NumSi32': Sint32(-44),
            'NumSi64': Sint64(-45),
            'NumR32': Real32(42.0),
            'NumR64': Real64(43.0),
            'Boolean': False,
            'Ref': CIMInstanceName('CIM_Bar'),
            'DTP': CIMDateTime(datetime(2014, 9, 22, 10, 49, 20, 524789)),
            'DTI': CIMDateTime(timedelta(10, 49, 20)),
        }
        exp_kb2 = {
            'NameU': u'Foo',
            'NameB': u'Bar' if CHECK_0_12_0 else b'Bar',
            'NumUi8': Uint8(42),
            'NumUi16': Uint16(43),
            'NumUi32': Uint32(44),
            'NumUi64': Uint64(45),
            'NumSi8': Sint8(-42),
            'NumSi16': Sint16(-43),
            'NumSi32': Sint32(-44),
            'NumSi64': Sint64(-45),
            'NumR32': Real32(42.0),
            'NumR64': Real64(43.0),
            'Boolean': False,
            'Ref': CIMInstanceName('CIM_Bar'),
            'DTP': CIMDateTime(datetime(2014, 9, 22, 10, 49, 20, 524789)),
            'DTI': CIMDateTime(timedelta(10, 49, 20)),
        }

        obj.classname = 'CIM_Bar'
        obj.keybindings = kb2
        obj.host = 'woom.com'
        obj.namespace = 'root/interop'

        self.assertCIMInstanceName(obj, 'CIM_Bar', exp_kb2,
                                   'woom.com', 'root/interop')

        # Setting classname to None

        if CHECK_0_12_0:
            with self.assertRaises(ValueError):
                obj.classname = None
        else:
            obj.classname = None
            self.assertIs(obj.classname, None)

        # Setting keybindings with CIMProperty objects

        if CHECK_0_12_0:

            kb3_in = {'Name': CIMProperty('Name', 'Foo')}
            kb3_exp = {'Name': 'Foo'}  # ... and that only the value is stored
            obj.keybindings = kb3_in
            self.assertEqual(obj.keybindings, kb3_exp)

            kb4_in = {'Name': CIMProperty('NameX', 'Foo')}
            with self.assertRaises(ValueError):
                obj.keybindings = kb4_in

        # Setting keybindings with int and float

        kb5 = {'KeyInt': 42,
               'KeyFloat': 7.5}
        obj.keybindings = kb5
        self.assertEqual(obj.keybindings, kb5)
        if CHECK_0_12_0:
            # TODO: Verify DeprecationWarning after migrating to py.test
            pass

        # Setting keybindings with key being None

        if CHECK_0_12_0:
            with self.assertRaises(ValueError):
                obj.keybindings = {None: 'bar'}
        else:
            obj.keybindings = {None: 'bar'}
            self.assertEqual(obj.keybindings[None], 'bar')


class CIMInstanceNameDict(DictionaryTestCase):
    """
    Test the dictionary interface of `CIMInstanceName` objects.
    """

    def test_all(self):

        kb = {'Chicken': 'Ham', 'Beans': 42}
        obj = CIMInstanceName('CIM_Foo', kb)

        self.runtest_dict(obj, kb)


class CIMInstanceNameEquality(unittest.TestCase):
    """
    Test the equality comparison of `CIMInstanceName` objects.
    """

    def test_all(self):

        # Basic equality tests

        self.assertEqual(CIMInstanceName('CIM_Foo'),
                         CIMInstanceName('CIM_Foo'))

        self.assertNotEqual(CIMInstanceName('CIM_Foo', {'Cheepy': 'Birds'}),
                            CIMInstanceName('CIM_Foo'))

        self.assertEqual(CIMInstanceName('CIM_Foo', {'Cheepy': 'Birds'}),
                         CIMInstanceName('CIM_Foo', {'Cheepy': 'Birds'}))

        # Class name should be case insensitive

        self.assertEqual(CIMInstanceName('CIM_Foo'),
                         CIMInstanceName('ciM_foO'))

        # Key bindings should be case insensitive

        self.assertEqual(CIMInstanceName('CIM_Foo', {'Cheepy': 'Birds'}),
                         CIMInstanceName('CIM_Foo', {'cheepy': 'Birds'}))

        self.assertNotEqual(CIMInstanceName('CIM_Foo', {'Cheepy': 'Birds'}),
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

        self.assertEqual(obj1, obj2)

        # Test that key binding types are not confused in comparisons

        self.assertNotEqual(CIMInstanceName('CIM_Foo', {'Foo': '42'}),
                            CIMInstanceName('CIM_Foo', {'Foo': 42}))

        self.assertNotEqual(CIMInstanceName('CIM_Foo', {'Bar': True}),
                            CIMInstanceName('CIM_Foo', {'Bar': 'TRUE'}))

        # Host name should be case insensitive

        self.assertEqual(CIMInstanceName('CIM_Foo', host='woot.com'),
                         CIMInstanceName('CIM_Foo', host='Woot.Com'))

        # Host name None

        self.assertNotEqual(CIMInstanceName('CIM_Foo', host=None),
                            CIMInstanceName('CIM_Foo', host='woot.com'))

        self.assertNotEqual(CIMInstanceName('CIM_Foo', host='woot.com'),
                            CIMInstanceName('CIM_Foo', host=None))

        self.assertEqual(CIMInstanceName('CIM_Foo', host=None),
                         CIMInstanceName('CIM_Foo', host=None))

        # Namespace should be case insensitive

        self.assertEqual(CIMInstanceName('CIM_Foo', namespace='root/cimv2'),
                         CIMInstanceName('CIM_Foo', namespace='Root/CIMv2'))

        # Namespace None

        self.assertNotEqual(CIMInstanceName('CIM_Foo', namespace=None),
                            CIMInstanceName('CIM_Foo', namespace='root/cimv2'))

        self.assertNotEqual(CIMInstanceName('CIM_Foo', namespace='root/cimv2'),
                            CIMInstanceName('CIM_Foo', namespace=None))

        self.assertEqual(CIMInstanceName('CIM_Foo', namespace=None),
                         CIMInstanceName('CIM_Foo', namespace=None))

        # Verify detection of incorrect type of second object

        with pytest.raises(TypeError):
            # pylint: disable=expression-not-assigned
            CIMInstanceName('CIM_Foo') == 'abc'

        with pytest.raises(TypeError):
            # pylint: disable=expression-not-assigned
            CIMInstanceName('CIM_Foo') != 'http://abc:CIM_Foo'

        with pytest.raises(TypeError):
            # pylint: disable=expression-not-assigned
            CIMInstanceName('CIM_Foo') == CIMInstance('CIM_Foo')

    def test_keybindings_order(self):
        """
        Test that two CIMInstanceName objects compare equal if their key
        bindings have a different order.

        This test was motivated by pywbem issue #686.

        This test attempts to construct dictionaries that have a different
        iteration order for their items. This may not work on all Python
        implementations and versions, but having the same order does not
        invalidate this test, it just lowers the quality of this test.

        The approach to achieve different iteration orders is based on the
        knowledge that in CPython<=3.2, the dict implementation uses a hash
        table with an initial size of 8 (which doubles its size under certain
        conditions). The two test keys 'bar' and 'baz' happen to have the
        same hash value of 4 (= hash(key) % 8) , and therefore occupy the
        same slot in the hash table (i.e. they produce a hash collision).
        In such a case, the iteration order depends on the order in which the
        items were added to the dictionary. For details, read
        http://stackoverflow.com/a/15479974/1424462.
        """

        key1 = 'bar'
        key2 = 'baz'  # should have same hash value as key1 (= hash(key) % 8)
        value1 = 'a'
        value2 = 'b'

        d1 = {key1: value1, key2: value2}
        kb1 = NocaseDict(d1)
        obj1 = CIMInstanceName('CIM_Foo', kb1)

        d2 = {key2: value2, key1: value1}
        kb2 = NocaseDict(d2)
        obj2 = CIMInstanceName('CIM_Foo', kb2)

        for k in obj1.keybindings:
            k1_first = k
            break
        for k in obj2.keybindings:
            k2_first = k
            break
        if k1_first != k2_first:
            # The key bindings do have different iteration order, so we have
            # a high test quality.
            pass
        else:
            print("\nInfo: CIMInstanceNameEquality.test_keybindings_order(): "
                  "Key bindings have the same order of keys, lowering the "
                  "quality of this test.")
            print("  Hash values of keys: k1=%r (hash: %s), k2=%r (hash: %s)" %
                  (key1, hash(key1) % 8, key2, hash(key2) % 8))
            print("  First keys: k1=%r, k2=%r" % (k1_first, k2_first))
            print("  Input dicts: d1=%r, d2=%r" % (d1, d2))
            print("  Input key bindings: kb1=%r, kb2=%r" % (kb1, kb2))
            print("  Object key bindings: obj1.kb=%r, obj2.kb=%r" %
                  (obj1.keybindings, obj2.keybindings))
            print("  Objects:\n    obj1=%r\n    obj2=%r" % (obj1, obj2))
        if obj1 != obj2:
            raise AssertionError(
                "CIMInstanceName objects with different iteration order of "
                "key bindings do not compare equal:\n"
                "  obj1=%r\n"
                "  obj2=%r" % (obj1, obj2))


class CIMInstanceNameCompare(unittest.TestCase):
    """
    Test the ordering comparison of `CIMInstanceName` objects.
    """

    @unimplemented
    def test_all(self):
        # TODO Implement ordering comparison test for CIMInstanceName
        raise AssertionError("test not implemented")


class CIMInstanceNameSort(unittest.TestCase):
    """
    Test the sorting of `CIMInstanceName` objects.
    """

    @unimplemented
    def test_all(self):
        # TODO Implement sorting test for CIMInstanceName
        raise AssertionError("test not implemented")


class Test_CIMInstanceName_str(RegexpMixin):
    """
    Test `CIMInstanceName.__str__() (returns instance path as WBEM URI)`.
    """

    @pytest.mark.parametrize(
        "obj, exp_uri", [
            (CIMInstanceName(
                classname='CIM_Foo',
                keybindings=None),
             'CIM_Foo'),
            (CIMInstanceName(
                classname='CIM_Foo',
                keybindings=dict()),
             'CIM_Foo'),
            (CIMInstanceName(
                classname='CIM_Foo',
                keybindings=dict(InstanceID=None)),
             'CIM_Foo.InstanceID="None"'),
            (CIMInstanceName(
                classname='CIM_Foo',
                keybindings=dict(InstanceID='1234')),
             'CIM_Foo.InstanceID="1234"'),
            (CIMInstanceName(
                classname='CIM_Foo',
                keybindings=dict(InstanceID='1234'),
                namespace='cimv2'),
             'cimv2:CIM_Foo.InstanceID="1234"'),
            (CIMInstanceName(
                classname='CIM_Foo',
                keybindings=dict(InstanceID='1234'),
                namespace='root/cimv2',
                host='10.11.12.13:5989'),
             '//10.11.12.13:5989/root/cimv2:CIM_Foo.InstanceID="1234"'),
            (CIMInstanceName(
                classname='CIM_Foo',
                keybindings=dict(InstanceID='1234'),
                namespace='root/cimv2',
                host='jdd:test@10.11.12.13'),
             '//jdd:test@10.11.12.13/root/cimv2:CIM_Foo.InstanceID="1234"'),
        ]
    )
    def test_single_key_succeeds(self, obj, exp_uri):
        """All test cases for CIMInstanceName.__str__() with single key that
        succeed."""

        s = str(obj)

        assert s == exp_uri

    def test_multi_key(self):
        """A test case for CIMInstanceName.__str__() with multiple keys."""

        obj = CIMInstanceName('CIM_Foo', {'Name': 'Foo', 'Secret': 42})

        s = str(obj)

        # We need to tolerate different orders of the key bindings
        assert re.match(r'^CIM_Foo\.', s)
        assert 'Secret=42' in s
        assert 'Name="Foo"' in s

        s = s.replace('CIM_Foo.', '')
        s = s.replace('Secret=42', '')
        s = s.replace('Name="Foo"', '')
        assert s == ','


class Test_CIMInstanceName_repr(RegexpMixin):
    """
    Test `CIMInstanceName.__repr__()`.
    """

    def test_all(self):

        obj = CIMInstanceName('CIM_Foo',
                              keybindings={'Name': 'Foo', 'Secret': 42},
                              namespace='root/cimv2',
                              host='woot.com')

        r = repr(obj)

        assert re.match(r'^CIMInstanceName\(', r)
        assert 'classname=%r' % obj.classname in r
        assert 'keybindings=' in r
        assert re.search('u?[\'"]Secret[\'"]: 42', r)
        assert re.search('u?[\'"]Name[\'"]: u?[\'"]Foo[\'"]', r)
        assert 'namespace=%r' % obj.namespace in r
        assert 'host=%r' % obj.host in r


class CIMInstanceNameToXML(ValidationTestCase):
    """
    Test that valid CIM-XML is generated for `CIMInstanceName` objects.
    """

    def test_all(self):

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
                                       'Boolean1': False,
                                       'Boolean2': True,
                                       'Ref': CIMInstanceName('CIM_Bar')}),
                      root_elem_CIMInstanceName_plain)

        self.validate(CIMInstanceName('CIM_Foo',
                                      namespace='root/cimv2'),
                      root_elem_CIMInstanceName_namespace)

        self.validate(CIMInstanceName('CIM_Foo',
                                      host='woot.com',
                                      namespace='root/cimv2'),
                      root_elem_CIMInstanceName_host)

        # Check that invalid key type is detected

        obj = CIMInstanceName('CIM_Foo', keybindings=dict(Name='Foo'))

        obj.keybindings['Foo'] = datetime(2017, 1, 1)  # invalid
        with pytest.raises(TypeError):
            obj.tocimxml()

        if CHECK_0_12_0:
            obj.keybindings['Foo'] = CIMParameter('Parm', 'string')  # invalid
            with pytest.raises(TypeError):
                obj.tocimxml()


class Test_CIMInstanceName_from_wbem_uri(object):
    """
    Test `CIMInstanceName.from_wbem_uri()`.
    """

    @pytest.mark.parametrize(
        "uri, exp_obj", [
            ('https://jdd:test@10.11.12.13:5989/root/cimv2:CIM_Foo.k1="v1"',
             CIMInstanceName(
                 classname='CIM_Foo',
                 keybindings=dict(k1='v1'),
                 namespace='root/cimv2',
                 host='jdd:test@10.11.12.13:5989')),
            ('https://10.11.12.13:5989/root/cimv2:CIM_Foo.k1="v1",k2="v2"',
             CIMInstanceName(
                 classname='CIM_Foo',
                 keybindings=dict(k1='v1', k2='v2'),
                 namespace='root/cimv2',
                 host='10.11.12.13:5989')),
            ('http://10.11.12.13/root/cimv2:CIM_Foo.k1="v1"',
             CIMInstanceName(
                 classname='CIM_Foo',
                 keybindings=dict(k1='v1'),
                 namespace='root/cimv2',
                 host='10.11.12.13')),
            ('http://10.11.12.13/cimv2:CIM_Foo.k1="v1"',
             CIMInstanceName(
                 classname='CIM_Foo',
                 keybindings=dict(k1='v1'),
                 namespace='cimv2',
                 host='10.11.12.13')),
            ('http://10.11.12.13/cimv2:CIM_Foo.k1=42,k2=true,k3="abc",k4="42"',
             CIMInstanceName(
                 classname='CIM_Foo',
                 keybindings=dict(k1=42, k2=True, k3='abc', k4='42'),
                 namespace='cimv2',
                 host='10.11.12.13')),
        ]
    )
    def test_succeeds(self, uri, exp_obj):
        """All test cases for CIMInstanceName.from_wbem_uri() that succeed."""

        if CHECK_0_12_0:

            obj = CIMInstanceName.from_wbem_uri(uri)

            assert isinstance(obj, CIMInstanceName)
            assert obj.classname == exp_obj.classname
            assert obj.keybindings == exp_obj.keybindings
            assert obj.namespace == exp_obj.namespace
            assert obj.host == exp_obj.host

    @pytest.mark.parametrize(
        # TODO: Improve implementation to make it fail for the disabled cases.
        "uri, exp_exc", [
            ('https:/10.11.12.13:5989/cimv2:CIM_Foo.k1="v1"',
             ValueError),  # missing '/' after scheme
            # ('xyz://10.11.12.13:5989/cimv2:CIM_Foo.k1="v1"',
            #  ValueError),  # invalid scheme
            # ('https://10.11.12.13;5989/cimv2:CIM_Foo.k1="v1"',
            #  ValueError),  # invalid ';' between host and port
            ('https://10.11.12.13:5989:cimv2:CIM_Foo.k1="v1"',
             ValueError),  # invalid ':' between port and namespace
            # ('https://10.11.12.13:5989/cimv2.CIM_Foo.k1="v1"',
            #  ValueError),  # invalid '.' between namespace and classname
            # ('https://10.11.12.13:5989/cimv2/CIM_Foo.k1="v1"',
            #  ValueError),  # invalid '/' between namespace and classname
            ('https://10.11.12.13:5989/cimv2:CIM_Foo:k1="v1"',
             ValueError),  # invalid ':' between classname and key k1
            ('https://10.11.12.13:5989/cimv2:CIM_Foo/k1="v1"',
             ValueError),  # invalid '/' between classname and key k1
            # ('https://10.11.12.13:5989/cimv2:CIM_Foo.k1="v1".k2="v2"',
            #  ValueError),  # invalid '.' between key k1 and key k2
            # ('https://10.11.12.13:5989/cimv2:CIM_Foo.k1="v1":k2="v2"',
            #  ValueError),  # invalid ':' between key k1 and key k2
            ('https://10.11.12.13:5989/cimv2:CIM_Foo.k1="v1".k2=v2',
             ValueError),  # double quotes missing around value of key k2
            ('https://10.11.12.13:5989/cimv2:CIM_Foo.k1="v1".k2=\'v2\'',
             ValueError),  # single quotes used around value of key k2
        ]
    )
    def test_fails(self, uri, exp_exc):
        """All test cases for CIMInstanceName.from_wbem_uri() that fail."""

        if CHECK_0_12_0:

            with pytest.raises(Exception) as exc_info:
                CIMInstanceName.from_wbem_uri(uri)
            exc = exc_info.value

            assert isinstance(exc, exp_exc)


class Test_CIMInstance_init(object):
    """
    Test the initialization of `CIMInstance` objects and the resulting
    attributes.

    Some notes on testing input parameters of this class:

    * `properties`: We are testing a reasonably full range of input variations,
      because there is processing of the provided properties in
      `CIMInstance.__init__()`.

    * `qualifiers: The full range of input variations is not tested, because
      we know that the input parameter is just turned into a `NocaseDict` and
      otherwise left unchanged, so the full range testing is expected to be
      tested in the test cases for `CIMQualifier`.

    * `property_list`: These tests are not here, but in class
      CIMInstancePropertyList.
    """

    # Defaults to expect for attributes when not specified in testcase
    default_exp_attrs = dict(
        properties=NocaseDict(),
        qualifiers=NocaseDict(),
        path=None,
        property_list=None,
    )

    testcases_succeeds = [
        # Testcases for test_succeeds(); each testcase has these items:
        # * desc: Short testcase description.
        # * kwargs: Dict of keyword arguments for __init__().
        # * exp_attrs: Dict of expected attributes of resulting object.
        # * exp_warn_type: Expected warning type.
        # * condition: Condition for testcase to run.

        (
            "Verify that classname None is accepted (before 0.12.0)",
            dict(classname=None),
            dict(classname=None),
            None, not CHECK_0_12_0
        ),
        (
            "Verify that binary classname is converted to unicode",
            dict(classname=b'CIM_Foo'),
            dict(classname=u'CIM_Foo'),
            None, True
        ),
        (
            "Verify that unicode classname remains unicode",
            dict(classname=u'CIM_Foo'),
            dict(classname=u'CIM_Foo'),
            None, True
        ),
        (
            "Verify property with binary string value",
            dict(
                classname='CIM_Foo',
                properties=dict(P1=b'Ham')),
            dict(
                classname=u'CIM_Foo',
                properties=NocaseDict(
                    P1=CIMProperty('P1', value=u'Ham'))),
            None, True
        ),
        (
            "Verify property with unicode string value",
            dict(
                classname='CIM_Foo',
                properties=dict(P1=u'H\u00E4m')),  # lower case a umlaut
            dict(
                classname=u'CIM_Foo',
                properties=NocaseDict(
                    P1=CIMProperty('P1', value=u'H\u00E4m'))),
            None, True
        ),
        (
            "Verify property with boolean True value",
            dict(
                classname='CIM_Foo',
                properties=dict(P1=True)),
            dict(
                classname=u'CIM_Foo',
                properties=NocaseDict(
                    P1=CIMProperty('P1', value=True))),
            None, True
        ),
        (
            "Verify property with boolean False value",
            dict(
                classname='CIM_Foo',
                properties=dict(P1=False)),
            dict(
                classname=u'CIM_Foo',
                properties=NocaseDict(
                    P1=CIMProperty('P1', value=False))),
            None, True
        ),
        (
            "Verify property with Uint8 value",
            dict(
                classname='CIM_Foo',
                properties=dict(P1=Uint8(42))),
            dict(
                classname=u'CIM_Foo',
                properties=NocaseDict(
                    P1=CIMProperty('P1', type='uint8', value=Uint8(42)))),
            None, True
        ),
        (
            "Verify property with Uint16 value",
            dict(
                classname='CIM_Foo',
                properties=dict(P1=Uint16(4216))),
            dict(
                classname=u'CIM_Foo',
                properties=NocaseDict(
                    P1=CIMProperty('P1', type='uint16', value=Uint16(4216)))),
            None, True
        ),
        (
            "Verify property with Uint32 value",
            dict(
                classname='CIM_Foo',
                properties=dict(P1=Uint32(4232))),
            dict(
                classname=u'CIM_Foo',
                properties=NocaseDict(
                    P1=CIMProperty('P1', type='uint32', value=Uint32(4232)))),
            None, True
        ),
        (
            "Verify property with Uint64 value",
            dict(
                classname='CIM_Foo',
                properties=dict(P1=Uint64(4264))),
            dict(
                classname=u'CIM_Foo',
                properties=NocaseDict(
                    P1=CIMProperty('P1', type='uint64', value=Uint64(4264)))),
            None, True
        ),
        (
            "Verify property with Sint8 value",
            dict(
                classname='CIM_Foo',
                properties=dict(P1=Sint8(-42))),
            dict(
                classname=u'CIM_Foo',
                properties=NocaseDict(
                    P1=CIMProperty('P1', type='sint8', value=Sint8(-42)))),
            None, True
        ),
        (
            "Verify property with Sint16 value",
            dict(
                classname='CIM_Foo',
                properties=dict(P1=Sint16(-4216))),
            dict(
                classname=u'CIM_Foo',
                properties=NocaseDict(
                    P1=CIMProperty('P1', type='sint16', value=Sint16(-4216)))),
            None, True
        ),
        (
            "Verify property with Sint32 value",
            dict(
                classname='CIM_Foo',
                properties=dict(P1=Sint32(-4232))),
            dict(
                classname=u'CIM_Foo',
                properties=NocaseDict(
                    P1=CIMProperty('P1', type='sint32', value=Sint32(-4232)))),
            None, True
        ),
        (
            "Verify property with Sint64 value",
            dict(
                classname='CIM_Foo',
                properties=dict(P1=Sint64(-4264))),
            dict(
                classname=u'CIM_Foo',
                properties=NocaseDict(
                    P1=CIMProperty('P1', type='sint64', value=Sint64(-4264)))),
            None, True
        ),
        (
            "Verify property with Real32 value",
            dict(
                classname='CIM_Foo',
                properties=dict(P1=Real32(-42.32))),
            dict(
                classname=u'CIM_Foo',
                properties=NocaseDict(
                    P1=CIMProperty('P1', type='real32', value=Real32(-42.32)))),
            None, True
        ),
        (
            "Verify property with Real64 value",
            dict(
                classname='CIM_Foo',
                properties=dict(P1=Real64(-42.64))),
            dict(
                classname=u'CIM_Foo',
                properties=NocaseDict(
                    P1=CIMProperty('P1', type='real64', value=Real64(-42.64)))),
            None, True
        ),
        (
            "Verify property with datetime value",
            # Note: Because this is a test for CIMInstance and not for
            # CIMProperty, we simplify this test by passing the same datetime
            # input to the expected attributes as we pass to the input args.
            dict(
                classname='CIM_Foo',
                properties=dict(P1=datetime(2014, 9, 22, 10, 49, 20, 524789))),
            dict(
                classname=u'CIM_Foo',
                properties=NocaseDict(
                    P1=CIMProperty(
                        'P1', type='datetime',
                        value=datetime(2014, 9, 22, 10, 49, 20, 524789)))),
            None, True
        ),
        (
            "Verify property with timedelta value",
            # Note: Because this is a test for CIMInstance and not for
            # CIMProperty, we simplify this test by passing the same timedelta
            # input to the expected attributes as we pass to the input args.
            dict(
                classname='CIM_Foo',
                properties=dict(P1=timedelta(10, 49, 20))),
            dict(
                classname=u'CIM_Foo',
                properties=NocaseDict(
                    P1=CIMProperty(
                        'P1', type='datetime',
                        value=timedelta(10, 49, 20)))),
            None, True
        ),
        (
            "Verify property with CIMProperty (of arbitrary type and value)",
            # Note: The full range of possible input values and types for
            # CIMProperty objects is tested in CIMProperty testcases.
            dict(
                classname='CIM_Foo',
                properties=dict(P1=CIMProperty('P1', value='Ham'))),
            dict(
                classname=u'CIM_Foo',
                properties=NocaseDict(
                    P1=CIMProperty('P1', value=u'Ham'))),
            None, True
        ),
        (
            "Verify qualifier with CIMQualifier (of arbitrary type and value)",
            # Note: The full range of possible input values and types for
            # CIMQualifier objects is tested in CIMQualifier testcases.
            dict(
                classname='CIM_Foo',
                qualifiers=dict(Q1=CIMQualifier('Q1', value='Ham'))),
            dict(
                classname=u'CIM_Foo',
                qualifiers=NocaseDict(
                    Q1=CIMQualifier('Q1', value=u'Ham'))),
            None, True
        ),
        (
            "Verify path without corresponding key property",
            dict(
                classname='CIM_Foo',
                path=CIMInstanceName(
                    classname='CIM_Foo',
                    keybindings=dict(K1='Key1'))),
            dict(
                classname=u'CIM_Foo',
                path=CIMInstanceName(
                    classname='CIM_Foo',
                    keybindings=dict(K1='Key1'))),
            None, True
        ),
        (
            "Verify the keybindings in path with corresponding key property "
            "are set to key property value",
            # Note: The full set of tests for this kind of updating is in
            # CIMInstancePropertyList.
            dict(
                classname='CIM_Foo',
                properties=dict(K1='Ham'),
                path=CIMInstanceName(
                    classname='CIM_Foo',
                    keybindings=dict(K1='Key1'))),
            dict(
                classname=u'CIM_Foo',
                properties=NocaseDict(
                    K1=CIMProperty('K1', value='Ham')),
                path=CIMInstanceName(
                    classname='CIM_Foo',
                    keybindings=dict(K1='Ham'))),  # has been updated
            None, True
        ),
    ]

    testcases_fails = [
        # Testcases for test_fails(); each testcase has these items:
        # * desc: Short testcase description.
        # * kwargs: Dict of keyword arguments for __init__().
        # * exp_exc_type: Expected exception type.
        # * condition: Condition for testcase to run.

        (
            "Verify that classname None fails (since 0.12.0)",
            dict(classname=None),
            ValueError,
            CHECK_0_12_0
        ),
        (
            "Verify that property with name None fails",
            dict(
                classname='CIM_Foo',
                properties={None: 'abc'}),
            ValueError,
            True
        ),
        (
            "Verify that property CIMProperty with inconsistent name fails "
            "(since 0.12.0)",
            dict(
                classname='CIM_Foo',
                properties=dict(P1=CIMProperty('P1_X', 'abc'))),
            ValueError,
            CHECK_0_12_0
        ),
        (
            "Verify that property with int value fails (with ValueError since "
            "0.12.0)",
            dict(
                classname='CIM_Foo',
                properties=dict(P1=42)),
            ValueError,
            CHECK_0_12_0
        ),
        (
            "Verify that property with int value fails (with TypeError before "
            "0.12.0)",
            dict(
                classname='CIM_Foo',
                properties=dict(P1=42)),
            TypeError,
            not CHECK_0_12_0
        ),
        (
            "Verify that property with float value fails (with ValueError "
            "since 0.12.0)",
            dict(
                classname='CIM_Foo',
                properties=dict(P1=42.1)),
            ValueError,
            CHECK_0_12_0
        ),
        (
            "Verify that property with float value fails (with TypeError "
            "before 0.12.0)",
            dict(
                classname='CIM_Foo',
                properties=dict(P1=42.1)),
            TypeError,
            not CHECK_0_12_0
        ),
        (
            "Verify that property with float value fails (on Python 2 only, "
            "with ValueError since 0.12.0)",
            dict(
                classname='CIM_Foo',
                properties=dict(P1=_Longint(42))),
            ValueError,
            six.PY2 and CHECK_0_12_0
        ),
        (
            "Verify that property with float value fails (on Python 2 only, "
            "with TypeError before 0.12.0)",
            dict(
                classname='CIM_Foo',
                properties=dict(P1=_Longint(42))),
            TypeError,
            six.PY2 and not CHECK_0_12_0
        ),
        (
            "Verify that qualifier with name None fails (with TypeError "
            "before 0.12.0)",
            dict(
                classname='CIM_Foo',
                qualifiers={None: 'abc'}),
            TypeError,
            not CHECK_0_12_0
        ),
        (
            "Verify that qualifier with name None fails (with ValueError "
            "since 0.12.0)",
            dict(
                classname='CIM_Foo',
                qualifiers={None: 'abc'}),
            ValueError,
            CHECK_0_12_0
        ),
        (
            "Verify that qualifier CIMQualifier with inconsistent name fails "
            "(since 0.12.0)",
            dict(
                classname='CIM_Foo',
                qualifiers=dict(Q1=CIMQualifier('Q1_X', 'abc'))),
            ValueError,
            CHECK_0_12_0
        ),
    ]

    def test_pos_args(self):
        # pylint: disable=unused-argument
        """Test position of arguments in `CIMInstance.__init__()`."""

        # The code to be tested
        obj = CIMInstance(
            'CIM_Foo',
            dict(P1=True),
            dict(Q1=CIMQualifier('Q1', value=True)),
            CIMInstanceName('CIM_Foo'),
            ['P1'])

        assert obj.classname == u'CIM_Foo'
        assert obj.properties == NocaseDict(P1=CIMProperty('P1', value=True))
        assert obj.qualifiers == NocaseDict(Q1=CIMQualifier('Q1', value=True))
        assert obj.path == CIMInstanceName('CIM_Foo')
        assert obj.property_list == ['p1']

    @pytest.mark.parametrize(
        "desc, kwargs, exp_attrs, exp_warn_type, condition",
        testcases_succeeds)
    def test_succeeds(self, desc, kwargs, exp_attrs, exp_warn_type, condition):
        # pylint: disable=unused-argument
        """All tests for initializing `CIMInstance` objects that succeed."""

        if condition:

            exp_classname = exp_attrs['classname']
            exp_properties = exp_attrs.get(
                'properties', self.default_exp_attrs['properties'])
            exp_qualifiers = exp_attrs.get(
                'qualifiers', self.default_exp_attrs['qualifiers'])
            exp_path = exp_attrs.get(
                'path', self.default_exp_attrs['path'])
            exp_property_list = exp_attrs.get(
                'property_list', self.default_exp_attrs['property_list'])

            if exp_warn_type is None:

                # The code to be tested
                obj = CIMInstance(**kwargs)

            else:
                with pytest.warns(exp_warn_type):

                    # The code to be tested
                    obj = CIMInstance(**kwargs)

            assert obj.classname == exp_classname
            assert type(obj.classname) is type(exp_classname)

            assert obj.properties == exp_properties
            assert type(obj.properties) is type(exp_properties)

            assert obj.qualifiers == exp_qualifiers
            assert type(obj.qualifiers) is type(exp_qualifiers)

            assert obj.path == exp_path
            assert type(obj.path) is type(exp_path)

            assert obj.property_list == exp_property_list
            assert type(obj.property_list) is type(exp_property_list)

    @pytest.mark.parametrize("desc, kwargs, exp_exc_type, condition",
                             testcases_fails)
    def test_fails(self, desc, kwargs, exp_exc_type, condition):
        # pylint: disable=unused-argument
        """All tests for initializing `CIMInstance` objects that fail."""

        if condition:

            with pytest.raises(exp_exc_type):

                # The code to be tested
                CIMInstance(**kwargs)


class CopyCIMInstance(unittest.TestCase):
    """
    Test the copy() method of `CIMInstance` objects.

    The basic idea is to modify the copy, and to verify that the original is
    still the same.
    """

    def test_all(self):

        # TODO Add tests for CIMInstance property_list argument

        i = CIMInstance('CIM_Foo',
                        properties={'Name': 'Foo', 'Chicken': 'Ham'},
                        qualifiers={'Key': CIMQualifier('Key', True)},
                        path=CIMInstanceName('CIM_Foo', {'Name': 'Foo'}))

        c = i.copy()

        self.assertEqual(i, c)

        c.classname = 'CIM_Bar'
        c.properties = {'InstanceID': '5678'}
        c.qualifiers = {}
        c.path = None

        self.assertEqual(i.classname, 'CIM_Foo')
        self.assertEqual(i['Name'], 'Foo')
        self.assertEqual(i.qualifiers['Key'], CIMQualifier('Key', True))
        self.assertEqual(i.path, CIMInstanceName('CIM_Foo', {'Name': 'Foo'}))

        # Test copy when path is None

        i = CIMInstance('CIM_Foo',
                        properties={'Name': 'Foo', 'Chicken': 'Ham'},
                        qualifiers={'Key': CIMQualifier('Key', True)},
                        path=None)

        c = i.copy()

        self.assertEqual(i, c)

        c.classname = 'CIM_Bar'
        c.properties = {'InstanceID': '5678'}
        c.qualifiers = {}
        c.path = CIMInstanceName('CIM_Foo', {'Name': 'Foo'})

        self.assertEqual(i.classname, 'CIM_Foo')
        self.assertEqual(i['Name'], 'Foo')
        self.assertEqual(i.qualifiers['Key'], CIMQualifier('Key', True))
        self.assertEqual(i.path, None)


class CIMInstanceAttrs(unittest.TestCase):
    """
    Test that the public data attributes of `CIMInstance` objects can be
    accessed and modified.
    """

    def test_all(self):

        props = {'Chicken': CIMProperty('Chicken', 'Ham'),
                 'Number': CIMProperty('Number', Uint32(42))}
        quals = {'Key': CIMQualifier('Key', True)}
        path = CIMInstanceName('CIM_Foo', {'Chicken': 'Ham'})

        obj = CIMInstance('CIM_Foo',
                          properties=props,
                          qualifiers=quals,
                          path=path)

        self.assertEqual(obj.classname, 'CIM_Foo')
        self.assertEqual(obj.properties, props)
        self.assertEqual(obj.qualifiers, quals)
        self.assertEqual(obj.path, path)

        props = {'Foo': CIMProperty('Foo', 'Bar')}
        quals = {'Min': CIMQualifier('Min', Uint32(42))}
        path = CIMInstanceName('CIM_Bar', {'Foo': 'Bar'})

        obj.classname = 'CIM_Bar'
        obj.properties = props
        obj.qualifiers = quals
        obj.path = path

        self.assertEqual(obj.classname, 'CIM_Bar')
        self.assertEqual(obj.properties, props)
        self.assertEqual(obj.qualifiers, quals)
        self.assertEqual(obj.path, path)

        # Setting classname to None

        if CHECK_0_12_0:
            with self.assertRaises(ValueError):
                obj.classname = None
        else:
            # Before 0.12.0, the implementation allowed the classname to be
            # None, although the documentation required it not to be None.
            # We test the implemented behavior.
            obj.classname = None
            self.assertIs(obj.classname, None)

        # Setting properties to CIMProperty with inconsistent name

        if CHECK_0_12_0:
            props = {'Name': CIMProperty('NameX', 'Foo')}
            with self.assertRaises(ValueError):
                obj.properties = props

        # Setting properties with name being None

        if CHECK_0_12_0:
            with self.assertRaises(ValueError):
                obj.properties = {None: 'meat'}
        else:
            obj.properties = {None: 'meat'}
            self.assertEqual(len(obj.properties), 1)
            self.assertEqual(obj.properties[None], 'meat')


class CIMInstanceDict(DictionaryTestCase):
    """Test the Python dictionary interface for CIMInstance."""

    def test_all(self):

        props = {'Chicken': 'Ham', 'Beans': Uint32(42)}

        obj = CIMInstance('CIM_Foo', props)

        self.runtest_dict(obj, props)

        # Setting properties to int, float and long

        with self.assertRaises(ValueError if CHECK_0_12_0 else TypeError):
            obj['Foo'] = 43

        with self.assertRaises(ValueError if CHECK_0_12_0 else TypeError):
            obj['Foo'] = 43.1

        if six.PY2:
            with self.assertRaises(ValueError if CHECK_0_12_0 else TypeError):
                obj['Foo'] = long(43)  # noqa: F821

        # Setting properties to CIM data type values

        obj['Foo'] = Uint32(43)


class CIMInstanceEquality(unittest.TestCase):
    """Test comparing CIMInstance objects."""

    def test_all(self):

        # Basic equality tests

        self.assertEqual(CIMInstance('CIM_Foo'),
                         CIMInstance('CIM_Foo'))

        self.assertNotEqual(CIMInstance('CIM_Foo', {'Cheepy': 'Birds'}),
                            CIMInstance('CIM_Foo'))

        # Classname should be case insensitive

        self.assertEqual(CIMInstance('CIM_Foo'),
                         CIMInstance('cim_foo'))

        # NocaseDict should implement case insensitive keybinding names

        self.assertEqual(CIMInstance('CIM_Foo', {'Cheepy': 'Birds'}),
                         CIMInstance('CIM_Foo', {'cheepy': 'Birds'}))

        self.assertNotEqual(CIMInstance('CIM_Foo', {'Cheepy': 'Birds'}),
                            CIMInstance('CIM_Foo', {'cheepy': 'birds'}))

        # Qualifiers

        self.assertNotEqual(CIMInstance('CIM_Foo'),
                            CIMInstance('CIM_Foo',
                                        qualifiers={'Key':
                                                    CIMQualifier('Key',
                                                                 True)}))

        # Path

        self.assertNotEqual(CIMInstance('CIM_Foo'),
                            CIMInstance('CIM_Foo', {'Cheepy': 'Birds'}))

        # Reference properties

        self.assertEqual(CIMInstance('CIM_Foo',
                                     {'Ref1': CIMInstanceName('CIM_Bar')}),
                         CIMInstance('CIM_Foo',
                                     {'Ref1': CIMInstanceName('CIM_Bar')}))

        # Null properties

        self.assertEqual(
            CIMInstance('CIM_Foo',
                        {'Null': CIMProperty('Null', None, type='string')}),
            CIMInstance('CIM_Foo',
                        {'Null': CIMProperty('Null', None, type='string')}))

        self.assertNotEqual(
            CIMInstance('CIM_Foo',
                        {'Null': CIMProperty('Null', None, type='string')}),
            CIMInstance('CIM_Foo',
                        {'Null': CIMProperty('Null', '')}))

        self.assertNotEqual(
            CIMInstance('CIM_Foo',
                        {'Null': CIMProperty('Null', None, type='uint32')}),
            CIMInstance('CIM_Foo',
                        {'Null': CIMProperty('Null', Uint32(0))}))

        # Mix of CIMProperty and native Python types

        self.assertEqual(
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
            )  # noqa: E123

        # Verify detection of incorrect type of second object

        with pytest.raises(TypeError):
            # pylint: disable=expression-not-assigned
            CIMInstance('CIM_Foo') == 'abc'

        with pytest.raises(TypeError):
            # pylint: disable=expression-not-assigned
            CIMInstance('CIM_Foo') != 'http://abc:CIM_Foo'

        with pytest.raises(TypeError):
            # pylint: disable=expression-not-assigned
            CIMInstance('CIM_Foo') == CIMInstanceName('CIM_Foo')


class CIMInstanceCompare(unittest.TestCase):
    """
    Test the ordering comparison of `CIMInstance` objects.
    """

    @unimplemented
    def test_all(self):
        # TODO Implement ordering comparison test for CIMInstance
        raise AssertionError("test not implemented")


class CIMInstanceSort(unittest.TestCase):
    """
    Test the sorting of `CIMInstance` objects.
    """

    @unimplemented
    def test_all(self):
        # TODO Implement sorting test for CIMInstance
        raise AssertionError("test not implemented")


class Test_CIMInstance_str(object):
    """
    Test `CIMInstance.__str__()`.
    """

    def test_all(self):

        path = CIMInstanceName(
            'CIM_Foo',
            keybindings=dict(Name='Spottyfoot'))

        obj = CIMInstance(
            'CIM_Foo',
            properties=dict(
                Name='Spottyfoot',
                Ref1=CIMInstanceName('CIM_Bar')),
            path=path)

        s = str(obj)

        assert re.match(r'^CIMInstance\(', s)
        assert 'classname=%r' % obj.classname in s
        assert 'path=CIMInstanceName(' in s


class Test_CIMInstance_repr(object):
    """
    Test `CIMInstance.__repr__()`.
    """

    def test_all(self):

        path = CIMInstanceName(
            'CIM_Foo',
            keybindings=dict(Name='Spottyfoot'))

        obj = CIMInstance(
            'CIM_Foo',
            properties=dict(
                Name='Spottyfoot',
                Ref1=CIMInstanceName('CIM_Bar')),
            path=path)

        r = repr(obj)

        assert re.match(r'^CIMInstance\(', r)
        assert 'classname=%r' % obj.classname in r
        assert 'path=CIMInstanceName(' in r
        assert 'properties=' in r
        assert 'property_list=' in r
        assert 'qualifiers=' in r


class CIMInstanceToXML(ValidationTestCase):
    """
    Test that valid CIM-XML is generated for `CIMInstance` objects.
    """

    def test_all(self):

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

        # Verify that invalid property objects are detected

        obj = CIMInstance('CIM_Foo')

        obj.properties['Invalid'] = 'abc'  # invalid
        if CHECK_0_12_0:
            with pytest.raises(TypeError):
                obj.tocimxml()
        else:
            obj.tocimxml()

        obj.properties['Invalid'] = Uint8(42)  # invalid
        if CHECK_0_12_0:
            with pytest.raises(TypeError):
                obj.tocimxml()
        else:
            obj.tocimxml()


class CIMInstanceToMOF(unittest.TestCase):
    """
    Test that valid MOF is generated for `CIMInstance` objects.
    """

    def test_all(self):

        i = CIMInstance('CIM_Foo',
                        {'MyString': 'string',
                         'MyUint8': Uint8(0),
                         'MyUint8array': [Uint8(1), Uint8(2)],
                         'MyRef': CIMInstanceName('CIM_Bar')})

        imof = i.tomof()

        # match first line
        m = re.match(
            r"^\s*instance\s+of\s+CIM_Foo\s*\{"
            r"(?:\s*(\w+)\s*=\s*.*;){4,4}"  # just match the general syntax
            r"\s*\}\s*;\s*$", imof)
        if m is None:
            self.fail("Invalid MOF generated.\n"
                      "Instance: %r\n"
                      "Generated MOF: %r" % (i, imof))

        # search for one property
        s = re.search(r"\n\s*MyRef\s*=\s*CIM_Bar;\n", imof)
        if s is None:
            self.fail("Invalid MOF generated. No MyRef.\n"
                      "Instance: %r\n"
                      "Generated MOF: %r" % (i, imof))


class CIMInstanceWithEmbeddedInstToMOF(unittest.TestCase):
    """Test that MOF with valid embedded insance is generated for instance"""

    def test_all(self):

        str_data = "The pink fox jumped over the big blue dog"
        dt = datetime(2014, 9, 22, 10, 49, 20, 524789)

        embed = CIMInstance('CIM_Embedded',
                            {'EbString': 'string',
                             'EbUint8': Uint8(0),
                             'EbStrArray': [str_data, str_data, str_data],
                             'EbUint8array': [Uint8(1), Uint8(2)],
                             'EbRef': CIMInstanceName('CIM_Bar'),
                             'EbUint64Array': [Uint64(123456789),
                                               Uint64(123456789),
                                               Uint64(123456789)]})

        i = CIMInstance('CIM_Foo',
                        {'MyString': 'string',
                         'MyUint8': Uint8(0),
                         'MyUint8Array': [Uint8(1), Uint8(2)],
                         'MyUint64Array': [Uint64(123456789),
                                           Uint64(123456789),
                                           Uint64(123456789)],
                         'MyRef': CIMInstanceName('CIM_Bar'),
                         'MyEmbed': embed,
                         'MyUint32': Uint32(9999),
                         'MyDateTimeArray': [dt, dt, dt],
                         'MyStrLongArray': [str_data, str_data, str_data]})

        imof = i.tomof()

        m = re.match(
            r"^\s*instance\s+of\s+CIM_Foo\s*\{",
            imof)

        if m is None:
            self.fail("Invalid MOF generated.\n"
                      "Instance: %r\n"
                      "Generated MOF: %r" % (i, imof))

        # search for the CIM_Embedded instance.
        s = re.search(r"CIM_Embedded", imof)

        if s is None:
            self.fail("Invalid MOF embedded generated.\n"
                      "Instance: %r\n"
                      "Generated MOF: %r" % (i, imof))
        # TODO this test only catchs existence of the embedded instance


class CIMInstanceUpdatePath(unittest.TestCase):
    """
    Test updating key and non-key properties of `CIMInstance` objects.
    """

    def test_all(self):

        iname = CIMInstanceName('CIM_Foo', namespace='root/cimv2',
                                keybindings={'k1': None, 'k2': None})

        i = CIMInstance('CIM_Foo', path=iname)

        i['k1'] = 'key1'
        self.assertEqual(i['k1'], 'key1')
        self.assertTrue('k1' in i)
        self.assertEqual(i.path['k1'], 'key1')  # also updates the path

        i['k2'] = 'key2'
        self.assertEqual(i['k2'], 'key2')
        self.assertTrue('k2' in i)
        self.assertEqual(i.path['k2'], 'key2')  # also updates the path

        i['p1'] = 'prop1'
        self.assertEqual(len(i.path.keybindings), 2)
        self.assertTrue('p1' not in i.path)  # no key, does not update the path


class CIMInstancePropertyList(unittest.TestCase):
    """
    Test updating key and non-key properties of `CIMInstance` objects, with
    property list.
    """

    def test_all(self):

        iname = CIMInstanceName('CIM_Foo', namespace='root/cimv2',
                                keybindings={'k1': None, 'k2': None})

        i = CIMInstance('CIM_Foo', path=iname, property_list=['P1', 'P2'])

        self.assertEqual(i.property_list, ['p1', 'p2'])

        i['k1'] = 'key1'
        self.assertEqual(i['k1'], 'key1')
        self.assertTrue('k1' in i)
        self.assertEqual(i.path['k1'], 'key1')  # also updates the path

        i['k2'] = 'key2'
        self.assertEqual(i['k2'], 'key2')
        self.assertTrue('k2' in i)
        self.assertEqual(i.path['k2'], 'key2')  # also updates the path

        i['p1'] = 'prop1'
        self.assertEqual(i['p1'], 'prop1')
        self.assertTrue('p1' in i)
        self.assertEqual(len(i.path.keybindings), 2)
        self.assertTrue('p1' not in i.path)

        i['p2'] = 'prop2'
        self.assertEqual(i['p2'], 'prop2')
        self.assertTrue('p2' in i)
        self.assertEqual(len(i.path.keybindings), 2)
        self.assertTrue('p2' not in i.path)

        i['p3'] = 'prop3'
        self.assertTrue('p3' not in i)  # the effect of property list


class CIMInstanceUpdateExisting(unittest.TestCase):
    """
    Test the update_existing() method of `CIMInstance` objects.

    There is also a test for update_existing() on `CIMInstanceName` objects.
    """

    def test_all(self):

        i = CIMInstance('CIM_Foo',
                        {'string': 'string',
                         'uint8': Uint8(0),
                         'uint8array': [Uint8(1), Uint8(2)],
                         'ref': CIMInstanceName('CIM_Bar')})

        self.assertEqual(i['string'], 'string')

        i.update_existing({'one': '1', 'string': '_string_'})
        self.assertTrue('one' not in i)
        self.assertEqual(i['string'], '_string_')
        try:
            i['one']
        except KeyError:
            pass
        else:
            self.fail('KeyError not thrown')
        self.assertEqual(i['uint8'], 0)

        i.update_existing([('Uint8', 1), ('one', 1)])
        self.assertEqual(i['uint8'], 1)
        self.assertTrue('one' not in i)

        i.update_existing(one=1, uint8=2)
        self.assertTrue('one' not in i)
        self.assertEqual(i['uint8'], 2)
        self.assertTrue(isinstance(i['uint8'], Uint8))
        self.assertEqual(i['uint8'], Uint8(2))
        self.assertEqual(i['uint8'], 2)

        i.update_existing(Uint8Array=[3, 4, 5], foo=[1, 2])
        self.assertTrue('foo' not in i)
        self.assertEqual(i['uint8array'], [3, 4, 5])
        self.assertTrue(isinstance(i['uint8array'][0], Uint8))

        name = CIMInstanceName('CIM_Foo',
                               keybindings={'string': 'STRING', 'one': '1'})

        i.update_existing(name)
        self.assertTrue('one' not in i)
        self.assertEqual(i['string'], 'STRING')


class InitCIMProperty(unittest.TestCase, CIMObjectMixin):
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

    # pylint: disable=too-many-branches
    def test_all(self):

        # Note: The inferring of the type attribute of CIMProperty changed over
        # time: Before pywbem 0.8.1, a value of None required specifying a
        # type. In 0.8.1, a rather complex logic was implemented that tried to
        # be perfect in inferring unspecified input properties, at the price of
        # considerable complexity. In 0.12.0, this complex logic was
        # drastically simplified again. Some cases are still nicely inferred,
        # but some less common cases now require specifying the type again.

        quals = {'Key': CIMQualifier('Key', True)}

        # Initialization with name being None

        # Starting with 0.8.1, the implementation enforced name to be non-None
        with self.assertRaises(ValueError):
            CIMProperty(None, 42)

        # Initialization to CIM string type

        p = CIMProperty('Spotty', 'Foot')
        self.assertCIMProperty(p, 'Spotty', 'Foot', 'string')

        p = CIMProperty(name='Spotty', value='Foot')
        self.assertCIMProperty(p, 'Spotty', 'Foot', 'string')

        p = CIMProperty('Spotty', 'Foot', 'string')
        self.assertCIMProperty(p, 'Spotty', 'Foot', 'string')

        p = CIMProperty('Spotty', 'Foot', type='string')
        self.assertCIMProperty(p, 'Spotty', 'Foot', 'string')

        p = CIMProperty('Spotty', None, type='string')
        self.assertCIMProperty(p, 'Spotty', None, 'string')

        p = CIMProperty(u'Name', u'Brad')
        self.assertCIMProperty(p, u'Name', u'Brad', 'string')

        p = CIMProperty('Spotty', 'Foot', qualifiers=quals)
        self.assertCIMProperty(p, 'Spotty', 'Foot', 'string', qualifiers=quals)

        p = CIMProperty('Spotty', None, 'string', qualifiers=quals)
        self.assertCIMProperty(p, 'Spotty', None, 'string', qualifiers=quals)

        # Initialization to CIM integer and real types

        p = CIMProperty('Age', Uint16(32))
        self.assertCIMProperty(p, 'Age', 32, 'uint16')

        p = CIMProperty('Age', Uint16(32), 'uint16')
        self.assertCIMProperty(p, 'Age', 32, 'uint16')

        p = CIMProperty('Age', Real32(32.0))
        self.assertCIMProperty(p, 'Age', 32.0, 'real32')

        p = CIMProperty('Age', Real32(32.0), 'real32')
        self.assertCIMProperty(p, 'Age', 32.0, 'real32')

        for type_ in InitCIMProperty._INT_TYPES + InitCIMProperty._REAL_TYPES:

            p = CIMProperty('Age', 32, type_)
            self.assertCIMProperty(p, 'Age', 32, type_)

            p = CIMProperty('Age', None, type_)
            self.assertCIMProperty(p, 'Age', None, type_)

        for type_ in InitCIMProperty._REAL_TYPES:

            p = CIMProperty('Age', 32.0, type_)
            self.assertCIMProperty(p, 'Age', 32.0, type_)

        # Initialization to CIM boolean type

        p = CIMProperty('Aged', True)
        self.assertCIMProperty(p, 'Aged', True, 'boolean')

        p = CIMProperty('Aged', True, 'boolean')
        self.assertCIMProperty(p, 'Aged', True, 'boolean')

        p = CIMProperty('Aged', False)
        self.assertCIMProperty(p, 'Aged', False, 'boolean')

        p = CIMProperty('Aged', False, 'boolean')
        self.assertCIMProperty(p, 'Aged', False, 'boolean')

        p = CIMProperty('Aged', None, 'boolean')
        self.assertCIMProperty(p, 'Aged', None, 'boolean')

        # Initialization to CIM datetime type

        timedelta_1 = timedelta(days=12345678, hours=22, minutes=44,
                                seconds=55, microseconds=654321)
        cim_datetime_1 = '12345678224455.654321:000'

        # This test failed in the pre-0.8.1 implementation, because
        # the timedelta object was not converted to a CIMDateTime object.
        p = CIMProperty('Age', timedelta_1)
        self.assertCIMProperty(p, 'Age', CIMDateTime(cim_datetime_1),
                               'datetime')

        # This test failed in the pre-0.8.1 implementation, because the
        # timedelta object was not converted to a CIMDateTime object.
        p = CIMProperty('Age', timedelta_1, 'datetime')
        self.assertCIMProperty(p, 'Age', CIMDateTime(cim_datetime_1),
                               'datetime')

        p = CIMProperty('Age', CIMDateTime(timedelta_1))
        self.assertCIMProperty(p, 'Age', CIMDateTime(cim_datetime_1),
                               'datetime')

        p = CIMProperty('Age', CIMDateTime(timedelta_1), 'datetime')
        self.assertCIMProperty(p, 'Age', CIMDateTime(cim_datetime_1),
                               'datetime')

        # This test failed in the pre-0.8.1 implementation, because the
        # datetime formatted string was not converted to a CIMDateTime object.
        p = CIMProperty('Age', cim_datetime_1, 'datetime')
        self.assertCIMProperty(p, 'Age', CIMDateTime(cim_datetime_1),
                               'datetime')

        p = CIMProperty('Age', CIMDateTime(cim_datetime_1))
        self.assertCIMProperty(p, 'Age', CIMDateTime(cim_datetime_1),
                               'datetime')

        p = CIMProperty('Age', CIMDateTime(cim_datetime_1), 'datetime')
        self.assertCIMProperty(p, 'Age', CIMDateTime(cim_datetime_1),
                               'datetime')

        datetime_2 = datetime(year=2014, month=9, day=24, hour=19, minute=30,
                              second=40, microsecond=654321,
                              tzinfo=cim_types.MinutesFromUTC(120))
        cim_datetime_2 = '20140924193040.654321+120'

        # This test failed in the pre-0.8.1 implementation, because the
        # datetime object was not converted to a CIMDateTime object.
        p = CIMProperty('Age', datetime_2)
        self.assertCIMProperty(p, 'Age', CIMDateTime(cim_datetime_2),
                               'datetime')

        # This test failed in the pre-0.8.1 implementation, because the
        # datetime object was not converted to a CIMDateTime object.
        p = CIMProperty('Age', datetime_2, 'datetime')
        self.assertCIMProperty(p, 'Age', CIMDateTime(cim_datetime_2),
                               'datetime')

        p = CIMProperty('Age', CIMDateTime(datetime_2))
        self.assertCIMProperty(p, 'Age', CIMDateTime(cim_datetime_2),
                               'datetime')

        p = CIMProperty('Age', CIMDateTime(datetime_2), 'datetime')
        self.assertCIMProperty(p, 'Age', CIMDateTime(cim_datetime_2),
                               'datetime')

        # This test failed in the pre-0.8.1 implementation, because the
        # datetime formatted string was not converted to a CIMDateTime object.
        p = CIMProperty('Age', cim_datetime_2, 'datetime')
        self.assertCIMProperty(p, 'Age', CIMDateTime(cim_datetime_2),
                               'datetime')

        p = CIMProperty('Age', CIMDateTime(cim_datetime_2))
        self.assertCIMProperty(p, 'Age', CIMDateTime(cim_datetime_2),
                               'datetime')

        p = CIMProperty('Age', CIMDateTime(cim_datetime_2), 'datetime')
        self.assertCIMProperty(p, 'Age', CIMDateTime(cim_datetime_2),
                               'datetime')

        # Reference properties

        p = CIMProperty('Foo', None, 'reference')
        self.assertCIMProperty(p, 'Foo', None, 'reference',
                               reference_class=None)

        # This test failed in the pre-0.8.1 implementation, because the
        # reference_class argument was required to be provided for references.
        p = CIMProperty('Foo', CIMInstanceName('CIM_Foo'))
        self.assertCIMProperty(p, 'Foo', CIMInstanceName('CIM_Foo'),
                               'reference')

        # This test failed in the pre-0.8.1 implementation, because the
        # reference_class argument was required to be provided for references.
        p = CIMProperty('Foo', CIMInstanceName('CIM_Foo'), 'reference')
        self.assertCIMProperty(p, 'Foo', CIMInstanceName('CIM_Foo'),
                               'reference')

        # This test failed in the pre-0.8.1 implementation, because the
        # reference_class argument was required to be provided for references.
        p = CIMProperty('Foo', CIMInstanceName('CIM_Foo'),
                        qualifiers=quals)
        self.assertCIMProperty(p, 'Foo', CIMInstanceName('CIM_Foo'),
                               'reference', qualifiers=quals)

        # This test failed in the pre-0.8.1 implementation, because the
        # reference_class argument was required to be provided for references.
        p = CIMProperty('Foo', CIMInstanceName('CIM_Foo'), 'reference',
                        qualifiers=quals)
        self.assertCIMProperty(p, 'Foo', CIMInstanceName('CIM_Foo'),
                               'reference', qualifiers=quals)

        p = CIMProperty('Foo', CIMInstanceName('CIM_Foo'),
                        reference_class='CIM_Foo')
        self.assertCIMProperty(p, 'Foo', CIMInstanceName('CIM_Foo'),
                               'reference',
                               reference_class='CIM_Foo')

        # This is just a rough test whether a WBEM URI string will be converted
        # into a CIMInstanceName object. A more thorough test with variations
        # of WBEM URI strings is where CIMInstanceName.from_wbem_uri() is
        # tested.
        if CHECK_0_12_0:
            path_uri = 'https://10.11.12.13:5989/root/cimv2:' \
                       'CIM_Fo.k1="v1",k2="v2"'
            path_obj = CIMInstanceName('CIM_Fo',
                                       keybindings={'k1': 'v1', 'k2': 'v2'},
                                       namespace='root/cimv2',
                                       host='10.11.12.13:5989')
            p = CIMProperty('Foo', path_uri, 'reference',
                            reference_class='CIM_Fo')
            self.assertCIMProperty(p, 'Foo', path_obj, 'reference',
                                   reference_class='CIM_Fo')

        p = CIMProperty('Foo', CIMInstanceName('CIM_Foo'), 'reference',
                        reference_class='CIM_Foo')
        self.assertCIMProperty(p, 'Foo', CIMInstanceName('CIM_Foo'),
                               'reference',
                               reference_class='CIM_Foo')

        p = CIMProperty('Foo', CIMInstanceName('CIM_Foo'),
                        reference_class='CIM_Foo', qualifiers=quals)
        self.assertCIMProperty(p, 'Foo', CIMInstanceName('CIM_Foo'),
                               'reference',
                               reference_class='CIM_Foo', qualifiers=quals)

        p = CIMProperty('Foo', CIMInstanceName('CIM_Foo'),
                        'reference',
                        reference_class='CIM_Foo', qualifiers=quals)
        self.assertCIMProperty(p, 'Foo', CIMInstanceName('CIM_Foo'),
                               'reference',
                               reference_class='CIM_Foo', qualifiers=quals)

        # Initialization to CIM embedded object / instance

        # This test failed in the pre-0.8.1 implementation, succeeded in the
        # pre-0.12.0 implementation, and fails again from 0.12.0 on (because
        # type is required):
        if CHECK_0_12_0:
            with self.assertRaises(ValueError):
                CIMProperty('Bar', None, embedded_object='object')
        else:  # starting with 0.8.1
            p = CIMProperty('Bar', None, embedded_object='object')
            self.assertCIMProperty(p, 'Bar', None, 'string',
                                   embedded_object='object')

        p = CIMProperty('Bar', None, 'string', embedded_object='object')
        self.assertCIMProperty(p, 'Bar', None, 'string',
                               embedded_object='object')

        ec = CIMClass('CIM_Bar')

        p = CIMProperty('Bar', ec)
        self.assertCIMProperty(p, 'Bar', ec, 'string', embedded_object='object')

        # This test failed in the pre-0.8.1 implementation, because the
        # embedded_object attribute was not implied from the value argument if
        # the type argument was also provided.
        p = CIMProperty('Bar', ec, 'string')
        self.assertCIMProperty(p, 'Bar', ec, 'string',
                               embedded_object='object')

        p = CIMProperty('Bar', ec, embedded_object='object')
        self.assertCIMProperty(p, 'Bar', ec, 'string',
                               embedded_object='object')

        p = CIMProperty('Bar', ec, 'string', embedded_object='object')
        self.assertCIMProperty(p, 'Bar', ec, 'string',
                               embedded_object='object')

        ei = CIMInstance('CIM_Bar')

        # This test failed in the pre-0.8.1 implementation, because the
        # embedded_object argument value of 'object' was changed to 'instance'
        # when a CIMInstance typed value was provided.
        p = CIMProperty('Bar', ei, embedded_object='object')
        self.assertCIMProperty(p, 'Bar', ei, 'string',
                               embedded_object='object')

        p = CIMProperty('Bar', ei, 'string', embedded_object='object')
        self.assertCIMProperty(p, 'Bar', ei, 'string',
                               embedded_object='object')

        p = CIMProperty('Bar', ei)
        self.assertCIMProperty(p, 'Bar', ei, 'string',
                               embedded_object='instance')

        # This test failed in the pre-0.8.1 implementation, because the
        # embedded_object attribute was not implied from the value argument if
        # the type argument was also provided.
        p = CIMProperty('Bar', ei, 'string')
        self.assertCIMProperty(p, 'Bar', ei, 'string',
                               embedded_object='instance')

        p = CIMProperty('Bar', ei, embedded_object='instance')
        self.assertCIMProperty(p, 'Bar', ei, 'string',
                               embedded_object='instance')

        p = CIMProperty('Bar', ei, 'string', embedded_object='instance')
        self.assertCIMProperty(p, 'Bar', ei, 'string',
                               embedded_object='instance')

        # Invalid embedded_object value

        with self.assertRaises(ValueError):
            CIMProperty('Bar', value=None, type='string',
                        embedded_object='objectx')

        # Invalid CIM type for an embedded object

        with self.assertRaises(ValueError):
            CIMProperty('Bar', value=None, type='reference',
                        embedded_object='object')

        # Invalid value for an embedded object

        invalid_eo = CIMProperty('Boo', '')

        with self.assertRaises(ValueError):
            CIMProperty('Bar', value=invalid_eo, type='string',
                        embedded_object='object')

        with self.assertRaises(ValueError):
            CIMProperty('Bar', value=[invalid_eo], type='string',
                        embedded_object='object')

        # Check that initialization with Null without specifying a type is
        # rejected

        with self.assertRaises(ValueError):
            CIMProperty('Spotty', None)

        # Initialize with int, float and long, without specifying a type

        with self.assertRaises(ValueError if CHECK_0_12_0 else TypeError):
            CIMProperty('Age', 42)

        with self.assertRaises(ValueError if CHECK_0_12_0 else TypeError):
            CIMProperty('Age', 42.1)

        if six.PY2:
            with self.assertRaises(ValueError if CHECK_0_12_0 else TypeError):
                CIMProperty('Age', long(42))  # noqa: F821

        # Arrays with unspecified is_array

        # Check that a value of None results in a scalar
        p = CIMProperty('Foo', None, 'uint32', is_array=None)
        self.assertEqual(p.is_array, False)

        # Check that a scalar value results in a scalar
        p = CIMProperty('Foo', 42, 'uint32', is_array=None)
        self.assertEqual(p.is_array, False)

        # Check that an array value results in an array
        p = CIMProperty('Foo', [42], 'uint32', is_array=None)
        self.assertEqual(p.is_array, True)

        # Arrays of CIM string and numeric types

        p = CIMProperty('Foo', None, 'string', is_array=True)
        self.assertCIMProperty(p, 'Foo', None, 'string', is_array=True)

        p = CIMProperty('Foo', [], 'string')
        self.assertCIMProperty(p, 'Foo', [], 'string', is_array=True)

        p = CIMProperty('Foo', [], 'string', is_array=True)
        self.assertCIMProperty(p, 'Foo', [], 'string', is_array=True)

        p = CIMProperty('Foo', [None], 'string')
        self.assertCIMProperty(p, 'Foo', [None], 'string', is_array=True)

        p = CIMProperty('Foo', [None], 'string', is_array=True)
        self.assertCIMProperty(p, 'Foo', [None], 'string', is_array=True)

        p = CIMProperty('Foo', [Uint8(x) for x in [1, 2, 3]])
        self.assertCIMProperty(p, 'Foo', [Uint8(x) for x in [1, 2, 3]],
                               'uint8', is_array=True)

        p = CIMProperty('Foo', [Uint8(x) for x in [1, 2, 3]], is_array=True)
        self.assertCIMProperty(p, 'Foo', [Uint8(x) for x in [1, 2, 3]],
                               'uint8', is_array=True)

        p = CIMProperty('Foo', [Uint8(x) for x in [1, 2, 3]], type='uint8')
        self.assertCIMProperty(p, 'Foo', [Uint8(x) for x in [1, 2, 3]],
                               'uint8', is_array=True)

        p = CIMProperty('Foo', [Uint8(x) for x in [1, 2, 3]], qualifiers=quals)
        self.assertCIMProperty(p, 'Foo', [Uint8(x) for x in [1, 2, 3]],
                               'uint8', is_array=True, qualifiers=quals)

        # Arrays of CIM boolean type

        p = CIMProperty('Aged', [True])
        self.assertCIMProperty(p, 'Aged', [True], 'boolean', is_array=True)

        p = CIMProperty('Aged', [False, True], 'boolean')
        self.assertCIMProperty(p, 'Aged', [False, True], 'boolean',
                               is_array=True)

        p = CIMProperty('Aged', [None], 'boolean')
        self.assertCIMProperty(p, 'Aged', [None], 'boolean', is_array=True)

        p = CIMProperty('Aged', [], 'boolean')
        self.assertCIMProperty(p, 'Aged', [], 'boolean', is_array=True)

        # Arrays of CIM datetime type

        timedelta_1 = timedelta(days=12345678, hours=22, minutes=44,
                                seconds=55, microseconds=654321)
        cim_datetime_1 = '12345678224455.654321:000'

        # This test failed in the pre-0.8.1 implementation, because the
        # timedelta object was not converted to a CIMDateTime object.
        p = CIMProperty('Age', [timedelta_1])
        self.assertCIMProperty(p, 'Age', [CIMDateTime(cim_datetime_1)],
                               'datetime', is_array=True)

        # This test failed in the pre-0.8.1 implementation, because the
        # timedelta object was not converted to a CIMDateTime object.
        p = CIMProperty('Age', [timedelta_1], 'datetime')
        self.assertCIMProperty(p, 'Age', [CIMDateTime(cim_datetime_1)],
                               'datetime', is_array=True)

        p = CIMProperty('Age', [CIMDateTime(timedelta_1)])
        self.assertCIMProperty(p, 'Age', [CIMDateTime(cim_datetime_1)],
                               'datetime', is_array=True)

        p = CIMProperty('Age', [CIMDateTime(timedelta_1)], 'datetime')
        self.assertCIMProperty(p, 'Age', [CIMDateTime(cim_datetime_1)],
                               'datetime', is_array=True)

        # This test failed in the pre-0.8.1 implementation, because the
        # datetime formatted string was not converted to a CIMDateTime object.
        p = CIMProperty('Age', [cim_datetime_1], 'datetime')
        self.assertCIMProperty(p, 'Age', [CIMDateTime(cim_datetime_1)],
                               'datetime', is_array=True)

        p = CIMProperty('Age', [CIMDateTime(cim_datetime_1)])
        self.assertCIMProperty(p, 'Age', [CIMDateTime(cim_datetime_1)],
                               'datetime', is_array=True)

        p = CIMProperty('Age', [CIMDateTime(cim_datetime_1)], 'datetime')
        self.assertCIMProperty(p, 'Age', [CIMDateTime(cim_datetime_1)],
                               'datetime', is_array=True)

        p = CIMProperty('Age', [None], 'datetime')
        self.assertCIMProperty(p, 'Age', [None], 'datetime', is_array=True)

        datetime_2 = datetime(year=2014, month=9, day=24, hour=19, minute=30,
                              second=40, microsecond=654321,
                              tzinfo=cim_types.MinutesFromUTC(120))
        cim_datetime_2 = '20140924193040.654321+120'

        # This test failed in the pre-0.8.1 implementation, because the
        # datetime object was not converted to a CIMDateTime object.
        p = CIMProperty('Age', [datetime_2])
        self.assertCIMProperty(p, 'Age', [CIMDateTime(cim_datetime_2)],
                               'datetime', is_array=True)

        # This test failed in the pre-0.8.1 implementation, because the
        # datetime object was not converted to a CIMDateTime object.
        p = CIMProperty('Age', [datetime_2], 'datetime')
        self.assertCIMProperty(p, 'Age', [CIMDateTime(cim_datetime_2)],
                               'datetime', is_array=True)

        p = CIMProperty('Age', [CIMDateTime(datetime_2)])
        self.assertCIMProperty(p, 'Age', [CIMDateTime(cim_datetime_2)],
                               'datetime', is_array=True)

        p = CIMProperty('Age', [CIMDateTime(datetime_2)], 'datetime')
        self.assertCIMProperty(p, 'Age', [CIMDateTime(cim_datetime_2)],
                               'datetime', is_array=True)

        # This test failed in the pre-0.8.1 implementation, because the
        # datetime formatted string was not converted to a CIMDateTime object.
        p = CIMProperty('Age', [cim_datetime_2], 'datetime')
        self.assertCIMProperty(p, 'Age', [CIMDateTime(cim_datetime_2)],
                               'datetime', is_array=True)

        p = CIMProperty('Age', [CIMDateTime(cim_datetime_2)])
        self.assertCIMProperty(p, 'Age', [CIMDateTime(cim_datetime_2)],
                               'datetime', is_array=True)

        p = CIMProperty('Age', [CIMDateTime(cim_datetime_2)], 'datetime')
        self.assertCIMProperty(p, 'Age', [CIMDateTime(cim_datetime_2)],
                               'datetime', is_array=True)

        # Arrays of reference properties are not allowed in CIM v2.

        with self.assertRaises(ValueError):
            CIMProperty('Bar', [None], 'reference',
                        reference_class='CIM_Foo')

        # Arrays of CIM embedded objects / instances

        # This test failed in the pre-0.8.1 implementation (because the first
        # array element was used for defaulting the type, without checking for
        # None), succeeded in the pre-0.12.0 implementation, and fails again
        # from 0.12.0 on (because type is required when no value is provided):
        if CHECK_0_12_0:
            with self.assertRaises(ValueError):
                CIMProperty('Bar', [None], embedded_object='object')
        else:  # starting with 0.8.1
            p = CIMProperty('Bar', [None], embedded_object='object')
            self.assertCIMProperty(p, 'Bar', [None], 'string',
                                   embedded_object='object',
                                   is_array=True)

        p = CIMProperty('Bar', [None], 'string', embedded_object='object')
        self.assertCIMProperty(p, 'Bar', [None], 'string',
                               embedded_object='object',
                               is_array=True)

        # This test failed in the pre-0.8.1 implementation (because the type of
        # the empty array could not be inferred from the embedded_object
        # argument), succeeded in the pre-0.12.0 implementation, and fails
        # again from 0.12.0 on (because type is required when no value is
        # provided in the array):
        if CHECK_0_12_0:
            with self.assertRaises(ValueError):
                CIMProperty('Bar', [], embedded_object='object')
        else:  # starting with 0.8.1
            p = CIMProperty('Bar', [], embedded_object='object')
            self.assertCIMProperty(p, 'Bar', [], 'string',
                                   embedded_object='object',
                                   is_array=True)

        p = CIMProperty('Bar', [], 'string', embedded_object='object')
        self.assertCIMProperty(p, 'Bar', [], 'string',
                               embedded_object='object',
                               is_array=True)

        ec = CIMClass('CIM_Bar')

        p = CIMProperty('Bar', [ec])
        self.assertCIMProperty(p, 'Bar', [ec], 'string',
                               embedded_object='object',
                               is_array=True)

        # This test failed in the pre-0.8.1 implementation, because the
        # embedded_object attribute was not implied from the value argument if
        # the type argument was also provided.
        p = CIMProperty('Bar', [ec], 'string')
        self.assertCIMProperty(p, 'Bar', [ec], 'string',
                               embedded_object='object',
                               is_array=True)

        p = CIMProperty('Bar', [ec], embedded_object='object')
        self.assertCIMProperty(p, 'Bar', [ec], 'string',
                               embedded_object='object',
                               is_array=True)

        p = CIMProperty('Bar', [ec], 'string', embedded_object='object')
        self.assertCIMProperty(p, 'Bar', [ec], 'string',
                               embedded_object='object',
                               is_array=True)

        ei = CIMInstance('CIM_Bar')

        # This test failed in the pre-0.8.1 implementation, because the
        # embedded_object argument value of 'object' was changed to 'instance'
        # when a CIMInstance typed value was provided.
        p = CIMProperty('Bar', [ei], embedded_object='object')
        self.assertCIMProperty(p, 'Bar', [ei], 'string',
                               embedded_object='object',
                               is_array=True)

        p = CIMProperty('Bar', [ei], 'string', embedded_object='object')
        self.assertCIMProperty(p, 'Bar', [ei], 'string',
                               embedded_object='object',
                               is_array=True)

        p = CIMProperty('Bar', [ei])
        self.assertCIMProperty(p, 'Bar', [ei], 'string',
                               embedded_object='instance',
                               is_array=True)

        # This test failed in the pre-0.8.1 implementation, because the
        # embedded_object attribute was not implied from the value argument if
        # the type argument was also provided.
        p = CIMProperty('Bar', [ei], 'string')
        self.assertCIMProperty(p, 'Bar', [ei], 'string',
                               embedded_object='instance',
                               is_array=True)

        p = CIMProperty('Bar', [ei], embedded_object='instance')
        self.assertCIMProperty(p, 'Bar', [ei], 'string',
                               embedded_object='instance',
                               is_array=True)

        p = CIMProperty('Bar', [ei], 'string', embedded_object='instance')
        self.assertCIMProperty(p, 'Bar', [ei], 'string',
                               embedded_object='instance',
                               is_array=True)

        # Check that initialization with certain invalid arrays without
        # specifying a type is rejected

        with self.assertRaises(ValueError):
            CIMProperty('Foo', None, is_array=True)

        with self.assertRaises(ValueError):
            CIMProperty('Foo', [], is_array=True)

        with self.assertRaises(ValueError):
            CIMProperty('Foo', [None], is_array=True)

        with self.assertRaises(ValueError):
            CIMProperty('Foo', [None, "abc"], is_array=True)

        with self.assertRaises(ValueError):
            CIMProperty('Foo', [])

        with self.assertRaises(ValueError):
            CIMProperty('Foo', [None])

        with self.assertRaises(ValueError):
            CIMProperty('Foo', [None, "abc"])

        # Initialize with arrays of int, float and long, without type

        with self.assertRaises(ValueError if CHECK_0_12_0 else TypeError):
            CIMProperty('Foo', [1, 2, 3])

        with self.assertRaises(ValueError if CHECK_0_12_0 else TypeError):
            CIMProperty('Foo', [1.0, 2.0])

        if six.PY2:
            with self.assertRaises(ValueError if CHECK_0_12_0 else TypeError):
                CIMProperty('Foo', [long(42), long(43)])  # noqa: F821

        # Check that the documented examples don't fail:

        CIMProperty("MyString", "abc")

        if CHECK_0_12_0:
            p = CIMProperty("MyNum", 42, "uint8")
            self.assertCIMProperty(p, 'MyNum', Uint8(42), 'uint8')
        else:
            p = CIMProperty("MyNum", 42, "uint8")
            self.assertCIMProperty(p, 'MyNum', 42, 'uint8')

        CIMProperty("MyNum", Uint8(42))
        CIMProperty("MyNumArray", [1, 2, 3], "uint8")
        CIMProperty("MyRef", CIMInstanceName("Foo"))
        CIMProperty("MyEmbObj", CIMClass("Foo"))
        CIMProperty("MyEmbObj", CIMInstance("Foo"),
                    embedded_object="object")
        CIMProperty("MyEmbInst", CIMInstance("Foo"))
        CIMProperty("MyString", None, "string")
        CIMProperty("MyNum", None, "uint8")
        CIMProperty("MyRef", None, "reference", reference_class="MyClass")
        CIMProperty("MyEmbObj", None, "string", embedded_object="object")
        CIMProperty("MyEmbInst", None, "string",
                    embedded_object="instance")


class CopyCIMProperty(unittest.TestCase, CIMObjectMixin):

    def test_all(self):

        p = CIMProperty('Spotty', 'Foot')
        c = p.copy()

        self.assertEqual(p, c)

        c.name = '1234'
        c.value = '1234'
        c.qualifiers = {'Key': CIMQualifier('Value', True)}

        self.assertCIMProperty(p, 'Spotty', 'Foot', type_='string',
                               qualifiers={})


class CIMPropertyAttrs(unittest.TestCase, CIMObjectMixin):

    def test_all(self):

        # Attributes for single-valued property

        obj = CIMProperty('Spotty', 'Foot')
        self.assertCIMProperty(obj, 'Spotty', 'Foot', type_='string')

        # Attributes for array property

        v = [Uint8(x) for x in [1, 2, 3]]
        obj = CIMProperty('Foo', v)
        self.assertCIMProperty(obj, 'Foo', v, type_='uint8', is_array=True)

        # Attributes for property reference

        # This test failed in the pre-0.8.1 implementation, because the
        # reference_class argument was required to be provided for references.
        v = CIMInstanceName('CIM_Bar')
        obj = CIMProperty('Foo', v)
        self.assertCIMProperty(obj, 'Foo', v, type_='reference')

        if CHECK_0_12_0:
            # Check that name cannot be set to None
            with self.assertRaises(ValueError):
                obj.name = None
        else:
            # Before 0.12.0, the implementation allowed the name to be
            # None, although the documentation required it not to be None.
            # We test the implemented behavior.
            obj.name = None
            self.assertIs(obj.name, None)


class CIMPropertyEquality(unittest.TestCase):

    def test_all(self):

        # Compare single-valued properties

        self.assertEqual(CIMProperty('Spotty', None, 'string'),
                         CIMProperty('Spotty', None, 'string'))

        self.assertNotEqual(CIMProperty('Spotty', '', 'string'),
                            CIMProperty('Spotty', None, 'string'))

        self.assertEqual(CIMProperty('Spotty', 'Foot'),
                         CIMProperty('Spotty', 'Foot'))

        self.assertNotEqual(CIMProperty('Spotty', 'Foot'),
                            CIMProperty('Spotty', Uint32(42)))

        self.assertEqual(CIMProperty('Spotty', 'Foot'),
                         CIMProperty('spotty', 'Foot'))

        self.assertNotEqual(CIMProperty('Spotty', 'Foot'),
                            CIMProperty('Spotty', 'Foot',
                                        qualifiers={'Key':
                                                    CIMQualifier('Key',
                                                                 True)}))

        # Compare property arrays

        self.assertEqual(
            CIMProperty('Array', None, 'uint8', is_array=True),
            CIMProperty('array', None, 'uint8', is_array=True))

        self.assertEqual(
            CIMProperty('Array', [Uint8(x) for x in [1, 2, 3]]),
            CIMProperty('Array', [Uint8(x) for x in [1, 2, 3]]))

        self.assertNotEqual(
            CIMProperty('Array', [Uint8(x) for x in [1, 2, 3]]),
            CIMProperty('Array', [Uint16(x) for x in [1, 2, 3]]))

        self.assertNotEqual(
            CIMProperty('Array', [Uint8(x) for x in [1, 2, 3]]),
            CIMProperty('Array', [Uint16(x) for x in [1, 2, 3]],
                        qualifiers={'Key': CIMQualifier('Key', True)}))

        # Compare property references

        self.assertEqual(
            CIMProperty('Foo', CIMInstanceName('CIM_Foo')),
            CIMProperty('Foo', CIMInstanceName('CIM_Foo')))

        self.assertEqual(
            CIMProperty('Foo', CIMInstanceName('CIM_Foo')),
            CIMProperty('foo', CIMInstanceName('CIM_Foo')))

        self.assertNotEqual(
            CIMProperty('Foo', CIMInstanceName('CIM_Foo')),
            CIMProperty('foo', None, type='reference'))

        self.assertNotEqual(
            CIMProperty('Foo', CIMInstanceName('CIM_Foo')),
            CIMProperty('Foo', CIMInstanceName('CIM_Foo'),
                        qualifiers={'Key': CIMQualifier('Key', True)}))

        # Basic reference_class test

        self.assertEqual(CIMProperty('Foo', CIMInstanceName('CIM_Foo'),
                                     reference_class='CIM_FooBase'),
                         CIMProperty('Foo', CIMInstanceName('CIM_Foo'),
                                     reference_class='CIM_FooBase'))

        # reference_class should be compared case insensitive

        self.assertEqual(CIMProperty('Foo', CIMInstanceName('CIM_Foo'),
                                     reference_class='CIM_FooBase'),
                         CIMProperty('Foo', CIMInstanceName('CIM_Foo'),
                                     reference_class='CIM_FoObAsE'))

        # reference_class None

        self.assertNotEqual(CIMProperty('Foo', CIMInstanceName('CIM_Foo'),
                                        reference_class=None),
                            CIMProperty('Foo', CIMInstanceName('CIM_Foo'),
                                        reference_class='CIM_FoObAsE'))

        self.assertNotEqual(CIMProperty('Foo', CIMInstanceName('CIM_Foo'),
                                        reference_class='CIM_FoObAsE'),
                            CIMProperty('Foo', CIMInstanceName('CIM_Foo'),
                                        reference_class=None))

        self.assertEqual(CIMProperty('Foo', CIMInstanceName('CIM_Foo'),
                                     reference_class=None),
                         CIMProperty('Foo', CIMInstanceName('CIM_Foo'),
                                     reference_class=None))

        # Verify detection of incorrect type of second object

        with pytest.raises(TypeError):
            # pylint: disable=expression-not-assigned
            CIMProperty('Foo', 'abc') == 'abc'

        with pytest.raises(TypeError):
            # pylint: disable=expression-not-assigned
            CIMProperty('Foo', Uint8(42)) == 42


class CIMPropertyCompare(unittest.TestCase):

    @unimplemented
    def test_all(self):
        # TODO Implement ordering comparison test for CIMProperty
        raise AssertionError("test not implemented")


class CIMPropertySort(unittest.TestCase):

    @unimplemented
    def test_all(self):
        # TODO Implement sorting test for CIMProperty
        raise AssertionError("test not implemented")


class Test_CIMProperty_str(object):
    """
    Test `CIMProperty.__str__()`.
    """

    def test_all(self):

        obj = CIMProperty('Spotty', 'Foot', type='string')

        s = str(obj)

        assert re.match(r'^CIMProperty\(', s)
        assert 'name=%r' % obj.name in s
        assert 'value=%r' % obj.value in s
        assert 'type=%r' % obj.type in s
        assert 'reference_class=%r' % obj.reference_class in s
        assert 'embedded_object=%r' % obj.embedded_object in s
        assert 'is_array=%r' % obj.is_array in s


class Test_CIMProperty_repr(object):
    """
    Test `CIMProperty.__repr__()`.
    """

    def test_all(self):

        obj = CIMProperty('Spotty', 'Foot', type='string')

        r = repr(obj)

        assert re.match(r'^CIMProperty\(', r)
        assert 'name=%r' % obj.name in r
        assert 'value=%r' % obj.value in r
        assert 'type=%r' % obj.type in r
        assert 'reference_class=%r' % obj.reference_class in r
        assert 'embedded_object=%r' % obj.embedded_object in r
        assert 'is_array=%r' % obj.is_array in r
        assert 'array_size=%r' % obj.array_size in r
        assert 'class_origin=%r' % obj.class_origin in r
        assert 'propagated=%r' % obj.propagated in r
        assert 'qualifiers=' in r


class CIMPropertyToXML(ValidationTestCase):
    """Test valid XML is generated for various CIMProperty objects."""

    def test_all(self):

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


class InitCIMQualifier(unittest.TestCase):
    """Test initialising a CIMQualifier object."""

    def test_all(self):

        # Initialization with name being None

        if CHECK_0_12_0:
            with self.assertRaises(ValueError):
                CIMQualifier(None, None, 'string')
        else:
            # Before 0.12.0, the implementation allowed the name to be None,
            # although the documentation required it not to be None.
            # We test the implemented behavior
            q = CIMQualifier(None, None, 'string')
            self.assertIs(q.name, None)

        # Initialization with type being None

        q = CIMQualifier('Qoo', u'bla')
        assert q.type == 'string'

        q = CIMQualifier('Qoo', b'bla')
        assert q.type == 'string'

        q = CIMQualifier('Qoo', True)
        assert q.type == 'boolean'

        q = CIMQualifier('Qoo', False)
        assert q.type == 'boolean'

        q = CIMQualifier('Qoo', [u'bla'])
        assert q.type == 'string'

        q = CIMQualifier('Qoo', [b'bla'])
        assert q.type == 'string'

        q = CIMQualifier('Qoo', [True])
        assert q.type == 'boolean'

        q = CIMQualifier('Qoo', [False])
        assert q.type == 'boolean'

        # Initialize with type being None and value not being type-derivable

        with self.assertRaises(ValueError if CHECK_0_12_0 else TypeError):
            CIMQualifier('Qoo', None)

        with self.assertRaises(ValueError if CHECK_0_12_0 else TypeError):
            CIMQualifier('Qoo', [None])

        with self.assertRaises(ValueError if CHECK_0_12_0 else TypeError):
            CIMQualifier('Qoo', [])

        # Initialize with type being None and value being int, float and long

        with self.assertRaises(ValueError if CHECK_0_12_0 else TypeError):
            CIMQualifier('Qoo', 42)

        with self.assertRaises(ValueError if CHECK_0_12_0 else TypeError):
            CIMQualifier('Qoo', 42.1)

        if six.PY2:
            with self.assertRaises(ValueError if CHECK_0_12_0 else TypeError):
                CIMQualifier('Qoo', long(42))  # noqa: F821

        # Some normal cases

        CIMQualifier('Revision', '2.7.0', 'string')
        CIMQualifier('RevisionList', ['1', '2', '3'], propagated=False)
        CIMQualifier('Null', None, 'string')

        # Check that the documented examples don't fail:

        CIMQualifier("MyString", "abc")

        if CHECK_0_12_0:
            q = CIMQualifier("MyNum", 42, "uint8")
            self.assertEqual(q.value, Uint8(42))
        else:
            with self.assertRaises(TypeError):
                CIMQualifier("MyNum", 42, "uint8")

        CIMQualifier("MyNum", Uint8(42))
        CIMQualifier("MyNumArray", [1, 2, 3], "uint8")
        CIMQualifier("MyString", None, "string")
        CIMQualifier("MyNum", None, "uint8")


class CopyCIMQualifier(unittest.TestCase):

    def test_all(self):

        q = CIMQualifier('Revision', '2.7.0', 'string')
        c = q.copy()

        self.assertEqual(q, c)

        c.name = 'Fooble'
        c.value = 'eep'

        self.assertEqual(q.name, 'Revision')


class CIMQualifierAttrs(unittest.TestCase):
    """Test attributes of CIMQualifier object."""

    def test_all(self):

        q = CIMQualifier('Revision', '2.7.0')

        self.assertEqual(q.name, 'Revision')
        self.assertEqual(q.value, '2.7.0')

        self.assertEqual(q.propagated, None)
        self.assertEqual(q.overridable, None)
        self.assertEqual(q.tosubclass, None)
        self.assertEqual(q.toinstance, None)
        self.assertEqual(q.translatable, None)

        q = CIMQualifier('RevisionList',
                         [Uint8(x) for x in [1, 2, 3]],
                         propagated=False)

        self.assertEqual(q.name, 'RevisionList')
        self.assertEqual(q.value, [1, 2, 3])
        self.assertEqual(q.propagated, False)

        if CHECK_0_12_0:
            # Check that name cannot be set to None
            with self.assertRaises(ValueError):
                q.name = None
        else:
            # Before 0.12.0, the implementation allowed the name to be
            # None, although the documentation required it not to be None.
            # We test the implemented behavior.
            q.name = None
            self.assertIs(q.name, None)


class CIMQualifierEquality(unittest.TestCase):
    """Compare CIMQualifier objects."""

    def test_all(self):

        self.assertEqual(CIMQualifier('Spotty', 'Foot'),
                         CIMQualifier('Spotty', 'Foot'))

        self.assertEqual(CIMQualifier('Spotty', 'Foot'),
                         CIMQualifier('spotty', 'Foot'))

        self.assertNotEqual(CIMQualifier('Spotty', 'Foot'),
                            CIMQualifier('Spotty', 'foot'))

        self.assertNotEqual(CIMQualifier('Null', None, type='string'),
                            CIMQualifier('Null', ''))

        # Verify detection of incorrect type of second object

        with pytest.raises(TypeError):
            # pylint: disable=expression-not-assigned
            CIMQualifier('Foo', 'abc') == 'abc'

        with pytest.raises(TypeError):
            # pylint: disable=expression-not-assigned
            CIMQualifier('Foo', Uint8(42)) == 42


class CIMQualifierCompare(unittest.TestCase):

    @unimplemented
    def test_all(self):
        # TODO Implement ordering comparison test for CIMQualifier
        raise AssertionError("test not implemented")


class CIMQualifierSort(unittest.TestCase):

    @unimplemented
    def test_all(self):
        # TODO Implement sorting test for CIMQualifier
        raise AssertionError("test not implemented")


class Test_CIMQualifier_str(object):
    """
    Test `CIMQualifier.__str__()`.
    """

    def test_all(self):

        obj = CIMQualifier('RevisionList', ['1', '2', '3'],
                           propagated=False)

        s = str(obj)

        assert re.match(r'^CIMQualifier\(', s)
        assert 'name=%r' % obj.name in s
        assert 'value=%r' % obj.value in s
        assert 'type=%r' % obj.type in s


class Test_CIMQualifier_repr(object):
    """
    Test `CIMQualifier.__repr__()`.
    """

    def test_all(self):

        obj = CIMQualifier('RevisionList', ['1', '2', '3'],
                           propagated=False)

        r = repr(obj)

        assert re.match(r'^CIMQualifier\(', r)
        assert 'name=%r' % obj.name in r
        assert 'value=%r' % obj.value in r
        assert 'type=%r' % obj.type in r
        assert 'tosubclass=%r' % obj.tosubclass in r
        assert 'overridable=%r' % obj.overridable in r
        assert 'translatable=%r' % obj.translatable in r
        assert 'toinstance=%r' % obj.toinstance in r
        assert 'propagated=%r' % obj.propagated in r


class CIMQualifierToXML(ValidationTestCase):

    def test_all(self):

        # XML root elements for CIM-XML representations of CIMQualifier
        root_elem_CIMQualifier = 'QUALIFIER'

        self.validate(CIMQualifier('Spotty', 'Foot'),
                      root_elem_CIMQualifier)

        self.validate(CIMQualifier('Revision', Real32(2.7)),
                      root_elem_CIMQualifier)

        self.validate(CIMQualifier('RevisionList',
                                   [Uint16(x) for x in [1, 2, 3]],
                                   propagated=False),
                      root_elem_CIMQualifier)


class InitCIMClassName(unittest.TestCase):

    def test_all(self):

        if CHECK_0_12_0:
            # Check that classname is enforced not to be None
            with self.assertRaises(ValueError):
                CIMClassName(None)
        else:
            # Check that classname is enforced not to be None
            with self.assertRaises(TypeError):
                CIMClassName(None)

        # Initialise with classname, superclass

        CIMClassName('CIM_Foo')
        CIMClassName('CIM_Foo', host='fred', namespace='root/blah')


class CopyCIMClassName(unittest.TestCase):

    def test_all(self):

        c = CIMClassName('CIM_Foo')
        co = c.copy()
        self.assertEqual(c, co)
        co.classname = 'CIM_Bar'
        self.assertEqual(c.classname, 'CIM_Foo')
        self.assertEqual(co.host, None)
        self.assertEqual(co.namespace, None)

        c = CIMClassName('CIM_Foo', host='fred', namespace='root/blah')
        co = c.copy()
        self.assertEqual(c, co)
        self.assertEqual(c.classname, 'CIM_Foo')
        self.assertEqual(co.host, 'fred')
        self.assertEqual(co.namespace, 'root/blah')


class CIMClassNameAttrs(unittest.TestCase):

    def test_all(self):

        obj = CIMClassName('CIM_Foo')

        self.assertEqual(obj.classname, 'CIM_Foo')
        self.assertEqual(obj.host, None)
        self.assertEqual(obj.namespace, None)

        obj = CIMClassName('CIM_Foo', host='fred', namespace='root/cimv2')

        self.assertEqual(obj.classname, 'CIM_Foo')
        self.assertEqual(obj.host, 'fred')
        self.assertEqual(obj.namespace, 'root/cimv2')

        if CHECK_0_12_0:
            # Check that classname cannot be set to None
            with self.assertRaises(ValueError):
                obj.classname = None
        else:
            # Before 0.12.0, the implementation allowed the classname to be
            # None, although the documentation required it not to be None.
            # We test the implemented behavior.
            obj.classname = None
            self.assertIs(obj.classname, None)

        # Verify detection of incorrect type of second object

        with pytest.raises(TypeError):
            # pylint: disable=expression-not-assigned
            CIMClassName('CIM_Foo') == 'http://abc:CIM_Foo'

        with pytest.raises(TypeError):
            # pylint: disable=expression-not-assigned
            CIMClassName('CIM_Foo') == CIMClass('CIM_Foo')


class CIMClassNameEquality(unittest.TestCase):

    def test_all(self):

        # Basic equality tests

        self.assertEqual(CIMClassName('CIM_Foo'),
                         CIMClassName('CIM_Foo'))

        # Class name should be case insensitive

        self.assertEqual(CIMClassName('CIM_Foo'),
                         CIMClassName('ciM_foO'))

        # Host name should be case insensitive

        self.assertEqual(CIMClassName('CIM_Foo', host='woot.com'),
                         CIMClassName('CIM_Foo', host='Woot.Com'))

        # Host name None

        self.assertNotEqual(CIMClassName('CIM_Foo', host=None),
                            CIMClassName('CIM_Foo', host='woot.com'))

        self.assertNotEqual(CIMClassName('CIM_Foo', host='woot.com'),
                            CIMClassName('CIM_Foo', host=None))

        self.assertEqual(CIMClassName('CIM_Foo', host=None),
                         CIMClassName('CIM_Foo', host=None))

        # Namespace should be case insensitive

        self.assertEqual(CIMClassName('CIM_Foo', namespace='root/cimv2'),
                         CIMClassName('CIM_Foo', namespace='Root/CIMv2'))

        # Namespace None

        self.assertNotEqual(CIMClassName('CIM_Foo', namespace=None),
                            CIMClassName('CIM_Foo', namespace='root/cimv2'))

        self.assertNotEqual(CIMClassName('CIM_Foo', namespace='root/cimv2'),
                            CIMClassName('CIM_Foo', namespace=None))

        self.assertEqual(CIMClassName('CIM_Foo', namespace=None),
                         CIMClassName('CIM_Foo', namespace=None))


class Test_CIMClassName_str(object):
    """
    Test `CIMClassName.__str__() (returns class path as WBEM URI)`.
    """

    @pytest.mark.parametrize(
        "obj, exp_uri", [
            (CIMClassName(
                classname='CIM_Foo'),
             'CIM_Foo'),
            (CIMClassName(
                classname='CIM_Foo',
                namespace='cimv2'),
             'cimv2:CIM_Foo'),
            (CIMClassName(
                classname='CIM_Foo',
                namespace='cimv2',
                host='10.11.12.13'),
             '//10.11.12.13/cimv2:CIM_Foo'),
            (CIMClassName(
                classname='CIM_Foo',
                namespace='root/cimv2',
                host='10.11.12.13'),
             '//10.11.12.13/root/cimv2:CIM_Foo'),
            (CIMClassName(
                classname='CIM_Foo',
                namespace='root/cimv2',
                host='10.11.12.13:5989'),
             '//10.11.12.13:5989/root/cimv2:CIM_Foo'),
            (CIMClassName(
                classname='CIM_Foo',
                namespace='root/cimv2',
                host='jdd:test@10.11.12.13:5989'),
             '//jdd:test@10.11.12.13:5989/root/cimv2:CIM_Foo'),
        ]
    )
    def test_succeeds(self, obj, exp_uri):
        """All test cases for CIMClassName.__str__() that succeed."""

        s = str(obj)

        assert s == exp_uri


class Test_CIMClassName_repr(object):
    """
    Test `CIMClassName.__repr__()`.
    """

    def test_all(self):

        obj = CIMClassName('CIM_Foo',
                           namespace='root/cimv2',
                           host='woot.com')

        r = repr(obj)

        assert re.match(r'^CIMClassName\(', r)
        assert 'classname=%r' % obj.classname in r
        assert 'namespace=%r' % obj.namespace in r
        assert 'host=%r' % obj.host in r


class CIMClassNameToXML(ValidationTestCase):

    def test_all(self):

        self.validate(CIMClassName('CIM_Foo'),
                      'CLASSNAME')

        self.validate(CIMClassName('CIM_Foo',
                                   namespace='root/blah'),
                      'LOCALCLASSPATH')

        self.validate(CIMClassName('CIM_Foo',
                                   namespace='root/blah',
                                   host='fred'),
                      'CLASSPATH')


class Test_CIMClassName_from_wbem_uri(object):
    """
    Test `CIMClassName.from_wbem_uri()`.
    """

    @pytest.mark.parametrize(
        "uri, exp_obj", [
            ('https://jdd:test@10.11.12.13:5989/root/cimv2:CIM_Foo',
             CIMClassName(
                 classname='CIM_Foo',
                 namespace='root/cimv2',
                 host='jdd:test@10.11.12.13:5989')),
            ('https://10.11.12.13:5989/root/cimv2:CIM_Foo',
             CIMClassName(
                 classname='CIM_Foo',
                 namespace='root/cimv2',
                 host='10.11.12.13:5989')),
            ('http://10.11.12.13/root/cimv2:CIM_Foo',
             CIMClassName(
                 classname='CIM_Foo',
                 namespace='root/cimv2',
                 host='10.11.12.13')),
            ('http://10.11.12.13/cimv2:CIM_Foo',
             CIMClassName(
                 classname='CIM_Foo',
                 namespace='cimv2',
                 host='10.11.12.13')),
        ]
    )
    def test_succeeds(self, uri, exp_obj):
        """All test cases for CIMClassName.from_wbem_uri() that succeed."""

        if CHECK_0_12_0:

            obj = CIMClassName.from_wbem_uri(uri)

            assert isinstance(obj, CIMClassName)
            assert obj.classname == exp_obj.classname
            assert obj.namespace == exp_obj.namespace
            assert obj.host == exp_obj.host

    @pytest.mark.parametrize(
        # TODO: Improve implementation to make it fail for the disabled cases.
        "uri, exp_exc", [
            ('https:/10.11.12.13:5989/cimv2:CIM_Foo',
             ValueError),  # missing '/' after scheme
            # ('xyz://10.11.12.13:5989/cimv2:CIM_Foo',
            #  ValueError),  # invalid scheme
            # ('https://10.11.12.13;5989/cimv2:CIM_Foo',
            #  ValueError),  # invalid ';' between host and port
            # ('https://10.11.12.13:5989:cimv2:CIM_Foo',
            #  ValueError),  # invalid ':' between port and namespace
            # ('https://10.11.12.13:5989/cimv2.CIM_Foo',
            #  ValueError),  # invalid '.' between namespace and classname
            # ('https://10.11.12.13:5989/cimv2/CIM_Foo',
            #  ValueError),  # invalid '/' between namespace and classname
            ('https://10.11.12.13:5989/cimv2:CIM_Foo.k1="v1"',
             ValueError),  # instance path used as class path
        ]
    )
    def test_fails(self, uri, exp_exc):
        """All test cases for CIMClassName.from_wbem_uri() that fail."""

        if CHECK_0_12_0:

            with pytest.raises(Exception) as exc_info:
                CIMClassName.from_wbem_uri(uri)
            exc = exc_info.value

            assert isinstance(exc, exp_exc)


class InitCIMClass(unittest.TestCase):

    def test_all(self):

        # Class name is None

        if CHECK_0_12_0:
            with self.assertRaises(ValueError):
                CIMClass(None)
        else:
            # Before 0.12.0, the implementation allowed the name to be None,
            # although the documentation required it not to be None.
            # We test the implemented behavior.
            obj = CIMClass(None)
            self.assertIs(obj.classname, None)

        # Initialise with classname, superclass

        CIMClass('CIM_Foo')
        CIMClass('CIM_Foo', superclass='CIM_Bar')

        # Initialise with properties

        CIMClass('CIM_Foo', properties={'InstanceID':
                                        CIMProperty('InstanceID', None,
                                                    type='string')})

        # Initialise with properties with inconsistent name

        if CHECK_0_12_0:
            with self.assertRaises(ValueError):
                CIMClass('CIM_Foo',
                         properties={'Name': CIMProperty('NameX', 'Foo')})
        else:
            obj = CIMClass('CIM_Foo',
                           properties={'Name': CIMProperty('NameX', 'Foo')})
            self.assertEqual(len(obj.properties), 1)
            self.assertEqual(obj.properties['Name'].name, 'NameX')

        # Initialise with properties with name being None.

        # Note that the name of the CIMProperty object is intentionally
        # not None, in order to get over that check, and to get to the
        # check for None as a dict key.
        with self.assertRaises(ValueError if CHECK_0_12_0 else TypeError):
            CIMClass('CIM_Foo',
                     properties={None: CIMProperty('Name', 'Foo')})

        # Initialise with properties using invalid object type

        if CHECK_0_12_0:
            with self.assertRaises(TypeError):
                CIMClass('CIM_Foo',
                         properties={'Name': 'Foo'})
        else:
            obj = CIMClass('CIM_Foo',
                           properties={'Name': 'Foo'})
            self.assertEqual(len(obj.properties), 1)
            self.assertEqual(obj.properties['Name'], 'Foo')

        # Initialise with method

        CIMClass('CIM_Foo', methods={'Delete': CIMMethod('Delete',
                                                         'uint32')})

        # Initialise with methods with inconsistent name

        if CHECK_0_12_0:
            with self.assertRaises(ValueError):
                CIMClass('CIM_Foo',
                         methods={'Name': CIMMethod('NameX', 'uint32')})
        else:
            obj = CIMClass('CIM_Foo',
                           methods={'Name': CIMMethod('NameX', 'uint32')})
            self.assertEqual(len(obj.methods), 1)
            self.assertEqual(obj.methods['Name'].name, 'NameX')

        # Initialise with methods with name being None

        # Note that the name of the CIMMethod object is intentionally
        # not None, in order to get over that check, and to get to the
        # check for None as a dict key.
        with self.assertRaises(ValueError if CHECK_0_12_0 else TypeError):
            CIMClass('CIM_Foo',
                     methods={None: CIMMethod('Name', 'uint32')})

        # Initialise with methods using invalid object type

        if CHECK_0_12_0:
            with self.assertRaises(TypeError):
                CIMClass('CIM_Foo', methods={'Name': 'Foo'})
        else:
            obj = CIMClass('CIM_Foo', methods={'Name': 'Foo'})
            self.assertEqual(len(obj.methods), 1)
            self.assertEqual(obj.methods['Name'], 'Foo')

        # Initialise with qualifiers using CIMQualifier

        obj = CIMClass('CIM_Foo',
                       qualifiers={'Key': CIMQualifier('Key', True)})
        self.assertEqual(len(obj.qualifiers), 1)
        self.assertEqual(obj.qualifiers['Key'], CIMQualifier('Key', True))

        # Initialise with qualifiers using simple type

        obj = CIMClass('CIM_Foo', qualifiers={'Key': True})
        self.assertEqual(len(obj.qualifiers), 1)
        qual = obj.qualifiers['Key']
        if CHECK_0_12_0:
            self.assertIsInstance(qual, CIMQualifier)
            self.assertEqual(qual, CIMQualifier('Key', True))
        else:
            self.assertIsInstance(qual, bool)
            self.assertEqual(qual, True)
            with self.assertRaises(TypeError):
                # We want to invoke the equal comparison, and use assert only
                # to avoid that checkers complain about the unused expression.
                assert qual == CIMQualifier('Key', True)

        # Initialise with qualifiers with inconsistent name

        if CHECK_0_12_0:
            with self.assertRaises(ValueError):
                CIMClass('CIM_Foo',
                         qualifiers={'Key': CIMQualifier('KeyX', True)})
        else:
            obj = CIMClass('CIM_Foo',
                           qualifiers={'Key': CIMQualifier('KeyX', True)})
            self.assertEqual(len(obj.qualifiers), 1)
            self.assertEqual(obj.qualifiers['Key'].name, 'KeyX')

        # Initialise with qualifiers with name being None

        # Note that the name of the CIMMethod object is intentionally
        # not None, in order to get over that check, and to get to the
        # check for None as a dict key.
        with self.assertRaises(ValueError if CHECK_0_12_0 else TypeError):
            CIMClass('CIM_Foo',
                     qualifiers={None: CIMQualifier('Key', True)})

        # Initialise with path

        path = CIMClassName('CIM_Bar', host='fred', namespace='root/cimv2')
        CIMClass('CIM_Foo', path=path)


class CopyCIMClass(unittest.TestCase):

    def test_all(self):

        path = CIMClassName('CIM_Bar', host='fred', namespace='root/cimv2')

        c = CIMClass('CIM_Foo',
                     methods={'Delete': CIMMethod('Delete', 'uint32')},
                     qualifiers={'Key': CIMQualifier('Key', True)},
                     path=path)

        co = c.copy()

        self.assertEqual(c, co)

        co.classname = 'CIM_Bar'
        del co.methods['Delete']
        del co.qualifiers['Key']
        co.path = None

        self.assertEqual(c.classname, 'CIM_Foo')
        self.assertTrue(c.methods['Delete'])
        self.assertTrue(c.qualifiers['Key'])
        self.assertEqual(c.path, path)


class CIMClassAttrs(unittest.TestCase):

    def test_all(self):

        obj = CIMClass('CIM_Foo', superclass='CIM_Bar')

        self.assertEqual(obj.classname, 'CIM_Foo')
        self.assertEqual(obj.superclass, 'CIM_Bar')
        self.assertEqual(obj.properties, {})
        self.assertEqual(obj.qualifiers, {})
        self.assertEqual(obj.methods, {})
        self.assertEqual(obj.qualifiers, {})
        self.assertEqual(obj.path, None)

        if CHECK_0_12_0:
            # Check that classname cannot be set to None
            with self.assertRaises(ValueError):
                obj.classname = None
        else:
            # Before 0.12.0, the implementation allowed the classname to be
            # None, although the documentation required it not to be None.
            # We test the implemented behavior.
            obj.classname = None
            self.assertIs(obj.classname, None)

        # Setting properties with inconsistent name

        if CHECK_0_12_0:
            with self.assertRaises(ValueError):
                obj.properties = {'Name': CIMProperty('NameX', 'Foo')}
        else:
            obj.properties = {'Name': CIMProperty('NameX', 'Foo')}
            self.assertEqual(len(obj.properties), 1)
            self.assertEqual(obj.properties['Name'].name, 'NameX')

        # Setting properties with name being None

        # Note that the name of the CIMProperty object is intentionally
        # not None, in order to get over that check, and to get to the
        # check for None as a dict key.
        if CHECK_0_12_0:
            with self.assertRaises(ValueError):
                obj.properties = {None: CIMProperty('Name', 'Foo')}
        else:
            obj.properties = {None: CIMProperty('Name', 'Foo')}
            self.assertEqual(len(obj.properties), 1)
            self.assertEqual(obj.properties[None], CIMProperty('Name', 'Foo'))

        # Setting properties using invalid object type

        if CHECK_0_12_0:
            with self.assertRaises(TypeError):
                obj.properties = {'Name': 'Foo'}
        else:
            obj.properties = {'Name': 'Foo'}
            self.assertEqual(len(obj.properties), 1)
            self.assertEqual(obj.properties['Name'], 'Foo')

        # Setting methods with inconsistent name

        if CHECK_0_12_0:
            with self.assertRaises(ValueError):
                obj.methods = {'Name': CIMMethod('NameX', 'uint32')}
        else:
            obj.methods = {'Name': CIMMethod('NameX', 'uint32')}
            self.assertEqual(len(obj.methods), 1)
            self.assertEqual(obj.methods['Name'].name, 'NameX')

        # Setting methods with name being None

        # Note that the name of the CIMMethod object is intentionally
        # not None, in order to get over that check, and to get to the
        # check for None as a dict key.
        if CHECK_0_12_0:
            with self.assertRaises(ValueError if CHECK_0_12_0 else TypeError):
                obj.methods = {None: CIMMethod('Name', 'uint32')}
        else:
            obj.methods = {None: CIMMethod('Name', 'uint32')}
            self.assertEqual(len(obj.methods), 1)
            self.assertEqual(obj.methods[None], CIMMethod('Name', 'uint32'))

        # Setting methods using invalid object type

        if CHECK_0_12_0:
            with self.assertRaises(TypeError):
                obj.methods = {'Name': 'Foo'}
        else:
            obj.methods = {'Name': 'Foo'}
            self.assertEqual(len(obj.methods), 1)
            self.assertEqual(obj.methods['Name'], 'Foo')

        # Setting qualifiers using CIMQualifier

        obj.qualifiers = {'Key': CIMQualifier('Key', True)}
        self.assertEqual(len(obj.qualifiers), 1)
        self.assertEqual(obj.qualifiers['Key'], CIMQualifier('Key', True))

        # Setting qualifiers using simple type

        obj.qualifiers = {'Key': True}
        self.assertEqual(len(obj.qualifiers), 1)
        qual = obj.qualifiers['Key']
        if CHECK_0_12_0:
            self.assertIsInstance(qual, CIMQualifier)
            self.assertEqual(qual, CIMQualifier('Key', True))
        else:
            self.assertIsInstance(qual, bool)
            self.assertEqual(qual, True)
            with self.assertRaises(TypeError):
                # We want to invoke the equal comparison, and use assert only
                # to avoid that checkers complain about the unused expression.
                assert qual == CIMQualifier('Key', True)

        # Setting qualifiers with inconsistent name

        if CHECK_0_12_0:
            with self.assertRaises(ValueError):
                obj.qualifiers = {'Key': CIMQualifier('KeyX', True)}
        else:
            obj.qualifiers = {'Key': CIMQualifier('KeyX', True)}
            self.assertEqual(len(obj.qualifiers), 1)
            self.assertEqual(obj.qualifiers['Key'].name, 'KeyX')

        # Setting qualifiers with name being None

        # Note that the name of the CIMQualifier object is intentionally
        # not None, in order to get over that check, and to get to the
        # check for None as a dict key.
        if CHECK_0_12_0:
            with self.assertRaises(ValueError if CHECK_0_12_0 else TypeError):
                obj.qualifiers = {None: CIMQualifier('Key', True)}
        else:
            obj.qualifiers = {None: CIMQualifier('Key', True)}
            self.assertEqual(obj.qualifiers[None], CIMQualifier('Key', True))


class CIMClassEquality(unittest.TestCase):

    def test_all(self):

        self.assertEqual(CIMClass('CIM_Foo'), CIMClass('CIM_Foo'))
        self.assertEqual(CIMClass('CIM_Foo'), CIMClass('cim_foo'))

        self.assertNotEqual(CIMClass('CIM_Foo', superclass='CIM_Bar'),
                            CIMClass('CIM_Foo'))

        properties = {'InstanceID':
                      CIMProperty('InstanceID', None,
                                  type='string')}

        methods = {'Delete': CIMMethod('Delete', 'uint32')}

        qualifiers = {'Key': CIMQualifier('Key', True)}

        path = CIMClassName('CIM_Bar', host='fred', namespace='root/cimv2')

        self.assertNotEqual(CIMClass('CIM_Foo'),
                            CIMClass('CIM_Foo', properties=properties))

        self.assertNotEqual(CIMClass('CIM_Foo'),
                            CIMClass('CIM_Foo', methods=methods))

        self.assertNotEqual(CIMClass('CIM_Foo'),
                            CIMClass('CIM_Foo', qualifiers=qualifiers))

        self.assertNotEqual(CIMClass('CIM_Foo'),
                            CIMClass('CIM_Foo', path=path))

        # Basic superclass name test

        self.assertEqual(CIMClass('CIM_Foo', superclass='CIM_Bar'),
                         CIMClass('CIM_Foo', superclass='CIM_Bar'))

        # Superclass name should be case insensitive

        self.assertEqual(CIMClass('CIM_Foo', superclass='CIM_Bar'),
                         CIMClass('CIM_Foo', superclass='cim_bar'))

        # Superclass name None

        self.assertNotEqual(CIMClass('CIM_Foo', superclass=None),
                            CIMClass('CIM_Foo', superclass='CIM_Bar'))

        self.assertNotEqual(CIMClass('CIM_Foo', superclass='CIM_Bar'),
                            CIMClass('CIM_Foo', superclass=None))

        self.assertEqual(CIMClass('CIM_Foo', superclass=None),
                         CIMClass('CIM_Foo', superclass=None))

        # Verify detection of incorrect type of second object

        with pytest.raises(TypeError):
            # pylint: disable=expression-not-assigned
            CIMClass('CIM_Foo') == 'CIM_Foo'

        with pytest.raises(TypeError):
            # pylint: disable=expression-not-assigned
            CIMClass('CIM_Foo') == CIMClassName('CIM_Foo')


class CIMClassCompare(unittest.TestCase):

    @unimplemented
    def test_all(self):
        # TODO Implement ordering comparison test for CIMClass
        raise AssertionError("test not implemented")


class CIMClassSort(unittest.TestCase):

    @unimplemented
    def test_all(self):
        # TODO Implement sorting test for CIMClass
        raise AssertionError("test not implemented")


class Test_CIMClass_str(object):
    """
    Test `CIMClass.__str__()`.
    """

    def test_all(self):

        path = CIMClassName('CIM_Foo')

        obj = CIMClass(
            'CIM_Foo',
            properties=dict(
                Name=CIMProperty('Name', 'string'),
                Ref1=CIMProperty('Ref1', 'reference')),
            path=path)

        s = str(obj)

        assert re.match(r'^CIMClass\(', s)
        assert 'classname=%r' % obj.classname in s


class Test_CIMClass_repr(object):
    """
    Test `CIMClass.__repr__()`.
    """

    def test_all(self):

        path = CIMClassName('CIM_Foo')

        obj = CIMClass(
            'CIM_Foo',
            properties=dict(
                Name=CIMProperty('Name', 'string'),
                Ref1=CIMProperty('Ref1', 'reference')),
            path=path)

        r = repr(obj)

        assert re.match(r'^CIMClass\(', r)
        assert 'classname=%r' % obj.classname in r
        assert 'superclass=%r' % obj.superclass in r
        assert 'properties=' in r
        assert 'methods=' in r
        assert 'qualifiers=' in r
        assert 'path=CIMClassName(' in r


class CIMClassToXML(ValidationTestCase):

    def test_all(self):

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
                               methods={'Delete': CIMMethod('Delete',
                                                            'uint32')}),
                      root_elem_CIMClass)

        self.validate(CIMClass('CIM_Foo',
                               qualifiers={'Key': CIMQualifier('Key', True)}),
                      root_elem_CIMClass)


class CIMClassToMOF(unittest.TestCase, RegexpMixin):

    def test_all(self):

        cl = CIMClass(
            'CIM_Foo',
            properties={'InstanceID': CIMProperty('InstanceID', None,
                                                  type='string')})

        imof = cl.tomof()

        self.assertRegexpContains(imof, r"^\s*class\s+CIM_Foo\s*\{")

        self.assertRegexpContains(imof, r"\n\s*string\s+InstanceID")
        self.assertRegexpContains(imof, r"\n\};")


class CIMClassPropertyWithValueToMOF(unittest.TestCase, RegexpMixin):

    def test_ScalarPropertyValues(self):

        cl = CIMClass(
            'CIM_Foo',
            properties={'InstanceID': CIMProperty('InstanceID', None,
                                                  type='string'),
                        'MyUint8': CIMProperty('MyUint8', Uint8(99),
                                               type='uint8'),
                        'MyUint16': CIMProperty('MyUint16', Uint16(999),
                                                type='uint16'),
                        'MyUint32': CIMProperty('MyUint32', Uint32(12345),
                                                type='uint32'),
                        'MySint32': CIMProperty('MySint32', Sint32(-12345),
                                                type='sint32'),
                        'Mydatetime': CIMProperty('Mydatetime',
                                                  '12345678224455.654321:000',
                                                  type='datetime'),
                        'MyStr': CIMProperty('MyStr', 'This is a test',
                                             type='string')})

        imof = cl.tomof()

        self.assertRegexpContains(imof, r"^\s*class\s+CIM_Foo\s*\{")

        self.assertRegexpContains(imof, r"\n\s*string\s+InstanceID")
        self.assertRegexpContains(imof, r"\n\s*uint8\s+MyUint8\s+=\s+99;")
        self.assertRegexpContains(imof, r"\n\s*uint16\s+MyUint16\s+=\s+999;")
        self.assertRegexpContains(imof, r"\n\s*uint32\s+MyUint32\s+=\s+12345;")
        self.assertRegexpContains(imof, r"\n\s*sint32\s+MySint32\s+=\s+"
                                        r"-12345;")
        self.assertRegexpContains(imof, r"\n\s*datetime\s+Mydatetime\s+=\s+"
                                        r"\"12345678224455.654321:000\";")
        self.assertRegexpContains(imof, r"\n\s*string\s+MyStr\s+=\s+"
                                        r"\"This is a test\";")

        self.assertRegexpContains(imof, r"\n\};")


class CIMClassToMofArrayProperty(unittest.TestCase, RegexpMixin):
    def test_ArrayDef32(self):

        cl = CIMClass(
            'CIM_Foo',
            properties={'Uint32Array': CIMProperty('Uint32Array', None,
                                                   type='uint32',
                                                   is_array=True)})

        imof = cl.tomof()

        self.assertRegexpContains(imof, r"^\s*class\s+CIM_Foo\s*\{")

        self.assertRegexpContains(imof, r"\n\s*uint32\s+Uint32Array\[];\n")

    def test_ArrayDefWSize32(self):

        cl = CIMClass(
            'CIM_Foo',
            properties={'Uint32Array': CIMProperty('Uint32Array', None,
                                                   type='uint32',
                                                   array_size=9,
                                                   is_array=True)})
        imof = cl.tomof()

        self.assertRegexpContains(imof, r"^\s*class\s+CIM_Foo\s*\{")
        self.assertRegexpContains(imof, r"\n\s*uint32\s+Uint32Array\[9];\n")
        self.assertRegexpContains(imof, r"\n\};",)

    def test_ArrayDefStr(self):

        cl = CIMClass(
            'CIM_Foo',
            properties={'StrArray': CIMProperty('StrArray', None,
                                                type='string',
                                                is_array=True)})

        imof = cl.tomof()

        self.assertRegexpContains(imof, r"^\s*class\s+CIM_Foo\s*\{")
        self.assertRegexpContains(imof, r"\n\s*string\s+StrArray\[];\n")
        self.assertRegexpContains(imof, r"\n\};",)

    def test_ArrayDefWSizeStr(self):

        cl = CIMClass(
            'CIM_Foo',
            properties={'StrArray': CIMProperty('StrArray', None,
                                                type='string',
                                                array_size=111,
                                                is_array=True)})
        imof = cl.tomof()

        self.assertRegexpContains(imof, r"^\s*class\s+CIM_Foo\s*\{")

        self.assertRegexpContains(imof, r"\n\s*string\s+StrArray\[111];\n")
        self.assertRegexpContains(imof, r"\n};\n")

    # TODO ks apr 16: extend this test for other alternatives for mof output
    # of property parameters.


class CIMClassMethodsToMOF(unittest.TestCase, RegexpMixin):
    """Test variations of class method mof output"""

    def test_OneMethod(self):
        """test a cimple method with no parameters mof output"""
        cl = CIMClass(
            'CIM_FooOneMethod',
            methods={'Simple': CIMMethod('Simple', 'uint32')})

        imof = cl.tomof()

        self.assertRegexpContains(imof, r"^\s*class\s+CIM_FooOneMethod\s*\{")
        self.assertRegexpContains(imof, r"\s*uint32\s+Simple\(\);")
        self.assertRegexpContains(imof, r"\n\};",)

    def test_SimpleMethod(self):
        """Test multiple methods some with parameters"""
        params = {'Param1': CIMParameter('Param1', 'string'),
                  'Param2': CIMParameter('Param2', 'uint32')}

        cl = CIMClass(
            'CIM_FooSimple',
            methods={'Simple': CIMMethod('Simple', 'uint32'),
                     'WithParams': CIMMethod('WithParams', 'uint32',
                                             parameters=params)})
        imof = cl.tomof()

        self.assertRegexpContains(imof, r"^\s*class\s+CIM_FooSimple\s*\{")
        self.assertRegexpContains(imof, r"\n\s*uint32\s+Simple\(\);")
        self.assertRegexpContains(imof, r"\n\s*uint32\s+WithParams\(")
        self.assertRegexpContains(imof, r"\n\s*uint32\s+Param2")
        self.assertRegexpContains(imof, r"\n\s*string\s+Param1")
        self.assertRegexpContains(imof, r"\n\};",)

    def test_ArrayParams(self):
        """Test methods with parameters that defined arrays"""
        array_p1 = {'Param3': CIMParameter('Param3', 'string',
                                           is_array=True)}
        array_p2 = {'Param4': CIMParameter('Param4', 'sint32',
                                           is_array=True, array_size=9)}

        cl = CIMClass(
            'CIM_FooArray',
            methods={'ArrayP1': CIMMethod('ArrayP1', 'uint32',
                                          parameters=array_p1),
                     'ArrayP2': CIMMethod('ArrayP2', 'uint32',
                                          parameters=array_p2)})

        imof = cl.tomof()

        self.assertRegexpContains(imof, r"^\s*class\s+CIM_FooArray\s*\{")
        self.assertRegexpContains(imof, r"\n\s*string\s+Param3\[\]\);")
        self.assertRegexpContains(imof, r"\n\s*sint32\s+Param4\[9\]\);")
        self.assertRegexpContains(imof, r"\n\};",)


class CIMClassWQualToMOF(unittest.TestCase):
    """Generate mof output for a a class with a qualifiers, multiple
       properties and methods
    """

    def test_all(self):

        # predefine qualifiers, params
        pquals = {'ModelCorresponse': CIMQualifier('ModelCorrespondense',
                                                   'BlahBlahClass'),
                  'Description': CIMQualifier('Description', "This is a"
                                              " description for a property"
                                              " that serves no purpose"
                                              " but is multiline.")}
        pquals2 = {'ValueMap': CIMQualifier('ValueMap',
                                            ["0", "1", "2", "3", "4",
                                             "5", "6"]),
                   'Values': CIMQualifier('Values',
                                          ["Unknown", "value1", "value2",
                                           "value3", "value4", "value5",
                                           "value6"])}
        mquals = {'Description': CIMQualifier('Description', "blah blah")}

        prquals = {'Description': CIMQualifier('Description', "more blah"),
                   'IN': CIMQualifier('in', False)}

        params = {'Param1': CIMParameter('Param1', 'string',
                                         qualifiers=prquals),
                  'Param2': CIMParameter('Param2', 'uint32')}
        embedqual = {'Description': CIMQualifier('Description',
                                                 "An embedded instance"),
                     'EmbeddedInstance': CIMQualifier('EmbeddedInstance',
                                                      "My_Embedded")}
        # define the target class
        cl = CIMClass(
            'CIM_Foo', superclass='CIM_Bar',
            qualifiers={'Abstract': CIMQualifier('Abstract', True),
                        'Description': CIMQualifier('Description',
                                                    'This is a class '
                                                    'description')},

            properties={'InstanceID': CIMProperty('InstanceID', None,
                                                  type='string',
                                                  qualifiers=pquals),
                        'MyUint8': CIMProperty('MyUint8', None,
                                               type='uint8',
                                               qualifiers=pquals),
                        'MyUint16': CIMProperty('MyUint16', None,
                                                type='uint16',
                                                qualifiers=pquals2),
                        'MyUint32': CIMProperty('MyUint32', None,
                                                type='uint32',
                                                qualifiers=pquals),
                        'MyUint32Ar': CIMProperty('MyUint32Ar', None,
                                                  type='uint32',
                                                  is_array=True,
                                                  qualifiers=pquals),
                        'MyEmbedded': CIMProperty('MyEmbedded', None,
                                                  type='string',
                                                  qualifiers=embedqual)},

            methods={'Delete': CIMMethod('Delete', 'uint32',
                                         qualifiers=mquals),
                     'FooMethod': CIMMethod('FooMethod', 'uint32',
                                            parameters=params,
                                            qualifiers=mquals)}
            )  # noqa: E123

        clmof = cl.tomof()

        # match first line for [Abstract (True),
        m = re.match(r"^\s*\[Abstract", clmof)
        if m is None:
            self.fail("Invalid MOF generated. First line\n"
                      "Class: %r\n"
                      "Generated MOF: \n%s" % (cl, clmof))

        # search for class CIM_Foo: CIM_Bar {
        s = re.search(r"\s*class\s+CIM_Foo\s*:\s*CIM_Bar\s*\{", clmof)

        if s is None:
            self.fail("Invalid MOF generated. Class name line.\n"
                      "Class: %r\n"
                      "Generated MOF: \n%s" % (cl, clmof))

        # search for EmbeddedInstance ("My_Embedded")]
        s = re.search(r"\s*EmbeddedInstance\s+\(\"My_Embedded\"\)\]", clmof)

        if s is None:
            self.fail("Invalid MOF generated. EmbeddedInstance.\n"
                      "Class: %r\n"
                      "Generated MOF: \n%s" % (cl, clmof))

        # search for 'string MyEmbedded;'
        s = re.search(r"\s*string\s+MyEmbedded;", clmof)

        if s is None:
            self.fail("Invalid MOF generated. property string MyEmbedded.\n"
                      "Class: %r\n"
                      "Generated MOF: \n%s" % (cl, clmof))


class CIMClassWoQualifiersToMof(unittest.TestCase, RegexpMixin):
    """Generate class without qualifiers and convert to mof.
    """

    def test_all(self):

        params = {'Param1': CIMParameter('Param1', 'string'),
                  'Param2': CIMParameter('Param2', 'uint32')}

        cl = CIMClass(
            'CIM_FooNoQual', superclass='CIM_Bar',

            properties={'InstanceID': CIMProperty('InstanceID', None,
                                                  type='string'),
                        'MyUint8': CIMProperty('MyUint8', None,
                                               type='uint8'),
                        'MyUint16': CIMProperty('MyUint16', None,
                                                type='uint16'),
                       },  # noqa: E124
            methods={'Delete': CIMMethod('Delete', 'uint32'),
                     'FooMethod': CIMMethod('FooMethod', 'uint32',
                                            parameters=params)
                    }  # noqa: E124
            )  # noqa: E123

        # Generate the mof. Does not really test result
        clmof = cl.tomof()

        # search for class CIM_Foo: CIM_Bar {
        self.assertRegexpContains(clmof,
                                  r"^\s*class\s+CIM_FooNoQual\s*:\s*"
                                  r"CIM_Bar\s*\{")

        # match method Delete,
        self.assertRegexpContains(clmof, r"\n\s*uint32\s+Delete\(\);\n")
        self.assertRegexpContains(clmof, r"\n\};",)


class Test_InitCIMMethod(object):

    def test_all(self):

        # Initialization with name being None

        if CHECK_0_12_0:
            with pytest.raises(ValueError):
                CIMMethod(None, 'uint32')
        else:
            # Before 0.12.0 (at least in 0.11.0, maybe earlier), the
            # implementation already checked for None, but raised a different
            # exception.
            with pytest.raises(TypeError):
                CIMMethod(None, 'uint32')

        CIMMethod('FooMethod', 'uint32')

        CIMMethod('FooMethod', 'uint32',
                  parameters={'Param1': CIMParameter('Param1', 'uint32'),
                              'Param2': CIMParameter('Param2', 'string')})

        CIMMethod('FooMethod', 'uint32',
                  parameters={'Param1': CIMParameter('Param1', 'uint32'),
                              'Param2': CIMParameter('Param2', 'string')},
                  qualifiers={'Key': CIMQualifier('Key', True)})

        # Verify the deprecated methodname parameter

        obj = CIMMethod(methodname='FooMethod', return_type='uint32')
        assert obj.name == 'FooMethod'

        if CHECK_0_12_0:
            with pytest.raises(ValueError):
                CIMMethod(methodname='FooMethod', name='FooMethod',
                          return_type='uint32')
        else:
            # Before 0.12.0, the implementation already checked for this, but
            # raised a different exception.
            with pytest.raises(TypeError):
                CIMMethod(methodname='FooMethod', name='FooMethod',
                          return_type='uint32')


class CopyCIMMethod(unittest.TestCase):

    def test_all(self):

        m = CIMMethod('FooMethod', 'uint32',
                      parameters={'P1': CIMParameter('P1', 'uint32'),
                                  'P2': CIMParameter('P2', 'string')},
                      qualifiers={'Key': CIMQualifier('Key', True)})

        c = m.copy()

        self.assertEqual(m, c)

        c.name = 'BarMethod'
        c.return_type = 'string'
        del c.parameters['P1']
        del c.qualifiers['Key']

        self.assertEqual(m.name, 'FooMethod')
        self.assertEqual(m.return_type, 'uint32')
        self.assertTrue(m.parameters['P1'])
        self.assertTrue(m.qualifiers['Key'])


class CIMMethodAttrs(unittest.TestCase):

    def test_all(self):

        m = CIMMethod('FooMethod', 'uint32',
                      parameters={'Param1': CIMParameter('Param1', 'uint32'),
                                  'Param2': CIMParameter('Param2', 'string')})

        self.assertEqual(m.name, 'FooMethod')
        self.assertEqual(m.return_type, 'uint32')
        self.assertEqual(len(m.parameters), 2)
        self.assertEqual(m.qualifiers, {})

        if CHECK_0_12_0:
            # Check that name cannot be set to None
            with self.assertRaises(ValueError):
                m.name = None
        else:
            # Before 0.12.0, the implementation allowed the name to be
            # None, although the documentation required it not to be None.
            # We test the implemented behavior.
            m.name = None
            self.assertIs(m.name, None)


class CIMMethodEquality(unittest.TestCase):

    def test_all(self):

        self.assertEqual(CIMMethod('FooMethod', 'uint32'),
                         CIMMethod('FooMethod', 'uint32'))

        self.assertEqual(CIMMethod('FooMethod', 'uint32'),
                         CIMMethod('fooMethod', 'uint32'))

        self.assertNotEqual(CIMMethod('FooMethod', 'uint32'),
                            CIMMethod('FooMethod', 'uint32',
                                      qualifiers={'Key': CIMQualifier('Key',
                                                                      True)}))
        # Verify detection of incorrect type of second object

        with pytest.raises(TypeError):
            # pylint: disable=expression-not-assigned
            CIMMethod('FooMethod', 'uint32') == 'FooMethod'


class CIMMethodCompare(unittest.TestCase):

    @unimplemented
    def test_all(self):
        # TODO Implement ordering comparison test for CIMMethod
        raise AssertionError("test not implemented")


class CIMMethodSort(unittest.TestCase):

    @unimplemented
    def test_all(self):
        # TODO Implement sorting test for CIMMethod
        raise AssertionError("test not implemented")


class Test_CIMMethod_str(object):
    """
    Test `CIMMethod.__str__()`.
    """

    def test_all(self):

        obj = CIMMethod('FooMethod', 'uint32')

        s = str(obj)

        assert re.match(r'^CIMMethod\(', s)
        assert 'return_type=%r' % obj.return_type in s


class Test_CIMMethod_repr(object):
    """
    Test `CIMMethod.__repr__()`.
    """

    def test_all(self):

        obj = CIMMethod('FooMethod', 'uint32')

        r = repr(obj)

        assert re.match(r'^CIMMethod\(', r)
        assert 'return_type=%r' % obj.return_type in r
        assert 'class_origin=%r' % obj.class_origin in r
        assert 'propagated=%r' % obj.propagated in r
        assert 'parameters=' in r
        assert 'qualifiers=' in r


class CIMMethodNoReturn(unittest.TestCase):
    """Test that CIMMethod without return value fails"""

    def test_all(self):
        try:
            str(CIMMethod('FooMethod'))
            self.fail('Expected Exception')

        except ValueError:
            pass


class CIMMethodToXML(ValidationTestCase):

    def test_all(self):

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


class InitCIMParameter(unittest.TestCase):

    def test_all(self):

        # Initialization with name being None

        if CHECK_0_12_0:
            with self.assertRaises(ValueError):
                CIMParameter(None, 'uint32')
        else:
            # Before 0.12.0, the implementation allowed the name to be None,
            # although the documentation required it not to be None.
            # We test the implemented behavior
            p = CIMParameter(None, 'uint32')
            self.assertIs(p.name, None)

        # Initialization with type being None

        if CHECK_0_12_0:
            with self.assertRaises(ValueError):
                CIMParameter('Foo', type=None)
        else:
            # Before 0.12.0, the implementation allowed the type to be None,
            # although the documentation required it not to be None.
            # We test the implemented behavior
            p = CIMParameter('Foo', type=None)
            self.assertIs(p.type, None)

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

        # Check unspecified is_array

        if CHECK_0_12_0:

            # Check that a value of None results in a scalar
            p = CIMParameter('Foo', 'uint32', is_array=None, value=None)
            self.assertEqual(p.is_array, False)

            # Check that a scalar value results in a scalar
            p = CIMParameter('Foo', 'uint32', is_array=None, value=42)
            self.assertEqual(p.is_array, False)

            # Check that an array value results in an array
            p = CIMParameter('Foo', 'uint32', is_array=None, value=[42])
            self.assertEqual(p.is_array, True)

        else:

            # Before 0.12.0, the implementation just stored the provided
            # is_array value without checking or inferring it. The
            # documentation was inconsistent about that: In the description of
            # the is_array constructor parameter, it stated that `None` is
            # stored as-is, and in the description of the is_array attribute,
            # it stated that it will never be `None`.

            # The following tests verify the implemented behavior.

            p = CIMParameter('Foo', 'uint32', is_array=None, value=None)
            self.assertIs(p.is_array, None)

            p = CIMParameter('Foo', 'uint32', is_array=None, value=42)
            self.assertIs(p.is_array, None)

            p = CIMParameter('Foo', 'uint32', is_array=None, value=[42])
            self.assertIs(p.is_array, None)

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


class CopyCIMParameter(unittest.TestCase):

    def test_all(self):

        p = CIMParameter('RefParam', 'reference',
                         reference_class='CIM_Foo',
                         qualifiers={'Key': CIMQualifier('Key', True)})

        c = p.copy()

        self.assertEqual(p, c)

        c.name = 'Fooble'
        c.type = 'string'
        c.reference_class = None
        del c.qualifiers['Key']

        self.assertEqual(p.name, 'RefParam')
        self.assertEqual(p.type, 'reference')
        self.assertEqual(p.reference_class, 'CIM_Foo')
        self.assertTrue(p.qualifiers['Key'])


class CIMParameterAttrs(unittest.TestCase):

    def test_all(self):

        obj = CIMParameter('Param0', 'string')

        # Setting the name to None
        if CHECK_0_12_0:
            with self.assertRaises(ValueError):
                obj.name = None
        else:
            # Before 0.12.0, the implementation allowed the name to be
            # None, although the documentation required it not to be None.
            # We test the implemented behavior.
            obj.name = None
            self.assertIs(obj.name, None)

        # Setting the type to None
        if CHECK_0_12_0:
            with self.assertRaises(ValueError):
                obj.type = None
        else:
            # Before 0.12.0, the implementation allowed the type to be None,
            # although the documentation required it not to be None.
            # We test the implemented behavior
            obj.type = None
            self.assertIs(obj.type, None)

        # Single-valued parameters

        p = CIMParameter('Param1', 'string')

        self.assertEqual(p.name, 'Param1')
        self.assertEqual(p.type, 'string')
        self.assertEqual(p.qualifiers, {})

        # Array parameters

        p = CIMParameter('ArrayParam', 'uint32', is_array=True)

        self.assertEqual(p.name, 'ArrayParam')
        self.assertEqual(p.type, 'uint32')
        self.assertEqual(p.array_size, None)
        self.assertEqual(p.qualifiers, {})

        # Reference parameters

        p = CIMParameter('RefParam', 'reference', reference_class='CIM_Foo')

        self.assertEqual(p.name, 'RefParam')
        self.assertEqual(p.reference_class, 'CIM_Foo')
        self.assertEqual(p.qualifiers, {})

        # Reference array parameters

        p = CIMParameter('RefArrayParam', 'reference',
                         reference_class='CIM_Foo', is_array=True,
                         array_size=10)

        self.assertEqual(p.name, 'RefArrayParam')
        self.assertEqual(p.reference_class, 'CIM_Foo')
        self.assertEqual(p.array_size, 10)
        self.assertEqual(p.is_array, True)
        self.assertEqual(p.qualifiers, {})

        if CHECK_0_12_0:
            # Check that name cannot be set to None
            with self.assertRaises(ValueError):
                p.name = None
        else:
            # Before 0.12.0, the implementation allowed the name to be
            # None, although the documentation required it not to be None.
            # We test the implemented behavior.
            p.name = None
            self.assertIs(p.name, None)


class CIMParameterEquality(unittest.TestCase):

    def test_all(self):

        # Single-valued parameters

        self.assertEqual(CIMParameter('Param1', 'uint32'),
                         CIMParameter('Param1', 'uint32'))

        self.assertEqual(CIMParameter('Param1', 'uint32'),
                         CIMParameter('param1', 'uint32'))

        self.assertNotEqual(CIMParameter('Param1', 'uint32'),
                            CIMParameter('param1', 'string'))

        self.assertNotEqual(CIMParameter('Param1', 'uint32'),
                            CIMParameter('param1', 'uint32',
                                         qualifiers={'Key':
                                                     CIMQualifier('Key',
                                                                  True)}))

        # Array parameters

        self.assertEqual(
            CIMParameter('ArrayParam', 'uint32', is_array=True),
            CIMParameter('ArrayParam', 'uint32', is_array=True))

        self.assertEqual(
            CIMParameter('ArrayParam', 'uint32', is_array=True),
            CIMParameter('arrayParam', 'uint32', is_array=True))

        self.assertNotEqual(
            CIMParameter('ArrayParam', 'uint32', is_array=True),
            CIMParameter('ArrayParam', 'string', is_array=True))

        self.assertNotEqual(
            CIMParameter('ArrayParam', 'uint32', is_array=True),
            CIMParameter('ArrayParam', 'string', is_array=True,
                         array_size=10))

        self.assertNotEqual(
            CIMParameter('ArrayParam', 'uint32', is_array=True),
            CIMParameter('ArrayParam', 'uint32', is_array=True,
                         qualifiers={'Key': CIMQualifier('Key', True)}))

        # Reference parameters

        self.assertEqual(CIMParameter('RefParam', 'reference',
                                      reference_class='CIM_Foo'),
                         CIMParameter('RefParam', 'reference',
                                      reference_class='CIM_Foo'))

        self.assertEqual(CIMParameter('RefParam', 'reference',
                                      reference_class='CIM_Foo'),
                         CIMParameter('refParam', 'reference',
                                      reference_class='CIM_Foo'))

        self.assertEqual(CIMParameter('RefParam', 'reference',
                                      reference_class='CIM_Foo'),
                         CIMParameter('refParam', 'reference',
                                      reference_class='CIM_foo'))

        self.assertNotEqual(CIMParameter('RefParam', 'reference',
                                         reference_class='CIM_Foo'),
                            CIMParameter('RefParam', 'reference',
                                         reference_class='CIM_Bar'))

        self.assertNotEqual(CIMParameter('RefParam', 'reference',
                                         reference_class='CIM_Foo'),
                            CIMParameter('RefParam', 'reference',
                                         reference_class='CIM_Foo',
                                         qualifiers={'Key': CIMQualifier('Key',
                                                                         True)})
                           )  # noqa: E124

        # reference_class None

        self.assertNotEqual(CIMParameter('RefParam', 'reference',
                                         reference_class=None),
                            CIMParameter('RefParam', 'reference',
                                         reference_class='CIM_Foo'))

        self.assertNotEqual(CIMParameter('RefParam', 'reference',
                                         reference_class='CIM_Foo'),
                            CIMParameter('RefParam', 'reference',
                                         reference_class=None))

        self.assertEqual(CIMParameter('RefParam', 'reference',
                                      reference_class=None),
                         CIMParameter('RefParam', 'reference',
                                      reference_class=None))

        # Reference array parameters

        self.assertEqual(CIMParameter('ArrayParam', 'reference',
                                      reference_class='CIM_Foo',
                                      is_array=True),
                         CIMParameter('ArrayParam', 'reference',
                                      reference_class='CIM_Foo',
                                      is_array=True))

        self.assertEqual(CIMParameter('ArrayParam', 'reference',
                                      reference_class='CIM_Foo',
                                      is_array=True),
                         CIMParameter('arrayparam', 'reference',
                                      reference_class='CIM_Foo',
                                      is_array=True))

        self.assertNotEqual(CIMParameter('ArrayParam', 'reference',
                                         reference_class='CIM_Foo',
                                         is_array=True),
                            CIMParameter('arrayParam', 'reference',
                                         reference_class='CIM_foo',
                                         is_array=True,
                                         array_size=10))

        self.assertNotEqual(CIMParameter('ArrayParam', 'reference',
                                         reference_class='CIM_Foo',
                                         is_array=True),
                            CIMParameter('ArrayParam', 'reference',
                                         reference_class='CIM_Foo',
                                         is_array=True,
                                         qualifiers={'Key':
                                                     CIMQualifier('Key',
                                                                  True)}))

        # Verify detection of incorrect type of second object

        with pytest.raises(TypeError):
            # pylint: disable=expression-not-assigned
            CIMParameter('Param1', 'uint32') == 'Param1'


class CIMParameterCompare(unittest.TestCase):

    @unimplemented
    def test_all(self):
        # TODO Implement ordering comparison test for CIMParameter
        raise AssertionError("test not implemented")


class CIMParameterSort(unittest.TestCase):

    @unimplemented
    def test_all(self):
        # TODO Implement sorting test for CIMParameter
        raise AssertionError("test not implemented")


class Test_CIMParameter_str(object):
    """
    Test `CIMParameter.__str__()`.
    """

    def test_all(self):

        obj = CIMParameter('Param1', 'uint32')

        s = str(obj)

        assert re.match(r'^CIMParameter\(', s)
        assert 'name=%r' % obj.name in s
        assert 'type=%r' % obj.type in s
        assert 'reference_class=%r' % obj.reference_class in s
        assert 'is_array=%r' % obj.is_array in s


class Test_CIMParameter_repr(object):
    """
    Test `CIMParameter.__repr__()`.
    """

    def test_all(self):

        obj = CIMParameter('Param1', 'uint32')

        r = repr(obj)

        assert re.match(r'^CIMParameter\(', r)
        assert 'name=%r' % obj.name in r
        assert 'type=%r' % obj.type in r
        assert 'reference_class=%r' % obj.reference_class in r
        assert 'is_array=%r' % obj.is_array in r
        assert 'array_size=%r' % obj.array_size in r
        assert 'qualifiers=' in r


class CIMParameterToXML(ValidationTestCase):

    def test_all(self):

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


class InitCIMQualifierDeclaration(unittest.TestCase):
    """Test construction of CIMQualifierDeclarations."""

    def test_all(self):
        """Test the constructor options."""

        # Initialization with name being None

        if CHECK_0_12_0:
            with self.assertRaises(ValueError):
                CIMQualifierDeclaration(None, 'string')
        else:
            # Before 0.12.0, the implementation allowed the name to be None,
            # although the documentation required it not to be None.
            # We test the implemented behavior
            qd = CIMQualifierDeclaration(None, 'string')
            self.assertIs(qd.name, None)

        # Initialization with type being None

        if CHECK_0_12_0:
            with self.assertRaises(ValueError):
                CIMQualifierDeclaration('Qoo', None, value='abc')
        else:
            # Before 0.12.0, the implementation allowed the type to be None,
            # although the documentation required it not to be None.
            # We test the implemented behavior
            qd = CIMQualifierDeclaration('Qoo', None, value='abc')
            self.assertIs(qd.type, None)

        # Some normal cases

        CIMQualifierDeclaration('FooQualDecl', 'uint32')

        CIMQualifierDeclaration('FooQualDecl', 'string', value='my string')

        CIMQualifierDeclaration('FooQualDecl', 'string', is_array=True,
                                array_size=4,
                                overridable=True, tosubclass=True,
                                toinstance=True, translatable=False)

        scopes = {'CLASS': False, 'ANY': False, 'ASSOCIATION': False}
        CIMQualifierDeclaration('FooQualDecl', 'uint64', is_array=True,
                                array_size=4, scopes=scopes,
                                overridable=True, tosubclass=True,
                                toinstance=True, translatable=False)

        CIMQualifierDeclaration('FooQualDecl', 'uint32', is_array=True,
                                value=[Uint32(x) for x in [1, 2, 3]],
                                overridable=True, tosubclass=True,
                                toinstance=True, translatable=False)

        CIMQualifierDeclaration('FooQualDecl', 'uint32', is_array=False,
                                value=Uint32(3),
                                overridable=True, tosubclass=True,
                                toinstance=True, translatable=False)

        # Check unspecified is_array

        if CHECK_0_12_0:

            # Check that a value of None results in a scalar
            qd = CIMQualifierDeclaration('FooQualDecl', 'uint32', value=None,
                                         is_array=None)
            self.assertEqual(qd.is_array, False)

            # Check that a scalar value results in a scalar
            qd = CIMQualifierDeclaration('FooQualDecl', 'uint32', value=42,
                                         is_array=None)
            self.assertEqual(qd.is_array, False)

            # Check that an array value results in an array
            qd = CIMQualifierDeclaration('FooQualDecl', 'uint32', value=[42],
                                         is_array=None)
            self.assertEqual(qd.is_array, True)

        else:

            with self.assertRaises(ValueError):
                CIMQualifierDeclaration('FooQualDecl', 'uint32', value=None,
                                        is_array=None)
            with self.assertRaises(ValueError):
                CIMQualifierDeclaration('FooQualDecl', 'uint32', value=42,
                                        is_array=None)
            with self.assertRaises(ValueError):
                CIMQualifierDeclaration('FooQualDecl', 'uint32', value=[42],
                                        is_array=None)

    def test_errors(self):
        """Test constructors that should generate errors"""

        try:
            CIMQualifierDeclaration('is_arraySizeMismatch', 'string',
                                    is_array=False,
                                    array_size=4,
                                    overridable=True, tosubclass=True,
                                    toinstance=True, translatable=False)
            self.fail('Exception expected')
        except ValueError:
            pass

        try:
            CIMQualifierDeclaration('is_arrayValueMismatch', 'uint32',
                                    is_array=False,
                                    value=[Uint32(x) for x in [1, 2, 3]],
                                    overridable=True, tosubclass=True,
                                    toinstance=True, translatable=False)
            self.fail('Exception expected')
        except ValueError:
            pass

        try:
            CIMQualifierDeclaration('is_arrayValueMismatch', 'uint32',
                                    is_array=True,
                                    value=Uint32(3),
                                    overridable=True, tosubclass=True,
                                    toinstance=True, translatable=False)
            self.fail('Exception expected')
        except ValueError:
            pass


class CopyCIMQualifierDeclaration(unittest.TestCase):

    def test_all(self):

        qd = CIMQualifierDeclaration('FooQualDecl', 'uint32')
        c = qd.copy()
        self.assertEqual(qd, c)

        scopes = {'CLASS': False, 'ANY': False, 'ASSOCIATION': False}
        qd = CIMQualifierDeclaration('FooQualDecl', 'string', is_array=True,
                                     array_size=4, scopes=scopes,
                                     overridable=True, tosubclass=True,
                                     toinstance=True, translatable=False)
        c = qd.copy()
        self.assertEqual(qd, c)


class CIMQualifierDeclarationAttrs(unittest.TestCase):

    def test_all(self):

        obj = CIMQualifierDeclaration('Foo', 'string')

        # Setting the name to None
        if CHECK_0_12_0:
            with self.assertRaises(ValueError):
                obj.name = None
        else:
            # Before 0.12.0, the implementation allowed the name to be
            # None, although the documentation required it not to be None.
            # We test the implemented behavior.
            obj.name = None
            self.assertIs(obj.name, None)

        # Setting the type to None
        if CHECK_0_12_0:
            with self.assertRaises(ValueError):
                obj.type = None
        else:
            # Before 0.12.0, the implementation allowed the type to be None,
            # although the documentation required it not to be None.
            # We test the implemented behavior
            obj.type = None
            self.assertIs(obj.type, None)


class CIMQualifierDeclarationEquality(unittest.TestCase):

    def test_all(self):
        self.assertEqual(CIMQualifierDeclaration('FooQualDecl', 'uint32'),
                         CIMQualifierDeclaration('FooQualDecl', 'uint32'))

        self.assertNotEqual(
            CIMQualifierDeclaration('FooQualDecl1', 'uint32'),
            CIMQualifierDeclaration('FooQualDecl2', 'uint32'))

        scopes = {'CLASS': False, 'ANY': False, 'ASSOCIATION': False}
        self.assertEqual(
            CIMQualifierDeclaration('FooQualDecl', 'string', is_array=True,
                                    array_size=4, scopes=scopes,
                                    overridable=True, tosubclass=True,
                                    toinstance=True, translatable=False),
            CIMQualifierDeclaration('FooQualDecl', 'string', is_array=True,
                                    array_size=4, scopes=scopes,
                                    overridable=True, tosubclass=True,
                                    toinstance=True, translatable=False))
        self.assertNotEqual(
            CIMQualifierDeclaration('FooQualDecl', 'string', is_array=True,
                                    array_size=4, scopes=scopes,
                                    overridable=True, tosubclass=True,
                                    toinstance=True, translatable=False),
            CIMQualifierDeclaration('FooQualDecl', 'string', is_array=True,
                                    array_size=5, scopes=scopes,
                                    overridable=True, tosubclass=True,
                                    toinstance=True, translatable=False))
        self.assertNotEqual(
            CIMQualifierDeclaration('FooQualDecl', 'string', is_array=True,
                                    array_size=4,
                                    overridable=True, tosubclass=True,
                                    toinstance=True, translatable=False),
            CIMQualifierDeclaration('FooQualDecl', 'string', is_array=True,
                                    array_size=4, scopes=scopes,
                                    overridable=True, tosubclass=True,
                                    toinstance=True, translatable=False))
        self.assertNotEqual(
            CIMQualifierDeclaration('FooQualDecl', 'string', is_array=True,
                                    array_size=4, scopes=scopes,
                                    overridable=True, tosubclass=True,
                                    toinstance=True, translatable=False),
            CIMQualifierDeclaration('FooQualDecl', 'string', is_array=True,
                                    array_size=4, scopes=scopes,
                                    overridable=False, tosubclass=True,
                                    toinstance=True, translatable=False))

        # TODO ks Dec 16. Add more equality tests.

        # Verify detection of incorrect type of second object

        with pytest.raises(TypeError):
            # pylint: disable=expression-not-assigned
            CIMQualifierDeclaration('FooQualDecl', 'string') == 'FooQualDecl'


class CIMQualifierDeclarationCompare(unittest.TestCase):
    # pylint: disable=invalid-name

    @unimplemented
    def test_all(self):
        # TODO Implement ordering comparison test for CIMQualifierDeclaration
        raise AssertionError("test not implemented")


class CIMQualifierDeclarationSort(unittest.TestCase):

    @unimplemented
    def test_all(self):
        # TODO Implement sorting test for CIMQualifierDeclaration
        raise AssertionError("test not implemented")


class Test_CIMQualifierDeclaration_str(object):
    """
    Test `CIMQualifierDeclaration.__str__()`.
    """

    def test_all(self):

        obj = CIMQualifierDeclaration(
            'FooQualDecl', 'string', is_array=True, array_size=4,
            scopes=dict(CLASS=True), overridable=True, tosubclass=True,
            toinstance=True, translatable=False)

        s = str(obj)

        assert re.match(r'^CIMQualifierDeclaration\(', s)
        assert 'name=%r' % obj.name in s
        assert 'value=%r' % obj.value in s
        assert 'type=%r' % obj.type in s
        assert 'is_array=%r' % obj.is_array in s


class Test_CIMQualifierDeclaration_repr(object):
    """
    Test `CIMQualifierDeclaration.__repr__()`.
    """

    def test_all(self):

        obj = CIMQualifierDeclaration(
            'FooQualDecl', 'string', is_array=True, array_size=4,
            scopes=dict(CLASS=True), overridable=True, tosubclass=True,
            toinstance=True, translatable=False)

        r = repr(obj)

        assert re.match(r'^CIMQualifierDeclaration\(', r)
        assert 'name=%r' % obj.name in r
        assert 'value=%r' % obj.value in r
        assert 'type=%r' % obj.type in r
        assert 'is_array=%r' % obj.is_array in r
        assert 'array_size=%r' % obj.array_size in r
        assert 'scopes=%r' % obj.scopes in r
        assert 'tosubclass=%r' % obj.tosubclass in r
        assert 'overridable=%r' % obj.overridable in r
        assert 'translatable=%r' % obj.translatable in r
        assert 'toinstance=%r' % obj.toinstance in r


class CIMQualifierDeclarationToXML(unittest.TestCase):

    @unimplemented
    def test_all(self):
        # TODO Implement tocimxml() test for CIMQualifierDeclaration
        raise AssertionError("test not implemented")


class Test_tocimxml(object):

    @unimplemented
    def test_all(self):
        # TODO Implement tocimxml() test for remaining types
        # (bool, invalid array, other invalid cases)
        raise AssertionError("test not implemented")


class ToCIMObj(unittest.TestCase):

    def test_all(self):
        path = cim_obj.tocimobj(
            'reference',
            "Acme_OS.Name=\"acmeunit\",SystemName=\"UnixHost\"")
        self.assertTrue(isinstance(path, CIMInstanceName))
        self.assertEqual(path.classname, 'Acme_OS')
        self.assertEqual(path['Name'], 'acmeunit')
        self.assertEqual(path['SystemName'], 'UnixHost')
        self.assertEqual(len(path.keybindings), 2)
        self.assertTrue(path.namespace is None)
        self.assertTrue(path.host is None)

        path = cim_obj.tocimobj(
            'reference',
            "Acme_User.uid=33,OSName=\"acmeunit\","
            "SystemName=\"UnixHost\"")
        self.assertTrue(isinstance(path, CIMInstanceName))
        self.assertTrue(path.namespace is None)
        self.assertTrue(path.host is None)
        self.assertEqual(path.classname, 'Acme_User')
        self.assertEqual(path['uid'], 33)
        self.assertEqual(path['OSName'], 'acmeunit')
        self.assertEqual(path['SystemName'], 'UnixHost')
        self.assertEqual(len(path.keybindings), 3)

        path = cim_obj.tocimobj(
            'reference',
            'HTTP://CIMOM_host/root/CIMV2:CIM_Disk.key1="value1"')
        self.assertTrue(isinstance(path, CIMInstanceName))
        self.assertEqual(path.namespace, 'root/CIMV2')
        self.assertEqual(path.host, 'CIMOM_host')
        self.assertEqual(path.classname, 'CIM_Disk')
        self.assertEqual(path['key1'], 'value1')
        self.assertEqual(len(path.keybindings), 1)

        path = cim_obj.tocimobj(
            'reference',
            "ex_sampleClass.label1=9921,label2=8821")
        self.assertTrue(isinstance(path, CIMInstanceName))
        self.assertTrue(path.namespace is None)
        self.assertTrue(path.host is None)
        self.assertEqual(path.classname, 'ex_sampleClass')
        self.assertEqual(path['label1'], 9921)
        self.assertEqual(path['label2'], 8821)
        self.assertEqual(len(path.keybindings), 2)

        path = cim_obj.tocimobj('reference', "ex_sampleClass")
        self.assertTrue(isinstance(path, CIMClassName))
        self.assertTrue(path.namespace is None)
        self.assertTrue(path.host is None)
        self.assertEqual(path.classname, 'ex_sampleClass')

        path = cim_obj.tocimobj(
            'reference',
            '//./root/default:LogicalDisk.SystemName="acme",'
            'LogicalDisk.Drive="C"')
        self.assertTrue(isinstance(path, CIMInstanceName))
        self.assertEqual(path.namespace, 'root/default')
        self.assertEqual(path.host, '.')
        self.assertEqual(path.classname, 'LogicalDisk')
        self.assertEqual(path['SystemName'], 'acme')
        self.assertEqual(path['Drive'], 'C')
        self.assertEqual(len(path.keybindings), 2)

        path = cim_obj.tocimobj(
            'reference',
            "X.key1=\"John Smith\",key2=33.3")
        self.assertTrue(isinstance(path, CIMInstanceName))
        self.assertTrue(path.namespace is None)
        self.assertTrue(path.host is None)
        self.assertEqual(path.classname, 'X')
        self.assertEqual(path['key1'], 'John Smith')
        self.assertEqual(path['key2'], 33.3)

        path = cim_obj.tocimobj(
            'reference',
            "//./root/default:NetworkCard=2")
        # TODO How should pywbem deal with a single, unnamed, keybinding?
        # self.assertTrue(isinstance(path, CIMInstanceName))
        # self.assertEqual(path.namespace, 'root/default')
        # self.assertEqual(path.host, '.')
        # self.assertEqual(path.classname, 'NetworkCard')


class Test_cimvalue(object):
    """
    Test `cimvalue()`.
    """

    max_uint8 = 2**8 - 1
    max_uint16 = 2**16 - 1
    max_uint32 = 2**32 - 1
    max_uint64 = 2**64 - 1

    min_sint8 = -2**7
    min_sint16 = -2**15
    min_sint32 = -2**31
    min_sint64 = -2**63

    max_sint8 = 2**7 - 1
    max_sint16 = 2**15 - 1
    max_sint32 = 2**31 - 1
    max_sint64 = 2**63 - 1

    datetime1_dt = datetime(2014, 9, 22, 10, 49, 20, 524789)
    datetime1_str = '20140922104920.524789+000'
    datetime1_obj = CIMDateTime(datetime1_dt)

    timedelta1_td = timedelta(183, (13 * 60 + 25) * 60 + 42, 234567)
    timedelta1_str = '00000183132542.234567:000'
    timedelta1_obj = CIMDateTime(timedelta1_td)

    ref1_str = 'http://host/ns:CN.k1=42'
    ref1_obj = CIMInstanceName(classname='CN', keybindings=dict(k1=42),
                               namespace='ns', host='host')

    @pytest.mark.parametrize(
        "value, type, exp_obj", [

            # Type is None (and is inferred from the value)

            (None, None, None),

            (u'a', None, u'a'),
            (b'a', None, u'a'),
            ('true', None, 'true'),
            ('false', None, 'false'),
            (datetime1_str, None, datetime1_str),
            (timedelta1_str, None, timedelta1_str),
            (ref1_str, None, ref1_str),

            (True, None, True),
            (False, None, False),

            (datetime1_dt, None, datetime1_obj),
            (timedelta1_td, None, timedelta1_obj),

            # Type is string

            (None, 'string', None),

            (u'', 'string', u''),
            (u'a', 'string', u'a'),
            (u'abc', 'string', u'abc'),
            (u'\u00E4', 'string', u'\u00E4'),  # U+00E4 = lower case a umlaut

            (b'', 'string', u''),
            (b'a', 'string', u'a'),
            (b'abc', 'string', u'abc'),

            # Type is char16

            (None, 'char16', None),

            (u'', 'char16', u''),
            (u'a', 'char16', u'a'),
            (u'\u00E4', 'char16', u'\u00E4'),  # U+00E4 = lower case a umlaut

            (b'', 'char16', u''),
            (b'a', 'char16', u'a'),

            # Type is boolean

            (None, 'boolean', None),

            (True, 'boolean', True),
            (False, 'boolean', False),

            ('abc', 'boolean', True),
            ('true', 'boolean', True),  # No special treatment of that string
            ('false', 'boolean', True),  # No special treatment of that string
            ('', 'boolean', False),

            (0, 'boolean', False),
            (1, 'boolean', True),
            (-1, 'boolean', True),

            # Type is an unsigned integer

            (None, 'uint8', None),
            (0, 'uint8', Uint8(0)),
            (max_uint8, 'uint8', Uint8(max_uint8)),
            (Uint8(0), 'uint8', Uint8(0)),
            (Uint8(max_uint8), 'uint8', Uint8(max_uint8)),

            (None, 'uint16', None),
            (0, 'uint16', Uint16(0)),
            (max_uint16, 'uint16', Uint16(max_uint16)),
            (Uint16(0), 'uint16', Uint16(0)),
            (Uint16(max_uint16), 'uint16', Uint16(max_uint16)),

            (None, 'uint32', None),
            (0, 'uint32', Uint32(0)),
            (max_uint32, 'uint32', Uint32(max_uint32)),
            (Uint32(0), 'uint32', Uint32(0)),
            (Uint32(max_uint32), 'uint32', Uint32(max_uint32)),

            (None, 'uint64', None),
            (0, 'uint64', Uint64(0)),
            (max_uint64, 'uint64', Uint64(max_uint64)),
            (Uint64(0), 'uint64', Uint64(0)),
            (Uint64(max_uint64), 'uint64', Uint64(max_uint64)),

            # Type is a signed integer

            (None, 'sint8', None),
            (min_sint8, 'sint8', Sint8(min_sint8)),
            (max_sint8, 'sint8', Sint8(max_sint8)),
            (Sint8(min_sint8), 'sint8', Sint8(min_sint8)),
            (Sint8(max_sint8), 'sint8', Sint8(max_sint8)),

            (None, 'sint16', None),
            (min_sint16, 'sint16', Sint16(min_sint16)),
            (max_sint16, 'sint16', Sint16(max_sint16)),
            (Sint16(min_sint16), 'sint16', Sint16(min_sint16)),
            (Sint16(max_sint16), 'sint16', Sint16(max_sint16)),

            (None, 'sint32', None),
            (min_sint32, 'sint32', Sint32(min_sint32)),
            (max_sint32, 'sint32', Sint32(max_sint32)),
            (Sint32(min_sint32), 'sint32', Sint32(min_sint32)),
            (Sint32(max_sint32), 'sint32', Sint32(max_sint32)),

            (None, 'sint64', None),
            (min_sint64, 'sint64', Sint64(min_sint64)),
            (max_sint64, 'sint64', Sint64(max_sint64)),
            (Sint64(min_sint64), 'sint64', Sint64(min_sint64)),
            (Sint64(max_sint64), 'sint64', Sint64(max_sint64)),

            # Type is a real

            (None, 'real32', None),
            (0, 'real32', Real32(0)),
            (3.14, 'real32', Real32(3.14)),
            (-42E7, 'real32', Real32(-42E7)),
            (-42E-7, 'real32', Real32(-42E-7)),

            (None, 'real64', None),
            (0, 'real64', Real64(0)),
            (3.14, 'real64', Real64(3.14)),
            (-42E7, 'real64', Real64(-42E7)),
            (-42E-7, 'real64', Real64(-42E-7)),

            # Type is datetime

            (None, 'datetime', None),

            (datetime1_dt, 'datetime', datetime1_obj),
            (datetime1_str, 'datetime', datetime1_obj),
            (datetime1_obj, 'datetime', datetime1_obj),

            (timedelta1_td, 'datetime', timedelta1_obj),
            (timedelta1_str, 'datetime', timedelta1_obj),
            (timedelta1_obj, 'datetime', timedelta1_obj),

            # Type is reference

            (None, 'reference', None),

            (ref1_str, 'reference', ref1_obj),
            (ref1_obj, 'reference', ref1_obj),
        ]
    )
    def test_succeeds(self, value, type, exp_obj):
        # pylint: disable=redefined-builtin
        """All test cases for cimvalue() that succeed."""

        if CHECK_0_12_0:

            obj = cimvalue(value, type)

            assert obj == exp_obj

    @pytest.mark.parametrize(
        "value, type, exp_exc", [
            (42, None, TypeError),  # invalid type of value
            (-42, None, TypeError),
            (0, None, TypeError),
            (42.1, None, TypeError),

            ('abc', 'foo', ValueError),  # invalid CIM type name

            ('000000:000', 'datetime', ValueError),  # invalid dt value

            ('foo', 'reference', ValueError),  # invalid ref value
            (CIMClassName('CIM_Foo'), 'reference', TypeError),  # invalid type
        ]
    )
    def test_fails(self, value, type, exp_exc):
        # pylint: disable=redefined-builtin
        """All test cases for cimvalue() that fail."""

        if CHECK_0_12_0:

            with pytest.raises(Exception) as exc_info:

                cimvalue(value, type)

            exc = exc_info.value
            assert isinstance(exc, exp_exc)


class MofStr(unittest.TestCase):
    """Test cases for mofstr()."""

    def _run_single(self, in_value, exp_value):
        '''
        Test function for single invocation of mofstr()
        '''

        ret_value = cim_obj.mofstr(in_value)

        self.assertEqual(ret_value, exp_value)

    def test_all(self):
        '''
        Run all tests for mofstr().
        '''

        # Note: The following literal strings use normal Python escaping.

        # Some standard cases
        self._run_single('', '""')
        self._run_single('c', '"c"')
        self._run_single('c d', '"c d"')

        # Whitespace
        self._run_single(' c', '" c"')
        self._run_single('c ', '"c "')
        self._run_single(' ', '" "')
        self._run_single('c  d', '"c  d"')

        # Single quote (gets escaped)
        self._run_single('\'', '"\\\'"')
        self._run_single('c\'d', '"c\\\'d"')
        self._run_single('c\'\'d', '"c\\\'\\\'d"')

        # Double quote (gets escaped)
        self._run_single('"', '"\\""')
        self._run_single('c"d', '"c\\"d"')
        self._run_single('c""d', '"c\\"\\"d"')

        # Backslash character (gets escaped)
        self._run_single('\\', '"\\\\"')
        self._run_single('\\c', '"\\\\c"')
        self._run_single('c\\', '"c\\\\"')
        self._run_single('c\\d', '"c\\\\d"')
        self._run_single('c\\\\d', '"c\\\\\\\\d"')

        # Other MOF-escapable characters (get escaped)
        self._run_single('\b', '"\\b"')
        self._run_single('\t', '"\\t"')
        self._run_single('\n', '"\\n"')
        self._run_single('\f', '"\\f"')
        self._run_single('\r', '"\\r"')
        self._run_single('c\bd', '"c\\bd"')
        self._run_single('c\td', '"c\\td"')
        self._run_single('c\nd', '"c\\nd"')
        self._run_single('c\fd', '"c\\fd"')
        self._run_single('c\rd', '"c\\rd"')

        # An already MOF-escaped sequence.
        # Such a sequence is treated as separate characters, i.e. backslash
        # gets escaped, and the following char gets escaped on its own.
        # These sequences were treated specially before v0.9, by parsing them
        # as already-escaped MOF sequences and passing them through unchanged.
        self._run_single('\\b', '"\\\\b"')
        self._run_single('\\t', '"\\\\t"')
        self._run_single('\\n', '"\\\\n"')
        self._run_single('\\f', '"\\\\f"')
        self._run_single('\\r', '"\\\\r"')
        self._run_single('\\\'', '"\\\\\\\'"')  # escape the following quote
        self._run_single('\\"', '"\\\\\\""')  # escape the following quote
        self._run_single('c\\bd', '"c\\\\bd"')
        self._run_single('c\\td', '"c\\\\td"')
        self._run_single('c\\nd', '"c\\\\nd"')
        self._run_single('c\\fd', '"c\\\\fd"')
        self._run_single('c\\rd', '"c\\\\rd"')
        self._run_single('c\\\'d', '"c\\\\\\\'d"')  # escape the following quote
        self._run_single('c\\"d', '"c\\\\\\"d"')  # escape the following quote

        # Backslash followed by MOF-escapable character (are treated separately)
        self._run_single('\\\b', '"\\\\\\b"')
        self._run_single('\\\t', '"\\\\\\t"')
        self._run_single('\\\n', '"\\\\\\n"')
        self._run_single('\\\f', '"\\\\\\f"')
        self._run_single('\\\r', '"\\\\\\r"')
        self._run_single('c\\\bd', '"c\\\\\\bd"')
        self._run_single('c\\\td', '"c\\\\\\td"')
        self._run_single('c\\\nd', '"c\\\\\\nd"')
        self._run_single('c\\\fd', '"c\\\\\\fd"')
        self._run_single('c\\\rd', '"c\\\\\\rd"')

        # Control character (get escaped)
        self._run_single(u'\u0001', '"\\x0001"')
        self._run_single(u'\u0002', '"\\x0002"')
        self._run_single(u'\u0003', '"\\x0003"')
        self._run_single(u'\u0004', '"\\x0004"')
        self._run_single(u'\u0005', '"\\x0005"')
        self._run_single(u'\u0006', '"\\x0006"')
        self._run_single(u'\u0007', '"\\x0007"')
        self._run_single(u'\u0008', '"\\b"')
        self._run_single(u'\u0009', '"\\t"')
        self._run_single(u'\u000A', '"\\n"')
        self._run_single(u'\u000B', '"\\x000B"')
        self._run_single(u'\u000C', '"\\f"')
        self._run_single(u'\u000D', '"\\r"')
        self._run_single(u'\u000E', '"\\x000E"')
        self._run_single(u'\u000F', '"\\x000F"')
        self._run_single(u'\u0010', '"\\x0010"')
        self._run_single(u'\u0011', '"\\x0011"')
        self._run_single(u'\u0012', '"\\x0012"')
        self._run_single(u'\u0013', '"\\x0013"')
        self._run_single(u'\u0014', '"\\x0014"')
        self._run_single(u'\u0015', '"\\x0015"')
        self._run_single(u'\u0016', '"\\x0016"')
        self._run_single(u'\u0017', '"\\x0017"')
        self._run_single(u'\u0018', '"\\x0018"')
        self._run_single(u'\u0019', '"\\x0019"')
        self._run_single(u'\u001A', '"\\x001A"')
        self._run_single(u'\u001B', '"\\x001B"')
        self._run_single(u'\u001C', '"\\x001C"')
        self._run_single(u'\u001D', '"\\x001D"')
        self._run_single(u'\u001E', '"\\x001E"')
        self._run_single(u'\u001F', '"\\x001F"')
        self._run_single(u'\u0020', '" "')

        # Line break cases

        self._run_single(
            # |2                                                          |60
            'the big brown fox jumps over a big brown fox jumps over a big' \
            ' brown f jumps over a big brown fox', \
            '"the big brown fox jumps over a big brown fox jumps over a big' \
            ' brown f "\n' \
            '    "jumps over a big brown fox"')

        self._run_single(
            # |2                                                          |60
            'the big brown fox jumps over a big brown fox jumps over a big' \
            ' brown fo jumps over a big brown fox', \
            '"the big brown fox jumps over a big brown fox jumps over a big' \
            ' brown fo "\n' \
            '    "jumps over a big brown fox"')

        self._run_single(
            # |2                                                          |60
            'the big brown fox jumps over a big brown fox jumps over a big' \
            ' brown fox jumps over a big brown fox', \
            '"the big brown fox jumps over a big brown fox jumps over a big' \
            ' brown fox "\n' \
            '    "jumps over a big brown fox"')

        self._run_single(
            # |2                                                          |60
            'the big brown fox jumps over a big brown fox jumps over a big' \
            ' brown foxx jumps over a big brown fox', \
            '"the big brown fox jumps over a big brown fox jumps over a big' \
            ' brown foxx "\n' \
            '    "jumps over a big brown fox"')
        self._run_single(
            # |2                                                          |60
            'the big brown fox jumps over a big brown fox jumps over a big' \
            ' brown foxxx jumps over a big brown fox', \
            '"the big brown fox jumps over a big brown fox jumps over a big' \
            ' brown "\n' \
            '    "foxxx jumps over a big brown fox"')

        # TODO: This may be wrong in that it breaks a word, not between words.
        self._run_single(
            # |2                                                          |60
            'the_big_brown_fox_jumps_over_a_big_brown_fox_jumps_over_a_big' \
            '_brown_fox_jumps_over a big brown fox', \
            '"the_big_brown_fox_jumps_over_a_big_brown_fox_jumps_over_a_big' \
            '_brown_fox_j"\n' \
            '    "umps_over a big brown fox"')

        self._run_single(
            # |2                                                          |60
            'the big brown fox jumps over a big brown fox jumps over a big' \
            ' brown fox_jumps_over_a_big_brown_fox', \
            '"the big brown fox jumps over a big brown fox jumps over a big' \
            ' brown "\n' \
            '    "fox_jumps_over_a_big_brown_fox"')

        return 0


# Determine the directory where this module is located. This must be done
# before comfychair gets control, because it changes directories.
_MODULE_PATH = os.path.abspath(os.path.dirname(
    inspect.getfile(ValidationTestCase)))
