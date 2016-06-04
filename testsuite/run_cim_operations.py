#!/usr/bin/env python

"""
Test CIM operations against a real WBEM server that is specified on the
command line.  It executes either a specific test or the full test
suite depending on user input.

The return codes here may be specific to OpenPegasus.
"""

from __future__ import absolute_import

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

# Test for decorator for unimplemented tests
# decorator is @unittest.skip(UNIMPLEMENTED)
UNIMPLEMENTED = "test not implemented"


# A class that should be implemented in a wbem server and is used
# for testing
TEST_CLASS = 'CIM_ComputerSystem'
TEST_CLASS_NAMESPACE = 'root/cimv2'
TEST_CLASS_PROPERTY1 = 'Name'
TEST_CLASS_PROPERTY2 = 'CreationClassName'

INTEROP_NAMESPACE_LIST = ['interop', 'root/interop', 'root/PG_InterOp']


class ClientTest(unittest.TestCase):
    """ Base class that creates a pywbem.WBEMConnection for
        subclasses to use based on cmd line arguments. It provides
        a common cimcall method that executes test calls and logs
        results
    """

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
            timeout=args['timeout'],
            no_verification=args['nvc'],
            ca_certs=args['cacerts'])

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
        if self.verbose:
            self.log('FUTURE: disconnect this connection')

    def assertInstanceValid(self, instance, includes_path=True,
                            prop_count=None, property_list=None):
        """ Test for valid basic characteristics of an instance
            Optional parameters allow optional tests including:

              - includes_path - Test for path component if true
              - prop_count - test for number of properties in instance
              - property_list - Test for existence of properties in list
        """
        self.assertTrue(isinstance(instance, CIMInstance))
        if includes_path:
            self.assertTrue(isinstance(instance.path, CIMInstanceName))
            self.assertTrue(len(instance.path.namespace) > 0)
            self.assertTrue(instance.path.namespace == self.namespace)
        if prop_count is not None:
            self.assertTrue(len(instance.properties) == prop_count)
        if property_list is not None:
            for p in property_list:
                prop = instance.properties[p]
                self.assertIsInstance(prop, CIMProperty)

    def assertInstanceNameValid(self, path, includes_namespace=True, \
                                includes_keybindings=True,
                                namespace=None):
        """
        Validate that the path argument is a valid CIMInstanceName.
        Default is to test for namespace existing and keybindings.
        Optional is to compare namespace.
        """
        self.assertTrue(isinstance(path, CIMInstanceName))
        if includes_namespace:
            self.assertTrue(len(path.namespace) > 0)
        if includes_keybindings:
            self.assertTrue(path.keybindings is not None)
        if namespace is not None:
            self.assertTrue(path.namespace == namespace)

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
            self.assertInstanceNameValid(name, namespace=self.namespace)

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

        # Call with explicit class name that does not exist

        try:

            self.cimcall(self.conn.EnumerateInstanceNames,
                         'Blah_Blah')

        except CIMError as ce:
            if ce.args[0] != CIM_ERR_INVALID_CLASS:
                raise

class EnumerateInstances(ClientTest):
    """Test enumerateInstance variations against the server"""
    def display_response(self, instances):
        """Display the response instances as mof output"""
        if self.verbose:
            print('instance count = %s' % (len(instances)))
            for inst in instances:
                print('%s' % inst.tomof())

    def instance_classorigin(self, instance, exists):
        """Determine if classorigin in each property matches
           exists parameter (True or false)
           Returns True if classorigin attribute in returns matches
           exists parameter
           if exists True: class_origin
        """
        for value in instance.properties.values():
            if exists:
                try:
                    self.assertTrue(value.class_origin is not None)
                    return True
                except KeyError:
                    return False
            else:
                try:
                    return value.class_origin is None
                except KeyError:
                    return True

    def test_simple(self):
        """Simplest invocation of EnumerateInstances"""

        instances = self.cimcall(self.conn.EnumerateInstances,
                                 TEST_CLASS)

        self.assertTrue(len(instances) >= 1)

        for i in instances:
            self.assertInstanceValid(i)

    def test_with_propertylist(self):
        """Add property list to simple invocation"""

        self.cimcall(self.conn.EnumerateInstances,
                     TEST_CLASS,
                     namespace=self.conn.default_namespace)

        # Call with property list
        prop_list = [TEST_CLASS_PROPERTY1, TEST_CLASS_PROPERTY2]
        instances = self.cimcall(self.conn.EnumerateInstances,
                                 TEST_CLASS,
                                 PropertyList=prop_list,
                                 LocalOnly=False)

        self.assertTrue(len(instances) >= 1)

        for i in instances:
            self.assertInstanceValid(i, prop_count=2,
                                     property_list=prop_list)

        self.display_response(instances)

    def test_with_explicit_namespace(self):
        """Call with explicit CIM namespace that exists"""

        instances = self.cimcall(self.conn.EnumerateInstances,
                                 TEST_CLASS,
                                 namespace=self.conn.default_namespace)
        self.assertTrue(len(instances) >= 1)

        for i in instances:
            self.assertInstanceValid(i)


    def test_with_localonly(self):
        """Test LocalOnly specifically. Note that open pegasus ignores
        this one so cannot really test"""

        instances = self.cimcall(self.conn.EnumerateInstances,
                                 TEST_CLASS,
                                 LocalOnly=True)

        for i in instances:
            self.assertInstanceValid(i)

        self.display_response(instances)

        #Add specific response tests to the following
        instances = self.cimcall(self.conn.EnumerateInstances,
                                 TEST_CLASS,
                                 LocalOnly=False)
        for i in instances:
            self.assertInstanceValid(i)


    def test_propertylist(self):
        """ Test with propertyList for class and instance op. Should
            generate same number of properties
        """
        property_list = ('PowerManagementCapibilities')

        cls = self.cimcall(self.conn.GetClass, TEST_CLASS,
                           PropertyList=property_list)
        property_count = len(cls.properties)


        if self.verbose:
            for p in cls.properties.values():
                print('ClassPropertyName=%s' % p.name)

        instances = self.cimcall(self.conn.EnumerateInstances,
                                 TEST_CLASS,
                                 DeepInheritance=True,
                                 LocalOnly=False,
                                 PropertyList=property_list)
        for i in instances:
            self.assertInstanceValid(i)
            self.assertTrue(len(i.properties) >= property_count)

        inst_property_count = None
        for inst in instances:
            self.assertInstanceValid(inst)
            # confirm same number of properties
            if inst_property_count is None:
                inst_property_count = len(inst.properties)
                if self.verbose:
                    for p in inst.properties.values():
                        print('ClassPropertyName=%s' % p.name)
            else:
                self.assertTrue(inst_property_count == len(inst.properties))

        if property_count != inst_property_count:
            print('ERROR: property_count %s != inst_property_count %s' % \
                  (property_count, inst_property_count))
            for p in cls.properties.values():
                print('ClassPropertyName=%s' % p.name)
            for p in instances[0].properties.values():
                print('InstancePropertyName=%s' % p.name)

        # TODO Apparently ks 5/16 Pegasus did not implement all properties
        # now in the class
        #self.assertTrue(property_count == inst_property_count)

    def test_deepinheritance(self):
        """Test with deep inheritance set true and then false"""

        cls = self.cimcall(self.conn.GetClass, TEST_CLASS)
        property_count = len(cls.properties)

        if self.verbose:
            for p in cls.properties.values():
                print('ClassPropertyName=%s' % p.name)

        instances = self.cimcall(self.conn.EnumerateInstances,
                                 TEST_CLASS,
                                 DeepInheritance=True,
                                 LocalOnly=False)
        for i in instances:
            self.assertInstanceValid(i)
            self.assertTrue(len(i.properties) >= property_count)

        instances = self.cimcall(self.conn.EnumerateInstances,
                                 TEST_CLASS,
                                 DeepInheritance=False,
                                 LocalOnly=False)
        inst_property_count = None
        for inst in instances:
            self.assertInstanceValid(inst)
            # confirm same number of
            if inst_property_count is None:
                inst_property_count = len(inst.properties)
                if self.verbose:
                    for p in inst.properties.values():
                        print('ClassPropertyName=%s' % p.name)
            else:
                self.assertTrue(inst_property_count == len(inst.properties))

        if property_count != inst_property_count:
            print('ERROR: property_count %s != inst_property_count %s' % \
                  (property_count, inst_property_count))
            for p in cls.properties.values():
                print('ClassPropertyName=%s' % p.name)
            for p in instances[0].properties.values():
                print('InstancePropertyName=%s' % p.name)

    def test_includequalifiers_true(self):
        """Test Include qualifiers. No detailed added test because
           most servers ignore this"""

        prop_list = [TEST_CLASS_PROPERTY1, TEST_CLASS_PROPERTY2]
        instances = self.cimcall(self.conn.EnumerateInstances,
                                 TEST_CLASS,
                                 PropertyList=prop_list,
                                 IncludeQualifiers=False)
        for i in instances:
            self.assertInstanceValid(i, prop_count=2,
                                     property_list=prop_list)

    def test_includequalifiers_false(self):
        """ Can only test if works wnen set"""
        prop_list = [TEST_CLASS_PROPERTY1, TEST_CLASS_PROPERTY2]
        instances = self.cimcall(self.conn.EnumerateInstances,
                                 TEST_CLASS,
                                 PropertyList=prop_list,
                                 IncludeQualifiers=True)
        for i in instances:
            self.assertInstanceValid(i, prop_count=2,
                                     property_list=prop_list)

        self.display_response(instances)

    def test_includeclassorigin(self):
        """test with includeclassorigin"""
        prop_list = [TEST_CLASS_PROPERTY1, TEST_CLASS_PROPERTY2]
        instances = self.cimcall(self.conn.EnumerateInstances,
                                 TEST_CLASS,
                                 PropertyList=prop_list,
                                 IncludeClassOrigin=True)
        for i in instances:
            self.assertInstanceValid(i, prop_count=2,
                                     property_list=prop_list)
            #self.assertTrue(self.instance_classorigin(i, True))

        instances = self.cimcall(self.conn.EnumerateInstances,
                                 TEST_CLASS,
                                 PropertyList=prop_list,
                                 IncludeClassOrigin=False)
        for i in instances:
            self.assertInstanceValid(i, prop_count=2,
                                     property_list=prop_list)
            self.assertTrue(self.instance_classorigin(i, False))

    def test_nonexistent_namespace(self):
        """ Confirm correct error with nonexistent namespace"""

        try:
            self.cimcall(self.conn.EnumerateInstances,
                         TEST_CLASS,
                         namespace='root/blah')
            self.failIf(True)      # should never get here

        except CIMError as ce:
            if ce.args[0] != CIM_ERR_INVALID_NAMESPACE:
                raise

    def test_nonexistent_classname(self):
        """ Confirm correct error with nonexistent classname"""
        try:
            self.cimcall(self.conn.EnumerateInstances, 'CIM_BlahBlah')
            self.failIf(True)

        except CIMError as ce:
            if ce.args[0] != CIM_ERR_INVALID_CLASS:
                raise

    def test_invalid_request_parameter(self):
        """Should return error if invalid parameter"""
        try:
            self.cimcall(self.conn.EnumerateInstances, TEST_CLASS,
                         blablah=3)
            self.failIf(True)

        except CIMError as ce:
            if ce.args[0] != CIM_ERR_NOT_SUPPORTED:
                raise

#
#   Test the Pull Operations
#
class PullEnumerateInstances(ClientTest):

    def test_open_complete(self):
        """Simplest invocation. Everything comes back in
           initial response with end-of-sequence == True
           Note that these tests include the while pull loop beause
           in some cases OpenPegasus returns zero instances for the
           open even if a MaxObjectCount > 0 is included.
        """

        result = self.cimcall(self.conn.OpenEnumerateInstances,
                              TEST_CLASS,
                              MaxObjectCount=100)
        insts = result.instances

        while not result.eos:
            result = self.cimcall(
                self.conn.PullInstancesWithPath, result.context,
                MaxObjectCount=1)

            self.assertTrue(len(result.instances) == 1)
            insts.append(result.instances)

        for inst in insts:
            self.assertTrue(isinstance(inst, CIMInstance))
            self.assertTrue(isinstance(inst.path, CIMInstanceName))
            self.assertTrue(len(inst.path.namespace) > 0)

        insts2 = self.cimcall(self.conn.EnumerateInstances, TEST_CLASS)

        self.assertTrue(len(result.instances) == len(insts2))

    def test_open_deepinheritance(self):
        """Simple OpenEnumerateInstances but with DeepInheritance set
        """

        result = self.cimcall(self.conn.OpenEnumerateInstances,
                              TEST_CLASS,
                              MaxObjectCount=100,
                              DeepInheritance=True)
        insts = result.instances

        while not result.eos:
            result = self.cimcall(
                self.conn.PullInstancesWithPath, result.context,
                MaxObjectCount=100)

            insts.append(result.instances)

        for inst in insts:
            self.assertTrue(isinstance(inst, CIMInstance))
            self.assertTrue(isinstance(inst.path, CIMInstanceName))
            self.assertTrue(len(inst.path.namespace) > 0)

        insts2 = self.cimcall(self.conn.EnumerateInstances, TEST_CLASS)

        self.assertTrue(len(result.instances) == len(insts2))

    def test_open_includequalifiers(self):
        """Simple OpenEnumerateInstances but with IncludeQualifiers set
        """

        result = self.cimcall(self.conn.OpenEnumerateInstances,
                              TEST_CLASS,
                              MaxObjectCount=100,
                              IncludeQualifiers=True)

        insts = result.instances

        while not result.eos:
            result = self.cimcall(
                self.conn.PullInstancesWithPath, result.context,
                MaxObjectCount=1)

            self.assertTrue(len(result.instances) <= 1)
            insts.append(result.instances)

        for inst in insts:
            self.assertTrue(isinstance(inst, CIMInstance))
            self.assertTrue(isinstance(inst.path, CIMInstanceName))
            self.assertTrue(len(inst.path.namespace) > 0)

        insts2 = self.cimcall(self.conn.EnumerateInstances, TEST_CLASS)

        self.assertTrue(len(result.instances) == len(insts2))

    def test_open_includeclassorigin(self):
        """Simple OpenEnumerateInstances but with DeepInheritance set
        """

        result = self.cimcall(self.conn.OpenEnumerateInstances,
                              TEST_CLASS,
                              MaxObjectCount=100,
                              IncludeClassOrigin=True)

        insts = result.instances

        while not result.eos:
            result = self.cimcall(
                self.conn.PullInstancesWithPath, result.context,
                MaxObjectCount=1)

            self.assertTrue(len(result.instances) <= 1)
            insts.append(result.instances)

        for inst in result.instances:
            self.assertTrue(isinstance(inst, CIMInstance))
            self.assertTrue(isinstance(inst.path, CIMInstanceName))
            self.assertTrue(len(inst.path.namespace) > 0)

        insts2 = self.cimcall(self.conn.EnumerateInstances, TEST_CLASS)

        self.assertTrue(len(result.instances) == len(insts2))

    def test_open_complete_with_ns(self):
        """Simple call that is complete with just the open and
           with explicit namespace
        """

        result = self.cimcall(self.conn.OpenEnumerateInstances, TEST_CLASS,
                              MaxObjectCount=100,
                              namespace=TEST_CLASS_NAMESPACE)

        insts = result.instances

        while not result.eos:
            result = self.cimcall(
                self.conn.PullInstancesWithPath, result.context,
                MaxObjectCount=1)

            self.assertTrue(len(result.instances) <= 1)
            insts.append(result.instances)

        for inst in result.instances:
            self.assertTrue(isinstance(inst, CIMInstance))
            self.assertTrue(isinstance(inst.path, CIMInstanceName))
            self.assertTrue(len(inst.path.namespace) > 0)

        insts2 = self.cimcall(self.conn.EnumerateInstances, TEST_CLASS)

        if len(result.instances) != len(insts2):
            print('Error len(result.instances=%s len(insts2=%s' %
                  (len(result.instances), len(insts2)))

        self.assertTrue(len(result.instances) == len(insts2))

    def test_bad_namespace(self):
        """Call with explicit CIM namespace that does not exist"""

        try:
            self.cimcall(self.conn.OpenEnumerateInstances,
                         TEST_CLASS,
                         namespace='root/blah')

        except CIMError as arg:
            if arg[0] != CIM_ERR_INVALID_NAMESPACE:
                raise

    def test_zero_open(self):
        """ Test with default on open. Should return zero instances
        """
        result = self.cimcall(self.conn.OpenEnumerateInstances, TEST_CLASS)

        self.assertTrue(result.eos is False)
        self.assertTrue(len(result.instances) == 0)

        result = self.cimcall(self.conn.PullInstancesWithPath,
                              result.context,
                              MaxObjectCount=100)

        self.assertTrue(result.eos is True)

    def test_close_early(self):
        """"Close enumeration session after initial Open"""
        result = self.cimcall(self.conn.OpenEnumerateInstances, TEST_CLASS)

        self.assertFalse(result.eos)
        self.assertTrue(len(result.instances) == 0)

        self.cimcall(self.conn.CloseEnumeration, result.context)

    def test_get_onebyone(self):
        """Get instances with MaxObjectCount = 1)"""

        result = self.cimcall(
            self.conn.OpenEnumerateInstances, 'CIM_ManagedElement',
            MaxObjectCount=1)

        self.assertTrue(len(result.instances) <= 1)

        self.assertFalse(result.eos)

        insts = result.instances

        while not result.eos:
            result = self.cimcall(
                self.conn.PullInstancesWithPath, result.context,
                MaxObjectCount=1)

            self.assertTrue(len(result.instances) <= 1)
            insts.append(result.instances)

        # get with EnumInstances and compare returns
        insts2 = self.cimcall(self.conn.EnumerateInstances,
                              'CIM_ManagedElement')

        if (len(insts) != len(insts2)):
            print('ERROR. rtn counts do not match insts=%s insts2=%s' % \
                 (len(insts), len(insts2)))
        self.assertTrue(len(insts) == len(insts2))

    def test_open_continueonerror(self):
        """ContinueOnError. Pegasus does not support this parameter
        """
        try:
            self.cimcall(self.conn.OpenEnumerateInstances,
                         TEST_CLASS,
                         MaxObjectCount=100,
                         ContinueOnError=True)

        except CIMError as arg:
            if arg[0] != CIM_ERR_NOT_SUPPORTED:
                raise

    def test_open_invalid_filterquerylanguage(self):
        """Test invalid FilterQueryLanguage parameter """
        try:
            self.cimcall(self.conn.OpenEnumerateInstances,
                         TEST_CLASS,
                         MaxObjectCount=100,
                         FilterQueryLanguage='BLAH')
        # TODO why does pegasus return this
        except CIMError as arg:
            if arg[0] != CIM_ERR_FAILED:
                raise

    def test_open_invalid_filterquerylanguagewithfilter(self):
        """Test valid filter but invalid FilterQueryLanguage"""
        try:
            self.cimcall(self.conn.OpenEnumerateInstances,
                         TEST_CLASS,
                         MaxObjectCount=100,
                         FilterQueryLanguage='BLAH',
                         FilterQuery="p = 4")

        except CIMError as arg:
            if arg[0] != CIM_ERR_QUERY_LANGUAGE_NOT_SUPPORTED:
                raise

    def test_open_invalid_filterquery(self):
        """Test Invalid FilterQuery
        """
        try:
            self.cimcall(self.conn.OpenEnumerateInstances,
                         TEST_CLASS,
                         MaxObjectCount=100,
                         FilterQueryLanguage='DMTF:FQL',
                         FilterQuery="blah")

        except CIMError as arg:
            if arg[0] != CIM_ERR_INVALID_QUERY:
                raise

    def test_open_filter_returnsnone(self):
        """Test with filter that filters out all responses
        """

        filter_statement = "%s = 'blah'" % TEST_CLASS_PROPERTY2
        result = self.cimcall(self.conn.OpenEnumerateInstances,
                              TEST_CLASS,
                              MaxObjectCount=100,
                              FilterQueryLanguage='DMTF:FQL',
                              FilterQuery=filter_statement)
        self.assertTrue(result.eos)
        self.assertTrue(len(result.instances) == 0)

    def test_open_timeoutset(self):
        """Test with filter that filters out all responses
        """

        result = self.cimcall(self.conn.OpenEnumerateInstances,
                              TEST_CLASS,
                              MaxObjectCount=100,
                              OperationTimeout=10)
        self.assertTrue(result.eos)
        self.assertTrue(len(result.instances) == 1)

class PullEnumerateInstancePaths(ClientTest):

    def test_open_complete(self):
        """Simplest invocation. Everything comes back in
           initial response with end-of-sequence == True
           Cannot depend on open returning anything because of
           server timing.
        """

        result = self.cimcall(self.conn.OpenEnumerateInstancePaths,
                              TEST_CLASS,
                              MaxObjectCount=100)

        paths = result.paths

        self.assertTrue(len(result.paths) <= 100)

        if result.eos:
            self.assertTrue(result.context is None)
        else:
            self.assertTrue(len(result.context) != 0)

        while not result.eos:
            result = self.cimcall(self.conn.PullInstancePaths,
                                  result.context,
                                  MaxObjectCount=1)

            self.assertTrue(len(result.paths) <= 1)
            paths.append(result.paths)

        paths2 = self.cimcall(self.conn.EnumerateInstanceNames, TEST_CLASS)

        self.assertTrue(len(result.paths) == len(paths2))

    def test_open_complete_with_ns(self):
        """Simplest invocation. Everything comes back in
           initial response with end-of-sequence == True
        """

        result = self.cimcall(self.conn.OpenEnumerateInstancePaths,
                              TEST_CLASS, namespace=TEST_CLASS_NAMESPACE,
                              MaxObjectCount=100)

        paths = result.paths
        print('openenum pathslen = %s' % len(result.paths))
        self.assertTrue(len(result.paths) <= 100)

        if result.eos:
            self.assertTrue(result.context is None)
        else:
            self.assertTrue(len(result.context) != 0)

        while not result.eos:
            result = self.cimcall(self.conn.PullInstancePaths,
                                  result.context,
                                  MaxObjectCount=1)

            self.assertTrue(len(result.paths) <= 1)
            paths.append(result.paths)
            print('openenum while len=%s total=%s' % (len(result.paths),
                                                      len(paths)))

        # get with enum.
        paths2 = self.cimcall(self.conn.EnumerateInstanceNames, TEST_CLASS)

        if (len(paths) != len(paths2)):
            print('ERROR result.paths len %s ne paths2 len %s' %  \
                (len(paths), len(paths2)))
        self.assertTrue(len(paths) == len(paths2))

    def test_bad_namespace(self):
        """Call with explicit CIM namespace that does not exist"""

        try:
            self.cimcall(self.conn.OpenEnumerateInstancePaths,
                         TEST_CLASS,
                         namespace='root/blah')

        except CIMError as arg:
            if arg[0] != CIM_ERR_INVALID_NAMESPACE:
                raise

    def test_zero_open(self):
        """ TODO
        """
        result = self.cimcall(self.conn.OpenEnumerateInstancePaths, TEST_CLASS)

        self.assertFalse(result.eos)

        # Pull the remainder of the paths
        result = self.cimcall(self.conn.PullInstancePaths,
                              result.context,
                              MaxObjectCount=100)

        self.assertTrue(result.eos)

    def test_close_early(self):
        """"Close enumeration session after initial Open"""
        result = self.cimcall(self.conn.OpenEnumerateInstancePaths, TEST_CLASS)

        self.assertFalse(result.eos)
        self.assertTrue(len(result.paths) == 0)

        self.cimcall(self.conn.CloseEnumeration, result.context)

    def test_get_onebyone(self):
        """Get instances with MaxObjectCount = 1)"""

        result = self.cimcall(
            self.conn.OpenEnumerateInstancePaths, 'CIM_ManagedElement',
            MaxObjectCount=1)

        self.assertFalse(result.eos)

        paths = result.paths

        while not result.eos:
            result = self.cimcall(self.conn.PullInstancePaths,
                                  result.context,
                                  MaxObjectCount=1)

            self.assertTrue(len(result.paths) <= 1)
            paths.append(result.paths)

        # get with EnumInstanceNamess and compare returns
        paths2 = self.cimcall(self.conn.EnumerateInstanceNames,
                              'CIM_ManagedElement')

        if (len(paths) != len(paths2)):
            print('Error in length paths=%s, paths2=%s' % (len(paths),
                                                           len(paths2)))
        self.assertTrue(len(paths) == len(paths2))

class PullReferences(ClientTest):

    def test_all_instances_in_ns(self):
        """Simplest invocation. Everything comes back in
           initial response with end-of-sequence == True
        """
        # get all instances under CIM_ManagedElement
        paths = self.cimcall(self.conn.EnumerateInstanceNames,
                             'CIM_ManagedElement')

        for pathi in paths:
            result = self.cimcall(self.conn.OpenReferenceInstances,
                                  pathi,
                                  MaxObjectCount=100)

            insts = result.instances

            while not result.eos:
                result = self.cimcall(
                    self.conn.PullInstancesWithPath, result.context,
                    MaxObjectCount=1)

                self.assertTrue(len(result.instances) <= 1)
                insts.append(result.instances)

            for inst in result.instances:
                self.assertTrue(isinstance(inst, CIMInstanceName))
                self.assertTrue(len(inst.namespace) > 0)

            insts2 = self.cimcall(self.conn.References, pathi)
            if len(insts2) != 0:
                print('References %s count %s' % (pathi, len(insts2)))
            self.assertTrue(len(insts) == len(insts2))
            #TODO ks 5/30 2016 add tests here
            #Do this as a loop for all instances above.

    def test_invalid_instance_name(self):
        """Test with name that is invalid class Expects exception"""
        foo_path = CIMInstanceName('CIM_Foo')

        try:
            self.cimcall(self.conn.OpenReferenceInstances,
                         foo_path, MaxObjectCount=100)
                         
            # should never execute next line                      
            self.assertTrue(False)
            
        except CIMError as ce:
            if ce.args[0] != CIM_ERR_INVALID_PARAMETER:
                raise

class PullReferencePaths(ClientTest):
    """Tests on OpenReferencePaths and pulling"""
    
    def test_all_instances_in_ns(self):
        """
            Simplest invocation. Execute and compae with results
            of ReferenceNames
        """
        # get all instances under CIM_ManagedElement
        paths = self.cimcall(self.conn.EnumerateInstanceNames,
                             'CIM_ManagedElement')
        # loop for all paths returned by EnumerateInstanceNames
        for pathi in paths:
            result = self.cimcall(self.conn.OpenReferenceInstancePaths,
                                  pathi,
                                  MaxObjectCount=100)

            for path in result.paths:
                self.assertInstanceNameValid(path)

            paths = result.paths

            while not result.eos:
                result = self.cimcall(self.conn.PullInstancePaths,
                                      result.context,
                                      MaxObjectCount=1)

                for path in result.path:
                    self.assertInstanceNameValid(path)

                paths.append(result.paths)

            paths2 = self.cimcall(self.conn.ReferenceNames, pathi)
            if len(paths2) != 0:
                print('References %s count %s' % (pathi, len(paths2)))
            self.assertTrue(len(paths) == len(paths2))
            
            #TODO ks 5/30 2016 add tests here
            #Do this as a loop for all instances above.

class PullAssociators(ClientTest):

    def test_all_instances_in_ns(self):
        """Simplest invocation. Everything comes back in
           initial response with end-of-sequence == True
        """
        # get all instances under CIM_ManagedElement
        paths = self.cimcall(self.conn.EnumerateInstanceNames,
                             'CIM_ManagedElement')

        for pathi in paths:
            result = self.cimcall(self.conn.OpenAssociatorInstances,
                                  pathi,
                                  MaxObjectCount=100)

            insts = result.instances

            while not result.eos:
                result = self.cimcall(
                    self.conn.PullInstancesWithPath, result.context,
                    MaxObjectCount=1)

                self.assertTrue(len(result.instances) <= 1)
                insts.append(result.instances)

            for inst in result.instances:
                self.assertTrue(isinstance(inst, CIMInstanceName))
                self.assertTrue(len(inst.namespace) > 0)

            insts2 = self.cimcall(self.conn.References, pathi)
            if len(insts2) != 0:
                print('Associators %s count %s' % (insts, len(insts2)))
            self.assertTrue(len(insts) == len(insts2))
            #TODO ks 5/30 2016 add tests here
            #Do this as a loop for all instances above.

    def test_invalid_instance_name(self):
        """Test with name that is invalid class"""
        foo_path = CIMInstanceName('CIM_Foo')

        try:
            self.cimcall(self.conn.OpenAssociatorInstances,
                                  foo_path,
                                  MaxObjectCount=100)
            self.assertTrue(False)
        except CIMError as ce:
            if ce.args[0] != CIM_ERR_INVALID_PARAMETER:
                raise


class PullAssociatorPaths(ClientTest):

    def test_all_instances_in_ns(self):
        """Simplest invocation. Everything comes back in
           initial response with end-of-sequence == True
        """
        # get all instances under CIM_ManagedElement
        paths = self.cimcall(self.conn.EnumerateInstanceNames,
                             'CIM_ManagedElement')
        # loop for all paths returned by EnumerateInstanceNames
        for pathi in paths:
            result = self.cimcall(self.conn.OpenAssociatorInstancePaths,
                                  pathi,
                                  MaxObjectCount=100)

            for path in result.paths:
                self.assertInstanceNameValid(path)

            paths = result.paths

            while not result.eos:
                result = self.cimcall(self.conn.PullInstancePaths,
                                      result.context,
                                      MaxObjectCount=1)

                for path in result.path:
                    self.assertInstanceNameValid(path)

                paths.append(result.paths)

            paths2 = self.cimcall(self.conn.AssociatorNames, pathi)
            if len(paths2) != 0:
                print('Associator Names %s count %s' % (pathi, len(paths2)))
            self.assertTrue(len(paths) == len(paths2))
            #TODO ks 5/30 2016 add tests here
            #Do this as a loop for all instances above.

class ExecQuery(ClientTest):

    def test_simple_execquery(self):
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
    def test_execquery_namespace_error(self):
        try:

            self.cimcall(self.conn.ExecQuery,
                         'WQL',
                         'Select * from %s' % TEST_CLASS,
                         namespace='root/blah')

        except CIMError as ce:
            if ce.args[0] != CIM_ERR_INVALID_NAMESPACE:
                raise

    def test_execquery_invalid_querylang(self):
        """Test execquery with invalid query_lang parameter"""
        try:

            self.cimcall(self.conn.ExecQuery,
                         'wql',
                         'Select * from %s' % TEST_CLASS,
                         namespace='root/cimv2')

        except CIMError as ce:
            if ce.args[0] != CIM_ERR_QUERY_LANGUAGE_NOT_SUPPORTED:
                raise

    def test_execquery_invalid_query(self):
        """Test with invalid query syntax"""
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

        # Simple invocation

        obj = self.cimcall(self.conn.GetInstance,
                           name)

        self.assertTrue(isinstance(obj, CIMInstance))
        self.assertTrue(isinstance(obj.path, CIMInstanceName))

        # Call with property list and localonly=False
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

        # call with  IncludeQualifiers

        # Call with IncludeClassOrigin

        # Call with IncludeQualifiers and IncludeClassOrigin

        # Call with invalid namespace path

        invalid_name = name.copy()
        invalid_name.namespace = 'blahblahblah'

        # Call with invalid Class Name

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
# Associators request interface tests
#################################################################

class Associators(ClientTest):
    """ Tests of the associators request operation"""

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

    def test_class_associator(self):
        """
            Test getting associator classes for defined class
        """

        assoc_classes = self.cimcall(self.conn.Associators, TEST_CLASS)

        print('class assoc for %s' % TEST_CLASS)
        for cls in assoc_classes:
            #validate is class return
            print('type %s' % type(cls))
            #self.assertTrue(isinstance(cls, CIMClass))
            print('%s\n' % repr(cls))

    def test_class_associators(self):
        """
            Test getting associator classes for all classes in
            namespace
        """

        classes = self.cimcall(self.conn.EnumerateClassNames,
                               DeepInheritance=True)

        for cls in classes:
            assoc_classes = self.cimcall(self.conn.Associators, cls)

            print('class assoc for %s \n%s' % (cls, assoc_classes))

class AssociatorNames(ClientTest):

    def test_all(self):

        # Call on named instance

        inst_names = self.cimcall(self.conn.EnumerateInstanceNames,
                                  TEST_CLASS)
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

        top_names = self.cimcall(self.conn.EnumerateClassNames)

        class_names = top_names

        for name in class_names:
            self.assertTrue(isinstance(name, six.string_types))

        if self.verbose:
            print('Found %s top level classes' % len(class_names))

        # enumerate each entry in top_names
        for name in top_names:
            sub_names = self.cimcall(self.conn.EnumerateClassNames,
                                     ClassName=name)
            for n in sub_names:
                self.assertTrue(isinstance(n, six.string_types))
            class_names += sub_names
        if self.verbose:
            print('Found %s 1,2 level classes' % len(class_names))

        # Test with DeepInheritance
        top_names = self.cimcall(self.conn.EnumerateClassNames)
        full_name_list = top_names
        subname_list = []
        for name in top_names:
            sub_names = self.cimcall(self.conn.EnumerateClassNames,
                                     ClassName=name, DeepInheritance=True)
            for n in sub_names:
                self.assertTrue(isinstance(n, six.string_types))
            subname_list += sub_names

        full_name_list += subname_list
        self.assertTrue(TEST_CLASS in full_name_list,
                        'test class not found')
        #TODO could we assert some size limit here. Probably Not
        # since this applies to any server.
        if self.verbose:
            print('end deep inheritance size %s' % len(full_name_list))

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

        #TODO extend for options of Deepinheritance, LocalOnly,
        # IncludeQualifiers, IncludeClassOrigin

class GetClass(ClientClassTest):
    """Test the get Class request operation"""

    def test_simple(self):
        """Get a classname from server and then get class"""

        name = self.cimcall(self.conn.EnumerateClassNames)[0]
        cl = self.cimcall(self.conn.GetClass, name)
        if self.debug:
            print('GetClass gets name %s' % name)
        self.verify_class(cl)
        mof_output = cl.tomof()
        if self.verbose:
            print('MOF OUTPUT\n%s' % (mof_output))

    def test_nonexistent_class(self):
        try:
            self.cimcall(self.conn.GetClass, 'CIM_BlanBlahBlah')
        except CIMError as ce:
            if ce.args[0] != CIM_ERR_NOT_FOUND:
                raise

        #TODO extend for options of Deepinheritance, LocalOnly,
        # IncludeQualifiers, IncludeClassOrigin


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
# Open pegasus tests
#################################################################

class PegasusServerTestBase(ClientTest):
    """ Common superclass for all tests run against OpenPegasus
        server.  Assumes characteristics that may exist only
        in this server and specifically in the test version of the
        server.
    """

    def get_namespaces(self):
        """ Return list of namespaces found converted to strings
            from utf-8 strings using CIM_Namespace class as source
        """

        interop = self.get_interop_namespace()
        class_name = 'CIM_Namespace'
        try:
            namespaces = []
            instances = self.cimcall(self.conn.EnumerateInstances,
                                     class_name,
                                     namespace=interop,
                                     LocalOnly=True)
            self.assertTrue(len(instances) != 0)
            if self.verbose:
                print('Namespaces:')
                for instance in instances:
                    prop = instance.properties['Name'].value
                    ascii = prop.encode()
                    print ('  %s' % (ascii))
                    namespaces.append(ascii)

            return namespaces

        except CIMError as ce:
            if ce.args[0] != CIM_ERR_NOT_FOUND:
                print('CIMError %s. Could not find' % class_name)
            raise

    def is_pegasus_server(self):
        """ Test to determine if this the OpenPegasus server.
            Test for valid interop namespace, and the existence of
            PG_ObjectManager in that namespace

            :returns: True if the server being tested is open pegasus
        """
        ns = self.get_interop_namespace()
        if ns is None:
            return False
        try:
            self.cimcall(self.conn.GetClass, "PG_ObjectManager",
                         namespace=ns)
        except CIMError:
            print('Class PG_ObjectManager not found')
            return False

        try:
            instances_ = self.cimcall(self.conn.EnumerateInstances,
                                      "PG_ObjectManager",
                                      namespace=ns,)
            # should be one instance of the class.

            if len(instances_) != 1:
                print('No instances of PG_ObjectManager')
                return False

            if self.verbose:
                for i in instances_:
                    if self.verbose:
                        # should have name and version in string
                        print(i.properties["Description"])
                        # should say pegasus
                        print(i.properties["ElementName"])


        except CIMError as ce:
            print('Class PG_ObjectManager not found')
            return False

        return False

    def is_pegasus_test_build(self):
        """Assure that this is a pegasus test build with the test
           namespace. Tests the test/testprovider namespace existence
        """

        if self.is_pegasus_server():
            namespaces = self.get_namespaces()

            if 'test/testprovider' in namespaces:
                return True
            return False
        return False


    def get_interop_namespace(self):
        """Return the namespace used by this pegasus as interop
           If one of the listed namespaces is interop, return
           the name of that namespace.
           If a namespace matches but it has no classes fail test
           If one of the listed namespaces cannot be found,
           return None
        """

        for ns in INTEROP_NAMESPACE_LIST:
            try:
                classes_ = self.cimcall(self.conn.EnumerateClassNames,
                                        namespace=ns,)
                self.assertFalse((len(classes_) == 0),
                                 'Interop namspace empty')
                return ns
            except CIMError as ce:
                if ce.args[0] != CIM_ERR_INVALID_NAMESPACE:
                    raise
        return None

    def try_class(self, ns, class_name):
        """Test if class exists
           returns true if `class_name` exists
        """
        try:
            my_class = self.cimcall(self.conn.GetClass, class_name,
                                    namespace=ns)
            return True
        except CIMError as ce:
            if ce.args[0] != CIM_ERR_NOT_FOUND:
                print('class get %s failed' % my_class)
                raise
            else:
                return False

    def has_namespace(self, ns):
        ns_ = self.get_namespaces()

        for n in ns_:
            if n == ns:
                return True
        return False

    def get_instances(self, ns, class_name):

        # test to be sure class exists
        # self.try_class(ns, class)

        try:
            instances = self.cimcall(self.conn.EnumerateInstances,
                                     class_name,
                                     namespace=ns)
            return instances

        # TODO figure out why we could not get instances of a class
        #  and whether we should continue. do more than raise. This
        #  is an assert
        except CIMError as ce:
            raise
            #if ce.args[0] != CIM_ERR_NOT_FOUND:
                #print('class get %s failed' % my_class)
                #raise
            #else:
                #return False

    def get_registered_profiles(self):
        """get the registered profile instances"""

        interop = self.get_interop_namespace()
        self.assertTrue(interop is not None)
        profiles = self.get_instances(interop, 'CIM_RegisteredProfile')
        self.assertTrue(len(profiles) != 0)
        if self.verbose:
            for i in profiles:
                print(i.tomof())

class PegasusInteropTest(PegasusServerTestBase):
    """Test for valid interop namespace in a pegasus server"""

    def test_interop_namespace(self):
        interop = self.get_interop_namespace()
        if self.verbose:
            print('interop=%r' % interop)

        self.assertTrue(interop is not None)

        namespaces_ = self.get_namespaces()

        self.assertTrue(namespaces_ is not None)

        self.assertTrue(self.try_class(interop, 'CIM_RegisteredProfile'))
        self.assertTrue(self.try_class(interop, 'CIM_Namespace'))

class PEGASUSCLITestClass(PegasusServerTestBase):
    """Test against a class that has all of the property types
       defined
    """

    def test_all(self):
        if self.is_pegasus_test_build():
            class_name = 'Test_CLITestProviderClass'
            ns = 'test/TestProvider'

            # Get the class, test and possibly display
            my_class = self.cimcall(self.conn.GetClass, class_name,
                                    namespace=ns, LocalOnly=False)

            mofout = my_class.tomof()
            xmlout = my_class.tocimxml().toprettyxml(indent='  ')

            if self.verbose:
                print('MOF for %s\n%s' % (my_class, mofout))
                print('CIMXML  for %s\n%s' % (my_class, xmlout))

            inst_paths = self.cimcall(self.conn.EnumerateInstanceNames,
                                      class_name, namespace=ns)
            for inst_path in inst_paths:
                if self.verbose:
                    print('class %s instance %s' % (class_name, inst_path))
                inst_path_xml = inst_path.tocimxml().toprettyxml(indent='  ')
                if self.verbose:
                    print('INST PATH %s' % inst_path_xml)

            # Enumerate instances of the class
            instances = self.cimcall(self.conn.EnumerateInstances,
                                     class_name, namespace=ns)
            for instance in instances:
                if self.verbose:
                    print('class %s============= instance %s'
                          % (class_name, instance.path))
                mofout = instance.tomof()
                xmlout = instance.tocimxml().toprettyxml(indent='  ')
                if self.verbose:
                    print('MOF for %s\n%s' % (instance, mofout))
                    print('CIMXML  for %s\n%s' % (instance, xmlout))
        # TODO create an instance write it, get it and test results


class PegasusTestEmbeddedInstance(PegasusServerTestBase):
    """Tests a specific provider implemented pegasus class that
        includes an embedded instance
    """

    def test_all(self):
        if self.is_pegasus_test_build():
            # test class with embedded instance
            cl1 = 'Test_CLITestEmbeddedClass'
            ns = 'test/TestProvider'
            prop_name = 'embeddedInst'
            property_list = ['embeddedInst']
            #property_list = ['comment', 'Id']
            property_list = [prop_name]

            instances = self.cimcall(self.conn.EnumerateInstances,
                                     cl1, namespace=ns,
                                     propertylist=property_list)
            for inst in instances:
                if self.verbose:
                    print('====== %s MOF=====\n%s' %(inst.path, inst.tomof()))
                    print('======%s XML=====\n%s' %(inst.path,
                                                    inst.tocimxmlstr(2)))
                prop = inst.properties[prop_name]

                self.assertTrue(prop.embedded_object)

                embedded_inst = prop.value

                if self.verbose:
                    print('EmbeddedInstance type=%s rep=%s' %
                          (type(embedded_inst), repr(embedded_inst)))
                self.assertIsInstance(embedded_inst, CIMInstance,
                                      msg='Embedded Inst must be CIMInstance')

                if embedded_inst.path is not None:
                    self.assertIsInstance(embedded_inst.path, CIMInstanceName)
                if self.verbose:
                    print('embedded_inst mof=%s' % embedded_inst.tomof())
                id_prop = embedded_inst.properties['Id']
                self.assertIsInstance(id_prop, CIMProperty)
                name_prop = embedded_inst.properties['name']
                self.assertIsInstance(name_prop, CIMProperty)

            # TODO Create a new instance on server and test return using
            # getInstance


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

    # Pegasus only tests
    'PEGASUSCLITestClass',
    'PegasusTestEmbeddedInstance'
    'PegasusInteropTest'
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
        print('    -nvc                Do not verify server certificates.')
        print('    --cacerts           File/dir with ca certificate(s).')

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
    args_['cacerts'] = None
    args_['nvc'] = None

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
        elif argv[1] == '-nvc':
            args_['nvc'] = True
            del argv[1:2]
        elif argv[1] == '--cacerts':
            args_['cacerts'] = True
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
    print("  nvc: %s"      % args['nvc'])
    print("  cacerts: %s" % args['cacerts'])
    print("  timeout: %s" % args['timeout'])
    print("  verbose: %s" % args['verbose'])
    print("  debug: %s" % args['debug'])

    # Note: unittest options are defined in separate args after
    # the url argumentl.
    unittest.main()

