#
# (C) Copyright 2018 InovaDevelopment.comn
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
import locale
import traceback
import re
from xml.dom import minidom
from mock import Mock
import six


from pywbem import WBEMConnection, CIMClass, CIMClassName, \
    CIMInstance, CIMInstanceName, CIMQualifierDeclaration, \
    CIMParameter, cimtype, CIMError, \
    CIM_ERR_NOT_FOUND, CIM_ERR_METHOD_NOT_FOUND, CIM_ERR_FAILED, \
    CIM_ERR_INVALID_PARAMETER, \
    CIM_ERR_INVALID_CLASS, CIM_ERR_ALREADY_EXISTS, \
    CIM_ERR_INVALID_NAMESPACE, CIM_ERR_INVALID_ENUMERATION_CONTEXT, \
    CIM_ERR_NOT_SUPPORTED, CIM_ERR_QUERY_LANGUAGE_NOT_SUPPORTED, \
    CIM_ERR_NAMESPACE_NOT_EMPTY, \
    DEFAULT_NAMESPACE, MOFCompiler
from pywbem._nocasedict import NocaseDict
from pywbem._utils import _format

from ._dmtf_cim_schema import DMTFCIMSchema
from ._resolvermixin import ResolverMixin
from ._mockmofwbemconnection import _MockMOFWBEMConnection

if six.PY2:
    import codecs  # pylint: disable=wrong-import-order


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


# TODO: ks Future We have not considered that iq and ico are deprecated in
# DSP0200 for get_instance, etc. We could  set up a default to ignore these
# parameters for the operations in which they are deprecated and we
# should/could ignore them. We need to document our behavior in relation to the
# spec.

STDOUT_ENCODING = getattr(sys.stdout, 'encoding', None)
if not STDOUT_ENCODING:
    STDOUT_ENCODING = locale.getpreferredencoding()
if not STDOUT_ENCODING:
    STDOUT_ENCODING = 'utf-8'


def _uprint(dest, text):
    """
    Write text to dest, adding a newline character.

    Text may be a unicode string, or a byte string in UTF-8 encoding.
    It must not be None.

    If dest is None, the text is encoded to a codepage suitable for the current
    stdout and is written to stdout.

    Otherwise, dest must be a file path, and the text is encoded to a UTF-8
    Byte sequence and is appended to the file (opening and closing the file).
    """
    if isinstance(text, six.text_type):
        text = text + u'\n'
    elif isinstance(text, six.binary_type):
        text = text + b'\n'
    else:
        raise TypeError(
            "text must be a unicode or byte string, but is {0}".
            format(type(text)))
    if dest is None:
        if six.PY2:
            # On py2, stdout.write() requires byte strings
            if isinstance(text, six.text_type):
                text = text.encode(STDOUT_ENCODING, 'replace')
        else:
            # On py3, stdout.write() requires unicode strings
            if isinstance(text, six.binary_type):
                text = text.decode('utf-8')
        sys.stdout.write(text)
    elif isinstance(dest, (six.text_type, six.binary_type)):
        if isinstance(text, six.text_type):
            open_kwargs = dict(mode='a', encoding='utf-8')
        else:
            open_kwargs = dict(mode='ab')
        if six.PY2:
            # Open with codecs to be able to set text mode
            with codecs.open(dest, **open_kwargs) as f:
                f.write(text)
        else:
            with open(dest, **open_kwargs) as f:
                f.write(text)
    else:
        raise TypeError(
            "dest must be None or a string, but is {0}".
            format(type(text)))


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
                 timeout=None, response_delay=None, repo_lite=False):
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

          repo_lite (:class:`py:bool`):
            Flag to set the
            :ref:`operation mode <mock repository operation modes>` of the mock
            repository.
            If `True`, lite mode is set.
            If `False`, full mode is set.
        """
        # Response delay in seconds. Any operation is delayed by this time.
        # Initialize before superclass init because otherwise logger may
        # fail with this attribute not found
        self._response_delay = response_delay

        super(FakedWBEMConnection, self).__init__(
            'http://FakedUrl',
            default_namespace=default_namespace,
            use_pull_operations=use_pull_operations,
            stats_enabled=stats_enabled, timeout=timeout)

        # The namespaces that may exist in the mock repository. This is a
        # dictionary where the key is the namespace name, and the value does
        # not matter (this approach is used to ensure namespace names are
        # treated case insensitively). This set of namespaces is used to
        # control into which namespaces of the mock repository classes,
        # qualifier types and instances may be added.
        self.namespaces = NocaseDict({default_namespace: True})

        # The CIM classes in the mock repository.
        # This is a dictionary of dictionaries where the top level key is the
        # CIM namespace name and the keys for each sub-dictionary in a
        # namespace are class names, and the values in each sub-dictionary are
        # the CIM classes in that namespace, represented as CIMClass objects.
        # The dictionaries are NocaseDict since namespaces should be case
        # insensitive.
        # The namespaces are added to the outer dictionary as needed (if
        # permitted as per self.namesaces).
        self.classes = NocaseDict()

        # The CIM qualifier types in the mock repository.
        # Same format as for classes above, except that the values in each
        # sub-dictionary are CIMQualifierDeclaration objects.
        # The namespaces are added to the outer dictionary as needed (if
        # permitted as per self.namesaces).
        self.qualifiers = NocaseDict()

        # The CIM instances in the mock repository.
        # Because instances do not have a name, the format is slightly
        # different: This is a dictionary of lists where the top level key is
        # the CIM namespace name and the value is a list of CIM instances in
        # that namespace, represented as CIMInstance objects.
        # The namespaces are added to the outer dictionary as needed (if
        # permitted as per self.namesaces).
        # TODO: ks. FUTURE maybe we should really have a subdict per class but
        #           it is not important for initial release.
        self.instances = NocaseDict()

        # The CIM methods with callback in the mock repository.
        # This is a dictionary of dictionaries of dictionaries, where the top
        # level key is the CIM namespace name, the second level key is the
        # CIM class name, and the third level key is the CIM method name.
        # The values at the last level are (TBD: method callbacks?).
        # The namespaces are added to the outer dictionary as needed (if
        # permitted as per self.namesaces).
        self.methods = NocaseDict()

        self._repo_lite = repo_lite

        # Open Pull Contexts. The key for each context is an enumeration
        # context id.  The data is the total list of instances/names to
        # be returned and the current position in the list. Any context in
        # this list is still open.
        self.enumeration_contexts = {}

        self._imethodcall = Mock(side_effect=self._mock_imethodcall)
        self._methodcall = Mock(side_effect=self._mock_methodcall)

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
    #   Methods to insert data into mock repository
    #
    ################################################################

    def add_namespace(self, namespace):
        """
        Add a CIM namespace to the mock repository.

        The namespace must not yet exist in the mock repository.

        Note that the default connection namespace is automatically added to
        the mock repository upon creation of this object.

        Parameters:

          namespace (:term:`string`):
            The name of the CIM namespace in the mock repository. Must not be
            `None`. Any leading and trailing slash characters are split off
            from the provided string.

        Raises:

          ValueError: Namespace argument must not be None
          CIMError: CIM_ERR_ALREADY_EXISTS if the namespace already exists in
            the mock repository.
        """

        if namespace is None:
            raise ValueError("Namespace argument must not be None")

        # Normalize the namespace name
        namespace = namespace.strip('/')

        if namespace in self.namespaces:
            raise CIMError(
                CIM_ERR_ALREADY_EXISTS,
                _format("Namespace {0!A} already exists in the mock "
                        "repository", namespace))

        self.namespaces[namespace] = True

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
          CIMError: CIM_ERR_NOT_FOUND if the namespace does not exist in
            the mock repository.
          CIMError: CIM_ERR_NAMESPACE_NOT_EMPTY if the namespace is not empty.
          CIMError: CIM_ERR_NAMESPACE_NOT_EMPTY if the default connection
            namespace was attempted to be deleted.
        """

        if namespace is None:
            raise ValueError("Namespace argument must not be None")

        # Normalize the namespace name
        namespace = namespace.strip('/')

        if namespace not in self.namespaces:
            raise CIMError(
                CIM_ERR_NOT_FOUND,
                _format("Namespace {0!A} does not exist in the mock "
                        "repository", namespace))

        if not self._class_repo_empty(namespace) or \
                not self._instance_repo_empty(namespace) or \
                not self._qualifier_repo_empty(namespace):
            raise CIMError(
                CIM_ERR_NAMESPACE_NOT_EMPTY,
                _format("Namespace {0!A} is not empty", namespace))

        if namespace == self.default_namespace:
            raise CIMError(
                CIM_ERR_NAMESPACE_NOT_EMPTY,
                _format("Connection default namespace {0!A} cannot be "
                        "deleted from mock repository", namespace))

        del self.namespaces[namespace]

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
          :exc:`~pywbem.MOFParseError`: Compile error in the MOF.
          :exc:`~pywbem.CIMError`: CIM_ERR_INVALID_NAMESPACE: Namespace does
            not exist.
          :exc:`~pywbem.CIMError`: Failure related to the CIM objects in the
            mock repository.
        """

        namespace = namespace or self.default_namespace
        self._validate_namespace(namespace)

        mofcomp = MOFCompiler(_MockMOFWBEMConnection(self),
                              search_paths=search_paths,
                              verbose=verbose)

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
          :exc:`~pywbem.MOFParseError`: Compile error in the MOF.
          :exc:`~pywbem.CIMError`: CIM_ERR_INVALID_NAMESPACE: Namespace does
            not exist.
          :exc:`~pywbem.CIMError`: Failure related to the CIM objects in the
            mock repository.
        """
        namespace = namespace or self.default_namespace

        # if not self._validate_namespace(namespace):  TODO
        #    self.add_namespace(namespace)
        self._validate_namespace(namespace)

        mofcomp = MOFCompiler(_MockMOFWBEMConnection(self),
                              search_paths=search_paths,
                              verbose=verbose)

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
          :exc:`~pywbem.MOFParseError`: Compile error in the MOF.
          :exc:`~pywbem.CIMError`: CIM_ERR_INVALID_NAMESPACE: Namespace does
            not exist.
          :exc:`~pywbem.CIMError`: Failure related to the CIM objects in the
            mock repository.
        """

        schema = DMTFCIMSchema(schema_version, schema_root_dir,
                               use_experimental=use_experimental,
                               verbose=verbose)
        schema_mof = schema.build_schema_mof(class_names)
        search_paths = schema.schema_mof_dir
        self.compile_mof_string(schema_mof, namespace=namespace,
                                search_paths=[search_paths],
                                verbose=verbose)

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
        self._validate_namespace(namespace)

        if isinstance(objects, list):
            for obj in objects:
                self.add_cimobjects(obj, namespace=namespace)

        else:
            obj = objects
            if isinstance(obj, CIMClass):
                cc = deepcopy(obj)
                if cc.superclass:
                    if not self._class_exists(cc.superclass, namespace):
                        raise ValueError(
                            _format("Class {0!A} defines superclass {1!A} but "
                                    "the superclass does not exist in the "
                                    "repository.",
                                    cc.classname, cc.superclass))
                class_repo = self._get_class_repo(namespace)

                # TODO this sort of kills off the conn_lite for classes
                # since we are resolving the classes.
                qualifier_repo = None if self._repo_lite else \
                    self._get_qualifier_repo(namespace)
                cc1 = self._resolve_class(cc, namespace, qualifier_repo,
                                          verbose=False)

                class_repo[cc.classname] = cc1.copy()

            elif isinstance(obj, CIMInstance):
                inst = deepcopy(obj)
                if inst.path is None:
                    raise ValueError(
                        _format("Instances added must include a path. "
                                "Instance {0!A} does not include a path",
                                inst))
                if inst.path.namespace is None:
                    inst.path.namespace = namespace
                if inst.path.host is not None:
                    inst.path.host = None
                instance_repo = self._get_instance_repo(namespace)
                try:
                    if self._find_instance(inst.path, instance_repo)[1] \
                            is not None:
                        raise ValueError(
                            _format("The instance {0!A} already exists in "
                                    "namespace {1!A}", inst, namespace))
                except CIMError as ce:
                    raise CIMError(
                        CIM_ERR_FAILED,
                        _format("Internal failure of add_cimobject operation. "
                                "Rcvd CIMError {0}", ce))
                instance_repo.append(inst)

            elif isinstance(obj, CIMQualifierDeclaration):
                qual = deepcopy(obj)
                qualifier_repo = self._get_qualifier_repo(namespace)
                self._init_qualifier_decl(qual, qualifier_repo)
                qualifier_repo[qual.name] = qual

            else:
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
            File path of the output file. If `None`, the output is written to
            stdout.

          summary (:class:`py:bool`):
            Flag for summary mode. If `True`, only a summary count of CIM
            objects in the specified namespaces of the mock repository is
            produced. If `False`, both the summary count and the details of
            the CIM objects are produced.

          output_format (:term:`string`):
            Output format, one of: 'mof', 'xml', or 'repr'.
        """
        if output_format == 'mof':
            cmt_begin = '# '
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
        repo_ns_set = set(self.namespaces.keys())

        if namespaces:
            if isinstance(namespaces, six.string_types):
                namespaces = [namespaces]

            repo_ns_set = repo_ns_set.intersection(set(namespaces))
        repo_ns_list = sorted(list(repo_ns_set))

        for ns in repo_ns_list:
            _uprint(dest,
                    _format(u"\n{0}NAMESPACE {1!A}{2}\n",
                            cmt_begin, ns, cmt_end))
            self._display_objects('Qualifier Declarations', self.qualifiers,
                                  ns, cmt_begin, cmt_end, dest=dest,
                                  summary=summary, output_format=output_format)
            self._display_objects('Classes', self.classes, ns, cmt_begin,
                                  cmt_end, dest=dest,
                                  summary=summary, output_format=output_format)
            self._display_objects('Instances', self.instances, ns,
                                  cmt_begin, cmt_end, dest=dest,
                                  summary=summary, output_format=output_format)
            self._display_objects('Methods', self.methods, ns,
                                  cmt_begin, cmt_end, dest=dest,
                                  summary=summary, output_format=output_format)

        _uprint(dest, u'============End Repository=================')

    @staticmethod
    def _display_objects(obj_type, object_repo, namespace, cmt_begin, cmt_end,
                         dest=None, summary=None, output_format=None):
        """
        Display a set of objects of obj_type from the dictionary defined
        by the parameter object_repo. obj_type is a string that defines the
        type of object ('Classes', 'Instances', 'Qualifier Declarations',
        'Methods').
        """

        # TODO:ks FUTURE Consider sorting to perserve order of compile/add.
        if namespace in object_repo:
            if obj_type == 'Methods':
                _uprint(dest,
                        _format(u"{0}Namespace {1!A}: contains {2} {3}:{4}\n",
                                cmt_begin, namespace,
                                len(object_repo[namespace]),
                                obj_type, cmt_end))
            else:
                _uprint(dest,
                        _format(u"{0}Namespace {1!A}: contains {2} {3} {4}\n",
                                cmt_begin, namespace,
                                len(object_repo[namespace]),
                                obj_type, cmt_end))
            if summary:
                return

            # instances are special because the inner struct is a list
            if obj_type == 'Instances':
                try:
                    insts = object_repo[namespace]
                except KeyError:
                    return

                # TODO:ks Future: Possibly sort insts by path order.
                for inst in insts:
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
                    methods = object_repo[namespace]
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
                assert obj_type in ['Classes', 'Qualifier Declarations']
                try:
                    objs = object_repo[namespace]
                except KeyError:
                    return
                for key in sorted(objs):
                    obj = objs[key]
                    if output_format == 'xml':
                        _uprint(dest, _pretty_xml(obj.tocimxmlstr()))
                    elif output_format == 'repr':
                        _uprint(dest, _format(u"{0!A}", obj))
                    else:
                        _uprint(dest, obj.tomof())

    def _get_inst_repo(self, namespace=None):
        """
        Test support method that returns instances from the repository with
        no processing.  It uses the default namespace if input parameter
        for namespace is None
        """
        if namespace is None:
            namespace = self.default_namespace
        return self.instances[namespace]

    ##########################################################
    #
    #   Functions Mocked. WBEMConnection only mocks the WBEMConnection
    #   _imethodcall and _methodcall methods.  This captures all calls
    #   to the wbem server.
    #
    ##########################################################

    def _mock_imethodcall(self, methodname, namespace, response_params_rqd=None,
                          **params):  # pylint: disable=unused-argument
        """
        Mocks the WBEMConnection._imethodcall() method.

        This mock calls methods within this class that fake the processing
        in a WBEM server (at the CIM Object level) for the varisous CIM/XML
        methods and return.

        Each function is named with the lower case method namd prepended with
        '_fake_'.
        """
        method_name = '_fake_' + methodname.lower()

        method_name = getattr(self, method_name)

        result = method_name(namespace, **params)

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
        class_repo = self._get_class_repo(namespace)
        return classname in class_repo

    @staticmethod
    def _make_tuple(rtn_value):
        """
        Make the return value into a tuple in accord with _imethodcall
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

    def _validate_namespace(self, namespace):
        """
        Validate whether a CIM namespace exists in the mock repository.

        Parameters:

          namespace (:term:`string`):
            The name of the CIM namespace in the mock repository. Must not be
            `None`.

        Raises:

          :exc:`~pywbem.CIMError`: CIM_ERR_INVALID_NAMESPACE: Namespace does
            not exist.
        """
        if namespace not in self.namespaces:
            raise CIMError(
                CIM_ERR_INVALID_NAMESPACE,
                _format("Namespace does not exist in mock repository: {0!A}",
                        namespace))

    def _get_class_repo(self, namespace):
        """
        Returns the class repository for the specified CIM namespace
        within the mock repository. This is the original instance variable,
        so any modifications will change the mock repository.

        Validates that the namespace exists in the mock repository.

        If the class repository does not contain the namespace yet, it is
        added.

        Parameters:

          namespace(:term:`string`): Namespace name. Must not be `None`.

        Returns:

          dict of CIMClass: Class repository.

        Raises:

          :exc:`~pywbem.CIMError`: CIM_ERR_INVALID_NAMESPACE: Namespace does
            not exist.
        """
        self._validate_namespace(namespace)
        if namespace not in self.classes:
            self.classes[namespace] = NocaseDict()
        return self.classes[namespace]

    def _get_instance_repo(self, namespace):
        """
        Returns the instance repository for the specified CIM namespace
        within the mock repository. This is the original instance variable,
        so any modifications will change the mock repository.

        Validates that the namespace exists in the mock repository.

        If the instance repository does not contain the namespace yet, it is
        added.

        Parameters:

          namespace(:term:`string`): Namespace name. Must not be `None`.

        Returns:

          list of CIMInstance: Instance repository.

        Raises:

          :exc:`~pywbem.CIMError`: CIM_ERR_INVALID_NAMESPACE: Namespace does
            not exist.
        """
        self._validate_namespace(namespace)
        if namespace not in self.instances:
            self.instances[namespace] = []
        return self.instances[namespace]

    def _get_qualifier_repo(self, namespace):
        """
        Returns the qualifier repository for the specified CIM namespace
        within the mock repository. This is the original instance variable,
        so any modifications will change the mock repository.

        Validates that the namespace exists in the mock repository.

        If the qualifier repository does not contain the namespace yet, it is
        added.

        Parameters:

          namespace(:term:`string`): Namespace name. Must not be `None`.

        Returns:

          dict of CIMQualifierDeclaration: Qualifier repository.

        Raises:

          :exc:`~pywbem.CIMError`: CIM_ERR_INVALID_NAMESPACE: Namespace does
            not exist.
        """
        self._validate_namespace(namespace)
        if namespace not in self.qualifiers:
            self.qualifiers[namespace] = NocaseDict()
        return self.qualifiers[namespace]

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

          dict of dict of method callback function: Method repository.

        Raises:

          :exc:`~pywbem.CIMError`: CIM_ERR_INVALID_NAMESPACE: Namespace does
            not exist.
        """
        self._validate_namespace(namespace)
        if namespace not in self.methods:
            self.methods[namespace] = NocaseDict()
        return self.methods[namespace]

    def _class_repo_empty(self, namespace):
        """
        Returns a bool indicating whether the class repository for the
        specified CIM namespace within the mock repository is empty.

        The class repository is considered empty if it does not exist for
        the namespace, or if it exists and is empty.

        Parameters:

          namespace(:term:`string`): Namespace name. Must not be `None`.

        Returns:

          bool: Class repository is empty (or does not exist for the namespace)
        """
        return namespace not in self.classes or not self.classes[namespace]

    def _instance_repo_empty(self, namespace):
        """
        Returns a bool indicating whether the instance repository for the
        specified CIM namespace within the mock repository is empty.

        The instance repository is considered empty if it does not exist for
        the namespace, or if it exists and is empty.

        Parameters:

          namespace(:term:`string`): Namespace name. Must not be `None`.

        Returns:

          bool: Instance repository is empty (or does not exist for the
            namespace)
        """
        return namespace not in self.instances or not self.instances[namespace]

    def _qualifier_repo_empty(self, namespace):
        """
        Returns a bool indicating whether the qualifier repository for the
        specified CIM namespace within the mock repository is empty.

        The qualifier repository is considered empty if it does not exist for
        the namespace, or if it exists and is empty.

        Parameters:

          namespace(:term:`string`): Namespace name. Must not be `None`.

        Returns:

          bool: Qualifier repository is empty (or does not exist for the
            namespace)
        """
        return namespace not in self.qualifiers or \
            not self.qualifiers[namespace]

    def _get_superclassnames(self, cn, namespace):
        """
        Get list of superclasses names from the class repository for the
        defined classname in the namespace.

        Returns in order of descending class hiearchy.
        """
        class_repo = self._get_class_repo(namespace)
        superclass_names = []
        if cn is not None:
            cnwork = cn
            while cnwork:
                cnsuper = class_repo[cnwork].superclass
                if cnsuper:
                    superclass_names.append(cnsuper)
                cnwork = cnsuper
            superclass_names.reverse()
        return superclass_names

    def _get_subclass_names(self, classname, namespace, deep_inheritance):
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

        # retrieve first level of subclasses for which classname is superclass
        try:
            classes = self.classes[namespace]
        except KeyError:
            classes = NocaseDict()
        if classname is None:
            rtn_classnames = [
                cl.classname for cl in six.itervalues(classes)
                if cl.superclass is None]
        else:
            rtn_classnames = [
                cl.classname for cl in six.itervalues(classes)
                if cl.superclass and cl.superclass.lower() == classname.lower()]

        # recurse for next level of class hiearchy
        if deep_inheritance:
            subclass_names = []
            if rtn_classnames:
                for cn in rtn_classnames:
                    subclass_names.extend(
                        self._get_subclass_names(cn, namespace,
                                                 deep_inheritance))
            rtn_classnames.extend(subclass_names)
        return rtn_classnames

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

        class_repo = self._get_class_repo(namespace)

        # try to get the target class and create a copy for response
        try:
            c = class_repo[classname]
        except KeyError:
            raise CIMError(
                CIM_ERR_NOT_FOUND,
                _format("Class {0!A} not found in namespace {1!A}.",
                        classname, namespace))
        cc = deepcopy(c)

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

    def _get_association_classes(self, namespace):
        """
        Return iterator of associator classes from the class repo

        Returns the classes that have associations qualifier.
        Does NOT copy so these are what is in repository. User functions
        MUST NOT modify these classes.

        Returns: Returns generator where each yield returns a single
                 association class
        """

        class_repo = self._get_class_repo(namespace)
        # associator_classes = []
        for cl in six.itervalues(class_repo):
            if 'Association' in cl.qualifiers:
                yield cl
        return

    @staticmethod
    def _find_instance(iname, instance_repo):
        """
        Find an instance in the instance repo by iname and return the
        index of that instance.

        Parameters:

          iname: CIMInstancename to find

          instance_repo: the instance repo to search

        Return (None, None if not found. Otherwise return tuple of
               index, instance

        Raises:

          CIMError: Failed if repo invalid.
        """

        rtn_inst = None
        rtn_index = None
        for index, inst in enumerate(instance_repo):
            if iname == inst.path:
                if rtn_inst is not None:
                    # TODO:ks Future Remove dup test since we should be
                    # insuring no dups on instance creation
                    raise CIMError(
                        CIM_ERR_FAILED,
                        _format("Invalid Repository. Multiple instances with "
                                "same path {0!A}.", rtn_inst.path))
                rtn_inst = inst
                rtn_index = index
        return(rtn_index, rtn_inst)

    def _get_instance(self, iname, namespace, property_list, local_only,
                      include_class_origin, include_qualifiers):
        """
        Local method implements getinstance. This is generally used by
        other instance methods that need to get an instance from the
        repository.

        It attempts to get the instance, copies it, and filters it
        for input parameters like localonly, includequalifiers, and
        propertylist.

        Returns:

          CIMInstance copy from the repository with property_list filtered,
          and qualifers removed if include_qualifiers=False and
          class origin removed if include_class_origin False
        """

        instance_repo = self._get_instance_repo(namespace)

        rtn_tup = self._find_instance(iname, instance_repo)
        inst = rtn_tup[1]

        if inst is None:
            raise CIMError(
                CIM_ERR_NOT_FOUND,
                _format("Instance not found in repository namespace {0!A}. "
                        "Path={1!A}", namespace, iname))
        rtn_inst = deepcopy(inst)

        # If local_only remove properties where class_origin
        # differs from class of target instance
        if local_only:
            for p in rtn_inst:
                class_origin = rtn_inst.properties[p].class_origin
                if class_origin and class_origin != inst.classname:
                    del rtn_inst[p]

        # if not repo_lite test against class properties
        if not self._repo_lite and local_only:
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

    def _get_subclass_list_for_enums(self, classname, namespace):
        """ Get class list (i.e names of subclasses for classname for the
            enumerateinstance methods. If conn.lite returns only classname but
            no subclasses.

            Returns NocaseDict where only the keys are important, This allows
            case insensitive matches of the names with Python "for cln in clns".
        """
        if self._repo_lite:
            return NocaseDict({classname: classname})
        if not self._class_exists(classname, namespace):
            raise CIMError(
                CIM_ERR_INVALID_CLASS,
                _format("Class {0!A} not found in namespace {1!A}.",
                        classname, namespace))

        if not self.classes:
            return NocaseDict()

        clnslist = self._get_subclass_names(classname, namespace, True)
        clnsdict = NocaseDict()
        for cln in clnslist:
            clnsdict[cln] = cln

        clnsdict[classname] = classname
        return clnsdict

    @staticmethod
    def _filter_properties(obj, property_list):
        """
        Remove properties from an instance or class that aren't in the
        plist parameter

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

    #####################################################################
    #
    #        Faked WBEMConnection operation methods.
    #        All the methods are named _fake_<methodname> and
    #        are responders that emulate the server response.
    #
    #        This is all the WBEMConnection methods that communicate with
    #        a WBEMServer.
    #
    ######################################################################

    def _fake_enumerateclasses(self, namespace, **params):
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

        self._validate_namespace(namespace)

        classname = params.get('ClassName', None)
        if classname:
            assert(isinstance(classname, CIMClassName))
            if not self._class_exists(classname.classname, namespace):
                raise CIMError(
                    CIM_ERR_INVALID_CLASS,
                    _format("The class {0!A} defined by 'ClassName' parameter "
                            "does not exist in namespace {1!A}",
                            classname, namespace))

        clns = self._get_subclass_names(classname, namespace,
                                        params['DeepInheritance'])

        # Note: _get_class will return NOT_FOUND if the class not in the
        # repo but it was just found by _get_subclass_names so that would
        # probably be some form of repo corruption.
        classes = [
            self._get_class(cn, namespace,
                            local_only=params['LocalOnly'],
                            include_qualifiers=params['IncludeQualifiers'],
                            include_classorigin=params['IncludeClassOrigin'])
            for cn in clns]

        return self._make_tuple(classes)

    def _fake_enumerateclassnames(self, namespace, **params):
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

        self._validate_namespace(namespace)

        classname = params.get('ClassName', None)
        if classname:
            assert(isinstance(classname, CIMClassName))
            if not self._class_exists(classname.classname, namespace):
                raise CIMError(
                    CIM_ERR_INVALID_CLASS,
                    _format("The class {0!A} defined by 'ClassName' parameter "
                            "does not exist in namespace {1!A}",
                            classname, namespace))

        clns = self._get_subclass_names(classname, namespace,
                                        params['DeepInheritance'])
        rtn_clns = [
            CIMClassName(cn, namespace=namespace, host=self.host)
            for cn in clns]

        return self._make_tuple(rtn_clns)

    def _fake_getclass(self, namespace, **params):
        """
        Implements a mock server responder for
        :meth:`~pywbem.WBEMConnection.GetClass

        Retrieve a CIM class from the local repository.

        For a description of the parameters, see
        :meth:`pywbem.WBEMConnection.GetClass`.
        """

        self._validate_namespace(namespace)

        cname = params['ClassName'].classname

        cc = self._get_class(cname, namespace, local_only=params['LocalOnly'],
                             include_qualifiers=params['IncludeQualifiers'],
                             include_classorigin=params['IncludeClassOrigin'],
                             property_list=params['PropertyList'])

        return self._make_tuple([cc])

    def _fake_createclass(self, namespace, **params):
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
        # Validate parameters
        new_class = params['NewClass']
        if not isinstance(new_class, CIMClass):
            raise CIMError(
                CIM_ERR_INVALID_PARAMETER,
                _format("NewClass not valid CIMClass. Rcvd type={0}",
                        type(new_class)))

        # Validate namespace
        class_repo = self._get_class_repo(namespace)

        qualifier_repo = None if self._repo_lite else \
            self._get_qualifier_repo(namespace)

        if new_class.classname in class_repo:
            raise CIMError(
                CIM_ERR_ALREADY_EXISTS,
                _format("Class {0!A} already exists in namespace {1!A}.",
                        new_class.classname, namespace))

        new_class = deepcopy(new_class)

        self._resolve_class(new_class, namespace, qualifier_repo, verbose=False)

        class_repo[new_class.classname] = new_class

    def _fake_modifyclass(self, namespace, **params):
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

        self._validate_namespace(namespace)

        raise CIMError(
            CIM_ERR_NOT_SUPPORTED,
            "Currently ModifyClass not supported in Fake_WBEMConnection")

    def _fake_deleteclass(self, namespace, **params):
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

        # Validate namespace
        class_repo = self._get_class_repo(namespace)

        cname = params['ClassName'].classname

        try:
            class_repo[cname]
        except KeyError:
            raise CIMError(
                CIM_ERR_NOT_FOUND,
                _format("Class {0!A} in namespace {1!A} not in repository. "
                        "Nothing deleted.", cname, namespace))

        classnames = self._get_subclass_names(cname, namespace, True)
        classnames.append(cname)

        # delete all instances in this class and subclasses and delete
        # this class and subclasses
        for clname in classnames:
            if self.instances:
                inst_names = self.EnumerateInstanceNames(clname, namespace)
                for iname in inst_names:
                    self.DeleteInstance(iname)
            del class_repo[clname]

    ##########################################################
    #
    #              Faked Qualifier methods
    #
    ###########################################################

    def _fake_enumeratequalifiers(self, namespace, **params):
        # pylint: disable=unused-argument
        """
        Imlements a mock server responder for
        :meth:`~pywbem.WBEMConnection.EnumerateQualifiers`

        Enumerates the qualifier declarations in the local repository of this
        namespace.
        """

        # Validate namespace
        qualifier_repo = self._get_qualifier_repo(namespace)

        qualifiers = list(qualifier_repo.values())

        return self._make_tuple(qualifiers)

    def _fake_getqualifier(self, namespace, **params):
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

        # Validate namespace
        qualifier_repo = self._get_qualifier_repo(namespace)

        qname = params['QualifierName']

        try:
            qualifier = qualifier_repo[qname]
        except KeyError:
            ce = CIMError(
                CIM_ERR_NOT_FOUND,
                _format("Qualifier declaration {0!A} not found in namespace "
                        "{1!A}.", qname, namespace))
            raise ce

        return self._make_tuple([qualifier])

    def _fake_setqualifier(self, namespace, **params):
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

        # TODO:ks FUTURE implement set... method for instance, qualifier, class
        # as general means to put new data into the repo.

        # Validate namespace
        qualifier_repo = self._get_qualifier_repo(namespace)

        qual_decl = params['QualifierDeclaration']
        if not isinstance(qual_decl, CIMQualifierDeclaration):
            raise CIMError(
                CIM_ERR_INVALID_PARAMETER,
                _format("QualifierDeclaration parameter is not a valid "
                        "valid CIMQualifierDeclaration. Rcvd type={0}",
                        type(qual_decl)))

        if qual_decl.name in qualifier_repo:
            raise CIMError(
                CIM_ERR_ALREADY_EXISTS,
                _format("Qualifier declaration {0!A} already exists in "
                        "namespace {1!A}.", qual_decl.name, namespace))

        self._init_qualifier_decl(qual_decl, qualifier_repo)

        qualifier_repo[qual_decl.name] = qual_decl

    def _fake_deletequalifier(self, namespace, **params):
        """
        Implements a server responder for
        :meth:`~pywbem.WBEMConnection.DeleteQualifier`

        Deletes a single qualifier if it is in the
        repository for this class and namespace

        Raises;

            CIMError: CIM_ERR_INVALID_NAMESPACE, CIM_ERR_NOT_FOUND
        """

        # Validate namespace
        qualifier_repo = self._get_qualifier_repo(namespace)

        qname = params['QualifierName']

        if qname in qualifier_repo:
            del qualifier_repo[qname]
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

    def _fake_createinstance(self, namespace, **params):
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

        if self._repo_lite:
            raise CIMError(
                CIM_ERR_NOT_SUPPORTED,
                "CreateInstance not supported when repo_lite set.")

        # Validate parameters
        new_instance = params['NewInstance']
        if not isinstance(new_instance, CIMInstance):
            raise CIMError(
                CIM_ERR_INVALID_PARAMETER,
                _format("NewInstance parameter is not a valid CIMInstance. "
                        "Rcvd type={0}", type(new_instance)))

        # Validate namespace
        instance_repo = self._get_instance_repo(namespace)

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
        # TODO AM 8/18 Generalize the hard coded handling into provider concept
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

            # Write it back to the instance in casde it was changed
            new_instance['Name'] = new_namespace

            # These values must match those in
            # tests/unittest/utils/wbemserver_mock.py.
            new_instance['CreationClassName'] = ns_classname
            new_instance['ObjectManagerName'] = 'MyFakeObjectManager'
            new_instance['ObjectManagerCreationClassName'] = \
                'CIM_ObjectManager'
            new_instance['SystemName'] = 'Mock_Test_WBEMServerTest'
            new_instance['SystemCreationClassName'] = 'CIM_ComputerSystem'

        # Test all key properties in instance. This is our repository limit
        # since the repository cannot add values for key properties. We do
        # no allow creating key properties from class defaults.
        key_props = [p.name for p in six.itervalues(target_class.properties)
                     if 'key' in p.qualifiers]
        for pn in key_props:
            if pn not in new_instance:
                raise CIMError(
                    CIM_ERR_INVALID_PARAMETER,
                    _format("Key property {0!A} not in NewInstance ", pn))

        # If property not in instance, add it from class and use default value
        # from class
        for cprop_name in target_class.properties:
            if cprop_name not in new_instance:
                default_value = target_class.properties[cprop_name]
                new_instance[cprop_name] = default_value

        # Exception if property in instance but not class or types do not
        # match
        for ipname in new_instance:
            if ipname not in target_class.properties:
                raise CIMError(
                    CIM_ERR_INVALID_PARAMETER,
                    _format("Property {0!A} specified in NewInstance is not "
                            "exposed by class {1!A} in namespace {2!A}",
                            ipname, target_class.classname, namespace))

            cprop = target_class.properties[ipname]
            iprop = new_instance.properties[ipname]
            if iprop.is_array != cprop.is_array or \
                    iprop.type != cprop.type:
                raise CIMError(
                    CIM_ERR_INVALID_PARAMETER,
                    _format("Instance and class property {0!A} types "
                            "do not match: instance={1!A}, class={2!A}",
                            ipname, iprop, cprop))

        # Build instance path. We build the complete instance path
        new_instance.path = CIMInstanceName.from_instance(
            target_class,
            new_instance,
            namespace=namespace)

        # Check for duplicate instances
        for inst in instance_repo:
            if inst.path == new_instance.path:
                raise CIMError(
                    CIM_ERR_ALREADY_EXISTS,
                    _format("NewInstance {0!A} already exists in namespace "
                            "{1!A}.", new_instance.path, namespace))

        # Reflect the new namespace in the mock repository
        if ns_classname:
            self.add_namespace(new_namespace)

        # Store the new instance in the mock repository
        instance_repo.append(new_instance)

        # Create instance returns model path, path relative to namespace
        return self._make_tuple([deepcopy(new_instance.path)])

    def _fake_modifyinstance(self, namespace, **params):
        """
        Implements a server responder for
        :meth:`~pywbem.WBEMConnection.CreateInstance`

        Modify a CIM instance in the local repository.

        Raises:

            CIMError: CIM_ERR_ALREADY_EXISTS, CIM_ERR_INVALID_CLASS
        """

        if self._repo_lite:
            raise CIMError(
                CIM_ERR_NOT_SUPPORTED,
                "ModifyInstance not supported when repo_lite set.")

        # Validate namespace
        instance_repo = self._get_instance_repo(namespace)

        modified_instance = deepcopy(params['ModifiedInstance'])
        property_list = params['PropertyList']

        # Return if empty property list
        if property_list is not None and not property_list:
            return

        if modified_instance is not None and not modified_instance:
            return

        if not isinstance(modified_instance, CIMInstance):
            raise CIMError(
                CIM_ERR_INVALID_PARAMETER,
                _format("The ModifiedInstance parameter is not a valid "
                        "CIMInstance. Rcvd type={0}", type(modified_instance)))

        # Classnames in instance and path must match
        if modified_instance.classname != modified_instance.path.classname:
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

        # get key properties and all class props
        cl_props = [p.name for p in six.itervalues(target_class.properties)]
        key_props = [p.name for p in six.itervalues(target_class.properties)
                     if 'key' in p.qualifiers]

        # Get original instance in repo.  Does not copy the orig instance.
        mod_inst_path = modified_instance.path.copy()
        if modified_instance.path.namespace is None:
            mod_inst_path.namespace = namespace

        orig_instance_tup = self._find_instance(mod_inst_path, instance_repo)
        if orig_instance_tup[0] is None:
            raise CIMError(
                CIM_ERR_NOT_FOUND,
                _format("Original Instance {0!A} not found in namespace {1!A}",
                        modified_instance.path, namespace))
        original_instance = orig_instance_tup[1]

        # Remove duplicate properties from property_list
        if property_list:
            if len(property_list) != len(set(property_list)):
                property_list = list(set(property_list))

        # Test that all properties in modified instance and property list
        # are in the class
        if property_list:
            for p in property_list:
                if p not in cl_props:
                    raise CIMError(
                        CIM_ERR_INVALID_PARAMETER,
                        _format("Property {0!A} in PropertyList not in class "
                                "{1!A}", p, modified_instance.classname))
        for p in modified_instance:
            if p not in cl_props:
                raise CIMError(
                    CIM_ERR_INVALID_PARAMETER,
                    _format("Property {0!A} in ModifiedInstance not in class "
                            "{1!A}", p, modified_instance.classname))

        # Set the class value for properties in the property list but not
        # in the modified_instance. This sets just the value component.
        mod_inst_props = set(modified_instance.keys())
        new_props = mod_inst_props.difference(set(cl_props))
        if new_props:
            for new_prop in new_props:
                modified_instance[new_prop] = \
                    target_class.properties[new_prop].value

        # Remove all properties that do not change value between original
        # instance and modified instance
        for p in list(modified_instance):
            if original_instance[p] == modified_instance[p]:
                del modified_instance[p]

        # Confirm no key properties in remaining modified instance
        for p in key_props:
            if p in modified_instance:
                raise CIMError(
                    CIM_ERR_INVALID_PARAMETER,
                    _format("ModifyInstance cannot modify key property {0!A}",
                            p))

        # Remove any properties from modified instance not in the property_list
        if property_list:
            for p in list(modified_instance):
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

        # Modify the value of properties in the repo with those from
        # modified instance
        index = orig_instance_tup[0]
        instance_repo[index].update(modified_instance.properties)
        return

    def _fake_getinstance(self, namespace, **params):
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

        iname = params['InstanceName']
        if iname.namespace is None:
            iname.namespace = namespace

        self._validate_namespace(namespace)

        # If not repo lite, corresponding class must exist.
        if not self._repo_lite:
            if not self._class_exists(iname.classname, namespace):
                raise CIMError(
                    CIM_ERR_INVALID_CLASS,
                    _format("Class {0!A} for GetInstance of instance {1!A} "
                            "does not exist.", iname.classname, iname))

        inst = self._get_instance(iname, namespace,
                                  params['PropertyList'],
                                  params['LocalOnly'],
                                  params['IncludeClassOrigin'],
                                  params['IncludeQualifiers'])

        return self._make_tuple([inst])

    def _fake_deleteinstance(self, namespace, **params):
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

        iname = params['InstanceName']
        iname.namespace = namespace

        # Validate namespace
        instance_repo = self._get_instance_repo(namespace)

        # if not repo_lite, Corresponding class must exist
        if not self._repo_lite:
            if not self._class_exists(iname.classname, namespace):
                raise CIMError(
                    CIM_ERR_INVALID_CLASS,
                    _format("Class {0!A} in namespace {1!A} not found. "
                            "Cannot delete instance {2!A}",
                            iname.classname, namespace, iname))

        del_index = None
        for i, inst in enumerate(instance_repo):
            if iname == inst.path:
                if del_index is not None:
                    raise CIMError(
                        CIM_ERR_FAILED,
                        _format("Internal Error: Invalid Repository. "
                                "Multiple instances with same path {0!A}",
                                inst.path))
                # TODO:ks Future remove this test for duplicate inst paths since
                #       we test for dups on insertion
                del_index = i

        if del_index is None:
            raise CIMError(
                CIM_ERR_NOT_FOUND,
                _format("Instance {0!A} not found in repository namespace "
                        "{1!A}", iname, namespace))

        # Handle namespace deletion, currently hard coded.
        # TODO AM 8/18 Generalize the hard coded handling into provider concept
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

        # Reflect the instance deletion in the mock repository
        del instance_repo[del_index]

    def _fake_enumerateinstances(self, namespace, **params):
        """
        Implements a server responder for
        :meth:`~pywbem.WBEMConnection.EnumerateInstances`.

        Gets a list of subclasses if the classes exist in the repository
        then executes getInstance for each to create the list of instances
        to be returned.

        Raises:

            CIMError: CIM_ERR_INVALID_NAMESPACE
        """

        # Validate namespace
        instance_repo = self._get_instance_repo(namespace)

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
        lo = params['LocalOnly']

        if not self._repo_lite:
            # gets class propertylist which is may be localonly or all
            # superclasses
            cl = self._get_class(cname, namespace, local_only=lo)
            class_pl = cl.properties.keys()
        else:
            class_pl = None

        # if not lite repo and not di compute property list to filter
        # all instances to the properties in the target class as modified
        # by the PropertyList
        if not self._repo_lite:
            if not di:
                if pl is None:
                    pl = class_pl
                else:      # reduce pl to properties in class_properties
                    pl = [pc for pc in class_pl if pc in pl]

        clns_dict = self._get_subclass_list_for_enums(cname, namespace)
        insts = [self._get_instance(inst.path, namespace,
                                    pl,
                                    None,  # LocalOnly never gets passed
                                    params['IncludeClassOrigin'],
                                    params['IncludeQualifiers'])
                 for inst in instance_repo if inst.path.classname in clns_dict]

        return self._make_tuple(insts)

    def _fake_enumerateinstancenames(self, namespace, **params):
        """
        Implements a server responder for
        :meth:`~pywbem.WBEMConnection.EnumerateInstanceNames`

        Get instance names for instances that match the path define
        by `ClassName` and returns a list of the names.
        """
        cname = params['ClassName']
        assert isinstance(cname, CIMClassName)
        cname = cname.classname

        # Validate namespace
        instance_repo = self._get_instance_repo(namespace)

        clns = self._get_subclass_list_for_enums(cname, namespace)

        inst_paths = [inst.path for inst in instance_repo
                      if inst.path.classname in clns]

        rtn_paths = [deepcopy(path) for path in inst_paths]

        return self._make_tuple(rtn_paths)

    def _fake_execquery(self, namespace, **params):
        # pylint: disable=unused-argument
        """
        Implements a mock WBEM server responder for
            :meth:`~pywbem.WBEMConnection.ExecQuery`

        Executes the equilavent of the WBEMConnection ExecQuery for
        the querylanguage and query defined
        """

        self._validate_namespace(namespace)

        raise CIMError(
            CIM_ERR_NOT_SUPPORTED,
            "ExecQuery not implemented!")

    #####################################################################
    #
    #  Faked WBEMConnection Reference and Associator methods
    #
    #####################################################################

    @staticmethod
    def _appendpath_unique(list_, path):
        """Append path to list if not already in list"""
        for p in list_:
            if p == path:
                return
        list_.append(path)

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

    def _classnamelist(self, classname, namespace):
        """Build a list of this class and its subclasses if classname is
           a string/CIMClassName or an empty list if classname is None.

           Differs from _get_subclass_names in that it includes classname and
           that it returns None if there is no classname
        """
        if not classname:
            return []

        cn = classname.classname if isinstance(classname, CIMClassName) \
            else classname
        result = self._get_subclass_names(cn, namespace, True)
        result.append(classname)
        return result

    def _classnamedict(self, classname, namespace):
        """Get from _classnamelist and cvt to NocaseDict"""
        clns = self._classnamelist(classname, namespace)
        rtn_dict = NocaseDict()
        for cln in clns:
            rtn_dict[cln] = cln
        return rtn_dict

    @staticmethod
    def _ref_prop_matches(prop, target_classname, ref_classname,
                          resultclass_names, role):
        """
        Test filters for a reference property
        Returns `True` if matches the criteria.

        Returns `False` if it does not match.

        The match criteria are:
          - target_classname == prop_reference_class
          - if result_classes are not None, ref_classname is in result_classes
          - If role is not None, prop name matches role
        """
        assert prop.type == 'reference'
        if prop.reference_class.lower() == target_classname.lower():
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
        property name
        """
        assert prop.type == 'reference'

        if assoc_classes and ref_classname not in assoc_classes:
            return False
        if result_classes and prop.reference_class not in result_classes:
            return False
        if result_role and prop.name.lower() != result_role:
            return False
        return True

    def _get_reference_classnames(self, classname, namespace,
                                  resultclass_name, role):
        """
        Get list of classnames that are references for which this classname
        is a target filtered by the result_class and role parameters if they
        are none.
        This is a common method used by all of the other reference and
        associator methods to create a list of reference classnames

        Returns:
            list of classnames that satisfy the criteria.
        """

        self._validate_namespace(namespace)

        result_classes = self._classnamedict(resultclass_name, namespace)

        rtn_classnames_set = set()
        role = role.lower() if role else role

        for cl in self._get_association_classes(namespace):
            for prop in six.itervalues(cl.properties):
                if prop.type == 'reference' and \
                        self._ref_prop_matches(prop, classname,
                                               cl.classname,
                                               result_classes,
                                               role):
                    rtn_classnames_set.add(cl.classname)
        return list(rtn_classnames_set)

    def _get_reference_instnames(self, instname, namespace, resultclass_name,
                                 role):
        """
        Get the reference instances from the repository for the target
        instname and filtered by the result_class and role parameters.

        Returns a list of the reference instance names. The returned list is
        the original, not a copy so the user must copy them
        """
        instance_repo = self._get_instance_repo(namespace)

        if resultclass_name:
            # if there is a class repository get subclasses
            if self._get_class_repo(namespace):
                resultclass_dict = self._classnamedict(resultclass_name,
                                                       namespace)
            else:
                resultclass_dict = NocaseDict(resultclass_name=resultclass_name)
        else:
            resultclass_dict = NocaseDict()

        instname.namespace = namespace
        rtn_instpaths = []
        role = role.lower() if role else role
        # TODO:ks FUTURE: Make list from _get_reference_classnames if classes
        #       exist. Otherwise set list to instance_repo to search every
        #       instance.
        for inst in instance_repo:
            for prop in six.itervalues(inst.properties):
                if prop.type == 'reference':
                    # does this prop instance name match target inst name
                    if prop.value == instname:
                        if resultclass_name:
                            if inst.classname not in resultclass_dict:
                                continue
                        if role and prop.name.lower() != role:
                            continue

                        self._appendpath_unique(rtn_instpaths, inst.path)

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
        class_repo = self._get_class_repo(namespace)

        result_classes = self._classnamedict(result_class, namespace)
        assoc_classes = self._classnamedict(assoc_class, namespace)

        rtn_classnames_set = set()

        role = role.lower() if role else role
        result_role = result_role.lower() if result_role else result_role

        ref_clns = self._get_reference_classnames(classname, namespace,
                                                  assoc_class, role)

        cls = [class_repo[cln] for cln in ref_clns]
        for cl in cls:
            for prop in six.itervalues(cl.properties):
                if prop.type == 'reference':
                    if self._assoc_prop_matches(prop,
                                                cl.classname,
                                                assoc_classes,
                                                result_classes,
                                                result_role):

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
        instance_repo = self._get_instance_repo(namespace)
        result_classes = self._classnamedict(result_class, namespace)
        assoc_classes = self._classnamedict(assoc_class, namespace)

        inst_name.namespace = namespace
        rtn_instpaths = []
        role = role.lower() if role else role
        result_role = result_role.lower() if result_role else result_role

        ref_paths = self._get_reference_instnames(inst_name, namespace,
                                                  assoc_class, role)
        # Get associated instance names
        for ref_path in ref_paths:
            inst = self._find_instance(ref_path, instance_repo)[1]
            for prop in six.itervalues(inst.properties):
                if prop.type == 'reference':
                    if prop.value == inst_name:
                        if assoc_class and inst.classname not in assoc_classes:
                            continue
                        if role and prop.name.lower() != role:
                            continue
                    else:
                        if result_class and (prop.value.classname
                                             not in result_classes):
                            continue
                        if result_role and prop.name.lower() != result_role:
                            continue
                        self._appendpath_unique(rtn_instpaths, prop.value)

        return rtn_instpaths

    def _fake_referencenames(self, namespace, **params):
        """
        Implements a mock WBEM server responder for
        :meth:`~pywbem.WBEMConnection.ReferenceNames`
        """
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
                                                            rc, role)

            ref_result = [CIMClassName(classname=cn, host=self.host,
                                       namespace=namespace)
                          for cn in ref_classnames]

            return self._return_assoc_tuple(ref_result)

        assert isinstance(obj_name, CIMInstanceName)
        ref_paths = self._get_reference_instnames(obj_name, namespace,
                                                  rc, role)
        rtn_names = [deepcopy(r) for r in ref_paths]

        for iname in rtn_names:
            if iname.host is None:
                iname.host = self.host

        return self._return_assoc_tuple(rtn_names)

    def _fake_references(self, namespace, **params):
        """
        Implements a mock WBEM server responder for
        :meth:`~pywbem.WBEMConnection.References`
        """
        rc = None if params['ResultClass'] is None else \
            params['ResultClass'].classname
        role = params['Role']
        obj_name = params['ObjectName']
        classname = obj_name.classname
        pl = params['PropertyList']
        ico = params['IncludeClassOrigin']
        iq = params['IncludeQualifiers']

        if isinstance(obj_name, CIMClassName):
            rtn_classnames = self._get_reference_classnames(
                classname, namespace, rc, role)
            # returns list of tuples of (CIMClassname, CIMClass)
            return self._return_assoc_class_tuples(rtn_classnames, namespace,
                                                   iq, ico, pl)

        assert isinstance(obj_name, CIMInstanceName)
        ref_paths = self._get_reference_instnames(obj_name, namespace, rc,
                                                  role)
        rtn_insts = []
        for path in ref_paths:
            rtn_insts.append(self._get_instance(
                path, namespace, None,
                params['PropertyList'],
                params['IncludeClassOrigin'],
                params['IncludeQualifiers']))

        for inst in rtn_insts:
            if inst.path.host is None:
                inst.path.host = self.host

        return self._return_assoc_tuple(rtn_insts)

    def _fake_associatornames(self, namespace, **params):
        # pylint: disable=invalid-name
        """
        Implements a mock WBEM server responder for
        :meth:`~pywbem.WBEMConnection.AssociatorNames`
        """

        self._validate_namespace(namespace)

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
        results = [deepcopy(p) for p in rtn_paths]

        for iname in results:
            if iname.host is None:
                iname.host = self.host

        return self._return_assoc_tuple(results)

    def _fake_associators(self, namespace, **params):
        """
        Implements a mock WBEM server responder for
            :meth:`~pywbem.WBEMConnection.Associators`
        """

        self._validate_namespace(namespace)

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
        iq = params['IncludeQualifiers']

        if isinstance(obj_name, CIMClassName):
            rtn_classnames = self._get_associated_classnames(classname,
                                                             namespace,
                                                             ac, rc,
                                                             result_role, role)
            # returns list of tuples of (CIMClassname, CIMClass)
            return self._return_assoc_class_tuples(rtn_classnames, namespace,
                                                   iq, ico, pl)

        assert isinstance(obj_name, CIMInstanceName)
        assoc_names = self._get_associated_instancenames(obj_name,
                                                         namespace,
                                                         ac, rc,
                                                         result_role, role)
        results = []
        for obj_name in assoc_names:
            results.append(self._get_instance(
                obj_name, namespace, None,
                params['PropertyList'],
                params['IncludeClassOrigin'],
                params['IncludeQualifiers']))

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
            # TODO:ks Future. Use the timeout along with response delay. Then
            # user could timeout pulls. This means adding timer test to
            # pulls and close. Timer should be used to close old contexts
            # also.
            self.enumeration_contexts[context_id] = {'pull_type': pull_type,
                                                     'data': objects,
                                                     'namespace': namespace,
                                                     'time': time.clock(),
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

        self._validate_namespace(namespace)

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

    def _fake_openenumerateinstancepaths(self, namespace, **params):
        # pylint: disable=invalid-name
        """
        Implements WBEM server responder for
        :meth:`~pywbem.WBEMConnection.OpenEnumerationInstancePaths`
        with data from the instance repository.
        """
        self._validate_namespace(namespace)
        self._validate_open_params(**params)

        result_t = self._fake_enumerateinstancenames(namespace, **params)

        return self._open_response(result_t[0][2], namespace,
                                   'PullInstancePaths', **params)

    def _fake_openenumerateinstances(self, namespace, **params):
        """
        Implements WBEM server responder for
        :meth:`~pywbem.WBEMConnection.OpenEnumerationInstances`
        with data from the instance repository.
        """
        self._validate_namespace(namespace)
        self._validate_open_params(**params)

        result_t = self._fake_enumerateinstances(namespace, **params)

        return self._open_response(result_t[0][2], namespace,
                                   'PullInstancesWithPath', **params)

    def _fake_openreferenceinstancepaths(self, namespace, **params):
        # pylint: disable=invalid-name
        """
        Implements WBEM server responder for
        :meth:`~pywbem.WBEMConnection.OpenReferenceInstancePaths`
        with data from the instance repository.
        """
        self._validate_namespace(namespace)
        self._validate_open_params(**params)
        params['ObjectName'] = params['InstanceName']
        del params['InstanceName']

        result = self._fake_referencenames(namespace, **params)

        objects = [] if result is None else [x[2] for x in result[0][2]]

        return self._open_response(objects, namespace,
                                   'PullInstancePaths', **params)

    def _fake_openreferenceinstances(self, namespace, **params):
        """
        Implements WBEM server responder for
        :meth:`~pywbem.WBEMConnection.OpenReferenceInstances`
        with data from the instance repository.
        """
        self._validate_namespace(namespace)
        self._validate_open_params(**params)
        params['ObjectName'] = params['InstanceName']
        del params['InstanceName']

        result = self._fake_references(namespace, **params)

        objects = [] if result is None else [x[2] for x in result[0][2]]

        return self._open_response(objects, namespace,
                                   'PullInstancesWithPath', **params)

    def _fake_openassociatorinstancepaths(self, namespace, **params):
        # pylint: disable=invalid-name
        """
        Implements WBEM server responder for
        :meth:`~pywbem.WBEMConnection.OpenAssociatorInstancePaths`
        with data from the instance repository.
        """
        self._validate_namespace(namespace)
        self._validate_open_params(**params)
        params['ObjectName'] = params['InstanceName']
        del params['InstanceName']

        result = self._fake_associatornames(namespace, **params)

        objects = [] if result is None else [x[2] for x in result[0][2]]

        return self._open_response(objects, namespace,
                                   'PullInstancePaths', **params)

    def _fake_openassociatorinstances(self, namespace, **params):
        """
        Implements WBEM server responder for
        WBEMConnection.OpenAssociatorInstances
        with data from the instance repository.
        """
        self._validate_namespace(namespace)
        self._validate_open_params(**params)
        params['ObjectName'] = params['InstanceName']
        del params['InstanceName']

        result = self._fake_associators(namespace, **params)

        objects = [] if result is None else [x[2] for x in result[0][2]]

        return self._open_response(objects, namespace,
                                   'PullInstancesWithPath', **params)

    def _fake_openqueryinstances(self, namespace, **params):
        # pylint: disable=invalid-name
        """
        Implements WBEM server responder for
        :meth:`~pywbem.WBEMConnection.OpenQueryInstances`
        with data from the instance repository.
        """
        self._validate_namespace(namespace)
        self._validate_open_params(**params)

        # pylint: disable=assignment-from-no-return
        # TODO: Not implemented
        result = self._fake_execquery(namespace, **params)

        objects = [] if result is None else [x[2] for x in result[0][2]]

        return self._open_response(objects, namespace,
                                   'PullInstancesWithPath', **params)

    def _fake_pullinstanceswithpath(self, namespace, **params):
        """
        Implements WBEM server responder for
        :meth:`~pywbem.WBEMConnection.OpenPullInstancesWithPath`
        with data from the instance repository.
        """
        return self._pull_response(namespace, 'PullInstancesWithPath',
                                   **params)

    def _fake_pullinstancepaths(self, namespace, **params):
        """
        Implements WBEM server responder for
        :meth:`~pywbem.WBEMConnection.OpenPullInstancePaths`
        with data from the instance repository.
        """
        return self._pull_response(namespace, 'PullInstancePaths', **params)

    def _fake_pullinstances(self, namespace, **params):
        """
        Implements WBEM server responder for
        :meth:`~pywbem.WBEMConnection.OpenPullInstances`
        with data from the instance repository.
        """
        return self._pull_response(namespace, 'PullInstances', **params)

    def _fake_closeenumeration(self, namespace, **params):
        """
            Implements WBEM server responder for
            :meth:`~pywbem.WBEMConnection.CloseEnumeration`
            with data from the instance repository.

            If the EnumerationContext is valid it removes it from the
            context repository. Otherwise it returns an exception.
        """
        self._validate_namespace(namespace)

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
            localobject = deepcopy(objectname)
            if localobject.namespace is None:
                localobject.namespace = self.default_namespace
                localobject.host = None

        elif isinstance(objectname, six.string_types):
            # a string is always interpreted as a class name
            localobject = CIMClassName(objectname,
                                       namespace=self.default_namespace)

        else:
            raise TypeError(
                _format("FakedWBEMConnection InvokeMethod invalid type for "
                        "objectname: {0!A}", type(objectname)))

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
            # TODO FUTURE: add method to repo that allows privileged users
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
                    raise CIMError(
                        CIM_ERR_INVALID_PARAMETER,
                        _format("InvokeMethod Param {0!A} invalid type, "
                                "{1}. Expected tuple or CIMParameter",
                                param, type(param)))

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

        except Exception as ex:
            exc_type, exc_value, exc_traceback = sys.exc_info()
            tb = repr(traceback.format_exception(exc_type, exc_value,
                                                 exc_traceback))

            raise CIMError(
                CIM_ERR_FAILED,
                _format("Exception failure of invoked method {0!A} in "
                        "namespace {1!A} with input localobject {2!A}, "
                        "parameters {3!A}. Exception: {4}\n"
                        "Traceback\n{5}",
                        methodname, namespace, localobject, params, ex, tb))

        # test for valid data in response.
        if not isinstance(result, (list, tuple)):
            raise CIMError(
                CIM_ERR_FAILED,
                _format("Callback method returned {0} response type. "
                        "Expected list or tuple", type(result)))
        for param in result[1]:
            if not isinstance(param, CIMParameter):
                raise CIMError(
                    CIM_ERR_FAILED,
                    _format("Callback method returned {0} response type. "
                            "Expected CIMParameter.", type(param)))

        # Map output params to NocaseDict to be compatible with return
        # from _methodcall. The input list is just CIMParameters
        output_params = NocaseDict()
        for param in result[1]:
            output_params[param.name] = param.value

        return (result[0], output_params)
