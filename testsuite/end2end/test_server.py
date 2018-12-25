"""
End2end tests for WBEMServer class.
"""

from __future__ import absolute_import, print_function

# Note: The wbem_connection fixture uses the server_definition fixture, and
# due to the way py.test searches for fixtures, it also need to be imported.
from pytest_end2end import wbem_connection, server_definition  # noqa: F401, E501
from pytest_end2end import default_namespace  # noqa: F401, E501

from pywbem import WBEMServer


def test_namespace_consistency(  # noqa: F811
        wbem_connection, default_namespace):
    """
    Test that the Interop namespace and all namespaces and namespace paths can
    be determined, and verify consistency between them.
    """
    wbem_connection.default_namespace = default_namespace
    server = WBEMServer(wbem_connection)
    msg = "for server at URL {0!r}".format(wbem_connection.url)

    interop_ns_lower = server.interop_ns.lower()
    namespaces_lower = [ns.lower() for ns in server.namespaces]
    namespace_paths = server.namespace_paths

    assert interop_ns_lower in namespaces_lower, msg

    # Note: One server has been found that supports the Interop namespace, but
    # does not represent it as a CIM instance. In that case, server.namespaces
    # contains the Interop namespace while server.namespace_paths does not.
    # The following checks accomodate that.
    for ns_path in namespace_paths:
        assert ns_path.namespace.lower() == interop_ns_lower, msg
        ns_path_name_lower = ns_path['Name'].lower()
        assert ns_path_name_lower in namespaces_lower, msg


def test_namespace_getinstance(  # noqa: F811
        wbem_connection, default_namespace):
    """
    Test that GetInstance on the instance paths of all namespaces succeeds.
    """
    wbem_connection.default_namespace = default_namespace
    server = WBEMServer(wbem_connection)
    msg = "for server at URL {0!r}".format(wbem_connection.url)

    namespace_paths = server.namespace_paths

    for path in namespace_paths:

        inst = wbem_connection.GetInstance(path)

        inst_name_lower = inst['Name'].lower()
        path_name_lower = path['Name'].lower()
        assert inst_name_lower == path_name_lower, msg


def test_brand_version(  # noqa: F811
        wbem_connection, default_namespace):
    """
    Test that the server brand and version can be determined.
    """
    wbem_connection.default_namespace = default_namespace
    server = WBEMServer(wbem_connection)
    msg = "for server at URL {0!r}".format(wbem_connection.url)

    brand = server.brand
    version = server.version

    assert brand is not None, msg
    assert version is not None, msg


def test_cimom_inst(  # noqa: F811
        wbem_connection, default_namespace):
    """
    Test that the instance representing the server can be determined and that
    GetInstance on it succeeds.
    """
    wbem_connection.default_namespace = default_namespace
    server = WBEMServer(wbem_connection)
    msg = "for server at URL {0!r}".format(wbem_connection.url)

    cimom_inst = server.cimom_inst

    interop_ns_lower = server.interop_ns.lower()

    assert cimom_inst.path is not None, msg
    assert cimom_inst.path.namespace.lower() == interop_ns_lower, msg

    get_inst = wbem_connection.GetInstance(cimom_inst.path)

    assert cimom_inst == get_inst, msg


def test_profiles(  # noqa: F811
        wbem_connection, default_namespace):
    """
    Test that the registered profiles advertised by the server can be
    determined and that GetInstance on them succeeds.
    """
    wbem_connection.default_namespace = default_namespace
    server = WBEMServer(wbem_connection)
    msg = "for server at URL {0!r}".format(wbem_connection.url)

    profile_insts = server.profiles

    interop_ns_lower = server.interop_ns.lower()

    for profile_inst in profile_insts:
        assert profile_inst.path is not None, msg
        assert profile_inst.path.namespace.lower() == interop_ns_lower, msg
        assert profile_inst['RegisteredOrganization'] is not None, msg
        assert profile_inst['RegisteredName'] is not None, msg
        assert profile_inst['RegisteredVersion'] is not None, msg

        get_inst = wbem_connection.GetInstance(profile_inst.path)

        assert profile_inst == get_inst, msg


def test_get_selected_profiles_no_filter(  # noqa: F811
        wbem_connection, default_namespace):
    """
    Test that the get_selected_profiles() method without filtering returns
    the same profiles as the profiles attribute.
    """
    wbem_connection.default_namespace = default_namespace
    server = WBEMServer(wbem_connection)
    msg = "for server at URL {0!r}".format(wbem_connection.url)

    profile_insts = server.profiles
    all_profile_insts = server.get_selected_profiles()

    assert len(profile_insts) == len(all_profile_insts), msg
    for inst in profile_insts:
        assert inst in all_profile_insts, msg
