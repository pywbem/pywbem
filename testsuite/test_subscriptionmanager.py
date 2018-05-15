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
from six.moves.urllib.parse import urlparse

from pywbem import WBEMServer, CIMInstance, CIMInstanceName, \
    CIMClassName, WBEMSubscriptionManager

from pywbem._nocasedict import NocaseDict

from pywbem._subscription_manager import SUBSCRIPTION_CLASSNAME, \
    DESTINATION_CLASSNAME, FILTER_CLASSNAME


from pywbem_mock import FakedWBEMConnection

from dmtf_mof_schema_def import DMTF_TEST_SCHEMA_VER

# location of testsuite/schema dir used by all tests as test DMTF CIM Schema
# This directory is permanent and should not be removed.
TEST_DIR = os.path.dirname(__file__)
TESTSUITE_SCHEMA_DIR = os.path.join(TEST_DIR, 'schema')

VERBOSE = True


class BaseMethodsForTests(object):
    """
    Base Class for tests contains all common methods and class level
    setup.
    """
    #   conn = None
    interop_ns = 'interop'
    system_name = 'Mock_Test_subscription_mgr'
    object_manager_name = 'MyFakeObjectManager'

    def setup_method(self):
        """Create the Fake connection and set the connection """
        FakedWBEMConnection._reset_logging_config()
        self.conn = FakedWBEMConnection(default_namespace=self.interop_ns)
        classnames = ['CIM_IndicationSubscription',
                      'CIM_ListenerDestinationCIMXML',
                      'CIM_IndicationFilter',
                      # The following are requied by WBEMServer
                      'CIM_Namespace',
                      'CIM_ObjectManager',
                      'CIM_RegisteredProfile']

        self.conn.compile_dmtf_schema(DMTF_TEST_SCHEMA_VER,
                                      TESTSUITE_SCHEMA_DIR,
                                      class_names=classnames, verbose=False)

        # build CIM_Namespace instances
        test_namespaces = [self.interop_ns]

        # Build CIM_ObjectManager instance
        self.build_obj_mgr_inst(self.conn, self.interop_ns,
                                self.system_name,
                                self.object_manager_name)

        self.build_cimnamespace_insts(self.conn, self.interop_ns,
                                      self.system_name,
                                      self.object_manager_name, test_namespaces)

        # self.conn.display_repository()

    @staticmethod
    def inst_from_class(klass, namespace=None,
                        property_values=None,
                        include_null_properties=True,
                        include_path=True, strict=False,
                        include_class_origin=False):
        """
        Build a new CIMInstance from the input CIMClass using the
        property_values dictionary to complete properties and the other
        parameters to filter properties, validate the properties, and
        optionally set the path component of the CIMInstance.  If any of the
        properties in the class have default values, those values are passed
        to the instance unless overridden by the property_values dictionary.
        No CIMProperty qualifiers are included in the created instance and the
        `class_origin` attribute is transfered from the class only if the
        `include_class_origin` parameter is True

        Parameters:
          klass (:class:`pywbem:CIMClass`)
            CIMClass from which the instance will be constructed.  This
            class must include qualifiers and should include properties
            from any superclasses to be sure it includes all properties
            that are to be built into the instance. Properties may be
            excluded from the instance by not including them in the `klass`
            parameter.

          namespace (:term:`string`):
            Namespace in the WBEMConnection used to retrieve the class or
            `None` if the default_namespace is to be used.

          property_values (dictionary):
            Dictionary containing name/value pairs where the names are the
            names of properties in the class and the properties are the
            property values to be set into the instance. If a property is in
            the property_values dictionary but not in the class an ValueError
            exception is raised.

          include_null_properties (:class:`py:bool`):
            Determines if properties with Null values are included in the
            instance.

            If `True` they are included in the instance returned.

            If `False` they are not included in the instance returned

         include_class_origin  (:class:`py:bool`):
            Determines if ClassOrigin information is included in the returned
            instance.

            If None or False, class origin information is not included.

            If True, class origin information is included.

          include_path (:class:`py:bool`:):
            If `True` the CIMInstanceName path is build and inserted into
            the new instance.  If `strict` all key properties must be in the
            instance.

          strict (:class:`py:bool`:):
            If `True` and `include_path` is set, all key properties must be in
            the instance so that

            If not `True` The path component is created even if not all
            key properties are in the created instance.

        Returns:
            Returns an instance with the defined properties and optionally
            the path set.  No qualifiers are included in the returned instance
            and the existence of ClassOrigin depends on the
            `include_class_origin` parameter. The value of each property is
            either the value from the `property_values` dictionary, the
            default_value from the class or Null(unless
            `include_null_properties` is False). All other attributes of each
            property are the same as the corresponding class property.

        Raises:
           ValueError if there are conflicts between the class and
           property_values dictionary or strict is set and the class is not
           complete.
        """
        class_name = klass.classname
        inst = CIMInstance(class_name)
        for p in property_values:
            if p not in klass.properties:
                raise ValueError('Property Name %s in property_values but '
                                 'not in class %s' % (p, class_name))
        for cp in klass.properties:
            ip = klass.properties[cp].copy()
            ip.qualifiers = NocaseDict()
            if not include_class_origin:
                ip.class_origin = None
            if ip.name in property_values:
                ip.value = property_values[ip.name]
            if include_null_properties:
                inst[ip.name] = ip
            else:
                if ip.value:
                    inst[ip.name] = ip

        if include_path:
            inst.path = CIMInstanceName.from_instance(klass, inst, namespace,
                                                      strict=strict)
        return inst

    def inst_from_classname(self, conn, class_name, namespace=None,
                            property_list=None,
                            property_values=None,
                            include_null_properties=True,
                            strict=False, include_path=True):
        """
        Build instance from class using class_name property to get class
        from a repository.
        """
        cls = conn.GetClass(class_name, namespace=namespace, LocalOnly=False,
                            IncludeQualifiers=True, include_class_origin=True,
                            property_list=property_list)

        return self.inst_from_class(
            cls, namespace=namespace, property_values=property_values,
            include_null_properties=include_null_properties,
            strict=strict, include_path=include_path)

    def add_filter(self, sub_mgr, server_id, filter_id, owned=True):
        """
        Create a single filter definition in the sub_mgr and return it.
        This creates a filter specifically for OpenPegasus tests using the
        class/namespace information define in this method.
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
        return filter_

    def get_objects_from_server(self, sub_mgr_id=None):
        """
        Using Server class, get count of Filters, Subscriptions, Destinations
        from server as confirmation outside of SubscriptionManagerCode.
        """
        this_host = urlparse(self.conn.url).netloc
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
        When owned filter_path and subscription path are removed, this
        confirms that results are correct both int the local subscription
        manager and the remote WBEM server.
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

        print('Server_id=%s. Unreleased filters=%s, subs=%s, dest=%s' %
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

    def build_cimnamespace_insts(self, conn, namespace, system_name,
                                 object_manager_name, test_namespaces):
        """
        Build instances of CIM_Namespace defined by test_namespaces list
        """

        for ns in test_namespaces:
            nsdict = {"SystemName": system_name,
                      "ObjectManagerName": object_manager_name,
                      'Name': ns,
                      'CreationClassName': 'CIM_Namespace',
                      'ObjectManagerCreationClassName': 'CIM_ObjectManager',
                      'SystemCreationClassName': 'CIM_ComputerSystem'}

            nsinst = self.inst_from_classname(conn, "CIM_Namespace",
                                              namespace=namespace,
                                              property_values=nsdict,
                                              strict=True,
                                              include_null_properties=False,
                                              include_path=True)
            conn.add_cimobjects(nsinst, namespace=namespace)

        namespaces = conn.EnumerateInstances("CIM_Namespace",
                                             namespace=namespace)
        assert len(namespaces) == len(test_namespaces)

    def build_obj_mgr_inst(self, conn, namespace, system_name,
                           object_manager_name):
        """
        Build an instance of the ObjectManager class
        """
        omdict = {"SystemCreationClassName": "CIM_ComputerSystem",
                  "CreationClassName": "CIM_ObjectManager",
                  "SystemName": system_name,
                  "Name": object_manager_name,
                  "ElementName": "Pegasus",
                  "Description": "Pegasus CIM Server Version 2.15.0 Released"}

        ominst = self.inst_from_classname(conn, "CIM_ObjectManager",
                                          namespace=namespace,
                                          property_values=omdict, strict=True,
                                          include_null_properties=False,
                                          include_path=True)

        conn.add_cimobjects(ominst, namespace=namespace)

        assert(len(conn.EnumerateInstances("CIM_ObjectManager",
                                           namespace=namespace)) == 1)

        return ominst


class TestSubMgrClass(BaseMethodsForTests):
    """Test of subscription manager"""

    def test_one(self):
        """
        Test Basic Creation of sub mgr, creation of owned subscription
        and cleanup.
        """

        sm = "test_create_delete_subscription"
        server = WBEMServer(self.conn)

        listener_url = '%s:%s' % (self.conn.url, 5000)

        with WBEMSubscriptionManager(subscription_manager_id=sm) as sub_mgr:

            server_id = sub_mgr.add_server(server)
            sub_mgr.add_listener_destinations(server_id, listener_url)
            filter_ = self.add_filter(sub_mgr, server_id, 'NotUsed', owned=True)
            subscriptions = sub_mgr.add_subscriptions(server_id,
                                                      filter_.path)
            subscription_paths = [inst.path for inst in subscriptions]

            self.confirm_created(sub_mgr, server_id, filter_.path,
                                 subscription_paths)

            self.conn.display_repository()

            # confirm destination instance paths match
            assert sub_mgr.get_all_destinations(server_id)
            # TODO: ks Finish this test completely when we add other
            #  changes for filter ids

            sub_mgr.remove_subscriptions(server_id, subscription_paths)
            sub_mgr.remove_filter(server_id, filter_.path)

            self.confirm_removed(sub_mgr, server_id, filter_.path,
                                 subscription_paths)

            assert self.get_object_count(sub_mgr, server_id) == 0

            sub_mgr.remove_server(server_id)

        assert self.get_objects_from_server() == 0
