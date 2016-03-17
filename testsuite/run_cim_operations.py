#!/usr/bin/env python

"""
Test CIM operations against a real WBEM server that is specified on the
command line.  It executes either a specific test or the full test
suite depending on user input.

The return codes here may be specific to OpenPegasus.
"""

# pylint: disable=missing-docstring,superfluous-parens,no-self-use
import sys
from datetime import timedelta
import unittest
from getpass import getpass
import six

from pywbem.cim_constants import *
from pywbem import CIMInstance, CIMInstanceName, CIMClass, CIMClassName, \
                   CIMProperty, CIMQualifier, CIMQualifierDeclaration, \
                   CIMMethod, WBEMConnection, CIMError, \
                   Uint8, Uint16, Uint32, Uint64, \
                   Sint8, Sint16, Sint32, Sint64, \
                   Real32, Real64, CIMDateTime
from pywbem.cim_operations import CIMError

# Test for decorator for unimplemented tests
# decorator is @unittest.skip(UNIMPLEMENTED)
UNIMPLEMENTED = "test not implemented"


# A class that should be implemented in a wbem server and is used
# for testing
TEST_CLASS = 'CIM_ComputerSystem'
TEST_CLASS_PROPERTY1 = 'Name'
TEST_CLASS_PROPERTY2 = 'CreationClassName'

class ClientTest(unittest.TestCase):
    """Base class that creates a pywbem.WBEMConnection for
    subclasses to use."""

    def setUp(self):
        """Create a connection."""
        #pylint: disable=global-variable-not-assigned
        global args                 # pylint: disable=invalid-name

        self.system_url = args['url']
        self.namespace = args['namespace']
        self.verbose = args['verbose']
        self.debug = args['debug']

        self.log('setup connection {} ns {}'.format(self.system_url,
                                                    self.namespace))
        self.conn = WBEMConnection(
            self.system_url,
            (args['username'], args['password']),
            self.namespace,
            timeout=args['timeout'])
        # enable saving of xml for display
        self.conn.debug = args['verbose']
        self.log('Connected {}, ns {}'.format(self.system_url,
                                              args['namespace']))

    def cimcall(self, fn, *pargs, **kwargs):
        """Make a PyWBEM call, catch any exceptions, and log the
           request and response XML.
           Logs the call parameters, request/response xml,
           and response status

           Returns result of request to caller
        """
        self.log('cimcall fn {} args *pargs {} **kwargs {}'.
                 format(fn, pargs, kwargs))
        try:
            result = fn(*pargs, **kwargs)
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
        """Display log entry if verbose"""
        if self.verbose:
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

        # Call with property list and localonly
        instances = self.cimcall(self.conn.EnumerateInstances,
                                 TEST_CLASS,
                                 PropertyList=[TEST_CLASS_PROPERTY1, \
                                               TEST_CLASS_PROPERTY2],
                                 LocalOnly=False)

        self.assertTrue(len(instances) >= 1)

        for i in instances:
            self.assertTrue(isinstance(i, CIMInstance))
            self.assertTrue(isinstance(i.path, CIMInstanceName))
            self.assertTrue(len(i.path.namespace) > 0)
            self.assertTrue(i.path.namespace == self.namespace)
            self.assertTrue(len(i.properties) == 2)

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
                                     'WQL',
                                     'Select * from %s' % TEST_CLASS)

            self.assertTrue(len(instances) >= 1)

            for i in instances:
                self.assertTrue(isinstance(i, CIMInstance))
                self.assertTrue(isinstance(i.path, CIMInstanceName))
                self.assertTrue(len(i.path.namespace) > 0)

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

        # Call with explicit CIM namespace that does not exist

        try:

            self.cimcall(self.conn.ExecQuery,
                         'WQL',
                         'Select * from %s' % TEST_CLASS,
                         namespace='root/blah')

        except CIMError as ce:
            if ce.args[0] != CIM_ERR_INVALID_NAMESPACE:
                raise
        # Call with invalid query lang

        try:

            self.cimcall(self.conn.ExecQuery,
                         'wql',
                         'Select * from %s' % TEST_CLASS,
                         namespace='root/cimv2')

        except CIMError as ce:
            if ce.args[0] != CIM_ERR_QUERY_LANGUAGE_NOT_SUPPORTED:
                raise
        # Call with invalid query

        try:

            self.cimcall(self.conn.ExecQuery,
                         'WQL',
                         'SelectSLOP * from %s' % TEST_CLASS,
                         namespace='root/cimv2')

        except CIMError as ce:
            if ce.args[0] != CIM_ERR_INVALID_QUERY:
                raise

class GetInstance(ClientTest):

    def test_all(self):

        inst_names = self.cimcall(self.conn.EnumerateInstanceNames,
                                  TEST_CLASS)
        self.assertTrue(len(inst_names) >= 1)
        name = inst_names[0] # Pick the first returned instance

        # Simplest invocation

        obj = self.cimcall(self.conn.GetInstance,
                           name)

        self.assertTrue(isinstance(obj, CIMInstance))
        self.assertTrue(isinstance(obj.path, CIMInstanceName))

        # Call with property list and localonly
        obj = self.cimcall(self.conn.GetInstance,
                           name, \
                           PropertyList=[TEST_CLASS_PROPERTY1], \
                           LocalOnly=False)

        self.assertTrue(isinstance(obj, CIMInstance))
        self.assertTrue(isinstance(obj.path, CIMInstanceName))
        self.assertTrue(obj.path.namespace == self.namespace)
        self.assertTrue(len(obj.properties) == 1)

        # Call with property list empty

        obj = self.cimcall(self.conn.GetInstance,
                           name, \
                           PropertyList=[], \
                           LocalOnly=False)

        self.assertTrue(isinstance(obj, CIMInstance))
        self.assertTrue(isinstance(obj.path, CIMInstanceName))
        self.assertTrue(obj.path.namespace == self.namespace)
        self.assertTrue(len(obj.properties) == 0)

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

        # Delete if already exists (previous test incomplete)

        try:
            self.cimcall(self.conn.DeleteInstance, instance.path)
        except CIMError as ce:
            if ce.args[0] == CIM_ERR_NOT_FOUND:
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

            # TODO add get and test for change.

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

        inst_names = self.cimcall(self.conn.EnumerateInstanceNames,
                                  TEST_CLASS)
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
        self.assertTrue(len(classes) > 0)
        for cl in classes:
            self.assertTrue(isinstance(cl, tuple))
            self.assertTrue(isinstance(cl[0], CIMClassName))
            self.assertTrue(isinstance(cl[1], CIMClass))

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

        # Call on class name. Returns CIMClassName

        names = self.cimcall(self.conn.AssociatorNames, TEST_CLASS)

        for n in names:
            self.assertTrue(isinstance(n, CIMClassName))

        # TODO: check return values, NS, etc.

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
        self.assertTrue(len(classes) > 0)
        for cl in classes:
            self.assertTrue(isinstance(cl, tuple))
            self.assertTrue(isinstance(cl[0], CIMClassName))
            self.assertTrue(isinstance(cl[1], CIMClass))
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

        names = self.cimcall(self.conn.ReferenceNames, TEST_CLASS)

        for n in names:
            self.assertTrue(isinstance(n, CIMClassName))
        # TODO: further check return values

#################################################################
# Schema manipulation interface tests
#################################################################

class ClientClassTest(ClientTest):
    """Intermediate class for testing CIMClass instances.
       Class operations subclass from this class"""

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

class EnumerateClasses(ClientClassTest):

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

class GetClass(ClientClassTest):

    def test_all(self):
        """Get a classname from server and then get class"""

        name = self.cimcall(self.conn.EnumerateClassNames)[0]
        cl = self.cimcall(self.conn.GetClass, name)
        if self.debug:
            print('GetClass gets name %s' % name)
        self.verify_class(cl)

class CreateClass(ClientClassTest):

    @unittest.skip(UNIMPLEMENTED)
    def test_all(self):
        raise AssertionError("test not implemented")

class DeleteClass(ClientClassTest):

    @unittest.skip(UNIMPLEMENTED)
    def test_all(self):
        raise AssertionError("test not implemented")

class ModifyClass(ClientClassTest):

    @unittest.skip(UNIMPLEMENTED)
    def test_all(self):
        raise AssertionError("test not implemented")

#################################################################
# Qualifier Declaration provider interface tests
#################################################################

class QualifierDeclClientTest(ClientTest):
    """Base class for QualifierDeclaration tests. Adds specific
       tests
    """
    def verify_qual_decl(self, ql, test_name=None):
        """Verify simple class attributes"""
        self.assertTrue(isinstance(ql, CIMQualifierDeclaration))

        if test_name is not None:
            self.assertTrue(ql.name == test_name)

        # TODO expand the verification of qual decls

class EnumerateQualifiers(QualifierDeclClientTest):

    def test_all(self):
        qual_decls = self.cimcall(self.conn.EnumerateQualifiers)
        self.assertTrue(len(qual_decls) > 0)

        for qual_decl in qual_decls:
            self.verify_qual_decl(qual_decl)

class GetQualifier(QualifierDeclClientTest):

    def test_all(self):
        qual_decl = self.cimcall(self.conn.GetQualifier, 'Abstract')
        self.verify_qual_decl(qual_decl, test_name='Abstract')

        # test with name that is not found
        try:
            qual_decl = self.cimcall(self.conn.GetQualifier, 'blahblah')
        except CIMError as ce:
            if ce.args[0] != CIM_ERR_NOT_FOUND:
                raise


class SetQualifier(QualifierDeclClientTest):

    @unittest.skip(UNIMPLEMENTED)
    def test_all(self):
        raise AssertionError("test not implemented")

class DeleteQualifier(QualifierDeclClientTest):

    @unittest.skip(UNIMPLEMENTED)
    def test_all(self):
        raise AssertionError("test not implemented")

#################################################################
# Query provider interface
#################################################################

class ExecuteQuery(ClientTest):

    @unittest.skip(UNIMPLEMENTED)
    def test_all(self):
        raise AssertionError("test not implemented")
        
#################################################################
# Open pegasus special tests
#################################################################

class pegasus(ClientTest):

    def test_all(self):
        cl1 = 'Test_CLITestProviderClass'
        ns = 'test/TestProvider'
        
        cl = self.cimcall(self.conn.GetClass, cl1, namespace = ns,
                          LocalOnly = False)
        print('================CLASS {}============'.format(cl1))
        print(cl.tomof())
        print(cl.tocimxml().toprettyxml(indent='  '))
        
        names = self.cimcall(self.conn.EnumerateInstanceNames,
                              cl1, namespace = ns)
        for name in names:
            print('class %s instance %s' % (cl1,name))
            print(name.tocimxml().toprettyxml(indent='  '))
            
        instances = self.cimcall(self.conn.EnumerateInstances,
                              cl1, namespace = ns)
        for instance in instances:
            print('class %s instance %s' % (instance,name))
            print(instance.tomof())
            print(instance.tocimxml().toprettyxml(indent='  '))
            
class pegasusembedded(ClientTest):

    def test_all(self):            
        # test class with embedded instance    
        cl1 = 'Test_CLITestEmbeddedClass'
        ns = 'test/TestProvider'
        #prop_name = 'Id'
        prop_name = 'embeddedInst'
        #property_list = ['embeddedInst']
        #property_list = ['comment', 'Id']
        property_list = [prop_name]
        
        #cl = self.cimcall(self.conn.GetClass, cl1, namespace = ns,
                          #LocalOnly = False)
        #print('================CLASS {}============'.format(cl1))
        #print(cl.tomof())
        #print(cl.tocimxml().toprettyxml(indent='  '))
        
        #names = self.cimcall(self.conn.EnumerateInstanceNames,
                              #cl1, namespace = ns)
        #for name in names:
            #print('Class=%s, InstanceName=%s' % (cl1,name))

        insts = self.cimcall(self.conn.EnumerateInstances,
                             cl1, namespace=ns,
                             propertylist=property_list)
        ####for key, value in self.properties.items()        
        for inst in insts:
            print('INSTANCE ========= %s ============' % inst.path)
            #print('==========MOF=======\n%s' %(inst.tomof()))
            #print('==========XML=======\n%s' %(inst.tocimxml().toprettyxml()))

            print('instance {}'.format(inst))
            print('property count {}'.format(len(inst.properties)))
            
            print('======properties=======\nproplist {}\n========='.format(inst.properties))
            print('property id {}'.format(inst.properties[prop_name]))
            
            prop = inst.properties[prop_name]
            print('property {}: view {}'.format( prop_name, prop))
            print('property {}: details name={}, type={}, value={} eo={}'.format(prop_name,prop.name, prop.type, prop.value, prop.embedded_object))
            
            ## why does this produce a unicode output for property???
            #for property in inst.properties:
                #property
                #print('property view {}'.format(property))
                #print('property name={}, type={}, value={}'.format(property.name, property.type, property.value))
                #print('tocimxml\n{}'.format(property.tocimxml.toprettyxml()))
                ###print('tomof\n{}'.format(prop.tomof()))
        
        

#################################################################
# Main function
#################################################################

TEST_LIST = [

    # Instance provider interface tests

    'EnumerateInstanceNames',
    'EnumerateInstances',
    'GetInstance',
    'CreateInstance',
    'ModifyInstance',

    # Method provider interface tests

    'InvokeMethod',

    # Association provider interface tests

    'Associators',
    'AssociatorNames',
    'References',
    'ReferenceNames',

    # Schema manipulation interface tests

    'EnumerateClassNames',
    'EnumerateClasses',
    'GetClass',
    'CreateClass',
    'DeleteClass',
    'ModifyClass',

    # Qualifier provider interface tests

    'EnumerateQualifiers',
    'GetQualifier',
    'SetQualifier',
    'DeleteQualifier',

    # Query provider interface tests

    'ExecQuery',
    'ExecuteQuery',
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
        print('    URL                 URL of the target WBEM server.\n'\
              '                        http:// or https:// prefix'\
              ' defines ssl usage')
        print('    USERNAME            Userid used to log into '\
              'WBEM server.\n' \
              '                        Requests user input if not supplied')
        print('    PASSWORD            Password used to log into '\
              'WBEM server.\n' \
              '                        Requests user input if not supplier')
        print('    UT_OPTS             Unittest options (see below).')
        print('    UT_CLASS            Name of testcase class (e.g. '\
              'EnumerateInstances).')
        print('')
        print('General options[GEN_OPTS]:')
        print('    --help, -h          Display this help text.')
        print('    -n NAMESPACE        Use this CIM namespace instead of '\
              'default: %s' % DEFAULT_NAMESPACE)
        print('    -t TIMEOUT          Use this timeout (in seconds)'\
              ' instead of no timeout')
        print('    -v                  Verbose output which includes:\n' \
              '                          - xml input and output,\n' \
              '                          - connection details,\n'
              '                          - details of tests')
        print('    -d                  Debug flag for extra displays')
        print('    -hl                 List of indifidual tests')

        print('')
        print('Examples:')
        print('    %s https://9.10.11.12 username%%password' % argv[0])
        print('    %s https://myhost -v username%%password' % argv[0])
        print('    %s http://localhost -v username%%password' \
              ' GetQualifier' % argv[0])

        print('------------------------')
        print('Unittest arguments[UT_OPTS]:')
        print('')
        sys.argv[1:] = ['--help']
        unittest.main()
        sys.exit(2)

    args_ = {}
    # set argument defaults
    args_['namespace'] = DEFAULT_NAMESPACE
    args_['timeout'] = None
    args_['debug'] = False
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
        elif argv[1] == '-d':
            args_['debug'] = True
            del argv[1:2]
        elif argv[1] == '-hl':
            args_['debug'] = True
            del argv[1:3]
            print('List of tests: %s' % ", ".join(TEST_LIST))
            sys.exit(2)
        else:
            print("Error: Unknown option: %s" % argv[1])
            sys.exit(1)

    args_['url'] = argv[1]
    del argv[1:2]

    if len(argv) >= 2:
        args_['username'], args_['password'] = argv[1].split('%')
        del argv[1:2]
    else:
        # Get user name and pw from console
        sys.stdout.write('Username: ')
        sys.stdout.flush()
        args_['username'] = sys.stdin.readline().strip()
        args_['password'] = getpass()

    return args_, argv

if __name__ == '__main__':
    args, sys.argv = parse_args(sys.argv) # pylint: disable=invalid-name
    print("Using WBEM Server:")
    print("  server url: %s" % args['url'])
    print("  namespace: %s" % args['namespace'])
    print("  username: %s" % args['username'])
    print("  password: %s" % ("*"*len(args['password'])))
    print("  timeout: %s" % args['timeout'])
    print("  verbose: %s" % args['verbose'])
    print("  debug: %s" % args['debug'])

    # Note: unittest options are defined in separate args after
    # the url argumentl.
    unittest.main()

