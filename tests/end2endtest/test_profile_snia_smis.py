"""
End2end tests for SNIA SMI-S registered specification.
"""

from __future__ import absolute_import, print_function

import pytest

from pywbem import WBEMServer

# Note: The wbem_connection fixture uses the server_definition fixture, and
# due to the way py.test searches for fixtures, it also need to be imported.
# pylint: disable=unused-import, line-too-long
from .utils.pytest_extensions import wbem_connection, server_definition  # noqa: F401, E501
from .utils.assertions import assert_instance_of, assert_profile_tree, std_uri
from .utils.utils import server_func_asserted
# pylint: enable=unused-import, line-too-long

# Organization and name of the registered specification
SPEC_ORG = 'SNIA'
SPEC_NAME = 'SMI-S'
REFERENCE_DIRECTION = 'snia'


def test_snia_smis_to_profile_not_swapped(wbem_connection):  # noqa: F811
    """
    Test that the SMI-S specification does not reference its profiles via
    CIM_ElementConformsToProfile with its ends incorrectly swapped.
    """
    server = WBEMServer(wbem_connection)
    server_def = wbem_connection.server_definition

    spec_insts = server_func_asserted(
        server, 'get_selected_profiles',
        SPEC_ORG, SPEC_NAME)
    if not spec_insts:
        pytest.skip("Server {0} at {1}: The {2} {3!r} specification is not "
                    "advertised".
                    format(server_def.nickname, wbem_connection.url,
                           SPEC_ORG, SPEC_NAME))

    for spec_inst in spec_insts:

        profiles_swapped = server.conn.Associators(
            spec_inst.path,
            AssocClass='CIM_ElementConformsToProfile',
            ResultRole='ConformantStandard',  # swapped role
            ResultClass='CIM_RegisteredProfile',
            asserted=True)

        if profiles_swapped:
            raise AssertionError(
                "Server {0} at {1}: The instance representing the {2} {3!r} "
                "specification references {4} profiles via "
                "CIM_ElementConformsToProfile using incorrectly swapped roles "
                "so that ConformantStandard is on the profile side".
                format(server_def.nickname, wbem_connection.url,
                       SPEC_ORG, SPEC_NAME, len(profiles_swapped)))


def test_snia_smis_to_profile_not_reffed(wbem_connection):  # noqa: F811
    """
    Test that the SMI-S specification does not reference its profiles via
    CIM_ReferencedProfile.
    """
    server = WBEMServer(wbem_connection)
    server_def = wbem_connection.server_definition

    spec_insts = server_func_asserted(
        server, 'get_selected_profiles',
        SPEC_ORG, SPEC_NAME)
    if not spec_insts:
        pytest.skip("Server {0} at {1}: The {2} {3!r} specification is not "
                    "advertised".
                    format(server_def.nickname, wbem_connection.url,
                           SPEC_ORG, SPEC_NAME))

    for spec_inst in spec_insts:

        profiles_reffed = server.conn.Associators(
            spec_inst.path,
            AssocClass='CIM_ReferencedProfile',
            ResultClass='CIM_RegisteredProfile',
            asserted=True)

        if profiles_reffed:
            raise AssertionError(
                "Server {0} at {1}: The instance representing the {2} {3!r} "
                "specification incorrectly references {4} profiles via "
                "CIM_ReferencedProfile (it should do that via "
                "CIM_ElementConformsToProfile)".
                format(server_def.nickname, wbem_connection.url,
                       SPEC_ORG, SPEC_NAME,
                       len(profiles_reffed)))


def test_snia_smis_profile_tree_not_circular(wbem_connection):  # noqa: F811
    """
    Test that the SMI-S specification has a profile tree without circular
    references, when navigating to referenced profiles in the SNIA reference
    direction.
    """
    server = WBEMServer(wbem_connection)
    server_def = wbem_connection.server_definition

    spec_insts = server_func_asserted(
        server, 'get_selected_profiles',
        SPEC_ORG, SPEC_NAME)
    if not spec_insts:
        pytest.skip("Server {0} at {1}: The {2} {3!r} specification is not "
                    "advertised".
                    format(server_def.nickname, wbem_connection.url,
                           SPEC_ORG, SPEC_NAME))

    for spec_inst in spec_insts:

        spec_inst_uri = std_uri(spec_inst)

        # print("\nDebug: spec:     {0}".format(spec_inst_uri))

        top_profiles = server.conn.Associators(
            spec_inst.path,
            AssocClass='CIM_ElementConformsToProfile',
            ResultRole='ManagedElement',
            asserted=True)

        assert_instance_of(server.conn, top_profiles, 'CIM_RegisteredProfile')

        # Profile ancestry for the each specification instance:
        # * key: std_uri of profile
        # * value: std_uri of its referencing profile (or spec, for the top)
        profile_ancestry = dict()

        for top_profile_inst in top_profiles:

            top_profile_uri = std_uri(top_profile_inst)

            profile_ancestry[top_profile_uri] = spec_inst_uri

            assert_profile_tree(
                wbem_connection, top_profile_inst, profile_ancestry,
                REFERENCE_DIRECTION, SPEC_ORG, SPEC_NAME)

            del profile_ancestry[top_profile_uri]
