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
from ._listener import WBEMListener

# TODO: ks 8/16 Confirm that these are really the default listener ports
#               and we need to define here
DEFAULT_LISTENER_PORT_HTTP = 5988
DEFAULT_LISTENER_PORT_HTTPS = 5989
DEFAULT_QUERY_LANGUAGE = 'WQL'

# CIM-XML protocol related versions implemented by the WBEM listener.
# These are returned in export message responses.
IMPLEMENTED_CIM_VERSION = '2.0'
IMPLEMENTED_DTD_VERSION = '2.4'
IMPLEMENTED_PROTOCOL_VERSION = '1.4'

#CIM model classnames for subscription components
SUBSCRIPTION_CLASSNAME = 'CIM_IndicationSubscription'
DESTINATION_CLASSNAME = 'CIM_ListenerDestinationCIMXML'
FILTER_CLASSNAME = 'CIM_IndicationFilter'
SYSTEM_CREATION_CLASSNAME = 'CIM_ComputerSystem'


#pylint: disable=too-many-instance-attributes
class WBEMSubscriptionManager(object):
    """
    A Client to manage subscriptions to indications and optionally control
    the existence of a listener.

    """

    def __init__(self, listener=None, listener_id=None):
        """
        Parameters:

        listener (:class: `WBEMListener`) The listener to which indications
           are to be sent

        TODO: Should listener_id be here on in listener???

        """

        self._logger = logging.getLogger('pywbem.listener.%s' % id(self))
        self._logger.addHandler(logging.NullHandler())

        # The following dictionaries have the WBEM server ID as a key.
        self._servers = {}  # WBEMServer objects for the WBEM servers
        self._subscription_paths = {}  # CIMInstanceName of subscriptions
        self._dynamic_filter_paths = {}  # CIMInstanceName of dynamic filters
        self._destination_path = {}  # CIMInstanceName of listener destination
        self._listener = listener
        if listener_id is None:
            self._listener_id = ''
        elif isinstance(listener, six.string_types):
            if ':' in listener_id:
                raise ValueError("Invalid String: listener_id %s contains "\
                                 "':'" % listener_id)
            self._listener_id = '%s:' % listener_id
        else:
            raise TypeError("invalid type for flistener_id=%s" % listener_id)

    def __repr__(self):
        """
        Return a representation of the :class:`~pywbem.WBEMSubscriptionManager`
        object with all attributes, that is suitable for debugging.
        """
        return "%s(host=%r, _servers=%r, " \
               "_subscription_paths=%r, _dynamic_filter_paths=%r, " \
               "_destination_path=%r)" % \
               (self.__class__.__name__,
                self.logger,
                self._servers, self._subscription_paths,
                self._dynamic_filter_paths, self._destination_path)

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


    def add_server(self, server):
        """
        Add a WBEM server to the listener and register the listener with the
        server by creating an indication listener instance referencing this
        listener in the Interop namespace of the server.

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
            raise TypeError("server argument of add_server() must be a " \
                            "WBEMServer object")
        server_id = server.url
        if server_id in self._servers:
            raise ValueError("WBEM server already known by listener: %s" % \
                             server_id)

       # We let the WBEM server use HTTP or HTTPS dependent on whether we
        # contact it using HTTP or HTTPS.
        # TODO 8/16 Need more general way to set listener_url than matching
        # server scheme.
        if server.conn.url.lower().startswith('http'):
            scheme = 'http'
            port = self._listener.http_port
        elif server.conn.url.lower().startswith('https'):
            scheme = 'https'
            port = self._listener.https_port
        else:
            raise ValueError("Invalid scheme in server URL: %s" % \
                             server.conn.url)

        listener_url = '%s://%s:%s' % (scheme, self._listener.host, port)
        dest_path = _create_destination(server, listener_url,
                                        self._listener_id)

        #Create a new dictionary for this server
        self._servers[server_id] = server
        self._subscription_paths[server_id] = []
        self._dynamic_filter_paths[server_id] = []
        self._destination_path[server_id] = dest_path

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

        if server_id in self._subscription_paths:
            paths = self._subscription_paths[server_id]
            for i, path in enumerate(paths):
                server.conn.DeleteInstance(path)
            del self._subscription_paths[server_id]

        if server_id in self._dynamic_filter_paths:
            paths = self._dynamic_filter_paths[server_id]
            for i, path in enumerate(paths):
                server.conn.DeleteInstance(path)
            del self._dynamic_filter_paths[server_id]

        if server_id in self._destination_path:
            path = self._destination_path[server_id]
            server.conn.DeleteInstance(path)
            del self._destination_path[server_id]

        # Remove server from this listener
        del self._servers[server_id]


    def add_filter(self, server_id, source_namespace, query,
                   query_language=DEFAULT_QUERY_LANGUAGE,
                   dynamic_filter=True,
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

          dynamic_filter (:class: `pybool`) Defines whether a dynamic or
            static filter is to be created.  If True, a dynamic filter is
            created that is defined by the life cycle of this subscription
            manager instance.  If False a static filter is created in the
            sense that it outlives the lifecycle of the subscription manager
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

              "pywbemfilter:" [ <listener_id> ":"] [ <filter_id> ":" ] <guid>

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
        filter_path = _create_filter(server, source_namespace, query,
                                     query_language, self._listener_id,
                                     filter_id)
        if dynamic_filter:
            self._dynamic_filter_paths[server_id].append(filter_path)
        return filter_path

    def remove_dynamic_filter(self, server_id, filter_path):
        """
        Remove a dynamic indication filter from a WBEM server, by deleting an
        indication filter instance in the WBEM server.

        The indication filter must be a dynamic indication filter that has been
        created by this listener, and there must not exist any subscriptions
        referencing the filter.

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
        if server_id in self._dynamic_filter_paths:
            paths = self._dynamic_filter_paths[server_id]
            for i, path in enumerate(paths):
                if path == filter_path:
                    server.conn.DeleteInstance(path)
                    del paths[i]
                    break

    def remove_static_filter(self, server_id, filter_path):
        """
        Remove a static indication filter from a WBEM server, by deleting an
        indication filter instance in the WBEM server.

        The indication filter shuld be a static indication filter. It need not
        have been created by this subscription manager.

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
        server.conn.DeleteInstance(filter_path)

    def get_dynamic_filters(self, server_id):
        """
        Return the dynamic indication filter instance paths in a WBEM server
        that have been created by this listener. This function access only
        the local list of dynamic filters. It does NOT contact the WBEM
        server.

        Parameters:

          server_id (:term:`string`):
            The server ID for the WBEM server, returned by :meth:`add_server`.

        Returns:

            List of :class:`~pywbem.CIMInstanceName`: The dynamic indication
            filter instance paths.

        Raises:

            Exceptions raised by :class:`~pywbem.WBEMConnection`.
        """
        if server_id not in self._servers:
            raise ValueError("WBEM server not known by listener: %s" % \
                             server_id)
        return self._dynamic_filter_paths[server_id]

    def get_filters(self, server_id):
        """
        Return all (dynamic and static) indication filter instance paths in
        a WBEM server. This function requests filters from the WBEM server

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

    def add_subscription(self, server_id, filter_path,
                         dynamic_subscription=True):
        """
        Add a subscription to a WBEM server for particular set of indications
        defined by an indication filter, by creating an indication subscription
        instance in the Interop namespace of the server, that links the
        specified indication filter with the listener destination in the
        server that references this listener.

        The indication filter can be a dynamic filter created specifically for
        this listener via :meth:`add_dynamic_filter`, or a static filter that
        pre-exists in the WBEM server. Filters defined in the WBEM server can
        be retrieved via :meth:`get_filters`.

        Upon successful return of this method, the subscription is active.

        Parameters:

          server_id (:term:`string`):
            The server ID for the WBEM server, returned by :meth:`add_server`.

          filter_path (:class:`~pywbem.CIMInstanceName`):
            Instance path of the indication filter instance in the WBEM
            server that specifies the indications to be sent.

          dynamic_subscription (:class:`py:bool`) TODO

        Returns:

            :class:`~pywbem.CIMInstanceName`: Instance path of the indication
            subscription instance.

        Raises:

            Exceptions raised by :class:`~pywbem.WBEMConnection`.
        """
        if server_id not in self._servers:
            raise ValueError("WBEM server not known by listener: %s" % \
                             server_id)
        server = self._servers[server_id]

        # We let the WBEM server use HTTP or HTTPS dependent on whether we
        # contact it using HTTP or HTTPS.
        #TODO this not correct. We need more general way to set scheme, etc
        # for listener.
        if server.conn.url.lower().startswith('http'):
            scheme = 'http'
            port = self._listener.http_port
        elif server.conn.url.lower().startswith('https'):
            scheme = 'https'
            port = self._listener.https_port
        else:
            raise ValueError("Invalid scheme in server URL: %s" % \
                             server.conn.url)

        listener_url = '%s://%s:%s' % (scheme, self._listener.host, port)

        dest_path = self._destination_path[server_id] \
                        if dynamic_subscription else \
                            _create_destination(server, listener_url,
                                                self._listener_id)
        sub_path = _create_subscription(server, dest_path, filter_path)
        if dynamic_subscription:
            self._subscription_paths[server_id].append(sub_path)
        return sub_path

    def remove_static_subscription(self, server_id, sub_path, remove_all=True):
        """
        Remove a static subscription from a WBEMServer byt deleting an
        indication subscription instance in the server

        Parameters:

          server_id (:term:`string`):
            The server ID for the WBEM server, returned by :meth:`add_server`.

          sub_path (:class:`~pywbem.CIMInstanceName`):
            Instance path of the indication subscription instance in the WBEM
            server.

          remove_all (:class: `bool`) If True, this function attempts to
            remove the associated filter and destination objects for the
            defined subscription from the WBEM Server also.

        Raises:

            Exceptions raised by :class:`~pywbem.WBEMConnection`.
        """
        if server_id not in self._servers:
            raise ValueError("WBEM server not known by listener: %s" % \
                             server_id)
        server = self._servers[server_id]
        sub_instance_path = server.con.getInstance(sub_path)
        filter_path = sub_instance_path['Filter']
        dest_path = sub_instance_path['Handler']
        server.conn.DeleteInstance(sub_path)

        if remove_all:
            server.conn.DeleteInstance(filter_path)
            server.conn.DeleteInstance(dest_path)

    def remove_dynamic_subscription(self, server_id, sub_path):
        """
        Remove an indication subscription from a WBEM server, by deleting an
        indication subscription instance in the server.

        Parameters:

          server_id (:term:`string`):
            The server ID for the WBEM server, returned by :meth:`add_server`.

          sub_path (:class:`~pywbem.CIMInstanceName`):
            Instance path of the indication subscription instance in the WBEM
            server.

        Raises:

            Exceptions raised by :class:`~pywbem.WBEMConnection`.
        """
        if server_id not in self._servers:
            raise ValueError("WBEM server not known by listener: %s" % \
                             server_id)
        server = self._servers[server_id]
        if server_id in self._subscription_paths:
            sub_paths = self._subscription_paths[server_id]
            for i, path in enumerate(sub_paths):
                if path == sub_path:
                    server.conn.DeleteInstance(path)
                    del sub_paths[i]
                    break

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
        return self._subscription_paths[server_id]

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

def _create_destination(server, dest_url, listener_id=None):
    """
    Create a listener destination instance in the Interop namespace of a
    WBEM server and return its instance path.

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
    dest_inst['Name'] = 'pywbemlistener:%s%s' % (listener_id, uuid.uuid4())
    dest_inst['Destination'] = dest_url

    dest_path = server.conn.CreateInstance(dest_inst)
    return dest_path

def _create_filter(server, source_namespace, query, query_language, \
                   listener_id=None, filter_id=None):
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

      listener_id (:term: `string`))
        If not `None` a string of printable characters to be inserted in the
        name property of filter and listener destination instances to help the
        listener identify its filters and destination instances in a
        WBEM Server. The string must not contain the ":" character.

        The form for the name property of a PyWBEM of a filter is:

        "pywbemfilter:" [<listener_id>  ":"] [<filter_id> ":"] <guid>

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
    filter_inst['Name'] = 'pywbemfilter:%s%s%s' % (listener_id, \
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

