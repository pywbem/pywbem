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
import sys
import re
import inspect
import os.path
from datetime import timedelta, datetime
import warnings
import unittest2 as unittest  # we use assertRaises(exc) introduced in py27
try:
    from collections import OrderedDict
except ImportError:
    from ordereddict import OrderedDict

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
from unittest_extensions import CIMObjectMixin
import pytest_extensions


# A note on using pytest.warns:
#
# It turns out that catching Python warnings within test cases is a tricky
# thing.
#
# The main mechanism to understand is that Python warnings that are issued
# will be registered in a "warning registry" under certain circumstances. The
# "warning registry" is a variable named `__warningregistry__` in the global
# namespace of the module that issued the warning. A tuple of warning message,
# warning type, and line number where the warning is issued, is used as a key
# into that dictionary. If a warning is issued using `warnings.warn()`, and
# the "warning registry" already has the key for that warning (i.e. it has
# been previously been issued and registered), the warning is silently ignored,
# and thus will not be caught by the Python `warnings.catch_warnings` or
# `pytest.warns` context managers. This is of course undesired in test cases
# that use these context managers to verify that the warning was issued.
#
# The circumstances under which a warning is registered in the "warning
# registry" depend on the action that is set for that warning.
# For example, action "default" will cause the warning to be registered, and
# action "always" will not cause it to be registered.
# The `pytest.warns` context manager adds a filter with action "always" for all
# warnings upon entry, and removes that filter again upon exit.
#
# One solution is to catch all warnings that are ever issued, across all
# test cases that are executed in a single Python process invocation, with a
# `pytest.warns` context manager.
#
# Another solution is to set the action for all warnings to "always",
# e.g. by following the recommendation in
# https://docs.pytest.org/en/3.0.0/recwarn.html#ensuring-a-function-triggers-a-deprecation-warning
# namely to perform:
#    warnings.simplefilter('always')
# in each test case. The downside of this approach is that pytest displays a
# warning summary at the end for warnings that are issued that way.

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

    ncd_unnamed_key = NocaseDict()
    ncd_unnamed_key.allow_unnamed_keys = True
    ncd_unnamed_key[None] = 'abc'

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

        # Classname tests
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

        # Keybinding tests
        (
            "Verify that keybinding with name None succeeds (since 0.12",
            dict(
                classname='CIM_Foo',
                keybindings=dict(ncd_unnamed_key)),
            dict(
                classname=u'CIM_Foo',
                keybindings=ncd_unnamed_key),
            None, CHECK_0_12_0
        ),
        (
            "Verify keybindings order preservation with list of CIMProperty",
            dict(
                classname='CIM_Foo',
                keybindings=[
                    CIMProperty('K1', value='Ham'),
                    CIMProperty('K2', value='Cheese'),
                ]
            ),
            dict(
                classname=u'CIM_Foo',
                keybindings=NocaseDict([
                    ('K1', 'Ham'),
                    ('K2', 'Cheese'),
                ])
            ),
            None, True
        ),
        (
            "Verify keybindings order preservation with OrderedDict",
            dict(
                classname='CIM_Foo',
                keybindings=OrderedDict([
                    ('K1', 'Ham'),
                    ('K2', 'Cheese'),
                ])
            ),
            dict(
                classname=u'CIM_Foo',
                keybindings=NocaseDict([
                    ('K1', 'Ham'),
                    ('K2', 'Cheese'),
                ])
            ),
            None, True
        ),
        (
            "Verify keybindings order preservation with list of tuple(key,val)",
            dict(
                classname='CIM_Foo',
                keybindings=[
                    ('K1', 'Ham'),
                    ('K2', 'Cheese'),
                ]
            ),
            dict(
                classname=u'CIM_Foo',
                keybindings=NocaseDict([
                    ('K1', 'Ham'),
                    ('K2', 'Cheese'),
                ])
            ),
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
            "Verify keybinding with int value",
            dict(
                classname='CIM_Foo',
                keybindings=dict(K1=42)),
            dict(
                classname=u'CIM_Foo',
                keybindings=NocaseDict(K1=42)),
            None, True
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
            "Verify keybinding with float value",
            dict(
                classname='CIM_Foo',
                keybindings=dict(K1=42.1)),
            dict(
                classname=u'CIM_Foo',
                keybindings=NocaseDict(K1=42.1)),
            None, True
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
                keybindings=NocaseDict([('K1', u'Ham')])),
            None, CHECK_0_12_0
        ),
        (
            "Verify two keybindings",
            dict(
                classname='CIM_Foo',
                keybindings=OrderedDict([('K1', u'Ham'), ('K2', Uint8(42))])),
            dict(
                classname=u'CIM_Foo',
                keybindings=NocaseDict([('K1', u'Ham'), ('K2', Uint8(42))])),
            None, True
        ),
        (
            "Verify case insensitivity of keybinding names",
            dict(
                classname='CIM_Foo',
                keybindings=dict(Key1='Ham')),
            dict(
                classname=u'CIM_Foo',
                keybindings=NocaseDict([('kEY1', u'Ham')])),
            None, True
        ),

        # Namespace tests
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
            "Verify that one leading and trailing slash in namespace get "
            "stripped",
            dict(
                classname='CIM_Foo',
                namespace='/root/cimv2/'),
            dict(
                classname=u'CIM_Foo',
                namespace=u'root/cimv2'),
            None, True
        ),
        (
            "Verify that two leading and trailing slashes in namespace get "
            "stripped",
            dict(
                classname='CIM_Foo',
                namespace='//root/cimv2//'),
            dict(
                classname=u'CIM_Foo',
                namespace=u'root/cimv2'),
            None, True
        ),

        # Host tests
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
            with pytest.warns(exp_warn_type) as rec_warnings:

                # The code to be tested
                obj = CIMInstanceName(**kwargs)

            assert len(rec_warnings) == 1

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
            "Verify that keybinding with name None fails (before 0.12",
            dict(
                classname='CIM_Foo',
                keybindings={None: 'abc'}),
            TypeError,
            not CHECK_0_12_0
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

        kb = {'Chicken': 'Ham', 'Beans': Uint8(42)}

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

        # Setting keybindings with key being None

        obj.keybindings = {None: 'bar'}
        self.assertEqual(obj.keybindings[None], 'bar')


class CIMInstanceNameDict(DictionaryTestCase):
    """
    Test the dictionary interface of `CIMInstanceName` objects.
    """

    def test_all(self):

        kb = {'Chicken': 'Ham', 'Beans': Uint8(42)}
        obj = CIMInstanceName('CIM_Foo', kb)

        self.runtest_dict(obj, kb)


class CIMInstanceNameEquality(unittest.TestCase):
    """
    Test the equality comparison of `CIMInstanceName` objects.
    """

    # TODO 01/18 AM Remove test_all() once PR #955 is merged (is in test hash)
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
                                           'Number': Uint8(42),
                                           'Ref': CIMInstanceName('CIM_Bar')})

        obj2 = CIMInstanceName('CIM_Foo', {'Name': 'Foo',
                                           'Number': Uint8(42),
                                           'Boolean': False,
                                           'Ref': CIMInstanceName('CIM_Bar')})

        self.assertEqual(obj1, obj2)

        # Test that key binding types are not confused in comparisons

        self.assertNotEqual(CIMInstanceName('CIM_Foo', {'Foo': '42'}),
                            CIMInstanceName('CIM_Foo', {'Foo': Uint8(42)}))

        self.assertNotEqual(CIMInstanceName('CIM_Foo', {'Bar': True}),
                            CIMInstanceName('CIM_Foo', {'Bar': 'TRUE'}))

        # Key bindings should compare order-insensitively

        self.assertEqual(
            CIMInstanceName(
                'CIM_Foo',
                keybindings=(
                    ('Cheepy', 'Birds'),
                    ('Creepy', 'Ants'),
                )),
            CIMInstanceName(
                'CIM_Foo',
                keybindings=(
                    ('Cheepy', 'Birds'),
                    ('Creepy', 'Ants'),
                )),
        )

        self.assertEqual(
            CIMInstanceName(
                'CIM_Foo',
                keybindings=(
                    ('Cheepy', 'Birds'),
                    ('Creepy', 'Ants'),
                )),
            CIMInstanceName(
                'CIM_Foo',
                keybindings=(
                    ('Creepy', 'Ants'),
                    ('Cheepy', 'Birds'),
                )),
        )

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

    # TODO 01/18 AM Reformulate these tests in test hash once PR #955 is merged
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

        d1 = OrderedDict([(key1, value1), (key2, value2)])
        kb1 = NocaseDict(d1)
        obj1 = CIMInstanceName('CIM_Foo', kb1)

        d2 = OrderedDict([(key2, value2), (key1, value1)])
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


testcases_CIMInstanceName_hash = [

    # Each testcase tuple has these items:
    # * desc: Short testcase description.
    # * kwargs: Input arguments for test function, as a dict:
    #   * obj1: CIMInstanceName object #1 to be tested.
    #   * obj2: CIMInstanceName object #2 to be tested.
    #   * exp_hash_equal: Expected equality of the object hash values.
    # * exp_exc_types: Expected exception type(s), or None.
    # * exp_warn_types: Expected warning type(s), or None.
    # * condition: Boolean condition for testcase to run, or 'pdb' for debugger

    # Classname tests
    (
        "Classname, equal with same lexical case",
        dict(
            obj1=CIMInstanceName('CIM_Foo'),
            obj2=CIMInstanceName('CIM_Foo'),
            exp_hash_equal=True,
        ),
        None, None, True
    ),
    (
        "Classname, equal with different lexical case",
        dict(
            obj1=CIMInstanceName('CIM_Foo'),
            obj2=CIMInstanceName('ciM_foO'),
            exp_hash_equal=True,
        ),
        None, None, True
    ),
    (
        "Classname, different",
        dict(
            obj1=CIMInstanceName('CIM_Foo'),
            obj2=CIMInstanceName('CIM_Foo_x'),
            exp_hash_equal=False,
        ),
        None, None, True
    ),

    # Host tests
    (
        "Host name, equal with same lexical case",
        dict(
            obj1=CIMInstanceName('CIM_Foo', host='woot.com'),
            obj2=CIMInstanceName('CIM_Foo', host='woot.Com'),
            exp_hash_equal=True,
        ),
        None, None, True
    ),
    (
        "Host name, equal with different lexical case",
        dict(
            obj1=CIMInstanceName('CIM_Foo', host='woot.com'),
            obj2=CIMInstanceName('CIM_Foo', host='Woot.Com'),
            exp_hash_equal=True,
        ),
        None, None, True
    ),
    (
        "Host name, different with None / string",
        dict(
            obj1=CIMInstanceName('CIM_Foo', host=None),
            obj2=CIMInstanceName('CIM_Foo', host='woot.com'),
            exp_hash_equal=False,
        ),
        None, None, True
    ),
    (
        "Host name, different with string / None",
        dict(
            obj1=CIMInstanceName('CIM_Foo', host='woot.com'),
            obj2=CIMInstanceName('CIM_Foo', host=None),
            exp_hash_equal=False,
        ),
        None, None, True
    ),
    (
        "Host name, equal with None / None",
        dict(
            obj1=CIMInstanceName('CIM_Foo', host=None),
            obj2=CIMInstanceName('CIM_Foo', host=None),
            exp_hash_equal=True,
        ),
        None, None, True
    ),

    # Namespace tests
    (
        "Namespace, equal with same lexical case",
        dict(
            obj1=CIMInstanceName('CIM_Foo', namespace='root/cimv2'),
            obj2=CIMInstanceName('CIM_Foo', namespace='root/cimv2'),
            exp_hash_equal=True,
        ),
        None, None, True
    ),
    (
        "Namespace, equal with different lexical case",
        dict(
            obj1=CIMInstanceName('CIM_Foo', namespace='root/cimv2'),
            obj2=CIMInstanceName('CIM_Foo', namespace='Root/CIMv2'),
            exp_hash_equal=True,
        ),
        None, None, True
    ),
    (
        "Namespace, different",
        dict(
            obj1=CIMInstanceName('CIM_Foo', namespace='root/cimv2'),
            obj2=CIMInstanceName('CIM_Foo', namespace='abc'),
            exp_hash_equal=False,
        ),
        None, None, True
    ),
    (
        "Namespace, different with None / string",
        dict(
            obj1=CIMInstanceName('CIM_Foo', namespace=None),
            obj2=CIMInstanceName('CIM_Foo', namespace='root/cimv2'),
            exp_hash_equal=False,
        ),
        None, None, True
    ),
    (
        "Namespace, different with string / None",
        dict(
            obj1=CIMInstanceName('CIM_Foo', namespace='root/cimv2'),
            obj2=CIMInstanceName('CIM_Foo', namespace=None),
            exp_hash_equal=False,
        ),
        None, None, True
    ),
    (
        "Namespace, equal with None / None",
        dict(
            obj1=CIMInstanceName('CIM_Foo', namespace=None),
            obj2=CIMInstanceName('CIM_Foo', namespace=None),
            exp_hash_equal=True,
        ),
        None, None, True
    ),

    # Keybindings tests
    (
        "Matching keybindings, key names with same lexical case",
        dict(
            obj1=CIMInstanceName('CIM_Foo', keybindings={'Cheepy': 'Birds'}),
            obj2=CIMInstanceName('CIM_Foo', keybindings={'Cheepy': 'Birds'}),
            exp_hash_equal=True,
        ),
        None, None, True
    ),
    (
        "Matching keybindings, key names with different lexical case",
        dict(
            obj1=CIMInstanceName('CIM_Foo', keybindings={'Cheepy': 'Birds'}),
            obj2=CIMInstanceName('CIM_Foo', keybindings={'cheepy': 'Birds'}),
            exp_hash_equal=True,
        ),
        None, None, True
    ),
    (
        "Non-matching keybindings, one keybinding more",
        dict(
            obj1=CIMInstanceName('CIM_Foo'),
            obj2=CIMInstanceName('CIM_Foo', keybindings={'Cheepy': 'Birds'}),
            exp_hash_equal=False,
        ),
        None, None, True
    ),
    (
        "Non-matching keybindings, one keybinding less",
        dict(
            obj1=CIMInstanceName('CIM_Foo', keybindings={'Cheepy': 'Birds'}),
            obj2=CIMInstanceName('CIM_Foo'),
            exp_hash_equal=False,
        ),
        None, None, True
    ),
    (
        "Non-matching keybindings, different keybindings",
        dict(
            obj1=CIMInstanceName('CIM_Foo', keybindings={'Cheepy': 'Birds'}),
            obj2=CIMInstanceName('CIM_Foo', keybindings={'Creepy': 'Ants'}),
            exp_hash_equal=False,
        ),
        None, None, True
    ),
    (
        "Matching keybindings, with values that differ in lexical case",
        dict(
            obj1=CIMInstanceName('CIM_Foo', keybindings={'Cheepy': 'Birds'}),
            obj2=CIMInstanceName('CIM_Foo', keybindings={'Cheepy': 'birds'}),
            exp_hash_equal=False,
        ),
        None, None, True
    ),
    (
        "Matching keybindings, with values that is unicode / string",
        dict(
            obj1=CIMInstanceName('CIM_Foo', keybindings={'Cheepy': 'Birds'}),
            obj2=CIMInstanceName('CIM_Foo', keybindings={'Cheepy': u'Birds'}),
            exp_hash_equal=True,
        ),
        None, None, True
    ),
    (
        "Equal keybindings with a number of types",
        dict(
            obj1=CIMInstanceName('CIM_Foo', keybindings={
                'Name': 'Foo',
                'Boolean': False,
                'Number': Uint8(42),
                'Ref': CIMInstanceName('CIM_Bar'),
            }),
            obj2=CIMInstanceName('CIM_Foo', keybindings={
                'Name': 'Foo',
                'Boolean': False,
                'Number': Uint8(42),
                'Ref': CIMInstanceName('CIM_Bar'),
            }),
            exp_hash_equal=True,
        ),
        None, None, True
    ),
    (
        "Keybinding with different types (on input!): int / Uint8",
        dict(
            obj1=CIMInstanceName('CIM_Foo', keybindings={'Foo': 42}),
            obj2=CIMInstanceName('CIM_Foo', keybindings={'Foo': Uint8(42)}),
            exp_hash_equal=True,
        ),
        None, None, True
    ),
    (
        "Keybinding with different types: bool True / string 'TRUE'",
        dict(
            obj1=CIMInstanceName('CIM_Foo', keybindings={'Foo': True}),
            obj2=CIMInstanceName('CIM_Foo', keybindings={'Foo': 'TRUE'}),
            exp_hash_equal=False,
        ),
        None, None, True
    ),
    (
        "Keybinding with different types: bool False / string 'FALSE'",
        dict(
            obj1=CIMInstanceName('CIM_Foo', keybindings={'Foo': False}),
            obj2=CIMInstanceName('CIM_Foo', keybindings={'Foo': 'FALSE'}),
            exp_hash_equal=False,
        ),
        None, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    testcases_CIMInstanceName_hash)
@pytest_extensions.test_function
def test_CIMInstanceName_hash(
        desc, kwargs, exp_exc_types, exp_warn_types, condition):
    """
    All test cases for CIMInstanceName.__hash__().
    """

    obj1 = kwargs['obj1']
    obj2 = kwargs['obj2']

    # Double check they are different objects
    assert id(obj1) != id(obj2)

    # The code to be tested
    hash1 = hash(obj1)
    hash2 = hash(obj2)

    exp_hash_equal = kwargs['exp_hash_equal']

    assert (hash1 == hash2) == exp_hash_equal


class Test_CIMInstanceName_repr(object):
    # pylint: disable=too-few-public-methods
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
                search_str = 'u?[\'"]%s[\'"], ' % key
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
                                       'Number': Uint8(42),
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
    # pylint: disable=too-few-public-methods
    """
    Test CIMInstanceName.from_wbem_uri().
    """

    testcases = [
        # Testcases for CIMInstanceName.from_wbem_uri().
        # Each testcase has these items:
        # * desc: Short testcase description.
        # * uri: WBEM URI string to be tested.
        # * exp_result: Dict of all expected attributes of resulting object,
        #     if expected to succeed. Exception type, if expected to fail.
        # * exp_warn_type: Expected warning type.
        #     None, if no warning expected.
        # * condition: Condition for testcase to run.
        (
            "all components, normal case",
            'https://10.11.12.13:5989/root/cimv2:CIM_Foo.k1="v1"',
            dict(
                classname=u'CIM_Foo',
                keybindings=NocaseDict(k1=u'v1'),
                namespace=u'root/cimv2',
                host=u'10.11.12.13:5989'),
            None, CHECK_0_12_0
        ),
        (
            "no authority",
            'https:/root/cimv2:CIM_Foo.k1="v1"',
            dict(
                classname=u'CIM_Foo',
                keybindings=NocaseDict(k1=u'v1'),
                namespace=u'root/cimv2',
                host=None),
            None, CHECK_0_12_0
        ),
        (
            "authority with user:password",
            'https://jdd:test@10.11.12.13:5989/root/cimv2:CIM_Foo.k1="v1"',
            dict(
                classname=u'CIM_Foo',
                keybindings=NocaseDict(k1=u'v1'),
                namespace=u'root/cimv2',
                host=u'jdd:test@10.11.12.13:5989'),
            None, CHECK_0_12_0
        ),
        (
            "authority with user (no password)",
            'https://jdd@10.11.12.13:5989/root/cimv2:CIM_Foo.k1="v1"',
            dict(
                classname=u'CIM_Foo',
                keybindings=NocaseDict(k1=u'v1'),
                namespace=u'root/cimv2',
                host=u'jdd@10.11.12.13:5989'),
            None, CHECK_0_12_0
        ),
        (
            "authority without port",
            'https://10.11.12.13/root/cimv2:CIM_Foo.k1="v1"',
            dict(
                classname=u'CIM_Foo',
                keybindings=NocaseDict(k1=u'v1'),
                namespace=u'root/cimv2',
                host=u'10.11.12.13'),
            None, CHECK_0_12_0
        ),
        (
            "authority with IPv6 address",
            'https://[10:11:12:13]/root/cimv2:CIM_Foo.k1="v1"',
            dict(
                classname=u'CIM_Foo',
                keybindings=NocaseDict(k1=u'v1'),
                namespace=u'root/cimv2',
                host=u'[10:11:12:13]'),
            None, CHECK_0_12_0
        ),
        (
            "authority with IPv6 address and port",
            'https://[10:11:12:13]:5989/root/cimv2:CIM_Foo.k1="v1"',
            dict(
                classname=u'CIM_Foo',
                keybindings=NocaseDict(k1=u'v1'),
                namespace=u'root/cimv2',
                host=u'[10:11:12:13]:5989'),
            None, CHECK_0_12_0
        ),
        (
            "no namespace type",
            '//10.11.12.13:5989/root/cimv2:CIM_Foo.k1="v1"',
            dict(
                classname=u'CIM_Foo',
                keybindings=NocaseDict(k1=u'v1'),
                namespace=u'root/cimv2',
                host=u'10.11.12.13:5989'),
            None, CHECK_0_12_0
        ),
        (
            "namespace type http",
            'http://10.11.12.13:5989/root/cimv2:CIM_Foo.k1="v1"',
            dict(
                classname=u'CIM_Foo',
                keybindings=NocaseDict(k1=u'v1'),
                namespace=u'root/cimv2',
                host=u'10.11.12.13:5989'),
            None, CHECK_0_12_0
        ),
        (
            "namespace type upper case HTTP",
            'HTTP://10.11.12.13:5989/root/cimv2:CIM_Foo.k1="v1"',
            dict(
                classname=u'CIM_Foo',
                keybindings=NocaseDict(k1=u'v1'),
                namespace=u'root/cimv2',
                host=u'10.11.12.13:5989'),
            None, CHECK_0_12_0
        ),
        (
            "namespace type mixed case HttpS",
            'HttpS://10.11.12.13:5989/root/cimv2:CIM_Foo.k1="v1"',
            dict(
                classname=u'CIM_Foo',
                keybindings=NocaseDict(k1=u'v1'),
                namespace=u'root/cimv2',
                host=u'10.11.12.13:5989'),
            None, CHECK_0_12_0
        ),
        (
            "namespace type cimxml-wbem",
            'cimxml-wbem://10.11.12.13:5989/root/cimv2:CIM_Foo.k1="v1"',
            dict(
                classname=u'CIM_Foo',
                keybindings=NocaseDict(k1=u'v1'),
                namespace=u'root/cimv2',
                host=u'10.11.12.13:5989'),
            None, CHECK_0_12_0
        ),
        (
            "namespace type cimxml-wbems",
            'cimxml-wbems://10.11.12.13:5989/root/cimv2:CIM_Foo.k1="v1"',
            dict(
                classname=u'CIM_Foo',
                keybindings=NocaseDict(k1=u'v1'),
                namespace=u'root/cimv2',
                host=u'10.11.12.13:5989'),
            None, CHECK_0_12_0
        ),
        (
            "unknown namespace type",
            'xyz://10.11.12.13:5989/root/cimv2:CIM_Foo.k1="v1"',
            dict(
                classname=u'CIM_Foo',
                keybindings=NocaseDict(k1=u'v1'),
                namespace=u'root/cimv2',
                host=u'10.11.12.13:5989'),
            UserWarning, CHECK_0_12_0
        ),
        (
            "local WBEM URI (with missing initial slash)",
            'root/cimv2:CIM_Foo.k1="v1"',
            dict(
                classname=u'CIM_Foo',
                keybindings=NocaseDict(k1=u'v1'),
                namespace=u'root/cimv2',
                host=None),
            None, CHECK_0_12_0
        ),
        (
            "local WBEM URI with only class name",
            '/:CIM_Foo.k1="v1"',
            dict(
                classname=u'CIM_Foo',
                keybindings=NocaseDict(k1=u'v1'),
                namespace=None,
                host=None),
            None, CHECK_0_12_0
        ),
        (
            "local WBEM URI with only class name (with missing initial slash)",
            ':CIM_Foo.k1="v1"',
            dict(
                classname=u'CIM_Foo',
                keybindings=NocaseDict(k1=u'v1'),
                namespace=None,
                host=None),
            None, CHECK_0_12_0
        ),
        (
            "local WBEM URI with namespace that has only one component",
            '/root:CIM_Foo.k1="v1"',
            dict(
                classname=u'CIM_Foo',
                keybindings=NocaseDict(k1=u'v1'),
                namespace=u'root',
                host=None),
            None, CHECK_0_12_0
        ),
        (
            "local WBEM URI with namespace that has three components",
            '/root/cimv2/test:CIM_Foo.k1="v1"',
            dict(
                classname=u'CIM_Foo',
                keybindings=NocaseDict(k1=u'v1'),
                namespace=u'root/cimv2/test',
                host=None),
            None, CHECK_0_12_0
        ),
        (
            "multiple keys (bool) - in alphabetical order",
            '/n:C.k1=false,k2=true,k3=False,k4=True,k5=FALSE,k6=TRUE',
            dict(
                classname=u'C',
                keybindings=NocaseDict([('k1', False), ('k2', True),
                                        ('k3', False), ('k4', True),
                                        ('k5', False), ('k6', True)]),
                namespace=u'n',
                host=None),
            None, CHECK_0_12_0
        ),
        (
            "multiple keys (bool) - in non-alphabetical order",
            '/n:C.k1=false,k3=False,k2=true,k4=True,k5=FALSE,k6=TRUE',
            dict(
                classname=u'C',
                keybindings=NocaseDict([('k1', False), ('k3', False),
                                        ('k2', True), ('k4', True),
                                        ('k5', False), ('k6', True)]),
                namespace=u'n',
                host=None),
            None, CHECK_0_12_0
        ),
        (
            "multiple keys (int) - in non-alphabetical order",
            '/n:C.k1=0,k2=-1,k3=-32769,k4=42,k5=+42,'
            'kmax32=4294967295,'
            'kmin32=-4294967296,'
            'kmax64=9223372036854775807,'
            'kmin64=-9223372036854775808,'
            'klong=9223372036854775808',
            dict(
                classname=u'C',
                keybindings=NocaseDict([('k1', 0), ('k2', -1), ('k3', -32769),
                                        ('k4', 42), ('k5', 42),
                                        ('kmax32', 4294967295),
                                        ('kmin32', -4294967296),
                                        ('kmax64', 9223372036854775807),
                                        ('kmin64', -9223372036854775808),
                                        ('klong', 9223372036854775808)]),
                namespace=u'n',
                host=None),
            None, CHECK_0_12_0
        ),
        (
            "int key with invalid decimal digit U+0661 (ARABIC-INDIC ONE)",
            u'/n:C.k1=\u0661',
            ValueError,
            None, CHECK_0_12_0
        ),
        (
            "int key with invalid decimal digit U+1D7CF (MATHEM. BOLD ONE)",
            u'/n:C.k1=\U0001d7cf',
            ValueError,
            None, CHECK_0_12_0
        ),
        (
            "int key with invalid decimal digit U+2081 (SUBSCRIPT ONE)",
            u'/n:C.k1=\u2081',
            ValueError,
            None, CHECK_0_12_0
        ),
        (
            "int key with invalid decimal digit U+00B9 (SUPERSCRIPT ONE)",
            u'/n:C.k1=\u00b9',
            ValueError,
            None, CHECK_0_12_0
        ),
        (
            "int key with invalid non-decimal digit U+10A44 (KHAROSHTHI TEN)",
            u'/n:C.k1=\U00010a44',
            ValueError,
            None, CHECK_0_12_0
        ),
        (
            "multiple float keys - in non-alphabetical order",
            '/n:C.k1=.0,k2=-0.1,k3=+.1,k4=+31.4E-1,k5=.4e1,'
            'kmax32=3.402823466E38,'
            'kmin32=1.175494351E-38,'
            'kmax64=1.7976931348623157E308,'
            'kmin64=4.9E-324',
            dict(
                classname=u'C',
                keybindings=NocaseDict([('k1', 0.0), ('k2', -0.1), ('k3', 0.1),
                                        ('k4', 31.4E-1), ('k5', 0.4E1),
                                        ('kmax32', 3.402823466E38),
                                        ('kmin32', 1.175494351E-38),
                                        ('kmax64', 1.7976931348623157E308),
                                        ('kmin64', 4.9E-324)]),
                namespace=u'n',
                host=None),
            None, CHECK_0_12_0
        ),
        (
            "invalid float key 1. (not allowed in realValue)",
            '/n:C.k1=1.',
            ValueError,
            None, CHECK_0_12_0
        ),
        (
            "float key with special value INF (allowed by extension)",
            '/n:C.k1=INF',
            dict(
                classname=u'C',
                keybindings=NocaseDict(k1=float('inf')),
                namespace=u'n',
                host=None),
            None, CHECK_0_12_0
        ),
        (
            "float key with special value -INF (allowed by extension)",
            '/n:C.k1=-INF',
            dict(
                classname=u'C',
                keybindings=NocaseDict(k1=float('-inf')),
                namespace=u'n',
                host=None),
            None, CHECK_0_12_0
        ),
        (
            "float key with special value NAN (allowed by extension)",
            '/n:C.k1=NAN',
            dict(
                classname=u'C',
                keybindings=NocaseDict(k1=float('nan')),
                namespace=u'n',
                host=None),
            None, False  # float('nan') does not compare equal to itself
        ),
        (
            "multiple string keys - in alphabetical order",
            r'/n:C.k1="",k2="a",k3="42",k4="\"",k5="\\",k6="\\\"",k7="\'"',
            dict(
                classname=u'C',
                keybindings=NocaseDict([('k1', ''), ('k2', 'a'), ('k3', '42'),
                                        ('k4', '"'), ('k5', '\\'),
                                        ('k6', '\\"'), ('k7', "'")]),
                namespace=u'n',
                host=None),
            None, CHECK_0_12_0
        ),
        (
            "string key with keybindings syntax in its value",
            r'/n:C.k1="k2=42,k3=3"',
            dict(
                classname=u'C',
                keybindings=NocaseDict(k1='k2=42,k3=3'),
                namespace=u'n',
                host=None),
            None, CHECK_0_12_0
        ),
        (
            "multiple char16 keys - in non-alphabetical order",
            "/n:C.k1='a',k3='\"',k2='1',k4='\\'',k5='\\\\'",
            dict(
                classname=u'C',
                keybindings=NocaseDict([('k1', 'a'), ('k3', '"'), ('k2', '1'),
                                        ('k4', "'"), ('k5', '\\')]),
                namespace=u'n',
                host=None),
            None, CHECK_0_12_0
        ),
        (
            "empty char16 key",
            "/n:C.k1=''",
            ValueError,
            None, CHECK_0_12_0
        ),
        (
            "invalid char16 key with two characters",
            "/n:C.k1='ab'",
            ValueError,
            None, CHECK_0_12_0
        ),
        (
            "datetime key for point in time (in quotes)",
            '/n:C.k1="19980125133015.123456-300"',
            dict(
                classname=u'C',
                keybindings=NocaseDict([
                    ('k1', CIMDateTime('19980125133015.123456-300')),
                ]),
                namespace=u'n',
                host=None),
            None, CHECK_0_12_0
        ),
        (
            "datetime key for interval (in quotes)",
            '/n:C.k1="12345678133015.123456:000"',
            dict(
                classname=u'C',
                keybindings=NocaseDict([
                    ('k1', CIMDateTime('12345678133015.123456:000')),
                ]),
                namespace=u'n',
                host=None),
            None, CHECK_0_12_0
        ),
        (
            "datetime key for point in time (no quotes)",
            '/n:C.k1=19980125133015.123456-300',
            dict(
                classname=u'C',
                keybindings=NocaseDict([
                    ('k1', CIMDateTime('19980125133015.123456-300')),
                ]),
                namespace=u'n',
                host=None),
            UserWarning, CHECK_0_12_0
        ),
        (
            "datetime key for interval (no quotes)",
            '/n:C.k1=12345678133015.123456:000',
            dict(
                classname=u'C',
                keybindings=NocaseDict([
                    ('k1', CIMDateTime('12345678133015.123456:000')),
                ]),
                namespace=u'n',
                host=None),
            UserWarning, CHECK_0_12_0
        ),
        (
            "reference key that has an int key (normal association)",
            '/n1:C1.k1="/n2:C2.k2=1"',
            dict(
                classname=u'C1',
                keybindings=NocaseDict([
                    ('k1', CIMInstanceName(
                        classname='C2',
                        keybindings=NocaseDict([
                            ('k2', 1),
                        ]),
                        namespace='n2')),
                ]),
                namespace=u'n1',
                host=None),
            None, CHECK_0_12_0
        ),
        (
            "reference key that has a string key (normal association)",
            r'/n1:C1.k1="/n2:C2.k2=\"v2\""',
            dict(
                classname=u'C1',
                keybindings=NocaseDict([
                    ('k1', CIMInstanceName(
                        classname='C2',
                        keybindings=NocaseDict([
                            ('k2', 'v2'),
                        ]),
                        namespace='n2')),
                ]),
                namespace=u'n1',
                host=None),
            None, CHECK_0_12_0
        ),
        (
            "double nested reference to int key (association to association)",
            r'/n1:C1.k1="/n2:C2.k2=\"/n3:C3.k3=3\""',
            dict(
                classname=u'C1',
                keybindings=NocaseDict([
                    ('k1', CIMInstanceName(
                        classname='C2',
                        keybindings=NocaseDict([
                            ('k2', CIMInstanceName(
                                classname='C3',
                                keybindings=NocaseDict([
                                    ('k3', 3),
                                ]),
                                namespace='n3')),
                        ]),
                        namespace='n2')),
                ]),
                namespace=u'n1',
                host=None),
            None, CHECK_0_12_0
        ),
        (
            "double nested reference to string key (association to "
            "association)",
            r'/n1:C1.k1="/n2:C2.k2=\"/n3:C3.k3=\\\"v3\\\"\""',
            dict(
                classname=u'C1',
                keybindings=NocaseDict([
                    ('k1', CIMInstanceName(
                        classname='C2',
                        keybindings=NocaseDict([
                            ('k2', CIMInstanceName(
                                classname='C3',
                                keybindings=NocaseDict([
                                    ('k3', 'v3'),
                                ]),
                                namespace='n3')),
                        ]),
                        namespace='n2')),
                ]),
                namespace=u'n1',
                host=None),
            None, CHECK_0_12_0
        ),
        (
            "missing delimiter / before authority",
            'https:/10.11.12.13/cimv2:CIM_Foo.k1="v1"',
            ValueError,
            None, CHECK_0_12_0
        ),
        (
            "invalid char ; in authority",
            'https://10.11.12.13;5989/cimv2:CIM_Foo.k1="v1"',
            ValueError,
            None, CHECK_0_12_0
        ),
        (
            "delimiter / before namespace replaced with :",
            'https://10.11.12.13:5989:root:CIM_Foo.k1="v1"',
            ValueError,
            None, CHECK_0_12_0
        ),
        (
            "delimiter : before classname replaced with .",
            'https://10.11.12.13:5989/root.CIM_Foo.k1="v1"',
            ValueError,
            None, CHECK_0_12_0
        ),
        (
            "invalid '/' between namespace and classname",
            'https://10.11.12.13:5989/cimv2/CIM_Foo.k1="v1"',
            ValueError,
            None, CHECK_0_12_0
        ),
        (
            "class name missing",
            'https://10.11.12.13:5989/root/cimv2:k1="v1"',
            ValueError,
            None, CHECK_0_12_0
        ),
        (
            "class path used as instance path",
            'https://10.11.12.13:5989/root:CIM_Foo',
            ValueError,
            None, CHECK_0_12_0
        ),
        (
            "invalid ':' between classname and key k1",
            'https://10.11.12.13:5989/cimv2:CIM_Foo:k1="v1"',
            ValueError,
            None, CHECK_0_12_0
        ),
        (
            "invalid '/' between classname and key k1",
            'https://10.11.12.13:5989/cimv2:CIM_Foo/k1="v1"',
            ValueError,
            None, CHECK_0_12_0
        ),
        (
            "invalid '.' between key k1 and key k2",
            'https://10.11.12.13:5989/cimv2:CIM_Foo.k1="v1".k2="v2"',
            ValueError,
            None, CHECK_0_12_0 and False
        ),
        (
            "invalid ':' between key k1 and key k2",
            'https://10.11.12.13:5989/cimv2:CIM_Foo.k1="v1":k2="v2"',
            ValueError,
            None, CHECK_0_12_0 and False
        ),
        (
            "double quotes missing around string value of key k2",
            'https://10.11.12.13:5989/cimv2:CIM_Foo.k1="v1".k2=v2',
            ValueError,
            None, CHECK_0_12_0 and False
        ),
        (
            "invalid double comma between keybindings",
            'https://10.11.12.13:5989/cimv2:CIM_Foo.k1="v1",,k2=42',
            ValueError,
            None, CHECK_0_12_0
        ),
        (
            "invalid comma after last keybinding",
            'https://10.11.12.13:5989/cimv2:CIM_Foo.k1="v1",k2=42,',
            ValueError,
            None, CHECK_0_12_0
        ),
        (
            "equal sign missing in keyinding",
            'https://10.11.12.13:5989/cimv2:CIM_Foo.k1="v1",k242',
            ValueError,
            None, CHECK_0_12_0
        ),
        (
            "double equal sign in keyinding",
            'https://10.11.12.13:5989/cimv2:CIM_Foo.k1="v1",k2==42',
            ValueError,
            None, CHECK_0_12_0
        ),
    ]

    @pytest.mark.parametrize(
        "desc, uri, exp_result, exp_warn_type, condition",
        testcases)
    def test_CIMInstanceName_from_wbem_uri(
            self, desc, uri, exp_result, exp_warn_type, condition):
        """All test cases for CIMInstanceName.from_wbem_uri()."""

        if not condition:
            pytest.skip("Condition for test case not met")

        if isinstance(exp_result, type) and issubclass(exp_result, Exception):
            # We expect an exception
            exp_exc_type = exp_result
            exp_attrs = None
        else:
            # We expect the code to return
            exp_exc_type = None
            exp_attrs = exp_result

        if condition == 'pdb':
            import pdb
            pdb.set_trace()

        if exp_warn_type:
            with pytest.warns(exp_warn_type) as rec_warnings:
                if exp_exc_type:
                    with pytest.raises(exp_exc_type):

                        # The code to be tested
                        obj = CIMInstanceName.from_wbem_uri(uri)

                else:

                    # The code to be tested
                    obj = CIMInstanceName.from_wbem_uri(uri)

            assert len(rec_warnings) == 1

        else:
            if exp_exc_type:
                with pytest.raises(exp_exc_type):

                    # The code to be tested
                    obj = CIMInstanceName.from_wbem_uri(uri)

            else:

                # The code to be tested
                obj = CIMInstanceName.from_wbem_uri(uri)

        if exp_attrs:

            exp_classname = exp_attrs['classname']
            exp_keybindings = exp_attrs['keybindings']
            exp_namespace = exp_attrs['namespace']
            exp_host = exp_attrs['host']

            assert isinstance(obj, CIMInstanceName)

            assert obj.classname == exp_classname
            assert isinstance(obj.classname, type(exp_classname))

            assert obj.keybindings == exp_keybindings
            assert isinstance(obj.keybindings, type(exp_keybindings))

            assert obj.namespace == exp_namespace
            assert isinstance(obj.namespace, type(exp_namespace))

            assert obj.host == exp_host
            assert isinstance(obj.host, type(exp_host))


class Test_CIMInstanceName_from_instance(object):
    # pylint: disable=too-few-public-methods
    """
    Test the static method that creates CIMInstance name from the combination
    of a CIMClass and CIMInstance.
    """
    testcases = [
        # Testcases for CIMInstanceName.from_instance().
        # Each testcase has these items:
        # * desc: Short testcase description.
        # * cls_kwargs: Dict with Attributes from which test class is
        #   constructed
        # * inst_kwargs: Dict with Attributes from which test inst is
        #   constructed
        # * exp_result: Dict of all expected attributes of resulting
        #     CIMInstanceName without host and namespace if expected to suceed.
        #     Exception type, if expected to fail.
        # * strict: Value of strict attribute on from_instance call
        # * condition: Condition for testcase to run.
        (
            "Verify class with single key type string works",
            dict(
                classname='CIM_Foo',
                properties=[
                    CIMProperty('P1', None, type='string',
                                qualifiers={'Key': CIMQualifier('Key',
                                                                value=True)}),
                    CIMProperty('P2', value='Cheese'),
                ]
            ),
            dict(
                classname='CIM_Foo',
                properties=[
                    CIMProperty('P1', value='Ham'),
                    CIMProperty('P2', value='Cheese'),
                ]
            ),
            dict(
                classname='CIM_Foo',
                keybindings={'P1': 'Ham'}
            ),
            # strict, condition
            True, True,
        ),
        (
            "Verify class with two keys type string works",
            dict(
                classname='CIM_Foo',
                properties=[
                    CIMProperty('P1', None, type='string',
                                qualifiers={'Key': CIMQualifier('Key',
                                                                value=True)}),
                    CIMProperty('P2', None, type='string',
                                qualifiers={'Key': CIMQualifier('Key',
                                                                value=True)}),
                ]
            ),
            dict(
                classname='CIM_Foo',
                properties=[
                    CIMProperty('P1', value='Ham'),
                    CIMProperty('P2', value='Cheese'),
                ]
            ),
            dict(
                classname='CIM_Foo',
                keybindings={'P1': 'Ham', 'P2': 'Cheese'}
            ),
            # strict, condition
            True, True,
        ),
        (
            "Verify class with single key type strict=true, no key in inst"
            ' fails.',
            dict(
                classname='CIM_Foo',
                properties=[
                    CIMProperty('P1', None, type='string',
                                qualifiers={'Key': CIMQualifier('Key',
                                                                value=True)}),
                    CIMProperty('P2', value='Cheese'),
                ]
            ),
            dict(
                classname='CIM_Foo',
                properties=[
                    CIMProperty('P2', value='Cheese'),
                ]
            ),
            ValueError,
            # strict, condition
            True, True,
        ),
        (
            "Verify class strict=False and no key prop in instace passes",
            dict(
                classname='CIM_Foo',
                properties=[
                    CIMProperty('P1', None, type='string',
                                qualifiers={'Key': CIMQualifier('Key',
                                                                value=True)}),
                    CIMProperty('P2', value='Cheese'),
                ]
            ),
            dict(
                classname='CIM_Foo',
                properties=[
                    CIMProperty('P2', value='Cheese'),
                ]
            ),
            dict(
                classname='CIM_Foo',
                keybindings={'P1': None}
            ),
            # strict, condition
            False, True,
        ),
        (
            "Verify class with two keys not in instance strict=false works",
            dict(
                classname='CIM_Foo',
                properties=[
                    CIMProperty('P1', None, type='string',
                                qualifiers={'Key': CIMQualifier('Key',
                                                                value=True)}),
                    CIMProperty('P2', 'DEFAULT', type='string',
                                qualifiers={'Key': CIMQualifier('Key',
                                                                value=True)}),
                ]
            ),
            dict(
                classname='CIM_Foo',
                properties=[
                ]
            ),
            dict(
                classname='CIM_Foo',
                keybindings={'P1': None, 'P2': 'DEFAULT'}
            ),
            # strict,condition
            False, True,
        ),
        (
            "Verify class with reference properies as keys",
            dict(
                classname='CIM_Ref',
                properties=[
                    CIMProperty('R1', None, type='reference',
                                qualifiers={'Key': CIMQualifier('Key',
                                                                value=True)}),
                    CIMProperty('R2', type='string', value='Cheese'),
                ]
            ),
            dict(
                classname='CIM_Ref',
                properties=[
                    CIMProperty('R1', value=CIMInstanceName('CIM_X',
                                                            {'x': "X"})),
                ]
            ),
            dict(
                classname='CIM_Ref',
                keybindings={'R1': CIMInstanceName('CIM_X', {'x': "X"})}
            ),
            # strict, condition
            True, True,
        ),
    ]

    @pytest.mark.parametrize(
        # * ns: Namespace for CIMInstanceName on from_instance call or None
        # * host: Host for CIMInstanceName on from_instance call or None
        'ns, host', [
            [None, None],
            ['root/blah', None],
            [None, 'Fred'],
            ['root/blah', 'Fred'],
        ]
    )
    @pytest.mark.parametrize(
        "desc, cls_kwargs, inst_kwargs, exp_result, strict, condition",
        testcases)
    def test_CIMInstanceName_from_instance(
            self, desc, cls_kwargs, inst_kwargs, exp_result, strict, ns, host,
            condition):
        """All test cases for CIMInstanceName.from_instance."""

        if not condition:
            pytest.skip("Condition for test case not met")

        if condition == 'pdb':
            import pdb
            pdb.set_trace()

        cls = CIMClass(**cls_kwargs)

        inst = CIMInstance(**inst_kwargs)

        if isinstance(exp_result, dict):
            exp_inst_name = CIMInstanceName(**exp_result)
            # Add correct expected instance name namespace and host attributes
            exp_inst_name.namespace = ns
            exp_inst_name.host = host

            # Create the test CIMInstanceName with method being tested
            act_name = CIMInstanceName.from_instance(cls, inst,
                                                     namespace=ns,
                                                     host=host,
                                                     strict=strict)

            assert isinstance(act_name, CIMInstanceName)
            assert exp_inst_name == act_name

        else:
            with pytest.raises(exp_result):

                CIMInstanceName.from_instance(cls, inst,
                                              namespace=ns,
                                              host=host,
                                              strict=strict)


class Test_CIMInstanceName_to_wbem_uri_str(object):
    # pylint: disable=too-few-public-methods
    """
    Test CIMInstanceName.to_wbem_uri() and .__str__().
    """

    func_name = [
        # Fixture for function to be tested
        'to_wbem_uri', '__str__'
    ]

    testcases = [
        # Testcases for CIMInstanceName.to_wbem_uri().
        # Each testcase has these items:
        # * desc: Short testcase description.
        # * attrs: Dict of input attributes for the CIMInstanceName object
        #     to be tested.
        # * format: Format for to_wbem_uri(): one of 'standard', 'cimobject',
        #     'historical'.
        # * exp_result: Expected WBEM URI string, if expected to succeed.
        #     Exception type, if expected to fail.
        # * exp_warn_type: Expected warning type.
        #     None, if no warning expected.
        # * condition: Condition for testcase to run.
        (
            "all components, standard format",
            dict(
                classname=u'CIM_Foo',
                keybindings=NocaseDict(k1=u'v1'),
                namespace=u'root/cimv2',
                host=u'10.11.12.13:5989'),
            'standard',
            '//10.11.12.13:5989/root/cimv2:CIM_Foo.k1="v1"',
            None, CHECK_0_12_0
        ),
        (
            "all components, cimobject format",
            dict(
                classname=u'CIM_Foo',
                keybindings=NocaseDict(k1=u'v1'),
                namespace=u'root/cimv2',
                host=u'10.11.12.13:5989'),
            'cimobject',
            '//10.11.12.13:5989/root/cimv2:CIM_Foo.k1="v1"',
            None, CHECK_0_12_0
        ),
        (
            "all components, historical format",
            dict(
                classname=u'CIM_Foo',
                keybindings=NocaseDict(k1=u'v1'),
                namespace=u'root/cimv2',
                host=u'10.11.12.13:5989'),
            'historical',
            '//10.11.12.13:5989/root/cimv2:CIM_Foo.k1="v1"',
            None, CHECK_0_12_0
        ),
        (
            "no authority, standard format",
            dict(
                classname=u'CIM_Foo',
                keybindings=NocaseDict(k1=u'v1'),
                namespace=u'root/cimv2',
                host=None),
            'standard',
            '/root/cimv2:CIM_Foo.k1="v1"',
            None, CHECK_0_12_0
        ),
        (
            "no authority, cimobject format",
            dict(
                classname=u'CIM_Foo',
                keybindings=NocaseDict(k1=u'v1'),
                namespace=u'root/cimv2',
                host=None),
            'cimobject',
            'root/cimv2:CIM_Foo.k1="v1"',
            None, CHECK_0_12_0
        ),
        (
            "no authority, historical format",
            dict(
                classname=u'CIM_Foo',
                keybindings=NocaseDict(k1=u'v1'),
                namespace=u'root/cimv2',
                host=None),
            'historical',
            'root/cimv2:CIM_Foo.k1="v1"',
            None, CHECK_0_12_0
        ),
        (
            "authority with user:password",
            dict(
                classname=u'CIM_Foo',
                keybindings=NocaseDict(k1=u'v1'),
                namespace=u'root/cimv2',
                host=u'jdd:test@10.11.12.13:5989'),
            'standard',
            '//jdd:test@10.11.12.13:5989/root/cimv2:CIM_Foo.k1="v1"',
            None, CHECK_0_12_0
        ),
        (
            "authority with user (no password)",
            dict(
                classname=u'CIM_Foo',
                keybindings=NocaseDict(k1=u'v1'),
                namespace=u'root/cimv2',
                host=u'jdd@10.11.12.13:5989'),
            'standard',
            '//jdd@10.11.12.13:5989/root/cimv2:CIM_Foo.k1="v1"',
            None, CHECK_0_12_0
        ),
        (
            "authority without port",
            dict(
                classname=u'CIM_Foo',
                keybindings=NocaseDict(k1=u'v1'),
                namespace=u'root/cimv2',
                host=u'10.11.12.13'),
            'standard',
            '//10.11.12.13/root/cimv2:CIM_Foo.k1="v1"',
            None, CHECK_0_12_0
        ),
        (
            "authority with IPv6 address",
            dict(
                classname=u'CIM_Foo',
                keybindings=NocaseDict(k1=u'v1'),
                namespace=u'root/cimv2',
                host=u'[10:11:12:13]'),
            'standard',
            '//[10:11:12:13]/root/cimv2:CIM_Foo.k1="v1"',
            None, CHECK_0_12_0
        ),
        (
            "authority with IPv6 address and port",
            dict(
                classname=u'CIM_Foo',
                keybindings=NocaseDict(k1=u'v1'),
                namespace=u'root/cimv2',
                host=u'[10:11:12:13]:5989'),
            'standard',
            '//[10:11:12:13]:5989/root/cimv2:CIM_Foo.k1="v1"',
            None, CHECK_0_12_0
        ),
        (
            "local WBEM URI",
            dict(
                classname=u'CIM_Foo',
                keybindings=NocaseDict(k1=u'v1'),
                namespace=u'root/cimv2',
                host=None),
            'standard',
            '/root/cimv2:CIM_Foo.k1="v1"',
            None, CHECK_0_12_0
        ),
        (
            "local WBEM URI with only class name, standard format",
            dict(
                classname=u'CIM_Foo',
                keybindings=NocaseDict(k1=u'v1'),
                namespace=None,
                host=None),
            'standard',
            '/:CIM_Foo.k1="v1"',
            None, CHECK_0_12_0
        ),
        (
            "local WBEM URI with only class name, cimobject format",
            dict(
                classname=u'CIM_Foo',
                keybindings=NocaseDict(k1=u'v1'),
                namespace=None,
                host=None),
            'cimobject',
            ':CIM_Foo.k1="v1"',
            None, CHECK_0_12_0
        ),
        (
            "local WBEM URI with only class name, historical format",
            dict(
                classname=u'CIM_Foo',
                keybindings=NocaseDict(k1=u'v1'),
                namespace=None,
                host=None),
            'historical',
            'CIM_Foo.k1="v1"',
            None, CHECK_0_12_0
        ),
        (
            "local WBEM URI with namespace that has only one component",
            dict(
                classname=u'CIM_Foo',
                keybindings=NocaseDict(k1=u'v1'),
                namespace=u'root',
                host=None),
            'standard',
            '/root:CIM_Foo.k1="v1"',
            None, CHECK_0_12_0
        ),
        (
            "local WBEM URI with namespace that has three components",
            dict(
                classname=u'CIM_Foo',
                keybindings=NocaseDict(k1=u'v1'),
                namespace=u'root/cimv2/test',
                host=None),
            'standard',
            '/root/cimv2/test:CIM_Foo.k1="v1"',
            None, CHECK_0_12_0
        ),
        (
            "multiple keys (bool) - created in alphabetical order",
            dict(
                classname=u'C',
                keybindings=NocaseDict([('k1', False), ('k2', True)]),
                namespace=u'n',
                host=None),
            'standard',
            '/n:C.k1=FALSE,k2=TRUE',
            None, CHECK_0_12_0
        ),
        (
            "multiple keys (bool) - created in non-alphabetical order",
            dict(
                classname=u'C',
                keybindings=NocaseDict([('k2', True), ('k1', False)]),
                namespace=u'n',
                host=None),
            'standard',
            '/n:C.k2=TRUE,k1=FALSE',
            None, CHECK_0_12_0
        ),
        (
            "multiple keys (int) - created in non-alphabetical order",
            dict(
                classname=u'C',
                keybindings=NocaseDict([('k1', 0), ('k2', -1), ('k3', -32769),
                                        ('k4', 42), ('k5', 42),
                                        ('kmax32', 4294967295),
                                        ('kmin32', -4294967296),
                                        ('kmax64', 9223372036854775807),
                                        ('kmin64', -9223372036854775808),
                                        ('klong', 9223372036854775808)]),
                namespace=u'n',
                host=None),
            'standard',
            '/n:C.k1=0,k2=-1,k3=-32769,k4=42,k5=42,'
            'kmax32=4294967295,'
            'kmin32=-4294967296,'
            'kmax64=9223372036854775807,'
            'kmin64=-9223372036854775808,'
            'klong=9223372036854775808',
            None, CHECK_0_12_0
        ),
        (
            "multiple float keys - created in non-alphabetical order",
            dict(
                classname=u'C',
                keybindings=NocaseDict([('k1', 0.0), ('k2', -0.1), ('k3', 0.1),
                                        ('k4', 31.4E-1), ('k5', 0.4E1),
                                        ('kmax32', 3.402823466E38),
                                        ('kmin32', 1.175494351E-38),
                                        ('kmax64', 1.7976931348623157E308),
                                        ('kmin64', 2.2250738585072014E-308)]),
                namespace=u'n',
                host=None),
            'standard',
            '/n:C.k1=0.0,k2=-0.1,k3=0.1,k4=3.14,k5=4.0,'
            'kmax32=3.402823466e+38,'
            'kmin32=1.175494351e-38,'
            'kmax64=1.7976931348623157e+308,'
            'kmin64=2.2250738585072014e-308',
            None, CHECK_0_12_0 and sys.version_info[0:2] >= (2, 7)
        ),
        (
            "float key with special value INF (allowed by extension)",
            dict(
                classname=u'C',
                keybindings=NocaseDict(k1=float('inf')),
                namespace=u'n',
                host=None),
            'standard',
            '/n:C.k1=inf',
            None, CHECK_0_12_0
        ),
        (
            "float key with special value -INF (allowed by extension)",
            dict(
                classname=u'C',
                keybindings=NocaseDict(k1=float('-inf')),
                namespace=u'n',
                host=None),
            'standard',
            '/n:C.k1=-inf',
            None, CHECK_0_12_0
        ),
        (
            "float key with special value NAN (allowed by extension)",
            dict(
                classname=u'C',
                keybindings=NocaseDict(k1=float('nan')),
                namespace=u'n',
                host=None),
            'standard',
            '/n:C.k1=nan',
            None, False  # float('nan') does not compare equal to itself
        ),
        (
            "multiple string keys - created in alphabetical order",
            dict(
                classname=u'C',
                keybindings=NocaseDict([('k1', ''), ('k2', 'a'), ('k3', '42'),
                                        ('k4', '"'), ('k5', '\\'),
                                        ('k6', '\\"'), ('k7', "'")]),
                namespace=u'n',
                host=None),
            'standard',
            '/n:C.k1="",k2="a",k3="42",k4="\\\x22",'
            'k5="\\\\",k6="\\\\\\\x22",k7="\x27"',
            None, CHECK_0_12_0
        ),
        (
            "string key with keybindings syntax in its value",
            dict(
                classname=u'C',
                keybindings=NocaseDict(k1='k2=42,k3=3'),
                namespace=u'n',
                host=None),
            'standard',
            r'/n:C.k1="k2=42,k3=3"',
            None, CHECK_0_12_0
        ),
        (
            "multiple char16 keys - created in non-alphabetical order",
            dict(
                classname=u'C',
                keybindings=NocaseDict([('k1', 'a'), ('k3', '"'), ('k2', '1'),
                                        ('k4', "'"), ('k5', '\\')]),
                namespace=u'n',
                host=None),
            'standard',
            '/n:C.k1="a",k3="\\"",k2="1",k4="\'",k5="\\\\"',
            None, CHECK_0_12_0
        ),
        (
            "datetime key for point in time (in quotes)",
            dict(
                classname=u'C',
                keybindings=[
                    ('k1', CIMDateTime('19980125133015.123456-300')),
                ],
                namespace=u'n',
                host=None),
            'standard',
            '/n:C.k1="19980125133015.123456-300"',
            None, CHECK_0_12_0
        ),
        (
            "datetime key for interval (in quotes)",
            dict(
                classname=u'C',
                keybindings=[
                    ('k1', CIMDateTime('12345678133015.123456:000')),
                ],
                namespace=u'n',
                host=None),
            'standard',
            '/n:C.k1="12345678133015.123456:000"',
            None, CHECK_0_12_0
        ),
        (
            "reference key that has an int key (normal association)",
            dict(
                classname=u'C1',
                keybindings=[
                    ('k1', CIMInstanceName(
                        classname='C2',
                        keybindings=[
                            ('k2', 1),
                        ],
                        namespace='n2')),
                ],
                namespace=u'n1',
                host=None),
            'standard',
            '/n1:C1.k1="/n2:C2.k2=1"',
            None, CHECK_0_12_0
        ),
        (
            "reference key that has a string key (normal association)",
            dict(
                classname=u'C1',
                keybindings=[
                    ('k1', CIMInstanceName(
                        classname='C2',
                        keybindings=[
                            ('k2', 'v2'),
                        ],
                        namespace='n2')),
                ],
                namespace=u'n1',
                host=None),
            'standard',
            r'/n1:C1.k1="/n2:C2.k2=\"v2\""',
            None, CHECK_0_12_0
        ),
        (
            "double nested reference to int key (association to association)",
            dict(
                classname=u'C1',
                keybindings=[
                    ('k1', CIMInstanceName(
                        classname='C2',
                        keybindings=[
                            ('k2', CIMInstanceName(
                                classname='C3',
                                keybindings=[
                                    ('k3', 3),
                                ],
                                namespace='n3')),
                        ],
                        namespace='n2')),
                ],
                namespace=u'n1',
                host=None),
            'standard',
            r'/n1:C1.k1="/n2:C2.k2=\"/n3:C3.k3=3\""',
            None, CHECK_0_12_0
        ),
        (
            "double nested reference to string key (association to "
            "association)",
            dict(
                classname=u'C1',
                keybindings=[
                    ('k1', CIMInstanceName(
                        classname='C2',
                        keybindings=[
                            ('k2', CIMInstanceName(
                                classname='C3',
                                keybindings=[
                                    ('k3', 'v3'),
                                ],
                                namespace='n3')),
                        ],
                        namespace='n2')),
                ],
                namespace=u'n1',
                host=None),
            'standard',
            r'/n1:C1.k1="/n2:C2.k2=\"/n3:C3.k3=\\\"v3\\\"\""',
            None, CHECK_0_12_0
        ),
    ]

    @pytest.mark.parametrize(
        "func_name",
        func_name)
    @pytest.mark.parametrize(
        "desc, attrs, format, exp_result, exp_warn_type, condition",
        testcases)
    def test_CIMInstanceName_to_wbem_uri_str(
            self, desc, attrs, format, exp_result, exp_warn_type, condition,
            func_name):
        """All test cases for CIMInstanceName.to_wbem_uri() and .__str__()."""

        if not condition:
            pytest.skip("Condition for test case not met")

        if isinstance(exp_result, type) and issubclass(exp_result, Exception):
            # We expect an exception
            exp_exc_type = exp_result
            exp_uri = None
        else:
            # We expect the code to return
            exp_exc_type = None
            exp_uri = exp_result

        obj = CIMInstanceName(**attrs)

        func = getattr(obj, func_name)
        if func_name == 'to_wbem_uri':
            func_kwargs = dict(format=format)
        if func_name == '__str__':
            if format != 'historical':
                pytest.skip("Not testing CIMInstanceName.__str__() with "
                            "format: %r" % format)
            func_kwargs = dict()

        if condition == 'pdb':
            import pdb
            pdb.set_trace()

        if exp_warn_type:
            with pytest.warns(exp_warn_type) as rec_warnings:
                if exp_exc_type:
                    with pytest.raises(exp_exc_type):

                        # The code to be tested
                        uri = func(**func_kwargs)

                else:

                    # The code to be tested
                    uri = func(**func_kwargs)

            assert len(rec_warnings) == 1

        else:
            if exp_exc_type:
                with pytest.raises(exp_exc_type):

                    # The code to be tested
                    uri = func(**func_kwargs)

            else:

                # The code to be tested
                uri = func(**func_kwargs)

        if exp_uri:

            assert isinstance(uri, six.text_type)
            assert uri == exp_uri


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

        properties = [CIMProperty('P1', value=True)]
        qualifiers = [CIMQualifier('Q1', value=True)]
        path = CIMInstanceName('CIM_Foo')

        if CHECK_0_12_0:
            with pytest.warns(DeprecationWarning) as rec_warnings:

                # The code to be tested
                obj = CIMInstance(
                    'CIM_Foo',
                    properties,
                    qualifiers,
                    path,
                    ['P1'])  # property_list causes DeprecationWarning

            assert len(rec_warnings) == 1

        else:
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

        # Classname tests
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

        # Properties tests
        (
            "Verify properties order preservation with list of CIMProperty",
            dict(
                classname='CIM_Foo',
                properties=[
                    CIMProperty('P1', value='Ham'),
                    CIMProperty('P2', value='Cheese'),
                ]
            ),
            dict(
                classname=u'CIM_Foo',
                properties=NocaseDict([
                    ('P1', CIMProperty('P1', value='Ham')),
                    ('P2', CIMProperty('P2', value='Cheese')),
                ])
            ),
            None, True
        ),
        (
            "Verify properties order preservation with OrderedDict",
            dict(
                classname='CIM_Foo',
                properties=OrderedDict([
                    ('P1', CIMProperty('P1', value='Ham')),
                    ('P2', CIMProperty('P2', value='Cheese')),
                ])
            ),
            dict(
                classname=u'CIM_Foo',
                properties=NocaseDict([
                    ('P1', CIMProperty('P1', value='Ham')),
                    ('P2', CIMProperty('P2', value='Cheese')),
                ])
            ),
            None, True
        ),
        (
            "Verify properties order preservation with list of tuple(key,val)",
            dict(
                classname='CIM_Foo',
                properties=[
                    ('P1', CIMProperty('P1', value='Ham')),
                    ('P2', CIMProperty('P2', value='Cheese')),
                ]
            ),
            dict(
                classname=u'CIM_Foo',
                properties=NocaseDict([
                    ('P1', CIMProperty('P1', value='Ham')),
                    ('P2', CIMProperty('P2', value='Cheese')),
                ])
            ),
            None, True
        ),
        (
            "Verify property with binary string value",
            dict(
                classname='CIM_Foo',
                properties=dict(P1=b'Ham')),
            dict(
                classname=u'CIM_Foo',
                properties=NocaseDict([
                    CIMProperty('P1', value=u'Ham'),
                ])),
            None, True
        ),
        (
            "Verify property with unicode string value",
            dict(
                classname='CIM_Foo',
                properties=dict(P1=u'H\u00E4m')),  # lower case a umlaut
            dict(
                classname=u'CIM_Foo',
                properties=NocaseDict([
                    CIMProperty('P1', value=u'H\u00E4m'),
                ])),
            None, True
        ),
        (
            "Verify property with boolean True value",
            dict(
                classname='CIM_Foo',
                properties=dict(P1=True)),
            dict(
                classname=u'CIM_Foo',
                properties=NocaseDict([
                    CIMProperty('P1', value=True),
                ])),
            None, True
        ),
        (
            "Verify property with boolean False value",
            dict(
                classname='CIM_Foo',
                properties=dict(P1=False)),
            dict(
                classname=u'CIM_Foo',
                properties=NocaseDict([
                    CIMProperty('P1', value=False),
                ])),
            None, True
        ),
        (
            "Verify property with Uint8 value",
            dict(
                classname='CIM_Foo',
                properties=dict(P1=Uint8(42))),
            dict(
                classname=u'CIM_Foo',
                properties=NocaseDict([
                    CIMProperty('P1', type='uint8', value=Uint8(42)),
                ])),
            None, True
        ),
        (
            "Verify property with Uint16 value",
            dict(
                classname='CIM_Foo',
                properties=dict(P1=Uint16(4216))),
            dict(
                classname=u'CIM_Foo',
                properties=NocaseDict([
                    CIMProperty('P1', type='uint16', value=Uint16(4216)),
                ])),
            None, True
        ),
        (
            "Verify property with Uint32 value",
            dict(
                classname='CIM_Foo',
                properties=dict(P1=Uint32(4232))),
            dict(
                classname=u'CIM_Foo',
                properties=NocaseDict([
                    CIMProperty('P1', type='uint32', value=Uint32(4232)),
                ])),
            None, True
        ),
        (
            "Verify property with Uint64 value",
            dict(
                classname='CIM_Foo',
                properties=dict(P1=Uint64(4264))),
            dict(
                classname=u'CIM_Foo',
                properties=NocaseDict([
                    CIMProperty('P1', type='uint64', value=Uint64(4264)),
                ])),
            None, True
        ),
        (
            "Verify property with Sint8 value",
            dict(
                classname='CIM_Foo',
                properties=dict(P1=Sint8(-42))),
            dict(
                classname=u'CIM_Foo',
                properties=NocaseDict([
                    CIMProperty('P1', type='sint8', value=Sint8(-42)),
                ])),
            None, True
        ),
        (
            "Verify property with Sint16 value",
            dict(
                classname='CIM_Foo',
                properties=dict(P1=Sint16(-4216))),
            dict(
                classname=u'CIM_Foo',
                properties=NocaseDict([
                    CIMProperty('P1', type='sint16', value=Sint16(-4216)),
                ])),
            None, True
        ),
        (
            "Verify property with Sint32 value",
            dict(
                classname='CIM_Foo',
                properties=dict(P1=Sint32(-4232))),
            dict(
                classname=u'CIM_Foo',
                properties=NocaseDict([
                    CIMProperty('P1', type='sint32', value=Sint32(-4232)),
                ])),
            None, True
        ),
        (
            "Verify property with Sint64 value",
            dict(
                classname='CIM_Foo',
                properties=dict(P1=Sint64(-4264))),
            dict(
                classname=u'CIM_Foo',
                properties=NocaseDict([
                    CIMProperty('P1', type='sint64', value=Sint64(-4264)),
                ])),
            None, True
        ),
        (
            "Verify property with Real32 value",
            dict(
                classname='CIM_Foo',
                properties=dict(P1=Real32(-42.32))),
            dict(
                classname=u'CIM_Foo',
                properties=NocaseDict([
                    CIMProperty('P1', type='real32', value=Real32(-42.32)),
                ])),
            None, True
        ),
        (
            "Verify property with Real64 value",
            dict(
                classname='CIM_Foo',
                properties=dict(P1=Real64(-42.64))),
            dict(
                classname=u'CIM_Foo',
                properties=NocaseDict([
                    CIMProperty('P1', type='real64', value=Real64(-42.64)),
                ])),
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
                properties=NocaseDict([
                    CIMProperty(
                        'P1', type='datetime',
                        value=datetime(2014, 9, 22, 10, 49, 20, 524789)),
                ])),
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
                properties=NocaseDict([
                    CIMProperty(
                        'P1', type='datetime',
                        value=timedelta(10, 49, 20)),
                ])),
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
                properties=NocaseDict([
                    CIMProperty('P1', value=u'Ham'),
                ])),
            None, True
        ),
        (
            "Verify two properties in same order",
            dict(
                classname='CIM_Foo',
                properties=[
                    CIMProperty('P1', value='Ham'),
                    CIMProperty('P2', value=True),
                ]),
            dict(
                classname=u'CIM_Foo',
                properties=NocaseDict([
                    CIMProperty('P1', value='Ham'),
                    CIMProperty('P2', value=True),
                ])),
            None, True
        ),
        (
            "Verify that equality of instances does not depend on order of "
            "properties",
            dict(
                classname='CIM_Foo',
                properties=[
                    CIMProperty('P1', value='Ham'),
                    CIMProperty('P2', value=True),
                ]),
            dict(
                classname=u'CIM_Foo',
                properties=NocaseDict([
                    CIMProperty('P2', value=True),
                    CIMProperty('P1', value='Ham'),
                ])),
            None, True
        ),

        # Qualifiers tests
        (
            "Verify qualifiers order preservation with list of CIMQualifier",
            dict(
                classname='CIM_Foo',
                qualifiers=[
                    CIMQualifier('Q1', value='Ham'),
                    CIMQualifier('Q2', value='Cheese'),
                ]
            ),
            dict(
                classname=u'CIM_Foo',
                qualifiers=NocaseDict([
                    ('Q1', CIMQualifier('Q1', value='Ham')),
                    ('Q2', CIMQualifier('Q2', value='Cheese')),
                ])
            ),
            None, True
        ),
        (
            "Verify qualifiers order preservation with OrderedDict",
            dict(
                classname='CIM_Foo',
                qualifiers=OrderedDict([
                    ('Q1', CIMQualifier('Q1', value='Ham')),
                    ('Q2', CIMQualifier('Q2', value='Cheese')),
                ])
            ),
            dict(
                classname=u'CIM_Foo',
                qualifiers=NocaseDict([
                    ('Q1', CIMQualifier('Q1', value='Ham')),
                    ('Q2', CIMQualifier('Q2', value='Cheese')),
                ])
            ),
            None, True
        ),
        (
            "Verify qualifiers order preservation with list of tuple(key,val)",
            dict(
                classname='CIM_Foo',
                qualifiers=[
                    ('Q1', CIMQualifier('Q1', value='Ham')),
                    ('Q2', CIMQualifier('Q2', value='Cheese')),
                ]
            ),
            dict(
                classname=u'CIM_Foo',
                qualifiers=NocaseDict([
                    ('Q1', CIMQualifier('Q1', value='Ham')),
                    ('Q2', CIMQualifier('Q2', value='Cheese')),
                ])
            ),
            None, True
        ),
        (
            "Verify qualifier with CIMQualifier (of arbitrary type and value)",
            # Note: The full range of possible input values and types for
            # CIMQualifier objects is tested in CIMQualifier testcases.
            dict(
                classname='CIM_Foo',
                qualifiers=[CIMQualifier('Q1', value='Ham')]),
            dict(
                classname=u'CIM_Foo',
                qualifiers=NocaseDict([
                    CIMQualifier('Q1', value=u'Ham'),
                ])),
            None, True
        ),
        (
            "Verify that equality of instances does not depend on order of "
            "qualifiers",
            dict(
                classname='CIM_Foo',
                qualifiers=[
                    CIMQualifier('Q1', value='Ham'),
                    CIMQualifier('Q2', value=True),
                ]),
            dict(
                classname=u'CIM_Foo',
                qualifiers=NocaseDict([
                    CIMQualifier('Q2', value=True),
                    CIMQualifier('Q1', value=u'Ham'),
                ])),
            None, True
        ),

        # Path tests
        (
            "Verify path without corresponding key property",
            dict(
                classname='CIM_Foo',
                path=CIMInstanceName(
                    classname='CIM_Foo',
                    keybindings=dict(K1='Key1')
                )),
            dict(
                classname=u'CIM_Foo',
                path=CIMInstanceName(
                    classname='CIM_Foo',
                    keybindings=NocaseDict([
                        ('K1', 'Key1'),
                    ])
                )),
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
                properties=NocaseDict([
                    CIMProperty('K1', value='Ham'),
                ]),
                path=CIMInstanceName(
                    classname='CIM_Foo',
                    keybindings=NocaseDict([
                        ('K1', 'Ham'),  # keybinding value has been updated
                    ])
                )),
            None, True
        ),

        # Property_list tests
        (
            "Verify that using property_list issues DeprecationWarning",
            dict(
                classname='CIM_Foo',
                property_list=['P1']),
            dict(
                classname=u'CIM_Foo',
                property_list=['p1']),
            DeprecationWarning if CHECK_0_12_0 else None, True
        ),
        (
            "Verify that setting a property in property_list is not ignored",
            dict(
                classname='CIM_Foo',
                properties=dict(P1='v1', P2='v2'),
                property_list=['P1', 'P2']),
            dict(
                classname=u'CIM_Foo',
                properties=NocaseDict([
                    CIMProperty('P1', type='string', value='v1'),
                    CIMProperty('P2', type='string', value='v2'),
                ]),
                property_list=['p1', 'p2']),
            DeprecationWarning if CHECK_0_12_0 else None, True
        ),
        (
            "Verify that setting a property not in property_list is not "
            "ignored when no path is set",
            dict(
                classname='CIM_Foo',
                properties=dict(P1='v1', P2='v2'),
                property_list=['P2']),
            dict(
                classname=u'CIM_Foo',
                properties=NocaseDict([
                    CIMProperty('P1', type='string', value='v1'),
                    CIMProperty('P2', type='string', value='v2'),
                ]),
                property_list=['p2']),
            DeprecationWarning if CHECK_0_12_0 else None, True
        ),
        (
            "Verify that setting a property not in property_list is "
            "ignored when a path is set with a different keybinding",
            dict(
                classname='CIM_Foo',
                properties=dict(P1='v1', P2='v2', K3='v3'),
                path=CIMInstanceName(
                    classname='CIM_Foo',
                    keybindings=dict(K3='v3')),
                property_list=['P2', 'K3']),
            dict(
                classname=u'CIM_Foo',
                properties=NocaseDict([
                    CIMProperty('P2', type='string', value='v2'),
                    CIMProperty('K3', type='string', value='v3'),
                ]),
                path=CIMInstanceName(
                    classname='CIM_Foo',
                    keybindings=NocaseDict([
                        ('K3', 'v3'),
                    ]),
                ),
                property_list=['p2', 'k3']),
            DeprecationWarning if CHECK_0_12_0 else None, True
        ),
        (
            "Verify that setting a (key) property not in property_list is not "
            "ignored when a path is set with that property as a keybinding",
            dict(
                classname='CIM_Foo',
                properties=OrderedDict([('P1', 'v1'), ('P2', 'v2'),
                                        ('K3', 'v3')]),
                path=CIMInstanceName(
                    classname='CIM_Foo',
                    keybindings=dict(K3='v3')),
                property_list=['P1', 'P2']),
            dict(
                classname=u'CIM_Foo',
                properties=NocaseDict([
                    CIMProperty('P1', type='string', value='v1'),
                    CIMProperty('P2', type='string', value='v2'),
                    CIMProperty('K3', type='string', value='v3'),
                ]),
                path=CIMInstanceName(
                    classname='CIM_Foo',
                    keybindings=NocaseDict([
                        ('K3', 'v3'),
                    ])
                ),
                property_list=['p1', 'p2']),
            DeprecationWarning if CHECK_0_12_0 else None, True
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
            with pytest.warns(exp_warn_type) as rec_warnings:

                # The code to be tested
                obj = CIMInstance(**kwargs)

            assert len(rec_warnings) == 1

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

        # Properties should compare order-insensitively

        self.assertEqual(
            CIMInstance(
                'CIM_Foo',
                properties=[
                    ('Cheepy', 'Birds'),
                    ('Creepy', 'Ants'),
                ]),
            CIMInstance(
                'CIM_Foo',
                properties=[
                    ('Cheepy', 'Birds'),
                    ('Creepy', 'Ants'),
                ]),
        )

        self.assertEqual(
            CIMInstance(
                'CIM_Foo',
                properties=[
                    ('Cheepy', 'Birds'),
                    ('Creepy', 'Ants'),
                ]),
            CIMInstance(
                'CIM_Foo',
                properties=[
                    ('Creepy', 'Ants'),
                    ('Cheepy', 'Birds'),
                ]),
        )

        # Qualifiers

        self.assertNotEqual(CIMInstance('CIM_Foo'),
                            CIMInstance('CIM_Foo',
                                        qualifiers={'Key':
                                                    CIMQualifier('Key',
                                                                 True)}))

        # Qualifiers should compare order-insensitively

        self.assertEqual(
            CIMInstance(
                'CIM_Foo',
                qualifiers=[
                    CIMQualifier('Q1', 'Birds'),
                    CIMQualifier('Q2', 'Ants'),
                ]),
            CIMInstance(
                'CIM_Foo',
                qualifiers=[
                    CIMQualifier('Q1', 'Birds'),
                    CIMQualifier('Q2', 'Ants'),
                ]),
        )

        self.assertEqual(
            CIMInstance(
                'CIM_Foo',
                qualifiers=[
                    CIMQualifier('Q1', 'Birds'),
                    CIMQualifier('Q2', 'Ants'),
                ]),
            CIMInstance(
                'CIM_Foo',
                qualifiers=[
                    CIMQualifier('Q2', 'Ants'),
                    CIMQualifier('Q1', 'Birds'),
                ]),
        )

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


testcases_CIMInstance_hash = [

    # Each testcase tuple has these items:
    # * desc: Short testcase description.
    # * kwargs: Input arguments for test function, as a dict:
    #   * obj1: CIMInstance object #1 to be tested.
    #   * obj2: CIMInstance object #2 to be tested.
    #   * exp_hash_equal: Expected equality of the object hash values.
    # * exp_exc_types: Expected exception type(s), or None.
    # * exp_warn_types: Expected warning type(s), or None.
    # * condition: Boolean condition for testcase to run, or 'pdb' for debugger

    # Classname tests
    (
        "Classname, equal with same lexical case",
        dict(
            obj1=CIMInstance('CIM_Foo'),
            obj2=CIMInstance('CIM_Foo'),
            exp_hash_equal=True,
        ),
        None, None, True
    ),
    (
        "Classname, equal with different lexical case",
        dict(
            obj1=CIMInstance('CIM_Foo'),
            obj2=CIMInstance('ciM_foO'),
            exp_hash_equal=True,
        ),
        None, None, True
    ),
    (
        "Classname, different",
        dict(
            obj1=CIMInstance('CIM_Foo'),
            obj2=CIMInstance('CIM_Foo_x'),
            exp_hash_equal=False,
        ),
        None, None, True
    ),

    # Path tests
    (
        "Instance paths, equal with same lexical case",
        dict(
            obj1=CIMInstance(
                'CIM_Foo',
                path=CIMInstanceName('CIM_Foo', {'k1': 'v1'}),
            ),
            obj2=CIMInstance(
                'CIM_Foo',
                path=CIMInstanceName('CIM_Foo', {'k1': 'v1'}),
            ),
            exp_hash_equal=True,
        ),
        None, None, True
    ),
    (
        "Instance paths, equal with different lexical case in classname",
        dict(
            obj1=CIMInstance(
                'CIM_Foo',
                path=CIMInstanceName('CIM_Foo', {'k1': 'v1'}),
            ),
            obj2=CIMInstance(
                'CIM_Foo',
                path=CIMInstanceName('CIM_foo', {'k1': 'v1'}),
            ),
            exp_hash_equal=True,
        ),
        None, None, True
    ),
    (
        "Instance paths, different",
        dict(
            obj1=CIMInstance(
                'CIM_Foo',
                path=CIMInstanceName('CIM_Foo', {'k1': 'v1'}),
            ),
            obj2=CIMInstance(
                'CIM_Foo',
                path=CIMInstanceName('CIM_Foo', {'k1': 'v1_x'}),
            ),
            exp_hash_equal=False,
        ),
        None, None, True
    ),

    # Properties tests
    (
        "Matching properties, names with same lexical case",
        dict(
            obj1=CIMInstance('CIM_Foo', properties={'Cheepy': 'Birds'}),
            obj2=CIMInstance('CIM_Foo', properties={'Cheepy': 'Birds'}),
            exp_hash_equal=True,
        ),
        None, None, True
    ),
    (
        "Matching properties, names with different lexical case",
        dict(
            obj1=CIMInstance('CIM_Foo', properties={'Cheepy': 'Birds'}),
            obj2=CIMInstance('CIM_Foo', properties={'cheepy': 'Birds'}),
            exp_hash_equal=True,
        ),
        None, None, True
    ),

    (
        "Non-matching properties, one property more",
        dict(
            obj1=CIMInstance('CIM_Foo'),
            obj2=CIMInstance('CIM_Foo', properties={'Cheepy': 'Birds'}),
            exp_hash_equal=False,
        ),
        None, None, True
    ),
    (
        "Non-matching properties, one property less",
        dict(
            obj1=CIMInstance('CIM_Foo', properties={'Cheepy': 'Birds'}),
            obj2=CIMInstance('CIM_Foo'),
            exp_hash_equal=False,
        ),
        None, None, True
    ),
    (
        "Non-matching properties, different properties",
        dict(
            obj1=CIMInstance('CIM_Foo', properties={'Cheepy': 'Birds'}),
            obj2=CIMInstance('CIM_Foo', properties={'Creepy': 'Ants'}),
            exp_hash_equal=False,
        ),
        None, None, True
    ),
    (
        "Matching properties, with values that differ in lexical case",
        dict(
            obj1=CIMInstance('CIM_Foo', properties={'Cheepy': 'Birds'}),
            obj2=CIMInstance('CIM_Foo', properties={'Cheepy': 'birds'}),
            exp_hash_equal=False,
        ),
        None, None, True
    ),
    (
        "Matching properties, with values that is unicode / string",
        dict(
            obj1=CIMInstance('CIM_Foo', properties={'Cheepy': 'Birds'}),
            obj2=CIMInstance('CIM_Foo', properties={'Cheepy': u'Birds'}),
            exp_hash_equal=True,
        ),
        None, None, True
    ),
    (
        "Equal properties with a number of types",
        dict(
            obj1=CIMInstance('CIM_Foo', properties={
                'Name': 'Foo',
                'Boolean': False,
                'Number': Uint8(42),
                'Ref': CIMInstanceName('CIM_Bar'),
            }),
            obj2=CIMInstance('CIM_Foo', properties={
                'Name': 'Foo',
                'Boolean': False,
                'Number': Uint8(42),
                'Ref': CIMInstanceName('CIM_Bar'),
            }),
            exp_hash_equal=True,
        ),
        None, None, True
    ),
    (
        "Property with different types: bool True / string 'TRUE'",
        dict(
            obj1=CIMInstance('CIM_Foo', properties={'Foo': True}),
            obj2=CIMInstance('CIM_Foo', properties={'Foo': 'TRUE'}),
            exp_hash_equal=False,
        ),
        None, None, True
    ),
    (
        "Property with different types: bool False / string 'FALSE'",
        dict(
            obj1=CIMInstance('CIM_Foo', properties={'Foo': False}),
            obj2=CIMInstance('CIM_Foo', properties={'Foo': 'FALSE'}),
            exp_hash_equal=False,
        ),
        None, None, True
    ),

    # Qualifiers tests
    (
        "Matching qualifiers, qualifier names with same lexical case",
        dict(
            obj1=CIMInstance('CIM_Foo',
                             qualifiers={'Cheepy': 'Birds'}),
            obj2=CIMInstance('CIM_Foo',
                             qualifiers={'Cheepy': 'Birds'}),
            exp_hash_equal=True,
        ),
        None, None, True
    ),
    (
        "Matching qualifiers, qualifier names with different lexical case",
        dict(
            obj1=CIMInstance('CIM_Foo',
                             qualifiers={'Cheepy': 'Birds'}),
            obj2=CIMInstance('CIM_Foo',
                             qualifiers={'cheepy': 'Birds'}),
            exp_hash_equal=True,
        ),
        None, None, True
    ),
    (
        "Non-matching qualifiers, one qualifier more",
        dict(
            obj1=CIMInstance('CIM_Foo'),
            obj2=CIMInstance('CIM_Foo',
                             qualifiers={'Cheepy': 'Birds'}),
            exp_hash_equal=False,
        ),
        None, None, True
    ),
    (
        "Non-matching qualifiers, one qualifier less",
        dict(
            obj1=CIMInstance('CIM_Foo'),
            obj2=CIMInstance('CIM_Foo',
                             qualifiers={'Cheepy': 'Birds'}),
            exp_hash_equal=False,
        ),
        None, None, True
    ),
    (
        "Non-matching qualifiers, different qualifiers",
        dict(
            obj1=CIMInstance('CIM_Foo',
                             qualifiers={'Cheepy': 'Birds'}),
            obj2=CIMInstance('CIM_Foo',
                             qualifiers={'Creepy': 'Ants'}),
            exp_hash_equal=False,
        ),
        None, None, True
    ),
    (
        "Matching qualifiers, with values that differ in lexical case",
        dict(
            obj1=CIMInstance('CIM_Foo',
                             qualifiers={'Cheepy': 'Birds'}),
            obj2=CIMInstance('CIM_Foo',
                             qualifiers={'Cheepy': 'birds'}),
            exp_hash_equal=False,
        ),
        None, None, True
    ),
    (
        "Matching qualifiers, with values that is unicode / string",
        dict(
            obj1=CIMInstance('CIM_Foo',
                             qualifiers={'Cheepy': 'Birds'}),
            obj2=CIMInstance('CIM_Foo',
                             qualifiers={'Cheepy': u'Birds'}),
            exp_hash_equal=True,
        ),
        None, None, True
    ),
    (
        "Equal qualifiers with a number of types",
        dict(
            obj1=CIMInstance(
                'CIM_Foo',
                qualifiers={
                    'Name': 'Foo',
                    'Boolean': False,
                    'Number': Uint8(42),
                    'Ref': CIMInstanceName('CIM_Bar'),
                }
            ),
            obj2=CIMInstance(
                'CIM_Foo',
                qualifiers={
                    'Name': 'Foo',
                    'Boolean': False,
                    'Number': Uint8(42),
                    'Ref': CIMInstanceName('CIM_Bar'),
                }
            ),
            exp_hash_equal=True,
        ),
        None, None, True
    ),
    (
        "Qualifier with different types: bool True / string 'TRUE'",
        dict(
            obj1=CIMInstance('CIM_Foo',
                             qualifiers={'Foo': True}),
            obj2=CIMInstance('CIM_Foo',
                             qualifiers={'Foo': 'TRUE'}),
            exp_hash_equal=False,
        ),
        None, None, True
    ),
    (
        "Qualifier with different types: bool False / string 'FALSE'",
        dict(
            obj1=CIMInstance('CIM_Foo',
                             qualifiers={'Foo': False}),
            obj2=CIMInstance('CIM_Foo',
                             qualifiers={'Foo': 'FALSE'}),
            exp_hash_equal=False,
        ),
        None, None, True
    ),

    # Property_list tests
    (
        "Different property lists (does not matter for hash and equality)",
        dict(
            obj1=CIMInstance(
                'CIM_Foo',
                properties={'Cheepy': 'Birds'},
                property_list=['Cheepy'],
            ),
            obj2=CIMInstance(
                'CIM_Foo',
                properties={'Cheepy': 'Birds'},
                property_list=[],
            ),
            exp_hash_equal=True,
        ),
        None, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    testcases_CIMInstance_hash)
@pytest_extensions.test_function
def test_CIMInstance_hash(
        desc, kwargs, exp_exc_types, exp_warn_types, condition):
    """
    All test cases for CIMInstance.__hash__().
    """

    obj1 = kwargs['obj1']
    obj2 = kwargs['obj2']

    # Double check they are different objects
    assert id(obj1) != id(obj2)

    # The code to be tested
    hash1 = hash(obj1)
    hash2 = hash(obj2)

    exp_hash_equal = kwargs['exp_hash_equal']

    assert (hash1 == hash2) == exp_hash_equal


class Test_CIMInstance_str(object):  # pylint: disable=too-few-public-methods
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


class Test_CIMInstance_repr(object):  # pylint: disable=too-few-public-methods
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


class Test_CIMInstance_tomof(object):
    """
    Test CIMInstance.tomof().
    """

    testcases = [
        # Testcases for CIMInstance.tomof().
        # Each testcase has these items:
        # * desc: Short testcase description.
        # * obj: Object to be tested.
        # * exp_result: Expected MOF string, if expected to succeed.
        #     Exception type, if expected to fail.
        # * exp_warn_type: Expected warning type.
        #     None, if no warning expected.
        # * condition: Condition for testcase to run.
        (
            "all components",
            CIMInstance(
                classname='C1',
                properties=[
                    CIMProperty('p1', value=None, type='string'),
                ],
            ),
            """\
instance of C1 {
   p1 = NULL;
};
""" \
            if CHECK_0_12_0 else \
            """\
instance of C1 {
    p1 = NULL;
};
""",
            None, True
        ),
        (
            "Instance with NULL value on string property",
            CIMInstance(
                classname='C1',
                properties=[
                    CIMProperty('p1', value=None, type='string'),
                ],
            ),
            """\
instance of C1 {
   p1 = NULL;
};
""" \
            if CHECK_0_12_0 else \
            """\
instance of C1 {
    p1 = NULL;
};
""",
            None, True
        ),
        (
            "Instance with string property",
            CIMInstance(
                classname='C1',
                properties=[
                    CIMProperty('p1', value='abc'),
                ],
            ),
            """\
instance of C1 {
   p1 = "abc";
};
""" \
            if CHECK_0_12_0 else \
            """\
instance of C1 {
    p1 = "abc";
};
""",
            None, True
        ),
        (
            "Instance with uint8 property",
            CIMInstance(
                classname='C1',
                properties=[
                    CIMProperty('p1', value=Uint8(7)),
                ],
            ),
            """\
instance of C1 {
   p1 = 7;
};
""" \
            if CHECK_0_12_0 else \
            """\
instance of C1 {
    p1 = 7;
};
""",
            None, True
        ),
        (
            "Instance with sint8 array property",
            CIMInstance(
                classname='C1',
                properties=[
                    CIMProperty('p1', value=[Sint8(-1), Sint8(5)]),
                ],
            ),
            """\
instance of C1 {
   p1 = { -1, 5 };
};
""" \
            if CHECK_0_12_0 else \
            """\
instance of C1 {
    p1 =  = {-1, 5};
};
""",  # bug fixed in 0.12
            None, True
        ),
        (
            "Instance with embedded instance property having one key",
            CIMInstance(
                classname='C1',
                properties=[
                    CIMProperty(
                        'p1',
                        value=CIMInstance(
                            classname='EC',
                            properties=[
                                ('e1', 'abc'),
                            ],
                        ),
                        embedded_object='instance',
                    ),
                ],
            ),
            """\
instance of C1 {
   p1 = "instance of EC {\\n   e1 = \\"abc\\";\\n};\\n";
};
""" \
            if CHECK_0_12_0 else \
            """\
instance of C1 {
    p1 = "instance of EC {\\n    e1 = \\"abc\\";\\n};\\n";
};
""",
            None, True
        ),
        (
            "Instance with embedded instance property having multiple keys",
            CIMInstance(
                classname='C1',
                properties=[
                    CIMProperty(
                        'p1',
                        value=CIMInstance(
                            classname='EC',
                            properties=[
                                ('e1', 'abc'),
                                ('e2', Uint32(42)),
                                ('e3',
                                 CIMDateTime('19980125133015.123456-300')),
                            ],
                        ),
                        embedded_object='instance',
                    ),
                ],
            ),
            """\
instance of C1 {
   p1 =
      "instance of EC {\\n   e1 = \\"abc\\";\\n   e2 = 42;\\n   e3 = "
      "\\"19980125133015.123456-300\\";\\n};\\n";
};
""",
            None, CHECK_0_12_0  # Unpredictable order of keys before 0.12
        ),
        (
            "Instance with embedded instance property as EmbeddedObject",
            CIMInstance(
                classname='C1',
                properties=[
                    CIMProperty(
                        'p1',
                        value=CIMInstance(
                            classname='EC',
                            properties=[
                                ('e1', 'abc'),
                            ],
                        ),
                        embedded_object='object',
                    ),
                ],
            ),
            """\
instance of C1 {
   p1 = "instance of EC {\\n   e1 = \\"abc\\";\\n};\\n";
};
""" \
            if CHECK_0_12_0 else \
            """\
instance of C1 {
    p1 = "instance of EC {\\n    e1 = \\"abc\\";\\n};\\n";
};
""",
            None, True
        ),
        (
            "Instance with embedded class property as EmbeddedObject",
            CIMInstance(
                classname='C1',
                properties=[
                    CIMProperty(
                        'p1',
                        value=CIMClass(
                            classname='EC',
                            properties=[
                                CIMProperty(
                                    'e1',
                                    value=None,
                                    type='uint32',
                                ),
                            ],
                        ),
                        embedded_object='object',
                    ),
                ],
            ),
            """\
instance of C1 {
   p1 = "class EC {\\n\\n   uint32 e1;\\n\\n};\\n";
};
""" \
            if CHECK_0_12_0 else \
            """\
instance of C1 {
    p1 = "\\nclass EC {\\n\\n    uint32 e1;\\n};\\n";
};
""",
            None, True
        ),
        (
            "Instance with reference property",
            CIMInstance(
                classname='C1',
                properties=[
                    CIMProperty(
                        'p1',
                        value=CIMInstanceName(
                            classname='RC',
                            keybindings=[
                                ('k1', "abc"),
                            ],
                        ),
                        reference_class='RC',
                    ),
                ],
            ),
            """\
instance of C1 {
   p1 = "/:RC.k1=\\"abc\\"";
};
""" \
            if CHECK_0_12_0 else \
            """\
instance of C1 {
    p1 = RC.k1="abc";
};
""",  # bug fixed in 0.12
            None, True
        ),
    ]

    @pytest.mark.parametrize(
        "desc, obj, exp_result, exp_warn_type, condition",
        testcases)
    def test_CIMInstance_tomof(
            self, desc, obj, exp_result, exp_warn_type, condition):
        """All test cases for CIMInstance.tomof()."""

        if not condition:
            pytest.skip("Condition for test case not met")

        if isinstance(exp_result, type) and issubclass(exp_result, Exception):
            # We expect an exception
            exp_exc_type = exp_result
            exp_mof = None
        else:
            # We expect the code to return
            exp_exc_type = None
            exp_mof = exp_result

        if condition == 'pdb':
            import pdb
            pdb.set_trace()

        if exp_warn_type:
            with pytest.warns(exp_warn_type) as rec_warnings:
                if exp_exc_type:
                    with pytest.raises(exp_exc_type):

                        # The code to be tested
                        mof = obj.tomof()

                else:

                    # The code to be tested
                    mof = obj.tomof()

            assert len(rec_warnings) == 1

        else:
            if exp_exc_type:
                with pytest.raises(exp_exc_type):

                    # The code to be tested
                    mof = obj.tomof()

            else:

                # The code to be tested
                mof = obj.tomof()

        if exp_mof:

            assert isinstance(mof, six.text_type)
            assert mof == exp_mof

    def test_CIMInstance_tomof_indent_warning(self):
        """CIMInstance.tomof() with deprecated 'indent' parameter."""

        if not CHECK_0_12_0:
            pytest.skip("Condition for test case not met")

        obj = CIMInstance('C1')

        exp_mof = "instance of C1 {\n};\n"

        with pytest.warns(DeprecationWarning) as rec_warnings:

            # The code to be tested
            mof = obj.tomof(indent=5)

        assert len(rec_warnings) == 1

        assert isinstance(mof, six.text_type)
        assert mof == exp_mof


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

        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
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

        # Name tests
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

        # Value/type tests: Initialization to CIM string type
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

        # Value/type tests: Initialization to CIM integer types
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

        # Value/type tests: Initialization to CIM float types
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

        # Value/type tests: Initialization to CIM boolean type
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

        # Value/type tests: Initialization to CIM datetime type
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

        # Value/type/reference_class tests: Initialization to CIM ref type
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
                 value='https://10.1.2.3:5989/root/cimv2:C1.k1="v1",k2=True',
                 type='reference'),
            dict(name=u'FooProp',
                 value=CIMInstanceName(
                     'C1', keybindings=dict(k1='v1', k2=True),
                     namespace='root/cimv2', host='10.1.2.3:5989'),
                 type=u'reference'),
            None, CHECK_0_12_0
        ),

        # Value/type/embedded_object tests: Initialization to CIM embedded
        # object (instance or class)
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

        # Value/type/embedded_object tests: Initialization to CIM embedded
        # instance
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

        # Is_array/array_size tests: Array tests with different is_array and
        # array_size
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

        # Value/type tests with arrays: Initialization to arrays of CIM string
        # and numeric types
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

        # Value/type tests with arrays: Initialization to arrays of CIM boolean
        # type
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

        # Value/type tests with arrays: Initialization to arrays of CIM
        # datetime type
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

        # Value/type/embedded_object tests with arrays: Initialization to
        # arrays of CIM embedded objects (class and inst)
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

        # Value/type/embedded_object tests with arrays: Initialization to
        # arrays of CIM embedded instances
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

        # Qualifiers tests
        (
            "Verify qualifiers order preservation with list of CIMQualifier",
            dict(
                name='Prop1', value=None, type='string',
                qualifiers=[
                    CIMQualifier('Q1', value='Ham'),
                    CIMQualifier('Q2', value='Cheese'),
                ]
            ),
            dict(
                name=u'Prop1', value=None, type=u'string',
                qualifiers=NocaseDict([
                    ('Q1', CIMQualifier('Q1', value='Ham')),
                    ('Q2', CIMQualifier('Q2', value='Cheese')),
                ])
            ),
            None, True
        ),
        (
            "Verify qualifiers order preservation with OrderedDict",
            dict(
                name='Prop1', value=None, type='string',
                qualifiers=OrderedDict([
                    ('Q1', CIMQualifier('Q1', value='Ham')),
                    ('Q2', CIMQualifier('Q2', value='Cheese')),
                ])
            ),
            dict(
                name=u'Prop1', value=None, type=u'string',
                qualifiers=NocaseDict([
                    ('Q1', CIMQualifier('Q1', value='Ham')),
                    ('Q2', CIMQualifier('Q2', value='Cheese')),
                ])
            ),
            None, True
        ),
        (
            "Verify qualifiers order preservation with list of tuple(key,val)",
            dict(
                name='Prop1', value=None, type='string',
                qualifiers=[
                    ('Q1', CIMQualifier('Q1', value='Ham')),
                    ('Q2', CIMQualifier('Q2', value='Cheese')),
                ]
            ),
            dict(
                name=u'Prop1', value=None, type=u'string',
                qualifiers=NocaseDict([
                    ('Q1', CIMQualifier('Q1', value='Ham')),
                    ('Q2', CIMQualifier('Q2', value='Cheese')),
                ])
            ),
            None, True
        ),
        (
            "Verify that qualifiers dict is converted to NocaseDict",
            dict(name=u'FooProp', value=u'abc', type=u'string',
                 qualifiers=dict(Q1=qualifier_Q1)),
            dict(name=u'FooProp', value=u'abc', type=u'string',
                 qualifiers=NocaseDict(Q1=qualifier_Q1)),
            None, True
        ),
        (
            "Verify that qualifiers as list of CIMQualifier objects is "
            "converted to NocaseDict",
            dict(name=u'FooProp', value=u'abc', type=u'string',
                 qualifiers=[qualifier_Q1]),
            dict(name=u'FooProp', value=u'abc', type=u'string',
                 qualifiers=NocaseDict(Q1=qualifier_Q1)),
            None, True
        ),
        (
            "Verify that qualifiers as NocaseDict stays NocaseDict",
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
            with pytest.warns(exp_warn_type) as rec_warnings:

                # The code to be tested
                obj = CIMProperty(**kwargs)

            assert len(rec_warnings) == 1

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
            "Verify that an invalid type fails (since 0.12)",
            dict(name='FooProp', value=None, type='xxx'),
            ValueError, CHECK_0_12_0
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

        # Qualifiers should compare order-insensitively

        self.assertEqual(
            CIMProperty(
                'Foo', value='abc',
                qualifiers=[
                    CIMQualifier('Q1', 'Birds'),
                    CIMQualifier('Q2', 'Ants'),
                ]),
            CIMProperty(
                'Foo', value='abc',
                qualifiers=[
                    CIMQualifier('Q1', 'Birds'),
                    CIMQualifier('Q2', 'Ants'),
                ]),
        )

        self.assertEqual(
            CIMProperty(
                'Foo', value='abc',
                qualifiers=[
                    CIMQualifier('Q1', 'Birds'),
                    CIMQualifier('Q2', 'Ants'),
                ]),
            CIMProperty(
                'Foo', value='abc',
                qualifiers=[
                    CIMQualifier('Q2', 'Ants'),
                    CIMQualifier('Q1', 'Birds'),
                ]),
        )


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


testcases_CIMProperty_hash = [

    # Each testcase tuple has these items:
    # * desc: Short testcase description.
    # * kwargs: Input arguments for test function, as a dict:
    #   * obj1: CIMProperty object #1 to be tested.
    #   * obj2: CIMProperty object #2 to be tested.
    #   * exp_hash_equal: Expected equality of the object hash values.
    # * exp_exc_types: Expected exception type(s), or None.
    # * exp_warn_types: Expected warning type(s), or None.
    # * condition: Boolean condition for testcase to run, or 'pdb' for debugger

    # Name tests
    (
        "Name, equal with same lexical case",
        dict(
            obj1=CIMProperty('Prop1', value=''),
            obj2=CIMProperty('Prop1', value=''),
            exp_hash_equal=True,
        ),
        None, None, True
    ),
    (
        "Name, equal with different lexical case",
        dict(
            obj1=CIMProperty('Prop1', value=''),
            obj2=CIMProperty('prOP1', value=''),
            exp_hash_equal=True,
        ),
        None, None, True
    ),
    (
        "Name, different",
        dict(
            obj1=CIMProperty('Prop1', value=''),
            obj2=CIMProperty('Prop1_x', value=''),
            exp_hash_equal=False,
        ),
        None, None, True
    ),

    # Value tests
    (
        "Value, strings with different lexical case",
        dict(
            obj1=CIMProperty('Prop1', value='abc'),
            obj2=CIMProperty('Prop1', value='Abc'),
            exp_hash_equal=False,
        ),
        None, None, True
    ),
    (
        "Value, strings with None / string",
        dict(
            obj1=CIMProperty('Prop1', value=None, type='string'),
            obj2=CIMProperty('Prop1', value='abc', type='string'),
            exp_hash_equal=False,
        ),
        None, None, True
    ),
    (
        "Value, strings with string / None",
        dict(
            obj1=CIMProperty('Prop1', value='abc', type='string'),
            obj2=CIMProperty('Prop1', value=None, type='string'),
            exp_hash_equal=False,
        ),
        None, None, True
    ),
    (
        "Value, strings with None / None",
        dict(
            obj1=CIMProperty('Prop1', value=None, type='string'),
            obj2=CIMProperty('Prop1', value=None, type='string'),
            exp_hash_equal=True,
        ),
        None, None, True
    ),

    # Type tests
    (
        "Type, different",
        dict(
            obj1=CIMProperty('Prop1', value=7, type='uint8'),
            obj2=CIMProperty('Prop1', value=7, type='sint8'),
            exp_hash_equal=False,
        ),
        None, None, True
    ),

    # Reference_class tests
    (
        "Reference class, equal with same lexical case",
        dict(
            obj1=CIMProperty('Prop1', value=None, type='reference',
                             reference_class='CIM_Ref'),
            obj2=CIMProperty('Prop1', value=None, type='reference',
                             reference_class='CIM_Ref'),
            exp_hash_equal=True,
        ),
        None, None, True
    ),
    (
        "Reference class, equal with different lexical case",
        dict(
            obj1=CIMProperty('Prop1', value=None, type='reference',
                             reference_class='CIM_Ref'),
            obj2=CIMProperty('Prop1', value=None, type='reference',
                             reference_class='Cim_ref'),
            exp_hash_equal=True,
        ),
        None, None, True
    ),
    (
        "Reference class, different",
        dict(
            obj1=CIMProperty('Prop1', value=None, type='reference',
                             reference_class='CIM_Ref'),
            obj2=CIMProperty('Prop1', value=None, type='reference',
                             reference_class='CIM_Ref_x'),
            exp_hash_equal=False,
        ),
        None, None, True
    ),

    # Embedded_object tests
    (
        "Embedded object, equal",
        dict(
            obj1=CIMProperty('Prop1', value=None, type='string',
                             embedded_object='instance'),
            obj2=CIMProperty('Prop1', value=None, type='string',
                             embedded_object='instance'),
            exp_hash_equal=True,
        ),
        None, None, True
    ),
    (
        "Embedded object, different",
        dict(
            obj1=CIMProperty('Prop1', value=None, type='string',
                             embedded_object='instance'),
            obj2=CIMProperty('Prop1', value=None, type='string',
                             embedded_object='object'),
            exp_hash_equal=False,
        ),
        None, None, True
    ),

    # Is_array tests
    (
        "Is_array, equal",
        dict(
            obj1=CIMProperty('Prop1', value=None, type='string',
                             is_array=True),
            obj2=CIMProperty('Prop1', value=None, type='string',
                             is_array=True),
            exp_hash_equal=True,
        ),
        None, None, True
    ),
    (
        "Is_array, different",
        dict(
            obj1=CIMProperty('Prop1', value=None, type='string',
                             is_array=True),
            obj2=CIMProperty('Prop1', value=None, type='string',
                             is_array=False),
            exp_hash_equal=False,
        ),
        None, None, True
    ),

    # Array_size tests
    (
        "Array_size, equal",
        dict(
            obj1=CIMProperty('Prop1', value=None, type='string', is_array=True,
                             array_size=2),
            obj2=CIMProperty('Prop1', value=None, type='string', is_array=True,
                             array_size=2),
            exp_hash_equal=True,
        ),
        None, None, True
    ),
    (
        "Array_size, different",
        dict(
            obj1=CIMProperty('Prop1', value=None, type='string', is_array=True,
                             array_size=2),
            obj2=CIMProperty('Prop1', value=None, type='string', is_array=True,
                             array_size=3),
            exp_hash_equal=False,
        ),
        None, None, True
    ),

    # Propagated tests
    (
        "Propagated, equal",
        dict(
            obj1=CIMProperty('Prop1', value=None, type='string',
                             propagated=True),
            obj2=CIMProperty('Prop1', value=None, type='string',
                             propagated=True),
            exp_hash_equal=True,
        ),
        None, None, True
    ),
    (
        "Propagated, different",
        dict(
            obj1=CIMProperty('Prop1', value=None, type='string',
                             propagated=True),
            obj2=CIMProperty('Prop1', value=None, type='string',
                             propagated=False),
            exp_hash_equal=False,
        ),
        None, None, True
    ),

    # Class_origin tests
    (
        "Class_origin, equal with same lexical case",
        dict(
            obj1=CIMProperty('Prop1', value=None, type='string',
                             propagated=True, class_origin='CIM_Org'),
            obj2=CIMProperty('Prop1', value=None, type='string',
                             propagated=True, class_origin='CIM_Org'),
            exp_hash_equal=True,
        ),
        None, None, True
    ),
    (
        "Class_origin, equal with different lexical case",
        dict(
            obj1=CIMProperty('Prop1', value=None, type='string',
                             propagated=True, class_origin='CIM_Org'),
            obj2=CIMProperty('Prop1', value=None, type='string',
                             propagated=True, class_origin='Cim_org'),
            exp_hash_equal=True,
        ),
        None, None, True
    ),
    (
        "Class_origin, different",
        dict(
            obj1=CIMProperty('Prop1', value=None, type='string',
                             propagated=True, class_origin='CIM_Org'),
            obj2=CIMProperty('Prop1', value=None, type='string',
                             propagated=True, class_origin='CIM_Org_x'),
            exp_hash_equal=False,
        ),
        None, None, True
    ),

    # Qualifiers tests
    (
        "Matching qualifiers, qualifier names with same lexical case",
        dict(
            obj1=CIMProperty('Prop1', value='',
                             qualifiers={'Cheepy': 'Birds'}),
            obj2=CIMProperty('Prop1', value='',
                             qualifiers={'Cheepy': 'Birds'}),
            exp_hash_equal=True,
        ),
        None, None, True
    ),
    (
        "Matching qualifiers, qualifier names with different lexical case",
        dict(
            obj1=CIMProperty('Prop1', value='',
                             qualifiers={'Cheepy': 'Birds'}),
            obj2=CIMProperty('Prop1', value='',
                             qualifiers={'cheepy': 'Birds'}),
            exp_hash_equal=True,
        ),
        None, None, True
    ),
    (
        "Non-matching qualifiers, one qualifier more",
        dict(
            obj1=CIMProperty('Prop1', value=''),
            obj2=CIMProperty('Prop1', value='',
                             qualifiers={'Cheepy': 'Birds'}),
            exp_hash_equal=False,
        ),
        None, None, True
    ),
    (
        "Non-matching qualifiers, one qualifier less",
        dict(
            obj1=CIMProperty('Prop1', value='',
                             qualifiers={'Cheepy': 'Birds'}),
            obj2=CIMProperty('Prop1', value=''),
            exp_hash_equal=False,
        ),
        None, None, True
    ),
    (
        "Non-matching qualifiers, different qualifiers",
        dict(
            obj1=CIMProperty('Prop1', value='',
                             qualifiers={'Cheepy': 'Birds'}),
            obj2=CIMProperty('Prop1', value='',
                             qualifiers={'Creepy': 'Ants'}),
            exp_hash_equal=False,
        ),
        None, None, True
    ),
    (
        "Matching qualifiers, with values that differ in lexical case",
        dict(
            obj1=CIMProperty('Prop1', value='',
                             qualifiers={'Cheepy': 'Birds'}),
            obj2=CIMProperty('Prop1', value='',
                             qualifiers={'Cheepy': 'birds'}),
            exp_hash_equal=False,
        ),
        None, None, True
    ),
    (
        "Matching qualifiers, with values that are unicode / string",
        dict(
            obj1=CIMProperty('Prop1', value='',
                             qualifiers={'Cheepy': 'Birds'}),
            obj2=CIMProperty('Prop1', value='',
                             qualifiers={'Cheepy': u'Birds'}),
            exp_hash_equal=True,
        ),
        None, None, True
    ),
    (
        "Equal qualifiers with a number of types",
        dict(
            obj1=CIMProperty(
                'Prop1', value='',
                qualifiers={
                    'Name': 'Foo',
                    'Boolean': False,
                    'Number': Uint8(42),
                    'Ref': CIMInstanceName('CIM_Bar'),
                }
            ),
            obj2=CIMProperty(
                'Prop1', value='',
                qualifiers={
                    'Name': 'Foo',
                    'Boolean': False,
                    'Number': Uint8(42),
                    'Ref': CIMInstanceName('CIM_Bar'),
                }
            ),
            exp_hash_equal=True,
        ),
        None, None, True
    ),
    (
        "Qualifier with different types: bool True / string 'TRUE'",
        dict(
            obj1=CIMProperty('Prop1', value='',
                             qualifiers={'Foo': True}),
            obj2=CIMProperty('Prop1', value='',
                             qualifiers={'Foo': 'TRUE'}),
            exp_hash_equal=False,
        ),
        None, None, True
    ),
    (
        "Qualifier with different types: bool False / string 'FALSE'",
        dict(
            obj1=CIMProperty('Prop1', value='',
                             qualifiers={'Foo': False}),
            obj2=CIMProperty('Prop1', value='',
                             qualifiers={'Foo': 'FALSE'}),
            exp_hash_equal=False,
        ),
        None, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    testcases_CIMProperty_hash)
@pytest_extensions.test_function
def test_CIMProperty_hash(
        desc, kwargs, exp_exc_types, exp_warn_types, condition):
    """
    All test cases for CIMProperty.__hash__().
    """

    obj1 = kwargs['obj1']
    obj2 = kwargs['obj2']

    # Double check they are different objects
    assert id(obj1) != id(obj2)

    # The code to be tested
    hash1 = hash(obj1)
    hash2 = hash(obj2)

    exp_hash_equal = kwargs['exp_hash_equal']

    assert (hash1 == hash2) == exp_hash_equal


class Test_CIMProperty_str(object):  # pylint: disable=too-few-public-methods
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


class Test_CIMProperty_repr(object):  # pylint: disable=too-few-public-methods
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


class Test_CIMProperty_tomof(object):
    """
    Test CIMProperty.tomof().
    """

    testcases = [
        # Testcases for CIMProperty.tomof().
        # Each testcase has these items:
        # * desc: Short testcase description.
        # * obj: Object to be tested.
        # * indent: Number of spaces to indent the generated MOF lines.
        # * is_instance: Create instance MOF instead of class MOF.
        # * exp_result: Expected MOF string, if expected to succeed.
        #     Exception type, if expected to fail.
        # * exp_warn_type: Expected warning type.
        #     None, if no warning expected.
        # * condition: Condition for testcase to run.
        (
            "class property, all components",
            CIMProperty(
                name='P1',
                value="abc",
                type='string',
                qualifiers=[
                    CIMQualifier('Q1', value='abc', type='string'),
                    CIMQualifier('Q2', value=Uint32(42), type='uint32'),
                ],
            ),
            False, 12,
            u"""\
               [Q1 ( "abc" ),
                Q2 ( 42 )]
            string P1 = "abc";\n""" \
            if CHECK_0_12_0 else \
            u"""\

                [Q1 ("abc"),
                Q2 (42)]
            string P1 = "abc";\n""",
            None, True
        ),
        (
            "class property, no qualifiers",
            CIMProperty(
                name='P1',
                value=None,
                type='string',
            ),
            False, 12,
            u"""\
            string P1;\n""" \
            if CHECK_0_12_0 else \
            u"""\

            string P1;\n""",
            None, True
        ),
        (
            "class property, one scalar single line qualifier",
            CIMProperty(
                name='P1',
                value=None,
                type='string',
                qualifiers=[
                    CIMQualifier('Q1', value='abc', type='string'),
                ],
            ),
            False, 12,
            u"""\
               [Q1 ( "abc" )]
            string P1;\n""" \
            if CHECK_0_12_0 else \
            u"""\

                [Q1 ("abc")]
            string P1;\n""",
            None, True
        ),
        (
            "class property, one scalar multi line qualifier",
            CIMProperty(
                name='P1',
                value=None,
                type='string',
                qualifiers=[
                    CIMQualifier('Q1', value=('abc def ' * 10 + 'z'),
                                 type='string'),
                ],
            ),
            False, 12,
            u"""\
               [Q1 (
                   "abc def abc def abc def abc def abc def abc def abc def "
                   "abc def abc def abc def z" )]
            string P1;\n""" \
            if CHECK_0_12_0 else \
            u"""\

                [Q1 (
                  "abc def abc def abc def abc def abc def abc def abc def "
                  "abc def abc def abc def z")]
            string P1;\n""",
            None, True
        ),
        (
            "class property, two scalar single line qualifiers",
            CIMProperty(
                name='P1',
                value=None,
                type='string',
                qualifiers=[
                    CIMQualifier('Q1', value='abc', type='string'),
                    CIMQualifier('Q2', value=Uint32(42), type='uint32'),
                ],
            ),
            False, 12,
            u"""\
               [Q1 ( "abc" ),
                Q2 ( 42 )]
            string P1;\n""" \
            if CHECK_0_12_0 else \
            u"""\

                [Q1 ("abc"),
                Q2 (42)]
            string P1;\n""",
            None, True
        ),
        (
            "class property, two scalar multi line qualifiers",
            CIMProperty(
                name='P1',
                value=None,
                type='string',
                qualifiers=[
                    CIMQualifier('Q1', value=('abc def ' * 10 + 'z'),
                                 type='string'),
                    CIMQualifier('Q2', value=('rst uvw ' * 10 + 'z'),
                                 type='string'),
                ],
            ),
            False, 12,
            u"""\
               [Q1 (
                   "abc def abc def abc def abc def abc def abc def abc def "
                   "abc def abc def abc def z" ),
                Q2 (
                   "rst uvw rst uvw rst uvw rst uvw rst uvw rst uvw rst uvw "
                   "rst uvw rst uvw rst uvw z" )]
            string P1;\n""" \
            if CHECK_0_12_0 else \
            u"""\

                [Q1 (
                  "abc def abc def abc def abc def abc def abc def abc def "
                  "abc def abc def abc def z"),
                Q2 (
                  "rst uvw rst uvw rst uvw rst uvw rst uvw rst uvw rst uvw "
                  "rst uvw rst uvw rst uvw z")]
            string P1;\n""",
            None, True
        ),
        (
            "class property, one array single line qualifier",
            CIMProperty(
                name='P1',
                value=None,
                type='string',
                qualifiers=[
                    CIMQualifier('Q1', value=['abc', 'def'], type='string'),
                ],
            ),
            False, 12,
            u"""\
               [Q1 { "abc", "def" }]
            string P1;\n""" \
            if CHECK_0_12_0 else \
            u"""\

                [Q1 { "abc", "def"}]
            string P1;\n""",
            None, True
        ),
        (
            "class property, one array multi line qualifier with short items",
            CIMProperty(
                name='P1',
                value=None,
                type='string',
                qualifiers=[
                    CIMQualifier(
                        'Q1',
                        value=['abcdef%02d' % i for i in range(0, 10)],
                        type='string'),
                ],
            ),
            False, 12,
            u"""\
               [Q1 { "abcdef00", "abcdef01", "abcdef02", "abcdef03",
                   "abcdef04", "abcdef05", "abcdef06", "abcdef07",
                   "abcdef08", "abcdef09" }]
            string P1;\n""" \
            if CHECK_0_12_0 else \
            u"""\

                [Q1 { "abcdef00", "abcdef01", "abcdef02", "abcdef03",
                  "abcdef04", "abcdef05", "abcdef06", "abcdef07",
                  "abcdef08", "abcdef09"}]
            string P1;\n""",
            None, True
        ),
        (
            "class property, one array multi line qualifier with long items",
            CIMProperty(
                name='P1',
                value=None,
                type='string',
                qualifiers=[
                    CIMQualifier(
                        'Q1',
                        value=['abc def ' * 10 + 'z%02d' % i
                               for i in range(0, 2)],
                        type='string'),
                ],
            ),
            False, 12,
            u"""\
               [Q1 {
                   "abc def abc def abc def abc def abc def abc def abc def "
                   "abc def abc def abc def z00",
                   "abc def abc def abc def abc def abc def abc def abc def "
                   "abc def abc def abc def z01" }]
            string P1;\n""" \
            if CHECK_0_12_0 else \
            u"""\

                [Q1 {
                  "abc def abc def abc def abc def abc def abc def abc def "
                  "abc def abc def abc def z00",
                  "abc def abc def abc def abc def abc def abc def abc def "
                  "abc def abc def abc def z01"}]
            string P1;\n""",
            None, True
        ),
        (
            "class property, type string, no default value",
            CIMProperty(
                name='P1',
                value=None,
                type='string',
            ),
            False, 12,
            u"""\
            string P1;\n""" \
            if CHECK_0_12_0 else \
            u"""\

            string P1;\n""",
            None, True
        ),
        (
            "class property, type string, with default value",
            CIMProperty(
                name='P1',
                value="abc",
                type='string',
            ),
            False, 12,
            u"""\
            string P1 = "abc";\n""" \
            if CHECK_0_12_0 else \
            u"""\

            string P1 = "abc";\n""",
            None, True
        ),
        (
            "class property, type char16, no default value",
            CIMProperty(
                name='P1',
                value=None,
                type='char16',
            ),
            False, 12,
            u"""\
            char16 P1;\n""" \
            if CHECK_0_12_0 else \
            u"""\

            char16 P1;\n""",
            None, True
        ),
        (
            "class property, type char16, with default value",
            CIMProperty(
                name='P1',
                value="a",
                type='char16',
            ),
            False, 12,
            u"""\
            char16 P1 = 'a';\n""" \
            if CHECK_0_12_0 else \
            u"""\

            char16 P1 = a;\n""",  # bug fixed in 0.12
            None, True
        ),
        (
            "class property, variable size array of uint32, no default value",
            CIMProperty(
                name='P1',
                value=None,
                type='uint32',
                is_array=True,
            ),
            False, 12,
            u"""\
            uint32 P1[];\n""" \
            if CHECK_0_12_0 else \
            u"""\

            uint32 P1[];\n""",
            None, True
        ),
        (
            "class property, variable size array of uint32, with default value",
            CIMProperty(
                name='P1',
                value=[1, 2, 3],
                type='uint32',
                is_array=True,
            ),
            False, 12,
            u"""\
            uint32 P1[] = { 1, 2, 3 };\n""" \
            if CHECK_0_12_0 else \
            u"""\

            uint32 P1[] = {1, 2, 3};\n""",
            None, True
        ),
        (
            "class property, fixed size array of sint64, no default value",
            CIMProperty(
                name='P1',
                value=None,
                type='sint64',
                is_array=True,
                array_size=5,
            ),
            False, 12,
            u"""\
            sint64 P1[5];\n""" \
            if CHECK_0_12_0 else \
            u"""\

            sint64 P1[5];\n""",
            None, True
        ),
        (
            "class property, type reference, no default value",
            CIMProperty(
                name='P1',
                value=None,
                type='reference',
                reference_class="RC",
            ),
            False, 12,
            u"""\
            RC REF P1;\n""" \
            if CHECK_0_12_0 else \
            u"""\

            RC REF P1;\n""",
            None, True
        ),
        (
            "class property, type reference, with default value",
            CIMProperty(
                name='P1',
                value=CIMInstanceName("RC", dict(k1='abc')),
                type='reference',
                reference_class="RC",
            ),
            False, 12,
            u"""\
            RC REF P1 = "/:RC.k1=\\"abc\\"";\n""" \
            if CHECK_0_12_0 else \
            u"""\

            RC REF P1 = RC.k1="abc";\n""",    # bug fixed in 0.12
            None, True
        ),
        (
            "instance property, all components",
            CIMProperty(
                name='P1',
                value=["abc", "def"],
                type='string',
                is_array=True,
                array_size=5,
                qualifiers=[
                    CIMQualifier('Q1', value='abc', type='string'),
                    CIMQualifier('Q2', value=Uint32(42), type='uint32'),
                ],
            ),
            True, 12,
            u"""\
            P1 = { "abc", "def" };\n""" \
            if CHECK_0_12_0 else \
            u"""\
            P1 =  = {"abc", "def"};\n""",  # bug: '= =', fixed in 0.12
            None, True
        ),
        (
            "instance string property, with NULL value",
            CIMProperty(
                name='P1',
                value=None,
                type='string',
            ),
            True, 12,
            u"""\
            P1 = NULL;\n""",
            None, True
        ),
        (
            "instance string property, with multi-line scalar value",
            CIMProperty(
                name='P1',
                value=('abc def ' * 10 + 'z'),
                type='string',
            ),
            True, 12,
            # pylint: disable=line-too-long
            u"""\
            P1 =
               "abc def abc def abc def abc def abc def abc def abc def abc "
               "def abc def abc def z";\n""" \
            if CHECK_0_12_0 else \
            u"""\
            P1 = "abc def abc def abc def abc def abc def abc def abc def abc def "
            "abc def abc def z";\n""",  # noqa: E501
            None, True
        ),
        (
            "instance string array property, with multi-line short items",
            CIMProperty(
                name='P1',
                value=['abcdef%02d' % i for i in range(0, 10)],
                type='string',
            ),
            True, 12,
            # pylint: disable=line-too-long
            u"""\
            P1 = { "abcdef00", "abcdef01", "abcdef02", "abcdef03", "abcdef04",
               "abcdef05", "abcdef06", "abcdef07", "abcdef08", "abcdef09" };\n""" \
            if CHECK_0_12_0 else \
            u"""\
            P1 =  = {
                "abcdef00",
                "abcdef01",
                "abcdef02",
                "abcdef03",
                "abcdef04",
                "abcdef05",
                "abcdef06",
                "abcdef07",
                "abcdef08",
                "abcdef09"};\n""",  # noqa: E501  # bug: '= =', fixed in 0.12
            None, True
        ),
        (
            "instance uint32 property",
            CIMProperty(
                name='P1',
                value=42,
                type='uint32',
            ),
            True, 12,
            u"""\
            P1 = 42;\n""" \
            if CHECK_0_12_0 else \
            u"""\
            P1 = 42;\n""",
            None, True
        ),
        (
            "instance uint32 array property, single-line",
            CIMProperty(
                name='P1',
                value=list(range(0, 10)),
                type='uint32',
                is_array=True,
            ),
            True, 12,
            u"""\
            P1 = { 0, 1, 2, 3, 4, 5, 6, 7, 8, 9 };\n""" \
            if CHECK_0_12_0 else \
            u"""\
            P1 =  = {0, 1, 2, 3, 4, 5, 6, 7, 8, 9};\n""",  # bug fixed in 0.12
            None, True
        ),
        (
            "instance uint32 array property, multi-line",
            CIMProperty(
                name='P1',
                value=list(range(0, 20)),
                type='uint32',
                is_array=True,
            ),
            True, 12,
            u"""\
            P1 = { 0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16,
               17, 18, 19 };\n""" \
            if CHECK_0_12_0 else \
            u"""\
            P1 =  = {
                0,
                1,
                2,
                3,
                4,
                5,
                6,
                7,
                8,
                9,
                10,
                11,
                12,
                13,
                14,
                15,
                16,
                17,
                18,
                19};\n""",  # bug fixed in 0.12
            None, True
        ),
    ]

    @pytest.mark.parametrize(
        "desc, obj, is_instance, indent, exp_result, exp_warn_type, condition",
        testcases)
    def test_CIMProperty_tomof(
            self, desc, obj, is_instance, indent, exp_result, exp_warn_type,
            condition):
        """All test cases for CIMProperty.tomof()."""

        if not condition:
            pytest.skip("Condition for test case not met")

        if isinstance(exp_result, type) and issubclass(exp_result, Exception):
            # We expect an exception
            exp_exc_type = exp_result
            exp_mof = None
        else:
            # We expect the code to return
            exp_exc_type = None
            exp_mof = exp_result

        if condition == 'pdb':
            import pdb
            pdb.set_trace()

        if exp_warn_type:
            with pytest.warns(exp_warn_type) as rec_warnings:
                if exp_exc_type:
                    with pytest.raises(exp_exc_type):

                        # The code to be tested
                        mof = obj.tomof(is_instance, indent)

                else:

                    # The code to be tested
                    mof = obj.tomof(is_instance, indent)

            assert len(rec_warnings) == 1

        else:
            if exp_exc_type:
                with pytest.raises(exp_exc_type):

                    # The code to be tested
                    mof = obj.tomof(is_instance, indent)

            else:

                # The code to be tested
                mof = obj.tomof(is_instance, indent)

        if exp_mof:

            assert isinstance(mof, six.text_type)
            assert mof == exp_mof

    def test_CIMProperty_tomof_fail1(self):
        """CIMProperty.tomof() failure: Provoke TypeError with string"""

        if not CHECK_0_12_0:
            pytest.skip("Condition for test case not met")

        datetime_dt = datetime(2018, 1, 5, 15, 0, 0, 0)
        datetime_obj = CIMDateTime(datetime_dt)

        obj = CIMProperty(name='P1', value=datetime_obj, type='datetime')

        # Set an inconsistent CIM type. This is not prevented at this point.
        obj.type = 'string'
        assert obj.type == 'string'

        with pytest.raises(TypeError):

            # The code to be tested
            obj.tomof(is_instance=False)

    def test_CIMProperty_tomof_success1(self):
        """CIMProperty.tomof(): Use plain float value"""

        if not CHECK_0_12_0:
            pytest.skip("Condition for test case not met")

        obj = CIMProperty(name='P1', value=42.1, type='real32')
        assert isinstance(obj.value, Real32)

        # Set the value back to a plain float.
        obj.value = 42.1
        assert isinstance(obj.value, float)

        # The code to be tested
        mof = obj.tomof(is_instance=False)

        assert mof == u"real32 P1 = 42.1;\n"


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

        # Name tests
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

        # Value/type tests
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

        # Check documented examples
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
            with pytest.warns(exp_warn_type) as rec_warnings:

                # The code to be tested
                obj = CIMQualifier(**kwargs)

            assert len(rec_warnings) == 1

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
            "Verify that an invalid type fails (since 0.12)",
            dict(name='FooQual', value=None, type='xxx'),
            ValueError, CHECK_0_12_0
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


testcases_CIMQualifier_hash = [

    # Each testcase tuple has these items:
    # * desc: Short testcase description.
    # * kwargs: Input arguments for test function, as a dict:
    #   * obj1: CIMQualifier object #1 to be tested.
    #   * obj2: CIMQualifier object #2 to be tested.
    #   * exp_hash_equal: Expected equality of the object hash values.
    # * exp_exc_types: Expected exception type(s), or None.
    # * exp_warn_types: Expected warning type(s), or None.
    # * condition: Boolean condition for testcase to run, or 'pdb' for debugger

    # Name tests
    (
        "Name, equal with same lexical case",
        dict(
            obj1=CIMQualifier('Qual1', value=''),
            obj2=CIMQualifier('Qual1', value=''),
            exp_hash_equal=True,
        ),
        None, None, True
    ),
    (
        "Name, equal with different lexical case",
        dict(
            obj1=CIMQualifier('Qual1', value=''),
            obj2=CIMQualifier('quAL1', value=''),
            exp_hash_equal=True,
        ),
        None, None, True
    ),
    (
        "Name, different",
        dict(
            obj1=CIMQualifier('Qual1', value=''),
            obj2=CIMQualifier('Qual1_x', value=''),
            exp_hash_equal=False,
        ),
        None, None, True
    ),

    # Value tests
    (
        "Value, strings with different lexical case",
        dict(
            obj1=CIMQualifier('Qual1', value='abc'),
            obj2=CIMQualifier('Qual1', value='Abc'),
            exp_hash_equal=False,
        ),
        None, None, True
    ),
    (
        "Value, strings with None / string",
        dict(
            obj1=CIMQualifier('Qual1', value=None, type='string'),
            obj2=CIMQualifier('Qual1', value='abc', type='string'),
            exp_hash_equal=False,
        ),
        None, None, True
    ),
    (
        "Value, strings with string / None",
        dict(
            obj1=CIMQualifier('Qual1', value='abc', type='string'),
            obj2=CIMQualifier('Qual1', value=None, type='string'),
            exp_hash_equal=False,
        ),
        None, None, True
    ),
    (
        "Value, strings with None / None",
        dict(
            obj1=CIMQualifier('Qual1', value=None, type='string'),
            obj2=CIMQualifier('Qual1', value=None, type='string'),
            exp_hash_equal=True,
        ),
        None, None, True
    ),

    # Type tests
    (
        "Type, different",
        dict(
            obj1=CIMQualifier('Qual1', value=7, type='uint8'),
            obj2=CIMQualifier('Qual1', value=7, type='sint8'),
            exp_hash_equal=False,
        ),
        None, None, True
    ),

    # Propagated tests
    (
        "Propagated, equal",
        dict(
            obj1=CIMQualifier('Qual1', value=None, type='string',
                              propagated=True),
            obj2=CIMQualifier('Qual1', value=None, type='string',
                              propagated=True),
            exp_hash_equal=True,
        ),
        None, None, True
    ),
    (
        "Propagated, different",
        dict(
            obj1=CIMQualifier('Qual1', value=None, type='string',
                              propagated=True),
            obj2=CIMQualifier('Qual1', value=None, type='string',
                              propagated=False),
            exp_hash_equal=False,
        ),
        None, None, True
    ),

    # Overridable tests
    (
        "Overridable, equal",
        dict(
            obj1=CIMQualifier('Qual1', value=None, type='string',
                              overridable=True),
            obj2=CIMQualifier('Qual1', value=None, type='string',
                              overridable=True),
            exp_hash_equal=True,
        ),
        None, None, True
    ),
    (
        "Overridable, different",
        dict(
            obj1=CIMQualifier('Qual1', value=None, type='string',
                              overridable=True),
            obj2=CIMQualifier('Qual1', value=None, type='string',
                              overridable=False),
            exp_hash_equal=False,
        ),
        None, None, True
    ),

    # Tosubclass tests
    (
        "Tosubclass, equal",
        dict(
            obj1=CIMQualifier('Qual1', value=None, type='string',
                              tosubclass=True),
            obj2=CIMQualifier('Qual1', value=None, type='string',
                              tosubclass=True),
            exp_hash_equal=True,
        ),
        None, None, True
    ),
    (
        "Tosubclass, different",
        dict(
            obj1=CIMQualifier('Qual1', value=None, type='string',
                              tosubclass=True),
            obj2=CIMQualifier('Qual1', value=None, type='string',
                              tosubclass=False),
            exp_hash_equal=False,
        ),
        None, None, True
    ),

    # Toinstance tests
    (
        "Toinstance, equal",
        dict(
            obj1=CIMQualifier('Qual1', value=None, type='string',
                              toinstance=True),
            obj2=CIMQualifier('Qual1', value=None, type='string',
                              toinstance=True),
            exp_hash_equal=True,
        ),
        None, None, True
    ),
    (
        "Toinstance, different",
        dict(
            obj1=CIMQualifier('Qual1', value=None, type='string',
                              toinstance=True),
            obj2=CIMQualifier('Qual1', value=None, type='string',
                              toinstance=False),
            exp_hash_equal=False,
        ),
        None, None, True
    ),

    # Translatable tests
    (
        "Translatable, equal",
        dict(
            obj1=CIMQualifier('Qual1', value=None, type='string',
                              translatable=True),
            obj2=CIMQualifier('Qual1', value=None, type='string',
                              translatable=True),
            exp_hash_equal=True,
        ),
        None, None, True
    ),
    (
        "Translatable, different",
        dict(
            obj1=CIMQualifier('Qual1', value=None, type='string',
                              translatable=True),
            obj2=CIMQualifier('Qual1', value=None, type='string',
                              translatable=False),
            exp_hash_equal=False,
        ),
        None, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    testcases_CIMQualifier_hash)
@pytest_extensions.test_function
def test_CIMQualifier_hash(
        desc, kwargs, exp_exc_types, exp_warn_types, condition):
    """
    All test cases for CIMQualifier.__hash__().
    """

    obj1 = kwargs['obj1']
    obj2 = kwargs['obj2']

    # Double check they are different objects
    assert id(obj1) != id(obj2)

    # The code to be tested
    hash1 = hash(obj1)
    hash2 = hash(obj2)

    exp_hash_equal = kwargs['exp_hash_equal']

    assert (hash1 == hash2) == exp_hash_equal


class Test_CIMQualifier_str(object):  # pylint: disable=too-few-public-methods
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


class Test_CIMQualifier_repr(object):  # pylint: disable=too-few-public-methods
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


class Test_CIMQualifier_tomof(object):  # pylint: disable=too-few-public-methods
    """
    Test CIMQualifier.tomof().
    """

    testcases = [
        # Testcases for CIMQualifier.tomof().
        # Each testcase has these items:
        # * desc: Short testcase description.
        # * obj: Object to be tested.
        # * indent: Number of spaces to indent the generated MOF lines.
        # * exp_result: Expected MOF string, if expected to succeed.
        #     Exception type, if expected to fail.
        # * exp_warn_type: Expected warning type.
        #     None, if no warning expected.
        # * condition: Condition for testcase to run.
        (
            "all components",
            CIMQualifier(
                name='Q1',
                value=["abc"],
                type='string',
                propagated=True,
                overridable=True,
                tosubclass=True,
                toinstance=True,
                translatable=True,
            ),
            12,
            u"""Q1 { "abc" }""" \
            if CHECK_0_12_0 else \
            u"""Q1 { "abc"}""",
            None, True
        ),
        (
            "string type, NULL value",
            CIMQualifier(
                name='Q1',
                value=None,
                type='string',
            ),
            12,
            u"""Q1 ( NULL )""" \
            if CHECK_0_12_0 else \
            u"""Q1 (None)""",
            None, True
        ),
        (
            "string type, value with escape sequences dq,sq,bs",
            CIMQualifier(
                name='Q1',
                value="dq=\",sq=\',bs=\\",
                type='string',
            ),
            12,
            u"""Q1 ( "dq=\\",sq=\\',bs=\\\\" )""" \
            if CHECK_0_12_0 else \
            u"""Q1 ("dq=\\",sq=\\',bs=\\\\")""",
            None, True
        ),
        (
            "string type, value with escape sequences bt,tb,nl",
            CIMQualifier(
                name='Q1',
                value="bt=\b,tb=\t,nl=\n",
                type='string',
            ),
            12,
            u"""Q1 ( "bt=\\b,tb=\\t,nl=\\n" )""" \
            if CHECK_0_12_0 else \
            u"""Q1 ("bt=\\b,tb=\\t,nl=\\n")""",
            None, True
        ),
        (
            "string type, value with escape sequences vt,cr",
            CIMQualifier(
                name='Q1',
                value="vt=\f,cr=\r",
                type='string',
            ),
            12,
            u"""Q1 ( "vt=\\f,cr=\\r" )""" \
            if CHECK_0_12_0 else \
            u"""Q1 ("vt=\\f,cr=\\r")""",
            None, True
        ),
        (
            "string array with a value of two items",
            CIMQualifier(
                name='Q1',
                value=["abc", "def"],
                type='string',
            ),
            12,
            u"""Q1 { "abc", "def" }""" \
            if CHECK_0_12_0 else \
            u"""Q1 { abc, def}""",
            None, CHECK_0_12_0
        ),
        (
            "string array with a value of two items with one being None",
            CIMQualifier(
                name='Q1',
                value=["abc", None],
                type='string',
            ),
            12,
            u"""Q1 { "abc", NULL }""" \
            if CHECK_0_12_0 else \
            u"""Q1 { abc, None}""",
            None, CHECK_0_12_0
        ),
        (
            "string type with multi line value",
            CIMQualifier(
                name='Q1',
                value=('abc def ' * 10 + 'z'),
                type='string',
            ),
            12,
            u"""Q1 (
            "abc def abc def abc def abc def abc def abc def abc def abc def "
            "abc def abc def z" )""" \
            if CHECK_0_12_0 else \
            u"""Q1 (
            "abc def abc def abc def abc def abc def abc def abc def abc def "
            "abc def abc def z")""",
            None, True
        ),
        (
            "string array type with multi line value with short items",
            CIMQualifier(
                name='Q1',
                value=['abcdef%02d' % i for i in range(0, 10)],
                type='string',
            ),
            12,
            # pylint: disable=line-too-long
            u"""Q1 { "abcdef00", "abcdef01", "abcdef02", "abcdef03", "abcdef04", "abcdef05",
            "abcdef06", "abcdef07", "abcdef08", "abcdef09" }""" \
            if CHECK_0_12_0 else \
            u"""Q1 { "abcdef00", "abcdef01", "abcdef02", "abcdef03", "abcdef04",
            "abcdef05", "abcdef06", "abcdef07", "abcdef08", "abcdef09"}""",  # noqa: E501
            None, True
        ),
        (
            "string array type with with long items",
            CIMQualifier(
                name='Q1',
                value=['abc def ' * 10 + 'z%02d' % i for i in range(0, 2)],
                type='string',
            ),
            12,
            u"""Q1 {
            "abc def abc def abc def abc def abc def abc def abc def abc def "
            "abc def abc def z00",
            "abc def abc def abc def abc def abc def abc def abc def abc def "
            "abc def abc def z01" }""" \
            if CHECK_0_12_0 else \
            u"""Q1 {
            "abc def abc def abc def abc def abc def abc def abc def abc def "
            "abc def abc def z00",
            "abc def abc def abc def abc def abc def abc def abc def abc def "
            "abc def abc def z01"}""",
            None, True
        ),
        (
            "char16 type, value nl",
            CIMQualifier(
                name='Q1',
                value="\n",
                type='char16',
            ),
            12,
            u"""Q1 ( '\\n' ) """,
            None, False
            # TODO 01/18 AM Enable test case once char16 produces single quotes
        ),
        (
            "boolean type, value False",
            CIMQualifier(
                name='Q1',
                value=False,
                type='boolean',
            ),
            12,
            u"""Q1 ( false )""" \
            if CHECK_0_12_0 else \
            u"""Q1 (False)""",
            None, True
        ),
        (
            "uint32 type, value 42",
            CIMQualifier(
                name='Q1',
                value=Uint32(42),
                type='uint32',
            ),
            12,
            u"""Q1 ( 42 )""" \
            if CHECK_0_12_0 else \
            u"""Q1 (42)""",
            None, True
        ),
        (
            "real32 type, value 42.1",
            CIMQualifier(
                name='Q1',
                value=Real32(42.1),
                type='real32',
            ),
            12,
            u"""Q1 ( 42.1 )""",
            None, CHECK_0_12_0  # Unpredictable string before 0.12
        ),
        (
            "datetime type, with a value",
            CIMQualifier(
                name='Q1',
                value=CIMDateTime('20140924193040.654321+120'),
                type='datetime',
            ),
            12,
            u"""Q1 ( "20140924193040.654321+120" )""" \
            if CHECK_0_12_0 else \
            u"""Q1 (20140924193040.654321+120)""",
            None, True
        ),
        (
            "flavors ToSubclass EnableOverride",
            CIMQualifier(
                name='Q1',
                value='',
                type='string',
                overridable=True,
                tosubclass=True,
            ),
            12,
            u"""Q1 ( "" )""" \
            if CHECK_0_12_0 else \
            u"""Q1 ("")""",
            None, True
        ),
        (
            "flavor ToSubclass DisableOverride",
            CIMQualifier(
                name='Q1',
                value='',
                type='string',
                overridable=False,
                tosubclass=True,
            ),
            12,
            u"""Q1 ( "" )""" \
            if CHECK_0_12_0 else \
            u"""Q1 ("")""",
            None, True
        ),
        (
            "flavor Restricted",
            CIMQualifier(
                name='Q1',
                value='',
                type='string',
                tosubclass=False,
            ),
            12,
            u"""Q1 ( "" )""" \
            if CHECK_0_12_0 else \
            u"""Q1 ("")""",
            None, True
        ),
        (
            "flavor Translatable",
            CIMQualifier(
                name='Q1',
                value='',
                type='string',
                translatable=True,
            ),
            12,
            u"""Q1 ( "" )""" \
            if CHECK_0_12_0 else \
            u"""Q1 ("")""",
            None, True
        ),
        (
            "flavor ToInstance (not in DSP0004)",
            CIMQualifier(
                name='Q1',
                value='',
                type='string',
                toinstance=True,
            ),
            12,
            u"""Q1 ( "" )""" \
            if CHECK_0_12_0 else \
            u"""Q1 ("")""",
            None, True
        ),
    ]

    @pytest.mark.parametrize(
        "desc, obj, indent, exp_result, exp_warn_type, condition",
        testcases)
    def test_CIMQualifier_tomof(
            self, desc, obj, indent, exp_result, exp_warn_type, condition):
        """All test cases for CIMQualifier.tomof()."""

        if not condition:
            pytest.skip("Condition for test case not met")

        if isinstance(exp_result, type) and issubclass(exp_result, Exception):
            # We expect an exception
            exp_exc_type = exp_result
            exp_mof = None
        else:
            # We expect the code to return
            exp_exc_type = None
            exp_mof = exp_result

        if condition == 'pdb':
            import pdb
            pdb.set_trace()

        if exp_warn_type:
            with pytest.warns(exp_warn_type) as rec_warnings:
                if exp_exc_type:
                    with pytest.raises(exp_exc_type):

                        # The code to be tested
                        mof = obj.tomof(indent)

                else:

                    # The code to be tested
                    mof = obj.tomof(indent)

            assert len(rec_warnings) == 1

        else:
            if exp_exc_type:
                with pytest.raises(exp_exc_type):

                    # The code to be tested
                    mof = obj.tomof(indent)

            else:

                # The code to be tested
                mof = obj.tomof(indent)

        if exp_mof:

            assert isinstance(mof, six.text_type)
            assert mof == exp_mof


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

        # Classname tests
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

        # Namespace tests
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
            "Verify that one leading and trailing slash in namespace get "
            "stripped",
            dict(
                classname='CIM_Foo',
                namespace='/root/cimv2/'),
            dict(
                classname=u'CIM_Foo',
                namespace=u'root/cimv2'),
            None, True
        ),
        (
            "Verify that two leading and trailing slashes in namespace get "
            "stripped",
            dict(
                classname='CIM_Foo',
                namespace='//root/cimv2//'),
            dict(
                classname=u'CIM_Foo',
                namespace=u'root/cimv2'),
            None, True
        ),

        # Host tests
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
            with pytest.warns(exp_warn_type) as rec_warnings:

                # The code to be tested
                obj = CIMClassName(**kwargs)

            assert len(rec_warnings) == 1

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


testcases_CIMClassName_hash = [

    # Each testcase tuple has these items:
    # * desc: Short testcase description.
    # * kwargs: Input arguments for test function, as a dict:
    #   * obj1: CIMClassName object #1 to be tested.
    #   * obj2: CIMClassName object #2 to be tested.
    #   * exp_hash_equal: Expected equality of the object hash values.
    # * exp_exc_types: Expected exception type(s), or None.
    # * exp_warn_types: Expected warning type(s), or None.
    # * condition: Boolean condition for testcase to run, or 'pdb' for debugger

    # Classname tests
    (
        "Classname, equal with same lexical case",
        dict(
            obj1=CIMClassName('CIM_Foo'),
            obj2=CIMClassName('CIM_Foo'),
            exp_hash_equal=True,
        ),
        None, None, True
    ),
    (
        "Classname, equal with different lexical case",
        dict(
            obj1=CIMClassName('CIM_Foo'),
            obj2=CIMClassName('ciM_foO'),
            exp_hash_equal=True,
        ),
        None, None, True
    ),
    (
        "Classname, different",
        dict(
            obj1=CIMClassName('CIM_Foo'),
            obj2=CIMClassName('CIM_Foo_x'),
            exp_hash_equal=False,
        ),
        None, None, True
    ),

    # Host tests
    (
        "Host name, equal with same lexical case",
        dict(
            obj1=CIMClassName('CIM_Foo', host='woot.com'),
            obj2=CIMClassName('CIM_Foo', host='woot.Com'),
            exp_hash_equal=True,
        ),
        None, None, True
    ),
    (
        "Host name, equal with different lexical case",
        dict(
            obj1=CIMClassName('CIM_Foo', host='woot.com'),
            obj2=CIMClassName('CIM_Foo', host='Woot.Com'),
            exp_hash_equal=True,
        ),
        None, None, True
    ),
    (
        "Host name, different with None / string",
        dict(
            obj1=CIMClassName('CIM_Foo', host=None),
            obj2=CIMClassName('CIM_Foo', host='woot.com'),
            exp_hash_equal=False,
        ),
        None, None, True
    ),
    (
        "Host name, different with string / None",
        dict(
            obj1=CIMClassName('CIM_Foo', host='woot.com'),
            obj2=CIMClassName('CIM_Foo', host=None),
            exp_hash_equal=False,
        ),
        None, None, True
    ),
    (
        "Host name, equal with None / None",
        dict(
            obj1=CIMClassName('CIM_Foo', host=None),
            obj2=CIMClassName('CIM_Foo', host=None),
            exp_hash_equal=True,
        ),
        None, None, True
    ),

    # Namespace tests
    (
        "Namespace, equal with same lexical case",
        dict(
            obj1=CIMClassName('CIM_Foo', namespace='root/cimv2'),
            obj2=CIMClassName('CIM_Foo', namespace='root/cimv2'),
            exp_hash_equal=True,
        ),
        None, None, True
    ),
    (
        "Namespace, equal with different lexical case",
        dict(
            obj1=CIMClassName('CIM_Foo', namespace='root/cimv2'),
            obj2=CIMClassName('CIM_Foo', namespace='Root/CIMv2'),
            exp_hash_equal=True,
        ),
        None, None, True
    ),
    (
        "Namespace, different",
        dict(
            obj1=CIMClassName('CIM_Foo', namespace='root/cimv2'),
            obj2=CIMClassName('CIM_Foo', namespace='abc'),
            exp_hash_equal=False,
        ),
        None, None, True
    ),
    (
        "Namespace, different with None / string",
        dict(
            obj1=CIMClassName('CIM_Foo', namespace=None),
            obj2=CIMClassName('CIM_Foo', namespace='root/cimv2'),
            exp_hash_equal=False,
        ),
        None, None, True
    ),
    (
        "Namespace, different with string / None",
        dict(
            obj1=CIMClassName('CIM_Foo', namespace='root/cimv2'),
            obj2=CIMClassName('CIM_Foo', namespace=None),
            exp_hash_equal=False,
        ),
        None, None, True
    ),
    (
        "Namespace, equal with None / None",
        dict(
            obj1=CIMClassName('CIM_Foo', namespace=None),
            obj2=CIMClassName('CIM_Foo', namespace=None),
            exp_hash_equal=True,
        ),
        None, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    testcases_CIMClassName_hash)
@pytest_extensions.test_function
def test_CIMClassName_hash(
        desc, kwargs, exp_exc_types, exp_warn_types, condition):
    """
    All test cases for CIMClassName.__hash__().
    """

    obj1 = kwargs['obj1']
    obj2 = kwargs['obj2']

    # Double check they are different objects
    assert id(obj1) != id(obj2)

    # The code to be tested
    hash1 = hash(obj1)
    hash2 = hash(obj2)

    exp_hash_equal = kwargs['exp_hash_equal']

    assert (hash1 == hash2) == exp_hash_equal


class Test_CIMClassName_repr(object):  # pylint: disable=too-few-public-methods
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
    # pylint: disable=too-few-public-methods
    """
    Test CIMClassName.from_wbem_uri().
    """

    testcases = [
        # Testcases for CIMClassName.from_wbem_uri().
        # Each testcase has these items:
        # * desc: Short testcase description.
        # * uri: WBEM URI string to be tested.
        # * exp_result: Dict of all expected attributes of resulting object,
        #     if expected to succeed. Exception type, if expected to fail.
        # * exp_warn_type: Expected warning type.
        #     None, if no warning expected.
        # * condition: Condition for testcase to run.
        (
            "all components, normal case",
            'https://10.11.12.13:5989/root/cimv2:CIM_Foo',
            dict(
                classname=u'CIM_Foo',
                namespace=u'root/cimv2',
                host=u'10.11.12.13:5989'),
            None, CHECK_0_12_0
        ),
        (
            "no authority",
            'https:/root/cimv2:CIM_Foo',
            dict(
                classname=u'CIM_Foo',
                namespace=u'root/cimv2',
                host=None),
            None, CHECK_0_12_0
        ),
        (
            "authority with user:password",
            'https://jdd:test@10.11.12.13:5989/root/cimv2:CIM_Foo',
            dict(
                classname=u'CIM_Foo',
                namespace=u'root/cimv2',
                host=u'jdd:test@10.11.12.13:5989'),
            None, CHECK_0_12_0
        ),
        (
            "authority with user (no password)",
            'https://jdd@10.11.12.13:5989/root/cimv2:CIM_Foo',
            dict(
                classname=u'CIM_Foo',
                namespace=u'root/cimv2',
                host=u'jdd@10.11.12.13:5989'),
            None, CHECK_0_12_0
        ),
        (
            "authority without port",
            'https://10.11.12.13/root/cimv2:CIM_Foo',
            dict(
                classname=u'CIM_Foo',
                namespace=u'root/cimv2',
                host=u'10.11.12.13'),
            None, CHECK_0_12_0
        ),
        (
            "authority with IPv6 address",
            'https://[10:11:12:13]/root/cimv2:CIM_Foo',
            dict(
                classname=u'CIM_Foo',
                namespace=u'root/cimv2',
                host=u'[10:11:12:13]'),
            None, CHECK_0_12_0
        ),
        (
            "authority with IPv6 address and port",
            'https://[10:11:12:13]:5989/root/cimv2:CIM_Foo',
            dict(
                classname=u'CIM_Foo',
                namespace=u'root/cimv2',
                host=u'[10:11:12:13]:5989'),
            None, CHECK_0_12_0
        ),
        (
            "no namespace type",
            '//10.11.12.13:5989/root/cimv2:CIM_Foo',
            dict(
                classname=u'CIM_Foo',
                namespace=u'root/cimv2',
                host=u'10.11.12.13:5989'),
            None, CHECK_0_12_0
        ),
        (
            "namespace type http",
            'http://10.11.12.13:5989/root/cimv2:CIM_Foo',
            dict(
                classname=u'CIM_Foo',
                namespace=u'root/cimv2',
                host=u'10.11.12.13:5989'),
            None, CHECK_0_12_0
        ),
        (
            "namespace type upper case HTTP",
            'HTTP://10.11.12.13:5989/root/cimv2:CIM_Foo',
            dict(
                classname=u'CIM_Foo',
                namespace=u'root/cimv2',
                host=u'10.11.12.13:5989'),
            None, CHECK_0_12_0
        ),
        (
            "namespace type mixed case HttpS",
            'HttpS://10.11.12.13:5989/root/cimv2:CIM_Foo',
            dict(
                classname=u'CIM_Foo',
                namespace=u'root/cimv2',
                host=u'10.11.12.13:5989'),
            None, CHECK_0_12_0
        ),
        (
            "namespace type cimxml-wbem",
            'cimxml-wbem://10.11.12.13:5989/root/cimv2:CIM_Foo',
            dict(
                classname=u'CIM_Foo',
                namespace=u'root/cimv2',
                host=u'10.11.12.13:5989'),
            None, CHECK_0_12_0
        ),
        (
            "namespace type cimxml-wbems",
            'cimxml-wbems://10.11.12.13:5989/root/cimv2:CIM_Foo',
            dict(
                classname=u'CIM_Foo',
                namespace=u'root/cimv2',
                host=u'10.11.12.13:5989'),
            None, CHECK_0_12_0
        ),
        (
            "unknown namespace type",
            'xyz://10.11.12.13:5989/root/cimv2:CIM_Foo',
            dict(
                classname=u'CIM_Foo',
                namespace=u'root/cimv2',
                host=u'10.11.12.13:5989'),
            UserWarning, CHECK_0_12_0
        ),
        (
            "local WBEM URI (no namespace type, no authority)",
            '/root/cimv2:CIM_Foo',
            dict(
                classname=u'CIM_Foo',
                namespace=u'root/cimv2',
                host=None),
            None, CHECK_0_12_0
        ),
        (
            "local WBEM URI (with missing initial slash)",
            'root/cimv2:CIM_Foo',
            dict(
                classname=u'CIM_Foo',
                namespace=u'root/cimv2',
                host=None),
            None, CHECK_0_12_0
        ),
        (
            "local WBEM URI with only class name",
            '/:CIM_Foo',
            dict(
                classname=u'CIM_Foo',
                namespace=None,
                host=None),
            None, CHECK_0_12_0
        ),
        (
            "local WBEM URI with only class name (with missing initial slash)",
            ':CIM_Foo',
            dict(
                classname=u'CIM_Foo',
                namespace=None,
                host=None),
            None, CHECK_0_12_0
        ),
        (
            "local WBEM URI with namespace that has only one component",
            '/root:CIM_Foo',
            dict(
                classname=u'CIM_Foo',
                namespace=u'root',
                host=None),
            None, CHECK_0_12_0
        ),
        (
            "local WBEM URI with namespace that has three components",
            '/root/cimv2/test:CIM_Foo',
            dict(
                classname=u'CIM_Foo',
                namespace=u'root/cimv2/test',
                host=None),
            None, CHECK_0_12_0
        ),
        (
            "missing delimiter / before authority",
            'https:/10.11.12.13/cimv2:CIM_Foo',
            ValueError,
            None, CHECK_0_12_0
        ),
        (
            "invalid char ; in authority",
            'https://10.11.12.13;5989/cimv2:CIM_Foo',
            ValueError,
            None, CHECK_0_12_0
        ),
        (
            "delimiter / before namespace replaced with :",
            'https://10.11.12.13:5989:root:CIM_Foo',
            ValueError,
            None, CHECK_0_12_0
        ),
        (
            "delimiter : before classname replaced with .",
            'https://10.11.12.13:5989/root.CIM_Foo',
            ValueError,
            None, CHECK_0_12_0
        ),
        (
            "invalid '/' between namespace and classname",
            'https://10.11.12.13:5989/cimv2/CIM_Foo',
            ValueError,
            None, CHECK_0_12_0
        ),
        (
            "class name missing",
            'https://10.11.12.13:5989/root/cimv2',
            ValueError,
            None, CHECK_0_12_0
        ),
        (
            "instance path used as class path",
            'https://10.11.12.13:5989/root:CIM_Foo.k1="v1"',
            ValueError,
            None, CHECK_0_12_0
        ),
    ]

    @pytest.mark.parametrize(
        "desc, uri, exp_result, exp_warn_type, condition",
        testcases)
    def test_CIMClassName_from_wbem_uri(
            self, desc, uri, exp_result, exp_warn_type, condition):
        """All test cases for CIMClassName.from_wbem_uri()."""

        if not condition:
            pytest.skip("Condition for test case not met")

        if isinstance(exp_result, type) and issubclass(exp_result, Exception):
            # We expect an exception
            exp_exc_type = exp_result
            exp_attrs = None
        else:
            # We expect the code to return
            exp_exc_type = None
            exp_attrs = exp_result

        if condition == 'pdb':
            import pdb
            pdb.set_trace()

        if exp_warn_type:
            with pytest.warns(exp_warn_type) as rec_warnings:
                if exp_exc_type:
                    with pytest.raises(exp_exc_type):

                        # The code to be tested
                        obj = CIMClassName.from_wbem_uri(uri)

                else:

                    # The code to be tested
                    obj = CIMClassName.from_wbem_uri(uri)

            assert len(rec_warnings) == 1

        else:
            if exp_exc_type:
                with pytest.raises(exp_exc_type):

                    # The code to be tested
                    obj = CIMClassName.from_wbem_uri(uri)

            else:

                # The code to be tested
                obj = CIMClassName.from_wbem_uri(uri)

        if exp_attrs:

            exp_classname = exp_attrs['classname']
            exp_namespace = exp_attrs['namespace']
            exp_host = exp_attrs['host']

            assert isinstance(obj, CIMClassName)

            assert obj.classname == exp_classname
            assert isinstance(obj.classname, type(exp_classname))

            assert obj.namespace == exp_namespace
            assert isinstance(obj.namespace, type(exp_namespace))

            assert obj.host == exp_host
            assert isinstance(obj.host, type(exp_host))


class Test_CIMClassName_to_wbem_uri_str(object):
    # pylint: disable=too-few-public-methods
    """
    Test CIMClassName.to_wbem_uri() and .__str__().
    """

    func_name = [
        # Fixture for function to be tested
        'to_wbem_uri', '__str__'
    ]

    testcases = [
        # Testcases for CIMClassName.to_wbem_uri().
        # Each testcase has these items:
        # * desc: Short testcase description.
        # * attrs: Dict of input attributes for the CIMClassName object
        #     to be tested.
        # * format: Format for to_wbem_uri(): one of 'standard', 'cimobject',
        #     'historical'.
        # * exp_result: Expected WBEM URI string, if expected to succeed.
        #     Exception type, if expected to fail.
        # * exp_warn_type: Expected warning type.
        #     None, if no warning expected.
        # * condition: Condition for testcase to run.
        (
            "all components, standard format",
            dict(
                classname=u'CIM_Foo',
                namespace=u'root/cimv2',
                host=u'10.11.12.13:5989'),
            'standard',
            '//10.11.12.13:5989/root/cimv2:CIM_Foo',
            None, CHECK_0_12_0
        ),
        (
            "all components, cimobject format",
            dict(
                classname=u'CIM_Foo',
                namespace=u'root/cimv2',
                host=u'10.11.12.13:5989'),
            'cimobject',
            '//10.11.12.13:5989/root/cimv2:CIM_Foo',
            None, CHECK_0_12_0
        ),
        (
            "all components, historical format",
            dict(
                classname=u'CIM_Foo',
                namespace=u'root/cimv2',
                host=u'10.11.12.13:5989'),
            'historical',
            '//10.11.12.13:5989/root/cimv2:CIM_Foo',
            None, CHECK_0_12_0
        ),
        (
            "no authority, standard format",
            dict(
                classname=u'CIM_Foo',
                namespace=u'root/cimv2',
                host=None),
            'standard',
            '/root/cimv2:CIM_Foo',
            None, CHECK_0_12_0
        ),
        (
            "no authority, cimobject format",
            dict(
                classname=u'CIM_Foo',
                namespace=u'root/cimv2',
                host=None),
            'cimobject',
            'root/cimv2:CIM_Foo',
            None, CHECK_0_12_0
        ),
        (
            "no authority, historical format",
            dict(
                classname=u'CIM_Foo',
                namespace=u'root/cimv2',
                host=None),
            'historical',
            'root/cimv2:CIM_Foo',
            None, CHECK_0_12_0
        ),
        (
            "authority with user:password",
            dict(
                classname=u'CIM_Foo',
                namespace=u'root/cimv2',
                host=u'jdd:test@10.11.12.13:5989'),
            'standard',
            '//jdd:test@10.11.12.13:5989/root/cimv2:CIM_Foo',
            None, CHECK_0_12_0
        ),
        (
            "authority with user (no password)",
            dict(
                classname=u'CIM_Foo',
                namespace=u'root/cimv2',
                host=u'jdd@10.11.12.13:5989'),
            'standard',
            '//jdd@10.11.12.13:5989/root/cimv2:CIM_Foo',
            None, CHECK_0_12_0
        ),
        (
            "authority without port",
            dict(
                classname=u'CIM_Foo',
                namespace=u'root/cimv2',
                host=u'10.11.12.13'),
            'standard',
            '//10.11.12.13/root/cimv2:CIM_Foo',
            None, CHECK_0_12_0
        ),
        (
            "authority with IPv6 address",
            dict(
                classname=u'CIM_Foo',
                namespace=u'root/cimv2',
                host=u'[10:11:12:13]'),
            'standard',
            '//[10:11:12:13]/root/cimv2:CIM_Foo',
            None, CHECK_0_12_0
        ),
        (
            "authority with IPv6 address and port",
            dict(
                classname=u'CIM_Foo',
                namespace=u'root/cimv2',
                host=u'[10:11:12:13]:5989'),
            'standard',
            '//[10:11:12:13]:5989/root/cimv2:CIM_Foo',
            None, CHECK_0_12_0
        ),
        (
            "local WBEM URI (no authority)",
            dict(
                classname=u'CIM_Foo',
                namespace=u'root/cimv2',
                host=None),
            'standard',
            '/root/cimv2:CIM_Foo',
            None, CHECK_0_12_0
        ),
        (
            "local WBEM URI with only class name, standard format",
            dict(
                classname=u'CIM_Foo',
                namespace=None,
                host=None),
            'standard',
            '/:CIM_Foo',
            None, CHECK_0_12_0
        ),
        (
            "local WBEM URI with only class name, cimobject format",
            dict(
                classname=u'CIM_Foo',
                namespace=None,
                host=None),
            'cimobject',
            ':CIM_Foo',
            None, CHECK_0_12_0
        ),
        (
            "local WBEM URI with only class name, historical format",
            dict(
                classname=u'CIM_Foo',
                namespace=None,
                host=None),
            'historical',
            'CIM_Foo',
            None, CHECK_0_12_0
        ),
        (
            "local WBEM URI with namespace that has only one component",
            dict(
                classname=u'CIM_Foo',
                namespace=u'root',
                host=None),
            'standard',
            '/root:CIM_Foo',
            None, CHECK_0_12_0
        ),
        (
            "local WBEM URI with namespace that has three components",
            dict(
                classname=u'CIM_Foo',
                namespace=u'root/cimv2/test',
                host=None),
            'standard',
            '/root/cimv2/test:CIM_Foo',
            None, CHECK_0_12_0
        ),
    ]

    @pytest.mark.parametrize(
        "func_name",
        func_name)
    @pytest.mark.parametrize(
        "desc, attrs, format, exp_result, exp_warn_type, condition",
        testcases)
    def test_CIMClassName_to_wbem_uri_str(
            self, desc, format, attrs, exp_result, exp_warn_type, condition,
            func_name):
        """All test cases for CIMClassName.to_wbem_uri() and .__str__()."""

        if not condition:
            pytest.skip("Condition for test case not met")

        if isinstance(exp_result, type) and issubclass(exp_result, Exception):
            # We expect an exception
            exp_exc_type = exp_result
            exp_uri = None
        else:
            # We expect the code to return
            exp_exc_type = None
            exp_uri = exp_result

        obj = CIMClassName(**attrs)

        func = getattr(obj, func_name)
        if func_name == 'to_wbem_uri':
            func_kwargs = dict(format=format)
        if func_name == '__str__':
            if format != 'historical':
                pytest.skip("Not testing CIMClassName.__str__() with "
                            "format: %r" % format)
            func_kwargs = dict()

        if condition == 'pdb':
            import pdb
            pdb.set_trace()

        if exp_warn_type:
            with pytest.warns(exp_warn_type) as rec_warnings:
                if exp_exc_type:
                    with pytest.raises(exp_exc_type):

                        # The code to be tested
                        uri = func(**func_kwargs)

                else:

                    # The code to be tested
                    uri = func(**func_kwargs)

            assert len(rec_warnings) == 1

        else:
            if exp_exc_type:
                with pytest.raises(exp_exc_type):

                    # The code to be tested
                    uri = func(**func_kwargs)

            else:

                # The code to be tested
                uri = func(**func_kwargs)

        if exp_uri:

            assert isinstance(uri, six.text_type)
            assert uri == exp_uri


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

        # Classname tests
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

        # Superclass tests
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

        # Properties tests
        (
            "Verify properties order preservation with list of CIMProperty",
            dict(
                classname='CIM_Foo',
                properties=[
                    CIMProperty('P1', value='Ham'),
                    CIMProperty('P2', value='Cheese'),
                ]
            ),
            dict(
                classname=u'CIM_Foo',
                properties=NocaseDict([
                    ('P1', CIMProperty('P1', value='Ham')),
                    ('P2', CIMProperty('P2', value='Cheese')),
                ])
            ),
            None, True
        ),
        (
            "Verify properties order preservation with OrderedDict",
            dict(
                classname='CIM_Foo',
                properties=OrderedDict([
                    ('P1', CIMProperty('P1', value='Ham')),
                    ('P2', CIMProperty('P2', value='Cheese')),
                ])
            ),
            dict(
                classname=u'CIM_Foo',
                properties=NocaseDict([
                    ('P1', CIMProperty('P1', value='Ham')),
                    ('P2', CIMProperty('P2', value='Cheese')),
                ])
            ),
            None, True
        ),
        (
            "Verify properties order preservation with list of tuple(key,val)",
            dict(
                classname='CIM_Foo',
                properties=[
                    ('P1', CIMProperty('P1', value='Ham')),
                    ('P2', CIMProperty('P2', value='Cheese')),
                ]
            ),
            dict(
                classname=u'CIM_Foo',
                properties=NocaseDict([
                    ('P1', CIMProperty('P1', value='Ham')),
                    ('P2', CIMProperty('P2', value='Cheese')),
                ])
            ),
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

        # Methods tests
        (
            "Verify methods order preservation with list of CIMMethod",
            dict(
                classname='CIM_Foo',
                methods=[
                    CIMMethod('M1', return_type='string'),
                    CIMMethod('M2', return_type='uint32'),
                ]
            ),
            dict(
                classname=u'CIM_Foo',
                methods=NocaseDict([
                    ('M1', CIMMethod('M1', return_type='string')),
                    ('M2', CIMMethod('M2', return_type='uint32')),
                ])
            ),
            None, True
        ),
        (
            "Verify methods order preservation with OrderedDict",
            dict(
                classname='CIM_Foo',
                methods=OrderedDict([
                    ('M1', CIMMethod('M1', return_type='string')),
                    ('M2', CIMMethod('M2', return_type='uint32')),
                ])
            ),
            dict(
                classname=u'CIM_Foo',
                methods=NocaseDict([
                    ('M1', CIMMethod('M1', return_type='string')),
                    ('M2', CIMMethod('M2', return_type='uint32')),
                ])
            ),
            None, True
        ),
        (
            "Verify methods order preservation with list of tuple(key,val)",
            dict(
                classname='CIM_Foo',
                methods=[
                    ('M1', CIMMethod('M1', return_type='string')),
                    ('M2', CIMMethod('M2', return_type='uint32')),
                ]
            ),
            dict(
                classname=u'CIM_Foo',
                methods=NocaseDict([
                    ('M1', CIMMethod('M1', return_type='string')),
                    ('M2', CIMMethod('M2', return_type='uint32')),
                ])
            ),
            None, True
        ),
        (
            "Verify that methods dict is converted to NocaseDict",
            dict(classname=u'CIM_Foo', methods=dict(M1=method_M1)),
            dict(classname=u'CIM_Foo', methods=NocaseDict(M1=method_M1)),
            None, True
        ),

        # Qualifiers tests
        (
            "Verify qualifiers order preservation with list of CIMQualifier",
            dict(
                classname='CIM_Foo',
                qualifiers=[
                    CIMQualifier('Q1', value='Ham'),
                    CIMQualifier('Q2', value='Cheese'),
                ]
            ),
            dict(
                classname=u'CIM_Foo',
                qualifiers=NocaseDict([
                    ('Q1', CIMQualifier('Q1', value='Ham')),
                    ('Q2', CIMQualifier('Q2', value='Cheese')),
                ])
            ),
            None, True
        ),
        (
            "Verify qualifiers order preservation with OrderedDict",
            dict(
                classname='CIM_Foo',
                qualifiers=OrderedDict([
                    ('Q1', CIMQualifier('Q1', value='Ham')),
                    ('Q2', CIMQualifier('Q2', value='Cheese')),
                ])
            ),
            dict(
                classname=u'CIM_Foo',
                qualifiers=NocaseDict([
                    ('Q1', CIMQualifier('Q1', value='Ham')),
                    ('Q2', CIMQualifier('Q2', value='Cheese')),
                ])
            ),
            None, True
        ),
        (
            "Verify qualifiers order preservation with list of tuple(key,val)",
            dict(
                classname='CIM_Foo',
                qualifiers=[
                    ('Q1', CIMQualifier('Q1', value='Ham')),
                    ('Q2', CIMQualifier('Q2', value='Cheese')),
                ]
            ),
            dict(
                classname=u'CIM_Foo',
                qualifiers=NocaseDict([
                    ('Q1', CIMQualifier('Q1', value='Ham')),
                    ('Q2', CIMQualifier('Q2', value='Cheese')),
                ])
            ),
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

        # Path tests
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
            with pytest.warns(exp_warn_type) as rec_warnings:

                # The code to be tested
                obj = CIMClass(**kwargs)

            assert len(rec_warnings) == 1

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

        # Properties should compare order-insensitively

        self.assertEqual(
            CIMClass(
                'CIM_Foo',
                properties=[
                    CIMProperty('Cheepy', value='Birds'),
                    CIMProperty('Creepy', value='Ants'),
                ]),
            CIMClass(
                'CIM_Foo',
                properties=[
                    CIMProperty('Cheepy', value='Birds'),
                    CIMProperty('Creepy', value='Ants'),
                ]),
        )

        self.assertEqual(
            CIMClass(
                'CIM_Foo',
                properties=[
                    CIMProperty('Cheepy', value='Birds'),
                    CIMProperty('Creepy', value='Ants'),
                ]),
            CIMClass(
                'CIM_Foo',
                properties=[
                    CIMProperty('Creepy', value='Ants'),
                    CIMProperty('Cheepy', value='Birds'),
                ]),
        )

        # Methods should compare order-insensitively

        self.assertEqual(
            CIMClass(
                'CIM_Foo',
                methods=[
                    CIMMethod('Cheepy', return_type='string'),
                    CIMMethod('Creepy', return_type='uint32'),
                ]),
            CIMClass(
                'CIM_Foo',
                methods=[
                    CIMMethod('Cheepy', return_type='string'),
                    CIMMethod('Creepy', return_type='uint32'),
                ]),
        )

        self.assertEqual(
            CIMClass(
                'CIM_Foo',
                methods=[
                    CIMMethod('Cheepy', return_type='string'),
                    CIMMethod('Creepy', return_type='uint32'),
                ]),
            CIMClass(
                'CIM_Foo',
                methods=[
                    CIMMethod('Creepy', return_type='uint32'),
                    CIMMethod('Cheepy', return_type='string'),
                ]),
        )

        # Qualifiers should compare order-insensitively

        self.assertEqual(
            CIMClass(
                'CIM_Foo',
                qualifiers=[
                    CIMQualifier('Q1', 'Birds'),
                    CIMQualifier('Q2', 'Ants'),
                ]),
            CIMClass(
                'CIM_Foo',
                qualifiers=[
                    CIMQualifier('Q1', 'Birds'),
                    CIMQualifier('Q2', 'Ants'),
                ]),
        )

        self.assertEqual(
            CIMClass(
                'CIM_Foo',
                qualifiers=[
                    CIMQualifier('Q1', 'Birds'),
                    CIMQualifier('Q2', 'Ants'),
                ]),
            CIMClass(
                'CIM_Foo',
                qualifiers=[
                    CIMQualifier('Q2', 'Ants'),
                    CIMQualifier('Q1', 'Birds'),
                ]),
        )


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


testcases_CIMClass_hash = [

    # Each testcase tuple has these items:
    # * desc: Short testcase description.
    # * kwargs: Input arguments for test function, as a dict:
    #   * obj1: CIMClass object #1 to be tested.
    #   * obj2: CIMClass object #2 to be tested.
    #   * exp_hash_equal: Expected equality of the object hash values.
    # * exp_exc_types: Expected exception type(s), or None.
    # * exp_warn_types: Expected warning type(s), or None.
    # * condition: Boolean condition for testcase to run, or 'pdb' for debugger

    # Classname tests
    (
        "Classname, equal with same lexical case",
        dict(
            obj1=CIMClass('CIM_Foo'),
            obj2=CIMClass('CIM_Foo'),
            exp_hash_equal=True,
        ),
        None, None, True
    ),
    (
        "Classname, equal with different lexical case",
        dict(
            obj1=CIMClass('CIM_Foo'),
            obj2=CIMClass('ciM_foO'),
            exp_hash_equal=True,
        ),
        None, None, True
    ),
    (
        "Classname, different",
        dict(
            obj1=CIMClass('CIM_Foo'),
            obj2=CIMClass('CIM_Foo_x'),
            exp_hash_equal=False,
        ),
        None, None, True
    ),

    # Superclass tests
    (
        "Superclass, equal with same lexical case",
        dict(
            obj1=CIMClass('CIM_Foo', superclass='CIM_Bar'),
            obj2=CIMClass('CIM_Foo', superclass='CIM_Bar'),
            exp_hash_equal=True,
        ),
        None, None, True
    ),
    (
        "Superclass, equal with different lexical case",
        dict(
            obj1=CIMClass('CIM_Foo', superclass='CIM_Bar'),
            obj2=CIMClass('CIM_Foo', superclass='ciM_bAR'),
            exp_hash_equal=True,
        ),
        None, None, True
    ),
    (
        "Superclass, different",
        dict(
            obj1=CIMClass('CIM_Foo', superclass='CIM_Bar'),
            obj2=CIMClass('CIM_Foo', superclass='CIM_Bar_x'),
            exp_hash_equal=False,
        ),
        None, None, True
    ),

    # Path tests
    (
        "Class paths, equal with same lexical case",
        dict(
            obj1=CIMClass(
                'CIM_Foo',
                path=CIMClassName('CIM_Foo'),
            ),
            obj2=CIMClass(
                'CIM_Foo',
                path=CIMClassName('CIM_Foo'),
            ),
            exp_hash_equal=True,
        ),
        None, None, True
    ),
    (
        "Class paths, equal with different lexical case in classname",
        dict(
            obj1=CIMClass(
                'CIM_Foo',
                path=CIMClassName('CIM_Foo'),
            ),
            obj2=CIMClass(
                'CIM_Foo',
                path=CIMClassName('CIM_foo'),
            ),
            exp_hash_equal=True,
        ),
        None, None, True
    ),
    (
        "Class paths, different",
        dict(
            obj1=CIMClass(
                'CIM_Foo',
                path=CIMClassName('CIM_Foo'),
            ),
            obj2=CIMClass(
                'CIM_Foo',
                path=CIMClassName('CIM_Foo_x'),
            ),
            exp_hash_equal=False,
        ),
        None, None, True
    ),

    # Properties tests
    (
        "Matching properties, names with same lexical case",
        dict(
            obj1=CIMClass('CIM_Foo', properties=[
                CIMProperty('p1', value='v1'),
            ]),
            obj2=CIMClass('CIM_Foo', properties=[
                CIMProperty('p1', value='v1'),
            ]),
            exp_hash_equal=True,
        ),
        None, None, True
    ),
    (
        "Matching properties, names with different lexical case",
        dict(
            obj1=CIMClass('CIM_Foo', properties=[
                CIMProperty('p1', value='v1'),
            ]),
            obj2=CIMClass('CIM_Foo', properties=[
                CIMProperty('P1', value='v1'),
            ]),
            exp_hash_equal=True,
        ),
        None, None, True
    ),
    (
        "Non-matching properties, one property more",
        dict(
            obj1=CIMClass('CIM_Foo', properties=[
                CIMProperty('p1', value='v1'),
            ]),
            obj2=CIMClass('CIM_Foo', properties=[
                CIMProperty('p1', value='v1'),
                CIMProperty('p2', value='v2'),
            ]),
            exp_hash_equal=False,
        ),
        None, None, True
    ),
    (
        "Non-matching properties, one property less",
        dict(
            obj1=CIMClass('CIM_Foo', properties=[
                CIMProperty('p1', value='v1'),
                CIMProperty('p2', value='v2'),
            ]),
            obj2=CIMClass('CIM_Foo', properties=[
                CIMProperty('p1', value='v1'),
            ]),
            exp_hash_equal=False,
        ),
        None, None, True
    ),
    (
        "Non-matching properties, different properties",
        dict(
            obj1=CIMClass('CIM_Foo', properties=[
                CIMProperty('p2', value='v2'),
            ]),
            obj2=CIMClass('CIM_Foo', properties=[
                CIMProperty('p1', value='v1'),
            ]),
            exp_hash_equal=False,
        ),
        None, None, True
    ),
    (
        "Matching properties, default values with different lexical case",
        dict(
            obj1=CIMClass('CIM_Foo', properties=[
                CIMProperty('p1', value='v1'),
            ]),
            obj2=CIMClass('CIM_Foo', properties=[
                CIMProperty('p1', value='V1'),
            ]),
            exp_hash_equal=False,
        ),
        None, None, True
    ),
    (
        "Matching properties, with default values as unicode / string",
        dict(
            obj1=CIMClass('CIM_Foo', properties=[
                CIMProperty('p1', value='v1'),
            ]),
            obj2=CIMClass('CIM_Foo', properties=[
                CIMProperty('p1', value=u'v1'),
            ]),
            exp_hash_equal=True,
        ),
        None, None, True
    ),
    (
        "Matching properties, equal with a number of types",
        dict(
            obj1=CIMClass('CIM_Foo', properties=[
                CIMProperty('pstr', value='v1'),
                CIMProperty('pboo', value=False),
                CIMProperty('pui8', value=Uint8(42)),
                CIMProperty('pref', value=CIMInstanceName('CIM_Bar')),
            ]),
            obj2=CIMClass('CIM_Foo', properties=[
                CIMProperty('pstr', value='v1'),
                CIMProperty('pboo', value=False),
                CIMProperty('pui8', value=Uint8(42)),
                CIMProperty('pref', value=CIMInstanceName('CIM_Bar')),
            ]),
            exp_hash_equal=True,
        ),
        None, None, True
    ),

    # Methods tests
    (
        "Matching methods, names with same lexical case",
        dict(
            obj1=CIMClass('CIM_Foo', methods=[
                CIMMethod('m1', return_type='string'),
            ]),
            obj2=CIMClass('CIM_Foo', methods=[
                CIMMethod('m1', return_type='string'),
            ]),
            exp_hash_equal=True,
        ),
        None, None, True
    ),
    (
        "Matching methods, names with different lexical case",
        dict(
            obj1=CIMClass('CIM_Foo', methods=[
                CIMMethod('m1', return_type='string'),
            ]),
            obj2=CIMClass('CIM_Foo', methods=[
                CIMMethod('M1', return_type='string'),
            ]),
            exp_hash_equal=True,
        ),
        None, None, True
    ),
    (
        "Non-matching methods, one method more",
        dict(
            obj1=CIMClass('CIM_Foo', methods=[
                CIMMethod('m1', return_type='string'),
            ]),
            obj2=CIMClass('CIM_Foo', methods=[
                CIMMethod('m1', return_type='string'),
                CIMMethod('m2', return_type='string'),
            ]),
            exp_hash_equal=False,
        ),
        None, None, True
    ),
    (
        "Non-matching methods, one method less",
        dict(
            obj1=CIMClass('CIM_Foo', methods=[
                CIMMethod('m1', return_type='string'),
                CIMMethod('m2', return_type='string'),
            ]),
            obj2=CIMClass('CIM_Foo', methods=[
                CIMMethod('m1', return_type='string'),
            ]),
            exp_hash_equal=False,
        ),
        None, None, True
    ),
    (
        "Non-matching methods, different methods",
        dict(
            obj1=CIMClass('CIM_Foo', methods=[
                CIMMethod('m1', return_type='string'),
            ]),
            obj2=CIMClass('CIM_Foo', methods=[
                CIMMethod('m2', return_type='string'),
            ]),
            exp_hash_equal=False,
        ),
        None, None, True
    ),
    (
        "Matching methods, different return types",
        dict(
            obj1=CIMClass('CIM_Foo', methods=[
                CIMMethod('m1', return_type='string'),
            ]),
            obj2=CIMClass('CIM_Foo', methods=[
                CIMMethod('m1', return_type='uint8'),
            ]),
            exp_hash_equal=False,
        ),
        None, None, True
    ),

    # Qualifiers tests
    (
        "Matching qualifiers, qualifier names with same lexical case",
        dict(
            obj1=CIMClass('CIM_Foo',
                          qualifiers={'Cheepy': 'Birds'}),
            obj2=CIMClass('CIM_Foo',
                          qualifiers={'Cheepy': 'Birds'}),
            exp_hash_equal=True,
        ),
        None, None, True
    ),
    (
        "Matching qualifiers, qualifier names with different lexical case",
        dict(
            obj1=CIMClass('CIM_Foo',
                          qualifiers={'Cheepy': 'Birds'}),
            obj2=CIMClass('CIM_Foo',
                          qualifiers={'cheepy': 'Birds'}),
            exp_hash_equal=True,
        ),
        None, None, True
    ),
    (
        "Non-matching qualifiers, one qualifier more",
        dict(
            obj1=CIMClass('CIM_Foo'),
            obj2=CIMClass('CIM_Foo',
                          qualifiers={'Cheepy': 'Birds'}),
            exp_hash_equal=False,
        ),
        None, None, True
    ),
    (
        "Non-matching qualifiers, one qualifier less",
        dict(
            obj1=CIMClass('CIM_Foo',
                          qualifiers={'Cheepy': 'Birds'}),
            obj2=CIMClass('CIM_Foo'),
            exp_hash_equal=False,
        ),
        None, None, True
    ),
    (
        "Non-matching qualifiers, different qualifiers",
        dict(
            obj1=CIMClass('CIM_Foo',
                          qualifiers={'Cheepy': 'Birds'}),
            obj2=CIMClass('CIM_Foo',
                          qualifiers={'Creepy': 'Ants'}),
            exp_hash_equal=False,
        ),
        None, None, True
    ),
    (
        "Matching qualifiers, with values that differ in lexical case",
        dict(
            obj1=CIMClass('CIM_Foo',
                          qualifiers={'Cheepy': 'Birds'}),
            obj2=CIMClass('CIM_Foo',
                          qualifiers={'Cheepy': 'birds'}),
            exp_hash_equal=False,
        ),
        None, None, True
    ),
    (
        "Matching qualifiers, with values that are unicode / string",
        dict(
            obj1=CIMClass('CIM_Foo',
                          qualifiers={'Cheepy': 'Birds'}),
            obj2=CIMClass('CIM_Foo',
                          qualifiers={'Cheepy': u'Birds'}),
            exp_hash_equal=True,
        ),
        None, None, True
    ),
    (
        "Equal qualifiers with a number of types",
        dict(
            obj1=CIMClass(
                'CIM_Foo',
                qualifiers={
                    'Name': 'Foo',
                    'Boolean': False,
                    'Number': Uint8(42),
                    'Ref': CIMInstanceName('CIM_Bar'),
                }
            ),
            obj2=CIMClass(
                'CIM_Foo',
                qualifiers={
                    'Name': 'Foo',
                    'Boolean': False,
                    'Number': Uint8(42),
                    'Ref': CIMInstanceName('CIM_Bar'),
                }
            ),
            exp_hash_equal=True,
        ),
        None, None, True
    ),
    (
        "Qualifier with different types: bool True / string 'TRUE'",
        dict(
            obj1=CIMClass('CIM_Foo',
                          qualifiers={'Foo': True}),
            obj2=CIMClass('CIM_Foo',
                          qualifiers={'Foo': 'TRUE'}),
            exp_hash_equal=False,
        ),
        None, None, True
    ),
    (
        "Qualifier with different types: bool False / string 'FALSE'",
        dict(
            obj1=CIMClass('CIM_Foo',
                          qualifiers={'Foo': False}),
            obj2=CIMClass('CIM_Foo',
                          qualifiers={'Foo': 'FALSE'}),
            exp_hash_equal=False,
        ),
        None, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    testcases_CIMClass_hash)
@pytest_extensions.test_function
def test_CIMClass_hash(
        desc, kwargs, exp_exc_types, exp_warn_types, condition):
    """
    All test cases for CIMClass.__hash__().
    """

    obj1 = kwargs['obj1']
    obj2 = kwargs['obj2']

    # Double check they are different objects
    assert id(obj1) != id(obj2)

    # The code to be tested
    hash1 = hash(obj1)
    hash2 = hash(obj2)

    exp_hash_equal = kwargs['exp_hash_equal']

    assert (hash1 == hash2) == exp_hash_equal


class Test_CIMClass_str(object):  # pylint: disable=too-few-public-methods
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
                properties=[
                    CIMProperty('Name', 'string'),
                    CIMProperty('Ref1', 'reference'),
                ])
        ),
        (
            CIMClass(
                classname='CIM_Foo',
                properties=[
                    CIMProperty('Name', 'string'),
                    CIMProperty('Ref1', 'reference'),
                ],
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


class Test_CIMClass_repr(object):  # pylint: disable=too-few-public-methods
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
                properties=[
                    CIMProperty('Name', 'string'),
                    CIMProperty('Ref1', 'reference'),
                ])
        ),
        (
            CIMClass(
                classname='CIM_Foo',
                properties=[
                    CIMProperty('Name', 'string'),
                    CIMProperty('Ref1', 'reference'),
                ],
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


class Test_CIMClass_tomof(object):  # pylint: disable=too-few-public-methods
    """
    Test CIMClass.tomof().
    """

    testcases = [
        # Testcases for CIMClass.tomof().
        # Each testcase has these items:
        # * desc: Short testcase description.
        # * obj: Object to be tested.
        # * exp_result: Expected MOF string, if expected to succeed.
        #     Exception type, if expected to fail.
        # * exp_warn_type: Expected warning type.
        #     None, if no warning expected.
        # * condition: Condition for testcase to run.
        (
            "all components",
            CIMClass(
                classname=u'C1',
                superclass=u'C2',
                properties=[
                    CIMProperty(
                        'p2', value="abc", type='string',
                        qualifiers=[
                            CIMQualifier('q2', value="qv2", type='string'),
                        ],
                    ),
                ],
                methods=[
                    CIMMethod(
                        'm3', return_type='uint32',
                        qualifiers=[
                            CIMQualifier('q3', value="qv3", type='string'),
                        ],
                        parameters=[
                            CIMParameter(
                                'p4', type='string',
                                qualifiers=[
                                    CIMQualifier('q4', value="qv4",
                                                 type='string'),
                                ],
                            ),
                        ],
                    ),
                ],
                qualifiers=[
                    CIMQualifier('q1', value="qv1", type='string'),
                ],
                path=None
            ),
            """\
   [q1 ( "qv1" )]
class C1 : C2 {

      [q2 ( "qv2" )]
   string p2 = "abc";

      [q3 ( "qv3" )]
   uint32 m3(
         [q4 ( "qv4" )]
      string p4);

};
""" \
            if CHECK_0_12_0 else \
            """\
    [q1 ("qv1")]
class C1 : C2 {

        [q2 ("qv2")]
    string p2 = "abc";

        [q3 ("qv3")]
    uint32 m3(
          [q4 ("qv4")]
        string p4);
};
""",
            None, True
        ),
        (
            "class with embedded instance property with a default value",
            CIMClass(
                classname=u'C1',
                properties=[
                    CIMProperty(
                        'p1',
                        value=CIMInstance(
                            classname='CE',
                            properties=[
                                CIMProperty('emb1', value='abc'),
                                CIMProperty('emb2', value=Sint32(-1024)),
                                CIMProperty('emb3', value=True),
                            ],
                        ),
                        type='string',
                        qualifiers=[
                            CIMQualifier('EmbeddedInstance', value="CE",
                                         type='string'),
                        ],
                    ),
                ],
            ),
            # pylint: disable=line-too-long
            u"""\
class C1 {

      [EmbeddedInstance ( "CE" )]
   string p1 =
      "instance of CE {\\n   emb1 = \\"abc\\";\\n   emb2 = -1024;\\n   emb3 = "
      "true;\\n};\\n";

};
""",
            None, CHECK_0_12_0
        ),
        (
            "class with reference property with a multi-line default value",
            CIMClass(
                classname=u'C1',
                properties=[
                    CIMProperty(
                        'p1',
                        value=CIMInstanceName(
                            host='some.long.host.name:5989',
                            namespace='root/cimv2',
                            classname='CIM_ReferencedClass',
                            keybindings=[
                                ('k1', 'key1'),
                                ('k2', 'key2'),
                            ],
                        ),
                        type='reference',
                        reference_class='CIM_ReferencedClass',
                    ),
                ],
            ),
            # pylint: disable=line-too-long
            u"""\
class C1 {

   CIM_ReferencedClass REF p1 =
      "//some.long.host.name:5989/root/cimv2:CIM_ReferencedClass.k1=\\"key1\\",k2"
      "=\\"key2\\"";

};
""",  # noqa: E501
            None, CHECK_0_12_0
        ),
    ]

    @pytest.mark.parametrize(
        "desc, obj, exp_result, exp_warn_type, condition",
        testcases)
    def test_CIMClass_tomof(
            self, desc, obj, exp_result, exp_warn_type, condition):
        """All test cases for CIMClass.tomof()."""

        if not condition:
            pytest.skip("Condition for test case not met")

        if isinstance(exp_result, type) and issubclass(exp_result, Exception):
            # We expect an exception
            exp_exc_type = exp_result
            exp_mof = None
        else:
            # We expect the code to return
            exp_exc_type = None
            exp_mof = exp_result

        if condition == 'pdb':
            import pdb
            pdb.set_trace()

        if exp_warn_type:
            with pytest.warns(exp_warn_type) as rec_warnings:
                if exp_exc_type:
                    with pytest.raises(exp_exc_type):

                        # The code to be tested
                        mof = obj.tomof()

                else:

                    # The code to be tested
                    mof = obj.tomof()

            assert len(rec_warnings) == 1

        else:
            if exp_exc_type:
                with pytest.raises(exp_exc_type):

                    # The code to be tested
                    mof = obj.tomof()

            else:

                # The code to be tested
                mof = obj.tomof()

        if exp_mof:

            assert isinstance(mof, six.text_type)
            assert mof == exp_mof


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

        with pytest.warns(DeprecationWarning) as rec_warnings:

            # The code to be tested
            obj = CIMMethod(
                methodname='FooMethod',
                return_type='string')

        assert len(rec_warnings) == 1
        assert obj.name == u'FooMethod'

    def test_CIMMethod_init_name_methodname(self):
        # pylint: disable=unused-argument
        """Test both name and methodname argument of CIMMethod.__init__()."""

        if CHECK_0_12_0:
            exp_exc_type = ValueError
        else:
            exp_exc_type = TypeError

        with pytest.raises(exp_exc_type):

            with pytest.warns(DeprecationWarning):

                # The code to be tested
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

        # Name tests
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

        # Parameters tests
        (
            "Verify parameters order preservation with list of CIMParameter",
            dict(
                name='Meth1', return_type='string',
                parameters=[
                    CIMParameter('P1', type='string'),
                    CIMParameter('P2', type='uint32'),
                ]
            ),
            dict(
                name=u'Meth1', return_type=u'string',
                parameters=NocaseDict([
                    ('P1', CIMParameter('P1', type='string')),
                    ('P2', CIMParameter('P2', type='uint32')),
                ])
            ),
            None, True
        ),
        (
            "Verify parameters order preservation with OrderedDict",
            dict(
                name='Meth1', return_type='string',
                parameters=OrderedDict([
                    ('P1', CIMParameter('P1', type='string')),
                    ('P2', CIMParameter('P2', type='uint32')),
                ])
            ),
            dict(
                name=u'Meth1', return_type=u'string',
                parameters=NocaseDict([
                    ('P1', CIMParameter('P1', type='string')),
                    ('P2', CIMParameter('P2', type='uint32')),
                ])
            ),
            None, True
        ),
        (
            "Verify parameters order preservation with list of tuple(key,val)",
            dict(
                name='Meth1', return_type='string',
                parameters=[
                    ('P1', CIMParameter('P1', type='string')),
                    ('P2', CIMParameter('P2', type='uint32')),
                ]
            ),
            dict(
                name=u'Meth1', return_type=u'string',
                parameters=NocaseDict([
                    ('P1', CIMParameter('P1', type='string')),
                    ('P2', CIMParameter('P2', type='uint32')),
                ])
            ),
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

        # Qualifiers tests
        (
            "Verify qualifiers order preservation with list of CIMQualifier",
            dict(
                name='Meth1', return_type='string',
                qualifiers=[
                    CIMQualifier('Q1', value='Ham'),
                    CIMQualifier('Q2', value='Cheese'),
                ]
            ),
            dict(
                name=u'Meth1', return_type=u'string',
                qualifiers=NocaseDict([
                    ('Q1', CIMQualifier('Q1', value='Ham')),
                    ('Q2', CIMQualifier('Q2', value='Cheese')),
                ])
            ),
            None, True
        ),
        (
            "Verify qualifiers order preservation with OrderedDict",
            dict(
                name='Meth1', return_type='string',
                qualifiers=OrderedDict([
                    ('Q1', CIMQualifier('Q1', value='Ham')),
                    ('Q2', CIMQualifier('Q2', value='Cheese')),
                ])
            ),
            dict(
                name=u'Meth1', return_type=u'string',
                qualifiers=NocaseDict([
                    ('Q1', CIMQualifier('Q1', value='Ham')),
                    ('Q2', CIMQualifier('Q2', value='Cheese')),
                ])
            ),
            None, True
        ),
        (
            "Verify qualifiers order preservation with list of tuple(key,val)",
            dict(
                name='Meth1', return_type='string',
                qualifiers=[
                    ('Q1', CIMQualifier('Q1', value='Ham')),
                    ('Q2', CIMQualifier('Q2', value='Cheese')),
                ]
            ),
            dict(
                name=u'Meth1', return_type=u'string',
                qualifiers=NocaseDict([
                    ('Q1', CIMQualifier('Q1', value='Ham')),
                    ('Q2', CIMQualifier('Q2', value='Cheese')),
                ])
            ),
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
            with pytest.warns(exp_warn_type) as rec_warnings:

                # The code to be tested
                obj = CIMMethod(**kwargs)

            assert len(rec_warnings) == 1

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
        # * exp_warn_type: Expected warning type.
        # * condition: Condition for testcase to run.
        (
            "Verify that name None fails (with ValueError since 0.12)",
            dict(name=None, return_type='string'),
            ValueError, None, CHECK_0_12_0
        ),
        (
            "Verify that name None fails (with TypeError before 0.12)",
            dict(name=None, return_type='string'),
            TypeError, None, not CHECK_0_12_0
        ),
        (
            "Verify that name and methodname fails (ValueError since 0.12)",
            dict(name='M', methodname='M', return_type='string'),
            ValueError, DeprecationWarning, CHECK_0_12_0
        ),
        (
            "Verify that name and methodname fails (TypeError before 0.12)",
            dict(name='M', methodname='M', return_type='string'),
            TypeError, DeprecationWarning, not CHECK_0_12_0
        ),
        (
            "Verify that parameters with inconsistent name fails "
            "(since 0.12)",
            dict(
                name='M',
                parameters=dict(P1=CIMParameter('P1_X', type='string'))),
            ValueError, None, CHECK_0_12_0
        ),
        (
            "Verify that qualifiers with inconsistent name fails "
            "(since 0.12)",
            dict(
                name='M',
                qualifiers=dict(Q1=CIMQualifier('Q1_X', value='abc'))),
            ValueError, None, CHECK_0_12_0
        ),
        (
            "Verify that return_type None fails (since 0.12)",
            dict(
                name='M',
                return_type=None),
            ValueError, None, CHECK_0_12_0
        ),
        (
            "Verify that return_type 'reference' fails (since 0.12)",
            dict(
                name='M',
                return_type='reference'),
            ValueError, None, CHECK_0_12_0
        ),
        (
            "Verify that invalid return_type fails (since 0.12)",
            dict(
                name='M',
                return_type='xxx'),
            ValueError, None, CHECK_0_12_0
        ),
    ]

    @pytest.mark.parametrize(
        "desc, kwargs, exp_exc_type, exp_warn_type, condition",
        testcases_fails)
    def test_CIMMethod_init_fails(
            self, desc, kwargs, exp_exc_type, exp_warn_type, condition):
        # pylint: disable=unused-argument
        """All test cases where CIMMethod.__init__() fails."""

        if not condition:
            pytest.skip("Condition for test case not met")

        with pytest.raises(exp_exc_type):

            if exp_warn_type is None:

                # The code to be tested
                CIMMethod(**kwargs)

            else:
                with pytest.warns(exp_warn_type) as rec_warnings:

                    # The code to be tested
                    CIMMethod(**kwargs)

                assert len(rec_warnings) == 1


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

        # Parameters should compare order-insensitively

        self.assertEqual(
            CIMMethod(
                'FooMethod', return_type='string',
                parameters=[
                    CIMParameter('Cheepy', type='string'),
                    CIMParameter('Creepy', type='uint32'),
                ]),
            CIMMethod(
                'FooMethod', return_type='string',
                parameters=[
                    CIMParameter('Cheepy', type='string'),
                    CIMParameter('Creepy', type='uint32'),
                ]),
        )

        self.assertEqual(
            CIMMethod(
                'FooMethod', return_type='string',
                parameters=[
                    CIMParameter('Cheepy', type='string'),
                    CIMParameter('Creepy', type='uint32'),
                ]),
            CIMMethod(
                'FooMethod', return_type='string',
                parameters=[
                    CIMParameter('Creepy', type='uint32'),
                    CIMParameter('Cheepy', type='string'),
                ]),
        )

        # Qualifiers should compare order-insensitively

        self.assertEqual(
            CIMMethod(
                'FooMethod', return_type='string',
                qualifiers=[
                    CIMQualifier('Q1', 'Birds'),
                    CIMQualifier('Q2', 'Ants'),
                ]),
            CIMMethod(
                'FooMethod', return_type='string',
                qualifiers=[
                    CIMQualifier('Q1', 'Birds'),
                    CIMQualifier('Q2', 'Ants'),
                ]),
        )

        self.assertEqual(
            CIMMethod(
                'FooMethod', return_type='string',
                qualifiers=[
                    CIMQualifier('Q1', 'Birds'),
                    CIMQualifier('Q2', 'Ants'),
                ]),
            CIMMethod(
                'FooMethod', return_type='string',
                qualifiers=[
                    CIMQualifier('Q2', 'Ants'),
                    CIMQualifier('Q1', 'Birds'),
                ]),
        )


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


testcases_CIMMethod_hash = [

    # Each testcase tuple has these items:
    # * desc: Short testcase description.
    # * kwargs: Input arguments for test function, as a dict:
    #   * obj1: CIMMethod object #1 to be tested.
    #   * obj2: CIMMethod object #2 to be tested.
    #   * exp_hash_equal: Expected equality of the object hash values.
    # * exp_exc_types: Expected exception type(s), or None.
    # * exp_warn_types: Expected warning type(s), or None.
    # * condition: Boolean condition for testcase to run, or 'pdb' for debugger

    # Name tests
    (
        "Name, equal with same lexical case",
        dict(
            obj1=CIMMethod('Meth1', return_type='string'),
            obj2=CIMMethod('Meth1', return_type='string'),
            exp_hash_equal=True,
        ),
        None, None, True
    ),
    (
        "Name, equal with different lexical case",
        dict(
            obj1=CIMMethod('Meth1', return_type='string'),
            obj2=CIMMethod('metH1', return_type='string'),
            exp_hash_equal=True,
        ),
        None, None, True
    ),
    (
        "Name, different",
        dict(
            obj1=CIMMethod('Meth1', return_type='string'),
            obj2=CIMMethod('Meth1_x', return_type='string'),
            exp_hash_equal=False,
        ),
        None, None, True
    ),

    # Return_type tests
    (
        "Return_type, different",
        dict(
            obj1=CIMMethod('Meth1', return_type='uint8'),
            obj2=CIMMethod('Meth1', return_type='sint8'),
            exp_hash_equal=False,
        ),
        None, None, True
    ),

    # Parameters tests
    (
        "Matching parameters, names with same lexical case",
        dict(
            obj1=CIMMethod('Meth1', return_type='uint8', parameters=[
                CIMParameter('p1', type='string'),
            ]),
            obj2=CIMMethod('Meth1', return_type='uint8', parameters=[
                CIMParameter('p1', type='string'),
            ]),
            exp_hash_equal=True,
        ),
        None, None, True
    ),
    (
        "Matching parameters, names with different lexical case",
        dict(
            obj1=CIMMethod('Meth1', return_type='uint8', parameters=[
                CIMParameter('p1', type='string'),
            ]),
            obj2=CIMMethod('Meth1', return_type='uint8', parameters=[
                CIMParameter('P1', type='string'),
            ]),
            exp_hash_equal=True,
        ),
        None, None, True
    ),
    (
        "Non-matching parameters, one parameter more",
        dict(
            obj1=CIMMethod('Meth1', return_type='uint8', parameters=[
                CIMParameter('p1', type='string'),
            ]),
            obj2=CIMMethod('Meth1', return_type='uint8', parameters=[
                CIMParameter('p1', type='string'),
                CIMParameter('p2', type='string'),
            ]),
            exp_hash_equal=False,
        ),
        None, None, True
    ),
    (
        "Non-matching parameters, one parameter less",
        dict(
            obj1=CIMMethod('Meth1', return_type='uint8', parameters=[
                CIMParameter('p1', type='string'),
                CIMParameter('p2', type='string'),
            ]),
            obj2=CIMMethod('Meth1', return_type='uint8', parameters=[
                CIMParameter('p1', type='string'),
            ]),
            exp_hash_equal=False,
        ),
        None, None, True
    ),
    (
        "Non-matching parameters, different parameters",
        dict(
            obj1=CIMMethod('Meth1', return_type='uint8', parameters=[
                CIMParameter('p2', type='string'),
            ]),
            obj2=CIMMethod('Meth1', return_type='uint8', parameters=[
                CIMParameter('p1', type='string'),
            ]),
            exp_hash_equal=False,
        ),
        None, None, True
    ),

    # Propagated tests
    (
        "Propagated, equal",
        dict(
            obj1=CIMMethod('Meth1', return_type='string',
                           propagated=True),
            obj2=CIMMethod('Meth1', return_type='string',
                           propagated=True),
            exp_hash_equal=True,
        ),
        None, None, True
    ),
    (
        "Propagated, different",
        dict(
            obj1=CIMMethod('Meth1', return_type='string',
                           propagated=True),
            obj2=CIMMethod('Meth1', return_type='string',
                           propagated=False),
            exp_hash_equal=False,
        ),
        None, None, True
    ),

    # Class_origin tests
    (
        "Class_origin, equal with same lexical case",
        dict(
            obj1=CIMMethod('Meth1', return_type='string',
                           propagated=True, class_origin='CIM_Org'),
            obj2=CIMMethod('Meth1', return_type='string',
                           propagated=True, class_origin='CIM_Org'),
            exp_hash_equal=True,
        ),
        None, None, True
    ),
    (
        "Class_origin, equal with different lexical case",
        dict(
            obj1=CIMMethod('Meth1', return_type='string',
                           propagated=True, class_origin='CIM_Org'),
            obj2=CIMMethod('Meth1', return_type='string',
                           propagated=True, class_origin='Cim_org'),
            exp_hash_equal=True,
        ),
        None, None, True
    ),
    (
        "Class_origin, different",
        dict(
            obj1=CIMMethod('Meth1', return_type='string',
                           propagated=True, class_origin='CIM_Org'),
            obj2=CIMMethod('Meth1', return_type='string',
                           propagated=True, class_origin='CIM_Org_x'),
            exp_hash_equal=False,
        ),
        None, None, True
    ),

    # Qualifiers tests
    (
        "Matching qualifiers, qualifier names with same lexical case",
        dict(
            obj1=CIMMethod('Meth1', return_type='string',
                           qualifiers={'Cheepy': 'Birds'}),
            obj2=CIMMethod('Meth1', return_type='string',
                           qualifiers={'Cheepy': 'Birds'}),
            exp_hash_equal=True,
        ),
        None, None, True
    ),
    (
        "Matching qualifiers, qualifier names with different lexical case",
        dict(
            obj1=CIMMethod('Meth1', return_type='string',
                           qualifiers={'Cheepy': 'Birds'}),
            obj2=CIMMethod('Meth1', return_type='string',
                           qualifiers={'cheepy': 'Birds'}),
            exp_hash_equal=True,
        ),
        None, None, True
    ),
    (
        "Non-matching qualifiers, one qualifier more",
        dict(
            obj1=CIMMethod('Meth1', return_type='string'),
            obj2=CIMMethod('Meth1', return_type='string',
                           qualifiers={'Cheepy': 'Birds'}),
            exp_hash_equal=False,
        ),
        None, None, True
    ),
    (
        "Non-matching qualifiers, one qualifier less",
        dict(
            obj1=CIMMethod('Meth1', return_type='string',
                           qualifiers={'Cheepy': 'Birds'}),
            obj2=CIMMethod('Meth1', return_type='string'),
            exp_hash_equal=False,
        ),
        None, None, True
    ),
    (
        "Non-matching qualifiers, different qualifiers",
        dict(
            obj1=CIMMethod('Meth1', return_type='string',
                           qualifiers={'Cheepy': 'Birds'}),
            obj2=CIMMethod('Meth1', return_type='string',
                           qualifiers={'Creepy': 'Ants'}),
            exp_hash_equal=False,
        ),
        None, None, True
    ),
    (
        "Matching qualifiers, with values that differ in lexical case",
        dict(
            obj1=CIMMethod('Meth1', return_type='string',
                           qualifiers={'Cheepy': 'Birds'}),
            obj2=CIMMethod('Meth1', return_type='string',
                           qualifiers={'Cheepy': 'birds'}),
            exp_hash_equal=False,
        ),
        None, None, True
    ),
    (
        "Matching qualifiers, with values that are unicode / string",
        dict(
            obj1=CIMMethod('Meth1', return_type='string',
                           qualifiers={'Cheepy': 'Birds'}),
            obj2=CIMMethod('Meth1', return_type='string',
                           qualifiers={'Cheepy': u'Birds'}),
            exp_hash_equal=True,
        ),
        None, None, True
    ),
    (
        "Equal qualifiers with a number of types",
        dict(
            obj1=CIMMethod(
                'Meth1', return_type='string',
                qualifiers={
                    'Name': 'Foo',
                    'Boolean': False,
                    'Number': Uint8(42),
                    'Ref': CIMInstanceName('CIM_Bar'),
                }
            ),
            obj2=CIMMethod(
                'Meth1', return_type='string',
                qualifiers={
                    'Name': 'Foo',
                    'Boolean': False,
                    'Number': Uint8(42),
                    'Ref': CIMInstanceName('CIM_Bar'),
                }
            ),
            exp_hash_equal=True,
        ),
        None, None, True
    ),
    (
        "Qualifier with different types: bool True / string 'TRUE'",
        dict(
            obj1=CIMMethod('Meth1', return_type='string',
                           qualifiers={'Foo': True}),
            obj2=CIMMethod('Meth1', return_type='string',
                           qualifiers={'Foo': 'TRUE'}),
            exp_hash_equal=False,
        ),
        None, None, True
    ),
    (
        "Qualifier with different types: bool False / string 'FALSE'",
        dict(
            obj1=CIMMethod('Meth1', return_type='string',
                           qualifiers={'Foo': False}),
            obj2=CIMMethod('Meth1', return_type='string',
                           qualifiers={'Foo': 'FALSE'}),
            exp_hash_equal=False,
        ),
        None, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    testcases_CIMMethod_hash)
@pytest_extensions.test_function
def test_CIMMethod_hash(
        desc, kwargs, exp_exc_types, exp_warn_types, condition):
    """
    All test cases for CIMMethod.__hash__().
    """

    obj1 = kwargs['obj1']
    obj2 = kwargs['obj2']

    # Double check they are different objects
    assert id(obj1) != id(obj2)

    # The code to be tested
    hash1 = hash(obj1)
    hash2 = hash(obj2)

    exp_hash_equal = kwargs['exp_hash_equal']

    assert (hash1 == hash2) == exp_hash_equal


class Test_CIMMethod_str(object):  # pylint: disable=too-few-public-methods
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


class Test_CIMMethod_repr(object):  # pylint: disable=too-few-public-methods
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


class Test_CIMMethod_tomof(object):  # pylint: disable=too-few-public-methods
    """
    Test CIMMethod.tomof().
    """

    testcases = [
        # Testcases for CIMMethod.tomof().
        # Each testcase has these items:
        # * desc: Short testcase description.
        # * obj: Object to be tested.
        # * indent: Number of spaces to indent the generated MOF lines.
        # * exp_result: Expected MOF string, if expected to succeed.
        #     Exception type, if expected to fail.
        # * exp_warn_type: Expected warning type.
        #     None, if no warning expected.
        # * condition: Condition for testcase to run.
        (
            "all components",
            CIMMethod(
                name='M1',
                return_type='string',
                qualifiers=[
                    CIMQualifier('Q1', value='abc', type='string'),
                    CIMQualifier('Q2', value=Uint32(42), type='uint32'),
                ],
                parameters=[
                    CIMParameter(
                        'P1', type='string',
                        qualifiers=[
                            CIMQualifier('Q3', value="def", type='string'),
                            CIMQualifier('Q4', value=Sint32(-3), type='sint32'),
                        ],
                    ),
                ],
            ),
            12,
            u"""\
               [Q1 ( "abc" ),
                Q2 ( 42 )]
            string M1(
                  [Q3 ( "def" ),
                   Q4 ( -3 )]
               string P1);\n""" \
            if CHECK_0_12_0 else \
            u"""\
                [Q1 ("abc"),
                Q2 (42)]
            string M1(
                  [Q3 ("def"),
                  Q4 (-3)]
                string P1);\n""",
            None, True
        ),
        (
            "no qualifiers, no parameters",
            CIMMethod(
                name='M1',
                return_type='string',
            ),
            12,
            u"""\
            string M1();\n""",
            None, True
        ),
        (
            "one scalar single line qualifier, no parameters",
            CIMMethod(
                name='M1',
                return_type='string',
                qualifiers=[
                    CIMQualifier('Q1', value='abc', type='string'),
                ],
            ),
            12,
            u"""\
               [Q1 ( "abc" )]
            string M1();\n""" \
            if CHECK_0_12_0 else \
            u"""\
                [Q1 ("abc")]
            string M1();\n""",
            None, True
        ),
        (
            "one scalar multi line qualifier, no parameters",
            CIMMethod(
                name='M1',
                return_type='string',
                qualifiers=[
                    CIMQualifier('Q1', value=('abc def ' * 10 + 'z'),
                                 type='string'),
                ],
            ),
            12,
            u"""\
               [Q1 (
                   "abc def abc def abc def abc def abc def abc def abc def "
                   "abc def abc def abc def z" )]
            string M1();\n""" \
            if CHECK_0_12_0 else \
            u"""\
                [Q1 (
                  "abc def abc def abc def abc def abc def abc def abc def "
                  "abc def abc def abc def z")]
            string M1();\n""",
            None, True
        ),
        (
            "two scalar single line qualifiers, no parameters",
            CIMMethod(
                name='M1',
                return_type='string',
                qualifiers=[
                    CIMQualifier('Q1', value='abc', type='string'),
                    CIMQualifier('Q2', value=Uint32(42), type='uint32'),
                ],
            ),
            12,
            u"""\
               [Q1 ( "abc" ),
                Q2 ( 42 )]
            string M1();\n""" \
            if CHECK_0_12_0 else \
            u"""\
                [Q1 ("abc"),
                Q2 (42)]
            string M1();\n""",
            None, True
        ),
        (
            "two scalar multi line qualifiers, no parameters",
            CIMMethod(
                name='M1',
                return_type='string',
                qualifiers=[
                    CIMQualifier('Q1', value=('abc def ' * 10 + 'z'),
                                 type='string'),
                    CIMQualifier('Q2', value=('rst uvw ' * 10 + 'z'),
                                 type='string'),
                ],
            ),
            12,
            u"""\
               [Q1 (
                   "abc def abc def abc def abc def abc def abc def abc def "
                   "abc def abc def abc def z" ),
                Q2 (
                   "rst uvw rst uvw rst uvw rst uvw rst uvw rst uvw rst uvw "
                   "rst uvw rst uvw rst uvw z" )]
            string M1();\n""" \
            if CHECK_0_12_0 else \
            u"""\
                [Q1 (
                  "abc def abc def abc def abc def abc def abc def abc def "
                  "abc def abc def abc def z"),
                Q2 (
                  "rst uvw rst uvw rst uvw rst uvw rst uvw rst uvw rst uvw "
                  "rst uvw rst uvw rst uvw z")]
            string M1();\n""",
            None, True
        ),
        (
            "one array single line qualifier, no parameters",
            CIMMethod(
                name='M1',
                return_type='string',
                qualifiers=[
                    CIMQualifier('Q1', value=['abc', 'def'], type='string'),
                ],
            ),
            12,
            u"""\
               [Q1 { "abc", "def" }]
            string M1();\n""" \
            if CHECK_0_12_0 else \
            u"""\
                [Q1 { "abc", "def"}]
            string M1();\n""",
            None, True
        ),
        (
            "one array multi line qualifier with short items, no parameters",
            CIMMethod(
                name='M1',
                return_type='string',
                qualifiers=[
                    CIMQualifier(
                        'Q1',
                        value=['abcdef%02d' % i for i in range(0, 10)],
                        type='string'),
                ],
            ),
            12,
            u"""\
               [Q1 { "abcdef00", "abcdef01", "abcdef02", "abcdef03",
                   "abcdef04", "abcdef05", "abcdef06", "abcdef07",
                   "abcdef08", "abcdef09" }]
            string M1();\n""" \
            if CHECK_0_12_0 else \
            u"""\
                [Q1 { "abcdef00", "abcdef01", "abcdef02", "abcdef03",
                  "abcdef04", "abcdef05", "abcdef06", "abcdef07",
                  "abcdef08", "abcdef09"}]
            string M1();\n""",
            None, True
        ),
        (
            "one array multi line qualifier with long items, no parameters",
            CIMMethod(
                name='M1',
                return_type='string',
                qualifiers=[
                    CIMQualifier(
                        'Q1',
                        value=['abc def ' * 10 + 'z%02d' % i
                               for i in range(0, 2)],
                        type='string'),
                ],
            ),
            12,
            u"""\
               [Q1 {
                   "abc def abc def abc def abc def abc def abc def abc def "
                   "abc def abc def abc def z00",
                   "abc def abc def abc def abc def abc def abc def abc def "
                   "abc def abc def abc def z01" }]
            string M1();\n""" \
            if CHECK_0_12_0 else \
            u"""\
                [Q1 {
                  "abc def abc def abc def abc def abc def abc def abc def "
                  "abc def abc def abc def z00",
                  "abc def abc def abc def abc def abc def abc def abc def "
                  "abc def abc def abc def z01"}]
            string M1();\n""",
            None, True
        ),
        (
            "return type string, two parameters with type string",
            CIMMethod(
                name='M1',
                return_type='string',
                parameters=[
                    CIMParameter('P1', type='string'),
                    CIMParameter('P2', type='string'),
                ],
            ),
            12,
            u"""\
            string M1(
               string P1,
               string P2);\n""",
            None, CHECK_0_12_0  # Unpredictable order before 0.12
        ),
        (
            "return type uint32, one parameter with type sint32",
            CIMMethod(
                name='M1',
                return_type='uint32',
                parameters=[
                    CIMParameter('P1', type='sint32'),
                ],
            ),
            12,
            u"""\
            uint32 M1(
               sint32 P1);\n""" \
            if CHECK_0_12_0 else \
            u"""\
            uint32 M1(
                sint32 P1);\n""",
            None, True
        ),
    ]

    @pytest.mark.parametrize(
        "desc, obj, indent, exp_result, exp_warn_type, condition",
        testcases)
    def test_CIMMethod_tomof(
            self, desc, obj, indent, exp_result, exp_warn_type, condition):
        """All test cases for CIMMethod.tomof()."""

        if not condition:
            pytest.skip("Condition for test case not met")

        if isinstance(exp_result, type) and issubclass(exp_result, Exception):
            # We expect an exception
            exp_exc_type = exp_result
            exp_mof = None
        else:
            # We expect the code to return
            exp_exc_type = None
            exp_mof = exp_result

        if condition == 'pdb':
            import pdb
            pdb.set_trace()

        if exp_warn_type:
            with pytest.warns(exp_warn_type) as rec_warnings:
                if exp_exc_type:
                    with pytest.raises(exp_exc_type):

                        # The code to be tested
                        mof = obj.tomof(indent)

                else:

                    # The code to be tested
                    mof = obj.tomof(indent)

            assert len(rec_warnings) == 1

        else:
            if exp_exc_type:
                with pytest.raises(exp_exc_type):

                    # The code to be tested
                    mof = obj.tomof(indent)

            else:

                # The code to be tested
                mof = obj.tomof(indent)

        if exp_mof:

            assert isinstance(mof, six.text_type)
            assert mof == exp_mof


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
            [Uint32(42)],
            None)

        assert obj.name == u'FooParam'
        assert obj.type == u'uint32'
        assert obj.reference_class == u'CIM_Ref'
        assert obj.is_array is True
        assert obj.array_size == 2
        assert obj.qualifiers == NocaseDict(qualifiers)
        assert obj.value == [Uint32(42)]
        assert obj.embedded_object is None

    # Defaults to expect for attributes when not specified in testcase
    default_exp_attrs = dict(
        reference_class=None,
        is_array=False if CHECK_0_12_0 else None,
        array_size=None,
        qualifiers=NocaseDict(),
        value=None,
        embedded_object=None,
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
            None, CHECK_0_12_0
        ),
        (
            "Verify that unspecified is_array is implied to array by array "
            "value (since 0.12)",
            dict(name='FooParam', type='string',
                 is_array=None, value=[u'abc']),
            dict(name=u'FooParam', type=u'string',
                 is_array=True, value=[u'abc']),
            None, CHECK_0_12_0
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

        # Value tests
        (
            "Verify that a string value is converted to unicode",
            dict(name=u'FooParam', type=u'string',
                 value='abc'),
            dict(name=u'FooParam', type=u'string',
                 value=u'abc' if CHECK_0_12_0 else 'abc'),
            None, True
        ),
        (
            "Verify that an integer value is converted to Uint32",
            dict(name=u'FooParam', type=u'uint32',
                 value=42),
            dict(name=u'FooParam', type=u'uint32',
                 value=Uint32(42)),
            None, True
        ),
        (
            "Verify that an integer value 1 is converted to bool True",
            dict(name=u'FooParam', type=u'boolean',
                 value=1),
            dict(name=u'FooParam', type=u'boolean',
                 value=True),
            None, True
        ),
        (
            "Verify that an integer value 0 is converted to bool False",
            dict(name=u'FooParam', type=u'boolean',
                 value=0),
            dict(name=u'FooParam', type=u'boolean',
                 value=False),
            None, True
        ),
        (
            "Verify that a non-empty string value is converted to bool True",
            dict(name=u'FooParam', type=u'boolean',
                 value='FALSE'),
            dict(name=u'FooParam', type=u'boolean',
                 value=True),
            None, True
        ),
        (
            "Verify that a float value is converted to real32",
            dict(name=u'FooParam', type=u'real32',
                 value=42.1),
            dict(name=u'FooParam', type=u'real32',
                 value=Real32(42.1)),
            None, True
        ),
        (
            "Verify that a datetime string value is converted to CIM datetime",
            dict(name=u'FooParam', type=u'datetime',
                 value='19980125133015.123456-300'),
            dict(name=u'FooParam', type=u'datetime',
                 value=CIMDateTime('19980125133015.123456-300')),
            None, True
        ),
        (
            "Verify that an embedded instance is accepted and embedded_object "
            "defaults to 'instance'",
            dict(name=u'FooParam', type=u'string',
                 value=CIMInstance('CIM_Emb')),
            dict(name=u'FooParam', type=u'string',
                 value=CIMInstance('CIM_Emb'), embedded_object=u'instance'),
            None, True
        ),
        (
            "Verify that an embedded instance is accepted with embedded_object "
            "specified as 'instance'",
            dict(name=u'FooParam', type=u'string',
                 value=CIMInstance('CIM_Emb'), embedded_object='instance'),
            dict(name=u'FooParam', type=u'string',
                 value=CIMInstance('CIM_Emb'), embedded_object=u'instance'),
            None, True
        ),
        (
            "Verify that an embedded class is accepted and embedded_object "
            "defaults to 'object'",
            dict(name=u'FooParam', type=u'string',
                 value=CIMClass('CIM_Emb')),
            dict(name=u'FooParam', type=u'string',
                 value=CIMClass('CIM_Emb'), embedded_object=u'object'),
            None, True
        ),
        (
            "Verify that an embedded class is accepted with embedded_object "
            "specified as 'object'",
            dict(name=u'FooParam', type=u'string',
                 value=CIMClass('CIM_Emb'), embedded_object='object'),
            dict(name=u'FooParam', type=u'string',
                 value=CIMClass('CIM_Emb'), embedded_object=u'object'),
            None, True
        ),

        # Value array tests
        (
            "Verify that a string array value causes is_array to be "
            "defaulted to True",
            dict(name=u'FooParam', type=u'string',
                 value=['abc']),
            dict(name=u'FooParam', type=u'string', is_array=True,
                 value=[u'abc'] if CHECK_0_12_0 else ['abc']),
            None, True
        ),
        (
            "Verify that an integer array value is converted to [Uint32]",
            dict(name=u'FooParam', type=u'uint32',
                 value=[42]),
            dict(name=u'FooParam', type=u'uint32', is_array=True,
                 value=[Uint32(42)]),
            None, True
        ),
        (
            "Verify that an integer array value 1 is converted to bool True",
            dict(name=u'FooParam', type=u'boolean',
                 value=[1]),
            dict(name=u'FooParam', type=u'boolean', is_array=True,
                 value=[True]),
            None, True
        ),
        (
            "Verify that an array item None remains None",
            dict(name=u'FooParam', type=u'boolean',
                 value=[None]),
            dict(name=u'FooParam', type=u'boolean', is_array=True,
                 value=[None]),
            None, True
        ),
        (
            "Verify that an integer array value 0 is converted to bool False",
            dict(name=u'FooParam', type=u'boolean',
                 value=[0]),
            dict(name=u'FooParam', type=u'boolean', is_array=True,
                 value=[False]),
            None, True
        ),
        (
            "Verify that a non-empty string array value is converted to bool "
            "True",
            dict(name=u'FooParam', type=u'boolean',
                 value=['FALSE']),
            dict(name=u'FooParam', type=u'boolean', is_array=True,
                 value=[True]),
            None, True
        ),
        (
            "Verify that a float array value is converted to real32",
            dict(name=u'FooParam', type=u'real32',
                 value=[42.1]),
            dict(name=u'FooParam', type=u'real32', is_array=True,
                 value=[Real32(42.1)]),
            None, True
        ),
        (
            "Verify that a datetime string array value is converted to CIM "
            "datetime",
            dict(name=u'FooParam', type=u'datetime',
                 value=['19980125133015.123456-300']),
            dict(name=u'FooParam', type=u'datetime', is_array=True,
                 value=[CIMDateTime('19980125133015.123456-300')]),
            None, True
        ),
        (
            "Verify that an embedded instance array is accepted and "
            "embedded_object defaults to 'instance'",
            dict(name=u'FooParam', type=u'string',
                 value=[CIMInstance('CIM_Emb')]),
            dict(name=u'FooParam', type=u'string', is_array=True,
                 value=[CIMInstance('CIM_Emb')], embedded_object=u'instance'),
            None, True
        ),
        (
            "Verify that an embedded instance array is accepted with "
            "embedded_object specified as 'instance'",
            dict(name=u'FooParam', type=u'string',
                 value=[CIMInstance('CIM_Emb')], embedded_object='instance'),
            dict(name=u'FooParam', type=u'string', is_array=True,
                 value=[CIMInstance('CIM_Emb')], embedded_object=u'instance'),
            None, True
        ),
        (
            "Verify that an embedded class array is accepted and "
            "embedded_object defaults to 'object'",
            dict(name=u'FooParam', type=u'string',
                 value=[CIMClass('CIM_Emb')]),
            dict(name=u'FooParam', type=u'string', is_array=True,
                 value=[CIMClass('CIM_Emb')], embedded_object=u'object'),
            None, True
        ),
        (
            "Verify that an embedded class array is accepted with "
            "embedded_object specified as 'object'",
            dict(name=u'FooParam', type=u'string',
                 value=[CIMClass('CIM_Emb')], embedded_object='object'),
            dict(name=u'FooParam', type=u'string', is_array=True,
                 value=[CIMClass('CIM_Emb')], embedded_object=u'object'),
            None, True
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
        exp_embedded_object = exp_attrs.get(
            'embedded_object', self.default_exp_attrs['embedded_object'])

        if exp_warn_type is None:

            # The code to be tested
            obj = CIMParameter(**kwargs)

        else:
            with pytest.warns(exp_warn_type) as rec_warnings:

                # The code to be tested
                obj = CIMParameter(**kwargs)

            assert len(rec_warnings) == 1

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

        assert obj.embedded_object == exp_embedded_object
        assert isinstance(obj.embedded_object, type(exp_embedded_object))

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
            "Verify that invalid type fails (since 0.12)",
            dict(name='M', type='xxx'),
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

        # Qualifiers should compare order-insensitively

        self.assertEqual(
            CIMParameter(
                'Param1', type='string',
                qualifiers=[
                    CIMQualifier('Q1', 'Birds'),
                    CIMQualifier('Q2', 'Ants'),
                ]),
            CIMParameter(
                'Param1', type='string',
                qualifiers=[
                    CIMQualifier('Q1', 'Birds'),
                    CIMQualifier('Q2', 'Ants'),
                ]),
        )

        self.assertEqual(
            CIMParameter(
                'Param1', type='string',
                qualifiers=[
                    CIMQualifier('Q1', 'Birds'),
                    CIMQualifier('Q2', 'Ants'),
                ]),
            CIMParameter(
                'Param1', type='string',
                qualifiers=[
                    CIMQualifier('Q2', 'Ants'),
                    CIMQualifier('Q1', 'Birds'),
                ]),
        )


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


testcases_CIMParameter_hash = [

    # Each testcase tuple has these items:
    # * desc: Short testcase description.
    # * kwargs: Input arguments for test function, as a dict:
    #   * obj1: CIMParameter object #1 to be tested.
    #   * obj2: CIMParameter object #2 to be tested.
    #   * exp_hash_equal: Expected equality of the object hash values.
    # * exp_exc_types: Expected exception type(s), or None.
    # * exp_warn_types: Expected warning type(s), or None.
    # * condition: Boolean condition for testcase to run, or 'pdb' for debugger

    # Name tests
    (
        "Name, equal with same lexical case",
        dict(
            obj1=CIMParameter('Parm1', type='string'),
            obj2=CIMParameter('Parm1', type='string'),
            exp_hash_equal=True,
        ),
        None, None, True
    ),
    (
        "Name, equal with different lexical case",
        dict(
            obj1=CIMParameter('Parm1', type='string'),
            obj2=CIMParameter('pARM1', type='string'),
            exp_hash_equal=True,
        ),
        None, None, True
    ),
    (
        "Name, different",
        dict(
            obj1=CIMParameter('Parm1', type='string'),
            obj2=CIMParameter('Parm1_x', type='string'),
            exp_hash_equal=False,
        ),
        None, None, True
    ),

    # Type tests
    (
        "Type, different",
        dict(
            obj1=CIMParameter('Parm1', type='uint8'),
            obj2=CIMParameter('Parm1', type='sint8'),
            exp_hash_equal=False,
        ),
        None, None, True
    ),

    # Reference_class tests
    (
        "Reference class, equal with same lexical case",
        dict(
            obj1=CIMParameter('Parm1', type='reference',
                              reference_class='CIM_Ref'),
            obj2=CIMParameter('Parm1', type='reference',
                              reference_class='CIM_Ref'),
            exp_hash_equal=True,
        ),
        None, None, True
    ),
    (
        "Reference class, equal with different lexical case",
        dict(
            obj1=CIMParameter('Parm1', type='reference',
                              reference_class='CIM_Ref'),
            obj2=CIMParameter('Parm1', type='reference',
                              reference_class='Cim_ref'),
            exp_hash_equal=True,
        ),
        None, None, True
    ),
    (
        "Reference class, different",
        dict(
            obj1=CIMParameter('Parm1', type='reference',
                              reference_class='CIM_Ref'),
            obj2=CIMParameter('Parm1', type='reference',
                              reference_class='CIM_Ref_x'),
            exp_hash_equal=False,
        ),
        None, None, True
    ),

    # Is_array tests
    (
        "Is_array, equal",
        dict(
            obj1=CIMParameter('Parm1', type='string',
                              is_array=True),
            obj2=CIMParameter('Parm1', type='string',
                              is_array=True),
            exp_hash_equal=True,
        ),
        None, None, True
    ),
    (
        "Is_array, different",
        dict(
            obj1=CIMParameter('Parm1', type='string',
                              is_array=True),
            obj2=CIMParameter('Parm1', type='string',
                              is_array=False),
            exp_hash_equal=False,
        ),
        None, None, True
    ),

    # Array_size tests
    (
        "Array_size, equal",
        dict(
            obj1=CIMParameter('Parm1', type='string', is_array=True,
                              array_size=2),
            obj2=CIMParameter('Parm1', type='string', is_array=True,
                              array_size=2),
            exp_hash_equal=True,
        ),
        None, None, True
    ),
    (
        "Array_size, different",
        dict(
            obj1=CIMParameter('Parm1', type='string', is_array=True,
                              array_size=2),
            obj2=CIMParameter('Parm1', type='string', is_array=True,
                              array_size=3),
            exp_hash_equal=False,
        ),
        None, None, True
    ),

    # Qualifiers tests
    (
        "Matching qualifiers, qualifier names with same lexical case",
        dict(
            obj1=CIMParameter('Parm1', type='string',
                              qualifiers={'Cheepy': 'Birds'}),
            obj2=CIMParameter('Parm1', type='string',
                              qualifiers={'Cheepy': 'Birds'}),
            exp_hash_equal=True,
        ),
        None, None, True
    ),
    (
        "Matching qualifiers, qualifier names with different lexical case",
        dict(
            obj1=CIMParameter('Parm1', type='string',
                              qualifiers={'Cheepy': 'Birds'}),
            obj2=CIMParameter('Parm1', type='string',
                              qualifiers={'cheepy': 'Birds'}),
            exp_hash_equal=True,
        ),
        None, None, True
    ),
    (
        "Non-matching qualifiers, one qualifier more",
        dict(
            obj1=CIMParameter('Parm1', type='string'),
            obj2=CIMParameter('Parm1', type='string',
                              qualifiers={'Cheepy': 'Birds'}),
            exp_hash_equal=False,
        ),
        None, None, True
    ),
    (
        "Non-matching qualifiers, one qualifier less",
        dict(
            obj1=CIMParameter('Parm1', type='string',
                              qualifiers={'Cheepy': 'Birds'}),
            obj2=CIMParameter('Parm1', type='string'),
            exp_hash_equal=False,
        ),
        None, None, True
    ),
    (
        "Non-matching qualifiers, different qualifiers",
        dict(
            obj1=CIMParameter('Parm1', type='string',
                              qualifiers={'Cheepy': 'Birds'}),
            obj2=CIMParameter('Parm1', type='string',
                              qualifiers={'Creepy': 'Ants'}),
            exp_hash_equal=False,
        ),
        None, None, True
    ),
    (
        "Matching qualifiers, with values that differ in lexical case",
        dict(
            obj1=CIMParameter('Parm1', type='string',
                              qualifiers={'Cheepy': 'Birds'}),
            obj2=CIMParameter('Parm1', type='string',
                              qualifiers={'Cheepy': 'birds'}),
            exp_hash_equal=False,
        ),
        None, None, True
    ),
    (
        "Matching qualifiers, with values that are unicode / string",
        dict(
            obj1=CIMParameter('Parm1', type='string',
                              qualifiers={'Cheepy': 'Birds'}),
            obj2=CIMParameter('Parm1', type='string',
                              qualifiers={'Cheepy': u'Birds'}),
            exp_hash_equal=True,
        ),
        None, None, True
    ),
    (
        "Equal qualifiers with a number of types",
        dict(
            obj1=CIMParameter(
                'Parm1', type='string',
                qualifiers={
                    'Name': 'Foo',
                    'Boolean': False,
                    'Number': Uint8(42),
                    'Ref': CIMInstanceName('CIM_Bar'),
                }
            ),
            obj2=CIMParameter(
                'Parm1', type='string',
                qualifiers={
                    'Name': 'Foo',
                    'Boolean': False,
                    'Number': Uint8(42),
                    'Ref': CIMInstanceName('CIM_Bar'),
                }
            ),
            exp_hash_equal=True,
        ),
        None, None, True
    ),
    (
        "Qualifier with different types: bool True / string 'TRUE'",
        dict(
            obj1=CIMParameter('Parm1', type='string',
                              qualifiers={'Foo': True}),
            obj2=CIMParameter('Parm1', type='string',
                              qualifiers={'Foo': 'TRUE'}),
            exp_hash_equal=False,
        ),
        None, None, True
    ),
    (
        "Qualifier with different types: bool False / string 'FALSE'",
        dict(
            obj1=CIMParameter('Parm1', type='string',
                              qualifiers={'Foo': False}),
            obj2=CIMParameter('Parm1', type='string',
                              qualifiers={'Foo': 'FALSE'}),
            exp_hash_equal=False,
        ),
        None, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    testcases_CIMParameter_hash)
@pytest_extensions.test_function
def test_CIMParameter_hash(
        desc, kwargs, exp_exc_types, exp_warn_types, condition):
    """
    All test cases for CIMParameter.__hash__().
    """

    obj1 = kwargs['obj1']
    obj2 = kwargs['obj2']

    # Double check they are different objects
    assert id(obj1) != id(obj2)

    # The code to be tested
    hash1 = hash(obj1)
    hash2 = hash(obj2)

    exp_hash_equal = kwargs['exp_hash_equal']

    assert (hash1 == hash2) == exp_hash_equal


class Test_CIMParameter_str(object):  # pylint: disable=too-few-public-methods
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


class Test_CIMParameter_repr(object):  # pylint: disable=too-few-public-methods
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


class Test_CIMParameter_tomof(object):  # pylint: disable=too-few-public-methods
    """
    Test CIMParameter.tomof().
    """

    testcases = [
        # Testcases for CIMParameter.tomof().
        # Note: The deprecated 'value' attribute of CIMParameter is not used in
        #   its tomof() method, nor does it influence other attributes, hence
        #   it does not appear in these testcases.
        # Each testcase has these items:
        # * desc: Short testcase description.
        # * obj: Object to be tested.
        # * indent: Number of spaces to indent the generated MOF lines.
        # * exp_result: Expected MOF string, if expected to succeed.
        #     Exception type, if expected to fail.
        # * exp_warn_type: Expected warning type.
        #     None, if no warning expected.
        # * condition: Condition for testcase to run.
        (
            "all components",
            CIMParameter(
                name='P1',
                type='string',
                reference_class=None,
                is_array=True,
                array_size=5,
                qualifiers=[
                    CIMQualifier('Q1', value='abc', type='string'),
                    CIMQualifier('Q2', value=Uint32(42), type='uint32'),
                ],
            ),
            12,
            u"""\
               [Q1 ( "abc" ),
                Q2 ( 42 )]
            string P1[5]""" \
            if CHECK_0_12_0 else \
            u"""\
              [Q1 ("abc"),
              Q2 (42)]
            string P1[5]""",
            None, True
        ),
        (
            "no qualifiers",
            CIMParameter(
                name='P1',
                type='string',
            ),
            12,
            u"""\
            string P1""",
            None, True
        ),
        (
            "one scalar single line qualifier",
            CIMParameter(
                name='P1',
                type='string',
                qualifiers=[
                    CIMQualifier('Q1', value='abc', type='string'),
                ],
            ),
            12,
            u"""\
               [Q1 ( "abc" )]
            string P1""" \
            if CHECK_0_12_0 else \
            u"""\
              [Q1 ("abc")]
            string P1""",
            None, True
        ),
        (
            "one scalar multi line qualifier",
            CIMParameter(
                name='P1',
                type='string',
                qualifiers=[
                    CIMQualifier('Q1', value=('abc def ' * 10 + 'z'),
                                 type='string'),
                ],
            ),
            12,
            u"""\
               [Q1 (
                   "abc def abc def abc def abc def abc def abc def abc def "
                   "abc def abc def abc def z" )]
            string P1""" \
            if CHECK_0_12_0 else \
            u"""\
              [Q1 (
                "abc def abc def abc def abc def abc def abc def abc def abc "
                "def abc def abc def z")]
            string P1""",
            None, True
        ),
        (
            "two scalar single line qualifiers",
            CIMParameter(
                name='P1',
                type='string',
                qualifiers=[
                    CIMQualifier('Q1', value='abc', type='string'),
                    CIMQualifier('Q2', value=Uint32(42), type='uint32'),
                ],
            ),
            12,
            u"""\
               [Q1 ( "abc" ),
                Q2 ( 42 )]
            string P1""" \
            if CHECK_0_12_0 else \
            u"""\
              [Q1 ("abc"),
              Q2 (42)]
            string P1""",
            None, True
        ),
        (
            "two scalar multi line qualifiers",
            CIMParameter(
                name='P1',
                type='string',
                qualifiers=[
                    CIMQualifier('Q1', value=('abc def ' * 10 + 'z'),
                                 type='string'),
                    CIMQualifier('Q2', value=('rst uvw ' * 10 + 'z'),
                                 type='string'),
                ],
            ),
            12,
            u"""\
               [Q1 (
                   "abc def abc def abc def abc def abc def abc def abc def "
                   "abc def abc def abc def z" ),
                Q2 (
                   "rst uvw rst uvw rst uvw rst uvw rst uvw rst uvw rst uvw "
                   "rst uvw rst uvw rst uvw z" )]
            string P1""" \
            if CHECK_0_12_0 else \
            u"""\
              [Q1 (
                "abc def abc def abc def abc def abc def abc def abc def abc "
                "def abc def abc def z"),
              Q2 (
                "rst uvw rst uvw rst uvw rst uvw rst uvw rst uvw rst uvw rst "
                "uvw rst uvw rst uvw z")]
            string P1""",
            None, True
        ),
        (
            "one array single line qualifier",
            CIMParameter(
                name='P1',
                type='string',
                qualifiers=[
                    CIMQualifier('Q1', value=['abc', 'def'], type='string'),
                ],
            ),
            12,
            u"""\
               [Q1 { "abc", "def" }]
            string P1""" \
            if CHECK_0_12_0 else \
            u"""\
              [Q1 { "abc", "def"}]
            string P1""",
            None, True
        ),
        (
            "one array multi line qualifier with short items",
            CIMParameter(
                name='P1',
                type='string',
                qualifiers=[
                    CIMQualifier(
                        'Q1',
                        value=['abcdef%02d' % i for i in range(0, 10)],
                        type='string'),
                ],
            ),
            12,
            u"""\
               [Q1 { "abcdef00", "abcdef01", "abcdef02", "abcdef03",
                   "abcdef04", "abcdef05", "abcdef06", "abcdef07",
                   "abcdef08", "abcdef09" }]
            string P1""" \
            if CHECK_0_12_0 else \
            u"""\
              [Q1 { "abcdef00", "abcdef01", "abcdef02", "abcdef03",
                "abcdef04", "abcdef05", "abcdef06", "abcdef07",
                "abcdef08", "abcdef09"}]
            string P1""",
            None, True
        ),
        (
            "one array multi line qualifier with long items",
            CIMParameter(
                name='P1',
                type='string',
                qualifiers=[
                    CIMQualifier(
                        'Q1',
                        value=['abc def ' * 10 + 'z%02d' % i
                               for i in range(0, 2)],
                        type='string'),
                ],
            ),
            12,
            u"""\
               [Q1 {
                   "abc def abc def abc def abc def abc def abc def abc def "
                   "abc def abc def abc def z00",
                   "abc def abc def abc def abc def abc def abc def abc def "
                   "abc def abc def abc def z01" }]
            string P1""" \
            if CHECK_0_12_0 else \
            u"""\
              [Q1 {
                "abc def abc def abc def abc def abc def abc def abc def abc "
                "def abc def abc def z00",
                "abc def abc def abc def abc def abc def abc def abc def abc "
                "def abc def abc def z01"}]
            string P1""",
            None, True
        ),
        (
            "string array parameter, variable size",
            CIMParameter(
                name='P1',
                type='string',
                is_array=True,
            ),
            12,
            u"""\
            string P1[]""",
            None, True
        ),
        (
            "uint32 array parameter, fixed size",
            CIMParameter(
                name='P1',
                type='uint32',
                is_array=True,
                array_size=5,
            ),
            12,
            u"""\
            uint32 P1[5]""",
            None, True
        ),
        (
            "reference parameter",
            CIMParameter(
                name='P1',
                type='reference',
                reference_class='RC',
            ),
            12,
            u"""\
            RC REF P1""",
            None, True
        ),
        (
            "reference array parameter, variable size",
            CIMParameter(
                name='P1',
                type='reference',
                reference_class='RC',
                is_array=True,
            ),
            12,
            u"""\
            RC REF P1[]""",
            None, True
        ),
        (
            "datetime parameter",
            CIMParameter(
                name='P1',
                type='datetime',
            ),
            12,
            u"""\
            datetime P1""",
            None, True
        ),
        (
            "boolean array parameter, fixed size",
            CIMParameter(
                name='P1',
                type='boolean',
                is_array=True,
                array_size=5,
            ),
            12,
            u"""\
            boolean P1[5]""",
            None, True
        ),
        (
            "real64 parameter",
            CIMParameter(
                name='P1',
                type='real64',
            ),
            12,
            u"""\
            real64 P1""",
            None, True
        ),
    ]

    @pytest.mark.parametrize(
        "desc, obj, indent, exp_result, exp_warn_type, condition",
        testcases)
    def test_CIMParameter_tomof(
            self, desc, obj, indent, exp_result, exp_warn_type, condition):
        """All test cases for CIMParameter.tomof()."""

        if not condition:
            pytest.skip("Condition for test case not met")

        if isinstance(exp_result, type) and issubclass(exp_result, Exception):
            # We expect an exception
            exp_exc_type = exp_result
            exp_mof = None
        else:
            # We expect the code to return
            exp_exc_type = None
            exp_mof = exp_result

        if condition == 'pdb':
            import pdb
            pdb.set_trace()

        if exp_warn_type:
            with pytest.warns(exp_warn_type) as rec_warnings:
                if exp_exc_type:
                    with pytest.raises(exp_exc_type):

                        # The code to be tested
                        mof = obj.tomof(indent)

                else:

                    # The code to be tested
                    mof = obj.tomof(indent)

            assert len(rec_warnings) == 1

        else:
            if exp_exc_type:
                with pytest.raises(exp_exc_type):

                    # The code to be tested
                    mof = obj.tomof(indent)

            else:

                # The code to be tested
                mof = obj.tomof(indent)

        if exp_mof:

            assert isinstance(mof, six.text_type)
            assert mof == exp_mof


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

        # Name/type tests
        (
            "Verify that name can be None although documented otherwise "
            "(before 0.12)",
            dict(name=None, type=u'string'),
            dict(name=None, type=u'string'),
            None, not CHECK_0_12_0
        ),

        # Type tests
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

        # Type tests with arrays
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

        # Scopes tests
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

        # Overridable tests
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

        # Tosubclass tests
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

        # Toinstance tests
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

        # Translatable tests
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
            with pytest.warns(exp_warn_type) as rec_warnings:

                # The code to be tested
                obj = CIMQualifierDeclaration(**kwargs)

            assert len(rec_warnings) == 1

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
            "Verify that invalid type fails (since 0.12)",
            dict(name='FooQual', type='xxx'),
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

        scopes = NocaseDict([
            ('CLASS', False),
            ('ANY', False),
            ('ASSOCIATION', False),
        ])

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

        scopes = NocaseDict([
            ('CLASS', False),
            ('ANY', False),
            ('ASSOCIATION', False),
        ])

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


testcases_CIMQualifierDeclaration_hash = [

    # Each testcase tuple has these items:
    # * desc: Short testcase description.
    # * kwargs: Input arguments for test function, as a dict:
    #   * obj1: CIMQualifierDeclaration object #1 to be tested.
    #   * obj2: CIMQualifierDeclaration object #2 to be tested.
    #   * exp_hash_equal: Expected equality of the object hash values.
    # * exp_exc_types: Expected exception type(s), or None.
    # * exp_warn_types: Expected warning type(s), or None.
    # * condition: Boolean condition for testcase to run, or 'pdb' for debugger

    # Name tests
    (
        "Name, equal with same lexical case",
        dict(
            obj1=CIMQualifierDeclaration('Qual1', type='string'),
            obj2=CIMQualifierDeclaration('Qual1', type='string'),
            exp_hash_equal=True,
        ),
        None, None, True
    ),
    (
        "Name, equal with different lexical case",
        dict(
            obj1=CIMQualifierDeclaration('Qual1', type='string'),
            obj2=CIMQualifierDeclaration('quAL1', type='string'),
            exp_hash_equal=True,
        ),
        None, None, True
    ),
    (
        "Name, different",
        dict(
            obj1=CIMQualifierDeclaration('Qual1', type='string'),
            obj2=CIMQualifierDeclaration('Qual1_x', type='string'),
            exp_hash_equal=False,
        ),
        None, None, True
    ),

    # Type tests
    (
        "Type, different",
        dict(
            obj1=CIMQualifierDeclaration('Qual1', type='uint8'),
            obj2=CIMQualifierDeclaration('Qual1', type='sint8'),
            exp_hash_equal=False,
        ),
        None, None, True
    ),

    # Value tests
    (
        "Value, strings with different lexical case",
        dict(
            obj1=CIMQualifierDeclaration('Qual1', type='string', value='abc'),
            obj2=CIMQualifierDeclaration('Qual1', type='string', value='Abc'),
            exp_hash_equal=False,
        ),
        None, None, True
    ),
    (
        "Value, strings with None / string",
        dict(
            obj1=CIMQualifierDeclaration('Qual1', type='string', value=None),
            obj2=CIMQualifierDeclaration('Qual1', type='string', value='abc'),
            exp_hash_equal=False,
        ),
        None, None, True
    ),
    (
        "Value, strings with string / None",
        dict(
            obj1=CIMQualifierDeclaration('Qual1', type='string', value='abc'),
            obj2=CIMQualifierDeclaration('Qual1', type='string', value=None),
            exp_hash_equal=False,
        ),
        None, None, True
    ),
    (
        "Value, strings with None / None",
        dict(
            obj1=CIMQualifierDeclaration('Qual1', type='string', value=None),
            obj2=CIMQualifierDeclaration('Qual1', type='string', value=None),
            exp_hash_equal=True,
        ),
        None, None, True
    ),


    # Is_array tests
    (
        "Is_array, equal",
        dict(
            obj1=CIMQualifierDeclaration('Qual1', type='string',
                                         is_array=True),
            obj2=CIMQualifierDeclaration('Qual1', type='string',
                                         is_array=True),
            exp_hash_equal=True,
        ),
        None, None, True
    ),
    (
        "Is_array, different",
        dict(
            obj1=CIMQualifierDeclaration('Qual1', type='string',
                                         is_array=True),
            obj2=CIMQualifierDeclaration('Qual1', type='string',
                                         is_array=False),
            exp_hash_equal=False,
        ),
        None, None, True
    ),

    # Array_size tests
    (
        "Array_size, equal",
        dict(
            obj1=CIMQualifierDeclaration('Qual1', type='string', is_array=True,
                                         array_size=2),
            obj2=CIMQualifierDeclaration('Qual1', type='string', is_array=True,
                                         array_size=2),
            exp_hash_equal=True,
        ),
        None, None, True
    ),
    (
        "Array_size, different",
        dict(
            obj1=CIMQualifierDeclaration('Qual1', type='string', is_array=True,
                                         array_size=2),
            obj2=CIMQualifierDeclaration('Qual1', type='string', is_array=True,
                                         array_size=3),
            exp_hash_equal=False,
        ),
        None, None, True
    ),

    # Scopes tests
    (
        "Matching scopes, names with same lexical case",
        dict(
            obj1=CIMQualifierDeclaration(
                'Qual1', type='string', scopes=[
                    ('CLASS', True),
                ]
            ),
            obj2=CIMQualifierDeclaration(
                'Qual1', type='string', scopes=[
                    ('CLASS', True),
                ]
            ),
            exp_hash_equal=True,
        ),
        None, None, True
    ),
    (
        "Matching scopes, names with different lexical case",
        dict(
            obj1=CIMQualifierDeclaration(
                'Qual1', type='string', scopes=[
                    ('CLASS', True),
                ]
            ),
            obj2=CIMQualifierDeclaration(
                'Qual1', type='string', scopes=[
                    ('claSS', True),
                ]
            ),
            exp_hash_equal=True,
        ),
        None, None, True
    ),
    (
        "Non-matching scopes, one scope more",
        dict(
            obj1=CIMQualifierDeclaration(
                'Qual1', type='string', scopes=[
                    ('CLASS', True),
                ]
            ),
            obj2=CIMQualifierDeclaration(
                'Qual1', type='string', scopes=[
                    ('CLASS', True),
                    ('ASSOCIAION', True),
                ]
            ),
            exp_hash_equal=False,
        ),
        None, None, True
    ),
    (
        "Non-matching scopes, one scope less",
        dict(
            obj1=CIMQualifierDeclaration(
                'Qual1', type='string', scopes=[
                    ('CLASS', True),
                    ('ASSOCIAION', True),
                ]
            ),
            obj2=CIMQualifierDeclaration(
                'Qual1', type='string', scopes=[
                    ('CLASS', True),
                ]
            ),
            exp_hash_equal=False,
        ),
        None, None, True
    ),
    (
        "Non-matching scopes, different scopes",
        dict(
            obj1=CIMQualifierDeclaration(
                'Qual1', type='string', scopes=[
                    ('ASSOCIAION', True),
                ]
            ),
            obj2=CIMQualifierDeclaration(
                'Qual1', type='string', scopes=[
                    ('CLASS', True),
                ]
            ),
            exp_hash_equal=False,
        ),
        None, None, True
    ),

    # Overridable tests
    (
        "Overridable, equal",
        dict(
            obj1=CIMQualifierDeclaration('Qual1', value=None, type='string',
                                         overridable=True),
            obj2=CIMQualifierDeclaration('Qual1', value=None, type='string',
                                         overridable=True),
            exp_hash_equal=True,
        ),
        None, None, True
    ),
    (
        "Overridable, different",
        dict(
            obj1=CIMQualifierDeclaration('Qual1', value=None, type='string',
                                         overridable=True),
            obj2=CIMQualifierDeclaration('Qual1', value=None, type='string',
                                         overridable=False),
            exp_hash_equal=False,
        ),
        None, None, True
    ),

    # Tosubclass tests
    (
        "Tosubclass, equal",
        dict(
            obj1=CIMQualifierDeclaration('Qual1', value=None, type='string',
                                         tosubclass=True),
            obj2=CIMQualifierDeclaration('Qual1', value=None, type='string',
                                         tosubclass=True),
            exp_hash_equal=True,
        ),
        None, None, True
    ),
    (
        "Tosubclass, different",
        dict(
            obj1=CIMQualifierDeclaration('Qual1', value=None, type='string',
                                         tosubclass=True),
            obj2=CIMQualifierDeclaration('Qual1', value=None, type='string',
                                         tosubclass=False),
            exp_hash_equal=False,
        ),
        None, None, True
    ),

    # Toinstance tests
    (
        "Toinstance, equal",
        dict(
            obj1=CIMQualifierDeclaration('Qual1', value=None, type='string',
                                         toinstance=True),
            obj2=CIMQualifierDeclaration('Qual1', value=None, type='string',
                                         toinstance=True),
            exp_hash_equal=True,
        ),
        None, None, True
    ),
    (
        "Toinstance, different",
        dict(
            obj1=CIMQualifierDeclaration('Qual1', value=None, type='string',
                                         toinstance=True),
            obj2=CIMQualifierDeclaration('Qual1', value=None, type='string',
                                         toinstance=False),
            exp_hash_equal=False,
        ),
        None, None, True
    ),

    # Translatable tests
    (
        "Translatable, equal",
        dict(
            obj1=CIMQualifierDeclaration('Qual1', value=None, type='string',
                                         translatable=True),
            obj2=CIMQualifierDeclaration('Qual1', value=None, type='string',
                                         translatable=True),
            exp_hash_equal=True,
        ),
        None, None, True
    ),
    (
        "Translatable, different",
        dict(
            obj1=CIMQualifierDeclaration('Qual1', value=None, type='string',
                                         translatable=True),
            obj2=CIMQualifierDeclaration('Qual1', value=None, type='string',
                                         translatable=False),
            exp_hash_equal=False,
        ),
        None, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    testcases_CIMQualifierDeclaration_hash)
@pytest_extensions.test_function
def test_CIMQualifierDeclaration_hash(
        desc, kwargs, exp_exc_types, exp_warn_types, condition):
    """
    All test cases for CIMQualifierDeclaration.__hash__().
    """

    obj1 = kwargs['obj1']
    obj2 = kwargs['obj2']

    # Double check they are different objects
    assert id(obj1) != id(obj2)

    # The code to be tested
    hash1 = hash(obj1)
    hash2 = hash(obj2)

    exp_hash_equal = kwargs['exp_hash_equal']

    assert (hash1 == hash2) == exp_hash_equal


class Test_CIMQualifierDeclaration_str(object):
    # pylint: disable=too-few-public-methods
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
    # pylint: disable=too-few-public-methods
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


class Test_CIMQualifierDeclaration_tomof(object):
    # pylint: disable=too-few-public-methods
    """
    Test CIMQualifierDeclaration.tomof().
    """

    testcases = [
        # Testcases for CIMQualifierDeclaration.tomof().
        # Each testcase has these items:
        # * desc: Short testcase description.
        # * obj: Object to be tested.
        # * exp_result: Expected MOF string, if expected to succeed.
        #     Exception type, if expected to fail.
        # * exp_warn_type: Expected warning type.
        #     None, if no warning expected.
        # * condition: Condition for testcase to run.
        (
            "all components",
            CIMQualifierDeclaration(
                name='Q1',
                type='string',
                is_array=True,
                array_size=5,
                value=["abc"],
                scopes=[('PROPERTY', True), ('METHOD', True),
                        ('PARAMETER', True)],
                overridable=True,
                tosubclass=True,
                toinstance=True,
                translatable=True,
            ),
            u"""\
Qualifier Q1 : string[5] = { "abc" },
    Scope(property, method, parameter),
    Flavor(EnableOverride, ToSubclass, Translatable);
""",
            None, CHECK_0_12_0  # unpredictable order of scopes before 0.12
        ),
        (
            "string type, no default value",
            CIMQualifierDeclaration(
                name='Q1',
                type='string',
                value=None,
            ),
            u"""\
Qualifier Q1 : string,
    Scope();
""" \
            if CHECK_0_12_0 else \
            u"""\
Qualifier Q1 : string,
    Scope();""",
            None, True
        ),
        (
            "string type, default value with escape sequences dq,sq,bs",
            CIMQualifierDeclaration(
                name='Q1',
                type='string',
                value="dq=\",sq=\',bs=\\",
            ),
            u"""\
Qualifier Q1 : string = "dq=\\",sq=\\',bs=\\\\",
    Scope();
""" \
            if CHECK_0_12_0 else \
            u"""\
Qualifier Q1 : string = dq=\",sq=\',bs=\\,
    Scope();""",
            None, True
        ),
        (
            "string type, default value with escape sequences bt,tb,nl,vt,cr",
            CIMQualifierDeclaration(
                name='Q1',
                type='string',
                value="bt=\b,tb=\t,nl=\n,vt=\f,cr=\r",
            ),
            u"""\
Qualifier Q1 : string = "bt=\\b,tb=\\t,nl=\\n,vt=\\f,cr=\\r",
    Scope();
""" \
            if CHECK_0_12_0 else \
            u"""\
Qualifier Q1 : string = bt=\b,tb=\t,nl=\n,vt=\f,cr=\r,
    Scope();""",
            None, True
        ),
        (
            "char16 type, default value nl",
            CIMQualifierDeclaration(
                name='Q1',
                type='char16',
                value="\n",
            ),
            u"""\
Qualifier Q1 : char16 = '\\n',
    Scope();
""" \
            if CHECK_0_12_0 else \
            u"""\
Qualifier Q1 : char16 = '\\n',
    Scope();""",
            None, False  # TODO 01/18 AM Enable once char16 uses single quotes
        ),
        (
            "boolean type, default value",
            CIMQualifierDeclaration(
                name='Q1',
                type='boolean',
                value=False,
            ),
            u"""\
Qualifier Q1 : boolean = false,
    Scope();
""" \
            if CHECK_0_12_0 else \
            u"""\
Qualifier Q1 : boolean = false,
    Scope();""",
            None, True
        ),
        (
            "uint32 type, default value",
            CIMQualifierDeclaration(
                name='Q1',
                type='uint32',
                value=42,
            ),
            u"""\
Qualifier Q1 : uint32 = 42,
    Scope();
""" \
            if CHECK_0_12_0 else \
            u"""\
Qualifier Q1 : uint32 = 42,
    Scope();""",
            None, True
        ),
        (
            "real32 type, default value",
            CIMQualifierDeclaration(
                name='Q1',
                type='real32',
                value=Real32(42.1),
            ),
            u"""\
Qualifier Q1 : real32 = 42.1,
    Scope();
""",
            None, CHECK_0_12_0  # unpredictable value before 0.12
        ),
        (
            "datetime type, default value",
            CIMQualifierDeclaration(
                name='Q1',
                type='datetime',
                value=CIMDateTime('20140924193040.654321+120'),
            ),
            u"""\
Qualifier Q1 : datetime = "20140924193040.654321+120",
    Scope();
""" \
            if CHECK_0_12_0 else \
            u"""\
Qualifier Q1 : datetime = 20140924193040.654321+120,
    Scope();""",
            None, True
        ),
        (
            "string array of variable size",
            CIMQualifierDeclaration(
                name='Q1',
                type='string',
                is_array=True,
                array_size=None,
                value=["abc", "def"],
            ),
            u"""\
Qualifier Q1 : string[] = { "abc", "def" },
    Scope();
""" \
            if CHECK_0_12_0 else \
            u"""\
Qualifier Q1 : string[] = {abc, def},
    Scope();""",
            None, True
        ),
        (
            "string array of fixed size",
            CIMQualifierDeclaration(
                name='Q1',
                type='string',
                is_array=True,
                array_size=5,
                value=["abc", "def"],
            ),
            u"""\
Qualifier Q1 : string[5] = { "abc", "def" },
    Scope();
""" \
            if CHECK_0_12_0 else \
            u"""\
Qualifier Q1 : string[5] = {abc, def},
    Scope();""",
            None, True
        ),
        (
            "single scope",
            CIMQualifierDeclaration(
                name='Q1',
                type='string',
                scopes=dict(CLASS=True),
            ),
            u"""\
Qualifier Q1 : string,
    Scope(class);
""" \
            if CHECK_0_12_0 else \
            u"""\
Qualifier Q1 : string,
    Scope(class);""",
            None, True
        ),
        (
            "all scopes as a list",
            CIMQualifierDeclaration(
                name='Q1',
                type='string',
                scopes=[('CLASS', True), ('ASSOCIATION', True),
                        ('INDICATION', True), ('PROPERTY', True),
                        ('REFERENCE', True), ('METHOD', True),
                        ('PARAMETER', True)],
            ),
            # pylint: disable=line-too-long
            u"""\
Qualifier Q1 : string,
    Scope(class, association, indication, property, reference, method, parameter);
""",  # noqa: E501
            None, CHECK_0_12_0  # unpredictable order of scopes before 0.12
        ),
        (
            "all scopes as any",
            CIMQualifierDeclaration(
                name='Q1',
                type='string',
                scopes=dict(ANY=True),
            ),
            u"""\
Qualifier Q1 : string,
    Scope(any);
""" \
            if CHECK_0_12_0 else \
            u"""\
Qualifier Q1 : string,
    Scope(any);""",
            None, True
        ),
        (
            "flavor EnableOverride",
            CIMQualifierDeclaration(
                name='Q1',
                type='string',
                overridable=True,
            ),
            u"""\
Qualifier Q1 : string,
    Scope(),
    Flavor(EnableOverride);
""" \
            if CHECK_0_12_0 else \
            u"""\
Qualifier Q1 : string,
    Scope(),
    Flavor(EnableOverride, Restricted);""",
            None, True
        ),
        (
            "flavor ToSubclass EnableOverride",
            CIMQualifierDeclaration(
                name='Q1',
                type='string',
                overridable=True,
                tosubclass=True,
            ),
            u"""\
Qualifier Q1 : string,
    Scope(),
    Flavor(EnableOverride, ToSubclass);
""" \
            if CHECK_0_12_0 else \
            u"""\
Qualifier Q1 : string,
    Scope(),
    Flavor(EnableOverride, ToSubclass);""",
            None, True
        ),
        (
            "flavor DisableOverride",
            CIMQualifierDeclaration(
                name='Q1',
                type='string',
                overridable=False,
            ),
            u"""\
Qualifier Q1 : string,
    Scope(),
    Flavor(DisableOverride);
""" \
            if CHECK_0_12_0 else \
            u"""\
Qualifier Q1 : string,
    Scope();""",
            None, True
        ),
        (
            "flavor Restricted",
            CIMQualifierDeclaration(
                name='Q1',
                type='string',
                tosubclass=False,
            ),
            u"""\
Qualifier Q1 : string,
    Scope(),
    Flavor(Restricted);
""" \
            if CHECK_0_12_0 else \
            u"""\
Qualifier Q1 : string,
    Scope();""",
            None, True
        ),
        (
            "flavor ToSubclass",
            CIMQualifierDeclaration(
                name='Q1',
                type='string',
                tosubclass=True,
            ),
            u"""\
Qualifier Q1 : string,
    Scope(),
    Flavor(ToSubclass);
""" \
            if CHECK_0_12_0 else \
            u"""\
Qualifier Q1 : string,
    Scope(),
    Flavor(DisableOverride, ToSubclass);""",
            None, True
        ),
        (
            "flavor Translatable",
            CIMQualifierDeclaration(
                name='Q1',
                type='string',
                translatable=True,
            ),
            u"""\
Qualifier Q1 : string,
    Scope(),
    Flavor(Translatable);
""" \
            if CHECK_0_12_0 else \
            u"""\
Qualifier Q1 : string,
    Scope(),
    Flavor(DisableOverride, Restricted, Translatable);""",
            None, True
        ),
        (
            "flavor ToInstance (not generated because not in DSP0004)",
            CIMQualifierDeclaration(
                name='Q1',
                type='string',
                toinstance=True,
            ),
            u"""\
Qualifier Q1 : string,
    Scope();
""" \
            if CHECK_0_12_0 else \
            u"""\
Qualifier Q1 : string,
    Scope();""",
            None, True
        ),
    ]

    @pytest.mark.parametrize(
        "desc, obj, exp_result, exp_warn_type, condition",
        testcases)
    def test_CIMQualifierDeclaration_tomof(
            self, desc, obj, exp_result, exp_warn_type, condition):
        """All test cases for CIMQualifierDeclaration.tomof()."""

        if not condition:
            pytest.skip("Condition for test case not met")

        if isinstance(exp_result, type) and issubclass(exp_result, Exception):
            # We expect an exception
            exp_exc_type = exp_result
            exp_mof = None
        else:
            # We expect the code to return
            exp_exc_type = None
            exp_mof = exp_result

        if condition == 'pdb':
            import pdb
            pdb.set_trace()

        if exp_warn_type:
            with pytest.warns(exp_warn_type) as rec_warnings:
                if exp_exc_type:
                    with pytest.raises(exp_exc_type):

                        # The code to be tested
                        mof = obj.tomof()

                else:

                    # The code to be tested
                    mof = obj.tomof()

            assert len(rec_warnings) == 1

        else:
            if exp_exc_type:
                with pytest.raises(exp_exc_type):

                    # The code to be tested
                    mof = obj.tomof()

            else:

                # The code to be tested
                mof = obj.tomof()

        if exp_mof:

            assert isinstance(mof, six.text_type)
            assert mof == exp_mof


class Test_tocimxml(object):  # pylint: disable=too-few-public-methods

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

    ref1_str = 'http://host/ns:CN.k1="abc"'
    ref1_obj = CIMInstanceName(classname='CN', keybindings=dict(k1="abc"),
                               namespace='ns', host='host')
    ref2_obj = CIMClassName('CIM_Foo')

    testcases_succeeds = [
        # Testcases where cimvalue() succeeds.
        # Each testcase has these items:
        # * value: The input value.
        # * type: The input type (as a CIM type name).
        # * exp_obj: Expected CIM value object.
        # * exp_warn_type: Expected warning type.
        # * condition: Condition for testcase to run.

        # Test cases where: Type is None (and is inferred from the value)

        (None, None, None, None, CHECK_0_12_0),

        (u'a', None, u'a', None, CHECK_0_12_0),
        (b'a', None, u'a', None, CHECK_0_12_0),
        ('true', None, 'true', None, CHECK_0_12_0),
        ('false', None, 'false', None, CHECK_0_12_0),
        (datetime1_str, None, datetime1_str, None, CHECK_0_12_0),
        (timedelta1_str, None, timedelta1_str, None, CHECK_0_12_0),
        (ref1_str, None, ref1_str, None, CHECK_0_12_0),

        (True, None, True, None, CHECK_0_12_0),
        (False, None, False, None, CHECK_0_12_0),

        (datetime1_dt, None, datetime1_obj, None, CHECK_0_12_0),
        (timedelta1_td, None, timedelta1_obj, None, CHECK_0_12_0),

        # Test cases where: Type is string

        (None, 'string', None, None, CHECK_0_12_0),

        (u'', 'string', u'', None, CHECK_0_12_0),
        (u'a', 'string', u'a', None, CHECK_0_12_0),
        (u'abc', 'string', u'abc', None, CHECK_0_12_0),
        (u'\u00E4', 'string', u'\u00E4', None, CHECK_0_12_0),
        # U+00E4 = lower case a umlaut

        (b'', 'string', u'', None, CHECK_0_12_0),
        (b'a', 'string', u'a', None, CHECK_0_12_0),
        (b'abc', 'string', u'abc', None, CHECK_0_12_0),

        # Test cases where: Type is char16

        (None, 'char16', None, None, CHECK_0_12_0),

        (u'', 'char16', u'', None, CHECK_0_12_0),
        (u'a', 'char16', u'a', None, CHECK_0_12_0),
        (u'\u00E4', 'char16', u'\u00E4', None, CHECK_0_12_0),

        (b'', 'char16', u'', None, CHECK_0_12_0),
        (b'a', 'char16', u'a', None, CHECK_0_12_0),

        # Test cases where: Type is boolean

        (None, 'boolean', None, None, CHECK_0_12_0),

        (True, 'boolean', True, None, CHECK_0_12_0),
        (False, 'boolean', False, None, CHECK_0_12_0),

        ('abc', 'boolean', True, None, CHECK_0_12_0),
        # No special treatment of the following two strings
        ('true', 'boolean', True, None, CHECK_0_12_0),
        ('false', 'boolean', True, None, CHECK_0_12_0),
        ('', 'boolean', False, None, CHECK_0_12_0),

        (0, 'boolean', False, None, CHECK_0_12_0),
        (1, 'boolean', True, None, CHECK_0_12_0),
        (-1, 'boolean', True, None, CHECK_0_12_0),

        # Test cases where: Type is an unsigned integer

        (None, 'uint8', None, None, CHECK_0_12_0),
        (0, 'uint8', Uint8(0), None, CHECK_0_12_0),
        (max_uint8, 'uint8', Uint8(max_uint8), None, CHECK_0_12_0),
        (Uint8(0), 'uint8', Uint8(0), None, CHECK_0_12_0),
        (Uint8(max_uint8), 'uint8', Uint8(max_uint8), None, CHECK_0_12_0),

        (None, 'uint16', None, None, CHECK_0_12_0),
        (0, 'uint16', Uint16(0), None, CHECK_0_12_0),
        (max_uint16, 'uint16', Uint16(max_uint16), None, CHECK_0_12_0),
        (Uint16(0), 'uint16', Uint16(0), None, CHECK_0_12_0),
        (Uint16(max_uint16), 'uint16', Uint16(max_uint16), None, CHECK_0_12_0),

        (None, 'uint32', None, None, CHECK_0_12_0),
        (0, 'uint32', Uint32(0), None, CHECK_0_12_0),
        (max_uint32, 'uint32', Uint32(max_uint32), None, CHECK_0_12_0),
        (Uint32(0), 'uint32', Uint32(0), None, CHECK_0_12_0),
        (Uint32(max_uint32), 'uint32', Uint32(max_uint32), None, CHECK_0_12_0),

        (None, 'uint64', None, None, CHECK_0_12_0),
        (0, 'uint64', Uint64(0), None, CHECK_0_12_0),
        (max_uint64, 'uint64', Uint64(max_uint64), None, CHECK_0_12_0),
        (Uint64(0), 'uint64', Uint64(0), None, CHECK_0_12_0),
        (Uint64(max_uint64), 'uint64', Uint64(max_uint64), None, CHECK_0_12_0),

        # Test cases where: Type is a signed integer

        (None, 'sint8', None, None, CHECK_0_12_0),
        (min_sint8, 'sint8', Sint8(min_sint8), None, CHECK_0_12_0),
        (max_sint8, 'sint8', Sint8(max_sint8), None, CHECK_0_12_0),
        (Sint8(min_sint8), 'sint8', Sint8(min_sint8), None, CHECK_0_12_0),
        (Sint8(max_sint8), 'sint8', Sint8(max_sint8), None, CHECK_0_12_0),

        (None, 'sint16', None, None, CHECK_0_12_0),
        (min_sint16, 'sint16', Sint16(min_sint16), None, CHECK_0_12_0),
        (max_sint16, 'sint16', Sint16(max_sint16), None, CHECK_0_12_0),
        (Sint16(min_sint16), 'sint16', Sint16(min_sint16), None, CHECK_0_12_0),
        (Sint16(max_sint16), 'sint16', Sint16(max_sint16), None, CHECK_0_12_0),

        (None, 'sint32', None, None, CHECK_0_12_0),
        (min_sint32, 'sint32', Sint32(min_sint32), None, CHECK_0_12_0),
        (max_sint32, 'sint32', Sint32(max_sint32), None, CHECK_0_12_0),
        (Sint32(min_sint32), 'sint32', Sint32(min_sint32), None, CHECK_0_12_0),
        (Sint32(max_sint32), 'sint32', Sint32(max_sint32), None, CHECK_0_12_0),

        (None, 'sint64', None, None, CHECK_0_12_0),
        (min_sint64, 'sint64', Sint64(min_sint64), None, CHECK_0_12_0),
        (max_sint64, 'sint64', Sint64(max_sint64), None, CHECK_0_12_0),
        (Sint64(min_sint64), 'sint64', Sint64(min_sint64), None, CHECK_0_12_0),
        (Sint64(max_sint64), 'sint64', Sint64(max_sint64), None, CHECK_0_12_0),

        # Test cases where: Type is a real

        (None, 'real32', None, None, CHECK_0_12_0),
        (0, 'real32', Real32(0), None, CHECK_0_12_0),
        (3.14, 'real32', Real32(3.14), None, CHECK_0_12_0),
        (-42E7, 'real32', Real32(-42E7), None, CHECK_0_12_0),
        (-42E-7, 'real32', Real32(-42E-7), None, CHECK_0_12_0),

        (None, 'real64', None, None, CHECK_0_12_0),
        (0, 'real64', Real64(0), None, CHECK_0_12_0),
        (3.14, 'real64', Real64(3.14), None, CHECK_0_12_0),
        (-42E7, 'real64', Real64(-42E7), None, CHECK_0_12_0),
        (-42E-7, 'real64', Real64(-42E-7), None, CHECK_0_12_0),

        # Test cases where: Type is datetime

        (None, 'datetime', None, None, CHECK_0_12_0),

        (datetime1_dt, 'datetime', datetime1_obj, None, CHECK_0_12_0),
        (datetime1_str, 'datetime', datetime1_obj, None, CHECK_0_12_0),
        (datetime1_obj, 'datetime', datetime1_obj, None, CHECK_0_12_0),

        (timedelta1_td, 'datetime', timedelta1_obj, None, CHECK_0_12_0),
        (timedelta1_str, 'datetime', timedelta1_obj, None, CHECK_0_12_0),
        (timedelta1_obj, 'datetime', timedelta1_obj, None, CHECK_0_12_0),

        # Test cases where: Type is reference

        (None, 'reference', None, None, CHECK_0_12_0),

        (ref1_str, 'reference', ref1_obj, None, CHECK_0_12_0),
        (ref1_obj, 'reference', ref1_obj, None, CHECK_0_12_0),
        (ref2_obj, 'reference', ref2_obj, None, CHECK_0_12_0),
    ]

    @pytest.mark.parametrize(
        "value, type, exp_obj, exp_warn_type, condition",
        testcases_succeeds)
    def test_cimvalue_succeeds(
            self, value, type, exp_obj, exp_warn_type, condition):
        # pylint: disable=redefined-builtin
        """All test cases where cimvalue() succeeds."""

        if not condition:
            pytest.skip("Condition for test case not met")

        if exp_warn_type is None:

            # The code to be tested
            obj = cimvalue(value, type)

        else:
            with pytest.warns(exp_warn_type) as rec_warnings:

                # The code to be tested
                obj = cimvalue(value, type)

            assert len(rec_warnings) == 1

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


class Test_mofstr(object):  # pylint: disable=too-few-public-methods
    """Test cases for cim_obj.mofstr()."""

    # Default input arguments if not specified in testcase
    # They do not necessarily have to match the default values.
    default_kwargs = dict(
        indent=cim_obj.MOF_INDENT,
        maxline=cim_obj.MAX_MOF_LINE,
        line_pos=0,
        end_space=0,
        avoid_splits=False,
        quote_char=u'"',
    )

    testcases = [
        # Testcases for cim_obj.mofstr().
        # Each testcase has these items:
        # * desc: Short testcase description.
        # * kwargs: Dict of keyword arguments for mofstr():
        #   - value: Value to be tested.
        #   - indent: Indentation for new lines.
        #   - maxline: Maximum line length.
        #   - line_pos: Length of content already on the current line.
        #   - end_space: Length of space to be left free on the last line.
        #   - avoid_splits: Avoid splits at the price of starting a new line.
        #   - quote_char: Character to be used for surrounding the string parts.
        # * exp_result: Expected result tuple, if expected to succeed.
        #     Exception type, if expected to fail.
        # * exp_warn_type: Expected warning type.
        #     None, if no warning expected.
        # * condition: Condition for testcase to run.

        # Some simple cases
        (
            "Empty string",
            dict(value=u''), (u'""', 2), None, True,
        ),
        (
            "Single character",
            dict(value=u'c'), (u'"c"', 3), None, True,
        ),

        # Test whitespace preservation
        (
            "String with inside blank",
            dict(value=u'c d'), (u'"c d"', 5), None, True,
        ),
        (
            "String with leading blank",
            dict(value=u' d'), (u'" d"', 4), None, True,
        ),
        (
            "String with trailing blank",
            dict(value=u'c '), (u'"c "', 4), None, True,
        ),
        (
            "String that is a blank",
            dict(value=u' '), (u'" "', 3), None, True,
        ),
        (
            "String with two inside blanks",
            dict(value=u'c  d'), (u'"c  d"', 6), None, True,
        ),

        # Test single quote escaping
        (
            "String that is single quote",
            dict(value=u'\''), (u'"\\\'"', 4), None, True,
        ),
        (
            "String with inside single quote",
            dict(value=u'c\'d'), (u'"c\\\'d"', 6), None, True,
        ),
        (
            "String with two inside single quotes",
            dict(value=u'c\'\'d'), (u'"c\\\'\\\'d"', 8), None, True,
        ),

        # Test double quote escaping
        (
            "String that is double quote",
            dict(value=u'"'), (u'"\\""', 4), None, True,
        ),
        (
            "String with inside double quote",
            dict(value=u'c"d'), (u'"c\\"d"', 6), None, True,
        ),
        (
            "String with two inside double quotes",
            dict(value=u'c""d'), (u'"c\\"\\"d"', 8), None, True,
        ),

        # Test backslash escaping
        (
            "String that is backslash",
            dict(value=u'\\'), (u'"\\\\"', 4), None, True,
        ),
        (
            "String with leading backslash",
            dict(value=u'\\d'), (u'"\\\\d"', 5), None, True,
        ),
        (
            "String with trailing backslash",
            dict(value=u'c\\'), (u'"c\\\\"', 5), None, True,
        ),
        (
            "String with inside backslash",
            dict(value=u'c\\d'), (u'"c\\\\d"', 6), None, True,
        ),
        (
            "String with two inside backslashes",
            dict(value=u'c\\\\d'), (u'"c\\\\\\\\d"', 8), None, True,
        ),

        # Test MOF named escape sequences
        (
            "String that is escapable character \\b",
            dict(value=u'\b'), (u'"\\b"', 4), None, True,
        ),
        (
            "String that is escapable character \\t",
            dict(value=u'\t'), (u'"\\t"', 4), None, True,
        ),
        (
            "String that is escapable character \\n",
            dict(value=u'\n'), (u'"\\n"', 4), None, True,
        ),
        (
            "String that is escapable character \\f",
            dict(value=u'\f'), (u'"\\f"', 4), None, True,
        ),
        (
            "String that is escapable character \\r",
            dict(value=u'\r'), (u'"\\r"', 4), None, True,
        ),
        (
            "String with inside escapable character \\b",
            dict(value=u'c\bd'), (u'"c\\bd"', 6), None, True,
        ),
        (
            "String with inside escapable character \\t",
            dict(value=u'c\td'), (u'"c\\td"', 6), None, True,
        ),
        (
            "String with inside escapable character \\n",
            dict(value=u'c\nd'), (u'"c\\nd"', 6), None, True,
        ),
        (
            "String with inside escapable character \\f",
            dict(value=u'c\fd'), (u'"c\\fd"', 6), None, True,
        ),
        (
            "String with inside escapable character \\r",
            dict(value=u'c\rd'), (u'"c\\rd"', 6), None, True,
        ),

        # Test an already MOF-escaped sequence.
        # Such a sequence is treated as separate characters, i.e. backslash
        # gets escaped, and the following char gets escaped on its own.
        # These sequences were treated specially before v0.9, by parsing them
        # as already-escaped MOF sequences and passing them through unchanged.
        (
            "String that is escaped character \\b",
            dict(value=u'\\b'), (u'"\\\\b"', 5), None, True
        ),
        (
            "String that is escaped character \\t",
            dict(value=u'\\t'), (u'"\\\\t"', 5), None, True
        ),
        (
            "String that is escaped character \\n",
            dict(value=u'\\n'), (u'"\\\\n"', 5), None, True
        ),
        (
            "String that is escaped character \\f",
            dict(value=u'\\f'), (u'"\\\\f"', 5), None, True
        ),
        (
            "String that is escaped character \\r",
            dict(value=u'\\r'), (u'"\\\\r"', 5), None, True
        ),
        (
            "String that is escaped character \' ",
            dict(value=u'\\\''), (u'"\\\\\\\'"', 6), None, True
        ),
        (
            "String that is escaped character \" ",
            dict(value=u'\\"'), (u'"\\\\\\""', 6), None, True
        ),
        (
            "String with inside escaped character \\b",
            dict(value=u'c\\bd'), (u'"c\\\\bd"', 7), None, True
        ),
        (
            "String with inside escaped character \\t",
            dict(value=u'c\\td'), (u'"c\\\\td"', 7), None, True
        ),
        (
            "String with inside escaped character \\n",
            dict(value=u'c\\nd'), (u'"c\\\\nd"', 7), None, True
        ),
        (
            "String with inside escaped character \\f",
            dict(value=u'c\\fd'), (u'"c\\\\fd"', 7), None, True
        ),
        (
            "String with inside escaped character \\r",
            dict(value=u'c\\rd'), (u'"c\\\\rd"', 7), None, True
        ),
        (
            "String with inside escaped character \' ",
            dict(value=u'c\\\'d'), (u'"c\\\\\\\'d"', 8), None, True
        ),
        (
            "String with inside escaped character \" ",
            dict(value=u'c\\"d'), (u'"c\\\\\\"d"', 8), None, True
        ),

        # Test backslash followed by MOF-escapable character
        (
            "String with backslash and escapable character \\b",
            dict(value=u'\\\b'), (u'"\\\\\\b"', 6), None, True
        ),
        (
            "String with backslash and escapable character \\t",
            dict(value=u'\\\t'), (u'"\\\\\\t"', 6), None, True
        ),
        (
            "String with backslash and escapable character \\n",
            dict(value=u'\\\n'), (u'"\\\\\\n"', 6), None, True
        ),
        (
            "String with backslash and escapable character \\f",
            dict(value=u'\\\f'), (u'"\\\\\\f"', 6), None, True
        ),
        (
            "String with backslash and escapable character \\r",
            dict(value=u'\\\r'), (u'"\\\\\\r"', 6), None, True
        ),
        (
            "String with inside backslash and escapable character \\b",
            dict(value=u'c\\\bd'), (u'"c\\\\\\bd"', 8), None, True
        ),
        (
            "String with inside backslash and escapable character \\t",
            dict(value=u'c\\\td'), (u'"c\\\\\\td"', 8), None, True
        ),
        (
            "String with inside backslash and escapable character \\n",
            dict(value=u'c\\\nd'), (u'"c\\\\\\nd"', 8), None, True
        ),
        (
            "String with inside backslash and escapable character \\f",
            dict(value=u'c\\\fd'), (u'"c\\\\\\fd"', 8), None, True
        ),
        (
            "String with inside backslash and escapable character \\r",
            dict(value=u'c\\\rd'), (u'"c\\\\\\rd"', 8), None, True
        ),

        # Test control characters
        (
            "String that is control character U+0001",
            dict(value=u'\u0001'), (u'"\\x0001"', 8), None, True
        ),
        (
            "String that is control character U+0002",
            dict(value=u'\u0002'), (u'"\\x0002"', 8), None, True
        ),
        (
            "String that is control character U+0003",
            dict(value=u'\u0003'), (u'"\\x0003"', 8), None, True
        ),
        (
            "String that is control character U+0004",
            dict(value=u'\u0004'), (u'"\\x0004"', 8), None, True
        ),
        (
            "String that is control character U+0005",
            dict(value=u'\u0005'), (u'"\\x0005"', 8), None, True
        ),
        (
            "String that is control character U+0006",
            dict(value=u'\u0006'), (u'"\\x0006"', 8), None, True
        ),
        (
            "String that is control character U+0007",
            dict(value=u'\u0007'), (u'"\\x0007"', 8), None, True
        ),
        (
            "String that is control character U+0008",
            dict(value=u'\u0008'), (u'"\\b"', 4), None, True
        ),
        (
            "String that is control character U+0009",
            dict(value=u'\u0009'), (u'"\\t"', 4), None, True
        ),
        (
            "String that is control character U+000A",
            dict(value=u'\u000A'), (u'"\\n"', 4), None, True
        ),
        (
            "String that is control character U+000B",
            dict(value=u'\u000B'), (u'"\\x000B"', 8), None, True
        ),
        (
            "String that is control character U+000C",
            dict(value=u'\u000C'), (u'"\\f"', 4), None, True
        ),
        (
            "String that is control character U+000D",
            dict(value=u'\u000D'), (u'"\\r"', 4), None, True
        ),
        (
            "String that is control character U+000E",
            dict(value=u'\u000E'), (u'"\\x000E"', 8), None, True
        ),
        (
            "String that is control character U+000F",
            dict(value=u'\u000F'), (u'"\\x000F"', 8), None, True
        ),
        (
            "String that is control character U+0010",
            dict(value=u'\u0010'), (u'"\\x0010"', 8), None, True
        ),
        (
            "String that is control character U+0011",
            dict(value=u'\u0011'), (u'"\\x0011"', 8), None, True
        ),
        (
            "String that is control character U+0012",
            dict(value=u'\u0012'), (u'"\\x0012"', 8), None, True
        ),
        (
            "String that is control character U+0013",
            dict(value=u'\u0013'), (u'"\\x0013"', 8), None, True
        ),
        (
            "String that is control character U+0014",
            dict(value=u'\u0014'), (u'"\\x0014"', 8), None, True
        ),
        (
            "String that is control character U+0015",
            dict(value=u'\u0015'), (u'"\\x0015"', 8), None, True
        ),
        (
            "String that is control character U+0016",
            dict(value=u'\u0016'), (u'"\\x0016"', 8), None, True
        ),
        (
            "String that is control character U+0017",
            dict(value=u'\u0017'), (u'"\\x0017"', 8), None, True
        ),
        (
            "String that is control character U+0018",
            dict(value=u'\u0018'), (u'"\\x0018"', 8), None, True
        ),
        (
            "String that is control character U+0019",
            dict(value=u'\u0019'), (u'"\\x0019"', 8), None, True
        ),
        (
            "String that is control character U+001A",
            dict(value=u'\u001A'), (u'"\\x001A"', 8), None, True
        ),
        (
            "String that is control character U+001B",
            dict(value=u'\u001B'), (u'"\\x001B"', 8), None, True
        ),
        (
            "String that is control character U+001C",
            dict(value=u'\u001C'), (u'"\\x001C"', 8), None, True
        ),
        (
            "String that is control character U+001D",
            dict(value=u'\u001D'), (u'"\\x001D"', 8), None, True
        ),
        (
            "String that is control character U+001E",
            dict(value=u'\u001E'), (u'"\\x001E"', 8), None, True
        ),
        (
            "String that is control character U+001F",
            dict(value=u'\u001F'), (u'"\\x001F"', 8), None, True
        ),
        (
            "String that is control character U+0020",
            dict(value=u'\u0020'), (u'" "', 3), None, True
        ),

        # Test line break cases, starting at begin of line
        (
            "Line break with split on a space between words",
            dict(value=u'the big brown fox1 jumps over a big brown fox2 jumps '
                 u'over a big brown fox3',
                 maxline=56),
            (
                u'"the big brown fox1 jumps over a big brown fox2 jumps "\n'
                u'   "over a big brown fox3"',
                26
            ),
            None, CHECK_0_12_0
        ),
        (
            "Line break with split in a long word with no blanks",
            dict(value=u'the_big_brown_fox1_jumps_over_a_big_brown_fox2_jumps_'
                 u'over_a_big_brown_fox3',
                 maxline=56),
            (
                u'\n'
                u'   "the_big_brown_fox1_jumps_over_a_big_brown_fox2_jump"\n'
                u'   "s_over_a_big_brown_fox3"',
                28
            ),
            None, CHECK_0_12_0
        ),

        # Test initial line position on words without blanks
        (
            "No blanks, Line position without new line",
            dict(value=u'abc', line_pos=8),
            (u'"abc"', 13),
            None, CHECK_0_12_0,
        ),
        (
            "No blanks, Line position with new line using max",
            dict(value=u'abcd_fghi_abcd_fghi_ab',
                 line_pos=5, maxline=15, indent=2),
            (u'\n  "abcd_fghi_a"\n  "bcd_fghi_ab"', 15),
            None, CHECK_0_12_0,
        ),
        (
            "No blanks, Line position with new line using max - 1",
            dict(value=u'abcd_fghi_abcd_fghi_a',
                 line_pos=5, maxline=15, indent=2),
            (u'\n  "abcd_fghi_a"\n  "bcd_fghi_a"', 14),
            None, CHECK_0_12_0,
        ),
        (
            "No blanks, Line position with new line using max + 1",
            dict(value=u'abcd_fghi_abcd_fghi_abc',
                 line_pos=5, maxline=15, indent=2),
            (u'\n  "abcd_fghi_a"\n  "bcd_fghi_ab"\n  "c"', 5),
            None, CHECK_0_12_0,
        ),
        (
            "No blanks, Line position starting at maxline",
            dict(value=u'abcd_fghi',
                 line_pos=15, maxline=15, indent=2),
            (u'\n  "abcd_fghi"', 13),
            None, CHECK_0_12_0,
        ),

        # Test initial line position on words with blanks
        (
            "Blanks, Line position with new line using max",
            dict(value=u'abcd fghij lmnop',
                 line_pos=5, maxline=15, indent=2),
            (u'"abcd "\n  "fghij lmnop"', 15),
            None, CHECK_0_12_0,
        ),
        (
            "Blanks, Line position with new line using max - 1",
            dict(value=u'abcd fghij lmno',
                 line_pos=5, maxline=15, indent=2),
            (u'"abcd "\n  "fghij lmno"', 14),
            None, CHECK_0_12_0,
        ),
        (
            "Blanks, Line position with new line using max + 1",
            dict(value=u'abcd fghij lmnopq',
                 line_pos=5, maxline=15, indent=2),
            (u'"abcd "\n  "fghij "\n  "lmnopq"', 10),
            None, CHECK_0_12_0,
        ),
        (
            "Blanks, Line position starting at maxline",
            dict(value=u'abcd fghi',
                 line_pos=15, maxline=15, indent=2),
            (u'\n  "abcd fghi"', 13),
            None, CHECK_0_12_0,
        ),
        (
            "Blanks, Line position starting to exactly fit first word",
            dict(value=u'abcd fghi',
                 line_pos=8, maxline=15, indent=2),
            (u'"abcd "\n  "fghi"', 8),
            None, CHECK_0_12_0,
        ),
        (
            "See issue #343",
            dict(value=u'Linux version 3.13.0-86-generic (buildd@lgw01-51) '
                 u'(gcc version 4.8.2',
                 line_pos=18, maxline=80, indent=8),
            (
                u'"Linux version 3.13.0-86-generic (buildd@lgw01-51) (gcc "\n'
                u'        "version 4.8.2"',
                23
            ),
            None, CHECK_0_12_0
        ),

        # Test end space on words with blanks
        (
            "Blanks, End space with new line using max",
            dict(value=u'abcd fghij lmn',
                 line_pos=5, maxline=15, indent=2, end_space=2),
            (u'"abcd "\n  "fghij lmn"', 13),
            None, CHECK_0_12_0,
        ),
        (
            "Blanks, End space with new line using max - 1",
            dict(value=u'abcd fghij lm',
                 line_pos=5, maxline=15, indent=2, end_space=2),
            (u'"abcd "\n  "fghij lm"', 12),
            None, CHECK_0_12_0,
        ),
        (
            "Blanks, End space with new line using max + 1",
            dict(value=u'abcd fghij lmno',
                 line_pos=5, maxline=15, indent=2, end_space=2),
            (u'"abcd "\n  "fghij "\n  "lmno"', 8),
            None, CHECK_0_12_0,
        ),
        (
            "Blanks, End space with new line using max + 1, on first part",
            dict(value=u'abcdefgh',
                 line_pos=4, maxline=15, indent=2, end_space=2),
            (u'\n  "abcdefgh"', 12),
            None, CHECK_0_12_0,
        ),
    ]

    @pytest.mark.parametrize(
        "desc, kwargs, exp_result, exp_warn_type, condition",
        testcases)
    def test_mofstr(
            self, desc, kwargs, exp_result, exp_warn_type, condition):
        """All test cases for mofstr()."""

        if not condition:
            pytest.skip("Condition for test case not met")

        # Skip testcase if it uses the new args added in 0.12
        if not CHECK_0_12_0:
            if 'line_pos' in kwargs or \
                    'end_space' in kwargs or \
                    'avoid_splits' in kwargs or \
                    'quote_char' in kwargs:
                pytest.skip("test case uses new args added in 0.12")

        if isinstance(exp_result, type) and issubclass(exp_result, Exception):
            # We expect an exception
            exp_exc_type = exp_result
            exp_mof = exp_pos = None
        else:
            # We expect the code to return
            exp_exc_type = None
            exp_mof, exp_pos = exp_result

        if CHECK_0_12_0:
            for k in self.default_kwargs:
                if k not in kwargs:
                    kwargs[k] = self.default_kwargs[k]
        else:
            # Undo the arg rename from strvalue to value
            if 'value' in kwargs:
                kwargs['strvalue'] = kwargs['value']
                del kwargs['value']

        if condition == 'pdb':
            import pdb
            pdb.set_trace()

        if exp_warn_type:
            with pytest.warns(exp_warn_type) as rec_warnings:
                if exp_exc_type:
                    with pytest.raises(exp_exc_type):

                        # The code to be tested
                        result = cim_obj.mofstr(**kwargs)

                else:

                    # The code to be tested
                    result = cim_obj.mofstr(**kwargs)

            assert len(rec_warnings) == 1

        else:
            if exp_exc_type:
                with pytest.raises(exp_exc_type):

                    # The code to be tested
                    result = cim_obj.mofstr(**kwargs)

            else:

                # The code to be tested
                result = cim_obj.mofstr(**kwargs)

        if exp_mof:
            if CHECK_0_12_0:
                mof, pos = result
                assert isinstance(mof, six.text_type)
                assert mof == exp_mof
                assert isinstance(pos, int)
                assert pos == exp_pos
            else:
                mof = result
                assert isinstance(mof, six.string_types)
                assert mof == exp_mof


# Determine the directory where this module is located. This must be done
# before comfychair gets control, because it changes directories.
_MODULE_PATH = os.path.abspath(os.path.dirname(
    inspect.getfile(ValidationTestCase)))
