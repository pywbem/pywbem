# -*- coding: utf-8 -*-
#
# (C) Copyright 2022 InovaDevelopment.com
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
Pywbem mock tests for associations that crosses namespaces.  These
tests are separate because the multi-namespace capability was added in pywbem
1.1 so it was simpler to add a new test file. The tests
provide a test of the logic of processing these associations.
"""
from __future__ import absolute_import, print_function

import pytest

from ...utils import skip_if_moftab_regenerated
from ..utils.pytest_extensions import simplified_test_function

# pylint: disable=wrong-import-position, wrong-import-order, invalid-name
from pywbem._utils import _format  # noqa: E402

from ...utils import import_installed
pywbem = import_installed('pywbem')

from pywbem import DEFAULT_NAMESPACE, CIMInstanceName, CIMProperty, \
    CIMInstance, CIMError, CIM_ERR_NOT_FOUND, MOFRepositoryError, \
    Uint32  # noqa: E402

pywbem_mock = import_installed('pywbem_mock')
from pywbem_mock import FakedWBEMConnection  # noqa:E402
# pylint: enable=wrong-import-position, wrong-import-order, invalid-name

# List of initially existing namespaces in the CIM repository
INITIAL_NAMESPACES = [DEFAULT_NAMESPACE]

#
# Class mof for associations and endpoints. This is created in all namespaces.
#
TST_CLASSES_MOF = """
    Qualifier Association : boolean = false,
        Scope(association),
        Flavor(DisableOverride, ToSubclass);

    Qualifier Description : string = null,
        Scope(any),
        Flavor(EnableOverride, ToSubclass, Translatable);

    Qualifier Key : boolean = false,
        Scope(property, reference),
        Flavor(DisableOverride, ToSubclass);

    class TST_Person{
            [Key, Description ("This is key prop")]
        string name;
        string extraProperty = "defaultvalue";
    };

    class TST_Personsub : TST_Person{
        string secondProperty = "empty";
        uint32 counter;
    };

    [ Description("Third endpoint for TST_MemberOfGroup3EP") ]
    class TST_THIRD_EP {
            [Key, Description ("This is key prop and endpoint name")]
        string name;
    };

    [ Description("Collection of Persons into a group") ]
    class TST_Group {
            [Key, Description ("This is key prop and group name")]
        string name;
    };

    [Association, Description("Association defines the relationship "
        "between people and groups with InstanceID as key.") ]
    class TST_MemberOfGroup {
        [key] string InstanceID;
        TST_Person ref member;
        TST_Group ref group;
            [Description("Extra parameter to allow ModifyInstance test")]
        string ExtraPropStr;
        uint32 ExtraPropInt;
    };

    [Association, Description(" Association defines the relationship "
        "between people and groups with reference properties as keys.") ]
    class TST_MemberOfGroupNoID {
        [key] TST_Person ref member;
        [key] TST_Group ref group;
            [Description("Extra parameter to allow ModifyInstance test")]
        string ExtraPropStr;
        uint32 ExtraPropInt;
    };

    [Association, Description(" Association defines the 3-way relationship "
        "between people, groups, and 3ep with reference properties as keys.") ]
    class TST_MemberOfGroup3EP {
        [key] string InstanceID;
        TST_Person ref member;
        TST_Group ref group;
        TST_THIRD_EP ref ep_3;
            [Description("Extra parameter to allow ModifyInstance test")]
        string ExtraPropStr;
        uint32 ExtraPropInt;

    };

"""

# MOF of Simple cross namespace association endpoint where association key is
# InstanceID. This defines the instances for one of the association endpoints,
# normally TST_Person
INSTANCE_INITIAL_ENDPOINTS = """
instance of TST_Person as $Mike { name = "Mike"; };

"""

# This defines the common endpoint and the association of
# TST_MemberOfGroup in ns1.
ASSOCIATION_MOF_SAME_NS = """
// association in same namespace

instance of TST_Group as $NS1G1
{
    name = "ns1group1";
};

instance of TST_MemberOfGroup as $G1MikeNS1
{
    InstanceID = "G1MikeNS1";
    member = $Mike;
    group = $NS1G1;
};

"""

# Association TST_MemberOfGroup in ns1 with person in ns1, group in ns2,
# and the association in ns1
ASSOCIATION_MOF_CROSS_NS = """
// association crosses namespaces

#pragma namespace ("ns2")
// target instance
instance of TST_Group as $NS2G1
{
    name = "ns2group1";
};

#pragma namespace ("ns1")
instance of TST_MemberOfGroup as $G1MikeNS2
{
    InstanceID = "G1MikeNS1";
    member = $Mike;
    group = $NS2G1;
    ExtraPropStr = "OrigValue";
    ExtraPropInt = 999;
};
"""

# Association TST_MemberOfGroup in ns1 with person in ns1, group in ns2,
# and the association in ns1 with extra properties in association. Used to
# test modify instance
ASSOCIATION_MOF_CROSS_NS_NO_EXTRAPROPS = """
// association crosses namespaces

#pragma namespace ("ns2")
// target instance
instance of TST_Group as $NS2G1
{
    name = "ns2group1";
};

#pragma namespace ("ns1")
instance of TST_MemberOfGroup as $G1MikeNS2
{
    InstanceID = "G1MikeNS1";
    member = $Mike;
    group = $NS2G1;

};
"""

# Association TST_MemberOfGroup in ns1 with person in ns1 and group in ns2
ASSOCIATION_MOF_CROSS_NS_CAUSES_CLASSERROR = """
// association crosses namespaces

#pragma namespace ("ns2")
// target instance
instance of TST_Group as $NS2G1
{
    name = "ns2group1";
};

#pragma namespace ("ns1")
instance of TST_MemberOfGroup as $G1MikeNS2
{
    InstanceID = "G1MikeNS1";
    member = $Mike;
    group = $NS2G1;
};
"""

# Association TST_MemberOfGroupNoID in ns1 with person in ns1 and group in ns2
# Assoc key is ref properties
ASSOCNOID_MOF_CROSS_NS = """
// association crosses namespaces

#pragma namespace ("ns2")
// target instance
instance of TST_Group as $NS2G1
{
    name = "ns2group1";
};

#pragma namespace ("ns1")
instance of TST_MemberOfGroupNoID as $G1MikeNS2A2
{
    member = $Mike;
    group = $NS2G1;
};

"""


# Association 3-way with TST_THIRD_EP endpoint and instance of
# TST_MemberOfGroup3EP
ASSOCIATIONX_3WAY_MOF_CROSS_NS = """
// association crosses namespaces

#pragma namespace ("ns2")
// target instance
instance of TST_Group as $NS2G1
{
    name = "ns2group1";
};

#pragma namespace ("ns3")
// target instance  of class TST_THIRD_EP
instance of TST_THIRD_EP as $NS3X1
{
    name = "ns3X1";
};

#pragma namespace ("ns1")
instance of TST_MemberOfGroup3EP as $G1MikeAxNs3
{
    InstanceID = "G1MikeAxNs3";
    member = $Mike;
    group = $NS2G1;
    ep_3 = $NS3X1;
};

"""


# Instance paths for instances of MenberOfGroupNoID, the association that
# uses the references as keys.  Too long to insert into tests themselves.
COMMON_MEMBEROFGROUPNOID = 'TST_MemberOfGroupNoID.group="/ns2:TST_Group.' \
    'name=\\"ns2group1\\"",member="/ns1:TST_Person.name=\\"Mike\\""'

MEMBEROFGROUPNOIDNS1 = '/ns1:' + COMMON_MEMBEROFGROUPNOID
MEMBEROFGROUPNOIDNS2 = '/ns2:' + COMMON_MEMBEROFGROUPNOID

# test variables to allow selectively executing tests.
OK = True
RUN = True
FAIL = False
VERBOSE = False


def create_repository(conn, namespaces, class_mof, inst_mof, assoc_inst_mof):
    """
    Create the namespaces, qualdecls, classes, instances for the test
    """
    # Create remaining namespaces
    for ns in namespaces:
        if ns not in conn.namespaces:
            conn.add_namespace(ns)

    skip_if_moftab_regenerated()

    # Compile the class mof in all namespaces
    for ns in namespaces:
        for mof in class_mof:
            conn.compile_mof_string(mof, ns)

    # Compile all instance mof together to utilize compiler alias capability
    # each of the components is a list.
    all_inst_mof = "\n".join(inst_mof) + "\n".join(assoc_inst_mof)

    conn.compile_mof_string(all_inst_mof)


def val_act_exp_paths(act_rtns, exp_rtn, ns, operation, source_cln):
    """
    Test that the  actual instance paths are exactly the same as
    the expected returns in exp_rtn[ns][operation][source_cln].

    Ignores host parameter of returned instance paths
    """

    assert isinstance(act_rtns, list)

    # Get expected returns for this ns, operation, and source_cln
    # from exp_rtn dictionary
    exp_rtns = exp_rtn[ns][operation][source_cln]

    # Convert URIs in exp_rtns to CIMInstanceName objects
    exp_objs = [CIMInstanceName.from_wbem_uri(p) for p in exp_rtns]

    assert len(act_rtns) == len(exp_rtns), \
        _format("ns:{}, operation:{}, source_cln:{}", ns, operation, source_cln)

    for instname in act_rtns:
        instname.host = None

    assert set(act_rtns) == set(exp_objs), \
        _format("ns:{}, operation:{}, tst_class:{}", ns, operation, source_cln)


def validate_instance_enumeration(conn, namespaces, enum_clns, exp_rtn):
    """
    Validate that EnumerateInstances returns correct instances. Note we only
    test instance names. The enum_clns is the list of all classnames for which
    EnumerateInstanceNames is to be executed.
    """
    for ns in namespaces:
        # Test EnumerateInstanceNames for all classes in enumeration
        for tst_cln in enum_clns:
            inst_paths = conn.EnumerateInstanceNames(tst_cln, namespace=ns)
            val_act_exp_paths(inst_paths, exp_rtn, ns, 'ENUM', tst_cln)


def validate_instance_associations(conn, namespaces, source_clns, exp_rtn):
    """
    Test that AssociationNames and ReferenceNames return correct instance
    paths
    """
    for ns in namespaces:
        # Test References and Associators for each classname in source_clns
        # This tests associations in both directions.
        for source_cln in source_clns:
            # Test only if there is an instance of source_cln
            if conn.EnumerateInstances(source_cln):
                source_paths = conn.EnumerateInstanceNames(source_cln,
                                                           namespace=ns)

                for source_path in source_paths:
                    # Compare ReferenceNames and AssociatonNames requests
                    inst_paths = conn.ReferenceNames(source_path)
                    val_act_exp_paths(inst_paths, exp_rtn, ns, 'REF',
                                      source_cln)
                    inst_paths = conn.AssociatorNames(source_path)
                    val_act_exp_paths(inst_paths, exp_rtn, ns, 'ASSOC',
                                      source_cln)

                    # Compare paths of References returns
                    insts = conn.References(source_path)
                    # Validate path and reference property same values
                    for inst in insts:
                        keys = inst.path.keybindings
                        for prop in inst.properties.values():
                            if prop.type == 'references':
                                if prop.name in keys:
                                    assert prop.value == keys[prop.name]
                    inst_paths = [i.path for i in insts]
                    val_act_exp_paths(inst_paths, exp_rtn, ns, 'REF',
                                      source_cln)

                    # Compare paths of Associator returns
                    insts = conn.Associators(source_path)
                    inst_paths = [r.path for r in insts]
                    val_act_exp_paths(inst_paths, exp_rtn, ns, 'ASSOC',
                                      source_cln)


# pylint: disable=bad-continuation


TESTCASES_MULTI_NAMESPACES = [
    # Each list item is a testcase tuple with these items:
    # * desc: Short testcase description.
    # * kwargs: Keyword arguments for the test function:
    #   * namespaces - List of namespaces in mock environment
    #   * class_mof - list of strings containing qualdecl and class mof to
    #     be compiled
    #   * inst_mof - list of strings containing instance mof to be compiled
    #   * assoc_inst_mof - list of strings  containing instances defining
    #     associations to be compiled. These strings must define the namespace
    #     for components that are not in the default namespace.
    #   * source classnames for ENUM, REF, ASSOC tests - The classnames that
    #     are the source classes for these operations
    #   * assoc_clns - The classname of the reference class being tested
    #   * delete_ns - If not None, defnes namespace from which association
    #     is deleted in delete test.  If None, deleted from creation ns.
    #   * exp_rtn: dictionary containing expected return objects (primarily
    #     CIMInstanceNames). The dictionary is defined as
    #     {<namespace>: <operation>: <source_class>: list of results instance
    #     names.
    # * exp_exc_types: Expected exception type(s), or None.
    # * exp_warn_types: Expected warning type(s), or None.
    # * condition: Boolean condition for testcase to run, or 'pdb' for
    #   debugger

    (
        "Test association in one namespace. Assures model/test works",
        dict(
            # first namespace becomes the default namespace
            namespaces=['ns1', 'ns2'],
            class_mof=[TST_CLASSES_MOF],
            inst_mof=[INSTANCE_INITIAL_ENDPOINTS],
            assoc_inst_mof=[ASSOCIATION_MOF_SAME_NS],
            source_clns=['TST_Person', 'TST_Group'],
            assoc_clns='TST_MemberOfGroup',
            delete_ns=None,
            exp_rtn={
                'ns1':
                    {'ENUM':
                        {'TST_Person': ['/ns1:TST_Person.name="Mike"'],
                         'TST_Group': ['/ns1:TST_Group.name="ns1group1"'],
                         'TST_MemberOfGroup':
                             ['/ns1:TST_MemberOfGroup.InstanceID="G1MikeNS1"']},
                     'REF':
                        {'TST_Person':
                             ['/ns1:TST_MemberOfGroup.InstanceID="G1MikeNS1"'],
                         'TST_Group':
                             ['/ns1:TST_MemberOfGroup.InstanceID="G1MikeNS1"']},
                     'ASSOC':
                        {'TST_Group': ['/ns1:TST_Person.name="Mike"'],
                         'TST_Person': ['/ns1:TST_Group.name="ns1group1"']}, },
                'ns2':
                    {'ENUM':
                        {'TST_Person': [],
                         'TST_Group': [],
                         'TST_MemberOfGroup': []},
                     'REF':
                        {'TST_Person': []},
                     'ASSOC':
                        {'TST_Person': [],
                         'TST_Group': []}, },
            },
        ),
        None, None, OK
    ),

    (
        "Test association cross namespaces with MemberOfGroup",
        dict(
            # first namespace becomes the default namespace
            namespaces=['ns1', 'ns2'],
            class_mof=[TST_CLASSES_MOF],
            inst_mof=[INSTANCE_INITIAL_ENDPOINTS],
            assoc_inst_mof=[ASSOCIATION_MOF_CROSS_NS],
            source_clns=['TST_Person', 'TST_Group'],
            assoc_clns='TST_MemberOfGroup',
            delete_ns=None,
            exp_rtn={
                'ns1':
                    {'ENUM':
                        {'TST_Person': ['/ns1:TST_Person.name="Mike"'],
                         'TST_Group': [],
                         'TST_MemberOfGroup':
                             ['/ns1:TST_MemberOfGroup.InstanceID="G1MikeNS1"']},
                     'REF':
                        {'TST_Person':
                             ['/ns1:TST_MemberOfGroup.InstanceID="G1MikeNS1"']},
                     'ASSOC':
                        {'TST_Group': [],
                         'TST_Person': ['/ns2:TST_Group.name="ns2group1"']}},
                'ns2':
                    {'ENUM':
                        {'TST_Person': [],
                         'TST_Group': ['/ns2:TST_Group.name="ns2group1"'],
                         'TST_MemberOfGroup':
                             ['/ns2:TST_MemberOfGroup.InstanceID="G1MikeNS1"']},
                     'REF':
                        {'TST_Group':
                            ['/ns2:TST_MemberOfGroup.InstanceID="G1MikeNS1"']},
                     'ASSOC':
                        {'TST_Person': [],
                         'TST_Group': ['/ns1:TST_Person.name="Mike"']}}
            },
        ),
        None, None, OK
    ),

    (
        "Test association cross namespaces with MemberOfGroup delete from "
        "alternate namespace",
        dict(
            # first namespace becomes the default namespace
            namespaces=['ns1', 'ns2'],
            class_mof=[TST_CLASSES_MOF],
            inst_mof=[INSTANCE_INITIAL_ENDPOINTS],
            assoc_inst_mof=[ASSOCIATION_MOF_CROSS_NS],
            source_clns=['TST_Person', 'TST_Group'],
            assoc_clns='TST_MemberOfGroup',
            delete_ns='ns2',
            exp_rtn={
                'ns1':
                    {'ENUM':
                        {'TST_Person': ['/ns1:TST_Person.name="Mike"'],
                         'TST_Group': [],
                         'TST_MemberOfGroup':
                             ['/ns1:TST_MemberOfGroup.InstanceID="G1MikeNS1"']},
                     'REF':
                        {'TST_Person':
                             ['/ns1:TST_MemberOfGroup.InstanceID="G1MikeNS1"']},
                     'ASSOC':
                        {'TST_Group': [],
                         'TST_Person': ['/ns2:TST_Group.name="ns2group1"']}},
                'ns2':
                    {'ENUM':
                        {'TST_Person': [],
                         'TST_Group': ['/ns2:TST_Group.name="ns2group1"'],
                         'TST_MemberOfGroup':
                             ['/ns2:TST_MemberOfGroup.InstanceID="G1MikeNS1"']},
                     'REF':
                        {'TST_Group':
                            ['/ns2:TST_MemberOfGroup.InstanceID="G1MikeNS1"']},
                     'ASSOC':
                        {'TST_Person': [],
                         'TST_Group': ['/ns1:TST_Person.name="Mike"']}}
            },
        ),
        None, None, OK
    ),

    (
        "Test association TST_MemberOfGroupNoID (refs as keys) cross ns",
        dict(
            # first namespace becomes the default namespace
            namespaces=['ns1', 'ns2'],
            class_mof=[TST_CLASSES_MOF],
            inst_mof=[INSTANCE_INITIAL_ENDPOINTS],
            assoc_inst_mof=[ASSOCNOID_MOF_CROSS_NS],
            source_clns=['TST_Person', 'TST_Group'],
            assoc_clns='TST_MemberOfGroupNoID',
            delete_ns=None,
            exp_rtn={
                'ns1':
                    {'ENUM':
                        {'TST_Person': ['/ns1:TST_Person.name="Mike"'],
                         'TST_Group': [],
                         'TST_MemberOfGroupNoID': [MEMBEROFGROUPNOIDNS1]},
                     'REF':
                        {'TST_Person': [MEMBEROFGROUPNOIDNS1]},
                     'ASSOC':
                        {'TST_Group': [],
                         'TST_Person': ['/ns2:TST_Group.name="ns2group1"']}},
                'ns2':
                    {'ENUM':
                        {'TST_Person': [],
                         'TST_Group': ['/ns2:TST_Group.name="ns2group1"'],
                         'TST_MemberOfGroupNoID': [MEMBEROFGROUPNOIDNS2]},
                     'REF':
                        {'TST_Group': [MEMBEROFGROUPNOIDNS2]},
                     'ASSOC':
                        {'TST_Person': [],
                         'TST_Group': ['/ns1:TST_Person.name="Mike"']}}
            },
        ),
        None, None, OK
    ),

    (
        "Test 3way association TST_MemberOfGroup3EP cross  3 namespaces",
        dict(
            # first namespace becomes the default namespace
            namespaces=['ns1', 'ns2', 'ns3'],
            class_mof=[TST_CLASSES_MOF],
            inst_mof=[INSTANCE_INITIAL_ENDPOINTS],
            assoc_inst_mof=[ASSOCIATIONX_3WAY_MOF_CROSS_NS],
            source_clns=['TST_Person', 'TST_Group', 'TST_THIRD_EP'],
            assoc_clns='TST_MemberOfGroup3EP',
            delete_ns='ns1',
            exp_rtn={
                'ns1':
                    {'ENUM':
                        {'TST_Person': ['/ns1:TST_Person.name="Mike"'],
                         'TST_Group': [],
                         'TST_THIRD_EP': [],
                         'TST_MemberOfGroup3EP':
                             ['/ns1:TST_MemberOfGroup3EP.InstanceID='
                              '"G1MikeAxNs3"']},
                     'REF':
                        {'TST_Person':
                            ['/ns1:TST_MemberOfGroup3EP.InstanceID='
                             '"G1MikeAxNs3"']},
                     'ASSOC':
                        {'TST_Person': ['/ns2:TST_Group.name="ns2group1"',
                                        '/ns3:TST_THIRD_EP.name="ns3X1"'],
                         'TST_Group': [],
                         'TST_THIRD_EP': []}},
                'ns2':
                    {'ENUM':
                        {'TST_Person': [],
                         'TST_Group': ['/ns2:TST_Group.name="ns2group1"'],
                         "TST_THIRD_EP": [],
                         'TST_MemberOfGroup3EP':
                             ['/ns2:TST_MemberOfGroup3EP.InstanceID='
                              '"G1MikeAxNs3"']},
                     'REF':
                        {'TST_Group':
                            ['/ns1:TST_MemberOfGroup3EP.InstanceID='
                             '"G1MikeAxNs3"']},
                     'ASSOC':
                        {'TST_Person': [],
                         'TST_Group': ['/ns1:TST_Person.name="Mike"',
                                       '/ns3:TST_THIRD_EP.name="ns3X1"'],
                         'TST_THIRD_EP': []}},
                'ns3':
                    {'ENUM':
                        {'TST_Person': [],
                         'TST_Group': [],
                         'TST_THIRD_EP': ['/ns3:TST_THIRD_EP.name="ns3X1"'],
                         'TST_MemberOfGroup3EP':
                             ['/ns3:TST_MemberOfGroup3EP.InstanceID='
                              '"G1MikeAxNs3"']},
                     'REF':
                        {'TST_Group':
                            ['/ns2:TST_MemberOfGroup3EP.InstanceID='
                             '"G1MikeNS1"']},
                     'ASSOC':
                        {'TST_Person': [],
                         'TST_Group': [],
                         'TST_THIRD_EP': ['/ns1:TST_Person.name="Mike"',
                                          '/ns2:TST_Group.name="ns2group1"']}},
            },
        ),
        None, None, OK
    ),

    # TODO: Needs the following tests.
    #  Test with other instances and more associations in the test
    #  Lower priority:
    #    Test 3 way association.

]
# pylint: enable=bad-continuation

# Disabled because it is unhappy with indentation of multilevel dictionary
# lower levels.  Note that this occurs with minimum version tests but not with
# latest version tests


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_MULTI_NAMESPACES)
@simplified_test_function
def test_multiple_namespace_assoc(testcase, namespaces, class_mof, inst_mof,
                                  assoc_inst_mof, source_clns, assoc_clns,
                                  delete_ns, exp_rtn):
    # pylint: disable=unused-argument
    """
    Test the creation and deletion of instances of association that cross
    namespaces.
    """
    conn = FakedWBEMConnection(default_namespace=namespaces[0])

    # Create the repository from test components.  Creates qualdecls,
    # classes, endpoint instances, association instances in multiple
    # namespaces
    create_repository(conn, namespaces, class_mof, inst_mof, assoc_inst_mof)

    assert len(namespaces) == len(exp_rtn)

    # Create list of all classes for enumeration test. Note: This
    # creates a new list.  list() forces create of new object
    enum_clns = list(source_clns)
    enum_clns.append(assoc_clns)

    # Test that the creation of instances was correct.
    validate_instance_enumeration(conn, namespaces, enum_clns, exp_rtn)

    validate_instance_associations(conn, namespaces, source_clns, exp_rtn)

    # Test delete of association instances

    # delete the instance names of the associations in namespace defined by
    # delete_ns.  This should delete each of these associations in each
    # namespace
    deleted_assocs = []
    if delete_ns:
        ns = delete_ns
        inst_names = conn.EnumerateInstanceNames(assoc_clns, namespace=ns)
        for inst_name in inst_names:
            _ = conn.GetInstance(inst_name)
            conn.DeleteInstance(inst_name)
            deleted_assocs.append(inst_name)

        # Confirm inst_name deleted in all namespaces
        for namespace in namespaces:
            for assoc_name in deleted_assocs:
                try:
                    assoc_name.namespace = namespace
                    conn.GetInstance(assoc_name)
                    assert False, _format(
                        "Instance {} should not exist in ns {} after delete",
                        assoc_name, namespace)
                except CIMError as ce:
                    assert ce.status_code == CIM_ERR_NOT_FOUND


# pylint: disable=bad-continuation

TESTCASES_MULTI_NAMESPACES_ERRORS = [
    # Each list item is a testcase tuple with these items:
    # * desc: Short testcase description.
    # * kwargs: Keyword arguments for the test function:
    #   * namespaces - List of namespaces in mock environment
    #   * class_mof - list of strings containing qualdecl and class mof to
    #     be compiled
    #   * classes to remove from namespaces (dict <ns>: [<class names>]) before
    #     attempting to compile instances.
    #   * inst_mof - list of strings containing instance mof to be compiled
    #   * assoc_inst_mof
    #   * assoc_inst_obj - Instance definition in python. Used to create
    #     invalid instances
    #   * src_clns -
    #   * assoc_clns -
    #   * delete_ns -
    #   * exp_rtn -
    # * exp_exc_types: Expected exception type(s), or None.
    # * exp_warn_types: Expected warning type(s), or None.
    # * condition: Boolean condition for testcase to run, or 'pdb' for
    #   debugger

    (
        "Test fails with assoc class missing from second namespace",
        dict(
            # first namespace becomes the default namespace
            namespaces=['ns1', 'ns2'],
            class_mof=[TST_CLASSES_MOF],
            remove_classes={'ns2': ['TST_MemberOfGroup']},
            inst_mof=[INSTANCE_INITIAL_ENDPOINTS],
            assoc_inst_mof=[ASSOCIATION_MOF_CROSS_NS],
            assoc_inst_obj=None,
            source_clns=['TST_Person', 'TST_Group'],
            assoc_clns='TST_MemberOfGroupNoID',
            delete_ns=None,
            exp_rtn=None
        ),
        MOFRepositoryError, None, OK
    ),

    (
        "Test fails,assoc instance already exists",
        dict(
            # first namespace becomes the default namespace
            namespaces=['ns1', 'ns2'],
            class_mof=[TST_CLASSES_MOF],
            remove_classes={'ns2': ['TST_MemberOfGroup']},
            inst_mof=[INSTANCE_INITIAL_ENDPOINTS],
            assoc_inst_mof=[ASSOCIATION_MOF_CROSS_NS],
            assoc_inst_obj=None,
            source_clns=['TST_Person', 'TST_Group'],
            assoc_clns='TST_MemberOfGroupNoID',
            delete_ns=None,
            exp_rtn=None
        ),
        MOFRepositoryError, None, OK
    ),

    (
        "Test  bad end-points paths (do not exist) fails",
        dict(
            namespaces=['ns1', 'ns2'],
            class_mof=[TST_CLASSES_MOF],
            remove_classes={'ns2': ['TST_MemberOfGroup']},
            inst_mof=[INSTANCE_INITIAL_ENDPOINTS],
            assoc_inst_mof=[],
            # Association instance with  invalid reference properties
            assoc_inst_obj=CIMInstance(
                'TST_MemberOfGroup',
                path=CIMInstanceName(
                    "TST_MemberOfGroup", keybindings=dict(InstanceID="blah"),
                    namespace='ns1'),
                properties=dict(
                    InstanceID=CIMProperty("InstanceID", "blah"),
                    member=CIMProperty(
                        "member",
                        CIMInstanceName('TST_PERSON',
                                        keybindings=dict(name="fred"),
                                        namespace='ns1')),
                    group=CIMProperty(
                        'group',
                        CIMInstanceName('TST_Group',
                                        keybindings=dict(name="john"),
                                        namespace='ns2')))),
            source_clns=['TST_Person', 'TST_Group'],
            assoc_clns='TST_MemberOfGroup',
            delete_ns=None,
            exp_rtn=None
        ),
        CIMError, None, OK
    ),

    (
        "Test  bad 2nd end-point path (instance does not exist) fails",
        dict(
            namespaces=['ns1', 'ns2'],
            class_mof=[TST_CLASSES_MOF],
            remove_classes={'ns2': ['TST_MemberOfGroup']},
            inst_mof=[INSTANCE_INITIAL_ENDPOINTS],
            assoc_inst_mof=[],
            # Association instance with  invalid reference properties
            assoc_inst_obj=CIMInstance(
                'TST_MemberOfGroup',
                path=CIMInstanceName(
                    "TST_MemberOfGroup", keybindings=dict(InstanceID="blah"),
                    namespace='ns1'),
                properties=dict(
                    InstanceID=CIMProperty("InstanceID", "blah"),
                    member=CIMProperty(
                        "member",
                        CIMInstanceName('TST_PERSON',
                                        keybindings=dict(name="Mike"),
                                        namespace='ns1')),
                    group=CIMProperty(
                        'group',
                        CIMInstanceName('TST_Group',
                                        keybindings=dict(name="john"),
                                        namespace='ns2')))),
            source_clns=['TST_Person', 'TST_Group'],
            assoc_clns='TST_MemberOfGroup',
            delete_ns=None,
            exp_rtn=None
        ),
        CIMError, None, OK
    ),

    (
        "Test bad 2nd end-point path  namespace does not exist) fails",
        dict(
            namespaces=['ns1', 'ns2'],
            class_mof=[TST_CLASSES_MOF],
            remove_classes={'ns2': ['TST_MemberOfGroup']},
            inst_mof=[INSTANCE_INITIAL_ENDPOINTS],
            assoc_inst_mof=[],
            # Association instance with  invalid reference properties
            assoc_inst_obj=CIMInstance(
                'TST_MemberOfGroup',
                path=CIMInstanceName(
                    "TST_MemberOfGroup", keybindings=dict(InstanceID="blah"),
                    namespace='ns1'),
                properties=dict(
                    InstanceID=CIMProperty("InstanceID", "blah"),
                    member=CIMProperty(
                        "member",
                        CIMInstanceName('TST_PERSON',
                                        keybindings=dict(name="Mike"),
                                        namespace='ns1')),
                    group=CIMProperty(
                        'group',
                        CIMInstanceName('TST_Group',
                                        keybindings=dict(name="ns2group1"),
                                        namespace='InvalidNS')))),
            source_clns=['TST_Person', 'TST_Group'],
            assoc_clns='TST_MemberOfGroup',
            delete_ns=None,
            exp_rtn=None
        ),
        CIMError, None, OK
    ),


    #  Test fail mode, Create assoc instance where instance already exists.
    #  Test fail mode where on create assoc instance exists already in
    #  second namespace

]
# pylint: enable=bad-continuation


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_MULTI_NAMESPACES_ERRORS)
@simplified_test_function
def test_multiple_namespace_assoc_errs(testcase, namespaces, class_mof,
                                       remove_classes, inst_mof,
                                       assoc_inst_mof, assoc_inst_obj,
                                       source_clns, assoc_clns,
                                       delete_ns, exp_rtn):

    # pylint: disable=unused-argument
    """
    Test the creation and deletion of instances of association that cross
    namespaces.
    """
    conn = FakedWBEMConnection(default_namespace=namespaces[0])

    # Create namespaces
    for ns in namespaces:
        if ns not in conn.namespaces:
            conn.add_namespace(ns)

    skip_if_moftab_regenerated()

    # Compile the class mof in all namespaces
    for ns in namespaces:
        for mof in class_mof:
            conn.compile_mof_string(mof, ns)

    # Delete classes defined by remove_classes to set up compile failures
    for ns, clns in remove_classes.items():
        for cln in clns:
            conn.DeleteClass(cln, ns)

    # Compile all instance mof together to utilize compiler alias capability
    # each of the components is a list.
    all_inst_mof = "\n".join(inst_mof) + "\n".join(assoc_inst_mof)

    conn.compile_mof_string(all_inst_mof, verbose=VERBOSE)

    # Create list of all classes for enumeration test. Note: This
    # creates a new list.
    enum_clns = list(source_clns)
    enum_clns.append(assoc_clns)

    # Create instance defined by assoc_inst_obj.
    if assoc_inst_obj:
        conn.CreateInstance(assoc_inst_obj)

    # Test that the creation of instances was correct.
    for ns in namespaces:
        # Test EnumerateInstanceNames for all classes in enumeration
        for tst_cln in enum_clns:
            inst_paths = conn.EnumerateInstanceNames(tst_cln, namespace=ns)
            val_act_exp_paths(inst_paths, exp_rtn, ns, 'ENUM', tst_cln)

        # Test References and Associators for each classname in source_clns
        for source_cln in source_clns:
            # Test only if there is an instance of source_cln
            if conn.EnumerateInstances(source_cln):
                source_paths = conn.EnumerateInstanceNames(source_cln,
                                                           namespace=ns)

                for source_path in source_paths:
                    # Compare ..Names requests
                    inst_paths = conn.ReferenceNames(source_path)
                    val_act_exp_paths(inst_paths, exp_rtn, ns, 'REF',
                                      source_cln)
                    inst_paths = conn.AssociatorNames(source_path)
                    val_act_exp_paths(inst_paths, exp_rtn, ns, 'ASSOC',
                                      source_cln)

                    # Compare paths of References returns
                    insts = conn.References(source_path)
                    # Validate path and reference property same values
                    for inst in insts:
                        keys = inst.path.keybindings
                        for prop in inst.properties.values():
                            if prop.type == 'references':
                                if prop.name in keys:
                                    assert prop.value == keys[prop.name]
                    inst_paths = [i.path for i in insts]
                    val_act_exp_paths(inst_paths, exp_rtn, ns, 'REF',
                                      source_cln)

                    # Compare paths of Associator returns
                    insts = conn.Associators(source_path)
                    inst_paths = [r.path for r in insts]
                    val_act_exp_paths(inst_paths, exp_rtn, ns, 'ASSOC',
                                      source_cln)


# pylint: disable=bad-continuation

TESTCASES_MULTI_NAMESPACES_MODIFY_INSTANCE = [
    # Each list item is a testcase tuple with these items:
    # * desc: Short testcase description.
    # * kwargs: Keyword arguments for the test function:
    #   * namespaces - List of namespaces in mock environment
    #   * class_mof - list of strings containing qualdecl and class mof to
    #     be compiled
    #   * inst_mof - list of strings containing instance mof to be compiled.
    #     These are the endpoint instances to be installed in ns1
    #   * assoc_inst_mof - list of strings  containing instances defining
    #     associations and other endpoints to be compiled. These strings must
    #     define the namespace for components that are not in the ns1 namespace.
    #   * source classnames for ENUM, REF, ASSOC tests - The classnames that
    #     are the source classes for these operations
    #   * assoc_clns - The classname of the reference class being tested
    #   * delete_ns - If not None, defnes namespace from which association
    #     is deleted in delete test.  If None, deleted from creation ns.
    #   * property_mods - If None defines a set of modifications to properties
    #     of an instance defined in a tuple where item 0 is the path to the
    #     instance to modify and item 1 is is a tuple with either:
    #     * one or more tuples where each tuple defines the property name and
    #       new value for the modification.
    #     * a CIMProperty that defines the name, type and value of the
    #       replacement property value.
    #     Prop_list to be passed to ModifyInstance. None, modify all properties
    #     defined as different (see property_mods), list of strings, modify
    #     only properties in the list, empty list, modify no properties.
    #   * del_assoc_instance_test: defines instance path of one assoc instance
    #     to delete (one of the shadowed instances) to test modify when
    #     shadow insts not complete.
    #   * exp_rtn: dictionary containing expected return objects (primarily
    #     CIMInstanceNames). The dictionary is defined as
    #     {<namespace>: <operation>: <source_class>: list of results instance
    #     names.
    # * exp_exc_types: Expected exception type(s), or None.
    # * exp_warn_types: Expected warning type(s), or None.
    # * condition: Boolean condition for testcase to run, or 'pdb' for
    #   debugger

    (
        "Test association Modify in one namespace. Modify ExtraPropStr prop",
        dict(
            # first namespace becomes the default namespace
            namespaces=['ns1', 'ns2'],
            class_mof=[TST_CLASSES_MOF],
            inst_mof=[INSTANCE_INITIAL_ENDPOINTS],
            assoc_inst_mof=[ASSOCIATION_MOF_SAME_NS],
            source_clns=['TST_Person', 'TST_Group'],
            assoc_clns='TST_MemberOfGroup',
            property_mods=('/ns1:TST_MemberOfGroup.InstanceID="G1MikeNS1"',
                           (("ExtraPropStr", "NewStringVal"),)),
            prop_list=None,
            delete_ns='ns1',
            delete_assoc_inst_test=None,
            exp_rtn={
                'ns1':
                    {'ENUM':
                        {'TST_Person': ['/ns1:TST_Person.name="Mike"'],
                         'TST_Group': ['/ns1:TST_Group.name="ns1group1"'],
                         'TST_MemberOfGroup':
                             ['/ns1:TST_MemberOfGroup.InstanceID="G1MikeNS1"']},
                     'REF':
                        {'TST_Person':
                             ['/ns1:TST_MemberOfGroup.InstanceID="G1MikeNS1"'],
                         'TST_Group':
                             ['/ns1:TST_MemberOfGroup.InstanceID="G1MikeNS1"']},
                     'ASSOC':
                        {'TST_Group': ['/ns1:TST_Person.name="Mike"'],
                         'TST_Person': ['/ns1:TST_Group.name="ns1group1"']}, },
                'ns2':
                    {'ENUM':
                        {'TST_Person': [],
                         'TST_Group': [],
                         'TST_MemberOfGroup': []},
                     'REF':
                        {'TST_Person': []},
                     'ASSOC':
                        {'TST_Person': [],
                         'TST_Group': []}, },
            },
        ),
        None, None, OK
    ),

    (
        "Test association modify cross namespaces with MemberOfGroup. No prop "
        "values in instance",
        dict(
            # first namespace becomes the default namespace
            namespaces=['ns1', 'ns2'],
            class_mof=[TST_CLASSES_MOF],
            inst_mof=[INSTANCE_INITIAL_ENDPOINTS],
            assoc_inst_mof=[ASSOCIATION_MOF_CROSS_NS_NO_EXTRAPROPS],
            source_clns=['TST_Person', 'TST_Group'],
            assoc_clns='TST_MemberOfGroup',
            property_mods=('/ns1:TST_MemberOfGroup.InstanceID="G1MikeNS1"',
                           (("ExtraPropStr", "NewStringVal"),
                            ("ExtraPropInt", Uint32(88888)))),
            prop_list=None,
            delete_ns='ns1',
            delete_assoc_inst_test=None,
            exp_rtn={
                'ns1':
                    {'ENUM':
                        {'TST_Person': ['/ns1:TST_Person.name="Mike"'],
                         'TST_Group': [],
                         'TST_MemberOfGroup':
                             ['/ns1:TST_MemberOfGroup.InstanceID="G1MikeNS1"']},
                     'REF':
                        {'TST_Person':
                             ['/ns1:TST_MemberOfGroup.InstanceID="G1MikeNS1"']},
                     'ASSOC':
                        {'TST_Group': [],
                         'TST_Person': ['/ns2:TST_Group.name="ns2group1"']}},
                'ns2':
                    {'ENUM':
                        {'TST_Person': [],
                         'TST_Group': ['/ns2:TST_Group.name="ns2group1"'],
                         'TST_MemberOfGroup':
                             ['/ns2:TST_MemberOfGroup.InstanceID="G1MikeNS1"']},
                     'REF':
                        {'TST_Group':
                            ['/ns2:TST_MemberOfGroup.InstanceID="G1MikeNS1"']},
                     'ASSOC':
                        {'TST_Person': [],
                         'TST_Group': ['/ns1:TST_Person.name="Mike"']}}
            },
        ),
        None, None, OK
    ),

    (
        "Test association modify cross namespaces with MemberOfGroup modifiy 2 "
        "properties",
        dict(
            # first namespace becomes the default namespace
            namespaces=['ns1', 'ns2'],
            class_mof=[TST_CLASSES_MOF],
            inst_mof=[INSTANCE_INITIAL_ENDPOINTS],
            assoc_inst_mof=[ASSOCIATION_MOF_CROSS_NS],
            source_clns=['TST_Person', 'TST_Group'],
            assoc_clns='TST_MemberOfGroup',
            property_mods=('/ns1:TST_MemberOfGroup.InstanceID="G1MikeNS1"',
                           (("ExtraPropStr", "NewStringVal"),
                            ("ExtraPropInt", Uint32(88888)))),
            prop_list=None,
            delete_ns='ns1',
            delete_assoc_inst_test=None,
            exp_rtn={
                'ns1':
                    {'ENUM':
                        {'TST_Person': ['/ns1:TST_Person.name="Mike"'],
                         'TST_Group': [],
                         'TST_MemberOfGroup':
                             ['/ns1:TST_MemberOfGroup.InstanceID="G1MikeNS1"']},
                     'REF':
                        {'TST_Person':
                             ['/ns1:TST_MemberOfGroup.InstanceID="G1MikeNS1"']},
                     'ASSOC':
                        {'TST_Group': [],
                         'TST_Person': ['/ns2:TST_Group.name="ns2group1"']}},
                'ns2':
                    {'ENUM':
                        {'TST_Person': [],
                         'TST_Group': ['/ns2:TST_Group.name="ns2group1"'],
                         'TST_MemberOfGroup':
                             ['/ns2:TST_MemberOfGroup.InstanceID="G1MikeNS1"']},
                     'REF':
                        {'TST_Group':
                            ['/ns2:TST_MemberOfGroup.InstanceID="G1MikeNS1"']},
                     'ASSOC':
                        {'TST_Person': [],
                         'TST_Group': ['/ns1:TST_Person.name="Mike"']}}
            },
        ),
        None, None, OK
    ),

    (
        "Test association modify cross namespaces with MemberOfGroup mod 2 prop"
        " and property list with both properties",
        dict(
            # first namespace becomes the default namespace
            namespaces=['ns1', 'ns2'],
            class_mof=[TST_CLASSES_MOF],
            inst_mof=[INSTANCE_INITIAL_ENDPOINTS],
            assoc_inst_mof=[ASSOCIATION_MOF_CROSS_NS],
            source_clns=['TST_Person', 'TST_Group'],
            assoc_clns='TST_MemberOfGroup',
            property_mods=('/ns1:TST_MemberOfGroup.InstanceID="G1MikeNS1"',
                           (("ExtraPropStr", "NewStringVal"),
                            ("ExtraPropInt", Uint32(88888)))),
            prop_list=["ExtraPropStr", "ExtraPropInt"],
            delete_ns='ns1',
            delete_assoc_inst_test=None,
            exp_rtn={
                'ns1':
                    {'ENUM':
                        {'TST_Person': ['/ns1:TST_Person.name="Mike"'],
                         'TST_Group': [],
                         'TST_MemberOfGroup':
                             ['/ns1:TST_MemberOfGroup.InstanceID="G1MikeNS1"']},
                     'REF':
                        {'TST_Person':
                             ['/ns1:TST_MemberOfGroup.InstanceID="G1MikeNS1"']},
                     'ASSOC':
                        {'TST_Group': [],
                         'TST_Person': ['/ns2:TST_Group.name="ns2group1"']}},
                'ns2':
                    {'ENUM':
                        {'TST_Person': [],
                         'TST_Group': ['/ns2:TST_Group.name="ns2group1"'],
                         'TST_MemberOfGroup':
                             ['/ns2:TST_MemberOfGroup.InstanceID="G1MikeNS1"']},
                     'REF':
                        {'TST_Group':
                            ['/ns2:TST_MemberOfGroup.InstanceID="G1MikeNS1"']},
                     'ASSOC':
                        {'TST_Person': [],
                         'TST_Group': ['/ns1:TST_Person.name="Mike"']}}
            },
        ),
        None, None, OK
    ),


    (
        "Test association modify cross namespaces with MemberOfGroup delete "
        "from alternate namespace",
        dict(
            # first namespace becomes the default namespace
            namespaces=['ns1', 'ns2'],
            class_mof=[TST_CLASSES_MOF],
            inst_mof=[INSTANCE_INITIAL_ENDPOINTS],
            assoc_inst_mof=[ASSOCIATION_MOF_CROSS_NS],
            source_clns=['TST_Person', 'TST_Group'],
            assoc_clns='TST_MemberOfGroup',
            property_mods=('/ns1:TST_MemberOfGroup.InstanceID="G1MikeNS1"',
                           (("ExtraPropStr", "NewStringVal"),)),
            prop_list=None,
            delete_ns='ns2',
            delete_assoc_inst_test=None,
            exp_rtn={
                'ns1':
                    {'ENUM':
                        {'TST_Person': ['/ns1:TST_Person.name="Mike"'],
                         'TST_Group': [],
                         'TST_MemberOfGroup':
                             ['/ns1:TST_MemberOfGroup.InstanceID="G1MikeNS1"']},
                     'REF':
                        {'TST_Person':
                             ['/ns1:TST_MemberOfGroup.InstanceID="G1MikeNS1"']},
                     'ASSOC':
                        {'TST_Group': [],
                         'TST_Person': ['/ns2:TST_Group.name="ns2group1"']}},
                'ns2':
                    {'ENUM':
                        {'TST_Person': [],
                         'TST_Group': ['/ns2:TST_Group.name="ns2group1"'],
                         'TST_MemberOfGroup':
                             ['/ns2:TST_MemberOfGroup.InstanceID="G1MikeNS1"']},
                     'REF':
                        {'TST_Group':
                            ['/ns2:TST_MemberOfGroup.InstanceID="G1MikeNS1"']},
                     'ASSOC':
                        {'TST_Person': [],
                         'TST_Group': ['/ns1:TST_Person.name="Mike"']}}
            },
        ),
        None, None, OK
    ),

    (
        "Test association modify TST_MemberOfGroupNoID (refs as keys) cross ns",
        dict(
            # first namespace becomes the default namespace
            namespaces=['ns1', 'ns2'],
            class_mof=[TST_CLASSES_MOF],
            inst_mof=[INSTANCE_INITIAL_ENDPOINTS],
            assoc_inst_mof=[ASSOCNOID_MOF_CROSS_NS],
            source_clns=['TST_Person', 'TST_Group'],
            assoc_clns='TST_MemberOfGroupNoID',
            property_mods=(MEMBEROFGROUPNOIDNS1,
                           (("ExtraPropStr", "NewStringVal"),)),
            prop_list=None,
            delete_ns='ns1',
            delete_assoc_inst_test=None,
            exp_rtn={
                'ns1':
                    {'ENUM':
                        {'TST_Person': ['/ns1:TST_Person.name="Mike"'],
                         'TST_Group': [],
                         'TST_MemberOfGroupNoID':
                             [MEMBEROFGROUPNOIDNS1]},
                     'REF':
                        {'TST_Person':
                             [MEMBEROFGROUPNOIDNS1]},
                     'ASSOC':
                        {'TST_Group': [],
                         'TST_Person': ['/ns2:TST_Group.name="ns2group1"']}},
                'ns2':
                    {'ENUM':
                        {'TST_Person': [],
                         'TST_Group': ['/ns2:TST_Group.name="ns2group1"'],
                         'TST_MemberOfGroupNoID':
                             [MEMBEROFGROUPNOIDNS2]},
                     'REF':
                        {'TST_Group':
                            [MEMBEROFGROUPNOIDNS2]},
                     'ASSOC':
                        {'TST_Person': [],
                         'TST_Group': ['/ns1:TST_Person.name="Mike"']}}
            },
        ),
        None, None, OK
    ),

    (
        "Test 3way association modify TST_MemberOfGroup3EP cross  3 namespaces",
        dict(
            # first namespace becomes the default namespace
            namespaces=['ns1', 'ns2', 'ns3'],
            class_mof=[TST_CLASSES_MOF],
            inst_mof=[INSTANCE_INITIAL_ENDPOINTS],
            assoc_inst_mof=[ASSOCIATIONX_3WAY_MOF_CROSS_NS],
            source_clns=['TST_Person', 'TST_Group', 'TST_THIRD_EP'],
            assoc_clns='TST_MemberOfGroup3EP',
            property_mods=('/ns1:TST_MemberOfGroup3EP.InstanceID="G1MikeAxNs3"',
                           (("ExtraPropStr", "NewStringVal"),)),
            prop_list=None,
            delete_ns='ns1',
            delete_assoc_inst_test=None,
            exp_rtn={
                'ns1':
                    {'ENUM':
                        {'TST_Person': ['/ns1:TST_Person.name="Mike"'],
                         'TST_Group': [],
                         'TST_THIRD_EP': [],
                         'TST_MemberOfGroup3EP':
                             ['/ns1:TST_MemberOfGroup3EP.InstanceID='
                              '"G1MikeAxNs3"']},
                     'REF':
                        {'TST_Person':
                            ['/ns1:TST_MemberOfGroup3EP.InstanceID='
                             '"G1MikeAxNs3"']},
                     'ASSOC':
                        {'TST_Person': ['/ns2:TST_Group.name="ns2group1"',
                                        '/ns3:TST_THIRD_EP.name="ns3X1"'],
                         'TST_Group': [],
                         'TST_THIRD_EP': []}},
                'ns2':
                    {'ENUM':
                        {'TST_Person': [],
                         'TST_Group': ['/ns2:TST_Group.name="ns2group1"'],
                         "TST_THIRD_EP": [],
                         'TST_MemberOfGroup3EP':
                             ['/ns2:TST_MemberOfGroup3EP.InstanceID='
                              '"G1MikeAxNs3"']},
                     'REF':
                        {'TST_Group':
                            ['/ns1:TST_MemberOfGroup3EP.InstanceID='
                             '"G1MikeAxNs3"']},
                     'ASSOC':
                        {'TST_Person': [],
                         'TST_Group': ['/ns1:TST_Person.name="Mike"',
                                       '/ns3:TST_THIRD_EP.name="ns3X1"'],
                         'TST_THIRD_EP': []}},
                'ns3':
                    {'ENUM':
                        {'TST_Person': [],
                         'TST_Group': [],
                         'TST_THIRD_EP': ['/ns3:TST_THIRD_EP.name="ns3X1"'],
                         'TST_MemberOfGroup3EP':
                             ['/ns3:TST_MemberOfGroup3EP.InstanceID='
                              '"G1MikeAxNs3"']},
                     'REF':
                        {'TST_Group':
                            ['/ns2:TST_MemberOfGroup3EP.InstanceID='
                             '"G1MikeAxNS1"']},
                     'ASSOC':
                        {'TST_Person': [],
                         'TST_Group': [],
                         'TST_THIRD_EP': ['/ns1:TST_Person.name="Mike"',
                                          '/ns2:TST_Group.name="ns2group1"']}},
            },
        ),
        None, None, OK
    ),

    (
        "Test association modify cross namespaces with MemberOfGroup and"
        "ref prop modification",
        dict(
            # first namespace becomes the default namespace
            namespaces=['ns1', 'ns2'],
            class_mof=[TST_CLASSES_MOF],
            inst_mof=[INSTANCE_INITIAL_ENDPOINTS],
            assoc_inst_mof=[ASSOCIATION_MOF_CROSS_NS],
            source_clns=['TST_Person', 'TST_Group'],
            assoc_clns='TST_MemberOfGroup',
            property_mods=(
                '/ns1:TST_MemberOfGroup.InstanceID="G1MikeNS1"',
                # Modify group reference property
                (("group", CIMInstanceName("TST_Group", namespace='ns2',
                                           keybindings={"name":
                                                        "NotExist"})), )),
            prop_list=None,
            delete_ns='ns1',
            delete_assoc_inst_test=None,
            exp_rtn={
                'ns1':
                    {'ENUM':
                        {'TST_Person': ['/ns1:TST_Person.name="Mike"'],
                         'TST_Group': [],
                         'TST_MemberOfGroup':
                             ['/ns1:TST_MemberOfGroup.InstanceID="G1MikeNS1"']},
                     'REF':
                        {'TST_Person':
                             ['/ns1:TST_MemberOfGroup.InstanceID="G1MikeNS1"']},
                     'ASSOC':
                        {'TST_Group': [],
                         'TST_Person': ['/ns2:TST_Group.name="ns2group1"']}},
                'ns2':
                    {'ENUM':
                        {'TST_Person': [],
                         'TST_Group': ['/ns2:TST_Group.name="ns2group1"'],
                         'TST_MemberOfGroup':
                             ['/ns2:TST_MemberOfGroup.InstanceID="G1MikeNS1"']},
                     'REF':
                        {'TST_Group':
                            ['/ns2:TST_MemberOfGroup.InstanceID="G1MikeNS1"']},
                     'ASSOC':
                        {'TST_Person': [],
                         'TST_Group': ['/ns1:TST_Person.name="Mike"']}}
            },
        ),
        CIMError, None, OK
    ),

    (
        "Test association modify cross namespaces with a shadow assoc inst "
        "missing",
        dict(
            # first namespace becomes the default namespace
            namespaces=['ns1', 'ns2'],
            class_mof=[TST_CLASSES_MOF],
            inst_mof=[INSTANCE_INITIAL_ENDPOINTS],
            assoc_inst_mof=[ASSOCIATION_MOF_CROSS_NS],
            source_clns=['TST_Person', 'TST_Group'],
            assoc_clns='TST_MemberOfGroup',
            property_mods=('/ns1:TST_MemberOfGroup.InstanceID="G1MikeNS1"',
                           ((CIMProperty("member", type="reference",
                                         value=None),))),
            prop_list=None,
            delete_ns='ns1',
            delete_assoc_inst_test=None,
            exp_rtn={
                'ns1':
                    {'ENUM':
                        {'TST_Person': ['/ns1:TST_Person.name="Mike"'],
                         'TST_Group': [],
                         'TST_MemberOfGroup':
                             ['/ns1:TST_MemberOfGroup.InstanceID="G1MikeNS1"']},
                     'REF':
                        {'TST_Person':
                             ['/ns1:TST_MemberOfGroup.InstanceID="G1MikeNS1"']},
                     'ASSOC':
                        {'TST_Group': [],
                         'TST_Person': ['/ns2:TST_Group.name="ns2group1"']}},
                'ns2':
                    {'ENUM':
                        {'TST_Person': [],
                         'TST_Group': ['/ns2:TST_Group.name="ns2group1"'],
                         'TST_MemberOfGroup':
                             ['/ns2:TST_MemberOfGroup.InstanceID="G1MikeNS1"']},
                     'REF':
                        {'TST_Group':
                            ['/ns2:TST_MemberOfGroup.InstanceID="G1MikeNS1"']},
                     'ASSOC':
                        {'TST_Person': [],
                         'TST_Group': ['/ns1:TST_Person.name="Mike"']}}
            },
        ),
        CIMError, None, OK
    ),

    (
        "Test association modify cross namespaces with MemberOfGroup mod "
        "ref to Null",
        dict(
            # first namespace becomes the default namespace
            namespaces=['ns1', 'ns2'],
            class_mof=[TST_CLASSES_MOF],
            inst_mof=[INSTANCE_INITIAL_ENDPOINTS],
            assoc_inst_mof=[ASSOCIATION_MOF_CROSS_NS],
            source_clns=['TST_Person', 'TST_Group'],
            assoc_clns='TST_MemberOfGroup',
            property_mods=('/ns1:TST_MemberOfGroup.InstanceID="G1MikeNS1"',
                           ((CIMProperty("member", type="reference",
                                         value=None),))),
            prop_list=None,
            delete_ns='ns1',
            delete_assoc_inst_test=None,
            exp_rtn={
                'ns1':
                    {'ENUM':
                        {'TST_Person': ['/ns1:TST_Person.name="Mike"'],
                         'TST_Group': [],
                         'TST_MemberOfGroup':
                             ['/ns1:TST_MemberOfGroup.InstanceID="G1MikeNS1"']},
                     'REF':
                        {'TST_Person':
                             ['/ns1:TST_MemberOfGroup.InstanceID="G1MikeNS1"']},
                     'ASSOC':
                        {'TST_Group': [],
                         'TST_Person': ['/ns2:TST_Group.name="ns2group1"']}},
                'ns2':
                    {'ENUM':
                        {'TST_Person': [],
                         'TST_Group': ['/ns2:TST_Group.name="ns2group1"'],
                         'TST_MemberOfGroup':
                             ['/ns2:TST_MemberOfGroup.InstanceID="G1MikeNS1"']},
                     'REF':
                        {'TST_Group':
                            ['/ns2:TST_MemberOfGroup.InstanceID="G1MikeNS1"']},
                     'ASSOC':
                        {'TST_Person': [],
                         'TST_Group': ['/ns1:TST_Person.name="Mike"']}}
            },
        ),
        CIMError, None, RUN
    ),


    # TODO: Needs the following tests.


]
# pylint: enable=bad-continuation

# Disabled this pylint because it is unhappy with indentation of multilevel
# dictionary lower levels.  Note that this occurs with minimum version tests
# but not with latest version tests


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_MULTI_NAMESPACES_MODIFY_INSTANCE)
@simplified_test_function
def test_multiple_namespace_assoc_modify(testcase, namespaces, class_mof,
                                         inst_mof, assoc_inst_mof, source_clns,
                                         assoc_clns, property_mods, prop_list,
                                         delete_ns, delete_assoc_inst_test,
                                         exp_rtn):
    # pylint: disable=unused-argument
    """
    Test the ModifyInstance of multi-namespace association instances defined
    in pywbem_mock.
    """
    conn = FakedWBEMConnection(default_namespace=namespaces[0])

    # Create the repository from test components.  Creates qualdecls,
    # classes, endpoint instances, association instances in multiple
    # namespaces
    create_repository(conn, namespaces, class_mof, inst_mof, assoc_inst_mof)

    assert len(namespaces) == len(exp_rtn)

    # Create list of all classes for enumeration test. Note: This
    # creates a new list.  list() forces create of new object
    enum_clns = list(source_clns)
    enum_clns.append(assoc_clns)

    # Test that the creation of instances was correct.
    validate_instance_enumeration(conn, namespaces, enum_clns, exp_rtn)

    validate_instance_associations(conn, namespaces, source_clns, exp_rtn)

    # if delete_assoc_inst_test exists delete the instance defined for the
    # test from the repository.  The modify should then fail.
    if delete_assoc_inst_test:
        ns = delete_assoc_inst_test.namespace
        instance_store = conn.cimrepository.get_instance_store(ns)
        instance_store.delete(delete_assoc_inst_test)

    # Modify the association instance defined. Test by getting it from repo and
    # comparing values
    if property_mods:
        inst_name = CIMInstanceName.from_wbem_uri(property_mods[0])
        modified_inst = conn.GetInstance(inst_name)
        mods = property_mods[1]
        for pmod in mods:
            if isinstance(pmod, tuple):
                modified_inst[pmod[0]] = pmod[1]
            elif isinstance(pmod, CIMProperty):
                modified_inst[pmod.name] = pmod
            else:
                assert False, "Invalid property_mod test parameter"

        if prop_list is None:
            conn.ModifyInstance(modified_inst)
        else:
            conn.ModifyInstance(modified_inst, PropertyList=prop_list)

        modified_inst_rtn = conn.GetInstance(modified_inst.path)
        for prop in modified_inst:
            assert modified_inst_rtn[prop] == modified_inst[prop]

        for pmod in mods:
            if prop_list and pmod in prop_list:
                assert modified_inst_rtn[pmod[0]] == pmod[1]

    # validate enumeration and associations with modified instance
    validate_instance_enumeration(conn, namespaces, enum_clns, exp_rtn)

    validate_instance_associations(conn, namespaces, source_clns, exp_rtn)

    # Test delete of association instances

    # delete the instance names of the associations in namespace defined by
    # delete_ns.  This should delete each of these associations in each
    # namespace
    deleted_assocs = []
    if delete_ns:
        ns = delete_ns
        inst_names = conn.EnumerateInstanceNames(assoc_clns, namespace=ns)
        for inst_name in inst_names:
            _ = conn.GetInstance(inst_name)
            conn.DeleteInstance(inst_name)
            deleted_assocs.append(inst_name)

        # Confirm inst_name deleted in all namespaces
        for namespace in namespaces:
            for assoc_name in deleted_assocs:
                try:
                    assoc_name.namespace = namespace
                    conn.GetInstance(inst_name)
                    assert False, _format("Instance {} should not exist in "
                                          "ns {} after delete", inst_name,
                                          namespace)
                except CIMError as ce:
                    assert ce.status_code == CIM_ERR_NOT_FOUND


# pylint: disable=bad-continuation
