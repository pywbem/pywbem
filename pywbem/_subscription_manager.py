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

"""
*New in pywbem 0.9 as experimental and finalized in 0.10.*

The :class:`~pywbem.WBEMSubscriptionManager` class is a subscription manager
that provides for creating and removing indication subscriptions (including
indication filters and listener destinations) for multiple WBEM servers and
multiple WBEM listeners and for getting information about existing indication
subscriptions.

The WBEM listener is identified through its URL, so it may be the pywbem
listener (that is, a :class:`~pywbem.WBEMListener` object) or any other WBEM
listener.

This subscription manager supports three types of ownership of the CIM
instances in WBEM servers that represent subscriptions, filters and listener
destinations:

* **Owned**

  Owned CIM instances are created via the subscription manager and their life
  cycle is bound to the life cycle of the registration of that WBEM server with
  the subscription manager via
  :meth:`~pywbem.WBEMSubscriptionManager.add_server`.

  Owned CIM instances are deleted automatically when their WBEM server is
  deregistered from the subscription manager via
  :meth:`~pywbem.WBEMSubscriptionManager.remove_server` or
  :meth:`~pywbem.WBEMSubscriptionManager.remove_all_servers`. In addition, they
  can be deleted by the user via the removal methods of the
  :class:`~pywbem.WBEMSubscriptionManager` class.

* **Permanent**

  Permanent CIM instances are created via the subscription manager and their
  life cycle is independent of the life cycle of the registration of that WBEM
  server with the subscription manager.

  Permanent CIM instances are not deleted automatically when their WBEM server
  is deregistered from the subscription manager. The user is responsible for
  their lifetime management: They can be deleted via the removal methods of the
  :class:`~pywbem.WBEMSubscriptionManager` class.

* **Static**

  Static CIM instances pre-exist in the WBEM server and cannot be deleted
  (or created) by a WBEM client.

If a client creates a subscription between a filter and a listener destination,
the types of ownership of these three CIM instances may be arbitrarily mixed,
with one exception:

* A permanent subscription cannot be created on an owned filter or an owned
  listener destination. Allowing that would prevent the automatic life cycle
  management of the owned filter or listener destination by the subscription
  manager. This restriction is enforced by the
  :class:`~pywbem.WBEMSubscriptionManager` class.

The :class:`~pywbem.WBEMSubscriptionManager` object remembers owned
subscriptions, filters, and listener destinations. If for some reason that
object gets deleted before all servers could be removed (e.g. because the
Python program aborts), the corresponding CIM instances in the WBEM server
still exist, but the knowledge is lost that these instances were owned by that
subscription manager. Therefore, the subscription manager discovers owned
subscriptions, filters, and listener destinations when a server is added.
For filters, this discovery is based upon the Name property. Therefore, if
the Name property is set by the user (e.g. because a management profile
requires a particular name), the filter must be permanent and cannot be owned.

Examples
--------

The following example code demonstrates the use of a subscription manager
to subscribe for a CIM alert indication on a WBEM server. The WBEM listener
is assumed to exist somewhere and is identified by its URL::

    import sys
    from socket import getfqdn
    from pywbem import WBEMConnection, WBEMServer, WBEMSubscriptionManager

    server_url = 'http://myserver'
    server_credentials = (user, password)

    listener_url = 'http://mylistener'

    conn = WBEMConnection(server_url, server_credentials)
    server = WBEMServer(conn)
    sub_mgr = WBEMSubscriptionManager(subscription_manager_id='fred')

    # Register the server in the subscription manager:
    server_id = sub_mgr.add_server(server)

    # Add a listener destination in the server:
    dest_inst = sub_mgr.add_listener_destinations(server_id, listener_url)

    # Subscribe to a static filter of a given name:
    filter1_name = "DMTF:Indications:GlobalAlertIndicationFilter"
    filter1_insts = sub_mgr.get_all_filters(server_id)
    for inst in filter1_insts:
        if inst['Name'] == filter1_name:
            sub_mgr.add_subscriptions(server_id, inst.path, dest_inst.path)
            break

    # Create a dynamic alert filter and subscribe to it:
    filter2_source_ns = "root/cimv2"
    filter2_query = "SELECT * FROM CIM_AlertIndication " \\
                    "WHERE OwningEntity = 'DMTF' " \\
                    "AND MessageID LIKE 'SVPC0123|SVPC0124|SVPC0125'"
    filter2_language = "DMTF:CQL"
    filter2_inst = subscription_manager.add_filter(server_id,
        filter2_source_ns, filter2_query, filter2_language, owned=True,
        filter_id="myalert")
    sub_mgr.add_subscriptions(server_id, filter2_inst.path, dest_inst.path)

The following example code briefly shows how to use a subscription manager
as a context manager, in order to get automatic cleanup of owned instances::

    with WBEMSubscriptionManager('fred') as sub_mgr:
        server_id = sub_mgr.add_server(server)
        . . .
    # The exit method automatically calls remove_all_servers(), which deletes
    # all owned subscription, filter and destination instances in the servers
    # that were registered.

The :ref:`Tutorial` section contains a tutorial about the subscription manager.
"""

import re
from socket import getfqdn
import uuid
import six

from ._server import WBEMServer
from ._cim_obj import CIMInstance, CIMInstanceName
from ._cim_http import parse_url
from ._cim_constants import CIM_ERR_FAILED
from ._exceptions import CIMError
from ._utils import _format

# CIM model classnames for subscription components
SUBSCRIPTION_CLASSNAME = 'CIM_IndicationSubscription'
DESTINATION_CLASSNAME = 'CIM_ListenerDestinationCIMXML'
FILTER_CLASSNAME = 'CIM_IndicationFilter'
SYSTEM_CREATION_CLASSNAME = 'CIM_ComputerSystem'

DEFAULT_QUERY_LANGUAGE = 'WQL'

__all__ = ['WBEMSubscriptionManager']


class WBEMSubscriptionManager(object):
    """
    *New in pywbem 0.9 as experimental and finalized in 0.10.*

    A class for managing subscriptions for CIM indications in a WBEM server.

    The class may be used as a Python context manager, in order to get
    automatic clean up (see :meth:`~pywbem.WBEMSubscriptionManager.__exit__`).
    """

    def __init__(self, subscription_manager_id):
        """
        Parameters:

          subscription_manager_id (:term:`string`):
            A subscription manager ID string that is used as a component in
            the value of the `Name` property of indication filter and listener
            destination instances to help the user identify these instances in
            a WBEM server.

            Must not be `None`.

            The string must consist of printable characters, and must not
            contain the character ':' because that is the separator between
            components within the value of the `Name` property.

            The subscription manager ID must be unique on the current host.

            For example, the form of the `Name` property of a filter instance
            is (for details, see
            :meth:`~pywbem.WBEMSubscriptionManager.add_filter`):

              ``"pywbemfilter:" {ownership} ":" {subscription_manager_id} ":"
              {filter_id} ":" {guid}``

        Raises:

            ValueError: Incorrect input parameter values.
            TypeError: Incorrect input parameter types.
        """

        # The following dictionaries have the WBEM server ID as a key.
        self._servers = {}  # WBEMServer objects for the WBEM servers
        self._owned_subscriptions = {}  # CIMInstance of owned subscriptions
        self._owned_filters = {}  # CIMInstance of owned filters
        self._owned_destinations = {}  # CIMInstance owned destinations

        if subscription_manager_id is None:
            raise ValueError("Subscription manager ID must not be None")
        if not isinstance(subscription_manager_id, six.string_types):
            raise TypeError(
                _format("Invalid type for subscription manager ID: {0!A}",
                        subscription_manager_id))
        if ':' in subscription_manager_id:
            raise ValueError(
                _format("Subscription manager ID contains ':': {0!A}",
                        subscription_manager_id))
        self._subscription_manager_id = subscription_manager_id

    def __str__(self):
        """
        Return a representation of the :class:`~pywbem.WBEMSubscriptionManager`
        object with a subset of its attributes.
        """
        return _format(
            "WBEMSubscriptionManager("
            "_subscription_manager_id={s._subscription_manager_id!A}, "
            "_servers={s._servers}, "
            "...)",
            s=self)

    def __repr__(self):
        """
        Return a representation of the :class:`~pywbem.WBEMSubscriptionManager`
        object with all attributes, that is suitable for debugging.
        """
        return _format(
            "WBEMSubscriptionManager("
            "_subscription_manager_id={s._subscription_manager_id!A}, "
            "_servers={s._servers!A}, "
            "_owned_subscriptions={s._owned_subscriptions!A}, "
            "_owned_filters={s._owned_filters!A}, "
            "_owned_destinations={s._owned_destinations!A})",
            s=self)

    def __enter__(self):
        """
        *New in pywbem 0.10.*

        Enter method when the class is used as a context manager.
        Returns the subscription manager object
        """
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """
        *New in pywbem 0.10.*

        Exit method when the class is used as a context manager.

        It cleans up by calling
        :meth:`~pywbem.WBEMSubscriptionManager.remove_all_servers`.
        """
        self.remove_all_servers()
        return False  # re-raise any exceptions

    def _get_server(self, server_id):
        """
        Internal method to get the server object, given a server_id.

        Parameters:

          server_id (:term:`string`):
            The server ID of the WBEM server, returned by
            :meth:`~pywbem.WBEMSubscriptionManager.add_server`.

        Returns:

          server (:class:`~pywbem.WBEMServer`):
            The WBEM server.

        Raises:

            ValueError: server_id not known to subscription manager.
        """

        if server_id not in self._servers:
            raise ValueError(
                _format("WBEM server {0!A} not known by subscription manager",
                        server_id))

        return self._servers[server_id]

    def add_server(self, server):
        """
        Register a WBEM server with the subscription manager. This is a
        prerequisite for adding listener destinations, indication filters and
        indication subscriptions to the server.

        This method discovers listener destination, indication filter, and
        subscription instances in the WBEM server owned by this subscription
        manager, and registers them in the subscription manager as if they had
        been created through it.

        In this discovery process, listener destination and indication filter
        instances are matched based upon the value of their `Name` property.
        Subscription instances are matched based upon the ownership of the
        referenced destination and filter instances: If a subscription
        references a filter or a destination that is owned by this subscription
        manager, it is considered owned by this subscription manager as well.

        Parameters:

          server (:class:`~pywbem.WBEMServer`):
            The WBEM server.

        Returns:

            :term:`string`: An ID for the WBEM server, for use by other
            methods of this class.

        Raises:

            Exceptions raised by :class:`~pywbem.WBEMConnection`.
            ValueError: Incorrect input parameter values.
            TypeError: Incorrect input parameter types.
        """

        if not isinstance(server, WBEMServer):
            raise TypeError("Server argument of add_server() must be a "
                            "WBEMServer object")
        server_id = server.url
        if server_id in self._servers:
            raise ValueError(
                _format("WBEM server already known by listener: {0!A}",
                        server_id))

        # Create dictionary entries for this server
        self._servers[server_id] = server
        self._owned_subscriptions[server_id] = []
        self._owned_filters[server_id] = []
        self._owned_destinations[server_id] = []

        # Recover any owned destination, filter, and subscription instances
        # that exist on this server

        this_host = getfqdn()

        dest_name_pattern = re.compile(
            _format(r'^pywbemdestination:owned:{0}:{1}:[^:]*$',
                    this_host, self._subscription_manager_id))
        dest_insts = server.conn.EnumerateInstances(
            DESTINATION_CLASSNAME, namespace=server.interop_ns)
        for inst in dest_insts:
            if re.match(dest_name_pattern, inst.path.keybindings['Name']) \
                    and inst.path.keybindings['SystemName'] == this_host:
                self._owned_destinations[server_id].append(inst)

        filter_name_pattern = re.compile(
            _format(r'^pywbemfilter:owned:{0}:{1}:[^:]*:[^:]*$',
                    this_host, self._subscription_manager_id))
        filter_insts = server.conn.EnumerateInstances(
            FILTER_CLASSNAME, namespace=server.interop_ns)
        for inst in filter_insts:
            if re.match(filter_name_pattern, inst.path.keybindings['Name']) \
                    and inst.path.keybindings['SystemName'] == this_host:
                self._owned_filters[server_id].append(inst)

        sub_insts = server.conn.EnumerateInstances(
            SUBSCRIPTION_CLASSNAME, namespace=server.interop_ns)
        owned_filter_paths = [inst.path for inst in
                              self._owned_filters[server_id]]
        owned_destination_paths = [inst.path for inst in
                                   self._owned_destinations[server_id]]
        for inst in sub_insts:
            if inst.path.keybindings['Filter'] in \
                    owned_filter_paths \
                    or inst.path.keybindings['Handler'] in \
                    owned_destination_paths:
                self._owned_subscriptions[server_id].append(inst)

        return server_id

    def remove_server(self, server_id):
        """
        Remove a registered WBEM server from the subscription manager. This
        also unregisters listeners from that server and removes all owned
        indication subscriptions, owned indication filters and owned listener
        destinations.

        Parameters:

          server_id (:term:`string`):
            The server ID of the WBEM server, returned by
            :meth:`~pywbem.WBEMSubscriptionManager.add_server`.

        Raises:

            Exceptions raised by :class:`~pywbem.WBEMConnection`.
        """

        # Validate server_id
        server = self._get_server(server_id)

        # Delete any instances we recorded to be cleaned up

        if server_id in self._owned_subscriptions:
            inst_list = self._owned_subscriptions[server_id]
            # We iterate backwards because we change the list
            for i in six.moves.range(len(inst_list) - 1, -1, -1):
                inst = inst_list[i]
                server.conn.DeleteInstance(inst.path)
                del inst_list[i]
            del self._owned_subscriptions[server_id]

        if server_id in self._owned_filters:
            inst_list = self._owned_filters[server_id]
            # We iterate backwards because we change the list
            for i in six.moves.range(len(inst_list) - 1, -1, -1):
                inst = inst_list[i]
                server.conn.DeleteInstance(inst.path)
                del inst_list[i]
            del self._owned_filters[server_id]

        if server_id in self._owned_destinations:
            inst_list = self._owned_destinations[server_id]
            # We iterate backwards because we change the list
            for i in six.moves.range(len(inst_list) - 1, -1, -1):
                inst = inst_list[i]
                server.conn.DeleteInstance(inst.path)
                del inst_list[i]
            del self._owned_destinations[server_id]

        # Remove server from this listener
        del self._servers[server_id]

    def remove_all_servers(self):
        """
        Remove all registered WBEM servers from the subscription manager. This
        also unregisters listeners from these servers and removes all owned
        indication subscriptions, owned indication filters, and owned listener
        destinations.

        Raises:

            Exceptions raised by :class:`~pywbem.WBEMConnection`.
        """

        for server_id in list(self._servers.keys()):
            self.remove_server(server_id)

    def add_listener_destinations(self, server_id, listener_urls, owned=True):
        """
        Register WBEM listeners to be the target of indications sent by a
        WBEM server.

        This function automatically creates a listener destination instance
        (of CIM class "CIM_ListenerDestinationCIMXML") for each specified
        listener URL in the Interop namespace of the specified WBEM server.

        The form of the `Name` property of the created destination instance is:

          ``"pywbemdestination:" {ownership} ":" {subscription_manager_id} ":"
          {guid}``

        where ``{ownership}`` is ``"owned"`` or ``"permanent"`` dependent on
        the `owned` argument; ``{subscription_manager_id}`` is the
        subscription manager ID; and ``{guid}`` is a globally unique
        identifier.

        Owned listener destinations are added or updated conditionally: If the
        listener destination instance to be added is already registered with
        this subscription manager and has the same property values, it is not
        created or modified. If it has the same path but different property
        values, it is modified to get the desired property values. If an
        instance with this path does not exist yet (the normal case), it is
        created.

        Permanent listener destinations are created unconditionally, and it is
        up to the user to ensure that such an instance does not exist yet.

        Parameters:

          server_id (:term:`string`):
            The server ID of the WBEM server, returned by
            :meth:`~pywbem.WBEMSubscriptionManager.add_server`.

          listener_urls (:term:`string` or list of :term:`string`):
            The URL or URLs of the WBEM listeners to be registered.

            The WBEM listener may be a :class:`~pywbem.WBEMListener` object or
            any external WBEM listener.

            Each listener URL string must have the format:

              ``[{scheme}://]{host}:{port}``

            The following URL schemes are supported:

            * ``https``: Causes HTTPS to be used.
            * ``http``: Causes HTTP to be used. This is the default

            The host can be specified in any of the usual formats:

            * a short or fully qualified DNS hostname
            * a literal (= dotted) IPv4 address
            * a literal IPv6 address, formatted as defined in :term:`RFC3986`
              with the extensions for zone identifiers as defined in
              :term:`RFC6874`, supporting ``-`` (minus) for the delimiter
              before the zone ID string, as an additional choice to ``%25``.

            Note that the port is required in listener URLs.

            See :class:`~pywbem.WBEMConnection` for examples of valid URLs,
            with the caveat that the port in server URLs is optional.

          owned (:class:`py:bool`):
            Defines the ownership type of the created listener destination
            instances: If `True`, they will be owned. Otherwise, they will be
            permanent. See :ref:`WBEMSubscriptionManager` for details about
            these ownership types.

        Returns:

            :class:`py:list` of :class:`~pywbem.CIMInstance`: The created
            listener destination instances for the defined listener URLs.

        Raises:

            Exceptions raised by :class:`~pywbem.WBEMConnection`.
        """

        # server_id is validated in _create_...() method.

        # If list, recursively call this function with each list item.
        if isinstance(listener_urls, list):
            dest_insts = []
            for listener_url in listener_urls:
                new_dest_insts = self.add_listener_destinations(
                    server_id, listener_url)
                dest_insts.extend(new_dest_insts)
            return dest_insts

        # Here, the variable will be a single list item.
        listener_url = listener_urls

        dest_inst = self._create_destination(server_id, listener_url, owned)

        return [dest_inst]

    def get_owned_destinations(self, server_id):
        """
        Return the listener destinations in a WBEM server owned by this
        subscription manager.

        This function accesses only the local list of owned destinations; it
        does not contact the WBEM server. The local list of owned destinations
        is discovered from the WBEM server when the server is registered with
        the subscription manager, and is maintained from then on as changes
        happen through this subscription manager.

        Parameters:

          server_id (:term:`string`):
            The server ID of the WBEM server, returned by
            :meth:`~pywbem.WBEMSubscriptionManager.add_server`.

        Returns:

            :class:`py:list` of :class:`~pywbem.CIMInstance`: The listener
            destination instances.
        """

        # Validate server_id
        self._get_server(server_id)

        return list(self._owned_destinations[server_id])

    def get_all_destinations(self, server_id):
        """
        Return all listener destinations in a WBEM server.

        This function contacts the WBEM server and retrieves the listener
        destinations by enumerating the instances of CIM class
        "CIM_ListenerDestinationCIMXML" in the Interop namespace of the WBEM
        server.

        Parameters:

          server_id (:term:`string`):
            The server ID of the WBEM server, returned by
            :meth:`~pywbem.WBEMSubscriptionManager.add_server`.

        Returns:

            :class:`py:list` of :class:`~pywbem.CIMInstance`: The listener
            destination instances.

        Raises:

            Exceptions raised by :class:`~pywbem.WBEMConnection`.
        """

        # Validate server_id
        server = self._get_server(server_id)

        return server.conn.EnumerateInstances(DESTINATION_CLASSNAME,
                                              namespace=server.interop_ns)

    def remove_destinations(self, server_id, destination_paths):
        # pylint: disable=line-too-long
        """
        Remove listener destinations from a WBEM server, by deleting the
        listener destination instances in the server.

        The listener destinations must be owned or permanent (i.e. not static).

        This method verifies that there are not currently any subscriptions on
        the listener destinations to be removed, in order to handle server
        implementations that do not ensure that on the server side as required
        by :term:`DSP1054`.

        Parameters:

          server_id (:term:`string`):
            The server ID of the WBEM server, returned by
            :meth:`~pywbem.WBEMSubscriptionManager.add_server`.

          destination_paths (:class:`~pywbem.CIMInstanceName` or list of :class:`~pywbem.CIMInstanceName`):
            Instance path(s) of the listener destination instance(s) in the
            WBEM server.

        Raises:

            Exceptions raised by :class:`~pywbem.WBEMConnection`.
            CIMError: CIM_ERR_FAILED, if there are referencing subscriptions.
        """  # noqa: E501

        # Validate server_id
        server = self._get_server(server_id)
        conn_id = server.conn.conn_id if server.conn is not None else None

        # If list, recursively call this function with each list item.
        if isinstance(destination_paths, list):
            for dest_path in destination_paths:
                self.remove_destinations(server_id, dest_path)
            return

        # Here, the variable will be a single list item.
        dest_path = destination_paths

        # Verify referencing subscriptions.
        ref_paths = server.conn.ReferenceNames(
            dest_path, ResultClass=SUBSCRIPTION_CLASSNAME)
        if ref_paths:
            # DSP1054 1.2 defines that this CIM error is raised by the server
            # in that case, so we simulate that behavior on the client side.
            raise CIMError(
                CIM_ERR_FAILED,
                "The listener destination is referenced by subscriptions.",
                conn_id=conn_id)

        server.conn.DeleteInstance(dest_path)

        inst_list = self._owned_destinations[server_id]
        # We iterate backwards because we change the list
        for i in six.moves.range(len(inst_list) - 1, -1, -1):
            inst = inst_list[i]
            if inst.path == dest_path:
                del inst_list[i]
                # continue loop to find any possible duplicate entries

    def add_filter(self, server_id, source_namespace, query,
                   query_language=DEFAULT_QUERY_LANGUAGE, owned=True,
                   filter_id=None, name=None):
        """
        Add a :term:`dynamic indication filter` to a WBEM server, by creating
        an indication filter instance (of CIM class "CIM_IndicationFilter") in
        the Interop namespace of the server.

        The `Name` property of the created filter instance can be set in one
        of two ways:

        * directly by specifying the `name` parameter.

          In this case, the `Name` property is set directly to the `name`
          parameter.

          This should be used in cases where the user needs to have control
          over the filter name (e.g. because a DMTF management profile
          requires a particular name), but it cannot be used for owned
          filters.

        * indirectly by specifying the `filter_id` parameter.

          In this case, the value of the `Name` property will be:

          ``"pywbemfilter:" {ownership} ":" {subscription_manager_id} ":"
          {filter_id} ":" {guid}``

          where
          ``{ownership}`` is ``"owned"`` or ``"permanent"`` dependent on
          whether the filter is owned or permmanent;
          ``{subscription_manager_id}`` is the subscription manager ID;
          ``{filter_id}`` is the filter ID; and
          ``{guid}`` is a globally unique identifier.

          This can be used for both owned and permanent filters.

        Owned indication filters are added or updated conditionally: If the
        indication filter instance to be added is already registered with
        this subscription manager and has the same property values, it is not
        created or modified. If it has the same path but different property
        values, it is modified to get the desired property values. If an
        instance with this path does not exist yet (the normal case), it is
        created.

        Permanent indication filters are created unconditionally, and it is
        up to the user to ensure that such an instance does not exist yet.

        Parameters:

          server_id (:term:`string`):
            The server ID of the WBEM server, returned by
            :meth:`~pywbem.WBEMSubscriptionManager.add_server`.

          source_namespace (:term:`string`):
            Source namespace of the indication filter.

          query (:term:`string`):
            Filter query in the specified query language.

          query_language (:term:`string`):
            Query language for the specified filter query.

            Examples: 'WQL', 'DMTF:CQL'.

          owned (:class:`py:bool`):
            Defines the ownership type of the created indication filter
            instance: If `True`, it will be owned. Otherwise, it will be
            permanent. See :ref:`WBEMSubscriptionManager` for details about
            these ownership types.

          filter_id (:term:`string`)
            A filter ID string that is used as a component in the value of the
            `Name` property of filter instances to help the user identify
            these instances in a WBEM server, or `None` if the `name`
            parameter is specified.

            The string must consist of printable characters, and must not
            contain the character ':' because that is the separator between
            components within the value of the `Name` property.

            There is no requirement that the filter ID be unique. This can be
            used to identify groups of filters by using the same value for
            multiple filters.

          name (:term:`string`)
            *New in pywbem 0.10.*

            The filter name to be used directly for the `Name` property of the
            filter instance, or `None` if the `filter_id` parameter is
            specified.

        Returns:

            :class:`~pywbem.CIMInstance`: The created indication filter
            instance.

        Raises:

            Exceptions raised by :class:`~pywbem.WBEMConnection`.
            ValueError: Incorrect input parameter values.
            TypeError: Incorrect input parameter types.
        """

        # server_id is validated in _create_...() method.

        if filter_id is None and name is None:
            raise ValueError("The filter_id and name parameters are both "
                             "None, but exactly one of them must be specified")
        if filter_id is not None:
            if name is not None:
                raise ValueError("The filter_id and name parameters are both "
                                 "specified, but only one of them must be "
                                 "specified")
            if not isinstance(filter_id, six.string_types):
                raise TypeError(
                    _format("Invalid type for filter ID: {0!A}", filter_id))
            if ':' in filter_id:
                raise ValueError(
                    _format("Filter ID contains ':': {0!A}", filter_id))

        filter_inst = self._create_filter(server_id, source_namespace, query,
                                          query_language, owned, filter_id,
                                          name)

        return filter_inst

    def get_owned_filters(self, server_id):
        """
        Return the indication filters in a WBEM server owned by this
        subscription manager.

        This function accesses only the local list of owned filters; it does
        not contact the WBEM server. The local list of owned filters is
        discovered from the WBEM server when the server is registered with the
        the subscription manager, and is maintained from then on as changes
        happen through this subscription manager.

        Parameters:

          server_id (:term:`string`):
            The server ID of the WBEM server, returned by
            :meth:`~pywbem.WBEMSubscriptionManager.add_server`.

        Returns:

            :class:`py:list` of :class:`~pywbem.CIMInstance`: The indication
            filter instances.
        """

        # Validate server_id
        self._get_server(server_id)

        return list(self._owned_filters[server_id])

    def get_all_filters(self, server_id):
        """
        Return all indication filters in a WBEM server.

        This function contacts the WBEM server and retrieves the indication
        filters by enumerating the instances of CIM class
        "CIM_IndicationFilter" in the Interop namespace of the WBEM server.

        Parameters:

          server_id (:term:`string`):
            The server ID of the WBEM server, returned by
            :meth:`~pywbem.WBEMSubscriptionManager.add_server`.

        Returns:

            :class:`py:list` of :class:`~pywbem.CIMInstance`: The indication
            filter instances.

        Raises:

            Exceptions raised by :class:`~pywbem.WBEMConnection`.
        """

        # Validate server_id
        server = self._get_server(server_id)

        return server.conn.EnumerateInstances('CIM_IndicationFilter',
                                              namespace=server.interop_ns)

    def remove_filter(self, server_id, filter_path):
        """
        Remove an indication filter from a WBEM server, by deleting the
        indication filter instance in the WBEM server.

        The indication filter must be owned or permanent (i.e. not static).

        This method verifies that there are not currently any subscriptions on
        the specified indication filter, in order to handle server
        implementations that do not ensure that on the server side as required
        by :term:`DSP1054`.

        Parameters:

          server_id (:term:`string`):
            The server ID of the WBEM server, returned by
            :meth:`~pywbem.WBEMSubscriptionManager.add_server`.

          filter_path (:class:`~pywbem.CIMInstanceName`):
            Instance path of the indication filter instance in the WBEM
            server.

        Raises:

            Exceptions raised by :class:`~pywbem.WBEMConnection`.
            CIMError: CIM_ERR_FAILED, if there are referencing subscriptions.
        """

        # Validate server_id
        server = self._get_server(server_id)
        conn_id = server.conn.conn_id if server.conn is not None else None

        # Verify referencing subscriptions.
        ref_paths = server.conn.ReferenceNames(
            filter_path, ResultClass=SUBSCRIPTION_CLASSNAME)
        if ref_paths:
            # DSP1054 1.2 defines that this CIM error is raised by the server
            # in that case, so we simulate that behavior on the client side.
            raise CIMError(
                CIM_ERR_FAILED,
                "The indication filter is referenced by subscriptions.",
                conn_id=conn_id)

        server.conn.DeleteInstance(filter_path)

        inst_list = self._owned_filters[server_id]
        # We iterate backwards because we change the list
        for i in six.moves.range(len(inst_list) - 1, -1, -1):
            inst = inst_list[i]
            if inst.path == filter_path:
                del inst_list[i]
                # continue loop to find any possible duplicate entries

    def add_subscriptions(self, server_id, filter_path, destination_paths=None,
                          owned=True):
        # pylint: disable=line-too-long
        """
        Add subscriptions to a WBEM server for a particular set of indications
        defined by an indication filter and for a particular set of WBEM
        listeners defined by the instance paths of their listener destinations,
        by creating indication subscription instances (of CIM class
        "CIM_IndicationSubscription") in the Interop namespace of that server.

        The specified indication filter may be owned, permanent or static.

        The specified listener destinations may be owned, permanent or static.

        When creating permanent subscriptions, the indication filter and the
        listener destinations must not be owned.

        Owned subscriptions are added or updated conditionally: If the
        subscription instance to be added is already registered with
        this subscription manager and has the same property values, it is not
        created or modified. If it has the same path but different property
        values, it is modified to get the desired property values. If an
        instance with this path does not exist yet (the normal case), it is
        created.

        Permanent subscriptions are created unconditionally, and it is up to
        the user to ensure that such an instance does not exist yet.

        Upon successful return of this method, the added subscriptions are
        active, so that the specified WBEM listeners may immediately receive
        indications.

        Parameters:

          server_id (:term:`string`):
            The server ID of the WBEM server, returned by
            :meth:`~pywbem.WBEMSubscriptionManager.add_server`.

          filter_path (:class:`~pywbem.CIMInstanceName`):
            Instance path of the indication filter instance in the WBEM
            server that specifies the indications to be sent.

          destination_paths (:class:`~pywbem.CIMInstanceName` or list of :class:`~pywbem.CIMInstanceName`):
            Instance paths of the listener destination instances in the WBEM
            server that specify the target WBEM listener.

            If `None`, subscriptions will be created for all owned listener
            destinations registered to this subscription manager.

          owned (:class:`py:bool`):
            Defines the ownership type of the created subscription
            instances: If `True`, they will be owned. Otherwise, they will be
            permanent. See :ref:`WBEMSubscriptionManager` for details about
            these ownership types.

        Returns:

            :class:`py:list` of :class:`~pywbem.CIMInstance`: The indication
            subscription instances created in the WBEM server.

        Raises:

            Exceptions raised by :class:`~pywbem.WBEMConnection`.
            ValueError: Incorrect input parameter values.
        """  # noqa: E501

        # server_id is validated in _create_...() method.

        owned_destination_paths = [inst.path for inst in
                                   self._owned_destinations[server_id]]

        # Apply default
        if destination_paths is None:
            destination_paths = owned_destination_paths

        # If list, recursively call this function with each list item.
        if isinstance(destination_paths, list):
            sub_insts = []
            for dest_path in destination_paths:
                new_sub_insts = self.add_subscriptions(
                    server_id, filter_path, dest_path, owned)
                sub_insts.extend(new_sub_insts)
            return sub_insts

        # Here, the variable will be a single list item.
        dest_path = destination_paths

        owned_filter_paths = [inst.path for inst in
                              self._owned_filters[server_id]]

        # Enforce that a permanent subscription is not created on an owned
        # filter or on an owned destination.
        if not owned:
            if filter_path in owned_filter_paths:
                raise ValueError(
                    _format("Permanent subscription cannot be created on "
                            "owned filter: {0!A}", filter_path))
            if dest_path in owned_destination_paths:
                raise ValueError(
                    _format("Permanent subscription cannot be created on "
                            "owned listener destination: {0!A}", dest_path))

        sub_inst = self._create_subscription(server_id, dest_path, filter_path,
                                             owned)

        return [sub_inst]

    def get_owned_subscriptions(self, server_id):
        """
        Return the indication subscriptions in a WBEM server owned by this
        subscription manager.

        This function accesses only the local list of owned subscriptions; it
        does not contact the WBEM server. The local list of owned subscriptions
        is discovered from the WBEM server when the server is registered with
        the subscription manager, and is maintained from then on as changes
        happen through this subscription manager.

        Parameters:

          server_id (:term:`string`):
            The server ID of the WBEM server, returned by
            :meth:`~pywbem.WBEMSubscriptionManager.add_server`.

        Returns:

            :class:`py:list` of :class:`~pywbem.CIMInstance`: The indication
            subscription instances.
        """

        # Validate server_id
        self._get_server(server_id)

        return list(self._owned_subscriptions[server_id])

    def get_all_subscriptions(self, server_id):
        """
        Return all indication subscriptions in a WBEM server.

        This function contacts the WBEM server and retrieves the indication
        subscriptions by enumerating the instances of CIM class
        "CIM_IndicationSubscription" in the Interop namespace of the WBEM
        server.

        Parameters:

          server_id (:term:`string`):
            The server ID of the WBEM server, returned by
            :meth:`~pywbem.WBEMSubscriptionManager.add_server`.

        Returns:

            :class:`py:list` of :class:`~pywbem.CIMInstance`: The indication
            subscription instances.

        Raises:

            Exceptions raised by :class:`~pywbem.WBEMConnection`.
        """

        # Validate server_id
        server = self._get_server(server_id)

        return server.conn.EnumerateInstances(SUBSCRIPTION_CLASSNAME,
                                              namespace=server.interop_ns)

    def remove_subscriptions(self, server_id, sub_paths):
        # pylint: disable=line-too-long
        """
        Remove indication subscription(s) from a WBEM server, by deleting the
        indication subscription instances in the server.

        The indication subscriptions must be owned or permanent (i.e. not
        static).

        Parameters:

          server_id (:term:`string`):
            The server ID of the WBEM server, returned by
            :meth:`~pywbem.WBEMSubscriptionManager.add_server`.

          sub_paths (:class:`~pywbem.CIMInstanceName` or list of :class:`~pywbem.CIMInstanceName`):
            Instance path(s) of the indication subscription instance(s) in the
            WBEM server.

        Raises:

            Exceptions raised by :class:`~pywbem.WBEMConnection`.
        """  # noqa: E501

        # Validate server_id
        server = self._get_server(server_id)

        # If list, recursively call this function with each list item.
        if isinstance(sub_paths, list):
            for sub_path in sub_paths:
                self.remove_subscriptions(server_id, sub_path)
            return

        # Here, the variable will be a single list item.
        sub_path = sub_paths

        server.conn.DeleteInstance(sub_path)

        inst_list = self._owned_subscriptions[server_id]
        # We iterate backwards because we change the list
        for i in six.moves.range(len(inst_list) - 1, -1, -1):
            inst = inst_list[i]
            if inst.path == sub_path:
                del inst_list[i]
                # continue loop to find any possible duplicate entries

    def _create_destination(self, server_id, dest_url, owned):
        """
        Create a listener destination instance in the Interop namespace of a
        WBEM server and return that instance.

        In order to catch any changes the server applies, the instance is
        retrieved again using the instance path returned by instance creation.

        Parameters:

          server_id (:term:`string`):
            The server ID of the WBEM server, returned by
            :meth:`~pywbem.WBEMSubscriptionManager.add_server`.

          dest_url (:term:`string`):
            URL of the listener that is used by the WBEM server to send any
            indications to.

            The URL scheme (e.g. http/https) determines whether the WBEM server
            uses HTTP or HTTPS for sending the indication. Host and port in the
            URL specify the target location to be used by the WBEM server.

          owned (:class:`py:bool`):
            Defines whether or not the created instance is *owned* by the
            subscription manager.

        Returns:

            :class:`~pywbem.CIMInstance`: The created instance, as retrieved
            from the server.

        Raises:

            Exceptions raised by :class:`~pywbem.WBEMConnection`.
        """

        # Validate server_id
        server = self._get_server(server_id)

        # validate the URL by reconstructing it. Do not allow defaults
        host, port, ssl = parse_url(dest_url, allow_defaults=False)
        schema = 'https' if ssl else 'http'
        listener_url = '{0}://{1}:{2}'.format(schema, host, port)

        this_host = getfqdn()
        ownership = "owned" if owned else "permanent"

        dest_path = CIMInstanceName(DESTINATION_CLASSNAME,
                                    namespace=server.interop_ns)

        dest_inst = CIMInstance(DESTINATION_CLASSNAME)
        dest_inst.path = dest_path
        dest_inst['CreationClassName'] = DESTINATION_CLASSNAME
        dest_inst['SystemCreationClassName'] = SYSTEM_CREATION_CLASSNAME
        dest_inst['SystemName'] = this_host
        dest_inst['Name'] = _format(
            'pywbemdestination:{0}:{1}:{2}',
            ownership, self._subscription_manager_id, uuid.uuid4())
        dest_inst['Destination'] = listener_url

        if owned:
            for i, inst in enumerate(self._owned_destinations[server_id]):
                if inst.path == dest_path:
                    # It already exists, now check its properties
                    if inst != dest_inst:
                        server.conn.ModifyInstance(dest_inst)
                        dest_inst = server.conn.GetInstance(dest_path)
                        self._owned_destinations[server_id][i] = dest_inst
                    return dest_inst
            dest_path = server.conn.CreateInstance(dest_inst)
            dest_inst = server.conn.GetInstance(dest_path)
            self._owned_destinations[server_id].append(dest_inst)
        else:
            # Responsibility to ensure it does not exist yet is with the user
            dest_path = server.conn.CreateInstance(dest_inst)
            dest_inst = server.conn.GetInstance(dest_path)

        return dest_inst

    def _create_filter(self, server_id, source_namespace, query,
                       query_language, owned, filter_id, name):
        """
        Create a :term:`dynamic indication filter` instance in the Interop
        namespace of a WBEM server and return that instance.

        In order to catch any changes the server applies, the instance is
        retrieved again using the instance path returned by instance creation.

        Parameters:

          server_id (:term:`string`):
            The server ID of the WBEM server, returned by
            :meth:`~pywbem.WBEMSubscriptionManager.add_server`.

          source_namespace (:term:`string`):
            Source namespace of the indication filter.

          query (:term:`string`):
            Filter query in the specified query language.

          query_language (:term:`string`):
            Query language for the specified filter query.

            Examples: 'WQL', 'DMTF:CQL'.

          owned (:class:`py:bool`):
            Defines whether or not the created instance is *owned* by the
            subscription manager.

          filter_id (:term:`string`):
            Filter ID string to be incorporated into the `Name` property of the
            filter instance, as detailed for `subscription_manager_id`, or
            `None`.
            Mutually exclusive with the `name` parameter.

          name (:term:`string`):
            Value for the `Name` property of the filter instance, or `None`.
            Mutually exclusive with the `filter_id` parameter.

        Returns:

            :class:`~pywbem.CIMInstance`: The created instance, as retrieved
            from the server.

        Raises:

            Exceptions raised by :class:`~pywbem.WBEMConnection`.
        """

        # Validate server_id
        server = self._get_server(server_id)

        this_host = getfqdn()
        ownership = "owned" if owned else "permanent"

        filter_path = CIMInstanceName(FILTER_CLASSNAME,
                                      namespace=server.interop_ns)

        filter_inst = CIMInstance(FILTER_CLASSNAME)
        filter_inst.path = filter_path
        filter_inst['CreationClassName'] = FILTER_CLASSNAME
        filter_inst['SystemCreationClassName'] = SYSTEM_CREATION_CLASSNAME
        filter_inst['SystemName'] = this_host
        if filter_id:
            filter_inst['Name'] = _format(
                'pywbemfilter:{0}:{1}:{2}:{3}',
                ownership, self._subscription_manager_id, filter_id,
                uuid.uuid4())
        if name:
            filter_inst['Name'] = name
        filter_inst['SourceNamespace'] = source_namespace
        filter_inst['Query'] = query
        filter_inst['QueryLanguage'] = query_language

        if owned:
            for i, inst in enumerate(self._owned_filters[server_id]):
                if inst.path == filter_path:
                    # It already exists, now check its properties
                    if inst != filter_inst:
                        server.conn.ModifyInstance(filter_inst)
                        filter_inst = server.conn.GetInstance(filter_path)
                        self._owned_filters[server_id][i] = filter_inst
                    return filter_inst
            filter_path = server.conn.CreateInstance(filter_inst)
            filter_inst = server.conn.GetInstance(filter_path)
            self._owned_filters[server_id].append(filter_inst)
        else:
            # Responsibility to ensure it does not exist yet is with the user
            filter_path = server.conn.CreateInstance(filter_inst)
            filter_inst = server.conn.GetInstance(filter_path)

        return filter_inst

    def _create_subscription(self, server_id, dest_path, filter_path, owned):
        """
        Create an indication subscription instance in the Interop namespace of
        a WBEM server and return that instance.

        In order to catch any changes the server applies, the instance is
        retrieved again using the instance path returned by instance creation.

        Parameters:

          server_id (:term:`string`):
            The server ID of the WBEM server, returned by
            :meth:`~pywbem.WBEMSubscriptionManager.add_server`.

          dest_path (:class:`~pywbem.CIMInstanceName`):
            Instance path of the listener destination instance in the WBEM
            server that references this listener.

          filter_path (:class:`~pywbem.CIMInstanceName`):
            Instance path of the indication filter instance in the WBEM
            server that specifies the indications to be sent.

          owned (:class:`py:bool`):
            Defines whether or not the created instance is *owned* by the
            subscription manager.

        Returns:

            :class:`~pywbem.CIMInstance`: The created instance, as retrieved
            from the server.

        Raises:

            Exceptions raised by :class:`~pywbem.WBEMConnection`.
        """

        # Validate server_id
        server = self._get_server(server_id)

        sub_path = CIMInstanceName(SUBSCRIPTION_CLASSNAME,
                                   namespace=server.interop_ns)

        sub_inst = CIMInstance(SUBSCRIPTION_CLASSNAME)
        sub_inst.path = sub_path
        sub_inst['Filter'] = filter_path
        sub_inst['Handler'] = dest_path

        if owned:
            for inst in self._owned_subscriptions[server_id]:
                if inst.path == sub_path:
                    # It does not have any properties besides its keys,
                    # so checking the path is sufficient.
                    return sub_inst
            sub_path = server.conn.CreateInstance(sub_inst)
            sub_inst = server.conn.GetInstance(sub_path)
            self._owned_subscriptions[server_id].append(sub_inst)
        else:
            # Responsibility to ensure it does not exist yet is with the user
            sub_path = server.conn.CreateInstance(sub_inst)
            sub_inst = server.conn.GetInstance(sub_path)

        return sub_inst
