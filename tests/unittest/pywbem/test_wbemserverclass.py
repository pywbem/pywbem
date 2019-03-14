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
Test for the WBEMServer class  in pywbem._server.py that uses the pywbem_mock
support package the methods of the class. Mock is required since, testing
WBEMServer requires access to a WBEM server.
"""
from __future__ import absolute_import, print_function

import os
import pytest

from pywbem import ValueMapping, CIMInstanceName, CIMError, \
    CIMQualifierDeclaration, CIMClass
from pywbem._nocasedict import NocaseDict

from ..utils.wbemserver_mock import WbemServerMock
from ..utils.pytest_extensions import simplified_test_function

VERBOSE = True

# Location of DMTF schema directory used by all tests.
# This directory is permanent and should not be removed.
TESTSUITE_SCHEMA_DIR = os.path.join('tests', 'schema')


class BaseMethodsForTests(object):  # pylint: disable=too-few-public-methods
    """
    Common methods for test of WBEMServer class.  This includes methods to
    build the DMTF schema and to build individual instances.
    """


class TestServerClass(BaseMethodsForTests):
    # pylint: disable=too-few-public-methods
    """
    Conduct tests on the WBEMServer class.
    """

    @pytest.mark.parametrize(
        "tst_namespace",
        ['interop', 'root/interop', 'root/PG_Interop'])
    def test_wbemserver_basic(self, tst_namespace):
        # pylint: disable=no-self-use
        """
        Test the basic functions that access server information. This test
        creates the mock repository and adds classes and instances for
        the WBEMServer tests that involve namespaces, brand, profiles and
        a subset of the central_instance tests.  It includes no tests for
        errors. The primary goal of this test was to develop the mechanisms
        for easily getting classes and instances into the repo and to provide
        a basic test of functionality.
        """

        # Build the wbem server mock using the  WbemServerMock default test
        # data except that we define the interop namespace
        mock_wbemserver = WbemServerMock(interop_ns=tst_namespace)
        server = mock_wbemserver.wbem_server

        # Build instances for get_central instance
        # Using central methodology, i.e. ElementConformsToProfile

        # Test basic brand, version, namespace methods
        assert server.namespace_classname == 'CIM_Namespace'

        assert server.url == 'http://FakedUrl'

        assert server.brand == "OpenPegasus"
        assert server.version == "2.15.0"
        assert server.interop_ns == tst_namespace
        assert set(server.namespaces) == set([tst_namespace])

        # Test basic profiles methods
        org_vm = ValueMapping.for_property(server, server.interop_ns,
                                           'CIM_RegisteredProfile',
                                           'RegisteredOrganization')

        for inst in server.profiles:
            org = org_vm.tovalues(inst['RegisteredOrganization'])
            name = inst['RegisteredName']
            vers = inst['RegisteredVersion']

            tst_tup = (org, name, vers)
            pass_tst = False
            for tup in mock_wbemserver.registered_profiles:
                if tst_tup == tup:
                    pass_tst = True
                    break
            assert pass_tst

        sel_prof = server.get_selected_profiles(registered_org='DMTF',
                                                registered_name='Indications')
        assert len(sel_prof) == 1
        for inst in sel_prof:
            assert org_vm.tovalues(inst['RegisteredOrganization']) == 'DMTF'
            assert inst['RegisteredName'] == 'Indications'

        # Test case insensitive matching
        sel_prof = server.get_selected_profiles(registered_org='DmtF',
                                                registered_name='inDiCations')
        assert len(sel_prof) == 1
        for inst in sel_prof:
            assert org_vm.tovalues(inst['RegisteredOrganization']) == 'DMTF'
            assert inst['RegisteredName'] == 'Indications'

        sel_prof = server.get_selected_profiles(registered_org='DMTF')
        assert len(sel_prof) == 3
        for inst in sel_prof:
            assert org_vm.tovalues(inst['RegisteredOrganization']) == 'DMTF'

        # Simple get_cental_instance.
        # profile_path, central_class=None,
        #                       scoping_class=None, scoping_path=None
        profile_insts = server.get_selected_profiles(registered_org='SNIA',
                                                     registered_name='Server',
                                                     registered_version='1.1.0')
        profile_path = profile_insts[0].path
        insts = server.get_central_instances(profile_path, 'CIM_ObjectManager')
        assert len(insts) == 1
        kb = NocaseDict([('SystemCreationClassName', 'CIM_ComputerSystem'),
                         ('SystemName', mock_wbemserver.system_name),
                         ('CreationClassName', 'CIM_ObjectManager'),
                         ('Name', 'MyFakeObjectManager'), ])
        assert insts[0] == CIMInstanceName('CIM_ObjectManager', keybindings=kb,
                                           namespace=tst_namespace,
                                           host=server.conn.host)


TESTCASES_CREATE_NAMESPACE = [

    # Testcases for WBEMServer.create_namespace()

    # Each list item is a testcase tuple with these items:
    # * desc: Short testcase description.
    # * kwargs: Keyword arguments for the test function:
    #   * new_namespace: Name of the namespace to be created.
    #   * exp_namespace: Expected returned namespace name.
    # * exp_exc_types: Expected exception type(s), or None.
    # * exp_warn_types: Expected warning type(s), or None.
    # * condition: Boolean condition for testcase to run, or 'pdb' for debugger

    (
        "New top level namespace",
        dict(
            new_namespace='abc',
            exp_namespace=u'abc',
        ),
        None, None, True
    ),
    (
        "New top level namespace with leading and trailing slash",
        dict(
            new_namespace='/abc/',
            exp_namespace=u'abc',
        ),
        None, None, True
    ),
    (
        "New two-segment namespace with leading and trailing slash",
        dict(
            new_namespace='/abc/def/',
            exp_namespace=u'abc/def',
        ),
        None, None, True
    ),
    (
        "New two-segment namespace where first segment already exists",
        dict(
            new_namespace='interop/def',
            exp_namespace=u'interop/def',
        ),
        None, None, True
    ),
    (
        "Existing top level namespace",
        dict(
            new_namespace='interop',
            exp_namespace=None,
        ),
        CIMError, None, True
    ),

]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_CREATE_NAMESPACE)
@simplified_test_function
def test_create_namespace_2(testcase,
                            new_namespace, exp_namespace):
    """
    Test creation of a namespace using approach 2.
    """

    mock_wbemserver = WbemServerMock(interop_ns='interop')
    server = mock_wbemserver.wbem_server

    act_namespace = server.create_namespace(new_namespace)

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None

    assert act_namespace == exp_namespace


TESTCASES_DELETE_NAMESPACE = [

    # Testcases for WBEMServer.delete_namespace()

    # Each list item is a testcase tuple with these items:
    # * desc: Short testcase description.
    # * kwargs: Keyword arguments for the test function:
    #   * namespace: Name of the namespace to be deleted.
    #   * namespace_content: Content of initial namespace, as a dict with
    #     the namespace name as a key and a list of CIMClass, CIMInstance and
    #     CIMQualifierDeclaration objects as the value.
    #   * exp_namespace: Expected returned namespace name.
    # * exp_exc_types: Expected exception type(s), or None.
    # * exp_warn_types: Expected warning type(s), or None.
    # * condition: Boolean condition for testcase to run, or 'pdb' for debugger

    (
        "Empty top level namespace",
        dict(
            namespace='abc',
            namespace_content={'abc': []},
            exp_namespace=u'abc',
        ),
        None, None, True
    ),
    (
        "Empty top level namespace with leading and trailing slash",
        dict(
            namespace='/abc/',
            namespace_content={'abc': []},
            exp_namespace=u'abc',
        ),
        None, None, True
    ),
    (
        "Empty two-segment namespace with leading and trailing slash",
        dict(
            namespace='/abc/def/',
            namespace_content={'abc/def': []},
            exp_namespace=u'abc/def',
        ),
        None, None, True
    ),
    (
        "Empty two-segment namespace where first segment already exists",
        dict(
            namespace='interop/def',
            namespace_content={'interop/def': []},
            exp_namespace=u'interop/def',
        ),
        None, None, True
    ),
    (
        "Non-existing top level namespace",
        dict(
            namespace='abc',
            namespace_content={},
            exp_namespace=None,
        ),
        CIMError, None, True
    ),
    (
        "Non-empty top level namespace containing a class",
        dict(
            namespace='abc',
            namespace_content={'abc': [
                CIMClass('Foo')
            ]},
            exp_namespace=None,
        ),
        CIMError, None, True
    ),
    (
        "Non-empty top level namespace containing a qualifier type",
        dict(
            namespace='abc',
            namespace_content={'abc': [
                CIMQualifierDeclaration('Foo', 'string')
            ]},
            exp_namespace=None,
        ),
        CIMError, None, True
    ),

]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_DELETE_NAMESPACE)
@simplified_test_function
def test_delete_namespace(testcase,
                          namespace, namespace_content, exp_namespace):
    """
    Test deletion of a namespace.
    """

    mock_wbemserver = WbemServerMock(interop_ns='interop')
    server = mock_wbemserver.wbem_server

    # Ensure that the namespace is set up as specified in the testcase
    for ns in namespace_content:
        server.create_namespace(ns)
        for obj in namespace_content[ns]:
            if isinstance(obj, CIMClass):
                server.conn.CreateClass(NewClass=obj, namespace=ns)
            else:
                assert isinstance(obj, CIMQualifierDeclaration)
                server.conn.SetQualifier(QualifierDeclaration=obj,
                                         namespace=ns)

    # The code to be tested
    act_namespace = server.delete_namespace(namespace)

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None

    assert act_namespace == exp_namespace


TESTCASES_GET_CENTRAL_INSTANCES = [

    # Testcases for WBEMServer.get_central_instances()

    # Each list item is a testcase tuple with these items:
    # * desc: Short testcase description.
    # * kwargs: Keyword arguments for the test function:
    #   * profile_name: Name of the profile as tuple (org, name, version)
    #   * central_class: Name of the central class of the profile.
    #   * scoping_class: Name of the scoping class of the profile, or None for
    #     autonomous profiles.
    #   * scoping_path: List of class names for the scoping path (from central
    #     class to scoping class, not including central or scoping classes), or
    #     None for autonomous profiles.
    #   * direction: Reference direction 'snia' or 'dmtf'.
    #   * exp_paths: Expected returned instance paths, as a list of
    #     CIMInstanceName objects.
    # * exp_exc_types: Expected exception type(s), or None.
    # * exp_warn_types: Expected warning type(s), or None.
    # * condition: Boolean condition for testcase to run, or 'pdb' for debugger
    (
        "Valid central class",
        dict(
            profile_name=('SNIA', 'Server', '1.2.0'),
            central_class='XXX_StorageComputerSystem',
            scoping_class=None,
            scoping_path=None,
            direction='snia',
            exp_paths=[
                CIMInstanceName('XXX_StorageComputerSystem',
                                keybindings={'Name': "10.1.2.3",
                                             'CreationClassName':
                                             'XXX_StorageComputerSystem'},
                                host='FakedUrl',
                                namespace='interop'), ]
        ),
        None, None, True
    ),
    # TODO add more central instance tests
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_GET_CENTRAL_INSTANCES)
@simplified_test_function
def test_get_central_instances(testcase, profile_name, central_class,
                               scoping_class, scoping_path, direction,
                               exp_paths):
    """
    Test the execution of WBEMSeever.get_central_instances()
    """
    mock_wbemserver = WbemServerMock(interop_ns='interop')
    server = mock_wbemserver.wbem_server
    profile_insts = server.get_selected_profiles(
        registered_org=profile_name[0],
        registered_name=profile_name[1],
        registered_version=profile_name[2])
    assert len(profile_insts) == 1
    profile_inst = profile_insts[0]

    # The code to be tested.
    # Must start from a single good profile instance

    # server.conn.display_repository()
    act_paths = server.get_central_instances(profile_inst.path,
                                             central_class=central_class,
                                             scoping_class=scoping_class,
                                             scoping_path=scoping_path,
                                             reference_direction=direction)

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None

    assert act_paths == exp_paths


# TODO Break up tests to do individual tests for each group of methods so we can
#      test for errors, variations on what is in the repo with each method.
#      Right now we build it all in a single test.  Thus, for example we
#      need to create a test group for find_central_instances since the
#      definition of the repo is different for each method of getting the
#      central instances Iex. If the server method exists, no other methods
#      are tried.
