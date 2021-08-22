"""
Utility functions for pywbem end2end tests.
"""

from __future__ import absolute_import, print_function

from copy import deepcopy

from pywbem import CIMInstance, CIMInstanceName, \
    Error, CIMError, CIM_ERR_INVALID_CLASS, WBEMConnection


def latest_profile_inst(profile_insts):
    """
    Determine the instance with the latest version in a list of registered
    profile instances and return that instance.
    """
    profile_versions = [inst['RegisteredVersion'] for inst in profile_insts]
    latest_i = None
    latest_version = [0, 0, 0]
    for i, profile_version in enumerate(profile_versions):
        profile_version = [int(v) for v in profile_version.split('.')]
        if profile_version > latest_version:
            latest_version = profile_version
            latest_i = i
    return profile_insts[latest_i]


def path_equal(inst1_path, inst2_path):
    """
    Return whether two instance paths are equal, with special treatment
    of their host component:
    - The host component is compared literally (but case insensitively),
      i.e. no IP address to hostname translation is performed.
    - If one or both of the instance paths have their host component set to
      None, the comparison is considered equal.

    For keys of the instance paths that are references, the special
    treatment of their host component is applied recursively.
    """
    assert isinstance(inst1_path, CIMInstanceName)
    assert isinstance(inst2_path, CIMInstanceName)
    if inst1_path.classname.lower() != inst2_path.classname.lower():
        return False
    if inst1_path.namespace.lower() != inst2_path.namespace.lower():
        return False
    if inst1_path.host is not None and \
            inst2_path.host is not None and \
            inst1_path.host.lower() != inst2_path.host.lower():
        return False
    if len(inst1_path.keybindings) != len(inst2_path.keybindings):
        return False
    for key_name in inst1_path.keybindings:
        key1_value = inst1_path.keybindings[key_name]
        if key_name not in inst2_path.keybindings:
            return False
        key2_value = inst2_path.keybindings[key_name]
        # pylint: disable=no-else-return
        if isinstance(key1_value, CIMInstanceName) and \
                isinstance(key2_value, CIMInstanceName) and \
                not path_equal(key1_value, key2_value):
            return False
        elif key1_value != key2_value:
            return False
    return True


def path_in(inst_path, inst_path_list):
    """
    Return whether an instance path is in an instance path list, with special
    treatment of their host component when testing for equality, as described
    for path_equal().

    Each item in inst_path list can be an instance path (CIMInstanceName)
    or an instance (CIMInstance) whose path is then used for the test.
    """
    assert isinstance(inst_path, CIMInstanceName)
    for ip in inst_path_list:
        if isinstance(ip, CIMInstance):
            ip = ip.path
        assert isinstance(ip, CIMInstanceName)
        if path_equal(inst_path, ip):
            return True
    return False


class ServerObjectCache(object):
    """
    A cache for named lists of CIM objects from a particular WBEM server.

    Each list is identified by a name that can be an arbitrary string.

    The WBEM server is identified by its URL. This allows the objects to
    be reused across WBEMConnection or WBEMServer objects to the same server.
    """

    def __init__(self):
        # Cache dictionary:
        # - key: server URL
        # - value: dictionary of named lists:
        #   - key: list name
        #   _ value: list of CIM objects (e.g. CIMInstanceName, CIMClass)
        self._server_dict = {}

    def add_list(self, server_url, list_name, obj_list):
        """Add obj_list to the list named list_name"""
        if server_url not in self._server_dict:
            self._server_dict[server_url] = {}
        list_dict = self._server_dict[server_url]
        if list_name in list_dict:
            raise KeyError(
                "List {0!r} for server {1!r} is already in the cache".
                format(list_name, server_url))
        list_dict[list_name] = deepcopy(obj_list)

    def del_list(self, server_url, list_name):
        """Delete list_name"""
        if server_url not in self._server_dict:
            raise KeyError(
                "Server {0!r} is not in the cache".
                format(server_url))
        list_dict = self._server_dict[server_url]
        if list_name not in list_dict:
            raise KeyError(
                "List {0!r} for server {1!r} is not in the cache".
                format(list_name, server_url))
        del list_dict[list_name]
        if not list_dict:
            del self._server_dict[server_url]

    def get_list(self, server_url, list_name):
        """Get the list named list_name"""
        if server_url not in self._server_dict:
            raise KeyError(
                "Server {0!r} is not in the cache".
                format(server_url))
        list_dict = self._server_dict[server_url]
        if list_name not in list_dict:
            raise KeyError(
                "List {0!r} for server {1!r} is not in the cache".
                format(list_name, server_url))
        return list_dict[list_name]

    def has_list(self, server_url, list_name):
        """Return boolean indicating whether there is a list named list_name"""
        if server_url not in self._server_dict:
            return False
        list_dict = self._server_dict[server_url]
        if list_name not in list_dict:
            return False
        return True


ENUM_INST_CACHE = ServerObjectCache()


def instance_of(conn, obj_list, classname):
    """
    Return whether all of a set of CIM instances and/or CIM instance paths are
    of a particular CIM class (including subclasses).

    Because there are WBEM servers without support for class operations,
    this is implemented without relying on class operations. The function
    performs an EnumerateInstanceNames operation on the desired class in
    the namespace of the instance in question, and verifies that the
    instance in question is in the result.

    Parameters:

        obj_list (CIMInstanceName or CIMInstance or tuple/list thereof):
          The CIM instances and CIM instance paths to be evaluated.

        classname (string): The CIM class name.
    """

    assert obj_list is not None
    if not isinstance(obj_list, (tuple, list)):
        obj_list = [obj_list]

    paths = []
    for obj in obj_list:
        if isinstance(obj, CIMInstance):
            path = obj.path
        else:
            path = obj
        assert isinstance(path, CIMInstanceName)  # ensured by CIMInstance
        assert path.classname is not None  # ensured by CIMInstanceName
        assert path.namespace is not None
        paths.append(path)

    assert len(paths) >= 1
    namespace = paths[0].namespace
    for path in paths:
        assert path.namespace.lower() == namespace.lower()

    enum_paths_id = namespace.lower() + ':' + classname.lower()

    try:
        enum_paths = ENUM_INST_CACHE.get_list(conn.url, enum_paths_id)
    except KeyError:
        try:
            enum_paths = conn.EnumerateInstanceNames(
                namespace=namespace, ClassName=classname,
                asserted=False)
        except CIMError as exc:
            if exc.status_code == CIM_ERR_INVALID_CLASS:
                raise AssertionError(
                    "Server {0} at {1}: Class {2!r} does not exist in "
                    "namespace {3!r}".
                    format(conn.es_server.nickname, conn.url,
                           classname, namespace))
            conn.raise_as_assertion_error(exc, 'EnumerateInstanceNames')
        except Error as exc:
            conn.raise_as_assertion_error(exc, 'EnumerateInstanceNames')
        ENUM_INST_CACHE.add_list(conn.url, enum_paths_id, enum_paths)

    for path in paths:
        if not path_in(path, enum_paths):
            return False
    return True


class WBEMConnectionAsserted(WBEMConnection):
    """
    Subclass of WBEMConnection that adds the functionality to assert that
    the operation succeeds, and that raises an AssertionError if it does
    not succeed.

    The assertion behavior is disabled by default and can be enabled by
    specifying keyword argument `asserted=True`.
    """

    def __init__(self, *args, **kwargs):
        """
        Parameters:

          es_server (easy_server.Server): Definition of server to test against
            (required keyword argument)

          All other positional and keyword arguments are passed to the
          superclass init.
        """
        es_server = kwargs['es_server']
        del kwargs['es_server']
        super(WBEMConnectionAsserted, self).__init__(*args, **kwargs)
        self.es_server = es_server

    def _call_op(self, funcname, *args, **kwargs):
        """
        Call the specified operation function of the base class.

        If keyword argument 'asserted' is True, raise any pywbem.Error
        exceptions as AssertionError exceptions.
        """
        if 'asserted' in kwargs:
            asserted = bool(kwargs['asserted'])
            del kwargs['asserted']
        else:
            # The default must be non-asserted, in order to allow all the
            # operation invocations in WBEMServer to do their error handling.
            asserted = False
        func = getattr(super(WBEMConnectionAsserted, self), funcname)
        # returns a bound method
        if asserted:
            try:
                return func(*args, **kwargs)
            except Error as exc:
                raise self._assertion_error(exc, funcname, *args, **kwargs)
        else:
            return func(*args, **kwargs)

    def _assertion_error(self, exc, funcname, *args, **kwargs):
        """
        Return an AssertionError about the specified exception.
        """
        parm_list = ["{0!r}".format(a) for a in args]
        parm_list.extend(["{0}={1!r}".format(k, v) for k, v in kwargs.items()])
        parm_str = ", ".join(parm_list)
        return AssertionError(
            "Server {0} at {1}: WBEMConnection.{2}() failed and raised "
            "{3} - {4}. "
            "Parameters: ({5})".
            format(self.es_server.nickname, self.url, funcname,
                   exc.__class__.__name__, exc, parm_str))

    def EnumerateInstances(self, *args, **kwargs):
        # pylint: disable=arguments-differ
        return self._call_op('EnumerateInstances', *args, **kwargs)

    def EnumerateInstanceNames(self, *args, **kwargs):
        # pylint: disable=arguments-differ
        return self._call_op('EnumerateInstanceNames', *args, **kwargs)

    def GetInstance(self, *args, **kwargs):
        # pylint: disable=arguments-differ
        return self._call_op('GetInstance', *args, **kwargs)

    def ModifyInstance(self, *args, **kwargs):
        # pylint: disable=arguments-differ
        return self._call_op('ModifyInstance', *args, **kwargs)

    def CreateInstance(self, *args, **kwargs):
        # pylint: disable=arguments-differ
        return self._call_op('CreateInstance', *args, **kwargs)

    def DeleteInstance(self, *args, **kwargs):
        # pylint: disable=arguments-differ
        return self._call_op('DeleteInstance', *args, **kwargs)

    def Associators(self, *args, **kwargs):
        # pylint: disable=arguments-differ
        return self._call_op('Associators', *args, **kwargs)

    def AssociatorNames(self, *args, **kwargs):
        # pylint: disable=arguments-differ
        return self._call_op('AssociatorNames', *args, **kwargs)

    def References(self, *args, **kwargs):
        # pylint: disable=arguments-differ
        return self._call_op('References', *args, **kwargs)

    def ReferenceNames(self, *args, **kwargs):
        # pylint: disable=arguments-differ
        return self._call_op('ReferenceNames', *args, **kwargs)

    def InvokeMethod(self, *args, **kwargs):
        # pylint: disable=arguments-differ
        return self._call_op('InvokeMethod', *args, **kwargs)

    def ExecQuery(self, *args, **kwargs):
        # pylint: disable=arguments-differ
        return self._call_op('ExecQuery', *args, **kwargs)

    def IterEnumerateInstances(self, *args, **kwargs):
        # pylint: disable=arguments-differ
        return self._call_op('IterEnumerateInstances', *args, **kwargs)

    def IterEnumerateInstancePaths(self, *args, **kwargs):
        # pylint: disable=arguments-differ
        return self._call_op('IterEnumerateInstancePaths', *args, **kwargs)

    def IterAssociatorInstances(self, *args, **kwargs):
        # pylint: disable=arguments-differ
        return self._call_op('IterAssociatorInstances', *args, **kwargs)

    def IterAssociatorInstancePaths(self, *args, **kwargs):
        # pylint: disable=arguments-differ
        return self._call_op('IterAssociatorInstancePaths', *args, **kwargs)

    def IterReferenceInstances(self, *args, **kwargs):
        # pylint: disable=arguments-differ
        return self._call_op('IterReferenceInstances', *args, **kwargs)

    def IterReferenceInstancePaths(self, *args, **kwargs):
        # pylint: disable=arguments-differ
        return self._call_op('IterReferenceInstancePaths', *args, **kwargs)

    def IterQueryInstances(self, *args, **kwargs):
        # pylint: disable=arguments-differ
        return self._call_op('IterQueryInstances', *args, **kwargs)

    def OpenEnumerateInstances(self, *args, **kwargs):
        # pylint: disable=arguments-differ
        return self._call_op('OpenEnumerateInstances', *args, **kwargs)

    def OpenEnumerateInstancePaths(self, *args, **kwargs):
        # pylint: disable=arguments-differ
        return self._call_op('OpenEnumerateInstancePaths', *args, **kwargs)

    def OpenAssociatorInstances(self, *args, **kwargs):
        # pylint: disable=arguments-differ
        return self._call_op('OpenAssociatorInstances', *args, **kwargs)

    def OpenAssociatorInstancePaths(self, *args, **kwargs):
        # pylint: disable=arguments-differ
        return self._call_op('OpenAssociatorInstancePaths', *args, **kwargs)

    def OpenReferenceInstances(self, *args, **kwargs):
        # pylint: disable=arguments-differ
        return self._call_op('OpenReferenceInstances', *args, **kwargs)

    def OpenReferenceInstancePaths(self, *args, **kwargs):
        # pylint: disable=arguments-differ
        return self._call_op('OpenReferenceInstancePaths', *args, **kwargs)

    def OpenQueryInstances(self, *args, **kwargs):
        # pylint: disable=arguments-differ
        return self._call_op('OpenQueryInstances', *args, **kwargs)

    def PullInstancesWithPath(self, *args, **kwargs):
        # pylint: disable=arguments-differ
        return self._call_op('PullInstancesWithPath', *args, **kwargs)

    def PullInstancePaths(self, *args, **kwargs):
        # pylint: disable=arguments-differ
        return self._call_op('PullInstancePaths', *args, **kwargs)

    def PullInstances(self, *args, **kwargs):
        # pylint: disable=arguments-differ
        return self._call_op('PullInstances', *args, **kwargs)

    def CloseEnumeration(self, *args, **kwargs):
        # pylint: disable=arguments-differ
        return self._call_op('CloseEnumeration', *args, **kwargs)

    def EnumerateClasses(self, *args, **kwargs):
        # pylint: disable=arguments-differ
        return self._call_op('EnumerateClasses', *args, **kwargs)

    def EnumerateClassNames(self, *args, **kwargs):
        # pylint: disable=arguments-differ
        return self._call_op('EnumerateClassNames', *args, **kwargs)

    def GetClass(self, *args, **kwargs):
        # pylint: disable=arguments-differ
        return self._call_op('GetClass', *args, **kwargs)

    def ModifyClass(self, *args, **kwargs):
        # pylint: disable=arguments-differ
        return self._call_op('ModifyClass', *args, **kwargs)

    def CreateClass(self, *args, **kwargs):
        # pylint: disable=arguments-differ
        return self._call_op('CreateClass', *args, **kwargs)

    def DeleteClass(self, *args, **kwargs):
        # pylint: disable=arguments-differ
        return self._call_op('DeleteClass', *args, **kwargs)

    def EnumerateQualifiers(self, *args, **kwargs):
        # pylint: disable=arguments-differ
        return self._call_op('EnumerateQualifiers', *args, **kwargs)

    def GetQualifier(self, *args, **kwargs):
        # pylint: disable=arguments-differ
        return self._call_op('GetQualifier', *args, **kwargs)

    def SetQualifier(self, *args, **kwargs):
        # pylint: disable=arguments-differ
        return self._call_op('SetQualifier', *args, **kwargs)

    def DeleteQualifier(self, *args, **kwargs):
        # pylint: disable=arguments-differ
        return self._call_op('DeleteQualifier', *args, **kwargs)


def server_func_asserted(server, funcname, *args, **kwargs):
    """
    Call a method on a `WBEMServer` object and assert that it does not raise a
    pywbem.Error exception.
    """
    func = getattr(server, funcname)
    try:
        return func(*args, **kwargs)
    except Error as exc:
        parm_list = ["{0!r}".format(a) for a in args]
        parm_list.extend(["{0}={1!r}".format(k, v) for k, v in kwargs.items()])
        parm_str = ", ".join(parm_list)
        raise AssertionError(
            "Server {0} at {1}: Calling WBEMServer.{2}() failed and "
            "raised {3} - {4}. "
            "Parameters: ({5})".
            format(server.conn.es_server.nickname, server.conn.url,
                   funcname, exc.__class__.__name__, exc, parm_str))


def server_prop_asserted(server, propname):
    """
    Get the value of a property of a `WBEMServer` object and assert that it
    does not raise a pywbem.Error exception.
    """
    try:
        return getattr(server, propname)
    except Error as exc:
        raise AssertionError(
            "Server {0} at {1}: Getting WBEMServer.{2} failed and "
            "raised {3} - {4}.".
            format(server.conn.es_server.nickname, server.conn.url,
                   propname, exc.__class__.__name__, exc))
