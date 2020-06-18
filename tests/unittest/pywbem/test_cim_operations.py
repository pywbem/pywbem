#!/usr/bin/env python
#

"""
Unittest functions in _cim_operations.
"""

from __future__ import print_function, absolute_import

import os
import re
import pytest

from ...utils import skip_if_moftab_regenerated
from ..utils.dmtf_mof_schema_def import install_test_dmtf_schema
from ..utils.pytest_extensions import simplified_test_function

# pylint: disable=wrong-import-position, wrong-import-order, invalid-name
from ...utils import import_installed
pywbem = import_installed('pywbem')
from pywbem import WBEMConnection, ParseError, DEFAULT_NAMESPACE, \
    CIMError  # noqa: E402
from pywbem._recorder import LogOperationRecorder  # noqa: E402
from pywbem._recorder import TestClientRecorder as \
    MyTestClientRecorder  # noqa: E402
from pywbem._cim_operations import is_subclass  # noqa: E402
pywbem_mock = import_installed('pywbem_mock')
from pywbem_mock import FakedWBEMConnection  # noqa: E402
# pylint: enable=wrong-import-position, wrong-import-order, invalid-name


TESTCASES_INIT = [

    # the testcase items are tuples with these items:
    # * desc: Testcase description
    # * files: empty files to be created before the test
    # * init_kwargs: dict of init arguments for WBEMConnection, in addition to
    #   the utl argument
    # * exp_attrs: dict of expected WBEMConnection attributes after init
    # * exp_exc: Type of expected exception, or None
    # * exp_exc_regex: Regexp for the expected exception message, or None

    (
        "No optional init parameters, test defaults",
        [],
        dict(),
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
        dict(),
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
        dict(),
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
        dict(),
        TypeError, "cert_file.* must be a string"
    ),
    (
        "x509 parameter that is an existing file (invalid)",
        ['mycertfile.tmp'],
        dict(
            x509='mycertfile.tmp',
        ),
        dict(),
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
        dict(),
        TypeError, "ca_certs .* invalid type"
    ),
    (
        "ca_certs parameter that is a non-existing file (invalid)",
        [],
        dict(
            ca_certs='mycacertfile.tmp',
        ),
        dict(),
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
        dict(),
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
        TESTCASES_INIT)
    def test_init(self, desc, files, init_kwargs, exp_attrs, exp_exc,
                  exp_exc_regex):
        # pylint: disable=no-self-use,unused-argument
        """
        Test initialization of a WBEMConnection object.
        """

        try:
            for fname in files:
                open(fname, 'a').close()  # create empty file

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
            ('timeout', 30),
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

    skip_if_moftab_regenerated()

    conn = build_repo()   # we wanted this to be fixture.
    # The code to be tested
    result = is_subclass(conn, conn.default_namespace, *init_args)

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None
    assert exp_attrs == result
