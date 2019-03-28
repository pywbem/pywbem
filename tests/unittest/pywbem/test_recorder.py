#!/usr/bin/env python

"""
Unit test recorder functions.

"""

from __future__ import absolute_import, print_function

# Allows use of lots of single character variable names.
# pylint: disable=invalid-name,missing-docstring,too-many-statements
# pylint: disable=too-many-lines,no-self-use
import os
import os.path
import logging
import logging.handlers
from io import open as _open

import unittest2 as unittest  # we use @skip introduced in py27
import six
from testfixtures import LogCapture, log_capture
# Enabled only to display a tree of loggers
# from logging_tree import printout as logging_tree_printout
import yaml
try:
    from collections import OrderedDict
except ImportError:
    from ordereddict import OrderedDict

from pywbem import CIMInstanceName, CIMInstance, \
    Uint8, Uint16, Uint32, Uint64, Sint8, Sint16, \
    Sint32, Sint64, Real32, Real64, CIMProperty, CIMDateTime, CIMError, \
    HTTPError, WBEMConnection, LogOperationRecorder, configure_logger
# Renamed the following import to not have py.test pick it up as a test class:
from pywbem import TestClientRecorder as _TestClientRecorder
from pywbem.cim_operations import pull_path_result_tuple, pull_inst_result_tuple
from pywbem._utils import _format
from pywbem_mock import FakedWBEMConnection

from ..utils.dmtf_mof_schema_def import install_test_dmtf_schema


TEST_DIR = os.path.dirname(__file__)

# test outpuf file for the recorder tests.  This is opened for each
# test to save yaml output and may be reloaded during the same test
# to confirm the yaml results.
TEST_YAML_FILE = os.path.join(TEST_DIR, 'test_recorder.yaml')

TEST_OUTPUT_LOG = os.path.join(TEST_DIR, 'test_recorder.log')

VERBOSE = False


class BaseRecorderTests(unittest.TestCase):
    """Base class for recorder unit tests. Implements methods
       for creating instance and instancename
    """

    def create_ciminstance(self, set_path=False):
        """
        Create a sample instance with multiple properties and
        property types.
        """

        props_input = OrderedDict([
            ('S1', b'Ham'),
            ('Bool', True),
            ('UI8', Uint8(42)),
            ('UI16', Uint16(4216)),
            ('UI32', Uint32(4232)),
            ('UI64', Uint64(4264)),
            ('SI8', Sint8(-42)),
            ('SI16', Sint16(-4216)),
            ('SI32', Sint32(-4232)),
            ('SI64', Sint64(-4264)),
            ('R32', Real32(42.0)),
            ('R64', Real64(42.64)),
            ('S2', u'H\u00E4m'),  # U+00E4 = lower case a umlaut
            # CIMDateTime.__repr__() output changes between Python versions,
            # so we omit that from these properties. After all, this is not a
            # test for a correct repr() of all CIM datatypes, but a test of
            # the recorder with a long string.
        ])

        inst = CIMInstance('CIM_Foo', props_input)
        if set_path:
            inst.path = self.create_ciminstancename()
        return inst

    def create_ciminstancename(self):
        kb = [('Chicken', 'Ham')]
        obj_name = CIMInstanceName('CIM_Foo',
                                   kb,
                                   namespace='root/cimv2',
                                   host='woot.com')
        return obj_name

    def create_ciminstances(self):
        """Create multiple instances using """
        instances = []
        instances.append(self.create_ciminstance(set_path=True))
        instances.append(self.create_ciminstance(set_path=True))
        return instances

    def create_ciminstancepaths(self):
        """Create multiple instances using """
        paths = []
        paths.append(self.create_ciminstancename())
        paths.append(self.create_ciminstancename())
        return paths

    def create_method_params(self):
        """Create a set of method params to be used in InvokeMethodTests."""
        obj_name = self.create_ciminstancename()

        params = [('StringParam', 'Spotty'),
                  ('Uint8', Uint8(1)),
                  ('Sint8', Sint8(2)),
                  ('Uint16', Uint16(3)),
                  ('Sint16', Sint16(3)),
                  ('Uint32', Uint32(4)),
                  ('Sint32', Sint32(5)),
                  ('Uint64', Uint64(6)),
                  ('Sint64', Sint64(7)),
                  ('Real32', Real32(8)),
                  ('Real64', Real64(9)),
                  ('Bool', True),
                  ('Ref', obj_name)]
        # CIMDateTime.__repr__() output changes between Python
        # versions, so we omit any datetime parameters. After all,
        # this is not a test for a correct repr() of all CIM
        # datatypes, but a test of the recorder with a long string.
        return params


class ClientRecorderTests(BaseRecorderTests):
    """
    Common base for all tests on the TestClientRecorder. Defines specific common
    methods including setUp and tearDown for the TestClientRecorder.
    """
    def setUp(self):
        """ Setup recorder instance including defining output file"""
        self.testyamlfile = os.path.join(TEST_DIR, TEST_YAML_FILE)
        if os.path.isfile(self.testyamlfile):
            os.remove(self.testyamlfile)

        self.yamlfp = _TestClientRecorder.open_file(self.testyamlfile, 'a')

        self.test_recorder = _TestClientRecorder(self.yamlfp)
        self.test_recorder.reset()
        self.test_recorder.enable()

    def tearDown(self):
        """Close the test_client YAML file."""
        if self.yamlfp is not None:
            self.yamlfp.close()

    def closeYamlFile(self):
        """Close the yaml file if it is open"""
        if self.yamlfp is not None:
            self.yamlfp.close()
            self.yamlfp = None

    def loadYamlFile(self):
        """Load any created yaml file"""
        self.closeYamlFile()
        with _open(self.testyamlfile, encoding="utf-8") as fp:
            testyaml = yaml.safe_load(fp)
        return testyaml


class ToYaml(ClientRecorderTests):
    """Test the toyaml function with multiple data input"""
    def test_inst_to_yaml_simple(self):
        """Test Simple instancename toyaml conversion"""

        test_yaml = self.test_recorder.toyaml(self.create_ciminstancename())

        self.assertEqual(test_yaml['pywbem_object'], 'CIMInstanceName')
        self.assertEqual(test_yaml['classname'], 'CIM_Foo')
        self.assertEqual(test_yaml['namespace'], 'root/cimv2')
        kb = test_yaml['keybindings']
        self.assertEqual(kb['Chicken'], 'Ham')

        # CIMClass, cimqualifierdecl

    def test_to_yaml_simple2(self):
        """Test Simple cimdatetime and other primitive types to toyaml"""

        test_yaml = self.test_recorder.toyaml(
            CIMDateTime('20140924193040.654321+120'))

        self.assertEqual(test_yaml, '20140924193040.654321+120')

        self.assertEqual(self.test_recorder.toyaml(True), True)
        self.assertEqual(self.test_recorder.toyaml(False), False)
        self.assertEqual(self.test_recorder.toyaml(1234), 1234)
        self.assertEqual(self.test_recorder.toyaml('blahblah '), 'blahblah ')

    def test_inst_to_yaml_all_prop_types(self):
        """Test all property types toyaml"""

        inst = self.create_ciminstance()

        test_yaml = self.test_recorder.toyaml(inst)

        self.assertEqual(test_yaml['pywbem_object'], 'CIMInstance')
        self.assertEqual(test_yaml['classname'], 'CIM_Foo')
        properties = test_yaml['properties']

        si64 = properties['SI64']
        self.assertEqual(si64['name'], 'SI64')
        self.assertEqual(si64['type'], 'sint64')
        self.assertEqual(si64['value'], -4264)

        # TODO add test for reference properties
        # TODO add test for embedded object property

    def test_inst_to_yaml_array_props(self):
        """Test  property with array toyaml"""
        str_data = "The pink fox jumped over the big blue dog"
        array_props = [
            ('MyString', str_data),
            ('MyUint8Array', [Uint8(1), Uint8(2)]),
            ('MySint8Array', [Sint8(1), Sint8(2)]),
            ('MyUint64Array', [Uint64(123456789),
                               Uint64(123456789),
                               Uint64(123456789)]),
            ('MyUint32Array', [Uint32(9999), Uint32(9999)]),
            ('MyStrLongArray', [str_data, str_data, str_data]),
        ]
        inst = CIMInstance('CIM_FooArray', array_props)
        test_yaml = self.test_recorder.toyaml(inst)

        self.assertEqual(test_yaml['pywbem_object'], 'CIMInstance')
        self.assertEqual(test_yaml['classname'], 'CIM_FooArray')
        properties = test_yaml['properties']
        my_string = properties['MyString']
        self.assertEqual(my_string['name'], 'MyString')
        self.assertEqual(my_string['type'], 'string')
        self.assertEqual(my_string['value'], str_data)

        my_uint8array = properties['MyUint8Array']
        self.assertEqual(my_uint8array['name'], 'MyUint8Array')
        self.assertEqual(my_uint8array['type'], 'uint8')
        self.assertEqual(my_uint8array['value'], [Uint8(1), Uint8(2)])

        my_sint8array = properties['MySint8Array']
        self.assertEqual(my_sint8array['name'], 'MySint8Array')
        self.assertEqual(my_sint8array['type'], 'sint8')
        self.assertEqual(my_sint8array['value'], [Sint8(1), Sint8(2)])

        my_sint64array = properties['MyUint64Array']
        self.assertEqual(my_sint64array['name'], 'MyUint64Array')
        self.assertEqual(my_sint64array['type'], 'uint64')
        self.assertEqual(my_sint64array['value'], [Uint64(123456789),
                                                   Uint64(123456789),
                                                   Uint64(123456789)])

    def test_instname_to_yaml(self):
        """Test  instname toyaml"""

        inst_name = self.create_ciminstancename()

        test_yaml = self.test_recorder.toyaml(inst_name)

        self.assertEqual(test_yaml['pywbem_object'], 'CIMInstanceName')
        self.assertEqual(test_yaml['classname'], 'CIM_Foo')
        # TODO host does not appear in output yaml. Is that correct???
        # ##self.assertEqual[test_yaml['host'], 'woot.com']
        kbs = test_yaml['keybindings']
        self.assertEqual(len(kbs), 1)
        self.assertEqual(kbs['Chicken'], 'Ham')

    def test_openreq_resulttuple(self):
        """test tuple result from open operation. The input is a
        named tuple.
        """
        result = []
        context = ('test_rtn_context', 'root/cim_namespace')
        result_tuple = pull_path_result_tuple(result, True, None)

        test_yaml = self.test_recorder.toyaml(result_tuple)

        self.assertEqual(test_yaml['paths'], [])
        self.assertEqual(test_yaml['eos'], True)
        self.assertEqual(test_yaml['context'], None)

        result_tuple = pull_path_result_tuple(result, False, context)

        test_yaml = self.test_recorder.toyaml(result_tuple)

        self.assertEqual(test_yaml['paths'], [])
        self.assertEqual(test_yaml['eos'], False)
        self.assertEqual(test_yaml['context'], list(context))


class ClientOperationStageTests(ClientRecorderTests):
    """
    Test staging for different cim_operations.  This defines fixed
    parameters for the before and after staging, stages (which creates
    a yaml file), and then inspects that file to determine if valid
    yaml was created
    """

    def test_invoke_method(self):
        """
        Emulates call to invokemethod to test parameter processing.
        Currently creates the pywbem_request component.
        Each test emulated a single cim operation with fixed data to
        create the input for the yaml, create the yaml, and test the result
        """
        params = self.create_method_params()
        in_params_dict = OrderedDict(params)
        obj_name = in_params_dict['Ref']

        self.test_recorder.stage_pywbem_args(method='InvokeMethod',
                                             MethodName='Blah',
                                             ObjectName=obj_name,
                                             Params=params)
        method_result_tuple = None
        method_exception = None

        self.test_recorder.stage_pywbem_result(method_result_tuple,
                                               method_exception)

        self.test_recorder.record_staged()

        # reload the yaml to test created values
        test_yaml = self.loadYamlFile()
        test_yaml = test_yaml[0]

        pywbem_request = test_yaml['pywbem_request']
        self.assertEqual(pywbem_request['url'], 'http://acme.com:80')

        operation = pywbem_request['operation']
        self.assertEqual(operation['pywbem_method'], 'InvokeMethod')
        self.assertEqual(operation['MethodName'], 'Blah')
        out_params_dict = OrderedDict(operation['Params'])

        self.assertEqual(len(in_params_dict), len(out_params_dict))

        self.assertEqual(out_params_dict['StringParam'], 'Spotty')
        self.assertEqual(out_params_dict['Uint8'], 1)
        self.assertEqual(out_params_dict['Sint8'], 2)
        self.assertEqual(out_params_dict['Uint16'], 3)
        self.assertEqual(out_params_dict['Sint16'], 3)
        self.assertEqual(out_params_dict['Uint32'], 4)
        self.assertEqual(out_params_dict['Sint32'], 5)
        self.assertEqual(out_params_dict['Uint64'], 6)
        self.assertEqual(out_params_dict['Sint64'], 7)
        self.assertEqual(out_params_dict['Real32'], 8)
        self.assertEqual(out_params_dict['Real64'], 9)
        self.assertEqual(out_params_dict['Bool'], True)
        # TODO fix the following. Currently it fails with:
        # AssertionError: CIMIn[16 chars]name={'classname': 'CIM_Foo',
        # 'keybindings': {[132 chars]None) != CIMIn[16 chars]name=u'CIM_Foo',
        # keybindings=NocaseDict({('Chi[55 chars]com')
        # self.assertEqual(CIMInstanceName(out_params_dict['Ref']), obj_name)

    def test_get_instance(self):
        """
        Emulates call to getInstance to test parameter processing.
        Currently creates the pywbem_request component.
        """
        InstanceName = self.create_ciminstancename()

        self.test_recorder.reset()

        self.test_recorder.stage_pywbem_args(
            method='GetInstance',
            InstanceName=InstanceName,
            LocalOnly=True,
            IncludeQualifiers=True,
            IncludeClassOrigin=True,
            PropertyList=['propertyblah'])

        instance = None
        exc = None

        self.test_recorder.stage_pywbem_result(instance, exc)

        self.test_recorder.record_staged()

        test_yaml = self.loadYamlFile()
        test_yaml = test_yaml[0]
        pywbem_request = test_yaml['pywbem_request']
        self.assertEqual(pywbem_request['url'], 'http://acme.com:80')
        operation = pywbem_request['operation']
        self.assertEqual(operation['pywbem_method'], 'GetInstance')
        self.assertEqual(operation['LocalOnly'], True)
        self.assertEqual(operation['IncludeQualifiers'], True)
        self.assertEqual(operation['PropertyList'], ['propertyblah'])
        pywbem_response = test_yaml['pywbem_response']
        self.assertEqual(pywbem_response, {})

    def test_create_instance(self):
        """Test record of create instance"""

        NewInstance = self.create_ciminstance()

        self.test_recorder.reset()

        self.test_recorder.stage_pywbem_args(
            method='CreateInstance',
            NewInstance=NewInstance,
            namespace='cim/blah')

        exc = None
        obj_name = self.create_ciminstancename()

        self.test_recorder.stage_pywbem_result(obj_name, exc)

        self.test_recorder.record_staged()

        test_yaml = self.loadYamlFile()
        test_yaml = test_yaml[0]
        pywbem_request = test_yaml['pywbem_request']
        self.assertEqual(pywbem_request['url'], 'http://acme.com:80')
        operation = pywbem_request['operation']
        self.assertEqual(operation['pywbem_method'], 'CreateInstance')
        returned_new_inst = operation['NewInstance']
        self.assertEqual(returned_new_inst['classname'], NewInstance.classname)
        pd = returned_new_inst['properties']

        # compare all properties returned against original
        self.assertEqual(len(pd), len(NewInstance.properties))
        for pn, pv in pd.items():
            prop = CIMProperty(pn, pv['value'], type=pv['type'],
                               array_size=pv['array_size'],
                               propagated=pv['propagated'],
                               is_array=pv['is_array'],
                               reference_class=pv['reference_class'],
                               qualifiers=pv['qualifiers'],
                               embedded_object=pv['embedded_object'])

            self.assertEqual(NewInstance.properties[pn], prop,
                             'Property compare failed orig %s, recreated %s' %
                             (NewInstance.properties[pn], prop))

    def test_open_enumerateInstancePaths(self):
        """Emulate staging of enumerateInstancePaths call. Tests building
        yaml for this call. Used to test the generation of context, eos
        result info.
        """
        namespace = 'root/cimv2'

        self.test_recorder.reset(pull_op=True)

        self.test_recorder.stage_pywbem_args(
            method='OpenEnumerateInstancePaths',
            ClassName='CIM_BLAH',
            namespace=namespace,
            FilterQueryLanguage='WQL',
            FilterQuery='Property = 3',
            OperationTimeout=40,
            ContinueOnError=False,
            MaxObjectCount=100)

        exc = None
        result = []
        result_tuple = pull_path_result_tuple(result, True, None)

        self.test_recorder.stage_pywbem_result(result_tuple, exc)

        self.test_recorder.record_staged()

        test_yaml = self.loadYamlFile()
        test_yaml = test_yaml[0]

        pywbem_request = test_yaml['pywbem_request']
        self.assertEqual(pywbem_request['url'], 'http://acme.com:80')
        operation = pywbem_request['operation']
        self.assertEqual(operation['pywbem_method'],
                         'OpenEnumerateInstancePaths')
        self.assertEqual(operation['ClassName'], 'CIM_BLAH')
        self.assertEqual(operation['MaxObjectCount'], 100)
        self.assertEqual(operation['FilterQueryLanguage'], 'WQL')
        self.assertEqual(operation['FilterQuery'], 'Property = 3')
        self.assertEqual(operation['ContinueOnError'], False)
        self.assertEqual(operation['OperationTimeout'], 40)

        pywbem_response = test_yaml['pywbem_response']
        pull_result = pywbem_response['pullresult']
        self.assertEqual(pull_result['paths'], [])
        self.assertEqual(pull_result['eos'], True)
        self.assertEqual(pull_result['context'], None)


################################################################
#
#           LogOperationRecorder tests
#
################################################################

class BaseLogOperationRecorderTests(BaseRecorderTests):
    """
    Test the LogOperationRecorder functions. Creates log entries and
    uses testfixture to validate results
    """
    def setUp(self):
        """
        Setup that is run before each test method.
        Shut down any existing logger and reset WBEMConnection and
        reset WBEMConnection class attributes
        """
        # pylint: disable=protected-access
        WBEMConnection._reset_logging_config()
        logging.shutdown()
        # NOTE We do not clean up handlers or logger names already defined.
        #      That should not affect the tests.

    def recorder_setup(self, detail_level=None):
        """Setup the recorder for a defined max output size"""

        configure_logger('api', log_dest='file',
                         detail_level=detail_level,
                         log_filename=TEST_OUTPUT_LOG, propagate=True)

        configure_logger('http', log_dest='file',
                         detail_level=detail_level,
                         log_filename=TEST_OUTPUT_LOG, propagate=True)

        # Define an attribute that is a single LogOperationRecorder to be used
        # in some of the tests.  Note that if detail_level is dict it is used
        # directly.
        if isinstance(detail_level, (six.string_types, six.integer_types)):
            detail_level = {'api': detail_level, 'http': detail_level}

        # pylint: disable=attribute-defined-outside-init
        # Set a conn id into the connection. Saves testing the connection
        # log for each test.
        self.test_recorder = LogOperationRecorder('test_id',
                                                  detail_levels=detail_level)
        # pylint: disable=protected-access
        self.test_recorder.reset()
        self.test_recorder.enable()

    def tearDown(self):
        """Remove LogCapture."""
        LogCapture.uninstall_all()
        logging.shutdown()
        # remove any existing log file
        if os.path.isfile(TEST_OUTPUT_LOG):
            os.remove(TEST_OUTPUT_LOG)


class LogOperationRecorderStagingTests(BaseLogOperationRecorderTests):
    """
    Test staging for different cim_operations.  This defines fixed
    parameters for the before and after staging, stages (which creates
    a yaml file), and then inspects that file to determine if valid
    yaml was created
    """

    @log_capture()
    def test_create_connection1(self, lc):
        """Create connection with default parameters"""
        # Fake the connection to create a fixed data environment
        conn = WBEMConnection('http://blah')
        # TODO AM 2018-06: Suppress the printing to stderr
        configure_logger('api', log_dest='file', detail_level='all',
                         connection=conn, log_filename=TEST_OUTPUT_LOG,
                         propagate=True)

        conn_id = conn.conn_id
        api_exp_log_id = 'pywbem.api.{0}'.format(conn_id)

        result_con = _format(
            "Connection:{0} WBEMConnection("
            "url='http://blah', "
            "creds=None, "
            "conn_id={0!A}, "
            "default_namespace='root/cimv2', "
            "x509=None, "
            "verify_callback=None, "
            "ca_certs=None, "
            "no_verification=False, "
            "timeout=None, "
            "use_pull_operations=False, "
            "stats_enabled=False, "
            "recorders=['LogOperationRecorder'])",
            conn_id)

        lc.check(
            (api_exp_log_id, 'DEBUG', result_con),
        )

    @log_capture()
    def test_create_connection2(self, lc):
        """Test log of wbem connection with detailed information"""

        x509_dict = {"cert_file": 'Certfile.x', 'key_file': 'keyfile.x'}
        conn = WBEMConnection('http://blah',
                              default_namespace='root/blah',
                              creds=('username', 'password'),
                              x509=x509_dict,
                              no_verification=True,
                              timeout=10,
                              use_pull_operations=True,
                              stats_enabled=True)
        # TODO AM 2018-06: Suppress the printing to stderr
        configure_logger('api', log_dest='file', detail_level='all',
                         connection=conn, log_filename=TEST_OUTPUT_LOG,
                         propagate=True)

        conn_id = conn.conn_id
        api_exp_log_id = 'pywbem.api.{0}'.format(conn_id)

        result_con = _format(
            "Connection:{0} WBEMConnection("
            "url='http://blah', "
            "creds=('username', ...), "
            "conn_id={0!A}, "
            "default_namespace='root/blah', "
            "x509={{'cert_file': 'Certfile.x', 'key_file': 'keyfile.x'}}, "
            "verify_callback=None, "
            "ca_certs=None, "
            "no_verification=True, "
            "timeout=10, "
            "use_pull_operations=True, "
            "stats_enabled=True, "
            "recorders=['LogOperationRecorder'])",
            conn_id)

        lc.check(
            (api_exp_log_id, 'DEBUG', result_con),
        )

    @log_capture()
    def test_create_connection_summary(self, lc):
        """Test log of wbem connection with detailed information"""

        x509_dict = {"cert_file": 'Certfile.x', 'key_file': 'keyfile.x'}
        conn = WBEMConnection('http://blah',
                              default_namespace='root/blah',
                              creds=('username', 'password'),
                              x509=x509_dict,
                              no_verification=True,
                              timeout=10,
                              use_pull_operations=True,
                              stats_enabled=True)
        # TODO AM 2018-06: Suppress the printing to stderr
        configure_logger('api', log_dest='file', detail_level='summary',
                         connection=conn, log_filename=TEST_OUTPUT_LOG,
                         propagate=True)

        conn_id = conn.conn_id
        api_exp_log_id = 'pywbem.api.{0}'.format(conn_id)

        result_con = _format(
            "Connection:{0} WBEMConnection("
            "url='http://blah', "
            "creds=('username', ...), "
            "default_namespace='root/blah', "
            "...)",
            conn_id)

        lc.check(
            (api_exp_log_id, 'DEBUG', result_con),
        )

    @log_capture()
    def test_stage_result_exception(self, lc):
        """Test the ops result log None return, HTTPError exception."""
        self.recorder_setup(detail_level=10)

        # Note: cimerror is the CIMError HTTP header field
        exc = HTTPError(500, "Fake Reason", cimerror="Fake CIMError")

        self.test_recorder.stage_pywbem_result(None, exc)

        result_exc = "Exception:test_id None('HTTPError...)"

        lc.check(
            ('pywbem.api.test_id', 'DEBUG', result_exc),
        )

    @log_capture()
    def test_stage_result_exception_all(self, lc):
        """Test the ops result log None return, HTTPError exception."""
        self.recorder_setup(detail_level='all')

        # Note: cimerror is the CIMError HTTP header field
        exc = HTTPError(500, "Fake Reason", cimerror="Fake CIMError")

        self.test_recorder.stage_pywbem_result(None, exc)

        result_exc = _format(
            "Exception:test_id None('HTTPError({0})')",
            exc)

        lc.check(
            ('pywbem.api.test_id', 'DEBUG', result_exc),
        )

    @log_capture()
    def test_stage_getinstance_args(self, lc):
        """
        Emulates call to getInstance to test parameter processing.
        Currently creates the pywbem_request component.
        """

        inst_name = self.create_ciminstancename()

        self.recorder_setup(detail_level='all')

        self.test_recorder.stage_pywbem_args(
            method='GetInstance',
            InstanceName=inst_name,
            LocalOnly=True,
            IncludeQualifiers=True,
            IncludeClassOrigin=True,
            PropertyList=['propertyblah'])

        result_req = (
            "Request:test_id GetInstance("
            "IncludeClassOrigin=True, "
            "IncludeQualifiers=True, "
            "InstanceName=CIMInstanceName("
            "classname='CIM_Foo', "
            "keybindings=NocaseDict({'Chicken': 'Ham'}), "
            "namespace='root/cimv2', host='woot.com'), "
            "LocalOnly=True, "
            "PropertyList=['propertyblah'])"
        )

        lc.check(
            ('pywbem.api.test_id', 'DEBUG', result_req),
        )

    @log_capture()
    def test_stage_instance_result(self, lc):
        instance = self.create_ciminstance()
        self.recorder_setup(detail_level=10)
        exc = None

        self.test_recorder.stage_pywbem_result(instance, exc)

        result_ret = "Return:test_id None(CIMInstanc...)"

        lc.check(
            ('pywbem.api.test_id', 'DEBUG', result_ret),
        )

    @log_capture()
    def test_stage_instance_result_default(self, lc):
        instance = self.create_ciminstance()
        # set the length in accord with the "min" definition.
        self.recorder_setup(detail_level=1000)
        exc = None

        self.test_recorder.stage_pywbem_result(instance, exc)

        result_ret = (
            "Return:test_id None(CIMInstance(classname='CIM_Foo', "
            "path=None, properties=NocaseDict({"
            "'S1': CIMProperty(name='S1', value='Ham', type='string', "
            "reference_class=None, embedded_object=None, is_array=False, "
            "array_size=None, class_origin=None, propagated=None, "
            "qualifiers=NocaseDict({})), "
            "'Bool': CIMProperty(name='Bool', value=True, "
            "type='boolean', reference_class=None, embedded_object=None, "
            "is_array=False, array_size=None, class_origin=None, "
            "propagated=None, qualifiers=NocaseDict({})), "
            "'UI8': CIMProperty(name='UI8', value=42, type='uint8', "
            "reference_class=None, embedded_object=None, is_array=False, "
            "array_size=None, class_origin=None, propagated=None, "
            "qualifiers=NocaseDict({})), "
            "'UI16': CIMProperty(name='UI16', value=4216, "
            "type='uint16', reference_class=None, embedded_object=None, "
            "is_array=False, array_size=None, class_origin=None, "
            "propagated=None, qualifiers=NocaseDict({})), "
            "'UI32': CIMProperty(name='UI32', value=4232, "
            "type='uint32', reference_class=None, embedded_object=None, "
            "is_array=False, array_size=None,...)")

        lc.check(
            ('pywbem.api.test_id', 'DEBUG', result_ret),
        )

    @log_capture()
    def test_stage_instance_result_all(self, lc):
        instance = self.create_ciminstance()
        self.recorder_setup(detail_level='all')
        exc = None

        self.test_recorder.stage_pywbem_result(instance, exc)

        result_ret = (
            "Return:test_id None(CIMInstance(classname='CIM_Foo', "
            "path=None, properties=NocaseDict({"
            "'S1': CIMProperty(name='S1', value='Ham', "
            "type='string', reference_class=None, "
            "embedded_object=None, is_array=False, array_size=None, "
            "class_origin=None, propagated=None, "
            "qualifiers=NocaseDict({})), "
            "'Bool': CIMProperty(name='Bool', value=True, "
            "type='boolean', reference_class=None, "
            "embedded_object=None, is_array=False, array_size=None, "
            "class_origin=None, propagated=None, "
            "qualifiers=NocaseDict({})), "
            "'UI8': CIMProperty(name='UI8', value=42, "
            "type='uint8', reference_class=None, embedded_object=None, "
            "is_array=False, array_size=None, class_origin=None, "
            "propagated=None, qualifiers=NocaseDict({})), "
            "'UI16': CIMProperty(name='UI16', value=4216, "
            "type='uint16', reference_class=None, embedded_object=None, "
            "is_array=False, array_size=None, class_origin=None, "
            "propagated=None, qualifiers=NocaseDict({})), "
            "'UI32': CIMProperty(name='UI32', value=4232, "
            "type='uint32', reference_class=None, embedded_object=None, "
            "is_array=False, array_size=None, class_origin=None, "
            "propagated=None, qualifiers=NocaseDict({})), "
            "'UI64': CIMProperty(name='UI64', value=4264, "
            "type='uint64', reference_class=None, embedded_object=None, "
            "is_array=False, array_size=None, class_origin=None, "
            "propagated=None, qualifiers=NocaseDict({})), "
            "'SI8': CIMProperty(name='SI8', value=-42, "
            "type='sint8', reference_class=None, embedded_object=None, "
            "is_array=False, array_size=None, class_origin=None, "
            "propagated=None, qualifiers=NocaseDict({})), "
            "'SI16': CIMProperty(name='SI16', value=-4216, "
            "type='sint16', reference_class=None, embedded_object=None, "
            "is_array=False, array_size=None, class_origin=None, "
            "propagated=None, qualifiers=NocaseDict({})), "
            "'SI32': CIMProperty(name='SI32', value=-4232, type='sint32', "
            "reference_class=None, embedded_object=None, "
            "is_array=False, array_size=None, class_origin=None, "
            "propagated=None, qualifiers=NocaseDict({})), "
            "'SI64': CIMProperty(name='SI64', value=-4264, type='sint64', "
            "reference_class=None, embedded_object=None, is_array=False, "
            "array_size=None, class_origin=None, propagated=None, "
            "qualifiers=NocaseDict({})), "
            "'R32': CIMProperty(name='R32', value=42.0, type='real32', "
            "reference_class=None, embedded_object=None, is_array=False,"
            " array_size=None, class_origin=None, propagated=None, "
            "qualifiers=NocaseDict({})), "
            "'R64': CIMProperty(name='R64', value=42.64, type='real64', "
            "reference_class=None, embedded_object=None, "
            "is_array=False, array_size=None, class_origin=None, "
            "propagated=None, qualifiers=NocaseDict({})), "
            "'S2': CIMProperty(name='S2', value='H\\u00e4m', type='string', "
            "reference_class=None, embedded_object=None, is_array=False, "
            "array_size=None, class_origin=None, propagated=None, "
            "qualifiers=NocaseDict({}))"
            "}), property_list=None, qualifiers=NocaseDict({})))")

        lc.check(
            ('pywbem.api.test_id', 'DEBUG', result_ret),
        )

    @log_capture()
    def test_stage_instance_result_inst_path(self, lc):
        instance = self.create_ciminstance(set_path=True)
        self.recorder_setup(detail_level='paths')
        exc = None

        self.test_recorder.stage_pywbem_result(instance, exc)

        result_ret = (
            "Return:test_id None("
            "'//woot.com/root/cimv2:CIM_Foo.Chicken=\"Ham\"')")

        lc.check(
            ('pywbem.api.test_id', 'DEBUG', result_ret),
        )

    @log_capture()
    def test_stage_instance_result_paths(self, lc):
        self.recorder_setup(detail_level='paths')
        instances = self.create_ciminstances()
        exc = None

        self.test_recorder.stage_pywbem_result(instances, exc)

        result_ret = (
            "Return:test_id None("
            "'//woot.com/root/cimv2:CIM_Foo.Chicken=\"Ham\"', "
            "'//woot.com/root/cimv2:CIM_Foo.Chicken=\"Ham\"')")

        lc.check(
            ('pywbem.api.test_id', 'DEBUG', result_ret),
        )

    @log_capture()
    def test_stage_instance_result_pull(self, lc):
        self.recorder_setup(detail_level='paths')
        instances = self.create_ciminstances()
        exc = None

        context = ('test_rtn_context', 'root/blah')
        result_tuple = pull_inst_result_tuple(instances, False, context)

        self.test_recorder.stage_pywbem_result(result_tuple, exc)

        result_ret = (
            "Return:test_id None(pull_inst_result_tuple("
            "context=('test_rtn_context', 'root/blah'), eos=False, "
            "instances='//woot.com/root/cimv2:CIM_Foo.Chicken=\"Ham\"', "
            "'//woot.com/root/cimv2:CIM_Foo.Chicken=\"Ham\"'))"
        )

        lc.check(
            ('pywbem.api.test_id', 'DEBUG', result_ret),
        )

    def build_http_request(self):
        """
        Build an http request for the following tests
        """
        headers = OrderedDict([
            ('CIMOperation', 'MethodCall'),
            ('CIMMethod', 'GetInstance'),
            ('CIMObject', 'root/cimv2')])
        url = 'http://blah'
        method = 'POST'
        target = '/cimom'

        payload = (
            '<?xml version="1.0" encoding="utf-8" ?>\n'
            '<CIM CIMVERSION="2.0" DTDVERSION="2.0">\n'
            '<MESSAGE ID="1001" PROTOCOLVERSION="1.0">\n'
            '<SIMPLEREQ>\n'
            '<IMETHODCALL NAME="GetInstance">\n'
            '<LOCALNAMESPACEPATH>\n'
            '<NAMESPACE NAME="root"/>\n'
            '<NAMESPACE NAME="cimv2"/>\n'
            '</LOCALNAMESPACEPATH>\n'
            '<IPARAMVALUE NAME="InstanceName">\n'
            '<INSTANCENAME CLASSNAME="PyWBEM_Person">\n'
            '<KEYBINDING NAME="Name">\n'
            '<KEYVALUE VALUETYPE="string">Fritz</KEYVALUE>\n'
            '</KEYBINDING>\n'
            '</INSTANCENAME>\n'
            '</IPARAMVALUE>\n'
            '<IPARAMVALUE NAME="LocalOnly">\n'
            '<VALUE>FALSE</VALUE>\n'
            '</IPARAMVALUE>\n'
            '</IMETHODCALL>\n'
            '</SIMPLEREQ>\n'
            '</MESSAGE>\n'
            '</CIM>)')

        return url, target, method, headers, payload

    @log_capture()
    def test_stage_http_request_all(self, lc):
        """Test stage of http_request log with detail_level='all'"""
        self.recorder_setup(detail_level='all')
        url, target, method, headers, payload = self.build_http_request()

        self.test_recorder.stage_http_request('test_id', 11, url, target,
                                              method, headers, payload)

        result_req = (
            "Request:test_id POST /cimom 11 http://blah "
            "CIMOperation:'MethodCall' "
            "CIMMethod:'GetInstance' "
            "CIMObject:'root/cimv2'\n"
            '    <?xml version="1.0" encoding="utf-8" ?>\n'
            '<CIM CIMVERSION="2.0" DTDVERSION="2.0">\n'
            '<MESSAGE ID="1001" PROTOCOLVERSION="1.0">\n'
            '<SIMPLEREQ>\n'
            '<IMETHODCALL NAME="GetInstance">\n'
            '<LOCALNAMESPACEPATH>\n'
            '<NAMESPACE NAME="root"/>\n'
            '<NAMESPACE NAME="cimv2"/>\n'
            '</LOCALNAMESPACEPATH>\n'
            '<IPARAMVALUE NAME="InstanceName">\n'
            '<INSTANCENAME CLASSNAME="PyWBEM_Person">\n'
            '<KEYBINDING NAME="Name">\n'
            '<KEYVALUE VALUETYPE="string">Fritz</KEYVALUE>\n'
            '</KEYBINDING>\n'
            '</INSTANCENAME>\n'
            '</IPARAMVALUE>\n'
            '<IPARAMVALUE NAME="LocalOnly">\n'
            '<VALUE>FALSE</VALUE>\n'
            '</IPARAMVALUE>\n'
            '</IMETHODCALL>\n'
            '</SIMPLEREQ>\n'
            '</MESSAGE>\n'
            '</CIM>)')

        lc.check(
            ('pywbem.http.test_id', 'DEBUG', result_req),
        )

    @log_capture()
    def test_stage_http_request_summary(self, lc):
        """
        Test http request log record with summary as detail level
        """
        self.recorder_setup(detail_level='summary')
        url, target, method, headers, payload = self.build_http_request()
        self.test_recorder.stage_http_request('test_id', 11, url, target,
                                              method, headers, payload)

        result_req = (
            "Request:test_id POST /cimom 11 http://blah "
            "CIMOperation:'MethodCall' "
            "CIMMethod:'GetInstance' "
            "CIMObject:'root/cimv2'\n"
            '    ')

        lc.check(
            ('pywbem.http.test_id', 'DEBUG', result_req),
        )

    @log_capture()
    def test_stage_http_request_int(self, lc):
        """
        Test http log record with integer as detail_level
        """
        self.recorder_setup(detail_level=10)

        url, target, method, headers, payload = self.build_http_request()

        self.test_recorder.stage_http_request('test_id', 11, url, target,
                                              method, headers, payload)

        result_req = (
            "Request:test_id POST /cimom 11 http://blah "
            "CIMOperation:'MethodCall' "
            "CIMMethod:'GetInstance' "
            "CIMObject:'root/cimv2'\n"
            '    <?xml vers...')

        lc.check(
            ('pywbem.http.test_id', 'DEBUG', result_req),
        )

    def build_http_response(self):
        """
        Build an http response. Builds the complete stage_http_response1
        and executes and returns the body component so each test can build
        stage_http_response2 since that is where the logging occurs
        """
        body = ('<?xml version="1.0" encoding="utf-8" ?>\n'
                '<CIM CIMVERSION="2.0" DTDVERSION="2.0">\n'
                '<MESSAGE ID="1001" PROTOCOLVERSION="1.0">\n'
                '<SIMPLERSP>\n'
                '<IMETHODRESPONSE NAME="GetInstance">\n'
                '<IRETURNVALUE>\n'
                '<INSTANCE CLASSNAME="PyWBEM_Person">\n'
                '<PROPERTY NAME="Name" TYPE="string">\n'
                '<VALUE>Fritz</VALUE>\n'
                '</PROPERTY>\n'
                '<PROPERTY NAME="Address" TYPE="string">\n'
                '<VALUE>Fritz Town</VALUE>\n'
                '</PROPERTY>\n'
                '</INSTANCE>\n'
                '</IRETURNVALUE>\n'
                '</IMETHODRESPONSE>\n'
                '</SIMPLERSP>\n'
                '</MESSAGE>\n'
                '</CIM>)\n')
        headers = OrderedDict([
            ('Content-type', 'application/xml; charset="utf-8"'),
            ('Content-length', str(len(body)))])
        status = 200
        reason = ""
        version = 11
        self.test_recorder.stage_http_response1('test_id', version,
                                                status, reason, headers)

        return body

    @log_capture()
    def test_stage_http_response_all(self, lc):
        """
        Test http response log record with 'all' detail_level
        """
        self.recorder_setup(detail_level='all')

        body = self.build_http_response()

        self.test_recorder.stage_http_response2(body)

        result_resp = (
            "Response:test_id 200: 11 "
            "Content-type:'application/xml; charset=\"utf-8\"' "
            "Content-length:'450'\n"
            '    <?xml version="1.0" encoding="utf-8" ?>\n'
            '<CIM CIMVERSION="2.0" DTDVERSION="2.0">\n'
            '<MESSAGE ID="1001" PROTOCOLVERSION="1.0">\n'
            '<SIMPLERSP>\n'
            '<IMETHODRESPONSE NAME="GetInstance">\n'
            '<IRETURNVALUE>\n'
            '<INSTANCE CLASSNAME="PyWBEM_Person">\n'
            '<PROPERTY NAME="Name" TYPE="string">\n'
            '<VALUE>Fritz</VALUE>\n'
            '</PROPERTY>\n'
            '<PROPERTY NAME="Address" TYPE="string">\n'
            '<VALUE>Fritz Town</VALUE>\n'
            '</PROPERTY>\n'
            '</INSTANCE>\n'
            '</IRETURNVALUE>\n'
            '</IMETHODRESPONSE>\n'
            '</SIMPLERSP>\n'
            '</MESSAGE>\n'
            '</CIM>)\n')

        lc.check(
            ('pywbem.http.test_id', 'DEBUG', result_resp),
        )

    @log_capture()
    def test_stage_http_response_summary(self, lc):
        """
        Test http response log record with 'all' detail_level
        """
        self.recorder_setup(detail_level='summary')

        body = self.build_http_response()

        self.test_recorder.stage_http_response2(body)

        result_resp = (
            "Response:test_id 200: 11 "
            "Content-type:'application/xml; charset=\"utf-8\"' "
            "Content-length:'450'\n"
            '    ')

        lc.check(
            ('pywbem.http.test_id', 'DEBUG', result_resp),
        )

    @log_capture()
    def test_stage_http_response_int(self, lc):
        """
        Test http response log record with 'all' detail_level
        """
        self.recorder_setup(detail_level=30)

        body = self.build_http_response()

        self.test_recorder.stage_http_response2(body)

        result_resp = (
            "Response:test_id 200: 11 "
            "Content-type:'application/xml; charset=\"utf-8\"' "
            "Content-length:'450'\n"
            '    <?xml version="1.0" encoding="...')

        lc.check(
            ('pywbem.http.test_id', 'DEBUG', result_resp),
        )


class LogOperationRecorderTests(BaseLogOperationRecorderTests):
    """
    Test args and results logging. This emulates the WBEMConnection method
    call and the response together.
    """

    @log_capture()
    def test_getinstance(self, lc):
        """Test the ops result log for get instance"""

        inst_name = self.create_ciminstancename()

        # set recorder to limit response to length of 10
        self.recorder_setup(detail_level=10)

        self.test_recorder.stage_pywbem_args(
            method='GetInstance',
            InstanceName=inst_name,
            LocalOnly=True,
            IncludeQualifiers=True,
            IncludeClassOrigin=True,
            PropertyList=['propertyblah'])
        instance = self.create_ciminstance()
        exc = None
        self.test_recorder.stage_pywbem_result(instance, exc)

        result_req = (
            "Request:test_id GetInstance(IncludeCla...)")

        result_ret = (
            "Return:test_id GetInstance(CIMInstanc...)")

        lc.check(
            ('pywbem.api.test_id', 'DEBUG', result_req),
            ('pywbem.api.test_id', 'DEBUG', result_ret),
        )

    @log_capture()
    def test_getinstance_exception(self, lc):
        """Test the ops result log for get instance"""

        inst_name = self.create_ciminstancename()

        self.recorder_setup(detail_level=11)

        self.test_recorder.stage_pywbem_args(
            method='GetInstance',
            InstanceName=inst_name,
            LocalOnly=True,
            IncludeQualifiers=True,
            IncludeClassOrigin=True,
            PropertyList=['propertyblah'])
        instance = None
        exc = CIMError(6, "Fake CIMError")
        self.test_recorder.stage_pywbem_result(instance, exc)

        result_req = (
            "Request:test_id GetInstance(IncludeClas...)")

        result_exc = (
            "Exception:test_id GetInstance('CIMError(6...)")

        lc.check(
            ('pywbem.api.test_id', 'DEBUG', result_req),
            ('pywbem.api.test_id', 'DEBUG', result_exc),
        )

    @log_capture()
    def test_getinstance_exception_all(self, lc):
        """Test the ops result log for get instance CIMError exception"""

        inst_name = self.create_ciminstancename()

        self.recorder_setup(detail_level='all')

        self.test_recorder.stage_pywbem_args(
            method='GetInstance',
            InstanceName=inst_name)
        instance = None
        exc = CIMError(6, "Fake CIMError")
        self.test_recorder.stage_pywbem_result(instance, exc)

        result_req = (
            "Request:test_id GetInstance("
            "InstanceName=CIMInstanceName("
            "classname='CIM_Foo', "
            "keybindings=NocaseDict({'Chicken': 'Ham'}), "
            "namespace='root/cimv2', host='woot.com'))")

        result_exc = _format(
            "Exception:test_id GetInstance('CIMError({0})')", exc)

        lc.check(
            ('pywbem.api.test_id', 'DEBUG', result_req),
            ('pywbem.api.test_id', 'DEBUG', result_exc),
        )

    @log_capture()
    def test_getinstance_result_all(self, lc):
        """Test the ops result log for get instance"""

        inst_name = self.create_ciminstancename()

        self.recorder_setup(detail_level='all')

        self.test_recorder.stage_pywbem_args(
            method='GetInstance',
            InstanceName=inst_name,
            LocalOnly=True,
            IncludeQualifiers=True,
            IncludeClassOrigin=True,
            PropertyList=['propertyblah'])
        instance = self.create_ciminstance()
        exc = None

        self.test_recorder.stage_pywbem_result(instance, exc)

        result_req = (
            'Request:test_id GetInstance(IncludeClassOrigin=True, '
            'IncludeQualifiers=True, '
            "InstanceName=CIMInstanceName(classname='CIM_Foo', "
            "keybindings=NocaseDict({'Chicken': 'Ham'}), "
            "namespace='root/cimv2', "
            "host='woot.com'), LocalOnly=True, "
            "PropertyList=['propertyblah'])")

        result_ret = (
            "Return:test_id GetInstance(CIMInstance(classname='CIM_Foo', "
            "path=None, properties=NocaseDict({"
            "'S1': CIMProperty(name='S1', value='Ham', type='string', "
            "reference_class=None, embedded_object=None, is_array=False, "
            "array_size=None, class_origin=None, propagated=None, "
            "qualifiers=NocaseDict({})), "
            "'Bool': CIMProperty(name='Bool', value=True, type='boolean', "
            "reference_class=None, embedded_object=None, is_array=False, "
            "array_size=None, class_origin=None, propagated=None, "
            "qualifiers=NocaseDict({})), "
            "'UI8': CIMProperty(name='UI8', value=42, type='uint8', "
            "reference_class=None, embedded_object=None, is_array=False, "
            "array_size=None, class_origin=None, propagated=None, "
            "qualifiers=NocaseDict({})), "
            "'UI16': CIMProperty(name='UI16', value=4216, type='uint16', "
            "reference_class=None, embedded_object=None, is_array=False, "
            "array_size=None, class_origin=None, propagated=None, "
            "qualifiers=NocaseDict({})), "
            "'UI32': CIMProperty(name='UI32', value=4232, type='uint32', "
            "reference_class=None, embedded_object=None, is_array=False, "
            "array_size=None, class_origin=None, propagated=None, "
            "qualifiers=NocaseDict({})), "
            "'UI64': CIMProperty(name='UI64', value=4264, "
            "type='uint64', reference_class=None, embedded_object=None, "
            "is_array=False, array_size=None, class_origin=None, "
            "propagated=None, qualifiers=NocaseDict({})), "
            "'SI8': CIMProperty(name='SI8', value=-42, type='sint8', "
            "reference_class=None, embedded_object=None, is_array=False, "
            "array_size=None, class_origin=None, propagated=None, "
            "qualifiers=NocaseDict({})), "
            "'SI16': CIMProperty(name='SI16', value=-4216, type='sint16', "
            "reference_class=None, embedded_object=None, is_array=False, "
            "array_size=None, class_origin=None, propagated=None, "
            "qualifiers=NocaseDict({})), "
            "'SI32': CIMProperty(name='SI32', value=-4232, "
            "type='sint32', reference_class=None, embedded_object=None, "
            "is_array=False, array_size=None, class_origin=None, "
            "propagated=None, qualifiers=NocaseDict({})), "
            "'SI64': CIMProperty(name='SI64', value=-4264, type='sint64', "
            "reference_class=None, embedded_object=None, is_array=False, "
            "array_size=None, class_origin=None, propagated=None, "
            "qualifiers=NocaseDict({})), "
            "'R32': CIMProperty(name='R32', value=42.0, type='real32', "
            "reference_class=None, embedded_object=None, is_array=False, "
            "array_size=None, class_origin=None, propagated=None, "
            "qualifiers=NocaseDict({})), "
            "'R64': CIMProperty(name='R64', value=42.64, type='real64', "
            "reference_class=None, embedded_object=None, is_array=False, "
            "array_size=None, class_origin=None, propagated=None, "
            "qualifiers=NocaseDict({})), "
            "'S2': CIMProperty(name='S2', value='H\\u00e4m', type='string', "
            "reference_class=None, embedded_object=None, is_array=False, "
            "array_size=None, class_origin=None, propagated=None, "
            "qualifiers=NocaseDict({}))"
            "}), property_list=None, qualifiers=NocaseDict({})))")

        lc.check(
            ('pywbem.api.test_id', 'DEBUG', result_req),
            ('pywbem.api.test_id', 'DEBUG', result_ret),
        )

    @log_capture()
    def test_enuminstances_result(self, lc):
        """Test the ops result log for enumerate instances"""

        # set recorder to limit response to length of 10
        self.recorder_setup(detail_level=10)

        self.test_recorder.stage_pywbem_args(
            method='EnumerateInstances',
            ClassName='CIM_Foo',
            LocalOnly=True,
            IncludeQualifiers=True,
            IncludeClassOrigin=True,
            PropertyList=['propertyblah'])

        instance = self.create_ciminstance()
        exc = None

        self.test_recorder.stage_pywbem_result([instance, instance], exc)

        result_req = (
            "Request:test_id EnumerateInstances(ClassName=...)")

        result_ret = (
            "Return:test_id EnumerateInstances([CIMInstan...)")

        lc.check(
            ('pywbem.api.test_id', 'DEBUG', result_req),
            ('pywbem.api.test_id', 'DEBUG', result_ret),
        )

    @log_capture()
    def test_enuminstancenames_result(self, lc):
        """Test the ops result log for enumerate instances"""

        # set recorder to limit response to length of 10
        self.recorder_setup(detail_level=10)

        self.test_recorder.stage_pywbem_args(
            method='EnumerateInstanceNames',
            ClassName='CIM_Foo',
            LocalOnly=True,
            IncludeQualifiers=True,
            IncludeClassOrigin=True,
            PropertyList=['propertyblah', 'blah2'])

        exc = None
        inst_name = self.create_ciminstancename()

        self.test_recorder.stage_pywbem_result([inst_name, inst_name], exc)

        result_req = (
            "Request:test_id EnumerateInstanceNames(ClassName=...)")

        result_ret = (
            "Return:test_id EnumerateInstanceNames([CIMInstan...)")

        lc.check(
            ('pywbem.api.test_id', 'DEBUG', result_req),
            ('pywbem.api.test_id', 'DEBUG', result_ret),
        )

    @log_capture()
    def test_openenuminstances_result_all(self, lc):
        """Test the ops result log for enumerate instances. Returns no
        instances.
        """

        # set recorder to limit response to length of 10
        self.recorder_setup(detail_level='all')

        self.test_recorder.stage_pywbem_args(
            method='OpenEnumerateInstances',
            ClassName='CIM_Foo',
            LocalOnly=True,
            IncludeQualifiers=True,
            IncludeClassOrigin=True,
            PropertyList=['propertyblah'])

        # instance = self.create_ciminstance()
        exc = None

        result = []
        context = ('test_rtn_context', 'root/blah')
        result_tuple = pull_inst_result_tuple(result, False, context)

        self.test_recorder.stage_pywbem_result(result_tuple, exc)

        result_req = (
            "Request:test_id OpenEnumerateInstances("
            "ClassName='CIM_Foo', "
            "IncludeClassOrigin=True, "
            "IncludeQualifiers=True, "
            "LocalOnly=True, "
            "PropertyList=['propertyblah'])")

        result_ret = (
            "Return:test_id OpenEnumerateInstances(pull_inst_result_tuple("
            "context=('test_rtn_context', 'root/blah'), eos=False, "
            "instances=[]))")

        lc.check(
            ('pywbem.api.test_id', 'DEBUG', result_req),
            ('pywbem.api.test_id', 'DEBUG', result_ret),
        )

    @log_capture()
    def test_openenuminstances_all(self, lc):
        """Test the ops result log for enumerate instances paths with
        data in the paths component"""

        # set recorder to limit response to length of 10
        self.recorder_setup(detail_level='all')

        self.test_recorder.stage_pywbem_args(
            method='OpenEnumerateInstancePaths',
            ClassName='CIM_Foo',
            FilterQueryLanguage='FQL',
            FilterQuery='SELECT A from B',
            OperationTimeout=10,
            ContinueOnError=None,
            MaxObjectCount=100)

        inst_name = self.create_ciminstancename()
        result = [inst_name, inst_name]
        exc = None

        context = ('test_rtn_context', 'root/blah')
        result_tuple = pull_path_result_tuple(result, False, context)

        self.test_recorder.stage_pywbem_result(result_tuple, exc)

        result_req = (
            "Request:test_id OpenEnumerateInstancePaths("
            "ClassName='CIM_Foo', "
            "ContinueOnError=None, "
            "FilterQuery='SELECT A from B', "
            "FilterQueryLanguage='FQL', "
            "MaxObjectCount=100, "
            "OperationTimeout=10)")

        result_ret = (
            "Return:test_id OpenEnumerateInstancePaths("
            "pull_path_result_tuple("
            "context=('test_rtn_context', 'root/blah'), eos=False, "
            "paths=["
            "CIMInstanceName(classname='CIM_Foo', "
            "keybindings=NocaseDict({'Chicken': 'Ham'}), "
            "namespace='root/cimv2', host='woot.com'), "
            "CIMInstanceName(classname='CIM_Foo', "
            "keybindings=NocaseDict({'Chicken': 'Ham'}), "
            "namespace='root/cimv2', host='woot.com')"
            "]))")

        lc.check(
            ('pywbem.api.test_id', 'DEBUG', result_req),
            ('pywbem.api.test_id', 'DEBUG', result_ret),
        )

    @log_capture()
    def test_associators_result(self, lc):
        """Test the ops result log for Associators that returns nothing"""

        inst_name = self.create_ciminstancename()

        # set recorder to limit response to length of 10
        self.recorder_setup(detail_level=10)

        self.test_recorder.stage_pywbem_args(
            method='Associators',
            InstanceName=inst_name,
            AssocClass='BLAH_Assoc',
            ResultClass='BLAH_Result',
            IncludeQualifiers=True,
            IncludeClassOrigin=True,
            PropertyList=['propertyblah', 'propertyblah2'])
        exc = None

        self.test_recorder.stage_pywbem_result([], exc)

        result_req = (
            "Request:test_id Associators(AssocClass...)")

        result_ret = (
            "Return:test_id Associators([])")

        lc.check(
            ('pywbem.api.test_id', 'DEBUG', result_req),
            ('pywbem.api.test_id', 'DEBUG', result_ret),
        )

    @log_capture()
    def test_associators_result_exception(self, lc):
        """Test the ops result log for associators that returns exception"""

        # set recorder to limit response to length of 10
        self.recorder_setup(detail_level=11)

        exc = CIMError(6, "Fake CIMError")

        self.test_recorder.stage_pywbem_result([], exc)

        result_exc = "Exception:test_id None('CIMError(6...)"

        lc.check(
            ('pywbem.api.test_id', 'DEBUG', result_exc),
        )

    @log_capture()
    def test_invokemethod_int(self, lc):
        """Test invoke method log"""
        self.recorder_setup(detail_level=11)

        obj_name = self.create_ciminstancename()
        return_val = 0
        params = [('StringParam', 'Spotty'),
                  ('Uint8', Uint8(1)),
                  ('Sint8', Sint8(2))]

        self.test_recorder.stage_pywbem_args(method='InvokeMethod',
                                             MethodName='Blah',
                                             ObjectName=obj_name,
                                             Params=OrderedDict(params))

        self.test_recorder.stage_pywbem_result((return_val, params),
                                               None)

        result_req = "Request:test_id InvokeMethod(MethodName=...)"

        result_ret = "Return:test_id InvokeMethod((0, [('Stri...)"

        lc.check(
            ('pywbem.api.test_id', 'DEBUG', result_req),
            ('pywbem.api.test_id', 'DEBUG', result_ret),
        )

    @log_capture()
    def test_invokemethod_summary(self, lc):
        """Test invoke method log"""
        self.recorder_setup(detail_level='summary')

        obj_name = self.create_ciminstancename()
        return_val = 0
        params = [('StringParam', 'Spotty'),
                  ('Uint8', Uint8(1)),
                  ('Sint8', Sint8(2))]

        self.test_recorder.stage_pywbem_args(method='InvokeMethod',
                                             MethodName='Blah',
                                             ObjectName=obj_name,
                                             Params=OrderedDict(params))

        self.test_recorder.stage_pywbem_result((return_val, params),
                                               None)

        result_req = (
            "Request:test_id InvokeMethod("
            "MethodName='Blah', "
            "ObjectName=CIMInstanceName("
            "classname='CIM_Foo', "
            "keybindings=NocaseDict({'Chicken': 'Ham'}), "
            "namespace='root/cimv2', host='woot.com'), "
            "Params=OrderedDict(["
            "('StringParam', 'Spotty'), "
            "('Uint8', Uint8(cimtype='uint8', minvalue=0, maxvalue=255, 1)), "
            "('Sint8', Sint8(cimtype='sint8', minvalue=-128, maxvalue=127, 2))"
            "]))")

        result_ret = "Return:test_id InvokeMethod(tuple )"

        lc.check(
            ('pywbem.api.test_id', 'DEBUG', result_req),
            ('pywbem.api.test_id', 'DEBUG', result_ret),
        )

    # TODO add tests for all for invoke method.


class TestExternLoggerDef(BaseLogOperationRecorderTests):
    """ Test configuring loggers above level of our loggers"""

    @log_capture()
    def test_root_logger(self, lc):
        """
        Create a logger using logging.basicConfig and generate logs
        """
        logging.basicConfig(filename=TEST_OUTPUT_LOG, level=logging.DEBUG)

        detail_level_int = 10
        detail_level = {'api': detail_level_int, 'http': detail_level_int}

        # pylint: disable=attribute-defined-outside-init
        self.test_recorder = LogOperationRecorder('test_id',
                                                  detail_levels=detail_level)

        # We don't activate because we are not using wbemconnection, just
        # the recorder calls.
        self.test_recorder.stage_pywbem_args(
            method='EnumerateInstanceNames',
            ClassName='CIM_Foo',
            LocalOnly=True,
            IncludeQualifiers=True,
            IncludeClassOrigin=True,
            PropertyList=['propertyblah', 'blah2'])

        exc = None
        inst_name = self.create_ciminstancename()

        self.test_recorder.stage_pywbem_result([inst_name, inst_name], exc)

        result_req = "Request:test_id EnumerateInstanceNames(ClassName=...)"

        result_ret = "Return:test_id EnumerateInstanceNames([CIMInstan...)"

        lc.check(
            ('pywbem.api.test_id', 'DEBUG', result_req),
            ('pywbem.api.test_id', 'DEBUG', result_ret),
        )

    @unittest.skip("Test unreliable exception not always the same")
    @log_capture()
    def test_pywbem_logger(self, lc):
        """
        Test executing a connection with an externally created handler. Note
        that this test inconsistently reports the text of the exception
        in that sometimes adds the message  "[Errno 113] No route to host" and
        sometimes the message "timed out".
        """
        logger = logging.getLogger('pywbem')
        handler = logging.FileHandler(TEST_OUTPUT_LOG)
        handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)

        configure_logger('api', detail_level='summary', connection=True,
                         propagate=True)
        try:
            conn = WBEMConnection('http://blah', timeout=1)

            conn.GetClass('blah')
        except Exception:  # pylint: disable=broad-except
            pass

        conn_id = conn.conn_id

        api_exp_log_id = 'pywbem.api.{0}'.format(conn_id)
        http_exp_log_id = 'pywbem.http.{0}'.format(conn_id)

        result_exc = _format(
            "Exception:{0} GetClass('ConnectionError(Socket error: "
            "[Errno 113] No route to host)')",
            conn_id)

        result_con = _format(
            "Connection:{0} WBEMConnection("
            "url='http://blah', "
            "creds=None, "
            "conn_id={0!A}, "
            "default_namespace='root/cimv2', "
            "x509=None, "
            "verify_callback=None, "
            "ca_certs=None, "
            "no_verification=False, "
            "timeout=1, "
            "use_pull_operations=False, "
            "stats_enabled=False, "
            "recorders=['LogOperationRecorder'])",
            conn_id)

        result_req = _format(
            "Request:{0} GetClass("
            "ClassName='blah', "
            "IncludeClassOrigin=None, "
            "IncludeQualifiers=None, "
            "LocalOnly=None, "
            "PropertyList=None, "
            "namespace=None)",
            conn_id)

        result_hreq = _format(
            "Request:{0} POST /cimom 11 http://blah "
            "CIMOperation:'MethodCall' "
            "CIMMethod:'GetClass' "
            "CIMObject:u'root/cimv2'\n"
            '<?xml version="1.0" encoding="utf-8" ?>\n'
            '<CIM CIMVERSION="2.0" DTDVERSION="2.0">'
            '<MESSAGE ID="1001" PROTOCOLVERSION="1.0">'
            '<SIMPLEREQ>'
            '<IMETHODCALL NAME="GetClass">'
            '<LOCALNAMESPACEPATH>'
            '<NAMESPACE NAME="root"/>'
            '<NAMESPACE NAME="cimv2"/>'
            '</LOCALNAMESPACEPATH>'
            '<IPARAMVALUE NAME="ClassName">'
            '<CLASSNAME NAME="blah"/>'
            '</IPARAMVALUE>'
            '</IMETHODCALL>'
            '</SIMPLEREQ>'
            '</MESSAGE>'
            '</CIM>',
            conn_id)

        lc.check(
            (api_exp_log_id, 'DEBUG', result_con),
            (api_exp_log_id, 'DEBUG', result_req),
            (http_exp_log_id, 'DEBUG', result_hreq),
            (api_exp_log_id, 'DEBUG', result_exc),
        )


class TestLoggingEndToEnd(BaseLogOperationRecorderTests):
    """
    Test the examples documented in _logging.py document string. Because
    there is not logging until the first http request, these extend the
    examples to actually issue a request.  Therefore, they use the mocker
    to emulate a server

    """

    def build_repo(self, namespace):
        """Build a fake repo and FakeWBEMConnection so we get responses back"""
        schema = install_test_dmtf_schema()
        partial_schema = """
            #pragma locale ("en_US")
            #pragma include ("Interop/CIM_ObjectManager.mof")
            """

        conn = FakedWBEMConnection(default_namespace=namespace)
        conn.compile_mof_string(partial_schema, namespace=namespace,
                                search_paths=[schema.schema_mof_dir])
        return conn

    @log_capture()
    def test_1(self, lc):
        """
        Configure the "pywbem.api" logger for summary information output to a
        file and activate that logger for all subsequently created
        :class:`~pywbem.WBEMConnection` objects.
        NOTE: We changed from example to log to file and use log_captyre
        """
        # setup schema in test because we configure before we create the
        # connection in this test.
        namespace = 'root/blah'
        schema = install_test_dmtf_schema()
        partial_schema = """
            #pragma locale ("en_US")
            #pragma include ("Interop/CIM_ObjectManager.mof")
            """
        conn = FakedWBEMConnection(default_namespace=namespace)
        conn.compile_mof_string(partial_schema, namespace=namespace,
                                search_paths=[schema.schema_mof_dir])

        configure_logger('api', log_dest='file',
                         detail_level='summary',
                         log_filename=TEST_OUTPUT_LOG,
                         connection=conn, propagate=True)
        conn.GetClass('CIM_ObjectManager', namespace=namespace)

        conn_id = conn.conn_id

        api_exp_log_id = 'pywbem.api.{0}'.format(conn_id)

        result_con = _format(
            "Connection:{0} FakedWBEMConnection("
            "response_delay=None, "
            "super=WBEMConnection("
            "url='http://FakedUrl', "
            "creds=None, "
            "default_namespace={1!A}, ...))",
            conn_id, namespace)

        result_req = _format(
            "Request:{0} GetClass("
            "ClassName='CIM_ObjectManager', "
            "IncludeClassOrigin=None, "
            "IncludeQualifiers=None, "
            "LocalOnly=None, "
            "PropertyList=None, "
            "namespace={1!A})",
            conn_id, namespace)

        result_ret = _format(
            "Return:{0} GetClass(CIMClass CIM_ObjectManager)",
            conn_id)

        lc.check(
            (api_exp_log_id, 'DEBUG', result_con),
            (api_exp_log_id, 'DEBUG', result_req),
            (api_exp_log_id, 'DEBUG', result_ret)
        )

    @log_capture()
    def test_2(self, lc):
        """
        Configure and activate a single :class:`~pywbem.WBEMConnection` object
        logger for output of summary information for both "pywbem.api" and
        "pywbem.http"::
        Differs from example in that we set detail_level to limit output for
        test
        """
        namespace = 'root/blah'
        conn = self.build_repo(namespace)
        configure_logger('all', log_dest='file',
                         log_filename=TEST_OUTPUT_LOG,
                         detail_level=10,
                         connection=conn, propagate=True)
        conn.GetClass('CIM_ObjectManager', namespace=namespace)

        conn_id = conn.conn_id

        api_exp_log_id = 'pywbem.api.{0}'.format(conn_id)

        result_con = _format("Connection:{0} FakedWBEMC...", conn_id)

        result_req = _format("Request:{0} GetClass(ClassName=...)", conn_id)

        result_ret = _format("Return:{0} GetClass(CIMClass(c...)", conn_id)

        lc.check(
            (api_exp_log_id, 'DEBUG', result_con),
            (api_exp_log_id, 'DEBUG', result_req),
            (api_exp_log_id, 'DEBUG', result_ret),
        )

    @log_capture()
    def test_3(self, lc):
        """
        Configure a single pywbem connection with standard Python logger
        methods by defining the root logger with basicConfig
        Differs from example in that we set detail_level to limit output for
        test.
        Does not produce http request/response info because when using the
        pywbem_mock, no http is generated.
        """
        logging.basicConfig(filename='example.log', level=logging.DEBUG)
        namespace = 'root/blah'
        conn = self.build_repo(namespace)

        # Define the detail_level and WBEMConnection object to activate.
        configure_logger('all', detail_level=10, connection=conn,
                         propagate=True)

        # logging_tree_printout()

        conn.GetClass('CIM_ObjectManager', namespace=namespace)

        conn_id = conn.conn_id

        api_exp_log_id = 'pywbem.api.{0}'.format(conn_id)

        result_con = _format("Connection:{0} FakedWBEMC...", conn_id)

        result_req = _format("Request:{0} GetClass(ClassName=...)", conn_id)

        result_ret = _format("Return:{0} GetClass(CIMClass(c...)", conn_id)

        lc.check(
            (api_exp_log_id, 'DEBUG', result_con),
            (api_exp_log_id, 'DEBUG', result_req),
            (api_exp_log_id, 'DEBUG', result_ret),
        )

    @log_capture()
    def test_4(self, lc):
        """
        Configure a single pywbem connection with standard Python logger
        methods by defining the root logger with basicConfig
        Differs from example in that we set detail_level to limit output for
        test
        """
        logging.basicConfig(filename='basicconfig.log', level=logging.DEBUG)
        namespace = 'root/blah'
        conn = self.build_repo(namespace)

        # Define the detail_level and WBEMConnection object to activate.
        configure_logger('api', detail_level=10, connection=conn,
                         propagate=True)

        # logging_tree_printout()

        conn.GetClass('CIM_ObjectManager', namespace=namespace)

        conn_id = conn.conn_id

        api_exp_log_id = 'pywbem.api.{0}'.format(conn_id)

        result_con = _format("Connection:{0} FakedWBEMC...", conn_id)

        result_req = _format("Request:{0} GetClass(ClassName=...)", conn_id)

        result_ret = _format("Return:{0} GetClass(CIMClass(c...)", conn_id)

        lc.check(
            (api_exp_log_id, 'DEBUG', result_con),
            (api_exp_log_id, 'DEBUG', result_req),
            (api_exp_log_id, 'DEBUG', result_ret),
        )

    @log_capture()
    def test_5(self, lc):
        """
        Configure a single pywbem connection with standard Python logger
        methods by defining the root logger with basicConfig
        Differs from example in that we set detail_level to limit output for
        test. The basic logger should have no effect since pywbem sets the
        NULLHandler at the pywbem level.
        """
        logging.basicConfig(filename='basicconfig.log', level=logging.DEBUG)
        namespace = 'root/blah'
        conn = self.build_repo(namespace)

        # Define the detail_level and WBEMConnection object to activate.
        configure_logger('api', detail_level=10, connection=conn,
                         propagate=True)

        # logging_tree_printout()

        conn.GetClass('CIM_ObjectManager', namespace=namespace)

        conn_id = conn.conn_id

        api_exp_log_id = 'pywbem.api.{0}'.format(conn_id)

        result_con = _format("Connection:{0} FakedWBEMC...", conn_id)

        result_req = _format("Request:{0} GetClass(ClassName=...)", conn_id)

        result_ret = _format("Return:{0} GetClass(CIMClass(c...)", conn_id)

        lc.check(
            (api_exp_log_id, 'DEBUG', result_con),
            (api_exp_log_id, 'DEBUG', result_req),
            (api_exp_log_id, 'DEBUG', result_ret)
        )

    @log_capture()
    def test_6(self, lc):
        """
        Configure a http logger with detail_level='all' and
        a log config with just 'http'  (which produces no output because the
        mocker does not generate http requests or responses) and at the
        same time setting the logging basic logger which we do not use.
        This test ability to generate connection log when only http log is
        activated.
        """
        logging.basicConfig(filename='example.log', level=logging.DEBUG)
        namespace = 'root/blah'
        conn = self.build_repo(namespace)

        # Define the detail_level and WBEMConnection object to activate.
        configure_logger('http', detail_level='all', log_dest='file',
                         log_filename=TEST_OUTPUT_LOG,
                         connection=conn, propagate=True)

        conn.GetClass('CIM_ObjectManager', namespace=namespace)

        conn_id = conn.conn_id

        http_exp_log_id = 'pywbem.http.{0}'.format(conn_id)

        result_con = _format(
            "Connection:{0} FakedWBEMConnection("
            "response_delay=None, "
            "super=WBEMConnection("
            "url='http://FakedUrl', "
            "creds=None, "
            "conn_id={0!A}, "
            "default_namespace={1!A}, "
            "x509=None, "
            "verify_callback=None, "
            "ca_certs=None, "
            "no_verification=False, "
            "timeout=None, "
            "use_pull_operations=False, "
            "stats_enabled=False, "
            "recorders=['LogOperationRecorder']))",
            conn_id, namespace)

        lc.check(
            (http_exp_log_id, 'DEBUG', result_con)
        )

    @log_capture()
    def test_7(self, lc):
        """
        Configure a http logger with detail_level='all', log_dest=none
        a log config with just 'http'  (which produces no output because the
        mocker does not generate http requests or responses) and at the
        same time setting the logging basic logger which we do not use.
        This test ability to generate connection log when only http log is
        activated.
        """
        logging.basicConfig(filename='example.log', level=logging.DEBUG)
        namespace = 'root/blah'
        conn = self.build_repo(namespace)

        # Define the detail_level and WBEMConnection object to activate.
        configure_logger('http', detail_level='all', log_dest=None,
                         connection=conn, propagate=True)

        conn.GetClass('CIM_ObjectManager', namespace=namespace)

        conn_id = conn.conn_id

        http_exp_log_id = 'pywbem.http.{0}'.format(conn_id)

        result_con = _format(
            "Connection:{0} FakedWBEMConnection("
            "response_delay=None, "
            "super=WBEMConnection("
            "url='http://FakedUrl', "
            "creds=None, "
            "conn_id={0!A}, "
            "default_namespace={1!A}, "
            "x509=None, "
            "verify_callback=None, "
            "ca_certs=None, "
            "no_verification=False, "
            "timeout=None, "
            "use_pull_operations=False, "
            "stats_enabled=False, "
            "recorders=['LogOperationRecorder']))",
            conn_id, namespace)

        lc.check(
            (http_exp_log_id, 'DEBUG', result_con)
        )

    @log_capture()
    def test_8(self, lc):
        """
        Configure a http logger with detail_level='all' and
        a log config with just 'http'  (which produces no output because the
        mocker does not generate http requests or responses) and at the
        same time setting the logging basic logger which we do not use.
        This test ability to generate connection log when only http log is
        activated.
        """
        msg_format = '%(asctime)s-%(name)s-%(message)s'
        handler = logging.FileHandler(TEST_OUTPUT_LOG, encoding="UTF-8")
        handler.setFormatter(logging.Formatter(msg_format))
        logger = logging.getLogger('pywbem')
        logger.setLevel(logging.DEBUG)
        logger.addHandler(handler)

        namespace = 'root/blah'
        conn = self.build_repo(namespace)

        # Define the detail_level and WBEMConnection object to activate.
        configure_logger('http', detail_level='all', log_dest=None,
                         connection=conn, propagate=True)

        conn.GetClass('CIM_ObjectManager', namespace=namespace)

        conn_id = conn.conn_id

        http_exp_log_id = 'pywbem.http.{0}'.format(conn_id)

        result_con = _format(
            "Connection:{0} FakedWBEMConnection("
            "response_delay=None, "
            "super=WBEMConnection("
            "url='http://FakedUrl', "
            "creds=None, "
            "conn_id={0!A}, "
            "default_namespace={1!A}, "
            "x509=None, "
            "verify_callback=None, "
            "ca_certs=None, "
            "no_verification=False, "
            "timeout=None, "
            "use_pull_operations=False, "
            "stats_enabled=False, "
            "recorders=['LogOperationRecorder']))",
            conn_id, namespace)

        lc.check(
            (http_exp_log_id, 'DEBUG', result_con)
        )

    @log_capture()
    def test_9(self, lc):
        """
        Configure a http logger with detail_level='all' and
        a log config with just 'http'  (which produces no output because the
        mocker does not generate http requests or responses) and at the
        same time setting the logging basic logger which we do not use.
        This test ability to generate connection log when only http log is
        activated.
        """

        namespace = 'root/blah'
        conn = self.build_repo(namespace)

        # Define the detail_level and WBEMConnection object to activate.
        configure_logger('http', detail_level='all', log_dest=None,
                         connection=conn, propagate=True)

        conn.GetClass('CIM_ObjectManager', namespace=namespace)

        conn_id = conn.conn_id

        http_exp_log_id = 'pywbem.http.{0}'.format(conn_id)

        result_con = _format(
            "Connection:{0} FakedWBEMConnection("
            "response_delay=None, "
            "super=WBEMConnection("
            "url='http://FakedUrl', "
            "creds=None, "
            "conn_id={0!A}, "
            "default_namespace={1!A}, "
            "x509=None, "
            "verify_callback=None, "
            "ca_certs=None, "
            "no_verification=False, "
            "timeout=None, "
            "use_pull_operations=False, "
            "stats_enabled=False, "
            "recorders=['LogOperationRecorder']))",
            conn_id, namespace)

        lc.check(
            (http_exp_log_id, 'DEBUG', result_con)
        )

    @log_capture()
    def test_10(self, lc):
        """
        Configure a http logger with detail_level='all' and
        a log config with just 'http'  (which produces no output because the
        mocker does not generate http requests or responses) and at the
        same time setting the logging basic logger which we do not use.
        This test ability to generate connection log when only http log is
        activated.
        """

        namespace = 'root/blah'
        # Define the detail_level and WBEMConnection object to activate.
        configure_logger('http', detail_level='all',
                         connection=True, propagate=True)
        conn = self.build_repo(namespace)

        conn.GetClass('CIM_ObjectManager', namespace=namespace)

        conn_id = conn.conn_id

        http_exp_log_id = 'pywbem.http.{0}'.format(conn_id)

        result_con = _format(
            "Connection:{0} FakedWBEMConnection("
            "response_delay=None, "
            "super=WBEMConnection("
            "url='http://FakedUrl', "
            "creds=None, "
            "conn_id={0!A}, "
            "default_namespace={1!A}, "
            "x509=None, "
            "verify_callback=None, "
            "ca_certs=None, "
            "no_verification=False, "
            "timeout=None, "
            "use_pull_operations=False, "
            "stats_enabled=False, "
            "recorders=['LogOperationRecorder']))",
            conn_id, namespace)

        lc.check(
            (http_exp_log_id, 'DEBUG', result_con)
        )

    @log_capture()
    def test_err(self, lc):
        """
        Test configure_logger exception
        """
        namespace = 'root/blah'
        conn = self.build_repo(namespace)

        # Define the detail_level and WBEMConnection object to activate.
        try:
            configure_logger('api', detail_level='blah', connection=conn,
                             propagate=True)
            self.fail("Exception expected")
        except ValueError:
            pass

        lc.check()


if __name__ == '__main__':
    unittest.main()
