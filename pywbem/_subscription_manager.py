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
The `WBEM API`_ provides functionality for managing subscriptions for
indications from one or more WBEM servers
.. note::

   At this point, the WBEM subscription managerAPI is experimental.

Examples
--------

The following example code combines a subscription manager and listeener to
subscribes for a CIM alert indication on two WBEM servers and register a
callback function for indication delivery:

::

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
        filter1_paths = subscription_manager.get_filters(url1)
        for fp in filter1_paths:
            if fp.keybindings['Name'] == \\
               "DMTF:Indications:GlobalAlertIndicationFilter":
                subscription_manager.add_subscription(url1, fp)
                break

        # Create a dynamic alert indication filter and subscribe for it
        filter2_path = subscription_manager.add_dynamic_filter(
            url2,
            query_language="DMTF:CQL"
            query="SELECT * FROM CIM_AlertIndication " \\
                  "WHERE OwningEntity = 'DMTF' " \\
                  "AND MessageID LIKE 'SVPC0123|SVPC0124|SVPC0125'")

        subscription_manager.add_subscription(server2_id, filter2_path)

Another more practical example is in the script ``examples/listen.py``
(when you clone the GitHub pywbem/pywbem project).
It is an interactive Python shell that creates a WBEM listener and displays
any indications it receives, in MOF format.
"""

import sys
from socket import getfqdn
import uuid
import six

from ._server import WBEMServer
from ._version import __version__
from .cim_obj import CIMInstance, CIMInstanceName

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
        """
        Parameters:

          subscription_manager_id (:term:`string`):
            If not `None` a string of printable characters to be inserted in
            the name property of filter and listener destination instances
            to help the user identify its filters and destination instances
            in a WBEM Server.

            The string must not contain the character ':' since that
            is the separator between components of the name property applied
            to each filter.

            There is no requirement that the subscription manager id be unique.

            The form for the name property of a PyWBEM of a filter is:

        "pywbemfilter:" [<subscription_manager_id>  ":"]
                            [<filter_id> ":"] <guid>

        """

        # The following dictionaries have the WBEM server ID as a key.
        self._servers = {}  # WBEMServer objects for the WBEM servers
        self._owned_subscription_paths = {}  # CIMInstanceName of subscriptions
        self._owned_filter_paths = {}  # CIMInstanceName of dynamic filters
        self._server_dest_tuples = {}  #tuple listener_url and dest_path

        if subscription_manager_id is None:
            self._subscription_manager_id = ''
        elif isinstance(subscription_manager_id, six.string_types):
            if ':' in subscription_manager_id:
                raise ValueError("Invalid String: subscription_manager_id %s" \
                                 " contains ':'" % subscription_manager_id)
            self._subscription_manager_id = subscription_manager_id
        else:
            raise TypeError("invalid type for subscription_manager_id=%s" % \
                            subscription_manager_id)

    def __repr__(self):
        """
        Return a representation of the :class:`~pywbem.WBEMSubscriptionManager`
        object with all attributes, that is suitable for debugging.
        """
        return "%s(subscription_manager_id=%s, _servers=%r, " \
               "_owned_subscription_paths=%r, _owned_filter_paths=%r, " \
               "_destination_paths=%r)" % \
               (self.__class__.__name__,
                self.self.subscription_manager_id,
                self._servers, self._owned_subscription_paths,
                self._owned_filter_paths, self._server_dest_tuples,
                subscription_manager_id)

    def _get_server(self, server_id):
        """
            Internal method to get the server object given a server_id.

        Parameters:

          server_id (:term:`string`):
            The server ID for the WBEM server, returned by :meth:`add_server`.

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


    def add_listener_destinations(self, server_id, listener_urls, owned=True):
        """
        Add the URL of a WBEM listener to  the set of listeners for which
        indications will be targeted for the defined WBEM Server.

        This function creates a destination instance for each specified listener
        in listener_urls and registers that instance with the WBEM server
        defined by server_id.

        Parameters:

          server_id (:term:`string`):
            The server ID for the WBEM server, returned by :meth:`add_server`.

          listener_urls ((list of :term:`string`) or (:term:`string`)):
            Either a  single listener URL or list of listener
            urls. This represents the listeners for which indications will
            be routed and for which destinations instances are registered
            with the WBEM server.

            Each listener URL is defined in the format:

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

        See `WBEMConnection` for examples of valid urls.
        """
        
        # if list, recursively call this function with each entry
        if isinstance(listener_urls, list):
            for listener_url in listener_urls:
                self.add_listener_destinations(server_id, listener_url)
            return

        # process a single URL 
        listener_url = listener_urls    # documents that this is single URL
        server = self._get_server(server_id)

        dest_path = _create_destination(server, listener_url,
                                        self._subscription_manager_id)

        # Put listener URL and dest path into a tuple and save in a dictionary
        if owned:
            dest_tuple = (listener_url, dest_path)
            self._server_dest_tuples[server_id].append(dest_tuple)

    def add_server(self, server):
        """
        Add a WBEM server to the subscription manager. The WBEM server
        is the target for filters and subscriptions and generates
        indications.

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
        self._server_dest_tuples[server_id] = []

        return server_id

    def remove_server(self, server_id):
        """
        Remove a WBEM server from the subscription manager and unregister the
        listeners from the server by deleting all indication subscriptions,
        owned indication filters and ownedlistener destinations in the server
        that were created by this subscription manager.

        Parameters:

          server_id (:term:`string`):
            The server ID for the WBEM server, returned by :meth:`add_server`.

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

        if server_id in self._server_dest_tuples:
            for dest_tuple in self._server_dest_tuples[server_id]:
                path = dest_tuple[1]
                server.conn.DeleteInstance(path)

            del self._server_dest_tuples[server_id]

        # Remove server from this listener
        del self._servers[server_id]


    def add_filter(self, server_id, source_namespace, query,
                   query_language=DEFAULT_QUERY_LANGUAGE,
                   owned=True,
                   filter_id=None):
        """
        Add a dynamic indication filter to a WBEM server, by creating an
        indication filter instance in the Interop namespace of the server.

        Dynamic indication filters are those that are created by clients.
        Indication filters that pre-exist in the WBEM server are termed
        *static indication filters* and cannot be removed by clients.
        See :term:`DSP1054` for details about indication filters.

        Parameters:

          server_id (:term:`string`):
            The server ID for the WBEM server, returned by :meth:`add_server`.

          source_namespace (:term:`string`):
            Source namespace of the indication filter.

          query (:term:`string`):
            Filter query in the specified query language.


          query_language (:term:`string`):
            Query language for the specified filter query.

            Examples: 'WQL', 'DMTF:CQL'.

          owned (:class:`py:bool`)
            Defines whether a filter whose lifecycle is owned by this server
            or not is to be created. If True, a filter is 
            created that is defined by the life cycle of this server instance
            within this subscription manager.  If False a  filter is created
            that it may outlive the lifecycle of the server instance
            and must be removed manually by the user (for example using
            the `remove_filter` function.

          filter_id (:term:`string`)
            If not `None` a printable string that is incorporated into the name
            property of the filter instance to help the listener identify
            its filters and handler instances in a WBEM Server. The character
            ":" is not allowed in this string since it is the separator between
            components of the final filter_id.  Filter ids need not be
            unique and can be used to identify groups of filters by applying
            the same `filter_id` to them.

            The form of the filter name property is:

              "pywbemfilter:" [ <subscription_manager_id> ":"]
                  [ <filter_id> ":" ] <guid>

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
        Remove an indication filter from a WBEM server, by deleting an
        indication filter instance in the WBEM server.

        Parameters:

          server_id (:term:`string`):
            The server ID for the WBEM server, returned by :meth:`add_server`.

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
        Return the owned indication filter instance paths in a WBEM server
        that have been created by this subscription manager for server_id.
        This function access only the local list of owned filters.
        It does NOT contact the WBEM server.

        Parameters:

          server_id (:term:`string`):
            The server ID for the WBEM server, returned by :meth:`add_server`.

        Returns:

            List of :class:`~pywbem.CIMInstanceName`: The owned indication
            filter instance paths.

        Raises:

            Exceptions raised by :class:`~pywbem.WBEMConnection`.
        """
        _ = self._get_server(server_id)

        return self._owned_filter_paths[server_id]

    def get_filters(self, server_id):
        """
        Return the instance paths of all filter instance paths inthe
        defined WBEM server. This function requests filters from the
        WBEM server defined by server_id

        Parameters:

          server_id (:term:`string`):
            The server ID for the WBEM server, returned by :meth:`add_server`.

        Returns:

          List of :class:`~pywbem.CIMInstanceName`: The indication filter
          instance paths.

        Raises:

            Exceptions raised by :class:`~pywbem.WBEMConnection`.
        """
        server = self._get_server(server_id)

        return server.conn.EnumerateInstanceNames('CIM_IndicationFilter',
                                                  namespace=server.interop_ns)

    def add_subscriptions(self, server_id, filter_path,
                          listener_urls=None, owned=True):
        """
        Add subscriptions to a WBEM server for particular set of indications
        defined by an indication filter and listener as defined by a
        destination instance, by creating an indication subscription
        instance in the Interop namespace of the server that links the
        specified indication filter with the listener destination in the
        server that references this listener.

        The indication filter can be a filter created specifically for
        this listener via :meth:`add_filter`, or a filter that
        pre-exists in the WBEM server. Filters defined in the WBEM server can
        be retrieved via :meth:`get_filters`.

        This may create multiple subscription instances if there are multiple
        listeners related to a server through :meth:`add.server`.

        Upon successful return of this method, the subscriptions are active.

        Parameters:

          server_id (:term:`string`):
            The server ID for the WBEM server, returned by :meth:`add_server`.

          filter_path (:class:`~pywbem.CIMInstanceName`):
            Instance path of the indication filter instance in the WBEM
            server that specifies the indications to be sent.

          listener_urls (list of :term:`string` or single :term:`string`):
              Create subscriptions only for the lintener_urls defined in
              this list or single entry.

              If `None`, create subscriptions for all listeners defined by
              :meth: add_listener_destinations for this server_id

          owned (:class:`py:bool`)
            If True, this owned subscriptions life
            cycle is controlled by the lifecycle of the server to which it
            is attached. If False, the filter is created and registered with
            the server but not recorded in the local subscription manager
            for removal.

        Returns:

            (list of :class:`~pywbem.CIMInstanceName`): Instance paths of
            the subscription instances created in the WBEM server.

        Raises:

            Exceptions raised by :class:`~pywbem.WBEMConnection`.
        """

        server = self._get_server(server_id)

        # force the listener_urls into a list
        listener_urls = listener_urls if isinstance(listener_urls, list) \
            else [listener_urls]

        # Create a subscription for every entry in the dest_tuples list
        # unless filtered by listener_urls
        # This subscribes the filter for each listener as defined by its
        # destination path
        dest_tuples = self._server_dest_tuples[server_id]
        sub_paths = []
        for dest_tuple in dest_tuples:
            listener_url = dest_tuple[0]
            dest_path = dest_tuple[1]
            if listener_urls is None or listener_url in listener_urls:
                _create_destination(server, listener_url,
                                    self._subscription_manager_id)
                sub_path = _create_subscription(server, dest_path, filter_path)
                sub_paths.append(sub_path)
                if owned:
                    self._owned_subscription_paths[server_id].append(sub_path)
                    
        return sub_paths

    def remove_subscriptions(self, server_id, sub_paths):
        """
        Remove an indication subscription or list of subscriptions from a
        WBEM server, by deleting the indication subscription instances in the
        server.

        Parameters:

          server_id (:term:`string`):
            The server ID for the WBEM server, returned by :meth:`add_server`.

          sub_paths (list of :class:`~pywbem.CIMInstanceName`) or
              (:class:`~pywbem.CIMInstanceName`):
            List of instance paths or instance path of the indication
            subscription instance in the WBEM server.

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
                    

    def get_owned_subscriptions(self, server_id):
        """
        Return the indication subscriptions in a WBEM server that have been
        created by this listener. Retrievies all subscriptions registered
        with the WBEM server and in the interop namespace.

        Parameters:

          server_id (:term:`string`):
            The server ID for the WBEM server, returned by :meth:`add_server`.

        Returns:

            List of :class:`~pywbem.CIMInstanceName`: The indication
            subscription instance paths.

        Raises:

            Exceptions raised by :class:`~pywbem.WBEMConnection`.
        """

        # validate that this server exists.
        _ = self._get_server(server_id)

        return self._owned_subscription_paths[server_id]

    def get_all_listener_destination_instances(self, server_id):
        """
        Return all 'CIM_ListenerDestinationCIMXML' instance paths in a
        WBEM server.

        Parameters:

          server_id (:term:`string`):
            The server ID for the WBEM server, returned by :meth:`add_server`.

        Returns:

          List of :class:`~pywbem.CIMInstanceName`: The
          CIM_ListenerDestinationCIMXML instance paths.

        Raises:

            Exceptions raised by :class:`~pywbem.WBEMConnection`.
        """

        server = self._get_server(server_id)

        return server.conn.EnumerateInstanceNames(DESTINATION_CLASSNAME,
                                                  namespace=server.interop_ns)

    def get_all_subscriptions(self, server_id):
        """
        Return all CIM_IndicationSubscription instance paths in a WBEM server.

        Parameters:

          server_id (:term:`string`):
            The server ID for the WBEM server, returned by :meth:`add_server`.

        Returns:

          List of :class:`~pywbem.CIMInstanceName`: The subscription
          instance paths.

        Raises:

            Exceptions raised by :class:`~pywbem.WBEMConnection`.
        """
        server = self._get_server(server_id)

        return server.conn.EnumerateInstanceNames(SUBSCRIPTION_CLASSNAME,
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
        String to be incorporated into the name property of the destination
        instance.

        The form for the name property of a PyWBEM of a destination instance is:

        "pywbemdestination:" [<subscription_manager_id>  ":"]
            [<fsubscription_manager_id> ":"] <guid>

    Returns:

        :class:`~pywbem.CIMInstanceName`: The instance path of the created
        instance.

    Raises:

        Exceptions raised by :class:`~pywbem.WBEMConnection`.
    """

    dest_path = CIMInstanceName(DESTINATION_CLASSNAME)
    dest_path.classname = DESTINATION_CLASSNAME
    dest_path.namespace = server.interop_ns

    dest_inst = CIMInstance(DESTINATION_CLASSNAME)
    dest_inst.path = dest_path
    dest_inst['CreationClassName'] = DESTINATION_CLASSNAME
    dest_inst['SystemCreationClassName'] = SYSTEM_CREATION_CLASSNAME
    dest_inst['SystemName'] = getfqdn()
    dest_inst['Name'] = 'pywbemdestination:%s:%s' % (subscription_manager_id,
                                                   uuid.uuid4())
    dest_inst['Destination'] = dest_url
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
        String prefex that will be prepended to the created filter. Can
        be used to help identify filters in the server. If `None` no prefix
        is added to the system-defined name for this filter

      subscription_manager_id (:term:`string`))
        If not `None` a string of printable characters to be inserted in the
        name property of filter and listener destination instances to help the
        listener identify its filters and destination instances in a
        WBEM Server. The string must not contain the ":" character.

        The form for the name property of a PyWBEM of a filter is:

        "pywbemfilter:" [<subscription_manager_id>  ":"]
            [<filter_id> ":"] <guid>

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
            raise ValueError("Invalid String: filter_id %s contains ':'" % \
                             filter_id)
        filter_id_ = '%s:' % filter_id
    else:
        raise TypeError("invalid type for filter_id=%s" % filter_id)

    filter_inst.path = filter_path
    filter_inst['CreationClassName'] = FILTER_CLASSNAME
    filter_inst['SystemCreationClassName'] = SYSTEM_CREATION_CLASSNAME
    filter_inst['SystemName'] = getfqdn()
    filter_inst['Name'] = 'pywbemfilter:%s:%s:%s' % (subscription_manager_id, \
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

