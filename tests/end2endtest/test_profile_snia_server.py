"""
End2end tests for SNIA 'Server' profile.
"""

from __future__ import absolute_import, print_function

import warnings

from pywbem import ToleratedServerIssueWarning
from pywbem._utils import _format

# Note: The wbem_connection fixture uses the server_definition fixture, and
# due to the way py.test searches for fixtures, it also must be imported.

# pylint: disable=line-too-long,unused-import
from .utils.pytest_extensions import wbem_connection, server_definition  # noqa: F401, E501
from .utils.pytest_extensions import assert_association_func  # noqa: F401
# pylint: enable=line-too-long,unused-import

from .utils.pytest_extensions import ProfileTest
from .utils.assertions import assert_number_of_instances_equal, \
    assert_number_of_instances_minimum, assert_instance_of, \
    assert_instance_consistency, assert_mandatory_properties, \
    assert_property_one_of, assert_property_contains
from .utils.utils import server_func_asserted, server_prop_asserted


class Test_SNIA_Server_Profile(ProfileTest):
    """
    All end2end tests for SNIA 'Server' profile.
    """

    def init_profile(self, conn):  # pylint: disable=arguments-differ
        super(Test_SNIA_Server_Profile, self).init_profile(
            conn, profile_org='SNIA', profile_name='Server')

    def test_get_central_instances(self, wbem_connection):  # noqa: F811
        # pylint: disable=redefined-outer-name
        """
        Test WBEMServer.get_central_instances() for this profile.
        """
        self.init_profile(wbem_connection)

        central_inst_paths = server_func_asserted(
            self.server, 'get_central_instances',
            self.profile_inst.path,
            central_class=self.profile_definition['central_class'],
            scoping_class=self.profile_definition['scoping_class'],
            scoping_path=self.profile_definition['scoping_path'],
            reference_direction=self.profile_definition['reference_direction'])

        central_insts_msg = _format(
            "central instances of profile {0} {1!A}",
            self.profile_definition['registered_org'],
            self.profile_definition['registered_name'])

        # Check that there is just one central instance for this profile
        assert_number_of_instances_equal(
            wbem_connection, central_inst_paths, central_insts_msg, 1)

    def test_central_instance(self, wbem_connection):  # noqa: F811
        # pylint: disable=redefined-outer-name
        """
        Test the CIM_ObjectManager central instance.
        """
        self.init_central_instances(wbem_connection)
        central_inst_path = self.central_inst_paths[0]

        assert_instance_of(
            wbem_connection, central_inst_path, 'CIM_ObjectManager')

        central_inst = self.conn.GetInstance(
            central_inst_path,
            asserted=True)

        assert_instance_of(
            wbem_connection, central_inst, 'CIM_ObjectManager')

        assert_instance_consistency(
            wbem_connection, central_inst, central_inst_path)

        assert_mandatory_properties(
            wbem_connection, central_inst,
            ['SystemCreationClassName', 'SystemName', 'CreationClassName',
             'Name', 'ElementName', 'Description', 'OperationalStatus',
             'Started'])

    def test_Namespace(
            self, assert_association_func, wbem_connection):  # noqa: F811
        # pylint: disable=redefined-outer-name
        """
        Test the associated CIM_Namespace instances.
        """
        self.init_central_instances(wbem_connection)
        central_inst_path = self.central_inst_paths[0]

        far_insts, _ = assert_association_func(
            conn=wbem_connection,
            profile_id=self.profile_id,
            source_path=central_inst_path,
            source_role='Antecedent',
            assoc_class='CIM_NamespaceInManager',
            far_role='Dependent',
            far_class='CIM_Namespace')

        far_insts_msg = _format(
            "CIM_Namespace instances associated via "
            "CIM_NamespaceInManager to "
            "central instance of profile {0} {1!A}",
            self.profile_definition['registered_org'],
            self.profile_definition['registered_name'])

        for inst in far_insts:

            assert_mandatory_properties(
                wbem_connection, inst,
                ['SystemCreationClassName', 'SystemName',
                 'ObjectManagerCreationClassName', 'ObjectManagerName',
                 'CreationClassName', 'Name', 'ClassType'])

        # Check that they are the namespaces determined by WBEMServer.
        # Because the Interop namespace is added if missing, we need to also
        # do that here.
        inst_names = [inst['Name'].lower() for inst in far_insts]
        interop_ns_lower = server_prop_asserted(
            self.server, 'interop_ns').lower()
        if interop_ns_lower not in inst_names:
            inst_names.append(interop_ns_lower)
        determined_names = [ns.lower()
                            for ns in server_prop_asserted(
                                self.server, 'namespaces')]

        if set(inst_names) != set(determined_names):
            raise AssertionError(
                _format("Server {0} at {1}: The namespaces ({2}) of the {3} "
                        "do not match the namespaces ({4}) determined by the "
                        "WBEMServer class",
                        wbem_connection.server_definition.nickname,
                        wbem_connection.url,
                        set(inst_names), far_insts_msg,
                        set(determined_names)))

    def test_ObjectManagerCommunicationMechanism(
            self, assert_association_func, wbem_connection):  # noqa: F811
        # pylint: disable=redefined-outer-name
        """
        Test the associated CIM_ObjectManagerCommunicationMechanism instances.
        """
        self.init_central_instances(wbem_connection)
        central_inst_path = self.central_inst_paths[0]

        far_insts, _ = assert_association_func(
            conn=wbem_connection,
            profile_id=self.profile_id,
            source_path=central_inst_path,
            source_role='Antecedent',
            assoc_class='CIM_CommMechanismForManager',
            far_role='Dependent',
            far_class='CIM_ObjectManagerCommunicationMechanism')

        far_insts_msg = _format(
            "CIM_ObjectManagerCommunicationMechanism instances associated via "
            "CIM_CommMechanismForManager to "
            "central instance of profile {0} {1!A}",
            self.profile_definition['registered_org'],
            self.profile_definition['registered_name'])

        for inst in far_insts:

            assert_mandatory_properties(
                wbem_connection, inst,
                ['SystemCreationClassName', 'SystemName', 'CreationClassName',
                 'Name', 'ElementName', 'CommunicationMechanism',
                 'FunctionalProfilesSupported', 'MultipleOperationsSupported',
                 'AuthenticationMechanismsSupported'])

            assert_property_one_of(
                wbem_connection, inst,
                'CommunicationMechanism', [2, 4])

            # Note: The SNIA Server profile mandates that the
            #       FunctionalProfilesSupported property is 0 (Unknown), but it
            #       is an array property. Even after fixing this to an array
            #       with one item 0, it does not make much sense to require
            #       that that support is not implemented just because the
            #       profile does not use it.
            # TODO 2018-12 AM: This should be brought back to SMI-S.
            try:
                assert_property_contains(
                    wbem_connection, inst,
                    'FunctionalProfilesSupported', 0)
            except AssertionError as exc:
                warnings.warn("Downgraded the following test failure to a "
                              "warning: {0}: {1}".
                              format(exc.__class__.__name__, exc),
                              ToleratedServerIssueWarning)

            # Note: The SNIA Server profile mandates that the
            #       MultipleOperationsSupported property is False, but it does
            #       not make much sense to require that that support is not
            #       implemented just because the profile does not use it.
            # TODO 2018-12 AM: This should be brought back to SMI-S.
            try:
                assert_property_one_of(
                    wbem_connection, inst,
                    'MultipleOperationsSupported', [False])
            except AssertionError as exc:
                warnings.warn("Downgraded the following test failure to a "
                              "warning: {0}: {1}".
                              format(exc.__class__.__name__, exc),
                              ToleratedServerIssueWarning)

        # Check that there is at least one associated istance
        assert_number_of_instances_minimum(
            wbem_connection, far_insts, far_insts_msg, 1)

    def test_System(
            self, assert_association_func, wbem_connection):  # noqa: F811
        # pylint: disable=redefined-outer-name
        """
        Test the associated CIM_System instance.
        """
        self.init_central_instances(wbem_connection)
        central_inst_path = self.central_inst_paths[0]

        far_insts, _ = assert_association_func(
            conn=wbem_connection,
            profile_id=self.profile_id,
            source_path=central_inst_path,
            source_role='Dependent',
            assoc_class='CIM_HostedService',
            far_role='Antecedent',
            far_class='CIM_System')

        far_insts_msg = _format(
            "CIM_System instances associated via CIM_HostedService to "
            "central instance of profile {0} {1!A}",
            self.profile_definition['registered_org'],
            self.profile_definition['registered_name'])

        for inst in far_insts:

            assert_mandatory_properties(
                wbem_connection, inst,
                ['CreationClassName', 'Name', 'NameFormat', 'Description',
                 'ElementName', 'OperationalStatus'])

            assert_property_one_of(
                wbem_connection, inst,
                'NameFormat', ['IP', 'WWN', 'Other'])

        # Check that there is one associated CIM_System instance
        assert_number_of_instances_equal(
            wbem_connection, far_insts, far_insts_msg, 1)
