"""
End2end tests for generic profile related stuff (advertisement, central
instances).
"""

from __future__ import absolute_import, print_function

import warnings
import pytest
from pywbem import WBEMServer, ValueMapping

# Note: The wbem_connection fixture uses the server_definition fixture, and
# due to the way py.test searches for fixtures, it also need to be imported.
from pytest_end2end import wbem_connection, server_definition  # noqa: F401, E501
from pytest_end2end import profile_definition  # noqa: F401, E501
from pytest_end2end import PROFILE_DEFINITION_DICT
from _utils import latest_profile_inst


def test_get_central_instances(  # noqa: F811
        wbem_connection, profile_definition):
    """
    Test that the central instances of the profile can be determined using
    WBEMServer.gen_central_instances().
    """
    server = WBEMServer(wbem_connection)

    # Verify that the profile to be tested is advertised by the server
    # and skip the profile if not advertised.
    profile_insts = server.get_selected_profiles(
        profile_definition['registered_org'],
        profile_definition['registered_name'])

    if profile_definition['type'] == 'pattern':
            pytest.skip("{0} {1} is a pattern on server {2} at {3}".
                        format(profile_definition['registered_org'],
                               profile_definition['registered_name'],
                               wbem_connection.server_definition.nickname,
                               wbem_connection.url))
    if not profile_insts:
        pytest.skip("{0} {1} profile is not advertised on server {2} at {3}".
                    format(profile_definition['registered_org'],
                           profile_definition['registered_name'],
                           wbem_connection.server_definition.nickname,
                           wbem_connection.url))

    # In case there is more than one version advertised, use only the latest
    # version.
    profile_inst = latest_profile_inst(profile_insts)

    # Check test case consistency
    if profile_definition['central_class'] is None:
        raise ValueError(
            "Profile definition error: The central_class attribute of "
            "item {0} {1!r} with type {0} must be non-null".
            format(profile_definition['registered_org'],
                   profile_definition['registered_name'],
                   profile_definition['type']))
    # Note: Even for component profiles, we allow scoping class and scoping
    # path to be unspecified (= None), because they do not matter if the
    # central class methodology is implemented.

    # Function to be tested
    server.get_central_instances(
        profile_inst.path,
        central_class=profile_definition['central_class'],
        scoping_class=profile_definition['scoping_class'],
        scoping_path=profile_definition['scoping_path'],
        reference_direction=profile_definition['reference_direction'])

    # We intentionally do not check a minimum number of central instances,
    # because it is generally valid for profile implementations not to require
    # at least one central instance.


def test_warn_undefined_profiles(  # noqa: F811
        wbem_connection):
    """
    Warn if the server advertises profiles not defined in profiles.yml.
    """
    server = WBEMServer(wbem_connection)
    server_def = wbem_connection.server_definition

    org_vm = ValueMapping.for_property(server, server.interop_ns,
                                       'CIM_RegisteredProfile',
                                       'RegisteredOrganization')

    for inst in server.profiles:
        org = org_vm.tovalues(inst['RegisteredOrganization'])
        name = inst['RegisteredName']
        version = inst['RegisteredVersion']
        pd_key = '{0}:{1}'.format(org, name)
        if pd_key not in PROFILE_DEFINITION_DICT:
            warnings.warn(
                "{0} {1!r} profile version {2} advertised on server {3} "
                "(at {4}) is not defined in profiles.yml".
                format(org, name, version, server_def.nickname,
                       wbem_connection.url),
                RuntimeWarning)
