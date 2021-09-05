"""
End2end tests for generic profile related stuff (advertisement, central
instances).
"""

from __future__ import absolute_import, print_function

import pytest

from .utils.pytest_extensions import skip_if_unsupported_capability
from .utils.utils import latest_profile_inst, server_func_asserted, \
    server_prop_asserted

# Note: The wbem_connection fixture uses the es_server fixture, and
# due to the way py.test searches for fixtures, it also need to be imported.
# pylint: disable=unused-import,wrong-import-order
from .utils.pytest_extensions import wbem_connection  # noqa: F401
from pytest_easy_server import es_server  # noqa: F401
from .utils.pytest_extensions import assert_association_func  # noqa: F401
from .utils.pytest_extensions import profile_definition  # noqa: F401
from .utils.pytest_extensions import single_profile_definition  # noqa: F401
# pylint: enable=unused-import,wrong-import-order

# pylint: disable=wrong-import-position, wrong-import-order, invalid-name
from ..utils import import_installed
pywbem = import_installed('pywbem')
from pywbem import WBEMServer, ValueMapping  # noqa: E402
# pylint: enable=wrong-import-position, wrong-import-order, invalid-name


def test_get_central_instances(
        profile_definition, wbem_connection):  # noqa: F811
    # pylint: disable=redefined-outer-name
    """
    Test that the central instances of the profile can be determined using
    WBEMServer.gen_central_instances().
    """
    skip_if_unsupported_capability(wbem_connection, 'smis')

    server = WBEMServer(wbem_connection)

    profile_org = profile_definition['registered_org']
    profile_name = profile_definition['registered_name']
    profile_version = profile_definition['registered_version']  # May be None

    # Verify that the profile to be tested is advertised by the server
    # and skip the profile if not advertised.
    profile_insts = server_func_asserted(
        server, 'get_selected_profiles',
        registered_org=profile_org,
        registered_name=profile_name,
        registered_version=profile_version)

    if not profile_insts:
        pytest.skip("Server {0} at {1}: The {2} {3!r} profile (version {4}) "
                    "is not advertised".
                    format(wbem_connection.es_server.nickname,
                           wbem_connection.url, profile_org,
                           profile_name, profile_version or 'any'))

    # In case there is more than one version advertised, use only the latest
    # version.
    profile_inst = latest_profile_inst(profile_insts)

    # Check test case consistency
    if profile_definition['central_class'] is None:
        raise ValueError(
            "Profile definition error: The central_class attribute of "
            "the {0} {1!r} profile (version {2}) with type {3} must be "
            "non-null".
            format(profile_org, profile_name, profile_version or 'any',
                   profile_definition['type']))
    # Note: Even for component profiles, we allow scoping class and scoping
    # path to be unspecified (= None), because they do not matter if the
    # central class methodology is implemented.

    # Function to be tested
    server_func_asserted(
        server, 'get_central_instances',
        profile_path=profile_inst.path,
        central_class=profile_definition['central_class'],
        scoping_class=profile_definition['scoping_class'],
        scoping_path=profile_definition['scoping_path'],
        reference_direction=profile_definition['reference_direction'])

    # We intentionally do not check a minimum number of central instances,
    # because it is generally valid for profile implementations not to require
    # at least one central instance.


def test_undefined_profiles(wbem_connection):  # noqa: F811
    # pylint: disable=redefined-outer-name
    """
    Test that the server advertises only profiles defined in profiles.yml.
    """
    skip_if_unsupported_capability(wbem_connection, 'smis')

    server = WBEMServer(wbem_connection)

    org_vm = ValueMapping.for_property(
        server,
        server_prop_asserted(server, 'interop_ns'),
        'CIM_RegisteredProfile',
        'RegisteredOrganization')

    undefined_profile_ids = []
    # pylint: disable=not-an-iterable
    for inst in server_prop_asserted(server, 'profiles'):
        org = org_vm.tovalues(inst['RegisteredOrganization'])
        name = inst['RegisteredName']
        version = inst['RegisteredVersion']
        if not single_profile_definition(org, name, version):
            undefined_profile_ids.append(
                "{0} {1!r} {2}".format(org, name, version))

    if undefined_profile_ids:
        undefined_profile_lines = '\n'.join(undefined_profile_ids)
        raise AssertionError(
            "Server {0} at {1} advertises the following profiles that are "
            "not defined in profiles.yml. This may be caused by incorrectly "
            "implemented profile names:\n{2}".
            format(wbem_connection.es_server.nickname, wbem_connection.url,
                   undefined_profile_lines))
