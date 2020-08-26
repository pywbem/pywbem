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
This file defines the ProviderRegistry class. The provider registry allows
user-defined providers to be created in the pywbem_mock environment and
registered with an instance of FakedWBEMConnection so that these user-defined
providers will be executed for their server requests in place of the default
server response behavior.  Providers are registered with the register_provider
method for particular namespaces, classnames servered by the provider and their
provider types (instance or method providers).

User defined providers can be registere for the following requests:

* CreateClass
* ModifyClass
* DeleteClass
* InvokeMethod
"""

import six
from pywbem._nocasedict import NocaseDict
from pywbem._utils import _format

from ._instancewriteprovider import InstanceWriteProvider
from ._methodprovider import MethodProvider
from ._utils import _uprint

__all__ = ['ProviderRegistry']


class ProviderRegistry(object):
    """
    This class defines the provider registry with methods to register
    a provider and to get the registered provider for a particular classname
    namespace, and provider_type.
    """
    #: Allowed provider types
    PROVIDER_TYPES = ["instance-write", "method"]

    def __init__(self):
        # Dictionary of registered providers.
        # Hierarchy of dictionaries is [namespace][classname][type]
        # value is provider object.
        self._registry = NocaseDict()

    def __repr__(self):
        return _format(
            "ProviderRegistry("
            "registry={s._registry}, ",
            s=self)

    def display_registered_providers(self, dest=None):
        """
        Generate display of registry in readable form and return the string
        Output format is:
        <namespace>:
          <classname>: CIM_Namespace provider: NamespaceProvider type: instance

        For example:

            Registered Providers:
            namespace: root/cimv2
              CIM_Foo      instance  UserInstanceTestProvider
              CIM_Foo      method    UserMethodTestProvider
            namespace: root/cimv3
              CIM_Foo      instance  UserInstanceTestProvider
              CIM_Foo      method    UserMethodTestProvider

        Parameters:

          dest (:term:`string`):
            File path of an output file. If `None`, the output is written to
            stdout.
        """
        def print_ljust(rows):
            """
            Print left justified and column aligned row of rows where each item
            is either a string or list of strings
            """

            widths = [max(map(len, col)) for col in zip(*rows)]
            for row in rows:
                _uprint(dest, u"  {0}".format(
                    u"  ".join((val.ljust(width) for
                                (val, width) in zip(row, widths)))))

        _uprint(dest, "Registered Providers:")
        for ns in self.provider_namespaces():
            rows = []
            _uprint(dest, _format(u'namespace: {0}', ns))
            for class_name in sorted(self.provider_classes(ns)):
                for type_ in sorted(self.provider_types(ns, class_name)):
                    provider = self.provider_obj(ns, class_name, type_)
                    provider_cn = provider.__class__.__name__
                    rows.append([class_name, type_, provider_cn])
            print_ljust(rows)

    def register_provider(self, conn, provider, namespaces=None,
                          schema_pragma_files=None, verbose=None):
        # pylint: disable=line-too-long
        """
        Register the provider object for specific namespaces and CIM classes.
        Registering a provider tells the FakedWBEMConnection that the provider
        implementation provided with this call as the `provider` parameter is
        to be executed as the request response method for the namespaces
        defined in the `namespaces` parameter, the provider type defined in the
        provider 'provider_type` attribute of the `provider` and the classes
        defined in the provider `provider_classnames` attribute of the
        `provider`.

        The provider registration process includes:

        1. Validation that the namespaces defined for the provider exist.
        2. Validation that the superclass of the provider is consistent with
           the `provider_type` attribute defined in the provider.
        3. Installation of any CIM classes defined by the provider
           (`provider_classnames` attribute) including installation of
           dependencies for these classes using the `schema_pragma_files` to
           locate the search directories for dependencies.
        4. Adding the provider to the registry of user_providers so that any
           of the request methods defined for the `provider_type` are
           passed to this provider in place of the default request processors.
        5. Execute post_register_setup() call to the provider to allow the
           provider to perform any special setup functionality.

        Providers can only be registered for the following request response
        methods:

        1. provider_type = 'instance-write': defines methods for CreateInstance,
           ModifyInstance, and DeleteInstance requests within a subclass of
           the `InstanceWriteProvider` class.

        2. provider_type = 'method': defines a InvokeMethod method within
           a subclass of the `MethodProvider` class.

        Each classname in a particular namespace may have at most one provider
        registered

        Parameters:

          conn  (:class:`~pywbem_mock.FakedWBEMConnection`):
            Defines the attributes of the connection. Used to issue requests to
            create instances in the Interop namespace for all existing
            namespaces that do not have instances of CIM_Namespace defined

          provider (instance of subclass of :class:`pywbem_mock.InstanceWriteProvider` or :class:`pywbem_mock.MethodProvider`):
            The methods in this subclass override the corresponding methods in
            the superclass. The method call parameters must be the same
            as the default method in the superclass and it must return
            data in the same format if the default method returns data.
             This
            class must contain variables `provider_type` and
            `provider_classnames` that define the type of provider and the CIM
            classes that the provider serves.

          namespaces (:term:`string` or :class:`py:list` of :term:`string`):
            Namespace or namespaces for which the provider is being registered.

            If `None`, the default namespace of the connection will be set to
            the built-in default namespace

          schema_pragma_files (:term:`py:iterable` of :term:`string` or :term:`string`):
            Path names of schema pragma files for the set of CIM
            classes that make up a schema such as the DMTF schema. These files
            must contain include pragams defining the file location of the
            classes to be compiled for the defined provider and for any
            dependencies required to compile those classes.  The directory
            containing each schema pragma file is passed to the MOF compiler as
            the search path for compile dependencies.

            see :class:`pywbem.MOFCompiler` for more information on the
            `search_paths` parameter.

          verbose (:class:`py:bool`):
            Display details on actions

        Raises:

            TypeError: Invalid provider_type retrieved from provider or
                       provider_type does not match superlclass. or the
                       namespace parameter is invalid.
            ValueError: provider_type retrieved from provider is not a
                        valid type string.
            ValueError: classnames parameter not a valid string or iterable or
                        namespace does not exist in repository.
        """  # noqa: E501
        # pylint: enable=line-too-long

        if schema_pragma_files:
            if isinstance(schema_pragma_files, six.string_types):
                schema_pragma_files = [schema_pragma_files]

        try:
            provider_type = provider.provider_type
            provider_classnames = provider.provider_classnames
        except AttributeError as ae:
            raise TypeError(
                _format("Attributes provider_type and provider_classnames "
                        "required in provider. exception {}",
                        ae))
        if provider_type == 'instance-write':
            if not isinstance(provider, InstanceWriteProvider):
                raise TypeError(
                    _format("Provider argument {0!A} is not a "
                            "valid subclass of InstanceWriteProvider. ",
                            provider))
        elif provider_type == 'method':
            if not isinstance(provider, MethodProvider):
                raise TypeError(
                    _format("Provider argument {0!A} is not a "
                            "valid subclass of MethodProvider. ",
                            provider))
        else:
            raise ValueError(
                _format("Provider_type argument {0!A} is not a valid provider "
                        "type. Valid provider types are {1!A}.",
                        provider_type, self.PROVIDER_TYPES))

        if provider_classnames is None:
            raise ValueError(
                _format('Classnames argument must be string '
                        'or list of strings. None not allowed.'))

        if namespaces is None:
            namespaces = [conn.default_namespace]

        if isinstance(namespaces, six.string_types):
            namespaces = [namespaces]

        if not isinstance(namespaces, (list, tuple)):
            raise TypeError(
                _format('Namespace argument {0|A} must be a string or '
                        'list/tuple but is {1}',
                        namespaces, type(namespaces)))

        for namespace in namespaces:
            if not isinstance(namespace, six.string_types):
                raise TypeError(
                    _format('Namespace "{0!A}" in namespaces argument not '
                            'a string. ', namespace))

            if namespace not in conn.namespaces:
                raise ValueError(
                    _format('Namespace "{0!A}" in namespaces argument not '
                            'in CIM repository. '
                            'Existing namespaces are: {1!A}. ',
                            namespace, conn.namespaces))

        if isinstance(provider_classnames, six.string_types):
            provider_classnames = [provider_classnames]
        assert isinstance(provider_classnames, (list, tuple))

        for classname in provider_classnames:
            assert isinstance(classname, six.string_types)

        # For each namespace in which the provider is to be registered,
        # if the class is not in that namespace, either compile it in if
        # pragmas exist or generate an exception if no pragmas exist

        for namespace in namespaces:
            for classname in provider_classnames:
                # pylint: disable=protected-access
                if not conn._mainprovider.class_exists(namespace, classname):
                    if schema_pragma_files:
                        conn.compile_schema_classes(
                            provider_classnames,
                            schema_pragma_files,
                            namespace=namespace,
                            verbose=verbose)
                    else:
                        raise ValueError(
                            _format('Class "{0!A}" does not exist in '
                                    'namespace {1!A} of the CIM repository '
                                    'and no schema pragma files were specified',
                                    classname, namespace))
            if namespace not in self._registry:
                self._registry[namespace] = NocaseDict()

            # Add classnames for the namespace
            for classname in provider_classnames:
                if classname not in self._registry[namespace]:
                    self._registry[namespace][classname] = {}
                self._registry[namespace][classname][provider_type] = provider

        if verbose:
            _format("Provider {0!A} registered: classes:[{1!A}],  "
                    "type: {1!A} namespaces:{2!A}",
                    provider.__class__.__name__,
                    ", ".join(provider_classnames),
                    provider_type, ", ".join(namespaces))

        # Call post_register_setup.  Since this method is defined in the
        # default provider methods (MethodProvider, etc.) any exception is
        # caught as an error.
        provider.post_register_setup(conn)

    def get_registered_provider(self, namespace, provider_type, classname):
        """
        Get the  user-defined provider registered for this namespace,
        provider_type, and classname.

        If no provider is registered, return `None`.

        Parameters:

          namespace (:term:`string`):
            The namespace in which the request will be executed.

          provider_type (:term:`string`):
            String containing keyword ('instance-write' or 'method') defining
            the type of provider.

          classname (:term:`string`):
            Name of the class defined for the operation

        Returns:

          Instance of :class:`~pywbem_mock.BaseProvider`: The registered
          provider.

          None if the registry is empty, the classname is not in the registry
          or the namespace is not in the registry or the entry for the
          classname, namespace and provider type is not defined.
        """

        if not self._registry or namespace not in self._registry:
            return None

        if classname not in self._registry[namespace]:
            return None

        # Return None if requested type is not registered type
        if provider_type not in self.provider_types(namespace, classname):
            return None

        return self.provider_obj(namespace, classname, provider_type)

    def provider_namespaces(self):
        """
        Get list of namespaces for registered providers. The returned
        list is case sensitive.

        Returns:
            :class:`py:list` of :term:`string`: namespaces
            for which providers are registered.
        """
        return list(self._registry.keys())

    def provider_classes(self, namespace):
        """
        Get case insensitive iterable  of the classes for providers registered
        for a namespace. The returned list is case sensitive.

        Parameters:

          namespace (:term:`string`):
            The namespace in which the request will be executed.

        Returns:
            :class:`py:list` of :term:`string`:
            Names of classes registered for namespace

        Raises:
          KeyError: if namespace invalid
        """

        return list(self._registry[namespace].keys())

    def provider_types(self, namespace, classname):
        """
        Get provider types for a namespace and classname.  This is
        a case-sensitive list.

        Parameters:

          namespace (:term:`string`):
            The namespace in which the request will be executed.

          classname (:term:`string`):
            Name of the class defined for the operation.

        Returns:
            :class:`py:list` of :term:`string`: Strings defining provider
            types for the defined namespace and classname

        Raises:
          KeyError: if namespace invalid
        """
        return list(self._registry[namespace][classname].keys())

    def provider_obj(self, namespace, classname, provider_type):
        """
        Get the registered provider object (instance of the registered
        provider) for namespace, provider classname, and provider_type.

        Parameters:

          namespace (:term:`string`):
            The namespace in which the request will be executed.

          classname (:term:`string`):
            Name of the class defined for the operation.

          provider_type (:term:`string`):
            String containing keyword ('instance-write' or 'method') defining
            the type of provider.

        Returns:
            The registered object

        Raises:
          KeyError: if namespace or classname invalid
        """
        return self._registry[namespace][classname][provider_type]

    def iteritems(self):
        """
        Return an iterator through the registered provider items. Each item
        is a tuple(namespace, classname, provider_type, provider_obj),
        with:

          namespace (:term:`string`):
            The namespace in which the request will be executed.

          classname (:term:`string`):
            Name of the class defined for the operation.

          provider_type (:term:`string`):
            String containing keyword ('instance-write' or 'method') defining
            the type of provider.

          provider_obj (:class:`~pywbem_mock.BaseProvider`):
            The registered provider.
        """
        ns_dict = self._registry
        for ns in ns_dict:
            cln_dict = ns_dict[ns]
            for cln in cln_dict:
                pt_dict = cln_dict[cln]
                for pt in pt_dict:
                    pobj = pt_dict[pt]
                    yield (ns, cln, pt, pobj)

    def load(self, other):
        """
        Replace the data in this object with the data from the other object.

        This is used to restore the object from a serialized state, without
        changing its identity.
        """
        # pylint: disable=protected-access
        self._registry = other._registry
