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

from mock import Mock

# pylint: disable=wrong-import-position, wrong-import-order, invalid-name
from ...utils import import_installed
pywbem = import_installed('pywbem')
from pywbem import WBEMConnection, CIMInstance, CIMClass, CIMInstanceName, \
    CIMProperty, CIMError, CIM_ERR_NOT_SUPPORTED  # noqa: E402
from pywbem.config import DEFAULT_ITER_MAXOBJECTCOUNT  # noqa: E402
from pywbem._cim_operations import pull_inst_result_tuple, \
    pull_path_result_tuple, pull_query_result_tuple  # noqa: E402
# pylint: enable=wrong-import-position, wrong-import-order, invalid-name


# TODO: ks Oct 17 Remove this pylint disable in the future when pylint or
# the pylint plugin for pylint is fixed
# Today it reports error "redefining name ..."
# pylint: disable=redefined-outer-name


@pytest.fixture
def tst_insts():
    """
    Pytest fixture to return an instance
    """
    i = CIMInstance('CIM_Foo',
                    properties={'Name': 'Foo', 'Chicken': 'Ham'},
                    path=CIMInstanceName('CIM_Foo', {'Name': 'Foo'}))
    return[i]


@pytest.fixture
def tst_class():
    """
    Pytest fixture to return an instance
    """
    cl = CIMClass('CIM_Foo', properties={'InstanceID':
                                         CIMProperty('InstanceID', None,
                                                     type='string')})
    return cl


@pytest.fixture
def tst_paths():
    """ Pytest fixture to return an instance name. This creates a list
        of CIMInstanceName objects and returns the list.
    """
    inst_count = 1
    rtn = []
    for i in six.moves.range(inst_count):
        i = CIMInstanceName('CIM_Foo',
                            keybindings={'InstanceID': str(i + 1000)},
                            host='woot.com',
                            namespace='root/cimv2')
        rtn.append(i)
    return rtn

########################################################################
#
#               IterEnumerateInstances tests
#
########################################################################


class TestIterEnumerateInstances(object):
    """Test IterEnumerateInstance Execution"""
    @pytest.mark.parametrize(
        "use_pull_param", [None, False]
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
    def test_orig_operation_success(self, use_pull_param, tst_insts, ns,
                                    di, iq, lo, ico, pl,):
        # pylint: disable=no-self-use
        """
            Test Use of IterEnumerateInstances from IterEnumerateInstances.
            This forces the enumerate by mocking NOT_Supported on the
            OpenEnumerateInstancess.
            It is parameterized to test variations on all parameters. Note
            that it only tests legal parameters.

            It confirms that EnumerateInstances receives the correct parameter
            for all parameters.
        """
        conn = WBEMConnection('dummy', use_pull_operations=use_pull_param)

        # mock original function works, open returns CIMError
        conn.EnumerateInstances = Mock(return_value=tst_insts)
        conn.OpenEnumerateInstances = \
            Mock(side_effect=CIMError(CIM_ERR_NOT_SUPPORTED, 'Blah'))

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
            PropertyList=pl))

        conn.EnumerateInstances.assert_called_with(
            'CIM_Foo',
            namespace=ns,
            LocalOnly=lo,
            DeepInheritance=di,
            IncludeQualifiers=iq,
            IncludeClassOrigin=ico,
            PropertyList=pl)

        assert conn._use_enum_inst_pull_operations is False
        assert conn.use_pull_operations == use_pull_param
        assert result == tst_insts

    def test_operation_fail(self, tst_insts):
        # pylint: disable=no-self-use
        """
            Test operation with use_pull_operation=True and
            pull operation returns exception.
            This must fail since we force use of the pull operations but
            they return error.
        """
        conn = WBEMConnection('dummy', use_pull_operations=True)

        conn.EnumerateInstances = Mock(return_value=tst_insts)
        conn.OpenEnumerateInstances = \
            Mock(side_effect=CIMError(CIM_ERR_NOT_SUPPORTED, 'description'))

        assert conn.use_pull_operations is True
        # pylint: disable=protected-access
        assert conn._use_enum_inst_pull_operations is True

        with pytest.raises(CIMError) as exec_info:
            _ = list(conn.IterEnumerateInstances('CIM_Foo'))

        exc = exec_info.value
        assert exc.status_code_name == 'CIM_ERR_NOT_SUPPORTED'

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
        # pylint: disable=no-self-use
        """
            Test call with forced pull operation and pull operation
            returns exception. This tests with variations of all of the
            input parameters from None to other valid values.  It does not
            do any invalid values.
        """
        conn = WBEMConnection('dummy', use_pull_operations=use_pull_param)

        conn.EnumerateInstances = \
            Mock(side_effect=CIMError(CIM_ERR_NOT_SUPPORTED, 'Blah'))
        conn.OpenEnumerateInstances = \
            Mock(return_value=pull_inst_result_tuple(instances=tst_insts,
                                                     eos=True,
                                                     context=None))

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

        # pylint: disable=protected-access
        assert conn._use_enum_inst_pull_operations is True
        assert conn.use_pull_operations == use_pull_param
        assert result == tst_insts

    @pytest.mark.parametrize(
        "use_pull_param", [None, True]
    )
    def test_pull_operation_success(self, tst_insts, use_pull_param):
        # pylint: disable=no-self-use
        """
            Test call with forced pull operation Open returns nothing and
            pull returns the instance and eos
        """
        conn = WBEMConnection('dummy', use_pull_operations=use_pull_param)

        conn.EnumerateInstances = \
            Mock(side_effect=CIMError(CIM_ERR_NOT_SUPPORTED, 'Blah'))
        conn.OpenEnumerateInstances = \
            Mock(return_value=pull_inst_result_tuple(instances=[], eos=False,
                                                     context='blah'))
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
        "op_to, max_cnt, exp_exc",
        [
            ['bla', 1, TypeError()],
            [-1, 1, ValueError()],
            [None, 0, ValueError()],
            [None, -1, ValueError()],
            [None, None, ValueError()],
            [None, 'bla', TypeError()],
        ]
    )
    def test_invalid_params(self, tst_insts, op_to, max_cnt, exp_exc):
        # pylint: disable=no-self-use
        """
        Test for invalid value and types of those input parameters that are
        actually checked in the Iter..() operation (i.e. OperationTimeout
        and MaxObjectCount).
        """
        conn = WBEMConnection('dummy', use_pull_operations=True)

        conn.EnumerateInstances = Mock(return_value=tst_insts)
        conn.OpenEnumerateInstances = \
            Mock(side_effect=CIMError(CIM_ERR_NOT_SUPPORTED, 'Blah'))

        with pytest.raises(type(exp_exc)):
            _ = list(conn.IterEnumerateInstances(
                'CIM_Foo',
                OperationTimeout=op_to,
                MaxObjectCount=max_cnt))


########################################################################
#
#               IterEnumerateInstancePaths tests
#
########################################################################


class TestIterEnumerateInstancePaths(object):
    """Test IterEnumerateInstanceNames execution"""
    @pytest.mark.parametrize(
        "use_pull_param", [None, False]
    )
    @pytest.mark.parametrize(
        "ns", [None, 'test/testnamespace']
    )
    def test_orig_operation_success(self, use_pull_param, tst_paths, ns):
        # pylint: disable=no-self-use
        """
            Test call with no forcing
        """
        conn = WBEMConnection('dummy', use_pull_operations=use_pull_param)

        conn.EnumerateInstanceNames = Mock(return_value=tst_paths)
        conn.OpenEnumerateInstancePaths = \
            Mock(side_effect=CIMError(CIM_ERR_NOT_SUPPORTED, 'Blah'))

        assert conn.use_pull_operations == use_pull_param
        # pylint: disable=protected-access
        assert conn._use_enum_path_pull_operations == use_pull_param

        result = list(conn.IterEnumerateInstancePaths(
            'CIM_Foo',
            namespace=ns))

        conn.EnumerateInstanceNames.assert_called_with(
            'CIM_Foo',
            namespace=ns)

        # pylint: disable=protected-access
        assert conn._use_enum_path_pull_operations is False
        assert conn.use_pull_operations == use_pull_param
        assert result == tst_paths

    def test_operation_fail(self, tst_insts):
        # pylint: disable=no-self-use
        """
            Test IterEnumerateInstances with forced pull operation and
            pull operation returns exception
        """
        conn = WBEMConnection('dummy', use_pull_operations=True)

        conn.EnumerateInstanceNames = Mock(return_value=tst_insts)
        conn.OpenEnumerateInstancePaths = \
            Mock(side_effect=CIMError(CIM_ERR_NOT_SUPPORTED, 'description'))

        assert conn.use_pull_operations is True
        # pylint: disable=protected-access
        assert conn._use_enum_path_pull_operations is True

        with pytest.raises(CIMError) as exec_info:
            _ = list(conn.IterEnumerateInstancePaths('CIM_Foo'))

        exc = exec_info.value
        assert exc.status_code_name == 'CIM_ERR_NOT_SUPPORTED'

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
        # pylint: disable=no-self-use
        """
            Test call with forced pull operation and pull operation
            returns exception. This runs parametrized tests with all of the
            input parameters for legal values.  It does not test for illegal
            values.
            It all tests the mocs OpenEnumerateInstances for correct
            parameters.
        """
        conn = WBEMConnection('dummy', use_pull_operations=use_pull_param)

        conn.EnumerateInstanceNames = \
            Mock(side_effect=CIMError(CIM_ERR_NOT_SUPPORTED, 'Blah'))
        conn.OpenEnumerateInstancePaths = \
            Mock(return_value=pull_path_result_tuple(paths=tst_paths,
                                                     eos=True,
                                                     context=None))

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

        # pylint: disable=protected-access
        assert conn._use_enum_path_pull_operations is True
        assert conn.use_pull_operations == use_pull_param
        assert result == tst_paths

    @pytest.mark.parametrize(
        "use_pull_param", [None, True]
    )
    def test_pull_operation_success(self, tst_paths, use_pull_param):
        # pylint: disable=no-self-use
        """
            Test call with forced pull operation Open returns nothing and
            pull returns the instance and eos
        """
        conn = WBEMConnection('dummy', use_pull_operations=use_pull_param)

        conn.EnumerateInstanceNames = \
            Mock(side_effect=CIMError(CIM_ERR_NOT_SUPPORTED, 'Blah'))
        conn.OpenEnumerateInstancePaths = \
            Mock(return_value=pull_path_result_tuple(paths=[], eos=False,
                                                     context='blah'))
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
        "op_to, max_cnt, exp_exc",
        [
            ['bla', 1, TypeError()],
            [-1, 1, ValueError()],
            [None, 0, ValueError()],
            [None, -1, ValueError()],
            [None, None, ValueError()],
            [None, 'bla', TypeError()],
        ]
    )
    def test_invalid_params(self, tst_paths, op_to, max_cnt, exp_exc):
        # pylint: disable=no-self-use
        """
        Test for invalid OperationTimeout, ContinueOnError, and MaxObjectCount
        input parameters.
        """
        conn = WBEMConnection('dummy', use_pull_operations=True)

        conn.EnumerateInstanceNames = Mock(return_value=tst_paths)
        conn.OpenEnumeratePaths = \
            Mock(side_effect=CIMError(CIM_ERR_NOT_SUPPORTED, 'Blah'))

        with pytest.raises(type(exp_exc)):
            _ = list(conn.IterEnumerateInstancePaths(
                'CIM_Foo',
                OperationTimeout=op_to,
                MaxObjectCount=max_cnt))


########################################################################
#
#               IterReferenceInstances tests
#
########################################################################


class TestIterReferenceInstances(object):
    """Test IterReferenceInstance Execution"""

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
    def test_orig_operation_success(self, use_pull_param, tst_insts, ns,
                                    rc, ro, iq, ico, pl,):
        # pylint: disable=no-self-use
        """
            Test Use of IterReferenceInstances from IterReferenceInstances.
            This forces the enumerate by mocking NOT_Supported on the
            OpenReferenceInstancess.
            It is parameterized to test variations on all parameters. Note
            that it only tests legal parameters.

            It confirms that ReferenceInstances receives the correct parameter
            for all parameters.
        """
        conn = WBEMConnection('dummy', use_pull_operations=use_pull_param)

        # mock original function works, open returns CIMError
        conn.References = Mock(return_value=tst_insts)
        conn.OpenReferenceInstances = \
            Mock(side_effect=CIMError(CIM_ERR_NOT_SUPPORTED, 'Blah'))

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

    def test_operation_fail(self, tst_insts):
        # pylint: disable=no-self-use
        """
            Test operation with use_pull_operation=True and
            pull operation returns exception.
            This must fail since we force use of the pull operations but
            they return error.
        """
        conn = WBEMConnection('dummy', use_pull_operations=True)

        conn.References = Mock(return_value=tst_insts)
        conn.OpenReferenceInstances = \
            Mock(side_effect=CIMError(CIM_ERR_NOT_SUPPORTED, 'description'))

        assert conn.use_pull_operations is True
        # pylint: disable=protected-access
        assert conn._use_ref_inst_pull_operations is True

        with pytest.raises(CIMError) as exec_info:
            _ = list(conn.IterReferenceInstances(
                self.target_path('root/cimv2')))

        exc = exec_info.value
        assert exc.status_code_name == 'CIM_ERR_NOT_SUPPORTED'

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
        # pylint: disable=no-self-use
        """
            Test call with forced pull operation and pull operation
            returns exception. This tests with variations of all of the
            input parameters from None to other valid values.  It does not
            do any invalid values.
        """
        conn = WBEMConnection('dummy', use_pull_operations=use_pull_param)

        conn.References = \
            Mock(side_effect=CIMError(CIM_ERR_NOT_SUPPORTED, 'Blah'))
        conn.OpenReferenceInstances = \
            Mock(return_value=pull_inst_result_tuple(instances=tst_insts,
                                                     eos=True,
                                                     context=None))

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

        # pylint: disable=protected-access
        assert conn._use_ref_inst_pull_operations is True
        assert conn.use_pull_operations == use_pull_param
        assert result == tst_insts

    @pytest.mark.parametrize(
        "use_pull_param", [None, True]
    )
    def test_pull_operation_success(self, tst_insts, use_pull_param):
        # pylint: disable=no-self-use
        """
            Test call with forced pull operation Open returns nothing and
            pull returns the instance and eos. This does not retest the
            variations of input parameters because it is only confirming
            that the pull executes.
        """
        conn = WBEMConnection('dummy', use_pull_operations=use_pull_param)

        conn.References = \
            Mock(side_effect=CIMError(CIM_ERR_NOT_SUPPORTED, 'Blah'))
        conn.OpenReferenceInstances = \
            Mock(return_value=pull_inst_result_tuple(instances=[], eos=False,
                                                     context='blah'))
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
        "op_to, max_cnt, exp_exc",
        [
            ['bla', 1, TypeError()],
            [-1, 1, ValueError()],
            [None, 0, ValueError()],
            [None, -1, ValueError()],
            [None, None, ValueError()],
            [None, 'bla', TypeError()],
        ]
    )
    def test_invalid_params(self, tst_insts, op_to, max_cnt, exp_exc):
        # pylint: disable=no-self-use
        """
        Test for invalid OperationTimeout, ContinueOnError, and MaxObjectCount
        input parameters.
        """
        conn = WBEMConnection('dummy', use_pull_operations=True)

        conn.References = Mock(return_value=tst_insts)
        conn.OpenReferenceInstances = \
            Mock(side_effect=CIMError(CIM_ERR_NOT_SUPPORTED, 'Blah'))

        with pytest.raises(type(exp_exc)):
            _ = list(conn.IterReferenceInstances(
                self.target_path('root/x'),
                OperationTimeout=op_to,
                MaxObjectCount=max_cnt))


########################################################################
#
#               IterReferenceInstancePaths tests
#
########################################################################

class TestIterReferenceInstancePaths(object):
    """Test IterReferenceInstancePaths Execution"""

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
        "ns", [None, 'test/testnamespace']
    )
    # result_role, result_class
    @pytest.mark.parametrize(
        "ro, rc", [[None, None],
                   [None, 'CIM_Blah'],
                   ['RRole', None],
                   ['RRole', 'CIM_Blah']]
    )
    def test_orig_operation_success(self, use_pull_param, tst_insts, ns, rc,
                                    ro):
        # pylint: disable=no-self-use
        """
            Test Use of IterReferenceInstancePaths from
            IterReferenceInstancePaths.
            This forces the enumerate by mocking NOT_Supported on the
            OpenReferenceInstances.
            It is parameterized to test variations on all parameters. Note
            that it only tests legal parameters.

            It confirms that ReferenceInstances receives the correct parameter
            for all parameters.
        """
        conn = WBEMConnection('dummy', use_pull_operations=use_pull_param)

        # mock original function works, open returns CIMError
        conn.ReferenceNames = Mock(return_value=tst_insts)
        conn.OpenReferenceInstancePaths = \
            Mock(side_effect=CIMError(CIM_ERR_NOT_SUPPORTED, 'Blah'))

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

    def test_operation_fail(self, tst_insts):
        # pylint: disable=no-self-use
        """
            Test operation with use_pull_operation=True and
            pull operation returns exception.
            This must fail since we force use of the pull operations but
            they return error.
        """
        conn = WBEMConnection('dummy', use_pull_operations=True)

        conn.ReferenceNames = Mock(return_value=tst_insts)
        conn.OpenReferenceInstancePaths = \
            Mock(side_effect=CIMError(CIM_ERR_NOT_SUPPORTED, 'description'))

        assert conn.use_pull_operations is True
        # pylint: disable=protected-access
        assert conn._use_ref_path_pull_operations is True

        with pytest.raises(CIMError) as exec_info:
            _ = list(conn.IterReferenceInstancePaths(
                self.target_path('root/cimv2')))

        exc = exec_info.value
        assert exc.status_code_name == 'CIM_ERR_NOT_SUPPORTED'

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
        # pylint: disable=no-self-use
        """
            Test call with forced pull operation and pull operation
            returns exception. This tests with variations of all of the
            input parameters from None to other valid values.  It does not
            do any invalid values.
        """
        conn = WBEMConnection('dummy', use_pull_operations=use_pull_param)

        conn.ReferenceNames = \
            Mock(side_effect=CIMError(CIM_ERR_NOT_SUPPORTED, 'Blah'))
        conn.OpenReferenceInstancePaths = \
            Mock(return_value=pull_path_result_tuple(paths=tst_paths,
                                                     eos=True,
                                                     context=None))

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

        # pylint: disable=protected-access
        assert conn._use_ref_path_pull_operations is True
        assert conn.use_pull_operations == use_pull_param
        assert result == tst_paths

    @pytest.mark.parametrize(
        "use_pull_param", [None, True]
    )
    def test_pull_operation_success(self, tst_paths, use_pull_param):
        # pylint: disable=no-self-use
        """
            Test call with forced pull operation Open returns nothing and
            pull returns the instance and eos. This does not retest the
            variations of input parameters because it is only confirming
            that the pull executes.
        """
        conn = WBEMConnection('dummy', use_pull_operations=use_pull_param)

        conn.ReferenceNames = \
            Mock(side_effect=CIMError(CIM_ERR_NOT_SUPPORTED, 'Blah'))
        conn.OpenReferenceInstancePaths = \
            Mock(return_value=pull_path_result_tuple(paths=[], eos=False,
                                                     context='blah'))
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
        "op_to, max_cnt, exp_exc",
        [
            ['bla', 1, TypeError()],
            [-1, 1, ValueError()],
            [None, 0, ValueError()],
            [None, -1, ValueError()],
            [None, None, ValueError()],
            [None, 'bla', TypeError()],
        ]
    )
    def test_invalid_params(self, tst_insts, op_to, max_cnt, exp_exc):
        # pylint: disable=no-self-use
        """
        Test for invalid OperationTimeout, ContinueOnError, and MaxObjectCount
        input parameters.
        """
        conn = WBEMConnection('dummy', use_pull_operations=True)

        conn.ReferenceNames = Mock(return_value=tst_insts)
        conn.OpenReferenceInstancePaths = \
            Mock(side_effect=CIMError(CIM_ERR_NOT_SUPPORTED, 'Blah'))

        with pytest.raises(type(exp_exc)):
            _ = list(conn.IterReferenceInstancePaths(
                self.target_path('dum'),
                OperationTimeout=op_to,
                MaxObjectCount=max_cnt))

########################################################################
#
#               IterAssociatorInstances tests
#
########################################################################


class TestIterAssociatorInstances(object):
    """Test IterReferenceInstance Execution"""

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
    def test_orig_operation_success(self, use_pull_param, tst_insts, ns,
                                    rc, ro, ac, rr, iq, ico, pl,):
        # pylint: disable=no-self-use
        """
            Test Use of IterAssociatorInstances from IterAssociatorInstances.
            This forces the enumerate by mocking NOT_Supported on the
            OpenAssociatorInstancess.
            It is parameterized to test variations on all parameters. Note
            that it only tests legal parameters.

            It confirms that AssociatorInstances receives the correct parameter
            for all parameters.
        """
        conn = WBEMConnection('dummy', use_pull_operations=use_pull_param)

        # mock original function works, open returns CIMError
        conn.Associators = Mock(return_value=tst_insts)
        conn.OpenAssociatorInstances = \
            Mock(side_effect=CIMError(CIM_ERR_NOT_SUPPORTED, 'Blah'))

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

    def test_operation_fail(self, tst_insts):
        # pylint: disable=no-self-use
        """
            Test operation with use_pull_operation=True and
            pull operation returns exception.
            This must fail since we force use of the pull operations but
            they return error.
        """
        conn = WBEMConnection('dummy', use_pull_operations=True)

        conn.Associators = Mock(return_value=tst_insts)
        conn.OpenAssociatorInstances = \
            Mock(side_effect=CIMError(CIM_ERR_NOT_SUPPORTED, 'description'))

        assert conn.use_pull_operations is True
        # pylint: disable=protected-access
        assert conn._use_assoc_inst_pull_operations is True

        with pytest.raises(CIMError) as exec_info:
            _ = list(conn.IterAssociatorInstances(
                self.target_path('root/cimv2')))

        exc = exec_info.value
        assert exc.status_code_name == 'CIM_ERR_NOT_SUPPORTED'

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
        # pylint: disable=no-self-use
        """
            Test call with forced pull operation and pull operation
            returns exception. This tests with variations of all of the
            input parameters from None to other valid values.  It does not
            do any invalid values.
        """
        conn = WBEMConnection('dummy', use_pull_operations=use_pull_param)

        conn.Associators = \
            Mock(side_effect=CIMError(CIM_ERR_NOT_SUPPORTED, 'Blah'))
        conn.OpenAssociatorInstances = \
            Mock(return_value=pull_inst_result_tuple(instances=tst_insts,
                                                     eos=True,
                                                     context=None))

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

        # pylint: disable=protected-access
        assert conn._use_assoc_inst_pull_operations is True
        assert conn.use_pull_operations == use_pull_param
        assert result == tst_insts

    @pytest.mark.parametrize(
        "use_pull_param", [None, True]
    )
    def test_pull_operation_success(self, tst_insts, use_pull_param):
        # pylint: disable=no-self-use
        """
            Test call with forced pull operation Open returns nothing and
            pull returns the instance and eos. This does not retest the
            variations of input parameters because it is only confirming
            that the pull executes.
        """
        conn = WBEMConnection('dummy', use_pull_operations=use_pull_param)

        conn.Associators = \
            Mock(side_effect=CIMError(CIM_ERR_NOT_SUPPORTED, 'Blah'))
        conn.OpenAssociatorInstances = \
            Mock(return_value=pull_inst_result_tuple(instances=[], eos=False,
                                                     context='blah'))
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
        "op_to, max_cnt, exp_exc",
        [
            ['bla', 1, TypeError()],
            [-1, 1, ValueError()],
            [None, 0, ValueError()],
            [None, -1, ValueError()],
            [None, None, ValueError()],
            [None, 'bla', TypeError()],
        ]
    )
    def test_invalid_params(self, tst_insts, op_to, max_cnt, exp_exc):
        # pylint: disable=no-self-use
        """
        Test for invalid OperationTimeout, ContinueOnError, and MaxObjectCount
        input parameters.
        """
        conn = WBEMConnection('dummy', use_pull_operations=True)

        conn.Associators = Mock(return_value=tst_insts)
        conn.OpenAssociatorInstances = \
            Mock(side_effect=CIMError(CIM_ERR_NOT_SUPPORTED, 'Blah'))

        with pytest.raises(type(exp_exc)):
            _ = list(conn.IterAssociatorInstances(
                self.target_path('root/x'),
                OperationTimeout=op_to,
                MaxObjectCount=max_cnt))

########################################################################
#
#               IterAssociatorInstancePaths tests
#
########################################################################


class TestIterAssociatorInstancePaths(object):  # pylint: disable=invalid-name
    """Test IterAssociatorInstancePaths Execution."""

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
        "ns", [None, 'test/testnamespace']
    )
    # role, result_class, ResultRole, AssocClass
    @pytest.mark.parametrize(
        "ro, rc, rr, ac", [[None, None, None, None],
                           [None, 'CIM_Blah', None, 'AssocClass'],
                           ['RRole', None, 'ARole', None],
                           ['RRole', 'CIM_Blah', 'ARole', 'AssocClass']]
    )
    def test_orig_operation_success(self, use_pull_param, tst_paths, ns, rc,
                                    ro, rr, ac):
        # pylint: disable=no-self-use
        """
            Test Use of IterAssociatorInstancePaths from
            IterAssociatorInstancePaths.
            This forces the enumerate by mocking NOT_Supported on the
            OpenReferenceInstances.
            It is parameterized to test variations on all parameters. Note
            that it only tests legal parameters.

            It confirms that ReferenceInstances receives the correct parameter
            for all parameters.
        """
        conn = WBEMConnection('dummy', use_pull_operations=use_pull_param)

        # mock original function works, open returns CIMError
        conn.AssociatorNames = Mock(return_value=tst_paths)
        conn.OpenAssociatorInstancePaths = \
            Mock(side_effect=CIMError(CIM_ERR_NOT_SUPPORTED, 'Blah'))

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

    def test_operation_fail(self, tst_paths):
        # pylint: disable=no-self-use
        """
            Test operation with use_pull_operation=True and
            pull operation returns exception.
            This must fail since we force use of the pull operations but
            they return error.
        """
        conn = WBEMConnection('dummy', use_pull_operations=True)

        conn.AssociatorNames = Mock(return_value=tst_paths)
        conn.OpenAssociatorInstancePaths = \
            Mock(side_effect=CIMError(CIM_ERR_NOT_SUPPORTED, 'description'))

        assert conn.use_pull_operations is True
        # pylint: disable=protected-access
        assert conn._use_assoc_path_pull_operations is True

        with pytest.raises(CIMError) as exec_info:
            _ = list(conn.IterAssociatorInstancePaths(
                self.target_path('root/cimv2')))

        exc = exec_info.value
        assert exc.status_code_name == 'CIM_ERR_NOT_SUPPORTED'

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
        # pylint: disable=no-self-use
        """
            Test call with forced pull operation and pull operation
            returns exception. This tests with variations of all of the
            input parameters from None to other valid values.  It does not
            do any invalid values.
        """
        conn = WBEMConnection('dummy', use_pull_operations=use_pull_param)

        conn.AssociatorNames = \
            Mock(side_effect=CIMError(CIM_ERR_NOT_SUPPORTED, 'Blah'))
        conn.OpenAssociatorInstancePaths = \
            Mock(return_value=pull_path_result_tuple(paths=tst_paths,
                                                     eos=True,
                                                     context=None))

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

        # pylint: disable=protected-access
        assert conn._use_assoc_path_pull_operations is True
        assert conn.use_pull_operations == use_pull_param
        assert result == tst_paths

    @pytest.mark.parametrize(
        "use_pull_param", [None, True]
    )
    def test_pull_operation_success(self, tst_paths, use_pull_param):
        # pylint: disable=no-self-use
        """
            Test call with forced pull operation Open returns nothing and
            pull returns the instance and eos. This does not retest the
            variations of input parameters because it is only confirming
            that the pull executes.
        """
        conn = WBEMConnection('dummy', use_pull_operations=use_pull_param)

        conn.AssociatorNames = \
            Mock(side_effect=CIMError(CIM_ERR_NOT_SUPPORTED, 'Blah'))
        conn.OpenAssociatorInstancePaths = \
            Mock(return_value=pull_path_result_tuple(paths=[], eos=False,
                                                     context='blah'))
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
        "op_to, max_cnt, exp_exc",
        [
            ['bla', 1, TypeError()],
            [-1, 1, ValueError()],
            [None, 0, ValueError()],
            [None, -1, ValueError()],
            [None, None, ValueError()],
            [None, 'bla', TypeError()],
        ]
    )
    def test_invalid_params(self, tst_paths, op_to, max_cnt, exp_exc):
        # pylint: disable=no-self-use
        """
        Test for invalid OperationTimeout, ContinueOnError, and MaxObjectCount
        input parameters.
        """
        conn = WBEMConnection('dummy', use_pull_operations=True)

        conn.AssociatorNames = Mock(return_value=tst_paths)
        conn.OpenAssociatorInstancePaths = \
            Mock(side_effect=CIMError(CIM_ERR_NOT_SUPPORTED, 'Blah'))

        with pytest.raises(type(exp_exc)):
            _ = list(conn.IterAssociatorInstancePaths(
                self.target_path('dum'),
                OperationTimeout=op_to,
                MaxObjectCount=max_cnt))


########################################################################
#
#               IterQueryInstances tests
#
########################################################################


class TestIterQueryInstances(object):  # pylint: disable=invalid-name
    """Test IterAssociatorInstancePaths Execution."""

    @pytest.mark.parametrize(
        "use_pull_param", [None, False]
    )
    @pytest.mark.parametrize(
        "ns", [None, 'test/testnamespace']
    )
    @pytest.mark.parametrize(
        "ql, query", [(None, None), ('CQL', 'SELECT from *')]
    )
    def test_orig_operation_success(self, use_pull_param, tst_insts, ns,
                                    ql, query):
        # pylint: disable=no-self-use
        """
            Test Use IterQueryInstances using the original ExecQuery op
        """
        conn = WBEMConnection('dummy', use_pull_operations=use_pull_param)

        # mock original function works, open returns CIMError
        conn.ExecQuery = Mock(return_value=tst_insts)
        conn.OpenQueryInstances = \
            Mock(side_effect=CIMError(CIM_ERR_NOT_SUPPORTED, 'Blah'))

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

    def test_operation_fail(self, tst_insts):
        # pylint: disable=no-self-use
        """
            Test operation with use_pull_operation=True and
            pull operation returns exception.
            This must fail since we force use of the pull operations but
            they return error.
        """
        conn = WBEMConnection('dummy', use_pull_operations=True)

        conn.ExecQuery = Mock(return_value=tst_insts)
        conn.OpenQueryInstances = \
            Mock(side_effect=CIMError(CIM_ERR_NOT_SUPPORTED, 'description'))

        assert conn.use_pull_operations is True
        # pylint: disable=protected-access
        assert conn._use_query_pull_operations is True

        with pytest.raises(CIMError) as exec_info:
            conn.IterQueryInstances('CQL', 'Select from *')

        exc = exec_info.value
        assert exc.status_code_name == 'CIM_ERR_NOT_SUPPORTED'

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
        # pylint: disable=no-self-use
        """
            Test call with forced pull operation and pull operation
            returns exception. This tests with variations of all of the
            input parameters from None to other valid values.  It does not
            do any invalid values.
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
        # pylint: disable=no-self-use
        """
            Test call with forced pull operation Open returns nothing and
            pull returns the instance and eos. This does not retest the
            variations of input parameters because it is only confirming
            that the pull executes.
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

        # TODO ks: This assert disabled.
        # assert(q_result.query_result_class == rc)

        # pylint: disable=protected-access
        assert conn._use_query_pull_operations is True
        assert conn.use_pull_operations == use_pull_param
        assert result_insts == tst_insts

    @pytest.mark.parametrize(
        "op_to, max_cnt, exp_exc",
        [
            ['bla', 1, TypeError()],
            [-1, 1, ValueError()],
            [None, 0, ValueError()],
            [None, -1, ValueError()],
            [None, None, ValueError()],
            [None, 'bla', TypeError()],
        ]
    )
    def test_invalid_params(self, tst_insts, op_to, max_cnt, exp_exc):
        # pylint: disable=no-self-use
        """
        Test for invalid OperationTimeout, ContinueOnError, and MaxObjectCount
        input parameters.
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
                OperationTimeout=op_to,
                MaxObjectCount=max_cnt)
