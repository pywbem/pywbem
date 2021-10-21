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

The SubscriptionManager only manages CIM/XML listener destinations and does not
view, add, or remove other destinations such as files, etc.

The CIM/XML WBEM listener is identified through its URL, so it may be the pywbem
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
Python program aborts or the client is terminated), the corresponding CIM
instances in the WBEM server still exist, but the knowledge is lost that these
instances were owned by that subscription manager. Therefore, the subscription
manager discovers owned subscriptions, filters, and listener destinations when
a server is added. For this discovery, is based upon the Name property.
Therefore, if the Name property is set by the user (e.g. because a management
profile requires a particular name), the filter must be permanent and cannot be
owned.

Since :class:`~pywbem.WBEMSubscriptionManager` does not directly modify
existing instances of filter or destinations or subscriptions, the user must do
this directly through the `ModifyInstance` WBEM request method and then update
the local owned instances list by executing get_all_filters(),
get_all_destinations(), or get_all_subscriptions().

Examples
--------

The following example code demonstrates the use of a subscri tion manager
to subscribe for a CIM alert indication on a WBEM server. The WBEM listener
is assumed to exist somewhere and is identified by its URL::

    from pywbem import WBEMConnection, WBEMServer, WBEMSubscriptionManager

    server_url = 'http://myserver'
    server_credentials = ('myuser', 'mypassword')

    listener_url = 'http://mylistener'

    conn = WBEMConnection(server_url, server_credentials)
    server = WBEMServer(conn)
    sub_mgr = WBEMSubscriptionManager(subscription_manager_id='fred')

    # Register the server in the subscription manager:
    server_id = sub_mgr.add_server(server)

    # Add a listener destination in the server:
    dest_inst = sub_mgr.add_destination(
        server_id, listener_url, owned=True, destination_id='id1')

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
    filter2_inst = sub_mgr.add_filter(
        server_id, filter2_source_ns, filter2_query, filter2_language,
        owned=True, filter_id="myalert")
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
import warnings
from socket import getfqdn
import six
from nocasedict import NocaseDict

from ._server import WBEMServer
from ._cim_obj import CIMInstance, CIMInstanceName
from ._cim_types import Uint16
from ._cim_http import parse_url
from ._cim_constants import CIM_ERR_FAILED, CIM_ERR_ALREADY_EXISTS
from ._exceptions import CIMError
from ._warnings import OldNameFilterWarning, OldNameDestinationWarning
from ._utils import _format

# CIM model classnames for subscription components
SUBSCRIPTION_CLASSNAME = 'CIM_IndicationSubscription'
DESTINATION_CLASSNAME = 'CIM_ListenerDestinationCIMXML'
FILTER_CLASSNAME = 'CIM_IndicationFilter'
SYSTEM_CREATION_CLASSNAME = 'CIM_ComputerSystem'

DEFAULT_QUERY_LANGUAGE = 'WQL'

__all__ = ['WBEMSubscriptionManager']


def validate_persistence_type(pt):
    """
    Validate persistence type parameter pt as string possible
    values::transient" or "permanent" and convert to corresponding integer
    value
    Returns integer value or None for the `PersistenceType` property based on
    the input string.
    """
    if pt is None:
        return None
    if not isinstance(pt, six.string_types):
        raise ValueError(
            _format("The persistence_type must be a string. Type {0} not "
                    "allowed.", type(pt)))

    persistence_type_dict = NocaseDict([('permanent', 2), ('transient', 3)])

    if pt not in persistence_type_dict:
        raise ValueError(
            _format("The persistence_type string must be one of: {0}."
                    " The value '{1}' is invalid",
                    ", ".join(list(persistence_type_dict.keys())), pt))

    return persistence_type_dict[pt]


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
            destination instances and thus allows identifying these instances
            in a WBEM server.

            Must not be `None`.

            The string must consist of printable characters, and must not
            contain the character ':' because that is the separator between
            components within the value of the `Name` property.

        Raises:

            ValueError: Incorrect input parameter values.
            TypeError: Incorrect input parameter types.
        """

        # The following dictionaries have the WBEM server ID as a key.
        self._servers = {}  # WBEMServer objects for the WBEM servers
        self._owned_subscriptions = {}  # CIMInstance of owned subscriptions
        self._owned_filters = {}  # CIMInstance of owned filters
        self._owned_destinations = {}  # CIMInstance owned destinations
        self._systemnames = {}  # Dict that will contain SystemNames

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
            "_servers={s._servers}, _systemnames={s._systemnames!A}"
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
            "_systemnames={s._systemnames!A}",
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

        # Get the SystemName from the WBEMServer CIM_ObjectManager for this
        # server.
        self._systemnames[server_id] = server.cimom_inst['SystemName']

        # Issue #2709 Expand to account for WBEMServer profile

        # Get the hostname of the client system to be part of destination Name
        this_client = getfqdn()

        # Recover owned destination, filter, and subscription instances
        # that exist on the WBEMServer
        dest_name_pattern = re.compile(
            _format(r'^pywbemdestination:{0}:[^:]*$',
                    self._subscription_manager_id))
        dest_name_old_pattern = re.compile(
            _format(r'^pywbemdestination:owned:{0}:{1}:[^:]*$',
                    this_client, self._subscription_manager_id))

        dest_insts = server.conn.EnumerateInstances(
            DESTINATION_CLASSNAME, namespace=server.interop_ns)

        for inst in dest_insts:
            if re.match(dest_name_pattern, inst.path.keybindings['Name']):
                self._owned_destinations[server_id].append(inst)
            if re.match(dest_name_old_pattern, inst.path.keybindings['Name']):
                warnings.warn(
                    _format(
                        "Ignored listener destination instance when detecting "
                        "owned instances because it has the old name format: "
                        "{0}",
                        inst.path),
                    OldNameDestinationWarning, 2)

        filter_name_pattern = re.compile(
            _format(r'^pywbemfilter:{0}:[^:]*$',
                    self._subscription_manager_id))
        filter_name_old_pattern = re.compile(  # before pywbem 1.3
            _format(r'^pywbemfilter:owned:{0}:{1}:[^:]*:[^:]*$',
                    this_client, self._subscription_manager_id))

        filter_insts = server.conn.EnumerateInstances(
            FILTER_CLASSNAME, namespace=server.interop_ns)

        for inst in filter_insts:
            if re.match(filter_name_pattern, inst.path.keybindings['Name']):
                self._owned_filters[server_id].append(inst)
            if re.match(filter_name_old_pattern, inst.path.keybindings['Name']):
                warnings.warn(
                    _format(
                        "Ignored indication filter instance when detecting "
                        "owned instances because it has the old name format: "
                        "{0}",
                        inst.path),
                    OldNameFilterWarning, 2)

        sub_insts = server.conn.EnumerateInstances(
            SUBSCRIPTION_CLASSNAME, namespace=server.interop_ns)
        owned_filter_paths = [inst.path for inst in
                              self._owned_filters[server_id]]
        owned_destination_paths = [inst.path for inst in
                                   self._owned_destinations[server_id]]

        # Subscription is owned if either filter or destination is owned.
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

    def add_destination(self, server_id, listener_url, owned=True,
                        destination_id=None, name=None,
                        persistence_type=None):
        """
        Add a listener destination to be the target of indications sent by a
        WBEM server, by creating an instance of CIM class
        "CIM_ListenerDestinationCIMXML" in the Interop namespace of the
        server.

        The `Name` property of the created listener destination instance can be
        set in one of two ways:

        * directly by specifying the `name` parameter.

          In this case, the `Name` property is set directly to the `name`
          parameter.

          This should be used in cases where the user needs to have control
          over the destination name (e.g. because a DMTF management profile
          requires a particular name).

          The `name` parameter can only be specified for permanent destinations.

        * indirectly by specifying the `destination_id` parameter.

          In this case, the value of the `Name` property will be:

          ``"pywbemdestination:" {submgr_id} ":" {destination_id}``

          where:

          - ``{submgr_id}`` is the subscription manager ID
          - ``{destination_id}`` is the value of the `destination_id` parameter

          The `destination_id` parameter can only be specified for owned
          destinations.

          If an owned listener destination instance for the specified listener
          URL and `PersistenceType` already exists, it is returned without
          creating a new instance.

        If a listener destination instance with the specified or generated
        `Name` property already exists, the method raises
        CIMError(CIM_ERR_ALREADY_EXISTS). Note that this is a more strict
        behavior than what a WBEM server would do, because the `Name` property
        is only one of four key properties.

        Parameters:

          server_id (:term:`string`):
            The server ID of the WBEM server, returned by
            :meth:`~pywbem.WBEMSubscriptionManager.add_server`.

          listener_url (:term:`string`):
            The URL of the WBEM listener that should receive the indications.

            The WBEM listener may be a :class:`~pywbem.WBEMListener` object or
            any external WBEM listener.

            The listener URL string must have the format:

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

            The port is required in the listener URL.

            See :class:`~pywbem.WBEMConnection` for examples of valid URLs,
            with the caveat that the port in server URLs is optional.

          owned (:class:`py:bool`):
            Defines the ownership type of the created listener destination
            instance: If `True`, it will be owned. Otherwise, it will be
            permanent. See :ref:`WBEMSubscriptionManager` for details about
            these ownership types.

          destination_id (:term:`string`):
            A destination ID string that is used as a component in the value of
            the `Name` property of owned destination instances to help the user
            identify these instances in a WBEM server, or `None` if the `name`
            parameter is specified.

            The string must consist of printable characters, and must not
            contain the character ':' because that is the separator between
            components within the value of the `Name` property.

            This parameter is required for owned destinations and is rejected
            for permanent destinations.

          name (:term:`string`):
            The destination name to be used directly for the `Name` property of
            permanent destination instances, or `None` if the `destination_id`
            parameter is specified.

            This parameter is required for permanent destinations and is
            rejected for owned destinations.

          persistence_type (:term:`string`):
            Optional string where the allowed strings are "transient" and
            "permanent" and the default is None.  The strings are used to
            set the `PersistenceType` property, an integer property with the
            values of 2 (Permanent) or 3 (Transient)

            The default value is None so that the `PersistenceType`
            property is not created on the destination instance for permanent
            filters. and is created with PersistenceType 3 (Transient) for owned
            destinations.

            Most WBEM servers set the PersistenceType value to 2 (Permanent) if
            no value is provided.

            This method does not provide for adding the OtherPersistenceType
            property.

        Returns:

            :class:`~pywbem.CIMInstance`: The created listener destination
            instance for the defined listener URL.

        Raises:

            Exceptions raised by :class:`~pywbem.WBEMConnection`.
            CIMError(CIM_ERR_ALREADY_EXISTS): A filter with the specified
              or generated `Name` property already exists in the server.
            ValueError: Incorrect input parameter values.
        """

        # server_id is validated in _create_...() method.

        if owned:
            if destination_id is None:
                raise ValueError("For owned destinations, the 'destination_id' "
                                 "parameter must be specified")
            if name is not None:
                raise ValueError("For owned destinations, the 'name' "
                                 "parameter must not be specified")
        else:  # permanent
            if name is None:
                raise ValueError("For permanent destinations, 'name' "
                                 "parameter must be specified")
            if destination_id is not None:
                raise ValueError("For permanent destinations, the "
                                 "'destination_id' parameter must not be "
                                 "specified")

        # Validate persistence_type, and default it to 3 (transient) if the
        # destination is owned.
        persistence_type_value = validate_persistence_type(persistence_type)
        if owned and persistence_type is None:
            persistence_type_value = 3

        dest_inst = self._create_destination(
            server_id, listener_url, owned, destination_id, name,
            persistence_type_value)

        return dest_inst

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

    def add_filter(self, server_id, source_namespaces, query,
                   query_language=DEFAULT_QUERY_LANGUAGE, owned=True,
                   filter_id=None, name=None, source_namespace=None):
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
          requires a particular name).

          The `name` parameter can only be specified for permanent filters.

        * indirectly by specifying the `filter_id` parameter.

          In this case, the value of the `Name` property will be:

          ``"pywbemfilter:" {submgr_id} ":" {filter_id}``

          where:

          - ``{submgr_id}`` is the subscription manager ID
          - ``{filter_id}`` is the filter ID

          The `filter_id` parameter can only be specified for owned filters.

        If an indication filter instance with the specified or generated `Name`
        property already exists, the method raises
        CIMError(CIM_ERR_ALREADY_EXISTS). Note that this is a more strict
        behavior than what a WBEM server would do, because the `Name` property
        is only one of four key properties.

        Parameters:

          server_id (:term:`string`):
            The server ID of the WBEM server, returned by
            :meth:`~pywbem.WBEMSubscriptionManager.add_server`.

          source_namespaces (:term:`string`, list of :term:`string`, or None):
            Source namespace or list of source namespaces  of the indication
            filter. The values will be inserted into the CIM_IndicationFilter
            SourceNamespaces property. If None, the SourceNamespaces property
            will not be created. and the WBEM server will use the Interop
            namespace as the source namespace for the indication filter.

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

          filter_id (:term:`string`):
            A filter ID string that is used as a component in the value of the
            `Name` property of filter instances to help the user identify
            these instances in a WBEM server, or `None` if the `name`
            parameter is specified.

            The string must consist of printable characters, and must not
            contain the character ':' because that is the separator between
            components within the value of the `Name` property.

            This parameter is required for owned filters and is rejected for
            permanent filters.

            There is no requirement that the filter ID be unique. This can be
            used to identify groups of filters by using the same value for
            multiple filters.

          name (:term:`string`):
            *New in pywbem 0.10.*

            The filter name to be used directly for the `Name` property of the
            filter instance, or `None` if the `filter_id` parameter is
            specified.

            This parameter is required for permanent filters and is rejected for
            owned filters.

          source_namespace (:term:`string`):
            Optional source namespace of the indication filter. If the
            parameter is provided the value will be inserted into the
            CIM_IndicationFilter SourceNamespace property. Otherwise the
            SourceNamespace property will not be created. The `SourceNamespace`
            property is deprecated in the DMTF CIM_IndicationFilter class in
            favor of `SourceNamespaces` (see the `SourceNamespaces` parameter
            above). This parameter is provided only to support calls to
            add_filter() that use the `source_namespace` as a keyword parameter
            or to support very old WBEM servers (prior to DMTF schema version
            2.22) that require the `SourceNamespace` property.

        Returns:

            :class:`~pywbem.CIMInstance`: The created indication filter
            instance.

        Raises:
            Exceptions raised by :class:`~pywbem.WBEMConnection`.
            CIMError(CIM_ERR_ALREADY_EXISTS): A filter with the specified or
              generated `Name` property already exists in the server.
            ValueError: Incorrect input parameter values.
            TypeError: Incorrect input parameter types.
        """

        # server_id is validated in _create_...() method.

        if owned:
            if filter_id is None:
                raise ValueError("For owned filters, the 'filter_id' "
                                 "parameter must be specified")
            if name is not None:
                raise ValueError("For owned filters, the 'name' "
                                 "parameter must not be specified")
        else:  # permanent
            if name is None:
                raise ValueError("For permanent filters, 'name' "
                                 "parameter must be specified")
            if filter_id is not None:
                raise ValueError("For permanent filters, the 'filter_id' "
                                 "parameter must not be specified")

        if filter_id is not None:
            if not isinstance(filter_id, six.string_types):
                raise TypeError(
                    _format("Invalid type for filter ID: {0!A}", filter_id))
            if ':' in filter_id:
                raise ValueError(
                    _format("Filter ID contains ':': {0!A}", filter_id))

        if source_namespaces is not None:
            if not isinstance(source_namespaces, (six.string_types, list)):
                raise TypeError(
                    _format("source_namespaces must string or list. {0} is "
                            "type {1}.", source_namespace,
                            type(source_namespace)))

            if isinstance(source_namespaces, six.string_types):
                source_namespaces = [source_namespaces]

        filter_inst = self._create_filter(
            server_id, source_namespaces, query, query_language,
            filter_id, name, source_namespace=source_namespace)

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

        Owned subscriptions are added conditionally: If the
        subscription instance to be added is already registered with
        this subscription manager and has the same path, it is not
        created or modified. In that case, the instance already registered is
        returned. This method does not modify subscriptions.

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
            subscription instances created in the WBEM server or the instance
            already in the WBEM server if the new instance is owned and there
            is already an owned subscription with the same path.

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

    def _create_destination(self, server_id, dest_url, owned, destination_id,
                            name, persistence_type_value):
        """
        Create a listener destination instance in the Interop namespace of a
        WBEM server and return that instance.

        In order to catch any changes the server applies, the instance is
        retrieved again using the instance path returned by instance creation.

        If the request is owned and an owned instance is found in the server
        with the same value of the `Destination` and `PersistenceType`
        properties, no new instance is created and the existing is returned. A
        client may detect that an existing instance was returned by comparing
        the destination_id component of the requested `Name` property with the
        destination_id of the submitted `Name` property.

        Parameters:

          server_id (:term:`string`):
            The server ID of the WBEM server, returned by
            :meth:`~pywbem.WBEMSubscriptionManager.add_server`.

          dest_url (:term:`string`):
            URL of the listener that is used by the WBEM server as the
            destination for indications.

            The URL scheme (e.g. http/https) determines whether the WBEM server
            uses HTTP or HTTPS for sending the indication. Host and port in the
            URL specify the target location to be used by the WBEM server.

          owned (:class:`py:bool`):
            Defines the ownership type of the created listener destination
            instance: If `True`, it will be owned. Otherwise, it will be
            permanent. See :ref:`WBEMSubscriptionManager` for details about
            these ownership types.

          destination_id (:term:`string`):
            A destination ID string that is used as a component in the value of
            the `Name` property of owned destination instances to help the user
            identify these instances in a WBEM server, or `None` if the `name`
            parameter is specified.

            The string must consist of printable characters, and must not
            contain the character ':' because that is the separator between
            components within the value of the `Name` property.

            This parameter is required for owned destinations and is rejected
            for permanent destinations.

          name (:term:`string`):
            The destination name to be used directly for the `Name` property of
            permanent destination instances, or `None` if the `destination_id`
            parameter is specified.

            This parameter is required for permanent destinations and is
            rejected for owned destinations.

          persistence_type_value (:class:`int` or None)
            If integer, it is the value of the PeristenceType property.  If
            None, the `PersistenceType` property is not included in the
            created instance.

        Returns:

            :class:`~pywbem.CIMInstance`: The created instance, as retrieved
            from the server or, if the destination is owned and an instance
            already exists with the same dest_url and persistence_type value,
            return that instance.

        Raises:

            Exceptions raised by :class:`~pywbem.WBEMConnection`.
        """

        # Validate server_id
        server = self._get_server(server_id)

        # Validate the URL by reconstructing it. Do not allow defaults
        _, _, listener_url = parse_url(dest_url, allow_defaults=False)

        dest_inst = CIMInstance(DESTINATION_CLASSNAME)
        dest_inst['CreationClassName'] = DESTINATION_CLASSNAME
        dest_inst['SystemCreationClassName'] = SYSTEM_CREATION_CLASSNAME
        dest_inst['SystemName'] = self._systemnames[server_id]
        if persistence_type_value is not None:
            dest_inst['PersistenceType'] = Uint16(persistence_type_value)

        if owned:
            name = _format(
                'pywbemdestination:{0}:{1}',
                self._subscription_manager_id, destination_id)
        dest_inst['Name'] = name
        dest_inst['Destination'] = listener_url

        # Test if instance already exists in the WBEM server
        existing_dest_insts = server.conn.EnumerateInstances(
            DESTINATION_CLASSNAME, namespace=server.interop_ns)
        for inst in existing_dest_insts:
            name_prop = inst.properties.get('Name', None)  # CIMProperty
            if name_prop and name_prop.value == name:
                raise CIMError(
                    CIM_ERR_ALREADY_EXISTS,
                    "Listener destination instance with Name='{0}' already "
                    "exists: {1}".format(name, inst.path))

        if owned:
            # If an owned destination instance for the same destination and
            # persistence type already exists, reuse it and do not create a
            # new instance.
            for inst in self._owned_destinations[server_id]:
                if inst['Destination'] == dest_inst['Destination'] and \
                        inst['PersistenceType'] == dest_inst['PersistenceType']:
                    return inst

        dest_path = server.conn.CreateInstance(
            dest_inst, namespace=server.interop_ns)
        dest_inst = server.conn.GetInstance(dest_path)

        if owned:
            self._owned_destinations[server_id].append(dest_inst)

        return dest_inst

    def _create_filter(self, server_id, source_namespaces, query,
                       query_language, filter_id, name, source_namespace):
        """
        Create a :term:`dynamic indication filter` instance in the Interop
        namespace of a WBEM server and return that instance.

        In order to catch any changes the server applies, the instance is
        retrieved again using the instance path returned by instance creation.

        Parameters:

          server_id (:term:`string`):
            The server ID of the WBEM server, returned by
            :meth:`~pywbem.WBEMSubscriptionManager.add_server`.

          source_namespaces (list of :term:`string` or None):
            List of source namespaces of the indication filter. If None
            the SourceNamespaces property will not be created.

          query (:term:`string`):
            Filter query in the specified query language.

          query_language (:term:`string`):
            Query language for the specified filter query.

            Examples: 'WQL', 'DMTF:CQL'.

          filter_id (:term:`string`):
            Filter ID string to be incorporated into the `Name` property of the
            filter instance, or `None`.
            Mutually exclusive with the `name` parameter.

          name (:term:`string`):
            Value for the `Name` property of the filter instance, or `None`.
            Mutually exclusive with the `filter_id` parameter.

          source_namespace (:term:`string` or None):
            A namespace or None.

        Returns:

            :class:`~pywbem.CIMInstance`: The created instance, as retrieved
            from the server.

        Raises:

            Exceptions raised by :class:`~pywbem.WBEMConnection`.
        """

        # Validate server_id
        server = self._get_server(server_id)

        owned = filter_id is not None

        filter_inst = CIMInstance(FILTER_CLASSNAME)
        filter_inst['CreationClassName'] = FILTER_CLASSNAME
        filter_inst['SystemCreationClassName'] = SYSTEM_CREATION_CLASSNAME
        filter_inst['SystemName'] = self._systemnames[server_id]
        if owned:
            name = _format(
                'pywbemfilter:{0}:{1}',
                self._subscription_manager_id, filter_id)
        filter_inst['Name'] = name
        if source_namespaces:
            filter_inst['SourceNamespaces'] = source_namespaces
        if source_namespace:
            filter_inst['SourceNamespace'] = source_namespace
        filter_inst['Query'] = query
        filter_inst['QueryLanguage'] = query_language

        existing_filter_insts = server.conn.EnumerateInstances(
            FILTER_CLASSNAME, namespace=server.interop_ns)
        for inst in existing_filter_insts:
            name_prop = inst.properties.get('Name', None)  # CIMProperty
            if name_prop and name_prop.value == name:
                raise CIMError(
                    CIM_ERR_ALREADY_EXISTS,
                    "Filter instance with Name='{0}' already exists: {1}".
                    format(name, inst.path))
        filter_path = server.conn.CreateInstance(
            filter_inst, namespace=server.interop_ns)
        filter_inst = server.conn.GetInstance(filter_path)

        if owned:
            self._owned_filters[server_id].append(filter_inst)

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
                                   namespace=server.interop_ns,
                                   keybindings=[('Filter', filter_path),
                                                ('Handler', dest_path)])

        sub_inst = CIMInstance(SUBSCRIPTION_CLASSNAME)
        sub_inst.path = sub_path
        sub_inst['Filter'] = filter_path
        sub_inst['Handler'] = dest_path

        if owned:
            for inst in self._owned_subscriptions[server_id]:
                if inst.path == sub_path:
                    # Return the instance originally created since the
                    # creation process may have added properties.
                    # We do not care about any differences in properties since
                    # we only create new instances and sub_inst.path already
                    # exists.
                    return inst
            sub_path = server.conn.CreateInstance(
                sub_inst, namespace=server.interop_ns)
            sub_inst = server.conn.GetInstance(sub_path)
            self._owned_subscriptions[server_id].append(sub_inst)
        else:
            # Responsibility to ensure it does not exist yet is with the user
            sub_path = server.conn.CreateInstance(
                sub_inst, namespace=server.interop_ns)
            sub_inst = server.conn.GetInstance(sub_path)

        return sub_inst
