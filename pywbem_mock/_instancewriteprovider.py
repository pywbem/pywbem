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
This module contains the InstanceWrite Provider with the default implementation
for the mock WBEM server responders for `CreateInstance`, `ModifyInstance` and
`DeleteInstance`.  These the methods will be executed if there is no provider
registered  for a namespace and class name.

This module adds support for user-defined instance providers.  User-defined
instance providers may be created within the pywbem_mock environment to modify
the functionality of these WBEM requests.
:class:`~pywbem_mock.InstanceWriteProvider` defines the  default implementation
of ``CreateInstance``, ``ModifyInstance`` and ``DeleteInstance`` default
mock WBEM server responder methods that may be overwritten by user-defined
subclasses of the :class:`~pywbem_mock.InstanceWriteProvider`.

User-defined providers may be created for specific CIM classes (which are
defined in the user-defined provider) and namespaces (which are defined a
parameter of the provider registration) to override one or more of the
operation request methods defined in
:class:`~pywbem_mock.InstanceWriteProvider` with user methods defined in a
subclass of :class:`~pywbem_mock.InstanceWriteProvider`.  If any of the
InstanceWriteProviders do not exist in the user-defined provider, the
corresponding default method is executed.

This module contains the default InstanceWriteProvider class which provides the
following:

1. Definition of the provider type (`provider_type = instance`).
2. Definition of the method APIs, default implementation and return for the
   `CreateInstance`, 'ModifyInstance', and `DeleteInstance` methods required
   in the user-defined subclass.

A user-defined instance provider can be created as follows:

1. Implement the subclass of :class:`~pywbem_mock.InstanceWriteProvider` with:

   a. Constructor:
      `__init__()` that takes as input at least the cimrepository
      object parameter and passes it to the superclass and any other
      constructor parameters the user-defined provider requires.  Since the
      user creates the instance.

      .. code-block:: python

         def __init__(self, cimrepository):
             super(MyInstanceWriteProvider, self).__init__(cimrepository)

      Since the registration (:meth:`pywbem.WBEMConnection.register_provider`)
      requires that the provider be instantiated before being registered, a
      user could add more parameters to the constructor.

   b. Definition of the CIM class(es) the provider supports as a class variable.

      .. code-block:: python

        provider_classnames = 'CIM_Foo'
        or
        provider_classnames = ['CIM_Foo', 'CIM_Foo_blah']

   c. Definition and implementation of the WBEM operations supported by the
      provider from the set of request operations defined in the table above.
      This must be a subset of the methods defined for the provider type.
      Methods that do not exist in the user-defined provider default to the
      default method. Each of these methods may:

      * provide parameter or CIM repository validation in addition to the normal
        request validation,
      * modify parameters of the request,
      * abort the request with a CIMError exception,
      * make modifications to the CIM repository.

      The request may be completed by the user provider method calling the
      superclass corresponding method to complete its final validation and
      modify the repository or by the provider directly modifying the
      repository based on the method and parameters.

      The user-defined providers have access to:
        * methods defined in their superclass
        * methods defined in :class:~pywbem_mock.BaseProvider`
        * methods to access the CIM repository using the methods defined in
          :class:`~pywbem_mock.InMemoryRepository`

      .. code-block:: python

        # define CreateInstance method and call the superclass method
        def CreateInstance(self, namespace, NewInstance):
        \"\"\"Test Create instance just calls super class method\"\"\"

        # Calls the default responder method for CreateInstance
        return super(MyInstanceWriteProvider, self).CreateInstance(
            namespace, NewInstance)

   d. Optional post register setup method
      The provider may include
      (:meth:`~pywbem_mock.InstanceWriteProvider.post_register-setup()`) that
      :meth:`~pywbem_mock.FakedWBEMConnection.register_provider` will call as
      after the provider registration is successful.  This allows the provider
      to do any special setup it desires uses its own methods. This method
      includes the current connection as a parameter so that client methods can
      be executed directly.

      .. code-block:: python

          def post_register_setup(self, conn):
            # code that performs post registration setup for the provider


   The input parameters for the user defined methods  will
   have been already validated in
   :class:`~pywbem_mock.ProviderDispatcher.ProviderDispatcher` including:

   a. The namespace defined in the namespace parameter exists.

   b. The CIM class for the instance or instance path defined in the input
      parameter exists in the exists.

   c. The input object (NewInstance, etc. is of the correct CIM type) and
      properties of the instance for CreateInstance are valid.

   d. The instance does not exist for CreateInstance and does exist for
      Modify Instance.


   The created methods should implement any exceptions based on
   :class:`pywbem.CIMError` using the error codes defined in :term:`DSP0200`
   which will be passed back to the client.

   The user-defined class must include the following class variable:

   * `provider_classnames` (:term:`string` or list of :term`string`): defines
     the class(es) that this provider will serve.

   The user-defined provider has access to:
       * methods defined in the superclass
         :class:~pywbem_mock.InstanceWriteProvider`
       * methods defined in :class:~pywbem_mock.BaseProvider`
       * methods to access the CIM repository using the methods defined in
         :class:`~pywbem_mock.InMemoryRepository`

2. Register the user-defined provider using
   :meth:`~pywbem_mock.FakedWBEMConnection.register_provider` to define the
   namespaces for which the user provider will override
   :class:`~pywbem_mock.InstanceWriteProvider`.  The registration of the user
   provider must occur after the namespaces defined in the registration have
   been added to the CIM repository.

      .. code-block:: python

        # class for this provider previously installed in CIM repository
        provider = MyCIM_BlanInstanceWriteProvider(self.cimrepository)
        conn.register_provider(provider,
                               namespaces=['root/interop', 'root/cimv2'])
"""

from __future__ import absolute_import, print_function

from pywbem import CIMInstanceName, CIMError, \
    CIM_ERR_INVALID_PARAMETER, CIM_ERR_ALREADY_EXISTS

from pywbem._utils import _format

from ._baseprovider import BaseProvider

# None of the request method names conform since they are camel case
# pylint: disable=invalid-name

__all__ = ['InstanceWriteProvider']


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

        # This default provider determines the instance path from the key
        # properties in the new instance. A user-defined provider may do that
        # as well, or invent key properties such as InstanceID.
        # Specifying strict=True in from_instance() verifies that all key
        # properties exposed by the class are specified in the new instance,
        # and raises ValueError if key properties are missing.
        try:
            new_instance.path = CIMInstanceName.from_instance(
                creation_class, new_instance, namespace=namespace, strict=True)
        except ValueError as exc:
            raise CIMError(CIM_ERR_INVALID_PARAMETER, str(exc))

        # Get the instance store of the CIM repository. Since the existence of
        # the namespace has already been verified, this will always succeed.
        instance_store = self.cimrepository.get_instance_store(namespace)

        # Store the new instance in the CIM repository, verifying that it does
        # not exist yet.
        try:
            instance_store.create(new_instance.path, new_instance)
        except ValueError:
            raise CIMError(
                CIM_ERR_ALREADY_EXISTS,
                _format("New instance {0!A} already exists in namespace "
                        "{1!A}.", new_instance.path, namespace))

        # CreateInstance returns the instance path of the new instance
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

        Validation that should be performed by this provider method:

        - modified_instance does not specify any changed values for
          properties that are not allowed to be changed by the client,
          depending on the model implemented by the provider.

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
        instance = instance_store.get(modified_instance.path)

        # Modify the properties of the local instance copy. The implemented
        # approach is intentionally careful, to ensure that only the property
        # values get updated.
        for pn in modified_instance.properties:
            mod_prop = modified_instance.properties[pn]
            inst_prop = instance.properties[pn]
            inst_prop.value = mod_prop.value  # Update the property value

        # Note that IncludeQualifiers is completely ignored.

        # Replace the instance in the CIM repository with the local copy.
        instance_store.update(modified_instance.path, instance)

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

        Raises:

            None
        """

        namespace = InstanceName.namespace
        instance_store = self.cimrepository.get_instance_store(namespace)

        # Delete the instance from the CIM repository
        instance_store.delete(InstanceName)

    def post_register_setup(self, conn):
        """
        Method called by provider registration after registation of provider
        is successful. Using this method is optional for registration cases
        where the provider must execute some activity (ex. modify the
        CIM repository after successful provider registration).

        Override this method in the user-defined provider subclass to execute
        this method.

        Parameters:

          conn (:class:`~pywbem.WBEMConnection`):
            Current connection which allows client methods to be executed
            from within this method.
        """
