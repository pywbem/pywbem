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
A CIM provider creates WBEM server responses to operations defined in DSP0200.

The BaseProvider WBEM server provider handles provider required data that
is common to both the MainProvider, InstanceWriteProvider, and any
registered instance providers including:

  * Access to the CIM repository
  * Access to the Method repository
  * Local provider methods that are common to both the main provider and other
    providers.
  * CIMInstance request operations except for selected operations that are
    handled by the BaseInstanceProvider to allow for specialized
    instance providers to be implemented.
  * Associator request operations

This provider uses a separate CIM repository for the objects maintained by
the CIM repository and defined with the interfaces in `BaseRepository`.
"""

from __future__ import absolute_import, print_function

from copy import deepcopy

from pywbem import CIMError, \
    CIM_ERR_NOT_FOUND, \
    CIM_ERR_ALREADY_EXISTS, CIM_ERR_INVALID_NAMESPACE, \
    CIM_ERR_NAMESPACE_NOT_EMPTY

from pywbem._utils import _format

# pywbem_mock implementation configuration variables that are used in
# request responsders.

# Default Max_Object_Count for Fake Server if not specified by request
_DEFAULT_MAX_OBJECT_COUNT = 100

# Maximum Open... timeout if not set by request
OPEN_MAX_TIMEOUT = 40

# Per DSP0200, the default behavior for EnumerateInstance DeepInheritance
# if not set by server.  Default is True.
DEFAULT_DEEP_INHERITANCE = True

# Value of LocalOnly parameter for instance retrevial operations.  This is
# set to False in this implementation because of issues between different
# versions of the DSP0200 specification that defined incompatible behavior
# for this parameter that were resolved in Version 1.4 by
# stating that False was the recommended Server setting for all instance
# retrevial requests and that clients should use False also to avoid the
# incompatibility.
INSTANCE_RETRIEVE_LOCAL_ONLY = False


class BaseProvider(object):
    """
    BaseProvider is the top level class in the provider hiearchy and includes
    methods required by the subclasses such as MainProvider and
    InstanceWriteProvider.  This class is not intended to be executed
    directly.
    """

    def __init__(self):
        """
        Set up dummy instance variables.
        """
        self.cimrepository = None
        self.provider_registry = None

    @property
    def disable_pull_operations(self):
        """
        Boolean Flag to set option to disable the execution of the open and
        pull operation request handlers in the mock CIM repository. This
        emulates the characteristic in some CIM servers that did not
        implement pull operations. The default is to allow pull operations.
        All pull operations requests may be forbidden from executing by
        setting disable_pull_operations to True.

        This attribute is settable. For details, see the description of the
        same-named init parameter of
        :class:`this class <pywbem.FakedWBEMConnection>`.
        """
        return self._disable_pull_operations

    @disable_pull_operations.setter
    def disable_pull_operations(self, disable):
        """Setter method; for a description see the getter method."""
        # Attribute will always be boolean
        if disable is None:
            disable = False
        if isinstance(disable, bool):
            # pylint: disable=attribute-defined-outside-init
            self._disable_pull_operations = disable
        else:
            raise ValueError(
                _format('Invalid type for disable_pull_operations: {0!A}, '
                        'must be a boolean', disable))

    def __repr__(self):
        return _format(
            "MainProvider("
            "cimrepository={s.cimrepository}, "
            "host={s.host}, "
            "disable_pull_operations={s.disable_pull_operations})",
            s=self)

    @property
    def namespaces(self):
        """
        Return the namespaces that exist in the CIM repository.
        """
        return self.cimrepository.namespaces

    ###############################################################
    #
    #   Access  to data store
    #
    #   The following methods provide access to the data store for
    #   a single namespace. There are separate methods to provide
    #   access to each of the 3 object stores within each namespace of
    #   the CIM Repository CIMClass, CIMInstance, and CIMQualifierDeclaration.
    #
    ##################################################################

    def get_class_store(self, namespace):
        """
        Returns the class object store for the specified CIM namespace within
        the CIM repository.  This method validates that the namespace exists in
        the data store.

        This method does not validate that the namespace exists. Be certain
        namespace is validated against CIM repository before calling this
        method

        Parameters:

          namespace(:term:`string`):
            The name of the CIM namespace in the CIM repository (case
            insensitive). Must not be `None`. Leading or trailing
            slash charactes are ignored.

        Returns:

          Instance of class derived from :class:`~pywbem_mock.`BaseObjectStore`
          which is the object store for classes in the CIM repository.

        """
        return self.cimrepository.get_class_store(namespace)

    def get_instance_store(self, namespace):
        """
        Returns the instance object store for the specified CIM namespace
        within the CIM repository.  This method validates that the namespace
        exists.

        This method does not validate that the namespace exists. Be certain
        namespace is validated against CIM repository before calling this
        method

        Parameters:

          namespace(:term:`string`):
            The name of the CIM namespace in the CIM repository (case
            insensitive). Must not be `None`. Leading or trailing
            slash characters are ignored.

        Returns:

           Instance of CIM Repository class
           derived:class:`~pywbem_mock.`BaseObjectStore` which is the object
           store for instances in the CIM repository.

        Raises:

          :exc:`~pywbem.CIMError`: CIM_ERR_INVALID_NAMESPACE: Namespace does
            not exist.
        """

        return self.cimrepository.get_instance_store(namespace)

    def get_qualifier_store(self, namespace):
        """
        Returns the qualifier declaration object store for the specified CIM
        namespace within the CIM repository.  This method validates that the
        namespace exists.

        This method does not validate that the namespace exists. Be certain
        namespace is validated against CIM repository before calling this
        method

        Parameters:

          namespace(:term:`string`):
            The name of the CIM namespace in the CIM repository (case
            insensitive). Must not be `None`. Leading or trailing
            slash characters are ignored.

        Returns:

          Instance of CIM Repository class derived
          from:class:`~pywbem_mock.`BaseObjectStore` which is the object store
          for qualifier declarations in the CIM repository.

        Raises:

          :exc:`~pywbem.CIMError`: CIM_ERR_INVALID_NAMESPACE: Namespace does
            not exist.
        """

        return self.cimrepository.get_qualifier_store(namespace)

    ################################################################
    #
    #   Methods to manage namespaces
    #
    ################################################################

    def validate_namespace(self, namespace):
        """
        Validates that a namespace is defined in the CIM repository.
        Returns only if namespace is valid. Otherwise it generates an
        exception.

          Parameters:

            namespace (:term:`string`):
              The name of the CIM namespace in the CIM repository (case
              insensitive). Must not be `None`. Any leading or trailing
              slash characters are ignored.

          Raises:

            CIMError: CIM_ERR_INVALID_NAMESPACE: Namespace does not exist.
        """
        try:
            self.cimrepository.validate_namespace(namespace)
        except KeyError:
            raise CIMError(
                CIM_ERR_INVALID_NAMESPACE,
                _format("Namespace does not exist in CIM repository: {0!A}",
                        namespace))

    def add_namespace(self, namespace):
        """
        Add a CIM namespace to the CIM repository.

        The namespace must not yet exist in the CIM repository.

        Parameters:

          namespace (:term:`string`):
            The name of the CIM namespace in the CIM repository. Must not be
            `None`. Any leading or trailing slash characters are removed before
            the string is used to define the namespace name.

        Raises:

          ValueError: Namespace argument must not be None.
          :exc:`~pywbem.CIMError`: CIM_ERR_ALREADY_EXISTS if the namespace
            already exists in the CIM repository.
        """

        if namespace is None:
            raise ValueError("Namespace argument must not be None")

        try:
            self.cimrepository.add_namespace(namespace)
        except ValueError:
            raise CIMError(
                CIM_ERR_ALREADY_EXISTS,
                _format("Namespace {0!A} already exists in the CIM repository ",
                        namespace))

    def remove_namespace(self, namespace):
        """
        Remove a CIM namespace from the CIM repository.

        The namespace must exist in the CIM repository and must be empty.

        Parameters:

          namespace (:term:`string`):
            The name of the CIM namespace in the CIM repository (case
            insensitive). Must not be `None`. Leading or trailing
            slash characters are ignored.

        Raises:

          ValueError: Namespace argument must not be None
          :exc:`~pywbem.CIMError`:  CIM_ERR_NOT_FOUND if the namespace does
            not exist in the CIM repository.
          :exc:`~pywbem.CIMError`:  CIM_ERR_NAMESPACE_NOT_EMPTY if the
            namespace is not empty.
          :exc:`~pywbem.CIMError`:  CIM_ERR_NAMESPACE_NOT_EMPTY if attempting
            to delete the default connection namespace.  This namespace cannot
            be deleted from the CIM repository
        """
        if namespace is None:
            raise ValueError("Namespace argument must not be None")

        try:
            self.cimrepository.remove_namespace(namespace)
        except KeyError:
            raise CIMError(
                CIM_ERR_NOT_FOUND,
                _format("Namespace {0!A} does not exist in the CIM repository ",
                        namespace))
        except ValueError:
            raise CIMError(
                CIM_ERR_NAMESPACE_NOT_EMPTY,
                _format("Namespace {0!A} contains objects.", namespace))

    ################################################################
    #
    #   Common Repository access methods used by MainProvider and
    #   InstanceProviders
    #
    ################################################################

    def get_class(self, namespace, classname, local_only=None,
                  include_qualifiers=None, include_classorigin=None,
                  property_list=None):
        # pylint: disable=invalid-name
        """
        Get class from CIM repository.  Gets the class defined by classname
        from the CIM repository, creates a copy, expands the copied class to
        include superclass properties if not localonly, and filters the
        class based on propertylist and includeClassOrigin.

        It also sets the propagated attribute.

        Parameters:

          classname (:term:`string`):
            Name of class to retrieve

          namespace (:term:`string`):
            The name of the CIM namespace in the CIM repository (case
            insensitive). Must not be `None`. Leading or trailing slash
            charactes are ignored.

          local_only (:class:`py:bool`):
            If `True`, or `None`only properties and methods in this specific
            class are returned. `None` means not supplied by client and the
            normal server default is `True`
            If `False` properties and methods from the superclasses
            are included.

          include_qualifiers (:class:`py:bool`):
            If `True` or `None`, include qualifiers.  `None` is the server
            default if the parameter is not provided by the client.
            If `False` do not include qualifiers.

          include_classorigin (:class:`py:bool`):
            If `True` return the class_origin attributes of properties and
            methods.
            If `False` or `None` (use server default), class_origin attributes
            of properties and methods are not returned

          property_list (list of :term:`string`):
            Properties to be included in returned class.  If None, all
            properties are returned.  If empty list, no properties are returned

        Returns:

          Copy of the CIM class if found with superclass properties
          installed and filtered per the method arguments.

        Raises:
          CIMError: (CIM_ERR_NOT_FOUND) if class Not found in CIM repository or
          CIMError: (CIM_ERR_INVALID_NAMESPACE) if namespace does not exist
        """

        class_store = self.get_class_store(namespace)

        # Try to get the target class and create a copy for response
        try:
            cls = class_store.get(classname)
        except KeyError:
            raise CIMError(
                CIM_ERR_NOT_FOUND,
                _format("Class {0!A} not found in namespace {1!A}.",
                        classname, namespace))

        # Use deepcopy to assure copying all elements of the class.
        # cls.copy() does not copy all elements.
        cc = deepcopy(cls)

        # local_only server default is True so True or None remove properties
        if local_only is True or local_only is None:
            for prop, pvalue in cc.properties.items():
                if pvalue.propagated:
                    del cc.properties[prop]
            for method, mvalue in cc.methods.items():
                if mvalue.propagated:
                    del cc.methods[method]

        self.filter_properties(cc, property_list)

        # Remove qualifiers if specified.  Note that the server default
        # is to include_qualifiers if include_qualifiers is None
        if include_qualifiers is False:
            self._remove_qualifiers(cc)

        # class_origin default is False so None or False cause removal
        if not include_classorigin:
            self._remove_classorigin(cc)
        return cc

    def class_exists(self, namespace, classname):
        """
        Test if class defined by classname parameter exists in
        CIM repository defined by namespace parameter.

        Returns `True` if class exists and `False` if it does not exist.

        Exception if the namespace does not exist
        """
        class_store = self.get_class_store(namespace)
        return class_store.exists(classname)

    @staticmethod
    def filter_properties(obj, property_list):
        """
        Remove properties from an instance or class that aren't in the
        property_list parameter

        obj(:class:`~pywbem.CIMClass` or :class:`~pywbem.CIMInstance):
            The class or instance from which properties are to be filtered

        property_list(list of :term:`string`):
            List of properties which are to be included in the result. If
            None, remove nothing.  If empty list, remove everything. else
            remove properties that are not in property_list. Duplicated names
            are allowed in the list and ignored.
        """
        if property_list is not None:
            property_list = [p.lower() for p in property_list]
            for pname in obj.properties.keys():
                if pname.lower() not in property_list:
                    del obj.properties[pname]

    @staticmethod
    def find_instance(instance_name, instance_store, copy_inst=None):
        """
        Find an instance in the CIM repository by iname and return
        that instance. the copy_inst controls whether the original
        instance in the CIM repository is returned or a copy.  The
        only time the original should be returned is when the user is
        certain that the returned object WILL NOT be modified.

        Parameters:

          instance_name: CIMInstancename to find in the instance_store

          instance_store (:class:`~pywbem_mock.BaseObjectStore):
            The CIM repository to search for the instance

          copy_inst: boolean.
            If True do copy of the instance and return the copy. Otherwise
            return the instance in the CIM repository

        Returns:
            None if the instance defined by iname is not found.
            If it is found, the complete instance or copy is returned.

        """

        if instance_store.exists(instance_name):
            if copy_inst:
                return instance_store.get(instance_name).copy()
            return instance_store.get(instance_name)

        return None

    def get_registered_provider(self, namespace, provider_type, classname):
        """
        If there is a provider registered for this namespace, provider_type,
        and classname return that object (the instance of the
        InstanceWriteProvider subclass).

        If no provider is registered, return None.

        Parameters:

          namespace (:term:`string`):
            The namespace in which the request will be executed.

          provider_type (:term:`string`):
            String containing keyword ('instance' or 'method') defining the
            type of provider.

          classname (:term:`string`):
            Name of the class defined for the operation
        """

        if not self.provider_registry:
            return None

        if classname not in self.provider_registry:
            return None

        if namespace not in self.provider_registry[classname]:
            return None

        tp = self.provider_registry[classname][namespace]

        if provider_type not in tp:
            return None

        return tp[provider_type]
