#!/usr/bin/python
#
# Test CIM operations function interface.  The return codes here may
# be specific to OpenPegasus.
#

from datetime import timedelta
from types import StringTypes
from comfychair import main, TestCase, NotRunError
from pywbem import *

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
            (username, password))
        self.conn.debug = True

    def cimcall(self, fn, *args, **kw):
        """Make a PyWBEM call and log the request and response XML."""
        
        try:
            result = fn(*args, **kw)
        except:
            self.log('Failed Request:\n\n%s\n' % self.conn.last_request)
            self.log('Failed Reply:\n\n%s\n' % self.conn.last_reply)
            raise

        self.log('Request:\n\n%s\n' % self.conn.last_request)
        self.log('Reply:\n\n%s\n' % self.conn.last_reply)

        return result

#################################################################
# Instance provider interface tests
#################################################################

class EnumerateInstanceNames(ClientTest):

    def runtest(self):

        # Single arg call

        names = self.cimcall(
            self.conn.EnumerateInstanceNames,
            'PyWBEM_Person')

        self.assert_(len(names) == 3)

        [self.assert_(isinstance(n, CIMInstanceName)) for n in names]
        [self.assert_(len(n.namespace) > 0) for n in names]
        
        # Call with optional namespace path

        try:

            self.cimcall(
                self.conn.EnumerateInstanceNames,
                'PyWBEM_Person',
                namespace = 'root/pywbem')

        except CIMError, arg:
            if arg[0] != CIM_ERR_INVALID_NAMESPACE:
                raise

class EnumerateInstances(ClientTest):

    def runtest(self):

        # Simplest invocation

        instances = self.cimcall(
            self.conn.EnumerateInstances,
            'PyWBEM_Person')

        self.assert_(len(instances) == 3)

        [self.assert_(isinstance(i, CIMInstance)) for i in instances]
        [self.assert_(isinstance(i.path, CIMInstanceName)) for i in instances]
        [self.assert_(len(i.path.namespace) > 0) for i in instances]

        # Call with optional namespace path

        try:

            self.cimcall(
                self.conn.EnumerateInstances,
                'PyWBEM_Person',
                namespace = 'root/pywbem')

        except CIMError, arg:
            if arg[0] != CIM_ERR_INVALID_NAMESPACE:
                raise


class ExecQuery(ClientTest):

    def runtest(self):

        try:
            instances = self.cimcall(
                self.conn.ExecQuery, 
                'wql',
                'Select * from PyWBEM_Person')

            self.assert_(len(instances) == 3)

            [self.assert_(isinstance(i, CIMInstance)) for i in instances]
            [self.assert_(isinstance(i.path, CIMInstanceName)) for i in instances]
            [self.assert_(len(i.path.namespace) > 0) for i in instances]

        # Call with optional namespace path
            try:

                self.cimcall(
                    self.conn.ExecQuery, 
                    'wql',
                    'Select * from PyWBEM_Person',
                    namespace = 'root/pywbem')

            except CIMError, arg:
                if arg[0] != CIM_ERR_INVALID_NAMESPACE:
                    raise

        except CIMError, arg:
            if arg[0] == CIM_ERR_NOT_SUPPORTED:
                raise NotRunError, "CIMOM doesn't support ExecQuery"
            else:
                raise


class GetInstance(ClientTest):

    def runtest(self):

        name = self.cimcall(
            self.conn.EnumerateInstanceNames,
            'PyWBEM_Person')[0]

        # Simplest invocation

        obj = self.cimcall(self.conn.GetInstance, name)

        self.assert_(isinstance(obj, CIMInstance))
        self.assert_(isinstance(obj.path, CIMInstanceName))

        # Call with invalid namespace path

        invalid_name = name.copy()
        invalid_name.namespace = 'blahblahblah'

        try:

            self.cimcall(
                self.conn.GetInstance,
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
            path = CIMInstanceName('PyWBEM_Person',
                                   {'CreationClassName': 'PyWBEM_Person',
                                    'Name': 'Test'}))
                                                      
        # Delete if already exists

        try:
            self.cimcall(self.conn.DeleteInstance, instance.path)
        except CIMError, arg:
            if arg == CIM_ERR_NOT_FOUND:
                pass

        # Simple create and delete

        result = self.cimcall(self.conn.CreateInstance, instance)

        self.assert_(isinstance(result, CIMInstanceName))
        self.assert_(len(result.namespace) > 0)
        
        result = self.cimcall(self.conn.DeleteInstance, instance.path)

        self.assert_(result == None)

        try:
            self.cimcall(self.conn.GetInstance(instance.path))
        except CIMError, arg:
            if arg == CIM_ERR_NOT_FOUND:
                pass

        # Arg plus namespace

        try:

            self.cimcall(
                self.conn.CreateInstance,
                instance)

        except CIMError, arg:
            if arg[0] != CIM_ERR_INVALID_NAMESPACE:
                raise

class ModifyInstance(ClientTest):

    def runtest(self):

        # Test instance

        instance = CIMInstance(
            'PyWBEM_Person',
            {'CreationClassName': 'PyWBEM_Person',
             'Name': 'Test'},
            path = CIMInstanceName('PyWBEM_Person',
                                   {'CreationClassName': 'PyWBEM_Person',
                                    'Name': 'Test'}))

        # Delete if already exists

        try:
            self.cimcall(self.conn.DeleteInstance, instance.path)
        except CIMError, arg:
            if arg == CIM_ERR_NOT_FOUND:
                pass

        # Create instance

        self.cimcall(self.conn.CreateInstance, instance)

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
                'CIM_Process')

        except CIMError, arg:
            if arg[0] != CIM_ERR_METHOD_NOT_AVAILABLE:
                raise

        # Invoke on an InstanceName

        name = self.cimcall(self.conn.EnumerateInstanceNames, 'CIM_Process')[0]

        try:

            self.cimcall(self.conn.InvokeMethod,
                         'FooMethod',
                         name)

        except CIMError, arg:
            if arg[0] != CIM_ERR_METHOD_NOT_AVAILABLE:
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
            if arg[0] != CIM_ERR_METHOD_NOT_AVAILABLE:
                raise        

        # Call with all possible parameter types

        try:
            self.cimcall(self.conn.InvokeMethod,
                         'FooMethod',
                         'CIM_Process',
                         String = 'Spotty',
                         Uint8  = Uint8(1),
                         Sint8  = Sint8(2),
                         Uint16 = Uint16(3),
                         Uint32 = Uint32(4),
                         Sint32 = Sint32(5),
                         Uint64 = Uint64(6),
                         Sint64 = Sint64(7),
                         Real32 = Real32(8),
                         Real64 = Real64(9),
                         Bool   = True,
                         Date1  = CIMDateTime.now(),
                         Date2  = timedelta(60),
                         Ref = name)
        except CIMError, arg:
            if arg[0] != CIM_ERR_METHOD_NOT_AVAILABLE:
                raise

        # Call with non-empty arrays

        try:

            self.cimcall(self.conn.InvokeMethod,
                         'FooMethod',
                         'CIM_Process',
                         StringArray = 'Spotty',
                         Uint8Array  = [Uint8(1)],
                         Sint8Array  = [Sint8(2)],
                         Uint16Array = [Uint16(3)],
                         Uint32Array = [Uint32(4)],
                         Sint32Array = [Sint32(5)],
                         Uint64Array = [Uint64(6)],
                         Sint64Array = [Sint64(7)],
                         Real32Array = [Real32(8)],
                         Real64Array = [Real64(9)],
                         BoolArray   = [False, True],
                         Date1Array  = [CIMDateTime.now(), CIMDateTime.now()],
                         Date2Array  = [timedelta(0), timedelta(60)],
                         RefArray = [name, name])

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

        collection = self.cimcall(
            self.conn.EnumerateInstanceNames, 'PyWBEM_PersonCollection')[0]

        instances = self.cimcall(self.conn.Associators, collection)

        [self.assert_(isinstance(i, CIMInstance)) for i in instances]
        [self.assert_(isinstance(i.path, CIMInstanceName)) for i in instances]

        [self.assert_(i.classname == 'PyWBEM_Person') for i in instances]

        [self.assert_(i.path.namespace is not None) for i in instances]
        [self.assert_(i.path.host is not None) for i in instances]

        # Call on class name

        classes = self.cimcall(
            self.conn.Associators, 'PyWBEM_PersonCollection')

        # TODO: check return values
    
class AssociatorNames(ClientTest):

    def runtest(self):

        # Call on instance name

        collection = self.cimcall(
            self.conn.EnumerateInstanceNames, 'PyWBEM_PersonCollection')[0]

        names = self.cimcall(self.conn.AssociatorNames, collection)

        [self.assert_(isinstance(n, CIMInstanceName)) for n in names]

        [self.assert_(n.classname == 'PyWBEM_Person') for n in names]

        [self.assert_(n.namespace is not None) for n in names]
        [self.assert_(n.host is not None) for n in names]

        # Call on class name

        classes = self.cimcall(
            self.conn.AssociatorNames, 'PyWBEM_PersonCollection')

        # TODO: check return values
        
class References(ClientTest):

    def runtest(self):

        # Call on named instance

        collection = self.cimcall(
            self.conn.EnumerateInstanceNames, 'PyWBEM_PersonCollection')[0]

        instances = self.cimcall(self.conn.References, collection)

        [self.assert_(isinstance(i, CIMInstance)) for i in instances]
        [self.assert_(isinstance(i.path, CIMInstanceName)) for i in instances]

        [self.assert_(i.classname == 'PyWBEM_MemberOfPersonCollection')
         for i in instances]

        [self.assert_(i.path.namespace is not None) for i in instances]
        [self.assert_(i.path.host is not None) for i in instances]

        # Call on class name

        classes = self.cimcall(
            self.conn.References, 'PyWBEM_PersonCollection')

        # TODO: check return values

class ReferenceNames(ClientTest):

    def runtest(self):

        # Call on instance name

        collection = self.cimcall(
            self.conn.EnumerateInstanceNames, 'PyWBEM_PersonCollection')[0]

        names = self.cimcall(self.conn.ReferenceNames, collection)

        [self.assert_(isinstance(n, CIMInstanceName)) for n in names]

        [self.assert_(n.classname == 'PyWBEM_MemberOfPersonCollection')
         for n in names]

        [self.assert_(n.namespace is not None) for n in names]
        [self.assert_(n.host is not None) for n in names]

        # Call on class name

        classes = self.cimcall(
            self.conn.ReferenceNames, 'PyWBEM_PersonCollection')

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
                             ClassName = 'CIM_ManagedElement')

        [self.assert_(isinstance(n, StringTypes)) for n in names]

class EnumerateClasses(ClientTest, ClassVerifier):

    def runtest(self):

        # Enumerate all classes

        classes = self.cimcall(self.conn.EnumerateClasses)
        [self.assert_(isinstance(c, CIMClass)) for c in classes]
        [self.verify_class(c) for c in classes]

        # Enumerate with classname arg

        classes = self.cimcall(self.conn.EnumerateClasses,
                               ClassName = 'CIM_ManagedElement')
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
        print 'Usage: test_cim_operations.py URL [USERNAME%PASSWORD]'
        sys.exit(0)

    url = sys.argv[1]
    if len(sys.argv) == 3:
        username, password = sys.argv[2].split('%')
    else:
        from getpass import getpass
        print 'Username: ',
        username = sys.stdin.readline().strip()
        password = getpass()

    sys.argv = sys.argv[2:]

    main(tests)
