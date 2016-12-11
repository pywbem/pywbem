#!/usr/bin/env python
#

""" Test the mof compiler against both locally defined mof and
    a version of the DMTF released Schema.
"""

from __future__ import print_function, absolute_import

import os
from time import time
from zipfile import ZipFile
import unittest
import six
from ply import lex
from pywbem.cim_operations import CIMError
from pywbem.mof_compiler import MOFCompiler, MOFWBEMConnection, MOFParseError
from pywbem.cim_constants import CIM_ERR_FAILED, CIM_ERR_INVALID_PARAMETER, \
    CIM_ERR_INVALID_SUPERCLASS
from pywbem.cim_obj import CIMClass, CIMProperty, CIMQualifier, \
    CIMQualifierDeclaration, CIMDateTime
from pywbem import mof_compiler

from unittest_extensions import CIMObjectMixin

if six.PY2:
    # pylint: disable=wrong-import-order
    from urllib2 import urlopen
else:
    # pylint: disable=wrong-import-order
    from urllib.request import urlopen

# Constants
NAME_SPACE = 'root/test'

SCRIPT_DIR = os.path.dirname(__file__)
SCHEMA_DIR = os.path.join(SCRIPT_DIR, 'schema')
SCHEMA_MOF_DIR = os.path.join(SCHEMA_DIR, 'mof')

# Change the following variables when a new version of the CIM Schema is used.
# Also, manually delete SCHEMA_DIR.
MOF_ZIP_BN = 'cim_schema_2.45.0Final-MOFs.zip'
MOF_ZIP_URL = 'http://www.dmtf.org/standards/cim/cim_schema_v2450/' + \
    MOF_ZIP_BN
SCHEMA_MOF_BN = 'cim_schema_2.45.0.mof'

MOF_ZIP_FN = os.path.join(SCHEMA_DIR, MOF_ZIP_BN)
SCHEMA_MOF_FN = os.path.join(SCHEMA_MOF_DIR, SCHEMA_MOF_BN)

TOTAL_QUALIFIERS = 70       # These may change for each schema release
TOTAL_CLASSES = 1621

TMP_FILE = 'test_mofRoundTripOutput.mof'


def setUpModule():
    """ Setup the unittest. Includes possibly getting the
        schema mof from DMTF web
    """

    print("")

    if not os.path.isdir(SCHEMA_DIR):
        print("Creating directory for CIM Schema archive: %s" % SCHEMA_DIR)
        os.mkdir(SCHEMA_DIR)

    if not os.path.isfile(MOF_ZIP_FN):
        print("Downloading CIM Schema archive from: %s" % MOF_ZIP_URL)
        ufo = urlopen(MOF_ZIP_URL)
        with open(MOF_ZIP_FN, 'w') as fp:
            for data in ufo:
                fp.write(data)

    if not os.path.isdir(SCHEMA_MOF_DIR):
        print("Creating directory for CIM Schema MOF files: %s" %
              SCHEMA_MOF_DIR)
        os.mkdir(SCHEMA_MOF_DIR)

    if not os.path.isfile(SCHEMA_MOF_FN):
        print("Unpacking CIM Schema archive: %s" % MOF_ZIP_FN)
        try:
            zfp = ZipFile(MOF_ZIP_FN, 'r')
            nlist = zfp.namelist()
            for i in range(0, len(nlist)):
                file_ = nlist[i]
                dfile = os.path.join(SCHEMA_MOF_DIR, file_)
                if dfile[-1] == '/':
                    if not os.path.exists(dfile):
                        os.mkdir(dfile)
                else:
                    with open(dfile, 'w+b') as dfp:
                        dfp.write(zfp.read(file_))
        finally:
            zfp.close()


class MOFTest(unittest.TestCase):
    """A base class that creates a MOF compiler instance"""

    def setUp(self):
        """Create the MOF compiler."""

        def moflog(msg):
            """Display message to moflog"""
            print(msg, file=self.logfile)

        moflog_file = os.path.join(SCRIPT_DIR, 'moflog.txt')
        self.logfile = open(moflog_file, 'w')
        self.mofcomp = MOFCompiler(
            MOFWBEMConnection(),
            search_paths=[SCHEMA_MOF_DIR],
            verbose=False,
            log_func=moflog)


class TestFlavors(MOFTest):
    """Test for the various combinations of valid and invalid flavors"""

    def test_valid_flavors(self):
        """Valid flavor combinations compile"""

        mof_str = "Qualifier testoneflavor : boolean = false, scope(class), " \
            "Flavor(DisableOverride);\n"

        self.mofcomp.compile_string(mof_str, NAME_SPACE)

        mof_str = "Qualifier testtwoflav : boolean = false, scope(class), " \
            "Flavor(DisableOverride, ToSubclass);\n"

        self.mofcomp.compile_string(mof_str, NAME_SPACE)

        mof_str = "Qualifier Version : string = null, \n" \
            "Scope(class, association, indication),\n" \
            "Flavor(EnableOverride, Restricted, Translatable);\n"
        self.mofcomp.compile_string(mof_str, NAME_SPACE)

    def test_valid_flavor2(self):
        """Test for case independence of flavor keywords"""

        mof_str = "Qualifier test1 : scope(class),\n" \
            "Flavor(enableoverride, RESTRICTED, Translatable);"
        try:
            self.mofcomp.compile_string(mof_str, NAME_SPACE)
            self.fail("Test must generate exception")
        except MOFParseError:
            pass

    def test_conflicting_flavors1(self):
        """Conflicting flavors should cause exception"""

        mof_str = "Qualifier test1 : scope(class),\n" \
                  "Flavor(DisableOverride, EnableOverride);"
        try:
            self.mofcomp.compile_string(mof_str, NAME_SPACE)
            self.fail("Test must generate exception")
        except MOFParseError:
            pass

    def test_conflicting_flavors2(self):
        """Conflicting flavors should cause exception"""

        mof_str = "Qualifier test1 : scope(class),\n" \
                  "Flavor(Restricted, ToSubclass);"
        try:
            self.mofcomp.compile_string(mof_str, NAME_SPACE)
            self.fail("Test must generate exception")
        except MOFParseError:
            pass

    def test_invalid_flavor1(self):
        """Invalid flavor should cause exception"""

        mof_str = "Qualifier test1 : scope(class),\n" \
                  "Flavor(Restricted, ToSubclass, invalidflavor);"
        try:
            self.mofcomp.compile_string(mof_str, NAME_SPACE)
            self.fail("Test must generate exception")
        except MOFParseError:
            pass

    def test_invalid_flavor2(self):
        """Invalid flavor should cause exception"""

        mof_str = "Qualifier test1 : scope(class),\n" \
                  "Flavor(invalidflavor);"
        try:
            self.mofcomp.compile_string(mof_str, NAME_SPACE)
            self.fail("Test must generate exception")
        except MOFParseError:
            pass


class TestAliases(MOFTest):
    """Test of a mof file that contains aliases"""

    def test_all(self):
        """Execute test using test.mof file"""

        self.mofcomp.compile_file(
            os.path.join(SCRIPT_DIR, 'test.mof'), NAME_SPACE)

    # TODO: ks 4/16 confirm that this actually works other than just compile


class TestSchemaError(MOFTest):
    """Test with errors in the schema"""

    def test_all(self):
        """Test multiple errors. Each test tries to compile a
           specific mof and should result in a specific error
        """
        # TODO ks 4/16 should these become individual tests
        self.mofcomp.parser.search_paths = []
        try:
            self.mofcomp.compile_file(os.path.join(SCHEMA_MOF_DIR,
                                                   'System',
                                                   'CIM_ComputerSystem.mof'),
                                      NAME_SPACE)
        except CIMError as ce:
            self.assertEqual(ce.args[0], CIM_ERR_FAILED)
            self.assertEqual(ce.file_line[0],
                             os.path.join(SCHEMA_MOF_DIR,
                                          'System',
                                          'CIM_ComputerSystem.mof'))
            if ce.file_line[1] != 2:
                print('assert {}'.format(ce.file_line))
            self.assertEqual(ce.file_line[1], 2)

        self.mofcomp.compile_file(os.path.join(SCHEMA_MOF_DIR,
                                               'qualifiers.mof'),
                                  NAME_SPACE)
        try:
            self.mofcomp.compile_file(os.path.join(SCHEMA_MOF_DIR,
                                                   'System',
                                                   'CIM_ComputerSystem.mof'),
                                      NAME_SPACE)
        except CIMError as ce:
            self.assertEqual(ce.args[0], CIM_ERR_INVALID_SUPERCLASS)
            self.assertEqual(ce.file_line[0],
                             os.path.join(
                                 SCHEMA_MOF_DIR,
                                 'System',
                                 'CIM_ComputerSystem.mof'))
            # TODO The following is cim version dependent.
            if ce.file_line[1] != 179:
                print('assertEqual {} line {}'.format(ce,
                                                      ce.file_line[1]))
            self.assertEqual(ce.file_line[1], 179)


class TestSchemaSearch(MOFTest):
    """Test the search attribute for schema in a directory defined
       by search attribute. Searches the SCHEMA_MOF_DIR
    """

    def test_all(self):
        """Test against schema single mof file that is dependent
           on other files in the schema directory
        """
        self.mofcomp.compile_file(os.path.join(SCHEMA_MOF_DIR,
                                               'System',
                                               'CIM_ComputerSystem.mof'),
                                  NAME_SPACE)
        ccs = self.mofcomp.handle.GetClass(
            'CIM_ComputerSystem',
            LocalOnly=False, IncludeQualifiers=True)
        self.assertEqual(ccs.properties['RequestedState'].type, 'uint16')
        self.assertEqual(ccs.properties['Dedicated'].type, 'uint16')
        cele = self.mofcomp.handle.GetClass(
            'CIM_EnabledLogicalElement',
            LocalOnly=False, IncludeQualifiers=True)
        self.assertEqual(cele.properties['RequestedState'].type, 'uint16')

        # TODO ks 4/16 add error test for something not found
        # in schema directory


class TestParseError(MOFTest):
    """Test multiple mof compile errors. Each test should generate
       a defined error.
    """

    def test_error01(self):
        """Test missing statement end comment"""

        _file = os.path.join(SCRIPT_DIR,
                             'testmofs',
                             'parse_error01.mof')
        try:
            self.mofcomp.compile_file(_file, NAME_SPACE)
        except MOFParseError as pe:
            self.assertEqual(pe.file, _file)
            self.assertEqual(pe.lineno, 16)
            self.assertEqual(pe.context[5][1:5], '^^^^')
            self.assertEqual(pe.context[4][1:5], 'size')

    def test_error02(self):
        """Test invalid instance def TODO what is error? ks 6/16"""
        _file = os.path.join(SCRIPT_DIR,
                             'testmofs',
                             'parse_error02.mof')
        try:
            self.mofcomp.compile_file(_file, NAME_SPACE)
        except MOFParseError as pe:
            self.assertEqual(pe.file, _file)
            self.assertEqual(pe.lineno, 6)
            self.assertEqual(pe.context[5][7:13], '^^^^^^')
            self.assertEqual(pe.context[4][7:13], 'weight')

    def test_error03(self):
        """Test invalid mof, extra } character"""

        _file = os.path.join(SCRIPT_DIR,
                             'testmofs',
                             'parse_error03.mof')
        try:
            self.mofcomp.compile_file(_file, NAME_SPACE)
        except MOFParseError as pe:
            self.assertEqual(pe.file, _file)
            self.assertEqual(pe.lineno, 24)
            self.assertEqual(pe.context[5][53], '^')
            self.assertEqual(pe.context[4][53], '}')

    def test_error04(self):
        """Test invalid mof, Pragmas with invalid file definitions."""

        # TODO ks 6/16why does this generate end-of-file rather than more
        # logical error
        _file = os.path.join(SCRIPT_DIR,
                             'testmofs',
                             'parse_error04.mof')
        try:
            self.mofcomp.compile_file(_file, NAME_SPACE)
        except MOFParseError as pe:
            self.assertEqual(pe.msg, 'Unexpected end of file')


class TestPropertyAlternatives(MOFTest):
    """
        Test compile of a class with individual property alternatives
    """

    def test_array_type(self):
        """ Test compile of class with array property"""

        mof_str = "class PyWBEM_TestArray{\n    Uint32 arrayprop[];\n};"
        self.mofcomp.compile_string(mof_str, NAME_SPACE)
        cl = self.mofcomp.handle.GetClass(
            'PyWBEM_TestArray',
            LocalOnly=False, IncludeQualifiers=True)
        self.assertEqual(cl.properties['arrayprop'].type, 'uint32')
        self.assertEqual(cl.properties['arrayprop'].is_array, True)
        self.assertEqual(cl.properties['arrayprop'].array_size, None)

    def test_array_type_w_size(self):
        """ Test compile of class with array property with size"""
        mof_str = "class PyWBEM_TestArray{\n    Uint32 arrayprop[9];\n};"
        self.mofcomp.compile_string(mof_str, NAME_SPACE)
        cl = self.mofcomp.handle.GetClass(
            'PyWBEM_TestArray',
            LocalOnly=False, IncludeQualifiers=True)
        self.assertEqual(cl.properties['arrayprop'].type, 'uint32')
        self.assertEqual(cl.properties['arrayprop'].is_array, True)
        self.assertEqual(cl.properties['arrayprop'].array_size, 9)

    # TODO ks apr 2016 Grow the number of functions to test property
    #      parameter alternatives one by one.


class TestRefs(MOFTest):
    """Test for valid References in mof"""

    def test_all(self):
        """Execute test"""
        self.mofcomp.compile_file(os.path.join(SCRIPT_DIR,
                                               'testmofs',
                                               'test_refs.mof'),
                                  NAME_SPACE)


class TestInstCompile(MOFTest, CIMObjectMixin):
    """ Test the compile of instances defined with a class"""

    def test_good_compile(self):
        """Execute test with file containing class and two instances."""

        self.mofcomp.compile_file(os.path.join(SCRIPT_DIR,
                                               'testmofs',
                                               'test_instance.mof'),
                                  NAME_SPACE)
        test_class = 'EX_AllTypes'
        repo = self.mofcomp.handle

        classes = repo.classes[NAME_SPACE]
        self.assertTrue(test_class in classes)

        ac_class = classes[test_class]
        self.assertTrue(isinstance(ac_class, CIMClass))

        instances = repo.instances[NAME_SPACE]

        self.assertEqual(len(instances), 2)

        for i in instances:
            # both keys must exist
            self.assertTrue('k1' in i)
            self.assertTrue('k2' in i)

            if i['k1'] == 9921 and i['k2'] == 'SampleLabelInner':
                self.assertEqual(i['pui8'], 0)
                self.assertEqual(i['pui16'], 0)
                self.assertEqual(i['pui32'], 0)
                self.assertEqual(i['pui64'], 0)
                self.assertEqual(i['psi8'], 127)
                self.assertEqual(i['psi16'], 32767)
                self.assertEqual(i['psi32'], 2147483647)
                self.assertEqual(i['psi64'], 9223372036854775807)
                self.assertEqual(i['ps'], 'abcdefg')
                self.assertEqual(i['pc'], u"'a'")
                self.assertEqual(i['pb'], False)
                self.assertEqual(i['pdt'],
                                 CIMDateTime("01234567061213.123456:000"))
                self.assertEqual(i['peo'], None)
                self.assertEqual(i['pei'], None)

            elif i['k1'] == 9922 and i['k2'] == 'SampleLabelOuter':
                self.assertEqual(i['pui8'], 255)
                self.assertEqual(i['pui16'], 65535)
                self.assertEqual(i['pui32'], 4294967295)
                self.assertEqual(i['pui64'], 18446744073709551615)
                self.assertEqual(i['psi8'], -128)
                self.assertEqual(i['psi16'], -32768)
                self.assertEqual(i['psi32'], -2147483648)
                self.assertEqual(i['psi64'], -9223372036854775808)
                self.assertEqual(i['ps'], 'abcdefg')
                self.assertEqual(i['pc'], u"'a'")
                self.assertEqual(i['pb'], True)
                self.assertEqual(i['pdt'],
                                 CIMDateTime("20160409061213.123456+120"))
                # self.assertEqual(i['peo'], None)
                # self.assertEqual(i['pei'], None)
            else:
                self.fail('Cannot find required instance k1=%s, k2=%s' %
                          (i['k1'], i['k2']))

    def test_invalid_property(self):
        """Test compile of instance with duplicated property fails"""
        self.mofcomp.compile_file(os.path.join(SCRIPT_DIR,
                                               'testmofs',
                                               'test_instance.mof'),
                                  NAME_SPACE)
        test_class = 'EX_AllTypes'
        repo = self.mofcomp.handle

        classes = repo.classes[NAME_SPACE]
        self.assertTrue(test_class in classes)

        third_instance = 'instance of EX_AllTypes\n' \
                         '{\n' \
                         'k1 = 9923;\n' \
                         'k2 = "SampleLabeldupProperty";' \
                         'pui8 = 0;\n' \
                         'blah = 0;\n};'
        try:
            self.mofcomp.compile_string(third_instance, NAME_SPACE)
            self.fail('Must fail compile with invalid property name')
        except CIMError as ce:
            self.assertEqual(ce.args[0], CIM_ERR_INVALID_PARAMETER)

    def test_dup_property(self):
        """Test compile of instance with duplicated property fails"""
        self.mofcomp.compile_file(os.path.join(SCRIPT_DIR,
                                               'testmofs',
                                               'test_instance.mof'),
                                  NAME_SPACE)
        test_class = 'EX_AllTypes'
        repo = self.mofcomp.handle

        classes = repo.classes[NAME_SPACE]
        self.assertTrue(test_class in classes)

        third_instance = 'instance of EX_AllTypes\n' \
                         '{\n' \
                         'k1 = 9923;\n' \
                         'k2 = "SampleLabeldupProperty";' \
                         'pui8 = 0;\n' \
                         'pui8 = 0;\n};'
        try:
            self.mofcomp.compile_string(third_instance, NAME_SPACE)
            self.fail('Must fail compile with duplicate property name')
        except CIMError as ce:
            self.assertEqual(ce.args[0], CIM_ERR_INVALID_PARAMETER)

    def test_mismatch_property(self):
        """Test compile of instance with duplicated property fails"""
        self.mofcomp.compile_file(os.path.join(SCRIPT_DIR,
                                               'testmofs',
                                               'test_instance.mof'),
                                  NAME_SPACE)
        test_class = 'EX_AllTypes'
        repo = self.mofcomp.handle

        classes = repo.classes[NAME_SPACE]
        self.assertTrue(test_class in classes)

        third_instance = 'instance of EX_AllTypes\n' \
                         '{\n' \
                         'k1 = 9923;\n' \
                         'k2 = "SampleLabeldupProperty";' \
                         'pui8 = "String for unit8";\n' \
                         '};'
        try:
            self.mofcomp.compile_string(third_instance, NAME_SPACE)
            self.fail('Must fail compile with mismatch property name')
        except CIMError as ce:
            self.assertEqual(ce.args[0], CIM_ERR_INVALID_PARAMETER)

    # TODO add test for array value in inst, not scalar


class TestTypes(MOFTest, CIMObjectMixin):
    """Test for all CIM data types in a class mof"""

    def test_all(self):
        """Execute test"""
        self.mofcomp.compile_file(os.path.join(SCRIPT_DIR,
                                               'testmofs',
                                               'test_types.mof'),
                                  NAME_SPACE)

        test_class = 'EX_AllTypes'
        repo = self.mofcomp.handle

        classes = repo.classes[NAME_SPACE]
        self.assertTrue(test_class in classes)

        ac_class = classes[test_class]
        self.assertTrue(isinstance(ac_class, CIMClass))

        # The expected representation of the class must match the MOF
        # in testmofs/test_types.mof.
        exp_ac_properties = {
            # pylint: disable=bad-continuation
            'k1': CIMProperty(
                'k1', None, type='uint32', class_origin=test_class,
                qualifiers={
                    # TODO: Apply issues #203, #205 to flavor parms.
                    'key': CIMQualifier('key', True, overridable=False,
                                        tosubclass=True)
                }),
            # pylint: disable=bad-continuation
            'k2': CIMProperty(
                'k2', None, type='string',
                class_origin=test_class,
                qualifiers={
                    # TODO: Apply issues #203, #205 to flavor parms.
                    'key': CIMQualifier('key', True, overridable=False,
                                        tosubclass=True)
                }),
            'pui8': CIMProperty('pui8', None, type='uint8',
                                class_origin=test_class),
            'pui16': CIMProperty('pui16', None, type='uint16',
                                 class_origin=test_class),
            'pui32': CIMProperty('pui32', None, type='uint32',
                                 class_origin=test_class),
            'pui64': CIMProperty('pui64', None, type='uint64',
                                 class_origin=test_class),
            'psi8': CIMProperty('psi8', None, type='sint8',
                                class_origin=test_class),
            'psi16': CIMProperty('psi16', None, type='sint16',
                                 class_origin=test_class),
            'psi32': CIMProperty('psi32', None, type='sint32',
                                 class_origin=test_class),
            'psi64': CIMProperty('psi64', None, type='sint64',
                                 class_origin=test_class),
            'ps': CIMProperty('ps', None, type='string',
                              class_origin=test_class),
            'pc': CIMProperty('pc', None, type='char16',
                              class_origin=test_class),
            'pb': CIMProperty('pb', None, type='boolean',
                              class_origin=test_class),
            'pdt': CIMProperty('pdt', None, type='datetime',
                               class_origin=test_class),
            'peo': CIMProperty(
                'peo', None, type='string', class_origin=test_class,
                qualifiers={
                    # TODO: Apply issues #203, #205 to flavor parms.
                    'embeddedobject': CIMQualifier(
                        'embeddedobject', True, overridable=False,
                        tosubclass=True, toinstance=None)
                }),
            'pei': CIMProperty(
                'pei', None, type='string', class_origin=test_class,
                qualifiers={
                    # TODO: Apply issues #203, #205 to flavor parms.
                    'embeddedinstance': CIMQualifier(
                        'embeddedinstance', 'EX_AllTypes', overridable=None,
                        tosubclass=None, toinstance=None)
                }),
        }
        exp_ac_class = CIMClass(
            classname='EX_AllTypes',
            properties=exp_ac_properties
        )
        self.assertEqualCIMClass(ac_class, exp_ac_class)


def _build_scope(set_true=None):
    """ Build a basic scope dictionary to be used in building classes
        for tests. Required because the compiler supplies all
        values in the scope list whether true or false
    """
    dict_ = {'CLASS': False, 'ANY': False, 'ASSOCIATION': False,
             'INDICATION': False, 'METHOD': False,
             'PARAMETER': False, 'PROPERTY': False,
             'REFERENCE': False}
    for n in set_true:
        dict_[n] = True
    return dict_


class TestToInstanceFlavor(MOFTest, CIMObjectMixin):
    """ Test variations on use of ToInstance Flavor"""

    def test_no_toinstance_flavor(self):
        """ Test that this is not attached to tosubclass flavor by
            compiler in qualifier decl or in class creation from that
            qualifier.  """

        mof_str = 'Qualifier Tst: boolean = true, Scope(class),'\
                  ' Flavor(ToSubclass);\n' \
                  '[Tst]\n' \
                  'class Py_ToInst{\n' \
                  '};'
        self.mofcomp.compile_string(mof_str, NAME_SPACE)

        # compare qualifier declaration
        scope_def = _build_scope(set_true=['CLASS'])
        qld = self.mofcomp.handle.GetQualifier('Tst')
        cmp_qld = CIMQualifierDeclaration('Tst', 'boolean', value=True,
                                          scopes=scope_def,
                                          tosubclass=True)
        self.assertEqual(qld, cmp_qld)

        # compare classes
        cl = self.mofcomp.handle.GetClass('Py_ToInst',
                                          LocalOnly=False,
                                          IncludeQualifiers=True)

        cmp_cl = CIMClass('Py_ToInst',
                          qualifiers={'Tst': CIMQualifier('Tst', True,
                                                          tosubclass=True)})
        self.assertEqual(cl, cmp_cl)

    def test_no_toinstance_flavor2(self):
        """ Test that this is not attached to tosubclass flavor by
            compiler in qualifier decl or in class creation from that
            qualifier.  """

        mof_str = 'Qualifier Tst: boolean = true, Scope(class),'\
                  ' Flavor(ToSubclass, ToInstance);\n' \
                  '[Tst]\n' \
                  'class Py_ToInst{\n' \
                  '};'
        self.mofcomp.compile_string(mof_str, NAME_SPACE)

        # compare qualifier declaration
        scope_def = _build_scope(set_true=['CLASS'])
        qld = self.mofcomp.handle.GetQualifier('Tst')
        cmp_qld = CIMQualifierDeclaration('Tst', 'boolean', value=True,
                                          scopes=scope_def,
                                          tosubclass=True, toinstance=True)
        self.assertEqual(qld, cmp_qld)

        # compare classes
        cl = self.mofcomp.handle.GetClass('Py_ToInst',
                                          LocalOnly=False,
                                          IncludeQualifiers=True)

        cmp_cl = CIMClass('Py_ToInst',
                          qualifiers={'Tst': CIMQualifier('Tst', True,
                                                          tosubclass=True,
                                                          toinstance=True)})
        self.assertEqual(cl, cmp_cl)


# pylint: disable=too-few-public-methods
class LexErrorToken(lex.LexToken):
    """Class indicating an expected LEX error."""
    # Like lex.LexToken, we set its instance variables from outside
    pass


def _test_log(msg):     # pylint: disable=unused-argument
    """Our log function when testing."""
    pass


class BaseTestLexer(unittest.TestCase):
    """Base class for testcases just for the lexical analyzer."""

    def setUp(self):
        self.mofcomp = MOFCompiler(handle=None, log_func=_test_log)
        self.lexer = self.mofcomp.lexer
        self.last_error_t = None  # saves 't' arg of t_error()

        def test_t_error(t):  # pylint: disable=invalid-name
            """Our replacement for t_error() when testing."""
            self.last_error_t = t
            self.saved_t_error(t)

        self.saved_t_error = mof_compiler.t_error
        mof_compiler.t_error = test_t_error

    def tearDown(self):
        mof_compiler.t_error = self.saved_t_error

    @staticmethod
    def lex_token(type_, value, lineno, lexpos):
        """Return an expected LexToken."""
        tok = lex.LexToken()
        tok.type = type_
        tok.value = value
        tok.lineno = lineno
        tok.lexpos = lexpos
        return tok

    @staticmethod
    def lex_error(value, lineno, lexpos):
        """Return an expected LEX error."""
        tok = LexErrorToken()
        # pylint: disable=attribute-defined-outside-init
        tok.type = None
        tok.value = value
        tok.lineno = lineno
        tok.lexpos = lexpos
        return tok

    def debug_data(self, input_data):
        """For debugging testcases: Print input data and its tokens."""
        print("debug_data: input_data=<%s>" % input_data)
        self.lexer.input(input_data)
        while True:
            tok = self.lexer.token()
            if not tok:
                break  # No more input
            print("debug_data: token=<%s>" % tok)

    def run_assert_lexer(self, input_data, exp_tokens):
        """Run lexer and assert results."""

        # Supply the lexer with input
        self.lexer.input(input_data)

        token_iter = iter(exp_tokens)
        while True:

            # Get next parsed token from lexer,
            # returns None if exhausted
            act_token = self.lexer.token()

            try:
                exp_token = six.next(token_iter)
            except StopIteration:
                exp_token = None  # indicate tokens exhausted

            if act_token is None and exp_token is None:
                break  # successfully came to the end
            elif act_token is None and exp_token is not None:
                self.fail("Not enough tokens found, expected: %r" % exp_token)
            elif act_token is not None and exp_token is None:
                self.fail("Too many tokens found: %r" % act_token)
            else:
                # We have both an expected and an actual token
                if isinstance(exp_token, LexErrorToken):
                    # We expect an error
                    if self.last_error_t is None:
                        self.fail("t_error() was not called as expected, "
                                  "actual token: %r" % act_token)
                    else:
                        self.assertTrue(
                            self.last_error_t.type == exp_token.type and
                            self.last_error_t.value == exp_token.value,
                            "t_error() was called with an unexpected "
                            "token: %r (expected: %r)" %
                            (self.last_error_t, exp_token))
                else:
                    # We do not expect an error
                    if self.last_error_t is not None:
                        self.fail(
                            "t_error() was unexpectedly called with "
                            "token: %r" % self.last_error_t)
                    else:
                        self.assertTrue(
                            act_token.type == exp_token.type,
                            "Unexpected token type: %s (expected: %s) "
                            "in token: %r" %
                            (act_token.type, exp_token.type, act_token))
                        self.assertTrue(
                            act_token.value == exp_token.value,
                            "Unexpected token value: %s (expected: %s) "
                            "in token: %r" %
                            (act_token.value, exp_token.value, act_token))
                        self.assertTrue(
                            act_token.lineno == exp_token.lineno,
                            "Unexpected token lineno: %s (expected: %s) "
                            "in token: %r" %
                            (act_token.lineno, exp_token.lineno, act_token))
                        self.assertTrue(
                            act_token.lexpos == exp_token.lexpos,
                            "Unexpected token lexpos: %s (expected: %s) "
                            "in token: %r" %
                            (act_token.lexpos, exp_token.lexpos, act_token))


class TestLexerSimple(BaseTestLexer):
    """Simple testcases for the lexical analyzer."""

    def test_empty(self):
        """Test an empty input."""
        self.run_assert_lexer("", [])

    def test_simple(self):
        """Test a simple list of tokens."""
        input_data = "a 42"
        exp_tokens = [
            self.lex_token('IDENTIFIER', 'a', 1, 0),
            self.lex_token('decimalValue', '42', 1, 2),
        ]
        self.run_assert_lexer(input_data, exp_tokens)


class TestLexerNumber(BaseTestLexer):
    """Number testcases for the lexical analyzer."""

    # Decimal numbers

    def test_decimal_0(self):
        """Test a decimal number 0."""
        input_data = "0"
        exp_tokens = [
            self.lex_token('decimalValue', input_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_decimal_plus_0(self):
        """Test a decimal number +0."""
        input_data = "+0"
        exp_tokens = [
            self.lex_token('decimalValue', input_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_decimal_minus_0(self):
        """Test a decimal number -0."""
        input_data = "-0"
        exp_tokens = [
            self.lex_token('decimalValue', input_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_decimal_small(self):
        """Test a small decimal number."""
        input_data = "12345"
        exp_tokens = [
            self.lex_token('decimalValue', input_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_decimal_small_plus(self):
        """Test a small decimal number with +."""
        input_data = "+12345"
        exp_tokens = [
            self.lex_token('decimalValue', input_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_decimal_small_minus(self):
        """Test a small decimal number with -."""
        input_data = "-12345"
        exp_tokens = [
            self.lex_token('decimalValue', input_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_decimal_long(self):
        """Test a decimal number that is long."""
        input_data = "12345678901234567890"
        exp_tokens = [
            self.lex_token('decimalValue', input_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    # Binary numbers

    def test_binary_0b(self):
        """Test a binary number 0b."""
        input_data = "0b"
        exp_tokens = [
            self.lex_token('binaryValue', input_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_binary_0B(self):
        # pylint: disable=invalid-name
        """Test a binary number 0B (upper case B)."""
        input_data = "0B"
        exp_tokens = [
            self.lex_token('binaryValue', input_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_binary_small(self):
        """Test a small binary number."""
        input_data = "101b"
        exp_tokens = [
            self.lex_token('binaryValue', input_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_binary_small_plus(self):
        """Test a small binary number with +."""
        input_data = "+1011b"
        exp_tokens = [
            self.lex_token('binaryValue', input_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_binary_small_minus(self):
        """Test a small binary number with -."""
        input_data = "-1011b"
        exp_tokens = [
            self.lex_token('binaryValue', input_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_binary_long(self):
        """Test a binary number that is long."""
        input_data = "1011001101001011101101101010101011001011111001101b"
        exp_tokens = [
            self.lex_token('binaryValue', input_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_binary_leadingzero(self):
        """Test a binary number with a leading zero."""
        input_data = "01b"
        exp_tokens = [
            self.lex_token('binaryValue', input_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_binary_leadingzeros(self):
        """Test a binary number with two leading zeros."""
        input_data = "001b"
        exp_tokens = [
            self.lex_token('binaryValue', input_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    # Octal numbers

    def test_octal_00(self):
        """Test octal number 00."""
        input_data = "00"
        exp_tokens = [
            self.lex_token('octalValue', input_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_octal_01(self):
        """Test octal number 01."""
        input_data = "01"
        exp_tokens = [
            self.lex_token('octalValue', input_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_octal_small(self):
        """Test a small octal number."""
        input_data = "0101"
        exp_tokens = [
            self.lex_token('octalValue', input_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_octal_small_plus(self):
        """Test a small octal number with +."""
        input_data = "+01011"
        exp_tokens = [
            self.lex_token('octalValue', input_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_octal_small_minus(self):
        """Test a small octal number with -."""
        input_data = "-01011"
        exp_tokens = [
            self.lex_token('octalValue', input_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_octal_long(self):
        """Test an octal number that is long."""
        input_data = "07051604302011021104151151610403031021011271071701"
        exp_tokens = [
            self.lex_token('octalValue', input_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_octal_leadingzeros(self):
        """Test an octal number with two leading zeros."""
        input_data = "001"
        exp_tokens = [
            self.lex_token('octalValue', input_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    # Hex numbers

    def test_hex_0x0(self):
        """Test hex number 0x0."""
        input_data = "0x0"
        exp_tokens = [
            self.lex_token('hexValue', input_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_hex_0X0(self):
        # pylint: disable=invalid-name
        """Test hex number 0X0."""
        input_data = "0X0"
        exp_tokens = [
            self.lex_token('hexValue', input_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_hex_0x1(self):
        """Test hex number 0x1."""
        input_data = "0x1"
        exp_tokens = [
            self.lex_token('hexValue', input_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_hex_0x01(self):
        """Test hex number 0x01."""
        input_data = "0x01"
        exp_tokens = [
            self.lex_token('hexValue', input_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_hex_small(self):
        """Test a small hex number."""
        input_data = "0x1F2a"
        exp_tokens = [
            self.lex_token('hexValue', input_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_hex_small_plus(self):
        """Test a small hex number with +."""
        input_data = "+0x1F2a"
        exp_tokens = [
            self.lex_token('hexValue', input_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_hex_small_minus(self):
        """Test a small hex number with -."""
        input_data = "-0x1F2a"
        exp_tokens = [
            self.lex_token('hexValue', input_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_hex_long(self):
        """Test a hex number that is long."""
        input_data = "0x1F2E3D4C5B6A79801f2e3d4c5b6a79801F2E3D4C5B6A7980"
        exp_tokens = [
            self.lex_token('hexValue', input_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_hex_leadingzeros(self):
        """Test a hex number with two leading zeros."""
        input_data = "0x00F"
        exp_tokens = [
            self.lex_token('hexValue', input_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    # Floating point numbers

    def test_float_dot0(self):
        """Test a float number '.0'."""
        input_data = ".0"
        exp_tokens = [
            self.lex_token('floatValue', input_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_float_0dot0(self):
        """Test a float number '0.0'."""
        input_data = "0.0"
        exp_tokens = [
            self.lex_token('floatValue', input_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_float_plus_0dot0(self):
        """Test a float number '+0.0'."""
        input_data = "+0.0"
        exp_tokens = [
            self.lex_token('floatValue', input_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_float_minus_0dot0(self):
        """Test a float number '-0.0'."""
        input_data = "-0.0"
        exp_tokens = [
            self.lex_token('floatValue', input_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_float_small(self):
        """Test a small float number."""
        input_data = "123.45"
        exp_tokens = [
            self.lex_token('floatValue', input_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_float_small_plus(self):
        """Test a small float number with +."""
        input_data = "+123.45"
        exp_tokens = [
            self.lex_token('floatValue', input_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_float_small_minus(self):
        """Test a small float number with -."""
        input_data = "-123.45"
        exp_tokens = [
            self.lex_token('floatValue', input_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_float_long(self):
        """Test a float number that is long."""
        input_data = "1.2345678901234567890"
        exp_tokens = [
            self.lex_token('floatValue', input_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    # Errors

    def test_error_09(self):
        """Test '09' (decimal: no leading zeros; octal: digit out of range)."""
        input_data = "09"
        exp_tokens = [
            self.lex_token('error', input_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_error_008(self):
        """Test '008' (decimal: no leading zeros; octal: digit out of range)."""
        input_data = "008"
        exp_tokens = [
            self.lex_token('error', input_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_error_2b(self):
        """Test '2b' (decimal: b means binary; binary: digit out of range)."""
        input_data = "2b"
        exp_tokens = [
            self.lex_token('error', input_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_error_02B(self):
        # pylint: disable=invalid-name
        """Test '02B' (decimal: B means binary; binary: digit out of range;
        octal: B means binary)."""
        input_data = "02B"
        exp_tokens = [
            self.lex_token('error', input_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_error_0dot(self):
        """Test a float number '0.' (not allowed)."""
        input_data = "0."
        exp_tokens = [
            # TODO: The current floatValue regexp does not match, so
            # it treats this as decimal. Improve the handling of this.
            self.lex_token('decimalValue', '0', 1, 0),
            # TODO: This testcase succeeds without any expected token for the
            # '.'. Find out why.
        ]
        self.run_assert_lexer(input_data, exp_tokens)


class TestLexerString(BaseTestLexer):
    """Lexer testcases for CIM datatype string."""

    def test_string_empty(self):
        """Test an empty string."""
        input_data = '""'
        exp_tokens = [
            self.lex_token('stringValue', input_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_string_onechar(self):
        """Test a string with one character."""
        input_data = '"a"'
        exp_tokens = [
            self.lex_token('stringValue', input_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_string_long(self):
        """Test a long string with ASCII chars (no backslash or quotes)."""
        input_data = '"abcdefghijklmnopqrstuvwxyz 0123456789_.,:;?=()[]{}/&%$!"'
        exp_tokens = [
            self.lex_token('stringValue', input_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_string_one_sq(self):
        """Test a string with a single quote."""
        input_data = "\"'\""
        exp_tokens = [
            self.lex_token('stringValue', input_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_string_two_sq(self):
        """Test a string with two single quotes."""
        input_data = "\"''\""
        exp_tokens = [
            self.lex_token('stringValue', input_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_string_two_sq_char(self):
        """Test a string with two single quotes and a char."""
        input_data = "\"'a'\""
        exp_tokens = [
            self.lex_token('stringValue', input_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_string_one_dq(self):
        """Test a string with an escaped double quote."""
        input_data = "\"\\\"\""
        exp_tokens = [
            self.lex_token('stringValue', input_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_string_two_dq_char(self):
        """Test a string with two escaped double quotes and a char."""
        input_data = "\"\\\"a\\\"\""
        exp_tokens = [
            self.lex_token('stringValue', input_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)


class TestLexerChar(BaseTestLexer):
    """Lexer testcases for CIM datatype char16."""

    def test_char_char(self):
        """Test a char16 with one character."""
        input_data = "'a'"
        exp_tokens = [
            self.lex_token('charValue', input_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_char_space(self):
        """Test a char16 with one space."""
        input_data = "' '"
        exp_tokens = [
            self.lex_token('charValue', input_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_char_dquote(self):
        """Test a char16 with a double quote."""
        input_data = '\'"\''
        exp_tokens = [
            self.lex_token('charValue', input_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_char_esquote(self):
        """Test a char16 with an escaped single quote."""
        input_data = '\'\\\'\''
        exp_tokens = [
            self.lex_token('charValue', input_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)


class TestFullSchema(MOFTest):
    """ Test the compile of a full DMTF schema and also
        the recreation of the mof using tomof and recompile of this new
        mof file. Tests have numbers to control ordering.
    """

    def setupCompilerForReCompile(self, debug=False):
        """Setup a second compiler instance for recompile. Result is
           mofcomp2
        """
        def moflog2(msg):
            """Display message to moflog2"""
            print(msg, file=self.logfile2)

        moflog_file2 = os.path.join(SCRIPT_DIR, 'moflog2.txt')
        # pylint: disable=attribute-defined-outside-init
        self.logfile2 = open(moflog_file2, 'w')

        # pylint: disable=attribute-defined-outside-init
        self.mofcomp2 = MOFCompiler(
            MOFWBEMConnection(),
            search_paths=None, verbose=debug,
            log_func=moflog2)

    def test_mof_schema_roundtrip(self):
        """ Test compile, of the schema, write of a new mof output file
            and recompile of that file
        """

        # original compile and write of output mof
        start_time = time()
        self.mofcomp.compile_file(SCHEMA_MOF_FN, NAME_SPACE)

        print('elapsed compile: %f  ' % (time() - start_time))

        repo = self.mofcomp.handle

        # Create file for mof output
        mofout_filename = os.path.join(SCRIPT_DIR, TMP_FILE)
        mof_out_hndl = open(mofout_filename, 'w')
        qual_decls = repo.qualifiers[NAME_SPACE]

        for qd in sorted(repo.qualifiers[NAME_SPACE].values()):
            print(qd.tomof(), file=mof_out_hndl)

        orig_classes = repo.classes[NAME_SPACE]
        for cl_ in repo.compile_ordered_classnames:
            print(orig_classes[cl_].tomof(), file=mof_out_hndl)

        mof_out_hndl.flush()
        mof_out_hndl.close()

        # Recompile the created mof output file.
        # Setup new compiler instance to avoid changing the data in
        # the first instance. Classes, etc. from the first are
        # needed for compare with recompile
        self.setupCompilerForReCompile(False)

        repo2 = self.mofcomp2.handle

        print('Start recompile file= %s' % mofout_filename)

        self.mofcomp2.compile_file(mofout_filename, NAME_SPACE)

        # Confirm lengths for qualifiers compiled, orig and recompile
        # This always works so we fail if there is an error.
        self.assertEqual(len(repo2.qualifiers[NAME_SPACE]),
                         TOTAL_QUALIFIERS)
        self.assertEqual(len(qual_decls),
                         len(repo2.qualifiers[NAME_SPACE]))
        # compare the qualifier declaractions. They must be the same
        for qd in sorted(qual_decls.values()):
            nextqd = repo2.qualifiers[NAME_SPACE][qd.name]
            self.assertEqual(nextqd, qd)

        self.assertEqual(len(repo2.classes[NAME_SPACE]),
                         TOTAL_CLASSES)

        self.assertEqual(len(orig_classes),
                         len(repo2.classes[NAME_SPACE]))

        for cl_ in orig_classes:
            orig_class = orig_classes[cl_]
            recompiled_class = repo2.classes[NAME_SPACE][cl_]
            self.assertTrue(isinstance(recompiled_class, CIMClass))
            self.assertTrue(isinstance(orig_class, CIMClass))
            self.assertTrue(recompiled_class == orig_class)

        print('elapsed recompile: %f  ' % (time() - start_time))
        os.remove(mofout_filename)


if __name__ == '__main__':
    unittest.main()
