"""
Utility functions for end2end tests.
"""

from __future__ import absolute_import, print_function

from copy import deepcopy

from pywbem import CIMInstance, CIMInstanceName, \
    CIMError, CIM_ERR_INVALID_CLASS


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
    latest_profile_inst = profile_insts[latest_i]
    return latest_profile_inst


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
        self._server_dict = dict()

    def add_list(self, server_url, list_name, obj_list):
        if server_url not in self._server_dict:
            self._server_dict[server_url] = dict()
        list_dict = self._server_dict[server_url]
        if list_name in list_dict:
            raise KeyError(
                "List {0!r} for server {1!r} is already in the cache".
                format(list_name, server_url))
        list_dict[list_name] = deepcopy(obj_list)

    def del_list(self, server_url, list_name):
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
        if server_url not in self._server_dict:
            return False
        list_dict = self._server_dict[server_url]
        if list_name not in list_dict:
            return False
        return True


ENUM_INST_CACHE = ServerObjectCache()


def instance_of(conn, path_list, classname):
    """
    Return whether all of a set of CIM instances (identified by their instance
    paths) are of a particular CIM class, i.e. that the creation class of the
    CIM instances or one of its superclasses has the specified class name.

    Because there are WBEM servers without support for class operations,
    this is implemented without relying on class operations. The function
    performs an EnumerateInstanceNames operation on the desired class in
    the namespace of the instance in question, and verifies that the
    instance in question is in the result.

    Parameters:

        path_list (CIMInstanceName or CIMInstance or tuple/list
          thereof): The CIM instance paths. The instance paths must have a
          namespace and classname set. The namespace must be the same
          across all instance paths. The host portion of the instance
          paths is treated specially when comparing them, as described
          in path_equal().

        classname (string): The CIM class name.
    """

    # Check and transform parameters
    assert path_list is not None
    if not isinstance(path_list, (tuple, list)):
        path_list = [path_list]
    paths = []
    for obj in path_list:
        if isinstance(obj, CIMInstance):
            obj = obj.path
        assert isinstance(obj, CIMInstanceName)
        assert obj.namespace is not None
        assert obj.classname is not None
        paths.append(obj)
    del path_list
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
                namespace=namespace, ClassName=classname)
        except CIMError as exc:
            if exc.status_code == CIM_ERR_INVALID_CLASS:
                raise AssertionError(
                    "Class {0!r} does not exist in namespace {1!r}".
                    format(classname, namespace))
            else:
                raise
        ENUM_INST_CACHE.add_list(conn.url, enum_paths_id, enum_paths)

    for path in paths:
        if not path_in(path, enum_paths):
            return False
    return True
