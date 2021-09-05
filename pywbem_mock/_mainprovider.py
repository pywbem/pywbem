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

MainProvider WBEM server provider handles and responds to:

  * CIMClass request Operations.
  * CIMQualifierDeclaration request Operations
  * CIMInstance request operations except for selected operations that are
    handled by the BaseInstanceProvider to allow for specialized
    instance providers to be implemented.
  * Associator request operations

This provider uses a separate CIM repository for the objects maintained by
the CIM repository and defined with the interfaces in `BaseRepository`.
"""

from __future__ import absolute_import, print_function

import uuid
from collections import Counter
from copy import deepcopy
import re
import six
from nocaselist import NocaseList

# pylint: disable=ungrouped-imports
try:
    from time import perf_counter
except ImportError:
    # For Python <3.3, fall back to time.clock() (deprecated since Python 3.3).
    # Note: On Python 3.6 and 3.7, Pylint 2.10.2 raises the warning
    #       'deprecated-method' on the lines where perf_counter() is used.
    #       Remove disabling that warning once Pylint issue
    #       https://github.com/PyCQA/pylint/issues/4966 is resolved.
    from time import clock as perf_counter
# pylint: enable=ungrouped-imports

from pywbem import CIMClass, CIMClassName, CIMInstanceName, \
    CIMQualifierDeclaration, CIMError, \
    CIM_ERR_NOT_FOUND, CIM_ERR_INVALID_PARAMETER, CIM_ERR_INVALID_CLASS, \
    CIM_ERR_ALREADY_EXISTS, CIM_ERR_INVALID_ENUMERATION_CONTEXT, \
    CIM_ERR_NOT_SUPPORTED, CIM_ERR_QUERY_LANGUAGE_NOT_SUPPORTED, \
    CIM_ERR_INVALID_QUERY, CIM_ERR_FAILED, CIM_ERR_CLASS_HAS_CHILDREN, \
    CIM_ERR_CLASS_HAS_INSTANCES, CIM_ERR_INVALID_SUPERCLASS
from pywbem._utils import _format

from pywbem_mock.config import IGNORE_INSTANCE_IQ_PARAM, \
    IGNORE_INSTANCE_ICO_PARAM
from pywbem_mock._baseprovider import BaseProvider

from ._resolvermixin import ResolverMixin

# The following config items only apply to open/pull operations
from .config import DEFAULT_MAX_OBJECT_COUNT, OPEN_MAX_TIMEOUT


# per DSP0200, the default behavior for EnumerateInstance DeepInheritance
# if not set by in the client request.  Default is True so that the mock server
# EnumerateInstance method retrieves all properties of each subclass instance
# by default.
DEFAULT_DEEP_INHERITANCE = True


# Value of LocalOnly parameter for instance retrevial operations.  This is
# set to False in this implementation because of issues between different
# versions of the DSP0200 specification that defined incompatible behavior
# for this parameter that were resolved in Version 1.4 by
# stating that False was the recommended Server setting for all instance
# retrevial requests and that clients should use False also to avoid the
# incompatibility.
# The mock server retrieves superclass properties for GetInstance,
# EnumerateInstance, Associators, etc. in all cases and ignores ignores
# the value received from the client.

INSTANCE_RETRIEVE_LOCAL_ONLY = False


# None of the request method names conform since they are camel case
# pylint: disable=invalid-name


class MainProvider(ResolverMixin, BaseProvider):
    """
    A CIM provider in the mock support of pywbem creates WBEM server responses
    to operations defined in DSP0200 and implements them using a CIM
    repository. Because the CIM repository has a uniform interface (defined by
    BaseRepository), most operations can be implemented in a generic way, and
    only those operations that create, delete or modify CIM instances have a
    need to have user-defined providers.

    The MainProvider class is the main CIM provider in the mock support of
    pywbem and handles all those operations that do not have a need to be
    implementable by users. Specifically, it implements:

    * All operations on CIM classes.
    * All operations on CIM qualifier declarations.
    * All read operations on CIM instances (i.e. get, traditional and
      pull enumerations, and association operations).

    Operations that create, delete or modify CIM instances or that invoke
    static or non-static methods have a default implementation in the
    BaseInstanceProvider class and can be overwritten by users on a per class
    and per operation basis.

    The MainProvider class also includes methods to add namespaces, remove
    namespaces and get a list of namespaces in the CIM repository.

    There MUST BE only one instance of MainProvider created for each
    FakedWBEMConnection attributes since some of the instance level structures
    depend on a single instance of the attribute throughout a connection.

    For more details, see mocksupport.rst.
    """

    def __init__(self, host, disable_pull_operations, cimrepository,
                 providerdispatcher):
        # pylint: disable=super-init-not-called
        """
        Parameters:

          host (:term:`string`):
            Value of the host attribute from the class that called
            this constructor, normally FakedWBEMConnection.  This
            attribute is used to construct the host component of
            CIMNamespaces in some responses.

          disable_pull_operations (:class:`py:bool`):
            Flag to allow user to disable the pull operations ( Open... and
            Pull.. requests). The default is None which enables pull operations
            to execute. Setting the flag to True causes pull operations
            to raise CIMError(CIM_ERR_NOT_SUPPORTED).

          cimrepository (:class:`~pywbem_mock.BaseRepository` or subclass):
            Defines the repository to be used by the providers.

          providerdispatcher (:class:`~pywbem_mock.ProviderDispatcher`):
            Defines the providerdispatcher object that is called in some
            operations (see DeleteClass method).
        """
        super(MainProvider, self).__init__(cimrepository)

        # value of the host name.  This should be considered read-only
        self.host = host

        self.providerdispatcher = providerdispatcher

        self.disable_pull_operations = disable_pull_operations

        # Open Pull Contexts. The key for each context is an enumeration
        # context id.  The data is the total list of instances/names to
        # be returned and the current position in the list. Any context in
        # this list is still open. Defined in MainRepository because only
        # this provider handles Pull requests.
        self.enumeration_contexts = {}

    @property
    def disable_pull_operations(self):
        """
        Boolean Flag to set option to disable the execution of the open and
        pull operation request handlers in the CIM repository. This
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

    #####################################################################
    #
    #     Common methods that the MainProvider request processing methods
    #     use to communicate with the defined CIM repository. These are
    #     generally private methods.
    #
    #####################################################################

    @staticmethod
    def _get_superclass_names(classname, class_store):
        """
        Get list of superclasses names from the class datastore for the
        defined classname (cln) in the namespace.

        Parameters:
          classname(:term:`string` or None):
            Class name for which superclasses will be retrieved.
            If None, an empty list is returned

        Returns:
         List of classnames in order of ascending class hierarchy or an empty
         list if classname is None or the top of the class hierarchy. The list
         is returned in desending hierarchial order.
        """

        superclass_names = []
        if classname is not None:
            cln_work = classname
            while cln_work:
                # Accesses class in CIM repository. Note, no copy made
                cln_superclass = class_store.get(cln_work).superclass
                if cln_superclass:
                    superclass_names.append(cln_superclass)
                cln_work = cln_superclass
            superclass_names.reverse()
        return superclass_names

    def _get_subclass_names(self, classname, class_store, deep_inheritance):
        """
        Get class names that are subclasses of the classname input
        parameter from the CIM repository.

        If DeepInheritance is False, get only classes in the
        CIM repository for the defined namespace for which this class is a
        direct super class.

        If deep_inheritance is `True`, get all direct and indirect
        subclasses.  If False, get only a the next level of the
        hierarchy.  `None` is treated the same as `False`

        The input classname is NOT included in the returned list.

        Parameters:
          classname (:term:`string` or None):
            The name of the CIM class for which subclass names will
            be retrieved. If None, retrieval starts at the root of
            the class hierarchy

          class_store (:class:`~pywbem_mock.BaseObjectStore):
           The CIM repository to search for this class and subclasses

          deep_inheritance (:class:`py:bool`):

        Returns:
          list of :term:`unicode string` with the names of all subclasses of
          `classname`.
        """

        assert classname is None or isinstance(classname, six.string_types)

        if classname is None:
            rtn_classnames = [
                c.classname for c in class_store.iter_values(copy=False)
                if c.superclass is None]
        else:
            rtn_classnames = [
                c.classname for c in class_store.iter_values(copy=False)
                if c.superclass and c.superclass.lower() == classname.lower()]

        # Recurse for next level of class hierarchy
        if deep_inheritance:
            subclass_names = []
            if rtn_classnames:
                for cln in rtn_classnames:
                    subclass_names.extend(
                        self._get_subclass_names(cln, class_store,
                                                 deep_inheritance))
            rtn_classnames.extend(subclass_names)
        return rtn_classnames

    def _iter_association_classes(self, namespace):
        """
        Return iterator of association classes from the class repo

        Returns the classes that have associations qualifier.
        Does NOT copy so these are what is in CIM repository. User functions
        MUST NOT modify these classes.

        Returns: Returns generator where each yield returns a single
                 association class
        """

        class_store = self.cimrepository.get_class_store(namespace)
        for cl in class_store.iter_values():
            if 'Association' in cl.qualifiers:
                yield cl
        return

    def _get_instance(self, instance_name, instance_store,
                      local_only, include_class_origin,
                      include_qualifiers, property_list):
        # pylint: disable=line-too-long
        """
        Local method implements the core functionality of a GetInstance
        provider. This is used by other instance retrevial methods that need
        to get and process an instance from the CIM repository.

        It attempts to get the instance, copies it, and filters it
        for input parameters of local_only, include_qualifiers,
        include_class_origin, and propertylist.

        Parameters:

          instance_name (:class:`~pywbem.CIMInstanceName`):
            The instance name of the instance to be retrieved with the
            following attributes:

            * `classname`: Name of the creation class of the instance.
            * `keybindings`: Keybindings of the instance.
            * `namespace`: Name of the CIM namespace containing the instance.
              Must not be None.
            * `host`: value ignored.

          instance_store (:class:`~pywbem_mock.BaseObjectStore):
            The CIM repository to access for this class and subclasses.
            This parameter allows accessing many instances without repeated
            namespace existence tests.

          property_list (:term:`string` or :term:`py:iterable` of :term:`string`):
            List of property names that will be used to filter properties
            of the returned instance.  If property_list is None, no
            filtering is done. Otherwise each property name in the
            list defines a property to be retained in the returned instance.
            An empty list causes the method to return an instance with
            no properties.

          local_only (:class:`pybool`):
             If `True` only properties with classorigin same as classname
             are returned.

             If `False` or `None` all properties are returned. This method
             maintains the code to implement local only consistent with
             version 1.4 of DSP0004. However every call to _get_instances
             now sets the default `False` since that was the only way to
             get around issues between different versions of DSP0200 that
             defined incompatible behaviors to this request parameter.

          include_class_origin (:class:`pybool`):
              If `True`, class_origin included in returned object.
              If `False` or `None` class_origin is not included in the
              returned object

              The value of this argument may be overridden by the
              IGNORE_INSTANCE_ICO_PARAM config variable.  The default config
              value is True(ignore this parameter and use False)

          include_qualifiers (:class:`pybool`):
              If `True`, any qualifiers in the stored instance the instance and
              properties are returned

              If `False` or None no qualifiers in the instance or properties
              are returned.

              The value of this argument may be overridden by the
              IGNORE_INSTANCE_IQ_PARAM config variable. The default config
              value is True(ignore this parameter and use False)

        Returns:

          Copy of the :class:`~pywbem.CIMInstance` object in the CIM repository
          that is a representation of the retrieved instance with property_list
          filtered, and qualifers removed if include_qualifiers=False and class
          origin removed if include_class_origin False.

          Its `path` attribute is a :class:`~pywbem.CIMInstanceName` object
          with its attributes set as follows:

          * `classname`: Name of the creation class of the instance.
          * `keybindings`: Keybindings of the instance.
          * `namespace`: Name of the CIM namespace containing the instance.
          * `host`: `None`, indicating the WBEM server is unspecified.

        Raises:

            :exc:`~pywbem.CIMError`: (CIM_ERR_NOT_FOUND) if the instance does
              not exist in the repository.

            :exc:`~pywbem.CIMError`: (CIM_ERR_INVALID_CLASS) if superclasses
              required for resolution of the instance do not exist in the
              repository.
        """  # noqa: E501
        # pylint: enable=line-too-long

        rtn_inst = self._get_bare_instance(instance_name, instance_store,
                                           copy=True)

        if rtn_inst is None:
            raise CIMError(
                CIM_ERR_NOT_FOUND,
                _format("Instance not found in CIM repository namespace {0!A}. "
                        "Path={1!A}", instance_name.namespace, instance_name))

        # If local_only remove properties where class_origin
        # differs from class of target instance
        if local_only:
            for p in list(rtn_inst):
                class_origin = rtn_inst.properties[p].class_origin
                if class_origin and class_origin != rtn_inst.classname:
                    del rtn_inst[p]

        if local_only:
            # gets class propertylist which may be local only or all
            # superclasses
            try:
                cl = self.get_class(instance_name.namespace,
                                    instance_name.classname,
                                    local_only=local_only)
            except CIMError as ce:
                if ce.status_code == CIM_ERR_NOT_FOUND:
                    raise CIMError(
                        CIM_ERR_INVALID_CLASS,
                        _format("Class {0!A} not found for instance {1!A} in "
                                "CIM repository namespace {2!A}.",
                                instance_name.classname, instance_name,
                                instance_name.namespace))

            class_pl = cl.properties.keys()

            # delete properties in instance but not in class
            for p in list(rtn_inst):
                if p not in class_pl:
                    del rtn_inst[p]

        if rtn_inst.path.host:
            rtn_inst.path.host = None

        self.filter_properties(rtn_inst, property_list)

        if IGNORE_INSTANCE_IQ_PARAM or not include_qualifiers:
            self._remove_qualifiers(rtn_inst)

        if IGNORE_INSTANCE_ICO_PARAM or not include_class_origin:
            self._remove_classorigin(rtn_inst)
        return rtn_inst

    def _get_subclass_list_for_enums(self, classname, namespace, class_store):
        """
        Return the class names of subclasses of the specified classname
        in the specified namespace, including the specified classname itself.

        Returns:

          :term:`NocaseList`: Class names of subclasses, including classname
          itself.

        Raises:

            :exc:`~pywbem.CIMError`: (CIM_ERR_INVALID_CLASS) if classname not
              in CIM repository.
        """

        if not class_store.object_exists(classname):
            raise CIMError(
                CIM_ERR_INVALID_CLASS,
                _format("Class {0!A} not found in namespace {1!A}.",
                        classname, namespace))

        cln_list = self._get_subclass_names(classname, class_store, True)

        result = NocaseList(cln_list)
        result.append(classname)
        return result

    @staticmethod
    def _validate_instancename_namespace(namespace, object_name):
        """
        Validates that the namespace in ObjectName is None or same as
        in namespace. This is because we receive both namespace parameter
        and InstanceName parameter on some methods and need to resolve any
        differences.

        If the namespaces both exist and differ, the namespace parameter
        is used.

        Raises:

            :exc:`~pywbem.CIMError`: (CIM_ERR_INVALID_PARAMETER) if both exist
              and they don't match.
        """

        assert isinstance(object_name, CIMInstanceName)
        if object_name.namespace is None:
            object_name.namespace = namespace
        elif object_name.namespace == namespace:
            return
        else:
            raise CIMError(
                CIM_ERR_INVALID_PARAMETER,
                _format("Namespace {0!A} in path {1!A} "
                        "does not match request namespace parameter {2!A}.",
                        object_name.namespace, object_name, namespace))

    @staticmethod
    def _validate_dependencies_exist(klass, class_store, namespace):
        """
        Validate that class dependencies (reference classnames and Embedded
        object classnames) exist in the class repository

        Parameters:

          klass (:class:`~pywbem.CIMClassName`):
            The class to be inspected
          class_store (:class:`~pywbem_mock.BaseObjectStore):
            The CIM repository class store to to search for the
            classes.

        Raises:
            CIMError if any of the classes upon which this class depends
            does not exist in the CIM repository
        """
        # Validate that dependent classes exist
        objects = list(klass.properties.values())
        klass_namelc = klass.classname.lower()
        for meth in klass.methods.values():
            objects += list(meth.parameters.values())

        for obj in objects:
            # Validate that reference_class exists in repo
            if obj.type == 'reference':
                if obj.reference_class.lower() == klass_namelc:
                    continue
                if not class_store.object_exists(obj.reference_class):
                    raise CIMError(
                        CIM_ERR_INVALID_PARAMETER,
                        _format("Class {0!A} referenced by element {1!A} "
                                "of class {2!A} in namespace {3!A} does "
                                "not exist",
                                obj.reference_class, obj.name,
                                klass.classname, namespace))
            elif obj.type == 'string':
                if 'EmbeddedInstance' in obj.qualifiers:
                    eiqualifier = obj.qualifiers['EmbeddedInstance']
                    # The DMTF spec allows the value to be None
                    if eiqualifier.value is None or \
                            eiqualifier.value.lower() == klass_namelc:
                        continue
                    if not class_store.object_exists(eiqualifier.value):
                        raise CIMError(
                            CIM_ERR_INVALID_PARAMETER,
                            _format("Class {0!A} specified by "
                                    "EmbeddInstance qualifier on element "
                                    "{1!A} of class {2!A} in namespace "
                                    "{3!A} does not exist",
                                    eiqualifier.value, obj.name,
                                    klass.classname, namespace))

    #####################################################################
    #
    #   Mock WBEM server provider methods.
    #
    #   These provider methods emulate the server response; they are named like
    #   the client methods in WBEMConnection and correspond directly to them.
    #
    #   The API for these calls differs from the methods in WBEMConnection
    #   in that every provider call API includes the namespace as a
    #   positional argument including those where WBEMConnection methods do not
    #   include the namespace. This is logical in that the server
    #   does not have the concept of a default whereas the client does.
    #
    #   The pattern we try to use in the processing is to use the
    #   namespace only to validate namespace, and get the corresponding
    #   repository for the CIM type and namespace from the data store
    #   and use that in further processing. The only other use of namespace
    #   should be in possibly preparing data for sending to the data
    #   store and generating excption messages.
    #
    ######################################################################

    ####################################################################
    #
    #   Class-related provider methods
    #
    ####################################################################

    def EnumerateClasses(self, namespace, ClassName=None,
                         DeepInheritance=None, LocalOnly=None,
                         IncludeQualifiers=None, IncludeClassOrigin=None):
        """
        Provider method for
        :meth:`pywbem.WBEMConnection.EnumerateClasses`.

        Enumerate classes from CIM repository. If classname parameter exists,
        use it as the starting point for the hierarchy to get subclasses.

        Parameters:

          namespace (:term:`string`):
            The name of the CIM namespace in the CIM repository (case
            insensitive). Must not be `None`. Leading or trailing
            slash characters are ignored.

          ClassName (:term:`string`):
            Name of the class whose subclasses will be retrieved
            (case independent).

            If `None`, the top-level classes in the namespace will be
            retrieved.

          DeepInheritance (:class:`py:bool`):
            Indicates that all (direct and indirect) subclasses of the
            specified class or of the top-level classes are to be included in
            the result, as follows:

            * If `False`, only direct subclasses of the specified class or only
              top-level classes are included in the result.
            * If `True`, all direct and indirect subclasses of the specified
              class or the top-level classes and all of their direct and
              indirect subclasses are included in the result.
            * If `None`, the server defined default is False
              per :term:`DSP0200` (server-implemented default is `False`).

            Note, the semantics of the `DeepInheritance` parameter in
            :meth:`pywbem.WBEMConnection.EnumerateInstances` is different.

          LocalOnly (:class:`py:bool`):
            Indicates that inherited properties, methods, and qualifiers are to
            be excluded from the returned classes, as follows.

            * If `False`, inherited elements are not excluded.
            * If `True`, inherited elements are excluded.
            * If `None`, the :term:`DSP0200` server default of `True` is used.

          IncludeQualifiers (:class:`py:bool`):
            Indicates that qualifiers are to be included in the returned
            classes, as follows:

            * If `False`, qualifiers are not included.
            * If `True`, qualifiers are included.
            * If `None`, the  :term:`DSP0200`  defined default is `True`.

          IncludeClassOrigin (:class:`py:bool`):
            Indicates that class origin information is to be included on each
            property and method in the returned classes, as follows:

            * If `False`, class origin information is not included.
            * If `True`, class origin information is included.
            * If `None`, :term:`DSP0200` (server-implemented default is `False`)
              is used.
              per :term:`DSP0200` (server-implemented default is `False`).

        Returns:

            List of :class:`~pywbem.CIMClass` that are the enumerated classes.

        Raises:

            :exc:`~pywbem.CIMError`: (CIM_ERR_INVALID_NAMESPACE)
            :exc:`~pywbem.CIMError`: (CIM_ERR_NOT_FOUND) A class that should
              be a subclass of either the root or "ClassName" parameter was not
              found in the CIM repository. This is probably a CIM repository
              build error.
            :exc:`~pywbem.CIMError`: (CIM_ERR_INVALID_CLASS) class defined by
              the classname parameter does not exist.
        """

        # Parameter types are already checked by WBEMConnection operation
        assert isinstance(namespace, six.string_types)
        assert isinstance(ClassName, (six.string_types, type(None)))
        assert isinstance(DeepInheritance, (bool, type(None)))
        assert isinstance(LocalOnly, (bool, type(None)))
        assert isinstance(IncludeQualifiers, (bool, type(None)))
        assert isinstance(IncludeClassOrigin, (bool, type(None)))

        self.validate_namespace(namespace)

        class_store = self.cimrepository.get_class_store(namespace)

        if ClassName:
            if not class_store.object_exists(ClassName):
                raise CIMError(
                    CIM_ERR_INVALID_CLASS,
                    _format("The class {0!A} defined by 'ClassName' parameter "
                            "does not exist in namespace {1!A}",
                            ClassName, namespace))

        clns = self._get_subclass_names(ClassName, class_store,
                                        DeepInheritance)

        # Get each class and process it for the modifiers.
        classes = [
            self.get_class(namespace, cln,
                           local_only=LocalOnly,
                           include_qualifiers=IncludeQualifiers,
                           include_classorigin=IncludeClassOrigin)
            for cln in clns]

        return classes

    def EnumerateClassNames(self, namespace, ClassName=None,
                            DeepInheritance=None):
        """
        Provider method for
        :meth:`pywbem.WBEMConnection.EnumerateClassNames`.

        Enumerate the class names that are subclasses of the class name in the
        `classname` parameter or from the top of the class hierarchy if
        `classname` is None.

        Parameters:

          namespace (:term:`string`):
            The name of the CIM namespace in the CIM repository (case
            insensitive). Must not be `None`. Leading or trailing
            slash characters are ignored.

          ClassName (:term:`string`):
            Name of the class whose subclasses are to be retrieved
            (case independent).

            If `None`, the top-level classes in the namespace will be
            retrieved.

          DeepInheritance (:class:`py:bool`):
            Indicates that all (direct and indirect) subclasses of the
            specified class or of the top-level classes are to be included in
            the result, as follows:

            * If `False`, only direct subclasses of the specified class or only
              top-level classes are included in the result.
            * If `True`, all direct and indirect subclasses of the specified
              class or the top-level classes and all of their direct and
              indirect subclasses are included in the result.
            * If `None`, this parameter is treated as False, as defined in
              :term:`DSP0200` (server-implemented default is `False`).

            Note, the semantics of the `DeepInheritance` parameter in
            :meth:`pywbem.WBEMConnection.EnumerateInstances` is different.

        Returns:

            A list of :term:`unicode string` objects that are the class names
            of the enumerated classes

        Raises:

            :exc:`~pywbem.CIMError`: (CIM_ERR_INVALID_NAMESPACE)
            :exc:`~pywbem.CIMError`: (CIM_ERR_INVALID_CLASS) class defined by
              the classname parameter does not exist.
        """

        # Parameter types are already checked by WBEMConnection operation
        assert isinstance(namespace, six.string_types)
        assert isinstance(ClassName, (six.string_types, type(None)))
        assert isinstance(DeepInheritance, (bool, type(None)))

        self.validate_namespace(namespace)

        class_store = self.cimrepository.get_class_store(namespace)

        if ClassName:
            if not class_store.object_exists(ClassName):
                raise CIMError(
                    CIM_ERR_INVALID_CLASS,
                    _format("The class {0!A} defined by 'ClassName' parameter "
                            "does not exist in namespace {1!A}",
                            ClassName, namespace))

        # Return list of subclass names
        return self._get_subclass_names(ClassName, class_store, DeepInheritance)

    def GetClass(self, namespace, ClassName, LocalOnly=None,
                 IncludeQualifiers=None, IncludeClassOrigin=None,
                 PropertyList=None):
        # pylint: disable=line-too-long
        """
        Provider method for
        :meth:`pywbem.WBEMConnection.GetClass`.

        Retrieve a CIM class from the CIM repository.

        Parameters:

          namespace (:term:`string`):
            The name of the CIM namespace in the CIM repository (case
            insensitive). Must not be `None`. Leading or trailing
            slash characters are ignored.

          ClassName (:term:`string`):
            Name of the class to be retrieved (case independent).

          LocalOnly (:class:`py:bool`):
            Indicates that inherited properties, methods, and qualifiers are to
            be excluded from the returned class, as follows.

            * If `False`, inherited elements are not excluded.
            * If `True`, inherited elements are excluded.
            * If `None`, uses :term:`DSP0200` defined server default of `True`.

          IncludeQualifiers (:class:`py:bool`):
            Indicates that qualifiers are to be included in the returned
            class, as follows:

            * If `False`, qualifiers are not included.
            * If `True`, qualifiers are included.
            * If `None`, uses :term:`DSP0200` defined server default of `True`.

          IncludeClassOrigin (:class:`py:bool`):
            Indicates that class origin information is to be included on each
            property and method in the returned class, as follows:

            * If `False`, class origin information is not included.
            * If `True`, class origin information is included.
            * If `None`, uses :term:`DSP0200` defined server default of `False`.

          PropertyList (:term:`string` or :term:`py:iterable` of :term:`string`):
            An iterable specifying the names of the properties (or a string
            that defines a single property) to be included in the returned
            class (case independent).

            An empty iterable indicates to include no properties.

            If `None`, all properties are included.

        Returns:

            :class:`~pywbem.CIMClass` object that is a representation of the
            retrieved class

        Raises:

            :exc:`~pywbem.CIMError`: (CIM_ERR_INVALID_NAMESPACE)
            :exc:`~pywbem.CIMError`: (CIM_ERR_INVALID_CLASS)
        """  # noqa: E501
        # pylint: enable=line-too-long

        # Parameter types are already checked by WBEMConnection operation
        assert isinstance(namespace, six.string_types)
        assert isinstance(ClassName, six.string_types)
        assert isinstance(LocalOnly, (bool, type(None)))
        assert isinstance(IncludeQualifiers, (bool, type(None)))
        assert isinstance(IncludeClassOrigin, (bool, type(None)))
        assert isinstance(PropertyList,
                          (six.string_types, list, tuple, type(None)))

        self.validate_namespace(namespace)

        cc = self.get_class(namespace, ClassName, local_only=LocalOnly,
                            include_qualifiers=IncludeQualifiers,
                            include_classorigin=IncludeClassOrigin,
                            property_list=PropertyList)

        return cc

    def CreateClass(self, namespace, NewClass):
        """
        Provider method for
        :meth:`pywbem.WBEMConnection.CreateClass`.

        Creates a new class in the CIM repository.  Nothing is returned.

        Classes that are in the CIM repository contain the qualifiers,
        properties, and methods of that class and the propagated properties of
        the superclasses.  The NewClass object contains only the qualifiers,
        properties, and methods of the new class including any override
        qualifiers necessary to allow the complete class to be created.

        Parameters:

          namespace (:term:`string`):
            The name of the CIM namespace in the CIM repository (case
            insensitive). Must not be `None`. Leading or trailing
            slash characters are ignored.

          NewClass (:class:`~pywbem.CIMClass`):
            A representation of the class to be created.

            The properties, methods and qualifiers defined in this object
            specify how the class is to be created.

            Its `path` attribute is ignored.

        Raises:

            :exc:`~pywbem.CIMError`: (CIM_ERR_INVALID_NAMESPACE)
            :exc:`~pywbem.CIMError`: (CIM_ERR_INVALID_PARAMETER)
            :exc:`~pywbem.CIMError`: (CIM_ERR_INVALID_SUPERCLASS)
            :exc:`~pywbem.CIMError`: (CIM_ERR_ALREADY_EXISTS)
        """

        # Parameter types are already checked by WBEMConnection operation
        assert isinstance(namespace, six.string_types)
        assert isinstance(NewClass, CIMClass)

        self.validate_namespace(namespace)

        class_store = self.cimrepository.get_class_store(namespace)
        if class_store.object_exists(NewClass.classname):
            raise CIMError(
                CIM_ERR_ALREADY_EXISTS,
                _format("Class {0!A} already exists in namespace {1!A}.",
                        NewClass.classname, namespace))

        # Validate that classes upon which this class depends exist
        self._validate_dependencies_exist(NewClass, class_store, namespace)

        # Create copy because resolve_class modifies elements of class
        new_class = deepcopy(NewClass)

        qualifier_store = self.cimrepository.get_qualifier_store(namespace)
        self._resolve_class(new_class, namespace, qualifier_store,
                            verbose=False)

        # Add new class to CIM repository
        class_store.create(new_class.classname, new_class)

    def ModifyClass(self, namespace, ModifiedClass):
        # pylint: disable=no-self-use,unused-argument
        """
        Provider method for :meth:`pywbem.WBEMConnection.ModifyClass`.

        Modifies an existing class in the CIM repository.  Nothing is returned.

        The modified class is rejected if subclasses to ModifiedClass exist,
        instances of ModifiedClass exist,  or the superclass name is different
        than the original superclass name.

        The ModifiedClass is resolved to validate properties, methods,
        parameters, qualifiers, and propagated values if a superclass is
        defined before it is inserted into the CIM repository.

        Parameters:

          namespace (:term:`string`):
            The name of the CIM namespace in the CIM repository (case
            insensitive). Must not be `None`. Leading or trailing
            slash characters are ignored.

          ModifiedClass (:class:`~pywbem.CIMClass`):
            A representation of the modified class.

            The properties, methods and qualifiers defined in this object
            specify what is to be modified.

        Raises:

            :exc:`~pywbem.CIMError`: (CIM_ERR_INVALID_NAMESPACE)
            :exc:`~pywbem.CIMError`: (CIM_ERR_INVALID_PARAMETER)
            :exc:`~pywbem.CIMError`: (CIM_ERR_NOT_FOUND)
        """
        # Parameter types are already checked by WBEMConnection operation
        assert isinstance(namespace, six.string_types)
        assert isinstance(ModifiedClass, CIMClass)

        self.validate_namespace(namespace)

        class_store = self.cimrepository.get_class_store(namespace)
        instance_store = self.cimrepository.get_instance_store(namespace)

        modifiedclass_name = ModifiedClass.classname

        if not class_store.object_exists(modifiedclass_name):
            raise CIMError(
                CIM_ERR_NOT_FOUND,
                _format("Class {0!A} does not exist in namespace {1!A}.",
                        modifiedclass_name, namespace))

        # Error if there are subclasses
        subclns = self._get_subclass_names(modifiedclass_name,
                                           class_store, False)
        if subclns:
            raise CIMError(
                CIM_ERR_CLASS_HAS_CHILDREN,
                _format("Class {0!A} namespace {1!A} cannot be modified "
                        "because it has subclasses.",
                        modifiedclass_name, namespace))

        # Error if there are instances
        clns = NocaseList([modifiedclass_name])
        inst_paths = [inst.path for inst in instance_store.iter_values()
                      if inst.path.classname in clns]
        if inst_paths:
            raise CIMError(
                CIM_ERR_CLASS_HAS_INSTANCES,
                _format("Class {0!A} namespace {1!A} cannot be modified "
                        "because it has instances.",
                        ModifiedClass.classname, namespace))

        # Error if superclass defined and does not exist.
        if ModifiedClass.superclass:
            if not class_store.object_exists(ModifiedClass.superclass):
                raise CIMError(
                    CIM_ERR_INVALID_SUPERCLASS,
                    _format("Superclass {0!A} for class {1!A} does not exist "
                            "in namespace {2!A}.", ModifiedClass.superclass,
                            modifiedclass_name, namespace))

        # Get original class
        orig_class = class_store.get(modifiedclass_name)

        # Error if original and modified classes do not have the same
        # superclass name or both both not None
        if (ModifiedClass.superclass is None and orig_class.superclass) \
                or (ModifiedClass.superclass and orig_class.superclass is None):
            raise CIMError(
                CIM_ERR_INVALID_SUPERCLASS,
                _format("Superclass name in modified class {0!A} "
                        "in namespace {1!A} and in original class "
                        "must both exist: original superclass ",
                        "name {2!A}; modified superclass name {3!A}",
                        modifiedclass_name, namespace,
                        orig_class.superclass or "''",
                        ModifiedClass.superclass or "''"))

        # else they must both exist and be equal
        if ModifiedClass.superclass and orig_class.superclass:
            if orig_class.superclass.lower() != \
                    ModifiedClass.superclass.lower():
                raise CIMError(
                    CIM_ERR_INVALID_SUPERCLASS,
                    _format("Superclass name in modified class {0!A} "
                            "in namespace {1!A} different than superclass "
                            "name in the modified class: original "
                            "superclass name {2!A}; modified superclass "
                            "name {3!A}",
                            modifiedclass_name, namespace,
                            orig_class.superclass,
                            ModifiedClass.superclass))

        # Validate that classes upon which this class depends exist
        self._validate_dependencies_exist(ModifiedClass, class_store, namespace)

        # Create copy because resolve_class can modify elements of class
        modified_class = deepcopy(ModifiedClass)

        qualifier_store = self.cimrepository.get_qualifier_store(namespace)
        self._resolve_class(modified_class, namespace, qualifier_store,
                            verbose=False)

        # Update class in CIM repository
        class_store.update(modified_class.classname, modified_class)

    def DeleteClass(self, namespace, ClassName):
        """
        Provider method for
        :meth:`pywbem.WBEMConnection.DeleteClass`.

        Delete a class in the class CIM repository if it exists.

        This method also deletes any subclasses and CIM instances of
        the target class or its subclasses.

        Nothing is returned.

        Parameters:

          namespace (:term:`string`):
            The name of the CIM namespace in the CIM repository (case
            insensitive). Must not be `None`. Leading or trailing
            slash characters are ignored.

          ClassName (:term:`string`):
            Name of the class to be deleted (case independent).

        Raises:

            :exc:`~pywbem.CIMError`: (CIM_ERR_INVALID_NAMESPACE)
            :exc:`~pywbem.CIMError`: (CIM_ERR_NOT_FOUND)
        """

        # Parameter types are already checked by WBEMConnection operation
        assert isinstance(namespace, six.string_types)
        assert isinstance(ClassName, six.string_types)

        self.validate_namespace(namespace)

        class_store = self.cimrepository.get_class_store(namespace)
        instance_store = self.cimrepository.get_instance_store(namespace)

        if not class_store.object_exists(ClassName):
            raise CIMError(
                CIM_ERR_NOT_FOUND,
                _format("Class {0!A} in namespace {1!A} not in CIM repository. "
                        "Nothing deleted.", ClassName, namespace))

        # create list of subclass names and append the target class
        classnames = self._get_subclass_names(ClassName, class_store, True)
        classnames.append(ClassName)

        # Delete all instances in this class and subclasses and delete
        # this class and subclasses
        for clname in classnames:
            sub_clns = self._get_subclass_list_for_enums(ClassName, namespace,
                                                         class_store)

            inst_paths = [inst.path for inst in instance_store.iter_values()
                          if inst.path.classname in sub_clns]

            # Routes instance delete calls through the ProviderDispatcher to
            # assure that providers get called rather than calling the
            # CIM repository directly.
            for ipath in inst_paths:
                self.providerdispatcher.DeleteInstance(ipath)

            class_store.delete(clname)

    ##########################################################
    #
    #   Qualifier-related provider methods
    #
    ###########################################################

    def EnumerateQualifiers(self, namespace):
        """
        Provider method for
        :meth:`pywbem.WBEMConnection.EnumerateQualifiers`.

        Enumerates the qualifier declarations in the local CIM repository of
        namespace.

        Parameters:

          namespace (:term:`string`):
            The name of the CIM namespace in the CIM repository (case
            insensitive). Must not be `None`. Leading or trailing
            slash characters are ignored.

        Returns:

            A list of :class:`~pywbem.CIMQualifierDeclaration` objects that are
            representations of the enumerated qualifier declarations.

        Raises:

            :exc:`~pywbem.CIMError`: (CIM_ERR_INVALID_NAMESPACE)
        """

        # Parameter types are already checked by WBEMConnection operation
        assert isinstance(namespace, six.string_types)

        self.validate_namespace(namespace)

        qualifier_store = self.cimrepository.get_qualifier_store(namespace)

        # pylint: disable=unnecessary-comprehension
        qualifiers = [q for q in qualifier_store.iter_values()]

        return qualifiers

    def GetQualifier(self, namespace, QualifierName):
        """
        Provider method for
        :meth:`pywbem.WBEMConnection.GetQualifier`.

        Retrieves a qualifier declaration from the local CIM repository of this
        namespace.

        Parameters:

          namespace (:term:`string`):
            The name of the CIM namespace in the CIM repository (case
            insensitive). Must not be `None`. Leading or trailing
            slash characters are ignored.

          QualifierName (:term:`string`):
            Name of the qualifier declaration to be retrieved
            (case independent).

        Returns:

          :class:`~pywbem.CIMQualifierDeclaration`: a representation of the
          retrieved qualifier declaration.

        Raises:

            :exc:`~pywbem.CIMError`: (CIM_ERR_INVALID_NAMESPACE)
            :exc:`~pywbem.CIMError`: (CIM_ERR_INVALID_PARAMETER)
            :exc:`~pywbem.CIMError`: (CIM_ERR_NOT_FOUND)
        """

        # Parameter types are already checked by WBEMConnection operation
        assert isinstance(namespace, six.string_types)
        assert isinstance(QualifierName, six.string_types)

        self.validate_namespace(namespace)

        qualifier_store = self.cimrepository.get_qualifier_store(namespace)

        try:
            qualifier = qualifier_store.get(QualifierName)
        except KeyError:
            ce = CIMError(
                CIM_ERR_NOT_FOUND,
                _format("Qualifier declaration {0!A} not found in namespace "
                        "{1!A}.", QualifierName, namespace))
            raise ce

        return qualifier

    def SetQualifier(self, namespace, QualifierDeclaration):
        """
        Provider method for
        :meth:`pywbem.WBEMConnection.SetQualifier`.

        Create or modify a qualifier declaration in the CIM repository of this
        class.  This method will create a new namespace for the qualifier
        if none is defined.

        Parameters:

          namespace (:term:`string`):
            The name of the CIM namespace in the CIM repository (case
            insensitive). Must not be `None`. Leading or trailing
            slash characters are ignored.

          QualifierDeclaration (:class:`~pywbem.CIMQualifierDeclaration`):
            Representation of the qualifier declaration to be created or
            modified.

        Raises:

            :exc:`~pywbem.CIMError`: (CIM_ERR_INVALID_NAMESPACE)
            :exc:`~pywbem.CIMError`: (CIM_ERR_INVALID_PARAMETER)
        """

        # Parameter types are already checked by WBEMConnection operation
        assert isinstance(namespace, six.string_types)
        assert isinstance(QualifierDeclaration, CIMQualifierDeclaration)

        self.validate_namespace(namespace)

        qualifier_store = self.cimrepository.get_qualifier_store(namespace)

        # Try to create and if that fails, modify the existing qualifier decl
        try:
            qualifier_store.create(
                QualifierDeclaration.name, QualifierDeclaration)
        except ValueError:
            qualifier_store.update(
                QualifierDeclaration.name, QualifierDeclaration)

    def DeleteQualifier(self, namespace, QualifierName):
        """
        Provider method for
        :meth:`pywbem.WBEMConnection.DeleteQualifier`.

        Deletes a single qualifier declaration if it is in the CIM repository
        for this namespace and is not being used by any class in the namespace.

        Parameters:

          namespace (:term:`string`):
            The name of the CIM namespace in the CIM repository (case
            insensitive). Must not be `None`. Leading or trailing slash
            characters are ignored.

          QualifierName (:term:`string`):
            Name of the qualifier declaration to be deleted (case independent).

        Raises:

            :exc:`~pywbem.CIMError`: (CIM_ERR_INVALID_NAMESPACE)
            :exc:`~pywbem.CIMError`: (CIM_ERR_INVALID_PARAMETER)
            :exc:`~pywbem.CIMError`: (CIM_ERR_NOT_FOUND)
            :exc:`~pywbem.CIMError`: (CIM_ERR_FAILED)

        """
        def qualifier_exists_in_cls(cls, qualifier_name):
            """
            Test for qualifier exists in any component of the class cls.

            Parameters:
              cls (:class:`~pywbem.CIMClass`)
                CIM class to search for existence of qualifier
              qualifier_name (:term:`string`):
                Name of qualifier for which search is executed

            Returns:
                :class:`py:bool` True if qualifier exists, False if qualifier
                not found in the class
            """
            if qualifier_name in cls.qualifiers:
                return True
            for prop in six.itervalues(cls.properties):
                if qualifier_name in prop.qualifiers:
                    return True
            for method in six.itervalues(cls.methods):
                if qualifier_name in method.qualifiers:
                    return True
                for parameter in six.itervalues(method.parameters):
                    if qualifier_name in parameter.qualifiers:
                        return True
            return False
        # Parameter types are already checked by WBEMConnection operation
        assert isinstance(namespace, six.string_types)
        assert isinstance(QualifierName, six.string_types)

        self.validate_namespace(namespace)

        qualifier_store = self.cimrepository.get_qualifier_store(namespace)

        if qualifier_store.object_exists(QualifierName):
            # if qualifier exists in any class in ns generate exception
            class_store = self.cimrepository.get_class_store(namespace)
            for cls in class_store.iter_values(copy=False):
                if qualifier_exists_in_cls(cls, QualifierName):
                    raise CIMError(
                        CIM_ERR_FAILED,
                        _format("QualifierDeclaration {0!A} namespace {1!A} "
                                "cannot be deleted. "
                                "It is being used at least in class {2!A}.",
                                QualifierName, namespace, cls.classname))
            qualifier_store.delete(QualifierName)
        else:
            raise CIMError(
                CIM_ERR_NOT_FOUND,
                _format("QualifierDeclaration {0!A} not found in namespace "
                        "{1!A}.", QualifierName, namespace))

    #####################################################################
    #
    #  Instance-related provider methods
    #
    #####################################################################

    def GetInstance(self, InstanceName, LocalOnly=None,
                    IncludeQualifiers=None, IncludeClassOrigin=None,
                    PropertyList=None):
        # pylint: disable=line-too-long
        """
        Provider method for
        :meth:`pywbem.WBEMConnection.GetInstance`.

        Gets a single instance from the CIM repository based on the
        InstanceName and filters it for PropertyList, etc.

        This method uses a common CIM repository access method _get_instance to
        get, copy, and process the instance.

        NOTE: This method includes namespace within the InstanceName rather
        than as a separate input argument.

        Parameters:

          InstanceName (:class:`~pywbem.CIMInstanceName`):
            The instance path of the instance to be retrieved  with the
            following attributes:

            * `classname`: Name of the creation class of the instance.
            * `keybindings`: Keybindings of the instance.
            * `namespace`: Name of the CIM namespace containing the instance.
              Must not be None.
            * `host`: value ignored.

          LocalOnly (:class:`py:bool`):
            This parameter is used to control the exclusion of inherited
            properties in the returned instances. :term:`DSP0200` version 1.2
            has deprecated this parameter and allows servers to honor it, or to
            treat it as False, as long as that is done consistently.

            This provider ignores the parameter and treats it as False, so that
            inherited properties are included in the returned instances. This
            is consistent with the recommendation in DSP0200 for clients to set
            the parameter to False.

          IncludeQualifiers (:class:`py:bool`):
            Indicates that qualifiers are to be included in the returned
            instance, as follows:

            * If `False`, qualifiers are not included.
            * If `True`, qualifiers are included if the WBEM server implements
              support for this parameter.
            * If `None`, the :term:`DSP0200` defined server default `False`
              is used.

            This parameter has been deprecated in :term:`DSP0200`. Clients
            cannot rely on qualifiers to be returned in this operation.
            The value of this argument may be overridden by the
            IGNORE_INSTANCE_IQ_PARAM config variable. The default config
            value is True(ignore this parameter and use False)

          IncludeClassOrigin (:class:`py:bool`):
            Indicates that class origin information is to be included on each
            property in the returned instance, as follows:

            * If `False`, class origin information is not included.
            * If `True`, class origin information is included.
            * If `None`, uses :term:`DSP0200` server default `False`.

            The value of this argument may be overridden by the
            IGNORE_INSTANCE_ICO_PARAM config variable. The default config
            value is True(ignore this parameter and use False)

          PropertyList (:term:`string` or :term:`py:iterable` of :term:`string`):
            An iterable specifying the names of the properties (or a string
            that defines a single property) to be included in the returned
            instance (case independent).

            An empty iterable indicates to include no properties.

            If `None`, all properties are included.

        Returns:

            A :class:`~pywbem.CIMInstance` object that is a representation of
            the retrieved instance.
            Its `path` attribute is a :class:`~pywbem.CIMInstanceName` object
            with its attributes set as follows:

            * `classname`: Name of the creation class of the instance.
            * `keybindings`: Keybindings of the instance.
            * `namespace`: Name of the CIM namespace containing the instance.
            * `host`: `None`, indicating the WBEM server is unspecified.

        Raises:

            :exc:`~pywbem.CIMError`: (CIM_ERR_INVALID_NAMESPACE)
            :exc:`~pywbem.CIMError`: (CIM_ERR_INVALID_CLASS)
            :exc:`~pywbem.CIMError`: (CIM_ERR_NOT_FOUND)
        """  # noqa: E501
        # pylint: enable=line-too-long

        # Parameter types are already checked by WBEMConnection operation
        assert isinstance(InstanceName, CIMInstanceName)
        assert isinstance(LocalOnly, (bool, type(None)))
        assert isinstance(IncludeQualifiers, (bool, type(None)))
        assert isinstance(IncludeClassOrigin, (bool, type(None)))
        assert isinstance(PropertyList,
                          (six.string_types, list, tuple, type(None)))

        namespace = InstanceName.namespace
        self.validate_namespace(namespace)
        iname = InstanceName

        instance_store = self.cimrepository.get_instance_store(namespace)

        if not self.class_exists(namespace, iname.classname):
            raise CIMError(
                CIM_ERR_INVALID_CLASS,
                _format("Class {0!A} for GetInstance of instance {1!A} "
                        "does not exist.", iname.classname, iname))
        # Set LocalOnly to False as fixed value.
        LocalOnly = INSTANCE_RETRIEVE_LOCAL_ONLY
        return self._get_instance(iname, instance_store,
                                  LocalOnly,
                                  IncludeClassOrigin,
                                  IncludeQualifiers, PropertyList)

    def EnumerateInstances(self, namespace, ClassName, LocalOnly=None,
                           DeepInheritance=None, IncludeQualifiers=None,
                           IncludeClassOrigin=None, PropertyList=None):
        # pylint: disable=line-too-long
        """
        Provider method for
        :meth:`pywbem.WBEMConnection.EnumerateInstances`.

        Enumerate the instances of a class (including instances of its
        subclasses) in a namespace.

        Parameters:

          namespace (:term:`string`):
            The name of the CIM namespace in the CIM repository (case
            insensitive). Must not be `None`. Leading or trailing slash
            characters are ignored.

          ClassName (:term:`string`):
            Name of the class for which instances are to be enumerated (case
            independent).

          LocalOnly (:class:`py:bool`):
            This parameter is used to control the exclusion of inherited
            properties in the returned instances. :term:`DSP0200` version 1.2
            has deprecated this parameter and allows servers to honor it, or to
            treat it as False, as long as that is done consistently.

            This provider ignores the parameter and treats it as False, so that
            inherited properties are included in the returned instances. This
            is consistent with the recommendation in DSP0200 for clients to set
            the parameter to False.

          DeepInheritance (:class:`py:bool`):
            Indicates that properties added by subclasses of the specified
            class are to be included in the returned instances, as follows:

            * If `False`, properties added by subclasses are not included.
            * If `True`, properties added by subclasses are included.
            * If `None`, (not received from client) this parameter acts as
              if  the value is `True` in accord with :term:`DSP0200`.

            Note, the semantics of the `DeepInheritance` parameter in
            :meth:`pywbem.WBEMConnection.EnumerateClasses` and
            :meth:`pywbem.WBEMConnection.EnumerateClassNames`
            is different.

          IncludeQualifiers (:class:`py:bool`):
            This parameter has been deprecated in :term:`DSP0200`. and this
            provider ignores it and never returns qualifiers.

          IncludeClassOrigin (:class:`py:bool`):
            Indicates that class origin information is to be included on each
            property in the returned instances, as follows:

            * If `False`, class origin information is not included.
            * If `True`, class origin information is included.
            * If `None`, this parameter is treated as `False`.

            This parameter has been deprecated in :term:`DSP0200`. This
            implementation treats this parameter always as if the value is
            `False`.

          PropertyList (:term:`string` or :term:`py:iterable` of :term:`string`):
            An iterable specifying the names of the properties (or a string
            that defines a single property) to be included in the returned
            instances (case independent).

            An empty iterable indicates to include no properties.

            If `None`, all properties are included.

        Returns:

          A list of :class:`~pywbem.CIMInstance` objects that are
          representations of the enumerated instances.

          The `path` attribute of each :class:`~pywbem.CIMInstance`
          object is a :class:`~pywbem.CIMInstanceName` object with its
          attributes set as follows:

          * `classname`: Name of the creation class of the instance.
          * `keybindings`: Keybindings of the instance.
          * `namespace`: Name of the CIM namespace containing the instance.
          * `host`: `None`, indicating the WBEM server is unspecified.

        Raises:

            :exc:`~pywbem.CIMError`: (CIM_ERR_INVALID_NAMESPACE)
            :exc:`~pywbem.CIMError`: (CIM_ERR_INVALID_CLASS)
        """  # noqa: E501
        # pylint: enable=line-too-long

        # Parameter types are already checked by WBEMConnection operation
        assert isinstance(namespace, six.string_types)
        assert isinstance(ClassName, six.string_types)
        assert isinstance(LocalOnly, (bool, type(None)))
        assert isinstance(DeepInheritance, (bool, type(None)))
        assert isinstance(IncludeQualifiers, (bool, type(None)))
        assert isinstance(IncludeClassOrigin, (bool, type(None)))
        assert isinstance(PropertyList,
                          (six.string_types, list, tuple, type(None)))

        self.validate_namespace(namespace)

        instance_store = self.cimrepository.get_instance_store(namespace)
        class_store = self.cimrepository.get_class_store(namespace)

        # If DeepInheritance False use only properties from the original
        # class. Modify property list to limit properties to those from this
        # class.  This only works if class exists. If class not in
        # CIM repository, ignore DeepInheritance.

        # If None, set to server default
        if DeepInheritance is None:
            DeepInheritance = DEFAULT_DEEP_INHERITANCE

        pl = PropertyList

        try:
            cl = self.get_class(namespace, ClassName, local_only=False)
        except CIMError as exc:
            if exc.status_code == CIM_ERR_NOT_FOUND:
                raise CIMError(
                    CIM_ERR_INVALID_CLASS,
                    _format("Class {0!A} not found in namespace {1!A}.",
                            ClassName, namespace))
            raise

        # Get class property list which may be localonly or all
        # superclasses
        class_pl = cl.properties.keys()

        # If not DeepInheritance, compute property list to filter
        # all instances to the properties in the target class as modified
        # by the PropertyList
        if not DeepInheritance:
            if pl is None:  # properties in class form property list
                pl = class_pl
            else:      # reduce pl to properties in class_properties
                pl_lower = [pc.lower() for pc in pl]
                pl = [pc for pc in class_pl if pc.lower() in pl_lower]

        # Create dictionary of all subclasses.
        clns_dict = self._get_subclass_list_for_enums(ClassName, namespace,
                                                      class_store)

        # get and process instances from the instance_store
        LocalOnly = INSTANCE_RETRIEVE_LOCAL_ONLY
        insts = [self._get_instance(inst.path, instance_store,
                                    LocalOnly,
                                    IncludeClassOrigin,
                                    IncludeQualifiers, pl)
                 for inst in instance_store.iter_values()
                 if inst.path.classname in clns_dict]

        return insts

    def EnumerateInstanceNames(self, namespace, ClassName):
        """
        Provider method for
        :meth:`pywbem.WBEMConnection.EnumerateInstanceNames`.

        Enumerate the instance paths of instances of a class (including
        instances of its subclasses) in a namespace.

        Parameters:

          namespace (:term:`string`):
            The name of the CIM namespace in the CIM repository (case
            insensitive). Must not be `None`. Leading or trailing slash
            characters are ignored.

          ClassName (:term:`string`):
            Name of the class to be enumerated (case independent).

        Returns:

          A list of :class:`~pywbem.CIMInstanceName` objects that are the
          enumerated instance paths, with its attributes set
          as follows:

          * `classname`: Name of the creation class of the instance.
          * `keybindings`: Keybindings of the instance.
          * `namespace`: Name of the CIM namespace containing the instance.
          * `host`: `None`, indicating the WBEM server is unspecified.

        Raises:

            :exc:`~pywbem.CIMError`: (CIM_ERR_INVALID_NAMESPACE)
            :exc:`~pywbem.CIMError`: (CIM_ERR_INVALID_PARAMETER)
            :exc:`~pywbem.CIMError`: (CIM_ERR_INVALID_CLASS)
        """

        # Parameter types are already checked by WBEMConnection operation
        assert isinstance(namespace, six.string_types)
        assert isinstance(ClassName, six.string_types)

        self.validate_namespace(namespace)

        instance_store = self.cimrepository.get_instance_store(namespace)
        class_store = self.cimrepository.get_class_store(namespace)

        clns = self._get_subclass_list_for_enums(ClassName, namespace,
                                                 class_store)

        inst_paths = [inst.path for inst in instance_store.iter_values()
                      if inst.path.classname in clns]

        return_paths = [path.copy() for path in inst_paths]

        return return_paths

    def ExecQuery(self, namespace, QueryLanguage, Query):
        # pylint: disable=unused-argument,no-self-use
        """
        Provider method for
        :meth:`pywbem.WBEMConnection.ExecQuery`.

        Executes the the query defined by the QueryLanguage and Query parameter
        in the namespace defined.

        NOTE: This operation currently returns CIM_ERR_NOT_SUPPORTED

        Parameters:

          namespace (:term:`string`):
            The name of the CIM namespace in the CIM repository (case
            insensitive). Must not be `None`. Leading or trailing slash
            characters are ignored.

          QueryLanguage (:term:`string`):
            Name of the query language used in the `Query` parameter, e.g.
            "DMTF:CQL" for CIM Query Language, and "WQL" for WBEM Query
            Language.

          Query (:term:`string`):
            Query string in the query language specified in the `QueryLanguage`
            parameter.

        Returns:

            A list of :class:`~pywbem.CIMInstance` objects that represents
            the query result.

            These instances have their `path` attribute set to identify
            their creation class and the target namespace of the query, but
            they are not addressable instances.

        Raises:

            :exc:`~pywbem.CIMError`: (CIM_ERR_NOT_SUPPORTED)
        """

        raise CIMError(
            CIM_ERR_NOT_SUPPORTED,
            "ExecQuery not implemented!")

    #####################################################################
    #
    #  Faked WBEMConnection Reference and Associator methods
    #
    #####################################################################

    def _return_assoc_class_tuples(self, rtn_classnames, namespace, iq, ico,
                                   pl):
        """
        Creates the correct tuples for associator and references class
        level responses from a list of classnames.  This is unique because
        the class level references and associators return a tuple of
        CIMClassName and CIMClass for every entry.
        """

        rtn_tups = []
        for cn in rtn_classnames:
            rtn_tups.append((CIMClassName(cn, namespace=namespace,
                                          host=self.host),
                             self.get_class(namespace, cn,
                                            include_qualifiers=iq,
                                            include_classorigin=ico,
                                            property_list=pl)))
        return rtn_tups

    def _subclasses_lc(self, classname, class_store):
        """
        Return a list of this class and it subclasses in lower case.
        Exception if class is not in CIM repository.
        """
        if not classname:
            return []
        clns = [classname]
        clns.extend(self._get_subclass_names(classname, class_store, True))
        return [cln.lower() for cln in clns]

    def _validate_class_exists(self, namespace, cln, req_param="TargetClass"):
        """
        Common test for the References and Associators requests to test for the
        existence of the class named cln in namespace.

        Returns if the class exists.

        If the class does not exist, executes an INVALID_PARAMETER
        exception which is the specified exception for invalid classes for
        the TargetClass, AssocClass, and ResultClass for reference and
        associator operations
        """
        if not self.class_exists(namespace, cln):
            raise CIMError(
                CIM_ERR_INVALID_PARAMETER,
                _format('Class {0!A} {1} parameter not found in namespace '
                        '{2!A}.', cln, req_param, namespace))

    @staticmethod
    def _ref_prop_matches(prop, target_classnames, ref_classname,
                          resultclass_names, role):
        """
        Test filters for a reference property
        Returns `True` if matches the criteria.

        Returns `False` if it does not match.

        The match criteria are:
          - target_classnames includes prop_reference_class
          - if result_classes are not None, ref_classname is in result_classes
          - If role is not None, prop name matches role
        """

        assert prop.type == 'reference'
        if prop.reference_class.lower() in target_classnames:
            if resultclass_names and ref_classname not in resultclass_names:
                return False
            if role and prop.name.lower() != role:
                return False
            return True
        return False

    @staticmethod
    def _assoc_prop_matches(prop, ref_classname,
                            assoc_classes, result_classes, result_role):
        """
        Test filters of a reference property and its associated entity
        Returns `True` if matches the criteria. Returns `False` if it does not
        match.

        Matches if ref_classname in assoc_classes, and result_role matches
        property name  and reference_class
        """

        assert prop.type == 'reference'
        if assoc_classes and ref_classname.lower() not in assoc_classes:
            return False
        if result_classes and  \
                prop.reference_class.lower() not in result_classes:
            return False
        if result_role and prop.name.lower() != result_role:
            return False
        return True

    def _get_reference_classnames(self, namespace, classname, result_class,
                                  role):
        """
        Get list of classnames that are references for which this classname
        is a target filtered by the result_class and role parameters if they
        are none.

        This is a common method used by all of the other reference and
        associator methods to create a list of reference classnames

        Returns:
            list of classnames that satisfy the criteria.
        """
        class_store = self.cimrepository.get_class_store(namespace)
        self._validate_class_exists(namespace, classname, "TargetClass")

        if result_class:
            self._validate_class_exists(namespace, result_class, "ResultClass")

        # get list of subclasses in lower case.
        result_classes = self._subclasses_lc(result_class, class_store)

        # Get the set of superclasses for the target classname and set
        # lower case
        target_classlist = self._get_superclass_names(classname, class_store)
        target_classlist.append(classname)
        target_classlist = [cn.lower() for cn in target_classlist]

        # add results to set to avoid any duplicates
        rtn_classnames_set = set()
        # set role to lowercase if it exists
        role = role.lower() if role else role

        # Iterate through class repo getting association classes for namespace
        for assoc_cl in self._iter_association_classes(namespace):
            for prop in six.itervalues(assoc_cl.properties):
                if prop.type == 'reference' and \
                        self._ref_prop_matches(prop, target_classlist,
                                               assoc_cl.classname.lower(),
                                               result_classes,
                                               role):
                    rtn_classnames_set.add(assoc_cl.classname)

        return list(rtn_classnames_set)

    def _get_reference_instnames(self, namespace, instname, result_class,
                                 role):
        """
        Get the reference instances from the CIM repository for the target
        instname and filtered by the result_class and role parameters.

        Returns a list of the reference instance names. The returned list is
        the original, not a copy so the user must copy them
        """

        instance_store = self.cimrepository.get_instance_store(namespace)
        class_store = self.cimrepository.get_class_store(namespace)

        # DSP0200 specifies INVALID_PARAMETER and not INVALID_CLASS
        if not class_store.object_exists(instname.classname):
            raise CIMError(
                # DSP0200 does not list not found errors for this operation.
                CIM_ERR_INVALID_PARAMETER,
                _format("Class {0!A} not found in namespace {1!A}.",
                        instname.classname, namespace))

        # Get list of class and subclasses in lower case
        if result_class:
            self._validate_class_exists(namespace, result_class, "ResultClass")
        resultclasses = self._subclasses_lc(result_class, class_store)

        instname.namespace = namespace
        role = role.lower() if role else None

        # ISSUE 2662  Search very wide here.  Not isolating to
        # associations and not limiting to expected result_classes. Consider
        # making list from get_reference_classnames if classes exist, otherwise
        # set list to instance_store to search all instances. This is just
        # a performance issue.

        rtn_instpaths = set()
        for inst in instance_store.iter_values():
            for prop in six.itervalues(inst.properties):
                if prop.type == 'reference':
                    # Does this prop instance name match target inst name
                    if prop.value == instname:
                        if result_class:
                            if inst.classname.lower() not in resultclasses:
                                continue
                        if role and prop.name.lower() != role:
                            continue
                        rtn_instpaths.add(inst.path)

        return rtn_instpaths

    def _get_associated_classnames(self, namespace, classname, assoc_class,
                                   result_class, result_role, role):
        """
        Get list of classnames that are associated classes for which this
        classname is a target filtered by the assoc_class, role, result_class,
        and result_role parameters if they are none.

        This is a common method used by all of the other reference and
        associator methods to create a list of reference classnames

        Returns:
            list of classnames that satisfy the criteria.
        """

        # Validate namespace and get class_store for this namespace
        class_store = self.cimrepository.get_class_store(namespace)
        if assoc_class:
            self._validate_class_exists(namespace, assoc_class, "AssocClass")

        if result_class:
            self._validate_class_exists(namespace, result_class, "ResultClass")

        # Get list of subclasses for result and assoc classes (lower case)
        result_classes = self._subclasses_lc(result_class, class_store)
        assoc_classes = self._subclasses_lc(assoc_class, class_store)

        rtn_classnames_set = set()

        role = role.lower() if role else role
        result_role = result_role.lower() if result_role else result_role

        ref_clns = self._get_reference_classnames(namespace, classname,
                                                  assoc_class, role)

        # Find reference properties that have multiple use of
        # same reference_class
        klasses = [class_store.get(cln) for cln in ref_clns]
        for cl in klasses:
            # Count reference property usage.
            pd = Counter([p.reference_class for p in
                          six.itervalues(cl.properties)
                          if p.type == 'reference'])
            single_use = [p for p, v in pd.items() if v == 1]

            for prop in six.itervalues(cl.properties):
                if prop.type == 'reference':
                    if self._assoc_prop_matches(prop,
                                                cl.classname,
                                                assoc_classes,
                                                result_classes,
                                                result_role):
                        # Test of referemce cln same as source class
                        if prop.reference_class == classname and \
                                prop.reference_class in single_use:
                            continue

                        rtn_classnames_set.add(prop.reference_class)

        return list(rtn_classnames_set)

    def _get_associated_instancenames(self, namespace, inst_name, assoc_class,
                                      result_class, result_role, role):
        """
        Get the reference instances from the CIM repository for the target
        instname and filtered by the result_class and role parameters.

        Returns a list of the reference instance names. The returned list is
        the original, not a copy so the user must copy them
        """

        instance_store = self.cimrepository.get_instance_store(namespace)
        class_store = self.cimrepository.get_class_store(namespace)

        if assoc_class:
            self._validate_class_exists(namespace, assoc_class, "AssocClass")

        if result_class:
            self._validate_class_exists(namespace, result_class, "ResultClass")

        result_classes = self._subclasses_lc(result_class, class_store)
        assoc_classes = self._subclasses_lc(assoc_class, class_store)

        inst_name.namespace = namespace
        role = role.lower() if role else role
        result_role = result_role.lower() if result_role else result_role

        ref_paths = self._get_reference_instnames(namespace, inst_name,
                                                  assoc_class, role)

        # Get associated instance names
        rtn_instpaths = set()
        for ref_path in ref_paths:
            inst = self._get_bare_instance(ref_path, instance_store)
            for prop in six.itervalues(inst.properties):
                if prop.type == 'reference':
                    if prop.value == inst_name:
                        if assoc_class \
                                and inst.classname.lower() not in assoc_classes:
                            continue
                        if role and prop.name.lower() != role:
                            continue
                    else:
                        if result_class and (prop.value.classname.lower()
                                             not in result_classes):
                            continue
                        if result_role and prop.name.lower() != result_role:
                            continue
                        rtn_instpaths.add(prop.value)
        return rtn_instpaths

    def ReferenceNames(self, namespace, ObjectName, ResultClass=None,
                       Role=None):
        """
        Provider method for
        :meth:`pywbem.WBEMConnection.ReferenceNames`.

        Retrieves the instance paths of the association instances that
        reference a source instance, or the class paths of the association
        classes that reference a source class from the CIM instances in the CIM
        repository. The association instances defining the relationship between
        ObjectName and result classes must exist in the CIM repository.

        Parameters:

          namespace (:term:`string`):
            The name of the CIM namespace in the CIM repository (case
            insensitive). Must not be `None`. Leading or trailing slash
            characters are ignored.

          ObjectName:
            The object path of the source object:

            * Instance-level use: The instance path of the source instance,
              as a :class:`~pywbem.CIMInstanceName` object.
              The `namespace` attribute of this object will be equal to the
              namespace parameter.
              Its `host` attribute of this object will be `None`.

            * Class-level use: The class path of the source class,
              as a :term:`string` object.
              The `namespace` attribute of this object will be equal to the
              namespace parameter.
              Its `host` attribute of this object will be `None`.

          ResultClass (:term:`string`):
            Class name of an association class (case independent),
            to filter the result to include only traversals of that association
            class (or subclasses).

            `None` means that no such filtering is peformed.

          Role (:term:`string`):
            Role name (= property name) of the source end (case independent),
            to filter the result to include only traversals from that source
            role.

            `None` means that no such filtering is peformed.

        Returns:

            : The returned list of objects depend on the usage:

            * For instance-level requests: A list of
              :class:`~pywbem.CIMInstanceName` objects that are the instance
              paths of the referencing association instances, with their
              attributes set as follows:

              * `classname`: Name of the creation class of the instance.
              * `keybindings`: Keybindings of the instance.
              * `namespace`: Name of the CIM namespace containing the instance.
              * `host`: Host and optionally port of the WBEM server containing
                the CIM namespace, or `None` if the server did not return host
                information.

            * For class-level requests: A list of :class:`~pywbem.CIMClassName`
              objects that are the class paths of the referencing association
              classes, with their attributes set as follows:

              * `classname`: Name of the class.
              * `namespace`: Name of the CIM namespace containing the class.
              * `host`: Host and optionally port of the WBEM server containing
                the CIM namespace, or `None` if the server did not return host
                information.

        Raises:

            :exc:`~pywbem.CIMError`: (CIM_ERR_INVALID_NAMESPACE)
        """

        # Parameter types are already checked by WBEMConnection operation
        assert isinstance(namespace, six.string_types)
        assert isinstance(ObjectName, (six.string_types, CIMInstanceName))
        assert isinstance(ResultClass, (six.string_types, type(None)))
        assert isinstance(Role, (six.string_types, type(None)))

        self.validate_namespace(namespace)

        if isinstance(ObjectName, CIMInstanceName):
            self._validate_instancename_namespace(namespace, ObjectName)
            ref_paths = self._get_reference_instnames(namespace, ObjectName,
                                                      ResultClass,
                                                      Role)
            rtn_names = [r.copy() for r in ref_paths]

            for iname in rtn_names:
                if iname.host is None:
                    iname.host = self.host

            return rtn_names

        ref_classnames = self._get_reference_classnames(namespace, ObjectName,
                                                        ResultClass, Role)

        ref_result = [CIMClassName(classname=cn, host=self.host,
                                   namespace=namespace)
                      for cn in ref_classnames]

        return ref_result

    def References(self, namespace, ObjectName, ResultClass=None, Role=None,
                   IncludeQualifiers=None, IncludeClassOrigin=None,
                   PropertyList=None):
        # pylint: disable=line-too-long
        """
        Provider method for
        :meth:`pywbem.WBEMConnection.References`.

        Parameters:

          namespace (:term:`string`):
            The name of the CIM namespace in the CIM repository (case
            insensitive). Must not be `None`. Leading or trailing slash
            characters are ignored.

          ObjectName:
            The object path of the source object:

            * Instance-level use: The instance path of the source instance,
              as a :class:`~pywbem.CIMInstanceName` object.
              The `namespace` attribute of this object will be equal to the
              namespace parameter.
              Its `host` attribute of this object will be `None`.

            * Class-level use: The class path of the source class,
              as a :term:`string` object.
              The `namespace` attribute of this object will be equal to the
              namespace parameter.
              Its `host` attribute of this object will be `None`.

          ResultClass (:term:`string`):
            Class name of an association class (case independent),
            to filter the result to include only traversals of that association
            class (or subclasses).

            `None` means that no such filtering is peformed.

          Role (:term:`string`):
            Role name (= property name) of the source end (case independent),
            to filter the result to include only traversals from that source
            role.

            `None` means that no such filtering is peformed.

          IncludeQualifiers (:class:`py:bool`):
            Indicates that qualifiers are to be included in the returned
            instances (or classes), as follows:

            * If `False`, qualifiers are not included.
            * If `True`, qualifiers are included if the WBEM server implements
              support for this parameter.
            * If `None`, this parameter is not passed to the WBEM server, and
              causes the server-implemented default to be used. :term:`DSP0200`
              defines that the server-implemented default is `False`.

            This parameter has been deprecated in :term:`DSP0200`. Clients
            cannot rely on qualifiers to be returned in this operation.

          IncludeClassOrigin (:class:`py:bool`):
            Indicates that class origin information is to be included on each
            property or method in the returned instances (or classes), as
            follows:

            * If `False`, class origin information is not included.
            * If `True`, class origin information is included.
            * If `None`, this parameter is not passed to the WBEM server, and
              causes the server-implemented default to be used. :term:`DSP0200`
              defines that the server-implemented default is `False`.

            This parameter has been deprecated in :term:`DSP0200` for
            instance-level use. WBEM servers may either implement this
            parameter as specified, or may treat any specified value as `False`.

          PropertyList (:term:`string` or :term:`py:iterable` of :term:`string`):
            An iterable specifying the names of the properties (or a string
            that defines a single property) to be included in the returned
            instances (or classes) (case independent).

            An empty iterable indicates to include no properties.

            If `None`, all properties are included.


        Returns:
            : The returned list of objects depend on the usage:

            * For instance-level requests: A list of
              :class:`~pywbem.CIMInstance` objects that are representations
              of the referencing association instances.

              The `path` attribute of each :class:`~pywbem.CIMInstance`
              object is a :class:`~pywbem.CIMInstanceName` object with its
              attributes set as follows:

              * `classname`: Name of the creation class of the instance.
              * `keybindings`: Keybindings of the instance.
              * `namespace`: Name of the CIM namespace containing the instance.
              * `host`: Host and optionally port of the WBEM server containing
                the CIM namespace, or `None` if the server did not return host
                information.

            * For class-level requests: A list of :func:`py:tuple` of
              (classpath, class) objects that are representations of the
              referencing association classes.

              Each tuple represents one class and has these items:

              * classpath (:class:`~pywbem.CIMClassName`): The class
                path of the class, with its attributes set as follows:

                * `classname`: Name of the class.
                * `namespace`: Name of the CIM namespace containing the class.
                * `host`: Host and optionally port of the WBEM server containing
                  the CIM namespace.

              * class (:class:`~pywbem.CIMClass`): The representation of the
                class, with its `path` attribute set to the `classpath` tuple
                item.

        Raises:

            :exc:`~pywbem.CIMError`: (CIM_ERR_INVALID_NAMESPACE)
        """  # noqa: E501
        # pylint: enable=line-too-long

        # Parameter types are already checked by WBEMConnection operation
        assert isinstance(namespace, six.string_types)
        assert isinstance(ObjectName, (six.string_types, CIMInstanceName))
        assert isinstance(ResultClass, (six.string_types, type(None)))
        assert isinstance(Role, (six.string_types, type(None)))
        assert isinstance(IncludeQualifiers, (bool, type(None)))
        assert isinstance(IncludeClassOrigin, (bool, type(None)))
        assert isinstance(PropertyList,
                          (six.string_types, list, tuple, type(None)))

        self.validate_namespace(namespace)

        if isinstance(ObjectName, CIMInstanceName):
            # This is an  instance reference
            self._validate_instancename_namespace(namespace, ObjectName)
            ref_paths = self._get_reference_instnames(namespace, ObjectName,
                                                      ResultClass,
                                                      Role)

            instance_store = self.cimrepository.get_instance_store(namespace)
            rtn_insts = [self._get_instance(path, instance_store,
                                            INSTANCE_RETRIEVE_LOCAL_ONLY,
                                            IncludeClassOrigin,
                                            IncludeQualifiers, PropertyList)
                         for path in ref_paths]

            for inst in rtn_insts:
                if inst.path.host is None:
                    inst.path.host = self.host

            return rtn_insts

        rtn_classnames = self._get_reference_classnames(namespace, ObjectName,
                                                        ResultClass, Role)
        # returns list of tuples of (CIMClassname, CIMClass)
        return self._return_assoc_class_tuples(rtn_classnames, namespace,
                                               IncludeQualifiers,
                                               IncludeClassOrigin,
                                               PropertyList)

    def AssociatorNames(self, namespace, ObjectName, AssocClass=None,
                        ResultClass=None, Role=None, ResultRole=None):
        # pylint: disable=invalid-name
        """
        Provider method for
        :meth:`pywbem.WBEMConnection.AssociatorNames`.

        Parameters:

          namespace (:term:`string`):
            The name of the CIM namespace in the CIM repository (case
            insensitive). Must not be `None`. Leading or trailing slash
            characters are ignored.

          ObjectName:
            The object path of the source object:

            * Instance-level use: The instance path of the source instance,
              as a :class:`~pywbem.CIMInstanceName` object.
              The `namespace` attribute of this object will be equal to the
              namespace parameter.
              Its `host` attribute of this object will be `None`.

            * Class-level use: The class path of the source class,
              as a :term:`string` object.
              The `namespace` attribute of this object will be equal to the
              namespace parameter.
              Its `host` attribute of this object will be `None`.

          See :meth:`pywbem.WBEMConnection.AssociatorNames` for description of
          remaining parameters

        Returns:

            * For instance-level requests
              (ObjectName is :class:`~pywbem.CIMInstanceName`): A list of
              :class:`~pywbem.CIMInstance` objects that are representations of
              the associated instances.

              The `path` attribute of each :class:`~pywbem.CIMInstance`
              object is a :class:`~pywbem.CIMInstanceName` object with its
              attributes set as follows:

              * `classname`: Name of the creation class of the instance.
              * `keybindings`: Keybindings of the instance.
              * `namespace`: Name of the CIM namespace containing the instance.
              * `host`: Host and optionally port of the WBEM server containing
                the CIM namespace, or `None` if the server did not return host
                information.

            * For class-level requests (ObjectName is :term:`string`):
              A list of :class:`~pywbem.CIMClassName` objects that are the
              class paths of the associated classes, with their attributes set
              as follows:

              * `classname`: Name of the class.
              * `namespace`: Name of the CIM namespace containing the class.
              * `host`: Host and optionally port of the WBEM server containing
                the CIM namespace.

        Raises:

            :exc:`~pywbem.CIMError`: (CIM_ERR_INVALID_NAMESPACE)
        """

        # Parameter types are already checked by WBEMConnection operation
        assert isinstance(namespace, six.string_types)
        assert isinstance(ObjectName, (six.string_types, CIMInstanceName))
        assert isinstance(AssocClass, (six.string_types, type(None)))
        assert isinstance(ResultClass, (six.string_types, type(None)))
        assert isinstance(Role, (six.string_types, type(None)))
        assert isinstance(ResultRole, (six.string_types, type(None)))

        self.validate_namespace(namespace)

        if isinstance(ObjectName, CIMInstanceName):
            self._validate_instancename_namespace(namespace, ObjectName)
            rtn_paths = self._get_associated_instancenames(namespace,
                                                           ObjectName,
                                                           AssocClass,
                                                           ResultClass,
                                                           ResultRole, Role)
            results = [p.copy() for p in rtn_paths]

            for iname in results:
                if iname.host is None:
                    iname.host = self.host

        else:
            rtn_classnames = self._get_associated_classnames(namespace,
                                                             ObjectName,
                                                             AssocClass,
                                                             ResultClass,
                                                             ResultRole, Role)
            # returns list of CIMClassName entities
            results = [CIMClassName(classname=cln, host=self.host,
                                    namespace=namespace)
                       for cln in rtn_classnames]

        return results

    def Associators(self, namespace, ObjectName, AssocClass=None,
                    ResultClass=None,
                    Role=None, ResultRole=None, IncludeQualifiers=None,
                    IncludeClassOrigin=None, PropertyList=None):
        """
        Provider method for
        :meth:`pywbem.WBEMConnection.Associators`.

        Parameters:

          namespace (:term:`string`):
            The name of the CIM namespace in the CIM repository (case
            insensitive). Must not be `None`. Leading or trailing slash
            characters are ignored.

          ObjectName:
            The object path of the source object:

            * Instance-level use: The instance path of the source instance,
              as a :class:`~pywbem.CIMInstanceName` object.
              The `namespace` attribute of this object will be equal to the
              namespace parameter.
              Its `host` attribute of this object will be `None`.

            * Class-level use: The class path of the source class,
              as a :term:`string` object.
              The `namespace` attribute of this object will be equal to the
              namespace parameter.
              Its `host` attribute of this object will be `None`.

          See :meth:`pywbem.WBEMConnection.Associators` for description of
          remaining parameters

        Returns:

            * For instance-level requests
              (ObjectName is :class:`~pywbem.CIMInstanceName`): A list of
              :class:`~pywbem.CIMInstance` objects that are representations
              of the associated instances.

              The `path` attribute of each :class:`~pywbem.CIMInstance`
              object is a :class:`~pywbem.CIMInstanceName` object with its
              attributes set as follows:

              * `classname`: Name of the creation class of the instance.
              * `keybindings`: Keybindings of the instance.
              * `namespace`: Name of the CIM namespace containing the instance.
              * `host`: Host and optionally port of the WBEM server containing
                the CIM namespace.

            * For class-level requests (ObjectName is :term:`string`):
              A list of :func:`py:tuple` of (classpath, class) objects that are
              representations of the associated classes.

              Each tuple represents one class and has these items:

              * classpath (:class:`~pywbem.CIMClassName`): The class
                path of the class, with its attributes set as follows:

                * `classname`: Name of the class.
                * `namespace`: Name of the CIM namespace containing the class.
                * `host`: Host and optionally port of the WBEM server containing
                  the CIM namespace.

              * class (:class:`~pywbem.CIMClass`): The representation of the
                class, with its `path` attribute set to the `classpath` tuple
                item.

        Raises:

            :exc:`~pywbem.CIMError`: (CIM_ERR_INVALID_NAMESPACE)
        """

        # Parameter types are already checked by WBEMConnection operation
        assert isinstance(namespace, six.string_types)
        assert isinstance(ObjectName, (six.string_types, CIMInstanceName))
        assert isinstance(AssocClass, (six.string_types, type(None)))
        assert isinstance(ResultClass, (six.string_types, type(None)))
        assert isinstance(Role, (six.string_types, type(None)))
        assert isinstance(ResultRole, (six.string_types, type(None)))
        assert isinstance(IncludeQualifiers, (bool, type(None)))
        assert isinstance(IncludeClassOrigin, (bool, type(None)))
        assert isinstance(PropertyList,
                          (six.string_types, list, tuple, type(None)))

        self.validate_namespace(namespace)

        if isinstance(ObjectName, CIMInstanceName):
            self._validate_instancename_namespace(namespace, ObjectName)
            assoc_names = self._get_associated_instancenames(namespace,
                                                             ObjectName,
                                                             AssocClass,
                                                             ResultClass,
                                                             ResultRole, Role)
            results = []
            instance_store = self.cimrepository.get_instance_store(namespace)
            for obj_name in assoc_names:
                results.append(self._get_instance(
                    obj_name, instance_store,
                    INSTANCE_RETRIEVE_LOCAL_ONLY,
                    IncludeClassOrigin, IncludeQualifiers, PropertyList))

            return results

        # Processing obj_name is class name
        rtn_classnames = self._get_associated_classnames(namespace,
                                                         ObjectName,
                                                         AssocClass,
                                                         ResultClass,
                                                         ResultRole, Role)
        # returns list of tuples of (CIMClassname, CIMClass)
        return self._return_assoc_class_tuples(rtn_classnames, namespace,
                                               IncludeQualifiers,
                                               IncludeClassOrigin,
                                               PropertyList)

    #####################################################################
    #
    #  Faked WBEMConnection Open and Pull Instances Methods
    #
    #  All of the following methods take the simplistic approach of getting
    #  all of the data from the original functions and saving it
    #  in the contexts dictionary.
    #
    #####################################################################

    @staticmethod
    def _create_contextid():
        """Return a new uuid for an enumeration context"""
        return str(uuid.uuid4())

    def _open_response(self, namespace, objects, pull_type, OperationTimeout,
                       MaxObjectCount, ContinueOnError):
        # pylint: disable=line-too-long
        """
        Build response to any Open... request once the objects have been
        extracted from the CIM repository.

        Parameters:

          namespace (:term:`string`):
            The name of the CIM namespace in the CIM repository (case
            insensitive). Must not be `None`. Leading or trailing slash
            characters are ignored.

          objects (list of:class:`CIMInstanceName` or list of :class:`CIMInstance` ):
            list of objects to be returned to the caller.

          FilterQueryLanguage (:term:`string`):
            The name of the filter query language used for the `FilterQuery`
            parameter. The DMTF-defined Filter Query Language (see
            :term:`DSP0212`) is specified as "DMTF:FQL".

          FilterQuery (:term:`string`):
            The filter query in the query language defined by the
            `FilterQueryLanguage` parameter.

          OperationTimeout (:class:`~pywbem.Uint32`):
            Minimum time in seconds the WBEM Server shall maintain an open
            enumeration session after a previous Open or Pull request is
            sent to the client. Once this timeout time has expired, the
            WBEM server may close the enumeration session.

            * If not `None`, this parameter is sent to the WBEM server as the
              proposed timeout for the enumeration session. A value of 0
              indicates that the server is expected to never time out. The
              server may reject the proposed value, causing a
              :exc:`~pywbem.CIMError` to be raised with status code
              :attr:`~pywbem.CIM_ERR_INVALID_OPERATION_TIMEOUT`.
            * If `None`, this parameter is not passed to the WBEM server, and
              causes the server-implemented default timeout to be used.

          ContinueOnError (:class:`py:bool`):
            Indicates to the WBEM server to continue sending responses
            after an error response has been sent.

            * If `True`, the server is to continue sending responses after
              sending an error response. Not all servers support continuation
              on error; a server that does not support it must send an error
              response if `True` was specified, causing
              :exc:`~pywbem.CIMError` to be raised with status code
              :attr:`~pywbem.CIM_ERR_CONTINUATION_ON_ERROR_NOT_SUPPORTED`.
            * If `False`, the server is requested to close the enumeration after
              sending an error response.
            * If `None`, this parameter is not passed to the WBEM server, and
              causes the server-implemented default behaviour to be used.
              :term:`DSP0200` defines that the server-implemented default is
              `False`.

          MaxObjectCount (:class:`~pywbem.Uint32`):
            Maximum number of instances the WBEM server may return
            for this request.

            * If positive, the WBEM server is to return no more than the
              specified number of instances.
            * If zero, the WBEM server is to return no instances. This may
              be used by a client to leave the handling of any returned
              instances to a loop of Pull operations.
            * If `None`, this parameter is not passed to the WBEM server, and
              causes the server-implemented default behaviour to be used.
              :term:`DSP0200` defines that the server-implemented default is
              to return zero instances.

        Returns:

            A :func:`~py:collections.namedtuple` object containing the following
            named items:

            * **instances** or **instance_patns**
              Representations of the retrieved instances.

            * **eos** (:class:`py:bool`):
              Indicates whether the enumeration session is exhausted after
              this operation:

              - If `True`, the enumeration session is exhausted, and the
                server has closed the enumeration session.
              - If `False`, the enumeration session is not exhausted and the
                `context` item is the context object for the next operation on
                the enumeration session.

            * **context** (:func:`py:tuple` of server_context, namespace):
              A context object identifying the open enumeration session,
              including its current enumeration state, and the namespace. This
              object must be supplied with the next pull or close operation for
              this enumeration session.

              The tuple items are:

              * server_context (:term:`string`):
                Enumeration context string returned by the server if
                the session is not exhausted, or `None` otherwise. This string
                is opaque for the client.
              * namespace (:term:`string`):
                Name of the CIM namespace that was used for this operation.

              NOTE: This inner tuple hides the need for a CIM namespace
              on subsequent operations in the enumeration session. CIM
              operations always require target namespace, but it never
              makes sense to specify a different one in subsequent
              operations on the same enumeration session.

        Raises:

            :exc:`~pywbem.CIMError`: (CIM_ERR_INVALID_NAMESPACE)
            :exc:`~pywbem.CIMError`: (CIM_ERR_INVALID_PARAMETER)
        """  # noqa: E501
        # pylint: enable=line-too-long

        max_obj_cnt = MaxObjectCount
        if max_obj_cnt is None:
            max_obj_cnt = DEFAULT_MAX_OBJECT_COUNT

        if ContinueOnError is None:
            ContinueOnError = False

        default_server_timeout = 40
        timeout = default_server_timeout if OperationTimeout is None \
            else OperationTimeout

        # If objects returne in open lt max_obj_cnt, set Enum context to
        # complete status.
        if len(objects) <= max_obj_cnt:
            eos = u'TRUE'
            context_id = ""
            rtn_objects = objects
        # Otherwise create an entry in the open context
        # table, return incomplete status.
        else:
            eos = u'FALSE'
            context_id = self._create_contextid()
            # Issue #2063  Use the timeout along with response delay.
            # Then user could timeout pulls. This means adding timer test to
            # pulls and close. Timer should be used to close old contexts.
            # Also The 'time' item contains elapsed time in fractional seconds
            # since an undefined point in time, so it is only useful for
            # calculating deltas.
            self.enumeration_contexts[context_id] = \
                {'pull_type': pull_type,
                 'data': objects,
                 'namespace': namespace,
                 'time': perf_counter(),  # pylint: disable=deprecated-method
                 'interoptimeout': timeout,
                 'continueonerror': ContinueOnError}
            rtn_objects = objects[0:max_obj_cnt]
            # remove objects from list that are being sent to client
            del objects[0: max_obj_cnt]

        return (rtn_objects, eos, context_id)

    def _openquery_response(self, namespace, objects, pull_type,
                            OperationTimeout, MaxObjectCount, ContinueOnError,
                            QueryResultClass):
        """
        Like _open_response(), just adds QueryResultClass to the returned
        tuple.
        """
        rtn_objects, eos, context_id = self._open_response(
            namespace, objects, pull_type, OperationTimeout, MaxObjectCount,
            ContinueOnError)
        return (rtn_objects, eos, context_id, QueryResultClass)

    def _pull_response(self, req_type, EnumerationContext, MaxObjectCount):
        """
        Common method for all of the Pull methods. Since all of the pull
        methods operate independent of the type of data, this single function
        severs as common code

        This method validates the EnumerationContext, gets data on the
        enumeration sequence from the enumeration_contexts table, validates the
        pull type, and returns the required number of objects.

        This method assumes the same context_id throughout the sequence.

        Returns:

            Tuple of CIM objects, EndOfSequence flag, EnumerationContext

        Raises:

            :exc:`~pywbem.CIMError`: (CIM_ERR_INVALID_ENUMERATION_CONTEXT)
        """

        try:
            context_data = self.enumeration_contexts[EnumerationContext]
        except KeyError:
            raise CIMError(
                CIM_ERR_INVALID_ENUMERATION_CONTEXT,
                _format("EnumerationContext {0!A} does not exist.",
                        EnumerationContext))

        # validate that namespace still exists for pull
        self.validate_namespace(context_data['namespace'])

        if context_data['pull_type'] != req_type:
            raise CIMError(
                CIM_ERR_INVALID_ENUMERATION_CONTEXT,
                _format("Invalid pull operations {0!A} does not match "
                        "expected {1!A} for EnumerationContext {2!A}",
                        context_data['pull_type'], req_type,
                        EnumerationContext))

        objs_list = context_data['data']

        max_obj_cnt = MaxObjectCount
        if not max_obj_cnt:
            max_obj_cnt = DEFAULT_MAX_OBJECT_COUNT

        if len(objs_list) <= max_obj_cnt:
            eos = u'TRUE'
            rtn_objs_list = objs_list
            del self.enumeration_contexts[EnumerationContext]
            context_id = ""
        else:
            eos = u'FALSE'
            rtn_objs_list = objs_list[0: max_obj_cnt]
            del objs_list[0: max_obj_cnt]
            context_id = EnumerationContext

        # returns tuple of list of insts, eos, and context_id
        return (rtn_objs_list, eos, context_id)

    @staticmethod
    def _validate_open_params(FilterQueryLanguage, FilterQuery,
                              OperationTimeout):
        """
        Validate the fql parameters and if invalid, generate exception
        """
        if not FilterQueryLanguage and FilterQuery:
            raise CIMError(
                CIM_ERR_INVALID_PARAMETER,
                "FilterQuery without FilterQueryLanguage definition is "
                "invalid")
        if FilterQueryLanguage:
            if FilterQueryLanguage != 'DMTF:FQL':
                raise CIMError(
                    CIM_ERR_QUERY_LANGUAGE_NOT_SUPPORTED,
                    _format("FilterQueryLanguage {0!A} not supported",
                            FilterQueryLanguage))
        ot = OperationTimeout
        if ot:
            if not isinstance(ot, six.integer_types) or ot < 0 \
                    or ot > OPEN_MAX_TIMEOUT:
                raise CIMError(
                    CIM_ERR_INVALID_PARAMETER,
                    _format("OperationTimeout {0!A }must be positive integer "
                            "less than {1!A}", ot, OPEN_MAX_TIMEOUT))

    def _validate_pull_operations_enabled(self):
        """
        Verify that pull operations are enabled.
        If they are not, raise exception.
        """
        if self.disable_pull_operations:
            raise CIMError(CIM_ERR_NOT_SUPPORTED,
                           "Pull Operations not supported. "
                           "disable_pull_operations=True")

    ####################################################################
    #
    #   Pull operation related provider methods
    #
    #   The following implement the server side of the WBEM pull
    #   operations including the Open...(), Pull...(), and Close()
    #
    #   They implement these operations by using the original equivalent
    #   operations (EnumerateInstances, etc.) and depend on those operations
    #   for parameter validation like namespace.
    #
    ####################################################################

    def OpenEnumerateInstancePaths(self, namespace, ClassName,
                                   FilterQueryLanguage=None, FilterQuery=None,
                                   OperationTimeout=None, ContinueOnError=None,
                                   MaxObjectCount=None):
        """
        Provider method for
        :meth:`pywbem.WBEMConnection.OpenEnumerateInstancePaths`.

        Parameters:

          namespace (:term:`string`):
            The name of the CIM namespace in the CIM repository (case
            insensitive). Must not be `None`. Leading or trailing slash
            characters are ignored.

          ClassName (:term:`string`):
            Name of the class to be enumerated (case independent).

          See _open_response() for description of additional parameters

        Returns:

            A :func:`~py:collections.namedtuple` object containing the following
            named items:

            * **paths** (:class:`py:list` of :class:`~pywbem.CIMInstanceName`):
              Representations of the retrieved instance paths, with their
              attributes set as follows:

              * `classname`: Name of the creation class of the instance.
              * `keybindings`: Keybindings of the instance.
              * `namespace`: Name of the CIM namespace containing the instance.
              * `host`: Host and optionally port of the WBEM server containing
                the CIM namespace.

            * **eos** (:class:`py:bool`):
              Indicates whether the enumeration session is exhausted after
              this operation:

              - If `True`, the enumeration session is exhausted, and the
                server has closed the enumeration session.
              - If `False`, the enumeration session is not exhausted and the
                `context` item is the context object for the next operation on
                the enumeration session.

            * **context** (:func:`py:tuple` of server_context, namespace):
              A context object identifying the open enumeration session,
              including its current enumeration state, and the namespace. This
              object must be supplied with the next pull or close operation for
              this enumeration session.

              The tuple items are:

              * server_context (:term:`string`):
                Enumeration context string returned by the server if
                the session is not exhausted, or `None` otherwise. This string
                is opaque for the client.
              * namespace (:term:`string`):
                Name of the CIM namespace that was used for this operation.

              NOTE: This inner tuple hides the need for a CIM namespace
              on subsequent operations in the enumeration session. CIM
              operations always require target namespace, but it never
              makes sense to specify a different one in subsequent
              operations on the same enumeration session.

        Raises:

            :exc:`~pywbem.CIMError`: (CIM_ERR_NOT_SUPPORTED)
            :exc:`~pywbem.CIMError`: (CIM_ERR_INVALID_NAMESPACE)
            :exc:`~pywbem.CIMError`: (CIM_ERR_INVALID_PARAMETER)
            :exc:`~pywbem.CIMError`: (CIM_ERR_INVALID_CLASS)
        """

        # Parameter types are already checked by WBEMConnection operation
        assert isinstance(namespace, six.string_types)
        assert isinstance(ClassName, six.string_types)
        assert isinstance(FilterQueryLanguage, (six.string_types, type(None)))
        assert isinstance(FilterQuery, (six.string_types, type(None)))
        assert isinstance(OperationTimeout, (six.integer_types, type(None)))
        assert isinstance(ContinueOnError, (bool, type(None)))
        assert isinstance(MaxObjectCount, (six.integer_types, type(None)))

        self._validate_pull_operations_enabled()
        self.validate_namespace(namespace)
        self._validate_open_params(FilterQueryLanguage, FilterQuery,
                                   OperationTimeout)

        result = self.EnumerateInstanceNames(namespace, ClassName)

        return self._open_response(namespace, result,
                                   'PullInstancePaths',
                                   OperationTimeout,
                                   MaxObjectCount,
                                   ContinueOnError)

    def OpenEnumerateInstances(self, namespace, ClassName,
                               DeepInheritance=None,
                               IncludeClassOrigin=None, PropertyList=None,
                               FilterQueryLanguage=None, FilterQuery=None,
                               OperationTimeout=None, ContinueOnError=None,
                               MaxObjectCount=None):
        """
        Provider method for
        :meth:`pywbem.WBEMConnection.OpenEnumerateInstances`.

        Parameters:

          namespace (:term:`string`):
            The name of the CIM namespace in the CIM repository (case
            insensitive). Must not be `None`. Leading or trailing slash
            characters are ignored.

          ClassName (:term:`string`):
            Name of the class to be enumerated (case independent).

          See _open_response() for description of additional parameters

        Returns:

            A :func:`~py:collections.namedtuple` object containing the following
            named items:

            * **instances** (:class:`py:list` of :class:`~pywbem.CIMInstance`):
              Representations of the retrieved instances.

              The `path` attribute of each :class:`~pywbem.CIMInstance`
              object is a :class:`~pywbem.CIMInstanceName` object with its
              attributes set as follows:

              * `classname`: Name of the creation class of the instance.
              * `keybindings`: Keybindings of the instance.
              * `namespace`: Name of the CIM namespace containing the instance.
              * `host`: Host and optionally port of the WBEM server containing
                the CIM namespace.

            * **eos** (:class:`py:bool`):
              Indicates whether the enumeration session is exhausted after
              this operation:

              - If `True`, the enumeration session is exhausted, and the
                server has closed the enumeration session.
              - If `False`, the enumeration session is not exhausted and the
                `context` item is the context object for the next operation on
                the enumeration session.

            * **context** (:func:`py:tuple` of server_context, namespace):
              A context object identifying the open enumeration session,
              including its current enumeration state, and the namespace. This
              object must be supplied with the next pull or close operation for
              this enumeration session.

              The tuple items are:

              * server_context (:term:`string`):
                Enumeration context string returned by the server if
                the session is not exhausted, or `None` otherwise. This string
                is opaque for the client.
              * namespace (:term:`string`):
                Name of the CIM namespace that was used for this operation.

              NOTE: This inner tuple hides the need for a CIM namespace
              on subsequent operations in the enumeration session. CIM
              operations always require target namespace, but it never
              makes sense to specify a different one in subsequent
              operations on the same enumeration session.

        Raises:

            :exc:`~pywbem.CIMError`: (CIM_ERR_NOT_SUPPORTED)
            :exc:`~pywbem.CIMError`: (CIM_ERR_INVALID_NAMESPACE)
            :exc:`~pywbem.CIMError`: (CIM_ERR_INVALID_PARAMETER)
            :exc:`~pywbem.CIMError`: (CIM_ERR_INVALID_CLASS)
        """

        # Parameter types are already checked by WBEMConnection operation
        assert isinstance(namespace, six.string_types)
        assert isinstance(ClassName, six.string_types)
        assert isinstance(DeepInheritance, (bool, type(None)))
        assert isinstance(IncludeClassOrigin, (bool, type(None)))
        assert isinstance(PropertyList,
                          (six.string_types, list, tuple, type(None)))
        assert isinstance(FilterQueryLanguage, (six.string_types, type(None)))
        assert isinstance(FilterQuery, (six.string_types, type(None)))
        assert isinstance(OperationTimeout, (six.integer_types, type(None)))
        assert isinstance(ContinueOnError, (bool, type(None)))
        assert isinstance(MaxObjectCount, (six.integer_types, type(None)))

        self._validate_pull_operations_enabled()
        self.validate_namespace(namespace)
        self._validate_open_params(FilterQueryLanguage, FilterQuery,
                                   OperationTimeout)

        result = self.EnumerateInstances(
            namespace, ClassName,
            DeepInheritance=DeepInheritance,
            IncludeQualifiers=None,              # not used with this request
            IncludeClassOrigin=IncludeClassOrigin,
            PropertyList=PropertyList)

        return self._open_response(namespace, result,
                                   'PullInstancesWithPath',
                                   OperationTimeout,
                                   MaxObjectCount,
                                   ContinueOnError)

    def OpenReferenceInstancePaths(self, namespace, InstanceName,
                                   ResultClass=None, Role=None,
                                   FilterQueryLanguage=None, FilterQuery=None,
                                   OperationTimeout=None, ContinueOnError=None,
                                   MaxObjectCount=None):
        # pylint: disable=invalid-name
        """
        Provider method for
        :meth:`pywbem.WBEMConnection.OpenReferenceInstancePaths`.

        Parameters:

          namespace (:term:`string`):
            The name of the CIM namespace in the CIM repository (case
            insensitive). Must not be `None`. Leading or trailing slash
            characters are ignored.

          InstanceName (:class:`~pywbem.CIMInstanceName`):
            The instance path of the source instance. If this object does
            specifies a namespace, it must equal the value of the namespace
            parameter. Its `host` attribute will be ignored.

          See :meth:`pywbem.WBEMConnection.ReferenceNames` for description of
          ResultClass, Role and _open_response for description of other
          parameters.

        Returns:

            See :meth:`~pywbem..WBEMConnection.ReferenceNames` for description
            of the returns

        Raises:

            :exc:`~pywbem.CIMError`: (CIM_ERR_NOT_SUPPORTED)
            :exc:`~pywbem.CIMError`: (CIM_ERR_INVALID_NAMESPACE)
            :exc:`~pywbem.CIMError`: (CIM_ERR_INVALID_PARAMETER)
        """

        # Parameter types are already checked by WBEMConnection operation
        assert isinstance(namespace, six.string_types)
        assert isinstance(InstanceName, CIMInstanceName)
        assert isinstance(ResultClass, (six.string_types, type(None)))
        assert isinstance(Role, (six.string_types, type(None)))
        assert isinstance(FilterQueryLanguage, (six.string_types, type(None)))
        assert isinstance(FilterQuery, (six.string_types, type(None)))
        assert isinstance(OperationTimeout, (six.integer_types, type(None)))
        assert isinstance(ContinueOnError, (bool, type(None)))
        assert isinstance(MaxObjectCount, (six.integer_types, type(None)))

        self._validate_pull_operations_enabled()
        self.validate_namespace(namespace)
        self._validate_open_params(FilterQueryLanguage, FilterQuery,
                                   OperationTimeout)

        instances = self.ReferenceNames(namespace, InstanceName,
                                        ResultClass=ResultClass,
                                        Role=Role)

        return self._open_response(namespace, instances,
                                   'PullInstancePaths',
                                   OperationTimeout,
                                   MaxObjectCount,
                                   ContinueOnError)

    def OpenReferenceInstances(self, namespace, InstanceName,
                               ResultClass=None, Role=None,
                               IncludeClassOrigin=None, PropertyList=None,
                               FilterQueryLanguage=None, FilterQuery=None,
                               OperationTimeout=None, ContinueOnError=None,
                               MaxObjectCount=None):
        """
        Provider method for
        :meth:`pywbem.WBEMConnection.OpenReferenceInstances`.

        Parameters:

          namespace (:term:`string`):
            The name of the CIM namespace in the CIM repository (case
            insensitive). Must not be `None`. Leading or trailing slash
            characters are ignored.

          InstanceName (:class:`~pywbem.CIMInstanceName`):
            The instance path of the source instance.
            If this object does specifies a namespace, it must equal the
            value of the namespace parameter.
            Its `host` attribute will be ignored.

        See :meth:`pywbem.WBEMConnection.References` for description of
        ResultClass, Role, , FilterQueryLanguage, FilterQuery,
        OperationTimeout, ContinueOnError, and MaxObjectCount parameters

        Returns:

            See :meth:`pywbem.WBEMConnection.References` for description
            of the returns.

        Raises:

            :exc:`~pywbem.CIMError`: (CIM_ERR_NOT_SUPPORTED)
            :exc:`~pywbem.CIMError`: (CIM_ERR_INVALID_NAMESPACE)
            :exc:`~pywbem.CIMError`: (CIM_ERR_INVALID_PARAMETER)
        """

        # Parameter types are already checked by WBEMConnection operation
        assert isinstance(namespace, six.string_types)
        assert isinstance(InstanceName, CIMInstanceName)
        assert isinstance(ResultClass, (six.string_types, type(None)))
        assert isinstance(Role, (six.string_types, type(None)))
        assert isinstance(IncludeClassOrigin, (bool, type(None)))
        assert isinstance(PropertyList,
                          (six.string_types, list, tuple, type(None)))
        assert isinstance(FilterQueryLanguage, (six.string_types, type(None)))
        assert isinstance(FilterQuery, (six.string_types, type(None)))
        assert isinstance(OperationTimeout, (six.integer_types, type(None)))
        assert isinstance(ContinueOnError, (bool, type(None)))
        assert isinstance(MaxObjectCount, (six.integer_types, type(None)))

        self._validate_pull_operations_enabled()
        self.validate_namespace(namespace)
        self._validate_open_params(FilterQueryLanguage, FilterQuery,
                                   OperationTimeout)

        instances = self.References(namespace, InstanceName,
                                    ResultClass=ResultClass,
                                    Role=Role,
                                    IncludeClassOrigin=IncludeClassOrigin,
                                    PropertyList=PropertyList)

        return self._open_response(namespace, instances,
                                   'PullInstancesWithPath',
                                   OperationTimeout,
                                   MaxObjectCount,
                                   ContinueOnError)

    def OpenAssociatorInstancePaths(self, namespace, InstanceName,
                                    AssocClass=None, ResultClass=None,
                                    Role=None, ResultRole=None,
                                    FilterQueryLanguage=None, FilterQuery=None,
                                    OperationTimeout=None, ContinueOnError=None,
                                    MaxObjectCount=None):
        # pylint: disable=invalid-name
        """
        Provider method for
        :meth:`pywbem.WBEMConnection.OpenAssociatorInstancePaths`.

        Parameters:

          namespace (:term:`string`):
            The name of the CIM namespace in the CIM repository (case
            insensitive). Must not be `None`. Leading or trailing slash
            characters are ignored.

          InstanceName (:class:`~pywbem.CIMInstanceName`):
            The instance path of the source instance.
            If this object does specifies a namespace, it must equal the
            value of the namespace parameter.
            Its `host` attribute will be ignored.

        See :meth:`~pywbem.AssociatorNames` for description of ResultClass,
        Role, AssocClass, ResultClass, , FilterQueryLanguage, FilterQuery,
        OperationTimeout, ContinueOnError, and MaxObjectCount parameters

        Returns:

            See :meth:`~pywbem..WBEMConnection.AssociatorNames` for description
            of the returns

        Raises:

            :exc:`~pywbem.CIMError`: (CIM_ERR_NOT_SUPPORTED)
            :exc:`~pywbem.CIMError`: (CIM_ERR_INVALID_NAMESPACE)
            :exc:`~pywbem.CIMError`: (CIM_ERR_INVALID_PARAMETER)
        """

        # Parameter types are already checked by WBEMConnection operation
        assert isinstance(namespace, six.string_types)
        assert isinstance(InstanceName, CIMInstanceName)
        assert isinstance(AssocClass, (six.string_types, type(None)))
        assert isinstance(ResultClass, (six.string_types, type(None)))
        assert isinstance(Role, (six.string_types, type(None)))
        assert isinstance(ResultRole, (six.string_types, type(None)))
        assert isinstance(FilterQueryLanguage, (six.string_types, type(None)))
        assert isinstance(FilterQuery, (six.string_types, type(None)))
        assert isinstance(OperationTimeout, (six.integer_types, type(None)))
        assert isinstance(ContinueOnError, (bool, type(None)))
        assert isinstance(MaxObjectCount, (six.integer_types, type(None)))

        self._validate_pull_operations_enabled()
        self.validate_namespace(namespace)
        self._validate_open_params(FilterQueryLanguage, FilterQuery,
                                   OperationTimeout)

        instances = self.AssociatorNames(namespace, InstanceName,
                                         AssocClass=AssocClass,
                                         ResultClass=ResultClass, Role=Role,
                                         ResultRole=ResultRole)

        return self._open_response(namespace, instances,
                                   'PullInstancePaths',
                                   OperationTimeout,
                                   MaxObjectCount,
                                   ContinueOnError)

    def OpenAssociatorInstances(self, namespace, InstanceName, AssocClass=None,
                                ResultClass=None, Role=None, ResultRole=None,
                                IncludeClassOrigin=None,
                                PropertyList=None, FilterQueryLanguage=None,
                                FilterQuery=None, OperationTimeout=None,
                                ContinueOnError=None, MaxObjectCount=None):
        """
        Provider method for
        :meth:`pywbem.WBEMConnection.OpenAssociatorInstances`
        with data from the instance store.

        Parameters:

          namespace (:term:`string`):
            The name of the CIM namespace in the CIM repository (case
            insensitive). Must not be `None`. Leading or trailing slash
            characters are ignored.

          InstanceName (:class:`~pywbem.CIMInstanceName`):
            The instance path of the source instance.
            If this object does specifies a namespace, it must equal the
            value of the namespace parameter.
            Its `host` attribute will be ignored.

        See :meth:`~pywbem.OpenAssociatorInstances` for description of
        ResultClass, Role, AssocClass, ResultClass, FilterQueryLanguage,
        FilterQuery, OperationTimeout,
        ContinueOnError, and MaxObjectCount parameters

        Returns:

            See :meth:`~pywbem..WBEMConnection.Associators` for description
            of the returns

        Raises:

            :exc:`~pywbem.CIMError`: (CIM_ERR_NOT_SUPPORTED)
            :exc:`~pywbem.CIMError`: (CIM_ERR_INVALID_NAMESPACE)
            :exc:`~pywbem.CIMError`: (CIM_ERR_INVALID_PARAMETER)
        """

        # Parameter types are already checked by WBEMConnection operation
        assert isinstance(namespace, six.string_types)
        assert isinstance(InstanceName, CIMInstanceName)
        assert isinstance(AssocClass, (six.string_types, type(None)))
        assert isinstance(ResultClass, (six.string_types, type(None)))
        assert isinstance(Role, (six.string_types, type(None)))
        assert isinstance(ResultRole, (six.string_types, type(None)))
        assert isinstance(IncludeClassOrigin, (bool, type(None)))
        assert isinstance(PropertyList,
                          (six.string_types, list, tuple, type(None)))
        assert isinstance(FilterQueryLanguage, (six.string_types, type(None)))
        assert isinstance(FilterQuery, (six.string_types, type(None)))
        assert isinstance(OperationTimeout, (six.integer_types, type(None)))
        assert isinstance(ContinueOnError, (bool, type(None)))
        assert isinstance(MaxObjectCount, (six.integer_types, type(None)))

        self._validate_pull_operations_enabled()
        self.validate_namespace(namespace)
        self._validate_open_params(FilterQueryLanguage, FilterQuery,
                                   OperationTimeout)

        instances = self.Associators(namespace, InstanceName,
                                     AssocClass=AssocClass,
                                     ResultClass=ResultClass, Role=Role,
                                     ResultRole=ResultRole,
                                     IncludeClassOrigin=IncludeClassOrigin,
                                     PropertyList=PropertyList)

        return self._open_response(namespace, instances,
                                   'PullInstancesWithPath',
                                   OperationTimeout,
                                   MaxObjectCount,
                                   ContinueOnError)

    def OpenQueryInstances(self, namespace, FilterQueryLanguage, FilterQuery,
                           ReturnQueryResultClass=None,
                           OperationTimeout=None, ContinueOnError=None,
                           MaxObjectCount=None):
        # pylint: disable=invalid-name,unused-argument
        """
        Provider method for
        :meth:`pywbem.WBEMConnection.OpenQueryInstances`.

        NOTE: Since ExecQuery is not implemented this method returns
        the not implemented exception.

        Parameters:

          namespace (:term:`string`):
            The name of the CIM namespace in the CIM repository (case
            insensitive). Must not be `None`. Leading or trailing slash
            characters are ignored.

        See :meth:`pywbem.WBEMConnection.OpenQueryInstances` for description
        of FilterQueryLanguage, FilterQuery, ReturnQueryResultClass,
        OperationTimeout, ContinueOnError, and MaxObjectCount
        parameters.

        Raises:

            :exc:`~pywbem.CIMError`: (CIM_ERR_NOT_SUPPORTED)
            :exc:`~pywbem.CIMError`: (CIM_ERR_INVALID_NAMESPACE)
            :exc:`~pywbem.CIMError`: (CIM_ERR_INVALID_PARAMETER)
        """

        # Parameter types are already checked by WBEMConnection operation
        assert isinstance(namespace, six.string_types)
        assert isinstance(FilterQueryLanguage, (six.string_types, type(None)))
        assert isinstance(FilterQuery, (six.string_types, type(None)))
        assert isinstance(ReturnQueryResultClass, (bool, type(None)))
        assert isinstance(OperationTimeout, (six.integer_types, type(None)))
        assert isinstance(ContinueOnError, (bool, type(None)))
        assert isinstance(MaxObjectCount, (six.integer_types, type(None)))

        self._validate_pull_operations_enabled()
        self.validate_namespace(namespace)
        self._validate_open_params(FilterQueryLanguage, FilterQuery,
                                   OperationTimeout)

        # Issue #2064 implement execquery
        # pylint: disable=assignment-from-no-return
        instances = self.ExecQuery(namespace, FilterQueryLanguage, FilterQuery)

        if ReturnQueryResultClass:
            m = re.search(r' FROM +([^ \(\)\[\]"\'\-\.\*\+]+)', FilterQuery)
            if not m:
                raise CIMError(
                    CIM_ERR_INVALID_QUERY,
                    _format("{} filter query does not contain 'FROM class' "
                            "clause: {}", FilterQueryLanguage, FilterQuery))
            classname = m.group(1)
            # May raise CIMError:
            QueryResultClass = self.get_class(
                namespace, classname, local_only=False,
                include_qualifiers=False, include_classorigin=False)
        else:
            QueryResultClass = None

        return self._openquery_response(
            namespace, instances, 'PullInstancesWithPath', OperationTimeout,
            MaxObjectCount, ContinueOnError, QueryResultClass)

    def PullInstancesWithPath(self, EnumerationContext, MaxObjectCount):
        """
        Provider method for
        :meth:`pywbem.WBEMConnection.PullInstancesWithPath`.

        Parameters:

          EnumerationContext (:term:`string`):
            Identifier for the enumeration context created by the
            corresponding Open... request.

          MaxObjectCount (:term:`integer`):
            Positive integer that defines the maximum number of instances
            that may be returned from this request.

        Returns:
            A :func:`~py:collections.namedtuple` object containing the following
            named items:

            * **instances** (:class:`py:list` of :class:`~pywbem.CIMInstance`):
              Representations of the retrieved instances.

              The `path` attribute of each :class:`~pywbem.CIMInstance`
              object is a :class:`~pywbem.CIMInstanceName` object with its
              attributes set as follows:

              * `classname`: Name of the creation class of the instance.
              * `keybindings`: Keybindings of the instance.
              * `namespace`: Name of the CIM namespace containing the instance.
              * `host`: Host and optionally port of the WBEM server containing
                the CIM namespace.

            * **eos** (:class:`py:bool`):
              Indicates whether the enumeration session is exhausted after
              this operation:

              - If `True`, the enumeration session is exhausted, and the
                server has closed the enumeration session.
              - If `False`, the enumeration session is not exhausted and the
                `context` item is the context object for the next operation on
                the enumeration session.

            * **context** (:func:`py:tuple` of server_context, namespace):
              A context object identifying the open enumeration session,
              including its current enumeration state, and the namespace. This
              object must be supplied with the next pull or close operation for
              this enumeration session.

              The tuple items are:

              * server_context (:term:`string`):
                Enumeration context string returned by the server if
                the session is not exhausted, or `None` otherwise. This string
                is opaque for the client.
              * namespace (:term:`string`):
                Name of the CIM namespace that was used for this operation.

              NOTE: This inner tuple hides the need for a CIM namespace
              on subsequent operations in the enumeration session. CIM
              operations always require target namespace, but it never
              makes sense to specify a different one in subsequent
              operations on the same enumeration session.

        Raises:

            :exc:`~pywbem.CIMError`: (CIM_ERR_NOT_SUPPORTED)
            :exc:`~pywbem.CIMError`: (CIM_ERR_INVALID_ENUMERATION_CONTEXT)
        """

        assert isinstance(EnumerationContext, six.string_types)
        assert isinstance(MaxObjectCount, (six.integer_types, type(None)))

        self._validate_pull_operations_enabled()
        return self._pull_response('PullInstancesWithPath',
                                   EnumerationContext, MaxObjectCount)

    def PullInstancePaths(self, EnumerationContext, MaxObjectCount):
        """
        Provider method for
        :meth:`pywbem.WBEMConnection.PullInstancePaths`.

        Parameters:

          EnumerationContext (:term:`string`):
            Identifier for the enumeration context created by the
            corresponding Open... request.

          MaxObjectCount (:term:`integer`):
            Positive integer that defines the maximum number of instances
            that may be returned from this request.

        Returns:

            A :func:`~py:collections.namedtuple` object containing the following
            named items:

            * **paths** (:class:`py:list` of :class:`~pywbem.CIMInstanceName`):
              Representations of the retrieved instance paths, with their
              attributes set as follows:

              * `classname`: Name of the creation class of the instance.
              * `keybindings`: Keybindings of the instance.
              * `namespace`: Name of the CIM namespace containing the instance.
              * `host`: Host and optionally port of the WBEM server containing
                the CIM namespace.

            * **eos** (:class:`py:bool`):
              Indicates whether the enumeration session is exhausted after
              this operation:

              - If `True`, the enumeration session is exhausted, and the
                server has closed the enumeration session.
              - If `False`, the enumeration session is not exhausted and the
                `context` item is the context object for the next operation on
                the enumeration session.

            * **context** (:func:`py:tuple` of server_context, namespace):
              A context object identifying the open enumeration session,
              including its current enumeration state, and the namespace. This
              object must be supplied with the next pull or close operation for
              this enumeration session.

              The tuple items are:

              * server_context (:term:`string`):
                Enumeration context string returned by the server if
                the session is not exhausted, or `None` otherwise. This string
                is opaque for the client.
              * namespace (:term:`string`):
                Name of the CIM namespace that was used for this operation.

              NOTE: This inner tuple hides the need for a CIM namespace
              on subsequent operations in the enumeration session. CIM
              operations always require target namespace, but it never
              makes sense to specify a different one in subsequent
              operations on the same enumeration session.

        Raises:

            :exc:`~pywbem.CIMError`: (CIM_ERR_NOT_SUPPORTED)
            :exc:`~pywbem.CIMError`: (CIM_ERR_INVALID_ENUMERATION_CONTEXT)
        """

        assert isinstance(EnumerationContext, six.string_types)
        assert isinstance(MaxObjectCount, (six.integer_types, type(None)))

        self._validate_pull_operations_enabled()
        return self._pull_response('PullInstancePaths',
                                   EnumerationContext, MaxObjectCount)

    def PullInstances(self, EnumerationContext, MaxObjectCount):
        """
        Provider method for
        :meth:`pywbem.WBEMConnection.PullInstances`.

        Parameters:

          EnumerationContext (:term:`string`):
            Identifier for the enumeration context created by the
            corresponding Open... request.

          MaxObjectCount (:term:`integer`):
            Positive integer that defines the maximum number of instances
            that may be returned from this request.

        Returns:

            A :func:`~py:collections.namedtuple` object containing the following
            named items:

            * **instances** (:class:`py:list` of :class:`~pywbem.CIMInstance`):
              Representations of the retrieved instances.

              The `path` attribute of each :class:`~pywbem.CIMInstance`
              object is `None`, because this operation does not return instance
              paths.

            * **eos** (:class:`py:bool`):
              Indicates whether the enumeration session is exhausted after
              this operation:

              - If `True`, the enumeration session is exhausted, and the
                server has closed the enumeration session.
              - If `False`, the enumeration session is not exhausted and the
                `context` item is the context object for the next operation on
                the enumeration session.

            * **context** (:func:`py:tuple` of server_context, namespace):
              A context object identifying the open enumeration session,
              including its current enumeration state, and the namespace. This
              object must be supplied with the next pull or close operation for
              this enumeration session.

              The tuple items are:

              * server_context (:term:`string`):
                Enumeration context string returned by the server if
                the session is not exhausted, or `None` otherwise. This string
                is opaque for the client.
              * namespace (:term:`string`):
                Name of the CIM namespace that was used for this operation.

              NOTE: This inner tuple hides the need for a CIM namespace
              on subsequent operations in the enumeration session. CIM
              operations always require target namespace, but it never
              makes sense to specify a different one in subsequent
              operations on the same enumeration session.

        Raises:

            :exc:`~pywbem.CIMError`: (CIM_ERR_NOT_SUPPORTED)
            :exc:`~pywbem.CIMError`: (CIM_ERR_INVALID_ENUMERATION_CONTEXT)
        """

        assert isinstance(EnumerationContext, six.string_types)
        assert isinstance(MaxObjectCount, (six.integer_types, type(None)))

        self._validate_pull_operations_enabled()
        return self._pull_response('PullInstances',
                                   EnumerationContext, MaxObjectCount)

    def CloseEnumeration(self, EnumerationContext):
        """
        Provider method for
        :meth:`pywbem.WBEMConnection.CloseEnumeration`.

        If the EnumerationContext is valid and open it removes it from the
        context CIM repository. Otherwise it returns an exception.

        Parameters:

          EnumerationContext(:term:`string`):
            Identifier for the enumeration context created by the
            corresponding Open... request.

        Raises:

            :exc:`~pywbem.CIMError`: (CIM_ERR_NOT_SUPPORTED)
            :exc:`~pywbem.CIMError`: (CIM_ERR_INVALID_ENUMERATION_CONTEXT)
        """

        assert isinstance(EnumerationContext, six.string_types)

        self._validate_pull_operations_enabled()

        if EnumerationContext in self.enumeration_contexts:
            del self.enumeration_contexts[EnumerationContext]
        else:
            raise CIMError(
                CIM_ERR_INVALID_ENUMERATION_CONTEXT,
                _format("EnumerationContext {0!A} not found in CIM server "
                        "enumeration contexts.", EnumerationContext))
