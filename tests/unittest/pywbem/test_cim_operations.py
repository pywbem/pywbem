#!/usr/bin/env python
#

"""
Unittest functions in cim_operations.
"""

from __future__ import print_function, absolute_import

import os
import pytest

from pywbem import WBEMConnection, ParseError, DEFAULT_NAMESPACE, CIMError

from pywbem._recorder import LogOperationRecorder
from pywbem._recorder import TestClientRecorder as MyTestClientRecorder
from pywbem.cim_operations import is_subclass
from pywbem_mock import FakedWBEMConnection

from ..utils.dmtf_mof_schema_def import install_test_dmtf_schema
from ..utils.pytest_extensions import simplified_test_function


class TestCreateConnection(object):
    """
    Test construction of WBEMConnection and those functions that do not
    depend on actually creating a connection
    """
    def test_connection_defaults(self):  # pylint: disable=no-self-use
        """
        Test creation of a connection with default init parameters.
        """
        conn = WBEMConnection('http://localhost')
        assert conn.url == 'http://localhost'
        assert conn.creds is None
        assert conn.x509 is None
        assert conn.use_pull_operations is False
        assert conn.stats_enabled is False

    @pytest.mark.parametrize(
        'attr_name, value', [
            ('url', 'http:/myserver'),
            ('creds', ('x', 'y')),
            ('x509', dict(cert_file='c', key_file='k')),
            ('verify_callback', lambda a, b, c, d, e: True),
            ('ca_certs', 'xxx'),
            ('no_verification', True),
            ('timeout', 30),
        ])
    def test_attrs_deprecated_setters(self, attr_name, value):
        # pylint: disable=no-self-use
        """
        Test that the setting of certain attributes is deprecated.
        """
        conn = WBEMConnection('http://localhost')
        with pytest.warns(DeprecationWarning) as rec_warnings:

            # The code to be tested
            setattr(conn, attr_name, value)

        assert len(rec_warnings) == 1

        attr_value = getattr(conn, attr_name)
        assert attr_value == value

    @pytest.mark.parametrize(
        'attr_name, value', [
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
        Test that certain attributes that were previously public are now
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

    def test_no_recorder(self):  # pylint: disable=no-self-use
        """Test creation of wbem connection with specific parameters"""
        creds = ('myname', 'mypw')
        x509 = {'cert_file': 'mycertfile.crt', 'key_file': 'mykeyfile.key'}
        conn = WBEMConnection('http://localhost', creds,
                              default_namespace='root/blah',
                              x509=x509,
                              use_pull_operations=True,
                              stats_enabled=True)
        assert conn.url == 'http://localhost'
        assert conn.creds == creds
        assert conn.default_namespace == 'root/blah'
        assert conn.x509 == x509
        assert conn.stats_enabled is True
        assert conn.use_pull_operations is True

    @pytest.mark.parametrize(
        'kwargs, exp_default_namespace', [
            (dict(), DEFAULT_NAMESPACE),
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
       Definde as a function without the pytest.fixture decorator becasue
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

    # Testcases for WBEMConnection.is_subclass(...)

    # Each list item is a testcase tuple with these items:
    # * desc: Short testcase description.
    # * kwargs: Keyword arguments for the test function:
    #   * init_args: Tuple of positional arguments to is_subclass.
    #   * init_kwargs: Dict of keyword arguments to is_subclass.
    #   * exp_attrs: Dict of expected attributes of resulting object.
    # * exp_exc_types: Expected exception type(s), or None.
    # * exp_warn_types: Expected warning type(s), or None.
    # * condition: Boolean condition for testcase to run, or 'pdb' for
    #   debugger
    (
        "Test of valid call that returns True",
        dict(
            init_args=['CIM_ManagedElement', 'CIM_ObjectManager'],
            exp_attrs=True,
        ),
        None, None, True
    ),
    (
        "Test of valid call that returns False",
        dict(
            init_args=['CIM_ObjectManager', 'CIM_ManagedElement'],
            exp_attrs=False,
        ),
        None, None, True
    ),
    (
        "Test of invalid subclass, not in repo",
        dict(
            init_args=['CIM_ManagedElement', 'CIM_Blah'],
            exp_attrs=True,
        ),
        CIMError, None, True
    ),
    (
        "Test of subclass and superclass ==",
        dict(
            init_args=['CIM_ObjectManager', 'CIM_ObjectManager'],
            exp_attrs=True,
        ),
        None, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_IS_SUBCLASS)
@simplified_test_function
def test_is_subclass(testcase, init_args, exp_attrs):
    # pylint: disable no_self_use,unused-argument
    """
    Test the method is_subclass(ch, ns, super_class, sub).
    """
    conn = build_repo()   # we wanted this to be fixture.
    # The code to be tested
    result = is_subclass(conn, conn.default_namespace, *init_args)

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None
    assert exp_attrs == result
