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
    CIM_ERR_INVALID_SUPERCLASS, CIM_ERR_INVALID_PARAMETER, \
    CIM_ERR_INVALID_CLASS, CIM_ERR_ALREADY_EXISTS, \
    CIM_ERR_INVALID_NAMESPACE, CIM_ERR_INVALID_ENUMERATION_CONTEXT, \
    CIM_ERR_NOT_SUPPORTED, CIM_ERR_QUERY_LANGUAGE_NOT_SUPPORTED, \
    DEFAULT_NAMESPACE, MOFCompiler, MOFWBEMConnection
from pywbem._nocasedict import NocaseDict
from ._dmtf_cim_schema import DMTFCIMSchema

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

    Text must be a unicode string and must not be None.

    If dest is a file path, the text is encoded to a UTF-8 Byte sequence and
    is appended to the file (opening and closing the file).

    If dest is None, the text is encoded to a codepage suitable for the current
    stdout and is written to stdout.
    """
    assert isinstance(text, six.text_type)
    if dest is None:
        btext = text.encode(STDOUT_ENCODING, 'replace')
        if six.PY3:
            print(btext.decode(STDOUT_ENCODING))
        else:
            print(btext)
    else:
        if six.PY2:
            # Open with codecs to define text mode
            with codecs.open(dest, mode='a', encoding='utf-8') as f:
                print(text, file=f)
        else:
            with open(dest, 'a', encoding='utf-8') as f:
                print(text, file=f)


def method_callback_interface(conn, objectname, methodname, **params):
    # pylint: disable=unused-argument, invalid-name, line-too-long
    """
    **Experimental:** *New in pywbem 0.12 as experimental.*

    Interface for user-provided callback functions for CIM method invocation
    on a faked connection.

    Parameters:

      conn (:class:`~pywbem_mock.FakedWBEMConnection`):
        Faked connection. This can be used to access the mock repository of the
        faked connection, via its operation methods (e.g. `GetClass`).

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

      methodname (:term:`string`):
        The CIM method name that is being invoked. This is the method name for
        which the callback function was registered. This parameter allows a
        single callback function to be registered for multiple methods.

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


class FakedWBEMConnection(WBEMConnection):
    """
    **Experimental:** *New in pywbem 0.12 as experimental.*

    A subclass of :class:`pywbem.WBEMConnection` that mocks the communication
    with a WBEM server by utilizing a local in-memory *mock repository* to
    generate responses in the same way the WBEM server would.

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

        # The CIM classes in the mock repository.
        # This is a dictionary of dictionaries where the top level key is the
        # CIM namespace name and the keys for each sub-dictionary in a
        # namespace are class names, and the values in each sub-dictionary are
        # the CIM classes in that namespace, represented as CIMClass objects.
        # The dictionaries are NocaseDict since namespaces should be case
        # insensitive.
        self.classes = NocaseDict()

        # The CIM qualifier types in the mock repository.
        # Same format as for classes above, except that the values in each
        # sub-dictionary are CIMQualifierDeclaration objects.
        self.qualifiers = NocaseDict()

        # The CIM instances in the mock repository.
        # Because instances do not have a name, the format is slightly
        # different: This is a dictionary of lists where the top level key is
        # the CIM namespace name and the value is a list of CIM instances in
        # that namespace, represented as CIMInstance objects.
        # TODO: ks. FUTURE maybe we should really have a subdict per class but
        #           it is not important for initial release.
        self.instances = NocaseDict()

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
          same-named constructor parameter.
        """
        return self._response_delay

    @response_delay.setter
    def response_delay(self, delay):
        """Setter method; for a description see the getter method."""
        if isinstance(delay, (int, float)) and delay >= 0 or delay is None:
            self._response_delay = delay
        else:
            raise ValueError("Invalid value for response_delay: %r, must be "
                             "a positive number" % delay)

    def __repr__(self):
        return '%s(response_delay=%s, WBEMConnection(%r))' % \
            (self.__class__.__name__, self.response_delay,
             super(FakedWBEMConnection, self).__repr__())

    ################################################################
    #
    #   Methods to insert data into mock repository
    #
    ################################################################

    def compile_mof_file(self, mof_file, namespace=None, search_paths=None,
                         verbose=None):
        """
        Compile the MOF definitions in the specified file (and its included
        files) and add the resulting CIM objects to the specified namespace
        of the mock repository.

        If the CIM namespace does not exist, it is created.

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

          :exc:`~pywbem.CIMError`: Failure related to the CIM objects in the
            mock repository.
        """

        if namespace is None:
            namespace = self.default_namespace

        mofcomp = MOFCompiler(MOFWBEMConnection(),
                              search_paths=search_paths,
                              verbose=verbose)
        mof_repo = mofcomp.handle
        self._setup_mof_repo(mof_repo)

        mofcomp.compile_file(mof_file, namespace)

        self._merge_repos(mof_repo)

    def compile_mof_string(self, mof_str, namespace=None, search_paths=None,
                           verbose=None):
        """
        Compile the MOF definitions in the specified string and add the
        resulting CIM objects to the specified namespace of the mock
        repository.

        If the CIM namespace does not exist, it is created.

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

          :exc:`~pywbem.CIMError`: Failure related to the CIM objects in the
            mock repository.
        """

        if namespace is None:
            namespace = self.default_namespace

        # TODO:ks Future we might be able to use our own MOFWBEMRepository to
        # directly insert into our repository instead of copying them
        # after the compile.
        mofcomp = MOFCompiler(MOFWBEMConnection(),
                              search_paths=search_paths,
                              verbose=verbose)

        mof_repo = mofcomp.handle
        self._setup_mof_repo(mof_repo)

        mofcomp.compile_string(mof_str, namespace)

        self._merge_repos(mof_repo)

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

        If the CIM namespace does not exist, it is created.

        The method imposes very few limits on the objects added. It does
        require that the superclass exist for any class added and that
        instances added include a path component.

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
        """  # noqa: E501
        # pylint: enable=line-too-long

        if namespace is None:
            namespace = self.default_namespace

        if isinstance(objects, list):
            for obj in objects:
                self.add_cimobjects(obj, namespace=namespace)

        else:
            obj = objects
            if isinstance(obj, CIMClass):
                cc = deepcopy(obj)
                if cc.superclass:
                    if not self._class_exists(cc.superclass, namespace):
                        raise ValueError('Class %s defines superclass %s but '
                                         'the superclass does not exist in the '
                                         'repository.' % (cc.classname,
                                                          cc.superclass))
                try:
                    # The following generates an exception for each new ns
                    self.classes[namespace][cc.classname] = cc
                except KeyError:
                    self.classes[namespace] = NocaseDict({cc.classname: cc})

            elif isinstance(obj, CIMInstance):
                inst = deepcopy(obj)
                if inst.path is None:
                    raise ValueError("Instances added must include a path. "
                                     "Instance %r does not include a path" %
                                     inst)
                if inst.path.namespace is None:
                    inst.path.namespace = namespace
                if inst.path.host is not None:
                    inst.path.host = None
                try:
                    inst_repo = self._get_instance_repo(namespace)
                    if self._find_instance(inst.path, inst_repo)[1] is not None:
                        raise ValueError('The instance %s already exists in '
                                         'namespace %s' % (inst, namespace))
                    self.instances[namespace].append(inst)
                except CIMError as ce:
                    if ce.status_code == CIM_ERR_INVALID_NAMESPACE:
                        self.instances[namespace] = [inst]
                    else:
                        raise CIMError(CIM_ERR_FAILED, 'Internal failure of '
                                       'add_cimobject operation. Rcvd '
                                       ' CIMError %s' % ce)

            elif isinstance(obj, CIMQualifierDeclaration):
                qual = deepcopy(obj)
                try:
                    self.qualifiers[namespace][qual.name] = qual
                except KeyError:
                    self.qualifiers[namespace] = NocaseDict({qual.name: qual})
            else:
                assert False, 'Object to add_cimobjects. %s invalid type' \
                              % type(obj)

    def add_method_callback(self, classname, methodname, method_callback,
                            namespace=None,):
        """
        Register a callback function for a CIM method that will be called when
        the CIM method is invoked via `InvokeMethod`.

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
        """

        if namespace is None:
            namespace = self.default_namespace

        if namespace not in self.methods:
            self.methods[namespace] = NocaseDict()

        if classname not in self.methods[namespace]:
            self.methods[namespace][classname] = NocaseDict()

        if methodname in self.methods[namespace][classname]:
            raise ValueError("Duplicate method specification")
        self.methods[namespace][classname][methodname] = method_callback

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
            raise ValueError('Invalid output format definition %s. '
                             '%s are valid.' % (output_format, OUTPUT_FORMATS))

        _uprint(dest, u'%s========Mock Repo Display fmt=%s namespaces=%s '
                      '=========%s\n' %
                (cmt_begin, output_format,
                 ('all' if namespaces is None else namespaces), cmt_end))

        # get all namespaces
        repo_ns = []
        if self.classes:
            repo_ns.extend([ns for ns in self.classes])
        if self.instances:
            repo_ns.extend([ns for ns in self.instances])
        if self.qualifiers:
            repo_ns.extend([ns for ns in self.qualifiers])
        if self.methods:
            repo_ns.extend([ns for ns in self.methods])
        repo_nss = set(repo_ns)

        if namespaces:
            if isinstance(namespaces, six.string_types):
                namespaces = [namespaces]

            repo_nss = repo_nss.intersection(set(namespaces))
        repo_nss = sorted(repo_nss)

        for ns in repo_nss:
            _uprint(dest, u'\n%sNAMESPACE %s%s\n' % (cmt_begin, ns, cmt_end))
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
    def _display_objects(obj_type, objects_repo, namespace, cmt_begin, cmt_end,
                         dest=None, summary=None, output_format=None):
        """
        Display a set of objects of obj_type from the dictionary defined
        by the parameter objects_dict. obj_type is a string that defines the
        type of object (instance, class, qualifier declaration).

        """
        # TODO:ks FUTURE Consider sorting to perserve order of compile/add.
        if namespace in objects_repo:
            if obj_type == 'Methods':
                _uprint(dest, u'%sNamespace %s: contains %s %s:%s\n' %
                        (cmt_begin, namespace,
                         len(objects_repo[namespace]),
                         obj_type, cmt_end))
            else:
                _uprint(dest, u'%sNamespace %s: contains %s %s %s\n' %
                        (cmt_begin, namespace,
                         len(objects_repo[namespace]), obj_type, cmt_end))
            if summary:
                return
            # instances are special because the inner struct is a list
            if obj_type == 'Instances':
                try:
                    insts = objects_repo[namespace]
                except KeyError:
                    return

                # TODO:ks Future: Possibly sort insts by path order.
                for inst in insts:
                    if output_format == 'xml':
                        _uprint(dest, u'%s Path=%s %s\n%s' %
                                (cmt_begin, inst.path.to_wbem_uri(), cmt_end,
                                 _pretty_xml(inst.tocimxmlstr())))
                    elif output_format == 'repr':
                        _uprint(dest, u'Path:\n%r\nInst:\n%r\n' %
                                (inst.path, inst))
                    else:
                        _uprint(dest, u'%s Path=%s %s\n%s' %
                                (cmt_begin, inst.path.to_wbem_uri(), cmt_end,
                                 inst.tomof()))

            elif obj_type == 'Methods':
                try:
                    methods = objects_repo[namespace]

                except KeyError:
                    return

                for cln in methods:
                    for method in methods[cln]:
                        _uprint(dest, u'%sClass: %s, method: %s, '
                                      'callback: %s %s' %
                                (cmt_begin, cln, method,
                                 methods[cln][method].__name__, cmt_end))
            else:
                # Covers QualifierDeclarations and Classes
                try:
                    objs = objects_repo[namespace]
                except KeyError:
                    return
                for key in sorted(objs):
                    obj = objs[key]
                    if output_format == 'xml':
                        _uprint(dest, _pretty_xml(obj.tocimxmlstr()))
                    elif output_format == 'repr':
                        _uprint(dest, u'%r' % obj)
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

    def _setup_mof_repo(self, repo):
        """
        Move our repo to the mofcompile repo to provide a basis
        for the compile.
        """
        repo.classes = deepcopy(self.classes)
        repo.qualifiers = deepcopy(self.qualifiers)
        repo.instances = deepcopy(self.instances)

    def _merge_repos(self, repo):
        """
        Move objects from the repo repository to the self repository. Since the
        setup copied all existing objects to the compile repo, this clears
        the repository and them copies all of them back.

        """
        if repo.classes:
            self.classes.clear()
            for ns in repo.classes:
                for cl in six.itervalues(repo.classes[ns]):
                    try:
                        self.classes[ns][cl.classname] = \
                            repo.classes[ns][cl.classname].copy()
                    except KeyError:
                        self.classes[ns] = NocaseDict({cl.classname: cl})
        if repo.instances:
            self.instances.clear()
            for ns, insts in six.iteritems(repo.instances):
                for inst in insts:
                    if inst.path is None:
                        # use GetClass to get all properties
                        cc = self.GetClass(inst.classname, namespace=ns,
                                           LocalOnly=False,
                                           IncludeQualifiers=True,
                                           IncludeClassOrigin=True)
                        inst.path = CIMInstanceName.from_instance(cc, inst, ns)
                    try:
                        self.instances[ns].append(inst)
                    except KeyError:
                        self.instances[ns] = [inst]
        if repo.qualifiers:
            self.qualifiers.clear()
            for ns in repo.qualifiers:
                for qual in six.itervalues(repo.qualifiers[ns]):
                    try:
                        self.qualifiers[ns][qual.name] = \
                            repo.qualifiers[ns][qual.name].copy()
                    except KeyError:
                        self.qualifiers[ns] = NocaseDict({qual.name: qual})

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
        return True if classname in class_repo else False

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

    @staticmethod
    def _validate_repo(namespace, repo_dict, repo_type):
        """
        Common method to validate existence of namespace for defined
        repo_dict.

        Returns the dictionary for this namespace if valid
        """
        if namespace not in repo_dict:
            raise CIMError(CIM_ERR_INVALID_NAMESPACE,
                           'Namespace %r not found for %r' % (namespace,
                                                              repo_type))
        return repo_dict[namespace]

    def _get_class_repo(self, namespace):
        """
        Validates that the class repository for the input namespaces exists
        and if it does, returns the handle to that repository. If the
        repo for namespace does not exist, it generates a CIM_Error

        The class repository is a NocaseDict with class as key and
        the CIMClass as value.

        Parameters:

          namespace(:term:`string`):
              String containing the name of the namespace to get

        Returns:
          Dictionary containing classes that have been inserted
          into the repository

        Raises:
          CIM_Error, CIM_ERR_INVALID_NAMESPACE if this namespace
          does not exist in the  classrepository
        """
        return self._validate_repo(namespace, self.classes, 'classes')

    def _get_instance_repo(self, namespace):
        """
        Validates that the instance repository for the input namespaces exists
        and if it does, returns the handle to that repository. If the
        repo for namespace does not exist, it generates a CIM_Error

        The instance repository is a list if instances within the
        defined namespace

        Parameters:

          namespace(:term:`string`):
            String containing the name of the namespace to get

        Returns: List of instances

        Raises:
           CIM_Error, CIM_ERR_INVALID_NAMESPACE if this namespace
          does not exist in the  classrepository
        """
        if namespace not in self.instances:
            # create empty instance repo if there is a class repo for the
            # namespace. Existence of the class repo should imply existence
            # of instance repo
            if self._get_class_repo(namespace):
                self.instances[namespace] = []
                if namespace not in self.methods:
                    self.methods[namespace] = NocaseDict()

        return self._validate_repo(namespace, self.instances, 'instances')

    def _get_qualifier_repo(self, namespace):
        """
        Validates that the qualifier repository for the input namespaces exists
        and if it does, returns the handle to that repository. If the
        repo for namespace does not exist, it generates a CIM_Error

        The instance repository is a list if instances within the
        defined namespace

        Parameters:

          namespace(:term:`string`):
              String containing the name of the namespace to get

        Returns:
           Dictionary of QualifierDeclaration objects in the repo

        Raises:
          CIM_Error: CIM_ERR_INVALID_NAMESPACE if this namespace
          does not exist in the  classrepository
        """
        return self._validate_repo(namespace, self.qualifiers, 'qualifiers')

    def _get_methods_repo(self, namespace=None):
        """
        Validate that the table of methods exists for this namespace and if
        it does, return the handle to the dictionary that represents the
        methods defined for this namespce.  If that repo does not exist,
        generate a CIM_Error.
        """
        return self._validate_repo(namespace, self.methods, 'methods')

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
        if classname is None:
            rtn_classnames = [
                cl.classname for cl in six.itervalues(self.classes[namespace])
                if cl.superclass is None]
        else:
            rtn_classnames = [
                cl.classname for cl in six.itervalues(self.classes[namespace])
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
        classes_repo = self._get_class_repo(namespace)

        # try to get the target class and create a copy for response
        try:
            cc = deepcopy(classes_repo[classname])
            # local properties and methods are marked not propagated.
            for prop in cc.properties.values():
                prop.propagated = False
            for method in cc.properties.values():
                method.propagated = False
        except KeyError:
            raise CIMError(CIM_ERR_NOT_FOUND, 'Class %r not found in '
                                              'namespace %r.' %
                           (classname, namespace))

        if not local_only and cc.superclass:
            sc_name = cc.superclass
            super_class = None
            while sc_name:
                try:
                    super_class = classes_repo[sc_name]
                except KeyError:
                    cx = cc if super_class is None else super_class
                    raise CIMError(CIM_ERR_INVALID_SUPERCLASS,
                                   'Class %r has invalid superclass %r.' %
                                   (cx.classname, sc_name))
                for prop in super_class.properties.values():
                    if prop.name not in cc.properties:
                        cc.properties[prop.name] = deepcopy(prop)
                        cc.properties[prop.name].propagated = True
                for meth in super_class.methods.values():
                    if meth.name not in cc.methods:
                        cc.methods[meth.name] = deepcopy(meth)
                        cc.methods[meth.name].propagated = True

                sc_name = super_class.superclass

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

        Returns: Returns generator where each yield returns a singe
                 association class
        """
        class_repo = self._get_class_repo(namespace)
        # associator_classes = []
        for cl in six.itervalues(class_repo):
            if 'Association' in cl.qualifiers:
                yield cl
        return

    @staticmethod
    def _find_instance(iname, inst_repo):
        """
        Find an instance in the instance repo by iname and return the
        index of that instance.

        Parameters:

          iname: CIMInstancename to find

          inst_repo: the instance repo to search

        Return (None, None if not found. Otherwise return tuple of
               index, instance

        Raises:

          CIMError: Failed if repo invalid.
        """
        rtn_inst = None
        rtn_index = None
        for index, inst in enumerate(inst_repo):
            if iname == inst.path:
                if rtn_inst is not None:
                    # TODO:ks Future Remove dup test since we should be
                    # insuring no dups on instance creation
                    raise CIMError(CIM_ERR_FAILED, 'Invalid Repository. '
                                   'Multiple instances with same path %r.'
                                   % rtn_inst.path)
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
        inst_repo = self._get_instance_repo(namespace)

        rtn_tup = self._find_instance(iname, inst_repo)
        inst = rtn_tup[1]

        if inst is None:
            raise CIMError(CIM_ERR_NOT_FOUND,
                           'Instance not found in repository namespace %r. '
                           'Path=%r' % (namespace, iname))
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
                    raise CIMError(CIM_ERR_INVALID_CLASS, 'Class %r not found'
                                   ' for instance %r in namespace %r.' %
                                   (iname.classname, iname, namespace))

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
            raise CIMError(CIM_ERR_INVALID_CLASS, 'Class %r not found '
                           'in namespace %r.' % (classname, namespace))

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
        self._get_class_repo(namespace)

        classname = params.get('ClassName', None)
        if classname:
            assert(isinstance(classname, CIMClassName))
            if not self._class_exists(classname.classname, namespace):
                raise CIMError(CIM_ERR_INVALID_CLASS,
                               'The class %r defined by "ClassName" parameter '
                               'does not exist in namespace %r' %
                               (classname, namespace))

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
        self._get_class_repo(namespace)

        classname = params.get('ClassName', None)
        if classname:
            assert(isinstance(classname, CIMClassName))
            if not self._class_exists(classname.classname, namespace):
                raise CIMError(CIM_ERR_INVALID_CLASS,
                               'The class %r defined by "ClassName" parameter '
                               'does not exist in namespace %r' %
                               (classname, namespace))

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
        self._get_class_repo(namespace)
        cname = params['ClassName'].classname

        cc = self._get_class(cname, namespace, local_only=params['LocalOnly'],
                             include_qualifiers=params['IncludeQualifiers'],
                             include_classorigin=params['IncludeClassOrigin'],
                             property_list=params['PropertyList'])

        return self._make_tuple([cc])

    @staticmethod
    def _test_qualifier_decl(qualifier, qual_repo, namespace):
        """
        Test that qualifier is in repo and valid.
        For for conn_lite, ignore this test
        """
        if qual_repo is None:
            return
        if qualifier.name not in qual_repo:
            raise CIMError(CIM_ERR_INVALID_PARAMETER, 'Qualifier '
                           ' declaration %r required by CreateClass not '
                           'found in namespace %r.'
                           % (qualifier.name, namespace))

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
        new_class = params['NewClass']

        if not isinstance(new_class, CIMClass):
            raise CIMError(CIM_ERR_INVALID_PARAMETER,
                           'NewClass not valid CIMClass. Rcvd type=%s' %
                           type(new_class))

        if namespace not in self.classes:
            self.classes[namespace] = NocaseDict({})
            if namespace not in self.methods:
                self.methods[namespace] = NocaseDict()

        if new_class.classname in self.classes[namespace]:
            raise CIMError(CIM_ERR_ALREADY_EXISTS,
                           'Class %r already exists in namespace %r.' %
                           (new_class.classname, namespace))

        # If there is a superclass defined, test existence and test for
        # overridden properties
        new_class = deepcopy(new_class)

        if new_class.superclass:
            try:
                sc = self._get_class(new_class.superclass,  # noqa: F841
                                     namespace=namespace,
                                     local_only=False,
                                     include_qualifiers=True,
                                     include_classorigin=True)
            except CIMError as ce:
                if ce.status_code == CIM_ERR_NOT_FOUND:
                    raise CIMError(CIM_ERR_INVALID_SUPERCLASS, 'Superclass '
                                   '%r for class %r not found in namespace '
                                   ' %r.' %
                                   (new_class.superclass, new_class.classname,
                                    namespace))
                else:
                    raise

            for pname, prop in six.iteritems(new_class.properties):
                if pname in sc.properties:
                    # TODO: should we use prop name from qualifier in override?
                    if 'Override' not in new_class.properties[pname].qualifiers:
                        raise CIMError(CIM_ERR_INVALID_PARAMETER,
                                       'Property %r duplicates property in '
                                       '%r without override.'
                                       % (pname, sc.classname))
                    else:
                        sp = sc.properties[pname]
                        if sp.type != prop.type \
                            or sp.is_array != prop.is_array \
                                or sp.embedded_object != prop.embedded_object:
                            raise CIMError(CIM_ERR_INVALID_PARAMETER,
                                           'Invalid new_class property %r. '
                                           'Does not match overridden '
                                           'property in class %r' %
                                           (pname, sc.classname))

            for mname, method in six.iteritems(new_class.methods):
                if mname in sc.methods:
                    if 'Override' not in new_class.method.qualifiers:
                        raise CIMError(CIM_ERR_INVALID_PARAMETER,
                                       'Method %r duplicates method in class '
                                       '%r without override'
                                       % (mname, sc.classname))
                    else:
                        super_meth = sc.method[mname]
                        if super_meth.type != method.type \
                            or super_meth.is_array != method.is_array \
                                or super_meth.return_type != method.return_type:
                            raise CIMError(CIM_ERR_INVALID_PARAMETER,
                                           'Invalid new_class method %r. '
                                           'Does not match overridden '
                                           'method in class %r.' %
                                           (mname, sc.classname))
                        # TODO: match qualifiers in override.

            # TODO: test class qualifiers.

        # Set class_origin and propagated in the new class and its elements.
        if self._repo_lite:
            qual_repo = None
        else:
            association_class = 'Association' in new_class.qualifiers

            qual_repo = self._get_qualifier_repo(namespace)
            for qual in six.itervalues(new_class.qualifiers):
                qual.propagated = False
                self._test_qualifier_decl(qual, qual_repo, namespace)

            for prop in six.itervalues(new_class.properties):
                if not association_class and prop.type == 'reference':
                    raise CIMError(CIM_ERR_INVALID_PARAMETER,
                                   'Reference property %r not allowed on '
                                   'non-association class %r' %
                                   (prop.name, new_class.classname))
                prop.class_origin = new_class.classname
                prop.propagated = False
                for qual in six.itervalues(prop.qualifiers):
                    self._test_qualifier_decl(qual, qual_repo, namespace)
                    qual.propagated = False

            for method in six.itervalues(new_class.methods):
                method.class_origin = new_class.classname
                method.propagated = False
                for qual in six.itervalues(method.qualifiers):
                    self._test_qualifier_decl(qual, qual_repo, namespace)
                    qual.propagated = False
                for param in six.itervalues(method.parameters):
                    for qual in six.itervalues(param.qualifiers):
                        self._test_qualifier_decl(qual, qual_repo, namespace)
                        param.qualifiers.propagated = False

        self.classes[namespace][new_class.classname] = new_class

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
        self._get_class_repo(namespace)
        raise CIMError(CIM_ERR_NOT_SUPPORTED, 'Currently ModifyClass not '
                                              'supported in '
                                              'Fake_WBEMConnection')

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
        class_repo = self._get_class_repo(namespace)

        cname = params['ClassName'].classname

        try:
            class_repo[cname]
        except KeyError:
            raise CIMError(CIM_ERR_NOT_FOUND, 'Class %r in namespace %r'
                           'not in repository. Nothing deleted.' %
                           (cname, namespace))

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
        qualifier_repo = self._get_qualifier_repo(namespace)

        qname = params['QualifierName']

        try:
            qualifier = qualifier_repo[qname]
            return self._make_tuple([qualifier])
        except KeyError:
            ce = CIMError(CIM_ERR_NOT_FOUND,
                          'Qualifier declaration %r not found in namespace '
                          '%r.' % (qname, namespace))
            raise ce

    def _fake_setqualifier(self, namespace, **params):
        """
        Implements a server responder for
        :meth:`pywbem.WBEMConnection.SetQualifier`.

        Create or modify a qualifier type in the local repository of this
        class.  This method will create a new namespace for the qualifier
        if none is defined.

        Raises:

            CIMError: CIM_ERR_INVALID_PARAMETER
            CIMError: CIM_ERR_ALREADY_EXISTS
        """
        qual = params['QualifierDeclaration']

        # TODO:ks FUTURE implement set... method for instance, qualifier, class
        # as general means to put new data into the repo.
        if namespace not in self.qualifiers:
            self.qualifiers[namespace] = NocaseDict({})

        if not isinstance(qual, CIMQualifierDeclaration):
            raise CIMError(CIM_ERR_INVALID_PARAMETER,
                           'QualifierDeclaration parameter is not a '
                           'valid CIMQualifierDeclaration. Rcvd type=%s' %
                           type(qual))

        if qual.name in self.qualifiers[namespace]:
            raise CIMError(CIM_ERR_ALREADY_EXISTS,
                           'Qualifier declaration %r already exists in '
                           'namespace %r.'
                           % (qual.name, namespace))
        try:
            self.qualifiers[namespace][qual.name] = qual
        except KeyError:
            self.qualifiers[namespace] = NocaseDict({qual.name: qual})

    def _fake_deletequalifier(self, namespace, **params):
        """
        Implements a server responder for
        :meth:`~pywbem.WBEMConnection.DeleteQualifier`

        Deletes a single qualifier if it is in the
        repository for this class and namespace

        Raises;

            CIMError: CIM_ERR_INVALID_NAMESPACE, CIM_ERR_NOT_FOUND
        """
        qualifier_repo = self._get_qualifier_repo(namespace)

        qname = params['QualifierName']

        if qname in qualifier_repo:
            del qualifier_repo[qname]
        else:
            raise CIMError(CIM_ERR_NOT_FOUND,
                           'QualifierDeclaration %r not found in '
                           'namespace %r.' % (qname, namespace))

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

        new_instance = params['NewInstance']

        if self._repo_lite:
            raise CIMError(CIM_ERR_NOT_SUPPORTED, 'CreateInstance not '
                           ' supported when repo_lite set.')

        if not isinstance(new_instance, CIMInstance):
            raise CIMError(CIM_ERR_INVALID_PARAMETER,
                           'NewInstance parameter is not a '
                           'valid CIMInstance. Rcvd type=%s' %
                           type(new_instance))

        # Requires corresponding class to build path to be returned
        try:
            target_class = self._get_class(new_instance.classname,
                                           namespace,
                                           local_only=False,
                                           include_qualifiers=True,
                                           include_classorigin=True)
        except CIMError as ce:
            if ce.status_code == CIM_ERR_NOT_FOUND:
                raise CIMError(CIM_ERR_INVALID_CLASS,
                               'Cannot modify instance because its creation '
                               ' class %r does not exist in namespace %r.' %
                               (new_instance.classname, namespace))
            else:
                raise

        # Handle special classes, currently hard coded.
        # TODO AM 8/18 Generalize the hard coded handling into provider concept
        if new_instance.classname.lower() == 'pg_namespace':
            # These values must match those in testsuite/wbemserver_mock.py
            new_instance['CreationClassName'] = 'PG_Namespace'
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
                raise CIMError(CIM_ERR_INVALID_PARAMETER,
                               'Key property %r not in NewInstance ' % pn)

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
                raise CIMError(CIM_ERR_INVALID_PARAMETER,
                               'Property %r specified in NewInstance is not '
                               'exposed by class %s in namespace %r'
                               % (ipname, target_class.classname, namespace))
            else:
                cprop = target_class.properties[ipname]
                iprop = new_instance.properties[ipname]
                if iprop.is_array != cprop.is_array or \
                        iprop.type != cprop.type:
                    raise CIMError(CIM_ERR_INVALID_PARAMETER,
                                   'Instance and class property %r types '
                                   'do not match: instance=%r, class=%r' %
                                   (ipname, iprop, cprop))

        # Build instance path. We build the complete instance path
        new_instance.path = CIMInstanceName.from_instance(
            target_class,
            new_instance,
            namespace=namespace)
        try:
            # TODO:ks Future use internal function of repo to create namespace
            #         for this repo. ex. _set_instance
            for inst in self.instances[namespace]:
                if inst.path == new_instance.path:
                    raise CIMError(CIM_ERR_ALREADY_EXISTS,
                                   'NewInstance %r already exists in '
                                   'namespace %r.' %
                                   (new_instance.path, namespace))
            self.instances[namespace].append(new_instance)
        except KeyError:
            self.instances[namespace] = [new_instance]
            if namespace not in self.methods:
                self.methods[namespace] = NocaseDict()

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
            raise CIMError(CIM_ERR_NOT_SUPPORTED, 'ModifyInstance not '
                           ' supported when repo_lite set.')

        inst_repo = self._get_instance_repo(namespace)
        modified_instance = deepcopy(params['ModifiedInstance'])
        property_list = params['PropertyList']

        # Return if empty property list
        if property_list is not None and not property_list:
            return

        if modified_instance is not None and not modified_instance:
            return

        if not isinstance(modified_instance, CIMInstance):
            raise CIMError(CIM_ERR_INVALID_PARAMETER,
                           'The ModifiedInstance parameter is not a '
                           'valid CIMInstance. Rcvd type=%s' %
                           type(modified_instance))

        # Classnames in instance and path must match
        if modified_instance.classname != modified_instance.path.classname:
            raise CIMError(CIM_ERR_INVALID_PARAMETER,
                           'ModifyInstance classname in path and instance do '
                           'not match. classname=%r, path.classname=%r' %
                           (modified_instance.classname,
                            modified_instance.path.classname))

        # Get class including properties from superclasses
        try:
            target_class = self.GetClass(modified_instance.classname,
                                         namespace=namespace,
                                         LocalOnly=False,
                                         IncludeQualifiers=True,
                                         IncludeClassOrigin=True)
        except CIMError as ce:
            if ce.status_code == CIM_ERR_NOT_FOUND:
                raise CIMError(CIM_ERR_INVALID_CLASS,
                               'Cannot modify instance because its creation '
                               ' class %r does not exist in namespace %r.'
                               % (modified_instance.classname, namespace))
            else:
                raise

        # get key properties and all class props
        cl_props = [p.name for p in six.itervalues(target_class.properties)]
        key_props = [p.name for p in six.itervalues(target_class.properties)
                     if 'key' in p.qualifiers]

        # Get original instance in repo.  Does not copy the orig instance.
        mod_inst_path = modified_instance.path.copy()
        if modified_instance.path.namespace is None:
            mod_inst_path.namespace = namespace

        orig_instance_tup = self._find_instance(mod_inst_path, inst_repo)
        if orig_instance_tup[0] is None:
            raise CIMError(CIM_ERR_NOT_FOUND,
                           'Original Instance %r not found in namespace %r'
                           % (modified_instance.path, namespace))
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
                    raise CIMError(CIM_ERR_INVALID_PARAMETER,
                                   'Property %r in PropertyList not in class '
                                   '%r' % (p, modified_instance.classname))
        for p in modified_instance:
            if p not in cl_props:
                raise CIMError(CIM_ERR_INVALID_PARAMETER,
                               'Property %r in ModifiedInstance not in class '
                               '%r' % (p, modified_instance.classname))

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
                raise CIMError(CIM_ERR_INVALID_PARAMETER,
                               'ModifyInstance cannot modify key property %r' %
                               p)

        # Remove any properties from modified instance not in the property_list
        if property_list:
            for p in list(modified_instance):
                if p not in property_list:
                    del modified_instance[p]

        # Exception if property in instance but not class or types do not
        # match
        for pname in modified_instance:
            if pname not in target_class.properties:
                raise CIMError(CIM_ERR_INVALID_PARAMETER,
                               'Property %r specified in ModifiedInstance is '
                               'not exposed by class %r in namespace %r'
                               % (pname, target_class.classname, namespace))
            else:
                cprop = target_class.properties[pname]
                iprop = modified_instance.properties[pname]
                if iprop.is_array != cprop.is_array \
                        or iprop.type != cprop.type \
                        or iprop.array_size != cprop.array_size:
                    raise CIMError(CIM_ERR_INVALID_PARAMETER,
                                   'Instance and class property name=%r type '
                                   'or other attributes do not match: '
                                   'instance=%r, class=%r' %
                                   (pname, iprop, cprop))

        # Modify the value of properties in the repo with those from
        # modified instance
        index = orig_instance_tup[0]
        inst_repo[index].update(modified_instance.properties)
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

        # If not repo lite, corresponding class must exist.
        if not self._repo_lite:
            if not self._class_exists(iname.classname, namespace):
                raise CIMError(CIM_ERR_INVALID_CLASS, 'Class %r for '
                               'GetInstance of instance %r does not exist.'
                               % (iname.classname, iname))

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
        """
        iname = params['InstanceName']
        iname.namespace = namespace

        insts_repo = self._get_instance_repo(namespace)

        # if not repo_lite, Corresponding class must exist
        if not self._repo_lite:
            if not self._class_exists(iname.classname, namespace):
                raise CIMError(CIM_ERR_INVALID_CLASS,
                               'Class %r in namespace %r not found. '
                               ' Cannot delete instance %r' %
                               (iname.classname, namespace, iname))

        del_inst = None
        for enum_tup in enumerate(insts_repo):
            index = enum_tup[0]
            inst = enum_tup[1]
            if iname == inst.path:
                if del_inst is not None:
                    raise CIMError(CIM_ERR_FAILED, 'Internal Error: Invalid '
                                   ' Repository. Multiple instances with same '
                                   ' path %r' % inst.path)
                # TODO:ks Future remove this test for duplicate inst paths since
                #       we test for dups on insertion
                else:
                    del insts_repo[index]
                    del_inst = iname

        if not del_inst:
            raise CIMError(CIM_ERR_NOT_FOUND, 'Instance %r not found in '
                           'repository namespace %r' % (iname, namespace))

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

        inst_repo = self._get_instance_repo(namespace)

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
                 for inst in inst_repo if inst.path.classname in clns_dict]

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

        inst_repo = self._get_instance_repo(namespace)

        clns = self._get_subclass_list_for_enums(cname, namespace)
        inst_paths = [inst.path for inst in inst_repo
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
        self._get_instance_repo(namespace)
        raise CIMError(CIM_ERR_NOT_SUPPORTED, 'ExecQuery not implemented!')

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
        # print('CLNS %s for classname=%s' % (clns, classname))
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
        self._get_class_repo(namespace)

        result_classes = self._classnamedict(resultclass_name, namespace)

        rtn_classnames_set = set()
        role = role.lower() if role else role

        for cl in self._get_association_classes(namespace):
            # print('CLINASSOCCLASSES %s' % cl)
            for prop in six.itervalues(cl.properties):
                if prop.type == 'reference' and \
                        self._ref_prop_matches(prop, classname,
                                               cl.classname,
                                               result_classes,
                                               role):
                    rtn_classnames_set.add(cl.classname)
        # print('GET_REF_CLASSNAMES %s' % rtn_classnames_set)
        return list(rtn_classnames_set)

    def _get_reference_instnames(self, instname, namespace, resultclass_name,
                                 role):
        """
        Get the reference instances from the repository for the target
        instname and filtered by the result_class and role parameters.

        Returns a list of the reference instance names. The returned list is
        the original, not a copy so the user must copy them
        """
        insts_repo = self._get_instance_repo(namespace)

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
        #       exist. Otherwise set list to insts_repo to search every instance
        for inst in insts_repo:
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
        self._get_instance_repo(namespace)

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
        self._get_instance_repo(namespace)

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
        self._get_instance_repo(namespace)
        context_id = params['EnumerationContext']

        try:
            context_data = self.enumeration_contexts[context_id]
        except KeyError:
            raise CIMError(CIM_ERR_INVALID_ENUMERATION_CONTEXT,
                           'EnumerationContext %r not found in mock server '
                           'enumeration contexts.' % context_id)

        if context_data['pull_type'] != req_type:
            raise CIMError(CIM_ERR_INVALID_ENUMERATION_CONTEXT,
                           'Invalid pull operations %r does not match '
                           'expected %r for EnumerationContext %r'
                           % (context_data['pull_type'], req_type, context_id))

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
            raise CIMError(CIM_ERR_INVALID_PARAMETER, 'FilterQuery without '
                           'FilterQueryLanguage definition is invalid')
        if params['FilterQueryLanguage']:
            if params['FilterQueryLanguage'] != 'DMTF:FQL':
                raise CIMError(CIM_ERR_QUERY_LANGUAGE_NOT_SUPPORTED,
                               'FilterQueryLanguage %r not supported'
                               % params['FilterQueryLanguage'])
        ot = params['OperationTimeout']
        if ot:
            if not isinstance(ot, six.integer_types) or ot < 0 \
                    or ot > OPEN_MAX_TIMEOUT:
                raise CIMError(CIM_ERR_INVALID_PARAMETER,
                               'OperationTimeout %r must be positive integer '
                               ' less than %s' % (ot, OPEN_MAX_TIMEOUT))

    def _fake_openenumerateinstancepaths(self, namespace, **params):
        # pylint: disable=invalid-name
        """
        Implements WBEM server responder for
        :meth:`~pywbem.WBEMConnection.OpenEnumerationInstancePaths`
        with data from the instance repository.
        """
        self._get_instance_repo(namespace)

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
        self._get_instance_repo(namespace)
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
        self._get_instance_repo(namespace)
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
        self._get_instance_repo(namespace)
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
        self._get_instance_repo(namespace)
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
        self._get_instance_repo(namespace)
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
        self._get_instance_repo(namespace)
        self._validate_open_params(**params)

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
        self._get_instance_repo(namespace)

        context_id = params['EnumerationContext']

        try:
            context_data = self.enumeration_contexts[context_id]
            # This is probably relatively useless because pywbem handles
            # namespace internally but it could catch an error if user plays
            # with the context.
            if context_data['namespace'] != namespace:
                raise CIMError(CIM_ERR_INVALID_NAMESPACE,
                               'Invalid namespace %r for CloseEnumeration '
                               '%r' % (namespace, context_id))
        except KeyError:
            raise CIMError(CIM_ERR_INVALID_ENUMERATION_CONTEXT,
                           'EnumerationContext %r not found in mock server '
                           'enumeration contexts. ' % context_id)
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
            raise TypeError('FakedWBEMConnection InvokeMethod invalid type for '
                            'objectname: %r' % type(objectname))

        namespace = localobject.namespace
        try:
            methodsrepo = self._get_methods_repo(namespace)
        except CIMError as ce:
            # If invoke indicates method repo not built, create it.
            if ce.status_code == CIM_ERR_INVALID_NAMESPACE:
                if namespace in self.classes or \
                        namespace in self.instances:
                    raise CIMError(CIM_ERR_METHOD_NOT_FOUND,
                                   'Method %r in namespace %r not '
                                   'registered in repository' %
                                   (methodname, namespace))
                else:
                    raise

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
            raise CIMError(CIM_ERR_METHOD_NOT_FOUND, 'Method %s not found '
                           'in class %r.' % (methodname,
                                             localobject.classname))
        if target_cln != cc.classname:
            # TODO FUTURE: add method to repo that allows privileged users
            # direct access so we don't have to go through _get_class and can
            # test classes directly in repo
            tcc = self._get_class(target_cln, namespace,
                                  local_only=False, include_qualifiers=True,
                                  include_classorigin=True)
            if methodname not in tcc.methods:
                raise CIMError(CIM_ERR_METHOD_NOT_FOUND, 'Method %r not found '
                               'in origin class %r derived from '
                               'objectname class %r' % (methodname, target_cln,
                                                        localobject.classname))

        # Test for target class in methods repo
        try:
            methods = methodsrepo[target_cln]
        except KeyError:
            raise CIMError(CIM_ERR_METHOD_NOT_FOUND,
                           'Class %r for method %r in namespace %r not '
                           'registered in methods repository' %
                           (localobject.classname, methodname, namespace))

        # Test for method in local class.
        try:
            cc.methods[methodname]
        except KeyError:
            raise CIMError(CIM_ERR_METHOD_NOT_FOUND, 'Method %r not found '
                           'in methods repository for class %r' %
                           (methodname, localobject.classname))

        try:
            bound_method = methods[methodname]
        except KeyError:
            raise CIMError(CIM_ERR_METHOD_NOT_FOUND,
                           'Method %r in namespace %r not registered in '
                           ' methods repository. Internal error' %
                           (methodname, namespace))

        if bound_method is None:
            raise CIMError(CIM_ERR_METHOD_NOT_FOUND,
                           'Class %r for method %r in registered in '
                           'methods repository namespace %r' %
                           (localobject.classname, methodname, namespace))

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
                    raise CIMError(CIM_ERR_INVALID_PARAMETER,
                                   'InvokeMethod Param %r invalid type, '
                                   '%r. Expected tuple or CIMParameter' %
                                   (param, type(param)))

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

            raise CIMError(CIM_ERR_FAILED, 'Exception failure of invoked '
                                           'method %r in namespace %r with '
                                           'input localobject "%r", parameters '
                                           '"%r". Exception: %r\nTraceback\n%s'
                           %
                           (methodname, namespace, localobject, params, ex, tb))

        # test for valid data in response.
        if not isinstance(result, (list, tuple)):
            raise CIMError(CIM_ERR_FAILED, 'Callback method returned %r '
                           'response type. Expected list or tuple' %
                           type(result))
        for param in result[1]:
            if not isinstance(param, CIMParameter):
                raise CIMError(CIM_ERR_FAILED, 'Callback method returned '
                               '%r response type. Expected CIMParameter. '
                               % type(param))

        # Map output params to NocaseDict to be compatible with return
        # from _methodcall. The input list is just CIMParameters
        output_params = NocaseDict()
        for param in result[1]:
            output_params[param.name] = param.value

        return (result[0], output_params)
