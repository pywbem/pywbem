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
The WBEM server API encapsulates certain functionality of a WBEM server for use
by a WBEM client application, such as determining the Interop namespace of the
server, or the management profiles advertised by the server.

This chapter has the following sections:

* :ref:`Example <Server Example>` - An example on how to use the API.

* :ref:`WBEMServer` - The :class:`~pywbem.WBEMServer` class serves as a general
  access point for clients to WBEM servers. It allows determining the Interop
  namespace of the server, or the advertised management profiles.

* :ref:`ValueMapping` - The :class:`~pywbem.ValueMapping` class maps
  corresponding values of the `Values` and `ValueMap` qualifiers of a CIM
  element and supports the translation of the actual value (often an integer)
  to the corresponding value of the `Values` qualifier.

.. note::

   The WBEM server API has been introduced in v0.9.0 as experimental and
   has been declared final in 0.10.0.

.. _`Server Example`:

Example
-------

The following example code displays some information about a WBEM server:

::

    from pywbem import WBEMConnection, WBEMServer, ValueMapping

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
            org = org_vm.tovalues(inst['RegisteredOrganization'])
            name = inst['RegisteredName']
            vers = inst['RegisteredVersion']
            print("  %s %s Profile %s" % (org, name, vers))

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

import re
import six

from .cim_constants import CIM_ERR_INVALID_NAMESPACE, CIM_ERR_INVALID_CLASS, \
    CIM_ERR_METHOD_NOT_AVAILABLE, CIM_ERR_NOT_SUPPORTED, CIM_ERR_NOT_FOUND
from .exceptions import CIMError
from .cim_obj import CIMInstanceName, NocaseDict
from .cim_types import CIMInt, type_from_name
from .cim_operations import WBEMConnection

__all__ = ['WBEMServer', 'ValueMapping']


class WBEMServer(object):
    """
    A representation of a WBEM server that serves as a general access point to
    a client.

    It supports determining the Interop namespace of the server, all namespaces,
    its brand and version, the advertised management profiles and finally
    allows to retrieve the central instances of a management profile with
    one method invocation regardless of whether the profile implementation
    chose the central or scoping class profile advertisement methodology
    (see :term:`DSP1033`).

    It also provides functions to subscribe for indications.
    """

    #: A class variable with the possible names of Interop namespaces that
    #: should be tried when determining the Interop namespace on the WBEM
    #: server.
    INTEROP_NAMESPACES = [
        'interop',
        'root/interop',
        'root/PG_Interop',
        # TODO: Clarify which OpenPegasus versions need root/PGInterOp?
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
        if not isinstance(conn, WBEMConnection):
            raise TypeError("conn argument of WBEMServer must be a "
                            "WBEMConnection object")
        self._conn = conn
        self._interop_ns = None
        self._namespaces = None
        self._namespace_classname = None
        self._brand = None
        self._version = None
        self._profiles = None

    def __repr__(self):
        """
        Return a representation of the :class:`~pywbem.WBEMServer` object
        with all attributes, that is suitable for debugging.
        """
        return "%s(url=%r, conn=%r, interop_ns=%s, namespaces=%s, " \
               "namespace_classname=%r, brand=%r, version=%r, " \
               "profiles=[... %s instances])" % \
               (self.__class__.__name__, self.url, self.conn, self.interop_ns,
                self.namespaces, self.namespace_classname, self.brand,
                self.version, len(self.profiles))

    @property
    def url(self):
        """
        The URL of the WBEM server, as a :term:`string`.
        """
        return self._conn.url

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

        Raises:

            Exceptions raised by :class:`~pywbem.WBEMConnection`.
            CIMError: CIM_ERR_NOT_FOUND, Interop namespace could not be
              determined.
        """
        if self._interop_ns is None:
            self._determine_interop_ns()
        return self._interop_ns

    @property
    def namespace_classname(self):
        """
        The name of the CIM class that was found to represent the CIM
        namespaces of the WBEM server, as a :term:`string`.

        Raises:

            Exceptions raised by :class:`~pywbem.WBEMConnection`.
            CIMError: CIM_ERR_NOT_FOUND, Interop namespace could not be
              determined.
            CIMError: CIM_ERR_NOT_FOUND, Namespace class could not be
              determined.
        """
        if self._namespace_classname is None:
            self._determine_namespaces()
        return self._namespace_classname

    @property
    def namespaces(self):
        """
        A list with the names of all namespaces of the WBEM server, each
        list item being a :term:`string`.

        Raises:

            Exceptions raised by :class:`~pywbem.WBEMConnection`.
            CIMError: CIM_ERR_NOT_FOUND, Interop namespace could not be
              determined.
            CIMError: CIM_ERR_NOT_FOUND, Namespace class could not be
              determined.
        """
        if self._namespaces is None:
            self._determine_namespaces()
        return self._namespaces

    @property
    def brand(self):
        """
        Brand of the WBEM server, as a :term:`string`.

        The brand string will be one of the following:

        * ``"OpenPegasus"``, for OpenPegasus
        * ``"SFCB"``, for SFCB
        * First word of the value of the ElementName property of the
          CIM_ObjectManager instance, for any other WBEM servers.
        * ``"unknown"``, if the ElementName property is Null.

        Raises:

            Exceptions raised by :class:`~pywbem.WBEMConnection`.
            CIMError: CIM_ERR_NOT_FOUND, Interop namespace could not be
              determined.
            CIMError: CIM_ERR_NOT_FOUND, Unexpected number of
              CIM_ObjectManager instances.
        """
        if self._brand is None:
            self._determine_brand()
        return self._brand

    @property
    def version(self):
        """
        Version of the WBEM server, as a :term:`string`. `None`, if the version
        cannot be determined.

        Raises:

            Exceptions raised by :class:`~pywbem.WBEMConnection`.
            CIMError: CIM_ERR_NOT_FOUND, Interop namespace could not be
              determined.
            CIMError: CIM_ERR_NOT_FOUND, Unexpected number of
              CIM_ObjectManager instances.
        """
        if self._version is None:
            self._determine_brand()
        return self._version

    @property
    def profiles(self):
        """
        List of management profiles advertised by the WBEM server, each list
        item being a :class:`~pywbem.CIMInstance` object representing a
        CIM_RegisteredProfile instance.

        Raises:

            Exceptions raised by :class:`~pywbem.WBEMConnection`.
            CIMError: CIM_ERR_NOT_FOUND, Interop namespace could not be
              determined.
        """
        if self._profiles is None:
            self._determine_profiles()
        return self._profiles

    def get_selected_profiles(self, registered_org=None, registered_name=None,
                              registered_version=None):
        """
        List of management profiles advertised by the WBEM server and
        filtered by the input parameters for registered_org, registered_name,
        and registered_version parameters. Each list
        item is a :class:`~pywbem.CIMInstance` object representing a
        CIM_RegisteredProfile instance.

        Parameters:

            profile_org (:term:`string`) or None: the `RegisteredOrganization`
              to match the `RegisteredOrganization` of the profile.
              If None, this parameter is ignored in the filter

            profile_name (:term:`string`) or None: the `RegisteredName`.
              If None, this parameter is ignored in the filter

            profile_version (:term:`string`) or None: the `RegisteredVersion`.
              If None, this parameter is ignored in the filter

        Raises:

            Exceptions raised by :class:`~pywbem.WBEMConnection`.
            CIMError: CIM_ERR_NOT_FOUND, Interop namespace could not be
              determined.
            KeyError: If an instance in the list of profiles is incomplete
              and does not include the required properties.
        """

        org_vm = ValueMapping.for_property(self, self.interop_ns,
                                           'CIM_RegisteredProfile',
                                           'RegisteredOrganization')
        rtn = []
        for inst in self.profiles:
            inst_org = org_vm.tovalues(inst['RegisteredOrganization'])
            inst_name = inst['RegisteredName']
            inst_version = inst['RegisteredVersion']

            # pylint: disable=too-many-boolean-expressions
            if (registered_org is None or registered_org == inst_org) and \
                    (registered_name is None or registered_name == inst_name) \
                    and \
                    (registered_version is None or
                     registered_version == inst_version):
                rtn.append(inst)
        return rtn

    def get_central_instances(self, profile_path, central_class=None,
                              scoping_class=None, scoping_path=None):
        """
        Determine the central instances for a management profile, and return
        their instance paths as a list of :class:`~pywbem.CIMInstanceName`
        objects.

        This method supports the following profile advertisement methodologies
        (see :term:`DSP1033`), and attempts them in this order:

        * GetCentralInstances methodology (new in :term:`DSP1033` 1.1)
        * Central class methodology
        * Scoping class methodology

        Use of the scoping class methodology requires specifying the central
        class, scoping class and scoping path defined by the profile. If any
        of them is `None`, this method will attempt only the GetCentralInstances
        and central class methodologies, but not the scoping class methodology.
        If using these two methodologies does not result in any central
        instances, and the scoping class methodology cannot be used, an
        exception is raised.

        The scoping path is a directed traversal path from the central
        instances to the scoping instances. Its first list item is always
        the association class name of the traversal hop starting at the
        central instances. For each further traversal hop, the list contains
        two more items: The class name of the near end of that hop, and
        the class name of the traversed association.
        As a result, the class names of the central instances and scoping
        instances are not part of the list.

        Example for a 1-hop traversal:

        * central class: ``"CIM_Fan"``
        * scoping path: ``["CIM_SystemDevice"]``
        * scoping class: ``"CIM_ComputerSystem"``

        Example for a 2-hop traversal:

        * central class: ``"CIM_Sensor"``
        * scoping path: ``["CIM_AssociatedSensor", "CIM_Fan", \
                           "CIM_SystemDevice"]``
        * scoping class: ``"CIM_ComputerSystem"``

        Parameters:

          profile_path (:class:`~pywbem.CIMInstanceName`):
            Instance path of CIM_RegisteredProfile instance representing the
            management profile.

          central_class (:term:`string`):
            Class name of central class defined by the management profile.

            Will be ignored, unless the profile is a component profile and its
            implementation supports only the scoping class methodology.
            `None` will cause the scoping class methodology not to be attempted.

          scoping_class (:term:`string`):
            Class name of scoping class defined by the management profile.

            Will be ignored, unless the profile is a component profile and its
            implementation supports only the scoping class methodology.
            `None` will cause the scoping class methodology not to be attempted.

          scoping_path (list of :term:`string`):
            Scoping path defined by the management profile.

            Will be ignored, unless the profile is a component profile and its
            implementation supports only the scoping class methodology.
            `None` will cause the scoping class methodology not to be attempted.

        Returns:

          List of :class:`~pywbem.CIMInstanceName` objects representing the
          instance paths of the central instances of the management profile.

        Raises:

            Exceptions raised by :class:`~pywbem.WBEMConnection`.
            ValueError: Various errors in scoping path traversal.
            TypeError: profile_path must be a CIMInstanceName.
        """
        if not isinstance(profile_path, CIMInstanceName):
            raise TypeError("profile_path must be a CIMInstanceName, but is "
                            "a %s" % type(profile_path))

        # Try GetCentralInstances() method:
        try:
            (ret_val, out_params) = self._conn.InvokeMethod(
                MethodName="GetCentralInstances",
                ObjectName=profile_path)
        except CIMError as exc:
            if exc.status_code in (CIM_ERR_METHOD_NOT_AVAILABLE,
                                   CIM_ERR_NOT_SUPPORTED):
                # Method is not implemented.
                # CIM_ERR_NOT_SUPPORTED is not an official status code for this
                # situation, but is used by some implementations.
                pass  # try next approach
            else:
                raise
        else:
            if ret_val != 0:
                raise ValueError("GetCentralInstances() implemented but "
                                 "failed with rc=%s" % ret_val)
            return out_params['CentralInstances']

        # Try central methodology
        ci_paths = self._conn.AssociatorNames(
            ObjectName=profile_path,
            AssocClass="CIM_ElementConformsToProfile",
            ResultRole="ManagedElement")
        if len(ci_paths) > 0:
            return ci_paths

        # Try scoping methodology
        if central_class is None or \
           scoping_class is None or \
           scoping_path is None:
            raise ValueError("No central instances found after applying "
                             "GetCentralInstances and central class "
                             "methodologies, and parameters for scoping "
                             "class methodology were not specified")

        # Go up one level on the profile side
        referencing_profile_paths = self._conn.AssociatorNames(
            ObjectName=profile_path,
            AssocClass="CIM_ReferencedProfile",
            ResultRole="Dependent")
        if len(referencing_profile_paths) == 0:
            raise ValueError("No referencing profile found")
        elif len(referencing_profile_paths) > 1:
            raise ValueError("More than one referencing profile found")

        # Traverse to the resource side (remember that scoping instances are
        # the central instances at the next upper level).
        # Do this recursively, if needed.
        if len(scoping_path) >= 3:
            upper_central_class = scoping_path[1]
            upper_scoping_path = scoping_path[2:-1]
        else:
            upper_central_class = None
            upper_scoping_path = None
        scoping_inst_paths = self.get_central_instances(
            referencing_profile_paths[0],
            upper_central_class, scoping_class, upper_scoping_path)
        if len(scoping_inst_paths) == 0:
            raise ValueError("No scoping instances found")

        # Go down one level on the resource side (using the last
        # entry in the scoping path as the association to traverse)
        total_ci_paths = []
        assoc_class = scoping_path[-1]
        for ip in scoping_inst_paths:
            ci_paths = self._conn.AssociatorNames(
                ObjectName=ip,
                AssocClass=assoc_class,
                ResultClass=central_class)
            if len(ci_paths) == 0:
                # At least one central instance for each scoping instance
                raise ValueError("No central instances found traversing down "
                                 "across %s to %s" %
                                 (assoc_class, central_class))
            total_ci_paths.extend(ci_paths)

        return total_ci_paths

    def _determine_interop_ns(self):
        """
        Determine the name of the Interop namespace of the WBEM server, by
        trying to communicate with it on a number of possible Interop
        namespace names, that are defined in the :attr:`INTEROP_NAMESPACES`
        class variable.

        If the Interop namespace could be determined, this method sets the
        :attr:`interop_ns` property of this object to that namespace and
        returns.
        Otherwise, it raises an exception.

        Raises:

            Exceptions raised by :class:`~pywbem.WBEMConnection`.
            CIMError: CIM_ERR_NOT_FOUND, Interop namespace could not be
              determined.
        """
        test_classname = 'CIM_Namespace'
        interop_ns = None
        for ns in self.INTEROP_NAMESPACES:
            try:
                inst_paths = self._conn.EnumerateInstanceNames(test_classname,
                                                               namespace=ns)
            except CIMError as exc:
                if exc.status_code == CIM_ERR_INVALID_NAMESPACE:
                    # Current namespace does not exist.
                    continue
                elif exc.status_code in (CIM_ERR_INVALID_CLASS,
                                         CIM_ERR_NOT_FOUND):
                    # Class is not implemented, but current namespace exists.
                    interop_ns = ns
                    break
                else:
                    # Some other error happened.
                    raise
            else:
                # Namespace class is implemented in the current namespace.
                # Use the returned namespace name, if possible.
                ns_names = [p.keybindings['name'] for p in inst_paths]
                ns_dict = NocaseDict(list(zip(ns_names, ns_names)))
                try:
                    interop_ns = ns_dict[ns]
                except KeyError:
                    interop_ns = ns
                break
        if interop_ns is None:
            # Exhausted the possible namespaces
            raise CIMError(CIM_ERR_NOT_FOUND,
                           "Interop namespace could not be determined "
                           "(tried %s)" % self.INTEROP_NAMESPACES)
        self._interop_ns = interop_ns

    def _validate_interop_ns(self, interop_ns):
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
        except CIMError as exc:
            # We tolerate it if the WBEM server does not implement this class,
            # as long as it does not return CIM_ERR_INVALID_NAMESPACE.
            if exc.status_code in (CIM_ERR_INVALID_CLASS,
                                   CIM_ERR_NOT_FOUND):
                pass
            else:
                raise
        self._interop_ns = interop_ns

    def _determine_namespaces(self):
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
            CIMError: CIM_ERR_NOT_FOUND, Interop namespace could not be
              determined.
            CIMError: CIM_ERR_NOT_FOUND, Namespace class could not be
              determined.
        """
        ns_insts = None
        ns_classname = None
        for classname in self.NAMESPACE_CLASSNAMES:
            try:
                ns_insts = self._conn.EnumerateInstances(
                    classname, namespace=self.interop_ns)
            except CIMError as exc:
                if exc.status_code in (CIM_ERR_INVALID_CLASS,
                                       CIM_ERR_NOT_FOUND):
                    # Class is not implemented, try next one.
                    continue
                else:
                    # Some other error.
                    raise
            else:
                # Found a namespace class that is implemented.
                ns_classname = classname
                break
        if ns_insts is None:
            # Exhausted the possible class names
            raise CIMError(CIM_ERR_NOT_FOUND,
                           "Namespace class could not be determined "
                           "(tried %s)" % self.NAMESPACE_CLASSNAMES)
        self._namespace_classname = ns_classname
        self._namespaces = [inst['Name'] for inst in ns_insts]

    def _determine_brand(self):
        """
        Determine the brand of the WBEM server (e.g. OpenPegasus, SFCB, ...)
        and its version, by communicating with it and retrieving the
        CIM_ObjectManager instance.

        On success, this method sets the :attr:`brand` and :attr:`version`
        properties of this object and returns.
        Otherwise, it raises an exception.

        Raises:

            Exceptions raised by :class:`~pywbem.WBEMConnection`.
            CIMError: CIM_ERR_NOT_FOUND, Interop namespace could not be
              determined.
            CIMError: CIM_ERR_NOT_FOUND, Unexpected number of
              CIM_ObjectManager instances.
        """
        cimom_insts = self._conn.EnumerateInstances(
            "CIM_ObjectManager", namespace=self.interop_ns)
        if len(cimom_insts) != 1:
            raise CIMError(CIM_ERR_NOT_FOUND,
                           "Unexpected number of CIM_ObjectManager "
                           "instances: %s " %
                           [i['ElementName'] for i in cimom_insts])
        cimom_inst = cimom_insts[0]
        element_name = cimom_inst['ElementName']
        if element_name is not None:
            element_word = element_name.split(' ')[0]
        else:
            element_word = "unknown"
        if element_word in ("Pegasus", "OpenPegasus"):
            brand = 'OpenPegasus'
            # Description = "Pegasus OpenPegasus Version 2.12.0"
            m = re.match(r'.+ *Version *([^ ]+)', cimom_inst['Description'])
            if m:
                version = m.group(1)
            else:
                version = None
        elif element_word == "SFCB":
            brand = 'SFCB'
            # TODO: Figure out how to get version of SFCB
            version = None
        else:
            brand = element_word
            version = None
        self._brand = brand
        self._version = version

    def _determine_profiles(self):
        """
        Determine the WBEM management profiles advertised by the WBEM server,
        by communicating with it and enumerating the instances of
        CIM_RegisteredProfile.

        If the profiles could be determined, this method sets the
        :attr:`profiles` property of this object to the list of
        CIM_RegisteredProfile instances (as :class:`~pywbem.CIMInstance`
        objects), and returns.
        Otherwise, it raises an exception.

        Raises:

            Exceptions raised by :class:`~pywbem.WBEMConnection`.
            CIMError: CIM_ERR_NOT_FOUND, Interop namespace could not be
              determined.
        """
        mp_insts = self._conn.EnumerateInstances("CIM_RegisteredProfile",
                                                 namespace=self.interop_ns)
        self._profiles = mp_insts


class ValueMapping(object):
    """
    A utility class that translates the values of a corresponding integer-typed
    CIM element (property, method, parameter) that is qualified with the
    ValueMap and Values qualifiers, from the element value space into into its
    Values qualifier space.

    This is done by retrieving the CIM class definition defining the CIM
    element in question, and by inspecting its ValueMap and Values qualifiers.

    The actual translation of the values is performed by the
    :meth:`~pywbem.ValueMapping.tovalues` method.

    Instances of this class should be created through one of the factory class
    methods: :meth:`~pywbem.ValueMapping.for_property`,
    :meth:`~pywbem.ValueMapping.for_method`, or
    :meth:`~pywbem.ValueMapping.for_parameter`.

    Value ranges (``"2..4"``) and the indicator for unclaimed values (``".."``)
    in the ValueMap qualifier are supported.

    Example: Given the following definition of a property in MOF:

    ::

        [ValueMap{ "0", "2..4", "..6", "7..", "9", ".." },
         Values{ "zero", "two-four", "five-six", "seven-eight", "nine", \
             "unclaimed"}]
        uint16 MyProp;

    The following code will create a value mapping for this property and will
    print a few integer values and their Values strings:

    ::

        vm = pywbem.ValueMapping.for_property(server, namespace, classname,\
                "MyProp")
        for value in range(0, 12):
            print("value: %s, Values string: %r" % (value, vm.tovalues(value))

        Results:
        value: 0, Values string: 'zero'
        value: 1, Values string: 'unclaimed'
        value: 2, Values string: 'two-four'
        value: 3, Values string: 'two-four'
        value: 4, Values string: 'two-four'
        value: 5, Values string: 'five-six'
        value: 6, Values string: 'five-six'
        value: 7, Values string: 'seven-eight'
        value: 8, Values string: 'seven-eight'
        value: 9, Values string: 'nine'
        value: 10, Values string: 'unclaimed'
        value: 11, Values string: 'unclaimed'
    """

    def __init__(self):
        self._element_obj = None
        self._single_dict = {}  # for single values; elem_val: values_str)
        self._range_tuple_list = []  # for value ranges; tuple(lo,hi,values_str)
        self._unclaimed = None  # value of the unclaimed indicator '..'

    @classmethod
    def for_property(cls, server, namespace, classname, propname):
        """
        Factory method that returns a new :class:`~pywbem.ValueMapping`
        instance corresponding to a CIM property.

        If a Values qualifier is defined but no ValueMap qualifier, a default
        of 0-based consecutive numbers is applied (that is the default defined
        in :term:`DSP0004`).

        Parameters:

          server (:class:`~pywbem.WBEMServer`):
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

            The new :class:`~pywbem.ValueMapping` instance.

        Raises:

            Exceptions raised by :class:`~pywbem.WBEMConnection`.
            ValueError: No Values qualifier defined.
            TypeError: The property is not integer-typed.
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
        Factory method that returns a new :class:`~pywbem.ValueMapping`
        instance corresponding to a CIM method.

        If a Values qualifier is defined but no ValueMap qualifier, a default
        of 0-based consecutive numbers is applied (that is the default defined
        in :term:`DSP0004`).

        Parameters:

          server (:class:`~pywbem.WBEMServer`):
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

            The new :class:`~pywbem.ValueMapping` instance.

        Raises:

            Exceptions raised by :class:`~pywbem.WBEMConnection`.
            ValueError: No Values qualifier defined.
            TypeError: The method is not integer-typed.
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
        Factory method that returns a new :class:`~pywbem.ValueMapping`
        instance corresponding to a CIM parameter.

        If a Values qualifier is defined but no ValueMap qualifier, a default
        of 0-based consecutive numbers is applied (that is the default defined
        in :term:`DSP0004`).

        Parameters:

          server (:class:`~pywbem.WBEMServer`):
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

            The new :class:`~pywbem.ValueMapping` instance.

        Raises:

            Exceptions raised by :class:`~pywbem.WBEMConnection`.
            ValueError: No Values qualifier defined.
            TypeError: The parameter is not integer-typed.
        """
        class_obj = server.conn.GetClass(ClassName=classname,
                                         namespace=namespace,
                                         LocalOnly=False,
                                         IncludeQualifiers=True)
        method_obj = class_obj.methods[methodname]
        parameter_obj = method_obj.parameters[parametername]
        return cls._create_for_element(parameter_obj)

    @classmethod
    def _values_tuple(cls, i, valuemap_list, values_list, cimtype):
        """
        Return a tuple for the value range at position i, with these items:

        * lo - low value of the range
        * hi - high value of the range (can be equal to lo)
        * values - Value of Values qualifier for this position

        Parameters:

          i (integer): position into valuemap_list and values_list

          valuemap_list (list of strings): ValueMap qualifier value

          values_list (list of strings): Values qualifier value

          cimtype (type): CIM type of the CIM element

        Raises:

            ValueError: Invalid ValueMap entry.
        """
        values_str = values_list[i]
        valuemap_str = valuemap_list[i]
        try:
            valuemap_int = int(valuemap_str)
            return (valuemap_int, valuemap_int, values_str)
        except ValueError:
            m = re.match(r'^([0-9]*)\.\.([0-9]*)$', valuemap_str)
            if m is None:
                raise ValueError("Invalid ValueMap entry: %r" % valuemap_str)
            lo = m.group(1)
            if lo == '':
                if i == 0:
                    lo = 0
                    # TODO: Change to min(cimtype) once issue #268 is solved.
                else:
                    _, previous_hi, _ = cls._values_tuple(
                        i - 1, valuemap_list, values_list, cimtype)
                    lo = previous_hi + 1
            else:
                lo = int(lo)
            hi = m.group(2)
            if hi == '':
                if i == len(valuemap_list) - 1:
                    hi = 32767
                    # TODO: Change to max(cimtype) once issue #268 is solved.
                else:
                    next_lo, _, _ = cls._values_tuple(
                        i + 1, valuemap_list, values_list, cimtype)
                    hi = next_lo - 1
            else:
                hi = int(hi)
            return (lo, hi, values_str)

    @classmethod
    def _create_for_element(cls, element_obj):
        # pylint: disable=line-too-long
        """
        Return a new :class:`~pywbem.ValueMapping` instance for the specified
        CIM element.

        If a Values qualifier is defined but no ValueMap qualifier, a default
        of 0-based consecutive numbers is applied (that is the default defined
        in :term:`DSP0004`).

        Parameters:

          element_obj (:class:`~pywbem.CIMProperty`, :class:`~pywbem.CIMMethod`, or :class:`~pywbem.CIMParameter`):
            The CIM element on which the qualifiers are defined.

        Returns:

            The created :class:`~pywbem.ValueMapping` instance for the specified
            CIM element.

        Raises:

            ValueError: No Values qualifier defined.
            ValueError: Invalid ValueMap entry.
            TypeError: The CIM element is not integer-typed.
        """  # noqa: E501

        # pylint: disable=protected-access

        typename = element_obj.type
        # TODO: We should make type_from_name() and cimtype() part of the API
        cimtype = type_from_name(typename)

        if not issubclass(cimtype, CIMInt):
            raise TypeError("The CIM element is not integer-typed: %s" %
                            typename)

        vm = ValueMapping()
        vm._element_obj = element_obj

        values_qual = element_obj.qualifiers.get('Values', None)
        if values_qual is None:
            # DSP0004 defines no default for a missing Values qualifier
            raise ValueError("No Values qualifier defined")
        values_list = values_qual.value

        valuemap_qual = element_obj.qualifiers.get('ValueMap', None)
        if valuemap_qual is None:
            # DSP0004 defines a default of consecutive index numbers
            vm._single_dict = dict(zip(range(0, len(values_list)), values_list))
            vm._range_tuple_list = []
            vm._unclaimed = None
        else:
            vm._single_dict = {}
            vm._range_tuple_list = []
            vm._unclaimed = None
            valuemap_list = valuemap_qual.value
            for i, valuemap_str in enumerate(valuemap_list):
                values_str = values_list[i]
                if valuemap_str == '..':
                    vm._unclaimed = values_str
                else:
                    lo, hi, values_str = cls._values_tuple(
                        i, valuemap_list, values_list, cimtype)
                    if lo == hi:
                        # single value
                        vm._single_dict[lo] = values_str
                    else:
                        # value range
                        vm._range_tuple_list.append((lo, hi, values_str))

        return vm

    @property
    def element(self):
        """
        Return the corresponding CIM element of this instance, as a CIM object
        (:class:`~pywbem.CIMProperty`, :class:`~pywbem.CIMMethod`, or
        :class:`~pywbem.CIMParameter`).
        """
        return self._element_obj

    def tovalues(self, element_value):
        """
        Return the Values string for an element value, based on the ValueMap /
        Values qualifiers of the corresponding CIM element.

        Parameters:

          element_value (:term:`integer` or :class:`~pywbem.CIMInt`):
            The value of the CIM element.

        Returns:

          :term:`string`:
            The Values string for the element value.

        Raises:

            ValueError: Element value outside of the set defined by ValueMap.
            ValueError: No Values qualifier defined.
            ValueError: Invalid ValueMap entry.
            TypeError: The CIM element is not integer-typed.
            TypeError: Element value is not an integer type.
        """

        if not isinstance(element_value, (six.integer_types, CIMInt)):
            raise TypeError("Element value is not an integer type: %s" %
                            type(element_value))

        # try single value
        try:
            return self._single_dict[element_value]
        except KeyError:
            pass

        # try value ranges
        for range_tuple in self._range_tuple_list:
            lo, hi, values_str = range_tuple
            if lo <= element_value <= hi:
                return values_str

        # try catch-all '..'
        if self._unclaimed is not None:
            return self._unclaimed

        raise ValueError("Element value outside of the set defined by "
                         "ValueMap: %r" % element_value)
