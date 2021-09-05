"""
End2end tests for WBEMServer class.
"""

from __future__ import absolute_import, print_function

import re

from .utils.utils import server_func_asserted, server_prop_asserted
from .utils.pytest_extensions import skip_if_unsupported_capability

# Note: The wbem_connection fixture uses the es_server fixture, and
# due to the way py.test searches for fixtures, it also need to be imported.
# pylint: disable=unused-import,wrong-import-order
from .utils.pytest_extensions import wbem_connection  # noqa: F401
from pytest_easy_server import es_server  # noqa: F401
from .utils.pytest_extensions import default_namespace  # noqa: F401
# pylint: enable=unused-import,wrong-import-order

# pylint: disable=wrong-import-position, wrong-import-order, invalid-name
from ..utils import import_installed
pywbem = import_installed('pywbem')
from pywbem import WBEMServer  # noqa: E402
# pylint: enable=wrong-import-position, wrong-import-order, invalid-name


def test_namespace_consistency(
        default_namespace, wbem_connection):  # noqa: F811
    # pylint: disable=redefined-outer-name
    """
    Test that the Interop namespace and all namespaces and namespace paths can
    be determined, and verify consistency between them.
    """
    skip_if_unsupported_capability(wbem_connection, 'interop')

    wbem_connection.default_namespace = default_namespace
    server = WBEMServer(wbem_connection)
    msg = "for server at URL {0!r}".format(wbem_connection.url)

    interop_ns_lower = server_prop_asserted(server, 'interop_ns').lower()
    # pylint: disable=not-an-iterable
    namespaces_lower = [ns.lower()
                        for ns in server_prop_asserted(server, 'namespaces')]
    namespace_paths = server_prop_asserted(server, 'namespace_paths')

    assert interop_ns_lower in namespaces_lower, msg

    # Note: One server has been found that supports the Interop namespace, but
    # does not represent it as a CIM instance. In that case, server.namespaces
    # contains the Interop namespace while server.namespace_paths does not.
    # The following checks accomodate that.
    # pylint: disable=not-an-iterable
    for ns_path in namespace_paths:
        assert ns_path.namespace.lower() == interop_ns_lower, msg
        ns_path_name_lower = ns_path['Name'].lower()
        assert ns_path_name_lower in namespaces_lower, msg


def test_namespace_getinstance(
        default_namespace, wbem_connection):  # noqa: F811
    # pylint: disable=redefined-outer-name
    """
    Test that GetInstance on the instance paths of all namespaces succeeds.
    """
    skip_if_unsupported_capability(wbem_connection, 'interop')

    wbem_connection.default_namespace = default_namespace
    server = WBEMServer(wbem_connection)
    msg = "for server at URL {0!r}".format(wbem_connection.url)

    namespace_paths = server_prop_asserted(server, 'namespace_paths')

    # pylint: disable=not-an-iterable
    for path in namespace_paths:

        inst = wbem_connection.GetInstance(
            path,
            asserted=True)

        inst_name_lower = inst['Name'].lower()
        path_name_lower = path['Name'].lower()
        assert inst_name_lower == path_name_lower, msg


def test_brand_version(
        default_namespace, wbem_connection):  # noqa: F811
    # pylint: disable=redefined-outer-name
    """
    Test that the server brand and version can be determined.
    """
    skip_if_unsupported_capability(wbem_connection, 'interop')

    wbem_connection.default_namespace = default_namespace
    server = WBEMServer(wbem_connection)
    msg = "for server at URL {0!r}".format(wbem_connection.url)

    brand = server_prop_asserted(server, 'brand')
    assert brand is not None, msg

    # Note: The version is None if it cannot be determined.
    # We check that it begins with a digit and does not contain blanks.
    version = server_prop_asserted(server, 'version')
    if version is not None:
        assert re.match(r'^[0-9][^ ]*$', version), \
            "version={0!r}; {1}".format(version, msg)


def test_cimom_inst(
        default_namespace, wbem_connection):  # noqa: F811
    # pylint: disable=redefined-outer-name
    """
    Test that the instance representing the server can be determined and that
    GetInstance on it succeeds.
    """
    skip_if_unsupported_capability(wbem_connection, 'interop')

    wbem_connection.default_namespace = default_namespace
    server = WBEMServer(wbem_connection)
    msg = "for server at URL {0!r}".format(wbem_connection.url)

    cimom_inst = server_prop_asserted(server, 'cimom_inst')

    interop_ns_lower = server_prop_asserted(server, 'interop_ns').lower()

    assert cimom_inst.path is not None, msg
    assert cimom_inst.path.namespace.lower() == interop_ns_lower, msg

    get_inst = wbem_connection.GetInstance(
        cimom_inst.path,
        asserted=True)

    assert cimom_inst == get_inst, msg


def test_profiles(
        default_namespace, wbem_connection):  # noqa: F811
    # pylint: disable=redefined-outer-name
    """
    Test that the registered profiles advertised by the server can be
    determined and that GetInstance on them succeeds.
    """
    skip_if_unsupported_capability(wbem_connection, 'profiles')

    wbem_connection.default_namespace = default_namespace
    server = WBEMServer(wbem_connection)
    msg = "for server at URL {0!r}".format(wbem_connection.url)

    profile_insts = server_prop_asserted(server, 'profiles')

    interop_ns_lower = server_prop_asserted(server, 'interop_ns').lower()

    # pylint: disable=not-an-iterable
    for profile_inst in profile_insts:
        assert profile_inst.path is not None, msg
        assert profile_inst.path.namespace.lower() == interop_ns_lower, msg
        assert profile_inst['RegisteredOrganization'] is not None, msg
        assert profile_inst['RegisteredName'] is not None, msg
        assert profile_inst['RegisteredVersion'] is not None, msg

        get_inst = wbem_connection.GetInstance(
            profile_inst.path,
            asserted=True)

        assert profile_inst == get_inst, msg


def test_get_selected_profiles_no_filter(
        default_namespace, wbem_connection):  # noqa: F811
    # pylint: disable=redefined-outer-name
    """
    Test that the get_selected_profiles() method without filtering returns
    the same profiles as the profiles attribute.
    """
    skip_if_unsupported_capability(wbem_connection, 'profiles')

    wbem_connection.default_namespace = default_namespace
    server = WBEMServer(wbem_connection)
    msg = "for server at URL {0!r}".format(wbem_connection.url)

    profile_insts = server_prop_asserted(server, 'profiles')
    all_profile_insts = server_func_asserted(server, 'get_selected_profiles')

    assert len(profile_insts) == len(all_profile_insts), msg
    # pylint: disable=not-an-iterable
    for inst in profile_insts:
        assert inst in all_profile_insts, msg
