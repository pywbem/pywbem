#!/usr/bin/env python

"""
Test CIM operations against a real WBEM server that is specified on the
command line.  It executes either a specific test or the full test
suite depending on user input.

The return codes here may be specific to OpenPegasus.
"""

from __future__ import absolute_import

# Can be used with pb.set_trace() to debug really nasty issues.
# import pdb

# pylint: disable=missing-docstring,superfluous-parens,no-self-use

import sys
import os
import re
from socket import getfqdn
import threading
import types
from datetime import timedelta, datetime
import unittest
from getpass import getpass
import warnings
import time
import traceback

from six.moves.urllib.parse import urlparse
import six

from tests.unittest.utils.unittest_extensions import RegexpMixin

# pylint: disable=wrong-import-position, wrong-import-order, invalid-name
from tests.utils import import_installed
pywbem = import_installed('pywbem')
from pywbem import CIM_ERR_NOT_FOUND, CIM_ERR_FAILED, \
    CIM_ERR_INVALID_NAMESPACE, CIM_ERR_INVALID_PARAMETER, \
    CIM_ERR_NOT_SUPPORTED, CIM_ERR_INVALID_CLASS, \
    CIM_ERR_METHOD_NOT_AVAILABLE, CIM_ERR_INVALID_QUERY, \
    CIM_ERR_QUERY_LANGUAGE_NOT_SUPPORTED, CIM_ERR_INVALID_ENUMERATION_CONTEXT, \
    CIM_ERR_METHOD_NOT_FOUND, CIM_ERR_ALREADY_EXISTS, DEFAULT_NAMESPACE, \
    MinutesFromUTC  # noqa: E402
from pywbem import WBEMConnection, WBEMServer, CIMError, Error, WBEMListener, \
    WBEMSubscriptionManager, CIMInstance, CIMInstanceName, CIMClass, \
    CIMClassName, CIMProperty, CIMQualifier, CIMQualifierDeclaration, \
    CIMMethod, ValueMapping, Uint8, Uint16, Uint32, Uint64, Sint8, Sint16, \
    Sint32, Sint64, Real32, Real64, CIMDateTime, TestClientRecorder, \
    configure_logger  # noqa: E402
from pywbem._mof_compiler import MOFCompiler  # noqa: E402
from pywbem._subscription_manager import SUBSCRIPTION_CLASSNAME, \
    DESTINATION_CLASSNAME, FILTER_CLASSNAME  # noqa: E402
# pylint: enable=wrong-import-position, wrong-import-order, invalid-name


# output files
TEST_DIR = os.path.dirname(__file__)
LOG_FILE_NAME = 'run_cim_operations.log'
RUN_CIM_OPERATIONS_OUTPUT_LOG = '%s/%s' % (TEST_DIR, LOG_FILE_NAME)

# Test for decorator for unimplemented tests
# decorator is @unittest.skip(UNIMPLEMENTED)
UNIMPLEMENTED = "test not implemented"

# Test for long running unittests.  Modified by cli args.
SKIP_LONGRUNNING_TEST = True

CLI_ARGS = None

# define the file that contains the PyWBEM_Person, etc. mof
PYWBEM_TEST_MOF_FILE = os.path.join('tests', 'unittest', 'pywbem', 'test.mof')

# A class that should be implemented in a wbem server and is used
# for testing
TEST_CLASS = 'CIM_ComputerSystem'
TEST_CLASS_NAMESPACE = 'root/cimv2'
TEST_CLASS_PROPERTY1 = 'Name'
TEST_CLASS_PROPERTY2 = 'CreationClassName'
TEST_CLASS_CIMNAME = CIMInstanceName(TEST_CLASS,
                                     namespace=TEST_CLASS_NAMESPACE)

# Pegasus class/namespace to use for some tests.  This is pegasus only but
# allows the client to define the number of response objects.
TEST_PEG_STRESS_NAMESPACE = "test/TestProvider"
TEST_PEG_STRESS_CLASSNAME = "TST_ResponseStressTestCxx"

# definition of a standard class defined in PyWBEM package that can be
# used.  Any test should first confirm that the primary class exists
# in the envirnment before using.  There is a defined method in setUp
# (pywbem_person_class_exists) for this.
# TODO ks Nov 2016 Create decerators for both this and the OpenPegasus
# limitations on tests.
PYWBEM_PERSON_CLASS = "PyWBEM_Person"
PYWBEM_PERSONCOLLECTION = "PyWBEM_PersonCollection"
PYWBEM_MEMBEROFPERSONCOLLECTION = "PyWBEM_MemberOfPersonCollection"
PYWBEM_SOURCE_ROLE = "member"
PYWBEM_TARGET_ROLE = "collection"

# TOP level class that can be used for tests. Note that this class delivers
# differing numbers of instances over time because it is reporting on the
# running server.
TOP_CLASS = 'CIM_ManagedElement'
TOP_CLASS_NAMESPACE = 'root/cimv2'

INTEROP_NAMESPACE_LIST = ['interop', 'root/interop', 'root/PG_InterOp']


class ClientTest(unittest.TestCase):
    """ Base class that creates a pywbem.WBEMConnection for
        subclasses to use based on cmd line arguments. It provides
        a common cimcall method that executes test calls and logs
        results
    """
    # pylint: disable=arguments-differ
    def setUp(self, use_pull_operations=None):
        """Create a connection."""

        self.system_url = CLI_ARGS['url']
        self.namespace = CLI_ARGS['namespace']
        self.verbose = CLI_ARGS['verbose']
        self.debug = CLI_ARGS['debug']
        self.yamlfile = CLI_ARGS['yamlfile']
        self.output_log = CLI_ARGS['log']
        self.yamlfp = None
        self.stats_enabled = bool(CLI_ARGS['stats'])
        if self.stats_enabled:
            self.start_time = time.time()

        # Set this because python 3 http libs generate many ResourceWarnings
        # and unittest enables these warnings.
        if not six.PY2:
            # pylint: disable=undefined-variable
            warnings.simplefilter("ignore", ResourceWarning)  # noqa: F821

        self.log('setup connection {0} ns {1}'.
                 format(self.system_url, self.namespace))

        self.conn = WBEMConnection(
            self.system_url,
            (CLI_ARGS['username'], CLI_ARGS['password']),
            self.namespace,
            timeout=CLI_ARGS['timeout'],
            no_verification=CLI_ARGS['nvc'],
            ca_certs=CLI_ARGS['cacerts'],
            use_pull_operations=use_pull_operations,
            stats_enabled=self.stats_enabled)

        # if log set, enable the logger.
        if self.output_log:
            configure_logger(
                'all', log_dest='file', log_filename='run_cimoperations.log',
                connection=self.conn)

        # enable saving of xml for display
        self.conn.debug = CLI_ARGS['debug']

        if self.yamlfile is not None:
            self.yamlfp = TestClientRecorder.open_file(self.yamlfile, 'a')
            self.conn.add_operation_recorder(TestClientRecorder(self.yamlfp))

        self.log('Connected {0}, ns {1}'.
                 format(self.system_url, CLI_ARGS['namespace']))

    def tearDown(self):
        """Close the test_client YAML file and display stats."""

        if self.stats_enabled:
            print('%s: Test time %.2f sec.' % (self.id(),
                                               (time.time() - self.start_time)))
            print('%s\n%s' % (self.id(), self.conn.statistics.formatted()))

        if self.yamlfp is not None:
            self.yamlfp.close()

    def cimcall(self, fn, *pargs, **kwargs):
        """Make a PyWBEM call, catch any exceptions, and log the
           request and response XML.
           Logs the call parameters, request/response xml,
           and response status

           Returns result of request to caller
        """

        self.log('cimcall fn {0} args *pargs {1} **kwargs {2}'.
                 format(fn, pargs, kwargs))
        try:
            result = fn(*pargs, **kwargs)
        except Exception as exc:
            self.log('Operation %s failed with %s: %s\n' %
                     (fn.__name__, exc.__class__.__name__, str(exc)))
            last_request = self.conn.last_request or self.conn.last_raw_request
            self.log('Request:\n\n%s\n' % last_request)
            last_reply = self.conn.last_reply or self.conn.last_raw_reply
            self.log('Reply:\n\n%s\n' % last_reply)
            raise

        # This code displays operation results by calling the method log
        self.log('Operation %s succeeded\n' % fn.__name__)
        last_request = self.conn.last_request or self.conn.last_raw_request
        self.log('Request:\n\n%s\n' % last_request)
        last_reply = self.conn.last_reply or self.conn.last_raw_reply
        self.log('Reply:\n\n%s\n' % last_reply)

        # account for issue where last operation exception, in particular
        # those few exceptions that occur outside of the try block in the
        # Iter... operations.
        if self.stats_enabled:
            # svr_time and operation_time may return None
            svr_time = ('%.4f' % self.conn.last_server_response_time) \
                if self.conn.last_server_response_time else 'None'

            operation_time = ('%.4f' % self.conn.last_operation_time) \
                if self.conn.last_operation_time else 'None'

            print('Operation stats: time %s req_len %d reply_len %d '
                  'svr_time %s' %
                  (operation_time,
                   self.conn.last_request_len,
                   self.conn.last_reply_len,
                   svr_time))

        return result

    def log(self, data_):
        """Display log entry if verbose."""
        # TODO ks aug 17. FUTURE This should be integrated into logging
        if self.verbose:
            print('{0}'.format(data_))

    def pywbem_person_class_exists(self):
        """
        Test this class if it exists in the root/cimv2 namespace.

        This is a simple group of classes that allows class, instance,
        and reference/associators testing. If the class does not exist
        the detailed tests should ignore the test.

        The mof for this test is in the MOF file PYWBEM_TEST_MOF_FILE.

        Returns True if the class exists. or was correctly installed
        in the target WBEMServer. Otherwise returns False so tests can
        continue wittout the tests that involve these classes.
        """
        try:
            self.cimcall(self.conn.GetClass, PYWBEM_PERSON_CLASS)
            return True
        except CIMError as ce:
            if ce.status_code == CIM_ERR_NOT_FOUND:
                mofcomp = MOFCompiler(handle=self.conn)
                try:
                    mofcomp.compile_file(PYWBEM_TEST_MOF_FILE, self.namespace)
                except Error:
                    return False
                else:
                    return True
            # Error other than NOT_FOUND. Just return False so tests continue
            else:
                return False

    def assertClassNamesValid(self, classnames):
        """
        Validate that the classnames are valid cimobject CIMClassName.
        """
        if isinstance(classnames, list):
            for name in classnames:
                self.assertClassNamesValid(name)
        else:
            name = classnames
            self.assertTrue(isinstance(name, CIMClassName))

    def assertPathsValid(self, paths, namespace=None):
        """
        Test for valid path or list of paths.

        Tests for type, and namespace info in path
        """
        # if list, recurse this function
        if isinstance(paths, list):
            for path in paths:
                self.assertPathsValid(path, namespace=namespace)

        else:
            path = paths
            self.assertTrue(isinstance(path, CIMInstanceName))
            self.assertTrue(path.namespace)

            if namespace is None:
                self.assertTrue(paths.namespace == self.namespace)
            else:
                self.assertTrue(path.namespace == namespace)

    def assertInstancesValid(self, instances, includes_path=True,
                             prop_count=None, property_list=None,
                             namespace=None):
        """ Test for valid basic characteristics of an instance or list
            of instances.

            Optional parameters allow optional tests including:

              - includes_path - Test for path component if true. default=true
              - prop_count - test for number of properties in instance
              - property_list - Test for existence of properties in list
              - namespace - Test for valid namespace in path. If none test
                against default namespace. Otherwise test against provided
                namespace name
        """

        # if list, recurse this function
        if isinstance(instances, list):
            for inst in instances:
                self.assertInstancesValid(inst, includes_path=includes_path,
                                          prop_count=prop_count,
                                          property_list=property_list,
                                          namespace=namespace)
        else:
            instance = instances
            self.assertTrue(isinstance(instance, CIMInstance))

            if includes_path:
                self.assertTrue(isinstance(instance.path, CIMInstanceName))
                self.assertTrue(instance.path.namespace,
                                'Instance path missing in instance path.')

                if namespace is None:
                    namespace = self.namespace

                self.assertEqual(instance.path.namespace, namespace,
                                 'Expected instance.path.namespace %s to '
                                 'match expected namespace %s' %
                                 (instance.path.namespace, namespace))

            if prop_count is not None:
                self.assertEqual(len(instance.properties), prop_count,
                                 'Expected %s properties; tested instance has '
                                 '%s properties' % (prop_count,
                                                    len(instance.properties)))

            if property_list is not None:
                for p in property_list:
                    prop = instance.properties[p]
                    self.assertIsInstance(prop, CIMProperty)

    def assertInstanceNamesValid(self, paths, includes_namespace=True,
                                 includes_keybindings=True,
                                 namespace=None):
        """
        Validate that the paths argument is a valid CIMInstanceName or
        list of valid CIMInstanceNames.
        Default is to test for namespace existing and keybindings.
        Optional is to compare namespace.
        """
        if isinstance(paths, list):
            for path in paths:
                self.assertInstanceNamesValid(
                    path,
                    includes_namespace=includes_namespace,
                    includes_keybindings=includes_keybindings,
                    namespace=namespace)

        else:
            path = paths
            self.assertTrue(isinstance(path, CIMInstanceName))
            if includes_namespace:
                self.assertTrue(path.namespace)
            if includes_keybindings:
                self.assertTrue(path.keybindings is not None)
            if namespace is not None:
                self.assertTrue(path.namespace == namespace)

    def assertAssocRefClassRtnValid(self, op_result):
        """ Confirm that an associator or Reference class response
            returns a tuple of (classname, class).

            Accepts either a class or list of classes
        """
        if isinstance(op_result, list):
            for r in op_result:
                self.assertAssocRefClassRtnValid(r)

        else:
            self.assertTrue(isinstance(op_result, tuple))

            self.assertTrue(isinstance(op_result[0], CIMClassName))
            self.assertTrue(op_result[0].namespace)
            self.assertTrue(isinstance(op_result[1], CIMClass))

    def inst_in_list(self, inst, instances, ignore_host=False):
        """ Determine if an instance is in a list of instances.
            Return:
            True if the instance is in the list. Otherwise return False.
            Tests on path only.
        """
        for i in instances:
            if self.pathsEqual(i.path, inst.path, ignore_host=ignore_host):
                return True
        return False

    def pathsEqual(self, path1, path2, ignore_host=False):
        """Test for paths equal. Test ignoring the host component if
           ignore_host = True. Allows us to test without the host
           comonent since that is a difference between pull and not
           pull responses, at least on pegasus
        """
        if ignore_host:
            if path1.host is not None:
                path1 = path1.copy()
                path1.host = None
            if path2.host is not None:
                path2 = path2.copy()
                path2.host = None

        return path1 == path2

    def path_in_list(self, path, paths, ignore_host=False):
        """ Determine if an path is in a list of paths. Return
            True if the instance is in the list. Otherwise return False.
        """
        for i in paths:
            if self.pathsEqual(i, path, ignore_host=ignore_host):
                return True
        return False

    def cmpitem(self, item1, item2):
        """
        Compare two items (CIM values, CIM objects, or NocaseDict objects) for
        unequality.

        Note: Support for comparing the order of the items has been removed
        in pywbem v0.9.0.

        One or both of the items may be `None`.

        The implementation uses the '==' operator of the item datatypes.

        If value1 == value2, 0 is returned.
        If value1 != value2, 1 is returned.
        """
        if item1 is None and item2 is None:
            return 0
        if item1 is None or item2 is None:
            return 1
        if item1 == item2:
            return 0
        return 1

    def assertInstancesEqual(self, insts1, insts2, ignore_host=False,
                             ignore_value_diff=False):
        """Compare two lists of instances for equality of instances
           The instances do not have to be in the same order in
           the lists. The lists must be of equal length.

           Parameters:

             insts1: list of instances or single instance for compare

             insts2: list of instances or single instance for compare to insts1

             ignore_host: Boolean. If true, test for equal host values in\
             path

             ignore_value_diff: Boolean. If True, compare the value of each
             property. If false ignore value differences.
        """

        if not isinstance(insts1, list):
            insts1 = [insts1]
        if not isinstance(insts2, list):
            insts2 = [insts2]
        self.assertEqual(len(insts1), len(insts2))

        for inst1 in insts1:
            self.assertTrue(isinstance(inst1, CIMInstance))
            if not self.inst_in_list(inst1, insts2, ignore_host=ignore_host):
                inst2pathlist = [inst.path for inst in insts2]
                self.fail('Instance Lists do not match. %s not in other list'
                          ' %s' % (inst1.path, inst2pathlist))
            else:
                for inst2 in insts2:
                    if self.pathsEqual(inst1.path, inst2.path,
                                       ignore_host=ignore_host):

                        self.assertTrue(isinstance(inst2, CIMInstance))
                        if ignore_host:
                            if inst1.path.host is not None:
                                inst1 = inst1.copy()
                                inst1.path.host = None
                            if inst2.path.host is not None:
                                inst2 = inst2.copy()
                                inst2.path.host = None
                        # detailed test of instance components if not equal
                        if inst1 != inst2:
                            self.assertEqual(inst1.classname, inst2.classname)
                            self.assertEqual(inst1.path, inst2.path)
                            self.assertEqual(inst1.qualifiers, inst2.qualifiers)

                            # test of equality of each property. We do this
                            # in detail because there are cases where the
                            # property values differ but we test everything
                            # else
                            if inst1.properties != inst2.properties:
                                for k1 in inst1:
                                    p2 = inst2.properties[k1]
                                    p1 = inst1.properties[k1]
                                    self.assertEqual(p1.name, p2.name)
                                    self.assertEqual(p1.type, p2.type)
                                    self.assertEqual(p1.class_origin,
                                                     p2.class_origin)
                                    self.assertEqual(p1.propagated,
                                                     p2.propagated)
                                    self.assertEqual(p1.reference_class,
                                                     p2.reference_class)
                                    self.assertEqual(p1.embedded_object,
                                                     p2.embedded_object)

                                    if p1.value != p2.value:
                                        if not ignore_value_diff:
                                            self.assertEqual(p1.value,
                                                             p2.value)
                                        else:
                                            if self.verbose:
                                                print(
                                                    'Property %s values differ.'
                                                    ' v1=%s\nv2=%s' %
                                                    (p1.name, p1.value,
                                                     p2.value))
                                            continue

                                    self.assertEqual(p1, p2)

                            self.assertEqual(inst1.qualifiers, inst2.qualifiers)
                        # retest to confirm
                        if not ignore_value_diff:
                            self.assertEqual(inst1, inst2)
                        return

                self.fail('assertInstancesEqual fail.')

    def assertPathsEqual(self, paths1, paths2, ignore_host=False):
        """ Compare two lists of paths or paths for equality
            assert if they are not the same
        """
        if not isinstance(paths1, list):
            paths1 = [paths1]
        if not isinstance(paths2, list):
            paths2 = [paths2]
        self.assertEqual(len(paths1), len(paths2))

        for path1 in paths1:
            self.assertTrue(isinstance(path1, CIMInstanceName))
            if not self.path_in_list(path1, paths2, ignore_host=ignore_host):
                self.fail("Path Lists do not match. %s not in %s" %
                          (path1, paths2))
            else:
                for path2 in paths2:
                    if self.pathsEqual(path1, path2, ignore_host=ignore_host):
                        return
                self.fail('assertPathsEqual fail')


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
            self.assertInstanceNamesValid(name, namespace=self.namespace)

        # Call with explicit CIM namespace that exists

        self.cimcall(self.conn.EnumerateInstanceNames,
                     TEST_CLASS,
                     namespace=self.conn.default_namespace)

        # Call with explicit CIM namespace that does not exist

        try:
            self.cimcall(self.conn.EnumerateInstanceNames,
                         TEST_CLASS,
                         namespace='root/blah')
            self.fail('Expected CIMError')

        except CIMError as ce:
            if ce.args[0] != CIM_ERR_INVALID_NAMESPACE:
                raise

        # Call with explicit class name that does not exist

        try:
            self.cimcall(self.conn.EnumerateInstanceNames,
                         'Blah_Blah')
            self.fail('Expected CIMError')

        except CIMError as ce:
            if ce.args[0] != CIM_ERR_INVALID_CLASS:
                raise


class EnumerateInstances(ClientTest):
    """Test enumerateInstance variations against the server."""

    def display_response(self, instances):
        """Display the response instances as mof output."""
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
        """Simplest invocation of EnumerateInstances."""

        instances = self.cimcall(self.conn.EnumerateInstances,
                                 TEST_CLASS)

        self.assertTrue(len(instances) >= 1)

        self.assertInstancesValid(instances)

    def test_with_propertylist(self):
        """Add property list to simple invocation."""

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

        self.assertInstancesValid(instances, prop_count=2,
                                  property_list=prop_list)

        self.display_response(instances)

    def test_with_explicit_namespace(self):
        """Call with explicit CIM namespace that exists."""

        instances = self.cimcall(self.conn.EnumerateInstances,
                                 TEST_CLASS,
                                 namespace=self.conn.default_namespace)
        self.assertTrue(len(instances) >= 1)

        self.assertInstancesValid(instances)

    def test_with_localonly(self):
        """Test LocalOnly specifically.
        Open pegasus ignores this one so cannot really test."""

        instances = self.cimcall(self.conn.EnumerateInstances,
                                 TEST_CLASS,
                                 LocalOnly=True)

        self.assertInstancesValid(instances)

        self.display_response(instances)

        # Add specific response tests to the following
        instances = self.cimcall(self.conn.EnumerateInstances,
                                 TEST_CLASS,
                                 LocalOnly=False)

        self.assertInstancesValid(instances)

    def test_class_propertylist(self):
        """ Test with propertyList for getClass to confirm property in class.
        """
        property_list = [TEST_CLASS_PROPERTY2]

        cls = self.cimcall(self.conn.GetClass, TEST_CLASS,
                           PropertyList=property_list, LocalOnly=False)

        self.assertEqual(len(cls.properties), len(property_list))

        if self.verbose:
            for p in cls.properties.values():
                print('ClassPropertyName=%s' % p.name)

    def test_instance_propertylist(self):
        """ Test property list on enumerate instances."""

        property_list = [TEST_CLASS_PROPERTY2]

        # confirm property is in the class
        cls = self.cimcall(self.conn.GetClass, TEST_CLASS,
                           PropertyList=property_list, LocalOnly=False)
        cls_property_count = len(cls.properties)
        self.assertEqual(len(cls.properties), len(property_list))

        # Get instances of class
        instances = self.cimcall(self.conn.EnumerateInstances,
                                 TEST_CLASS,
                                 DeepInheritance=True,
                                 LocalOnly=False,
                                 PropertyList=property_list)

        self.assertInstancesValid(instances)

        for i in instances:
            self.assertTrue(len(i.properties) >= cls_property_count)

        inst_property_count = None

        # confirm same number of properties on each instance
        for inst in instances:
            if inst_property_count is None:
                inst_property_count = len(inst.properties)
            else:
                self.assertTrue(inst_property_count == len(inst.properties))

            if self.verbose:
                for p in inst.properties.values():
                    print('ClassPropertyName=%s' % p.name)

        if cls_property_count != inst_property_count:
            print('ERROR: classproperty_count %s != inst_property_count %s' %
                  (cls_property_count, inst_property_count))
            for p in cls.properties.values():
                print('ClassPropertyName=%s' % p.name)
            for p in instances[0].properties.values():
                print('InstancePropertyName=%s' % p.name)

        # TODO Apparently ks 5/16 Pegasus did not implement all properties
        # now in the class
        # self.assertTrue(property_count == inst_property_count)

    def test_instance_propertylist2(self):
        """ Test property list on enumerate instances."""

        property_list = ['PowerManagementCapibilities']

        cls = self.cimcall(self.conn.GetClass, TEST_CLASS,
                           PropertyList=property_list)
        cls_property_count = len(cls.properties)

        instances = self.cimcall(self.conn.EnumerateInstances,
                                 TEST_CLASS,
                                 DeepInheritance=True,
                                 LocalOnly=False,
                                 PropertyList=property_list)

        for i in instances:
            self.assertInstancesValid(i)
            self.assertTrue(len(i.properties) >= cls_property_count)

        inst_property_count = None
        for inst in instances:
            self.assertInstancesValid(inst)
            # confirm same number of properties on each instance
            if inst_property_count is None:
                inst_property_count = len(inst.properties)
            else:
                self.assertTrue(inst_property_count == len(inst.properties))

            if self.verbose:
                for p in inst.properties.values():
                    print('ClassPropertyName=%s' % p.name)

        if cls_property_count != inst_property_count:
            print('ERROR: classproperty_count %s != inst_property_count %s' %
                  (cls_property_count, inst_property_count))
            for p in cls.properties.values():
                print('ClassPropertyName=%s' % p.name)
            for p in instances[0].properties.values():
                print('InstancePropertyName=%s' % p.name)

        # TODO Apparently ks 5/16 Pegasus did not implement all properties
        # now in the class
        # self.assertTrue(property_count == inst_property_count)

    def test_instance_simple_propertylist(self):  # pylint: disable=invalid-name
        """Test property list with one property as a string."""

        property_list = TEST_CLASS_PROPERTY1

        # Get instances of class
        instances = self.cimcall(self.conn.EnumerateInstances,
                                 TEST_CLASS,
                                 DeepInheritance=True,
                                 LocalOnly=False,
                                 PropertyList=property_list)

        self.assertInstancesValid(instances)

        # confirm same number of properties on each instance
        for inst in instances:
            self.assertTrue(len(inst.properties) == 1)

    def test_deepinheritance(self):
        """
        Test with deep inheritance set false and then True. In this test we use
        CIM_ManagedElement so we get instances from multiple subclasses.
        Without deep inheritance, no instance should have number of properties
        gt number of properties in CIM_ManagedElement. If deep inheritance set,
        there should be instances with property count gt the number of
        properties in CIM_ManagedElement.
        """

        tst_class = 'CIM_ManagedElement'
        cls = self.cimcall(self.conn.GetClass, tst_class, LocalOnly=True)
        cls_property_count = len(cls.properties)

        instances = self.cimcall(self.conn.EnumerateInstances,
                                 tst_class,
                                 DeepInheritance=False,
                                 LocalOnly=True)
        self.assertInstancesValid(instances)

        for instance in instances:
            self.assertTrue(len(instance.properties) <= cls_property_count)

        # retest with DeepInheritance True
        instances = self.cimcall(self.conn.EnumerateInstances,
                                 tst_class,
                                 DeepInheritance=True,
                                 LocalOnly=True)

        self.assertInstancesValid(instances)

        max_prop_count = 0
        for instance in instances:
            max_prop_count = max(len(instance.properties), max_prop_count)
        self.assertTrue(max_prop_count > cls_property_count)

    def test_includequalifiers_true(self):
        """Test Include qualifiers. No detailed added test because
           most servers ignore this."""

        prop_list = [TEST_CLASS_PROPERTY1, TEST_CLASS_PROPERTY2]
        instances = self.cimcall(self.conn.EnumerateInstances,
                                 TEST_CLASS,
                                 PropertyList=prop_list,
                                 IncludeQualifiers=False)

        self.assertInstancesValid(instances, prop_count=2,
                                  property_list=prop_list)

    def test_includequalifiers_false(self):
        """ Can only test if works wnen set."""
        prop_list = [TEST_CLASS_PROPERTY1, TEST_CLASS_PROPERTY2]
        instances = self.cimcall(self.conn.EnumerateInstances,
                                 TEST_CLASS,
                                 PropertyList=prop_list,
                                 IncludeQualifiers=True)

        self.assertInstancesValid(instances, prop_count=2,
                                  property_list=prop_list)

        self.display_response(instances)

    def test_includeclassorigin(self):
        """test with includeclassorigin."""
        prop_list = [TEST_CLASS_PROPERTY1, TEST_CLASS_PROPERTY2]
        instances = self.cimcall(self.conn.EnumerateInstances,
                                 TEST_CLASS,
                                 PropertyList=prop_list,
                                 IncludeClassOrigin=True)

        self.assertInstancesValid(instances, prop_count=2,
                                  property_list=prop_list)

        # self.assertTrue(self.instance_classorigin(i, True))

        instances = self.cimcall(self.conn.EnumerateInstances,
                                 TEST_CLASS,
                                 PropertyList=prop_list,
                                 IncludeClassOrigin=False)
        for i in instances:
            self.assertInstancesValid(i, prop_count=2,
                                      property_list=prop_list)
            self.assertTrue(self.instance_classorigin(i, False))

    def test_nonexistent_namespace(self):
        """ Confirm correct error with nonexistent namespace."""

        try:
            self.cimcall(self.conn.EnumerateInstances,
                         TEST_CLASS,
                         namespace='root/blah')
            self.fail()      # should never get here

        except CIMError as ce:
            if ce.args[0] != CIM_ERR_INVALID_NAMESPACE:
                raise

    def test_nonexistent_classname(self):
        """ Confirm correct error with nonexistent classname."""
        try:
            self.cimcall(self.conn.EnumerateInstances, 'CIM_BlahBlah')
            self.fail()  # should never get here

        except CIMError as ce:
            if ce.args[0] != CIM_ERR_INVALID_CLASS:
                raise

    def test_invalid_request_parameter(self):
        """Should return error if invalid parameter."""
        try:
            self.cimcall(self.conn.EnumerateInstances, TEST_CLASS,
                         blablah=3)
            self.fail()  # Expecting exception

        except CIMError as ce:
            if ce.args[0] != CIM_ERR_NOT_SUPPORTED:
                raise


#
#   Test the Pull Operations
#


class PullEnumerateInstances(ClientTest):
    """
        Tests on OpenEnumerateInstances and corresponding PullInstancesWithPath
    """

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
        insts_pulled = result.instances

        self.assertInstancesValid(result.instances)

        while not result.eos:
            result = self.cimcall(
                self.conn.PullInstancesWithPath, result.context, 1)

            self.assertInstancesValid(result.instances)

            self.assertTrue(len(result.instances) <= 1)
            insts_pulled.extend(result.instances)

        self.assertInstancesValid(insts_pulled)

        insts_enum = self.cimcall(self.conn.EnumerateInstances, TEST_CLASS)

        self.assertInstancesValid(insts_enum)

        self.assertInstancesEqual(insts_pulled, insts_enum, ignore_host=True)

    def test_open_deepinheritance(self):
        """Simple OpenEnumerateInstances but with DeepInheritance set."""

        result = self.cimcall(self.conn.OpenEnumerateInstances,
                              TEST_CLASS,
                              MaxObjectCount=100,
                              DeepInheritance=True)
        insts_pulled = result.instances

        while not result.eos:
            result = self.cimcall(
                self.conn.PullInstancesWithPath, result.context, 100)
            insts_pulled.extend(result.instances)

        self.assertInstancesValid(insts_pulled)

        insts_enum = self.cimcall(self.conn.EnumerateInstances, TEST_CLASS)

        self.assertInstancesValid(insts_enum)

        self.assertInstancesEqual(insts_pulled, insts_enum, ignore_host=True)

    def test_open_includequalifiers(self):
        """Simple OpenEnumerateInstances but with IncludeQualifiers set."""

        result = self.cimcall(self.conn.OpenEnumerateInstances,
                              TEST_CLASS,
                              MaxObjectCount=100,
                              IncludeQualifiers=True)

        insts_pulled = result.instances

        while not result.eos:
            result = self.cimcall(
                self.conn.PullInstancesWithPath, result.context,
                MaxObjectCount=1)

            self.assertTrue(len(result.instances) <= 1)
            insts_pulled.extend(result.instances)

        self.assertInstancesValid(insts_pulled)

        insts_enum = self.cimcall(self.conn.EnumerateInstances, TEST_CLASS,
                                  IncludeQualifiers=True)

        self.assertInstancesValid(insts_enum)

        self.assertInstancesEqual(insts_pulled, insts_enum, ignore_host=True)

    def test_open_includeclassorigin(self):
        """Simple OpenEnumerateInstances but with DeepInheritance set."""

        result = self.cimcall(self.conn.OpenEnumerateInstances,
                              TEST_CLASS,
                              MaxObjectCount=100,
                              IncludeClassOrigin=True)

        insts_pulled = result.instances

        while not result.eos:
            result = self.cimcall(
                self.conn.PullInstancesWithPath, result.context, 1)

            self.assertTrue(len(result.instances) <= 1)
            insts_pulled.extend(result.instances)

        self.assertInstancesValid(insts_pulled)

        insts_enum = self.cimcall(self.conn.EnumerateInstances, TEST_CLASS)

        self.assertInstancesEqual(insts_pulled, insts_enum, ignore_host=True)

    def test_open_complete_with_ns(self):
        """Simple call that is complete with just the open and
           with explicit namespace.
        """

        result = self.cimcall(self.conn.OpenEnumerateInstances, TEST_CLASS,
                              MaxObjectCount=100,
                              namespace=TEST_CLASS_NAMESPACE)

        insts_pulled = result.instances

        while not result.eos:
            result = self.cimcall(
                self.conn.PullInstancesWithPath, result.context, 1)

            self.assertTrue(len(result.instances) <= 1)
            insts_pulled.extend(result.instances)

        self.assertInstancesValid(insts_pulled)

        insts_enum = self.cimcall(self.conn.EnumerateInstances, TEST_CLASS)

        self.assertInstancesEqual(insts_pulled, insts_enum, ignore_host=True)

    def test_zero_open(self):
        """ Test with default on open. Should return zero instances.
        """
        result = self.cimcall(self.conn.OpenEnumerateInstances, TEST_CLASS)

        self.assertTrue(result.eos is False)
        self.assertTrue(len(result.instances) == 0)

        insts_pulled = result.instances

        while not result.eos:
            result = self.cimcall(
                self.conn.PullInstancesWithPath, result.context, 100)
            self.assertTrue(len(result.instances) <= 1)
            insts_pulled.extend(result.instances)

        self.assertTrue(result.eos is True)

    def test_close_early(self):
        """"Close enumeration session after initial Open."""
        result = self.cimcall(self.conn.OpenEnumerateInstances, TEST_CLASS)

        self.assertFalse(result.eos)
        self.assertTrue(len(result.instances) == 0)

        self.cimcall(self.conn.CloseEnumeration, result.context)

        try:
            self.conn.PullInstancesWithPath(result.context, 10)
            self.fail('Expected CIMError')
        except CIMError as ce:
            if ce.args[0] != CIM_ERR_INVALID_ENUMERATION_CONTEXT:
                raise

    def test_close_invalid(self):
        """"Close enumeration session after complete."""
        result = self.cimcall(self.conn.OpenEnumerateInstances, TEST_CLASS,
                              MaxObjectCount=100)

        while not result.eos:
            result = self.cimcall(
                self.conn.PullInstancesWithPath, result.context, 100)

        try:
            self.cimcall(self.conn.CloseEnumeration, result.context)
            self.fail('Expected Value Error')

        except ValueError:
            pass

    def test_get_onebyone(self):
        """Get instances with MaxObjectCount = 1).
        This test is subject to differences between the pull and non
        pull sequence because it is getting live instances from the
        server and they may change between the requests.
        """

        result = self.cimcall(self.conn.OpenEnumerateInstances, TOP_CLASS,
                              MaxObjectCount=1)

        self.assertTrue(len(result.instances) <= 1)
        self.assertFalse(result.eos)
        insts_pulled = result.instances

        while not result.eos:
            result = self.cimcall(
                self.conn.PullInstancesWithPath, result.context,
                MaxObjectCount=1)
            self.assertTrue(len(result.instances) <= 1)
            insts_pulled.extend(result.instances)

        # get with EnumInstances
        insts_enum = self.cimcall(  # noqa: F841
            self.conn.EnumerateInstances, TOP_CLASS)

        # Because this is getting real instances, it does no always return
        # exactly the same count. In particular Pegasus includes a threads
        # provider.
        # In pegasus test tests things like threads that change all the
        # time so the totals will change slightly between requests
        self.assertTrue(abs(len(insts_pulled) - len(insts_enum)) < 10)

    def test_bad_namespace(self):
        """Call with explicit CIM namespace that does not exist."""

        try:
            self.cimcall(self.conn.OpenEnumerateInstances,
                         TEST_CLASS,
                         namespace='root/blah')
            self.fail('Expected CIMError')

        except CIMError as ce:
            if ce.args[0] != CIM_ERR_INVALID_NAMESPACE:
                raise

    def test_open_continueonerror(self):
        """ContinueOnError. Pegasus does not support this parameter."""

        try:
            self.cimcall(self.conn.OpenEnumerateInstances,
                         TEST_CLASS,
                         MaxObjectCount=100,
                         ContinueOnError=True)
            self.fail('Expected CIMError')

        except CIMError as ce:
            if ce.args[0] != CIM_ERR_NOT_SUPPORTED:
                raise

    # pylint: disable=invalid-name
    def test_open_invalid_filterquerylanguage(self):
        """Test invalid FilterQueryLanguage parameter."""
        try:
            self.cimcall(self.conn.OpenEnumerateInstances,
                         TEST_CLASS,
                         MaxObjectCount=100,
                         FilterQueryLanguage='BLAH')
            self.fail('Expected CIMError')
        # TODO ks 5/16 why does pegasus return this particular err.
        except CIMError as ce:
            self.assertEqual(ce.args[0], CIM_ERR_FAILED)

    # pylint: disable=invalid-name
    def test_open_invalid_filterquerylanguagewithfilter(self):
        """Test valid filter but invalid FilterQueryLanguage."""
        try:
            self.cimcall(self.conn.OpenEnumerateInstances,
                         TEST_CLASS,
                         MaxObjectCount=100,
                         FilterQueryLanguage='BLAH',
                         FilterQuery="p = 4")
            self.fail('Expected CIMError')

        except CIMError as ce:
            self.assertEqual(ce.args[0],
                             CIM_ERR_QUERY_LANGUAGE_NOT_SUPPORTED)

    def test_open_invalid_filterquery(self):
        """Test Invalid FilterQuery."""
        try:
            self.cimcall(self.conn.OpenEnumerateInstances,
                         TEST_CLASS,
                         MaxObjectCount=100,
                         FilterQueryLanguage='DMTF:FQL',
                         FilterQuery="blah")
            self.fail('Expected CIMError')

        except CIMError as ce:
            if ce.args[0] != CIM_ERR_INVALID_QUERY:
                raise

    def test_open_filter_returnsnone(self):
        """Test with filter that filters out all responses."""

        filter_statement = "%s = 'blah'" % TEST_CLASS_PROPERTY2
        result = self.cimcall(self.conn.OpenEnumerateInstances,
                              TEST_CLASS,
                              MaxObjectCount=100,
                              FilterQueryLanguage='DMTF:FQL',
                              FilterQuery=filter_statement)
        self.assertTrue(result.eos)
        self.assertTrue(len(result.instances) == 0)

    def test_open_timeoutset(self):
        """Test with timeout set. Just open and if not finished, close."""

        result = self.cimcall(self.conn.OpenEnumerateInstances,
                              TEST_CLASS,
                              MaxObjectCount=0,
                              OperationTimeout=10)

        if result.eos is False:
            self.cimcall(self.conn.CloseEnumeration, result.context)


class PullEnumerateInstancePaths(ClientTest):
    """ Tests on OpenEnumerateInstancePaths and PullInstancePaths sequences.
    """

    def test_open_complete(self):
        """Simplest invocation. Everything comes back in
           initial response with end-of-sequence == True
           Cannot depend on open returning anything because of
           server timing.
        """

        result = self.cimcall(self.conn.OpenEnumerateInstancePaths,
                              'Pywbem_person',
                              MaxObjectCount=100)

        paths_pulled = result.paths

        self.assertTrue(len(result.paths) <= 100)

        # Confirm that eos and context are mutually correct
        if result.eos:
            self.assertTrue(result.context is None)
        else:
            self.assertTrue(result.context)

        # loop to complete the enumeration session
        while not result.eos:
            result = self.cimcall(self.conn.PullInstancePaths,
                                  result.context, 1)

            self.assertTrue(len(result.paths) <= 1)
            paths_pulled.extend(result.paths)

        paths_enum = self.cimcall(self.conn.EnumerateInstanceNames,
                                  'Pywbem_person')

        self.assertEqual(len(paths_pulled), len(paths_enum))

    def test_open_complete_with_ns(self):
        """Simplest invocation. Everything comes back in
           initial response with end-of-sequence == True
        """

        result = self.cimcall(self.conn.OpenEnumerateInstancePaths,
                              TEST_CLASS, namespace=TEST_CLASS_NAMESPACE,
                              MaxObjectCount=100)

        paths_pulled = result.paths

        self.assertTrue(len(result.paths) <= 100)

        if result.eos:
            self.assertTrue(result.context is None)
        else:
            self.assertTrue(result.context)

        while not result.eos:
            result = self.cimcall(self.conn.PullInstancePaths,
                                  result.context, 1)

            self.assertTrue(len(result.paths) <= 1)
            paths_pulled.extend(result.paths)

        # get with enum to confirm
        paths_enum = self.cimcall(self.conn.EnumerateInstanceNames, TEST_CLASS)

        if (len(paths_pulled) != len(paths_enum)):
            print('ERROR result.paths len %s ne paths_enum len %s' %
                  (len(paths_pulled), len(paths_enum)))

        self.assertTrue(len(paths_pulled) == len(paths_enum))

    def test_bad_namespace(self):
        """Call with explicit CIM namespace that does not exist."""

        try:
            self.cimcall(self.conn.OpenEnumerateInstancePaths,
                         TEST_CLASS,
                         namespace='root/blah')
            self.fail('Expected CIMError')

        except CIMError as ce:
            if ce.args[0] != CIM_ERR_INVALID_NAMESPACE:
                raise

    def test_zero_open(self):
        """ Test for request with MaxObjectCount default on open. This
            must return zero objects on response.
        """
        result = self.cimcall(self.conn.OpenEnumerateInstancePaths, TEST_CLASS)

        self.assertFalse(result.eos)

        # Pull the remainder of the paths
        result = self.cimcall(self.conn.PullInstancePaths, result.context, 100)

        self.assertTrue(result.eos)

    def test_close_early(self):
        """"Close enumeration session after initial Open."""

        # open requesting zero instances
        result = self.cimcall(self.conn.OpenEnumerateInstancePaths, TEST_CLASS)

        self.assertFalse(result.eos)
        self.assertTrue(len(result.paths) == 0)

        self.cimcall(self.conn.CloseEnumeration, result.context)

        try:
            self.conn.PullInstancePaths(result.context, 10)
            self.fail('Expected CIMError')
        except CIMError as ce:
            if ce.args[0] != CIM_ERR_INVALID_ENUMERATION_CONTEXT:
                raise

    def show_differences(self, paths1, paths2):
        if len(paths1) > len(paths2):
            print([path for path in paths1 if path not in paths2])
        # paths2 ge paths1
        else:
            print([path for path in paths2 if path not in paths1])

    # TODO this only returns single instance.
    def test_get_onebyone(self):
        """Enumerate instances with MaxObjectCount = 1)."""

        result = self.cimcall(
            self.conn.OpenEnumerateInstancePaths, TEST_CLASS,
            MaxObjectCount=1)

        self.assertTrue(len(result.paths) <= 1)

        paths_pulled = result.paths

        while not result.eos:
            result = self.cimcall(self.conn.PullInstancePaths,
                                  result.context, 1)

            self.assertTrue(len(result.paths) <= 1)
            paths_pulled.extend(result.paths)

        # get with EnumInstanceNames and compare returns
        paths_enum = self.cimcall(self.conn.EnumerateInstanceNames,
                                  TEST_CLASS)

        # This test does NOT always deliver the same number of instances.
        # Therefore we do an initial test with a range and if that range is
        # to large, fail the test.  If the results are equal, we to the
        # compare
        diff = abs(len(paths_pulled) - len(paths_enum))
        if diff == 0:
            self.assertPathsEqual(paths_pulled, paths_enum, ignore_host=True)
        elif paths_pulled / diff < 10:
            print('Return diff count %s of total %s ignored' %
                  (diff, paths_pulled))
        else:
            self.fail('Issues with pull vs non-pull responses')


class PullReferences(ClientTest):
    """Test OpenReferences and PullInstancesWithPath."""

    def test_one_instance(self):
        # Get one valid instance name
        inst_names = self.cimcall(self.conn.EnumerateInstanceNames,
                                  TEST_CLASS)
        self.assertTrue(len(inst_names) >= 1)
        inst_name = inst_names[0]  # Pick the first returned instance

        result = self.cimcall(self.conn.OpenReferenceInstances,
                              inst_name,
                              MaxObjectCount=0)

        insts_pulled = result.instances

        while not result.eos:
            result = self.cimcall(
                self.conn.PullInstancesWithPath, result.context, 1)

            self.assertTrue(len(result.instances) <= 1)
            insts_pulled.extend(result.instances)

        for inst in insts_pulled:
            self.assertTrue(isinstance(inst, CIMInstanceName))
            self.assertTrue(len(inst.namespace) > 0)

        insts_enum = self.cimcall(self.conn.References, inst_name)

        for i in insts_pulled:
            self.assertTrue(isinstance(i, CIMInstance))
            self.assertTrue(isinstance(i.path, CIMInstanceName))

            # TODO: For now, disabled test for class name of associated insts.
            # self.assertTrue(i.classname == 'TBD')

            self.assertTrue(i.path.namespace is not None)
            self.assertTrue(i.path.host is not None)

        self.assertInstancesEqual(insts_pulled, insts_enum)

    def test_pywbem_person_noparams(self):
        """
        Test OpenReferencesWithPath PyWBEM_Person class
        and no associator filter parameters
        """
        if not self.pywbem_person_class_exists():
            return

        inst_paths = self.cimcall(self.conn.EnumerateInstanceNames,
                                  PYWBEM_PERSON_CLASS)
        self.assertTrue(len(inst_paths) >= 1)

        # for each returned instance, execute  test sequence to get
        # all instances
        for path in inst_paths:
            result = self.cimcall(self.conn.OpenReferenceInstances,
                                  path,
                                  MaxObjectCount=100)

            insts_pulled = result.instances

            while not result.eos:
                result = self.cimcall(
                    self.conn.PullInstancesWithPath, result.context, 1)
                self.assertTrue(len(result.instances) <= 1)
                insts_pulled.extend(result.instances)

            # test the returned insts_pulled
            self.assertTrue(len(insts_pulled) > 0,
                            'PyWBEM_Person expects pulled instances')
            self.assertInstancesValid(insts_pulled)
            for inst in insts_pulled:
                self.assertEqual(inst.classname,
                                 PYWBEM_MEMBEROFPERSONCOLLECTION)

    @unittest.skipIf(SKIP_LONGRUNNING_TEST, 'skip test against all instances')
    def test_all_instances_in_ns(self):
        """Simplest invocation. Everything comes back in
           initial response with end-of-sequence == True
        """
        # get all instances under CIM_ManagedElement
        paths = self.cimcall(self.conn.EnumerateInstanceNames,
                             'CIM_ManagedElement')

        # Do for all instances returned from EnumerateInstanceNames
        for pathi in paths:
            result = self.cimcall(self.conn.OpenReferenceInstances,
                                  pathi,
                                  MaxObjectCount=100)

            insts_pulled = result.instances

            while not result.eos:
                result = self.cimcall(
                    self.conn.PullInstancesWithPath, result.context, 1)

                self.assertTrue(len(result.instances) <= 1)
                insts_pulled.extend(result.instances)

            self.assertInstancesValid(result.instances)

            insts_enum = self.cimcall(self.conn.References, pathi)
            if insts_enum:
                print('References %s count %s' % (pathi, len(insts_enum)))
            self.assertTrue(len(insts_pulled) == len(insts_enum))

            # TODO ks 5/30 2016 add tests here
            # Do this as a loop for all instances above.

    def test_invalid_instance_name(self):
        """Test with name that is invalid class Expects exception"""
        foo_path = CIMInstanceName('CIM_Foo')

        try:
            self.cimcall(self.conn.OpenReferenceInstances,
                         foo_path, MaxObjectCount=100)
            self.fail("Expected exception response")

        except CIMError as ce:
            if ce.args[0] != CIM_ERR_INVALID_PARAMETER:
                raise


class PullReferencePaths(ClientTest):
    """Tests on OpenReferencePaths and PullInstancePaths."""

    def test_one_instance(self):

        inst_names = self.cimcall(self.conn.EnumerateInstanceNames,
                                  TEST_CLASS)
        self.assertTrue(len(inst_names) >= 1)
        inst_name = inst_names[0]  # Pick the first returned instance

        result = self.cimcall(self.conn.OpenReferenceInstancePaths,
                              inst_name,
                              MaxObjectCount=0)

        paths_pulled = result.paths

        while not result.eos:
            result = self.cimcall(
                self.conn.PullInstancePaths, result.context, 1)

            self.assertTrue(len(result.paths) <= 1)
            paths_pulled.extend(result.paths)

        for path in result.paths:
            self.assertTrue(isinstance(path, CIMInstanceName))
            self.assertTrue(len(path.namespace) > 0)

        paths_enum = self.cimcall(self.conn.ReferenceNames, inst_name)

        for i in paths_enum:
            self.assertTrue(isinstance(i, CIMInstanceName))

            # TODO: For now, disabled test for class name of associated insts.
            # self.assertTrue(i.classname == 'TBD')

            self.assertTrue(i.namespace is not None)
            self.assertTrue(i.host is not None)

        self.assertPathsEqual(paths_pulled, paths_enum)

    def test_pywbem_person_noparams(self):
        """
        Test OpenReferencesPaths PyWBEM_Person class
        and no associator filter parameters
        """
        if not self.pywbem_person_class_exists():
            return

        inst_paths = self.cimcall(self.conn.EnumerateInstanceNames,
                                  PYWBEM_PERSON_CLASS)
        self.assertTrue(len(inst_paths) >= 1)

        # for each returned instance, execute  test sequence to get
        # all instances
        for path in inst_paths:
            result = self.cimcall(self.conn.OpenReferenceInstancePaths,
                                  path,
                                  MaxObjectCount=100)

            paths_pulled = result.paths

            while not result.eos:
                result = self.cimcall(
                    self.conn.PullInstancePaths, result.context, 1)
                self.assertTrue(len(result.paths) <= 1)
                paths_pulled.extend(result.paths)

            # test the returned paths_pulled
            self.assertTrue(len(paths_pulled) > 0)
            self.assertPathsValid(paths_pulled)
            for path_ in paths_pulled:
                self.assertEqual(path_.classname,
                                 PYWBEM_MEMBEROFPERSONCOLLECTION)

    @unittest.skipIf(SKIP_LONGRUNNING_TEST, 'skip long test for all instances')
    def test_all_instances_in_ns(self):
        """
            Simplest invocation. Execute and compare with results
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
                self.assertInstanceNamesValid(path)

            paths = result.paths

            while not result.eos:
                result = self.cimcall(self.conn.PullInstancePaths,
                                      result.context, 1)

                for path in result.paths:
                    self.assertInstanceNamesValid(path)

                paths.extend(result.paths)

            paths_enum = self.cimcall(self.conn.ReferenceNames, pathi)
            if paths_enum:
                print('References %s count %s' % (pathi, len(paths_enum)))
            self.assertTrue(len(paths) == len(paths_enum))

            # TODO ks 5/30 2016 add tests here
            # Do this as a loop for all instances above.


class PullAssociators(ClientTest):
    """Test the OpenAssociators and corresponding pull."""

    def test_one_instance(self):
        # Call on named instance

        inst_names = self.cimcall(self.conn.EnumerateInstanceNames,
                                  TEST_CLASS)
        self.assertTrue(len(inst_names) >= 1)
        inst_name = inst_names[0]  # Pick the first returned instance

        result = self.cimcall(self.conn.OpenAssociatorInstances,
                              inst_name,
                              MaxObjectCount=0)

        insts_pulled = result.instances

        while not result.eos:
            result = self.cimcall(
                self.conn.PullInstancesWithPath, result.context, 1)

            self.assertTrue(len(result.instances) <= 1)
            insts_pulled.extend(result.instances)

        for inst in insts_pulled:
            self.assertTrue(isinstance(inst, CIMInstanceName))
            self.assertTrue(len(inst.namespace) > 0)

        insts_enum = self.cimcall(self.conn.Associators, inst_name)

        for i in insts_enum:
            self.assertTrue(isinstance(i, CIMInstance))
            self.assertTrue(isinstance(i.path, CIMInstanceName))

            # TODO: For now, disabled test for class name of associated insts.
            # self.assertTrue(i.classname == 'TBD')

            self.assertTrue(i.path.namespace is not None)
            self.assertTrue(i.path.host is not None)

        self.assertInstancesEqual(insts_pulled, insts_enum)

    def test_pywbem_person_noparams(self):
        """
        Test associator with PyWBEM_Person class and no associator
        filter parameters
        """
        if not self.pywbem_person_class_exists():
            return
        inst_names = self.cimcall(self.conn.EnumerateInstanceNames,
                                  PYWBEM_PERSON_CLASS)
        self.assertTrue(len(inst_names) >= 1)

        for name in inst_names:
            result = self.cimcall(self.conn.OpenAssociatorInstances,
                                  name,
                                  MaxObjectCount=100)

            insts_pulled = result.instances

            while not result.eos:
                result = self.cimcall(
                    self.conn.PullInstancesWithPath, result.context, 1)
                self.assertTrue(len(result.instances) <= 1)
                insts_pulled.extend(result.instances)

        # TODO ks This not right. we are going back to associators
        for path in inst_names:
            ref_insts = self.cimcall(
                self.conn.Associators, path)
            self.assertTrue(len(ref_insts) > 0)
            self.assertInstancesValid(ref_insts)
            for inst in ref_insts:
                self.assertEqual(inst.classname, 'PyWBEM_PersonCollection')

    @unittest.skipIf(SKIP_LONGRUNNING_TEST, 'skip long  all instances test')
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

            insts_pulled = result.instances

            while not result.eos:
                result = self.cimcall(
                    self.conn.PullInstancesWithPath, result.context, 1)

                self.assertTrue(len(result.instances) <= 1)
                insts_pulled.extend(result.instances)

            for inst in insts_pulled:
                self.assertTrue(isinstance(inst, CIMInstanceName))
                self.assertTrue(len(inst.namespace) > 0)

            insts_enum = self.cimcall(self.conn.References, pathi)

            if insts_enum:
                print('Associators %s count %s' % (insts_pulled,
                                                   len(insts_enum)))
            self.assertTrue(len(insts_pulled) == len(insts_enum))
            # TODO ks 5/30 2016 add tests here
            # Do this as a loop for all instances above.

    def test_invalid_instance_name(self):
        """Test with name that is invalid class."""

        foo_path = CIMInstanceName('CIM_Foo')

        try:
            self.cimcall(self.conn.OpenAssociatorInstances,
                         foo_path,
                         MaxObjectCount=100)
            self.fail("Expected exception response")

        except CIMError as ce:
            if ce.args[0] != CIM_ERR_INVALID_PARAMETER:
                raise


class PullAssociatorPaths(ClientTest):
    """Test OpenAssociatorPaths and corresponding PullInstancePaths."""

    def test_one_instance(self):

        inst_names = self.cimcall(self.conn.EnumerateInstanceNames,
                                  TEST_CLASS)
        self.assertTrue(len(inst_names) >= 1)
        inst_name = inst_names[0]  # Pick the first returned instance

        result = self.cimcall(self.conn.OpenAssociatorInstancePaths,
                              inst_name,
                              MaxObjectCount=0)

        paths_pulled = result.paths

        while not result.eos:
            result = self.cimcall(
                self.conn.PullInstancePaths, result.context, 1)

            self.assertTrue(len(result.paths) <= 1)
            paths_pulled.extend(result.paths)

        for path in paths_pulled:
            self.assertTrue(isinstance(path, CIMInstanceName))
            self.assertTrue(len(path.namespace) > 0)

        # get same through associationNames and compare
        paths_enum = self.cimcall(self.conn.AssociatorNames, inst_name)

        for i in paths_enum:
            self.assertTrue(isinstance(i, CIMInstanceName))

            # TODO: For now, disabled test for class name of associated insts.
            # self.assertTrue(i.classname == 'TBD')

            self.assertTrue(i.namespace is not None)
            self.assertTrue(i.host is not None)

        self.assertPathsEqual(paths_pulled, paths_enum)

    def test_pywbem_person_noparams(self):
        """
        Test associator with PyWBEM_Person class and no associator
        filter parameters
        """
        if not self.pywbem_person_class_exists():
            return

        inst_names = self.cimcall(self.conn.EnumerateInstanceNames,
                                  PYWBEM_PERSON_CLASS)
        self.assertTrue(len(inst_names) >= 1)

        for name in inst_names:
            result = self.cimcall(self.conn.OpenAssociatorInstancePaths,
                                  name,
                                  MaxObjectCount=100)

            paths_pulled = result.paths

            while not result.eos:
                result = self.cimcall(
                    self.conn.PullInstancePaths, result.context, 1)
                self.assertTrue(len(result.paths) <= 1)
                paths_pulled.extend(result.paths)

        for path in inst_names:
            ref_insts = self.cimcall(
                self.conn.Associators, path)
            self.assertTrue(len(ref_insts) > 0)
            self.assertInstancesValid(ref_insts)
            for inst in ref_insts:
                self.assertEqual(inst.classname, 'PyWBEM_PersonCollection')

    @unittest.skipIf(SKIP_LONGRUNNING_TEST, 'skip long test')
    def test_all_instances_in_ns(self):
        """Simplest invocation. Everything comes back in
           initial response with end-of-sequence == True. Compare results
           of complete pull sequence and original associators operation.
           This test takes a long time because it tests every class in
           the namespace.
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
                self.assertInstanceNamesValid(path)

            paths_pulled = result.paths

            while not result.eos:
                result = self.cimcall(self.conn.PullInstancePaths,
                                      result.context, 1)
                for path in result.paths:
                    self.assertInstanceNamesValid(path)
                paths_pulled.extend(result.paths)

            paths_enum = self.cimcall(self.conn.AssociatorNames, pathi)
            if paths_enum:
                print('Associator Names %s count %s' % (pathi, len(paths_enum)))
            self.assertEqual(len(paths_pulled), len(paths_enum))
            # TODO ks 5/30 2016 add tests here
            # Do this as a loop for all instances above.


class PullQueryInstances(ClientTest):
    """Test of openexecquery and pullinstances."""

    def test_simple_pull_sequence(self):
        try:

            # Simplest invocation

            result = self.cimcall(self.conn.OpenQueryInstances,
                                  'WQL',
                                  'Select * from %s' % TEST_CLASS,
                                  MaxObjectCount=100)

            for i in result.instances:
                self.assertTrue(isinstance(i, CIMInstance))

            insts_pulled = result.instances
            eos = result.eos

            while eos is False:
                op_result = self.cimcall(self.conn.PullInstances,
                                         result.context, 100)
                insts_pulled.extend(result.instances)
                eos = op_result.eos

            self.assertInstancesValid(insts_pulled, includes_path=False)

        except CIMError as ce:
            if ce.args[0] == CIM_ERR_NOT_SUPPORTED:
                raise AssertionError(
                    "CIM_ERR_NOT_SUPPORTED: The WBEM server doesn't"
                    " support OpenQueryInstances for this query")
            if ce.args[0] == CIM_ERR_QUERY_LANGUAGE_NOT_SUPPORTED:
                raise AssertionError(
                    "CIM_ERR_QUERY_LANGUAGE_NOT_SUPPORTED: The WBEM"
                    " server doesn't support WQL for ExecQuery")

            raise

    def test_zeroopen_pull_sequence(self):
        try:

            # Simplest invocation

            result = self.cimcall(self.conn.OpenQueryInstances,
                                  'WQL',
                                  'Select * from %s' % TEST_CLASS)

            for i in result.instances:
                self.assertTrue(isinstance(i, CIMInstance))
            insts_pulled = result.instances
            eos = result.eos

            while eos is False:
                op_result = self.cimcall(self.conn.PullInstances,
                                         result.context, 100)
                insts_pulled.extend(result.instances)
                eos = op_result.eos

        except CIMError as ce:
            if ce.args[0] == CIM_ERR_NOT_SUPPORTED:
                raise AssertionError(
                    "CIM_ERR_NOT_SUPPORTED: The WBEM server doesn't"
                    " support OpenQueryInstances for this query")
            if ce.args[0] == CIM_ERR_QUERY_LANGUAGE_NOT_SUPPORTED:
                raise AssertionError(
                    "CIM_ERR_QUERY_LANGUAGE_NOT_SUPPORTED: The WBEM"
                    " server doesn't support WQL for ExecQuery")

            raise


class ExecQuery(ClientTest):

    def test_simple(self):
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
                    "CIM_ERR_NOT_SUPPORTED: The WBEM server doesn't"
                    " support ExecQuery for this query")
            if ce.args[0] == CIM_ERR_QUERY_LANGUAGE_NOT_SUPPORTED:
                raise AssertionError(
                    "CIM_ERR_QUERY_LANGUAGE_NOT_SUPPORTED: The WBEM"
                    " server doesn't support WQL for ExecQuery")

            raise

    def test_namespace_error(self):
        """Call with explicit CIM namespace that does not exist."""

        try:

            self.cimcall(self.conn.ExecQuery,
                         'WQL',
                         'Select * from %s' % TEST_CLASS,
                         namespace='root/blah')

        except CIMError as ce:
            if ce.args[0] != CIM_ERR_INVALID_NAMESPACE:
                raise

    def test_invalid_querylang(self):
        """Test execquery with invalid query_lang parameter."""
        try:

            self.cimcall(self.conn.ExecQuery,
                         'wql',
                         'Select * from %s' % TEST_CLASS,
                         namespace='root/cimv2')

        except CIMError as ce:
            if ce.args[0] != CIM_ERR_QUERY_LANGUAGE_NOT_SUPPORTED:
                raise

    def test_invalid_query(self):
        """Test with invalid query syntax."""
        try:

            self.cimcall(self.conn.ExecQuery,
                         'WQL',
                         'SelectSLOP * from %s' % TEST_CLASS,
                         namespace='root/cimv2')

        except CIMError as ce:
            if ce.args[0] != CIM_ERR_INVALID_QUERY:
                raise


class GetInstance(ClientTest):
    """Test getclass operation"""
    def test_various(self):

        inst_names = self.cimcall(self.conn.EnumerateInstanceNames,
                                  TEST_CLASS)
        self.assertTrue(len(inst_names) >= 1)
        name = inst_names[0]  # Pick the first returned instance

        # Simple invocation

        obj = self.cimcall(self.conn.GetInstance,
                           name)

        self.assertTrue(isinstance(obj, CIMInstance))
        self.assertTrue(isinstance(obj.path, CIMInstanceName))

        # Call with propertylist and localonly=False
        obj = self.cimcall(self.conn.GetInstance,
                           name,
                           PropertyList=[TEST_CLASS_PROPERTY1],
                           LocalOnly=False)

        self.assertTrue(isinstance(obj, CIMInstance))
        self.assertTrue(isinstance(obj.path, CIMInstanceName))
        self.assertTrue(obj.path.namespace == self.namespace)
        self.assertTrue(len(obj.properties) == 1)

        # Call with propertylist (2 properties)

        obj = self.cimcall(self.conn.GetInstance,
                           name,
                           PropertyList=[TEST_CLASS_PROPERTY1,
                                         TEST_CLASS_PROPERTY2],
                           LocalOnly=False)

        self.assertTrue(isinstance(obj, CIMInstance))
        self.assertTrue(isinstance(obj.path, CIMInstanceName))
        self.assertTrue(obj.path.namespace == self.namespace)
        self.assertTrue(len(obj.properties) == 2)

        # Call with property list empty

        obj = self.cimcall(self.conn.GetInstance,
                           name,
                           PropertyList=[],
                           LocalOnly=False)

        self.assertTrue(isinstance(obj, CIMInstance))
        self.assertTrue(isinstance(obj.path, CIMInstanceName))
        self.assertTrue(obj.path.namespace == self.namespace)
        self.assertTrue(len(obj.properties) == 0)

        # call with  IncludeQualifiers

        obj = self.cimcall(self.conn.GetInstance,
                           name,
                           IncludeQualifiers=True)

        self.assertTrue(isinstance(obj, CIMInstance))
        self.assertTrue(isinstance(obj.path, CIMInstanceName))
        self.assertTrue(obj.path.namespace == self.namespace)

        # Call with IncludeClassOrigin

        obj = self.cimcall(self.conn.GetInstance,
                           name,
                           IncludeClassOrigin=True)

        self.assertTrue(isinstance(obj, CIMInstance))
        self.assertTrue(isinstance(obj.path, CIMInstanceName))
        self.assertTrue(obj.path.namespace == self.namespace)
        # confirm results

        # Call with IncludeQualifiers and IncludeClassOrigin

        obj = self.cimcall(self.conn.GetInstance,
                           name,
                           IncludeClassOrigin=True,
                           IncludeQualifiers=True)

        self.assertTrue(isinstance(obj, CIMInstance))
        self.assertTrue(isinstance(obj.path, CIMInstanceName))
        self.assertTrue(obj.path.namespace == self.namespace)

        # Call with LocalOnly

        obj = self.cimcall(self.conn.GetInstance,
                           name,
                           LocalOnly=True)

        self.assertTrue(isinstance(obj, CIMInstance))
        self.assertTrue(isinstance(obj.path, CIMInstanceName))
        self.assertTrue(obj.path.namespace == self.namespace)

        # Call with invalid namespace path

        invalid_name = name.copy()
        invalid_name.namespace = 'blahblahblah'

        # Call with invalid Class Name

        try:
            self.cimcall(self.conn.GetInstance, invalid_name)

        except CIMError as ce:
            if ce.args[0] != CIM_ERR_INVALID_NAMESPACE:
                raise

    def test_propertylist_tuple(self):
        """ Test property list as tuple instead of list."""

        inst_names = self.cimcall(self.conn.EnumerateInstanceNames,
                                  TEST_CLASS)
        self.assertTrue(len(inst_names) >= 1)
        name = inst_names[0]  # Pick the first returned instance

        obj = self.cimcall(self.conn.GetInstance,
                           name,
                           PropertyList=(TEST_CLASS_PROPERTY1,
                                         TEST_CLASS_PROPERTY2),
                           LocalOnly=False)
        self.assertTrue(isinstance(obj, CIMInstance))
        self.assertTrue(isinstance(obj.path, CIMInstanceName))
        self.assertTrue(obj.path.namespace == self.namespace)
        self.assertTrue(len(obj.properties) == 2)

        obj = self.cimcall(self.conn.GetInstance,
                           name,
                           PropertyList=(TEST_CLASS_PROPERTY1,),
                           LocalOnly=False)
        self.assertTrue(isinstance(obj, CIMInstance))
        self.assertTrue(isinstance(obj.path, CIMInstanceName))
        self.assertTrue(obj.path.namespace == self.namespace)
        self.assertTrue(len(obj.properties) == 1)

        # test with single property.
        obj = self.cimcall(self.conn.GetInstance,
                           name,
                           PropertyList=TEST_CLASS_PROPERTY1,
                           LocalOnly=False)
        self.assertTrue(isinstance(obj, CIMInstance))
        self.assertTrue(isinstance(obj.path, CIMInstanceName))
        self.assertTrue(obj.path.namespace == self.namespace)
        self.assertTrue(len(obj.properties) == 1)


class CreateInstance(ClientTest):
    """Test the CreateInstance Operations"""

    def test_pywbem_person_create(self):
        """Test Creation of an instance of PyWBEM_Person."""
        if not self.pywbem_person_class_exists():
            return

        # Note: We do not use the variables that name the class here
        instance = CIMInstance(
            'PyWBEM_Person',
            {'CreationClassName': 'PyWBEM_Person',
             'Name': 'run_cimoperations_test'},
            path=CIMInstanceName('PyWBEM_Person',
                                 {'CreationClassName': 'PyWBEM_Person',
                                  'Name': 'run_cimoperations_test'}))

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

        # Should fail.  Insance already deleted
        try:
            self.cimcall(self.conn.GetInstance(instance.path))

        except CIMError as arg:
            if arg == CIM_ERR_NOT_FOUND:
                pass

    def test_pywbem_AllTypes(self):  # pylint: disable=invalid-name
        """Test Creation of an instance of PyWBEM_AllTypes."""
        if not self.pywbem_person_class_exists():
            return

        # Note: We do not use the variables that name the class here
        dt = datetime(year=2016, month=3, day=31, hour=19, minute=30,
                      second=40, microsecond=654321,
                      tzinfo=MinutesFromUTC(120))
        td = timedelta(days=1234, seconds=(11 * 3600 + 22 * 60 + 33),
                       microseconds=654321)

        instance_id = 'run_cimoperations_test1'

        tst_instance = CIMInstance(
            'PyWBEM_AllTypes',
            properties=[
                ('InstanceId', instance_id),
                ('scalBool', True),
                ('scalUint8', Uint8(42)),
                ('scalSint8', Sint8(-42)),
                ('scalUint16', Uint16(4216)),
                ('scalSint16', Sint16(-4216)),
                ('scalUint32', Uint32(4232)),
                ('scalSint32', Sint32(-4232)),
                ('scalUint64', Uint64(99999)),
                ('scalSint64', Sint64(-99999)),
                ('scalReal32', Real32(42.0)),
                ('scalReal64', Real64(42.64)),
                ('scalString', 'ham'),
                ('scalDateTime', dt),
                ('scalTimeDelta', td),
                ('arrayBool', [False, True]),
                ('arrayUint8', [Uint8(x) for x in [0, 1, 44, 127]]),
                ('arraySint8', [Sint8(x) for x in [0, -1, 44, 127]]),
                ('arrayUint16', [Sint16(x) for x in [0, -1, 44, 127]]),
                ('arraySint16', [Sint16(42), Sint16(-99)]),
                ('arrayUint32', [Uint32(42), Uint32(99)]),
                ('arraySint32', [Sint32(42), Sint32(-99)]),
                ('arrayUint64', [Uint64(42), Uint64(999999)]),
                ('arraySint64', [Sint64(4222222), Sint64(-999999)]),
                ('arrayReal32', [Real32(42.0), Real32(4442.9)]),
                ('arrayReal64', [Real64(42.0), Real64(4442.9)]),
                ('arrayString', ['ham', u'H\u00E4m']),  # U+00E4=lower a umlaut
                ('arrayDateTime', [dt, dt]),
                ('arrayTimeDelta', [td, td]),
            ])

        tst_instance.path = CIMInstanceName(
            'PyWBEM_AllTypes', {'InstanceId': instance_id})

        # Delete if already exists (previous test incomplete)
        try:
            self.cimcall(self.conn.DeleteInstance, tst_instance.path)
        except CIMError as ce:
            if ce.args[0] == CIM_ERR_NOT_FOUND:
                pass

        # Create instance and get/compare then delete if the create was
        # successful
        try:
            real_inst_path = self.cimcall(self.conn.CreateInstance,
                                          tst_instance)
        except CIMError as ce:
            if ce.args[0] == CIM_ERR_INVALID_CLASS:
                # does not support creation
                pass
        else:
            self.assertTrue(isinstance(real_inst_path, CIMInstanceName))
            self.assertTrue(len(real_inst_path.namespace) > 0)

            got_instance = self.cimcall(self.conn.GetInstance,
                                        tst_instance.path)

            self.assertEqual(tst_instance, got_instance)

            result = self.cimcall(self.conn.DeleteInstance,
                                  real_inst_path)

            self.assertTrue(result is None)

        # Should fail.  Instance already deleted
        try:
            self.cimcall(self.conn.GetInstance(tst_instance.path))

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

    def test_class_level(self):
        """Invoke method on a class name"""
        # Invoke on classname

        try:
            self.cimcall(
                self.conn.InvokeMethod,
                'FooMethod',
                TEST_CLASS)

        except CIMError as ce:
            if ce.args[0] != CIM_ERR_METHOD_NOT_AVAILABLE:
                raise

    def test_instance_level(self):
        """Invoke on an InstanceName"""

        inst_names = self.cimcall(self.conn.EnumerateInstanceNames,
                                  TEST_CLASS)
        self.assertTrue(len(inst_names) >= 1)
        name = inst_names[0]  # Pick the first returned instance

        try:

            self.cimcall(self.conn.InvokeMethod,
                         'FooMethod',
                         name)

        except CIMError as ce:
            if ce.args[0] not in (CIM_ERR_METHOD_NOT_AVAILABLE,
                                  CIM_ERR_METHOD_NOT_FOUND):
                raise

    def test_remote_instance_name(self):
        """Test remote instance name"""
        inst_names = self.cimcall(self.conn.EnumerateInstanceNames,
                                  TEST_CLASS)
        self.assertTrue(len(inst_names) >= 1)
        name = inst_names[0]  # Pick the first returned instance
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

    def test_all_param_types(self):
        """Call invoke method with all possible parameter types"""
        inst_names = self.cimcall(self.conn.EnumerateInstanceNames,
                                  TEST_CLASS)
        self.assertTrue(len(inst_names) >= 1)
        name = inst_names[0]  # Pick the first returned instance
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

    def test_one_param_types(self):
        """Call invoke method with all possible parameter types"""
        inst_names = self.cimcall(self.conn.EnumerateInstanceNames,
                                  TEST_CLASS)
        self.assertTrue(len(inst_names) >= 1)
        name = inst_names[0]  # Pick the first returned instance
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

    def test_non_empty_arrays(self):
        """Call with non-empty arrays"""
        inst_names = self.cimcall(self.conn.EnumerateInstanceNames,
                                  TEST_CLASS)
        self.assertTrue(len(inst_names) >= 1)
        name = inst_names[0]  # Pick the first returned instance
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

    def test_new_params_arg(self):
        """Call with new Params arg"""

        try:
            self.cimcall(self.conn.InvokeMethod,
                         'FooMethod',
                         TEST_CLASS,
                         [('Spam', Uint16(1)), ('Ham', Uint16(2))],  # Params
                         Drink=Uint16(3),  # begin of **params
                         Beer=Uint16(4))
        except CIMError as ce:
            if ce.args[0] != CIM_ERR_METHOD_NOT_AVAILABLE:
                raise

    # TODO specalize this one for OpenPegasus
    def test_working_method(self):
        """OpenPegasus specific method that works"""
        test_class = 'Test_IndicationProviderClass'
        test_class_namespace = 'test/TestProvider'
        class_name = CIMClassName(test_class,
                                  namespace=test_class_namespace)

        result = self.cimcall(self.conn.InvokeMethod,
                              "SendTestIndicationsCount",
                              class_name,
                              [('indicationSendCount',
                                Uint32(0))])

        # TODO ks Mar 2017. Returns value 1 rather than zero for some reason
        # Sometimes returns value 0.
        # Review pegasus code.
        self.assertEqual(result[0], 1, 'Expected method result value 1 '
                         'Received result value %s' % result[0])

        # TODO: Call with empty arrays

        # TODO: Call with weird VALUE.REFERENCE child types:
        # (CLASSPATH|LOCALCLASSPATH|CLASSNAME|INSTANCEPATH|LOCALINSTANCEPATH|
        #  INSTANCENAME)

#################################################################
# Associators request interface tests
#################################################################


class Associators(ClientTest):
    """ Tests of the associators instance request operation."""

    def test_assoc_one_class(self):

        # Call on named instance

        inst_names = self.cimcall(self.conn.EnumerateInstanceNames,
                                  TEST_CLASS)
        self.assertTrue(len(inst_names) >= 1)
        inst_name = inst_names[0]  # Pick the first returned instance

        instances = self.cimcall(self.conn.Associators, inst_name)

        for i in instances:
            self.assertTrue(isinstance(i, CIMInstance))
            self.assertTrue(isinstance(i.path, CIMInstanceName))

            # TODO: For now, disabled test for class name of associated insts.
            # self.assertTrue(i.classname == 'TBD')

            self.assertTrue(i.path.namespace is not None)
            self.assertTrue(i.path.host is not None)

        # TODO: check return values

    def test_one_class_associator(self):
        """
            Test getting associator classes for defined class."""

        assoc_classes = self.cimcall(self.conn.Associators, TEST_CLASS)

        for cls in assoc_classes:
            self.assertAssocRefClassRtnValid(cls)

    def test_pywbem_person_class_associator(self):
        # pylint: disable=invalid-name
        """Get Class Associator for PyWBEM_Person source instance."""
        if not self.pywbem_person_class_exists():
            return

        result = self.cimcall(self.conn.Associators, PYWBEM_PERSON_CLASS)

        self.assertAssocRefClassRtnValid(result)

    def test_pywbem_person_class_associator2(self):
        # pylint: disable=invalid-name
        """Get a class associator filtered by result role and role"""
        if not self.pywbem_person_class_exists():
            return

        result = self.cimcall(
            self.conn.Associators, PYWBEM_PERSON_CLASS,
            AssocClass=PYWBEM_MEMBEROFPERSONCOLLECTION)

        self.assertAssocRefClassRtnValid(result)

        self.assertEqual(len(result), 1)

        self.assertEqual(result[0][1].classname, 'CIM_Collection')

    def test_pywbem_person_class_associator3(self):
        # pylint: disable=invalid-name
        """Get a class associator filtered by result role and role"""
        if not self.pywbem_person_class_exists():
            return

        result = self.cimcall(
            self.conn.Associators, PYWBEM_PERSON_CLASS,
            AssocClass=PYWBEM_MEMBEROFPERSONCOLLECTION,
            role=PYWBEM_SOURCE_ROLE)

        self.assertAssocRefClassRtnValid(result)

        self.assertEqual(len(result), 1)

        self.assertEqual(result[0][1].classname, 'CIM_Collection')

    # TODO ks dec/16 why returning CIM_Collection
    # TODO ks dec/16 why do we not get return when we user resultrole

    def test_pywbem_person_inst_associator(self):
        # pylint: disable=invalid-name
        """Get Class Associator for PyWBEM_Person source instance."""
        if not self.pywbem_person_class_exists():
            return

        inst_names = self.cimcall(self.conn.EnumerateInstanceNames,
                                  PYWBEM_PERSON_CLASS)
        self.assertTrue(len(inst_names) >= 1)

        for path in inst_names:
            ref_insts = self.cimcall(
                self.conn.Associators, path,
                AssocClass=PYWBEM_MEMBEROFPERSONCOLLECTION,
                Role=PYWBEM_SOURCE_ROLE)
            self.assertTrue(len(ref_insts) > 0)
            self.assertInstancesValid(ref_insts)
            for inst in ref_insts:
                self.assertEqual(inst.classname, 'PyWBEM_PersonCollection')

    def test_pywbem_person_inst_associator_fail(self):
        # pylint: disable=invalid-name
        """Fail get of associator instance because namespace fails."""
        if not self.pywbem_person_class_exists():
            return

        inst_names = self.cimcall(self.conn.EnumerateInstanceNames,
                                  PYWBEM_PERSON_CLASS)
        self.assertTrue(len(inst_names) >= 1)

        try:
            for path in inst_names:
                path.namespace = 'blah'
                ref_insts = self.cimcall(
                    self.conn.Associators, path,
                    AssocClass=PYWBEM_MEMBEROFPERSONCOLLECTION,
                    Role=PYWBEM_SOURCE_ROLE)
                self.assertTrue(len(ref_insts) > 0)
                self.assertInstancesValid(ref_insts)
                for inst in ref_insts:
                    self.assertEqual(inst.classname, 'PyWBEM_PersonCollection')
            self.fail('Expect exception')
        except CIMError as ce:
            if ce.args[0] != CIM_ERR_INVALID_NAMESPACE:
                raise

    def test_pywbem_person_inst_associatorName2(self):
        # pylint: disable=invalid-name
        """Get Class associator for PyWBEM_Person source instance.

           All parameters included
        """
        if not self.pywbem_person_class_exists():
            return

        inst_names = self.cimcall(self.conn.EnumerateInstanceNames,
                                  PYWBEM_PERSON_CLASS)
        self.assertTrue(len(inst_names) >= 1)

        for path in inst_names:
            ref_insts = self.cimcall(
                self.conn.AssociatorNames, path,
                ResultClass='CIM_Collection',
                AssocClass=PYWBEM_MEMBEROFPERSONCOLLECTION,
                Role=PYWBEM_SOURCE_ROLE,
                ResultRole='Collection')

            self.assertTrue(len(ref_insts) > 0)
            self.assertPathsValid(ref_insts)
            for inst in ref_insts:
                self.assertEqual(inst.classname, 'PyWBEM_PersonCollection')

    def test_invalid_classname(self):
        """Test fail with invalid classname"""
        try:
            self.cimcall(self.conn.Associators, 'CIM_BlanBlahBlah')
        except CIMError as ce:
            if ce.args[0] != CIM_ERR_INVALID_PARAMETER:
                raise

    @unittest.skipIf(SKIP_LONGRUNNING_TEST, 'skip long test')
    def test_all_class_associators(self):
        """Test getting associator classes for all classes in a namespace."""

        classes = self.cimcall(self.conn.EnumerateClassNames,
                               DeepInheritance=True)

        for cls in classes:
            assoc_classes = self.cimcall(self.conn.Associators, cls)

            for clsa in assoc_classes:
                self.assertAssocRefClassRtnValid(clsa)


class AssociatorNames(ClientTest):

    def test_one_assocname(self):

        # Call on named instance

        inst_names = self.cimcall(self.conn.EnumerateInstanceNames,
                                  TEST_CLASS)
        self.assertTrue(len(inst_names) >= 1)
        inst_name = inst_names[0]  # Pick the first returned instance

        names = self.cimcall(self.conn.AssociatorNames, inst_name)

        for n in names:
            self.assertTrue(isinstance(n, CIMInstanceName))

            # TODO: For now, disabled test for class name of associated insts.
            # self.assertTrue(n.classname == 'TBD')

            self.assertTrue(n.namespace is not None)
            self.assertTrue(n.host is not None)

    def test_one_class_associatorname(self):
        # pylint: disable=invalid-name
        """Test call with classname."""

        names = self.cimcall(self.conn.AssociatorNames, TEST_CLASS)
        self.assertTrue(len(names) > 0)
        self.assertClassNamesValid(names)

    def test_pywbem_person_class_associatorname(self):
        # pylint: disable=invalid-name
        """Get Class associator for PyWBEM_Person source instance."""
        if not self.pywbem_person_class_exists():
            return

        names = self.cimcall(self.conn.AssociatorNames, PYWBEM_PERSON_CLASS)
        self.assertTrue(len(names) > 0)
        self.assertClassNamesValid(names)

    def test_pywbem_person_class_associatorname2(self):
        # pylint: disable=invalid-name
        """Get a class associator filtered by assoc class"""
        if not self.pywbem_person_class_exists():
            return

        names = self.cimcall(
            self.conn.AssociatorNames, PYWBEM_PERSON_CLASS,
            AssocClass=PYWBEM_MEMBEROFPERSONCOLLECTION)

        self.assertClassNamesValid(names)

        self.assertEqual(len(names), 1)

    def test_pywbem_person_class_associatorname3(self):
        # pylint: disable=invalid-name
        """Get a class associator filtered by result role and role"""
        if not self.pywbem_person_class_exists():
            return

        names = self.cimcall(
            self.conn.AssociatorNames, PYWBEM_PERSON_CLASS,
            AssocClass=PYWBEM_MEMBEROFPERSONCOLLECTION,
            Role=PYWBEM_SOURCE_ROLE)

        self.assertClassNamesValid(names)

        self.assertEqual(len(names), 1)

    def test_pywbem_person_class_associatorname4(self):
        # pylint: disable=invalid-name
        """Get a class associator filtered by result role and role"""
        if not self.pywbem_person_class_exists():
            return

        names = self.cimcall(
            self.conn.AssociatorNames, PYWBEM_PERSON_CLASS,
            ResultClass='CIM_Collection',
            AssocClass=PYWBEM_MEMBEROFPERSONCOLLECTION,
            Role=PYWBEM_SOURCE_ROLE,
            ResultRole='Collection')

        self.assertClassNamesValid(names)

        self.assertEqual(len(names), 1)

    def test_pywbem_person_inst_associatorName(self):
        # pylint: disable=invalid-name
        """
        Get associator instances for PyWBEM_Person source instance.

        Uses default for all optional request parameters

        """
        if not self.pywbem_person_class_exists():
            return

        inst_names = self.cimcall(self.conn.EnumerateInstanceNames,
                                  PYWBEM_PERSON_CLASS)
        self.assertTrue(len(inst_names) >= 1)

        for path in inst_names:
            ref_inst_names = self.cimcall(
                self.conn.AssociatorNames, path)

            self.assertTrue(len(ref_inst_names) > 0)
            self.assertInstanceNamesValid(ref_inst_names)

    def test_pywbem_person_inst_associatorName2(self):
        # pylint: disable=invalid-name
        """
        Get associator instances for PyWBEM_Person source instance.

        This test includes all of the association filters

        """
        if not self.pywbem_person_class_exists():
            return

        inst_names = self.cimcall(self.conn.EnumerateInstanceNames,
                                  PYWBEM_PERSON_CLASS)
        self.assertTrue(len(inst_names) >= 1)

        for path in inst_names:
            ref_inst_names = self.cimcall(
                self.conn.AssociatorNames, path,
                ResultClass='CIM_Collection',
                AssocClass=PYWBEM_MEMBEROFPERSONCOLLECTION,
                Role=PYWBEM_SOURCE_ROLE,
                ResultRole='Collection')

            self.assertTrue(len(ref_inst_names) > 0)
            self.assertInstanceNamesValid(ref_inst_names)

    def test_invalid_classname(self):
        """Test fail with invalid classname"""
        try:
            self.cimcall(self.conn.AssociatorNames, 'CIM_BlanBlahBlah')
        except CIMError as ce:
            if ce.args[0] != CIM_ERR_INVALID_PARAMETER:
                raise

    @unittest.skipIf(SKIP_LONGRUNNING_TEST, 'skip long test')
    def test_all_class_associatornames(self):
        """Test getting associator classes for all classes in a namespace."""

        names = self.cimcall(self.conn.EnumerateClassNames,
                             DeepInheritance=True)

        for name in names:
            assoc_classnames = self.cimcall(self.conn.AssociatorNames, name)

            for n in assoc_classnames:
                self.assertTrue(isinstance(n, CIMClassName))


class References(ClientTest):

    def test_one_ref(self):

        # Call on named instance
        # TODO. This is really broken

        inst_names = self.cimcall(self.conn.EnumerateInstanceNames, TEST_CLASS)
        self.assertTrue(len(inst_names) >= 1)
        inst_name = inst_names[0]  # Pick the first returned instance

        instances = self.cimcall(self.conn.References, inst_name)

        for i in instances:
            self.assertTrue(isinstance(i, CIMInstance))
            self.assertTrue(isinstance(i.path, CIMInstanceName))

            # TODO: For now, disabled test for class name of referencing insts.
            # self.assertTrue(i.classname == 'TBD')

            self.assertTrue(i.path.namespace is not None)
            self.assertTrue(i.path.host is not None)

    def test_one_class_reference(self):
        """Test call with classname that returns classes."""

        result = self.cimcall(self.conn.References, TEST_CLASS)

        self.assertAssocRefClassRtnValid(result)

    def test_pywbem_person_class_ref(self):
        """Get Class Reference for PyWBEM_Person source instance."""
        if not self.pywbem_person_class_exists():
            return

        result = self.cimcall(self.conn.References, PYWBEM_PERSON_CLASS)

        self.assertAssocRefClassRtnValid(result)

    def test_pywbem_person_class_ref2(self):
        """Get a class reference filtered by result role and role"""
        if not self.pywbem_person_class_exists():
            return

        result = self.cimcall(
            self.conn.References, PYWBEM_PERSON_CLASS,
            ResultClass=PYWBEM_MEMBEROFPERSONCOLLECTION)

        self.assertAssocRefClassRtnValid(result)

        self.assertEqual(len(result), 1)

        self.assertEqual(result[0][1].classname,
                         PYWBEM_MEMBEROFPERSONCOLLECTION)

    def test_pywbem_person_class_ref3(self):
        """Get a class reference filtered by result role and role"""
        if not self.pywbem_person_class_exists():
            return

        result = self.cimcall(
            self.conn.References, PYWBEM_PERSON_CLASS,
            ResultClass=PYWBEM_MEMBEROFPERSONCOLLECTION,
            role=PYWBEM_SOURCE_ROLE)

        self.assertAssocRefClassRtnValid(result)

        self.assertEqual(len(result), 1)

        self.assertEqual(result[0][1].classname,
                         PYWBEM_MEMBEROFPERSONCOLLECTION)

    def test_pywbem_person_inst_ref(self):
        """Get Class Reference for PyWBEM_Person source instance."""
        if not self.pywbem_person_class_exists():
            return

        inst_names = self.cimcall(self.conn.EnumerateInstanceNames,
                                  PYWBEM_PERSON_CLASS)
        self.assertTrue(len(inst_names) >= 1)

        for path in inst_names:
            ref_insts = self.cimcall(
                self.conn.References, path,
                ResultClass=PYWBEM_MEMBEROFPERSONCOLLECTION,
                Role=PYWBEM_SOURCE_ROLE)
            self.assertTrue(len(ref_insts) > 0,
                            'Reference Instances expected. None received')
            self.assertInstancesValid(ref_insts)
            for inst in ref_insts:
                self.assertEqual(inst.classname,
                                 PYWBEM_MEMBEROFPERSONCOLLECTION)

    def test_invalid_classname(self):
        """Test fail with invalid classname"""
        try:
            self.cimcall(self.conn.References, 'CIM_BlanBlahBlah')
        except CIMError as ce:
            if ce.args[0] != CIM_ERR_INVALID_PARAMETER:
                raise


class ReferenceNames(ClientTest):

    def test_one_refname(self):

        # Call on instance name

        inst_names = self.cimcall(self.conn.EnumerateInstanceNames, TEST_CLASS)
        self.assertTrue(len(inst_names) >= 1)
        inst_name = inst_names[0]  # Pick the first returned instance

        names = self.cimcall(self.conn.ReferenceNames, inst_name)

        self.assertClassNamesValid(names)

    def test_one_class_referencename(self):
        """Test call with classname."""

        names = self.cimcall(self.conn.ReferenceNames, TEST_CLASS)

        self.assertTrue(len(names) > 0)

        self.assertClassNamesValid(names)

    # pylint: disable=invalid-name
    def test_pywbem_person_class_referencename(self):
        """Get Class Reference for PyWBEM_Person source instance."""
        if not self.pywbem_person_class_exists():
            return

        names = self.cimcall(self.conn.ReferenceNames, PYWBEM_PERSON_CLASS)
        self.assertClassNamesValid(names)

    def test_pywbem_person_class_referencename2(self):
        """Get a class reference filtered by result role and role"""
        if not self.pywbem_person_class_exists():
            return

        names = self.cimcall(
            self.conn.ReferenceNames, PYWBEM_PERSON_CLASS,
            ResultClass=PYWBEM_MEMBEROFPERSONCOLLECTION)

        self.assertClassNamesValid(names)

        self.assertEqual(len(names), 1)

    def test_pywbem_person_class_referencename3(self):
        """Get a class reference filtered by result role and role"""
        if not self.pywbem_person_class_exists():
            return

        names = self.cimcall(
            self.conn.ReferenceNames, PYWBEM_PERSON_CLASS,
            ResultClass=PYWBEM_MEMBEROFPERSONCOLLECTION,
            role=PYWBEM_SOURCE_ROLE)

        self.assertClassNamesValid(names)

        self.assertEqual(len(names), 1)

    def test_pywbem_person_inst_ref(self):
        """Get Class Reference for PyWBEM_Person source instance."""
        if not self.pywbem_person_class_exists():
            return

        inst_names = self.cimcall(self.conn.EnumerateInstanceNames,
                                  PYWBEM_PERSON_CLASS)
        self.assertTrue(len(inst_names) >= 1)

        for path in inst_names:
            ref_inst_names = self.cimcall(
                self.conn.ReferenceNames, path,
                ResultClass=PYWBEM_MEMBEROFPERSONCOLLECTION,
                Role=PYWBEM_SOURCE_ROLE)
            self.assertTrue(len(ref_inst_names) > 0,
                            'Reference Classes expected. Received none')
            self.assertInstanceNamesValid(ref_inst_names)
            # for inst in ref_insts:
            #    self.assertEqual(inst.classname,
            #        PYWBEM_MEMBEROFPERSONCOLLECTION)

    def test_invalid_classname(self):
        """Test fail with invalid classname"""
        try:
            self.cimcall(self.conn.ReferenceNames, 'CIM_BlanBlahBlah')
        except CIMError as ce:
            if ce.args[0] != CIM_ERR_INVALID_PARAMETER:
                raise


#################################################################
# Schema manipulation interface tests
#################################################################


class ClientClassTest(ClientTest):
    """Intermediate class for testing CIMClass instances.
       Class operations subclass from this class"""

    def verify_property(self, prop):
        """Verify that this a cim property and verify attributes."""

        self.assertTrue(isinstance(prop, CIMProperty))

    def verify_qualifier(self, qualifier):
        """Verify qualifier attributes."""
        self.assertTrue(isinstance(qualifier, CIMQualifier))
        self.assertTrue(qualifier.name)
        self.assertTrue(qualifier.value)

    def verify_method(self, method):
        """Verify method attributes."""
        self.assertTrue(isinstance(method, CIMMethod))
        # TODO add these tests
        # #pass

    def verify_class(self, cl):
        """Verify simple class attributes."""
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
        # TODO could we assert some size limit here. Probably Not
        # since this applies to any server.
        if self.verbose:
            print('end deep inheritance size %s' % len(full_name_list))

    def test_pywbem_person(self):
        '''Enumerate starting at pywbem_person with no extra parameters.'''
        if not self.pywbem_person_class_exists():
            return

        classes = self.cimcall(self.conn.EnumerateClassNames,
                               ClassName=PYWBEM_PERSON_CLASS)

        # The requested class should NOT be in the list
        # since this gets subclass names.
        for cl in classes:
            self.assertTrue(isinstance(cl, six.string_types))

    def test_bad_classname(self):
        '''Enumerate starting at pywbem_person with no extra parameters.'''
        if not self.pywbem_person_class_exists():
            return

        try:
            self.cimcall(self.conn.EnumerateClassNames, ClassName='XXX_Blah')
        except CIMError as ce:
            if ce.args[0] != CIM_ERR_INVALID_CLASS:
                raise


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

    def test_pywbem_person(self):
        '''Enumerate starting at pywbem_person with no extra parameters.'''
        if not self.pywbem_person_class_exists():
            return

        classes = self.cimcall(self.conn.EnumerateClasses,
                               ClassName=PYWBEM_PERSON_CLASS)

        for cl in classes:
            self.assertTrue(isinstance(cl, CIMClass))
            self.verify_class(cl)

    def test_pywbem_person2(self):
        '''Enumerate starting at pywbem_person with no all parameters.'''
        if not self.pywbem_person_class_exists():
            return

        classes = self.cimcall(self.conn.EnumerateClasses,
                               ClassName=PYWBEM_PERSON_CLASS,
                               IncludeClassOrigin=True,
                               IncludeQualifiers=True,
                               LocalOnly=False,
                               DeepInheritance=True)
        for cl in classes:
            self.assertTrue(isinstance(cl, CIMClass))
            self.verify_class(cl)

    def test_invalid_classname(self):

        # Enumerate all classes
        try:
            self.cimcall(self.conn.EnumerateClasses, ClassName="CIM_Blah")
        except CIMError as ce:
            if ce.args[0] != CIM_ERR_INVALID_CLASS:
                raise


class GetClass(ClientClassTest):
    """Test the get Class request operation"""

    def test_simple(self):
        """Get a classname from server and then get class."""

        name = self.cimcall(self.conn.EnumerateClassNames)[0]
        cl = self.cimcall(self.conn.GetClass, name)
        if self.debug:
            print('GetClass gets name %s' % name)
        self.verify_class(cl)
        mof_output = cl.tomof()
        if self.verbose:
            print('MOF OUTPUT\n%s' % (mof_output))

    def test_class_propertylist(self):
        """ Test with propertyList for getClass."""

        property_list = ['PowerManagementCapabilities']

        cls = self.cimcall(self.conn.GetClass, TEST_CLASS,
                           PropertyList=property_list, LocalOnly=False)

        self.assertTrue(len(cls.properties) == len(property_list))

        if self.verbose:
            for p in cls.properties.values():
                print('ClassPropertyName=%s' % p.name)

    def test_class_single_property(self):
        """ Test with propertyList for getClass to confirm that single
            string not in list works.
        """
        property_list = TEST_CLASS_PROPERTY2

        cls = self.cimcall(self.conn.GetClass, TEST_CLASS,
                           PropertyList=property_list, LocalOnly=False)

        self.assertEqual(len(cls.properties), 1)

        if self.verbose:
            for p in cls.properties.values():
                print('ClassPropertyName=%s' % p.name)

    def test_nonexistent_class(self):
        try:
            self.cimcall(self.conn.GetClass, 'CIM_BlanBlahBlah')
        except CIMError as ce:
            if ce.args[0] != CIM_ERR_NOT_FOUND:
                raise

        # TODO extend for options of Deepinheritance, LocalOnly,
        # IncludeQualifiers, IncludeClassOrigin


class ClassOperations(ClientClassTest):
    """
    Common functions for Create, Delete, Modify class tests
    """
    def create_simple_class(self):
        """
        Create an instance of the class we will use for create/modify tests.

        This creates a very simple class with only two properties

        Returns the class created.
        """
        test_class_name = 'PyWbem_Run_CIM_Operations0'
        test_class = CIMClass(
            test_class_name,
            methods={u'Delete': CIMMethod(u'Delete', 'uint32')},
            qualifiers={u'Description': CIMQualifier('Description',
                                                     'This is a class '
                                                     'description')},
            properties={u'InstanceID': CIMProperty(u'InstanceID', None,
                                                   type='string'),
                        u'MyUint8': CIMProperty(u'MyUint8', Uint8(99),
                                                type='uint8')})

        # force propagated False for all properties
        # Effective V 0.12.0 propagated must be set to compare with
        # info returned from server.
        for p in test_class.properties:
            test_class.properties[p].propagated = False

        return test_class

    def create_class(self):
        """
        Create an instance of the class we will use for create/modify tests.

        This creates a complex class with many properties and most property
        types

        Returns the class created.
        """
        test_class_name = 'PyWbem_Run_CIM_Operations1'
        test_class = CIMClass(
            test_class_name,
            methods={u'Delete': CIMMethod(u'Delete', 'uint32')},
            qualifiers={u'Description': CIMQualifier('Description',
                                                     'This is a class '
                                                     'description')},
            properties={u'InstanceID': CIMProperty(u'InstanceID', None,
                                                   type='string'),
                        u'MyUint8': CIMProperty(u'MyUint8', Uint8(99),
                                                type='uint8'),
                        u'MySint8': CIMProperty(u'MySint8', Sint8(99),
                                                type='sint8'),
                        u'MyUint16': CIMProperty(u'MyUint16', Uint16(999),
                                                 type='uint16'),
                        u'MySint16': CIMProperty(u'MySint16', Sint16(-999),
                                                 type='sint16'),
                        u'MyUint32': CIMProperty(u'MyUint32', Uint32(12345),
                                                 type='uint32'),
                        u'MySint32': CIMProperty(u'MySint32', Sint32(-12345),
                                                 type='sint32'),
                        u'MyUint64': CIMProperty(u'MyUint64', Uint64(12345),
                                                 type='uint64'),
                        u'MySint64': CIMProperty(u'MySint64', Sint64(-12345),
                                                 type='sint64'),
                        u'MyReal32': CIMProperty(u'MyReal32', Real32(12345),
                                                 type='real32'),
                        u'MyReal64': CIMProperty(u'MyReal64', Real64(12345),
                                                 type='real64'),
                        u'Mydatetime': CIMProperty(u'Mydatetime',
                                                   '12345678224455.654321:000',
                                                   type='datetime'),
                        u'Uint32Array': CIMProperty(u'Uint32Array', None,
                                                    type='uint32',
                                                    is_array=True),
                        u'Sint32Array': CIMProperty(u'Sint32Array', None,
                                                    type='sint32',
                                                    is_array=True),
                        u'Uint64Array': CIMProperty(u'Uint64Array', None,
                                                    type='uint64',
                                                    is_array=True),
                        u'Sint64Array': CIMProperty(u'Sint64Array', None,
                                                    type='sint64',
                                                    is_array=True),
                        u'MyStr': CIMProperty(u'MyStr', 'This is a test',
                                              type='string')})
        for p in test_class.properties:
            test_class.properties[p].propagated = False
        return test_class


class CreateClass(ClassOperations):

    def test_simple_create_delete(self):
        """
        Test Create Class by creating a new class in the server.

        This also tests delete class because we first confirm that the
        class does not exist with DeleteClass and then delete the
        class from the repository after creation.
        """

        test_class = self.create_simple_class()
        test_class_name = test_class.classname

        # Delete if already exists (previous test incomplete)
        try:
            self.cimcall(self.conn.DeleteClass, test_class_name)
        except CIMError as ce:
            if ce.args[0] == CIM_ERR_NOT_FOUND:
                pass

        # Create the class in the server

        try:
            self.cimcall(self.conn.CreateClass, test_class)
        except CIMError as ce:
            if ce.args[0] == CIM_ERR_INVALID_CLASS:
                print('NOTE: This server/namespace does not support '
                      'CreateClass since it returned INVALID_CLASS')
        else:
            # get the class and compare with original
            rtn_class = self.cimcall(self.conn.GetClass, test_class_name)
            # returns with propagated  and translatable set by the server
            # but sent as none. Make the same to compare.
            if rtn_class.methods['Delete'].propagated != \
                    test_class.methods['Delete'].propagated:
                rtn_class.methods['Delete'].propagated = \
                    test_class.methods['Delete'].propagated

            if rtn_class.qualifiers['Description'].propagated != \
                    test_class.qualifiers['Description'].propagated:
                rtn_class.qualifiers['Description'].propagated = \
                    test_class.qualifiers['Description'].propagated

            if rtn_class.qualifiers['Description'].translatable != \
                    test_class.qualifiers['Description'].translatable:
                rtn_class.qualifiers['Description'].translatable = \
                    test_class.qualifiers['Description'].translatable

            if rtn_class.qualifiers['Description'].tosubclass != \
                    test_class.qualifiers['Description'].tosubclass:
                rtn_class.qualifiers['Description'].tosubclass = \
                    test_class.qualifiers['Description'].tosubclass

            if rtn_class.qualifiers['Description'].toinstance != \
                    test_class.qualifiers['Description'].toinstance:
                rtn_class.qualifiers['Description'].toinstance = \
                    test_class.qualifiers['Description'].toinstance

            if rtn_class.qualifiers['Description'].overridable != \
                    test_class.qualifiers['Description'].overridable:
                rtn_class.qualifiers['Description'].overridable = \
                    test_class.qualifiers['Description'].overridable

            # move CIMClassName from return to test class for compare
            test_class.path = rtn_class.path
            self.assertEqual(rtn_class.classname, test_class_name)
            self.assertEqual(rtn_class, test_class)
            # delete the new class
            self.cimcall(self.conn.DeleteClass, test_class_name)

        # This should fail.  class already deleted
        try:
            self.cimcall(self.conn.GetClass, test_class_name)

        except CIMError as arg:
            if arg == CIM_ERR_NOT_FOUND:
                pass

    def test_create_delete1(self):
        """
        Test Create Class by creating a new class in the server.

        This also tests delete class because we first confirm that the
        class does not exist with DeleteClass and then delete the
        class from the repository after creation.
        """

        test_class = self.create_class()
        test_class_name = test_class.classname

        # Delete if already exists (previous test incomplete)
        try:
            self.cimcall(self.conn.DeleteClass, test_class_name)
        except CIMError as ce:
            if ce.args[0] == CIM_ERR_NOT_FOUND:
                pass

        # Create the class in the server

        try:
            self.cimcall(self.conn.CreateClass, test_class)
        except CIMError as ce:
            if ce.args[0] == CIM_ERR_INVALID_CLASS:
                print('NOTE: This server/namespace does not support '
                      'CreateClass since it returned INVALID_CLASS')

        else:
            # get the class and compare with original
            rtn_class = self.cimcall(self.conn.GetClass, test_class_name)
            # returns with propagated  and translatable set by the server
            # but sent as none. Make the same to compare.
            if rtn_class.methods['Delete'].propagated != \
                    test_class.methods['Delete'].propagated:
                rtn_class.methods['Delete'].propagated = \
                    test_class.methods['Delete'].propagated

            if rtn_class.qualifiers['Description'].propagated != \
                    test_class.qualifiers['Description'].propagated:
                rtn_class.qualifiers['Description'].propagated = \
                    test_class.qualifiers['Description'].propagated

            if rtn_class.qualifiers['Description'].translatable != \
                    test_class.qualifiers['Description'].translatable:
                rtn_class.qualifiers['Description'].translatable = \
                    test_class.qualifiers['Description'].translatable

            if rtn_class.qualifiers['Description'].tosubclass != \
                    test_class.qualifiers['Description'].tosubclass:
                rtn_class.qualifiers['Description'].tosubclass = \
                    test_class.qualifiers['Description'].tosubclass

            if rtn_class.qualifiers['Description'].toinstance != \
                    test_class.qualifiers['Description'].toinstance:
                rtn_class.qualifiers['Description'].toinstance = \
                    test_class.qualifiers['Description'].toinstance

            if rtn_class.qualifiers['Description'].overridable != \
                    test_class.qualifiers['Description'].overridable:
                rtn_class.qualifiers['Description'].overridable = \
                    test_class.qualifiers['Description'].overridable

            # put classpath into original class for compare
            test_class.path = rtn_class.path
            self.assertEqual(rtn_class.classname, test_class_name)
            self.assertEqual(rtn_class, test_class)
            # delete the new class
            self.cimcall(self.conn.DeleteClass, test_class_name)

        # This should fail.  class already deleted
        try:
            self.cimcall(self.conn.GetClass, test_class_name)

        except CIMError as arg:
            if arg == CIM_ERR_NOT_FOUND:
                pass

    def test_fail_namespace(self):
        """
        Test Create Class by creating a new class in the server.

        This also tests delete class because we first confirm that the
        class does not exist with DeleteClass and then delete the
        class from the repository after creation.
        """

        test_class_name = 'PyWbem_Run_CIM_Operations1'
        test_class = CIMClass(
            test_class_name,
            properties={'InstanceID': CIMProperty('InstanceID', None,
                                                  type='string'),
                        'MyStr': CIMProperty('MyStr', 'This is a test',
                                             type='string')})

        try:
            self.cimcall(self.conn.CreateClass, test_class, namespace='blah')
            self.fail("Create class should have failed with namespace error")
        except CIMError as ce:
            if ce.args[0] == CIM_ERR_INVALID_NAMESPACE:
                pass


class DeleteClass(ClassOperations):

    @unittest.skip(UNIMPLEMENTED)
    def test_all(self):
        raise AssertionError("test not implemented. See CreateClass")


class ModifyClass(ClassOperations):
    """Test the Modify class operation."""

    def test_modify_simple_class(self):
        """
        Test Modify Class by creating a new class and then changing the
        class and issuing ModifyClass.

        This also tests delete class because we first confirm that the
        class does not exist with DeleteClass and then delete the
        class from the repository after creation.
        """

        test_class = self.create_simple_class()
        test_class_name = test_class.classname

        # Delete if already exists (previous test incomplete)
        try:
            self.cimcall(self.conn.DeleteClass, test_class_name)
        except CIMError as ce:
            if ce.args[0] == CIM_ERR_NOT_FOUND:
                pass

        # Create the class in the server

        try:
            self.cimcall(self.conn.CreateClass, test_class)
        except CIMError as ce:
            if ce.args[0] == CIM_ERR_INVALID_CLASS:
                print('NOTE: This server/namespace does not support '
                      'CreateClass since it returned INVALID_CLASS')

        # Modify the original class by adding a new property
        new_property = CIMProperty('Str2', None,
                                   type='string',
                                   is_array=False,
                                   propagated=False)

        test_class.properties['Str2'] = new_property

        try:
            self.cimcall(self.conn.ModifyClass, test_class)
        except CIMError as ce:
            if ce.args[0] == CIM_ERR_INVALID_CLASS:
                print('NOTE: This server/namespace does not support '
                      'CreateClass since it returned INVALID_CLASS')

        else:
            # get the class and compare with original
            rtn_class = self.cimcall(self.conn.GetClass, test_class_name)
            # returns with propagated  and translatable set by the server
            # but sent as none. Make the same to compare.
            if rtn_class.methods['Delete'].propagated != \
                    test_class.methods['Delete'].propagated:
                rtn_class.methods['Delete'].propagated = \
                    test_class.methods['Delete'].propagated

            if rtn_class.qualifiers['Description'].propagated != \
                    test_class.qualifiers['Description'].propagated:
                rtn_class.qualifiers['Description'].propagated = \
                    test_class.qualifiers['Description'].propagated

            if rtn_class.qualifiers['Description'].translatable != \
                    test_class.qualifiers['Description'].translatable:
                rtn_class.qualifiers['Description'].translatable = \
                    test_class.qualifiers['Description'].translatable

            if rtn_class.qualifiers['Description'].tosubclass != \
                    test_class.qualifiers['Description'].tosubclass:
                rtn_class.qualifiers['Description'].tosubclass = \
                    test_class.qualifiers['Description'].tosubclass

            if rtn_class.qualifiers['Description'].toinstance != \
                    test_class.qualifiers['Description'].toinstance:
                rtn_class.qualifiers['Description'].toinstance = \
                    test_class.qualifiers['Description'].toinstance

            if rtn_class.qualifiers['Description'].overridable != \
                    test_class.qualifiers['Description'].overridable:
                rtn_class.qualifiers['Description'].overridable = \
                    test_class.qualifiers['Description'].overridable

            # test classpath on return class
            self.assertEqual(rtn_class.path.classname, test_class_name)
            self.assertEqual(rtn_class.path.namespace, self.namespace)
            # set rtn class path into test_class for compare
            test_class.path = rtn_class.path
            self.assertEqual(rtn_class.classname, test_class_name)
            for prop, value in rtn_class.properties.items():
                self.assertEqual(value, test_class.properties[prop])
            for method, value in rtn_class.methods.items():
                self.assertEqual(value, test_class.methods[method])
            # Don't test qualifier flavors because server controls these
            for qual, value in rtn_class.qualifiers.items():
                self.assertEqual(qual, test_class.qualifiers[qual].name)
            self.assertEqual(rtn_class, test_class)
            # delete the new class
            self.cimcall(self.conn.DeleteClass, test_class_name)

        # This should fail.  class already deleted
        try:
            self.cimcall(self.conn.GetClass, test_class_name)

        except CIMError as arg:
            if arg == CIM_ERR_NOT_FOUND:
                pass

    def test_modify_invalid_namespace(self):
        """Test failure when when modifyclass on nonexistent class."""
        test_class_name = 'PyWbem_Run_CIM_Operations2'
        test_class = CIMClass(
            test_class_name,
            properties={u'InstanceID': CIMProperty(u'InstanceID', None,
                                                   type='string'),
                        u'MyStr': CIMProperty(u'MyStr', 'This is a test',
                                              type='string')})

        try:
            self.cimcall(self.conn.ModifyClass, test_class, namespace='blah')
            self.fail("Modify class should have failed with namespace error")
        except CIMError as ce:
            if ce.args[0] == CIM_ERR_INVALID_NAMESPACE:
                pass

    def test_modify_invalid_class(self):
        """Test failure when when modifyclass on nonexistent class."""
        test_class_name = 'PyWbem_Run_CIM_Operations2'
        test_class = CIMClass(
            test_class_name,
            properties={u'InstanceID': CIMProperty(u'InstanceID', None,
                                                   type='string'),
                        u'MyStr': CIMProperty(u'MyStr', 'This is a test',
                                              type='string')})

        try:
            self.cimcall(self.conn.ModifyClass, test_class)
            self.fail("Modify class should have failed not found")
        except CIMError as ce:
            if ce.args[0] == CIM_ERR_NOT_FOUND:
                pass


#################################################################
# Qualifier Declaration provider interface tests
#################################################################


class QualifierDeclClientTest(ClientTest):
    """Base class for QualifierDeclaration tests. Adds specific
       tests.
    """
    def verify_qual_decls(self, qls, test_name=None):
        """Verify simple qualifier decl attributes."""
        if isinstance(qls, list):
            for ql in qls:
                self.verify_qual_decls(ql, test_name=None)

        else:
            ql = qls
            self.assertTrue(isinstance(ql, CIMQualifierDeclaration))

            if test_name is not None:
                self.assertTrue(ql.name == test_name)


class EnumerateQualifiers(QualifierDeclClientTest):
    """Test enumerating all qualifiers"""
    def test_get_all(self):
        qual_decls = self.cimcall(self.conn.EnumerateQualifiers)
        self.verify_qual_decls(qual_decls)
        my_qls = [ql for ql in qual_decls if ql.name == 'Abstract']
        self.assertEqual(len(my_qls), 1)

    def test_fail_namespace(self):
        try:
            self.cimcall(self.conn.EnumerateQualifiers, namespace='xx')
            self.fail('Should get exception')
        except CIMError as ce:
            if ce.args[0] != CIM_ERR_INVALID_NAMESPACE:
                raise


class GetQualifier(QualifierDeclClientTest):
    def test_get_one(self):
        """Test getqualifier with valid qualifier name"""
        qual_decl = self.cimcall(self.conn.GetQualifier, 'Abstract')
        self.verify_qual_decls(qual_decl, test_name='Abstract')

    def test_get_badname(self):
        """Test getqualifier with invalid qualifier name"""
        try:
            self.cimcall(self.conn.GetQualifier, 'blahblah')
        except CIMError as ce:
            if ce.args[0] != CIM_ERR_NOT_FOUND:
                raise


class SetQualifier(QualifierDeclClientTest):
    """Test the capability to create a QualifierDeclaration in the server.
       Since the goal is to keep the server repository clean, this also tests
       DeleteQualifier.
    """

    def test_create_delete(self):
        """
        Create a qualifier declaration, set it into the server, get
        the qualifier declaration created and then delete it.
        """

        qd = CIMQualifierDeclaration(u'FooQualDecl', 'string', is_array=False,
                                     value='Some string',
                                     scopes={'CLASS': True},
                                     overridable=False, tosubclass=False,
                                     translatable=False, toinstance=False)

        # Delete if already exists (previous test incomplete)
        try:
            self.cimcall(self.conn.DeleteQualifier, qd.name)
        except CIMError as ce:
            if ce.args[0] == CIM_ERR_NOT_SUPPORTED:
                print('NOTE: This server/namespace does not support '
                      'DeleteQualifier since it returned NOT SUPPORTED')
                return
            if ce.args[0] == CIM_ERR_NOT_FOUND:
                pass

        # Create the qualifier declaration in the server

        try:
            self.cimcall(self.conn.SetQualifier, qd)
        except CIMError as ce:
            if ce.args[0] == CIM_ERR_NOT_SUPPORTED:
                print('NOTE: This server/namespace does not support '
                      'SetQualifier since it returned NOT SUPPORTED')
                return

        # get the qd and compare with original
        rtn_qd = self.cimcall(self.conn.GetQualifier, qd.name)
        self.assertEqual(qd, rtn_qd, 'Returned qualifier declaration did not '
                         'match created')

        self.cimcall(self.conn.DeleteQualifier, qd.name)

        # This should fail.  class already deleted
        try:
            self.cimcall(self.conn.GetQualifier, qd.name)
            self.fail('This call should have failed')
        except CIMError as arg:
            if arg == CIM_ERR_NOT_FOUND:
                pass

    def test_create_fail(self):
        """
        Set aualifier declaration known to exist to server.

        Should fail. To do this, first create the new qualiferdecl and then
        try to create it a second time.
        """

        # create new one and send to server.
        scopes = {'CLASS': True}
        qd = CIMQualifierDeclaration(u'FooQualDecl', 'string', is_array=False,
                                     value='Some string',
                                     scopes=scopes,
                                     overridable=False, tosubclass=False)
        try:
            self.cimcall(self.conn.SetQualifier, qd)
        except CIMError as ce:
            if ce.args[0] == CIM_ERR_NOT_SUPPORTED:
                print('NOTE: This server/namespace does not support '
                      'SetQualifier since it returned NOT SUPPORTED')
                return

        # Now try to create a second time

        # Create should fail. qualifier exists
        # NOTE: There is an issue with OpenPegasus in that it rejects
        # the request instead of overwriting the qualifier declaration.
        # We need to account for that difference.
        # TODO account for openpegasus only response of returning
        # not supportedby confirming that this is the openpegasus
        # server.
        try:
            self.cimcall(self.conn.SetQualifier, qd)
        except CIMError as ce:
            if ce.args[0] == CIM_ERR_NOT_SUPPORTED:
                print('NOTE: This server/namespace does not support '
                      'SetQualifier since it returned\nNOT SUPPORTED,'
                      ' This may be due to issue with OpenPegasus'
                      ' that rejects\nSetQualifier on an existing qualifier'
                      'declaration.')
                return
        # finally delete the new qualifier to leave the server clean
        self.cimcall(self.conn.DeleteQualifier, qd.name)
        # This should fail.  class already deleted
        try:
            self.cimcall(self.conn.GetQualifier, qd.name)
        except CIMError as arg:
            if arg == CIM_ERR_NOT_FOUND:
                pass


class DeleteQualifier(QualifierDeclClientTest):
    """
    See the SetQualifier tests for the test to correctly delete a qualifier
    declaration.
    """

    def test_delete_fail(self):
        """
        Test for error return if set into an invalid namespace.
        """
        try:
            self.cimcall(self.conn.DeleteQualifier, "BlahBlah")
        except CIMError as ce:
            if ce.args[0] == CIM_ERR_NOT_SUPPORTED:
                print('NOTE: This server/namespace does not support '
                      'SetQualifier since it returned NOT SUPPORTED')
                return
            if ce.args[0] == CIM_ERR_NOT_FOUND:
                pass

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
            from utf-8 strings using CIM_Namespace class as source.
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

            for instance in instances:
                name = instance.properties['Name'].value
                namespaces.append(name)

            if self.verbose:
                print('Namespaces:')
                for n in namespaces:
                    print('  %s' % (n))

            return namespaces

        except CIMError as ce:
            if ce.args[0] != CIM_ERR_NOT_FOUND:
                print('CIMError %s. Could not find' % class_name)
            raise

    def is_pegasus_server(self):
        """ Test to determine if this the OpenPegasus server.
            Test for valid interop namespace, and the existence of
            PG_ObjectManager in that namespace.

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
                print('Not Pegasus Server. No instances of PG_ObjectManager')
                return False

            if self.verbose:
                for i in instances_:
                    if self.verbose:
                        # should have name and version in string
                        print(i.properties["Description"])
                        # should say pegasus
                        print(i.properties["ElementName"])

        except CIMError:
            return False

        return True

    def is_pegasus_test_build(self):
        """Assure that this is a pegasus test build with the test
           namespace. Tests the test/testprovider namespace existence.
        """

        if self.is_pegasus_server():
            namespaces = self.get_namespaces()

            if 'test/TestProvider' in namespaces:
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
                self.assertTrue((len(classes_) != 0),
                                'Interop namspace empty')
                return ns
            except CIMError as ce:
                if ce.args[0] != CIM_ERR_INVALID_NAMESPACE:
                    raise
        return None

    def try_class(self, ns, class_name):
        """Test if class exists.
           Returns true if `class_name` exists
        """
        try:
            my_class = self.cimcall(self.conn.GetClass, class_name,
                                    namespace=ns)
            return True
        except CIMError as ce:
            if ce.args[0] != CIM_ERR_NOT_FOUND:
                print('class get %s failed' % my_class)
                raise

            return False

    def has_namespace(self, ns):
        ns_ = self.get_namespaces()

        for n in ns_:
            if n == ns:
                return True
        return False

    def get_instances(self, ns, class_name):
        """Enum Instances of the defined class. returns instances. """

        try:
            instances = self.cimcall(self.conn.EnumerateInstances,
                                     class_name,
                                     namespace=ns)
            return instances

        # TODO ks 5/16 figure out why we could not get instances of a class
        #  and whether we should continue. do more than raise. This
        #  is an assert
        except CIMError:  # pylint: disable=try-except-raise
            raise

    def get_registered_profiles(self):
        """get the registered profile instances."""

        interop_ns = self.get_interop_namespace()
        self.assertTrue(interop_ns is not None)
        profiles = self.get_instances(interop_ns, 'CIM_RegisteredProfile')
        self.assertTrue(len(profiles) != 0)
        if self.verbose:
            for i in profiles:
                print(i.tomof())
        return profiles

    def set_stress_provider_parameters(self, count, size):
        """
        Set the pegasus stress provider parameters with InvokeMethod.
        This controls how many instances are returned for each enumerate
        response and the size of the responses.
        """
        try:
            invoke_classname = CIMClassName(TEST_PEG_STRESS_CLASSNAME,
                                            namespace=TEST_PEG_STRESS_NAMESPACE)
            result = self.conn.InvokeMethod("Set", invoke_classname,
                                            [('ResponseCount', Uint64(count)),
                                             ('Size', Uint64(size))])
            self.assertEqual(result[0], 0,
                             'SendTestIndicationCount Method error.')

        except Error as er:
            print('Error: Invoke Method exception %s' % er)
            raise


class PegasusInteropTest(PegasusServerTestBase):
    """Test for valid interop namespace in a pegasus server."""

    def test_interop_namespace(self):
        interop = self.get_interop_namespace()
        if self.verbose:
            print('interop=%r' % interop)

        self.assertTrue(interop is not None)

        namespaces_ = self.get_namespaces()

        self.assertTrue(namespaces_ is not None)

        self.assertTrue(self.try_class(interop, 'CIM_RegisteredProfile'))
        self.assertTrue(self.try_class(interop, 'CIM_Namespace'))

    def test_get_namespaces(self):
        """Test getting list of namespaces."""

        namespaces_ = self.get_namespaces()

        self.assertTrue(len(namespaces_) != 0)

        self.assertTrue(self.get_interop_namespace() in namespaces_)

    def test_get_registered_profiles(self):
        """ Test ability to get known profiles from server. """

        profiles = self.get_registered_profiles()
        self.assertTrue(len(profiles) != 0)
        if self.verbose:
            for p in profiles:
                print('org=%s RegisteredName=%s, RegisteredVersion=%s' %
                      (p['RegisteredOrganization'], p['RegisteredName'],
                       p['RegisteredVersion']))


class PEGASUSCLITestClass(PegasusServerTestBase):
    """Test against a class that has all of the property types
       defined.
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


class PegasusTestEmbeddedInstance(RegexpMixin, PegasusServerTestBase):
    """Tests a specific provider implemented pegasus class that
        includes an embedded instance.
    """

    def test_receive(self):
        if self.is_pegasus_test_build():
            # test class with embedded instance
            cl1 = 'Test_CLITestEmbeddedClass'
            ns = 'test/TestProvider'
            prop_name = 'embeddedInst'
            property_list = [prop_name]

            instances = self.cimcall(self.conn.EnumerateInstances,
                                     cl1, namespace=ns,
                                     propertylist=property_list)
            for inst in instances:
                str_mof = inst.tomof()
                str_xml = inst.tocimxmlstr(2)
                if self.verbose:
                    print('====== %s MOF=====\n%s' % (inst.path, str_mof))
                    print('======%s XML=====\n%s' % (inst.path, str_xml))

                # confirm general characteristics of mof output
                self.assert_regexp_matches(
                    str_mof, r"instance of Test_CLITestEmbeddedClass {")
                self.assert_regexp_contains(
                    str_mof.replace('\n', ' '),
                    r"embeddedInst = +\"instance of Test_CLITestEmbedded1 {")

                # get the embedded instance property
                prop = inst.properties[prop_name]
                self.assertTrue(prop.embedded_object)

                embedded_inst = prop.value

                if self.verbose:
                    print('EmbeddedInstance type=%s rep=%s' %
                          (type(embedded_inst), repr(embedded_inst)))
                self.assertIsInstance(embedded_inst, CIMInstance,
                                      msg='Embedded Inst must be CIMInstance')

                # confirm that a valid instance is in embedded_inst
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


class PyWBEMServerClass(RegexpMixin, PegasusServerTestBase):
    """
       Test the components of the server class and compare with previous tests
       for openpegasus.  This set of tests runs only on openpegasus.
       Tests for valid namespaces, valid interop namespace, valid profiles,
       pegasus brand information.
    """

    def print_profile_info(self, org_vm, inst):
        """Print the registered org, name, version for the profile defined by
           inst.
        """
        org = org_vm.tovalues(inst['RegisteredOrganization'])
        name = inst['RegisteredName']
        vers = inst['RegisteredVersion']
        print("  %s %s Profile %s" % (org, name, vers))

    def test_namespaces(self):
        """ Compare namespaces from the pegasus function with those from
            the server function.
        """

        peg_namespaces = self.get_namespaces()

        server = WBEMServer(self.conn)

        self.assertEqual(len(server.namespaces), len(peg_namespaces))
        for n in peg_namespaces:
            self.assertTrue(n in server.namespaces)

    def test_interop_namespace(self):
        """Confirm that pegasus tests and Server class select same namespace
           as interop namespace.
        """

        server = WBEMServer(self.conn)

        peg_interop = self.get_interop_namespace()

        self.assertEqual(peg_interop.lower(), server.interop_ns.lower())

    def test_registered_profiles(self):
        """ Test getting profiles from server class against getting list
            directly from server.
        """

        server = WBEMServer(self.conn)

        org_vm = ValueMapping.for_property(server, server.interop_ns,
                                           'CIM_RegisteredProfile',
                                           'RegisteredOrganization')

        peg_profiles = self.get_registered_profiles()

        self.assertEqual(len(peg_profiles), len(server.profiles))

        for inst in peg_profiles:
            self.assertTrue(inst in server.profiles)

        if self.verbose:
            print()
            for inst in server.profiles:
                org = org_vm.tovalues(inst['RegisteredOrganization'])
                name = inst['RegisteredName']
                vers = inst['RegisteredVersion']
                print("  %s %s Profile %s" % (org, name, vers))

    def test_get_brand(self):
        """ Get brand info. If pegasus server test for correct response.
            Otherwise display result.
        """

        server = WBEMServer(self.conn)

        if self.is_pegasus_server():
            self.assertEqual(server.brand, 'OpenPegasus')
            self.assert_regexp_matches(server.version, r"^2\.1[0-7]\.[0-7]$")
        else:
            # Do not know what server it is so just display
            print("Brand: %s" % server.brand)
            print("Server Version:\n  %s" % server.version)

    def test_indication_profile_info(self):
        """ Get the indications central class."""

        server = WBEMServer(self.conn)

        org_vm = ValueMapping.for_property(server, server.interop_ns,
                                           'CIM_RegisteredProfile',
                                           'RegisteredOrganization')

        indications_profile = None

        # find indication profiles
        for inst in server.profiles:
            org = org_vm.tovalues(inst['RegisteredOrganization'])
            name = inst['RegisteredName']
            vers = inst['RegisteredVersion']
            if org == "DMTF" and name == "Indications" and vers == "1.1.0":
                indications_profile = inst

        try:
            # get central class. Central_class = CIM_IndicationService
            # scoping_class=CIM_System, scoping_path- association class is
            # cim_HostedService
            ci_paths = server.get_central_instances(
                indications_profile.path,
                "CIM_IndicationService", "CIM_System", ["CIM_HostedService"])
        except Exception as exc:  # pylint: disable=broad-except
            print("Error: %s" % str(exc))
            ci_paths = []
            self.fail("No central class for indication profile")

        for ip in ci_paths:
            ind_svc_inst = self.cimcall(self.conn.GetInstance, ip)
            if self.verbose:
                print(ind_svc_inst.tomof())

            # Search class hierarchy for CIM_IndicationService
            # TODO change to create function to do the hierarchy search
            cls_name = ind_svc_inst.classname
            while cls_name != 'CIM_IndicationService':
                cls = self.cimcall(self.conn.GetClass, cls_name,
                                   namespace=ip.namespace)

                if cls.superclass is not None:
                    cls_name = cls.superclass
                else:
                    self.fail("Could not find CIM_IndicationService")

    def test_server_profile(self):
        """Test getting the server profile."""

        server = WBEMServer(self.conn)

        org_vm = ValueMapping.for_property(server, server.interop_ns,
                                           'CIM_RegisteredProfile',
                                           'RegisteredOrganization')

        server_profile = None

        # find server profile
        for inst in server.profiles:
            org = org_vm.tovalues(inst['RegisteredOrganization'])
            name = inst['RegisteredName']
            vers = inst['RegisteredVersion']

            if org == 'SNIA' and name == "Server" and vers == "1.2.0":
                server_profile = inst

        self.assertTrue(len(server_profile) is not None)
        try:
            ci_paths = server.get_central_instances(server_profile.path)

            for ip in ci_paths:
                server_inst = self.cimcall(self.conn.GetInstance, ip)
                if self.verbose:
                    print(server_inst.tomof())

                cls_name = server_inst.classname

                # Search class hierarchy for CIM_ObjectManager
                while cls_name != 'CIM_ObjectManager':
                    cls = self.cimcall(self.conn.GetClass, cls_name,
                                       namespace=ip.namespace)

                    if cls.superclass is not None:
                        cls_name = cls.superclass
                    else:
                        self.fail("Could not find CIM_ObjectManager")
        except Exception as exc:  # pylint: disable=broad-except
            print("Error: %s" % str(exc))
            self.fail("No Server class")

    def test_server_select_profiles(self):
        """Test the select_profiles function."""

        server = WBEMServer(self.conn)

        org_vm = ValueMapping.for_property(server, server.interop_ns,
                                           'CIM_RegisteredProfile',
                                           'RegisteredOrganization')

        if self.verbose:
            for inst in server.profiles:
                self.print_profile_info(org_vm, inst)

        indication_profiles = server.get_selected_profiles('DMTF',
                                                           'Indications')

        if self.verbose:
            print('Profiles for DMTF:Indications')
            for inst in indication_profiles:
                self.print_profile_info(org_vm, inst)

        # Test for getting multiple profiles
        # get without the function
        indication_profiles2 = []
        for inst in server.profiles:
            org = org_vm.tovalues(inst['RegisteredOrganization'])
            name = inst['RegisteredName']
            vers = inst['RegisteredVersion']
            if org == 'DMTF' and name == "Indications":
                indication_profiles2.append(inst)

        self.assertEqual(len(indication_profiles), len(indication_profiles2))

        self.assertInstancesEqual(indication_profiles, indication_profiles2)

        # test getting a single profile
        indication_profile3 = []
        for inst in server.profiles:
            org = org_vm.tovalues(inst['RegisteredOrganization'])
            name = inst['RegisteredName']
            vers = inst['RegisteredVersion']
        if org == 'DMTF' and name == "Indications" and vers == "1.1.0":
            indication_profile3.append(inst)

        if self.verbose:
            for inst in indication_profile3:
                self.print_profile_info(org_vm, inst)

        # Must return only one since specifying all parameters
        self.assertEqual(len(indication_profile3), 1)

        self.assertInstancesEqual(indication_profile3,
                                  server.get_selected_profiles('DMTF',
                                                               'Indications',
                                                               '1.1.0'))

        # test getting nothing
        self.assertEqual(len(server.get_selected_profiles('blah', 'blah')), 0)
        self.assertEqual(len(server.get_selected_profiles('blah')), 0)

    def test_create_namespace(self):
        """Test the creat_namespace method."""

        def delete_namespace(conn, ns_name, interop):
            """Delete the namespace defined by ns_name"""
            class_name = 'CIM_Namespace'
            instances = self.cimcall(conn.EnumerateInstances,
                                     class_name,
                                     namespace=interop,
                                     LocalOnly=True)
            for instance in instances:
                if ns_name == instance.properties['Name'].value:
                    try:
                        self.cimcall(conn.DeleteInstance, instance.path)
                        return
                    except Exception as ex:  # pylint: disable=broad-except
                        self.fail("Delete of created namespace failed %s " % ex)

            self.fail("new ns %s not found in namespace instances %r" %
                      (ns_name, instances))

        server = WBEMServer(self.conn)
        namespaces = server.namespaces
        interop = server.interop_ns
        for test_ns in ['root/runcimoperationstestns', 'runcimoperationns']:

            if test_ns in namespaces:
                self.fail("Test Create Namespace %s already in namespaces %s" %
                          (test_ns, namespaces))

            server.create_namespace(test_ns)

            assert test_ns in server.namespaces
            namespaces = server.namespaces
            interop2 = server.interop_ns
            assert interop2 == interop

            # test adding a qualifier decl
            qd = CIMQualifierDeclaration(u'FooQualDecl', 'string',
                                         is_array=False,
                                         value='Some string',
                                         scopes={'CLASS': True},
                                         overridable=False, tosubclass=False,
                                         translatable=False, toinstance=False)

            # Create the qualifier declaration in the server

            try:
                self.cimcall(self.conn.SetQualifier, qd, namespace=test_ns)
            except CIMError as ce:
                if ce.args[0] == CIM_ERR_NOT_SUPPORTED:
                    print('NOTE: This server/namespace does not support '
                          'SetQualifier since it returned NOT SUPPORTED')
                    return

            # get the qd and compare with original
            rtn_qd = self.cimcall(self.conn.GetQualifier, qd.name,
                                  namespace=test_ns)
            self.assertEqual(qd, rtn_qd, 'Returned qualifier declaration '
                             'did not match created')

            self.cimcall(self.conn.DeleteQualifier, qd.name, namespace=test_ns)

            delete_namespace(self.conn, test_ns, interop)

    def test_create_namespace_er(self):
        """Test error response, namespace exists"""
        server = WBEMServer(self.conn)
        interop = server.interop_ns
        try:
            server.create_namespace(interop)
            self.fail("Exception expected")
        except CIMError as ce:
            self.assertEqual(ce.status_code, CIM_ERR_ALREADY_EXISTS)


##################################################################
# Iter method tests
##################################################################

MAX_OBJECT_COUNT = 100


class IterEnumerateInstances(PegasusServerTestBase):
    """Test IterEnumerateInstances methods"""

    def run_enum_test(self, ClassName, namespace=None, LocalOnly=None,
                      DeepInheritance=None, IncludeQualifiers=None,
                      IncludeClassOrigin=None, PropertyList=None,
                      FilterQueryLanguage=None, FilterQuery=None,
                      OperationTimeout=None, ContinueOnError=None,
                      MaxObjectCount=None, ignore_value_diff=False,
                      expected_response_count=None):
        # pylint: disable=invalid-name
        """
        Run test by executing interEnumInstances, open/pull instance,
        and EnumerateInstance and compare the results.
        """

        # account for possible non unicode namespace.  Test fails in compare
        # of unicode and non-unicode namespaces otherwise.
        if namespace is not None and six.PY3:
            if isinstance(namespace, bytes):
                namespace = namespace.decode()

        # execute iterator operation
        generator = self.cimcall(self.conn.IterEnumerateInstances, ClassName,
                                 namespace=namespace, LocalOnly=LocalOnly,
                                 DeepInheritance=DeepInheritance,
                                 IncludeQualifiers=IncludeQualifiers,
                                 IncludeClassOrigin=IncludeClassOrigin,
                                 PropertyList=PropertyList,
                                 FilterQueryLanguage=FilterQueryLanguage,
                                 FilterQuery=FilterQuery,
                                 OperationTimeout=OperationTimeout,
                                 ContinueOnError=ContinueOnError,
                                 MaxObjectCount=MaxObjectCount)
        self.assertTrue(isinstance(generator, types.GeneratorType))
        iter_instances = list(generator)

        if expected_response_count is not None:
            self.assertEqual(len(iter_instances), expected_response_count)

        # execute open/pull sequence
        result = self.cimcall(self.conn.OpenEnumerateInstances, ClassName,
                              namespace=namespace,
                              DeepInheritance=DeepInheritance,
                              IncludeQualifiers=IncludeQualifiers,
                              IncludeClassOrigin=IncludeClassOrigin,
                              PropertyList=PropertyList,
                              FilterQueryLanguage=FilterQueryLanguage,
                              FilterQuery=FilterQuery,
                              OperationTimeout=OperationTimeout,
                              ContinueOnError=ContinueOnError,
                              MaxObjectCount=MaxObjectCount)
        pulled_instances = result.instances
        self.assertInstancesValid(result.instances, namespace=namespace)

        while not result.eos:
            result = self.cimcall(
                self.conn.PullInstancesWithPath, result.context,
                MaxObjectCount=MAX_OBJECT_COUNT)

            self.assertInstancesValid(result.instances, namespace=namespace)

            pulled_instances.extend(result.instances)

        if expected_response_count is not None:
            self.assertEqual(len(pulled_instances), expected_response_count)

        # ignore host if test is for pull operations disabled.
        self.assertInstancesEqual(iter_instances, pulled_instances,
                                  ignore_host=True,
                                  ignore_value_diff=ignore_value_diff)

        # execute original enumerate instances operation
        orig_instances = self.cimcall(self.conn.EnumerateInstances, ClassName,
                                      namespace=namespace, LocalOnly=LocalOnly,
                                      DeepInheritance=DeepInheritance,
                                      IncludeQualifiers=IncludeQualifiers,
                                      IncludeClassOrigin=IncludeClassOrigin,
                                      PropertyList=PropertyList)

        # compare with original instances. Ignore host here because
        # EnumerateInstances does NOT return host info
        # ignore where LocalOnly or IncludeQualifiers set because these
        # act differently between pull and original operations
        if not LocalOnly or not IncludeQualifiers:
            self.assertInstancesEqual(pulled_instances, orig_instances,
                                      ignore_host=True,
                                      ignore_value_diff=ignore_value_diff)
        else:
            self.assertEqual(len(orig_instances), len(pulled_instances))
            self.assertEqual(len(orig_instances), len(iter_instances))

    def test_simple_iter_enum(self):
        """
        Test iter class api by itself.
        Test only for valid instances.
        """
        iterator = self.cimcall(self.conn.IterEnumerateInstances, TEST_CLASS,
                                namespace=TEST_CLASS_NAMESPACE)
        iter_instances = []
        for inst in iterator:
            iter_instances.append(inst)

        self.assertInstancesValid(iter_instances,
                                  namespace=TEST_CLASS_NAMESPACE)

        # pylint: disable=protected-access
        self.assertEqual(self.conn._use_enum_inst_pull_operations, True)
        self.assertEqual(self.conn._use_enum_path_pull_operations, None)
        self.assertEqual(self.conn._use_ref_inst_pull_operations, None)
        self.assertEqual(self.conn._use_ref_path_pull_operations, None)
        self.assertEqual(self.conn._use_assoc_inst_pull_operations, None)
        self.assertEqual(self.conn._use_assoc_path_pull_operations, None)
        self.assertEqual(self.conn._use_query_pull_operations, None)

    def test_live_class_compare(self):
        """Test without extra request parameters"""
        test_class = 'CIM_ComputerSystem'
        self.run_enum_test(test_class, MaxObjectCount=100)

        # pylint: disable=protected-access
        self.assertEqual(self.conn._use_enum_inst_pull_operations, True)
        self.assertEqual(self.conn._use_enum_path_pull_operations, None)
        self.assertEqual(self.conn._use_ref_inst_pull_operations, None)
        self.assertEqual(self.conn._use_ref_path_pull_operations, None)
        self.assertEqual(self.conn._use_assoc_inst_pull_operations, None)
        self.assertEqual(self.conn._use_assoc_path_pull_operations, None)
        self.assertEqual(self.conn._use_query_pull_operations, None)

    def test_compare_ok_returns(self):
        """
        Test class that returns defined number of objects.

        All the methods should return the same thing except for the issue
        of host in the path.
        """
        expected_response_count = 200
        self.set_stress_provider_parameters(expected_response_count, 200)

        # we ignore value differences because there is at least one property
        # that changes value with time (interval)
        self.run_enum_test(TEST_PEG_STRESS_CLASSNAME,
                           namespace=TEST_PEG_STRESS_NAMESPACE,
                           MaxObjectCount=100, ignore_value_diff=True,
                           expected_response_count=expected_response_count)

        # pylint: disable=protected-access
        self.assertEqual(self.conn._use_enum_inst_pull_operations, True)
        self.assertEqual(self.conn._use_enum_path_pull_operations, None)
        self.assertEqual(self.conn._use_ref_inst_pull_operations, None)
        self.assertEqual(self.conn._use_ref_path_pull_operations, None)
        self.assertEqual(self.conn._use_assoc_inst_pull_operations, None)
        self.assertEqual(self.conn._use_assoc_path_pull_operations, None)
        self.assertEqual(self.conn._use_query_pull_operations, None)

    def test_propertylist(self):
        """Test with a propertylist."""
        expected_response_count = 200
        self.set_stress_provider_parameters(expected_response_count, 200)

        # use property list to avoide properties that change value between
        # operations
        property_list = ['Id', 'SequenceNumber', 'ResponseCount', 'S1']
        self.run_enum_test(TEST_PEG_STRESS_CLASSNAME,
                           namespace=TEST_PEG_STRESS_NAMESPACE,
                           MaxObjectCount=100, PropertyList=property_list)

        # pylint: disable=protected-access
        self.assertEqual(self.conn._use_enum_inst_pull_operations, True)
        self.assertEqual(self.conn._use_enum_path_pull_operations, None)
        self.assertEqual(self.conn._use_ref_inst_pull_operations, None)
        self.assertEqual(self.conn._use_ref_path_pull_operations, None)
        self.assertEqual(self.conn._use_assoc_inst_pull_operations, None)
        self.assertEqual(self.conn._use_assoc_path_pull_operations, None)
        self.assertEqual(self.conn._use_query_pull_operations, None)

    def test_force_original_operation(self):
        """
        Test where we force the use of the original operation.

        To force the original operation, recall self.setup with
        has_pull_operation = False

        """

        # Force a new setup to set the use_pull_operations False.
        self.setUp(use_pull_operations=False)

        expected_response_count = 10
        self.set_stress_provider_parameters(expected_response_count, 200)

        # use property list to avoid properties that change value between
        # operations
        property_list = ['Id', 'SequenceNumber', 'ResponseCount', 'S1']
        self.run_enum_test(TEST_PEG_STRESS_CLASSNAME,
                           namespace=TEST_PEG_STRESS_NAMESPACE,
                           MaxObjectCount=100, PropertyList=property_list)

        # pylint: disable=protected-access
        self.assertEqual(self.conn.use_pull_operations, False)
        self.assertEqual(self.conn._use_enum_inst_pull_operations, False)
        self.assertEqual(self.conn._use_enum_path_pull_operations, False)
        self.assertEqual(self.conn._use_ref_inst_pull_operations, False)
        self.assertEqual(self.conn._use_ref_path_pull_operations, False)
        self.assertEqual(self.conn._use_assoc_inst_pull_operations, False)
        self.assertEqual(self.conn._use_assoc_path_pull_operations, False)
        self.assertEqual(self.conn._use_query_pull_operations, False)

    def test_propertylist2(self):
        """Test with one item property list."""
        expected_response_count = 200
        self.set_stress_provider_parameters(expected_response_count, 200)

        # use property list to avoide properties that change value between
        # operations
        property_list = ['Id']
        self.run_enum_test(TEST_PEG_STRESS_CLASSNAME,
                           namespace=TEST_PEG_STRESS_NAMESPACE,
                           MaxObjectCount=100, PropertyList=property_list)

    def test_localonly(self):
        """
        Test with includequalifiers set. Only tests that the same
        number of insances returned
        """
        test_class = 'CIM_ComputerSystem'
        self.run_enum_test(test_class, MaxObjectCount=100, LocalOnly=True)

    def test_includequalifiers(self):
        """Test witho includequalifiers set True. Only tests that same
        number of instances returned
        """
        expected_response_count = 200
        self.set_stress_provider_parameters(expected_response_count, 200)

        property_list = ['Id', 'SequenceNumber', 'ResponseCount', 'S1']
        self.run_enum_test(TEST_PEG_STRESS_CLASSNAME,
                           namespace=TEST_PEG_STRESS_NAMESPACE,
                           MaxObjectCount=100, PropertyList=property_list,
                           IncludeQualifiers=True)

    def test_IncludeClassOrigin(self):  # pylint: disable=invalid-name
        """Test with IncludeClassOrigin True"""
        expected_response_count = 200
        self.set_stress_provider_parameters(expected_response_count, 200)

        property_list = ['Id', 'SequenceNumber', 'ResponseCount', 'S1']
        self.run_enum_test(TEST_PEG_STRESS_CLASSNAME,
                           namespace=TEST_PEG_STRESS_NAMESPACE,
                           MaxObjectCount=100, PropertyList=property_list,
                           IncludeClassOrigin=True)

    def test_minMaxObjectCount(self):  # pylint: disable=invalid-name
        """Test with that svr rtns correct # objects"""
        expected_response_count = 200
        self.set_stress_provider_parameters(expected_response_count, 200)

        # we ignore value differences because there is at least one property
        # that changes value with time (interval)
        property_list = ['Id', 'SequenceNumber', 'ResponseCount', 'S1']
        self.run_enum_test(TEST_PEG_STRESS_CLASSNAME,
                           namespace=TEST_PEG_STRESS_NAMESPACE,
                           MaxObjectCount=1, PropertyList=property_list,
                           IncludeClassOrigin=True)

    def test_zero_MaxObjectCount(self):  # pylint: disable=invalid-name
        """
        Test iter function with dZero MaxObjectCount.

        Use TEST_CLASS for this test.
        """
        try:
            self.run_enum_test(TEST_CLASS,
                               namespace=TEST_CLASS_NAMESPACE,
                               MaxObjectCount=0)
            self.fail('Expected exception: Non-zero MaxObjectCount required')
        except ValueError:
            pass

    # There is something broken in the following code.  It does an exception
    # on the call to the Iter... call apparently but that does not show up
    # as an exception. Traced it and the fn(...) either does not go to the
    # function or trace does not work.  In any case, this executes a good
    # response where it should fail.  It is clear that the code is not called
    # because print statements are not executed from within iter...
    # The MaxObjectCount=0 is the one difference in this code.
    # The code above works ks Nov 2016)
    # def test_zero_MaxObjectCount(self):  # pylint: disable=invalid-name
        # print('test_zero_maxobjcnt')
        # pdb.set_trace()
        # try:
            # self.cimcall(self.conn.IterEnumerateInstances, TEST_CLASS,
            #     MaxObjectCount=0)
            # self.fail('Expected exception: Non-zero MaxObjectCount required')
        # except ValueError:
            # pass

    def test_no_MaxObjectCount(self):  # pylint: disable=invalid-name
        """
        Test iter function with default MaxObjectCount.

        Use TEST_CLASS for this test.  Note that we do not use the function
        that executes all 3 calls because it does not handle the default
        MaxObjectCount.
        """
        iterator = self.cimcall(self.conn.IterEnumerateInstances,
                                TEST_CLASS, namespace=TEST_CLASS_NAMESPACE)
        iter_instances = []
        for inst in iterator:
            iter_instances.append(inst)

        self.assertInstancesValid(iter_instances)

    def test_invalid_namespace(self):
        try:
            self.run_enum_test(TEST_PEG_STRESS_CLASSNAME,
                               MaxObjectCount=1, namespace='BLAH')
            self.fail('Expected exception: invalid namespace')
        except CIMError as ce:
            if ce.args[0] != CIM_ERR_INVALID_NAMESPACE:
                raise

    def test_classname_not_found(self):
        try:
            self.run_enum_test('blah', MaxObjectCount=1,
                               namespace=TEST_PEG_STRESS_NAMESPACE)
            self.fail('Expected exception: class not found')
        except CIMError as ce:
            if ce.args[0] != CIM_ERR_INVALID_CLASS:
                raise


class IterEnumerateInstancePaths(PegasusServerTestBase):
    """Test IterEnumerateInstancePaths methods"""

    def run_enumpath_test(self, ClassName, namespace=None,
                          FilterQueryLanguage=None, FilterQuery=None,
                          OperationTimeout=None, ContinueOnError=None,
                          MaxObjectCount=None):
        # pylint: disable=invalid-name,
        """
        Run test by executing interEnumInstances, open/pull instance,
        and EnumerateInstance and compare the results.

        This is a common function used by other tests in this class.
        """

        # execute iterator operation
        generator = self.cimcall(self.conn.IterEnumerateInstancePaths,
                                 ClassName,
                                 namespace=namespace,
                                 FilterQueryLanguage=FilterQueryLanguage,
                                 FilterQuery=FilterQuery,
                                 OperationTimeout=OperationTimeout,
                                 ContinueOnError=ContinueOnError,
                                 MaxObjectCount=MaxObjectCount)
        self.assertTrue(isinstance(generator, types.GeneratorType))
        iter_paths = list(generator)

        # execute open/pull operation sequence
        result = self.cimcall(self.conn.OpenEnumerateInstancePaths, ClassName,
                              namespace=namespace,
                              FilterQueryLanguage=FilterQueryLanguage,
                              FilterQuery=FilterQuery,
                              OperationTimeout=OperationTimeout,
                              ContinueOnError=ContinueOnError,
                              MaxObjectCount=MaxObjectCount)
        pulled_paths = result.paths
        self.assertPathsValid(result.paths, namespace=namespace)

        while not result.eos:
            result = self.cimcall(
                self.conn.PullInstancePaths, result.context,
                MaxObjectCount=MAX_OBJECT_COUNT)

            self.assertPathsValid(result.paths, namespace=namespace)

            pulled_paths.extend(result.paths)

        self.assertPathsEqual(iter_paths, pulled_paths, True)

        # Execute original enumerate instance paths operation
        # Ignore host here because EnumerateInstanceNames does not return
        # it.
        orig_paths = self.cimcall(self.conn.EnumerateInstanceNames, ClassName,
                                  namespace=namespace)
        self.assertPathsValid(result.paths, namespace=namespace)

        self.assertPathsEqual(pulled_paths, orig_paths, ignore_host=True)

    def test_compare_returns(self):
        """Test without extra request parameters"""
        self.set_stress_provider_parameters(200, 200)
        self.run_enumpath_test(TEST_PEG_STRESS_CLASSNAME,
                               namespace=TEST_PEG_STRESS_NAMESPACE,
                               MaxObjectCount=100)

        # pylint: disable=protected-access
        self.assertEqual(self.conn._use_enum_inst_pull_operations, None)
        self.assertEqual(self.conn._use_enum_path_pull_operations, True)
        self.assertEqual(self.conn._use_ref_inst_pull_operations, None)
        self.assertEqual(self.conn._use_ref_path_pull_operations, None)
        self.assertEqual(self.conn._use_assoc_inst_pull_operations, None)
        self.assertEqual(self.conn._use_assoc_path_pull_operations, None)
        self.assertEqual(self.conn._use_query_pull_operations, None)

    def test_force_original_operation(self):
        """
        Test where we force the use of the original operation.

        To force the original operation, recall self.setup with
        has_pull_operation = False
        """

        # Force a new setup to set the use_pull_operations False.
        self.setUp(use_pull_operations=False)

        expected_response_count = 10
        self.set_stress_provider_parameters(expected_response_count, 200)

        self.run_enumpath_test(TEST_PEG_STRESS_CLASSNAME,
                               namespace=TEST_PEG_STRESS_NAMESPACE,
                               MaxObjectCount=100)

        # pylint: disable=protected-access
        self.assertEqual(self.conn.use_pull_operations, False)
        self.assertEqual(self.conn._use_enum_inst_pull_operations, False)
        self.assertEqual(self.conn._use_enum_path_pull_operations, False)
        self.assertEqual(self.conn._use_ref_inst_pull_operations, False)
        self.assertEqual(self.conn._use_ref_path_pull_operations, False)
        self.assertEqual(self.conn._use_assoc_inst_pull_operations, False)
        self.assertEqual(self.conn._use_assoc_path_pull_operations, False)
        self.assertEqual(self.conn._use_query_pull_operations, False)

    def test_zero_MaxObjectCount(self):  # pylint: disable=invalid-name
        """
        Test iter function with dZero MaxObjectCount.

        Use TEST_CLASS for this test.
        """
        try:
            self.run_enumpath_test(TEST_CLASS,
                                   namespace=TEST_CLASS_NAMESPACE,
                                   MaxObjectCount=0)
            self.fail('Expected exception: Non-zero MaxObjectCount required')
        except ValueError:
            pass

    def test_no_MaxObjectCount(self):  # pylint: disable=invalid-name
        """
        Test iter function with default MaxObjectCount.

        Use TEST_CLASS for this test.  Note that we do not use the function
        that executes all 3 calls because it does not handle the default
        MaxObjectCount.
        """
        iterator = self.cimcall(self.conn.IterEnumerateInstancePaths,
                                TEST_CLASS, namespace=TEST_CLASS_NAMESPACE)
        iter_paths = []
        for path in iterator:
            iter_paths.append(path)

        self.assertPathsValid(iter_paths)

    def test_invalid_namespace(self):
        try:
            self.run_enumpath_test(TEST_PEG_STRESS_CLASSNAME,
                                   MaxObjectCount=1, namespace='BLAH')
            self.fail('Expected exception: invalid namespace')
        except CIMError as ce:
            if ce.args[0] != CIM_ERR_INVALID_NAMESPACE:
                raise

    def test_classname_not_found(self):
        try:
            self.run_enumpath_test('blah', MaxObjectCount=1,
                                   namespace=TEST_PEG_STRESS_NAMESPACE)
            self.fail('Expected exception: class not found')
        except CIMError as ce:
            if ce.args[0] != CIM_ERR_INVALID_CLASS:
                raise


class IterReferenceInstances(PegasusServerTestBase):
    """Test IterReferenceInstancePaths methods"""

    def get_source_name(self):
        """
        Get a reference source path based on TEST_CLASS. Tests fail if
        there are no instances returned.
        """
        inst_names = self.cimcall(self.conn.EnumerateInstanceNames,
                                  TEST_CLASS)
        self.assertTrue(len(inst_names) >= 1)
        return inst_names[0]  # Pick the first returned instance

    def run_enum_test(self, InstanceName, ResultClass=None, Role=None,
                      IncludeQualifiers=None, IncludeClassOrigin=None,
                      PropertyList=None,
                      FilterQueryLanguage=None, FilterQuery=None,
                      OperationTimeout=None, ContinueOnError=None,
                      MaxObjectCount=None, pull_disabled=False):
        # pylint: disable=invalid-name,
        """
        Run test by executing interReferenceInstances, open/pull
        References, and References and compare the results.

        This is a common function used by other tests in this class.
        """
        # execute iterator operation
        generator = self.cimcall(self.conn.IterReferenceInstances,
                                 InstanceName, ResultClass=ResultClass,
                                 Role=Role, IncludeQualifiers=IncludeQualifiers,
                                 IncludeClassOrigin=IncludeClassOrigin,
                                 PropertyList=PropertyList,
                                 FilterQueryLanguage=FilterQueryLanguage,
                                 FilterQuery=FilterQuery,
                                 OperationTimeout=OperationTimeout,
                                 ContinueOnError=ContinueOnError,
                                 MaxObjectCount=MaxObjectCount)
        self.assertTrue(isinstance(generator, types.GeneratorType))
        iter_instances = list(generator)

        # execute pull operation
        result = self.cimcall(self.conn.OpenReferenceInstances,
                              InstanceName, ResultClass=ResultClass, Role=Role,
                              IncludeQualifiers=IncludeQualifiers,
                              IncludeClassOrigin=IncludeClassOrigin,
                              PropertyList=PropertyList,
                              FilterQueryLanguage=FilterQueryLanguage,
                              FilterQuery=FilterQuery,
                              OperationTimeout=OperationTimeout,
                              ContinueOnError=ContinueOnError,
                              MaxObjectCount=MaxObjectCount)
        pulled_instances = result.instances
        self.assertInstancesValid(result.instances)

        while not result.eos:
            result = self.cimcall(
                self.conn.PullInstancesWithPath, result.context,
                MaxObjectCount=MAX_OBJECT_COUNT)

            self.assertInstancesValid(result.instances)
            pulled_instances.extend(result.instances)

        # execute original enumerate instance paths operation
        orig_instances = self.cimcall(self.conn.References, InstanceName,
                                      ResultClass=ResultClass, Role=Role,
                                      IncludeQualifiers=IncludeQualifiers,
                                      IncludeClassOrigin=IncludeClassOrigin,
                                      PropertyList=PropertyList)

        # cannot depend on equal instances when IncludeQualifiers set
        if not IncludeQualifiers:
            self.assertInstancesEqual(pulled_instances, orig_instances)
            self.assertInstancesEqual(iter_instances, pulled_instances,
                                      ignore_host=pull_disabled)
        else:
            self.assertEqual(len(orig_instances), len(pulled_instances))
            self.assertEqual(len(orig_instances), len(iter_instances))

    def test_compare_returns(self):
        """Test without extra request parameters"""
        self.run_enum_test(self.get_source_name(), MaxObjectCount=100)

        # pylint: disable=protected-access
        self.assertEqual(self.conn._use_enum_inst_pull_operations, None)
        self.assertEqual(self.conn._use_enum_path_pull_operations, None)
        self.assertEqual(self.conn._use_ref_inst_pull_operations, True)
        self.assertEqual(self.conn._use_ref_path_pull_operations, None)
        self.assertEqual(self.conn._use_assoc_inst_pull_operations, None)
        self.assertEqual(self.conn._use_assoc_path_pull_operations, None)
        self.assertEqual(self.conn._use_query_pull_operations, None)

    def test_force_original_operation(self):
        """
        Test where we force the use of the original operation.

        To force the original operation, recall self.setup with
        has_pull_operation = False

        """

        # Force a new setup to set the use_pull_operations False.
        self.setUp(use_pull_operations=False)

        self.run_enum_test(self.get_source_name(),
                           MaxObjectCount=100, pull_disabled=True)

        # pylint: disable=protected-access
        self.assertEqual(self.conn.use_pull_operations, False)
        self.assertEqual(self.conn._use_enum_inst_pull_operations, False)
        self.assertEqual(self.conn._use_enum_path_pull_operations, False)
        self.assertEqual(self.conn._use_ref_inst_pull_operations, False)
        self.assertEqual(self.conn._use_ref_path_pull_operations, False)
        self.assertEqual(self.conn._use_assoc_inst_pull_operations, False)
        self.assertEqual(self.conn._use_assoc_path_pull_operations, False)
        self.assertEqual(self.conn._use_query_pull_operations, False)

    def test_propertylist(self):
        """Test with a propertylist."""

        # use property list to avoide properties that change value between
        # operations
        property_list = ['CreationClassName', 'Name', 'PrimaryOwnerName']
        self.run_enum_test(self.get_source_name(),
                           MaxObjectCount=100, PropertyList=property_list)

        # pylint: disable=protected-access
        self.assertEqual(self.conn._use_enum_inst_pull_operations, None)
        self.assertEqual(self.conn._use_enum_path_pull_operations, None)
        self.assertEqual(self.conn._use_ref_inst_pull_operations, True)
        self.assertEqual(self.conn._use_ref_path_pull_operations, None)
        self.assertEqual(self.conn._use_assoc_inst_pull_operations, None)
        self.assertEqual(self.conn._use_assoc_path_pull_operations, None)
        self.assertEqual(self.conn._use_query_pull_operations, None)

    def test_includequalifier(self):
        """Test with IncludeQualifier set"""
        property_list = ['CreationClassName', 'Name', 'PrimaryOwnerName']
        self.run_enum_test(self.get_source_name(),
                           MaxObjectCount=100, PropertyList=property_list)

    def test_zero_MaxObjectCount(self):  # pylint: disable=invalid-name
        """
        Test iter function with dZero MaxObjectCount.

        Use TEST_CLASS for this test.
        """
        try:
            self.run_enum_test(self.get_source_name(), MaxObjectCount=0)
            self.fail('Expected exception: Non-zero MaxObjectCount required')
        except ValueError:
            pass

    def test_no_MaxObjectCount(self):  # pylint: disable=invalid-name
        """Test without extra request parameters"""

        try:
            self.run_enum_test(self.get_source_name())
            self.fail('Expected exception: MaxObjectCount required')
        except ValueError:
            pass

    def test_pywbem_person_noparams(self):
        """
        Test OpenReferencesWithPath PyWBEM_Person class
        and no associator filter parameters
        """
        if not self.pywbem_person_class_exists():
            return

        # get all instances of the class
        inst_paths = self.cimcall(self.conn.EnumerateInstanceNames,
                                  PYWBEM_PERSON_CLASS)
        self.assertTrue(len(inst_paths) >= 1)

        # for each returned instance, execute  test sequence to get
        # all instances
        for path in inst_paths:
            self.run_enum_test(path, MaxObjectCount=100)


class IterReferenceInstancePaths(PegasusServerTestBase):
    """Test IterReferenceInstancePaths methods"""

    def get_source_name(self):
        """
        Get a reference source path
        """
        inst_names = self.cimcall(self.conn.EnumerateInstanceNames,
                                  TEST_CLASS)
        self.assertTrue(len(inst_names) >= 1)
        return inst_names[0]  # Pick the first returned instance

    def run_enumpath_test(self, InstanceName, ResultClass=None, Role=None,
                          FilterQueryLanguage=None, FilterQuery=None,
                          OperationTimeout=None, ContinueOnError=None,
                          MaxObjectCount=None, pull_disabled=False):
        # pylint: disable=invalid-name,
        """
        Run test by executing interEnumInstances, open/pull instance,
        and EnumerateInstance and compare the results.

        This is a common function used by other tests in this class.
        """
        # execute iterator operation
        generator = self.cimcall(self.conn.IterReferenceInstancePaths,
                                 InstanceName, ResultClass=ResultClass,
                                 Role=Role,
                                 FilterQueryLanguage=FilterQueryLanguage,
                                 FilterQuery=FilterQuery,
                                 OperationTimeout=OperationTimeout,
                                 ContinueOnError=ContinueOnError,
                                 MaxObjectCount=MaxObjectCount)
        self.assertTrue(isinstance(generator, types.GeneratorType))
        iter_paths = list(generator)

        # execute open/pull operation sequence
        result = self.cimcall(self.conn.OpenReferenceInstancePaths,
                              InstanceName, ResultClass=ResultClass, Role=Role,
                              FilterQueryLanguage=FilterQueryLanguage,
                              FilterQuery=FilterQuery,
                              OperationTimeout=OperationTimeout,
                              ContinueOnError=ContinueOnError,
                              MaxObjectCount=MaxObjectCount)
        pulled_paths = result.paths
        self.assertPathsValid(result.paths)

        while not result.eos:
            result = self.cimcall(
                self.conn.PullInstancePaths, result.context,
                MaxObjectCount=MAX_OBJECT_COUNT)

            self.assertPathsValid(result.paths)

            pulled_paths.extend(result.paths)

        self.assertPathsEqual(iter_paths, pulled_paths,
                              ignore_host=pull_disabled)

        # execute original enumerate instance paths operation
        orig_paths = self.cimcall(self.conn.ReferenceNames, InstanceName,
                                  ResultClass=ResultClass, Role=Role)

        self.assertPathsEqual(pulled_paths, orig_paths)

    def test_compare_returns(self):
        """Test without extra request parameters"""
        instance_name = self.get_source_name()

        self.run_enumpath_test(instance_name, MaxObjectCount=100)

        # pylint: disable=protected-access
        self.assertEqual(self.conn._use_enum_inst_pull_operations, None)
        self.assertEqual(self.conn._use_enum_path_pull_operations, None)
        self.assertEqual(self.conn._use_ref_inst_pull_operations, None)
        self.assertEqual(self.conn._use_ref_path_pull_operations, True)
        self.assertEqual(self.conn._use_assoc_inst_pull_operations, None)
        self.assertEqual(self.conn._use_assoc_path_pull_operations, None)
        self.assertEqual(self.conn._use_query_pull_operations, None)

    def test_force_original_operation(self):
        """
        Test where we force the use of the original operation.

        To force the original operation, recall self.setup with
        has_pull_operation = False

        """

        # Force a new setup to set the use_pull_operations False.
        self.setUp(use_pull_operations=False)

        instance_name = self.get_source_name()

        self.run_enumpath_test(instance_name,
                               MaxObjectCount=100, pull_disabled=True)

        # pylint: disable=protected-access
        self.assertEqual(self.conn.use_pull_operations, False)
        self.assertEqual(self.conn._use_enum_inst_pull_operations, False)
        self.assertEqual(self.conn._use_enum_path_pull_operations, False)
        self.assertEqual(self.conn._use_ref_inst_pull_operations, False)
        self.assertEqual(self.conn._use_ref_path_pull_operations, False)
        self.assertEqual(self.conn._use_assoc_inst_pull_operations, False)
        self.assertEqual(self.conn._use_assoc_path_pull_operations, False)
        self.assertEqual(self.conn._use_query_pull_operations, False)

    def test_zero_MaxObjectCount(self):  # pylint: disable=invalid-name
        """
        Test iter function with dZero MaxObjectCount.

        Use TEST_CLASS for this test.
        """
        try:
            self.run_enumpath_test(TEST_CLASS_CIMNAME, MaxObjectCount=0)
            self.fail('Expected exception: Non-zero MaxObjectCount required')
        except ValueError:
            pass

    def test_no_MaxObjectCount(self):  # pylint: disable=invalid-name
        """Test without extra request parameters"""
        instance_name = self.get_source_name()

        try:
            self.run_enumpath_test(instance_name)
            self.fail('Expected exception: MaxObjectCount required')
        except ValueError:
            pass

    def test_classname_not_found(self):
        kb = {'Name': 'Foo', 'Chicken': 'Ham'}
        obj = CIMInstanceName(classname='CIM_Foo', keybindings=kb,
                              namespace='root/cimv2')
        try:
            self.run_enumpath_test(obj, MaxObjectCount=1)
            self.fail('Expected exception: class not found')
        except CIMError as ce:
            if ce.args[0] != CIM_ERR_INVALID_PARAMETER:
                raise

    def test_pywbem_person_noparams(self):
        """
        Test OpenReferencesWithPath PyWBEM_Person class
        and no associator filter parameters
        """
        if not self.pywbem_person_class_exists():
            return

        # get all instances of the class
        inst_paths = self.cimcall(self.conn.EnumerateInstanceNames,
                                  PYWBEM_PERSON_CLASS)
        self.assertTrue(len(inst_paths) >= 1)

        # for each returned instance, execute  test sequence to get
        # all instances
        for path in inst_paths:
            self.run_enumpath_test(path, MaxObjectCount=100)


class IterAssociatorInstances(PegasusServerTestBase):
    """Test IterAssociatorInstances methods"""

    def get_source_name(self):
        """
        Get a reference source path
        """
        inst_names = self.cimcall(self.conn.EnumerateInstanceNames,
                                  TEST_CLASS)
        self.assertTrue(len(inst_names) >= 1)
        return inst_names[0]  # Pick the first returned instance

    def run_enum_test(self, InstanceName, AssocClass=None,
                      ResultClass=None, Role=None,
                      ResultRole=None,
                      IncludeQualifiers=None, IncludeClassOrigin=None,
                      PropertyList=None,
                      FilterQueryLanguage=None, FilterQuery=None,
                      OperationTimeout=None, ContinueOnError=None,
                      MaxObjectCount=None, pull_disabled=False):
        # pylint: disable=invalid-name,
        """
        Run test by executing interAssociatorInstances, open/pull
        Associators, and Associators and compare the results.

        This is a common function used by other tests in this class.
        """
        # execute iterator operation
        generator = self.cimcall(self.conn.IterAssociatorInstances,
                                 InstanceName, AssocClass=AssocClass,
                                 ResultClass=ResultClass, Role=Role,
                                 ResultRole=ResultRole,
                                 IncludeQualifiers=IncludeQualifiers,
                                 IncludeClassOrigin=IncludeClassOrigin,
                                 PropertyList=PropertyList,
                                 FilterQueryLanguage=FilterQueryLanguage,
                                 FilterQuery=FilterQuery,
                                 OperationTimeout=OperationTimeout,
                                 ContinueOnError=ContinueOnError,
                                 MaxObjectCount=MaxObjectCount)
        self.assertTrue(isinstance(generator, types.GeneratorType))
        iter_instances = list(generator)

        # execute pull operation
        result = self.cimcall(self.conn.OpenAssociatorInstances,
                              InstanceName, AssocClass=AssocClass,
                              ResultClass=ResultClass, Role=Role,
                              ResultRole=ResultRole,
                              IncludeClassOrigin=IncludeClassOrigin,
                              PropertyList=PropertyList,
                              FilterQueryLanguage=FilterQueryLanguage,
                              FilterQuery=FilterQuery,
                              OperationTimeout=OperationTimeout,
                              ContinueOnError=ContinueOnError,
                              MaxObjectCount=MaxObjectCount)
        pulled_instances = result.instances
        self.assertInstancesValid(result.instances)

        while not result.eos:
            result = self.cimcall(
                self.conn.PullInstancesWithPath, result.context,
                MaxObjectCount=MAX_OBJECT_COUNT)

            self.assertInstancesValid(result.instances)
            pulled_instances.extend(result.instances)

        # execute original enumerate instance paths operation
        orig_instances = self.cimcall(self.conn.Associators, InstanceName,
                                      ResultClass=ResultClass, Role=Role,
                                      ResultRole=ResultRole,
                                      IncludeQualifiers=IncludeQualifiers,
                                      IncludeClassOrigin=IncludeClassOrigin,
                                      PropertyList=PropertyList)

        # cannot depend on equal instances if IncludeQualifiers set.
        if not IncludeQualifiers:
            self.assertInstancesEqual(pulled_instances, orig_instances)
            self.assertInstancesEqual(iter_instances, pulled_instances,
                                      ignore_host=pull_disabled)
        else:
            self.assertEqual(len(orig_instances), len(pulled_instances))
            self.assertEqual(len(orig_instances), len(iter_instances))

    def test_compare_returns(self):
        """
        Test simple IterReferenceInstances request.
        This request has no extra parameters
        """
        self.run_enum_test(self.get_source_name(), MaxObjectCount=100)

        # pylint: disable=protected-access
        self.assertEqual(self.conn._use_enum_inst_pull_operations, None)
        self.assertEqual(self.conn._use_enum_path_pull_operations, None)
        self.assertEqual(self.conn._use_ref_inst_pull_operations, None)
        self.assertEqual(self.conn._use_ref_path_pull_operations, None)
        self.assertEqual(self.conn._use_assoc_inst_pull_operations, True)
        self.assertEqual(self.conn._use_assoc_path_pull_operations, None)
        self.assertEqual(self.conn._use_query_pull_operations, None)

    def test_force_original_operation(self):
        """
        Test where we force the use of the original operation.

        To force the original operation, recall self.setup with
        has_pull_operation = False

        """

        # Force a new setup to set the use_pull_operations False.
        self.setUp(use_pull_operations=False)

        self.run_enum_test(self.get_source_name(),
                           MaxObjectCount=100, pull_disabled=True)

        # pylint: disable=protected-access
        self.assertEqual(self.conn.use_pull_operations, False)
        self.assertEqual(self.conn._use_enum_inst_pull_operations, False)
        self.assertEqual(self.conn._use_enum_path_pull_operations, False)
        self.assertEqual(self.conn._use_ref_inst_pull_operations, False)
        self.assertEqual(self.conn._use_ref_path_pull_operations, False)
        self.assertEqual(self.conn._use_assoc_inst_pull_operations, False)
        self.assertEqual(self.conn._use_assoc_path_pull_operations, False)
        self.assertEqual(self.conn._use_query_pull_operations, False)

    def test_propertylist(self):
        """Test with a propertylist."""

        # use property list to avoide properties that change value between
        # operations
        property_list = ['CreationClassName', 'Name', 'PrimaryOwnerName']
        self.run_enum_test(self.get_source_name(),
                           MaxObjectCount=100, PropertyList=property_list)

        # pylint: disable=protected-access
        self.assertEqual(self.conn._use_enum_inst_pull_operations, None)
        self.assertEqual(self.conn._use_enum_path_pull_operations, None)
        self.assertEqual(self.conn._use_ref_inst_pull_operations, None)
        self.assertEqual(self.conn._use_ref_path_pull_operations, None)
        self.assertEqual(self.conn._use_assoc_inst_pull_operations, True)
        self.assertEqual(self.conn._use_assoc_path_pull_operations, None)
        self.assertEqual(self.conn._use_query_pull_operations, None)

    def test_includequalifier(self):
        """Test with IncludeQualifier set"""
        property_list = ['CreationClassName', 'Name', 'PrimaryOwnerName']
        self.run_enum_test(self.get_source_name(),
                           MaxObjectCount=100, IncludeQualifiers=True,
                           PropertyList=property_list)

    def test_zero_MaxObjectCount(self):  # pylint: disable=invalid-name
        """
        Test iter function with dZero MaxObjectCount.

        Use TEST_CLASS for this test.
        """
        try:
            self.run_enum_test(self.get_source_name(), MaxObjectCount=0)
            self.fail('Expected exception: Non-zero MaxObjectCount required')
        except ValueError:
            pass

    def test_no_MaxObjectCount(self):  # pylint: disable=invalid-name
        """Test without extra request parameters"""

        try:
            self.run_enum_test(self.get_source_name())
            self.fail('Expected exception: MaxObjectCount required')
        except ValueError:
            pass

    def test_pywbem_person_noparams(self):
        """
        Test OpenReferencesWithPath PyWBEM_Person class
        and no associator filter parameters
        """
        if not self.pywbem_person_class_exists():
            return

        # get all instances of the class
        inst_paths = self.cimcall(self.conn.EnumerateInstanceNames,
                                  PYWBEM_PERSON_CLASS)
        self.assertTrue(len(inst_paths) >= 1)

        # for each returned instance, execute  test sequence to get
        # all instances
        for path in inst_paths:
            self.run_enum_test(path, MaxObjectCount=100)


# TODO confirm that this should be pegasus
class IterAssociatorInstancePaths(PegasusServerTestBase):
    """Test IterAssociatorInstancePaths methods"""

    def get_source_name(self):
        """
        Get a reference source path
        """
        inst_names = self.cimcall(self.conn.EnumerateInstanceNames,
                                  TEST_CLASS)
        self.assertTrue(len(inst_names) >= 1)
        return inst_names[0]  # Pick the first returned instance

    def run_enumpath_test(self, InstanceName, AssocClass=None,
                          ResultClass=None, Role=None,
                          ResultRole=None,
                          FilterQueryLanguage=None, FilterQuery=None,
                          OperationTimeout=None, ContinueOnError=None,
                          MaxObjectCount=None, pull_disabled=False):
        # pylint: disable=invalid-name,
        """
        Run test by executing interAssociatorInstancePaths, open/pull
        AssociatorPaths, and AssociatorNames and compare the results.

        This is a common function used by other tests in this class.
        """
        # execute iterator operation
        generator = self.cimcall(self.conn.IterAssociatorInstancePaths,
                                 InstanceName, AssocClass=AssocClass,
                                 ResultClass=ResultClass, Role=Role,
                                 ResultRole=Role,
                                 FilterQueryLanguage=FilterQueryLanguage,
                                 FilterQuery=FilterQuery,
                                 OperationTimeout=OperationTimeout,
                                 ContinueOnError=ContinueOnError,
                                 MaxObjectCount=MaxObjectCount)
        self.assertTrue(isinstance(generator, types.GeneratorType))
        iter_paths = list(generator)

        # execute pull operation
        result = self.cimcall(self.conn.OpenAssociatorInstancePaths,
                              InstanceName, AssocClass=AssocClass,
                              ResultClass=ResultClass, Role=Role,
                              ResultRole=ResultRole,
                              FilterQueryLanguage=FilterQueryLanguage,
                              FilterQuery=FilterQuery,
                              OperationTimeout=OperationTimeout,
                              ContinueOnError=ContinueOnError,
                              MaxObjectCount=MaxObjectCount)
        pulled_paths = result.paths
        self.assertPathsValid(result.paths)

        while not result.eos:
            result = self.cimcall(
                self.conn.PullInstancePaths, result.context,
                MaxObjectCount=MAX_OBJECT_COUNT)

            self.assertPathsValid(result.paths)

            pulled_paths.extend(result.paths)

        self.assertPathsEqual(iter_paths, pulled_paths,
                              ignore_host=pull_disabled)

        # execute original enumerate instance paths operation
        orig_paths = self.cimcall(self.conn.AssociatorNames, InstanceName,
                                  AssocClass=ResultRole,
                                  ResultClass=ResultClass, Role=Role,
                                  ResultRole=ResultRole)

        self.assertPathsEqual(pulled_paths, orig_paths)

    def test_compare_returns(self):
        """Test without extra request parameters"""
        instance_name = self.get_source_name()

        self.run_enumpath_test(instance_name, MaxObjectCount=100)

        # pylint: disable=protected-access
        self.assertEqual(self.conn._use_enum_inst_pull_operations, None)
        self.assertEqual(self.conn._use_enum_path_pull_operations, None)
        self.assertEqual(self.conn._use_ref_inst_pull_operations, None)
        self.assertEqual(self.conn._use_ref_path_pull_operations, None)
        self.assertEqual(self.conn._use_assoc_inst_pull_operations, None)
        self.assertEqual(self.conn._use_assoc_path_pull_operations, True)
        self.assertEqual(self.conn._use_query_pull_operations, None)

    def test_force_original_operation(self):
        """
        Test where we force the use of the original operation.

        To force the original operation, recall self.setup with
        has_pull_operation = False

        """

        # Force a new setup to set the use_pull_operations False.
        self.setUp(use_pull_operations=False)

        instance_name = self.get_source_name()

        self.run_enumpath_test(instance_name,
                               MaxObjectCount=100, pull_disabled=True)

        # pylint: disable=protected-access
        self.assertEqual(self.conn.use_pull_operations, False)
        self.assertEqual(self.conn._use_enum_inst_pull_operations, False)
        self.assertEqual(self.conn._use_enum_path_pull_operations, False)
        self.assertEqual(self.conn._use_ref_inst_pull_operations, False)
        self.assertEqual(self.conn._use_ref_path_pull_operations, False)
        self.assertEqual(self.conn._use_assoc_inst_pull_operations, False)
        self.assertEqual(self.conn._use_assoc_path_pull_operations, False)
        self.assertEqual(self.conn._use_query_pull_operations, False)

    def test_zero_MaxObjectCount(self):  # pylint: disable=invalid-name
        """
        Test iter function with dZero MaxObjectCount.

        Use TEST_CLASS for this test.
        """
        try:
            self.run_enumpath_test(TEST_CLASS_CIMNAME, MaxObjectCount=0)
            self.fail('Expected exception: Non-zero MaxObjectCount required')
        except ValueError:
            pass

    def test_no_MaxObjectCount(self):  # pylint: disable=invalid-name
        """Test without extra request parameters"""
        instance_name = self.get_source_name()

        try:
            self.run_enumpath_test(instance_name)
            self.fail('Expected exception: MaxObjectCount required')
        except ValueError:
            pass

    def test_classname_not_found(self):
        kb = {'Name': 'Foo', 'Chicken': 'Ham'}
        obj = CIMInstanceName(classname='CIM_Foo', keybindings=kb,
                              namespace='root/cimv2')
        try:
            self.run_enumpath_test(obj, MaxObjectCount=1)
            self.fail('Expected exception: class not found')
        except CIMError as ce:
            if ce.args[0] != CIM_ERR_INVALID_PARAMETER:
                raise

    def test_pywbem_person_noparams(self):
        """
        Test OpenReferencesWithPath PyWBEM_Person class
        and no associator filter parameters
        """
        if not self.pywbem_person_class_exists():
            return

        # get all instances of the class
        inst_paths = self.cimcall(self.conn.EnumerateInstanceNames,
                                  PYWBEM_PERSON_CLASS)
        self.assertTrue(len(inst_paths) >= 1)

        # for each returned instance, execute  test sequence to get
        # all instances
        for path in inst_paths:
            self.run_enumpath_test(path, MaxObjectCount=100)


class IterQueryInstances(PegasusServerTestBase):

    def test_simple_iter_queryinstances(self):  # pylint: disable=invalid-name
        try:
            # Simplest invocation

            result = self.cimcall(self.conn.IterQueryInstances,
                                  'WQL',
                                  'Select * from %s' % TEST_CLASS,
                                  MaxObjectCount=100)
            self.assertEqual(result.query_result_class, None)
            count = 0
            for inst in result.generator:
                count += 1
                self.assertTrue(isinstance(inst, CIMInstance))

            self.assertTrue(count != 0)
            # pylint: disable=protected-access
            self.assertEqual(self.conn._use_enum_inst_pull_operations, None)
            self.assertEqual(self.conn._use_enum_path_pull_operations, None)
            self.assertEqual(self.conn._use_ref_inst_pull_operations, None)
            self.assertEqual(self.conn._use_ref_path_pull_operations, None)
            self.assertEqual(self.conn._use_assoc_inst_pull_operations, None)
            self.assertEqual(self.conn._use_assoc_path_pull_operations, None)
            self.assertEqual(self.conn._use_query_pull_operations, True)

        except CIMError as ce:
            if ce.args[0] == CIM_ERR_NOT_SUPPORTED:
                raise AssertionError(
                    "CIM_ERR_NOT_SUPPORTED: The WBEM server doesn't"
                    " support OpenQueryInstances for this query")
            if ce.args[0] == CIM_ERR_QUERY_LANGUAGE_NOT_SUPPORTED:
                raise AssertionError(
                    "CIM_ERR_QUERY_LANGUAGE_NOT_SUPPORTED: The WBEM"
                    " server doesn't support WQL for ExecQuery")

            raise

    def test_zeroopen_iterexecquery(self):
        try:

            # Simplest invocation
            result = self.cimcall(self.conn.IterQueryInstances,
                                  'WQL',
                                  'Select * from %s' % TEST_CLASS)

            self.assertEqual(result.query_result_class, None)
            count = 0
            for inst in result.generator:
                count += 1
                self.assertTrue(isinstance(inst, CIMInstance))
            self.assertTrue(count != 0)
            # pylint: disable=protected-access
            self.assertEqual(self.conn._use_enum_inst_pull_operations, None)
            self.assertEqual(self.conn._use_enum_path_pull_operations, None)
            self.assertEqual(self.conn._use_ref_inst_pull_operations, None)
            self.assertEqual(self.conn._use_ref_path_pull_operations, None)
            self.assertEqual(self.conn._use_assoc_inst_pull_operations, None)
            self.assertEqual(self.conn._use_assoc_path_pull_operations, None)
            self.assertEqual(self.conn._use_query_pull_operations, True)

        except CIMError as ce:
            if ce.args[0] == CIM_ERR_NOT_SUPPORTED:
                raise AssertionError(
                    "CIM_ERR_NOT_SUPPORTED: The WBEM server doesn't"
                    " support OpenQueryInstances for this query")
            if ce.args[0] == CIM_ERR_QUERY_LANGUAGE_NOT_SUPPORTED:
                raise AssertionError(
                    "CIM_ERR_QUERY_LANGUAGE_NOT_SUPPORTED: The WBEM"
                    " server doesn't support WQL for ExecQuery")

            raise

    def test_original_execquery(self):
        """Set to use original operation and retry request"""
        try:
            # Force a new setup to set the use_pull_operations False.
            self.setUp(use_pull_operations=False)

            # Simplest invocation
            result = self.cimcall(self.conn.IterQueryInstances,
                                  'WQL',
                                  'Select * from %s' % TEST_CLASS)

            self.assertEqual(result.query_result_class, None)
            count = 0
            for inst in result.generator:
                count += 1
                self.assertTrue(isinstance(inst, CIMInstance))
            self.assertTrue(count != 0)
            # pylint: disable=protected-access
            self.assertEqual(self.conn._use_enum_inst_pull_operations, False)
            self.assertEqual(self.conn._use_enum_path_pull_operations, False)
            self.assertEqual(self.conn._use_ref_inst_pull_operations, False)
            self.assertEqual(self.conn._use_ref_path_pull_operations, False)
            self.assertEqual(self.conn._use_assoc_inst_pull_operations, False)
            self.assertEqual(self.conn._use_assoc_path_pull_operations, False)
            self.assertEqual(self.conn._use_query_pull_operations, False)

        except CIMError as ce:
            if ce.args[0] == CIM_ERR_NOT_SUPPORTED:
                raise AssertionError(
                    "CIM_ERR_NOT_SUPPORTED: The WBEM server doesn't"
                    " support OpenQueryInstances for this query")
            if ce.args[0] == CIM_ERR_QUERY_LANGUAGE_NOT_SUPPORTED:
                raise AssertionError(
                    "CIM_ERR_QUERY_LANGUAGE_NOT_SUPPORTED: The WBEM"
                    " server doesn't support WQL for ExecQuery")

            raise


RECEIVED_INDICATION_COUNT = 0
COUNTER_LOCK = threading.Lock()


# pylint: disable=unused-argument
def consume_indication(indication, host):
    """This function is called when an indication is received.
        It counts indications received into a global counter. It is used by
        tests in the PyWBEMListenerClass
    """

    # pylint: disable=global-variable-not-assigned
    # pylint: disable=global-statement
    global RECEIVED_INDICATION_COUNT
    # increment count.
    with COUNTER_LOCK:
        RECEIVED_INDICATION_COUNT += 1


class TestSubscriptionsClass(PyWBEMServerClass):
    """Test the management of indications with the listener class.
       All of these functions depend on existence of a WBEM server to
       which subscriptions/filters are sent."""

    def create_listener(self):
        """ Standard test method to start a listener. Creates a listener
            with predefined callback resets the RECEIVED_INDICATION_COUNTER
            and starts the listener.

            Returns the active listener object.
        """
        # Set arbitrary ports for the listener
        test_http_listener = True
        http_listener_port = 50000
        https_listener_port = None

        try:
            if test_http_listener:
                url = '%s:%s' % (self.conn.url, http_listener_port)
            else:
                url = '%s:%s' % (self.conn.url, https_listener_port)

            # pylint: disable=attribute-defined-outside-init
            self.listener_url = url

            listener_addr = urlparse(self.system_url).netloc

            listener = WBEMListener(listener_addr,
                                    http_port=http_listener_port,
                                    https_port=https_listener_port)

            listener.add_callback(consume_indication)

            # pylint: disable=global-statement
            global RECEIVED_INDICATION_COUNT
            # increment count.
            with COUNTER_LOCK:
                RECEIVED_INDICATION_COUNT = 0

            listener.start()
        except Exception as ex:  # pylint: disable=broad-except
            self.fail('CreateListener failed with exception %r' % ex)

        return listener

    def pegasus_send_indications(self, class_name, requested_count):
        """
        Send method to OpenPegasus server to create  required number of
        indications. This is a pegasus specific class and method
        Function sends indications, tests received count, and waits for
        all indications to be received.

        Terminates early if not all received in time

        Returns True if all received. Else returns False.
        """

        result = self.cimcall(self.conn.InvokeMethod,
                              "SendTestIndicationsCount",
                              class_name,
                              [('indicationSendCount',
                                Uint32(requested_count))])

        if result[0] != 0:
            self.fail('Error: invokemethod to create indication. result = %s'
                      % result[0])

        # wait for indications to be received
        success = False
        wait_time = int(requested_count / 5) + 3
        for _ in range(wait_time):
            time.sleep(1)
            # exit the loop if all indications recieved.
            if RECEIVED_INDICATION_COUNT >= requested_count:
                success = True
                break

        # If success, wait and recheck to be sure no extra indications received.
        if success:
            time.sleep(2)
            # self.assertEqual(RECEIVED_INDICATION_COUNT, requested_count)
        if requested_count != RECEIVED_INDICATION_COUNT:
            print('Mismatch count receiving indications. Expected=%s '
                  'Received=%s' % (requested_count, RECEIVED_INDICATION_COUNT))

        return RECEIVED_INDICATION_COUNT == requested_count

    def confirm_removed(self, sub_mgr, server_id, filter_paths,
                        subscription_paths):
        """
        When filter_path and subscription path are removed, this
        confirms that results are correct both in the local subscription
        manager and the remote WBEM server.
        """
        if not isinstance(filter_paths, list):
            filter_paths = [filter_paths]

        owned_filters = sub_mgr.get_owned_filters(server_id)
        for filter_path in filter_paths:
            self.assertFalse(filter_path in owned_filters)

        # confirm not in owned subscriptions
        if not isinstance(subscription_paths, list):
            subscription_paths = [subscription_paths]

        owned_subscriptions = sub_mgr.get_owned_subscriptions(server_id)
        owned_sub_paths = [inst.path for inst in owned_subscriptions]
        for subscription_path in subscription_paths:
            self.assertFalse(subscription_path in owned_sub_paths)

        all_filters = sub_mgr.get_all_filters(server_id)
        all_filter_paths = [inst.path for inst in all_filters]
        for filter_path in filter_paths:
            self.assertFalse(filter_path in all_filter_paths)

        all_subscriptions = sub_mgr.get_all_subscriptions(server_id)
        all_sub_paths = [inst.path for inst in all_subscriptions]
        for subscription_path in subscription_paths:
            self.assertFalse(subscription_path in all_sub_paths)

    def confirm_created(self, sub_mgr, server_id, filter_path,
                        subscription_paths, owned=True):
        """
        When owned filter_path and subscription path are removed, this
        confirms that results are correct both int the local subscription
        manager and the remote WBEM server.
        """

        if owned:
            owned_filters = sub_mgr.get_owned_filters(server_id)
            owned_filter_paths = [inst.path for inst in owned_filters]
            self.assertTrue(filter_path in owned_filter_paths)

            owned_subscriptions = sub_mgr.get_owned_subscriptions(server_id)
            owned_sub_paths = [inst.path for inst in owned_subscriptions]
            for subscription_path in owned_sub_paths:
                self.assertTrue(subscription_path in owned_sub_paths)

        all_filters = sub_mgr.get_all_filters(server_id)
        all_filter_paths = [inst.path for inst in all_filters]
        self.assertTrue(filter_path in all_filter_paths)

        all_subscriptions = sub_mgr.get_all_subscriptions(server_id)
        all_sub_paths = [inst.path for inst in all_subscriptions]
        for subscription_path in subscription_paths:
            self.assertTrue(subscription_path in all_sub_paths)

    def add_peg_filter(
            self, sub_mgr, server_id, filter_id=None, name=None, owned=True):
        """
        Create a single filter definition in the sub_mgr and return it.
        This creates a filter specifically for OpenPegasus tests using the
        class/namespace information define in this method.
        """
        # pylint: disable=attribute-defined-outside-init
        self.test_class = 'Test_IndicationProviderClass'
        self.test_class_namespace = 'test/TestProvider'

        self.test_query = 'SELECT * from %s' % self.test_class
        self.test_classname = CIMClassName(self.test_class,
                                           namespace=self.test_class_namespace)

        filter_ = sub_mgr.add_filter(server_id,
                                     self.test_class_namespace,
                                     self.test_query,
                                     query_language="DMTF:CQL",
                                     filter_id=filter_id,
                                     name=name,
                                     owned=owned)
        return filter_

    @staticmethod
    def count_outstanding(sub_mgr, server_id):
        """
            Count outstanding filters, subscriptions, and destinations and
            return tuple with the counts
        """
        filters = len(sub_mgr.get_all_filters(server_id))
        subscriptions = len(sub_mgr.get_all_subscriptions(server_id))
        dests = len(sub_mgr.get_all_subscriptions(server_id))

        return (filters, subscriptions, dests)

    def get_objects_from_server(self, sub_mgr_id=None):
        """
        Using Server class, get count of Filters, Subscriptions, Destinations
        from server as confirmation outside of SubscriptionManagerCode.
        """
        this_host = getfqdn()
        server = WBEMServer(self.conn)

        dest_name_pattern = re.compile(r'^pywbemdestination:')
        dest_insts = server.conn.EnumerateInstances(
            DESTINATION_CLASSNAME, namespace=server.interop_ns)
        valid_dests = []
        for inst in dest_insts:
            if re.match(dest_name_pattern, inst.path.keybindings['Name']) \
                    and inst.path.keybindings['SystemName'] == this_host:
                valid_dests.append(inst)

        filter_instances = server.conn.EnumerateInstances(
            FILTER_CLASSNAME, namespace=server.interop_ns)
        valid_filters = []
        filter_name_pattern = re.compile(r'^pywbemfilter')
        for inst in filter_instances:
            if re.match(filter_name_pattern, inst.path.keybindings['Name']) \
                    and inst.path.keybindings['SystemName'] == this_host:
                valid_filters.append(inst)

        filter_paths = [inst.path for inst in valid_filters]
        destination_paths = [inst.path for inst in valid_dests]

        sub_insts = server.conn.EnumerateInstances(
            SUBSCRIPTION_CLASSNAME, namespace=server.interop_ns)
        valid_subscriptions = []
        for inst in sub_insts:
            if inst.path.keybindings['Filter'] in filter_paths \
                    or inst.path.keybindings['Handler'] in destination_paths:
                valid_subscriptions.append(inst)

        if self.verbose:
            print('All objects: filters=%s dests=%s subs=%s' %
                  (len(filter_instances),
                   len(dest_insts), len(sub_insts)))
            print('Pywbem objects: filters=%s dests=%s subs=%s' %
                  (len(filter_paths), len(destination_paths),
                   len(valid_subscriptions)))

        return sum([len(filter_paths), len(destination_paths),
                    len(valid_subscriptions)])

    def get_object_count(self, sub_mgr, server_id):
        """
        Return count of all filters, subscriptions, and dests
        for the defined sub_mgr and server_id. Accumulates the filter,
        subscription, dests that should represent what is in the server
        and local.
        """
        return sum(self.count_outstanding(sub_mgr, server_id))

    def empty_expected(self, sub_mgr, server_id):
        counts = self.count_outstanding(sub_mgr, server_id)
        if sum(counts) == 0:
            return True

        print('Server_id=%s. Unreleased filters=%s, subs=%s, dest=%s' %
              (server_id, counts[0], counts[1], counts[2]))
        return False

    def display_all(self, sub_mgr, server_id):
        """Display all filters, subscriptions, and destinations in the
           defined server_id
        """
        def is_owned(item, list_):
            return "is owned" if item in list_ else "not owned"

        filters = sub_mgr.get_all_filters(server_id)
        owned_filters = sub_mgr.get_owned_filters(server_id)
        if filters:
            for i, filter_ in enumerate(filters):
                print('filter %s %s %s', (i, is_owned(filter_, owned_filters),
                                          filter_,))

        subscriptions = sub_mgr.get_all_subscriptions(server_id)
        owned_subs = sub_mgr.get_owned_subscriptions(server_id)
        if subscriptions:
            for i, subscription in enumerate(subscriptions):
                print('subscription %s %s %s', (i,
                                                is_owned(subscription,
                                                         owned_subs),
                                                subscription))

        dests = sub_mgr.get_all_subscriptions(server_id)
        if dests:
            for i, dest in enumerate(dests):
                print('destination %s %s' % (i, dest))

    # pylint: disable=invalid-name
    def test_create_delete_subscription(self):
        """
        Create and delete a server and listener and create an indication.
        Then delete everything. This test does not send indications
        This is a pegasus specific test because it depends on the existence
        of pegasus specific classes and providers for subscriptions.
        """
        # TODO modify this so it is not Pegasus dependent
        if not self.is_pegasus_test_build():
            return

        server = WBEMServer(self.conn)
        sm = "test_create_delete_subscription"

        my_listener = self.create_listener()
        try:

            with WBEMSubscriptionManager(subscription_manager_id=sm) \
                    as sub_mgr:

                try:
                    server_id = sub_mgr.add_server(server)

                    sub_mgr.add_destination(
                        server_id, self.listener_url, owned=True,
                        destination_id='dest1')

                    filter_ = self.add_peg_filter(
                        sub_mgr, server_id, filter_id='filter1', owned=True)

                    subscriptions = sub_mgr.add_subscriptions(server_id,
                                                              filter_.path)
                    subscription_paths = [inst.path for inst in subscriptions]

                    self.confirm_created(sub_mgr, server_id, filter_.path,
                                         subscription_paths)

                    # confirm destination instance paths match
                    self.assertTrue(sub_mgr.get_all_destinations(server_id))
                    # TODO: ks Finish this test completely when we add other
                    #  changes for filter ids

                    sub_mgr.remove_subscriptions(server_id, subscription_paths)
                    sub_mgr.remove_filter(server_id, filter_.path)

                    self.confirm_removed(sub_mgr, server_id, filter_.path,
                                         subscription_paths)

                    self.assertEqual(self.get_object_count(sub_mgr,
                                                           server_id), 0)

                    sub_mgr.remove_server(server_id)

                except Exception as ex1:  # pylint: disable=broad-except
                    print('WBEMSubscription mgr exception %r' % ex1)

                self.assertEqual(self.get_objects_from_server(), 0)

        except Exception as ex:  # pylint: disable=broad-except
            traceback.print_exc()
            self.fail('Unexpected Exception %r' % ex)
        finally:
            my_listener.stop()

        self.assertEqual(self.get_objects_from_server(), 0)

        # TODO ks 6/16 add more tests including: multiple subscriptions, filters
        #     actual indication production, Errors. extend for ssl, test
        #     logging

    def test_create_indications(self):
        """Create a server, listener, etc. create a filter  and subscription
           and request OpenPegasus to send a set of indications to our
           consumer.  Tests that the proper set of indications received
           and then cleans up and shuts down
        """
        # exclusive to openpegasus because it uses an openpegasus test
        # provider
        if not self.is_pegasus_test_build():
            return

        requested_count = 20

        server = WBEMServer(self.conn)

        sm = 'test_create_indications'

        my_listener = self.create_listener()
        try:

            with WBEMSubscriptionManager(subscription_manager_id=sm) \
                    as sub_mgr:

                server_id = sub_mgr.add_server(server)

                sub_mgr.add_destination(
                    server_id, self.listener_url, owned=True,
                    destination_id='dest1')

                filter_ = self.add_peg_filter(
                    sub_mgr, server_id, filter_id='filter1', owned=True)

                # NOTE: The uuid from uuid4 is actually 36 char but not we
                # made it  30-40 in case the format changes in future.
                self.assert_regexp_matches(
                    filter_.path.keybindings['Name'],
                    r'^pywbemfilter:owned:test_create_indications:MyfilterId:'
                    r'[0-9a-f-]{30,40}\Z')
                subscriptions = sub_mgr.add_subscriptions(server_id,
                                                          filter_.path)
                subscription_paths = [inst.path for inst in subscriptions]

                self.confirm_created(sub_mgr, server_id, filter_.path,
                                     subscription_paths)

                if not self.pegasus_send_indications(self.test_classname,
                                                     requested_count):
                    print('Test "test_create_indications" rcvd unexpected '
                          'indications')

                sub_mgr.remove_subscriptions(server_id, subscription_paths)
                sub_mgr.remove_filter(server_id, filter_.path)

                self.confirm_removed(sub_mgr, server_id, filter_.path,
                                     subscription_paths)

                self.assertEqual(self.get_object_count(sub_mgr, server_id), 0)

                sub_mgr.remove_server(server_id)

        except Exception as ex:  # pylint: disable=broad-except
            traceback.print_exc()
            self.fail('Unexpected Exception %r' % ex)

        finally:
            my_listener.stop()

        self.assertEqual(self.get_objects_from_server(), 0)

    def test_no_subscription_id(self):
        """Test to confirm that subscriptions must have id property"""

        try:
            # pylint: disable=no-value-for-parameter
            WBEMSubscriptionManager()
            self.fail("Test should fail with TypeError")
        except TypeError:
            pass

    def test_no_filter_id(self):
        """ Test requirement for filter to have an ID"""

        server = WBEMServer(self.conn)

        sub_mgr = WBEMSubscriptionManager(subscription_manager_id='fred2')
        server_id = sub_mgr.add_server(server)

        try:
            sub_mgr.add_filter(server_id,
                               "blah",
                               "blah",
                               query_language="DMTF:CQL",)
        except ValueError:
            pass

    def test_id_attributes(self):
        """
        Test the use of subscription_manager_id and filter_id identifiers.
        Validates that they are created correctly
        """

        if not self.is_pegasus_test_build():
            return

        server = WBEMServer(self.conn)

        my_listener = self.create_listener()
        try:

            sm = 'test_id_attributes'
            with WBEMSubscriptionManager(subscription_manager_id=sm) as sub_mgr:

                server_id = sub_mgr.add_server(server)
                sub_mgr.add_destination(
                    server_id, self.listener_url, owned=True,
                    destination_id='dest1')

                filter_ = self.add_peg_filter(
                    sub_mgr, server_id, filter_id='filter1', owned=True)

                subscriptions = sub_mgr.add_subscriptions(server_id,
                                                          filter_.path)
                subscription_paths = [inst.path for inst in subscriptions]

                owned_filters = sub_mgr.get_owned_filters(server_id)
                owned_filter_paths = [inst.path for inst in owned_filters]
                self.assertEqual(len(owned_filter_paths), 1)

                for path in owned_filter_paths:
                    name = path.keybindings['Name']
                    self.assert_regexp_matches(
                        name,
                        r'^pywbemfilter:owned:test_id_attributes:fred:' +
                        r'[0-9a-f-]{30,40}\Z')
                self.assertTrue(filter_.path in owned_filter_paths)

                # Confirm format of second dynamic filter name property
                filter2 = self.add_peg_filter(
                    sub_mgr, server_id, filter_id='test_id_attributes1',
                    owned=True)

                self.assert_regexp_matches(
                    filter2.path.keybindings['Name'],
                    r'^pywbemfilter:owned:test_id_attributes:' +
                    r'test_id_attributes1:[0-9a-f-]{30,40}\Z')

                # Confirm valid id with filter that contains no name
                filter3 = sub_mgr.add_filter(
                    server_id, self.test_class_namespace, self.test_query,
                    query_language="DMTF:CQL", filter_id='test_id_attributes2')

                self.assert_regexp_matches(
                    filter3.path.keybindings['Name'],
                    r'^pywbemfilter:owned:test_id_attributes:' +
                    r'test_id_attributes2:[0-9a-f-]{30,40}\Z')

                # test to confirm fails on bad name (i.e. with : character)
                try:
                    sub_mgr.add_filter(
                        server_id, self.test_class_namespace, self.test_query,
                        query_language="DMTF:CQL", filter_id='fr:ed')
                    self.fail("Should fail this operation")
                except ValueError:
                    pass

                owned_filters = sub_mgr.get_owned_filters(server_id)
                self.assertEqual(len(owned_filters), 3)

                owned_subscriptions = sub_mgr.get_owned_subscriptions(server_id)
                owned_sub_paths = [inst.path for inst in owned_subscriptions]
                for subscription_path in subscription_paths:
                    self.assertTrue(subscription_path in owned_sub_paths)

                sub_mgr.remove_subscriptions(server_id, subscription_paths)
                sub_mgr.remove_filter(server_id, filter_.path)

                # confirm that filter and subscription were removed
                owned_filters = sub_mgr.get_owned_filters(server_id)
                owned_filter_paths = [inst.path for inst in owned_filters]
                self.assertFalse(filter_.path in owned_filter_paths)

                owned_subscriptions = sub_mgr.get_owned_subscriptions(server_id)
                owned_sub_paths = [inst.path for inst in owned_subscriptions]
                for subscription_path in subscription_paths:
                    self.assertFalse(subscription_path in owned_sub_paths)

                self.assertEqual(self.get_object_count(sub_mgr, server_id), 2)

                sub_mgr.remove_server(server_id)

            with WBEMSubscriptionManager(subscription_manager_id=sm) as sub_mgr:
                server_id = sub_mgr.add_server(server)
                self.assertEqual(self. get_object_count(sub_mgr, server_id), 0)

        except Exception as ex:  # pylint: disable=broad-except
            traceback.print_exc()
            self.fail('Unexpected Exception %r' % ex)
        finally:
            my_listener.stop()

        self.assertEqual(self.get_objects_from_server(), 0)

    def test_id_attributes2(self):
        """
        Test the use of filter_id identifiers. Test filter_id with no
        subscription_manager.id
        """
        # TODO Future: modify this so it is not Pegasus dependent
        if not self.is_pegasus_test_build():
            return

        server = WBEMServer(self.conn)

        my_listener = self.create_listener()
        try:

            sm = 'test_id_attributes2'
            with WBEMSubscriptionManager(subscription_manager_id=sm) as sub_mgr:

                server_id = sub_mgr.add_server(server)
                sub_mgr.add_destination(
                    server_id, self.listener_url, owned=True,
                    destination_id='dest1')

                filter_ = self.add_peg_filter(
                    sub_mgr, server_id, filter_id='filter1', owned=True)

                subscriptions = sub_mgr.add_subscriptions(server_id,
                                                          filter_.path)
                subscription_paths = [inst.path for inst in subscriptions]

                owned_filters = sub_mgr.get_owned_filters(server_id)
                owned_filter_paths = [inst.path for inst in owned_filters]

                self.assertEqual(len(owned_filter_paths), 1)
                for path in owned_filter_paths:
                    name = path.keybindings['Name']
                    self.assert_regexp_matches(
                        name,
                        r'^pywbemfilter:owned:test_id_attributes2:fred:' +
                        r'[0-9a-f-]{30,40}\Z')
                self.assertTrue(filter_.path in owned_filter_paths)

                sub_mgr.remove_subscriptions(server_id, subscription_paths)
                sub_mgr.remove_filter(server_id, filter_.path)

                # confirm that filter and subscription were removed
                owned_filters = sub_mgr.get_owned_filters(server_id)

                self.assertFalse(filter_.path in owned_filters)

                owned_subscriptions = sub_mgr.get_owned_subscriptions(server_id)
                for subscription_path in subscription_paths:
                    self.assertFalse(subscription_path in owned_subscriptions)

                self.assertEqual(self. get_object_count(sub_mgr, server_id), 0)

                sub_mgr.remove_server(server_id)

            with WBEMSubscriptionManager(subscription_manager_id=sm) as sub_mgr:
                server_id = sub_mgr.add_server(server)
                self.assertEqual(self. get_object_count(sub_mgr, server_id), 0)

        except Exception as ex:  # pylint: disable=broad-except
            traceback.print_exc()
            self.fail('Unexpected Exception %r' % ex)
        finally:
            my_listener.stop()

        self.assertEqual(self.get_objects_from_server(), 0)

    def test_not_owned_indications(self):
        """Create a server, listener, etc. create a filter  and subscription
           for not owned indications.  Test that they are created work and
           then are removed.
        """
        if not self.is_pegasus_test_build():
            return

        requested_count = 200

        server = WBEMServer(self.conn)
        sm = 'test_not_owned_indications'

        my_listener = self.create_listener()
        try:
            # TODO should we context this sub_mgr
            sub_mgr = WBEMSubscriptionManager(subscription_manager_id=sm)
            server_id = sub_mgr.add_server(server)

            # Create non-owned subscription
            dests = sub_mgr.add_destination(
                server_id, self.listener_url, owned=False, name='name1')
            dest_paths = [inst.path for inst in dests]

            filter_ = self.add_peg_filter(
                sub_mgr, server_id, name='name1', owned=False)

            subscriptions = sub_mgr.add_subscriptions(
                server_id,
                filter_.path,
                destination_paths=dest_paths,
                owned=False)
            subscription_paths = [inst.path for inst in subscriptions]

            self.confirm_created(sub_mgr, server_id, filter_.path,
                                 subscription_paths, owned=False)

            self.assertTrue(self.pegasus_send_indications(self.test_classname,
                                                          requested_count),
                            'Send indications failed. Counts did not match')

            sub_mgr.remove_subscriptions(server_id, subscription_paths)
            sub_mgr.remove_filter(server_id, filter_.path)
            sub_mgr.remove_destinations(server_id, dest_paths)

            self.confirm_removed(sub_mgr, server_id, filter_.path,
                                 subscription_paths)

            self.assertEqual(self.get_object_count(sub_mgr, server_id), 0)

            sub_mgr.remove_server(server_id)

            # double check for instances retrieved from server
            with WBEMSubscriptionManager(subscription_manager_id=sm) as sub_mgr:
                server_id = sub_mgr.add_server(server)
                self.assertEqual(self. get_object_count(sub_mgr, server_id), 0)

        except Exception as ex:  # pylint: disable=broad-except
            traceback.print_exc()
            self.fail('Unexpected Exception %r' % ex)
        finally:
            my_listener.stop()

        self.assertEqual(self.get_objects_from_server(), 0)

    def test_not_owned_indications2(self):
        # pylint: disable=too-many-locals
        """Create a server, listener, etc. create a filter  and subscription
           and request OpenPegasus to send a set of indications to our
           consumer.  Tests that the proper set of indications received
           and then cleans up and shuts down.
           In this test shut down the subscription manager with the
           subscriptions outstanding and then restart the manager and get
           the subscriptions from the wbem server.
        """

        if not self.is_pegasus_test_build():
            return

        requested_count = 20

        server = WBEMServer(self.conn)
        sm = 'test_not_owned_indications2'
        my_listener = self.create_listener()
        try:

            with WBEMSubscriptionManager(subscription_manager_id=sm) as sub_mgr:
                server_id = sub_mgr.add_server(server)

                # Create non-owned subscription
                dests = sub_mgr.add_destination(
                    server_id, self.listener_url, owned=False, name='name1')
                dest_paths = [inst.path for inst in dests]

                filter_ = self.add_peg_filter(
                    sub_mgr, server_id, name='name1', owned=False)

                subscriptions = sub_mgr.add_subscriptions(
                    server_id,
                    filter_.path,
                    destination_paths=dest_paths,
                    owned=False)

                subscription_paths = [inst.path for inst in subscriptions]

                self.confirm_created(sub_mgr, server_id, filter_.path,
                                     subscription_paths, owned=False)

                self.assertTrue(
                    self.pegasus_send_indications(self.test_classname,
                                                  requested_count),
                    'send Indications test failed')

                sub_mgr.remove_server(server_id)

            # Stop the subscription manager and start a new subscription
            # manager.  Confirm that subscription still exists and then
            # delete it.
            self.assertEqual(self.get_objects_from_server(), 3)

            sub_mgr2 = WBEMSubscriptionManager(
                subscription_manager_id='testNotOwnedStillThere')

            server_id = sub_mgr2.add_server(server)

            # The filter, etc. paths should still be in place in the server
            self.confirm_created(sub_mgr2, server_id, filter_.path,
                                 subscription_paths, owned=False)

            self.assertEqual(self.get_object_count(sub_mgr2, server_id), 3)

            # For some reason server returns too many instances here.
            # there is some memory in server we are not seeing.
            # self.assertTrue(self.pegasus_send_indications(self.test_classname,
            #                                              requested_count),
            #                'send Indications test failed')
            self.pegasus_send_indications(self.test_classname, requested_count)

            sub_mgr2.remove_subscriptions(server_id, subscription_paths)
            sub_mgr2.remove_filter(server_id, filter_.path)
            sub_mgr2.remove_destinations(server_id, dest_paths)

            self.confirm_removed(sub_mgr2, server_id, filter_.path,
                                 subscription_paths)

            self.assertEqual(self.get_object_count(sub_mgr2, server_id), 0)

            sub_mgr2.remove_server(server_id)

            # double check for instances retrieved from server. Should
            # be None
            with WBEMSubscriptionManager(subscription_manager_id=sm) as sub_2:
                server_id = sub_2.add_server(server)
                self.assertEqual(self. get_object_count(sub_2, server_id), 0)

        except Exception as ex:  # pylint: disable=broad-except
            traceback.print_exc()
            self.fail('Unexpected Exception %r' % ex)
        finally:
            my_listener.stop()

        self.assertEqual(self.get_objects_from_server(), 0)

    def test_both_indications(self):  # pylint: disable=too-many-locals
        """Create a server, listener, etc. create a filter  and subscription
           and request OpenPegasus to send a set of indications to our
           consumer.  Tests that the proper set of indications received
           and then cleans up and shuts down
        """

        if not self.is_pegasus_test_build():
            return

        requested_count = 1

        server = WBEMServer(self.conn)

        my_listener = self.create_listener()
        try:

            try:
                sub_mgr = WBEMSubscriptionManager(
                    subscription_manager_id='test_both_indications')
                server_id = sub_mgr.add_server(server)

                sub_mgr.add_destination(
                    server_id, self.listener_url, owned=True,
                    destination_id='dest1')

                filter_owned = self.add_peg_filter(
                    sub_mgr, server_id, filter_id='filter1', owned=True)

                subscriptions_owned = sub_mgr.add_subscriptions(
                    server_id, filter_owned.path)
                subscription_paths_owned = [inst.path for inst in
                                            subscriptions_owned]

                self.confirm_created(sub_mgr, server_id, filter_owned.path,
                                     subscription_paths_owned)

                # Create non-owned dest, filter, subscription

                n_owned_dests = sub_mgr.add_destination(
                    server_id, self.listener_url, owned=False, name='name1')
                n_owned_dest_paths = [inst.path for inst in n_owned_dests]

                n_owned_filter = self.add_peg_filter(
                    sub_mgr, server_id, name='name1', owned=False)

                n_owned_subscriptions = sub_mgr.add_subscriptions(
                    server_id,
                    n_owned_filter.path,
                    destination_paths=n_owned_dest_paths,
                    owned=False)

                n_owned_subscription_paths = [inst.path for inst in
                                              n_owned_subscriptions]

                self.confirm_created(sub_mgr, server_id, n_owned_filter.path,
                                     n_owned_subscription_paths, owned=False)

                # TODO Pegasus Issue.  Why does this code cause 8 indications
                # to be produced most of the time.
                if not self.pegasus_send_indications(self.test_classname,
                                                     requested_count * 8):
                    print('Test "test_both_indications" rcvd unexpected '
                          'indications')

            # Force the finally to remove all filters, subscriptions, etc.
            # both owned and not_owned.
            finally:
                # Remove owned subscriptions
                sub_mgr.remove_subscriptions(server_id,
                                             subscription_paths_owned)
                sub_mgr.remove_filter(server_id, filter_owned.path)

                self.confirm_removed(sub_mgr, server_id, filter_owned.path,
                                     subscription_paths_owned)

                # remove not owned subscriptions, etc.

                sub_mgr.remove_subscriptions(server_id,
                                             n_owned_subscription_paths)
                sub_mgr.remove_filter(server_id, n_owned_filter.path)
                sub_mgr.remove_destinations(server_id, n_owned_dest_paths)

                self.confirm_removed(sub_mgr, server_id, n_owned_filter.path,
                                     n_owned_subscription_paths)

                if not self.empty_expected(sub_mgr, server_id):
                    self.display_all(sub_mgr, server_id)

                self.assertEqual(self.get_object_count(sub_mgr, server_id), 0)

                sub_mgr.remove_server(server_id)

        except Exception as ex:  # pylint: disable=broad-except
            traceback.print_exc()
            self.fail('Unexpected Exception %r' % ex)
        finally:
            my_listener.stop()

        self.assertEqual(self.get_objects_from_server(), 0)

    def test_subscription_context_manager(self):
        """Test that the WBEMSUbscriptionmanager class can be used as a
           Python context manager and that its exit method cleans up.
        """

        if not self.is_pegasus_test_build():
            return

        server = WBEMServer(self.conn)

        # First, verify the behavior of remove_all_servers() with a
        # normal WBEMSubscriptionManager instance.

        sub_mgr = WBEMSubscriptionManager(
            subscription_manager_id='test_ctxt_mgr_1')

        server_id = sub_mgr.add_server(server)
        # pylint: disable=protected-access
        self.assertEqual(set(sub_mgr._servers.keys()), {server_id})

        sub_mgr.remove_all_servers()
        # pylint: disable=protected-access
        self.assertEqual(len(sub_mgr._servers.keys()), 0)

        # Now, perform the actual test of the context manager.

        # pylint: disable=bad-continuation
        with WBEMSubscriptionManager(
                subscription_manager_id='test_ctxt_mgr_2') as sub_mgr:

            server_id = sub_mgr.add_server(server)
            # pylint: disable=protected-access
            self.assertEqual(set(sub_mgr._servers.keys()), {server_id})

        # confirm that context manager cleared servers.
        self.assertEqual(len(sub_mgr._servers.keys()), 0)


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

    # PullOperations
    'PullEnumerateInstancePaths',
    'PullEnumerateInstances',
    'PullAssociators',
    'PullAssociatorPaths',
    'PullReferences',
    'PullReferencePaths',
    'PullQueryInstances',

    # iter operations
    'IterEnumerateInstancePaths',
    'IterEnumerateInstances',
    'IterAssociators',
    'IterAssociatorPaths',
    'IterReferences',
    'IterReferencePaths',
    'IterQueryInstances',

    # TestServerClass
    'PyWBEMServerClass',

    # Test Indication Subscriptions and processing
    'PyWEBEMSubscriptionClass',

    # Pegasus only tests
    'PEGASUSCLITestClass',
    'PegasusTestEmbeddedInstance',
    'PegasusInteropTest',
    'PegasusTestEmbeddedInstance'
    ]  # noqa: E123


def parse_args(argv_):
    # pylint: disable=too-many-branches, too-many-statements
    argv = list(argv_)

    if len(argv) <= 1:
        print('Error: No arguments specified; Call with --help or -h for '
              'usage.')
        sys.exit(2)
    elif argv[1] == '--help' or argv[1] == '-h':
        print('')
        print('Test program for CIM operations.')
        print('')
        print('Usage:')
        print('    %s [GEN_OPTS] URL [USERNAME%%PASSWORD [UT_OPTS '
              '[UT_CLASS ...]]] ' % argv[0])
        print('')
        print('Where:')
        print('    GEN_OPTS            General options (see below).')
        print('    URL                 URL of the target WBEM server.\n'
              '                        http:// or https:// prefix\n'
              '                        defines ssl usage')
        print('    USERNAME            Userid used to log into WBEM server.\n'
              '                        Requests user input if not supplied')
        print('    PASSWORD            Password used to log into\n'
              '                        WBEM server.\n'
              '                        Requests user input if not supplier')
        print('    -nvc                Do not verify server certificates.')
        print('    --cacerts           File/dir with ca certificate(s).')
        print('    --yamlfile yamlfile  Test_client YAML file to be recorded.')
        print('    --stats             If set, statistics are generated')
        print('                        and displayed.')
        print('    UT_OPTS             Unittest options (see below).')
        print('    UT_CLASS            Name of testcase class (e.g.\n'
              '                        EnumerateInstances).')
        print('')
        print('General options[GEN_OPTS]:')
        print('    --help, -h          Display this help text.')
        print('    -n NAMESPACE        Use this CIM namespace instead of '
              'default: %s' % DEFAULT_NAMESPACE)
        print('    -t TIMEOUT          Use this timeout (in seconds) instead\n'
              '                        of no timeout\n')
        print('    -v                  Verbose output which includes:\n'
              '                          - connection details,\n'
              '                          - details of tests')
        print('    -d                  Debug flag for extra displays:\n'
              '                          - xml input and output, if -v set.\n')
        print('    -l                  Do long running tests. If not set,\n'
              '                        skips a number of tests that take a\n'
              '                        long time to run')
        print('    --log               Log all operations and http to file.\n'
              '                        run_cim_operations.log.\n'
              '                        Any existing log is renamed with .bak\n'
              '                        suffix.')
        print('    -hl                 List of individual tests')

        print('')
        print('Examples:')
        print('    %s https://9.10.11.12 username%%password' % argv[0])
        print('    %s --log https://myhostusername%%password' % argv[0])
        print('    %s -v http://localhost username%%password'
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
    args_['yamlfile'] = None
    args_['long_running'] = None
    args_['stats'] = None
    args_['log'] = False

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
        elif argv[1] == '--stats':
            args_['stats'] = True
            del argv[1:2]
        elif argv[1] == '-l':
            args_['long_running'] = True
            del argv[1:2]
        elif argv[1] == '--yamlfile':
            args_['yamlfile'] = argv[2]
            del argv[1:3]
        elif argv[1] == '--log':
            args_['log'] = True
            del argv[1:2]
        elif argv[1] == '-hl':
            args_['debug'] = True
            del argv[1:2]
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


def main():
    # pylint: disable=global-statement
    global SKIP_LONGRUNNING_TEST, CLI_ARGS

    CLI_ARGS, sys.argv = parse_args(sys.argv)  # pylint: disable=invalid-name
    if CLI_ARGS['verbose']:
        print("Using WBEM Server:")
        print("  server url: %s" % CLI_ARGS['url'])
        print("  namespace: %s" % CLI_ARGS['namespace'])
        print("  username: %s" % CLI_ARGS['username'])
        print("  password: %s" % ("*" * len(CLI_ARGS['password'])))
        print("  nvc: %s" % CLI_ARGS['nvc'])
        print("  cacerts: %s" % CLI_ARGS['cacerts'])
        print("  timeout: %s" % CLI_ARGS['timeout'])
        print("  verbose: %s" % CLI_ARGS['verbose'])
        print("  stats: %s" % CLI_ARGS['stats'])
        print("  debug: %s" % CLI_ARGS['debug'])
        print("  yamlfile: %s" % CLI_ARGS['yamlfile'])
        print("  log: %s" % CLI_ARGS['log'])
        print("  long_running: %s" % CLI_ARGS['long_running'])

        if CLI_ARGS['long_running'] is True:
            SKIP_LONGRUNNING_TEST = False

    # if yamlfile  or log file exists rename them with .bak suffix
    if CLI_ARGS['yamlfile']:
        yamlfile_name = CLI_ARGS['yamlfile']
        if os.path.isfile(yamlfile_name):
            backupfile_name = '%s.bak' % yamlfile_name
            if os.path.isfile(backupfile_name):
                os.remove(backupfile_name)
            os.rename(yamlfile_name, backupfile_name)

    if CLI_ARGS['log']:
        if os.path.isfile(RUN_CIM_OPERATIONS_OUTPUT_LOG):
            backupfile_name = '%s.bak' % RUN_CIM_OPERATIONS_OUTPUT_LOG
            if os.path.isfile(backupfile_name):
                os.remove(backupfile_name)
            os.rename(RUN_CIM_OPERATIONS_OUTPUT_LOG, backupfile_name)

    # Note: unittest options are defined in separate args after
    # the url argument.

    unittest.main()


if __name__ == '__main__':
    main()
