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
from copy import deepcopy

from pywbem import CIMInstance, CIMInstanceName, CIMParameter, CIMError, \
    CIM_ERR_NOT_FOUND, CIM_ERR_INVALID_PARAMETER, CIM_ERR_INVALID_CLASS, \
    CIM_ERR_METHOD_NOT_FOUND

from pywbem._utils import _format
from pywbem._nocasedict import NocaseDict

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

    @staticmethod
    def _array_ness(is_array):
        """Return text for array-ness"""
        return "an array" if is_array else "a scalar"

    def CreateInstance(self, namespace, NewInstance):
        # pylint: disable=invalid-name
        """
        Dispatcher for the CreateInstance provider method.

        This method performs validations and if successful, routes the provider
        method call either to a registered provider, or to the default provider.
        """

        # Verify the input parameter types (type errors have already been
        # raised during checks in the WBEMConnection operation).
        assert isinstance(namespace, six.string_types)
        assert isinstance(NewInstance, CIMInstance)

        # Verify that the new instance has no path (ensured by the
        # WBEMConnection operation).
        assert NewInstance.path is None

        # Verify that the namespace exists in the CIM repository.
        self.validate_namespace(namespace)

        # Get creation class from CIM repository. The CIMClass objects in the
        # class store of the repository have all exposed properties (i.e.
        # defined and inherited, having resolved all overrides), qualifiers,
        # and classorigjn information.
        class_store = self.cimrepository.get_class_store(namespace)
        try:
            creation_class = class_store.get(NewInstance.classname)
        except KeyError:
            raise CIMError(
                CIM_ERR_INVALID_CLASS,
                _format("Creation class {0!A} of new instance does not "
                        "exist in namespace {1!A} of the CIM repository.",
                        NewInstance.classname, namespace))

        # Verify that the properties in the new instance are exposed by the
        # creation class and have the correct type-related attributes.
        for pn in NewInstance.properties:

            if pn not in creation_class.properties:
                raise CIMError(
                    CIM_ERR_INVALID_PARAMETER,
                    _format("Property {0!A} in new instance does not exist "
                            "in its creation class {1!A} in namespace {2!A} "
                            "of the CIM repository",
                            pn, NewInstance.classname, namespace))

            prop_inst = NewInstance.properties[pn]
            prop_cls = creation_class.properties[pn]

            if prop_inst.type != prop_cls.type:
                raise CIMError(
                    CIM_ERR_INVALID_PARAMETER,
                    _format("Property {0!A} in new instance has incorrect "
                            "type={1!A}, but should have type={2!A} "
                            "according to its creation class {3!A} in "
                            "namespace {4!A} of the CIM repository",
                            pn, prop_inst.type, prop_cls.type,
                            NewInstance.classname, namespace))

            if prop_inst.is_array != prop_cls.is_array:
                raise CIMError(
                    CIM_ERR_INVALID_PARAMETER,
                    _format("Property {0!A} in new instance has incorrect "
                            "is_array={1!A}, but should have is_array={2!A} "
                            "according to its creation class {3!A} in "
                            "namespace {4!A} of the CIM repository",
                            pn, prop_inst.is_array, prop_cls.is_array,
                            NewInstance.classname, namespace))

            if prop_inst.embedded_object != prop_cls.embedded_object:
                raise CIMError(
                    CIM_ERR_INVALID_PARAMETER,
                    _format("Property {0!A} in new instance has incorrect "
                            "embedded_object={1!A}, but should have "
                            "embedded_object={2!A} "
                            "according to its creation class {3!A} in "
                            "namespace {4!A} of the CIM repository",
                            pn, prop_inst.embedded_object,
                            prop_cls.embedded_object,
                            NewInstance.classname, namespace))

        # The providers are guaranteed to get a deep copy of the original
        # new instance since they may update properties.
        # TODO: Consolidate this deep copy with the shallow copy in
        #       WBEMConnection.CreateInstance().
        new_instance = deepcopy(NewInstance)

        # Determine the provider to be used. Note that a registered provider
        # always has all responder methods for the provider type, either
        # implemented or inherited.
        provider = self.provider_registry.get_registered_provider(
            namespace, 'instance-write', new_instance.classname)
        if not provider:
            provider = self.default_instance_write_provider

        # Call the provider method.
        result = provider.CreateInstance(namespace, new_instance)

        # Verify provider method result.
        assert isinstance(result, CIMInstanceName)

        return result

    def ModifyInstance(self, ModifiedInstance,
                       IncludeQualifiers=None, PropertyList=None):
        # pylint: disable=invalid-name
        """
        Dispatcher for the ModifyInstance provider method.

        This method performs validations and if successful, routes the provider
        method call either to a registered provider, or to the default provider.
        """

        # Verify the input parameter types (type errors have already been
        # raised during checks in the WBEMConnection operation).
        assert isinstance(ModifiedInstance, CIMInstance)
        assert isinstance(IncludeQualifiers, (bool, type(None)))
        assert isinstance(PropertyList,
                          (six.string_types, list, tuple, type(None)))
        assert isinstance(ModifiedInstance.path, CIMInstanceName)

        # Verify consistency of the class names in the modified instance.
        if ModifiedInstance.classname.lower() != \
                ModifiedInstance.path.classname.lower():
            raise CIMError(
                CIM_ERR_INVALID_PARAMETER,
                _format("Modified instance has inconsistent class names: "
                        "{0!A} in the instance, and {1!A} in the instance "
                        "path.",
                        ModifiedInstance.classname,
                        ModifiedInstance.path.classname))

        # Verify that the namespace exists in the CIM repository.
        namespace = ModifiedInstance.path.namespace
        self.validate_namespace(namespace)

        class_store = self.cimrepository.get_class_store(namespace)
        instance_store = self.cimrepository.get_instance_store(namespace)

        # Get creation class from CIM repository and verify that it exists.
        # The CIMClass objects in the class store of the repository have all
        # exposed properties (i.e. defined and inherited, having resolved all
        # overrides), qualifiers, and classorigjn information.
        try:
            creation_class = class_store.get(ModifiedInstance.classname)
        except KeyError:
            raise CIMError(
                CIM_ERR_INVALID_CLASS,
                _format("Creation class {0!A} of modified instance does not "
                        "exist in namespace {1!A} of the CIM repository.",
                        ModifiedInstance.classname, namespace))

        # Get instance to be modified from CIM repository.
        try:
            instance = instance_store.get(ModifiedInstance.path)
        except KeyError:
            raise CIMError(
                CIM_ERR_NOT_FOUND,
                _format("Instance to be modified does not exist in the CIM "
                        "repository: {0!A}",
                        ModifiedInstance.path))

        # Verify that the properties in the property list are exposed by the
        # creation class.
        if PropertyList:
            for pn in PropertyList:
                if pn not in creation_class.properties:
                    raise CIMError(
                        CIM_ERR_INVALID_PARAMETER,
                        _format("Property {0!A} in PropertyList does not "
                                "exist in creation class {1!A} in namespace "
                                "{2!A} of the CIM repository",
                                pn, ModifiedInstance.classname, namespace))

        # Verify that the properties in the modified instance are exposed by the
        # creation class and have the correct type-related attributes.
        # Strictly, we would only need to verify the properties to be modified
        # as reduced by the PropertyList.
        for pn in ModifiedInstance.properties:

            if pn not in creation_class.properties:
                raise CIMError(
                    CIM_ERR_INVALID_PARAMETER,
                    _format("Property {0!A} in modified instance does not "
                            "exist in its creation class {1!A} in namespace "
                            "{2!A} of the CIM repository",
                            pn, ModifiedInstance.classname, namespace))

            prop_inst = ModifiedInstance.properties[pn]
            prop_cls = creation_class.properties[pn]

            if prop_inst.type != prop_cls.type:
                raise CIMError(
                    CIM_ERR_INVALID_PARAMETER,
                    _format("Property {0!A} in modified instance has incorrect "
                            "type={1!A}, but should have "
                            "type={2!A} "
                            "according to its creation class {3!A} in "
                            "namespace {4!A} of the CIM repository",
                            pn, prop_inst.type, prop_cls.type,
                            ModifiedInstance.classname, namespace))

            if prop_inst.is_array != prop_cls.is_array:
                raise CIMError(
                    CIM_ERR_INVALID_PARAMETER,
                    _format("Property {0!A} in modified instance has incorrect "
                            "is_array={1!A}, but should have "
                            "is_array={2!A} "
                            "according to its creation class {3!A} in "
                            "namespace {4!A} of the CIM repository",
                            pn, prop_inst.is_array, prop_cls.is_array,
                            ModifiedInstance.classname, namespace))

            if prop_inst.embedded_object != prop_cls.embedded_object:
                raise CIMError(
                    CIM_ERR_INVALID_PARAMETER,
                    _format("Property {0!A} in modified instance has incorrect "
                            "embedded_object={1!A}, but should have "
                            "embedded_object={2!A} "
                            "according to its creation class {3!A} in "
                            "namespace {4!A} of the CIM repository",
                            pn, prop_inst.embedded_object,
                            prop_cls.embedded_object,
                            ModifiedInstance.classname, namespace))

            if prop_cls.qualifiers.get('key', False) and \
                    prop_inst.value != instance[pn]:
                raise CIMError(
                    CIM_ERR_INVALID_PARAMETER,
                    _format("Property {0!A} in modified instance is a key "
                            "property and thus cannot be modified, "
                            "according to its creation class {1!A} in "
                            "namespace {2!A} of the CIM repository",
                            pn, ModifiedInstance.classname, namespace))

        # The providers are guaranteed to get a deep copy of the original
        # modified instance since they may update properties.
        # TODO: Consolidate this deep copy with the shallow copy in
        #       WBEMConnection.ModifyInstance().
        modified_instance = deepcopy(ModifiedInstance)

        # Determine the provider to be used. Note that a registered provider
        # always has all responder methods for the provider type, either
        # implemented or inherited.
        provider = self.provider_registry.get_registered_provider(
            namespace, 'instance-write', ModifiedInstance.classname)
        if not provider:
            provider = self.default_instance_write_provider

        # Call the provider method.
        result = provider.ModifyInstance(
            modified_instance, IncludeQualifiers=IncludeQualifiers,
            PropertyList=PropertyList)

        # Verify provider method result.
        assert result is None

    def DeleteInstance(self, InstanceName):
        # pylint: disable=invalid-name
        """
        Dispatcher for the DeleteInstance provider method.

        This method performs validations and if successful, routes the provider
        method call either to a registered provider, or to the default provider.
        """

        # Verify the input parameter types (type errors have already been
        # raised during checks in the WBEMConnection operation).
        assert isinstance(InstanceName, CIMInstanceName)

        # Verify that the namespace exists in the CIM repository.
        namespace = InstanceName.namespace
        self.validate_namespace(namespace)

        class_store = self.cimrepository.get_class_store(namespace)
        instance_store = self.cimrepository.get_instance_store(namespace)

        # Verify that the creation class of the instance to be deleted exists
        # in the CIM repository.
        if not class_store.object_exists(InstanceName.classname):
            raise CIMError(
                CIM_ERR_INVALID_CLASS,
                _format("Creation class {0!A} of instance to be deleted does "
                        "not exist in namespace {1!A} of the CIM repository.",
                        InstanceName.classname, namespace))

        # Verify that the instance to be deleted exists in the CIM repository.
        if not instance_store.object_exists(InstanceName):
            raise CIMError(
                CIM_ERR_NOT_FOUND,
                _format("Instance to be deleted does not exist in the CIM "
                        "repository: {0!A}",
                        InstanceName))

        # Determine the provider to be used. Note that a registered provider
        # always has all responder methods for the provider type, either
        # implemented or inherited.
        provider = self.provider_registry.get_registered_provider(
            namespace, 'instance-write', InstanceName.classname)
        if not provider:
            provider = self.default_instance_write_provider

        # Call the provider method.
        result = provider.DeleteInstance(InstanceName)

        # Verify provider method result.
        assert result is None

    def InvokeMethod(self, namespace, MethodName, ObjectName, Params):
        # pylint: disable=invalid-name
        """
        Dispatcher for the InvokeMethod provider method.

        This method performs validations and if successful, routes the provider
        method call either to a registered provider, or to the default provider.
        """

        # Verify the input parameter types (type errors have already been
        # raised during checks in the WBEMConnection operation).
        assert isinstance(namespace, six.string_types)
        assert isinstance(MethodName, six.string_types)
        assert isinstance(ObjectName, (CIMInstanceName, six.string_types))
        assert isinstance(Params, NocaseDict)

        # Verify that the namespace exists in the CIM repository.
        self.validate_namespace(namespace)

        class_store = self.cimrepository.get_class_store(namespace)
        instance_store = self.cimrepository.get_instance_store(namespace)

        if isinstance(ObjectName, CIMInstanceName):
            # instance-level use

            # Get the creation class of the target instance from the CIM
            # repository, verifying that it exists.
            try:
                klass = class_store.get(ObjectName.classname)
            except KeyError:
                raise CIMError(
                    CIM_ERR_INVALID_CLASS,
                    _format("Creation class {0!A} of target instance does "
                            "not exist in namespace {1!A} of the CIM "
                            "repository.",
                            ObjectName.classname, namespace))

            # Verify that the target instance exists in the CIM repository.
            if not instance_store.object_exists(ObjectName):
                raise CIMError(
                    CIM_ERR_NOT_FOUND,
                    _format("Target instance does not exist in the CIM "
                            "repository: {0!A}",
                            ObjectName))

        else:
            # class-level use

            # Get the target class from the CIM repository, verifying that it
            # exists.
            try:
                klass = class_store.get(ObjectName)
            except KeyError:
                raise CIMError(
                    CIM_ERR_NOT_FOUND,
                    _format("Target class {0!A} does not exist in namespace "
                            "{1!A} of the CIM repository.",
                            ObjectName, namespace))

        # Verify that the class exposes the CIM method.
        if MethodName not in klass.methods:
            raise CIMError(
                CIM_ERR_METHOD_NOT_FOUND,
                _format("Method {0!A} is not exposed by class {1!A} in "
                        "namespace {2!A} of the CIM repository.",
                        MethodName, klass.classname, namespace))
        method = klass.methods[MethodName]

        if not isinstance(ObjectName, CIMInstanceName):
            # class-level use

            # Verify that the method is static.
            # Note: A similar check for instance-level use is not appropriate
            # because static methods can be invoked on instances or on classes.
            static_qual = method.qualifiers.get('Static')
            static_value = static_qual.value if static_qual else False
            if not static_value:
                raise CIMError(
                    CIM_ERR_INVALID_PARAMETER,
                    _format("Non-static method {0!A} in class {1!A} in "
                            "namespace {2!A} cannot be invoked on a class "
                            "object.",
                            MethodName, klass.classname, namespace))

        # Verify that the input parameters are defined by the method and have
        # the correct type-related attributes.
        for pn in Params:
            assert isinstance(pn, six.string_types)
            param_in = Params[pn]
            assert isinstance(param_in, CIMParameter)

            if pn not in method.parameters:
                raise CIMError(
                    CIM_ERR_INVALID_PARAMETER,
                    _format("Input parameter {0!A} specified in Params is not "
                            "defined in method {1!A} of class {2!A} in "
                            "namespace {3!A} of the CIM repository",
                            pn, MethodName, klass.classname, namespace))

            param_cls = method.parameters[pn]

            in_qual = method.qualifiers.get('In')
            in_value = in_qual.value if in_qual else True
            if not in_value:
                raise CIMError(
                    CIM_ERR_INVALID_PARAMETER,
                    _format("Input parameter {0!A} specified in Params is "
                            "defined as an output-only parameter according to "
                            "its method {1!A} of class {2!A} in namespace "
                            "{3!A} of the CIM repository",
                            pn, MethodName, klass.classname, namespace))

            if param_in.type != param_cls.type:
                raise CIMError(
                    CIM_ERR_INVALID_PARAMETER,
                    _format("Input parameter {0!A} specified in Params has "
                            "incorrect type={1!A}, but should have type={2!A} "
                            "according to its method {3!A} in class {4!A} in "
                            "namespace {5!A} of the CIM repository",
                            pn, param_in.type, param_cls.type,
                            MethodName, klass.classname, namespace))

            if param_in.is_array != param_cls.is_array:
                raise CIMError(
                    CIM_ERR_INVALID_PARAMETER,
                    _format("Input parameter {0!A} specified in Params has "
                            "incorrect is_array={1!A}, but should have "
                            "is_array={2!A} "
                            "according to its method {3!A} in class {4!A} in "
                            "namespace {5!A} of the CIM repository",
                            pn, param_in.is_array, param_cls.is_array,
                            MethodName, klass.classname, namespace))

            if param_in.embedded_object != param_cls.embedded_object:
                raise CIMError(
                    CIM_ERR_INVALID_PARAMETER,
                    _format("Input parameter {0!A} specified in Params has "
                            "incorrect embedded_object={1!A}, but should have "
                            "embedded_object={2!A} "
                            "according to its method {3!A} in class {4!A} in "
                            "namespace {5!A} of the CIM repository",
                            pn, param_in.embedded_object,
                            param_cls.embedded_object,
                            MethodName, klass.classname, namespace))

        # Determine the provider to be used.
        provider = self.provider_registry.get_registered_provider(
            namespace, 'method', klass.classname)
        if not provider:
            provider = self.default_method_provider

        # Call the provider method.
        result = provider.InvokeMethod(
            namespace, MethodName, ObjectName, Params)

        # Verify provider method result.
        assert isinstance(result, (tuple, list, dict))
        assert len(result) == 2

        return result
