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
    CIM_ERR_METHOD_NOT_AVAILABLE, CIM_ERR_METHOD_NOT_FOUND

from pywbem._utils import _format

from ._baseprovider import BaseProvider


class ProviderDispatcher(BaseProvider):
    """
    This class dispatches requests destined for the instance provider methods
    defined in InstanceWriteProvider  to the either the default instance
    provder method or the provider defined for processing the defined class in
    the defined namespace.
    """

    def __init__(self, cimrepository, provider_registry,
                 default_instance_provider):
        """
        Set instance parameters passed from FakedWBEMConnection
        """
        super(ProviderDispatcher, self).__init__(cimrepository)

        self.provider_registry = provider_registry

        # Defines the instance of InstanceWriteProvider that will
        # be called to dispatch operation to default provider.
        self.default_instance_provider = default_instance_provider

    def CreateInstance(self, namespace, NewInstance):
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
            namespace, 'instance', NewInstance.classname)

        # Execute the method in the provider if the method exists. Otherwise
        # fall back to the default provider
        if provider:
            try:
                return provider.CreateInstance(namespace, NewInstance)
            except AttributeError:
                pass

        return self.default_instance_provider.CreateInstance(
            namespace, NewInstance)

    def ModifyInstance(self, ModifiedInstance,
                       IncludeQualifiers=None, PropertyList=None):
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
        instance_store = self.get_instance_store(namespace)
        # Do not copy because not modified or passed on
        orig_instance = self.find_instance(ModifiedInstance.path,
                                           instance_store,
                                           copy=False)
        if orig_instance is None:
            raise CIMError(
                CIM_ERR_NOT_FOUND,
                _format("Original Instance {0!A} not found in namespace {1!A}",
                        ModifiedInstance.path, namespace))

        provider = self.provider_registry.get_registered_provider(
            namespace, 'instance', ModifiedInstance.classname)

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

        return self.default_instance_provider.ModifyInstance(
            ModifiedInstance,
            IncludeQualifiers=IncludeQualifiers,
            PropertyList=PropertyList)

    def DeleteInstance(self, InstanceName):
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

        instance_store = self.get_instance_store(namespace)
        if not instance_store.object_exists(InstanceName):
            raise CIMError(
                CIM_ERR_NOT_FOUND,
                _format("Instance {0!A} not found in CIM repository namespace "
                        "{1!A}", InstanceName, namespace))

        provider = self.provider_registry.get_registered_provider(
            InstanceName.namespace, 'instance', InstanceName.classname)

        # Execute the method in the provider if the method exists. Otherwise
        # fall back to the default provider
        if provider:
            try:
                return provider.DeleteInstance(InstanceName)
            except AttributeError:
                pass

        return self.default_instance_provider.DeleteInstance(
            InstanceName)

    def InvokeMethod(self, namespace, methodname, objectname, Params):
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

        # There is no default method provider so no user InvokeMethod
        # is defined for namespace and class, exception raise.
        raise CIMError(CIM_ERR_METHOD_NOT_AVAILABLE)
