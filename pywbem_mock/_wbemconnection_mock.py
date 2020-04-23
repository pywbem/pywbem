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

import time
import sys
import traceback
import re
from xml.dom import minidom
from mock import Mock
import six

from pywbem import WBEMConnection, CIMClass, CIMClassName, \
    CIMInstance, CIMInstanceName, CIMParameter, CIMQualifierDeclaration, \
    cimtype, CIMError, CIM_ERR_FAILED, DEFAULT_NAMESPACE, \
    CIM_ERR_METHOD_NOT_FOUND, MOFCompiler
from pywbem._nocasedict import NocaseDict
from pywbem._utils import _format
from ._mainprovider import MainProvider

from ._inmemoryrepository import InMemoryRepository

from ._mockmofwbemconnection import _MockMOFWBEMConnection

from ._defaultinstanceprovider import ProviderDispatcher, \
    InstanceWriteProvider

from ._dmtf_cim_schema import DMTFCIMSchema
from ._utils import _uprint

__all__ = ['FakedWBEMConnection', 'method_callback_interface']

# Fake Server default values for parameters that apply to repo and operations

# Default Max_Object_Count for Fake Server if not specified by request
_DEFAULT_MAX_OBJECT_COUNT = 100

# Maximum Open... timeout if not set by request
OPEN_MAX_TIMEOUT = 40

# per DSP0200, the default behavior for EnumerateInstance DeepInheritance
# if not set by server.  Default is True.
DEFAULT_DEEP_INHERITANCE = True

# allowed output formats for the repository display
OUTPUT_FORMATS = ['mof', 'xml', 'repr']


# Issue #2065. We have not considered that iq and ico are deprecated in
# on DSP0200 for get_instance, etc. We could  set up a default to ignore these
# parameters for the operations in which they are deprecated and we
# should/could ignore them. We need to document our behavior in relation to the
# spec.


def method_callback_interface(conn, methodname, objectname, **params):
    # pylint: disable=unused-argument, invalid-name, line-too-long
    """
    Interface for user-provided callback functions for CIM method invocation
    on a faked connection.

    **Experimental:** *New in pywbem 0.12 as experimental.*

    Parameters:

      conn (:class:`~pywbem_mock.FakedWBEMConnection`):
        Faked connection. This can be used to access the mock repository of the
        faked connection, via its operation methods (e.g. `GetClass`).

      methodname (:term:`string`):
        The CIM method name that is being invoked. This is the method name for
        which the callback function was registered. This parameter allows a
        single callback function to be registered for multiple methods.

      objectname (:class:`~pywbem.CIMInstanceName` or :class:`~pywbem.CIMClassName`):
        The object path of the target object of the invoked method, as follows:

        * Instance-level call: The instance path of the target instance, as a
          :class:`~pywbem.CIMInstanceName` object which has its `namespace`
          property set to the target namespace of the invocation. Its `host`
          property will not be set.

        * Class-level call: The class path of the target class, as a
          :class:`~pywbem.CIMClassName` object which has its `namespace`
          property set to the target namespace of the invocation. Its `host`
          property will not be set.

      params (:ref:`NocaseDict`):
        The input parameters for the method that were passed to the
        `InvokeMethod` operation.

        Each dictionary item represents a single input parameter for the CIM
        method and is a :class:`~pywbem.CIMParameter` object, regardless of
        how the input parameter was passed to the
        :meth:`~pywbem.WBEMConnection.InvokeMethod` method.

        The :class:`~pywbem.CIMParameter` object will have at least the
        following properties set:

        * name (:term:`string`): Parameter name (case independent).
        * type (:term:`string`): CIM data type of the parameter.
        * value (:term:`CIM data type`): Parameter value.

    Returns:

      tuple: The callback function must return a tuple consisting of:

      * return_value (:term:`CIM data type`): Return value for the CIM
        method.

      * out_params (:term:`py:iterable` of :class:`~pywbem.CIMParameter`):

        Each item represents a single output parameter of the CIM method.
        The :class:`~pywbem.CIMParameter` objects must have at least
        the following properties set:

        * name (:term:`string`): Parameter name (case independent).
        * type (:term:`string`): CIM data type of the parameter.
        * value (:term:`CIM data type`): Parameter value.

    Raises:

      : Since the callback function mocks a CIM method invocation, it should
        raise :exc:`~pywbem.CIMError` exceptions to indicate failures. Any
        other exceptions raised by the callback function will be mapped to
        :exc:`~pywbem.CIMError` exceptions with status CIM_ERR_FAILED and
        a message that contains information about the exception including a
        traceback.
    """  # noqa: E501
    # pylint: enable=line-too-long
    raise NotImplementedError


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
    with a WBEM server by utilizing a local in-memory *mock repository* to
    generate responses in the same way the WBEM server would.

    **Experimental:** *New in pywbem 0.12 as experimental.*

    For a description of the operation methods on this class, see
    :ref:`Faked WBEM operations`.

    Each :class:`~pywbem.FakedWBEMConnection` object has its own mock
    repository which contains multiple CIM namespaces, and each namespace may
    contain CIM qualifier types (declarations), CIM classes and CIM instances.

    This class provides only a subset of the init parameters of
    :class:`~pywbem.WBEMConnection` because it does not have a connection to a
    WBEM server. It uses a faked and fixed URL for the WBEM server
    (``http://FakedUrl``) as a means of identifying the connection by users.

    Logging of the faked operations is supported via the pywbem logging
    facility and can be controlled in the same way as for
    :class:`~pywbem.WBEMConnection`. For details, see
    :ref:`WBEM operation logging`.
    """
    def __init__(self, default_namespace=DEFAULT_NAMESPACE,
                 use_pull_operations=False, stats_enabled=False,
                 timeout=None, response_delay=None,
                 disable_pull_operations=None):
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
            to execute. Setting the variable to True causes pull operation
            requests to the mock CIM repository to return CIM_ERR_NOT_SUPPORTED.

            The :attr:`~pywbem_mock.FakedWBEMConnection.disable_pull_operations`
            property can be used to set this variable.
        """

        # Response delay in seconds. Any operation is delayed by this time.
        # Initialize before superclass init because otherwise logger may
        # fail with this attribute not found
        self._response_delay = response_delay

        # define attribute here to assure it is defined before cim repository
        # created. Reset again after repository created.
        self._disable_pull_operations = disable_pull_operations

        super(FakedWBEMConnection, self).__init__(
            'http://FakedUrl:5988',
            default_namespace=default_namespace,
            use_pull_operations=use_pull_operations,
            stats_enabled=stats_enabled, timeout=timeout)

        # Implementation of the CIM object repository that contains the server
        # handler methods for each of the WBEM operations and is the data store
        # for CIM classes, CIM instances, CIM qualifier declarations and
        # CIM methods for the mocker.  All access to the mocker CIM data must
        # pass through this variable to the CIM repository.
        # See :py:module:`pywbem_mock/inmemoryrepository` for a description of
        # the repository interface.

        # Provider registry defines user added providers.  This is a dictionary
        # with key equal classname that contains entries for namespaces,
        # provider type, and provider for each class name defined
        self.provider_registry = NocaseDict()

        # Define the datastore to be used with an initial namespace, the client
        # connection default namespace. This is passed to the mainprovider
        # and not used further in this class.
        self.cimrepository = InMemoryRepository(self.default_namespace)

        # Initiate the MainProvider with parameters required to execute
        self.mainprovider = MainProvider(self.host,
                                         self.disable_pull_operations,
                                         self.cimrepository)

        # Initiate the InstanceWriteProvider with the cimrepository
        self.defaultinstanceprovider = InstanceWriteProvider(
            self.cimrepository)

        # Initiate instance of the ProviderDispatcher with required
        # parameters including the cimrepository
        self.providerdispatcher = ProviderDispatcher(
            self.cimrepository, self.provider_registry,
            self.defaultinstanceprovider)

        # Flag to allow or disallow the use of the Open... and Pull...
        # operations. Uses the setter method
        self.disable_pull_operations = disable_pull_operations

        # Defines the connection for the compiler.  The compiler uses
        # its local repo for work but sends new objects back to the
        # methods in the mainprovider attached to this class.
        self._mofwbemconnection = _MockMOFWBEMConnection(self,
                                                         self.mainprovider)

        # The CIM methods with callback in the mock repository.
        # This is a dictionary of dictionaries of dictionaries, where the top
        # level key is the CIM namespace name, the second level key is the
        # CIM class name, and the third level key is the CIM method name.
        # The values at the last level are (TBD: method callbacks?).
        # The namespaces are added to the outer dictionary as needed (if
        # permitted as per self.namesaces).
        # TODO/ks: This must move to provider when provider is defined
        self.methods = NocaseDict()

        # Open Pull Contexts. The key for each context is an enumeration
        # context id.  The data is the total list of instances/names to
        # be returned and the current position in the list. Any context in
        # this list is still open.
        self.enumeration_contexts = {}

        self._imethodcall = Mock(side_effect=self._mock_imethodcall)
        self._methodcall = Mock(side_effect=self._mock_methodcall)

    @property
    def namespaces(self):
        """
        list: List of namespaces in the repository.
        """
        return self.mainprovider.namespaces

    @property
    def response_delay(self):
        """
        :term:`number`:
          Artifically created delay for each operation, in seconds.
          If `None`, there is no delay.

          This attribute is settable. For details, see the description of the
          same-named init parameter of
          :class:`this class <pywbem.FakedWBEMConnection>`.
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
        ::`allow`:
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
            # modify the parameter in the mainprovider
            self.mainprovider.disable_pull_operations = disable
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

    def _get_qualifier_store(self, namespace):
        # pylint: disable=missing-function-docstring,missing-docstring
        return self.mainprovider.get_qualifier_store(namespace)

    def _get_class_store(self, namespace):
        # pylint: disable=missing-function-docstring,missing-docstring
        return self.mainprovider.get_class_store(namespace)

    def _get_instance_store(self, namespace):
        # pylint: disable=missing-function-docstring,missing-docstring
        return self.mainprovider.get_instance_store(namespace)

    # TODO: This changes when we add provider concept.
    def _get_method_repo(self, namespace):
        # pylint: disable=missing-function-docstring,missing-docstring
        self.mainprovider.validate_namespace(namespace)
        if namespace not in self.methods:
            self.methods[namespace] = NocaseDict()
        return self.methods[namespace]

    # The namespace management methods must be in the this class directly
    # so they can be access with call to the methods from instance of
    # this class. they are considered part of the external API.

    def add_namespace(self, namespace):
        # pylint: disable=missing-function-docstring,missing-docstring
        self.mainprovider.add_namespace(namespace)

    def remove_namespace(self, namespace):
        # pylint: disable=missing-function-docstring,missing-docstring
        self.mainprovider.remove_namespace(namespace)

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
        of the mock repository.

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

        In all cases where this method raises an exception, the mock repository
        remains unchanged.

        Parameters:

          mof_file (:term:`string`):
            Path name of the file containing the MOF definitions to be compiled.

          namespace (:term:`string`):
            The name of the target CIM namespace in the mock repository. This
            namespace is also used for lookup of any existing or dependent
            CIM objects. If `None`, the default namespace of the connection is
            used.

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

        namespace = namespace or self.default_namespace
        self.mainprovider.validate_namespace(namespace)

        # issue #2063 refactor this so there is cleaner interface to
        # WBEMConnection
        mofcomp = MOFCompiler(self._mofwbemconnection,
                              search_paths=search_paths,
                              verbose=verbose, log_func=None)

        mofcomp.compile_file(mof_file, namespace)

    def compile_mof_string(self, mof_str, namespace=None, search_paths=None,
                           verbose=None):
        """
        Compile the MOF definitions in the specified string and add the
        resulting CIM objects to the specified CIM namespace of the mock
        repository.

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

        In all cases where this method raises an exception, the mock repository
        remains unchanged.

        Parameters:

          mof_str (:term:`string`):
            A string with the MOF definitions to be compiled.

          namespace (:term:`string`):
            The name of the target CIM namespace in the mock repository. This
            namespace is also used for lookup of any existing or dependent
            CIM objects. If `None`, the default namespace of the connection is
            used.

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

        namespace = namespace or self.default_namespace

        self.mainprovider.validate_namespace(namespace)

        mofcomp = MOFCompiler(self._mofwbemconnection,
                              search_paths=search_paths,
                              verbose=verbose, log_func=None)

        mofcomp.compile_string(mof_str, namespace)

    def compile_dmtf_schema(self, schema_version, schema_root_dir, class_names,
                            use_experimental=False, namespace=None,
                            verbose=False):
        """
        Compile the classes defined by `class_names` and their dependent
        classes from the DMTF CIM schema version defined by
        `schema_version` and keep the downloaded DMTF CIM schema in the
        directory defined by `schema_dir`.

        This method uses the :class:`~pywbem_mock.DMTFCIMSchema` class to
        download the DMTF CIM schema defined by `schema_version` from the DMTF,
        into the `schema_root_dir` directory, extract the MOF files, create a
        MOF file with the `#include pragma` statements for the files in
        `class_names` and attempt to compile this set of files.

        It automatically compiles all of the DMTF qualifier declarations that
        are in the files `qualifiers.mof` and `qualifiers_optional.mof`.

        The result of the compilation is added to the specified CIM namespace
        of the mock repository.

        If the namespace does not exist, :exc:`~pywbem.CIMError` with status
        CIM_ERR_INVALID_NAMESPACE is raised.

        Parameters:

          schema_version (tuple of 3 integers (m, n, u):
            Represents the DMTF CIM schema version where:

            * m is the DMTF CIM schema major version
            * n is the DMTF CIM schema minor version
            * u is the DMTF CIM schema update version

            This must represent a DMTF CIM schema that is available from the
            DMTF web site.

          schema_root_dir (:term:`string`):
            Directory into which the DMTF CIM schema is installed or will be
            installed.  A single `schema_dir` can be used for multiple
            schema versions because subdirectories are uniquely defined by
            schema version and schema_type (i.e. Final or Experimental).

            Multiple DMTF CIM schemas may be maintained in the same
            `schema_root_dir` simultaneously because the MOF for each schema is
            extracted into a subdirectory identified by the schema version
            information.

          class_names (:term:`py:list` of :term:`string` or :term:`string`):
            List of class names from the DMTF CIM Schema to be included in the
            repository.

            A single class may be defined as a string not in a list.

            These must be classes in the defined DMTF CIM schema and can be a
            list of just the leaf classes required The MOF compiler will search
            the DMTF CIM schema MOF classes for superclasses, classes defined
            in reference properties, and classes defined in EmbeddedInstance
            qualifiers  and compile them also.

          use_experimental (:class:`py:bool`):
            If `True` the expermental version of the DMTF CIM Schema
            is installed or to be installed.

            If `False` (default) the final version of the DMTF
            CIM Schema is installed or to be installed.

          namespace (:term:`string`):
            The name of the target CIM namespace in the mock repository. This
            namespace is also used for lookup of any existing or dependent
            CIM objects. If `None`, the default namespace of the connection is
            used.

          verbose (:class:`py:bool`):
            If `True`, progress messages are output to stdout

        Raises:

          ValueError: The schema cannot be retrieved from the DMTF web
            site, the schema_version is invalid, or a class name cannot
            be found in the defined DMTF CIM schema.
          TypeError: The 'schema_version' is not a valid tuple with 3
            integer components
          :exc:`~pywbem.MOFCompileError`: Compile error in the MOF.
        """

        schema = DMTFCIMSchema(schema_version, schema_root_dir,
                               use_experimental=use_experimental,
                               verbose=verbose)
        schema_mof = schema.build_schema_mof(class_names)
        search_paths = schema.schema_mof_dir
        self.compile_mof_string(schema_mof, namespace=namespace,
                                search_paths=[search_paths],
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
        to the specified CIM namespace of the mock repository.

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
        this method fails, and the mock repository remains unchanged.

        If a CIM instance to be added already exists in the target namespace
        with the same keybinding values, this method fails, and the mock
        repository remains unchanged.

        Parameters:

          objects (:class:`~pywbem.CIMClass` or :class:`~pywbem.CIMInstance` or :class:`~pywbem.CIMQualifierDeclaration`, or list of them):
            CIM object or objects to be added to the mock repository. The
            list may contain different kinds of CIM objects.

          namespace (:term:`string`):
            The name of the target CIM namespace in the mock repository. This
            namespace is also used for lookup of any existing or dependent
            CIM objects. If `None`, the default namespace of the connection is
            used.

        Raises:

          ValueError: Invalid input CIM object in `objects` parameter.
          TypeError: Invalid type in `objects` parameter.
          :exc:`~pywbem.CIMError`: CIM_ERR_INVALID_NAMESPACE: Namespace does
            not exist.
          :exc:`~pywbem.CIMError`: Failure related to the CIM objects in the
            mock repository.
        """  # noqa: E501
        # pylint: enable=line-too-long
        namespace = namespace or self.default_namespace
        self.mainprovider.validate_namespace(namespace)

        if isinstance(objects, list):
            for obj in objects:
                self.add_cimobjects(obj, namespace=namespace)

        else:
            obj = objects
            if isinstance(obj, CIMClass):
                cc = obj.copy()
                if cc.superclass:
                    if not self.mainprovider.class_exists(namespace,
                                                          cc.superclass):
                        raise ValueError(
                            _format("Class {0!A} defines superclass {1!A} but "
                                    "the superclass does not exist in the "
                                    "repository.",
                                    cc.classname, cc.superclass))
                class_store = self._get_class_store(namespace)

                qualifier_store = self._get_qualifier_store(namespace)

                # pylint: disable=protected-access
                cc1 = self.mainprovider._resolve_class(cc, namespace,
                                                       qualifier_store,
                                                       verbose=False)

                # TODO: ks. Originally this impled set whether exists or not
                # using create changes semantic to only add
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
                instance_store = self._get_instance_store(namespace)
                try:
                    # pylint: disable=protected-access
                    if self.mainprovider.find_instance(inst.path,
                                                       instance_store):
                        raise ValueError(
                            _format("The instance {0!A} already exists in "
                                    "namespace {1!A}", inst, namespace))
                except CIMError as ce:
                    raise CIMError(
                        CIM_ERR_FAILED,
                        _format("Internal failure of add_cimobject operation. "
                                "Rcvd CIMError {0}", ce))
                instance_store.create(inst.path, inst)

            elif isinstance(obj, CIMQualifierDeclaration):
                qual = obj.copy()
                qualifier_store = self._get_qualifier_store(namespace)
                qualifier_store.create(qual.name, qual)

            else:
                # Internal mocker error
                assert False, \
                    _format("Object to add_cimobjects. {0} invalid type",
                            type(obj))

    def add_method_callback(self, classname, methodname, method_callback,
                            namespace=None,):
        """
        Register a callback function for a CIM method that will be called when
        the CIM method is invoked via `InvokeMethod`.

        If the namespace does not exist, :exc:`~pywbem.CIMError` with status
        CIM_ERR_INVALID_NAMESPACE is raised.

        Parameters:

          classname (:term:`string`):
            The CIM class name for which the callback function is registered.

            The faked `InvokeMethod` implementation uses this information to
            look up the callback function from its parameters.

            For method invocations on a target instance, this must be the class
            name of the creation class of the target instance.

            For method invocations on a target class, this must be the class
            name of the target class.

          methodname (:term:`string`):
            The CIM method name for which the callback function is registered.

            The faked `InvokeMethod` implementation uses this information to
            look up the callback function from its parameters.

          method_callback (:func:`~pywbem_mock.method_callback_interface`):
            The callback function.

          namespace (:term:`string`):
            The CIM namespace for which the callback function is registered.

            If `None`, the callback function is registered for the default
            namespace of the connection.

            The faked `InvokeMethod` implementation uses this information to
            look up the callback function from its parameters.

        Raises:

          ValueError: Duplicate method specification.
          :exc:`~pywbem.CIMError`: CIM_ERR_INVALID_NAMESPACE: Namespace does
            not exist.
        """

        if namespace is None:
            namespace = self.default_namespace

        # Validate namespace
        method_repo = self._get_method_repo(namespace)

        # TODO: Future, when we add provider, this should move to provider
        # support
        if classname not in method_repo:
            method_repo[classname] = NocaseDict()

        if methodname in method_repo[classname]:
            raise ValueError("Duplicate method specification")

        method_repo[classname][methodname] = method_callback

    def display_repository(self, namespaces=None, dest=None, summary=False,
                           output_format='mof'):
        """
        Display the namespaces and objects in the mock repository in one of
        multiple formats to a destination.

        Parameters:

          namespaces (:term:`string` or list of :term:`string`):
            Limits display output to the specified CIM namespace or namespaces.
            If `None`, all namespaces of the mock repository are displayed.

          dest (:term:`string`):
            File path of an output file. If `None`, the output is written to
            stdout.

          summary (:class:`py:bool`):
            Flag for summary mode. If `True`, only a summary count of CIM
            objects in the specified namespaces of the mock repository is
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
                                  self._get_qualifier_store(ns),
                                  ns, cmt_begin, cmt_end, dest=dest,
                                  summary=summary, output_format=output_format)
            self._display_objects('Classes', self._get_class_store(ns), ns,
                                  cmt_begin, cmt_end, dest=dest,
                                  summary=summary, output_format=output_format)
            self._display_objects('Instances', self._get_instance_store(ns), ns,
                                  cmt_begin, cmt_end, dest=dest,
                                  summary=summary, output_format=output_format)
            self._display_objects('Methods', self._get_method_repo(ns), ns,
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

        # Issue #2062: TODO/ks FUTURE Consider sorting to preserve order of
        # compile/add. Make this part of refactor to separate repository and
        # datastore because it may be data store dependent
        if obj_type == 'Methods':
            _uprint(dest,
                    _format(u"{0}Namespace {1!A}: contains {2} {3}:{4}\n",
                            cmt_begin, namespace,
                            len(object_repo),
                            obj_type, cmt_end))
        else:
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

        elif obj_type == 'Methods':
            try:
                methods = object_repo
            except KeyError:
                return

            for cln in methods:
                for method in methods[cln]:
                    _uprint(dest,
                            _format(u"{0}Class: {1}, method: {2}, "
                                    u"callback: {3} {4}",
                                    cmt_begin, cln, method,
                                    methods[cln][method].__name__,
                                    cmt_end))

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

    def register_provider(self, namespaces, classnames, provider_type,
                          provider):
        # pylint: disable=line-too-long
        """
        Register the provider object for namespace and class. Registering a
        provider tells the FakedWBEMConnection that the provider implementation
        provided with this call is to be executed as the request response
        method for the namespace and class defined in lieu of the default
        provider.

        Providers can only be registered for request response methods
        CreateInstance and DeleteInstance and InvokeMethod.

        Multiple providers may be registered for the same classname in
        different namespaces

        Parameters:

          namespaces (:term:`string` or :class:`py:list` of :term:`string`):
            Namespace or namespaces for which the provider is being registered.
            At least one namespace is required.

          classnames (:term:`string` or :class:`py:list` of :term:`string`):
            Classname or classnames for which the provider is being
            registered. At least one classname is required.

          provider_type (:term:`string`):
            Keyword defining the type of request the provider will service.
            The allowed types are instance (keyword 'instance') which responds
            to the request responder methods defined in InstanceWriteProvider
            (ex. CreateInstance) and method (keyword 'method') which responds
            to the InvokeMethod.

          provider (subclass of :class::class:`pywbem_mock:InstanceWriteProvider`):
            The user provider class which is a subclass of
            :class:`pywbem_mock:InstanceWriteProvider`.  The methods in this
            subclass override the corresponding methods in
            InstanceWriteProvider. The method call parameters must be the
            same as the defult method in InstanceWriteProvider and it must
            return data in the same format if the default method returns data.
        """  # noqa: E501
        # pylint: enable=line-too-long

        provider_types = ('instance', 'method')

        if provider_type not in provider_types:
            raise ValueError("provider_type argument {0!A} "
                             "is not a valid provider type. "
                             "Valid provider types are {1!A}.", provider_type,
                             provider_types)

        if not issubclass(provider, InstanceWriteProvider):
            raise TypeError(
                _format("provider argument {0!A} is not a "
                        "valid subclass of InstanceWriteProvider. ",
                        provider))

        if classnames is None:
            raise ValueError(
                _format('classnames argument must be string '
                        'or list of strings. None not allowed.'))

        if namespaces is None:
            raise ValueError(
                _format('namespaces argument must be string '
                        'or list of strings. None not allowed.'))

            if not isinstance(namespaces, (list, tuple, six.string_types)):
                raise TypeError(
                    _format('Namespace argument {0|A} must be a string or '
                            'list/tuple but is {1}',
                            namespaces, type(namespaces)))

            if isinstance(namespaces, six.string_types):
                namespaces = [namespaces]

            for namespace in namespaces:
                if namespace not in self.namespaces:
                    raise ValueError(
                        _format('Namespace "{0!A}" in namespaces argument not '
                                'in CIM repository. '
                                'Existing namespaces are: {1!A}. ',
                                namespace, self.namespaces))

        # If classnames is list, recursively call this method
        if isinstance(classnames, (list, tuple)):
            for classname in classnames:
                self.register_provider(namespaces, classname, provider_type,
                                       provider)
            return

        # Processing for classnames defining a single classname
        classname = classnames
        assert isinstance(classname, six.string_types)

        if isinstance(namespaces, six.string_types):
            namespaces = [namespaces]
        for namespace in namespaces:
            if not self.mainprovider.class_exists(namespace, classname):
                raise ValueError(
                    _format('class "{0!A}" does not exist in '
                            'namespace {1!A} of the CIM repository',
                            classname, namespace))

        if classname not in self.provider_registry:
            self.provider_registry[classname] = NocaseDict()

        for namespace in namespaces:
            if namespace not in self.provider_registry[classname]:
                # add the provider_type dictionary
                self.provider_registry[classname][namespace] = {}
            self.provider_registry[classname][namespace][provider_type] = \
                provider

    ########################################################################
    #
    #   Pywbem functions mocked. WBEMConnection only mocks the WBEMConnection
    #   _imethodcall and _methodcall methods.  This captures all calls
    #   to the wbem server.
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
        # Create the local method name
        methodname = '_imeth_' + methodname
        methodnameattr = getattr(self, methodname)

        # Execute the named method
        result = methodnameattr(namespace, **params)

        # sleep for defined number of seconds
        if self._response_delay:
            time.sleep(self._response_delay)

        return result

    def _mock_methodcall(self, methodname, localobject, Params=None, **params):
        # pylint: disable=invalid-name
        """
        Mocks the WBEMConnection._methodcall() method. This calls the
        server execution function of extrinsic methods (InvokeMethod).
        """
        result = self._imeth_InvokeMethod(methodname, localobject,
                                          Params, **params)

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
    #####################################################################

    # Instance Operations

    def _imeth_EnumerateInstanceNames(self, namespace, **params):
        """
        Call :meth:`~pywbem_mock.MainProvider.EnumerateInstanceNames` with
        parameters defined for that method and map response to tuple response
        for imethodcall.

        Parameters:

          params (class:`py:dict`):
            Dictionary of parameters for the method called.

        Returns:

          Tuple with instance paths comatible with imethodcall

        Raises:

          Error: Exceptions from the call
        """
        instance_paths = self.mainprovider.EnumerateInstanceNames(
            ClassName=_cvt_rqd_classname(params['ClassName']),
            namespace=namespace)
        return self._make_tuple(instance_paths)

    def _imeth_EnumerateInstances(self, namespace, **params):
        """
        Call :meth:`~pywbem_mock.MainProvider.EnumerateInstances` with
        parameters defined for that method and map response to tuple response
        for imethodcall.

        Parameters:

          params (class:`py:dict`):
            Dictionary of parameters for the method called.

        Returns:

          Tuple with instances comatible with imethodcall

        Raises:

          Error: Exceptions from the call
        """
        instances = self.mainprovider.EnumerateInstances(
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

          params (class:`py:dict`):

            Dictionary of parameters for the method called.

        Returns:
          Tuple with instance comatible with imethodcall

        Raises:

          Error: Exceptions from the call
        """
        InstanceName = params['InstanceName']
        assert InstanceName.namespace is None
        InstanceName.namespace = namespace
        instance = self.mainprovider.GetInstance(
            InstanceName=InstanceName,
            LocalOnly=params.get('LocalOnly', None),
            IncludeQualifiers=params.get('IncludeQualifiers', None),
            IncludeClassOrigin=params.get('IncludeClassOrigin', None),
            PropertyList=params.get('PropertyList', None))
        return self._make_tuple([instance])

    def _imeth_CreateInstance(self, namespace, **params):
        """
        Call :meth:`~pywbem_mock.MainProvider.CreateInstance` with
        parameters defined for that method and map response to tuple response
        for imethodcall.

        This method allows user providers and therefore is passed to the
        :class:`ProviderDispatcher`.

        Parameters:

          params (class:`py:dict`):
            Dictionary of parameters for the method called.

        Raises:

          Error: Exceptions from the call
        """
        new_instance_path = self.providerdispatcher.CreateInstance(
            namespace=namespace,
            NewInstance=params['NewInstance'])
        return self._make_tuple([new_instance_path])

    def _imeth_ModifyInstance(self, namespace, **params):
        """
        Call :meth:`~pywbem_mock.MainProvider.ModifyInstance` with
        parameters defined for that method and map response to tuple response
        for imethodcall.

        The method called includes the namespace within the ModifiedInstance
        rather than as a separate element.

        This method allows user providers and therefore is passed to the
        :class:`ProviderDispatcher`.

        Parameters:

          params (class:`py:dict`):
            Dictionary of parameters for the method called.

        Raises:

          Error: Exceptions from the call
        """

        ModifiedInstance = params['ModifiedInstance']
        assert ModifiedInstance.path.namespace is None
        ModifiedInstance.path.namespace = namespace

        self.providerdispatcher.ModifyInstance(
            ModifiedInstance=ModifiedInstance,
            IncludeQualifiers=params.get('IncludeQualifiers', None),
            PropertyList=params.get('PropertyList', None))

    def _imeth_DeleteInstance(self, namespace, **params):
        """
        Call :meth:`~pywbem_mock.MainProvider.DeleteInstance` with
        parameters defined for that method and map response to tuple response
        for imethodcall.

        The method called includes the namespace within the InstanceName
        rather than as a separate element.

        This method allows user providers and therefore is passed to the
        :class:`ProviderDispatcher`.

        Parameters:

          params (class:`py:dict`):
            Dictionary of parameters for the method called.

        Raises:

          Error: Exceptions from the call
        """
        InstanceName = params['InstanceName']
        assert InstanceName.namespace is None
        InstanceName.namespace = namespace

        self.providerdispatcher.DeleteInstance(
            InstanceName=InstanceName)

    def ExecQuery(self, namespace, **params):
        """
        Call :meth:`~pywbem_mock.MainProvider.ExecQuery` with
        parameters defined for that method and map response to tuple response
        for imethodcall.

        Parameters:

          params (class:`py:dict`):
            Dictionary of parameters for the method called.

        Returns:

          Tuple with instances compatible with imethodcall

        Raises:

          Error: Exceptions from the call
        """
        instances = self.mainprovider.ExecQuery(
            namespace=namespace,
            QueryLanguage=params['QueryLanguage'],
            Query=params['Query'])
        # TODO: The following is untested because the
        # mainprovider ExecQuery only generates exception.
        return self._make_tuple([instances])

    # CIMClass operations

    def _imeth_EnumerateClasses(self, namespace, **params):
        """
        Call :meth:`~pywbem_mock.MainProvider.EnumerateClasses` with
        parameters defined for that method and map response to tuple response
        for imethodcall.
        """
        classes = self.mainprovider.EnumerateClasses(
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
        classnames = self.mainprovider.EnumerateClassNames(
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
        klass = self.mainprovider.GetClass(
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
        self.mainprovider.CreateClass(
            namespace,
            NewClass=params['NewClass'])

    def _imeth_ModifyClass(self, namespace, **params):
        """
        Call :meth:`~pywbem_mock.MainProvider.ModifyClass` with
        parameters defined for that method and map response to tuple response
        for imethodcall.
        """
        self.mainprovider.ModifyClass(
            namespace,
            ModifiedClass=params['ModifiedClass'])

    def _imeth_DeleteClass(self, namespace, **params):
        """
        Call :meth:`~pywbem_mock.MainProvider.DeleteClass` with
        parameters defined for that method and map response to tuple response
        for imethodcall.
        """
        self.mainprovider.DeleteClass(
            namespace,
            ClassName=_cvt_rqd_classname(params['ClassName']))

    # Qualifier declaration operations

    def _imeth_EnumerateQualifiers(self, namespace, **params):
        """
        Call :meth:`~pywbem_mock.MainProvider.EnumerateQualifiers` with
        parameters defined for that method and map response to tuple response
        for imethodcall.
        """
        qualifiers = self.mainprovider.EnumerateQualifiers(
            namespace=namespace)
        return self._make_tuple(qualifiers)

    def _imeth_GetQualifier(self, namespace, **params):
        """
        Call :meth:`~pywbem_mock.MainProvider.GetQualifier` with
        parameters defined for that method and map response to tuple response
        for imethodcall.
        """
        qualifier = self.mainprovider.GetQualifier(
            namespace=namespace,
            QualifierName=params['QualifierName'])
        return self._make_tuple([qualifier])

    def _imeth_DeleteQualifier(self, namespace, **params):
        """
        Call :meth:`~pywbem_mock.MainProvider.DeleteQualifier` with
        parameters defined for that method and map response to tuple response
        for imethodcall.
        """
        self.mainprovider.DeleteQualifier(
            namespace=namespace,
            QualifierName=params['QualifierName'])

    def _imeth_SetQualifier(self, namespace, **params):
        """
        Call :meth:`~pywbem_mock.MainProvider.SetQualifier` with
        parameters defined for that method and map response to tuple response
        for imethodcall.
        """
        self.mainprovider.SetQualifier(
            namespace=namespace,
            QualifierDeclaration=params['QualifierDeclaration'])

    # Associator and Reference operations

    def _imeth_ReferenceNames(self, namespace, **params):
        """
        Call :meth:`~pywbem_mock.MainProvider.ReferenceNames` with
        parameters defined for that method and map response to tuple response
        for imethodcall.,
        """
        object_names = self.mainprovider.ReferenceNames(
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
        objects = self.mainprovider.References(
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
        object_names = self.mainprovider.AssociatorNames(
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
        objects = self.mainprovider.Associators(
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
        context_tuple = self.mainprovider.OpenEnumerateInstancePaths(
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

        context_tuple = self.mainprovider.OpenEnumerateInstances(
            namespace=namespace,
            ClassName=_cvt_rqd_classname(params['ClassName']),
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
        context_tuple = self.mainprovider.OpenReferenceInstancePaths(
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
        context_tuple = self.mainprovider.OpenReferenceInstances(
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
        context_tuple = self.mainprovider.OpenAssociatorInstances(
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
        context_tuple = self.mainprovider.OpenAssociatorInstancePaths(
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
        context_tuple = self.mainprovider.OpenQueryInstances(
            namespace=namespace,
            FilterQueryLanguage=params.get('FilterQueryLanguage', None),
            FilterQuery=params.get('FilterQuery', None),
            ReturnQueryResultClass=params.get('FilterQueryLanguage', None),
            OperationTimeout=params.get('OperationTimeout', None),
            ContinueOnError=params.get('ContinueOnError', None),
            MaxObjectCount=params.get('MaxObjectCount', None))
        return self._make_pull_imethod_resp(*context_tuple)

    def _imeth_PullInstancePaths(self, namespace, **params):
        """
        Call :meth:`~pywbem_mock.MainProvider.PullInstancePaths` with
        parameters defined for that method and map response to tuple response
        for imethodcall.
        """
        context_tuple = self.mainprovider.PullInstancePaths(
            EnumerationContext=params['EnumerationContext'],
            MaxObjectCount=params['MaxObjectCount'])
        return self._make_pull_imethod_resp(*context_tuple)

    def _imeth_PullInstancesWithPath(self, namespace, **params):
        """
        Call :meth:`~pywbem_mock.MainProvider.PullInstancesWithPath` with
        parameters defined for that method and map response to tuple response
        for imethodcall.
        """
        context_tuple = self.mainprovider.PullInstancesWithPath(
            EnumerationContext=params['EnumerationContext'],
            MaxObjectCount=params['MaxObjectCount'])
        return self._make_pull_imethod_resp(*context_tuple)

    def _imeth_PullInstances(self, namespace, **params):
        """
        Call :meth:`~pywbem_mock.MainProvider.PullInstances` with
        parameters defined for that method and map response to tuple response
        for imethodcall.
        """
        context_tuple = self.mainprovider.PullInstances(
            EnumerationContext=params['EnumerationContext'],
            MaxObjectCount=params['MaxObjectCount'])
        return self._make_pull_imethod_resp(*context_tuple)

    def _imeth_CloseEnumeration(self, namespace, **params):
        """
        Call :meth:`~pywbem_mock.MainProvider.CloseEnumeration` with
        parameters defined for that method. Returns nothing
        """
        self.mainprovider.CloseEnumeration(
            EnumerationContext=params['EnumerationContext'])

    ####################################################################
    #
    #   Server responder for InvokeMethod.
    #
    ####################################################################

    def _imeth_InvokeMethod(self, methodname, objectname, Params, **params):
        # pylint: disable=invalid-name
        """
        Implements a mock WBEM server responder for
        :meth:`~pywbem.WBEMConnection.InvokeMethod`

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
              Its `host` attribute will be ignored.

            * For class-level use: The class path of the target class, as a
              :term:`string` or :class:`~pywbem.CIMClassName` object:

              If specified as a string, the string is interpreted as a class
              name in the default namespace of the connection
              (case independent).

              If specified as a :class:`~pywbem.CIMClassName` object, its `host`
              attribute will be ignored. If this object does not specify
              a namespace, the default namespace of the connection is used.

          Params (:term:`py:iterable`):
            An iterable of input parameter values for the CIM method. Each item
            in the iterable is a single parameter value and can be any of:

            * :class:`~pywbem.CIMParameter` representing a parameter value. The
              `name`, `value`, `type` and `embedded_object` attributes of this
              object are used.

            * tuple of name, value, with:

                - name (:term:`string`): Parameter name (case independent)
                - value (:term:`CIM data type`): Parameter value

          **params :
            Each keyword parameter is an additional input parameter value for
            the CIM method, with:

            * key (:term:`string`): Parameter name (case independent)
            * value (:term:`CIM data type`): Parameter value

        Returns:

            A :func:`py:tuple` of (returnvalue, outparams), with these
            tuple items:

            * returnvalue (:term:`CIM data type`):
              Return value of the CIM method.
            * outparams (:ref:`NocaseDict`):
              Dictionary with all provided output parameters of the CIM method,
              with:

              * key (:term:`unicode string`):
                Parameter name, preserving its lexical case
              * value (:term:`CIM data type`):
                Parameter value
        """

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
                _format("InvokeMethod of method {0!A} on object {1!A}: "
                        "Objectname argument has incorrect Python type {2} "
                        "- expected one of pywbem.CIMInstanceName, "
                        "pywbem.CIMClassName, or string",
                        methodname, objectname, type(objectname)))

        namespace = localobject.namespace

        # Validate namespace
        method_repo = self._get_method_repo(namespace)

        # Find the methods entry corresponding to classname. It must be in
        # the class defined by classname or one of its superclasses that
        # includes this method. Since the classes in the repo are not
        # resolved

        # This raises CIM_ERR_NOT_FOUND or CIM_ERR_INVALID_NAMESPACE
        # Uses local_only = False to get characteristics from super classes
        # and include_class_origin to get origin of method in hiearchy
        cc = self.mainprovider.get_class(namespace, localobject.classname,
                                         local_only=False,
                                         include_qualifiers=True,
                                         include_classorigin=True)

        # Determine if method defined in classname defined in
        # the classorigin of the method
        try:
            target_cln = cc.methods[methodname].class_origin
        except KeyError:
            raise CIMError(
                CIM_ERR_METHOD_NOT_FOUND,
                _format("Method {0!A} not found in class {1!A}.",
                        methodname, localobject.classname))
        if target_cln != cc.classname:
            # Issue #2062: add method to repo that allows privileged users
            # direct access so we don't have to go through _get_class and can
            # test classes directly in repo
            tcc = self.mainprovider.get_class(namespace, target_cln,
                                              local_only=False,
                                              include_qualifiers=True,
                                              include_classorigin=True)
            if methodname not in tcc.methods:
                raise CIMError(
                    CIM_ERR_METHOD_NOT_FOUND,
                    _format("Method {0!A} not found in origin class {1!A} "
                            "derived from objectname class {2!A}",
                            methodname, target_cln, localobject.classname))

        # Test for target class in methods repo
        try:
            methods = method_repo[target_cln]
        except KeyError:
            raise CIMError(
                CIM_ERR_METHOD_NOT_FOUND,
                _format("Class {0!A} for method {1!A} in namespace {2!A} not "
                        "registered in methods repository",
                        localobject.classname, methodname, namespace))

        # Test for method in local class.
        try:
            cc.methods[methodname]
        except KeyError:
            raise CIMError(
                CIM_ERR_METHOD_NOT_FOUND,
                _format("Method {0!A} not found in methods repository for "
                        "class {1!A}", methodname, localobject.classname))

        try:
            bound_method = methods[methodname]
        except KeyError:
            raise CIMError(
                CIM_ERR_METHOD_NOT_FOUND,
                _format("Method {0!A} in namespace {1!A} not registered in "
                        "methods repository. Internal error",
                        methodname, namespace))

        if bound_method is None:
            raise CIMError(
                CIM_ERR_METHOD_NOT_FOUND,
                _format("Class {0!A} for method {1!A} in registered in "
                        "methods repository namespace {2!A}",
                        localobject.classname, methodname, namespace))

        # Map the Params and **params into a single no-case dictionary
        # of CIMParameters
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
            for param in params:
                params_dict[param] = CIMParameter(param,
                                                  cimtype(param[param]),
                                                  value=param[param])

        # Call the registered method and catch exceptions.
        try:
            result = bound_method(self, methodname, localobject, **params_dict)

        except CIMError:
            raise

        except Exception:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            tb = traceback.format_exception(exc_type, exc_value, exc_traceback)
            method_code = bound_method.func_code
            raise CIMError(
                CIM_ERR_FAILED,
                _format("Error in implementation of mocked method {0!A} of "
                        "class {1!A} (File {2} line {3}): "
                        "Unhandled Python exception:\n"
                        "{4}",
                        methodname, localobject.classname,
                        method_code.co_filename, method_code.co_firstlineno,
                        "\n".join(tb)))

        # test for valid data in response.
        if not isinstance(result, (list, tuple)):
            method_code = bound_method.func_code
            raise CIMError(
                CIM_ERR_FAILED,
                _format("Error in implementation of mocked method {0!A} of "
                        "class {1!A} (File {2} line {3}): "
                        "Object returned by mock function has incorrect type "
                        "{4} - expected list/tuple (CIM value, list/tuple "
                        "(pywbem.CIMParameter))",
                        methodname, localobject.classname,
                        method_code.co_filename, method_code.co_firstlineno,
                        type(result)))
        for param in result[1]:
            if not isinstance(param, CIMParameter):
                method_code = bound_method.func_code
                raise CIMError(
                    CIM_ERR_FAILED,
                    _format("Error in implementation of mocked method {0!A} "
                            "of class {1!A} (File {2} line {3}): "
                            "Output parameter has incorrect type {4} "
                            "- expected pywbem.CIMParameter",
                            methodname, localobject.classname,
                            method_code.co_filename, method_code.co_firstlineno,
                            type(param)))

        # Map output params to NocaseDict to be compatible with return
        # from _methodcall. The input list is just CIMParameters
        output_params = NocaseDict()
        for param in result[1]:
            output_params[param.name] = param.value

        return (result[0], output_params)
