"""
The `WBEM server API`_ is provided by the :mod:`pywbem.server` module.

It provides basic functionality of a WBEM server that is relevant for a
client, such as determing its Interop namespace, the type of WBEM server,
the supported management profiles, and functions to subscribe for indications.

Example
-------

The following example code displays the namespaces of a WBEM server:

::

    from pywbem import WBEMConnection
    from pywbem.server import WBEMServer

    def main():

        conn1 = WBEMConnection('http://server1')
        server1 = WBEMServer(conn1)
        server1.determine_interop_ns()

        for ns in server1.namespaces:
            print(ns)
"""

import os
import sys
import time
from socket import getfqdn

import six

import pywbem

__all__ = ['WBEMServer']


class WBEMServer(object):
    """
    A representation of a WBEM server that serves as an access point to
    a client, providing basic functionality such as determing its Interop
    namespace, the type of WBEM server, the supported management profiles,
    and functions to subscribe for indications.
    """

    #: A class variable with the possible names of Interop namespaces that
    #: should be tried when determining the Interop namespace on the WBEM
    #: server.
    INTEROP_NAMESPACES = [
        'interop',
        'root/interop',
        # TODO: Disabled namespace names with leading slash; see issue #255
        # '/interop',   
        # '/root/interop',
        'root/PG_Interop',
    ]

    #: A class variable with the possible names of CIM classes for
    #: representing CIM namespaces, that should be tried when determining the
    #: namespaces on the WBEM server.
    NAMESPACE_CLASSNAMES = [
        'CIM_Namespace',
        '__Namespace',
    ]

    def __init__(self, conn):
        """
        Parameters:

          conn (:class:`~pywbem.WBEMConnection`):
            Connection to the WBEM server.
        """
        self._conn = conn
        self._interop_ns = None
        self._namespaces = None
        self._namespace_classname = None

    @property
    def conn(self):
        """The connection to the WBEM server, as a
        :class:`~pywbem.WBEMConnection` object."""
        return self._conn

    @property
    def interop_ns(self):
        """The name of the Interop namespace of the WBEM server, as a
        :term:`string`. Initially `None`.

        Will be populated by :meth:`determine_interop_ns` or
        :meth:`validate_interop_ns`."""
        return self._interop_ns

    @property
    def namespace_classname(self):
        """The name of the CIM class that was found to represent the CIM
        namespaces of the WBEM server, as a :term:`string`. Initially `None`.

        Will be populated by :meth:`determine_namespaces`."""
        return self._namespace_classname

    @property
    def namespaces(self):
        """A list with the names of all namespaces of the WBEM server, each
        list item being a :term:`string`. Initially `None`.

        Will be populated by :meth:`determine_namespaces`."""
        return self._namespaces

    @property
    def url(self):
        """The URL of the WBEM server."""
        return self._conn.url

    def determine_interop_ns(self):
        """
        Determine the name of the Interop namespace of the WBEM server, by
        communicating with it and trying a number of possible Interop
        namespace names, that are defined in the :attr:`INTEROP_NAMESPACES`
        class variable.

        If the Interop namespace could be determined, this method sets the
        :attr:`interop_ns` property of this object to that namespace and
        returns.
        Otherwise, it raises an exception.

        Raises:

            Exceptions raised by :class:`~pywbem.WBEMConnection`.
        """
        test_classname = 'CIM_Namespace'
        interop_ns = None
        for ns in self.INTEROP_NAMESPACES:
            print("Debug: Trying with namespace=<%s>" % ns)
            try:
                self._conn.EnumerateInstanceNames(test_classname, namespace=ns)
            except pywbem.CIMError as exc:
                if exc.status_code == pywbem.CIM_ERR_INVALID_NAMESPACE:
                    # Current namespace does not exist.
                    continue
                elif exc.status_code in (pywbem.CIM_ERR_INVALID_CLASS,
                                         pywbem.CIM_ERR_NOT_FOUND):
                    # Class is not implemented, but current namespace exists.
                    interop_ns = ns
                    break
                else:
                    # Some other error happened.
                    raise
            else:
                # Namespace class is implemented in the current namespace.
                interop_ns = ns
                break
        if interop_ns is None:
            # Exhausted the possible namespaces
            raise pywbem.CIMError(pywbem.CIM_ERR_NOT_FOUND,
                                  "Interop namespace could not be determined " \
                                  "(tried %s)" % self.INTEROP_NAMESPACES)
        self._interop_ns = interop_ns

    def validate_interop_ns(self, interop_ns):
        """
        Validate whether the specified Interop namespace exists in the WBEM
        server, by communicating with it.

        If the specified Interop namespace exists, this method sets the
        :attr:`interop_ns` property of this object to that namespace and
        returns.
        Otherwise, it raises an exception.

        Parameters:

          interop_ns (:term:`string`):
            Name of the Interop namespace to be validated.

            Must not be `None`.

        Raises:

            Exceptions raised by :class:`~pywbem.WBEMConnection`.
        """
        test_classname = 'CIM_Namespace'
        try:
            self._conn.EnumerateInstanceNames(test_classname,
                                              namespace=interop_ns)
        except pywbem.CIMError as exc:
            # We tolerate it if the WBEM server does not implement this class,
            # as long as it does not return CIM_ERR_INVALID_NAMESPACE.
            if exc.status_code in (pywbem.CIM_ERR_INVALID_CLASS,
                                   pywbem.CIM_ERR_NOT_FOUND):
                pass
            else:
                raise
        self._interop_ns = interop_ns

    def determine_namespaces(self):
        """
        Determine the names of all namespaces of the WBEM server, by
        communicating with it and enumerating the instances of a number of
        possible CIM classes that typically represent CIM namespaces. Their
        class names are defined in the :attr:`NAMESPACE_CLASSNAMES`
        class variable.

        If the namespaces could be determined, this method sets the
        :attr:`namespace_classname` property of this object to the class name
        that was found to work, the :attr:`namespaces` property to these
        namespaces, and returns.
        Otherwise, it raises an exception.

        Raises:

            Exceptions raised by :class:`~pywbem.WBEMConnection`.
        """
        if self._interop_ns is None:
            self.determine_interop_ns()
        ns_insts = None
        for ns_classname in self.NAMESPACE_CLASSNAMES:
            try:
                ns_insts = self._conn.EnumerateInstances(
                    ns_classname, namespace=self._interop_ns)
            except pywbem.CIMError as exc:
                if exc.status_code in (pywbem.CIM_ERR_INVALID_CLASS,
                                       pywbem.CIM_ERR_NOT_FOUND):
                    # Class is not implemented, try next one.
                    continue
                else:
                    # Some other error.
                    raise
            else:
                # Found a namespace class that is implemented.
                break
        if ns_insts is None:
            # Exhausted the possible class names
            raise pywbem.CIMError(pywbem.CIM_ERR_NOT_FOUND,
                                  "Namespace class could not be determined " \
                                  "(tried %s)" % self.NAMESPACE_CLASSNAMES)
        self._namespace_classname = ns_classname
        self._namespaces = [inst['Name'] for inst in ns_insts]

    def create_destination(self, dest_url):
        """
        Create a listener destination instance in the Interop namespace of the
        WBEM server and return its instance path.

        Parameters:

          dest_url (:term:`string`):
            URL of the listener that is used by the WBEM server to send any
            indications to.

            The URL scheme (e.g. http/https) determines whether the WBEM server
            uses HTTP or HTTPS for sending the indication. Host and port in the
            URL specify the target location to be used by the WBEM server.

        Returns:

          :class:`~pywbem.CIMInstanceName` object representing the instance
          path of the created instance.

        Raises:

            Exceptions raised by :class:`~pywbem.WBEMConnection`.
        """

        if self._interop_ns is None:
            self.determine_interop_ns()

        classname = 'CIM_ListenerDestinationCIMXML'

        dest_path = pywbem.CIMInstanceName(classname)
        dest_path.classname = classname
        dest_path.namespace = self._interop_ns

        dest_inst = pywbem.CIMInstance(classname)
        dest_inst.path = dest_path
        dest_inst['CreationClassName'] = classname
        dest_inst['SystemCreationClassName'] = 'CIM_ComputerSystem'
        dest_inst['SystemName'] = getfqdn()
        dest_inst['Name'] = 'cimlistener%d' % time.time()
        dest_inst['Destination'] = dest_url

        dest_path = self._conn.CreateInstance(dest_inst)
        return dest_path

    def create_filter(self, query, query_language):
        """
        Create a dynamic indication filter instance in the Interop namespace
        of the WBEM server and return its instance path.

        Parameters:

          query (:term:`string`):
            Filter query in the specified query language.

          query_language (:term:`string`):
            Query language for the specified filter query.

            Examples: 'WQL', 'DMTF:CQL'.

        Returns:

          :class:`~pywbem.CIMInstanceName` object representing the instance
          path of the created instance.

        Raises:

            Exceptions raised by :class:`~pywbem.WBEMConnection`.
        """

        if self._interop_ns is None:
            self.determine_interop_ns()

        classname = 'CIM_IndicationFilter'

        filter_path = pywbem.CIMInstanceName(classname)
        filter_path.classname = classname
        filter_path.namespace = self._interop_ns

        filter_inst = pywbem.CIMInstance(classname)
        filter_inst.path = filter_path
        filter_inst['CreationClassName'] = classname
        filter_inst['SystemCreationClassName'] = 'CIM_ComputerSystem'
        filter_inst['SystemName'] = getfqdn()
        filter_inst['Name'] = 'cimfilter%d' % time.time()
        filter_inst['Query'] = query
        filter_inst['QueryLanguage'] = query_language

        filter_path = self._conn.CreateInstance(filter_inst)
        return filter_path

    def create_subscription(self, dest_path, filter_path):
        """
        Create an indication subscription instance in the Interop namespace of
        the WBEM server and return its instance path.

        Parameters:

          dest_path (:class:`~pywbem.CIMInstanceName`):
            Instance path of the listener destination instance in the WBEM
            server that references this listener.

          filter_path (:class:`~pywbem.CIMInstanceName`):
            Instance path of the indication filter instance in the WBEM
            server that specifies the indications to be sent.

        Returns:

          :class:`~pywbem.CIMInstanceName` object representing the instance
          path of the created instance.

        Raises:

            Exceptions raised by :class:`~pywbem.WBEMConnection`.
        """

        if self._interop_ns is None:
            self.determine_interop_ns()

        classname = 'CIM_IndicationSubscription'

        sub_path = pywbem.CIMInstanceName(classname)
        sub_path.classname = classname
        sub_path.namespace = self._interop_ns

        sub_inst = pywbem.CIMInstance(classname)
        sub_inst.path = sub_path
        sub_inst['Filter'] = filter_path
        sub_inst['Handler'] = dest_path

        sub_path = self._conn.CreateInstance(sub_inst)
        return sub_path

