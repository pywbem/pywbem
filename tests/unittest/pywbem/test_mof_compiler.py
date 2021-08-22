""" Test the mof compiler against both locally defined MOF and
    a version of the DMTF released Schema.
"""

from __future__ import print_function, absolute_import

import os
import io
import unittest
import re
import pytest
import six
from ply import lex
try:
    from collections import OrderedDict
except ImportError:
    from ordereddict import OrderedDict

from ...utils import skip_if_moftab_regenerated
from ..utils.unittest_extensions import CIMObjectMixin
from ..utils.dmtf_mof_schema_def import install_test_dmtf_schema, \
    TOTAL_QUALIFIERS, TOTAL_CLASSES
from ..utils.pytest_extensions import simplified_test_function

# pylint: disable=wrong-import-position, wrong-import-order, invalid-name
from ...utils import import_installed
pywbem = import_installed('pywbem')
from pywbem._mof_compiler import MOFCompiler, MOFWBEMConnection, \
    MOFParseError, MOFDependencyError  # noqa: E402
from pywbem._cim_constants import CIM_ERR_ALREADY_EXISTS, \
    CIM_ERR_INVALID_NAMESPACE, CIM_ERR_NOT_FOUND  # noqa: E402
from pywbem._cim_obj import CIMClass, CIMProperty, CIMQualifier, \
    CIMQualifierDeclaration, CIMDateTime, CIMInstanceName  # noqa: E402
from pywbem import _mof_compiler, CIMInstance, CIMError  # noqa: E402
from pywbem._utils import _format  # noqa: E402
from pywbem._nocasedict import NocaseDict  # noqa: E402
pywbem_mock = import_installed('pywbem_mock')
from pywbem_mock import FakedWBEMConnection  # noqa: E402
# pylint: enable=wrong-import-position, wrong-import-order, invalid-name

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
        # pylint: disable=consider-using-with
        self.logfile = io.open(moflog_file, 'w', encoding='utf-8')
        self.mofcomp = MOFCompiler(
            MOFWBEMConnection(),
            search_paths=[TEST_DMTF_CIMSCHEMA_MOF_DIR],
            verbose=False,
            log_func=moflog)

        # Set up a second MOF compiler for recompile.
        # Using a second MOF compiler object avoids changing the data in the
        # first MOF compiler object. Classes, etc. from the first MOF compiler
        # are needed for compare with recompile.

        def moflog2(msg):
            """Display message to moflog2"""
            print(msg, file=self.logfile2)

        moflog_file2 = os.path.join(TEST_DIR, 'moflog2.txt')
        # pylint: disable=consider-using-with
        self.logfile2 = io.open(moflog_file2, 'w', encoding='utf-8')
        self.mofcomp2 = MOFCompiler(
            MOFWBEMConnection(),
            search_paths=None, verbose=False,
            log_func=moflog2)

        self.partial_schema_file = None

    def tearDown(self):
        """Close the log file and any partial schema file."""

        self.logfile.close()
        self.logfile2.close()

        self.mofcomp.conn_close()
        self.mofcomp2.conn_close()

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

        self.assertIsInstance(mofcomp.handle, FakedWBEMConnection)

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

        skip_if_moftab_regenerated()

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

        repo = self.mofcomp.handle

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

        skip_if_moftab_regenerated()

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

        repo = self.mofcomp.handle

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

        skip_if_moftab_regenerated()

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

        skip_if_moftab_regenerated()

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

        skip_if_moftab_regenerated()

        mof_str = "Qualifier test1 : scope(class),\n" \
            "Flavor(enableoverride, RESTRICTED, Translatable);"
        try:
            self.mofcomp.compile_string(mof_str, NAME_SPACE)
            self.fail("Test must generate exception")
        except MOFParseError:
            pass

    def test_conflicting_flavors1(self):
        """Conflicting flavors should cause exception"""

        skip_if_moftab_regenerated()

        mof_str = "Qualifier test1 : scope(class),\n" \
                  "Flavor(DisableOverride, EnableOverride);"
        try:
            self.mofcomp.compile_string(mof_str, NAME_SPACE)
            self.fail("Test must generate exception")
        except MOFParseError:
            pass

    def test_conflicting_flavors2(self):
        """Conflicting flavors should cause exception"""

        skip_if_moftab_regenerated()

        mof_str = "Qualifier test1 : scope(class),\n" \
                  "Flavor(Restricted, ToSubclass);"
        try:
            self.mofcomp.compile_string(mof_str, NAME_SPACE)
            self.fail("Test must generate exception")
        except MOFParseError:
            pass

    def test_invalid_flavor1(self):
        """Invalid flavor should cause exception"""

        skip_if_moftab_regenerated()

        mof_str = "Qualifier test1 : scope(class),\n" \
                  "Flavor(Restricted, ToSubclass, invalidflavor);"
        try:
            self.mofcomp.compile_string(mof_str, NAME_SPACE)
            self.fail("Test must generate exception")
        except MOFParseError:
            pass

    def test_invalid_flavor2(self):
        """Invalid flavor should cause exception"""

        skip_if_moftab_regenerated()

        mof_str = "Qualifier test1 : scope(class),\n" \
                  "Flavor(invalidflavor);"
        try:
            self.mofcomp.compile_string(mof_str, NAME_SPACE)
            self.fail("Test must generate exception")
        except MOFParseError:
            pass


class TestRemove(MOFTest):
    """Test rollback using test.mof"""

    def test_remove(self):
        """
        Test create mof and rollback using mocker as remote repository
        """

        def moflog(msg):
            """Display message to moflog"""
            print(msg, file=self.logfile)

        skip_if_moftab_regenerated()

        # Compile the mof. The DMTF schema mof is installed by the setup

        ns = 'root/test'
        conn = FakedWBEMConnection(default_namespace=ns)

        # Create compiler using FakedWBEMConnection as conn
        # This compiler writes new classes and instances to conn
        self.mofcomp = MOFCompiler(
            conn,
            search_paths=[TEST_DMTF_CIMSCHEMA_MOF_DIR],
            verbose=False,
            log_func=moflog)

        # Classes in the test class file
        clns = ['PyWBEM_AllTypes', 'PyWBEM_MemberOfPersonCollection',
                'PyWBEM_PersonCollection', 'PyWBEM_Person']

        # Compile the file to the conn destination
        self.mofcomp.compile_file(
            os.path.join(TEST_DIR, 'test.mof'), ns)

        for cln in clns:
            conn.GetClass(cln)
            assert conn.EnumerateInstances(cln) is not None

        # Remove the mof defined by the testfile
        # create rollback definition

        conn_mof_mofcomp = MOFCompiler(
            MOFWBEMConnection(conn=conn),
            search_paths=[TEST_DMTF_CIMSCHEMA_MOF_DIR],
            verbose=False,
            log_func=moflog)

        # recompile to MOFWBEMConnection for remove
        conn_mof_mofcomp.compile_file(
            os.path.join(TEST_DIR, 'test.mof'), ns)

        conn_mof_mofcomp.rollback(verbose=False)

        for cln in clns:
            try:
                conn.GetClass(cln)
            except CIMError as ce:
                assert ce.status_code == CIM_ERR_NOT_FOUND


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
        skip_if_moftab_regenerated()
        # compile the mof. The DMTF schema mof is installed by the setup
        self.mofcomp.compile_file(
            os.path.join(TEST_DIR, 'test.mof'), NAME_SPACE)

        repo = self.mofcomp.handle

        # test for valid classes since we do not do that elsewhere
        pywbem_person_class = repo.GetClass(
            'PyWBEM_Person', namespace=NAME_SPACE,
            LocalOnly=False, IncludeQualifiers=True)
        self.assertEqual(pywbem_person_class.properties['Name'].type, 'string')

        ccs = repo.GetClass(
            'PyWBEM_MemberOfPersonCollection', namespace=NAME_SPACE,
            LocalOnly=False, IncludeQualifiers=True)
        self.assertEqual(ccs.properties['Member'].type, 'reference')

        # get the instances
        insts = repo.instances[NAME_SPACE]

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

        def confirm_instance_path(path, repo):
            """Local method confirms paths found for all created instances."""
            for inst in repo:
                if inst.path == path:
                    return True
            return False

        skip_if_moftab_regenerated()

        self.mofcomp.compile_string(mof_str, NAME_SPACE)

        # set the connection default namespace to the test namespace name
        # Setting default_namespace because MOFWBEMConnection GetClass does not
        # support namespace parameter
        repo = self.mofcomp.handle

        cl = repo.GetClass('TST_Person', namespace=NAME_SPACE,
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
            self.assertTrue(confirm_instance_path(path, instances))


class TestSchemaError(MOFTest):
    """Test with errors in the schema"""

    def test_all(self):
        """Test multiple errors. Each test tries to compile a
           specific mof and should result in a specific error
        """

        skip_if_moftab_regenerated()

        self.mofcomp.parser.search_paths = []
        try:
            self.mofcomp.compile_file(os.path.join(TEST_DMTF_CIMSCHEMA_MOF_DIR,
                                                   'System',
                                                   'CIM_ComputerSystem.mof'),
                                      NAME_SPACE)
            self.fail("Must fail with missing qualifier declaration")
        except MOFDependencyError as pe:
            assert re.search(
                r"Cannot compile element specifying qualifier .* "
                r"qualifier declaration .* not exist",
                pe.msg, re.IGNORECASE)
            self.assertEqual(pe.file,
                             os.path.join(TEST_DMTF_CIMSCHEMA_MOF_DIR,
                                          'System',
                                          'CIM_ComputerSystem.mof'))
            self.assertEqual(pe.lineno, 2,
                             msg="Unexpected line number: "
                             "got {0}, expected {1}, exception: {2!r}".
                             format(pe.lineno, 2, pe))

        self.mofcomp.compile_file(os.path.join(TEST_DMTF_CIMSCHEMA_MOF_DIR,
                                               'qualifiers.mof'),
                                  NAME_SPACE)
        try:
            self.mofcomp.compile_file(os.path.join(TEST_DMTF_CIMSCHEMA_MOF_DIR,
                                                   'System',
                                                   'CIM_ComputerSystem.mof'),
                                      NAME_SPACE)
            self.fail("Must fail with missing superclass")
        except MOFDependencyError as pe:
            assert re.search(
                r"Cannot compile class .* superclass .* not exist",
                pe.msg, re.IGNORECASE)
            self.assertEqual(pe.file,
                             os.path.join(
                                 TEST_DMTF_CIMSCHEMA_MOF_DIR,
                                 'System',
                                 'CIM_ComputerSystem.mof'))
            # TODO The following is cim version dependent.
            self.assertEqual(pe.lineno, 179,
                             msg="Unexpected line number: "
                             "got {0}, expected {1}, exception: {2!r}".
                             format(pe.lineno, 179, pe))


class TestSchemaSearch(MOFTest):
    """Test the search attribute for schema in a directory defined
       by search attribute. Searches the TEST_DMTF_CIMSCHEMA_MOF_DIR
    """

    def test_compile_one(self):
        """Test against schema single mof file that is dependent
           on other files in the schema directory
        """

        skip_if_moftab_regenerated()

        self.mofcomp.compile_file(os.path.join(TEST_DMTF_CIMSCHEMA_MOF_DIR,
                                               'System',
                                               'CIM_ComputerSystem.mof'),
                                  NAME_SPACE)

        repo = self.mofcomp.handle

        # assert compile has not changed default_namespace in MOFWBEMConnection
        assert repo.default_namespace == 'root/cimv2'

        ccs = repo.GetClass('CIM_ComputerSystem', namespace=NAME_SPACE,
                            LocalOnly=False, IncludeQualifiers=True)
        self.assertEqual(ccs.properties['RequestedState'].type, 'uint16')
        self.assertEqual(ccs.properties['Dedicated'].type, 'uint16')
        cele = repo.GetClass('CIM_EnabledLogicalElement', namespace=NAME_SPACE,
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

        skip_if_moftab_regenerated()

        mofcomp = MOFCompiler(
            MOFWBEMConnection(),
            search_paths=TEST_DMTF_CIMSCHEMA_MOF_DIR,
            verbose=False,
            log_func=moflog)

        mofcomp.compile_file(os.path.join(TEST_DMTF_CIMSCHEMA_MOF_DIR,
                                          'System',
                                          'CIM_ComputerSystem.mof'),
                             NAME_SPACE)

        repo = mofcomp.handle

        repo.GetClass('CIM_ComputerSystem', namespace=NAME_SPACE,
                      LocalOnly=False, IncludeQualifiers=True)

    def test_search_None(self):
        """
        Test search_paths with single string as path definition.  Compiles
        a single file and tests that file compiled
        """

        def moflog(msg):
            """Display message to moflog"""
            print(msg, file=self.logfile)

        skip_if_moftab_regenerated()

        mofcomp = MOFCompiler(
            MOFWBEMConnection(),
            verbose=False,
            log_func=moflog)

        try:
            mofcomp.compile_file(os.path.join(TEST_DMTF_CIMSCHEMA_MOF_DIR,
                                              'System',
                                              'CIM_ComputerSystem.mof'),
                                 NAME_SPACE)
            self.fail("Must fail with missing qualifier declaration")
        except MOFDependencyError as pe:
            assert re.search(
                r"Cannot compile element specifying qualifier .* "
                r"qualifier declaration .* not exist",
                pe.msg, re.IGNORECASE)


class TestParseError(MOFTest):
    """Test multiple mof compile errors. Each test should generate
       a defined error.
    """

    def test_error01(self):
        """Test missing statement end comment"""

        skip_if_moftab_regenerated()

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

        skip_if_moftab_regenerated()

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

        skip_if_moftab_regenerated()

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

        skip_if_moftab_regenerated()

        # TODO ks 6/16why does this generate end-of-file rather than more
        # logical error
        _file = os.path.join(TEST_DIR,
                             'testmofs',
                             'parse_error04.mof')
        try:
            self.mofcomp.compile_file(_file, NAME_SPACE)
            self.fail("Exception expected.")
        except MOFParseError as pe:
            self.assertEqual(pe.msg, 'Unexpected end of MOF')

    def test_invalid_scope(self):
        """
        Test for qualifier declaration scope with invalid keyword
        """
        mof_str = """
        Qualifier Association : boolean = false,
            Scope(badscopekeyword),
            Flavor(DisableOverride, ToSubclass);
        """

        skip_if_moftab_regenerated()

        try:
            self.mofcomp.compile_string(mof_str, NAME_SPACE)
            self.fail("Exception expected.")
        except MOFParseError:
            pass

    def test_invalid_scope2(self):
        """
        Test for qualifier declaration scope with invalid keyword "qualifier".
        Tests specifically for keyword qualifier as keyword because this
        was fixed in issue #2491.
        """
        mof_str = """
        Qualifier Association : boolean = false,
            Scope(qualiifier),
            Flavor(DisableOverride, ToSubclass);
        """

        skip_if_moftab_regenerated()

        try:
            self.mofcomp.compile_string(mof_str, NAME_SPACE)
            self.fail("Exception expected.")
        except MOFParseError:
            pass

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

        skip_if_moftab_regenerated()

        try:
            self.mofcomp.compile_string(mof_str, NAME_SPACE)
            self.fail("Exception expected.")
        except MOFParseError as pe:
            assert re.search(
                r"Cannot compile reference initialization .* instance alias "
                r".* not previously defined",
                pe.msg, re.IGNORECASE)

    def test_missing_superclass(self):
        """
        Test for missing superclass
        """
        mof_str = """
        class PyWBEM_Person : CIM_Blah {
        };
        """

        skip_if_moftab_regenerated()

        try:
            self.mofcomp.compile_string(mof_str, NAME_SPACE)
            self.fail("Exception expected.")
        except MOFDependencyError as pe:
            assert re.search(
                r"Cannot compile class .* superclass",
                pe.msg, re.IGNORECASE)

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

        skip_if_moftab_regenerated()

        self.mofcomp.compile_string(mof_str, NAME_SPACE)

    def test_instance_wo_class(self):
        """Test Current behavior for instance without class"""
        mof_str = """

        instance of ex_sampleClass
        {
            label1 = 9921;
            size = 1;
        };
        """

        skip_if_moftab_regenerated()

        try:
            self.mofcomp.compile_string(mof_str, NAME_SPACE)
            self.fail("Exception expected.")
        except MOFDependencyError as pe:
            assert re.search(
                r"Cannot compile instance .* class .* not exist",
                pe.msg, re.IGNORECASE)

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

        skip_if_moftab_regenerated()

        self.mofcomp.compile_string(mof_str, NAME_SPACE)

    def test_missing_namespace_pragma_value_name(self):
        """Test Current behavior where #pragma namespace contains no
           namespace name."""
        mof_str = """
        #pragma namespace ()
        Qualifier Key : boolean = false,
            Scope(property, reference),
            Flavor(DisableOverride, ToSubclass);
        """

        skip_if_moftab_regenerated()

        try:
            self.mofcomp.compile_string(mof_str, NAME_SPACE)
        except MOFParseError as pe:
            self.assertEqual(pe.msg, 'MOF grammar error')

    def test_missing_namespace_pragma_value(self):
        """Test Current behavior where spragma namespace contains no
           namespace."""
        mof_str = """
        #pragma namespace
        Qualifier Key : boolean = false,
            Scope(property, reference),
            Flavor(DisableOverride, ToSubclass);
        """

        skip_if_moftab_regenerated()

        try:
            self.mofcomp.compile_string(mof_str, NAME_SPACE)
        except MOFParseError as pe:
            self.assertEqual(pe.msg, 'MOF grammar error')

    def test_invalid_namespace_pragma_ns(self):
        """Test Current behavior where spragma namespace contains no
           namespace."""
        mof_str = """
        #pragma namespace http://acme.com/root/cimv2
        Qualifier Key : boolean = false,
            Scope(property, reference),
            Flavor(DisableOverride, ToSubclass);
        """

        skip_if_moftab_regenerated()

        try:
            self.mofcomp.compile_string(mof_str, NAME_SPACE)
        except MOFParseError as pe:
            self.assertEqual(pe.msg, 'MOF grammar error')


class TestPropertyAlternatives(MOFTest):
    """
        Test compile of a class with individual property alternatives
    """

    def test_array_type(self):
        """ Test compile of class with array property"""

        skip_if_moftab_regenerated()

        mof_str = "class PyWBEM_TestArray{\n    Uint32 arrayprop[];\n};"
        self.mofcomp.compile_string(mof_str, NAME_SPACE)

        repo = self.mofcomp.handle

        cl = repo.GetClass('PyWBEM_TestArray', namespace=NAME_SPACE,
                           LocalOnly=False, IncludeQualifiers=True)
        self.assertEqual(cl.properties['arrayprop'].type, 'uint32')
        self.assertEqual(cl.properties['arrayprop'].is_array, True)
        self.assertEqual(cl.properties['arrayprop'].array_size, None)

    def test_array_type_w_size(self):
        """ Test compile of class with array property with size"""

        skip_if_moftab_regenerated()

        mof_str = "class PyWBEM_TestArray{\n    Uint32 arrayprop[9];\n};"
        self.mofcomp.compile_string(mof_str, NAME_SPACE)

        repo = self.mofcomp.handle

        cl = repo.GetClass('PyWBEM_TestArray', namespace=NAME_SPACE,
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

        skip_if_moftab_regenerated()

        self.mofcomp.compile_file(os.path.join(TEST_DIR,
                                               'testmofs',
                                               'test_refs.mof'),
                                  NAME_SPACE)


class TestInstCompile(CIMObjectMixin, MOFTest):
    """ Test the compile of instances defined with a class"""

    def test_good_compile(self):
        """Execute test with file containing class and two instances."""

        skip_if_moftab_regenerated()

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

        # Get the embedded instance/object instancesand prepare them for
        # test against the the corresponding properties.
        instance_peo = None
        instance_pei = None
        for i in instances:
            if i['k1'] == 9924 and i['k2'] == 'SampleLabelZeroes':
                instance_peo = i
                instance_peo.path = None
            elif i['k1'] == 9923 and i['k2'] == 'SampleLabelValues1':
                instance_pei = i
                instance_pei.path = None

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
                self.assertEqual(i['peo'], instance_peo)
                self.assertEqual(i['pei'], instance_pei)

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
                self.fail("Cannot find required instance k1=%s, k2=%s" %
                          (i['k1'], i['k2']))

    def test_invalid_property(self):
        """Test compile of instance with undeclared property fails"""

        skip_if_moftab_regenerated()

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
            self.fail("Must fail with undeclared property")
        except MOFDependencyError as pe:
            assert re.search(
                r"Cannot compile instance .* property .* not declared",
                pe.msg, re.IGNORECASE)

    def test_dup_property(self):
        """Test compile of instance with duplicated property fails"""

        skip_if_moftab_regenerated()

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
            self.fail("Must fail with duplicate property name")
        except MOFParseError as pe:
            assert re.search(
                r"Cannot compile instance .* property .* more than once",
                pe.msg, re.IGNORECASE)

    def test_mismatch_property(self):
        """Test compile of instance with duplicated property fails"""

        skip_if_moftab_regenerated()

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
            self.fail("Must fail with invalid property value")
        except MOFParseError as pe:
            assert re.search(
                r"Cannot compile instance .* property .* invalid value",
                pe.msg, re.IGNORECASE)

    # TODO add test for array value in inst, not scalar


class TestTypes(CIMObjectMixin, MOFTest):
    """Test for all CIM data types in a class mof"""

    def test_all(self):
        """Execute test"""

        skip_if_moftab_regenerated()

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


class TestToInstanceFlavor(CIMObjectMixin, MOFTest):
    """ Test variations on use of ToInstance Flavor"""

    def test_no_toinstance_flavor(self):
        """ Test that this is not attached to tosubclass flavor by
            compiler in qualifier decl or in class creation from that
            qualifier.  """

        skip_if_moftab_regenerated()

        mof_str = 'Qualifier Tst: boolean = true, Scope(class),'\
                  ' Flavor(ToSubclass);\n' \
                  '[Tst]\n' \
                  'class Py_ToInst{\n' \
                  '};'
        self.mofcomp.compile_string(mof_str, NAME_SPACE)

        repo = self.mofcomp.handle
#        repo.default_namespace = NAME_SPACE

        # compare qualifier declaration
        scope_def = _build_scope(set_true=['CLASS'])
        qld = repo.GetQualifier('Tst', namespace=NAME_SPACE)
        cmp_qld = CIMQualifierDeclaration('Tst', 'boolean', value=True,
                                          scopes=scope_def,
                                          tosubclass=True)
        self.assertEqual(qld, cmp_qld)

        # compare classes
        cl = repo.GetClass('Py_ToInst', namespace=NAME_SPACE,
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

        skip_if_moftab_regenerated()

        mof_str = 'Qualifier Tst: boolean = true, Scope(class),'\
                  ' Flavor(ToSubclass, ToInstance);\n' \
                  '[Tst]\n' \
                  'class Py_ToInst{\n' \
                  '};'
        self.mofcomp.compile_string(mof_str, NAME_SPACE)

        repo = self.mofcomp.handle

        # compare qualifier declaration
        scope_def = _build_scope(set_true=['CLASS'])
        qld = repo.GetQualifier('Tst', namespace=NAME_SPACE)
        cmp_qld = CIMQualifierDeclaration('Tst', 'boolean', value=True,
                                          scopes=scope_def,
                                          tosubclass=True, toinstance=True)
        self.assertEqual(qld, cmp_qld)

        # compare classes
        cl = repo.GetClass('Py_ToInst', namespace=NAME_SPACE,
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

        self.saved_t_error = _mof_compiler.t_error
        _mof_compiler.t_error = test_t_error

    def tearDown(self):
        _mof_compiler.t_error = self.saved_t_error

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

            if act_token is None and exp_token is not None:
                self.fail("Not enough tokens found, expected: %r" % exp_token)

            if act_token is not None and exp_token is None:
                self.fail("Too many tokens found: %r" % act_token)

            # We have both an expected and an actual token
            if isinstance(exp_token, LexErrorToken):
                # We expect an error
                if self.last_error_t is None:
                    self.fail("t_error() was not called as expected, "
                              "actual token: %r" % act_token)

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
        skip_if_moftab_regenerated()
        self.run_assert_lexer("", [])

    def test_simple(self):
        """Test a simple list of tokens."""
        skip_if_moftab_regenerated()
        input_data = "a 42"
        exp_tokens = [
            self.lex_token('IDENTIFIER', 'a', 1, 0),
            self.lex_token('decimalValue', 42, 1, 2),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_no_ws_delimiter(self):
        """Test that no whitespace is needed to delimit tokens."""
        skip_if_moftab_regenerated()
        input_data = "0f"
        exp_tokens = [
            self.lex_token('decimalValue', 0, 1, 0),
            self.lex_token('IDENTIFIER', 'f', 1, 1),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_ignore_space(self):
        """Test that space is ignored, but triggers new token."""
        skip_if_moftab_regenerated()
        input_data = "a b"
        exp_tokens = [
            self.lex_token('IDENTIFIER', 'a', 1, 0),
            self.lex_token('IDENTIFIER', 'b', 1, 2),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_ignore_cr(self):
        """Test that CR is ignored, but triggers new token."""
        skip_if_moftab_regenerated()
        input_data = "a\rb"
        exp_tokens = [
            self.lex_token('IDENTIFIER', 'a', 1, 0),
            self.lex_token('IDENTIFIER', 'b', 1, 2),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_ignore_tab(self):
        """Test that TAB is ignored, but triggers new token."""
        skip_if_moftab_regenerated()
        input_data = "a\tb"
        exp_tokens = [
            self.lex_token('IDENTIFIER', 'a', 1, 0),
            self.lex_token('IDENTIFIER', 'b', 1, 2),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_invalid_token(self):
        """Test that an invalid token is recognized as error."""
        skip_if_moftab_regenerated()
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
        skip_if_moftab_regenerated()
        input_data = "0"
        exp_data = 0
        exp_tokens = [
            self.lex_token('decimalValue', exp_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_decimal_plus_0(self):
        """Test a decimal number +0."""
        skip_if_moftab_regenerated()
        input_data = "+0"
        exp_data = 0
        exp_tokens = [
            self.lex_token('decimalValue', exp_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_decimal_minus_0(self):
        """Test a decimal number -0."""
        skip_if_moftab_regenerated()
        input_data = "-0"
        exp_data = 0
        exp_tokens = [
            self.lex_token('decimalValue', exp_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_decimal_small(self):
        """Test a small decimal number."""
        skip_if_moftab_regenerated()
        input_data = "12345"
        exp_data = 12345
        exp_tokens = [
            self.lex_token('decimalValue', exp_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_decimal_small_plus(self):
        """Test a small decimal number with +."""
        skip_if_moftab_regenerated()
        input_data = "+12345"
        exp_data = 12345
        exp_tokens = [
            self.lex_token('decimalValue', exp_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_decimal_small_minus(self):
        """Test a small decimal number with -."""
        skip_if_moftab_regenerated()
        input_data = "-12345"
        exp_data = -12345
        exp_tokens = [
            self.lex_token('decimalValue', exp_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_decimal_long(self):
        """Test a decimal number that is long."""
        skip_if_moftab_regenerated()
        input_data = "12345678901234567890"
        exp_data = 12345678901234567890
        exp_tokens = [
            self.lex_token('decimalValue', exp_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    # Binary numbers

    def test_binary_0b(self):
        """Test a binary number 0b."""
        skip_if_moftab_regenerated()
        input_data = "0b"
        exp_data = 0
        exp_tokens = [
            self.lex_token('binaryValue', exp_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_binary_0B(self):
        # pylint: disable=invalid-name
        """Test a binary number 0B (upper case B)."""
        skip_if_moftab_regenerated()
        input_data = "0B"
        exp_data = 0
        exp_tokens = [
            self.lex_token('binaryValue', exp_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_binary_small(self):
        """Test a small binary number."""
        skip_if_moftab_regenerated()
        input_data = "101b"
        exp_data = 0b101
        exp_tokens = [
            self.lex_token('binaryValue', exp_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_binary_small_plus(self):
        """Test a small binary number with +."""
        skip_if_moftab_regenerated()
        input_data = "+1011b"
        exp_data = 0b1011
        exp_tokens = [
            self.lex_token('binaryValue', exp_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_binary_small_minus(self):
        """Test a small binary number with -."""
        skip_if_moftab_regenerated()
        input_data = "-1011b"
        exp_data = -0b1011
        exp_tokens = [
            self.lex_token('binaryValue', exp_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_binary_long(self):
        """Test a binary number that is long."""
        skip_if_moftab_regenerated()
        input_data = "1011001101001011101101101010101011001011111001101b"
        exp_data = 0b1011001101001011101101101010101011001011111001101
        exp_tokens = [
            self.lex_token('binaryValue', exp_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_binary_leadingzero(self):
        """Test a binary number with a leading zero."""
        skip_if_moftab_regenerated()
        input_data = "01b"
        exp_data = 0b01
        exp_tokens = [
            self.lex_token('binaryValue', exp_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_binary_leadingzeros(self):
        """Test a binary number with two leading zeros."""
        skip_if_moftab_regenerated()
        input_data = "001b"
        exp_data = 0b001
        exp_tokens = [
            self.lex_token('binaryValue', exp_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    # Octal numbers

    def test_octal_00(self):
        """Test octal number 00."""
        skip_if_moftab_regenerated()
        input_data = "00"
        exp_data = 0
        exp_tokens = [
            self.lex_token('octalValue', exp_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_octal_01(self):
        """Test octal number 01."""
        skip_if_moftab_regenerated()
        input_data = "01"
        exp_data = 0o01
        exp_tokens = [
            self.lex_token('octalValue', exp_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_octal_small(self):
        """Test a small octal number."""
        skip_if_moftab_regenerated()
        input_data = "0101"
        exp_data = 0o0101
        exp_tokens = [
            self.lex_token('octalValue', exp_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_octal_small_plus(self):
        """Test a small octal number with +."""
        skip_if_moftab_regenerated()
        input_data = "+01011"
        exp_data = 0o1011
        exp_tokens = [
            self.lex_token('octalValue', exp_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_octal_small_minus(self):
        """Test a small octal number with -."""
        skip_if_moftab_regenerated()
        input_data = "-01011"
        exp_data = -0o1011
        exp_tokens = [
            self.lex_token('octalValue', exp_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_octal_long(self):
        """Test an octal number that is long."""
        skip_if_moftab_regenerated()
        input_data = "07051604302011021104151151610403031021011271071701"
        exp_data = 0o7051604302011021104151151610403031021011271071701
        exp_tokens = [
            self.lex_token('octalValue', exp_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_octal_leadingzeros(self):
        """Test an octal number with two leading zeros."""
        skip_if_moftab_regenerated()
        input_data = "001"
        exp_data = 0o001
        exp_tokens = [
            self.lex_token('octalValue', exp_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    # Hex numbers

    def test_hex_0x0(self):
        """Test hex number 0x0."""
        skip_if_moftab_regenerated()
        input_data = "0x0"
        exp_data = 0o0
        exp_tokens = [
            self.lex_token('hexValue', exp_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_hex_0X0(self):
        # pylint: disable=invalid-name
        """Test hex number 0X0."""
        skip_if_moftab_regenerated()
        input_data = "0X0"
        exp_data = 0x0
        exp_tokens = [
            self.lex_token('hexValue', exp_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_hex_0x1(self):
        """Test hex number 0x1."""
        skip_if_moftab_regenerated()
        input_data = "0x1"
        exp_data = 0x1
        exp_tokens = [
            self.lex_token('hexValue', exp_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_hex_0x01(self):
        """Test hex number 0x01."""
        skip_if_moftab_regenerated()
        input_data = "0x01"
        exp_data = 0x01
        exp_tokens = [
            self.lex_token('hexValue', exp_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_hex_small(self):
        """Test a small hex number."""
        skip_if_moftab_regenerated()
        input_data = "0x1F2a"
        exp_data = 0x1f2a
        exp_tokens = [
            self.lex_token('hexValue', exp_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_hex_small_plus(self):
        """Test a small hex number with +."""
        skip_if_moftab_regenerated()
        input_data = "+0x1F2a"
        exp_data = 0x1f2a
        exp_tokens = [
            self.lex_token('hexValue', exp_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_hex_small_minus(self):
        """Test a small hex number with -."""
        skip_if_moftab_regenerated()
        input_data = "-0x1F2a"
        exp_data = -0x1f2a
        exp_tokens = [
            self.lex_token('hexValue', exp_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_hex_long(self):
        """Test a hex number that is long."""
        skip_if_moftab_regenerated()
        input_data = "0x1F2E3D4C5B6A79801f2e3d4c5b6a79801F2E3D4C5B6A7980"
        exp_data = 0x1F2E3D4C5B6A79801f2e3d4c5b6a79801F2E3D4C5B6A7980
        exp_tokens = [
            self.lex_token('hexValue', exp_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_hex_leadingzeros(self):
        """Test a hex number with two leading zeros."""
        skip_if_moftab_regenerated()
        input_data = "0x00F"
        exp_data = 0x00F
        exp_tokens = [
            self.lex_token('hexValue', exp_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    # Floating point numbers

    def test_float_dot0(self):
        """Test a float number '.0'."""
        skip_if_moftab_regenerated()
        input_data = ".0"
        exp_data = 0.0
        exp_tokens = [
            self.lex_token('floatValue', exp_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_float_0dot0(self):
        """Test a float number '0.0'."""
        skip_if_moftab_regenerated()
        input_data = "0.0"
        exp_data = 0.0
        exp_tokens = [
            self.lex_token('floatValue', exp_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_float_plus_0dot0(self):
        """Test a float number '+0.0'."""
        skip_if_moftab_regenerated()
        input_data = "+0.0"
        exp_data = 0.0
        exp_tokens = [
            self.lex_token('floatValue', exp_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_float_minus_0dot0(self):
        """Test a float number '-0.0'."""
        skip_if_moftab_regenerated()
        input_data = "-0.0"
        exp_data = 0.0
        exp_tokens = [
            self.lex_token('floatValue', exp_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_float_small(self):
        """Test a small float number."""
        skip_if_moftab_regenerated()
        input_data = "123.45"
        exp_data = 123.45
        exp_tokens = [
            self.lex_token('floatValue', exp_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_float_small_plus(self):
        """Test a small float number with +."""
        skip_if_moftab_regenerated()
        input_data = "+123.45"
        exp_data = 123.45
        exp_tokens = [
            self.lex_token('floatValue', exp_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_float_small_minus(self):
        """Test a small float number with -."""
        skip_if_moftab_regenerated()
        input_data = "-123.45"
        exp_data = -123.45
        exp_tokens = [
            self.lex_token('floatValue', exp_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_float_long(self):
        """Test a float number that is long."""
        skip_if_moftab_regenerated()
        input_data = "1.2345678901234567890"
        exp_data = 1.2345678901234567890
        exp_tokens = [
            self.lex_token('floatValue', exp_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    # Errors

    def test_error_09(self):
        """Test '09' (decimal: no leading zeros; octal: digit out of range)."""
        skip_if_moftab_regenerated()
        input_data = "09 bla"
        exp_tokens = [
            self.lex_token('error', '09', 1, 0),
            self.lex_token('IDENTIFIER', 'bla', 1, 3),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_error_008(self):
        """Test '008' (decimal: no leading zeros; octal: digit out of range)."""
        skip_if_moftab_regenerated()
        input_data = "008 bla"
        exp_tokens = [
            self.lex_token('error', '008', 1, 0),
            self.lex_token('IDENTIFIER', 'bla', 1, 4),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_error_2b(self):
        """Test '2b' (decimal: b means binary; binary: digit out of range)."""
        skip_if_moftab_regenerated()
        input_data = "2b bla"
        exp_tokens = [
            self.lex_token('error', '2b', 1, 0),
            self.lex_token('IDENTIFIER', 'bla', 1, 3),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_error_9b(self):
        """Test '9b' (decimal: b means binary; binary: digit out of range)."""
        skip_if_moftab_regenerated()
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
        skip_if_moftab_regenerated()
        input_data = "02B bla"
        exp_tokens = [
            self.lex_token('error', '02B', 1, 0),
            self.lex_token('IDENTIFIER', 'bla', 1, 4),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_error_0dot(self):
        """Test '0.' (not a valid float, is parsed as a decimal '0' followed by
        an illegal character '.' which is skipped in t_error()."""
        skip_if_moftab_regenerated()
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
        skip_if_moftab_regenerated()
        input_data = '""'
        exp_tokens = [
            self.lex_token('stringValue', input_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_string_onechar(self):
        """Test a string with one character."""
        skip_if_moftab_regenerated()
        input_data = '"a"'
        exp_tokens = [
            self.lex_token('stringValue', input_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_string_long(self):
        """Test a long string with ASCII chars (no backslash or quotes)."""
        skip_if_moftab_regenerated()
        input_data = '"abcdefghijklmnopqrstuvwxyz 0123456789_.,:;?=()[]{}/&%$!"'
        exp_tokens = [
            self.lex_token('stringValue', input_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_string_one_sq(self):
        """Test a string with a single quote."""
        skip_if_moftab_regenerated()
        input_data = "\"'\""
        exp_tokens = [
            self.lex_token('stringValue', input_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_string_two_sq(self):
        """Test a string with two single quotes."""
        skip_if_moftab_regenerated()
        input_data = "\"''\""
        exp_tokens = [
            self.lex_token('stringValue', input_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_string_two_sq_char(self):
        """Test a string with two single quotes and a char."""
        skip_if_moftab_regenerated()
        input_data = "\"'a'\""
        exp_tokens = [
            self.lex_token('stringValue', input_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_string_one_dq(self):
        """Test a string with an escaped double quote."""
        skip_if_moftab_regenerated()
        input_data = "\"\\\"\""
        exp_tokens = [
            self.lex_token('stringValue', input_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_string_two_dq_char(self):
        """Test a string with two escaped double quotes and a char."""
        skip_if_moftab_regenerated()
        input_data = "\"\\\"a\\\"\""
        exp_tokens = [
            self.lex_token('stringValue', input_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)


class TestLexerChar(BaseTestLexer):
    """Lexer testcases for CIM datatype char16."""

    def test_char_char(self):
        """Test a char16 with one character."""
        skip_if_moftab_regenerated()
        input_data = "'a'"
        exp_tokens = [
            self.lex_token('charValue', input_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_char_space(self):
        """Test a char16 with one space."""
        skip_if_moftab_regenerated()
        input_data = "' '"
        exp_tokens = [
            self.lex_token('charValue', input_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_char_dquote(self):
        """Test a char16 with a double quote."""
        skip_if_moftab_regenerated()
        input_data = '\'"\''
        exp_tokens = [
            self.lex_token('charValue', input_data, 1, 0),
        ]
        self.run_assert_lexer(input_data, exp_tokens)

    def test_char_esquote(self):
        """Test a char16 with an escaped single quote."""
        skip_if_moftab_regenerated()
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

    def test_mof_schema_roundtrip(self):
        """ Test compile, of the schema, write of a new mof output file
            and recompile of that file
        """

        skip_if_moftab_regenerated()

        # original compile and write of output mof
        # start_time = time()
        self.mofcomp.compile_file(TEST_DMTF_CIMSCHEMA.schema_pragma_file,
                                  NAME_SPACE)
        # print('elapsed compile: %f  ' % (time() - start_time))

        repo = self.mofcomp.handle

        # Create file for mof output
        mofout_filename = os.path.join(TEST_DIR, TMP_FILE)

        # pylint: disable=consider-using-with
        mof_out_hndl = io.open(mofout_filename, 'w', encoding='utf-8')

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
        schema_mof = u"""
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

        skip_if_moftab_regenerated()

        schema_mof = self.define_partial_schema()

        # write the schema to a file in the schema directory
        self.partial_schema_file = 'test_partial_schema.mof'
        test_schemafile = os.path.join(TEST_DMTF_CIMSCHEMA_MOF_DIR,
                                       self.partial_schema_file)
        with io.open(test_schemafile, "w", encoding='utf-8') as sf:
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

        skip_if_moftab_regenerated()

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

        skip_if_moftab_regenerated()

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

        skip_if_moftab_regenerated()

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

        skip_if_moftab_regenerated()

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
            self.fail("Must fail with MOF file for dependent class not found")
        except MOFDependencyError as pe:
            assert re.search(
                r"Cannot compile class .* dependent class .* not exist",
                pe.msg, re.IGNORECASE)

    def test_compile_class_embinst(self):
        """
        Test compile a single class with property and method param containing
        embedded instance.
        """

        skip_if_moftab_regenerated()

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

        skip_if_moftab_regenerated()

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
            self.fail("Must fail with MOF file for dependent class not found")
        except MOFDependencyError as pe:
            assert re.search(
                r"Cannot compile class .* dependent class .* not exist",
                pe.msg, re.IGNORECASE)

    def test_compile_class_circular(self):
        """
        Test compile a class that itself contains a circular reference, in this
        case a reference to itself through the EmbeddedInstance qualifier.
        """

        skip_if_moftab_regenerated()

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

        self.mofcomp = MOFCompiler(
            MOFWBEMConnection(),
            verbose=False,
            log_func=moflog)

    def test_file_not_found(self):
        """
            Test for case where compile file does not exist.
        """
        skip_if_moftab_regenerated()
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
        skip_if_moftab_regenerated()
        self.create_mofcompiler()
        try:
            self.mofcomp.compile_file(
                os.path.join(TEST_DMTF_CIMSCHEMA_MOF_DIR, 'System',
                             'CIM_ComputerSystemx.mof'),
                NAME_SPACE)
        except IOError:
            pass


######################################################################
#
#  Test for duplicate inst in CreateInstance mof compiler logic
#
######################################################################

class MOFWBEMConnectionInstDups(MOFWBEMConnection):
    """
    An adaptation of MOFWBEMConnection class that changes the instance to test
    the compiler CreateInstance duplicate instance logic.

    It changes the instance repository to a dictionary, adds a tests for
    duplicate instance names in CreateInstance, and enables a very simple
    ModifyInstance.
    """

    def __init__(self, conn=None):
        """
        Parameters:

          conn (BaseRepositoryConnection):
            The underlying repository connection.

            `None` means that there is no underlying repository and all
            operations performed through this object will fail.
        """

        super(MOFWBEMConnectionInstDups, self).__init__(conn=conn)

    def ModifyInstance(self, *args, **kwargs):
        """This method is used by the MOF compiler only in the course of
        handling CIM_ERR_ALREADY_EXISTS after trying to create an instance.

        NOTE: It does NOT support the propertylist attribute that is part
        of the CIM/XML defintion of ModifyInstance and it requires that
        each created instance include the instance path which means that
        the MOF must include the instance alias on each created instance.
        """
        mod_inst = args[0] if args else kwargs['ModifiedInstance']
        ns = mod_inst.path.namespace
        if ns not in self.instances:
            raise CIMError(
                CIM_ERR_INVALID_NAMESPACE,
                _format('ModifyInstance failed. No instance repo exists. '
                        'Use compiler instance alias to set path on '
                        'instance declaration. inst: {0!A}', mod_inst))

        if mod_inst.path not in self.instances[ns]:
            raise CIMError(
                CIM_ERR_NOT_FOUND,
                _format('ModifyInstance failed. No instance exists. '
                        'Use compiler instance alias to set path on '
                        'instance declaration. inst: {0!A}', mod_inst))

        orig_instance = self.instances[ns][mod_inst.path]
        orig_instance.update(mod_inst.properties)
        self.instances[ns][mod_inst.path] = orig_instance

    def CreateInstance(self, *args, **kwargs):
        """
        Create a CIM instance in the local repository of this class. This
        implementation tests for duplicate instances and returns an error if
        they exist.  Note that the CreateInstance must build the instance.path
        since the compiler leaves the NewInstance path as None

        For a description of the parameters, see
        :meth:`pywbem.WBEMConnection.CreateInstance`.
        """

        inst = args[0] if args else kwargs['NewInstance']

        ns = kwargs.get('namespace', self.default_namespace)

        cls = self.GetClass(inst.classname, namespace=ns, LocalOnly=False,
                            IncludeQualifiers=True)
        inst.path = CIMInstanceName.from_instance(
            cls, inst, namespace=ns)

        if ns not in self.instances:
            self.instances[ns] = {}

        if ns in self.instances:
            if inst.path in self.instances[ns]:
                raise CIMError(
                    CIM_ERR_ALREADY_EXISTS,
                    _format('CreateInstance failed. Instance with path {0!A} '
                            'already exists in CIM repository', inst.path))
        try:
            self.instances[ns][inst.path] = inst
        except KeyError:
            self.instances[ns] = {}
            self.instances[ns][inst.path] = inst
        return inst.path


class Test_CreateInstanceWithDups(unittest.TestCase):
    """
    Testcases for the MOF compiler with duplicate instances.
    """

    def setUp(self):
        """Create the MOF compiler."""

        def moflog(msg):
            """Display message to moflog"""
            print(msg, file=self.logfile)

        moflog_file = os.path.join(TEST_DIR, 'moflog.txt')
        # pylint: disable=consider-using-with
        self.logfile = io.open(moflog_file, 'w', encoding='utf-8')
        self.mofcomp = MOFCompiler(
            MOFWBEMConnectionInstDups(),
            search_paths=[TEST_DMTF_CIMSCHEMA_MOF_DIR],
            verbose=False,
            log_func=moflog)

        self.partial_schema_file = None

    def tearDown(self):
        """Close the log file and any partial schema file."""
        self.logfile.close()
        if self.partial_schema_file:
            if os.path.exists(self.partial_schema_file):
                os.remove(self.partial_schema_file)

    def test_nopath(self):
        """
        Test no alias on instance. Result should include path in the repo
        """

        mof_str = """
        Qualifier Key : boolean = false,
            Scope(property, reference),
            Flavor(DisableOverride, ToSubclass);

        class TST_Person{
            [Key] string name;
            Uint32 value;
        };

        instance of TST_Person { name = "Mike"; value = 1;};
        """
        skip_if_moftab_regenerated()

        self.mofcomp.compile_string(mof_str, NAME_SPACE)
        repo = self.mofcomp.handle

        path = CIMInstanceName("TST_Person", keybindings={'name': "Mike"},
                               namespace=NAME_SPACE)

        # This test because there is no GetInstance in MOFWBEMConnectionInstDups
        assert len(repo.instances) == 1
        assert len(repo.instances[NAME_SPACE]) == 1
        assert path in repo.instances[NAME_SPACE]


class TestNamespacePragma(MOFTest):
    """Test use of the namespace pragma"""

    def test_single_namespace(self):
        """
        Test that uses namespace pragma. NOTE: This only tests the use
        of the pragma, not using it for different namespace and that
        instances are created in the pragma defined namespace. Since the test
        uses MOFWBEMConnection as the repository which always creates a
        new namespace it cannot test for invalid namespace
        """

        mof_str = """
            #pragma namespace ("root/test")
            Qualifier Key : boolean = false,
                Scope(property, reference),
                Flavor(DisableOverride, ToSubclass);

            class TST_Person{
                [Key] string name;
                Uint32 value;
            };

            instance of TST_Person as $Mike { name = "Mike"; value = 1;};

            instance of TST_Person as $Fred { name = "Fred"; value = 2;};
        """
        skip_if_moftab_regenerated()

        test_namespace = 'root/test'
        self.mofcomp.compile_string(mof_str, test_namespace)

        repo = self.mofcomp.handle

        namespaces = repo.classes.keys()

        assert len(namespaces) == 1
        assert test_namespace in namespaces

        cl = repo.GetClass('TST_Person', namespace=test_namespace,
                           LocalOnly=False, IncludeQualifiers=True)

        self.assertEqual(cl.properties['name'].type, 'string')

        self.assertEqual(len(repo.instances[NAME_SPACE]), 2)

    def test_invalid_namespace(self):
        """
        Test that uses namespace pragma. NOTE: This only tests the use
        of the pragma, not using it for different namespace and that
        instances are created in the pragma defined namespace. Since the test
        uses MOFWBEMConnection as the repository which always creates a
        new namespace it cannot test for invalid namespace
        """

        mof_str = """
            #pragma namespace ("http://acme.com/root/test")
            Qualifier Key : boolean = false,
                Scope(property, reference),
                Flavor(DisableOverride, ToSubclass);

            class TST_Person{
                [Key] string name;
                Uint32 value;
            };
        """
        skip_if_moftab_regenerated()

        test_namespace = 'root/test'
        try:
            self.mofcomp.compile_string(mof_str, test_namespace)
            assert(False)
        except MOFParseError:
            pass


EMBEDDED_INSTANCE_TEST_MOF = """

    Qualifier Key : boolean = false,
        Scope(property, reference),
        Flavor(DisableOverride, ToSubclass);

    Qualifier Description : string = null,
        Scope(any),
        Flavor(EnableOverride, ToSubclass, Translatable);

    Qualifier EmbeddedInstance : string = null,
        Scope(property, method, parameter),
        Flavor(DisableOverride, ToSubclass);

    Qualifier EmbeddedObject : boolean = false,
        Scope(property, method, parameter),
        Flavor(DisableOverride, ToSubclass);

    class TST_Embedded1 {
        boolean Bool1;

        string Str1;

            [Description ( "Recursive embed" ),
                EmbeddedInstance ( "TST_Embedded1" )]
        string RecursedEmbed;
    };

         [Description ("Test class that contains embedded properties")]
    class TST_Container {
            [Key, Description ("Key property")]
        string InstanceID;

            [Description ( "Scalar Embedded Instance Property" ),
                EmbeddedInstance ( "TST_Embedded1" )]
        string EmbedInstanceScalar;

            [Description ( "Scalar Embedded Object Property" ),
                EmbeddedObject]
        string EmbedObjectScalar;

            [Description ( "Array Embedded Instance Property" ),
                EmbeddedInstance ( "TST_Embedded1" )]
        string EmbedInstanceArray[];

            [Description ( "Array Embedded Object Property" ),
                EmbeddedObject]
        string EmbedObjectArray[];
    };

    // See issue # 2330. EOL in embedded instance fails
    //instance of TST_Container {
    //    InstanceID = "AllWaysCompiled";
    //    EmbedInstanceScalar = "instance of TST_Embedded1 {"
    //              "Bool1 = true;"
    //              "};";
    //};
"""

OK = True
RUN = True
FAIL = False

TESTCASES_EMBEDDED_OBJECT_PROP_COMPILE = [

    # Testcases for EmbeddedObject Property compile tests

    # Each list item is a testcase tuple with these items:
    # * desc: Short testcase description.
    # * kwargs: Keyword arguments for the test function:
    #   * id: The value of the InstanceID property
    #   * prname: name of the embedded instance property
    #   * pstr: String containing mof for property
    #   * exp_dict:
    #           EmbeddedObject: Expected embedded_object attrribute value
    #           Array: True if Array property
    # * exp_exc_types: Expected exception type(s), or None.
    # * exp_warn_types: Expected warning type(s), or None.
    # * condition: Boolean condition for testcase to run, or 'pdb' for debugger
    # NOTE: All embedded property mof defintions that are python strings must
    # define any included EOL with either the python raw (r'<string' or double
    # \\ (\\n).

    (
        "Test creation of Scalar EmbeddedInstance property",
        dict(
            iid='TSTScalarInstance',
            pname='EmbedInstanceScalar',
            pstr="instance of TST_Embedded1 {\\n"
                 "Bool1 = true;\\n"
                 "};\\n",
            exp_dict=dict(
                EmbeddedObject='instance',
                Array=False,
            ),
        ),
        None, None, RUN
    ),
    (
        "Test creation of Scalar EmbeddedInstance property defined with r",
        dict(
            iid='TSTScalarInstance_rawstring',
            pname='EmbedInstanceScalar',
            pstr=r"instance of TST_Embedded1 {\n"
                 r"Bool1 = true;\n"
                 r"};\n",
            exp_dict=dict(
                EmbeddedObject='instance',
                Array=False,
            ),
        ),
        None, None, RUN
    ),

    (
        "Test creation of EmbeddedInstance property Array type, one property",
        dict(
            iid='TSTArrayInstance',
            pname='EmbedInstanceArray',
            pstr=['instance of TST_Embedded1 {\\n'
                  'Bool1 = false;\\n'
                  '};\\n'],
            exp_dict=dict(
                EmbeddedObject='instance',
                Array=True,
                Size=1
            ),
        ),
        None, None, OK
    ),

    (
        "Test creation of EmbeddedInstance property Array type  more props",
        dict(
            iid='TSTArrayInstance_multiple_properties',
            pname='EmbedInstanceArray',
            pstr=["instance of TST_Embedded1 {\\n"
                  "Bool1 = false;\\n"
                  "};\\n",
                  "instance of TST_Embedded1 {\\n"
                  "Bool1 = true;\\n"
                  "};\\n", ],
            exp_dict=dict(
                EmbeddedObject='instance',
                Array=True,
                Size=2
            ),
        ),
        None, None, OK
    ),

    (
        "Test creation of simple EmbeddedObject property",
        dict(
            iid='test_embedded_object_scalar',
            pname='EmbedObjectScalar',
            pstr="instance of TST_Embedded1 {"
                 "Bool1 = true;"
                 "};",
            exp_dict=dict(
                EmbeddedObject='object',
                Array=False,
            ),
        ),
        None, None, OK
    ),

    (
        "Test for compile error in embedded instance string",
        dict(
            iid='test_compile_error',
            pname='EmbedObjectScalar',
            pstr="instancex of TST_Embedded1 {"
                 "Bool1 = true;"
                 "};",
            exp_dict=dict(
                EmbeddedObject='object',
                Array=False,
            ),
        ),
        MOFParseError, None, OK
    ),

    (
        "Test for Classname not found error in compile",
        dict(
            iid='test_classname_notfound',
            pname='EmbedObjectScalar',
            pstr="instance of TST_NoClass {"
                 "Bool1 = true;"
                 "};",
            exp_dict=dict(
                EmbeddedObject='object',
                Array=False,
            ),
        ),
        MOFDependencyError, None, OK
    ),

    (
        "Test for embeddedproperty not found error in compile",
        dict(
            iid='test_embedded-property_notfound',
            pname='EmbedObjectScalar',
            pstr="instancex of TST_Embedded1 {"
                 "Bool1NotFound = true;"
                 "};",
            exp_dict=dict(
                EmbeddedObject='object',
                Array=False,
            ),
        ),
        MOFParseError, None, OK
    ),

    (
        "Test for property not found error in compile",
        dict(
            iid='test_property_notfound',
            pname='EmbedObjectScalarNOTFOUND',
            pstr="instancex of TST_Embedded1 {"
                 "Bool1NotFound = true;"
                 "};",
            exp_dict=dict(
                EmbeddedObject='object',
                Array=False,
            ),
        ),
        MOFDependencyError, None, OK
    ),

    (
        "Test for property not found error in compile",
        dict(
            iid='test_invalidpropname',
            pname='EmbedObjectScalar-invalid',
            pstr="instancex of TST_Embedded1 {"
                 "Bool1NotFound = true;"
                 "};",
            exp_dict=dict(
                EmbeddedObject='object',
                Array=False,
            ),
        ),
        MOFParseError, None, OK
    ),

    (
        "Test creation compile fails arrayness mismatch",
        dict(
            iid='TSTScalarInstanceError_arrayness',
            pname='EmbedInstanceScalar',
            pstr=["instance of TST_Embedded1 {"
                  "Bool1 = false;"
                  "};",
                  "instance of TST_Embedded1 {"
                  "Bool1 = true;"
                  "};", ],
            exp_dict=dict(
                EmbeddedObject='instance',
                Array=False,
            ),
        ),
        MOFParseError, None, OK
    ),

    (
        "Test creation compile class fails arrayness mismatch",
        dict(
            iid='TSTScalarInstanceError',
            pname='EmbedInstanceScalar',
            pstr="class blah{"
                 "boolean Bool1"
                 "};",
            exp_dict=dict(
                EmbeddedObject='instance',
                Array=False,
            ),
        ),
        MOFParseError, None, OK
    ),
    (
        "Test creation compile fail single \n in embededinstancename",
        dict(
            iid='TSTScalarInstanceError',
            pname='EmbedInstanceScalar',
            pstr="class blah{\n"
                 "boolean Bool1"
                 "};",
            exp_dict=dict(
                EmbeddedObject='instance',
                Array=False,
            ),
        ),
        MOFParseError, None, OK
    ),
    (
        "Test embedded qualifierdecl creation fails",
        dict(
            iid='TSTQualDeclCreationError',
            pname='EmbedInstanceScalar',
            pstr="Qualifier Key : boolean = false, "
                 "Scope(property, reference),"
                 "Flavor(DisableOverride, ToSubclass);"
                 "};",
            exp_dict=dict(
                EmbeddedObject='instance',
                Array=False,
            ),
        ),
        MOFParseError, None, OK
    ),

]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_EMBEDDED_OBJECT_PROP_COMPILE)
@simplified_test_function
def test_embedded_object_property_compile(testcase, iid, pname, pstr, exp_dict):
    # pylint: disable=unused-argument
    """
    Test embedded object instances
    """
    # Create the instance mof from the following template of a property with
    # embedded instance value (i.e. scalar with one string or array with
    # multiple strings)
    embed_inst_template = 'instance of TST_Container {{ ' \
                          'InstanceID = {0}; ' \
                          '{1} = {2};' \
                          '}};'
    if exp_dict['Array']:
        array_strings = []
        for strx in pstr:
            array_strings.append('"{0}"'.format(strx))

        embedd_inst_value = "{{ {0} }}".format(", ".join(array_strings))
        inst_mof = embed_inst_template.format(iid, pname, embedd_inst_value)
    else:
        pstr = '"{0}"'.format(pstr)
        inst_mof = embed_inst_template.format(iid, pname, pstr)

    conn = FakedWBEMConnection()
    conn.compile_mof_string(EMBEDDED_INSTANCE_TEST_MOF, verbose=False)

    # Code to test - Compile the instance of TST_Container defined for the test
    conn.compile_mof_string(inst_mof)

    # Validate instance(s) created

    path = CIMInstanceName("TST_Container", keybindings=dict(InstanceID=iid))
    rtn_inst = conn.GetInstance(path)
    rtn_property = rtn_inst.properties[pname]

    # Validate returned property type and embedded_object attribute
    assert rtn_property.type == 'string'
    rtn_property_value = rtn_property.value
    assert exp_dict['EmbeddedObject'] == rtn_property.embedded_object

    # Test for embedded object type, number of items, and classname
    if exp_dict['Array']:
        assert exp_dict['Size'] == len(rtn_property_value)
        for pvalue in rtn_property_value:
            assert isinstance(pvalue, CIMInstance)
            assert pvalue.classname == 'TST_Embedded1'
    else:
        assert isinstance(rtn_property_value, CIMInstance)
        assert rtn_property_value.classname == 'TST_Embedded1'


if __name__ == '__main__':
    unittest.main()
