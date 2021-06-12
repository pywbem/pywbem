"""
    Define the classes and instances to mock a WEMServer as the basis for
    other test mocks
"""

from __future__ import print_function, absolute_import

import os

from .dmtf_mof_schema_def import DMTF_TEST_SCHEMA_VER, DMTFCIMSchema

# pylint: disable=wrong-import-position, wrong-import-order, invalid-name
from ...utils import import_installed
pywbem = import_installed('pywbem')
from pywbem import WBEMServer, ValueMapping, CIMInstance, CIMQualifier, \
    CIMInstanceName  # noqa: E402
pywbem_mock = import_installed('pywbem_mock')
from pywbem_mock import FakedWBEMConnection  # noqa: E402
from pywbem_mock import OBJECTMANAGERCREATIONCLASSNAME, \
    SYSTEMCREATIONCLASSNAME, OBJECTMANAGERNAME, \
    SYSTEMNAME  # noqa: E402
# pylint: enable=wrong-import-position, wrong-import-order, invalid-name


# Location of DMTF schema directory used by all tests.
# This directory is permanent and should not be removed.
TESTSUITE_SCHEMA_DIR = os.path.join('tests', 'schema')

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
#  namespace is defined in the WbemServerMock init method that overrides any
#  value in this dictionary
#
#  other_namespaces: Any other namespaces that the users wants to be defined
#  in the CIM repository
#
#  registered_profiles: The Organization, profile name, profile version for any
#  registered profiles
#
#  referenced_profiles: Definition of CIM_ReferencedProfile associations
#  between CIM_RegisteredProfiles. This is used to test get_central_instances
#
#
DEFAULT_WBEM_SERVER_MOCK_DICT = {
    'dmtf_schema': {'version': DMTF_TEST_SCHEMA_VER,
                    'dir': TESTSUITE_SCHEMA_DIR},
    'tst_schema': {
        'dir': os.path.join(TESTSUITE_SCHEMA_DIR, 'FakeWBEMServer'),
        'files': []},

    # if a url is defined it is set as the url of the mock wbem server
    'url': None,

    # Leaf classnames that will be installed in the WBEM server from the
    # dmtf_schema defined above.
    'class_names': ['CIM_Namespace',
                    'CIM_ObjectManager',
                    'CIM_RegisteredProfile',
                    'CIM_ElementConformsToProfile',
                    'CIM_ReferencedProfile',
                    'CIM_ComputerSystem'],
    'class-mof': ["class XXX_StorageComputerSystem : CIM_ComputerSystem{};", ],
    'system_name': SYSTEMNAME,
    'object_manager': {'Name': OBJECTMANAGERNAME,
                       'ElementName': 'Mock_Test',
                       'Description': 'Mock_Test CIM Server Version 2.15.0'
                                      ' Released', },
    'interop_namspace': 'interop',
    'other_namespaces': [],
    # mock providers that should be installed as part of startup
    # The common parameter is the namespace for the provider
    'providers': ["namespace_provider"],

    # Definition of registered profiles.  Each entry creates a registered
    # profile instance (i.e CIM_RegisteredProfile)
    'registered_profiles': [('DMTF', 'Indications', '1.1.0'),
                            ('DMTF', 'Profile Registration', '1.0.0'),
                            ('SNIA', 'Server', '1.2.0'),
                            ('SNIA', 'Server', '1.1.0'),
                            ('SNIA', 'SMI-S', '1.2.0'),
                            ('SNIA', 'Array', '1.4.0'),
                            ('SNIA', 'Software', '1.4.0'),
                            ('DMTF', 'Component', '1.4.0'), ],

    # Each entry creates an instance of
    'referenced_profiles': [
        (('SNIA', 'Server', '1.2.0'), ('DMTF', 'Indications', '1.1.0')),
        (('SNIA', 'Server', '1.2.0'), ('SNIA', 'Array', '1.4.0')),
        (('SNIA', 'Array', '1.4.0'), ('DMTF', 'Component', '1.4.0')),
        (('SNIA', 'Array', '1.4.0'), ('SNIA', 'Software', '1.4.0')),

    ],
    # define profile relation to central class instance
    # First element is a profile, second is name and keybindings of a
    # CIMInstanceName
    'element_conforms_to_profile': [
        (('SNIA', 'Server', '1.2.0'),
         ("XXX_StorageComputerSystem", {'Name': "10.1.2.3",
                                        'CreationClassName':
                                            "XXX_StorageComputerSystem"})), ],
    # List of CIMInstances. Each entry is a CIM instance with classname,
    # and properties. All properties required to build the path must be
    # defined. No other properties are required for this test.
    # TODO: We may expand this for more scoping tests.
    'central-instances': [
        CIMInstance(
            'XXX_StorageComputerSystem',
            properties={
                'Name': "10.1.2.3",
                'CreationClassName': "XXX_StorageComputerSystem",
                'NameFormat': "IP"}),
    ],
    'scoping-instances': []
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

    def __init__(self, interop_ns=None, server_mock_data=None, url=None):
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
        self.url = self.server_mock_data['url']
        if url:
            self.url = url
        self.object_manager_name = \
            self.server_mock_data['object_manager']['Name']

        # override dictionary interop namespace with init parameter
        if interop_ns:
            self.interop_ns = interop_ns
        else:
            self.interop_ns = self.server_mock_data['interop_ns']

        self.dmtf_schema_ver = self.server_mock_data['dmtf_schema']['version']
        self.schema_dir = self.server_mock_data['dmtf_schema']['dir']
        self.tst_schema_dir = self.server_mock_data['tst_schema']['dir']
        self.tst_schema_files = self.server_mock_data['tst_schema']['files']
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

    def build_class_repo(self, default_namespace, url=None):
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
        conn = FakedWBEMConnection(default_namespace=default_namespace, url=url)

        schema = DMTFCIMSchema(self.dmtf_schema_ver, self.schema_dir,
                               verbose=False)

        conn.compile_schema_classes(
            self.server_mock_data['class_names'],
            schema.schema_pragma_file,
            verbose=False)

        for fn in self.tst_schema_files:
            pg_file = os.path.join(self.tst_schema_dir, fn)
            conn.compile_mof_file(pg_file, namespace=default_namespace,
                                  search_paths=[self.tst_schema_dir],
                                  verbose=False)

        # compile the mof defined in the 'class-mof definitions
        for mof in self.server_mock_data['class-mof']:
            conn.compile_mof_string(mof, namespace=default_namespace,
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
                            IncludeQualifiers=True, IncludeClassOrigin=True,
                            PropertyList=property_list)

        return CIMInstance.from_class(
            cls, namespace=namespace, property_values=property_values,
            include_missing_properties=include_missing_properties,
            include_path=include_path)

    def build_obj_mgr_inst(self, conn, system_name, object_manager_name,
                           object_manager_element_name,
                           object_manager_description):
        """
        Build a CIMObjectManager instance for the mock wbem server using
        fixed data defined in this method and data from the init parameter
        mock data.
        """
        omdict = {"SystemCreationClassName": SYSTEMCREATIONCLASSNAME,
                  "CreationClassName": OBJECTMANAGERCREATIONCLASSNAME,
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

        assert len(rtn_rpinsts) == len(profiles), \
            "Expected registered profiles: %r, got %s" % (len(profiles),
                                                          len(rtn_rpinsts))

    def build_elementconformstoprofile_inst(self, conn, profile_path,
                                            element_path):
        """
        Build an instance of CIM_ElementConformsToProfile and insert into
        repository
        """
        class_name = 'CIM_ElementConformsToProfile'
        element_conforms_dict = {'ConformantStandard': profile_path,
                                 'ManagedElement': element_path}

        # TODO modify this when issue #1540  (resolve qualifiers)fixed
        # inst = self.inst_from_classname(conn, class_name,
        #                                namespace=self.interop_ns,
        #                                property_values=element_conforms_dict,
        #                                include_missing_properties=False,
        #                                include_path=True)
        cls = conn.GetClass(class_name, namespace=self.interop_ns,
                            LocalOnly=False, IncludeQualifiers=True,
                            IncludeClassOrigin=True)

        for pvalue in cls.properties.values():
            if pvalue.type == 'reference':
                if "key" not in pvalue.qualifiers:
                    pvalue.qualifiers['Key'] = \
                        CIMQualifier('Key', True, propagated=True)

        inst = CIMInstance.from_class(
            cls, namespace=self.interop_ns,
            property_values=element_conforms_dict,
            include_missing_properties=False,
            include_path=True)
        # TODO end of temp code

        conn.add_cimobjects(inst, namespace=self.interop_ns)

        assert conn.EnumerateInstances(class_name, namespace=self.interop_ns)
        assert conn.GetInstance(inst.path)

    def build_referenced_profile_insts(self, server, referenced_profiles):
        """
        Build and install in repository the referemced profile instances
        defined by the referemces parameter. A dictionary of tuples where each
        tuple contains Antecedent and Dependent reference in terms of the
        profile name as a tuple (org, name, version).

        Parameters:
          conn:
          profiles (dict of tuples where each tuple defines the antecedent
          and dependent)
        """
        class_name = 'CIM_ReferencedProfile'
        for profile_name in referenced_profiles:
            antecedent = profile_name[0]
            dependent = profile_name[1]
            antecedent_inst = server.get_selected_profiles(
                registered_org=antecedent[0],
                registered_name=antecedent[1],
                registered_version=antecedent[2])
            dependent_inst = server.get_selected_profiles(
                registered_org=dependent[0],
                registered_name=dependent[1],
                registered_version=dependent[2])

            assert len(antecedent_inst) == 1, \
                "Antecedent: {0}".format(antecedent)
            assert len(dependent_inst) == 1, \
                "Dependent: {0}".format(dependent)

            ref_profile_dict = {'Antecedent': antecedent_inst[0].path,
                                'Dependent': dependent_inst[0].path}

            # TODO replace the setting of key qualifier with the commented
            # code with #issue 1540 is fixed, i.e the key qualifier is
            # included in the class.
            # inst = self.inst_from_classname(server.conn, class_name,
            #                                namespace=self.interop_ns,
            #                                property_values=ref_profile_dict,
            #                                include_missing_properties=False,
            #                                include_path=True)

            cls = server.conn.GetClass(class_name, namespace=self.interop_ns,
                                       LocalOnly=False, IncludeQualifiers=True,
                                       IncludeClassOrigin=True,
                                       PropertyList=None)

            for pvalue in cls.properties.values():
                if pvalue.type == 'reference':
                    if "key" not in pvalue.qualifiers:
                        pvalue.qualifiers['Key'] = \
                            CIMQualifier('Key', True, propagated=True)

            inst = CIMInstance.from_class(
                cls, namespace=self.interop_ns,
                property_values=ref_profile_dict,
                include_missing_properties=False,
                include_path=True)
            # TODO end of code to drop for #1540 fix

            server.conn.add_cimobjects(inst, namespace=self.interop_ns)

            assert server.conn.EnumerateInstances(class_name,
                                                  namespace=self.interop_ns)
            assert server.conn.GetInstance(inst.path)

    def build_central_instances(self, conn, central_instances):
        """
        Build the central_instances from the definitions provided in the list
        central_instance where each definition is a python CIMInstance object
        and add them to the repositoryu. This method adds the path to each
        """
        for inst in central_instances:
            cls = conn.GetClass(inst.classname, namespace=self.interop_ns,
                                LocalOnly=False, IncludeQualifiers=True,
                                IncludeClassOrigin=True)
            inst.path = CIMInstanceName.from_instance(
                cls, inst, namespace=self.interop_ns, strict=True)

            conn.add_cimobjects(inst, namespace=self.interop_ns)

    def build_mock(self):
        """
            Builds the classes and instances for a mock WBEMServer from data
            in the init parameter. This calls the builder for:
              the object manager
              the namespaces
              the profiles
        """
        conn = self.build_class_repo(self.interop_ns, self.url)
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

        # build CIM_Namespace instances based on the init parameters
        namespaces = [self.interop_ns]
        if self.server_mock_data['other_namespaces']:
            namespaces.extend(self.server_mock_data['other_namespaces'])

        # Install providers from prenamed list. Need to add common
        # method to mocker to replace install_namespace_provider
        for provider in self.server_mock_data['providers']:
            if provider == "namespace_provider":
                conn.install_namespace_provider(self.interop_ns)
            elif provider == 'subscription_providers':
                conn.install_subscription_providers(self.interop_ns)

        self.build_reg_profile_insts(conn, self.registered_profiles)

        self.build_referenced_profile_insts(
            server, self.server_mock_data['referenced_profiles'])

        self.build_central_instances(
            conn, self.server_mock_data['central-instances'])

        # Element conforms for SNIA server to object manager
        prof_inst = server.get_selected_profiles(registered_org='SNIA',
                                                 registered_name='Server',
                                                 registered_version='1.1.0')
        # TODO this is simplistic form and only builds one instance of
        # conforms to.  Should expand but need better way to define instance
        # at other end.
        self.build_elementconformstoprofile_inst(conn,
                                                 prof_inst[0].path,
                                                 om_inst.path)
        for item in self.server_mock_data['element_conforms_to_profile']:
            profile_name = item[0]
            # TODO we are fixing the host name here.  Not good
            central_inst_path = CIMInstanceName(item[1][0],
                                                keybindings=item[1][1],
                                                host='FakedUrl',
                                                namespace=server.interop_ns)
            prof_insts = server.get_selected_profiles(
                registered_org=profile_name[0],
                registered_name=profile_name[1],
                registered_version=profile_name[2])
            assert len(prof_insts) == 1

            self.build_elementconformstoprofile_inst(conn,
                                                     prof_insts[0].path,
                                                     central_inst_path)
        return server
