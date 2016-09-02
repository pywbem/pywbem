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
The :class:`~pywbem.WBEMSubscriptionManager` class is a subscription manager
that provides for creating and removing indication subscriptions (including
indication filters and listener destinations) for multiple WBEM servers and
multiple WBEM listeners and for getting information about existing indication
subscriptions.

The WBEM listener is identified through its URL, so it may be a
:class:`~pywbem.WBEMListener` object or any external WBEM listener.

This subscription manager supports two types of subscriptions:

* **Owned subscriptions, filters, and listener destinations** -
  These are indication subscription, indication filter and listener destination
  CIM instances in a WBEM server whose life cycle is bound to the life cycle of
  the registration of that WBEM server with the subscription manager.

  Such owned CIM instances are deleted automatically when their WBEM server is
  deregistered from the subscription manager
  (see :meth:`~pywbem.WBEMSubscriptionManager.remove_server` and
  :meth:`~pywbem.WBEMSubscriptionManager.remove_all_servers`).

* **Not-owned subscriptions, filters, and listener destinations** -
  These are indication subscription, indication filter and listener destination
  CIM instances in a WBEM server whose life cycle is independent of the life
  cycle of the registration of that WBEM server with the subscription manager.

  Such not-owned CIM instances are not deleted automatically when their WBEM
  server is deregistered from the subscription manager. Instead, the user
  needs to take care of deleting them (if they can and should be deleted).
  For example, static indication filters can be used for subscribing to them
  using this subscription manager, but they cannot be deleted (static
  indication filters are those that by definition pre-exist in the WBEM
  server). Also, if some other entity has created such CIM instances in a WBEM
  server, this client may want to use them but not delete them.

Owned and not-owned subscriptions, filters, and listener destinations can be
arbitrarily mixed, with one exception: A not-owned subscription can only be
created between a not-owned filter and a not-owned listener destination.
This restriction is enforced by the :class:`~pywbem.WBEMSubscriptionManager`
class, and it is motivated by the fact that an indication subscription
depends on the indication filter and on the listener destination it relates.
The automatic removal of an owned filter or an owned listener destination
would therefore not be possible if a subscription relating them was not-owned.

Examples
--------

The following example code combines a subscription manager and listener to
subscribe for a CIM alert indication on two WBEM servers and register a
callback function for indication delivery::

    import sys
    from socket import getfqdn
    from pywbem import WBEMConnection, WBEMListener, WBEMServer,
                       WBEMSubscriptionManager

    def process_indication(indication, host):
        '''This function gets called when an indication is received.'''

        print("Received CIM indication from {host}: {ind!r}". \\
            format(host=host, ind=indication))

    def main():

        certkeyfile = 'listener.pem'

        url1 = 'http://server1'
        conn1 = WBEMConnection(url1)
        server1 = WBEMServer(conn1)
        server1.determine_interop_ns()

        url2 = 'http://server2'
        conn2 = WBEMConnection(url2)
        server2 = WBEMServer(conn2)
        server2.validate_interop_ns('root/PG_InterOp')

        my_listener = WBEMListener(host=getfqdn()
                                http_port=5988,
                                https_port=5989,
                                certfile=certkeyfile,
                                keyfile=certkeyfile)
        my_listener.add_callback(process_indication)
        listener.start()

        subscription_manager = WBEMSubscriptionManager(
            subscription_manager_id='fred')

        server1_id = subscription_manager.add_server(server1)
        subscription_manager.add_listener_destinations(server1_id,
                                                      'http://localhost:5988')

        server2_id = subscription_manager.add_server(server2_id)
        subscription_manager.add_listener_destinations(server2,
                                                      'https://localhost:5989')


        # Subscribe for a static filter of a given name
        filter1_paths = subscription_manager.get_all_filters(url1)
        for fp in filter1_paths:
            if fp.keybindings['Name'] == \\
               "DMTF:Indications:GlobalAlertIndicationFilter":
                subscription_manager.add_subscription(url1, fp)
                break

        # Create a dynamic alert indication filter and subscribe for it
        filter2_path = subscription_manager.add_filter(
            url2,
            query_language="DMTF:CQL"
            query="SELECT * FROM CIM_AlertIndication " \\
                  "WHERE OwningEntity = 'DMTF' " \\
                  "AND MessageID LIKE 'SVPC0123|SVPC0124|SVPC0125'")

        subscription_manager.add_subscription(server2_id, filter2_path)

Another more practical example is in the script
``examples/pegIndicationTest.py`` (when you clone the GitHub pywbem/pywbem
project).
"""

from socket import getfqdn
import uuid
import six

from ._server import WBEMServer
from ._version import __version__
from .cim_obj import CIMInstance, CIMInstanceName
from .cim_http import parse_url

# CIM model classnames for subscription components
SUBSCRIPTION_CLASSNAME = 'CIM_IndicationSubscription'
DESTINATION_CLASSNAME = 'CIM_ListenerDestinationCIMXML'
FILTER_CLASSNAME = 'CIM_IndicationFilter'
SYSTEM_CREATION_CLASSNAME = 'CIM_ComputerSystem'

DEFAULT_QUERY_LANGUAGE = 'WQL'

__all__ = ['WBEMSubscriptionManager']

class WBEMSubscriptionManager(object):
    """
    A Client to manage subscriptions to indications and optionally control
    the existence of a listener.

    """

    def __init__(self, subscription_manager_id=None):
        #pylint: disable=line-too-long
        """
        Parameters:

          subscription_manager_id (:term:`string`):
            A subscription manager ID string that is used as a component in
            the value of the `Name` properties of filter and listener
            destination instances to help the user identify these instances in
            a WBEM server.

            The string must consist of printable characters, and not contain
            the character ':' because that is the separator between components
            within the value of these `Name` properties.

            There is no requirement that the subscription manager ID be unique.

            `None` indicates that the subscription manager ID should not be
            included in the value of these `Name` properties.

            For example, the form of the `Name` property of a filter instance
            is:

              ``"pywbemfilter:" [{subscription_manager_id} ":"]
              [{filter_id} ":"] {guid}``
        """

        # The following dictionaries have the WBEM server ID as a key.
        self._servers = {}  # WBEMServer objects for the WBEM servers
        self._owned_subscription_paths = {}  # CIMInstanceName of subscriptions
        self._owned_filter_paths = {}  # CIMInstanceName of dynamic filters
        self._owned_destination_paths = {}  #destination paths for server

        if subscription_manager_id is None:
            self._subscription_manager_id = subscription_manager_id
        elif isinstance(subscription_manager_id, six.string_types):
            if ':' in subscription_manager_id:
                raise ValueError("Subscription manager ID contains ':': %s" % \
                                 subscription_manager_id)
            self._subscription_manager_id = subscription_manager_id
        else:
            raise TypeError("Invalid type for subscription manager ID: %r" % \
                            subscription_manager_id)

    def __repr__(self):
        """
        Return a representation of the :class:`~pywbem.WBEMSubscriptionManager`
        object with all attributes, that is suitable for debugging.
        """
        return "%s(_subscription_manager_id=%r, _servers=%r, " \
               "_owned_subscription_paths=%r, _owned_filter_paths=%r, " \
               "_owned_destinations=%r)" % \
               (self.__class__.__name__, self._subscription_manager_id,
                self._servers, self._owned_subscription_paths,
                self._owned_filter_paths, self._owned_destination_paths)

    def _get_server(self, server_id):
        """
            Internal method to get the server object given a server_id.

        Parameters:

          server_id (:term:`string`):
            The server ID for the WBEM server, returned by
            :meth:`~pywbem.WBEMSubscriptionManager.add_server`.

        Returns:

             server (:class:`~pywbem.WBEMServer`):
             The WBEM server.

        Raises:

            ValueError: server_id not known to subscription manager.
        """

        if server_id not in self._servers:
            raise ValueError('WBEM server %s not known by subscription '
                             'manager' % server_id)

        return self._servers[server_id]

    #pylint: disable=line-too-long
    def add_listener_destinations(self, server_id, listener_urls, owned=True):
        """
        Register a WBEM listener to be the target of indications sent by a
        WBEM server.

        This function automatically creates a listener destination instance
        (of CIM class "CIM_ListenerDestinationCIMXML") for each specified
        listener in the Interop namespace of the specified WBEM server.

        Parameters:

          server_id (:term:`string`):
            The server ID for the WBEM server, returned by
            :meth:`~pywbem.WBEMSubscriptionManager.add_server`.

          listener_urls (:term:`string` or list of :term:`string`):
            The URL or URLs of the WBEM listeners to be registered.

            The WBEM listener may be a :class:`~pywbem.WBEMListener` object or
            any external WBEM listener.

            Each listener URL string must have the format:

              ``[{scheme}://]{host}[:{port}]``

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

            If no port is specified in the URL, the default ports are:

            * If HTTPS is used, port 5989.
            * If HTTP is used, port 5988.

            See :class:`~pywbem.WBEMConnection` for examples of valid URLs.

          owned (:class:`py:bool`)
            Defines whether or not the listener destination instances that are
            created in the WBEM server are *owned* by the subscription manager.

            If `True`, these listener destination instances are owned and will
            have a life cycle that is bound to the registration of the WBEM
            server within this subscription manager. The user does not need to
            take care of deleting these instances in the WBEM server. Instead,
            if the WBEM server is deregistered from this subscription manager
            (see :meth:`~pywbem.WBEMSubscriptionManager.remove_server` and
            :meth:`~pywbem.WBEMSubscriptionManager.remove_all_servers`), these
            listener destination instances will be automatically deleted in the
            WBEM server.

            If `False`, these listener destination instances are not-owned and
            will have a life cycle that is independent of the registration of
            the WBEM server within this subscription manager. The user is
            responsible for deleting these listener destination instances
            explicitly (for example by using
            :meth:`~pywbem.WBEMSubscriptionManager.remove_destinations`).

        Returns:

            :class:`py:list` of :class:`~pywbem.CIMInstanceName`: The instance
            paths of the created listener destination instances for the defined
            listener URLs.

        Raises:

            Exceptions raised by :class:`~pywbem.WBEMConnection`.
        """

        # If list, recursively call this function with each entry
        if isinstance(listener_urls, list):
            dest_paths = []
            for listener_url in listener_urls:
                listener_dest_paths = self.add_listener_destinations(
                    server_id, listener_url)
                dest_paths.extend(listener_dest_paths)
            return dest_paths

        # Process a single URL
        listener_url = listener_urls    # documents that this is single URL

        server = self._get_server(server_id)

        dest_path = _create_destination(server, listener_url,
                                        self._subscription_manager_id)

        if owned:
            self._owned_destination_paths[server_id].append(dest_path)

        return [dest_path]

    def add_server(self, server):
        """
        Register a WBEM server with the subscription manager. This is a
        prerequisite for lateron adding listener destinations, indication
        filters and indication subscriptions to the server.

        Parameters:

          server (:class:`~pywbem.WBEMServer`):
            The WBEM server.

        Returns:

            :term:`string`: An ID for the WBEM server, for use by other
            methods of this class.

        Raises:

            Exceptions raised by :class:`~pywbem.WBEMConnection`.
        """

        if not isinstance(server, WBEMServer):
            raise TypeError("Server argument of add_server() must be a " \
                            "WBEMServer object")
        server_id = server.url
        if server_id in self._servers:
            raise ValueError("WBEM server already known by listener: %s" % \
                             server_id)

        # Create dictionary entries for this server
        self._servers[server_id] = server
        self._owned_subscription_paths[server_id] = []
        self._owned_filter_paths[server_id] = []
        self._owned_destination_paths[server_id] = []

        return server_id

    def remove_all_servers(self):
        """
        Remove all registered WBEM servers from the subscription manager. This
        also unregisters listeners from these servers and removes all owned
        indication subscriptions, owned indication filters, and owned listener
        destinations that were created by this subscription manager.

        This is, in effect, a complete shutdown of the subscription manager.

        Raises:

            Exceptions raised by :class:`~pywbem.WBEMConnection`.
        """

        for server in self._servers:
            # This depends on server.url same as server_id
            self.remove_server(server.url)

    def remove_server(self, server_id):
        """
        Remove a registered WBEM server from the subscription manager. This
        also unregisters listeners from that server and removes all owned
        indication subscriptions, owned indication filters and owned listener
        destinations that were created by this subscription manager for that
        server.

        Parameters:

          server_id (:term:`string`):
            The server ID for the WBEM server, returned by
            :meth:`~pywbem.WBEMSubscriptionManager.add_server`.

        Raises:

            Exceptions raised by :class:`~pywbem.WBEMConnection`.
        """

        server = self._get_server(server_id)

        # Delete any instances we recorded to be cleaned up

        if server_id in self._owned_subscription_paths:
            paths = self._owned_subscription_paths[server_id]
            for path in paths:
                server.conn.DeleteInstance(path)
            del self._owned_subscription_paths[server_id]

        if server_id in self._owned_filter_paths:
            paths = self._owned_filter_paths[server_id]
            for path in paths:
                server.conn.DeleteInstance(path)
            del self._owned_filter_paths[server_id]

        if server_id in self._owned_destination_paths:
            for path in self._owned_destination_paths[server_id]:
                server.conn.DeleteInstance(path)
            del self._owned_destination_paths[server_id]

        # Remove server from this listener
        del self._servers[server_id]


    def add_filter(self, server_id, source_namespace, query,
                   query_language=DEFAULT_QUERY_LANGUAGE,
                   owned=True,
                   filter_id=None):
        #pylint: disable=line-too-long
        """
        Add a dynamic indication filter to a WBEM server, by creating an
        indication filter instance (of CIM class "CIM_IndicationFilter") in the
        Interop namespace of the server.

        Dynamic indication filters are those that are created by clients.
        Indication filters that pre-exist in the WBEM server are termed
        *static indication filters* and cannot be created or removed by
        clients. See :term:`DSP1054` for details about indication filters.

        Parameters:

          server_id (:term:`string`):
            The server ID for the WBEM server, returned by
            :meth:`~pywbem.WBEMSubscriptionManager.add_server`.

          source_namespace (:term:`string`):
            Source namespace of the indication filter.

          query (:term:`string`):
            Filter query in the specified query language.

          query_language (:term:`string`):
            Query language for the specified filter query.

            Examples: 'WQL', 'DMTF:CQL'.

          owned (:class:`py:bool`)
            Defines whether or not the filter instances that are created in the
            WBEM server are *owned* by the subscription manager.

            If `True`, these filter instances are owned and will have a life
            cycle that is bound to the registration of the WBEM server within
            this subscription manager. The user does not need to take care of
            deleting these instances in the WBEM server. Instead, if the WBEM
            server is deregistered from this subscription manager
            (see :meth:`~pywbem.WBEMSubscriptionManager.remove_server` and
            :meth:`~pywbem.WBEMSubscriptionManager.remove_all_servers`), these
            filter instances will be automatically deleted in the WBEM server.
            Of course, the user may still delete these filter instances
            explicitly (for example by using
            :meth:`~pywbem.WBEMSubscriptionManager.remove_filter`).

            If `False`, these filter instances are not-owned and will have a
            life cycle that is independent of the registration of the WBEM
            server within this subscription manager. The user is responsible
            for deleting these filter instances explicitly (for example by
            using :meth:`~pywbem.WBEMSubscriptionManager.remove_filter`).

          filter_id (:term:`string`)
            A filter ID string that is used as a component in the value of the
            `Name` properties of filter instances to help the user identify
            these instances in a WBEM server.
            
            There is no requirement that the filter ID be unique. This can be
            used to identify groups of filters by using the same value for
            multiple filters.

            The string must consist of printable characters, and not contain
            the character ':' because that is the separator between components
            within the value of these `Name` properties.

            `None` indicates that the filter ID should not be included in the
            value of these `Name` properties.

            The form of the `Name` property of the created filter instance is:

              ``"pywbemfilter:" [{subscription_manager_id} ":"]
              [{filter_id} ":"] {guid}``

        Returns:

            :class:`~pywbem.CIMInstanceName`: The instance path of the
            indication filter instance.

        Raises:

            Exceptions raised by :class:`~pywbem.WBEMConnection`.
        """
        server = self._get_server(server_id)

        # create a single filter for a server.
        filter_path = _create_filter(server, source_namespace, query,
                                     query_language,
                                     self._subscription_manager_id,
                                     filter_id)

        if owned:
            self._owned_filter_paths[server_id].append(filter_path)

        return filter_path

    def remove_filter(self, server_id, filter_path):
        """
        Remove an indication filter from a WBEM server, by deleting the
        indication filter instance in the WBEM server.

        The indication filter must be a dynamic filter (static filters
        cannot be removed by clients) but may be owned or not-owned.

        Parameters:

          server_id (:term:`string`):
            The server ID for the WBEM server, returned by
            :meth:`~pywbem.WBEMSubscriptionManager.add_server`.

          filter_path (:class:`~pywbem.CIMInstanceName`):
            Instance path of the indication filter instance in the WBEM
            server.

        Raises:

            Exceptions raised by :class:`~pywbem.WBEMConnection`.
        """
        server = self._get_server(server_id)
        server.conn.DeleteInstance(filter_path)

        paths = self._owned_filter_paths[server_id]
        for i, path in enumerate(paths):
            if path == filter_path:
                del paths[i]
                # continue look to find any possible duplicate entries

    def get_owned_filters(self, server_id):
        """
        Return the owned indication filters in a WBEM server that have been
        created by this subscription manager.

        This function accesses only the local list of owned filters; it does
        not contact the WBEM server.

        Parameters:

          server_id (:term:`string`):
            The server ID for the WBEM server, returned by
            :meth:`~pywbem.WBEMSubscriptionManager.add_server`.

        Returns:

            :class:`py:list` of :class:`~pywbem.CIMInstanceName`: The instance
            paths of the indication filter instances.

        Raises:

            Exceptions raised by :class:`~pywbem.WBEMConnection`.
        """
        _ = self._get_server(server_id)

        return self._owned_filter_paths[server_id]

    def get_all_filters(self, server_id):
        """
        Return all indication filters in a WBEM server.

        This function contacts the WBEM server and retrieves the indication
        filters by enumerating the instances of CIM class
        "CIM_IndicationFilter" in the Interop namespace of the WBEM server.

        Parameters:

          server_id (:term:`string`):
            The server ID for the WBEM server, returned by
            :meth:`~pywbem.WBEMSubscriptionManager.add_server`.

        Returns:

            :class:`py:list` of :class:`~pywbem.CIMInstanceName`: The instance
            paths of the indication filter instances.

        Raises:

            Exceptions raised by :class:`~pywbem.WBEMConnection`.
        """
        server = self._get_server(server_id)

        return server.conn.EnumerateInstanceNames('CIM_IndicationFilter',
                                                  namespace=server.interop_ns)

    def add_subscriptions(self, server_id, filter_path, destination_paths=None,
                          owned=True):
        """
        Add subscriptions to a WBEM server for a particular set of indications
        defined by an indication filter and for a particular set of WBEM
        listeners defined by the instance paths of their listener destination
        instances in that WBEM server, by creating indication subscription
        instances (of CIM class "CIM_IndicationSubscription") in the Interop
        namespace of that server.

        The indication filter can be an (owned or not-owned) dynamic filter
        created via :meth:`~pywbem.WBEMSubscriptionManager.add_filter`,
        or a dynamic or static filter that already exists in the WBEM server.
        Existing filters in the WBEM server can be retrieved via
        :meth:`~pywbem.WBEMSubscriptionManager.get_all_filters`.

        Upon successful return of this method, the added subscriptions are
        active, so that the specified WBEM listeners may immediately receive
        indications.

        Parameters:

          server_id (:term:`string`):
            The server ID for the WBEM server, returned by
            :meth:`~pywbem.WBEMSubscriptionManager.add_server`.

          filter_path (:class:`~pywbem.CIMInstanceName`):
            Instance path of the indication filter instance in the WBEM
            server that specifies the indications to be sent. When creating
            not-owned subscriptions, this must be a not-owned filter.

          destination_paths (:class:`~pywbem.CIMInstanceName` or list of :class:`~pywbem.CIMInstanceName`):
            If not `None`, the instance paths of the listener destination
            instances in the specified WBEM server that will become the
            destinations for the created subscriptions. When creating not-owned
            subscriptions, this must be a not-owned listener destination.
            
          owned (:class:`py:bool`)
            Defines whether or not the subscription instances that are created
            in the WBEM server are *owned* by the subscription manager.

            If `True`, these subscription instances are owned and will have a
            life cycle that is bound to the registration of the WBEM server
            within this subscription manager. The user does not need to take
            care of deleting these subscription instances in the WBEM server.
            Instead, if the WBEM server is deregistered from this subscription
            manager (see :meth:`~pywbem.WBEMSubscriptionManager.remove_server`
            and :meth:`~pywbem.WBEMSubscriptionManager.remove_all_servers`),
            these subscription instances will be automatically deleted in the
            WBEM server. Of course, the user may still delete these
            subscription instances explicitly (for example by using
            :meth:`~pywbem.WBEMSubscriptionManager.remove_subscriptions`).

            If `False`, these subscription instances are not-owned and will
            have a life cycle that is independent of the registration of the
            WBEM server within this subscription manager. The user is
            responsible for deleting these subscription instances explicitly
            (for example by using
            :meth:`~pywbem.WBEMSubscriptionManager.remove_subscriptions`).

        Returns:

            :class:`py:list` of :class:`~pywbem.CIMInstanceName`: The instance
            paths of the indication subscription instances created in the WBEM
            server.

        Raises:

            Exceptions raised by :class:`~pywbem.WBEMConnection`.
        """
        # validate server_id
        server = self._get_server(server_id)

        sub_paths = []

        # set destination_paths to either input or owned destination_paths
        if destination_paths is None:
            destination_paths = self._owned_destination_paths[server_id]
        elif not isinstance(destination_paths, list):
            destination_paths = [destination_paths]

        # Validate that owned flag and owned status of path matches
        if not owned and filter_path in self._owned_filter_paths[server_id]:
            raise ValueError("Not-owned subscription cannot be created on "\
                             "owned filter: %s" % filter_path)

        for dest_path in destination_paths:

            # Validate that owned flag and owned status of paths match
            if not owned and \
               dest_path in self._owned_destination_paths[server_id]:
                raise ValueError("Not-owned subscription cannot be created "\
                                 "on owned listener destination: %s" % \
                                 dest_path)

            sub_path = _create_subscription(server, dest_path, filter_path)
            sub_paths.append(sub_path)
            if owned:
                self._owned_subscription_paths[server_id].append(sub_path)

        return sub_paths

    def remove_subscriptions(self, server_id, sub_paths):
        """
        Remove indication subscription(s) from a WBEM server, by deleting the
        indication subscription instances in the server.

        The indication subscriptions may be owned or not-owned.

        Parameters:

          server_id (:term:`string`):
            The server ID for the WBEM server, returned by
            :meth:`~pywbem.WBEMSubscriptionManager.add_server`.

          sub_paths (:class:`~pywbem.CIMInstanceName` or list of :class:`~pywbem.CIMInstanceName`):
            Instance path(s) of the indication subscription instance(s) in the
            WBEM server.

        Raises:

            Exceptions raised by :class:`~pywbem.WBEMConnection`.
        """

        # if list, recursively call this remove subscriptions for each entry
        if isinstance(sub_paths, list):
            for sub_path in sub_paths:
                self.remove_subscriptions(server_id, sub_path)
            return

        # Here sub_paths will contain only a single path entry
        server = self._get_server(server_id)

        sub_path = sub_paths        # assign to internal variable for clarity
        server.conn.DeleteInstance(sub_path)

        sub_path_list = self._owned_subscription_paths[server_id]
        for i, path in enumerate(sub_path_list):
            if path == sub_path:
                del sub_path_list[i]
                # continue to end of list to pick up any duplicates

    def remove_destinations(self, server_id, destination_paths):
        """
        Remove listener destinations from a WBEM server, by deleting the
        listener destination instances in the server.

        The listener destination instances must be not-owned. Owned listener
        destination instances are not allowed to be removed using this method,
        because the subscription manager will automatically remove them when
        the WBEM server is deregistered from it.

        Parameters:

          server_id (:term:`string`):
            The server ID for the WBEM server, returned by
            :meth:`~pywbem.WBEMSubscriptionManager.add_server`.

          destination_paths (:class:`~pywbem.CIMInstanceName` or list of :class:`~pywbem.CIMInstanceName`):
            Instance path(s) of the listener destination instance(s) in the
            WBEM server.

        Raises:

            Exceptions raised by :class:`~pywbem.WBEMConnection`.
        """

        # if list, recursively call this remove subscriptions for each entry
        if isinstance(destination_paths, list):
            for dest_path in destination_paths:
                self.remove_destinations(server_id, dest_path)
            return

        # Here sub_paths will contain only a single path entry
        server = self._get_server(server_id)

        dest_path = destination_paths  # assign to internal variable for clarity
        if dest_path in self._owned_destination_paths:
            raise ValueError("Not allowed to remove owned listener "\
                             "destination: %s" % dest_path)

        server.conn.DeleteInstance(dest_path)

    def get_owned_subscriptions(self, server_id):
        """
        Return the owned indication subscriptions for a WBEM server that have
        been created by this subscription manager.

        This function accesses only the local list of owned subscriptions; it
        does not contact the WBEM server.

        Parameters:

          server_id (:term:`string`):
            The server ID for the WBEM server, returned by
            :meth:`~pywbem.WBEMSubscriptionManager.add_server`.

        Returns:

            :class:`py:list` of :class:`~pywbem.CIMInstanceName`: The instance
            paths of the indication subscription instances.

        Raises:

            Exceptions raised by :class:`~pywbem.WBEMConnection`.
        """

        # validate that this server exists.
        _ = self._get_server(server_id)

        return self._owned_subscription_paths[server_id]

    def get_all_subscriptions(self, server_id):
        """
        Return all indication subscriptions in a WBEM server.

        This function contacts the WBEM server and retrieves the indication
        subscriptions by enumerating the instances of CIM class
        "CIM_IndicationSubscription" in the Interop namespace of the WBEM
        server.

        Parameters:

          server_id (:term:`string`):
            The server ID for the WBEM server, returned by
            :meth:`~pywbem.WBEMSubscriptionManager.add_server`.

        Returns:

            :class:`py:list` of :class:`~pywbem.CIMInstanceName`: The instance
            paths of the indication subscription instances.

        Raises:

            Exceptions raised by :class:`~pywbem.WBEMConnection`.
        """
        server = self._get_server(server_id)

        return server.conn.EnumerateInstanceNames(SUBSCRIPTION_CLASSNAME,
                                                  namespace=server.interop_ns)

    def get_all_destinations(self, server_id):
        """
        Return all listener destinations in a WBEM server.

        This function contacts the WBEM server and retrieves the listener
        destinations by enumerating the instances of CIM class
        "CIM_ListenerDestinationCIMXML" in the Interop namespace of the WBEM
        server.

        Parameters:

          server_id (:term:`string`):
            The server ID for the WBEM server, returned by
            :meth:`~pywbem.WBEMSubscriptionManager.add_server`.

        Returns:

            :class:`py:list` of :class:`~pywbem.CIMInstanceName`: The instance
            paths of the listener destination instances.

        Raises:

            Exceptions raised by :class:`~pywbem.WBEMConnection`.
        """

        server = self._get_server(server_id)

        return server.conn.EnumerateInstanceNames(DESTINATION_CLASSNAME,
                                                  namespace=server.interop_ns)

def _create_destination(server, dest_url, subscription_manager_id=None):
    """
    Create a listener destination instance in the Interop namespace of a
    WBEM server and return its instance path. Creates the destination
    instance in the server and returns the resulting path.

    Parameters:

      server (:class:`~pywbem.WBEMServer`):
        Identifies the WBEM server.

      dest_url (:term:`string`):
        URL of the listener that is used by the WBEM server to send any
        indications to.

        The URL scheme (e.g. http/https) determines whether the WBEM server
        uses HTTP or HTTPS for sending the indication. Host and port in the
        URL specify the target location to be used by the WBEM server.

      subscription_manager_id (:term:`string`):
        Subscription manager ID string to be incorporated into the `Name`
        property of the destination instance.
        If `None`, the corresponding component is not added.

        The form of the `Name` property of the created destination instance is:
        
          ``"pywbemdestination:" [{subscription_manager_id} ":"]
          {guid}``

    Returns:

        :class:`~pywbem.CIMInstanceName`: The instance path of the created
        instance.

    Raises:

        Exceptions raised by :class:`~pywbem.WBEMConnection`.
    """

    # validate the URL by reconstructing it. Do not allow defaults
    host, port, ssl = parse_url(dest_url, allow_defaults=False)
    schema = 'https' if ssl else 'http'
    listener_url = '{}://{}:{}'.format(schema, host, port)

    dest_path = CIMInstanceName(DESTINATION_CLASSNAME)
    dest_path.classname = DESTINATION_CLASSNAME
    dest_path.namespace = server.interop_ns

    dest_inst = CIMInstance(DESTINATION_CLASSNAME)
    dest_inst.path = dest_path
    dest_inst['CreationClassName'] = DESTINATION_CLASSNAME
    dest_inst['SystemCreationClassName'] = SYSTEM_CREATION_CLASSNAME
    dest_inst['SystemName'] = getfqdn()

    sub_mgr_id = ''
    if subscription_manager_id is not None:
        sub_mgr_id = '%s:' % subscription_manager_id

    dest_inst['Name'] = 'pywbemdestination:%s%s' % (sub_mgr_id,
                                                    uuid.uuid4())
    dest_inst['Destination'] = listener_url
    dest_path = server.conn.CreateInstance(dest_inst)
    return dest_path

def _create_filter(server, source_namespace, query, query_language, \
                   subscription_manager_id=None, filter_id=None):
    """
    Create a dynamic indication filter instance in the Interop namespace
    of a WBEM server and return its instance path.

    Parameters:

      server (:class:`~pywbem.WBEMServer`):
        Identifies the WBEM server.

      source_namespace (:term:`string`):
        Source namespace of the indication filter.

      query (:term:`string`):
        Filter query in the specified query language.

      query_language (:term:`string`):
        Query language for the specified filter query.

        Examples: 'WQL', 'DMTF:CQL'.

      filter_id (:term:`string`):
        Filter ID string to be incorporated into the `Name` property of the
        filter instance, as detailed for `subscription_manager_id`.
        If `None`, the corresponding component is not added.

      subscription_manager_id (:term:`string`):
        Subscription manager ID string to be incorporated into the `Name`
        property of the filter instance.
        If `None`, the corresponding component is not added.

        The form of the `Name` property of the created filter instance is:
        
          ``"pywbemfilter:" [{subscription_manager_id} ":"]
          [{filter_id} ":"] {guid}``

    Returns:

        :class:`~pywbem.CIMInstanceName`: The instance path of the created
        instance.

    Raises:

        Exceptions raised by :class:`~pywbem.WBEMConnection`.
    """

    filter_path = CIMInstanceName(FILTER_CLASSNAME)
    filter_path.classname = FILTER_CLASSNAME
    filter_path.namespace = server.interop_ns

    filter_inst = CIMInstance(FILTER_CLASSNAME)
    if filter_id is None:
        filter_id_ = ''
    elif isinstance(filter_id, six.string_types):
        if ':' in filter_id:
            raise ValueError("Filter ID contains ':': %s" % filter_id)
        filter_id_ = '%s:' % filter_id
    else:
        raise TypeError("Invalid type for filter ID: %r" % filter_id)

    filter_inst.path = filter_path
    filter_inst['CreationClassName'] = FILTER_CLASSNAME
    filter_inst['SystemCreationClassName'] = SYSTEM_CREATION_CLASSNAME
    filter_inst['SystemName'] = getfqdn()

    sub_mgr_id = ''
    if subscription_manager_id is not None:
        sub_mgr_id = '%s:' % (subscription_manager_id)

    filter_inst['Name'] = 'pywbemfilter:%s%s%s' % (sub_mgr_id, \
                                                   filter_id_, \
                                                   uuid.uuid4())
    filter_inst['SourceNamespace'] = source_namespace
    filter_inst['Query'] = query
    filter_inst['QueryLanguage'] = query_language

    filter_path = server.conn.CreateInstance(filter_inst)
    return filter_path

def _create_subscription(server, dest_path, filter_path):
    """
    Create an indication subscription instance in the Interop namespace of
    a WBEM server and return its instance path.

    Parameters:

      server (:class:`~pywbem.WBEMServer`):
        Identifies the WBEM server.

      dest_path (:class:`~pywbem.CIMInstanceName`):
        Instance path of the listener destination instance in the WBEM
        server that references this listener.

      filter_path (:class:`~pywbem.CIMInstanceName`):
        Instance path of the indication filter instance in the WBEM
        server that specifies the indications to be sent.

    Returns:

        :class:`~pywbem.CIMInstanceName`: The instance path of the created
        instance.

    Raises:

        Exceptions raised by :class:`~pywbem.WBEMConnection`.
    """


    sub_path = CIMInstanceName(SUBSCRIPTION_CLASSNAME)
    sub_path.classname = SUBSCRIPTION_CLASSNAME
    sub_path.namespace = server.interop_ns

    sub_inst = CIMInstance(SUBSCRIPTION_CLASSNAME)
    sub_inst.path = sub_path
    sub_inst['Filter'] = filter_path
    sub_inst['Handler'] = dest_path

    sub_path = server.conn.CreateInstance(sub_inst)
    return sub_path
