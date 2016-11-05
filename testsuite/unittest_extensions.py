"""
Extensions for unittest module.

The ideas for these extensions are based on functions from the comfychair
module by Martin Pool <mbp@samba.org>.
"""

from __future__ import absolute_import

import re
import os

from pywbem.cim_obj import NocaseDict


class RegexpMixin(object):
    """Mixin class for classes derived from unittest.TestCase, providing
    assertion functions for regular expression tests."""

    def assertRegexpContains(self, text, pattern, msg=None):
        """Assert that a string text *contains* a particular regular expression
        pattern.

        Parameters:
            text         string: string text to be searched
            pattern      string: regular expression

        Raises:
            AssertionError if not matched
          """
        if not re.search(pattern, text):
            raise AssertionError(
                "String text does not contain regexp pattern\n"
                "    text:    %r\n"
                "    pattern: %r" % (text, pattern))

    def assertRegexpMatches(self, text, pattern, msg=None):
        """Assert that a string text matches a particular regular expression
        pattern.

        Note: This method is provided by unittest starting from Python 2.7.
        For Python 2.6, we need this function here.

        Parameters:
            text         string: string text to be matched
            pattern      string: regular expression

        Raises:
            AssertionError if not matched
          """
        if not re.match(pattern, text):
            raise AssertionError(
                "String text does not match regexp pattern\n"
                "    text:    %r\n"
                "    pattern: %r" % (text, pattern))


class FileMixin(object):
    """Mixin class for classes derived from unittest.TestCase, providing
    assertion functions for file related tests."""

    def assertFileExists(self, filename):
        assert os.path.exists(filename), \
            ("File does not exist but should: %s" % filename)

    def assertFileNotExists(self, filename):
        assert not os.path.exists(filename), \
            ("File exists but should not: %s" % filename)


class CIMObjectMixin(object):
    """Mixin class for classes derived from unittest.TestCase, providing
    assertion functions for CIM object related tests."""

    def assertCIMInstanceName(self, obj, classname, keybindings, host=None,
                              namespace=None):
        """
        Verify the attributes of the CIMInstanceName object in `obj` against
        expected values passed as the remaining arguments.
        """
        self.assertEqual(obj.classname, classname, "classname attribute")
        self.assertEqual(obj.keybindings, keybindings, "keybindings attribute")
        self.assertEqual(obj.host, host, "host attribute")
        self.assertEqual(obj.namespace, namespace, "namespace attribute")

    def assertCIMProperty(self, obj, name, value, type_=None,
                          class_origin=None, array_size=None, propagated=None,
                          is_array=False, reference_class=None, qualifiers=None,
                          embedded_object=None):
        """
        Verify the attributes of the CIMProperty object in `obj` against
        expected values passed as the remaining arguments.
        """
        self.assertEqual(obj.name, name, "name attribute")
        self.assertEqual(obj.value, value, "value attribute")
        self.assertEqual(obj.type, type_, "type attribute")
        self.assertEqual(obj.class_origin, class_origin,
                         "class_origin attribute")
        self.assertEqual(obj.array_size, array_size, "array_size attribute")
        self.assertEqual(obj.propagated, propagated, "propagated attribute")
        self.assertEqual(obj.is_array, is_array, "is_array attribute")
        self.assertEqual(obj.reference_class, reference_class,
                         "reference_class attribute")
        self.assertEqual(obj.qualifiers, NocaseDict(qualifiers),
                         "qualifiers attribute")
        self.assertEqual(obj.embedded_object, embedded_object,
                         "embedded_object attribute")

    def assertEqualCIMClass(self, act_class, exp_class):
        """
        Verify that two CIMClass objects are equal.
        """
        self.assertEqual(act_class.classname,
                         exp_class.classname,
                         "Unexpected classname: %s" % act_class.classname)
        context = "class %s" % act_class.classname
        self.assertEqual(act_class.superclass,
                         exp_class.superclass,
                         "Unexpected superclass: %s" % act_class.superclass)
        self.assertEqualProperties(
            act_class.properties, exp_class.properties,
            context)
        self.assertEqualMethods(
            act_class.methods, exp_class.methods,
            context)
        self.assertEqualQualifiers(
            act_class.qualifiers, exp_class.qualifiers,
            context)

    def assertEqualProperties(self, act_properties, exp_properties, context):
        """
        Verify that two dicts of CIMProperty objects are equal.
        """

        self.assertEqualKeys(act_properties,
                             exp_properties,
                             "%s, property names" % context)
        for propname in act_properties:
            self.assertEqualCIMProperty(
                act_properties[propname], exp_properties[propname],
                "%s, property %s" % (context, propname))

    def assertEqualMethods(self, act_methods, exp_methods, context):
        """
        Verify that two dicts of CIMMethod objects are equal.
        """

        self.assertEqualKeys(act_methods,
                             exp_methods,
                             "%s, method names" % context)
        for methname in act_methods:
            self.assertEqualCIMMethod(
                act_methods[methname], exp_methods[methname],
                "%s, method %s" % (context, methname))

    def assertEqualParameters(self, act_parameters, exp_parameters, context):
        """
        Verify that two dicts of CIMParameter objects are equal.
        """

        self.assertEqualKeys(act_parameters,
                             exp_parameters,
                             "%s, parameter names" % context)
        for parmname in act_parameters:
            self.assertEqualCIMParameter(
                act_parameters[parmname], exp_parameters[parmname],
                "%s, parameter %s" % (context, parmname))

    def assertEqualQualifiers(self, act_qualifiers, exp_qualifiers, context):
        """
        Verify that two dicts of CIMQualifier objects are equal.
        """

        self.assertEqualKeys(act_qualifiers,
                             exp_qualifiers,
                             "%s, qualifier names" % context)
        for qualname in act_qualifiers:
            self.assertEqualCIMQualifier(
                act_qualifiers[qualname], exp_qualifiers[qualname],
                "%s, qualifier %s" % (context, qualname))

    def assertEqualCIMProperty(self, act_property, exp_property, context):
        """
        Verify that two CIMProperty declaration objects are equal.
        """

        self.assertEqual(
            act_property.name, exp_property.name,
            "%s (dict key), name attribute: %s (expected: %s)" %
            (context,
             act_property.name, exp_property.name))
        self.assertEqual(
            act_property.value, exp_property.value,
            "%s, value attribute: %s (expected: %s)" %
            (context,
             act_property.value, exp_property.value))
        self.assertEqual(
            act_property.type, exp_property.type,
            "%s, type attribute: %s (expected: %s)" %
            (context,
             act_property.type, exp_property.type))
        self.assertEqual(
            act_property.reference_class, exp_property.reference_class,
            "%s, reference_class attribute: %s (expected: %s)" %
            (context,
             act_property.reference_class, exp_property.reference_class))
        self.assertEqual(
            act_property.embedded_object, exp_property.embedded_object,
            "%s, embedded_object attribute: %s (expected: %s)" %
            (context,
             act_property.embedded_object, exp_property.embedded_object))
        self.assertEqual(
            act_property.is_array, exp_property.is_array,
            "%s, is_array attribute: %s (expected: %s)" %
            (context,
             act_property.is_array, exp_property.is_array))
        self.assertEqual(
            act_property.array_size, exp_property.array_size,
            "%s, array_size attribute: %s (expected: %s)" %
            (context,
             act_property.array_size, exp_property.array_size))
        self.assertEqual(
            act_property.class_origin, exp_property.class_origin,
            "%s, class_origin attribute: %s (expected: %s)" %
            (context,
             act_property.class_origin, exp_property.class_origin))
        self.assertEqual(
            act_property.propagated, exp_property.propagated,
            "%s, propagated attribute: %s (expected: %s)" %
            (context,
             act_property.propagated, exp_property.propagated))
        self.assertEqualQualifiers(
            act_property.qualifiers, exp_property.qualifiers,
            context)

    def assertEqualCIMMethod(self, act_method, exp_method, context):
        """
        Verify that two CIMMethod objects are equal.
        """

        self.assertEqual(
            act_method.name, exp_method.name,
            "%s (dict key), name attribute: %s (expected: %s)" %
            (context,
             act_method.name, exp_method.name))
        self.assertEqual(
            act_method.return_type, exp_method.return_type,
            "%s, return_type attribute: %s (expected: %s)" %
            (context,
             act_method.return_type, exp_method.return_type))
        self.assertEqual(
            act_method.class_origin, exp_method.class_origin,
            "%s, class_origin attribute: %s (expected: %s)" %
            (context,
             act_method.class_origin, exp_method.class_origin))
        self.assertEqual(
            act_method.propagated, exp_method.propagated,
            "%s, propagated attribute: %s methodmethod (expected: %s)" %
            (context,
             act_method.propagated, exp_method.propagated))
        self.assertEqualParameters(
            act_method.parameters, exp_method.parameters,
            context)
        self.assertEqualQualifiers(
            act_method.qualifiers, exp_method.qualifiers,
            context)

    def assertEqualCIMParameter(self, act_parameter, exp_parameter, context):
        """
        Verify that two CIMParameter objects are equal.
        """

        self.assertEqual(
            act_parameter.name, exp_parameter.name,
            "%s (dict key), name attribute: %s (expected: %s)" %
            (context,
             act_parameter.name, exp_parameter.name))
        self.assertEqual(
            act_parameter.type, exp_parameter.type,
            "%s, type attribute: %s (expected: %s)" %
            (context,
             act_parameter.type, exp_parameter.type))
        self.assertEqual(
            act_parameter.reference_class, exp_parameter.reference_class,
            "%s, reference_class attribute: %s (expected: %s)" %
            (context,
             act_parameter.reference_class, exp_parameter.reference_class))
        self.assertEqual(
            act_parameter.is_array, exp_parameter.is_array,
            "%s, is_array attribute: %s (expected: %s)" %
            (context,
             act_parameter.is_array, exp_parameter.is_array))
        self.assertEqual(
            act_parameter.array_size, exp_parameter.array_size,
            "%s, array_size attribute: %s (expected: %s)" %
            (context,
             act_parameter.array_size, exp_parameter.array_size))
        self.assertEqualQualifiers(
            act_parameter.qualifiers, exp_parameter.qualifiers,
            context)

    def assertEqualCIMQualifier(self, act_qualifier, exp_qualifier, context):
        """
        Verify that two CIMQualifier objects are equal.
        """

        self.assertEqual(
            act_qualifier.name, exp_qualifier.name,
            "%s (dict key), name attribute: %s (expected: %s)" %
            (context,
             act_qualifier.name, exp_qualifier.name))
        self.assertEqual(
            act_qualifier.value, exp_qualifier.value,
            "%s, value attribute: %s (expected: %s)" %
            (context,
             act_qualifier.value, exp_qualifier.value))
        self.assertEqual(
            act_qualifier.type, exp_qualifier.type,
            "%s, type attribute: %s (expected: %s)" %
            (context,
             act_qualifier.type, exp_qualifier.type))
        self.assertEqual(
            act_qualifier.propagated, exp_qualifier.propagated,
            "%s, propagated attribute: %s (expected: %s)" %
            (context,
             act_qualifier.propagated, exp_qualifier.propagated))
        self.assertEqual(
            act_qualifier.overridable, exp_qualifier.overridable,
            "%s, overridable attribute: %s (expected: %s)" %
            (context,
             act_qualifier.overridable, exp_qualifier.overridable))
        self.assertEqual(
            act_qualifier.tosubclass, exp_qualifier.tosubclass,
            "%s, tosubclass attribute: %s (expected: %s)" %
            (context,
             act_qualifier.tosubclass, exp_qualifier.tosubclass))
        self.assertEqual(
            act_qualifier.toinstance, exp_qualifier.toinstance,
            "%s, toinstance attribute: %s (expected: %s)" %
            (context,
             act_qualifier.toinstance, exp_qualifier.toinstance))
        self.assertEqual(
            act_qualifier.translatable, exp_qualifier.translatable,
            "%s, translatable attribute: %s (expected: %s)" %
            (context,
             act_qualifier.translatable, exp_qualifier.translatable))

    def assertEqualKeys(self, act_dict, exp_dict, context):
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
