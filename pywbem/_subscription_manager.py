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

This subscription manager supports two types of subscriptions, filters and
listener destinations:

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
  For example, a :term:`static indication filter` can be used for subscribing
  to it using this subscription manager, but it cannot be deleted. Also, if
  some other entity has created such CIM instances in a WBEM server, this
  client may want to use them but not delete them.

Owned and not-owned subscriptions, filters, and listener destinations can be
arbitrarily mixed, with one exception:

* A not-owned subscription cannot be created with an owned filter and/or an
  owned listener destination because that would prevent the automatic life
  cycle management of the owned filter or listener destination by the
  subscription manager. This restriction is enforced by the
  :class:`~pywbem.WBEMSubscriptionManager` class.

The :class:`~pywbem.WBEMSubscriptionManager` object remembers owned
subscriptions, filters, and listener destinations. If for some reason that
object gets deleted (e.g. because the Python program aborts) before all servers
could be removed, the corresponding CIM instances in the WBEM server still
exist, but the knowledge that these instances were owned by that subscription
manager, is lost. Therefore, these instances will be considered not-owned
by any other subscription managers, including a restarted instance of the
subscription manager that went away.

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

The following example code briefly shows how to use a subscription manager
as a context manager, in order to get automatic cleanup::

    with WBEMSubscriptionManager('fred') as subscription_manager:
        server1_id = subscription_manager.add_server(server1)
        . . .
    # The exit method automatically calls remove_all_servers(), which removes
    # all owned subscriptions, filters and destinations.

Another more practical example is in the script
``examples/pegIndicationTest.py`` (when you clone the GitHub pywbem/pywbem
project).
"""

import re
from socket import getfqdn
import uuid
import six

from ._server import WBEMServer
from .cim_obj import CIMInstance, CIMInstanceName
from .cim_http import parse_url
from .cim_constants import CIM_ERR_FAILED
from .exceptions import CIMError

# CIM model classnames for subscription components
SUBSCRIPTION_CLASSNAME = 'CIM_IndicationSubscription'
DESTINATION_CLASSNAME = 'CIM_ListenerDestinationCIMXML'
FILTER_CLASSNAME = 'CIM_IndicationFilter'
SYSTEM_CREATION_CLASSNAME = 'CIM_ComputerSystem'

DEFAULT_QUERY_LANGUAGE = 'WQL'

__all__ = ['WBEMSubscriptionManager']


class WBEMSubscriptionManager(object):
    """
    A class for managing subscriptions for CIM indications in a WBEM server.

    The class may be used as a Python context manager, in order to get
    automatic clean up (see :meth:`~pywbem.WBEMSubscriptionManager.__exit__`).
    """

    def __init__(self, subscription_manager_id=None):
        # pylint: disable=line-too-long
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
        """

        # The following dictionaries have the WBEM server ID as a key.
        self._servers = {}  # WBEMServer objects for the WBEM servers
        self._owned_subscription_paths = {}  # CIMInstanceName of subscriptions
        self._owned_filter_paths = {}  # CIMInstanceName of dynamic filters
        self._owned_destination_paths = {}  # destination paths for server

        if subscription_manager_id is None:
            raise ValueError("Subscription manager ID must not be None")
        if not isinstance(subscription_manager_id, six.string_types):
            raise TypeError("Invalid type for subscription manager ID: %r" %
                            subscription_manager_id)
        if ':' in subscription_manager_id:
            raise ValueError("Subscription manager ID contains ':': %s" %
                             subscription_manager_id)
        self._subscription_manager_id = subscription_manager_id

    def __repr__(self):
        """
        Return a representation of the :class:`~pywbem.WBEMSubscriptionManager`
        object with all attributes, that is suitable for debugging.
        """
        return "%s(_subscription_manager_id=%r, _servers=%r, " \
               "_owned_subscription_paths=%r, _owned_filter_paths=%r, " \
               "_owned_destination_paths=%r)" % \
               (self.__class__.__name__, self._subscription_manager_id,
                self._servers, self._owned_subscription_paths,
                self._owned_filter_paths, self._owned_destination_paths)

    def __enter__(self):
        """
        Enter method when the class is used as a context manager.
        """
        pass

    def __exit__(self, exc_type, exc_value, traceback):
        """
        Exit method when the class is used as a context manager.

        It cleans up by calling
        :meth:`~pywbem.WBEMSubscriptionManager.remove_all_servers`.
        """
        self.remove_all_servers()
        return False  # re-raise any exceptions

    def _get_server(self, server_id):
        """
            Internal method to get the server object given a server_id.

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
            raise ValueError('WBEM server %s not known by subscription '
                             'manager' % server_id)

        return self._servers[server_id]

    def add_server(self, server):
        """
        Register a WBEM server with the subscription manager. This is a
        prerequisite for adding listener destinations, indication filters and
        indication subscriptions to the server.

        Listener destinations, indication filters, and subscriptions that
        already exist in the WBEM server and that are found to be owned by a
        subscription manager with the same ID on the current host, are
        considered owned by this subscription manager, and will be registered
        accordingly.

        In this process, the ownership of listener destinations and indication
        filters is determined based upon the value of their `Name` property.
        The ownership of subscriptions is determined based upon the ownership
        of the referenced destination and filter instances: If a subscription
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
        """

        if not isinstance(server, WBEMServer):
            raise TypeError("Server argument of add_server() must be a "
                            "WBEMServer object")
        server_id = server.url
        if server_id in self._servers:
            raise ValueError("WBEM server already known by listener: %s" %
                             server_id)

        # Create dictionary entries for this server
        self._servers[server_id] = server
        self._owned_subscription_paths[server_id] = []
        self._owned_filter_paths[server_id] = []
        self._owned_destination_paths[server_id] = []

        # Recover any owned destination, filter, and subscription instances
        # that exist on this server

        this_host = getfqdn()

        dest_name_pattern = re.compile(
            r'^pywbemdestination:owned:%s:%s:[^:]*$' %
            (this_host, self._subscription_manager_id))
        dest_inst_paths = server.conn.EnumerateInstanceNames(
            DESTINATION_CLASSNAME, namespace=server.interop_ns)
        for ip in dest_inst_paths:
            if re.match(dest_name_pattern, ip.keybindings['Name']) \
                    and ip.keybindings['SystemName'] == this_host:
                self._owned_destination_paths[server_id].append(ip)

        filter_name_pattern = re.compile(
            r'^pywbemfilter:owned:%s:%s:[^:]*:[^:]*$' %
            (this_host, self._subscription_manager_id))
        filter_inst_paths = server.conn.EnumerateInstanceNames(
            FILTER_CLASSNAME, namespace=server.interop_ns)
        for ip in filter_inst_paths:
            if re.match(filter_name_pattern, ip.keybindings['Name']) \
                    and ip.keybindings['SystemName'] == this_host:
                self._owned_filter_paths[server_id].append(ip)

        sub_inst_paths = server.conn.EnumerateInstanceNames(
            SUBSCRIPTION_CLASSNAME, namespace=server.interop_ns)
        for ip in sub_inst_paths:
            if ip.keybindings['Filter'] in \
                    self._owned_filter_paths[server_id] \
                    or ip.keybindings['Handler'] in \
                    self._owned_destination_paths[server_id]:
                self._owned_subscription_paths[server_id].append(ip)

        return server_id

    def remove_server(self, server_id):
        """
        Remove a registered WBEM server from the subscription manager. This
        also unregisters listeners from that server and removes all owned
        indication subscriptions, owned indication filters and owned listener
        destinations that were created by this subscription manager for that
        server.

        Parameters:

          server_id (:term:`string`):
            The server ID of the WBEM server, returned by
            :meth:`~pywbem.WBEMSubscriptionManager.add_server`.

        Raises:

            Exceptions raised by :class:`~pywbem.WBEMConnection`.
        """

        server = self._get_server(server_id)

        # Delete any instances we recorded to be cleaned up

        if server_id in list(self._owned_subscription_paths.keys()):
            paths = self._owned_subscription_paths[server_id]
            for path in paths:
                server.conn.DeleteInstance(path)
            del self._owned_subscription_paths[server_id]

        if server_id in list(self._owned_filter_paths.keys()):
            paths = self._owned_filter_paths[server_id]
            for path in paths:
                server.conn.DeleteInstance(path)
            del self._owned_filter_paths[server_id]

        if server_id in list(self._owned_destination_paths.keys()):
            for path in self._owned_destination_paths[server_id]:
                server.conn.DeleteInstance(path)
            del self._owned_destination_paths[server_id]

        # Remove server from this listener
        del self._servers[server_id]

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

        for server_id in list(self._servers.keys()):
            self.remove_server(server_id)

    # pylint: disable=line-too-long
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
        whether the destination is owned; ``{subscription_manager_id}`` is
        the subscription manager ID; and ``{guid}`` is a globally unique
        identifier.

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
                                        self._subscription_manager_id, owned)

        if owned:
            self._owned_destination_paths[server_id].append(dest_path)

        return [dest_path]

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

            :class:`py:list` of :class:`~pywbem.CIMInstanceName`: The instance
            paths of the listener destination instances.

        Raises:

            Exceptions raised by :class:`~pywbem.WBEMConnection`.
        """

        server = self._get_server(server_id)

        return server.conn.EnumerateInstanceNames(DESTINATION_CLASSNAME,
                                                  namespace=server.interop_ns)

    def remove_destinations(self, server_id, destination_paths):
        """
        Remove listener destinations from a WBEM server, by deleting the
        listener destination instances in the server.

        The listener destinations may be owned or not-owned.

        This method verifies that there are not currently any subscriptions on
        the specified listener destination, in order to handle server
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
            CIMError(CIM_ERR_FAILED) if there are referencing subscriptions.
        """  # noqa: E501

        # if list, recursively call this remove subscriptions for each entry
        if isinstance(destination_paths, list):
            for dest_path in destination_paths:
                self.remove_destinations(server_id, dest_path)
            return

        server = self._get_server(server_id)

        # Here destination_paths will contain only a single path entry.
        # Assign to internal variable for clarity
        dest_path = destination_paths

        # Verify referencing subscriptions.
        ref_paths = server.conn.ReferenceNames(
            dest_path, ResultClass=SUBSCRIPTION_CLASSNAME)
        if len(ref_paths) > 0:
            # DSP1054 1.2 defines that this CIM error is raised by the server
            # in that case, so we simulate that behavior on the client side.
            raise CIMError(CIM_ERR_FAILED,
                           "The listener destination is referenced by "
                           "subscriptions.")

        server.conn.DeleteInstance(dest_path)

        paths = self._owned_destination_paths[server_id]
        for i, path in enumerate(paths):
            if path == dest_path:
                del paths[i]
                # continue look to find any possible duplicate entries

    def add_filter(self, server_id, source_namespace, query,
                   query_language=DEFAULT_QUERY_LANGUAGE,
                   owned=True,
                   filter_id=None):
        # pylint: disable=line-too-long
        """
        Add a :term:`dynamic indication filter` to a WBEM server, by creating
        an indication filter instance (of CIM class "CIM_IndicationFilter") in
        the Interop namespace of the server.

        The form of the `Name` property of the created filter instance is:

          ``"pywbemfilter:" {ownership} ":" {subscription_manager_id} ":"
          {filter_id} ":" {guid}``

        where ``{ownership}`` is ``"owned"`` or ``"permanent"`` dependent on
        whether the filter is owned; ``{subscription_manager_id}`` is the
        subscription manager ID; ``{filter_id}`` is the filter ID; and
        ``{guid}`` is a globally unique identifier.

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
            The user may also delete these filter instances explicitly (for
            example by using
            :meth:`~pywbem.WBEMSubscriptionManager.remove_filter`).

            If `False`, these filter instances are not-owned and will have a
            life cycle that is independent of the registration of the WBEM
            server within this subscription manager. The user is responsible
            for deleting these filter instances explicitly (for example by
            using :meth:`~pywbem.WBEMSubscriptionManager.remove_filter`).

          filter_id (:term:`string`)
            A filter ID string that is used as a component in the value of the
            `Name` property of filter instances to help the user identify
            these instances in a WBEM server.

            Must not be `None`.

            The string must consist of printable characters, and must not
            contain the character ':' because that is the separator between
            components within the value of the `Name` property.

            There is no requirement that the filter ID be unique. This can be
            used to identify groups of filters by using the same value for
            multiple filters.

        Returns:

            :class:`~pywbem.CIMInstanceName`: The instance path of the
            indication filter instance.

        Raises:

            Exceptions raised by :class:`~pywbem.WBEMConnection`.
        """
        server = self._get_server(server_id)

        if filter_id is None:
            raise ValueError("Filter ID must not be None")
        if not isinstance(filter_id, six.string_types):
            raise TypeError("Invalid type for filter ID: %r" % filter_id)
        if ':' in filter_id:
            raise ValueError("Filter ID contains ':': %s" % filter_id)

        # create a single filter for a server.
        filter_path = _create_filter(server, source_namespace, query,
                                     query_language,
                                     self._subscription_manager_id,
                                     filter_id, owned)

        if owned:
            self._owned_filter_paths[server_id].append(filter_path)

        return filter_path

    def get_owned_filters(self, server_id):
        """
        Return the owned indication filters in a WBEM server that have been
        created by this subscription manager.

        This function accesses only the local list of owned filters; it does
        not contact the WBEM server.

        Parameters:

          server_id (:term:`string`):
            The server ID of the WBEM server, returned by
            :meth:`~pywbem.WBEMSubscriptionManager.add_server`.

        Returns:

            :class:`py:list` of :class:`~pywbem.CIMInstanceName`: The instance
            paths of the indication filter instances.

        Raises:

            Exceptions raised by :class:`~pywbem.WBEMConnection`.
        """
        self._get_server(server_id)

        return self._owned_filter_paths[server_id]

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

            :class:`py:list` of :class:`~pywbem.CIMInstanceName`: The instance
            paths of the indication filter instances.

        Raises:

            Exceptions raised by :class:`~pywbem.WBEMConnection`.
        """
        server = self._get_server(server_id)

        return server.conn.EnumerateInstanceNames('CIM_IndicationFilter',
                                                  namespace=server.interop_ns)

    def remove_filter(self, server_id, filter_path):
        """
        Remove an indication filter from a WBEM server, by deleting the
        indication filter instance in the WBEM server.

        The indication filter must be a :term:`dynamic filter` but may be owned
        or not-owned.

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
            CIMError(CIM_ERR_FAILED) if there are referencing subscriptions.
        """
        server = self._get_server(server_id)

        # Verify referencing subscriptions.
        ref_paths = server.conn.ReferenceNames(
            filter_path, ResultClass=SUBSCRIPTION_CLASSNAME)
        if len(ref_paths) > 0:
            # DSP1054 1.2 defines that this CIM error is raised by the server
            # in that case, so we simulate that behavior on the client side.
            raise CIMError(CIM_ERR_FAILED,
                           "The indication filter is referenced by "
                           "subscriptions.")

        server.conn.DeleteInstance(filter_path)

        paths = self._owned_filter_paths[server_id]
        for i, path in enumerate(paths):
            if path == filter_path:
                del paths[i]
                # continue look to find any possible duplicate entries

    def add_subscriptions(self, server_id, filter_path, destination_paths=None,
                          owned=True):
        """
        Add subscriptions to a WBEM server for a particular set of indications
        defined by an indication filter and for a particular set of WBEM
        listeners defined by the instance paths of their listener destination
        instances in that WBEM server, by creating indication subscription
        instances (of CIM class "CIM_IndicationSubscription") in the Interop
        namespace of that server.

        The indication filter can be an (owned or not-owned)
        :term:`dynamic filter` created via
        :meth:`~pywbem.WBEMSubscriptionManager.add_filter`, or a dynamic or
        :term:`static filter` that already exists in the WBEM server.
        Existing filters in the WBEM server can be retrieved via
        :meth:`~pywbem.WBEMSubscriptionManager.get_all_filters`.

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

            When creating not-owned subscriptions, this filter also must be
            not-owned.

          destination_paths (:class:`~pywbem.CIMInstanceName` or list of :class:`~pywbem.CIMInstanceName`):
            If not `None`, subscriptions will be created for the listener
            destinations whose instance paths are specified in this argument.

            If `None`, subscriptions will be created for all owned listener
            destinations registered to this subscription manager.

            When creating not-owned subscriptions, all involved listener
            destinations must be not-owned, too.

          owned (:class:`py:bool`):
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
            WBEM server. The user may also delete these subscription instances
            explicitly (for example by using
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
        """  # noqa: E501
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
            raise ValueError("Not-owned subscription cannot be created on "
                             "owned filter: %s" % filter_path)

        for dest_path in destination_paths:

            # Validate that owned flag and owned status of paths match
            if not owned and \
               dest_path in self._owned_destination_paths[server_id]:
                raise ValueError("Not-owned subscription cannot be created "
                                 "on owned listener destination: %s" %
                                 dest_path)

            sub_path = _create_subscription(server, dest_path, filter_path)
            sub_paths.append(sub_path)
            if owned:
                self._owned_subscription_paths[server_id].append(sub_path)

        return sub_paths

    def get_owned_subscriptions(self, server_id):
        """
        Return the owned indication subscriptions for a WBEM server that have
        been created by this subscription manager.

        This function accesses only the local list of owned subscriptions; it
        does not contact the WBEM server.

        Parameters:

          server_id (:term:`string`):
            The server ID of the WBEM server, returned by
            :meth:`~pywbem.WBEMSubscriptionManager.add_server`.

        Returns:

            :class:`py:list` of :class:`~pywbem.CIMInstanceName`: The instance
            paths of the indication subscription instances.

        Raises:

            Exceptions raised by :class:`~pywbem.WBEMConnection`.
        """

        # validate that this server exists.
        self._get_server(server_id)

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
            The server ID of the WBEM server, returned by
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

    def remove_subscriptions(self, server_id, sub_paths):
        """
        Remove indication subscription(s) from a WBEM server, by deleting the
        indication subscription instances in the server.

        The indication subscriptions may be owned or not-owned.

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

        # if list, recursively call this remove subscriptions for each entry
        if isinstance(sub_paths, list):
            for sub_path in sub_paths:
                self.remove_subscriptions(server_id, sub_path)
            return

        # Here sub_paths will contain only a single path entry
        server = self._get_server(server_id)

        # Assign to internal variable for clarity
        sub_path = sub_paths

        server.conn.DeleteInstance(sub_path)

        sub_path_list = self._owned_subscription_paths[server_id]
        for i, path in enumerate(sub_path_list):
            if path == sub_path:
                del sub_path_list[i]
                # continue to end of list to pick up any duplicates


def _create_destination(server, dest_url, subscription_manager_id, owned):
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
        Must not be `None`.

      owned (:class:`py:bool`):
        Defines whether or not the created instance is *owned* by the
        subscription manager.

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

    this_host = getfqdn()
    ownership = "owned" if owned else "permanent"

    dest_path = CIMInstanceName(DESTINATION_CLASSNAME)
    dest_path.classname = DESTINATION_CLASSNAME
    dest_path.namespace = server.interop_ns

    dest_inst = CIMInstance(DESTINATION_CLASSNAME)
    dest_inst.path = dest_path
    dest_inst['CreationClassName'] = DESTINATION_CLASSNAME
    dest_inst['SystemCreationClassName'] = SYSTEM_CREATION_CLASSNAME
    dest_inst['SystemName'] = this_host
    dest_inst['Name'] = 'pywbemdestination:%s:%s:%s' % \
                        (ownership, subscription_manager_id, uuid.uuid4())
    dest_inst['Destination'] = listener_url
    dest_path = server.conn.CreateInstance(dest_inst)
    return dest_path


def _create_filter(server, source_namespace, query, query_language,
                   subscription_manager_id, filter_id, owned):
    """
    Create a :term:`dynamic indication filter` instance in the Interop
    namespace of a WBEM server and return its instance path.

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

      subscription_manager_id (:term:`string`):
        Subscription manager ID string to be incorporated into the `Name`
        property of the filter instance.
        Must not be `None`.

      filter_id (:term:`string`):
        Filter ID string to be incorporated into the `Name` property of the
        filter instance, as detailed for `subscription_manager_id`.
        Must not be `None`.

      owned (:class:`py:bool`):
        Defines whether or not the created instance is *owned* by the
        subscription manager.

    Returns:

        :class:`~pywbem.CIMInstanceName`: The instance path of the created
        instance.

    Raises:

        Exceptions raised by :class:`~pywbem.WBEMConnection`.
    """

    this_host = getfqdn()
    ownership = "owned" if owned else "permanent"

    filter_path = CIMInstanceName(FILTER_CLASSNAME)
    filter_path.classname = FILTER_CLASSNAME
    filter_path.namespace = server.interop_ns

    filter_inst = CIMInstance(FILTER_CLASSNAME)
    filter_inst.path = filter_path
    filter_inst['CreationClassName'] = FILTER_CLASSNAME
    filter_inst['SystemCreationClassName'] = SYSTEM_CREATION_CLASSNAME
    filter_inst['SystemName'] = this_host
    # TODO: We should not set the `Name` property of filters, because it
    # needs to be user-defined. See issue #540.
    filter_inst['Name'] = 'pywbemfilter:%s:%s:%s:%s' % \
        (ownership, subscription_manager_id, filter_id, uuid.uuid4())
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
