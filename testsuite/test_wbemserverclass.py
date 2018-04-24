#
# (C) Copyright 2018 InovaDevelopment.com
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
#
# Author: Karl  Schopmeyer <inovadevelopment.com>
#

"""
Test for the WBEMServer class  in pywbem._server.py that uses the pywbem_mock
support package the methods of the class. Mock is required since, testing
WBEMServe requires access to a WBEMServer.
"""
from __future__ import absolute_import, print_function

import os
import pytest

from pywbem import WBEMServer, ValueMapping, CIMInstance, CIMInstanceName
from pywbem._nocasedict import NocaseDict

from pywbem_mock import FakedWBEMConnection

from dmtf_mof_schema_def import install_test_dmtf_schema

VERBOSE = True


class BaseMethodsForTests(object):
    """
    Common methods for test of server class.  This includes methods to
    build the DMTF schema and to build individual instances.
    """

    @staticmethod
    def build_schema_list(conn, namespace):
        """
        Build the schema qualifier and class objects in the repository.
        This requires only that the leaf objects be defined in a mof
        include file since the compiler finds the files for qualifiers
        and dependent classes.
        TODO: ks 3/18 Right now we must build a file in the schema directory
        to do this because the compile_from_string does not support
        include files, etc. It does not search for files. See issue 1138
        """
        dmtf_schema = install_test_dmtf_schema()
        class_list = """
            #pragma locale ("en_US")
            #pragma include ("Interop/CIM_RegisteredProfile.mof")
            #pragma include ("Interop/CIM_Namespace.mof")
            #pragma include ("Interop/CIM_ObjectManager.mof")
            #pragma include ("Interop/CIM_ElementConformsToProfile.mof")
            #pragma include ("Interop/CIM_ReferencedProfile.mof")
            """

        test_schema = os.path.join(dmtf_schema.schema_root_dir,
                                   'test_schema1.mof')

        with open(test_schema, "w") as schema_file:
            schema_file.write(class_list)

        conn.compile_mof_file(test_schema, namespace=namespace,
                              search_paths=[dmtf_schema.schema_mof_dir])

        if os.path.isfile(test_schema):
            os.remove(test_schema)
        return

    @staticmethod
    def inst_from_class(klass, namespace=None,
                        property_values=None,
                        include_null_properties=True,
                        include_path=True, strict=False,
                        include_class_origin=False):
        """
        Build a new CIMInstance from the input CIMClass using the
        property_values dictionary to complete properties and the other
        parameters to filter properties, validate the properties, and
        optionally set the path component of the CIMInstance.  If any of the
        properties in the class have default values, those values are passed
        to the instance unless overridden by the property_values dictionary.
        No CIMProperty qualifiers are included in the created instance and the
        `class_origin` attribute is transfered from the class only if the
        `include_class_origin` parameter is True

        Parameters:
          klass (:class:`pywbem:CIMClass`)
            CIMClass from which the instance will be constructed.  This
            class must include qualifiers and should include properties
            from any superclasses to be sure it includes all properties
            that are to be built into the instance. Properties may be
            excluded from the instance by not including them in the `klass`
            parameter.

          namespace (:term:`string`):
            Namespace in the WBEMConnection used to retrieve the class or
            `None` if the default_namespace is to be used.

          property_values (dictionary):
            Dictionary containing name/value pairs where the names are the
            names of properties in the class and the properties are the
            property values to be set into the instance. If a property is in
            the property_values dictionary but not in the class an ValueError
            exception is raised.

          include_null_properties (:class:`py:bool`):
            Determines if properties with Null values are included in the
            instance.

            If `True` they are included in the instance returned.

            If `False` they are not included in the instance returned

         inclued_class_origin  (:class:`py:bool`):
            Determines if ClassOrigin information is included in the returned
            instance.

            If None or False, class origin information is not included.

            If True, class origin information is included.

          include_path (:class:`py:bool`:):
            If `True` the CIMInstanceName path is build and inserted into
            the new instance.  If `strict` all key properties must be in the
            instance.

          strict (:class:`py:bool`:):
            If `True` and `include_path` is set, all key properties must be in
            the instance so that

            If not `True` The path component is created even if not all
            key properties are in the created instance.

        Returns:
            Returns an instance with the defined properties and optionally
            the path set.  No qualifiers are included in the returned instance
            and the existence of ClassOrigin depends on the
            `include_class_origin` parameter. The value of each property is
            either the value from the `property_values` dictionary, the
            default_value from the class or Null(unless
            `include_null_properties` is False). All other attributes of each
            property are the same as the corresponding class property.

        Raises:
           ValueError if there are conflicts between the class and
           property_values dictionary or strict is set and the class is not
           complete.
        """
        class_name = klass.classname
        inst = CIMInstance(class_name)
        for p in property_values:
            if p not in klass.properties:
                raise ValueError('Property Name %s in property_values but '
                                 'not in class %s' % (p, class_name))
        for cp in klass.properties:
            ip = klass.properties[cp].copy()
            ip.qualifiers = NocaseDict()
            if not include_class_origin:
                ip.class_origin = None
            if ip.name in property_values:
                ip.value = property_values[ip.name]
            if include_null_properties:
                inst[ip.name] = ip
            else:
                if ip.value:
                    inst[ip.name] = ip

        if include_path:
            inst.path = CIMInstanceName.from_instance(klass, inst, namespace,
                                                      strict=strict)
        return inst

    def inst_from_classname(self, conn, class_name, namespace=None,
                            property_list=None,
                            property_values=None,
                            include_null_properties=True,
                            strict=False, include_path=True):
        """
        Build instance from class using class_name property to get class
        from a repository.
        """
        cls = conn.GetClass(class_name, namespace=namespace, LocalOnly=False,
                            IncludeQualifiers=True, include_class_origin=True,
                            property_list=property_list)

        return self.inst_from_class(
            cls, namespace=namespace, property_values=property_values,
            include_null_properties=include_null_properties,
            strict=strict, include_path=include_path)


class TestServerClass(BaseMethodsForTests):
    """
    Conduct tests on the server class
    """
    def build_obj_mgr_inst(self, conn, namespace, system_name,
                           object_manager_name):
        """
        Build the Faked Class Repository and build the core instances for
        this test.
        """
        omdict = {"SystemCreationClassName": "CIM_ComputerSystem",
                  "CreationClassName": "CIM_ObjectManager",
                  "SystemName": system_name,
                  "Name": object_manager_name,
                  "ElementName": "Pegasus",
                  "Description": "Pegasus CIM Server Version 2.15.0 Released"}

        ominst = self.inst_from_classname(conn, "CIM_ObjectManager",
                                          namespace=namespace,
                                          property_values=omdict, strict=True,
                                          include_null_properties=False,
                                          include_path=True)

        conn.add_cimobjects(ominst, namespace=namespace)

        assert(len(conn.EnumerateInstances("CIM_ObjectManager",
                                           namespace=namespace)) == 1)
        return ominst

    def build_cimnamespace_insts(self, conn, namespace, system_name,
                                 object_manager_name, test_namespaces):
        """
        Build instances of CIM_Namespace defined by test_namespaces list
        """

        for ns in test_namespaces:
            nsdict = {"SystemName": system_name,
                      "ObjectManagerName": object_manager_name,
                      'Name': ns,
                      'CreationClassName': 'CIM_Namespace',
                      'ObjectManagerCreationClassName': 'CIM_ObjectManager',
                      'SystemCreationClassName': 'CIM_ComputerSystem'}

            ominst = self.inst_from_classname(conn, "CIM_Namespace",
                                              namespace=namespace,
                                              property_values=nsdict,
                                              strict=True,
                                              include_null_properties=False,
                                              include_path=True)
            conn.add_cimobjects(ominst, namespace=namespace)

        namespaces = conn.EnumerateInstances("CIM_Namespace",
                                             namespace=namespace)
        assert len(namespaces) == len(test_namespaces)

        # Build test CIM_RegisteredProfile instances
    def build_reg_profile_insts(self, conn, namespace, profiles):
        """
        Build and install in repository the registered profiles define by
        the profiles dictionary. The profiles to be build are defined by
        the profiles parameter, A dictionary of tuples where each tuple
        contains RegisteredOrganization, RegisteredName, RegisteredVersion
        """
        # Map ValueMap to Value
        org_vm = ValueMapping.for_property(conn, namespace,
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
                                              namespace=namespace,
                                              property_values=reg_prof_dict,
                                              strict=True,
                                              include_null_properties=False,
                                              include_path=True)

            conn.add_cimobjects(rpinst, namespace=namespace)

        assert(conn.EnumerateInstances("CIM_RegisteredProfile",
                                       namespace=namespace))

    def build_elementconformstoprofile_inst(self, conn, namespace,
                                            profile_inst, element_inst):
        """
        Build an instance of CIM_ElementConformsToProfile and insert into
        repository
        """
        class_name = 'CIM_ElementConformsToProfile'
        element_conforms_dict = {'ConformantStandard': profile_inst,
                                 'ManagedElement': element_inst}

        inst = self.inst_from_classname(conn, class_name,
                                        namespace=namespace,
                                        property_values=element_conforms_dict,
                                        strict=True,
                                        include_null_properties=False,
                                        include_path=True)
        conn.add_cimobjects(inst, namespace=namespace)

        assert conn.EnumerateInstances(class_name, namespace=namespace)
        assert conn.GetInstance(inst.path)

    @pytest.mark.parametrize(
        "tst_namespace",
        ['interop', 'root/interop', 'root/PG_Interop'])
    def test_server_basic(self, tst_namespace):
        """
        Test the basic functions that access server information. This test
        creates the mock repository and adds classes and instances for
        the WBEMServer tests that involve namespaces, brand, profiles and
        a subset of the central_instance tests.  It includes no tests for
        errors. The primary goal of this test was to develop the mechanisms
        for easily getting classes and instances into the repo and to provide
        a basic test of functionality.
        """
        conn = FakedWBEMConnection()
        self.build_schema_list(conn, tst_namespace)
        system_name = 'Mock_Test_server_class'
        object_manager_name = 'MyFakeObjectManager'
        server = WBEMServer(conn)

        # Build CIM_ObjectManager instance
        om_inst = self.build_obj_mgr_inst(conn, tst_namespace, system_name,
                                          object_manager_name)

        # build CIM_Namespace instances
        test_namespaces = [tst_namespace, 'root/cimv2']

        self.build_cimnamespace_insts(conn, tst_namespace, system_name,
                                      object_manager_name, test_namespaces)

        # Build RegisteredProfile instances
        profiles = [('DMTF', 'Indications', '1.1.0'),
                    ('DMTF', 'Profile Registration', '1.0.0'),
                    ('SNIA', 'Server', '1.2.0'),
                    ('SNIA', 'Server', '1.1.0'),
                    ('SNIA', 'SMI-S', '1.2.0')]

        self.build_reg_profile_insts(conn, tst_namespace, profiles)

        # Build instances for get_central instance
        # Using central methodology, i.e. ElementConformsToProfile

        # Element conforms for SNIA server to object manager
        prof_inst = server.get_selected_profiles(registered_org='SNIA',
                                                 registered_name='Server',
                                                 registered_version='1.1.0')

        self.build_elementconformstoprofile_inst(conn, tst_namespace,
                                                 prof_inst[0].path,
                                                 om_inst.path)

        # Test basic brand, version, namespace methods
        assert server.namespace_classname == 'CIM_Namespace'

        assert server.url == 'http://FakedUrl'

        assert server.brand == "OpenPegasus"
        assert server.version == "2.15.0"
        assert server.interop_ns == tst_namespace
        assert set(server.namespaces) == set([tst_namespace, 'root/cimv2'])

        # Test basic profiles methods
        org_vm = ValueMapping.for_property(server, server.interop_ns,
                                           'CIM_RegisteredProfile',
                                           'RegisteredOrganization')

        for inst in server.profiles:
            org = org_vm.tovalues(inst['RegisteredOrganization'])
            name = inst['RegisteredName']
            vers = inst['RegisteredVersion']

            tst_tup = (org, name, vers)
            pass_tst = False
            for tup in profiles:
                if tst_tup == tup:
                    pass_tst = True
                    break
            assert pass_tst

        sel_prof = server.get_selected_profiles(registered_org='DMTF',
                                                registered_name='Indications')
        assert len(sel_prof) == 1
        for inst in sel_prof:
            assert org_vm.tovalues(inst['RegisteredOrganization']) == 'DMTF'
            assert inst['RegisteredName'] == 'Indications'

        sel_prof = server.get_selected_profiles(registered_org='DMTF')
        assert len(sel_prof) == 2
        for inst in sel_prof:
            assert org_vm.tovalues(inst['RegisteredOrganization']) == 'DMTF'

        # Simple get_cental_instance.
        # profile_path, central_class=None,
        #                       scoping_class=None, scoping_path=None
        profile_insts = server.get_selected_profiles(registered_org='SNIA',
                                                     registered_name='Server',
                                                     registered_version='1.1.0')
        profile_path = profile_insts[0].path
        insts = server.get_central_instances(profile_path, 'CIM_ObjectManager')
        print('central inst %s' % insts[0])
        assert len(insts) == 1
        kb = NocaseDict([('SystemCreationClassName', 'CIM_ComputerSystem'),
                         ('SystemName', system_name),
                         ('CreationClassName', 'CIM_ObjectManager')])
        assert insts[0] == CIMInstanceName('CIM_ObjectManager', keybindings=kb,
                                           namespace=tst_namespace,
                                           host=conn.host)


# TODO Break up tests to do individual tests for each group of methds so we can
#      test for errors, variations on what is in the repowith each method.
#      Right now we build it all in a single test.  Thus, for example we
#      need to create a test group for find_central_instances since the
#      definition of the repo is different for each method of getting the
#      central instances Iex. If the server method exists, no other methods
#      are tried.
