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

from copy import deepcopy
import uuid
import time
import sys

import traceback
import re
from xml.dom import minidom
from collections import Counter
from mock import Mock
import six

# pylint: disable=ungrouped-imports
try:
    # time.perf_counter() was added in Python 3.3
    from time import perf_counter as delta_time
except ImportError:
    # time.clock() was deprecated in Python 3.3
    from time import clock as delta_time
# pylint: enable=ungrouped-imports

from pywbem import WBEMConnection, CIMClass, CIMClassName, \
    CIMInstance, CIMInstanceName, CIMQualifierDeclaration, \
    CIMParameter, cimtype, CIMError, \
    CIM_ERR_NOT_FOUND, CIM_ERR_METHOD_NOT_FOUND, CIM_ERR_FAILED, \
    CIM_ERR_INVALID_PARAMETER, CIM_ERR_NAMESPACE_NOT_EMPTY, \
    CIM_ERR_INVALID_CLASS, CIM_ERR_ALREADY_EXISTS, \
    CIM_ERR_INVALID_NAMESPACE, CIM_ERR_INVALID_ENUMERATION_CONTEXT, \
    CIM_ERR_NOT_SUPPORTED, CIM_ERR_QUERY_LANGUAGE_NOT_SUPPORTED, \
    DEFAULT_NAMESPACE, MOFCompiler
from pywbem._nocasedict import NocaseDict
from pywbem._utils import _format

from ._inmemoryrepository import InMemoryRepository

from ._mockmofwbemconnection import _MockMOFWBEMConnection

from ._dmtf_cim_schema import DMTFCIMSchema
from ._resolvermixin import ResolverMixin
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


class FakedWBEMConnection(WBEMConnection, ResolverMixin):
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
                 timeout=None, response_delay=None):
        """
        Parameters:

          default_namespace (:term:`string`):
            Default namespace.
            This parameter has the same characteristics as the same-named init
            parameter of :class:`~pywbem.WBEMConnection`.

          use_pull_operations (:class:`py:bool`):
            Flag to control whether pull or traditional operaitons are
            used in the iter operations.
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
        """
        # Response delay in seconds. Any operation is delayed by this time.
        # Initialize before superclass init because otherwise logger may
        # fail with this attribute not found
        self._response_delay = response_delay

        super(FakedWBEMConnection, self).__init__(
            'http://FakedUrl:5988',
            default_namespace=default_namespace,
            use_pull_operations=use_pull_operations,
            stats_enabled=stats_enabled, timeout=timeout)

        # Implementation of the CIM object repository that is the data store
        # for CIM classes, CIM instances, CIM qualifier declarations and
        # CIM methods for the mocker.  All access to the mocker CIM data must
        # pass through this variable to the datastore.
        self.repo = InMemoryRepository(self.default_namespace)

        # Defines the connection for the compiler.  The compiler uses
        # its local repo for work but sends new objects back to the
        # methods in this class
        self._mofwbemconnection = _MockMOFWBEMConnection(self)

        # The CIM methods with callback in the mock repository.
        # This is a dictionary of dictionaries of dictionaries, where the top
        # level key is the CIM namespace name, the second level key is the
        # CIM class name, and the third level key is the CIM method name.
        # The values at the last level are (TBD: method callbacks?).
        # The namespaces are added to the outer dictionary as needed (if
        # permitted as per self.namesaces).
        # TODO: This must move to provider when provider is defined
        self.methods = NocaseDict()

        # Open Pull Contexts. The key for each context is an enumeration
        # context id.  The data is the total list of instances/names to
        # be returned and the current position in the list. Any context in
        # this list is still open.
        self.enumeration_contexts = {}

        self._imethodcall = Mock(side_effect=self._mock_imethodcall)
        self._methodcall = Mock(side_effect=self._mock_methodcall)

        # Current namespace.  Set by the mock calls it is used by the
        # request methods to determine the current namespace.  This is used
        # because namespace is NOT part of the WBEMConnection calls.
        #
        self.namespace = None

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
            "super={super})",
            s=self, super=super(FakedWBEMConnection, self).__repr__())

    ################################################################
    #
    #   Methods to manage namespaces
    #
    ################################################################

    def validate_namespace(self, namespace):
        """
        Validates that a namespace is defined in the repository.

          Parameters:

            namespace (:term:`string`):
              The name of the CIM namespace in the mock repository. Must not be
              `None`.

          Returns:
             True if the namespace is defined

          Raises:

          :exc:`~pywbem.CIMError`: CIM_ERR_INVALID_NAMESPACE: Namespace does
            not exist.
        """
        try:
            self.repo.validate_namespace(namespace)
        except KeyError:
            raise CIMError(
                CIM_ERR_INVALID_NAMESPACE,
                _format("Namespace does not exist in mock repository: {0!A}",
                        namespace))

    def add_namespace(self, namespace):
        """
        Add a CIM namespace to the mock repository.

        The namespace must not yet exist in the mock repository.

        The default connection namespace is automatically added to
        the mock repository upon creation of this connection.

        Parameters:

          namespace (:term:`string`):
            The name of the CIM namespace in the mock repository. Must not be
            `None`. Leading and trailing slash characters are split off
            from the provided string.

        Raises:

          ValueError: Namespace argument must not be None.
          :exc:`~pywbem.CIMError`: CIM_ERR_ALREADY_EXISTS if the namespace
            already exists in the mock repository.
        """

        if namespace is None:
            raise ValueError("Namespace argument must not be None")

        try:
            self.repo.add_namespace(namespace)
        except ValueError:
            raise CIMError(
                CIM_ERR_ALREADY_EXISTS,
                _format("Namespace {0!A} already exists in the mock "
                        "repository", namespace))

    def _remove_namespace(self, namespace):
        """
        Remove a CIM namespace from the mock repository.

        The namespace must exist in the mock repository and must be empty.

        The default connection namespace cannot be removed.

        Parameters:

          namespace (:term:`string`):
            The name of the CIM namespace in the mock repository. Must not be
            `None`. Any leading and trailing slash characters are split off
            from the provided string.

        Raises:

          ValueError: Namespace argument must not be None
          :exc:`~pywbem.CIMError`:  CIM_ERR_NOT_FOUND if the namespace does
            not exist in the mock repository.
          :exc:`~pywbem.CIMError`:  CIM_ERR_NAMESPACE_NOT_EMPTY if the
            namespace is not empty.
          :exc:`~pywbem.CIMError`:  CIM_ERR_NAMESPACE_NOT_EMPTY if attempting
            to delete the default connection namespace.  This namespace cannot
            be deleted from the mock repository
        """
        if namespace is None:
            raise ValueError("Namespace argument must not be None")

        if namespace == self.default_namespace:
            raise CIMError(
                CIM_ERR_NAMESPACE_NOT_EMPTY,
                _format("Connection default namespace {0!A} cannot be "
                        "deleted from mock repository", namespace))
        try:
            self.repo.remove_namespace(namespace)
        except KeyError:
            raise CIMError(
                CIM_ERR_NOT_FOUND,
                _format("Namespace {0!A} does not exist in the mock "
                        "repository", namespace))
        except ValueError:
            raise CIMError(
                CIM_ERR_NAMESPACE_NOT_EMPTY,
                _format("Namespace {0!A} contains objects.", namespace))

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
        self.validate_namespace(namespace)

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

        self.validate_namespace(namespace)

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
        self.validate_namespace(namespace)

        if isinstance(objects, list):
            for obj in objects:
                self.add_cimobjects(obj, namespace=namespace)

        else:
            obj = objects
            if isinstance(obj, CIMClass):
                cc = obj.copy()
                if cc.superclass:
                    if not self._class_exists(cc.superclass, namespace):
                        raise ValueError(
                            _format("Class {0!A} defines superclass {1!A} but "
                                    "the superclass does not exist in the "
                                    "repository.",
                                    cc.classname, cc.superclass))
                class_store = self._get_class_store(namespace)

                qualifier_store = self._get_qualifier_store(namespace)

                cc1 = self._resolve_class(cc, namespace, qualifier_store,
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
                    if self._find_instance(inst.path, instance_store):
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
            File-like object(ex. file_path, or other data stream definition )
            for the output. If `None`, the output is written to stdout.

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

        # get all namespaces
        repo_ns = sorted(self.repo.namespaces)

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
            names = [n for n in object_repo.iter_names()]
            if names:
                for name in sorted(names):
                    obj = object_repo.get(name)
                    if output_format == 'xml':
                        _uprint(dest, _pretty_xml(obj.tocimxmlstr()))
                    elif output_format == 'repr':
                        _uprint(dest, _format(u"{0!A}", obj))
                    else:
                        _uprint(dest, obj.tomof())

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

        Each function is named with the method name prepended with
        '_fake_'.
        """
        self.namespace = namespace
        method_name = '_fake_' + methodname

        method_name = getattr(self, method_name)

        result = method_name(**params)

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
        result = self._fake_invokemethod(methodname, localobject, Params,
                                         **params)

        # Sleep for defined number of seconds
        if self._response_delay:
            time.sleep(self._response_delay)

        return result

    #####################################################################
    #
    #     Common methods that the Fake... WBEMConnection methods use to
    #     to communicate with the Mock repository. These are generally
    #     private methods.
    #
    #####################################################################

    def _class_exists(self, classname, namespace):
        """
        Test if class defined by classname parameter exists in
        repository defined by namespace parameter.

        Returns `True` if class exists and `False` if it does not exist.

        Exception if the namespace does not exist
        """
        class_store = self._get_class_store(namespace)
        return class_store.exists(classname)

    @staticmethod
    def _make_tuple(rtn_value):
        """
        Change the return value from the value consistent with the definition
        in cim_operations.py into a tuple in accord with _imethodcall
        """
        return [("IRETURNVALUE", {}, rtn_value)]

    @staticmethod
    def _remove_qualifiers(obj):
        """
        Remove all qualifiers from the input objectwhere the object may
        be an CIMInstance or CIMClass. Removes qualifiers from the object and
        from properties, methods, and parameters

        This is used to process the IncludeQualifier parameter for classes
        and instances
        """
        assert isinstance(obj, (CIMInstance, CIMClass))
        obj.qualifiers = NocaseDict()
        for prop in obj.properties:
            obj.properties[prop].qualifiers = NocaseDict()
        if isinstance(obj, CIMClass):
            for method in obj.methods:
                obj.methods[method].qualifiers = NocaseDict()
                for param in obj.methods[method].parameters:
                    obj.methods[method].parameters[param].qualifiers = \
                        NocaseDict()

    @staticmethod
    def _remove_classorigin(obj):
        """
        Remove all ClassOrigin attributes from the input object. The object
        may be a CIMInstance or CIMClass.

        Used to process the IncludeClassOrigin parameter of requests
        """
        assert isinstance(obj, (CIMInstance, CIMClass))
        for prop in obj.properties:
            obj.properties[prop].class_origin = None
        if isinstance(obj, CIMClass):
            for method in obj.methods:
                obj.methods[method].class_origin = None

    def _get_superclass_names(self, cln, class_store):
        """
        Get list of superclasses names from the class repository for the
        defined classname (cln) in the namespace.

        Returns:
         List of classnames in order of descending class hierarchy or an
         empty list if cln is None
        """

        superclass_names = []
        if cln is not None:
            cln_work = cln
            while cln_work:
                # Accesses class in repository. Note, no copy made
                cln_superclass = class_store.get(cln_work).superclass
                if cln_superclass:
                    superclass_names.append(cln_superclass)
                cln_work = cln_superclass
            superclass_names.reverse()
        return superclass_names

    def _get_subclass_names(self, classname, class_store, deep_inheritance):
        """
            Get class names that are subclasses of the
            classname input parameter from the repository.

            If DeepInheritance is False, get only classes in the
            repository for the defined namespace for which this class is a
            direct super class.

            If deep_inheritance is `True`, get all direct and indirect
            subclasses.  If false, get only a the next level of the
            hiearchy.

        Returns:
            list of strings with the names of all subclasses of `classname`.

        """

        assert classname is None or isinstance(classname, (six.string_types,
                                                           CIMClassName))

        if isinstance(classname, CIMClassName):
            classname = classname.classname

        if classname is None:
            rtn_classnames = [
                c.classname for c in class_store.iter_values()
                if c.superclass is None]
        else:
            rtn_classnames = [
                c.classname for c in class_store.iter_values()
                if c.superclass and c.superclass.lower() == classname.lower()]

        # Recurse for next level of class hiearchy
        if deep_inheritance:
            subclass_names = []
            if rtn_classnames:
                for cln in rtn_classnames:
                    subclass_names.extend(
                        self._get_subclass_names(cln, class_store,
                                                 deep_inheritance))
            rtn_classnames.extend(subclass_names)
        return rtn_classnames

    def _exists_class(self, classname, namespace):
        """
        Test if the class defined by classname exists in the namespace

        Parameters:

          classname (:term:`string`):
            Name of class to retrieve

          namespace (:term:`string`):
            Namespace from which to retrieve the class

        Returns:

            True if exists. False if does not exist

        """
        class_store = self._get_class_store(namespace)
        return class_store.exists(classname)

    def _get_class(self, classname, namespace, local_only=None,
                   include_qualifiers=None, include_classorigin=None,
                   property_list=None):
        # pylint: disable=invalid-name
        """
        Get class from repository.  Gets the class defined by classname
        from the repository, creates a copy, expands the copied class to
        include superclass properties if not localonly, and filters the
        class based on propertylist and includeClassOrigin.

        It also sets the propagated attribute.

        Parameters:

          classname (:term:`string`):
            Name of class to retrieve

          namespace (:term:`string`):
            Namespace from which to retrieve the class

          local_only (:class:`py:bool`):
            If `True`, only properties and methods in this specific class are
            returned. Otherwise properties and methods from the superclasses
            are included.

          include_qualifiers (:class:`py:bool`):
            If `True`, include qualifiers. Otherwise remove all qualifiers

          include_classorigin (:class:`py:bool`):
            If `True` return the class_origin attributes of properties and
            methods.

          property_list ():
            Properties to be included in returned class.  If None, all
            properties are returned.  If empty, no properties are returned

        Returns:

            Copy of the class if found with superclass properties installed and
            filtered per the keywords in params.

        Raises:
            CIMError: (CIM_ERR_NOT_FOUND) if class Not found in repository or
            CIMError: (CIM_ERR_INVALID_NAMESPACE) if namespace does not exist
        """

        class_store = self._get_class_store(namespace)

        # Try to get the target class and create a copy for response
        try:
            cls = class_store.get(classname)
        except KeyError:
            raise CIMError(
                CIM_ERR_NOT_FOUND,
                _format("Class {0!A} not found in namespace {1!A}.",
                        classname, namespace))

        # TODO/ks: changing this to cls.copy() causes failures with
        # class qualifiers not created.
        cc = deepcopy(cls)

        if local_only:
            for prop, pvalue in cc.properties.items():
                if pvalue.propagated:
                    del cc.properties[prop]
            for method, mvalue in cc.methods.items():
                if mvalue.propagated:
                    del cc.methods[method]

        self._filter_properties(cc, property_list)

        if not include_qualifiers:
            self._remove_qualifiers(cc)

        if not include_classorigin:
            self._remove_classorigin(cc)
        return cc

    def _iter_association_classes(self, namespace):
        """
        Return iterator of association classes from the class repo

        Returns the classes that have associations qualifier.
        Does NOT copy so these are what is in repository. User functions
        MUST NOT modify these classes.

        Returns: Returns generator where each yield returns a single
                 association class
        """

        class_store = self._get_class_store(namespace)
        for cl in class_store.iter_values():
            if 'Association' in cl.qualifiers:
                yield cl
        return

    @staticmethod
    def _find_instance(iname, instance_store, copy_inst=None):
        """
        Find an instance in the instance repo by iname and return the
        index of that instance.

        Parameters:

          iname: CIMInstancename to find

          instance_store: the instance repo to search

          copy_inst: boolean.
            If True do deep copy of the instance and return the copy. Otherwise
            return the instance in the repository

        Return (None, None if not found. Otherwise return instance or
        copy of instance

        Raises:

          CIMError: Failed if repo invalid.
        """

        if instance_store.exists(iname):
            if copy_inst:
                return instance_store.get(iname).copy()
            return instance_store.get(iname)

        return None

    def _get_instance(self, iname, namespace, instance_store, property_list,
                      local_only, include_class_origin, include_qualifiers):
        """
        Local method implements getinstance. This is generally used by
        other instance methods that need to get an instance from the
        repository.

        It attempts to get the instance, copies it, and filters it
        for input parameters of local_only, include_qualifiers,
        include_class_origin, and propertylist.

        Parameters:

            iname (:class:`~pywbem.CIMInstanceName`)
                The instance name of the instance to be retrieved.

            namespace (:term:`string`)
                Namespace containing the instance. This is used only for
                explanatory data in exceptions

            instance_store:
                Validated instance repository for the current namespace

            property_list: (:term:`string` or :term:`py:iterable` of :term:`string`)  # noqa: E501

            local_only:(:class:`pybool`)
                If True only properties with classorigin same as classname
                are returned.
            include_class_origin:(:class:`pybool`)
                If True, class_origin included in returned object.

            include_qualifiers:(:class:`pybool`)
                If True, any qualifiers in the stored instance the instance and
                properties are returned
                NOTE: This is deprecated so generally has no effect.

        Returns:

          CIMInstance copy from the repository with property_list filtered,
          and qualifers removed if include_qualifiers=False and
          class origin removed if include_class_origin False

        Raises:
            CIMError: (CIM_ERR_NOT_FOUND) if the or its class instance do not
            exist in the repository
        """

        rtn_inst = self._find_instance(iname, instance_store, copy_inst=True)

        if rtn_inst is None:
            raise CIMError(
                CIM_ERR_NOT_FOUND,
                _format("Instance not found in repository namespace {0!A}. "
                        "Path={1!A}", namespace, iname))

        # If local_only remove properties where class_origin
        # differs from class of target instance
        if local_only:
            for p in rtn_inst:
                class_origin = rtn_inst.properties[p].class_origin
                if class_origin and class_origin != rtn_inst.classname:
                    del rtn_inst[p]

        if local_only:
            # gets class propertylist which may be local only or all
            # superclasses
            try:
                cl = self._get_class(iname.classname, namespace,
                                     local_only=local_only)
            except CIMError as ce:
                if ce.status_code == CIM_ERR_NOT_FOUND:
                    raise CIMError(
                        CIM_ERR_INVALID_CLASS,
                        _format("Class {0!A} not found for instance {1!A} in "
                                "namespace {2!A}.",
                                iname.classname, iname, namespace))

            class_pl = cl.properties.keys()

            for p in list(rtn_inst):
                if p not in class_pl:
                    del rtn_inst[p]

        self._filter_properties(rtn_inst, property_list)

        if not include_qualifiers:
            self._remove_qualifiers(rtn_inst)

        if not include_class_origin:
            self._remove_classorigin(rtn_inst)
        return rtn_inst

    def _get_subclass_list_for_enums(self, classname, namespace, class_store):
        """
        Get class list (i.e names of subclasses for classname for the
        enumerateinstance methods in a case-insenstive dictionary. The input
        classname is included in this dictionary.

        Returns:
           NocaseDict where only the keys are important, This allows case
           insensitive matches of the names with Python "for cln in clns".

        Raises:

            CIMError: (CIM_ERR_INVALID_CLASS) if classname not in repository
        """

        if not class_store.exists(classname):
            raise CIMError(
                CIM_ERR_INVALID_CLASS,
                _format("Class {0!A} not found in namespace {1!A}.",
                        classname, namespace))

        clnslist = self._get_subclass_names(classname, class_store, True)
        clnsdict = NocaseDict()
        for cln in clnslist:
            clnsdict[cln] = cln

        clnsdict[classname] = classname
        return clnsdict

    @staticmethod
    def _filter_properties(obj, property_list):
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

    ###############################################################
    #
    #   Access  to instance data repository
    #
    #   The following methods provide access to the instance repo for
    #   a single namespace. They should be the basis for access to the
    #   instance repo until we convert to using a class that cleanly provides
    #   access to the repo.
    #
    ##################################################################

    def _get_class_store(self, namespace):
        """
        Returns the class data storefor the specified CIM namespace
        within the mock repository. This is the original instance variable,
        so any modifications will change the mock repository.

        Validates that the namespace exists in the mock repository.

        If the class repository does not contain the namespace yet, it is
        added.

        Parameters:

          namespace(:term:`string`): Namespace name. Must not be `None`.

        Returns:

          Case independent dictionary where each entry is:
            <classname> :CIMClass

        Raises:

          :exc:`~pywbem.CIMError`: CIM_ERR_INVALID_NAMESPACE: Namespace does
            not exist.
        """
        self.validate_namespace(namespace)
        return self.repo.get_class_store(namespace)

    def _get_instance_store(self, namespace):
        """
        Returns the instance data store for the specified CIM namespace
        within the mock repository.

        Validates that the namespace exists in the mock repository.

        If the instance repository does not contain the namespace yet, it is
        added.

        Parameters:

          namespace(:term:`string`): Namespace name. Must not be `None`.

        Returns:

          Dictionary of instances where each dictionary entry is:
              <CIMInstanceName> : CIMInstance

        Raises:

          :exc:`~pywbem.CIMError`: CIM_ERR_INVALID_NAMESPACE: Namespace does
            not exist.
        """

        self.validate_namespace(namespace)
        return self.repo.get_instance_store(namespace)

    def _get_qualifier_store(self, namespace):
        """
        Returns the qualifier data store for the specified CIM namespace
        within the mock repository. This is the original instance variable,
        so any modifications will change the mock repository.

        Validates that the namespace exists in the mock repository.

        If the qualifier repository does not contain the namespace yet, it is
        added.

        Parameters:

          namespace(:term:`string`): Namespace name. Must not be `None`.

        Returns:

          No case dictionary of <qualifier_name>: CIMQualifierDeclaration
          entries.


        Raises:

          :exc:`~pywbem.CIMError`: CIM_ERR_INVALID_NAMESPACE: Namespace does
            not exist.
        """

        self.validate_namespace(namespace)
        return self.repo.get_qualifier_store(namespace)

    def _get_method_repo(self, namespace=None):
        """
        Returns the method repository for the specified CIM namespace
        within the mock repository. This is the original instance variable,
        so any modifications will change the mock repository.

        Validates that the namespace exists in the mock repository.

        If the method repository does not contain the namespace yet, it is
        added.

        Parameters:

          namespace(:term:`string`): Namespace name. Must not be `None`.

        Returns:

          No case dictionary where each entry is
            <method name>: <Callable method>

        Raises:

          :exc:`~pywbem.CIMError`: CIM_ERR_INVALID_NAMESPACE: Namespace does
            not exist.
        """
        self.validate_namespace(namespace)
        if namespace not in self.methods:
            self.methods[namespace] = NocaseDict()
        return self.methods[namespace]

    #####################################################################
    #
    #   Faked WBEMConnection operation methods.
    #   All the methods are named _fake_<methodname> and
    #   are responders that emulate the server response.
    #
    #   This is all the WBEMConnection methods that communicate with
    #   a WBEMServer.
    #
    #   The API for these calls differes from the methods in _WBEMConnection
    #   in that every call API includes the namespace as a positional
    #   in all of the calls including those where _WBEMConnection does not
    #   include the naespace. This is logical in that the server
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

    def _fake_EnumerateClasses(self, **params):
        """
        Implements a mock server responder for
        :meth:`~pywbem.WBEMConnection.EnumerateClasses`.

        Enumerate classes from class repository. If classname parameter
        exists, use it as the starting point for the hiearchy to get subclasses.

        Returns:

            return tuple including list of classes

        Raises:

            CIMError: CIM_ERR_INVALID_NAMESPACE: invalid namespace,
            CIMError: CIM_ERR_NOT_FOUND: A class that should be a subclass
            of either the root or "ClassName" parameter was not found in the
            repository. This is probably a repository build error.
            CIMError: CIM_ERR_INVALID_CLASS: class defined by the classname
            parameter does not exist.
        """
        namespace = self.namespace
        # Validate namespace and get class_store for this namespace
        class_store = self._get_class_store(namespace)

        classname = params.get('ClassName', None)
        if classname:
            assert(isinstance(classname, CIMClassName))
            if not class_store.exists(classname.classname):
                raise CIMError(
                    CIM_ERR_INVALID_CLASS,
                    _format("The class {0!A} defined by 'ClassName' parameter "
                            "does not exist in namespace {1!A}",
                            classname, namespace))

        clns = self._get_subclass_names(classname, class_store,
                                        params['DeepInheritance'])

        classes = [
            self._get_class(cn, namespace,
                            local_only=params['LocalOnly'],
                            include_qualifiers=params['IncludeQualifiers'],
                            include_classorigin=params['IncludeClassOrigin'])
            for cn in clns]

        return self._make_tuple(classes)

    def _fake_EnumerateClassNames(self, **params):
        """
        Implements a mock server responder for
        :meth:`~pywbem.WBEMConnection.EnumerateClassNames`.

        Enumerates the classnames of the classname in the 'classname' parameter
        or from the top of the tree if 'classname is None.

        Returns:

            return tuple including list of classnames

        Raises:

            CIMError: CIM_ERR_INVALID_NAMESPACE: invalid namespace,
            CIMError: CIM_ERR_INVALID_CLASS: class defined by the classname
            parameter does not exist
        """
        namespace = self.namespace

        # Validate namespace and get class_store for this namespace
        class_store = self._get_class_store(namespace)

        classname = params.get('ClassName', None)
        if classname:
            assert(isinstance(classname, CIMClassName))
            if not class_store.exists(classname.classname):
                raise CIMError(
                    CIM_ERR_INVALID_CLASS,
                    _format("The class {0!A} defined by 'ClassName' parameter "
                            "does not exist in namespace {1!A}",
                            classname, namespace))

        clns = self._get_subclass_names(classname, class_store,
                                        params['DeepInheritance'])
        rtn_clns = [
            CIMClassName(cn, namespace=namespace, host=self.host)
            for cn in clns]

        return self._make_tuple(rtn_clns)

    def _fake_GetClass(self, **params):
        """
        Implements a mock server responder for
        :meth:`~pywbem.WBEMConnection.GetClass

        Retrieve a CIM class from the local repository.

        For a description of the parameters, see
        :meth:`pywbem.WBEMConnection.GetClass`.
        """
        namespace = self.namespace

        self.validate_namespace(namespace)

        cname = params['ClassName'].classname

        cc = self._get_class(cname, namespace, local_only=params['LocalOnly'],
                             include_qualifiers=params['IncludeQualifiers'],
                             include_classorigin=params['IncludeClassOrigin'],
                             property_list=params['PropertyList'])

        return self._make_tuple([cc])

    def _fake_CreateClass(self, **params):
        """
        Implements a mock server responder for
        :meth:`~pywbem.WBEMConnection.CreateClass`

        Creates a new class in the repository.  Nothing is returned.
        Emulates WBEMConnection.CreateClass(...))

        If the class repository for this namespace does not
        exist, this method creates it.

        Classes that are in the repository contain only the properties in
        the new_class, not any properties from inheritated classes.  The
        corresponding _get_class resolves any inherited properties to create
        a complete class with both local and inherited properties.

        Raises:
            CIMError: CIM_ERR_INVALID_SUPERCLASS if superclass specified bu
              does not exist

            CIMError: CIM_ERR_INVALID_PARAMETER if NewClass parameter not a
              class

            CIMError: CIM_ERR_ALREADY_EXISTS if class already exists
        """
        namespace = self.namespace
        # Validate parameters
        new_class = params['NewClass']
        if not isinstance(new_class, CIMClass):
            raise CIMError(
                CIM_ERR_INVALID_PARAMETER,
                _format("NewClass not valid CIMClass. Rcvd type={0}",
                        type(new_class)))

        # Validate namespace and get the class datastore for this namespace
        class_store = self._get_class_store(namespace)

        if class_store.exists(new_class.classname):
            raise CIMError(
                CIM_ERR_ALREADY_EXISTS,
                _format("Class {0!A} already exists in namespace {1!A}.",
                        new_class.classname, namespace))

        new_class = new_class.copy()

        qualifier_store = self._get_qualifier_store(namespace)
        self._resolve_class(new_class, namespace, qualifier_store,
                            verbose=False)

        # add mew class to repository
        class_store.create(new_class.classname, new_class)

    def _fake_ModifyClass(self, **params):
        # pylint: disable=unused-argument
        """
        Currently not implemented
        Implements a mock server responder for
        :meth:`~pywbem.WBEMConnection.MmodifyClass`

        Modifies a new class in the repository.  Nothing is returned.
        Emulates WBEMConnection.CreateClass(...))

        if the class repository for this namespace does not
        exist, this method creates it.

        Raises:

            CIMError: CIM_ERR_NOT_SUPPORTED
        """
        namespace = self.namespace

        self.validate_namespace(namespace)

        raise CIMError(
            CIM_ERR_NOT_SUPPORTED,
            "Currently ModifyClass not supported in Fake_WBEMConnection")

    def _fake_DeleteClass(self, **params):
        """
        Implements a mock server responder for
        :meth:`~pywbem.WBEMConnection.DeleteClass`

        Delete a class in the class repository if it exists.
        Emulates WBEMConnection.DeleteClass(...))

        This is simplistic in that it ignores issues like existing
        subclasses and existence of instances.

        Nothing is returned.

        Raises:

            CIMError: CIM_ERR_NOT_FOUND if ClassName defines class not in
                repository
        """

        namespace = self.namespace

        # Validate namespace and get the class datastore for this namespace
        class_store = self._get_class_store(namespace)
        instance_store = self._get_instance_store(namespace)

        cname = params['ClassName'].classname

        if not class_store.exists(cname):
            raise CIMError(
                CIM_ERR_NOT_FOUND,
                _format("Class {0!A} in namespace {1!A} not in repository. "
                        "Nothing deleted.", cname, namespace))

        classnames = self._get_subclass_names(cname, class_store, True)
        classnames.append(cname)

        # Delete all instances in this class and subclasses and delete
        # this class and subclasses
        for clname in classnames:
            clns = self._get_subclass_list_for_enums(cname, namespace,
                                                     class_store)

            inst_paths = [inst.path for inst in instance_store.iter_values()
                          if inst.path.classname in clns]

            for iname in inst_paths:
                self.DeleteInstance(iname)

            class_store.delete(clname)

    ##########################################################
    #
    #              Faked Qualifier methods
    #
    ###########################################################

    def _fake_EnumerateQualifiers(self, **params):
        # pylint: disable=unused-argument
        """
        Imlements a mock server responder for
        :meth:`~pywbem.WBEMConnection.EnumerateQualifiers`

        Enumerates the qualifier declarations in the local repository of this
        namespace.
        """

        namespace = self.namespace
        # Validate namespace and get qualifier_store for this namespace
        qualifier_store = self._get_qualifier_store(namespace)

        # pylint: disable=unnecessary-comprehension
        qualifiers = [q for q in qualifier_store.iter_values()]

        return self._make_tuple(qualifiers)

    def _fake_GetQualifier(self, **params):
        """
        Implements a server responder for
        :meth:`pywbem.WBEMConnection.GetQualifier`.

        Retrieves a qualifier declaration from the local repository of this
        namespace.

        Returns:

          Returns a tuple representing the _imethodcall return for this
          method where the data is a QualifierDeclaration

        Raises:
            CIMError: CIM_ERR_INVALID_NAMESPACE

            CIMError: CIM_ERR_NOT_FOUND
        """

        namespace = self.namespace
        # Validate namespace and get qualifier_store for this namespace
        qualifier_store = self._get_qualifier_store(namespace)

        qname = params['QualifierName']

        try:
            qualifier = qualifier_store.get(qname)
        except KeyError:
            ce = CIMError(
                CIM_ERR_NOT_FOUND,
                _format("Qualifier declaration {0!A} not found in namespace "
                        "{1!A}.", qname, namespace))
            raise ce

        return self._make_tuple([qualifier])

    def _fake_SetQualifier(self, **params):
        """
        Implements a server responder for
        :meth:`pywbem.WBEMConnection.SetQualifier`.

        Create or modify a qualifier declaration in the local repository of this
        class.  This method will create a new namespace for the qualifier
        if none is defined.

        Raises:

            CIMError: CIM_ERR_INVALID_PARAMETER
            CIMError: CIM_ERR_ALREADY_EXISTS
        """

        namespace = self.namespace
        # Issue #2062 ks Refactor to separate data store from repository method

        # Validate namespace and get the qualifier data store for this namespace
        qualifier_store = self._get_qualifier_store(namespace)

        qual_decl = params['QualifierDeclaration']
        if not isinstance(qual_decl, CIMQualifierDeclaration):
            raise CIMError(
                CIM_ERR_INVALID_PARAMETER,
                _format("QualifierDeclaration parameter is not a valid "
                        "valid CIMQualifierDeclaration. Rcvd type={0}",
                        type(qual_decl)))

        try:
            qualifier_store.create(qual_decl.name, qual_decl)
        except ValueError:
            raise CIMError(
                CIM_ERR_ALREADY_EXISTS,
                _format("Qualifier declaration {0!A} already exists in "
                        "namespace {1!A}.", qual_decl.name, namespace))

    def _fake_DeleteQualifier(self, **params):
        """
        Implements a server responder for
        :meth:`~pywbem.WBEMConnection.DeleteQualifier`

        Deletes a single qualifier if it is in the
        repository for this class and namespace

        Raises;

            CIMError: CIM_ERR_INVALID_NAMESPACE, CIM_ERR_NOT_FOUND
        """

        namespace = self.namespace
        # Validate namespace and get the qualifier data store for this namespace
        qualifier_store = self._get_qualifier_store(namespace)

        qname = params['QualifierName']

        if qualifier_store.exists(qname):
            qualifier_store.delete(qname)
        else:
            raise CIMError(
                CIM_ERR_NOT_FOUND,
                _format("QualifierDeclaration {0!A} not found in namespace "
                        "{1!A}.", qname, namespace))

    #####################################################################
    #
    #  Faked WBEMConnection Instance methods
    #
    #####################################################################

    def _fake_CreateInstance(self, **params):
        """
        Implements a server responder for
        :meth:`~pywbem.WBEMConnection.CreateInstance`

        Create a CIM instance in the local repository of this class.

        Always use the namespace parameter assuming that
        pywbem.CreateInstance has captured any namespace in the instance
        path component.

        Raisess:

            CIMError: CIM_ERR_ALREADY_EXISTS

            CIMError: CIM_ERR_INVALID_CLASS
        """

        namespace = self.namespace
        # Validate parameters
        new_instance = params['NewInstance']
        if not isinstance(new_instance, CIMInstance):
            raise CIMError(
                CIM_ERR_INVALID_PARAMETER,
                _format("NewInstance parameter is not a valid CIMInstance. "
                        "Rcvd type={0}", type(new_instance)))

        # Validate namespace
        instance_store = self._get_instance_store(namespace)

        # Requires corresponding class to build path to be returned
        try:
            target_class = self._get_class(new_instance.classname,
                                           namespace,
                                           local_only=False,
                                           include_qualifiers=True,
                                           include_classorigin=True)
        except CIMError as ce:
            if ce.status_code != CIM_ERR_NOT_FOUND:
                raise

            raise CIMError(
                CIM_ERR_INVALID_CLASS,
                _format("Cannot create instance because its creation "
                        "class {0!A} does not exist in namespace {1!A}.",
                        new_instance.classname, namespace))

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
            # TODO: We should not have to normalize here, that is lower level
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

        # Test all key properties in instance. Mocker repository
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
        for iprop_name in new_instance:
            if iprop_name not in target_class.properties:
                raise CIMError(
                    CIM_ERR_INVALID_PARAMETER,
                    _format("Property {0!A} specified in NewInstance is not "
                            "exposed by class {1!A} in namespace {2!A}",
                            iprop_name, target_class.classname, namespace))

            cprop = target_class.properties[iprop_name]
            iprop = new_instance.properties[iprop_name]
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
                new_instance.properties[iprop_name].name = cprop_name

        # If property not in instance, add it from class and use default value
        # from class
        for cprop_name in target_class.properties:
            if cprop_name not in new_instance:
                default_value = target_class.properties[cprop_name]
                new_instance[cprop_name] = default_value

        # Build instance path. We build the complete instance path
        new_instance.path = CIMInstanceName.from_instance(
            target_class,
            new_instance,
            namespace=namespace)

        # Check for duplicate instances
        if instance_store.exists(new_instance.path):
            raise CIMError(
                CIM_ERR_ALREADY_EXISTS,
                _format("NewInstance {0!A} already exists in namespace "
                        "{1!A}.", new_instance.path, namespace))

        # Reflect the new namespace in the mock repository
        if ns_classname:
            self.add_namespace(new_namespace)

        # Store the new instance in the mock repository
        instance_store.create(new_instance.path, new_instance)

        # Create instance returns model path, path relative to namespace
        # TODO: Change to use copy
        return self._make_tuple([deepcopy(new_instance.path)])

    def _fake_ModifyInstance(self, **params):
        """
        Implements a server responder for
        :meth:`~pywbem.WBEMConnection.CreateInstance`

        Modify a CIM instance in the local repository.

        Raises:

            CIMError: CIM_ERR_ALREADY_EXISTS, CIM_ERR_INVALID_CLASS
        """

        namespace = self.namespace
        # Validate namespace and get instance data store
        instance_store = self._get_instance_store(namespace)

        modified_instance = deepcopy(params['ModifiedInstance'])
        property_list = params['PropertyList']

        # Return if empty property list, nothing would be changed
        if property_list is not None and not property_list:
            return

        if not isinstance(modified_instance, CIMInstance):
            raise CIMError(
                CIM_ERR_INVALID_PARAMETER,
                _format("The ModifiedInstance parameter is not a valid "
                        "CIMInstance. Rcvd type={0}", type(modified_instance)))

        # Classnames in instance and path must match
        if modified_instance.classname.lower() != \
                modified_instance.path.classname.lower():
            raise CIMError(
                CIM_ERR_INVALID_PARAMETER,
                _format("ModifyInstance classname in path and instance do "
                        "not match. classname={0!A}, path.classname={1!A}",
                        modified_instance.classname,
                        modified_instance.path.classname))

        # Get class including properties from superclasses from repo
        try:
            target_class = self.GetClass(modified_instance.classname,
                                         namespace=namespace,
                                         LocalOnly=False,
                                         IncludeQualifiers=True,
                                         IncludeClassOrigin=True)
        except CIMError as ce:
            if ce.status_code == CIM_ERR_NOT_FOUND:
                raise CIMError(
                    CIM_ERR_INVALID_CLASS,
                    _format("Cannot modify instance because its creation "
                            "class {0!A} does not exist in namespace {1!A}.",
                            modified_instance.classname, namespace))
            raise

        # Get original instance in repo.
        if modified_instance.path.namespace is None:
            modified_instance.path.namespace = namespace

        orig_instance = self._find_instance(modified_instance.path,
                                            instance_store,
                                            copy_inst=True)
        if orig_instance is None:
            raise CIMError(
                CIM_ERR_NOT_FOUND,
                _format("Original Instance {0!A} not found in namespace {1!A}",
                        modified_instance.path, namespace))

        # Remove duplicate properties from property_list
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

            cprop = target_class.properties[pname]
            iprop = modified_instance.properties[pname]
            if iprop.is_array != cprop.is_array \
                    or iprop.type != cprop.type \
                    or iprop.array_size != cprop.array_size:
                raise CIMError(
                    CIM_ERR_INVALID_PARAMETER,
                    _format("Instance and class property name={0!A} type "
                            "or other attributes do not match: "
                            "instance={1!A}, class={2!A}",
                            pname, iprop, cprop))
            # If case of modified_instance property != case of class property
            # change the name in the modified_instance
            if iprop.name != cprop.name:
                modified_instance.properties[iprop.name].name = cprop.name

        # Modify the value of properties in the repo with those from
        # modified instance inserted into the original instance
        orig_instance.update(modified_instance.properties)
        instance_store.update(modified_instance.path, orig_instance)

        return

    def _fake_GetInstance(self, **params):
        """
        Implements a mock server responder for
        :meth:`~pywbem.WBEMConnection.GetInstance`.

        Gets a single instance from the repository based on the
        InstanceName and filters it for PropertyList, etc.

        This method uses a common repository access method _get_instance to
        get, copy, and process the instance.

        Raises:

            CIMError:  CIM_ERR_INVALID_NAMESPACE, CIM_ERR_INVALID_PARAMETER
              CIM_ERR_NOT_FOUND
        """

        namespace = self.namespace
        iname = params['InstanceName']
        if iname.namespace is None:
            iname.namespace = namespace
        assert iname.namespace == namespace

        instance_store = self._get_instance_store(namespace)

        if not self._class_exists(iname.classname, namespace):
            raise CIMError(
                CIM_ERR_INVALID_CLASS,
                _format("Class {0!A} for GetInstance of instance {1!A} "
                        "does not exist.", iname.classname, iname))

        inst = self._get_instance(iname, namespace, instance_store,
                                  params['PropertyList'],
                                  params['LocalOnly'],
                                  params['IncludeClassOrigin'],
                                  params['IncludeQualifiers'])

        return self._make_tuple([inst])

    def _fake_DeleteInstance(self, **params):
        """
        Implements a mock server responder for
        :meth:`~pywbem.WBEMConnection.DeleteInstance`.

        This deletes a single instance from the mock repository based on the
        iname and namespace parameters.

        It does not attempt to delete referenceing instances (associations,
        etc. that reference this instance.)

        If the creation class of the instance to be deleted is PG_Namespace or
        CIM_Namespace, then the namespace identified by the 'Name' property
        of the instance is being deleted in the mock repository in addition to
        the CIM instance. The default connection namespace of this faked
        commection cannot be deleted.
        """

        namespace = self.namespace
        iname = params['InstanceName']
        # assumes namespace input parameter is authoritive namespace name
        iname.namespace = namespace

        # Validate namespace and get instance datastore
        instance_store = self._get_instance_store(namespace)

        if not self._class_exists(iname.classname, namespace):
            raise CIMError(
                CIM_ERR_INVALID_CLASS,
                _format("Class {0!A} in namespace {1!A} not found. "
                        "Cannot delete instance {2!A}",
                        iname.classname, namespace, iname))

        if not instance_store.exists(iname):
            raise CIMError(
                CIM_ERR_NOT_FOUND,
                _format("Instance {0!A} not found in repository namespace "
                        "{1!A}", iname, namespace))

        # Handle namespace deletion, currently hard coded.
        # Issue #2062 TODO/AM 8/18 Generalize the hard coded handling into
        # provider concept
        classname_lower = iname.classname.lower()
        if classname_lower == 'pg_namespace':
            ns_classname = 'PG_Namespace'
        elif classname_lower == 'cim_namespace':
            ns_classname = 'CIM_Namespace'
        else:
            ns_classname = None
        if ns_classname:
            namespace = iname.keybindings['Name']

            # Reflect the namespace deletion in the mock repository
            # This will check the namespace for being empty.
            self._remove_namespace(namespace)

        # Delete the instance from the repository
        instance_store.delete(iname)

    def _fake_EnumerateInstances(self, **params):
        """
        Implements a server responder for
        :meth:`~pywbem.WBEMConnection.EnumerateInstances`.

        Gets a list of subclasses if the classes exist in the repository
        then executes getInstance for each to create the list of instances
        to be returned.

        Raises:

            CIMError: CIM_ERR_INVALID_NAMESPACE
        """

        namespace = self.namespace
        # Validate namespace
        instance_store = self._get_instance_store(namespace)

        class_store = self._get_class_store(namespace)

        cname = params['ClassName']
        assert isinstance(cname, CIMClassName)
        cname = cname.classname

        # If di False we use only properties from the original class. Modify
        # property list to limit properties to those from this class.  This
        # only works if class exists.
        # if class not in repository, ignore di.
        di = params['DeepInheritance']

        # If None, set to server default
        if di is None:
            di = DEFAULT_DEEP_INHERITANCE

        pl = params['PropertyList']
        lo = params.get('LocalOnly', None)
        ico = params['IncludeClassOrigin']
        iq = params.get('IncludeQualifiers', None)

        # gets class propertylist which is may be localonly or all
        # superclasses
        cl = self._get_class(cname, namespace, local_only=lo)
        class_pl = cl.properties.keys()

        # If not di, compute property list to filter
        # all instances to the properties in the target class as modified
        # by the PropertyList
        if not di:
            if pl is None:  # properties in class form property list
                pl = class_pl
            else:      # reduce pl to properties in class_properties
                pl_lower = [pc.lower() for pc in pl]
                pl = [pc for pc in class_pl if pc.lower() in pl_lower]

        clns_dict = self._get_subclass_list_for_enums(cname, namespace,
                                                      class_store)

        insts = [self._get_instance(inst.path, namespace, instance_store, pl,
                                    None,  # LocalOnly never gets passed
                                    ico, iq)
                 for inst in instance_store.iter_values()
                 if inst.path.classname in clns_dict]

        return self._make_tuple(insts)

    def _fake_EnumerateInstanceNames(self, **params):
        """
        Implements a server responder for
        :meth:`~pywbem.WBEMConnection.EnumerateInstanceNames`

        Get instance names for instances that match the path define
        by `ClassName` and returns a list of the names.
        """

        namespace = self.namespace
        cname = params['ClassName']
        assert isinstance(cname, CIMClassName)
        cname = cname.classname

        # Validate namespace and get instance datastore for this namespace
        instance_store = self._get_instance_store(namespace)
        class_store = self._get_class_store(namespace)

        clns = self._get_subclass_list_for_enums(cname, namespace, class_store)

        inst_paths = [inst.path for inst in instance_store.iter_values()
                      if inst.path.classname in clns]

        rtn_paths = [path.copy() for path in inst_paths]

        return self._make_tuple(rtn_paths)

    def _fake_ExecQuery(self, **params):
        # pylint: disable=unused-argument
        """
        Implements a mock WBEM server responder for
            :meth:`~pywbem.WBEMConnection.ExecQuery`

        Executes the equilavent of the WBEMConnection ExecQuery for
        the querylanguage and query defined
        """

        namespace = self.namespace
        self.validate_namespace(namespace)

        raise CIMError(
            CIM_ERR_NOT_SUPPORTED,
            "ExecQuery not implemented!")

    #####################################################################
    #
    #  Faked WBEMConnection Reference and Associator methods
    #
    #####################################################################

    def _validate_class_exists(self, cln, namespace, req_param="TargetClass"):
        """
        Common test for the references and associators to test for the
        existence of the class named cln  in namespace.

        Returns if the class exists.

        If the class does not exist, executes an INVALID_PARAMETER
        exception which is the specified exception for invalid classes for
        the TargetClass, AssocClass, and ResultClass for reference and
        associator operations
        """
        if not self._exists_class(cln, namespace):
            raise CIMError(
                CIM_ERR_INVALID_PARAMETER,
                _format('Class {0!A} {1} parameter not found in namespace '
                        '{2!A}.', cln, req_param, namespace))

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

    def _return_assoc_class_tuples(self, rtn_classnames, namespace, iq, ico,
                                   pl):
        """
        Creates the correct tuples of for associator and references class
        level responses from a list of classnames.  This is special because
        the class level references and associators return a tuple of
        CIMClassName and CIMClass for every entry.
        """

        rtn_tups = []
        for cn in rtn_classnames:
            rtn_tups.append((CIMClassName(cn, namespace=namespace,
                                          host=self.host),
                             self._get_class(cn,
                                             namespace=namespace,
                                             include_qualifiers=iq,
                                             include_classorigin=ico,
                                             property_list=pl)))
        return self._return_assoc_tuple(rtn_tups)

    def _subclasses_lc(self, classname, class_store):
        """
        Return a list of this class and it subclasses in lower case.
        Exception of class is not in repository.
        """
        if not classname:
            return []
        clns = [classname]
        clns.extend(self._get_subclass_names(classname, class_store, True))
        return [cln.lower() for cln in clns]

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

    def _get_reference_classnames(self, classname, namespace, class_store,
                                  result_class, role):
        """
        Get list of classnames that are references for which this classname
        is a target filtered by the result_class and role parameters if they
        are none.
        This is a common method used by all of the other reference and
        associator methods to create a list of reference classnames

        Returns:
            list of classnames that satisfy the criteria.
        """

        class_store = self._get_class_store(namespace)
        self._validate_class_exists(classname, namespace, "TargetClass")

        if result_class:
            self._validate_class_exists(result_class, namespace,
                                        "ResultClass")

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

    def _get_reference_instnames(self, instname, namespace, class_store,
                                 result_class, role):
        """
        Get the reference instances from the repository for the target
        instname and filtered by the result_class and role parameters.

        Returns a list of the reference instance names. The returned list is
        the original, not a copy so the user must copy them
        """

        instance_store = self._get_instance_store(namespace)

        if not class_store.exists(instname.classname):
            raise CIMError(
                CIM_ERR_INVALID_PARAMETER,
                _format("Class {0!A} not found in namespace {1!A}.",
                        instname.classname, namespace))

        # Get list of class and subclasses in lower case
        if result_class:
            self._validate_class_exists(result_class, namespace,
                                        "ResultClass")
        resultclasses = self._subclasses_lc(result_class, class_store)

        instname.namespace = namespace
        role = role.lower() if role else None

        # Future TODO/ks: Search very wide here.  Not isolating to associations
        # and not limiting to expected result_classes. Consider making list from
        # get_reference_classnames if classes exist, otherwise set list to
        # instance_store to search all instances

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

    def _get_associated_classnames(self, classname, namespace, assoc_class,
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
        class_store = self._get_class_store(namespace)
        if assoc_class:
            self._validate_class_exists(assoc_class, namespace, "AssocClass")

        if result_class:
            self._validate_class_exists(result_class, namespace, "ResultClass")

        # Get list of subclasses for result and assoc classes (lower case)
        result_classes = self._subclasses_lc(result_class, class_store)
        assoc_classes = self._subclasses_lc(assoc_class, class_store)

        rtn_classnames_set = set()

        role = role.lower() if role else role
        result_role = result_role.lower() if result_role else result_role

        ref_clns = self._get_reference_classnames(classname, namespace,
                                                  class_store, assoc_class,
                                                  role)

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

    def _get_associated_instancenames(self, inst_name, namespace, assoc_class,
                                      result_class, result_role, role):
        """
        Get the reference instances from the repository for the target
        instname and filtered by the result_class and role parameters.

        Returns a list of the reference instance names. The returned list is
        the original, not a copy so the user must copy them
        """

        instance_store = self._get_instance_store(namespace)
        class_store = self._get_class_store(namespace)

        if assoc_class:
            self._validate_class_exists(assoc_class, namespace, "AssocClass")

        if result_class:
            self._validate_class_exists(result_class, namespace, "ResultClass")

        result_classes = self._subclasses_lc(result_class, class_store)
        assoc_classes = self._subclasses_lc(assoc_class, class_store)

        inst_name.namespace = namespace
        role = role.lower() if role else role
        result_role = result_role.lower() if result_role else result_role

        ref_paths = self._get_reference_instnames(inst_name, namespace,
                                                  class_store,
                                                  assoc_class, role)

        # Get associated instance names
        rtn_instpaths = set()
        for ref_path in ref_paths:
            inst = self._find_instance(ref_path, instance_store)
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

    def _fake_ReferenceNames(self, **params):
        """
        Implements a mock WBEM server responder for
        :meth:`~pywbem.WBEMConnection.ReferenceNames`
        """

        namespace = self.namespace
        self.validate_namespace(namespace)
        class_store = self._get_class_store(namespace)

        assert params['ResultClass'] is None or \
            isinstance(params['ResultClass'], CIMClassName)

        rc = None if params['ResultClass'] is None else \
            params['ResultClass'].classname
        role = params['Role']
        obj_name = params['ObjectName']
        classname = obj_name.classname

        if isinstance(obj_name, CIMClassName):
            ref_classnames = self._get_reference_classnames(classname,
                                                            namespace,
                                                            class_store,
                                                            rc, role)

            ref_result = [CIMClassName(classname=cn, host=self.host,
                                       namespace=namespace)
                          for cn in ref_classnames]

            return self._return_assoc_tuple(ref_result)

        assert isinstance(obj_name, CIMInstanceName)
        ref_paths = self._get_reference_instnames(obj_name, namespace,
                                                  class_store,
                                                  rc, role)
        rtn_names = [r.copy() for r in ref_paths]

        for iname in rtn_names:
            if iname.host is None:
                iname.host = self.host

        return self._return_assoc_tuple(rtn_names)

    def _fake_References(self, **params):
        """
        Implements a mock WBEM server responder for
        :meth:`~pywbem.WBEMConnection.References`
        """

        namespace = self.namespace
        # validate namespace and get class_storesitory for this namespace
        class_store = self._get_class_store(namespace)

        rc = None if params['ResultClass'] is None else \
            params['ResultClass'].classname
        role = params['Role']
        obj_name = params['ObjectName']
        classname = obj_name.classname
        pl = params['PropertyList']
        ico = params['IncludeClassOrigin']
        iq = params.get('IncludeQualifiers', None)

        if isinstance(obj_name, CIMClassName):
            rtn_classnames = self._get_reference_classnames(
                classname, namespace, class_store, rc, role)
            # returns list of tuples of (CIMClassname, CIMClass)
            return self._return_assoc_class_tuples(rtn_classnames, namespace,
                                                   iq, ico, pl)

        # This is an  instance reference
        instance_store = self._get_instance_store(namespace)
        assert isinstance(obj_name, CIMInstanceName)
        ref_paths = self._get_reference_instnames(obj_name, namespace,
                                                  class_store, rc,
                                                  role)

        rtn_insts = [self._get_instance(p, namespace, instance_store, None,
                                        pl, ico, iq)
                     for p in ref_paths]

        for inst in rtn_insts:
            if inst.path.host is None:
                inst.path.host = self.host

        return self._return_assoc_tuple(rtn_insts)

    def _fake_AssociatorNames(self, **params):
        # pylint: disable=invalid-name
        """
        Implements a mock WBEM server responder for
        :meth:`~pywbem.WBEMConnection.AssociatorNames`
        """

        namespace = self.namespace
        self.validate_namespace(namespace)

        rc = None if params['ResultClass'] is None else \
            params['ResultClass'].classname
        ac = None if params['AssocClass'] is None else \
            params['AssocClass'].classname
        role = params['Role']
        result_role = params['ResultRole']
        obj_name = params['ObjectName']
        classname = obj_name.classname

        if isinstance(obj_name, CIMClassName):
            rtn_classnames = self._get_associated_classnames(classname,
                                                             namespace,
                                                             ac, rc,
                                                             result_role, role)

            assoc_result = [CIMClassName(classname=cn, host=self.host,
                                         namespace=namespace)
                            for cn in rtn_classnames]

            return self._return_assoc_tuple(assoc_result)

        assert isinstance(obj_name, CIMInstanceName)
        rtn_paths = self._get_associated_instancenames(obj_name,
                                                       namespace,
                                                       ac, rc,
                                                       result_role, role)
        results = [p.copy() for p in rtn_paths]

        for iname in results:
            if iname.host is None:
                iname.host = self.host

        return self._return_assoc_tuple(results)

    def _fake_Associators(self, **params):
        """
        Implements a mock WBEM server responder for
            :meth:`~pywbem.WBEMConnection.Associators`
        """

        namespace = self.namespace
        self.validate_namespace(namespace)

        rc = None if params['ResultClass'] is None else \
            params['ResultClass'].classname
        ac = None if params['AssocClass'] is None else \
            params['AssocClass'].classname
        role = params['Role']
        result_role = params['ResultRole']
        obj_name = params['ObjectName']
        classname = obj_name.classname
        pl = params['PropertyList']
        ico = params['IncludeClassOrigin']
        iq = params.get('IncludeQualifiers', None)

        if isinstance(obj_name, CIMClassName):
            rtn_classnames = self._get_associated_classnames(classname,
                                                             namespace,
                                                             ac, rc,
                                                             result_role, role)
            # returns list of tuples of (CIMClassname, CIMClass)
            return self._return_assoc_class_tuples(rtn_classnames, namespace,
                                                   iq, ico, pl)

        # Processing for instancename
        instance_store = self._get_instance_store(namespace)
        assert isinstance(obj_name, CIMInstanceName)
        assoc_names = self._get_associated_instancenames(obj_name,
                                                         namespace,
                                                         ac, rc,
                                                         result_role, role)
        results = []
        for obj_name in assoc_names:
            results.append(self._get_instance(
                obj_name, namespace, instance_store, None,
                pl, ico, iq))

        return self._return_assoc_tuple(results)

    #####################################################################
    #
    #  Faked WBEMConnection Open and Pull Instances Methods
    #
    #  All of the following methods take the simplistic approach of getting
    #  all of the data from the original functions and saving it
    #  in the contexts dictionary.
    #  We could improve performance by using an iterator to get the data
    #  but are taking the simple approach since this is a mock tool.
    #
    #####################################################################

    @staticmethod
    def _create_contextid():
        """Return a new uuid for an enumeration context"""
        return str(uuid.uuid4())

    @staticmethod
    def _make_pull_imethod_resp(objs, eos, context_id):
        """
        Create the correct imethod response for the open and pull methods
        """
        eos_tup = (u'EndOfSequence', None, eos)
        enum_ctxt_tup = (u'EnumerationContext', None, context_id)

        return [("IRETURNVALUE", {}, objs), enum_ctxt_tup, eos_tup]

    def _open_response(self, objects, namespace, pull_type, **params):
        """
        Build an open... response once the objects have been extracted from
        the repository.
        """
        max_obj_cnt = params['MaxObjectCount']
        if max_obj_cnt is None:
            max_obj_cnt = _DEFAULT_MAX_OBJECT_COUNT

        default_server_timeout = 40
        timeout = default_server_timeout if params['OperationTimeout'] is None \
            else params['OperationTimeout']

        if len(objects) <= max_obj_cnt:
            eos = u'TRUE'
            context_id = ""
            rtn_inst_names = objects
        else:
            eos = u'FALSE'
            context_id = self._create_contextid()
            # Issue #2063  Use the timeout along with response delay.
            # Then user could timeout pulls. This means adding timer test to
            # pulls and close. Timer should be used to close old contexts.
            # Also The 'time' item contains elapsed time in fractional seconds
            # since an undefined point in time, so it is only useful for
            # calculating deltas.
            self.enumeration_contexts[context_id] = {'pull_type': pull_type,
                                                     'data': objects,
                                                     'namespace': namespace,
                                                     'time': delta_time(),
                                                     'interoptimeout': timeout}
            rtn_inst_names = objects[0:max_obj_cnt]
            del objects[0: max_obj_cnt]

        return self._make_pull_imethod_resp(rtn_inst_names, eos, context_id)

    def _pull_response(self, namespace, req_type, **params):
        """
        Common method for all of the Pull methods. Since all of the pull
        methods operate independent of the type of data, this single function
        severs as common code

        This method validates the namespace, gets data on the enumeration
        sequence from the enumeration_contexts table, validates the pull
        type, and returns the required number of objects.

        This method assumes the same context_id throughout the sequence.

        Raises:

            CIMError: CIM_ERR_INVALID_ENUMERATION_CONTEXT
        """

        self.validate_namespace(namespace)

        context_id = params['EnumerationContext']

        try:
            context_data = self.enumeration_contexts[context_id]
        except KeyError:
            raise CIMError(
                CIM_ERR_INVALID_ENUMERATION_CONTEXT,
                _format("EnumerationContext {0!A} not found in mock server "
                        "enumeration contexts.", context_id))

        if context_data['pull_type'] != req_type:
            raise CIMError(
                CIM_ERR_INVALID_ENUMERATION_CONTEXT,
                _format("Invalid pull operations {0!A} does not match "
                        "expected {1!A} for EnumerationContext {2!A}",
                        context_data['pull_type'], req_type, context_id))

        objs_list = context_data['data']

        max_obj_cnt = params['MaxObjectCount']
        if not max_obj_cnt:
            max_obj_cnt = _DEFAULT_MAX_OBJECT_COUNT

        if len(objs_list) <= max_obj_cnt:
            eos = u'TRUE'
            rtn_objs_list = objs_list
            del self.enumeration_contexts[context_id]
            context_id = ""
        else:
            eos = u'FALSE'
            rtn_objs_list = objs_list[0: max_obj_cnt]
            del objs_list[0: max_obj_cnt]

        return self._make_pull_imethod_resp(rtn_objs_list, eos, context_id)

    @staticmethod
    def _validate_open_params(**params):
        """
        Validate the fql parameters and if invalid, generate exception
        """
        if not params['FilterQueryLanguage'] and params['FilterQuery']:
            raise CIMError(
                CIM_ERR_INVALID_PARAMETER,
                "FilterQuery without FilterQueryLanguage definition is "
                "invalid")
        if params['FilterQueryLanguage']:
            if params['FilterQueryLanguage'] != 'DMTF:FQL':
                raise CIMError(
                    CIM_ERR_QUERY_LANGUAGE_NOT_SUPPORTED,
                    _format("FilterQueryLanguage {0!A} not supported",
                            params['FilterQueryLanguage']))
        ot = params['OperationTimeout']
        if ot:
            if not isinstance(ot, six.integer_types) or ot < 0 \
                    or ot > OPEN_MAX_TIMEOUT:
                raise CIMError(
                    CIM_ERR_INVALID_PARAMETER,
                    _format("OperationTimeout {0!A }must be positive integer "
                            "less than {1!A}", ot, OPEN_MAX_TIMEOUT))

    def _fake_OpenEnumerateInstancePaths(self, **params):
        # pylint: disable=invalid-name
        """
        Implements WBEM server responder for
        :meth:`~pywbem.WBEMConnection.OpenEnumerationInstancePaths`
        with data from the instance repository.
        """

        namespace = self.namespace
        self.validate_namespace(namespace)
        self._validate_open_params(**params)

        result_t = self._fake_EnumerateInstanceNames(**params)

        return self._open_response(result_t[0][2], namespace,
                                   'PullInstancePaths', **params)

    def _fake_OpenEnumerateInstances(self, **params):
        """
        Implements WBEM server responder for
        :meth:`~pywbem.WBEMConnection.OpenEnumerationInstances`
        with data from the instance repository.
        """
        namespace = self.namespace
        self.validate_namespace(namespace)
        self._validate_open_params(**params)

        result_t = self._fake_EnumerateInstances(**params)

        return self._open_response(result_t[0][2], namespace,
                                   'PullInstancesWithPath', **params)

    def _fake_OpenReferenceInstancePaths(self, **params):
        # pylint: disable=invalid-name
        """
        Implements WBEM server responder for
        :meth:`~pywbem.WBEMConnection.OpenReferenceInstancePaths`
        with data from the instance repository.
        """
        namespace = self.namespace
        self.validate_namespace(namespace)
        self._validate_open_params(**params)
        params['ObjectName'] = params['InstanceName']
        del params['InstanceName']

        result = self._fake_ReferenceNames(**params)

        objects = [] if result is None else [x[2] for x in result[0][2]]

        return self._open_response(objects, namespace,
                                   'PullInstancePaths', **params)

    def _fake_OpenReferenceInstances(self, **params):
        """
        Implements WBEM server responder for
        :meth:`~pywbem.WBEMConnection.OpenReferenceInstances`
        with data from the instance repository.
        """

        namespace = self.namespace
        self.validate_namespace(namespace)
        self._validate_open_params(**params)
        params['ObjectName'] = params['InstanceName']
        del params['InstanceName']

        result = self._fake_References(**params)

        objects = [] if result is None else [x[2] for x in result[0][2]]

        return self._open_response(objects, namespace,
                                   'PullInstancesWithPath', **params)

    def _fake_OpenAssociatorInstancePaths(self, **params):
        # pylint: disable=invalid-name
        """
        Implements WBEM server responder for
        :meth:`~pywbem.WBEMConnection.OpenAssociatorInstancePaths`
        with data from the instance repository.
        """

        namespace = self.namespace
        self.validate_namespace(namespace)
        self._validate_open_params(**params)
        params['ObjectName'] = params['InstanceName']
        del params['InstanceName']

        result = self._fake_AssociatorNames(**params)

        objects = [] if result is None else [x[2] for x in result[0][2]]

        return self._open_response(objects, namespace,
                                   'PullInstancePaths', **params)

    def _fake_OpenAssociatorInstances(self, **params):
        """
        Implements WBEM server responder for
        WBEMConnection.OpenAssociatorInstances
        with data from the instance repository.
        """

        namespace = self.namespace
        self.validate_namespace(namespace)
        self._validate_open_params(**params)
        params['ObjectName'] = params['InstanceName']
        del params['InstanceName']

        result = self._fake_Associators(**params)

        objects = [] if result is None else [x[2] for x in result[0][2]]

        return self._open_response(objects, namespace,
                                   'PullInstancesWithPath', **params)

    def _fake_OpenQueryInstances(self, **params):
        # pylint: disable=invalid-name
        """
        Implements WBEM server responder for
        :meth:`~pywbem.WBEMConnection.OpenQueryInstances`
        with data from the instance repository.
        """

        namespace = self.namespace
        self.validate_namespace(namespace)
        self._validate_open_params(**params)

        # pylint: disable=assignment-from-no-return
        # Issue #2064 TODO/ks implement execquery
        result = self._fake_ExecQuery(**params)

        objects = [] if result is None else [x[2] for x in result[0][2]]

        return self._open_response(objects, namespace,
                                   'PullInstancesWithPath', **params)

    def _fake_PullInstancesWithPath(self, **params):
        """
        Implements WBEM server responder for
        :meth:`~pywbem.WBEMConnection.OpenPullInstancesWithPath`
        with data from the instance repository.
        """

        namespace = self.namespace
        return self._pull_response(namespace, 'PullInstancesWithPath',
                                   **params)

    def _fake_PullInstancePaths(self, **params):
        """
        Implements WBEM server responder for
        :meth:`~pywbem.WBEMConnection.OpenPullInstancePaths`
        with data from the instance repository.
        """

        namespace = self.namespace
        return self._pull_response(namespace, 'PullInstancePaths', **params)

    def _fake_PullInstances(self, **params):
        """
        Implements WBEM server responder for
        :meth:`~pywbem.WBEMConnection.OpenPullInstances`
        with data from the instance repository.
        """

        namespace = self.namespace
        return self._pull_response(namespace, 'PullInstances', **params)

    def _fake_CloseEnumeration(self, **params):
        """
            Implements WBEM server responder for
            :meth:`~pywbem.WBEMConnection.CloseEnumeration`
            with data from the instance repository.

            If the EnumerationContext is valid it removes it from the
            context repository. Otherwise it returns an exception.
        """

        namespace = self.namespace
        self.validate_namespace(namespace)

        context_id = params['EnumerationContext']

        try:
            context_data = self.enumeration_contexts[context_id]
        except KeyError:
            raise CIMError(
                CIM_ERR_INVALID_ENUMERATION_CONTEXT,
                _format("EnumerationContext {0!A} not found in mock server "
                        "enumeration contexts.", context_id))

        # This is probably relatively useless because pywbem handles
        # namespace internally but it could catch an error if user plays
        # with the context.
        if context_data['namespace'] != namespace:
            raise CIMError(
                CIM_ERR_INVALID_NAMESPACE,
                _format("Invalid namespace {0!A} for CloseEnumeration {1!A}",
                        namespace, context_id))

        del self.enumeration_contexts[context_id]

    #####################################################################
    #
    #  Faked WBEMConnection InvokeMethod
    #
    #####################################################################

    def _fake_invokemethod(self, methodname, objectname, Params, **params):
        # pylint: disable=invalid-name
        """
        Implements a mock WBEM server responder for
        :meth:`~pywbem.WBEMConnection.InvokeMethod`

        This responder calls a function defined by an entry in the methods
        repository. The return from that function is returned to the user.

        Input params are MethodName, ObjectName, and Params

        The return is espected to be the same as the return defined by
        WBEMConnection.InvokeMethod (ReturnValue, OutputParameters).
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
        cc = self._get_class(localobject.classname, namespace,
                             local_only=False, include_qualifiers=True,
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
            tcc = self._get_class(target_cln, namespace,
                                  local_only=False, include_qualifiers=True,
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
