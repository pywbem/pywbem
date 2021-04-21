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

The WBEM server library API of pywbem encapsulates selected functionality of a
WBEM server for use by a WBEM client application, such as determining the
Interop namespace and other basic information about the server, or the
management profiles advertised by the server.

This chapter has the following sections:

* :ref:`Example <Server Example>` - An example on how to use the WBEM server
  library API.

* :ref:`WBEMServer` - The :class:`~pywbem.WBEMServer` class serves as a general
  access point for clients to WBEM servers. It allows determining the Interop
  namespace of the server and other basic information about the server, or the
  advertised management profiles.

.. _`Server Example`:

Example
-------

The following example code displays some information about a WBEM server:

::

    from pywbem import WBEMConnection, WBEMServer, ValueMapping

    def explore_server(server_url, username, password):

        print("WBEM server URL:\\n  {0}".format(server_url))

        conn = WBEMConnection(server_url, (username, password))
        server = WBEMServer(conn)

        print("Brand:\\n  {0}".format(server.brand))
        print("Version:\\n  {0}".format(server.version))
        print("Interop namespace:\\n  {0}".format(server.interop_ns))

        print("All namespaces:")
        for ns in server.namespaces:
            print("  {0}".format(ns))

        print("Advertised management profiles:")
        org_vm = ValueMapping.for_property(server, server.interop_ns,
            'CIM_RegisteredProfile', 'RegisteredOrganization')
        for inst in server.profiles:
            org = org_vm.tovalues(inst['RegisteredOrganization'])
            name = inst['RegisteredName']
            vers = inst['RegisteredVersion']
            print("  {0} {1} Profile {2}".format(org, name, vers))

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
import warnings

from ._cim_constants import CIM_ERR_INVALID_NAMESPACE, CIM_ERR_INVALID_CLASS, \
    CIM_ERR_METHOD_NOT_FOUND, CIM_ERR_METHOD_NOT_AVAILABLE, \
    CIM_ERR_NOT_SUPPORTED, CIM_ERR_NOT_FOUND, CIM_ERR_FAILED, \
    CIM_ERR_NAMESPACE_NOT_EMPTY
from ._exceptions import CIMError, CIMXMLParseError, XMLParseError, ModelError
from ._warnings import ToleratedServerIssueWarning
from ._nocasedict import NocaseDict
from ._cim_obj import CIMInstanceName, CIMInstance
from ._cim_operations import WBEMConnection
from ._valuemapping import ValueMapping
from ._utils import _ensure_unicode, _format

__all__ = ['WBEMServer']


class WBEMServer(object):
    """
    *New in pywbem 0.9 as experimental and finalized in 0.10.*

    A representation of a WBEM server that serves as a general access point to
    a client.

    It supports determining the Interop namespace of the server, all namespaces,
    its brand and version, the advertised management profiles and finally
    allows retrieving the central instances of an implementation of a
    management profile with one method invocation regardless of whether the
    profile implementation chose to implement the central or scoping class
    profile advertisement methodology (see section
    :ref:`Profile advertisement methodologies`).

    It also provides functions to subscribe for indications.
    """

    #: A class variable with the possible names of Interop namespaces that
    #: should be tried when determining the Interop namespace on the WBEM
    #: server.
    INTEROP_NAMESPACES = [
        'interop',
        'root/interop',
        'root/PG_Interop',
        # OpenPegasus before version 2.12.0 defined only PG_Interop as the
        # interop namespace. Using other namespaces was a manual
        # modification of at least the pegasus/mak/configschema.mak file.
        # Starting in version 2.12.0 a configuration variable was defined
        # so that OpenPegasus could be build with any of the specified names
        # for interop namespace (PEGASUS_INTEROP_NAMESPACE)
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
            raise TypeError(
                _format("conn argument of WBEMServer must be a WBEMConnection "
                        "object, but has type: {0}", type(conn)))
        self._conn = conn
        self._interop_ns = None
        self._namespaces = None
        self._namespace_paths = None
        self._namespace_classname = None
        self._brand = None
        self._version = None
        self._cimom_inst = None
        self._profiles = None

    def __str__(self):
        """
        Return a representation of the :class:`~pywbem.WBEMServer` object
        with a subset of its attributes.
        """
        return _format(
            "WBEMServer("
            "conn.url={s._conn.url!A}, "
            "brand={s._brand!A}, "
            "version={s._version!A}, "
            "... )",
            s=self)

    def __repr__(self):
        """
        Return a representation of the :class:`~pywbem.WBEMServer` object
        with all attributes, that is suitable for debugging.
        """
        return _format(
            "WBEMServer("
            "conn.url={s._conn.url!A}, "
            "interop_ns={s._interop_ns!A}, "
            "namespaces={s._namespaces!A}, "
            "namespace_paths={s._namespace_paths!A}, "
            "namespace_classname={s._namespace_classname!A}, "
            "brand={s._brand!A}, "
            "version={s._version!A}, "
            "profiles=[{pnum} instances])",
            s=self,
            pnum=len(self._profiles) if self._profiles else 0)

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
            ModelError: An error with the model implemented by the WBEM server.
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
            ModelError: An error with the model implemented by the WBEM server.
        """
        if self._namespaces is None:
            self._determine_namespaces()
        return self._namespaces

    @property
    def namespace_paths(self):
        """
        :class:`py:list` of :class:`~pywbem.CIMInstanceName`: Instance paths
        of the CIM instances in the Interop namespace that represent the
        namespaces of the WBEM server.

        Note: One WBEM server has been found to support an Interop namespace
        without representing it as a CIM instance. In that case, this property
        will not have an instance path for the Interop namespace, but the
        :attr:`namespaces` property will have the name of the Interop
        namespace.

        Raises:

            Exceptions raised by :class:`~pywbem.WBEMConnection`.
            ModelError: An error with the model implemented by the WBEM server.
        """
        if self._namespace_paths is None:
            self._determine_namespaces()
        return self._namespace_paths

    @property
    def brand(self):
        """
        :term:`string`: Brand of the WBEM server.

        The brand is determined from the `CIM_ObjectManager` instance in
        the Interop namespace, by looking at its `ElementName` property.

        For known WBEM servers, the brand is then normalized in order to make
        it identifiable:

        * ``"OpenPegasus"``
        * ``"SFCB"`` (Small Footprint CIM Broker)
        * ``"WBEM Solutions J WBEM Server"``
        * ``"EMC CIM Server"``
        * ``"FUJITSU CIM Object Manager"``

        For all other WBEM servers, the brand is the value of the
        `ElementName` property, or the string ``"unknown"``, if that
        property is not set or the empty string.

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
        :term:`string`: Version of the WBEM server.

        `None`, if the version cannot be determined.

        The version is determined from the `CIM_ObjectManager` instance in
        the Interop namespace, by looking at its `ElementName` property, or if
        that is not set, at its `Description` property, and by taking the
        string after ``"version"`` or ``"release"`` (case insensitively).

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
    def cimom_inst(self):
        """
        :class:`~pywbem.CIMInstance`: CIM instance of class `CIM_ObjectManager`
        that represents the WBEM server.

        Raises:

            Exceptions raised by :class:`~pywbem.WBEMConnection`.
            CIMError: CIM_ERR_NOT_FOUND, Interop namespace could not be
              determined.
            CIMError: CIM_ERR_NOT_FOUND, Unexpected number of
              `CIM_ObjectManager` instances.
        """
        if self._cimom_inst is None:
            self._determine_brand()
        return self._cimom_inst

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

    def create_namespace(self, namespace):
        """
        Create the specified CIM namespace in the WBEM server and
        update this WBEMServer object to reflect the new namespace
        there.

        This method cannot create an Interop namespace because creating the
        an Interop namespace with client operations depends on the prior
        existence of an Interop namespace, and creating additional Interop
        namespaces if one already exists is usually prevented by servers.

        This method attempts the following approaches for creating the
        namespace, in order, until an approach succeeds:

        1. Namespace creation as described in the WBEM Server profile
           (:term:`DSP1092`) via CIM method
           `CIM_WBEMServer.CreateWBEMServerNamespace()`.

           This is a new standard approach that is not likely to be
           widely implemented yet.

        2. Issuing the `CreateInstance` operation using the CIM class
           representing namespaces ('PG_Namespace' for OpenPegasus,
           and 'CIM_Namespace' otherwise), against the Interop namespace.

           This approach is typically supported in WBEM servers that
           support the creation of CIM namespaces. This approach is
           similar to the approach described in :term:`DSP0200`.

        Creating namespaces using the `__Namespace` pseudo-class has been
        deprecated already in DSP0200 1.1.0 (released in 01/2003), and pywbem
        does not implement that approach.

        Parameters:

            namespace (:term:`string`): CIM namespace name. Must not be `None`.
              The namespace may contain leading and a trailing slash, both of
              which will be ignored.

        Returns:

          :term:`unicode string`: The specified CIM namespace name in its
          standard format (i.e. without leading or trailing slash characters).

        Raises:

            Exceptions raised by :class:`~pywbem.WBEMConnection`.
            ModelError: An error with the model implemented by the WBEM server.
        """

        std_namespace = _ensure_unicode(namespace.strip('/'))

        try:
            ws_profiles = self.get_selected_profiles('DMTF', 'WBEM Server')
        except (CIMError, ModelError):
            ws_profiles = None
        if ws_profiles:

            # Use approach 1: Method defined in WBEM Server profile

            ws_profiles_sorted = sorted(
                ws_profiles, key=lambda prof: prof['RegisteredVersion'])
            ws_profile_inst = ws_profiles_sorted[-1]  # latest version
            ws_insts = self.get_central_instances(ws_profile_inst.path)
            if len(ws_insts) != 1:
                raise ModelError(
                    _format("Unexpected number of central instances of WBEM "
                            "Server profile: {0!A}",
                            [i.path for i in ws_insts]))
            ws_inst = ws_insts[0]

            ns_inst = CIMInstance('CIM_WBEMServerNamespace')
            ns_inst['Name'] = std_namespace

            try:
                (ret_val, out_params) = self._conn.InvokeMethod(
                    MethodName="CreateWBEMServerNamespace",
                    ObjectName=ws_inst.path,
                    Params=[('NamespaceTemplate', ns_inst)])
            except CIMError as exc:
                if exc.status_code in (CIM_ERR_METHOD_NOT_FOUND,
                                       CIM_ERR_METHOD_NOT_AVAILABLE,
                                       CIM_ERR_NOT_SUPPORTED):
                    # Method is not implemented.
                    # CIM_ERR_NOT_SUPPORTED is not an official status code for
                    # this situation, but is used by some implementations.
                    pass  # try next approach
                else:
                    raise
            else:
                if ret_val != 0:
                    raise ModelError(
                        _format("The CreateWBEMServerNamespace() method is "
                                "implemented but failed: {0}",
                                out_params['Errors']))

        else:

            # Use approach 2: CreateInstance of CIM class for namespaces

            # For OpenPegasus, use 'PG_Namespace' class to account for issue
            # when using 'CIM_Namespace'. See OpenPegasus bug 10112:
            # https://bugzilla.openpegasus.org/show_bug.cgi?id=10112
            if self.brand == "OpenPegasus":
                ns_classname = 'PG_Namespace'
            else:
                ns_classname = 'CIM_Namespace'

            ns_inst = CIMInstance(ns_classname)

            # OpenPegasus requires this property to be True, in order to
            # allow schema updates in the namespace.
            if self.brand == "OpenPegasus":
                ns_inst['SchemaUpdatesAllowed'] = True

            ns_inst['Name'] = std_namespace

            # DSP0200 is not clear as to whether just "Name" or all key
            # properties need to be provided. For now, we provide all key
            # properties.
            # OpenPegasus requires all key properties, and it re-creates the
            # 5 key properties besides "Name" so that the returned instance
            # path may differ from the key properties provided.

            ns_inst['CreationClassName'] = ns_classname
            ns_inst['ObjectManagerName'] = self.cimom_inst['Name']
            ns_inst['ObjectManagerCreationClassName'] = \
                self.cimom_inst['CreationClassName']
            ns_inst['SystemName'] = self.cimom_inst['SystemName']
            ns_inst['SystemCreationClassName'] = \
                self.cimom_inst['SystemCreationClassName']

            self.conn.CreateInstance(ns_inst, namespace=self.interop_ns)

        # Refresh the list of namespaces in this object to include the one
        # we just created.
        # Namespace creation is such a rare operation that we can afford
        # the extra namespace determination operations, to make sure we
        # really have the new namespace.
        self._determine_namespaces()

        return std_namespace

    def delete_namespace(self, namespace):
        """
        Delete the specified CIM namespace in the WBEM server and
        update this WBEMServer object to reflect the removed namespace
        there.

        The specified namespace must be empty (i.e. must not contain any
        classes, instances, or qualifier types.

        This method cannot delete the Interop namespace because servers will
        usually prevent their deletion.

        This method attempts the following approaches for deleting the
        namespace, in order, until an approach succeeds:

        1. Issuing the `DeleteInstance` operation using the CIM class
           representing namespaces ('PG_Namespace' for OpenPegasus,
           and 'CIM_Namespace' otherwise), against the Interop namespace.

           This approach is typically supported in WBEM servers that
           support the creation of CIM namespaces. This approach is
           similar to the approach described in :term:`DSP0200`.

        The approach described in the WBEM Server profile (:term:`DSP1092`) via
        deleting the `CIM_WBEMServerNamespace` instance is not implemented
        because that would also delete any classes, instances, and
        qualifier types in the namespace.

        Deleting namespaces using the `__Namespace` pseudo-class has been
        deprecated already in DSP0200 1.1.0 (released in 01/2003), and pywbem
        does not implement that approach.

        Parameters:

            namespace (:term:`string`): CIM namespace name. Must not be `None`.
              The namespace may contain leading and a trailing slash, both of
              which will be ignored.

        Returns:

          :term:`unicode string`: The specified CIM namespace name in its
          standard format (i.e. without leading or trailing slash characters).

        Raises:

            Exceptions raised by :class:`~pywbem.WBEMConnection`.
            ModelError: An error with the model implemented by the WBEM server.
            CIMError: CIM_ERR_NOT_FOUND, Specified namespace does not exist.
            CIMError: CIM_ERR_NAMESPACE_NOT_EMPTY, Specified namespace is not
              empty.
        """

        std_namespace = _ensure_unicode(namespace.strip('/'))

        # Use approach 1: DeleteInstance of CIM class for namespaces

        # Refresh the list of namespaces in this object to make sure
        # it is up to date.
        self._determine_namespaces()

        if std_namespace not in self.namespaces:
            raise CIMError(
                CIM_ERR_NOT_FOUND,
                _format("pywbem detected that the specified namespace does not "
                        "exist: {0!A}",
                        std_namespace),
                conn_id=self.conn.conn_id)

        ns_path = None
        for p in self.namespace_paths:
            if p.keybindings['Name'] == std_namespace:
                ns_path = p
        assert ns_path is not None

        # Ensure the namespace is empty. We do not check for instances, because
        # classes are a prerequisite for instances, so if no classes exist,
        # no instances will exist.
        # WBEM servers that do not support class operations (e.g. SFCB) will
        # raise a CIMError with status CIM_ERR_NOT_SUPPORTED.
        class_paths = self.conn.EnumerateClassNames(
            namespace=std_namespace, ClassName=None, DeepInheritance=False)
        quals = self.conn.EnumerateQualifiers(namespace=std_namespace)
        if class_paths or quals:
            raise CIMError(
                CIM_ERR_NAMESPACE_NOT_EMPTY,
                _format("pywbem detected that the specified namespace {0!A} "
                        "is not empty; it contains "
                        "{1} top-level classes and {2} qualifier types",
                        std_namespace, len(class_paths), len(quals)),
                conn_id=self.conn.conn_id)

        self.conn.DeleteInstance(ns_path)

        # Refresh the list of namespaces in this object to remove the one
        # we just deleted.
        self._determine_namespaces()

        return std_namespace

    def get_selected_profiles(self, registered_org=None, registered_name=None,
                              registered_version=None):
        """
        Return the `CIM_RegisteredProfile` instances representing a filtered
        subset of the management profiles advertised by the WBEM server, that
        can be filtered by registered organization, registered name, and/or
        registered version.

        Parameters:

            registered_org (:term:`string`): A filter for the registered
              organization of the profile, matching (case insensitively) the
              `RegisteredOrganization` property of the `CIM_RegisteredProfile`
              instance, via its `Values` qualifier.
              If `None`, this parameter is ignored for filtering.

            registered_name (:term:`string`): A filter for the registered name
              of the profile, matching (case insensitively) the
              `RegisteredName` property of the `CIM_RegisteredProfile`
              instance.
              If `None`, this parameter is ignored for filtering.

            registered_version (:term:`string`): A filter for the registered
              version of the profile, matching (case insensitively) the
              `RegisteredVersion` property of the `CIM_RegisteredProfile`
              instance. Note that version strings may contain aplhabetic
              characters to indicate the draft level.
              If `None`, this parameter is ignored for filtering.

        Returns:

          :class:`py:list` of :class:`~pywbem.CIMInstance`: The
          `CIM_RegisteredProfile` instances representing the filtered
          subset of the management profiles advertised by the WBEM server.

        Raises:

            Exceptions raised by :class:`~pywbem.WBEMConnection`.
            CIMError: CIM_ERR_NOT_FOUND, Interop namespace could not be
              determined.
            ModelError: If an instance in the list of profiles is incomplete
              and does not include the required properties.
        """

        org_vm = ValueMapping.for_property(self, self.interop_ns,
                                           'CIM_RegisteredProfile',
                                           'RegisteredOrganization')
        org_lower = registered_org.lower() \
            if registered_org is not None else None
        name_lower = registered_name.lower() \
            if registered_name is not None else None
        version_lower = registered_version.lower() \
            if registered_version is not None else None

        rtn = []
        for inst in self.profiles:
            try:
                inst_org_value = inst['RegisteredOrganization']
            except KeyError:
                raise ModelError(
                    _format("CIM_RegisteredProfile instance in namespace "
                            "{0!A} does not have a property "
                            "'RegisteredOrganization'",
                            self.interop_ns))
            inst_org = org_vm.tovalues(inst_org_value)
            try:
                inst_name = inst['RegisteredName']
            except KeyError:
                raise ModelError(
                    _format("CIM_RegisteredProfile instance in namespace "
                            "{0!A} does not have a property "
                            "'RegisteredName'",
                            self.interop_ns))
            try:
                inst_version = inst['RegisteredVersion']
            except KeyError:
                raise ModelError(
                    _format("CIM_RegisteredProfile instance in namespace "
                            "{0!A} does not have a property "
                            "'RegisteredVersion'",
                            self.interop_ns))

            inst_org_lower = inst_org.lower() \
                if inst_org is not None else None
            inst_name_lower = inst_name.lower() \
                if inst_name is not None else None
            inst_version_lower = inst_version.lower() \
                if inst_version is not None else None

            # pylint: disable=too-many-boolean-expressions
            if (org_lower is None or org_lower == inst_org_lower) and \
                    (name_lower is None or name_lower == inst_name_lower) and \
                    (version_lower is None or
                     version_lower == inst_version_lower):
                rtn.append(inst)
        return rtn

    def get_central_instances(self, profile_path, central_class=None,
                              scoping_class=None, scoping_path=None,
                              reference_direction='dmtf',
                              try_gci_method=False):
        """
        Return the instance paths of the central instances of a management
        profile.

        DMTF defines the following profile advertisement methodologies
        in :term:`DSP1033`:

        * GetCentralInstances methodology (new in :term:`DSP1033` 1.1, only
          when explicitly requested by the caller)
        * Central class methodology
        * Scoping class methodology

        A brief explanation of these methodologies can be found in
        section :ref:`Profile advertisement methodologies`.

        Pywbem attempts all three profile advertisement methodologies in the
        order listed above.

        All three methodologies start from the CIM_RegisteredProfile instance
        referenced by the `profile_path` parameter. That instance represents
        a management profile. In case of multiple uses of a component profile
        in a WBEM server, one such instance is supposed to represent one such
        profile use.

        If the profile is a component profile and its implementation does not
        support the GetCentralInstances or central class methodologies, the
        `central_class`, `scoping_class`, and `scoping_path` parameters are
        required in order for the method to attempt the scoping class
        methodology. The method will not fail if these parameters are not
        provided, as long as the profile implementation supports the
        GetCentralInstances or central class methodology.

        Example parameters for a 1-hop scoping path:

        * ``central_class = "CIM_Fan"``
        * ``scoping_path = ["CIM_SystemDevice"]``
        * ``scoping_class = "CIM_ComputerSystem"``

        Example parameters for a 2-hop scoping path:

        * ``central_class = "CIM_Sensor"``
        * ``scoping_path = ["CIM_AssociatedSensor", "CIM_Fan",
          "CIM_SystemDevice"]``
        * ``scoping_class = "CIM_ComputerSystem"``

        Parameters:

          profile_path (:class:`~pywbem.CIMInstanceName`):
            Instance path of the `CIM_RegisteredProfile` instance representing
            the management profile (or its use, if there are multiple uses
            in a WBEM server).

          central_class (:term:`string`):
            Class name of central class defined by the management profile.

            Will be ignored, unless the profile is a component profile and its
            implementation supports only the scoping class methodology.
            `None` will cause the scoping class methodology not to be
            attempted.

          scoping_class (:term:`string`):
            Class name of scoping class defined by the management profile.

            Will be ignored, unless the profile is a component profile and its
            implementation supports only the scoping class methodology.
            `None` will cause the scoping class methodology not to be
            attempted.

          scoping_path (list of :term:`string`):
            Scoping path defined by the management profile.

            Will be ignored, unless the profile is a component profile and its
            implementation supports only the scoping class methodology.
            `None` will cause the scoping class methodology not to be
            attempted.

          reference_direction (:term:`string`):
            Defines the navigation direction across the CIM_ReferencedProfile
            association when navigating from the current profile to its
            scoping (= referencing, autonomous) profile when using the scoping
            class methodology, as follows:

            * 'dmtf' (default): Assume DMTF conformance, i.e. the 'Dependent'
              end is followed.
            * 'snia': Assume SNIA SMI-S conformance, i.e. the 'Antecedent'
              end is followed.

            This parameter supports the different definitions between DMTF and
            SNIA SMI-S standards regarding the use of the two ends of the
            CIM_ReferencedProfile association:

            * The DMTF standards define in DSP1033 and DSP1001:

              - Antecedent = referenced profile = component profile
              - Dependent = referencing profile = autonomous profile

            * The SNIA SMI-S standard defines in the "Profile Registration
              Profile" (in the SMI-S "Common Profiles" book):

              - Antecedent = autonomous profile
              - Dependent = component (= sub) profile

            It should be assumed that all profiles that are directly or
            indirectly scoped by a particular top-level (= wrapper)
            specification implement the reference direction that matches the
            registered organisation of the top-level specification.

            Examples:

            * All profiles scoped by the SNIA SMI-S top-level specification
              should be assumed to implement the 'snia' reference direction.

            * All profiles scoped by the DMTF SMASH wrapper specification
              should be assumed to implement the 'dmtf' reference direction.

          try_gci_method (:class:`py:bool`):
            Flag indicating that the GetCentralInstances methodology should be
            attempted. This methodology is not expected to be implemented by
            WBEM servers at this point, and causes undesirable behavior with
            some WBEM servers, so it is not attempted by default. Note that
            WBEM servers are required to support the scoping class methodology.

        Returns:

          :class:`py:list` of :class:`~pywbem.CIMInstanceName`: The instance
          paths of the central instances of the implementation of the
          management profile.

        Raises:

            Exceptions raised by :class:`~pywbem.WBEMConnection`.
            ModelError: An error with the model implemented by the WBEM server.
            ValueError: User errors regarding input parameter values.
            TypeError: User errors regarding input parameter types.
        """

        if reference_direction not in ('dmtf', 'snia'):
            raise ValueError(
                _format("The reference_direction parameter must be 'dmtf' or "
                        "'snia', but is: {0!A}", reference_direction))

        scoping_result_role = "Dependent" if reference_direction == 'dmtf' \
            else "Antecedent"

        if not isinstance(profile_path, CIMInstanceName):
            raise TypeError(
                _format("The profile_path argument must be a CIMInstanceName, "
                        "but has type: {0}", type(profile_path)))

        if try_gci_method:

            # Try GetCentralInstances() method:
            try:
                (ret_val, out_params) = self._conn.InvokeMethod(
                    MethodName="GetCentralInstances",
                    ObjectName=profile_path)
            except CIMError as exc:
                if exc.status_code in (CIM_ERR_FAILED,
                                       CIM_ERR_METHOD_NOT_FOUND,
                                       CIM_ERR_METHOD_NOT_AVAILABLE,
                                       CIM_ERR_NOT_SUPPORTED):
                    # Method is not implemented.
                    # CIM_ERR_NOT_SUPPORTED is not an official status code for
                    # this situation, but is used by some implementations.
                    pass  # try next approach
                else:
                    raise
            except (CIMXMLParseError, XMLParseError) as exc:
                # The EMC server returns XMLParseError due to ill-formed XML.
                # The Dell server returns CIMXMLParseError due to INSTANCE
                # element with missing CLASSNAME attribute.
                # In both cases the ERROR element is parseable in the CIM-XML
                # string. Tolerate that behavior if the error is that the
                # method is not implemented, and try next approach.
                reply_oneline = self._conn.last_raw_reply.replace(b'\n', b'')
                m = re.search(b'<ERROR CODE="([0-9]+)"', reply_oneline)
                if m:
                    try:
                        status_code = int(m.group(1))
                    except ValueError:
                        status_code = None
                    if status_code in (CIM_ERR_FAILED,
                                       CIM_ERR_METHOD_NOT_FOUND,
                                       CIM_ERR_METHOD_NOT_AVAILABLE,
                                       CIM_ERR_NOT_SUPPORTED):
                        warnings.warn(
                            _format("Tolerating {0} raised when parsing "
                                    "CIM-XML response of invoking CIM method "
                                    "GetCentralInstances, with a CIM status "
                                    "code {1}: {2}",
                                    exc.__class__.__name__, status_code, exc),
                            ToleratedServerIssueWarning, 1)
                        # try next approach
                    else:
                        # It would be nice to extend the exception message to
                        # indicate that a CIM status code was detectable, but
                        # it is not possible to do that if we want to maintain
                        # standard exception semantics w.r.t. the message.
                        # So we just re-raise the original CIMXMLParseError or
                        # XMLParseError.
                        raise
                else:
                    # In this case, the ERROR element is not recognizable, so
                    # we just re-raise the original CIMXMLParseError or
                    # XMLParseError.
                    raise
            else:
                if ret_val != 0:
                    raise ModelError(
                        _format("The GetCentralInstances() method is "
                                "implemented but failed with rc={0} for "
                                "profile {1!A}",
                                ret_val, profile_path.to_wbem_uri()))
                central_inst_paths = out_params['CentralInstances']
                return central_inst_paths

        # Try central methodology
        try:
            central_inst_paths = self._conn.AssociatorNames(
                ObjectName=profile_path,
                AssocClass="CIM_ElementConformsToProfile",
                ResultRole="ManagedElement")
        except CIMError as exc:
            if exc.status_code == CIM_ERR_NOT_SUPPORTED:
                # This association traversal is not implemented, so we can
                # conclude that the central methodology is not implemented.
                pass  # Try next methodology
            else:
                raise
        else:
            # The central methodology is implemented.
            # Note: It is possible (and valid) that there are no central
            # instances.
            return central_inst_paths

        # Try scoping methodology
        if central_class is None or \
           scoping_class is None or \
           scoping_path is None:
            raise ValueError(
                _format("Parameters required for scoping class methodology not "
                        "specified and other methodologies not implemented "
                        "for profile {0!A}",
                        profile_path.to_wbem_uri()))

        # Go up one level on the profile side, to the scoping profile
        referencing_profile_paths = self._conn.AssociatorNames(
            ObjectName=profile_path,
            AssocClass="CIM_ReferencedProfile",
            ResultRole=scoping_result_role)
        if not referencing_profile_paths:
            raise ModelError(
                _format("No referencing profile found for profile {0!A} when "
                        "attempting the scoping class methodology (traversing "
                        "CIM_ReferencedProfile to its {1!A} end using the {2} "
                        "reference direction)",
                        profile_path.to_wbem_uri(), scoping_result_role,
                        reference_direction))

        if len(referencing_profile_paths) > 1:
            raise ModelError(
                _format("More than one referencing profile found for profile "
                        "{0!A} when attempting the scoping class methodology "
                        "(traversing CIM_ReferencedProfile to its {1!A} end "
                        "using the {2} reference direction). "
                        "Found referencing profiles {3!A}",
                        profile_path.to_wbem_uri(), scoping_result_role,
                        reference_direction,
                        [p.to_wbem_uri() for p in referencing_profile_paths]))

        # Traverse to the resource side.
        # Note: Because the scoping path of the scoping profile is not known,
        # all we can do is to rely on the central methodology to be implemented
        # by the scoping profile. Therefore, we pass only the central class of
        # the scoping profile (which is the scoping class of the original
        # profile).
        # Note: It is assumed that the scoping profile has the same reference
        # direction as the original profile.
        scoping_profile_path = referencing_profile_paths[0]
        scoping_inst_paths = self.get_central_instances(
            scoping_profile_path,
            scoping_class, None, None,
            reference_direction)
        if not scoping_inst_paths:
            # In order to be able to traverse down to the original profile's
            # central instances, we need the scoping profile to have
            # at least one central instance.
            raise ModelError(
                _format("Profile {0!A} does not have any central instances, "
                        "but that is required in its role of the scoping "
                        "profile of profile {1!A} when attempting the "
                        "scoping class methodology",
                        scoping_profile_path.to_wbem_uri(),
                        profile_path.to_wbem_uri()))

        # On the resource side, traverse down the reversed scoping path,
        # to the central instances of the original profile.
        traversal_path = list(reversed(scoping_path))
        traversal_path.append(central_class)
        central_inst_paths = self._traverse(scoping_inst_paths, traversal_path)
        return central_inst_paths

    def _traverse(self, start_paths, traversal_path):
        """
        Traverse a multi-hop traversal path from a list of start instance
        paths, and return the resulting list of instance paths.

        Parameters:
          start_paths (list of CIMInstanceName): Instance paths to start
            traversal from.
          traversal_path (list of string): Traversal hops, where the list
            contains pairs of items: association class name, far end class
            name. Example: a 2-hop traversal is represented as
            `['A1', 'C1', 'A2', 'C2']`.

        Returns:
          List of CIMInstanceName: Instances at the far end of the traversal.
        """
        assert len(traversal_path) >= 2
        assoc_class = traversal_path[0]
        far_class = traversal_path[1]
        total_next_paths = []
        for path in start_paths:
            next_paths = self._conn.AssociatorNames(
                ObjectName=path,
                AssocClass=assoc_class,
                ResultClass=far_class)
            total_next_paths.extend(next_paths)
        traversal_path = traversal_path[2:]
        if traversal_path:
            total_next_paths = self._traverse(total_next_paths, traversal_path)
        return total_next_paths

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
            ModelError: An error with the model implemented by the WBEM server.
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
                if exc.status_code in (CIM_ERR_INVALID_CLASS,
                                       CIM_ERR_NOT_FOUND):
                    # Class is not implemented, but current namespace exists.
                    interop_ns = ns
                    break
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
            raise ModelError(
                _format("Interop namespace could not be determined "
                        "(tried {0!A})", self.INTEROP_NAMESPACES),
                conn_id=self.conn.conn_id)
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

        If the namespaces could be determined, this method sets the following
        properties of this object:

        * :attr:`namespace_classname`
        * :attr:`namespaces`
        * :attr:`namespace_paths`

        Otherwise, it raises an exception.

        Note that there is at least one WBEM server that implements an Interop
        namespace but does not represent that with a CIM instance. In that
        case, the :attr:`namespaces` property will include the Interop
        namespace, but the :attr:`namespace_paths` property will not.

        Raises:

            Exceptions raised by :class:`~pywbem.WBEMConnection`.
            ModelError: An error with the model implemented by the WBEM server.
        """
        ns_insts = None
        ns_classname = None
        interop_ns = self.interop_ns  # Determines the Interop namespace
        for classname in self.NAMESPACE_CLASSNAMES:
            try:
                ns_insts = self._conn.EnumerateInstances(
                    classname, namespace=interop_ns)
            except CIMError as exc:
                if exc.status_code in (CIM_ERR_INVALID_CLASS,
                                       CIM_ERR_NOT_FOUND):
                    # Class is not implemented, try next one.
                    continue
                # Some other error.
                raise
            else:
                # Found a namespace class that is implemented.
                ns_classname = classname
                break
        if ns_insts is None:
            # Exhausted the possible class names
            raise ModelError(
                _format("Namespace class could not be determined "
                        "(tried {0!A})", self.NAMESPACE_CLASSNAMES),
                conn_id=self.conn.conn_id)
        self._namespace_classname = ns_classname
        self._namespaces = [inst['Name'] for inst in ns_insts]
        self._namespace_paths = [inst.path for inst in ns_insts]

        # An old version of a Hitachi server supports an Interop namespace
        # named 'interop' but does not represent it with a CIM instance.
        namespaces_lower = [ns.lower() for ns in self._namespaces]
        if interop_ns.lower() not in namespaces_lower:
            warnings.warn(
                _format("Server at {0} has an Interop namespace {1!A}, but "
                        "does not return it when enumerating class {2!A} "
                        "- adding it to the 'namespaces' property",
                        self.conn.url, interop_ns, ns_classname),
                ToleratedServerIssueWarning, stacklevel=2)
            self._namespaces.append(interop_ns)

    def _determine_brand(self):
        """
        Determine the brand of the WBEM server (e.g. OpenPegasus, SFCB, ...)
        and its version, by communicating with it and retrieving the
        `CIM_ObjectManager` instance.

        On success, this method sets the :attr:`brand`, :attr:`version`, and
        :attr:`cimom_inst` attributes of this object and returns.
        Otherwise, it raises an exception.

        Raises:

            Exceptions raised by :class:`~pywbem.WBEMConnection`.
            ModelError: An error with the model implemented by the WBEM server.
        """
        cimom_insts = self._conn.EnumerateInstances(
            "CIM_ObjectManager", namespace=self.interop_ns)
        if len(cimom_insts) != 1:
            raise ModelError(
                _format("Unexpected number of CIM_ObjectManager instances: "
                        "{0!A} ", [i['ElementName'] for i in cimom_insts]),
                conn_id=self.conn.conn_id)
        cimom_inst = cimom_insts[0]

        elementname = cimom_inst.get('ElementName', None)
        description = cimom_inst.get('Description', None)

        elementname_lower = elementname.lower()
        if "pegasus" in elementname_lower:
            # ElementName = "Pegasus"
            # Description = "Pegasus CIM Server Version 2.13.0"
            #             | "Pegasus CIM Server Version 2.15.0 Released"
            brand = "OpenPegasus"
            m = re.match(r'^.*(?:version) *([0-9]+\.[0-9]+[^ ]*)(?: .+)?$',
                         description, re.IGNORECASE)
            version = m.group(1) if m else None
        elif "sfcb" in elementname_lower:
            # ElementName = "sfcb"
            # Description = "Small Footprint CIM Broker 1.3.11"
            brand = "SFCB"
            m = re.match(r'^.* ([0-9]+\.[0-9]+.*)$',
                         description, re.IGNORECASE)
            version = m.group(1) if m else None
        elif " j wbem server" in elementname_lower:
            # ElementName = "WS J WBEM Server" | "WBEM Solutions J WBEM Server"
            # Description = "WS J WBEM Server" | "WBEM Solutions J WBEM Server"
            # Version = "4.5.1"
            # Build = "02/25/2016 13:09"
            brand = "WBEM Solutions J WBEM Server"
            version = cimom_inst.get('Version', None)
        elif "emc cim server" in elementname_lower:
            # ElementName = "EMC CIM Server"
            # Description = "EMC CIM Server Version 2.7.3.6.0.11D"
            brand = "EMC CIM Server"
            m = re.match(r'^.* version *(.*)$', description, re.IGNORECASE)
            version = m.group(1) if m else None
        elif "CIM Object Manager for FUJITSU" in elementname_lower:
            # ElementName = "CIM Object Manager for FUJITSU storage system"
            # Description = "CIM Object Manager for FUJITSU storage system"
            brand = "FUJITSU CIM Object Manager"
            version = None
        else:
            brand = elementname or 'unknown'
            version = None
            if description is not None:
                m = re.match(r'^.* (?:version|release) *(.+)?$',
                             description, re.IGNORECASE)
                version = m.group(1) if m else None

        self._brand = brand
        self._version = version
        self._cimom_inst = cimom_inst

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
            ModelError: An error with the model implemented by the WBEM server.
        """
        mp_insts = self._conn.EnumerateInstances("CIM_RegisteredProfile",
                                                 namespace=self.interop_ns)
        self._profiles = mp_insts
