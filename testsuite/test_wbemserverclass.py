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

from pywbem_mock import FakedWBEMConnection
from dmtf_mof_schema_def import install_dmtf_schema, SCHEMA_MOF_DIR

TEST_SCHEMA = os.path.join(SCHEMA_MOF_DIR, 'test_schema1.mof')

VERBOSE = True


class BaseMethodsForTests(object):
    """
    Common methods for test of server class.  This includes methods to
    build the DMTF schema and to build individual instances.
    """

    def build_schema_list(self, conn, namespace):
        """
        Build the schema qualifier and class objects in the repository.
        This requires only that the leaf objects be defined in a mof
        include file since the compiler finds the files for qualifiers
        and dependent classes.
        TODO: ks 3/18 Right now we must build a file in the schema directory
        to do this because the compile_from_string does not support
        include files, etc. It does not search for files. See issue 1138
        """
        install_dmtf_schema()
        class_list = """
            #pragma locale ("en_US")
            #pragma include ("Interop/CIM_RegisteredProfile.mof")
            #pragma include ("Interop/CIM_Namespace.mof")
            #pragma include ("Interop/CIM_ObjectManager.mof")
            """
        # See issue 1138.
        # conn.compile_mof_str(class_list, namespace=namespace,
        #                      search_paths=SCHEMA_MOF_DIR)
        with open(TEST_SCHEMA, "w") as schema_file:
            schema_file.write(class_list)

        conn.compile_mof_file(TEST_SCHEMA, namespace=namespace,
                              search_paths=[SCHEMA_MOF_DIR])

        if os.path.isfile(TEST_SCHEMA):
            os.remove(TEST_SCHEMA)
        return

    def inst_from_class(self, klass, namespace=None, PropertyValues=None,
                        IncludeNullProperties=True,
                        IncludePath=True, strict=False,):
        """
        Build a new CIMInstance from the input CIMClass using the
        PropertyValues dictionary to complete properties and the other
        parameters to filter properties, validate the properties, and
        optionally set the path component of the CIMInstance.  If any of the
        properties in the class have default values, those values are passed
        to the instance unless overridden by the PropertyValues dictionary.

        Parameters:
          klass (:class:`pywbem:CIMClass`)
            CIMClass from which the instance will be constructed.  This
            class must include qualifiers and should include properties
            from any superclasses to be sure it includes all properties
            that are to be built into the instance. Properties may be
            excluded from the instance by not including them in the class.

          namespace (:term:`string`):
            Namespace in the WBEMConnection used to retrieve the class or
            `None` if the default_namespace is to be used.

          PropertyValues (dictionary):
            Dictionary containing nane/value pairs where the names are the
            names of properties in the class and the properties are the
            property values to be set into the instance. If a property is in
            the PropertyValues dictionary but not in the class an ValueError
            exception is raised.

          IncludeNullProperties (:class:`py:bool`:):
            Determines if properties with Null values are included in the
            instance.

            If `True` they are included in the instance returned.

            If `False` they are not included in the instance returned

          strict (:class:`py:bool`:):
            If `True` the property type in PropertyValue must exactly match
            the property type in the class. Also, if IncludePath is `True` the
            created instance is tested to assure that all key properties from
            the class are in the instance so a complete path can be buil

            If not `True` the value is inserted into the property whatever the
            type

          IncludePath (:class:`py:bool`:):
            If `True` the CIMInstanceName path is build and inserted into
            the new instance.  If `strict` all key properties must be in the
            instance.

        Returns:
            Returns an instance with the defined properties and optionally
            the path set.

        Raises:
           ValueError if there are conflicts between the class and
           PropertyValues dictionary or strict is set and the class is not
           complete.
        """
        class_name = klass.classname
        inst = CIMInstance(class_name)
        for p in PropertyValues:
            if p not in klass.properties:
                raise ValueError('Property Name %s in PropertyValues but '
                                 'not in class %s' % (p, class_name))
        for cp in klass.properties:
            ip = klass.properties[cp].copy()
            if ip.name in PropertyValues:
                ip.value = PropertyValues[ip.name]
            if strict:
                if ip.type != klass.properties[cp].type:
                    raise ValueError('Property "%s" Class type "%s" does not '
                                     'prop_value type "%s"' %
                                     (ip.name, klass.properties[cp].type,
                                      ip.type))
            if IncludeNullProperties:
                inst[ip.name] = ip
            else:
                if ip.value:
                    inst[ip.name] = ip

        if IncludePath:
            inst.path = CIMInstanceName.from_instance(klass, inst, namespace,
                                                      strict=strict)
        return inst

    def inst_from_classname(self, conn, class_name, namespace=None,
                            PropertyList=None,
                            PropertyValues=None, IncludeNullProperties=True,
                            strict=False, IncludePath=True):
        """
        Build instance from class using class_name property to get class
        from a repository.
        """
        cls = conn.GetClass(class_name, namespace=namespace, LocalOnly=False,
                            IncludeQualifiers=True, IncludeClassOrigin=True,
                            PropertyList=PropertyList)

        return self.inst_from_class(cls, namespace=namespace,
                                    PropertyValues=PropertyValues,
                                    IncludeNullProperties=IncludeNullProperties,
                                    strict=strict, IncludePath=IncludePath)


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
                                          PropertyValues=omdict, strict=True,
                                          IncludeNullProperties=False,
                                          IncludePath=True)

        conn.add_cimobjects(ominst, namespace=namespace)

        assert(len(conn.EnumerateInstances("CIM_ObjectManager",
                                           namespace=namespace)) == 1)

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
                                              PropertyValues=nsdict,
                                              strict=True,
                                              IncludeNullProperties=False,
                                              IncludePath=True)
            conn.add_cimobjects(ominst, namespace=namespace)

        namespaces = conn.EnumerateInstances("CIM_Namespace",
                                             namespace=namespace)
        assert len(namespaces) == len(test_namespaces)

        # Build test CIM_RegisteredProfile instances
    def build_reg_profile_insts(self, conn, namespace, profiles):
        """
        Build and install in repo the registered profiles define by
        the profiles dictionary
        """
        org_vm = ValueMapping.for_property(conn, namespace,
                                           'CIM_RegisteredProfile',
                                           'RegisteredOrganization')
        # Map ValueMap to Value
        org_vm_dict = {}
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
                                              PropertyValues=reg_prof_dict,
                                              strict=True,
                                              IncludeNullProperties=False,
                                              IncludePath=True)

            conn.add_cimobjects(rpinst, namespace=namespace)

        assert(conn.EnumerateInstances("CIM_RegisteredProfile",
                                       namespace=namespace))

    @pytest.mark.parametrize(
        "tst_namespace",
        ['interop', 'root/interop', 'root/PG_Interop'])
    def test_server_basic(self, tst_namespace):
        """
        Test the basic functions that access server information
        """
        conn = FakedWBEMConnection()
        self.build_schema_list(conn, tst_namespace)
        system_name = '"Mock Test_server_Class"'
        object_manager_name = "MyFakeObjectManager"

        self.build_obj_mgr_inst(conn, tst_namespace, system_name,
                                object_manager_name)

        test_namespaces = [tst_namespace, 'root/cimv2']

        self.build_cimnamespace_insts(conn, tst_namespace, system_name,
                                      object_manager_name, test_namespaces)

        profiles = [('DMTF', 'Indications', '1.1.0'),
                    ('DMTF', 'Profile Registration', '1.0.0'),
                    ('SNIA', 'Server', '1.2.0')]

        self.build_reg_profile_insts(conn, tst_namespace, profiles)

        server = WBEMServer(conn)

        assert server.namespace_classname == 'CIM_Namespace'

        assert server.url == 'http://FakedUrl'

        assert server.brand == "OpenPegasus"
        assert server.version == "2.15.0"
        assert server.interop_ns == tst_namespace
        assert set(server.namespaces) == set([tst_namespace, 'root/cimv2'])

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

# TODO Break up test to do individual tests for so we can test for errors
#      with each method.  Right now we build it all in a single test

# TODO add test for find
