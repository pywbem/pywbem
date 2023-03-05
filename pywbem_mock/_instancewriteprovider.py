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
The :class:`~pywbem_mock.InstanceWriteProvider` class provides the default
implementations of the ``CreateInstance``, ``ModifyInstance`` and
``DeleteInstance`` provider methods by means of
:meth:`~pywbem_mock.InstanceWriteProvider.CreateInstance`,
:meth:`~pywbem_mock.InstanceWriteProvider.ModifyInstance`, and
:meth:`~pywbem_mock.InstanceWriteProvider.DeleteInstance`.

A user-defined instance write provider may implement some or all of these
provider methods. The method descriptions linked above provide a detailed
definition of the input parameters, return values, and required behavior.

The following is a simple example of a user-defined instance write provider
that serves the 'CIM_Foo' and 'CIM_FooFoo' classes and implements
``CreateInstance`` for the purpose of setting a value for the 'InstanceID' key
property:

.. code-block:: python

    import uuid
    from pywbem_mock import InstanceWriteProvider

    class MyInstanceProvider(InstanceWriteProvider):

        # CIM classes served by this provider
        provider_classnames = ['CIM_Foo', 'CIM_FooFoo']

        def CreateInstance(self, namespace, new_instance):
            new_instance.properties["InstanceID"] = \\
                "{}.{}".format(new_instance.classname, uuid.uuid4())
            return super(MyInstanceProvider, self).CreateInstance(
                namespace, new_instance)

Because the provider in this example does not implement the
``ModifyInstance`` and ``DeleteInstance`` methods, these operations will
use their default implementations from
:class:`~pywbem_mock.InstanceWriteProvider`.

NOTE: Bidirectional association support was added in pywbem version 1.5.
originally the association was visible only in the target namespace for the
CreateInstance so Associations and References only handled reference properties
in that namespace.

This instance provider handles association instances that cross namespaces.
Since the association must be available in all of the namespaces defined by the
reference properties of a new instance (References and Associations requests
can be issued using any of the reference properties in the instance), the
CreateInstance creates the association instance in each namespace defined in a
reference property of the instance (it creates shadow instances of the
association in each namespace defined by a reference property in the
association), ModifyInstance modifies the instance and shadow instances, and
DeleteInstance deletes the instance and shadow instances. References and
Association requests can be executed on instances defined in any namespace
where the association is defined.

These shadow instances are visible in each affected namespaces with the
GetInstance and EnumerateInstance requests.

This is transparent. The association instance is visible in each of the
affected namespaces and References and Associations requests can be issued
using any of the reference properties and the operation source instance.

The provider in this example does not need to implement an ``__init__()``
method, because no additional init parameters are needed.
"""

from __future__ import absolute_import, print_function

from pywbem._nocasedict import NocaseDict

from pywbem import CIMInstanceName, CIMInstance, CIMError, CIMClass, \
    CIM_ERR_INVALID_PARAMETER, CIM_ERR_ALREADY_EXISTS, CIM_ERR_INVALID_CLASS, \
    CIM_ERR_NOT_FOUND

from pywbem._utils import _format

from ._baseprovider import BaseProvider

# None of the request method names conform since they are camel case
# pylint: disable=invalid-name

__all__ = ['InstanceWriteProvider']


class InstanceWriteProvider(BaseProvider):
    """
    This class defines those instance provider methods that may have
    user-defined providers that override the default provider implementation
    in this class.

    *New in pywbem 1.0 as experimental and finalized in 1.2.*

    User providers are defined by creating a subclass of this class and
    defining a new provider method for one of the methods in this class with
    the same signature.

    Note that user-defined providers may, in turn, call the default providers
    in this class to complete the CreateInstance, ModifyInstance, or
    DeleteInstance, in particular for instance providers that dynamically
    Create or Modify an instance.
    """

    #: :term:`string`: Keyword defining the type of request the provider will
    #: service. The type for this provider class is predefined as 'instance'.
    provider_type = 'instance-write'

    def __init__(self, cimrepository=None):
        """
        Parameters:

          cimrepository (:class:`~pywbem_mock.BaseRepository` or subclass):
            The CIM repository to be used by the provider.
        """
        super(InstanceWriteProvider, self).__init__(cimrepository)

    def CreateInstance(self, namespace, new_instance):
        """
        Default provider method for
        :meth:`pywbem.WBEMConnection.CreateInstance`.

        Create a new CIM instance in the CIM repository of the mock WBEM server.

        Validation already performed by the provider dispatcher that calls
        this provider method:

        - The provider method is called only for the registered class and
          namespace (only applies to user-defined providers).

        - The Python types of all input parameters to this provider method are
          as specified below.

        - The namespace exists in the CIM repository.

        - The creation class of the new instance exists in the namespace
          in the CIM repository.

        - All properties specified in the new instance are exposed (i.e.
          defined and inherited with any overrides resolved) by the creation
          class in the CIM repository, and have the same type-related
          attributes (i.e. type, is_array, embedded_object).

        - The creation class of the new instance must not be an abstract class.

        Validation that should be performed by this provider method:

        - new_instance does not specify any properties that are not
          allowed to be initialized by the client, depending on the model
          implemented by the provider.

        - new_instance specifies all key properties needed by the
          provider, depending on the model implemented by the provider.
          The CIM repository will reject any new instance that does not have
          all key properties specified.

        - The new instance (i.e. an instance with the new instance path) does
          not exist in the CIM repository.
          This validation needs to be done by the provider because the
          determination of the key properties for the new instance path may
          depend on the model implemented by the provider.
          The CIM repository will reject the creation of instances that already
          exist, so this check can be delegated to the repository once the
          new instance path has been determined.

        - If new_instance is an association, the reference properties must
          define existing end-point paths to instances or have value
          None.

        Parameters:

          namespace (:term:`string`):
            The name of the CIM namespace in which the CIM instance is to be
            created, in any lexical case, and with leading and trailing slash
            characters removed.

          new_instance (:class:`~pywbem.CIMInstance`):
            A representation of the CIM instance to be created.

            This object is a deep copy of the original client parameter, and may
            be modified by the provider as needed, before storing it in the
            CIM repository.

            The property names in this object have been adjusted to match the
            lexical case of the property definitions in the creation class
            of the instance in the CIM repository.

            The `classname` attribute of this object will specify the
            creation class for the new instance, in any lexical case.

            The `properties` attribute of this object will specify the
            initial property values for the new CIM instance, with property
            names in any lexical case. Key properties may or may not be
            included.

            The `path` attribute of this object will be `None`.

            The `qualifiers` attribute of this object, if non-empty, should
            be ignored by the provider, because instance-level qualifiers have
            been deprecated in CIM.

        Returns:

            :class:`~pywbem.CIMInstanceName`: Instance path of the new CIM
            instance.

        Raises:
            :exc:`~pywbem.CIMError`: The provider may raise CIMError with any
              status code, and typically raises:
              - CIM_ERR_INVALID_PARAMETER
              - CIM_ERR_ALREADY_EXISTS
        """

        # Get the creation class with all exposed properties and qualifiers.
        # Since the existence of the class has already been verified, this
        # will always succeed.

        class_store = self.cimrepository.get_class_store(namespace)
        creation_class = class_store.get(new_instance.classname, copy=False)

        # Validate association class references have valid end points
        # paths or None
        if self.is_association(creation_class):
            for pn in new_instance:
                prop = new_instance.properties[pn]
                if prop.type == 'reference':
                    if prop.value is None:
                        continue
                    # Exception if end point does not exist
                    self.validate_reference_property_endpoint_exists(prop,)

        # If association class and references multiple namespaces, add instance
        # to each namespace defined in the reference properties
        if self.is_association(creation_class):
            assoc_namespaces = self.find_multins_association_ref_namespaces(
                new_instance, namespace)
            if assoc_namespaces:
                # It is a multi-namespace association instance. Validate
                # characteristics of other namespaces and insert the same
                # instance in each of these namespaces with specific path.
                return self.create_multi_namespace_instance(
                    new_instance, namespace, assoc_namespaces)

        # Otherwise create a single new instance.
        # This default provider determines the instance path from the key
        # properties in the new instance. A user-defined provider may do
        # that as well, or invent key properties such as InstanceID.
        # Specifying strict=True in from_instance() verifies that all key
        # properties exposed by the class are specified in the new instance,
        # and raises ValueError if key properties are missing.
        self.create_new_instance_path(creation_class, new_instance, namespace)
        self.add_new_instance(new_instance)
        return new_instance.path

    def ModifyInstance(self, modified_instance, IncludeQualifiers=None):
        # pylint: disable=invalid-name,line-too-long,unused-argument
        """
        Default provider method for
        :meth:`pywbem.WBEMConnection.CreateInstance`.

        Modify an existing CIM instance in the CIM repository of the mock WBEM
        server.

        NOTE: This method specifies the namespace in modified_instance.path
        rather than as a separate input parameter.

        The modification of the instance in the CIM repository that is performed
        by the provider should be limited to property value changes (including
        addition of properties if not yet set on the instance), because
        instance-level qualifiers have been deprecated in CIM.

        The set of properties that are to be modified in the CIM instance has
        already been determined by the caller so that the modified_instance
        parameter specifies exactly the set of properties to be modified.
        Therefore, this provider method does not have a property list
        parameter.

        Validation already performed by the provider dispatcher that calls
        this provider method:

        - The provider method is called only for the registered class and
          namespace (only applies to user-defined providers).

        - The Python types of all input parameters to this provider method are
          as specified below.

        - The classnames in modified_instance are consistent between
          instance and instance path.

        - The namespace exists in the CIM repository.

        - The creation class of the instance to be modified exists in the
          namespace of the CIM repository.

        - The instance to be modified exists in the namespace of the CIM
          repository.

        - All properties in modified_instance that are to be modified are
          exposed (i.e. defined and inherited with any overrides resolved) by
          the creation class in the CIM repository, and have the same
          type-related attributes (i.e. type, is_array, embedded_object).

        - No key properties are requested to change their values.

        - If there was a property list for the request, only properties defined
          in that property list are included in the modified_instance.

        Validation that should be performed by this provider method:

        - modified_instance does not specify any changed values for
          properties that are not allowed to be changed by the client,
          depending on the model implemented by the provider.

        Validation executed for this default provider:

        - Validate that any reference properties to be modified that are not
          keys define an association end point instance that currently exists
          and that the en-point instances exist.

        - If the association crosses namespaces, validate that the association
          already exists in all namespaces defined in the reference properties.

        Parameters:

          modified_instance (:class:`~pywbem.CIMInstance`):
            A representation of the modified CIM instance, also indicating its
            instance path, with exactly the set of properties to be modified.

            This object is a deep copy of the original client parameter, and may
            be modified by the provider as needed, before storing it in the
            CIM repository.

            The `path` attribute of this object will be set and is the
            instance path of the instance to be modified in the CIM repository.
            Its `namespace`, `classname` and `keybindings` attributes
            will be set. The names will be in any lexical case.

            The `classname` attribute of this object will specify the creation
            class of the instance to be modified, in any lexical case.

            The `properties` attribute of this object will specify exactly the
            set of properties that are to be updated, taking into account the
            original ModifiedInstance and PropertyList input parameters of the
            ModifyInstance() client call.
            The lexical case of the property names has been adjusted to match
            the lexical cae of the property definitions in the creation class
            in the CIM repository.

            The `qualifiers` attribute of this object, if non-empty, should
            be ignored by the provider, because instance-level qualifiers have
            been deprecated in CIM.

          IncludeQualifiers (:class:`py:bool`):
            This parameter should be ignored by the provider, because
            instance-level qualifiers have been deprecated in CIM.

        Raises:
            :exc:`~pywbem.CIMError`: The provider may raise CIMError with any
              status code, and typically raises:
              - CIM_ERR_INVALID_PARAMETER
        """  # noqa: E501
        # pylint: disable=invalid-name,line-too-long

        namespace = modified_instance.path.namespace

        # Get a copy of the instance to be modified from the CIM repository.
        instance_store = self.cimrepository.get_instance_store(namespace)
        # Copied because this will be used as the instance to update.
        original_instance = instance_store.get(modified_instance.path)

        # Get class defined for modified instance.
        class_store = self.cimrepository.get_class_store(namespace)
        creation_class = class_store.get(modified_instance.classname,
                                         copy=False)

        # Test for modified reference properties and validate if corresponding
        # instances exist. This is behavior for this default provider.
        # A specific provider may behave differently, ex. ignore non-existend
        # end-point instances
        if self.is_association(creation_class):
            for pn in modified_instance:
                prop = modified_instance.properties[pn]
                if prop.type == 'reference':
                    # Do not allow setting ref property value to None. Would
                    # mean significant extra work removing shadow instances
                    if prop.value is None:
                        raise CIMError(
                            CIM_ERR_INVALID_PARAMETER,
                            _format("Reference property {0!A} association "
                                    "end {1!A} with None value not allowed ",
                                    prop.name, prop.value))
                    if prop.value != original_instance[pn]:
                        self.validate_reference_property_endpoint_exists(prop,)

        # Update the properties in the original instance from properties
        # in the modified instance
        original_instance.update(modified_instance.properties)

        # Note: IncludeQualifiers is completely ignored per DMTF spec.

        # If association class and reference properties define multiple
        # namespaces, modify instance in each namespace defined in the
        # instance.
        if self.is_association(creation_class):
            assoc_namespaces = self.find_multins_association_ref_namespaces(
                original_instance, namespace)
            if assoc_namespaces:
                # It is a multi-namespace association instance. Validate
                # characteristics of other namespaces and insert the same
                # instance in each of these namespaces with specific path.
                self.modify_multi_namespace_instance(
                    original_instance, assoc_namespaces)
                return

        # Replace the instance in the CIM repository with the local copy.
        instance_store.update(original_instance.path, original_instance)

    def DeleteInstance(self, InstanceName):
        """
        Default provider method for
        :meth:`pywbem.WBEMConnection.DeleteInstance`.

        Delete an existing instance in the CIM repository of the mock WBEM
        server.

        NOTE: This method specifies the namespace in InstanceName
        rather than as a separate input parameter.

        The provider is not responsible for determining other instances that
        depend on the instance to be deleted (e.g. association instances
        referencing the instance to be deleted); such dependency detection and
        handling is done elsewhere.

        Validation already performed by the provider dispatcher that calls
        this provider method:

        - The provider method is called only for the registered class and
          namespace (only applies to user-defined providers).

        - The Python types of all input parameters to this provider method are
          as specified below.

        - The namespace exists in the CIM repository.

        - The creation class of the instance to be deleted exists in the
          namespace of the CIM repository.

        - The instance to be deleted exists in the namespace of the CIM
          repository.

        Parameters:

          InstanceName (:class:`~pywbem.CIMInstanceName`):
            The instance path of the instance to be deleted with the
            following attributes:

            * `classname`: Name of the creation class of the instance.
            * `keybindings`: Keybindings of the instance.
            * `namespace`: Name of the CIM namespace containing the instance.
              Will not be `None`.
            * `host`: Will be `None`.
        """

        namespace = InstanceName.namespace

        class_store = self.cimrepository.get_class_store(namespace)
        creation_class = class_store.get(InstanceName.classname, copy=False)

        if not self.is_association(creation_class):
            # Delete the instance from the CIM repository
            instance_store = self.cimrepository.get_instance_store(namespace)
            instance_store.delete(InstanceName)

        else:
            multi_ns = self.find_multins_association_ref_namespaces(
                InstanceName, namespace)
            if multi_ns:
                multi_ns.append(namespace)
                instance_name_copy = InstanceName.copy()
                for ns in multi_ns:
                    instance_name_copy.namespace = ns
                    instance_store = self.cimrepository.get_instance_store(ns)
                    instance_store.delete(instance_name_copy)
            else:
                instance_store = \
                    self.cimrepository.get_instance_store(namespace)
                instance_store.delete(InstanceName)

    def post_register_setup(self, conn):
        """
        Method called by provider registration after registation of provider
        is successful. Using this method is optional for registration cases
        where the provider must execute some activity (ex. modify the
        CIM repository) after successful provider registration).

        Override this method in the user-defined provider subclass to execute
        this method.

        Parameters:

          conn (:class:`~pywbem.WBEMConnection`):
            Current connection which allows client methods to be executed
            from within this method.
        """

    #####################################################################
    #
    # Support methods.  The following methods are support for the
    # Create/Modify/Delete instance default implementations above.
    # They are shown as public because they an be useful in building
    # alternates to the this default Create/Modify/Delete instance
    # implementation.
    #
    #####################################################################
    def find_multins_association_ref_namespaces(self, cim_object,
                                                target_namespace):
        """
        Return list of namespaces in which this association participates
        excluding the target namespace.  If an empty list is returned, this
        is not a multi-namespace association.

        Parameters:

          cim_object (:class:`CIMInstance` or :class:`CIMInstanceName`):
            object from which references/keybindings searched to determine
            if multinamespace object. Must be an association.

          target_namespace (:term:`string`):
            The namespace name provided with the request call
            (ex. CreateInstance)

        Returns:
            List of namespace names of namespaces in which this
            association instance participates if there are multiple namespaces.
            If no other namespaces are defined by reference properties, it
            returns None.
        """
        if isinstance(cim_object, CIMInstanceName):
            instance_store = self.cimrepository.get_instance_store(
                target_namespace)
            cim_object = instance_store.get(cim_object, copy=False)

        assert isinstance(cim_object, CIMInstance)
        creation_class = self.get_required_class(cim_object,
                                                 target_namespace)
        assert self.is_association(creation_class)

        ref_namespaces = set()
        for inst_prop in cim_object.properties.values():
            if inst_prop.type == 'reference':
                refprop_namespace = inst_prop.value.namespace
                assert refprop_namespace is not None, \
                    _format("Invalid namespace value None found in reference "
                            "property: {0|A}", inst_prop.value)

                # Add to list if namespace exists and not same as
                # target_namespace
                if refprop_namespace:
                    if refprop_namespace != target_namespace:
                        ref_namespaces.add(inst_prop.value.namespace)

        return list(ref_namespaces)

    def get_required_class(self, instance, namespace):
        """
        Get the class defined by instance.classname from the repository. This
        is the common method to validate the class for create instance.

        If the class  does not exist, generate a CIMError.
        """
        class_store = self.cimrepository.get_class_store(namespace)

        try:
            return class_store.get(instance.classname)
        except KeyError:
            raise CIMError(
                CIM_ERR_INVALID_CLASS,
                _format("Creation class {0!A} of new multi-namespace "
                        "association instance does not "
                        "exist in namespace {1!A} of the CIM repository.",
                        instance.classname, namespace))

    @staticmethod
    def is_association(klass):
        """
        Test if klass is an association class.

        Return True if klass is an association class and value is True.
        If association qualifier exists but is False or does not exist return
        False.
        """
        assert isinstance(klass, CIMClass)
        return klass.qualifiers.get('Association', False)

    def create_multi_namespace_instance(self, new_instance, orig_ns,
                                        assoc_namespaces):
        """
        Creates an instance of association new_instance in each namespace
        defined by reference properties of the association instance where the
        namespace in the reference property is not the namespace defined with
        the create instance call.

        Each instance is the same as the original instance except that each
        has its own namespace definition in the CIMInstanceName and the
        reference properties differ if any reference property does not include
        the namespace in its definition.

        Confirm that this is a multi-namespace association instance, that
        the class exists in all namespaces. If these tests are OK,
        confirm that the instance does not exist in any other namespace.
        Then, place the instance in the remote namespaces

        Any case where the instances cannot be created for all required
        namespaces causes an exception.

        Parameters:
          new_instance ((:class:`~pywbem.CIMInstance`):)
            The new instance that will be created

          orig_ns (:term:`string`):
            The namespace name attached to the CreateInstance request

          assoc_namespaces (list of :term:`string`):
            List of the namespaces defined in reference properties including
            the original namespace (orig_ns)

        Returns:
          If the instance is created, the CIM_InstanceName for the created
          instance is returned.

        Asserts:
            CIMError if error occurs in validity of other namespaces, class
            in other namespaces, or creating of instance in other namespaces.
        """

        # Add the original namespace to the list.
        assoc_namespaces.append(orig_ns)

        # Validate that the class exists in all of the namespaces.  It was
        # already tested for existence in the namespace defined with the
        # create.
        for ns in assoc_namespaces:
            # Verify that the class exists in the namespace
            creation_class = self.get_required_class(new_instance, ns)

        # Class exists in all target namespaces.  Confirm instances are correct.
        new_instance_paths = {}
        for ns in assoc_namespaces:
            # Set new path in the instance for namespace ns
            # This is the default behavior. A provider may chose to
            # define the path otherwise since it may also be building the
            # instance to be created dynamically.
            # FUTURE: How do we handle that or should we require that this is
            # the only multi-ns method.
            try:
                inst_path = CIMInstanceName.from_instance(
                    creation_class, new_instance, namespace=ns,
                    strict=True)
                new_instance_paths[ns] = inst_path
            except ValueError as exc:
                raise CIMError(CIM_ERR_INVALID_PARAMETER, str(exc))

        # Confirm the new instance does not exist in any of the namespaces.
        for ns, path in new_instance_paths.items():
            instance_store = self.cimrepository.get_instance_store(ns)
            if instance_store.object_exists(path):
                raise CIMError(
                    CIM_ERR_ALREADY_EXISTS,
                    _format("New instance {0!A} already exists in namespace "
                            "{1!A}. Cannot create new instance.", path, ns))

        # Add the new instance with path for each ns to each of the namespaces.
        for ns, path in new_instance_paths.items():
            instance_store = self.cimrepository.get_instance_store(ns)
            new_instance.path = path
            self.add_new_instance(new_instance)

        return new_instance_paths[orig_ns]

    def add_new_instance(self, new_instance):
        """
        Add the new instance to the repository.  If the instance already exists
        raises CIMError exception
        """
        namespace = new_instance.path.namespace
        # Get the instance store of the CIM repository. Since the existence of
        # the namespace has already been verified, this will always succeed.
        instance_store = self.cimrepository.get_instance_store(namespace)

        # Store the new instance in the CIM repository, verifying that it does
        # not exist yet.
        # NOTE: This is where we have invalid repository issue
        try:
            instance_store.create(new_instance.path, new_instance)
        except ValueError:
            raise CIMError(
                CIM_ERR_ALREADY_EXISTS,
                _format("New instance {0!A} already exists in namespace "
                        "{1!A}.", new_instance.path, namespace))

    def modify_multi_namespace_instance(self, modified_instance,
                                        assoc_namespaces):
        """
        Modifies the instance of association modified_instance in each
        namespace defined by reference properties of the association instance
        where the namespace in the reference property is not the namespace
        defined with the create instance call.

        The instances are the same except the instance path contains the
        namespace in which the instance exists.

        Any case where the instances cannot be modified for all required
        namespaces causes an exception.

        Parameters:
          modified_instance ((:class:`~pywbem.CIMInstance`):)
            The modified instance that is to replace the original
            instance in the repository

          assoc_namespaces (list of :term:`string`):
            List of the namespaces defined in reference properties including
            the original namespace (orig_ns)

        Returns:
          If the instance is created, the CIM_InstanceName for the created
          instance is returned.

        Asserts:
            CIMError if error occurs in validity of other namespaces, class
            in other namespaces, or creating of instance in other namespaces.
        """

        # Add the original namespace as the last in list.
        assoc_namespaces.append(modified_instance.path.namespace)

        # Validate that the class exists in all of the namespaces.  It was
        # already tested for existence in the namespace defined with the
        # create.
        for ns in assoc_namespaces:
            # Verify that the class exists in the namespace
            _ = self.get_required_class(modified_instance, ns)

        # Confirm instances are correct and build dict of instance names for
        # all the assoc intance names
        modified_instance_paths = NocaseDict()  # used to keep dict order
        for ns in assoc_namespaces:
            # Set new path in the instance for namespace ns
            modified_path = modified_instance.copy().path
            modified_path.namespace = ns
            modified_instance_paths[ns] = modified_path

        # Confirm the modified instance exists in all of the namespaces.
        for ns, path in modified_instance_paths.items():
            instance_store = self.cimrepository.get_instance_store(ns)
            if not instance_store.object_exists(path):
                raise CIMError(
                    CIM_ERR_NOT_FOUND,
                    _format("Modified instance {0!A} does not exist in "
                            "namespace {1!A}. Modify Failed", path, ns))

        # Modify the instance path for each namespace
        for ns, path in modified_instance_paths.items():
            instance_store = self.cimrepository.get_instance_store(ns)
            modified_instance.path = path
            instance_store.update(modified_instance.path, modified_instance)

    @staticmethod
    def create_new_instance_path(creation_class, new_instance, namespace):
        """
        Create the path for the new instance and insert it into the
        new_instance.path.

        This default provider determines the instance path from the key
        properties in the new instance. A user-defined provider may do that
        as well, or invent key properties such as InstanceID.
        Specifying strict=True from_instance() verifies that all key
        properties exposed by the class are specified in the new instance,
        and raises ValueError if key properties are missing.

        Parameters:
          creation_class (:class:`~pywbem.CIMClass`):
          The CIM class from which the instance was created. Used to determine
          the key properties.

          new_instance (:class:`~pywbem.CIMInstance`):
            The instance from which the CIMInstanceName will be derived.

          namespace: (:term:`string`):
            The namespace in which the instance will be added.

        Raises:
            CIMError if instance name cannot be created from instance.

        """
        try:
            new_instance.path = CIMInstanceName.from_instance(
                creation_class, new_instance, namespace=namespace,
                strict=True)

        except ValueError as exc:
            raise CIMError(CIM_ERR_INVALID_PARAMETER, str(exc))

    def validate_instance_exists(self, path):
        """
        Confirm that the path defined by the path exists in the namespace
        defined for that path. Null value for path allowed (i.e. no path
        defined). Returns True if the object exists or the path is empty
        otherwise False.

        Parameters:
            path (:class:`pywbem.CIMInstanceName`)
                path to instance to be tested including namespace.

        Returns:
            True if path exists in instance store or path is Null.
            False if path exists and is not in instance store.
        """
        if not path:
            return True

        try:
            inst_store = self.cimrepository.get_instance_store(path.namespace)
        except KeyError as ke:
            raise CIMError(CIM_ERR_INVALID_PARAMETER, str(ke))

        return inst_store.object_exists(path)

    def validate_reference_property_endpoint_exists(self, prop):
        """
        Validate that the path defined for the reference property prop
        exists.  Generates INVALID_PARAMETER if it does not exist.

        Parameters:
          prop (:class:`pywbem.CIMInstanceName`):
            Reference property containing CIMInstanceName as value or
            Null Value

        Raises:
            CIMError if value of property is not a valid instance or Null
        """
        path = prop.value

        if path.host:
            raise CIMError(
                CIM_ERR_INVALID_PARAMETER,
                _format("Reference property {0!A} association "
                        "end point {1!A} includes host element {2!A}. "
                        "Pywbem_mock does not allow host element in "
                        "reference properties of association instances",
                        prop.name, path, path.host))

        if not self.validate_instance_exists(path):
            raise CIMError(
                CIM_ERR_INVALID_PARAMETER,
                _format("Reference property {0!A} association "
                        "end point {1!A} does not exist ",
                        prop.name, path))
