#
# (C) Copyright 2018 InovaDevelopment.com
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
This module adds support for user-defined providers.  User defined
providers may be created by the use of pywbem_mock to extend the capability
of the mocker for special processing for certain classes to be mocked.

This module contains two classes:

1. ProviderDispatcher - Routes the calls for request methods that allow
user-defined providers either to the default method in InstanceWriteProvider
or to a user defined method in the provider registry.

2. InstanceWriteProvider - The default implementation for the request
responders that may include user defined providers.  This is the method that
will be called if there is no provider registered for a namespace and class
name.

User defined providers may be created for specific CIM classes and specific
namespaces to override one or more of the operation request methods defined in
:class:`~pywbem_mock:InstanceWriteProvider` with user methods defined in a
subclass of :class:`~pywbem_mock:InstanceWriteProvider`.

A user defined provider is created as follows:

1. Define the subclass of :class:`~pywbem_mock:InstanceWriteProvider` with an
__init__ method and the methods that will override any of the request methods
defined in :class:`~pywbem_mock:InstanceWriteProvider`.  Note that not all of
the requests methods in :class:`~pywbem_mock:InstanceWriteProvider` need to
be implemented, just those for which user provider will manipulate the incoming
request parameters.

Thus, a user provider can override the
:meth:`~pywbem_mock:InstanceWriteProvider.CreateInstance` method to modify the
``NewInstance`` input parameter to change properties, etc. and either submit it
to the CIM repository within the user provider or call the
:meth:`~pywbem_mock:InstanceWriteProviderCreateInstance` in the superclass to
complete submission of the ``NewInstance``.

2. Define registraton of the user provider using
:meth:`~pywbem_mock:WBEMConnection.register_provider' to define the namespaces
and classes for which the user provider will override the corresponding method
in the :class:`~pywbem_mock:InstanceWriteProvider`.  The registration of the
user provider must occur after the namespaces and classnames defined in the
registration have been added to the CIM repository.
"""

from __future__ import absolute_import, print_function

import six

from pywbem import CIMInstance, CIMInstanceName, CIMError, \
    CIM_ERR_NOT_FOUND, CIM_ERR_INVALID_PARAMETER, CIM_ERR_INVALID_CLASS, \
    CIM_ERR_ALREADY_EXISTS, CIM_ERR_METHOD_NOT_AVAILABLE, \
    CIM_ERR_METHOD_NOT_FOUND

from pywbem._utils import _format

from ._baseprovider import BaseProvider

# None of the request method names conform since they are camel case
# pylint: disable=invalid-name

__all__ = ['InstanceWriteProvider', 'MethodProvider']


def validate_inst_props(namespace, target_class, instance):
    """
    Validate that all properties in instance are in target_class and validate
    that property types are compatible.

    Finally it adds any properties from the target_class that are not in the
    instance.

    Parameters:

        namespace (:term:`string`):
          Namespace to be used.  In this method it is used only for
          documentation in exceptions

        target_class (:class:`~pywbem.CIMClass`):
          The CIM class defined in instance.classname including all qualifiers,
          superclass elements, and classorigin elements.

        instance (:class:`~pywbem.CIMInstance`):
          The CIM instance to be validated.

    Returns:
       Nothing is returned but instance may have been modified.

    Raises:
        CIMError: CIM_ERR_INVALID_PARAMETER for invalid conditions in the
        input instance.
    """

    for iprop_name in instance:
        if iprop_name not in target_class.properties:
            raise CIMError(
                CIM_ERR_INVALID_PARAMETER,
                _format("Property {0!A} specified in NewInstance is not "
                        "exposed by class {1!A} in namespace {2!A}",
                        iprop_name, target_class.classname, namespace))

        cprop = target_class.properties[iprop_name]
        iprop = instance.properties[iprop_name]
        if iprop.is_array != cprop.is_array or \
                iprop.type != cprop.type:
            raise CIMError(
                CIM_ERR_INVALID_PARAMETER,
                _format("Instance and class property {0!A} types "
                        "do not match: instance={1!A}, class={2!A}",
                        iprop_name, iprop, cprop))

        # The class and instnames are the same except for possible case
        # sensitivity. If case different, set cprop_name into new instance
        # to maintain case equality
        cprop_name = cprop.name
        if cprop_name != iprop_name:
            instance.properties[iprop_name].name = cprop_name

        # If property not in instance, add it from class and use default value
        # from class
        for cprop_name in target_class.properties:
            if cprop_name not in instance:
                default_value = target_class.properties[cprop_name]
                instance[cprop_name] = default_value


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

        self.cimrepository = cimrepository
        self.provider_registry = provider_registry

        # defines the instance of InstanceWriteProvider that will
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

        provider = self.get_registered_provider(namespace, 'instance',
                                                NewInstance.classname)

        if provider:
            providerinst = provider(self.cimrepository)
            return providerinst.CreateInstance(namespace, NewInstance)

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
        orig_instance = self.find_instance(ModifiedInstance.path,
                                           instance_store,
                                           copy_inst=False)
        if orig_instance is None:
            raise CIMError(
                CIM_ERR_NOT_FOUND,
                _format("Original Instance {0!A} not found in namespace {1!A}",
                        ModifiedInstance.path, namespace))

        provider = self.get_registered_provider(namespace,
                                                'instance',
                                                ModifiedInstance.classname)
        if provider:
            providerinst = provider(self.cimrepository)
            return providerinst.ModifyInstance(
                ModifiedInstance,
                IncludeQualifiers=IncludeQualifiers,
                PropertyList=PropertyList)

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

        provider = self.get_registered_provider(InstanceName.namespace,
                                                'instance',
                                                InstanceName.classname)
        if provider:
            providerinst = provider(self.cimrepository)
            return providerinst.DeleteInstance(InstanceName)

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

        provider = self.get_registered_provider(namespace,
                                                'method',
                                                classname)
        if provider:
            providerinst = provider(self.cimrepository)
            return providerinst.InvokeMethod(namespace, methodname,
                                             objectname, Params)

        # There is no default method provider so no user InvokeMethod
        # is defined for namespace and class, exception raise.
        raise CIMError(CIM_ERR_METHOD_NOT_AVAILABLE)


class InstanceWriteProvider(BaseProvider):
    """
    This class defines those instance provider methods that may have user-
    defined providers that override the default provider implementation in this
    class.

    User providers are defined by creating a subclass of this class and
    defining a new provider method for one of the methods in this class with
    the same signature.

    Note that user-defined providers may, in turn, call the default providers
    in this class.

    """
    def __init__(self, cimrepository=None):
        """
        Initialize the instance variables.

        Parameters:

          cimrepository (:class:`~pywbem_mock.InMemoryRepository` or subclass):
            Defines the repository to be used by request responders.  The
            repository is fully initialized.
        """

        if cimrepository:
            self.cimrepository = cimrepository

    ####################################################################
    #
    #   CreateInstance server request
    #
    ####################################################################

    def CreateInstance(self, namespace, NewInstance):
        """
        Implements a WBEM server responder for
        :meth:`pywbem.WBEMConnection.CreateInstance`.

        Create a CIM instance in the local CIM repository of this class.

        The input parameters must have been validated before this method
        is called including:

        1. Namespace is valid in CIM repository.
        2. The NewInstance is a valid CIM Instance.
        3. All key properties defined in the class  of NewInstnace are defined
           in NewInstance. This method cannot add properties or property
           values to NewInstance.
        4. There are no properties in NewInstance that are not in the
           corresponding class.
        5. NewInstance path must not exist in the CIM repository.

        Parameters:

          namespace (:term:`string`):
            The name of the CIM namespace in the CIM repository (case
            insensitive). Must not be `None`. Leading or trailing slash
            characters are ignored.

          NewInstance (:class:`~pywbem.CIMInstance`):
            A representation of the CIM instance to be created.

            The `classname` attribute of this object specifies the creation
            class for the new instance.

            The namespace of the `path` attribute must be `None` or the
            same as the namespace parameter.

            The `properties` attribute of this object specifies initial
            property values for the new CIM instance.

            Instance-level qualifiers have been deprecated in CIM, so any
            qualifier values specified using the `qualifiers` attribute
            of this object are ignored.

        Returns:
            CIMInstanceName with the server defined instance path
            for the new instance.

        Raises:

            CIMError: CIM_ERR_ALREADY_EXISTS
              The instance defined by namespace and instance name already
              exists.

            CIMError: CIM_ERR_INVALID_CLASS
              The class defined in NewInstance  does not exist in the
              namespace.
        """

        new_instance = NewInstance

        self.validate_namespace(namespace)
        instance_store = self.get_instance_store(namespace)

        # Requires corresponding class to build path to be returned
        target_class = self.get_class(namespace,
                                      new_instance.classname,
                                      local_only=False,
                                      include_qualifiers=True,
                                      include_classorigin=True)

        # Handle namespace creation, currently hard coded.
        # Issue #2062 TODO/AM 8/18 Generalize the hard coded handling into
        # provider concept
        classname_lower = new_instance.classname.lower()
        if classname_lower == 'pg_namespace':
            ns_classname = 'PG_Namespace'
        elif classname_lower == 'cim_namespace':
            ns_classname = 'CIM_Namespace'
        else:
            ns_classname = None
        if ns_classname:
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

            # These values must match those in
            # tests/unittest/utils/wbemserver_mock.py.
            new_instance['CreationClassName'] = ns_classname
            new_instance['ObjectManagerName'] = 'MyFakeObjectManager'
            new_instance['ObjectManagerCreationClassName'] = \
                'CIM_ObjectManager'
            new_instance['SystemName'] = 'Mock_Test_WBEMServerTest'
            new_instance['SystemCreationClassName'] = 'CIM_ComputerSystem'

        # Test all key properties in instance. The CIM repository
        # cannot add values for key properties and does
        # not allow creating key properties from class defaults.
        key_props = [p.name for p in six.itervalues(target_class.properties)
                     if 'key' in p.qualifiers]
        for pn in key_props:
            if pn not in new_instance:
                raise CIMError(
                    CIM_ERR_INVALID_PARAMETER,
                    _format("Key property {0!A} not in NewInstance ", pn))

        # Exception if property in instance but not class or types do not
        # match
        validate_inst_props(namespace, target_class, new_instance)

        # Build instance path from values in the instance.
        new_instance.path = CIMInstanceName.from_instance(
            target_class,
            new_instance,
            namespace=namespace)

        # Reflect the new namespace in the  CIM repository
        # TODO/ks: This should not be necessary here when we have provider
        if ns_classname:
            self.add_namespace(new_namespace)

        # Store the new instance in the  CIM repository if it is not
        # already in the repository
        try:
            instance_store.create(new_instance.path, new_instance)
        except ValueError:
            raise CIMError(
                CIM_ERR_ALREADY_EXISTS,
                _format("NewInstance {0!A} already exists in namespace "
                        "{1!A}.", new_instance.path, namespace))

        # Create instance returns model path
        return new_instance.path.copy()

    ####################################################################
    #
    #   ModifyInstance server request
    #
    ####################################################################

    def ModifyInstance(self, ModifiedInstance,
                       IncludeQualifiers=None, PropertyList=None):
        # pylint: disable=invalid-name,line-too-long
        """
        Implements a WBEM server responder for
        :meth:`pywbem.WBEMConnection.CreateInstance`.

        Modify a CIM instance in the CIM repository.

        NOTE: This method includes namespace within the path element
        of the ModifiedInstance rather than as a separate input parameter.

          ModifiedInstance (:class:`~pywbem.CIMInstance`):
            A representation of the modified instance, also indicating its
            instance path.

            The `path` attribute of this object identifies the instance to be
            modified. Its `keybindings` attribute is required. Its
            `namespace` attribute must be the namespace containing the instance
            to be modified. Its `host` attribute will be ignored.

            The `classname` attribute of the instance path and the `classname`
            attribute of the instance must specify the same class name.

            The properties defined in this object specify the new property
            values (including `None` for NULL). If a property is designated to
            be modified but is not specified in this object, the WBEM server
            will use the default value of the property declaration if specified
            (including `None`), and otherwise may update the property to any
            value (including `None`).

          IncludeQualifiers (:class:`py:bool`):
            This parameter is ignored by this method.
            Indicates that qualifiers are to be modified as specified in the
            `ModifiedInstance` parameter, as follows:

            * If `False`, qualifiers not modified.
            * If `True`, qualifiers are modified if the WBEM server implements
              support for this parameter.
            * If `None`, the  :term:`DSP0200` defined default is `True`.

            This parameter has been deprecated in :term:`DSP0200`. Clients
            cannot rely on qualifiers to be modified.

          PropertyList (:term:`string` or :term:`py:iterable` of :term:`string`):
            This parameter defines which properties are designated to be
            modified.

            This parameter is an iterable specifying the names of the
            properties, or a string that specifies a single property name. In
            all cases, the property names are matched case insensitively.
            The specified properties are designated to be modified. Properties
            not specified are not designated to be modified.

            An empty iterable indicates that no properties are designated to be
            modified.

            If `None`, DSP0200 states that the properties with values different
            from the current values in the instance are designated to be
            modified, but for all practical purposes this is equivalent to
            stating that all properties exposed by the instance are designated
            to be modified.

        Raises:

            CIMError: CIM_ERR_ALREADY_EXISTS,
            CIMError: CIM_ERR_INVALID_CLASS
            CIMError: CIM_ERR_INVALID_PARAMETER
            CIMError: CIM_ERR_NAMESPACE_NOT_FOUND
        """  # noqa: E501
        # pylint: disable=invalid-name,line-too-long

        # get the namespace from the Modified instance
        namespace = ModifiedInstance.path.namespace

        instance_store = self.get_instance_store(namespace)
        modified_instance = ModifiedInstance.copy()

        # Return if empty property list, nothing would be changed
        if PropertyList is not None and not PropertyList:
            return

        # Get class including inherited properties from CIM repository
        try:
            target_class = self.get_class(
                namespace,
                modified_instance.classname,
                local_only=False,
                include_qualifiers=True,
                include_classorigin=True,
                property_list=None)
        except CIMError as ce:
            if ce.status_code in [CIM_ERR_NOT_FOUND, CIM_ERR_INVALID_CLASS]:
                raise CIMError(
                    CIM_ERR_INVALID_CLASS,
                    _format("Cannot modify instance because its creation "
                            "class {0!A} does not exist in namespace {1!A}.",
                            modified_instance.classname, namespace))
            raise

        # Get original instance in datastore.
        orig_instance = self.find_instance(modified_instance.path,
                                           instance_store,
                                           copy_inst=True)
        if orig_instance is None:
            raise CIMError(
                CIM_ERR_NOT_FOUND,
                _format("Original Instance {0!A} not found in namespace {1!A}",
                        modified_instance.path, namespace))

        # Remove duplicate properties from property_list
        property_list = PropertyList
        if property_list:
            if len(property_list) != len(set(property_list)):
                property_list = list(set(property_list))

        # Test that all properties in modified instance and property list
        # are in the class
        if property_list:
            for p in property_list:
                if p not in target_class.properties:
                    raise CIMError(
                        CIM_ERR_INVALID_PARAMETER,
                        _format("Property {0!A} in PropertyList not in class "
                                "{1!A}", p, modified_instance.classname))
        for p in modified_instance:
            if p not in target_class.properties:
                raise CIMError(
                    CIM_ERR_INVALID_PARAMETER,
                    _format("Property {0!A} in ModifiedInstance not in class "
                            "{1!A}", p, modified_instance.classname))

        # Set the class value for properties in the property list but not
        # in the modified_instance. This sets just the value component.
        mod_inst_props = set([k.lower() for k in modified_instance.keys()])
        cl_props = [pn.lower() for pn in target_class.properties]
        chngd_props = mod_inst_props.difference(set(cl_props))
        if chngd_props:
            for prop in chngd_props:
                modified_instance[prop] = \
                    target_class.properties[prop].value

        # Remove all properties that do not change value between original
        # instance and modified instance
        for p in list(modified_instance):
            if orig_instance[p] == modified_instance[p]:
                del modified_instance[p]

        # Confirm no key properties in remaining modified instance
        key_props = [p.name for p in six.itervalues(target_class.properties)
                     if 'key' in p.qualifiers]
        for p in key_props:
            if p in modified_instance:
                raise CIMError(
                    CIM_ERR_INVALID_PARAMETER,
                    _format("ModifyInstance cannot modify key property {0!A}",
                            p))

        # Remove any properties from modified instance not in the property_list
        if property_list:
            for p in list(modified_instance):  # create list before loop
                if p not in property_list:
                    del modified_instance[p]

        # Exception if property in instance but not class or types do not
        # match
        for pname in modified_instance:
            if pname not in target_class.properties:
                raise CIMError(
                    CIM_ERR_INVALID_PARAMETER,
                    _format("Property {0!A} specified in ModifiedInstance is "
                            "not exposed by class {1!A} in namespace {2!A}",
                            pname, target_class.classname, namespace))

            classprop = target_class.properties[pname]
            instprop = modified_instance.properties[pname]
            if instprop.is_array != classprop.is_array \
                    or instprop.type != classprop.type \
                    or instprop.array_size != classprop.array_size:
                raise CIMError(
                    CIM_ERR_INVALID_PARAMETER,
                    _format("Instance and class property name={0!A} type "
                            "or other attributes do not match: "
                            "instance={1!A}, class={2!A}",
                            pname, instprop, classprop))
            # If case of modified_instance property != case of class property
            # change the name in the modified_instance
            if instprop.name != classprop.name:
                modified_instance.properties[instprop.name].name = \
                    classprop.name

        # Modify the value of properties in the repo with those from
        # modified instance inserted into the original instance
        orig_instance.update(modified_instance.properties)
        instance_store.update(modified_instance.path, orig_instance)

        return

    ####################################################################
    #
    #   DeleteInstance server request
    #
    ####################################################################

    def DeleteInstance(self, InstanceName):
        """
        Implements a WBEM server responder for
        :meth:`pywbem.WBEMConnection.DeleteInstance`.

        This method deletes a single instance from the CIM repository based on
        the  InstanceName parameter.

        It does not attempt to delete referencing instances (associations,
        etc.) that reference this instance.

        If the creation class of the instance to be deleted is PG_Namespace or
        CIM_Namespace, then the namespace identified by the 'Name' property
        of the instance is being deleted in the CIM repository in addition to
        the CIM instance.

        The input parameters must have been validated before this method is
        called including:

          1. Valid namespace in the repository
          2. Instance exists in the repository

        NOTE: This method includes namespace within the InstanceName
        rather than as a separate input argument

        Parameters:

          InstanceName (:class:`~pywbem.CIMInstanceName`):
            The instance path of the instance to be deleted.
            The instance path of the instance to be retrieved  with the
            following attributes:

            * `classname`: Name of the creation class of the instance.
            * `keybindings`: Keybindings of the instance.
            * `namespace`: Name of the CIM namespace containing the instance.
              Must not be None.
            * `host`: value ignored.

        Raises:
            CIMError: CIM_ERR_INVALID_NAMESPACE
            CIMError: CIM_ERR_INVALID_CLASS
            CIMError: CIM_ERR_NOT_FOUND
        """

        instance_store = self.get_instance_store(InstanceName.namespace)

        # Handle namespace deletion, currently hard coded.
        # Issue #2062 TODO/AM 8/18 Generalize the hard coded handling into
        # provider concept
        classname_lower = InstanceName.classname.lower()
        if classname_lower == 'pg_namespace':
            ns_classname = 'PG_Namespace'
        elif classname_lower == 'cim_namespace':
            ns_classname = 'CIM_Namespace'
        else:
            ns_classname = None
        if ns_classname:
            namespace = InstanceName.keybindings['Name']

            # Reflect the namespace deletion in the CIM repository
            # This will check the namespace for being empty.
            self.remove_namespace(namespace)

        # Delete the instance from the CIM repository
        instance_store.delete(InstanceName)


class MethodProvider(BaseProvider):
    """
    This class defines those instance provider methods that may have user-
    defined providers that override the default provider implementation in this
    class.

    User providers are defined by creating a subclass of this class and
    defining an InvokeMethod based on the method in this class.

    """
    def __init__(self, cimrepository=None):
        """
        Initialize the instance variables.

        Parameters:

          cimrepository (:class:`~pywbem_mock.InMemoryRepository` or subclass):
            Defines the repository to be used by request responders.  The
            repository is fully initialized.
        """

        if cimrepository:
            self.cimrepository = cimrepository

    ####################################################################
    #
    #   Server responder for InvokeMethod.
    #
    ####################################################################

    def InvokeMethod(self, namespace, methodname, objectname, Params):
        # pylint: disable=invalid-name
        """
        Defines the API and return for a mock WBEM server responder for
        :meth:`~pywbem.WBEMConnection.InvokeMethod`

        This method should never be called.

        This responder calls a function defined by an entry in the methods
        repository. The return from that function is returned to the user.

        Parameters:

          MethodName (:term:`string`):
            Name of the method to be invoked (case independent).

          ObjectName:
            The object path of the target object, as follows:

            * For instance-level use: The instance path of the target
              instance, as a :class:`~pywbem.CIMInstanceName` object.
              If this object does not specify a namespace, the default namespace
              of the connection is used.
              Its `namespace`, and `host` attributes will be ignored.

            * For class-level use: The class path of the target class, as a
              :term:`string`:

              The string is interpreted as a class name in the default
              namespace of the connection (case independent).

          Params (:term:`py:iterable`):
            An iterable of input parameter values for the CIM method. Each item
            in the iterable is a single parameter value and is:

            * :class:`~pywbem.CIMParameter` representing a parameter value. The
              `name`, `value`, `type` and `embedded_object` attributes of this
              object are used.

        Returns:

            A :func:`py:tuple` of (returnvalue, outparams), with these
            tuple items:

            * returnvalue (:term:`CIM data type`):
              Return value of the CIM method.
            * outparams (:term:`py:iterable` of :class:`~pywbem.CIMParameter`):
              Each item represents a single output parameter of the CIM method.
              The :class:`~pywbem.CIMParameter` objects must have at least
              the following properties set:

                * name (:term:`string`): Parameter name (case independent).
                * type (:term:`string`): CIM data type of the parameter.
                * value (:term:`CIM data type`): Parameter value.
        """
        raise NotImplementedError
