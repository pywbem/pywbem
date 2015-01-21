#!/usr/bin/env python

"""
Test CIM operations against a real WBEM server that is specified on the
command line.

The return codes here may be specific to OpenPegasus.
"""

import sys
from datetime import timedelta
from types import StringTypes

from pywbem.cim_constants import *
from pywbem import CIMInstance, CIMInstanceName, CIMClass, CIMProperty, \
                   WBEMConnection, CIMError, \
                   Uint8, Uint16, Uint32, Uint64, \
                   Sint8, Sint16, Sint32, Sint64, \
                   Real32, Real64, CIMDateTime

from comfychair import main, TestCase, NotRunError
from pywbem.cim_operations import DEFAULT_NAMESPACE

# A class that should be implemented and is used for testing
TEST_CLASS = 'CIM_ComputerSystem'

# Test classes

class ClientTest(TestCase):
    """A base class that creates a pywbem.WBEMConnection for
    subclasses to use."""

    def setup(self):
        """Create a connection."""

        # Use globals url, username and password

        self.system_url = url
        self.conn = WBEMConnection(
            self.system_url,
            (username, password),
            namespace)
        self.conn.debug = True

    def cimcall(self, fn, *args, **kw):
        """Make a PyWBEM call and log the request and response XML."""

        try:
            result = fn(*args, **kw)
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

#################################################################
# Instance provider interface tests
#################################################################

class EnumerateInstanceNames(ClientTest):

    def runtest(self):

        # Single arg call

        names = self.cimcall(self.conn.EnumerateInstanceNames,
                             TEST_CLASS)

        self.assert_(len(names) >= 1)

        [self.assert_(isinstance(n, CIMInstanceName)) for n in names]
        [self.assert_(len(n.namespace) > 0) for n in names]

        # Call with explicit CIM namespace that exists

        self.cimcall(self.conn.EnumerateInstanceNames,
                     TEST_CLASS,
                     namespace=self.conn.default_namespace)

        # Call with explicit CIM namespace that does not exist

        try:

            self.cimcall(self.conn.EnumerateInstanceNames,
                         TEST_CLASS,
                         namespace='root/blah')

        except CIMError, arg:
            if arg[0] != CIM_ERR_INVALID_NAMESPACE:
                raise

class EnumerateInstances(ClientTest):

    def runtest(self):

        # Simplest invocation

        instances = self.cimcall(self.conn.EnumerateInstances,
                                 TEST_CLASS)

        self.assert_(len(instances) >= 1)

        [self.assert_(isinstance(i, CIMInstance)) for i in instances]
        [self.assert_(isinstance(i.path, CIMInstanceName)) for i in instances]
        [self.assert_(len(i.path.namespace) > 0) for i in instances]

        # Call with explicit CIM namespace that exists

        self.cimcall(self.conn.EnumerateInstances,
                     TEST_CLASS,
                     namespace=self.conn.default_namespace)

        # Call with explicit CIM namespace that does not exist

        try:

            self.cimcall(self.conn.EnumerateInstances,
                         TEST_CLASS,
                         namespace='root/blah')

        except CIMError, arg:
            if arg[0] != CIM_ERR_INVALID_NAMESPACE:
                raise


class ExecQuery(ClientTest):

    def runtest(self):

        try:

            # Simplest invocation

            instances = self.cimcall(self.conn.ExecQuery,
                                     'wql',
                                     'Select * from %s' % TEST_CLASS)

            self.assert_(len(instances) >= 1)

            [self.assert_(isinstance(i, CIMInstance)) for i in instances]
            [self.assert_(isinstance(i.path, CIMInstanceName)) \
             for i in instances]
            [self.assert_(len(i.path.namespace) > 0) for i in instances]

            # Call with explicit CIM namespace that does not exist

            try:

                self.cimcall(self.conn.ExecQuery,
                             'wql',
                             'Select * from %s' % TEST_CLASS,
                             namespace='root/blah')

            except CIMError, arg:
                if arg[0] != CIM_ERR_INVALID_NAMESPACE:
                    raise

        except CIMError, arg:
            if arg[0] == CIM_ERR_NOT_SUPPORTED:
                raise NotRunError, "The WBEM server doesn't support ExecQuery"
            if arg[0] == CIM_ERR_QUERY_LANGUAGE_NOT_SUPPORTED:
                raise NotRunError, "The WBEM server doesn't support WQL for ExecQuery"
            else:
                raise


class GetInstance(ClientTest):

    def runtest(self):

        inst_names = self.cimcall(self.conn.EnumerateInstanceNames, TEST_CLASS)
        self.assert_(len(inst_names) >= 1)
        name = inst_names[0] # Pick the first returned instance

        # Simplest invocation

        obj = self.cimcall(self.conn.GetInstance,
                           name)

        self.assert_(isinstance(obj, CIMInstance))
        self.assert_(isinstance(obj.path, CIMInstanceName))

        # Call with invalid namespace path

        invalid_name = name.copy()
        invalid_name.namespace = 'blahblahblah'

        try:

            self.cimcall(self.conn.GetInstance,
                         invalid_name)

        except CIMError, arg:
            if arg[0] != CIM_ERR_INVALID_NAMESPACE:
                raise

class CreateInstance(ClientTest):

    def runtest(self):

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
        except CIMError, arg:
            if arg == CIM_ERR_NOT_FOUND:
                pass

        # Simple create and delete

        try:
            result = self.cimcall(self.conn.CreateInstance, instance)
        except CIMError, arg:
            if arg == CIM_ERR_INVALID_CLASS:
                # does not support creation
                pass
        else:
            self.assert_(isinstance(result, CIMInstanceName))
            self.assert_(len(result.namespace) > 0)

            result = self.cimcall(self.conn.DeleteInstance, instance.path)

            self.assert_(result == None)

        try:
            self.cimcall(self.conn.GetInstance(instance.path))
        except CIMError, arg:
            if arg == CIM_ERR_NOT_FOUND:
                pass

class ModifyInstance(ClientTest):

    def runtest(self):

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
        except CIMError, arg:
            if arg == CIM_ERR_NOT_FOUND:
                pass

        # Create instance

        try:
            self.cimcall(self.conn.CreateInstance, instance)
        except CIMError, arg:
            if arg == CIM_ERR_INVALID_CLASS:
                # does not support creation
                pass
        else:

            # Modify instance
    
            instance['Title'] = 'Sir'
    
            instance.path.namespace = 'root/cimv2'
            result = self.cimcall(self.conn.ModifyInstance, instance)
    
            self.assert_(result is None)
    
            # Clean up
    
            self.cimcall(self.conn.DeleteInstance, instance.path)


#################################################################
# Method provider interface tests
#################################################################

class InvokeMethod(ClientTest):

    def runtest(self):

        # Invoke on classname

        try:

            self.cimcall(
                self.conn.InvokeMethod,
                'FooMethod',
                TEST_CLASS)

        except CIMError, arg:
            if arg[0] != CIM_ERR_METHOD_NOT_AVAILABLE:
                raise

        # Invoke on an InstanceName

        inst_names = self.cimcall(self.conn.EnumerateInstanceNames, TEST_CLASS)
        self.assert_(len(inst_names) >= 1)
        name = inst_names[0] # Pick the first returned instance

        try:

            self.cimcall(self.conn.InvokeMethod,
                         'FooMethod',
                         name)

        except CIMError, arg:
            if arg[0] not in (CIM_ERR_METHOD_NOT_AVAILABLE, CIM_ERR_METHOD_NOT_FOUND):
                raise

        # Test remote instance name

        name2 = name.copy()
        name2.host = 'woot.com'
        name2.namespace = 'root/cimv2'

        try:

            self.cimcall(self.conn.InvokeMethod,
                         'FooMethod',
                         name)

        except CIMError, arg:
            if arg[0] not in (CIM_ERR_METHOD_NOT_AVAILABLE, CIM_ERR_METHOD_NOT_FOUND):
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
        except CIMError, arg:
            if arg[0] != CIM_ERR_METHOD_NOT_AVAILABLE:
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

        except CIMError, arg:
            if arg[0] != CIM_ERR_METHOD_NOT_AVAILABLE:
                raise

        # Call with new Params arg

        try:
            self.cimcall(self.conn.InvokeMethod,
                         'FooMethod',
                         TEST_CLASS,
                         [('Spam',Uint16(1)),('Ham',Uint16(2))], # Params
                         Drink=Uint16(3), # begin of **params
                         Beer=Uint16(4))
        except CIMError, arg:
            if arg[0] != CIM_ERR_METHOD_NOT_AVAILABLE:
                raise

        # TODO: Call with empty arrays

        # TODO: Call with weird VALUE.REFERENCE child types:
        # (CLASSPATH|LOCALCLASSPATH|CLASSNAME|INSTANCEPATH|LOCALINSTANCEPATH|
        #  INSTANCENAME)

#################################################################
# Association provider interface tests
#################################################################

class Associators(ClientTest):

    def runtest(self):

        # Call on named instance

        inst_names = self.cimcall(self.conn.EnumerateInstanceNames, TEST_CLASS)
        self.assert_(len(inst_names) >= 1)
        inst_name = inst_names[0] # Pick the first returned instance

        instances = self.cimcall(self.conn.Associators, inst_name)

        [self.assert_(isinstance(i, CIMInstance)) for i in instances]
        [self.assert_(isinstance(i.path, CIMInstanceName)) for i in instances]

        # TODO: For now, disabled test for class name of associated instances.
        # [self.assert_(i.classname == 'TBD') for i in instances]

        [self.assert_(i.path.namespace is not None) for i in instances]
        [self.assert_(i.path.host is not None) for i in instances]

        # Call on class name

        classes = self.cimcall(self.conn.Associators, TEST_CLASS)

        # TODO: check return values

class AssociatorNames(ClientTest):

    def runtest(self):

        # Call on named instance

        inst_names = self.cimcall(self.conn.EnumerateInstanceNames, TEST_CLASS)
        self.assert_(len(inst_names) >= 1)
        inst_name = inst_names[0] # Pick the first returned instance

        names = self.cimcall(self.conn.AssociatorNames, inst_name)

        [self.assert_(isinstance(n, CIMInstanceName)) for n in names]

        # TODO: For now, disabled test for class name of associated instances.
        # [self.assert_(n.classname == 'TBD') for n in names]

        [self.assert_(n.namespace is not None) for n in names]
        [self.assert_(n.host is not None) for n in names]

        # Call on class name

        classes = self.cimcall(self.conn.AssociatorNames, TEST_CLASS)

        # TODO: check return values

class References(ClientTest):

    def runtest(self):

        # Call on named instance

        inst_names = self.cimcall(self.conn.EnumerateInstanceNames, TEST_CLASS)
        self.assert_(len(inst_names) >= 1)
        inst_name = inst_names[0] # Pick the first returned instance

        instances = self.cimcall(self.conn.References, inst_name)

        [self.assert_(isinstance(i, CIMInstance)) for i in instances]
        [self.assert_(isinstance(i.path, CIMInstanceName)) for i in instances]

        # TODO: For now, disabled test for class name of referencing instances.
        #[self.assert_(i.classname == 'TBD')
        # for i in instances]

        [self.assert_(i.path.namespace is not None) for i in instances]
        [self.assert_(i.path.host is not None) for i in instances]

        # Call on class name

        classes = self.cimcall(self.conn.References, TEST_CLASS)

        # TODO: check return values

class ReferenceNames(ClientTest):

    def runtest(self):

        # Call on instance name

        inst_names = self.cimcall(self.conn.EnumerateInstanceNames, TEST_CLASS)
        self.assert_(len(inst_names) >= 1)
        inst_name = inst_names[0] # Pick the first returned instance

        names = self.cimcall(self.conn.ReferenceNames, inst_name)

        [self.assert_(isinstance(n, CIMInstanceName)) for n in names]

        # TODO: For now, disabled test for class name of referencing instances.
        #[self.assert_(n.classname == 'TBD')
        # for n in names]

        [self.assert_(n.namespace is not None) for n in names]
        [self.assert_(n.host is not None) for n in names]

        # Call on class name

        classes = self.cimcall(self.conn.ReferenceNames, TEST_CLASS)

        # TODO: check return values

#################################################################
# Schema manipulation interface tests
#################################################################

class ClassVerifier(object):
    """Base class for testing CIMClass instances."""

    def verify_property(self, p):
        self.assert_(isinstance(p, CIMProperty))

    def verify_qualifier(self, q):
        self.assert_(q.name)
        self.assert_(q.value)

    def verify_method(self, m):
        # TODO: verify method
        pass

    def verify_class(self, cl):

        # Verify simple attributes

        self.assert_(cl.classname)

        if cl.superclass is not None:
            self.assert_(cl.superclass)

        # Verify properties, qualifiers and methods

        [self.verify_property(p) for p in cl.properties.values()]
        [self.verify_qualifier(q) for q in cl.qualifiers.values()]
        [self.verify_method(m) for m in cl.methods.values()]

class EnumerateClassNames(ClientTest):

    def runtest(self):

        # Enumerate all classes

        names = self.cimcall(self.conn.EnumerateClassNames)
        [self.assert_(isinstance(n, StringTypes)) for n in names]

        # Enumerate with classname arg

        names = self.cimcall(self.conn.EnumerateClassNames,
                             ClassName='CIM_ManagedElement')

        [self.assert_(isinstance(n, StringTypes)) for n in names]

class EnumerateClasses(ClientTest, ClassVerifier):

    def runtest(self):

        # Enumerate all classes

        classes = self.cimcall(self.conn.EnumerateClasses)
        [self.assert_(isinstance(c, CIMClass)) for c in classes]
        [self.verify_class(c) for c in classes]

        # Enumerate with classname arg

        classes = self.cimcall(self.conn.EnumerateClasses,
                               ClassName='CIM_ManagedElement')
        [self.assert_(isinstance(c, CIMClass)) for c in classes]
        [self.verify_class(c) for c in classes]

class GetClass(ClientTest, ClassVerifier):

    def runtest(self):

        name = self.cimcall(self.conn.EnumerateClassNames)[0]
        self.cimcall(self.conn.GetClass, name)

class CreateClass(ClientTest):

    def runtest(self):
        raise(NotRunError);

class DeleteClass(ClientTest):

    def runtest(self):
        raise(NotRunError);

class ModifyClass(ClientTest):

    def runtest(self):
        raise(NotRunError);

#################################################################
# Property provider interface tests
#################################################################

class GetProperty(ClientTest):
    def runtest(self):
        raise(NotRunError);

class SetProperty(ClientTest):
    def runtest(self):
        raise(NotRunError);

#################################################################
# Qualifier provider interface tests
#################################################################

class EnumerateQualifiers(ClientTest):
    def runtest(self):
        raise(NotRunError);

class GetQualifier(ClientTest):
    def runtest(self):
        raise(NotRunError);

class SetQualifier(ClientTest):
    def runtest(self):
        raise(NotRunError);

class DeleteQualifier(ClientTest):
    def runtest(self):
        raise(NotRunError);

#################################################################
# Query provider interface
#################################################################

class ExecuteQuery(ClientTest):
    def runtest(self):
        raise(NotRunError);

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

if __name__ == '__main__':

    if len(sys.argv) < 2:
        print 'Usage: %s [OPTS] URL [USERNAME%%PASSWORD [COMFYOPTS] '\
              '[COMFYTESTS]]' % sys.argv[0]
        sys.exit(0)
    elif sys.argv[1] == '--help' or sys.argv[1] == '-h':
        print ''
        print 'Test program for CIM operations.'
        print ''
        print 'Usage:'
        print '    %s [OPTS] URL [USERNAME%%PASSWORD [COMFYOPTS] '\
              '[COMFYTESTS]]' % sys.argv[0]
        print ''
        print 'Where:'
        print '    OPTS                See general options section, below.'
        print '    URL                 The URL of the WBEM server to run '\
              'against.'
        print '    USERNAME            Userid to be used for logging on to '\
              'WBEM server.'
        print '    PASSWORD            Password to be used for logging on to '\
              'WBEM server.'
        print '    COMFYOPTS           Comfychair options, see options '\
              'section in Comfychair help, below.'
        print '    COMFYTESTS          List of Comfychair testcase names. '\
              'Default: All testcases.'
        print ''
        print 'General options:'
        print '    --help, -h          Display this help text.'
        print '    -n NAMESPACE        Use this CIM namespace instead of '\
              'default: %s' % DEFAULT_NAMESPACE
        print ''
        print 'Comfychair help:'
        print ''
        sys.argv = sys.argv[0:1] + ['--help']
        main(tests)
        print ''
        print 'Examples:'
        print '    %s x u%%p --list' % sys.argv[0]
        print '    %s https://9.10.11.12 username%%password -q '\
              'EnumerateInstances GetInstance ' % sys.argv[0]
        sys.exit(0)

    namespace = DEFAULT_NAMESPACE
    while (True):
        if sys.argv[1][0] != '-':
            # Stop at first non-option
            break
        if sys.argv[1] == '-n':
            namespace = sys.argv[2]
            del sys.argv[1:3]
        else:
            print "Error: Unknown option: %s" % sys.argv[1]
            sys.exit(1)

    url = sys.argv[1]

    if len(sys.argv) >= 3:
        username, password = sys.argv[2].split('%')
    else:
        from getpass import getpass
        print 'Username: ',
        username = sys.stdin.readline().strip()
        password = getpass()

    if len(sys.argv) >= 4:
        comfychair_args = sys.argv[3:]
    else:
        comfychair_args = []

    sys.argv = sys.argv[0:1] + comfychair_args

    main(tests)
