#!/usr/bin/env python
#

""" Test the mof compiler against both locally defined mof and
    a version of the DMTF released Schema.
"""

from __future__ import print_function, absolute_import

import os
import unittest2 as unittest  # we use assertRaises(exc) introduced in py27
import six
from ply import lex
try:
    from collections import OrderedDict
except ImportError:
    from ordereddict import OrderedDict

from pywbem.cim_operations import CIMError
from pywbem.mof_compiler import MOFCompiler, MOFWBEMConnection, MOFParseError
from pywbem.cim_constants import CIM_ERR_FAILED, CIM_ERR_INVALID_PARAMETER, \
    CIM_ERR_INVALID_SUPERCLASS, CIM_ERR_INVALID_CLASS
from pywbem.cim_obj import CIMClass, CIMProperty, CIMQualifier, \
    CIMQualifierDeclaration, CIMDateTime, CIMInstanceName
from pywbem import mof_compiler
from pywbem._nocasedict import NocaseDict
from pywbem_mock import FakedWBEMConnection

from ..utils.unittest_extensions import CIMObjectMixin
from ..utils.dmtf_mof_schema_def import install_test_dmtf_schema, \
    TOTAL_QUALIFIERS, TOTAL_CLASSES

# Location of the schema for use by test_mof_compiler.
# This should not change unless you intend to use another schema directory
TEST_DIR = os.path.dirname(__file__)

# Constants
NAME_SPACE = 'root/test'

TMP_FILE = 'test_mofRoundTripOutput.mof'

# global that contains DMTFCIMSchema object created by setUpModule
TEST_DMTF_CIMSCHEMA = None
TEST_DMTF_CIMSCHEMA_MOF_DIR = None


def setUpModule():
    """ Setup the unittest. Includes possibly getting the
        schema mof from DMTF web
    """
    global TEST_DMTF_CIMSCHEMA  # pylint: disable=global-statement
    global TEST_DMTF_CIMSCHEMA_MOF_DIR  # pylint: disable=global-statement

    schema = install_test_dmtf_schema()
    TEST_DMTF_CIMSCHEMA = schema
    TEST_DMTF_CIMSCHEMA_MOF_DIR = schema.schema_mof_dir


class MOFTest(unittest.TestCase):
    """A base class that creates a MOF compiler instance"""

    def setUp(self):
        """Create the MOF compiler."""

        def moflog(msg):
            """Display message to moflog"""
            print(msg, file=self.logfile)

        moflog_file = os.path.join(TEST_DIR, 'moflog.txt')
        self.logfile = open(moflog_file, 'w')
        self.mofcomp = MOFCompiler(
            MOFWBEMConnection(),
            search_paths=[TEST_DMTF_CIMSCHEMA_MOF_DIR],
            verbose=True,
            log_func=moflog)

        self.partial_schema_file = None

    def tearDown(self):
        """Close the log file and any partial schema file."""
        self.logfile.close()
        if self.partial_schema_file:
            if os.path.exists(self.partial_schema_file):
                os.remove(self.partial_schema_file)


class Test_MOFCompiler_init(unittest.TestCase):
    """Test the MOFCompiler initialization"""

    def test_handle_repo_connection(self):
        """Test init with a handle that is a MOFWBEMConnection"""

        handle = MOFWBEMConnection()

        mofcomp = MOFCompiler(handle)

        self.assertIs(mofcomp.handle, handle)

    def test_handle_wbem_connection(self):
        """Test init with a handle that is a WBEMConnection"""

        conn = FakedWBEMConnection()

        mofcomp = MOFCompiler(conn)

        self.assertIsInstance(mofcomp.handle, MOFWBEMConnection)
        self.assertIs(mofcomp.handle.conn, conn)

    def test_handle_invalid(self):
        """Test init with a handle that is an invalid type"""

        invalid = "boo"

        with self.assertRaises(TypeError):
            MOFCompiler(invalid)


class TestInstancesUnicode(MOFTest):
    """
    Test compile of an instance with Unicode characters in string properties
    """

    def test_instance_unicode_literal(self):
        """
        Test compile of string property with literal Unicode characters
        """

        repo = self.mofcomp.handle

        class_mof = \
            'class PyWBEM_TestUnicode {\n' \
            '    string uprop;\n' \
            '};'
        self.mofcomp.compile_string(class_mof, NAME_SPACE)

        inst_mof = \
            u'instance of PyWBEM_TestUnicode {\n' \
            u'    uprop = "\u212b \u0420 \u043e \u0441 \u0441"\n' \
            u'            "\u0438 \u044f \u00e0";\n' \
            u'};'
        exp_uprop = u"\u212b \u0420 \u043e \u0441 \u0441" \
                    u"\u0438 \u044f \u00e0"

        self.mofcomp.compile_string(inst_mof, NAME_SPACE)

        for inst in repo.instances[NAME_SPACE]:
            if inst.classname == 'PyWBEM_TestUnicode':
                break
        else:
            inst = None
        assert inst is not None

        uprop = inst.properties['uprop'].value

        self.assertEqual(uprop, exp_uprop)

    def test_instance_unicode_escape(self):
        """
        Test compile of string property with MOF escaped Unicode characters
        """

        repo = self.mofcomp.handle

        class_mof = \
            'class PyWBEM_TestUnicode {\n' \
            '    string uprop;\n' \
            '};'
        self.mofcomp.compile_string(class_mof, NAME_SPACE)

        inst_mof = \
            u'instance of PyWBEM_TestUnicode {\n' \
            u'    uprop = "\\X212B \\X0420 \\x043E \\x0441 \\x0441 ' \
            u'\\x0438 \\x044f \\x00e0";\n' \
            u'};'
        exp_uprop = u"\u212b \u0420 \u043e \u0441 \u0441 " \
                    u"\u0438 \u044f \u00e0"

        self.mofcomp.compile_string(inst_mof, NAME_SPACE)

        for inst in repo.instances[NAME_SPACE]:
            if inst.classname == 'PyWBEM_TestUnicode':
                break
        else:
            inst = None
        assert inst is not None

        uprop = inst.properties['uprop'].value

        self.assertEqual(uprop, exp_uprop)

    def test_instance_unicode_escape_fail1(self):
        """
        Test compile of string property with Unicode escape with no hex chars
        """

        class_mof = \
            'class PyWBEM_TestUnicode {\n' \
            '    string uprop;\n' \
            '};'
        self.mofcomp.compile_string(class_mof, NAME_SPACE)

        inst_mof = \
            u'instance of PyWBEM_TestUnicode {\n' \
            u'    uprop = "\\xzzzz";\n' \
            u'};'

        with self.assertRaises(MOFParseError):
            self.mofcomp.compile_string(inst_mof, NAME_SPACE)


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

    def test_testmof(self):
        """
        Execute test using test.mof file. This compiles the test.mof file
        and tests for a) valid classes and instances, and then for
        a correct instance of the association class.

        This was easier than trying to create a test case in memory since that
        would involve 3 classes and multiple instances.
        """
        # compile the mof. The DMTF schema mof is installed by the setup
        self.mofcomp.compile_file(
            os.path.join(TEST_DIR, 'test.mof'), NAME_SPACE)

        # test for valid classes since we do not do that elsewhere
        pywbem_person_class = self.mofcomp.handle.GetClass(
            'PyWBEM_Person', LocalOnly=False, IncludeQualifiers=True)
        self.assertEqual(pywbem_person_class.properties['Name'].type, 'string')

        ccs = self.mofcomp.handle.GetClass(
            'PyWBEM_MemberOfPersonCollection',
            LocalOnly=False, IncludeQualifiers=True)
        self.assertEqual(ccs.properties['Member'].type, 'reference')

        # get the instances
        insts = self.mofcomp.handle.instances[NAME_SPACE]

        # get a particular instance of PyWBEM_Person.  This is
        # equivalent to getInstance('PyWBEM_PERSON.name=Alice')
        my_person = [inst for inst in insts
                     if inst.classname == 'PyWBEM_Person' and
                     inst['name'] == 'Alice']

        self.assertEqual(len(my_person), 1)
        my_person = my_person[0]

        # get the instance we want of PyWBEM_PersonCollection
        inst_coll = [inst for inst in insts
                     if inst.classname == 'PyWBEM_PersonCollection' and
                     inst['InstanceID'] == 'PersonCollection']
        self.assertEqual(len(inst_coll), 1)
        inst_coll = inst_coll[0]
        #   and inst.properties['InstanceID'] == 'PersonCollection'

        member_path = my_person.path
        collection_path = inst_coll.path
        pywbem_members = [
            inst for inst in insts
            if inst.classname == 'PyWBEM_MemberOfPersonCollection']

        # test for valid keybinding in one instance of MembersOfPersonCollection
        # against predefined CIMInstanceName. Confirms keybindings exist
        pywbem_member = pywbem_members[0]
        member_property = pywbem_member.properties['Collection']

        kb = NocaseDict({'InstanceID': 'PersonCollection'})
        exp_path = CIMInstanceName('PyWBEM_PersonCollection', kb,
                                   namespace=NAME_SPACE)
        self.assertEqual(member_property.value, exp_path)

        # find our instance in MembersOfPersonCollection
        my_member = [inst for inst in pywbem_members
                     if inst['member'] == member_path and
                     inst['Collection'] == collection_path]
        self.assertEqual(len(my_member), 1)

    def test_ref_alias(self):
        """
        Test for aliases for association classes with reference properties
        as keys.
        """
        mof_str = """
        Qualifier Association : boolean = false,
            Scope(association),
            Flavor(DisableOverride, ToSubclass);
        Qualifier Description : string = null,
            Scope(any),
            Flavor(EnableOverride, ToSubclass, Translatable);
        Qualifier Key : boolean = false,
            Scope(property, reference),
            Flavor(DisableOverride, ToSubclass);

        class TST_Person{
            [Key] string name;
        };
        [Association]
        class TST_MemberOfFamilyCollection {
           [key] TST_Person ref family;
           [key] TST_Person ref member;
        };
        class TST_FamilyCollection {
            [key] string name;
        };

        instance of TST_Person as $Mike { name = "Mike"; };
        instance of TST_FamilyCollection as $Family1 { name = "family1"; };

        instance of TST_MemberOfFamilyCollection as $MikeMember
        {
            family = $Family1;
            member = $Mike;
        };
        """

        def find_instance(path, repo):
            """Local method confirms paths found for all created instances."""
            for inst in repo:
                if inst.path == path:
                    return True
            return False

        self.mofcomp.compile_string(mof_str, NAME_SPACE)
        repo = self.mofcomp.handle

        cl = repo.GetClass(
            'TST_Person',
            LocalOnly=False, IncludeQualifiers=True)
        self.assertEqual(cl.properties['name'].type, 'string')
        instances = repo.instances[NAME_SPACE]

        # create list of correct paths and determine that they exist.
        kbs = NocaseDict()
        kbs['family'] = CIMInstanceName('TST_FamilyCollection',
                                        keybindings={'name': 'family1'},
                                        namespace=NAME_SPACE)
        kbs['member'] = CIMInstanceName('TST_Person',
                                        keybindings={'name': 'Mike'},
                                        namespace=NAME_SPACE)

        exp_paths = [
            CIMInstanceName('TST_Person', keybindings={'name': 'Mike'},
                            namespace=NAME_SPACE),
            CIMInstanceName('TST_FamilyCollection',
                            keybindings={'name': 'family1'},
                            namespace=NAME_SPACE),
            CIMInstanceName('TST_MemberOfFamilyCollection', keybindings=kbs,
                            namespace=NAME_SPACE)
        ]

        for path in exp_paths:
            self.assertTrue(find_instance(path, instances))


class TestSchemaError(MOFTest):
    """Test with errors in the schema"""

    def test_all(self):
        """Test multiple errors. Each test tries to compile a
           specific mof and should result in a specific error
        """
        self.mofcomp.parser.search_paths = []
        try:
            self.mofcomp.compile_file(os.path.join(TEST_DMTF_CIMSCHEMA_MOF_DIR,
                                                   'System',
                                                   'CIM_ComputerSystem.mof'),
                                      NAME_SPACE)
            self.fail('Expected exception')
        except CIMError as ce:
            self.assertEqual(ce.status_code, CIM_ERR_FAILED)
            self.assertEqual(ce.file_line[0],
                             os.path.join(TEST_DMTF_CIMSCHEMA_MOF_DIR,
                                          'System',
                                          'CIM_ComputerSystem.mof'))
            if ce.file_line[1] != 2:
                print('assert {}'.format(ce.file_line))
            self.assertEqual(ce.file_line[1], 2)

        self.mofcomp.compile_file(os.path.join(TEST_DMTF_CIMSCHEMA_MOF_DIR,
                                               'qualifiers.mof'),
                                  NAME_SPACE)
        try:
            self.mofcomp.compile_file(os.path.join(TEST_DMTF_CIMSCHEMA_MOF_DIR,
                                                   'System',
                                                   'CIM_ComputerSystem.mof'),
                                      NAME_SPACE)
            self.fail('Expected exception')
        except CIMError as ce:
            self.assertEqual(ce.status_code, CIM_ERR_INVALID_SUPERCLASS)
            self.assertEqual(ce.file_line[0],
                             os.path.join(
                                 TEST_DMTF_CIMSCHEMA_MOF_DIR,
                                 'System',
                                 'CIM_ComputerSystem.mof'))
            # TODO The following is cim version dependent.
            if ce.file_line[1] != 179:
                print('assertEqual {} line {}'.format(ce,
                                                      ce.file_line[1]))
            self.assertEqual(ce.file_line[1], 179)


class TestSchemaSearch(MOFTest):
    """Test the search attribute for schema in a directory defined
       by search attribute. Searches the TEST_DMTF_CIMSCHEMA_MOF_DIR
    """

    def test_compile_one(self):
        """Test against schema single mof file that is dependent
           on other files in the schema directory
        """
        self.mofcomp.compile_file(os.path.join(TEST_DMTF_CIMSCHEMA_MOF_DIR,
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

    def test_search_single_string(self):
        """
        Test search_paths with single string as path definition.  Compiles
        a single file and tests that file compiled
        """
        def moflog(msg):
            """Display message to moflog"""
            print(msg, file=self.logfile)

        moflog_file = os.path.join(TEST_DIR, 'moflog.txt')
        open(moflog_file, 'w')
        mofcomp = MOFCompiler(
            MOFWBEMConnection(),
            search_paths=TEST_DMTF_CIMSCHEMA_MOF_DIR,
            verbose=True,
            log_func=moflog)
        mofcomp.compile_file(os.path.join(TEST_DMTF_CIMSCHEMA_MOF_DIR,
                                          'System',
                                          'CIM_ComputerSystem.mof'),
                             NAME_SPACE)
        mofcomp.handle.GetClass(
            'CIM_ComputerSystem',
            LocalOnly=False, IncludeQualifiers=True)

    def test_search_None(self):
        """
        Test search_paths with single string as path definition.  Compiles
        a single file and tests that file compiled
        """
        def moflog(msg):
            """Display message to moflog"""
            print(msg, file=self.logfile)

        moflog_file = os.path.join(TEST_DIR, 'moflog.txt')
        open(moflog_file, 'w')
        mofcomp = MOFCompiler(
            MOFWBEMConnection(),
            verbose=True,
            log_func=moflog)
        try:
            mofcomp.compile_file(os.path.join(TEST_DMTF_CIMSCHEMA_MOF_DIR,
                                              'System',
                                              'CIM_ComputerSystem.mof'),
                                 NAME_SPACE)
            self.fail("Exception expected")
        except CIMError as ce:
            self.assertTrue(ce.status_code == CIM_ERR_FAILED)


class TestParseError(MOFTest):
    """Test multiple mof compile errors. Each test should generate
       a defined error.
    """

    def test_error01(self):
        """Test missing statement end comment"""

        _file = os.path.join(TEST_DIR,
                             'testmofs',
                             'parse_error01.mof')
        try:
            self.mofcomp.compile_file(_file, NAME_SPACE)
            self.fail("Exception expected.")
        except MOFParseError as pe:
            self.assertEqual(pe.file, _file)
            self.assertEqual(pe.lineno, 16)
            # pylint: disable=unsubscriptable-object
            # This may be a pylint issue
            self.assertEqual(pe.context[5][1:5], '^^^^')
            self.assertEqual(pe.context[4][1:5], 'size')

    def test_error02(self):
        """Test invalid instance def TODO what is error? ks 6/16"""
        _file = os.path.join(TEST_DIR,
                             'testmofs',
                             'parse_error02.mof')
        try:
            self.mofcomp.compile_file(_file, NAME_SPACE)
            self.fail("Exception expected.")
        except MOFParseError as pe:
            self.assertEqual(pe.file, _file)
            self.assertEqual(pe.lineno, 6)
            # pylint: disable=unsubscriptable-object
            self.assertEqual(pe.context[5][7:13], '^^^^^^')
            self.assertEqual(pe.context[4][7:13], 'weight')

    def test_error03(self):
        """Test invalid mof, extra } character"""

        _file = os.path.join(TEST_DIR,
                             'testmofs',
                             'parse_error03.mof')
        try:
            self.mofcomp.compile_file(_file, NAME_SPACE)
            self.fail("Should fail")
        except MOFParseError as pe:
            self.assertEqual(pe.file, _file)
            self.assertEqual(pe.lineno, 24)
            # pylint: disable=unsubscriptable-object
            self.assertEqual(pe.context[5][53], '^')
            self.assertEqual(pe.context[4][53], '}')

    def test_error04(self):
        """Test invalid mof, Pragmas with invalid file definitions."""

        # TODO ks 6/16why does this generate end-of-file rather than more
        # logical error
        _file = os.path.join(TEST_DIR,
                             'testmofs',
                             'parse_error04.mof')
        try:
            self.mofcomp.compile_file(_file, NAME_SPACE)
            self.fail("Exception expected.")
        except MOFParseError as pe:
            self.assertEqual(pe.msg, 'Unexpected end of file')

    def test_missing_alias(self):
        """
        Test for alias not defined
        """
        mof_str = """
        Qualifier Association : boolean = false,
            Scope(association),
            Flavor(DisableOverride, ToSubclass);
        Qualifier Description : string = null,
            Scope(any),
            Flavor(EnableOverride, ToSubclass, Translatable);
        Qualifier Key : boolean = false,
            Scope(property, reference),
            Flavor(DisableOverride, ToSubclass);

        class TST_Person{
            [Key] string name;
        };
        [Association]
        class TST_MemberOfFamilyCollection {
           [key] TST_Person ref family;
           [key] TST_Person ref member;
        };
        class TST_FamilyCollection {
            [key] string name;
        };

        instance of TST_Person { name = "Mike"; };
        instance of TST_FamilyCollection { name = "family1"; };

        instance of TST_MemberOfFamilyCollection as $MikeMember
        {
            family = $Family1;
            member = $Mike;
        };
        """
        try:
            self.mofcomp.compile_string(mof_str, NAME_SPACE)
            self.fail("Exception expected.")
        except CIMError as ce:
            self.assertEqual(ce.status_code, CIM_ERR_FAILED)
            self.assertEqual(ce.status_description, "Unknown alias: '$Family1'")

    def test_missing_superclass(self):
        """
        Test for alias not defined
        """
        mof_str = """
        class PyWBEM_Person : CIM_Blah {
        };
        """
        try:
            self.mofcomp.compile_string(mof_str, NAME_SPACE)
            self.fail("Exception expected.")
        except CIMError as ce:
            self.assertEqual(ce.status_code, CIM_ERR_INVALID_SUPERCLASS)

    def test_dup_instance(self):
        """Test Current behavior where dup instance gets put into repo"""
        mof_str = """
        Qualifier Key : boolean = false,
            Scope(property, reference),
            Flavor(DisableOverride, ToSubclass);
        Class ex_sampleClass
        {
            [key] uint32 label1;
            uint32 size;
        };

        instance of ex_sampleClass
        {
            label1 = 9921;
            size = 1;
        };

        instance of ex_sampleClass
        {
            label1 = 9921;
            size = 2;
        };
        """
        self.mofcomp.compile_string(mof_str, NAME_SPACE)

    def test_instance_wo_class(self):
        """Test Current behavior where dup instance gets put into repo"""
        mof_str = """

        instance of ex_sampleClass
        {
            label1 = 9921;
            size = 1;
        };
        """
        try:
            self.mofcomp.compile_string(mof_str, NAME_SPACE)
            self.fail("Exception expected.")
        except CIMError as ce:
            self.assertEqual(ce.status_code, CIM_ERR_INVALID_CLASS)

    def test_dup_qualifiers(self):
        """Test Current behavior where set qualifierbehavior overrides."""
        mof_str = """
        Qualifier Key : boolean = false,
            Scope(property, reference),
            Flavor(DisableOverride, ToSubclass);
        Qualifier Key : boolean = false,
            Scope(property, reference),
            Flavor(DisableOverride, ToSubclass);
        """
        self.mofcomp.compile_string(mof_str, NAME_SPACE)


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
        self.mofcomp.compile_file(os.path.join(TEST_DIR,
                                               'testmofs',
                                               'test_refs.mof'),
                                  NAME_SPACE)


class TestInstCompile(MOFTest, CIMObjectMixin):
    """ Test the compile of instances defined with a class"""

    def test_good_compile(self):
        """Execute test with file containing class and two instances."""

        self.mofcomp.compile_file(os.path.join(TEST_DIR,
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

        self.assertEqual(len(instances), 4)

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
                self.assertEqual(i['pr32'], 1.175494351E-38)
                self.assertEqual(i['pr64'], 4.9E-324)
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
                self.assertEqual(i['pr32'], 3.402823466E38)
                self.assertEqual(i['pr64'], 1.7976931348623157E308)
                self.assertEqual(i['ps'], 'abcdefg')
                self.assertEqual(i['pc'], u"'a'")
                self.assertEqual(i['pb'], True)
                self.assertEqual(i['pdt'],
                                 CIMDateTime("20160409061213.123456+120"))
                # self.assertEqual(i['peo'], None)
                # self.assertEqual(i['pei'], None)

            elif i['k1'] == 9923 and i['k2'] == 'SampleLabelValues1':
                self.assertEqual(i['pui8'], 0b101)
                self.assertEqual(i['pui16'], 0o77)
                self.assertEqual(i['pui32'], 88)
                self.assertEqual(i['pui64'], 0xabc)
                self.assertEqual(i['psi8'], -0b101)
                self.assertEqual(i['psi16'], -0o77)
                self.assertEqual(i['psi32'], -88)
                self.assertEqual(i['psi64'], -0xdef)
                self.assertEqual(i['pr32'], 0.1)
                self.assertEqual(i['pr64'], -1.1E-15)

            elif i['k1'] == 9924 and i['k2'] == 'SampleLabelZeroes':
                self.assertEqual(i['pui8'], 0)
                self.assertEqual(i['pui16'], 0)
                self.assertEqual(i['pui32'], 0)
                self.assertEqual(i['pui64'], 0)
                self.assertEqual(i['psi8'], 0)
                self.assertEqual(i['psi16'], None)
                self.assertEqual(i['psi32'], None)
                self.assertEqual(i['psi64'], None)
                self.assertEqual(i['pr32'], 0.0)
                self.assertEqual(i['pr64'], 0.0)

            else:
                self.fail('Cannot find required instance k1=%s, k2=%s' %
                          (i['k1'], i['k2']))

    def test_invalid_property(self):
        """Test compile of instance with duplicated property fails"""
        self.mofcomp.compile_file(os.path.join(TEST_DIR,
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
            self.assertEqual(ce.status_code, CIM_ERR_INVALID_PARAMETER)

    def test_dup_property(self):
        """Test compile of instance with duplicated property fails"""
        self.mofcomp.compile_file(os.path.join(TEST_DIR,
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
            self.assertEqual(ce.status_code,
                             CIM_ERR_INVALID_PARAMETER)

    def test_mismatch_property(self):
        """Test compile of instance with duplicated property fails"""
        self.mofcomp.compile_file(os.path.join(TEST_DIR,
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
            self.assertEqual(ce.status_code, CIM_ERR_INVALID_PARAMETER)

    # TODO add test for array value in inst, not scalar


class TestTypes(MOFTest, CIMObjectMixin):
    """Test for all CIM data types in a class mof"""

    def test_all(self):
        """Execute test"""
        self.mofcomp.compile_file(os.path.join(TEST_DIR,
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
            'pr32': CIMProperty('pr32', None, type='real32',
                                class_origin=test_class),
            'pr64': CIMProperty('pr64', None, type='real64',
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
        self.assert_CIMClass_obj(ac_class, exp_ac_class)


def _build_scope(set_true=None):
    """ Build a basic scope dictionary to be used in building classes
        for tests. Required because the compiler supplies all
        values in the scope list whether true or false
    """
    dict_ = OrderedDict([
        ('CLASS', False),
        ('ANY', False),
        ('ASSOCIATION', False),
        ('INDICATION', False),
        ('METHOD', False),
        ('PARAMETER', False),
        ('PROPERTY', False),
        ('REFERENCE', False),
    ])
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
                            "Unexpected token type: %r (expected: %r) "
                            "in token: %r" %
                            (act_token.type, exp_token.type, act_token))
                        self.assertTrue(
                            act_token.value == exp_token.value,
                            "Unexpected token value: %r (expected: %r) "
                            "in token: %r" %
                            (act_token.value, exp_token.value, act_token))
                        self.assertTrue(
                            act_token.lineno == exp_token.lineno,
                            "Unexpected token lineno: %r (expected: %r) "
                            "in token: %r" %
                            (act_token.lineno, exp_token.lineno, act_token))
                        self.assertTrue(
                            act_token.lexpos == exp_token.lexpos,
                            "Unexpected token lexpos: %r (expected: %r) "
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
            self.lex_token('decimalValue', 42, 1, 2),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_no_ws_delimiter(self):
        """Test that no whitespace is needed to delimit tokens."""
        input_data = "0f"
        exp_tokens = [
            self.lex_token('decimalValue', 0, 1, 0),
            self.lex_token('IDENTIFIER', 'f', 1, 1),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_ignore_space(self):
        """Test that space is ignored, but triggers new token."""
        input_data = "a b"
        exp_tokens = [
            self.lex_token('IDENTIFIER', 'a', 1, 0),
            self.lex_token('IDENTIFIER', 'b', 1, 2),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_ignore_cr(self):
        """Test that CR is ignored, but triggers new token."""
        input_data = "a\rb"
        exp_tokens = [
            self.lex_token('IDENTIFIER', 'a', 1, 0),
            self.lex_token('IDENTIFIER', 'b', 1, 2),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_ignore_tab(self):
        """Test that TAB is ignored, but triggers new token."""
        input_data = "a\tb"
        exp_tokens = [
            self.lex_token('IDENTIFIER', 'a', 1, 0),
            self.lex_token('IDENTIFIER', 'b', 1, 2),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_invalid_token(self):
        """Test that an invalid token is recognized as error."""
        input_data = "a%b cd"
        exp_tokens = [
            self.lex_token('IDENTIFIER', 'a', 1, 0),
            self.lex_token('error', '%b cd', 1, 1),
            self.lex_token('IDENTIFIER', 'b', 1, 2),
            self.lex_token('IDENTIFIER', 'cd', 1, 4),
        ]
        self.run_assert_lexer(input_data, exp_tokens)


class TestLexerNumber(BaseTestLexer):
    """Number testcases for the lexical analyzer."""

    # Decimal numbers

    def test_decimal_0(self):
        """Test a decimal number 0."""
        input_data = "0"
        exp_data = 0
        exp_tokens = [
            self.lex_token('decimalValue', exp_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_decimal_plus_0(self):
        """Test a decimal number +0."""
        input_data = "+0"
        exp_data = 0
        exp_tokens = [
            self.lex_token('decimalValue', exp_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_decimal_minus_0(self):
        """Test a decimal number -0."""
        input_data = "-0"
        exp_data = 0
        exp_tokens = [
            self.lex_token('decimalValue', exp_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_decimal_small(self):
        """Test a small decimal number."""
        input_data = "12345"
        exp_data = 12345
        exp_tokens = [
            self.lex_token('decimalValue', exp_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_decimal_small_plus(self):
        """Test a small decimal number with +."""
        input_data = "+12345"
        exp_data = 12345
        exp_tokens = [
            self.lex_token('decimalValue', exp_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_decimal_small_minus(self):
        """Test a small decimal number with -."""
        input_data = "-12345"
        exp_data = -12345
        exp_tokens = [
            self.lex_token('decimalValue', exp_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_decimal_long(self):
        """Test a decimal number that is long."""
        input_data = "12345678901234567890"
        exp_data = 12345678901234567890
        exp_tokens = [
            self.lex_token('decimalValue', exp_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    # Binary numbers

    def test_binary_0b(self):
        """Test a binary number 0b."""
        input_data = "0b"
        exp_data = 0
        exp_tokens = [
            self.lex_token('binaryValue', exp_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_binary_0B(self):
        # pylint: disable=invalid-name
        """Test a binary number 0B (upper case B)."""
        input_data = "0B"
        exp_data = 0
        exp_tokens = [
            self.lex_token('binaryValue', exp_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_binary_small(self):
        """Test a small binary number."""
        input_data = "101b"
        exp_data = 0b101
        exp_tokens = [
            self.lex_token('binaryValue', exp_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_binary_small_plus(self):
        """Test a small binary number with +."""
        input_data = "+1011b"
        exp_data = 0b1011
        exp_tokens = [
            self.lex_token('binaryValue', exp_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_binary_small_minus(self):
        """Test a small binary number with -."""
        input_data = "-1011b"
        exp_data = -0b1011
        exp_tokens = [
            self.lex_token('binaryValue', exp_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_binary_long(self):
        """Test a binary number that is long."""
        input_data = "1011001101001011101101101010101011001011111001101b"
        exp_data = 0b1011001101001011101101101010101011001011111001101
        exp_tokens = [
            self.lex_token('binaryValue', exp_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_binary_leadingzero(self):
        """Test a binary number with a leading zero."""
        input_data = "01b"
        exp_data = 0b01
        exp_tokens = [
            self.lex_token('binaryValue', exp_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_binary_leadingzeros(self):
        """Test a binary number with two leading zeros."""
        input_data = "001b"
        exp_data = 0b001
        exp_tokens = [
            self.lex_token('binaryValue', exp_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    # Octal numbers

    def test_octal_00(self):
        """Test octal number 00."""
        input_data = "00"
        exp_data = 0
        exp_tokens = [
            self.lex_token('octalValue', exp_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_octal_01(self):
        """Test octal number 01."""
        input_data = "01"
        exp_data = 0o01
        exp_tokens = [
            self.lex_token('octalValue', exp_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_octal_small(self):
        """Test a small octal number."""
        input_data = "0101"
        exp_data = 0o0101
        exp_tokens = [
            self.lex_token('octalValue', exp_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_octal_small_plus(self):
        """Test a small octal number with +."""
        input_data = "+01011"
        exp_data = 0o1011
        exp_tokens = [
            self.lex_token('octalValue', exp_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_octal_small_minus(self):
        """Test a small octal number with -."""
        input_data = "-01011"
        exp_data = -0o1011
        exp_tokens = [
            self.lex_token('octalValue', exp_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_octal_long(self):
        """Test an octal number that is long."""
        input_data = "07051604302011021104151151610403031021011271071701"
        exp_data = 0o7051604302011021104151151610403031021011271071701
        exp_tokens = [
            self.lex_token('octalValue', exp_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_octal_leadingzeros(self):
        """Test an octal number with two leading zeros."""
        input_data = "001"
        exp_data = 0o001
        exp_tokens = [
            self.lex_token('octalValue', exp_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    # Hex numbers

    def test_hex_0x0(self):
        """Test hex number 0x0."""
        input_data = "0x0"
        exp_data = 0o0
        exp_tokens = [
            self.lex_token('hexValue', exp_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_hex_0X0(self):
        # pylint: disable=invalid-name
        """Test hex number 0X0."""
        input_data = "0X0"
        exp_data = 0x0
        exp_tokens = [
            self.lex_token('hexValue', exp_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_hex_0x1(self):
        """Test hex number 0x1."""
        input_data = "0x1"
        exp_data = 0x1
        exp_tokens = [
            self.lex_token('hexValue', exp_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_hex_0x01(self):
        """Test hex number 0x01."""
        input_data = "0x01"
        exp_data = 0x01
        exp_tokens = [
            self.lex_token('hexValue', exp_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_hex_small(self):
        """Test a small hex number."""
        input_data = "0x1F2a"
        exp_data = 0x1f2a
        exp_tokens = [
            self.lex_token('hexValue', exp_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_hex_small_plus(self):
        """Test a small hex number with +."""
        input_data = "+0x1F2a"
        exp_data = 0x1f2a
        exp_tokens = [
            self.lex_token('hexValue', exp_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_hex_small_minus(self):
        """Test a small hex number with -."""
        input_data = "-0x1F2a"
        exp_data = -0x1f2a
        exp_tokens = [
            self.lex_token('hexValue', exp_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_hex_long(self):
        """Test a hex number that is long."""
        input_data = "0x1F2E3D4C5B6A79801f2e3d4c5b6a79801F2E3D4C5B6A7980"
        exp_data = 0x1F2E3D4C5B6A79801f2e3d4c5b6a79801F2E3D4C5B6A7980
        exp_tokens = [
            self.lex_token('hexValue', exp_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_hex_leadingzeros(self):
        """Test a hex number with two leading zeros."""
        input_data = "0x00F"
        exp_data = 0x00F
        exp_tokens = [
            self.lex_token('hexValue', exp_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    # Floating point numbers

    def test_float_dot0(self):
        """Test a float number '.0'."""
        input_data = ".0"
        exp_data = 0.0
        exp_tokens = [
            self.lex_token('floatValue', exp_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_float_0dot0(self):
        """Test a float number '0.0'."""
        input_data = "0.0"
        exp_data = 0.0
        exp_tokens = [
            self.lex_token('floatValue', exp_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_float_plus_0dot0(self):
        """Test a float number '+0.0'."""
        input_data = "+0.0"
        exp_data = 0.0
        exp_tokens = [
            self.lex_token('floatValue', exp_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_float_minus_0dot0(self):
        """Test a float number '-0.0'."""
        input_data = "-0.0"
        exp_data = 0.0
        exp_tokens = [
            self.lex_token('floatValue', exp_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_float_small(self):
        """Test a small float number."""
        input_data = "123.45"
        exp_data = 123.45
        exp_tokens = [
            self.lex_token('floatValue', exp_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_float_small_plus(self):
        """Test a small float number with +."""
        input_data = "+123.45"
        exp_data = 123.45
        exp_tokens = [
            self.lex_token('floatValue', exp_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_float_small_minus(self):
        """Test a small float number with -."""
        input_data = "-123.45"
        exp_data = -123.45
        exp_tokens = [
            self.lex_token('floatValue', exp_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_float_long(self):
        """Test a float number that is long."""
        input_data = "1.2345678901234567890"
        exp_data = 1.2345678901234567890
        exp_tokens = [
            self.lex_token('floatValue', exp_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    # Errors

    def test_error_09(self):
        """Test '09' (decimal: no leading zeros; octal: digit out of range)."""
        input_data = "09 bla"
        exp_tokens = [
            self.lex_token('error', '09', 1, 0),
            self.lex_token('IDENTIFIER', 'bla', 1, 3),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_error_008(self):
        """Test '008' (decimal: no leading zeros; octal: digit out of range)."""
        input_data = "008 bla"
        exp_tokens = [
            self.lex_token('error', '008', 1, 0),
            self.lex_token('IDENTIFIER', 'bla', 1, 4),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_error_2b(self):
        """Test '2b' (decimal: b means binary; binary: digit out of range)."""
        input_data = "2b bla"
        exp_tokens = [
            self.lex_token('error', '2b', 1, 0),
            self.lex_token('IDENTIFIER', 'bla', 1, 3),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_error_9b(self):
        """Test '9b' (decimal: b means binary; binary: digit out of range)."""
        input_data = "9b bla"
        exp_tokens = [
            self.lex_token('error', '9b', 1, 0),
            self.lex_token('IDENTIFIER', 'bla', 1, 3),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_error_02B(self):
        # pylint: disable=invalid-name
        """Test '02B' (decimal: B means binary; binary: digit out of range;
        octal: B means binary)."""
        input_data = "02B bla"
        exp_tokens = [
            self.lex_token('error', '02B', 1, 0),
            self.lex_token('IDENTIFIER', 'bla', 1, 4),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_error_0dot(self):
        """Test '0.' (not a valid float, is parsed as a decimal '0' followed by
        an illegal character '.' which is skipped in t_error()."""
        input_data = "0. bla"
        exp_tokens = [
            self.lex_token('decimalValue', 0, 1, 0),
            self.lex_token('error', '. bla', 1, 1),
            self.lex_token('IDENTIFIER', 'bla', 1, 3),
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

        moflog_file2 = os.path.join(TEST_DIR, 'moflog2.txt')
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
        # start_time = time()
        self.mofcomp.compile_file(TEST_DMTF_CIMSCHEMA.schema_mof_file,
                                  NAME_SPACE)
        # print('elapsed compile: %f  ' % (time() - start_time))

        repo = self.mofcomp.handle

        # Create file for mof output
        mofout_filename = os.path.join(TEST_DIR, TMP_FILE)
        mof_out_hndl = open(mofout_filename, 'w')

        # Output and verify the qualifier declarations
        orig_qual_decls = repo.qualifiers[NAME_SPACE]
        self.assertEqual(len(orig_qual_decls), TOTAL_QUALIFIERS)
        for qn in sorted(orig_qual_decls.keys()):
            orig_qual_decl = orig_qual_decls[qn]
            self.assertTrue(isinstance(orig_qual_decl, CIMQualifierDeclaration))
            print(orig_qual_decl.tomof(), file=mof_out_hndl)

        # Output and verify the classes
        orig_classes = repo.classes[NAME_SPACE]
        self.assertEqual(len(orig_classes), TOTAL_CLASSES)
        self.assertEqual(len(repo.compile_ordered_classnames), TOTAL_CLASSES)
        for cn in repo.compile_ordered_classnames:
            orig_class = orig_classes[cn]
            self.assertTrue(isinstance(orig_class, CIMClass))
            print(orig_class.tomof(), file=mof_out_hndl)

        mof_out_hndl.flush()
        mof_out_hndl.close()

        # Recompile the created mof output file.
        # Setup new compiler instance to avoid changing the data in
        # the first instance. Classes, etc. from the first are
        # needed for compare with recompile
        self.setupCompilerForReCompile(False)

        repo2 = self.mofcomp2.handle

        # print('Start recompile file= %s' % mofout_filename)
        # start_time = time()
        self.mofcomp2.compile_file(mofout_filename, NAME_SPACE)
        # print('elapsed recompile: %f  ' % (time() - start_time))

        # Verify the recompiled qualifier declaractions are like the originals
        recompiled_qual_decls = repo2.qualifiers[NAME_SPACE]
        self.assertEqual(len(recompiled_qual_decls), len(orig_qual_decls))
        for qn in sorted(orig_qual_decls.keys()):
            orig_qual_decl = orig_qual_decls[qn]
            recompiled_qual_decl = recompiled_qual_decls[qn]
            self.assertEqual(recompiled_qual_decl, orig_qual_decl)

        # Verify the recompiled classes are like the originals
        recompiled_classes = repo2.classes[NAME_SPACE]
        self.assertEqual(len(recompiled_classes), len(orig_classes))
        for cn in orig_classes:
            orig_class = orig_classes[cn]
            recompiled_class = recompiled_classes[cn]
            self.assertEqual(recompiled_class, orig_class)

        os.remove(mofout_filename)


class TestPartialSchema(MOFTest):
    """ Test the compile of a full DMTF schema and also
        the recreation of the mof using tomof and recompile of this new
        mof file. Tests have numbers to control ordering.
    """

    @staticmethod
    def define_partial_schema():
        """
        Build  a schema include file that has a subset of the files in
        a complete DMTF schema.
        """
        schema_mof = """
            #pragma locale ("en_US")
            #pragma include ("Interop/CIM_RegisteredProfile.mof")
            #pragma include ("Interop/CIM_ObjectManager.mof")
            #pragma include ("Interop/CIM_ElementConformsToProfile.mof")
            #pragma include ("Interop/CIM_ReferencedProfile.mof")
            #pragma include ("System/CIM_LocalFileSystem.mof")
            """
        return schema_mof

    @staticmethod
    def expected_classes():
        """The classes expected to be directly compiled from the schema_mof
           above
        """
        return('CIM_RegisteredProfile', 'CIM_ObjectManager',
               'CIM_ElementConformsToProfile', 'CIM_ReferencedProfile',
               'CIM_LocalFileSystem')

    @staticmethod
    def expected_dependent_classes():
        """ Return tuple of expected dependent classes from the compile"""
        return('CIM_ManagedElement', 'CIM_WBEMService', 'CIM_Service',
               'CIM_RegisteredSpecification')

    def test_build_from_partial_schema(self):
        """
        Build the schema qualifier and class objects in the repository.
        This requires only that the leaf objects be defined in a mof
        include file since the compiler finds the files for qualifiers
        and dependent classes.
        """
        schema_mof = self.define_partial_schema()

        # write the schema to a file in the schema directory
        self.partial_schema_file = 'test_partial_schema.mof'
        test_schemafile = os.path.join(TEST_DMTF_CIMSCHEMA_MOF_DIR,
                                       self.partial_schema_file)
        with open(test_schemafile, "w") as sf:
            sf.write(schema_mof)

        self.mofcomp.compile_file(test_schemafile, NAME_SPACE)

        repo = self.mofcomp.handle
        qualrepo = repo.qualifiers[NAME_SPACE]
        clsrepo = repo.classes[NAME_SPACE]
        # Assert that at least some qualifiers exist
        # The compiler automatically add qualifiers to the schema compile
        self.assertTrue('Abstract' in qualrepo)
        self.assertEqual(len(qualrepo), TOTAL_QUALIFIERS)

        # assert compiled classes exist
        for cln in self.expected_classes():
            self.assertTrue(cln in clsrepo)

        # assert superclasses not specifically defined in the schema file
        # were included from the compile search algorithm
        for cln in self.expected_dependent_classes():
            self.assertTrue(cln in clsrepo)

    def test_build_from_schema_string(self):
        """
        Build the schema qualifier and class objects in the repository from
        a mof file defined as a string. This uses the same input data as
        test_build_from_partial_schema above.
        """
        schema_mof = self.define_partial_schema()

        self.mofcomp.compile_string(schema_mof, NAME_SPACE)

        repo = self.mofcomp.handle
        qualrepo = repo.qualifiers[NAME_SPACE]
        clsrepo = repo.classes[NAME_SPACE]
        # assert that at least some qualifiers exist
        self.assertTrue('Abstract' in qualrepo)
        self.assertEqual(len(qualrepo), TOTAL_QUALIFIERS)

        # assert compiled classes exist
        for cln in self.expected_classes():
            self.assertTrue(cln in clsrepo)

        for cln in self.expected_dependent_classes():
            self.assertTrue(cln in clsrepo)

    def test_compile_class_withref(self):

        """
        Test compile a single class with reference properties that are not
        listed in pragma.
        """
        schema_mof = """
            #pragma locale ("en_US")
            #pragma include ("Interop/CIM_ElementConformsToProfile.mof")
            """
        exp_classes = ['CIM_ElementConformsToProfile', 'CIM_ManagedElement',
                       'CIM_RegisteredSpecification', 'CIM_RegisteredProfile']
        self.mofcomp.compile_string(schema_mof, NAME_SPACE)

        repo = self.mofcomp.handle
        clsrepo = repo.classes[NAME_SPACE]
        self.assertEqual(len(exp_classes), len(clsrepo))
        for cln in exp_classes:
            self.assertTrue(cln in clsrepo)

    def test_compile_classmethod_ref(self):

        """
        Test compile a single class with reference properties that are not
        listed in pragma. This test installs the dependent classes
        """
        schema_mof = """
           class My_ClassWithRef {
                  [Key]
                string InstanceID;

                uint16 MyMethod(
                    CIM_SettingData Ref MySettingData);
            };
            """
        exp_classes = ['My_ClassWithRef', 'CIM_ManagedElement',
                       'CIM_SettingData']
        self.mofcomp.compile_string(schema_mof, NAME_SPACE)

        repo = self.mofcomp.handle
        clsrepo = repo.classes[NAME_SPACE]
        self.assertEqual(len(exp_classes), len(clsrepo))
        for cln in exp_classes:
            self.assertTrue(cln in clsrepo)

    def test_compile_class_ref_err(self):

        """
        Test compile a single class with reference properties where the
        reference class does not exist. Results in exception.
        """
        schema_mof = """
            class My_BadAssoc
            {
                    [Key]
                MY_ClassDoesNotexist REF Group;

                    [Key]
                MY_ClassDoesNotexist2 REF Component;
            };
            """
        try:
            self.mofcomp.compile_string(schema_mof, NAME_SPACE)
            self.fail("Exception expected")
        except CIMError as ce:
            self.assertTrue(ce.status_code == CIM_ERR_INVALID_PARAMETER)

    def test_compile_class_embinst(self):
        """
        Test compile a single class with property and method param containing
        embedded instance.
        """

        schema_mof = """
            class My_ClassWithEmbeddedInst {
                  [Key]
                string InstanceID;

                    [EmbeddedInstance ( "CIM_Keystore" )]
                string FakeEmbeddedInstProp;

                uint16 MyMethod(
                        [EmbeddedInstance("CIM_SettingData")]
                    string ParamWithEmbeddedInstance);
            };
            """

        exp_classes = ['My_ClassWithEmbeddedInst', 'CIM_SettingData',
                       'CIM_ManagedElement', 'CIM_Collection',
                       'CIM_CredentialStore', 'CIM_Keystore']
        self.mofcomp.compile_string(schema_mof, NAME_SPACE)
        repo = self.mofcomp.handle
        clsrepo = repo.classes[NAME_SPACE]
        self.assertEqual(len(exp_classes), len(clsrepo))
        for cln in exp_classes:
            self.assertTrue(cln in clsrepo)

    def test_compile_class_embinst_err(self):
        """
        Test finding class for EmbeddedInstance qualifier where
        class does not exist.
        """
        schema_mof = """
            class My_ClassWithEmbeddedInst {
                  [Key]
                string InstanceID;

                    [EmbeddedInstance ( "CIM_ClassDoesNotExist" )]
                string FakeEmbeddedInstProp;

                uint16 MyMethod(
                        [EmbeddedInstance("CIM_SettingData")]
                    string ParamWithEmbeddedInstance);
            };
            """
        try:
            self.mofcomp.compile_string(schema_mof, NAME_SPACE)
            self.fail("Exception expected")
        except CIMError as ce:
            self.assertTrue(ce.status_code == CIM_ERR_INVALID_PARAMETER)

    def test_compile_class_circular(self):

        """
        Test compile a class that itself contains a circular reference, in this
        case a reference to itself through the EmbeddedInstance qualifier.
        """

        schema_mof = """
            class My_ClassWithEmbeddedInst {
                  [Key]
                string InstanceID;

                    [EmbeddedInstance ( "My_ClassWithEmbeddedInst" )]
                string FakeEmbeddedInstProp;

                uint16 MyMethod(
                        [EmbeddedInstance("CIM_SettingData")]
                    string ParamWithEmbeddedInstance);
            };
            """

        exp_classes = ['My_ClassWithEmbeddedInst', 'CIM_SettingData',
                       'CIM_ManagedElement']
        self.mofcomp.compile_string(schema_mof, NAME_SPACE)
        repo = self.mofcomp.handle
        clsrepo = repo.classes[NAME_SPACE]
        self.assertEqual(len(exp_classes), len(clsrepo))
        for cln in exp_classes:
            self.assertTrue(cln in clsrepo)


class TestFileErrors(MOFTest):
    """
        Test for IO errors in compile where file does not exist either
        direct compile or expected in search path.
    """

    def create_mofcompiler(self):
        """ Create the compiler with no search path """

        def moflog(msg):
            """Display message to moflog"""
            print(msg, file=self.logfile)

        moflog_file = os.path.join(TEST_DIR, 'moflog.txt')
        self.logfile = open(moflog_file, 'w')
        self.mofcomp = MOFCompiler(
            MOFWBEMConnection(),
            verbose=False,
            log_func=moflog)

    def test_file_not_found(self):
        """
            Test for case where compile file does not exist.
        """
        self.create_mofcompiler()
        try:
            self.mofcomp.compile_file('NoSuchFile.mof', NAME_SPACE)
        except IOError:
            pass

    def test_filedir_not_found(self):
        """
            Test for filename with dir component not found.
        """
        self.create_mofcompiler()
        try:
            self.mofcomp.compile_file('abc/NoSuchFile.mof', NAME_SPACE)
        except IOError:
            pass

    def test_error_search(self):
        """
            Test for file not found in search path where search path is
            schema dir.
        """

        try:
            self.mofcomp.compile_file(
                os.path.join(TEST_DMTF_CIMSCHEMA_MOF_DIR, 'System',
                             'CIM_ComputerSystemx.mof'),
                NAME_SPACE)
        except IOError:
            pass


if __name__ == '__main__':
    unittest.main()
