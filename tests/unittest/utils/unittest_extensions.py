"""
Extensions for unittest module.

The ideas for these extensions are based on functions from the comfychair
module by Martin Pool <mbp@samba.org>.
"""

from __future__ import absolute_import

import re
import os

import six

# pylint: disable=wrong-import-position, wrong-import-order, invalid-name
from ...utils import import_installed
pywbem = import_installed('pywbem')
from pywbem._nocasedict import NocaseDict  # noqa: E402
# pylint: enable=wrong-import-position, wrong-import-order, invalid-name


class RegexpMixin(object):
    """Mixin class for classes derived from unittest.TestCase, providing
    assertion functions for regular expression tests."""

    @staticmethod
    def assert_regexp_contains(text, pattern, msg=None):
        """Assert that a string text *contains* a particular regular expression
        pattern.

        Parameters:
            text         string: string text to be searched
            pattern      string: regular expression
            msg          string: additional message text (normally not needed)

        Raises:
            AssertionError if not matched
          """
        assert re.search(pattern, text), \
            "String text does not contain regexp pattern\n" \
            "    text:    %r\n" \
            "    pattern: %r\n" \
            "%s" % (text, pattern, msg)

    @staticmethod
    def assert_regexp_matches(text, pattern, msg=None):
        """Assert that a string text matches a particular regular expression
        pattern.

        Parameters:
            text         string: string text to be matched
            pattern      string: regular expression
            msg          string: additional message text (normally not needed)

        Raises:
            AssertionError if not matched
          """
        assert re.match(pattern, text), \
            "String text does not match regexp pattern\n" \
            "    text:    %r\n" \
            "    pattern: %r\n" \
            "%s" % (text, pattern, msg)


class FileMixin(object):
    """Mixin class for classes derived from unittest.TestCase, providing
    assertion functions for file related tests."""

    @staticmethod
    def assert_file_exists(filename):
        """Test assert file exists"""
        assert os.path.exists(filename), \
            "File does not exist but should: %s" % filename

    @staticmethod
    def assert_file_not_exists(filename):
        """Test assert file exists but should not"""
        assert not os.path.exists(filename), \
            "File exists but should not: %s" % filename


class CIMObjectMixin(object):
    """
    Mixin class for testing CIM objects.
    """

    @staticmethod
    def assert_CIMInstanceName_attrs(
            obj, classname, keybindings, host=None, namespace=None):
        """
        Verify the attributes of the CIMInstanceName object in `obj` against
        expected values passed as the remaining arguments.
        """
        assert obj.classname == classname
        assert obj.keybindings == keybindings
        assert obj.host == host
        assert obj.namespace == namespace

    @staticmethod
    def assert_CIMProperty_attrs(
            obj, name, value, type_=None, class_origin=None,
            array_size=None, propagated=None, is_array=False,
            reference_class=None, qualifiers=None, embedded_object=None):
        """
        Verify the attributes of the CIMProperty object in `obj` against
        expected values passed as the remaining arguments.
        """
        assert obj.name == name
        assert obj.value == value
        assert obj.type == type_
        assert obj.class_origin == class_origin
        assert obj.array_size == array_size
        assert obj.propagated == propagated
        assert obj.is_array == is_array
        assert obj.reference_class == reference_class
        assert obj.qualifiers == NocaseDict(qualifiers)
        assert obj.embedded_object == embedded_object

    def assert_CIMClass_obj(self, act_class, exp_class):
        """
        Verify that two CIMClass objects are equal.
        """
        assert act_class.classname == exp_class.classname
        context = "class %s" % act_class.classname
        assert act_class.superclass == exp_class.superclass
        self.assert_CIMProperty_dict(
            act_class.properties, exp_class.properties, context)
        self.assert_CIMMethod_dict(
            act_class.methods, exp_class.methods, context)
        self.assert_CIMQualifier_dict(
            act_class.qualifiers, exp_class.qualifiers, context)

    def assert_CIMProperty_dict(self, act_properties, exp_properties, context):
        """
        Verify that two dicts of CIMProperty objects are equal.
        """

        self.assert_dict_keys(act_properties, exp_properties,
                              "%s, property names" % context)
        for propname in act_properties:
            self.assert_CIMProperty_obj(
                act_properties[propname], exp_properties[propname],
                "%s, property %s" % (context, propname))

    def assert_CIMMethod_dict(self, act_methods, exp_methods, context):
        """
        Verify that two dicts of CIMMethod objects are equal.
        """

        self.assert_dict_keys(act_methods, exp_methods,
                              "%s, method names" % context)
        for methname in act_methods:
            self.assert_CIMMethod_obj(
                act_methods[methname], exp_methods[methname],
                "%s, method %s" % (context, methname))

    def assert_CIMParameter_dict(self, act_parameters, exp_parameters, context):
        """
        Verify that two dicts of CIMParameter objects are equal.
        """

        self.assert_dict_keys(act_parameters, exp_parameters,
                              "%s, parameter names" % context)
        for parmname in act_parameters:
            self.assert_CIMParameter_obj(
                act_parameters[parmname], exp_parameters[parmname],
                "%s, parameter %s" % (context, parmname))

    def assert_CIMQualifier_dict(self, act_qualifiers, exp_qualifiers, context):
        """
        Verify that two dicts of CIMQualifier objects are equal.
        """

        self.assert_dict_keys(act_qualifiers, exp_qualifiers,
                              "%s, qualifier names" % context)
        for qualname in act_qualifiers:
            self.assert_CIMQualifier_obj(
                act_qualifiers[qualname], exp_qualifiers[qualname],
                "%s, qualifier %s" % (context, qualname))

    def assert_CIMProperty_obj(self, act_property, exp_property, context):
        """
        Verify that two CIMProperty declaration objects are equal.
        """

        assert act_property.name == exp_property.name, \
            "%s (dict key), name attribute: %s (expected: %s)" % \
            (context, act_property.name, exp_property.name)
        assert act_property.value == exp_property.value, \
            "%s, value attribute: %s (expected: %s)" % \
            (context, act_property.value, exp_property.value)
        assert act_property.type == exp_property.type, \
            "%s, type attribute: %s (expected: %s)" % \
            (context, act_property.type, exp_property.type)
        assert act_property.reference_class == exp_property.reference_class, \
            "%s, reference_class attribute: %s (expected: %s)" % \
            (context,
             act_property.reference_class, exp_property.reference_class)
        assert act_property.embedded_object == exp_property.embedded_object, \
            "%s, embedded_object attribute: %s (expected: %s)" % \
            (context,
             act_property.embedded_object, exp_property.embedded_object)
        assert act_property.is_array == exp_property.is_array, \
            "%s, is_array attribute: %s (expected: %s)" % \
            (context, act_property.is_array, exp_property.is_array)
        assert act_property.array_size == exp_property.array_size, \
            "%s, array_size attribute: %s (expected: %s)" % \
            (context, act_property.array_size, exp_property.array_size)
        assert act_property.class_origin == exp_property.class_origin, \
            "%s, class_origin attribute: %s (expected: %s)" % \
            (context, act_property.class_origin, exp_property.class_origin)
        assert act_property.propagated == exp_property.propagated, \
            "%s, propagated attribute: %s (expected: %s)" % \
            (context, act_property.propagated, exp_property.propagated)
        self.assert_CIMQualifier_dict(
            act_property.qualifiers, exp_property.qualifiers, context)

    def assert_CIMMethod_obj(self, act_method, exp_method, context):
        """
        Verify that two CIMMethod objects are equal.
        """

        assert act_method.name == exp_method.name, \
            "%s (dict key), name attribute: %s (expected: %s)" % \
            (context, act_method.name, exp_method.name)
        assert act_method.return_type == exp_method.return_type, \
            "%s, return_type attribute: %s (expected: %s)" % \
            (context, act_method.return_type, exp_method.return_type)
        assert act_method.class_origin == exp_method.class_origin, \
            "%s, class_origin attribute: %s (expected: %s)" % \
            (context, act_method.class_origin, exp_method.class_origin)
        assert act_method.propagated == exp_method.propagated, \
            "%s, propagated attribute: %s methodmethod (expected: %s)" % \
            (context, act_method.propagated, exp_method.propagated)
        self.assert_CIMParameter_dict(
            act_method.parameters, exp_method.parameters, context)
        self.assert_CIMQualifier_dict(
            act_method.qualifiers, exp_method.qualifiers, context)

    def assert_CIMParameter_obj(self, act_parameter, exp_parameter, context):
        """
        Verify that two CIMParameter objects are equal.
        """

        assert act_parameter.name == exp_parameter.name, \
            "%s (dict key), name attribute: %s (expected: %s)" % \
            (context, act_parameter.name, exp_parameter.name)
        assert act_parameter.type == exp_parameter.type, \
            "%s, type attribute: %s (expected: %s)" % \
            (context, act_parameter.type, exp_parameter.type)
        assert act_parameter.reference_class == exp_parameter.reference_class, \
            "%s, reference_class attribute: %s (expected: %s)" % \
            (context,
             act_parameter.reference_class, exp_parameter.reference_class)
        assert act_parameter.is_array == exp_parameter.is_array, \
            "%s, is_array attribute: %s (expected: %s)" % \
            (context, act_parameter.is_array, exp_parameter.is_array)
        assert act_parameter.array_size == exp_parameter.array_size, \
            "%s, array_size attribute: %s (expected: %s)" % \
            (context, act_parameter.array_size, exp_parameter.array_size)
        self.assert_CIMQualifier_dict(
            act_parameter.qualifiers, exp_parameter.qualifiers, context)

    @staticmethod
    def assert_CIMQualifier_obj(act_qualifier, exp_qualifier, context):
        """
        Verify that two CIMQualifier objects are equal.
        """

        assert act_qualifier.name == exp_qualifier.name, \
            "%s (dict key), name attribute: %s (expected: %s)" % \
            (context, act_qualifier.name, exp_qualifier.name)
        assert act_qualifier.value == exp_qualifier.value, \
            "%s, value attribute: %s (expected: %s)" % \
            (context, act_qualifier.value, exp_qualifier.value)
        assert act_qualifier.type == exp_qualifier.type, \
            "%s, type attribute: %s (expected: %s)" % \
            (context, act_qualifier.type, exp_qualifier.type)
        assert act_qualifier.propagated == exp_qualifier.propagated, \
            "%s, propagated attribute: %s (expected: %s)" % \
            (context, act_qualifier.propagated, exp_qualifier.propagated)
        assert act_qualifier.overridable == exp_qualifier.overridable, \
            "%s, overridable attribute: %s (expected: %s)" % \
            (context, act_qualifier.overridable, exp_qualifier.overridable)
        assert act_qualifier.tosubclass == exp_qualifier.tosubclass, \
            "%s, tosubclass attribute: %s (expected: %s)" % \
            (context, act_qualifier.tosubclass, exp_qualifier.tosubclass)
        assert act_qualifier.toinstance == exp_qualifier.toinstance, \
            "%s, toinstance attribute: %s (expected: %s)" % \
            (context, act_qualifier.toinstance, exp_qualifier.toinstance)
        assert act_qualifier.translatable == exp_qualifier.translatable, \
            "%s, translatable attribute: %s (expected: %s)" % \
            (context, act_qualifier.translatable, exp_qualifier.translatable)

    def assert_dict_keys(self, act_dict, exp_dict, context):
        """
        Verify that two dicts have the same set of keys.
        """
        act_keys = set(act_dict.keys())
        exp_keys = set(exp_dict.keys())
        if act_keys != exp_keys:
            missing_keys = exp_keys - act_keys
            added_keys = act_keys - exp_keys
            msg = "Different sets of %s" % context
            if missing_keys:
                msg += ", missing: %s" % list(missing_keys)
            if added_keys:
                msg += ", added: %s" % list(added_keys)
            self.fail(msg)


def assert_copy(cpy, org):
    """
    Assert that the copied object is a copy of the original object, as follows:

    For mutable types, the copied object must be equal to the original object,
    and they must be different objects.

    For immutable types, the copied object must be equal to the original object,
    but they may be the same object or different objects.

    The determination of mutability in this function is not perfect; it is
    optimized for the types that are used in the tests.
    """
    if isinstance(org, (dict, list)):
        # Mutable
        assert cpy == org
        assert id(cpy) != id(org)
    elif isinstance(org, (tuple, six.string_types, bool, int, type(None))):
        # Immutable
        assert cpy == org
    else:
        raise TypeError("assert_copy() does not support type {}".
                        format(type(org)))
