"""
The `WBEM server API`_ is provided by the :mod:`pywbem.server` module.

It provides basic functionality of a WBEM server that is relevant for a client.

The :class:`WBEMServer` class serves as a general access point for clients,
and supports determing the Interop namespace of the server, all namespaces, its
brand and version, the advertised management profiles, and functions to
subscribe for indications.

The :class:`ValueMapping` class maps corresponding entries in Values and
ValueMap qualifiers of a CIM element and supports a translation between the two.

Example
-------

The following example code displays some information about a WBEM server:

::

    from pywbem import WBEMConnection
    from pywbem.server import WBEMServer, ValueMapping

    def explore_server(server_url, username, password):

        print("WBEM server URL:\\n  %s" % server_url)

        conn = WBEMConnection(server_url, (username, password))
        server = WBEMServer(conn)

        print("Brand:\\n  %s" % server.brand)
        print("Version:\\n  %s" % server.version)
        print("Interop namespace:\\n  %s" % server.interop_ns)

        print("All namespaces:")
        for ns in server.namespaces:
            print("  %s" % ns)

        print("Advertised management profiles:")
        org_vm = ValueMapping.for_property(server, server.interop_ns,
            'CIM_RegisteredProfile', 'RegisteredOrganization')
        for inst in server.profiles:
            print("  %s %s Profile %s" % \\
                (org_vm.tovalues(str(inst['RegisteredOrganization'])),
                 inst['RegisteredName'], inst['RegisteredVersion']))

Example output:

::

    WBEM server URL:
      http://0.0.0.0
    Brand:
      pegasus
    Version:
      2.12.0
    Interop namespace:
      root/PG_Interop
    All namespaces:
      root/PG_InterOp
      root/PG_Internal
      root/cimv2
      root
    Advertised management profiles:
      SNIA Indication Profile 1.1.0
      SNIA Indication Profile 1.2.0
      SNIA Software Profile 1.1.0
      SNIA Software Profile 1.2.0
      SNIA Profile Registration Profile 1.0.0
      SNIA SMI-S Profile 1.2.0
      SNIA Server Profile 1.1.0
      SNIA Server Profile 1.2.0
      DMTF Profile Registration Profile 1.0.0
      DMTF Indications Profile 1.1.0
"""

import os
import sys
import time
import re
from socket import getfqdn

import six

import pywbem

__all__ = ['WBEMServer']


class WBEMServer(object):
    """
    A representation of a WBEM server that serves as a general access point to
    a client.

    It supports determing the Interop namespace of the server, all namespaces,
    its brand and version, the advertised management profiles, and functions to
    subscribe for indications.

    TODO: Provide function that returns the central instances of a profile,
    based on the new method, and the traditional central and scoping mechanism.
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
        'root/PG_Interop',  # Needed up to OpenPegasus 2.12?
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
        self._brand = None
        self._version = None
        self._profiles = None

    @property
    def conn(self):
        """
        The connection to the WBEM server, as a
        :class:`~pywbem.WBEMConnection` object.
        """
        return self._conn

    @property
    def interop_ns(self):
        """
        The name of the Interop namespace of the WBEM server, as a
        :term:`string`.
        """
        if self._interop_ns is None:
            self.determine_interop_ns()
        return self._interop_ns

    @property
    def namespace_classname(self):
        """
        The name of the CIM class that was found to represent the CIM
        namespaces of the WBEM server, as a :term:`string`.
        """
        if self._namespace_classname is None:
            self.determine_namespaces()
        return self._namespace_classname

    @property
    def namespaces(self):
        """
        A list with the names of all namespaces of the WBEM server, each
        list item being a :term:`string`.
        """
        if self._namespaces is None:
            self.determine_namespaces()
        return self._namespaces

    @property
    def brand(self):
        """
        Brand of the WBEM server, as a :term:`string`.

        The brand string will be one of the following:

        * ``pegasus``: OpenPegasus
        * ``sfcb``: SFCB
        * Value of the ElementName property of the CIM_ObjectManager instance,
          for any other WBEM servers.
        """
        if self._brand is None:
            self.determine_brand()
        return self._brand

    @property
    def version(self):
        """
        Version of the WBEM server, as a :term:`string`. `None`, if the version
        cannot be determined.
        """
        if self._version is None:
            self.determine_brand()
        return self._version

    @property
    def profiles(self):
        """
        List of management profiles advertised by the WBEM server, each list
        item being a :class:`CIMClassName` object representing the instance
        path of the corresponding CIM_RegisteredProfile instance.
        """
        if self._profiles is None:
            self.determine_profiles()
        return self._profiles

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

    def determine_brand(self):
        """
        Determine the brand of the WBEM server (e.g. OpenPegasus, SFCB, ...)
        and its version, by communicating with it and retrieving the
        CIM_ObjectManager instance.

        On success, this method sets the :attr:`brand` and :attr:`version`
        properties of this object and returns.
        Otherwise, it raises an exception.

        Raises:

            Exceptions raised by :class:`~pywbem.WBEMConnection`.
        """
        if self._interop_ns is None:
            self.determine_interop_ns()
        cimom_insts = self._conn.EnumerateInstances(
            "CIM_ObjectManager", namespace=self._interop_ns)
        if len(cimom_insts) != 1:
            raise pywbem.CIMError(pywbem.CIM_ERR_NOT_FOUND,
                                  "Unexpected number of CIM_ObjectManager " \
                                  "instances: %s " % \
                                  [i['ElementName'] for i in cimom_insts])
        cimom_inst = cimom_insts[0]
        element_name = cimom_inst['ElementName']
        if element_name == "Pegasus":
            brand = 'pegasus'
            # Description = "Pegasus OpenPegasus Version 2.12.0"
            m = re.match(r'.+ *Version *([^ ]+)', cimom_inst['Description'])
            if m:
                version = m.group(1)
            else:
                version = None
        elif element_name == "SFCB":
            brand = 'sfcb'
            # TODO: figure out version of SFCB
            version = None
        else:
            brand = element_name
            version = None
        self._brand = brand
        self._version = version

    def determine_profiles(self):
        """
        Determine the WBEM management profiles advertised by the WBEM server,
        by communicating with it and enumerating the instances of
        CIM_RegisteredProfile.

        If the profiles could be determined, this method sets the
        :attr:`profiles` property of this object to the list of
        CIM_RegisteredProfile instances (as :class:`CIMInstance` objects),
        and returns.
        Otherwise, it raises an exception.

        Raises:

            Exceptions raised by :class:`~pywbem.WBEMConnection`.
        """
        if self._interop_ns is None:
            self.determine_interop_ns()
        mp_insts = self._conn.EnumerateInstances("CIM_RegisteredProfile",
                                                 namespace=self._interop_ns)
        self._profiles = mp_insts

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


class ValueMapping(object):
    """
    A mapping between ValueMap and Values qualifiers on a specific CIM element
    (property, parameter, ...) in a WBEM server.

    Instances of this class should be created through one of the factory class
    methods: :meth:`for_property`, :meth:`for_method`, or
    :meth:`for_parameter`.
    """

    def __init__(self, element_obj, values_dict, valuemap_dict):
        """
        Parameters:

          element_obj (:class:`~pywbem.CIMProperty`, :class:`~pywbem.CIMMethod`, or :class:`~pywbem.CIMParameter`):
            The CIM element on which the qualifiers are defined.

          values_dict (dict):
            A dictionary that maps ValueMap qualifier entries to their
            corresponding Values qualifier entries.

          valuemap_dict (dict):
            A dictionary that maps Values qualifier entries to their
            corresponding ValueMap qualifier entries.
        """
        self._element_obj = element_obj
        self._values_dict = values_dict
        self._valuemap_dict = valuemap_dict

    @classmethod
    def for_property(cls, server, namespace, classname, propname):
        """
        Return a new :class:`ValueMapping` instance for the Values / ValueMap
        qualifiers defined on a CIM property.

        This is done by retrieving the class definition for the specified
        class, and by inspecting these qualifiers.

        Parameters:

          server (:class:`WBEMServer`):
            The WBEM server containing the namespace.

          namespace (:term:`string`):
            Name of the CIM namespace containing the class.

          classname (:term:`string`):
            Name of the CIM class exposing the property. The property can be
            defined in that class or inherited into that class.

          propname (:term:`string`):
            Name of the CIM property that defines the Values / ValueMap
            qualifiers.

        Returns:

            The created :class:`ValueMapping` instance for the Values /
            ValueMap qualifiers defined on the CIM property.

        Raises:

            Exceptions raised by :class:`~pywbem.WBEMConnection`.
        """
        class_obj = server.conn.GetClass(ClassName=classname,
                                         namespace=namespace,
                                         LocalOnly=False,
                                         IncludeQualifiers=True)
        property_obj = class_obj.properties[propname]
        return cls._create_for_element(property_obj)

    @classmethod
    def for_method(cls, server, namespace, classname, methodname):
        """
        Return a new :class:`ValueMapping` instance for the Values / ValueMap
        qualifiers defined on a CIM method.

        This is done by retrieving the class definition for the specified
        class, and by inspecting these qualifiers.

        Parameters:

          server (:class:`WBEMServer`):
            The WBEM server containing the namespace.

          namespace (:term:`string`):
            Name of the CIM namespace containing the class.

          classname (:term:`string`):
            Name of the CIM class exposing the method. The method can be
            defined in that class or inherited into that class.

          methodname (:term:`string`):
            Name of the CIM method that defines the Values / ValueMap
            qualifiers.

        Returns:

            The created :class:`ValueMapping` instance for the Values /
            ValueMap qualifiers defined on the CIM method.

        Raises:

            Exceptions raised by :class:`~pywbem.WBEMConnection`.
        """
        class_obj = server.conn.GetClass(ClassName=classname,
                                         namespace=namespace,
                                         LocalOnly=False,
                                         IncludeQualifiers=True)
        method_obj = class_obj.methods[methodname]
        return cls._create_for_element(method_obj)

    @classmethod
    def for_parameter(cls, server, namespace, classname, methodname,
                      parametername):
        """
        Return a new :class:`ValueMapping` instance for the Values / ValueMap
        qualifiers defined on a CIM parameter.

        This is done by retrieving the class definition for the specified
        class, and by inspecting these qualifiers.

        Parameters:

          server (:class:`WBEMServer`):
            The WBEM server containing the namespace.

          namespace (:term:`string`):
            Name of the CIM namespace containing the class.

          classname (:term:`string`):
            Name of the CIM class exposing the method. The method can be
            defined in that class or inherited into that class.

          methodname (:term:`string`):
            Name of the CIM method that has the parameter.

          parametername (:term:`string`):
            Name of the CIM parameter that defines the Values / ValueMap
            qualifiers.

        Returns:

            The created :class:`ValueMapping` instance for the Values /
            ValueMap qualifiers defined on the CIM parameter.

        Raises:

            Exceptions raised by :class:`~pywbem.WBEMConnection`.
        """
        class_obj = server.conn.GetClass(ClassName=classname,
                                         namespace=namespace,
                                         LocalOnly=False,
                                         IncludeQualifiers=True)
        method_obj = class_obj.methods[methodname]
        parameter_obj = method_obj.parameters[parametername]
        return cls._create_for_element(parameter_obj)

    @classmethod
    def _create_for_element(cls, element_obj):
        """
        Return a new :class:`ValueMapping` instance for the specified
        CIM element.

        The defaults defined in DSP0004 for a missing ValueMap qualifier
        are applied.

        Parameters:

          element_obj (:class:`~pywbem.CIMProperty`, :class:`~pywbem.CIMMethod`, or :class:`~pywbem.CIMParameter`):
            The CIM element on which the qualifiers are defined.

        Returns:

            The created :class:`ValueMapping` instance for the specified
            CIM element.
        """

        values_qual = element_obj.qualifiers.get('Values', None)
        valuemap_qual = element_obj.qualifiers.get('ValueMap', None)

        if valuemap_qual is None:
            # DSP0004 defines a default of consecutive index numbers
            valuemap_list = range(0, len(values_qual.value))
        else:
            valuemap_list = valuemap_qual.value
        if values_qual is None:
            # DSP0004 defines no default for a missing Values qualifier
            raise ValueError("No Values qualifier defined")
        values_list = values_qual.value

        values_dict = dict(zip(valuemap_list, values_list))
        valuemap_dict = dict(zip(values_list, valuemap_list))

        vm = ValueMapping(element_obj, values_dict, valuemap_dict)

        return vm

    @property
    def element(self):
        """
        Return the element on which the Values and ValueMap qualifiers are
        defined, as a CIM object (:class:`~pywbem.CIMProperty`,
        :class:`~pywbem.CIMMethod`, or :class:`~pywbem.CIMParameter`).
        """
        return self._element_obj

    def tovalues(self, valuemap):
        """
        Return the entry in the Values qualifier that corresponds to an entry
        in the ValueMaps qualifier.

        Parameters:

          valuemap (:term:`string`):
            The entry in the ValueMaps qualifier.

        Returns:

          :term:`string`:
            The entry in the Values qualifier.

        Raises:

            KeyError: The ValueMaps entry does not exist in this mapping.
        """
        return self._values_dict[valuemap]

    def tovaluemap(self, values):
        """
        Return the entry in the ValueMap qualifier that corresponds to an entry
        in the Values qualifier.

        Parameters:

          values (:term:`string`):
            The entry in the Values qualifier.

        Returns:

          :term:`string`:
            The entry in the ValueMap qualifier.

        Raises:

            KeyError: The Values entry does not exist in this mapping.
        """
        return self._valuemap_dict[values]

