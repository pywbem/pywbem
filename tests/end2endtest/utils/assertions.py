"""
Assertion functions for pywbem end2end tests.
"""

from __future__ import absolute_import

import six

from pywbem import CIMInstance, CIMInstanceName
from pywbem._utils import _format

from .utils import path_equal, path_in, instance_of, ServerObjectCache

OBJECT_CACHE = ServerObjectCache()


def assert_number_of_instances_equal(
        conn, inst_list, inst_list_msg, exp_number):
    """
    Assert that the number of objects in a list of instances or instance paths
    is equal to an expected number.

    Parameters:

        conn (WBEMConnection with 'es_server' attribute)

        exp_number (integer): Expected number of instances or instance paths.

        inst_list (list of CIMInstanceName or CIMInstance): List of instances
          or instance paths to be tested.

        inst_list_msg (string): Short definition what inst_list is.
    """
    if len(inst_list) != exp_number:
        raise AssertionError(
            _format("Server {0} at {1}: List of instances ({2}) does not have "
                    "the expected exact size of {3} but is {4}",
                    conn.es_server.nickname, conn.url,
                    inst_list_msg, exp_number, len(inst_list)))


def assert_number_of_instances_minimum(
        conn, inst_list, inst_list_msg, exp_number):
    """
    Assert that the number of objects in a list of instances or instance paths
    is equal to or larger than an expected number.

    Parameters:

        conn (WBEMConnection with 'es_server' attribute)

        exp_number (integer): Expected number of instances or instance paths.

        inst_list (list of CIMInstanceName or CIMInstance): List of instances
          or instance paths to be tested.

        inst_list_msg (string): Short definition what inst_list is.
    """
    if len(inst_list) < exp_number:
        raise AssertionError(
            _format("Server {0} at {1}: List of instances ({2}) does not have "
                    "the expected minimum size of {3} but is {4}",
                    conn.es_server.nickname, conn.url,
                    inst_list_msg, exp_number, len(inst_list)))


def assert_instance_of(conn, obj_list, classname):
    """
    Assert that a set of CIM instances and/or CIM instance paths are of a
    particular CIM class (including subclasses).

    Because there are WBEM servers without support for class operations,
    this is implemented without relying on class operations. The function
    performs an EnumerateInstanceNames operation on the desired class in
    the namespace of the instance in question, and verifies that the
    instance in question is in the result.

    Parameters:

        conn (WBEMConnection with 'es_server' attribute)

        obj_list (CIMInstanceName or CIMInstance or tuple/list thereof):
          The CIM instances and CIM instance paths to be evaluated.

        classname (string): The CIM class name.
    """

    # TODO 2018-12 AM: Improve performance by avoiding EI on each path
    if not isinstance(obj_list, (tuple, list)):
        obj_list = [obj_list]

    for obj in obj_list:
        if isinstance(obj, CIMInstance):
            path = obj.path
            assert isinstance(path, CIMInstanceName)  # Ensured by CIMInstance
            assert path.namespace is not None  # Ensured by WBEMConnection ops
            if path.classname != obj.classname:
                raise AssertionError(
                    _format("Server {0} at {1}: Inconsistent class name in "
                            "CIMInstance object: obj.classname={2!A}, "
                            "obj.path.classname={3!A}, obj.path={4!A}",
                            conn.es_server.nickname, conn.url,
                            obj.classname, path.classname, path.to_wbem_uri()))
        else:
            path = obj
            assert isinstance(path, CIMInstanceName)
        if not instance_of(conn, path, classname):
            raise AssertionError(
                _format("Server {0} at {1}: Instance at {2!A} is not of "
                        "class {3!A}",
                        conn.es_server.nickname, conn.url,
                        path.to_wbem_uri(), classname))


def assert_instance_consistency(conn, instance, path):
    """
    Assert that an instance and an instance path are consistent:

    - They must have the same classname.
    - The instance must have the key properties matching the keybindings
      of the instance path.

    The 'path' attribute of the instance is ignored for this purpose.
    Of course, this function can be used to verify consistency of
    an instance and its 'path' attribute by passing it as the 'path'
    parameter.

    Parameters:

        conn (WBEMConnection with 'es_server' attribute)

        instance (CIMInstance): The CIM instance to be verified.

        path (CIMInstanceName): The CIM instance path to be verified.
    """

    # Check parameters
    assert isinstance(instance, CIMInstance)
    assert isinstance(path, CIMInstanceName)

    if instance.classname.lower() != path.classname.lower():
        raise AssertionError(
            _format("Server {0} at {1}: Inconsistent instance and instance "
                    "path: Instance classname {2!A} does not match classname "
                    "of instance path {3!A}",
                    conn.es_server.nickname, conn.url,
                    instance.classname, path.to_wbem_uri()))

    for key_name in path.keybindings:

        if key_name not in instance.properties:
            raise AssertionError(
                _format("Server {0} at {1}: Inconsistent instance and "
                        "instance path: Instance does not have key property "
                        "{2!A} of instance path {3!A}",
                        conn.es_server.nickname, conn.url,
                        key_name, path.to_wbem_uri()))

        if instance.properties[key_name].value != \
                path.keybindings[key_name]:
            raise AssertionError(
                _format("Server {0} at {1}: Inconsistent instance and "
                        "instance path: For key {2!A}, instance property "
                        "value {3!A} does not match instance path keybinding "
                        "value {4!A}",
                        conn.es_server.nickname, conn.url,
                        key_name, instance.properties[key_name],
                        path.keybindings[key_name]))


def assert_mandatory_properties(conn, instance, property_list):
    """
    Assert that an instance has non-null values for a set of properties.

    Parameters:

        conn (WBEMConnection with 'es_server' attribute)

        instance (CIMInstance): The CIM instance to be verified.

        property_list (iterable of string): The property names.
    """

    # Check parameters
    assert isinstance(instance, CIMInstance)

    instance_prop_names = instance.properties.keys()
    for prop_name in property_list:
        assert isinstance(prop_name, six.string_types)

        if prop_name not in instance_prop_names:
            raise AssertionError(
                _format("Server {0} at {1}: Mandatory properties issue: "
                        "Instance of class {2!A} does not have mandatory "
                        "property {3!A}",
                        conn.es_server.nickname, conn.url,
                        instance.classname, prop_name))

        prop_value = instance.properties[prop_name]
        if prop_value is None:
            raise AssertionError(
                _format("Server {0} at {1}: Mandatory properties issue: "
                        "Instance of class {2!A} has mandatory property "
                        "{3!A} but with a value of NULL",
                        conn.es_server.nickname, conn.url,
                        instance.classname, prop_name))


def assert_property_one_of(conn, instance, prop_name, value_list):
    """
    Assert that a simple (= non-array) CIM property of an instance has a
    value that is one of a set of allowable values.

    Parameters:

        conn (WBEMConnection with 'es_server' attribute)

        instance (CIMInstance): The CIM instance that has the property to
          be verified.

        prop_name (string): Name of the CIM property to be verified.

        value_list (iterable of values): The set of allowable values for
          the property.
    """

    # Check parameters
    assert isinstance(instance, CIMInstance)
    assert isinstance(prop_name, six.string_types)
    prop = instance.properties[prop_name]
    assert not prop.is_array

    prop_value = prop.value
    if prop_value not in value_list:
        raise AssertionError(
            _format("Server {0} at {1}: Property value issue: The value of "
                    "simple property {2!A} in an instance of class {3!A} is "
                    "not in the allowable set of values {4!A}, but is {5!A}",
                    conn.es_server.nickname, conn.url,
                    prop_name, instance.classname, value_list, prop_value))


def assert_property_contains(conn, instance, prop_name, value):
    """
    Assert that a CIM array property (of an instance) contains a particular
    value.

    Parameters:

        conn (WBEMConnection with 'es_server' attribute)

        instance (CIMInstance): The CIM instance that has the property to
          be verified.

        prop_name (string): Name of the CIM property to be verified.

        value (value): The value.
    """

    # Check parameters
    assert isinstance(instance, CIMInstance)
    assert isinstance(prop_name, six.string_types)
    prop = instance.properties[prop_name]
    assert prop.is_array

    prop_values = prop.value
    if value not in prop_values:
        raise AssertionError(
            _format("Server {0} at {1}: Property value issue: The value of "
                    "array property {2!A} in an instance of class {3!A} does "
                    "not contain value {4!A}, but is {5!A}",
                    conn.es_server.nickname, conn.url,
                    prop_name, instance.classname, value, prop_values))


def assert_path_equal(conn, path1, path1_msg, path2, path2_msg):
    """
    Assert that two instance paths are equal, with special treatment
    of their host component:

    - The host component is compared literally (but case insensitively),
      i.e. no IP address to hostname translation is performed.
    - If one or both of the instance paths have their host component set to
      None, the comparison is considered equal.

    For keys of the instance paths that are references, the special
    treatment of their host component is applied recursively.

    Parameters:

        conn (WBEMConnection with 'es_server' attribute)

        path1 (CIMInstanceName): First instance path to be compared.

        path1_msg (string): Short definition what path1 is.

        path2 (CIMInstanceName): Second instance path to be compared.

        path2_msg (string): Short definition what path2 is.
    """

    # Check parameters
    # Note: path1 and path2 are checked in path_equal()
    assert isinstance(path1_msg, six.string_types)
    assert isinstance(path2_msg, six.string_types)

    if not path_equal(path1, path2):
        raise AssertionError(
            _format("Server {0} at {1}: Instance path issue: Instance path "
                    "{2!A} ({3}) does not match instance path {4!A} ({5})",
                    conn.es_server.nickname, conn.url,
                    path1.to_wbem_uri(), path1_msg,
                    path2.to_wbem_uri(), path2_msg))


def assert_path_in(conn, path, path_msg, path_list, path_list_msg):
    """
    Assert that an instance path is in a list of instance paths or
    instances, with special treatment of their host component as described
    in assert_path_equal().

    Parameters:

        conn (WBEMConnection with 'es_server' attribute)

        path (CIMInstanceName): Instance path to be tested for being contained
          in list.

        path_msg (string): Short definition what path is.

        path_list (iterable of CIMInstanceName): List of instance paths tested
          for containing path.

        path_list_msg (string): Short definition what path_list is.
    """

    # Check parameters
    # Note: path and path_list are checked in path_in()
    assert isinstance(path_msg, six.string_types)
    assert isinstance(path_list_msg, six.string_types)

    if not path_in(path, path_list):
        raise AssertionError(
            _format("Server {0} at {1}: Instance path issue: Instance path "
                    "{2!A} ({3}) is not in expected set of instance paths "
                    "({4})",
                    conn.es_server.nickname, conn.url,
                    path.to_wbem_uri(), path_msg, path_list_msg))


def assert_association_a1(
        conn, profile_id,
        source_path, source_role, assoc_class, far_role, far_class):
    """
    Assert that navigation from a source instance across an association
    succeeds.

    This test performs approach a1:
      - associations: References with manual far end filtering
      - far ends: Associators with operation-based far end filtering

    Parameters:

        conn (WBEMConnection with 'es_server' attribute)

        profile_id (string): Profile org and name as 'org:name'

        source_path (CIMInstanceName): Instance path of the source instance.

        source_role (string): Filter: Role on source end of association.

        source_class (string): Filter: Class name of source end of association.

        far_role (string): Filter: Role on far end of association.

        far_class (string): Filter: Class name of far end of association.
    """

    a1_assoc_insts = conn.References(
        source_path,
        ResultClass=assoc_class,
        Role=source_role,
        asserted=True)

    a1_assoc_insts = [
        inst for inst in a1_assoc_insts
        if far_role in inst.path.keybindings and
        instance_of(conn, inst.path.keybindings[far_role], far_class)
    ]
    a1_assoc_paths = [inst.path for inst in a1_assoc_insts]

    a1_far_insts = conn.Associators(
        source_path,
        AssocClass=assoc_class,
        ResultClass=far_class,
        Role=source_role,
        ResultRole=far_role,
        asserted=True)

    a1_far_paths = [inst.path for inst in a1_far_insts]

    _assert_association_consistency(
        conn, profile_id,
        source_path, source_role,
        a1_assoc_insts,
        "manually filtered result of References (a1)",
        a1_assoc_paths,
        "paths of manually filtered result of References (a1)",
        assoc_class,
        a1_far_insts,
        "result of Associators (a1)",
        a1_far_paths,
        "paths of result of Associators (a1)",
        far_class, far_role)

    return a1_far_insts, a1_assoc_insts


def assert_association_a2(
        conn, profile_id,
        source_path, source_role, assoc_class, far_role, far_class):
    """
    Assert that navigation from a source instance across an association
    succeeds.

    This test performs approach a2:
      - associations: References with manual far end filtering
      - far end: Associators with manual far end filtering

    Parameters:

        conn (WBEMConnection with 'es_server' attribute)

        profile_id (string): Profile org and name as 'org:name'

        source_path (CIMInstanceName): Instance path of the source instance.

        source_role (string): Filter: Role on source end of association.

        source_class (string): Filter: Class name of source end of association.

        far_role (string): Filter: Role on far end of association.

        far_class (string): Filter: Class name of far end of association.
    """

    a2_assoc_insts = conn.References(
        source_path,
        ResultClass=assoc_class,
        Role=source_role,
        asserted=True)

    a2_assoc_insts = [
        inst for inst in a2_assoc_insts
        if far_role in inst.path.keybindings and
        instance_of(conn, inst.path.keybindings[far_role], far_class)
    ]
    a2_assoc_paths = [inst.path for inst in a2_assoc_insts]
    a2_assoc_far_paths = [path.keybindings[far_role]
                          for path in a2_assoc_paths]

    a2_far_insts = conn.Associators(
        source_path,
        AssocClass=assoc_class,
        Role=source_role,
        asserted=True)

    a2_far_insts = [
        inst for inst in a2_far_insts
        if path_in(inst.path, a2_assoc_far_paths) and
        instance_of(conn, inst.path, far_class)
    ]
    a2_far_paths = [inst.path for inst in a2_far_insts]

    _assert_association_consistency(
        conn, profile_id,
        source_path, source_role,
        a2_assoc_insts,
        "manually filtered result of References (a2)",
        a2_assoc_paths,
        "paths of manually filtered result of References (a2)",
        assoc_class,
        a2_far_insts,
        "manually filtered result of Associators (a2)",
        a2_far_paths,
        "paths of manually filtered result of Associators (a2)",
        far_class, far_role)

    return a2_far_insts, a2_assoc_insts


def assert_association_a3(
        conn, profile_id,
        source_path, source_role, assoc_class, far_role, far_class):
    """
    Assert that navigation from a source instance across an association
    succeeds.

    This test performs approach a3:
      - associations: ReferenceNames with manual far end filtering and
        GetInstance.
      - far end: AssociatorNames with operation-based far end filtering and
        GetInstance.

    Parameters:

        conn (WBEMConnection with 'es_server' attribute)

        profile_id (string): Profile org and name as 'org:name'

        source_path (CIMInstanceName): Instance path of the source instance.

        source_role (string): Filter: Role on source end of association.

        source_class (string): Filter: Class name of source end of association.

        far_role (string): Filter: Role on far end of association.

        far_class (string): Filter: Class name of far end of association.
    """

    a3_assoc_paths = conn.ReferenceNames(
        source_path,
        ResultClass=assoc_class,
        Role=source_role,
        asserted=True)

    a3_assoc_paths = [
        path for path in a3_assoc_paths
        if far_role in path.keybindings and
        instance_of(conn, path.keybindings[far_role], far_class)
    ]
    a3_assoc_insts = []

    for path in a3_assoc_paths:
        _inst = conn.GetInstance(path, asserted=True)
        a3_assoc_insts.append(_inst)

    a3_far_paths = conn.AssociatorNames(
        source_path,
        AssocClass=assoc_class,
        ResultClass=far_class,
        Role=source_role,
        ResultRole=far_role,
        asserted=True)

    a3_far_insts = []
    for path in a3_far_paths:
        _inst = conn.GetInstance(path, asserted=True)
        a3_far_insts.append(_inst)

    _assert_association_consistency(
        conn, profile_id,
        source_path, source_role,
        a3_assoc_insts,
        "GetInstance on manually filtered result of ReferenceNames (a3)",
        a3_assoc_paths,
        "manually filtered result of ReferenceNames (a3)",
        assoc_class,
        a3_far_insts,
        "GetInstance on result of AssociatorNames (a3)",
        a3_far_paths,
        "result of AssociatorNames (a3)",
        far_class, far_role)

    return a3_far_insts, a3_assoc_insts


def assert_association_a4(
        conn, profile_id,
        source_path, source_role, assoc_class, far_role, far_class):
    """
    Assert that navigation from a source instance across an association
    succeeds.

    This test performs approach a4:
      - associations: ReferenceNames with manual far end filtering and
        GetInstance.
      - far end: AssociatorNames with manual far end filtering and
        GetInstance.

    Parameters:

        conn (WBEMConnection with 'es_server' attribute)

        profile_id (string): Profile org and name as 'org:name'

        source_path (CIMInstanceName): Instance path of the source instance.

        source_role (string): Filter: Role on source end of association.

        source_class (string): Filter: Class name of source end of association.

        far_role (string): Filter: Role on far end of association.

        far_class (string): Filter: Class name of far end of association.
    """

    a4_assoc_paths = conn.ReferenceNames(
        source_path,
        ResultClass=assoc_class,
        Role=source_role,
        asserted=True)

    a4_assoc_paths = [
        path for path in a4_assoc_paths
        if far_role in path.keybindings and
        instance_of(conn, path.keybindings[far_role], far_class)
    ]
    a4_assoc_far_paths = [path.keybindings[far_role]
                          for path in a4_assoc_paths]

    a4_assoc_insts = []
    for path in a4_assoc_paths:
        _inst = conn.GetInstance(path, asserted=True)
        a4_assoc_insts.append(_inst)

    a4_far_paths = conn.AssociatorNames(
        source_path,
        AssocClass=assoc_class,
        Role=source_role,
        asserted=True)

    a4_far_paths = [
        path for path in a4_far_paths
        if path_in(path, a4_assoc_far_paths) and
        instance_of(conn, path, far_class)
    ]

    a4_far_insts = []
    for path in a4_far_paths:
        _inst = conn.GetInstance(path, asserted=True)
        a4_far_insts.append(_inst)

    _assert_association_consistency(
        conn, profile_id,
        source_path, source_role,
        a4_assoc_insts,
        "GetInstance on manually filtered result of ReferenceNames (a4)",
        a4_assoc_paths,
        "manually filtered result of ReferenceNames (a4)",
        assoc_class,
        a4_far_insts,
        "GetInstance on manually filtered result of AssociatorNames (a4)",
        a4_far_paths,
        "manually filtered result of AssociatorNames (a4)",
        far_class, far_role)

    return a4_far_insts, a4_assoc_insts


def assert_association_a5(
        conn, profile_id,
        source_path, source_role, assoc_class, far_role, far_class):
    """
    Assert that navigation from a source instance across an association
    succeeds.

    This test performs approach a5:
      - associations: EnumerateInstances of the association and manual
        filtering.
      - far end: GetInstance on the far end keys of the associations.

    Parameters:

        conn (WBEMConnection with 'es_server' attribute)

        profile_id (string): Profile org and name as 'org:name'

        source_path (CIMInstanceName): Instance path of the source instance.

        source_role (string): Filter: Role on source end of association.

        source_class (string): Filter: Class name of source end of association.

        far_role (string): Filter: Role on far end of association.

        far_class (string): Filter: Class name of far end of association.
    """

    a5_assoc_insts = conn.EnumerateInstances(
        namespace=source_path.namespace,
        ClassName=assoc_class,
        asserted=True)

    a5_assoc_insts = [
        inst for inst in a5_assoc_insts
        if source_role in inst.path.keybindings and
        path_equal(inst.path.keybindings[source_role], source_path) and
        far_role in inst.path.keybindings and
        instance_of(conn, inst.path.keybindings[far_role], far_class)
    ]
    a5_assoc_paths = [inst.path for inst in a5_assoc_insts]
    a5_assoc_far_paths = [path.keybindings[far_role]
                          for path in a5_assoc_paths]

    a5_far_insts = []
    for path in a5_assoc_far_paths:
        _inst = conn.GetInstance(path, asserted=True)
        a5_far_insts.append(_inst)

    a5_far_paths = [inst.path for inst in a5_far_insts]

    _assert_association_consistency(
        conn, profile_id,
        source_path, source_role,
        a5_assoc_insts,
        "manually filtered result of "
        "EnumerateInstances on association class (a5)",
        a5_assoc_paths,
        "paths of manually filtered result of "
        "EnumerateInstances on association class (a5)",
        assoc_class,
        a5_far_insts,
        "GetInstance on far ends of manually filtered result of "
        "EnumerateInstances on association class (a5)",
        a5_far_paths,
        "far ends of manually filtered result of "
        "EnumerateInstances on association class (a5)",
        far_class, far_role)

    return a5_far_insts, a5_assoc_insts


def assert_association_a6(
        conn, profile_id,
        source_path, source_role, assoc_class, far_role, far_class):
    """
    Assert that navigation from a source instance across an association
    succeeds.

    This test performs approach a6:
      - associations: EnumerateInstanceNames of the association and manual
        filtering, followed by GetInstance.
      - far end: GetInstance on the far end keys of the associations.

    Parameters:

        conn (WBEMConnection with 'es_server' attribute)

        profile_id (string): Profile org and name as 'org:name'

        source_path (CIMInstanceName): Instance path of the source instance.

        source_role (string): Filter: Role on source end of association.

        source_class (string): Filter: Class name of source end of association.

        far_role (string): Filter: Role on far end of association.

        far_class (string): Filter: Class name of far end of association.
    """

    a6_assoc_paths = conn.EnumerateInstanceNames(
        namespace=source_path.namespace,
        ClassName=assoc_class,
        asserted=True)

    a6_assoc_paths = [
        path for path in a6_assoc_paths
        if source_role in path.keybindings and
        path_equal(path.keybindings[source_role], source_path) and
        far_role in path.keybindings and
        instance_of(conn, path.keybindings[far_role], far_class)
    ]
    a6_assoc_far_paths = [path.keybindings[far_role]
                          for path in a6_assoc_paths]

    a6_assoc_insts = []
    for path in a6_assoc_paths:
        _inst = conn.GetInstance(path, asserted=True)
        a6_assoc_insts.append(_inst)

    a6_far_insts = []
    for path in a6_assoc_far_paths:
        _inst = conn.GetInstance(path, asserted=True)
        a6_far_insts.append(_inst)

    a6_far_paths = [inst.path for inst in a6_far_insts]

    _assert_association_consistency(
        conn, profile_id,
        source_path, source_role,
        a6_assoc_insts,
        "GetInstance on manually filtered result of "
        "EnumerateInstanceNames on association class (a6)",
        a6_assoc_paths,
        "manually filtered result of "
        "EnumerateInstanceNames on association class (a6)",
        assoc_class,
        a6_far_insts,
        "GetInstance on far ends of manually filtered result of "
        "EnumerateInstanceNames on association class (a6)",
        a6_far_paths,
        "far ends of manually filtered result of "
        "EnumerateInstanceNames on association class (a6)",
        far_class, far_role)

    return a6_far_insts, a6_assoc_insts


def _assert_association_consistency(
        conn, profile_id,
        source_path, source_role,
        assoc_insts, assoc_insts_msg, assoc_paths, assoc_paths_msg,
        assoc_class,
        far_insts, far_insts_msg, far_paths, far_paths_msg,
        far_class, far_role):
    """
    Internal function that asserts the consistency of the result of
    navigating from a source instance across an association.
    """
    if len(far_insts) != len(far_paths):
        raise AssertionError(
            _format("Server {0} at {1}: Number of far end instances {2} ({3}) "
                    "does not match number of far end paths {4} ({5})",
                    conn.es_server.nickname, conn.url,
                    len(far_insts), far_insts_msg,
                    len(far_paths), far_paths_msg))

    if len(assoc_insts) != len(assoc_paths):
        raise AssertionError(
            _format("Server {0} at {1}: Number of association instances {2} "
                    "({3}) does not match number of association paths "
                    "{4} ({5})",
                    conn.es_server.nickname, conn.url,
                    len(assoc_insts), assoc_insts_msg,
                    len(assoc_paths), assoc_paths_msg))

    if len(far_insts) != len(assoc_insts):
        raise AssertionError(
            _format("Server {0} at {1}: Number of far end instances {2} ({3}) "
                    "does not match number of association instances {4} ({5})",
                    conn.es_server.nickname, conn.url,
                    len(far_insts), far_insts_msg,
                    len(assoc_insts), assoc_insts_msg))

    assert_instance_of(conn, far_insts, far_class)
    for inst in far_insts:
        assert_instance_consistency(conn, inst, inst.path)
    for path in far_paths:
        assert_path_in(
            conn, path, far_paths_msg,
            far_insts, "path of {0}".format(far_insts_msg))

    assert_instance_of(conn, assoc_insts, assoc_class)
    for inst in assoc_insts:
        assert_instance_consistency(conn, inst, inst.path)
        assert source_role in inst.path.keybindings
        assert_path_equal(
            conn,
            inst.path.keybindings[source_role],
            "source end {0!r} of {1}".format(source_role, assoc_insts_msg),
            source_path,
            "source instance")
        assert far_role in inst.path.keybindings
        assert_path_in(
            conn,
            inst.path.keybindings[far_role],
            "far end {0!r} of {1}".format(far_role, assoc_insts_msg),
            far_paths,
            far_paths_msg)
    for path in assoc_paths:
        assert_path_in(
            conn,
            path, assoc_paths_msg,
            assoc_insts, "path of {0}".format(assoc_insts_msg))

    # Check consistency across the association approaches
    # Py test does not seem to have a reliable order of executing the
    # testcases w.r.t. items in fixtures. Therefore, we have to assume
    # that this function is invoked in arbitrary order w.r.t. the
    # association approaches. The algorithn we use is that the
    # first approach defines the results all subsequent approaches
    # compare against.
    prefix = ':'.join([profile_id, source_path.to_wbem_uri(),
                       source_role, assoc_class, far_role, far_class])
    far_paths_id = prefix + ':far_paths'
    assoc_paths_id = prefix + ':assoc_paths'
    if not OBJECT_CACHE.has_list(conn.url, far_paths_id):
        # This is the first approach executed (not necessarily a1).
        # Store the results in the object cache.
        OBJECT_CACHE.add_list(
            conn.url, far_paths_id, far_paths)
        OBJECT_CACHE.add_list(
            conn.url, assoc_paths_id, assoc_paths)
    else:
        # This is not the first approach executed.

        # Retrieve the result of the first approach from the object cache.
        first_far_paths = OBJECT_CACHE.get_list(
            conn.url, far_paths_id)
        first_assoc_paths = OBJECT_CACHE.get_list(
            conn.url, assoc_paths_id)

        # Check consistency with first approach
        assert len(assoc_paths) == len(first_assoc_paths)
        for path in assoc_paths:
            assert_path_in(
                conn,
                path,
                assoc_paths_msg,
                first_assoc_paths,
                assoc_paths_msg + " of first executed association approach")
        assert len(far_paths) == len(first_far_paths)
        for path in far_paths:
            assert_path_in(
                conn,
                path,
                far_paths_msg,
                first_far_paths,
                far_paths_msg + " of first executed association approach")


def std_uri(instance):
    """
    Return canonical WBEM URI of the path of the instance, nullifying the
    host, or the empty string.
    """
    if instance is None or instance.path is None:
        return ''

    path = instance.path.copy()
    path.host = None
    return path.to_wbem_uri(format='canonical')


def assert_profile_tree(conn, profile_inst, profile_ancestry,
                        reference_direction, tls_org, tls_name):
    """
    Assert that a profile tree is a tree without circular references,
    when navigating to referenced profiles in the specified reference
    direction.

    Parameters:

        conn (WBEMConnection with 'es_server' attribute)

        profile_inst (CIMInstance): Profile that is tested.

        profile_ancestry (dict): Profile ancestry up to the top level spec,
          as a dict with:
            * key: std_uri of profile that is tested.
            * value: std_uri of its referencing profile (or spec, for the top).

        reference_direction (string): Reference direction to use for the test
          ('dmtf' or 'snia').

        tls_org (string), tls_name (string): Org and name of top level spec
          of the profile tree (used only for failure messages).
    """

    profile_uri = std_uri(profile_inst)

    # from pprint import pprint
    # print("Debug: assert_profile_tree called")
    # print("       profile:  {0}".format(profile_uri))
    # print("       ancestry: ")
    # for k in profile_ancestry.keys():
    #     print("                 {0}".format(k))

    if reference_direction == 'dmtf':
        result_role_down = 'Antecedent'
        # result_role_up = 'Dependent'
    else:
        assert reference_direction == 'snia'
        result_role_down = 'Dependent'
        # result_role_up = 'Antecedent'

    sub_profile_insts = conn.Associators(
        profile_inst.path,
        AssocClass='CIM_ReferencedProfile',
        ResultRole=result_role_down,
        asserted=True)

    if not sub_profile_insts:
        # The profile is a leaf profile, i.e. does not reference any further
        # profiles.
        pass
    else:
        for sub_profile_inst in sub_profile_insts:

            sub_profile_uri = std_uri(sub_profile_inst)

            if sub_profile_uri in profile_ancestry:
                raise AssertionError(
                    "Server {0} at {1}: Profile tree under top level "
                    "specification {2} {3!r} has a circular reference: "
                    "Profile at {4} references profile at {5} which is "
                    "already in its own reference ancestry {6}".
                    format(conn.es_server.nickname, conn.url,
                           tls_org, tls_name,
                           profile_uri, sub_profile_uri,
                           profile_ancestry.keys()))

            profile_ancestry[sub_profile_uri] = profile_uri

            assert_profile_tree(
                conn, sub_profile_inst, profile_ancestry,
                reference_direction, tls_org, tls_name)

            del profile_ancestry[sub_profile_uri]
