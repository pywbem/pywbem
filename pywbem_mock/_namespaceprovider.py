#
# (C) Copyright 2020 InovaDevelopment.com
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
# Author: Karl  Schopmeyer <inovadevelopment.com>
#

"""
This module implements a user-defined provider for the class CIM_Namespace

This  provider manages creation and deletion of the instances of the
CIM_Namespace class and limits that activity to the server environment interop
classname.  The CIM_Namespace class is a DMTF defined class that
defines an instance for each namespace in the server environment and allows
the creation and deletion of server CIM namespaces to be controlled through
creation and deletion of instances of  the CIM_Namespace class.
"""

from copy import deepcopy

from pywbem import CIMError, CIMInstance, CIM_ERR_NOT_SUPPORTED, \
    CIM_ERR_INVALID_PARAMETER

from pywbem._nocasedict import NocaseDict

from pywbem._utils import _format

# TODO: Should be able to import from pywbem_mock
from ._instancewriteprovider import InstanceWriteProvider

from .config import OBJECTMANAGERNAME, SYSTEMNAME, SYSTEMCREATIONCLASSNAME, \
    OBJECTMANAGERCREATIONCLASSNAME


class CIMNamespaceProvider(InstanceWriteProvider):
    # pylint: disable=line-too-long
    """
    Implements the user defined provider for the class CIM_Namespace.

    This provider provides the create, modify, and delete methods for
    adding an instance of the class CIM_Namspace when a namespace is created or
    deleted in a pywbem mock environment.

    This class and the instances of this class only exist in the WBEM server
    Interop namespace per DMTF definitions.

    This class __init__ saves the  cimrepository variable used by methods in
    this class and by methods of its superclasses (i.e.  InstanceWriteProvider).

    The provider defines the class level attribute `provider_classnames` (CIM_Namespace)

    This provider presumes that an Interop namespace has been created before
    the provider object is constructed and fails the constructor if
    there is not interop_namespace
    """  # noqa: E501
    # pylint: enable=line-too-long

    # This class level attribute must exist to define the CIM classname(es) .
    # for which this provider is responsible.
    #: provider_classnames (:term:`string`):
    #:        The classname for this provider
    provider_classnames = 'CIM_Namespace'

    def __init__(self, cimrepository):
        """
        Parameters:

          cimrepository (:class:`~pywbem_mock.BaseRepository` or subclass):
            Defines the CIM repository to be used by request responders.  The
            repository is fully initialized except for CIM classes or instances
            required by this user-defined provider.
        """
        super(CIMNamespaceProvider, self).__init__(cimrepository)

        # NOTE: conn is only required for the following operation and
        # is not kept in the constructed object.

        if not self.find_interop_namespace():
            raise CIMError(
                CIM_ERR_INVALID_PARAMETER,
                _format("No Interop namespace found. "
                        "Construction of CIM_Namespace provider aborted."
                        "Namespaces found: ", ", ".
                        join(self.interop_namespace_names)))

        self.installed = False  # test if provider previously installed.

    def __repr__(self):
        return _format(
            "CIMNamespaceProvider("
            "provider_type={s.provider_type}, "
            "provider_classnames={s.provider_classnames})",
            s=self)

    def CreateInstance(self, namespace, NewInstance):
        """
        Create an instance of the CIM_Namespace class in the Interop namespace
        with the required parameters.  If the namespace defined in
        NewInstance.name does not exist, it creates the namespace in the
        cimrepository.

        The Interop namespace must already exist in the CIM repository when
        this method is executed.

        If the namespace defined in the the NewInstance.Name property does
        not exist in the CIM repository, that namespace is added to the
        repository.

        See `~pywbem_mock.InstanceWriteProvider.CreateInstance` for
        documentation of the input parameters noting extra conditions defined
        below:

        Parameters:
          namespace (:term:`string`):
            The name of the Interop namespace in the CIM repository (case
            insensitive). Must not be `None`. Leading or trailing slash
            characters are ignored.

         NewInstance (:class:`~pywbem.CIMInstance`):
            A representation of the CIM instance to be created.

            Since this method is called by the ProviderDispatcher, the key
            characteristics of the instance have been validated already.

            This must be an instance of the class CIM_Instance. Note that
            most of the properties are modified by this method.  The Name
            property must exist since it defines the name of the namespace
            which this instance will represent

        Raises:

          :exc:`~pywbem.CIMError`: (CIM_ERR_INVALID_PARAMETER) if namespace
            is not the Interop namespace in the CIM repository or the Name
            property does not exist or the other properties cannot be added to
            the instance.
        """
        self.validate_namespace(namespace)

        new_instance = deepcopy(NewInstance)

        if not self.is_interop_namespace(namespace):
            raise CIMError(
                CIM_ERR_INVALID_PARAMETER,
                _format(
                    "Instances of {0!A} are only allowed in the Interop "
                    "namespace for the server. {1!A} is not an Interop "
                    "namespace. It must be one of {2!A} ",
                    NewInstance.classname, namespace,
                    ", ".join(self.interop_namespace_names)))

        try:
            new_namespace = new_instance['Name']
        except KeyError:
            raise CIMError(
                CIM_ERR_INVALID_PARAMETER,
                _format("Namespace creation via CreateInstance: "
                        "Missing 'Name' property in the {0!A} instance ",
                        new_instance.classname))

        # Normalize the namespace name
        new_namespace = new_namespace.strip('/')

        # Write it back to the instance in case it was changed
        new_instance['Name'] = new_namespace

        # Validate the property values.
        try:
            ccn_prop = 'CreationClassName'
            if new_instance[ccn_prop] != new_instance.classname:
                raise CIMError(
                    CIM_ERR_INVALID_PARAMETER,
                    _format("CIM_Namespace CreateInstance: "
                            "Invalid property {0|A} for CIM_Instance {1!A}",
                            ccn_prop, new_instance))

        except KeyError as ke:
            raise CIMError(
                CIM_ERR_INVALID_PARAMETER,
                _format("Namespace creation via CreateInstance: "
                        "Missing property {0|A}for CIM_Instance {0!A}. "
                        "Exception: {1!A}", ccn_prop, new_instance, ke))

        ns_dict = NocaseDict({ns: ns for ns in self.cimrepository.namespaces})
        if new_namespace not in ns_dict:
            self.cimrepository.add_namespace(new_namespace)

        # Pass NewInstance to the default CreateInstance
        # Default CreateInstance creates path, validates all key properties
        # in instance and inserts instance into the repository.
        return super(CIMNamespaceProvider, self).CreateInstance(namespace,
                                                                new_instance)

    def ModifyInstance(self, ModifiedInstance,
                       IncludeQualifiers=None, PropertyList=None):
        """
        Modification of CIM_Namespace instance not allowed
        """
        raise CIMError(
            CIM_ERR_NOT_SUPPORTED,
            _format("Modification of CIM_Namespace {0!A} not allowed. ",
                    ModifiedInstance.classname))

    def DeleteInstance(self, InstanceName):
        """
        Delete the namespace defined by the `Name` keybinding in the
        InstanceName parameter and remove the instance defined by InstanceName.

        The namespace must be empty to be removed otherwise an exception is
        generated.

        This method does not allow removing the Interop namespace.

        Parameters:

          InstanceName: (:class:`~pywbem.CIMInstanceName`):
            The instance path of the instance to be deleted with the
            following attributes:

            * `classname`: Name of the creation class of the instance.
            * `keybindings`: Keybindings of the instance. The keybinding
              `Name` must exist. It defines the namespace to be removed.
            * `namespace`: Name of the CIM namespace containing the instance.
              Must not be None.
            * `host`: value ignored.

        Raises:

          :exc:`~pywbem.CIMError`: (CIM_ERR_INVALID_NAMESPACE) if the
            namespace defined in InstanceName does not exist in the CIM
            repository.
          :exc:`~pywbem.CIMError`: (CIM_ERR_INVALID_CLASS) if the classname
            does not exist in the CIM repository.
          :exc:`~pywbem.CIMError`: (CIM_ERR_NOT_FOUND) if the instance to be
            deleted is not found in the ICM repository.
          :exc:`~pywbem.CIMError`: (CIM_ERR_NAMESPACE_NOT_EMPTY) if attempting
            to delete the default connection namespace.  This namespace cannot
            be deleted from the CIM repository.
        """

        assert InstanceName.classname.lower() == \
            CIMNamespaceProvider.provider_classnames.lower()

        remove_namespace = InstanceName.keybindings['Name']

        if self.is_interop_namespace(remove_namespace):
            raise CIMError(
                CIM_ERR_INVALID_PARAMETER,
                _format("Namespace deletion of the Interop namespace {0|A} "
                        "is not allowed by the namespace provider.",
                        remove_namespace))

        # Reflect the namespace deletion in the CIM repository
        # This call implements the CIM repository remove namespace which
        # checks for empty namespace.
        self.remove_namespace(remove_namespace)

        # Delete the instance from the CIM repository
        instance_store = self.cimrepository.get_instance_store(
            InstanceName.namespace)
        instance_store.delete(InstanceName)

    def post_register_setup(self, conn):
        """
        Method called by FakedWBEMConnection.register_provider to complete
        initialization of this provider.  This method is called after
        the required classes are installed in the cim_repository

        This is necessary because pywbem_mock does not allow user-defined
        providers for the instance read operations such as EnumerateInstances
        so the instance for each namespace must be exist in the repository.

        This method:

        1. Inserts instances of CIM_Namespace for every namespace in the
           CIM repository.
        """
        assert self.installed is False

        self.installed = True

        # Temp code to validate class installed.  Will generate exception
        # if class does not exist.
        interop_namespace = conn.find_interop_namespace()
        provider_classname = self.provider_classnames
        conn.GetClass(provider_classname, interop_namespace)

        # Create instance CIM_Namespace for each existing namespace

        insts = conn.EnumerateInstances('CIM_Namespace',
                                        namespace=conn.find_interop_namespace(),
                                        LocalOnly=False,
                                        DeepInheritance=False)

        # NocaseDict for case-insensitive tests
        nsinsts_dict = NocaseDict([(inst.name, None) for inst in insts])

        # Get the current namespaces directly from the repository since the
        # instances of CIM_Namespace not yet set up.
        namespaces = conn.cimrepository.namespaces

        klass = conn.GetClass(provider_classname, interop_namespace,
                              LocalOnly=False,
                              IncludeQualifiers=True,
                              IncludeClassOrigin=True)

        for ns in namespaces:
            if ns not in nsinsts_dict:
                self.create_cimnamespace_instance(conn, ns, interop_namespace,
                                                  klass)

    @staticmethod
    def create_cimnamespace_instance(conn, namespace, interop_namespace, klass):
        """
        Build and execute CreateInstance for an instance of CIM_Namespace using
        the `namespace` parameter as the value of the name property in the
        instance. The instance is created in the `interop_namespace`

        Parameters:

          namespace (:term:`string`):
            Namespace that this instance defines.

          interop_namespace (:term:`string`):
            Interop namespace for this environment.

          klass (:class:`CIM_Namespace`):
            The CIM class CIM_Namespace which is used to create the instance.

        Raises:

            :exc:`~pywbem.CIMError`: For errors encountered with CreateInstance
        """
        properties = NocaseDict(
            [('Name', namespace),
             ('CreationClassName', klass.classname),
             ('ObjectManagerName', OBJECTMANAGERNAME),
             ('ObjectManagerCreationClassName', OBJECTMANAGERCREATIONCLASSNAME),
             ('SystemName', SYSTEMNAME),
             ('SystemCreationClassName', SYSTEMCREATIONCLASSNAME)])

        new_instance = CIMInstance.from_class(klass, property_values=properties)
        conn.CreateInstance(new_instance, interop_namespace)
