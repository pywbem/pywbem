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
This module is part of the support for user-defined providers.  User-defined
providers may be created within pywbem_mock to extend the capability
of the mocker for special processing for selected classes.

This module contains the ProviderDispatcher class which routes request methods
that allow user-defined providers either to the default method  or if a
user-defined provider is registered to the user-defined method for the
provider class defined in the provider registry.
"""

from __future__ import absolute_import, print_function

import six

from pywbem import CIMInstance, CIMInstanceName, CIMError, \
    CIM_ERR_NOT_FOUND, CIM_ERR_INVALID_PARAMETER, CIM_ERR_INVALID_CLASS, \
    CIM_ERR_METHOD_NOT_FOUND

from pywbem._utils import _format

from ._baseprovider import BaseProvider
from ._instancewriteprovider import InstanceWriteProvider
from ._methodprovider import MethodProvider


class ProviderDispatcher(BaseProvider):
    """
    This class dispatches requests destined for the provider methods defined in
    InstanceWriteProvider or MethodProvider  to the either the default provider
    method or the provider registered for processing the defined class in the
    defined namespace.

    It handles the following requests:

    * CreateInstance: default is InstanceWriteProvider.CreateInstance
    * ModifyInstance: default is InstanceWriteProvider.ModifyInstance
    * DeleteInstance: default is InstanceWriteProvider.DeleteInstance
    * InvokeMethod: default is MethodProvider.InvokeMethod
    """

    def __init__(self, cimrepository, provider_registry):
        """
        Set instance parameters passed from FakedWBEMConnection
        """
        super(ProviderDispatcher, self).__init__(cimrepository)

        self.provider_registry = provider_registry

        # Define the instances of the default implementations for the
        # InstanceWriteProvider and MethodProvider. The default providers
        # are constructed on first call.
        self._default_instance_write_provider = None
        self._default_method_provider = None

    @property
    def default_instance_write_provider(self):
        """
        Instance object for default instance provider. Constructed on first
        call
        """
        if self._default_instance_write_provider is None:
            self._default_instance_write_provider = InstanceWriteProvider(
                self.cimrepository)
        return self._default_instance_write_provider

    @property
    def default_method_provider(self):
        """
        Instance object for default method provider. Constructed on first
        call
        """
        if self._default_method_provider is None:
            self._default_method_provider = MethodProvider(
                self.cimrepository)
        return self._default_method_provider

    def CreateInstance(self, namespace, NewInstance):
        # pylint: disable=invalid-name
        """
        Dispatcher for CreateInstance.

        This method validates input parameters against the repository and
        provider required parameter types and if successful, routes the method
        either to the default provider or to a provider registered for the
        namespace and class in InstanceName
        """
        # Validate input parameters

        self.validate_namespace(namespace)

        if not isinstance(NewInstance, CIMInstance):
            raise TypeError(
                _format("NewInstance parameter is not a valid CIMInstance. "
                        "Rcvd type={0}", type(NewInstance)))

        if not self.class_exists(namespace, NewInstance.classname):
            raise CIMError(
                CIM_ERR_INVALID_CLASS,
                _format("Cannot create instance because its creation "
                        "class {0!A} does not exist in namespace {1!A}.",
                        NewInstance.classname, namespace))

        provider = self.provider_registry.get_registered_provider(
            namespace, 'instance-write', NewInstance.classname)

        # Execute the method in the provider if the method exists. Otherwise
        # fall back to the default provider
        if provider:
            try:
                return provider.CreateInstance(namespace, NewInstance)
            except AttributeError:
                pass

        return self.default_instance_write_provider.CreateInstance(
            namespace, NewInstance)

    def ModifyInstance(self, ModifiedInstance,
                       IncludeQualifiers=None, PropertyList=None):
        # pylint: disable=invalid-name
        """
        Dispatcher for the ModifyInstance method.

        This method validates input parameters against the repository and
        provider required types and if successful, routes the method either to
        the default provider or to a provider registered for the namespace and
        class in ModifiedInstance.

        Validates basic characteristics of parameters including:

        1. Namespace xists.
        2. Modified instance is valid instance.
        3. ClassName same in instance and instance.path
        4. Class exists in repository
        5. Instance exists in repository.
        """

        namespace = ModifiedInstance.path.namespace
        self.validate_namespace(namespace)

        if not isinstance(ModifiedInstance, CIMInstance):
            raise CIMError(
                CIM_ERR_INVALID_PARAMETER,
                _format("The ModifiedInstance parameter is not a valid "
                        "CIMInstance. Rcvd type={0}", type(ModifiedInstance)))

        # Classnames in instance and path must match
        if ModifiedInstance.classname.lower() != \
                ModifiedInstance.path.classname.lower():
            raise CIMError(
                CIM_ERR_INVALID_PARAMETER,
                _format("ModifyInstance classname in path and instance do "
                        "not match. classname={0!A}, path.classname={1!A}",
                        ModifiedInstance.classname,
                        ModifiedInstance.path.classname))

        if not self.class_exists(namespace, ModifiedInstance.classname):
            raise CIMError(
                CIM_ERR_INVALID_CLASS,
                _format("ModifyInstance classn {0!A} does not exist in"
                        "CIM repository for namespace {1!A}.",
                        ModifiedInstance.classname,
                        namespace))

        # Test original instance exists.
        instance_store = self.cimrepository.get_instance_store(namespace)
        if not instance_store.object_exists(ModifiedInstance.path):
            raise CIMError(
                CIM_ERR_NOT_FOUND,
                _format("ModifiedInstance {0!A} not found in CIM repository",
                        ModifiedInstance.path))

        provider = self.provider_registry.get_registered_provider(
            namespace, 'instance-write', ModifiedInstance.classname)

        # Execute the method in the provider if the method exists. Otherwise
        # fall back to the default provider
        if provider:
            try:
                return provider.ModifyInstance(
                    ModifiedInstance,
                    IncludeQualifiers=IncludeQualifiers,
                    PropertyList=PropertyList)
            except AttributeError:
                pass

        return self.default_instance_write_provider.ModifyInstance(
            ModifiedInstance,
            IncludeQualifiers=IncludeQualifiers,
            PropertyList=PropertyList)

    def DeleteInstance(self, InstanceName):
        # pylint: disable=invalid-name
        """
        Dispatcher for the DeleteInstance method.

        This method validates input parameters against the repository and
        provider required types and if successful, routes the method either to
        the default provider or to a provider registered for the namespace and
        class in InstanceName
        """

        # Validate input parameters
        namespace = InstanceName.namespace
        self.validate_namespace(namespace)

        # Test if corresponding class and instance already exist
        if not self.class_exists(namespace, InstanceName.classname):
            raise CIMError(
                CIM_ERR_INVALID_CLASS,
                _format("Class {0!A} in namespace {1!A} not found. "
                        "Cannot delete instance {2!A}",
                        InstanceName.classname, namespace, InstanceName))

        instance_store = self.cimrepository.get_instance_store(namespace)
        if not instance_store.object_exists(InstanceName):
            raise CIMError(
                CIM_ERR_NOT_FOUND,
                _format("Instance {0!A} not found in CIM repository",
                        InstanceName))

        provider = self.provider_registry.get_registered_provider(
            InstanceName.namespace, 'instance-write', InstanceName.classname)

        # Execute the method in the provider if the method exists. Otherwise
        # fall back to the default provider
        if provider:
            try:
                return provider.DeleteInstance(InstanceName)
            except AttributeError:
                pass

        return self.default_instance_write_provider.DeleteInstance(
            InstanceName)

    def InvokeMethod(self, namespace, methodname, objectname, Params):
        # pylint: disable=invalid-name
        """
        Default Method provider.
        NOTE: There is no default method provider because all method
        providers provide specific functionality and there is no way
        to do that in a default method provider.
        """
        # Validate input parameters
        self.validate_namespace(namespace)

        assert isinstance(objectname, (CIMInstanceName, six.string_types))

        classname = objectname.classname \
            if isinstance(objectname, CIMInstanceName) else objectname

        # This raises CIM_ERR_NOT_FOUND or CIM_ERR_INVALID_NAMESPACE
        # Uses local_only = False to get characteristics from super classes
        # and include_class_origin to get origin of method in hierarchy
        cc = self.get_class(namespace, classname,
                            local_only=False,
                            include_qualifiers=True,
                            include_classorigin=True)

        # Determine if method defined in classname defined in
        # the classorigin of the method
        try:
            cc.methods[methodname].class_origin
        except KeyError:
            raise CIMError(
                CIM_ERR_METHOD_NOT_FOUND,
                _format("Method {0!A} not found in class {1!A}.",
                        methodname, classname))

        provider = self.provider_registry.get_registered_provider(
            namespace, 'method', classname)

        # The provider method MUST exist.
        if provider:
            return provider.InvokeMethod(namespace, methodname,
                                         objectname, Params)

        # Call the default provider.  Since there is not really a default
        # provider for a method, this generates a NOT_FOUND exception
        return self.default_method_provider.InvokeMethod(namespace, methodname,
                                                         objectname, Params)
