"""
End2end tests for generic profile related stuff (advertisement, central
instances).
"""

from __future__ import absolute_import, print_function

import pytest
from pywbem import WBEMServer, ValueMapping

# Note: The wbem_connection fixture uses the server_definition fixture, and
# due to the way py.test searches for fixtures, it also need to be imported.
# pylint: disable=unused-import, line-too-long
from .utils.pytest_extensions import wbem_connection, server_definition  # noqa: F401, E501
from .utils.pytest_extensions import profile_definition  # noqa: F401, E501
from .utils.pytest_extensions import PROFILE_DEFINITION_DICT
from .utils.utils import latest_profile_inst, server_func_asserted, \
    server_prop_asserted
# pylint: enable=unused-import, line-too-long


def test_get_central_instances(
        profile_definition, wbem_connection):  # noqa: F811
    # pylint: disable=redefined-outer-name
    """
    Test that the central instances of the profile can be determined using
    WBEMServer.gen_central_instances().
    """
    server = WBEMServer(wbem_connection)

    # Verify that the profile to be tested is advertised by the server
    # and skip the profile if not advertised.
    profile_insts = server_func_asserted(
        server, 'get_selected_profiles',
        profile_definition['registered_org'],
        profile_definition['registered_name'])

    if not profile_insts:
        pytest.skip("Server {0} at {1}: The {2} {3!r} profile is not "
                    "advertised".
                    format(wbem_connection.server_definition.nickname,
                           wbem_connection.url,
                           profile_definition['registered_org'],
                           profile_definition['registered_name']))

    # In case there is more than one version advertised, use only the latest
    # version.
    profile_inst = latest_profile_inst(profile_insts)

    # Check test case consistency
    if profile_definition['central_class'] is None:
        raise ValueError(
            "Profile definition error: The central_class attribute of "
            "item {0} {1!r} with type {2} must be non-null".
            format(profile_definition['registered_org'],
                   profile_definition['registered_name'],
                   profile_definition['type']))
    # Note: Even for component profiles, we allow scoping class and scoping
    # path to be unspecified (= None), because they do not matter if the
    # central class methodology is implemented.

    # Function to be tested
    server_func_asserted(
        server, 'get_central_instances',
        profile_inst.path,
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
    server = WBEMServer(wbem_connection)
    server_def = wbem_connection.server_definition

    org_vm = ValueMapping.for_property(
        server,
        server_prop_asserted(server, 'interop_ns'),
        'CIM_RegisteredProfile',
        'RegisteredOrganization')

    undefined_profile_ids = []
    for inst in server_prop_asserted(server, 'profiles'):
        org = org_vm.tovalues(inst['RegisteredOrganization'])
        name = inst['RegisteredName']
        version = inst['RegisteredVersion']
        pd_key = '{0}:{1}'.format(org, name)
        if pd_key not in PROFILE_DEFINITION_DICT:
            undefined_profile_ids.append(
                "{0} {1!r} {2}".format(org, name, version))

    if undefined_profile_ids:
        undefined_profile_lines = '\n'.join(undefined_profile_ids)
        raise AssertionError(
            "Server {0} at {1} advertises the following profiles that are "
            "not defined in profiles.yml. This may be caused by incorrectly "
            "implemented profile names:\n{2}".
            format(server_def.nickname, wbem_connection.url,
                   undefined_profile_lines))
