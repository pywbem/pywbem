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
Mock support for the WBEMConnection class to allow pywbem users to test the
pywbem client without requiring a running WBEM server.

For documentation, see mocksupport.rst.
"""

from __future__ import absolute_import, print_function

import os
import time
import re
from xml.dom import minidom
# try:
#    from unittest.mock import Mock
# except ImportError:
#    from mock import Mock
import six

from pywbem import WBEMConnection, CIMClass, CIMClassName, \
    CIMInstance, CIMInstanceName, CIMParameter, CIMQualifierDeclaration, \
    cimtype, CIMError, CIM_ERR_FAILED, DEFAULT_NAMESPACE, MOFCompiler, \
    DEFAULT_TIMEOUT, WBEMServer, ModelError
from pywbem._nocasedict import NocaseDict
from pywbem._utils import _format
from ._mainprovider import MainProvider

from ._inmemoryrepository import InMemoryRepository

from ._mockmofwbemconnection import _MockMOFWBEMConnection

from ._providerregistry import ProviderRegistry
from ._providerdependentregistry import ProviderDependentRegistry

from ._providerdispatcher import ProviderDispatcher

from ._dmtf_cim_schema import build_schema_mof
from ._utils import _uprint

from ._namespaceprovider import CIMNamespaceProvider

from ._subscriptionproviders import CIMIndicationSubscriptionProvider, \
    CIMListenerDestinationProvider, CIMIndicationFilterProvider

__all__ = ['FakedWBEMConnection']

# Fake Server default values for parameters that apply to repo and operations

# allowed output formats for the repository display
OUTPUT_FORMATS = ['mof', 'xml', 'repr']

# Issue #2065. We have not considered that iq and ico are deprecated in
# on DSP0200 for get_instance, etc. We could  set up a default to ignore these
# parameters for the operations in which they are deprecated and we
# should/could ignore them. We need to document our behavior in relation to the
# spec.


def _pretty_xml(xml_string):
    """
    Common function to produce pretty xml string from an input xml_string.

    This function is NOT intended to be used in major code paths since it
    uses the minidom to produce the prettified xml and that uses a lot
    of memory
    """

    result_dom = minidom.parseString(xml_string)
    pretty_result = result_dom.toprettyxml(indent='  ')

    # remove extra empty lines
    return re.sub(r'>( *[\r\n]+)+( *)<', r'>\n\2<', pretty_result)


def _cvt_rqd_classname(classname):
    """Convert required classname to string"""
    if isinstance(classname, CIMClassName):
        classname = classname.classname
    return classname


def _cvt_opt_classname(classname):
    """Convert optional classname to string if it exists"""
    if classname is None:
        return classname
    if isinstance(classname, CIMClassName):
        return classname.classname
    return classname


def _cvt_obj_name(objname):
    """Convert objectname to string if classname or return if inst name"""
    if isinstance(objname, CIMInstanceName):
        return objname
    if isinstance(objname, CIMClassName):
        return objname.classname
    return objname


class FakedWBEMConnection(WBEMConnection):
    """
    A subclass of :class:`pywbem.WBEMConnection` that mocks the communication
    with a WBEM server by utilizing a local in-memory CIM repository to
    generate responses in the same way the WBEM server would.

    *New in pywbem 0.12 as experimental and finalized in 1.2.*

    Each :class:`~pywbem_mock.FakedWBEMConnection` object has its own
    CIM repository which contains multiple CIM namespaces, and each namespace
    may contain CIM qualifier types (declarations), CIM classes and
    CIM instances.

    This class provides only a subset of the init parameters of
    :class:`~pywbem.WBEMConnection` because it does not have a connection to a
    WBEM server. It uses a faked and fixed URL for the WBEM server
    (``http://FakedUrl``) as a means of identifying the connection by users.

    Logging of the faked operations is supported via the pywbem logging
    facility and can be controlled in the same way as for
    :class:`~pywbem.WBEMConnection`. For details, see
    :ref:`WBEM operation logging`.

    Some of the longer running methods of this class add time statistics to the
    :attr:`pywbem.WBEMConnection.statistics`. For details on how to get the
    statistics, see :ref:`WBEM operation statistics`.
    """
    def __init__(self, default_namespace=DEFAULT_NAMESPACE,
                 use_pull_operations=False, stats_enabled=False,
                 timeout=DEFAULT_TIMEOUT, response_delay=None,
                 disable_pull_operations=None, url=None):
        """
        Parameters:

          default_namespace (:term:`string`):
            Default namespace.
            This parameter has the same characteristics as the same-named init
            parameter of :class:`~pywbem.WBEMConnection`.

          use_pull_operations (:class:`py:bool`):
            Flag to control whether pull or traditional operations are
            used in the iter... operations.
            This parameter has the same characteristics as the same-named init
            parameter of :class:`~pywbem.WBEMConnection`.

          timeout (:term:`number`):
            This parameter has the same characteristics as the same-named init
            parameter of :class:`~pywbem.WBEMConnection`.

          stats_enabled (:class:`py:bool`):
            Flag to enable operation statistics.
            This parameter has the same characteristics as the same-named init
            parameter of :class:`~pywbem.WBEMConnection`.

          response_delay (:term:`number`):
            Artifically created delay for each operation, in seconds. This must
            be a positive number. Delays less than a second or other fractional
            delays may be achieved with float numbers.
            `None` disables the delay.

            Note that the
            :attr:`~pywbem_mock.FakedWBEMConnection.response_delay` property
            can be used to set this delay subsequent to object creation.

          disable_pull_operations (:class:`py:bool`):
            Flag to allow user to disable the pull operations ( Open... and
            Pull.. requests). The default is None which enables pull operations
            to execute. Setting the flag to True causes pull operations
            to raise CIMError(CIM_ERR_NOT_SUPPORTED).

            The :attr:`~pywbem_mock.FakedWBEMConnection.disable_pull_operations`
            property can be used to set this variable.

        url (:term:`string`):
            Defines a url to replace the default http://FakedURL.5988 url which
            is passed to the superclass. The url must be an acceptable syntax
            for WBEMConnection initialization.  This is useful when multiple
            mocks are required for testing.

        Raises:
          ValueError: Invalid arguments
        """

        # Response delay in seconds. Any operation is delayed by this time.
        # Initialize before superclass init because otherwise logger may
        # fail with this attribute not found
        self._response_delay = response_delay

        # define attribute here to assure it is defined before CIM repository
        # created. Reset again after repository created.
        self._disable_pull_operations = disable_pull_operations

        super(FakedWBEMConnection, self).__init__(
            url or 'http://FakedUrl:5988',
            default_namespace=default_namespace,
            use_pull_operations=use_pull_operations,
            stats_enabled=stats_enabled, timeout=timeout)

        # See the cimrepository property for more information
        self._cimrepository = None

        # Provider registry defines user added providers.  This is a dictionary
        # with key equal classname that contains entries for namespaces,
        # provider type, and provider for each class name defined
        self._provider_registry = ProviderRegistry()

        # Registry for provider dependent files.
        self._provider_dependent_registry = ProviderDependentRegistry()

        # Define the datastore to be used with an initial namespace, the client
        # connection default namespace. This is passed to the providerdispatcher
        # and mainprovider and not used further in this class.
        # Initiate instance of the ProviderDispatcher with required
        # parameters including the CIM repository. This call initializes
        # self.cimrepository.
        self._providerdispatcher = ProviderDispatcher(
            self.cimrepository, self._provider_registry)

        # Initiate the MainProvider with parameters required to execute
        self._mainprovider = MainProvider(self.host,
                                          self.disable_pull_operations,
                                          self.cimrepository,
                                          self._providerdispatcher)

        # Flag to allow or disallow the use of the Open... and Pull...
        # operations. Uses the setter method
        self.disable_pull_operations = disable_pull_operations

        # Defines the connection for the compiler. The compiler uses this
        # instance of this class as the client interface.
        self._mofwbemconnection = _MockMOFWBEMConnection(self)

        self._imethodcall = self._mock_imethodcall
        self._methodcall = self._mock_methodcall

    @property
    def namespaces(self):
        """
        :term:`NocaseList` of :term:`string`:
        The names of the namespaces that exist in the CIM repository.
        """
        return self._mainprovider.namespaces

    @property
    def interop_namespace_names(self):
        """
        :term:`NocaseList` of :term:`string`:
        The valid Interop namespace names.

        Only these names may be the Interop namespace and only one
        Interop namespace may exist in a WBEM server environment.
        This list is defined in :attr:`pywbem.WBEMServer.INTEROP_NAMESPACES`.
        """
        return self._mainprovider.interop_namespace_names

    @property
    def cimrepository(self):
        """
        :class:`~pywbem_mock.InMemoryRepository`: The mocked in-memory CIM
        repository.

        The CIM repository is the data store for CIM classes, CIM instances,
        and CIM qualifier declarations, all partitioned by CIM namespaces.
        """
        if self._cimrepository is None:
            self._cimrepository = InMemoryRepository(self.default_namespace)
        return self._cimrepository

    @property
    def provider_dependent_registry(self):
        """
        :class:`~pywbem_mock.ProviderDependentRegistry`: The registry for
        provider dependent files, in context of a mock script.
        """
        return self._provider_dependent_registry

    @property
    def response_delay(self):
        """
        :term:`number`:
          Artifically created delay for each operation, in seconds.
          If `None`, there is no delay.

          This attribute is settable. For details, see the description of the
          same-named init parameter of
          :class:`this class <pywbem_mock.FakedWBEMConnection>`.
        """
        return self._response_delay

    @response_delay.setter
    def response_delay(self, delay):
        """Setter method; for a description see the getter method."""
        if isinstance(delay, (int, float)) and delay >= 0 or delay is None:
            self._response_delay = delay
        else:
            raise ValueError(
                _format("Invalid value for response_delay: {0!A}, must be a "
                        "positive number", delay))

    @property
    def disable_pull_operations(self):
        """
        :class:`py:bool`:
          Boolean flag to set option to disable the execution of the open and
          pull operation request handlers in the CIM repository. This
          emulates the characteristic in some CIM servers that did not
          implement pull operations. The default is to allow pull operations.
          All pull operations requests may be forbidden from executing by
          setting disable_pull_operations to True.

          This attribute is settable. For details, see the description of the
          same-named init parameter of
          :class:`this class <pywbem_mock.FakedWBEMConnection>`.
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
            # modify the parameter in the mainprovider
            self._mainprovider.disable_pull_operations = disable
        else:
            raise ValueError(
                _format('Invalid type for disable_pull_operations: {0!A}, '
                        'must be a boolean', disable))

    def __str__(self):
        return _format(
            "FakedWBEMConnection("
            "response_delay={s.response_delay}, "
            "super={super})",
            s=self, super=super(FakedWBEMConnection, self).__str__())

    def __repr__(self):
        return _format(
            "FakedWBEMConnection("
            "response_delay={s.response_delay}, "
            "disable_pull_operations={s.disable_pull_operations} "
            "super={super})",
            s=self, super=super(FakedWBEMConnection, self).__repr__())

    def copy(self):
        """
        *New in pywbem 1.3.*

        Return a deep copy of the object with internal state reset and reusing
        the same repository and registries.

        The returned object uses the same repository, provider registry and
        provider dependent registry objects as the original object.
        Besides that, all other user-specifiable attributes of the object are
        deep-copied, and all other internal state is reset.
        """
        cpy = FakedWBEMConnection(
            default_namespace=self.default_namespace,
            use_pull_operations=self.use_pull_operations,
            stats_enabled=self.stats_enabled,
            timeout=self.timeout,
            response_delay=self._response_delay,
            disable_pull_operations=self._disable_pull_operations,
            url=self.url,
        )  # only immutable parameters

        # pylint: disable=protected-access

        # Reuse repository and registries of the original object
        cpy._cimrepository = self._cimrepository
        cpy._provider_registry = self._provider_registry
        cpy._provider_dependent_registry = self._provider_dependent_registry

        # These objects know about the repository and registries, but other
        # wise do not have internal state
        cpy._providerdispatcher = self._providerdispatcher
        cpy._mainprovider = self._mainprovider

        # pylint: enable=protected-access

        return cpy

    # The namespace management methods must be in the this class directly
    # so they can be access with call to the methods from instance of
    # this class. they are considered part of the external API.

    def add_namespace(self, namespace, verbose=False):
        """
        Add a CIM namespace to the CIM repository of the faked connection.

        The namespace must not yet exist in the CIM repository.

        If a namespace provider has already been created, this method must
        use that provider to create the namespace rather than try to create
        the namespace directly in the repository

        Parameters:

          namespace (:term:`string`):
            The name of the CIM namespace to be added to the CIM repository.
            Must not be `None`. Any leading or trailing slash characters are
            removed before the string is used to define the namespace name.

          verbose (:class:`py:bool`):
            Verbose mode: Print a message about the namespace creation.

        Raises:

          ValueError: Namespace argument must not be None.
          :exc:`~pywbem.CIMError`: CIM_ERR_ALREADY_EXISTS if the namespace
            already exists in the CIM repository.
        """
        if self.find_interop_namespace():
            try:
                server = WBEMServer(self)
                server.create_namespace(namespace)
                if verbose:
                    print("Created namespace {} (in mock support)".
                          format(namespace))
                return
            except (ModelError, CIMError):
                pass

        # No interop namespace or fail to create above.  Use add_namespace
        self._mainprovider.add_namespace(namespace, verbose=verbose)

    def remove_namespace(self, namespace, verbose=False):
        """
        Remove a CIM namespace from the CIM repository of the faked connection.

        The namespace must exist in the CIM repository and must be empty.

        Parameters:

          namespace (:term:`string`):
            The name of the CIM namespace in the CIM repository (case
            insensitive). Must not be `None`. Leading or trailing
            slash characters are ignored.

          verbose (:class:`py:bool`):
            Verbose mode: Print a message about the namespace deletion.

        Raises:

          ValueError: Namespace argument must not be None
          :exc:`~pywbem.CIMError`: (CIM_ERR_NOT_FOUND) if the namespace does
            not exist in the CIM repository.
          :exc:`~pywbem.CIMError`: (CIM_ERR_NAMESPACE_NOT_EMPTY) if the
            namespace is not empty.
          :exc:`~pywbem.CIMError`: (CIM_ERR_NAMESPACE_NOT_EMPTY) if attempting
            to delete the default connection namespace.  This namespace cannot
            be deleted from the CIM repository
        """
        self._mainprovider.remove_namespace(namespace, verbose=verbose)

    def is_interop_namespace(self, namespace):
        """
        Tests if a namespace name is a valid Interop namespace name.

        This method does not access the CIM repository for this test; it
        merely compares the specified namespace name against the list of valid
        Interop namespace names returned by :meth:`interop_namespace_names`.

        Parameters:

          namespace (:term:`string`):
            The namespace name that is to be tested.

        Returns:

          :class:`py:bool`: Indicates whether the namespace name is a valid
          Interop namespace name.
        """
        return self._mainprovider.is_interop_namespace(namespace)

    def find_interop_namespace(self):
        """
        Find the Interop namespace in the CIM repository, or return `None`.

        The Interop namespace is identified by comparing all namespace names
        in the CIM repository against the list of valid Interop namespace names
        returned by :meth:`interop_namespace_names`.

        Returns:

          :term:`string`: The name of the Interop namespace if one exists in
          the CIM repository or otherwise `None`.
        """
        return self._mainprovider.find_interop_namespace()

    def install_namespace_provider(self, interop_namespace,
                                   schema_pragma_file=None,
                                   verbose=None):
        """
        FakedWBEMConnection user method to install the namespace provider in
        the Interop namespace where the proposed interop_namespace is defined
        by the parameter interop_namespace

        Because this provider requires a set of classes from the
        DMTF schema, the schema_pragma_file install the schema is required.

        This method should only be called once at the creation of the
        mock environment.

        Parameters:

          interop_namespace  (:term:`string`):
            The Interop namespace defined for this environment

          schema_pragma_file (:term:`string`):
            File path defining a CIM schema pragma file for the set of
            CIM classes that make up a schema such as the DMTF schema.
            This file must contain a pragma statement for each of the
            classes defined in the schema.

            If None, no attempt is made to any CIM classes required for the
            provider and it is assumed that the CIM classes are already
            installed

          verbose (:class:`py:bool`):
            If True, displays progress information as providers are installed.

        Raises:

          :exc:`~pywbem.CIMError`: with status code appropriate for any
            error encountered in the installation of the provider.
        """

        # Determine if an interop namespace already exists and confirm that
        # we are using a valid interop namespace name to add the
        # new namespace.
        if not self.find_interop_namespace():
            self.add_namespace(interop_namespace)

        provider = CIMNamespaceProvider(self.cimrepository)

        self.register_provider(provider,
                               namespaces=interop_namespace,
                               schema_pragma_files=schema_pragma_file,
                               verbose=verbose)

    def install_subscription_providers(self, interop_namespace,
                                       schema_pragma_file=None,
                                       verbose=None):
        """
        FakedWBEMConnection user method to install the indication subscription
        providers in the Interop namespace where the proposed interop_namespace
        is defined by the parameter interop_namespace

        **Experimental:** *New in pywbem 1.3.0 as experimental.*

        Because these provider requires a set of classes from the
        DMTF schema, the schema_pragma_file install the schema is required.

        This method should only be called once at the creation of the
        mock environment.

        Parameters:

          interop_namespace  (:term:`string`):
            The Interop namespace defined for this environment

          schema_pragma_file (:term:`string`):
            File path defining a CIM schema pragma file for the set of
            CIM classes that make up a schema such as the DMTF schema.
            This file must contain a pragma statement for each of the
            classes defined in the schema.

            If None, no attempt is made to any CIM classes required for the
            provider and it is assumed that the CIM classes are already
            installed

          verbose (:class:`py:bool`):
            If True, displays progress information as providers are installed.

        Raises:

          :exc:`~pywbem.CIMError`: with status code appropriate for any
            error encountered in the installation of the provider.
        """

        # Determine if an interop namespace already exists and confirm that
        # we are using a valid interop namespace name to add the
        # new namespace.
        if not self.find_interop_namespace():
            self.add_namespace(interop_namespace)

        provider = CIMListenerDestinationProvider(self.cimrepository)
        self.register_provider(provider,
                               namespaces=interop_namespace,
                               schema_pragma_files=schema_pragma_file,
                               verbose=verbose)

        provider = CIMIndicationFilterProvider(self.cimrepository)
        self.register_provider(provider,
                               namespaces=interop_namespace,
                               schema_pragma_files=schema_pragma_file,
                               verbose=verbose)

        provider = CIMIndicationSubscriptionProvider(self.cimrepository)
        self.register_provider(provider,
                               namespaces=interop_namespace,
                               schema_pragma_files=schema_pragma_file,
                               verbose=verbose)

    ###########################################################################
    #
    #  Methods to compile mof files into repository
    #
    ###########################################################################

    def compile_mof_file(self, mof_file, namespace=None, search_paths=None,
                         verbose=None):
        """
        Compile the MOF definitions in the specified file (and its included
        files) and add the resulting CIM objects to the specified CIM namespace
        of the CIM repository.

        If the namespace does not exist, :exc:`~pywbem.CIMError` with status
        CIM_ERR_INVALID_NAMESPACE is raised.

        This method supports all MOF pragmas, and specifically the include
        pragma.

        If a CIM class or CIM qualifier type to be added already exists in the
        target namespace with the same name (comparing case insensitively),
        this method raises :exc:`~pywbem.CIMError`.

        If a CIM instance to be added already exists in the target namespace
        with the same keybinding values, this method raises
        :exc:`~pywbem.CIMError`.

        In all cases where this method raises an exception, the CIM repository
        remains unchanged.

        Parameters:

          mof_file (:term:`string`):
            Path name of the file containing the MOF definitions to be compiled.

          namespace (:term:`string`):
            The name of the CIM namespace in the associated CIM repository that
            is the target of the compilation, and is also used for lookup of any
            dependent CIM elements. If `None`, the default namespace of the
            connection is used. A namespace defined in a namespace pragma of
            the MOF superceeds this namespace from the point in the
            compilation unit(string/file) where it is declared.  The namespace
            specified in this parameter or the MOF inamespace pragma must
            exist.

          search_paths (:term:`py:iterable` of :term:`string`):
            An iterable of directory path names where MOF dependent files will
            be looked up.
            See the description of the `search_path` init parameter of the
            :class:`~pywbem.MOFCompiler` class for more information on MOF
            dependent files.

          verbose (:class:`py:bool`):
            Controls whether to issue more detailed compiler messages.

        Raises:

          IOError: MOF file not found.
          :exc:`~pywbem.MOFCompileError`: Compile error in the MOF.
        """

        # By default, error messages are always printed in addition to being
        # raised as MOFCompileError. We only want them to be printed in verbose
        # mode:
        log_func_kwargs = {}
        if not verbose:
            log_func_kwargs['log_func'] = None

        stats_name = "compile_mof_file(ns={!r})".format(namespace)
        with self.statistics(stats_name):

            namespace = namespace or self.default_namespace
            self._mainprovider.validate_namespace(namespace)

            # issue #2063 refactor this so there is cleaner interface to
            # WBEMConnection
            mofcomp = MOFCompiler(self._mofwbemconnection,
                                  search_paths=search_paths,
                                  verbose=verbose, **log_func_kwargs)

            mofcomp.compile_file(mof_file, namespace)

    def compile_mof_string(self, mof_str, namespace=None, search_paths=None,
                           verbose=None):
        """
        Compile the MOF definitions in the specified string and add the
        resulting CIM objects to the specified CIM namespace of the
        CIM repository.

        If the namespace does not exist, :exc:`~pywbem.CIMError` with status
        CIM_ERR_INVALID_NAMESPACE is raised.

        This method supports all MOF pragmas, and specifically the include
        pragma.

        If a CIM class or CIM qualifier type to be added already exists in the
        target namespace with the same name (comparing case insensitively),
        this method  raises :exc:`~pywbem.CIMError`.

        If a CIM instance to be added already exists in the target namespace
        with the same keybinding values, this method raises
        :exc:`~pywbem.CIMError`.

        In all cases where this method raises an exception, the CIM repository
        remains unchanged.

        Parameters:

          mof_str (:term:`string`):
            A string with the MOF definitions to be compiled.

          namespace (:term:`string`):
            The name of the CIM namespace in the associated CIM repository that
            is the target of the compilation, and is also used for lookup of any
            dependent CIM elements. If `None`, the default namespace of the
            connection is used. A namespace defined in a namespace pragma of
            the MOF superceeds this namespace from the point in the
            compilation unit(string/file) where it is declared.  The namespace
            specified in this parameter or the MOF inamespace pragma must
            exist.

          search_paths (:term:`py:iterable` of :term:`string`):
            An iterable of directory path names where MOF dependent files will
            be looked up.
            See the description of the `search_path` init parameter of the
            :class:`~pywbem.MOFCompiler` class for more information on MOF
            dependent files.

          verbose (:class:`py:bool`):
            Controls whether to issue more detailed compiler messages.

        Raises:

          IOError: MOF file not found.
          :exc:`~pywbem.MOFCompileError`: Compile error in the MOF.
        """

        # By default, error messages are always printed in addition to being
        # raised as MOFCompileError. We only want them to be printed in verbose
        # mode:
        log_func_kwargs = {}
        if not verbose:
            log_func_kwargs['log_func'] = None

        stats_name = "compile_mof_string(ns={!r})".format(namespace)
        with self.statistics(stats_name):

            namespace = namespace or self.default_namespace
            self._mainprovider.validate_namespace(namespace)

            mofcomp = MOFCompiler(self._mofwbemconnection,
                                  search_paths=search_paths,
                                  verbose=verbose, **log_func_kwargs)

            mofcomp.compile_string(mof_str, namespace)

    def compile_schema_classes(self, class_names, schema_pragma_files,
                               namespace=None, verbose=False):
        # pylint: disable=line-too-long
        """
        Compile the classes defined by `class_names` and all of their
        dependences. The class names must be classes in the defined schema and
        with pragma statements in a schema pragma file. Each
        schema pragma file in the `schema_pragma_files` parameter must be in a
        directory that also encompasses the MOF files for all of the classes
        defined in the schema pragma file and the dependencies of those
        classes. While the relative paths of all of the CIM class files is
        defined in the `schema_pragma_file` the pywbem MOF compiler may also
        search for dependencies (ex. superclasses, references, etc.) that are
        not specifically listed in the `class_names` and the path of the
        `schema_pragma_file` is the top level directory for that search. The
        mof schema directory must include:

        1. Qualifier declarations defined in a single file with the name
           `qualifiers.mof` defined within the directory defined by the
           `schema_mof_dir` parameter

        2. The file `schema_pragma_file` that defines the location of all
           of the CIM class files within the a schema mof directory
           hierarchy. This is the `schema_pragma_file` attribute of the
           DMTFCIMSchema class.

        3. The MOF files, one for each class, for the classes that could be
           compiled within the directory hierarchy defined by `schema_mof_dir`.

        Only the leaf class names need be included in the `class_names` list
        since the compiler will find all dependencies as part of the dependency
        resolution for the compile of each class in `class_names`.

        Parameters:

          class_names (:term:`string` or :class:`py:list` of :term:`string`):
            Class names of the classes to be compiled. These class names must
            be a subset of the classes defined in `schema_pragma_file`.

          schema_pragma_files (:term:`string` or :class:`py:list` of :term:`string`):
            Relative or absolute file path(s) of schema pragma files that
            include a MOF pragma include statement for each CIM class to be
            compiled.  This file path is available from
            :attr:`pywbem_mock.DMTFCIMSchema.schema_pragma_file`.

          namespace (:term:`string`):
            The name of the CIM namespace in the associated CIM repository that
            is the target of the compilation, and is also used for lookup of any
            dependent CIM elements. If `None`, the default namespace of the
            connection is used. A namespace defined in a namespace pragma of
            the MOF superceeds this namespace from the point in the
            compilation unit(string/file) where it is declared.  The namespace
            specified in this parameter or the MOF inamespace pragma must
            exist.

          verbose (:class:`py:bool`):
            If `True`, progress messages are output to stdout as the schema is
            downloaded and expanded. Default is `False`.

        Raises:

          :class:`~pywbem.MOFCompileError`: For errors in MOF parsing, finding
            MOF dependencies or issues with the CIM repository.
          :exc:`~pywbem.CIMError`: Other errors relating to the target server
            environment.
        """  # noqa: E501
        # pylint: enable:line-too-long

        stats_name = "compile_schema_classes(ns={!r})".format(namespace)
        with self.statistics(stats_name):

            if isinstance(schema_pragma_files, six.string_types):
                schema_pragma_files = [schema_pragma_files]

            # Build the pragma file and compile for each pragma file in
            # schema_pragma_files. The search path for each compile is the
            # directory containing that schema_pragma_file
            for schema_pragma_file in schema_pragma_files:
                search_path = os.path.dirname(schema_pragma_file)
                compile_pragma = build_schema_mof(
                    class_names, schema_pragma_file)
                self.compile_mof_string(compile_pragma,
                                        namespace=namespace,
                                        search_paths=search_path,
                                        verbose=verbose)

    ######################################################################
    #
    #       Add Pywbem CIM objects directly to the data store
    #
    ######################################################################

    def add_cimobjects(self, objects, namespace=None):
        # pylint: disable=line-too-long
        """
        Add CIM classes, instances and/or CIM qualifier types (declarations)
        to the specified CIM namespace of the CIM repository.

        This method adds a copy of the objects presented so that the user may
        modify the objects without impacting the repository.

        If the namespace does not exist, :exc:`~pywbem.CIMError` with status
        CIM_ERR_INVALID_NAMESPACE is raised.

        The method imposes very few limits on the objects added. It does
        require that the superclass exist for any class added and that
        instances added include a path component. If the qualifier flavor
        attributes are not set, it sets them to those defined in the Qualifier
        Declarations if those exist.

        If a CIM class or CIM qualifier type to be added already exists in the
        target namespace with the same name (comparing case insensitively),
        this method fails, and the CIM repository remains unchanged.

        If a CIM instance to be added already exists in the target namespace
        with the same keybinding values, this method fails, and the
        CIM repository remains unchanged.

        Parameters:

          objects (:class:`~pywbem.CIMClass` or :class:`~pywbem.CIMInstance` or :class:`~pywbem.CIMQualifierDeclaration`, or list of them):
            CIM object or objects to be added to the CIM repository. The
            list may contain different kinds of CIM objects.

          namespace (:term:`string`):
            The name of the target CIM namespace in the CIM repository. This
            namespace is also used for lookup of any existing or dependent
            CIM objects. If `None`, the default namespace of the connection is
            used.

        Raises:

          ValueError: Invalid input CIM object in `objects` parameter.
          TypeError: Invalid type in `objects` parameter.
          :exc:`~pywbem.CIMError`: CIM_ERR_INVALID_NAMESPACE: Namespace does
            not exist.
          :exc:`~pywbem.CIMError`: Failure related to the CIM objects in the
            CIM repository.
        """  # noqa: E501
        # pylint: enable=line-too-long

        stats_name = "add_cimobjects(ns={!r})".format(namespace)
        with self.statistics(stats_name):

            namespace = namespace or self.default_namespace
            self._mainprovider.validate_namespace(namespace)

            if isinstance(objects, list):
                for obj in objects:
                    self.add_cimobjects(obj, namespace=namespace)

            else:
                obj = objects
                if isinstance(obj, CIMClass):
                    cc = obj.copy()
                    if cc.superclass:
                        if not self._mainprovider.class_exists(
                                namespace, cc.superclass):
                            raise ValueError(
                                _format("Class {0!A} defines superclass {1!A} "
                                        "but the superclass does not exist in "
                                        "the repository.",
                                        cc.classname, cc.superclass))

                    # pylint: disable=protected-access
                    cc1 = self._mainprovider._resolve_class(
                        cc, namespace,
                        self.cimrepository.get_qualifier_store(namespace),
                        verbose=False)

                    class_store = self.cimrepository.get_class_store(namespace)
                    class_store.create(cc.classname, cc1.copy())

                elif isinstance(obj, CIMInstance):
                    inst = obj.copy()
                    if inst.path is None:
                        raise ValueError(
                            _format("Instances added must include a path. "
                                    "Instance {0!A} does not include a path",
                                    inst))
                    if inst.path.namespace is None:
                        inst.path.namespace = namespace
                    if inst.path.host is not None:
                        inst.path.host = None
                    instance_store = \
                        self.cimrepository.get_instance_store(namespace)
                    try:
                        if instance_store.object_exists(inst.path):
                            raise ValueError(
                                _format("Instance {0!A} already exists in "
                                        "CIM repository", inst))
                    except CIMError as ce:
                        raise CIMError(
                            CIM_ERR_FAILED,
                            _format("Internal failure of add_cimobject "
                                    "operation. Rcvd CIMError {0!A}", ce))
                    instance_store.create(inst.path, inst)

                elif isinstance(obj, CIMQualifierDeclaration):
                    qual = obj.copy()
                    qualifier_store = \
                        self.cimrepository.get_qualifier_store(namespace)
                    qualifier_store.create(qual.name, qual)

                else:
                    # Internal mocker error
                    assert False, \
                        _format("Object to add_cimobjects. {0} invalid type",
                                type(obj))

    def display_repository(self, namespaces=None, dest=None, summary=False,
                           output_format='mof'):
        """
        Display the namespaces and objects in the CIM repository in one of
        multiple formats to a destination.

        Parameters:

          namespaces (:term:`string` or :class:`py:list` of :term:`string`):
            Limits display output to the specified CIM namespace or namespaces.
            If `None`, all namespaces of the CIM repository are displayed.

          dest (:term:`string`):
            File path of an output file. If `None`, the output is written to
            stdout.

          summary (:class:`py:bool`):
            Flag for summary mode. If `True`, only a summary count of CIM
            objects in the specified namespaces of the CIM repository is
            produced. If `False`, both the summary count and the details of
            the CIM objects are produced.

          output_format (:term:`string`):
            Output format, one of: 'mof', 'xml', or 'repr'.
        """

        # The comments are line oriented.
        if output_format == 'mof':
            cmt_begin = '// '
            cmt_end = ''
        elif output_format == 'xml':
            cmt_begin = '<!-- '
            cmt_end = ' ->'
        else:
            cmt_begin = ''
            cmt_end = ''
        if output_format not in OUTPUT_FORMATS:
            raise ValueError(
                _format("Invalid output format definition {0!A}. "
                        "{1!A} are valid.", output_format, OUTPUT_FORMATS))

        _uprint(dest,
                _format(u"{0}========Mock Repo Display fmt={1} "
                        u"namespaces={2} ========={3}\n",
                        cmt_begin, output_format,
                        ('all' if namespaces is None
                         else _format("{0!A}", namespaces)),
                        cmt_end))

        # get all namespace names
        repo_ns = sorted(self.namespaces)

        for ns in repo_ns:
            _uprint(dest,
                    _format(u"\n{0}NAMESPACE {1!A}{2}\n",
                            cmt_begin, ns, cmt_end))
            self._display_objects('Qualifier Declarations',
                                  self.cimrepository.get_qualifier_store(ns),
                                  ns, cmt_begin, cmt_end, dest=dest,
                                  summary=summary, output_format=output_format)
            self._display_objects('Classes',
                                  self.cimrepository.get_class_store(ns), ns,
                                  cmt_begin, cmt_end, dest=dest,
                                  summary=summary, output_format=output_format)
            self._display_objects('Instances',
                                  self.cimrepository.get_instance_store(ns), ns,
                                  cmt_begin, cmt_end, dest=dest,
                                  summary=summary, output_format=output_format)

        _uprint(dest,
                _format(u'{0}============End Repository================={1}',
                        cmt_begin, cmt_end))

    @staticmethod
    def _display_objects(obj_type, object_repo, namespace, cmt_begin, cmt_end,
                         dest=None, summary=None, output_format=None):
        """
        Display a set of objects of obj_type from the dictionary defined
        by the parameter object_repo. obj_type is a string that defines the
        type of object ('Classes', 'Instances', 'Qualifier Declarations',
        'Methods').
        """

        # Issue #2062: Consider sorting to preserve order of
        # compile/add. Make this part of refactor to separate repository and
        # datastore because it may be data store dependent
        _uprint(dest,
                _format(u"{0}Namespace {1!A}: contains {2} {3} {4}\n",
                        cmt_begin, namespace,
                        object_repo.len(),
                        obj_type, cmt_end))
        if summary:
            return

        # instances are special because the inner struct is a list
        if obj_type == 'Instances':
            # Issue # 2062 - Consider sorting here in the future
            for inst in object_repo.iter_values():
                if output_format == 'xml':
                    _uprint(dest,
                            _format(u"{0} Path={1} {2}\n{3}",
                                    cmt_begin, inst.path.to_wbem_uri(),
                                    cmt_end,
                                    _pretty_xml(inst.tocimxmlstr())))
                elif output_format == 'repr':
                    _uprint(dest,
                            _format(u"Path:\n{0!A}\nInst:\n{1!A}\n",
                                    inst.path, inst))
                else:
                    _uprint(dest,
                            _format(u"{0} Path={1} {2}\n{3}",
                                    cmt_begin, inst.path.to_wbem_uri(),
                                    cmt_end, inst.tomof()))

        else:
            # Display classes and qualifier declarations sorted
            assert obj_type in ['Classes', 'Qualifier Declarations']
            names = list(object_repo.iter_names())
            if names:
                for name in sorted(names):
                    obj = object_repo.get(name)
                    if output_format == 'xml':
                        _uprint(dest, _pretty_xml(obj.tocimxmlstr()))
                    elif output_format == 'repr':
                        _uprint(dest, _format(u"{0!A}", obj))
                    else:
                        _uprint(dest, obj.tomof())

    def register_provider(self, provider, namespaces=None,
                          schema_pragma_files=None, verbose=None):
        # pylint: disable=line-too-long
        """
        Register the `provider` object for specific namespaces and CIM classes.
        Registering a provider tells the FakedWBEMConnection that the provider
        implementation provided with this method as the `provider` parameter is
        to be executed as the request response method for the namespaces
        defined in the `namespaces` parameter, the provider type defined in the
        'provider_type` attribute of the `provider` and the class(es)
        defined in the provider `provider_classnames` attribute of the
        `provider`.

        The provider registration process includes:

        1. Validation that the namespaces defined for the provider exist.
        2. Validation that the superclass of the provider is consistent with
           the `provider_type` attribute defined in the provider.
        3. Installation of any CIM classes defined by the provider
           `provider_classnames` attribute including dependencies for these
           classes using the `schema_pragma_files` parameter to define the MOF
           compiler search directories for dependencies.
        4. Adding the provider to the registry of user_providers so that any
           of the request methods defined for the `provider_type` are
           passed to this provider in place of the default request processors.
        5. Execute post_register_setup() call to the provider to allow the
           provider to perform any special setup functionality.

        Providers can only be registered for the following request response
        methods:

        1. provider_type = 'instance': defines methods for CreateInstance,
           ModifyInstance, and DeleteInstance requests within a subclass of
           the `InstanceWriteProvider` class.

        2. provider_type = 'method': defines a InvokeMethod method within
           a subclass of the `MethodProvider` class.

        Each classname in a particular namespace may have at most one provider
        registered

        Parameters:

          provider (instance of subclass of :class:`pywbem_mock.InstanceWriteProvider` or :class:`pywbem_mock.MethodProvider`):
            An instance of the user provider class which is a subclass of
            :class:`pywbem_mock.InstanceWriteProvider`.  The methods in this
            subclass override the corresponding methods in
            InstanceWriteProvider. The method call parameters must be the
            same as the defult method in InstanceWriteProvider and it must
            return data in the same format if the default method returns data.

          namespaces (:term:`string` or :class:`py:list` of :term:`string`):
            Namespace or namespaces for which the provider is to be registered.

            If `None`, the default namespace of the connection will be used.

          schema_pragma_files  (:term:`string` or :class:`py:list` of :term:`string`):
            File paths defining a schema pragma file MOF for the set of CIM
            classes that make up a schema such as the DMTF schema. These files
            must contain include pragma statements defining the file location
            of the classes to be compiled for the defined provider and for any
            dependencies required to compile those classes.  The directory
            containing each schema pragma file is passed to the MOF compiler as
            the search path for compile dependencies.

            See :class:`pywbem.MOFCompiler` for more information on the
            `search_paths` parameter.

          verbose (:class:`py:bool`):
            Flag to enable detailed display of actions

        Raises:
          TypeError: Invalid provider_type retrieved from provider or
            provider_type does not match superlclass or the
            namespace parameter is invalid.
          ValueError: Provider_type retrieved from provider is not a
            valid string.
          ValueError: Classnames parameter retrieved from provider not a
            valid string or iterable or namespace does not exist
            in repository.
        """  # noqa: E501
        # pylint: enable=line-too-long

        self._provider_registry.register_provider(
            self, provider, namespaces=namespaces,
            schema_pragma_files=schema_pragma_files,
            verbose=verbose)

    def display_registered_providers(self):
        """
        Display information on the currently registered providers.

        Parameters:

          dest (:term:`string`):
            File path of an output file. If `None`, the output is written to
            stdout.
        """
        self._provider_registry.display_registered_providers()

    ########################################################################
    #
    #   Pywbem functions mocked. FakedWBEMConnection only mocks the
    #   WBEMConnection _imethodcall and _methodcall methods.  This captures
    #   all calls to the wbem server.
    #
    ########################################################################

    def _mock_imethodcall(self, methodname, namespace, response_params_rqd=None,
                          **params):  # pylint: disable=unused-argument
        """
        Mocks the WBEMConnection._imethodcall() method.

        This mock calls methods within this class that fake the processing
        in a WBEM server (at the CIM Object level) for the varisous CIM/XML
        methods and return.

        The methodname input parameters directly translate to the server
        request handler names (i.e. GetClass, ...) including capitalization
        """

        # The statistics is already applied in WBEMConnection.

        # Create the local method name
        methodname = '_imeth_' + methodname
        methodnameattr = getattr(self, methodname)

        # Execute the named method
        result = methodnameattr(namespace, **params)

        # sleep for defined number of seconds
        if self._response_delay:
            time.sleep(self._response_delay)

        return result

    def _mock_methodcall(self, methodname, objectname, Params=None, **params):
        # pylint: disable=invalid-name
        """
        Mocks the WBEMConnection._methodcall() method.

        This function performs the same checks and transformations as
        WBEMConnection._methodcall().
        """

        # The statistics is already applied in WBEMConnection.

        # Normalize the target object into either CIMInstanceName or
        # CIMClassName, both with namespace set.
        if isinstance(objectname, (CIMInstanceName, CIMClassName)):
            localobject = objectname.copy()
            if localobject.namespace is None:
                localobject.namespace = self.default_namespace
            localobject.host = None
        elif isinstance(objectname, six.string_types):
            # a string is always interpreted as a class name
            localobject = CIMClassName(objectname,
                                       namespace=self.default_namespace)
        else:
            raise TypeError(
                _format("The 'ObjectName' parameter of the WBEMConnection "
                        "operation has invalid type {0} (must be a string, "
                        "a CIMClassName, or a CIMInstanceName)",
                        type(objectname)))

        # Merge the Params and **params into a single no-case dictionary
        # of name: CIMParameter
        params_dict = NocaseDict()
        if Params:
            for param in Params:
                if isinstance(param, CIMParameter):
                    params_dict[param.name] = param
                elif isinstance(param, tuple):
                    params_dict[param[0]] = CIMParameter(param[0],
                                                         cimtype(param[1]),
                                                         value=param[1])
                else:
                    raise TypeError(
                        _format("InvokeMethod of method {0!A} on object {1!A}: "
                                "A parameter in the Params argument has "
                                "incorrect Python type {2} "
                                "- expected one of tuple (name, value) or "
                                "pywbem.CIMParameter",
                                methodname, localobject, type(param)))
        if params:
            for pname, pvalue in params.items():
                params_dict[pname] = CIMParameter(
                    pname, cimtype(pvalue), value=pvalue)

        result = self._meth_InvokeMethod(methodname, localobject, params_dict)

        # Sleep for defined number of seconds
        if self._response_delay:
            time.sleep(self._response_delay)

        return result

    @staticmethod
    def _make_pull_imethod_resp(objs, eos, context_id):
        """
        Create the correct imethod response for the open and pull methods
        """
        eos_tuple = (u'EndOfSequence', None, eos)
        enum_ctxt_tuple = (u'EnumerationContext', None, context_id)

        return [("IRETURNVALUE", {}, objs), enum_ctxt_tuple, eos_tuple]

    @staticmethod
    def _make_openquery_imethod_resp(objs, eos, context_id, result_class):
        """
        Create the correct imethod response for the OpenQueryInstances method
        """
        eos_tuple = (u'EndOfSequence', None, eos)
        enum_ctxt_tuple = (u'EnumerationContext', None, context_id)
        result_class_tuple = (u'QueryResultClass', None, result_class)

        return [("IRETURNVALUE", {}, objs), enum_ctxt_tuple, eos_tuple,
                result_class_tuple]

    @staticmethod
    def _make_tuple(rtn_value):
        """
        Change the return value from the value consistent with the definition
        in cim_operations.py into a tuple in accord with _imethodcall
        """
        return [("IRETURNVALUE", {}, rtn_value)]

    def _return_assoc_tuple(self, objects):
        """
        Create the property tuple for _imethod return of references,
        referencenames, associators, and associatornames methods.

        This is different than the get/enum imethod return tuples. It creates an
        OBJECTPATH for each object in the return list.

        _imethod call returns None when there are zero objects rather
        than a tuple with empty object path
        """
        if objects:
            result = [(u'OBJECTPATH', {}, obj) for obj in objects]
            return self._make_tuple(result)

        return None

    #####################################################################
    #
    #  The following methods map the imethodcall interface (dictionary of
    #  the method parameters to the arguments required by each corresponding
    #  method in the MainProvider  or InstanceWriteProvider and call that
    #  method. the resultsare mapped back to be compatible with imethodcall
    #  return tuple.
    #  Methods that allow user providers are routed to the
    #  InstanceWriteProvider. All other methods are rounted to the
    #  MainProvider.
    #
    #  In general, the namespace that is the target of each operation is
    #  provided as a separate parameter even if the public API defines
    #  the namespace as part of the target object definition
    #
    #####################################################################

    # Instance Operations

    def _imeth_EnumerateInstanceNames(self, namespace, **params):
        """
        Call :meth:`~pywbem_mock.MainProvider.EnumerateInstanceNames` with
        parameters defined for that method and map response to tuple response
        for imethodcall.

        Parameters:

          namespace (:term:`string_type`):
            The namespace from which the instance namess are to be retrieved.
            Must not be None.

          params (class:`py:dict`):
            Dictionary of parameters for the method called.

        Returns:

          Tuple with instance paths comatible with imethodcall

        Raises:
          Error: Exceptions from the call
        """
        instance_paths = self._mainprovider.EnumerateInstanceNames(
            ClassName=_cvt_rqd_classname(params['ClassName']),
            namespace=namespace)
        return self._make_tuple(instance_paths)

    def _imeth_EnumerateInstances(self, namespace, **params):
        """
        Call :meth:`~pywbem_mock.MainProvider.EnumerateInstances` with
        parameters defined for that method and map response to tuple response
        for imethodcall.

        Parameters:

          namespace (:term:`string_type`):
            The namespace from which the instance is to be retrieved. Must not
            be None.

          params (class:`py:dict`):
            Dictionary of parameters for the method called.

        Returns:
          Tuple with instances comatible with imethodcall

        Raises:
          Error: Exceptions from the call
        """
        instances = self._mainprovider.EnumerateInstances(
            ClassName=_cvt_rqd_classname(params['ClassName']),
            namespace=namespace,
            LocalOnly=params.get('LocalOnly', None),
            DeepInheritance=params.get('DeepInheritance', None),
            IncludeQualifiers=params.get('IncludeQualifiers', None),
            IncludeClassOrigin=params.get('IncludeClassOrigin', None),
            PropertyList=params.get('PropertyList', None))
        return self._make_tuple(instances)

    def _imeth_GetInstance(self, namespace, **params):
        """
        Call :meth:`~pywbem_mock.MainProvider.GetInstance` with
        parameters defined for that method and map response to tuple response
        for imethodcall.

        The method called includes the namespace within the InstanceName
        rather than as a separate element.

        Parameters:

          namespace (:term:`string_type`):
            The namespace from which the instance is to be retrieved. Must not
            be None.

          params (class:`py:dict`):
            Dictionary of parameters for the method called.

        Returns:
          Tuple with instance comatible with imethodcall

        Raises:
          Error: Exceptions from the call
        """
        instance_name = params['InstanceName']
        assert instance_name.namespace is None
        instance_name.namespace = namespace
        instance = self._mainprovider.GetInstance(
            InstanceName=instance_name,
            LocalOnly=params.get('LocalOnly', None),
            IncludeQualifiers=params.get('IncludeQualifiers', None),
            IncludeClassOrigin=params.get('IncludeClassOrigin', None),
            PropertyList=params.get('PropertyList', None))
        return self._make_tuple([instance])

    def _imeth_CreateInstance(self, namespace, **params):
        """
        Call :meth:`~pywbem_mock.ProviderDispatcher.CreateInstance` with
        parameters defined for that method and map response to tuple response
        for imethodcall.

        This method allows user providers and therefore is passed to the
        :class:`ProviderDispatcher`.

        Parameters:

          namespace (:term:`string`):
            Namespace in which the instance will be created
            Must not be None.

          params (class:`py:dict`):
            Dictionary of parameters for the method called.

        Raises:
          Error: Exceptions from the call
        """

        new_instance_path = self._providerdispatcher.CreateInstance(
            namespace=namespace,
            NewInstance=params['NewInstance'])
        return self._make_tuple([new_instance_path])

    def _imeth_ModifyInstance(self, namespace, **params):
        """
        Call :meth:`~pywbem_mock.ProviderDispatcher.ModifyInstance` with
        parameters defined for that method and map response to tuple response
        for imethodcall.


        This method allows user providers and therefore is passed to the
        :class:`ProviderDispatcher`.

        Parameters:
          namespace (:term:`string`):
            Namespace in containing the instance to be modified
            Must not be None.

          params (class:`py:dict`):
            Dictionary of parameters for the method called.

        Raises:
          Error: Exceptions from the call
        """
        modified_instance = params['ModifiedInstance']
        assert modified_instance.path.namespace is None
        modified_instance.path.namespace = namespace

        self._providerdispatcher.ModifyInstance(
            ModifiedInstance=modified_instance,
            IncludeQualifiers=params.get('IncludeQualifiers', None),
            PropertyList=params.get('PropertyList', None))

    def _imeth_DeleteInstance(self, namespace, **params):
        """
        Call :meth:`~pywbem_mock.ProviderDispatcher.DeleteInstance` with
        parameters defined for that method and map response to tuple response
        for imethodcall.

        This method allows user providers and therefore is passed to the
        :class:`ProviderDispatcher`.

        Parameters:
          namespace (:term:`string`):
            Namespace containing the instance to be deleted
            Must not be None.

          params (class:`py:dict`):
            Dictionary of parameters for the method called.

        Raises:
          Error: Exceptions from the call
        """
        instance_name = params['InstanceName']
        assert instance_name.namespace is None
        instance_name.namespace = namespace

        self._providerdispatcher.DeleteInstance(
            InstanceName=instance_name)

    def _imeth_ExecQuery(self, namespace, **params):
        """
        Call :meth:`~pywbem_mock.MainProvider.ExecQuery` with
        parameters defined for that method and map response to tuple response
        for imethodcall.

        Parameters:
          namespace (:term:`string`):
            Namespace containing the class and method
            Must not be None.

          params (class:`py:dict`):
            Dictionary of parameters for the method called.

        Returns:
          Tuple with instances compatible with imethodcall

        Raises:
          Error: Exceptions from the call
        """
        # pylint: disable=assignment-from-no-return
        instances = self._mainprovider.ExecQuery(
            namespace=namespace,
            QueryLanguage=params['QueryLanguage'],
            Query=params['Query'])
        # Issue 2064: The following is untested because the
        # mainprovider ExecQuery only generates exception.
        return self._make_tuple([instances])

    # CIMClass operations

    def _imeth_EnumerateClasses(self, namespace, **params):
        """
        Call :meth:`~pywbem_mock.MainProvider.EnumerateClasses` with
        parameters defined for that method and map response to tuple response
        for imethodcall.
        """
        classes = self._mainprovider.EnumerateClasses(
            params.get("namespace", namespace),
            ClassName=_cvt_opt_classname(params.get('ClassName', None)),
            DeepInheritance=params.get('DeepInheritance', None),
            LocalOnly=params.get('LocalOnly', None),
            IncludeQualifiers=params.get('IncludeQualifiers', None),
            IncludeClassOrigin=params.get('IncludeClassOrigin, None)', None))
        return self._make_tuple(classes)

    def _imeth_EnumerateClassNames(self, namespace, **params):
        """
        Call :meth:`~pywbem_mock.MainProvider.EnumerateClasseNames` with
        parameters defined for that method and map response to tuple response
        for imethodcall.
        """
        classnames = self._mainprovider.EnumerateClassNames(
            params.get("namespace", namespace),
            ClassName=_cvt_opt_classname(params.get('ClassName', None)),
            DeepInheritance=params.get('DeepInheritance', None))

        # Map the class name strings to CIMClassName
        rtn_cim_classnames = [
            CIMClassName(cn, namespace=namespace, host=self.host)
            for cn in classnames]
        return self._make_tuple(rtn_cim_classnames)

    def _imeth_GetClass(self, namespace, **params):
        """
        Call :meth:`~pywbem_mock.MainProvider.EGetClass` with
        parameters defined for that method and map response to tuple response
        for imethodcall.
        """
        klass = self._mainprovider.GetClass(
            params.get("namespace", namespace),
            ClassName=_cvt_rqd_classname(params['ClassName']),
            LocalOnly=params.get('LocalOnly', None),
            IncludeQualifiers=params.get('IncludeQualifiers', None),
            IncludeClassOrigin=params.get('IncludeClassOrigin', None),
            PropertyList=params.get('PropertyList', None))
        return self._make_tuple([klass])

    def _imeth_CreateClass(self, namespace, **params):
        """
        Call :meth:`~pywbem_mock.MainProvider.CreateClass` with
        parameters defined for that method and map response to tuple response
        for imethodcall.
        """
        self._mainprovider.CreateClass(
            namespace,
            NewClass=params['NewClass'])

    def _imeth_ModifyClass(self, namespace, **params):
        """
        Call :meth:`~pywbem_mock.MainProvider.ModifyClass` with
        parameters defined for that method and map response to tuple response
        for imethodcall.
        """
        self._mainprovider.ModifyClass(
            namespace,
            ModifiedClass=params['ModifiedClass'])

    def _imeth_DeleteClass(self, namespace, **params):
        """
        Call :meth:`~pywbem_mock.MainProvider.DeleteClass` with
        parameters defined for that method and map response to tuple response
        for imethodcall.
        """
        self._mainprovider.DeleteClass(
            namespace,
            ClassName=_cvt_rqd_classname(params['ClassName']))

    # Qualifier declaration operations

    def _imeth_EnumerateQualifiers(self, namespace, **params):
        # pylint: disable=unused-argument
        """
        Call :meth:`~pywbem_mock.MainProvider.EnumerateQualifiers` with
        parameters defined for that method and map response to tuple response
        for imethodcall.
        """
        qualifiers = self._mainprovider.EnumerateQualifiers(
            namespace=namespace)
        return self._make_tuple(qualifiers)

    def _imeth_GetQualifier(self, namespace, **params):
        """
        Call :meth:`~pywbem_mock.MainProvider.GetQualifier` with
        parameters defined for that method and map response to tuple response
        for imethodcall.
        """
        qualifier = self._mainprovider.GetQualifier(
            namespace=namespace,
            QualifierName=params['QualifierName'])
        return self._make_tuple([qualifier])

    def _imeth_DeleteQualifier(self, namespace, **params):
        """
        Call :meth:`~pywbem_mock.MainProvider.DeleteQualifier` with
        parameters defined for that method and map response to tuple response
        for imethodcall.
        """
        self._mainprovider.DeleteQualifier(
            namespace=namespace,
            QualifierName=params['QualifierName'])

    def _imeth_SetQualifier(self, namespace, **params):
        """
        Call :meth:`~pywbem_mock.MainProvider.SetQualifier` with
        parameters defined for that method and map response to tuple response
        for imethodcall.
        """
        self._mainprovider.SetQualifier(
            namespace=namespace,
            QualifierDeclaration=params['QualifierDeclaration'])

    # Associator and Reference operations

    def _imeth_ReferenceNames(self, namespace, **params):
        """
        Call :meth:`~pywbem_mock.MainProvider.ReferenceNames` with
        parameters defined for that method and map response to tuple response
        for imethodcall.,
        """
        object_names = self._mainprovider.ReferenceNames(
            namespace=namespace,
            ObjectName=_cvt_obj_name(params['ObjectName']),
            ResultClass=_cvt_opt_classname(params.get('ResultClass', None)),
            Role=params.get('Role', None))
        return self._return_assoc_tuple(object_names)

    def _imeth_References(self, namespace, **params):
        """
        Call :meth:`~pywbem_mock.MainProvider.References` with
        parameters defined for that method and map response to tuple response
        for imethodcall.
        """
        objects = self._mainprovider.References(
            namespace=namespace,
            ObjectName=_cvt_obj_name(params['ObjectName']),
            ResultClass=_cvt_opt_classname(params.get('ResultClass', None)),
            Role=params.get('Role', None),
            IncludeQualifiers=params.get('IncludeQualifiers', None),
            IncludeClassOrigin=params.get('IncludeClassOrigin', None),
            PropertyList=params.get('PropertyList', None))
        return self._return_assoc_tuple(objects)

    def _imeth_AssociatorNames(self, namespace, **params):
        """
        Call :meth:`~pywbem_mock.MainProvider.AssociatorNames` with
        parameters defined for that method and map response to tuple response
        for imethodcall.
        """
        object_names = self._mainprovider.AssociatorNames(
            namespace=namespace,
            ObjectName=_cvt_obj_name(params['ObjectName']),
            AssocClass=_cvt_opt_classname(params.get('AssocClass', None)),
            ResultClass=_cvt_opt_classname(params.get('ResultClass', None)),
            Role=params.get('Role', None),
            ResultRole=params.get('ResultRole', None))
        return self._return_assoc_tuple(object_names)

    def _imeth_Associators(self, namespace, **params):
        """
        Call :meth:`~pywbem_mock.MainProvider.Associators` with
        parameters defined for that method and map response to tuple response
        for imethodcall.
        """
        objects = self._mainprovider.Associators(
            namespace=namespace,
            ObjectName=_cvt_obj_name(params['ObjectName']),
            AssocClass=_cvt_opt_classname(params.get('AssocClass', None)),
            ResultClass=_cvt_opt_classname(params.get('ResultClass', None)),
            Role=params.get('Role', None),
            ResultRole=params.get('ResultRole', None),
            IncludeQualifiers=params.get('IncludeQualifiers', None),
            IncludeClassOrigin=params.get('IncludeClassOrigin', None),
            PropertyList=params.get('PropertyList', None))
        return self._return_assoc_tuple(objects)

    # The pull operations including Open..., Pull... and CloseEnumeration

    def _imeth_OpenEnumerateInstancePaths(self, namespace, **params):
        """
        Call :meth:`~pywbem_mock.MainProvider.OpenEnumerateInstancePaths` with
        parameters defined for that method and map response to tuple response
        for imethodcall.
        """
        context_tuple = self._mainprovider.OpenEnumerateInstancePaths(
            namespace=namespace,
            ClassName=_cvt_rqd_classname(params['ClassName']),
            FilterQueryLanguage=params.get('FilterQueryLanguage', None),
            FilterQuery=params.get('FilterQuery', None),
            OperationTimeout=params.get('OperationTimeout', None),
            ContinueOnError=params.get('ContinueOnError', None),
            MaxObjectCount=params.get('MaxObjectCount', None))
        return self._make_pull_imethod_resp(*context_tuple)

    def _imeth_OpenEnumerateInstances(self, namespace, **params):
        """
        Call :meth:`~pywbem_mock.MainProvider.OpenEnumerateInstances` with
        parameters defined for that method and map response to tuple response
        for imethodcall.
        """

        context_tuple = self._mainprovider.OpenEnumerateInstances(
            namespace=namespace,
            ClassName=_cvt_rqd_classname(params['ClassName']),
            DeepInheritance=params.get('DeepInheritance', None),
            IncludeClassOrigin=params.get('IncludeClassOrigin', None),
            PropertyList=params.get('PropertyList', None),
            FilterQueryLanguage=params.get('FilterQueryLanguage', None),
            FilterQuery=params.get('FilterQuery', None),
            OperationTimeout=params.get('OperationTimeout', None),
            ContinueOnError=params.get('ContinueOnError', None),
            MaxObjectCount=params.get('MaxObjectCount', None))
        return self._make_pull_imethod_resp(*context_tuple)

    def _imeth_OpenReferenceInstancePaths(self, namespace, **params):
        """
        Call :meth:`~pywbem_mock.MainProvider.OpenReferenceInstancePaths` with
        parameters defined for that method and map response to tuple response
        for imethodcall.
        """
        context_tuple = self._mainprovider.OpenReferenceInstancePaths(
            namespace=namespace,
            InstanceName=params['InstanceName'],
            ResultClass=_cvt_opt_classname(params.get('ResultClass', None)),
            Role=params.get('Role', None),
            FilterQueryLanguage=params.get('FilterQueryLanguage', None),
            FilterQuery=params.get('FilterQuery', None),
            OperationTimeout=params.get('OperationTimeout', None),
            ContinueOnError=params.get('ContinueOnError', None),
            MaxObjectCount=params.get('MaxObjectCount', None))
        return self._make_pull_imethod_resp(*context_tuple)

    def _imeth_OpenReferenceInstances(self, namespace, **params):
        """
        Call :meth:`~pywbem_mock.MainProvider.OpenReferenceInstances` with
        parameters defined for that method and map response to tuple response
        for imethodcall.
        """
        context_tuple = self._mainprovider.OpenReferenceInstances(
            namespace=namespace,
            InstanceName=params['InstanceName'],
            ResultClass=_cvt_opt_classname(params.get('ResultClass', None)),
            Role=params.get('Role', None),
            IncludeClassOrigin=params.get('IncludeClassOrigin', None),
            PropertyList=params.get('PropertyList', None),
            FilterQueryLanguage=params.get('FilterQueryLanguage', None),
            FilterQuery=params.get('FilterQuery', None),
            OperationTimeout=params.get('OperationTimeout', None),
            ContinueOnError=params.get('ContinueOnError', None),
            MaxObjectCount=params.get('MaxObjectCount', None))
        return self._make_pull_imethod_resp(*context_tuple)

    def _imeth_OpenAssociatorInstances(self, namespace, **params):
        """
        Call :meth:`~pywbem_mock.MainProvider.OpenAssociatorInstances` with
        parameters defined for that method and map response to tuple response
        for imethodcall.
        """
        context_tuple = self._mainprovider.OpenAssociatorInstances(
            namespace=namespace,
            InstanceName=params['InstanceName'],
            AssocClass=_cvt_opt_classname(params.get('AssocClass', None)),
            ResultClass=_cvt_opt_classname(params.get('ResultClass', None)),
            Role=params.get('Role', None),
            ResultRole=params.get('ResultRole', None),
            IncludeClassOrigin=params.get('IncludeClassOrigin', None),
            PropertyList=params.get('PropertyList', None),
            FilterQueryLanguage=params.get('FilterQueryLanguage', None),
            FilterQuery=params.get('FilterQuery', None),
            OperationTimeout=params.get('OperationTimeout', None),
            ContinueOnError=params.get('ContinueOnError', None),
            MaxObjectCount=params.get('MaxObjectCount', None))
        return self._make_pull_imethod_resp(*context_tuple)

    def _imeth_OpenAssociatorInstancePaths(self, namespace, **params):
        """
        Call :meth:`~pywbem_mock.MainProvider.OpenAssociatorInstancePaths` with
        parameters defined for that method and map response to tuple response
        for imethodcall.
        """
        context_tuple = self._mainprovider.OpenAssociatorInstancePaths(
            namespace=namespace,
            InstanceName=params['InstanceName'],
            AssocClass=_cvt_opt_classname(params.get('AssocClass', None)),
            ResultClass=_cvt_opt_classname(params.get('ResultClass', None)),
            Role=params.get('Role', None),
            ResultRole=params.get('ResultRole', None),
            FilterQueryLanguage=params.get('FilterQueryLanguage', None),
            FilterQuery=params.get('FilterQuery', None),
            OperationTimeout=params.get('OperationTimeout', None),
            ContinueOnError=params.get('ContinueOnError', None),
            MaxObjectCount=params.get('MaxObjectCount', None))
        return self._make_pull_imethod_resp(*context_tuple)

    def _imeth_OpenQueryInstances(self, namespace, **params):
        """
        Call :meth:`~pywbem_mock.MainProvider.OpenQueryInstances` with
        parameters defined for that method and map response to tuple response
        for imethodcall.
        """
        context_tuple = self._mainprovider.OpenQueryInstances(
            namespace=namespace,
            FilterQueryLanguage=params.get('FilterQueryLanguage', None),
            FilterQuery=params.get('FilterQuery', None),
            ReturnQueryResultClass=params.get('ReturnQueryResultClass', None),
            OperationTimeout=params.get('OperationTimeout', None),
            ContinueOnError=params.get('ContinueOnError', None),
            MaxObjectCount=params.get('MaxObjectCount', None))
        return self._make_openquery_imethod_resp(*context_tuple)

    def _imeth_PullInstancePaths(self, namespace, **params):
        # pylint: disable=unused-argument
        """
        Call :meth:`~pywbem_mock.MainProvider.PullInstancePaths` with
        parameters defined for that method and map response to tuple response
        for imethodcall.
        """
        context_tuple = self._mainprovider.PullInstancePaths(
            EnumerationContext=params['EnumerationContext'],
            MaxObjectCount=params['MaxObjectCount'])
        return self._make_pull_imethod_resp(*context_tuple)

    def _imeth_PullInstancesWithPath(self, namespace, **params):
        # pylint: disable=unused-argument
        """
        Call :meth:`~pywbem_mock.MainProvider.PullInstancesWithPath` with
        parameters defined for that method and map response to tuple response
        for imethodcall.
        """
        context_tuple = self._mainprovider.PullInstancesWithPath(
            EnumerationContext=params['EnumerationContext'],
            MaxObjectCount=params['MaxObjectCount'])
        return self._make_pull_imethod_resp(*context_tuple)

    def _imeth_PullInstances(self, namespace, **params):
        # pylint: disable=unused-argument
        """
        Call :meth:`~pywbem_mock.MainProvider.PullInstances` with
        parameters defined for that method and map response to tuple response
        for imethodcall.
        """
        context_tuple = self._mainprovider.PullInstances(
            EnumerationContext=params['EnumerationContext'],
            MaxObjectCount=params['MaxObjectCount'])
        return self._make_pull_imethod_resp(*context_tuple)

    def _imeth_CloseEnumeration(self, namespace, **params):
        # pylint: disable=unused-argument
        """
        Call :meth:`~pywbem_mock.MainProvider.CloseEnumeration` with
        parameters defined for that method. Returns nothing
        """
        self._mainprovider.CloseEnumeration(
            EnumerationContext=params['EnumerationContext'])

    def _meth_InvokeMethod(self, methodname, localobject, params):
        # pylint: disable=invalid-name
        """
        Call :meth:`~pywbem_mock.ProviderDispatcher.InvokeMethod`.
        """
        result = self._providerdispatcher.InvokeMethod(
            methodname, localobject, params)
        return result
