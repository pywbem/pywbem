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

The WBEM server API encapsulates certain functionality of a WBEM server for use
by a WBEM client application, such as determining the Interop namespace of the
server, or the management profiles advertised by the server.

This chapter has the following sections:

* :ref:`Example <Server Example>` - An example on how to use the API.

* :ref:`WBEMServer` - The :class:`~pywbem.WBEMServer` class serves as a general
  access point for clients to WBEM servers. It allows determining the Interop
  namespace of the server, or the advertised management profiles.

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
      OpenPegasus
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

from .cim_constants import CIM_ERR_INVALID_NAMESPACE, CIM_ERR_INVALID_CLASS, \
    CIM_ERR_METHOD_NOT_FOUND, CIM_ERR_METHOD_NOT_AVAILABLE, \
    CIM_ERR_NOT_SUPPORTED, CIM_ERR_NOT_FOUND
from .exceptions import CIMError
from .cim_obj import CIMInstanceName, NocaseDict
from .cim_operations import WBEMConnection
from ._valuemapping import ValueMapping

__all__ = ['WBEMServer']


class WBEMServer(object):
    """
    *New in pywbem 0.9 as experimental and finalized in 0.10.*

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
        :term:`string`: URL of the WBEM server.
        """
        return self._conn.url

    @property
    def conn(self):
        """
        :class:`~pywbem.WBEMConnection`: Connection to the WBEM server.
        """
        return self._conn

    @property
    def interop_ns(self):
        """
        :term:`string`: Name of the Interop namespace of the WBEM server.

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
        :term:`string`: Name of the CIM class that was found to represent the
        CIM namespaces of the WBEM server.

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
        :class:`py:list` of :term:`string`: Names of all namespaces of the
        WBEM server.

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
        :term:`string`: Brand of the WBEM server.

        The brand will be one of the following:

        * ``"OpenPegasus"``, for OpenPegasus
        * ``"SFCB"``, for SFCB
        * First word of the value of the `ElementName` property of the
          `CIM_ObjectManager` instance, for any other WBEM servers.
        * ``"unknown"``, if the `ElementName` property is NULL.

        Raises:

            Exceptions raised by :class:`~pywbem.WBEMConnection`.
            CIMError: CIM_ERR_NOT_FOUND, Interop namespace could not be
              determined.
            CIMError: CIM_ERR_NOT_FOUND, Unexpected number of
              `CIM_ObjectManager` instances.
        """
        if self._brand is None:
            self._determine_brand()
        return self._brand

    @property
    def version(self):
        """
        :term:`string`: Version of the WBEM server. `None`, if the version
        cannot be determined.

        Raises:

            Exceptions raised by :class:`~pywbem.WBEMConnection`.
            CIMError: CIM_ERR_NOT_FOUND, Interop namespace could not be
              determined.
            CIMError: CIM_ERR_NOT_FOUND, Unexpected number of
              `CIM_ObjectManager` instances.
        """
        if self._version is None:
            self._determine_brand()
        return self._version

    @property
    def profiles(self):
        """
        :class:`py:list` of :class:`~pywbem.CIMInstance`: The
        `CIM_RegisteredProfile` instances representing all management profiles
        advertised by the WBEM server.

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
        Return the `CIM_RegisteredProfile` instances representing a filtered
        subset of the management profiles advertised by the WBEM server, that
        can be filtered by registered organization, registered name, and/or
        registered version.

        Parameters:

            profile_org (:term:`string`): A filter for the registered
              organization of the profile, matching (case sensitively) the
              `RegisteredOrganization` property of the `CIM_RegisteredProfile`
              instance, via its `Values` qualifier.
              If `None`, this parameter is ignored for filtering.

            profile_name (:term:`string`): A filter for the registered name of
              the profile, matching (case sensitively) the `RegisteredName`
              property of the `CIM_RegisteredProfile` instance.
              If `None`, this parameter is ignored for filtering.

            profile_version (:term:`string`): A filter for the registered
              version of the profile, matching (case sensitively) the
              `RegisteredVersion` property of the `CIM_RegisteredProfile`
              instance.
              If `None`, this parameter is ignored for filtering.

        Returns:

          :class:`py:list` of :class:`~pywbem.CIMInstance`: The
          `CIM_RegisteredProfile` instances representing the filtered
          subset of the management profiles advertised by the WBEM server.

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
        # pylint: disable=line-too-long
        """
        Return the instance paths of the central instances of a management
        profile.

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
        * scoping path: ``["CIM_AssociatedSensor", "CIM_Fan", "CIM_SystemDevice"]``
        * scoping class: ``"CIM_ComputerSystem"``

        Parameters:

          profile_path (:class:`~pywbem.CIMInstanceName`):
            Instance path of the `CIM_RegisteredProfile` instance representing
            the management profile.

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

          :class:`py:list` of :class:`~pywbem.CIMInstanceName`: The instance
          paths of the central instances of the management profile.

        Raises:

            Exceptions raised by :class:`~pywbem.WBEMConnection`.
            ValueError: Various errors in scoping path traversal.
            TypeError: `profile_path` must be a
              :class:`~pywbem.CIMInstanceName`.
        """  # noqa: E501
        # pylint: enable=line-too-long
        if not isinstance(profile_path, CIMInstanceName):
            raise TypeError("profile_path must be a CIMInstanceName, but is "
                            "a %s" % type(profile_path))

        # Try GetCentralInstances() method:
        try:
            (ret_val, out_params) = self._conn.InvokeMethod(
                MethodName="GetCentralInstances",
                ObjectName=profile_path)
        except CIMError as exc:
            if exc.status_code in (CIM_ERR_METHOD_NOT_FOUND,
                                   CIM_ERR_METHOD_NOT_AVAILABLE,
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
        if ci_paths:
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
        if not referencing_profile_paths:
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
        if not scoping_inst_paths:
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
            if not ci_paths:
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
        `CIM_ObjectManager` instance.

        On success, this method sets the :attr:`brand` and :attr:`version`
        properties of this object and returns.
        Otherwise, it raises an exception.

        Raises:

            Exceptions raised by :class:`~pywbem.WBEMConnection`.
            CIMError: CIM_ERR_NOT_FOUND, Interop namespace could not be
              determined.
            CIMError: CIM_ERR_NOT_FOUND, Unexpected number of
              `CIM_ObjectManager` instances.
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
        `CIM_RegisteredProfile`.

        If the profiles could be determined, this method sets the
        :attr:`profiles` property of this object to the list of
        `CIM_RegisteredProfile` instances (as :class:`~pywbem.CIMInstance`
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
