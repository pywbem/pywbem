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

from copy import deepcopy
import six
try:
    from collections.abc import Mapping, Sequence
except ImportError:  # py2
    # pylint: disable=deprecated-class
    from collections import Mapping, Sequence

from pywbem import CIMInstance, CIMInstanceName, CIMClass, CIMClassName, \
    CIMParameter, CIMError, CIM_ERR_NOT_FOUND, CIM_ERR_INVALID_PARAMETER, \
    CIM_ERR_INVALID_CLASS, CIM_ERR_METHOD_NOT_FOUND, cimtype, CIM_ERR_FAILED

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

    def _validate_property(
            self, prop_name, instance, creation_class, namespace, class_store):
        """
        Validate a property of an instance against its declaration in a class.
        """

        if prop_name not in creation_class.properties:
            raise CIMError(
                CIM_ERR_INVALID_PARAMETER,
                _format("Property {0!A} in the instance does not exist in its "
                        "creation class {1!A} in namespace {2!A} of the CIM "
                        "repository",
                        prop_name, instance.classname, namespace))

        prop_inst = instance.properties[prop_name]
        prop_cls = creation_class.properties[prop_name]

        if prop_inst.type != prop_cls.type:
            raise CIMError(
                CIM_ERR_INVALID_PARAMETER,
                _format("Property {0!A} in the instance has incorrect "
                        "type={1!A}, but should have type={2!A} according to "
                        "its creation class {3!A} in namespace {4!A} of the "
                        "CIM repository",
                        prop_name, prop_inst.type, prop_cls.type,
                        instance.classname, namespace))

        if prop_inst.is_array != prop_cls.is_array:
            raise CIMError(
                CIM_ERR_INVALID_PARAMETER,
                _format("Property {0!A} in the instance has incorrect "
                        "is_array={1!A}, but should have is_array={2!A} "
                        "according to its creation class {3!A} in namespace "
                        "{4!A} of the CIM repository",
                        prop_name, prop_inst.is_array, prop_cls.is_array,
                        instance.classname, namespace))

        if isinstance(prop_inst.value, CIMInstance):
            emb_classname_inst = prop_inst.value.classname
            if 'EmbeddedInstance' in prop_cls.qualifiers:
                ei_qual = prop_cls.qualifiers['EmbeddedInstance']
                emb_classname_cls = ei_qual.value
                if not self.is_subclass(
                        emb_classname_inst, emb_classname_cls, class_store):
                    raise CIMError(
                        CIM_ERR_INVALID_PARAMETER,
                        _format("Property {0!A} in the instance is an embedded "
                                "instance of class {1!A}, but should be of "
                                "class {2!A} according to its creation class "
                                "{3!A} in namespace {4!A} of the CIM "
                                "repository",
                                prop_name, emb_classname_inst,
                                emb_classname_cls,
                                instance.classname, namespace))
            elif 'EmbeddedObject' not in prop_cls.qualifiers:
                raise CIMError(
                    CIM_ERR_INVALID_PARAMETER,
                    _format("Property {0!A} in the instance is an embedded "
                            "instance of class {1!A}, but the property "
                            "declaration has neither EmbeddedInstance nor "
                            "EmbeddedObject set in its creation class {2!A} in "
                            "namespace {3!A} of the CIM repository",
                            prop_name, emb_classname_inst,
                            instance.classname, namespace))

        if isinstance(prop_inst.value, CIMClass):
            emb_classname_inst = prop_inst.value.classname
            if 'EmbeddedObject' not in prop_cls.qualifiers:
                raise CIMError(
                    CIM_ERR_INVALID_PARAMETER,
                    _format("Property {0!A} in the instance is an embedded "
                            "class {1!A}, but the property declaration does "
                            "not have EmbeddedObject set in its creation class "
                            "{2!A} in namespace {3!A} of the CIM repository",
                            prop_name, emb_classname_inst,
                            instance.classname, namespace))

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

        if "Abstract" in creation_class.qualifiers:
            raise CIMError(
                CIM_ERR_FAILED,
                _format("CreateInstance failed. Cannot instantiate abstract "
                        "class {0!A} in Namespace {1!A}.",
                        NewInstance.classname, namespace))

        # Verify that the properties in the new instance are exposed by the
        # creation class and have the correct type-related attributes.
        for pn in NewInstance.properties:
            self._validate_property(
                pn, NewInstance, creation_class, namespace, class_store)

        # The providers are guaranteed to get a deep copy of the original
        # new instance since they may update properties.
        new_instance = deepcopy(NewInstance)

        # Adjust the lexical case of the property names in the new instance
        # to match the lexical case of the property definitions in the creation
        # class.
        for inst_pn in new_instance.properties:
            inst_prop = new_instance.properties[inst_pn]
            cls_pn = creation_class.properties[inst_pn].name
            if inst_pn != cls_pn:
                inst_prop.name = cls_pn  # modifies new_instance

        # Determine the provider to be used. Note that a registered provider
        # always has all provider methods for the provider type, either
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

        # Verify equality of the class names in the modified instance.
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
        # creation class, and reduce property list to be unique.
        if PropertyList is None:
            property_list = None
        else:
            property_list = []
            property_dict = NocaseDict()
            for pn in PropertyList:
                if pn not in creation_class.properties:
                    raise CIMError(
                        CIM_ERR_INVALID_PARAMETER,
                        _format("Property {0!A} in PropertyList does not "
                                "exist in creation class {1!A} in namespace "
                                "{2!A} of the CIM repository",
                                pn, ModifiedInstance.classname, namespace))
                if pn not in property_dict:
                    property_dict[pn] = True
                    property_list.append(pn)

        # Verify that the properties in the modified instance are exposed by the
        # creation class and have the correct type-related attributes.
        # Strictly, we would only need to verify the properties to be modified
        # as reduced by the PropertyList.

        for pn in ModifiedInstance.properties:

            self._validate_property(
                pn, ModifiedInstance, creation_class, namespace, class_store)

            prop_inst = ModifiedInstance.properties[pn]
            prop_cls = creation_class.properties[pn]
            # See issue #2449. This test never executed since if the key
            # properties changed, the original instance get would have already
            # failed.
            if prop_cls.qualifiers.get('key', False) and \
                    prop_inst.value != instance[pn]:
                raise CIMError(
                    CIM_ERR_INVALID_PARAMETER,
                    _format("Property {0!A} in the instance is a key "
                            "property and thus cannot be modified, "
                            "according to its creation class {1!A} in "
                            "namespace {2!A} of the CIM repository",
                            pn, ModifiedInstance.classname, namespace))

        # The providers are guaranteed to get a deep copy of the original
        # modified instance since they may update properties.
        modified_instance = deepcopy(ModifiedInstance)

        # Reduce modified_instance to have just the properties to be modified
        if property_list is not None:

            # Add class default values for properties not specified in
            # ModifiedInstance.
            for pn in property_list:
                if pn not in modified_instance:
                    # If the property in the class does not have a default
                    # value, it is None.
                    modified_instance[pn] = creation_class.properties[pn].value

            # Remove properties from modified_instance that are not in
            # PropertyList.
            for pn in list(modified_instance):
                if pn not in property_dict:
                    del modified_instance[pn]

        # Adjust the lexical case of the properties in the modified instance to
        # the lexical case they have in the creation class.
        for pn in modified_instance.properties:
            inst_prop = modified_instance.properties[pn]
            cl_prop = creation_class.properties[pn]
            if inst_prop.name != cl_prop.name:
                inst_prop.name = cl_prop.name  # changes modified_instance

        # Determine the provider to be used. Note that a registered provider
        # always has all provider methods for the provider type, either
        # implemented or inherited.
        provider = self.provider_registry.get_registered_provider(
            namespace, 'instance-write', modified_instance.classname)
        if not provider:
            provider = self.default_instance_write_provider

        # Call the provider method.
        result = provider.ModifyInstance(
            modified_instance, IncludeQualifiers=IncludeQualifiers)

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
        # always has all provider methods for the provider type, either
        # implemented or inherited.
        provider = self.provider_registry.get_registered_provider(
            namespace, 'instance-write', InstanceName.classname)
        if not provider:
            provider = self.default_instance_write_provider

        # Call the provider method.
        result = provider.DeleteInstance(InstanceName)

        # Verify provider method result.
        assert result is None

    def InvokeMethod(self, methodname, localobject, params):
        # pylint: disable=invalid-name
        """
        Dispatcher for the InvokeMethod provider method.

        This method performs validations and if successful, routes the provider
        method call either to a registered provider, or to the default provider.

        Parameters:

          methodname (string): Method name

          localobject (CIMInstanceName or CIMClassName): Target object, with
            namespace set. Types are validated.

          params (NocaseDict): Input parameters, as follows:
            * key (string): Parameter name.
            * value (CIMParameter): Parameter value.
            Types are validated.

        Returns:

          A tuple of (returnvalue, outparams), with these tuple items:

            * returnvalue (CIM data type): Return value.

            * outparams (NocaseDict): Output parameters, with:
              * key (string): Parameter name
              * value (CIM data type): Parameter value
        """

        namespace = localobject.namespace

        # Verify the input parameter types (type errors have already been
        # raised during checks in WBEMConnection.InvokeMethod(), and in
        # FakedWBEMConnection._mock_methodcall()).
        assert isinstance(namespace, six.string_types)
        assert isinstance(methodname, six.string_types)
        assert isinstance(localobject, (CIMInstanceName, CIMClassName))
        assert isinstance(params, NocaseDict)

        # Verify that the namespace exists in the CIM repository.
        self.validate_namespace(namespace)

        class_store = self.cimrepository.get_class_store(namespace)
        instance_store = self.cimrepository.get_instance_store(namespace)

        if isinstance(localobject, CIMInstanceName):
            # instance-level use

            # Get the creation class of the target instance from the CIM
            # repository, verifying that it exists.
            try:
                klass = class_store.get(localobject.classname)
            except KeyError:
                raise CIMError(
                    CIM_ERR_INVALID_CLASS,
                    _format("Creation class {0!A} of target instance does "
                            "not exist in namespace {1!A} of the CIM "
                            "repository.",
                            localobject.classname, namespace))

            # Verify that the target instance exists in the CIM repository.
            if not instance_store.object_exists(localobject):
                raise CIMError(
                    CIM_ERR_NOT_FOUND,
                    _format("Target instance does not exist in the CIM "
                            "repository: {0!A}",
                            localobject))

        else:
            assert isinstance(localobject, CIMClassName)
            # class-level use

            # Get the target class from the CIM repository, verifying that it
            # exists.
            try:
                klass = class_store.get(localobject.classname)
            except KeyError:
                raise CIMError(
                    CIM_ERR_NOT_FOUND,
                    _format("Target class {0!A} does not exist in namespace "
                            "{1!A} of the CIM repository.",
                            localobject.classname, namespace))

        # Verify that the class exposes the CIM method.
        if methodname not in klass.methods:
            raise CIMError(
                CIM_ERR_METHOD_NOT_FOUND,
                _format("Method {0!A} is not exposed by class {1!A} in "
                        "namespace {2!A} of the CIM repository.",
                        methodname, klass.classname, namespace))
        method = klass.methods[methodname]

        if isinstance(localobject, CIMClassName):
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
                            methodname, klass.classname, namespace))

        # Verify that the input parameters are defined by the method and have
        # the correct type-related attributes.
        for pn in params:
            assert isinstance(pn, six.string_types)
            param_in = params[pn]
            assert isinstance(param_in, CIMParameter)

            if pn not in method.parameters:
                raise CIMError(
                    CIM_ERR_INVALID_PARAMETER,
                    _format("The specified input parameter {0!A} is not "
                            "defined in method {1!A} of class {2!A} in "
                            "namespace {3!A} of the CIM repository",
                            pn, methodname, klass.classname, namespace))

            param_cls = method.parameters[pn]

            in_qual = method.qualifiers.get('In')
            in_value = in_qual.value if in_qual else True
            if not in_value:
                raise CIMError(
                    CIM_ERR_INVALID_PARAMETER,
                    _format("The specified input parameter {0!A} is "
                            "defined as an output-only parameter according to "
                            "its method {1!A} of class {2!A} in namespace "
                            "{3!A} of the CIM repository",
                            pn, methodname, klass.classname, namespace))

            if param_in.type != param_cls.type:
                raise CIMError(
                    CIM_ERR_INVALID_PARAMETER,
                    _format("The specified input parameter {0!A} has "
                            "incorrect type={1!A}, but should have type={2!A} "
                            "according to its method {3!A} in class {4!A} in "
                            "namespace {5!A} of the CIM repository",
                            pn, param_in.type, param_cls.type,
                            methodname, klass.classname, namespace))

            if param_in.is_array != param_cls.is_array:
                raise CIMError(
                    CIM_ERR_INVALID_PARAMETER,
                    _format("The specified input parameter {0!A} has "
                            "incorrect is_array={1!A}, but should have "
                            "is_array={2!A} "
                            "according to its method {3!A} in class {4!A} in "
                            "namespace {5!A} of the CIM repository",
                            pn, param_in.is_array, param_cls.is_array,
                            methodname, klass.classname, namespace))

            if param_in.embedded_object != param_cls.embedded_object:
                raise CIMError(
                    CIM_ERR_INVALID_PARAMETER,
                    _format("The specified input parameter {0!A} has "
                            "incorrect embedded_object={1!A}, but should have "
                            "embedded_object={2!A} "
                            "according to its method {3!A} in class {4!A} in "
                            "namespace {5!A} of the CIM repository",
                            pn, param_in.embedded_object,
                            param_cls.embedded_object,
                            methodname, klass.classname, namespace))

        # Determine the provider to be used.
        provider = self.provider_registry.get_registered_provider(
            namespace, 'method', klass.classname)
        if not provider:
            provider = self.default_method_provider

        # Call the provider method
        result = provider.InvokeMethod(methodname, localobject, params)

        # Verify provider method result
        if not isinstance(result, (list, tuple)):
            raise TypeError(
                _format("InvokeMethod provider method returned invalid type: "
                        "{0}. Must return list/tuple (return value, output "
                        "parameters)",
                        type(result)))
        if len(result) != 2:
            raise ValueError(
                _format("InvokeMethod provider method returned invalid number "
                        "of items: {0}. Must be list/tuple (return value, "
                        "output parameters)",
                        len(result)))
        return_value = result[0]
        output_params = result[1]

        # Map the more flexible way output parameters can be returned from
        # the provider method to what _mock_methodcall() expects
        output_params_dict = NocaseDict()
        if isinstance(output_params, Sequence):
            # sequence of CIMParameter
            for param in output_params:
                if not isinstance(param, CIMParameter):
                    raise TypeError(
                        _format("InvokeMethod provider method returned invalid "
                                "type for item in output parameters "
                                "sequence: {0}. Item type must be "
                                "CIMParameter",
                                type(param)))
                output_params_dict[param.name] = param.value
        elif isinstance(output_params, Mapping):
            # mapping of name:value or name:CIMParameter
            for pname in output_params:
                pvalue = output_params[pname]
                if isinstance(pvalue, CIMParameter):
                    pvalue = pvalue.value
                else:
                    # Perform check for valid CIM data type:
                    try:
                        cimtype(pvalue)
                    except TypeError:
                        new_exc = TypeError(
                            _format("InvokeMethod provider method returned "
                                    "invalid type for value in output "
                                    "parameters mapping: {0}. Value type must "
                                    "be a CIM data type or CIMParameter",
                                    type(pvalue)))
                        new_exc.__cause__ = None
                        raise new_exc
                    except ValueError:
                        # Empty array
                        pass
                output_params_dict[pname] = pvalue
        else:
            raise TypeError(
                _format("InvokeMethod provider method returned invalid type "
                        "for output parameters: {0}. Must be "
                        "Sequence(CIMParameter) or "
                        "Mapping(name: value/CIMParameter)",
                        type(output_params)))

        return return_value, output_params_dict
