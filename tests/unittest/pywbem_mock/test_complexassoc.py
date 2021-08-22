# -*- coding: utf-8 -*-
#
# (C) Copyright 2018 InovaDevelopment.com
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
#
# Author: Karl  Schopmeyer <inovadevelopment.com>
#

"""
Pywbem mock tests for a complex association.  These tests are separate because
they were added later than original tests. They provide a test of the logic
of processing complex associations including ternary associations (more than
2 reference properties and subclasses of the association and result classes)
"""
from __future__ import absolute_import, print_function

import os
import io

import pytest

from ...utils import skip_if_moftab_regenerated

# pylint: disable=wrong-import-position, wrong-import-order, invalid-name
from ...utils import import_installed
pywbem = import_installed('pywbem')
from pywbem import CIMInstanceName, CIMClassName, \
    DEFAULT_NAMESPACE  # noqa: E402
pywbem_mock = import_installed('pywbem_mock')
# pylint: enable=wrong-import-position, wrong-import-order, invalid-name

# List of initially existing namespaces in the CIM repository
INITIAL_NAMESPACES = [DEFAULT_NAMESPACE]


@pytest.fixture()
def complex_assoc_mof(tst_qualifiers_mof):
    """
    Defines a ternary association to enable testing of complex association
    model mocking. This model rougly simulates the
    CIM_InitiatorTargetLogicalUnitPath with reference properties for
    Initiator, Target, and LogicalDevice. However we kept the naming
    very simple and very limited properties in the classes to simplify the
    tests.
    """
    complex_associations_mof = """
//
//  MOF models defines a ternary association with subclasses to test
//  the capability to process a ternary association and also toe
//  process subclasses.
//  This is based on the CIM InitiatorTargetLogicalPath classes in
//  CIM with references for Initiator, Target, and LogicalDevice
//  The names have been simplified to make creating tests easier.

// This model requires the following associators which must be installed
// separately
// Association, Description, Key, Override
// The qualifiers were separated so that the MOF can be loaded into
// a running server for comparison

    [Description("Top level class i.e ManagedElement")]
class TST_ME {
        [key]
    Uint32 InstanceID;
};

    [Description("ManagedElement")]
class TST_EP:TST_ME {
    string EP_Prop;
};

    [Description("EndPoint")]
class TST_EPSub:TST_EP {
    string EP_SubProp;
};

    [Description("LogicalDevice")]
class TST_LD:TST_ME  {
    string LD_Prop;
};

    [Description("LogicalDevice Subclass")]
class TST_LDSub:TST_LD  {
    string LD_SubProp;
};

   [Association ( true ), Description ("Ternary way association." )]
class TST_A3 {
        [Key ( true ), Description ( "Initiator Endpoint." )]
    TST_EP REF Initiator;

        [Key ( true ),
         Description ( "Target endpoint." )]
    TST_EP REF Target;

        [Key ( true ),
         Description ("Subclass of LogicalDevice representing a Logical Unit" )]
    TST_LD REF LogicalUnit;};

    [Association ( true ), Description ("Ternary way association subclass." )]
class TST_A3Sub:TST_A3 {
       [Key ( true ), Description ( "Initiator Endpointsub." ),
        Override ( "Initiator" )]
    TST_EPSub REF Initiator;

       [Key ( true ), Description ( "Target endpointsub." ),
        Override ( "Target" )]
    TST_EPSub REF Target;

       [Key ( true ), Description (
           "Subclass of LogicalDevice representing a Logical Unit" ),
        Override ( "LogicalUnit" )]
    TST_LDSub REF LogicalUnit;

        [Description ( "Extra property to confirm that it does cause issues." )]
    string TST_Prop;
};

// Instances for one association
// Relate two TST_EP instances (initiator, target) to 1 TST_LD (this
// class and subclass)
// NOTE: InstanceID is monotonically increasing integer for all instances
// in the model to make displays small and simplify tests
instance of TST_EP as $EP1I {
    InstanceID = 1;
    EP_Prop = "Initiator1";};

instance of TST_EP as $EP1T {
    InstanceID = 2;
    EP_Prop = "Target1";};

instance of TST_LD as $LD1 {
    InstanceID = 3;
    LD_Prop = "LogDev1";};

// The top level association instance
instance of TST_A3 as $A311 {
    Initiator = $EP1I;
    Target = $EP1T;
    LogicalUnit = $LD1;
};

// Extra instances that are not part of basic model but that will be used
// To create more instances in test

instance of TST_LDSub as $LD4Sub {
    InstanceID = 4;
    LD_Prop = "LogDev2";};

instance of TST_EP as $EP5I {
    InstanceID = 5;
    EP_Prop = "Initiator5";};

instance of TST_EPSub as $EPSub6I {
    InstanceID = 6;
    EP_Prop = "Initiator6";
    EP_SubProp = "Subprop EPSUB6I";};

instance of TST_EPSub as $EPSub7T {
    InstanceID = 7;
    EP_Prop = "Target7";
    EP_SubProp = "Subprop EPSUB7T";};
"""
    return tst_qualifiers_mof + '\n\n' + complex_associations_mof + '\n\n'


VERBOSE = False

# Flag that when set true causes the data for tests to be executed to be
# saved in a manner that we can duplicate the test through pywbemcli and
# OpenPegasus. This includes the test mof, the request and the expected response
SAVE_TEST = False

# test variables to allow selectively executing tests.
OK = True
RUN = True
FAIL = False


PYWBEMCLI_CMDS = 'complex_assoc_pywbemcli_cmds.txt'
COMPLEX_MODEL_MOF = 'complex_association_model.mof'
COMPLEX_MODEL_OUT_MOF = 'complex_association_model_out.mof'


@pytest.fixture(scope='module', autouse=True)
def cleanup():
    """
    Cleanup the save_data files if they exist and if running tests with
    SAVE_TEST == True. This should run once per execution of the tests.
    """
    if SAVE_TEST:
        if os.path.exists(COMPLEX_MODEL_OUT_MOF):
            os.remove(COMPLEX_MODEL_OUT_MOF)
        if os.path.exists(COMPLEX_MODEL_MOF):
            os.remove(COMPLEX_MODEL_MOF)
        if os.path.exists(PYWBEMCLI_CMDS):
            os.remove(PYWBEMCLI_CMDS)


def save_data(conn, mof, request, response, exp_response):
    """
    Save the defined strings to a file as a possible pywbemcli command set
    This includes:

    1. The original mof that defined the test
    2. The mof created by the mof compiler
    3. The corresponding pywbemcli request
    4. The corresponding pywbemcli response
    5. The expected response from the test
    """
    if SAVE_TEST:
        if not os.path.exists(COMPLEX_MODEL_OUT_MOF):
            conn.display_repository(dest=COMPLEX_MODEL_OUT_MOF)

        if not os.path.exists(COMPLEX_MODEL_MOF):
            with io.open('complex_association_model.mof', 'w',
                         encoding='utf-8') as f:
                print(mof, file=f)

        with io.open(PYWBEMCLI_CMDS, 'a', encoding='utf-8') as f:
            print('%s ' % request, file=f)
            print("Resp : %s" % response, file=f)
            print("ExpResp : %s" % exp_response, file=f)


X1 = """
// Instances for one association
// Relate two TST_EP instances (initiator, target) to 1 TST_LD (this
// class and subclass)
// This association replaces LogicalUnit with instance from subclass
instance of TST_A3 as $A3114 {
    Initiator = $EP1I;
    Target = $EP1T;
    LogicalUnit = $LD4Sub;
};
"""

X2 = """
// Instances for one association
// Relate two TST_EP instances (initiator, target) to 1 TST_LD (this
// class and subclass)
// NOTE: InstanceID is monotonically increasing integer for all instances
// in the model to make displays small and simplify tests
instance of TST_A3 as $A3511 {
    Initiator = $EP5I;
    Target = $EP1T;
    LogicalUnit = $LD1;
};
"""

X3 = """
// Instances for one association
// Relate two TST_EP instances (initiator, target) to 1 TST_LD (this
// class and subclass)
// NOTE: InstanceID is monotonically increasing integer for all instances
// in the model to make displays small and simplify tests
instance of TST_A3Sub as $A3Sub511 {
    Initiator = $EPSub6I;
    Target = $EPSub7T;
    LogicalUnit = $LD4Sub;
};
"""

X4 = """
// Instances for one association
// Relate two TST_EP instances (initiator, target) to 1 TST_LD (this
// class and subclass)
// NOTE: InstanceID is monotonically increasing integer for all instances
// in the model to make displays small and simplify tests
instance of TST_A3Sub as $A3Sub511 {
    Initiator = $EP1I;
    Target = $EPSub7T;
    LogicalUnit = $LD4Sub;
};
"""


@pytest.mark.parametrize(
    "ns", INITIAL_NAMESPACES + [None])
@pytest.mark.parametrize(
    "target, r, rc, mof, exp_rslt, cond", [
        # target: Target Classname (i.e. the association object name)
        # r: role attribute
        # ac: associated class attribute
        # rr: resultrole attribute
        # rc: resultclass attribute
        # mof: Extra instance MOF used for some tests
        # exp_result: Either list of names of expected classes returned
        #             or string defining error response
        # cond: True; run test; 'pdb'; start debugger; False; skip test
        # Test TST_EP  and role as initiator
        # targcln, r, rc
        # pylint: disable=line-too-long
        ['TST_EP', None, None, None, ['TST_A3'], OK],
        ['TST_EP', None, 'TST_A3', None, ['TST_A3'], OK],
        ['TST_EP', 'Initiator', 'TST_A3', None, ['TST_A3'], OK],
        ['TST_EP', 'Target', 'TST_A3', None, ['TST_A3'], OK],
        ['TST_EP', 'LogicalUnit', 'TST_A3', None, [], OK],
        ['TST_EPSub', 'Initiator', 'TST_A3', None, ['TST_A3', 'TST_A3Sub'], OK],

        ['TST_LD', None, None, None, ['TST_A3'], OK],
        ['TST_LD', None, 'TST_A3', None, ['TST_A3'], OK],
        ['TST_LD', 'LogicalUnit', 'TST_A3', None, ['TST_A3'], OK],
        ['TST_LDSub', 'LogicalUnit', 'TST_A3', None, ['TST_A3', 'TST_A3Sub'],
         OK],
    ]
)
def test_complexref_classnames(conn, ns, target, r, rc, mof, exp_rslt,
                               complex_assoc_mof, cond):
    # pylint: disable=redefined-outer-name,invalid-name
    """
    Test referencenames class operations against a ternary model defined by
    the fixture complex_assoc_mof
    """
    if not cond:
        pytest.skip("Condition for test case not met")

    skip_if_moftab_regenerated()

    mof = mof or ""
    conn.compile_mof_string(complex_assoc_mof + mof, namespace=ns)

    if ns is not None:
        target = CIMClassName(target, namespace=ns)
    if cond == 'pdb':
        # pylint: disable=import-outside-toplevel
        import pdb
        pdb.set_trace()  # pylint: disable=forgotten-debug-statement

    rtn_clns = conn.ReferenceNames(target, ResultClass=rc, Role=r)
    exp_ns = ns or conn.default_namespace

    assert isinstance(rtn_clns, list)
    for cln in rtn_clns:
        assert isinstance(cln, CIMClassName)
        assert cln.host == conn.host
        assert cln.namespace == exp_ns

    exp_clns = [CIMClassName(classname=n, namespace=exp_ns, host=conn.host)
                for n in exp_rslt]

    request = "pywbemcli class references {0} --role {1} --result_class {2}". \
        format(target, r, rc)
    response = [c.classname for c in exp_clns]
    exp_response = [c.classname for c in exp_clns]
    save_data(conn, complex_assoc_mof, request, response, exp_response)

    if VERBOSE:
        print('\nACT %s\nEXP %s' % ([c.classname for c in rtn_clns],
                                    [c.classname for c in exp_clns]))

    assert set(cln.classname.lower() for cln in exp_clns) == \
        set(cln.classname.lower() for cln in rtn_clns)


@pytest.mark.parametrize(
    "ns", INITIAL_NAMESPACES + [None])
@pytest.mark.parametrize(
    "target, r, rc, mof, exp_rslt, cond", [
        # target: Target Classname (i.e. the association object name)
        # r: role attribute
        # ac: associated class attribute
        # rr: resultrole attribute
        # rc: resultclass attribute
        # mof: MOF for Extra instances to compile to extend test
        # exp_result: List of instance names to be returned as tuple with
        #             item 0 classname, item 1, dictionary of reference prop
        #             definitions for each reference property
        # cond: True; run test; 'pdb'; start debugger; False; skip test
        # Test TST_EP  and role as initiator
        # targcln, r, rc
        (
            ('TST_EP', 1), None, None, None,
            [
                ('TST_A3', {'Initiator': ('TST_EP', 1),
                            'Target': ('TST_EP', 2),
                            'LogicalUnit': ('TST_LD', 3)})
            ],
            OK
        ),
        (
            ('TST_EP', 1), None, 'TST_A3', None,
            [
                ('TST_A3', {'Initiator': ('TST_EP', 1),
                            'Target': ('TST_EP', 2),
                            'LogicalUnit': ('TST_LD', 3)})
            ],
            OK
        ),
        (
            ('TST_EP', 1), 'Initiator', 'TST_A3', None,
            [
                ('TST_A3', {'Initiator': ('TST_EP', 1),
                            'Target': ('TST_EP', 2),
                            'LogicalUnit': ('TST_LD', 3)})
            ],
            OK
        ),
        (
            ('TST_EP', 1), 'Target', 'TST_A3', None,
            [],
            OK
        ),
        (
            ('TST_EP', 1), 'LogicalUnit', 'TST_A3', None,
            [],
            OK
        ),
        (
            ('TST_EPSub', 6), 'Initiator', 'TST_A3', None,
            [],
            OK
        ),
        (
            ('TST_EPSub', 6), 'Initiator', 'TST_A3Sub', X3,
            [
                ('TST_A3Sub', {'Initiator': ('TST_EPSub', 6),
                               'Target': ('TST_EPSub', 7),
                               'LogicalUnit': ('TST_LDSub', 4)})
            ],
            OK
        ),
        (
            ('TST_LD', 3), None, None, None,
            [
                ('TST_A3', {'Initiator': ('TST_EP', 1),
                            'Target': ('TST_EP', 2),
                            'LogicalUnit': ('TST_LD', 3)})
            ],
            OK
        ),
        (
            ('TST_LD', 3), None, 'TST_A3', None,
            [
                ('TST_A3', {'Initiator': ('TST_EP', 1),
                            'Target': ('TST_EP', 2),
                            'LogicalUnit': ('TST_LD', 3)})
            ],
            OK
        ),
        (
            ('TST_LD', 3), 'LogicalUnit', 'TST_A3', None,
            [
                ('TST_A3', {'Initiator': ('TST_EP', 1),
                            'Target': ('TST_EP', 2),
                            'LogicalUnit': ('TST_LD', 3)})
            ],
            OK
        ),
        (
            ('TST_LDSub', 4), 'LogicalUnit', 'TST_A3Sub', X3,
            [
                ('TST_A3Sub', {'Initiator': ('TST_EPSub', 6),
                               'Target': ('TST_EPSub', 7),
                               'LogicalUnit': ('TST_LDSub', 4)})
            ],
            OK
        ),
    ]
)
def test_complexref_instnames(conn, ns, target, r, rc, mof, exp_rslt,
                              complex_assoc_mof, cond):
    # pylint: disable=redefined-outer-name,invalid-name
    """
    Test referencenames class operations against a ternary model defined by
    the fixture complex_assoc_mof
    """

    if not cond:
        pytest.skip("Condition for test case not met")

    skip_if_moftab_regenerated()

    mof = mof or ""
    conn.compile_mof_string(complex_assoc_mof + mof, namespace=ns)

    if cond == 'pdb':
        # pylint: disable=import-outside-toplevel
        import pdb
        pdb.set_trace()  # pylint: disable=forgotten-debug-statement

    target_inst = CIMInstanceName(target[0],
                                  keybindings={'InstanceID': target[1]},
                                  namespace=ns)

    rtn_instnames = conn.ReferenceNames(target_inst, ResultClass=rc, Role=r)
    exp_ns = ns or conn.default_namespace

    assert isinstance(rtn_instnames, list)
    for instname in rtn_instnames:
        assert isinstance(instname, CIMInstanceName)
        assert instname.host == conn.host
        assert instname.namespace == exp_ns

    # Build the expected instance name to be returned. With the defined model
    # this is the association with 3 references. Each entry in exp_rslt
    # defines a classname and 3 integers representing the InstanceID of the
    # reference property
    exp_instnames = []
    if exp_rslt:
        for response_item in exp_rslt:
            kb = {}
            for prop_def, prop_value in response_item[1].items():
                kb[prop_def] = CIMInstanceName(prop_value[0],
                                               keybindings={'InstanceID':
                                                            prop_value[1]},
                                               namespace=exp_ns)
            exp_instnames.append(CIMInstanceName(response_item[0],
                                                 keybindings=kb,
                                                 namespace=exp_ns,
                                                 host=conn.host))

    rtn_instnames_str = [str(n) for n in rtn_instnames]
    exp_instnames_str = [str(n) for n in exp_instnames]
    if VERBOSE:
        print('\nACT:\n%s\nEXP:\n%s' % ("\n".join(rtn_instnames_str),
                                        "\n".join(exp_instnames_str)))

    request = "pywbemcli class references {0} --role {1} --result_class {2}". \
        format(target_inst, r, rc)
    save_data(conn, complex_assoc_mof, request, rtn_instnames_str,
              exp_instnames_str)

    assert set(exp_instnames) == set(rtn_instnames)


@pytest.mark.parametrize(
    "ns", INITIAL_NAMESPACES + [None])
@pytest.mark.parametrize(
    "target, r, ac, rr, rc, mof, exp_rslt, cond", [
        # targ: Target Classname (i.e. the association object name)
        # r: role attribute
        # ac: associated class attribute
        # rr: resultrole attribute
        # rc: resultclass attribute
        # mof: MOF for Extra instances to compile to extend test
        # exp_result: Either list of names of expected classes returned
        #             or string defining error response
        # cond: True; run test; 'pdb'; start debugger; False; skip test
        # Test TST_EP  and role as initiator
        # targcln, r, ac, rr, rc
        # pylint: disable=line-too-long
        ['TST_EP', None, None, None, None, None, ['TST_EP', 'TST_LD'], OK],
        ['TST_EP', None, 'TST_A3', None, None, None, ['TST_EP', 'TST_LD'], OK],
        ['TST_EP', 'Initiator', None, None, None, None, ['TST_EP', 'TST_LD'], OK],  # noqa: 501
        ['TST_EP', 'Initiator', 'TST_A3', None, None, None, ['TST_EP', 'TST_LD'], OK],  # noqa: 501
        ['TST_EP', None, 'TST_A3', 'Target', None, None, ['TST_EP'], OK],
        ['TST_EP', 'Initiator', 'TST_A3', 'Target', None, None, ['TST_EP'], OK],
        ['TST_EP', None, 'TST_A3', 'Target', 'TST_LD', None, [], OK],
        ['TST_EP', 'Initiator', 'TST_A3', 'Target', None, None, ['TST_EP'], OK],
        ['TST_EP', 'Initiator', 'TST_A3', 'Target', 'TST_LD', None, [], OK],
        ['TST_EP', 'Initiator', 'TST_A3', 'LogicalUnit', 'TST_LD', None, ['TST_LD'], OK],  # noqa: 501
        # test for case indepence on all parameters
        ['tst_ep', 'INITIATOR', 'tst_a3', 'LOGICALUNIT', 'tst_ld', None, ['TST_LD'], OK],  # noqa: 501

        # test source TST_EP and Target as role
        ['TST_EP', None, None, None, None, None, ['TST_EP', 'TST_LD'], OK],
        ['TST_EP', None, 'TST_A3', None, None, None, ['TST_EP', 'TST_LD'], OK],
        ['TST_EP', 'Target', None, None, None, None, ['TST_EP', 'TST_LD'], OK],
        ['TST_EP', 'Target', 'TST_A3', None, None, None, ['TST_EP', 'TST_LD'], OK],  # noqa: 501
        ['TST_EP', None, 'TST_A3', 'Initiator', None, None, ['TST_EP'], OK],
        ['TST_EP', 'Target', 'TST_A3', 'Initiator', None, None, ['TST_EP'], OK],
        ['TST_EP', None, 'TST_A3', 'Initiator', 'TST_LD', None, [], OK],
        ['TST_EP', 'Target', 'TST_A3', 'Initiator', None, None, ['TST_EP'], OK],
        ['TST_EP', 'Target', 'TST_A3', 'Initiator', 'TST_LD', None, [], OK],
        ['TST_EP', 'Target', 'TST_A3', 'LogicalUnit', 'TST_LD', None, ['TST_LD'], OK],  # noqa: 501

        # Test source TST_LD, Initiator as ResultRole
        # TODO 4 Failures. PEG Returns TST_EP only. Mock ACT TST_EP and TST_LD
        ['TST_LD', None, None, None, None, None, ['TST_EP'], OK],
        ['TST_LD', None, 'TST_A3', None, None, None, ['TST_EP'], OK],
        ['TST_LD', 'LogicalUnit', None, None, None, None, ['TST_EP'], OK],
        ['TST_LD', 'LogicalUnit', 'TST_A3', None, None, None, ['TST_EP'], OK],
        ['TST_LD', None, 'TST_A3', 'Initiator', None, None, ['TST_EP'], OK],
        # TODO: did we miss this option with all params in tests above
        ['TST_LD', 'LogicalUnit', 'TST_A3', 'Initiator', 'TST_EP', None, ['TST_EP'], OK],  # noqa: 501
        ['TST_LD', 'LogicalUnit', 'TST_A3', 'Initiator', None, None, ['TST_EP'], OK],  # noqa: 501
        ['TST_LD', None, 'TST_A3', 'Initiator', 'TST_LD', None, [], OK],
        ['TST_LD', 'LogicalUnit', 'TST_A3', 'Initiator', None, None, ['TST_EP'], OK],  # noqa: 501
        ['TST_LD', 'LogicalUnit', 'TST_A3', 'Initiator', 'TST_EP', None, ['TST_EP'], OK],  # noqa: 501

        ['TST_LD', 'LogicalUnit', 'TST_A3', 'Initiator', 'TST_LD', None, [], OK],  # noqa: 501
        ['TST_LD', 'LogicalUnit', 'TST_A3', 'Target', None, None, ['TST_EP'], OK],  # noqa: 501
        ['TST_LD', None, 'TST_A3', 'Target', 'TST_LD', None, [], OK],
        ['TST_LD', 'LogicalUnit', 'TST_A3', 'Target', None, None, ['TST_EP'], OK],  # noqa: 501
        ['TST_LD', 'LogicalUnit', 'TST_A3', 'Target', 'TST_EP', None, ['TST_EP'], OK],  # noqa: 501
        ['TST_LD', 'LogicalUnit', 'TST_A3', 'Target', 'TST_LD', None, [], OK],
        # pylint: enable=line-too-long

    ]
)
def test_complexassoc_classnames(conn, ns, target, r, rr, ac,
                                 rc, mof, exp_rslt, complex_assoc_mof, cond):
    # pylint: disable=redefined-outer-name,invalid-name
    """
    Test associatornames class operations against a ternary model defined by
    the fixture complex_assoc_mof. We do not test the associator calls
    since that logic just takes the names and expands to return instances
    """
    if not cond:
        pytest.skip("Condition for test case not met")

    skip_if_moftab_regenerated()

    mof = mof or ""
    conn.compile_mof_string(complex_assoc_mof + mof, namespace=ns)

    if ns is not None:
        target = CIMClassName(target, namespace=ns)
    if cond == 'pdb':
        # pylint: disable=import-outside-toplevel
        import pdb
        pdb.set_trace()  # pylint: disable=forgotten-debug-statement

    rtn_clns = conn.AssociatorNames(target,
                                    AssocClass=ac,
                                    Role=r,
                                    ResultRole=rr,
                                    ResultClass=rc)
    exp_ns = ns or conn.default_namespace

    assert isinstance(rtn_clns, list)
    for cln in rtn_clns:
        assert isinstance(cln, CIMClassName)
        assert cln.host == conn.host
        assert cln.namespace == exp_ns

    exp_clns = [CIMClassName(classname=n, namespace=exp_ns, host=conn.host)
                for n in exp_rslt]
    if VERBOSE:
        print('\nACT %s\nEXP %s' % ([c.classname for c in rtn_clns],
                                    [c.classname for c in exp_clns]))

    request = "pywbemcli class associators {0} --role {1} --assoc-class {2} " \
        "--result-role {3} --result-class {4}". \
        format(target, r, ac, rr, rc)
    save_data(conn, complex_assoc_mof, request, rtn_clns, exp_clns)

    assert set(cln.classname.lower() for cln in exp_clns) == \
        set(cln.classname.lower() for cln in rtn_clns)


@pytest.mark.parametrize(
    "ns", INITIAL_NAMESPACES + [None])
@pytest.mark.parametrize(
    "target, r, ac, rr, rc, , mof, exp_rslt, cond", [
        # target: Tuple or list representing instname with 2 components
        #         (Classname, value for InstanceID key property)
        # r: role attribute
        # ac: associated class attribute
        # rr: resultrole attribute
        # rc: resultclass attribute
        # mof: MOF for Extra instances to compile to extend test
        # exp_result: Either list of names of expected classes returned
        #             or string defining error response
        # cond: True; run test; 'pdb'; start debugger; False; skip test
        # targ, r, ac, rr, rc, exp_result, cond
        # pylint: disable=line-too-long
        [
            ('TST_EP', 1), None, None, None, None, None,
            [
                ('TST_EP', 2),
                ('TST_LD', 3)
            ],
            OK
        ],
        [
            ('TST_EP', 1), None, 'TST_A3', None, None, None,
            [
                ('TST_EP', 2),
                ('TST_LD', 3)
            ],
            OK
        ],
        [
            ('TST_EP', 1), 'Initiator', None, None, None, None,
            [
                ('TST_EP', 2),
                ('TST_LD', 3)
            ],
            OK
        ],
        [
            ('TST_EP', 1), 'Initiator', 'TST_A3', None, None, None,
            [
                ('TST_EP', 2),
                ('TST_LD', 3)
            ],
            OK
        ],
        [
            ('TST_EP', 1), None, 'TST_A3', 'Target', None, None,
            [
                ('TST_EP', 2)
            ],
            OK
        ],
        [
            ('TST_EP', 1), 'Initiator', 'TST_A3', 'Target', None, None,
            [
                ('TST_EP', 2)
            ],
            OK
        ],
        [
            ('TST_EP', 1), None, 'TST_A3', 'Target', 'TST_LD', None,
            [],
            OK
        ],
        [
            ('TST_EP', 1), 'Initiator', 'TST_A3', 'Target', None, None,
            [
                ('TST_EP', 2)
            ],
            OK
        ],
        [
            ('TST_EP', 1), 'Initiator', 'TST_A3', 'Target', 'TST_LD', None,
            [],
            OK
        ],
        [
            ('TST_EP', 1), 'Initiator', 'TST_A3', 'LogicalUnit', 'TST_LD', None,
            [
                ('TST_LD', 3)
            ],
            OK
        ],

        # test source TST_EP and Target as role
        [
            ('TST_EP', 1), None, None, None, None, None,
            [
                ('TST_EP', 2),
                ('TST_LD', 3)
            ],
            OK
        ],
        [
            ('TST_EP', 1), None, 'TST_A3', None, None, None,
            [
                ('TST_EP', 2),
                ('TST_LD', 3)
            ],
            OK
        ],
        [
            ('TST_EP', 1), 'Target', None, None, None, None,
            [],
            OK
        ],
        [
            ('TST_EP', 1), 'Target', 'TST_A3', None, None, None,
            [],
            OK
        ],
        [
            ('TST_EP', 1), None, 'TST_A3', 'Initiator', None, None,
            [],
            OK
        ],
        [
            ('TST_EP', 1), 'Target', 'TST_A3', 'Initiator', None, None,
            [],
            OK
        ],
        [
            ('TST_EP', 1), None, 'TST_A3', 'Initiator', 'TST_LD', None,
            [],
            OK
        ],
        [
            ('TST_EP', 1), 'Target', 'TST_A3', 'Initiator', None, None,
            [],
            OK
        ],
        [
            ('TST_EP', 1), 'Target', 'TST_A3', 'Initiator', 'TST_LD', None,
            [],
            OK
        ],
        [
            ('TST_EP', 1), 'Target', 'TST_A3', 'LogicalUnit', 'TST_LD', None,
            [],
            OK
        ],

        # Repeat for second EP
        [
            ('TST_EP', 2), None, None, None, None, None,
            [
                ('TST_EP', 1),
                ('TST_LD', 3)
            ],
            OK
        ],
        [
            ('TST_EP', 2), None, 'TST_A3', None, None, None,
            [
                ('TST_EP', 1),
                ('TST_LD', 3)
            ],
            OK
        ],
        [
            ('TST_EP', 2), 'Initiator', None, None, None, None,
            [],
            OK
        ],
        [
            ('TST_EP', 2), 'Initiator', 'TST_A3', None, None, None,
            [],
            OK
        ],
        [
            ('TST_EP', 2), None, 'TST_A3', 'Target', None, None,
            [],
            OK
        ],
        [
            ('TST_EP', 2), 'Initiator', 'TST_A3', 'Target', None, None,
            [],
            OK
        ],
        [
            ('TST_EP', 2), None, 'TST_A3', 'Target', 'TST_LD', None,
            [],
            OK
        ],
        [
            ('TST_EP', 2), 'Initiator', 'TST_A3', 'Target', None, None,
            [],
            OK
        ],
        [
            ('TST_EP', 2), 'Initiator', 'TST_A3', 'Target', 'TST_LD', None,
            [],
            OK
        ],
        [
            ('TST_EP', 2), None, None, None, None, None,
            [
                ('TST_EP', 1),
                ('TST_LD', 3)
            ],
            OK
        ],
        [
            ('TST_EP', 2), None, 'TST_A3', None, None, None,
            [
                ('TST_EP', 1),
                ('TST_LD', 3)
            ],
            OK
        ],
        [
            ('TST_EP', 2), 'Target', None, None, None, None,
            [
                ('TST_EP', 1),
                ('TST_LD', 3)
            ],
            OK
        ],
        [
            ('TST_EP', 2), 'Target', 'TST_A3', None, None, None,
            [
                ('TST_EP', 1),
                ('TST_LD', 3)
            ],
            OK
        ],
        [
            ('TST_EP', 2), None, 'TST_A3', 'Initiator', None, None,
            [
                ('TST_EP', 1)
            ],
            OK
        ],
        [
            ('TST_EP', 2), 'Target', 'TST_A3', 'Initiator', None, None,
            [
                ('TST_EP', 1)
            ],
            OK
        ],
        [
            ('TST_EP', 2), None, 'TST_A3', 'Initiator', 'TST_LD', None,
            [],
            OK
        ],
        [
            ('TST_EP', 2), 'Target', 'TST_A3', 'Initiator', None, None,
            [
                ('TST_EP', 1)
            ],
            OK
        ],
        [
            ('TST_EP', 2), 'Target', 'TST_A3', 'Initiator', 'TST_LD', None,
            [],
            OK
        ],
        [
            ('TST_EP', 2), 'Target', 'TST_A3', 'LogicalUnit', 'TST_LD', None,
            [
                ('TST_LD', 3)
            ],
            OK
        ],

        # Test source TST_LD, Initiator as ResultRole
        [
            ('TST_LD', 3), None, None, None, None, None,
            [
                ('TST_EP', 1),
                ('TST_EP', 2)
            ],
            OK
        ],
        [
            ('TST_LD', 3), None, 'TST_A3', None, None, None,
            [
                ('TST_EP', 1),
                ('TST_EP', 2)
            ],
            OK
        ],
        [
            ('TST_LD', 3), 'LogicalUnit', None, None, None, None,
            [('TST_EP', 1), ('TST_EP', 2)],
            OK
        ],
        [
            ('TST_LD', 3), 'LogicalUnit', 'TST_A3', None, None, None,
            [
                ('TST_EP', 1),
                ('TST_EP', 2)
            ],
            OK
        ],
        [
            ('TST_LD', 3), None, 'TST_A3', 'Initiator', None, None,
            [
                ('TST_EP', 1)
            ],
            OK
        ],
        # TODO did we miss this option with all params in tests above
        [
            ('TST_LD', 3), 'LogicalUnit', 'TST_A3', 'Initiator', 'TST_EP', None,
            [
                ('TST_EP', 1)
            ],
            OK
        ],
        [
            ('TST_LD', 3), 'LogicalUnit', 'TST_A3', 'Initiator', None, None,
            [
                ('TST_EP', 1)
            ],
            OK
        ],

        [
            ('TST_LD', 3), None, 'TST_A3', 'Initiator', 'TST_EP', None,
            [
                ('TST_EP', 1)
            ],
            OK
        ],
        [
            ('TST_LD', 3), 'LogicalUnit', 'TST_A3', 'Initiator', None, None,
            [
                ('TST_EP', 1)
            ],
            OK
        ],
        [
            ('TST_LD', 3), 'LogicalUnit', 'TST_A3', 'Initiator', 'TST_EP', None,
            [
                ('TST_EP', 1)
            ],
            OK
        ],
        [
            ('TST_LD', 3), 'LogicalUnit', 'TST_A3', 'Initiator', 'TST_LD', None,
            [],
            OK
        ],
        [
            ('TST_LD', 3), 'LogicalUnit', 'TST_A3', 'Target', None, None,
            [
                ('TST_EP', 2)
            ],
            OK
        ],
        # [
        #     ('TST_LD', 3), None, 'TST_A3', 'Target', 'TST_LD', None, None,
        #     [],
        #     OK
        # ],
        [
            ('TST_LD', 3), 'LogicalUnit', 'TST_A3', 'Target', None, None,
            [
                ('TST_EP', 2)
            ],
            OK
        ],
        [
            ('TST_LD', 3), 'LogicalUnit', 'TST_A3', 'Target', 'TST_EP', None,
            [
                ('TST_EP', 2)
            ],
            OK
        ],
        [
            ('TST_LD', 3), 'LogicalUnit', 'TST_A3', 'Target', 'TST_LD', None,
            [],
            OK
        ],

        # add extra instance of association with subclass of LD
        [
            ('TST_EP', 1), None, None, None, None, X1,
            [
                ('TST_EP', 2),
                ('TST_LD', 3),
                ('TST_LDSub', 4)
            ],
            OK
        ],
        [
            ('TST_EP', 1), None, None, None, 'TST_LDSub', X1,
            [
                ('TST_LDSub', 4)
            ],
            OK
        ],

        # add extra instance of association with multiple instances of EP
        [
            ('TST_EP', 1), None, None, None, None, X2,
            [
                ('TST_EP', 2),
                ('TST_LD', 3)
            ],
            OK
        ],
        [
            ('TST_EP', 1), None, None, None, None, X2,
            [
                ('TST_EP', 2),
                ('TST_LD', 3)
            ],
            OK
        ],
        [
            ('TST_EP', 2), None, None, None, None, X2,
            [
                ('TST_EP', 1),
                ('TST_LD', 3),
                ('TST_EP', 5)
            ],
            OK
        ],
        [
            ('TST_EP', 5), None, None, None, 'TST_EP', X2,
            [
                ('TST_EP', 2)
            ],
            OK
        ],
        [
            ('TST_EP', 1), None, None, None, 'TST_EPSub', X2,
            [],
            OK
        ],

        # Test gets subclass of assoc class
        [
            ('TST_EP', 1), None, None, None, None, X4,
            [
                ('TST_EP', 2),
                ('TST_LD', 3),
                ('TST_EPSub', 7),
                ('TST_LDSub', 4)
            ],
            OK
        ],
        [
            ('TST_EP', 1), 'Initiator', None, None, None, X4,
            [
                ('TST_EP', 2),
                ('TST_LD', 3),
                ('TST_EPSub', 7),
                ('TST_LDSub', 4)
            ],
            OK
        ],

        # TODO fails becuase of TST_A3 class.  Should this be class and
        # subclasses.
        [
            ('TST_EP', 1), 'Initiator', 'TST_A3', None, None, X4,
            [
                ('TST_EP', 2),
                ('TST_LD', 3),
                ('TST_EPSub', 7),
                ('TST_LDSub', 4)
            ],
            OK
        ],

        # Test with subclass as target instance
        [
            ('TST_EPSub', 6), None, None, None, None, X3,
            [
                ('TST_EPSub', 7),
                ('TST_LDSub', 4)
            ],
            FAIL
        ],
    ]
)
def test_complexassoc_instnames(conn, ns, target, r, rr, ac,
                                rc, mof, exp_rslt, complex_assoc_mof, cond):
    # pylint: disable=redefined-outer-name,invalid-name
    """
    Test associatornames class operations against a ternary model defined by
    the fixture complex_assoc_mof
    """
    if not cond:
        pytest.skip("Condition for test case not met")

    if cond == 'pdb':
        # pylint: disable=import-outside-toplevel
        import pdb
        pdb.set_trace()  # pylint: disable=forgotten-debug-statement

    skip_if_moftab_regenerated()

    mof = mof or ""

    conn.compile_mof_string(complex_assoc_mof + mof, namespace=ns)

    if VERBOSE:
        conn.display_repository()

    assert isinstance(target, (tuple, list))
    for rslt in exp_rslt:
        assert isinstance(rslt, (tuple, list))

    target_inst = CIMInstanceName(target[0],
                                  keybindings={'InstanceID': target[1]},
                                  namespace=ns)
    exp_ns = ns or conn.default_namespace
    exp_instnames = []
    if exp_rslt:
        for item in exp_rslt:
            assert conn.GetClass(item[0])  # Test to assure class exists
            exp_instnames.append(CIMInstanceName(item[0],
                                                 keybindings={'InstanceID':
                                                              item[1]},
                                                 namespace=exp_ns,
                                                 host=conn.host))

    rtn_instnames = conn.AssociatorNames(target_inst,
                                         AssocClass=ac,
                                         Role=r,
                                         ResultRole=rr,
                                         ResultClass=rc)

    assert isinstance(rtn_instnames, list)
    for instname in rtn_instnames:
        assert isinstance(instname, CIMInstanceName)
        assert instname.host == conn.host
        assert instname.namespace == exp_ns

    rtn_instnames_str = [str(n) for n in rtn_instnames]
    exp_instnames_str = [str(n) for n in exp_instnames]
    if VERBOSE:
        print('\nACT:\n%s\nEXP:\n%s' % ("\n".join(rtn_instnames_str),
                                        "\n".join(exp_instnames_str)))

    request = "pywbemcli class associators {0} --role {1} --assoc-class {2} " \
        "--result-role {3} --result-class {4}". \
        format(target_inst, r, ac, rr, rc)
    save_data(conn, complex_assoc_mof, request, rtn_instnames_str,
              exp_instnames_str)

    assert set(exp_instnames) == set(rtn_instnames)
    # TODO this should be in conftest.py
    # assert_equal_ciminstancenames(exp_instnames, rtn_instnames)
