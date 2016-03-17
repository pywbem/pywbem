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

# Allows use of lots of single character variable names.
# pylint: disable=invalid-name,missing-docstring,too-many-statements
# pylint: disable=too-many-lines
import re
import inspect
import os.path
from datetime import timedelta, datetime
import unittest
import pytest
import six

from pywbem import cim_obj, cim_types
from pywbem import CIMInstance, CIMInstanceName, CIMClass, CIMClassName, \
                   CIMProperty, CIMMethod, CIMParameter, CIMQualifier, \
                   Uint8, Uint16, Uint32, Uint64, \
                   Sint8, Sint16, Sint32, Sint64,\
                   Real32, Real64, CIMDateTime
from pywbem.cim_obj import NocaseDict

from validate import validate_xml
from unittest_extensions import RegexpMixin, CIMObjectMixin

unimplemented = pytest.mark.skipif(True, reason="test not implemented")


class ValidateTest(unittest.TestCase):
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
        self.assertTrue(
            validate_xml(xml,
                         dtd_directory=os.path.relpath(_MODULE_PATH),
                         root_elem=root_elem),
            'XML validation failed\n'\
            '  Required XML root element: %s\n'\
            '  Generated CIM-XML: %s' % (root_elem, xml))


#class CIMInstanceToMOF(unittest.TestCase):
#    """
#    Test that valid MOF is generated for `CIMInstance` objects.
#    """
#
#    def test_all(self):
#
#        i = CIMInstance('CIM_Foo',
#                        {'MyString': 'string',
#                         'MyUint8': Uint8(0),
#                         'MyUint8array': [Uint8(1), Uint8(2)],
#                         'MyRef': CIMInstanceName('CIM_Bar')})
#
#        imof = i.tomof()
#
#        # Result (with unpredictable order of properties):
#        #   instance of CIM_Foo {
#        #       MyString = "string";
#        #       MyRef = "CIM_Bar";
#        #       MyUint8array = {1, 2};
#        #       MyUint8 = 0;
#        #   };
#
#        m = re.match(
#            r"^\s*instance\s+of\s+CIM_Foo\s*\{"
#            r"(?:\s*(\w+)\s*=\s*.*;){4,4}" # just match the general syntax
#            r"\s*\}\s*;\s*$", imof)
#        if m is None:
#            self.fail("Invalid MOF generated.\n"\
#                      "Instance: %r\n"\
#                      "Generated MOF: %r" % (i, imof))

class CIMInstanceWithEmbeddedInst(unittest.TestCase):
    def test_all(self):

        embed = CIMInstance('CIM_Embedded',
                        {'EbString': 'string',
                         'EbUint8': Uint8(0),
                         'EbUint8array': [Uint8(1), Uint8(2)],
                         'EbRef': CIMInstanceName('CIM_Bar')})

        i = CIMInstance('CIM_Foo',
                        {'MyString': 'string',
                         'MyUint8': Uint8(0),
                         'MyUint8array': [Uint8(1), Uint8(2)],
                         'MyRef': CIMInstanceName('CIM_Bar'),
                         'MyEmbed' : embed,
                         'MyUint32' : Uint32(9999)})

        imof = i.tomof()
        print('{}'.format(imof))



#class CIMPropertyToXML(ValidateTest):
#    """Test valid XML is generated for various CIMProperty objects."""
#
#    def test_all(self):
#
#        # XML root elements for CIM-XML representations of CIMProperty
#        root_elem_CIMProperty_single = 'PROPERTY'
#        root_elem_CIMProperty_array = 'PROPERTY.ARRAY'
#        root_elem_CIMProperty_ref = 'PROPERTY.REFERENCE'
#
#        # Single-valued ordinary properties
#
#        self.validate(CIMProperty('Spotty', None, type='string'),
#                      root_elem_CIMProperty_single)
#
#        self.validate(CIMProperty(u'Name', u'Brad'),
#                      root_elem_CIMProperty_single)
#
#        self.validate(CIMProperty('Age', Uint16(32)),
#                      root_elem_CIMProperty_single)
#
#        self.validate(CIMProperty('Age', Uint16(32),
#                                  qualifiers={'Key':
#                                              CIMQualifier('Key', True)}),
#                      root_elem_CIMProperty_single)
#
#        # Array properties
#
#        self.validate(CIMProperty('Foo', None, 'string', is_array=True),
#                      root_elem_CIMProperty_array)
#
#        self.validate(CIMProperty('Foo', [], 'string'),
#                      root_elem_CIMProperty_array)
#
#        self.validate(CIMProperty('Foo', [Uint8(x) for x in [1, 2, 3]]),
#                      root_elem_CIMProperty_array)
#
#        self.validate(CIMProperty('Foo', [Uint8(x) for x in [1, 2, 3]],
#                                  qualifiers={'Key': CIMQualifier('Key',
#                                                                  True)}),
#                      root_elem_CIMProperty_array)
#
#        # Reference properties
#
#        self.validate(CIMProperty('Foo', None, type='reference'),
#                      root_elem_CIMProperty_ref)
#
#        self.validate(CIMProperty('Foo', CIMInstanceName('CIM_Foo')),
#                      root_elem_CIMProperty_ref)
#
#        self.validate(CIMProperty('Foo',
#                                  CIMInstanceName('CIM_Foo'),
#                                  qualifiers={'Key': CIMQualifier('Key',
#                                                                  True)}),
#                      root_elem_CIMProperty_ref)

#class CIMClassToMOF(unittest.TestCase):
#
#    def test_all(self):
#
#        c = CIMClass(
#            'CIM_Foo',
#            properties={'InstanceID': CIMProperty('InstanceID', None,
#                                                  type='string')})
#
#        c.tomof()



#class MofStr(unittest.TestCase):
#    """Test cases for mofstr()."""
#
#    def _run_single(self, in_value, exp_value):
#        '''
#        Test function for single invocation of mofstr()
#        '''
#
#        ret_value = cim_obj.mofstr(in_value)
#
#        self.assertEqual(ret_value, exp_value)
#
#    def test_all(self):
#        '''
#        Run all tests for mofstr().
#        '''
#
#        self._run_single('', '""')
#        self._run_single('\\', '"\\\\"')
#        self._run_single('"', '"\\""')
#        self._run_single('a"b', '"a\\"b"')
#        # TODO: Enable the following test, once "" is supported.
#        #self._run_single('a""b', '"a\\"\\"b"')
#        self._run_single("'", '"\'"')
#        self._run_single("a'b", '"a\'b"')
#        self._run_single("a''b", '"a\'\'b"')
#        self._run_single("\\'", '"\\\'"')
#        self._run_single('\\"', '"\\""')
#        self._run_single('\r\n\t\b\f', '"\\r\\n\\t\\b\\f"')
#        self._run_single('\\r\\n\\t\\b\\f', '"\\r\\n\\t\\b\\f"')
#        self._run_single('\\_\\+\\v\\h\\j', '"\\_\\+\\v\\h\\j"')
#        self._run_single('a', '"a"')
#        self._run_single('a b', '"a b"')
#        self._run_single(' b', '" b"')
#        self._run_single('a ', '"a "')
#        self._run_single(' ', '" "')
#
#        # pylint: disable=line-too-long
#        #                    |0                                                                     |71
#        # pylint: disable=line-too-long
#        self._run_single('the big brown fox jumps over a big brown fox jumps over a big brown f jumps over a big brown fox',\
#                           '"the big brown fox jumps over a big brown fox jumps over a big brown f "\n       '+\
#                           '"jumps over a big brown fox"')
#        # pylint: disable=line-too-long
#        self._run_single('the big brown fox jumps over a big brown fox jumps over a big brown fo jumps over a big brown fox',\
#                           '"the big brown fox jumps over a big brown fox jumps over a big brown fo "\n       '+\
#                           '"jumps over a big brown fox"')
#        # pylint: disable=line-too-long
#        self._run_single('the big brown fox jumps over a big brown fox jumps over a big brown fox jumps over a big brown fox',\
#                           '"the big brown fox jumps over a big brown fox jumps over a big brown "\n       '+\
#                           '"fox jumps over a big brown fox"')
#        # pylint: disable=line-too-long
#        self._run_single('the big brown fox jumps over a big brown fox jumps over a big brown foxx jumps over a big brown fox',\
#                           '"the big brown fox jumps over a big brown fox jumps over a big brown "\n       '+\
#                           '"foxx jumps over a big brown fox"')
#        # pylint: disable=line-too-long
#        self._run_single('the big brown fox jumps over a big brown fox jumps over a big brown foxxx jumps over a big brown fox',\
#                           '"the big brown fox jumps over a big brown fox jumps over a big brown "\n       '+\
#                           '"foxxx jumps over a big brown fox"')
#        # pylint: disable=line-too-long
#        self._run_single('the_big_brown_fox_jumps_over_a_big_brown_fox_jumps_over_a_big_brown_fox_jumps_over a big brown fox',\
#                           '"the_big_brown_fox_jumps_over_a_big_brown_fox_jumps_over_a_big_brown_fox"\n       '+\
#                           '"_jumps_over a big brown fox"')
#        # pylint: disable=line-too-long
#        self._run_single('the big brown fox jumps over a big brown fox jumps over a big brown fox_jumps_over_a_big_brown_fox',\
#                           '"the big brown fox jumps over a big brown fox jumps over a big brown "\n       '+\
#                           '"fox_jumps_over_a_big_brown_fox"')
#
#        return 0


# Determine the directory where this module is located. This must be done
# before comfychair gets control, because it changes directories.
_MODULE_PATH = os.path.abspath(os.path.dirname(inspect.getfile(ValidateTest)))


if __name__ == '__main__':
    unittest.main()
