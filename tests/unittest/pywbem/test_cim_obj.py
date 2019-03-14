"""
Test CIM objects (e.g. `CIMInstance`).

Note that class `NocaseDict` is tested in test_nocasedict.py.
"""

from __future__ import absolute_import, print_function

# Allows use of lots of single character variable names.
# pylint: disable=invalid-name,missing-docstring,too-many-statements
# pylint: disable=too-many-lines,no-self-use
import sys
import re
from datetime import timedelta, datetime
import warnings
import unittest2 as unittest  # we use assertRaises(exc) introduced in py27
from mock import patch
try:
    from collections import OrderedDict
except ImportError:
    from ordereddict import OrderedDict  # pylint: disable=import-error
import pytest
import six

from pywbem import CIMInstance, CIMInstanceName, CIMClass, CIMClassName, \
    CIMProperty, CIMMethod, CIMParameter, CIMQualifier, \
    CIMQualifierDeclaration, Uint8, Uint16, Uint32, Uint64, Sint8, Sint16, \
    Sint32, Sint64, Real32, Real64, CIMDateTime, tocimobj, MinutesFromUTC, \
    __version__

from pywbem._nocasedict import NocaseDict
from pywbem.cim_types import _Longint
from pywbem.cim_obj import mofstr, MOF_INDENT, MAX_MOF_LINE
from pywbem._utils import _format
try:
    from pywbem import cimvalue
except ImportError:
    pass

from ..utils.validate import validate_cim_xml_obj
from ..utils.unittest_extensions import CIMObjectMixin
from ..utils.pytest_extensions import simplified_test_function


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


# Common constant objects for use in the test cases

DATETIME1_DT = datetime(2014, 9, 22, 10, 49, 20, 524789)
DATETIME1_OBJ = CIMDateTime(DATETIME1_DT)

TIMEDELTA1_TD = timedelta(183, (13 * 60 + 25) * 60 + 42, 234567)
TIMEDELTA1_OBJ = CIMDateTime(TIMEDELTA1_TD)

UNNAMED_KEY_NCD = NocaseDict()
UNNAMED_KEY_NCD.allow_unnamed_keys = True
UNNAMED_KEY_NCD[None] = 'abc'

TESTCASES_CIMINSTANCENAME_INIT = [

    # Testcases for CIMInstanceName.__init__() / ip=CIMInstanceName()

    # Each list item is a testcase tuple with these items:
    # * desc: Short testcase description.
    # * kwargs: Keyword arguments for the test function:
    #   * init_args: Tuple of positional arguments to CIMInstanceName().
    #   * init_kwargs: Dict of keyword arguments to CIMInstanceName().
    #   * exp_attrs: Dict of expected attributes of resulting object.
    # * exp_exc_types: Expected exception type(s), or None.
    # * exp_warn_types: Expected warning type(s), or None.
    # * condition: Boolean condition for testcase to run, or 'pdb' for debugger

    # Order of positional arguments
    (
        "Verify order of positional arguments",
        dict(
            init_args=[
                'CIM_Foo',
                dict(P1=True),
                'woot.com',
                'cimv2',
            ],
            init_kwargs={},
            exp_attrs=dict(
                classname=u'CIM_Foo',
                keybindings=NocaseDict(P1=True),
                host=u'woot.com',
                namespace=u'cimv2',
            ),
        ),
        None, None, True
    ),

    # Classname tests
    (
        "Verify that bytes classname is converted to unicode",
        dict(
            init_args=[],
            init_kwargs=dict(classname=b'CIM_Foo'),
            exp_attrs=dict(classname=u'CIM_Foo'),
        ),
        None, None, True
    ),
    (
        "Verify that unicode classname remains unicode",
        dict(
            init_args=[],
            init_kwargs=dict(classname=u'CIM_Foo'),
            exp_attrs=dict(classname=u'CIM_Foo'),
        ),
        None, None, True
    ),

    # Keybinding tests
    (
        "Verify that keybinding with name None succeeds (since 0.12)",
        dict(
            init_args=[],
            init_kwargs=dict(
                classname='CIM_Foo',
                keybindings=dict(UNNAMED_KEY_NCD)),
            exp_attrs=dict(
                classname=u'CIM_Foo',
                keybindings=UNNAMED_KEY_NCD),
        ),
        None, None, CHECK_0_12_0
    ),
    (
        "Verify keybindings order preservation with list of CIMProperty",
        dict(
            init_args=[],
            init_kwargs=dict(
                classname='CIM_Foo',
                keybindings=[
                    CIMProperty('K1', value='Ham'),
                    CIMProperty('K2', value='Cheese'),
                ]
            ),
            exp_attrs=dict(
                classname=u'CIM_Foo',
                keybindings=NocaseDict([
                    ('K1', 'Ham'),
                    ('K2', 'Cheese'),
                ])
            ),
        ),
        None, None, True
    ),
    (
        "Verify keybindings order preservation with OrderedDict",
        dict(
            init_args=[],
            init_kwargs=dict(
                classname='CIM_Foo',
                keybindings=OrderedDict([
                    ('K1', 'Ham'),
                    ('K2', 'Cheese'),
                ])
            ),
            exp_attrs=dict(
                classname=u'CIM_Foo',
                keybindings=NocaseDict([
                    ('K1', 'Ham'),
                    ('K2', 'Cheese'),
                ])
            ),
        ),
        None, None, True
    ),
    (
        "Verify keybindings order preservation with list of tuple(key,val)",
        dict(
            init_args=[],
            init_kwargs=dict(
                classname='CIM_Foo',
                keybindings=[
                    ('K1', 'Ham'),
                    ('K2', 'Cheese'),
                ]
            ),
            exp_attrs=dict(
                classname=u'CIM_Foo',
                keybindings=NocaseDict([
                    ('K1', 'Ham'),
                    ('K2', 'Cheese'),
                ])
            ),
        ),
        None, None, True
    ),
    (
        "Verify keybinding with bytes string value",
        dict(
            init_args=[],
            init_kwargs=dict(
                classname='CIM_Foo',
                keybindings=dict(K1=b'Ham')),
            exp_attrs=dict(
                classname=u'CIM_Foo',
                keybindings=NocaseDict(K1=u'Ham' if CHECK_0_12_0 else b'Ham')),
        ),
        None, None, True
    ),
    (
        "Verify keybinding with unicode string value",
        dict(
            init_args=[],
            init_kwargs=dict(
                classname='CIM_Foo',
                # lower case a umlaut
                keybindings=dict(K1=u'H\u00E4m')),
            exp_attrs=dict(
                classname=u'CIM_Foo',
                keybindings=NocaseDict(K1=u'H\u00E4m')),
        ),
        None, None, True
    ),
    (
        "Verify keybinding with boolean True value",
        dict(
            init_args=[],
            init_kwargs=dict(
                classname='CIM_Foo',
                keybindings=dict(K1=True)),
            exp_attrs=dict(
                classname=u'CIM_Foo',
                keybindings=NocaseDict(K1=True)),
        ),
        None, None, True
    ),
    (
        "Verify keybinding with boolean False value",
        dict(
            init_args=[],
            init_kwargs=dict(
                classname='CIM_Foo',
                keybindings=dict(K1=False)),
            exp_attrs=dict(
                classname=u'CIM_Foo',
                keybindings=NocaseDict(K1=False)),
        ),
        None, None, True
    ),
    (
        "Verify keybinding with int value",
        dict(
            init_args=[],
            init_kwargs=dict(
                classname='CIM_Foo',
                keybindings=dict(K1=42)),
            exp_attrs=dict(
                classname=u'CIM_Foo',
                keybindings=NocaseDict(K1=42)),
        ),
        None, None, True
    ),
    (
        "Verify keybinding with Uint8 value",
        dict(
            init_args=[],
            init_kwargs=dict(
                classname='CIM_Foo',
                keybindings=dict(K1=Uint8(42))),
            exp_attrs=dict(
                classname=u'CIM_Foo',
                keybindings=NocaseDict(K1=42)),
        ),
        None, None, True
    ),
    (
        "Verify keybinding with Uint16 value",
        dict(
            init_args=[],
            init_kwargs=dict(
                classname='CIM_Foo',
                keybindings=dict(K1=Uint16(4216))),
            exp_attrs=dict(
                classname=u'CIM_Foo',
                keybindings=NocaseDict(K1=4216)),
        ),
        None, None, True
    ),
    (
        "Verify keybinding with Uint32 value",
        dict(
            init_args=[],
            init_kwargs=dict(
                classname='CIM_Foo',
                keybindings=dict(K1=Uint32(4232))),
            exp_attrs=dict(
                classname=u'CIM_Foo',
                keybindings=NocaseDict(K1=4232)),
        ),
        None, None, True
    ),
    (
        "Verify keybinding with Uint64 value",
        dict(
            init_args=[],
            init_kwargs=dict(
                classname='CIM_Foo',
                keybindings=dict(K1=Uint64(4264))),
            exp_attrs=dict(
                classname=u'CIM_Foo',
                keybindings=NocaseDict(K1=4264)),
        ),
        None, None, True
    ),
    (
        "Verify keybinding with Sint8 value",
        dict(
            init_args=[],
            init_kwargs=dict(
                classname='CIM_Foo',
                keybindings=dict(K1=Sint8(-42))),
            exp_attrs=dict(
                classname=u'CIM_Foo',
                keybindings=NocaseDict(K1=-42)),
        ),
        None, None, True
    ),
    (
        "Verify keybinding with Sint16 value",
        dict(
            init_args=[],
            init_kwargs=dict(
                classname='CIM_Foo',
                keybindings=dict(K1=Sint16(-4216))),
            exp_attrs=dict(
                classname=u'CIM_Foo',
                keybindings=NocaseDict(K1=-4216)),
        ),
        None, None, True
    ),
    (
        "Verify keybinding with Sint32 value",
        dict(
            init_args=[],
            init_kwargs=dict(
                classname='CIM_Foo',
                keybindings=dict(K1=Sint32(-4232))),
            exp_attrs=dict(
                classname=u'CIM_Foo',
                keybindings=NocaseDict(K1=-4232)),
        ),
        None, None, True
    ),
    (
        "Verify keybinding with Sint64 value",
        dict(
            init_args=[],
            init_kwargs=dict(
                classname='CIM_Foo',
                keybindings=dict(K1=Sint64(-4264))),
            exp_attrs=dict(
                classname=u'CIM_Foo',
                keybindings=NocaseDict(K1=-4264)),
        ),
        None, None, True
    ),
    (
        "Verify keybinding with float value",
        dict(
            init_args=[],
            init_kwargs=dict(
                classname='CIM_Foo',
                keybindings=dict(K1=42.1)),
            exp_attrs=dict(
                classname=u'CIM_Foo',
                keybindings=NocaseDict(K1=42.1)),
        ),
        None, None, True
    ),
    (
        "Verify keybinding with Real32 value",
        dict(
            init_args=[],
            init_kwargs=dict(
                classname='CIM_Foo',
                keybindings=dict(K1=Real32(-42.32))),
            exp_attrs=dict(
                classname=u'CIM_Foo',
                keybindings=NocaseDict(K1=-42.32)),
        ),
        None, None, True
    ),
    (
        "Verify keybinding with Real64 value",
        dict(
            init_args=[],
            init_kwargs=dict(
                classname='CIM_Foo',
                keybindings=dict(K1=Real64(-42.64))),
            exp_attrs=dict(
                classname=u'CIM_Foo',
                keybindings=NocaseDict(K1=-42.64)),
        ),
        None, None, True
    ),
    (
        "Verify keybinding with datetime value",
        dict(
            init_args=[],
            init_kwargs=dict(
                classname='CIM_Foo',
                keybindings=dict(K1=DATETIME1_OBJ)),
            exp_attrs=dict(
                classname=u'CIM_Foo',
                keybindings=NocaseDict(K1=DATETIME1_OBJ)),
        ),
        None, None, True
    ),
    (
        "Verify keybinding with timedelta value",
        dict(
            init_args=[],
            init_kwargs=dict(
                classname='CIM_Foo',
                keybindings=dict(K1=TIMEDELTA1_OBJ)),
            exp_attrs=dict(
                classname=u'CIM_Foo',
                keybindings=NocaseDict(K1=TIMEDELTA1_OBJ)),
        ),
        None, None, True
    ),
    (
        "Verify keybinding with CIMProperty (of arbitrary type and value)",
        # Note: The full range of possible input values and types for
        # CIMProperty objects is tested in CIMProperty testcases.
        dict(
            init_args=[],
            init_kwargs=dict(
                classname='CIM_Foo',
                keybindings=dict(K1=CIMProperty('K1', value='Ham'))),
            exp_attrs=dict(
                classname=u'CIM_Foo',
                keybindings=NocaseDict([('K1', u'Ham')])),
        ),
        None, None, CHECK_0_12_0
    ),
    (
        "Verify two keybindings",
        dict(
            init_args=[],
            init_kwargs=dict(
                classname='CIM_Foo',
                keybindings=OrderedDict([('K1', u'Ham'), ('K2', Uint8(42))])),
            exp_attrs=dict(
                classname=u'CIM_Foo',
                keybindings=NocaseDict([('K1', u'Ham'), ('K2', Uint8(42))])),
        ),
        None, None, True
    ),
    (
        "Verify case insensitivity of keybinding names",
        dict(
            init_args=[],
            init_kwargs=dict(
                classname='CIM_Foo',
                keybindings=dict(Key1='Ham')),
            exp_attrs=dict(
                classname=u'CIM_Foo',
                keybindings=NocaseDict([('kEY1', u'Ham')])),
        ),
        None, None, True
    ),
    (
        "Verify that keybinding with None value fails with ValueError",
        dict(
            init_args=[],
            init_kwargs=dict(
                classname='CIM_Foo',
                keybindings=dict(Key1=None)),
            exp_attrs=dict(
                classname=u'CIM_Foo',
                keybindings=dict(Key1=None)),
        ),
        ValueError, None, True
    ),

    # Namespace tests
    (
        "Verify that bytes namespace is converted to unicode",
        dict(
            init_args=[],
            init_kwargs=dict(
                classname='CIM_Foo',
                namespace=b'root/cimv2'),
            exp_attrs=dict(
                classname=u'CIM_Foo',
                namespace=u'root/cimv2'),
        ),
        None, None, True
    ),
    (
        "Verify that unicode namespace remains unicode",
        dict(
            init_args=[],
            init_kwargs=dict(
                classname='CIM_Foo',
                namespace=u'root/cimv2'),
            exp_attrs=dict(
                classname=u'CIM_Foo',
                namespace=u'root/cimv2'),
        ),
        None, None, True
    ),
    (
        "Verify that one leading and trailing slash in namespace get "
        "stripped",
        dict(
            init_args=[],
            init_kwargs=dict(
                classname='CIM_Foo',
                namespace='/root/cimv2/'),
            exp_attrs=dict(
                classname=u'CIM_Foo',
                namespace=u'root/cimv2'),
        ),
        None, None, True
    ),
    (
        "Verify that two leading and trailing slashes in namespace get "
        "stripped",
        dict(
            init_args=[],
            init_kwargs=dict(
                classname='CIM_Foo',
                namespace='//root/cimv2//'),
            exp_attrs=dict(
                classname=u'CIM_Foo',
                namespace=u'root/cimv2'),
        ),
        None, None, True
    ),

    # Host tests
    (
        "Verify that bytes host is converted to unicode",
        dict(
            init_args=[],
            init_kwargs=dict(
                classname='CIM_Foo',
                namespace='root/cimv2',
                host=b'woot.com'),
            exp_attrs=dict(
                classname=u'CIM_Foo',
                namespace=u'root/cimv2',
                host=u'woot.com'),
        ),
        None, None, True
    ),
    (
        "Verify that unicode host remains unicode",
        dict(
            init_args=[],
            init_kwargs=dict(
                classname='CIM_Foo',
                namespace='root/cimv2',
                host=u'woot.com'),
            exp_attrs=dict(
                classname=u'CIM_Foo',
                namespace=u'root/cimv2',
                host=u'woot.com'),
        ),
        None, None, True
    ),

    # Exception testcases
    (
        "Verify that classname None fails",
        dict(
            init_args=[],
            init_kwargs=dict(classname=None),
            exp_attrs=None,
        ),
        ValueError, None, True
    ),
    (
        "Verify that keybinding with name None fails (before 0.12",
        dict(
            init_args=[],
            init_kwargs=dict(
                classname='CIM_Foo',
                keybindings={None: 'abc'}),
            exp_attrs=None,
        ),
        TypeError, None, not CHECK_0_12_0
    ),
    (
        "Verify that keybinding with inconsistent name fails",
        dict(
            init_args=[],
            init_kwargs=dict(
                classname='CIM_Foo',
                keybindings=dict(K1=CIMProperty('K1_X', value='Ham'))),
            exp_attrs=None,
        ),
        ValueError, None, CHECK_0_12_0
    ),
    (
        "Verify that keybinding with a value of an embedded class fails",
        dict(
            init_args=[],
            init_kwargs=dict(
                classname='CIM_Foo',
                keybindings=dict(K1=CIMClass('CIM_EmbClass'))),
            exp_attrs=None,
        ),
        TypeError, None, CHECK_0_12_0
    ),
    (
        "Verify that keybinding with a value of an embedded instance fails",
        dict(
            init_args=[],
            init_kwargs=dict(
                classname='CIM_Foo',
                keybindings=dict(K1=CIMInstance('CIM_EmbInst'))),
            exp_attrs=None,
        ),
        TypeError, None, CHECK_0_12_0
    ),
    (
        "Verify that keybinding with an array value fails",
        dict(
            init_args=[],
            init_kwargs=dict(
                classname='CIM_Foo',
                keybindings=dict(K1=[1, 2])),
            exp_attrs=None,
        ),
        TypeError, None, CHECK_0_12_0
    ),
    (
        "Verify that keybinding with a value of some other unsupported "
        "object type (e.g. exception type) fails",
        dict(
            init_args=[],
            init_kwargs=dict(
                classname='CIM_Foo',
                keybindings=dict(K1=TypeError)),
            exp_attrs=None,
        ),
        TypeError, None, CHECK_0_12_0
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_CIMINSTANCENAME_INIT)
@simplified_test_function
def test_CIMInstanceName_init(testcase,
                              init_args, init_kwargs, exp_attrs):
    """
    Test function for CIMInstanceName.__init__() / ip=CIMInstanceName()
    """

    # The code to be tested
    obj = CIMInstanceName(*init_args, **init_kwargs)

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None

    exp_classname = exp_attrs['classname']
    assert obj.classname == exp_classname
    assert isinstance(obj.classname, type(exp_classname))

    exp_keybindings = exp_attrs.get('keybindings', NocaseDict())
    assert obj.keybindings == exp_keybindings
    assert isinstance(obj.keybindings, type(exp_keybindings))

    exp_host = exp_attrs.get('host', None)
    assert obj.host == exp_host
    assert isinstance(obj.host, type(exp_host))

    exp_namespace = exp_attrs.get('namespace', None)
    assert obj.namespace == exp_namespace
    assert isinstance(obj.namespace, type(exp_namespace))


TESTCASES_KEYBINDING_CONFIG = [

    # Testcases for CIMInstanceName.__init__() / ip=CIMInstanceName()

    # Each list item is a testcase tuple with these items:
    # * desc: Short testcase description.
    # * kwargs: Keyword arguments for the test function:
    #   * init_args: Tuple of positional arguments to CIMInstanceName().
    #   * ignore_flag: Value of IGNORE_NULL_KEY_VALUE config variable
    #   * init_kwargs: Dict of keyword arguments to CIMInstanceName().
    #   * exp_attrs: Dict of expected attributes of resulting object.
    # * exp_exc_types: Expected exception type(s), or None.
    # * exp_warn_types: Expected warning type(s), or None.
    # * condition: Boolean condition for testcase to run, or 'pdb' for debugger
    (
        "Verify that keybinding with None value fails with ValueError when"
        "config variable False",
        dict(
            init_args=[],
            ignore_flag=False,
            init_kwargs=dict(
                classname='CIM_Foo',
                keybindings=dict(Key1=None)),
            exp_attrs=dict(
                classname=u'CIM_Foo',
                keybindings=dict(Key1=None)),
        ),
        ValueError, None, True
    ),
    (
        "Verify that keybinding with None value OK with config True",
        dict(
            init_args=[],
            ignore_flag=True,
            init_kwargs=dict(
                classname='CIM_Foo',
                keybindings=dict(Key1=None)),
            exp_attrs=dict(
                classname=u'CIM_Foo',
                keybindings=dict(Key1=None)),
        ),
        None, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_KEYBINDING_CONFIG)
@simplified_test_function
def test_keybinding_config_option(testcase,
                                  init_args, ignore_flag, init_kwargs,
                                  exp_attrs):
    """
    Test CIMInstanceName behavior with changes to config variable
    IGNORE_NULL_KEY_VALUE.
    """
    # The code to be tested
    # pylint: disable=unused-variable
    # patch with context resets original at end of test
    with patch('pywbem.config.IGNORE_NULL_KEY_VALUE', ignore_flag):
        obj = CIMInstanceName(*init_args, **init_kwargs)

        # Ensure that exceptions raised in the remainder of this function
        # are not mistaken as expected exceptions
        assert testcase.exp_exc_types is None

        exp_classname = exp_attrs['classname']
        assert obj.classname == exp_classname
        assert isinstance(obj.classname, type(exp_classname))

        exp_keybindings = exp_attrs.get('keybindings', NocaseDict())
        assert obj.keybindings == exp_keybindings


class CIMInstanceNameCopy(unittest.TestCase, CIMObjectMixin):
    """
    Test the copy() method of `CIMInstanceName` objects.

    The basic idea is to modify the copy, and to verify that the original is
    still the same.
    """

    def test_CIMInstanceName_copy(self):  # XXX: Migrate to pytest

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

        self.assert_CIMInstanceName_attrs(i, 'CIM_Foo', {'InstanceID': '1234'},
                                          'woot.com', 'root/cimv2')


class CIMInstanceNameAttrs(unittest.TestCase, CIMObjectMixin):
    """
    Test that the public data attributes of `CIMInstanceName` objects can be
    accessed and modified.
    """

    def test_CIMInstanceName_attrs(self):  # XXX: Migrate to pytest

        kb = {'Chicken': 'Ham', 'Beans': Uint8(42)}

        obj = CIMInstanceName('CIM_Foo',
                              kb,
                              namespace='root/cimv2',
                              host='woot.com')

        self.assert_CIMInstanceName_attrs(obj, 'CIM_Foo', kb,
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

        self.assert_CIMInstanceName_attrs(obj, 'CIM_Bar', exp_kb2,
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

    def test_CIMInstanceName_dict(self):  # XXX: Migrate to pytest

        kb = {'Chicken': 'Ham', 'Beans': Uint8(42)}
        obj = CIMInstanceName('CIM_Foo', kb)

        self.runtest_dict(obj, kb)


class CIMInstanceNameEquality(unittest.TestCase):
    """
    Test the equality comparison of `CIMInstanceName` objects.
    """

    def test_CIMInstanceName_eq(self):  # XXX: Migrate to pytest

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

    def test_keybindings_order(self):  # XXX: Migrate to pytest
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
        https://stackoverflow.com/a/15479974/1424462.
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
    def test_CIMInstanceName_cmp(self):  # XXX: Implement with pytest
        raise AssertionError("test not implemented")


class CIMInstanceNameSort(unittest.TestCase):
    """
    Test the sorting of `CIMInstanceName` objects.
    """

    @unimplemented
    def test_CIMInstanceName_sort(self):  # XXX: Implement with pytest
        raise AssertionError("test not implemented")


TESTCASES_CIMINSTANCENAME_HASH = [

    # Testcases for CIMInstanceName.__hash__()

    # Each list item is a testcase tuple with these items:
    # * desc: Short testcase description.
    # * kwargs: Keyword arguments for the test function:
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
    TESTCASES_CIMINSTANCENAME_HASH)
@simplified_test_function
def test_CIMInstanceName_hash(testcase,
                              obj1, obj2, exp_hash_equal):
    """
    Test function for CIMInstanceName.__hash__().
    """

    # The code to be tested
    hash1 = hash(obj1)
    hash2 = hash(obj2)

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None

    # Double check they are different objects
    assert id(obj1) != id(obj2)

    if exp_hash_equal:
        assert hash1 == hash2
    else:
        assert hash1 != hash2


TESTCASES_CIMINSTANCENAME_REPR = [

    # Testcases for CIMInstanceName.__repr__() / repr()
    # Note: CIMInstanceName.__str__() is tested along with to_wbem_uri()

    # Each list item is a testcase tuple with these items:
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
    # (
    #    CIMInstanceName(
    #        classname='CIM_Foo',
    #        keybindings=dict(InstanceID=None))
    # ),
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
    TESTCASES_CIMINSTANCENAME_REPR)
def test_CIMInstanceName_repr(obj):
    """
    Test function for CIMInstanceName.__repr__() / repr()

    Note: CIMInstanceName.__str__() is tested along with to_wbem_uri()
    """

    # The code to be tested
    r = repr(obj)

    assert re.match(r'^CIMInstanceName\(', r)

    exp_classname = _format('classname={0!A}', obj.classname)
    assert exp_classname in r

    assert 'keybindings=' in r
    if obj.keybindings:
        for key, value in obj.keybindings.items():
            search_str = _format("{0!A}: {1!A}", key, value)
            assert re.search(search_str, r), "For key %r" % key

    exp_namespace = _format('namespace={0!A}', obj.namespace)
    assert exp_namespace in r

    exp_host = _format('host={0!A}', obj.host)
    assert exp_host in r


# Some CIMInstanceName objects for CIMInstanceName.tocimxml() tests

CIMINSTANCENAME_INV_KEYBINDINGS_1 = CIMInstanceName(
    'CIM_Foo', keybindings=dict(Name='Foo'))
CIMINSTANCENAME_INV_KEYBINDINGS_1.keybindings['Foo'] = datetime(2017, 1, 1)

CIMINSTANCENAME_INV_KEYBINDINGS_2 = CIMInstanceName(
    'CIM_Foo', keybindings=dict(Name='Foo'))
CIMINSTANCENAME_INV_KEYBINDINGS_2.keybindings['Foo'] = CIMParameter(
    'Foo', type='string')

CIMINSTANCENAME_INV_KEYBINDINGS_3 = CIMInstanceName(
    'CIM_Foo', keybindings=dict(Name='Foo'))
CIMINSTANCENAME_INV_KEYBINDINGS_3.keybindings['Foo'] = CIMProperty(
    'Foo', type='string', value='bla')

TESTCASES_CIMINSTANCENAME_TOCIMXML = [

    # Testcases for CIMInstanceName.tocimxml() and tocimxmlstr()

    # Each list item is a testcase tuple with these items:
    # * desc: Short testcase description.
    # * kwargs: Keyword arguments for the test function:
    #   * obj: CIMInstanceName object to be tested.
    #   * kwargs: Dict of input args for tocimxml().
    #   * exp_xml_str: Expected CIM-XML string, as a tuple/list of parts.
    # * exp_exc_types: Expected exception type(s), or None.
    # * exp_warn_types: Expected warning type(s), or None.
    # * condition: Boolean condition for testcase to run, or 'pdb' for debugger

    # Classname-only tests
    (
        "Classname only, with implied default args",
        dict(
            obj=CIMInstanceName('CIM_Foo'),
            kwargs=dict(),
            exp_xml_str=(
                '<INSTANCENAME CLASSNAME="CIM_Foo"/>',
            )
        ),
        None, None, True
    ),
    (
        "Classname only, with specified default args",
        dict(
            obj=CIMInstanceName('CIM_Foo'),
            kwargs=dict(
                ignore_host=False,
                ignore_namespace=False,
            ),
            exp_xml_str=(
                '<INSTANCENAME CLASSNAME="CIM_Foo"/>',
            )
        ),
        None, None, True
    ),
    (
        "Classname only, with non-default args: ignore_host=True",
        dict(
            obj=CIMInstanceName('CIM_Foo'),
            kwargs=dict(
                ignore_host=True,
            ),
            exp_xml_str=(
                '<INSTANCENAME CLASSNAME="CIM_Foo"/>',
            )
        ),
        None, None, True
    ),
    (
        "Classname only, with non-default args: ignore_namespace=True",
        dict(
            obj=CIMInstanceName('CIM_Foo'),
            kwargs=dict(
                ignore_namespace=True,
            ),
            exp_xml_str=(
                '<INSTANCENAME CLASSNAME="CIM_Foo"/>',
            )
        ),
        None, None, True
    ),

    # Classname with one keybinding tests
    (
        "Classname with one keybinding, with implied default args",
        dict(
            obj=CIMInstanceName('CIM_Foo', {'Cheepy': 'Birds'}),
            kwargs=dict(),
            exp_xml_str=(
                '<INSTANCENAME CLASSNAME="CIM_Foo">',
                '<KEYBINDING NAME="Cheepy">',
                '<KEYVALUE VALUETYPE="string">Birds</KEYVALUE>',
                '</KEYBINDING>',
                '</INSTANCENAME>',
            )
        ),
        None, None, True
    ),
    (
        "Classname with one keybinding, with specified default args",
        dict(
            obj=CIMInstanceName('CIM_Foo', {'Cheepy': 'Birds'}),
            kwargs=dict(
                ignore_host=False,
                ignore_namespace=False,
            ),
            exp_xml_str=(
                '<INSTANCENAME CLASSNAME="CIM_Foo">',
                '<KEYBINDING NAME="Cheepy">',
                '<KEYVALUE VALUETYPE="string">Birds</KEYVALUE>',
                '</KEYBINDING>',
                '</INSTANCENAME>',
            )
        ),
        None, None, True
    ),
    (
        "Classname with one keybinding, with non-default: ignore_host=True",
        dict(
            obj=CIMInstanceName('CIM_Foo', {'Cheepy': 'Birds'}),
            kwargs=dict(
                ignore_host=True,
            ),
            exp_xml_str=(
                '<INSTANCENAME CLASSNAME="CIM_Foo">',
                '<KEYBINDING NAME="Cheepy">',
                '<KEYVALUE VALUETYPE="string">Birds</KEYVALUE>',
                '</KEYBINDING>',
                '</INSTANCENAME>',
            )
        ),
        None, None, True
    ),
    (
        "Classname with one keybinding, with non-def.: ignore_namespace=True",
        dict(
            obj=CIMInstanceName('CIM_Foo', {'Cheepy': 'Birds'}),
            kwargs=dict(
                ignore_namespace=True,
            ),
            exp_xml_str=(
                '<INSTANCENAME CLASSNAME="CIM_Foo">',
                '<KEYBINDING NAME="Cheepy">',
                '<KEYVALUE VALUETYPE="string">Birds</KEYVALUE>',
                '</KEYBINDING>',
                '</INSTANCENAME>',
            )
        ),
        None, None, True
    ),

    # Classname with mult. keybindings tests
    (
        "Classname with mult. keybindings, with implied default args",
        dict(
            obj=CIMInstanceName(
                'CIM_Foo',
                NocaseDict([
                    ('Name', 'Foo'),
                    ('Number', Uint8(42)),
                    ('Boolean', False),
                    ('Ref', CIMInstanceName('CIM_Bar')),
                ]),
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<INSTANCENAME CLASSNAME="CIM_Foo">',
                '<KEYBINDING NAME="Name">',
                '<KEYVALUE VALUETYPE="string">Foo</KEYVALUE>',
                '</KEYBINDING>',
                '<KEYBINDING NAME="Number">',
                '<KEYVALUE VALUETYPE="numeric">42</KEYVALUE>',
                '</KEYBINDING>',
                '<KEYBINDING NAME="Boolean">',
                '<KEYVALUE VALUETYPE="boolean">FALSE</KEYVALUE>',
                '</KEYBINDING>',
                '<KEYBINDING NAME="Ref">',
                '<VALUE.REFERENCE>',
                '<INSTANCENAME CLASSNAME="CIM_Bar"/>',
                '</VALUE.REFERENCE>',
                '</KEYBINDING>',
                '</INSTANCENAME>',
            )
        ),
        None, None, True
    ),
    (
        "Classname with mult. keybindings, with specified default args",
        dict(
            obj=CIMInstanceName(
                'CIM_Foo',
                NocaseDict([
                    ('Name', 'Foo'),
                    ('Number', Uint8(42)),
                    ('Boolean', False),
                    ('Ref', CIMInstanceName('CIM_Bar')),
                ]),
            ),
            kwargs=dict(
                ignore_host=False,
                ignore_namespace=False,
            ),
            exp_xml_str=(
                '<INSTANCENAME CLASSNAME="CIM_Foo">',
                '<KEYBINDING NAME="Name">',
                '<KEYVALUE VALUETYPE="string">Foo</KEYVALUE>',
                '</KEYBINDING>',
                '<KEYBINDING NAME="Number">',
                '<KEYVALUE VALUETYPE="numeric">42</KEYVALUE>',
                '</KEYBINDING>',
                '<KEYBINDING NAME="Boolean">',
                '<KEYVALUE VALUETYPE="boolean">FALSE</KEYVALUE>',
                '</KEYBINDING>',
                '<KEYBINDING NAME="Ref">',
                '<VALUE.REFERENCE>',
                '<INSTANCENAME CLASSNAME="CIM_Bar"/>',
                '</VALUE.REFERENCE>',
                '</KEYBINDING>',
                '</INSTANCENAME>',
            )
        ),
        None, None, True
    ),
    (
        "Classname with mult. keybindings, with non-default: ignore_host=True",
        dict(
            obj=CIMInstanceName(
                'CIM_Foo',
                NocaseDict([
                    ('Name', 'Foo'),
                    ('Number', Uint8(42)),
                    ('Boolean', False),
                    ('Ref', CIMInstanceName('CIM_Bar')),
                ]),
            ),
            kwargs=dict(
                ignore_host=True,
            ),
            exp_xml_str=(
                '<INSTANCENAME CLASSNAME="CIM_Foo">',
                '<KEYBINDING NAME="Name">',
                '<KEYVALUE VALUETYPE="string">Foo</KEYVALUE>',
                '</KEYBINDING>',
                '<KEYBINDING NAME="Number">',
                '<KEYVALUE VALUETYPE="numeric">42</KEYVALUE>',
                '</KEYBINDING>',
                '<KEYBINDING NAME="Boolean">',
                '<KEYVALUE VALUETYPE="boolean">FALSE</KEYVALUE>',
                '</KEYBINDING>',
                '<KEYBINDING NAME="Ref">',
                '<VALUE.REFERENCE>',
                '<INSTANCENAME CLASSNAME="CIM_Bar"/>',
                '</VALUE.REFERENCE>',
                '</KEYBINDING>',
                '</INSTANCENAME>',
            )
        ),
        None, None, True
    ),
    (
        "Classname with mult. keybindings, with non-def: ignore_namespace=True",
        dict(
            obj=CIMInstanceName(
                'CIM_Foo',
                NocaseDict([
                    ('Name', 'Foo'),
                    ('Number', Uint8(42)),
                    ('Boolean', False),
                    ('Ref', CIMInstanceName('CIM_Bar')),
                ]),
            ),
            kwargs=dict(
                ignore_namespace=True,
            ),
            exp_xml_str=(
                '<INSTANCENAME CLASSNAME="CIM_Foo">',
                '<KEYBINDING NAME="Name">',
                '<KEYVALUE VALUETYPE="string">Foo</KEYVALUE>',
                '</KEYBINDING>',
                '<KEYBINDING NAME="Number">',
                '<KEYVALUE VALUETYPE="numeric">42</KEYVALUE>',
                '</KEYBINDING>',
                '<KEYBINDING NAME="Boolean">',
                '<KEYVALUE VALUETYPE="boolean">FALSE</KEYVALUE>',
                '</KEYBINDING>',
                '<KEYBINDING NAME="Ref">',
                '<VALUE.REFERENCE>',
                '<INSTANCENAME CLASSNAME="CIM_Bar"/>',
                '</VALUE.REFERENCE>',
                '</KEYBINDING>',
                '</INSTANCENAME>',
            )
        ),
        None, None, True
    ),

    # Classname with namespace tests
    (
        "Classname with namespace, with implied default args",
        dict(
            obj=CIMInstanceName(
                'CIM_Foo',
                namespace='root/cimv2',
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<LOCALINSTANCEPATH>',
                '<LOCALNAMESPACEPATH>',
                '<NAMESPACE NAME="root"/>',
                '<NAMESPACE NAME="cimv2"/>',
                '</LOCALNAMESPACEPATH>',
                '<INSTANCENAME CLASSNAME="CIM_Foo"/>',
                '</LOCALINSTANCEPATH>',
            )
        ),
        None, None, True
    ),
    (
        "Classname with namespace, with specified default args",
        dict(
            obj=CIMInstanceName(
                'CIM_Foo',
                namespace='root/cimv2',
            ),
            kwargs=dict(
                ignore_host=False,
                ignore_namespace=False,
            ),
            exp_xml_str=(
                '<LOCALINSTANCEPATH>',
                '<LOCALNAMESPACEPATH>',
                '<NAMESPACE NAME="root"/>',
                '<NAMESPACE NAME="cimv2"/>',
                '</LOCALNAMESPACEPATH>',
                '<INSTANCENAME CLASSNAME="CIM_Foo"/>',
                '</LOCALINSTANCEPATH>',
            )
        ),
        None, None, True
    ),
    (
        "Classname with namespace, with non-default: ignore_host=True",
        dict(
            obj=CIMInstanceName(
                'CIM_Foo',
                namespace='root/cimv2',
            ),
            kwargs=dict(
                ignore_host=True,
            ),
            exp_xml_str=(
                '<LOCALINSTANCEPATH>',
                '<LOCALNAMESPACEPATH>',
                '<NAMESPACE NAME="root"/>',
                '<NAMESPACE NAME="cimv2"/>',
                '</LOCALNAMESPACEPATH>',
                '<INSTANCENAME CLASSNAME="CIM_Foo"/>',
                '</LOCALINSTANCEPATH>',
            )
        ),
        None, None, True
    ),
    (
        "Classname with namespace, with non-def: ignore_namespace=True",
        dict(
            obj=CIMInstanceName(
                'CIM_Foo',
                namespace='root/cimv2',
            ),
            kwargs=dict(
                ignore_namespace=True,
            ),
            exp_xml_str=(
                '<INSTANCENAME CLASSNAME="CIM_Foo"/>',
            )
        ),
        None, None, True
    ),

    # Classname with namespace+host tests
    (
        "Classname with namespace+host, with implied default args",
        dict(
            obj=CIMInstanceName(
                'CIM_Foo',
                namespace='root/cimv2',
                host='woot.com',
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<INSTANCEPATH>',
                '<NAMESPACEPATH>',
                '<HOST>woot.com</HOST>',
                '<LOCALNAMESPACEPATH>',
                '<NAMESPACE NAME="root"/>',
                '<NAMESPACE NAME="cimv2"/>',
                '</LOCALNAMESPACEPATH>',
                '</NAMESPACEPATH>',
                '<INSTANCENAME CLASSNAME="CIM_Foo"/>',
                '</INSTANCEPATH>',
            )
        ),
        None, None, True
    ),
    (
        "Classname with namespace+host, with specified default args",
        dict(
            obj=CIMInstanceName(
                'CIM_Foo',
                namespace='root/cimv2',
                host='woot.com',
            ),
            kwargs=dict(
                ignore_host=False,
                ignore_namespace=False,
            ),
            exp_xml_str=(
                '<INSTANCEPATH>',
                '<NAMESPACEPATH>',
                '<HOST>woot.com</HOST>',
                '<LOCALNAMESPACEPATH>',
                '<NAMESPACE NAME="root"/>',
                '<NAMESPACE NAME="cimv2"/>',
                '</LOCALNAMESPACEPATH>',
                '</NAMESPACEPATH>',
                '<INSTANCENAME CLASSNAME="CIM_Foo"/>',
                '</INSTANCEPATH>',
            )
        ),
        None, None, True
    ),
    (
        "Classname with namespace+host, with non-default: ignore_host=True",
        dict(
            obj=CIMInstanceName(
                'CIM_Foo',
                namespace='root/cimv2',
                host='woot.com',
            ),
            kwargs=dict(
                ignore_host=True,
            ),
            exp_xml_str=(
                '<LOCALINSTANCEPATH>',
                '<LOCALNAMESPACEPATH>',
                '<NAMESPACE NAME="root"/>',
                '<NAMESPACE NAME="cimv2"/>',
                '</LOCALNAMESPACEPATH>',
                '<INSTANCENAME CLASSNAME="CIM_Foo"/>',
                '</LOCALINSTANCEPATH>',
            )
        ),
        None, None, True
    ),
    (
        "Classname with namespace+host, with non-def: ignore_namespace=True",
        dict(
            obj=CIMInstanceName(
                'CIM_Foo',
                namespace='root/cimv2',
                host='woot.com',
            ),
            kwargs=dict(
                ignore_namespace=True,
            ),
            exp_xml_str=(
                '<INSTANCENAME CLASSNAME="CIM_Foo"/>',
            )
        ),
        None, None, True
    ),

    # Tests with invalid keybinding values
    (
        "Keybinding value with invalid datetime type",
        dict(
            obj=CIMINSTANCENAME_INV_KEYBINDINGS_1,
            kwargs=dict(),
            exp_xml_str=None
        ),
        TypeError, None, True
    ),
    (
        "Keybinding value with invalid CIMParameter type",
        dict(
            obj=CIMINSTANCENAME_INV_KEYBINDINGS_2,
            kwargs=dict(),
            exp_xml_str=None
        ),
        TypeError, None, CHECK_0_12_0
    ),
    (
        "Keybinding value with invalid CIMProperty type",
        dict(
            obj=CIMINSTANCENAME_INV_KEYBINDINGS_3,
            kwargs=dict(),
            exp_xml_str=None
        ),
        TypeError, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_CIMINSTANCENAME_TOCIMXML)
@simplified_test_function
def test_CIMInstanceName_tocimxml(testcase,
                                  obj, kwargs, exp_xml_str):
    """
    Test function for CIMInstanceName.tocimxml().
    """

    # The code to be tested
    obj_xml = obj.tocimxml(**kwargs)

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None

    obj_xml_str = obj_xml.toxml()
    exp_xml_str = ''.join(exp_xml_str)
    validate_cim_xml_obj(obj, obj_xml_str, exp_xml_str)


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_CIMINSTANCENAME_TOCIMXML)
@simplified_test_function
def test_CIMInstanceName_tocimxmlstr(testcase,
                                     obj, kwargs, exp_xml_str):
    """
    Test function for CIMInstanceName.tocimxmlstr().
    """

    # The code to be tested
    obj_xml_str = obj.tocimxmlstr(**kwargs)

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None

    assert isinstance(obj_xml_str, six.text_type)

    exp_xml_str = ''.join(exp_xml_str)
    validate_cim_xml_obj(obj, obj_xml_str, exp_xml_str)


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_CIMINSTANCENAME_TOCIMXML)
@simplified_test_function
def test_CIMInstanceName_tocimxmlstr_indent_int(
        testcase, obj, kwargs, exp_xml_str):
    """
    Test function for CIMInstanceName.tocimxmlstr() with indent as integer.
    """

    indent = 4
    indent_str = ' ' * indent

    # The code to be tested
    obj_xml_str = obj.tocimxmlstr(indent=indent, **kwargs)

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None

    obj_xml = obj.tocimxml(**kwargs)  # This is tested elsewhere
    exp_xml_str = obj_xml.toprettyxml(indent=indent_str)

    assert obj_xml_str == exp_xml_str, \
        "{0}.tocimxmlstr(indent={1!r}) returns unexpected CIM-XML string". \
        format(obj.__class__.__name__, indent)


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_CIMINSTANCENAME_TOCIMXML)
@simplified_test_function
def test_CIMInstanceName_tocimxmlstr_indent_str(
        testcase, obj, kwargs, exp_xml_str):
    """
    Test function for CIMInstanceName.tocimxmlstr() with indent as string.
    """

    indent = 4
    indent_str = ' ' * indent

    # The code to be tested
    obj_xml_str = obj.tocimxmlstr(indent=indent_str, **kwargs)

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None

    obj_xml = obj.tocimxml(**kwargs)  # This is tested elsewhere
    exp_xml_str = obj_xml.toprettyxml(indent=indent_str)

    assert obj_xml_str == exp_xml_str, \
        "{0}.tocimxmlstr(indent={1!r}) returns unexpected CIM-XML string". \
        format(obj.__class__.__name__, indent_str)


TESTCASES_CIMINSTANCENAME_FROM_WBEM_URI = [

    # Testcases for CIMInstanceName.from_wbem_uri()

    # Each list item is a testcase tuple with these items:
    # * desc: Short testcase description.
    # * kwargs: Keyword arguments for the test function:
    #   * uri: WBEM URI string to be tested.
    #   * exp_attrs: Dict of all expected attributes of created object, or None.
    # * exp_exc_types: Expected exception type(s), or None.
    # * exp_warn_types: Expected warning type(s), or None.
    # * condition: Boolean condition for testcase to run, or 'pdb' for debugger

    (
        "all components, normal case",
        dict(
            uri='https://10.11.12.13:5989/root/cimv2:CIM_Foo.k1="v1"',
            exp_attrs=dict(
                classname=u'CIM_Foo',
                keybindings=NocaseDict(k1=u'v1'),
                namespace=u'root/cimv2',
                host=u'10.11.12.13:5989'),
        ),
        None, None, CHECK_0_12_0
    ),
    (
        "no authority",
        dict(
            uri='https:/root/cimv2:CIM_Foo.k1="v1"',
            exp_attrs=dict(
                classname=u'CIM_Foo',
                keybindings=NocaseDict(k1=u'v1'),
                namespace=u'root/cimv2',
                host=None),
        ),
        None, None, CHECK_0_12_0
    ),
    (
        "authority with user:password",
        dict(
            uri='https://jdd:test@10.11.12.13:5989/root/cimv2:CIM_Foo.k1="v1"',
            exp_attrs=dict(
                classname=u'CIM_Foo',
                keybindings=NocaseDict(k1=u'v1'),
                namespace=u'root/cimv2',
                host=u'jdd:test@10.11.12.13:5989'),
        ),
        None, None, CHECK_0_12_0
    ),
    (
        "authority with user (no password)",
        dict(
            uri='https://jdd@10.11.12.13:5989/root/cimv2:CIM_Foo.k1="v1"',
            exp_attrs=dict(
                classname=u'CIM_Foo',
                keybindings=NocaseDict(k1=u'v1'),
                namespace=u'root/cimv2',
                host=u'jdd@10.11.12.13:5989'),
        ),
        None, None, CHECK_0_12_0
    ),
    (
        "authority without port",
        dict(
            uri='https://10.11.12.13/root/cimv2:CIM_Foo.k1="v1"',
            exp_attrs=dict(
                classname=u'CIM_Foo',
                keybindings=NocaseDict(k1=u'v1'),
                namespace=u'root/cimv2',
                host=u'10.11.12.13'),
        ),
        None, None, CHECK_0_12_0
    ),
    (
        "authority with IPv6 address",
        dict(
            uri='https://[10:11:12:13]/root/cimv2:CIM_Foo.k1="v1"',
            exp_attrs=dict(
                classname=u'CIM_Foo',
                keybindings=NocaseDict(k1=u'v1'),
                namespace=u'root/cimv2',
                host=u'[10:11:12:13]'),
        ),
        None, None, CHECK_0_12_0
    ),
    (
        "authority with IPv6 address and port",
        dict(
            uri='https://[10:11:12:13]:5989/root/cimv2:CIM_Foo.k1="v1"',
            exp_attrs=dict(
                classname=u'CIM_Foo',
                keybindings=NocaseDict(k1=u'v1'),
                namespace=u'root/cimv2',
                host=u'[10:11:12:13]:5989'),
        ),
        None, None, CHECK_0_12_0
    ),
    (
        "no namespace type",
        dict(
            uri='//10.11.12.13:5989/root/cimv2:CIM_Foo.k1="v1"',
            exp_attrs=dict(
                classname=u'CIM_Foo',
                keybindings=NocaseDict(k1=u'v1'),
                namespace=u'root/cimv2',
                host=u'10.11.12.13:5989'),
        ),
        None, None, CHECK_0_12_0
    ),
    (
        "namespace type http",
        dict(
            uri='http://10.11.12.13:5989/root/cimv2:CIM_Foo.k1="v1"',
            exp_attrs=dict(
                classname=u'CIM_Foo',
                keybindings=NocaseDict(k1=u'v1'),
                namespace=u'root/cimv2',
                host=u'10.11.12.13:5989'),
        ),
        None, None, CHECK_0_12_0
    ),
    (
        "namespace type upper case HTTP",
        dict(
            uri='HTTP://10.11.12.13:5989/root/cimv2:CIM_Foo.k1="v1"',
            exp_attrs=dict(
                classname=u'CIM_Foo',
                keybindings=NocaseDict(k1=u'v1'),
                namespace=u'root/cimv2',
                host=u'10.11.12.13:5989'),
        ),
        None, None, CHECK_0_12_0
    ),
    (
        "namespace type mixed case HttpS",
        dict(
            uri='HttpS://10.11.12.13:5989/root/cimv2:CIM_Foo.k1="v1"',
            exp_attrs=dict(
                classname=u'CIM_Foo',
                keybindings=NocaseDict(k1=u'v1'),
                namespace=u'root/cimv2',
                host=u'10.11.12.13:5989'),
        ),
        None, None, CHECK_0_12_0
    ),
    (
        "namespace type cimxml-wbem",
        dict(
            uri='cimxml-wbem://10.11.12.13:5989/root/cimv2:CIM_Foo.k1="v1"',
            exp_attrs=dict(
                classname=u'CIM_Foo',
                keybindings=NocaseDict(k1=u'v1'),
                namespace=u'root/cimv2',
                host=u'10.11.12.13:5989'),
        ),
        None, None, CHECK_0_12_0
    ),
    (
        "namespace type cimxml-wbems",
        dict(
            uri='cimxml-wbems://10.11.12.13:5989/root/cimv2:CIM_Foo.k1="v1"',
            exp_attrs=dict(
                classname=u'CIM_Foo',
                keybindings=NocaseDict(k1=u'v1'),
                namespace=u'root/cimv2',
                host=u'10.11.12.13:5989'),
        ),
        None, None, CHECK_0_12_0
    ),
    (
        "unknown namespace type",
        dict(
            uri='xyz://10.11.12.13:5989/root/cimv2:CIM_Foo.k1="v1"',
            exp_attrs=dict(
                classname=u'CIM_Foo',
                keybindings=NocaseDict(k1=u'v1'),
                namespace=u'root/cimv2',
                host=u'10.11.12.13:5989'),
        ),
        None, UserWarning, CHECK_0_12_0
    ),
    (
        "local WBEM URI (with initial slash)",
        dict(
            uri='/root/cimv2:CIM_Foo.k1="v1"',
            exp_attrs=dict(
                classname=u'CIM_Foo',
                keybindings=NocaseDict(k1=u'v1'),
                namespace=u'root/cimv2',
                host=None),
        ),
        None, None, CHECK_0_12_0
    ),
    (
        "local WBEM URI (with missing initial slash)",
        dict(
            uri='root/cimv2:CIM_Foo.k1="v1"',
            exp_attrs=dict(
                classname=u'CIM_Foo',
                keybindings=NocaseDict(k1=u'v1'),
                namespace=u'root/cimv2',
                host=None),
        ),
        None, None, CHECK_0_12_0
    ),
    (
        "local WBEM URI with only class name (with initial slash+colon)",
        dict(
            uri='/:CIM_Foo.k1="v1"',
            exp_attrs=dict(
                classname=u'CIM_Foo',
                keybindings=NocaseDict(k1=u'v1'),
                namespace=None,
                host=None),
        ),
        None, None, CHECK_0_12_0
    ),
    (
        "local WBEM URI with only class name (without initial slash)",
        dict(
            uri=':CIM_Foo.k1="v1"',
            exp_attrs=dict(
                classname=u'CIM_Foo',
                keybindings=NocaseDict(k1=u'v1'),
                namespace=None,
                host=None),
        ),
        None, None, CHECK_0_12_0
    ),
    (
        "local WBEM URI with only class name (without initial slash+colon)",
        dict(
            uri='CIM_Foo.k1="v1"',
            exp_attrs=dict(
                classname=u'CIM_Foo',
                keybindings=NocaseDict(k1=u'v1'),
                namespace=None,
                host=None),
        ),
        None, None, CHECK_0_12_0
    ),
    (
        "local WBEM URI with namespace that has only one component",
        dict(
            uri='/root:CIM_Foo.k1="v1"',
            exp_attrs=dict(
                classname=u'CIM_Foo',
                keybindings=NocaseDict(k1=u'v1'),
                namespace=u'root',
                host=None),
        ),
        None, None, CHECK_0_12_0
    ),
    (
        "local WBEM URI with namespace that has three components",
        dict(
            uri='/root/cimv2/test:CIM_Foo.k1="v1"',
            exp_attrs=dict(
                classname=u'CIM_Foo',
                keybindings=NocaseDict(k1=u'v1'),
                namespace=u'root/cimv2/test',
                host=None),
        ),
        None, None, CHECK_0_12_0
    ),
    (
        "multiple keys (bool) - in alphabetical order",
        dict(
            uri='/n:C.k1=false,k2=true,k3=False,k4=True,k5=FALSE,k6=TRUE',
            exp_attrs=dict(
                classname=u'C',
                keybindings=NocaseDict([
                    ('k1', False), ('k2', True),
                    ('k3', False), ('k4', True),
                    ('k5', False), ('k6', True)]),
                namespace=u'n',
                host=None),
        ),
        None, None, CHECK_0_12_0
    ),
    (
        "multiple keys (bool) - in non-alphabetical order",
        dict(
            uri='/n:C.k1=false,k3=False,k2=true,k4=True,k5=FALSE,k6=TRUE',
            exp_attrs=dict(
                classname=u'C',
                keybindings=NocaseDict([
                    ('k1', False), ('k3', False),
                    ('k2', True), ('k4', True),
                    ('k5', False), ('k6', True)]),
                namespace=u'n',
                host=None),
        ),
        None, None, CHECK_0_12_0
    ),
    (
        "multiple keys (int) - in non-alphabetical order",
        dict(
            uri='/n:C.k1=0,k2=-1,k3=-32769,k4=42,k5=+42,'
                'kmax32=4294967295,'
                'kmin32=-4294967296,'
                'kmax64=9223372036854775807,'
                'kmin64=-9223372036854775808,'
                'klong=9223372036854775808',
            exp_attrs=dict(
                classname=u'C',
                keybindings=NocaseDict([
                    ('k1', 0), ('k2', -1), ('k3', -32769),
                    ('k4', 42), ('k5', 42),
                    ('kmax32', 4294967295),
                    ('kmin32', -4294967296),
                    ('kmax64', 9223372036854775807),
                    ('kmin64', -9223372036854775808),
                    ('klong', 9223372036854775808)]),
                namespace=u'n',
                host=None),
        ),
        None, None, CHECK_0_12_0
    ),
    (
        "int key with invalid decimal digit U+0661 (ARABIC-INDIC ONE)",
        dict(
            uri=u'/n:C.k1=\u0661',
            exp_attrs=None,
        ),
        ValueError, None, CHECK_0_12_0
    ),
    (
        "int key with invalid decimal digit U+1D7CF (MATHEM. BOLD ONE)",
        dict(
            uri=u'/n:C.k1=\U0001d7cf',
            exp_attrs=None,
        ),
        ValueError, None, CHECK_0_12_0
    ),
    (
        "int key with invalid decimal digit U+2081 (SUBSCRIPT ONE)",
        dict(
            uri=u'/n:C.k1=\u2081',
            exp_attrs=None,
        ),
        ValueError, None, CHECK_0_12_0
    ),
    (
        "int key with invalid decimal digit U+00B9 (SUPERSCRIPT ONE)",
        dict(
            uri=u'/n:C.k1=\u00b9',
            exp_attrs=None,
        ),
        ValueError, None, CHECK_0_12_0
    ),
    (
        "int key with invalid non-decimal digit U+10A44 (KHAROSHTHI TEN)",
        dict(
            uri=u'/n:C.k1=\U00010a44',
            exp_attrs=None,
        ),
        ValueError, None, CHECK_0_12_0
    ),
    (
        "positive int key in octal representation",
        dict(
            uri=u'/n:C.k1=015',
            exp_attrs=dict(
                classname=u'C',
                keybindings=NocaseDict([('k1', 13)]),
                namespace=u'n',
                host=None),
        ),
        None, None, CHECK_0_12_0
    ),
    (
        "negative int key in octal representation",
        dict(
            uri=u'/n:C.k1=-017',
            exp_attrs=dict(
                classname=u'C',
                keybindings=NocaseDict([('k1', -15)]),
                namespace=u'n',
                host=None),
        ),
        None, None, CHECK_0_12_0
    ),
    (
        "int key in octal representation with invalid octal digits",
        dict(
            uri=u'/n:C.k1=018',
            exp_attrs=None,
        ),
        ValueError, None, CHECK_0_12_0
    ),
    (
        "positive int key in binary representation (upper case)",
        dict(
            uri=u'/n:C.k1=0101B',
            exp_attrs=dict(
                classname=u'C',
                keybindings=NocaseDict([('k1', 5)]),
                namespace=u'n',
                host=None),
        ),
        None, None, CHECK_0_12_0
    ),
    (
        "negative int key in binary representation (lower case)",
        dict(
            uri=u'/n:C.k1=-0101b',
            exp_attrs=dict(
                classname=u'C',
                keybindings=NocaseDict([('k1', -5)]),
                namespace=u'n',
                host=None),
        ),
        None, None, CHECK_0_12_0
    ),
    (
        "int key in binary representation with invalid binary digits",
        dict(
            uri=u'/n:C.k1=0102',
            exp_attrs=None,
        ),
        ValueError, None, CHECK_0_12_0
    ),
    (
        "positive int key in hex representation (upper case)",
        dict(
            uri=u'/n:C.k1=0X19AF',
            exp_attrs=dict(
                classname=u'C',
                keybindings=NocaseDict([('k1', 0x19AF)]),
                namespace=u'n',
                host=None),
        ),
        None, None, CHECK_0_12_0
    ),
    (
        "negative int key in hex representation (lower case)",
        dict(
            uri=u'/n:C.k1=-0x19af',
            exp_attrs=dict(
                classname=u'C',
                keybindings=NocaseDict([('k1', -0x19AF)]),
                namespace=u'n',
                host=None),
        ),
        None, None, CHECK_0_12_0
    ),
    (
        "int key in hex representation with invalid hex digits",
        dict(
            uri=u'/n:C.k1=0x19afg',
            exp_attrs=None,
        ),
        ValueError, None, CHECK_0_12_0
    ),
    (
        "multiple float keys - in non-alphabetical order",
        dict(
            uri='/n:C.k1=.0,k2=-0.1,k3=+.1,k4=+31.4E-1,k5=.4e1,'
                'kmax32=3.402823466E38,'
                'kmin32=1.175494351E-38,'
                'kmax64=1.7976931348623157E308,'
                'kmin64=4.9E-324',
            exp_attrs=dict(
                classname=u'C',
                keybindings=NocaseDict([
                    ('k1', 0.0), ('k2', -0.1), ('k3', 0.1),
                    ('k4', 31.4E-1), ('k5', 0.4E1),
                    ('kmax32', 3.402823466E38),
                    ('kmin32', 1.175494351E-38),
                    ('kmax64', 1.7976931348623157E308),
                    ('kmin64', 4.9E-324),
                ]),
                namespace=u'n',
                host=None),
        ),
        None, None, CHECK_0_12_0
    ),
    (
        "invalid float key 1. (not allowed in realValue)",
        dict(
            uri='/n:C.k1=1.',
            exp_attrs=None,
        ),
        ValueError, None, CHECK_0_12_0
    ),
    (
        "float key with special value INF (allowed by extension)",
        dict(
            uri='/n:C.k1=INF',
            exp_attrs=dict(
                classname=u'C',
                keybindings=NocaseDict(k1=float('inf')),
                namespace=u'n',
                host=None),
        ),
        None, None, CHECK_0_12_0
    ),
    (
        "float key with special value -INF (allowed by extension)",
        dict(
            uri='/n:C.k1=-INF',
            exp_attrs=dict(
                classname=u'C',
                keybindings=NocaseDict(k1=float('-inf')),
                namespace=u'n',
                host=None),
        ),
        None, None, CHECK_0_12_0
    ),
    (
        "float key with special value NAN (allowed by extension)",
        dict(
            uri='/n:C.k1=NAN',
            exp_attrs=dict(
                classname=u'C',
                keybindings=NocaseDict(k1=float('nan')),
                namespace=u'n',
                host=None),
        ),
        None, None, False  # float('nan') does not compare equal to itself
    ),
    (
        "multiple string keys - in alphabetical order",
        dict(
            uri=r'/n:C.k1="",k2="a",k3="42",k4="\"",k5="\\",k6="\\\"",k7="\'"',
            exp_attrs=dict(
                classname=u'C',
                keybindings=NocaseDict([
                    ('k1', ''), ('k2', 'a'), ('k3', '42'), ('k4', '"'),
                    ('k5', '\\'), ('k6', '\\"'), ('k7', "'"),
                ]),
                namespace=u'n',
                host=None),
        ),
        None, None, CHECK_0_12_0
    ),
    (
        "string key with keybindings syntax in its value",
        dict(
            uri=r'/n:C.k1="k2=42,k3=3"',
            exp_attrs=dict(
                classname=u'C',
                keybindings=NocaseDict(k1='k2=42,k3=3'),
                namespace=u'n',
                host=None),
        ),
        None, None, CHECK_0_12_0
    ),
    (
        "multiple char16 keys - in non-alphabetical order",
        dict(
            uri="/n:C.k1='a',k3='\"',k2='1',k4='\\'',k5='\\\\'",
            exp_attrs=dict(
                classname=u'C',
                keybindings=NocaseDict([
                    ('k1', 'a'), ('k3', '"'), ('k2', '1'), ('k4', "'"),
                    ('k5', '\\'),
                ]),
                namespace=u'n',
                host=None),
        ),
        None, None, CHECK_0_12_0
    ),
    (
        "empty char16 key",
        dict(
            uri="/n:C.k1=''",
            exp_attrs=None,
        ),
        ValueError, None, CHECK_0_12_0
    ),
    (
        "invalid char16 key with two characters",
        dict(
            uri="/n:C.k1='ab'",
            exp_attrs=None,
        ),
        ValueError, None, CHECK_0_12_0
    ),
    (
        "datetime key for point in time (in quotes)",
        dict(
            uri='/n:C.k1="19980125133015.123456-300"',
            exp_attrs=dict(
                classname=u'C',
                keybindings=NocaseDict([
                    ('k1', CIMDateTime('19980125133015.123456-300')),
                ]),
                namespace=u'n',
                host=None),
        ),
        None, None, CHECK_0_12_0
    ),
    (
        "datetime key for interval (in quotes)",
        dict(
            uri='/n:C.k1="12345678133015.123456:000"',
            exp_attrs=dict(
                classname=u'C',
                keybindings=NocaseDict([
                    ('k1', CIMDateTime('12345678133015.123456:000')),
                ]),
                namespace=u'n',
                host=None),
        ),
        None, None, CHECK_0_12_0
    ),
    (
        "datetime key for point in time (no quotes)",
        dict(
            uri='/n:C.k1=19980125133015.123456-300',
            exp_attrs=dict(
                classname=u'C',
                keybindings=NocaseDict([
                    ('k1', CIMDateTime('19980125133015.123456-300')),
                ]),
                namespace=u'n',
                host=None),
        ),
        None, UserWarning, CHECK_0_12_0
    ),
    (
        "datetime key for interval (no quotes)",
        dict(
            uri='/n:C.k1=12345678133015.123456:000',
            exp_attrs=dict(
                classname=u'C',
                keybindings=NocaseDict([
                    ('k1', CIMDateTime('12345678133015.123456:000')),
                ]),
                namespace=u'n',
                host=None),
        ),
        None, UserWarning, CHECK_0_12_0
    ),
    (
        "reference key that has an int key (normal association)",
        dict(
            uri='/n1:C1.k1="/n2:C2.k2=1"',
            exp_attrs=dict(
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
        ),
        None, None, CHECK_0_12_0
    ),
    (
        "reference key that has a string key (normal association)",
        dict(
            uri=r'/n1:C1.k1="/n2:C2.k2=\"v2\""',
            exp_attrs=dict(
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
        ),
        None, None, CHECK_0_12_0
    ),
    (
        "double nested reference to int key (association to association)",
        dict(
            uri=r'/n1:C1.k1="/n2:C2.k2=\"/n3:C3.k3=3\""',
            exp_attrs=dict(
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
                host=None,
            ),
        ),
        None, None, CHECK_0_12_0
    ),
    (
        "double nested reference to string key (association to "
        "association)",
        dict(
            uri=r'/n1:C1.k1="/n2:C2.k2=\"/n3:C3.k3=\\\"v3\\\"\""',
            exp_attrs=dict(
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
                host=None,
            ),
        ),
        None, None, CHECK_0_12_0
    ),
    (
        "missing delimiter / before authority",
        dict(
            uri='https:/10.11.12.13/cimv2:CIM_Foo.k1="v1"',
            exp_attrs=None,
        ),
        ValueError, None, CHECK_0_12_0
    ),
    (
        "invalid char ; in authority",
        dict(
            uri='https://10.11.12.13;5989/cimv2:CIM_Foo.k1="v1"',
            exp_attrs=None,
        ),
        ValueError, None, CHECK_0_12_0
    ),
    (
        "delimiter / before namespace replaced with :",
        dict(
            uri='https://10.11.12.13:5989:root:CIM_Foo.k1="v1"',
            exp_attrs=None,
        ),
        ValueError, None, CHECK_0_12_0
    ),
    (
        "delimiter : before classname replaced with .",
        dict(
            uri='https://10.11.12.13:5989/root.CIM_Foo.k1="v1"',
            exp_attrs=None,
        ),
        ValueError, None, CHECK_0_12_0
    ),
    (
        "invalid '/' between namespace and classname",
        dict(
            uri='https://10.11.12.13:5989/cimv2/CIM_Foo.k1="v1"',
            exp_attrs=None,
        ),
        ValueError, None, CHECK_0_12_0
    ),
    (
        "class name missing",
        dict(
            uri='https://10.11.12.13:5989/root/cimv2:k1="v1"',
            exp_attrs=None,
        ),
        ValueError, None, CHECK_0_12_0
    ),
    (
        "class path used as instance path",
        dict(
            uri='https://10.11.12.13:5989/root:CIM_Foo',
            exp_attrs=None,
        ),
        ValueError, None, CHECK_0_12_0
    ),
    (
        "invalid ':' between classname and key k1",
        dict(
            uri='https://10.11.12.13:5989/cimv2:CIM_Foo:k1="v1"',
            exp_attrs=None,
        ),
        ValueError, None, CHECK_0_12_0
    ),
    (
        "invalid '/' between classname and key k1",
        dict(
            uri='https://10.11.12.13:5989/cimv2:CIM_Foo/k1="v1"',
            exp_attrs=None,
        ),
        ValueError, None, CHECK_0_12_0
    ),
    (
        "invalid '.' between key k1 and key k2",
        dict(
            uri='https://10.11.12.13:5989/cimv2:CIM_Foo.k1="v1".k2="v2"',
            exp_attrs=None,
        ),
        ValueError, None, CHECK_0_12_0 and False
    ),
    (
        "invalid ':' between key k1 and key k2",
        dict(
            uri='https://10.11.12.13:5989/cimv2:CIM_Foo.k1="v1":k2="v2"',
            exp_attrs=None,
        ),
        ValueError, None, CHECK_0_12_0 and False
    ),
    (
        "double quotes missing around string value of key k2",
        dict(
            uri='https://10.11.12.13:5989/cimv2:CIM_Foo.k1="v1".k2=v2',
            exp_attrs=None,
        ),
        ValueError, None, CHECK_0_12_0 and False
    ),
    (
        "invalid double comma between keybindings",
        dict(
            uri='https://10.11.12.13:5989/cimv2:CIM_Foo.k1="v1",,k2=42',
            exp_attrs=None,
        ),
        ValueError, None, CHECK_0_12_0
    ),
    (
        "invalid comma after last keybinding",
        dict(
            uri='https://10.11.12.13:5989/cimv2:CIM_Foo.k1="v1",k2=42,',
            exp_attrs=None,
        ),
        ValueError, None, CHECK_0_12_0
    ),
    (
        "equal sign missing in keyinding",
        dict(
            uri='https://10.11.12.13:5989/cimv2:CIM_Foo.k1="v1",k242',
            exp_attrs=None,
        ),
        ValueError, None, CHECK_0_12_0
    ),
    (
        "double equal sign in keyinding",
        dict(
            uri='https://10.11.12.13:5989/cimv2:CIM_Foo.k1="v1",k2==42',
            exp_attrs=None,
        ),
        ValueError, None, CHECK_0_12_0
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_CIMINSTANCENAME_FROM_WBEM_URI)
@simplified_test_function
def test_CIMInstanceName_from_wbem_uri(testcase,
                                       uri, exp_attrs):
    """
    Test function for CIMInstanceName.from_wbem_uri()
    """

    # The code to be tested
    obj = CIMInstanceName.from_wbem_uri(uri)

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None

    assert isinstance(obj, CIMInstanceName)

    exp_classname = exp_attrs['classname']
    assert obj.classname == exp_classname
    assert isinstance(obj.classname, type(exp_classname))

    exp_keybindings = exp_attrs['keybindings']
    assert obj.keybindings == exp_keybindings
    assert isinstance(obj.keybindings, type(exp_keybindings))

    exp_namespace = exp_attrs['namespace']
    assert obj.namespace == exp_namespace
    assert isinstance(obj.namespace, type(exp_namespace))

    exp_host = exp_attrs['host']
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
            "Verify class with single key works",
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
            "Verify class with two keys  works",
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
                keybindings=[('P1', 'Ham'), ('P2', 'Cheese')]
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
                classname='CIM_Foo'
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
                classname='CIM_Foo'
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
    def test_CIMInstanceName_from_instance(  # XXX: Migrate to s.tst.fnc.
            self, desc, cls_kwargs, inst_kwargs, exp_result, strict, ns, host,
            condition):
        # pylint: disable=unused-argument
        """Test function for CIMInstanceName.from_instance."""

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
        # * format_: Format for to_wbem_uri(): one of 'standard', 'canonical',
        #     'cimobject', 'historical'.
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
            "all components, canonical format",
            dict(
                classname=u'CIM_Foo',
                keybindings=NocaseDict(K1=u'V1'),
                namespace=u'root/CIMv2',
                host=u'MyHost:5989'),
            'canonical',
            '//myhost:5989/root/cimv2:cim_foo.k1="V1"',
            None, CHECK_0_12_0
        ),
        (
            "all components, cimobject format (host is ignored)",
            dict(
                classname=u'CIM_Foo',
                keybindings=NocaseDict(k1=u'v1'),
                namespace=u'root/cimv2',
                host=u'10.11.12.13:5989'),
            'cimobject',
            '/root/cimv2:CIM_Foo.k1="v1"',
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
            "no authority, canonical format",
            dict(
                classname=u'CIM_Foo',
                keybindings=NocaseDict(K1=u'V1'),
                namespace=u'root/CIMv2',
                host=None),
            'canonical',
            '/root/cimv2:cim_foo.k1="V1"',
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
            "local WBEM URI with only class name, canonical format",
            dict(
                classname=u'CIM_Foo',
                keybindings=NocaseDict(K1=u'V1'),
                namespace=None,
                host=None),
            'canonical',
            '/:cim_foo.k1="V1"',
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
            "multiple keys (bool) in alphabetical order, standard format",
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
            "multiple keys (bool) in alphabetical order (lower-cased), "
            "canonical format",
            dict(
                classname=u'C',
                keybindings=NocaseDict([('j1', False), ('K2', True)]),
                namespace=u'N',
                host=None),
            'canonical',
            '/n:c.j1=FALSE,k2=TRUE',
            None, CHECK_0_12_0
        ),
        (
            "multiple keys (bool) in non-alphabetical order, standard format",
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
            "multiple keys (bool) in non-alphabetical order (lower-cased), "
            "canonical format",
            dict(
                classname=u'C',
                keybindings=NocaseDict([('K2', True), ('j1', False)]),
                namespace=u'N',
                host=None),
            'canonical',
            '/n:c.j1=FALSE,k2=TRUE',
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
            "reference key that has an int key (normal association), "
            "standard format",
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
            "reference key that has an int key (normal association), "
            "canonical format",
            dict(
                classname=u'C1',
                keybindings=[
                    ('K1', CIMInstanceName(
                        classname='C2',
                        keybindings=[
                            ('K2', 1),
                        ],
                        namespace='N2')),
                ],
                namespace=u'N1',
                host=None),
            'canonical',
            '/n1:c1.k1="/n2:c2.k2=1"',
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
        "desc, attrs, format_, exp_result, exp_warn_type, condition",
        testcases)
    def test_CIMInstanceName_to_wbem_uri_str(  # XXX: Migrate to s.tst.fnc.
            self, desc, attrs, format_, exp_result, exp_warn_type, condition,
            func_name):
        # pylint: disable=unused-argument
        """Test function for CIMInstanceName.to_wbem_uri() and .__str__()."""

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
            func_kwargs = dict(format=format_)
        if func_name == '__str__':
            if format_ != 'historical':
                pytest.skip("Not testing CIMInstanceName.__str__() with "
                            "format: %r" % format_)
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

    def test_CIMInstance_init_pos_args(self):  # XXX: Merge with succeeds
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
            "Verify that bytes classname is converted to unicode",
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
            "Verify property with bytes string value",
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
    def test_CIMInstance_init_succeeds(  # XXX: Migrate to s.tst.fnc.
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
    def test_CIMInstance_init_fails(  # XXX: Merge with succeeds
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

    def test_CIMInstance_copy(self):  # XXX: Migrate to pytest

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

    def test_CIMInstance_attrs(self):  # XXX: Migrate to pytest

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

    def test_CIMInstance_dict(self):  # XXX: Migrate to pytest

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
                # pylint: disable=undefined-variable
                obj['Foo'] = long(43)  # noqa: F821

        # Setting properties to CIM data type values

        obj['Foo'] = Uint32(43)


class CIMInstanceEquality(unittest.TestCase):
    """Test comparing CIMInstance objects."""

    def test_CIMInstance_eq(self):  # XXX: Migrate to pytest

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
    def test_CIMInstance_cmp(self):  # XXX: Implement with pytest
        raise AssertionError("test not implemented")


class CIMInstanceSort(unittest.TestCase):
    """
    Test the sorting of `CIMInstance` objects.
    """

    @unimplemented
    def test_CIMInstance_sort(self):  # XXX: Implement with pytest
        raise AssertionError("test not implemented")


# Special CIMInstance objects for TESTCASES_CIMINSTANCE_HASH:
with pytest.warns(DeprecationWarning):
    _INST_HASH_A_1 = CIMInstance(
        'CIM_Foo',
        properties={'Cheepy': 'Birds'},
        property_list=['Cheepy'],
    )
    _INST_HASH_A_2 = CIMInstance(
        'CIM_Foo',
        properties={'Cheepy': 'Birds'},
        property_list=[],
    )


TESTCASES_CIMINSTANCE_HASH = [

    # Testcases for CIMInstance.__hash__()

    # Each list item is a testcase tuple with these items:
    # * desc: Short testcase description.
    # * kwargs: Keyword arguments for the test function:
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
        "Scalar property with different types: bool True / string 'TRUE'",
        dict(
            obj1=CIMInstance('CIM_Foo', properties={'Foo': True}),
            obj2=CIMInstance('CIM_Foo', properties={'Foo': 'TRUE'}),
            exp_hash_equal=False,
        ),
        None, None, True
    ),
    (
        "Scalar property with different types: bool False / string 'FALSE'",
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
            obj1=_INST_HASH_A_1,
            obj2=_INST_HASH_A_2,
            exp_hash_equal=True,
        ),
        None, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_CIMINSTANCE_HASH)
@simplified_test_function
def test_CIMInstance_hash(testcase,
                          obj1, obj2, exp_hash_equal):
    """
    Test function for CIMInstance.__hash__().
    """

    # The code to be tested
    hash1 = hash(obj1)
    hash2 = hash(obj2)

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None

    # Double check they are different objects
    assert id(obj1) != id(obj2)

    if exp_hash_equal:
        assert hash1 == hash2
    else:
        assert hash1 != hash2


TESTCASES_CIMINSTANCE_STR_REPR = [

    # Testcases for CIMInstance.__repr__(), __str__() / repr(), str()

    # Each list item is a testcase tuple with these items:
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
            path=CIMInstanceName(
                'CIM_Foo',
                keybindings=dict(Name='Spottyfoot')))
    ),
]


@pytest.mark.parametrize(
    "obj",
    TESTCASES_CIMINSTANCE_STR_REPR)
def test_CIMInstance_str(obj):
    """
    Test function for CIMInstance.__str__() / str()
    """

    # The code to be tested
    s = str(obj)

    assert re.match(r'^CIMInstance\(', s)

    exp_classname = _format('classname={0!A}', obj.classname)
    assert exp_classname in s

    exp_path = _format('path={0!A}', obj.path)
    assert exp_path in s


@pytest.mark.parametrize(
    "obj",
    TESTCASES_CIMINSTANCE_STR_REPR)
def test_CIMInstance_repr(obj):
    """
    Test function for CIMInstance.__repr__() / repr()
    """

    # The code to be tested
    r = repr(obj)

    assert re.match(r'^CIMInstance\(', r)

    exp_classname = _format('classname={0!A}', obj.classname)
    assert exp_classname in r

    exp_path = _format('path={0!A}', obj.path)
    assert exp_path in r

    exp_properties = _format('properties={0!A}', obj.properties)
    assert exp_properties in r

    exp_property_list = _format('property_list={0!A}', obj.property_list)
    assert exp_property_list in r

    exp_qualifiers = _format('qualifiers={0!A}', obj.qualifiers)
    assert exp_qualifiers in r


# Some CIMInstance objects for CIMInstance.tocimxml() tests

CIMINSTANCE_INV_PROPERTY_1 = CIMInstance('CIM_Foo')
CIMINSTANCE_INV_PROPERTY_1.properties['Foo'] = 'bla'  # no CIMProperty

CIMINSTANCE_INV_PROPERTY_2 = CIMInstance('CIM_Foo')
CIMINSTANCE_INV_PROPERTY_2.properties['Foo'] = Uint16(42)  # no CIMProperty

# Some CIMInstanceName objects for CIMInstance.tocimxml() tests

CIMINSTANCENAME_CLASSNAME1 = CIMInstanceName('CIM_Foo')
CIMINSTANCENAME_NAMESPACE1 = CIMInstanceName('CIM_Foo', namespace='interop')
CIMINSTANCENAME_HOST1 = CIMInstanceName('CIM_Foo', namespace='interop',
                                        host='woot.com')

TESTCASES_CIMINSTANCE_TOCIMXML = [

    # Testcases for CIMInstance.tocimxml() and tocimxmlstr()

    # Each list item is a testcase tuple with these items:
    # * desc: Short testcase description.
    # * kwargs: Keyword arguments for the test function:
    #   * obj: CIMInstance object to be tested.
    #   * kwargs: Dict of input args for tocimxml().
    #   * exp_xml_str: Expected CIM-XML string, as a tuple/list of parts.
    # * exp_exc_types: Expected exception type(s), or None.
    # * exp_warn_types: Expected warning type(s), or None.
    # * condition: Boolean condition for testcase to run, or 'pdb' for debugger

    # Tests with path and args variations
    (
        "No path, implied default args",
        dict(
            obj=CIMInstance('CIM_Foo'),
            kwargs=dict(),
            exp_xml_str=(
                '<INSTANCE CLASSNAME="CIM_Foo"/>',
            )
        ),
        None, None, True
    ),
    (
        "No path, specified default args",
        dict(
            obj=CIMInstance('CIM_Foo'),
            kwargs=dict(
                ignore_path=False,
            ),
            exp_xml_str=(
                '<INSTANCE CLASSNAME="CIM_Foo"/>',
            )
        ),
        None, None, True
    ),
    (
        "No path, non-default args ignore_path=True",
        dict(
            obj=CIMInstance('CIM_Foo'),
            kwargs=dict(
                ignore_path=True,
            ),
            exp_xml_str=(
                '<INSTANCE CLASSNAME="CIM_Foo"/>',
            )
        ),
        None, None, True
    ),
    (
        "Path with classname-only, implied default args",
        dict(
            obj=CIMInstance(
                'CIM_Foo',
                path=CIMINSTANCENAME_CLASSNAME1,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<VALUE.NAMEDINSTANCE>',
                '<INSTANCENAME CLASSNAME="CIM_Foo"/>',
                '<INSTANCE CLASSNAME="CIM_Foo"/>',
                '</VALUE.NAMEDINSTANCE>',
            )
        ),
        None, None, True
    ),
    (
        "Path with classname-only, specified default args",
        dict(
            obj=CIMInstance(
                'CIM_Foo',
                path=CIMINSTANCENAME_CLASSNAME1,
            ),
            kwargs=dict(
                ignore_path=False,
            ),
            exp_xml_str=(
                '<VALUE.NAMEDINSTANCE>',
                '<INSTANCENAME CLASSNAME="CIM_Foo"/>',
                '<INSTANCE CLASSNAME="CIM_Foo"/>',
                '</VALUE.NAMEDINSTANCE>',
            )
        ),
        None, None, True
    ),
    (
        "Path with classname-only, non-default args ignore_path=True",
        dict(
            obj=CIMInstance(
                'CIM_Foo',
                path=CIMINSTANCENAME_CLASSNAME1,
            ),
            kwargs=dict(
                ignore_path=True,
            ),
            exp_xml_str=(
                '<INSTANCE CLASSNAME="CIM_Foo"/>',
            )
        ),
        None, None, True
    ),
    (
        "Path with namespace, implied default args",
        dict(
            obj=CIMInstance(
                'CIM_Foo',
                path=CIMINSTANCENAME_NAMESPACE1,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<VALUE.OBJECTWITHLOCALPATH>',
                '<LOCALINSTANCEPATH>',
                '<LOCALNAMESPACEPATH>',
                '<NAMESPACE NAME="interop"/>',
                '</LOCALNAMESPACEPATH>',
                '<INSTANCENAME CLASSNAME="CIM_Foo"/>',
                '</LOCALINSTANCEPATH>',
                '<INSTANCE CLASSNAME="CIM_Foo"/>',
                '</VALUE.OBJECTWITHLOCALPATH>',
            )
        ),
        None, None, True
    ),
    (
        "Path with namespace, specified default args",
        dict(
            obj=CIMInstance(
                'CIM_Foo',
                path=CIMINSTANCENAME_NAMESPACE1,
            ),
            kwargs=dict(
                ignore_path=False,
            ),
            exp_xml_str=(
                '<VALUE.OBJECTWITHLOCALPATH>',
                '<LOCALINSTANCEPATH>',
                '<LOCALNAMESPACEPATH>',
                '<NAMESPACE NAME="interop"/>',
                '</LOCALNAMESPACEPATH>',
                '<INSTANCENAME CLASSNAME="CIM_Foo"/>',
                '</LOCALINSTANCEPATH>',
                '<INSTANCE CLASSNAME="CIM_Foo"/>',
                '</VALUE.OBJECTWITHLOCALPATH>',
            )
        ),
        None, None, True
    ),
    (
        "Path with namespace, non-default args ignore_path=True",
        dict(
            obj=CIMInstance(
                'CIM_Foo',
                path=CIMINSTANCENAME_NAMESPACE1,
            ),
            kwargs=dict(
                ignore_path=True,
            ),
            exp_xml_str=(
                '<INSTANCE CLASSNAME="CIM_Foo"/>',
            )
        ),
        None, None, True
    ),
    (
        "Path with namespace+host, implied default args",
        dict(
            obj=CIMInstance(
                'CIM_Foo',
                path=CIMINSTANCENAME_HOST1,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<VALUE.INSTANCEWITHPATH>',
                '<INSTANCEPATH>',
                '<NAMESPACEPATH>',
                '<HOST>woot.com</HOST>',
                '<LOCALNAMESPACEPATH>',
                '<NAMESPACE NAME="interop"/>',
                '</LOCALNAMESPACEPATH>',
                '</NAMESPACEPATH>',
                '<INSTANCENAME CLASSNAME="CIM_Foo"/>',
                '</INSTANCEPATH>',
                '<INSTANCE CLASSNAME="CIM_Foo"/>',
                '</VALUE.INSTANCEWITHPATH>',
            )
        ),
        None, None, True
    ),
    (
        "Path with namespace+host, specified default args",
        dict(
            obj=CIMInstance(
                'CIM_Foo',
                path=CIMINSTANCENAME_HOST1,
            ),
            kwargs=dict(
                ignore_path=False,
            ),
            exp_xml_str=(
                '<VALUE.INSTANCEWITHPATH>',
                '<INSTANCEPATH>',
                '<NAMESPACEPATH>',
                '<HOST>woot.com</HOST>',
                '<LOCALNAMESPACEPATH>',
                '<NAMESPACE NAME="interop"/>',
                '</LOCALNAMESPACEPATH>',
                '</NAMESPACEPATH>',
                '<INSTANCENAME CLASSNAME="CIM_Foo"/>',
                '</INSTANCEPATH>',
                '<INSTANCE CLASSNAME="CIM_Foo"/>',
                '</VALUE.INSTANCEWITHPATH>',
            )
        ),
        None, None, True
    ),
    (
        "Path with namespace+host, non-default args ignore_path=True",
        dict(
            obj=CIMInstance(
                'CIM_Foo',
                path=CIMINSTANCENAME_HOST1,
            ),
            kwargs=dict(
                ignore_path=True,
            ),
            exp_xml_str=(
                '<INSTANCE CLASSNAME="CIM_Foo"/>',
            )
        ),
        None, None, True
    ),

    # Tests with property variations
    (
        "Two properties",
        dict(
            obj=CIMInstance(
                'CIM_Foo',
                properties=[
                    CIMProperty('P1', 'bla'),
                    CIMProperty('P2', 42, type='uint16'),
                ],
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<INSTANCE CLASSNAME="CIM_Foo">',
                '<PROPERTY NAME="P1" TYPE="string">',
                '<VALUE>bla</VALUE>',
                '</PROPERTY>',
                '<PROPERTY NAME="P2" TYPE="uint16">',
                '<VALUE>42</VALUE>',
                '</PROPERTY>',
                '</INSTANCE>',
            )
        ),
        None, None, True
    ),

    # Tests with qualifier variations
    (
        "Two qualifiers",
        dict(
            obj=CIMInstance(
                'CIM_Foo',
                qualifiers=[
                    CIMQualifier('Q2', 'bla'),
                    CIMQualifier('Q1', True),
                ],
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<INSTANCE CLASSNAME="CIM_Foo">',
                '<QUALIFIER NAME="Q2" TYPE="string">',
                '<VALUE>bla</VALUE>',
                '</QUALIFIER>',
                '<QUALIFIER NAME="Q1" TYPE="boolean">',
                '<VALUE>TRUE</VALUE>',
                '</QUALIFIER>',
                '</INSTANCE>',
            )
        ),
        None, None, True
    ),

    # Tests with qualifier, property variations
    (
        "Two qualifiers and two properties",
        dict(
            obj=CIMInstance(
                'CIM_Foo',
                qualifiers=[
                    CIMQualifier('Q2', 'bla'),
                    CIMQualifier('Q1', True),
                ],
                properties=[
                    CIMProperty('P2', 42, type='uint16'),
                    CIMProperty('P1', 'bla'),
                ],
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<INSTANCE CLASSNAME="CIM_Foo">',
                '<QUALIFIER NAME="Q2" TYPE="string">',
                '<VALUE>bla</VALUE>',
                '</QUALIFIER>',
                '<QUALIFIER NAME="Q1" TYPE="boolean">',
                '<VALUE>TRUE</VALUE>',
                '</QUALIFIER>',
                '<PROPERTY NAME="P2" TYPE="uint16">',
                '<VALUE>42</VALUE>',
                '</PROPERTY>',
                '<PROPERTY NAME="P1" TYPE="string">',
                '<VALUE>bla</VALUE>',
                '</PROPERTY>',
                '</INSTANCE>',
            )
        ),
        None, None, True
    ),

    # Tests with invalid property objects
    (
        "With invalid property object (type string)",
        dict(
            obj=CIMINSTANCE_INV_PROPERTY_1,
            kwargs=dict(),
            exp_xml_str=None if CHECK_0_12_0 else \
            (
                '<INSTANCE CLASSNAME="CIM_Foo">',
                '<PROPERTY NAME="Foo" TYPE="string">',
                '<VALUE>bla</VALUE>',
                '</PROPERTY>',
                '</INSTANCE>',
            )
        ),
        TypeError if CHECK_0_12_0 else None, None, True
    ),
    (
        "With invalid property object (type Uint16)",
        dict(
            obj=CIMINSTANCE_INV_PROPERTY_2,
            kwargs=dict(),
            exp_xml_str=None if CHECK_0_12_0 else \
            (
                '<INSTANCE CLASSNAME="CIM_Foo">',
                '<PROPERTY NAME="Foo" TYPE="uint16">',
                '<VALUE>42</VALUE>',
                '</PROPERTY>',
                '</INSTANCE>',
            )
        ),
        TypeError if CHECK_0_12_0 else None, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_CIMINSTANCE_TOCIMXML)
@simplified_test_function
def test_CIMInstance_tocimxml(testcase,
                              obj, kwargs, exp_xml_str):
    """
    Test function for CIMInstance.tocimxml().
    """

    # The code to be tested
    obj_xml = obj.tocimxml(**kwargs)

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None

    obj_xml_str = obj_xml.toxml()
    exp_xml_str = ''.join(exp_xml_str)
    validate_cim_xml_obj(obj, obj_xml_str, exp_xml_str)


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_CIMINSTANCE_TOCIMXML)
@simplified_test_function
def test_CIMInstance_tocimxmlstr(testcase,
                                 obj, kwargs, exp_xml_str):
    """
    Test function for CIMInstance.tocimxmlstr().
    """

    # The code to be tested
    obj_xml_str = obj.tocimxmlstr(**kwargs)

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None

    assert isinstance(obj_xml_str, six.text_type)

    exp_xml_str = ''.join(exp_xml_str)
    validate_cim_xml_obj(obj, obj_xml_str, exp_xml_str)


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_CIMINSTANCE_TOCIMXML)
@simplified_test_function
def test_CIMInstance_tocimxmlstr_indent_int(
        testcase, obj, kwargs, exp_xml_str):
    """
    Test function for CIMInstance.tocimxmlstr() with indent as integer.
    """

    indent = 4
    indent_str = ' ' * indent

    # The code to be tested
    obj_xml_str = obj.tocimxmlstr(indent=indent, **kwargs)

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None

    obj_xml = obj.tocimxml(**kwargs)  # This is tested elsewhere
    exp_xml_str = obj_xml.toprettyxml(indent=indent_str)

    assert obj_xml_str == exp_xml_str, \
        "{0}.tocimxmlstr(indent={1!r}) returns unexpected CIM-XML string". \
        format(obj.__class__.__name__, indent)


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_CIMINSTANCE_TOCIMXML)
@simplified_test_function
def test_CIMInstance_tocimxmlstr_indent_str(
        testcase, obj, kwargs, exp_xml_str):
    """
    Test function for CIMInstance.tocimxmlstr() with indent as string.
    """

    indent = 4
    indent_str = ' ' * indent

    # The code to be tested
    obj_xml_str = obj.tocimxmlstr(indent=indent_str, **kwargs)

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None

    obj_xml = obj.tocimxml(**kwargs)  # This is tested elsewhere
    exp_xml_str = obj_xml.toprettyxml(indent=indent_str)

    assert obj_xml_str == exp_xml_str, \
        "{0}.tocimxmlstr(indent={1!r}) returns unexpected CIM-XML string". \
        format(obj.__class__.__name__, indent_str)


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
    def test_CIMInstance_tomof(  # XXX: Migrate to s.tst.fnc.
            self, desc, obj, exp_result, exp_warn_type, condition):
        # pylint: disable=unused-argument
        """Test function for CIMInstance.tomof()."""

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

    def test_CIMInstance_tomof_indent_warning(self):  # XXX: Migrate to pytest
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

    def test_CIMInstance_update_path(self):  # XXX: Migrate to pytest

        iname = CIMInstanceName('CIM_Foo', namespace='root/cimv2',
                                keybindings={'k1': 'blah', 'k2': 'blah'})

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

    def test_CIMInstance_property_list(self):  # XXX: Migrate to pytest

        iname = CIMInstanceName('CIM_Foo', namespace='root/cimv2',
                                keybindings={'k1': 'blah', 'k2': 'blah'})

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

    def test_CIMInstance_update_existing(self):  # XXX: Migrate to pytest

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


# Components to build the test class for the instance_from class test
TST_CLS = 'CIM_Foo'
ID_PROP = CIMProperty(u'ID', None, type='string', class_origin=TST_CLS,
                      qualifiers={'Key': CIMQualifier('Key', True)})
STR_PROP = CIMProperty(u'STR', None, type='string', class_origin=TST_CLS)
INT_PROP = CIMProperty(u'U32', None, type='uint32', class_origin=TST_CLS)
ARR_PROP = CIMProperty(u'A32', None, type='uint32', is_array=True,
                       class_origin=TST_CLS)
REF_PROP = CIMProperty(u'REF', None, type='reference', class_origin=TST_CLS,
                       reference_class='CIM_Foo')
# Properties with default in class
ID_PROP_D = CIMProperty(u'ID', u"cls_id", type='string', class_origin=TST_CLS,
                        qualifiers={'Key': CIMQualifier('Key', True)})
STR_PROP_D = CIMProperty(u'STR', u"cls_str", type='string',
                         class_origin=TST_CLS)
INT_PROP_D = CIMProperty(u'U32', 4, type='uint32', class_origin=TST_CLS)


# Temporary flags to clarify state of each test below.
# set condition to OK for tests that we know passed.  Setting OK to True runs
#     all tests and OK = False, bypasses all tests with OK
# Set condition to FAIL for any tests currently failing. Bypasses these tests
# Set condition to RUN for test currently being run
OK = True
FAIL = False
RUN = True

TESTCASES_CIMINSTANCE_FROMCLASS = [

    # Testcases for CIMInstance.tocimxml() and tocimxmlstr()

    # Each list item is a testcase tuple with these items:
    # * desc: Short testcase description.
    # * kwargs: Keyword arguments for the test function:
    #   * cls_props: Dict of input properties for CIMClass.
    #   * inst_prop_vals: Dict of property values for the instance
    #   * kwargs: Dict of input args to from_class method
    #   * exp_props: Expected properties in created instance as a dictionary
    # * exp_exc_types: Expected exception type(s), or None.
    # * exp_warn_types: Expected warning type(s), or None.
    # * condition: Boolean condition for testcase to run, or 'pdb' for debugger

    # Tests based on class with 3 properties
    (
        "Verify same properties in instance and class and default params"
        " passes (returns instance that matches exp_props",
        dict(
            cls_props=(ID_PROP, STR_PROP, INT_PROP),
            inst_prop_vals={u'ID': u'inst_id', u'STR': u'str_val',
                            u'U32': Uint32(3)},
            kwargs={},
            exp_props={u'ID': u'inst_id', u'STR': u'str_val',
                       u'U32': Uint32(3)},
        ),
        None, None, OK
    ),
    (
        "Verify same property names case independent. Instance properties set"
        "to lower case in test",
        dict(
            cls_props=(ID_PROP, STR_PROP, INT_PROP),
            inst_prop_vals={u'id': u'inst_id', u'str': u'str_val',
                            u'u32': Uint32(3)},
            kwargs={'include_path': True},
            exp_props={u'ID': u'inst_id', u'STR': u'str_val',
                       u'U32': Uint32(3)},
        ),
        None, None, OK
    ),
    (
        "Verify same property names case independent. This only works if "
        "property_values is a case independent dictionary.",
        dict(
            cls_props=(ID_PROP, STR_PROP, INT_PROP),
            inst_prop_vals={u'id': u'inst_id', u'str': u'str_val',
                            u'u32': Uint32(3)},
            kwargs={'include_path': True},
            exp_props={u'id': u'inst_id', u'str': u'str_val',
                       u'u32': Uint32(3)},
        ),
        None, None, OK
    ),
    (
        "Verify same properties in instance and class and default params"
        " passes (returns instance that matches exp_props",
        dict(
            cls_props=(ID_PROP, STR_PROP, INT_PROP, REF_PROP),
            inst_prop_vals={u'ID': u'inst_id', u'STR': u'str_val',
                            u'U32': Uint32(3), u'REF':
                            CIMInstanceName('CIM_Foo',
                                            keybindings={'InstID': '1234'},
                                            host='woot.com',
                                            namespace='root/cimv2')},
            kwargs={},
            exp_props={u'ID': u'inst_id', u'STR': u'str_val',
                       u'U32': Uint32(3),
                       u'REF': CIMProperty(u'REF',
                                           CIMInstanceName(
                                               'CIM_Foo',
                                               keybindings={'InstID': '1234'},
                                               host='woot.com',
                                               namespace='root/cimv2'),
                                           type='reference',
                                           reference_class='CIM_Foo')},
        ),
        None, None, OK
    ),
    (
        "Verify class with only 2 props defined in instance, 3 in class. "
        "inc_null_prop=True passes",
        dict(
            cls_props=(ID_PROP, STR_PROP, INT_PROP),
            inst_prop_vals={u'ID': u'inst_id', u'STR': u'str_val'},
            kwargs={'include_missing_properties': True},
            exp_props={u'ID': u'inst_id', u'STR': u'str_val',
                       u'U32': CIMProperty(u'U32', None, type='uint32')},
        ),
        None, None, OK
    ),
    (
        "Verify 2 props defined in instance inc_nul_prop=True passes",
        dict(
            cls_props=(ID_PROP, STR_PROP, INT_PROP),
            inst_prop_vals={u'ID': u'inst_id', u'STR': u'str_val'},
            kwargs={'include_missing_properties': True},
            exp_props={u'ID': u'inst_id', u'STR': u'str_val',
                       u'U32': CIMProperty(u'U32', None, type='uint32')},
        ),
        None, None, OK
    ),
    (
        "Verify 2 props defined in instance inc_null_prop=False passes",
        dict(
            cls_props=(ID_PROP, STR_PROP, INT_PROP),
            inst_prop_vals={u'ID': u'inst_id', u'STR': u'str_val'},
            kwargs={'include_missing_properties': False},
            exp_props={u'ID': u'inst_id', u'STR': u'str_val'},
        ),
        None, None, OK
    ),
    # Test include path option
    (
        "Verify class and inst with 3 properties tests include path = True "
        "passes.",
        dict(
            cls_props=(ID_PROP, STR_PROP, INT_PROP),
            inst_prop_vals={u'ID': u'inst_id', u'STR': u'str_val',
                            u'U32': Uint32(3)},
            kwargs={'include_path': True},
            exp_props={u'ID': u'inst_id', u'STR': u'str_val',
                       u'U32': Uint32(3)},
        ),
        None, None, OK
    ),
    (
        "Verify Class with 3 properties, params: include_path=False passes",
        dict(
            cls_props=(ID_PROP, STR_PROP, INT_PROP),
            inst_prop_vals={u'ID': 'inst_id', u'STR': 'str_val',
                            u'U32': Uint32(3)},
            kwargs={'include_path': False},
            exp_props={u'ID': u'inst_id', u'STR': u'str_val',
                       u'U32': Uint32(3)},
        ),
        None, None, OK
    ),
    # test expect properties value None
    (
        "Instance with some properties with None. Fails because cannot infer"
        "with None and no type",
        dict(
            cls_props=(ID_PROP, STR_PROP, INT_PROP),
            inst_prop_vals={u'ID': 'inst_id', u'STR': None, u'U32': None},
            kwargs={'include_path': False},
            exp_props={u'ID': u'inst_id', u'STR': None, u'U32': None},
        ),
        ValueError, None, OK
    ),
    (
        "Verify instance with same props as class one prop with None value and"
        "typed passes",

        dict(
            cls_props=(ID_PROP, STR_PROP, INT_PROP),
            inst_prop_vals={u'ID': 'inst_id', u'STR': 'blah', u'U32': None},

            kwargs={'include_path': False},
            exp_props={u'ID': u'inst_id', u'STR': "blah",
                       u'U32': CIMProperty(u'U32', None, 'uint32')},
        ),
        None, None, OK
    ),
    # test include_class_origin = True
    (
        "Verify class with one property. include_class_origin=True passes",
        dict(
            cls_props=(ID_PROP, STR_PROP, INT_PROP),
            inst_prop_vals={u'ID': u'inst_id'},
            kwargs={'include_path': False, 'include_class_origin': True,
                    'include_missing_properties': False},
            exp_props={u'ID': CIMProperty(u'ID', u'inst_id', type='string',
                                          class_origin='CIM_Foo')},
        ),
        None, None, OK
    ),
    (
        "Verify same properties in instance & class inc_path=True, "
        "creates new instance with path",
        dict(
            cls_props=(ID_PROP, STR_PROP, INT_PROP),
            inst_prop_vals={u'ID': u'inst_id', u'STR': u'str_val',
                            u'U32': Uint32(3)},
            kwargs={'include_path': True},
            exp_props={u'ID': u'inst_id', u'STR': u'str_val',
                       u'U32': Uint32(3)},
        ),
        None, None, OK
    ),
    (
        "Verify instance with missing id property in instance flags: inc path, "
        "include_missing_properties=False fails.",
        dict(
            cls_props=(ID_PROP, STR_PROP, INT_PROP),
            inst_prop_vals={u'STR': u'str_val', u'U32': Uint32(99999)},
            kwargs={'include_path': True,
                    'include_missing_properties': False},
            exp_props={u'ID': u'inst_id', u'STR': u'str_val',
                       u'U32': Uint32(99999)},
        ),
        ValueError, None, OK
    ),
    (
        "Instance with missing id property in instance flags: inc path, "
        " Test fails, key propety value None",
        dict(
            cls_props=(ID_PROP, STR_PROP, INT_PROP),
            inst_prop_vals={u'STR': u'str_val', u'U32': Uint32(99999)},
            kwargs={'include_path': True},
            exp_props={u'ID': u'inst_id', u'STR': u'str_val',
                       u'U32': Uint32(99999)},
        ),
        ValueError, None, OK
    ),
    (
        "Instance with property in instance but not in class fails",
        dict(
            cls_props=(ID_PROP, STR_PROP, INT_PROP),
            inst_prop_vals={u'ID': u'inst_id', u'STR': u'str_val',
                            u'U32': Uint32(3),
                            u'BLAH': Uint64(9)},
            kwargs={},
            exp_props={u'ID': 'inst_id', u'STR': u'str_val',
                       u'U32': Uint32(3)},
        ),
        ValueError, None, OK
    ),
    (
        "Instance with property type different than class fails",
        dict(
            cls_props=(ID_PROP, STR_PROP, INT_PROP),
            inst_prop_vals={u'ID': u'inst_id', u'STR': u'str_val',
                            u'U32': u'blah'},
            kwargs={},
            exp_props={u'ID': u'inst_id', u'STR': u'str_val',
                       u'U32': Uint32(3)},
        ),
        ValueError, None, OK
    ),
    (
        "Class with with valid array property passes test",
        dict(
            cls_props=(ID_PROP, STR_PROP, INT_PROP, ARR_PROP),
            inst_prop_vals={u'ID': u'inst_id', u'STR': u'str_val',
                            u'U32': Uint32(3), u'A32': [Uint32(3),
                                                        Uint32(9999)]},
            kwargs={},
            exp_props={u'ID': u'inst_id', u'STR': u'str_val',
                       u'U32': Uint32(3), u'A32': [Uint32(3), Uint32(9999)]},
        ),
        None, None, OK
    ),
    (
        "Class with with array property but non-array in instance fails",
        dict(
            cls_props=(ID_PROP, STR_PROP, INT_PROP, ARR_PROP),
            inst_prop_vals={u'ID': u'inst_id', u'STR': u'str_val',
                            u'U32': Uint32(3), u'A32': Uint32(3)},
            kwargs={},
            exp_props={u'ID': u'inst_id', u'STR': u'str_val',
                       u'U32': Uint32(3), u'A32': Uint32(3)},
        ),
        ValueError, None, OK
    ),
    (
        "Same properties in instance and class. Default params witn namespace",
        dict(
            cls_props=(ID_PROP, STR_PROP, INT_PROP),
            inst_prop_vals={u'ID': u'inst_id', u'STR': u'str_val',
                            u'U32': Uint32(3)},
            kwargs={'namespace': 'root/blah', 'include_path': True},
            exp_props={u'ID': u'inst_id', u'STR': u'str_val',
                       u'U32': Uint32(3)},
        ),
        None, None, OK
    ),

    # Tests with defaults prop values in class
    (
        "Class with default props. No props in instance. Fails because "
        "include_missing_properties not set. No properties set in instance",
        dict(
            cls_props=(ID_PROP_D, STR_PROP_D, INT_PROP_D),
            inst_prop_vals={},
            kwargs={'include_path': True,
                    'include_missing_properties': False},
            exp_props={u'ID': u'cls_id', u'STR': u'cls_str', u'U32': Uint32(4)},
        ),
        ValueError, None, OK
    ),
    (
        "Class with default props. No props in instance passes because "
        "include_missing_properties is set",
        dict(
            cls_props=(ID_PROP_D, STR_PROP_D, INT_PROP_D),
            inst_prop_vals={},
            kwargs={'include_path': True,
                    'include_missing_properties': True},
            exp_props={u'ID': u'cls_id', u'STR': u'cls_str', u'U32': Uint32(4)},
        ),
        None, None, OK
    ),
    (
        "Class default props. All props in instance. ",
        dict(
            cls_props=(ID_PROP_D, STR_PROP_D, INT_PROP_D),
            inst_prop_vals={'ID': 'inst_id', 'STR': 'str_val',
                            'U32': Uint32(3), 'A32': Uint32(3)},
            kwargs={'include_path': True,
                    'include_missing_properties': False},
            exp_props={u'ID': u'inst_id', u'STR': u'str_val',
                       u'U32': Uint32(3)},
        ),
        ValueError, None, OK
    ),
    (
        "Verify no input properties with include_path True and "
        "include_missing_properties False returns empty instance",
        dict(
            cls_props=(ID_PROP_D, STR_PROP_D, INT_PROP_D),
            inst_prop_vals={},
            kwargs={'include_path': False,
                    'include_missing_properties': False},
            exp_props={},
        ),
        None, None, OK
    ),
    (
        "Verify invalid_type for property_values cause exception",
        dict(
            cls_props=(ID_PROP_D, STR_PROP_D, INT_PROP_D),
            inst_prop_vals='blah',
            kwargs={'include_path': False,
                    'include_missing_properties': False},
            exp_props={},
        ),
        TypeError, None, OK
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_CIMINSTANCE_FROMCLASS)
@simplified_test_function
def test_instance_from_class(testcase, cls_props, inst_prop_vals, kwargs,
                             exp_props):
    """
    Test the static method from_class where cls_props defines the
    class properties used to build the class, inst_prop_vals defines the
    property values to be input into the property_values parameter of the
    method being tested, kwargs defines any other arguments for the method
    call, and exp_props defines the properties expected in the created
    instance.
    """
    # Create the test class
    cim_class = CIMClass('CIM_Foo', properties=cls_props)

    # define expected params for call with their defaults for result tests
    include_path = kwargs.get('include_path', True)
    namespace = kwargs.get('namespace', None)
    include_class_origin = kwargs.get('include_class_origin', False)

    # test the method
    act_inst = CIMInstance.from_class(cim_class,
                                      property_values=inst_prop_vals,
                                      **kwargs)

    assert isinstance(exp_props, dict)
    if not isinstance(exp_props, NocaseDict):
        ncd = NocaseDict()
        ncd.update(exp_props)
        exp_props = ncd

    exp_inst = CIMInstance('CIM_Foo', properties=exp_props)

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None

    if include_path:
        exp_inst.path = CIMInstanceName.from_instance(cim_class,
                                                      exp_inst,
                                                      namespace)
        assert act_inst.path
        assert act_inst.path.namespace == namespace
    else:
        assert act_inst.path is None

    for prop in act_inst.properties.values():
        assert isinstance(prop, CIMProperty)
        class_origin = prop.class_origin  # pylint: disable=no-member
        if include_class_origin:
            assert class_origin is not None
        else:
            assert class_origin is None

    assert exp_inst == act_inst


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

    def test_CIMProperty_init_pos_args(self):  # XXX: Merge with succeeds
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
                          tzinfo=MinutesFromUTC(120))
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
            "Verify that bytes name is converted to unicode",
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
            "Verify bytes string without type",
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
            "Verify bytes string with type",
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
            "Verify that bytes reference_class is converted to unicode",
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

        # embedded_object=False tests
        (
            "Verify that embedded_object=False results in None",
            dict(name=u'FooProp', value=u'abc', type='string',
                 embedded_object=False),
            dict(name=u'FooProp', value=u'abc', type=u'string',
                 embedded_object=None),
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
        (
            "Verify that mismatch between is_array False and array_size is "
            "ignored",
            dict(name=u'FooProp', value=u'abc', type=u'string',
                 is_array=False, array_size=2),
            dict(name=u'FooProp', value=u'abc', type=u'string',
                 is_array=False, array_size=2),
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
    def test_CIMProperty_init_succeeds(  # XXX: Migrate to s.tst.fnc.
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
    def test_CIMProperty_init_fails(  # XXX: Merge with succeeds
            self, desc, kwargs, exp_exc_type, condition):
        # pylint: disable=unused-argument
        """All test cases where CIMProperty.__init__() fails."""

        if not condition:
            pytest.skip("Condition for test case not met")

        with pytest.raises(exp_exc_type):

            # The code to be tested
            CIMProperty(**kwargs)


class CIMPropertyCopy(unittest.TestCase, CIMObjectMixin):

    def test_CIMProperty_copy(self):  # XXX: Migrate to pytest

        p = CIMProperty('Spotty', 'Foot')
        c = p.copy()

        self.assertEqual(p, c)

        c.name = '1234'
        c.value = '1234'
        c.qualifiers = {'Key': CIMQualifier('Key', True)}

        self.assert_CIMProperty_attrs(p, 'Spotty', 'Foot', type_='string',
                                      qualifiers={})


class CIMPropertyAttrs(unittest.TestCase, CIMObjectMixin):

    def test_CIMProperty_attrs(self):  # XXX: Migrate to pytest

        # Attributes for single-valued property

        obj = CIMProperty('Spotty', 'Foot')
        self.assert_CIMProperty_attrs(obj, 'Spotty', 'Foot', type_='string')

        # Attributes for array property

        v = [Uint8(x) for x in [1, 2, 3]]
        obj = CIMProperty('Foo', v)
        self.assert_CIMProperty_attrs(obj, 'Foo', v, type_='uint8',
                                      is_array=True)

        # Attributes for property reference

        # This test failed in the pre-0.8.1 implementation, because the
        # reference_class argument was required to be provided for references.
        v = CIMInstanceName('CIM_Bar')
        obj = CIMProperty('Foo', v)
        self.assert_CIMProperty_attrs(obj, 'Foo', v, type_='reference')

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

    def test_CIMProperty_eq(self):  # XXX: Migrate to pytest

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
    def test_CIMProperty_cmp(self):  # XXX: Implement with pytest
        raise AssertionError("test not implemented")


class CIMPropertySort(unittest.TestCase):

    @unimplemented
    def test_CIMProperty_sort(self):  # XXX: Implement with pytest
        raise AssertionError("test not implemented")


TESTCASES_CIMPROPERTY_HASH = [

    # Testcases for CIMProperty.__hash__()

    # Each list item is a testcase tuple with these items:
    # * desc: Short testcase description.
    # * kwargs: Keyword arguments for the test function:
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
    TESTCASES_CIMPROPERTY_HASH)
@simplified_test_function
def test_CIMProperty_hash(testcase,
                          obj1, obj2, exp_hash_equal):
    """
    Test function for CIMProperty.__hash__().
    """

    # The code to be tested
    hash1 = hash(obj1)
    hash2 = hash(obj2)

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None

    # Double check they are different objects
    assert id(obj1) != id(obj2)

    if exp_hash_equal:
        assert hash1 == hash2
    else:
        assert hash1 != hash2


TESTCASES_CIMPROPERTY_STR_REPR = [

    # Testcases for CIMProperty.__repr__(), __str__() / repr(), str()

    # Each list item is a testcase tuple with these items:
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
            value=CIMInstance('CIM_Bar'),
            type='string',
            embedded_object='instance')
    ),
    (
        CIMProperty(
            name='Spotty',
            value=CIMInstance('CIM_Bar'),
            type='string',
            embedded_object='object')
    ),
    (
        CIMProperty(
            name='Spotty',
            value=CIMClass('CIM_Bar'),
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
    TESTCASES_CIMPROPERTY_STR_REPR)
def test_CIMProperty_str(obj):
    """
    Test function for CIMProperty.__str__() / str()
    """

    # The code to be tested
    s = str(obj)

    assert re.match(r'^CIMProperty\(', s)

    exp_name = _format('name={0!A}', obj.name)
    assert exp_name in s

    exp_value = _format('value={0!A}', obj.value)
    assert exp_value in s

    exp_type = _format('type={0!A}', obj.type)
    assert exp_type in s

    exp_reference_class = _format('reference_class={0!A}', obj.reference_class)
    assert exp_reference_class in s

    exp_embedded_object = _format('embedded_object={0!A}', obj.embedded_object)
    assert exp_embedded_object in s

    exp_is_array = _format('is_array={0!A}', obj.is_array)
    assert exp_is_array in s


@pytest.mark.parametrize(
    "obj",
    TESTCASES_CIMPROPERTY_STR_REPR)
def test_CIMProperty_repr(obj):
    """
    Test function for CIMProperty.__repr__() / repr()
    """

    # The code to be tested
    r = repr(obj)

    assert re.match(r'^CIMProperty\(', r)

    exp_name = _format('name={0!A}', obj.name)
    assert exp_name in r

    exp_value = _format('value={0!A}', obj.value)
    assert exp_value in r

    exp_type = _format('type={0!A}', obj.type)
    assert exp_type in r

    exp_reference_class = _format('reference_class={0!A}', obj.reference_class)
    assert exp_reference_class in r

    exp_embedded_object = _format('embedded_object={0!A}', obj.embedded_object)
    assert exp_embedded_object in r

    exp_is_array = _format('is_array={0!A}', obj.is_array)
    assert exp_is_array in r

    exp_array_size = _format('array_size={0!A}', obj.array_size)
    assert exp_array_size in r

    exp_class_origin = _format('class_origin={0!A}', obj.class_origin)
    assert exp_class_origin in r

    exp_propagated = _format('propagated={0!A}', obj.propagated)
    assert exp_propagated in r

    exp_qualifiers = _format('qualifiers={0!A}', obj.qualifiers)
    assert exp_qualifiers in r


TESTCASES_CIMPROPERTY_TOCIMXML = [

    # Testcases for CIMProperty.tocimxml() and tocimxmlstr()

    # Each list item is a testcase tuple with these items:
    # * desc: Short testcase description.
    # * kwargs: Keyword arguments for the test function:
    #   * obj: CIMProperty object to be tested.
    #   * kwargs: Dict of input args for tocimxml() (empty).
    #   * exp_xml_str: Expected CIM-XML string, as a tuple/list of parts.
    # * exp_exc_types: Expected exception type(s), or None.
    # * exp_warn_types: Expected warning type(s), or None.
    # * condition: Boolean condition for testcase to run, or 'pdb' for debugger

    # Tests with name variations
    (
        "Name with ASCII characters, as byte string",
        dict(
            obj=CIMProperty(b'Foo', value=None, type='string'),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY NAME="Foo" TYPE="string"/>',
            )
        ),
        None, None, True
    ),
    (
        "Name with ASCII characters, as unicode string",
        dict(
            obj=CIMProperty(u'Foo', value=None, type='string'),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY NAME="Foo" TYPE="string"/>',
            )
        ),
        None, None, True
    ),
    (
        "Name with non-ASCII UCS-2 characters, as byte string",
        dict(
            obj=CIMProperty(b'Foo\xC3\xA9', value=None, type='string'),
            kwargs=dict(),
            exp_xml_str=(
                u'<PROPERTY NAME="Foo\u00E9" TYPE="string"/>',
            )
        ),
        None, None, True
    ),
    (
        "Name with non-ASCII UCS-2 characters, as unicode string",
        dict(
            obj=CIMProperty(u'Foo\u00E9', value=None, type='string'),
            kwargs=dict(),
            exp_xml_str=(
                u'<PROPERTY NAME="Foo\u00E9" TYPE="string"/>',
            )
        ),
        None, None, True
    ),
    (
        "Name with non-UCS-2 characters, as byte string",
        dict(
            obj=CIMProperty(b'Foo\xF0\x90\x85\x82', value=None, type='string'),
            kwargs=dict(),
            exp_xml_str=(
                u'<PROPERTY NAME="Foo\U00010142" TYPE="string"/>',
            )
        ),
        None, None, True
    ),
    (
        "Name with non-UCS-2 characters, as unicode string",
        dict(
            obj=CIMProperty(u'Foo\U00010142', value=None, type='string'),
            kwargs=dict(),
            exp_xml_str=(
                u'<PROPERTY NAME="Foo\U00010142" TYPE="string"/>',
            )
        ),
        None, None, True
    ),

    # Tests with qualifier variations
    (
        "Two qualifiers and string value",
        dict(
            obj=CIMProperty(
                'Foo', type='string', value='foo',
                qualifiers=[
                    CIMQualifier('Q2', 'bla'),
                    CIMQualifier('Q1', True),
                ],
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY NAME="Foo" TYPE="string">',
                '<QUALIFIER NAME="Q2" TYPE="string">',
                '<VALUE>bla</VALUE>',
                '</QUALIFIER>',
                '<QUALIFIER NAME="Q1" TYPE="boolean">',
                '<VALUE>TRUE</VALUE>',
                '</QUALIFIER>',
                '<VALUE>foo</VALUE>',
                '</PROPERTY>',
            )
        ),
        None, None, True
    ),

    # Scalar properties with boolean type
    (
        "Scalar property with boolean type, value NULL",
        dict(
            obj=CIMProperty(
                'Foo', type='boolean', value=None,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY NAME="Foo" TYPE="boolean"/>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar property with boolean type, value True",
        dict(
            obj=CIMProperty(
                'Foo', type='boolean', value=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY NAME="Foo" TYPE="boolean">',
                '<VALUE>TRUE</VALUE>',
                '</PROPERTY>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar property with boolean type, value False",
        dict(
            obj=CIMProperty(
                'Foo', type='boolean', value=False,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY NAME="Foo" TYPE="boolean">',
                '<VALUE>FALSE</VALUE>',
                '</PROPERTY>',
            )
        ),
        None, None, True
    ),

    # Scalar properties with string type
    (
        "Scalar property with string type, value NULL",
        dict(
            obj=CIMProperty(
                'Foo', type='string', value=None,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY NAME="Foo" TYPE="string"/>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar property with string type, value has one entry with ASCII "
        "characters",
        dict(
            obj=CIMProperty(
                'Foo', type='string', value='foo',
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY NAME="Foo" TYPE="string">',
                '<VALUE>foo</VALUE>',
                '</PROPERTY>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar property with string type, value has one entry with non-ASCII "
        "UCS-2 characters",
        dict(
            obj=CIMProperty(
                'Foo', type='string', value=u'foo\u00E9',
            ),
            kwargs=dict(),
            exp_xml_str=(
                u'<PROPERTY NAME="Foo" TYPE="string">',
                u'<VALUE>foo\u00E9</VALUE>',
                u'</PROPERTY>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar property with string type, value has one entry with non-UCS-2 "
        "characters",
        dict(
            obj=CIMProperty(
                'Foo', type='string', value=u'foo\U00010142',
            ),
            kwargs=dict(),
            exp_xml_str=(
                u'<PROPERTY NAME="Foo" TYPE="string">',
                u'<VALUE>foo\U00010142</VALUE>',
                u'</PROPERTY>',
            )
        ),
        None, None, True
    ),

    # Scalar properties with embedded objects/instances
    (
        "Scalar property with embedded instance type containing an instance",
        dict(
            obj=CIMProperty(
                'Foo', type='string',
                value=CIMInstance('CIM_Emb'), embedded_object='instance',
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY EmbeddedObject="instance"',
                ' NAME="Foo" TYPE="string">',
                '<VALUE>',
                '&lt;INSTANCE CLASSNAME=&quot;CIM_Emb&quot;/&gt;',
                '</VALUE>',
                '</PROPERTY>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar property with embedded object type containing an instance",
        dict(
            obj=CIMProperty(
                'Foo', type='string',
                value=CIMInstance('CIM_Emb'), embedded_object='object',
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY EmbeddedObject="object"',
                ' NAME="Foo" TYPE="string">',
                '<VALUE>',
                '&lt;INSTANCE CLASSNAME=&quot;CIM_Emb&quot;/&gt;',
                '</VALUE>',
                '</PROPERTY>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar property with embedded object type containing a class",
        dict(
            obj=CIMProperty(
                'Foo', type='string',
                value=CIMClass('CIM_Emb'), embedded_object='object',
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY EmbeddedObject="object"',
                ' NAME="Foo" TYPE="string">',
                '<VALUE>',
                '&lt;CLASS NAME=&quot;CIM_Emb&quot;/&gt;',
                '</VALUE>',
                '</PROPERTY>',
            )
        ),
        None, None, True
    ),

    # Scalar properties with char16 type
    (
        "Scalar property with char16 type, value NULL",
        dict(
            obj=CIMProperty(
                'Foo', type='char16', value=None,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY NAME="Foo" TYPE="char16"/>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar property with char16 type, value has one entry with an ASCII "
        "character",
        dict(
            obj=CIMProperty(
                'Foo', type='char16', value='f',
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY NAME="Foo" TYPE="char16">',
                '<VALUE>f</VALUE>',
                '</PROPERTY>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar property with char16 type, value has one entry with a "
        "non-ASCII UCS-2 character",
        dict(
            obj=CIMProperty(
                'Foo', type='char16', value=u'\u00E9',
            ),
            kwargs=dict(),
            exp_xml_str=(
                u'<PROPERTY NAME="Foo" TYPE="char16">',
                u'<VALUE>\u00E9</VALUE>',
                u'</PROPERTY>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar property with char16 type, value has one entry with a "
        "non-UCS-2 character (invalid as per DSP0004, but tolerated by pywbem)",
        dict(
            obj=CIMProperty(
                'Foo', type='char16', value=u'\U00010142',
            ),
            kwargs=dict(),
            exp_xml_str=(
                u'<PROPERTY NAME="Foo" TYPE="char16">',
                u'<VALUE>\U00010142</VALUE>',
                u'</PROPERTY>',
            )
        ),
        None, None, True
    ),

    # Scalar properties with uint8 type
    (
        "Scalar property with uint8 type, value NULL",
        dict(
            obj=CIMProperty(
                'Foo', type='uint8', value=None,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY NAME="Foo" TYPE="uint8"/>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar property with uint8 type, value has one entry in range",
        dict(
            obj=CIMProperty(
                'Foo', type='uint8', value=42,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY NAME="Foo" TYPE="uint8">',
                '<VALUE>42</VALUE>',
                '</PROPERTY>',
            )
        ),
        None, None, True
    ),

    # Scalar properties with uint16 type
    (
        "Scalar property with uint16 type, value NULL",
        dict(
            obj=CIMProperty(
                'Foo', type='uint16', value=None,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY NAME="Foo" TYPE="uint16"/>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar property with uint16 type, value has one entry in range",
        dict(
            obj=CIMProperty(
                'Foo', type='uint16', value=1234,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY NAME="Foo" TYPE="uint16">',
                '<VALUE>1234</VALUE>',
                '</PROPERTY>',
            )
        ),
        None, None, True
    ),

    # Scalar properties with uint32 type
    (
        "Scalar property with uint32 type, value NULL",
        dict(
            obj=CIMProperty(
                'Foo', type='uint32', value=None,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY NAME="Foo" TYPE="uint32"/>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar property with uint32 type, value has one entry in range",
        dict(
            obj=CIMProperty(
                'Foo', type='uint32', value=12345678,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY NAME="Foo" TYPE="uint32">',
                '<VALUE>12345678</VALUE>',
                '</PROPERTY>',
            )
        ),
        None, None, True
    ),

    # Scalar properties with uint64 type
    (
        "Scalar property with uint64 type, value NULL",
        dict(
            obj=CIMProperty(
                'Foo', type='uint64', value=None,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY NAME="Foo" TYPE="uint64"/>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar property with uint64 type, value has one entry in range",
        dict(
            obj=CIMProperty(
                'Foo', type='uint64', value=123456789012,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY NAME="Foo" TYPE="uint64">',
                '<VALUE>123456789012</VALUE>',
                '</PROPERTY>',
            )
        ),
        None, None, True
    ),

    # Scalar properties with sint8 type
    (
        "Scalar property with sint8 type, value NULL",
        dict(
            obj=CIMProperty(
                'Foo', type='sint8', value=None,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY NAME="Foo" TYPE="sint8"/>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar property with sint8 type, value has one entry in range",
        dict(
            obj=CIMProperty(
                'Foo', type='sint8', value=-42,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY NAME="Foo" TYPE="sint8">',
                '<VALUE>-42</VALUE>',
                '</PROPERTY>',
            )
        ),
        None, None, True
    ),

    # Scalar properties with sint16 type
    (
        "Scalar property with sint16 type, value NULL",
        dict(
            obj=CIMProperty(
                'Foo', type='sint16', value=None,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY NAME="Foo" TYPE="sint16"/>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar property with sint16 type, value has one entry in range",
        dict(
            obj=CIMProperty(
                'Foo', type='sint16', value=-1234,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY NAME="Foo" TYPE="sint16">',
                '<VALUE>-1234</VALUE>',
                '</PROPERTY>',
            )
        ),
        None, None, True
    ),

    # Scalar properties with sint32 type
    (
        "Scalar property with sint32 type, value NULL",
        dict(
            obj=CIMProperty(
                'Foo', type='sint32', value=None,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY NAME="Foo" TYPE="sint32"/>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar property with sint32 type, value has one entry in range",
        dict(
            obj=CIMProperty(
                'Foo', type='sint32', value=-12345678,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY NAME="Foo" TYPE="sint32">',
                '<VALUE>-12345678</VALUE>',
                '</PROPERTY>',
            )
        ),
        None, None, True
    ),

    # Scalar properties with sint64 type
    (
        "Scalar property with sint64 type, value NULL",
        dict(
            obj=CIMProperty(
                'Foo', type='sint64', value=None,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY NAME="Foo" TYPE="sint64"/>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar property with sint64 type, value has one entry in range",
        dict(
            obj=CIMProperty(
                'Foo', type='sint64', value=-123456789012,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY NAME="Foo" TYPE="sint64">',
                '<VALUE>-123456789012</VALUE>',
                '</PROPERTY>',
            )
        ),
        None, None, True
    ),

    # Scalar properties with real32 type
    (
        "Scalar property with real32 type, value NULL",
        dict(
            obj=CIMProperty(
                'Foo', type='real32', value=None,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY NAME="Foo" TYPE="real32"/>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar property with real32 type, value between 0 and 1",
        dict(
            obj=CIMProperty(
                'Foo', type='real32', value=0.42,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY NAME="Foo" TYPE="real32">',
                '<VALUE>0.42</VALUE>',
                '</PROPERTY>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar property with real32 type, value with max number of "
        "significant digits (11)",
        dict(
            obj=CIMProperty(
                'Foo', type='real32', value=1.2345678901,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY NAME="Foo" TYPE="real32">',
                '<VALUE>1.2345678901</VALUE>',
                '</PROPERTY>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar property with real32 type, value larger 1 without exponent",
        dict(
            obj=CIMProperty(
                'Foo', type='real32', value=42.0,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY NAME="Foo" TYPE="real32">',
                '<VALUE>42.0</VALUE>',
                '</PROPERTY>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar property with real32 type, value with small negative exponent",
        dict(
            obj=CIMProperty(
                'Foo', type='real32', value=-42.0E-3,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY NAME="Foo" TYPE="real32">',
                '<VALUE>-0.042</VALUE>',
                '</PROPERTY>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar property with real32 type, value with small positive exponent",
        dict(
            obj=CIMProperty(
                'Foo', type='real32', value=-42.0E+3,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY NAME="Foo" TYPE="real32">',
                '<VALUE>-42000.0</VALUE>',
                '</PROPERTY>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar property with real32 type, value with large negative exponent",
        dict(
            obj=CIMProperty(
                'Foo', type='real32', value=-42.0E-30,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY NAME="Foo" TYPE="real32">',
                '<VALUE>-4.2E-29</VALUE>',
                '</PROPERTY>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar property with real32 type, value with large positive exponent",
        dict(
            obj=CIMProperty(
                'Foo', type='real32', value=-42.0E+30,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY NAME="Foo" TYPE="real32">',
                '<VALUE>-4.2E+31</VALUE>',
                '</PROPERTY>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar property with real32 type, special value INF",
        dict(
            obj=CIMProperty(
                'Foo', type='real32', value=float('inf'),
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY NAME="Foo" TYPE="real32">',
                '<VALUE>INF</VALUE>',  # must be upper case
                '</PROPERTY>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar property with real32 type, special value -INF",
        dict(
            obj=CIMProperty(
                'Foo', type='real32', value=float('-inf'),
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY NAME="Foo" TYPE="real32">',
                '<VALUE>-INF</VALUE>',  # must be upper case
                '</PROPERTY>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar property with real32 type, special value NaN",
        dict(
            obj=CIMProperty(
                'Foo', type='real32', value=float('nan'),
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY NAME="Foo" TYPE="real32">',
                '<VALUE>NaN</VALUE>',  # must be upper case
                '</PROPERTY>',
            )
        ),
        None, None, True
    ),

    # Scalar properties with real64 type
    (
        "Scalar property with real64 type, value NULL",
        dict(
            obj=CIMProperty(
                'Foo', type='real64', value=None,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY NAME="Foo" TYPE="real64"/>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar property with real64 type, value between 0 and 1",
        dict(
            obj=CIMProperty(
                'Foo', type='real64', value=0.42,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY NAME="Foo" TYPE="real64">',
                '<VALUE>0.42</VALUE>',
                '</PROPERTY>',
            )
        ),
        None, None, False  # py27: 0.41999999999999998
    ),
    (
        "Scalar property with real64 type, value with max number of "
        "significant digits (17)",
        dict(
            obj=CIMProperty(
                'Foo', type='real64', value=1.2345678901234567,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY NAME="Foo" TYPE="real64">',
                '<VALUE>1.2345678901234567</VALUE>',
                '</PROPERTY>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar property with real64 type, value larger 1 without exponent",
        dict(
            obj=CIMProperty(
                'Foo', type='real64', value=42.0,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY NAME="Foo" TYPE="real64">',
                '<VALUE>42.0</VALUE>',
                '</PROPERTY>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar property with real64 type, value with small negative exponent",
        dict(
            obj=CIMProperty(
                'Foo', type='real64', value=-42.0E-3,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY NAME="Foo" TYPE="real64">',
                '<VALUE>-0.042</VALUE>',
                '</PROPERTY>',
            )
        ),
        None, None, False  # py27: -0.042000000000000003
    ),
    (
        "Scalar property with real64 type, value with small positive exponent",
        dict(
            obj=CIMProperty(
                'Foo', type='real64', value=-42.0E+3,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY NAME="Foo" TYPE="real64">',
                '<VALUE>-42000.0</VALUE>',
                '</PROPERTY>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar property with real64 type, value with large negative exponent",
        dict(
            obj=CIMProperty(
                'Foo', type='real64', value=-42.0E-30,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY NAME="Foo" TYPE="real64">',
                '<VALUE>-4.2E-29</VALUE>',
                '</PROPERTY>',
            )
        ),
        None, None, False  # py27: -4.1999999999999998E-29
    ),
    (
        "Scalar property with real64 type, value with large positive exponent",
        dict(
            obj=CIMProperty(
                'Foo', type='real64', value=-42.0E+30,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY NAME="Foo" TYPE="real64">',
                '<VALUE>-4.2E+31</VALUE>',
                '</PROPERTY>',
            )
        ),
        None, None, False  # py27: -4.1999999999999996E+31
    ),
    (
        "Scalar property with real64 type, special value INF",
        dict(
            obj=CIMProperty(
                'Foo', type='real64', value=float('inf'),
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY NAME="Foo" TYPE="real64">',
                '<VALUE>INF</VALUE>',  # must be upper case
                '</PROPERTY>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar property with real64 type, special value -INF",
        dict(
            obj=CIMProperty(
                'Foo', type='real64', value=float('-inf'),
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY NAME="Foo" TYPE="real64">',
                '<VALUE>-INF</VALUE>',  # must be upper case
                '</PROPERTY>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar property with real64 type, special value NaN",
        dict(
            obj=CIMProperty(
                'Foo', type='real64', value=float('nan'),
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY NAME="Foo" TYPE="real64">',
                '<VALUE>NaN</VALUE>',  # must be upper case
                '</PROPERTY>',
            )
        ),
        None, None, True
    ),

    # Scalar properties with datetime type
    (
        "Scalar property with datetime type, value NULL",
        dict(
            obj=CIMProperty(
                'Foo', type='datetime', value=None,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY NAME="Foo" TYPE="datetime"/>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar property with datetime type, point in time value",
        dict(
            obj=CIMProperty(
                'Foo', type='datetime',
                value=datetime(2014, 9, 22, 10, 49, 20, 524789),
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY NAME="Foo" TYPE="datetime">',
                '<VALUE>20140922104920.524789+000</VALUE>',
                '</PROPERTY>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar property with datetime type, interval value",
        dict(
            obj=CIMProperty(
                'Foo', type='datetime',
                value=timedelta(10, 49, 20),
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY NAME="Foo" TYPE="datetime">',
                '<VALUE>00000010000049.000020:000</VALUE>',
                '</PROPERTY>',
            )
        ),
        None, None, True
    ),

    # Scalar properties with reference type
    (
        "Scalar property with reference type, value NULL",
        dict(
            obj=CIMProperty(
                'Foo', type='reference', value=None,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY.REFERENCE NAME="Foo"/>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar property with reference type, classname-only ref value",
        dict(
            obj=CIMProperty(
                'Foo', type='reference',
                value=CIMInstanceName('CIM_Foo'),
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY.REFERENCE NAME="Foo">',
                '<VALUE.REFERENCE>',
                '<INSTANCENAME CLASSNAME="CIM_Foo"/>',
                '</VALUE.REFERENCE>',
                '</PROPERTY.REFERENCE>',
            )
        ),
        None, None, True
    ),

    # Array properties with boolean type
    (
        "Array property with boolean type, value is NULL",
        dict(
            obj=CIMProperty(
                'Foo', type='boolean', value=None,
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY.ARRAY NAME="Foo" TYPE="boolean"/>',
            )
        ),
        None, None, True
    ),
    (
        "Array property with boolean type, value is empty array",
        dict(
            obj=CIMProperty(
                'Foo', type='boolean', value=[],
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY.ARRAY NAME="Foo" TYPE="boolean">',
                '<VALUE.ARRAY/>',
                '</PROPERTY.ARRAY>',
            )
        ),
        None, None, True
    ),
    (
        "Array property with boolean type, value has one entry NULL",
        dict(
            obj=CIMProperty(
                'Foo', type='boolean', value=[None],
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY.ARRAY NAME="Foo" TYPE="boolean">',
                '<VALUE.ARRAY>',
                '<VALUE.NULL/>',
                '</VALUE.ARRAY>',
                '</PROPERTY.ARRAY>',
            )
        ),
        None, None, True
    ),
    (
        "Array property with boolean type, value has one entry True",
        dict(
            obj=CIMProperty(
                'Foo', type='boolean', value=[True],
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY.ARRAY NAME="Foo" TYPE="boolean">',
                '<VALUE.ARRAY>',
                '<VALUE>TRUE</VALUE>',
                '</VALUE.ARRAY>',
                '</PROPERTY.ARRAY>',
            )
        ),
        None, None, True
    ),
    (
        "Array property with boolean type, value has one entry False",
        dict(
            obj=CIMProperty(
                'Foo', type='boolean', value=[False],
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY.ARRAY NAME="Foo" TYPE="boolean">',
                '<VALUE.ARRAY>',
                '<VALUE>FALSE</VALUE>',
                '</VALUE.ARRAY>',
                '</PROPERTY.ARRAY>',
            )
        ),
        None, None, True
    ),

    # Array properties with string type
    (
        "Array property with string type, value is NULL",
        dict(
            obj=CIMProperty(
                'Foo', type='string', value=None,
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY.ARRAY NAME="Foo" TYPE="string"/>',
            )
        ),
        None, None, True
    ),
    (
        "Array property with string type, value is empty array",
        dict(
            obj=CIMProperty(
                'Foo', type='string', value=[],
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY.ARRAY NAME="Foo" TYPE="string">',
                '<VALUE.ARRAY/>',
                '</PROPERTY.ARRAY>',
            )
        ),
        None, None, True
    ),
    (
        "Array property with string type, value has one entry NULL",
        dict(
            obj=CIMProperty(
                'Foo', type='string', value=[None],
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY.ARRAY NAME="Foo" TYPE="string">',
                '<VALUE.ARRAY>',
                '<VALUE.NULL/>',
                '</VALUE.ARRAY>',
                '</PROPERTY.ARRAY>',
            )
        ),
        None, None, True
    ),
    (
        "Array property with string type, value has one entry with ASCII "
        "characters",
        dict(
            obj=CIMProperty(
                'Foo', type='string', value=['foo'],
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY.ARRAY NAME="Foo" TYPE="string">',
                '<VALUE.ARRAY>',
                '<VALUE>foo</VALUE>',
                '</VALUE.ARRAY>',
                '</PROPERTY.ARRAY>',
            )
        ),
        None, None, True
    ),
    (
        "Array property with string type, value has one entry with non-ASCII "
        "UCS-2 chars",
        dict(
            obj=CIMProperty(
                'Foo', type='string', value=[u'foo\u00E9'],
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                u'<PROPERTY.ARRAY NAME="Foo" TYPE="string">',
                u'<VALUE.ARRAY>',
                u'<VALUE>foo\u00E9</VALUE>',
                u'</VALUE.ARRAY>',
                u'</PROPERTY.ARRAY>',
            )
        ),
        None, None, True
    ),
    (
        "Array property with string type, value has one entry with non-UCS-2 "
        "characters",
        dict(
            obj=CIMProperty(
                'Foo', type='string', value=[u'foo\U00010142'],
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                u'<PROPERTY.ARRAY NAME="Foo" TYPE="string">',
                u'<VALUE.ARRAY>',
                u'<VALUE>foo\U00010142</VALUE>',
                u'</VALUE.ARRAY>',
                u'</PROPERTY.ARRAY>',
            )
        ),
        None, None, True
    ),

    # Array properties with embedded objects/instances
    (
        "Array property with embedded instance type, value has one entry that "
        "is an instance",
        dict(
            obj=CIMProperty(
                'Foo', type='string', is_array=True,
                value=[CIMInstance('CIM_Emb')], embedded_object='instance',
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY.ARRAY EmbeddedObject="instance"',
                ' NAME="Foo" TYPE="string">',
                '<VALUE.ARRAY>',
                '<VALUE>',
                '&lt;INSTANCE CLASSNAME=&quot;CIM_Emb&quot;/&gt;',
                '</VALUE>',
                '</VALUE.ARRAY>',
                '</PROPERTY.ARRAY>',
            )
        ),
        None, None, True
    ),
    (
        "Array property with embedded object type, value has one entry that "
        "is an instance",
        dict(
            obj=CIMProperty(
                'Foo', type='string', is_array=True,
                value=[CIMInstance('CIM_Emb')], embedded_object='object',
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY.ARRAY EmbeddedObject="object"',
                ' NAME="Foo" TYPE="string">',
                '<VALUE.ARRAY>',
                '<VALUE>',
                '&lt;INSTANCE CLASSNAME=&quot;CIM_Emb&quot;/&gt;',
                '</VALUE>',
                '</VALUE.ARRAY>',
                '</PROPERTY.ARRAY>',
            )
        ),
        None, None, True
    ),
    (
        "Array property with embedded object type, value has one entry that "
        "is a class",
        dict(
            obj=CIMProperty(
                'Foo', type='string', is_array=True,
                value=[CIMClass('CIM_Emb')], embedded_object='object',
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY.ARRAY EmbeddedObject="object"',
                ' NAME="Foo" TYPE="string">',
                '<VALUE.ARRAY>',
                '<VALUE>',
                '&lt;CLASS NAME=&quot;CIM_Emb&quot;/&gt;',
                '</VALUE>',
                '</VALUE.ARRAY>',
                '</PROPERTY.ARRAY>',
            )
        ),
        None, None, True
    ),

    # Array properties with char16 type
    (
        "Array property with char16 type, value is NULL",
        dict(
            obj=CIMProperty(
                'Foo', type='char16', value=None,
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY.ARRAY NAME="Foo" TYPE="char16"/>',
            )
        ),
        None, None, True
    ),
    (
        "Array property with char16 type, value is empty array",
        dict(
            obj=CIMProperty(
                'Foo', type='char16', value=[],
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY.ARRAY NAME="Foo" TYPE="char16">',
                '<VALUE.ARRAY/>',
                '</PROPERTY.ARRAY>',
            )
        ),
        None, None, True
    ),
    (
        "Array property with char16 type, value has one entry NULL",
        dict(
            obj=CIMProperty(
                'Foo', type='char16', value=[None],
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY.ARRAY NAME="Foo" TYPE="char16">',
                '<VALUE.ARRAY>',
                '<VALUE.NULL/>',
                '</VALUE.ARRAY>',
                '</PROPERTY.ARRAY>',
            )
        ),
        None, None, True
    ),
    (
        "Array property with char16 type, value has one entry with an ASCII "
        "character",
        dict(
            obj=CIMProperty(
                'Foo', type='char16', value=['f'],
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY.ARRAY NAME="Foo" TYPE="char16">',
                '<VALUE.ARRAY>',
                '<VALUE>f</VALUE>',
                '</VALUE.ARRAY>',
                '</PROPERTY.ARRAY>',
            )
        ),
        None, None, True
    ),
    (
        "Array property with char16 type, value has one entry with a "
        "non-ASCII UCS-2 character",
        dict(
            obj=CIMProperty(
                'Foo', type='char16', value=[u'\u00E9'],
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                u'<PROPERTY.ARRAY NAME="Foo" TYPE="char16">',
                u'<VALUE.ARRAY>',
                u'<VALUE>\u00E9</VALUE>',
                u'</VALUE.ARRAY>',
                u'</PROPERTY.ARRAY>',
            )
        ),
        None, None, True
    ),
    (
        "Array property with char16 type, value has one entry with a "
        "non-UCS-2 character (invalid as per DSP0004, but tolerated by pywbem)",
        dict(
            obj=CIMProperty(
                'Foo', type='char16', value=[u'\U00010142'],
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                u'<PROPERTY.ARRAY NAME="Foo" TYPE="char16">',
                u'<VALUE.ARRAY>',
                u'<VALUE>\U00010142</VALUE>',
                u'</VALUE.ARRAY>',
                u'</PROPERTY.ARRAY>',
            )
        ),
        None, None, True
    ),

    # Array properties with uint8 type
    (
        "Array property with uint8 type, value is NULL",
        dict(
            obj=CIMProperty(
                'Foo', type='uint8', value=None,
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY.ARRAY NAME="Foo" TYPE="uint8"/>',
            )
        ),
        None, None, True
    ),
    (
        "Array property with uint8 type, value is empty array",
        dict(
            obj=CIMProperty(
                'Foo', type='uint8', value=[],
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY.ARRAY NAME="Foo" TYPE="uint8">',
                '<VALUE.ARRAY/>',
                '</PROPERTY.ARRAY>',
            )
        ),
        None, None, True
    ),
    (
        "Array property with uint8 type, value has one entry NULL",
        dict(
            obj=CIMProperty(
                'Foo', type='uint8', value=[None],
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY.ARRAY NAME="Foo" TYPE="uint8">',
                '<VALUE.ARRAY>',
                '<VALUE.NULL/>',
                '</VALUE.ARRAY>',
                '</PROPERTY.ARRAY>',
            )
        ),
        None, None, True
    ),
    (
        "Array property with uint8 type, value has one entry in range",
        dict(
            obj=CIMProperty(
                'Foo', type='uint8', value=[42],
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY.ARRAY NAME="Foo" TYPE="uint8">',
                '<VALUE.ARRAY>',
                '<VALUE>42</VALUE>',
                '</VALUE.ARRAY>',
                '</PROPERTY.ARRAY>',
            )
        ),
        None, None, True
    ),

    # Array properties with uint16 type
    (
        "Array property with uint16 type, value is NULL",
        dict(
            obj=CIMProperty(
                'Foo', type='uint16', value=None,
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY.ARRAY NAME="Foo" TYPE="uint16"/>',
            )
        ),
        None, None, True
    ),
    (
        "Array property with uint16 type, value is empty array",
        dict(
            obj=CIMProperty(
                'Foo', type='uint16', value=[],
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY.ARRAY NAME="Foo" TYPE="uint16">',
                '<VALUE.ARRAY/>',
                '</PROPERTY.ARRAY>',
            )
        ),
        None, None, True
    ),
    (
        "Array property with uint16 type, value has one entry NULL",
        dict(
            obj=CIMProperty(
                'Foo', type='uint16', value=[None],
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY.ARRAY NAME="Foo" TYPE="uint16">',
                '<VALUE.ARRAY>',
                '<VALUE.NULL/>',
                '</VALUE.ARRAY>',
                '</PROPERTY.ARRAY>',
            )
        ),
        None, None, True
    ),
    (
        "Array property with uint16 type, value has one entry in range",
        dict(
            obj=CIMProperty(
                'Foo', type='uint16', value=[1234],
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY.ARRAY NAME="Foo" TYPE="uint16">',
                '<VALUE.ARRAY>',
                '<VALUE>1234</VALUE>',
                '</VALUE.ARRAY>',
                '</PROPERTY.ARRAY>',
            )
        ),
        None, None, True
    ),

    # Array properties with uint32 type
    (
        "Array property with uint32 type, value is NULL",
        dict(
            obj=CIMProperty(
                'Foo', type='uint32', value=None,
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY.ARRAY NAME="Foo" TYPE="uint32"/>',
            )
        ),
        None, None, True
    ),
    (
        "Array property with uint32 type, value is empty array",
        dict(
            obj=CIMProperty(
                'Foo', type='uint32', value=[],
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY.ARRAY NAME="Foo" TYPE="uint32">',
                '<VALUE.ARRAY/>',
                '</PROPERTY.ARRAY>',
            )
        ),
        None, None, True
    ),
    (
        "Array property with uint32 type, value has one entry NULL",
        dict(
            obj=CIMProperty(
                'Foo', type='uint32', value=[None],
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY.ARRAY NAME="Foo" TYPE="uint32">',
                '<VALUE.ARRAY>',
                '<VALUE.NULL/>',
                '</VALUE.ARRAY>',
                '</PROPERTY.ARRAY>',
            )
        ),
        None, None, True
    ),
    (
        "Array property with uint32 type, value has one entry in range",
        dict(
            obj=CIMProperty(
                'Foo', type='uint32', value=[12345678],
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY.ARRAY NAME="Foo" TYPE="uint32">',
                '<VALUE.ARRAY>',
                '<VALUE>12345678</VALUE>',
                '</VALUE.ARRAY>',
                '</PROPERTY.ARRAY>',
            )
        ),
        None, None, True
    ),

    # Array properties with uint64 type
    (
        "Array property with uint64 type, value is NULL",
        dict(
            obj=CIMProperty(
                'Foo', type='uint64', value=None,
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY.ARRAY NAME="Foo" TYPE="uint64"/>',
            )
        ),
        None, None, True
    ),
    (
        "Array property with uint64 type, value is empty array",
        dict(
            obj=CIMProperty(
                'Foo', type='uint64', value=[],
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY.ARRAY NAME="Foo" TYPE="uint64">',
                '<VALUE.ARRAY/>',
                '</PROPERTY.ARRAY>',
            )
        ),
        None, None, True
    ),
    (
        "Array property with uint64 type, value has one entry NULL",
        dict(
            obj=CIMProperty(
                'Foo', type='uint64', value=[None],
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY.ARRAY NAME="Foo" TYPE="uint64">',
                '<VALUE.ARRAY>',
                '<VALUE.NULL/>',
                '</VALUE.ARRAY>',
                '</PROPERTY.ARRAY>',
            )
        ),
        None, None, True
    ),
    (
        "Array property with uint64 type, value has one entry in range",
        dict(
            obj=CIMProperty(
                'Foo', type='uint64', value=[123456789012],
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY.ARRAY NAME="Foo" TYPE="uint64">',
                '<VALUE.ARRAY>',
                '<VALUE>123456789012</VALUE>',
                '</VALUE.ARRAY>',
                '</PROPERTY.ARRAY>',
            )
        ),
        None, None, True
    ),

    # Array properties with sint8 type
    (
        "Array property with sint8 type, value is NULL",
        dict(
            obj=CIMProperty(
                'Foo', type='sint8', value=None,
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY.ARRAY NAME="Foo" TYPE="sint8"/>',
            )
        ),
        None, None, True
    ),
    (
        "Array property with sint8 type, value is empty array",
        dict(
            obj=CIMProperty(
                'Foo', type='sint8', value=[],
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY.ARRAY NAME="Foo" TYPE="sint8">',
                '<VALUE.ARRAY/>',
                '</PROPERTY.ARRAY>',
            )
        ),
        None, None, True
    ),
    (
        "Array property with sint8 type, value has one entry NULL",
        dict(
            obj=CIMProperty(
                'Foo', type='sint8', value=[None],
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY.ARRAY NAME="Foo" TYPE="sint8">',
                '<VALUE.ARRAY>',
                '<VALUE.NULL/>',
                '</VALUE.ARRAY>',
                '</PROPERTY.ARRAY>',
            )
        ),
        None, None, True
    ),
    (
        "Array property with sint8 type, value has one entry in range",
        dict(
            obj=CIMProperty(
                'Foo', type='sint8', value=[-42],
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY.ARRAY NAME="Foo" TYPE="sint8">',
                '<VALUE.ARRAY>',
                '<VALUE>-42</VALUE>',
                '</VALUE.ARRAY>',
                '</PROPERTY.ARRAY>',
            )
        ),
        None, None, True
    ),

    # Array properties with sint16 type
    (
        "Array property with sint16 type, value is NULL",
        dict(
            obj=CIMProperty(
                'Foo', type='sint16', value=None,
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY.ARRAY NAME="Foo" TYPE="sint16"/>',
            )
        ),
        None, None, True
    ),
    (
        "Array property with sint16 type, value is empty array",
        dict(
            obj=CIMProperty(
                'Foo', type='sint16', value=[],
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY.ARRAY NAME="Foo" TYPE="sint16">',
                '<VALUE.ARRAY/>',
                '</PROPERTY.ARRAY>',
            )
        ),
        None, None, True
    ),
    (
        "Array property with sint16 type, value has one entry NULL",
        dict(
            obj=CIMProperty(
                'Foo', type='sint16', value=[None],
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY.ARRAY NAME="Foo" TYPE="sint16">',
                '<VALUE.ARRAY>',
                '<VALUE.NULL/>',
                '</VALUE.ARRAY>',
                '</PROPERTY.ARRAY>',
            )
        ),
        None, None, True
    ),
    (
        "Array property with sint16 type, value has one entry in range",
        dict(
            obj=CIMProperty(
                'Foo', type='sint16', value=[-1234],
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY.ARRAY NAME="Foo" TYPE="sint16">',
                '<VALUE.ARRAY>',
                '<VALUE>-1234</VALUE>',
                '</VALUE.ARRAY>',
                '</PROPERTY.ARRAY>',
            )
        ),
        None, None, True
    ),

    # Array properties with sint32 type
    (
        "Array property with sint32 type, value is NULL",
        dict(
            obj=CIMProperty(
                'Foo', type='sint32', value=None,
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY.ARRAY NAME="Foo" TYPE="sint32"/>',
            )
        ),
        None, None, True
    ),
    (
        "Array property with sint32 type, value is empty array",
        dict(
            obj=CIMProperty(
                'Foo', type='sint32', value=[],
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY.ARRAY NAME="Foo" TYPE="sint32">',
                '<VALUE.ARRAY/>',
                '</PROPERTY.ARRAY>',
            )
        ),
        None, None, True
    ),
    (
        "Array property with sint32 type, value has one entry NULL",
        dict(
            obj=CIMProperty(
                'Foo', type='sint32', value=[None],
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY.ARRAY NAME="Foo" TYPE="sint32">',
                '<VALUE.ARRAY>',
                '<VALUE.NULL/>',
                '</VALUE.ARRAY>',
                '</PROPERTY.ARRAY>',
            )
        ),
        None, None, True
    ),
    (
        "Array property with sint32 type, value has one entry in range",
        dict(
            obj=CIMProperty(
                'Foo', type='sint32', value=[-12345678],
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY.ARRAY NAME="Foo" TYPE="sint32">',
                '<VALUE.ARRAY>',
                '<VALUE>-12345678</VALUE>',
                '</VALUE.ARRAY>',
                '</PROPERTY.ARRAY>',
            )
        ),
        None, None, True
    ),

    # Array properties with sint64 type
    (
        "Array property with sint64 type, value is NULL",
        dict(
            obj=CIMProperty(
                'Foo', type='sint64', value=None,
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY.ARRAY NAME="Foo" TYPE="sint64"/>',
            )
        ),
        None, None, True
    ),
    (
        "Array property with sint64 type, value is empty array",
        dict(
            obj=CIMProperty(
                'Foo', type='sint64', value=[],
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY.ARRAY NAME="Foo" TYPE="sint64">',
                '<VALUE.ARRAY/>',
                '</PROPERTY.ARRAY>',
            )
        ),
        None, None, True
    ),
    (
        "Array property with sint64 type, value has one entry NULL",
        dict(
            obj=CIMProperty(
                'Foo', type='sint64', value=[None],
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY.ARRAY NAME="Foo" TYPE="sint64">',
                '<VALUE.ARRAY>',
                '<VALUE.NULL/>',
                '</VALUE.ARRAY>',
                '</PROPERTY.ARRAY>',
            )
        ),
        None, None, True
    ),
    (
        "Array property with sint64 type, value has one entry in range",
        dict(
            obj=CIMProperty(
                'Foo', type='sint64', value=[-123456789012],
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY.ARRAY NAME="Foo" TYPE="sint64">',
                '<VALUE.ARRAY>',
                '<VALUE>-123456789012</VALUE>',
                '</VALUE.ARRAY>',
                '</PROPERTY.ARRAY>',
            )
        ),
        None, None, True
    ),

    # Array properties with real32 type
    (
        "Array property with real32 type, value is NULL",
        dict(
            obj=CIMProperty(
                'Foo', type='real32', value=None,
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY.ARRAY NAME="Foo" TYPE="real32"/>',
            )
        ),
        None, None, True
    ),
    (
        "Array property with real32 type, value is empty array",
        dict(
            obj=CIMProperty(
                'Foo', type='real32', value=[],
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY.ARRAY NAME="Foo" TYPE="real32">',
                '<VALUE.ARRAY/>',
                '</PROPERTY.ARRAY>',
            )
        ),
        None, None, True
    ),
    (
        "Array property with real32 type, value has one entry NULL",
        dict(
            obj=CIMProperty(
                'Foo', type='real32', value=[None],
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY.ARRAY NAME="Foo" TYPE="real32">',
                '<VALUE.ARRAY>',
                '<VALUE.NULL/>',
                '</VALUE.ARRAY>',
                '</PROPERTY.ARRAY>',
            )
        ),
        None, None, True
    ),
    (
        "Array property with real32 type, value has one entry between 0 and 1",
        dict(
            obj=CIMProperty(
                'Foo', type='real32', value=[0.42],
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY.ARRAY NAME="Foo" TYPE="real32">',
                '<VALUE.ARRAY>',
                '<VALUE>0.42</VALUE>',
                '</VALUE.ARRAY>',
                '</PROPERTY.ARRAY>',
            )
        ),
        None, None, True
    ),
    (
        "Array property with real32 type, value has one entry with max number "
        "of significant digits (11)",
        dict(
            obj=CIMProperty(
                'Foo', type='real32', value=[1.2345678901],
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY.ARRAY NAME="Foo" TYPE="real32">',
                '<VALUE.ARRAY>',
                '<VALUE>1.2345678901</VALUE>',
                '</VALUE.ARRAY>',
                '</PROPERTY.ARRAY>',
            )
        ),
        None, None, True
    ),
    (
        "Array property with real32 type, value has one entry larger 1 "
        "without exponent",
        dict(
            obj=CIMProperty(
                'Foo', type='real32', value=[42.0],
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY.ARRAY NAME="Foo" TYPE="real32">',
                '<VALUE.ARRAY>',
                '<VALUE>42.0</VALUE>',
                '</VALUE.ARRAY>',
                '</PROPERTY.ARRAY>',
            )
        ),
        None, None, True
    ),
    (
        "Array property with real32 type, value has one entry with small "
        "negative exponent",
        dict(
            obj=CIMProperty(
                'Foo', type='real32', value=[-42.0E-3],
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY.ARRAY NAME="Foo" TYPE="real32">',
                '<VALUE.ARRAY>',
                '<VALUE>-0.042</VALUE>',
                '</VALUE.ARRAY>',
                '</PROPERTY.ARRAY>',
            )
        ),
        None, None, True
    ),
    (
        "Array property with real32 type, value has one entry with small "
        "positive exponent",
        dict(
            obj=CIMProperty(
                'Foo', type='real32', value=[-42.0E+3],
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY.ARRAY NAME="Foo" TYPE="real32">',
                '<VALUE.ARRAY>',
                '<VALUE>-42000.0</VALUE>',
                '</VALUE.ARRAY>',
                '</PROPERTY.ARRAY>',
            )
        ),
        None, None, True
    ),
    (
        "Array property with real32 type, value has one entry with large "
        "negative exponent",
        dict(
            obj=CIMProperty(
                'Foo', type='real32', value=[-42.0E-30],
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY.ARRAY NAME="Foo" TYPE="real32">',
                '<VALUE.ARRAY>',
                '<VALUE>-4.2E-29</VALUE>',
                '</VALUE.ARRAY>',
                '</PROPERTY.ARRAY>',
            )
        ),
        None, None, True
    ),
    (
        "Array property with real32 type, value has one entry with large "
        "positive exponent",
        dict(
            obj=CIMProperty(
                'Foo', type='real32', value=[-42.0E+30],
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY.ARRAY NAME="Foo" TYPE="real32">',
                '<VALUE.ARRAY>',
                '<VALUE>-4.2E+31</VALUE>',
                '</VALUE.ARRAY>',
                '</PROPERTY.ARRAY>',
            )
        ),
        None, None, True
    ),
    (
        "Array property with real32 type, value has one entry that is special "
        "value INF",
        dict(
            obj=CIMProperty(
                'Foo', type='real32', value=[float('inf')],
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY.ARRAY NAME="Foo" TYPE="real32">',
                '<VALUE.ARRAY>',
                '<VALUE>INF</VALUE>',  # must be upper case
                '</VALUE.ARRAY>',
                '</PROPERTY.ARRAY>',
            )
        ),
        None, None, True
    ),
    (
        "Array property with real32 type, value has one entry that is special "
        "value -INF",
        dict(
            obj=CIMProperty(
                'Foo', type='real32', value=[float('-inf')],
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY.ARRAY NAME="Foo" TYPE="real32">',
                '<VALUE.ARRAY>',
                '<VALUE>-INF</VALUE>',  # must be upper case
                '</VALUE.ARRAY>',
                '</PROPERTY.ARRAY>',
            )
        ),
        None, None, True
    ),
    (
        "Array property with real32 type, value has one entry that is special "
        "value NaN",
        dict(
            obj=CIMProperty(
                'Foo', type='real32', value=[float('nan')],
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY.ARRAY NAME="Foo" TYPE="real32">',
                '<VALUE.ARRAY>',
                '<VALUE>NaN</VALUE>',  # must be upper case
                '</VALUE.ARRAY>',
                '</PROPERTY.ARRAY>',
            )
        ),
        None, None, True
    ),

    # Array properties with real64 type
    (
        "Array property with real64 type, value is NULL",
        dict(
            obj=CIMProperty(
                'Foo', type='real64', value=None,
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY.ARRAY NAME="Foo" TYPE="real64"/>',
            )
        ),
        None, None, True
    ),
    (
        "Array property with real64 type, value is empty array",
        dict(
            obj=CIMProperty(
                'Foo', type='real64', value=[],
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY.ARRAY NAME="Foo" TYPE="real64">',
                '<VALUE.ARRAY/>',
                '</PROPERTY.ARRAY>',
            )
        ),
        None, None, True
    ),
    (
        "Array property with real64 type, value has one entry NULL",
        dict(
            obj=CIMProperty(
                'Foo', type='real64', value=[None],
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY.ARRAY NAME="Foo" TYPE="real64">',
                '<VALUE.ARRAY>',
                '<VALUE.NULL/>',
                '</VALUE.ARRAY>',
                '</PROPERTY.ARRAY>',
            )
        ),
        None, None, True
    ),
    (
        "Array property with real64 type, value has one entry between 0 and 1",
        dict(
            obj=CIMProperty(
                'Foo', type='real64', value=[0.42],
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY.ARRAY NAME="Foo" TYPE="real64">',
                '<VALUE.ARRAY>',
                '<VALUE>0.42</VALUE>',
                '</VALUE.ARRAY>',
                '</PROPERTY.ARRAY>',
            )
        ),
        None, None, False  # py27: 0.41999999999999998
    ),
    (
        "Array property with real64 type, value has one entry with max number "
        "of significant digits (17)",
        dict(
            obj=CIMProperty(
                'Foo', type='real64', value=[1.2345678901234567],
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY.ARRAY NAME="Foo" TYPE="real64">',
                '<VALUE.ARRAY>',
                '<VALUE>1.2345678901234567</VALUE>',
                '</VALUE.ARRAY>',
                '</PROPERTY.ARRAY>',
            )
        ),
        None, None, True
    ),
    (
        "Array property with real64 type, value has one entry larger 1 "
        "without exponent",
        dict(
            obj=CIMProperty(
                'Foo', type='real64', value=[42.0],
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY.ARRAY NAME="Foo" TYPE="real64">',
                '<VALUE.ARRAY>',
                '<VALUE>42.0</VALUE>',
                '</VALUE.ARRAY>',
                '</PROPERTY.ARRAY>',
            )
        ),
        None, None, True
    ),
    (
        "Array property with real64 type, value has one entry with small "
        "negative exponent",
        dict(
            obj=CIMProperty(
                'Foo', type='real64', value=[-42.0E-3],
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY.ARRAY NAME="Foo" TYPE="real64">',
                '<VALUE.ARRAY>',
                '<VALUE>-0.042</VALUE>',
                '</VALUE.ARRAY>',
                '</PROPERTY.ARRAY>',
            )
        ),
        None, None, False  # py27: -0.042000000000000003
    ),
    (
        "Array property with real64 type, value has one entry with small "
        "positive exponent",
        dict(
            obj=CIMProperty(
                'Foo', type='real64', value=[-42.0E+3],
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY.ARRAY NAME="Foo" TYPE="real64">',
                '<VALUE.ARRAY>',
                '<VALUE>-42000.0</VALUE>',
                '</VALUE.ARRAY>',
                '</PROPERTY.ARRAY>',
            )
        ),
        None, None, True
    ),
    (
        "Array property with real64 type, value has one entry with large "
        "negative exponent",
        dict(
            obj=CIMProperty(
                'Foo', type='real64', value=[-42.0E-30],
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY.ARRAY NAME="Foo" TYPE="real64">',
                '<VALUE.ARRAY>',
                '<VALUE>-4.2E-29</VALUE>',
                '</VALUE.ARRAY>',
                '</PROPERTY.ARRAY>',
            )
        ),
        None, None, False  # py27: -4.1999999999999998E-29
    ),
    (
        "Array property with real64 type, value has one entry with large "
        "positive exponent",
        dict(
            obj=CIMProperty(
                'Foo', type='real64', value=[-42.0E+30],
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY.ARRAY NAME="Foo" TYPE="real64">',
                '<VALUE.ARRAY>',
                '<VALUE>-4.2E+31</VALUE>',
                '</VALUE.ARRAY>',
                '</PROPERTY.ARRAY>',
            )
        ),
        None, None, False  # py27: -4.1999999999999996E+31
    ),
    (
        "Array property with real64 type, value has one entry that is special "
        "value INF",
        dict(
            obj=CIMProperty(
                'Foo', type='real64', value=[float('inf')],
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY.ARRAY NAME="Foo" TYPE="real64">',
                '<VALUE.ARRAY>',
                '<VALUE>INF</VALUE>',  # must be upper case
                '</VALUE.ARRAY>',
                '</PROPERTY.ARRAY>',
            )
        ),
        None, None, True
    ),
    (
        "Array property with real64 type, value has one entry that is special "
        "value -INF",
        dict(
            obj=CIMProperty(
                'Foo', type='real64', value=[float('-inf')],
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY.ARRAY NAME="Foo" TYPE="real64">',
                '<VALUE.ARRAY>',
                '<VALUE>-INF</VALUE>',  # must be upper case
                '</VALUE.ARRAY>',
                '</PROPERTY.ARRAY>',
            )
        ),
        None, None, True
    ),
    (
        "Array property with real64 type, value has one entry that is special "
        "value NaN",
        dict(
            obj=CIMProperty(
                'Foo', type='real64', value=[float('nan')],
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY.ARRAY NAME="Foo" TYPE="real64">',
                '<VALUE.ARRAY>',
                '<VALUE>NaN</VALUE>',  # must be upper case
                '</VALUE.ARRAY>',
                '</PROPERTY.ARRAY>',
            )
        ),
        None, None, True
    ),

    # Array properties with datetime type
    (
        "Array property with datetime type, value is NULL",
        dict(
            obj=CIMProperty(
                'Foo', type='datetime', value=None,
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY.ARRAY NAME="Foo" TYPE="datetime"/>',
            )
        ),
        None, None, True
    ),
    (
        "Array property with datetime type, value is empty array",
        dict(
            obj=CIMProperty(
                'Foo', type='datetime', value=[],
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY.ARRAY NAME="Foo" TYPE="datetime">',
                '<VALUE.ARRAY/>',
                '</PROPERTY.ARRAY>',
            )
        ),
        None, None, True
    ),
    (
        "Array property with datetime type, value has one entry NULL",
        dict(
            obj=CIMProperty(
                'Foo', type='datetime', value=[None],
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY.ARRAY NAME="Foo" TYPE="datetime">',
                '<VALUE.ARRAY>',
                '<VALUE.NULL/>',
                '</VALUE.ARRAY>',
                '</PROPERTY.ARRAY>',
            )
        ),
        None, None, True
    ),
    (
        "Array property with datetime type, value has one entry point in time",
        dict(
            obj=CIMProperty(
                'Foo', type='datetime',
                value=[datetime(2014, 9, 22, 10, 49, 20, 524789)],
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY.ARRAY NAME="Foo" TYPE="datetime">',
                '<VALUE.ARRAY>',
                '<VALUE>20140922104920.524789+000</VALUE>',
                '</VALUE.ARRAY>',
                '</PROPERTY.ARRAY>',
            )
        ),
        None, None, True
    ),
    (
        "Array property with datetime type, value has one entry interval",
        dict(
            obj=CIMProperty(
                'Foo', type='datetime',
                value=[timedelta(10, 49, 20)],
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY.ARRAY NAME="Foo" TYPE="datetime">',
                '<VALUE.ARRAY>',
                '<VALUE>00000010000049.000020:000</VALUE>',
                '</VALUE.ARRAY>',
                '</PROPERTY.ARRAY>',
            )
        ),
        None, None, True
    ),

    # Array properties with reference type are not allowed

    # Tests with class_origin, propagated variations
    (
        "Class origin set",
        dict(
            obj=CIMProperty(
                'Foo', type='uint32', value=None, class_origin='CIM_Origin',
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY CLASSORIGIN="CIM_Origin" NAME="Foo" TYPE="uint32"/>',
            )
        ),
        None, None, True
    ),
    (
        "Propagated set to True",
        dict(
            obj=CIMProperty(
                'Foo', type='uint32', value=None, propagated=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY NAME="Foo" PROPAGATED="true" TYPE="uint32"/>',
            )
        ),
        None, None, True
    ),
    (
        "Propagated set to False",
        dict(
            obj=CIMProperty(
                'Foo', type='uint32', value=None, propagated=False,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<PROPERTY NAME="Foo" PROPAGATED="false" TYPE="uint32"/>',
            )
        ),
        None, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_CIMPROPERTY_TOCIMXML)
@simplified_test_function
def test_CIMProperty_tocimxml(testcase,
                              obj, kwargs, exp_xml_str):
    """
    Test function for CIMProperty.tocimxml().
    """

    # The code to be tested
    obj_xml = obj.tocimxml(**kwargs)

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None

    obj_xml_str = obj_xml.toxml()
    exp_xml_str = ''.join(exp_xml_str)
    validate_cim_xml_obj(obj, obj_xml_str, exp_xml_str)


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_CIMPROPERTY_TOCIMXML)
@simplified_test_function
def test_CIMProperty_tocimxmlstr(testcase,
                                 obj, kwargs, exp_xml_str):
    """
    Test function for CIMProperty.tocimxmlstr().
    """

    # The code to be tested
    obj_xml_str = obj.tocimxmlstr(**kwargs)

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None

    assert isinstance(obj_xml_str, six.text_type)

    exp_xml_str = u''.join(exp_xml_str)
    validate_cim_xml_obj(obj, obj_xml_str, exp_xml_str)


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_CIMPROPERTY_TOCIMXML)
@simplified_test_function
def test_CIMProperty_tocimxmlstr_indent_int(
        testcase, obj, kwargs, exp_xml_str):
    """
    Test function for CIMProperty.tocimxmlstr() with indent as integer.
    """

    indent = 4
    indent_str = ' ' * indent

    # The code to be tested
    obj_xml_str = obj.tocimxmlstr(indent=indent, **kwargs)

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None

    obj_xml = obj.tocimxml(**kwargs)  # This is tested elsewhere
    exp_xml_str = obj_xml.toprettyxml(indent=indent_str)

    assert obj_xml_str == exp_xml_str, \
        "{0}.tocimxmlstr(indent={1!r}) returns unexpected CIM-XML string". \
        format(obj.__class__.__name__, indent)


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_CIMPROPERTY_TOCIMXML)
@simplified_test_function
def test_CIMProperty_tocimxmlstr_indent_str(
        testcase, obj, kwargs, exp_xml_str):
    """
    Test function for CIMProperty.tocimxmlstr() with indent as string.
    """

    indent = 4
    indent_str = ' ' * indent

    # The code to be tested
    obj_xml_str = obj.tocimxmlstr(indent=indent_str, **kwargs)

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None

    obj_xml = obj.tocimxml(**kwargs)  # This is tested elsewhere
    exp_xml_str = obj_xml.toprettyxml(indent=indent_str)

    assert obj_xml_str == exp_xml_str, \
        "{0}.tocimxmlstr(indent={1!r}) returns unexpected CIM-XML string". \
        format(obj.__class__.__name__, indent_str)


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
            "instance uint32 array property, empty array",
            CIMProperty(
                name='P1',
                value=list(),
                type='uint32',
                is_array=True,
            ),
            True, 12,
            u"""\
            P1 = { };\n""",
            None, CHECK_0_12_0
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
    def test_CIMProperty_tomof(  # XXX: Migrate to s.tst.fnc.
            self, desc, obj, is_instance, indent, exp_result, exp_warn_type,
            condition):
        # pylint: disable=unused-argument
        """Test function for CIMProperty.tomof()."""

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

    def test_CIMProperty_tomof_fail1(self):  # Merge with normal func
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

    def test_CIMProperty_tomof_success1(self):  # Merge with normal func
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

    def test_CIMQualifier_init_pos_args(self):  # XXX: Merge with succeeds
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
            "Verify that bytes name is converted to unicode",
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
            "Verify that bytes value is converted to unicode and "
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
            "Verify that bytes array value is converted to unicode and "
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
    def test_CIMQualifier_init_succeeds(  # XXX: Migrate to s.tst.fnc.
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
    def test_CIMQualifier_init_fails(  # XXX: Merge with succeeds
            self, desc, kwargs, exp_exc_type, condition):
        # pylint: disable=unused-argument
        """All test cases where CIMQualifier.__init__() fails."""

        if not condition:
            pytest.skip("Condition for test case not met")

        with pytest.raises(exp_exc_type):

            # The code to be tested
            CIMQualifier(**kwargs)


class CIMQualifierCopy(unittest.TestCase):

    def test_CIMQualifier_copy(self):  # XXX: Migrate to pytest

        q = CIMQualifier('Revision', '2.7.0', 'string')
        c = q.copy()

        self.assertEqual(q, c)

        c.name = 'Fooble'
        c.value = 'eep'

        self.assertEqual(q.name, 'Revision')


class CIMQualifierAttrs(unittest.TestCase):
    """Test attributes of CIMQualifier object."""

    def test_CIMQualifier_attrs(self):  # XXX: Migrate to pytest

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

    def test_CIMQualifier_eq(self):  # XXX: Migrate to pytest

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
    def test_CIMQualifier_cmp(self):  # XXX: Implement with pytest
        raise AssertionError("test not implemented")


class CIMQualifierSort(unittest.TestCase):

    @unimplemented
    def test_CIMQualifier_sort(self):  # XXX: Implement with pytest
        raise AssertionError("test not implemented")


TESTCASES_CIMQUALIFIER_HASH = [

    # Testcases for CIMQualifier.__hash__()

    # Each list item is a testcase tuple with these items:
    # * desc: Short testcase description.
    # * kwargs: Keyword arguments for the test function:
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
    TESTCASES_CIMQUALIFIER_HASH)
@simplified_test_function
def test_CIMQualifier_hash(testcase,
                           obj1, obj2, exp_hash_equal):
    """
    Test function for CIMQualifier.__hash__().
    """

    # The code to be tested
    hash1 = hash(obj1)
    hash2 = hash(obj2)

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None

    # Double check they are different objects
    assert id(obj1) != id(obj2)

    if exp_hash_equal:
        assert hash1 == hash2
    else:
        assert hash1 != hash2


TESTCASES_CIMQUALIFIER_STR_REPR = [

    # Testcases for CIMQualifier.__repr__(), __str__() / repr(), str()

    # Each list item is a testcase tuple with these items:
    # * obj: CIMQualifier object to be tested.
    (
        CIMQualifier('Spotty', 'Foot')
    ),
    (
        CIMQualifier('Revision', Real32(2.7))
    ),
    (
        CIMQualifier('RevisionList',
                     [Uint16(1), Uint16(2), Uint16(3)],
                     propagated=False)
    ),
]


@pytest.mark.parametrize(
    "obj",
    TESTCASES_CIMQUALIFIER_STR_REPR)
def test_CIMQualifier_str(obj):
    """
    Test function for CIMQualifier.__str__() / str()
    """

    # The code to be tested
    s = str(obj)

    assert re.match(r'^CIMQualifier\(', s)

    exp_name = _format('name={0!A}', obj.name)
    assert exp_name in s

    exp_value = _format('value={0!A}', obj.value)
    assert exp_value in s

    exp_type = _format('type={0!A}', obj.type)
    assert exp_type in s


@pytest.mark.parametrize(
    "obj",
    TESTCASES_CIMQUALIFIER_STR_REPR)
def test_CIMQualifier_repr(obj):
    """
    Test function for CIMQualifier.__repr__() / repr()
    """

    # The code to be tested
    r = repr(obj)

    assert re.match(r'^CIMQualifier\(', r)

    exp_name = _format('name={0!A}', obj.name)
    assert exp_name in r

    exp_value = _format('value={0!A}', obj.value)
    assert exp_value in r

    exp_type = _format('type={0!A}', obj.type)
    assert exp_type in r

    exp_tosubclass = _format('tosubclass={0!A}', obj.tosubclass)
    assert exp_tosubclass in r

    exp_overridable = _format('overridable={0!A}', obj.overridable)
    assert exp_overridable in r

    exp_translatable = _format('translatable={0!A}', obj.translatable)
    assert exp_translatable in r

    exp_toinstance = _format('toinstance={0!A}', obj.toinstance)
    assert exp_toinstance in r

    exp_propagated = _format('propagated={0!A}', obj.propagated)
    assert exp_propagated in r


TESTCASES_CIMQUALIFIER_TOCIMXML = [

    # Testcases for CIMQualifier.tocimxml() and tocimxmlstr()

    # Each list item is a testcase tuple with these items:
    # * desc: Short testcase description.
    # * kwargs: Keyword arguments for the test function:
    #   * obj: CIMQualifier object to be tested.
    #   * kwargs: Dict of input args for tocimxml() (empty).
    #   * exp_xml_str: Expected CIM-XML string, as a tuple/list of parts.
    # * exp_exc_types: Expected exception type(s), or None.
    # * exp_warn_types: Expected warning type(s), or None.
    # * condition: Boolean condition for testcase to run, or 'pdb' for debugger

    # Tests with name variations
    (
        "Name with ASCII characters, as byte string",
        dict(
            obj=CIMQualifier(b'Foo', value=None, type='string'),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" TYPE="string"/>',
            )
        ),
        None, None, True
    ),
    (
        "Name with ASCII characters, as unicode string",
        dict(
            obj=CIMQualifier(u'Foo', value=None, type='string'),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" TYPE="string"/>',
            )
        ),
        None, None, True
    ),
    (
        "Name with non-ASCII UCS-2 characters, as byte string",
        dict(
            obj=CIMQualifier(b'Foo\xC3\xA9', value=None, type='string'),
            kwargs=dict(),
            exp_xml_str=(
                u'<QUALIFIER NAME="Foo\u00E9" TYPE="string"/>',
            )
        ),
        None, None, True
    ),
    (
        "Name with non-ASCII UCS-2 characters, as unicode string",
        dict(
            obj=CIMQualifier(u'Foo\u00E9', value=None, type='string'),
            kwargs=dict(),
            exp_xml_str=(
                u'<QUALIFIER NAME="Foo\u00E9" TYPE="string"/>',
            )
        ),
        None, None, True
    ),
    (
        "Name with non-UCS-2 characters, as byte string",
        dict(
            obj=CIMQualifier(b'Foo\xF0\x90\x85\x82', value=None, type='string'),
            kwargs=dict(),
            exp_xml_str=(
                u'<QUALIFIER NAME="Foo\U00010142" TYPE="string"/>',
            )
        ),
        None, None, True
    ),
    (
        "Name with non-UCS-2 characters, as unicode string",
        dict(
            obj=CIMQualifier(u'Foo\U00010142', value=None, type='string'),
            kwargs=dict(),
            exp_xml_str=(
                u'<QUALIFIER NAME="Foo\U00010142" TYPE="string"/>',
            )
        ),
        None, None, True
    ),

    # Variations of propagated argument
    (
        "Qualifier with propagated True",
        dict(
            obj=CIMQualifier(
                'Foo', type='boolean', value=None,
                propagated=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" PROPAGATED="true" TYPE="boolean"/>',
            )
        ),
        None, None, True
    ),
    (
        "Qualifier with propagated False",
        dict(
            obj=CIMQualifier(
                'Foo', type='boolean', value=None,
                propagated=False,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" PROPAGATED="false" TYPE="boolean"/>',
            )
        ),
        None, None, True
    ),

    # Variations of overridable argument
    (
        "Qualifier with overridable True",
        dict(
            obj=CIMQualifier(
                'Foo', type='boolean', value=None,
                overridable=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" OVERRIDABLE="true" TYPE="boolean"/>',
            )
        ),
        None, None, True
    ),
    (
        "Qualifier with overridable False",
        dict(
            obj=CIMQualifier(
                'Foo', type='boolean', value=None,
                overridable=False,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" OVERRIDABLE="false" TYPE="boolean"/>',
            )
        ),
        None, None, True
    ),

    # Variations of tosubclass argument
    (
        "Qualifier with tosubclass True",
        dict(
            obj=CIMQualifier(
                'Foo', type='boolean', value=None,
                tosubclass=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" TOSUBCLASS="true" TYPE="boolean"/>',
            )
        ),
        None, None, True
    ),
    (
        "Qualifier with tosubclass False",
        dict(
            obj=CIMQualifier(
                'Foo', type='boolean', value=None,
                tosubclass=False,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" TOSUBCLASS="false" TYPE="boolean"/>',
            )
        ),
        None, None, True
    ),

    # Variations of toinstance argument
    (
        "Qualifier with toinstance True",
        dict(
            obj=CIMQualifier(
                'Foo', type='boolean', value=None,
                toinstance=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" TOINSTANCE="true" TYPE="boolean"/>',
            )
        ),
        None, None, True
    ),
    (
        "Qualifier with toinstance False",
        dict(
            obj=CIMQualifier(
                'Foo', type='boolean', value=None,
                toinstance=False,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" TOINSTANCE="false" TYPE="boolean"/>',
            )
        ),
        None, None, True
    ),

    # Variations of translatable argument
    (
        "Qualifier with translatable True",
        dict(
            obj=CIMQualifier(
                'Foo', type='boolean', value=None,
                translatable=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" TRANSLATABLE="true" TYPE="boolean"/>',
            )
        ),
        None, None, True
    ),
    (
        "Qualifier with translatable False",
        dict(
            obj=CIMQualifier(
                'Foo', type='boolean', value=None,
                translatable=False,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" TRANSLATABLE="false" TYPE="boolean"/>',
            )
        ),
        None, None, True
    ),

    # Scalar qualifiers with boolean type
    (
        "Scalar qualifier with boolean type, value NULL",
        dict(
            obj=CIMQualifier(
                'Foo', type='boolean', value=None,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" TYPE="boolean"/>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar qualifier with boolean type, value True",
        dict(
            obj=CIMQualifier(
                'Foo', type='boolean', value=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" TYPE="boolean">',
                '<VALUE>TRUE</VALUE>',
                '</QUALIFIER>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar qualifier with boolean type, value False",
        dict(
            obj=CIMQualifier(
                'Foo', type='boolean', value=False,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" TYPE="boolean">',
                '<VALUE>FALSE</VALUE>',
                '</QUALIFIER>',
            )
        ),
        None, None, True
    ),

    # Scalar qualifiers with string type
    (
        "Scalar qualifier with string type, value NULL",
        dict(
            obj=CIMQualifier(
                'Foo', type='string', value=None,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" TYPE="string"/>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar qualifier with string type, value has one entry with ASCII "
        "characters",
        dict(
            obj=CIMQualifier(
                'Foo', type='string', value='foo',
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" TYPE="string">',
                '<VALUE>foo</VALUE>',
                '</QUALIFIER>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar qualifier with string type, value has one entry with "
        "non-ASCII UCS-2 characters",
        dict(
            obj=CIMQualifier(
                'Foo', type='string', value=u'foo\u00E9',
            ),
            kwargs=dict(),
            exp_xml_str=(
                u'<QUALIFIER NAME="Foo" TYPE="string">',
                u'<VALUE>foo\u00E9</VALUE>',
                u'</QUALIFIER>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar qualifier with string type, value has one entry with "
        "non-UCS-2 characters",
        dict(
            obj=CIMQualifier(
                'Foo', type='string', value=u'foo\U00010142',
            ),
            kwargs=dict(),
            exp_xml_str=(
                u'<QUALIFIER NAME="Foo" TYPE="string">',
                u'<VALUE>foo\U00010142</VALUE>',
                u'</QUALIFIER>',
            )
        ),
        None, None, True
    ),

    # Scalar qualifiers with char16 type
    (
        "Scalar qualifier with char16 type, value NULL",
        dict(
            obj=CIMQualifier(
                'Foo', type='char16', value=None,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" TYPE="char16"/>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar qualifier with char16 type, value has one entry with an ASCII "
        "character",
        dict(
            obj=CIMQualifier(
                'Foo', type='char16', value='f',
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" TYPE="char16">',
                '<VALUE>f</VALUE>',
                '</QUALIFIER>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar qualifier with char16 type, value has one entry with a "
        "non-ASCII UCS-2 character",
        dict(
            obj=CIMQualifier(
                'Foo', type='char16', value=u'\u00E9',
            ),
            kwargs=dict(),
            exp_xml_str=(
                u'<QUALIFIER NAME="Foo" TYPE="char16">',
                u'<VALUE>\u00E9</VALUE>',
                u'</QUALIFIER>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar qualifier with char16 type, value has one entry with "
        "non-UCS-2 character (invalid as per DSP0004, but tolerated by pywbem)",
        dict(
            obj=CIMQualifier(
                'Foo', type='char16', value=u'\U00010142',
            ),
            kwargs=dict(),
            exp_xml_str=(
                u'<QUALIFIER NAME="Foo" TYPE="char16">',
                u'<VALUE>\U00010142</VALUE>',
                u'</QUALIFIER>',
            )
        ),
        None, None, True
    ),

    # Scalar qualifiers with uint8 type
    (
        "Scalar qualifier with uint8 type, value NULL",
        dict(
            obj=CIMQualifier(
                'Foo', type='uint8', value=None,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" TYPE="uint8"/>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar qualifier with uint8 type, value has one entry in range",
        dict(
            obj=CIMQualifier(
                'Foo', type='uint8', value=42,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" TYPE="uint8">',
                '<VALUE>42</VALUE>',
                '</QUALIFIER>',
            )
        ),
        None, None, True
    ),

    # Scalar qualifiers with uint16 type
    (
        "Scalar qualifier with uint16 type, value NULL",
        dict(
            obj=CIMQualifier(
                'Foo', type='uint16', value=None,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" TYPE="uint16"/>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar qualifier with uint16 type, value has one entry in range",
        dict(
            obj=CIMQualifier(
                'Foo', type='uint16', value=1234,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" TYPE="uint16">',
                '<VALUE>1234</VALUE>',
                '</QUALIFIER>',
            )
        ),
        None, None, True
    ),

    # Scalar qualifiers with uint32 type
    (
        "Scalar qualifier with uint32 type, value NULL",
        dict(
            obj=CIMQualifier(
                'Foo', type='uint32', value=None,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" TYPE="uint32"/>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar qualifier with uint32 type, value has one entry in range",
        dict(
            obj=CIMQualifier(
                'Foo', type='uint32', value=12345678,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" TYPE="uint32">',
                '<VALUE>12345678</VALUE>',
                '</QUALIFIER>',
            )
        ),
        None, None, True
    ),

    # Scalar qualifiers with uint64 type
    (
        "Scalar qualifier with uint64 type, value NULL",
        dict(
            obj=CIMQualifier(
                'Foo', type='uint64', value=None,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" TYPE="uint64"/>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar qualifier with uint64 type, value has one entry in range",
        dict(
            obj=CIMQualifier(
                'Foo', type='uint64', value=123456789012,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" TYPE="uint64">',
                '<VALUE>123456789012</VALUE>',
                '</QUALIFIER>',
            )
        ),
        None, None, True
    ),

    # Scalar qualifiers with sint8 type
    (
        "Scalar qualifier with sint8 type, value NULL",
        dict(
            obj=CIMQualifier(
                'Foo', type='sint8', value=None,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" TYPE="sint8"/>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar qualifier with sint8 type, value has one entry in range",
        dict(
            obj=CIMQualifier(
                'Foo', type='sint8', value=-42,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" TYPE="sint8">',
                '<VALUE>-42</VALUE>',
                '</QUALIFIER>',
            )
        ),
        None, None, True
    ),

    # Scalar qualifiers with sint16 type
    (
        "Scalar qualifier with sint16 type, value NULL",
        dict(
            obj=CIMQualifier(
                'Foo', type='sint16', value=None,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" TYPE="sint16"/>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar qualifier with sint16 type, value has one entry in range",
        dict(
            obj=CIMQualifier(
                'Foo', type='sint16', value=-1234,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" TYPE="sint16">',
                '<VALUE>-1234</VALUE>',
                '</QUALIFIER>',
            )
        ),
        None, None, True
    ),

    # Scalar qualifiers with sint32 type
    (
        "Scalar qualifier with sint32 type, value NULL",
        dict(
            obj=CIMQualifier(
                'Foo', type='sint32', value=None,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" TYPE="sint32"/>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar qualifier with sint32 type, value has one entry in range",
        dict(
            obj=CIMQualifier(
                'Foo', type='sint32', value=-12345678,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" TYPE="sint32">',
                '<VALUE>-12345678</VALUE>',
                '</QUALIFIER>',
            )
        ),
        None, None, True
    ),

    # Scalar qualifiers with sint64 type
    (
        "Scalar qualifier with sint64 type, value NULL",
        dict(
            obj=CIMQualifier(
                'Foo', type='sint64', value=None,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" TYPE="sint64"/>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar qualifier with sint64 type, value has one entry in range",
        dict(
            obj=CIMQualifier(
                'Foo', type='sint64', value=-123456789012,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" TYPE="sint64">',
                '<VALUE>-123456789012</VALUE>',
                '</QUALIFIER>',
            )
        ),
        None, None, True
    ),

    # Scalar qualifiers with real32 type
    (
        "Scalar qualifier with real32 type, value NULL",
        dict(
            obj=CIMQualifier(
                'Foo', type='real32', value=None,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" TYPE="real32"/>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar qualifier with real32 type, value between 0 and 1",
        dict(
            obj=CIMQualifier(
                'Foo', type='real32', value=0.42,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" TYPE="real32">',
                '<VALUE>0.42</VALUE>',
                '</QUALIFIER>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar qualifier with real32 type, value with max number of "
        "significant digits (11)",
        dict(
            obj=CIMQualifier(
                'Foo', type='real32', value=1.2345678901,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" TYPE="real32">',
                '<VALUE>1.2345678901</VALUE>',
                '</QUALIFIER>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar qualifier with real32 type, value larger 1 without exponent",
        dict(
            obj=CIMQualifier(
                'Foo', type='real32', value=42.0,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" TYPE="real32">',
                '<VALUE>42.0</VALUE>',
                '</QUALIFIER>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar qualifier with real32 type, value with small negative exponent",
        dict(
            obj=CIMQualifier(
                'Foo', type='real32', value=-42.0E-3,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" TYPE="real32">',
                '<VALUE>-0.042</VALUE>',
                '</QUALIFIER>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar qualifier with real32 type, value with small positive exponent",
        dict(
            obj=CIMQualifier(
                'Foo', type='real32', value=-42.0E+3,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" TYPE="real32">',
                '<VALUE>-42000.0</VALUE>',
                '</QUALIFIER>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar qualifier with real32 type, value with large negative exponent",
        dict(
            obj=CIMQualifier(
                'Foo', type='real32', value=-42.0E-30,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" TYPE="real32">',
                '<VALUE>-4.2E-29</VALUE>',
                '</QUALIFIER>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar qualifier with real32 type, value with large positive exponent",
        dict(
            obj=CIMQualifier(
                'Foo', type='real32', value=-42.0E+30,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" TYPE="real32">',
                '<VALUE>-4.2E+31</VALUE>',
                '</QUALIFIER>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar qualifier with real32 type, special value INF",
        dict(
            obj=CIMQualifier(
                'Foo', type='real32', value=float('inf'),
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" TYPE="real32">',
                '<VALUE>INF</VALUE>',  # must be upper case
                '</QUALIFIER>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar qualifier with real32 type, special value -INF",
        dict(
            obj=CIMQualifier(
                'Foo', type='real32', value=float('-inf'),
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" TYPE="real32">',
                '<VALUE>-INF</VALUE>',  # must be upper case
                '</QUALIFIER>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar qualifier with real32 type, special value NaN",
        dict(
            obj=CIMQualifier(
                'Foo', type='real32', value=float('nan'),
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" TYPE="real32">',
                '<VALUE>NaN</VALUE>',  # must be upper case
                '</QUALIFIER>',
            )
        ),
        None, None, True
    ),

    # Scalar qualifiers with real64 type
    (
        "Scalar qualifier with real64 type, value NULL",
        dict(
            obj=CIMQualifier(
                'Foo', type='real64', value=None,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" TYPE="real64"/>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar qualifier with real64 type, value between 0 and 1",
        dict(
            obj=CIMQualifier(
                'Foo', type='real64', value=0.42,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" TYPE="real64">',
                '<VALUE>0.42</VALUE>',
                '</QUALIFIER>',
            )
        ),
        None, None, False  # py27: 0.41999999999999998
    ),
    (
        "Scalar qualifier with real64 type, value with max number of "
        "significant digits (17)",
        dict(
            obj=CIMQualifier(
                'Foo', type='real64', value=1.2345678901234567,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" TYPE="real64">',
                '<VALUE>1.2345678901234567</VALUE>',
                '</QUALIFIER>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar qualifier with real64 type, value larger 1 without exponent",
        dict(
            obj=CIMQualifier(
                'Foo', type='real64', value=42.0,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" TYPE="real64">',
                '<VALUE>42.0</VALUE>',
                '</QUALIFIER>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar qualifier with real64 type, value with small negative exponent",
        dict(
            obj=CIMQualifier(
                'Foo', type='real64', value=-42.0E-3,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" TYPE="real64">',
                '<VALUE>-0.042</VALUE>',
                '</QUALIFIER>',
            )
        ),
        None, None, False  # py27: -0.042000000000000003
    ),
    (
        "Scalar qualifier with real64 type, value with small positive exponent",
        dict(
            obj=CIMQualifier(
                'Foo', type='real64', value=-42.0E+3,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" TYPE="real64">',
                '<VALUE>-42000.0</VALUE>',
                '</QUALIFIER>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar qualifier with real64 type, value with large negative exponent",
        dict(
            obj=CIMQualifier(
                'Foo', type='real64', value=-42.0E-30,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" TYPE="real64">',
                '<VALUE>-4.2E-29</VALUE>',
                '</QUALIFIER>',
            )
        ),
        None, None, False  # py27: -4.1999999999999998E-29
    ),
    (
        "Scalar qualifier with real64 type, value with large positive exponent",
        dict(
            obj=CIMQualifier(
                'Foo', type='real64', value=-42.0E+30,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" TYPE="real64">',
                '<VALUE>-4.2E+31</VALUE>',
                '</QUALIFIER>',
            )
        ),
        None, None, False  # py27: -4.1999999999999996E+31
    ),
    (
        "Scalar qualifier with real64 type, special value INF",
        dict(
            obj=CIMQualifier(
                'Foo', type='real64', value=float('inf'),
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" TYPE="real64">',
                '<VALUE>INF</VALUE>',  # must be upper case
                '</QUALIFIER>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar qualifier with real64 type, special value -INF",
        dict(
            obj=CIMQualifier(
                'Foo', type='real64', value=float('-inf'),
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" TYPE="real64">',
                '<VALUE>-INF</VALUE>',  # must be upper case
                '</QUALIFIER>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar qualifier with real64 type, special value NaN",
        dict(
            obj=CIMQualifier(
                'Foo', type='real64', value=float('nan'),
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" TYPE="real64">',
                '<VALUE>NaN</VALUE>',  # must be upper case
                '</QUALIFIER>',
            )
        ),
        None, None, True
    ),

    # Scalar qualifiers with datetime type
    (
        "Scalar qualifier with datetime type, value NULL",
        dict(
            obj=CIMQualifier(
                'Foo', type='datetime', value=None,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" TYPE="datetime"/>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar qualifier with datetime type, point in time value",
        dict(
            obj=CIMQualifier(
                'Foo', type='datetime',
                value=datetime(2014, 9, 22, 10, 49, 20, 524789),
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" TYPE="datetime">',
                '<VALUE>20140922104920.524789+000</VALUE>',
                '</QUALIFIER>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar qualifier with datetime type, interval value",
        dict(
            obj=CIMQualifier(
                'Foo', type='datetime',
                value=timedelta(10, 49, 20),
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" TYPE="datetime">',
                '<VALUE>00000010000049.000020:000</VALUE>',
                '</QUALIFIER>',
            )
        ),
        None, None, True
    ),

    # Qualifiers with reference type are not allowed as per DSP0004

    # Array qualifiers with boolean type
    (
        "Array qualifier with boolean type, value is NULL",
        dict(
            obj=CIMQualifier(
                'Foo', type='boolean', value=None,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" TYPE="boolean"/>',
            )
        ),
        None, None, True
    ),
    (
        "Array qualifier with boolean type, value is empty array",
        dict(
            obj=CIMQualifier(
                'Foo', type='boolean', value=[],
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" TYPE="boolean">',
                '<VALUE.ARRAY/>',
                '</QUALIFIER>',
            )
        ),
        None, None, True
    ),
    (
        "Array qualifier with boolean type, value has one entry NULL",
        dict(
            obj=CIMQualifier(
                'Foo', type='boolean', value=[None],
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" TYPE="boolean">',
                '<VALUE.ARRAY>',
                '<VALUE.NULL/>',
                '</VALUE.ARRAY>',
                '</QUALIFIER>',
            )
        ),
        None, None, True
    ),
    (
        "Array qualifier with boolean type, value has one entry True",
        dict(
            obj=CIMQualifier(
                'Foo', type='boolean', value=[True],
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" TYPE="boolean">',
                '<VALUE.ARRAY>',
                '<VALUE>TRUE</VALUE>',
                '</VALUE.ARRAY>',
                '</QUALIFIER>',
            )
        ),
        None, None, True
    ),
    (
        "Array qualifier with boolean type, value has one entry False",
        dict(
            obj=CIMQualifier(
                'Foo', type='boolean', value=[False],
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" TYPE="boolean">',
                '<VALUE.ARRAY>',
                '<VALUE>FALSE</VALUE>',
                '</VALUE.ARRAY>',
                '</QUALIFIER>',
            )
        ),
        None, None, True
    ),

    # Array qualifiers with string type
    (
        "Array qualifier with string type, value is NULL",
        dict(
            obj=CIMQualifier(
                'Foo', type='string', value=None,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" TYPE="string"/>',
            )
        ),
        None, None, True
    ),
    (
        "Array qualifier with string type, value is empty array",
        dict(
            obj=CIMQualifier(
                'Foo', type='string', value=[],
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" TYPE="string">',
                '<VALUE.ARRAY/>',
                '</QUALIFIER>',
            )
        ),
        None, None, True
    ),
    (
        "Array qualifier with string type, value has one entry NULL",
        dict(
            obj=CIMQualifier(
                'Foo', type='string', value=[None],
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" TYPE="string">',
                '<VALUE.ARRAY>',
                '<VALUE.NULL/>',
                '</VALUE.ARRAY>',
                '</QUALIFIER>',
            )
        ),
        None, None, True
    ),
    (
        "Array qualifier with string type, value has one entry with ASCII "
        "characters",
        dict(
            obj=CIMQualifier(
                'Foo', type='string', value=['foo'],
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" TYPE="string">',
                '<VALUE.ARRAY>',
                '<VALUE>foo</VALUE>',
                '</VALUE.ARRAY>',
                '</QUALIFIER>',
            )
        ),
        None, None, True
    ),
    (
        "Array qualifier with string type, value has one entry with non-ASCII "
        "UCS-2 characters",
        dict(
            obj=CIMQualifier(
                'Foo', type='string', value=[u'foo\u00E9'],
            ),
            kwargs=dict(),
            exp_xml_str=(
                u'<QUALIFIER NAME="Foo" TYPE="string">',
                u'<VALUE.ARRAY>',
                u'<VALUE>foo\u00E9</VALUE>',
                u'</VALUE.ARRAY>',
                u'</QUALIFIER>',
            )
        ),
        None, None, True
    ),
    (
        "Array qualifier with string type, value has one entry with non-UCS-2 "
        "characters",
        dict(
            obj=CIMQualifier(
                'Foo', type='string', value=[u'foo\U00010142'],
            ),
            kwargs=dict(),
            exp_xml_str=(
                u'<QUALIFIER NAME="Foo" TYPE="string">',
                u'<VALUE.ARRAY>',
                u'<VALUE>foo\U00010142</VALUE>',
                u'</VALUE.ARRAY>',
                u'</QUALIFIER>',
            )
        ),
        None, None, True
    ),

    # Array qualifiers with char16 type
    (
        "Array qualifier with char16 type, value is NULL",
        dict(
            obj=CIMQualifier(
                'Foo', type='char16', value=None,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" TYPE="char16"/>',
            )
        ),
        None, None, True
    ),
    (
        "Array qualifier with char16 type, value is empty array",
        dict(
            obj=CIMQualifier(
                'Foo', type='char16', value=[],
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" TYPE="char16">',
                '<VALUE.ARRAY/>',
                '</QUALIFIER>',
            )
        ),
        None, None, True
    ),
    (
        "Array qualifier with char16 type, value has one entry NULL",
        dict(
            obj=CIMQualifier(
                'Foo', type='char16', value=[None],
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" TYPE="char16">',
                '<VALUE.ARRAY>',
                '<VALUE.NULL/>',
                '</VALUE.ARRAY>',
                '</QUALIFIER>',
            )
        ),
        None, None, True
    ),
    (
        "Array qualifier with char16 type, value has one entry with an ASCII "
        "character",
        dict(
            obj=CIMQualifier(
                'Foo', type='char16', value=['f'],
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" TYPE="char16">',
                '<VALUE.ARRAY>',
                '<VALUE>f</VALUE>',
                '</VALUE.ARRAY>',
                '</QUALIFIER>',
            )
        ),
        None, None, True
    ),
    (
        "Array qualifier with char16 type, value has one entry with a "
        "non-ASCII UCS-2 character",
        dict(
            obj=CIMQualifier(
                'Foo', type='char16', value=[u'\u00E9'],
            ),
            kwargs=dict(),
            exp_xml_str=(
                u'<QUALIFIER NAME="Foo" TYPE="char16">',
                u'<VALUE.ARRAY>',
                u'<VALUE>\u00E9</VALUE>',
                u'</VALUE.ARRAY>',
                u'</QUALIFIER>',
            )
        ),
        None, None, True
    ),
    (
        "Array qualifier with char16 type, value has one entry with a "
        "non-UCS-2 character (invalid as per DSP0004, but tolerated by pywbem)",
        dict(
            obj=CIMQualifier(
                'Foo', type='char16', value=[u'\U00010142'],
            ),
            kwargs=dict(),
            exp_xml_str=(
                u'<QUALIFIER NAME="Foo" TYPE="char16">',
                u'<VALUE.ARRAY>',
                u'<VALUE>\U00010142</VALUE>',
                u'</VALUE.ARRAY>',
                u'</QUALIFIER>',
            )
        ),
        None, None, True
    ),

    # Array qualifiers with uint8 type
    (
        "Array qualifier with uint8 type, value is NULL",
        dict(
            obj=CIMQualifier(
                'Foo', type='uint8', value=None,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" TYPE="uint8"/>',
            )
        ),
        None, None, True
    ),
    (
        "Array qualifier with uint8 type, value is empty array",
        dict(
            obj=CIMQualifier(
                'Foo', type='uint8', value=[],
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" TYPE="uint8">',
                '<VALUE.ARRAY/>',
                '</QUALIFIER>',
            )
        ),
        None, None, True
    ),
    (
        "Array qualifier with uint8 type, value has one entry NULL",
        dict(
            obj=CIMQualifier(
                'Foo', type='uint8', value=[None],
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" TYPE="uint8">',
                '<VALUE.ARRAY>',
                '<VALUE.NULL/>',
                '</VALUE.ARRAY>',
                '</QUALIFIER>',
            )
        ),
        None, None, True
    ),
    (
        "Array qualifier with uint8 type, value has one entry in range",
        dict(
            obj=CIMQualifier(
                'Foo', type='uint8', value=[42],
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" TYPE="uint8">',
                '<VALUE.ARRAY>',
                '<VALUE>42</VALUE>',
                '</VALUE.ARRAY>',
                '</QUALIFIER>',
            )
        ),
        None, None, True
    ),

    # Array qualifiers with uint16 type
    (
        "Array qualifier with uint16 type, value is NULL",
        dict(
            obj=CIMQualifier(
                'Foo', type='uint16', value=None,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" TYPE="uint16"/>',
            )
        ),
        None, None, True
    ),
    (
        "Array qualifier with uint16 type, value is empty array",
        dict(
            obj=CIMQualifier(
                'Foo', type='uint16', value=[],
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" TYPE="uint16">',
                '<VALUE.ARRAY/>',
                '</QUALIFIER>',
            )
        ),
        None, None, True
    ),
    (
        "Array qualifier with uint16 type, value has one entry NULL",
        dict(
            obj=CIMQualifier(
                'Foo', type='uint16', value=[None],
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" TYPE="uint16">',
                '<VALUE.ARRAY>',
                '<VALUE.NULL/>',
                '</VALUE.ARRAY>',
                '</QUALIFIER>',
            )
        ),
        None, None, True
    ),
    (
        "Array qualifier with uint16 type, value has one entry in range",
        dict(
            obj=CIMQualifier(
                'Foo', type='uint16', value=[1234],
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" TYPE="uint16">',
                '<VALUE.ARRAY>',
                '<VALUE>1234</VALUE>',
                '</VALUE.ARRAY>',
                '</QUALIFIER>',
            )
        ),
        None, None, True
    ),

    # Array qualifiers with uint32 type
    (
        "Array qualifier with uint32 type, value is NULL",
        dict(
            obj=CIMQualifier(
                'Foo', type='uint32', value=None,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" TYPE="uint32"/>',
            )
        ),
        None, None, True
    ),
    (
        "Array qualifier with uint32 type, value is empty array",
        dict(
            obj=CIMQualifier(
                'Foo', type='uint32', value=[],
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" TYPE="uint32">',
                '<VALUE.ARRAY/>',
                '</QUALIFIER>',
            )
        ),
        None, None, True
    ),
    (
        "Array qualifier with uint32 type, value has one entry NULL",
        dict(
            obj=CIMQualifier(
                'Foo', type='uint32', value=[None],
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" TYPE="uint32">',
                '<VALUE.ARRAY>',
                '<VALUE.NULL/>',
                '</VALUE.ARRAY>',
                '</QUALIFIER>',
            )
        ),
        None, None, True
    ),
    (
        "Array qualifier with uint32 type, value has one entry in range",
        dict(
            obj=CIMQualifier(
                'Foo', type='uint32', value=[12345678],
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" TYPE="uint32">',
                '<VALUE.ARRAY>',
                '<VALUE>12345678</VALUE>',
                '</VALUE.ARRAY>',
                '</QUALIFIER>',
            )
        ),
        None, None, True
    ),

    # Array qualifiers with uint64 type
    (
        "Array qualifier with uint64 type, value is NULL",
        dict(
            obj=CIMQualifier(
                'Foo', type='uint64', value=None,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" TYPE="uint64"/>',
            )
        ),
        None, None, True
    ),
    (
        "Array qualifier with uint64 type, value is empty array",
        dict(
            obj=CIMQualifier(
                'Foo', type='uint64', value=[],
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" TYPE="uint64">',
                '<VALUE.ARRAY/>',
                '</QUALIFIER>',
            )
        ),
        None, None, True
    ),
    (
        "Array qualifier with uint64 type, value has one entry NULL",
        dict(
            obj=CIMQualifier(
                'Foo', type='uint64', value=[None],
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" TYPE="uint64">',
                '<VALUE.ARRAY>',
                '<VALUE.NULL/>',
                '</VALUE.ARRAY>',
                '</QUALIFIER>',
            )
        ),
        None, None, True
    ),
    (
        "Array qualifier with uint64 type, value has one entry in range",
        dict(
            obj=CIMQualifier(
                'Foo', type='uint64', value=[123456789012],
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" TYPE="uint64">',
                '<VALUE.ARRAY>',
                '<VALUE>123456789012</VALUE>',
                '</VALUE.ARRAY>',
                '</QUALIFIER>',
            )
        ),
        None, None, True
    ),

    # Array qualifiers with sint8 type
    (
        "Array qualifier with sint8 type, value is NULL",
        dict(
            obj=CIMQualifier(
                'Foo', type='sint8', value=None,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" TYPE="sint8"/>',
            )
        ),
        None, None, True
    ),
    (
        "Array qualifier with sint8 type, value is empty array",
        dict(
            obj=CIMQualifier(
                'Foo', type='sint8', value=[],
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" TYPE="sint8">',
                '<VALUE.ARRAY/>',
                '</QUALIFIER>',
            )
        ),
        None, None, True
    ),
    (
        "Array qualifier with sint8 type, value has one entry NULL",
        dict(
            obj=CIMQualifier(
                'Foo', type='sint8', value=[None],
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" TYPE="sint8">',
                '<VALUE.ARRAY>',
                '<VALUE.NULL/>',
                '</VALUE.ARRAY>',
                '</QUALIFIER>',
            )
        ),
        None, None, True
    ),
    (
        "Array qualifier with sint8 type, value has one entry in range",
        dict(
            obj=CIMQualifier(
                'Foo', type='sint8', value=[-42],
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" TYPE="sint8">',
                '<VALUE.ARRAY>',
                '<VALUE>-42</VALUE>',
                '</VALUE.ARRAY>',
                '</QUALIFIER>',
            )
        ),
        None, None, True
    ),

    # Array qualifiers with sint16 type
    (
        "Array qualifier with sint16 type, value is NULL",
        dict(
            obj=CIMQualifier(
                'Foo', type='sint16', value=None,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" TYPE="sint16"/>',
            )
        ),
        None, None, True
    ),
    (
        "Array qualifier with sint16 type, value is empty array",
        dict(
            obj=CIMQualifier(
                'Foo', type='sint16', value=[],
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" TYPE="sint16">',
                '<VALUE.ARRAY/>',
                '</QUALIFIER>',
            )
        ),
        None, None, True
    ),
    (
        "Array qualifier with sint16 type, value has one entry NULL",
        dict(
            obj=CIMQualifier(
                'Foo', type='sint16', value=[None],
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" TYPE="sint16">',
                '<VALUE.ARRAY>',
                '<VALUE.NULL/>',
                '</VALUE.ARRAY>',
                '</QUALIFIER>',
            )
        ),
        None, None, True
    ),
    (
        "Array qualifier with sint16 type, value has one entry in range",
        dict(
            obj=CIMQualifier(
                'Foo', type='sint16', value=[-1234],
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" TYPE="sint16">',
                '<VALUE.ARRAY>',
                '<VALUE>-1234</VALUE>',
                '</VALUE.ARRAY>',
                '</QUALIFIER>',
            )
        ),
        None, None, True
    ),

    # Array qualifiers with sint32 type
    (
        "Array qualifier with sint32 type, value is NULL",
        dict(
            obj=CIMQualifier(
                'Foo', type='sint32', value=None,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" TYPE="sint32"/>',
            )
        ),
        None, None, True
    ),
    (
        "Array qualifier with sint32 type, value is empty array",
        dict(
            obj=CIMQualifier(
                'Foo', type='sint32', value=[],
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" TYPE="sint32">',
                '<VALUE.ARRAY/>',
                '</QUALIFIER>',
            )
        ),
        None, None, True
    ),
    (
        "Array qualifier with sint32 type, value has one entry NULL",
        dict(
            obj=CIMQualifier(
                'Foo', type='sint32', value=[None],
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" TYPE="sint32">',
                '<VALUE.ARRAY>',
                '<VALUE.NULL/>',
                '</VALUE.ARRAY>',
                '</QUALIFIER>',
            )
        ),
        None, None, True
    ),
    (
        "Array qualifier with sint32 type, value has one entry in range",
        dict(
            obj=CIMQualifier(
                'Foo', type='sint32', value=[-12345678],
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" TYPE="sint32">',
                '<VALUE.ARRAY>',
                '<VALUE>-12345678</VALUE>',
                '</VALUE.ARRAY>',
                '</QUALIFIER>',
            )
        ),
        None, None, True
    ),

    # Array qualifiers with sint64 type
    (
        "Array qualifier with sint64 type, value is NULL",
        dict(
            obj=CIMQualifier(
                'Foo', type='sint64', value=None,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" TYPE="sint64"/>',
            )
        ),
        None, None, True
    ),
    (
        "Array qualifier with sint64 type, value is empty array",
        dict(
            obj=CIMQualifier(
                'Foo', type='sint64', value=[],
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" TYPE="sint64">',
                '<VALUE.ARRAY/>',
                '</QUALIFIER>',
            )
        ),
        None, None, True
    ),
    (
        "Array qualifier with sint64 type, value has one entry NULL",
        dict(
            obj=CIMQualifier(
                'Foo', type='sint64', value=[None],
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" TYPE="sint64">',
                '<VALUE.ARRAY>',
                '<VALUE.NULL/>',
                '</VALUE.ARRAY>',
                '</QUALIFIER>',
            )
        ),
        None, None, True
    ),
    (
        "Array qualifier with sint64 type, value has one entry in range",
        dict(
            obj=CIMQualifier(
                'Foo', type='sint64', value=[-123456789012],
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" TYPE="sint64">',
                '<VALUE.ARRAY>',
                '<VALUE>-123456789012</VALUE>',
                '</VALUE.ARRAY>',
                '</QUALIFIER>',
            )
        ),
        None, None, True
    ),

    # Array qualifiers with real32 type
    (
        "Array qualifier with real32 type, value is NULL",
        dict(
            obj=CIMQualifier(
                'Foo', type='real32', value=None,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" TYPE="real32"/>',
            )
        ),
        None, None, True
    ),
    (
        "Array qualifier with real32 type, value is empty array",
        dict(
            obj=CIMQualifier(
                'Foo', type='real32', value=[],
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" TYPE="real32">',
                '<VALUE.ARRAY/>',
                '</QUALIFIER>',
            )
        ),
        None, None, True
    ),
    (
        "Array qualifier with real32 type, value has one entry NULL",
        dict(
            obj=CIMQualifier(
                'Foo', type='real32', value=[None],
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" TYPE="real32">',
                '<VALUE.ARRAY>',
                '<VALUE.NULL/>',
                '</VALUE.ARRAY>',
                '</QUALIFIER>',
            )
        ),
        None, None, True
    ),
    (
        "Array qualifier with real32 type, value has one entry between 0 and 1",
        dict(
            obj=CIMQualifier(
                'Foo', type='real32', value=[0.42],
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" TYPE="real32">',
                '<VALUE.ARRAY>',
                '<VALUE>0.42</VALUE>',
                '</VALUE.ARRAY>',
                '</QUALIFIER>',
            )
        ),
        None, None, True
    ),
    (
        "Array qualifier with real32 type, value has one entry with max "
        "number of significant digits (11)",
        dict(
            obj=CIMQualifier(
                'Foo', type='real32', value=[1.2345678901],
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" TYPE="real32">',
                '<VALUE.ARRAY>',
                '<VALUE>1.2345678901</VALUE>',
                '</VALUE.ARRAY>',
                '</QUALIFIER>',
            )
        ),
        None, None, True
    ),
    (
        "Array qualifier with real32 type, value has one entry larger 1 "
        "without exponent",
        dict(
            obj=CIMQualifier(
                'Foo', type='real32', value=[42.0],
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" TYPE="real32">',
                '<VALUE.ARRAY>',
                '<VALUE>42.0</VALUE>',
                '</VALUE.ARRAY>',
                '</QUALIFIER>',
            )
        ),
        None, None, True
    ),
    (
        "Array qualifier with real32 type, value has one entry with small "
        "negative exponent",
        dict(
            obj=CIMQualifier(
                'Foo', type='real32', value=[-42.0E-3],
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" TYPE="real32">',
                '<VALUE.ARRAY>',
                '<VALUE>-0.042</VALUE>',
                '</VALUE.ARRAY>',
                '</QUALIFIER>',
            )
        ),
        None, None, True
    ),
    (
        "Array qualifier with real32 type, value has one entry with small "
        "positive exponent",
        dict(
            obj=CIMQualifier(
                'Foo', type='real32', value=[-42.0E+3],
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" TYPE="real32">',
                '<VALUE.ARRAY>',
                '<VALUE>-42000.0</VALUE>',
                '</VALUE.ARRAY>',
                '</QUALIFIER>',
            )
        ),
        None, None, True
    ),
    (
        "Array qualifier with real32 type, value has one entry with large "
        "negative exponent",
        dict(
            obj=CIMQualifier(
                'Foo', type='real32', value=[-42.0E-30],
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" TYPE="real32">',
                '<VALUE.ARRAY>',
                '<VALUE>-4.2E-29</VALUE>',
                '</VALUE.ARRAY>',
                '</QUALIFIER>',
            )
        ),
        None, None, True
    ),
    (
        "Array qualifier with real32 type, value has one entry with large "
        "positive exponent",
        dict(
            obj=CIMQualifier(
                'Foo', type='real32', value=[-42.0E+30],
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" TYPE="real32">',
                '<VALUE.ARRAY>',
                '<VALUE>-4.2E+31</VALUE>',
                '</VALUE.ARRAY>',
                '</QUALIFIER>',
            )
        ),
        None, None, True
    ),
    (
        "Array qualifier with real32 type, value has one entry that is "
        "special value INF",
        dict(
            obj=CIMQualifier(
                'Foo', type='real32', value=[float('inf')],
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" TYPE="real32">',
                '<VALUE.ARRAY>',
                '<VALUE>INF</VALUE>',  # must be upper case
                '</VALUE.ARRAY>',
                '</QUALIFIER>',
            )
        ),
        None, None, True
    ),
    (
        "Array qualifier with real32 type, value has one entry that is "
        "special value -INF",
        dict(
            obj=CIMQualifier(
                'Foo', type='real32', value=[float('-inf')],
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" TYPE="real32">',
                '<VALUE.ARRAY>',
                '<VALUE>-INF</VALUE>',  # must be upper case
                '</VALUE.ARRAY>',
                '</QUALIFIER>',
            )
        ),
        None, None, True
    ),
    (
        "Array qualifier with real32 type, value has one entry that is "
        "special value NaN",
        dict(
            obj=CIMQualifier(
                'Foo', type='real32', value=[float('nan')],
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" TYPE="real32">',
                '<VALUE.ARRAY>',
                '<VALUE>NaN</VALUE>',  # must be upper case
                '</VALUE.ARRAY>',
                '</QUALIFIER>',
            )
        ),
        None, None, True
    ),

    # Array qualifiers with real64 type
    (
        "Array qualifier with real64 type, value is NULL",
        dict(
            obj=CIMQualifier(
                'Foo', type='real64', value=None,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" TYPE="real64"/>',
            )
        ),
        None, None, True
    ),
    (
        "Array qualifier with real64 type, value is empty array",
        dict(
            obj=CIMQualifier(
                'Foo', type='real64', value=[],
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" TYPE="real64">',
                '<VALUE.ARRAY/>',
                '</QUALIFIER>',
            )
        ),
        None, None, True
    ),
    (
        "Array qualifier with real64 type, value has one entry NULL",
        dict(
            obj=CIMQualifier(
                'Foo', type='real64', value=[None],
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" TYPE="real64">',
                '<VALUE.ARRAY>',
                '<VALUE.NULL/>',
                '</VALUE.ARRAY>',
                '</QUALIFIER>',
            )
        ),
        None, None, True
    ),
    (
        "Array qualifier with real64 type, value has one entry between 0 and 1",
        dict(
            obj=CIMQualifier(
                'Foo', type='real64', value=[0.42],
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" TYPE="real64">',
                '<VALUE.ARRAY>',
                '<VALUE>0.42</VALUE>',
                '</VALUE.ARRAY>',
                '</QUALIFIER>',
            )
        ),
        None, None, False  # py27: 0.41999999999999998
    ),
    (
        "Array qualifier with real64 type, value has one entry with max "
        "number of significant digits (17)",
        dict(
            obj=CIMQualifier(
                'Foo', type='real64', value=[1.2345678901234567],
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" TYPE="real64">',
                '<VALUE.ARRAY>',
                '<VALUE>1.2345678901234567</VALUE>',
                '</VALUE.ARRAY>',
                '</QUALIFIER>',
            )
        ),
        None, None, True
    ),
    (
        "Array qualifier with real64 type, value has one entry larger 1 "
        "without exponent",
        dict(
            obj=CIMQualifier(
                'Foo', type='real64', value=[42.0],
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" TYPE="real64">',
                '<VALUE.ARRAY>',
                '<VALUE>42.0</VALUE>',
                '</VALUE.ARRAY>',
                '</QUALIFIER>',
            )
        ),
        None, None, True
    ),
    (
        "Array qualifier with real64 type, value has one entry with small "
        "negative exponent",
        dict(
            obj=CIMQualifier(
                'Foo', type='real64', value=[-42.0E-3],
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" TYPE="real64">',
                '<VALUE.ARRAY>',
                '<VALUE>-0.042</VALUE>',
                '</VALUE.ARRAY>',
                '</QUALIFIER>',
            )
        ),
        None, None, False  # py27: -0.042000000000000003
    ),
    (
        "Array qualifier with real64 type, value has one entry with small "
        "positive exponent",
        dict(
            obj=CIMQualifier(
                'Foo', type='real64', value=[-42.0E+3],
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" TYPE="real64">',
                '<VALUE.ARRAY>',
                '<VALUE>-42000.0</VALUE>',
                '</VALUE.ARRAY>',
                '</QUALIFIER>',
            )
        ),
        None, None, True
    ),
    (
        "Array qualifier with real64 type, value has one entry with large "
        "negative exponent",
        dict(
            obj=CIMQualifier(
                'Foo', type='real64', value=[-42.0E-30],
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" TYPE="real64">',
                '<VALUE.ARRAY>',
                '<VALUE>-4.2E-29</VALUE>',
                '</VALUE.ARRAY>',
                '</QUALIFIER>',
            )
        ),
        None, None, False  # py27: -4.1999999999999998E-29
    ),
    (
        "Array qualifier with real64 type, value has one entry with large "
        "positive exponent",
        dict(
            obj=CIMQualifier(
                'Foo', type='real64', value=[-42.0E+30],
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" TYPE="real64">',
                '<VALUE.ARRAY>',
                '<VALUE>-4.2E+31</VALUE>',
                '</VALUE.ARRAY>',
                '</QUALIFIER>',
            )
        ),
        None, None, False  # py27: -4.1999999999999996E+31
    ),
    (
        "Array qualifier with real64 type, value has one entry that is "
        "special value INF",
        dict(
            obj=CIMQualifier(
                'Foo', type='real64', value=[float('inf')],
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" TYPE="real64">',
                '<VALUE.ARRAY>',
                '<VALUE>INF</VALUE>',  # must be upper case
                '</VALUE.ARRAY>',
                '</QUALIFIER>',
            )
        ),
        None, None, True
    ),
    (
        "Array qualifier with real64 type, value has one entry that is "
        "special value -INF",
        dict(
            obj=CIMQualifier(
                'Foo', type='real64', value=[float('-inf')],
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" TYPE="real64">',
                '<VALUE.ARRAY>',
                '<VALUE>-INF</VALUE>',  # must be upper case
                '</VALUE.ARRAY>',
                '</QUALIFIER>',
            )
        ),
        None, None, True
    ),
    (
        "Array qualifier with real64 type, value has one entry that is "
        "special value NaN",
        dict(
            obj=CIMQualifier(
                'Foo', type='real64', value=[float('nan')],
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" TYPE="real64">',
                '<VALUE.ARRAY>',
                '<VALUE>NaN</VALUE>',  # must be upper case
                '</VALUE.ARRAY>',
                '</QUALIFIER>',
            )
        ),
        None, None, True
    ),

    # Array qualifiers with datetime type
    (
        "Array qualifier with datetime type, value is NULL",
        dict(
            obj=CIMQualifier(
                'Foo', type='datetime', value=None,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" TYPE="datetime"/>',
            )
        ),
        None, None, True
    ),
    (
        "Array qualifier with datetime type, value is empty array",
        dict(
            obj=CIMQualifier(
                'Foo', type='datetime', value=[],
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" TYPE="datetime">',
                '<VALUE.ARRAY/>',
                '</QUALIFIER>',
            )
        ),
        None, None, True
    ),
    (
        "Array qualifier with datetime type, value has one entry NULL",
        dict(
            obj=CIMQualifier(
                'Foo', type='datetime', value=[None],
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" TYPE="datetime">',
                '<VALUE.ARRAY>',
                '<VALUE.NULL/>',
                '</VALUE.ARRAY>',
                '</QUALIFIER>',
            )
        ),
        None, None, True
    ),
    (
        "Array qualifier with datetime type, value has one entry point in time",
        dict(
            obj=CIMQualifier(
                'Foo', type='datetime',
                value=[datetime(2014, 9, 22, 10, 49, 20, 524789)],
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" TYPE="datetime">',
                '<VALUE.ARRAY>',
                '<VALUE>20140922104920.524789+000</VALUE>',
                '</VALUE.ARRAY>',
                '</QUALIFIER>',
            )
        ),
        None, None, True
    ),
    (
        "Array qualifier with datetime type, value has one entry interval",
        dict(
            obj=CIMQualifier(
                'Foo', type='datetime',
                value=[timedelta(10, 49, 20)],
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER NAME="Foo" TYPE="datetime">',
                '<VALUE.ARRAY>',
                '<VALUE>00000010000049.000020:000</VALUE>',
                '</VALUE.ARRAY>',
                '</QUALIFIER>',
            )
        ),
        None, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_CIMQUALIFIER_TOCIMXML)
@simplified_test_function
def test_CIMQualifier_tocimxml(testcase,
                               obj, kwargs, exp_xml_str):
    """
    Test function for CIMQualifier.tocimxml().
    """

    # The code to be tested
    obj_xml = obj.tocimxml(**kwargs)

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None

    obj_xml_str = obj_xml.toxml()
    exp_xml_str = ''.join(exp_xml_str)
    validate_cim_xml_obj(obj, obj_xml_str, exp_xml_str)


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_CIMQUALIFIER_TOCIMXML)
@simplified_test_function
def test_CIMQualifier_tocimxmlstr(testcase,
                                  obj, kwargs, exp_xml_str):
    """
    Test function for CIMQualifier.tocimxmlstr().
    """

    # The code to be tested
    obj_xml_str = obj.tocimxmlstr(**kwargs)

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None

    assert isinstance(obj_xml_str, six.text_type)

    exp_xml_str = ''.join(exp_xml_str)
    validate_cim_xml_obj(obj, obj_xml_str, exp_xml_str)


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_CIMQUALIFIER_TOCIMXML)
@simplified_test_function
def test_CIMQualifier_tocimxmlstr_indent_int(
        testcase, obj, kwargs, exp_xml_str):
    """
    Test function for CIMQualifier.tocimxmlstr() with indent as integer.
    """

    indent = 4
    indent_str = ' ' * indent

    # The code to be tested
    obj_xml_str = obj.tocimxmlstr(indent=indent, **kwargs)

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None

    obj_xml = obj.tocimxml(**kwargs)  # This is tested elsewhere
    exp_xml_str = obj_xml.toprettyxml(indent=indent_str)

    assert obj_xml_str == exp_xml_str, \
        "{0}.tocimxmlstr(indent={1!r}) returns unexpected CIM-XML string". \
        format(obj.__class__.__name__, indent)


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_CIMQUALIFIER_TOCIMXML)
@simplified_test_function
def test_CIMQualifier_tocimxmlstr_indent_str(
        testcase, obj, kwargs, exp_xml_str):
    """
    Test function for CIMQualifier.tocimxmlstr() with indent as string.
    """

    indent = 4
    indent_str = ' ' * indent

    # The code to be tested
    obj_xml_str = obj.tocimxmlstr(indent=indent_str, **kwargs)

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None

    obj_xml = obj.tocimxml(**kwargs)  # This is tested elsewhere
    exp_xml_str = obj_xml.toprettyxml(indent=indent_str)

    assert obj_xml_str == exp_xml_str, \
        "{0}.tocimxmlstr(indent={1!r}) returns unexpected CIM-XML string". \
        format(obj.__class__.__name__, indent_str)


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
            "string array that is empty",
            CIMQualifier(
                name='Q1',
                value=[],
                type='string',
            ),
            12,
            u"""Q1 { }""",
            None, CHECK_0_12_0
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
    def test_CIMQualifier_tomof(  # XXX: Migrate to s.tst.fnc.
            self, desc, obj, indent, exp_result, exp_warn_type, condition):
        # pylint: disable=unused-argument
        """Test function for CIMQualifier.tomof()."""

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

    def test_CIMClassName_init_pos_args(self):  # XXX: Merge with succeeds
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
            "Verify that bytes classname is converted to unicode",
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
            "Verify that bytes namespace is converted to unicode",
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
            "Verify that bytes host is converted to unicode",
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
    def test_CIMClassName_init_succeeds(  # XXX: Migrate to s.tst.fnc.
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
    def test_CIMClassName_init_fails(  # XXX: Merge with succeeds
            self, desc, kwargs, exp_exc_type, condition):
        # pylint: disable=unused-argument
        """All test cases where CIMClassName.__init__() fails."""

        if not condition:
            pytest.skip("Condition for test case not met")

        with pytest.raises(exp_exc_type):

            # The code to be tested
            CIMClassName(**kwargs)


class CIMClassNameCopy(unittest.TestCase):

    def test_CIMClassName_copyl(self):  # XXX: Migrate to pytest

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

    def test_CIMClassName_attrs(self):  # XXX: Migrate to pytest

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

    def test_CIMClassName_eq(self):  # XXX: Migrate to pytest

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


TESTCASES_CIMCLASSNAME_HASH = [

    # Testcases for CIMClassName.__hash__()

    # Each list item is a testcase tuple with these items:
    # * desc: Short testcase description.
    # * kwargs: Keyword arguments for the test function:
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
    TESTCASES_CIMCLASSNAME_HASH)
@simplified_test_function
def test_CIMClassName_hash(testcase,
                           obj1, obj2, exp_hash_equal):
    """
    Test function for CIMClassName.__hash__().
    """

    # The code to be tested
    hash1 = hash(obj1)
    hash2 = hash(obj2)

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None

    # Double check they are different objects
    assert id(obj1) != id(obj2)

    if exp_hash_equal:
        assert hash1 == hash2
    else:
        assert hash1 != hash2


TESTCASES_CIMCLASSNAME_REPR = [

    # Testcases for CIMClassName.__repr__() / repr()
    # Note: CIMClassName.__str__() is tested along with to_wbem_uri()

    # Each list item is a testcase tuple with these items:
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
    TESTCASES_CIMCLASSNAME_REPR)
def test_CIMClassName_repr(obj):
    """
    Test function for CIMClassName.__repr__() / repr()

    Note: CIMClassName.__str__() is tested along with to_wbem_uri()
    """

    # The code to be tested
    r = repr(obj)

    assert re.match(r'^CIMClassName\(', r)

    exp_classname = _format('classname={0!A}', obj.classname)
    assert exp_classname in r

    exp_namespace = _format('namespace={0!A}', obj.namespace)
    assert exp_namespace in r

    exp_host = _format('host={0!A}', obj.host)
    assert exp_host in r


TESTCASES_CIMCLASSNAME_TOCIMXML = [

    # Testcases for CIMClassName.tocimxml() and tocimxmlstr()

    # Each list item is a testcase tuple with these items:
    # * desc: Short testcase description.
    # * kwargs: Keyword arguments for the test function:
    #   * obj: CIMClassName object to be tested.
    #   * kwargs: Dict of input args for tocimxml().
    #   * exp_xml_str: Expected CIM-XML string, as a tuple/list of parts.
    # * exp_exc_types: Expected exception type(s), or None.
    # * exp_warn_types: Expected warning type(s), or None.
    # * condition: Boolean condition for testcase to run, or 'pdb' for debugger

    # Classname-only tests
    (
        "Classname only, with implied default args",
        dict(
            obj=CIMClassName('CIM_Foo'),
            kwargs=dict(),
            exp_xml_str=(
                '<CLASSNAME NAME="CIM_Foo"/>',
            )
        ),
        None, None, True
    ),
    (
        "Classname only, with specified default args",
        dict(
            obj=CIMClassName('CIM_Foo'),
            kwargs=dict(
                ignore_host=False,
                ignore_namespace=False,
            ),
            exp_xml_str=(
                '<CLASSNAME NAME="CIM_Foo"/>',
            )
        ),
        None, None, True
    ),
    (
        "Classname only, with non-default args: ignore_host=True",
        dict(
            obj=CIMClassName('CIM_Foo'),
            kwargs=dict(
                ignore_host=True,
            ),
            exp_xml_str=(
                '<CLASSNAME NAME="CIM_Foo"/>',
            )
        ),
        None, None, True
    ),
    (
        "Classname only, with non-default args: ignore_namespace=True",
        dict(
            obj=CIMClassName('CIM_Foo'),
            kwargs=dict(
                ignore_namespace=True,
            ),
            exp_xml_str=(
                '<CLASSNAME NAME="CIM_Foo"/>',
            )
        ),
        None, None, True
    ),

    # Classname with namespace tests
    (
        "Classname with namespace, with implied default args",
        dict(
            obj=CIMClassName(
                'CIM_Foo',
                namespace='root/cimv2',
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<LOCALCLASSPATH>',
                '<LOCALNAMESPACEPATH>',
                '<NAMESPACE NAME="root"/>',
                '<NAMESPACE NAME="cimv2"/>',
                '</LOCALNAMESPACEPATH>',
                '<CLASSNAME NAME="CIM_Foo"/>',
                '</LOCALCLASSPATH>',
            )
        ),
        None, None, True
    ),
    (
        "Classname with namespace, with specified default args",
        dict(
            obj=CIMClassName(
                'CIM_Foo',
                namespace='root/cimv2',
            ),
            kwargs=dict(
                ignore_host=False,
                ignore_namespace=False,
            ),
            exp_xml_str=(
                '<LOCALCLASSPATH>',
                '<LOCALNAMESPACEPATH>',
                '<NAMESPACE NAME="root"/>',
                '<NAMESPACE NAME="cimv2"/>',
                '</LOCALNAMESPACEPATH>',
                '<CLASSNAME NAME="CIM_Foo"/>',
                '</LOCALCLASSPATH>',
            )
        ),
        None, None, True
    ),
    (
        "Classname with namespace, with non-default: ignore_host=True",
        dict(
            obj=CIMClassName(
                'CIM_Foo',
                namespace='root/cimv2',
            ),
            kwargs=dict(
                ignore_host=True,
            ),
            exp_xml_str=(
                '<LOCALCLASSPATH>',
                '<LOCALNAMESPACEPATH>',
                '<NAMESPACE NAME="root"/>',
                '<NAMESPACE NAME="cimv2"/>',
                '</LOCALNAMESPACEPATH>',
                '<CLASSNAME NAME="CIM_Foo"/>',
                '</LOCALCLASSPATH>',
            )
        ),
        None, None, True
    ),
    (
        "Classname with namespace, with non-def: ignore_namespace=True",
        dict(
            obj=CIMClassName(
                'CIM_Foo',
                namespace='root/cimv2',
            ),
            kwargs=dict(
                ignore_namespace=True,
            ),
            exp_xml_str=(
                '<CLASSNAME NAME="CIM_Foo"/>',
            )
        ),
        None, None, True
    ),

    # Classname with namespace+host tests
    (
        "Classname with namespace+host, with implied default args",
        dict(
            obj=CIMClassName(
                'CIM_Foo',
                namespace='root/cimv2',
                host='woot.com',
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<CLASSPATH>',
                '<NAMESPACEPATH>',
                '<HOST>woot.com</HOST>',
                '<LOCALNAMESPACEPATH>',
                '<NAMESPACE NAME="root"/>',
                '<NAMESPACE NAME="cimv2"/>',
                '</LOCALNAMESPACEPATH>',
                '</NAMESPACEPATH>',
                '<CLASSNAME NAME="CIM_Foo"/>',
                '</CLASSPATH>',
            )
        ),
        None, None, True
    ),
    (
        "Classname with namespace+host, with specified default args",
        dict(
            obj=CIMClassName(
                'CIM_Foo',
                namespace='root/cimv2',
                host='woot.com',
            ),
            kwargs=dict(
                ignore_host=False,
                ignore_namespace=False,
            ),
            exp_xml_str=(
                '<CLASSPATH>',
                '<NAMESPACEPATH>',
                '<HOST>woot.com</HOST>',
                '<LOCALNAMESPACEPATH>',
                '<NAMESPACE NAME="root"/>',
                '<NAMESPACE NAME="cimv2"/>',
                '</LOCALNAMESPACEPATH>',
                '</NAMESPACEPATH>',
                '<CLASSNAME NAME="CIM_Foo"/>',
                '</CLASSPATH>',
            )
        ),
        None, None, True
    ),
    (
        "Classname with namespace+host, with non-default: ignore_host=True",
        dict(
            obj=CIMClassName(
                'CIM_Foo',
                namespace='root/cimv2',
                host='woot.com',
            ),
            kwargs=dict(
                ignore_host=True,
            ),
            exp_xml_str=(
                '<LOCALCLASSPATH>',
                '<LOCALNAMESPACEPATH>',
                '<NAMESPACE NAME="root"/>',
                '<NAMESPACE NAME="cimv2"/>',
                '</LOCALNAMESPACEPATH>',
                '<CLASSNAME NAME="CIM_Foo"/>',
                '</LOCALCLASSPATH>',
            )
        ),
        None, None, True
    ),
    (
        "Classname with namespace+host, with non-def: ignore_namespace=True",
        dict(
            obj=CIMClassName(
                'CIM_Foo',
                namespace='root/cimv2',
                host='woot.com',
            ),
            kwargs=dict(
                ignore_namespace=True,
            ),
            exp_xml_str=(
                '<CLASSNAME NAME="CIM_Foo"/>',
            )
        ),
        None, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_CIMCLASSNAME_TOCIMXML)
@simplified_test_function
def test_CIMClassName_tocimxml(testcase,
                               obj, kwargs, exp_xml_str):
    """
    Test function for CIMClassName.tocimxml().
    """

    # The code to be tested
    obj_xml = obj.tocimxml(**kwargs)

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None

    obj_xml_str = obj_xml.toxml()
    exp_xml_str = ''.join(exp_xml_str)
    validate_cim_xml_obj(obj, obj_xml_str, exp_xml_str)


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_CIMCLASSNAME_TOCIMXML)
@simplified_test_function
def test_CIMClassName_tocimxmlstr(testcase,
                                  obj, kwargs, exp_xml_str):
    """
    Test function for CIMClassName.tocimxmlstr().
    """

    # The code to be tested
    obj_xml_str = obj.tocimxmlstr(**kwargs)

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None

    assert isinstance(obj_xml_str, six.text_type)

    exp_xml_str = ''.join(exp_xml_str)
    validate_cim_xml_obj(obj, obj_xml_str, exp_xml_str)


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_CIMCLASSNAME_TOCIMXML)
@simplified_test_function
def test_CIMClassName_tocimxmlstr_indent_int(
        testcase, obj, kwargs, exp_xml_str):
    """
    Test function for CIMClassName.tocimxmlstr() with indent as integer.
    """

    indent = 4
    indent_str = ' ' * indent

    # The code to be tested
    obj_xml_str = obj.tocimxmlstr(indent=indent, **kwargs)

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None

    obj_xml = obj.tocimxml(**kwargs)  # This is tested elsewhere
    exp_xml_str = obj_xml.toprettyxml(indent=indent_str)

    assert obj_xml_str == exp_xml_str, \
        "{0}.tocimxmlstr(indent={1!r}) returns unexpected CIM-XML string". \
        format(obj.__class__.__name__, indent)


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_CIMCLASSNAME_TOCIMXML)
@simplified_test_function
def test_CIMClassName_tocimxmlstr_indent_str(
        testcase, obj, kwargs, exp_xml_str):
    """
    Test function for CIMClassName.tocimxmlstr() with indent as string.
    """

    indent = 4
    indent_str = ' ' * indent

    # The code to be tested
    obj_xml_str = obj.tocimxmlstr(indent=indent_str, **kwargs)

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None

    obj_xml = obj.tocimxml(**kwargs)  # This is tested elsewhere
    exp_xml_str = obj_xml.toprettyxml(indent=indent_str)

    assert obj_xml_str == exp_xml_str, \
        "{0}.tocimxmlstr(indent={1!r}) returns unexpected CIM-XML string". \
        format(obj.__class__.__name__, indent_str)


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
            "local WBEM URI with only class name (with initial slash+colon)",
            '/:CIM_Foo',
            dict(
                classname=u'CIM_Foo',
                namespace=None,
                host=None),
            None, CHECK_0_12_0
        ),
        (
            "local WBEM URI with only class name (without initial slash)",
            ':CIM_Foo',
            dict(
                classname=u'CIM_Foo',
                namespace=None,
                host=None),
            None, CHECK_0_12_0
        ),
        (
            "local WBEM URI with only class name (without initial slash+colon)",
            'CIM_Foo',
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
    def test_CIMClassName_from_wbem_uri(  # XXX: Migrate to s.tst.fnc.
            self, desc, uri, exp_result, exp_warn_type, condition):
        # pylint: disable=unused-argument
        """Test function for CIMClassName.from_wbem_uri()."""

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
        # * format_: Format for to_wbem_uri(): one of 'standard', 'cimobject',
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
            "all components, cimobject format (host is ignored)",
            dict(
                classname=u'CIM_Foo',
                namespace=u'root/cimv2',
                host=u'10.11.12.13:5989'),
            'cimobject',
            '/root/cimv2:CIM_Foo',
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
        "desc, attrs, format_, exp_result, exp_warn_type, condition",
        testcases)
    def test_CIMClassName_to_wbem_uri_str(  # XXX: Migrate to s.tst.fnc.
            self, desc, format_, attrs, exp_result, exp_warn_type, condition,
            func_name):
        # pylint: disable=unused-argument
        """Test function for CIMClassName.to_wbem_uri() and .__str__()."""

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
            func_kwargs = dict(format=format_)
        if func_name == '__str__':
            if format_ != 'historical':
                pytest.skip("Not testing CIMClassName.__str__() with "
                            "format: %r" % format_)
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

    def test_CIMClass_init_pos_args(self):  # XXX: Merge with succeeds
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
            "Verify that bytes classname is converted to unicode",
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
            "Verify that bytes superclass is converted to unicode",
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
    def test_CIMClass_init_succeeds(  # XXX: Migrate to s.tst.fnc.
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
    def test_CIMClass_init_fails(  # XXX: Merge with succeeds
            self, desc, kwargs, exp_exc_type, condition):
        # pylint: disable=unused-argument
        """All test cases where CIMClass.__init__() fails."""

        if not condition:
            pytest.skip("Condition for test case not met")

        with pytest.raises(exp_exc_type):

            # The code to be tested
            CIMClass(**kwargs)


class CIMClassCopy(unittest.TestCase):

    def test_CIMClass_copy(self):  # XXX: Migrate to pytest

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

    def test_CIMClass_attrs(self):  # XXX: Migrate to pytest

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

    def test_CIMClass_eq(self):  # XXX: Migrate to pytest

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
    def test_CIMClass_cmp(self):  # XXX: Implement with pytest
        raise AssertionError("test not implemented")


class CIMClassSort(unittest.TestCase):

    @unimplemented
    def test_CIMClass_sort(self):  # XXX: Implement with pytest
        raise AssertionError("test not implemented")


TESTCASES_CIMCLASS_HASH = [

    # Testcases for CIMClass.__hash__()

    # Each list item is a testcase tuple with these items:
    # * desc: Short testcase description.
    # * kwargs: Keyword arguments for the test function:
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
    TESTCASES_CIMCLASS_HASH)
@simplified_test_function
def test_CIMClass_hash(testcase,
                       obj1, obj2, exp_hash_equal):
    """
    Test function for CIMClass.__hash__().
    """

    # The code to be tested
    hash1 = hash(obj1)
    hash2 = hash(obj2)

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None

    # Double check they are different objects
    assert id(obj1) != id(obj2)

    if exp_hash_equal:
        assert hash1 == hash2
    else:
        assert hash1 != hash2


TESTCASES_CIMCLASS_STR_REPR = [

    # Testcases for CIMClass.__repr__(), __str__() / repr(), str()

    # Each list item is a testcase tuple with these items:
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
            path=CIMClassName('CIM_Foo'))
    ),
]


@pytest.mark.parametrize(
    "obj",
    TESTCASES_CIMCLASS_STR_REPR)
def test_CIMClass_str(obj):
    """
    Test function for CIMClass.__str__() / str()
    """

    # The code to be tested
    s = str(obj)

    assert re.match(r'^CIMClass\(', s)

    exp_classname = _format('classname={0!A}', obj.classname)
    assert exp_classname in s


@pytest.mark.parametrize(
    "obj",
    TESTCASES_CIMCLASS_STR_REPR)
def test_CIMClass_repr(obj):
    """
    Test function for CIMClass.__repr__() / repr()
    """

    # The code to be tested
    r = repr(obj)

    assert re.match(r'^CIMClass\(', r)

    exp_classname = _format('classname={0!A}', obj.classname)
    assert exp_classname in r

    exp_superclass = _format('superclass={0!A}', obj.superclass)
    assert exp_superclass in r

    exp_properties = _format('properties={0!A}', obj.properties)
    assert exp_properties in r

    exp_methods = _format('methods={0!A}', obj.methods)
    assert exp_methods in r

    exp_qualifiers = _format('qualifiers={0!A}', obj.qualifiers)
    assert exp_qualifiers in r

    exp_path = _format('path={0!A}', obj.path)
    assert exp_path in r


# Some CIMClassName objects for CIMClass.tocimxml() tests

CIMCLASSNAME_CLASSNAME1 = CIMClassName('CIM_Foo')
CIMCLASSNAME_NAMESPACE1 = CIMClassName('CIM_Foo', namespace='interop')
CIMCLASSNAME_HOST1 = CIMClassName('CIM_Foo', namespace='interop',
                                  host='woot.com')

TESTCASES_CIMCLASS_TOCIMXML = [

    # Testcases for CIMClass.tocimxml() and tocimxmlstr()

    # Each list item is a testcase tuple with these items:
    # * desc: Short testcase description.
    # * kwargs: Keyword arguments for the test function:
    #   * obj: CIMClass object to be tested.
    #   * kwargs: Dict of input args for tocimxml() (empty).
    #   * exp_xml_str: Expected CIM-XML string, as a tuple/list of parts.
    # * exp_exc_types: Expected exception type(s), or None.
    # * exp_warn_types: Expected warning type(s), or None.
    # * condition: Boolean condition for testcase to run, or 'pdb' for debugger

    # Tests with path and args variations
    (
        "No path",
        dict(
            obj=CIMClass('CIM_Foo'),
            kwargs=dict(),
            exp_xml_str=(
                '<CLASS NAME="CIM_Foo"/>',
            )
        ),
        None, None, True
    ),
    (
        "Path with classname-only",
        dict(
            obj=CIMClass(
                'CIM_Foo',
                path=CIMCLASSNAME_CLASSNAME1,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<CLASS NAME="CIM_Foo"/>',
            )
        ),
        None, None, True
    ),
    (
        "Path with namespace",
        dict(
            obj=CIMClass(
                'CIM_Foo',
                path=CIMCLASSNAME_NAMESPACE1,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<CLASS NAME="CIM_Foo"/>',
            )
        ),
        None, None, True
    ),
    (
        "Path with namespace+host",
        dict(
            obj=CIMClass(
                'CIM_Foo',
                path=CIMCLASSNAME_HOST1,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<CLASS NAME="CIM_Foo"/>',
            )
        ),
        None, None, True
    ),

    # Tests with property variations
    (
        "Two properties",
        dict(
            obj=CIMClass(
                'CIM_Foo',
                properties=[
                    CIMProperty('P1', 'bla'),
                    CIMProperty('P2', 42, type='uint16'),
                ],
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<CLASS NAME="CIM_Foo">',
                '<PROPERTY NAME="P1" TYPE="string">',
                '<VALUE>bla</VALUE>',
                '</PROPERTY>',
                '<PROPERTY NAME="P2" TYPE="uint16">',
                '<VALUE>42</VALUE>',
                '</PROPERTY>',
                '</CLASS>',
            )
        ),
        None, None, True
    ),

    # Tests with method variations
    (
        "Two methods",
        dict(
            obj=CIMClass(
                'CIM_Foo',
                methods=[
                    CIMMethod('M2', return_type='string'),
                    CIMMethod('M1', return_type='uint32'),
                ],
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<CLASS NAME="CIM_Foo">',
                '<METHOD NAME="M2" TYPE="string"/>',
                '<METHOD NAME="M1" TYPE="uint32"/>',
                '</CLASS>',
            )
        ),
        None, None, True
    ),

    # Tests with qualifier variations
    (
        "Two qualifiers",
        dict(
            obj=CIMClass(
                'CIM_Foo',
                qualifiers=[
                    CIMQualifier('Q2', 'bla'),
                    CIMQualifier('Q1', True),
                ],
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<CLASS NAME="CIM_Foo">',
                '<QUALIFIER NAME="Q2" TYPE="string">',
                '<VALUE>bla</VALUE>',
                '</QUALIFIER>',
                '<QUALIFIER NAME="Q1" TYPE="boolean">',
                '<VALUE>TRUE</VALUE>',
                '</QUALIFIER>',
                '</CLASS>',
            )
        ),
        None, None, True
    ),

    # Tests with qualifier, property, method variations
    (
        "Two qualifiers, two properties, two methods",
        dict(
            obj=CIMClass(
                'CIM_Foo',
                qualifiers=[
                    CIMQualifier('Q2', 'bla'),
                    CIMQualifier('Q1', True),
                ],
                properties=[
                    CIMProperty('P2', 42, type='uint16'),
                    CIMProperty('P1', 'bla'),
                ],
                methods=[
                    CIMMethod('M2', return_type='string'),
                    CIMMethod('M1', return_type='uint32'),
                ],
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<CLASS NAME="CIM_Foo">',
                '<QUALIFIER NAME="Q2" TYPE="string">',
                '<VALUE>bla</VALUE>',
                '</QUALIFIER>',
                '<QUALIFIER NAME="Q1" TYPE="boolean">',
                '<VALUE>TRUE</VALUE>',
                '</QUALIFIER>',
                '<PROPERTY NAME="P2" TYPE="uint16">',
                '<VALUE>42</VALUE>',
                '</PROPERTY>',
                '<PROPERTY NAME="P1" TYPE="string">',
                '<VALUE>bla</VALUE>',
                '</PROPERTY>',
                '<METHOD NAME="M2" TYPE="string"/>',
                '<METHOD NAME="M1" TYPE="uint32"/>',
                '</CLASS>',
            )
        ),
        None, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_CIMCLASS_TOCIMXML)
@simplified_test_function
def test_CIMClass_tocimxml(testcase,
                           obj, kwargs, exp_xml_str):
    """
    Test function for CIMClass.tocimxml().
    """

    # The code to be tested
    obj_xml = obj.tocimxml(**kwargs)

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None

    obj_xml_str = obj_xml.toxml()
    exp_xml_str = ''.join(exp_xml_str)
    validate_cim_xml_obj(obj, obj_xml_str, exp_xml_str)


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_CIMCLASS_TOCIMXML)
@simplified_test_function
def test_CIMClass_tocimxmlstr(testcase,
                              obj, kwargs, exp_xml_str):
    """
    Test function for CIMClass.tocimxmlstr().
    """

    # The code to be tested
    obj_xml_str = obj.tocimxmlstr(**kwargs)

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None

    assert isinstance(obj_xml_str, six.text_type)

    exp_xml_str = ''.join(exp_xml_str)
    validate_cim_xml_obj(obj, obj_xml_str, exp_xml_str)


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_CIMCLASS_TOCIMXML)
@simplified_test_function
def test_CIMClass_tocimxmlstr_indent_int(
        testcase, obj, kwargs, exp_xml_str):
    """
    Test function for CIMClass.tocimxmlstr() with indent as integer.
    """

    indent = 4
    indent_str = ' ' * indent

    # The code to be tested
    obj_xml_str = obj.tocimxmlstr(indent=indent, **kwargs)

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None

    obj_xml = obj.tocimxml(**kwargs)  # This is tested elsewhere
    exp_xml_str = obj_xml.toprettyxml(indent=indent_str)

    assert obj_xml_str == exp_xml_str, \
        "{0}.tocimxmlstr(indent={1!r}) returns unexpected CIM-XML string". \
        format(obj.__class__.__name__, indent)


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_CIMCLASS_TOCIMXML)
@simplified_test_function
def test_CIMClass_tocimxmlstr_indent_str(
        testcase, obj, kwargs, exp_xml_str):
    """
    Test function for CIMClass.tocimxmlstr() with indent as string.
    """

    indent = 4
    indent_str = ' ' * indent

    # The code to be tested
    obj_xml_str = obj.tocimxmlstr(indent=indent_str, **kwargs)

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None

    obj_xml = obj.tocimxml(**kwargs)  # This is tested elsewhere
    exp_xml_str = obj_xml.toprettyxml(indent=indent_str)

    assert obj_xml_str == exp_xml_str, \
        "{0}.tocimxmlstr(indent={1!r}) returns unexpected CIM-XML string". \
        format(obj.__class__.__name__, indent_str)


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
                        'p2', type='string', value="abc",
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
    def test_CIMClass_tomof(  # XXX: Migrate to s.tst.fnc.
            self, desc, obj, exp_result, exp_warn_type, condition):
        # pylint: disable=unused-argument
        """Test function for CIMClass.tomof()."""

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

    def test_CIMMethod_init_pos_args(self):  # XXX: Merge with succeeds
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

    def test_CIMMethod_init_methodname(self):  # XXX: Merge with succeeds
        # pylint: disable=unused-argument
        """Test deprecated methodname argument of CIMMethod.__init__()."""

        with pytest.warns(DeprecationWarning) as rec_warnings:

            # The code to be tested
            obj = CIMMethod(
                methodname='FooMethod',
                return_type='string')

        assert len(rec_warnings) == 1
        assert obj.name == u'FooMethod'

    def test_CIMMethod_init_name_methodname(self):  # XXX: Merge with succeeds
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
        propagated=None,
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
            "Verify that bytes name and return type are converted to unicode",
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
            "Verify that bytes class_origin is converted to unicode",
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
    def test_CIMMethod_init_succeeds(  # XXX: Migrate to s.tst.fnc.
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
    def test_CIMMethod_init_fails(  # XXX: Merge with succeeds
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

    def test_CIMMethod_copy(self):  # XXX: Migrate to pytest

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

    def test_CIMMethod_attrs(self):  # XXX: Migrate to pytest

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

    def test_CIMMethod_eq(self):  # XXX: Migrate to pytest

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
    def test_CIMMethod_cmp(self):  # XXX: Implement with pytest
        raise AssertionError("test not implemented")


class CIMMethodSort(unittest.TestCase):

    @unimplemented
    def test_CIMMethod_sort(self):  # XXX: Implement with pytest
        raise AssertionError("test not implemented")


TESTCASES_CIMMETHOD_HASH = [

    # Testcases for CIMMethod.__hash__()

    # Each list item is a testcase tuple with these items:
    # * desc: Short testcase description.
    # * kwargs: Keyword arguments for the test function:
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
    TESTCASES_CIMMETHOD_HASH)
@simplified_test_function
def test_CIMMethod_hash(testcase,
                        obj1, obj2, exp_hash_equal):
    """
    Test function for CIMMethod.__hash__().
    """

    # The code to be tested
    hash1 = hash(obj1)
    hash2 = hash(obj2)

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None

    # Double check they are different objects
    assert id(obj1) != id(obj2)

    if exp_hash_equal:
        assert hash1 == hash2
    else:
        assert hash1 != hash2


TESTCASES_CIMMETHOD_STR_REPR = [

    # Testcases for CIMMethod.__repr__(), __str__() / repr(), str()

    # Each list item is a testcase tuple with these items:
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
            parameters=dict(P1=CIMParameter('P1', type='uint32')),
            class_origin='CIM_Origin',
            propagated=True,
            qualifiers=dict(Q1=CIMQualifier('Q1', value=True)))
    ),
]


@pytest.mark.parametrize(
    "obj",
    TESTCASES_CIMMETHOD_STR_REPR)
def test_CIMMethod_str(obj):
    """
    Test function for CIMMethod.__str__() / str()
    """

    # The code to be tested
    s = str(obj)

    assert re.match(r'^CIMMethod\(', s)

    exp_name = _format('name={0!A}', obj.name)
    assert exp_name in s

    exp_return_type = _format('return_type={0!A}', obj.return_type)
    assert exp_return_type in s


@pytest.mark.parametrize(
    "obj",
    TESTCASES_CIMMETHOD_STR_REPR)
def test_CIMMethod_repr(obj):
    """
    Test function for CIMMethod.__repr__() / repr()
    """

    # The code to be tested
    r = repr(obj)

    assert re.match(r'^CIMMethod\(', r)

    exp_name = _format('name={0!A}', obj.name)
    assert exp_name in r

    exp_return_type = _format('return_type={0!A}', obj.return_type)
    assert exp_return_type in r

    exp_parameters = _format('parameters={0!A}', obj.parameters)
    assert exp_parameters in r

    exp_class_origin = _format('class_origin={0!A}', obj.class_origin)
    assert exp_class_origin in r

    exp_propagated = _format('propagated={0!A}', obj.propagated)
    assert exp_propagated in r

    exp_qualifiers = _format('qualifiers={0!A}', obj.qualifiers)
    assert exp_qualifiers in r


class CIMMethodNoReturn(unittest.TestCase):
    """Test that CIMMethod without return value fails"""

    def test_CIMMethod_init_NoReturn(self):  # XXX: Merge with succeeds
        try:
            str(CIMMethod('FooMethod'))
            self.fail('Expected Exception')

        except ValueError:
            pass


TESTCASES_CIMMETHOD_TOCIMXML = [

    # Testcases for CIMMethod.tocimxml() and tocimxmlstr()

    # Each list item is a testcase tuple with these items:
    # * desc: Short testcase description.
    # * kwargs: Keyword arguments for the test function:
    #   * obj: CIMMethod object to be tested.
    #   * kwargs: Dict of input args for tocimxml() (empty).
    #   * exp_xml_str: Expected CIM-XML string, as a tuple/list of parts.
    # * exp_exc_types: Expected exception type(s), or None.
    # * exp_warn_types: Expected warning type(s), or None.
    # * condition: Boolean condition for testcase to run, or 'pdb' for debugger

    # Tests with name variations
    (
        "Name with ASCII characters, as byte string",
        dict(
            obj=CIMMethod(b'Foo', return_type='string'),
            kwargs=dict(),
            exp_xml_str=(
                '<METHOD NAME="Foo" TYPE="string"/>',
            )
        ),
        None, None, True
    ),
    (
        "Name with ASCII characters, as unicode string",
        dict(
            obj=CIMMethod(u'Foo', return_type='string'),
            kwargs=dict(),
            exp_xml_str=(
                '<METHOD NAME="Foo" TYPE="string"/>',
            )
        ),
        None, None, True
    ),
    (
        "Name with non-ASCII UCS-2 characters, as byte string",
        dict(
            obj=CIMMethod(b'Foo\xC3\xA9', return_type='string'),
            kwargs=dict(),
            exp_xml_str=(
                u'<METHOD NAME="Foo\u00E9" TYPE="string"/>',
            )
        ),
        None, None, True
    ),
    (
        "Name with non-ASCII UCS-2 characters, as unicode string",
        dict(
            obj=CIMMethod(u'Foo\u00E9', return_type='string'),
            kwargs=dict(),
            exp_xml_str=(
                u'<METHOD NAME="Foo\u00E9" TYPE="string"/>',
            )
        ),
        None, None, True
    ),
    (
        "Name with non-UCS-2 characters, as byte string",
        dict(
            obj=CIMMethod(b'Foo\xF0\x90\x85\x82', return_type='string'),
            kwargs=dict(),
            exp_xml_str=(
                u'<METHOD NAME="Foo\U00010142" TYPE="string"/>',
            )
        ),
        None, None, True
    ),
    (
        "Name with non-UCS-2 characters, as unicode string",
        dict(
            obj=CIMMethod(u'Foo\U00010142', return_type='string'),
            kwargs=dict(),
            exp_xml_str=(
                u'<METHOD NAME="Foo\U00010142" TYPE="string"/>',
            )
        ),
        None, None, True
    ),

    # Tests with qualifier variations
    (
        "Two qualifiers",
        dict(
            obj=CIMMethod(
                'Foo', return_type='string',
                qualifiers=[
                    CIMQualifier('Q2', 'bla'),
                    CIMQualifier('Q1', True),
                ],
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<METHOD NAME="Foo" TYPE="string">',
                '<QUALIFIER NAME="Q2" TYPE="string">',
                '<VALUE>bla</VALUE>',
                '</QUALIFIER>',
                '<QUALIFIER NAME="Q1" TYPE="boolean">',
                '<VALUE>TRUE</VALUE>',
                '</QUALIFIER>',
                '</METHOD>',
            )
        ),
        None, None, True
    ),

    # Tests with return type variations (subset, scalar-only)
    # Methods cannot have reference return type (checked by CIMMethod)
    (
        "Return type boolean",
        dict(
            obj=CIMMethod(
                'Foo', return_type='boolean',
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<METHOD NAME="Foo" TYPE="boolean"/>',
            )
        ),
        None, None, True
    ),
    (
        "Return type string",
        dict(
            obj=CIMMethod(
                'Foo', return_type='string',
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<METHOD NAME="Foo" TYPE="string"/>',
            )
        ),
        None, None, True
    ),
    (
        "Return type real32",
        dict(
            obj=CIMMethod(
                'Foo', return_type='real32',
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<METHOD NAME="Foo" TYPE="real32"/>',
            )
        ),
        None, None, True
    ),
    (
        "Return type sint64",
        dict(
            obj=CIMMethod(
                'Foo', return_type='sint64',
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<METHOD NAME="Foo" TYPE="sint64"/>',
            )
        ),
        None, None, True
    ),
    (
        "Return type datetime",
        dict(
            obj=CIMMethod(
                'Foo', return_type='datetime',
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<METHOD NAME="Foo" TYPE="datetime"/>',
            )
        ),
        None, None, True
    ),

    # Tests with parameter variations (subset)
    (
        "Two parameters",
        dict(
            obj=CIMMethod(
                'Foo', return_type='uint32',
                parameters=[
                    CIMParameter('P2', type='boolean'),
                    CIMParameter('P1', type='string', is_array=True),
                ],
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<METHOD NAME="Foo" TYPE="uint32">',
                '<PARAMETER NAME="P2" TYPE="boolean"/>',
                '<PARAMETER.ARRAY NAME="P1" TYPE="string"/>',
                '</METHOD>',
            )
        ),
        None, None, True
    ),

    # Tests with class_origin, propagated variations
    (
        "Class origin set",
        dict(
            obj=CIMMethod(
                'Foo', return_type='uint32', class_origin='CIM_Origin',
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<METHOD CLASSORIGIN="CIM_Origin" NAME="Foo" TYPE="uint32"/>',
            )
        ),
        None, None, True
    ),
    (
        "Propagated set to True",
        dict(
            obj=CIMMethod(
                'Foo', return_type='uint32', propagated=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<METHOD NAME="Foo" PROPAGATED="true" TYPE="uint32"/>',
            )
        ),
        None, None, True
    ),
    (
        "Propagated set to False",
        dict(
            obj=CIMMethod(
                'Foo', return_type='uint32', propagated=False,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<METHOD NAME="Foo" PROPAGATED="false" TYPE="uint32"/>',
            )
        ),
        None, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_CIMMETHOD_TOCIMXML)
@simplified_test_function
def test_CIMMethod_tocimxml(testcase,
                            obj, kwargs, exp_xml_str):
    """
    Test function for CIMMethod.tocimxml().
    """

    # The code to be tested
    obj_xml = obj.tocimxml(**kwargs)

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None

    obj_xml_str = obj_xml.toxml()
    exp_xml_str = ''.join(exp_xml_str)
    validate_cim_xml_obj(obj, obj_xml_str, exp_xml_str)


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_CIMMETHOD_TOCIMXML)
@simplified_test_function
def test_CIMMethod_tocimxmlstr(testcase,
                               obj, kwargs, exp_xml_str):
    """
    Test function for CIMMethod.tocimxmlstr().
    """

    # The code to be tested
    obj_xml_str = obj.tocimxmlstr(**kwargs)

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None

    assert isinstance(obj_xml_str, six.text_type)

    exp_xml_str = ''.join(exp_xml_str)
    validate_cim_xml_obj(obj, obj_xml_str, exp_xml_str)


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_CIMMETHOD_TOCIMXML)
@simplified_test_function
def test_CIMMethod_tocimxmlstr_indent_int(
        testcase, obj, kwargs, exp_xml_str):
    """
    Test function for CIMMethod.tocimxmlstr() with indent as integer.
    """

    indent = 4
    indent_str = ' ' * indent

    # The code to be tested
    obj_xml_str = obj.tocimxmlstr(indent=indent, **kwargs)

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None

    obj_xml = obj.tocimxml(**kwargs)  # This is tested elsewhere
    exp_xml_str = obj_xml.toprettyxml(indent=indent_str)

    assert obj_xml_str == exp_xml_str, \
        "{0}.tocimxmlstr(indent={1!r}) returns unexpected CIM-XML string". \
        format(obj.__class__.__name__, indent)


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_CIMMETHOD_TOCIMXML)
@simplified_test_function
def test_CIMMethod_tocimxmlstr_indent_str(
        testcase, obj, kwargs, exp_xml_str):
    """
    Test function for CIMMethod.tocimxmlstr() with indent as string.
    """

    indent = 4
    indent_str = ' ' * indent

    # The code to be tested
    obj_xml_str = obj.tocimxmlstr(indent=indent_str, **kwargs)

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None

    obj_xml = obj.tocimxml(**kwargs)  # This is tested elsewhere
    exp_xml_str = obj_xml.toprettyxml(indent=indent_str)

    assert obj_xml_str == exp_xml_str, \
        "{0}.tocimxmlstr(indent={1!r}) returns unexpected CIM-XML string". \
        format(obj.__class__.__name__, indent_str)


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
    def test_CIMMethod_tomof(  # XXX: Migrate to s.tst.fnc.
            self, desc, obj, indent, exp_result, exp_warn_type, condition):
        # pylint: disable=unused-argument
        """Test function for CIMMethod.tomof()."""

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

    def test_CIMParameter_init_pos_args(self):  # XXX: Merge with succeeds
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
            "Verify that bytes name and type are converted to unicode",
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
            "Verify that bytes reference_class is converted to unicode",
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
            "Verify that mismatch between is_array False and array_size is "
            "ignored",
            dict(name=u'FooParam', type=u'string', value=u'abc',
                 is_array=False, array_size=2),
            dict(name=u'FooParam', type=u'string', value=u'abc',
                 is_array=False, array_size=2),
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

        # embedded_object=False tests
        (
            "Verify that embedded_object=False results in None",
            dict(name=u'FooParam', type=u'string', value=u'abc',
                 embedded_object=False),
            dict(name=u'FooParam', type=u'string', value=u'abc',
                 embedded_object=None),
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
    def test_CIMParameter_init_succeeds(  # XXX: Migrate to s.tst.fnc.
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
    def test_CIMParameter_init_fails(  # XXX: Merge with succeeds
            self, desc, kwargs, exp_exc_type, condition):
        # pylint: disable=unused-argument
        """All test cases where CIMParameter.__init__() fails."""

        if not condition:
            pytest.skip("Condition for test case not met")

        with pytest.raises(exp_exc_type):

            # The code to be tested
            CIMParameter(**kwargs)


class CIMParameterCopy(unittest.TestCase):

    def test_CIMParameter_copy(self):  # XXX: Migrate to pytest

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

    def test_CIMParameter_attrs(self):  # XXX: Migrate to pytest

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

    def test_CIMParameter_eq(self):  # XXX: Migrate to pytest

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
    def test_CIMParameter_cmp(self):  # XXX: Implement with pytest
        raise AssertionError("test not implemented")


class CIMParameterSort(unittest.TestCase):

    @unimplemented
    def test_CIMParameter_sort(self):  # XXX: Implement with pytest
        raise AssertionError("test not implemented")


TESTCASES_CIMPARAMETER_HASH = [

    # Testcases for CIMParameter.__hash__()

    # Each list item is a testcase tuple with these items:
    # * desc: Short testcase description.
    # * kwargs: Keyword arguments for the test function:
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
    TESTCASES_CIMPARAMETER_HASH)
@simplified_test_function
def test_CIMParameter_hash(testcase,
                           obj1, obj2, exp_hash_equal):
    """
    Test function for CIMParameter.__hash__().
    """

    # The code to be tested
    hash1 = hash(obj1)
    hash2 = hash(obj2)

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None

    # Double check they are different objects
    assert id(obj1) != id(obj2)

    if exp_hash_equal:
        assert hash1 == hash2
    else:
        assert hash1 != hash2


TESTCASES_CIMPARAMETER_STR_REPR = [

    # Testcases for CIMParameter.__repr__(), __str__() / repr(), str()

    # Each list item is a testcase tuple with these items:
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
            qualifiers=dict(Q1=CIMQualifier('Q1', value=Uint32(42))),
            value=None)
    ),
]


@pytest.mark.parametrize(
    "obj",
    TESTCASES_CIMPARAMETER_STR_REPR)
def test_CIMParameter_str(obj):
    """
    Test function for CIMParameter.__str__() / str()
    """

    # The code to be tested
    s = str(obj)

    assert re.match(r'^CIMParameter\(', s)

    exp_name = _format('name={0!A}', obj.name)
    assert exp_name in s

    exp_type = _format('type={0!A}', obj.type)
    assert exp_type in s

    exp_reference_class = _format('reference_class={0!A}', obj.reference_class)
    assert exp_reference_class in s

    exp_is_array = _format('is_array={0!A}', obj.is_array)
    assert exp_is_array in s


@pytest.mark.parametrize(
    "obj",
    TESTCASES_CIMPARAMETER_STR_REPR)
def test_CIMParameter_repr(obj):
    """
    Test function for CIMParameter.__repr__() / repr()
    """

    # The code to be tested
    r = repr(obj)

    assert re.match(r'^CIMParameter\(', r)

    exp_name = _format('name={0!A}', obj.name)
    assert exp_name in r

    exp_type = _format('type={0!A}', obj.type)
    assert exp_type in r

    exp_reference_class = _format('reference_class={0!A}', obj.reference_class)
    assert exp_reference_class in r

    exp_is_array = _format('is_array={0!A}', obj.is_array)
    assert exp_is_array in r

    exp_array_size = _format('array_size={0!A}', obj.array_size)
    assert exp_array_size in r

    exp_qualifiers = _format('qualifiers={0!A}', obj.qualifiers)
    assert exp_qualifiers in r


TESTCASES_CIMPARAMETER_TOCIMXML = [

    # Testcases for CIMParameter.tocimxml() and tocimxmlstr()

    # Each list item is a testcase tuple with these items:
    # * desc: Short testcase description.
    # * kwargs: Keyword arguments for the test function:
    #   * obj: CIMParameter object to be tested.
    #   * kwargs: Dict of input args for tocimxml().
    #   * exp_xml_str: Expected CIM-XML string, as a tuple/list of parts.
    # * exp_exc_types: Expected exception type(s), or None.
    # * exp_warn_types: Expected warning type(s), or None.
    # * condition: Boolean condition for testcase to run, or 'pdb' for debugger

    # Parameters with variations of as_value argument
    (
        "Argument as_value defaults to False",
        dict(
            obj=CIMParameter(b'Foo', type='string', value=None),
            kwargs=dict(),
            exp_xml_str=(
                '<PARAMETER NAME="Foo" TYPE="string"/>',
            )
        ),
        None, None, True
    ),
    (
        "Argument as_value specified as False",
        dict(
            obj=CIMParameter(b'Foo', type='string', value=None),
            kwargs=dict(as_value=False),
            exp_xml_str=(
                '<PARAMETER NAME="Foo" TYPE="string"/>',
            )
        ),
        None, None, True
    ),
    (
        "Argument as_value specified as True",
        dict(
            obj=CIMParameter(b'Foo', type='string', value=None),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                '<PARAMVALUE NAME="Foo" PARAMTYPE="string"/>',
            )
        ),
        None, None, True
    ),

    # Parameters with name variations
    (
        "Parameter as declaration, name with ASCII characters, as byte string",
        dict(
            obj=CIMParameter(b'Foo', type='string'),
            kwargs=dict(as_value=False),
            exp_xml_str=(
                '<PARAMETER NAME="Foo" TYPE="string"/>',
            )
        ),
        None, None, True
    ),
    (
        "Parameter as declaration, name with ASCII characters, as unicode "
        "string",
        dict(
            obj=CIMParameter(u'Foo', type='string'),
            kwargs=dict(as_value=False),
            exp_xml_str=(
                '<PARAMETER NAME="Foo" TYPE="string"/>',
            )
        ),
        None, None, True
    ),
    (
        "Parameter as declaration, name with non-ASCII UCS-2 characters, as "
        "byte string",
        dict(
            obj=CIMParameter(b'Foo\xC3\xA9', value=None, type='string'),
            kwargs=dict(as_value=False),
            exp_xml_str=(
                u'<PARAMETER NAME="Foo\u00E9" TYPE="string"/>',
            )
        ),
        None, None, True
    ),
    (
        "Parameter as declaration, name with non-ASCII UCS-2 characters, as "
        "unicode string",
        dict(
            obj=CIMParameter(u'Foo\u00E9', value=None, type='string'),
            kwargs=dict(as_value=False),
            exp_xml_str=(
                u'<PARAMETER NAME="Foo\u00E9" TYPE="string"/>',
            )
        ),
        None, None, True
    ),
    (
        "Parameter as declaration, name with non-UCS-2 characters, as byte "
        "string",
        dict(
            obj=CIMParameter(b'Foo\xF0\x90\x85\x82', value=None, type='string'),
            kwargs=dict(as_value=False),
            exp_xml_str=(
                u'<PARAMETER NAME="Foo\U00010142" TYPE="string"/>',
            )
        ),
        None, None, True
    ),
    (
        "Parameter as declaration, name with non-UCS-2 characters, as unicode "
        "string",
        dict(
            obj=CIMParameter(u'Foo\U00010142', value=None, type='string'),
            kwargs=dict(as_value=False),
            exp_xml_str=(
                u'<PARAMETER NAME="Foo\U00010142" TYPE="string"/>',
            )
        ),
        None, None, True
    ),
    (
        "Parameter as value, name with ASCII characters, as byte string",
        dict(
            obj=CIMParameter(b'Foo', type='string'),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                '<PARAMVALUE NAME="Foo" PARAMTYPE="string"/>',
            )
        ),
        None, None, True
    ),
    (
        "Parameter as value, name with ASCII characters, as unicode string",
        dict(
            obj=CIMParameter(u'Foo', type='string'),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                '<PARAMVALUE NAME="Foo" PARAMTYPE="string"/>',
            )
        ),
        None, None, True
    ),
    (
        "Parameter as value, name with non-ASCII UCS-2 characters, as byte "
        "string",
        dict(
            obj=CIMParameter(b'Foo\xC3\xA9', value=None, type='string'),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                u'<PARAMVALUE NAME="Foo\u00E9" PARAMTYPE="string"/>',
            )
        ),
        None, None, True
    ),
    (
        "Parameter as value, name with non-ASCII UCS-2 characters, as unicode "
        "string",
        dict(
            obj=CIMParameter(u'Foo\u00E9', value=None, type='string'),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                u'<PARAMVALUE NAME="Foo\u00E9" PARAMTYPE="string"/>',
            )
        ),
        None, None, True
    ),
    (
        "Parameter as value, name with non-UCS-2 characters, as byte string",
        dict(
            obj=CIMParameter(b'Foo\xF0\x90\x85\x82', value=None, type='string'),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                u'<PARAMVALUE NAME="Foo\U00010142" PARAMTYPE="string"/>',
            )
        ),
        None, None, True
    ),
    (
        "Parameter as value, name with non-UCS-2 characters, as unicode string",
        dict(
            obj=CIMParameter(u'Foo\U00010142', value=None, type='string'),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                u'<PARAMVALUE NAME="Foo\U00010142" PARAMTYPE="string"/>',
            )
        ),
        None, None, True
    ),

    # Parameters with qualifier variations
    (
        "Parameter as declaration, no qualifiers",
        dict(
            obj=CIMParameter(
                'Foo', type='string', value=None,
                qualifiers=[],
            ),
            kwargs=dict(as_value=False),
            exp_xml_str=(
                '<PARAMETER NAME="Foo" TYPE="string"/>',
            )
        ),
        None, None, True
    ),
    (
        "Parameter as declaration, two qualifiers and string value",
        dict(
            obj=CIMParameter(
                'Foo', type='string', value='foo',
                qualifiers=[
                    CIMQualifier('Q2', 'bla'),
                    CIMQualifier('Q1', True),
                ],
            ),
            kwargs=dict(as_value=False),
            exp_xml_str=(
                '<PARAMETER NAME="Foo" TYPE="string">',
                '<QUALIFIER NAME="Q2" TYPE="string">',
                '<VALUE>bla</VALUE>',
                '</QUALIFIER>',
                '<QUALIFIER NAME="Q1" TYPE="boolean">',
                '<VALUE>TRUE</VALUE>',
                '</QUALIFIER>',
                '</PARAMETER>',
            )
        ),
        None, None, True
    ),
    (
        "Parameter as value, no qualifiers",
        dict(
            obj=CIMParameter(
                'Foo', type='string', value=None,
                qualifiers=[],
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                '<PARAMVALUE NAME="Foo" PARAMTYPE="string"/>',
            )
        ),
        None, None, True
    ),
    (
        "Parameter as value, two qualifiers and string value",
        dict(
            obj=CIMParameter(
                'Foo', type='string', value='foo',
                qualifiers=[
                    CIMQualifier('Q2', 'bla'),
                    CIMQualifier('Q1', True),
                ],
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                '<PARAMVALUE NAME="Foo" PARAMTYPE="string">',
                '<VALUE>foo</VALUE>',
                '</PARAMVALUE>',
            )
        ),
        None, None, True
    ),

    # Scalar parameters with boolean type
    (
        "Scalar parameter as declaration with boolean type",
        dict(
            obj=CIMParameter(
                'Foo', type='boolean', value=True,
            ),
            kwargs=dict(as_value=False),
            exp_xml_str=(
                '<PARAMETER NAME="Foo" TYPE="boolean"/>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar parameter as value with boolean type, value NULL",
        dict(
            obj=CIMParameter(
                'Foo', type='boolean', value=None,
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                '<PARAMVALUE NAME="Foo" PARAMTYPE="boolean"/>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar parameter as value with boolean type, value True",
        dict(
            obj=CIMParameter(
                'Foo', type='boolean', value=True,
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                '<PARAMVALUE NAME="Foo" PARAMTYPE="boolean">',
                '<VALUE>TRUE</VALUE>',
                '</PARAMVALUE>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar parameter as value with boolean type, value False",
        dict(
            obj=CIMParameter(
                'Foo', type='boolean', value=False,
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                '<PARAMVALUE NAME="Foo" PARAMTYPE="boolean">',
                '<VALUE>FALSE</VALUE>',
                '</PARAMVALUE>',
            )
        ),
        None, None, True
    ),

    # Scalar parameters with string type
    (
        "Scalar parameter as declaration with string type",
        dict(
            obj=CIMParameter(
                'Foo', type='string', value='bla',
            ),
            kwargs=dict(as_value=False),
            exp_xml_str=(
                '<PARAMETER NAME="Foo" TYPE="string"/>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar parameter as value with string type, value NULL",
        dict(
            obj=CIMParameter(
                'Foo', type='string', value=None,
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                '<PARAMVALUE NAME="Foo" PARAMTYPE="string"/>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar parameter as value with string type, value has one entry with "
        "ASCII characters",
        dict(
            obj=CIMParameter(
                'Foo', type='string', value='foo',
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                '<PARAMVALUE NAME="Foo" PARAMTYPE="string">',
                '<VALUE>foo</VALUE>',
                '</PARAMVALUE>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar parameter as value with string type, value has one entry with "
        "non-ASCII UCS-2 characters",
        dict(
            obj=CIMParameter(
                'Foo', type='string', value=u'foo\u00E9',
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                u'<PARAMVALUE NAME="Foo" PARAMTYPE="string">',
                u'<VALUE>foo\u00E9</VALUE>',
                u'</PARAMVALUE>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar parameter as value with string type, value has one entry with "
        "non-UCS-2 characters",
        dict(
            obj=CIMParameter(
                'Foo', type='string', value=u'foo\U00010142',
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                u'<PARAMVALUE NAME="Foo" PARAMTYPE="string">',
                u'<VALUE>foo\U00010142</VALUE>',
                u'</PARAMVALUE>',
            )
        ),
        None, None, True
    ),

    # Scalar parameters with char16 type
    (
        "Scalar parameter as declaration with char16 type",
        dict(
            obj=CIMParameter(
                'Foo', type='char16', value='b',
            ),
            kwargs=dict(as_value=False),
            exp_xml_str=(
                '<PARAMETER NAME="Foo" TYPE="char16"/>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar parameter as value with char16 type, value NULL",
        dict(
            obj=CIMParameter(
                'Foo', type='char16', value=None,
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                '<PARAMVALUE NAME="Foo" PARAMTYPE="char16"/>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar parameter as value with char16 type, value has one entry with "
        "a ASCII character",
        dict(
            obj=CIMParameter(
                'Foo', type='char16', value='f',
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                '<PARAMVALUE NAME="Foo" PARAMTYPE="char16">',
                '<VALUE>f</VALUE>',
                '</PARAMVALUE>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar parameter as value with char16 type, value has one entry with "
        "a non-ASCII UCS-2 character",
        dict(
            obj=CIMParameter(
                'Foo', type='char16', value=u'\u00E9',
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                u'<PARAMVALUE NAME="Foo" PARAMTYPE="char16">',
                u'<VALUE>\u00E9</VALUE>',
                u'</PARAMVALUE>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar parameter as value with char16 type, value has one entry with "
        "a non-UCS-2 character "
        "(invalid as per DSP0004, but tolerated by pywbem)",
        dict(
            obj=CIMParameter(
                'Foo', type='char16', value=u'\U00010142',
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                u'<PARAMVALUE NAME="Foo" PARAMTYPE="char16">',
                u'<VALUE>\U00010142</VALUE>',
                u'</PARAMVALUE>',
            )
        ),
        None, None, True
    ),

    # Scalar parameters with uint8 type
    (
        "Scalar parameter as declaration with uint8 type",
        dict(
            obj=CIMParameter(
                'Foo', type='uint8', value=42,
            ),
            kwargs=dict(as_value=False),
            exp_xml_str=(
                '<PARAMETER NAME="Foo" TYPE="uint8"/>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar parameter as value with uint8 type, value NULL",
        dict(
            obj=CIMParameter(
                'Foo', type='uint8', value=None,
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                '<PARAMVALUE NAME="Foo" PARAMTYPE="uint8"/>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar parameter as value with uint8 type, value has one entry in "
        "range",
        dict(
            obj=CIMParameter(
                'Foo', type='uint8', value=42,
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                '<PARAMVALUE NAME="Foo" PARAMTYPE="uint8">',
                '<VALUE>42</VALUE>',
                '</PARAMVALUE>',
            )
        ),
        None, None, True
    ),

    # Scalar parameters with uint16 type
    (
        "Scalar parameter as declaration with uint16 type",
        dict(
            obj=CIMParameter(
                'Foo', type='uint16', value=42,
            ),
            kwargs=dict(as_value=False),
            exp_xml_str=(
                '<PARAMETER NAME="Foo" TYPE="uint16"/>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar parameter as value with uint16 type, value NULL",
        dict(
            obj=CIMParameter(
                'Foo', type='uint16', value=None,
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                '<PARAMVALUE NAME="Foo" PARAMTYPE="uint16"/>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar parameter as value with uint16 type, value has one entry in "
        "range",
        dict(
            obj=CIMParameter(
                'Foo', type='uint16', value=1234,
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                '<PARAMVALUE NAME="Foo" PARAMTYPE="uint16">',
                '<VALUE>1234</VALUE>',
                '</PARAMVALUE>',
            )
        ),
        None, None, True
    ),

    # Scalar parameters with uint32 type
    (
        "Scalar parameter as declaration with uint32 type",
        dict(
            obj=CIMParameter(
                'Foo', type='uint32', value=42,
            ),
            kwargs=dict(as_value=False),
            exp_xml_str=(
                '<PARAMETER NAME="Foo" TYPE="uint32"/>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar parameter as value with uint32 type, value NULL",
        dict(
            obj=CIMParameter(
                'Foo', type='uint32', value=None,
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                '<PARAMVALUE NAME="Foo" PARAMTYPE="uint32"/>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar parameter as value with uint32 type, value has one entry in "
        "range",
        dict(
            obj=CIMParameter(
                'Foo', type='uint32', value=12345678,
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                '<PARAMVALUE NAME="Foo" PARAMTYPE="uint32">',
                '<VALUE>12345678</VALUE>',
                '</PARAMVALUE>',
            )
        ),
        None, None, True
    ),

    # Scalar parameters with uint64 type
    (
        "Scalar parameter as declaration with uint64 type",
        dict(
            obj=CIMParameter(
                'Foo', type='uint64', value=42,
            ),
            kwargs=dict(as_value=False),
            exp_xml_str=(
                '<PARAMETER NAME="Foo" TYPE="uint64"/>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar parameter as value with uint64 type, value NULL",
        dict(
            obj=CIMParameter(
                'Foo', type='uint64', value=None,
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                '<PARAMVALUE NAME="Foo" PARAMTYPE="uint64"/>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar parameter as value with uint64 type, value has one entry in "
        "range",
        dict(
            obj=CIMParameter(
                'Foo', type='uint64', value=123456789012,
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                '<PARAMVALUE NAME="Foo" PARAMTYPE="uint64">',
                '<VALUE>123456789012</VALUE>',
                '</PARAMVALUE>',
            )
        ),
        None, None, True
    ),

    # Scalar parameters with sint8 type
    (
        "Scalar parameter as declaration with sint8 type",
        dict(
            obj=CIMParameter(
                'Foo', type='sint8', value=42,
            ),
            kwargs=dict(as_value=False),
            exp_xml_str=(
                '<PARAMETER NAME="Foo" TYPE="sint8"/>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar parameter as value with sint8 type, value NULL",
        dict(
            obj=CIMParameter(
                'Foo', type='sint8', value=None,
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                '<PARAMVALUE NAME="Foo" PARAMTYPE="sint8"/>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar parameter as value with sint8 type, value has one entry in "
        "range",
        dict(
            obj=CIMParameter(
                'Foo', type='sint8', value=-42,
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                '<PARAMVALUE NAME="Foo" PARAMTYPE="sint8">',
                '<VALUE>-42</VALUE>',
                '</PARAMVALUE>',
            )
        ),
        None, None, True
    ),

    # Scalar parameters with sint16 type
    (
        "Scalar parameter as declaration with sint16 type",
        dict(
            obj=CIMParameter(
                'Foo', type='sint16', value=42,
            ),
            kwargs=dict(as_value=False),
            exp_xml_str=(
                '<PARAMETER NAME="Foo" TYPE="sint16"/>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar parameter as value with sint16 type, value NULL",
        dict(
            obj=CIMParameter(
                'Foo', type='sint16', value=None,
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                '<PARAMVALUE NAME="Foo" PARAMTYPE="sint16"/>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar parameter as value with sint16 type, value has one entry in "
        "range",
        dict(
            obj=CIMParameter(
                'Foo', type='sint16', value=-1234,
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                '<PARAMVALUE NAME="Foo" PARAMTYPE="sint16">',
                '<VALUE>-1234</VALUE>',
                '</PARAMVALUE>',
            )
        ),
        None, None, True
    ),

    # Scalar parameters with sint32 type
    (
        "Scalar parameter as declaration with sint32 type",
        dict(
            obj=CIMParameter(
                'Foo', type='sint32', value=42,
            ),
            kwargs=dict(as_value=False),
            exp_xml_str=(
                '<PARAMETER NAME="Foo" TYPE="sint32"/>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar parameter as value with sint32 type, value NULL",
        dict(
            obj=CIMParameter(
                'Foo', type='sint32', value=None,
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                '<PARAMVALUE NAME="Foo" PARAMTYPE="sint32"/>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar parameter as value with sint32 type, value has one entry in "
        "range",
        dict(
            obj=CIMParameter(
                'Foo', type='sint32', value=-12345678,
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                '<PARAMVALUE NAME="Foo" PARAMTYPE="sint32">',
                '<VALUE>-12345678</VALUE>',
                '</PARAMVALUE>',
            )
        ),
        None, None, True
    ),

    # Scalar parameters with sint64 type
    (
        "Scalar parameter as declaration with sint64 type",
        dict(
            obj=CIMParameter(
                'Foo', type='sint64', value=42,
            ),
            kwargs=dict(as_value=False),
            exp_xml_str=(
                '<PARAMETER NAME="Foo" TYPE="sint64"/>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar parameter as value with sint64 type, value NULL",
        dict(
            obj=CIMParameter(
                'Foo', type='sint64', value=None,
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                '<PARAMVALUE NAME="Foo" PARAMTYPE="sint64"/>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar parameter as value with sint64 type, value has one entry in "
        "range",
        dict(
            obj=CIMParameter(
                'Foo', type='sint64', value=-123456789012,
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                '<PARAMVALUE NAME="Foo" PARAMTYPE="sint64">',
                '<VALUE>-123456789012</VALUE>',
                '</PARAMVALUE>',
            )
        ),
        None, None, True
    ),

    # Scalar parameters with real32 type
    (
        "Scalar parameter as declaration with real32 type",
        dict(
            obj=CIMParameter(
                'Foo', type='real32', value=42,
            ),
            kwargs=dict(as_value=False),
            exp_xml_str=(
                '<PARAMETER NAME="Foo" TYPE="real32"/>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar parameter as value with real32 type, value NULL",
        dict(
            obj=CIMParameter(
                'Foo', type='real32', value=None,
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                '<PARAMVALUE NAME="Foo" PARAMTYPE="real32"/>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar parameter as value with real32 type, value between 0 and 1",
        dict(
            obj=CIMParameter(
                'Foo', type='real32', value=0.42,
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                '<PARAMVALUE NAME="Foo" PARAMTYPE="real32">',
                '<VALUE>0.42</VALUE>',
                '</PARAMVALUE>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar parameter as value with real32 type, value with max number of "
        "significant digits (11)",
        dict(
            obj=CIMParameter(
                'Foo', type='real32', value=1.2345678901,
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                '<PARAMVALUE NAME="Foo" PARAMTYPE="real32">',
                '<VALUE>1.2345678901</VALUE>',
                '</PARAMVALUE>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar parameter as value with real32 type, value larger 1 without "
        "exponent",
        dict(
            obj=CIMParameter(
                'Foo', type='real32', value=42.0,
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                '<PARAMVALUE NAME="Foo" PARAMTYPE="real32">',
                '<VALUE>42.0</VALUE>',
                '</PARAMVALUE>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar parameter as value with real32 type, value with small "
        "negative exponent",
        dict(
            obj=CIMParameter(
                'Foo', type='real32', value=-42.0E-3,
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                '<PARAMVALUE NAME="Foo" PARAMTYPE="real32">',
                '<VALUE>-0.042</VALUE>',
                '</PARAMVALUE>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar parameter as value with real32 type, value with small "
        "positive exponent",
        dict(
            obj=CIMParameter(
                'Foo', type='real32', value=-42.0E+3,
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                '<PARAMVALUE NAME="Foo" PARAMTYPE="real32">',
                '<VALUE>-42000.0</VALUE>',
                '</PARAMVALUE>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar parameter as value with real32 type, value with large "
        "negative exponent",
        dict(
            obj=CIMParameter(
                'Foo', type='real32', value=-42.0E-30,
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                '<PARAMVALUE NAME="Foo" PARAMTYPE="real32">',
                '<VALUE>-4.2E-29</VALUE>',
                '</PARAMVALUE>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar parameter as value with real32 type, value with large "
        "positive exponent",
        dict(
            obj=CIMParameter(
                'Foo', type='real32', value=-42.0E+30,
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                '<PARAMVALUE NAME="Foo" PARAMTYPE="real32">',
                '<VALUE>-4.2E+31</VALUE>',
                '</PARAMVALUE>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar parameter as value with real32 type, special value INF",
        dict(
            obj=CIMParameter(
                'Foo', type='real32', value=float('inf'),
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                '<PARAMVALUE NAME="Foo" PARAMTYPE="real32">',
                '<VALUE>INF</VALUE>',  # must be upper case
                '</PARAMVALUE>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar parameter as value with real32 type, special value -INF",
        dict(
            obj=CIMParameter(
                'Foo', type='real32', value=float('-inf'),
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                '<PARAMVALUE NAME="Foo" PARAMTYPE="real32">',
                '<VALUE>-INF</VALUE>',  # must be upper case
                '</PARAMVALUE>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar parameter as value with real32 type, special value NaN",
        dict(
            obj=CIMParameter(
                'Foo', type='real32', value=float('nan'),
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                '<PARAMVALUE NAME="Foo" PARAMTYPE="real32">',
                '<VALUE>NaN</VALUE>',  # must be upper case
                '</PARAMVALUE>',
            )
        ),
        None, None, True
    ),

    # Scalar parameters with real64 type
    (
        "Scalar parameter as declaration with real64 type",
        dict(
            obj=CIMParameter(
                'Foo', type='real64', value=42,
            ),
            kwargs=dict(as_value=False),
            exp_xml_str=(
                '<PARAMETER NAME="Foo" TYPE="real64"/>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar parameter as value with real64 type, value NULL",
        dict(
            obj=CIMParameter(
                'Foo', type='real64', value=None,
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                '<PARAMVALUE NAME="Foo" PARAMTYPE="real64"/>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar parameter as value with real64 type, value between 0 and 1",
        dict(
            obj=CIMParameter(
                'Foo', type='real64', value=0.42,
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                '<PARAMVALUE NAME="Foo" PARAMTYPE="real64">',
                '<VALUE>0.42</VALUE>',
                '</PARAMVALUE>',
            )
        ),
        None, None, False  # py27: 0.41999999999999998
    ),
    (
        "Scalar parameter as value with real64 type, value with max number of "
        "significant digits (17)",
        dict(
            obj=CIMParameter(
                'Foo', type='real64', value=1.2345678901234567,
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                '<PARAMVALUE NAME="Foo" PARAMTYPE="real64">',
                '<VALUE>1.2345678901234567</VALUE>',
                '</PARAMVALUE>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar parameter as value with real64 type, value larger 1 without "
        "exponent",
        dict(
            obj=CIMParameter(
                'Foo', type='real64', value=42.0,
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                '<PARAMVALUE NAME="Foo" PARAMTYPE="real64">',
                '<VALUE>42.0</VALUE>',
                '</PARAMVALUE>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar parameter as value with real64 type, value with small "
        "negative exponent",
        dict(
            obj=CIMParameter(
                'Foo', type='real64', value=-42.0E-3,
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                '<PARAMVALUE NAME="Foo" PARAMTYPE="real64">',
                '<VALUE>-0.042</VALUE>',
                '</PARAMVALUE>',
            )
        ),
        None, None, False  # py27: -0.042000000000000003
    ),
    (
        "Scalar parameter as value with real64 type, value with small "
        "positive exponent",
        dict(
            obj=CIMParameter(
                'Foo', type='real64', value=-42.0E+3,
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                '<PARAMVALUE NAME="Foo" PARAMTYPE="real64">',
                '<VALUE>-42000.0</VALUE>',
                '</PARAMVALUE>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar parameter as value with real64 type, value with large "
        "negative exponent",
        dict(
            obj=CIMParameter(
                'Foo', type='real64', value=-42.0E-30,
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                '<PARAMVALUE NAME="Foo" PARAMTYPE="real64">',
                '<VALUE>-4.2E-29</VALUE>',
                '</PARAMVALUE>',
            )
        ),
        None, None, False  # py27: -4.1999999999999998E-29
    ),
    (
        "Scalar parameter as value with real64 type, value with large "
        "positive exponent",
        dict(
            obj=CIMParameter(
                'Foo', type='real64', value=-42.0E+30,
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                '<PARAMVALUE NAME="Foo" PARAMTYPE="real64">',
                '<VALUE>-4.2E+31</VALUE>',
                '</PARAMVALUE>',
            )
        ),
        None, None, False  # py27: -4.1999999999999996E+31
    ),
    (
        "Scalar parameter as value with real64 type, special value INF",
        dict(
            obj=CIMParameter(
                'Foo', type='real64', value=float('inf'),
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                '<PARAMVALUE NAME="Foo" PARAMTYPE="real64">',
                '<VALUE>INF</VALUE>',  # must be upper case
                '</PARAMVALUE>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar parameter as value with real64 type, special value -INF",
        dict(
            obj=CIMParameter(
                'Foo', type='real64', value=float('-inf'),
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                '<PARAMVALUE NAME="Foo" PARAMTYPE="real64">',
                '<VALUE>-INF</VALUE>',  # must be upper case
                '</PARAMVALUE>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar parameter as value with real64 type, special value NaN",
        dict(
            obj=CIMParameter(
                'Foo', type='real64', value=float('nan'),
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                '<PARAMVALUE NAME="Foo" PARAMTYPE="real64">',
                '<VALUE>NaN</VALUE>',  # must be upper case
                '</PARAMVALUE>',
            )
        ),
        None, None, True
    ),

    # Scalar parameters with datetime type
    (
        "Scalar parameter as declaration with datetime type",
        dict(
            obj=CIMParameter(
                'Foo', type='datetime',
                value=datetime(2014, 9, 22, 10, 49, 20, 524789),
            ),
            kwargs=dict(as_value=False),
            exp_xml_str=(
                '<PARAMETER NAME="Foo" TYPE="datetime"/>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar parameter as value with datetime type, value NULL",
        dict(
            obj=CIMParameter(
                'Foo', type='datetime', value=None,
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                '<PARAMVALUE NAME="Foo" PARAMTYPE="datetime"/>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar parameter as value with datetime type, point in time value",
        dict(
            obj=CIMParameter(
                'Foo', type='datetime',
                value=datetime(2014, 9, 22, 10, 49, 20, 524789),
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                '<PARAMVALUE NAME="Foo" PARAMTYPE="datetime">',
                '<VALUE>20140922104920.524789+000</VALUE>',
                '</PARAMVALUE>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar parameter as value with datetime type, interval value",
        dict(
            obj=CIMParameter(
                'Foo', type='datetime',
                value=timedelta(10, 49, 20),
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                '<PARAMVALUE NAME="Foo" PARAMTYPE="datetime">',
                '<VALUE>00000010000049.000020:000</VALUE>',
                '</PARAMVALUE>',
            )
        ),
        None, None, True
    ),

    # Scalar parameters with reference type
    (
        "Scalar parameter as declaration with reference type",
        dict(
            obj=CIMParameter(
                'Foo', type='reference',
                value=CIMInstanceName('CIM_Foo'),
            ),
            kwargs=dict(as_value=False),
            exp_xml_str=(
                '<PARAMETER.REFERENCE NAME="Foo"/>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar parameter as value with reference type, value NULL",
        dict(
            obj=CIMParameter(
                'Foo', type='reference', value=None,
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                '<PARAMVALUE NAME="Foo" PARAMTYPE="reference"/>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar parameter as value with reference type, classname-only ref "
        "value",
        dict(
            obj=CIMParameter(
                'Foo', type='reference',
                value=CIMInstanceName('CIM_Foo'),
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                '<PARAMVALUE NAME="Foo" PARAMTYPE="reference">',
                '<VALUE.REFERENCE>',
                '<INSTANCENAME CLASSNAME="CIM_Foo"/>',
                '</VALUE.REFERENCE>',
                '</PARAMVALUE>',
            )
        ),
        None, None, True
    ),

    # Array parameters with boolean type
    (
        "Array parameter as declaration with boolean type",
        dict(
            obj=CIMParameter(
                'Foo', type='boolean', value=[True],
                is_array=True,
            ),
            kwargs=dict(as_value=False),
            exp_xml_str=(
                '<PARAMETER.ARRAY NAME="Foo" TYPE="boolean"/>',
            )
        ),
        None, None, True
    ),
    (
        "Array parameter as value with boolean type, value is NULL",
        dict(
            obj=CIMParameter(
                'Foo', type='boolean', value=None,
                is_array=True,
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                '<PARAMVALUE NAME="Foo" PARAMTYPE="boolean"/>',
            )
        ),
        None, None, True
    ),
    (
        "Array parameter as value with boolean type, value is empty array",
        dict(
            obj=CIMParameter(
                'Foo', type='boolean', value=[],
                is_array=True,
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                '<PARAMVALUE NAME="Foo" PARAMTYPE="boolean">',
                '<VALUE.ARRAY/>',
                '</PARAMVALUE>',
            )
        ),
        None, None, True
    ),
    (
        "Array parameter as value with boolean type, value has one entry NULL",
        dict(
            obj=CIMParameter(
                'Foo', type='boolean', value=[None],
                is_array=True,
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                '<PARAMVALUE NAME="Foo" PARAMTYPE="boolean">',
                '<VALUE.ARRAY>',
                '<VALUE.NULL/>',
                '</VALUE.ARRAY>',
                '</PARAMVALUE>',
            )
        ),
        None, None, True
    ),
    (
        "Array parameter as value with boolean type, value has one entry True",
        dict(
            obj=CIMParameter(
                'Foo', type='boolean', value=[True],
                is_array=True,
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                '<PARAMVALUE NAME="Foo" PARAMTYPE="boolean">',
                '<VALUE.ARRAY>',
                '<VALUE>TRUE</VALUE>',
                '</VALUE.ARRAY>',
                '</PARAMVALUE>',
            )
        ),
        None, None, True
    ),
    (
        "Array parameter as value with boolean type, value has one entry False",
        dict(
            obj=CIMParameter(
                'Foo', type='boolean', value=[False],
                is_array=True,
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                '<PARAMVALUE NAME="Foo" PARAMTYPE="boolean">',
                '<VALUE.ARRAY>',
                '<VALUE>FALSE</VALUE>',
                '</VALUE.ARRAY>',
                '</PARAMVALUE>',
            )
        ),
        None, None, True
    ),

    # Array parameters with string type
    (
        "Array parameter as declaration with string type",
        dict(
            obj=CIMParameter(
                'Foo', type='string', value=['bla'],
                is_array=True,
            ),
            kwargs=dict(as_value=False),
            exp_xml_str=(
                '<PARAMETER.ARRAY NAME="Foo" TYPE="string"/>',
            )
        ),
        None, None, True
    ),
    (
        "Array parameter as value with string type, value NULL",
        dict(
            obj=CIMParameter(
                'Foo', type='string', value=None,
                is_array=True,
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                '<PARAMVALUE NAME="Foo" PARAMTYPE="string"/>',
            )
        ),
        None, None, True
    ),
    (
        "Array parameter as value with string type, value empty array",
        dict(
            obj=CIMParameter(
                'Foo', type='string', value=[],
                is_array=True,
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                '<PARAMVALUE NAME="Foo" PARAMTYPE="string">',
                '<VALUE.ARRAY/>',
                '</PARAMVALUE>',
            )
        ),
        None, None, True
    ),
    (
        "Array parameter as value with string type, value has one entry NULL",
        dict(
            obj=CIMParameter(
                'Foo', type='string', value=[None],
                is_array=True,
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                '<PARAMVALUE NAME="Foo" PARAMTYPE="string">',
                '<VALUE.ARRAY>',
                '<VALUE.NULL/>',
                '</VALUE.ARRAY>',
                '</PARAMVALUE>',
            )
        ),
        None, None, True
    ),
    (
        "Array parameter as value with string type, value has one entry with "
        "ASCII characters",
        dict(
            obj=CIMParameter(
                'Foo', type='string', value=['foo'],
                is_array=True,
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                '<PARAMVALUE NAME="Foo" PARAMTYPE="string">',
                '<VALUE.ARRAY>',
                '<VALUE>foo</VALUE>',
                '</VALUE.ARRAY>',
                '</PARAMVALUE>',
            )
        ),
        None, None, True
    ),
    (
        "Array parameter as value with string type, value has one entry with "
        "non-ASCII UCS-2 characters",
        dict(
            obj=CIMParameter(
                'Foo', type='string', value=[u'foo\u00E9'],
                is_array=True,
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                u'<PARAMVALUE NAME="Foo" PARAMTYPE="string">',
                u'<VALUE.ARRAY>',
                u'<VALUE>foo\u00E9</VALUE>',
                u'</VALUE.ARRAY>',
                u'</PARAMVALUE>',
            )
        ),
        None, None, True
    ),
    (
        "Array parameter as value with string type, value has one entry with "
        "non-UCS-2 characters",
        dict(
            obj=CIMParameter(
                'Foo', type='string', value=[u'foo\U00010142'],
                is_array=True,
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                u'<PARAMVALUE NAME="Foo" PARAMTYPE="string">',
                u'<VALUE.ARRAY>',
                u'<VALUE>foo\U00010142</VALUE>',
                u'</VALUE.ARRAY>',
                u'</PARAMVALUE>',
            )
        ),
        None, None, True
    ),

    # Array parameters with char16 type
    (
        "Array parameter as declaration with char16 type",
        dict(
            obj=CIMParameter(
                'Foo', type='char16', value=['b'],
                is_array=True,
            ),
            kwargs=dict(as_value=False),
            exp_xml_str=(
                '<PARAMETER.ARRAY NAME="Foo" TYPE="char16"/>',
            )
        ),
        None, None, True
    ),
    (
        "Array parameter as value with char16 type, value NULL",
        dict(
            obj=CIMParameter(
                'Foo', type='char16', value=None,
                is_array=True,
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                '<PARAMVALUE NAME="Foo" PARAMTYPE="char16"/>',
            )
        ),
        None, None, True
    ),
    (
        "Array parameter as value with char16 type, value empty array",
        dict(
            obj=CIMParameter(
                'Foo', type='char16', value=[],
                is_array=True,
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                '<PARAMVALUE NAME="Foo" PARAMTYPE="char16">',
                '<VALUE.ARRAY/>',
                '</PARAMVALUE>',
            )
        ),
        None, None, True
    ),
    (
        "Array parameter as value with char16 type, value has one entry NULL",
        dict(
            obj=CIMParameter(
                'Foo', type='char16', value=[None],
                is_array=True,
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                '<PARAMVALUE NAME="Foo" PARAMTYPE="char16">',
                '<VALUE.ARRAY>',
                '<VALUE.NULL/>',
                '</VALUE.ARRAY>',
                '</PARAMVALUE>',
            )
        ),
        None, None, True
    ),
    (
        "Array parameter as value with char16 type, value has one entry with "
        "an ASCII character",
        dict(
            obj=CIMParameter(
                'Foo', type='char16', value=['f'],
                is_array=True,
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                '<PARAMVALUE NAME="Foo" PARAMTYPE="char16">',
                '<VALUE.ARRAY>',
                '<VALUE>f</VALUE>',
                '</VALUE.ARRAY>',
                '</PARAMVALUE>',
            )
        ),
        None, None, True
    ),
    (
        "Array parameter as value with char16 type, value has one entry with "
        "a non-ASCII UCS-2 character",
        dict(
            obj=CIMParameter(
                'Foo', type='char16', value=[u'\u00E9'],
                is_array=True,
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                u'<PARAMVALUE NAME="Foo" PARAMTYPE="char16">',
                u'<VALUE.ARRAY>',
                u'<VALUE>\u00E9</VALUE>',
                u'</VALUE.ARRAY>',
                u'</PARAMVALUE>',
            )
        ),
        None, None, True
    ),
    (
        "Array parameter as value with char16 type, value has one entry with "
        "a non-UCS-2 character "
        "(invalid as per DSP0004, but tolerated by pywbem)",
        dict(
            obj=CIMParameter(
                'Foo', type='char16', value=[u'\U00010142'],
                is_array=True,
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                u'<PARAMVALUE NAME="Foo" PARAMTYPE="char16">',
                u'<VALUE.ARRAY>',
                u'<VALUE>\U00010142</VALUE>',
                u'</VALUE.ARRAY>',
                u'</PARAMVALUE>',
            )
        ),
        None, None, True
    ),

    # Array parameters with uint8 type
    (
        "Array parameter as declaration with uint8 type",
        dict(
            obj=CIMParameter(
                'Foo', type='uint8', value=[42],
                is_array=True,
            ),
            kwargs=dict(as_value=False),
            exp_xml_str=(
                '<PARAMETER.ARRAY NAME="Foo" TYPE="uint8"/>',
            )
        ),
        None, None, True
    ),
    (
        "Array parameter as value with uint8 type, value NULL",
        dict(
            obj=CIMParameter(
                'Foo', type='uint8', value=None,
                is_array=True,
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                '<PARAMVALUE NAME="Foo" PARAMTYPE="uint8"/>',
            )
        ),
        None, None, True
    ),
    (
        "Array parameter as value with uint8 type, value empty array",
        dict(
            obj=CIMParameter(
                'Foo', type='uint8', value=[],
                is_array=True,
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                '<PARAMVALUE NAME="Foo" PARAMTYPE="uint8">',
                '<VALUE.ARRAY/>',
                '</PARAMVALUE>',
            )
        ),
        None, None, True
    ),
    (
        "Array parameter as value with uint8 type, value has one entry NULL",
        dict(
            obj=CIMParameter(
                'Foo', type='uint8', value=[None],
                is_array=True,
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                '<PARAMVALUE NAME="Foo" PARAMTYPE="uint8">',
                '<VALUE.ARRAY>',
                '<VALUE.NULL/>',
                '</VALUE.ARRAY>',
                '</PARAMVALUE>',
            )
        ),
        None, None, True
    ),
    (
        "Array parameter as value with uint8 type, value has one entry in "
        "range",
        dict(
            obj=CIMParameter(
                'Foo', type='uint8', value=[42],
                is_array=True,
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                '<PARAMVALUE NAME="Foo" PARAMTYPE="uint8">',
                '<VALUE.ARRAY>',
                '<VALUE>42</VALUE>',
                '</VALUE.ARRAY>',
                '</PARAMVALUE>',
            )
        ),
        None, None, True
    ),

    # Array parameters with uint16 type
    (
        "Array parameter as declaration with uint16 type",
        dict(
            obj=CIMParameter(
                'Foo', type='uint16', value=[42],
                is_array=True,
            ),
            kwargs=dict(as_value=False),
            exp_xml_str=(
                '<PARAMETER.ARRAY NAME="Foo" TYPE="uint16"/>',
            )
        ),
        None, None, True
    ),
    (
        "Array parameter as value with uint16 type, value NULL",
        dict(
            obj=CIMParameter(
                'Foo', type='uint16', value=None,
                is_array=True,
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                '<PARAMVALUE NAME="Foo" PARAMTYPE="uint16"/>',
            )
        ),
        None, None, True
    ),
    (
        "Array parameter as value with uint16 type, value empty array",
        dict(
            obj=CIMParameter(
                'Foo', type='uint16', value=[],
                is_array=True,
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                '<PARAMVALUE NAME="Foo" PARAMTYPE="uint16">',
                '<VALUE.ARRAY/>',
                '</PARAMVALUE>',
            )
        ),
        None, None, True
    ),
    (
        "Array parameter as value with uint16 type, value has one entry NULL",
        dict(
            obj=CIMParameter(
                'Foo', type='uint16', value=[None],
                is_array=True,
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                '<PARAMVALUE NAME="Foo" PARAMTYPE="uint16">',
                '<VALUE.ARRAY>',
                '<VALUE.NULL/>',
                '</VALUE.ARRAY>',
                '</PARAMVALUE>',
            )
        ),
        None, None, True
    ),
    (
        "Array parameter as value with uint16 type, value has one entry in "
        "range",
        dict(
            obj=CIMParameter(
                'Foo', type='uint16', value=[1234],
                is_array=True,
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                '<PARAMVALUE NAME="Foo" PARAMTYPE="uint16">',
                '<VALUE.ARRAY>',
                '<VALUE>1234</VALUE>',
                '</VALUE.ARRAY>',
                '</PARAMVALUE>',
            )
        ),
        None, None, True
    ),

    # Array parameters with uint32 type
    (
        "Array parameter as declaration with uint32 type",
        dict(
            obj=CIMParameter(
                'Foo', type='uint32', value=[42],
                is_array=True,
            ),
            kwargs=dict(as_value=False),
            exp_xml_str=(
                '<PARAMETER.ARRAY NAME="Foo" TYPE="uint32"/>',
            )
        ),
        None, None, True
    ),
    (
        "Array parameter as value with uint32 type, value NULL",
        dict(
            obj=CIMParameter(
                'Foo', type='uint32', value=None,
                is_array=True,
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                '<PARAMVALUE NAME="Foo" PARAMTYPE="uint32"/>',
            )
        ),
        None, None, True
    ),
    (
        "Array parameter as value with uint32 type, value empty array",
        dict(
            obj=CIMParameter(
                'Foo', type='uint32', value=[],
                is_array=True,
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                '<PARAMVALUE NAME="Foo" PARAMTYPE="uint32">',
                '<VALUE.ARRAY/>',
                '</PARAMVALUE>',
            )
        ),
        None, None, True
    ),
    (
        "Array parameter as value with uint32 type, value has one entry NULL",
        dict(
            obj=CIMParameter(
                'Foo', type='uint32', value=[None],
                is_array=True,
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                '<PARAMVALUE NAME="Foo" PARAMTYPE="uint32">',
                '<VALUE.ARRAY>',
                '<VALUE.NULL/>',
                '</VALUE.ARRAY>',
                '</PARAMVALUE>',
            )
        ),
        None, None, True
    ),
    (
        "Array parameter as value with uint32 type, value has one entry in "
        "range",
        dict(
            obj=CIMParameter(
                'Foo', type='uint32', value=[12345678],
                is_array=True,
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                '<PARAMVALUE NAME="Foo" PARAMTYPE="uint32">',
                '<VALUE.ARRAY>',
                '<VALUE>12345678</VALUE>',
                '</VALUE.ARRAY>',
                '</PARAMVALUE>',
            )
        ),
        None, None, True
    ),

    # Array properties with uint64 type
    (
        "Array parameter as declaration with uint64 type",
        dict(
            obj=CIMParameter(
                'Foo', type='uint64', value=[42],
                is_array=True,
            ),
            kwargs=dict(as_value=False),
            exp_xml_str=(
                '<PARAMETER.ARRAY NAME="Foo" TYPE="uint64"/>',
            )
        ),
        None, None, True
    ),
    (
        "Array parameter as value with uint64 type, value NULL",
        dict(
            obj=CIMParameter(
                'Foo', type='uint64', value=None,
                is_array=True,
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                '<PARAMVALUE NAME="Foo" PARAMTYPE="uint64"/>',
            )
        ),
        None, None, True
    ),
    (
        "Array parameter as value with uint64 type, value empty array",
        dict(
            obj=CIMParameter(
                'Foo', type='uint64', value=[],
                is_array=True,
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                '<PARAMVALUE NAME="Foo" PARAMTYPE="uint64">',
                '<VALUE.ARRAY/>',
                '</PARAMVALUE>',
            )
        ),
        None, None, True
    ),
    (
        "Array parameter as value with uint64 type, value has one entry NULL",
        dict(
            obj=CIMParameter(
                'Foo', type='uint64', value=[None],
                is_array=True,
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                '<PARAMVALUE NAME="Foo" PARAMTYPE="uint64">',
                '<VALUE.ARRAY>',
                '<VALUE.NULL/>',
                '</VALUE.ARRAY>',
                '</PARAMVALUE>',
            )
        ),
        None, None, True
    ),
    (
        "Array parameter as value with uint64 type, value has one entry in "
        "range",
        dict(
            obj=CIMParameter(
                'Foo', type='uint64', value=[123456789012],
                is_array=True,
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                '<PARAMVALUE NAME="Foo" PARAMTYPE="uint64">',
                '<VALUE.ARRAY>',
                '<VALUE>123456789012</VALUE>',
                '</VALUE.ARRAY>',
                '</PARAMVALUE>',
            )
        ),
        None, None, True
    ),

    # Array parameters with sint8 type
    (
        "Array parameter as declaration with sint8 type",
        dict(
            obj=CIMParameter(
                'Foo', type='sint8', value=[42],
                is_array=True,
            ),
            kwargs=dict(as_value=False),
            exp_xml_str=(
                '<PARAMETER.ARRAY NAME="Foo" TYPE="sint8"/>',
            )
        ),
        None, None, True
    ),
    (
        "Array parameter as value with sint8 type, value NULL",
        dict(
            obj=CIMParameter(
                'Foo', type='sint8', value=None,
                is_array=True,
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                '<PARAMVALUE NAME="Foo" PARAMTYPE="sint8"/>',
            )
        ),
        None, None, True
    ),
    (
        "Array parameter as value with sint8 type, value empty array",
        dict(
            obj=CIMParameter(
                'Foo', type='sint8', value=[],
                is_array=True,
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                '<PARAMVALUE NAME="Foo" PARAMTYPE="sint8">',
                '<VALUE.ARRAY/>',
                '</PARAMVALUE>',
            )
        ),
        None, None, True
    ),
    (
        "Array parameter as value with sint8 type, value has one entry NULL",
        dict(
            obj=CIMParameter(
                'Foo', type='sint8', value=[None],
                is_array=True,
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                '<PARAMVALUE NAME="Foo" PARAMTYPE="sint8">',
                '<VALUE.ARRAY>',
                '<VALUE.NULL/>',
                '</VALUE.ARRAY>',
                '</PARAMVALUE>',
            )
        ),
        None, None, True
    ),
    (
        "Array parameter as value with sint8 type, value has one entry in "
        "range",
        dict(
            obj=CIMParameter(
                'Foo', type='sint8', value=[-42],
                is_array=True,
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                '<PARAMVALUE NAME="Foo" PARAMTYPE="sint8">',
                '<VALUE.ARRAY>',
                '<VALUE>-42</VALUE>',
                '</VALUE.ARRAY>',
                '</PARAMVALUE>',
            )
        ),
        None, None, True
    ),

    # Array parameters with sint16 type
    (
        "Array parameter as declaration with sint16 type",
        dict(
            obj=CIMParameter(
                'Foo', type='sint16', value=[42],
                is_array=True,
            ),
            kwargs=dict(as_value=False),
            exp_xml_str=(
                '<PARAMETER.ARRAY NAME="Foo" TYPE="sint16"/>',
            )
        ),
        None, None, True
    ),
    (
        "Array parameter as value with sint16 type, value NULL",
        dict(
            obj=CIMParameter(
                'Foo', type='sint16', value=None,
                is_array=True,
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                '<PARAMVALUE NAME="Foo" PARAMTYPE="sint16"/>',
            )
        ),
        None, None, True
    ),
    (
        "Array parameter as value with sint16 type, value empty array",
        dict(
            obj=CIMParameter(
                'Foo', type='sint16', value=[],
                is_array=True,
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                '<PARAMVALUE NAME="Foo" PARAMTYPE="sint16">',
                '<VALUE.ARRAY/>',
                '</PARAMVALUE>',
            )
        ),
        None, None, True
    ),
    (
        "Array parameter as value with sint16 type, value has one entry NULL",
        dict(
            obj=CIMParameter(
                'Foo', type='sint16', value=[None],
                is_array=True,
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                '<PARAMVALUE NAME="Foo" PARAMTYPE="sint16">',
                '<VALUE.ARRAY>',
                '<VALUE.NULL/>',
                '</VALUE.ARRAY>',
                '</PARAMVALUE>',
            )
        ),
        None, None, True
    ),
    (
        "Array parameter as value with sint16 type, value has one entry in "
        "range",
        dict(
            obj=CIMParameter(
                'Foo', type='sint16', value=[-1234],
                is_array=True,
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                '<PARAMVALUE NAME="Foo" PARAMTYPE="sint16">',
                '<VALUE.ARRAY>',
                '<VALUE>-1234</VALUE>',
                '</VALUE.ARRAY>',
                '</PARAMVALUE>',
            )
        ),
        None, None, True
    ),

    # Array parameters with sint32 type
    (
        "Array parameter as declaration with sint32 type",
        dict(
            obj=CIMParameter(
                'Foo', type='sint32', value=[42],
                is_array=True,
            ),
            kwargs=dict(as_value=False),
            exp_xml_str=(
                '<PARAMETER.ARRAY NAME="Foo" TYPE="sint32"/>',
            )
        ),
        None, None, True
    ),
    (
        "Array parameter as value with sint32 type, value NULL",
        dict(
            obj=CIMParameter(
                'Foo', type='sint32', value=None,
                is_array=True,
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                '<PARAMVALUE NAME="Foo" PARAMTYPE="sint32"/>',
            )
        ),
        None, None, True
    ),
    (
        "Array parameter as value with sint32 type, value empty array",
        dict(
            obj=CIMParameter(
                'Foo', type='sint32', value=[],
                is_array=True,
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                '<PARAMVALUE NAME="Foo" PARAMTYPE="sint32">',
                '<VALUE.ARRAY/>',
                '</PARAMVALUE>',
            )
        ),
        None, None, True
    ),
    (
        "Array parameter as value with sint32 type, value has one entry NULL",
        dict(
            obj=CIMParameter(
                'Foo', type='sint32', value=[None],
                is_array=True,
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                '<PARAMVALUE NAME="Foo" PARAMTYPE="sint32">',
                '<VALUE.ARRAY>',
                '<VALUE.NULL/>',
                '</VALUE.ARRAY>',
                '</PARAMVALUE>',
            )
        ),
        None, None, True
    ),
    (
        "Array parameter as value with sint32 type, value has one entry in "
        "range",
        dict(
            obj=CIMParameter(
                'Foo', type='sint32', value=[-12345678],
                is_array=True,
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                '<PARAMVALUE NAME="Foo" PARAMTYPE="sint32">',
                '<VALUE.ARRAY>',
                '<VALUE>-12345678</VALUE>',
                '</VALUE.ARRAY>',
                '</PARAMVALUE>',
            )
        ),
        None, None, True
    ),

    # Array parameters with sint64 type
    (
        "Array parameter as declaration with sint64 type",
        dict(
            obj=CIMParameter(
                'Foo', type='sint64', value=[42],
                is_array=True,
            ),
            kwargs=dict(as_value=False),
            exp_xml_str=(
                '<PARAMETER.ARRAY NAME="Foo" TYPE="sint64"/>',
            )
        ),
        None, None, True
    ),
    (
        "Array parameter as value with sint64 type, value NULL",
        dict(
            obj=CIMParameter(
                'Foo', type='sint64', value=None,
                is_array=True,
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                '<PARAMVALUE NAME="Foo" PARAMTYPE="sint64"/>',
            )
        ),
        None, None, True
    ),
    (
        "Array parameter as value with sint64 type, value empty array",
        dict(
            obj=CIMParameter(
                'Foo', type='sint64', value=[],
                is_array=True,
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                '<PARAMVALUE NAME="Foo" PARAMTYPE="sint64">',
                '<VALUE.ARRAY/>',
                '</PARAMVALUE>',
            )
        ),
        None, None, True
    ),
    (
        "Array parameter as value with sint64 type, value has one entry NULL",
        dict(
            obj=CIMParameter(
                'Foo', type='sint64', value=[None],
                is_array=True,
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                '<PARAMVALUE NAME="Foo" PARAMTYPE="sint64">',
                '<VALUE.ARRAY>',
                '<VALUE.NULL/>',
                '</VALUE.ARRAY>',
                '</PARAMVALUE>',
            )
        ),
        None, None, True
    ),
    (
        "Array parameter as value with sint64 type, value has one entry in "
        "range",
        dict(
            obj=CIMParameter(
                'Foo', type='sint64', value=[-123456789012],
                is_array=True,
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                '<PARAMVALUE NAME="Foo" PARAMTYPE="sint64">',
                '<VALUE.ARRAY>',
                '<VALUE>-123456789012</VALUE>',
                '</VALUE.ARRAY>',
                '</PARAMVALUE>',
            )
        ),
        None, None, True
    ),

    # Array parameters with real32 type
    (
        "Array parameter as declaration with real32 type",
        dict(
            obj=CIMParameter(
                'Foo', type='real32', value=[42],
                is_array=True,
            ),
            kwargs=dict(as_value=False),
            exp_xml_str=(
                '<PARAMETER.ARRAY NAME="Foo" TYPE="real32"/>',
            )
        ),
        None, None, True
    ),
    (
        "Array parameter as value with real32 type, value NULL",
        dict(
            obj=CIMParameter(
                'Foo', type='real32', value=None,
                is_array=True,
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                '<PARAMVALUE NAME="Foo" PARAMTYPE="real32"/>',
            )
        ),
        None, None, True
    ),
    (
        "Array parameter as value with real32 type, value empty array",
        dict(
            obj=CIMParameter(
                'Foo', type='real32', value=[],
                is_array=True,
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                '<PARAMVALUE NAME="Foo" PARAMTYPE="real32">',
                '<VALUE.ARRAY/>',
                '</PARAMVALUE>',
            )
        ),
        None, None, True
    ),
    (
        "Array parameter as value with real32 type, value has one entry NULL",
        dict(
            obj=CIMParameter(
                'Foo', type='real32', value=[None],
                is_array=True,
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                '<PARAMVALUE NAME="Foo" PARAMTYPE="real32">',
                '<VALUE.ARRAY>',
                '<VALUE.NULL/>',
                '</VALUE.ARRAY>',
                '</PARAMVALUE>',
            )
        ),
        None, None, True
    ),
    (
        "Array parameter as value with real32 type, value between 0 and 1",
        dict(
            obj=CIMParameter(
                'Foo', type='real32', value=[0.42],
                is_array=True,
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                '<PARAMVALUE NAME="Foo" PARAMTYPE="real32">',
                '<VALUE.ARRAY>',
                '<VALUE>0.42</VALUE>',
                '</VALUE.ARRAY>',
                '</PARAMVALUE>',
            )
        ),
        None, None, True
    ),
    (
        "Array parameter as value with real32 type, value with max number of "
        "significant digits (11)",
        dict(
            obj=CIMParameter(
                'Foo', type='real32', value=[1.2345678901],
                is_array=True,
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                '<PARAMVALUE NAME="Foo" PARAMTYPE="real32">',
                '<VALUE.ARRAY>',
                '<VALUE>1.2345678901</VALUE>',
                '</VALUE.ARRAY>',
                '</PARAMVALUE>',
            )
        ),
        None, None, True
    ),
    (
        "Array parameter as value with real32 type, value larger 1 without "
        "exponent",
        dict(
            obj=CIMParameter(
                'Foo', type='real32', value=[42.0],
                is_array=True,
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                '<PARAMVALUE NAME="Foo" PARAMTYPE="real32">',
                '<VALUE.ARRAY>',
                '<VALUE>42.0</VALUE>',
                '</VALUE.ARRAY>',
                '</PARAMVALUE>',
            )
        ),
        None, None, True
    ),
    (
        "Array parameter as value with real32 type, value has one entry with "
        "small negative exponent",
        dict(
            obj=CIMParameter(
                'Foo', type='real32', value=[-42.0E-3],
                is_array=True,
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                '<PARAMVALUE NAME="Foo" PARAMTYPE="real32">',
                '<VALUE.ARRAY>',
                '<VALUE>-0.042</VALUE>',
                '</VALUE.ARRAY>',
                '</PARAMVALUE>',
            )
        ),
        None, None, True
    ),
    (
        "Array parameter as value with real32 type, value has one entry with "
        "small positive exponent",
        dict(
            obj=CIMParameter(
                'Foo', type='real32', value=[-42.0E+3],
                is_array=True,
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                '<PARAMVALUE NAME="Foo" PARAMTYPE="real32">',
                '<VALUE.ARRAY>',
                '<VALUE>-42000.0</VALUE>',
                '</VALUE.ARRAY>',
                '</PARAMVALUE>',
            )
        ),
        None, None, True
    ),
    (
        "Array parameter as value with real32 type, value has one entry with "
        "large negative exponent",
        dict(
            obj=CIMParameter(
                'Foo', type='real32', value=[-42.0E-30],
                is_array=True,
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                '<PARAMVALUE NAME="Foo" PARAMTYPE="real32">',
                '<VALUE.ARRAY>',
                '<VALUE>-4.2E-29</VALUE>',
                '</VALUE.ARRAY>',
                '</PARAMVALUE>',
            )
        ),
        None, None, True
    ),
    (
        "Array parameter as value with real32 type, value has one entry with "
        "large positive exponent",
        dict(
            obj=CIMParameter(
                'Foo', type='real32', value=[-42.0E+30],
                is_array=True,
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                '<PARAMVALUE NAME="Foo" PARAMTYPE="real32">',
                '<VALUE.ARRAY>',
                '<VALUE>-4.2E+31</VALUE>',
                '</VALUE.ARRAY>',
                '</PARAMVALUE>',
            )
        ),
        None, None, True
    ),
    (
        "Array parameter as value with real32 type, value has one entry with "
        "special value INF",
        dict(
            obj=CIMParameter(
                'Foo', type='real32', value=[float('inf')],
                is_array=True,
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                '<PARAMVALUE NAME="Foo" PARAMTYPE="real32">',
                '<VALUE.ARRAY>',
                '<VALUE>INF</VALUE>',  # must be upper case
                '</VALUE.ARRAY>',
                '</PARAMVALUE>',
            )
        ),
        None, None, True
    ),
    (
        "Array parameter as value with real32 type, value has one entry with "
        "special value -INF",
        dict(
            obj=CIMParameter(
                'Foo', type='real32', value=[float('-inf')],
                is_array=True,
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                '<PARAMVALUE NAME="Foo" PARAMTYPE="real32">',
                '<VALUE.ARRAY>',
                '<VALUE>-INF</VALUE>',  # must be upper case
                '</VALUE.ARRAY>',
                '</PARAMVALUE>',
            )
        ),
        None, None, True
    ),
    (
        "Array parameter as value with real32 type, value has one entry with "
        "special value NaN",
        dict(
            obj=CIMParameter(
                'Foo', type='real32', value=[float('nan')],
                is_array=True,
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                '<PARAMVALUE NAME="Foo" PARAMTYPE="real32">',
                '<VALUE.ARRAY>',
                '<VALUE>NaN</VALUE>',  # must be upper case
                '</VALUE.ARRAY>',
                '</PARAMVALUE>',
            )
        ),
        None, None, True
    ),

    # Array parameters with real64 type
    (
        "Array parameter as declaration with real64 type",
        dict(
            obj=CIMParameter(
                'Foo', type='real64', value=[42],
                is_array=True,
            ),
            kwargs=dict(as_value=False),
            exp_xml_str=(
                '<PARAMETER.ARRAY NAME="Foo" TYPE="real64"/>',
            )
        ),
        None, None, True
    ),
    (
        "Array parameter as value with real64 type, value NULL",
        dict(
            obj=CIMParameter(
                'Foo', type='real64', value=None,
                is_array=True,
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                '<PARAMVALUE NAME="Foo" PARAMTYPE="real64"/>',
            )
        ),
        None, None, True
    ),
    (
        "Array parameter as value with real64 type, value empty array",
        dict(
            obj=CIMParameter(
                'Foo', type='real64', value=[],
                is_array=True,
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                '<PARAMVALUE NAME="Foo" PARAMTYPE="real64">',
                '<VALUE.ARRAY/>',
                '</PARAMVALUE>',
            )
        ),
        None, None, True
    ),
    (
        "Array parameter as value with real64 type, value has one entry NULL",
        dict(
            obj=CIMParameter(
                'Foo', type='real64', value=[None],
                is_array=True,
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                '<PARAMVALUE NAME="Foo" PARAMTYPE="real64">',
                '<VALUE.ARRAY>',
                '<VALUE.NULL/>',
                '</VALUE.ARRAY>',
                '</PARAMVALUE>',
            )
        ),
        None, None, True
    ),
    (
        "Array parameter as value with real64 type, value between 0 and 1",
        dict(
            obj=CIMParameter(
                'Foo', type='real64', value=[0.42],
                is_array=True,
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                '<PARAMVALUE NAME="Foo" PARAMTYPE="real64">',
                '<VALUE.ARRAY>',
                '<VALUE>0.42</VALUE>',
                '</VALUE.ARRAY>',
                '</PARAMVALUE>',
            )
        ),
        None, None, False  # py27: 0.41999999999999998
    ),
    (
        "Array parameter as value with real64 type, value has one entry with "
        "max number of significant digits (17)",
        dict(
            obj=CIMParameter(
                'Foo', type='real64', value=[1.2345678901234567],
                is_array=True,
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                '<PARAMVALUE NAME="Foo" PARAMTYPE="real64">',
                '<VALUE.ARRAY>',
                '<VALUE>1.2345678901234567</VALUE>',
                '</VALUE.ARRAY>',
                '</PARAMVALUE>',
            )
        ),
        None, None, True
    ),
    (
        "Array parameter as value with real64 type, value has one entry "
        "larger 1 without exponent",
        dict(
            obj=CIMParameter(
                'Foo', type='real64', value=[42.0],
                is_array=True,
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                '<PARAMVALUE NAME="Foo" PARAMTYPE="real64">',
                '<VALUE.ARRAY>',
                '<VALUE>42.0</VALUE>',
                '</VALUE.ARRAY>',
                '</PARAMVALUE>',
            )
        ),
        None, None, True
    ),
    (
        "Array parameter as value with real64 type, value has one entry with "
        "small negative exponent",
        dict(
            obj=CIMParameter(
                'Foo', type='real64', value=[-42.0E-3],
                is_array=True,
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                '<PARAMVALUE NAME="Foo" PARAMTYPE="real64">',
                '<VALUE.ARRAY>',
                '<VALUE>-0.042</VALUE>',
                '</VALUE.ARRAY>',
                '</PARAMVALUE>',
            )
        ),
        None, None, False  # py27: -0.042000000000000003
    ),
    (
        "Array parameter as value with real64 type, value has one entry with "
        "small positive exponent",
        dict(
            obj=CIMParameter(
                'Foo', type='real64', value=[-42.0E+3],
                is_array=True,
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                '<PARAMVALUE NAME="Foo" PARAMTYPE="real64">',
                '<VALUE.ARRAY>',
                '<VALUE>-42000.0</VALUE>',
                '</VALUE.ARRAY>',
                '</PARAMVALUE>',
            )
        ),
        None, None, True
    ),
    (
        "Array parameter as value with real64 type, value has one entry with "
        "large negative exponent",
        dict(
            obj=CIMParameter(
                'Foo', type='real64', value=[-42.0E-30],
                is_array=True,
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                '<PARAMVALUE NAME="Foo" PARAMTYPE="real64">',
                '<VALUE.ARRAY>',
                '<VALUE>-4.2E-29</VALUE>',
                '</VALUE.ARRAY>',
                '</PARAMVALUE>',
            )
        ),
        None, None, False  # py27: -4.1999999999999998E-29
    ),
    (
        "Array parameter as value with real64 type, value has one entry with "
        "large positive exponent",
        dict(
            obj=CIMParameter(
                'Foo', type='real64', value=[-42.0E+30],
                is_array=True,
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                '<PARAMVALUE NAME="Foo" PARAMTYPE="real64">',
                '<VALUE.ARRAY>',
                '<VALUE>-4.2E+31</VALUE>',
                '</VALUE.ARRAY>',
                '</PARAMVALUE>',
            )
        ),
        None, None, False  # py27: -4.1999999999999996E+31
    ),
    (
        "Array parameter as value with real64 type, special value INF",
        dict(
            obj=CIMParameter(
                'Foo', type='real64', value=[float('inf')],
                is_array=True,
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                '<PARAMVALUE NAME="Foo" PARAMTYPE="real64">',
                '<VALUE.ARRAY>',
                '<VALUE>INF</VALUE>',  # must be upper case
                '</VALUE.ARRAY>',
                '</PARAMVALUE>',
            )
        ),
        None, None, True
    ),
    (
        "Array parameter as value with real64 type, special value -INF",
        dict(
            obj=CIMParameter(
                'Foo', type='real64', value=[float('-inf')],
                is_array=True,
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                '<PARAMVALUE NAME="Foo" PARAMTYPE="real64">',
                '<VALUE.ARRAY>',
                '<VALUE>-INF</VALUE>',  # must be upper case
                '</VALUE.ARRAY>',
                '</PARAMVALUE>',
            )
        ),
        None, None, True
    ),
    (
        "Array parameter as value with real64 type, special value NaN",
        dict(
            obj=CIMParameter(
                'Foo', type='real64', value=[float('nan')],
                is_array=True,
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                '<PARAMVALUE NAME="Foo" PARAMTYPE="real64">',
                '<VALUE.ARRAY>',
                '<VALUE>NaN</VALUE>',  # must be upper case
                '</VALUE.ARRAY>',
                '</PARAMVALUE>',
            )
        ),
        None, None, True
    ),

    # Array parameters with datetime type
    (
        "Array parameter as declaration with datetime type",
        dict(
            obj=CIMParameter(
                'Foo', type='datetime',
                value=[datetime(2014, 9, 22, 10, 49, 20, 524789)],
                is_array=True,
            ),
            kwargs=dict(as_value=False),
            exp_xml_str=(
                '<PARAMETER.ARRAY NAME="Foo" TYPE="datetime"/>',
            )
        ),
        None, None, True
    ),
    (
        "Array parameter as value with datetime type, value NULL",
        dict(
            obj=CIMParameter(
                'Foo', type='datetime', value=None,
                is_array=True,
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                '<PARAMVALUE NAME="Foo" PARAMTYPE="datetime"/>',
            )
        ),
        None, None, True
    ),
    (
        "Array parameter as value with datetime type, value empty array",
        dict(
            obj=CIMParameter(
                'Foo', type='datetime', value=[],
                is_array=True,
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                '<PARAMVALUE NAME="Foo" PARAMTYPE="datetime">',
                '<VALUE.ARRAY/>',
                '</PARAMVALUE>',
            )
        ),
        None, None, True
    ),
    (
        "Array parameter as value with datetime type, value has one entry NULL",
        dict(
            obj=CIMParameter(
                'Foo', type='datetime', value=[None],
                is_array=True,
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                '<PARAMVALUE NAME="Foo" PARAMTYPE="datetime">',
                '<VALUE.ARRAY>',
                '<VALUE.NULL/>',
                '</VALUE.ARRAY>',
                '</PARAMVALUE>',
            )
        ),
        None, None, True
    ),
    (
        "Array parameter as value with datetime type, value has one entry "
        "point in time",
        dict(
            obj=CIMParameter(
                'Foo', type='datetime',
                value=[datetime(2014, 9, 22, 10, 49, 20, 524789)],
                is_array=True,
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                '<PARAMVALUE NAME="Foo" PARAMTYPE="datetime">',
                '<VALUE.ARRAY>',
                '<VALUE>20140922104920.524789+000</VALUE>',
                '</VALUE.ARRAY>',
                '</PARAMVALUE>',
            )
        ),
        None, None, True
    ),
    (
        "Array parameter as value with datetime type, value has one entry "
        "interval",
        dict(
            obj=CIMParameter(
                'Foo', type='datetime',
                value=[timedelta(10, 49, 20)],
                is_array=True,
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                '<PARAMVALUE NAME="Foo" PARAMTYPE="datetime">',
                '<VALUE.ARRAY>',
                '<VALUE>00000010000049.000020:000</VALUE>',
                '</VALUE.ARRAY>',
                '</PARAMVALUE>',
            )
        ),
        None, None, True
    ),

    # Array parameters with reference type
    (
        "Array parameter as declaration with reference type",
        dict(
            obj=CIMParameter(
                'Foo', type='reference',
                value=[CIMInstanceName('CIM_Foo')],
                is_array=True,
            ),
            kwargs=dict(as_value=False),
            exp_xml_str=(
                '<PARAMETER.REFARRAY NAME="Foo"/>',
            )
        ),
        None, None, True
    ),
    (
        "Array parameter as value with reference type, value has one entry "
        "NULL",
        dict(
            obj=CIMParameter(
                'Foo', type='reference', value=None,
                is_array=True,
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                '<PARAMVALUE NAME="Foo" PARAMTYPE="reference"/>',
            )
        ),
        None, None, True
    ),
    (
        "Array parameter as value with reference type, value empty array",
        dict(
            obj=CIMParameter(
                'Foo', type='reference', value=[],
                is_array=True,
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                '<PARAMVALUE NAME="Foo" PARAMTYPE="reference">',
                '<VALUE.REFARRAY/>',
                '</PARAMVALUE>',
            )
        ),
        None, None, True
    ),
    (
        "Array parameter as value with reference type, value has one entry "
        "NULL",
        dict(
            obj=CIMParameter(
                'Foo', type='reference', value=[None],
                is_array=True,
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                '<PARAMVALUE NAME="Foo" PARAMTYPE="reference">',
                '<VALUE.REFARRAY>',
                '<VALUE.NULL/>',
                '</VALUE.REFARRAY>',
                '</PARAMVALUE>',
            )
        ),
        None, None, True
    ),
    (
        "Array parameter as value with reference type, value has one entry "
        "class-name only ref",
        dict(
            obj=CIMParameter(
                'Foo', type='reference',
                value=[CIMInstanceName('CIM_Foo')],
                is_array=True,
            ),
            kwargs=dict(as_value=True),
            exp_xml_str=(
                '<PARAMVALUE NAME="Foo" PARAMTYPE="reference">',
                '<VALUE.REFARRAY>',
                '<VALUE.REFERENCE>',
                '<INSTANCENAME CLASSNAME="CIM_Foo"/>',
                '</VALUE.REFERENCE>',
                '</VALUE.REFARRAY>',
                '</PARAMVALUE>',
            )
        ),
        None, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_CIMPARAMETER_TOCIMXML)
@simplified_test_function
def test_CIMParameter_tocimxml(testcase,
                               obj, kwargs, exp_xml_str):
    """
    Test function for CIMParameter.tocimxml().
    """

    # The code to be tested
    obj_xml = obj.tocimxml(**kwargs)

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None

    obj_xml_str = obj_xml.toxml()
    exp_xml_str = ''.join(exp_xml_str)
    validate_cim_xml_obj(obj, obj_xml_str, exp_xml_str)


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_CIMPARAMETER_TOCIMXML)
@simplified_test_function
def test_CIMParameter_tocimxmlstr(testcase,
                                  obj, kwargs, exp_xml_str):
    """
    Test function for CIMParameter.tocimxmlstr().
    """

    # The code to be tested
    obj_xml_str = obj.tocimxmlstr(**kwargs)

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None

    assert isinstance(obj_xml_str, six.text_type)

    exp_xml_str = ''.join(exp_xml_str)
    validate_cim_xml_obj(obj, obj_xml_str, exp_xml_str)


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_CIMPARAMETER_TOCIMXML)
@simplified_test_function
def test_CIMParameter_tocimxmlstr_indent_int(
        testcase, obj, kwargs, exp_xml_str):
    """
    Test function for CIMParameter.tocimxmlstr() with indent as integer.
    """

    indent = 4
    indent_str = ' ' * indent

    # The code to be tested
    obj_xml_str = obj.tocimxmlstr(indent=indent, **kwargs)

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None

    obj_xml = obj.tocimxml(**kwargs)  # This is tested elsewhere
    exp_xml_str = obj_xml.toprettyxml(indent=indent_str)

    assert obj_xml_str == exp_xml_str, \
        "{0}.tocimxmlstr(indent={1!r}) returns unexpected CIM-XML string". \
        format(obj.__class__.__name__, indent)


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_CIMPARAMETER_TOCIMXML)
@simplified_test_function
def test_CIMParameter_tocimxmlstr_indent_str(
        testcase, obj, kwargs, exp_xml_str):
    """
    Test function for CIMParameter.tocimxmlstr() with indent as string.
    """

    indent = 4
    indent_str = ' ' * indent

    # The code to be tested
    obj_xml_str = obj.tocimxmlstr(indent=indent_str, **kwargs)

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None

    obj_xml = obj.tocimxml(**kwargs)  # This is tested elsewhere
    exp_xml_str = obj_xml.toprettyxml(indent=indent_str)

    assert obj_xml_str == exp_xml_str, \
        "{0}.tocimxmlstr(indent={1!r}) returns unexpected CIM-XML string". \
        format(obj.__class__.__name__, indent_str)


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
    def test_CIMParameter_tomof(  # XXX: Migrate to s.tst.fnc.
            self, desc, obj, indent, exp_result, exp_warn_type, condition):
        # pylint: disable=unused-argument
        """Test function for CIMParameter.tomof()."""

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

    def test_CIMQualifierDeclaration_init_pos_args(self):  # XXX: Mrg. succeeds
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

    scopes1 = NocaseDict(CLASS=True)

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
            "Verify that bytes name and return type are converted to unicode",
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
        (
            "Verify that mismatch between is_array False and array_size is "
            "ignored",
            dict(name=u'FooQual', type=u'string',
                 is_array=False, array_size=4),
            dict(name=u'FooQual', type=u'string',
                 is_array=False, array_size=4),
            None, True
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
    def test_CIMQualifierDeclaration_init_succeeds(  # XXX: Migr. to s.tst.fnc.
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
    def test_CIMQualifierDeclaration_init_fails(  # XXX: Merge with succeeds
            self, desc, kwargs, exp_exc_type, condition):
        # pylint: disable=unused-argument
        """All test cases where CIMQualifierDeclaration.__init__() fails."""

        if not condition:
            pytest.skip("Condition for test case not met")

        with pytest.raises(exp_exc_type):

            # The code to be tested
            CIMQualifierDeclaration(**kwargs)


class CIMQualifierDeclarationCopy(unittest.TestCase):

    def test_CIMQualifierDeclaration_copy(self):  # XXX: Migrate to pytest

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

    def test_CIMQualifierDeclaration_attrs(self):  # XXX: Migrate to pytest

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

    def test_CIMQualifierDeclaration_eq(self):  # XXX: Migrate to pytest
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
    def test_CIMQualifierDeclaration_cmp(self):  # XXX: Implement with pytest
        raise AssertionError("test not implemented")


class CIMQualifierDeclarationSort(unittest.TestCase):

    @unimplemented
    def test_CIMQualifierDeclaration_sort(self):  # XXX: Implement with pytest
        raise AssertionError("test not implemented")


TESTCASES_CIMQUALIFIERDECLARATION_HASH = [

    # Testcases for CIMQualifierDeclaration.__hash__()

    # Each list item is a testcase tuple with these items:
    # * desc: Short testcase description.
    # * kwargs: Keyword arguments for the test function:
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
    TESTCASES_CIMQUALIFIERDECLARATION_HASH)
@simplified_test_function
def test_CIMQualifierDeclaration_hash(testcase,
                                      obj1, obj2, exp_hash_equal):
    """
    Test function for CIMQualifierDeclaration.__hash__().
    """

    # The code to be tested
    hash1 = hash(obj1)
    hash2 = hash(obj2)

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None

    # Double check they are different objects
    assert id(obj1) != id(obj2)

    if exp_hash_equal:
        assert hash1 == hash2
    else:
        assert hash1 != hash2


TESTCASES_CIMQUALIFIERDECLARATION_STR_REPR = [

    # Testcases for CIMQualifierDeclaration.__repr__(),__str__() / repr(),str()

    # Each list item is a testcase tuple with these items:
    # * obj: CIMQualifierDeclaration object to be tested.

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
            scopes=[('CLASS', True)],
            overridable=True,
            tosubclass=True,
            toinstance=False,
            translatable=False)
    ),
]


@pytest.mark.parametrize(
    "obj",
    TESTCASES_CIMQUALIFIERDECLARATION_STR_REPR)
def test_CIMQualifierDeclaration_str(obj):
    """
    Test function for CIMQualifierDeclaration.__str__() / str()
    """

    # The code to be tested
    s = str(obj)

    assert re.match(r'^CIMQualifierDeclaration\(', s)

    exp_name = _format('name={0!A}', obj.name)
    assert exp_name in s

    exp_value = _format('value={0!A}', obj.value)
    assert exp_value in s

    exp_type = _format('type={0!A}', obj.type)
    assert exp_type in s

    exp_is_array = _format('is_array={0!A}', obj.is_array)
    assert exp_is_array in s


@pytest.mark.parametrize(
    "obj",
    TESTCASES_CIMQUALIFIERDECLARATION_STR_REPR)
def test_CIMQualifierDeclaration_repr(obj):
    """
    Test function for CIMQualifierDeclaration.__repr__() / repr()
    """

    # The code to be tested
    r = repr(obj)

    assert re.match(r'^CIMQualifierDeclaration\(', r)

    exp_name = _format('name={0!A}', obj.name)
    assert exp_name in r

    exp_value = _format('value={0!A}', obj.value)
    assert exp_value in r

    exp_type = _format('type={0!A}', obj.type)
    assert exp_type in r

    exp_is_array = _format('is_array={0!A}', obj.is_array)
    assert exp_is_array in r

    exp_array_size = _format('array_size={0!A}', obj.array_size)
    assert exp_array_size in r

    exp_scopes = _format('scopes={0!A}', obj.scopes)
    assert exp_scopes in r

    exp_tosubclass = _format('tosubclass={0!A}', obj.tosubclass)
    assert exp_tosubclass in r

    exp_overridable = _format('overridable={0!A}', obj.overridable)
    assert exp_overridable in r

    exp_translatable = _format('translatable={0!A}', obj.translatable)
    assert exp_translatable in r

    exp_toinstance = _format('toinstance={0!A}', obj.toinstance)
    assert exp_toinstance in r


TESTCASES_CIMQUALIFIERDECLARATION_TOCIMXML = [

    # Testcases for CIMQualifierDeclaration.tocimxml() and tocimxmlstr()

    # Each list item is a testcase tuple with these items:
    # * desc: Short testcase description.
    # * kwargs: Keyword arguments for the test function:
    #   * obj: CIMQualifierDeclaration object to be tested.
    #   * kwargs: Dict of input args for tocimxml() (empty).
    #   * exp_xml_str: Expected CIM-XML string, as a tuple/list of parts.
    # * exp_exc_types: Expected exception type(s), or None.
    # * exp_warn_types: Expected warning type(s), or None.
    # * condition: Boolean condition for testcase to run, or 'pdb' for debugger

    # Tests with name variations
    (
        "Name with ASCII characters, as byte string",
        dict(
            obj=CIMQualifierDeclaration(b'Foo', value=None, type='string'),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="false" NAME="Foo"',
                ' TYPE="string"/>',
            )
        ),
        None, None, True
    ),
    (
        "Name with ASCII characters, as unicode string",
        dict(
            obj=CIMQualifierDeclaration(u'Foo', value=None, type='string'),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="false" NAME="Foo"',
                ' TYPE="string"/>',
            )
        ),
        None, None, True
    ),
    (
        "Name with non-ASCII UCS-2 characters, as byte string",
        dict(
            obj=CIMQualifierDeclaration(
                b'Foo\xC3\xA9', value=None, type='string'
            ),
            kwargs=dict(),
            exp_xml_str=(
                u'<QUALIFIER.DECLARATION ISARRAY="false" NAME="Foo\u00E9"',
                ' TYPE="string"/>',
            )
        ),
        None, None, True
    ),
    (
        "Name with non-ASCII UCS-2 characters, as unicode string",
        dict(
            obj=CIMQualifierDeclaration(
                u'Foo\u00E9', value=None, type='string'
            ),
            kwargs=dict(),
            exp_xml_str=(
                u'<QUALIFIER.DECLARATION ISARRAY="false" NAME="Foo\u00E9"',
                u' TYPE="string"/>',
            )
        ),
        None, None, True
    ),
    (
        "Name with non-UCS-2 characters, as byte string",
        dict(
            obj=CIMQualifierDeclaration(
                b'Foo\xF0\x90\x85\x82', value=None, type='string'
            ),
            kwargs=dict(),
            exp_xml_str=(
                u'<QUALIFIER.DECLARATION ISARRAY="false" NAME="Foo\U00010142"',
                u' TYPE="string"/>',
            )
        ),
        None, None, True
    ),
    (
        "Name with non-UCS-2 characters, as unicode string",
        dict(
            obj=CIMQualifierDeclaration(
                u'Foo\U00010142', value=None, type='string'
            ),
            kwargs=dict(),
            exp_xml_str=(
                u'<QUALIFIER.DECLARATION ISARRAY="false" NAME="Foo\U00010142"',
                u' TYPE="string"/>',
            )
        ),
        None, None, True
    ),

    # Variations of scopes argument
    (
        "QualifierDeclaration with scopes empty",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='boolean', value=None,
                scopes=[],
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="false" NAME="Foo"',
                ' TYPE="boolean"/>',
            )
        ),
        None, None, True
    ),
    (
        "QualifierDeclaration with scopes Association",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='boolean', value=None,
                scopes=[('ASSOCIATION', True)],
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="false" NAME="Foo"',
                ' TYPE="boolean">',
                '<SCOPE ASSOCIATION="true"/>',
                '</QUALIFIER.DECLARATION>',
            )
        ),
        None, None, True
    ),
    (
        "QualifierDeclaration with scopes Association, Property",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='boolean', value=None,
                scopes=[('ASSOCIATION', True), ('PROPERTY', True)],
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="false" NAME="Foo"',
                ' TYPE="boolean">',
                '<SCOPE ASSOCIATION="true" PROPERTY="true"/>',
                '</QUALIFIER.DECLARATION>',
            )
        ),
        None, None, True
    ),
    (
        "QualifierDeclaration with scopes Any",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='boolean', value=None,
                scopes=[('ANY', True)],
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="false" NAME="Foo"',
                ' TYPE="boolean">',
                '<SCOPE ASSOCIATION="true" CLASS="true" INDICATION="true"',
                ' METHOD="true" PARAMETER="true" PROPERTY="true" ',
                'REFERENCE="true"/>',
                '</QUALIFIER.DECLARATION>',
            )
        ),
        None, None, True
    ),

    # Variations of overridable argument
    (
        "QualifierDeclaration with overridable True",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='boolean', value=None,
                overridable=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="false" NAME="Foo"',
                ' OVERRIDABLE="true" TYPE="boolean"/>',
            )
        ),
        None, None, True
    ),
    (
        "QualifierDeclaration with overridable False",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='boolean', value=None,
                overridable=False,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="false" NAME="Foo"',
                ' OVERRIDABLE="false" TYPE="boolean"/>',
            )
        ),
        None, None, True
    ),

    # Variations of tosubclass argument
    (
        "QualifierDeclaration with tosubclass True",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='boolean', value=None,
                tosubclass=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="false" NAME="Foo"',
                ' TOSUBCLASS="true" TYPE="boolean"/>',
            )
        ),
        None, None, True
    ),
    (
        "QualifierDeclaration with tosubclass False",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='boolean', value=None,
                tosubclass=False,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="false" NAME="Foo"',
                ' TOSUBCLASS="false" TYPE="boolean"/>',
            )
        ),
        None, None, True
    ),

    # Variations of toinstance argument
    (
        "QualifierDeclaration with toinstance True",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='boolean', value=None,
                toinstance=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="false" NAME="Foo"',
                ' TOINSTANCE="true" TYPE="boolean"/>',
            )
        ),
        None, None, True
    ),
    (
        "QualifierDeclaration with toinstance False",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='boolean', value=None,
                toinstance=False,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="false" NAME="Foo"',
                ' TOINSTANCE="false" TYPE="boolean"/>',
            )
        ),
        None, None, True
    ),

    # Variations of translatable argument
    (
        "QualifierDeclaration with translatable True",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='boolean', value=None,
                translatable=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="false" NAME="Foo"',
                ' TRANSLATABLE="true" TYPE="boolean"/>',
            )
        ),
        None, None, True
    ),
    (
        "QualifierDeclaration with translatable False",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='boolean', value=None,
                translatable=False,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="false" NAME="Foo"',
                ' TRANSLATABLE="false" TYPE="boolean"/>',
            )
        ),
        None, None, True
    ),

    # Scalar qualifier declarations with boolean type
    (
        "Scalar qualifier declaration with boolean type, value NULL",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='boolean', value=None,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="false" NAME="Foo"',
                ' TYPE="boolean"/>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar qualifier declaration with boolean type, value True",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='boolean', value=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="false" NAME="Foo"',
                ' TYPE="boolean">',
                '<VALUE>TRUE</VALUE>',
                '</QUALIFIER.DECLARATION>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar qualifier declaration with boolean type, value False",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='boolean', value=False,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="false" NAME="Foo"',
                ' TYPE="boolean">',
                '<VALUE>FALSE</VALUE>',
                '</QUALIFIER.DECLARATION>',
            )
        ),
        None, None, True
    ),

    # Scalar qualifier declarations with string type
    (
        "Scalar qualifier declaration with string type, value NULL",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='string', value=None,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="false" NAME="Foo"',
                ' TYPE="string"/>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar qualifier declaration with string type, value has one entry "
        "with ASCII characters",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='string', value='foo',
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="false" NAME="Foo"',
                ' TYPE="string">',
                '<VALUE>foo</VALUE>',
                '</QUALIFIER.DECLARATION>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar qualifier declaration with string type, value has one entry "
        "with non-ASCII UCS-2 characters",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='string', value=u'foo\u00E9',
            ),
            kwargs=dict(),
            exp_xml_str=(
                u'<QUALIFIER.DECLARATION ISARRAY="false" NAME="Foo"',
                u' TYPE="string">',
                u'<VALUE>foo\u00E9</VALUE>',
                u'</QUALIFIER.DECLARATION>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar qualifier declaration with string type, value has one entry "
        "with non-UCS-2 characters",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='string', value=u'foo\U00010142',
            ),
            kwargs=dict(),
            exp_xml_str=(
                u'<QUALIFIER.DECLARATION ISARRAY="false" NAME="Foo"',
                u' TYPE="string">',
                u'<VALUE>foo\U00010142</VALUE>',
                u'</QUALIFIER.DECLARATION>',
            )
        ),
        None, None, True
    ),

    # Scalar qualifier declarations with char16 type
    (
        "Scalar qualifier declaration with char16 type, value NULL",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='char16', value=None,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="false" NAME="Foo"',
                ' TYPE="char16"/>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar qualifier declaration with char16 type, value has one entry "
        "with an ASCII character",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='char16', value='f',
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="false" NAME="Foo"',
                ' TYPE="char16">',
                '<VALUE>f</VALUE>',
                '</QUALIFIER.DECLARATION>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar qualifier declaration with char16 type, value has one entry "
        "with a non-ASCII UCS-2 character",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='char16', value=u'\u00E9',
            ),
            kwargs=dict(),
            exp_xml_str=(
                u'<QUALIFIER.DECLARATION ISARRAY="false" NAME="Foo"',
                u' TYPE="char16">',
                u'<VALUE>\u00E9</VALUE>',
                u'</QUALIFIER.DECLARATION>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar qualifier declaration with char16 type, value has one entry "
        "with non-UCS-2 character "
        "(invalid as per DSP0004, but tolerated by pywbem)",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='char16', value=u'\U00010142',
            ),
            kwargs=dict(),
            exp_xml_str=(
                u'<QUALIFIER.DECLARATION ISARRAY="false" NAME="Foo"',
                u' TYPE="char16">',
                u'<VALUE>\U00010142</VALUE>',
                u'</QUALIFIER.DECLARATION>',
            )
        ),
        None, None, True
    ),

    # Scalar qualifier declarations with uint8 type
    (
        "Scalar qualifier declaration with uint8 type, value NULL",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='uint8', value=None,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="false" NAME="Foo"',
                ' TYPE="uint8"/>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar qualifier declaration with uint8 type, value has one entry in "
        "range",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='uint8', value=42,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="false" NAME="Foo"',
                ' TYPE="uint8">',
                '<VALUE>42</VALUE>',
                '</QUALIFIER.DECLARATION>',
            )
        ),
        None, None, True
    ),

    # Scalar qualifier declarations with uint16 type
    (
        "Scalar qualifier declaration with uint16 type, value NULL",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='uint16', value=None,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="false" NAME="Foo"',
                ' TYPE="uint16"/>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar qualifier declaration with uint16 type, value has one entry "
        "in range",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='uint16', value=1234,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="false" NAME="Foo"',
                ' TYPE="uint16">',
                '<VALUE>1234</VALUE>',
                '</QUALIFIER.DECLARATION>',
            )
        ),
        None, None, True
    ),

    # Scalar qualifier declarations with uint32 type
    (
        "Scalar qualifier declaration with uint32 type, value NULL",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='uint32', value=None,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="false" NAME="Foo"',
                ' TYPE="uint32"/>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar qualifier declaration with uint32 type, value has one entry "
        "in range",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='uint32', value=12345678,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="false" NAME="Foo"',
                ' TYPE="uint32">',
                '<VALUE>12345678</VALUE>',
                '</QUALIFIER.DECLARATION>',
            )
        ),
        None, None, True
    ),

    # Scalar qualifier declarations with uint64 type
    (
        "Scalar qualifier declaration with uint64 type, value NULL",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='uint64', value=None,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="false" NAME="Foo"',
                ' TYPE="uint64"/>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar qualifier declaration with uint64 type, value has one entry "
        "in range",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='uint64', value=123456789012,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="false" NAME="Foo"',
                ' TYPE="uint64">',
                '<VALUE>123456789012</VALUE>',
                '</QUALIFIER.DECLARATION>',
            )
        ),
        None, None, True
    ),

    # Scalar qualifier declarations with sint8 type
    (
        "Scalar qualifier declaration with sint8 type, value NULL",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='sint8', value=None,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="false" NAME="Foo"',
                ' TYPE="sint8"/>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar qualifier declaration with sint8 type, value has one entry "
        "in range",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='sint8', value=-42,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="false" NAME="Foo"',
                ' TYPE="sint8">',
                '<VALUE>-42</VALUE>',
                '</QUALIFIER.DECLARATION>',
            )
        ),
        None, None, True
    ),

    # Scalar qualifier declarations with sint16 type
    (
        "Scalar qualifier declaration with sint16 type, value NULL",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='sint16', value=None,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="false" NAME="Foo"',
                ' TYPE="sint16"/>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar qualifier declaration with sint16 type, value has one entry "
        "in range",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='sint16', value=-1234,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="false" NAME="Foo"',
                ' TYPE="sint16">',
                '<VALUE>-1234</VALUE>',
                '</QUALIFIER.DECLARATION>',
            )
        ),
        None, None, True
    ),

    # Scalar qualifier declarations with sint32 type
    (
        "Scalar qualifier declaration with sint32 type, value NULL",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='sint32', value=None,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="false" NAME="Foo"',
                ' TYPE="sint32"/>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar qualifier declaration with sint32 type, value has one entry "
        "in range",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='sint32', value=-12345678,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="false" NAME="Foo"',
                ' TYPE="sint32">',
                '<VALUE>-12345678</VALUE>',
                '</QUALIFIER.DECLARATION>',
            )
        ),
        None, None, True
    ),

    # Scalar qualifier declarations with sint64 type
    (
        "Scalar qualifier declaration with sint64 type, value NULL",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='sint64', value=None,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="false" NAME="Foo"',
                ' TYPE="sint64"/>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar qualifier declaration with sint64 type, value has one entry "
        "in range",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='sint64', value=-123456789012,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="false" NAME="Foo"',
                ' TYPE="sint64">',
                '<VALUE>-123456789012</VALUE>',
                '</QUALIFIER.DECLARATION>',
            )
        ),
        None, None, True
    ),

    # Scalar qualifier declarations with real32 type
    (
        "Scalar qualifier declaration with real32 type, value NULL",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='real32', value=None,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="false" NAME="Foo"',
                ' TYPE="real32"/>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar qualifier declaration with real32 type, value between 0 and 1",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='real32', value=0.42,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="false" NAME="Foo"',
                ' TYPE="real32">',
                '<VALUE>0.42</VALUE>',
                '</QUALIFIER.DECLARATION>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar qualifier declaration with real32 type, value with max number "
        "of significant digits (11)",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='real32', value=1.2345678901,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="false" NAME="Foo"',
                ' TYPE="real32">',
                '<VALUE>1.2345678901</VALUE>',
                '</QUALIFIER.DECLARATION>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar qualifier declaration with real32 type, value larger 1 "
        "without exponent",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='real32', value=42.0,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="false" NAME="Foo"',
                ' TYPE="real32">',
                '<VALUE>42.0</VALUE>',
                '</QUALIFIER.DECLARATION>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar qualifier declaration with real32 type, value with small "
        "negative exponent",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='real32', value=-42.0E-3,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="false" NAME="Foo"',
                ' TYPE="real32">',
                '<VALUE>-0.042</VALUE>',
                '</QUALIFIER.DECLARATION>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar qualifier declaration with real32 type, value with small "
        "positive exponent",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='real32', value=-42.0E+3,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="false" NAME="Foo"',
                ' TYPE="real32">',
                '<VALUE>-42000.0</VALUE>',
                '</QUALIFIER.DECLARATION>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar qualifier declaration with real32 type, value with large "
        "negative exponent",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='real32', value=-42.0E-30,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="false" NAME="Foo"',
                ' TYPE="real32">',
                '<VALUE>-4.2E-29</VALUE>',
                '</QUALIFIER.DECLARATION>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar qualifier declaration with real32 type, value with large "
        "positive exponent",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='real32', value=-42.0E+30,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="false" NAME="Foo"',
                ' TYPE="real32">',
                '<VALUE>-4.2E+31</VALUE>',
                '</QUALIFIER.DECLARATION>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar qualifier declaration with real32 type, special value INF",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='real32', value=float('inf'),
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="false" NAME="Foo"',
                ' TYPE="real32">',
                '<VALUE>INF</VALUE>',  # must be upper case
                '</QUALIFIER.DECLARATION>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar qualifier declaration with real32 type, special value -INF",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='real32', value=float('-inf'),
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="false" NAME="Foo"',
                ' TYPE="real32">',
                '<VALUE>-INF</VALUE>',  # must be upper case
                '</QUALIFIER.DECLARATION>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar qualifier declaration with real32 type, special value NaN",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='real32', value=float('nan'),
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="false" NAME="Foo"',
                ' TYPE="real32">',
                '<VALUE>NaN</VALUE>',  # must be upper case
                '</QUALIFIER.DECLARATION>',
            )
        ),
        None, None, True
    ),

    # Scalar qualifier declarations with real64 type
    (
        "Scalar qualifier declaration with real64 type, value NULL",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='real64', value=None,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="false" NAME="Foo"',
                ' TYPE="real64"/>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar qualifier declaration with real64 type, value between 0 and 1",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='real64', value=0.42,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="false" NAME="Foo"',
                ' TYPE="real64">',
                '<VALUE>0.42</VALUE>',
                '</QUALIFIER.DECLARATION>',
            )
        ),
        None, None, False  # py27: 0.41999999999999998
    ),
    (
        "Scalar qualifier declaration with real64 type, value with max number "
        "of significant digits (17)",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='real64', value=1.2345678901234567,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="false" NAME="Foo"',
                ' TYPE="real64">',
                '<VALUE>1.2345678901234567</VALUE>',
                '</QUALIFIER.DECLARATION>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar qualifier declaration with real64 type, value larger 1 "
        "without exponent",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='real64', value=42.0,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="false" NAME="Foo"',
                ' TYPE="real64">',
                '<VALUE>42.0</VALUE>',
                '</QUALIFIER.DECLARATION>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar qualifier declaration with real64 type, value with small "
        "negative exponent",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='real64', value=-42.0E-3,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="false" NAME="Foo"',
                ' TYPE="real64">',
                '<VALUE>-0.042</VALUE>',
                '</QUALIFIER.DECLARATION>',
            )
        ),
        None, None, False  # py27: -0.042000000000000003
    ),
    (
        "Scalar qualifier declaration with real64 type, value with small "
        "positive exponent",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='real64', value=-42.0E+3,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="false" NAME="Foo"',
                ' TYPE="real64">',
                '<VALUE>-42000.0</VALUE>',
                '</QUALIFIER.DECLARATION>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar qualifier declaration with real64 type, value with large "
        "negative exponent",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='real64', value=-42.0E-30,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="false" NAME="Foo"',
                ' TYPE="real64">',
                '<VALUE>-4.2E-29</VALUE>',
                '</QUALIFIER.DECLARATION>',
            )
        ),
        None, None, False  # py27: -4.1999999999999998E-29
    ),
    (
        "Scalar qualifier declaration with real64 type, value with large "
        "positive exponent",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='real64', value=-42.0E+30,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="false" NAME="Foo"',
                ' TYPE="real64">',
                '<VALUE>-4.2E+31</VALUE>',
                '</QUALIFIER.DECLARATION>',
            )
        ),
        None, None, False  # py27: -4.1999999999999996E+31
    ),
    (
        "Scalar qualifier declaration with real64 type, special value INF",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='real64', value=float('inf'),
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="false" NAME="Foo"',
                ' TYPE="real64">',
                '<VALUE>INF</VALUE>',  # must be upper case
                '</QUALIFIER.DECLARATION>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar qualifier declaration with real64 type, special value -INF",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='real64', value=float('-inf'),
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="false" NAME="Foo"',
                ' TYPE="real64">',
                '<VALUE>-INF</VALUE>',  # must be upper case
                '</QUALIFIER.DECLARATION>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar qualifier declaration with real64 type, special value NaN",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='real64', value=float('nan'),
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="false" NAME="Foo"',
                ' TYPE="real64">',
                '<VALUE>NaN</VALUE>',  # must be upper case
                '</QUALIFIER.DECLARATION>',
            )
        ),
        None, None, True
    ),

    # Scalar qualifier declarations with datetime type
    (
        "Scalar qualifier declaration with datetime type, value NULL",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='datetime', value=None,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="false" NAME="Foo"',
                ' TYPE="datetime"/>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar qualifier declaration with datetime type, point in time value",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='datetime',
                value=datetime(2014, 9, 22, 10, 49, 20, 524789),
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="false" NAME="Foo"',
                ' TYPE="datetime">',
                '<VALUE>20140922104920.524789+000</VALUE>',
                '</QUALIFIER.DECLARATION>',
            )
        ),
        None, None, True
    ),
    (
        "Scalar qualifier declaration with datetime type, interval value",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='datetime',
                value=timedelta(10, 49, 20),
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="false" NAME="Foo"',
                ' TYPE="datetime">',
                '<VALUE>00000010000049.000020:000</VALUE>',
                '</QUALIFIER.DECLARATION>',
            )
        ),
        None, None, True
    ),

    # QualifierDeclarations with reference type are not allowed as per DSP0004

    # Array qualifier declarations with boolean type
    (
        "Array qualifier declaration with boolean type, value is NULL",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='boolean', value=None,
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="true" NAME="Foo"',
                ' TYPE="boolean"/>',
            )
        ),
        None, None, True
    ),
    (
        "Array qualifier declaration with boolean type, value is empty array",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='boolean', value=[],
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="true" NAME="Foo"',
                ' TYPE="boolean">',
                '<VALUE.ARRAY/>',
                '</QUALIFIER.DECLARATION>',
            )
        ),
        None, None, True
    ),
    (
        "Array qualifier declaration with boolean type, value has one entry "
        "NULL",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='boolean', value=[None],
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="true" NAME="Foo"',
                ' TYPE="boolean">',
                '<VALUE.ARRAY>',
                '<VALUE.NULL/>',
                '</VALUE.ARRAY>',
                '</QUALIFIER.DECLARATION>',
            )
        ),
        None, None, True
    ),
    (
        "Array qualifier declaration with boolean type, value has one entry "
        "True",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='boolean', value=[True],
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="true" NAME="Foo"',
                ' TYPE="boolean">',
                '<VALUE.ARRAY>',
                '<VALUE>TRUE</VALUE>',
                '</VALUE.ARRAY>',
                '</QUALIFIER.DECLARATION>',
            )
        ),
        None, None, True
    ),
    (
        "Array qualifier declaration with boolean type, value has one entry "
        "False",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='boolean', value=[False],
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="true" NAME="Foo"',
                ' TYPE="boolean">',
                '<VALUE.ARRAY>',
                '<VALUE>FALSE</VALUE>',
                '</VALUE.ARRAY>',
                '</QUALIFIER.DECLARATION>',
            )
        ),
        None, None, True
    ),

    # Array qualifier declarations with string type
    (
        "Array qualifier declaration with string type, value is NULL",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='string', value=None,
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="true" NAME="Foo"',
                ' TYPE="string"/>',
            )
        ),
        None, None, True
    ),
    (
        "Array qualifier declaration with string type, value is empty array",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='string', value=[],
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="true" NAME="Foo"',
                ' TYPE="string">',
                '<VALUE.ARRAY/>',
                '</QUALIFIER.DECLARATION>',
            )
        ),
        None, None, True
    ),
    (
        "Array qualifier declaration with string type, value has one entry "
        "NULL",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='string', value=[None],
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="true" NAME="Foo"',
                ' TYPE="string">',
                '<VALUE.ARRAY>',
                '<VALUE.NULL/>',
                '</VALUE.ARRAY>',
                '</QUALIFIER.DECLARATION>',
            )
        ),
        None, None, True
    ),
    (
        "Array qualifier declaration with string type, value has one entry "
        "with ASCII characters",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='string', value=['foo'],
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="true" NAME="Foo"',
                ' TYPE="string">',
                '<VALUE.ARRAY>',
                '<VALUE>foo</VALUE>',
                '</VALUE.ARRAY>',
                '</QUALIFIER.DECLARATION>',
            )
        ),
        None, None, True
    ),
    (
        "Array qualifier declaration with string type, value has one entry "
        "with non-ASCII UCS-2 characters",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='string', value=[u'foo\u00E9'],
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                u'<QUALIFIER.DECLARATION ISARRAY="true" NAME="Foo"',
                ' TYPE="string">',
                u'<VALUE.ARRAY>',
                u'<VALUE>foo\u00E9</VALUE>',
                u'</VALUE.ARRAY>',
                u'</QUALIFIER.DECLARATION>',
            )
        ),
        None, None, True
    ),
    (
        "Array qualifier declaration with string type, value has one entry "
        "with non-UCS-2 characters",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='string', value=[u'foo\U00010142'],
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                u'<QUALIFIER.DECLARATION ISARRAY="true" NAME="Foo"',
                ' TYPE="string">',
                u'<VALUE.ARRAY>',
                u'<VALUE>foo\U00010142</VALUE>',
                u'</VALUE.ARRAY>',
                u'</QUALIFIER.DECLARATION>',
            )
        ),
        None, None, True
    ),

    # Array qualifier declarations with char16 type
    (
        "Array qualifier declaration with char16 type, value is NULL",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='char16', value=None,
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="true" NAME="Foo"',
                ' TYPE="char16"/>',
            )
        ),
        None, None, True
    ),
    (
        "Array qualifier declaration with char16 type, value is empty array",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='char16', value=[],
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="true" NAME="Foo"',
                ' TYPE="char16">',
                '<VALUE.ARRAY/>',
                '</QUALIFIER.DECLARATION>',
            )
        ),
        None, None, True
    ),
    (
        "Array qualifier declaration with char16 type, value has one entry "
        "NULL",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='char16', value=[None],
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="true" NAME="Foo"',
                ' TYPE="char16">',
                '<VALUE.ARRAY>',
                '<VALUE.NULL/>',
                '</VALUE.ARRAY>',
                '</QUALIFIER.DECLARATION>',
            )
        ),
        None, None, True
    ),
    (
        "Array qualifier declaration with char16 type, value has one entry "
        "with an ASCII character",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='char16', value=['f'],
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="true" NAME="Foo"',
                ' TYPE="char16">',
                '<VALUE.ARRAY>',
                '<VALUE>f</VALUE>',
                '</VALUE.ARRAY>',
                '</QUALIFIER.DECLARATION>',
            )
        ),
        None, None, True
    ),
    (
        "Array qualifier declaration with char16 type, value has one entry "
        "with a non-ASCII UCS-2 character",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='char16', value=[u'\u00E9'],
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                u'<QUALIFIER.DECLARATION ISARRAY="true" NAME="Foo"',
                u' TYPE="char16">',
                u'<VALUE.ARRAY>',
                u'<VALUE>\u00E9</VALUE>',
                u'</VALUE.ARRAY>',
                u'</QUALIFIER.DECLARATION>',
            )
        ),
        None, None, True
    ),
    (
        "Array qualifier declaration with char16 type, value has one entry "
        "with a non-UCS-2 character "
        "(invalid as per DSP0004, but tolerated by pywbem)",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='char16', value=[u'\U00010142'],
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                u'<QUALIFIER.DECLARATION ISARRAY="true" NAME="Foo"',
                u' TYPE="char16">',
                u'<VALUE.ARRAY>',
                u'<VALUE>\U00010142</VALUE>',
                u'</VALUE.ARRAY>',
                u'</QUALIFIER.DECLARATION>',
            )
        ),
        None, None, True
    ),

    # Array qualifier declarations with uint8 type
    (
        "Array qualifier declaration with uint8 type, value is NULL",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='uint8', value=None,
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="true" NAME="Foo"',
                ' TYPE="uint8"/>',
            )
        ),
        None, None, True
    ),
    (
        "Array qualifier declaration with uint8 type, value is empty array",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='uint8', value=[],
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="true" NAME="Foo"',
                ' TYPE="uint8">',
                '<VALUE.ARRAY/>',
                '</QUALIFIER.DECLARATION>',
            )
        ),
        None, None, True
    ),
    (
        "Array qualifier declaration with uint8 type, value has one entry NULL",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='uint8', value=[None],
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="true" NAME="Foo"',
                ' TYPE="uint8">',
                '<VALUE.ARRAY>',
                '<VALUE.NULL/>',
                '</VALUE.ARRAY>',
                '</QUALIFIER.DECLARATION>',
            )
        ),
        None, None, True
    ),
    (
        "Array qualifier declaration with uint8 type, value has one entry in "
        "range",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='uint8', value=[42],
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="true" NAME="Foo"',
                ' TYPE="uint8">',
                '<VALUE.ARRAY>',
                '<VALUE>42</VALUE>',
                '</VALUE.ARRAY>',
                '</QUALIFIER.DECLARATION>',
            )
        ),
        None, None, True
    ),

    # Array qualifier declarations with uint16 type
    (
        "Array qualifier declaration with uint16 type, value is NULL",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='uint16', value=None,
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="true" NAME="Foo"',
                ' TYPE="uint16"/>',
            )
        ),
        None, None, True
    ),
    (
        "Array qualifier declaration with uint16 type, value is empty array",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='uint16', value=[],
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="true" NAME="Foo"',
                ' TYPE="uint16">',
                '<VALUE.ARRAY/>',
                '</QUALIFIER.DECLARATION>',
            )
        ),
        None, None, True
    ),
    (
        "Array qualifier declaration with uint16 type, value has one entry "
        "NULL",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='uint16', value=[None],
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="true" NAME="Foo"',
                ' TYPE="uint16">',
                '<VALUE.ARRAY>',
                '<VALUE.NULL/>',
                '</VALUE.ARRAY>',
                '</QUALIFIER.DECLARATION>',
            )
        ),
        None, None, True
    ),
    (
        "Array qualifier declaration with uint16 type, value has one entry "
        "in range",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='uint16', value=[1234],
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="true" NAME="Foo"',
                ' TYPE="uint16">',
                '<VALUE.ARRAY>',
                '<VALUE>1234</VALUE>',
                '</VALUE.ARRAY>',
                '</QUALIFIER.DECLARATION>',
            )
        ),
        None, None, True
    ),

    # Array qualifier declarations with uint32 type
    (
        "Array qualifier declaration with uint32 type, value is NULL",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='uint32', value=None,
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="true" NAME="Foo"',
                ' TYPE="uint32"/>',
            )
        ),
        None, None, True
    ),
    (
        "Array qualifier declaration with uint32 type, value is empty array",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='uint32', value=[],
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="true" NAME="Foo"',
                ' TYPE="uint32">',
                '<VALUE.ARRAY/>',
                '</QUALIFIER.DECLARATION>',
            )
        ),
        None, None, True
    ),
    (
        "Array qualifier declaration with uint32 type, value has one entry "
        "NULL",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='uint32', value=[None],
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="true" NAME="Foo"',
                ' TYPE="uint32">',
                '<VALUE.ARRAY>',
                '<VALUE.NULL/>',
                '</VALUE.ARRAY>',
                '</QUALIFIER.DECLARATION>',
            )
        ),
        None, None, True
    ),
    (
        "Array qualifier declaration with uint32 type, value has one entry "
        "in range",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='uint32', value=[12345678],
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="true" NAME="Foo"',
                ' TYPE="uint32">',
                '<VALUE.ARRAY>',
                '<VALUE>12345678</VALUE>',
                '</VALUE.ARRAY>',
                '</QUALIFIER.DECLARATION>',
            )
        ),
        None, None, True
    ),

    # Array qualifier declarations with uint64 type
    (
        "Array qualifier declaration with uint64 type, value is NULL",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='uint64', value=None,
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="true" NAME="Foo"',
                ' TYPE="uint64"/>',
            )
        ),
        None, None, True
    ),
    (
        "Array qualifier declaration with uint64 type, value is empty array",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='uint64', value=[],
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="true" NAME="Foo"',
                ' TYPE="uint64">',
                '<VALUE.ARRAY/>',
                '</QUALIFIER.DECLARATION>',
            )
        ),
        None, None, True
    ),
    (
        "Array qualifier declaration with uint64 type, value has one entry "
        "NULL",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='uint64', value=[None],
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="true" NAME="Foo"',
                ' TYPE="uint64">',
                '<VALUE.ARRAY>',
                '<VALUE.NULL/>',
                '</VALUE.ARRAY>',
                '</QUALIFIER.DECLARATION>',
            )
        ),
        None, None, True
    ),
    (
        "Array qualifier declaration with uint64 type, value has one entry "
        "in range",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='uint64', value=[123456789012],
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="true" NAME="Foo"',
                ' TYPE="uint64">',
                '<VALUE.ARRAY>',
                '<VALUE>123456789012</VALUE>',
                '</VALUE.ARRAY>',
                '</QUALIFIER.DECLARATION>',
            )
        ),
        None, None, True
    ),

    # Array qualifier declarations with sint8 type
    (
        "Array qualifier declaration with sint8 type, value is NULL",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='sint8', value=None,
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="true" NAME="Foo"',
                ' TYPE="sint8"/>',
            )
        ),
        None, None, True
    ),
    (
        "Array qualifier declaration with sint8 type, value is empty array",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='sint8', value=[],
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="true" NAME="Foo"',
                ' TYPE="sint8">',
                '<VALUE.ARRAY/>',
                '</QUALIFIER.DECLARATION>',
            )
        ),
        None, None, True
    ),
    (
        "Array qualifier declaration with sint8 type, value has one entry NULL",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='sint8', value=[None],
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="true" NAME="Foo"',
                ' TYPE="sint8">',
                '<VALUE.ARRAY>',
                '<VALUE.NULL/>',
                '</VALUE.ARRAY>',
                '</QUALIFIER.DECLARATION>',
            )
        ),
        None, None, True
    ),
    (
        "Array qualifier declaration with sint8 type, value has one entry "
        "in range",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='sint8', value=[-42],
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="true" NAME="Foo"',
                ' TYPE="sint8">',
                '<VALUE.ARRAY>',
                '<VALUE>-42</VALUE>',
                '</VALUE.ARRAY>',
                '</QUALIFIER.DECLARATION>',
            )
        ),
        None, None, True
    ),

    # Array qualifier declarations with sint16 type
    (
        "Array qualifier declaration with sint16 type, value is NULL",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='sint16', value=None,
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="true" NAME="Foo"',
                ' TYPE="sint16"/>',
            )
        ),
        None, None, True
    ),
    (
        "Array qualifier declaration with sint16 type, value is empty array",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='sint16', value=[],
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="true" NAME="Foo"',
                ' TYPE="sint16">',
                '<VALUE.ARRAY/>',
                '</QUALIFIER.DECLARATION>',
            )
        ),
        None, None, True
    ),
    (
        "Array qualifier declaration with sint16 type, value has one entry "
        "NULL",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='sint16', value=[None],
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="true" NAME="Foo"',
                ' TYPE="sint16">',
                '<VALUE.ARRAY>',
                '<VALUE.NULL/>',
                '</VALUE.ARRAY>',
                '</QUALIFIER.DECLARATION>',
            )
        ),
        None, None, True
    ),
    (
        "Array qualifier declaration with sint16 type, value has one entry "
        "in range",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='sint16', value=[-1234],
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="true" NAME="Foo"',
                ' TYPE="sint16">',
                '<VALUE.ARRAY>',
                '<VALUE>-1234</VALUE>',
                '</VALUE.ARRAY>',
                '</QUALIFIER.DECLARATION>',
            )
        ),
        None, None, True
    ),

    # Array qualifier declarations with sint32 type
    (
        "Array qualifier declaration with sint32 type, value is NULL",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='sint32', value=None,
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="true" NAME="Foo"',
                ' TYPE="sint32"/>',
            )
        ),
        None, None, True
    ),
    (
        "Array qualifier declaration with sint32 type, value is empty array",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='sint32', value=[],
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="true" NAME="Foo"',
                ' TYPE="sint32">',
                '<VALUE.ARRAY/>',
                '</QUALIFIER.DECLARATION>',
            )
        ),
        None, None, True
    ),
    (
        "Array qualifier declaration with sint32 type, value has one entry "
        "NULL",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='sint32', value=[None],
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="true" NAME="Foo"',
                ' TYPE="sint32">',
                '<VALUE.ARRAY>',
                '<VALUE.NULL/>',
                '</VALUE.ARRAY>',
                '</QUALIFIER.DECLARATION>',
            )
        ),
        None, None, True
    ),
    (
        "Array qualifier declaration with sint32 type, value has one entry "
        "in range",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='sint32', value=[-12345678],
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="true" NAME="Foo"',
                ' TYPE="sint32">',
                '<VALUE.ARRAY>',
                '<VALUE>-12345678</VALUE>',
                '</VALUE.ARRAY>',
                '</QUALIFIER.DECLARATION>',
            )
        ),
        None, None, True
    ),

    # Array qualifier declarations with sint64 type
    (
        "Array qualifier declaration with sint64 type, value is NULL",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='sint64', value=None,
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="true" NAME="Foo"',
                ' TYPE="sint64"/>',
            )
        ),
        None, None, True
    ),
    (
        "Array qualifier declaration with sint64 type, value is empty array",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='sint64', value=[],
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="true" NAME="Foo"',
                ' TYPE="sint64">',
                '<VALUE.ARRAY/>',
                '</QUALIFIER.DECLARATION>',
            )
        ),
        None, None, True
    ),
    (
        "Array qualifier declaration with sint64 type, value has one entry "
        "NULL",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='sint64', value=[None],
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="true" NAME="Foo"',
                ' TYPE="sint64">',
                '<VALUE.ARRAY>',
                '<VALUE.NULL/>',
                '</VALUE.ARRAY>',
                '</QUALIFIER.DECLARATION>',
            )
        ),
        None, None, True
    ),
    (
        "Array qualifier declaration with sint64 type, value has one entry "
        "in range",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='sint64', value=[-123456789012],
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="true" NAME="Foo"',
                ' TYPE="sint64">',
                '<VALUE.ARRAY>',
                '<VALUE>-123456789012</VALUE>',
                '</VALUE.ARRAY>',
                '</QUALIFIER.DECLARATION>',
            )
        ),
        None, None, True
    ),

    # Array qualifier declarations with real32 type
    (
        "Array qualifier declaration with real32 type, value is NULL",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='real32', value=None,
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="true" NAME="Foo"',
                ' TYPE="real32"/>',
            )
        ),
        None, None, True
    ),
    (
        "Array qualifier declaration with real32 type, value is empty array",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='real32', value=[],
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="true" NAME="Foo"',
                ' TYPE="real32">',
                '<VALUE.ARRAY/>',
                '</QUALIFIER.DECLARATION>',
            )
        ),
        None, None, True
    ),
    (
        "Array qualifier declaration with real32 type, value has one entry "
        "NULL",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='real32', value=[None],
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="true" NAME="Foo"',
                ' TYPE="real32">',
                '<VALUE.ARRAY>',
                '<VALUE.NULL/>',
                '</VALUE.ARRAY>',
                '</QUALIFIER.DECLARATION>',
            )
        ),
        None, None, True
    ),
    (
        "Array qualifier declaration with real32 type, value has one entry "
        "between 0 and 1",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='real32', value=[0.42],
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="true" NAME="Foo"',
                ' TYPE="real32">',
                '<VALUE.ARRAY>',
                '<VALUE>0.42</VALUE>',
                '</VALUE.ARRAY>',
                '</QUALIFIER.DECLARATION>',
            )
        ),
        None, None, True
    ),
    (
        "Array qualifier declaration with real32 type, value has one entry "
        "with max number of significant digits (11)",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='real32', value=[1.2345678901],
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="true" NAME="Foo"',
                ' TYPE="real32">',
                '<VALUE.ARRAY>',
                '<VALUE>1.2345678901</VALUE>',
                '</VALUE.ARRAY>',
                '</QUALIFIER.DECLARATION>',
            )
        ),
        None, None, True
    ),
    (
        "Array qualifier declaration with real32 type, value has one entry "
        "larger 1 without exponent",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='real32', value=[42.0],
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="true" NAME="Foo"',
                ' TYPE="real32">',
                '<VALUE.ARRAY>',
                '<VALUE>42.0</VALUE>',
                '</VALUE.ARRAY>',
                '</QUALIFIER.DECLARATION>',
            )
        ),
        None, None, True
    ),
    (
        "Array qualifier declaration with real32 type, value has one entry "
        "with small negative exponent",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='real32', value=[-42.0E-3],
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="true" NAME="Foo"',
                ' TYPE="real32">',
                '<VALUE.ARRAY>',
                '<VALUE>-0.042</VALUE>',
                '</VALUE.ARRAY>',
                '</QUALIFIER.DECLARATION>',
            )
        ),
        None, None, True
    ),
    (
        "Array qualifier declaration with real32 type, value has one entry "
        "with small positive exponent",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='real32', value=[-42.0E+3],
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="true" NAME="Foo"',
                ' TYPE="real32">',
                '<VALUE.ARRAY>',
                '<VALUE>-42000.0</VALUE>',
                '</VALUE.ARRAY>',
                '</QUALIFIER.DECLARATION>',
            )
        ),
        None, None, True
    ),
    (
        "Array qualifier declaration with real32 type, value has one entry "
        "with large negative exponent",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='real32', value=[-42.0E-30],
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="true" NAME="Foo"',
                ' TYPE="real32">',
                '<VALUE.ARRAY>',
                '<VALUE>-4.2E-29</VALUE>',
                '</VALUE.ARRAY>',
                '</QUALIFIER.DECLARATION>',
            )
        ),
        None, None, True
    ),
    (
        "Array qualifier declaration with real32 type, value has one entry "
        "with large positive exponent",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='real32', value=[-42.0E+30],
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="true" NAME="Foo"',
                ' TYPE="real32">',
                '<VALUE.ARRAY>',
                '<VALUE>-4.2E+31</VALUE>',
                '</VALUE.ARRAY>',
                '</QUALIFIER.DECLARATION>',
            )
        ),
        None, None, True
    ),
    (
        "Array qualifier declaration with real32 type, value has one entry "
        "that is special value INF",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='real32', value=[float('inf')],
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="true" NAME="Foo"',
                ' TYPE="real32">',
                '<VALUE.ARRAY>',
                '<VALUE>INF</VALUE>',  # must be upper case
                '</VALUE.ARRAY>',
                '</QUALIFIER.DECLARATION>',
            )
        ),
        None, None, True
    ),
    (
        "Array qualifier declaration with real32 type, value has one entry "
        "that is special value -INF",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='real32', value=[float('-inf')],
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="true" NAME="Foo"',
                ' TYPE="real32">',
                '<VALUE.ARRAY>',
                '<VALUE>-INF</VALUE>',  # must be upper case
                '</VALUE.ARRAY>',
                '</QUALIFIER.DECLARATION>',
            )
        ),
        None, None, True
    ),
    (
        "Array qualifier declaration with real32 type, value has one entry "
        "that is special value NaN",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='real32', value=[float('nan')],
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="true" NAME="Foo"',
                ' TYPE="real32">',
                '<VALUE.ARRAY>',
                '<VALUE>NaN</VALUE>',  # must be upper case
                '</VALUE.ARRAY>',
                '</QUALIFIER.DECLARATION>',
            )
        ),
        None, None, True
    ),

    # Array qualifier declarations with real64 type
    (
        "Array qualifier declaration with real64 type, value is NULL",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='real64', value=None,
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="true" NAME="Foo"',
                ' TYPE="real64"/>',
            )
        ),
        None, None, True
    ),
    (
        "Array qualifier declaration with real64 type, value is empty array",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='real64', value=[],
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="true" NAME="Foo"',
                ' TYPE="real64">',
                '<VALUE.ARRAY/>',
                '</QUALIFIER.DECLARATION>',
            )
        ),
        None, None, True
    ),
    (
        "Array qualifier declaration with real64 type, value has one entry "
        "NULL",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='real64', value=[None],
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="true" NAME="Foo"',
                ' TYPE="real64">',
                '<VALUE.ARRAY>',
                '<VALUE.NULL/>',
                '</VALUE.ARRAY>',
                '</QUALIFIER.DECLARATION>',
            )
        ),
        None, None, True
    ),
    (
        "Array qualifier declaration with real64 type, value has one entry "
        "between 0 and 1",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='real64', value=[0.42],
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="true" NAME="Foo"',
                ' TYPE="real64">',
                '<VALUE.ARRAY>',
                '<VALUE>0.42</VALUE>',
                '</VALUE.ARRAY>',
                '</QUALIFIER.DECLARATION>',
            )
        ),
        None, None, False  # py27: 0.41999999999999998
    ),
    (
        "Array qualifier declaration with real64 type, value has one entry "
        "with max number of significant digits (17)",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='real64', value=[1.2345678901234567],
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="true" NAME="Foo"',
                ' TYPE="real64">',
                '<VALUE.ARRAY>',
                '<VALUE>1.2345678901234567</VALUE>',
                '</VALUE.ARRAY>',
                '</QUALIFIER.DECLARATION>',
            )
        ),
        None, None, True
    ),
    (
        "Array qualifier declaration with real64 type, value has one entry "
        "larger 1 without exponent",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='real64', value=[42.0],
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="true" NAME="Foo"',
                ' TYPE="real64">',
                '<VALUE.ARRAY>',
                '<VALUE>42.0</VALUE>',
                '</VALUE.ARRAY>',
                '</QUALIFIER.DECLARATION>',
            )
        ),
        None, None, True
    ),
    (
        "Array qualifier declaration with real64 type, value has one entry "
        "with small negative exponent",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='real64', value=[-42.0E-3],
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="true" NAME="Foo"',
                ' TYPE="real64">',
                '<VALUE.ARRAY>',
                '<VALUE>-0.042</VALUE>',
                '</VALUE.ARRAY>',
                '</QUALIFIER.DECLARATION>',
            )
        ),
        None, None, False  # py27: -0.042000000000000003
    ),
    (
        "Array qualifier declaration with real64 type, value has one entry "
        "with small positive exponent",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='real64', value=[-42.0E+3],
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="true" NAME="Foo"',
                ' TYPE="real64">',
                '<VALUE.ARRAY>',
                '<VALUE>-42000.0</VALUE>',
                '</VALUE.ARRAY>',
                '</QUALIFIER.DECLARATION>',
            )
        ),
        None, None, True
    ),
    (
        "Array qualifier declaration with real64 type, value has one entry "
        "with large negative exponent",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='real64', value=[-42.0E-30],
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="true" NAME="Foo"',
                ' TYPE="real64">',
                '<VALUE.ARRAY>',
                '<VALUE>-4.2E-29</VALUE>',
                '</VALUE.ARRAY>',
                '</QUALIFIER.DECLARATION>',
            )
        ),
        None, None, False  # py27: -4.1999999999999998E-29
    ),
    (
        "Array qualifier declaration with real64 type, value has one entry "
        "with large positive exponent",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='real64', value=[-42.0E+30],
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="true" NAME="Foo"',
                ' TYPE="real64">',
                '<VALUE.ARRAY>',
                '<VALUE>-4.2E+31</VALUE>',
                '</VALUE.ARRAY>',
                '</QUALIFIER.DECLARATION>',
            )
        ),
        None, None, False  # py27: -4.1999999999999996E+31
    ),
    (
        "Array qualifier declaration with real64 type, value has one entry "
        "that is special value INF",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='real64', value=[float('inf')],
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="true" NAME="Foo"',
                ' TYPE="real64">',
                '<VALUE.ARRAY>',
                '<VALUE>INF</VALUE>',  # must be upper case
                '</VALUE.ARRAY>',
                '</QUALIFIER.DECLARATION>',
            )
        ),
        None, None, True
    ),
    (
        "Array qualifier declaration with real64 type, value has one entry "
        "that is special value -INF",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='real64', value=[float('-inf')],
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="true" NAME="Foo"',
                ' TYPE="real64">',
                '<VALUE.ARRAY>',
                '<VALUE>-INF</VALUE>',  # must be upper case
                '</VALUE.ARRAY>',
                '</QUALIFIER.DECLARATION>',
            )
        ),
        None, None, True
    ),
    (
        "Array qualifier declaration with real64 type, value has one entry "
        "that is special value NaN",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='real64', value=[float('nan')],
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="true" NAME="Foo"',
                ' TYPE="real64">',
                '<VALUE.ARRAY>',
                '<VALUE>NaN</VALUE>',  # must be upper case
                '</VALUE.ARRAY>',
                '</QUALIFIER.DECLARATION>',
            )
        ),
        None, None, True
    ),

    # Array qualifier declarations with datetime type
    (
        "Array qualifier declaration with datetime type, value is NULL",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='datetime', value=None,
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="true" NAME="Foo"',
                ' TYPE="datetime"/>',
            )
        ),
        None, None, True
    ),
    (
        "Array qualifier declaration with datetime type, value is empty array",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='datetime', value=[],
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="true" NAME="Foo"',
                ' TYPE="datetime">',
                '<VALUE.ARRAY/>',
                '</QUALIFIER.DECLARATION>',
            )
        ),
        None, None, True
    ),
    (
        "Array qualifier declaration with datetime type, value has one entry "
        "NULL",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='datetime', value=[None],
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="true" NAME="Foo"',
                ' TYPE="datetime">',
                '<VALUE.ARRAY>',
                '<VALUE.NULL/>',
                '</VALUE.ARRAY>',
                '</QUALIFIER.DECLARATION>',
            )
        ),
        None, None, True
    ),
    (
        "Array qualifier declaration with datetime type, value has one entry "
        "point in time",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='datetime',
                value=[datetime(2014, 9, 22, 10, 49, 20, 524789)],
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="true" NAME="Foo"',
                ' TYPE="datetime">',
                '<VALUE.ARRAY>',
                '<VALUE>20140922104920.524789+000</VALUE>',
                '</VALUE.ARRAY>',
                '</QUALIFIER.DECLARATION>',
            )
        ),
        None, None, True
    ),
    (
        "Array qualifier declaration with datetime type, value has one entry "
        "interval",
        dict(
            obj=CIMQualifierDeclaration(
                'Foo', type='datetime',
                value=[timedelta(10, 49, 20)],
                is_array=True,
            ),
            kwargs=dict(),
            exp_xml_str=(
                '<QUALIFIER.DECLARATION ISARRAY="true" NAME="Foo"',
                ' TYPE="datetime">',
                '<VALUE.ARRAY>',
                '<VALUE>00000010000049.000020:000</VALUE>',
                '</VALUE.ARRAY>',
                '</QUALIFIER.DECLARATION>',
            )
        ),
        None, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_CIMQUALIFIERDECLARATION_TOCIMXML)
@simplified_test_function
def test_CIMQualifierDeclaration_tocimxml(testcase,
                                          obj, kwargs, exp_xml_str):
    """
    Test function for CIMQualifierDeclaration.tocimxml().
    """

    # The code to be tested
    obj_xml = obj.tocimxml(**kwargs)

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None

    obj_xml_str = obj_xml.toxml()
    exp_xml_str = ''.join(exp_xml_str)
    validate_cim_xml_obj(obj, obj_xml_str, exp_xml_str)


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_CIMQUALIFIERDECLARATION_TOCIMXML)
@simplified_test_function
def test_CIMQualifierDeclaration_tocimxmlstr(testcase,
                                             obj, kwargs, exp_xml_str):
    """
    Test function for CIMQualifierDeclaration.tocimxmlstr().
    """

    # The code to be tested
    obj_xml_str = obj.tocimxmlstr(**kwargs)

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None

    assert isinstance(obj_xml_str, six.text_type)

    exp_xml_str = ''.join(exp_xml_str)
    validate_cim_xml_obj(obj, obj_xml_str, exp_xml_str)


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_CIMQUALIFIERDECLARATION_TOCIMXML)
@simplified_test_function
def test_CIMQualifierDeclaration_tocimxmlstr_indent_int(
        testcase, obj, kwargs, exp_xml_str):
    """
    Test function for CIMQualifierDeclaration.tocimxmlstr() with indent as
    integer.
    """

    indent = 4
    indent_str = ' ' * indent

    # The code to be tested
    obj_xml_str = obj.tocimxmlstr(indent=indent, **kwargs)

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None

    obj_xml = obj.tocimxml(**kwargs)  # This is tested elsewhere
    exp_xml_str = obj_xml.toprettyxml(indent=indent_str)

    assert obj_xml_str == exp_xml_str, \
        "{0}.tocimxmlstr(indent={1!r}) returns unexpected CIM-XML string". \
        format(obj.__class__.__name__, indent)


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_CIMQUALIFIERDECLARATION_TOCIMXML)
@simplified_test_function
def test_CIMQualifierDeclaration_tocimxmlstr_indent_str(
        testcase, obj, kwargs, exp_xml_str):
    """
    Test function for CIMQualifierDeclaration.tocimxmlstr() with indent as
    string.
    """

    indent = 4
    indent_str = ' ' * indent

    # The code to be tested
    obj_xml_str = obj.tocimxmlstr(indent=indent_str, **kwargs)

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None

    obj_xml = obj.tocimxml(**kwargs)  # This is tested elsewhere
    exp_xml_str = obj_xml.toprettyxml(indent=indent_str)

    assert obj_xml_str == exp_xml_str, \
        "{0}.tocimxmlstr(indent={1!r}) returns unexpected CIM-XML string". \
        format(obj.__class__.__name__, indent_str)


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
            "string array of variable size that has an empty array value",
            CIMQualifierDeclaration(
                name='Q1',
                type='string',
                is_array=True,
                array_size=None,
                value=[],
            ),
            u"""\
Qualifier Q1 : string[] = {  },
    Scope();
""",
            None, CHECK_0_12_0
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
                scopes=[('CLASS', True)],
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
                scopes=[('ANY', True)],
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
    def test_CIMQualifierDeclaration_tomof(  # XXX: Migrate to s.tst.fnc.
            self, desc, obj, exp_result, exp_warn_type, condition):
        # pylint: disable=unused-argument
        """Test function for CIMQualifierDeclaration.tomof()."""

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
    def test_tocimxml(self):  # XXX: Implement with pytest
        # (bool, invalid array, other invalid cases)
        raise AssertionError("test not implemented")


class ToCIMObj(unittest.TestCase):

    def test_tocimobj(self):  # XXX: Migrate to pytest

        path = tocimobj(
            'reference',
            "Acme_OS.Name=\"acmeunit\",SystemName=\"UnixHost\"")
        self.assertTrue(isinstance(path, CIMInstanceName))
        self.assertEqual(path.classname, 'Acme_OS')
        self.assertEqual(path['Name'], 'acmeunit')
        self.assertEqual(path['SystemName'], 'UnixHost')
        self.assertEqual(len(path.keybindings), 2)
        self.assertTrue(path.namespace is None)
        self.assertTrue(path.host is None)

        path = tocimobj(
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

        path = tocimobj(
            'reference',
            'HTTP://CIMOM_host/root/CIMV2:CIM_Disk.key1="value1"')
        self.assertTrue(isinstance(path, CIMInstanceName))
        self.assertEqual(path.namespace, 'root/CIMV2')
        self.assertEqual(path.host, 'CIMOM_host')
        self.assertEqual(path.classname, 'CIM_Disk')
        self.assertEqual(path['key1'], 'value1')
        self.assertEqual(len(path.keybindings), 1)

        path = tocimobj(
            'reference',
            "ex_sampleClass.label1=9921,label2=8821")
        self.assertTrue(isinstance(path, CIMInstanceName))
        self.assertTrue(path.namespace is None)
        self.assertTrue(path.host is None)
        self.assertEqual(path.classname, 'ex_sampleClass')
        self.assertEqual(path['label1'], 9921)
        self.assertEqual(path['label2'], 8821)
        self.assertEqual(len(path.keybindings), 2)

        path = tocimobj('reference', "ex_sampleClass")
        self.assertTrue(isinstance(path, CIMClassName))
        self.assertTrue(path.namespace is None)
        self.assertTrue(path.host is None)
        self.assertEqual(path.classname, 'ex_sampleClass')

        path = tocimobj(
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

        path = tocimobj(
            'reference',
            "X.key1=\"John Smith\",key2=33.3")
        self.assertTrue(isinstance(path, CIMInstanceName))
        self.assertTrue(path.namespace is None)
        self.assertTrue(path.host is None)
        self.assertEqual(path.classname, 'X')
        self.assertEqual(path['key1'], 'John Smith')
        self.assertEqual(path['key2'], 33.3)

        path = tocimobj(
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

    DATETIME1_DT = datetime(2014, 9, 22, 10, 49, 20, 524789)
    datetime1_str = '20140922104920.524789+000'
    DATETIME1_OBJ = CIMDateTime(DATETIME1_DT)

    TIMEDELTA1_TD = timedelta(183, (13 * 60 + 25) * 60 + 42, 234567)
    timedelta1_str = '00000183132542.234567:000'
    TIMEDELTA1_OBJ = CIMDateTime(TIMEDELTA1_TD)

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

        (DATETIME1_DT, None, DATETIME1_OBJ, None, CHECK_0_12_0),
        (TIMEDELTA1_TD, None, TIMEDELTA1_OBJ, None, CHECK_0_12_0),

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

        (DATETIME1_DT, 'datetime', DATETIME1_OBJ, None, CHECK_0_12_0),
        (datetime1_str, 'datetime', DATETIME1_OBJ, None, CHECK_0_12_0),
        (DATETIME1_OBJ, 'datetime', DATETIME1_OBJ, None, CHECK_0_12_0),

        (TIMEDELTA1_TD, 'datetime', TIMEDELTA1_OBJ, None, CHECK_0_12_0),
        (timedelta1_str, 'datetime', TIMEDELTA1_OBJ, None, CHECK_0_12_0),
        (TIMEDELTA1_OBJ, 'datetime', TIMEDELTA1_OBJ, None, CHECK_0_12_0),

        # Test cases where: Type is reference

        (None, 'reference', None, None, CHECK_0_12_0),

        (ref1_str, 'reference', ref1_obj, None, CHECK_0_12_0),
        (ref1_obj, 'reference', ref1_obj, None, CHECK_0_12_0),
        (ref2_obj, 'reference', ref2_obj, None, CHECK_0_12_0),
    ]

    @pytest.mark.parametrize(
        "value, type, exp_obj, exp_warn_type, condition",
        testcases_succeeds)
    def test_cimvalue_succeeds(  # XXX: Migrate to s.tst.fnc.
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
    def test_cimvalue_fails(  # XXX: Merge with succeeds
            self, value, type, exp_exc_type):
        # pylint: disable=redefined-builtin
        """All test cases where cimvalue() fails."""

        if CHECK_0_12_0:
            with pytest.raises(exp_exc_type):

                cimvalue(value, type)


class Test_mofstr(object):  # pylint: disable=too-few-public-methods
    """Test cases for mofstr()."""

    # Default input arguments if not specified in testcase
    # They do not necessarily have to match the default values.
    default_kwargs = dict(
        indent=MOF_INDENT,
        maxline=MAX_MOF_LINE,
        line_pos=0,
        end_space=0,
        avoid_splits=False,
        quote_char=u'"',
    )

    testcases = [
        # Testcases for mofstr().
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
    def test_mofstr(  # XXX: Migrate to s.tst.fnc.
            self, desc, kwargs, exp_result, exp_warn_type, condition):
        # pylint: disable=unused-argument
        """Test function for mofstr()."""

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
                        result = mofstr(**kwargs)

                else:

                    # The code to be tested
                    result = mofstr(**kwargs)

            assert len(rec_warnings) == 1

        else:
            if exp_exc_type:
                with pytest.raises(exp_exc_type):

                    # The code to be tested
                    result = mofstr(**kwargs)

            else:

                # The code to be tested
                result = mofstr(**kwargs)

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
