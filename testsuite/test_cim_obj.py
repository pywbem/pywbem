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

# Controls whether the new behavior for CIM objects in 0.12 is checked.
CHECK_0_12_0 = (__version__.split('.') > ['0', '11', '0'])

# Values for expected 'type' property; since 0.12 they are converted to unicode
exp_type_char16 = u'char16' if CHECK_0_12_0 else 'char16'
exp_type_string = u'string' if CHECK_0_12_0 else 'string'
exp_type_boolean = u'boolean' if CHECK_0_12_0 else 'boolean'
exp_type_uint8 = u'uint8' if CHECK_0_12_0 else 'uint8'
exp_type_uint16 = u'uint16' if CHECK_0_12_0 else 'uint16'
exp_type_uint32 = u'uint32' if CHECK_0_12_0 else 'uint32'
exp_type_uint64 = u'uint64' if CHECK_0_12_0 else 'uint64'
exp_type_sint8 = u'sint8' if CHECK_0_12_0 else 'sint8'
exp_type_sint16 = u'sint16' if CHECK_0_12_0 else 'sint16'
exp_type_sint32 = u'sint32' if CHECK_0_12_0 else 'sint32'
exp_type_sint64 = u'sint64' if CHECK_0_12_0 else 'sint64'
exp_type_real32 = u'real32' if CHECK_0_12_0 else 'real32'
exp_type_real64 = u'real64' if CHECK_0_12_0 else 'real64'
exp_type_datetime = u'datetime' if CHECK_0_12_0 else 'datetime'
exp_type_reference = u'reference' if CHECK_0_12_0 else 'reference'

# Values for expected 'embedded_object' property; since 0.12 they are converted
# to unicode
exp_eo_object = u'object' if CHECK_0_12_0 else 'object'
exp_eo_instance = u'instance' if CHECK_0_12_0 else 'instance'

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
    Test CIMInstanceName.__init__().

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

    def test_CIMInstanceName_init_pos_args(self):
        # pylint: disable=unused-argument
        """Test position of arguments in CIMInstanceName.__init__()."""

        keybindings = dict(P1=True)

        # The code to be tested
        obj = CIMInstanceName(
            'CIM_Foo',
            keybindings,
            'woot.com',
            'cimv2')

        assert obj.classname == u'CIM_Foo'
        assert obj.keybindings == NocaseDict(keybindings)
        assert obj.host == u'woot.com'
        assert obj.namespace == u'cimv2'

    testcases_succeeds = [
        # Testcases where CIMInstanceName.__init__() succeeds.
        # Each testcase has these items:
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
            "Verify keybinding with int value (before 0.12)",
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
            "since 0.12)",
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
            "Verify keybinding with float value (before 0.12)",
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
            "since 0.12)",
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

    @pytest.mark.parametrize(
        "desc, kwargs, exp_attrs, exp_warn_type, condition",
        testcases_succeeds
    )
    def test_CIMInstanceName_init_succeeds(
            self, desc, kwargs, exp_attrs, exp_warn_type, condition):
        # pylint: disable=unused-argument
        """All test cases where CIMInstanceName.__init__() succeeds."""

        if not condition:
            pytest.skip("Condition for test case not met")

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
        assert isinstance(obj.classname, type(exp_classname))

        assert obj.keybindings == exp_keybindings
        assert isinstance(obj.keybindings, type(exp_keybindings))

        assert obj.host == exp_host
        assert isinstance(obj.host, type(exp_host))

        assert obj.namespace == exp_namespace
        assert isinstance(obj.namespace, type(exp_namespace))

    testcases_fails = [
        # Testcases where CIMInstanceName.__init__() fails.
        # Each testcase has these items:
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
            "before 0.12",
            dict(
                classname='CIM_Foo',
                keybindings={None: 'abc'}),
            TypeError,
            not CHECK_0_12_0
        ),
        (
            "Verify that keybinding with name None fails (with ValueError "
            "since 0.12",
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
        (
            "Verify that keybinding with a value of an embedded class fails",
            dict(
                classname='CIM_Foo',
                keybindings=dict(K1=CIMClass('CIM_EmbClass'))),
            TypeError,
            CHECK_0_12_0
        ),
        (
            "Verify that keybinding with a value of an embedded instance fails",
            dict(
                classname='CIM_Foo',
                keybindings=dict(K1=CIMInstance('CIM_EmbInst'))),
            TypeError,
            CHECK_0_12_0
        ),
        (
            "Verify that keybinding with an array value fails",
            dict(
                classname='CIM_Foo',
                keybindings=dict(K1=[1, 2])),
            TypeError,
            CHECK_0_12_0
        ),
        (
            "Verify that keybinding with a value of some other unsupported "
            "object type (e.g. exception type) fails",
            dict(
                classname='CIM_Foo',
                keybindings=dict(K1=TypeError)),
            TypeError,
            CHECK_0_12_0
        ),
    ]

    @pytest.mark.parametrize(
        "desc, kwargs, exp_exc_type, condition",
        testcases_fails)
    def test_CIMInstanceName_init_fails(
            self, desc, kwargs, exp_exc_type, condition):
        # pylint: disable=unused-argument
        """All test cases where CIMInstanceName.__init__() fails."""

        if not condition:
            pytest.skip("Condition for test case not met")

        with pytest.raises(exp_exc_type):

            # The code to be tested
            CIMInstanceName(**kwargs)


class CIMInstanceNameCopy(unittest.TestCase, CIMObjectMixin):
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


class Test_CIMInstanceName_str(object):
    """
    Test CIMInstanceName.__str__().

    That function returns the instance path as a WBEM URI string.
    """

    testcases_single_key_succeeds = [
        # Testcases where CIMInstanceName.__str__() with single key succeeds.
        # Each testcase has these items:
        # * obj: CIMInstanceName object to be tested.
        # * exp_uri: Expected WBEM URI string.
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

    @pytest.mark.parametrize(
        "obj, exp_uri",
        testcases_single_key_succeeds)
    def test_CIMInstanceName_str_single_key_succeeds(
            self, obj, exp_uri):
        """All test cases where CIMInstanceName.__str__() with single key
        succeeds."""

        s = str(obj)

        assert s == exp_uri

    def test_CIMInstanceName_str_multi_key_succeeds(self):
        """A test case where CIMInstanceName.__str__() with multiple keys
        succeeds."""

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


class Test_CIMInstanceName_repr(object):
    """
    Test CIMInstanceName.__repr__().
    """

    testcases_succeeds = [
        # Testcases where CIMInstanceName.__repr__() succeeds.
        # Each testcase has these items:
        # * obj: CIMInstanceName object to be tested.
        (
            CIMInstanceName(
                classname='CIM_Foo',
                keybindings=None)
        ),
        (
            CIMInstanceName(
                classname='CIM_Foo',
                keybindings=dict())
        ),
        (
            CIMInstanceName(
                classname='CIM_Foo',
                keybindings=dict(InstanceID=None))
        ),
        (
            CIMInstanceName(
                classname='CIM_Foo',
                keybindings=dict(InstanceID='1234'))
        ),
        (
            CIMInstanceName(
                classname='CIM_Foo',
                keybindings=dict(InstanceID='1234'),
                namespace='cimv2')
        ),
        (
            CIMInstanceName(
                classname='CIM_Foo',
                keybindings=dict(InstanceID='1234'),
                namespace='root/cimv2',
                host='10.11.12.13:5989')
        ),
        (
            CIMInstanceName(
                classname='CIM_Foo',
                keybindings=dict(InstanceID='1234'),
                namespace='root/cimv2',
                host='jdd:test@10.11.12.13')
        ),
    ]

    @pytest.mark.parametrize(
        "obj",
        testcases_succeeds)
    def test_CIMInstanceName_repr_succeeds(self, obj):

        r = repr(obj)

        assert re.match(r'^CIMInstanceName\(', r)

        exp_classname = 'classname=%r' % obj.classname
        assert exp_classname in r

        assert 'keybindings=' in r
        if obj.keybindings:
            for key in obj.keybindings.keys():
                search_str = 'u?[\'"]%s[\'"]: ' % key
                assert re.search(search_str, r), "For key %r" % key

        exp_namespace = 'namespace=%r' % obj.namespace
        assert exp_namespace in r

        exp_host = 'host=%r' % obj.host
        assert exp_host in r


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
    Test CIMInstanceName.from_wbem_uri().
    """

    testcases_succeeds = [
        # Testcases where CIMInstanceName.from_wbem_uri() succeeds.
        # Each testcase has these items:
        # * uri: WBEM URI string to be tested.
        # * exp_obj: Expected CIMInstanceName object.
        (
            'https://jdd:test@10.11.12.13:5989/root/cimv2:CIM_Foo.k1="v1"',
            CIMInstanceName(
                classname='CIM_Foo',
                keybindings=dict(k1='v1'),
                namespace='root/cimv2',
                host='jdd:test@10.11.12.13:5989')
        ),
        (
            'https://10.11.12.13:5989/root/cimv2:CIM_Foo.k1="v1",k2="v2"',
            CIMInstanceName(
                classname='CIM_Foo',
                keybindings=dict(k1='v1', k2='v2'),
                namespace='root/cimv2',
                host='10.11.12.13:5989')
        ),
        (
            'http://10.11.12.13/root/cimv2:CIM_Foo.k1="v1"',
            CIMInstanceName(
                classname='CIM_Foo',
                keybindings=dict(k1='v1'),
                namespace='root/cimv2',
                host='10.11.12.13')
        ),
        (
            'http://10.11.12.13/cimv2:CIM_Foo.k1="v1"',
            CIMInstanceName(
                classname='CIM_Foo',
                keybindings=dict(k1='v1'),
                namespace='cimv2',
                host='10.11.12.13')
        ),
        (
            'http://10.11.12.13/cimv2:CIM_Foo.k1=42,k2=true,k3="abc",k4="42"',
            CIMInstanceName(
                classname='CIM_Foo',
                keybindings=dict(k1=42, k2=True, k3='abc', k4='42'),
                namespace='cimv2',
                host='10.11.12.13')
        ),
    ]

    @pytest.mark.parametrize(
        "uri, exp_obj",
        testcases_succeeds)
    def test_CIMInstanceName_from_wbem_uri_succeeds(self, uri, exp_obj):
        """All test cases where CIMInstanceName.from_wbem_uri() succeeds."""

        if CHECK_0_12_0:

            obj = CIMInstanceName.from_wbem_uri(uri)

            assert isinstance(obj, CIMInstanceName)

            assert obj.classname == exp_obj.classname
            assert isinstance(obj.classname, type(exp_obj.classname))

            assert obj.keybindings == exp_obj.keybindings
            assert isinstance(obj.keybindings, type(exp_obj.keybindings))

            assert obj.namespace == exp_obj.namespace
            assert isinstance(obj.namespace, type(exp_obj.namespace))

            assert obj.host == exp_obj.host
            assert isinstance(obj.host, type(exp_obj.host))

    testcases_fails = [
        # Testcases where CIMInstanceName.from_wbem_uri() fails.
        # Each testcase has these items:
        # * desc: Short testcase description.
        # * uri: WBEM URI string to be tested.
        # * exp_exc_type: Expected exception type.

        # TODO: Improve implementation to make it fail for the disabled cases.
        (
            "missing '/' after scheme",
            'https:/10.11.12.13:5989/cimv2:CIM_Foo.k1="v1"',
            ValueError
        ),
        # (
        #     "invalid scheme",
        #     'xyz://10.11.12.13:5989/cimv2:CIM_Foo.k1="v1"',
        #     ValueError
        # ),
        # (
        #     "invalid ';' between host and port",
        #     'https://10.11.12.13;5989/cimv2:CIM_Foo.k1="v1"',
        #     ValueError
        # ),
        (
            "invalid ':' between port and namespace",
            'https://10.11.12.13:5989:cimv2:CIM_Foo.k1="v1"',
            ValueError
        ),
        # (
        #     "invalid '.' between namespace and classname",
        #     'https://10.11.12.13:5989/cimv2.CIM_Foo.k1="v1"',
        #     ValueError
        # ),
        # (
        #     "invalid '/' between namespace and classname",
        #     'https://10.11.12.13:5989/cimv2/CIM_Foo.k1="v1"',
        #     ValueError
        # ),
        (
            "invalid ':' between classname and key k1",
            'https://10.11.12.13:5989/cimv2:CIM_Foo:k1="v1"',
            ValueError
        ),
        (
            "invalid '/' between classname and key k1",
            'https://10.11.12.13:5989/cimv2:CIM_Foo/k1="v1"',
            ValueError
        ),
        # (
        #     "invalid '.' between key k1 and key k2",
        #     'https://10.11.12.13:5989/cimv2:CIM_Foo.k1="v1".k2="v2"',
        #     ValueError
        # ),
        # (
        #     "invalid ':' between key k1 and key k2",
        #     'https://10.11.12.13:5989/cimv2:CIM_Foo.k1="v1":k2="v2"',
        #     ValueError
        # ),
        (
            "double quotes missing around value of key k2",
            'https://10.11.12.13:5989/cimv2:CIM_Foo.k1="v1".k2=v2',
            ValueError
        ),
        (
            "single quotes used around value of key k2",
            'https://10.11.12.13:5989/cimv2:CIM_Foo.k1="v1".k2=\'v2\'',
            ValueError
        ),
    ]

    @pytest.mark.parametrize(
        "desc, uri, exp_exc_type",
        testcases_fails)
    def test_CIMInstanceName_from_wbem_uri_fails(self, desc, uri, exp_exc_type):
        # pylint: disable=unused-argument
        """All test cases where CIMInstanceName.from_wbem_uri() fails."""

        if CHECK_0_12_0:

            with pytest.raises(exp_exc_type):
                CIMInstanceName.from_wbem_uri(uri)


class Test_CIMInstance_init(object):
    """
    Test CIMInstance.__init__().

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

    def test_CIMInstance_init_pos_args(self):
        # pylint: disable=unused-argument
        """Test position of arguments in CIMInstance.__init__()."""

        properties = dict(P1=CIMProperty('P1', value=True))
        qualifiers = dict(Q1=CIMQualifier('Q1', value=True))
        path = CIMInstanceName('CIM_Foo')

        # The code to be tested
        obj = CIMInstance(
            'CIM_Foo',
            properties,
            qualifiers,
            path,
            ['P1'])

        assert obj.classname == u'CIM_Foo'
        assert obj.properties == NocaseDict(properties)
        assert obj.qualifiers == NocaseDict(qualifiers)
        assert obj.path == path
        assert obj.property_list == ['p1']

    testcases_succeeds = [
        # Testcases where CIMInstance.__init__() succeeds.
        # Each testcase has these items:
        # * desc: Short testcase description.
        # * kwargs: Dict of keyword arguments for __init__().
        # * exp_attrs: Dict of expected attributes of resulting object.
        # * exp_warn_type: Expected warning type.
        # * condition: Condition for testcase to run.
        (
            "Verify that classname None is accepted (before 0.12)",
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

    @pytest.mark.parametrize(
        "desc, kwargs, exp_attrs, exp_warn_type, condition",
        testcases_succeeds)
    def test_CIMInstance_init_succeeds(
            self, desc, kwargs, exp_attrs, exp_warn_type, condition):
        # pylint: disable=unused-argument
        """All test cases where CIMInstance.__init__() succeeds."""

        if not condition:
            pytest.skip("Condition for test case not met")

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
        assert isinstance(obj.classname, type(exp_classname))

        assert obj.properties == exp_properties
        assert isinstance(obj.properties, type(exp_properties))

        assert obj.qualifiers == exp_qualifiers
        assert isinstance(obj.qualifiers, type(exp_qualifiers))

        assert obj.path == exp_path
        assert isinstance(obj.path, type(exp_path))

        assert obj.property_list == exp_property_list
        assert isinstance(obj.property_list, type(exp_property_list))

    testcases_fails = [
        # Testcases where CIMInstance.__init__() fails.
        # Each testcase has these items:
        # * desc: Short testcase description.
        # * kwargs: Dict of keyword arguments for __init__().
        # * exp_exc_type: Expected exception type.
        # * condition: Condition for testcase to run.
        (
            "Verify that classname None fails (since 0.12)",
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
            "(since 0.12)",
            dict(
                classname='CIM_Foo',
                properties=dict(P1=CIMProperty('P1_X', 'abc'))),
            ValueError,
            CHECK_0_12_0
        ),
        (
            "Verify that property with int value fails (with ValueError since "
            "0.12)",
            dict(
                classname='CIM_Foo',
                properties=dict(P1=42)),
            ValueError,
            CHECK_0_12_0
        ),
        (
            "Verify that property with int value fails (with TypeError before "
            "0.12)",
            dict(
                classname='CIM_Foo',
                properties=dict(P1=42)),
            TypeError,
            not CHECK_0_12_0
        ),
        (
            "Verify that property with float value fails (with ValueError "
            "since 0.12)",
            dict(
                classname='CIM_Foo',
                properties=dict(P1=42.1)),
            ValueError,
            CHECK_0_12_0
        ),
        (
            "Verify that property with float value fails (with TypeError "
            "before 0.12)",
            dict(
                classname='CIM_Foo',
                properties=dict(P1=42.1)),
            TypeError,
            not CHECK_0_12_0
        ),
        (
            "Verify that property with float value fails (on Python 2 only, "
            "with ValueError since 0.12)",
            dict(
                classname='CIM_Foo',
                properties=dict(P1=_Longint(42))),
            ValueError,
            six.PY2 and CHECK_0_12_0
        ),
        (
            "Verify that property with float value fails (on Python 2 only, "
            "with TypeError before 0.12)",
            dict(
                classname='CIM_Foo',
                properties=dict(P1=_Longint(42))),
            TypeError,
            six.PY2 and not CHECK_0_12_0
        ),
        (
            "Verify that qualifier with name None fails (with TypeError "
            "before 0.12)",
            dict(
                classname='CIM_Foo',
                qualifiers={None: 'abc'}),
            TypeError,
            not CHECK_0_12_0
        ),
        (
            "Verify that qualifier with name None fails (with ValueError "
            "since 0.12)",
            dict(
                classname='CIM_Foo',
                qualifiers={None: 'abc'}),
            ValueError,
            CHECK_0_12_0
        ),
        (
            "Verify that qualifier CIMQualifier with inconsistent name fails "
            "(since 0.12)",
            dict(
                classname='CIM_Foo',
                qualifiers=dict(Q1=CIMQualifier('Q1_X', 'abc'))),
            ValueError,
            CHECK_0_12_0
        ),
    ]

    @pytest.mark.parametrize(
        "desc, kwargs, exp_exc_type, condition",
        testcases_fails)
    def test_CIMInstance_init_fails(
            self, desc, kwargs, exp_exc_type, condition):
        # pylint: disable=unused-argument
        """All test cases where CIMInstance.__init__() fails."""

        if not condition:
            pytest.skip("Condition for test case not met")

        with pytest.raises(exp_exc_type):

            # The code to be tested
            CIMInstance(**kwargs)


class CIMInstanceCopy(unittest.TestCase):
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
    Test CIMInstance.__str__().

    That function returns for example::

       CIMInstance(classname=CIM_Foo, path=CIMINstanceName(...), ...)
    """

    instpath_1 = CIMInstanceName(
        'CIM_Foo',
        keybindings=dict(Name='Spottyfoot'))

    testcases_succeeds = [
        # Testcases where CIMInstance.__str__() succeeds.
        # Each testcase has these items:
        # * obj: CIMInstance object to be tested.
        (
            CIMInstance(
                classname='CIM_Foo')
        ),
        (
            CIMInstance(
                classname='CIM_Foo',
                properties=dict(
                    Name='Spottyfoot',
                    Ref1=CIMInstanceName('CIM_Bar')))
        ),
        (
            CIMInstance(
                classname='CIM_Foo',
                properties=dict(
                    Name='Spottyfoot',
                    Ref1=CIMInstanceName('CIM_Bar')),
                path=instpath_1)
        ),
    ]

    @pytest.mark.parametrize(
        "obj",
        testcases_succeeds)
    def test_CIMInstance_str_succeeds(self, obj):
        """All test cases where CIMInstance.__str__() succeeds."""

        s = str(obj)

        assert re.match(r'^CIMInstance\(', s)

        exp_classname = 'classname=%r' % obj.classname
        assert exp_classname in s

        exp_path = 'path=%r' % obj.path
        assert exp_path in s


class Test_CIMInstance_repr(object):
    """
    Test CIMInstance.__repr__().
    """

    instpath_1 = CIMInstanceName(
        'CIM_Foo',
        keybindings=dict(Name='Spottyfoot'))

    testcases_succeeds = [
        # Testcases where CIMInstance.__repr__() succeeds.
        # Each testcase has these items:
        # * obj: CIMInstance object to be tested.
        (
            CIMInstance(
                classname='CIM_Foo')
        ),
        (
            CIMInstance(
                classname='CIM_Foo',
                properties=dict(
                    Name='Spottyfoot',
                    Ref1=CIMInstanceName('CIM_Bar')))
        ),
        (
            CIMInstance(
                classname='CIM_Foo',
                properties=dict(
                    Name='Spottyfoot',
                    Ref1=CIMInstanceName('CIM_Bar')),
                path=instpath_1)
        ),
    ]

    @pytest.mark.parametrize(
        "obj",
        testcases_succeeds)
    def test_CIMInstance_repr_succeeds(self, obj):
        """All test cases where CIMInstance.__repr__() succeeds."""

        r = repr(obj)

        assert re.match(r'^CIMInstance\(', r)

        exp_classname = 'classname=%r' % obj.classname
        assert exp_classname in r

        exp_path = 'path=%r' % obj.path
        assert exp_path in r

        exp_properties = 'properties=%r' % obj.properties
        assert exp_properties in r

        exp_property_list = 'property_list=%r' % obj.property_list
        assert exp_property_list in r

        exp_qualifiers = 'qualifiers=%r' % obj.qualifiers
        assert exp_qualifiers in r


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


class Test_CIMProperty_init(object):
    """
    Test CIMProperty.__init__().

    On qualifiers: The full range of input variations is not tested, because
    we know that the input argument is just turned into a `NocaseDict` and
    otherwise left unchanged, so the full range testing is expected to be done
    in the test cases for `CIMQualifier`.

    Note: The inferring of the type attribute of CIMProperty changed over
    time: Before pywbem 0.8.1, a value of None required specifying a
    type. In 0.8.1, a rather complex logic was implemented that tried to
    be perfect in inferring unspecified input properties, at the price of
    considerable complexity. In 0.12.0, this complex logic was
    drastically simplified again. Some cases are still nicely inferred,
    but some less common cases now require specifying the type again.
    """

    _INT_TYPES = ['uint8', 'uint16', 'uint32', 'uint64',
                  'sint8', 'sint16', 'sint32', 'sint64']
    _REAL_TYPES = ['real32', 'real64']

    def test_CIMProperty_init_pos_args(self):
        # pylint: disable=unused-argument
        """Test position of arguments in CIMProperty.__init__()."""

        qualifiers = {'Key': CIMQualifier('Key', True)}

        # The code to be tested
        obj = CIMProperty(
            'FooProp',
            ['abc'],
            'string',
            'CIM_Origin',
            2,
            False,
            True,
            None,
            qualifiers,
            None)

        assert obj.name == u'FooProp'
        assert obj.value == [u'abc']
        assert obj.type == u'string'
        assert obj.class_origin == u'CIM_Origin'
        assert obj.array_size == 2
        assert obj.propagated is False
        assert obj.is_array is True
        assert obj.reference_class is None
        assert obj.qualifiers == NocaseDict(qualifiers)
        assert obj.embedded_object is None

    # Defaults to expect for attributes when not specified in testcase
    default_exp_attrs = dict(
        class_origin=None,
        array_size=None,
        propagated=None,
        is_array=False,
        reference_class=None,
        qualifiers=NocaseDict(),
        embedded_object=None
    )

    qualifier_Q1 = CIMQualifier('Q1', value='abc')

    # A timedelta and corresponding CIM datetime value
    timedelta_1 = timedelta(days=12345678, hours=22, minutes=44,
                            seconds=55, microseconds=654321)
    cim_timedelta_1 = '12345678224455.654321:000'

    # A datetime and corresponding CIM datetime value
    datetime_2 = datetime(year=2014, month=9, day=24, hour=19, minute=30,
                          second=40, microsecond=654321,
                          tzinfo=cim_types.MinutesFromUTC(120))
    cim_datetime_2 = '20140924193040.654321+120'

    emb_instance_1 = CIMInstance('CIM_Instance1')
    emb_class_1 = CIMClass('CIM_Class1')
    inst_path_1 = CIMInstanceName('CIM_Ref1')

    testcases_succeeds = [
        # Testcases where CIMProperty.__init__() succeeds.
        # Each testcase has these items:
        # * desc: Short testcase description.
        # * kwargs: Dict of keyword arguments for __init__().
        # * exp_attrs: Dict of expected attributes of resulting object.
        # * exp_warn_type: Expected warning type.
        # * condition: Condition for testcase to run.

        (
            "Verify that binary name is converted to unicode",
            dict(name=b'FooProp', value=u'abc'),
            dict(name=u'FooProp', value=u'abc', type=exp_type_string),
            None, True
        ),
        (
            "Verify that unicode name remains unicode",
            dict(name=u'FooProp', value=u'abc'),
            dict(name=u'FooProp', value=u'abc', type=exp_type_string),
            None, True
        ),

        # Initialization to CIM string type
        (
            "Verify binary string without type",
            dict(name=u'FooProp', value=b'abc'),
            dict(name=u'FooProp', value=u'abc', type=exp_type_string),
            None, True
        ),
        (
            "Verify unicode string without type",
            dict(name=u'FooProp', value=u'abc'),
            dict(name=u'FooProp', value=u'abc', type=exp_type_string),
            None, True
        ),
        (
            "Verify binary string with type",
            dict(name=u'FooProp', value=b'abc', type='string'),
            dict(name=u'FooProp', value=u'abc', type=u'string'),
            None, True
        ),
        (
            "Verify unicode string with type",
            dict(name=u'FooProp', value=u'abc', type='string'),
            dict(name=u'FooProp', value=u'abc', type=u'string'),
            None, True
        ),
        (
            "Verify None with type string",
            dict(name=u'FooProp', value=None, type='string'),
            dict(name=u'FooProp', value=None, type=u'string'),
            None, True
        ),

        # Initialization to CIM integer types
        (
            "Verify Uint8 value without type",
            dict(name=u'FooProp', value=Uint8(32)),
            dict(name=u'FooProp', value=Uint8(32), type=exp_type_uint8),
            None, True
        ),
        (
            "Verify Uint8 value with type uint8",
            dict(name=u'FooProp', value=Uint8(32), type='uint8'),
            dict(name=u'FooProp', value=Uint8(32), type=u'uint8'),
            None, True
        ),
        (
            "Verify None value with type uint8",
            dict(name=u'FooProp', value=None, type='uint8'),
            dict(name=u'FooProp', value=None, type=u'uint8'),
            None, True
        ),
        (
            "Verify Uint16 value without type",
            dict(name=u'FooProp', value=Uint16(32)),
            dict(name=u'FooProp', value=Uint16(32), type=exp_type_uint16),
            None, True
        ),
        (
            "Verify Uint16 value with type uint16",
            dict(name=u'FooProp', value=Uint16(32), type='uint16'),
            dict(name=u'FooProp', value=Uint16(32), type=u'uint16'),
            None, True
        ),
        (
            "Verify None value with type uint16",
            dict(name=u'FooProp', value=None, type='uint16'),
            dict(name=u'FooProp', value=None, type=u'uint16'),
            None, True
        ),
        (
            "Verify Uint32 value without type",
            dict(name=u'FooProp', value=Uint32(32)),
            dict(name=u'FooProp', value=Uint32(32), type=exp_type_uint32),
            None, True
        ),
        (
            "Verify Uint32 value with type uint32",
            dict(name=u'FooProp', value=Uint32(32), type='uint32'),
            dict(name=u'FooProp', value=Uint32(32), type=u'uint32'),
            None, True
        ),
        (
            "Verify None value with type uint32",
            dict(name=u'FooProp', value=None, type='uint32'),
            dict(name=u'FooProp', value=None, type=u'uint32'),
            None, True
        ),
        (
            "Verify Uint64 value without type",
            dict(name=u'FooProp', value=Uint64(32)),
            dict(name=u'FooProp', value=Uint64(32), type=exp_type_uint64),
            None, True
        ),
        (
            "Verify Uint64 value with type uint64",
            dict(name=u'FooProp', value=Uint64(32), type='uint64'),
            dict(name=u'FooProp', value=Uint64(32), type=u'uint64'),
            None, True
        ),
        (
            "Verify None value with type uint64",
            dict(name=u'FooProp', value=None, type='uint64'),
            dict(name=u'FooProp', value=None, type=u'uint64'),
            None, True
        ),
        (
            "Verify Sint8 value without type",
            dict(name=u'FooProp', value=Sint8(32)),
            dict(name=u'FooProp', value=Sint8(32), type=exp_type_sint8),
            None, True
        ),
        (
            "Verify Sint8 value with type sint8",
            dict(name=u'FooProp', value=Sint8(32), type='sint8'),
            dict(name=u'FooProp', value=Sint8(32), type=u'sint8'),
            None, True
        ),
        (
            "Verify None value with type sint8",
            dict(name=u'FooProp', value=None, type='sint8'),
            dict(name=u'FooProp', value=None, type=u'sint8'),
            None, True
        ),
        (
            "Verify Sint16 value without type",
            dict(name=u'FooProp', value=Sint16(32)),
            dict(name=u'FooProp', value=Sint16(32), type=exp_type_sint16),
            None, True
        ),
        (
            "Verify Sint16 value with type sint16",
            dict(name=u'FooProp', value=Sint16(32), type='sint16'),
            dict(name=u'FooProp', value=Sint16(32), type=u'sint16'),
            None, True
        ),
        (
            "Verify None value with type sint16",
            dict(name=u'FooProp', value=None, type='sint16'),
            dict(name=u'FooProp', value=None, type=u'sint16'),
            None, True
        ),
        (
            "Verify Sint32 value without type",
            dict(name=u'FooProp', value=Sint32(32)),
            dict(name=u'FooProp', value=Sint32(32), type=exp_type_sint32),
            None, True
        ),
        (
            "Verify Sint32 value with type sint32",
            dict(name=u'FooProp', value=Sint32(32), type='sint32'),
            dict(name=u'FooProp', value=Sint32(32), type=u'sint32'),
            None, True
        ),
        (
            "Verify None value with type sint32",
            dict(name=u'FooProp', value=None, type='sint32'),
            dict(name=u'FooProp', value=None, type=u'sint32'),
            None, True
        ),
        (
            "Verify Sint64 value without type",
            dict(name=u'FooProp', value=Sint64(32)),
            dict(name=u'FooProp', value=Sint64(32), type=exp_type_sint64),
            None, True
        ),
        (
            "Verify Sint64 value with type sint64",
            dict(name=u'FooProp', value=Sint64(32), type='sint64'),
            dict(name=u'FooProp', value=Sint64(32), type=u'sint64'),
            None, True
        ),
        (
            "Verify None value with type sint64",
            dict(name=u'FooProp', value=None, type='sint64'),
            dict(name=u'FooProp', value=None, type=u'sint64'),
            None, True
        ),

        # Initialization to CIM float types
        (
            "Verify Real32 value without type",
            dict(name=u'FooProp', value=Real32(32.0)),
            dict(name=u'FooProp', value=Real32(32.0), type=exp_type_real32),
            None, True
        ),
        (
            "Verify Real32 value with type real32",
            dict(name=u'FooProp', value=Real32(32.0), type='real32'),
            dict(name=u'FooProp', value=Real32(32.0), type=u'real32'),
            None, True
        ),
        (
            "Verify None value with type real32",
            dict(name=u'FooProp', value=None, type='real32'),
            dict(name=u'FooProp', value=None, type=u'real32'),
            None, True
        ),
        (
            "Verify Real64 value without type",
            dict(name=u'FooProp', value=Real64(32.0)),
            dict(name=u'FooProp', value=Real64(32.0), type=exp_type_real64),
            None, True
        ),
        (
            "Verify Real64 value with type real64",
            dict(name=u'FooProp', value=Real64(32.0), type='real64'),
            dict(name=u'FooProp', value=Real64(32.0), type=u'real64'),
            None, True
        ),
        (
            "Verify None value with type real64",
            dict(name=u'FooProp', value=None, type='real64'),
            dict(name=u'FooProp', value=None, type=u'real64'),
            None, True
        ),

        # Initialization to CIM boolean type
        (
            "Verify bool value True without type",
            dict(name=u'FooProp', value=True),
            dict(name=u'FooProp', value=True, type=exp_type_boolean),
            None, True
        ),
        (
            "Verify bool value True with type boolean",
            dict(name=u'FooProp', value=True, type='boolean'),
            dict(name=u'FooProp', value=True, type=u'boolean'),
            None, True
        ),
        (
            "Verify bool value False without type",
            dict(name=u'FooProp', value=False),
            dict(name=u'FooProp', value=False, type=exp_type_boolean),
            None, True
        ),
        (
            "Verify bool value False with type boolean",
            dict(name=u'FooProp', value=False, type='boolean'),
            dict(name=u'FooProp', value=False, type=u'boolean'),
            None, True
        ),
        (
            "Verify None value with type boolean",
            dict(name=u'FooProp', value=None, type='boolean'),
            dict(name=u'FooProp', value=None, type=u'boolean'),
            None, True
        ),

        # Initialization to CIM datetime type
        (
            "Verify timedelta interval value without type (since 0.8.1)",
            dict(name=u'FooProp', value=timedelta_1),
            dict(name=u'FooProp', value=CIMDateTime(cim_timedelta_1),
                 type=exp_type_datetime),
            None, True
        ),
        (
            "Verify timedelta interval value with type (since 0.8.1)",
            dict(name=u'FooProp', value=timedelta_1, type='datetime'),
            dict(name=u'FooProp', value=CIMDateTime(cim_timedelta_1),
                 type=u'datetime'),
            None, True
        ),
        (
            "Verify CIMDateTime interval value without type",
            dict(name=u'FooProp', value=CIMDateTime(timedelta_1)),
            dict(name=u'FooProp', value=CIMDateTime(cim_timedelta_1),
                 type=exp_type_datetime),
            None, True
        ),
        (
            "Verify CIMDateTime interval value with type",
            dict(name=u'FooProp', value=CIMDateTime(timedelta_1),
                 type='datetime'),
            dict(name=u'FooProp', value=CIMDateTime(cim_timedelta_1),
                 type=u'datetime'),
            None, True
        ),
        (
            "Verify CIM datetime string interval value with type",
            dict(name=u'FooProp', value=cim_timedelta_1,
                 type='datetime'),
            dict(name=u'FooProp', value=CIMDateTime(cim_timedelta_1),
                 type=u'datetime'),
            None, True
        ),
        (
            "Verify datetime point in time value without type (since 0.8.1)",
            dict(name=u'FooProp', value=datetime_2),
            dict(name=u'FooProp', value=CIMDateTime(cim_datetime_2),
                 type=exp_type_datetime),
            None, True
        ),
        (
            "Verify datetime point in time value with type (since 0.8.1)",
            dict(name=u'FooProp', value=datetime_2, type='datetime'),
            dict(name=u'FooProp', value=CIMDateTime(cim_datetime_2),
                 type=u'datetime'),
            None, True
        ),
        (
            "Verify CIMDateTime point in time value without type",
            dict(name=u'FooProp', value=CIMDateTime(datetime_2)),
            dict(name=u'FooProp', value=CIMDateTime(cim_datetime_2),
                 type=exp_type_datetime),
            None, True
        ),
        (
            "Verify CIMDateTime point in time value with type",
            dict(name=u'FooProp', value=CIMDateTime(datetime_2),
                 type='datetime'),
            dict(name=u'FooProp', value=CIMDateTime(cim_datetime_2),
                 type=u'datetime'),
            None, True
        ),
        (
            "Verify CIM datetime point in time string value with type",
            dict(name=u'FooProp', value=cim_datetime_2,
                 type='datetime'),
            dict(name=u'FooProp', value=CIMDateTime(cim_datetime_2),
                 type=u'datetime'),
            None, True
        ),

        # Initialization to CIM reference type
        (
            "Verify that reference_class None is permitted for reference type",
            dict(name=u'FooProp', value=None, type='reference',
                 reference_class=None),
            dict(name=u'FooProp', value=None, type=u'reference',
                 reference_class=None),
            None, True
        ),
        (
            "Verify that binary reference_class is converted to unicode",
            dict(name=u'FooProp', value=None, type='reference',
                 reference_class=b'CIM_Ref'),
            dict(name=u'FooProp', value=None, type=u'reference',
                 reference_class=u'CIM_Ref'),
            None, True
        ),
        (
            "Verify that unicode reference_class remains unicode",
            dict(name=u'FooProp', value=None, type='reference',
                 reference_class=u'CIM_Ref'),
            dict(name=u'FooProp', value=None, type=u'reference',
                 reference_class=u'CIM_Ref'),
            None, True
        ),
        (
            "Verify that reference type is implied from CIMInstanceName value "
            "(since 0.8.1)",
            dict(name=u'FooProp', value=inst_path_1),
            dict(name=u'FooProp', value=inst_path_1, type=exp_type_reference),
            None, True
        ),
        (
            "Verify normal case with value, type, reference_class specified",
            dict(name=u'FooProp', value=inst_path_1,
                 type='reference', reference_class=inst_path_1.classname),
            dict(name=u'FooProp', value=inst_path_1,
                 type=u'reference', reference_class=inst_path_1.classname),
            None, True
        ),
        (
            # This is just a rough test whether a WBEM URI string will be
            # converted into a CIMInstanceName object. A more thorough test
            # with variations of WBEM URI strings is in the test cases for
            # CIMInstanceName.from_wbem_uri().
            "Verify that WBEM URI string value is converted to CIMInstanceName",
            dict(name=u'FooProp',
                 value='https://10.1.2.3:5989/root/cimv2:C1.k1="v1",k2=2',
                 type='reference'),
            dict(name=u'FooProp',
                 value=CIMInstanceName(
                     'C1', keybindings=dict(k1='v1', k2=2),
                     namespace='root/cimv2', host='10.1.2.3:5989'),
                 type=u'reference'),
            None, CHECK_0_12_0
        ),

        # Initialization to CIM embedded object (instance or class)
        (
            "Verify that type string for value None is implied from "
            "embedded_object (since 0.8.1 and before 0.12)",
            dict(name=u'FooProp', value=None,
                 embedded_object='object'),
            dict(name=u'FooProp', value=None, type=exp_type_string,
                 embedded_object=u'object'),
            None, not CHECK_0_12_0
        ),
        (
            "Verify that value None is permitted with embedded_object",
            dict(name=u'FooProp', value=None, type='string',
                 embedded_object='object'),
            dict(name=u'FooProp', value=None, type=u'string',
                 embedded_object=u'object'),
            None, True
        ),
        (
            "Verify that value CIMClass implies type and embedded_object",
            dict(name=u'FooProp', value=emb_class_1),
            dict(name=u'FooProp', value=emb_class_1, type=exp_type_string,
                 embedded_object=exp_eo_object),
            None, True
        ),
        (
            "Verify that value CIMClass and type string imply embedded_object "
            "(since 0.8.1)",
            dict(name=u'FooProp', value=emb_class_1, type='string'),
            dict(name=u'FooProp', value=emb_class_1, type=u'string',
                 embedded_object=exp_eo_object),
            None, True
        ),
        (
            "Verify that value CIMClass and embedded_object imply type string",
            dict(name=u'FooProp', value=emb_class_1,
                 embedded_object='object'),
            dict(name=u'FooProp', value=emb_class_1, type=exp_type_string,
                 embedded_object=u'object'),
            None, True
        ),
        (
            "Verify normal case with value, type, embedded_object specified",
            dict(name=u'FooProp', value=emb_class_1, type='string',
                 embedded_object='object'),
            dict(name=u'FooProp', value=emb_class_1, type=u'string',
                 embedded_object=u'object'),
            None, True
        ),
        (
            "Verify that value CIMInstance and embedded_object imply type "
            "string (since 0.8.1)",
            dict(name=u'FooProp', value=emb_instance_1,
                 embedded_object='object'),
            dict(name=u'FooProp', value=emb_instance_1, type=exp_type_string,
                 embedded_object=u'object'),
            None, True
        ),
        (
            "Verify normal case with value CIMInstance, type, embedded_object "
            "specified",
            dict(name=u'FooProp', value=emb_instance_1, type='string',
                 embedded_object='object'),
            dict(name=u'FooProp', value=emb_instance_1, type=u'string',
                 embedded_object=u'object'),
            None, True
        ),

        # Initialization to CIM embedded instance
        (
            "Verify that value CIMInstance implies type and embedded_object",
            dict(name=u'FooProp', value=emb_instance_1),
            dict(name=u'FooProp', value=emb_instance_1, type=exp_type_string,
                 embedded_object=exp_eo_instance),
            None, True
        ),
        (
            "Verify that value CIMInstance and type string imply "
            "embedded_object (since 0.8.1)",
            dict(name=u'FooProp', value=emb_instance_1, type='string'),
            dict(name=u'FooProp', value=emb_instance_1, type=u'string',
                 embedded_object=exp_eo_instance),
            None, True
        ),
        (
            "Verify that value CIMInstance and embedded_object imply type "
            "string",
            dict(name=u'FooProp', value=emb_instance_1,
                 embedded_object='instance'),
            dict(name=u'FooProp', value=emb_instance_1, type=exp_type_string,
                 embedded_object=u'instance'),
            None, True
        ),
        (
            "Verify normal case with value CIMInstance, type, embedded_object "
            "specified",
            dict(name=u'FooProp', value=emb_instance_1, type='string',
                 embedded_object='instance'),
            dict(name=u'FooProp', value=emb_instance_1, type=u'string',
                 embedded_object=u'instance'),
            None, True
        ),

        # Array tests with different is_array and array_size
        (
            "Verify that is_array 42 is converted to bool (since 0.12)",
            dict(name=u'FooProp', value=[u'abc'], type=u'string',
                 is_array=42),
            dict(name=u'FooProp', value=[u'abc'], type=u'string',
                 is_array=True),
            None, CHECK_0_12_0
        ),
        (
            "Verify that is_array 'false' is converted to bool using Python "
            "bool rules(since 0.12)",
            dict(name=u'FooProp', value=[u'abc'], type=u'string',
                 is_array='false'),
            dict(name=u'FooProp', value=[u'abc'], type=u'string',
                 is_array=True),
            None, CHECK_0_12_0
        ),
        (
            "Verify that unspecified is_array is implied to scalar with "
            "None value and type string",
            dict(name=u'FooProp', value=None, type=u'string'),
            dict(name=u'FooProp', value=None, type=u'string',
                 is_array=False),
            None, True
        ),
        (
            "Verify that unspecified is_array is implied to scalar with "
            "scalar string value but without type",
            dict(name=u'FooProp', value=u'abc', type=u'string'),
            dict(name=u'FooProp', value=u'abc', type=u'string',
                 is_array=False),
            None, True
        ),
        (
            "Verify that unspecified is_array is implied to array with "
            "array value",
            dict(name=u'FooProp', value=[u'abc'], type=u'string'),
            dict(name=u'FooProp', value=[u'abc'], type=u'string',
                 is_array=True),
            None, True
        ),
        (
            "Verify that array_size 2 remains int",
            dict(name=u'FooProp', value=[u'abc'], type=u'string',
                 is_array=True, array_size=2),
            dict(name=u'FooProp', value=[u'abc'], type=u'string',
                 is_array=True, array_size=2),
            None, True
        ),

        # Initialization to arrays of CIM string and numeric types
        (
            "Verify that value None is permitted for string array",
            dict(name=u'FooProp', value=None, type=u'string', is_array=True),
            dict(name=u'FooProp', value=None, type=u'string', is_array=True),
            None, True
        ),
        (
            "Verify that value empty list is permitted for string array",
            dict(name=u'FooProp', value=[], type=u'string', is_array=True),
            dict(name=u'FooProp', value=[], type=u'string', is_array=True),
            None, True
        ),
        (
            "Verify that is_array is implied from value empty list",
            dict(name=u'FooProp', value=[], type=u'string'),
            dict(name=u'FooProp', value=[], type=u'string', is_array=True),
            None, True
        ),
        (
            "Verify that value list(None) is permitted for string array",
            dict(name=u'FooProp', value=[None], type=u'string', is_array=True),
            dict(name=u'FooProp', value=[None], type=u'string', is_array=True),
            None, True
        ),
        (
            "Verify that is_array is implied from value list(None)",
            dict(name=u'FooProp', value=[None], type=u'string'),
            dict(name=u'FooProp', value=[None], type=u'string', is_array=True),
            None, True
        ),
        (
            "Verify that type string is implied from value list(string)",
            dict(name=u'FooProp', value=[u'abc'],
                 is_array=True),
            dict(name=u'FooProp', value=[u'abc'], type=exp_type_string,
                 is_array=True),
            None, True
        ),
        (
            "Verify that is_array is implied from type string and value "
            "list(string)",
            dict(name=u'FooProp', value=[u'abc'], type=u'string'),
            dict(name=u'FooProp', value=[u'abc'], type=u'string',
                 is_array=True),
            None, True
        ),
        (
            "Verify that type string and is_array are implied from value "
            "list(string)",
            dict(name=u'FooProp', value=[u'abc']),
            dict(name=u'FooProp', value=[u'abc'], type=exp_type_string,
                 is_array=True),
            None, True
        ),
        (
            "Verify that type uint8 is implied from value list(uint8)",
            dict(name=u'FooProp', value=[Uint8(42)],
                 is_array=True),
            dict(name=u'FooProp', value=[Uint8(42)], type=exp_type_uint8,
                 is_array=True),
            None, True
        ),
        (
            "Verify that is_array is implied from type uint8 and value "
            "list(uint8)",
            dict(name=u'FooProp', value=[Uint8(42)], type=u'uint8'),
            dict(name=u'FooProp', value=[Uint8(42)], type=u'uint8',
                 is_array=True),
            None, True
        ),
        (
            "Verify that type uint8 and is_array are implied from value "
            "list(uint8)",
            dict(name=u'FooProp', value=[Uint8(42)]),
            dict(name=u'FooProp', value=[Uint8(42)], type=exp_type_uint8,
                 is_array=True),
            None, True
        ),

        # Initialization to arrays of CIM boolean type
        (
            "Verify that is_array is implied from value empty list",
            dict(name=u'FooProp', value=[], type=u'boolean'),
            dict(name=u'FooProp', value=[], type=u'boolean', is_array=True),
            None, True
        ),
        (
            "Verify that is_array is implied from value list(None)",
            dict(name=u'FooProp', value=[None], type=u'boolean'),
            dict(name=u'FooProp', value=[None], type=u'boolean', is_array=True),
            None, True
        ),
        (
            "Verify that type boolean and is_array are implied from value "
            "list(boolean)",
            dict(name=u'FooProp', value=[True]),
            dict(name=u'FooProp', value=[True], type=exp_type_boolean,
                 is_array=True),
            None, True
        ),
        (
            "Verify that is_array is implied from type boolean and value "
            "list(boolean)",
            dict(name=u'FooProp', value=[False], type=u'boolean'),
            dict(name=u'FooProp', value=[False], type=u'boolean',
                 is_array=True),
            None, True
        ),
        (
            "Verify that type boolean and is_array are implied from value "
            "list(boolean)",
            dict(name=u'FooProp', value=[True]),
            dict(name=u'FooProp', value=[True], type=exp_type_boolean,
                 is_array=True),
            None, True
        ),

        # Initialization to arrays of CIM datetime type
        (
            "Verify that type datetime and is_array are implied from value "
            "list(timedelta) (since 0.8.1)",
            dict(name=u'FooProp', value=[timedelta_1]),
            dict(name=u'FooProp', value=[CIMDateTime(cim_timedelta_1)],
                 type=exp_type_datetime, is_array=True),
            None, True
        ),
        (
            "Verify that is_array is implied from type datetime and value "
            "list(timedelta) (since 0.8.1)",
            dict(name=u'FooProp', value=[timedelta_1],
                 type='datetime'),
            dict(name=u'FooProp', value=[CIMDateTime(cim_timedelta_1)],
                 type=u'datetime', is_array=True),
            None, True
        ),
        (
            "Verify that type datetime and is_array are implied from value "
            "list(CIMDateTime)",
            dict(name=u'FooProp', value=[CIMDateTime(cim_timedelta_1)]),
            dict(name=u'FooProp', value=[CIMDateTime(cim_timedelta_1)],
                 type=exp_type_datetime, is_array=True),
            None, True
        ),
        (
            "Verify that is_array is implied from type datetime and value "
            "list(CIMDateTime)",
            dict(name=u'FooProp', value=[CIMDateTime(cim_timedelta_1)],
                 type='datetime'),
            dict(name=u'FooProp', value=[CIMDateTime(cim_timedelta_1)],
                 type=u'datetime', is_array=True),
            None, True
        ),
        (
            "Verify that type datetime and is_array are implied from value "
            "list(datetime) (since 0.8.1)",
            dict(name=u'FooProp', value=[datetime_2]),
            dict(name=u'FooProp', value=[CIMDateTime(cim_datetime_2)],
                 type=exp_type_datetime, is_array=True),
            None, True
        ),
        (
            "Verify that is_array is implied from type datetime and value "
            "list(datetime) (since 0.8.1)",
            dict(name=u'FooProp', value=[datetime_2],
                 type='datetime'),
            dict(name=u'FooProp', value=[CIMDateTime(cim_datetime_2)],
                 type=u'datetime', is_array=True),
            None, True
        ),
        (
            "Verify that type datetime and is_array are implied from value "
            "list(CIMDateTime)",
            dict(name=u'FooProp', value=[CIMDateTime(cim_datetime_2)]),
            dict(name=u'FooProp', value=[CIMDateTime(cim_datetime_2)],
                 type=exp_type_datetime, is_array=True),
            None, True
        ),
        (
            "Verify that is_array is implied from type datetime and value "
            "list(CIMDateTime)",
            dict(name=u'FooProp', value=[CIMDateTime(cim_datetime_2)],
                 type='datetime'),
            dict(name=u'FooProp', value=[CIMDateTime(cim_datetime_2)],
                 type=u'datetime', is_array=True),
            None, True
        ),
        (
            "Verify that is_array is implied from type datetime and value "
            "list(None)",
            dict(name=u'FooProp', value=[None],
                 type='datetime'),
            dict(name=u'FooProp', value=[None],
                 type=u'datetime', is_array=True),
            None, True
        ),

        # Initialization to arrays of CIM embedded objects (class and inst)
        (
            "Verify that is_array and type string are implied from "
            "embedded_object, for value list(None) (since 0.8.1 and "
            "before 0.12)",
            dict(name=u'FooProp', value=[None],
                 embedded_object=u'object'),
            dict(name=u'FooProp', value=[None], type=exp_type_string,
                 embedded_object=u'object', is_array=True),
            None, not CHECK_0_12_0
        ),
        (
            "Verify that is_array and type string are implied from "
            "embedded_object, for value list() (since 0.8.1 and "
            "before 0.12)",
            dict(name=u'FooProp', value=[],
                 embedded_object=u'object'),
            dict(name=u'FooProp', value=[], type=exp_type_string,
                 embedded_object=u'object', is_array=True),
            None, not CHECK_0_12_0
        ),
        (
            "Verify that is_array is implied from type string, "
            "embedded_object, for value list(None)",
            dict(name=u'FooProp', value=[None], type='string',
                 embedded_object=u'object'),
            dict(name=u'FooProp', value=[None], type=u'string',
                 embedded_object=u'object', is_array=True),
            None, True
        ),
        (
            "Verify that is_array is implied from type string, "
            "embedded_object, for value list()",
            dict(name=u'FooProp', value=[], type='string',
                 embedded_object=u'object'),
            dict(name=u'FooProp', value=[], type=u'string',
                 embedded_object=u'object', is_array=True),
            None, True
        ),
        (
            "Verify that is_array, type and embedded_object are implied "
            "from value list(CIMClass)",
            dict(name=u'FooProp', value=[emb_class_1]),
            dict(name=u'FooProp', value=[emb_class_1], type=exp_type_string,
                 embedded_object=exp_eo_object, is_array=True),
            None, True
        ),
        (
            "Verify that is_array and embedded_object are implied from type "
            "and value list(CIMClass) (since 0.8.1)",
            dict(name=u'FooProp', value=[emb_class_1], type='string'),
            dict(name=u'FooProp', value=[emb_class_1], type=u'string',
                 embedded_object=exp_eo_object, is_array=True),
            None, True
        ),
        (
            "Verify that is_array and type are implied from embedded_object "
            "and value list(CIMClass)",
            dict(name=u'FooProp', value=[emb_class_1],
                 embedded_object='object'),
            dict(name=u'FooProp', value=[emb_class_1], type=exp_type_string,
                 embedded_object=u'object', is_array=True),
            None, True
        ),
        (
            "Verify that is_array is implied from type, embedded_object "
            "and value list(CIMClass)",
            dict(name=u'FooProp', value=[emb_class_1], type='string',
                 embedded_object='object'),
            dict(name=u'FooProp', value=[emb_class_1], type=u'string',
                 embedded_object=u'object', is_array=True),
            None, True
        ),
        (
            "Verify that is_array and type are implied from embedded_object "
            "and value list(CIMInstance)",
            dict(name=u'FooProp', value=[emb_instance_1],
                 embedded_object='object'),
            dict(name=u'FooProp', value=[emb_instance_1], type=exp_type_string,
                 embedded_object=u'object', is_array=True),
            None, True
        ),
        (
            "Verify that is_array is implied from type, embedded_object "
            "and value list(CIMInstance)",
            dict(name=u'FooProp', value=[emb_instance_1], type='string',
                 embedded_object='object'),
            dict(name=u'FooProp', value=[emb_instance_1], type=u'string',
                 embedded_object=u'object', is_array=True),
            None, True
        ),

        # Initialization to arrays of CIM embedded instances
        (
            "Verify that is_array, type and embedded_object are implied from "
            "value list(CIMInstance)",
            dict(name=u'FooProp', value=[emb_instance_1]),
            dict(name=u'FooProp', value=[emb_instance_1], type=exp_type_string,
                 embedded_object=exp_eo_instance, is_array=True),
            None, True
        ),
        (
            "Verify that is_array and type are implied from embedded_object "
            "and value list(CIMInstance)",
            dict(name=u'FooProp', value=[emb_instance_1],
                 embedded_object='instance'),
            dict(name=u'FooProp', value=[emb_instance_1], type=exp_type_string,
                 embedded_object=u'instance', is_array=True),
            None, True
        ),
        (
            "Verify that is_array and embedded_object are implied from type "
            "and value list(CIMInstance) (since 0.8.1)",
            dict(name=u'FooProp', value=[emb_instance_1], type='string'),
            dict(name=u'FooProp', value=[emb_instance_1], type=u'string',
                 embedded_object=exp_eo_instance, is_array=True),
            None, True
        ),
        (
            "Verify that is_array is implied from type, embedded_object "
            "and value list(CIMInstance)",
            dict(name=u'FooProp', value=[emb_instance_1], type='string',
                 embedded_object='instance'),
            dict(name=u'FooProp', value=[emb_instance_1], type=u'string',
                 embedded_object=u'instance', is_array=True),
            None, True
        ),

        # Check that the documented examples don't fail
        (
            "Verify documented example 1",
            dict(name='MyNum', value=42, type='uint8'),
            dict(name=u'MyNum', value=Uint8(42),
                 type=u'uint8'),
            None, True
        ),
        (
            "Verify documented example 2",
            dict(name='MyNum', value=Uint8(42)),
            dict(name=u'MyNum', value=Uint8(42), type=exp_type_uint8),
            None, True
        ),
        (
            "Verify documented example 3",
            dict(name='MyNumArray', value=[1, 2, 3], type='uint8'),
            dict(name=u'MyNumArray', value=[Uint8(1), Uint8(2), Uint8(3)],
                 type=u'uint8', is_array=True),
            None, True
        ),
        (
            "Verify documented example 4",
            dict(name='MyRef', value=inst_path_1),
            dict(name=u'MyRef', value=inst_path_1, type=exp_type_reference),
            None, True
        ),
        (
            "Verify documented example 5",
            dict(name='MyEmbObj', value=emb_class_1),
            dict(name=u'MyEmbObj', value=emb_class_1, type=exp_type_string,
                 embedded_object=exp_eo_object),
            None, True
        ),
        (
            "Verify documented example 6",
            dict(name='MyEmbObj', value=emb_instance_1,
                 embedded_object='object'),
            dict(name=u'MyEmbObj', value=emb_instance_1, type=exp_type_string,
                 embedded_object=u'object'),
            None, True
        ),
        (
            "Verify documented example 7",
            dict(name='MyEmbInst', value=emb_instance_1),
            dict(name=u'MyEmbInst', value=emb_instance_1, type=exp_type_string,
                 embedded_object=exp_eo_instance),
            None, True
        ),
        (
            "Verify documented example 8",
            dict(name='MyString', value=None, type='string'),
            dict(name=u'MyString', value=None, type=u'string'),
            None, True
        ),
        (
            "Verify documented example 9",
            dict(name='MyNum', value=None, type='uint8'),
            dict(name=u'MyNum', value=None, type=u'uint8'),
            None, True
        ),
        (
            "Verify documented example 10",
            dict(name='MyRef', value=None, type='reference',
                 reference_class='MyClass'),
            dict(name=u'MyRef', value=None, type=u'reference',
                 reference_class=u'MyClass'),
            None, True
        ),
        (
            "Verify documented example 11",
            dict(name='MyEmbObj', value=None, type='string',
                 embedded_object='object'),
            dict(name=u'MyEmbObj', value=None, type=u'string',
                 embedded_object=u'object'),
            None, True
        ),
        (
            "Verify documented example 12",
            dict(name='MyEmbInst', value=None, type='string',
                 embedded_object='instance'),
            dict(name=u'MyEmbInst', value=None, type=u'string',
                 embedded_object=u'instance'),
            None, True
        ),

        # Qualifiers
        (
            "Verify that qualifiers dict is converted to NocaseDict",
            dict(name=u'FooProp', value=u'abc', type=u'string',
                 qualifiers=dict(Q1=qualifier_Q1)),
            dict(name=u'FooProp', value=u'abc', type=u'string',
                 qualifiers=NocaseDict(Q1=qualifier_Q1)),
            None, True
        ),
        (
            "Verify that qualifiers as NocaseDict is permitted",
            dict(name=u'FooProp', value=u'abc', type=u'string',
                 qualifiers=NocaseDict(Q1=qualifier_Q1)),
            dict(name=u'FooProp', value=u'abc', type=u'string',
                 qualifiers=NocaseDict(Q1=qualifier_Q1)),
            None, True
        ),
    ]

    @pytest.mark.parametrize(
        "desc, kwargs, exp_attrs, exp_warn_type, condition",
        testcases_succeeds)
    def test_CIMProperty_init_succeeds(
            self, desc, kwargs, exp_attrs, exp_warn_type, condition):
        # pylint: disable=unused-argument
        """All test cases where CIMProperty.__init__() succeeds."""

        if not condition:
            pytest.skip("Condition for test case not met")

        exp_name = exp_attrs['name']
        exp_value = exp_attrs['value']
        exp_type = exp_attrs['type']
        exp_class_origin = exp_attrs.get(
            'class_origin', self.default_exp_attrs['class_origin'])
        exp_array_size = exp_attrs.get(
            'array_size', self.default_exp_attrs['array_size'])
        exp_propagated = exp_attrs.get(
            'propagated', self.default_exp_attrs['propagated'])
        exp_is_array = exp_attrs.get(
            'is_array', self.default_exp_attrs['is_array'])
        exp_reference_class = exp_attrs.get(
            'reference_class', self.default_exp_attrs['reference_class'])
        exp_qualifiers = exp_attrs.get(
            'qualifiers', self.default_exp_attrs['qualifiers'])
        exp_embedded_object = exp_attrs.get(
            'embedded_object', self.default_exp_attrs['embedded_object'])

        if exp_warn_type is None:

            # The code to be tested
            obj = CIMProperty(**kwargs)

        else:
            with pytest.warns(exp_warn_type):

                # The code to be tested
                obj = CIMProperty(**kwargs)

        assert obj.name == exp_name
        assert isinstance(obj.name, type(exp_name))

        assert obj.value == exp_value
        assert isinstance(obj.value, type(exp_value))

        assert obj.type == exp_type
        assert isinstance(obj.type, type(exp_type))

        assert obj.class_origin == exp_class_origin
        assert isinstance(obj.class_origin, type(exp_class_origin))

        assert obj.array_size == exp_array_size
        assert isinstance(obj.array_size, type(exp_array_size))

        assert obj.propagated == exp_propagated
        assert isinstance(obj.propagated, type(exp_propagated))

        assert obj.is_array == exp_is_array
        assert isinstance(obj.is_array, type(exp_is_array))

        assert obj.reference_class == exp_reference_class
        assert isinstance(obj.reference_class, type(exp_reference_class))

        assert obj.qualifiers == exp_qualifiers
        assert isinstance(obj.qualifiers, type(exp_qualifiers))

        assert obj.embedded_object == exp_embedded_object
        assert isinstance(obj.embedded_object, type(exp_embedded_object))

    testcases_fails = [
        # Testcases where CIMProperty.__init__() fails.
        # Each testcase has these items:
        # * desc: Short testcase description.
        # * kwargs: Dict of keyword arguments for __init__().
        # * exp_exc_type: Expected exception type.
        # * condition: Condition for testcase to run.
        (
            "Verify that name None fails (since 0.8.1)",
            dict(name=None, value='abc'),
            ValueError, True
        ),
        (
            "Verify that value None without type fails",
            dict(name='FooProp', value=None),
            ValueError, True
        ),
        (
            "Verify that qualifier with inconsistent key / name fails "
            "(since 0.12)",
            dict(name='FooProp', value='abc',
                 qualifiers=dict(Q1_x=qualifier_Q1)),
            ValueError, CHECK_0_12_0
        ),
        (
            "Verify that type string for value None is not implied from "
            "embedded_object (before 0.8.1 and since 0.12)",
            dict(name='FooProp', value=None, embedded_object='object'),
            ValueError, CHECK_0_12_0
        ),
        (
            "Verify that invalid embedded_object value fails",
            dict(name='FooProp', value=None, type='string',
                 embedded_object='objectx'),
            ValueError, True
        ),
        (
            "Verify that invalid type for embedded_object fails",
            dict(name='FooProp', value=None, type='reference',
                 embedded_object='object'),
            ValueError, True
        ),
        (
            "Verify that invalid value for embedded_object fails",
            dict(name='FooProp', value=CIMProperty('Boo', ''),
                 type='string', embedded_object='object'),
            ValueError, True
        ),
        (
            "Verify that invalid array value for embedded_object fails",
            dict(name='FooProp', value=[CIMProperty('Boo', '')],
                 type='string', embedded_object='object'),
            ValueError, True
        ),
        (
            "Verify that a value of int without a type fails",
            dict(name='FooProp', value=42),
            ValueError if CHECK_0_12_0 else TypeError, True
        ),
        (
            "Verify that a value of float without a type fails",
            dict(name='FooProp', value=42.1),
            ValueError if CHECK_0_12_0 else TypeError, True
        ),
        (
            "Verify that a value of long without a type fails (Python 2 only)",
            dict(name='FooProp', value=_Longint(42)),
            ValueError if CHECK_0_12_0 else TypeError, six.PY2
        ),
        (
            "Verify that arrays of reference properties are not allowed in "
            "CIM v2",
            dict(name='FooProp', value=[None], type='reference',
                 reference_class='CIM_Foo'),
            ValueError, True
        ),
        (
            "Verify that is_array and type string are not implied from "
            "embedded_object, for value list(None) (before 0.8.1 and "
            "since 0.12)",
            dict(name=u'FooProp', value=[None], embedded_object=u'object'),
            ValueError, CHECK_0_12_0
        ),
        (
            "Verify that is_array and type string are not implied from "
            "embedded_object, for value list() (before 0.8.1 and "
            "since 0.12)",
            dict(name=u'FooProp', value=[], embedded_object=u'object'),
            ValueError, CHECK_0_12_0
        ),
        (
            "Verify that value None witout type fails also for arrays",
            dict(name=u'FooProp', value=None, is_array=True),
            ValueError, True
        ),
        (
            "Verify that value list() without type fails also for arrays",
            dict(name=u'FooProp', value=[], is_array=True),
            ValueError, True
        ),
        (
            "Verify that value list(None) without type fails also for arrays",
            dict(name=u'FooProp', value=[None], is_array=True),
            ValueError, True
        ),
        (
            "Verify that value list(None,str) without type fails also for "
            "arrays",
            dict(name=u'FooProp', value=[None, 'abc'], is_array=True),
            ValueError, True
        ),
        (
            "Verify that value list() without type fails also when "
            "is_array is unspecified",
            dict(name=u'FooProp', value=[]),
            ValueError, True
        ),
        (
            "Verify that value list(None) without type fails also when "
            "is_array is unspecified",
            dict(name=u'FooProp', value=[None]),
            ValueError, True
        ),
        (
            "Verify that value list(None,str) without type fails also when "
            "is_array is unspecified",
            dict(name=u'FooProp', value=[None, 'abc']),
            ValueError, True
        ),
        (
            "Verify that value list(int) without type fails",
            dict(name=u'FooProp', value=[1]),
            ValueError if CHECK_0_12_0 else TypeError, True
        ),
        (
            "Verify that value list(float) without type fails",
            dict(name=u'FooProp', value=[1.1]),
            ValueError if CHECK_0_12_0 else TypeError, True
        ),
        (
            "Verify that value list(long) without type fails (Python 2 only)",
            dict(name=u'FooProp', value=[_Longint(1)]),
            ValueError if CHECK_0_12_0 else TypeError, True
        ),
    ]

    @pytest.mark.parametrize(
        "desc, kwargs, exp_exc_type, condition",
        testcases_fails)
    def test_CIMProperty_init_fails(
            self, desc, kwargs, exp_exc_type, condition):
        # pylint: disable=unused-argument
        """All test cases where CIMProperty.__init__() fails."""

        if not condition:
            pytest.skip("Condition for test case not met")

        with pytest.raises(exp_exc_type):

            # The code to be tested
            CIMProperty(**kwargs)


class CIMPropertyCopy(unittest.TestCase, CIMObjectMixin):

    def test_all(self):

        p = CIMProperty('Spotty', 'Foot')
        c = p.copy()

        self.assertEqual(p, c)

        c.name = '1234'
        c.value = '1234'
        c.qualifiers = {'Key': CIMQualifier('Key', True)}

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
    Test CIMProperty.__str__().

    That function returns for example::

       CIMProperty(name=Prop, value=..., type=..., reference_class=...
       embedded_object=..., is_array=...)
    """

    emb_classname = 'CIM_Bar'
    emb_instance = CIMInstance(emb_classname)
    emb_class = CIMClass(emb_classname)

    testcases_succeeds = [
        # Testcases where CIMProperty.__str__() succeeds.
        # Each testcase has these items:
        # * obj: CIMProperty object to be tested.
        (
            CIMProperty(
                name='Spotty',
                value='Foot')
        ),
        (
            CIMProperty(
                name='Spotty',
                value='Foot',
                type='string')
        ),
        (
            CIMProperty(
                name='Spotty',
                value=None,
                type='reference',
                reference_class='CIM_Foo')
        ),
        (
            CIMProperty(
                name='Spotty',
                value=emb_instance,
                type='string',
                embedded_object='instance')
        ),
        (
            CIMProperty(
                name='Spotty',
                value=emb_instance,
                type='string',
                embedded_object='object')
        ),
        (
            CIMProperty(
                name='Spotty',
                value=emb_class,
                type='string',
                embedded_object='object')
        ),
        (
            CIMProperty(
                name='Spotty',
                value=['Foot'],
                is_array=True)
        ),
    ]

    @pytest.mark.parametrize(
        "obj",
        testcases_succeeds)
    def test_CIMProperty_str_succeeds(self, obj):
        """All test cases where CIMProperty.__str__() succeeds."""

        s = str(obj)

        assert re.match(r'^CIMProperty\(', s)

        exp_name = 'name=%r' % obj.name
        assert exp_name in s

        exp_value = 'value=%r' % obj.value
        assert exp_value in s

        exp_type = 'type=%r' % obj.type
        assert exp_type in s

        exp_reference_class = 'reference_class=%r' % obj.reference_class
        assert exp_reference_class in s

        exp_embedded_object = 'embedded_object=%r' % obj.embedded_object
        assert exp_embedded_object in s

        exp_is_array = 'is_array=%r' % obj.is_array
        assert exp_is_array in s


class Test_CIMProperty_repr(object):
    """
    Test CIMProperty.__repr__().
    """

    emb_classname = 'CIM_Bar'
    emb_instance = CIMInstance(emb_classname)
    emb_class = CIMClass(emb_classname)

    testcases_succeeds = [
        # Testcases where CIMProperty.__repr__() succeeds.
        # Each testcase has these items:
        # * obj: CIMProperty object to be tested.
        (
            CIMProperty(
                name='Spotty',
                value='Foot')
        ),
        (
            CIMProperty(
                name='Spotty',
                value='Foot',
                type='string')
        ),
        (
            CIMProperty(
                name='Spotty',
                value=None,
                type='reference',
                reference_class='CIM_Foo')
        ),
        (
            CIMProperty(
                name='Spotty',
                value=emb_instance,
                type='string',
                embedded_object='instance')
        ),
        (
            CIMProperty(
                name='Spotty',
                value=emb_instance,
                type='string',
                embedded_object='object')
        ),
        (
            CIMProperty(
                name='Spotty',
                value=emb_class,
                type='string',
                embedded_object='object')
        ),
        (
            CIMProperty(
                name='Spotty',
                value=['Foot'],
                is_array=True)
        ),
    ]

    @pytest.mark.parametrize(
        "obj",
        testcases_succeeds)
    def test_CIMProperty_repr_succeeds(self, obj):
        """All test cases where CIMProperty.__repr__() succeeds."""

        r = repr(obj)

        assert re.match(r'^CIMProperty\(', r)

        exp_name = 'name=%r' % obj.name
        assert exp_name in r

        exp_value = 'value=%r' % obj.value
        assert exp_value in r

        exp_type = 'type=%r' % obj.type
        assert exp_type in r

        exp_reference_class = 'reference_class=%r' % obj.reference_class
        assert exp_reference_class in r

        exp_embedded_object = 'embedded_object=%r' % obj.embedded_object
        assert exp_embedded_object in r

        exp_is_array = 'is_array=%r' % obj.is_array
        assert exp_is_array in r

        exp_array_size = 'array_size=%r' % obj.array_size
        assert exp_array_size in r

        exp_class_origin = 'class_origin=%r' % obj.class_origin
        assert exp_class_origin in r

        exp_propagated = 'propagated=%r' % obj.propagated
        assert exp_propagated in r

        exp_qualifiers = 'qualifiers=%r' % obj.qualifiers
        assert exp_qualifiers in r


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


class Test_CIMQualifier_init(object):
    """
    Test CIMQualifier.__init__().
    """

    def test_CIMQualifier_init_pos_args(self):
        # pylint: disable=unused-argument
        """Test position of arguments in CIMQualifier.__init__()."""

        # The code to be tested
        obj = CIMQualifier(
            'FooQual',
            'abc',
            'string',
            False,
            True,
            True,
            False,
            True)

        assert obj.name == u'FooQual'
        assert obj.value == u'abc'
        assert obj.type == u'string'
        assert obj.propagated is False
        assert obj.overridable is True
        assert obj.tosubclass is True
        assert obj.toinstance is False
        assert obj.translatable is True

    # Defaults to expect for attributes when not specified in testcase
    default_exp_attrs = dict(
        type=None,
        propagated=None,
        overridable=None,
        tosubclass=None,
        toinstance=None,
        translatable=None
    )

    testcases_succeeds = [
        # Testcases where CIMQualifier.__init__() succeeds.
        # Each testcase has these items:
        # * desc: Short testcase description.
        # * kwargs: Dict of keyword arguments for __init__().
        # * exp_attrs: Dict of expected attributes of resulting object.
        # * exp_warn_type: Expected warning type.
        # * condition: Condition for testcase to run.
        (
            "Verify that name can be None although documented otherwise "
            "(before 0.12)",
            dict(name=None, value=u'abc'),
            dict(name=None, value=u'abc', type=exp_type_string),
            None, not CHECK_0_12_0
        ),
        (
            "Verify that binary name is converted to unicode",
            dict(name=b'FooParam', value=u'abc'),
            dict(name=u'FooParam', value=u'abc', type=exp_type_string),
            None, True
        ),
        (
            "Verify that unicode name remains unicode",
            dict(name=u'FooParam', value=u'abc'),
            dict(name=u'FooParam', value=u'abc', type=exp_type_string),
            None, True
        ),
        (
            "Verify that binary value is converted to unicode and "
            "type is implied to string",
            dict(name=u'FooParam', value=b'abc'),
            dict(name=u'FooParam', value=u'abc' if CHECK_0_12_0 else b'abc',
                 type=exp_type_string),
            None, True
        ),
        (
            "Verify that unicode value remains unicode and "
            "type is implied to string",
            dict(name=u'FooParam', value=u'abc'),
            dict(name=u'FooParam', value=u'abc', type=exp_type_string),
            None, True
        ),
        (
            "Verify uint8 value without type",
            dict(name=u'FooParam', value=Uint8(42)),
            dict(name=u'FooParam', value=Uint8(42), type=exp_type_uint8),
            None, True
        ),
        (
            "Verify uint8 value with type",
            dict(name=u'FooParam', value=Uint8(42), type='uint8'),
            dict(name=u'FooParam', value=Uint8(42), type=u'uint8'),
            None, True
        ),
        (
            "Verify that boolean value True remains boolean and "
            "type is implied to boolean",
            dict(name=u'FooParam', value=True),
            dict(name=u'FooParam', value=True, type=exp_type_boolean),
            None, True
        ),
        (
            "Verify that boolean value False remains boolean and "
            "type is implied to boolean",
            dict(name=u'FooParam', value=False),
            dict(name=u'FooParam', value=False, type=exp_type_boolean),
            None, True
        ),
        (
            "Verify that binary array value is converted to unicode and "
            "type is implied to string",
            dict(name=u'FooParam', value=[b'abc']),
            dict(name=u'FooParam', value=[u'abc' if CHECK_0_12_0 else b'abc'],
                 type=exp_type_string),
            None, True
        ),
        (
            "Verify that unicode array value remains unicode and "
            "type is implied to string",
            dict(name=u'FooParam', value=[u'abc']),
            dict(name=u'FooParam', value=[u'abc'], type=exp_type_string),
            None, True
        ),
        (
            "Verify that boolean array value [False] remains boolean and "
            "type is implied to boolean",
            dict(name=u'FooParam', value=[False]),
            dict(name=u'FooParam', value=[False], type=exp_type_boolean),
            None, True
        ),
        (
            "Verify that boolean array value [True] remains boolean and "
            "type is implied to boolean",
            dict(name=u'FooParam', value=[True]),
            dict(name=u'FooParam', value=[True], type=exp_type_boolean),
            None, True
        ),
        (
            "Verify that setting boolean properties to 42 results in True "
            "(since 0.12)",
            dict(name=u'FooParam', value=u'abc',
                 propagated=42, overridable=42, tosubclass=42,
                 toinstance=42, translatable=42),
            dict(name=u'FooParam', value=u'abc', type=exp_type_string,
                 propagated=True, overridable=True, tosubclass=True,
                 toinstance=True, translatable=True),
            None, CHECK_0_12_0
        ),
        (
            "Verify that setting boolean properties to 'false' results in True "
            "(using Python bool rules, since 0.12)",
            dict(name=u'FooParam', value=u'abc',
                 propagated='false', overridable='false', tosubclass='false',
                 toinstance='false', translatable='false'),
            dict(name=u'FooParam', value=u'abc', type=exp_type_string,
                 propagated=True, overridable=True, tosubclass=True,
                 toinstance=True, translatable=True),
            None, CHECK_0_12_0
        ),
        (
            "Verify that setting boolean properties to 0 results in False "
            "(since 0.12)",
            dict(name=u'FooParam', value=u'abc',
                 propagated=0, overridable=0, tosubclass=0,
                 toinstance=0, translatable=0),
            dict(name=u'FooParam', value=u'abc', type=exp_type_string,
                 propagated=False, overridable=False, tosubclass=False,
                 toinstance=False, translatable=False),
            None, CHECK_0_12_0
        ),
        (
            "Verify documented example 1",
            dict(name='MyString', value=u'abc'),
            dict(name=u'MyString', value=u'abc', type=exp_type_string),
            None, True
        ),
        (
            "Verify documented example 2 (since 0.12)",
            dict(name='MyNum', value=42, type='uint8'),
            dict(name=u'MyNum', value=Uint8(42), type=exp_type_uint8),
            None, CHECK_0_12_0
        ),
        (
            "Verify documented example 3",
            dict(name='MyNum', value=Uint8(42)),
            dict(name=u'MyNum', value=Uint8(42), type=exp_type_uint8),
            None, True
        ),
        (
            "Verify documented example 4",
            dict(name='MyNumArray', value=[1, 2, 3], type='uint8'),
            dict(name=u'MyNumArray', value=[Uint8(1), Uint8(2), Uint8(3)],
                 type=u'uint8'),
            None, True
        ),
        (
            "Verify documented example 5",
            dict(name='MyString', value=None, type='string'),
            dict(name=u'MyString', value=None, type=u'string'),
            None, True
        ),
        (
            "Verify documented example 6",
            dict(name='MyNum', value=None, type='uint8'),
            dict(name=u'MyNum', value=None, type=u'uint8'),
            None, True
        ),
    ]

    @pytest.mark.parametrize(
        "desc, kwargs, exp_attrs, exp_warn_type, condition",
        testcases_succeeds)
    def test_CIMQualifier_init_succeeds(
            self, desc, kwargs, exp_attrs, exp_warn_type, condition):
        # pylint: disable=unused-argument
        """All test cases where CIMQualifier.__init__() succeeds."""

        # import pdb; pdb.set_trace()

        if not condition:
            pytest.skip("Condition for test case not met")

        exp_name = exp_attrs['name']
        exp_value = exp_attrs['value']
        exp_type = exp_attrs.get(
            'type', self.default_exp_attrs['type'])
        exp_propagated = exp_attrs.get(
            'propagated', self.default_exp_attrs['propagated'])
        exp_overridable = exp_attrs.get(
            'overridable', self.default_exp_attrs['overridable'])
        exp_tosubclass = exp_attrs.get(
            'tosubclass', self.default_exp_attrs['tosubclass'])
        exp_toinstance = exp_attrs.get(
            'toinstance', self.default_exp_attrs['toinstance'])
        exp_translatable = exp_attrs.get(
            'translatable', self.default_exp_attrs['translatable'])

        if exp_warn_type is None:

            # The code to be tested
            obj = CIMQualifier(**kwargs)

        else:
            with pytest.warns(exp_warn_type):

                # The code to be tested
                obj = CIMQualifier(**kwargs)

        assert obj.name == exp_name
        assert isinstance(obj.name, type(exp_name))

        assert obj.value == exp_value
        assert isinstance(obj.value, type(exp_value))

        assert obj.type == exp_type
        assert isinstance(obj.type, type(exp_type))

        assert obj.propagated == exp_propagated
        assert isinstance(obj.propagated, type(exp_propagated))

        assert obj.overridable == exp_overridable
        assert isinstance(obj.overridable, type(exp_overridable))

        assert obj.tosubclass == exp_tosubclass
        assert isinstance(obj.tosubclass, type(exp_tosubclass))

        assert obj.toinstance == exp_toinstance
        assert isinstance(obj.toinstance, type(exp_toinstance))

        assert obj.translatable == exp_translatable
        assert isinstance(obj.translatable, type(exp_translatable))

    testcases_fails = [
        # Testcases where CIMQualifier.__init__() fails.
        # Each testcase has these items:
        # * desc: Short testcase description.
        # * kwargs: Dict of keyword arguments for __init__().
        # * exp_exc_type: Expected exception type.
        # * condition: Condition for testcase to run.
        (
            "Verify that name None fails (since 0.12)",
            dict(name=None, value='abc'),
            ValueError, CHECK_0_12_0
        ),
        (
            "Verify that value None without type fails",
            dict(name='FooQual', value=None),
            ValueError if CHECK_0_12_0 else TypeError, True
        ),
        (
            "Verify that value [None] without type fails",
            dict(name='FooQual', value=[None]),
            ValueError if CHECK_0_12_0 else TypeError, True
        ),
        (
            "Verify that value [] without type fails",
            dict(name='FooQual', value=[]),
            ValueError if CHECK_0_12_0 else TypeError, True
        ),
        (
            "Verify that value of int without type fails",
            dict(name='FooQual', value=42),
            ValueError if CHECK_0_12_0 else TypeError, True
        ),
        (
            "Verify that value of float without type fails",
            dict(name='FooQual', value=42.1),
            ValueError if CHECK_0_12_0 else TypeError, True
        ),
        (
            "Verify that value of long without type fails (on Python 2)",
            dict(name='FooQual', value=_Longint(42)),
            ValueError if CHECK_0_12_0 else TypeError, six.PY2
        ),
        (
            "Verify documented example 3 (before 0.12)",
            dict(name='MyNum', value=42, type='uint8'),
            TypeError, not CHECK_0_12_0
        ),
    ]

    @pytest.mark.parametrize(
        "desc, kwargs, exp_exc_type, condition",
        testcases_fails)
    def test_CIMQualifier_init_fails(
            self, desc, kwargs, exp_exc_type, condition):
        # pylint: disable=unused-argument
        """All test cases where CIMQualifier.__init__() fails."""

        if not condition:
            pytest.skip("Condition for test case not met")

        with pytest.raises(exp_exc_type):

            # The code to be tested
            CIMQualifier(**kwargs)


class CIMQualifierCopy(unittest.TestCase):

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
    Test CIMQualifier.__str__().

    That function returns for example::

       CIMQualifier(name='Foo', value=True, type='boolean', ...)
    """

    testcases_succeeds = [
        # Testcases where CIMQualifier.__str__() succeeds.
        # Each testcase has these items:
        # * obj: CIMQualifier object to be tested.
        (
            CIMQualifier('Spotty', 'Foot')
        ),
        (
            CIMQualifier('Revision', Real32(2.7))
        ),
        (
            CIMQualifier('RevisionList',
                         [Uint16(x) for x in [1, 2, 3]],
                         propagated=False)
        ),
    ]

    @pytest.mark.parametrize(
        "obj",
        testcases_succeeds)
    def test_CIMQualifier_str_succeeds(self, obj):
        """All test cases where CIMQualifier.__str__() succeeds."""

        s = str(obj)

        assert re.match(r'^CIMQualifier\(', s)

        exp_name = 'name=%r' % obj.name
        assert exp_name in s

        exp_value = 'value=%r' % obj.value
        assert exp_value in s

        exp_type = 'type=%r' % obj.type
        assert exp_type in s


class Test_CIMQualifier_repr(object):
    """
    Test CIMQualifier.__repr__().
    """

    testcases_succeeds = [
        # Testcases where CIMQualifier.__repr__() succeeds.
        # Each testcase has these items:
        # * obj: CIMQualifier object to be tested.
        (
            CIMQualifier('Spotty', 'Foot')
        ),
        (
            CIMQualifier('Revision', Real32(2.7))
        ),
        (
            CIMQualifier('RevisionList',
                         [Uint16(x) for x in [1, 2, 3]],
                         propagated=False)
        ),
    ]

    @pytest.mark.parametrize(
        "obj",
        testcases_succeeds)
    def test_CIMQualifier_repr_succeeds(self, obj):
        """All test cases where CIMQualifier.__repr__() succeeds."""

        r = repr(obj)

        assert re.match(r'^CIMQualifier\(', r)

        exp_name = 'name=%r' % obj.name
        assert exp_name in r

        exp_value = 'value=%r' % obj.value
        assert exp_value in r

        exp_type = 'type=%r' % obj.type
        assert exp_type in r

        exp_tosubclass = 'tosubclass=%r' % obj.tosubclass
        assert exp_tosubclass in r

        exp_overridable = 'overridable=%r' % obj.overridable
        assert exp_overridable in r

        exp_translatable = 'translatable=%r' % obj.translatable
        assert exp_translatable in r

        exp_toinstance = 'toinstance=%r' % obj.toinstance
        assert exp_toinstance in r

        exp_propagated = 'propagated=%r' % obj.propagated
        assert exp_propagated in r


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


class Test_CIMClassName_init(object):
    """
    Test CIMClassName.__init__().
    """

    # Defaults to expect for attributes when not specified in testcase
    default_exp_attrs = dict(
        host=None,
        namespace=None,
    )

    def test_CIMClassName_init_pos_args(self):
        # pylint: disable=unused-argument
        """Test position of arguments in CIMClassName.__init__()."""

        # The code to be tested
        obj = CIMClassName(
            'CIM_Foo',
            'woot.com',
            'cimv2')

        assert obj.classname == u'CIM_Foo'
        assert obj.host == u'woot.com'
        assert obj.namespace == u'cimv2'

    testcases_succeeds = [
        # Testcases where CIMClassName.__init__() succeeds.
        # Each testcase has these items:
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

    @pytest.mark.parametrize(
        "desc, kwargs, exp_attrs, exp_warn_type, condition",
        testcases_succeeds
    )
    def test_CIMClassName_init_succeeds(
            self, desc, kwargs, exp_attrs, exp_warn_type, condition):
        # pylint: disable=unused-argument
        """All test cases where CIMClassName.__init__() succeeds."""

        if not condition:
            pytest.skip("Condition for test case not met")

        exp_classname = exp_attrs['classname']
        exp_host = exp_attrs.get(
            'host', self.default_exp_attrs['host'])
        exp_namespace = exp_attrs.get(
            'namespace', self.default_exp_attrs['namespace'])

        if exp_warn_type is None:

            # The code to be tested
            obj = CIMClassName(**kwargs)

        else:
            with pytest.warns(exp_warn_type):

                # The code to be tested
                obj = CIMClassName(**kwargs)

        assert obj.classname == exp_classname
        assert isinstance(obj.classname, type(exp_classname))

        assert obj.host == exp_host
        assert isinstance(obj.host, type(exp_host))

        assert obj.namespace == exp_namespace
        assert isinstance(obj.namespace, type(exp_namespace))

    testcases_fails = [
        # Testcases where CIMClassName.__init__() fails.
        # Each testcase has these items:
        # * desc: Short testcase description.
        # * kwargs: Dict of keyword arguments for __init__().
        # * exp_exc_type: Expected exception type.
        # * condition: Condition for testcase to run.
        (
            "Verify that classname None fails",
            dict(classname=None),
            ValueError if CHECK_0_12_0 else TypeError,
            True
        ),
    ]

    @pytest.mark.parametrize(
        "desc, kwargs, exp_exc_type, condition",
        testcases_fails)
    def test_CIMClassName_init_fails(
            self, desc, kwargs, exp_exc_type, condition):
        # pylint: disable=unused-argument
        """All test cases where CIMClassName.__init__() fails."""

        if not condition:
            pytest.skip("Condition for test case not met")

        with pytest.raises(exp_exc_type):

            # The code to be tested
            CIMClassName(**kwargs)


class CIMClassNameCopy(unittest.TestCase):

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
    Test CIMClassName.__str__().

    That function returns the class path as a WBEM URI string.
    """

    testcases_succeeds = [
        # Testcases where CIMClassName.__str__() succeeds.
        # Each testcase has these items:
        # * obj: CIMClassName object to be tested.
        # * exp_uri: Expected WBEM URI string.
        (
            CIMClassName(
                classname='CIM_Foo'),
            'CIM_Foo'
        ),
        (
            CIMClassName(
                classname='CIM_Foo',
                namespace='cimv2'),
            'cimv2:CIM_Foo'
        ),
        (
            CIMClassName(
                classname='CIM_Foo',
                namespace='cimv2',
                host='10.11.12.13'),
            '//10.11.12.13/cimv2:CIM_Foo'
        ),
        (
            CIMClassName(
                classname='CIM_Foo',
                namespace='root/cimv2',
                host='10.11.12.13'),
            '//10.11.12.13/root/cimv2:CIM_Foo'
        ),
        (
            CIMClassName(
                classname='CIM_Foo',
                namespace='root/cimv2',
                host='10.11.12.13:5989'),
            '//10.11.12.13:5989/root/cimv2:CIM_Foo'
        ),
        (
            CIMClassName(
                classname='CIM_Foo',
                namespace='root/cimv2',
                host='jdd:test@10.11.12.13:5989'),
            '//jdd:test@10.11.12.13:5989/root/cimv2:CIM_Foo'
        ),
    ]

    @pytest.mark.parametrize(
        "obj, exp_uri",
        testcases_succeeds)
    def test_CIMClassName_str_succeeds(self, obj, exp_uri):
        """All test cases where CIMClassName.__str__() succeeds."""

        s = str(obj)

        assert s == exp_uri


class Test_CIMClassName_repr(object):
    """
    Test CIMClassName.__repr__().
    """

    testcases_succeeds = [
        # Testcases where CIMClassName.__repr__() succeeds.
        # Each testcase has these items:
        # * obj: CIMClassName object to be tested.
        (
            CIMClassName(
                classname='CIM_Foo')
        ),
        (
            CIMClassName(
                classname='CIM_Foo',
                namespace='cimv2')
        ),
        (
            CIMClassName(
                classname='CIM_Foo',
                namespace='cimv2',
                host='10.11.12.13')
        ),
        (
            CIMClassName(
                classname='CIM_Foo',
                namespace='root/cimv2',
                host='10.11.12.13')
        ),
        (
            CIMClassName(
                classname='CIM_Foo',
                namespace='root/cimv2',
                host='10.11.12.13:5989')
        ),
        (
            CIMClassName(
                classname='CIM_Foo',
                namespace='root/cimv2',
                host='jdd:test@10.11.12.13:5989')
        ),
    ]

    @pytest.mark.parametrize(
        "obj",
        testcases_succeeds)
    def test_CIMClassName_str_succeeds(self, obj):
        """All test cases where CIMClassName.__str__() succeeds."""

        r = repr(obj)

        assert re.match(r'^CIMClassName\(', r)

        exp_classname = 'classname=%r' % obj.classname
        assert exp_classname in r

        exp_namespace = 'namespace=%r' % obj.namespace
        assert exp_namespace in r

        exp_host = 'host=%r' % obj.host
        assert exp_host in r


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
    Test CIMClassName.from_wbem_uri().
    """

    testcases_succeeds = [
        # Testcases where CIMClassName.from_wbem_uri() succeeds.
        # Each testcase has these items:
        # * uri: WBEM URI string to be tested.
        # * exp_obj: Expected CIMClassName object.
        (
            'https://jdd:test@10.11.12.13:5989/root/cimv2:CIM_Foo',
            CIMClassName(
                classname='CIM_Foo',
                namespace='root/cimv2',
                host='jdd:test@10.11.12.13:5989')
        ),
        (
            'https://10.11.12.13:5989/root/cimv2:CIM_Foo',
            CIMClassName(
                classname='CIM_Foo',
                namespace='root/cimv2',
                host='10.11.12.13:5989')
        ),
        (
            'http://10.11.12.13/root/cimv2:CIM_Foo',
            CIMClassName(
                classname='CIM_Foo',
                namespace='root/cimv2',
                host='10.11.12.13')
        ),
        (
            'http://10.11.12.13/cimv2:CIM_Foo',
            CIMClassName(
                classname='CIM_Foo',
                namespace='cimv2',
                host='10.11.12.13')
        ),
    ]

    @pytest.mark.parametrize(
        "uri, exp_obj",
        testcases_succeeds)
    def test_CIMClassName_from_wbem_uri_succeeds(self, uri, exp_obj):
        """All test cases where CIMClassName.from_wbem_uri() succeeds."""

        if CHECK_0_12_0:

            obj = CIMClassName.from_wbem_uri(uri)

            assert isinstance(obj, CIMClassName)

            assert obj.classname == exp_obj.classname
            assert isinstance(obj.classname, type(exp_obj.classname))

            assert obj.namespace == exp_obj.namespace
            assert isinstance(obj.namespace, type(exp_obj.namespace))

            assert obj.host == exp_obj.host
            assert isinstance(obj.host, type(exp_obj.host))

    testcases_fails = [
        # Testcases where CIMClassName.from_wbem_uri() succeeds.
        # Each testcase has these items:
        # * desc: Short testcase description.
        # * uri: WBEM URI string to be tested.
        # * exp_exc_type: Expected exception type.

        # TODO: Improve implementation to make it fail for the disabled cases.
        (
            "missing '/' after scheme",
            'https:/10.11.12.13:5989/cimv2:CIM_Foo',
            ValueError
        ),
        # (
        #     "invalid scheme",
        #     'xyz://10.11.12.13:5989/cimv2:CIM_Foo',
        #     ValueError
        # ),
        # (
        #     "invalid ';' between host and port",
        #     'https://10.11.12.13;5989/cimv2:CIM_Foo',
        #     ValueError
        # ),
        # (
        #     "invalid ':' between port and namespace",
        #     'https://10.11.12.13:5989:cimv2:CIM_Foo',
        #     ValueError
        # ),
        # (
        #     "invalid '.' between namespace and classname",
        #     'https://10.11.12.13:5989/cimv2.CIM_Foo',
        #     ValueError
        # ),
        # (
        #     "invalid '/' between namespace and classname",
        #     'https://10.11.12.13:5989/cimv2/CIM_Foo',
        #     ValueError
        # ),
        (
            "instance path used as class path",
            'https://10.11.12.13:5989/cimv2:CIM_Foo.k1="v1"',
            ValueError
        ),
    ]

    @pytest.mark.parametrize(
        "desc, uri, exp_exc_type",
        testcases_fails)
    def test_CIMClassName_from_wbem_uri_fails(self, desc, uri, exp_exc_type):
        # pylint: disable=unused-argument
        """All test cases where CIMClassName.from_wbem_uri() fails."""

        if CHECK_0_12_0:

            with pytest.raises(exp_exc_type):
                CIMClassName.from_wbem_uri(uri)


class Test_CIMClass_init(object):

    # Defaults to expect for attributes when not specified in testcase
    default_exp_attrs = dict(
        properties=NocaseDict(),
        methods=NocaseDict(),
        superclass=None,
        qualifiers=NocaseDict(),
        path=None,
    )

    def test_CIMClass_init_pos_args(self):
        # pylint: disable=unused-argument
        """Test position of arguments in CIMClass.__init__()."""

        properties = dict(P1=CIMProperty('P1', value=True))
        methods = dict(M1=CIMMethod('M1', return_type='string'))
        qualifiers = dict(Q1=CIMQualifier('Q1', value=True))
        path = CIMClassName('CIM_Foo')

        # The code to be tested
        obj = CIMClass(
            'CIM_Foo',
            properties,
            methods,
            'CIM_SuperFoo',
            qualifiers,
            path)

        assert obj.classname == u'CIM_Foo'
        assert obj.properties == NocaseDict(properties)
        assert obj.methods == NocaseDict(methods)
        assert obj.superclass == u'CIM_SuperFoo'
        assert obj.qualifiers == NocaseDict(qualifiers)
        assert obj.path == path

    property_P1 = CIMProperty('P1', value='abc')
    method_M1 = CIMMethod('M1', return_type='string')
    qualifier_Q1 = CIMQualifier('Q1', value='abc')
    classpath_1 = CIMClassName('CIM_Foo')

    testcases_succeeds = [
        # Testcases where CIMClass.__init__() succeeds.
        # Each testcase has these items:
        # * desc: Short testcase description.
        # * kwargs: Dict of keyword arguments for __init__().
        # * exp_attrs: Dict of expected attributes of resulting object.
        # * exp_warn_type: Expected warning type.
        # * condition: Condition for testcase to run.
        (
            "Verify that classname None is accepted (before 0.12)",
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
            "Verify that binary superclass is converted to unicode",
            dict(classname=u'CIM_Foo', superclass=b'CIM_Foo'),
            dict(classname=u'CIM_Foo', superclass=u'CIM_Foo'),
            None, True
        ),
        (
            "Verify that unicode superclass remains unicode",
            dict(classname=u'CIM_Foo', superclass=u'CIM_Foo'),
            dict(classname=u'CIM_Foo', superclass=u'CIM_Foo'),
            None, True
        ),
        (
            "Verify that properties dict is converted to NocaseDict",
            dict(classname=u'CIM_Foo', properties=dict(P1=property_P1)),
            dict(classname=u'CIM_Foo', properties=NocaseDict(P1=property_P1)),
            None, True
        ),
        (
            "Verify that property provided as simple value is stored as "
            "provided (before 0.12)",
            dict(classname=u'CIM_Foo',
                 properties=dict(P1=property_P1.value)),
            dict(classname=u'CIM_Foo',
                 properties=NocaseDict(P1=property_P1.value)),
            None, not CHECK_0_12_0
        ),
        (
            "Verify that methods dict is converted to NocaseDict",
            dict(classname=u'CIM_Foo', methods=dict(M1=method_M1)),
            dict(classname=u'CIM_Foo', methods=NocaseDict(M1=method_M1)),
            None, True
        ),
        (
            "Verify that qualifiers dict is converted to NocaseDict",
            dict(classname=u'CIM_Foo', qualifiers=dict(Q1=qualifier_Q1)),
            dict(classname=u'CIM_Foo', qualifiers=NocaseDict(Q1=qualifier_Q1)),
            None, True
        ),
        (
            "Verify that qualifier provided as simple value is stored as "
            "provided (before 0.12)",
            dict(classname=u'CIM_Foo',
                 qualifiers=dict(Q1=qualifier_Q1.value)),
            dict(classname=u'CIM_Foo',
                 qualifiers=NocaseDict(Q1=qualifier_Q1.value)),
            None, not CHECK_0_12_0
        ),
        (
            "Verify that qualifier provided as simple value is converted to "
            "CIMQualifier (since 0.12)",
            dict(classname=u'CIM_Foo',
                 qualifiers=dict(Q1=qualifier_Q1.value)),
            dict(classname=u'CIM_Foo',
                 qualifiers=NocaseDict(Q1=qualifier_Q1)),
            None, CHECK_0_12_0
        ),
        (
            "Verify that CIMClassName path is accepted",
            dict(classname=u'CIM_Foo', path=classpath_1),
            dict(classname=u'CIM_Foo', path=classpath_1),
            None, True
        ),
    ]

    @pytest.mark.parametrize(
        "desc, kwargs, exp_attrs, exp_warn_type, condition",
        testcases_succeeds)
    def test_CIMClass_init_succeeds(
            self, desc, kwargs, exp_attrs, exp_warn_type, condition):
        # pylint: disable=unused-argument
        """All test cases where CIMClass.__init__() succeeds."""

        if not condition:
            pytest.skip("Condition for test case not met")

        exp_classname = exp_attrs['classname']
        exp_properties = exp_attrs.get(
            'properties', self.default_exp_attrs['properties'])
        exp_methods = exp_attrs.get(
            'methods', self.default_exp_attrs['methods'])
        exp_superclass = exp_attrs.get(
            'superclass', self.default_exp_attrs['superclass'])
        exp_qualifiers = exp_attrs.get(
            'qualifiers', self.default_exp_attrs['qualifiers'])
        exp_path = exp_attrs.get(
            'path', self.default_exp_attrs['path'])

        if exp_warn_type is None:

            # The code to be tested
            obj = CIMClass(**kwargs)

        else:
            with pytest.warns(exp_warn_type):

                # The code to be tested
                obj = CIMClass(**kwargs)

        assert obj.classname == exp_classname
        assert isinstance(obj.classname, type(exp_classname))

        assert obj.properties == exp_properties
        assert isinstance(obj.properties, type(exp_properties))

        assert obj.methods == exp_methods
        assert isinstance(obj.methods, type(exp_methods))

        assert obj.superclass == exp_superclass
        assert isinstance(obj.superclass, type(exp_superclass))

        assert obj.qualifiers == exp_qualifiers
        assert isinstance(obj.qualifiers, type(exp_qualifiers))

        assert obj.path == exp_path
        assert isinstance(obj.path, type(exp_path))

    testcases_fails = [
        # Testcases where CIMClass.__init__() fails.
        # Each testcase has these items:
        # * desc: Short testcase description.
        # * kwargs: Dict of keyword arguments for __init__().
        # * exp_exc_type: Expected exception type.
        # * condition: Condition for testcase to run.
        (
            "Verify that classname None fails (since 0.12)",
            dict(classname=None),
            ValueError,
            CHECK_0_12_0
        ),
        (
            "Verify that property with key None fails",
            dict(
                classname='CIM_Foo',
                properties={None: property_P1}),
            ValueError if CHECK_0_12_0 else TypeError,
            True
        ),
        (
            "Verify that property with inconsistent key / name fails "
            "(since 0.12)",
            dict(
                classname='CIM_Foo',
                properties=dict(P1_X=property_P1)),
            ValueError,
            CHECK_0_12_0
        ),
        (
            "Verify that property provided as simple value fails "
            "(since 0.12)",
            dict(
                classname='CIM_Foo',
                properties=dict(P1=property_P1.value)),
            TypeError,
            CHECK_0_12_0
        ),
        (
            "Verify that method with key None fails",
            dict(
                classname='CIM_Foo',
                methods={None: method_M1}),
            ValueError if CHECK_0_12_0 else TypeError,
            True
        ),
        (
            "Verify that method with inconsistent key / name fails "
            "(since 0.12)",
            dict(
                classname='CIM_Foo',
                methods=dict(M1_X=method_M1)),
            ValueError,
            CHECK_0_12_0
        ),
        (
            "Verify that qualifier with key None fails",
            dict(
                classname='CIM_Foo',
                qualifiers={None: qualifier_Q1}),
            ValueError if CHECK_0_12_0 else TypeError,
            True
        ),
        (
            "Verify that qualifier with inconsistent key / name fails "
            "(since 0.12)",
            dict(
                classname='CIM_Foo',
                qualifiers=dict(Q1_X=qualifier_Q1)),
            ValueError,
            CHECK_0_12_0
        ),
    ]

    @pytest.mark.parametrize(
        "desc, kwargs, exp_exc_type, condition",
        testcases_fails)
    def test_CIMClass_init_fails(
            self, desc, kwargs, exp_exc_type, condition):
        # pylint: disable=unused-argument
        """All test cases where CIMClass.__init__() fails."""

        if not condition:
            pytest.skip("Condition for test case not met")

        with pytest.raises(exp_exc_type):

            # The code to be tested
            CIMClass(**kwargs)


class CIMClassCopy(unittest.TestCase):

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
    Test CIMClass.__str__().

    That function returns for example::

       CIMClass(classname=CIM_Foo, ...)
    """

    classpath_1 = CIMClassName('CIM_Foo')

    testcases_succeeds = [
        # Testcases where CIMClass.__str__() succeeds.
        # Each testcase has these items:
        # * obj: CIMClass object to be tested.
        (
            CIMClass(
                classname='CIM_Foo')
        ),
        (
            CIMClass(
                classname='CIM_Foo',
                properties=dict(
                    Name=CIMProperty('Name', 'string'),
                    Ref1=CIMProperty('Ref1', 'reference')))
        ),
        (
            CIMClass(
                classname='CIM_Foo',
                properties=dict(
                    Name=CIMProperty('Name', 'string'),
                    Ref1=CIMProperty('Ref1', 'reference')),
                path=classpath_1)
        ),
    ]

    @pytest.mark.parametrize(
        "obj",
        testcases_succeeds)
    def test_CIMClass_str_succeeds(self, obj):
        """All test cases where CIMClass.__str__() succeeds."""

        s = str(obj)

        assert re.match(r'^CIMClass\(', s)

        exp_classname = 'classname=%r' % obj.classname
        assert exp_classname in s


class Test_CIMClass_repr(object):
    """
    Test CIMClass.__repr__().
    """

    classpath_1 = CIMClassName('CIM_Foo')

    testcases_succeeds = [
        # Testcases where CIMClass.__repr__() succeeds.
        # Each testcase has these items:
        # * obj: CIMClass object to be tested.
        (
            CIMClass(
                classname='CIM_Foo')
        ),
        (
            CIMClass(
                classname='CIM_Foo',
                properties=dict(
                    Name=CIMProperty('Name', 'string'),
                    Ref1=CIMProperty('Ref1', 'reference')))
        ),
        (
            CIMClass(
                classname='CIM_Foo',
                properties=dict(
                    Name=CIMProperty('Name', 'string'),
                    Ref1=CIMProperty('Ref1', 'reference')),
                path=classpath_1)
        ),
    ]

    @pytest.mark.parametrize(
        "obj",
        testcases_succeeds)
    def test_CIMClass_repr_succeeds(self, obj):
        """All test cases where CIMClass.__repr__() succeeds."""

        r = repr(obj)

        assert re.match(r'^CIMClass\(', r)

        exp_classname = 'classname=%r' % obj.classname
        assert exp_classname in r

        exp_superclass = 'superclass=%r' % obj.superclass
        assert exp_superclass in r

        exp_properties = 'properties=%r' % obj.properties
        assert exp_properties in r

        exp_methods = 'methods=%r' % obj.methods
        assert exp_methods in r

        exp_qualifiers = 'qualifiers=%r' % obj.qualifiers
        assert exp_qualifiers in r

        exp_path = 'path=%r' % obj.path
        assert exp_path in r


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
        pquals = {'ModelCorrespondence': CIMQualifier('ModelCorrespondence',
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


class Test_CIMMethod_init(object):
    """
    Test CIMMethod.__init__().
    """

    def test_CIMMethod_init_pos_args(self):
        # pylint: disable=unused-argument
        """Test position of arguments in CIMMethod.__init__()."""

        parameters = {'Param1': CIMParameter('Param1', 'uint32')}
        qualifiers = {'Key': CIMQualifier('Key', True)}

        # The code to be tested
        obj = CIMMethod(
            'FooMethod',
            'uint32',
            parameters,
            'CIM_Origin',
            True,
            qualifiers)

        assert obj.name == u'FooMethod'
        assert obj.return_type == u'uint32'
        assert obj.parameters == NocaseDict(parameters)
        assert obj.class_origin == u'CIM_Origin'
        assert obj.propagated is True
        assert obj.qualifiers == NocaseDict(qualifiers)

    def test_CIMMethod_init_methodname(self):
        # pylint: disable=unused-argument
        """Test deprecated methodname argument of CIMMethod.__init__()."""

        # The code to be tested
        with pytest.warns(DeprecationWarning):
            obj = CIMMethod(
                methodname='FooMethod',
                return_type='string')

        assert obj.name == u'FooMethod'

    def test_CIMMethod_init_name_methodname(self):
        # pylint: disable=unused-argument
        """Test both name and methodname argument of CIMMethod.__init__()."""

        if CHECK_0_12_0:
            exp_exc_type = ValueError
        else:
            exp_exc_type = TypeError

        # The code to be tested
        with pytest.raises(exp_exc_type):
            CIMMethod(
                name='FooMethod',
                methodname='FooMethod',
                return_type='string')

    # Defaults to expect for attributes when not specified in testcase
    default_exp_attrs = dict(
        parameters=NocaseDict(),
        class_origin=None,
        propagated=False,
        qualifiers=NocaseDict(),
    )

    parameter_P1 = CIMParameter('P1', type='uint32')
    qualifier_Q1 = CIMQualifier('Q1', value='abc')

    testcases_succeeds = [
        # Testcases where CIMMethod.__init__() succeeds.
        # Each testcase has these items:
        # * desc: Short testcase description.
        # * kwargs: Dict of keyword arguments for __init__().
        # * exp_attrs: Dict of expected attributes of resulting object.
        # * exp_warn_type: Expected warning type.
        # * condition: Condition for testcase to run.
        (
            "Verify that binary name and return type are converted to unicode",
            dict(name=b'FooMethod', return_type=b'string'),
            dict(name=u'FooMethod', return_type=u'string'),
            None, True
        ),
        (
            "Verify that unicode name and return type remain unicode",
            dict(name=u'FooMethod', return_type=u'string'),
            dict(name=u'FooMethod', return_type=u'string'),
            None, True
        ),
        (
            "Verify that parameters dict is converted to NocaseDict",
            dict(name=u'FooMethod', return_type=u'string',
                 parameters=dict(P1=parameter_P1)),
            dict(name=u'FooMethod', return_type=u'string',
                 parameters=NocaseDict(P1=parameter_P1)),
            None, True
        ),
        (
            "Verify that qualifiers dict is converted to NocaseDict",
            dict(name=u'FooMethod', return_type=u'string',
                 qualifiers=dict(Q1=qualifier_Q1)),
            dict(name=u'FooMethod', return_type=u'string',
                 qualifiers=NocaseDict(Q1=qualifier_Q1)),
            None, True
        ),
        (
            "Verify that binary class_origin is converted to unicode",
            dict(name=u'FooMethod', return_type=u'string',
                 class_origin=b'CIM_Origin'),
            dict(name=u'FooMethod', return_type=u'string',
                 class_origin=u'CIM_Origin'),
            None, True
        ),
        (
            "Verify that unicode class_origin remains unicode",
            dict(name=u'FooMethod', return_type=u'string',
                 class_origin=u'CIM_Origin'),
            dict(name=u'FooMethod', return_type=u'string',
                 class_origin=u'CIM_Origin'),
            None, True
        ),
        (
            "Verify that propagated int 42 is converted to bool True",
            dict(name=u'FooMethod', return_type=u'string',
                 propagated=42),
            dict(name=u'FooMethod', return_type=u'string',
                 propagated=True),
            None, CHECK_0_12_0
        ),
        (
            "Verify that propagated int 0 is converted to bool False",
            dict(name=u'FooMethod', return_type=u'string',
                 propagated=0),
            dict(name=u'FooMethod', return_type=u'string',
                 propagated=False),
            None, CHECK_0_12_0
        ),
        (
            "Verify that propagated string 'false' is converted to bool True",
            dict(name=u'FooMethod', return_type=u'string',
                 propagated='false'),
            dict(name=u'FooMethod', return_type=u'string',
                 propagated=True),
            None, CHECK_0_12_0
        ),
        (
            "Verify that propagated string 'true' is converted to bool True",
            dict(name=u'FooMethod', return_type=u'string',
                 propagated='true'),
            dict(name=u'FooMethod', return_type=u'string',
                 propagated=True),
            None, CHECK_0_12_0
        ),
        (
            "Verify that propagated bool True remains True",
            dict(name=u'FooMethod', return_type=u'string',
                 propagated=True),
            dict(name=u'FooMethod', return_type=u'string',
                 propagated=True),
            None, True
        ),
        (
            "Verify that propagated bool False remains False",
            dict(name=u'FooMethod', return_type=u'string',
                 propagated=False),
            dict(name=u'FooMethod', return_type=u'string',
                 propagated=False),
            None, True
        ),
    ]

    @pytest.mark.parametrize(
        "desc, kwargs, exp_attrs, exp_warn_type, condition",
        testcases_succeeds)
    def test_CIMMethod_init_succeeds(
            self, desc, kwargs, exp_attrs, exp_warn_type, condition):
        # pylint: disable=unused-argument
        """All test cases where CIMMethod.__init__() succeeds."""

        if not condition:
            pytest.skip("Condition for test case not met")

        exp_name = exp_attrs['name']
        exp_return_type = exp_attrs['return_type']
        exp_parameters = exp_attrs.get(
            'parameters', self.default_exp_attrs['parameters'])
        exp_class_origin = exp_attrs.get(
            'class_origin', self.default_exp_attrs['class_origin'])
        exp_propagated = exp_attrs.get(
            'propagated', self.default_exp_attrs['propagated'])
        exp_qualifiers = exp_attrs.get(
            'qualifiers', self.default_exp_attrs['qualifiers'])

        if exp_warn_type is None:

            # The code to be tested
            obj = CIMMethod(**kwargs)

        else:
            with pytest.warns(exp_warn_type):

                # The code to be tested
                obj = CIMMethod(**kwargs)

        assert obj.name == exp_name
        assert isinstance(obj.name, type(exp_name))

        assert obj.return_type == exp_return_type
        assert isinstance(obj.return_type, type(exp_return_type))

        assert obj.parameters == exp_parameters
        assert isinstance(obj.parameters, type(exp_parameters))

        assert obj.class_origin == exp_class_origin
        assert isinstance(obj.class_origin, type(exp_class_origin))

        assert obj.propagated == exp_propagated
        assert isinstance(obj.propagated, type(exp_propagated))

        assert obj.qualifiers == exp_qualifiers
        assert isinstance(obj.qualifiers, type(exp_qualifiers))

    testcases_fails = [
        # Testcases where CIMMethod.__init__() fails.
        # Each testcase has these items:
        # * desc: Short testcase description.
        # * kwargs: Dict of keyword arguments for __init__().
        # * exp_exc_type: Expected exception type.
        # * condition: Condition for testcase to run.
        (
            "Verify that name None fails (with ValueError since 0.12)",
            dict(name=None, return_type='string'),
            ValueError, CHECK_0_12_0
        ),
        (
            "Verify that name None fails (with TypeError before 0.12)",
            dict(name=None, return_type='string'),
            TypeError, not CHECK_0_12_0
        ),
        (
            "Verify that name and methodname fails (ValueError since 0.12)",
            dict(name='M', methodname='M', return_type='string'),
            ValueError, CHECK_0_12_0
        ),
        (
            "Verify that name and methodname fails (TypeError before 0.12)",
            dict(name='M', methodname='M', return_type='string'),
            TypeError, not CHECK_0_12_0
        ),
        (
            "Verify that parameters with inconsistent name fails "
            "(since 0.12)",
            dict(
                name='M',
                parameters=dict(P1=CIMParameter('P1_X', 'abc'))),
            ValueError, CHECK_0_12_0
        ),
        (
            "Verify that qualifiers with inconsistent name fails "
            "(since 0.12)",
            dict(
                name='M',
                qualifiers=dict(Q1=CIMQualifier('Q1_X', 'abc'))),
            ValueError, CHECK_0_12_0
        ),
    ]

    @pytest.mark.parametrize(
        "desc, kwargs, exp_exc_type, condition",
        testcases_fails)
    def test_CIMMethod_init_fails(
            self, desc, kwargs, exp_exc_type, condition):
        # pylint: disable=unused-argument
        """All test cases where CIMMethod.__init__() fails."""

        if not condition:
            pytest.skip("Condition for test case not met")

        with pytest.raises(exp_exc_type):

            # The code to be tested
            CIMMethod(**kwargs)


class CIMMethodCopy(unittest.TestCase):

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
    Test CIMMethod.__str__().

    That function returns for example::

       CIMMethod(name='FooMethod', return_type='string')
    """

    parameter_P1 = CIMParameter('P1', type='uint32')
    qualifier_Q1 = CIMQualifier('Q1', value=True)

    testcases_succeeds = [
        # Testcases where CIMMethod.__str__() succeeds.
        # Each testcase has these items:
        # * obj: CIMMethod object to be tested.
        (
            CIMMethod(
                name='FooMethod',
                return_type='uint32')
        ),
        (
            CIMMethod(
                name='FooMethod',
                return_type='uint32',
                parameters=dict(P1=parameter_P1),
                class_origin='CIM_Origin',
                propagated=True,
                qualifiers=dict(Q1=qualifier_Q1))
        ),
    ]

    @pytest.mark.parametrize(
        "obj",
        testcases_succeeds)
    def test_CIMMethod_str_succeeds(self, obj):
        """All test cases where CIMMethod.__str__() succeeds."""

        s = str(obj)

        assert re.match(r'^CIMMethod\(', s)

        exp_name = 'name=%r' % obj.name
        assert exp_name in s

        exp_return_type = 'return_type=%r' % obj.return_type
        assert exp_return_type in s


class Test_CIMMethod_repr(object):
    """
    Test CIMMethod.__repr__().
    """

    parameter_P1 = CIMParameter('P1', type='uint32')
    qualifier_Q1 = CIMQualifier('Q1', value=True)

    testcases_succeeds = [
        # Testcases where CIMMethod.__repr__() succeeds.
        # Each testcase has these items:
        # * obj: CIMMethod object to be tested.
        (
            CIMMethod(
                name='FooMethod',
                return_type='uint32')
        ),
        (
            CIMMethod(
                name='FooMethod',
                return_type='uint32',
                parameters=dict(P1=parameter_P1),
                class_origin='CIM_Origin',
                propagated=True,
                qualifiers=dict(Q1=qualifier_Q1))
        ),
    ]

    @pytest.mark.parametrize(
        "obj",
        testcases_succeeds)
    def test_CIMMethod_repr_succeeds(self, obj):
        """All test cases where CIMMethod.__repr__() succeeds."""

        r = repr(obj)

        assert re.match(r'^CIMMethod\(', r)

        exp_name = 'name=%r' % obj.name
        assert exp_name in r

        exp_return_type = 'return_type=%r' % obj.return_type
        assert exp_return_type in r

        exp_parameters = 'parameters=%r' % obj.parameters
        assert exp_parameters in r

        exp_class_origin = 'class_origin=%r' % obj.class_origin
        assert exp_class_origin in r

        exp_propagated = 'propagated=%r' % obj.propagated
        assert exp_propagated in r

        exp_qualifiers = 'qualifiers=%r' % obj.qualifiers
        assert exp_qualifiers in r


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


class Test_CIMParameter_init(object):
    """
    Test CIMParameter.__init__().
    """

    def test_CIMParameter_init_pos_args(self):
        # pylint: disable=unused-argument
        """Test position of arguments in CIMParameter.__init__()."""

        qualifiers = {'Key': CIMQualifier('Key', True)}

        # The code to be tested
        obj = CIMParameter(
            'FooParam',
            'uint32',
            'CIM_Ref',
            True,
            2,
            qualifiers,
            None)

        assert obj.name == u'FooParam'
        assert obj.type == u'uint32'
        assert obj.reference_class == u'CIM_Ref'
        assert obj.is_array is True
        assert obj.array_size == 2
        assert obj.qualifiers == NocaseDict(qualifiers)
        assert obj.value is None

    # Defaults to expect for attributes when not specified in testcase
    default_exp_attrs = dict(
        reference_class=None,
        is_array=False if CHECK_0_12_0 else None,
        array_size=None,
        qualifiers=NocaseDict(),
        value=None,
    )

    qualifier_Q1 = CIMQualifier('Q1', value='abc')

    testcases_succeeds = [
        # Testcases where CIMParameter.__init__() succeeds.
        # Each testcase has these items:
        # * desc: Short testcase description.
        # * kwargs: Dict of keyword arguments for __init__().
        # * exp_attrs: Dict of expected attributes of resulting object.
        # * exp_warn_type: Expected warning type.
        # * condition: Condition for testcase to run.
        (
            "Verify that name can be None although documented otherwise "
            "(before 0.12)",
            dict(name=None, type=u'string'),
            dict(name=None, type=u'string'),
            None, not CHECK_0_12_0
        ),
        (
            "Verify that type can be None although documented otherwise "
            "(before 0.12)",
            dict(name=u'FooParam', type=None),
            dict(name=u'FooParam', type=None),
            None, not CHECK_0_12_0
        ),
        (
            "Verify that binary name and type are converted to unicode",
            dict(name=b'FooParam', type=b'string'),
            dict(name=u'FooParam', type=u'string'),
            None, True
        ),
        (
            "Verify that unicode name and type remain unicode",
            dict(name=u'FooParam', type=u'string'),
            dict(name=u'FooParam', type=u'string'),
            None, True
        ),
        (
            "Verify that binary reference_class is converted to unicode",
            dict(name=u'FooParam', type=u'string',
                 reference_class=b'CIM_Ref'),
            dict(name=u'FooParam', type=u'string',
                 reference_class=u'CIM_Ref'),
            None, True
        ),
        (
            "Verify that unicode reference_class remains unicode",
            dict(name=u'FooParam', type=u'string',
                 reference_class=u'CIM_Ref'),
            dict(name=u'FooParam', type=u'string',
                 reference_class=u'CIM_Ref'),
            None, True
        ),
        (
            "Verify that array reference_class is accepted",
            dict(name=u'FooParam', type=u'string', is_array=True,
                 reference_class=b'CIM_Ref'),
            dict(name=u'FooParam', type=u'string', is_array=True,
                 reference_class=u'CIM_Ref'),
            None, True
        ),
        (
            "Verify that is_array 42 is converted to bool (since 0.12)",
            dict(name=u'FooParam', type=u'string',
                 is_array=42),
            dict(name=u'FooParam', type=u'string',
                 is_array=True),
            None, CHECK_0_12_0
        ),
        (
            "Verify that is_array 'false' is converted to bool using Python "
            "bool rules(since 0.12)",
            dict(name=u'FooParam', type=u'string',
                 is_array='false'),
            dict(name=u'FooParam', type=u'string',
                 is_array=True),
            None, CHECK_0_12_0
        ),
        (
            "Verify that unspecified is_array is implied to scalar by value "
            "None (since 0.12)",
            dict(name='FooParam', type='string',
                 is_array=None, value=None),
            dict(name=u'FooParam', type=u'string',
                 is_array=False, value=None),
            None, CHECK_0_12_0
        ),
        (
            "Verify that unspecified is_array is implied to scalar by scalar "
            "value (since 0.12)",
            dict(name='FooParam', type='string',
                 is_array=None, value=u'abc'),
            dict(name=u'FooParam', type=u'string',
                 is_array=False, value=u'abc'),
            DeprecationWarning, CHECK_0_12_0
        ),
        (
            "Verify that unspecified is_array is implied to array by array "
            "value (since 0.12)",
            dict(name='FooParam', type='string',
                 is_array=None, value=[u'abc']),
            dict(name=u'FooParam', type=u'string',
                 is_array=True, value=[u'abc']),
            DeprecationWarning, CHECK_0_12_0
        ),
        (
            "Verify that unspecified is_array remains unspecified with value "
            "None (before 0.12)",
            dict(name='FooParam', type='string',
                 is_array=None, value=None),
            dict(name=u'FooParam', type=u'string',
                 is_array=None, value=None),
            None, not CHECK_0_12_0
        ),
        (
            "Verify that unspecified is_array remains unspecified with scalar "
            "value (before 0.12)",
            dict(name='FooParam', type='string',
                 is_array=None, value=u'abc'),
            dict(name=u'FooParam', type=u'string',
                 is_array=None, value=u'abc'),
            None, not CHECK_0_12_0
        ),
        (
            "Verify that unspecified is_array remains unspecified with array "
            "value (before 0.12)",
            dict(name='FooParam', type='string',
                 is_array=None, value=[u'abc']),
            dict(name=u'FooParam', type=u'string',
                 is_array=None, value=[u'abc']),
            None, not CHECK_0_12_0
        ),
        (
            "Verify that array_size 2 remains int",
            dict(name=u'FooParam', type=u'string', is_array=True,
                 array_size=2),
            dict(name=u'FooParam', type=u'string', is_array=True,
                 array_size=2),
            None, True
        ),
        (
            "Verify that qualifiers dict is converted to NocaseDict",
            dict(name=u'FooParam', type=u'string',
                 qualifiers=dict(Q1=qualifier_Q1)),
            dict(name=u'FooParam', type=u'string',
                 qualifiers=NocaseDict(Q1=qualifier_Q1)),
            None, True
        ),
        (
            "Verify that value is stored as provided (and issues deprecation "
            "warning since 0.12)",
            dict(name=u'FooParam', type=u'string',
                 value='abc'),
            dict(name=u'FooParam', type=u'string',
                 value=u'abc' if CHECK_0_12_0 else 'abc'),
            DeprecationWarning if CHECK_0_12_0 else None, True
        ),
    ]

    @pytest.mark.parametrize(
        "desc, kwargs, exp_attrs, exp_warn_type, condition",
        testcases_succeeds)
    def test_CIMParameter_init_succeeds(
            self, desc, kwargs, exp_attrs, exp_warn_type, condition):
        # pylint: disable=unused-argument
        """All test cases where CIMParameter.__init__() succeeds."""

        if not condition:
            pytest.skip("Condition for test case not met")

        exp_name = exp_attrs['name']
        exp_type = exp_attrs['type']
        exp_reference_class = exp_attrs.get(
            'reference_class', self.default_exp_attrs['reference_class'])
        exp_is_array = exp_attrs.get(
            'is_array', self.default_exp_attrs['is_array'])
        exp_array_size = exp_attrs.get(
            'array_size', self.default_exp_attrs['array_size'])
        exp_qualifiers = exp_attrs.get(
            'qualifiers', self.default_exp_attrs['qualifiers'])
        exp_value = exp_attrs.get(
            'value', self.default_exp_attrs['value'])

        if exp_warn_type is None:

            # The code to be tested
            obj = CIMParameter(**kwargs)

        else:
            with pytest.warns(exp_warn_type):

                # The code to be tested
                obj = CIMParameter(**kwargs)

        assert obj.name == exp_name
        assert isinstance(obj.name, type(exp_name))

        assert obj.type == exp_type
        assert isinstance(obj.type, type(exp_type))

        assert obj.reference_class == exp_reference_class
        assert isinstance(obj.reference_class, type(exp_reference_class))

        assert obj.is_array == exp_is_array
        assert isinstance(obj.is_array, type(exp_is_array))

        assert obj.array_size == exp_array_size
        assert isinstance(obj.array_size, type(exp_array_size))

        assert obj.qualifiers == exp_qualifiers
        assert isinstance(obj.qualifiers, type(exp_qualifiers))

        assert obj.value == exp_value
        assert isinstance(obj.value, type(exp_value))

    testcases_fails = [
        # Testcases where CIMParameter.__init__() fails.
        # Each testcase has these items:
        # * desc: Short testcase description.
        # * kwargs: Dict of keyword arguments for __init__().
        # * exp_exc_type: Expected exception type.
        # * condition: Condition for testcase to run.
        (
            "Verify that name None fails (since 0.12)",
            dict(name=None, type='string'),
            ValueError, CHECK_0_12_0
        ),
        (
            "Verify that type None fails (since 0.12)",
            dict(name='M', type=None),
            ValueError, CHECK_0_12_0
        ),
        (
            "Verify that qualifier with inconsistent key / name fails "
            "(since 0.12)",
            dict(name='M', type='string',
                 qualifiers=dict(Q1=CIMQualifier('Q1_X', 'abc'))),
            ValueError, CHECK_0_12_0
        ),
    ]

    @pytest.mark.parametrize(
        "desc, kwargs, exp_exc_type, condition",
        testcases_fails)
    def test_CIMParameter_init_fails(
            self, desc, kwargs, exp_exc_type, condition):
        # pylint: disable=unused-argument
        """All test cases where CIMParameter.__init__() fails."""

        if not condition:
            pytest.skip("Condition for test case not met")

        with pytest.raises(exp_exc_type):

            # The code to be tested
            CIMParameter(**kwargs)


class CIMParameterCopy(unittest.TestCase):

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
    Test CIMParameter.__str__().

    That function returns for example::

       CIMParameter(name='Param1', type='string', reference_class=None,
                    is_array=True, ...)
    """

    qualifier_Q1 = CIMQualifier('Q1', value=Uint32(42))

    testcases_succeeds = [
        # Testcases where CIMParameter.__str__() succeeds.
        # Each testcase has these items:
        # * obj: CIMParameter object to be tested.
        (
            CIMParameter(
                name='Param1',
                type='uint32')
        ),
        (
            CIMParameter(
                name='Param1',
                type='uint32',
                reference_class='CIM_Ref',
                is_array=False,
                array_size=None,
                qualifiers=dict(Q1=qualifier_Q1),
                value=None)
        ),
    ]

    @pytest.mark.parametrize(
        "obj",
        testcases_succeeds)
    def test_CIMParameter_str_succeeds(self, obj):
        """All test cases where CIMParameter.__str__() succeeds."""

        s = str(obj)

        assert re.match(r'^CIMParameter\(', s)

        exp_name = 'name=%r' % obj.name
        assert exp_name in s

        exp_type = 'type=%r' % obj.type
        assert exp_type in s

        exp_reference_class = 'reference_class=%r' % obj.reference_class
        assert exp_reference_class in s

        exp_is_array = 'is_array=%r' % obj.is_array
        assert exp_is_array in s


class Test_CIMParameter_repr(object):
    """
    Test CIMParameter.__repr__().
    """

    qualifier_Q1 = CIMQualifier('Q1', value=Uint32(42))

    testcases_succeeds = [
        # Testcases where CIMParameter.__str__() succeeds.
        # Each testcase has these items:
        # * obj: CIMParameter object to be tested.
        (
            CIMParameter(
                name='Param1',
                type='uint32')
        ),
        (
            CIMParameter(
                name='Param1',
                type='uint32',
                reference_class='CIM_Ref',
                is_array=False,
                array_size=None,
                qualifiers=dict(Q1=qualifier_Q1),
                value=None)
        ),
    ]

    @pytest.mark.parametrize(
        "obj",
        testcases_succeeds)
    def test_CIMParameter_repr_succeeds(self, obj):
        """All test cases where CIMParameter.__repr__() succeeds."""

        r = repr(obj)

        assert re.match(r'^CIMParameter\(', r)

        exp_name = 'name=%r' % obj.name
        assert exp_name in r

        exp_type = 'type=%r' % obj.type
        assert exp_type in r

        exp_reference_class = 'reference_class=%r' % obj.reference_class
        assert exp_reference_class in r

        exp_is_array = 'is_array=%r' % obj.is_array
        assert exp_is_array in r

        exp_array_size = 'array_size=%r' % obj.array_size
        assert exp_array_size in r

        exp_qualifiers = 'qualifiers=%r' % obj.qualifiers
        assert exp_qualifiers in r


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


class Test_CIMQualifierDeclaration_init(object):
    """
    Test CIMQualifierDeclaration.__init__().
    """

    def test_CIMQualifierDeclaration_init_pos_args(self):
        # pylint: disable=unused-argument
        """Test position of arguments in CIMQualifierDeclaration.__init__()."""

        scopes = dict(CLASS=True)

        # The code to be tested
        obj = CIMQualifierDeclaration(
            'FooQual',
            'uint32',
            [Uint32(42)],
            True,
            2,
            scopes,
            True,
            False,
            True,
            False)

        assert obj.name == u'FooQual'
        assert obj.type == u'uint32'
        assert obj.value == [Uint32(42)]
        assert obj.is_array is True
        assert obj.array_size == 2
        assert obj.scopes == NocaseDict(scopes)
        assert obj.overridable is True
        assert obj.tosubclass is False
        assert obj.toinstance is True
        assert obj.translatable is False

    # Defaults to expect for attributes when not specified in testcase
    default_exp_attrs = dict(
        value=None,
        is_array=False,
        array_size=None,
        scopes=NocaseDict(),
        overridable=None,
        tosubclass=None,
        toinstance=None,
        translatable=None
    )

    scopes1 = dict(CLASS=True)

    testcases_succeeds = [
        # Testcases where CIMQualifierDeclaration.__init__() succeeds.
        # Each testcase has these items:
        # * desc: Short testcase description.
        # * kwargs: Dict of keyword arguments for __init__().
        # * exp_attrs: Dict of expected attributes of resulting object.
        # * exp_warn_type: Expected warning type.
        # * condition: Condition for testcase to run.
        (
            "Verify that name can be None although documented otherwise "
            "(before 0.12)",
            dict(name=None, type=u'string'),
            dict(name=None, type=u'string'),
            None, not CHECK_0_12_0
        ),
        (
            "Verify that type can be None although documented otherwise "
            "(before 0.12)",
            dict(name=u'FooQual', type=None),
            dict(name=u'FooQual', type=None),
            None, not CHECK_0_12_0
        ),
        (
            "Verify that binary name and return type are converted to unicode",
            dict(name=b'FooQual', type=b'string'),
            dict(name=u'FooQual', type=u'string'),
            None, True
        ),
        (
            "Verify that unicode name and return type remain unicode",
            dict(name=u'FooQual', type=u'string'),
            dict(name=u'FooQual', type=u'string'),
            None, True
        ),
        (
            "Verify that is_array int 42 is converted to bool True",
            dict(
                name=u'FooQual',
                type=u'string',
                is_array=42),
            dict(
                name=u'FooQual',
                type=u'string',
                is_array=True),
            None, CHECK_0_12_0
        ),
        (
            "Verify that is_array int 0 is converted to bool False",
            dict(
                name=u'FooQual',
                type=u'string',
                is_array=0),
            dict(
                name=u'FooQual',
                type=u'string',
                is_array=False),
            None, CHECK_0_12_0
        ),
        (
            "Verify that is_array bool True remains True",
            dict(
                name=u'FooQual',
                type=u'string',
                is_array=True),
            dict(
                name=u'FooQual',
                type=u'string',
                is_array=True),
            None, True
        ),
        (
            "Verify that is_array bool False remains False",
            dict(
                name=u'FooQual',
                type=u'string',
                is_array=False),
            dict(
                name=u'FooQual',
                type=u'string',
                is_array=False),
            None, True
        ),
        (
            "Verify that unspecified is_array is implied to scalar by value "
            "None (since 0.12)",
            dict(name='FooQual', type='string',
                 is_array=None, value=None),
            dict(name=u'FooQual', type=u'string',
                 is_array=False, value=None),
            None, CHECK_0_12_0
        ),
        (
            "Verify that unspecified is_array is implied to scalar by scalar "
            "value (since 0.12)",
            dict(name='FooQual', type='string',
                 is_array=None, value=u'abc'),
            dict(name=u'FooQual', type=u'string',
                 is_array=False, value=u'abc'),
            None, CHECK_0_12_0
        ),
        (
            "Verify that unspecified is_array is implied to array by array "
            "value (since 0.12)",
            dict(name='FooQual', type='string',
                 is_array=None, value=[u'abc']),
            dict(name=u'FooQual', type=u'string',
                 is_array=True, value=[u'abc']),
            None, CHECK_0_12_0
        ),
        (
            "Verify that array_size int 42 remains int",
            dict(
                name=u'FooQual',
                type=u'string',
                is_array=True,
                array_size=42),
            dict(
                name=u'FooQual',
                type=u'string',
                is_array=True,
                array_size=42),
            None, CHECK_0_12_0
        ),
        (
            "Verify that scopes dict is converted to NocaseDict",
            dict(
                name=u'FooQual',
                type=u'string',
                scopes=scopes1),
            dict(
                name=u'FooQual',
                type=u'string',
                scopes=NocaseDict(scopes1)),
            None, CHECK_0_12_0
        ),
        (
            "Verify that overridable int 42 is converted to bool True",
            dict(
                name=u'FooQual',
                type=u'string',
                overridable=42),
            dict(
                name=u'FooQual',
                type=u'string',
                overridable=True),
            None, CHECK_0_12_0
        ),
        (
            "Verify that overridable int 0 is converted to bool False",
            dict(
                name=u'FooQual',
                type=u'string',
                overridable=0),
            dict(
                name=u'FooQual',
                type=u'string',
                overridable=False),
            None, CHECK_0_12_0
        ),
        (
            "Verify that overridable bool True remains True",
            dict(
                name=u'FooQual',
                type=u'string',
                overridable=True),
            dict(
                name=u'FooQual',
                type=u'string',
                overridable=True),
            None, True
        ),
        (
            "Verify that overridable bool False remains False",
            dict(
                name=u'FooQual',
                type=u'string',
                overridable=False),
            dict(
                name=u'FooQual',
                type=u'string',
                overridable=False),
            None, True
        ),
        (
            "Verify that tosubclass int 42 is converted to bool True",
            dict(
                name=u'FooQual',
                type=u'string',
                tosubclass=42),
            dict(
                name=u'FooQual',
                type=u'string',
                tosubclass=True),
            None, CHECK_0_12_0
        ),
        (
            "Verify that tosubclass int 0 is converted to bool False",
            dict(
                name=u'FooQual',
                type=u'string',
                tosubclass=0),
            dict(
                name=u'FooQual',
                type=u'string',
                tosubclass=False),
            None, CHECK_0_12_0
        ),
        (
            "Verify that tosubclass bool True remains True",
            dict(
                name=u'FooQual',
                type=u'string',
                tosubclass=True),
            dict(
                name=u'FooQual',
                type=u'string',
                tosubclass=True),
            None, True
        ),
        (
            "Verify that tosubclass bool False remains False",
            dict(
                name=u'FooQual',
                type=u'string',
                tosubclass=False),
            dict(
                name=u'FooQual',
                type=u'string',
                tosubclass=False),
            None, True
        ),
        (
            "Verify that toinstance int 42 is converted to bool True",
            dict(
                name=u'FooQual',
                type=u'string',
                toinstance=42),
            dict(
                name=u'FooQual',
                type=u'string',
                toinstance=True),
            None, CHECK_0_12_0
        ),
        (
            "Verify that toinstance int 0 is converted to bool False",
            dict(
                name=u'FooQual',
                type=u'string',
                toinstance=0),
            dict(
                name=u'FooQual',
                type=u'string',
                toinstance=False),
            None, CHECK_0_12_0
        ),
        (
            "Verify that toinstance bool True remains True",
            dict(
                name=u'FooQual',
                type=u'string',
                toinstance=True),
            dict(
                name=u'FooQual',
                type=u'string',
                toinstance=True),
            None, True
        ),
        (
            "Verify that toinstance bool False remains False",
            dict(
                name=u'FooQual',
                type=u'string',
                toinstance=False),
            dict(
                name=u'FooQual',
                type=u'string',
                toinstance=False),
            None, True
        ),
        (
            "Verify that translatable int 42 is converted to bool True",
            dict(
                name=u'FooQual',
                type=u'string',
                translatable=42),
            dict(
                name=u'FooQual',
                type=u'string',
                translatable=True),
            None, CHECK_0_12_0
        ),
        (
            "Verify that translatable int 0 is converted to bool False",
            dict(
                name=u'FooQual',
                type=u'string',
                translatable=0),
            dict(
                name=u'FooQual',
                type=u'string',
                translatable=False),
            None, CHECK_0_12_0
        ),
        (
            "Verify that translatable bool True remains True",
            dict(
                name=u'FooQual',
                type=u'string',
                translatable=True),
            dict(
                name=u'FooQual',
                type=u'string',
                translatable=True),
            None, True
        ),
        (
            "Verify that translatable bool False remains False",
            dict(
                name=u'FooQual',
                type=u'string',
                translatable=False),
            dict(
                name=u'FooQual',
                type=u'string',
                translatable=False),
            None, True
        ),
    ]

    @pytest.mark.parametrize(
        "desc, kwargs, exp_attrs, exp_warn_type, condition",
        testcases_succeeds)
    def test_CIMQualifierDeclaration_init_succeeds(
            self, desc, kwargs, exp_attrs, exp_warn_type, condition):
        # pylint: disable=unused-argument
        """All test cases where CIMQualifierDeclaration.__init__() succeeds."""

        if not condition:
            pytest.skip("Condition for test case not met")

        exp_name = exp_attrs['name']
        exp_type = exp_attrs['type']
        exp_value = exp_attrs.get(
            'value', self.default_exp_attrs['value'])
        exp_is_array = exp_attrs.get(
            'is_array', self.default_exp_attrs['is_array'])
        exp_array_size = exp_attrs.get(
            'array_size', self.default_exp_attrs['array_size'])
        exp_scopes = exp_attrs.get(
            'scopes', self.default_exp_attrs['scopes'])
        exp_overridable = exp_attrs.get(
            'overridable', self.default_exp_attrs['overridable'])
        exp_tosubclass = exp_attrs.get(
            'tosubclass', self.default_exp_attrs['tosubclass'])
        exp_toinstance = exp_attrs.get(
            'toinstance', self.default_exp_attrs['toinstance'])
        exp_translatable = exp_attrs.get(
            'translatable', self.default_exp_attrs['translatable'])

        if exp_warn_type is None:

            # The code to be tested
            obj = CIMQualifierDeclaration(**kwargs)

        else:
            with pytest.warns(exp_warn_type):

                # The code to be tested
                obj = CIMQualifierDeclaration(**kwargs)

        assert obj.name == exp_name
        assert isinstance(obj.name, type(exp_name))

        assert obj.type == exp_type
        assert isinstance(obj.type, type(exp_type))

        assert obj.value == exp_value
        assert isinstance(obj.value, type(exp_value))

        assert obj.is_array == exp_is_array
        assert isinstance(obj.is_array, type(exp_is_array))

        assert obj.array_size == exp_array_size
        assert isinstance(obj.array_size, type(exp_array_size))

        assert obj.scopes == exp_scopes
        assert isinstance(obj.scopes, type(exp_scopes))

        assert obj.overridable == exp_overridable
        assert isinstance(obj.overridable, type(exp_overridable))

        assert obj.tosubclass == exp_tosubclass
        assert isinstance(obj.tosubclass, type(exp_tosubclass))

        assert obj.toinstance == exp_toinstance
        assert isinstance(obj.toinstance, type(exp_toinstance))

        assert obj.translatable == exp_translatable
        assert isinstance(obj.translatable, type(exp_translatable))

    testcases_fails = [
        # Testcases where CIMQualifierDeclaration.__init__() fails.
        # Each testcase has these items:
        # * desc: Short testcase description.
        # * kwargs: Dict of keyword arguments for __init__().
        # * exp_exc_type: Expected exception type.
        # * condition: Condition for testcase to run.
        (
            "Verify that name None fails (since 0.12)",
            dict(name=None, type='string'),
            ValueError, CHECK_0_12_0
        ),
        (
            "Verify that type None fails (since 0.12)",
            dict(name='FooQual', type=None),
            ValueError, CHECK_0_12_0
        ),
        (
            "Verify that mismatch between is_array False and array_size fails",
            dict(name='FooQual', type='string',
                 is_array=False, array_size=4),
            ValueError, True
        ),
        (
            "Verify that mismatch between is_array False and array value fails",
            dict(name='FooQual', type='uint32',
                 is_array=False, value=[Uint32(x) for x in [1, 2, 3]]),
            ValueError, True
        ),
        (
            "Verify that mismatch between is_array True and scalar value fails",
            dict(name='FooQual', type='uint32',
                 is_array=True, value=Uint32(3)),
            ValueError, True
        ),
        (
            "Verify that unspecified is_array fails with value None "
            "(before 0.12)",
            dict(name='FooQual', type='string',
                 is_array=None, value=None),
            ValueError, not CHECK_0_12_0
        ),
        (
            "Verify that unspecified is_array fails with scalar value "
            "(before 0.12)",
            dict(name='FooQual', type='string',
                 is_array=None, value='abc'),
            ValueError, not CHECK_0_12_0
        ),
        (
            "Verify that unspecified is_array fails with array value "
            "(before 0.12)",
            dict(name='FooQual', type='string',
                 is_array=None, value=['abc']),
            ValueError, not CHECK_0_12_0
        ),
    ]

    @pytest.mark.parametrize(
        "desc, kwargs, exp_exc_type, condition",
        testcases_fails)
    def test_CIMQualifierDeclaration_init_fails(
            self, desc, kwargs, exp_exc_type, condition):
        # pylint: disable=unused-argument
        """All test cases where CIMQualifierDeclaration.__init__() fails."""

        if not condition:
            pytest.skip("Condition for test case not met")

        with pytest.raises(exp_exc_type):

            # The code to be tested
            CIMQualifierDeclaration(**kwargs)


class CIMQualifierDeclarationCopy(unittest.TestCase):

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
    Test CIMQualifierDeclaration.__str__().

    That function returns for example::

       CIMQualifierDeclaration(name='Qual1', value='abc', type='string',
                               is_array=False, ...)
    """

    testcases_succeeds = [
        # Testcases where CIMParameter.__str__() succeeds.
        # Each testcase has these items:
        # * obj: CIMParameter object to be tested.
        (
            CIMQualifierDeclaration(
                name='FooQualDecl',
                type='string')
        ),
        (
            CIMQualifierDeclaration(
                name='FooQualDecl',
                type='string',
                value=['abc'],
                is_array=True,
                array_size=1,
                scopes=dict(CLASS=True),
                overridable=True,
                tosubclass=True,
                toinstance=False,
                translatable=False)
        ),
    ]

    @pytest.mark.parametrize(
        "obj",
        testcases_succeeds)
    def test_CIMQualifierDeclaration_str_succeeds(self, obj):
        """All test cases where CIMQualifierDeclaration.__str__() succeeds."""

        s = str(obj)

        assert re.match(r'^CIMQualifierDeclaration\(', s)

        exp_name = 'name=%r' % obj.name
        assert exp_name in s

        exp_value = 'value=%r' % obj.value
        assert exp_value in s

        exp_type = 'type=%r' % obj.type
        assert exp_type in s

        exp_is_array = 'is_array=%r' % obj.is_array
        assert exp_is_array in s


class Test_CIMQualifierDeclaration_repr(object):
    """
    Test CIMQualifierDeclaration.__repr__().
    """

    testcases_succeeds = [
        # Testcases where CIMParameter.__repr__() succeeds.
        # Each testcase has these items:
        # * obj: CIMParameter object to be tested.
        (
            CIMQualifierDeclaration(
                name='FooQualDecl',
                type='string')
        ),
        (
            CIMQualifierDeclaration(
                name='FooQualDecl',
                type='string',
                value=['abc'],
                is_array=True,
                array_size=1,
                scopes=dict(CLASS=True),
                overridable=True,
                tosubclass=True,
                toinstance=False,
                translatable=False)
        ),
    ]

    @pytest.mark.parametrize(
        "obj",
        testcases_succeeds)
    def test_CIMQualifierDeclaration_repr_succeeds(self, obj):
        """All test cases where CIMQualifierDeclaration.__repr__() succeeds."""

        r = repr(obj)

        assert re.match(r'^CIMQualifierDeclaration\(', r)

        exp_name = 'name=%r' % obj.name
        assert exp_name in r

        exp_value = 'value=%r' % obj.value
        assert exp_value in r

        exp_type = 'type=%r' % obj.type
        assert exp_type in r

        exp_is_array = 'is_array=%r' % obj.is_array
        assert exp_is_array in r

        exp_array_size = 'array_size=%r' % obj.array_size
        assert exp_array_size in r

        exp_scopes = 'scopes=%r' % obj.scopes
        assert exp_scopes in r

        exp_tosubclass = 'tosubclass=%r' % obj.tosubclass
        assert exp_tosubclass in r

        exp_overridable = 'overridable=%r' % obj.overridable
        assert exp_overridable in r

        exp_translatable = 'translatable=%r' % obj.translatable
        assert exp_translatable in r

        exp_toinstance = 'toinstance=%r' % obj.toinstance
        assert exp_toinstance in r


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

    testcases_succeeds = [
        # Testcases where cimvalue() succeeds.
        # Each testcase has these items:
        # * value: The input value.
        # * type: The input type (as a CIM type name).
        # * exp_obj: Expected CIM value object.

        # Test cases where: Type is None (and is inferred from the value)

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

        # Test cases where: Type is string

        (None, 'string', None),

        (u'', 'string', u''),
        (u'a', 'string', u'a'),
        (u'abc', 'string', u'abc'),
        (u'\u00E4', 'string', u'\u00E4'),  # U+00E4 = lower case a umlaut

        (b'', 'string', u''),
        (b'a', 'string', u'a'),
        (b'abc', 'string', u'abc'),

        # Test cases where: Type is char16

        (None, 'char16', None),

        (u'', 'char16', u''),
        (u'a', 'char16', u'a'),
        (u'\u00E4', 'char16', u'\u00E4'),  # U+00E4 = lower case a umlaut

        (b'', 'char16', u''),
        (b'a', 'char16', u'a'),

        # Test cases where: Type is boolean

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

        # Test cases where: Type is an unsigned integer

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

        # Test cases where: Type is a signed integer

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

        # Test cases where: Type is a real

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

        # Test cases where: Type is datetime

        (None, 'datetime', None),

        (datetime1_dt, 'datetime', datetime1_obj),
        (datetime1_str, 'datetime', datetime1_obj),
        (datetime1_obj, 'datetime', datetime1_obj),

        (timedelta1_td, 'datetime', timedelta1_obj),
        (timedelta1_str, 'datetime', timedelta1_obj),
        (timedelta1_obj, 'datetime', timedelta1_obj),

        # Test cases where: Type is reference

        (None, 'reference', None),

        (ref1_str, 'reference', ref1_obj),
        (ref1_obj, 'reference', ref1_obj),
    ]

    @pytest.mark.parametrize(
        "value, type, exp_obj",
        testcases_succeeds)
    def test_cimvalue_succeeds(self, value, type, exp_obj):
        # pylint: disable=redefined-builtin
        """All test cases where cimvalue() succeeds."""

        if CHECK_0_12_0:

            obj = cimvalue(value, type)

            assert obj == exp_obj

    testcases_fails = [
        # Testcases where cimvalue() fails.
        # Each testcase has these items:
        # * value: The input value.
        # * type: The input type (as a CIM type name).
        # * exp_exc_type: Expected exception type.

        (42, None, TypeError),  # invalid type of value
        (-42, None, TypeError),
        (0, None, TypeError),
        (42.1, None, TypeError),

        ('abc', 'foo', ValueError),  # invalid CIM type name

        ('000000:000', 'datetime', ValueError),  # invalid dt value

        ('foo', 'reference', ValueError),  # invalid ref value
        (CIMClassName('CIM_Foo'), 'reference', TypeError),  # invalid type
    ]

    @pytest.mark.parametrize(
        "value, type, exp_exc_type",
        testcases_fails)
    def test_cimvalue_fails(self, value, type, exp_exc_type):
        # pylint: disable=redefined-builtin
        """All test cases where cimvalue() fails."""

        if CHECK_0_12_0:
            with pytest.raises(exp_exc_type):

                cimvalue(value, type)


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
