#!/usr/bin/env python

"""
Test CIM operations against a real WBEM server that is specified on the
command line.

The return codes here may be specific to OpenPegasus.
"""

# pylint: disable=missing-docstring,superfluous-parens,no-self-use
import sys
from datetime import timedelta
import unittest
from getpass import getpass
import six

from pywbem.cim_constants import *
from pywbem import CIMInstance, CIMInstanceName, CIMClass, CIMProperty, \
                   CIMQualifier, CIMQualifierDeclaration, CIMMethod, \
                   WBEMConnection, CIMError, \
                   Uint8, Uint16, Uint32, Uint64, \
                   Sint8, Sint16, Sint32, Sint64, \
                   Real32, Real64, CIMDateTime, ParseError
from pywbem.cim_operations import CIMError, DEFAULT_NAMESPACE,  \
                                  check_utf8_xml_chars

#decocrator for unimplemented tests
UNIMPLEMENTED = unittest.skip("test not implemented")

# A class that should be implemented and is used for testing
TEST_CLASS = 'CIM_ComputerSystem'

class ClientTest(unittest.TestCase):
    """A base class that creates a pywbem.WBEMConnection for
    subclasses to use."""

    def setUp(self):
        """Create a connection."""
        global args

        self.system_url = args['url']
        self.namespace = args['namespace']

        self.log('setup connection {} ns {}'.format(self.system_url,
                                                    self.namespace))
        self.conn = WBEMConnection(
            self.system_url,
            (args['username'], args['password']),
            self.namespace,
            timeout=args['timeout'])
        self.conn.debug = args['debug']
        self.log('Connected {}, ns {}'.format(self.system_url,
                                              args['namespace']))

    def cimcall(self, fn, *fargs, **kw):
        """Make a PyWBEM call and log the request and response XML."""
        self.log('cimcall args *args {} kwargs {}'.format(args, kw))
        try:
            result = fn(*fargs, **kw)
        except Exception as exc:
            self.log('Operation %s failed with %s: %s\n' % \
                     (fn.__name__, exc.__class__.__name__, str(exc)))
            last_request = self.conn.last_request or self.conn.last_raw_request
            self.log('Request:\n\n%s\n' % last_request)
            last_reply = self.conn.last_reply or self.conn.last_raw_reply
            self.log('Reply:\n\n%s\n' % last_reply)
            raise

        self.log('Operation %s succeeded\n' % fn.__name__)
        last_request = self.conn.last_request or self.conn.last_raw_request
        self.log('Request:\n\n%s\n' % last_request)
        last_reply = self.conn.last_reply or self.conn.last_raw_reply
        self.log('Reply:\n\n%s\n' % last_reply)

        return result

    def log(self, data_):
        if args['verbose']:
            print('{}'.format(data_))

    ## TODO this is where we should disconnect the client
    def tearDown(self):
        self.log('FUTURE: disconnect this connection')


#################################################################
# Instance provider interface tests
#################################################################

class EnumerateInstanceNames(ClientTest):

    def test_all(self):

        # Single arg call

        names = self.cimcall(self.conn.EnumerateInstanceNames,
                             TEST_CLASS)

        self.assertTrue(len(names) >= 1)

        for name in names:
            self.assertTrue(isinstance(name, CIMInstanceName))
            self.assertTrue(len(name.namespace) > 0)
            self.assertTrue(name.namespace == self.namespace)


        # Call with explicit CIM namespace that exists

        self.cimcall(self.conn.EnumerateInstanceNames,
                     TEST_CLASS,
                     namespace=self.conn.default_namespace)

        # Call with explicit CIM namespace that does not exist

        try:

            self.cimcall(self.conn.EnumerateInstanceNames,
                         TEST_CLASS,
                         namespace='root/blah')

        except CIMError as ce:
            if ce.args[0] != CIM_ERR_INVALID_NAMESPACE:
                raise

class EnumerateInstances(ClientTest):

    def test_all(self):

        # Simplest invocation

        instances = self.cimcall(self.conn.EnumerateInstances,
                                 TEST_CLASS)

        self.assertTrue(len(instances) >= 1)

        for i in instances:
            self.assertTrue(isinstance(i, CIMInstance))
            self.assertTrue(isinstance(i.path, CIMInstanceName))
            self.assertTrue(len(i.path.namespace) > 0)
            self.assertTrue(i.path.namespace == self.namespace)

        # Call with explicit CIM namespace that exists

        self.cimcall(self.conn.EnumerateInstances,
                     TEST_CLASS,
                     namespace=self.conn.default_namespace)

        # Call with explicit CIM namespace that does not exist

        try:

            self.cimcall(self.conn.EnumerateInstances,
                         TEST_CLASS,
                         namespace='root/blah')

        except CIMError as ce:
            if ce.args[0] != CIM_ERR_INVALID_NAMESPACE:
                raise


class ExecQuery(ClientTest):

    def test_all(self):

        try:

            # Simplest invocation

            instances = self.cimcall(self.conn.ExecQuery,
                                     'wql',
                                     'Select * from %s' % TEST_CLASS)

            self.assertTrue(len(instances) >= 1)

            for i in instances:
                self.assertTrue(isinstance(i, CIMInstance))
                self.assertTrue(isinstance(i.path, CIMInstanceName))
                self.assertTrue(len(i.path.namespace) > 0)

            # Call with explicit CIM namespace that does not exist

            try:

                self.cimcall(self.conn.ExecQuery,
                             'wql',
                             'Select * from %s' % TEST_CLASS,
                             namespace='root/blah')

            except CIMError as ce:
                if ce.args[0] != CIM_ERR_INVALID_NAMESPACE:
                    raise

        except CIMError as ce:
            if ce.args[0] == CIM_ERR_NOT_SUPPORTED:
                raise AssertionError(
                    "CIM_ERR_NOT_SUPPORTED: The WBEM server doesn't" \
                    " support ExecQuery for this query")
            if ce.args[0] == CIM_ERR_QUERY_LANGUAGE_NOT_SUPPORTED:
                raise AssertionError(
                    "CIM_ERR_QUERY_LANGUAGE_NOT_SUPPORTED: The WBEM" \
                    " server doesn't support WQL for ExecQuery")
            else:
                raise


class GetInstance(ClientTest):

    def test_all(self):

        inst_names = self.cimcall(self.conn.EnumerateInstanceNames, TEST_CLASS)
        self.assertTrue(len(inst_names) >= 1)
        name = inst_names[0] # Pick the first returned instance

        # Simplest invocation

        obj = self.cimcall(self.conn.GetInstance,
                           name)

        self.assertTrue(isinstance(obj, CIMInstance))
        self.assertTrue(isinstance(obj.path, CIMInstanceName))

        # Call with invalid namespace path

        invalid_name = name.copy()
        invalid_name.namespace = 'blahblahblah'

        try:
            self.cimcall(self.conn.GetInstance, invalid_name)

        except CIMError as ce:
            if ce.args[0] != CIM_ERR_INVALID_NAMESPACE:
                raise

class CreateInstance(ClientTest):

    def test_all(self):

        # Test instance

        instance = CIMInstance(
            'PyWBEM_Person',
            {'CreationClassName': 'PyWBEM_Person',
             'Name': 'Test'},
            path=CIMInstanceName('PyWBEM_Person',
                                 {'CreationClassName': 'PyWBEM_Person',
                                  'Name': 'Test'}))

        # Delete if already exists

        try:
            self.cimcall(self.conn.DeleteInstance, instance.path)
        except CIMError as ce:
            if ce.args[0] == CIM_ERR_NOT_FOUND:
            # TODO this should be an error
                pass

        # Simple create and delete

        try:
            result = self.cimcall(self.conn.CreateInstance, instance)
        except CIMError as ce:
            if ce.args[0] == CIM_ERR_INVALID_CLASS:
                # does not support creation
                pass
        else:
            self.assertTrue(isinstance(result, CIMInstanceName))
            self.assertTrue(len(result.namespace) > 0)

            result = self.cimcall(self.conn.DeleteInstance, instance.path)

            self.assertTrue(result is None)

        try:
            self.cimcall(self.conn.GetInstance(instance.path))
        except CIMError as arg:
            if arg == CIM_ERR_NOT_FOUND:
                pass

class ModifyInstance(ClientTest):

    def test_all(self):

        # Test instance

        instance = CIMInstance(
            'PyWBEM_Person',
            {'CreationClassName': 'PyWBEM_Person',
             'Name': 'Test'},
            path=CIMInstanceName('PyWBEM_Person',
                                 {'CreationClassName': 'PyWBEM_Person',
                                  'Name': 'Test'}))

        # Delete if already exists
        ## TODO validate this one

        try:
            self.cimcall(self.conn.DeleteInstance, instance.path)
        except CIMError as ce:
            if ce.args[0] == CIM_ERR_NOT_FOUND:
                pass

        # Create instance

        try:
            self.cimcall(self.conn.CreateInstance, instance)
        except CIMError as ce:
            if ce.args[0] == CIM_ERR_INVALID_CLASS:
                # does not support creation
                pass
        else:

            # Modify instance

            instance['Title'] = 'Sir'

            instance.path.namespace = 'root/cimv2'
            result = self.cimcall(self.conn.ModifyInstance, instance)

            self.assertTrue(result is None)

            # Clean up

            self.cimcall(self.conn.DeleteInstance, instance.path)


#################################################################
# Method provider interface tests
#################################################################

class InvokeMethod(ClientTest):

    def test_all(self):

        # Invoke on classname

        try:
            self.cimcall(
                self.conn.InvokeMethod,
                'FooMethod',
                TEST_CLASS)

        except CIMError as ce:
            if ce.args[0] != CIM_ERR_METHOD_NOT_AVAILABLE:
                raise

        # Invoke on an InstanceName

        inst_names = self.cimcall(self.conn.EnumerateInstanceNames, TEST_CLASS)
        self.assertTrue(len(inst_names) >= 1)
        name = inst_names[0] # Pick the first returned instance

        try:

            self.cimcall(self.conn.InvokeMethod,
                         'FooMethod',
                         name)

        except CIMError as ce:
            if ce.args[0] not in (CIM_ERR_METHOD_NOT_AVAILABLE,
                                  CIM_ERR_METHOD_NOT_FOUND):
                raise

        # Test remote instance name

        name2 = name.copy()
        name2.host = 'woot.com'
        name2.namespace = 'root/cimv2'

        try:
            self.cimcall(self.conn.InvokeMethod,
                         'FooMethod',
                         name)

        except CIMError as ce:
            if ce.args[0] not in (CIM_ERR_METHOD_NOT_AVAILABLE,
                                  CIM_ERR_METHOD_NOT_FOUND):
                raise

        # Call with all possible parameter types

        try:
            self.cimcall(self.conn.InvokeMethod,
                         'FooMethod',
                         TEST_CLASS,
                         String='Spotty',
                         Uint8=Uint8(1),
                         Sint8=Sint8(2),
                         Uint16=Uint16(3),
                         Sint16=Sint16(3),
                         Uint32=Uint32(4),
                         Sint32=Sint32(5),
                         Uint64=Uint64(6),
                         Sint64=Sint64(7),
                         Real32=Real32(8),
                         Real64=Real64(9),
                         Bool=True,
                         Date1=CIMDateTime.now(),
                         Date2=timedelta(60),
                         Ref=name)
        except CIMError as ce:
            if ce.args[0] != CIM_ERR_METHOD_NOT_AVAILABLE:
                raise

        # Call with non-empty arrays

        try:

            self.cimcall(self.conn.InvokeMethod,
                         'FooMethod',
                         TEST_CLASS,
                         StringArray='Spotty',
                         Uint8Array=[Uint8(1)],
                         Sint8Array=[Sint8(2)],
                         Uint16Array=[Uint16(3)],
                         Sint16Array=[Sint16(3)],
                         Uint32Array=[Uint32(4)],
                         Sint32Array=[Sint32(5)],
                         Uint64Array=[Uint64(6)],
                         Sint64Array=[Sint64(7)],
                         Real32Array=[Real32(8)],
                         Real64Array=[Real64(9)],
                         BoolArray=[False, True],
                         Date1Array=[CIMDateTime.now(), CIMDateTime.now()],
                         Date2Array=[timedelta(0), timedelta(60)],
                         RefArray=[name, name])

        except CIMError as ce:
            if ce.args[0] != CIM_ERR_METHOD_NOT_AVAILABLE:
                raise

        # Call with new Params arg

        try:
            self.cimcall(self.conn.InvokeMethod,
                         'FooMethod',
                         TEST_CLASS,
                         [('Spam', Uint16(1)), ('Ham', Uint16(2))], # Params
                         Drink=Uint16(3), # begin of **params
                         Beer=Uint16(4))
        except CIMError as ce:
            if ce.args[0] != CIM_ERR_METHOD_NOT_AVAILABLE:
                raise

        # TODO: Call with empty arrays

        # TODO: Call with weird VALUE.REFERENCE child types:
        # (CLASSPATH|LOCALCLASSPATH|CLASSNAME|INSTANCEPATH|LOCALINSTANCEPATH|
        #  INSTANCENAME)

#################################################################
# Association provider interface tests
#################################################################

class Associators(ClientTest):

    def test_all(self):

        # Call on named instance

        inst_names = self.cimcall(self.conn.EnumerateInstanceNames, TEST_CLASS)
        self.assertTrue(len(inst_names) >= 1)
        inst_name = inst_names[0] # Pick the first returned instance

        instances = self.cimcall(self.conn.Associators, inst_name)

        for i in instances:
            self.assertTrue(isinstance(i, CIMInstance))
            self.assertTrue(isinstance(i.path, CIMInstanceName))

            # TODO: For now, disabled test for class name of associated insts.
            # self.assertTrue(i.classname == 'TBD')

            self.assertTrue(i.path.namespace is not None)
            self.assertTrue(i.path.host is not None)

        # Call on class name

        classes = self.cimcall(self.conn.Associators, TEST_CLASS)

        # TODO: check return values

class AssociatorNames(ClientTest):

    def test_all(self):

        # Call on named instance

        inst_names = self.cimcall(self.conn.EnumerateInstanceNames, TEST_CLASS)
        self.assertTrue(len(inst_names) >= 1)
        inst_name = inst_names[0] # Pick the first returned instance

        names = self.cimcall(self.conn.AssociatorNames, inst_name)

        for n in names:
            self.assertTrue(isinstance(n, CIMInstanceName))

            # TODO: For now, disabled test for class name of associated insts.
            # self.assertTrue(n.classname == 'TBD')

            self.assertTrue(n.namespace is not None)
            self.assertTrue(n.host is not None)

        # Call on class name

        classes = self.cimcall(self.conn.AssociatorNames, TEST_CLASS)

        # TODO: check return values

class References(ClientTest):

    def test_all(self):

        # Call on named instance

        inst_names = self.cimcall(self.conn.EnumerateInstanceNames, TEST_CLASS)
        self.assertTrue(len(inst_names) >= 1)
        inst_name = inst_names[0] # Pick the first returned instance

        instances = self.cimcall(self.conn.References, inst_name)

        for i in instances:
            self.assertTrue(isinstance(i, CIMInstance))
            self.assertTrue(isinstance(i.path, CIMInstanceName))

            # TODO: For now, disabled test for class name of referencing insts.
            # self.assertTrue(i.classname == 'TBD')

            self.assertTrue(i.path.namespace is not None)
            self.assertTrue(i.path.host is not None)

        # Call on class name

        classes = self.cimcall(self.conn.References, TEST_CLASS)

        # TODO: check return values

class ReferenceNames(ClientTest):

    def test_all(self):

        # Call on instance name

        inst_names = self.cimcall(self.conn.EnumerateInstanceNames, TEST_CLASS)
        self.assertTrue(len(inst_names) >= 1)
        inst_name = inst_names[0] # Pick the first returned instance

        names = self.cimcall(self.conn.ReferenceNames, inst_name)

        for n in names:
            self.assertTrue(isinstance(n, CIMInstanceName))

            # TODO: For now, disabled test for class name of referencing insts.
            # self.assertTrue(n.classname == 'TBD')

            self.assertTrue(n.namespace is not None)
            self.assertTrue(n.host is not None)

        # Call on class name

        classes = self.cimcall(self.conn.ReferenceNames, TEST_CLASS)

        # TODO: check return values

#################################################################
# Schema manipulation interface tests
#################################################################

class ClassVerifier(object):
    """Mixin class for testing CIMClass instances."""

    def verify_property(self, prop):
        """Verify that this a cim property and verify attributes"""
        self.assertTrue(isinstance(prop, CIMProperty))

    def verify_qualifier(self, qualifier):
        """Verify qualifier attributes"""
        self.assertTrue(isinstance(qualifier, CIMQualifier))
        self.assertTrue(qualifier.name)
        self.assertTrue(qualifier.value)

    def verify_method(self, method):
        """Verify method attributes"""
        self.assertTrue(isinstance(method, CIMMethod))
        # TODO add these tests
        ##pass

    def verify_class(self, cl):
        """Verify simple class attributes"""
        self.assertTrue(isinstance(cl, CIMClass))

        self.assertTrue(cl.classname)

        if cl.superclass is not None:
            self.assertTrue(cl.superclass)

        # Verify properties, qualifiers and methods

        for p in cl.properties.values():
            self.verify_property(p)
        # TODO validate qualifiers in properties. here or elsewhere
        for q in cl.qualifiers.values():
            self.verify_qualifier(q)
        for m in cl.methods.values():
            self.verify_method(m)
        # TODO validate parameters in methods

class EnumerateClassNames(ClientTest):

    def test_all(self):

        # Enumerate all classes

        names = self.cimcall(self.conn.EnumerateClassNames)

        for n in names:
            self.assertTrue(isinstance(n, six.string_types))

        # Enumerate with classname arg

        names = self.cimcall(self.conn.EnumerateClassNames,
                             ClassName='CIM_ManagedElement')

        for n in names:
            self.assertTrue(isinstance(n, six.string_types))

class EnumerateClasses(ClientTest, ClassVerifier):

    def test_all(self):

        # Enumerate all classes

        classes = self.cimcall(self.conn.EnumerateClasses)

        for c in classes:
            self.assertTrue(isinstance(c, CIMClass))
            self.verify_class(c)

        # Enumerate with classname arg

        classes = self.cimcall(self.conn.EnumerateClasses,
                               ClassName='CIM_ManagedElement')

        for cl in classes:
            self.assertTrue(isinstance(cl, CIMClass))
            self.verify_class(cl)

class GetClass(ClientTest, ClassVerifier):

    def test_all(self):
        """Get a classname and then get class"""

        name = self.cimcall(self.conn.EnumerateClassNames)[0]
        cl = self.cimcall(self.conn.GetClass, name)
        self.verify_class(cl)

class CreateClass(ClientTest):

    @UNIMPLEMENTED
    def test_all(self):
        raise AssertionError("test not implemented")

class DeleteClass(ClientTest):

    @UNIMPLEMENTED
    def test_all(self):
        raise AssertionError("test not implemented")

class ModifyClass(ClientTest):

    @UNIMPLEMENTED
    def test_all(self):
        raise AssertionError("test not implemented")

#################################################################
# Property provider interface tests
#################################################################

class GetProperty(ClientTest):

    @UNIMPLEMENTED
    def test_all(self):
        raise AssertionError("test not implemented")

class SetProperty(ClientTest):

    @UNIMPLEMENTED
    def test_all(self):
        raise AssertionError("test not implemented")

#################################################################
# Qualifier provider interface tests
#################################################################

class EnumerateQualifiers(ClientTest):

    @UNIMPLEMENTED
    def test_all(self):
        raise AssertionError("test not implemented")

class GetQualifier(ClientTest):

    @UNIMPLEMENTED
    def test_all(self):
        raise AssertionError("test not implemented")

class SetQualifier(ClientTest):

    @UNIMPLEMENTED
    def test_all(self):
        raise AssertionError("test not implemented")

class DeleteQualifier(ClientTest):

    @UNIMPLEMENTED
    def test_all(self):
        raise AssertionError("test not implemented")

#################################################################
# Query provider interface
#################################################################

class ExecuteQuery(ClientTest):

    @UNIMPLEMENTED
    def test_all(self):
        raise AssertionError("test not implemented")

#################################################################
# Internal functions
#################################################################

class Test_check_utf8_xml_chars(unittest.TestCase):

    verbose = True  # Set to True during development of tests for manually
                     # verifying the expected results.

    def _run_single(self, utf8_xml, expected_ok):

        try:
            check_utf8_xml_chars(utf8_xml, "Test XML")
        except ParseError as exc:
            if self.verbose:
                print("Verify manually: Input XML: %r, ParseError: %s" %\
                      (utf8_xml, exc))
            self.assertTrue(not expected_ok,
                            "ParseError unexpectedly raised: %s" % exc)
        else:
            self.assertTrue(expected_ok,
                            "ParseError unexpectedly not raised.")

    def test_all(self):

        # good cases
        self._run_single('<V>a</V>', True)
        self._run_single('<V>a\tb\nc\rd</V>', True)
        self._run_single('<V>a\x09b\x0Ac\x0Dd</V>', True)
        self._run_single('<V>a\xCD\x90b</V>', True)             # U+350
        self._run_single('<V>a\xE2\x80\x93b</V>', True)         # U+2013
        self._run_single('<V>a\xF0\x90\x84\xA2b</V>', True)     # U+10122

        # invalid XML characters
        if self.verbose:
            print("From here on, the only expected exception is ParseError "\
                  "for invalid XML characters...")
        self._run_single('<V>a\bb</V>', False)
        self._run_single('<V>a\x08b</V>', False)
        self._run_single('<V>a\x00b</V>', False)
        self._run_single('<V>a\x01b</V>', False)
        self._run_single('<V>a\x1Ab</V>', False)
        self._run_single('<V>a\x1Ab\x1Fc</V>', False)

        # correctly encoded but ill-formed UTF-8
        if self.verbose:
            print("From here on, the only expected exception is ParseError "\
                  "for ill-formed UTF-8 Byte sequences...")
        # combo of U+D800,U+DD22:
        self._run_single('<V>a\xED\xA0\x80\xED\xB4\xA2b</V>', False)
        # combo of U+D800,U+DD22 and combo of U+D800,U+DD23:
        self._run_single('<V>a\xED\xA0\x80\xED\xB4\xA2b\xED\xA0\x80\xED\xB4\xA3</V>',
                         False)

        # incorrectly encoded UTF-8
        if self.verbose:
            print("From here on, the only expected exception is ParseError "\
                  "for invalid UTF-8 Byte sequences...")
        # incorrect 1-byte sequence:
        self._run_single('<V>a\x80b</V>', False)
        # 2-byte sequence with missing second byte:
        self._run_single('<V>a\xC0', False)
        # 2-byte sequence with incorrect 2nd byte
        self._run_single('<V>a\xC0b</V>', False)
        # 4-byte sequence with incorrect 3rd byte:
        self._run_single('<V>a\xF1\x80abc</V>', False)
        # 4-byte sequence with incorrect 3rd byte that is an incorr. new start:
        self._run_single('<V>a\xF1\x80\xFFbc</V>', False)
        # 4-byte sequence with incorrect 3rd byte that is an correct new start:
        self._run_single('<V>a\xF1\x80\xC2\x81c</V>', False)


#################################################################
# Main function
#################################################################

tests = [

    # Instance provider interface tests

    EnumerateInstanceNames,
    EnumerateInstances,
    GetInstance,
    CreateInstance,
    ModifyInstance,

    # Method provider interface tests

    InvokeMethod,

    # Association provider interface tests

    Associators,
    AssociatorNames,
    References,
    ReferenceNames,

    # Schema manipulation interface tests

    EnumerateClassNames,
    EnumerateClasses,
    GetClass,
    CreateClass,
    DeleteClass,
    ModifyClass,

    # Property provider interface tests

    GetProperty,
    SetProperty,

    # Qualifier provider interface tests

    EnumerateQualifiers,
    GetQualifier,
    SetQualifier,
    DeleteQualifier,

    # Query provider interface tests

    ExecQuery,
    ExecuteQuery,

    ]

tests_internal = [
    Test_check_utf8_xml_chars,
]

def parse_args(argv_):
    argv = list(argv_)

    if len(argv) <= 1:
        print('Error: No arguments specified; Call with --help or -h for '\
              'usage.')
        sys.exit(2)
    elif argv[1] == '--help' or argv[1] == '-h':
        print('')
        print('Test program for CIM operations.')
        print('')
        print('Usage:')
        print('    %s [GEN_OPTS] URL [USERNAME%%PASSWORD [UT_OPTS '\
              '[UT_CLASS ...]]] ' % argv[0])
        print('')
        print('Where:')
        print('    GEN_OPTS            General options (see below).')
        print('    URL                 The URL of the WBEM server to run '\
              'against. http:// or https:// prefix determines ssl usage')
        print('    USERNAME            Userid to be used for logging on to '\
              'WBEM server.')
        print('    PASSWORD            Password to be used for logging on to '\
              'WBEM server.')
        print('    UT_OPTS             Unittest options (see below).')
        print('    UT_CLASS            Name of testcase class (e.g. '\
              'EnumerateInstances).')
        print('')
        print('General options:')
        print('    --help, -h          Display this help text.')
        print('    -n NAMESPACE        Use this CIM namespace instead of '\
              'default: %s' % DEFAULT_NAMESPACE)
        print('    -t TIMEOUT          Use this timeout (in seconds) instead '\
              'of no timeout')
        print('')
        print('Unittest arguments:')
        sys.argv[1:] = ['--help']
        unittest.main()
        print('')
        print('Examples:')
        print('    %s https://9.10.11.12 username%%password' % argv[0])
        sys.exit(2)

    args_ = {}
    # set argument defaults
    args_['namespace'] = DEFAULT_NAMESPACE
    args_['timeout'] = None
    args_['debug'] = True
    args_['verbose'] = False
    args_['username'] = None
    args_['password'] = None

    # options must proceed arguments
    while True:
        if argv[1][0] != '-':
            # Stop at first non-option
            break
        if argv[1] == '-n':
            args_['namespace'] = argv[2]
            del argv[1:3]
        elif argv[1] == '-t':
            args_['timeout'] = int(argv[2])
            del argv[1:3]
        elif argv[1] == '-v':
            args_['verbose'] = True
            del argv[1:2]
        else:
            print("Error: Unknown option: %s" % argv[1])
            sys.exit(1)

    args_['url'] = argv[1]
    del argv[1:2]

    if len(argv) >= 2:
        args_['username'], args_['password'] = argv[1].split('%')
        del argv[1:2]
    else:
        ##print('Username: ,')
        ##args['username'] = sys.stdin.readline().strip()
        ##args['password'] = getpass()
        print('No username,password')

    print('args parsed {} argv {}'.format(args_, argv))
    return args_, argv

if __name__ == '__main__':
    args, sys.argv = parse_args(sys.argv)
    print("Using WBEM Server:")
    print("  server url: %s" % args['url'])
    print("  namespace: %s" % args['namespace'])
    print("  username: %s" % args['username'])
    print("  password: %s" % ("*"*len(args['password'])))
    print("  timeout: %s" % args['timeout'])
    print("  verbose: %s" % args['verbose'])
    if args['verbose']:
       verbose_ = 2
    else:
       verbose_ = 0
    unittest.main(verbosity=verbose_)

