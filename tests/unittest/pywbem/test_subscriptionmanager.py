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
Test for the WBEMSubscriptionManager class.
"""
from __future__ import absolute_import, print_function

import os
import re
import pytest

from ...utils import skip_if_moftab_regenerated
from ..utils.dmtf_mof_schema_def import DMTF_TEST_SCHEMA_VER
from ..utils.wbemserver_mock import WbemServerMock
from ..utils.pytest_extensions import simplified_test_function

# pylint: disable=wrong-import-position, wrong-import-order, invalid-name
from ...utils import import_installed
pywbem = import_installed('pywbem')
from pywbem import WBEMServer, CIMClassName, WBEMSubscriptionManager, \
    CIMInstance, CIMDateTime, CIMError, CIM_ERR_ALREADY_EXISTS  # noqa: E402
from pywbem._subscription_manager import SUBSCRIPTION_CLASSNAME, \
    DESTINATION_CLASSNAME, FILTER_CLASSNAME  # noqa: E402
from pywbem_mock import OBJECTMANAGERNAME, \
    SYSTEMNAME  # noqa: E402
pywbem_mock = import_installed('pywbem_mock')
# pylint: enable=wrong-import-position, wrong-import-order, invalid-name


# Location of DMTF schema directory used by all tests.
# This directory is permanent and should not be removed.
TESTSUITE_SCHEMA_DIR = os.path.join('tests', 'schema')

# The following dictionary is the mock WBEM server configuration for the
# WBEMServerMock class.  It defines a mock WBEM server that is build with
# defined class schemas, classnames, etc.  It uses the same dictionary pattern
# as the default dictionary in the ../utils directory.

SUBSCRIPTION_WBEM_SERVER_MOCK_DICT = {
    'dmtf_schema': {'version': DMTF_TEST_SCHEMA_VER,
                    'dir': TESTSUITE_SCHEMA_DIR},
    'tst_schema': {
        'dir': os.path.join(TESTSUITE_SCHEMA_DIR, 'FakeWBEMServer'),
        'files': []},

    # url of the mock server.  if None the default pywbem_mock url is used
    # This url can be overridden by the WBEMServerMock initialization parameter.
    'url': None,

    'class_names': ['CIM_Namespace',
                    'CIM_ObjectManager',
                    'CIM_RegisteredProfile',
                    'CIM_ElementConformsToProfile',
                    'CIM_ReferencedProfile',
                    'CIM_ComputerSystem',
                    'CIM_IndicationSubscription',
                    'CIM_ListenerDestinationCIMXML',
                    'CIM_IndicationFilter', ],

    'class-mof': ["class XXX_StorageComputerSystem : CIM_ComputerSystem{};", ],
    'system_name': SYSTEMNAME,
    'object_manager': {'Name': OBJECTMANAGERNAME,
                       'ElementName': 'Mock_Test',
                       'Description': 'Mock_Test CIM Server Version 2.15.0'
                                      ' Released', },
    'interop_namspace': 'interop',
    'other_namespaces': [],
    # mock providers that should be installed as part of startup
    # The common parameter is the namespace for the provider
    'providers': ["namespace_provider", 'subscription_providers'],

    # Definition of registered profiles.  Each entry creates a registered
    # profile instance (i.e CIM_RegisteredProfile)
    'registered_profiles': [('DMTF', 'Indications', '1.1.0'),
                            ('DMTF', 'Profile Registration', '1.0.0'),
                            ('SNIA', 'Server', '1.1.0'),
                            ('SNIA', 'Server', '1.2.0'), ],

    'referenced_profiles': [
        (('SNIA', 'Server', '1.2.0'), ('DMTF', 'Indications', '1.1.0')),
    ],
    # Define profile relation to central class instance
    # First element is a profile, second is name and keybindings of a
    # CIMInstanceName
    'element_conforms_to_profile': [],
    # List of CIMInstances. Each entry is a CIM instance with classname,
    # and properties. All properties required to build the path must be
    # defined. No other properties are required for this test.
    'central-instances': [],
    'scoping-instances': []
}


# NOTE: Please add new test functionality to the function
#       test_subscriptionmanager(...)) below. We will leave these functions
#       because they do provide a broad set of test functionality in just a few
#       tests (each tests creates the mock environment)
class BaseMethodsForTests(object):
    """
    Base Class for tests contains all common methods and class level
    setup.
    """

    def setup_method(self):
        """
        Create the Fake connection and setup the connection. This
        method first initializes the WbemServerMock and then supplements
        it with the classes required for the subscription manager.
        """
        skip_if_moftab_regenerated()

        server = WbemServerMock(
            interop_ns='interop',
            server_mock_data=SUBSCRIPTION_WBEM_SERVER_MOCK_DICT)
        # pylint: disable=attribute-defined-outside-init
        self.conn = server.wbem_server.conn

    @staticmethod
    def inst_from_classname(conn, class_name, namespace=None,
                            property_list=None,
                            property_values=None,
                            include_missing_properties=True,
                            include_path=True):
        # TODO AM 8/18 The inst_from_classname() method is not used.
        """
        Build instance from class using class_name property to get class
        from a repository.
        """
        cls = conn.GetClass(class_name, namespace=namespace, LocalOnly=False,
                            IncludeQualifiers=True, include_class_origin=True,
                            property_list=property_list)

        return CIMInstance.from_class(
            cls, namespace=namespace, property_values=property_values,
            include_missing_properties=include_missing_properties,
            include_path=include_path)

    def add_filter(self, sub_mgr, server_id, owned, filter_id=None, name=None):
        """
        Create a single filter definition in the sub_mgr (which adds it to
        the repository) and returns the path of the new filter instance.
        This creates a filter specifically these tests
        """
        # pylint: disable=attribute-defined-outside-init
        self.test_class = 'Test_IndicationProviderClass'
        self.test_class_namespace = 'test/TestProvider'

        self.test_query = 'SELECT * from %s' % self.test_class
        self.test_classname = CIMClassName(self.test_class,
                                           namespace=self.test_class_namespace)

        kwargs = {}
        if filter_id is not None:
            kwargs['filter_id'] = filter_id
        if name is not None:
            kwargs['name'] = name
        filter_ = sub_mgr.add_filter(server_id,
                                     self.test_class_namespace,
                                     self.test_query,
                                     query_language="DMTF:CQL",
                                     owned=owned, **kwargs)
        return filter_.path

    def get_owned_inst_counts(self):
        """
        Using the server connection, get the owned filters, destinations and
        subscriptions from the server and return a tuple with the count for
        each of them.
        """
        server = WBEMServer(self.conn)
        system_name = server.cimom_inst['SystemName']

        owned_dest_pattern = re.compile(r'^pywbemdestination:')
        dest_insts = server.conn.EnumerateInstances(
            DESTINATION_CLASSNAME, namespace=server.interop_ns)
        owned_dest_insts = []
        for inst in dest_insts:
            if re.match(owned_dest_pattern, inst.path.keybindings['Name']) \
                    and inst.path.keybindings['SystemName'] == system_name:
                owned_dest_insts.append(inst)

        filter_insts = server.conn.EnumerateInstances(
            FILTER_CLASSNAME, namespace=server.interop_ns)
        owned_filter_insts = []
        owned_filter_pattern = re.compile(r'^pywbemfilter:')
        for inst in filter_insts:
            if re.match(owned_filter_pattern, inst.path.keybindings['Name']) \
                    and inst.path.keybindings['SystemName'] == system_name:
                owned_filter_insts.append(inst)

        owned_filter_paths = [inst.path for inst in owned_filter_insts]
        owned_dest_paths = [inst.path for inst in owned_dest_insts]

        sub_insts = server.conn.EnumerateInstances(
            SUBSCRIPTION_CLASSNAME, namespace=server.interop_ns)
        owned_sub_insts = []
        for inst in sub_insts:
            if inst.path.keybindings['Filter'] in owned_filter_paths \
                    or inst.path.keybindings['Handler'] in owned_dest_paths:
                owned_sub_insts.append(inst)

        return (len(owned_filter_insts), len(owned_dest_insts),
                len(owned_sub_insts))

    def confirm_created(self, sub_mgr, server_id, filter_path,
                        subscription_paths, owned=True):
        # pylint: disable=no-self-use
        """
        Confirm that filters and subscription paths provided with call
        exist in the appropriated lists.
        """
        if owned:
            owned_filters = sub_mgr.get_owned_filters(server_id)
            owned_filter_paths = [inst.path for inst in owned_filters]

            assert filter_path in owned_filter_paths

            owned_subscriptions = sub_mgr.get_owned_subscriptions(server_id)
            owned_sub_paths = [inst.path for inst in owned_subscriptions]
            for subscription_path in owned_sub_paths:
                assert subscription_path in owned_sub_paths

        all_filters = sub_mgr.get_all_filters(server_id)
        all_filter_paths = [inst.path for inst in all_filters]
        assert filter_path in all_filter_paths

        all_subscriptions = sub_mgr.get_all_subscriptions(server_id)
        all_sub_paths = [inst.path for inst in all_subscriptions]
        for subscription_path in subscription_paths:
            assert subscription_path in all_sub_paths

    def confirm_removed(self, sub_mgr, server_id, filter_paths,
                        subscription_paths):
        # pylint: disable=no-self-use
        """
        When filter_path and subscription path are removed, this
        confirms that results are correct both in the local subscription
        manager and the remote WBEM server.
        """
        if not isinstance(filter_paths, list):
            filter_paths = [filter_paths]

        owned_filters = sub_mgr.get_owned_filters(server_id)
        for filter_path in filter_paths:
            assert filter_path not in owned_filters

        # confirm not in owned subscriptions
        if not isinstance(subscription_paths, list):
            subscription_paths = [subscription_paths]

        owned_subscriptions = sub_mgr.get_owned_subscriptions(server_id)
        owned_sub_paths = [inst.path for inst in owned_subscriptions]
        for subscription_path in subscription_paths:
            assert subscription_path not in owned_sub_paths

        all_filters = sub_mgr.get_all_filters(server_id)
        all_filter_paths = [inst.path for inst in all_filters]
        for filter_path in filter_paths:
            assert filter_path not in all_filter_paths

        all_subscriptions = sub_mgr.get_all_subscriptions(server_id)
        all_sub_paths = [inst.path for inst in all_subscriptions]
        for subscription_path in subscription_paths:
            assert subscription_path not in all_sub_paths

    def empty_expected(self, sub_mgr, server_id):
        """ Get outstanding objects from server. Return True if 0 objects """
        # pylint: disable=no-self-use

        counts = self.get_submgr_inst_counts(sub_mgr, server_id)
        if sum(counts) == 0:
            return True

        print('ERROR: Server_id=%s. Unreleased filters=%s, subs=%s, dest=%s' %
              (server_id, counts[0], counts[1], counts[2]))
        return False

    def get_submgr_inst_counts(self, sub_mgr, server_id):
        """
        Return count of all filters, subscriptions, and destinations on the
        specified subscription manager with the specified server ID,
        and return a tuple with the count for each of them.
        """
        # pylint: disable=no-self-use

        filters = len(sub_mgr.get_all_filters(server_id))
        subscriptions = len(sub_mgr.get_all_subscriptions(server_id))
        dests = len(sub_mgr.get_all_subscriptions(server_id))

        return (filters, subscriptions, dests)


class TestSubMgrClass(BaseMethodsForTests):
    """Test of subscription manager"""

    def test_create_owned_subscription(self):
        """
        Test Basic Creation of sub mgr, creation of owned subscription
        and cleanup based on the WBEMSubscriptionManager context manager.
        """
        sm = "test_create_delete_subscription"
        server = WBEMServer(self.conn)

        listener_url = '%s:%s' % (self.conn.url, 50000)

        with WBEMSubscriptionManager(subscription_manager_id=sm) as sub_mgr:

            server_id = sub_mgr.add_server(server)

            # Create an owned listener, filter, and subscription

            dest = sub_mgr.add_destination(
                server_id, listener_url, owned=True, destination_id='dest1')
            dest_path = dest.path
            # Note: this method returns path.
            filter_path = self.add_filter(
                sub_mgr, server_id, owned=True, filter_id='MyFilterID')
            # Should create a single subscription since there is just one
            # destination
            subscriptions = sub_mgr.add_subscriptions(
                server_id, filter_path, owned=True)

            assert len(subscriptions) == 1
            subscription_paths = [inst.path for inst in subscriptions]

            self.confirm_created(sub_mgr, server_id, filter_path,
                                 subscription_paths, owned=True)

            # Confirm destination instance paths match
            assert len(sub_mgr.get_all_destinations(server_id)) == 1

            # Test that these are considered owned objects
            # Test occurs in confirm_created() but dupped here to confirm
            owned_subscriptions = sub_mgr.get_owned_subscriptions(server_id)
            owned_filters = sub_mgr.get_owned_filters(server_id)
            owned_destinations = sub_mgr.get_owned_destinations(server_id)
            assert dest_path in [inst.path for inst in owned_destinations]
            assert filter_path in [inst.path for inst in owned_filters]
            assert subscription_paths[0] in [inst.path
                                             for inst in owned_subscriptions]

            # Issue #701
            # Test that the same owned subscription is not created a second
            # time because the path is the same as the first.
            subscriptions2 = sub_mgr.add_subscriptions(
                server_id, filter_path, owned=True)
            assert len(subscriptions2) == 1
            # Cannot assert subscription equality because of starttime
            # which is time dependent
            assert [s.path for s in subscriptions] == \
                [s.path for s in subscriptions2]

            # Set times in subscriptions to a fixed time and test for
            # subscription equality
            test_time = CIMDateTime.now()
            for sub in subscriptions:
                sub['SubscriptionStartTime'] = test_time
                sub['TimeOfLastStateChange'] = test_time
            for sub in subscriptions2:
                sub['SubscriptionStartTime'] = test_time
                sub['TimeOfLastStateChange'] = test_time
            assert subscriptions == subscriptions2
            assert len(sub_mgr.get_owned_destinations(server_id)) == 1

            # Trying to create a second filter with the same name fails
            with pytest.raises(CIMError) as exc_info:
                self.add_filter(sub_mgr, server_id, owned=True,
                                filter_id='MyFilterID')
            exc = exc_info.value
            assert exc.status_code == CIM_ERR_ALREADY_EXISTS
            assert len(sub_mgr.get_owned_filters(server_id)) == 1

            sub_mgr.remove_subscriptions(server_id, subscription_paths)
            sub_mgr.remove_filter(server_id, filter_path)

            self.confirm_removed(
                sub_mgr, server_id, [filter_path], subscription_paths)

            assert self.get_submgr_inst_counts(sub_mgr, server_id) == (0, 0, 0)

            sub_mgr.remove_server(server_id)

        # confirm no owned filters, destinations, subscriptions in server
        assert self.get_owned_inst_counts() == (0, 0, 0)

    def test_create_permanent_subscription(self):
        """
        Test creating permanent filter, destination and filter and determining
        if they are retained by the server after the subscription manager
        is closed.
        """
        sm = "test_create_delete_subscription"
        server = WBEMServer(self.conn)

        listener_url = '%s:%s' % (self.conn.url, 50000)
        # Create a single not_owned subscription
        with WBEMSubscriptionManager(subscription_manager_id=sm) as sub_mgr:
            server_id = sub_mgr.add_server(server)
            dest = sub_mgr.add_destination(
                server_id, listener_url, owned=False, name='name1')
            filter_path = self.add_filter(
                sub_mgr, server_id, owned=False, name='MyName')
            subscriptions = sub_mgr.add_subscriptions(
                server_id, filter_path,
                destination_paths=dest.path,
                owned=False)
            subscription_paths = [inst.path for inst in subscriptions]

            self.confirm_created(sub_mgr, server_id, filter_path,
                                 subscription_paths, owned=False)
            assert self.get_submgr_inst_counts(sub_mgr, server_id) == (1, 1, 1)

        # Test that subscriptions instances are still in repo
        # self.conn.display_repository()

        assert self.get_owned_inst_counts() == (0, 0, 0)

        # Create a new submgr and and test for filters, etc. retrieved.
        with WBEMSubscriptionManager(subscription_manager_id=sm) as sub_mgr:
            server_id = sub_mgr.add_server(server)
            assert self.get_submgr_inst_counts(sub_mgr, server_id) == (1, 1, 1)

            sub_paths = [s.path for s in
                         sub_mgr.get_all_subscriptions(server_id)]
            sub_mgr.remove_subscriptions(server_id, sub_paths)

            dest_paths = [d.path for d in
                          sub_mgr.get_all_destinations(server_id)]
            sub_mgr.remove_destinations(
                server_id, dest_paths)

            for filter_ in sub_mgr.get_all_filters(server_id):
                sub_mgr.remove_filter(server_id, filter_.path)
            assert self.get_submgr_inst_counts(sub_mgr, server_id) == (0, 0, 0)

    def test_recovery_of_owned_subscriptions(self):
        """
        Test the ability to recover owned subscriptions from the server. Tests
        ability of SubscriptionManager to recover owned subscriptions, etc.
        from server when started by creating a second subscription mgr.
        """

        sm = "test_subscription_object_recovery"
        server = WBEMServer(self.conn)

        listener_url = '%s:%s' % (self.conn.url, 50000)

        submgr1 = WBEMSubscriptionManager(subscription_manager_id=sm)
        server_id1 = submgr1.add_server(server)

        # Create an owned listener, filter, and subscription

        dest = submgr1.add_destination(
            server_id1, listener_url, owned=True, destination_id='dest1')
        dest_path = dest.path
        filter_path = self.add_filter(
            submgr1, server_id1, owned=True, filter_id='MyFilterID')
        subscriptions = submgr1.add_subscriptions(
            server_id1, filter_path, owned=True)

        assert len(subscriptions) == 1
        subscription_paths = [inst.path for inst in subscriptions]

        self.confirm_created(submgr1, server_id1, filter_path,
                             subscription_paths, owned=True)

        # Confirm destination instance paths match
        assert len(submgr1.get_all_destinations(server_id1)) == 1

        # Test that these are considered owned objects
        # Added to test fix for issue #701,
        # Test already occurs in confirm_created()
        owned_subscriptions = submgr1.get_owned_subscriptions(server_id1)
        owned_filters = submgr1.get_owned_filters(server_id1)
        owned_destinations = submgr1.get_owned_destinations(server_id1)
        assert dest_path in [inst.path for inst in owned_destinations]
        assert filter_path in [inst.path for inst in owned_filters]
        assert subscription_paths[0] in [inst.path
                                         for inst in owned_subscriptions]

        # Create a second subscription manager to recover owned objects
        submgr2 = WBEMSubscriptionManager(subscription_manager_id=sm)
        server_id2 = submgr2.add_server(server)
        assert len(submgr2.get_owned_subscriptions(server_id2)) == 1
        assert len(submgr2.get_owned_destinations(server_id2)) == 1
        assert len(submgr2.get_owned_filters(server_id2)) == 1

        assert submgr2.get_owned_filters(server_id2) == \
            submgr1.get_owned_filters(server_id1)

        assert submgr2.get_owned_destinations(server_id2) == \
            submgr1.get_owned_destinations(server_id1)

        assert submgr2.get_owned_subscriptions(server_id2) == \
            submgr1.get_owned_subscriptions(server_id1)

        # Remove all the subscription objects from submgr1
        submgr1.remove_subscriptions(server_id1, subscription_paths)
        submgr1.remove_filter(server_id1, filter_path)

        self.confirm_removed(submgr1, server_id1, filter_path,
                             subscription_paths)

        assert self.get_submgr_inst_counts(submgr1, server_id1) == (0, 0, 0)

        submgr1.remove_server(server_id1)

        # confirm no owned filters, destinations, subscriptions in server
        assert self.get_owned_inst_counts() == (0, 0, 0)


OK = True
RUN = True
FAIL = False


TESTCASES_SUBMGR = [

    # Testcases for Subscription Tests multiple valid and invalid options
    # in __init__, add_server, add_filter, add_destinations

    # Each list item is a testcase tuple with these items:
    # * desc: Short testcase description.
    # * kwargs: Keyword arguments for the test function:
    #   * submgr_id: submgr id
    #   * connection_attrs: FakedWBEMConnection attributes. this variable causes
    #     an add_server to be executed. If it is a list, multiple
    #     a server is added for each dict in the list. The attributes of
    #     the FakedWBEMConnection can be set as attributes. Note: this test
    #     already sets the interop namespace automatically
    #   * filter_attrs: dictionary of attributes for add_filter. If it is
    #     a list, one filter is added for each dict in the list
    #   * dest_attrs: dictionary of attributes for add_destination().
    #   * subscription_attrs: dictionary or list dictionaries where each
    #     dictionary is a dictionary that defines either the attributes of
    #     the subscription or to make it simpler to define tests, an integer
    #     for the position in the appropriate list for the required
    #     filter or destination.
    #   * remove_destinations: Option that removes all destinations, if
    #     True, single destination if integer or list of destinations if
    #     list of integers using the saved list from creation with the integer
    #     as index into the list of destinations created.
    #   * remove_filter: Option that removes all filters, if
    #     True, single filter if integer or list of filters if
    #     list of integers using the saved list from creation with the integer
    #     as index into the list of destinations created.
    #   * remove_subscription_attrs: Option that removes all subscriptions, if
    #     True, single subscription if integer or list of filters if
    #     list of integers using the saved list from creation with the integer
    #     as index into the list of subscription created.
    #   * remove_server_attrs: Single server_id identifying server to remove.
    #     This function is executed after all other methods and their tests so
    #     the other tests reflect what was added.
    #   * dest_props: TODO add definition from future pr
    #   * exp_result: Expected dictionary items, for validation. This includes:
    #       * server_id - The expected server_id
    #       * listener_count - Count of expected destinations
    #       * filter_count - Count of expected filters.
    #       * TODO: Add validation for filter, dest attributes
    #       * dest_props - Test for specific properties in specific instances.
    #         TODO: define syntax
    #       * filter_props - Test for specific properties in specific instances.
    #         TODO: define syntax
    #       * subscription_count - Count of expected subscriptions.
    #
    # * exp_exc_types: Expected exception type(s), or None.
    # * exp_warn_types: Expected warning type(s), or None.
    # * condition: Boolean condition for testcase to run, or 'pdb' for debugger

    (
        "Create no valid id",
        dict(
            submgr_id='MySubscriptionManager',
            connection_attrs=None,
            filter_attrs=None,
            dest_attrs=None,
            subscription_attrs=None,
            remove_destinations=None,
            remove_filters=None,
            remove_subscriptions=None,
            remove_server_attrs=None,
            exp_result={}
        ),
        None, None, OK
    ),
    (
        "Invalid subscription manager ID (includes :",
        dict(
            submgr_id='MySubscription:Manager',
            connection_attrs=None,
            filter_attrs=None,
            dest_attrs=None,
            subscription_attrs=None,
            remove_destinations=None,
            remove_filters=None,
            remove_subscriptions=None,
            remove_server_attrs=None,
            exp_result={}
        ),
        ValueError, None, OK
    ),
    (
        "Invalid subscription manager id not a string :",
        dict(
            submgr_id=333,
            connection_attrs=None,
            filter_attrs=None,
            dest_attrs=None,
            subscription_attrs=None,
            remove_destinations=None,
            remove_filters=None,
            remove_subscriptions=None,
            remove_server_attrs=None,
            exp_result={}
        ),
        TypeError, None, OK
    ),
    (
        "Invalid subscription manager id, value None",
        dict(
            submgr_id=None,
            connection_attrs=None,
            filter_attrs=None,
            dest_attrs=None,
            subscription_attrs=None,
            remove_destinations=None,
            remove_filters=None,
            remove_subscriptions=None,
            remove_server_attrs=None,
            exp_result={}
        ),
        ValueError, None, OK
    ),
    (
        "Valid submgr id and server id",
        dict(
            submgr_id="ValidID",
            connection_attrs=dict(url=None),
            filter_attrs=None,
            dest_attrs=None,
            remove_destinations=None,
            remove_filters=None,
            remove_subscriptions=None,
            subscription_attrs=None,
            remove_server_attrs=None,
            exp_result=dict(server_id="http://FakedUrl:5988")
        ),
        None, None, OK
    ),
    (
        "Valid submgr id and multiple server ids",
        dict(
            submgr_id="ValidID",
            connection_attrs=[dict(url=None),
                              dict(url="http://fake2:5988")],
            filter_attrs=None,
            dest_attrs=None,
            subscription_attrs=None,
            remove_destinations=None,
            remove_filters=None,
            remove_subscriptions=None,
            remove_server_attrs=None,
            exp_result=dict(server_id=["http://FakedUrl:5988",
                                       "http://fake2:5988"])
        ),
        None, None, OK
    ),
    (
        "Add_filter with No name or filter_id fails",
        dict(
            submgr_id="ValidID",
            connection_attrs=dict(url=None),
            filter_attrs=dict(server_id="http://FakedUrl:5988",
                              source_namespaces='root/interop',
                              query="SELECT * from blah",
                              query_language='WQL',
                              owned=True,
                              filter_id=None, name=None),
            dest_attrs=None,
            subscription_attrs=None,
            remove_destinations=None,
            remove_filters=None,
            remove_subscriptions=None,
            remove_server_attrs=None,
            exp_result=dict(server_id="http://FakedUrl:5988")
        ),
        ValueError, None, OK
    ),
    (
        "Add_filter with name and owned fails",
        dict(
            submgr_id="ValidID",
            connection_attrs=dict(url=None),
            filter_attrs=dict(server_id="http://FakedUrl:5988",
                              source_namespaces='root/interop',
                              query="SELECT * from blah",
                              query_language='WQL',
                              owned=True,
                              filter_id=None, name='NotAllowedWithOwned'),
            dest_attrs=None,
            subscription_attrs=None,
            remove_destinations=None,
            remove_filters=None,
            remove_subscriptions=None,
            remove_server_attrs=None,
            exp_result=dict(server_id="http://FakedUrl:5988")
        ),
        ValueError, None, OK
    ),
    (
        "Add_filter with filter_id and not owned fails",
        dict(
            submgr_id="ValidID",
            connection_attrs=dict(url=None),
            filter_attrs=dict(server_id="http://FakedUrl:5988",
                              source_namespaces='root/interop',
                              query="SELECT * from blah",
                              query_language='WQL',
                              owned=False,
                              filter_id='id1', name=None),
            dest_attrs=None,
            subscription_attrs=None,
            remove_destinations=None,
            remove_filters=None,
            remove_subscriptions=None,
            remove_server_attrs=None,
            exp_result=dict(server_id="http://FakedUrl:5988")
        ),
        ValueError, None, OK
    ),
    (
        "Add_filter with unknown server_id ",
        dict(
            submgr_id="ValidID",
            connection_attrs=dict(url=None),
            filter_attrs=dict(server_id="UnknownServerId",
                              source_namespaces='root/interop',
                              query="SELECT * from blah",
                              query_language='WQL',
                              owned=True,
                              filter_id=None, name=None),
            dest_attrs=None,
            subscription_attrs=None,
            remove_destinations=None,
            remove_filters=None,
            remove_subscriptions=None,
            remove_server_attrs=None,
            exp_result=dict(server_id="http://FakedUrl:5988")
        ),
        ValueError, None, OK
    ),
    (
        "Add_server with both name and filter_id fails",
        dict(
            submgr_id="ValidID",
            connection_attrs=dict(url=None),
            filter_attrs=dict(server_id="http://FakedUrl:5988",
                              source_namespaces='root/interop',
                              query="SELECT * from blah",
                              query_language='WQL',
                              owned=True,
                              filter_id="Fred", name="fred"),
            dest_attrs=None,
            subscription_attrs=None,
            remove_destinations=None,
            remove_filters=None,
            remove_subscriptions=None,
            remove_server_attrs=None,
            exp_result=dict(server_id="http://FakedUrl:5988")
        ),
        ValueError, None, OK
    ),
    (
        "Add_server twice with same serverID",
        dict(
            submgr_id="ValidID",
            connection_attrs=[dict(url=None), dict(url=None)],
            filter_attrs=dict(server_id="http://FakedUrl:5988",
                              source_namespaces='root/interop',
                              query="SELECT * from blah",
                              query_language='WQL',
                              owned=True,
                              filter_id="Fred", name="fred"),
            dest_attrs=None,
            subscription_attrs=None,
            remove_destinations=None,
            remove_filters=None,
            remove_subscriptions=None,
            remove_server_attrs=None,
            exp_result=dict(server_id="http://FakedUrl:5988")
        ),
        ValueError, None, OK
    ),
    (
        "Add_filter with filter_id containing : character fails",
        dict(
            submgr_id="ValidID",
            connection_attrs=dict(url=None),
            filter_attrs=dict(server_id="http://FakedUrl:5988",
                              source_namespaces='root/interop',
                              query="SELECT * from blah",
                              query_language='WQL',
                              owned=True,
                              filter_id="Fred:", name=None),
            dest_attrs=None,
            subscription_attrs=None,
            remove_destinations=None,
            remove_filters=None,
            remove_subscriptions=None,
            remove_server_attrs=None,
            exp_result=dict(server_id="http://FakedUrl:5988", )
        ),
        ValueError, None, OK
    ),
    (
        "Add_filter with filter_id not a string fails",
        dict(
            submgr_id="ValidID",
            connection_attrs=dict(url=None),
            filter_attrs=dict(server_id="http://FakedUrl:5988",
                              source_namespaces='root/interop',
                              query="SELECT * from blah",
                              query_language='WQL',
                              owned=True,
                              filter_id=9, name=None),
            dest_attrs=None,
            subscription_attrs=None,
            remove_destinations=None,
            remove_filters=None,
            remove_subscriptions=None,
            remove_server_attrs=None,
            exp_result=dict(server_id="http://FakedUrl:5988")
        ),
        TypeError, None, OK
    ),
    (
        "Add_filter with valid filter",
        dict(
            submgr_id="ValidID",
            connection_attrs=dict(url=None),
            filter_attrs=dict(server_id="http://FakedUrl:5988",
                              source_namespaces='root/interop',
                              query="SELECT * from blah",
                              query_language='WQL',
                              owned=True,
                              filter_id="Filter1", name=None),
            dest_attrs=None,
            subscription_attrs=None,
            remove_destinations=None,
            remove_filters=None,
            remove_subscriptions=None,
            remove_server_attrs=None,
            exp_result=dict(server_id="http://FakedUrl:5988",
                            filter_count=1,
                            filter_props=[0, [('SourceNamespaces',
                                               ['root/interop'])]]),
        ),
        None, None, OK
    ),
    (
        "Add_filter with valid filter that has multiple source namespaces",
        dict(
            submgr_id="ValidID",
            connection_attrs=dict(url=None),
            filter_attrs=dict(server_id="http://FakedUrl:5988",
                              source_namespaces=['root/interop', 'root/cimv2'],
                              query="SELECT * from blah",
                              query_language='WQL',
                              owned=True,
                              filter_id="Filter1", name=None),
            dest_attrs=None,
            subscription_attrs=None,
            remove_destinations=None,
            remove_filters=None,
            remove_subscriptions=None,
            remove_server_attrs=None,
            exp_result=dict(server_id="http://FakedUrl:5988",
                            filter_count=1,
                            filter_props=[0, [('SourceNamespaces',
                                               ['root/interop',
                                                'root/cimv2'])]]),
        ),
        None, None, OK
    ),
    (
        "Add valid filter with multiple source namespaces, sourcenamespace",
        dict(
            submgr_id="ValidID",
            connection_attrs=dict(url=None),
            filter_attrs=dict(server_id="http://FakedUrl:5988",
                              source_namespaces=['root/interop', 'root/cimv2'],
                              query="SELECT * from blah",
                              query_language='WQL',
                              owned=True,
                              filter_id="Filter1", name=None,
                              source_namespace="root/cimv3"),
            dest_attrs=None,
            subscription_attrs=None,
            remove_destinations=None,
            remove_filters=None,
            remove_subscriptions=None,
            remove_server_attrs=None,
            exp_result=dict(
                server_id="http://FakedUrl:5988",
                filter_count=1,
                filter_props=[0, [('SourceNamespaces', ['root/interop',
                                                        'root/cimv2']),
                                  ('SourceNamespace', 'root/cimv3')]], ),
        ),
        None, None, OK
    ),
    (
        "Add_filter with valid filter and remove server_id",
        dict(
            submgr_id="ValidID",
            connection_attrs=dict(url=None),
            filter_attrs=dict(server_id="http://FakedUrl:5988",
                              source_namespaces='root/interop',
                              query="SELECT * from blah",
                              query_language='WQL',
                              owned=True,
                              filter_id="Filter1", name=None),
            dest_attrs=None,
            subscription_attrs=None,
            remove_destinations=None,
            remove_filters=None,
            remove_subscriptions=None,
            remove_server_attrs="http://FakedUrl:5988",
            exp_result=dict(server_id="http://FakedUrl:5988",
                            filter_count=1)
        ),
        None, None, OK
    ),
    (
        "Add_filters with  2 valid filter definitions",
        dict(
            submgr_id="ValidID",
            connection_attrs=dict(url=None),
            filter_attrs=[dict(server_id="http://FakedUrl:5988",
                               source_namespaces='root/interop',
                               query="SELECT * from blah",
                               query_language='WQL',
                               owned=True,
                               filter_id="Filter1", name=None),
                          dict(server_id="http://FakedUrl:5988",
                               source_namespaces='root/interop',
                               query="SELECT * from blah",
                               query_language='WQL',
                               owned=True,
                               filter_id="Filter2", name=None), ],
            dest_attrs=None,
            subscription_attrs=None,
            remove_destinations=None,
            remove_filters=None,
            remove_subscriptions=None,
            remove_server_attrs=None,
            exp_result=dict(server_id="http://FakedUrl:5988",
                            filter_count=2)
        ),
        None, None, OK
    ),
    (
        "Add listener_dest with invalid url",
        dict(
            submgr_id="ValidID",
            connection_attrs=dict(url=None),
            filter_attrs=None,
            dest_attrs=dict(server_id="http://FakedUrl:5988",
                            listener_url="httpx",
                            owned=True,
                            destination_id='id1'),
            subscription_attrs=None,
            remove_destinations=None,
            remove_filters=None,
            remove_subscriptions=None,
            remove_server_attrs=None,
            exp_result=dict(server_id="http://FakedUrl:5988")
        ),
        ValueError, None, OK
    ),
    (
        "Add listener_dest with invalid persistence_type integer 4",
        dict(
            submgr_id="ValidID",
            connection_attrs=dict(url=None),
            filter_attrs=None,
            dest_attrs=dict(server_id="http://FakedUrl:5988",
                            listener_url="http://localhost:5000",
                            owned=True,
                            destination_id='id1',
                            persistence_type=4),
            subscription_attrs=None,
            remove_destinations=None,
            remove_filters=None,
            remove_subscriptions=None,
            remove_server_attrs=None,
            exp_result=dict(server_id="http://FakedUrl:5988")
        ),
        ValueError, None, OK
    ),
    (
        "Add duplicate destination. fails because Name property duplicate",
        dict(
            submgr_id="ValidID",
            connection_attrs=dict(url=None),
            filter_attrs=None,
            dest_attrs=[dict(server_id="http://FakedUrl:5988",
                             listener_url="http://localhost:5000",
                             owned=True,
                             destination_id='id1',
                             persistence_type='transient'),
                        dict(server_id="http://FakedUrl:5988",
                             listener_url="http://localhost:5000",
                             owned=True,
                             destination_id='id1',
                             persistence_type='transient')],
            subscription_attrs=None,
            remove_destinations=None,
            remove_filters=None,
            remove_subscriptions=None,
            remove_server_attrs=None,
            exp_result=dict(server_id="http://FakedUrl:5988")
        ),
        CIMError, None, OK
    ),
    (
        "Add duplicate destination. new Filter_id returns existing instance",
        dict(
            submgr_id="ValidID",
            connection_attrs=dict(url=None),
            filter_attrs=None,
            dest_attrs=[dict(server_id="http://FakedUrl:5988",
                             listener_url="http://localhost:5000",
                             owned=True,
                             destination_id='id1',
                             persistence_type='transient'),
                        dict(server_id="http://FakedUrl:5988",
                             listener_url="http://localhost:5000",
                             owned=True,
                             destination_id='id12',
                             persistence_type='transient')],
            subscription_attrs=None,
            remove_destinations=None,
            remove_filters=None,
            remove_subscriptions=None,
            remove_server_attrs=None,
            # test only one dest exists
            exp_result=dict(server_id="http://FakedUrl:5988",
                            listener_count=1, )
        ),
        None, None, OK
    ),
    (
        "Add listener_dest with invalid persistence_type value 'blah",
        dict(
            submgr_id="ValidID",
            connection_attrs=dict(url=None),
            filter_attrs=None,
            dest_attrs=dict(server_id="http://FakedUrl:5988",
                            listener_url="http://localhost:5000",
                            owned=True,
                            destination_id='id1',
                            persistence_type='blah'),
            subscription_attrs=None,
            remove_destinations=None,
            remove_filters=None,
            remove_subscriptions=None,
            remove_server_attrs=None,
            exp_result=dict(server_id="http://FakedUrl:5988")
        ),
        ValueError, None, OK
    ),
    (
        "Add listener_dest with valid persistence_type string, invalid value",
        dict(
            submgr_id="ValidID",
            connection_attrs=dict(url=None),
            filter_attrs=None,
            dest_attrs=dict(server_id="http://FakedUrl:5988",
                            listener_url="http://localhost:5000",
                            owned=True,
                            destination_id='id1',
                            persistence_type="fred"),
            subscription_attrs=None,
            remove_destinations=None,
            remove_filters=None,
            remove_subscriptions=None,
            remove_server_attrs=None,
            exp_result=dict(server_id="http://FakedUrl:5988")
        ),
        ValueError, None, OK
    ),
    (
        "Add listener_dest with valid persistence_type 'transient",
        dict(
            submgr_id="ValidID",
            connection_attrs=dict(url=None),
            filter_attrs=None,
            dest_attrs=dict(server_id="http://FakedUrl:5988",
                            listener_url="http://localhost:5000",
                            owned=False,
                            name='name1',
                            persistence_type='transient'),
            subscription_attrs=None,
            remove_destinations=None,
            remove_filters=None,
            remove_subscriptions=None,
            remove_server_attrs=None,
            exp_result=dict(server_id="http://FakedUrl:5988",
                            listener_count=1,
                            dest_props=[0, [('PersistenceType', 3)]])
        ),
        None, None, OK
    ),
    (
        "Add listener_dest with valid persistence_type 'permanent",
        dict(
            submgr_id="ValidID",
            connection_attrs=dict(url=None),
            filter_attrs=None,
            dest_attrs=dict(server_id="http://FakedUrl:5988",
                            listener_url="http://localhost:5000",
                            owned=False,
                            name='name1',
                            persistence_type='permanent'),
            subscription_attrs=None,
            remove_destinations=None,
            remove_filters=None,
            remove_subscriptions=None,
            remove_server_attrs=None,
            exp_result=dict(server_id="http://FakedUrl:5988",
                            listener_count=1,
                            dest_props=[0, [('PersistenceType', 2)]])
        ),
        None, None, OK
    ),
    (
        "Add listener_dest without persistence_type and owned.",
        dict(
            submgr_id="ValidID",
            connection_attrs=dict(url=None),
            filter_attrs=None,
            dest_attrs=dict(server_id="http://FakedUrl:5988",
                            listener_url="http://localhost:5000",
                            owned=True,
                            destination_id='id1'),
            subscription_attrs=None,
            remove_destinations=None,
            remove_filters=None,
            remove_subscriptions=None,
            remove_server_attrs=None,
            exp_result=dict(server_id="http://FakedUrl:5988",
                            listener_count=1,
                            dest_props=[0, [('PersistenceType', 3)]])
        ),
        None, None, OK
    ),
    (
        "Add listener_dest without persistence_type owned=False.",
        dict(
            submgr_id="ValidID",
            connection_attrs=dict(url=None),
            filter_attrs=None,
            dest_attrs=dict(server_id="http://FakedUrl:5988",
                            listener_url="http://localhost:5000",
                            owned=False,
                            name='name1'),
            subscription_attrs=None,
            remove_destinations=None,
            remove_filters=None,
            remove_subscriptions=None,
            remove_server_attrs=None,
            exp_result=dict(server_id="http://FakedUrl:5988",
                            listener_count=1,
                            dest_props=[0, [('PersistenceType', 2)]])
        ),
        None, None, OK
    ),
    (
        "Add a single valid subscription",
        dict(
            submgr_id="ValidID",
            connection_attrs=dict(url=None),
            dest_attrs=dict(server_id="http://FakedUrl:5988",
                            listener_url="http://localhost:5000",
                            owned=True,
                            destination_id='id1'),
            filter_attrs=dict(server_id="http://FakedUrl:5988",
                              source_namespaces='root/interop',
                              query="SELECT * from blah",
                              query_language='WQL',
                              owned=True,
                              filter_id="Filter1", name=None),
            subscription_attrs=dict(server_id="http://FakedUrl:5988",
                                    filter_path=0,
                                    destination_paths=0,
                                    owned=True),
            remove_destinations=None,
            remove_filters=None,
            remove_subscriptions=None,
            remove_server_attrs=None,
            exp_result=dict(server_id="http://FakedUrl:5988",
                            listener_count=1,
                            filter_count=1,
                            subscription_count=1)
        ),
        None, None, OK
    ),
    (
        "Remove listener with existing references",
        dict(
            submgr_id="ValidID",
            connection_attrs=dict(url=None),
            dest_attrs=dict(server_id="http://FakedUrl:5988",
                            listener_url="http://localhost:5000",
                            owned=True,
                            destination_id='id1'),
            filter_attrs=dict(server_id="http://FakedUrl:5988",
                              source_namespaces='root/interop',
                              query="SELECT * from blah",
                              query_language='WQL',
                              owned=True,
                              filter_id="Filter1", name=None),
            subscription_attrs=dict(server_id="http://FakedUrl:5988",
                                    filter_path=0,
                                    destination_paths=0,
                                    owned=True),
            remove_destinations=0,
            remove_filters=None,
            remove_subscriptions=None,
            remove_server_attrs=None,
            exp_result=dict(server_id="http://FakedUrl:5988",
                            listener_count=1,
                            filter_count=1,
                            subscription_count=1)
        ),
        CIMError, None, OK
    ),
    (
        "Add a single not_owned subscription with owned filter fails",
        dict(
            submgr_id="ValidID",
            connection_attrs=dict(url=None),
            dest_attrs=dict(server_id="http://FakedUrl:5988",
                            listener_url="http://localhost:5000",
                            owned=True,
                            destination_id='id1'),
            filter_attrs=dict(server_id="http://FakedUrl:5988",
                              source_namespaces='root/interop',
                              query="SELECT * from blah",
                              query_language='WQL',
                              owned=True,
                              filter_id="Filter1", name=None),
            subscription_attrs=dict(server_id="http://FakedUrl:5988",
                                    filter_path=0,
                                    destination_paths=0,
                                    owned=False),
            remove_destinations=None,
            remove_filters=None,
            remove_subscriptions=None,
            remove_server_attrs=None,
            exp_result=dict(server_id="http://FakedUrl:5988",
                            listener_count=1,
                            filter_count=1,
                            subscription_count=1)
        ),
        ValueError, None, OK
    ),
    (
        "Add a single not_owned subscription with owned destination fails",
        dict(
            submgr_id="ValidID",
            connection_attrs=dict(url=None),
            dest_attrs=dict(server_id="http://FakedUrl:5988",
                            listener_url="http://localhost:5000",
                            owned=True,
                            destination_id='id1'),
            filter_attrs=dict(server_id="http://FakedUrl:5988",
                              source_namespaces='root/interop',
                              query="SELECT * from blah",
                              query_language='WQL',
                              owned=False,
                              filter_id="NotOwnedFilter1", name=None),
            subscription_attrs=dict(server_id="http://FakedUrl:5988",
                                    filter_path=0,
                                    destination_paths=0,
                                    owned=False),
            remove_destinations=None,
            remove_filters=None,
            remove_subscriptions=None,
            remove_server_attrs=None,
            exp_result=dict(server_id="http://FakedUrl:5988",
                            listener_count=1,
                            filter_count=1,
                            subscription_count=1)
        ),
        ValueError, None, OK
    ),
    (
        "Test remove destination succeeds",
        dict(
            submgr_id="ValidID",
            connection_attrs=dict(url=None),
            dest_attrs=dict(server_id="http://FakedUrl:5988",
                            listener_url="http://localhost:5000",
                            owned=True,
                            destination_id='id1'),
            filter_attrs=None,
            subscription_attrs=None,
            remove_destinations=True,
            remove_filters=None,
            remove_subscriptions=None,
            remove_server_attrs=None,
            exp_result=dict(server_id="http://FakedUrl:5988",
                            listener_count=1,
                            final_listener_count=0)
        ),
        None, None, OK
    ),
    (
        "Test remove destination with subscriptions fails",
        dict(
            submgr_id="ValidID",
            connection_attrs=dict(url=None),
            dest_attrs=dict(server_id="http://FakedUrl:5988",
                            listener_url="http://localhost:5000",
                            owned=True,
                            destination_id='id1'),
            filter_attrs=dict(server_id="http://FakedUrl:5988",
                              source_namespaces='root/interop',
                              query="SELECT * from blah",
                              query_language='WQL',
                              owned=True,
                              filter_id="Filter1", name=None),
            subscription_attrs=dict(server_id="http://FakedUrl:5988",
                                    filter_path=0,
                                    destination_paths=0,
                                    owned=True),
            remove_destinations=True,
            remove_filters=None,
            remove_subscriptions=None,
            remove_server_attrs=None,
            exp_result=dict(server_id="http://FakedUrl:5988",
                            listener_count=1,
                            filter_count=1,
                            subscription_count=1)
        ),
        CIMError, None, OK
    ),
    (
        "Test remove filter succeeds without subscription",
        dict(
            submgr_id="ValidID",
            connection_attrs=dict(url=None),
            dest_attrs=None,
            filter_attrs=dict(server_id="http://FakedUrl:5988",
                              source_namespaces='root/interop',
                              query="SELECT * from blah",
                              query_language='WQL',
                              owned=True,
                              filter_id="Filter1", name=None),
            subscription_attrs=None,
            remove_destinations=True,
            remove_filters=[0],  # Removing this filter fails
            remove_subscriptions=None,
            remove_server_attrs=None,
            exp_result=dict(server_id="http://FakedUrl:5988",
                            filter_count=1,
                            final_filtercount=1)
        ),
        None, None, OK
    ),
    (
        "Test remove filter fails with subscription",
        dict(
            submgr_id="ValidID",
            connection_attrs=dict(url=None),
            dest_attrs=dict(server_id="http://FakedUrl:5988",
                            listener_url="http://localhost:5000",
                            owned=True,
                            destination_id='id1'),
            filter_attrs=dict(server_id="http://FakedUrl:5988",
                              source_namespaces='root/interop',
                              query="SELECT * from blah",
                              query_language='WQL',
                              owned=True,
                              filter_id="Filter1", name=None),
            subscription_attrs=dict(server_id="http://FakedUrl:5988",
                                    filter_path=0,
                                    destination_paths=0,
                                    owned=True),
            remove_destinations=True,
            remove_filters=[0],  # Removing this filter fails
            remove_subscriptions=None,
            remove_server_attrs=None,
            exp_result=dict(server_id="http://FakedUrl:5988",
                            listener_count=1,
                            filter_count=1,
                            subscription_count=1)
        ),
        CIMError, None, OK
    ),
    (
        "Test remove destination with subscription fails",
        dict(
            submgr_id="ValidID",
            connection_attrs=dict(url=None),
            dest_attrs=dict(server_id="http://FakedUrl:5988",
                            listener_url="http://localhost:5000",
                            owned=True,
                            destination_id='id1'),
            filter_attrs=dict(server_id="http://FakedUrl:5988",
                              source_namespaces='root/interop',
                              query="SELECT * from blah",
                              query_language='WQL',
                              owned=True,
                              filter_id="Filter1", name=None),
            subscription_attrs=dict(server_id="http://FakedUrl:5988",
                                    filter_path=0,
                                    destination_paths=0,
                                    owned=True),
            remove_destinations=True,
            remove_filters=[0],  # Removing this filter fails
            remove_subscriptions=None,
            remove_server_attrs=None,
            exp_result=dict(server_id="http://FakedUrl:5988",
                            listener_count=1,
                            filter_count=1,
                            subscription_count=1)
        ),
        CIMError, None, OK
    ),
    (
        "Test remove subscriptions succeeds",
        dict(
            submgr_id="ValidID",
            connection_attrs=dict(url=None),
            dest_attrs=dict(server_id="http://FakedUrl:5988",
                            listener_url="http://localhost:5000",
                            owned=True,
                            destination_id='id1'),
            filter_attrs=dict(server_id="http://FakedUrl:5988",
                              source_namespaces='root/interop',
                              query="SELECT * from blah",
                              query_language='WQL',
                              owned=True,
                              filter_id="Filter1", name=None),
            subscription_attrs=dict(server_id="http://FakedUrl:5988",
                                    filter_path=0,
                                    destination_paths=0,
                                    owned=True),
            remove_destinations=None,
            remove_filters=None,
            remove_subscriptions=True,
            remove_server_attrs=None,
            exp_result=dict(server_id="http://FakedUrl:5988",
                            listener_count=1,
                            filter_count=1,
                            subscription_count=1,
                            final_subscription_count=0,
                            final_filter_count=1,
                            final_listener_count=1)
        ),
        None, None, OK
    ),

    # Tests that need to be added
    # Add server where param is not WBEMServer
    # add not_owned filters and destinations
    # NOTE: Eventually this should replace most of the unit tests.
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_SUBMGR)
@simplified_test_function
def test_subscriptionmanager(testcase, submgr_id, connection_attrs,
                             filter_attrs, dest_attrs, subscription_attrs,
                             remove_destinations, remove_filters,
                             remove_subscriptions,
                             remove_server_attrs, exp_result):
    # pylint: disable=unused-argument
    """
    Tests all of the methods of the subscription manager.
    """
    skip_if_moftab_regenerated()

    def define_connection(connection_attrs):
        """
        Create a new mock connection with the attributes defined in
        connection_attrs. and the subscription providers.
        This method also does an add_server with the created mock server.
        Returns:
            returns the server_id associated with the connection.
        """
        mock_server = WbemServerMock(
            interop_ns='interop',
            server_mock_data=SUBSCRIPTION_WBEM_SERVER_MOCK_DICT,
            **connection_attrs)
        return submgr.add_server(mock_server.wbem_server)

    # The code to be tested starts here but encompasses most of this function
    # depending on the function parameters  We did not set a specific place
    # above which there should never be an exception. Depending on the tests,
    # exceptions could occur throughout the code below.
    submgr = WBEMSubscriptionManager(submgr_id)

    # Test result arrays for one or more server_ids. Each of the add and
    # remove methods will insert the results into these lists for validation
    # of the returns from these methods.
    server_id = None
    server_ids = []
    added_filters = []
    added_destinations = []
    added_subscriptions = []

    # The following code adds connections and filters
    # If connection_attrs exists, set up the server and save the server_ids
    # for later use in the test
    if connection_attrs:
        if isinstance(connection_attrs, list):
            for connection_attr in connection_attrs:
                server_ids.append(define_connection(connection_attr))
        else:
            server_id = define_connection(connection_attrs)

    # Test for add filter, adds one or more filters
    if filter_attrs:
        if isinstance(filter_attrs, dict):
            filter_attrs = [filter_attrs]
        for attr in filter_attrs:
            added_filters.append(submgr.add_filter(**attr))

    # Test for add destinations. Adds one or more destinations
    if dest_attrs:
        if isinstance(dest_attrs, dict):
            dest_attrs = [dest_attrs]
        for attr in dest_attrs:
            added_destinations.append(submgr.add_destination(**attr))

    # Test for adding subscriptions based on the attributes in the dest
    # definition. Here, the filter and dest components are integers defining
    # the entry in the already created object lists to use for the path
    # in the subscription.
    if subscription_attrs:
        if isinstance(subscription_attrs, dict):
            subscription_attrs = [subscription_attrs]
        for attr in subscription_attrs:
            if isinstance(attr['filter_path'], int):
                attr['filter_path'] = added_filters[attr['filter_path']].path
            if isinstance(attr['destination_paths'], int):
                attr['destination_paths'] = \
                    added_destinations[attr['destination_paths']].path
            elif isinstance(attr['destination_paths'], list):
                dest_paths = []
                for item in attr['destination_paths']:
                    dest_paths.append(
                        added_destinations[item].path)
                attr['destination_paths'] = dest_paths
            rslts = submgr.add_subscriptions(**attr)
            added_subscriptions.extend(rslts)

    if "server_id" in exp_result:
        if isinstance(exp_result['server_id'], list):
            assert set(server_ids) == set(exp_result['server_id'])
        else:
            assert server_id == exp_result['server_id']

    # test instances created before any remove requests.
    if 'listener_count' in exp_result:
        all_dests = submgr.get_all_destinations(server_id)
        assert len(all_dests) == exp_result['listener_count']

        owned_dests = submgr.get_owned_destinations(server_id)
        dest_prefix = 'pywbemdestination:{0}:'.format(submgr_id,)
        owned = [d for d in all_dests if d['Name'].startswith(dest_prefix)]
        assert set(owned) == set(owned_dests)

    if 'filter_count' in exp_result:
        all_filters = submgr.get_all_filters(server_id)
        assert len(all_filters) == exp_result['filter_count']

    if 'subscription_count' in exp_result:
        all_subs = submgr.get_all_subscriptions(server_id)
        assert len(all_subs) == exp_result['subscription_count']

    # Test for properties in instances
    if 'dest_props' in exp_result:
        dest_props = exp_result['dest_props']
        created_instance = added_destinations[dest_props[0]]
        props = dest_props[1]
        for prop, value in props:
            # If None expect either property with None or no property
            if value is None:
                if prop in created_instance:
                    assert created_instance[prop] == value
            else:
                assert created_instance[prop] == value

    if 'filter_props' in exp_result:
        filter_props = exp_result['filter_props']
        created_instance = added_filters[filter_props[0]]
        props = filter_props[1]
        for prop, value in props:
            # If None expect either property with None or no property
            if value is None:
                if prop in created_instance:
                    assert created_instance[prop] == value
            else:
                if created_instance[prop] != value:
                    print("THEERROR\n{}".format(created_instance.tomof()))
                assert created_instance[prop] == value

    # The removal methods are executed after all others methods defined for
    # the test and after tests on the results of other method execution
    if remove_destinations is not None:
        dest_paths = [inst.path for inst in added_destinations]
        if isinstance(remove_destinations, bool):
            assert remove_destinations
            submgr.remove_destinations(server_id, dest_paths)
            result = 0
        elif isinstance(remove_destinations, int):
            submgr.remove_destinations(server_id,
                                       dest_paths[remove_destinations])
            result = len(added_destinations) - 1
        elif isinstance(remove_destinations, list):
            removal_paths = [added_destinations[i].path for i in
                             remove_destinations]
            submgr.remove_destinations(server_id, removal_paths)
            result = len(added_destinations) - len(remove_destinations)
        assert len(submgr.get_all_destinations(server_id)) == result

    if remove_filters is not None:
        filter_paths = [inst.path for inst in added_filters]
        if isinstance(remove_filters, bool):
            assert remove_filters
            submgr.remove_filter(server_id, filter_paths)
            result = 0
        elif isinstance(remove_filters, int):
            submgr.remove_filter(server_id, filter_paths[remove_filters])
            result = len(added_filters) - 1
        elif isinstance(remove_filters, list):
            # Must remove one by one
            for item in remove_filters:
                submgr.remove_filter(server_id, filter_paths[item])
            result = len(added_filters) - len(remove_filters)
        assert len(submgr.get_all_filters(server_id)) == result

    if remove_subscriptions is not None:
        sub_paths = [inst.path for inst in added_subscriptions]
        if isinstance(remove_subscriptions, bool):
            assert remove_subscriptions
            submgr.remove_subscriptions(server_id, sub_paths)
            result = 0
        elif isinstance(remove_subscriptions, int):
            submgr.remove_subscriptions(server_id,
                                        sub_paths[remove_destinations])
            result = len(sub_paths) - 1
        elif isinstance(remove_subscriptions, list):
            removal_list = [added_subscriptions[i].path for i in
                            remove_subscriptions]
            submgr.remove_subscriptions(server_id, removal_list)
            result = len(sub_paths) - len(remove_subscriptions)
        assert len(submgr.get_all_subscriptions(server_id)) == result

    if remove_server_attrs:
        submgr.remove_server(remove_server_attrs)

        # The server_id should be missing and we get ValueError
        try:
            submgr.get_all_subscriptions(remove_server_attrs)
            assert False
        except ValueError:
            pass

    # Test for final counts after any remove test definitions
    if 'final_listenercount' in exp_result:
        assert len(submgr.get_all_destinations(server_id)) == \
            exp_result['final_listener_count']

    if 'final_filter_count' in exp_result:
        assert len(submgr.get_all_filters(server_id)) == \
            exp_result['final_filter_count']

    if 'final_subscription_count' in exp_result:
        assert len(submgr.get_all_subscriptions(server_id)) == \
            exp_result['final_subscription_count']


TESTCASES_SUBMGR_MODIFY = [

    # Testcases for Subscription Tests multiple valid and invalid options
    # in __init__, add_server, add_filter, add_destinations

    # Each list item is a testcase tuple with these items:
    # * desc: Short testcase description.
    # * kwargs: Keyword arguments for the test function:
    #   * submgr_id: submgr id
    #   * connection_attrs: FakedWBEMConnection attributes. this variable causes
    #     an add_server to be executed. If it is a list, multiple
    #     a server is added for each dict in the list. The attributes of
    #     the FakedWBEMConnection can be set as attributes. Note: this test
    #     already sets the interop namespace automatically
    #   * filter_attrs: dictionary of attributes for add_filter. If it is
    #     a list, one filter is added for each dict in the list
    #   * dest_attrs: dictionary of attributes for add_destination().
    #   * modify_dest: dictionary of attributes for modify_instance of listener
    #     destination.
    #   * subscription_attrs: dictionary or list dictionaries where each
    #     dictionary is a dictionary that defines either the attributes of
    #     the subscription or to make it simpler to define tests, an integer
    #     for the position in the appropriate list for the required
    #     filter or destination.
    #   * modify_filter_attrs: defines inst/properties properties to modify
    #     where instances are modified on the server external to
    #     SubscriptionManager (i.e. directly with conn.ModifyInstance)
    #     The attributes are:
    #       1. The index to the filter_dest to modify
    #       2. dict of properties to modify
    #   * modify_listener_dest_attrs: defines inst/properties properties to
    #     modify. The attributes are:
    #       1. The index to the listener_dest to modify
    #       2. dict of properties to modify
    #   * modify_subscription_attrs: defines inst/properties properties to
    #     modify. The attributes are:
    #       1. The index to the subscription_dest to modify
    #       2. dict of properties to modify
    #   * exp_result: Expected dictionary items, for validation. This includes:
    #       * server_id - The expected server_id
    #       * listener_count - Count of expected destinations
    #       * filter_count - Count of expected filters.
    #       * dest_props: TODO: Will get doc from later pr
    #       * TODO: Add validation for filter, subscriptions
    #       * subscription_count - Count of expected subscriptions.
    #
    # * exp_exc_types: Expected exception type(s), or None.
    # * exp_warn_types: Expected warning type(s), or None.
    # * condition: Boolean condition for testcase to run, or 'pdb' for debugger

    (
        "Modify fails, No modify property returns not supported from provider",
        dict(
            submgr_id="ValidID",
            connection_attrs=dict(url=None),
            filter_attrs=None,
            dest_attrs=dict(server_id="http://FakedUrl:5988",
                            listener_url="http://localhost:5000",
                            owned=True,
                            destination_id='id1'),
            subscription_attrs=None,
            modify_filter_attrs=None,
            modify_dest_attrs=[0, []],
            modify_subscription_attrs=None,
            exp_result=dict(server_id="http://FakedUrl:5988",
                            listener_count=1)
        ),
        CIMError, None, FAIL
    ),
    (
        "Modify OK. Property modified",
        dict(
            submgr_id="ValidID",
            connection_attrs=dict(url=None),
            filter_attrs=dict(server_id="http://FakedUrl:5988",
                              source_namespaces='root/interop',
                              query="SELECT * from blah",
                              query_language='WQL',
                              owned=True,
                              filter_id="Filter1", name=None),
            dest_attrs=dict(server_id="http://FakedUrl:5988",
                            listener_url="http://localhost:5000",
                            owned=True,
                            destination_id='id1'),
            subscription_attrs=None,
            modify_dest_attrs=None,
            modify_filter_attrs=[0, [('IndividualSubscriptionSupported',
                                      True)]],
            modify_subscription_attrs=None,
            exp_result=dict(server_id="http://FakedUrl:5988",
                            listener_count=1,
                            filter_props=[0,
                                          [('IndividualSubscriptionSupported',
                                            True)]]),
        ),
        None, None, OK
    ),
    (
        "Modify fails, Subscription exists",
        dict(
            submgr_id="ValidID",
            connection_attrs=dict(url=None),
            filter_attrs=dict(server_id="http://FakedUrl:5988",
                              source_namespaces='root/interop',
                              query="SELECT * from blah",
                              query_language='WQL',
                              owned=True,
                              filter_id="Filter1", name=None),
            dest_attrs=dict(server_id="http://FakedUrl:5988",
                            listener_url="http://localhost:5000",
                            owned=True,
                            destination_id='id1'),
            subscription_attrs=dict(server_id="http://FakedUrl:5988",
                                    filter_path=0,
                                    destination_paths=0,
                                    owned=True),
            modify_dest_attrs=None,
            modify_filter_attrs=[0, [('IndividualSubscriptionSupported',
                                      True)]],
            modify_subscription_attrs=None,
            exp_result=dict(server_id="http://FakedUrl:5988",
                            listener_count=1,
                            filter_props=[0,
                                          [('IndividualSubscriptionSupported',
                                            True)]]),
        ),
        CIMError, None, OK
    ),
    (
        "Modify fails, Filter query language, mock provider forbids change",
        dict(
            submgr_id="ValidID",
            connection_attrs=dict(url=None),
            filter_attrs=dict(server_id="http://FakedUrl:5988",
                              source_namespaces='root/interop',
                              query="SELECT * from blah",
                              query_language='WQL',
                              owned=True,
                              filter_id="Filter1", name=None),
            dest_attrs=dict(server_id="http://FakedUrl:5988",
                            listener_url="http://localhost:5000",
                            owned=True,
                            destination_id='id1'),
            subscription_attrs=dict(server_id="http://FakedUrl:5988",
                                    filter_path=0,
                                    destination_paths=0,
                                    owned=True),
            modify_dest_attrs=None,
            modify_filter_attrs=[0, [('QueryLanguage',
                                      'WQL')]],
            modify_subscription_attrs=None,
            exp_result=dict(server_id="http://FakedUrl:5988",
                            listener_count=1,
                            filter_props=[0,
                                          [('QueryLanguage',
                                            'WQL')]]),
        ),
        CIMError, None, OK
    ),

    # TODO: The following tests are not in the test list.
    # 1. Test for missing required_property. This one very difficult because
    #    list of required properties is also properties always set by
    #    SubscriptionManager
    # 2. Invalid Namespace on __init__ of mock subscription providers
    # 3. __repr__ for each mock subscription providers
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_SUBMGR_MODIFY)
@simplified_test_function
def test_submgr_modify(testcase, submgr_id, connection_attrs,
                       filter_attrs, dest_attrs, subscription_attrs,
                       modify_filter_attrs, modify_dest_attrs,
                       modify_subscription_attrs, exp_result):
    # pylint: disable=unused-argument
    """
    Tests the ability to modify instances of the subscription classes in the
    pywbem_mock subscription providers. This creates filters, listener
    destinations, and subscriptions and then tests with ModifyInstance.
    Note: The subscription manager does not include ModifyInstance methods
    for the indication subscription classes.
    """
    skip_if_moftab_regenerated()

    def define_connection(connection_attrs):
        """
        Create a new mock connection with the attributes defined in
        connection_attrs.
        This method also does an add_server with the created mock server.
        Returns:
            returns the server_id associated with the connection and the
            connection object.
        """
        mock_server = WbemServerMock(
            interop_ns='interop',
            server_mock_data=SUBSCRIPTION_WBEM_SERVER_MOCK_DICT,
            **connection_attrs)
        conn = mock_server.wbem_server.conn
        return (submgr.add_server(mock_server.wbem_server), conn)

    # The code to be tested starts here but encompasses most of this function
    # depending on the function parameters  We did not set a specific place
    # above which there should never be an exception. Depending on the tests,
    # exceptions could occur throughout the code below.
    submgr = WBEMSubscriptionManager(submgr_id)

    # Test result arrays for one or more server_ids. Each of the add and
    # remove methods will insert the results into these lists for validation
    # of the returns from these methods.
    server_id = None
    server_ids = []
    server_conn = None
    added_filters = []
    added_destinations = []
    added_subscriptions = []

    # The following code adds connections and filters
    # If connection_attrs exists, set up the server and save the server_ids
    # for later use in the test
    if connection_attrs:
        if isinstance(connection_attrs, list):
            # DO not allow multiple connections for this test.
            assert False
            for connection_attr in connection_attrs:
                server_ids.append(define_connection(connection_attr))
        else:
            server_id, server_conn = define_connection(connection_attrs)

    # Test for add filter, adds one or more filters
    if filter_attrs:
        if isinstance(filter_attrs, dict):
            filter_attrs = [filter_attrs]
        for attr in filter_attrs:
            added_filters.append(submgr.add_filter(**attr))

    # Test for add destinations.

    if dest_attrs:
        if isinstance(dest_attrs, dict):
            dest_attrs = [dest_attrs]
        for attr in dest_attrs:
            added_destinations.append(submgr.add_destination(**attr))

    # Test for adding subscriptions based on the attributes in the dest
    # definition. Here, the filter and dest components are integers defining
    # The entry in the already created object lists to use for the path
    # in the subscription.
    if subscription_attrs:
        if isinstance(subscription_attrs, dict):
            subscription_attrs = [subscription_attrs]
        for attr in subscription_attrs:
            if isinstance(attr['filter_path'], int):
                attr['filter_path'] = added_filters[attr['filter_path']].path
            if isinstance(attr['destination_paths'], int):
                attr['destination_paths'] = \
                    added_destinations[attr['destination_paths']].path
            elif isinstance(attr['destination_paths'], list):
                dest_paths = []
                for item in attr['destination_paths']:
                    dest_paths.append(
                        added_destinations[item].path)
                attr['destination_paths'] = dest_paths
            rslts = submgr.add_subscriptions(**attr)
            added_subscriptions.extend(rslts)

    if modify_dest_attrs:
        instance_to_modify = added_destinations[modify_dest_attrs[0]]
        modified_instance = instance_to_modify.copy()
        modified_instance.update(modify_dest_attrs[1])
        pl = [p[0] for p in modify_dest_attrs[1]]
        server_conn.ModifyInstance(modified_instance, PropertyList=pl)

    if modify_filter_attrs:
        instance_to_modify = added_filters[modify_filter_attrs[0]]
        modified_instance = instance_to_modify.copy()
        modified_instance.update(modify_filter_attrs[1])
        pl = [p[0] for p in modify_filter_attrs[1]]
        server_conn.ModifyInstance(modified_instance, PropertyList=pl)

    if modify_subscription_attrs:
        instance_to_modify = added_subscriptions[modify_subscription_attrs[0]]
        modified_instance = instance_to_modify.copy()
        modified_instance.update(modify_subscription_attrs[1])
        pl = [p[0] for p in modify_subscription_attrs[1]]
        server_conn.ModifyInstance(modified_instance)

    if 'dest_props' in exp_result:
        dest_props = exp_result['dest_props']
        orig_instance = added_destinations[dest_props[0]]
        updated_instance = server_conn.GetInstance(orig_instance.path)
        props = dest_props[1]
        for prop, value in props:
            assert updated_instance[prop] == value

    # test for listener_destinations created
    if 'listener_count' in exp_result:
        all_dests = submgr.get_all_destinations(server_id)
        assert len(all_dests) == exp_result['listener_count']

        owned_dests = submgr.get_owned_destinations(server_id)

        dest_prefix = 'pywbemdestination:{0}:'.format(submgr_id,)
        owned = [d for d in all_dests if d['Name'].startswith(dest_prefix)]
        assert set(owned) == set(owned_dests)

    if 'filter_count' in exp_result:
        all_filters = submgr.get_all_filters(server_id)
        assert len(all_filters) == exp_result['filter_count']

    if 'subscription_count' in exp_result:
        all_subs = submgr.get_all_subscriptions(server_id)
        assert len(all_subs) == exp_result['subscription_count']
