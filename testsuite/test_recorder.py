#!/usr/bin/env python

"""
Unit test recorder functions.

"""

from __future__ import absolute_import, print_function

# Allows use of lots of single character variable names.
# pylint: disable=invalid-name,missing-docstring,too-many-statements
# pylint: disable=too-many-lines,no-self-use
from datetime import timedelta, datetime, tzinfo
import os
import os.path
import logging
import logging.handlers
from io import open as _open

import unittest2 as unittest  # we use assertRaises(exc) introduced in py27
import six
from testfixtures import LogCapture, log_capture
# Enabled only to display a tree of loggers
# from logging_tree import printout as logging_tree_printout
import yaml
try:
    from collections import OrderedDict
except ImportError:
    from ordereddict import OrderedDict

from pywbem import CIMInstanceName, CIMInstance, MinutesFromUTC, \
    Uint8, Uint16, Uint32, Uint64, Sint8, Sint16, \
    Sint32, Sint64, Real32, Real64, CIMProperty, CIMDateTime, CIMError, \
    HTTPError, WBEMConnection, LogOperationRecorder, configure_logger
# Renamed the following import to not have py.test pick it up as a test class:
from pywbem import TestClientRecorder as _TestClientRecorder
from pywbem.cim_operations import pull_path_result_tuple, pull_inst_result_tuple
from pywbem_mock import FakedWBEMConnection
from dmtf_mof_schema_def import install_test_dmtf_schema


# test outpuf file for the recorder tests.  This is opened for each
# test to save yaml output and may be reloaded during the same test
# to confirm the yaml results.
TEST_YAML_FILE = 'test_recorder.yaml'
TEST_DIR = os.path.dirname(__file__)

LOG_FILE_NAME = 'test_recorder.log'
TEST_OUTPUT_LOG = '%s/%s' % (TEST_DIR, LOG_FILE_NAME)

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
        class TZ(tzinfo):
            """'Simplistic tsinfo subclass for this test"""
            def utcoffset(self, dt):  # pylint: disable=unused-argument
                return timedelta(minutes=-399)

        dt = datetime(year=2016, month=3, day=31, hour=19, minute=30,
                      second=40, microsecond=654321,
                      tzinfo=MinutesFromUTC(120))
        cim_dt = CIMDateTime(dt)
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
            ('DTI', CIMDateTime(timedelta(10, 49, 20))),
            ('DTF', cim_dt),
            ('DTP', CIMDateTime(datetime(2014, 9, 22, 10, 49, 20, 524789,
                                         tzinfo=TZ()))),
        ])
        # TODO python 2.7 will not write the following unicode character
        # For the moment, only add this property in python 3 test
        if six.PY3:
            props_input['S2'] = u'H\u00E4m'  # U+00E4 = lower case a umlaut

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
        dt_now = CIMDateTime.now()
        obj_name = self.create_ciminstancename()

        dt = datetime(year=2016, month=3, day=31, hour=19, minute=30,
                      second=40, microsecond=654321,
                      tzinfo=MinutesFromUTC(120))
        cim_dt = CIMDateTime(dt)

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
                  ('DTN', dt_now),
                  ('DTF', cim_dt),
                  ('DTI', CIMDateTime(timedelta(60))),
                  ('Ref', obj_name)]
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

        dtp = properties['DTP']
        self.assertEqual(dtp['name'], 'DTP')
        self.assertEqual(dtp['type'], 'datetime')
        self.assertEqual(dtp['value'], '20140922104920.524789-399')
        dti = properties['DTI']
        self.assertEqual(dti['name'], 'DTI')
        self.assertEqual(dti['type'], 'datetime')
        self.assertEqual(dti['value'], '00000010000049.000020:000')

        # TODO add test for reference properties
        # TODO add test for embedded object property

    def test_inst_to_yaml_array_props(self):
        """Test  property with array toyaml"""
        str_data = "The pink fox jumped over the big blue dog"
        dt = datetime(2014, 9, 22, 10, 49, 20, 524789)
        array_props = [
            ('MyString', str_data),
            ('MyUint8Array', [Uint8(1), Uint8(2)]),
            ('MySint8Array', [Sint8(1), Sint8(2)]),
            ('MyUint64Array', [Uint64(123456789),
                               Uint64(123456789),
                               Uint64(123456789)]),
            ('MyUint32Array', [Uint32(9999), Uint32(9999)]),
            ('MyDateTimeArray', [dt, dt, dt]),
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

        my_datetimearray = properties['MyDateTimeArray']
        self.assertEqual(my_datetimearray['name'], 'MyDateTimeArray')
        self.assertEqual(my_datetimearray['type'], 'datetime')
        cim_dt = str(CIMDateTime(dt))
        self.assertEqual(my_datetimearray['value'], [cim_dt, cim_dt, cim_dt])

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
        dt_now = str(in_params_dict['DTN'])

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
        self.assertEqual(out_params_dict['DTN'], dt_now)
        self.assertEqual(out_params_dict['DTI'],
                         str(CIMDateTime(timedelta(60))))
        # TODO fix the following. Currently it fails with:
        # AssertionError: CIMIn[16 chars]name={'classname': 'CIM_Foo',
        # 'keybindings': {[132 chars]None) != CIMIn[16 chars]name=u'CIM_Foo',
        # keybindings=NocaseDict([('Chi[55 chars]com')
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


# Long log entry for getInstance return all log
get_inst_return_all_log = (
    u"Return:test_id GetInstance(CIMInstance(classname='CIM_Foo', path=None, "
    u"properties=NocaseDict(["
    u"('S1', CIMProperty(name='S1', value='Ham', type='string', "
    u"reference_class=None, embedded_object=None, is_array=False, "
    u"array_size=None, class_origin=None, propagated=None, "
    u"qualifiers=NocaseDict([]))), "
    u"('Bool', CIMProperty(name='Bool', value=True, type='boolean', "
    u"reference_class=None, embedded_object=None, is_array=False, "
    u"array_size=None, class_origin=None, propagated=None, "
    u"qualifiers=NocaseDict([]))), "
    u"('UI8', CIMProperty(name='UI8', value=Uint8(cimtype='uint8', "
    u"minvalue=0, maxvalue=255, 42), type='uint8', reference_class=None, "
    u"embedded_object=None, is_array=False, array_size=None, "
    u"class_origin=None, propagated=None, "
    u"qualifiers=NocaseDict([]))), "
    u"('UI16', CIMProperty(name='UI16', value=Uint16(cimtype='uint16', "
    u"minvalue=0, maxvalue=65535, 4216), type='uint16', "
    u"reference_class=None, embedded_object=None, is_array=False, "
    u"array_size=None, class_origin=None, propagated=None, "
    u"qualifiers=NocaseDict([]))), "
    u"('UI32', CIMProperty(name='UI32', value=Uint32(cimtype='uint32', "
    u"minvalue=0, maxvalue=4294967295, 4232), type='uint32', "
    u"reference_class=None, embedded_object=None, is_array=False, "
    u"array_size=None, class_origin=None, propagated=None, "
    u"qualifiers=NocaseDict([]))), "
    u"('UI64', CIMProperty(name='UI64', value=Uint64(cimtype='uint64', "
    u"minvalue=0, maxvalue=18446744073709551615, 4264), type='uint64', "
    u"reference_class=None, embedded_object=None, is_array=False, "
    u"array_size=None, class_origin=None, propagated=None, "
    u"qualifiers=NocaseDict([]))), "
    u"('SI8', CIMProperty(name='SI8', value=Sint8(cimtype='sint8', "
    u"minvalue=-128, maxvalue=127, -42), type='sint8', reference_class=None, "
    u"embedded_object=None, is_array=False, array_size=None, "
    u"class_origin=None, propagated=None, "
    u"qualifiers=NocaseDict([]))), "
    u"('SI16', CIMProperty(name='SI16', value=Sint16(cimtype='sint16', "
    u"minvalue=-32768, maxvalue=32767, -4216), type='sint16', "
    u"reference_class=None, embedded_object=None, is_array=False, "
    u"array_size=None, class_origin=None, propagated=None, "
    u"qualifiers=NocaseDict([]))), "
    u"('SI32', CIMProperty(name='SI32', value=Sint32(cimtype='sint32', "
    u"minvalue=-2147483648, maxvalue=2147483647, -4232), type='sint32', "
    u"reference_class=None, embedded_object=None, is_array=False, "
    u"array_size=None, class_origin=None, propagated=None, "
    u"qualifiers=NocaseDict([]))), "
    u"('SI64', CIMProperty(name='SI64', value=Sint64(cimtype='sint64', "
    u"minvalue=-9223372036854775808, maxvalue=9223372036854775807, -4264), "
    u"type='sint64', reference_class=None, embedded_object=None, "
    u"is_array=False, array_size=None, class_origin=None, propagated=None, "
    u"qualifiers=NocaseDict([]))), "
    u"('R32', CIMProperty(name='R32', value=Real32(cimtype='real32', 42.0), "
    u"type='real32', reference_class=None, embedded_object=None, "
    u"is_array=False, array_size=None, class_origin=None, propagated=None, "
    u"qualifiers=NocaseDict([]))), "
    u"('R64', CIMProperty(name='R64', value=Real64(cimtype='real64', 42.64), "
    u"type='real64', reference_class=None, embedded_object=None, "
    u"is_array=False, array_size=None, class_origin=None, propagated=None, "
    u"qualifiers=NocaseDict([]))), "
    u"('DTI', CIMProperty(name='DTI', value=CIMDateTime(cimtype='datetime', "
    u"'00000010000049.000020:000'), type='datetime', reference_class=None, "
    u"embedded_object=None, is_array=False, array_size=None, "
    u"class_origin=None, propagated=None, qualifiers=NocaseDict([]))), "
    u"('DTF', CIMProperty(name='DTF', value=CIMDateTime(cimtype='datetime', "
    u"'20160331193040.654321+120'), type='datetime', reference_class=None, "
    u"embedded_object=None, is_array=False, array_size=None, "
    u"class_origin=None, propagated=None, qualifiers=NocaseDict([]))), "
    u"('DTP', CIMProperty(name='DTP', value=CIMDateTime(cimtype='datetime', "
    u"'20140922104920.524789-399'), type='datetime', reference_class=None, "
    u"embedded_object=None, is_array=False, array_size=None, "
    u"class_origin=None, propagated=None, qualifiers=NocaseDict([]))), "
    u"('S2', CIMProperty(name='S2', value='H\u00E4m', type='string', "
    u"reference_class=None, embedded_object=None, is_array=False, "
    u"array_size=None, class_origin=None, propagated=None, "
    u"qualifiers=NocaseDict([])))"
    u"]), property_list=None, qualifiers=NocaseDict([])))")


get_inst_return_all_log_PY2 = (
    "Return:test_id GetInstance(CIMInstance(classname=u'CIM_Foo', path=None, "
    "properties=NocaseDict(["
    "('S1', CIMProperty(name=u'S1', value=u'Ham', type=u'string', "
    "reference_class=None, embedded_object=None, is_array=False, "
    "array_size=None, class_origin=None, propagated=None, "
    "qualifiers=NocaseDict([]))), "
    "('Bool', CIMProperty(name=u'Bool', value=True, type=u'boolean', "
    "reference_class=None, embedded_object=None, is_array=False, "
    "array_size=None, class_origin=None, propagated=None, "
    "qualifiers=NocaseDict([]))), "
    "('UI8', CIMProperty(name=u'UI8', value=Uint8(cimtype='uint8', "
    "minvalue=0, maxvalue=255, 42), type=u'uint8', reference_class=None, "
    "embedded_object=None, is_array=False, array_size=None, "
    "class_origin=None, propagated=None, qualifiers=NocaseDict([]))), "
    "('UI16', CIMProperty(name=u'UI16', value=Uint16(cimtype='uint16', "
    "minvalue=0, maxvalue=65535, 4216), type=u'uint16', reference_class=None, "
    "embedded_object=None, is_array=False, array_size=None, class_origin=None, "
    "propagated=None, qualifiers=NocaseDict([]))), "
    "('UI32', CIMProperty(name=u'UI32', value=Uint32(cimtype='uint32', "
    "minvalue=0, maxvalue=4294967295, 4232), type=u'uint32', "
    "reference_class=None, embedded_object=None, is_array=False, "
    "array_size=None, class_origin=None, propagated=None, "
    "qualifiers=NocaseDict([]))), "
    "('UI64', CIMProperty(name=u'UI64', value=Uint64(cimtype='uint64', "
    "minvalue=0, maxvalue=18446744073709551615, 4264), type=u'uint64', "
    "reference_class=None, embedded_object=None, is_array=False, "
    "array_size=None, class_origin=None, propagated=None, "
    "qualifiers=NocaseDict([]))), "
    "('SI8', CIMProperty(name=u'SI8', value=Sint8(cimtype='sint8', "
    "minvalue=-128, maxvalue=127, -42), type=u'sint8', reference_class=None, "
    "embedded_object=None, is_array=False, array_size=None, "
    "class_origin=None, propagated=None, qualifiers=NocaseDict([]))), "
    "('SI16', CIMProperty(name=u'SI16', value=Sint16(cimtype='sint16', "
    "minvalue=-32768, maxvalue=32767, -4216), type=u'sint16', "
    "reference_class=None, embedded_object=None, is_array=False, "
    "array_size=None, class_origin=None, propagated=None, "
    "qualifiers=NocaseDict([]))), "
    "('SI32', CIMProperty(name=u'SI32', value=Sint32(cimtype='sint32', "
    "minvalue=-2147483648, maxvalue=2147483647, -4232), type=u'sint32', "
    "reference_class=None, embedded_object=None, is_array=False, "
    "array_size=None, class_origin=None, propagated=None, "
    "qualifiers=NocaseDict([]))), "
    "('SI64', CIMProperty(name=u'SI64', value=Sint64(cimtype='sint64', "
    "minvalue=-9223372036854775808, maxvalue=9223372036854775807, -4264), "
    "type=u'sint64', reference_class=None, embedded_object=None, "
    "is_array=False, array_size=None, class_origin=None, propagated=None, "
    "qualifiers=NocaseDict([]))), "
    "('R32', CIMProperty(name=u'R32', value=Real32(cimtype='real32', 42.0), "
    "type=u'real32', reference_class=None, embedded_object=None, "
    "is_array=False, array_size=None, class_origin=None, propagated=None, "
    "qualifiers=NocaseDict([]))), "
    "('R64', CIMProperty(name=u'R64', value=Real64(cimtype='real64', 42.64), "
    "type=u'real64', reference_class=None, embedded_object=None, "
    "is_array=False, array_size=None, class_origin=None, propagated=None, "
    "qualifiers=NocaseDict([]))), "
    "('DTI', CIMProperty(name=u'DTI', value=CIMDateTime(cimtype='datetime', "
    "'00000010000049.000020:000'), type=u'datetime', reference_class=None, "
    "embedded_object=None, is_array=False, array_size=None, class_origin=None,"
    " propagated=None, qualifiers=NocaseDict([]))), "
    "('DTF', CIMProperty(name=u'DTF', value=CIMDateTime("
    "cimtype='datetime', '20160331193040.654321+120'), type=u'datetime', "
    "reference_class=None, embedded_object=None, is_array=False, array_size="
    "None, class_origin=None, propagated=None, qualifiers=NocaseDict([]))), "
    "('DTP', CIMProperty(name=u'DTP', value=CIMDateTime(cimtype='datetime', "
    "'20140922104920.524789-399'), type=u'datetime', reference_class=None, "
    "embedded_object=None, is_array=False, array_size=None, "
    "class_origin=None, propagated=None, qualifiers=NocaseDict([])))"
    "]), property_list=None, qualifiers=NocaseDict([])))")


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
        configure_logger('api', log_dest='stderr', detail_level='all',
                         connection=conn, propagate=True)

        # pywbem 2 and 3 differ in only the use of unicode for certain
        # string properties. (ex. classname)
        log_name = 'pywbem.api.%s' % conn.conn_id

        result = ("Connection:<REPLACE_THIS> WBEMConnection(url=u'http://blah',"
                  " creds=None, conn_id=<REPLACE_THIS>, "
                  "default_namespace=u'root/cimv2', x509=None, "
                  "verify_callback=None, ca_certs=None, no_verification=False, "
                  "timeout=None, use_pull_operations=False, "
                  "stats_enabled=False, recorders=['LogOperationRecorder'])")
        result = result.replace('<REPLACE_THIS>', conn.conn_id)

        if six.PY2:
            lc.check((log_name, "DEBUG", result),)
        else:
            result = result.replace("u'http://blah'", "'http://blah'")
            result = result.replace("u'root/cimv2'", "'root/cimv2'")
            lc.check((log_name, "DEBUG", result),)

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
        configure_logger('api', log_dest='stderr', detail_level='all',
                         connection=conn, propagate=True)

        # fake conn id by directly setting internal attribute
        # pywbem 2 and 3 differ in only the use of unicode for certain
        # string properties. (ex. classname)
        log_name = 'pywbem.api.%s' % conn.conn_id
        result = (
            "Connection:<REPLACE_THIS> WBEMConnection(url=u'http://blah', "
            "creds=('username', ...), conn_id=<REPLACE_THIS>, "
            "default_namespace=u'root/blah', "
            "x509='cert_file': 'Certfile.x', 'key_file': 'keyfile.x', "
            "verify_callback=None, ca_certs=None, no_verification=True, "
            "timeout=10, use_pull_operations=True, stats_enabled=True, "
            "recorders=['LogOperationRecorder'])")
        result = result.replace('<REPLACE_THIS>', conn.conn_id)

        if six.PY2:
            lc.check((log_name, "DEBUG", result),)
        else:
            result = result.replace("u'root/blah'", "'root/blah'")
            result = result.replace("u'http://blah'", "'http://blah'")
            result = result.replace("u'root/cimv2'", "'root/cimv2'")
            lc.check((log_name, "DEBUG", result),)

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
        configure_logger('api', log_dest='stderr', detail_level='summary',
                         connection=conn, propagate=True)

        # fake conn id by directly setting internal attribute
        # pywbem 2 and 3 differ in only the use of unicode for certain
        # string properties. (ex. classname)
        log_name = 'pywbem.api.%s' % conn.conn_id
        result = (
            "Connection:<REPLACE_THIS> WBEMConnection(url=u'http://blah', "
            "creds=('username', ...), "
            "default_namespace=u'root/blah')")
        result = result.replace('<REPLACE_THIS>', conn.conn_id)

        if six.PY2:
            lc.check((log_name, "DEBUG", result),)
        else:
            result = result.replace("u'root/blah'", "'root/blah'")
            result = result.replace("u'http://blah'", "'http://blah'")
            result = result.replace("u'root/cimv2'", "'root/cimv2'")
            lc.check((log_name, "DEBUG", result),)

    @log_capture()
    def test_stage_result_exception(self, lc):
        """Test the ops result log None return, HTTPError exception."""
        self.recorder_setup(detail_level=10)
        ce = CIMError(6, "Fake CIMError")
        exc = HTTPError(500, "Fake Reason", cimerror='%s' % ce)
        self.test_recorder.stage_pywbem_result(None, exc)

        lc.check(
            ("pywbem.api.test_id", "DEBUG",
             "Exception:test_id None('HTTPError...)"))

    @log_capture()
    def test_stage_result_exception_all(self, lc):
        """Test the ops result log None return, HTTPError exception."""
        self.recorder_setup(detail_level='all')
        ce = CIMError(6, "Fake CIMError")
        exc = HTTPError(500, "Fake Reason", cimerror='%s' % ce)
        self.test_recorder.stage_pywbem_result(None, exc)

        # TODO. V2 valid string has extra single quote after CIMError
        if six.PY2:
            lc.check(
                ("pywbem.api.test_id", "DEBUG",
                 "Exception:test_id None('HTTPError(500 (Fake Reason), "
                 "CIMError: 6: Fake CIMError)')"),)
        else:
            lc.check(
                ("pywbem.api.test_id", "DEBUG",
                 "Exception:test_id None('HTTPError(500 (Fake Reason), "
                 "CIMError: 6: Fake CIMError)')"),)

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

        # pywbem 2 and 3 differ in only the use of unicode for certain
        # string properties. (ex. classname)
        result = ("Request:test_id GetInstance(IncludeClassOrigin=True, "
                  "IncludeQualifiers=True, InstanceName=CIMInstanceName("
                  "classname=u'CIM_Foo', keybindings=NocaseDict("
                  "[('Chicken', u'Ham')]), namespace=u'root/cimv2', "
                  "host=u'woot.com'), LocalOnly=True, "
                  "PropertyList=['propertyblah'])")
        log_name = 'pywbem.api.%s' % "test_id"
        if six.PY2:
            lc.check((log_name, "DEBUG", result))

        else:
            result = result.replace("u'root/cimv2'", "'root/cimv2'")
            result = result.replace("u'Ham'", "'Ham'")
            result = result.replace("u'woot.com'", "'woot.com'")
            result = result.replace("u'CIM_Foo'", "'CIM_Foo'")
            lc.check((log_name, "DEBUG", result))

    @log_capture()
    def test_stage_instance_result(self, lc):
        instance = self.create_ciminstance()
        self.recorder_setup(detail_level=10)
        exc = None
        self.test_recorder.stage_pywbem_result(instance, exc)

        if six.PY2:
            lc.check(
                ("pywbem.api.test_id", "DEBUG",
                 'Return:test_id None(CIMInstanc...)'))
        else:
            lc.check(
                ("pywbem.api.test_id", "DEBUG",
                 'Return:test_id None(CIMInstanc...)'))

    @log_capture()
    def test_stage_instance_result_default(self, lc):
        instance = self.create_ciminstance()
        # set the length in accord with the "min" definition.
        self.recorder_setup(detail_level=1000)
        exc = None
        self.test_recorder.stage_pywbem_result(instance, exc)

        if six.PY2:
            lc.check(
                ("pywbem.api.test_id", "DEBUG",
                 "Return:test_id None(CIMInstance(classname=u'CIM_Foo', "
                 "path=None, properties=NocaseDict(["
                 "('S1', CIMProperty(name=u'S1', value=u'Ham', "
                 "type=u'string', reference_class=None, "
                 "embedded_object=None, is_array=False, array_size=None, "
                 "class_origin=None, propagated=None, "
                 "qualifiers=NocaseDict([]))), "
                 "('Bool', CIMProperty(name=u'Bool', value=True, "
                 "type=u'boolean', reference_class=None, "
                 "embedded_object=None, is_array=False, array_size=None, "
                 "class_origin=None, propagated=None, "
                 "qualifiers=NocaseDict([]))), "
                 "('UI8', CIMProperty(name=u'UI8', value=Uint8("
                 "cimtype='uint8', minvalue=0, maxvalue=255, 42), "
                 "type=u'uint8', reference_class=None, embedded_object=None, "
                 "is_array=False, array_size=None, class_origin=None, "
                 "propagated=None, qualifiers=NocaseDict([]))), "
                 "('UI16', CIMProperty(name=u'UI16', value=Uint16("
                 "cimtype='uint16', minvalue=0, maxvalue=65535, 4216), "
                 "type=u'uint16', reference_class=None, embedded_object=None, "
                 "is_array=False, array_size=None, class_origin=None, "
                 "propagated=None, qualifiers=NocaseDict([]))), "
                 "('UI32', CIMPr...)"),)
        else:
            lc.check(
                ("pywbem.api.test_id", "DEBUG",
                 "Return:test_id None(CIMInstance(classname='CIM_Foo', "
                 "path=None, properties=NocaseDict(["
                 "('S1', CIMProperty(name='S1', value='Ham', type='string', "
                 "reference_class=None, embedded_object=None, is_array=False, "
                 "array_size=None, class_origin=None, propagated=None, "
                 "qualifiers=NocaseDict([]))), "
                 "('Bool', CIMProperty(name='Bool', value=True, "
                 "type='boolean', reference_class=None, embedded_object=None, "
                 "is_array=False, array_size=None, class_origin=None, "
                 "propagated=None, qualifiers=NocaseDict([]))), "
                 "('UI8', CIMProperty(name='UI8', value=Uint8(cimtype='uint8', "
                 "minvalue=0, maxvalue=255, 42), type='uint8', "
                 "reference_class=None, embedded_object=None, is_array=False, "
                 "array_size=None, class_origin=None, propagated=None, "
                 "qualifiers=NocaseDict([]))), "
                 "('UI16', CIMProperty(name='UI16', value=Uint16("
                 "cimtype='uint16', minvalue=0, maxvalue=65535, 4216), "
                 "type='uint16', reference_class=None, embedded_object=None, "
                 "is_array=False, array_size=None, class_origin=None, "
                 "propagated=None, qualifiers=NocaseDict([]))), "
                 "('UI32', CIMProperty(nam...)"),)

    @log_capture()
    def test_stage_instance_result_all(self, lc):
        instance = self.create_ciminstance()
        self.recorder_setup(detail_level='all')
        exc = None
        self.test_recorder.stage_pywbem_result(instance, exc)

        if six.PY2:
            lc.check(
                ("pywbem.api.test_id", "DEBUG",
                 "Return:test_id None(CIMInstance(classname=u'CIM_Foo', "
                 "path=None, properties=NocaseDict(["
                 "('S1', CIMProperty(name=u'S1', value=u'Ham', "
                 "type=u'string', reference_class=None, "
                 "embedded_object=None, is_array=False, array_size=None, "
                 "class_origin=None, propagated=None, "
                 "qualifiers=NocaseDict([]))), "
                 "('Bool', CIMProperty(name=u'Bool', value=True, "
                 "type=u'boolean', reference_class=None, "
                 "embedded_object=None, is_array=False, array_size=None, "
                 "class_origin=None, propagated=None, "
                 "qualifiers=NocaseDict([]))), "
                 "('UI8', CIMProperty(name=u'UI8', value=Uint8("
                 "cimtype='uint8', minvalue=0, maxvalue=255, 42), "
                 "type=u'uint8', reference_class=None, embedded_object=None, "
                 "is_array=False, array_size=None, class_origin=None, "
                 "propagated=None, qualifiers=NocaseDict([]))), "
                 "('UI16', CIMProperty(name=u'UI16', value=Uint16("
                 "cimtype='uint16', minvalue=0, maxvalue=65535, 4216), "
                 "type=u'uint16', reference_class=None, embedded_object=None, "
                 "is_array=False, array_size=None, class_origin=None, "
                 "propagated=None, qualifiers=NocaseDict([]))), "
                 "('UI32', CIMProperty(name=u'UI32', value=Uint32("
                 "cimtype='uint32', minvalue=0, maxvalue=4294967295, 4232), "
                 "type=u'uint32', reference_class=None, embedded_object=None, "
                 "is_array=False, array_size=None, class_origin=None, "
                 "propagated=None, qualifiers=NocaseDict([]))), "
                 "('UI64', CIMProperty(name=u'UI64', value=Uint64(cimtype"
                 "='uint64', minvalue=0, maxvalue=18446744073709551615, 4264), "
                 "type=u'uint64', reference_class=None, embedded_object=None, "
                 "is_array=False, array_size=None, class_origin=None, "
                 "propagated=None, qualifiers=NocaseDict([]))), "
                 "('SI8', CIMProperty(name=u'SI8', value=Sint8("
                 "cimtype='sint8', minvalue=-128, maxvalue=127, -42), "
                 "type=u'sint8', reference_class=None, embedded_object=None, "
                 "is_array=False, array_size=None, class_origin=None, "
                 "propagated=None, qualifiers=NocaseDict([]))), "
                 "('SI16', CIMProperty(name=u'SI16', value=Sint16("
                 "cimtype='sint16', minvalue=-32768, maxvalue=32767, -4216), "
                 "type=u'sint16', reference_class=None, embedded_object=None, "
                 "is_array=False, array_size=None, class_origin=None, "
                 "propagated=None, qualifiers=NocaseDict([]))), "
                 "('SI32', CIMProperty(name=u'SI32', value=Sint32("
                 "cimtype='sint32', minvalue=-2147483648, "
                 "maxvalue=2147483647, -4232), type=u'sint32', "
                 "reference_class=None, embedded_object=None, "
                 "is_array=False, array_size=None, class_origin=None, "
                 "propagated=None, qualifiers=NocaseDict([]))), "
                 "('SI64', CIMProperty(name=u'SI64', value=Sint64("
                 "cimtype='sint64', minvalue=-9223372036854775808, "
                 "maxvalue=9223372036854775807, -4264), type=u'sint64', "
                 "reference_class=None, embedded_object=None, is_array=False, "
                 "array_size=None, class_origin=None, propagated=None, "
                 "qualifiers=NocaseDict([]))), "
                 "('R32', CIMProperty(name=u'R32', value=Real32("
                 "cimtype='real32', 42.0), type=u'real32', "
                 "reference_class=None, embedded_object=None, is_array=False,"
                 " array_size=None, class_origin=None, propagated=None, "
                 "qualifiers=NocaseDict([]))), "
                 "('R64', CIMProperty(name=u'R64', value=Real64("
                 "cimtype='real64', 42.64), type=u'real64', "
                 "reference_class=None, embedded_object=None, "
                 "is_array=False, array_size=None, class_origin=None, "
                 "propagated=None, qualifiers=NocaseDict([]))), "
                 "('DTI', CIMProperty(name=u'DTI', value=CIMDateTime("
                 "cimtype='datetime', '00000010000049.000020:000'), "
                 "type=u'datetime', reference_class=None, "
                 "embedded_object=None, is_array=False, array_size=None, "
                 "class_origin=None, propagated=None, "
                 "qualifiers=NocaseDict([]))), "
                 "('DTF', CIMProperty(name=u'DTF', value=CIMDateTime("
                 "cimtype='datetime', '20160331193040.654321+120'), "
                 "type=u'datetime', reference_class=None, "
                 "embedded_object=None, is_array=False, array_size=None, "
                 "class_origin=None, propagated=None, "
                 "qualifiers=NocaseDict([]))), "
                 "('DTP', CIMProperty(name=u'DTP', value=CIMDateTime("
                 "cimtype='datetime', '20140922104920.524789-399'), "
                 "type=u'datetime', reference_class=None, "
                 "embedded_object=None, is_array=False, array_size=None, "
                 "class_origin=None, propagated=None, "
                 "qualifiers=NocaseDict([])))"
                 "]), property_list=None, qualifiers=NocaseDict([])))"),)
        else:
            none_result_all = get_inst_return_all_log.replace('GetInstance',
                                                              'None')
            lc.check(
                ("pywbem.api.test_id", "DEBUG", none_result_all))

    @log_capture()
    def test_stage_instance_result_inst_path(self, lc):
        instance = self.create_ciminstance(set_path=True)
        self.recorder_setup(detail_level='paths')
        exc = None
        self.test_recorder.stage_pywbem_result(instance, exc)
        if six.PY2:
            lc.check(("pywbem.api.test_id", "DEBUG",
                      u'Return:test_id None(//woot.com/root/cimv2:CIM_Foo.'
                      u'Chicken="Ham")'))
        else:
            lc.check(("pywbem.api.test_id", "DEBUG",
                      'Return:test_id None(//woot.com/root/cimv2:CIM_Foo.'
                      'Chicken="Ham")'))

    @log_capture()
    def test_stage_instance_result_paths(self, lc):
        self.recorder_setup(detail_level='paths')
        instances = self.create_ciminstances()
        exc = None
        self.test_recorder.stage_pywbem_result(instances, exc)

        result = ('Return:test_id None(//woot.com/root/cimv2:CIM_Foo.'
                  'Chicken="Ham", //woot.com/root/cimv2:CIM_Foo.Chicken="Ham")')

        if six.PY2:
            lc.check(("pywbem.api.test_id", "DEBUG", result))
        else:
            lc.check(("pywbem.api.test_id", "DEBUG", result))

    @log_capture()
    def test_stage_instance_result_pull(self, lc):
        self.recorder_setup(detail_level='paths')
        instances = self.create_ciminstances()
        exc = None

        context = ('test_rtn_context', 'root/blah')
        result_tuple = pull_inst_result_tuple(instances, False, context)

        self.test_recorder.stage_pywbem_result(result_tuple, exc)

        result = (
            'Return:test_id None(pull_inst_result_tuple(context=('
            '\'test_rtn_context\', \'root/blah\'), eos=False, instances='
            '//woot.com/root/cimv2:CIM_Foo.Chicken="Ham", '
            '//woot.com/root/cimv2:CIM_Foo.Chicken="Ham"))')

        lc.check(("pywbem.api.test_id", "DEBUG", result))

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

        result = (
            "Request:test_id POST /cimom 11 http://blah CIMOperation:"
            "'MethodCall' "
            "CIMMethod:'GetInstance' CIMObject:'root/cimv2'\n"
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

        lc.check(("pywbem.http.test_id", "DEBUG", result))

    @log_capture()
    def test_stage_http_request_summary(self, lc):
        """
        Test http request log record with summary as detail level
        """
        self.recorder_setup(detail_level='summary')
        url, target, method, headers, payload = self.build_http_request()
        self.test_recorder.stage_http_request('test_id', 11, url, target,
                                              method, headers, payload)

        result = (
            "Request:test_id POST /cimom 11 http://blah CIMOperation:"
            "'MethodCall' "
            "CIMMethod:'GetInstance' CIMObject:'root/cimv2'\n"
            '    ')

        lc.check(("pywbem.http.test_id", "DEBUG", result))

    @log_capture()
    def test_stage_http_request_int(self, lc):
        """
        Test http log record with integer as detail_level
        """
        self.recorder_setup(detail_level=10)

        url, target, method, headers, payload = self.build_http_request()

        self.test_recorder.stage_http_request('test_id', 11, url, target,
                                              method, headers, payload)

        result = (
            "Request:test_id POST /cimom 11 http://blah CIMOperation:"
            "'MethodCall' "
            "CIMMethod:'GetInstance' CIMObject:'root/cimv2'\n"
            '    <?xml vers...')

        lc.check(("pywbem.http.test_id", "DEBUG", result))

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

        result = ("Response:test_id 200: 11 Content-type:'application/xml; "
                  'charset="utf-8"\' Content-length:\'450\'\n'
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

        lc.check(("pywbem.http.test_id", "DEBUG", result))

    @log_capture()
    def test_stage_http_response_summary(self, lc):
        """
        Test http response log record with 'all' detail_level
        """
        self.recorder_setup(detail_level='summary')

        body = self.build_http_response()

        self.test_recorder.stage_http_response2(body)

        result = ("Response:test_id 200: 11 Content-type:'application/xml; "
                  'charset="utf-8"\' Content-length:\'450\'\n'
                  '    ')

        lc.check(("pywbem.http.test_id", "DEBUG", result))

    @log_capture()
    def test_stage_http_response_int(self, lc):
        """
        Test http response log record with 'all' detail_level
        """
        self.recorder_setup(detail_level=30)

        body = self.build_http_response()

        self.test_recorder.stage_http_response2(body)

        result = ("Response:test_id 200: 11 Content-type:'application/xml; "
                  'charset="utf-8"\' Content-length:\'450\'\n'
                  '    <?xml version="1.0" encoding="...')

        lc.check(("pywbem.http.test_id", "DEBUG", result))


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

        lc.check(
            ("pywbem.api.test_id", "DEBUG",
             "Request:test_id GetInstance(IncludeCla...)"),
            ('pywbem.api.test_id', 'DEBUG',
             'Return:test_id GetInstance(CIMInstanc...)'))

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

        lc.check(('pywbem.api.test_id',
                  'DEBUG',
                  'Request:test_id GetInstance(IncludeClas...)'),
                 ('pywbem.api.test_id',
                  'DEBUG',
                  "Exception:test_id GetInstance('CIMError(6...)"))

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

        if six.PY2:
            lc.check(
                ("pywbem.api.test_id", "DEBUG",
                 "Request:test_id GetInstance(InstanceName=CIMInstanceName("
                 "classname=u'CIM_Foo', keybindings=NocaseDict([('Chicken', "
                 "u'Ham')]), namespace=u'root/cimv2', host=u'woot.com'))"),
                ("pywbem.api.test_id", "DEBUG",
                 "Exception:test_id GetInstance('CIMError(6: Fake "
                 "CIMError)')"),)
        else:
            lc.check(
                ("pywbem.api.test_id", "DEBUG",
                 "Request:test_id GetInstance(InstanceName=CIMInstanceName("
                 "classname='CIM_Foo', keybindings=NocaseDict([('Chicken', "
                 "'Ham')]), namespace='root/cimv2', host='woot.com'))"),
                ("pywbem.api.test_id", "DEBUG",
                 "Exception:test_id GetInstance('CIMError(6: Fake "
                 "CIMError)')"),)

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

        if six.PY2:
            lc.check(
                ("pywbem.api.test_id", "DEBUG",
                 "Request:test_id GetInstance(IncludeClassOrigin=True, "
                 "IncludeQualifiers=True, InstanceName=CIMInstanceName("
                 "classname=u'CIM_Foo', keybindings=NocaseDict([('Chicken', "
                 "u'Ham')]), namespace=u'root/cimv2', host=u'woot.com'), "
                 "LocalOnly=True, PropertyList=['propertyblah'])"),
                ('pywbem.api.test_id',
                 'DEBUG',
                 get_inst_return_all_log_PY2))
        else:
            lc.check(
                ("pywbem.api.test_id", "DEBUG",
                 'Request:test_id GetInstance(IncludeClassOrigin=True, '
                 'IncludeQualifiers=True, '
                 "InstanceName=CIMInstanceName(classname='CIM_Foo', "
                 "keybindings=NocaseDict([('Chicken', 'Ham')]), "
                 "namespace='root/cimv2', "
                 "host='woot.com'), LocalOnly=True, "
                 "PropertyList=['propertyblah'])"),
                ("pywbem.api.test_id", "DEBUG", get_inst_return_all_log),)

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

        lc.check(
            ("pywbem.api.test_id", "DEBUG",
             "Request:test_id EnumerateInstances(ClassName=...)"),
            ('pywbem.api.test_id', 'DEBUG',
             'Return:test_id EnumerateInstances([CIMInstan...)'))

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

        lc.check(
            ("pywbem.api.test_id", "DEBUG",
             "Request:test_id EnumerateInstanceNames(ClassName=...)"),
            ('pywbem.api.test_id', 'DEBUG',
             'Return:test_id EnumerateInstanceNames([CIMInstan...)'))

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

        lc.check(
            ("pywbem.api.test_id", "DEBUG",
             "Request:test_id OpenEnumerateInstances(ClassName='CIM_Foo', "
             "IncludeClassOrigin=True, IncludeQualifiers=True, "
             "LocalOnly=True, PropertyList=['propertyblah'])"),
            ('pywbem.api.test_id', 'DEBUG',
             "Return:test_id OpenEnumerateInstances(pull_inst_result_tuple("
             "context=('test_rtn_context', 'root/blah'), eos=False, "
             "instances=[]))"),)

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

        if six.PY2:
            lc.check(
                ("pywbem.api.test_id", "DEBUG",
                 "Request:test_id OpenEnumerateInstancePaths(ClassName="
                 "'CIM_Foo', ContinueOnError=None, FilterQuery='SELECT A "
                 "from B', FilterQueryLanguage='FQL', MaxObjectCount=100, "
                 "OperationTimeout=10)"),
                ('pywbem.api.test_id', 'DEBUG',
                 "Return:test_id OpenEnumerateInstancePaths("
                 "pull_path_result_tuple(context=('test_rtn_context', "
                 "'root/blah'), eos=False, paths=[CIMInstanceName("
                 "classname=u'CIM_Foo', keybindings=NocaseDict([('Chicken', "
                 "u'Ham')]), namespace=u'root/cimv2', host=u'woot.com'), "
                 "CIMInstanceName(classname=u'CIM_Foo', keybindings="
                 "NocaseDict([('Chicken', u'Ham')]), namespace=u'root/cimv2',"
                 " host=u'woot.com')]))"))

        else:
            lc.check(
                ("pywbem.api.test_id", "DEBUG",
                 "Request:test_id OpenEnumerateInstancePaths("
                 "ClassName='CIM_Foo', "
                 "ContinueOnError=None, FilterQuery='SELECT A from B', "
                 "FilterQueryLanguage='FQL', MaxObjectCount=100, "
                 "OperationTimeout=10)"),
                ('pywbem.api.test_id', 'DEBUG',
                 'Return:test_id '
                 "OpenEnumerateInstancePaths(pull_path_result_tuple("
                 "context=('test_rtn_context', "
                 "'root/blah'), eos=False, paths=[CIMInstanceName("
                 "classname='CIM_Foo', "
                 "keybindings=NocaseDict([('Chicken', 'Ham')]), "
                 "namespace='root/cimv2', "
                 "host='woot.com'), CIMInstanceName(classname='CIM_Foo', "
                 "keybindings=NocaseDict([('Chicken', 'Ham')]), "
                 "namespace='root/cimv2', "
                 "host='woot.com')]))"),)

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

        lc.check(
            ('pywbem.api.test_id', 'DEBUG',
             "Request:test_id Associators(AssocClass...)"),
            ('pywbem.api.test_id', 'DEBUG', 'Return:test_id '
             'Associators([])'))

    @log_capture()
    def test_associators_result_exception(self, lc):
        """Test the ops result log for associators that returns exception"""

        # set recorder to limit response to length of 10
        self.recorder_setup(detail_level=11)

        exc = CIMError(6, "Fake CIMError")
        self.test_recorder.stage_pywbem_result([], exc)

        lc.check(
            ('pywbem.api.test_id', 'DEBUG',
             "Exception:test_id None('CIMError(6...)"),)

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

        lc.check(
            ('pywbem.api.test_id', 'DEBUG',
             "Request:test_id InvokeMethod(MethodName=...)"),
            ('pywbem.api.test_id',
             'DEBUG',
             "Return:test_id InvokeMethod((0, [('Stri...)"))

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

        req = "Request:test_id InvokeMethod(MethodName='Blah', " \
              "ObjectName=CIMInstanceName(classname=u'CIM_Foo', " \
              "keybindings=NocaseDict([('Chicken', u'Ham')]), namespace=" \
              "u'root/cimv2', host=u'woot.com'), Params=OrderedDict(" \
              "[('StringParam', 'Spotty'), ('Uint8', Uint8(cimtype='uint8', " \
              "minvalue=0, maxvalue=255, 1)), ('Sint8', Sint8(cimtype=" \
              "'sint8', minvalue=-128, maxvalue=127, 2))]))"

        if six.PY3:
            req = req.replace("u'", "'")

        lc.check(
            ('pywbem.api.test_id', 'DEBUG', req),
            ('pywbem.api.test_id', 'DEBUG',
             'Return:test_id InvokeMethod(tuple )'))

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

        lc.check(
            ("pywbem.api.test_id", "DEBUG",
             "Request:test_id EnumerateInstanceNames(ClassName=...)"),
            ('pywbem.api.test_id', 'DEBUG',
             'Return:test_id EnumerateInstanceNames([CIMInstan...)'))

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

        api_exp_log_id = 'pywbem.api.%s' % conn_id
        http_exp_log_id = 'pywbem.http.%s' % conn_id
        exc = "Exception:%s GetClass('ConnectionError(Socket error: " \
              "[Errno 113] No route to host)')" % conn_id
        # pylint: disable=line-too-long

        con = "Connection:%s WBEMConnection(url=u'http://blah', creds=None," \
              " conn_id=%s, default_namespace=u'root/cimv2', x509=None, " \
              "verify_callback=None, ca_certs=None, no_verification=False, " \
              "timeout=1, use_pull_operations=False, stats_enabled=False, " \
              "recorders=['LogOperationRecorder'])" % (conn_id, conn_id)

        req = "Request:%s GetClass(ClassName='blah', IncludeClassOrigin=None," \
              " IncludeQualifiers=None, LocalOnly=None, PropertyList=None, " \
              "namespace=None)" % conn_id
        hreq = u"Request:%s POST /cimom 11 http://blah CIMOperation:" \
               "'MethodCall' " \
               "CIMMethod:'GetClass' CIMObject:u'root/cimv2'\n" \
               '<?xml version="1.0" ' \
               'encoding="utf-8" ?>\n<CIM CIMVERSION="2.0" DTDVERSION="2.0">' \
               '<MESSAGE ID=' \
               '"1001" PROTOCOLVERSION="1.0"><SIMPLEREQ><IMETHODCALL ' \
               'NAME="GetClass">' \
               '<LOCALNAMESPACEPATH><NAMESPACE NAME="root"/><NAMESPACE ' \
               'NAME="cimv2"/>' \
               '</LOCALNAMESPACEPATH><IPARAMVALUE NAME="ClassName">' \
               '<CLASSNAME NAME="blah"/>' \
               '</IPARAMVALUE></IMETHODCALL></SIMPLEREQ></MESSAGE></CIM>' % \
               conn_id

        lc.check(
            (api_exp_log_id, 'DEBUG', con),
            (api_exp_log_id, 'DEBUG', req),
            (http_exp_log_id, 'DEBUG', hreq),
            (api_exp_log_id, 'DEBUG', exc)
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

        conn = FakedWBEMConnection('http://blah')
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
        namespace = 'interop'
        schema = install_test_dmtf_schema()
        partial_schema = """
            #pragma locale ("en_US")
            #pragma include ("Interop/CIM_ObjectManager.mof")
            """
        configure_logger('api', log_dest='file',
                         detail_level='summary',
                         log_filename=TEST_OUTPUT_LOG,
                         connection=True, propagate=True)
        conn = FakedWBEMConnection('http://blah')
        conn.compile_mof_string(partial_schema, namespace=namespace,
                                search_paths=[schema.schema_mof_dir])

        conn.GetClass('CIM_ObjectManager', namespace=namespace)

        conn_id = conn.conn_id

        api_exp_log_id = 'pywbem.api.%s' % conn_id
        # pylint: disable=line-too-long
        con = "Connection:%s FakedWBEMConnection(url=u'http://FakedUrl'," \
              " creds=None, default_namespace=u'http://blah')" % (conn_id)

        req = "Request:%s GetClass(ClassName='CIM_ObjectManager', " \
              "IncludeClassOrigin=None, IncludeQualifiers=None, LocalOnly=" \
              "None, PropertyList=None, namespace='interop')" % conn_id

        resp = "Return:%s GetClass(CIMClass CIM_ObjectManager)" % conn_id

        if six.PY3:
            con = con.replace("u\'", "'")

        lc.check(
            (api_exp_log_id, 'DEBUG', con),
            (api_exp_log_id, 'DEBUG', req),
            (api_exp_log_id, 'DEBUG', resp)
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
        namespace = 'interop'
        conn = self.build_repo(namespace)
        configure_logger('all', log_dest='file',
                         log_filename=TEST_OUTPUT_LOG,
                         detail_level=10,
                         connection=conn, propagate=True)
        conn.GetClass('CIM_ObjectManager', namespace=namespace)

        conn_id = conn.conn_id

        api_exp_log_id = 'pywbem.api.%s' % conn_id

        # pylint: disable=line-too-long
        con = 'Connection:%s FakedWBEMC...' % conn_id

        req = "Request:%s GetClass(ClassName=...)" % conn_id

        resp = "Return:%s GetClass(CIMClass(c...)" % conn_id

        if six.PY3:
            con = con.replace("u\'", "'")

        lc.check(
            (api_exp_log_id, 'DEBUG', con),
            (api_exp_log_id, 'DEBUG', req),
            (api_exp_log_id, 'DEBUG', resp)
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
        namespace = 'interop'
        conn = self.build_repo(namespace)

        # Define the detail_level and WBEMConnection object to activate.
        configure_logger('all', detail_level=10, connection=conn,
                         propagate=True)

        # logging_tree_printout()

        conn.GetClass('CIM_ObjectManager', namespace=namespace)

        conn_id = conn.conn_id

        api_exp_log_id = 'pywbem.api.%s' % conn_id

        # pylint: disable=line-too-long
        con = 'Connection:%s FakedWBEMC...' % conn_id

        req = "Request:%s GetClass(ClassName=...)" % conn_id

        resp = "Return:%s GetClass(CIMClass(c...)" % conn_id

        if six.PY3:
            con = con.replace("u\'", "'")

        lc.check(
            (api_exp_log_id, 'DEBUG', con),
            (api_exp_log_id, 'DEBUG', req),
            (api_exp_log_id, 'DEBUG', resp)
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
        namespace = 'interop'
        conn = self.build_repo(namespace)

        # Define the detail_level and WBEMConnection object to activate.
        configure_logger('api', detail_level=10, connection=conn,
                         propagate=True)

        # logging_tree_printout()

        conn.GetClass('CIM_ObjectManager', namespace=namespace)

        conn_id = conn.conn_id

        api_exp_log_id = 'pywbem.api.%s' % conn_id

        # pylint: disable=line-too-long
        con = 'Connection:%s FakedWBEMC...' % conn_id

        req = "Request:%s GetClass(ClassName=...)" % conn_id

        resp = "Return:%s GetClass(CIMClass(c...)" % conn_id

        if six.PY3:
            con = con.replace("u\'", "'")

        lc.check(
            (api_exp_log_id, 'DEBUG', con),
            (api_exp_log_id, 'DEBUG', req),
            (api_exp_log_id, 'DEBUG', resp)
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
        namespace = 'interop'
        conn = self.build_repo(namespace)

        # Define the detail_level and WBEMConnection object to activate.
        configure_logger('api', detail_level=10, connection=conn,
                         propagate=True)

        # logging_tree_printout()

        conn.GetClass('CIM_ObjectManager', namespace=namespace)

        conn_id = conn.conn_id

        api_exp_log_id = 'pywbem.api.%s' % conn_id

        # pylint: disable=line-too-long
        con = 'Connection:%s FakedWBEMC...' % conn_id

        req = "Request:%s GetClass(ClassName=...)" % conn_id

        resp = "Return:%s GetClass(CIMClass(c...)" % conn_id

        if six.PY3:
            con = con.replace("u\'", "'")

        lc.check(
            (api_exp_log_id, 'DEBUG', con),
            (api_exp_log_id, 'DEBUG', req),
            (api_exp_log_id, 'DEBUG', resp)
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
        namespace = 'interop'
        conn = self.build_repo(namespace)

        # Define the detail_level and WBEMConnection object to activate.
        configure_logger('http', detail_level='all', log_dest='file',
                         log_filename=TEST_OUTPUT_LOG,
                         connection=conn, propagate=True)

        conn.GetClass('CIM_ObjectManager', namespace=namespace)

        conn_id = conn.conn_id

        http_exp_log_id = 'pywbem.http.%s' % conn_id

        # pylint: disable=line-too-long
        con = 'Connection:%s FakedWBEMConnection(response_delay=None, ' \
              'WBEMConnection("FakedWBEMConnection(url=u\'http://FakedUrl\', ' \
              'creds=None, conn_id=%s, default_namespace=' \
              'u\'http://blah\', x509=None, verify_callback=None, ' \
              'ca_certs=None, no_verification=False, timeout=None, ' \
              "use_pull_operations=False, " \
              "stats_enabled=False, recorders=[\'LogOperationRecorder\']" \
              ')"))' % (conn_id, conn_id)

        if six.PY3:
            con = con.replace("u\'", "'")

        lc.check(
            (http_exp_log_id, 'DEBUG', con)
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
        namespace = 'interop'
        conn = self.build_repo(namespace)

        # Define the detail_level and WBEMConnection object to activate.
        configure_logger('http', detail_level='all', log_dest=None,
                         connection=conn, propagate=True)

        conn.GetClass('CIM_ObjectManager', namespace=namespace)

        conn_id = conn.conn_id

        http_exp_log_id = 'pywbem.http.%s' % conn_id

        # pylint: disable=line-too-long
        con = 'Connection:%s FakedWBEMConnection(response_delay=None, ' \
              'WBEMConnection("FakedWBEMConnection(url=u\'http://FakedUrl\', ' \
              'creds=None, conn_id=%s, default_namespace=' \
              'u\'http://blah\', x509=None, verify_callback=None, ' \
              'ca_certs=None, no_verification=False, timeout=None, ' \
              "use_pull_operations=False, " \
              "stats_enabled=False, recorders=[\'LogOperationRecorder\']" \
              ')"))' % (conn_id, conn_id)

        if six.PY3:
            con = con.replace("u\'", "'")

        lc.check(
            (http_exp_log_id, 'DEBUG', con)
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

        namespace = 'interop'
        conn = self.build_repo(namespace)

        # Define the detail_level and WBEMConnection object to activate.
        configure_logger('http', detail_level='all', log_dest=None,
                         connection=conn, propagate=True)

        conn.GetClass('CIM_ObjectManager', namespace=namespace)

        conn_id = conn.conn_id

        http_exp_log_id = 'pywbem.http.%s' % conn_id

        # pylint: disable=line-too-long
        con = 'Connection:%s FakedWBEMConnection(response_delay=None, ' \
              'WBEMConnection("FakedWBEMConnection(url=u\'http://FakedUrl\', ' \
              'creds=None, conn_id=%s, default_namespace=' \
              'u\'http://blah\', x509=None, verify_callback=None, ' \
              'ca_certs=None, no_verification=False, timeout=None, ' \
              "use_pull_operations=False, " \
              "stats_enabled=False, recorders=[\'LogOperationRecorder\']" \
              ')"))' % (conn_id, conn_id)

        if six.PY3:
            con = con.replace("u\'", "'")

        lc.check(
            (http_exp_log_id, 'DEBUG', con)
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

        namespace = 'interop'
        conn = self.build_repo(namespace)

        # Define the detail_level and WBEMConnection object to activate.
        configure_logger('http', detail_level='all', log_dest=None,
                         connection=conn, propagate=True)

        conn.GetClass('CIM_ObjectManager', namespace=namespace)

        conn_id = conn.conn_id

        http_exp_log_id = 'pywbem.http.%s' % conn_id

        # pylint: disable=line-too-long
        con = 'Connection:%s FakedWBEMConnection(response_delay=None, ' \
              'WBEMConnection("FakedWBEMConnection(url=u\'http://FakedUrl\', ' \
              'creds=None, conn_id=%s, default_namespace=' \
              'u\'http://blah\', x509=None, verify_callback=None, ' \
              'ca_certs=None, no_verification=False, timeout=None, ' \
              "use_pull_operations=False, " \
              "stats_enabled=False, recorders=[\'LogOperationRecorder\']" \
              ')"))' % (conn_id, conn_id)

        if six.PY3:
            con = con.replace("u\'", "'")

        lc.check(
            (http_exp_log_id, 'DEBUG', con)
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

        namespace = 'interop'
        # Define the detail_level and WBEMConnection object to activate.
        configure_logger('http', detail_level='all',
                         connection=True, propagate=True)
        conn = self.build_repo(namespace)

        conn.GetClass('CIM_ObjectManager', namespace=namespace)

        conn_id = conn.conn_id

        http_exp_log_id = 'pywbem.http.%s' % conn_id

        # pylint: disable=line-too-long
        con = 'Connection:%s FakedWBEMConnection(response_delay=None, ' \
              'WBEMConnection("FakedWBEMConnection(url=u\'http://FakedUrl\', ' \
              'creds=None, conn_id=%s, default_namespace=' \
              'u\'http://blah\', x509=None, verify_callback=None, ' \
              'ca_certs=None, no_verification=False, timeout=None, ' \
              "use_pull_operations=False, " \
              "stats_enabled=False, recorders=[\'LogOperationRecorder\']" \
              ')"))' % (conn_id, conn_id)

        if six.PY3:
            con = con.replace("u\'", "'")

        lc.check(
            (http_exp_log_id, 'DEBUG', con)
        )

    @log_capture()
    def test_err(self, lc):
        """
        Test configure_logger exception
        """
        namespace = 'interop'
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
