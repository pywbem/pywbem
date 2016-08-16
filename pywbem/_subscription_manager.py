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
    import logging
    from socket import getfqdn
    from pywbem import WBEMConnection, WBEMListener, WBEMServer,
                       WBEMSubscriptionManager

    def process_indication(indication, host):
        '''This function gets called when an indication is received.'''
        print("Received CIM indication from {host}: {ind!r}". \\
            format(host=host, ind=indication))

    def main():

        logging.basicConfig(stream=sys.stderr, level=logging.WARNING,
            format='%(asctime)s - %(levelname)s - %(message)s)

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

        subscription_manager = WBEMSubscriptionManager(listener=my_listener)
        subscription_manager.add_listener('http', getfqdn(), 5988)
        subscription_manager.add_server(server1)
        subscription_manager.add_server(server2)


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
        subscription_manager.add_subscription(url2, filter2_path)

Another more practical example is in the script ``examples/listen.py``
(when you clone the GitHub pywbem/pywbem project).
It is an interactive Python shell that creates a WBEM listener and displays
any indications it receives, in MOF format.
"""

####import re
from socket import getfqdn
import logging
import uuid
import six

from ._server import WBEMServer
from ._version import __version__
from .cim_obj import CIMInstance, CIMInstanceName


#CIM model classnames for subscription components
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
            to help the subscription manager identify its filters and
            destination instances in a WBEM Server.

            The string must not contain the character ':' since that
            is the separator between components of the name property applied
            to each filter.

            The form for the name property of a PyWBEM of a filter is:

        "pywbemfilter:" [<subscription_manager_id>  ":"]
                            [<filter_id> ":"] <guid>

        """

        self._logger = logging.getLogger('pywbem.SubscriptionManager.%s' %
                                         id(self))
        self._logger.addHandler(logging.NullHandler())

        self._listener_urls = []     # list of listeners for this server

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
            self._subscription_manager_id = '%s:' % subscription_manager_id
        else:
            raise TypeError("invalid type for subscription_manager_id=%s" % \
                            subscription_manager_id)

    def __repr__(self):
        """
        Return a representation of the :class:`~pywbem.WBEMSubscriptionManager`
        object with all attributes, that is suitable for debugging.
        """
        return "%s(host=%r, _servers=%r, " \
               "_owned_subscription_paths=%r, _owned_filter_paths=%r, " \
               "_ listener_urls=%s, _destination_paths=%r)" % \
               (self.__class__.__name__,
                self.logger,
                self._servers, self._owned_subscription_paths,
                self._owned_filter_paths, self._listener_urls,
                self._server_dest_tuples)

    @property
    def logger(self):
        """
        The logger object for this listener.

        Each listener object has its own separate logger object that is
        created via :func:`py:logging.getLogger`.

        The name of this logger object is: `pywbem.listener.{id}` where `{id}`
        is the :func:`id` value of the listener object. Users of the listener
        should not look up the logger object by name, but should use this
        property to get to it.

        By default, this logger uses the :class:`~py:logging.NullHandler` log
        handler, and its log level is :attr:`~py:logging.NOTSET`. This causes
        this logger not to emit any log messages and to propagate them to the
        Python root logger.

        The behavior of this logger can be changed by invoking its methods
        (see :class:`py:logging.Logger`). The behavior of the root logger can
        for example be configured using :func:`py:logging.basicConfig`:

        ::

            import sys
            import logging

            logging.basicConfig(stream=sys.stderr, level=logging.WARNING,
                format='%(asctime)s - %(levelname)s - %(message)s')
        """
        return self._logger

    def add_listener_url(self, scheme, hostname, port):
        """
        Add the url of a WBEM listener to  the set of listeners for which
        indications will be targeted. This url must include scheme, address,
        and port components.
        FUTURE TODO: we could leave off port and use defaults. based on scheme

        Parameters:
          host (:term:`string`):
            IP address or host name this listener can be reached at.

          port (:term:`string` or :term:`integer`):
            port the listener can be reached at.

        """

        if scheme != "http" and scheme != 'https':
            raise ValueError('Invalid Listener scheme %s' %  scheme)

        if isinstance(port, six.integer_types):
            _port = int(port)  # Convert Python 2 long to int
        elif isinstance(port, six.string_types):
            _port = int(port)
        else:
            raise TypeError("Invalid type for port: %s" % type(port))

        # listeners must be set before servers defined
        if len(self._servers) != 0:
            raise ValueError('Listeners must be defined before servers')

        listener_url = '%s.//%s:%s' %(scheme, hostname, _port)

        self._listener_urls.append(listener_url)

    def add_server(self, server, listener_urls=None):
        """
        Add a WBEM server to the subscription manager and register the
        listeners defined by listener_urls with the server by creating an
        indication listener instance referencing each         listener in the
        Interop namespace of the server.

        Parameters:

          server (:class:`~pywbem.WBEMServer`):
            The WBEM server.

          listener_urls TODO may be single listener url or list of listener
            urls. This represents the subset of the listener urls defined
            with the add_listener function for which indications from this
            web server are to be handled.

            If `None` the full set of listeners defined with the add_listener
            method is used.

        Returns:

            :term:`string`: An ID for the WBEM server, for use by other
            methods of this class.

        Raises:

            Exceptions raised by :class:`~pywbem.WBEMConnection`.
        """

        if not isinstance(server, WBEMServer):
            raise TypeError("server argument of add_server() must be a " \
                            "WBEMServer object")
        server_id = server.url
        if server_id in self._servers:
            raise ValueError("WBEM server already known by listener: %s" % \
                             server_id)

        #Create a new dictionary for this server
        self._servers[server_id] = server
        self._owned_subscription_paths[server_id] = []
        self._owned_filter_paths[server_id] = []
        self._server_dest_tuples[server_id] = []
        _listener_urls = listener_urls
        if listener_urls is None:
            _listener_urls = self._listener_urls

        if isinstance(_listener_urls, list):
            for url in _listener_urls:
                dest_path = _create_destination(server, url,
                                                self._subscription_manager_id)

                #put the listener url and dest path into a tuple
                self._server_dest_tuples[server_id].append((url, dest_path))

        else:
            dest_path = _create_destination(server, _listener_urls,
                                            self._subscription_manager_id)

            #put the listener url and dest path into a tuple
            self._server_dest_tuples[server_id].append((_listener_urls,
                                                        dest_path))

        return server_id

    def remove_server(self, server_id):
        """
        Remove a WBEM server from the listener and unregister the listener
        from the server by deleting all indication subscriptions, dynamic
        indication filters and listener destinations in the server that were
        created by this listener.

        Parameters:

          server_id (:term:`string`):
            The server ID for the WBEM server, returned by :meth:`add_server`.

        Raises:

            Exceptions raised by :class:`~pywbem.WBEMConnection`.
        """

        if server_id not in self._servers:
            raise ValueError("WBEM server not known by listener: %s" % \
                             server_id)
        server = self._servers[server_id]

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

        # TODO change this one
        if server_id in self._server_dest_tuples:
            for tup in self._server_dest_tuples[server_id]:
                path = tup[1]
                server.conn.DeleteInstance(path)

            del self._server_dest_tuples[server_id]

        # Remove server from this listener
        del self._servers[server_id]


    def add_filter(self, server_id, source_namespace, query,
                   query_language=DEFAULT_QUERY_LANGUAGE,
                   owned=True,
                   filter_id=None):
        """
        Add an indication filter to a WBEM server, by creating an
        indication filter instance in the Interop namespace of the server.

        Dynamic indication filters are those that are created by clients.
        Indication filters that pre-exist in the WBEM server or are created
        without the dynamic flag are termed *static indication filters* and
        must be removed manually (or possibly cannot be removed by clients)
        See :term:`DSP1054` for details about indication filters.

        Parameters:

          server_id (:term:`string`):
            The server ID for the WBEM server, returned by :meth:`add_server`.

          source_namespace (:term:`string`):
            Source namespace of the indication filter.

          query (:term:`string`):
            Filter query in the specified query language.

          owned (:class: `pybool`) Defines whether a filter whose lifecycle
            is owned by this server or not is to be created.
            If True, a filter is
            created that is defined by the life cycle of this server instance
            within this subscription manager.  If False a  filter is created
            that it may outlive the lifecycle of the server instance
            and must be removed manually by the user (for example using
            the `remove_filter` function.

          query_language (:term:`string`):
            Query language for the specified filter query.

            Examples: 'WQL', 'DMTF:CQL'.

        filter_id(:term: `string`)
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
        if server_id not in self._servers:
            raise ValueError("WBEM server not known by listener: %s" % \
                             server_id)
        server = self._servers[server_id]
        # create a single filter for a server.
        filter_path = _create_filter(server, source_namespace, query,
                                     query_language,
                                     self._subscription_manager_id,
                                     filter_id)
        if owned:
            self._owned_filter_paths[server_id].append(filter_path)
        return filter_path

    # TODO do we need to do this via a listener list???
    def remove_filter(self, server_id, filter_path):
        """
        Remove an indication filter from a WBEM server, by deleting an
        indication filter instance in the WBEM server.

        If the filter is owned by this subscription manager, it is deleted
        from the local list and the WBEM Server. Otherwise it is just deleted
        from the server defined by server_id

        Parameters:

          server_id (:term:`string`):
            The server ID for the WBEM server, returned by :meth:`add_server`.

          filter_path (:class:`~pywbem.CIMInstanceName`):
            Instance path of the indication filter instance in the WBEM
            server.

        Raises:

            Exceptions raised by :class:`~pywbem.WBEMConnection`.
        """
        if server_id not in self._servers:
            raise ValueError("WBEM server not known by listener: %s" % \
                             server_id)
        server = self._servers[server_id]
        if server_id in self._owned_filter_paths:
            paths = self._owned_filter_paths[server_id]
            for i, path in enumerate(paths):
                if path == filter_path:
                    server.conn.DeleteInstance(path)
                    del paths[i]
                    break
        else:
            server.conn.DeleteInstance(path)


    def get_owned_filters(self, server_id):
        """
        Return the owned indication filter instance paths in a WBEM server
        that have been created by this listener. This function access only
        the local list of dynamic filters. It does NOT contact the WBEM
        server.

        Parameters:

          server_id (:term:`string`):
            The server ID for the WBEM server, returned by :meth:`add_server`.

        Returns:

            List of :class:`~pywbem.CIMInstanceName`: The owned indication
            filter instance paths.

        Raises:

            Exceptions raised by :class:`~pywbem.WBEMConnection`.
        """
        if server_id not in self._servers:
            raise ValueError("WBEM server not known by listener: %s" % \
                             server_id)
        return self._owned_filter_paths[server_id]

    def get_filters(self, server_id):
        """
        Return all owned and remote indication filter instance paths for the
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
        if server_id not in self._servers:
            raise ValueError("WBEM server not known by listener: %s" % \
                             server_id)
        server = self._servers[server_id]
        return server.conn.EnumerateInstanceNames('CIM_IndicationFilter',
                                                  namespace=server.interop_ns)

    def add_subscription(self, server_id, filter_path, owned=True):
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
        listeners related to a server through the :meth:`add.server` method.

        Upon successful return of this method, the subscriptions are active.

        Parameters:

          server_id (:term:`string`):
            The server ID for the WBEM server, returned by :meth:`add_server`.

          filter_path (:class:`~pywbem.CIMInstanceName`):
            Instance path of the indication filter instance in the WBEM
            server that specifies the indications to be sent.

          owned (:class:`py:bool`) If True, this owned subscriptions life
            cycle is controled by the lifecycle of the server to which it
            is attached. If False, the filter is created and registered with
            the server but not recorded in the local subscription manager
            for removal.

        Returns:

            (list of :class:`~pywbem.CIMInstanceName`): Instance paths of
            the subscription instances created in the WBEM server.

        Raises:

            Exceptions raised by :class:`~pywbem.WBEMConnection`.
        """
        if server_id not in self._servers:
            raise ValueError("WBEM server not known by listener: %s" % \
                             server_id)
        server = self._servers[server_id]

        # Create a subscription for every entry in the dest_tuples list.
        # This subscribes the filter for each listener as defined by its
        # destination path
        dest_tuples = self._server_dest_tuples[server_id]
        sub_paths = []
        for dest_tuple in dest_tuples:
            listener_url = dest_tuple[0]
            dest_path = dest_tuple[1]
            _create_destination(server, listener_url,
                                self._subscription_manager_id)
            sub_path = _create_subscription(server, dest_path, filter_path)
            sub_paths.append(sub_path)
            if owned:
                self._owned_subscription_paths[server_id].append(sub_path)
        return sub_paths

    def remove_subscription(self, server_id, sub_paths):
        """
        Remove an indication subscription or list of subscriptions from a
        WBEM server, by deleting an indication subscription instance in the
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
        if isinstance(sub_paths, list):
            for sub_path in sub_paths:
                self.remove_subscription(server_id, sub_path)

        else:
            if server_id not in self._servers:
                raise ValueError("WBEM server not known by listener: %s" % \
                                 server_id)
            server = self._servers[server_id]
            if server_id in self._owned_subscription_paths:
                sub_path_list = self._owned_subscription_paths[server_id]
                for i, path in enumerate(sub_path_list):
                    if path == sub_paths:
                        server.conn.DeleteInstance(path)
                        del sub_path_list[i]
                        break
            else:
                server.conn.DeleteInstance(path)


    def get_subscriptions(self, server_id):
        """
        Return the indication subscriptions in a WBEM server that have been
        created by this listener.

        Parameters:

          server_id (:term:`string`):
            The server ID for the WBEM server, returned by :meth:`add_server`.

        Returns:

            List of :class:`~pywbem.CIMInstanceName`: The indication
            subscription instance paths.

        Raises:

            Exceptions raised by :class:`~pywbem.WBEMConnection`.
        """
        if server_id not in self._servers:
            raise ValueError("WBEM server not known by listener: %s" % \
                             server_id)
        return self._owned_subscription_paths[server_id]

    def get_all_destination_instances(self, server_id):
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

        if server_id not in self._servers:
            raise ValueError("WBEM server not known by listener: %s" % \
                             server_id)
        server = self._servers[server_id]
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

        if server_id not in self._servers:
            raise ValueError("WBEM server not known by listener: %s" % \
                             server_id)
        server = self._servers[server_id]
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
    dest_inst['Name'] = 'pywbemlistener:%s%s' % (subscription_manager_id,
                                                 uuid.uuid4())
    dest_inst['Destination'] = dest_url
    print('create dest_inst %s' % dest_inst)
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

      subscription_manager_id (:term: `string`))
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
    filter_inst['Name'] = 'pywbemfilter:%s%s%s' % (subscription_manager_id, \
                                                   filter_id_, \
                                                   uuid.uuid4())
    filter_inst['SourceNamespace'] = source_namespace
    filter_inst['Query'] = query
    filter_inst['QueryLanguage'] = query_language

    print('Create filter instance=%s' % filter_inst)
    filter_path = server.conn.CreateInstance(filter_inst)
    print('Created filter')
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

