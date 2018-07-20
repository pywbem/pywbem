"""
    Define the classes and instances to mock a WEMServer as the basis for
    other test mocks
"""
import os
from pywbem import WBEMServer, ValueMapping, CIMInstance
from pywbem_mock import FakedWBEMConnection
from dmtf_mof_schema_def import DMTF_TEST_SCHEMA_VER

# location of testsuite/schema dir used by all tests as test DMTF CIM Schema
# This directory is permanent and should not be removed.
TEST_DIR = os.path.dirname(__file__)
TESTSUITE_SCHEMA_DIR = os.path.join(TEST_DIR, 'schema')

# The following dictionary represents the data required to build a
# set of classes and instances for a mock WbemServer. This dictionary defines
# the following elements of a wbem server:
#
#  dmtf_schema: The DMTF schema version (ex (2, 49, 0) of the schema that
#  will be installed and the directory into which it will be installed
#
#  system_name: The name of the system (used by the CIM_ObjectManager)
#
#  object_manager: A dictionary that defines variable element for the
#  CIM_ObjectManager class.
#
#  interop_namespace: The interop namespace. Note that that if the interop
#  namespace is defined in the WbemServerMock constructor that overrides any
#  value in this dictionary
#
#  other_namespaces: Any other namespaces that the users wants to be defined
#  in the mock repository
#
#  registered_profiles: The Organization, profile name, profile version for any
#  registered profiles
#
DEFAULT_WBEM_SERVER_MOCK_DICT = {
    'dmtf_schema': {'version': DMTF_TEST_SCHEMA_VER,
                    'dir': TESTSUITE_SCHEMA_DIR},
    'pg_schema': {
        'dir': os.path.join(TESTSUITE_SCHEMA_DIR, 'OpenPegasus'),
        'files': ['PG_Namespace.mof']
    },
    'system_name': 'Mock_Test_WBEMServerTest',
    'object_manager': {'Name': 'MyFakeObjectManager',
                       'ElementName': 'Pegasus',
                       'Description': 'Pegasus CIM Server Version 2.15.0'
                                      ' Released', },
    'interop_namspace': 'interop',
    'other_namespaces': [],
    'registered_profiles': [('DMTF', 'Indications', '1.1.0'),
                            ('DMTF', 'Profile Registration', '1.0.0'),
                            ('SNIA', 'Server', '1.2.0'),
                            ('SNIA', 'Server', '1.1.0'),
                            ('SNIA', 'SMI-S', '1.2.0'), ],
    'element_conforms_to_profile': [['SNIA', 'Server', '1.1.0'], ]
}


class WbemServerMock(object):
    """
    Class that mocks the classes and methods used by the pywbem
    WBEMServer class so that the WBEMServer class will produce valid data
    for the server CIM_ObjectManager, CIM_Namespace, CIM_RegisteredProfile
    instances.

    This can be used to test the WbemServer class but is also required for
    other tests such as the Subscription manager since that class is based
    on getting data from the WbemServer class (ex. namespace)

    It allows building a the instance data for a particular server either
    from user defined input or from standard data predefined for pywbem
    tests
    """

    def __init__(self, interop_ns=None, server_mock_data=None):
        """
        Build the class repository for with the classes defined for
        the WBEMSERVER.  This is built either from a dictionary of data
        that represents the mock wbem server with the elements defined in
        DEFAULT_WBEM_SERVER_MOCK_DICT or if server_mock_data is None from
        the DEFAULT_WBEM_SERVER_MOCK_DICT dictionary.
        """
        if server_mock_data is None:
            self.server_mock_data = DEFAULT_WBEM_SERVER_MOCK_DICT
        else:
            self.server_mock_data = server_mock_data

        self.system_name = self.server_mock_data['system_name']
        self.object_manager_name = \
            self.server_mock_data['object_manager']['Name']

        # override dictionary interop namespace with constructor input
        if interop_ns:
            self.interop_ns = interop_ns
        else:
            self.interop_ns = self.server_mock_data['interop_ns']

        self.dmtf_schema_ver = self.server_mock_data['dmtf_schema']['version']
        self.schema_dir = self.server_mock_data['dmtf_schema']['dir']
        self.pg_schema_dir = self.server_mock_data['pg_schema']['dir']
        self.pg_schema_files = self.server_mock_data['pg_schema']['files']
        self.registered_profiles = self.server_mock_data['registered_profiles']
        self.wbem_server = self.build_mock()

    def __str__(self):
        ret_str = 'object_manager_name=%r, interop_ns=%r, system_name=%r, ' \
            'dmtf_schema_ver=%r, schema_dir=%r, wbem_server=%s' % \
            (self.object_manager_name, self.interop_ns, self.system_name,
             self.dmtf_schema_ver, self.schema_dir,
             getattr(self, 'wbem_server', None))
        return ret_str

    def __repr__(self):
        """
        Return a representation of the class object
        with all attributes, that is suitable for debugging.
        """
        ret_str = 'WBEMServerMock(object_manager_name=%r, interop_ns=%r, ' \
            'system_name=%r, dmtf_schema_ver=%r, schema_dir=%r, ' \
            'wbem_server=%r, registered_profiles=%r)' % \
            (self.object_manager_name, self.interop_ns, self.system_name,
             self.dmtf_schema_ver, self.schema_dir,
             getattr(self, 'wbem_server', None), self.registered_profiles)
        return ret_str

    def build_class_repo(self, default_namespace):
        """
        Build the schema qualifier and class objects in the repository
        from a DMTF schema.
        This requires only that the leaf objects be defined in a mof
        include file since the compiler finds the files for qualifiers
        and dependent classes.

        Returns:
            Instance of FakedWBEMConnection object.
        """
        # pylint: disable=protected-access

        FakedWBEMConnection._reset_logging_config()
        conn = FakedWBEMConnection(default_namespace=default_namespace)

        classnames = ['CIM_Namespace',
                      'CIM_ObjectManager',
                      'CIM_RegisteredProfile',
                      'CIM_ElementConformsToProfile']
        conn.compile_dmtf_schema(self.dmtf_schema_ver, self.schema_dir,
                                 class_names=classnames, verbose=False)

        for fn in self.pg_schema_files:
            pg_file = os.path.join(self.pg_schema_dir, fn)
            conn.compile_mof_file(pg_file, namespace=default_namespace,
                                  search_paths=[self.pg_schema_dir],
                                  verbose=False)

        return conn

    @staticmethod
    def inst_from_classname(conn, class_name, namespace=None,
                            property_list=None,
                            property_values=None,
                            include_missing_properties=True,
                            include_path=True):
        """
        Build instance from classname using class_name property to get class
        from a repository.
        """
        cls = conn.GetClass(class_name, namespace=namespace, LocalOnly=False,
                            IncludeQualifiers=True, include_class_origin=True,
                            property_list=property_list)

        return CIMInstance.from_class(
            cls, namespace=namespace, property_values=property_values,
            include_missing_properties=include_missing_properties,
            include_path=include_path)

    def build_obj_mgr_inst(self, conn, system_name, object_manager_name,
                           object_manager_element_name,
                           object_manager_description):
        """
        Build a CIMObjectManager instance for the mock wbem server using
        fixed data defined in this method and data from the constructor
        mock data.
        """
        omdict = {"SystemCreationClassName": "CIM_ComputerSystem",
                  "CreationClassName": "CIM_ObjectManager",
                  "SystemName": system_name,
                  "Name": object_manager_name,
                  "ElementName": object_manager_element_name,
                  "Description": object_manager_description}

        ominst = self.inst_from_classname(conn, "CIM_ObjectManager",
                                          namespace=self.interop_ns,
                                          property_values=omdict,
                                          include_missing_properties=False,
                                          include_path=True)

        conn.add_cimobjects(ominst, namespace=self.interop_ns)

        rtn_ominsts = conn.EnumerateInstances("CIM_ObjectManager",
                                              namespace=self.interop_ns)
        assert len(rtn_ominsts) == 1, \
            "Expected 1 ObjetManager instance, got %r" % rtn_ominsts

        return ominst

    def build_cimnamespace_insts(self, conn, namespaces=None):
        """
        Build instances of CIM_Namespace defined by test_namespaces list. These
        instances are built into the interop namespace
        """
        for ns in namespaces:
            nsdict = {"SystemName": self.system_name,
                      "ObjectManagerName": self.object_manager_name,
                      'Name': ns,
                      'CreationClassName': 'PG_Namespace',
                      'ObjectManagerCreationClassName': 'CIM_ObjectManager',
                      'SystemCreationClassName': 'CIM_ComputerSystem'}

            nsinst = self.inst_from_classname(conn, "PG_Namespace",
                                              namespace=self.interop_ns,
                                              property_values=nsdict,
                                              include_missing_properties=False,
                                              include_path=True)
            conn.add_cimobjects(nsinst, namespace=self.interop_ns)

        rtn_namespaces = conn.EnumerateInstances("CIM_Namespace",
                                                 namespace=self.interop_ns)
        assert len(rtn_namespaces) == len(namespaces), \
            "Expected namespaces: %r, got %s" % (namespaces, rtn_namespaces)

    def build_reg_profile_insts(self, conn, profiles):
        """
        Build and install in repository the registered profiles define by
        the profiles parameter. A dictionary of tuples where each tuple
        contains RegisteredOrganization, RegisteredName, RegisteredVersion

        Parameters:
          conn:
          profiles (dict of lists where each list contains org, name, version
             for a profiles)
        """
        # Map ValueMap to Value
        org_vm = ValueMapping.for_property(conn, self.interop_ns,
                                           'CIM_RegisteredProfile',
                                           'RegisteredOrganization')

        # This is a workaround hack to get ValueMap from Value
        org_vm_dict = {}   # reverse mapping dictionary (valueMap from Value)
        for value in range(0, 22):
            org_vm_dict[org_vm.tovalues(value)] = value

        for p in profiles:
            instance_id = '%s+%s+%s' % (p[0], p[1], p[2])
            reg_prof_dict = {'RegisteredOrganization': org_vm_dict[p[0]],
                             'RegisteredName': p[1],
                             'RegisteredVersion': p[2],
                             'InstanceID': instance_id}
            rpinst = self.inst_from_classname(conn, "CIM_RegisteredProfile",
                                              namespace=self.interop_ns,
                                              property_values=reg_prof_dict,
                                              include_missing_properties=False,
                                              include_path=True)

            conn.add_cimobjects(rpinst, namespace=self.interop_ns)

        rtn_rpinsts = conn.EnumerateInstances("CIM_RegisteredProfile",
                                              namespace=self.interop_ns)
        assert rtn_rpinsts, \
            "Expected 1 or more RegisteredProfile instances, got none"

    def build_elementconformstoprofile_inst(self, conn, profile_inst,
                                            element_inst):
        """
        Build an instance of CIM_ElementConformsToProfile and insert into
        repository
        """
        class_name = 'CIM_ElementConformsToProfile'
        element_conforms_dict = {'ConformantStandard': profile_inst,
                                 'ManagedElement': element_inst}

        inst = self.inst_from_classname(conn, class_name,
                                        namespace=self.interop_ns,
                                        property_values=element_conforms_dict,
                                        include_missing_properties=False,
                                        include_path=True)
        conn.add_cimobjects(inst, namespace=self.interop_ns)

        assert conn.EnumerateInstances(class_name, namespace=self.interop_ns)
        assert conn.GetInstance(inst.path)

    def build_mock(self):
        """
            Builds the classes and instances for a mock WBEMServer from data
            in the constructor. This calls the builder for:
              the object manager
              the namespaces
              the profiles
        """
        conn = self.build_class_repo(self.interop_ns)
        server = WBEMServer(conn)
        # NOTE: The wbemserver is not complete until the instances for at
        # least object manager and namespaces have been inserted. Any attempt
        # to display the instance object before that will fail because the
        # enumerate namespaces will be inconsistent

        # Build CIM_ObjectManager instance into the interop namespace since
        # this is required to build namespace instances
        om_inst = self.build_obj_mgr_inst(
            conn,
            self.system_name,
            self.object_manager_name,
            self.server_mock_data['object_manager']['ElementName'],
            self.server_mock_data['object_manager']['Description'])

        # build CIM_Namespace instances based on the constructor attributes
        namespaces = [self.interop_ns]
        if self.server_mock_data['other_namespaces']:
            namespaces.extend(self.server_mock_data['other_namespaces'])

        self.build_cimnamespace_insts(conn, namespaces)

        self.build_reg_profile_insts(conn, self.registered_profiles)

        # Element conforms for SNIA server to object manager
        prof_inst = server.get_selected_profiles(registered_org='SNIA',
                                                 registered_name='Server',
                                                 registered_version='1.1.0')

        self.build_elementconformstoprofile_inst(conn,
                                                 prof_inst[0].path,
                                                 om_inst.path)
        return server
