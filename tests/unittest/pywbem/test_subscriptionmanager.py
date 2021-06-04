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
from socket import getfqdn
import pytest

from ...utils import skip_if_moftab_regenerated
from ..utils.dmtf_mof_schema_def import DMTF_TEST_SCHEMA_VER
from ..utils.wbemserver_mock import WbemServerMock
from ..utils.pytest_extensions import simplified_test_function

# pylint: disable=wrong-import-position, wrong-import-order, invalid-name
from ...utils import import_installed
pywbem = import_installed('pywbem')
from pywbem import WBEMServer, CIMClassName, WBEMSubscriptionManager, \
    CIMInstance  # noqa: E402
from pywbem._subscription_manager import SUBSCRIPTION_CLASSNAME, \
    DESTINATION_CLASSNAME, FILTER_CLASSNAME  # noqa: E402
from pywbem_mock import OBJECTMANAGERNAME, \
    SYSTEMNAME  # noqa: E402
pywbem_mock = import_installed('pywbem_mock')
from pywbem_mock import DMTFCIMSchema  # noqa: E402
# pylint: enable=wrong-import-position, wrong-import-order, invalid-name


# Location of DMTF schema directory used by all tests.
# This directory is permanent and should not be removed.
TESTSUITE_SCHEMA_DIR = os.path.join('tests', 'schema')

VERBOSE = False

# The following dictionary is the mock WBEM server configuration for the
# WBEMServerMock class.  It defines a mock WBEM server that is build with
# defined class schemas, classnames, etc.
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
    # TODO: We may expand this for more scoping tests.
    'central-instances': [],
    'scoping-instances': []
}


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

        server = WbemServerMock(interop_ns='interop')
        # pylint: disable=attribute-defined-outside-init
        self.conn = server.wbem_server.conn
        classnames = ['CIM_IndicationSubscription',
                      'CIM_ListenerDestinationCIMXML',
                      'CIM_IndicationFilter', ]

        schema = DMTFCIMSchema(DMTF_TEST_SCHEMA_VER, TESTSUITE_SCHEMA_DIR,
                               verbose=False)

        self.conn.compile_schema_classes(classnames, schema.schema_pragma_file,
                                         verbose=False)

    @staticmethod
    def inst_from_classname(conn, class_name, namespace=None,
                            property_list=None,
                            property_values=None,
                            include_missing_properties=True,
                            include_path=True):
        # TODO AM 8/18 The inst_from_classname() method is not used.
        # NOTE: This method was never added to pywbem apparently
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

    def add_filter(self, sub_mgr, server_id, filter_id, owned=True):
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

        filter_ = sub_mgr.add_filter(server_id,
                                     self.test_class_namespace,
                                     self.test_query,
                                     query_language="DMTF:CQL",
                                     filter_id=filter_id,
                                     owned=owned)
        return filter_.path

    def get_objects_from_server(self):
        """
        Using Server class, get count of Filters, Subscriptions, Destinations
        from server as confirmation outside of SubscriptionManagerCode.
        """
        this_host = getfqdn()

        server = WBEMServer(self.conn)

        dest_name_pattern = re.compile(r'^pywbemdestination:')
        dest_insts = server.conn.EnumerateInstances(
            DESTINATION_CLASSNAME, namespace=server.interop_ns)
        valid_dests = []
        for inst in dest_insts:
            if re.match(dest_name_pattern, inst.path.keybindings['Name']) \
                    and inst.path.keybindings['SystemName'] == this_host:
                valid_dests.append(inst)

        filter_instances = server.conn.EnumerateInstances(
            FILTER_CLASSNAME, namespace=server.interop_ns)
        valid_filters = []
        filter_name_pattern = re.compile(r'^pywbemfilter')
        for inst in filter_instances:
            if re.match(filter_name_pattern, inst.path.keybindings['Name']) \
                    and inst.path.keybindings['SystemName'] == this_host:
                valid_filters.append(inst)

        filter_paths = [inst.path for inst in valid_filters]
        destination_paths = [inst.path for inst in valid_dests]

        sub_insts = server.conn.EnumerateInstances(
            SUBSCRIPTION_CLASSNAME, namespace=server.interop_ns)
        valid_subscriptions = []
        for inst in sub_insts:
            if inst.path.keybindings['Filter'] in filter_paths \
                    or inst.path.keybindings['Handler'] in destination_paths:
                valid_subscriptions.append(inst)

        if VERBOSE:
            print('All objects: filters=%s dests=%s subs=%s' %
                  (len(filter_instances),
                   len(dest_insts), len(sub_insts)))
            print('Pywbem objects: filters=%s dests=%s subs=%s' %
                  (len(filter_paths), len(destination_paths),
                   len(valid_subscriptions)))

        return sum([len(filter_paths), len(destination_paths),
                    len(valid_subscriptions)])

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

    def get_object_count(self, sub_mgr, server_id):
        """
        Return count of all filters, subscriptions, and dests
        for the defined sub_mgr and server_id. Accumulates the filter,
        subscription, dests that should represent what is in the server
        and local.
        """
        # pylint: disable=no-self-use
        return sum(self.count_outstanding(sub_mgr, server_id))

    def empty_expected(self, sub_mgr, server_id):
        """ Get outstanding objects from server. Return True if 0 objects """
        # pylint: disable=no-self-use

        counts = self.count_outstanding(sub_mgr, server_id)
        if sum(counts) == 0:
            return True

        print('ERROR: Server_id=%s. Unreleased filters=%s, subs=%s, dest=%s' %
              (server_id, counts[0], counts[1], counts[2]))
        return False

    def count_outstanding(self, sub_mgr, server_id):
        """
            Count outstanding filters, subscriptions, and destinations and
            return tuple with the counts
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
            sub_mgr.add_listener_destinations(server_id, listener_url,
                                              owned=True)
            filter_path = self.add_filter(sub_mgr, server_id, 'NotUsed',
                                          owned=True)
            subscriptions = sub_mgr.add_subscriptions(server_id,
                                                      filter_path,
                                                      owned=True)
            subscription_paths = [inst.path for inst in subscriptions]

            self.confirm_created(sub_mgr, server_id, filter_path,
                                 subscription_paths, owned=True)

            # confirm destination instance paths match
            assert sub_mgr.get_all_destinations(server_id)
            # TODO Finish this test completely when we add other
            #  changes for filter ids

            sub_mgr.remove_subscriptions(server_id, subscription_paths)
            sub_mgr.remove_filter(server_id, filter_path)

            self.confirm_removed(sub_mgr, server_id, filter_path,
                                 subscription_paths)

            assert self.get_object_count(sub_mgr, server_id) == 0

            sub_mgr.remove_server(server_id)

        # confirm no filters, destinations, subscriptions in server
        assert self.get_objects_from_server() == 0

    def test_create_not_owned_subscription(self):
        """
        Test creating not_owned filter, destination and filter and determining
        if they are retained by the server after the subscription manager
        is closed.

        """
        sm = "test_create_delete_subscription"
        server = WBEMServer(self.conn)

        listener_url = '%s:%s' % (self.conn.url, 50000)

        # Create a single not_owned subscription
        with WBEMSubscriptionManager(subscription_manager_id=sm) as sub_mgr:
            server_id = sub_mgr.add_server(server)
            dests = sub_mgr.add_listener_destinations(server_id, listener_url,
                                                      owned=False)
            dest_paths = [dest.path for dest in dests]
            filter_path = self.add_filter(sub_mgr, server_id, 'NotUsed',
                                          owned=False)
            subscriptions = sub_mgr.add_subscriptions(
                server_id, filter_path,
                destination_paths=dest_paths,
                owned=False)
            subscription_paths = [inst.path for inst in subscriptions]

            self.confirm_created(sub_mgr, server_id, filter_path,
                                 subscription_paths, owned=False)
            assert self.get_object_count(sub_mgr, server_id)

        # Test that subscriptions instances are still in repo
        # self.conn.display_repository()
        assert self.get_objects_from_server() == 3

        # Create a new submgr and and test for filters, etc. retrieved.
        with WBEMSubscriptionManager(subscription_manager_id=sm) as sub_mgr:
            server_id = sub_mgr.add_server(server)
            assert len(sub_mgr.get_all_destinations(server_id)) == 1
            assert len(sub_mgr.get_all_filters(server_id)) == 1
            assert len(sub_mgr.get_all_subscriptions(server_id)) == 1

            assert self.get_object_count(sub_mgr, server_id) == 3

            sub_paths = [sub.path for sub in
                         sub_mgr.get_all_subscriptions(server_id)]
            sub_mgr.remove_subscriptions(server_id, sub_paths)

            dest_paths = [dest.path for dest in
                          sub_mgr.get_all_destinations(server_id)]
            sub_mgr.remove_destinations(
                server_id, dest_paths)

            for filter_ in sub_mgr.get_all_filters(server_id):
                sub_mgr.remove_filter(server_id, filter_.path)
            assert self.get_object_count(sub_mgr, server_id) == 0


def setup_mock_server(url=None):
    """
    Setup a pywbem mock environment suitable for running subscription tests.
    This is the same definition as the setup in the unittests above.
    """
    skip_if_moftab_regenerated()
    server = WbemServerMock(interop_ns='interop', url=url,
                            server_mock_data=SUBSCRIPTION_WBEM_SERVER_MOCK_DICT)
    conn = server.wbem_server.conn
    return conn


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
    #   * dest_attrs: dictionary of attributes for add_listener_destinations.
    #     Since add_listener_destination can add lists, there is no option
    #     to add a list for this item.
    #   * subscription_attrs: dictionary or list dictionaries where each
    #     dictionary is a dictionary that defines either the attributes of
    #     the subscription or to make it simpler to define tests, an integer
    #     for the position in the appropriate list for the required
    #     filter or destination
    #   * exp_result: Expected dictionary items, for validation. This includes:
    #       * server_id - The expected server_id
    #       * listener_count - Count of expected destinations
    #       * filter_count - Count of expected filters.
    #       * TODO: Add validation for filter, dest attributes
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
            exp_result=dict()
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
            exp_result=dict()
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
            exp_result=dict()
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
            exp_result=dict()
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
            subscription_attrs=None,
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
                              source_namespace='root/interop',
                              query="SELECT * from blah",
                              query_language='WQL',
                              owned=True,
                              filter_id=None, name=None),
            dest_attrs=None,
            subscription_attrs=None,
            exp_result=dict(server_id="http://FakedUrl:5988")
        ),
        ValueError, None, OK
    ),
    (
        "Add_filter with both name and filter_id fails",
        dict(
            submgr_id="ValidID",
            connection_attrs=dict(url=None),
            filter_attrs=dict(server_id="http://FakedUrl:5988",
                              source_namespace='root/interop',
                              query="SELECT * from blah",
                              query_language='WQL',
                              owned=True,
                              filter_id="Fred", name="fred"),
            dest_attrs=None,
            subscription_attrs=None,
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
                              source_namespace='root/interop',
                              query="SELECT * from blah",
                              query_language='WQL',
                              owned=True,
                              filter_id="Fred:", name=None),
            dest_attrs=None,
            subscription_attrs=None,
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
                              source_namespace='root/interop',
                              query="SELECT * from blah",
                              query_language='WQL',
                              owned=True,
                              filter_id=9, name=None),
            dest_attrs=None,
            subscription_attrs=None,
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
                              source_namespace='root/interop',
                              query="SELECT * from blah",
                              query_language='WQL',
                              owned=True,
                              filter_id="Filter1", name=None),
            dest_attrs=None,
            subscription_attrs=None,
            exp_result=dict(server_id="http://FakedUrl:5988",
                            filter_count=1)
        ),
        None, None, OK
    ),
    (
        "Add_filter with  2 valid filters",
        dict(
            submgr_id="ValidID",
            connection_attrs=dict(url=None),
            filter_attrs=[dict(server_id="http://FakedUrl:5988",
                               source_namespace='root/interop',
                               query="SELECT * from blah",
                               query_language='WQL',
                               owned=True,
                               filter_id="Filter1", name=None),
                          dict(server_id="http://FakedUrl:5988",
                               source_namespace='root/interop',
                               query="SELECT * from blah",
                               query_language='WQL',
                               owned=True,
                               filter_id="Filter2", name=None), ],
            dest_attrs=None,
            subscription_attrs=None,
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
                            listener_urls="httpx",
                            owned=True),
            subscription_attrs=None,
            exp_result=dict(server_id="http://FakedUrl:5988")
        ),
        ValueError, None, OK
    ),
    (
        "Add valid listener_destination",
        dict(
            submgr_id="ValidID",
            connection_attrs=dict(url=None),
            filter_attrs=None,
            dest_attrs=dict(server_id="http://FakedUrl:5988",
                            listener_urls="http://localhost:5000",

                            owned=True),
            subscription_attrs=None,
            exp_result=dict(server_id="http://FakedUrl:5988",
                            listener_count=1)
        ),
        None, None, OK
    ),
    (
        "Add multiple valid listener_destinations",
        dict(
            submgr_id="ValidID",
            connection_attrs=dict(url=None),
            filter_attrs=None,
            dest_attrs=dict(server_id="http://FakedUrl:5988",
                            listener_urls=["http://localhost:5000",
                                           "https://localhost:5001"],
                            owned=True),
            subscription_attrs=None,
            exp_result=dict(server_id="http://FakedUrl:5988",
                            listener_count=2)
        ),
        None, None, OK
    ),
    (
        "Add a single valid subscription",
        dict(
            submgr_id="ValidID",
            connection_attrs=dict(url=None),
            dest_attrs=dict(server_id="http://FakedUrl:5988",
                            listener_urls="http://localhost:5000",
                            owned=True),
            filter_attrs=dict(server_id="http://FakedUrl:5988",
                              source_namespace='root/interop',
                              query="SELECT * from blah",
                              query_language='WQL',
                              owned=True,
                              filter_id="Filter1", name=None),
            subscription_attrs=dict(server_id="http://FakedUrl:5988",
                                    filter_path=0,
                                    destination_paths=0,
                                    owned=True),
            exp_result=dict(server_id="http://FakedUrl:5988",
                            listener_count=1,
                            filter_count=1,
                            subscription_count=1)
        ),
        None, None, RUN
    ),

    # Tests that need to be added
    # Add server_id second time, Should fail
    # Add server where param is not WBEMServer
    # add not_owned filters and destinations
    # NOTE: The following tests will be added after merge with issue #2701
    # Remove multiple owned subscriptions, filters, dests
    # NOTE: Because of issue# 2704, we cannot test a number of capabilities
    # NOTE: Eventually this should replace most of the unit tests.
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_SUBMGR)
@simplified_test_function
def test_subscriptionmanager(testcase, submgr_id, connection_attrs,
                             filter_attrs, dest_attrs, subscription_attrs,
                             exp_result):
    """
    Tests object init and add-server
    """
    skip_if_moftab_regenerated()

    def define_connection(connection_attrs):
        """
        Create a new mock connection with the attributes defined in
        connection_attrs.
        This method also does an add_server with the created mock server.
        Returns:
            returns the server_id associated with the connection.
        """
        mock_server = WbemServerMock(
            interop_ns='interop',
            server_mock_data=SUBSCRIPTION_WBEM_SERVER_MOCK_DICT,
            **connection_attrs)
        return submgr.add_server(mock_server.wbem_server)

    # The code to be tested.
    submgr = WBEMSubscriptionManager(submgr_id)

    # Test result arrays for one or more server_ids. Eachof the add and
    # remove methods will insert the results into these lists for validation
    # of the returns from these methods.
    server_id = None
    server_ids = []
    added_filters = []
    added_destinations = []
    added_subscriptions = []

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

    # Test for add destinations. There is no option for a list here since
    # the tested method includes adding lists
    if dest_attrs:
        added_destinations.extend(
            submgr.add_listener_destinations(**dest_attrs))

    if subscription_attrs:
        if isinstance(subscription_attrs, dict):
            subscription_attrs = [subscription_attrs]
        for attr in subscription_attrs:
            if isinstance(attr['filter_path'], int):
                attr['filter_path'] = added_filters[attr['filter_path']].path
            if isinstance(attr['destination_paths'], int):
                attr['destination_paths'] = \
                    added_destinations[attr['destination_paths']].path
            rslts = submgr.add_subscriptions(**attr)
            added_subscriptions.extend(rslts)

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None
    if "server_id" in exp_result:
        if isinstance(exp_result['server_id'], list):
            assert set(server_ids) == set(exp_result['server_id'])
        else:
            assert server_id == exp_result['server_id']

    if 'listener_count' in exp_result:
        assert len(submgr.get_all_destinations(server_id)) == \
            exp_result['listener_count']

    if 'filter_count' in exp_result:
        assert len(submgr.get_all_filters(server_id)) == \
            exp_result['filter_count']

    if 'subscription_count' in exp_result:
        assert len(submgr.get_all_subscriptions(server_id)) == \
            exp_result['subscription_count']
