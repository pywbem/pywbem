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

from nocaselist import NocaseList

from pywbem import CIMError, CIMInstance, CIM_ERR_NOT_SUPPORTED, \
    CIM_ERR_INVALID_PARAMETER
from pywbem._nocasedict import NocaseDict
from pywbem._utils import _format

from ._instancewriteprovider import InstanceWriteProvider
from .config import OBJECTMANAGERNAME, SYSTEMNAME, SYSTEMCREATIONCLASSNAME, \
    OBJECTMANAGERCREATIONCLASSNAME


# CIM class name of the namespace class implemented in this provider
NAMESPACE_CLASSNAME = 'CIM_Namespace'


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
    provider_classnames = NAMESPACE_CLASSNAME

    def __init__(self, cimrepository):
        """
        Parameters:

          cimrepository (:class:`~pywbem_mock.BaseRepository` or subclass):
            Defines the CIM repository to be used by the provider.
        """
        super(CIMNamespaceProvider, self).__init__(cimrepository)

        if not self.find_interop_namespace():
            raise CIMError(
                CIM_ERR_INVALID_PARAMETER,
                _format("Cannot create namespace provider (for class {0}): "
                        "No Interop namespace exists in the CIM repository. "
                        "Valid Interop namespaces are: {1}",
                        NAMESPACE_CLASSNAME,
                        ", ".join(self.interop_namespace_names)))

        self.installed = False  # test if provider previously installed.

    def __repr__(self):
        return _format(
            "CIMNamespaceProvider("
            "provider_type={s.provider_type}, "
            "provider_classnames={s.provider_classnames})",
            s=self)

    def CreateInstance(self, namespace, new_instance):
        """
        Create an instance of the CIM_Namespace class in an Interop namespace
        of the CIM repository, and if not yet existing create the new namespace
        in the CIM repository.

        See `~pywbem_mock.InstanceWriteProvider.CreateInstance` for
        documentation of validation and description of input parameters, noting
        extra conditions for this provider as described below:

        Parameters:

          namespace (:term:`string`):
            Must be a valid Interop namespace.

          new_instance (:class:`~pywbem.CIMInstance`):
            The following applies regarding its properties:
            * 'Name' property: This property is required since it defines the
              name of the new namespace to be created.
            * 'CreationClassName' property: This property is required and its
              value must match the class name of the new instance.

        Raises:

          :exc:`~pywbem.CIMError`: (CIM_ERR_INVALID_PARAMETER) if namespace
            is not the Interop namespace in the CIM repository or the Name
            property does not exist or the other properties cannot be added to
            the instance.
        """

        if not self.is_interop_namespace(namespace):
            raise CIMError(
                CIM_ERR_INVALID_PARAMETER,
                _format(
                    "Cannot create instance of class {0!A} in namespace {1!A}: "
                    "The namespace is not an Interop namespace. "
                    "Valid Interop namespaces are: {2!A}",
                    new_instance.classname, namespace,
                    ", ".join(self.interop_namespace_names)))

        ccn_pname = 'CreationClassName'
        name_pname = 'Name'

        # Validate that required properties are specified in the new instance
        for pn in [name_pname, ccn_pname]:
            if pn not in new_instance:
                raise CIMError(
                    CIM_ERR_INVALID_PARAMETER,
                    _format(
                        "Cannot create instance of class {0!A} in "
                        "namespace {1!A}: "
                        "Missing required property {2!A} in new_instance",
                        new_instance.classname, namespace, pn))

        # Get and normalize the new namespace name
        new_namespace = new_instance[name_pname]  # Property value
        new_namespace = new_namespace.strip('/')

        # Write it back to the instance in case it was changed
        new_instance[name_pname] = new_namespace

        # Validate other property values in the new instance
        if new_instance[ccn_pname].lower() != new_instance.classname.lower():
            raise CIMError(
                CIM_ERR_INVALID_PARAMETER,
                _format(
                    "Cannot create instance of class {0!A} in namespace "
                    "{1!A}: Value of property {2|A} in new_instance does not "
                    "match class name but is {3!A}",
                    new_instance.classname, namespace,
                    ccn_pname, new_instance[ccn_pname]))

        # Create the new namespace in the CIM repository, if needed.
        # The add_namespace() method will prevent the creation of a second
        # Interop namespace, raising CIMError(CIM_ERR_ALREADY_EXISTS).
        if new_namespace not in self.cimrepository.namespaces:
            self.add_namespace(new_namespace)

        # Create the CIM instance for the new namespace in the CIM repository,
        # by delegating to the default provider method.
        return super(CIMNamespaceProvider, self).CreateInstance(
            namespace, new_instance)

    def ModifyInstance(self, modified_instance, IncludeQualifiers=None):
        """
        Modification of CIM_Namespace instance not allowed
        """
        raise CIMError(
            CIM_ERR_NOT_SUPPORTED,
            _format("Modification of {0} instances is not allowed: "
                    "{1!A}",
                    NAMESPACE_CLASSNAME, modified_instance.path))

    def DeleteInstance(self, InstanceName):
        """
        Delete an instance of the CIM_Namespace class in an Interop namespace
        of the CIM repository, and in addition delete the namespace represented
        by it in the CIM repository.

        See `~pywbem_mock.InstanceWriteProvider.CreateInstance` for
        documentation of validation and description of input parameters, noting
        extra conditions for this provider as described below:

        The namespace to be deleted must be empty and must not be the Interop
        namespace.

        Parameters:

          InstanceName: (:class:`~pywbem.CIMInstanceName`):
            The keybinding `Name` must exist; it defines the namespace to be
            deleted.

        Raises:

          :exc:`~pywbem.CIMError`: (CIM_ERR_INVALID_PARAMETER)
          :exc:`~pywbem.CIMError`: (CIM_ERR_NAMESPACE_NOT_EMPTY)
        """

        # The provider dispatcher ensures that provider methods are only called
        # for the registered classes.
        # And this provider sets only a single class, not a list.
        assert InstanceName.classname.lower() == \
            CIMNamespaceProvider.provider_classnames.lower()

        remove_namespace = InstanceName.keybindings['Name']

        if self.is_interop_namespace(remove_namespace):
            raise CIMError(
                CIM_ERR_INVALID_PARAMETER,
                _format("Cannot delete instance {0!A} from the CIM repository: "
                        "This instance represents the Interop namespace {1!A} "
                        "which must not be deleted.",
                        InstanceName, remove_namespace))

        # Delete the namespace from the CIM repository.
        # This call verifies that the namespace is empty and raises
        # CIMError(CIM_ERR_NAMESPACE_NOT_EMPTY) if not empty.
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

        # List of namespaces for which there are CIM instances
        inst_ns_list = NocaseList(
            [inst['Name'] for inst in insts if 'Name' in inst])

        klass = conn.GetClass(provider_classname, interop_namespace,
                              LocalOnly=False,
                              IncludeQualifiers=True,
                              IncludeClassOrigin=True)

        # Set up any CIM_Namespace instances that are still missing given the
        # namespaces that exist in the CIM repository.
        for ns in conn.cimrepository.namespaces:
            if ns not in inst_ns_list:
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
