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
WBEMServe requires access to a WBEMServer.
"""
from __future__ import absolute_import, print_function

import os
import re
from socket import getfqdn

from pywbem import WBEMServer, CIMClassName, WBEMSubscriptionManager, \
    CIMInstance

from pywbem._subscription_manager import SUBSCRIPTION_CLASSNAME, \
    DESTINATION_CLASSNAME, FILTER_CLASSNAME

from ..utils.dmtf_mof_schema_def import DMTF_TEST_SCHEMA_VER
from ..utils.wbemserver_mock import WbemServerMock


# Location of DMTF schema directory used by all tests.
# This directory is permanent and should not be removed.
TESTSUITE_SCHEMA_DIR = os.path.join('tests', 'schema')

VERBOSE = False


class BaseMethodsForTests(object):
    """
    Base Class for tests contains all common methods and class level
    setup.
    """

    def setup_method(self):
        """
        Create the Fake connection and setup the connection. This
        method first initialized the WbemServerMock and then suplements
        it with the classes required for the subscription manager.
        """
        server = WbemServerMock(interop_ns='interop')
        # pylint: disable=attribute-defined-outside-init
        self.conn = server.wbem_server.conn
        classnames = ['CIM_IndicationSubscription',
                      'CIM_ListenerDestinationCIMXML',
                      'CIM_IndicationFilter', ]

        self.conn.compile_dmtf_schema(DMTF_TEST_SCHEMA_VER,
                                      TESTSUITE_SCHEMA_DIR,
                                      class_names=classnames, verbose=False)

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
        """ TODO """
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

            # self.conn.display_repository()

            self.confirm_created(sub_mgr, server_id, filter_path,
                                 subscription_paths, owned=True)

            # confirm destination instance paths match
            assert sub_mgr.get_all_destinations(server_id)
            # TODO: ks Finish this test completely when we add other
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
