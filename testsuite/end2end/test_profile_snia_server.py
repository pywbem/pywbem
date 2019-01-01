"""
End2end tests for SNIA 'Server' profile.
"""

from __future__ import absolute_import, print_function

# Note: The wbem_connection fixture uses the server_definition fixture, and
# due to the way py.test searches for fixtures, it also need to be imported.
from pytest_end2end import wbem_connection, server_definition  # noqa: F401, E501

from pytest_end2end import ProfileTest


class Test_SNIA_Server_Profile(ProfileTest):
    """
    All end2end tests for SNIA 'Server' profile.
    """

    def init_profile(self, conn):
        super(Test_SNIA_Server_Profile, self).init_profile(
            conn, 'SNIA', 'Server')

    def test_instances(self, wbem_connection):  # noqa: F811
        """
        Test the instances of the profile.
        """
        self.init_profile(wbem_connection)

        central_inst_paths = self.server.get_central_instances(
            self.profile_inst.path,
            central_class=self.profile_definition['central_class'],
            scoping_class=self.profile_definition['scoping_class'],
            scoping_path=self.profile_definition['scoping_path'],
            reference_direction=self.profile_definition['reference_direction'])

        # Check that there is one central instance
        assert len(central_inst_paths) == 1
        central_inst_path = central_inst_paths[0]

        # Test the CIM_ObjectManager central instance
        self.assert_instance_of(central_inst_path, 'CIM_ObjectManager')
        central_inst = self.conn.GetInstance(central_inst_path)
        self.assert_instance_of(central_inst, 'CIM_ObjectManager')
        self.assert_instance_consistency(central_inst, central_inst_path)
        mandatory_property_list = [
            'SystemCreationClassName', 'SystemName',
            'CreationClassName', 'Name',
            'ElementName', 'Description',
            'OperationalStatus', 'Started',
        ]
        self.assert_mandatory_properties(central_inst, mandatory_property_list)

        # Test the associated CIM_Namespace instances
        far_insts, _ = self.assert_association(
            source_path=central_inst_path,
            source_role='Antecedent',
            assoc_class='CIM_NamespaceInManager',
            far_role='Dependent',
            far_class='CIM_Namespace')
        mandatory_property_list = [
            'SystemCreationClassName', 'SystemName',
            'ObjectManagerCreationClassName', 'ObjectManagerName',
            'CreationClassName', 'Name',
            'ClassType',
        ]
        for inst in far_insts:
            self.assert_mandatory_properties(inst, mandatory_property_list)

        # Check that they are the namespaces determined by WBEMServer.
        # Because the Interop namespace is added if missing, we need to also
        # do that here.
        inst_names = [inst['Name'].lower() for inst in far_insts]
        if self.server.interop_ns.lower() not in inst_names:
            inst_names.append(self.server.interop_ns.lower())
        determined_names = [ns.lower() for ns in self.server.namespaces]
        assert set(inst_names) == set(determined_names)

        # Test the associated CIM_ObjectManagerCommunicationMechanism instances
        far_insts, _ = self.assert_association(
            source_path=central_inst_path,
            source_role='Antecedent',
            assoc_class='CIM_CommMechanismForManager',
            far_role='Dependent',
            far_class='CIM_ObjectManagerCommunicationMechanism')
        mandatory_property_list = [
            'SystemCreationClassName', 'SystemName',
            'CreationClassName', 'Name',
            'ElementName', 'CommunicationMechanism',
            'FunctionalProfilesSupported',
            'MultipleOperationsSupported',
            'AuthenticationMechanismsSupported',
        ]
        for inst in far_insts:
            self.assert_mandatory_properties(inst, mandatory_property_list)
            self.assert_property_one_of(
                inst, 'CommunicationMechanism', [2, 4])
            # TODO 2018-12 AM: The SNIA Server profile mandates that the
            #      FunctionalProfilesSupported property is 0 (Unknown), but it
            #      is an array property.
            # TODO 2018-12 AM: OP returns a set of functional profiles, which
            #      is in conflict with the profile. However, probably most
            #      WBEM servers will do so.
            # self.assert_property_contains(
            #     inst, 'FunctionalProfilesSupported', 0)
            self.assert_property_one_of(
                inst, 'MultipleOperationsSupported', [False])

        # Check that there is at least one associated CIM_ObjectManagerComm...
        assert len(far_insts) >= 1

        # Test the associated CIM_System instances
        far_insts, _ = self.assert_association(
            source_path=central_inst_path,
            source_role='Dependent',
            assoc_class='CIM_HostedService',
            far_role='Antecedent',
            far_class='CIM_System')
        mandatory_property_list = [
            'CreationClassName', 'Name',
            'NameFormat', 'Description', 'ElementName', 'OperationalStatus',
        ]
        for inst in far_insts:
            self.assert_mandatory_properties(inst, mandatory_property_list)
            self.assert_property_one_of(
                inst, 'NameFormat', ['IP', 'WWN', 'Other'])

        # Check that there is one associated CIM_System instance
        assert len(far_insts) == 1
        # system_inst = far_insts[0]
