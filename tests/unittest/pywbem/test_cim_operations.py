#!/usr/bin/env python
#

"""
Unittest functions in _cim_operations.
"""

from __future__ import print_function, absolute_import

import sys
import os
import io
import re
import pytest

from ...utils import skip_if_moftab_regenerated
from ..utils.dmtf_mof_schema_def import install_test_dmtf_schema
from ..utils.pytest_extensions import simplified_test_function
from ..utils.unittest_extensions import assert_copy

# pylint: disable=wrong-import-position, wrong-import-order, invalid-name
from ...utils import import_installed
pywbem = import_installed('pywbem')
from pywbem import WBEMConnection, ParseError, DEFAULT_NAMESPACE, \
    CIMError, CIMInstanceName, CIMClassName, CIMInstance, \
    CIMClass  # noqa: E402
# pylint: disable=redefined-builtin
from pywbem import ConnectionError  # noqa: E402
# pylint: enable=redefined-builtin
from pywbem._recorder import LogOperationRecorder  # noqa: E402
from pywbem._recorder import TestClientRecorder as \
    MyTestClientRecorder  # noqa: E402
pywbem_mock = import_installed('pywbem_mock')
from pywbem_mock import FakedWBEMConnection  # noqa: E402
# pylint: enable=wrong-import-position, wrong-import-order, invalid-name

# Name of null device
DEV_NULL = 'nul' if sys.platform == 'win32' else '/dev/null'

OK = True     # mark tests OK when they execute correctly
RUN = True    # Mark OK = False and current test case being created RUN
FAIL = False  # Any test currently FAILING or not tested yet
SKIP = False


TESTCASES_INIT_WBEMCONNECTION = [

    # Test WBEMConnection init
    # The testcase items are tuples with these items:
    # * desc: Testcase description
    # * files: empty files to be created before the test
    # * init_kwargs: dict of init arguments for WBEMConnection, in addition to
    #   the url argument
    # * exp_attrs: dict of expected WBEMConnection attributes after init
    # * exp_exc: Type of expected exception, or None
    # * exp_exc_regex: Regexp for the expected exception message, or None

    (
        "No optional init parameters, test defaults",
        [],
        {},
        dict(
            creds=None,
            default_namespace='root/cimv2',
            x509=None,
            ca_certs=None,
            no_verification=False,
            timeout=None,
            use_pull_operations=False,
            stats_enabled=False,
            proxies=None,
        ),
        None, None
    ),
    (
        "All optional init parameters, except x509 and ca_certs",
        [],
        dict(
            creds=('myuser', 'mypw'),
            default_namespace='root/myns',
            no_verification=True,
            timeout=30,
            use_pull_operations=True,
            stats_enabled=True,
            proxies=None,
        ),
        dict(
            creds=('myuser', 'mypw'),
            default_namespace='root/myns',
            no_verification=True,
            timeout=30,
            use_pull_operations=True,
            stats_enabled=True,
            proxies=None,
        ),
        None, None
    ),
    (
        "x509 parameter that is a dict with existing cert_file and "
        "existing key_file",
        ['mycertfile.tmp', 'mykeyfile.tmp'],
        dict(
            x509=dict(
                cert_file='mycertfile.tmp',
                key_file='mykeyfile.tmp',
            ),
        ),
        dict(
            x509=dict(
                cert_file='mycertfile.tmp',
                key_file='mykeyfile.tmp',
            ),
        ),
        None, None
    ),
    (
        "x509 parameter that is a dict with existing cert_file and "
        "omitted key_file",
        ['mycertfile.tmp'],
        dict(
            x509=dict(
                cert_file='mycertfile.tmp',
            ),
        ),
        dict(
            x509=dict(
                cert_file='mycertfile.tmp',
            ),
        ),
        None, None
    ),
    (
        "x509 parameter that is a dict with non-existing cert_file "
        "(invalid) and existing key_file",
        ['mykeyfile.tmp'],
        dict(
            x509=dict(
                cert_file='nonexistingcertfile.tmp',
                key_file='mykeyfile.tmp',
            ),
        ),
        {},
        IOError, "Client certificate file .* not found"
    ),
    (
        "x509 parameter that is a dict with existing cert_file "
        "and non-existing key_file (invalid)",
        ['mycertfile.tmp'],
        dict(
            x509=dict(
                cert_file='mycertfile.tmp',
                key_file='nonexistingkeyfile.tmp',
            ),
        ),
        {},
        IOError, "Client key file .* not found"
    ),
    (
        "x509 parameter that is a dict with cert_file=None (invalid) "
        "and key_file=None",
        [],
        dict(
            x509=dict(
                cert_file=None,
                key_file=None,
            ),
        ),
        {},
        TypeError, "cert_file.* must be a string"
    ),
    (
        "x509 parameter that is a dict with cert_file=3 (invalid) "
        " Must be a string",
        [],
        dict(
            x509=dict(
                cert_file=3,
                key_file=None,
            ),
        ),
        {},
        TypeError, "The 'cert_file' item in the x509 parameter must be a string"
    ),
    (
        "x509 parameter that is a dict with cert_file='mycertfile.tmp' "
        " keyfile invalid type",
        [],
        dict(
            x509=dict(
                cert_file='mycertfile.tmp',
                key_file=3,
            ),
        ),
        {},
        TypeError, "The 'key_file' item in the x509 parameter must be a string",
    ),
    (
        "x509 parameter that is a dict with no cert_file key "
        "and key_file=None",
        [],
        dict(
            x509=dict(
                key_file=None,
            ),
        ),
        {},
        ValueError, "The x509 parameter does not have the required key "
        "'cert_file'"
    ),

    (
        "x509 parameter that is an existing file (invalid)",
        ['mycertfile.tmp'],
        dict(
            x509='mycertfile.tmp',
        ),
        {},
        TypeError, "x509 .* must be a dictionary"
    ),
    (
        "ca_certs parameter that is an existing file",
        ['mycacertfile.tmp'],
        dict(
            ca_certs='mycacertfile.tmp',
        ),
        dict(
            ca_certs='mycacertfile.tmp',
        ),
        None, None
    ),
    (
        "ca_certs parameter that is an integer (invalid)",
        [],
        dict(
            ca_certs=42,
        ),
        {},
        TypeError, "ca_certs .* invalid type"
    ),
    (
        "ca_certs parameter that is a non-existing file (invalid)",
        [],
        dict(
            ca_certs='mycacertfile.tmp',
        ),
        {},
        IOError, "file or directory not found"
    ),
    (
        "proxies parameter that is valid",
        [],
        dict(
            proxies={
                'http': 'http://user:pass@10.10.1.10:3128',
                'https': 'http://user:pass@10.10.1.10:1080',
            },
        ),
        dict(
            proxies={
                'http': 'http://user:pass@10.10.1.10:3128',
                'https': 'http://user:pass@10.10.1.10:1080',
            },
        ),
        None, None
    ),
    (
        "proxies parameter that is an invalid type",
        [],
        dict(
            proxies=42,
        ),
        {},
        TypeError, "proxies .* must be a dictionary .*"
    ),
]


class TestCreateConnection(object):
    """
    Test construction of WBEMConnection and those functions that do not
    depend on actually creating a connection
    """

    @pytest.mark.parametrize(
        'desc, files, init_kwargs, exp_attrs, exp_exc, exp_exc_regex',
        TESTCASES_INIT_WBEMCONNECTION)
    def test_init(self, desc, files, init_kwargs, exp_attrs, exp_exc,
                  exp_exc_regex):
        # pylint: disable=no-self-use,unused-argument
        """
        Test initialization of a WBEMConnection object.
        """

        try:
            for fname in files:
                # create empty file
                with io.open(fname, 'a', encoding='utf-8'):
                    pass

            if exp_exc is not None:
                with pytest.raises(exp_exc) as exc_info:

                    # The code to be tested
                    WBEMConnection('http://localhost', **init_kwargs)

                exc = exc_info.value
                exc_msg = str(exc)
                if exp_exc_regex:
                    assert re.search(exp_exc_regex, exc_msg)
            else:

                # The code to be tested
                conn = WBEMConnection('http://localhost', **init_kwargs)

                for name in exp_attrs:
                    exp_value = exp_attrs[name]
                    act_value = getattr(conn, name)
                    assert act_value == exp_value

        finally:
            for fname in files:
                os.remove(fname)

    @pytest.mark.parametrize(
        'attr_name, value', [
            ('url', 'http://myserver:5988'),
            ('creds', ('x', 'y')),
            ('x509', dict(cert_file='c', key_file='k')),
            ('ca_certs', 'xxx'),
            ('no_verification', True),
            ('last_raw_request', '<CIM/>'),
            ('last_raw_reply', '<CIM/>'),
            ('last_raw_reply', '<CIM/>'),
            ('last_request', '<CIM/>'),
            ('last_request_len', 7),
            ('last_reply_len', 7),
        ])
    def test_attrs_readonly(self, attr_name, value):
        # pylint: disable=no-self-use
        """
        Test that certain attributes that were previously settable are now
        read-only and that the original value has not changed when trying to
        modify them.
        """
        conn = WBEMConnection('http://localhost')
        value1 = getattr(conn, attr_name)
        with pytest.raises(AttributeError):

            # The code to be tested
            setattr(conn, attr_name, value)

        value2 = getattr(conn, attr_name)
        assert value2 == value1

    @pytest.mark.parametrize(
        'kwargs, exp_default_namespace', [
            ({}, DEFAULT_NAMESPACE),
            (dict(default_namespace=None), DEFAULT_NAMESPACE),
            (dict(default_namespace=DEFAULT_NAMESPACE), DEFAULT_NAMESPACE),
            (dict(default_namespace='blah'), 'blah'),
        ])
    def test_init_default_namespace(self, kwargs, exp_default_namespace):
        # pylint: disable=no-self-use
        """Test creation of wbem connection with default_namespace values"""
        conn = WBEMConnection('http://localhost', ('name', 'pw'), **kwargs)
        assert conn.default_namespace == exp_default_namespace

    def test_namespace_slashes_init(self):  # pylint: disable=no-self-use
        """Test stripping of leading and trailing slashes in default namespace
        of wbem connection when initializing"""
        conn = WBEMConnection('http://localhost', None,
                              default_namespace='//root/blah//')
        assert conn.default_namespace == 'root/blah'

    def test_namespace_slashes_set(self):  # pylint: disable=no-self-use
        """Test stripping of leading and trailing slashes in default namespace
        of wbem connection when setting the attribute"""
        conn = WBEMConnection('http://localhost', None,
                              default_namespace=None)
        conn.default_namespace = '//root/blah//'
        assert conn.default_namespace == 'root/blah'

    def test_add_operation_recorder(self):  # pylint: disable=no-self-use
        """Test addition of an operation recorder"""
        conn = WBEMConnection('http://localhost')
        conn.add_operation_recorder(LogOperationRecorder('fake_conn_id'))
        # pylint: disable=protected-access
        assert len(conn._operation_recorders) == 1

    def test_add_operation_recorders(self):  # pylint: disable=no-self-use
        """Test addition of multiple operation recorders"""
        conn = WBEMConnection('http://localhost')
        conn.add_operation_recorder(LogOperationRecorder('fake_conn_id'))
        tcr_fn = 'blah.yaml'
        tcr_file = MyTestClientRecorder.open_file(tcr_fn, 'a')
        conn.add_operation_recorder(MyTestClientRecorder(tcr_file))
        # pylint: disable=protected-access
        assert len(conn._operation_recorders) == 2
        tcr_file.close()
        os.remove(tcr_fn)

    def test_add_same_twice(self):  # pylint: disable=no-self-use
        """
        Test addition of same recorder twice. This not allowed so
        generates exception
        """
        conn = WBEMConnection('http://localhost')
        conn.add_operation_recorder(LogOperationRecorder('fake_conn_id'))
        # pylint: disable=protected-access
        assert len(conn._operation_recorders) == 1

        with pytest.raises(ValueError):
            conn.add_operation_recorder(LogOperationRecorder('fake_conn_id'))

    def test_stats_enabled(self):  # pylint: disable=no-self-use
        """
        Test the property stats_enabled setter
        """
        conn = WBEMConnection('http://localhost')
        assert conn.stats_enabled is False
        conn.stats_enabled = True
        assert conn.stats_enabled is True
        conn.stats_enabled = False
        assert conn.stats_enabled is False

    def test_operation_recorder_enabled(self):  # pylint: disable=no-self-use
        """
        Test the property operation_recorder enabled setter
        """
        conn = WBEMConnection('http://localhost')
        conn.add_operation_recorder(LogOperationRecorder('fake_conn_id'))
        assert conn.operation_recorder_enabled is True
        conn.operation_recorder_enabled = False
        assert conn.operation_recorder_enabled is False
        conn.operation_recorder_enabled = True
        assert conn.operation_recorder_enabled is True

    def test_close(self):  # pylint: disable=no-self-use
        """
        Test closing a connection once.
        """
        conn = WBEMConnection('http://localhost')
        assert conn.session is not None
        conn.close()
        assert conn.session is None

    def test_close_twice(self):  # pylint: disable=no-self-use
        """
        Test closing a connection twice.
        """
        conn = WBEMConnection('http://localhost')
        conn.close()
        assert conn.session is None
        with pytest.raises(ConnectionError) as exc_info:
            conn.close()
            exc = exc_info.value
            assert re.match(r'is closed', str(exc))

    def test_close_imethod(self):  # pylint: disable=no-self-use
        """
        Test closing a connection and invoking an intrinsic operation.
        """
        conn = WBEMConnection('http://localhost')
        conn.close()
        assert conn.session is None
        with pytest.raises(ConnectionError) as exc_info:
            conn.GetClass('CIM_Foo')
            exc = exc_info.value
            assert re.match(r'is closed', str(exc))

    def test_close_method(self):  # pylint: disable=no-self-use
        """
        Test closing a connection and invoking a CIM method.
        """
        conn = WBEMConnection('http://localhost')
        conn.close()
        assert conn.session is None
        with pytest.raises(ConnectionError) as exc_info:
            conn.InvokeMethod(ObjectName='CIM_Foo', MethodName='M1')
            exc = exc_info.value
            assert re.match(r'is closed', str(exc))

    def test_close_export(self):  # pylint: disable=no-self-use
        """
        Test closing a connection and invoking an export operation.
        """
        conn = WBEMConnection('http://localhost')
        conn.close()
        assert conn.session is None
        indi = CIMInstance("CIM_AlertIndication")
        with pytest.raises(ConnectionError) as exc_info:
            conn.ExportIndication(NewIndication=indi)
            exc = exc_info.value
            assert re.match(r'is closed', str(exc))

    def test_context_manager(self):  # pylint: disable=no-self-use
        """
        Test the use of WBEMConnection as a context manager.
        """
        with WBEMConnection('http://localhost:5988') as conn:
            assert isinstance(conn, WBEMConnection)
            assert conn.url == 'http://localhost:5988'
            assert conn.session is not None
        assert conn.session is None


def test_conn_set_timeout():
    """
    Test setting the 'timeout' property of WBEMConnection.
    """
    conn = WBEMConnection('http://localhost', timeout=20)
    assert conn.timeout == 20
    conn.timeout = 25
    assert conn.timeout == 25


class TestGetRsltParams(object):
    """Test WBEMConnection._get_rslt_params method."""

    @pytest.mark.parametrize(
        'irval', [None, 'bla', [], {}])
    @pytest.mark.parametrize(
        # enumctxt input, eos input, expected eos, expected exception type
        'ec, eos, eos_exp, exctype_exp', [
            # following are successul returns
            [u'contextblah', u'False', False, None],  # normal enumctxt rtn
            ["", u'True', True, None],                # eos true, enmctxt empty
            [None, u'True', True, None],              # eos true, enmctxt None
            [u'contextblah', u'True', True, None],    # eos tru, cts with value
            # following are exceptions
            [None, None, None, ParseError],      # no values in eos or enumctxt
            [None, u'False', None, ParseError],  # no value in ec and eos False
        ]
    )
    def test_with_params(self, irval, ec, eos, eos_exp, exctype_exp):
        # pylint: disable=no-self-use,protected-access
        """
        Test combminations of IRETURNVALUE, EOS and EnumerationContext for
        both good and fail responses.
        """
        conn = WBEMConnection('http://localhost')
        result = [
            (u'IRETURNVALUE', {}, irval),
            (u'EnumerationContext', None, ec),
            (u'EndOfSequence', None, eos)
        ]

        if exctype_exp:
            with pytest.raises(exctype_exp):

                # pylint: disable=protected-access
                result = conn._get_rslt_params(result, 'root/blah')

        else:

            # pylint: disable=protected-access
            result = conn._get_rslt_params(result, 'root/blah')

            # the _get_rslt_params method sets context to None if eos True
            ecs = None if eos_exp is True else (ec, 'root/blah')
            assert result == (irval, eos_exp, ecs)

    def test_missing(self):
        # pylint: disable=no-self-use
        """
        Test both Enum context and EndOfSequence completely missing.
        Generates exception
        """
        conn = WBEMConnection('http://localhost')
        result = [
            (u'IRETURNVALUE', {}, {})
        ]

        with pytest.raises(ParseError):

            # pylint: disable=protected-access
            result = conn._get_rslt_params(result, 'namespace')


def build_repo():
    """Fixture to initialize the mock environment and install classes.
       Defined as a function without the pytest.fixture decorator because
       there is no way to include a fixture in the signature of a test
       function that uses simplified_test_function. Simplified_test_function
       reports a parameter count difference because of the extram parameter
       that is the fixture and fixtures may not be included in the testcases.
    """
    schema = install_test_dmtf_schema()
    namespace = "root/cimv2"
    partial_schema = """
        #pragma locale ("en_US")
        #pragma include ("Interop/CIM_ObjectManager.mof")
        #pragma include ("Interop/CIM_RegisteredProfile.mof")
        """

    conn = FakedWBEMConnection(default_namespace=namespace)
    conn.compile_mof_string(partial_schema, namespace=namespace,
                            search_paths=[schema.schema_mof_dir])
    return conn


TESTCASES_IS_SUBCLASS = [

    # Testcases for WBEMConnection.is_subclass()

    # Each list item is a testcase tuple with these items:
    # * desc: Short testcase description.
    # * kwargs: Keyword arguments for the test function:
    #   * init_args: Tuple of positional arguments to is_subclass().
    #   * init_kwargs: Dict of keyword arguments to is_subclass().
    #   * exp_attrs: Dict of expected attributes of resulting object.
    # * exp_exc_types: Expected exception type(s), or None.
    # * exp_warn_types: Expected warning type(s), or None.
    # * condition: Boolean condition for testcase to run, or 'pdb' for
    #   debugger

    (
        "Test of valid call with strings that returns True",
        dict(
            init_args=['CIM_ObjectManager', 'CIM_ManagedElement'],
            exp_attrs=True,
        ),
        None, None, True
    ),
    (
        "Test of valid call with CIM objects that returns True",
        dict(
            init_args=[
                CIMClass('CIM_ObjectManager', superclass='CIM_WBEMService'),
                CIMClass('CIM_ManagedElement', superclass=None),
            ],
            exp_attrs=True,
        ),
        None, None, True
    ),
    (
        "Test of valid call with CIM object and string that returns True",
        dict(
            init_args=[
                CIMClass('CIM_ObjectManager', superclass='CIM_WBEMService'),
                'CIM_ManagedElement',
            ],
            exp_attrs=True,
        ),
        None, None, True
    ),
    (
        "Test of valid call with string and CIM object that returns True",
        dict(
            init_args=[
                'CIM_ObjectManager',
                CIMClass('CIM_ManagedElement', superclass=None),
            ],
            exp_attrs=True,
        ),
        None, None, True
    ),
    (
        "Test of valid call that returns False",
        dict(
            init_args=['CIM_ManagedElement', 'CIM_ObjectManager'],
            exp_attrs=False,
        ),
        None, None, True
    ),
    (
        "Test of class equal to superclass",
        dict(
            init_args=['CIM_ObjectManager', 'CIM_ObjectManager'],
            exp_attrs=True,
        ),
        None, None, True
    ),
    (
        "Test of superclass not in repo, returns False",
        dict(
            init_args=['CIM_ManagedElement', 'CIM_Blah'],
            exp_attrs=False,
        ),
        None, None, True
    ),
    (
        "Test of class not in repo (error)",
        dict(
            init_args=['CIM_Blah', 'CIM_ManagedElement'],
            exp_attrs=None,
        ),
        CIMError, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_IS_SUBCLASS)
@simplified_test_function
def test_is_subclass(testcase, init_args, exp_attrs):
    # pylint: disable=unused-argument
    """
    Test the method WBEMConnection.is_subclass().
    """

    skip_if_moftab_regenerated()

    conn = build_repo()   # we wanted this to be fixture.
    # The code to be tested
    result = conn.is_subclass(conn.default_namespace, *init_args)

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None
    assert exp_attrs == result


# TODO List of failure tests to be tested with following test
# methodcall. test objectname
# Test Iter invalid maxcount >- 0 and OperationTimeout < 0
# line 2008, methodcall request with classname no namespace  - not a failue case
# line 2010, methodcall request with classname, use string  - not a failure case
# request with object name not CIMInstanceName, CIMClassName, not string - DONE
# test _iparam_objectname type error if not CIMClassname, instancename,
#     string - DONE
# iparam_classname not CIMClassName or string - DONE
# iparam_instancename not CIMInstanceName or None  - DONE
# modified instance. no path,
# Modified instance no class in path
# modified_instance no classname in modifiedinstance line 3022
# line 4595, iterenumerateinstances CIMClassName input no namespace
# line 4612, close iterenum early.  Not sure this can be done.

TESTCASES_REQUEST_INVALID_PARAMS = [

    # Testcases for WBEMConnection  method calls with invalid params.

    # Each list item is a testcase tuple with these items:
    # * desc: Short testcase description.
    # * kwargs: Keyword arguments for the test function:
    #   * init_kwargs: keyword args for WBEMConnection __init
    #   * method: operation method to call
    #   * args=: Arguments for the operation method being called
    #   * kwargs: Dict of keyword arguments for the WBEMConnection __init
    # * exp_exc_types: Expected exception type(s), or None.
    # * exp_warn_types: Expected warning type(s), or None.
    # * condition: Boolean condition for testcase to run, or 'pdb' for
    #   debugger
    (
        "Test invalid invokemethod objectname (integer)",
        dict(
            init_kwargs={},
            method='invokemethod',
            args=["MethodName", 1],
            kwargs={},
        ),
        TypeError, None, OK
    ),
    (
        "Test invalid invokemethod objectname is None",
        dict(
            init_kwargs={},
            method='invokemethod',
            args=["MethodName", None],
            kwargs={},
        ),
        TypeError, None, OK
    ),
    (
        "Test invalid invokemethod inferred object integer None",
        dict(
            init_kwargs={},
            method='invokemethod',
            args=[None, "ObjectName"],
            kwargs={"param1": 1},
        ),
        TypeError, None, False  # Fails with connection failure.
    ),
    (
        "Test enumerateinstances, fails, classname is not CIMClassname or Str",
        dict(
            init_kwargs={},
            method='enumerateinstances',
            args=[CIMInstanceName("CIM_Blah")],
            kwargs={},
        ),
        TypeError, None, OK
    ),
    (
        "Test GetInstance, invalid InstanceName tyhpe",
        dict(
            init_kwargs={},
            method='getinstance',
            args=[CIMClassName("CIM_Blah")],
            kwargs={},
        ),
        TypeError, None, OK
    ),

    (
        "Test ModifyInstance, No path in ModifiedInstance",
        dict(
            init_kwargs={},
            method='modifyinstance',
            args=[CIMInstance("CIMBlah")],
            kwargs={},
        ),
        ValueError, None, OK
    ),

    (
        "Test EnumerateInstances, Invalid args type",
        dict(
            init_kwargs={},
            method='enumerateinstances',
            args=[CIMClass("CIMBlah")],
            kwargs={},
        ),
        TypeError, None, OK
    ),

    (
        "Test OpenEnumerateInstances, Invalid type for operationtimeout",
        dict(
            init_kwargs={},
            method='openenumerateinstances',
            args=[CIMClass("CIMBlah")],
            kwargs={"OperationTimeout": "shouldbeinteger"},
        ),
        TypeError, None, OK
    ),

    (
        "Test OpenEnumerateInstances, Invalid value for operationtimeout",
        dict(
            init_kwargs={},
            method='openenumerateinstances',
            args=[CIMClass("CIMBlah")],
            kwargs={"OperationTimeout": -30},
        ),
        TypeError, None, OK
    ),

    (
        "Test OpenEnumerateInstancepaths, Invalid type for operationtimeout",
        dict(
            init_kwargs={},
            method='openenumerateinstancepaths',
            args=[CIMClass("CIMBlah")],
            kwargs={"OperationTimeout": "shouldbeinteger"},
        ),
        TypeError, None, OK
    ),

    (
        "Test OpenEnumerateInstancePaths, Invalid value for operationtimeout",
        dict(
            init_kwargs={},
            method='openenumerateinstancepaths',
            args=[CIMClass("CIMBlah")],
            kwargs={"OperationTimeout": -30},
        ),
        TypeError, None, OK
    ),

    (
        "Test pullinstancewithpath, Invalid context type",
        dict(
            init_kwargs={},
            method='pullinstanceswithpath',
            args=[1, 0],
            kwargs={},
        ),
        TypeError, None, OK
    ),

    (
        "Test pullinstancewithpath, context list len ",
        dict(
            init_kwargs={},
            method='pullinstanceswithpath',
            args=[[], 0],
            kwargs={},
        ),
        ValueError, None, OK
    ),

    (
        "Test IterEnumerateInstances, invalid timeout.lt 0",
        dict(
            init_kwargs={},
            method='iterenumerateinstances',
            args=[CIMClassName("CIMBlah")],
            kwargs=dict(OperationTimeout=-1),
        ),
        ValueError, None, OK
    ),

    (
        "Test IterEnumerateInstances, invalid maxobjectcount == 0",
        dict(
            init_kwargs={},
            method='iterenumerateinstances',
            args=[CIMClassName("CIMBlah")],
            kwargs=dict(MaxObjectCount=0),
        ),
        ValueError, None, OK
    ),

    (
        "Test IterEnumerateInstances, Pull not allowed. with Filterquery",
        dict(
            init_kwargs=dict(use_pull_operations=False),
            method='iterenumerateinstances',
            args=[CIMClassName("CIMBlah")],
            kwargs=dict(FilterQuery="blah"),
        ),
        ValueError, None, OK
    ),

    (
        "Test IterEnumerateInstances, Pull not allowed. with FilterQueryLang",
        dict(
            init_kwargs=dict(use_pull_operations=False),
            method='iterenumerateinstances',
            args=[CIMClassName("CIMBlah")],
            kwargs=dict(FilterQueryLanguage="blah"),
        ),
        ValueError, None, OK
    ),

    (
        "Test IterEnumerateInstancePaths, invalid timeout.lt 0",
        dict(
            init_kwargs={},
            method='iterenumerateinstancepaths',
            args=[CIMClassName("CIMBlah")],
            kwargs=dict(OperationTimeout=-1),
        ),
        ValueError, None, OK
    ),

    (
        "Test IterEnumerateInstancePaths, invalid maxobjectcount == 0",
        dict(
            init_kwargs={},
            method='iterenumerateinstancepaths',
            args=[CIMClassName("CIMBlah")],
            kwargs=dict(MaxObjectCount=0),
        ),
        ValueError, None, OK
    ),

    (
        "Test IterEnumerateInstancePaths, Pull not allowed. with Filterquery",
        dict(
            init_kwargs=dict(use_pull_operations=False),
            method='iterenumerateinstancepaths',
            args=[CIMClassName("CIMBlah")],
            kwargs=dict(FilterQuery="blah"),
        ),
        ValueError, None, OK
    ),

    (
        "Test IterEnumerateInstancePaths, Pull not allowed. with "
        "FilterQueryLang",
        dict(
            init_kwargs=dict(use_pull_operations=False),
            method='iterenumerateinstancepaths',
            args=[CIMClassName("CIMBlah")],
            kwargs=dict(FilterQueryLanguage="blah"),
        ),
        ValueError, None, OK
    ),

    (
        "Test IterEnumerateInstances, Pull not allowed. with "
        "ContinueOnError True",
        dict(
            init_kwargs=dict(use_pull_operations=False),
            method='iterenumerateinstances',
            args=[CIMClassName("CIMBlah")],
            kwargs=dict(ContinueOnError=True),
        ),
        ValueError, None, OK
    ),

    (
        "Test IterEnumerateInstancePaths, Pull not allowed. with "
        "ContinueOnError True",
        dict(
            init_kwargs=dict(use_pull_operations=False),
            method='iterenumerateinstancepaths',
            args=[CIMClassName("CIMBlah")],
            kwargs=dict(ContinueOnError=True),
        ),
        ValueError, None, OK
    ),

]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_REQUEST_INVALID_PARAMS)
@simplified_test_function
def test_request_invalid_params(testcase, init_kwargs, method, args, kwargs):
    """Execute the defined method expecting exception"""

    conn = WBEMConnection('http://localhost', **init_kwargs)

    if method == 'invokemethod':
        _ = conn.InvokeMethod(*args, **kwargs)

    elif method == 'enumerateinstances':
        _ = conn.EnumerateInstances(*args, **kwargs)

    elif method == 'getinstance':
        _ = conn.GetInstance(*args, **kwargs)

    elif method == 'modifyinstance':
        conn.ModifyInstance(*args, **kwargs)

    elif method == 'openenumerateinstances':
        _ = conn.OpenEnumerateInstances(*args, **kwargs)

    elif method == 'openenumerateinstancepaths':
        _ = conn.OpenEnumerateInstancePaths(*args, **kwargs)

    elif method == 'pullinstanceswithpath':
        _ = conn.PullInstancesWithPath(*args, **kwargs)

    elif method == 'iterenumerateinstances':
        _ = list(conn.IterEnumerateInstances(*args, **kwargs))

    elif method == 'iterenumerateinstancepaths':
        _ = list(conn.IterEnumerateInstancePaths(*args, **kwargs))

    else:
        assert False, "Test failed. Incomplete. "  \
            "method {0} not found".format(method)

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None


def test_close():
    """
    Test WBEMConnection.close().
    """

    conn = WBEMConnection('http://localhost')

    assert conn.session is not None

    # The code to be tested, good case
    conn.close()

    assert conn.session is None

    with pytest.raises(ConnectionError):

        # The code to be tested, error case
        conn.close()


TESTCASES_COPY_WBEMCONNECTION = [

    # Each list item is a testcase tuple with these items:
    # * desc: Short testcase description.
    # * kwargs: Keyword arguments for the test function:
    #   * files: empty files to be created before the test
    #   * init_kwargs: keyword args for WBEMConnection __init
    #   * set_debug: Boolean that causes debug to be enabled
    #   * add_recorder: Boolean that causes a LogRecorder to be added
    #   * enable_recorder: Boolean that causes recorders to be enabled
    #   * enable_statistics: Boolean that causes statistics to be enabled
    #   * perform_operation: Boolean that causes an operation to be performed
    # * exp_exc_types: Expected exception type(s), or None.
    # * exp_warn_types: Expected warning type(s), or None.
    # * condition: Boolean condition for testcase to run, or 'pdb' for
    #   debugger

    (
        "No optional init parameters, test defaults",
        dict(
            files=[],
            init_kwargs=dict(
                url='http://localhost:5988',
            ),
            set_debug=False,
            add_recorder=False,
            enable_recorder=False,
            enable_statistics=False,
            perform_operation=False,
        ),
        None, None, True
    ),
    (
        "All optional init parameters, except x509 and ca_certs",
        dict(
            files=[],
            init_kwargs=dict(
                url='http://localhost:5988',
                creds=('myuser', 'mypw'),
                default_namespace='root/myns',
                no_verification=True,
                timeout=30,
                use_pull_operations=True,
                stats_enabled=True,
                proxies={
                    'http': 'http://user:pass@10.10.1.10:3128',
                    'https': 'http://user:pass@10.10.1.10:1080',
                },
            ),
            set_debug=False,
            add_recorder=False,
            enable_recorder=False,
            enable_statistics=False,
            perform_operation=False,
        ),
        None, None, True
    ),
    (
        "x509 parameter that is a dict with existing cert_file and "
        "existing key_file",
        dict(
            files=['mycertfile.tmp', 'mykeyfile.tmp'],
            init_kwargs=dict(
                url='http://localhost:5988',
                x509=dict(
                    cert_file='mycertfile.tmp',
                    key_file='mykeyfile.tmp',
                ),
            ),
            set_debug=False,
            add_recorder=False,
            enable_recorder=False,
            enable_statistics=False,
            perform_operation=False,
        ),
        None, None, True
    ),
    (
        "x509 parameter that is a dict with existing cert_file and "
        "omitted key_file",
        dict(
            files=['mycertfile.tmp'],
            init_kwargs=dict(
                url='http://localhost:5988',
                x509=dict(
                    cert_file='mycertfile.tmp',
                ),
            ),
            set_debug=False,
            add_recorder=False,
            enable_recorder=False,
            enable_statistics=False,
            perform_operation=False,
        ),
        None, None, True
    ),
    (
        "with a recorder",
        dict(
            files=[],
            init_kwargs=dict(
                url='http://localhost:5988',
                creds=('myuser', 'mypw'),
                default_namespace='root/myns',
                no_verification=True,
                timeout=30,
                use_pull_operations=True,
                stats_enabled=True,
                proxies={
                    'http': 'http://user:pass@10.10.1.10:3128',
                    'https': 'http://user:pass@10.10.1.10:1080',
                },
            ),
            set_debug=True,
            add_recorder=True,
            enable_recorder=True,
            enable_statistics=True,
            perform_operation=False,
        ),
        None, None, True
    ),
    (
        "with a recorder and an operation performed",
        dict(
            files=[],
            init_kwargs=dict(
                url='http://localhost:5988',
                creds=('myuser', 'mypw'),
                default_namespace='root/myns',
                no_verification=True,
                timeout=1,
                use_pull_operations=True,
                stats_enabled=True,
                proxies={
                    'http': 'http://user:pass@10.10.1.10:3128',
                    'https': 'http://user:pass@10.10.1.10:1080',
                },
            ),
            set_debug=True,
            add_recorder=True,
            enable_recorder=True,
            enable_statistics=True,
            perform_operation=True,
        ),
        None, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_COPY_WBEMCONNECTION)
@simplified_test_function
def test_copy_conn(
        testcase, files, init_kwargs, set_debug, add_recorder, enable_recorder,
        enable_statistics, perform_operation):
    """Test WBEMConnection.copy()"""

    try:
        for fname in files:
            # create empty file
            with io.open(fname, 'a', encoding='utf-8'):
                pass

        # pylint: disable=consider-using-with
        dev_null = io.open(DEV_NULL, 'a', encoding='utf-8')

        conn = WBEMConnection(**init_kwargs)

        if set_debug:
            conn.debug = True

        if add_recorder:
            conn.add_operation_recorder(LogOperationRecorder('fake_conn_id'))
            conn.add_operation_recorder(MyTestClientRecorder(dev_null))

        if enable_recorder:
            conn.operation_recorder_enabled = True

        if enable_statistics:
            conn.stats_enabled = True

        if perform_operation:
            try:
                conn.GetQualifier('Abstract')
            except pywbem.Error:  # Should time out
                pass

        # The code to be tested
        cpy = conn.copy()

        # Ensure that exceptions raised in the remainder of this function
        # are not mistaken as expected exceptions
        assert testcase.exp_exc_types is None

        # pylint: disable=protected-access,unidiomatic-type-check

        # Verify attributes that should have been copied

        assert_copy(cpy.url, conn.url)
        assert_copy(cpy.creds, conn.creds)
        assert_copy(cpy.default_namespace, conn.default_namespace)
        assert_copy(cpy.x509, conn.x509)
        assert_copy(cpy.ca_certs, conn.ca_certs)
        assert_copy(cpy.no_verification, conn.no_verification)
        assert_copy(cpy.timeout, conn.timeout)
        assert_copy(cpy.use_pull_operations, conn.use_pull_operations)
        assert_copy(cpy.stats_enabled, conn.stats_enabled)
        assert_copy(cpy.proxies, conn.proxies)
        assert_copy(cpy._scheme, conn._scheme)
        assert_copy(cpy._host, conn._host)
        assert_copy(cpy._use_enum_inst_pull_operations,
                    conn._use_enum_inst_pull_operations)
        assert_copy(cpy._use_enum_path_pull_operations,
                    conn._use_enum_path_pull_operations)
        assert_copy(cpy._use_ref_inst_pull_operations,
                    conn._use_ref_inst_pull_operations)
        assert_copy(cpy._use_ref_path_pull_operations,
                    conn._use_ref_path_pull_operations)
        assert_copy(cpy._use_assoc_inst_pull_operations,
                    conn._use_assoc_inst_pull_operations)
        assert_copy(cpy._use_assoc_path_pull_operations,
                    conn._use_assoc_path_pull_operations)
        assert_copy(cpy._use_query_pull_operations,
                    conn._use_query_pull_operations)

        # Verify attributes that should have been reset

        assert cpy._debug is False
        assert cpy._last_raw_request is None
        assert cpy._last_raw_reply is None
        assert cpy._last_request is None
        assert cpy._last_request_xml_item is None
        assert cpy._last_reply is None
        assert cpy._last_reply_xml_item is None
        assert cpy._last_request_len == 0
        assert cpy._last_reply_len == 0
        assert cpy._last_operation_time is None
        assert cpy._last_server_response_time is None

        # Session object should be a new object
        assert type(cpy.session) is type(conn.session)  # noqa: E721
        assert id(cpy.session) != id(conn.session)
        # Check that the Session object has adapters for the same schemes
        assert len(cpy.session.adapters) == len(conn.session.adapters)
        for scheme in conn.session.adapters:
            assert scheme in cpy.session.adapters
        # Beyond that, we do not determine whether the Session object is a
        # deep copy or a new object, because that would make this test too
        # much dependent on the internal structure of requests.Session.

        # Recorder objects should be new objects, but with same enabled state
        assert len(cpy._operation_recorders) == len(conn._operation_recorders)
        for i, conn_rec in enumerate(conn._operation_recorders):
            cpy_rec = cpy._operation_recorders[i]
            assert type(cpy_rec) is type(conn_rec)  # noqa: E721
            assert id(cpy_rec) != id(conn_rec)
            assert cpy_rec._pywbem_method is None
            assert cpy_rec._pywbem_args is None
            assert cpy_rec._pywbem_result_ret is None
            assert cpy_rec._pywbem_result_exc is None
            assert cpy_rec.enabled == conn_rec.enabled

        # Statistics object should be a new object, but with same enabled state
        assert type(cpy._statistics) is type(conn._statistics)  # noqa: E721
        assert id(cpy._statistics) != id(conn._statistics)
        assert not cpy._statistics._op_stats
        assert cpy._statistics.enabled == conn._statistics.enabled

        # Verify attributes that have been treated specially

        assert cpy._conn_id != conn._conn_id  # increased

        # pylint: enable=protected-access,unidiomatic-type-check

    finally:
        for fname in files:
            os.remove(fname)
        dev_null.close()
