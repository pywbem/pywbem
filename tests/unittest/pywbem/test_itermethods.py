#!/usr/bin/env python

"""
Test the  WBEMConnection iteration methods (Iter...) by mocking the lower level
WBEMConnection methods that are called by the iteration methods.

Thus, to mock iterEnumerateInstances, we must mock OpenEnumerateInstances,
pullInstanceseWithPath, CloseEnumeration, and EnumerateInstances to be complete.
With that we can execute the variations on IterEnumerateInstances.

This test uses pytest as the test tool.

It specifically tests:
1. To assure that use_pull_operations works
2. The correct parameters are passed to the lower level methods.
3. The correct results are returned.

It does not test for valid parameters if the parameters are tested by lower
level methods because those are the methods that are mocked.
"""

from __future__ import absolute_import, print_function

import pytest
import six

try:
    from unittest.mock import Mock
except ImportError:
    from mock import Mock

# pylint: disable=wrong-import-position, wrong-import-order, invalid-name
from ...utils import import_installed
pywbem = import_installed('pywbem')
from pywbem import WBEMConnection, CIMInstance, CIMClass, CIMInstanceName, \
    CIMClassName, CIMProperty, CIMError, CIM_ERR_NOT_SUPPORTED, \
    CIM_ERR_FAILED  # noqa: E402
from pywbem.config import DEFAULT_ITER_MAXOBJECTCOUNT  # noqa: E402
from pywbem._cim_operations import pull_inst_result_tuple, \
    pull_path_result_tuple, pull_query_result_tuple  # noqa: E402
# pylint: enable=wrong-import-position, wrong-import-order, invalid-name


@pytest.fixture
def tst_class():
    """
    Pytest fixture to return a class.
    """
    cls = CIMClass(
        'CIM_Foo',
        properties=[
            CIMProperty('InstanceID', None, type='string'),
        ],
    )
    return cls


@pytest.fixture
def tst_insts():
    """
    Pytest fixture to return N instances of the class returned by tst_class.
    """
    obj_count = 2
    rtn = []
    for i in six.moves.range(obj_count):
        instanceid = str(i + 1000)
        obj = CIMInstance(
            'CIM_Foo',
            properties=[
                CIMProperty('InstanceID', instanceid, type='string'),
                CIMProperty('Chicken', 'Ham', type='string'),
            ],
            path=CIMInstanceName(
                'CIM_Foo',
                keybindings={'InstanceID': instanceid},
                host='woot.com',
                namespace='root/cimv2',
            ),
        )
        rtn.append(obj)
    return rtn


@pytest.fixture
def tst_paths():
    """
    Pytest fixture to return N instance paths of the class returned by
    tst_class.
    """
    obj_count = 2
    rtn = []
    for i in six.moves.range(obj_count):
        instanceid = str(i + 1000)
        obj = CIMInstanceName(
            'CIM_Foo',
            keybindings={'InstanceID': instanceid},
            host='woot.com',
            namespace='root/cimv2',
        )
        rtn.append(obj)
    return rtn


########################################################################
#
#               IterEnumerateInstances tests
#
########################################################################

class TestIterEnumerateInstances(object):
    """Test IterEnumerateInstances execution"""

    @pytest.mark.parametrize(
        "use_pull_param", [None, False]
    )
    @pytest.mark.parametrize(
        "pull_status", [CIM_ERR_NOT_SUPPORTED, CIM_ERR_FAILED]
    )
    @pytest.mark.parametrize(
        "ns", [None, 'test/testnamespace']
    )
    @pytest.mark.parametrize(
        "cim_classname", [False, True]
    )
    @pytest.mark.parametrize(
        "result_no_host_ns", [False, True]
    )
    @pytest.mark.parametrize(
        "lo, di, iq, ico", [[None, None, None, None],
                            [False, False, False, False],
                            [True, True, True, True]]
    )
    @pytest.mark.parametrize(
        "pl", [None, 'pl1', ['pl1', 'pl2']]
    )
    def test_trad_operation_success(
            self, use_pull_param, pull_status, tst_insts, ns,
            cim_classname, result_no_host_ns, di, iq, lo, ico, pl):
        # pylint: disable=no-self-use,redefined-outer-name
        """
        Test IterEnumerateInstances using the traditional operations,
        either by requesting it via use_pull_operations=False, or by leaving it
        to the implementation via use_pull_operations=None and raising
        NOT_SUPPORTED in the Open operation. This must succeed.

        The test is parameterized to test variations on all parameters. Note
        that it only tests legal parameters.

        The test confirms that the traditional operation receives the correct
        values for all parameters.
        """
        conn = WBEMConnection('dummy', use_pull_operations=use_pull_param)

        if result_no_host_ns:
            rtn_insts = []
            for i in tst_insts:
                rtn_inst = i.copy()
                rtn_inst.path.host = None
                rtn_inst.path.namespace = None
                rtn_insts.append(rtn_inst)
                i.path.namespace = ns or conn.default_namespace
                i.path.host = conn.host
        else:
            rtn_insts = list(tst_insts)

        # mock original function works, open returns CIMError
        conn.EnumerateInstances = Mock(return_value=rtn_insts)
        conn.OpenEnumerateInstances = \
            Mock(side_effect=CIMError(pull_status))

        assert conn.use_pull_operations == use_pull_param
        # pylint: disable=protected-access
        assert conn._use_enum_inst_pull_operations == use_pull_param

        if cim_classname:
            classname = CIMClassName('CIM_Foo', namespace=ns)
        else:
            classname = 'CIM_Foo'

        result = list(conn.IterEnumerateInstances(
            classname,
            namespace=ns,
            LocalOnly=lo,
            DeepInheritance=di,
            IncludeQualifiers=iq,
            IncludeClassOrigin=ico,
            PropertyList=pl))

        conn.EnumerateInstances.assert_called_with(
            classname,
            namespace=ns,
            LocalOnly=lo,
            DeepInheritance=di,
            IncludeQualifiers=iq,
            IncludeClassOrigin=ico,
            PropertyList=pl)

        assert conn._use_enum_inst_pull_operations is False
        assert conn.use_pull_operations == use_pull_param
        assert result == tst_insts

    @pytest.mark.parametrize(
        "pull_status", [CIM_ERR_NOT_SUPPORTED, CIM_ERR_FAILED]
    )
    def test_operation_fail(self, pull_status, tst_insts):
        # pylint: disable=no-self-use,redefined-outer-name
        """
        Test IterEnumerateInstances forcing the use of pull operations
        via use_pull_operations=True, and the Open operation raises
        NOT_SUPPORTED. This must fail.
        """
        conn = WBEMConnection('dummy', use_pull_operations=True)

        conn.EnumerateInstances = Mock(return_value=tst_insts)
        conn.OpenEnumerateInstances = \
            Mock(side_effect=CIMError(pull_status))

        assert conn.use_pull_operations is True
        # pylint: disable=protected-access
        assert conn._use_enum_inst_pull_operations is True

        with pytest.raises(CIMError) as exec_info:
            _ = list(conn.IterEnumerateInstances('CIM_Foo'))

        exc = exec_info.value
        assert exc.status_code == pull_status

        # pylint: disable=protected-access
        assert conn._use_enum_inst_pull_operations is True
        assert conn.use_pull_operations is True

    @pytest.mark.parametrize(
        "use_pull_param", [None, True]
    )
    @pytest.mark.parametrize(
        "ns", [None, 'test/testnamespace']
    )
    @pytest.mark.parametrize(
        "lo, di, iq, ico", [[None, None, None, None],
                            [False, False, False, False],
                            [True, True, True, True]]
    )
    @pytest.mark.parametrize(
        "pl", [None, 'pl1', ['pl1', 'pl2']]
    )
    @pytest.mark.parametrize(
        "fl,fq", [(None, None), ('FQL', 'SELECT')]
    )
    @pytest.mark.parametrize(
        "ot, coe, moc", [[None, None, 100],
                         [10, False, 100]]
    )
    def test_open_operation_success(self, use_pull_param, tst_insts, ns,
                                    lo, di, iq, ico, pl,
                                    fl, fq, ot, coe, moc):
        # pylint: disable=no-self-use,redefined-outer-name
        """
        Test IterEnumerateInstances using the pull operations,
        either by requesting it via use_pull_operations=True, or by leaving it
        to the implementation via use_pull_operations=None and raising
        NOT_SUPPORTED in the traditional operation. This must succeed.

        The test is parameterized to test variations on all parameters. Note
        that it only tests legal parameters.

        The test confirms that the Open operation receives the correct
        values for all parameters, and that the Close operation is not called.
        """
        conn = WBEMConnection('dummy', use_pull_operations=use_pull_param)

        conn.EnumerateInstances = \
            Mock(side_effect=CIMError(CIM_ERR_NOT_SUPPORTED, 'Blah'))
        conn.OpenEnumerateInstances = \
            Mock(return_value=pull_inst_result_tuple(instances=tst_insts,
                                                     eos=True,
                                                     context=None))
        conn.CloseEnumeration = Mock()

        assert conn.use_pull_operations == use_pull_param
        # pylint: disable=protected-access
        assert conn._use_enum_inst_pull_operations == use_pull_param

        result = list(conn.IterEnumerateInstances(
            'CIM_Foo',
            namespace=ns,
            LocalOnly=lo,
            DeepInheritance=di,
            IncludeQualifiers=iq,
            IncludeClassOrigin=ico,
            PropertyList=pl,
            FilterQueryLanguage=fl,
            FilterQuery=fq,
            OperationTimeout=ot,
            ContinueOnError=coe,
            MaxObjectCount=moc))

        conn.OpenEnumerateInstances.assert_called_with(
            'CIM_Foo',
            namespace=ns,
            DeepInheritance=di,
            IncludeClassOrigin=ico,
            PropertyList=pl,
            FilterQueryLanguage=fl,
            FilterQuery=fq,
            OperationTimeout=ot,
            ContinueOnError=coe,
            MaxObjectCount=moc)

        conn.CloseEnumeration.assert_not_called()

        # pylint: disable=protected-access
        assert conn._use_enum_inst_pull_operations is True
        assert conn.use_pull_operations == use_pull_param
        assert result == tst_insts

    @pytest.mark.parametrize(
        "use_pull_param", [None, True]
    )
    def test_pull_operation_success(self, tst_insts, use_pull_param):
        # pylint: disable=no-self-use,redefined-outer-name
        """
        Test IterEnumerateInstances using the pull operations,
        either by requesting it via use_pull_operations=True, or by leaving it
        to the implementation via use_pull_operations=None and raising
        NOT_SUPPORTED in the traditional operation. This must succeed.

        The Open operation returns no result objects, and the Pull operation
        returns all result objects and EOS.

        This does not retest the variations of input parameters because it
        is only confirming that the Pull operation executes.
        """
        conn = WBEMConnection('dummy', use_pull_operations=use_pull_param)

        ctx = ('blah', conn.default_namespace)

        conn.EnumerateInstances = \
            Mock(side_effect=CIMError(CIM_ERR_NOT_SUPPORTED, 'Blah'))
        conn.OpenEnumerateInstances = \
            Mock(return_value=pull_inst_result_tuple(instances=[], eos=False,
                                                     context=ctx))
        conn.PullInstancesWithPath = \
            Mock(return_value=pull_inst_result_tuple(instances=tst_insts,
                                                     eos=True,
                                                     context=None))

        assert conn.use_pull_operations == use_pull_param
        # pylint: disable=protected-access
        assert conn._use_enum_inst_pull_operations == use_pull_param

        result = list(conn.IterEnumerateInstances('CIM_Foo'))

        assert conn._use_enum_inst_pull_operations is True
        assert conn.use_pull_operations == use_pull_param
        assert result == tst_insts

    @pytest.mark.parametrize(
        "use_pull_param", [None, True]
    )
    @pytest.mark.parametrize(
        "max_obj_count", [1, 2]
    )
    @pytest.mark.parametrize(
        "close_after", [0, 1, 2]
    )
    def test_closed_operation_success(self, tst_insts, use_pull_param,
                                      max_obj_count, close_after):
        # pylint: disable=no-self-use,redefined-outer-name
        """
        Test IterEnumerateInstances using the pull operations,
        either by requesting it via use_pull_operations=True, or by leaving it
        to the implementation via use_pull_operations=None and raising
        NOT_SUPPORTED in the traditional operation.

        The iteration is closed after a number of retrievals, sometimes
        prematurely and sometimes not.

        This does not retest the variations of input parameters because it
        is only confirming that the Close operation executes if needed.
        """
        conn = WBEMConnection('dummy', use_pull_operations=use_pull_param)

        tst_insts_open = tst_insts[0:max_obj_count]
        tst_insts_pull = tst_insts[max_obj_count:]
        ctx = ('blah', conn.default_namespace)

        conn.EnumerateInstances = \
            Mock(side_effect=CIMError(CIM_ERR_NOT_SUPPORTED, 'Blah'))
        conn.OpenEnumerateInstances = \
            Mock(return_value=pull_inst_result_tuple(instances=tst_insts_open,
                                                     eos=False,
                                                     context=ctx))
        conn.PullInstancesWithPath = \
            Mock(return_value=pull_inst_result_tuple(instances=tst_insts_pull,
                                                     eos=True,
                                                     context=None))
        conn.CloseEnumeration = Mock()

        assert conn.use_pull_operations == use_pull_param
        # pylint: disable=protected-access
        assert conn._use_enum_inst_pull_operations == use_pull_param

        gen = conn.IterEnumerateInstances(
            'CIM_Foo', MaxObjectCount=max_obj_count)
        result = []
        for _ in six.moves.range(close_after):
            obj = next(gen)
            result.append(obj)
        gen.close()  # close prematurely

        if close_after == 0 or close_after > max_obj_count:
            # Pull has been called; enumeration is exhausted; enumeration was
            # closed automatically within Pull.
            conn.CloseEnumeration.assert_not_called()
        else:
            # Pull has not been called; enumeration is not exhausted;
            # enumeration was closed by calling Close.
            conn.CloseEnumeration.assert_called_with(ctx)
            assert conn._use_enum_inst_pull_operations is True

        assert conn.use_pull_operations == use_pull_param
        assert result == tst_insts[0:close_after]

    @pytest.mark.parametrize(
        "kwargs, exp_exc",
        [
            [dict(OperationTimeout='bla'), TypeError()],
            [dict(OperationTimeout=-1), ValueError()],
            [dict(MaxObjectCount=0), ValueError()],
            [dict(MaxObjectCount=-1), ValueError()],
            [dict(MaxObjectCount=None), ValueError()],
            [dict(MaxObjectCount='bla'), TypeError()],
            [dict(MaxObjectCount='bla'), TypeError()],
        ]
    )
    def test_open_invalid_params(self, tst_insts, kwargs, exp_exc):
        # pylint: disable=no-self-use,redefined-outer-name
        """
        Test IterEnumerateInstances using the pull operations,
        with invalid values and types of those input parameters that are
        actually checked (i.e. OperationTimeout and MaxObjectCount).
        """
        conn = WBEMConnection('dummy', use_pull_operations=True)

        conn.EnumerateInstances = Mock(return_value=tst_insts)
        conn.OpenEnumerateInstances = \
            Mock(side_effect=CIMError(CIM_ERR_NOT_SUPPORTED, 'Blah'))

        with pytest.raises(type(exp_exc)):
            _ = list(conn.IterEnumerateInstances(
                'CIM_Foo',
                **kwargs))

    @pytest.mark.parametrize(
        "kwargs, exp_exc",
        [
            [dict(FilterQueryLanguage='CQL'), ValueError()],
            [dict(FilterQuery='Prop=42'), ValueError()],
            [dict(ContinueOnError=True), ValueError()],
        ]
    )
    def test_trad_invalid_params(self, tst_insts, kwargs, exp_exc):
        # pylint: disable=no-self-use,redefined-outer-name
        """
        Test IterEnumerateInstances using the traditional operations,
        with invalid values and types of those input parameters that are
        actually checked (i.e. FilterQueryLanguage, FilterQuery,
        ContinueOnError).
        """
        conn = WBEMConnection('dummy', use_pull_operations=False)

        conn.EnumerateInstances = Mock(return_value=tst_insts)
        conn.OpenEnumerateInstances = \
            Mock(side_effect=CIMError(CIM_ERR_NOT_SUPPORTED, 'Blah'))

        with pytest.raises(type(exp_exc)):
            _ = list(conn.IterEnumerateInstances(
                'CIM_Foo',
                **kwargs))


########################################################################
#
#               IterEnumerateInstancePaths tests
#
########################################################################

class TestIterEnumerateInstancePaths(object):
    """Test IterEnumerateInstancePaths execution"""

    @pytest.mark.parametrize(
        "use_pull_param", [None, False]
    )
    @pytest.mark.parametrize(
        "pull_status", [CIM_ERR_NOT_SUPPORTED, CIM_ERR_FAILED]
    )
    @pytest.mark.parametrize(
        "ns", [None, 'test/testnamespace']
    )
    @pytest.mark.parametrize(
        "cim_classname", [False, True]
    )
    @pytest.mark.parametrize(
        "result_no_host_ns", [False, True]
    )
    def test_trad_operation_success(
            self, use_pull_param, pull_status, tst_paths, ns,
            cim_classname, result_no_host_ns):
        # pylint: disable=no-self-use,redefined-outer-name
        """
        Test IterEnumerateInstancePaths using the traditional operations,
        either by requesting it via use_pull_operations=False, or by leaving it
        to the implementation via use_pull_operations=None and raising
        NOT_SUPPORTED in the Open operation. This must succeed.

        The test is parameterized to test variations on all parameters. Note
        that it only tests legal parameters.

        The test confirms that the traditional operation receives the correct
        values for all parameters.
        """
        conn = WBEMConnection('dummy', use_pull_operations=use_pull_param)

        if result_no_host_ns:
            rtn_paths = []
            for p in tst_paths:
                rtn_path = p.copy()
                rtn_path.host = None
                rtn_path.namespace = None
                rtn_paths.append(rtn_path)
                p.namespace = ns or conn.default_namespace
                p.host = conn.host
        else:
            rtn_paths = tst_paths

        conn.EnumerateInstanceNames = Mock(return_value=rtn_paths)
        conn.OpenEnumerateInstancePaths = \
            Mock(side_effect=CIMError(pull_status))

        assert conn.use_pull_operations == use_pull_param
        # pylint: disable=protected-access
        assert conn._use_enum_path_pull_operations == use_pull_param

        if cim_classname:
            classname = CIMClassName('CIM_Foo', namespace=ns)
        else:
            classname = 'CIM_Foo'

        result = list(conn.IterEnumerateInstancePaths(
            classname,
            namespace=ns))

        conn.EnumerateInstanceNames.assert_called_with(
            classname,
            namespace=ns)

        # pylint: disable=protected-access
        assert conn._use_enum_path_pull_operations is False
        assert conn.use_pull_operations == use_pull_param
        assert result == tst_paths

    @pytest.mark.parametrize(
        "pull_status", [CIM_ERR_NOT_SUPPORTED, CIM_ERR_FAILED]
    )
    def test_operation_fail(self, pull_status, tst_insts):
        # pylint: disable=no-self-use,redefined-outer-name
        """
        Test IterEnumerateInstancePaths forcing the use of pull operations
        via use_pull_operations=True, and the Open operation raises
        NOT_SUPPORTED. This must fail.
        """
        conn = WBEMConnection('dummy', use_pull_operations=True)

        conn.EnumerateInstanceNames = Mock(return_value=tst_insts)
        conn.OpenEnumerateInstancePaths = \
            Mock(side_effect=CIMError(pull_status))

        assert conn.use_pull_operations is True
        # pylint: disable=protected-access
        assert conn._use_enum_path_pull_operations is True

        with pytest.raises(CIMError) as exec_info:
            _ = list(conn.IterEnumerateInstancePaths('CIM_Foo'))

        exc = exec_info.value
        assert exc.status_code == pull_status

        # pylint: disable=protected-access
        assert conn._use_enum_path_pull_operations is True
        assert conn.use_pull_operations is True

    @pytest.mark.parametrize(
        "use_pull_param", [None, True]
    )
    @pytest.mark.parametrize(
        "ns", [None, 'test/testnamespace']
    )
    @pytest.mark.parametrize(
        "fl,fq", [(None, None), ('FQL', 'SELECT')]
    )
    @pytest.mark.parametrize(
        "ot, coe, moc", [[None, None, 100],
                         [10, False, 100]]
    )
    def test_open_operation_success(self, tst_paths, ns, fl, fq, ot,
                                    coe, moc, use_pull_param):
        # pylint: disable=no-self-use,redefined-outer-name
        """
        Test IterEnumerateInstancePaths using the pull operations,
        either by requesting it via use_pull_operations=True, or by leaving it
        to the implementation via use_pull_operations=None and raising
        NOT_SUPPORTED in the traditional operation. This must succeed.

        The test is parameterized to test variations on all parameters. Note
        that it only tests legal parameters.

        The test confirms that the Open operation receives the correct
        values for all parameters, and that the Close operation is not called.
        """
        conn = WBEMConnection('dummy', use_pull_operations=use_pull_param)

        conn.EnumerateInstanceNames = \
            Mock(side_effect=CIMError(CIM_ERR_NOT_SUPPORTED, 'Blah'))
        conn.OpenEnumerateInstancePaths = \
            Mock(return_value=pull_path_result_tuple(paths=tst_paths,
                                                     eos=True,
                                                     context=None))
        conn.CloseEnumeration = Mock()

        assert conn.use_pull_operations == use_pull_param
        # pylint: disable=protected-access
        assert conn._use_enum_path_pull_operations == use_pull_param

        result = list(conn.IterEnumerateInstancePaths(
            'CIM_Foo',
            namespace=ns,
            FilterQueryLanguage=fl,
            FilterQuery=fq,
            OperationTimeout=ot,
            ContinueOnError=coe,
            MaxObjectCount=moc))

        conn.OpenEnumerateInstancePaths.assert_called_with(
            'CIM_Foo',
            namespace=ns,
            FilterQueryLanguage=fl,
            FilterQuery=fq,
            OperationTimeout=ot,
            ContinueOnError=coe,
            MaxObjectCount=moc)

        conn.CloseEnumeration.assert_not_called()

        # pylint: disable=protected-access
        assert conn._use_enum_path_pull_operations is True
        assert conn.use_pull_operations == use_pull_param
        assert result == tst_paths

    @pytest.mark.parametrize(
        "use_pull_param", [None, True]
    )
    def test_pull_operation_success(self, tst_paths, use_pull_param):
        # pylint: disable=no-self-use,redefined-outer-name
        """
        Test IterEnumerateInstancePaths using the pull operations,
        either by requesting it via use_pull_operations=True, or by leaving it
        to the implementation via use_pull_operations=None and raising
        NOT_SUPPORTED in the traditional operation. This must succeed.

        The Open operation returns no result objects, and the Pull operation
        returns all result objects and EOS.

        This does not retest the variations of input parameters because it
        is only confirming that the Pull operation executes.
        """
        conn = WBEMConnection('dummy', use_pull_operations=use_pull_param)

        ctx = ('blah', conn.default_namespace)

        conn.EnumerateInstanceNames = \
            Mock(side_effect=CIMError(CIM_ERR_NOT_SUPPORTED, 'Blah'))
        conn.OpenEnumerateInstancePaths = \
            Mock(return_value=pull_path_result_tuple(paths=[], eos=False,
                                                     context=ctx))
        conn.PullInstancePaths = \
            Mock(return_value=pull_path_result_tuple(paths=tst_paths,
                                                     eos=True,
                                                     context=None))

        assert conn.use_pull_operations == use_pull_param
        # pylint: disable=protected-access
        assert conn._use_enum_path_pull_operations == use_pull_param

        result = list(conn.IterEnumerateInstancePaths('CIM_Foo'))

        assert conn.use_pull_operations == use_pull_param
        # pylint: disable=protected-access
        assert conn._use_enum_path_pull_operations is True

        assert result == tst_paths

    @pytest.mark.parametrize(
        "use_pull_param", [None, True]
    )
    @pytest.mark.parametrize(
        "max_obj_count", [1, 2]
    )
    @pytest.mark.parametrize(
        "close_after", [0, 1, 2]
    )
    def test_closed_operation_success(self, tst_paths, use_pull_param,
                                      max_obj_count, close_after):
        # pylint: disable=no-self-use,redefined-outer-name
        """
        Test IterEnumerateInstancePaths using the pull operations,
        either by requesting it via use_pull_operations=True, or by leaving it
        to the implementation via use_pull_operations=None and raising
        NOT_SUPPORTED in the traditional operation.

        The iteration is closed after a number of retrievals, sometimes
        prematurely and sometimes not.

        This does not retest the variations of input parameters because it
        is only confirming that the Close operation executes if needed.
        """
        conn = WBEMConnection('dummy', use_pull_operations=use_pull_param)

        tst_paths_open = tst_paths[0:max_obj_count]
        tst_paths_pull = tst_paths[max_obj_count:]
        ctx = ('blah', conn.default_namespace)

        conn.EnumerateInstanceNames = \
            Mock(side_effect=CIMError(CIM_ERR_NOT_SUPPORTED, 'Blah'))
        conn.OpenEnumerateInstancePaths = \
            Mock(return_value=pull_path_result_tuple(paths=tst_paths_open,
                                                     eos=False,
                                                     context=ctx))
        conn.PullInstancePaths = \
            Mock(return_value=pull_path_result_tuple(paths=tst_paths_pull,
                                                     eos=True,
                                                     context=None))
        conn.CloseEnumeration = Mock()

        assert conn.use_pull_operations == use_pull_param
        # pylint: disable=protected-access
        assert conn._use_enum_path_pull_operations == use_pull_param

        gen = conn.IterEnumerateInstancePaths(
            'CIM_Foo', MaxObjectCount=max_obj_count)
        result = []
        for _ in six.moves.range(close_after):
            obj = next(gen)
            result.append(obj)
        gen.close()  # close prematurely

        if close_after == 0 or close_after > max_obj_count:
            # Pull has been called; enumeration is exhausted; enumeration was
            # closed automatically within Pull.
            conn.CloseEnumeration.assert_not_called()
        else:
            # Pull has not been called; enumeration is not exhausted;
            # enumeration was closed by calling Close.
            conn.CloseEnumeration.assert_called_with(ctx)
            assert conn._use_enum_path_pull_operations is True

        assert conn.use_pull_operations == use_pull_param
        assert result == tst_paths[0:close_after]

    @pytest.mark.parametrize(
        "kwargs, exp_exc",
        [
            [dict(OperationTimeout='bla'), TypeError()],
            [dict(OperationTimeout=-1), ValueError()],
            [dict(MaxObjectCount=0), ValueError()],
            [dict(MaxObjectCount=-1), ValueError()],
            [dict(MaxObjectCount=None), ValueError()],
            [dict(MaxObjectCount='bla'), TypeError()],
            [dict(MaxObjectCount='bla'), TypeError()],
        ]
    )
    def test_open_invalid_params(self, tst_paths, kwargs, exp_exc):
        # pylint: disable=no-self-use,redefined-outer-name
        """
        Test IterEnumerateInstancePaths using the pull operations,
        with invalid values and types of those input parameters that are
        actually checked (i.e. OperationTimeout and MaxObjectCount).
        """
        conn = WBEMConnection('dummy', use_pull_operations=True)

        conn.EnumerateInstanceNames = Mock(return_value=tst_paths)
        conn.OpenEnumeratePaths = \
            Mock(side_effect=CIMError(CIM_ERR_NOT_SUPPORTED, 'Blah'))

        with pytest.raises(type(exp_exc)):
            _ = list(conn.IterEnumerateInstancePaths(
                'CIM_Foo',
                **kwargs))

    @pytest.mark.parametrize(
        "kwargs, exp_exc",
        [
            [dict(FilterQueryLanguage='CQL'), ValueError()],
            [dict(FilterQuery='Prop=42'), ValueError()],
            [dict(ContinueOnError=True), ValueError()],
        ]
    )
    def test_trad_invalid_params(self, tst_paths, kwargs, exp_exc):
        # pylint: disable=no-self-use,redefined-outer-name
        """
        Test IterEnumerateInstancePaths using the traditional operations,
        with invalid values and types of those input parameters that are
        actually checked (i.e. FilterQueryLanguage, FilterQuery,
        ContinueOnError).
        """
        conn = WBEMConnection('dummy', use_pull_operations=False)

        conn.EnumerateInstanceNames = Mock(return_value=tst_paths)
        conn.OpenEnumeratePaths = \
            Mock(side_effect=CIMError(CIM_ERR_NOT_SUPPORTED, 'Blah'))

        with pytest.raises(type(exp_exc)):
            _ = list(conn.IterEnumerateInstancePaths(
                'CIM_Foo',
                **kwargs))


########################################################################
#
#               IterReferenceInstances tests
#
########################################################################

class TestIterReferenceInstances(object):
    """Test IterReferenceInstances execution"""

    @staticmethod
    def target_path(ns):
        """
        Return a valid target path for the calls
        """
        return CIMInstanceName('CIM_blah',
                               keybindings={'InstanceID': "1234"},
                               host='woot.com',
                               namespace=ns)

    @pytest.mark.parametrize(
        "use_pull_param", [None, False]
    )
    @pytest.mark.parametrize(
        "pull_status", [CIM_ERR_NOT_SUPPORTED, CIM_ERR_FAILED]
    )
    @pytest.mark.parametrize(
        "ns", [None, 'test/testnamespace']
    )
    @pytest.mark.parametrize(
        "iq, ico", [[None, None],
                    [False, False],
                    [True, True]]
    )
    # result_role, result_class
    @pytest.mark.parametrize(
        "ro, rc", [[None, None],
                   [None, 'CIM_Blah'],
                   ['RRole', None],
                   ['RRole', 'CIM_Blah']]
    )
    @pytest.mark.parametrize(
        "pl", [None, 'pl1', ['pl1', 'pl2']]
    )
    def test_trad_operation_success(
            self, use_pull_param, pull_status, tst_insts, ns,
            rc, ro, iq, ico, pl,):
        # pylint: disable=no-self-use,redefined-outer-name
        """
        Test IterReferenceInstances using the traditional operations,
        either by requesting it via use_pull_operations=False, or by leaving it
        to the implementation via use_pull_operations=None and raising
        NOT_SUPPORTED in the Open operation. This must succeed.

        The test is parameterized to test variations on all parameters. Note
        that it only tests legal parameters.

        The test confirms that the traditional operation receives the correct
        values for all parameters.
        """
        conn = WBEMConnection('dummy', use_pull_operations=use_pull_param)

        # mock original function works, open returns CIMError
        conn.References = Mock(return_value=tst_insts)
        conn.OpenReferenceInstances = \
            Mock(side_effect=CIMError(pull_status))

        assert conn.use_pull_operations == use_pull_param
        # pylint: disable=protected-access
        assert conn._use_ref_inst_pull_operations == use_pull_param

        result = list(conn.IterReferenceInstances(
            self.target_path(ns),
            ResultClass=rc,
            Role=ro,
            IncludeQualifiers=iq,
            IncludeClassOrigin=ico,
            PropertyList=pl))

        conn.References.assert_called_with(
            self.target_path(ns),
            ResultClass=rc,
            Role=ro,
            IncludeQualifiers=iq,
            IncludeClassOrigin=ico,
            PropertyList=pl)

        assert conn._use_ref_inst_pull_operations is False
        assert conn.use_pull_operations == use_pull_param
        assert result == tst_insts

    @pytest.mark.parametrize(
        "pull_status", [CIM_ERR_NOT_SUPPORTED, CIM_ERR_FAILED]
    )
    def test_operation_fail(self, pull_status, tst_insts):
        # pylint: disable=no-self-use,redefined-outer-name
        """
        Test IterReferenceInstances forcing the use of pull operations
        via use_pull_operations=True, and the Open operation raises
        NOT_SUPPORTED. This must fail.
        """
        conn = WBEMConnection('dummy', use_pull_operations=True)

        conn.References = Mock(return_value=tst_insts)
        conn.OpenReferenceInstances = \
            Mock(side_effect=CIMError(pull_status))

        assert conn.use_pull_operations is True
        # pylint: disable=protected-access
        assert conn._use_ref_inst_pull_operations is True

        with pytest.raises(CIMError) as exec_info:
            _ = list(conn.IterReferenceInstances(
                self.target_path('root/cimv2')))

        exc = exec_info.value
        assert exc.status_code == pull_status

        # pylint: disable=protected-access
        assert conn._use_ref_inst_pull_operations is True
        assert conn.use_pull_operations is True

    @pytest.mark.parametrize(
        "use_pull_param", [None, True]
    )
    @pytest.mark.parametrize(
        "ns", [None, 'test/testnamespace']
    )
    @pytest.mark.parametrize(
        "iq, ico", [[None, None],
                    [False, False],
                    [True, True]]
    )
    # result_role, result_class
    @pytest.mark.parametrize(
        "ro, rc", [[None, None],
                   [None, 'CIM_Blah'],
                   ['RRole', None],
                   ['RRole', 'CIM_Blah']]
    )
    @pytest.mark.parametrize(
        "pl", [None, 'pl1', ['pl1', 'pl2']]
    )
    @pytest.mark.parametrize(
        "fl,fq", [(None, None), ('FQL', 'SELECT')]
    )
    @pytest.mark.parametrize(
        "ot, coe, moc", [[None, None, 100],
                         [10, False, 100]]
    )
    def test_open_operation_success(self, use_pull_param, tst_insts, ns,
                                    rc, ro, iq, ico, pl, fl, fq, ot, coe,
                                    moc):
        # pylint: disable=no-self-use,redefined-outer-name
        """
        Test IterReferenceInstances using the pull operations,
        either by requesting it via use_pull_operations=True, or by leaving it
        to the implementation via use_pull_operations=None and raising
        NOT_SUPPORTED in the traditional operation. This must succeed.

        The test is parameterized to test variations on all parameters. Note
        that it only tests legal parameters.

        The test confirms that the Open operation receives the correct
        values for all parameters, and that the Close operation is not called.
        """
        conn = WBEMConnection('dummy', use_pull_operations=use_pull_param)

        conn.References = \
            Mock(side_effect=CIMError(CIM_ERR_NOT_SUPPORTED, 'Blah'))
        conn.OpenReferenceInstances = \
            Mock(return_value=pull_inst_result_tuple(instances=tst_insts,
                                                     eos=True,
                                                     context=None))
        conn.CloseEnumeration = Mock()

        assert conn.use_pull_operations == use_pull_param
        # pylint: disable=protected-access
        assert conn._use_ref_inst_pull_operations == use_pull_param

        result = list(conn.IterReferenceInstances(
            self.target_path(ns),
            ResultClass=rc,
            Role=ro,
            IncludeQualifiers=iq,
            IncludeClassOrigin=ico,
            PropertyList=pl,
            FilterQueryLanguage=fl,
            FilterQuery=fq,
            OperationTimeout=ot,
            ContinueOnError=coe,
            MaxObjectCount=moc))

        conn.OpenReferenceInstances.assert_called_with(
            self.target_path(ns),
            ResultClass=rc,
            Role=ro,
            IncludeClassOrigin=ico,
            PropertyList=pl,
            FilterQueryLanguage=fl,
            FilterQuery=fq,
            OperationTimeout=ot,
            ContinueOnError=coe,
            MaxObjectCount=moc)

        conn.CloseEnumeration.assert_not_called()

        # pylint: disable=protected-access
        assert conn._use_ref_inst_pull_operations is True
        assert conn.use_pull_operations == use_pull_param
        assert result == tst_insts

    @pytest.mark.parametrize(
        "use_pull_param", [None, True]
    )
    def test_pull_operation_success(self, tst_insts, use_pull_param):
        # pylint: disable=no-self-use,redefined-outer-name
        """
        Test IterReferenceInstances using the pull operations,
        either by requesting it via use_pull_operations=True, or by leaving it
        to the implementation via use_pull_operations=None and raising
        NOT_SUPPORTED in the traditional operation. This must succeed.

        The Open operation returns no result objects, and the Pull operation
        returns all result objects and EOS.

        This does not retest the variations of input parameters because it
        is only confirming that the Pull operation executes.
        """
        conn = WBEMConnection('dummy', use_pull_operations=use_pull_param)

        ctx = ('blah', conn.default_namespace)

        conn.References = \
            Mock(side_effect=CIMError(CIM_ERR_NOT_SUPPORTED, 'Blah'))
        conn.OpenReferenceInstances = \
            Mock(return_value=pull_inst_result_tuple(instances=[], eos=False,
                                                     context=ctx))
        conn.PullInstancesWithPath = \
            Mock(return_value=pull_inst_result_tuple(instances=tst_insts,
                                                     eos=True,
                                                     context=None))

        assert conn.use_pull_operations == use_pull_param
        # pylint: disable=protected-access
        assert conn._use_ref_inst_pull_operations == use_pull_param

        result = list(conn.IterReferenceInstances(
            self.target_path('root/cimv2')))

        assert conn._use_ref_inst_pull_operations is True
        assert conn.use_pull_operations == use_pull_param
        assert result == tst_insts

    @pytest.mark.parametrize(
        "use_pull_param", [None, True]
    )
    @pytest.mark.parametrize(
        "max_obj_count", [1, 2]
    )
    @pytest.mark.parametrize(
        "close_after", [0, 1, 2]
    )
    def test_closed_operation_success(self, tst_insts, use_pull_param,
                                      max_obj_count, close_after):
        # pylint: disable=no-self-use,redefined-outer-name
        """
        Test IterReferenceInstances using the pull operations,
        either by requesting it via use_pull_operations=True, or by leaving it
        to the implementation via use_pull_operations=None and raising
        NOT_SUPPORTED in the traditional operation.

        The iteration is closed after a number of retrievals, sometimes
        prematurely and sometimes not.

        This does not retest the variations of input parameters because it
        is only confirming that the Close operation executes if needed.
        """
        conn = WBEMConnection('dummy', use_pull_operations=use_pull_param)

        tst_insts_open = tst_insts[0:max_obj_count]
        tst_insts_pull = tst_insts[max_obj_count:]
        ctx = ('blah', conn.default_namespace)

        conn.References = \
            Mock(side_effect=CIMError(CIM_ERR_NOT_SUPPORTED, 'Blah'))
        conn.OpenReferenceInstances = \
            Mock(return_value=pull_inst_result_tuple(instances=tst_insts_open,
                                                     eos=False,
                                                     context=ctx))
        conn.PullInstancesWithPath = \
            Mock(return_value=pull_inst_result_tuple(instances=tst_insts_pull,
                                                     eos=True,
                                                     context=None))
        conn.CloseEnumeration = Mock()

        assert conn.use_pull_operations == use_pull_param
        # pylint: disable=protected-access
        assert conn._use_ref_inst_pull_operations == use_pull_param

        gen = conn.IterReferenceInstances(
            self.target_path('root/cimv2'), MaxObjectCount=max_obj_count)
        result = []
        for _ in six.moves.range(close_after):
            obj = next(gen)
            result.append(obj)
        gen.close()  # close prematurely

        if close_after == 0 or close_after > max_obj_count:
            # Pull has been called; enumeration is exhausted; enumeration was
            # closed automatically within Pull.
            conn.CloseEnumeration.assert_not_called()
        else:
            # Pull has not been called; enumeration is not exhausted;
            # enumeration was closed by calling Close.
            conn.CloseEnumeration.assert_called_with(ctx)
            assert conn._use_ref_inst_pull_operations is True

        assert conn.use_pull_operations == use_pull_param
        assert result == tst_insts[0:close_after]

    @pytest.mark.parametrize(
        "kwargs, exp_exc",
        [
            [dict(OperationTimeout='bla'), TypeError()],
            [dict(OperationTimeout=-1), ValueError()],
            [dict(MaxObjectCount=0), ValueError()],
            [dict(MaxObjectCount=-1), ValueError()],
            [dict(MaxObjectCount=None), ValueError()],
            [dict(MaxObjectCount='bla'), TypeError()],
            [dict(MaxObjectCount='bla'), TypeError()],
        ]
    )
    def test_open_invalid_params(self, tst_insts, kwargs, exp_exc):
        # pylint: disable=no-self-use,redefined-outer-name
        """
        Test IterReferenceInstances using the pull operations,
        with invalid values and types of those input parameters that are
        actually checked (i.e. OperationTimeout and MaxObjectCount).
        """
        conn = WBEMConnection('dummy', use_pull_operations=True)

        conn.References = Mock(return_value=tst_insts)
        conn.OpenReferenceInstances = \
            Mock(side_effect=CIMError(CIM_ERR_NOT_SUPPORTED, 'Blah'))

        with pytest.raises(type(exp_exc)):
            _ = list(conn.IterReferenceInstances(
                self.target_path('root/x'),
                **kwargs))

    @pytest.mark.parametrize(
        "kwargs, exp_exc",
        [
            [dict(FilterQueryLanguage='CQL'), ValueError()],
            [dict(FilterQuery='Prop=42'), ValueError()],
            [dict(ContinueOnError=True), ValueError()],
        ]
    )
    def test_trad_invalid_params(self, tst_insts, kwargs, exp_exc):
        # pylint: disable=no-self-use,redefined-outer-name
        """
        Test IterEnumerateInstances using the traditional operations,
        with invalid values and types of those input parameters that are
        actually checked (i.e. FilterQueryLanguage, FilterQuery,
        ContinueOnError).
        """
        conn = WBEMConnection('dummy', use_pull_operations=False)

        conn.References = Mock(return_value=tst_insts)
        conn.OpenReferenceInstances = \
            Mock(side_effect=CIMError(CIM_ERR_NOT_SUPPORTED, 'Blah'))

        with pytest.raises(type(exp_exc)):
            _ = list(conn.IterReferenceInstances(
                self.target_path('root/x'),
                **kwargs))


########################################################################
#
#               IterReferenceInstancePaths tests
#
########################################################################

class TestIterReferenceInstancePaths(object):
    """Test IterReferenceInstancePaths execution"""

    @staticmethod
    def target_path(ns):
        """
        Return a valid target path for the calls
        """
        return CIMInstanceName('CIM_blah',
                               keybindings={'InstanceID': "1234"},
                               host='woot.com',
                               namespace=ns)

    @pytest.mark.parametrize(
        "use_pull_param", [None, False]
    )
    @pytest.mark.parametrize(
        "pull_status", [CIM_ERR_NOT_SUPPORTED, CIM_ERR_FAILED]
    )
    @pytest.mark.parametrize(
        "ns", [None, 'test/testnamespace']
    )
    # result_role, result_class
    @pytest.mark.parametrize(
        "ro, rc", [[None, None],
                   [None, 'CIM_Blah'],
                   ['RRole', None],
                   ['RRole', 'CIM_Blah']]
    )
    def test_trad_operation_success(
            self, use_pull_param, pull_status, tst_insts, ns, rc, ro):
        # pylint: disable=no-self-use,redefined-outer-name
        """
        Test IterReferenceInstancePaths using the traditional operations,
        either by requesting it via use_pull_operations=False, or by leaving it
        to the implementation via use_pull_operations=None and raising
        NOT_SUPPORTED in the Open operation. This must succeed.

        The test is parameterized to test variations on all parameters. Note
        that it only tests legal parameters.

        The test confirms that the traditional operation receives the correct
        values for all parameters.
        """
        conn = WBEMConnection('dummy', use_pull_operations=use_pull_param)

        # mock original function works, open returns CIMError
        conn.ReferenceNames = Mock(return_value=tst_insts)
        conn.OpenReferenceInstancePaths = \
            Mock(side_effect=CIMError(pull_status))

        assert conn.use_pull_operations == use_pull_param
        # pylint: disable=protected-access
        assert conn._use_ref_path_pull_operations == use_pull_param

        result = list(conn.IterReferenceInstancePaths(
            self.target_path(ns),
            ResultClass=rc,
            Role=ro))

        conn.ReferenceNames.assert_called_with(
            self.target_path(ns),
            ResultClass=rc,
            Role=ro)

        assert conn._use_ref_path_pull_operations is False
        assert conn.use_pull_operations == use_pull_param
        assert result == tst_insts

    @pytest.mark.parametrize(
        "pull_status", [CIM_ERR_NOT_SUPPORTED, CIM_ERR_FAILED]
    )
    def test_operation_fail(self, pull_status, tst_insts):
        # pylint: disable=no-self-use,redefined-outer-name
        """
        Test IterReferenceInstancePaths forcing the use of pull operations
        via use_pull_operations=True, and the Open operation raises
        NOT_SUPPORTED. This must fail.
        """
        conn = WBEMConnection('dummy', use_pull_operations=True)

        conn.ReferenceNames = Mock(return_value=tst_insts)
        conn.OpenReferenceInstancePaths = \
            Mock(side_effect=CIMError(pull_status))

        assert conn.use_pull_operations is True
        # pylint: disable=protected-access
        assert conn._use_ref_path_pull_operations is True

        with pytest.raises(CIMError) as exec_info:
            _ = list(conn.IterReferenceInstancePaths(
                self.target_path('root/cimv2')))

        exc = exec_info.value
        assert exc.status_code == pull_status

        # pylint: disable=protected-access
        assert conn._use_ref_path_pull_operations is True
        assert conn.use_pull_operations is True

    @pytest.mark.parametrize(
        "use_pull_param", [None, True]
    )
    @pytest.mark.parametrize(
        "ns", [None, 'test/testnamespace']
    )
    # result_role, result_class
    @pytest.mark.parametrize(
        "ro, rc", [[None, None],
                   [None, 'CIM_Blah'],
                   ['RRole', None],
                   ['RRole', 'CIM_Blah']]
    )
    @pytest.mark.parametrize(
        "fl,fq", [(None, None), ('FQL', 'SELECT')]
    )
    @pytest.mark.parametrize(
        "ot, coe, moc", [[None, None, 100],
                         [10, False, 100]]
    )
    def test_open_operation_success(self, use_pull_param, tst_paths, ns,
                                    rc, ro, fl, fq, ot, coe, moc):
        # pylint: disable=no-self-use,redefined-outer-name
        """
        Test IterReferenceInstancePaths using the pull operations,
        either by requesting it via use_pull_operations=True, or by leaving it
        to the implementation via use_pull_operations=None and raising
        NOT_SUPPORTED in the traditional operation. This must succeed.

        The test is parameterized to test variations on all parameters. Note
        that it only tests legal parameters.

        The test confirms that the Open operation receives the correct
        values for all parameters, and that the Close operation is not called.
        """
        conn = WBEMConnection('dummy', use_pull_operations=use_pull_param)

        conn.ReferenceNames = \
            Mock(side_effect=CIMError(CIM_ERR_NOT_SUPPORTED, 'Blah'))
        conn.OpenReferenceInstancePaths = \
            Mock(return_value=pull_path_result_tuple(paths=tst_paths,
                                                     eos=True,
                                                     context=None))
        conn.CloseEnumeration = Mock()

        assert conn.use_pull_operations == use_pull_param
        # pylint: disable=protected-access
        assert conn._use_ref_path_pull_operations == use_pull_param

        result = list(conn.IterReferenceInstancePaths(
            self.target_path(ns),
            ResultClass=rc,
            Role=ro,
            FilterQueryLanguage=fl,
            FilterQuery=fq,
            OperationTimeout=ot,
            ContinueOnError=coe,
            MaxObjectCount=moc))

        conn.OpenReferenceInstancePaths.assert_called_with(
            self.target_path(ns),
            ResultClass=rc,
            Role=ro,
            FilterQueryLanguage=fl,
            FilterQuery=fq,
            OperationTimeout=ot,
            ContinueOnError=coe,
            MaxObjectCount=moc)

        conn.CloseEnumeration.assert_not_called()

        # pylint: disable=protected-access
        assert conn._use_ref_path_pull_operations is True
        assert conn.use_pull_operations == use_pull_param
        assert result == tst_paths

    @pytest.mark.parametrize(
        "use_pull_param", [None, True]
    )
    def test_pull_operation_success(self, tst_paths, use_pull_param):
        # pylint: disable=no-self-use,redefined-outer-name
        """
        Test IterReferenceInstancePaths using the pull operations,
        either by requesting it via use_pull_operations=True, or by leaving it
        to the implementation via use_pull_operations=None and raising
        NOT_SUPPORTED in the traditional operation. This must succeed.

        The Open operation returns no result objects, and the Pull operation
        returns all result objects and EOS.

        This does not retest the variations of input parameters because it
        is only confirming that the Pull operation executes.
        """
        conn = WBEMConnection('dummy', use_pull_operations=use_pull_param)

        ctx = ('blah', conn.default_namespace)

        conn.ReferenceNames = \
            Mock(side_effect=CIMError(CIM_ERR_NOT_SUPPORTED, 'Blah'))
        conn.OpenReferenceInstancePaths = \
            Mock(return_value=pull_path_result_tuple(paths=[], eos=False,
                                                     context=ctx))
        conn.PullInstancePaths = \
            Mock(return_value=pull_path_result_tuple(paths=tst_paths,
                                                     eos=True,
                                                     context=None))

        assert conn.use_pull_operations == use_pull_param
        # pylint: disable=protected-access
        assert conn._use_ref_path_pull_operations == use_pull_param

        result = list(conn.IterReferenceInstancePaths(
            self.target_path('root/cimv2')))

        assert conn._use_ref_path_pull_operations is True
        assert conn.use_pull_operations == use_pull_param
        assert result == tst_paths

    @pytest.mark.parametrize(
        "use_pull_param", [None, True]
    )
    @pytest.mark.parametrize(
        "max_obj_count", [1, 2]
    )
    @pytest.mark.parametrize(
        "close_after", [0, 1, 2]
    )
    def test_closed_operation_success(self, tst_paths, use_pull_param,
                                      max_obj_count, close_after):
        # pylint: disable=no-self-use,redefined-outer-name
        """
        Test IterReferenceInstancePaths using the pull operations,
        either by requesting it via use_pull_operations=True, or by leaving it
        to the implementation via use_pull_operations=None and raising
        NOT_SUPPORTED in the traditional operation.

        The iteration is closed after a number of retrievals, sometimes
        prematurely and sometimes not.

        This does not retest the variations of input parameters because it
        is only confirming that the Close operation executes if needed.
        """
        conn = WBEMConnection('dummy', use_pull_operations=use_pull_param)

        tst_paths_open = tst_paths[0:max_obj_count]
        tst_paths_pull = tst_paths[max_obj_count:]
        ctx = ('blah', conn.default_namespace)

        conn.ReferenceNames = \
            Mock(side_effect=CIMError(CIM_ERR_NOT_SUPPORTED, 'Blah'))
        conn.OpenReferenceInstancePaths = \
            Mock(return_value=pull_path_result_tuple(paths=tst_paths_open,
                                                     eos=False,
                                                     context=ctx))
        conn.PullInstancePaths = \
            Mock(return_value=pull_path_result_tuple(paths=tst_paths_pull,
                                                     eos=True,
                                                     context=None))
        conn.CloseEnumeration = Mock()

        assert conn.use_pull_operations == use_pull_param
        # pylint: disable=protected-access
        assert conn._use_ref_path_pull_operations == use_pull_param

        gen = conn.IterReferenceInstancePaths(
            self.target_path('root/cimv2'), MaxObjectCount=max_obj_count)
        result = []
        for _ in six.moves.range(close_after):
            obj = next(gen)
            result.append(obj)
        gen.close()  # close prematurely

        if close_after == 0 or close_after > max_obj_count:
            # Pull has been called; enumeration is exhausted; enumeration was
            # closed automatically within Pull.
            conn.CloseEnumeration.assert_not_called()
        else:
            # Pull has not been called; enumeration is not exhausted;
            # enumeration was closed by calling Close.
            conn.CloseEnumeration.assert_called_with(ctx)
            assert conn._use_ref_path_pull_operations is True

        assert conn.use_pull_operations == use_pull_param
        assert result == tst_paths[0:close_after]

    @pytest.mark.parametrize(
        "kwargs, exp_exc",
        [
            [dict(OperationTimeout='bla'), TypeError()],
            [dict(OperationTimeout=-1), ValueError()],
            [dict(MaxObjectCount=0), ValueError()],
            [dict(MaxObjectCount=-1), ValueError()],
            [dict(MaxObjectCount=None), ValueError()],
            [dict(MaxObjectCount='bla'), TypeError()],
            [dict(MaxObjectCount='bla'), TypeError()],
        ]
    )
    def test_open_invalid_params(self, tst_insts, kwargs, exp_exc):
        # pylint: disable=no-self-use,redefined-outer-name
        """
        Test IterReferenceInstancePaths using the pull operations,
        with invalid values and types of those input parameters that are
        actually checked (i.e. OperationTimeout and MaxObjectCount).
        """
        conn = WBEMConnection('dummy', use_pull_operations=True)

        conn.ReferenceNames = Mock(return_value=tst_insts)
        conn.OpenReferenceInstancePaths = \
            Mock(side_effect=CIMError(CIM_ERR_NOT_SUPPORTED, 'Blah'))

        with pytest.raises(type(exp_exc)):
            _ = list(conn.IterReferenceInstancePaths(
                self.target_path('dum'),
                **kwargs))

    @pytest.mark.parametrize(
        "kwargs, exp_exc",
        [
            [dict(FilterQueryLanguage='CQL'), ValueError()],
            [dict(FilterQuery='Prop=42'), ValueError()],
            [dict(ContinueOnError=True), ValueError()],
        ]
    )
    def test_trad_invalid_params(self, tst_insts, kwargs, exp_exc):
        # pylint: disable=no-self-use,redefined-outer-name
        """
        Test IterReferenceInstancePaths using the traditional operations,
        with invalid values and types of those input parameters that are
        actually checked (i.e. FilterQueryLanguage, FilterQuery,
        ContinueOnError).
        """
        conn = WBEMConnection('dummy', use_pull_operations=False)

        conn.ReferenceNames = Mock(return_value=tst_insts)
        conn.OpenReferenceInstancePaths = \
            Mock(side_effect=CIMError(CIM_ERR_NOT_SUPPORTED, 'Blah'))

        with pytest.raises(type(exp_exc)):
            _ = list(conn.IterReferenceInstancePaths(
                self.target_path('dum'),
                **kwargs))


########################################################################
#
#               IterAssociatorInstances tests
#
########################################################################

class TestIterAssociatorInstances(object):
    """Test IterAssociatorInstances execution"""

    @staticmethod
    def target_path(ns):
        """
        Return a valid target path for the calls
        """
        return CIMInstanceName('CIM_blah',
                               keybindings={'InstanceID': "1234"},
                               host='woot.com',
                               namespace=ns)

    @pytest.mark.parametrize(
        "use_pull_param", [None, False]
    )
    @pytest.mark.parametrize(
        "pull_status", [CIM_ERR_NOT_SUPPORTED, CIM_ERR_FAILED]
    )
    @pytest.mark.parametrize(
        "ns", [None, 'test/testnamespace']
    )
    @pytest.mark.parametrize(
        "iq, ico", [[None, None],
                    [False, False],
                    [True, True]]
    )
    # role, result_class, ResultRole, AssocClass
    @pytest.mark.parametrize(
        "ro, rc, rr, ac", [[None, None, None, None],
                           [None, 'CIM_Blah', None, 'AssocClass'],
                           ['RRole', None, 'ARole', None],
                           ['RRole', 'CIM_Blah', 'ARole', 'AssocClass']]
    )
    @pytest.mark.parametrize(
        "pl", [None, 'pl1', ['pl1', 'pl2']]
    )
    def test_trad_operation_success(
            self, use_pull_param, pull_status, tst_insts, ns,
            rc, ro, ac, rr, iq, ico, pl):
        # pylint: disable=no-self-use,redefined-outer-name
        """
        Test IterAssociatorInstances using the traditional operations,
        either by requesting it via use_pull_operations=False, or by leaving it
        to the implementation via use_pull_operations=None and raising
        NOT_SUPPORTED in the Open operation. This must succeed.

        The test is parameterized to test variations on all parameters. Note
        that it only tests legal parameters.

        The test confirms that the traditional operation receives the correct
        values for all parameters.
        """
        conn = WBEMConnection('dummy', use_pull_operations=use_pull_param)

        # mock original function works, open returns CIMError
        conn.Associators = Mock(return_value=tst_insts)
        conn.OpenAssociatorInstances = \
            Mock(side_effect=CIMError(pull_status))

        assert conn.use_pull_operations == use_pull_param
        # pylint: disable=protected-access
        assert conn._use_assoc_inst_pull_operations == use_pull_param

        result = list(conn.IterAssociatorInstances(
            self.target_path(ns),
            AssocClass=ac,
            ResultClass=rc,
            Role=ro,
            ResultRole=rr,
            IncludeQualifiers=iq,
            IncludeClassOrigin=ico,
            PropertyList=pl))

        conn.Associators.assert_called_with(
            self.target_path(ns),
            AssocClass=ac,
            ResultClass=rc,
            Role=ro,
            ResultRole=rr,
            IncludeQualifiers=iq,
            IncludeClassOrigin=ico,
            PropertyList=pl)

        assert conn._use_assoc_inst_pull_operations is False
        assert conn.use_pull_operations == use_pull_param
        assert result == tst_insts

    @pytest.mark.parametrize(
        "pull_status", [CIM_ERR_NOT_SUPPORTED, CIM_ERR_FAILED]
    )
    def test_operation_fail(self, pull_status, tst_insts):
        # pylint: disable=no-self-use,redefined-outer-name
        """
        Test IterAssociatorInstances forcing the use of pull operations
        via use_pull_operations=True, and the Open operation raises
        NOT_SUPPORTED. This must fail.
        """
        conn = WBEMConnection('dummy', use_pull_operations=True)

        conn.Associators = Mock(return_value=tst_insts)
        conn.OpenAssociatorInstances = \
            Mock(side_effect=CIMError(pull_status))

        assert conn.use_pull_operations is True
        # pylint: disable=protected-access
        assert conn._use_assoc_inst_pull_operations is True

        with pytest.raises(CIMError) as exec_info:
            _ = list(conn.IterAssociatorInstances(
                self.target_path('root/cimv2')))

        exc = exec_info.value
        assert exc.status_code == pull_status

        # pylint: disable=protected-access
        assert conn._use_assoc_inst_pull_operations is True
        assert conn.use_pull_operations is True

    @pytest.mark.parametrize(
        "use_pull_param", [None, True]
    )
    @pytest.mark.parametrize(
        "ns", [None, 'test/testnamespace']
    )
    @pytest.mark.parametrize(
        "iq, ico", [[None, None],
                    [False, False],
                    [True, True]]
    )
    # role, result_class, ResultRole, AssocClass
    @pytest.mark.parametrize(
        "ro, rc, rr, ac", [[None, None, None, None],
                           [None, 'CIM_Blah', None, 'AssocClass'],
                           ['RRole', None, 'ARole', None],
                           ['RRole', 'CIM_Blah', 'ARole', 'AssocClass']]
    )
    @pytest.mark.parametrize(
        "pl", [None, 'pl1', ['pl1', 'pl2']]
    )
    @pytest.mark.parametrize(
        "fl,fq", [(None, None), ('FQL', 'SELECT')]
    )
    @pytest.mark.parametrize(
        "ot, coe, moc", [[None, None, 100],
                         [10, False, 100]]
    )
    def test_open_operation_success(self, use_pull_param, tst_insts, ns,
                                    rc, ro, rr, ac, iq, ico, pl, fl, fq, ot,
                                    coe, moc):
        # pylint: disable=no-self-use,redefined-outer-name
        """
        Test IterAssociatorInstances using the pull operations,
        either by requesting it via use_pull_operations=True, or by leaving it
        to the implementation via use_pull_operations=None and raising
        NOT_SUPPORTED in the traditional operation. This must succeed.

        The test is parameterized to test variations on all parameters. Note
        that it only tests legal parameters.

        The test confirms that the Open operation receives the correct
        values for all parameters, and that the Close operation is not called.
        """
        conn = WBEMConnection('dummy', use_pull_operations=use_pull_param)

        conn.Associators = \
            Mock(side_effect=CIMError(CIM_ERR_NOT_SUPPORTED, 'Blah'))
        conn.OpenAssociatorInstances = \
            Mock(return_value=pull_inst_result_tuple(instances=tst_insts,
                                                     eos=True,
                                                     context=None))
        conn.CloseEnumeration = Mock()

        assert conn.use_pull_operations == use_pull_param
        # pylint: disable=protected-access
        assert conn._use_assoc_inst_pull_operations == use_pull_param

        result = list(conn.IterAssociatorInstances(
            self.target_path(ns),
            AssocClass=ac,
            ResultClass=rc,
            Role=ro,
            ResultRole=rr,
            IncludeQualifiers=iq,
            IncludeClassOrigin=ico,
            PropertyList=pl,
            FilterQueryLanguage=fl,
            FilterQuery=fq,
            OperationTimeout=ot,
            ContinueOnError=coe,
            MaxObjectCount=moc))

        conn.OpenAssociatorInstances.assert_called_with(
            self.target_path(ns),
            AssocClass=ac,
            ResultClass=rc,
            Role=ro,
            ResultRole=rr,
            IncludeClassOrigin=ico,
            PropertyList=pl,
            FilterQueryLanguage=fl,
            FilterQuery=fq,
            OperationTimeout=ot,
            ContinueOnError=coe,
            MaxObjectCount=moc)

        conn.CloseEnumeration.assert_not_called()

        # pylint: disable=protected-access
        assert conn._use_assoc_inst_pull_operations is True
        assert conn.use_pull_operations == use_pull_param
        assert result == tst_insts

    @pytest.mark.parametrize(
        "use_pull_param", [None, True]
    )
    def test_pull_operation_success(self, tst_insts, use_pull_param):
        # pylint: disable=no-self-use,redefined-outer-name
        """
        Test IterAssociatorInstances using the pull operations,
        either by requesting it via use_pull_operations=True, or by leaving it
        to the implementation via use_pull_operations=None and raising
        NOT_SUPPORTED in the traditional operation. This must succeed.

        The Open operation returns no result objects, and the Pull operation
        returns all result objects and EOS.

        This does not retest the variations of input parameters because it
        is only confirming that the Pull operation executes.
        """
        conn = WBEMConnection('dummy', use_pull_operations=use_pull_param)

        ctx = ('blah', conn.default_namespace)

        conn.Associators = \
            Mock(side_effect=CIMError(CIM_ERR_NOT_SUPPORTED, 'Blah'))
        conn.OpenAssociatorInstances = \
            Mock(return_value=pull_inst_result_tuple(instances=[], eos=False,
                                                     context=ctx))
        conn.PullInstancesWithPath = \
            Mock(return_value=pull_inst_result_tuple(instances=tst_insts,
                                                     eos=True,
                                                     context=None))

        assert conn.use_pull_operations == use_pull_param
        # pylint: disable=protected-access
        assert conn._use_assoc_inst_pull_operations == use_pull_param

        result = list(conn.IterAssociatorInstances(
            self.target_path('root/cimv2')))

        assert conn._use_assoc_inst_pull_operations is True
        assert conn.use_pull_operations == use_pull_param
        assert result == tst_insts

    @pytest.mark.parametrize(
        "use_pull_param", [None, True]
    )
    @pytest.mark.parametrize(
        "max_obj_count", [1, 2]
    )
    @pytest.mark.parametrize(
        "close_after", [0, 1, 2]
    )
    def test_closed_operation_success(self, tst_insts, use_pull_param,
                                      max_obj_count, close_after):
        # pylint: disable=no-self-use,redefined-outer-name
        """
        Test IterAssociatorInstances using the pull operations,
        either by requesting it via use_pull_operations=True, or by leaving it
        to the implementation via use_pull_operations=None and raising
        NOT_SUPPORTED in the traditional operation.

        The iteration is closed after a number of retrievals, sometimes
        prematurely and sometimes not.

        This does not retest the variations of input parameters because it
        is only confirming that the Close operation executes if needed.
        """
        conn = WBEMConnection('dummy', use_pull_operations=use_pull_param)

        tst_insts_open = tst_insts[0:max_obj_count]
        tst_insts_pull = tst_insts[max_obj_count:]
        ctx = ('blah', conn.default_namespace)

        conn.Associators = \
            Mock(side_effect=CIMError(CIM_ERR_NOT_SUPPORTED, 'Blah'))
        conn.OpenAssociatorInstances = \
            Mock(return_value=pull_inst_result_tuple(instances=tst_insts_open,
                                                     eos=False,
                                                     context=ctx))
        conn.PullInstancesWithPath = \
            Mock(return_value=pull_inst_result_tuple(instances=tst_insts_pull,
                                                     eos=True,
                                                     context=None))
        conn.CloseEnumeration = Mock()

        assert conn.use_pull_operations == use_pull_param
        # pylint: disable=protected-access
        assert conn._use_assoc_inst_pull_operations == use_pull_param

        gen = conn.IterAssociatorInstances(
            self.target_path('root/cimv2'), MaxObjectCount=max_obj_count)
        result = []
        for _ in six.moves.range(close_after):
            obj = next(gen)
            result.append(obj)
        gen.close()  # close prematurely

        if close_after == 0 or close_after > max_obj_count:
            # Pull has been called; enumeration is exhausted; enumeration was
            # closed automatically within Pull.
            conn.CloseEnumeration.assert_not_called()
        else:
            # Pull has not been called; enumeration is not exhausted;
            # enumeration was closed by calling Close.
            conn.CloseEnumeration.assert_called_with(ctx)
            assert conn._use_assoc_inst_pull_operations is True

        assert conn.use_pull_operations == use_pull_param
        assert result == tst_insts[0:close_after]

    @pytest.mark.parametrize(
        "kwargs, exp_exc",
        [
            [dict(OperationTimeout='bla'), TypeError()],
            [dict(OperationTimeout=-1), ValueError()],
            [dict(MaxObjectCount=0), ValueError()],
            [dict(MaxObjectCount=-1), ValueError()],
            [dict(MaxObjectCount=None), ValueError()],
            [dict(MaxObjectCount='bla'), TypeError()],
            [dict(MaxObjectCount='bla'), TypeError()],
        ]
    )
    def test_open_invalid_params(self, tst_insts, kwargs, exp_exc):
        # pylint: disable=no-self-use,redefined-outer-name
        """
        Test IterAssociatorInstances using the pull operations,
        with invalid values and types of those input parameters that are
        actually checked (i.e. OperationTimeout and MaxObjectCount).
        """
        conn = WBEMConnection('dummy', use_pull_operations=True)

        conn.Associators = Mock(return_value=tst_insts)
        conn.OpenAssociatorInstances = \
            Mock(side_effect=CIMError(CIM_ERR_NOT_SUPPORTED, 'Blah'))

        with pytest.raises(type(exp_exc)):
            _ = list(conn.IterAssociatorInstances(
                self.target_path('root/x'),
                **kwargs))

    @pytest.mark.parametrize(
        "kwargs, exp_exc",
        [
            [dict(FilterQueryLanguage='CQL'), ValueError()],
            [dict(FilterQuery='Prop=42'), ValueError()],
            [dict(ContinueOnError=True), ValueError()],
        ]
    )
    def test_trad_invalid_params(self, tst_insts, kwargs, exp_exc):
        # pylint: disable=no-self-use,redefined-outer-name
        """
        Test IterAssociatorInstances using the traditional operations,
        with invalid values and types of those input parameters that are
        actually checked (i.e. FilterQueryLanguage, FilterQuery,
        ContinueOnError).
        """
        conn = WBEMConnection('dummy', use_pull_operations=False)

        conn.Associators = Mock(return_value=tst_insts)
        conn.OpenAssociatorInstances = \
            Mock(side_effect=CIMError(CIM_ERR_NOT_SUPPORTED, 'Blah'))

        with pytest.raises(type(exp_exc)):
            _ = list(conn.IterAssociatorInstances(
                self.target_path('root/x'),
                **kwargs))


########################################################################
#
#               IterAssociatorInstancePaths tests
#
########################################################################

class TestIterAssociatorInstancePaths(object):
    """Test IterAssociatorInstancePaths execution"""

    @staticmethod
    def target_path(ns):
        """
            Return a valid target path for the calls
        """
        return CIMInstanceName('CIM_blah',
                               keybindings={'InstanceID': "1234"},
                               host='woot.com',
                               namespace=ns)

    @pytest.mark.parametrize(
        "use_pull_param", [None, False]
    )
    @pytest.mark.parametrize(
        "pull_status", [CIM_ERR_NOT_SUPPORTED, CIM_ERR_FAILED]
    )
    @pytest.mark.parametrize(
        "ns", [None, 'test/testnamespace']
    )
    # role, result_class, ResultRole, AssocClass
    @pytest.mark.parametrize(
        "ro, rc, rr, ac", [[None, None, None, None],
                           [None, 'CIM_Blah', None, 'AssocClass'],
                           ['RRole', None, 'ARole', None],
                           ['RRole', 'CIM_Blah', 'ARole', 'AssocClass']]
    )
    def test_trad_operation_success(
            self, use_pull_param, pull_status, tst_paths, ns, rc, ro, rr, ac):
        # pylint: disable=no-self-use,redefined-outer-name
        """
        Test IterAssociatorInstancePaths using the traditional operations,
        either by requesting it via use_pull_operations=False, or by leaving it
        to the implementation via use_pull_operations=None and raising
        NOT_SUPPORTED in the Open operation. This must succeed.

        The test is parameterized to test variations on all parameters. Note
        that it only tests legal parameters.

        The test confirms that the traditional operation receives the correct
        values for all parameters.
        """
        conn = WBEMConnection('dummy', use_pull_operations=use_pull_param)

        # mock original function works, open returns CIMError
        conn.AssociatorNames = Mock(return_value=tst_paths)
        conn.OpenAssociatorInstancePaths = \
            Mock(side_effect=CIMError(pull_status))

        assert conn.use_pull_operations == use_pull_param
        # pylint: disable=protected-access
        assert conn._use_assoc_path_pull_operations == use_pull_param

        result = list(conn.IterAssociatorInstancePaths(
            self.target_path(ns),
            AssocClass=ac,
            ResultClass=rc,
            Role=ro,
            ResultRole=rr))

        conn.AssociatorNames.assert_called_with(
            self.target_path(ns),
            AssocClass=ac,
            ResultClass=rc,
            Role=ro,
            ResultRole=rr)

        assert conn._use_assoc_path_pull_operations is False
        assert conn.use_pull_operations == use_pull_param
        assert result == tst_paths

    @pytest.mark.parametrize(
        "pull_status", [CIM_ERR_NOT_SUPPORTED, CIM_ERR_FAILED]
    )
    def test_operation_fail(self, pull_status, tst_paths):
        # pylint: disable=no-self-use,redefined-outer-name
        """
        Test IterAssociatorInstancePaths forcing the use of pull operations
        via use_pull_operations=True, and the Open operation raises
        NOT_SUPPORTED. This must fail.
        """
        conn = WBEMConnection('dummy', use_pull_operations=True)

        conn.AssociatorNames = Mock(return_value=tst_paths)
        conn.OpenAssociatorInstancePaths = \
            Mock(side_effect=CIMError(pull_status))

        assert conn.use_pull_operations is True
        # pylint: disable=protected-access
        assert conn._use_assoc_path_pull_operations is True

        with pytest.raises(CIMError) as exec_info:
            _ = list(conn.IterAssociatorInstancePaths(
                self.target_path('root/cimv2')))

        exc = exec_info.value
        assert exc.status_code == pull_status

        # pylint: disable=protected-access
        assert conn._use_assoc_path_pull_operations is True
        assert conn.use_pull_operations is True

    @pytest.mark.parametrize(
        "use_pull_param", [None, True]
    )
    @pytest.mark.parametrize(
        "ns", [None, 'test/testnamespace']
    )
    # role, result_class, ResultRole, AssocClass
    @pytest.mark.parametrize(
        "ro, rc, rr, ac", [[None, None, None, None],
                           [None, 'CIM_Blah', None, 'AssocClass'],
                           ['RRole', None, 'ARole', None],
                           ['RRole', 'CIM_Blah', 'ARole', 'AssocClass']]
    )
    @pytest.mark.parametrize(
        "fl,fq", [(None, None), ('FQL', 'SELECT')]
    )
    @pytest.mark.parametrize(
        "ot, coe, moc", [[None, None, 100],
                         [10, False, 100]]
    )
    def test_open_operation_success(self, use_pull_param, tst_paths, ns,
                                    rc, ro, rr, ac, fl, fq, ot, coe, moc):
        # pylint: disable=no-self-use,redefined-outer-name
        """
        Test IterAssociatorInstancePaths using the pull operations,
        either by requesting it via use_pull_operations=True, or by leaving it
        to the implementation via use_pull_operations=None and raising
        NOT_SUPPORTED in the traditional operation. This must succeed.

        The test is parameterized to test variations on all parameters. Note
        that it only tests legal parameters.

        The test confirms that the Open operation receives the correct
        values for all parameters, and that the Close operation is not called.
        """
        conn = WBEMConnection('dummy', use_pull_operations=use_pull_param)

        conn.AssociatorNames = \
            Mock(side_effect=CIMError(CIM_ERR_NOT_SUPPORTED, 'Blah'))
        conn.OpenAssociatorInstancePaths = \
            Mock(return_value=pull_path_result_tuple(paths=tst_paths,
                                                     eos=True,
                                                     context=None))
        conn.CloseEnumeration = Mock()

        assert conn.use_pull_operations == use_pull_param
        # pylint: disable=protected-access
        assert conn._use_assoc_path_pull_operations == use_pull_param

        result = list(conn.IterAssociatorInstancePaths(
            self.target_path(ns),
            AssocClass=ac,
            ResultClass=rc,
            Role=ro,
            ResultRole=rr,
            FilterQueryLanguage=fl,
            FilterQuery=fq,
            OperationTimeout=ot,
            ContinueOnError=coe,
            MaxObjectCount=moc))

        conn.OpenAssociatorInstancePaths.assert_called_with(
            self.target_path(ns),
            AssocClass=ac,
            ResultClass=rc,
            Role=ro,
            ResultRole=rr,
            FilterQueryLanguage=fl,
            FilterQuery=fq,
            OperationTimeout=ot,
            ContinueOnError=coe,
            MaxObjectCount=moc)

        conn.CloseEnumeration.assert_not_called()

        # pylint: disable=protected-access
        assert conn._use_assoc_path_pull_operations is True
        assert conn.use_pull_operations == use_pull_param
        assert result == tst_paths

    @pytest.mark.parametrize(
        "use_pull_param", [None, True]
    )
    def test_pull_operation_success(self, tst_paths, use_pull_param):
        # pylint: disable=no-self-use,redefined-outer-name
        """
        Test IterAssociatorInstancePaths using the pull operations,
        either by requesting it via use_pull_operations=True, or by leaving it
        to the implementation via use_pull_operations=None and raising
        NOT_SUPPORTED in the traditional operation. This must succeed.

        The Open operation returns no result objects, and the Pull operation
        returns all result objects and EOS.

        This does not retest the variations of input parameters because it
        is only confirming that the Pull operation executes.
        """
        conn = WBEMConnection('dummy', use_pull_operations=use_pull_param)

        ctx = ('blah', conn.default_namespace)

        conn.AssociatorNames = \
            Mock(side_effect=CIMError(CIM_ERR_NOT_SUPPORTED, 'Blah'))
        conn.OpenAssociatorInstancePaths = \
            Mock(return_value=pull_path_result_tuple(paths=[], eos=False,
                                                     context=ctx))
        conn.PullInstancePaths = \
            Mock(return_value=pull_path_result_tuple(paths=tst_paths,
                                                     eos=True,
                                                     context=None))

        assert conn.use_pull_operations == use_pull_param
        # pylint: disable=protected-access
        assert conn._use_assoc_path_pull_operations == use_pull_param

        result = list(conn.IterAssociatorInstancePaths(
            self.target_path('root/cimv2')))

        assert conn._use_assoc_path_pull_operations is True
        assert conn.use_pull_operations == use_pull_param
        assert result == tst_paths

    @pytest.mark.parametrize(
        "use_pull_param", [None, True]
    )
    @pytest.mark.parametrize(
        "max_obj_count", [1, 2]
    )
    @pytest.mark.parametrize(
        "close_after", [0, 1, 2]
    )
    def test_closed_operation_success(self, tst_paths, use_pull_param,
                                      max_obj_count, close_after):
        # pylint: disable=no-self-use,redefined-outer-name
        """
        Test IterAssociatorInstancePaths using the pull operations,
        either by requesting it via use_pull_operations=True, or by leaving it
        to the implementation via use_pull_operations=None and raising
        NOT_SUPPORTED in the traditional operation.

        The iteration is closed after a number of retrievals, sometimes
        prematurely and sometimes not.

        This does not retest the variations of input parameters because it
        is only confirming that the Close operation executes if needed.
        """
        conn = WBEMConnection('dummy', use_pull_operations=use_pull_param)

        tst_paths_open = tst_paths[0:max_obj_count]
        tst_paths_pull = tst_paths[max_obj_count:]
        ctx = ('blah', conn.default_namespace)

        conn.AssociatorNames = \
            Mock(side_effect=CIMError(CIM_ERR_NOT_SUPPORTED, 'Blah'))
        conn.OpenAssociatorInstancePaths = \
            Mock(return_value=pull_path_result_tuple(paths=tst_paths_open,
                                                     eos=False,
                                                     context=ctx))
        conn.PullInstancePaths = \
            Mock(return_value=pull_path_result_tuple(paths=tst_paths_pull,
                                                     eos=True,
                                                     context=None))
        conn.CloseEnumeration = Mock()

        assert conn.use_pull_operations == use_pull_param
        # pylint: disable=protected-access
        assert conn._use_assoc_path_pull_operations == use_pull_param

        gen = conn.IterAssociatorInstancePaths(
            self.target_path('root/cimv2'), MaxObjectCount=max_obj_count)
        result = []
        for _ in six.moves.range(close_after):
            obj = next(gen)
            result.append(obj)
        gen.close()  # close prematurely

        if close_after == 0 or close_after > max_obj_count:
            # Pull has been called; enumeration is exhausted; enumeration was
            # closed automatically within Pull.
            conn.CloseEnumeration.assert_not_called()
        else:
            # Pull has not been called; enumeration is not exhausted;
            # enumeration was closed by calling Close.
            conn.CloseEnumeration.assert_called_with(ctx)
            assert conn._use_assoc_path_pull_operations is True

        assert conn.use_pull_operations == use_pull_param
        assert result == tst_paths[0:close_after]

    @pytest.mark.parametrize(
        "kwargs, exp_exc",
        [
            [dict(OperationTimeout='bla'), TypeError()],
            [dict(OperationTimeout=-1), ValueError()],
            [dict(MaxObjectCount=0), ValueError()],
            [dict(MaxObjectCount=-1), ValueError()],
            [dict(MaxObjectCount=None), ValueError()],
            [dict(MaxObjectCount='bla'), TypeError()],
            [dict(MaxObjectCount='bla'), TypeError()],
        ]
    )
    def test_open_invalid_params(self, tst_paths, kwargs, exp_exc):
        # pylint: disable=no-self-use,redefined-outer-name
        """
        Test IterAssociatorInstancePaths using the pull operations,
        with invalid values and types of those input parameters that are
        actually checked (i.e. OperationTimeout and MaxObjectCount).
        """
        conn = WBEMConnection('dummy', use_pull_operations=True)

        conn.AssociatorNames = Mock(return_value=tst_paths)
        conn.OpenAssociatorInstancePaths = \
            Mock(side_effect=CIMError(CIM_ERR_NOT_SUPPORTED, 'Blah'))

        with pytest.raises(type(exp_exc)):
            _ = list(conn.IterAssociatorInstancePaths(
                self.target_path('dum'),
                **kwargs))

    @pytest.mark.parametrize(
        "kwargs, exp_exc",
        [
            [dict(FilterQueryLanguage='CQL'), ValueError()],
            [dict(FilterQuery='Prop=42'), ValueError()],
            [dict(ContinueOnError=True), ValueError()],
        ]
    )
    def test_trad_invalid_params(self, tst_paths, kwargs, exp_exc):
        # pylint: disable=no-self-use,redefined-outer-name
        """
        Test IterAssociatorInstancePaths using the traditional operations,
        with invalid values and types of those input parameters that are
        actually checked (i.e. FilterQueryLanguage, FilterQuery,
        ContinueOnError).
        """
        conn = WBEMConnection('dummy', use_pull_operations=False)

        conn.AssociatorNames = Mock(return_value=tst_paths)
        conn.OpenAssociatorInstancePaths = \
            Mock(side_effect=CIMError(CIM_ERR_NOT_SUPPORTED, 'Blah'))

        with pytest.raises(type(exp_exc)):
            _ = list(conn.IterAssociatorInstancePaths(
                self.target_path('dum'),
                **kwargs))


########################################################################
#
#               IterQueryInstances tests
#
########################################################################

class TestIterQueryInstances(object):
    """Test IterQueryInstances execution"""

    @pytest.mark.parametrize(
        "use_pull_param", [None, False]
    )
    @pytest.mark.parametrize(
        "pull_status", [CIM_ERR_NOT_SUPPORTED, CIM_ERR_FAILED]
    )
    @pytest.mark.parametrize(
        "ns", [None, 'test/testnamespace']
    )
    @pytest.mark.parametrize(
        "ql, query", [(None, None), ('CQL', 'SELECT from *')]
    )
    def test_trad_operation_success(
            self, use_pull_param, pull_status, tst_insts, ns, ql, query):
        # pylint: disable=no-self-use,redefined-outer-name
        """
        Test IterQueryInstances using the traditional operations,
        either by requesting it via use_pull_operations=False, or by leaving it
        to the implementation via use_pull_operations=None and raising
        NOT_SUPPORTED in the Open operation. This must succeed.

        The test is parameterized to test variations on all parameters. Note
        that it only tests legal parameters.

        The test confirms that the traditional operation receives the correct
        values for all parameters.
        """
        conn = WBEMConnection('dummy', use_pull_operations=use_pull_param)

        # mock original function works, open returns CIMError
        conn.ExecQuery = Mock(return_value=tst_insts)
        conn.OpenQueryInstances = \
            Mock(side_effect=CIMError(pull_status))

        assert conn.use_pull_operations == use_pull_param
        # pylint: disable=protected-access
        assert conn._use_query_pull_operations == use_pull_param

        q_result = conn.IterQueryInstances(ql, query, namespace=ns)
        result_insts = list(q_result.generator)

        conn.ExecQuery.assert_called_with(ql, query, namespace=ns)

        assert q_result.query_result_class is None
        assert conn._use_query_pull_operations is False
        assert conn.use_pull_operations == use_pull_param
        assert result_insts == tst_insts

    @pytest.mark.parametrize(
        "pull_status", [CIM_ERR_NOT_SUPPORTED, CIM_ERR_FAILED]
    )
    def test_operation_fail(self, pull_status, tst_insts):
        # pylint: disable=no-self-use,redefined-outer-name
        """
        Test IterQueryInstances forcing the use of pull operations
        via use_pull_operations=True, and the Open operation raises
        NOT_SUPPORTED. This must fail.
        """
        conn = WBEMConnection('dummy', use_pull_operations=True)

        conn.ExecQuery = Mock(return_value=tst_insts)
        conn.OpenQueryInstances = \
            Mock(side_effect=CIMError(pull_status))

        assert conn.use_pull_operations is True
        # pylint: disable=protected-access
        assert conn._use_query_pull_operations is True

        with pytest.raises(CIMError) as exec_info:
            conn.IterQueryInstances('CQL', 'Select from *')

        exc = exec_info.value
        assert exc.status_code == pull_status

        # pylint: disable=protected-access
        assert conn._use_query_pull_operations is True
        assert conn.use_pull_operations is True

    @pytest.mark.parametrize(
        "use_pull_param", [None, True]
    )
    @pytest.mark.parametrize(
        "ns", [None, 'test/testnamespace']
    )
    @pytest.mark.parametrize(
        "ql, query", [(None, None), ('CQL', 'SELECT from *')]
    )
    @pytest.mark.parametrize(
        "ot, coe, moc", [[None, None, 100],
                         [10, False, 100]]
    )
    # ReturnQueryResultClass (Boolean flag))
    @pytest.mark.parametrize(
        "rqrc_param", [None, True]
    )
    def test_open_operation_success(self, use_pull_param, tst_insts, ns,
                                    ql, query, ot, coe, moc, rqrc_param,
                                    tst_class):
        # pylint: disable=no-self-use,redefined-outer-name
        """
        Test IterQueryInstances using the pull operations,
        either by requesting it via use_pull_operations=True, or by leaving it
        to the implementation via use_pull_operations=None and raising
        NOT_SUPPORTED in the traditional operation. This must succeed.

        The test is parameterized to test variations on all parameters. Note
        that it only tests legal parameters.

        The test confirms that the Open operation receives the correct
        values for all parameters, and that the Close operation is not called.
        """
        conn = WBEMConnection('dummy', use_pull_operations=use_pull_param)

        # Get class definition for response if ReturnQueryResultClass
        qrc = tst_class if rqrc_param is True else None

        conn.ExecQuery = \
            Mock(side_effect=CIMError(CIM_ERR_NOT_SUPPORTED, 'Blah'))
        conn.OpenQueryInstances = \
            Mock(return_value=pull_query_result_tuple(instances=tst_insts,
                                                      eos=True,
                                                      context=None,
                                                      query_result_class=qrc))
        conn.CloseEnumeration = Mock()

        assert conn.use_pull_operations == use_pull_param
        # pylint: disable=protected-access
        assert conn._use_query_pull_operations == use_pull_param

        q_result = conn.IterQueryInstances(
            ql, query,
            namespace=ns,
            ReturnQueryResultClass=rqrc_param,
            OperationTimeout=ot,
            ContinueOnError=coe,
            MaxObjectCount=moc)

        conn.OpenQueryInstances.assert_called_with(
            ql, query,
            namespace=ns,
            ReturnQueryResultClass=rqrc_param,
            OperationTimeout=ot,
            ContinueOnError=coe,
            MaxObjectCount=moc)

        conn.CloseEnumeration.assert_not_called()

        result_insts = list(q_result.generator)

        assert q_result.query_result_class == qrc

        # pylint: disable=protected-access
        assert conn._use_query_pull_operations is True
        assert conn.use_pull_operations == use_pull_param
        assert result_insts == tst_insts

    @pytest.mark.parametrize(
        "use_pull_param", [None, True]
    )
    # ReturnQueryResultClass
    @pytest.mark.parametrize(
        "rqrc_param", [None, True]
    )
    def test_pull_operation_success(self, tst_insts, use_pull_param,
                                    rqrc_param):
        # pylint: disable=no-self-use,redefined-outer-name
        """
        Test IterQueryInstances using the pull operations,
        either by requesting it via use_pull_operations=True, or by leaving it
        to the implementation via use_pull_operations=None and raising
        NOT_SUPPORTED in the traditional operation. This must succeed.

        The Open operation returns no result objects, and the Pull operation
        returns all result objects and EOS.

        This does not retest the variations of input parameters because it
        is only confirming that the Pull operation executes.

        The test confirms that the Open operation receives the correct
        values for all parameters, and that the Close operation is not called.
        """
        conn = WBEMConnection('dummy', use_pull_operations=use_pull_param)

        # Get class definition for response if ReturnQueryResultClass
        qrc = tst_class if rqrc_param is True else None

        conn.ExecQuery = \
            Mock(side_effect=CIMError(CIM_ERR_NOT_SUPPORTED, 'Blah'))
        conn.OpenQueryInstances = \
            Mock(return_value=pull_query_result_tuple(
                instances=[],
                eos=False,
                context="BlahBlah",
                query_result_class=qrc))
        conn.PullInstances = \
            Mock(return_value=pull_query_result_tuple(instances=tst_insts,
                                                      eos=True,
                                                      context=None,
                                                      query_result_class=qrc))
        conn.CloseEnumeration = Mock()

        assert conn.use_pull_operations == use_pull_param
        # pylint: disable=protected-access
        assert conn._use_assoc_path_pull_operations == use_pull_param

        q_result = conn.IterQueryInstances(
            'CQL', 'Select from *',
            ReturnQueryResultClass=rqrc_param)

        result_insts = list(q_result.generator)

        conn.OpenQueryInstances.assert_called_with(
            'CQL', 'Select from *',
            namespace=None,
            ReturnQueryResultClass=rqrc_param,
            OperationTimeout=None,
            ContinueOnError=None,
            MaxObjectCount=DEFAULT_ITER_MAXOBJECTCOUNT)

        conn.CloseEnumeration.assert_not_called()

        # TODO ks: This assert disabled.
        # assert(q_result.query_result_class == rc)

        # pylint: disable=protected-access
        assert conn._use_query_pull_operations is True
        assert conn.use_pull_operations == use_pull_param
        assert result_insts == tst_insts

    @pytest.mark.parametrize(
        "use_pull_param", [None, True]
    )
    @pytest.mark.parametrize(
        "max_obj_count", [1, 2]
    )
    @pytest.mark.parametrize(
        "close_after", [0, 1, 2]
    )
    def test_closed_operation_success(self, tst_insts, use_pull_param,
                                      max_obj_count, close_after):
        # pylint: disable=no-self-use,redefined-outer-name
        """
        Test IterQueryInstances using the pull operations,
        either by requesting it via use_pull_operations=True, or by leaving it
        to the implementation via use_pull_operations=None and raising
        NOT_SUPPORTED in the traditional operation.

        The iteration is closed after a number of retrievals, sometimes
        prematurely and sometimes not.

        This does not retest the variations of input parameters because it
        is only confirming that the Close operation executes if needed.
        """
        conn = WBEMConnection('dummy', use_pull_operations=use_pull_param)

        tst_insts_open = tst_insts[0:max_obj_count]
        tst_insts_pull = tst_insts[max_obj_count:]
        ctx = ('blah', conn.default_namespace)

        conn.ExecQuery = \
            Mock(side_effect=CIMError(CIM_ERR_NOT_SUPPORTED, 'Blah'))
        conn.OpenQueryInstances = \
            Mock(return_value=pull_query_result_tuple(instances=tst_insts_open,
                                                      eos=False,
                                                      context=ctx,
                                                      query_result_class=None))
        conn.PullInstances = \
            Mock(return_value=pull_query_result_tuple(instances=tst_insts_pull,
                                                      eos=True,
                                                      context=None,
                                                      query_result_class=None))
        conn.CloseEnumeration = Mock()

        assert conn.use_pull_operations == use_pull_param
        # pylint: disable=protected-access
        assert conn._use_query_pull_operations == use_pull_param

        q_result = conn.IterQueryInstances(
            'CQL', 'Select from *',
            ReturnQueryResultClass=None, MaxObjectCount=max_obj_count)
        gen = q_result.generator
        result = []
        for _ in six.moves.range(close_after):
            obj = next(gen)
            result.append(obj)
        gen.close()  # close prematurely

        # In the current implementation of IterQuery, the enumeration is
        # always exhausted.
        conn.CloseEnumeration.assert_not_called()

        assert conn.use_pull_operations == use_pull_param
        assert result == tst_insts[0:close_after]

    @pytest.mark.parametrize(
        "kwargs, exp_exc",
        [
            [dict(OperationTimeout='bla'), TypeError()],
            [dict(OperationTimeout=-1), ValueError()],
            [dict(MaxObjectCount=0), ValueError()],
            [dict(MaxObjectCount=-1), ValueError()],
            [dict(MaxObjectCount=None), ValueError()],
            [dict(MaxObjectCount='bla'), TypeError()],
            [dict(MaxObjectCount='bla'), TypeError()],
        ]
    )
    def test_open_invalid_params(self, tst_insts, kwargs, exp_exc):
        # pylint: disable=no-self-use,redefined-outer-name
        """
        Test IterQueryInstances using the pull operations,
        with invalid values and types of those input parameters that are
        actually checked (i.e. OperationTimeout and MaxObjectCount).
        """
        conn = WBEMConnection('dummy', use_pull_operations=True)

        conn.ExecQuery = \
            Mock(side_effect=CIMError(CIM_ERR_NOT_SUPPORTED, 'Blah'))
        conn.OpenQueryInstances = \
            Mock(return_value=pull_query_result_tuple(instances=tst_insts,
                                                      eos=True,
                                                      context=None,
                                                      query_result_class=None))
        with pytest.raises(type(exp_exc)):
            conn.IterQueryInstances(
                'CQL', 'Select from *',
                **kwargs)

    @pytest.mark.parametrize(
        "kwargs, exp_exc",
        [
            [dict(ContinueOnError=True), ValueError()],
            [dict(ReturnQueryResultClass=True), ValueError()],
        ]
    )
    def test_trad_invalid_params(self, tst_insts, kwargs, exp_exc):
        # pylint: disable=no-self-use,redefined-outer-name
        """
        Test IterQueryInstances using the traditional operations,
        with invalid values and types of those input parameters that are
        actually checked (i.e. ContinueOnError).
        """
        conn = WBEMConnection('dummy', use_pull_operations=False)

        conn.ExecQuery = \
            Mock(side_effect=CIMError(CIM_ERR_NOT_SUPPORTED, 'Blah'))
        conn.OpenQueryInstances = \
            Mock(return_value=pull_query_result_tuple(instances=tst_insts,
                                                      eos=True,
                                                      context=None,
                                                      query_result_class=None))
        with pytest.raises(type(exp_exc)):
            conn.IterQueryInstances(
                'CQL', 'Select from *',
                **kwargs)
