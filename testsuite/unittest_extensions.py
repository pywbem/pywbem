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
                "String text does not contain regexp pattern\n"\
                "    text:    %r\n"\
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
                "String text does not match regexp pattern\n"\
                "    text:    %r\n"\
                "    pattern: %r" % (text, pattern))

class FileMixin(object):
    """Mixin class for classes derived from unittest.TestCase, providing
    assertion functions for file related tests."""

    def assertFileExists(self, filename):
        assert os.path.exists(filename),\
               ("File does not exist but should: %s" % filename)

    def assertFileNotExists(self, filename):
        assert not os.path.exists(filename),\
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

