# -*- coding: utf-8 -*-
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
Test of pywbem_mock package.  This tests the implementation of pywbem_mock
using a set of local mock qualifiers, classes, and instances.

"""
from __future__ import absolute_import, print_function

import os
from datetime import datetime
import operator
try:
    from collections import OrderedDict
except ImportError:
    from ordereddict import OrderedDict
import six
import pytest
from testfixtures import OutputCapture

from pywbem import CIMClass, CIMProperty, CIMInstance, CIMMethod, \
    CIMParameter, cimtype, Uint32, MOFParseError, \
    CIMInstanceName, CIMClassName, CIMQualifier, CIMQualifierDeclaration, \
    CIMError, DEFAULT_NAMESPACE, CIM_ERR_FAILED

from pywbem.cim_obj import NocaseDict

from pywbem.cim_operations import pull_path_result_tuple

from pywbem_mock import FakedWBEMConnection

from dmtf_mof_schema_def import TOTAL_QUALIFIERS, TOTAL_CLASSES, \
    install_dmtf_schema, SCHEMA_MOF_FN, SCHEMA_MOF_DIR, SCRIPT_DIR

VERBOSE = False


# Temporarily set this because all of the fixtures generate this warning
# for every use.  One alternative may be to prefix each fixture name with
# an underscore
# pylint: disable=redefined-outer-name


def model_path(inst_path):
    """
    Create just the model path for a CIMInstanceName. That is the CIMInstance
    Name with host and namespace removed.
    """
    model_path = inst_path.copy()
    model_path.host = None
    model_path.namespace = None
    return(model_path)


def equal_model_path(p1, p2):
    """
    Compare the model path component of CIMNamespaces for equality.

    Return True if equal, otherwise return False
    """
    if p1.keybindings == p2.keybindings \
            and p1.classname.lower() == p2.classname.lower():
        return True
    if p1.classname.lower() != p2.classname.lower():
        print('ModelPathCompare. classnames %s and %s not equal.' %
              (p1.classname, p2.classname))
    else:
        print('ModelPathCompare. keybinding difference:\np1:\n%s\np2\n%s' %
              (p1.keybindings, p2.keybindings))
    return False


def equal_ciminstnames(p1, p2):
    """Compare complete instance paths for equality including namespace and
       host
    """
    if not equal_model_path(p1, p2):
        return False
    if p1.namespace != p2.namespace:
        print('Match failure ns1=%s, ns2=%s' % (p1.namespace, p2.namespace))
        return False
    if p1.host != p2.host:
        print('Match failure nhost1=%s, host2=%s' % (p1.host, p2.host))
        return False
    return True


def equal_ciminstname_lists(l1, l2, model=False):
    """ Compare two lists of instance names for equality"""
    l1.sort(key=lambda x: x.classname)
    l2.sort(key=lambda x: x.classname)
    if len(l1) != len(l2):
        print('Lengths not equal %s vs %s' % (len(l1), len(l2)))
        return False
    for i, lx in enumerate(l1):
        if model:
            return equal_model_path(lx, l2[i])
        return equal_ciminstnames(lx, l2[i])


def insts_equal(inst1, inst2):
    """
    Compare the properties, qualifiers and model paths for equality
    """
    if equal_model_path(inst1.path, inst2.path) and \
            inst1.qualifiers == inst2.qualifiers and \
            inst1.properties == inst2.properties:
        return True
    if not inst1.properties == inst2.properties:
        if len(inst1.properties) != len(inst2.properties):
            print('Number of properties differ p1(%s)=%s, p2(%s)=%s' %
                  (len(inst1.properties), inst1.keys(),
                   len(inst2.properties), inst2.keys()))
        else:
            print('Inst mismatch properties\np1=%s\np2=%s' %
                  (inst1.properties, inst2.properties))
    elif inst1.qualifiers != inst2.qualifiers:
        print('Inst mismatch qualifiers\n%r\n%s' % (inst1.qualifiers,
                                                    inst2.qualifiers))
    else:
        print('MismatchInstances\n%r\n%r' % (inst1, inst2))
    return False


@pytest.fixture
def tst_class():
    """
    Builds and returns a single class: CIM_Foo that to be used as a
    test class for the mock class tests.
    """
    qkey = {'Key': CIMQualifier('Key', True, propagated=False)}
    dkey = {'Description': CIMQualifier('Description', 'blah blah',
                                        propagated=False)}

    c = CIMClass(
        'CIM_Foo', qualifiers=dkey,
        properties={'InstanceID':
                    CIMProperty('InstanceID', None, qualifiers=qkey,
                                type='string', class_origin='CIM_Foo',
                                propagated=False)},
        methods={'Delete': CIMMethod('Delete', 'uint32', qualifiers=dkey,
                                     class_origin='CIM_Foo',
                                     propagated=False),
                 'Fuzzy': CIMMethod('Fuzzy', 'string', qualifiers=dkey,
                                    class_origin='CIM_Foo',
                                    propagated=False)})
    return c


@pytest.fixture
def tst_classes(tst_class):
    """
    Builds and returns a list of 5 classes
        CIM_Foo - top level in hiearchy
        CIM_Foo_sub - Subclass to CIMFoo
        CIM_Foo_sub2 - Subclass to CIMFoo
        CIM_Foo_sub_sub - Subclass to CIMFoo_sub
        CIM_Foo_nokey - top level in hiearchy
    """
    qkey = {'Key': CIMQualifier('Key', True, propagated=False)}
    dkey = {'Description': CIMQualifier('Description', 'blah blah',
                                        propagated=False)}

    c2 = CIMClass(
        'CIM_Foo_sub', superclass='CIM_Foo', qualifiers=dkey,
        properties={'cimfoo_sub':
                    CIMProperty('cimfoo_sub', None, type='string',
                                class_origin='CIM_Foo_sub',
                                propagated=False)})

    c3 = CIMClass(
        'CIM_Foo_sub2', superclass='CIM_Foo', qualifiers=dkey,
        properties={'cimfoo_sub2':
                    CIMProperty('cimfoo_sub2', None, type='string',
                                class_origin='CIM_Foo_sub2',
                                propagated=False)})

    c4 = CIMClass(
        'CIM_Foo_sub_sub', superclass='CIM_Foo_sub', qualifiers=dkey,
        properties={'cimfoo_sub_sub':
                    CIMProperty('cimfoo_sub_sub', None, type='string',
                                class_origin='CIM_Foo_sub_sub',
                                propagated=False)})

    c5 = CIMClass(
        'CIM_Foo_nokey', qualifiers=dkey,
        properties=[
            CIMProperty('InstanceID', None, qualifiers=qkey,
                        type='string', class_origin='CIM_Foo_nokey',
                        propagated=False),
            CIMProperty('cimfoo', None, qualifiers=None,
                        type='string', class_origin='CIM_Foo_nokey',
                        propagated=False),
        ])

    return [tst_class, c2, c3, c4, c5]


def build_cimfoo_instance(id_):
    """
    Build a single instance of an instance of CIM_Foo where id is
    used to create the unique identity. The input parameter id_ is used
    to create the value for the key property InstanceID.
    """
    iname = 'CIM_Foo%s' % id_
    return CIMInstance('CIM_Foo',
                       properties={'InstanceID': iname},
                       path=CIMInstanceName('CIM_Foo', {'InstanceID': iname}))


def build_cimfoosub_instance(id_):
    """
    Build a single instance of an instance of CIM_Foo where id is
    used to create the unique identity.
    """
    inst_id = 'CIM_Foo_sub%s' % id_
    inst = CIMInstance('CIM_Foo_sub',
                       properties={
                           'InstanceID': inst_id,
                           'cimfoo_sub': 'cimfoo_sub prop  for %s' % inst_id},
                       path=CIMInstanceName('CIM_Foo_sub',
                                            {'InstanceID': inst_id}))
    return inst


def build_cimfoosub2_instance(id_):
    """
    Build a single instance of an instance of CIM_Foo_sub2 where id is
    used to create the unique identity.
    """
    inst_id = 'CIM_Foo_sub2%s' % id_
    inst = CIMInstance('CIM_Foo_sub2',
                       properties={
                           'InstanceID': inst_id,
                           'cimfoo_sub2': 'cimfoo_sub2 prop for %s' % inst_id},
                       path=CIMInstanceName('CIM_Foo_sub2',
                                            {'InstanceID': inst_id}))
    return inst


def build_cimfoosub_sub_instance(id_):
    """
    Build a single instance of an instance of CIM_Foo_sub2 where id is
    used to create the unique identity.
    """
    inst_id = 'CIM_Foo_sub_sub%s' % id_
    inst = CIMInstance('CIM_Foo_sub_sub',
                       properties={
                           'InstanceID': inst_id,
                           'cimfoo_sub': 'cimfoo_sub prop:  %s' % inst_id,
                           'cimfoo_sub_sub': 'cimfoo_sub_sub: %s' % inst_id},
                       path=CIMInstanceName('CIM_Foo_sub_sub',
                                            {'InstanceID': inst_id}))
    return inst


def build_cimfoo_nokey_instance():
    """
    Build a single instance of an instance of CIM_Foo_nokey.
    """
    return CIMInstance('CIM_Foo_nokey',
                       properties={'cimfoo': 'none'},
                       path=CIMInstanceName('CIM_Foo_nokey'))


@pytest.fixture
def tst_instances():
    """
    Build instances of CIM_foo and 2 instances of CIM_Foo_sub and
    return them
    """
    rtn = []

    for i in six.moves.range(1, 3):
        rtn.append(build_cimfoo_instance(i))
    for i in six.moves.range(4, 6):
        rtn.append(build_cimfoosub_instance(i))
    for i in six.moves.range(7, 9):
        rtn.append(build_cimfoosub2_instance(i))
    for i in six.moves.range(10, 12):
        rtn.append(build_cimfoosub_sub_instance(i))
    rtn.append(build_cimfoo_nokey_instance())
    return rtn


@pytest.fixture
def tst_insts_big():
    """
    Create Instances of cimfoo for the ide 3 to what is in list_size.  This
    does not include instances that were created in the tst_instances
    fixture.
    """
    list_size = 100
    big_list = []

    for i in six.moves.range(3, list_size + 1):
        big_list.append(build_cimfoo_instance(i))
    return big_list


@pytest.fixture
def tst_qualifiers_mof():
    """
    Mof string defining qualifier declarations for tests.
    """
    return """
        Qualifier Association : boolean = false,
            Scope(association),
            Flavor(DisableOverride, ToSubclass);

        Qualifier Indication : boolean = false,
            Scope(class, indication),
            Flavor(DisableOverride, ToSubclass);

        Qualifier Abstract : boolean = false,
            Scope(class, association, indication),
            Flavor(EnableOverride, Restricted);

        Qualifier Aggregate : boolean = false,
            Scope(reference),
            Flavor(DisableOverride, ToSubclass);

        Qualifier Description : string = null,
            Scope(any),
            Flavor(EnableOverride, ToSubclass, Translatable);

        Qualifier In : boolean = true,
            Scope(parameter),
            Flavor(DisableOverride, ToSubclass);

        Qualifier Key : boolean = false,
            Scope(property, reference),
            Flavor(DisableOverride, ToSubclass);

        Qualifier Out : boolean = false,
            Scope(parameter),
            Flavor(DisableOverride, ToSubclass);

        Qualifier Override : string = null,
            Scope(property, reference, method),
            Flavor(EnableOverride, Restricted);
        """


@pytest.fixture
def tst_classes_mof(tst_qualifiers_mof):
    """
    Test classes to be compiled as part of tests. This is the same
    classes as the tst_classes fixture. This merges the tst_compile_qualifiers
    str and the classes string into a single string and returns it.
    """

    cl_str = """
             [Description ("blah blah")]
        class CIM_Foo {
                [Key, Description ("This is key prop")]
            string InstanceID;

                [Description ("This is a method with in and out parameters")]
            uint32 Fuzzy(
                [IN, Description("FuzzyMethod Param")]
              string FuzzyParameter,

                [IN, OUT, Description ( "Test of ref in/out parameter")]
              CIM_Foo REF Foo,

                [IN ( false ), OUT, Description("TestMethod Param")]
              string OutputParam);

                [ Description("Method with no Parameters") ]
            uint32 DeleteNothing();
        };

            [Description ("Subclass of CIM_Foo")]
        class CIM_Foo_sub : CIM_Foo {
            string cimfoo_sub;
        };

        class CIM_Foo_sub2 : CIM_Foo {
            string cimfoo_sub2;
        };

        class CIM_Foo_sub_sub : CIM_Foo_sub {
            string cimfoo_sub_sub;
                [Description("Sample method with input and output parameters")]
            uint32 Method1(
                [IN, Description("Input Param1")]
              string InputParam1,
                [IN, Description("Input Param2")]
              string InputParam2,
                [IN ( false), OUT, Description("Response param 1")]
              string OutputParam1,
                [IN ( false), OUT, Description("Response param 2")]
              string OutputParam2);
            uint32 Method2(
                [IN, Description("Input Param1")]
              Uint32 InputParam1,
                [IN, Description("Input Param2")]
              string InputParam2,
                [IN, Description("Generate Exception if this exists")]
              string TestCIMErrorException,
                [IN ( false), OUT, Description("Response param 1")]
              string OutputParam1,
                [IN ( false), OUT, Description("Response param 2")]
              Uint64 OutputParam2[]);

        };

             [Description ("blah blah")]
        class CIM_Foo_nokey {
                [Key, Description ("This is key prop")]
            string InstanceID;

            string cimfoo;
        };
    """
    return tst_qualifiers_mof + '\n\n' + cl_str + '\n\n'


@pytest.fixture
def tst_instances_mof(tst_classes_mof):
    """
    Adds the same instances as defined in tst_instances to
    test_classes_mof
    """
    inst_str = """
        instance of CIM_Foo as $foo1 { InstanceID = "CIM_Foo1"; };
        instance of CIM_Foo as $foo2 { InstanceID = "CIM_Foo2"; };
        instance of CIM_Foo_sub as $foosub4 { InstanceID = "CIM_Foo_sub4";
                                              cimfoo_sub = "data sub 4";};
        instance of CIM_Foo_sub as $foosub5 { InstanceID = "CIM_Foo_sub5";
                                              cimfoo_sub = "data sub5";};
        instance of CIM_Foo_sub2 as $foosub21 { InstanceID = "CIM_Foo_sub21";
                                                cimfoo_sub2 = "data sub 21";};
        instance of CIM_Foo_sub2 as $foosub22 { InstanceID = "CIM_Foo_sub22";
                                                cimfoo_sub2 = "data sub22";};

        instance of CIM_Foo_sub_sub as $foosub21 {
            InstanceID = "CIM_Foo_sub_sub21";
            cimfoo_sub = "data sub 10";
            cimfoo_sub_sub = "data sub 21";};
        instance of CIM_Foo_sub_sub as $foosub22 {
            InstanceID = "CIM_Foo_sub_sub22";
            cimfoo_sub = "data sub 11";
            cimfoo_sub_sub = "data sub_sub22";};

        instance of CIM_Foo_nokey as $foonokey { cimfoo = "none"; };
    """
    return tst_classes_mof + '\n\n' + inst_str + '\n\n'


@pytest.fixture
def tst_person_instance_names():
    """Defines the instance names for the instances in tst_assoc_mof below"""
    return ['Mike', 'Saara', 'Sofi', 'Gabi']


@pytest.fixture
def tst_assoc_mof():
    """
    Complete mof definition of a simple set of classes and association class
    to test associations and references. Includes qualifiers, classes,
    and instances.
    """
    return """
        Qualifier Association : boolean = false,
            Scope(association),
            Flavor(DisableOverride, ToSubclass);

        Qualifier Description : string = null,
            Scope(any),
            Flavor(EnableOverride, ToSubclass, Translatable);

        Qualifier In : boolean = true,
            Scope(parameter),
            Flavor(DisableOverride, ToSubclass);

        Qualifier Key : boolean = false,
            Scope(property, reference),
            Flavor(DisableOverride, ToSubclass);

        Qualifier Out : boolean = false,
            Scope(parameter),
            Flavor(DisableOverride, ToSubclass);

        class TST_Person{
                [Key, Description ("This is key prop")]
            string name;
            string extraProperty = "defaultvalue";
        };

        class TST_Personsub : TST_Person{
            string secondProperty = "empty";
            uint32 counter;
        };

        [Association, Description(" Lineage defines the relationship "
            "between parents and children.") ]
        class TST_Lineage {
            [key] string InstanceID;
            TST_Person ref parent;
            TST_Person ref child;
        };

        [Association, Description(" Family gathers person to family.") ]
        class TST_MemberOfFamilyCollection {
           [key] TST_Person ref family;
           [key] TST_Person ref member;
        };

        [ Description("Collection of Persons into a Family") ]
        class TST_FamilyCollection {
                [Key, Description ("This is key prop and family name")]
            string name;
        };

        instance of TST_Person as $Mike { name = "Mike"; };
        instance of TST_Person as $Saara { name = "Saara"; };
        instance of TST_Person as $Sofi { name = "Sofi"; };
        instance of TST_Person as $Gabi{ name = "Gabi"; };

        instance of TST_PersonSub as $Mikesub{ name = "Mikesub";
                                    secondProperty = "one" ;
                                    counter = 1; };

        instance of TST_PersonSub as $Saarasub { name = "Saarasub";
                                    secondProperty = "two" ;
                                    counter = 2; };

        instance of TST_PersonSub as $Sofisub{ name = "Sofisub";
                                    secondProperty = "three" ;
                                    counter = 3; };

        instance of TST_PersonSub as $Gabisub{ name = "Gabisub";
                                    secondProperty = "four" ;
                                    counter = 4; };

        instance of TST_Lineage as $MikeSofi
        {
            InstanceID = "MikeSofi";
            parent = $Mike;
            child = $Sofi;
        };

        instance of TST_Lineage as $MikeGabi
        {
            InstanceID = "MikeGabi";
            parent = $Mike;
            child = $Gabi;
        };

        instance of TST_Lineage  as $SaaraSofi
        {
            InstanceID = "SaaraSofi";
            parent = $Saara;
            child = $Sofi;
        };

        instance of TST_FamilyCollection as $Family1
        {
            name = "family1";
        };

        instance of TST_FamilyCollection as $Family2
        {
            name = "Family2";
        };


        instance of TST_MemberOfFamilyCollection as $SofiMember
        {
            family = $Family1;
            member = $Sofi;
        };

        instance of TST_MemberOfFamilyCollection as $GabiMember
        {
            family = $Family1;
            member = $Gabi;
        };

        instance of TST_MemberOfFamilyCollection as $MikeMember
        {
            family = $Family2;
            member = $Mike;
        };
    """


@pytest.fixture
def conn():
    """
    Create the FakedWBEMConnection and return it
    """
    FakedWBEMConnection._reset_logging_config()
    return FakedWBEMConnection()


@pytest.fixture
def conn_lite():
    """
    Create the FakedWBEMConnection with the repo_lite flag set and return it.
    """
    FakedWBEMConnection._reset_logging_config()
    return FakedWBEMConnection(repo_lite=True)


#########################################################################
#
#            Pytest Test Classes
#
#########################################################################


class TestFakedWBEMConnection(object):
    """
    Test the basic characteristics of the FakedWBEMConnection including
    constructor parameters,
    """
    @pytest.mark.parametrize(
        "set_on_init", [False, True])
    @pytest.mark.parametrize(
        "delay", [.5, 1])
    def test_response_delay(self, tst_class, set_on_init, delay):
        # pylint: disable=no-self-use
        """
        Test the response delay attribute set both in constructor and with
        property
        """
        FakedWBEMConnection._reset_logging_config()
        if set_on_init:
            conn = FakedWBEMConnection(response_delay=delay)
        else:
            conn = FakedWBEMConnection()
            conn.response_delay = delay

        assert conn.response_delay == delay
        conn.add_cimobjects(tst_class)

        start_time = datetime.now()
        conn.GetClass('CIM_Foo')
        diff = datetime.now() - start_time
        # Had to do this because python 2.6 does not support total_seconds())
        exec_time = float(diff.seconds) + (float(diff.microseconds) / 1000000)

        if delay:
            assert exec_time > delay * .8 and exec_time < delay * 1.3
        else:
            assert exec_time < 0.1

    def test_repr(self):
        # pylint: disable=no-self-use
        """ Test output of repr"""
        FakedWBEMConnection._reset_logging_config()
        conn = FakedWBEMConnection(response_delay=3)
        repr_ = '%r' % conn
        assert repr_.startswith('FakedWBEMConnection(response_delay=3,')

    def test_attr(self):
        # pylint: disable=no-self-use
        """
        Test other FadedWBEMConnection attributes
        """
        FakedWBEMConnection._reset_logging_config()
        conn = FakedWBEMConnection()
        assert conn.host == 'FakedUrl'
        assert conn.use_pull_operations is False
        assert conn._repo_lite is False  # pylint: disable=protected-access
        assert conn.stats_enabled is False
        assert conn.default_namespace == DEFAULT_NAMESPACE
        assert conn.operation_recorder_enabled is False


result1 = (
    u"mock_imethodcall method=GetClass, namespace=root/cimv2, "
    u"response_params_rqd=None, params={'IncludeClassOrigin': None,"
    u" 'ClassName': CIMClassName(classname=u'CIM_Foo', "
    u"namespace=None, host=None), 'IncludeQualifiers': False,"
    u" 'PropertyList': None, 'LocalOnly': None}",

    u"mock result [('IRETURNVALUE', {}, [CIMClass(classname"
    u"u'CIM_Foo', superclass=None, properties=NocaseDict(["
    u"('InstanceID', CIMProperty(name=u'InstanceID', value=None,"
    u" type=u'string', reference_class=None, embedded_object=None,"
    u" is_array=False, array_size=None, class_origin=None, "
    u"propagated=None, qualifiers=NocaseDict([])))]), "
    u"methods=NocaseDict([('Fuzzy', CIMMethod(name=u'Fuzzy',"
    u" return_type=u'string', class_origin=None, propagated=False,"
    u" parameters=NocaseDict([]), qualifiers=NocaseDict([]))), "
    u"('Delete', CIMMethod(name=u'Delete', return_type=u'uint32',"
    u" class_origin=None, propagated=False, parameters="
    u"NocaseDict([]), qualifiers=NocaseDict([])))]), "
    u"qualifiers=NocaseDict([]), path=CIMClassName(classname",
    u"=u'CIM_Foo', namespace=u'root/cimv2', host=u'FakedUrl'))])]")

result2 = (
    u"mock_imethodcall method=GetClass, namespace=root/cimv2, "
    u"response_params_rqd=None, params={'IncludeClassOrigin': None,"
    u" 'ClassName': CIMClassName(classname=u'CIM_Foo', "
    u"namespace=None, host=None), 'IncludeQualifiers': False,"
    u" 'PropertyList': None, 'LocalOnly': None}",

    u"mock result [('IRETURNVALUE', {}, [CIMClass(classname"
    u"u'CIM_Foo', superclass=None, properties=NocaseDict(["
    u"('InstanceID', CIMProperty(name=u'InstanceID', value=None,"
    u" type=u'string', reference_class=None, embedded_object=None,"
    u" is_array=False, array_size=None, class_origin=None, "
    u"propagated=None, qualifiers=NocaseDict([])))]), "
    u"methods=NocaseDict([('Fuzzy', CIMMethod(name=u'Fuzzy',"
    u" return_type=u'string', class_origin=None, propagated=False,"
    u" parameters=NocaseDict([]), qualifiers=NocaseDict([]))), "
    u"('Delete', CIMMethod(name=u'Delete', return_type=u'uint32',"
    u" class_origin=None, propagated=False, parameters="
    u"NocaseDict([]), qualifiers=NocaseDict([])))]), "
    u"qualifiers=NocaseDict([]), path=CIMClassName(classname",
    u"=u'CIM_Foo', namespace=u'root/cimv2', host=u'FakedUrl'))])]")


class TestRepoMethods(object):
    """
    Test the repository support methods.
    """

    @pytest.mark.parametrize(
        "ns", [DEFAULT_NAMESPACE, 'root/blah'])
    @pytest.mark.parametrize(
        "mof", [False, True])
    @pytest.mark.parametrize(
        "cln, exp_rtn", [
            ['CIM_Foo', True],
            ['CIM_FooX', False],
        ]
    )
    def test_class_exists(self, conn, tst_classes, tst_classes_mof, ns, mof,
                          cln, exp_rtn):
        # pylint: disable=no-self-use
        """ Test the class exists method"""
        if mof:
            conn.compile_mof_string(tst_classes_mof, namespace=ns)
        else:
            conn.add_cimobjects(tst_classes, namespace=ns)
        # pylint: disable=protected-access
        assert conn._class_exists(cln, ns) == exp_rtn

    @pytest.mark.parametrize(
        "ns", [DEFAULT_NAMESPACE, 'root/blah'])
    @pytest.mark.parametrize(
        "mof", [False, True])
    @pytest.mark.parametrize(
        "cln, di, exp_clns", [
            [None, True, ['CIM_Foo', 'CIM_Foo_sub', 'CIM_Foo_sub2',
                          'CIM_Foo_sub_sub', 'CIM_Foo_nokey']],
            [None, False, ['CIM_Foo', 'CIM_Foo_nokey']],
            ['CIM_Foo', True, ['CIM_Foo_sub', 'CIM_Foo_sub2',
                               'CIM_Foo_sub_sub']],
            ['CIM_Foo', False, ['CIM_Foo_sub', 'CIM_Foo_sub2']],
            ['CIM_Foo_sub', True, ['CIM_Foo_sub_sub']],
            ['CIM_Foo_sub', False, ['CIM_Foo_sub_sub']],
        ]
    )
    def test_get_subclassnames(self, conn, tst_classes, tst_classes_mof, ns,
                               cln, mof, di, exp_clns):
        # pylint: disable=no-self-use
        """
        Test the _internal _get_subclasses method. Tests against both
        add_cimobjects and compiled objects
        """
        if mof:
            conn.compile_mof_string(tst_classes_mof, namespace=ns)
        else:
            conn.add_cimobjects(tst_classes, namespace=ns)
        # pylint: disable=protected-access
        assert set(conn._get_subclass_names(cln, ns, di)) == set(exp_clns)

    @pytest.mark.parametrize(
        "ns", [DEFAULT_NAMESPACE, 'root/blah'])
    @pytest.mark.parametrize(
        "mof", [False, True])
    @pytest.mark.parametrize(
        "cln, exp_cln", [
            ['CIM_Foo', []],
            ['CIM_Foo_sub', ['CIM_Foo']],
            ['CIM_Foo_sub_sub', ['CIM_Foo', 'CIM_Foo_sub']],
        ]
    )
    def test_get_superclassnames(self, conn, tst_classes, tst_classes_mof,
                                 ns, mof, cln, exp_cln):
        # pylint: disable=no-self-use
        """
            Test the _get_superclassnames method
        """
        if mof:
            conn.compile_mof_string(tst_classes_mof, namespace=ns)
        else:
            conn.add_cimobjects(tst_classes, namespace=ns)

        # pylint: disable=protected-access
        clns = conn._get_superclassnames(cln, ns)
        assert clns == exp_cln

    @pytest.mark.parametrize(
        "ns", [DEFAULT_NAMESPACE, 'root/blah'])
    @pytest.mark.parametrize(
        "mof", [False, True])
    @pytest.mark.parametrize(
        "cln, lo, iq, ico, pl, exp_prop", [
            # classname     lo     iq    ico   pl     exp_prop
            ['CIM_Foo_sub', False, True, True, None, ['InstanceID',
                                                      'cimfoo_sub']],
            ['CIM_Foo_sub', False, False, True, None, ['InstanceID',
                                                       'cimfoo_sub']],
            ['CIM_Foo_sub', False, True, False, None, ['InstanceID',
                                                       'cimfoo_sub']],
            ['CIM_Foo_sub', False, True, True, ['cimfoo_sub'], ['cimfoo_sub']],
            ['CIM_Foo_sub', False, True, True, ['InstanceID'], ['InstanceID']],
            ['CIM_Foo_sub', False, True, True, [''], []],
            ['CIM_Foo_sub', True, True, True, None, ['cimfoo_sub']],
            ['CIM_Foo_sub', True, False, True, None, ['cimfoo_sub']],
            ['CIM_Foo_sub', True, True, False, None, ['cimfoo_sub']],
            ['CIM_Foo_sub', True, True, False, ['InstanceID'], []],
            ['CIM_Foo_sub', True, True, False, ['cimfoo_sub'], ['cimfoo_sub']],
        ]
    )
    def test_get_class(self, conn, tst_classes, tst_classes_mof, ns, mof, cln,
                       lo, iq, ico, pl, exp_prop):
        # pylint: disable=no-self-use
        """
        Test variations on the _get_class method that gets a class
        from the repository, creates a copy  and filters it.
        """
        if mof:
            conn.compile_mof_string(tst_classes_mof, namespace=ns)
        else:
            conn.add_cimobjects(tst_classes, namespace=ns)

        # _get_class gets a copy of the class filtered by the parameters
        # pylint: disable=protected-access
        cl = conn._get_class(cln, ns, local_only=lo, include_qualifiers=iq,
                             include_classorigin=ico, property_list=pl)

        cl_props = [p.name for p in six.itervalues(cl.properties)]

        class_repo = conn._get_class_repo(ns)
        tst_class = class_repo[cln]

        if ico:
            for prop in six.itervalues(cl.properties):
                assert prop.class_origin
            for method in six.itervalues(cl.methods):
                assert method.class_origin
        else:
            for prop in six.itervalues(cl.properties):
                assert not prop.class_origin
            for method in six.itervalues(cl.methods):
                assert not method.class_origin

        if not iq:
            assert not cl.qualifiers
            for prop in six.itervalues(cl.properties):
                assert not prop.qualifiers
            for method in six.itervalues(cl.methods):
                for param in six.itervalues(method.parameters):
                    assert not param.qualifiers
        else:
            assert cl.qualifiers == tst_class.qualifiers

        if pl:
            # special test for empty property list
            if len(pl) == 1 and pl[0] == '':
                assert not cl_props
            else:
                # Cover case where pl is for property not in class
                tst_lst = [p for p in pl if p in cl_props]
                if tst_lst != pl:
                    assert set(cl_props) == set(tst_lst)
                else:
                    assert set(cl_props) == set(pl)
        else:
            assert set(cl_props) == set(exp_prop)

    @pytest.mark.parametrize(
        "ns", [DEFAULT_NAMESPACE, 'root/blah'])
    @pytest.mark.parametrize(
        "mof", [False, True])
    @pytest.mark.parametrize(
        "cln, key, iq, ico, pl, exp_props, exp_err",
        [
            #  cln         key      iq     ico   pl      exp_props   exp_err
            ['CIM_Foo', 'CIM_Foo1', None, None, None, ['InstanceID'], None],
            ['CIM_Foo', 'CIM_Foo1', None, None, ['InstanceID'], ['InstanceID'],
             None],
            ['CIM_Foo', 'CIM_Foo1', None, None, ['Instx'], [], None],
            ['CIM_Foo', 'CIM_Foo1', True, None, None, ['InstanceID'], None],
            ['CIM_Foo', 'CIM_Foo1', None, True, None, ['InstanceID'], None],
            ['CIM_Foo', 'CIM_Foo1', None, None, "", [], None],
            ['CIM_Foo', 'CIM_Foo2', None, None, None, ['InstanceID'], None],
            ['CIM_Foo_sub', 'CIM_Foo_sub4', None, None, None, ['InstanceID',
                                                               'cimfoo_sub'],
             None],

            ['CIM_Foo_sub', 'CIM_Foo_sub99', None, None, None, None,
             'CIM_ERR_NOT_FOUND'],
        ]
    )
    def test_get_instance(self, conn, tst_classes, tst_instances,
                          tst_instances_mof, ns, mof, cln, key, iq, ico, pl,
                          exp_props, exp_err):
        # pylint: disable=no-self-use
        """
        Test the internal _get_instance method.  Test for getting correct and
        error responses for both compiled and added objects including parameters
        of propertylist, include qualifiers, include class origin.
        """
        if mof:
            conn.compile_mof_string(tst_instances_mof, namespace=ns)
        else:
            conn.add_cimobjects(tst_classes, namespace=ns)
            conn.add_cimobjects(tst_instances, namespace=ns)

        lo = False   # TODO expand test to use lo parameterized.  Note that
        # since lo is deprecated we might just drop in and always
        # go false.

        iname = CIMInstanceName(cln,
                                keybindings={'InstanceID': key},
                                namespace=ns)
        if exp_err is None:
            # pylint: disable=protected-access
            inst = conn._get_instance(iname, ns, pl, lo, ico, iq)
            assert isinstance(inst, CIMInstance)
            assert inst.path.classname == cln
            assert iname == inst.path
            assert inst.classname == cln

            if pl == "":
                assert not inst.properties
            else:
                assert set(inst.keys()) == set(exp_props)

        else:
            with pytest.raises(CIMError) as exec_info:
                # pylint: disable=protected-access
                conn._get_instance(iname, ns, pl, lo, ico, iq)
            exc = exec_info.value
            assert exc.status_code_name == exp_err

    @pytest.mark.parametrize(
        "ns", [DEFAULT_NAMESPACE, 'root/blah'])
    @pytest.mark.parametrize(
        "mof", [False, True])
    @pytest.mark.parametrize(
        "cln, key, exp_ok",
        [
            ['CIM_Foo', 'CIM_Foo1', True],
            ['CIM_Foo', 'CIM_Foo2', True],
            ['CIM_Foo_sub', 'CIM_Foo_sub4', True],
            ['CIM_Foo_sub', 'CIM_Foo_sub99', False],
        ]
    )
    def test_find_instance(self, conn, tst_classes, tst_instances,
                           tst_instances_mof, ns, mof,
                           cln, key, exp_ok):
        # pylint: disable=no-self-use
        """
        Test the find instance repo method with both compiled and add
        creation of the repo.
        """
        if mof:
            conn.compile_mof_string(tst_instances_mof, namespace=ns)
        else:
            conn.add_cimobjects(tst_classes, namespace=ns)
            conn.add_cimobjects(tst_instances, namespace=ns)

        inst_repo = \
            conn._get_instance_repo(ns)  # pylint: disable=protected-access

        iname = CIMInstanceName(cln,
                                keybindings={'InstanceID': key},
                                namespace=ns)

        # pylint: disable=protected-access
        inst_tup = conn._find_instance(iname, inst_repo)
        assert isinstance(inst_tup, tuple)

        if exp_ok:
            assert isinstance(inst_tup[0], six.integer_types)
            assert isinstance(inst_tup[1], CIMInstance)
            assert equal_model_path(iname, inst_tup[1].path)
        else:
            assert inst_tup[0] is None
            assert inst_tup[1] is None

    @staticmethod
    def method2_callback(conn, methodname, object_name, **params):
        """Test callback function for ethod2. Not really used but
           installed to define function
        """
        pass

    @staticmethod
    def method1_callback(conn, methodname, object_name, **params):
        """Test callback function for method1. Not really used but
           installed to define function
        """
        pass

    @staticmethod
    def fuzzy_callback(conn, methodname, object_name, **params):
        """Test callback function for fuzzy method. Not really used but
           installed to define function
        """
        pass

    def test_display_repository(self, conn, tst_instances_mof):
        """
        Test the display of the repository with it various options.
        """
        # Create the objects in all namespaces
        namespaces = ['root/blah', 'interop']
        for ns in namespaces:
            conn.compile_mof_string(tst_instances_mof, namespace=ns)

            # Subscribe to InvokeMethod callback methods in the class.

            conn.add_method_callback('CIM_Foo_sub_sub', 'Method1',
                                     self.method1_callback,
                                     namespace=ns)
            conn.add_method_callback('CIM_Foo_sub_sub', 'Method2',
                                     self.method2_callback,
                                     namespace=ns)

            conn.add_method_callback('CIM_Foo', 'Fuzzy',
                                     self.fuzzy_callback,
                                     namespace=ns)

        # pylint: disable=unused-variable
        # Test various display_repository input and output options
        with OutputCapture() as output:  # noqa: F841
            conn.display_repository()
            for param in ('xml', 'mof', 'repr'):
                conn.display_repository(output_format=param)
            conn.display_repository(namespaces=namespaces)
            ns = namespaces[0]
            conn.display_repository(namespaces=[ns])
            conn.display_repository(namespaces=ns)

        with pytest.raises(ValueError):
            conn.display_repository(output_format='blah')

        tst_file_name = 'test_wbemconnection_mock_repo.txt'
        tst_file = os.path.join(SCRIPT_DIR, tst_file_name)

        conn.display_repository(dest=tst_file)
        assert os.path.isfile(tst_file)
        os.remove(tst_file)

    # TODO: Add test of format of the repo outut with a very simple schema
    #       to keep the comparison small.

    @pytest.mark.parametrize(
        "ns", [DEFAULT_NAMESPACE, 'root/blah'])
    def test_addcimobject(self, conn, ns, tst_classes, tst_instances,
                          tst_insts_big):
        """
        Test inserting all of the object definitions in the fixtures into
        the repository
        """
        # pylint: disable=no-self-use
        conn.add_cimobjects(tst_classes, namespace=ns)
        conn.add_cimobjects(tst_instances, namespace=ns)
        conn.add_cimobjects(tst_insts_big, namespace=ns)

        # pylint: disable=protected-access
        class_repo = conn._get_class_repo(ns)
        assert len(class_repo) == len(tst_classes)

        inst_repo = conn._get_instance_repo(ns)
        assert len(inst_repo) == len(tst_instances) + len(tst_insts_big)

    @pytest.mark.parametrize(
        "ns", [DEFAULT_NAMESPACE, 'root/blah'])
    def test_addcimobject_err(self, conn, ns, tst_classes, tst_instances):
        """Test error if duplicate instance inserted"""
        # pylint: disable=no-self-use
        conn.add_cimobjects(tst_classes, namespace=ns)
        conn.add_cimobjects(tst_instances, namespace=ns)
        with pytest.raises(ValueError):
            conn.add_cimobjects(tst_instances, namespace=ns)

    @pytest.mark.parametrize(
        "ns", [DEFAULT_NAMESPACE, 'root/blah'])
    def test_addcimobject_err1(self, conn, ns, tst_class):
        """Test error if class with no superclass"""
        # pylint: disable=no-self-use
        conn.add_cimobjects(tst_class, namespace=ns)
        c = CIMClass('CIM_BadClass', superclass='CIM_NotExist')
        with pytest.raises(ValueError):
            conn.add_cimobjects(c, namespace=ns)

    @pytest.mark.parametrize(
        "ns", [None, 'root/blah'])
    def test_compile_qualifiers(self, conn, ns, tst_qualifiers_mof):
        # pylint: disable=no-self-use
        """
        Test compile qualifiers with namespace from mof
        """
        conn.compile_mof_string(tst_qualifiers_mof, ns)

        assert conn.GetQualifier(
            'Association', namespace=ns).name == 'Association'
        assert conn.GetQualifier(
            'Indication', namespace=ns).name == 'Indication'
        assert conn.GetQualifier('Abstract', namespace=ns).name == 'Abstract'
        assert conn.GetQualifier('Aggregate', namespace=ns).name == 'Aggregate'
        assert conn.GetQualifier('Key', namespace=ns).name == 'Key'

        quals = conn.EnumerateQualifiers(namespace=ns)
        assert len(quals) == 9

    def test_unicode(self, conn):
        # pylint: disable=no-self-use
        """
        Test compile and display repository with unicode in mof string
        """
        ns = 'root/blah'

        qmof = """
        Qualifier Description : string = null,
            Scope(any),
            Flavor(EnableOverride, ToSubclass, Translatable);

        Qualifier Key : boolean = false,
            Scope(property, reference),
            Flavor(DisableOverride, ToSubclass);
        Qualifier Description : string = null,
            Scope(any),
            Flavor(EnableOverride, ToSubclass, Translatable);
        """

        cmof = u"""
        class CIM_Foo {
                [Key,
                 Description ("Å \u0420\u043e\u0441\u0441\u0438\u044f"
                              "\u00E0 voil\u00e0")]
            string InstanceID;
        };
        """

        conn.compile_mof_string(qmof, ns)
        conn.compile_mof_string(cmof, ns)

        with OutputCapture():
            conn.display_repository()
        tst_file_name = 'test_wbemconnection_mock_repo_unicode.txt'
        tst_file = os.path.join(SCRIPT_DIR, tst_file_name)

        conn.display_repository(dest=tst_file)
        assert os.path.isfile(tst_file)
        os.remove(tst_file)

    @pytest.mark.parametrize(
        "ns", [None, 'root/blah'])
    def test_compile_mult(self, conn, ns):  # pylint: disable=no-self-use
        """
        Test compile of multiple separate compile units including qualifiers,
        classes and instances.
        """
        # get the default namespace if ns is None
        tst_ns = conn.default_namespace if ns is None else ns

        q1 = """
        Qualifier Association : boolean = false,
            Scope(association),
            Flavor(DisableOverride, ToSubclass);
        """
        q2 = """
        Qualifier Description : string = null,
            Scope(any),
            Flavor(EnableOverride, ToSubclass, Translatable);

        Qualifier Key : boolean = false,
            Scope(property, reference),
            Flavor(DisableOverride, ToSubclass);
        """

        c1 = """
             [Description ("blah blah")]
        class CIM_Foo {
                [Key, Description ("This is key prop")]
            string InstanceID;
        };
        """
        c2 = """
            [Description ("Subclass of CIM_Foo")]
        class CIM_Foo_sub : CIM_Foo {
            string cimfoo_sub;
        };
        """
        i1 = """
        instance of CIM_Foo as $foo1 { InstanceID = "CIM_Foo1"; };
        """
        i2 = """
        instance of CIM_Foo as $foo2 { InstanceID = "CIM_Foo2"; };
        """
        i3 = """
        instance of CIM_Foo as $foo3 { InstanceID = "CIM_Foo3"; };
        """
        # TODO: Remove alias once inst without alias properly generates path
        i4 = """
        instance of CIM_Foo as $foo4 { InstanceID = "CIM_Foo4"; };
        """
        conn.compile_mof_string(q1, ns)
        qual_repo = \
            conn._get_qualifier_repo(tst_ns)  # pylint: disable=protected-access

        assert 'Association' in qual_repo
        conn.compile_mof_string(q2, ns)

        qual_repo = \
            conn._get_qualifier_repo(tst_ns)  # pylint: disable=protected-access
        assert 'Association' in qual_repo
        assert 'Description' in qual_repo
        assert 'Key' in qual_repo
        assert conn.GetQualifier('Association', namespace=ns)
        assert conn.GetQualifier('Description', namespace=ns)

        conn.compile_mof_string(c1, ns)
        assert conn.GetClass('CIM_Foo', namespace=ns, LocalOnly=False,
                             IncludeQualifiers=True, IncludeClassOrigin=True)

        conn.compile_mof_string(c2, ns)
        assert conn.GetClass('CIM_Foo_sub', namespace=ns)

        conn.compile_mof_string(i1, ns)
        rtn_names = conn.EnumerateInstanceNames('CIM_Foo', namespace=ns)
        assert len(rtn_names) == 1
        conn.compile_mof_string(i2, ns)
        rtn_names = conn.EnumerateInstanceNames('CIM_Foo', namespace=ns)
        assert len(rtn_names) == 2
        conn.compile_mof_string(i3, ns)
        rtn_names = conn.EnumerateInstanceNames('CIM_Foo', namespace=ns)
        assert len(rtn_names) == 3
        conn.compile_mof_string(i4, ns)
        rtn_names = conn.EnumerateInstanceNames('CIM_Foo', namespace=ns)
        assert len(rtn_names) == 4
        for name in rtn_names:
            inst = conn.GetInstance(name)
            assert inst.classname == 'CIM_Foo'

        for id_ in ['CIM_Foo4', 'CIM_Foo3', 'CIM_Foo2', 'CIM_Foo1']:
            iname = CIMInstanceName('CIM_Foo',
                                    keybindings={'InstanceID': id_},
                                    namespace=tst_ns)
            assert iname in rtn_names

    @pytest.mark.parametrize(
        "ns", [None, 'root/blah'])
    def test_compile_classes(self, conn, tst_classes_mof, ns):
        # pylint: disable=no-self-use
        """
        Test compile of classes into the repository
        """
        conn.compile_mof_string(tst_classes_mof, namespace=ns)

        assert conn.GetClass('CIM_Foo', namespace=ns).classname == 'CIM_Foo'
        assert conn.GetClass('CIM_Foo_sub',
                             namespace=ns).classname == 'CIM_Foo_sub'
        assert conn.GetClass('CIM_Foo_sub2',
                             namespace=ns).classname == 'CIM_Foo_sub2'
        assert conn.GetClass('CIM_Foo_sub_sub',
                             namespace=ns).classname == 'CIM_Foo_sub_sub'

        clns = conn.EnumerateClassNames(namespace=ns)
        assert len(clns) == 2
        clns = conn.EnumerateClassNames(namespace=ns, DeepInheritance=True)
        assert len(clns) == 5
        cls = conn.EnumerateClasses(namespace=ns, DeepInheritance=True)
        assert len(cls) == 5
        assert set(clns) == set([cl.classname for cl in cls])

    @pytest.mark.parametrize(
        "ns", [None, 'root/blah'])
    def test_compile_instances(self, conn, ns, tst_classes_mof):
        # pylint: disable=no-self-use
        """
        Test compile of instance mof into the repository in single file with
        classes.
        """
        # get the default namespace if ns is None
        tst_ns = conn.default_namespace if ns is None else ns
        insts_mof = """
            instance of CIM_Foo as $Alice {
            InstanceID = "Alice";
            };
            instance of CIM_Foo as $Bob {
                InstanceID = "Bob";
            };
            """
        # compile as single unit by combining classes and instances
        # The compiler builds the instance paths.
        all_mof = '%s\n\n%s' % (tst_classes_mof, insts_mof)

        conn.compile_mof_string(all_mof, namespace=ns)
        rtn_names = conn.EnumerateInstanceNames('CIM_Foo', namespace=ns)
        assert len(rtn_names) == 2

        for name in rtn_names:
            inst = conn.GetInstance(name)
            assert inst.classname == 'CIM_Foo'

        for id_ in ['Alice', 'Bob']:
            iname = CIMInstanceName('CIM_Foo',
                                    keybindings={'InstanceID': id_},
                                    namespace=tst_ns)
            assert iname in rtn_names

    @pytest.mark.parametrize(
        "ns", [None, 'root/blah'])
    def test_compile_assoc_mof(self, conn, tst_assoc_mof, ns,
                               tst_person_instance_names):
        # pylint: disable=no-self-use
        """
        Test the  tst_assoc_mof compiled mof to confirm compiled correct
        classes and instances.
        """
        conn.compile_mof_string(tst_assoc_mof, namespace=ns)

        clns = conn.EnumerateClassNames(namespace=ns, DeepInheritance=True)

        assert 'TST_Person' in clns
        assert 'TST_Lineage' in clns
        assert 'TST_Personsub' in clns
        assert 'TST_MemberOfFamilyCollection'
        assert 'TST_FamilyCollection'
        assert len(clns) == 5

        inst_names = conn.EnumerateInstanceNames('TST_Person', namespace=ns)
        assert len(inst_names) == 4
        insts = conn.EnumerateInstances('TST_Person', namespace=ns)
        assert len(inst_names) == 4

        # Test for particular instances in the enum response
        for name in tst_person_instance_names:
            result = [inst for inst in insts
                      if inst.classname == 'TST_Person' and
                      inst['name'] == name]
            assert len(result) == 1

        # test _get_instance
        for name in tst_person_instance_names:
            kb = {'name': name}
            inst_name = CIMInstanceName('TST_Person', kb, namespace=ns)
            conn.GetInstance(inst_name)

        inst_names = conn.EnumerateInstanceNames('TST_Lineage', namespace=ns)
        assert len(inst_names) == 3
        insts = conn.EnumerateInstances('TST_Lineage', namespace=ns)
        assert len(inst_names) == 3

        for inst_name in inst_names:
            conn.GetInstance(inst_name)

        # TODO test returned instance for match with what was created

    # pylint: disable=no-self-use
    def test_compile_dmtf_schema(self, conn):
        """
        Test Compiling DMTF MOF schema
        """
        ns = 'root/cimv2'
        # install the schema if necessary.
        install_dmtf_schema()

        conn.compile_mof_file(SCHEMA_MOF_FN, namespace=ns,
                              search_paths=[SCHEMA_MOF_DIR])

        # pylint: disable=protected-access
        assert len(conn._get_class_repo(ns)) == TOTAL_CLASSES
        assert len(conn._get_qualifier_repo(ns)) == TOTAL_QUALIFIERS

    def test_compile_err(self, conn, capsys):
        # pylint: disable=no-self-use
        """
        Test compile that has an error
        """
        q1 = """
            Qualifier Association : boolean = false,
                Scope(associations),
                Flavor(DisableOverride, ToSubclass);
        """

        with pytest.raises(MOFParseError):
            conn.compile_mof_string(q1)

        captured_out = capsys.readouterr()[0]
        assert "Scope(associations)" in captured_out


class TestClassOperations(object):
    """
    Test mocking of Class level operations including classname operations
    """
    def test_getclass(self, conn, tst_class):
        # pylint: disable=no-self-use
        """
        Test mocking wbemconnection getClass. Tests with default parameters
        except IncludeQualifiers

        """
        conn.add_cimobjects(tst_class)
        cl = conn.GetClass('CIM_Foo', IncludeQualifiers=True,
                           IncludeClassOrigin=True)

        cl.path = None
        assert cl == tst_class

    @pytest.mark.parametrize(
        "ns, cln, tst_ns, exp_er", [
            [None, 'CIM_Foo', None, None],
            [None, 'CIM_Foo', 'root/blah', 'CIM_ERR_INVALID_NAMESPACE'],
            ['root/blah', 'CIM_Foo', 'root/blah', None],
            [None, 'CIM_Foox', None, 'CIM_ERR_NOT_FOUND'],
        ]
    )
    def test_getclass_ns_er(self, conn, tst_class, ns, cln, tst_ns, exp_er):
        # pylint: disable=no-self-use
        """
        Test error returns from get class includeing;
          Invalid namespace
          Class Not found
        """
        conn.add_cimobjects(tst_class, namespace=ns)
        if exp_er is None:
            cl = conn.GetClass(cln, namespace=tst_ns,
                               IncludeQualifiers=True, IncludeClassOrigin=True)
            cl.path = None
            assert cl == tst_class
        else:
            with pytest.raises(CIMError) as exec_info:
                conn.GetClass(cln, namespace=tst_ns)
            exc = exec_info.value
            assert exc.status_code_name == exp_er

    @pytest.mark.parametrize(
        "ns", [None, 'root/blah'])
    @pytest.mark.parametrize(
        "cn, iq, ico",
        [
            ['CIM_Foo', False, False],
            ['CIM_Foo', True, False],
            ['CIM_Foo', True, True],
            ['CIM_Foo_sub', False, False],
            ['CIM_Foo_sub', True, False],
            ['CIM_Foo_sub', True, True],
        ]
    )
    def test_getclass_iqico(self, conn, tst_classes, ns, cn, iq, ico):
        # pylint: disable=no-self-use
        """
        Test mocking wbemconnection getClass
        test using Mock directly and returning a class.
        """
        for cl_ in tst_classes:
            if cl_.classname == cn:
                tst_class = cl_
        assert tst_class is not None

        conn.add_cimobjects(tst_classes, namespace=ns)

        cl = conn.GetClass(cn, namespace=ns, IncludeQualifiers=iq,
                           LocalOnly=True, IncludeClassOrigin=ico)

        cl.path = None

        c_tst = tst_class.copy()

        # remove all qualifiers and class_origins and test for equality
        if not iq:
            c_tst.qualifiers = NocaseDict()

            for prop in c_tst.properties:
                c_tst.properties[prop].qualifiers = NocaseDict()
            for method in c_tst.methods:
                c_tst.methods[method].qualifiers = NocaseDict()
                for param in c_tst.methods[method].parameters:
                    c_tst.methods[method].parameters[param].qualifiers = \
                        NocaseDict()
        if not ico:
            for prop in c_tst.properties:
                c_tst.properties[prop].class_origin = None
            for method in c_tst.methods:
                c_tst.methods[method].class_origin = None

        assert cl == c_tst

    @pytest.mark.parametrize(
        "ns", [None, 'root/blah'])
    @pytest.mark.parametrize(
        # parameters are classname(cn), LocalOnly(lo),
        # pl_exp(expected properties)
        "cn, lo, pl_exp", [
            ['CIM_Foo_sub', None, ['cimfoo_sub', 'InstanceID']],
            ['CIM_Foo_sub', True, ['cimfoo_sub']],
            ['CIM_Foo_sub', False, ['cimfoo_sub', 'InstanceID']],
            ['CIM_Foo_sub_sub', None, ['cimfoo_sub_sub', 'cimfoo_sub',
                                       'InstanceID']],
            ['CIM_Foo_sub_sub', True, ['cimfoo_sub_sub']],
            ['CIM_Foo_sub_sub', False, ['cimfoo_sub_sub', 'cimfoo_sub',
                                        'InstanceID']],
        ]
    )
    def test_getclass_lo(self, conn, ns, tst_classes, cn, lo, pl_exp):
        # pylint: disable=no-self-use
        """
        Test mocking wbemconnection getClass to test LocalOnly parameter.
        """
        conn.add_cimobjects(tst_classes, namespace=ns)

        if not lo:
            cl = conn.GetClass(cn, namespace=ns, LocalOnly=lo,
                               IncludeQualifiers=True)
        else:
            cl = conn.GetClass(cn, namespace=ns, LocalOnly=lo,
                               IncludeQualifiers=True)

        assert cl.classname == cn
        assert len(cl.properties) == len(pl_exp)
        rtn_props = cl.properties.keys()
        assert set(rtn_props) == set(pl_exp)

    @pytest.mark.parametrize(
        "ns", [None, 'root/blah'])
    # property list, expected properties in response
    @pytest.mark.parametrize(
        "pl, p_exp", [
            [None, ['InstanceID', 'cimfoo_sub', 'cimfoo_sub_sub']],
            ['', []],
            ['InstanceID', ['InstanceID']],
            [['InstanceID'], ['InstanceID']],
            [['InstanceID', 'InstanceID'], ['InstanceID']],
            [['InstanceID', 'cimfoo_sub'], ['InstanceID', 'cimfoo_sub']]
        ]
    )
    def test_getclass_pl(self, conn, ns, tst_classes, pl, p_exp):
        # pylint: disable=no-self-use
        """
        Test get_class property list filtering
        """
        conn.add_cimobjects(tst_classes, namespace=ns)
        cn = 'CIM_Foo_sub_sub'
        if pl is None:
            cl = conn.GetClass(cn, namespace=ns)
        else:
            cl = conn.GetClass(cn, PropertyList=pl, namespace=ns)

        assert len(cl.properties) == len(p_exp)
        rtn_props = cl.properties.keys()
        assert set(rtn_props) == set(p_exp)

    @pytest.mark.parametrize(
        "ns", [None, 'root/blah'])
    @pytest.mark.parametrize(
        "cn, di, cn_exp,", [
            [None, None, ['CIM_Foo', 'CIM_Foo_nokey']],
            [None, False, ['CIM_Foo', 'CIM_Foo_nokey']],
            [None, True, ['CIM_Foo', 'CIM_Foo_sub', 'CIM_Foo_sub2',
                          'CIM_Foo_sub_sub', 'CIM_Foo_nokey']],
            ['CIM_Foo', None, ['CIM_Foo_sub', 'CIM_Foo_sub2']],
            ['CIM_Foo', True, ['CIM_Foo_sub', 'CIM_Foo_sub2',
                               'CIM_Foo_sub_sub']],
            ['CIM_Foo_sub_sub', None, []],
        ]
    )
    def test_enumerateclassnames(self, conn, ns, cn, di, cn_exp, tst_classes):
        # pylint: disable=no-self-use
        """
        Test EnumerateClassNames mock with parameters for namespace,
        classname, DeepInheritance
        """
        conn.add_cimobjects(tst_classes, namespace=ns)

        if cn is None:
            rtn_clns = conn.EnumerateClassNames(namespace=ns,
                                                DeepInheritance=di,
                                                IncludeQualifiers=True)
        else:
            rtn_clns = conn.EnumerateClassNames(classname=cn,
                                                namespace=ns,
                                                DeepInheritance=di,
                                                IncludeQualifiers=True)

        for cn_ in rtn_clns:
            assert isinstance(cn_, six.string_types)
        assert len(rtn_clns) == len(cn_exp)
        assert set(rtn_clns) == set(cn_exp)
        # TODO add detailed test for di attribute.  This involves creating local
        # expected return and then comparing.

    @pytest.mark.parametrize(
        "ns", [None, 'root/blah'])
    @pytest.mark.parametrize(
        # iq: includequalifiers input parameter
        "iq", [None, False, True])
    @pytest.mark.parametrize(
        # ico: includeclassorigin input parameter
        "ico", [None, False, True])
    @pytest.mark.parametrize(
        # cn_param: classname input parameter
        # di: deepinheritance input parameter
        # pl_exp: Properties expected in response
        # len_exp: number of classes expected in response
        "cn_param, lo, di, pl_exp, len_exp", [
            [None, None, None, ['InstanceID', 'cimfoo'], 2],
            [None, None, True, ['InstanceID', 'cimfoo_sub', 'cimfoo_sub2',
                                'cimfoo_sub_sub', 'cimfoo'], 5],
            ['CIM_Foo', None, None, ['InstanceID', 'cimfoo_sub',
                                     'cimfoo_sub2'], 2],
            ['CIM_Foo', None, True, ['InstanceID', 'cimfoo_sub',
                                     'cimfoo_sub2', 'cimfoo_sub_sub'], 3],
            ['CIM_Foo_sub_sub', None, None, [], 0],
            ['CIM_Foo_sub_sub', None, True, [], 0],

            [None, True, None, ['InstanceID', 'cimfoo_sub', 'cimfoo_sub2',
                                'cimfoo_sub_sub', 'cimfoo'], 2],
            [None, True, True, ['InstanceID', 'cimfoo'], 5],
            ['CIM_Foo', True, None, ['InstanceID'], 2],
            ['CIM_Foo', True, True, ['InstanceID'], 3],
            ['CIM_Foo_sub_sub', True, None, [], 0],
            ['CIM_Foo_sub_sub', True, True, [], 0],

            [None, False, None, ['InstanceID', 'cimfoo_sub', 'cimfoo_sub2',
                                 'cimfoo_sub_sub', 'cimfoo'], 2],
            [None, False, True, ['InstanceID', 'cimfoo_sub', 'cimfoo_sub2',
                                 'cimfoo_sub_sub', 'cimfoo'], 5],
            ['CIM_Foo', False, None, ['InstanceID', 'cimfoo_sub',
                                      'cimfoo_sub2'], 2],
            ['CIM_Foo', False, True, ['InstanceID', 'cimfoo_sub',
                                      'cimfoo_sub2', 'cimfoo_sub_sub'], 3],
            ['CIM_Foo_sub_sub', False, None, [], 0],
            ['CIM_Foo_sub_sub', False, True, [], 0],
        ]
    )
    def test_enumerateclasses(self, conn, iq, ico, ns, cn_param, lo, di,
                              pl_exp, len_exp, tst_classes):
        # pylint: disable=no-self-use
        """
        Test EnumerateClasses for proper processing of input parameters.
        All tests in this test method pass and there should be no exceptions.
        Tests for correct properties, methods, and qualifiers, returned for
        lo and di and correct number of classes returned
        """
        conn.add_cimobjects(tst_classes, namespace=ns)

        if cn_param is None:
            rtn_classes = conn.EnumerateClasses(DeepInheritance=di,
                                                namespace=ns,
                                                LocalOnly=lo,
                                                IncludeQualifiers=iq,
                                                IncludeClassOrigin=ico)
        else:
            rtn_classes = conn.EnumerateClasses(classname=cn_param,
                                                namespace=ns,
                                                DeepInheritance=di,
                                                LocalOnly=lo,
                                                IncludeQualifiers=iq,
                                                IncludeClassOrigin=ico)

        assert len(rtn_classes) == len_exp

        for rtn_class in rtn_classes:
            assert(isinstance(rtn_class, CIMClass))

            if lo:
                # get the corresponding test input class
                tst_class = None
                for tst_cl in tst_classes:
                    if tst_cl.classname == rtn_class.classname:
                        tst_class = tst_cl
                        break
                assert tst_class

                assert set(rtn_class.properties.keys()) == \
                    set(tst_class.properties.keys())
            else:
                # not lo, returns all properties from superclasses.
                # test for return as subset of pl_exp
                rtn_set = set(rtn_class.properties.keys())
                assert rtn_set.issubset(set(pl_exp))

            # Confirm get_class returns the same set of properties
            rtn_getclass = conn.GetClass(rtn_class.classname, namespace=ns,
                                         DeepInheritance=di,
                                         LocalOnly=lo,
                                         IncludeQualifiers=iq,
                                         IncludeClassOrigin=ico)

            assert set(rtn_getclass.properties.keys()) == \
                set(rtn_class.properties.keys())

            assert set(rtn_getclass.methods.keys()) == \
                set(rtn_class.methods.keys())

            if ico:
                for prop in six.itervalues(rtn_getclass.properties):
                    assert prop.class_origin is not None

                for method in six.itervalues(rtn_getclass.methods):
                    assert method.class_origin is not None
            else:
                for prop in six.itervalues(rtn_getclass.properties):
                    assert prop.class_origin is None

                for method in six.itervalues(rtn_getclass.methods):
                    assert method.class_origin is None

            if iq:
                if rtn_getclass.qualifiers:
                    assert rtn_class.qualifiers
                for prop in six.itervalues(rtn_getclass.properties):
                    if rtn_getclass.properties[prop.name].qualifiers:
                        assert prop.qualifiers is not None

                for method in six.itervalues(rtn_getclass.methods):
                    if rtn_getclass.methods[method.name].qualifiers:
                        assert method.qualifiers is not None
            else:
                assert not rtn_class.qualifiers
                for prop in six.itervalues(rtn_getclass.properties):
                    assert not prop.qualifiers

                for method in six.itervalues(rtn_getclass.methods):
                    assert not method.qualifiers

    def process_pretcl(self, conn, pre_tst_classes, ns, tst_classes):
        """Support method for createclass. Executes createclass on the
           pre_tst_classes parameter. Compiles all classes found in the
           parameter
        """
        if pre_tst_classes:
            if isinstance(pre_tst_classes, list):
                for cls in pre_tst_classes:
                    self.process_pretcl(conn, cls, ns, tst_classes)
            elif isinstance(pre_tst_classes, six.string_types):
                for cls in tst_classes:
                    if cls.classname == pre_tst_classes:
                        conn.CreateClass(cls, namespace=ns)
            elif isinstance(pre_tst_classes, CIMClass):
                conn.CreateClass(pre_tst_classes, namespace=ns)

    @pytest.mark.parametrize(
        "ns", [None, 'root/blah'])
    @pytest.mark.parametrize(
        "pre_tst_classes, tcl, exp_rtn_cl, exp_err", [
            # pre_tst_classes: Create the defined class or classes before the
            #                  test. This allows testing subclass creation
            #                  May be class, name of class in tst_classes, or
            #                  list of class/classnames.
            # tcl: Either string defining test class name in tst_classes or
            #      CIMClass to be passed to CreateClass
            # exp_rtn_cl: None or expected CIMClass returned from get_instance
            # exp:err: None or Expected CIMError type string

            # Create class correctly
            [None, 'CIM_Foo', 'CIM_Foo', None],

            # Create valid subclass
            ['CIM_Foo', 'CIM_Foo_sub', 'CIM_Foo_sub', None],

            # Create valid 2nd level subclass.
            [['CIM_Foo', 'CIM_Foo_sub'], 'CIM_Foo_sub_sub',
             'CIM_Foo_sub_sub', None],

            # Create valid 2nd level subclass with property override.
            [
                ['CIM_Foo', 'CIM_Foo_sub'],
                CIMClass(
                    'CIM_Foo_sub_sub', superclass='CIM_Foo_sub',
                    properties={
                        'cimfoo_sub': CIMProperty(
                            'cimfoo_sub', "blah",  # noqa: E121
                            qualifiers={
                                'Override': CIMQualifier(
                                    'Override', 'cimfoo_sub_sub',
                                    propagated=False)
                            },
                            type='string', class_origin='CIM_Foo_sub_sub',
                            propagated=False)
                    }
                ),
                None, None
            ],

            # Create invalid subclass, dup property with no override
            [['CIM_Foo', 'CIM_Foo_sub'],
             CIMClass('CIM_Foo_sub_sub', superclass='CIM_Foo_sub',
                      properties={'cimfoo_sub':
                                  CIMProperty(
                                    'cimfoo_sub', "blah",  # noqa: E121
                                    type='string',
                                    class_origin='CIM_Foo_sub_sub',
                                    propagated=False)}),
             None, 'CIM_ERR_INVALID_PARAMETER'],

            # Fail because superclass does not exist in namespace
            [None, 'CIM_Foo_sub', None, 'CIM_ERR_INVALID_SUPERCLASS'],

            # Fails because trying to create incorrect type
            [None, CIMQualifierDeclaration('blah', 'string'), None,
             'CIM_ERR_INVALID_PARAMETER'],

            # No invalid namespace test defined because createclass creates
            # namespace
        ]
    )
    def test_createclass(self, conn, pre_tst_classes, tcl, tst_qualifiers_mof,
                         tst_classes, ns, exp_rtn_cl, exp_err):
        # pylint: disable=no-self-use
        """
            Test create class. Tests for namespace variable,
            correctly adding, and invalid add where class has superclass
            No way to do bad namespace error because this  method creates
            namespace if it does not exist.
        """
        # preinstall required qualifiers
        conn.compile_mof_string(tst_qualifiers_mof, namespace=ns)

        # if pretcl, create/install the pre test class.  Installs the
        # prerequisite classes into the repository.
        self.process_pretcl(conn, pre_tst_classes, ns, tst_classes)

        # Create the new_class to send to CreateClass from the
        # existing tst_classes
        if isinstance(tcl, six.string_types):
            for cl in tst_classes:
                if cl.classname == tcl:
                    new_class = cl
        else:
            new_class = tcl

        if exp_err is not None:
            with pytest.raises(CIMError) as exec_info:
                conn.CreateClass(new_class, namespace=ns)

            exc = exec_info.value
            assert(exc.status_code_name == exp_err)

        else:
            conn.CreateClass(new_class, namespace=ns)

            # Get class with localonly set and confirm against the
            # test class.
            rtn_class = conn.GetClass(new_class.classname,
                                      namespace=ns,
                                      IncludeQualifiers=True,
                                      IncludeClassOrigin=True,
                                      LocalOnly=True)

            rtn_class.path = None

            for pname, pvalue in rtn_class.properties.items():
                assert pvalue.propagated is False
                assert pvalue.class_origin == new_class.classname
            for mname, mvalue in rtn_class.methods.items():
                assert mvalue.propagated is False
                assert mvalue.class_origin == new_class.classname

            if isinstance(exp_rtn_cl, CIMClass):
                assert rtn_class == exp_rtn_cl

            elif isinstance(exp_rtn_cl, six.string_types):
                # This presumes that the tst_class has class_origin set
                # and propagated set
                for cl in tst_classes:
                    if cl.classname == exp_rtn_cl:
                        if cl != rtn_class:
                            print('cl==rtn_class\n%r\n%r' % (cl, rtn_class))
                        assert cl == rtn_class
            else:
                if isinstance(tcl, CIMClass):
                    if tcl != rtn_class:
                        print('\ntcl==rtn_class\n%r\n%r' % (tcl, rtn_class))
                    # tcl does not have propagated False on override qualifier
                    assert tcl == rtn_class
                else:
                    assert set(rtn_class.properties) == \
                        set(new_class.properties)
                    assert set(rtn_class.methods) == set(new_class.methods)
                    assert set(rtn_class.qualifiers) == \
                        set(new_class.qualifiers)

            # Get the class with local only false. and test for valid
            # ico, lo and non-lo properties/methods.

            rtn_class2 = conn.GetClass(new_class.classname,
                                       namespace=ns,
                                       IncludeQualifiers=True,
                                       IncludeClassOrigin=True,
                                       LocalOnly=False)

            if ns is None:
                ns = conn.default_namespace
            if new_class.superclass is None:
                superclasses = []
            else:
                superclasses = conn._get_superclassnames(new_class.classname,
                                                         ns)

            # TODO add to test to confirm that any property in superclasses
            # is in the returned instance. Local properties are covered by
            # testing against the new_class above.
            for pname, pvalue in rtn_class2.properties.items():
                if pname in rtn_class.properties:
                    assert pvalue.propagated is False
                    assert pvalue.class_origin == new_class.classname
                    assert pname in new_class.properties.keys()
                else:
                    assert pvalue.propagated is True
                    assert pvalue.class_origin in superclasses

            for mname, mvalue in rtn_class2.methods.items():
                if mname in rtn_class.methods:
                    assert mvalue.propagated is False
                    assert mvalue.class_origin == new_class.classname
                    assert mname in new_class.methods.keys()
                else:
                    assert mvalue.propagated is True
                    assert mvalue.class_origin in superclasses

    @pytest.mark.parametrize(
        "ns", [None, 'root/blah'])
    @pytest.mark.parametrize(
        "cn, exp_exc", [
            ['CIM_Foo', None],
            ['CIM_Foo', None],
            ['CIM_Foox', 'CIM_ERR_NOT_FOUND'],
            ['CIM_Foox', 'CIM_ERR_NOT_FOUND'],
        ]
    )
    def test_deleteclass(self, conn, tst_classes, cn, ns, exp_exc):
        # pylint: disable=no-self-use
        """
            Test create class. Tests for namespace variable,
            correctly adding, and invalid add where class has superclass
        """
        conn.add_cimobjects(tst_classes, namespace=ns)
        if not exp_exc:
            conn.DeleteClass(cn, namespace=ns)
            with pytest.raises(CIMError) as exec_info:
                conn.GetClass(cn, namespace=ns)
                exc = exec_info.value
                assert exc.status_code_name == 'CIM_ERR_NOT_FOUND'
        else:
            with pytest.raises(CIMError) as exec_info:
                conn.DeleteClass(cn, namespace=ns)
            exc = exec_info.value
            assert exc.status_code_name == exp_exc


class TestInstanceOperations(object):
    """
    Test the Instance mock operations including get, enumerate, create
    delete, modify, execquery, and invoke method on instance
    """

    @pytest.mark.parametrize(
        "ns, cln, inst_id, tst_ns, exp_er", [
            [None, 'CIM_Foo', 'CIM_Foo1', None, None],
            ['root/blah', 'CIM_Foo', 'CIM_Foo1', 'root/blah', None],
            ['blah', 'CIM_Foo', 'badid', 'blah', 'CIM_ERR_NOT_FOUND'],
            ['blah', 'CIM_Foo', 'CIM_Foo1', 'whoop',
             'CIM_ERR_INVALID_NAMESPACE'],
            ['blah', 'CIM_Foox', 'CIM_Foo1', 'blah', 'CIM_ERR_INVALID_CLASS'],
        ]
    )
    def test_getinstance(self, conn, ns, cln, inst_id, tst_ns, exp_er,
                         tst_classes, tst_instances):
        # pylint: disable=no-self-use
        """
        Test the With multiple ns for successful GetInstance and with
        error for namespace and instance name
        """
        conn.add_cimobjects(tst_classes, namespace=ns)
        conn.add_cimobjects(tst_instances, namespace=ns)
        req_inst_path = CIMInstanceName(cln, {'InstanceID': inst_id},
                                        namespace=tst_ns)
        if not exp_er:
            inst = conn.GetInstance(req_inst_path)
            inst.path.namespace = ns
            assert inst.path == req_inst_path
            # TODO test returned instance. Right now only comparing
            # the paths

        else:
            with pytest.raises(CIMError) as exec_info:
                conn.GetInstance(req_inst_path)
            exc = exec_info.value
            assert(exc.status_code_name == exp_er)

    @pytest.mark.parametrize(
        "ns", [None, 'root/blah']
    )
    @pytest.mark.parametrize(
        "lo, iq, ico", [
            [None, None, None],
            [None, True, None],
            [None, True, True],
        ]
    )
    def test_getinstancelite_opts(self, conn_lite, ns, lo, iq, ico,
                                  tst_instances):
        # pylint: disable=no-self-use
        """
        Test getting an instance from the repository with GetInstance and
        the options set
        """
        # TODO extend to test lo and iq
        conn_lite.add_cimobjects(tst_instances, namespace=ns)
        request_inst_path = CIMInstanceName(
            'CIM_Foo', {'InstanceID': 'CIM_Foo1'}, namespace=ns)

        inst = conn_lite.GetInstance(request_inst_path, LocalOnly=lo,
                                     IncludeQualifiers=iq,
                                     IncludeClassOrigin=ico)

        inst.path.namespace = ns
        assert(inst.path == request_inst_path)
        # TODO add tests for iq and ico

    @pytest.mark.parametrize(
        "ns", [None, 'root/blah']
    )
    @pytest.mark.parametrize(
        "lo, iq, ico", [
            [None, None, None],
            [None, True, None],
            [None, True, True],
        ]
    )
    def test_getinstance_opts(self, conn, ns, lo, iq, ico, tst_classes,
                              tst_instances):
        # pylint: disable=no-self-use
        """
        Test getting an instance from the repository with GetInstance and
        the options set
        """
        # TODO extend to test lo and iq
        conn.add_cimobjects(tst_classes, namespace=ns)
        conn.add_cimobjects(tst_instances, namespace=ns)
        request_inst_path = CIMInstanceName(
            'CIM_Foo', {'InstanceID': 'CIM_Foo1'}, namespace=ns)

        inst = conn.GetInstance(request_inst_path, LocalOnly=lo,
                                IncludClassOrigin=ico, IncludQualifiers=iq)

        inst.path.namespace = ns
        assert(inst.path == request_inst_path)
        # TODO test complete instances returned. Now only testing paths

    @pytest.mark.parametrize(
        "ns", [None, 'root/blah']
    )
    @pytest.mark.parametrize(
        "cln, inst_id, pl, props_exp",
        [
            #   cln        inst_id   pl      props_exp
            ['CIM_Foo', 'CIM_Foo1', None, ['InstanceID']],
            ['CIM_Foo', 'CIM_Foo1', "", []],
            ['CIM_Foo', 'CIM_Foo1', "blah", []],
            ['CIM_Foo', 'CIM_Foo1', 'InstanceID', ['InstanceID']],
            ['CIM_Foo', 'CIM_Foo1', ['InstanceID'], ['InstanceID']],
            ['CIM_Foo', 'CIM_Foo1', ['INSTANCEID'], ['InstanceID']],
            ['CIM_Foo_sub', 'CIM_Foo_sub4', None, ['InstanceID', 'cimfoo_sub']],
            ['CIM_Foo_sub', 'CIM_Foo_sub4', "", []],
            ['CIM_Foo_sub', 'CIM_Foo_sub4', 'cimfoo_sub', ['cimfoo_sub']],
            ['CIM_Foo_sub', 'CIM_Foo_sub4', "blah", []],
            ['CIM_Foo_sub', 'CIM_Foo_sub4', 'InstanceID', ['InstanceID']],
            ['CIM_Foo_sub', 'CIM_Foo_sub4', ['INSTANCEID'], ['InstanceID']],
            ['CIM_Foo_sub', 'CIM_Foo_sub4', ['InstanceID', 'cimfoo_sub'],
             ['InstanceID', 'cimfoo_sub']],
        ]
    )
    def test_getinstance_pl(self, conn, ns, cln, inst_id, pl, props_exp,
                            tst_classes, tst_instances):
        # pylint: disable=no-self-use
        """
        Test the variations of property list against what is returned by
        GetInstance.
        """
        conn.add_cimobjects(tst_classes, namespace=ns)
        conn.add_cimobjects(tst_instances, namespace=ns)
        request_inst_path = CIMInstanceName(
            cln, {'InstanceID': inst_id}, namespace=ns)

        inst = conn.GetInstance(request_inst_path, PropertyList=pl)

        inst.path.namespace = ns
        assert(inst.path == request_inst_path)

        # Assert p_exp(expected returned properties) matches returned
        # properties.
        assert set([x.lower() for x in props_exp]) ==  \
            set([x.lower() for x in inst.keys()])

    @pytest.mark.parametrize(
        "ns", [None, 'root/blah'])
    def test_enumerateinstnames_lite(self, conn_lite, ns, tst_instances):
        # pylint: disable=no-self-use
        """
        Test mock EnumerateInstanceNames against instances in tst_instances
        fixture. This test builds an instance only repository and uses
        conn_lite.
        """
        conn_lite.add_cimobjects(tst_instances, namespace=ns)

        cln = 'CIM_Foo'

        # since we do not have classes in the repository, we get back only
        # instances of the defined class
        rtn_inst_names = conn_lite.EnumerateInstanceNames(cln, ns)

        nsx = conn_lite.default_namespace if ns is None else ns

        # pylint: disable=protected-access
        request_inst_names = [i.path for i in conn_lite._get_instance_repo(nsx)
                              if i.classname == cln]

        assert len(rtn_inst_names) == len(request_inst_names)

        for inst_name in rtn_inst_names:
            assert isinstance(inst_name, CIMInstanceName)
            assert inst_name in request_inst_names
            assert inst_name.classname == cln

    @pytest.mark.parametrize(
        "ns", [None, 'root/blah'])
    def test_enumerateinstancenames(self, conn, ns, tst_classes, tst_instances):
        # pylint: disable=no-self-use
        """
        Test mock EnumerateInstanceNames against instances in tst_instances
        fixture with both classes and instances in the repo.  This does not
        use repo_lite
        """
        conn.add_cimobjects(tst_classes, namespace=ns)
        conn.add_cimobjects(tst_instances, namespace=ns)

        cln = 'CIM_Foo'

        rtn_inst_names = conn.EnumerateInstanceNames(cln, ns)

        nsx = conn.default_namespace if ns is None else ns

        # pylint: disable=protected-access
        exp_subclasses = conn._get_subclass_names(cln, nsx, True)
        exp_subclasses.append(cln)

        request_inst_names = [i.path for i in conn._get_instance_repo(nsx)
                              if i.classname in exp_subclasses]

        assert len(rtn_inst_names) == len(request_inst_names)

        for inst_name in rtn_inst_names:
            assert isinstance(inst_name, CIMInstanceName)
            assert inst_name in request_inst_names
            assert inst_name.classname in exp_subclasses

    @pytest.mark.parametrize(
        "ns, cln, tst_ns, exp_er", [  # TODO integrate this into normal test
            # ns: repo namespace
            # cln: target classname
            # tst_ns: namespace for enumerateinstances
            # exp_er: None or expected error code
            ['root/blah', None, 'root/blah', None],
            [None, None, None, None],
            ['blah', 'CIM_Foo', 'whoop', 'CIM_ERR_INVALID_NAMESPACE'],
            ['blah', 'CIM_Foox', 'blah', 'CIM_ERR_INVALID_CLASS'],
        ]
    )
    def test_enumerateinstnames_ns_er(self, conn, tst_classes,
                                      tst_instances, ns, cln, tst_ns, exp_er,):
        # pylint: disable=no-self-use
        """
        Test basic successful operation with namespaces and test for
        namespace and classname errors.
        """
        conn.add_cimobjects(tst_classes, namespace=ns)
        conn.add_cimobjects(tst_instances, namespace=ns)
        enum_classname = 'CIM_Foo'

        if not exp_er:
            # since we do not have classes in the repository, we get back only
            # instances of the defined class
            rtn_inst_names = conn.EnumerateInstanceNames(enum_classname, ns)

            exp_clns = [enum_classname, 'CIM_Foo_sub', 'CIM_Foo_sub2',
                        'CIM_Foo_sub_sub']

            # pylint: disable=protected-access
            request_inst_names = [i.path for i in conn._get_inst_repo(ns)
                                  if i.classname in exp_clns]

            assert len(rtn_inst_names) == len(request_inst_names)

            for inst_name in rtn_inst_names:
                assert isinstance(inst_name, CIMInstanceName)
                assert inst_name in request_inst_names
                # TODO change to use algorithm to get list of possible
                # classes. Right now just fixed list
                assert inst_name.classname in exp_clns

        else:
            with pytest.raises(CIMError) as exec_info:
                conn.EnumerateInstanceNames(cln, tst_ns)
            exc = exec_info.value
            assert(exc.status_code_name == exp_er)

    def test_enumerateinstances_lite(self, conn_lite, tst_instances):
        # pylint: disable=no-self-use
        """
        Test mock EnumerateInstances with repo_lite set.
        This returns only instances of the target class.
        """
        conn_lite.add_cimobjects(tst_instances)
        enum_classname = 'CIM_Foo'
        rtn_insts = conn_lite.EnumerateInstances(enum_classname)

        tst_inst_dict = {}
        for inst in tst_instances:
            tst_inst_dict[str(model_path(inst.path))] = inst

        # TODO compute number expected be in returned. This is number with
        # CIM_Foo as classname
        assert len(rtn_insts) == 2
        for inst in rtn_insts:
            assert isinstance(inst, CIMInstance)
            assert inst.classname == enum_classname

            mp = str(model_path(inst.path))
            assert mp in tst_inst_dict
            tst_inst = tst_inst_dict[mp]
            assert tst_inst is not None
            assert insts_equal(inst, tst_inst)

    @pytest.mark.parametrize(
        "ns", [None, 'root/blah'])
    @pytest.mark.parametrize(
        "cln, di, exp_cln, exp_prop", [
            # di True, expect all subprops
            ['CIM_Foo', True,
             ['CIM_Foo', 'CIM_Foo_sub', 'CIM_Foo_sub2', 'CIM_Foo_sub_sub'],
             ['InstanceID', 'cimfoo_sub', 'cimfoo_sub2', 'cimfoo_sub_sub']],
            ['CIM_Foo', False,
             ['CIM_Foo', 'CIM_Foo_sub', 'CIM_Foo_sub2', 'CIM_Foo_sub_sub'],
             ['InstanceID']],
        ]
    )
    def test_enumerateinstances_nolite(self, conn, tst_classes, tst_instances,
                                       ns, cln, di, exp_cln, exp_prop):
        # pylint: disable=no-self-use
        """
        Test mock EnumerateInstances without repo_lite. Returns instances
        of defined class and subclasses
        """
        conn.add_cimobjects(tst_classes, namespace=ns)
        conn.add_cimobjects(tst_instances, namespace=ns)

        rtn_insts = conn.EnumerateInstances(cln, namespace=ns,
                                            DeepInheritance=di)

        tst_inst_dict = {}
        for inst in tst_instances:
            tst_inst_dict[str(model_path(inst.path))] = inst

        # TODO compute number should be returned. Right now fixed number
        assert len(rtn_insts) == 8
        rtn_cln = []
        for inst in rtn_insts:
            assert isinstance(inst, CIMInstance)
            assert inst.classname in exp_cln   # don't need this
            rtn_cln.append(inst.classname)

            mp = str(model_path(inst.path))
            assert mp in tst_inst_dict
            tst_inst = tst_inst_dict[mp]
            assert tst_inst is not None
            # if not di it reports fixed set of properties based parameterize
            if not di:
                assert set(inst.keys()) == set(exp_prop)
            else:
                # di so properties differ instances of each different class.
                # TODO improve algorithm so we define exactly what properties
                # we should receive.
                assert set(inst.keys()).issubset(exp_prop)

    @pytest.mark.parametrize(
        "ns", [None, 'root/blah'])
    def test_enumerateinstances_ns(self, conn_lite, ns, tst_instances):
        # pylint: disable=no-self-use
        """
        Test mock EnumerateInstances with namespace as an input
        optional parameter defined by parametrizeration
        """
        conn_lite.add_cimobjects(tst_instances, namespace=ns)
        enum_classname = 'CIM_Foo'
        rtn_insts = conn_lite.EnumerateInstances('CIM_Foo', ns)

        assert len(rtn_insts) == 2
        for inst in rtn_insts:
            assert isinstance(inst, CIMInstance)
            assert inst.classname == enum_classname
            # TODO Test actual instance returned

    @pytest.mark.parametrize(
        "ns", [None, 'root/blah'])
    @pytest.mark.parametrize(
        "cln, pl, props_exp",
        [
            #  cln       pl     props_exp
            ['CIM_Foo', None, ['InstanceID']],
            ['CIM_Foo', "", []],
            ['CIM_Foo', "blah", []],
            ['CIM_Foo', 'InstanceID', ['InstanceID']],
            ['CIM_Foo', ['InstanceID'], ['InstanceID']],
            ['CIM_Foo', ['INSTANCEID'], ['InstanceID']],
            ['CIM_Foo_sub', None, ['InstanceID', 'cimfoo_sub']],
            ['CIM_Foo_sub', "", []],
            ['CIM_Foo_sub', 'cimfoo_sub', ['cimfoo_sub']],
            ['CIM_Foo_sub', "blah", []],
            ['CIM_Foo_sub', 'InstanceID', ['InstanceID']],
            ['CIM_Foo_sub', ['INSTANCEID'], ['InstanceID']],
            ['CIM_Foo_sub', ['InstanceID', 'cimfoo_sub'],
             ['InstanceID', 'cimfoo_sub']],
        ]
    )
    def test_enumerateinstances_pl(self, conn_lite, ns, cln, pl, props_exp,
                                   tst_instances):
        # pylint: disable=no-self-use
        """
        Test mock EnumerateInstances with namespace as an input
        optional parameter defined by parametrizeration.using repo_lite.

        """
        conn_lite.add_cimobjects(tst_instances, namespace=ns)

        rtn_insts = conn_lite.EnumerateInstances(cln, namespace=ns,
                                                 PropertyList=pl)

        assert len(rtn_insts) == 2
        for inst in rtn_insts:
            assert isinstance(inst, CIMInstance)
            assert inst.classname == cln
            # TODO Test actual instance returned

        # Assert p_exp(expected returned properties) matches returned
        # properties.
        for inst in rtn_insts:
            assert set([x.lower() for x in props_exp]) ==  \
                set([x.lower() for x in inst.keys()])

    # TODO repeat pl test with conn rather than connlite

    @pytest.mark.parametrize(
        "ns", [None, 'root/blah'])
    @pytest.mark.parametrize(
        "di", [None, True])
    def test_enumerateinstances_di(self, conn_lite, tst_instances, ns, di):
        # pylint: disable=no-self-use
        """
        Test EnumerateInstances with DeepInheritance options.
        TODO extend to cover property list.
        """
        conn_lite.add_cimobjects(tst_instances, namespace=ns)
        enum_classname = 'CIM_Foo'
        rtn_insts = conn_lite.EnumerateInstances('CIM_Foo', ns,
                                                 DeepInheritance=di)

        tst_cim_foo = [i for i in tst_instances
                       if i.path.classname == enum_classname]
        assert len(rtn_insts) == len(tst_cim_foo)
        for inst in rtn_insts:
            assert isinstance(inst, CIMInstance)
            assert inst.classname == enum_classname
            # props = [p for p in inst]
            # TODO Test actual instance returned

    @pytest.mark.parametrize(
        "ns", [None, 'root/blah'])
    @pytest.mark.parametrize(
        "di, pl, exp_p, exp_inst", [
            # [None, None, ['InstanceID', 'cimfoo_sub'], 8],
            [False, None, ['InstanceID'], 8],
        ]
    )
    def test_enumerateinstances_di2(self, conn, tst_classes, tst_instances, ns,
                                    di, pl, exp_p, exp_inst):
        # pylint: disable=no-self-use
        """
        Test EnumerateInstances with DeepInheritance and propertylist opetions.
        """
        conn.add_cimobjects(tst_classes, namespace=ns)
        conn.add_cimobjects(tst_instances, namespace=ns)

        cln = 'CIM_Foo'
        rtn_insts = conn.EnumerateInstances(cln, namespace=ns,
                                            DeepInheritance=di,
                                            PropertyList=pl)

        assert len(rtn_insts) == exp_inst

        target_class = conn.GetClass(cln, namespace=ns, LocalOnly=False)
        cl_props = [p.name for p in six.itervalues(target_class.properties)]

        tst_class_names = [cl.classname for cl in tst_classes]

        for inst in rtn_insts:
            assert isinstance(inst, CIMInstance)
            assert inst.classname in tst_class_names
            inst_props = list(set([p for p in inst]))
            if di is not True:   # inst props should match cl_props
                if len(inst_props) != len(cl_props):
                    # TODO: Still have issue with one test. and am therefore
                    # displaying the following as a reminder
                    print('TODO props %s and %s should match.\nprops=%s\n'
                          'clprops=%s' % (len(inst_props),
                                          len(cl_props), inst_props, cl_props))

                assert len(inst_props) == len(cl_props)
                assert set(inst_props) == set(cl_props)
            else:
                di_class = conn.GetClass(inst.classname, namespace=ns,
                                         LocalOnly=False)
                cl_props = [p.name for p in six.itervalues(di_class.properties)]
                assert len(inst_props) == len(cl_props)
                assert set(inst_props) == set(cl_props)
            # TODO Test actual instance returned

    # TODO test for ico and iq
    # TODO test for pl where repository contains classes
    # TODO test for instances do not exist.

    @pytest.mark.parametrize(
        "ns, cln, tst_ns, exp_er", [  # TODO integrate this into normal test
            # ['blah', None, 'blah', None],
            ['blah', 'CIM_Foo', 'whoop', 'CIM_ERR_INVALID_NAMESPACE'],
            # ['blah', 'CIM_Foox', 'blah', 'CIM_ERR_INVALID_CLASS'],
        ]
    )
    def test_enumerateinstances_er(self, conn, ns, cln, tst_ns,
                                   exp_er, tst_classes, tst_instances):
        # pylint: disable=no-self-use
        """
        Test the various error cases for Enumerate.  Errors include:
        Invalid namespace, instance not_found and if a class is specified
        on input, shou
        """
        conn.add_cimobjects(tst_classes, namespace=ns)
        conn.add_cimobjects(tst_instances, namespace=ns)

        if not exp_er:
            # since we do not have classes in the repository, we get back only
            # instances of the defined class
            rtn_inst_names = conn.EnumerateInstanceNames(cln, ns)

            # pylint: disable=protected-access
            request_inst_names = [i.path for i in conn._get_inst_repo(ns)
                                  if i.classname == cln]

            assert len(rtn_inst_names) == len(request_inst_names)

            for inst_name in rtn_inst_names:
                assert isinstance(inst_name, CIMInstanceName)
                assert inst_name in request_inst_names
                assert inst_name.classname == cln

        else:
            with pytest.raises(CIMError) as exec_info:
                conn.EnumerateInstances(cln, tst_ns)
            exc = exec_info.value
            assert(exc.status_code_name == exp_er)

    @pytest.mark.parametrize(
        "ns", [None, 'root/blah'])
    @pytest.mark.parametrize(
        "tst, new_inst, exp_err", [
            # tst: integer that defines special modification within test
            #      execution. 0 means no modification
            # new_instance: New instance to be tested. If integer it is the
            #      index into tst_instances that is to be created. Otherwise
            #      it is a CIMInstance definition.
            # exp_err: None or expected error code for test as string
            [2, 0, None],
            [2, 1, None],
            [2, 4, None],
            [2, 5, None],
            [2, 7, None],

            # test invalid namespace
            [1, CIMInstance('CIM_Foo_sub',
                            properties={'InstanceID': 'inst1',
                                        'cimfoo_sub': 'data1'}),
             'CIM_ERR_INVALID_NAMESPACE'],

            # No key property in new instance
            [0, CIMInstance('CIM_Foo_sub',
                            properties={'cimfoo_sub': 'data2'}),
             'CIM_ERR_INVALID_PARAMETER'],

            # Test instance class not in repository
            [0, CIMInstance('CIM_Foo_subx',
                            properties={'InstanceID': 'inst1',
                                        'cimfoo_sub': 'data3'}),
             'CIM_ERR_INVALID_CLASS'],

            # Test invalid property. Property not in class
            [0, CIMInstance('CIM_Foo_sub',
                            properties={'InstanceID': 'inst1',
                                        'cimfoo_subx': 'wrong prop name'}),
             'CIM_ERR_INVALID_PARAMETER'],

            # Test invalid property in new instance, type not same as class
            [0, CIMInstance('CIM_Foo_sub',
                            properties={'InstanceID': 'inst1',
                                        'cimfoo_sub': Uint32(6)}),
             'CIM_ERR_INVALID_PARAMETER'],

            # test array type mismatch
            [0, CIMInstance('CIM_Foo_sub',
                            properties={'InstanceID': 'inst1',
                                        'cimfoo_sub': ['blah', 'blah']}),
             'CIM_ERR_INVALID_PARAMETER'],

            # NewInstance is not an instance
            [0, CIMClass('CIM_Foo_sub'), 'CIM_ERR_INVALID_PARAMETER'],
        ]
    )
    def test_createinstance(self, conn, ns, tst, new_inst, exp_err, tst_classes,
                            tst_instances):
        # pylint: disable=no-self-use
        """
        Test creating an instance.  Tests by creating an
        instance and then getting that instance. This also includes error
        tests if exp_err is not None.
        """
        conn.add_cimobjects(tst_classes, namespace=ns)

        # modify input in accord with the tst parameter
        if tst == 0:   # pass on the new_inst defined in the parameter
            new_insts = [new_inst]
        elif tst == 1:   # invalid namespace test
            ns = 'BadNamespace'
            new_insts = [tst_instances[0]]
        elif tst == 2:  # Create one entry from the tst_instances list
            assert isinstance(new_inst, int)
            new_insts = [tst_instances[new_inst]]
        elif tst == 3:   # create everything in tst_instances
            new_insts = tst_instances
        else:  # Error. Test not defined.
            assert False, "The tst parameter %s not defined" % tst

        if not exp_err:
            for inst in new_insts:
                rtn_inst_name = conn.CreateInstance(inst, ns)
                rtn_inst = conn.GetInstance(rtn_inst_name)

                inst.path.namespace = rtn_inst.path.namespace
                assert rtn_inst.path == inst.path
                assert rtn_inst == inst

        else:
            with pytest.raises(CIMError) as exec_info:
                conn.CreateInstance(new_insts[0], ns)
            exc = exec_info.value
            assert exc.status_code_name == exp_err

    @pytest.mark.parametrize(
        "ns", [None, 'root/blah'])
    def test_createinstance_dup(self, conn, tst_class, tst_instances, ns):
        # pylint: disable=no-self-use
        """
        Test duplicate instance cannot be created.
        """
        conn.add_cimobjects(tst_class, namespace=ns)

        new_inst = tst_instances[0]

        rtn_inst_name = conn.CreateInstance(new_inst, ns)
        rtn_inst = conn.GetInstance(rtn_inst_name)

        new_inst.path.namespace = rtn_inst.path.namespace
        assert rtn_inst.path == new_inst.path
        assert rtn_inst == new_inst

        # test add again
        with pytest.raises(CIMError) as exec_info:
            conn.CreateInstance(new_inst)
        exc = exec_info.value
        assert(exc.status_code_name == 'CIM_ERR_ALREADY_EXISTS')

    @pytest.mark.parametrize(
        "ns", [None, 'root/blah'])
    def test_createinstance_lite(self, conn_lite, tst_instances, ns):
        # pylint: disable=no-self-use
        """Test that we reject createinstance when repolite set."""
        with pytest.raises(CIMError) as exec_info:
            conn_lite.CreateInstance(tst_instances[0], ns)
        exc = exec_info.value
        assert exc.status_code_name == 'CIM_ERR_NOT_SUPPORTED'

    @pytest.mark.parametrize(
        "ns", ['None, root/blah'])
    @pytest.mark.parametrize(
        "sp, nv, pl, exp_resp", [
            # sp: Special test. integer. 0 means No special test.
            #     other positive integers demand instance mod before modify
            # nv: (new value) single list containing a property name/value or
            #   iterable where each entry contains a propertyname/value
            # pl: property list for ModifyInstanceor None. May be empty
            #   property list
            # exp_resp: True if change expected. False if none expected.
            #   If exp_change is a string,it is error code expected.

            # change any property that is different
            [0, ['cimfoo_sub', 'newval'], None, True],
            # change this property only
            [0, ['cimfoo_sub', 'newval'], ['cimfoo_sub'], True],
            # Duplicate in property list
            [0, ['cimfoo_sub', 'newval'], ['cimfoo_sub', 'cimfoo_sub'], True],
            # empty prop list, no change
            [0, ['cimfoo_sub', 'newval'], [], False],
            # pl for prop that does not change
            [0, ['cimfoo_sub', 'newval'], ['cimfoo_sub_sub'], False],
            # change any property that is different
            [0, ['cimfoo_sub_sub', 'newval'], None, True],
            # change this property
            [0, ['cimfoo_sub_sub', 'newval'], ['cimfoo_sub_sub'], True],
            # empty prop list, no change
            [0, ['cimfoo_sub_sub', 'newval'], [], False],
            # pl for prop that does not change
            [0, ['cimfoo_sub_sub', 'newval'], ['cimfoo_sub'], False],
            # Prop name not in class but in Property list
            [0, ['cimfoo_sub', 'newval'], ['cimfoo_sub', 'not_in_class'],
             'CIM_ERR_INVALID_PARAMETER'],
            # change any property that is different, no prop list
            [0, [('cimfoo_sub', 'newval'),
                 ('cimfoo_sub_sub', 'newval2'), ], None, True],
            # Invalid change, Key property
            # change any property that is different, no prop list
            [0, ['InstanceID', 'newval'], None, 'CIM_ERR_NOT_FOUND'],
            # Invalid change, Key property
            # change any property that is different, no prop list
            [0, ['InstanceID', 'newval'], None, 'CIM_ERR_NOT_FOUND'],
            # Bad namespace. Depends on special code in path
            [2, ['cimfoo_sub', 'newval'], None, 'CIM_ERR_INVALID_NAMESPACE'],
            # Path and instance classnames differ. Changes inst classname
            [1, ['cimfoo_sub', 'newval'], None, 'CIM_ERR_INVALID_PARAMETER'],
            # Do one where path has bad classname
            [3, ['cimfoo_sub', 'newval'], None, 'CIM_ERR_INVALID_PARAMETER'],
            # 4 path and inst classnames same but not in repo
            [4, ['cimfoo_sub', 'newval'], None, 'CIM_ERR_INVALID_CLASS'],
            # 5, no properties in modified instance
            [5, [], None, False],

            # TODO additional tests.
            # 1. only some properties in modifiedinstance and variations of
            #    property list
        ]
    )
    def test_modifyinstance(self, conn, ns, sp, nv, pl, exp_resp, tst_classes,
                            tst_instances):
        # pylint: disable=no-self-use
        """
        Test the mock of modifying an existing instance. Gets the instance
        from the repo, modifies a property and calls ModifyInstance
        """
        conn.add_cimobjects(tst_classes, namespace=ns)
        conn.add_cimobjects(tst_instances, namespace=ns)

        insts = conn.EnumerateInstances('CIM_Foo_sub_sub', namespace=ns)
        assert insts
        orig_instance = insts[0]
        modify_instance = orig_instance.copy()

        # property values from the nv parameter.
        if nv:
            if not isinstance(nv[0], (list, tuple)):
                nv = [nv]
            for item in nv:
                modify_instance[item[0]] = item[1]

        # Code to change characteristics of modify_instance based on
        # sp parameter
        if sp == 1:
            modify_instance.classname = 'CIM_NoSuchClass'
        elif sp == 2:
            modify_instance.path.namespace = 'BadNamespace'
        elif sp == 3:
            modify_instance.path.classname = 'changedpathclassname'
        elif sp == 4:
            modify_instance.path.classname = 'CIM_NoSuchClass'
            modify_instance.classname = 'CIM_NoSuchClass'
        elif sp == 5:
            modify_instance.properties = NocaseDict()

        if not isinstance(exp_resp, six.string_types):
            conn.ModifyInstance(modify_instance, PropertyList=pl)

            rtn_instance = conn.GetInstance(modify_instance.path)
            if exp_resp:
                for p in rtn_instance:
                    assert rtn_instance[p] == modify_instance[p]
            else:
                for p in rtn_instance:
                    assert rtn_instance[p] == orig_instance[p]
        else:
            with pytest.raises(CIMError) as exec_info:
                conn.ModifyInstance(modify_instance, PropertyList=pl)
            exc = exec_info.value
            assert exc.status_code_name == exp_resp

    def test_modifyinstance_lite(self, conn_lite, tst_instances):
        # pylint: disable=no-self-use
        """Test that we reject createinstance when repolite set."""
        with pytest.raises(CIMError) as exec_info:
            conn_lite.ModifyInstance(tst_instances[0])
        exc = exec_info.value
        assert exc.status_code_name == 'CIM_ERR_NOT_SUPPORTED'

    @pytest.mark.parametrize(
        "ns", [None, 'root/blah'])
    def test_deleteinstance_lite(self, conn_lite, tst_instances, ns):
        # pylint: disable=no-self-use
        """
        Test delete instance by inserting instances into the repository
        and then deleting them. Deletes all instances that are CIM_Foo and
        subclasses
        """
        conn_lite.add_cimobjects(tst_instances, namespace=ns)

        inst_name_list = conn_lite.EnumerateInstanceNames('CIM_Foo', ns)

        for inst_name in inst_name_list:
            conn_lite.DeleteInstance(inst_name)

        for inst_name in inst_name_list:
            with pytest.raises(CIMError) as exec_info:
                conn_lite.DeleteInstance(inst_name)
            exc = exec_info.value
            assert(exc.status_code_name == 'CIM_ERR_NOT_FOUND')

    @pytest.mark.parametrize(
        "ns", [None, 'root/blah'])
    @pytest.mark.parametrize(
        "cln, key, exp_err", [
            # cln : Class name
            # key: Key for error tests where this is invalid key.
            # exp_err: if not None, CIMError as string for expected exception

            ['CIM_Foo', None, None],                   # valid class
            ['CIM_Foo_sub', None, None],               # valid subclass
            ['CIM_Foo', 'xxx', 'CIM_ERR_NOT_FOUND'],   # instance not found
            ['CIM_DoesNotExist', 'blah', 'CIM_ERR_INVALID_CLASS'],  # cl not fnd
            ['CIM_Foo', 'blah', 'CIM_ERR_INVALID_NAMESPACE'],  # ns not fnd
        ]
    )
    def test_deleteinstance(self, conn, tst_classes, tst_instances, ns,
                            cln, key, exp_err):
        # pylint: disable=no-self-use
        """
        Test delete instance by inserting instances into the repository
        and then deleting them. Deletes all instances that are in cln and
        subclasses.

        Error cases confirm that exp_err is received
        """
        conn.add_cimobjects(tst_classes, namespace=ns)
        conn.add_cimobjects(tst_instances, namespace=ns)

        if not exp_err:
            # Test deletes all instances for defined class
            inst_name_list = conn.EnumerateInstanceNames(cln, ns)
            for iname in inst_name_list:
                conn.DeleteInstance(iname)

            for iname in inst_name_list:
                with pytest.raises(CIMError) as exec_info:
                    conn.DeleteInstance(iname)
                exc = exec_info.value
                assert exc.status_code_name == 'CIM_ERR_NOT_FOUND'
        else:
            tst_ns = DEFAULT_NAMESPACE if ns is None else ns

            if exp_err == 'CIM_ERR_INVALID_NAMESPACE':
                tst_ns = 'BadNamespaceName'

            iname = CIMInstanceName(cln, keybindings={'InstanceID': key},
                                    namespace=tst_ns)
            with pytest.raises(CIMError) as exec_info:
                conn.DeleteInstance(iname)
            exc = exec_info.value
            assert exc.status_code_name == exp_err


class TestPullOperations(object):
    """
    Mock the open and pull operations
        ClassName, namespace=None,
        FilterQueryLanguage=None, FilterQuery=None,
        OperationTimeout=None, ContinueOnError=None,
        MaxObjectCount=None,
    """
    def test_openenumeratepaths(self, conn_lite, tst_instances):
        # pylint: disable=no-self-use
        """
            Test openenueratepaths where the open is the complete response
            and all parameters are default
        """
        conn_lite.add_cimobjects(tst_instances)
        result_tuple = conn_lite.OpenEnumerateInstancePaths('CIM_Foo')
        assert result_tuple.eos is True
        assert result_tuple.context is None
        tst_paths = [i.path for i in tst_instances
                     if i.classname == 'CIM_Foo']
        exp_ns = conn_lite.default_namespace
        for p in tst_paths:
            p.namespace = exp_ns
        tst_paths = [str(p) for p in tst_paths]
        rslt_paths = [str(i) for i in result_tuple.paths]
        assert rslt_paths == tst_paths

    @pytest.mark.parametrize(
        "ns", [None, 'root/blah'])
    @pytest.mark.parametrize(
        "moc", [None, 100])
    def test_openenumeratepaths1(self, conn_lite, tst_instances, ns, moc):
        # pylint: disable=no-self-use
        """
            Test openenueratepaths where the open is the complete response.
            This is achieved by setting the moc. value large
        """
        conn_lite.add_cimobjects(tst_instances, namespace=ns)
        result_tuple = conn_lite.OpenEnumerateInstancePaths('CIM_Foo', ns,
                                                            MaxObjectCount=moc)
        assert result_tuple.eos is True
        assert result_tuple.context is None

        tst_paths = [i.path for i in tst_instances
                     if i.classname == 'CIM_Foo']
        exp_ns = conn_lite.default_namespace if ns is None else ns
        for p in tst_paths:
            p.namespace = exp_ns
        tst_paths = [str(p) for p in tst_paths]
        rslt_paths = [str(i) for i in result_tuple.paths]
        assert rslt_paths == tst_paths

    @pytest.mark.parametrize(
        "ns", [None, 'root/blah'])
    # open max obj, pull max obj, expected objects on open, expected eos on
    # open, expected pull eos
    @pytest.mark.parametrize(
        "omoc, pmoc, exp_ortn, exp_ooc_eos", [
            [200, None, 2, True],  # return everything with open
            [0, 200, 0, False],  # return nothing with open; all with pull
            [1, 200, 1, False],  # return 1 with open; all with pull
        ]
    )
    def test_openenumeratepaths2(self, conn_lite, tst_instances, ns, omoc, pmoc,
                                 exp_ortn, exp_ooc_eos):
        # pylint: disable=no-self-use
        """
            Test openenueratepaths where the open may not be the complete
            response.
            This is a simplified sequence where either the open returns
            everything or the pull is executed and it returns everything not
            returned by the open.
            Tests whether initial response returns correct data and the
            pull returns everything else.
        """
        conn_lite.add_cimobjects(tst_instances, namespace=ns)

        # expected returns are only CIM_Foo instances
        exp_total_paths = [i.path for i in tst_instances
                           if i.classname == 'CIM_Foo']
        result_tuple = conn_lite.OpenEnumerateInstancePaths('CIM_Foo', ns,
                                                            MaxObjectCount=omoc)

        opn_rtn_len = len(result_tuple.paths)

        assert len(result_tuple.paths) == exp_ortn
        assert result_tuple.eos == exp_ooc_eos

        if result_tuple.eos:   # initial response complete
            assert result_tuple.context is None
        else:
            assert isinstance(result_tuple.context[0], six.string_types)
            assert isinstance(result_tuple.context[1], six.string_types)

        # open response incomplete, execute a pull
        if not result_tuple.eos:
            result_tuple = conn_lite.PullInstancePaths(result_tuple.context,
                                                       pmoc)
            assert len(result_tuple.paths) == len(exp_total_paths) - opn_rtn_len
            assert result_tuple.eos
            assert result_tuple.context is None

    @pytest.mark.parametrize(
        "ns", [None, 'root/blah'])
    @pytest.mark.parametrize(
        "omoc, pmoc, exp_ortn, exp_ooc_eos", [
            [200, None, 2, True],  # return everything with open
            [0, 200, 0, False],  # return nothing with open; all with pull
            [1, 200, 1, False],  # return 1 with open; others with pull
        ]
    )
    def test_openenumeratepaths3(self, conn_lite, tst_instances, ns, omoc, pmoc,
                                 exp_ortn, exp_ooc_eos):
        # pylint: disable=no-self-use
        """
        Test openenumeratepaths where we only test for totals at the end
        of the sequence
        """
        conn_lite.add_cimobjects(tst_instances, namespace=ns)
        # expected returns are only CIM_Foo instances
        exp_total_paths = [i.path for i in tst_instances
                           if i.classname == 'CIM_Foo']

        result_tuple = conn_lite.OpenEnumerateInstancePaths('CIM_Foo',
                                                            namespace=ns,
                                                            MaxObjectCount=omoc)
        paths = result_tuple.paths

        while not result_tuple.eos:
            result_tuple = conn_lite.PullInstancePaths(result_tuple.context,
                                                       pmoc)
            paths.extend(result_tuple.paths)

        assert len(paths) == len(exp_total_paths)
        # TODO fix common test for path equality
        # assert paths == exp_total_paths

    def test_openenumerateinstances(self, conn_lite, tst_instances):
        # pylint: disable=no-self-use
        """
            Test openenueratepaths where the open is the complete response
            and all parameters are default
        """
        conn_lite.add_cimobjects(tst_instances)
        result_tuple = conn_lite.OpenEnumerateInstances('CIM_Foo')
        assert result_tuple.eos is True
        assert result_tuple.context is None
        tst_insts = [i for i in tst_instances
                     if i.classname == 'CIM_Foo']
        exp_ns = conn_lite.default_namespace
        for p in tst_insts:
            p.path.namespace = exp_ns

        tst_paths = [str(i.path) for i in tst_insts]
        rslt_paths = [str(i.path) for i in result_tuple.instances]
        assert rslt_paths == tst_paths
        # TODO test actual instances

    @pytest.mark.parametrize(
        "ns", [None, 'root/blah'])
    @pytest.mark.parametrize(
        # src_inst: Source instance definitions (classname and name property
        # ro: Role
        # rc: ResultClass
        # exp_rslt: list of tuples where each tuple is class and key for inst
        "src_inst, ro, rc, exp_rslt", [
            [('TST_Person', 'Mike'), None, 'TST_Lineage',
             [('TST_Lineage', 'MikeSofi'),
              ('TST_Lineage', 'MikeGabi')]],

            [('TST_Person', 'Saara'), None, 'TST_Lineage',
             [('TST_Lineage', 'SaaraSofi'), ]],

            [('TST_Person', 'Saara'), None, 'TST_Lineage',
             'CIM_ERR_INVALID_NAMESPACE'],
        ]
    )
    def test_openreferenceinstancepaths(self, conn, ns, src_inst, ro, rc,
                                        exp_rslt, tst_assoc_mof):
        # pylint: disable=no-self-use,invalid-name
        """
            Test openenueratepaths where the open is the complete response
            and all parameters are default
        """
        conn.compile_mof_string(tst_assoc_mof, namespace=ns)

        source_inst_name = CIMInstanceName(src_inst[0],
                                           keybindings=dict(name=src_inst[1]),
                                           namespace=ns)

        if isinstance(exp_rslt, (list, tuple)):
            result_tuple = conn.OpenReferenceInstancePaths(source_inst_name,
                                                           ResultClass=rc,
                                                           Role=ro)

            assert result_tuple.eos is True
            assert result_tuple.context is None

            exp_ns = ns if ns else conn.default_namespace

            # build list of expected paths from exp_rslt
            exp_paths = []
            for exp in exp_rslt:
                exp_paths.append(CIMInstanceName(
                    exp[0],
                    keybindings=dict(InstanceID=exp[1]),
                    namespace=exp_ns,
                    host=conn.host))

            rslt_paths = result_tuple.paths

            assert equal_ciminstname_lists(rslt_paths, exp_paths)
        else:
            if exp_rslt == 'CIM_ERR_INVALID_NAMESPACE':
                source_inst_name.namespace = 'BadNamespaceName'

            with pytest.raises(CIMError) as exec_info:
                conn.OpenReferenceInstancePaths(source_inst_name,
                                                ResultClass=rc,
                                                Role=ro)
            exc = exec_info.value
            assert exc.status_code_name == exp_rslt

    @pytest.mark.parametrize(
        "ns", [None, 'root/blah'])
    @pytest.mark.parametrize(
        # src_inst: Source instance definition (classname and name property
        # ro: Role
        # ac: AssocClass
        # rc: ResultClass
        # rr: ResultRole
        # exp_rslt: list of tuples where each tuple is class and key for
        #           expected instance path returned or string if error
        #           response expected. String contains error code
        "src_inst, ro, ac, rc, rr, exp_rslt", [
            [('TST_Person', 'Mike'), 'parent', 'TST_Lineage', 'TST_Person',
             'child',
             [('TST_Person', 'Sofi'),
              ('TST_Person', 'Gabi')]],

            [('TST_Person', 'Mike'), None, 'TST_Lineage', 'TST_Person',
             'child',
             [('TST_Person', 'Sofi'),
              ('TST_Person', 'Gabi')]],

            [('TST_Person', 'Mike'), None, 'TST_Lineage', 'TST_Person',
             None,
             [('TST_Person', 'Sofi'),
              ('TST_Person', 'Gabi')]],

            [('TST_Person', 'Saara'), 'parent', 'TST_Lineage', 'TST_Person',
             'child', [('TST_Person', 'Sofi'), ]],

            [('TST_Person', 'Saara'), 'parent', 'TST_Lineage', 'TST_Person',
             'child', 'CIM_ERR_INVALID_NAMESPACE'],
        ]
    )
    def test_openassociatorinstancepaths(self, conn, ns, src_inst, ro, ac,
                                         rc, rr, exp_rslt, tst_assoc_mof):
        # pylint: disable=no-self-use,invalid-name
        """
            Test openenueratepaths where the open is the complete response
            and all parameters are default
        """
        conn.compile_mof_string(tst_assoc_mof, namespace=ns)

        source_inst_name = CIMInstanceName(src_inst[0],
                                           keybindings=dict(name=src_inst[1]),
                                           namespace=ns)

        if isinstance(exp_rslt, (list, tuple)):
            result_tuple = conn.OpenAssociatorInstancePaths(source_inst_name,
                                                            AssocClass=ac,
                                                            Role=ro,
                                                            ResultClass=rc,
                                                            ResultRole=rr)

            assert result_tuple.eos is True
            assert result_tuple.context is None

            exp_ns = ns if ns else conn.default_namespace

            # build list of expected paths from exp_rslt
            exp_paths = []
            for exp in exp_rslt:
                exp_paths.append(CIMInstanceName(
                    exp[0],
                    keybindings=dict(name=exp[1]),
                    namespace=exp_ns,
                    host=conn.host))

            rslt_paths = result_tuple.paths

            assert equal_ciminstname_lists(rslt_paths, exp_paths)

        else:
            if exp_rslt == 'CIM_ERR_INVALID_NAMESPACE':
                source_inst_name.namespace = 'BadNamespaceName'

            with pytest.raises(CIMError) as exec_info:
                conn.OpenAssociatorInstancePaths(source_inst_name,
                                                 AssocClass=ac,
                                                 Role=ro,
                                                 ResultClass=rc,
                                                 ResultRole=rr)
            exc = exec_info.value
            assert exc.status_code_name == exp_rslt

    @pytest.mark.parametrize(
        "ns", [None, 'root/blah'])
    @pytest.mark.parametrize(
        # src_inst: Source instance definition (classname and name property
        # ro: Role
        # ac: AssocClass
        # rc: ResultClass
        # rr: ResultRole
        # exp_rslt: list of tuples where each tuple is class and key for
        #           expected instance path returned or string if error
        #           response expected. String contains error code
        "src_inst, ro, ac, rc, rr, exp_rslt", [
            [('TST_Person', 'Mike'), 'parent', 'TST_Lineage', 'TST_Person',
             'child',
             [('TST_Person', 'Sofi'),
              ('TST_Person', 'Gabi')]],

            [('TST_Person', 'Mike'), None, 'TST_Lineage', 'TST_Person',
             'child',
             [('TST_Person', 'Sofi'),
              ('TST_Person', 'Gabi')]],

            [('TST_Person', 'Mike'), None, 'TST_Lineage', 'TST_Person',
             None,
             [('TST_Person', 'Sofi'),
              ('TST_Person', 'Gabi')]],

            [('TST_Person', 'Saara'), 'parent', 'TST_Lineage', 'TST_Person',
             'child', [('TST_Person', 'Sofi'), ]],

            [('TST_Person', 'Saara'), 'parent', 'TST_Lineage', 'TST_Person',
             'child', 'CIM_ERR_INVALID_NAMESPACE'],
        ]
    )
    def test_openassociatorinstances(self, conn, ns, src_inst, ro, ac,
                                     rc, rr, exp_rslt, tst_assoc_mof):
        # pylint: disable=no-self-use,invalid-name
        """
            Test openenueratepaths where the open is the complete response
            and all parameters are default
        """
        conn.compile_mof_string(tst_assoc_mof, namespace=ns)

        source_inst_name = CIMInstanceName(src_inst[0],
                                           keybindings=dict(name=src_inst[1]),
                                           namespace=ns)

        if isinstance(exp_rslt, (list, tuple)):
            result_tuple = conn.OpenAssociatorInstances(source_inst_name,
                                                        AssocClass=ac,
                                                        Role=ro,
                                                        ResultClass=rc,
                                                        ResultRole=rr)

            assert result_tuple.eos is True
            assert result_tuple.context is None

            exp_ns = ns if ns else conn.default_namespace

            # build list of expected paths from exp_rslt
            exp_paths = []
            for exp in exp_rslt:
                exp_paths.append(CIMInstanceName(
                    exp[0],
                    keybindings=dict(name=exp[1]),
                    namespace=exp_ns))

            rslt_paths = [inst.path for inst in result_tuple.instances]

            assert equal_ciminstname_lists(rslt_paths, exp_paths)
            # TODO test instances returned rather than just paths and
            # test for propertylist specifically

        else:
            if exp_rslt == 'CIM_ERR_INVALID_NAMESPACE':
                source_inst_name.namespace = 'BadNamespaceName'

            with pytest.raises(CIMError) as exec_info:
                conn.OpenAssociatorInstances(source_inst_name,
                                             AssocClass=ac,
                                             Role=ro,
                                             ResultClass=rc,
                                             ResultRole=rr)
            exc = exec_info.value
            assert exc.status_code_name == exp_rslt

    @pytest.mark.parametrize(
        "ns", [None, 'root/blah'])
    @pytest.mark.parametrize(
        "test, cln, omoc, pmoc, exp_err", [

            # Test closing after open with moc
            [0, 'CIM_Foo', 0, 1, None],

            # Execute close after sequence conplete
            [1, 'CIM_Foo', 100, 100, 'Value Not Used'],

            # Execute close with valid context but after sequence complete
            [2, 'CIM_Foo', 0, 100, 'CIM_ERR_INVALID_ENUMERATION_CONTEXT'],
            # TODO FUTURE: test with timer
        ]
    )
    def test_closeenumeration(self, conn, ns, test, cln, omoc, pmoc,
                              exp_err, tst_classes, tst_instances):
        # pylint: disable=no-self-use
        """
        Test variations on closing enumerate the enumeration context with
        the CloseEnumeration operation.  Tests both valid and invalid
        calls.
        """
        conn.add_cimobjects(tst_classes, namespace=ns)
        conn.add_cimobjects(tst_instances, namespace=ns)

        result_tuple = conn.OpenEnumerateInstancePaths(
            cln, namespace=ns, MaxObjectCount=omoc)

        if test == 0:
            assert result_tuple.eos is False
            assert result_tuple.context is not None
            conn.CloseEnumeration(result_tuple.context)

        elif test == 1:
            while not result_tuple.eos:
                result_tuple = conn.PullInstancePaths(
                    result_tuple.context, MaxObjectCount=pmoc)
            assert result_tuple.eos is True
            assert result_tuple.context is None
            with pytest.raises(ValueError) as exec_info:
                conn.CloseEnumeration(result_tuple.context)

        elif test == 2:
            save_result_tuple = pull_path_result_tuple(*result_tuple)

            while not result_tuple.eos:
                result_tuple = conn.PullInstancePaths(
                    result_tuple.context, MaxObjectCount=pmoc)
            assert result_tuple.eos is True
            assert result_tuple.context is None
            with pytest.raises(CIMError) as exec_info:
                assert save_result_tuple.context is not None
                conn.CloseEnumeration(save_result_tuple.context)
            exc = exec_info.value
            assert exc.status_code_name == exp_err
        else:
            assert False, 'Invalid test code %s' % test


class TestQualifierOperations(object):
    """
    Tests the qualifier set, enumerate, get and delete operations.
    Note this is really QualifierDeclarations
    """
    @staticmethod
    def _build_qualifiers():
        """
        Static method to build test qualifier declarations. Builds
        2 valid declarations and returns list
        """
        q1 = CIMQualifierDeclaration('FooQualDecl1', 'uint32')

        q2 = CIMQualifierDeclaration('FooQualDecl2', 'string',
                                     value='my string')
        return [q1, q2]

    @pytest.mark.parametrize(
        "ns", [None, 'root/blah'])
    @pytest.mark.parametrize(
        "qname, exp_err", [
            ['FooQualDecl1', None],
            ['badqualname', 'CIM_ERR_NOT_FOUND'],
            ['whatever', 'CIM_ERR_INVALID_NAMESPACE'],
        ]
    )
    def test_getqualifier(self, conn, ns, qname, exp_err):
        """
        Test adding a qualifierdecl to the repository and doing a
        WBEMConnection get to retrieve it.
        """
        q_list = self._build_qualifiers()
        conn.add_cimobjects(q_list, namespace=ns)

        if not exp_err:
            rtn_q1 = conn.GetQualifier(qname, namespace=ns)
            assert rtn_q1.name == qname

        else:
            if exp_err == 'CIM_ERR_INVALID_NAMESPACE':
                ns = 'badnamespace'

            with pytest.raises(CIMError) as exec_info:
                conn.GetQualifier(qname, namespace=ns)
            exc = exec_info.value
            assert exc.status_code_name == exp_err

    @pytest.mark.parametrize(
        "ns", [None, 'root/blah'])
    @pytest.mark.parametrize(
        "exp_err", [None, 'CIM_ERR_INVALID_NAMESPACE'])
    def test_enumeratequalifiers(self, conn, ns, exp_err):
        """
        Test adding a qualifierdecl to the repository and doing a
        WBEMConnection get to retrieve it.
        """
        q_list = self._build_qualifiers()

        conn.add_cimobjects(q_list, namespace=ns)

        if not exp_err:
            q_rtn = conn.EnumerateQualifiers(namespace=ns)
            for q in q_rtn:
                assert(isinstance(q, CIMQualifierDeclaration))

            q_list.sort(key=lambda x: x.name)
            q_rtn.sort(key=lambda x: x.name)
            assert(q_list == q_rtn)

        else:
            if exp_err == 'CIM_ERR_INVALID_NAMESPACE':
                ns = 'badnamespace'

            with pytest.raises(CIMError) as exec_info:
                conn.EnumerateQualifiers(namespace=ns)
            exc = exec_info.value
            assert exc.status_code_name == exp_err

    @pytest.mark.parametrize(
        "ns", [None, 'root/blah'])
    @pytest.mark.parametrize(
        "qual, exp_err", [
            [CIMQualifierDeclaration('FooQualDecl3', 'string',
                                     value='my string'), None],
            # Invalid definition for qualifierdeclaration
            [CIMClass('FooQualDecl3'), 'CIM_ERR_INVALID_PARAMETER'],
        ]
    )
    def test_setqualifier(self, conn, ns, qual, exp_err):
        # pylint: disable=no-self-use
        """
            Test create class. Tests for namespace variable,
            correctly adding, and invalid add where class has superclass
        """

        if not exp_err:
            conn.SetQualifier(qual, namespace=ns)

            rtn_qualifier = conn.GetQualifier(qual.name, namespace=ns)

            assert rtn_qualifier == qual

            # Test for already exists.
            with pytest.raises(CIMError) as exec_info:
                conn.SetQualifier(qual, namespace=ns)
            exc = exec_info.value
            assert(exc.status_code_name == 'CIM_ERR_ALREADY_EXISTS')

        else:
            if exp_err == 'CIM_ERR_INVALID_NAMESPACE':
                ns = 'badnamespace'

            with pytest.raises(CIMError) as exec_info:
                conn.SetQualifier(qual, namespace=ns)
            exc = exec_info.value
            assert exc.status_code_name == exp_err

    @pytest.mark.parametrize(
        "ns", [None, 'root/blah'])
    @pytest.mark.parametrize(
        "qname, exp_err", [
            ['FooQualDecl1', None],
            ['badqualname', 'CIM_ERR_NOT_FOUND'],
            ['whatever', 'CIM_ERR_INVALID_NAMESPACE'],
        ]
    )
    def test_deletequalifier(self, conn, ns, qname, exp_err):
        """
        Test  fake delete of qualifier declaration method. Adds qualifier
        declarations to repository and then deletes qualifier defined
        by qname. Tries to delete again and this should fail as not found.
        """
        q_list = self._build_qualifiers()
        conn.add_cimobjects(q_list, namespace=ns)

        if not exp_err:
            conn.DeleteQualifier('FooQualDecl2', namespace=ns)

            with pytest.raises(CIMError) as exec_info:
                conn.DeleteQualifier('QualDoesNotExist', namespace=ns)
            exc = exec_info.value
            assert(exc.status_code_name == 'CIM_ERR_NOT_FOUND')
        else:
            if exp_err == 'CIM_ERR_INVALID_NAMESPACE':
                ns = 'badnamespace'

            with pytest.raises(CIMError) as exec_info:
                conn.GetQualifier(qname, namespace=ns)
            exc = exec_info.value
            assert exc.status_code_name == exp_err


class TestReferenceOperations(object):
    """
    Tests of References class and instance operations
    """
    @pytest.mark.parametrize(
        "ns", [None, 'root/blah'])
    def test_association_classes(self, conn, ns, tst_assoc_mof):
        # pylint: disable=no-self-use
        """
        Test the method that filters classes to association classes
        """
        if ns is None:
            ns = conn.default_namespace
        conn.compile_mof_string(tst_assoc_mof, namespace=ns)

        # pylint: disable=protected-access
        clns = [cl.classname for cl in conn._get_association_classes(ns)]

        assert set(clns) == set([u'TST_Lineage',
                                 u'TST_MemberOfFamilyCollection'])

    @pytest.mark.parametrize(
        "ns", [None, 'root/blah'])
    @pytest.mark.parametrize(
        "cln", ['TST_Person', CIMClassName('TST_Person')])
    @pytest.mark.parametrize(
        # rc: ResultClass
        # ro: Role
        # exp_rslt: list of associator classnames that should be returned if
        #   good result expected.  String containing CIMError code if error
        #   return expected.  Currently we do not have any errors tested.
        "rc, ro, exp_rslt", [
            [None, None, ['TST_Lineage', 'TST_MemberOfFamilyCollection']],
            ['TST_Lineage', None, ['TST_Lineage']],
            ['TST_Lineage', 'parent', ['TST_Lineage']],
            ['TST_Lineage', 'child', ['TST_Lineage']],
            ['TST_Lineage', 'CHILD', ['TST_Lineage']],
            [None, 'parent', ['TST_Lineage']],
            [None, 'child', ['TST_Lineage']],
            [None, 'blah', []],
            ['TST_MemberOfFamilyCollection', None,
             ['TST_MemberOfFamilyCollection']],
            ['TST_MemberOfFamilyCollection', 'member',
             ['TST_MemberOfFamilyCollection']],
            ['TST_MemberOfFamilyCollection', 'family',
             ['TST_MemberOfFamilyCollection']],
            [None, 'member', ['TST_MemberOfFamilyCollection']],
            [None, 'family', ['TST_MemberOfFamilyCollection']],
            ['TST_BLAH', None, []],
            [None, None, 'CIM_ERR_INVALID_NAMESPACE'],
        ]
    )
    def test_reference_classnames(self, conn, ns, cln, tst_assoc_mof, rc, ro,
                                  exp_rslt):
        # pylint: disable=no-self-use
        """
        Test getting reference classnames with no options on call and default
        namespace. Tests for both string and CIMClassName input
        """
        conn.compile_mof_string(tst_assoc_mof, namespace=ns)

        # account for api where string classname only allowed with default
        # classname
        if ns is not None:
            if isinstance(cln, six.string_types):
                cim_cln = CIMClassName(classname=cln, namespace=ns)
            else:
                cim_cln = cln.copy()
                cim_cln.namespace = ns
        else:
            cim_cln = cln

        if isinstance(exp_rslt, list):    # if list exp OK result
            clns = conn.ReferenceNames(cim_cln, ResultClass=rc, Role=ro)

            assert isinstance(clns, list)
            assert len(clns) == len(exp_rslt)
            exp_ns = ns if ns else conn.default_namespace
            exp_clns = [CIMClassName(classname=n, namespace=exp_ns,
                                     host=conn.host)
                        for n in exp_rslt]

            # sort the expected and result by classname
            exp_clns.sort(key=operator.attrgetter('classname'))
            clns.sort(key=operator.attrgetter('classname'))

            assert clns == exp_clns
        else:  # exp_rslt is a CIMError code in str format

            # we have to fix the targetclassname for some of the tests
            if isinstance(cim_cln, six.string_types):
                cim_cln = CIMInstanceName(classname=cln)
            if exp_rslt == 'CIM_ERR_INVALID_NAMESPACE':
                cim_cln.namespace = 'non_existent_namespace'

            with pytest.raises(CIMError) as exec_info:
                # pylint: disable=protected-access
                conn.ReferenceNames(cim_cln, ResultClass=rc, Role=ro)
            exc = exec_info.value
            assert exc.status_code_name == exp_rslt

    def test_reference_instnames_min(self, conn, tst_assoc_mof):
        # pylint: disable=no-self-use
        """
        Test getting reference instnames with no options
        """
        conn.compile_mof_string(tst_assoc_mof)

        inst_name = CIMInstanceName('TST_Person',
                                    keybindings=dict(name='Mike'))
        inames = conn.ReferenceNames(inst_name)
        assert isinstance(inames, list)
        assert len(inames) == 3
        assert isinstance(inames[0], CIMInstanceName)
        assert inames[0].classname == 'TST_Lineage'

    @pytest.mark.parametrize(
        "ns", [None, 'root/blah'])
    @pytest.mark.parametrize(  # Don't really need this since rslts tied to cl.
        # target instance classname and key
        "tcln, key", [
            ['TST_Person', 'Mike'],
        ]
    )
    @pytest.mark.parametrize(
        # rc: ResultClass
        # ro: Role
        # exp_rslt: list of associator class/key tuples that should be returned
        #    if good result expected.  String containing CIMError code if error
        #   return expected.  Currently we do not have any errors tested.
        "rc, ro, exp_rslt", [
            # [None, None, ('TST_Lineage')],
            ['TST_Lineage', None, (('TST_Lineage', 'MikeSofi'),
                                   ('TST_Lineage', 'MikeGabi'),)],
            ['TST_Lineage', 'parent', (('TST_Lineage', 'MikeSofi'),
                                       ('TST_Lineage', 'MikeGabi'),)],
            ['TST_Lineage', 'child', (('TST_Lineage', 'MikeSofi'),
                                      ('TST_Lineage', 'MikeGabi'),)],
            ['TST_Lineage', 'CHILD', (('TST_Lineage', 'MikeSofi'),
                                      ('TST_Lineage', 'MikeGabi'),)],
            # TODO expand test exp_rslt definition. Need to be able to
            # express keys for TST_Memberof FamilyCollection since it has
            # 2 keys. Did in another test and need to copy
            # [None, 'parent', (('TST_Lineage', 'MikeSofi'),
            #                          ('TST_Lineage', 'MikeGabi'),
            #                         ('TST_MemberOfFamilyCollection', TODO ))],
            # [None, 'child', ['TST_Lineage']],
            # [None, 'blah', []],
            # ['TST_MemberOfFamilyCollection', None,
            #  [('TST_MemberOfFamilyCollection', 'blah'), None]],
            # ['TST_MemberOfFamilyCollection', 'member',
            #  ['TST_MemberOfFamilyCollection']],
            # ['TST_MemberOfFamilyCollection', 'family',
            # ['TST_MemberOfFamilyCollection']],
            # [None, 'member', ['TST_MemberOfFamilyCollection']],
            # [None, 'family', ['TST_MemberOfFamilyCollection']],
            ['TST_BLAH', None, []],
            [None, None, 'CIM_ERR_INVALID_NAMESPACE'],
            # TODO enable the above tests
        ]
    )
    def test_reference_instnames_ns(self, conn, ns, tcln, key, rc, ro, exp_rslt,
                                    tst_assoc_mof):
        # pylint: disable=no-self-use
        """
        Test getting reference classnames
        """
        conn.compile_mof_string(tst_assoc_mof, namespace=ns)

        targ_iname = CIMInstanceName(tcln, keybindings=dict(name=key),
                                     namespace=ns)

        if isinstance(exp_rslt, (list, tuple)):
            exp_inames = []
            for itup in exp_rslt:
                kb = dict(InstanceID=itup[1])
                exp_ns = ns if ns else conn.default_namespace
                exp_inames.append(CIMInstanceName(itup[0], kb, namespace=exp_ns,
                                                  host=conn.host))

            inames = conn.ReferenceNames(targ_iname, ResultClass=rc, role=ro)

            assert isinstance(inames, list)

            # TODO redo this as a clean compare test
            assert len(inames) == len(exp_rslt)
            for iname in inames:
                assert isinstance(iname, CIMInstanceName)
                assert iname in exp_inames

        else:  # exp_rslt is a CIMError code in str format

            if exp_rslt == 'CIM_ERR_INVALID_NAMESPACE':
                targ_iname.namespace = 'non_existent_namespace'

            with pytest.raises(CIMError) as exec_info:
                # pylint: disable=protected-access
                conn.ReferenceNames(targ_iname, ResultClass=rc, Role=ro)
            exc = exec_info.value
            assert exc.status_code_name == exp_rslt

    # TODO not sure we really need this testcase? Combine with next case
    # The only thing special about this test is it sets all parameters to
    # default
    def test_reference_instances_min(self, conn, tst_assoc_mof):
        # pylint: disable=no-self-use
        """
        Test getting reference instances from default namespace with
        detault parameters
        """
        conn.compile_mof_string(tst_assoc_mof)

        inst_name = CIMInstanceName('TST_Person',
                                    keybindings=dict(name='Mike'))

        insts = conn.References(inst_name)

        assert isinstance(insts, list)
        assert len(insts) == 3
        assert isinstance(insts[0], CIMInstance)
        assert insts[0].classname == 'TST_Lineage'
        # TODO test for specific instance.

    @pytest.mark.parametrize(
        "ns", [None, 'root/blah'])
    @pytest.mark.parametrize(
        "rc, role, exp_rtn", [
            # rc: ResultClass parameter
            # role: Role parameter
            # exp_rtn: tuple of classname and tuple of keys
            # in expected return CIMInstanceNames. Used to build expected
            # return keys.
            [None, None, (('TST_Lineage', ('InstanceID', 'MikeGabi')),
                          ('TST_Lineage', ('InstanceID', 'MikeSofi')),
                          ('TST_MemberOfFamilyCollection', (
                              ('TST_FamilyCollection', 'family', 'name',
                               "Family2"),
                              ('TST_Person', 'member', 'name', 'Mike'))))],

            ['TST_Lineage', None, (('TST_Lineage', ('InstanceID', 'MikeGabi')),
                                   ('TST_Lineage',
                                    ('InstanceID', 'MikeSofi')))],
            [None, 'parent', (('TST_Lineage', ('InstanceID', 'MikeGabi')),
                              ('TST_Lineage', ('InstanceID', 'MikeSofi')))],
            ['TST_Lineage', 'parent', (('TST_Lineage',
                                        ('InstanceID', 'MikeGabi')),
                                       ('TST_Lineage',
                                        ('InstanceID', 'MikeSofi')))],
            [None, 'friend', []],
        ]
    )
    def test_reference_instances_opts(self, conn, ns, rc, role, exp_rtn,
                                      tst_assoc_mof):
        # pylint: disable=no-self-use
        """
        Test getting reference instance names with rc and role options.
        """
        conn.compile_mof_string(tst_assoc_mof, namespace=ns)

        inst_name = CIMInstanceName('TST_Person',
                                    keybindings=dict(name='Mike'),
                                    namespace=ns)

        insts = conn.References(inst_name, ResultClass=rc, Role=role)

        paths = [i.path for i in insts]

        assert isinstance(insts, list)
        assert len(insts) == len(exp_rtn)
        for inst in insts:
            assert isinstance(inst, CIMInstance)

        exp_ns = conn.default_namespace if ns is None else ns

        # create the expected paths from exp_rtn fixture.
        exp_paths = []
        for exp_path in exp_rtn:
            kbs = OrderedDict()
            kys = exp_path[1]
            if not isinstance(kys[0], (tuple, list)):
                kys = [ kys ]  # noqa E201, E202 pylint: disable=bad-whitespace
            for ky in kys:
                if len(ky) == 2:   # simple instance path, 3 values
                    kbs[ky[0]] = ky[1]
                else:
                    assert len(ky) == 4
                    kbs[ky[1]] = CIMInstanceName(ky[0], namespace=exp_ns,
                                                 keybindings={ky[2]: ky[3]})
            path = CIMInstanceName(exp_path[0], namespace=exp_ns,
                                   keybindings=kbs, host=conn.host)
            exp_paths.append(path)

        assert set(paths) == set(exp_paths)

    # TODO test for references propertylist.


class TestAssociationOperations(object):
    """
    Tests of References class and instance operations
    """

    @pytest.mark.parametrize(
        "ns", [None, 'root/blah'])
    @pytest.mark.parametrize(
        "target_cln", ['TST_Person'])
    @pytest.mark.parametrize(
        "role, ac, rr, rc, exp_rslt", [
            # role: role attribute
            # ac: associated class attribute
            # rr: resultrole attribute
            # rc: resultclass attribute
            # exp_result: Either list of names of expected classes returned
            #             or string defining error response
            # TODO: ks Review all these tests and results. I am uncomfortable
            #       with results.
            [None, None, None, None, ['TST_Person']],
            [None, 'TST_Lineage', None, None, ['TST_Person']],
            ['Parent', 'TST_Lineage', None, None, ['TST_Person']],
            ['parent', 'TST_Lineage', None, None, ['TST_Person']],
            ['Parent', 'TST_Lineage', 'child', 'TST_Person', ['TST_Person']],
            ['parent', 'TST_Lineage', 'Child', 'TST_Person', ['TST_Person']],
            ['PARENT', 'TST_Lineage', 'CHILD', 'TST_Person', ['TST_Person']],
            [None, None, 'child', 'TST_Person', ['TST_Person']],
            ['Parent', 'TST_Lineage', 'child', 'TST_Person',
             'CIM_ERR_INVALID_NAMESPACE'],
        ]
    )
    def test_associator_classnames(self, conn, ns, target_cln, role, rr, ac, rc,
                                   exp_rslt, tst_assoc_mof):
        # pylint: disable=no-self-use
        """
        Test getting reference classnames with no options on call and default
        namespace. Tests for both string and CIMClassName input
        """
        conn.compile_mof_string(tst_assoc_mof, namespace=ns)

        if ns is not None:
            target_cln = CIMClassName(target_cln, namespace=ns)

        if isinstance(exp_rslt, (list, tuple)):

            rtn_clns = conn.AssociatorNames(target_cln, AssocClass=ac,
                                            Role=role,
                                            ResultRole=rr, ResultClass=rc)
            assert isinstance(rtn_clns, list)
            assert len(rtn_clns) == len(exp_rslt)
            for cln in rtn_clns:
                assert isinstance(cln, CIMClassName)

            assert set([cln.classname for cln in rtn_clns]) == set(exp_rslt)

        else:
            # Set up test for invalid namespace exception
            if exp_rslt == 'CIM_ERR_INVALID_NAMESPACE':
                if isinstance(target_cln, six.string_types):
                    target_cln = CIMClassName(target_cln,
                                              namespace='badnamespacename')
                else:
                    target_cln.namespace = 'badnamespacename'

            with pytest.raises(CIMError) as exec_info:
                # pylint: disable=protected-access
                conn.AssociatorNames(target_cln, AssocClass=ac, Role=role,
                                     ResultRole=rr, ResultClass=rc)
            exc = exec_info.value
            assert exc.status_code_name == exp_rslt

    @pytest.mark.parametrize(
        "ns", [None, 'root/blah'])
    @pytest.mark.parametrize(
        "cln, inst_id", [
            ['TST_Person', 'Mike'],
        ]
    )
    @pytest.mark.parametrize(
        "role, ac, rr, rc, exp_rslt", [
            # role: associator role parameter
            # ac: associator operation AssocClass parameter
            # rr: associator operation ResultRole parameter
            # rc: associator operation ResultClass parameter
            # exp_rslt: Expected result.  If list, list of instances in response
            #           If string, expected error code

            # Test for assigned role and assoc class
            ['parent', 'TST_Lineage', None, None, (('TST_person', 'Sofi'),
                                                   ('TST_person', 'Gabi'),)],
            # Test for assigned role, asoc class, result role, resultclass
            ['parent', 'TST_Lineage', 'child', 'TST_Person',
             (('TST_person', 'Sofi'), ('TST_person', 'Gabi'),)],
            # Execute invalid namespace test
            ['parent', 'TST_Lineage', 'child', 'TST_Person',
             'CIM_ERR_INVALID_NAMESPACE'],
            # TODO add more tests
        ]
    )
    def test_associator_instnames(self, conn, ns, cln, inst_id, role, rr, ac,
                                  rc, exp_rslt, tst_assoc_mof):
        # pylint: disable=no-self-use
        """
        Test getting associators with parameters for the response filters
        including role, etc.
        TODO add tests for IncludeQualifiers, PropertyList, IncludeClassOrigin
        """
        conn.compile_mof_string(tst_assoc_mof, namespace=ns)

        exp_ns = conn.default_namespace if ns is None else ns

        inst_name = CIMInstanceName(cln, namespace=exp_ns,
                                    keybindings=dict(name=inst_id))

        if isinstance(exp_rslt, (tuple, list)):
            rpaths = conn.AssociatorNames(inst_name, AssocClass=ac, Role=role,
                                          ResultRole=rr, ResultClass=rc)

            assert isinstance(rpaths, list)
            assert len(rpaths) == len(exp_rslt)
            for path in rpaths:
                assert isinstance(path, CIMInstanceName)

            if isinstance(exp_rslt, (list, tuple)):

                exp_paths = [CIMInstanceName(p[0], keybindings={'name': p[1]},
                                             namespace=exp_ns, host=conn.host)
                             for p in exp_rslt]
                assert equal_ciminstname_lists(rpaths, exp_paths)

        else:
            assert isinstance(exp_rslt, six.string_types)

            if exp_rslt == 'CIM_ERR_INVALID_NAMESPACE':
                inst_name.namespace = 'BadNameSpaceName'

            with pytest.raises(CIMError) as exec_info:
                # pylint: disable=protected-access
                conn.AssociatorNames(inst_name, AssocClass=ac, Role=role,
                                     ResultRole=rr, ResultClass=rc)
            exc = exec_info.value
            assert exc.status_code_name == exp_rslt

        # TODO expand associator instance names tests

    @pytest.mark.parametrize(
        "ns", [None, 'root/blah'])
    @pytest.mark.parametrize(
        "cln, inst_id", [
            ['TST_Person', 'Mike'],
        ]
    )
    @pytest.mark.parametrize(
        "role, ac, rr, rc, exp_rslt", [
            # role: associator role parameter
            # ac: associator operation AssocClass parameter
            # rr: associator operation ResultRole parameter
            # rc: associator operation ResultClass parameter
            # exp_rslt: Expected result.  If list, list of instances in response
            #           If string, expected error code

            # Test for assigned role and assoc class
            ['parent', 'TST_Lineage', None, None, (('TST_person', 'Sofi'),
                                                   ('TST_person', 'Gabi'),)],
            # Test for assigned role, asoc class, result role, resultclass
            ['parent', 'TST_Lineage', 'child', 'TST_Person',
             (('TST_person', 'Sofi'), ('TST_person', 'Gabi'),)],
            # Execute invalid namespace test
            ['parent', 'TST_Lineage', 'child', 'TST_Person',
             'CIM_ERR_INVALID_NAMESPACE'],
            # TODO add more tests
        ]
    )
    def test_associator_instances(self, conn, ns, cln, inst_id, role, rr, ac,
                                  rc, exp_rslt, tst_assoc_mof):
        # pylint: disable=no-self-use
        """
        Test getting associators with parameters for the response filters
        including role, etc.
        TODO add tests for IncludeQualifiers, PropertyList, IncludeClassOrigin
        """
        conn.compile_mof_string(tst_assoc_mof, namespace=ns)

        exp_ns = conn.default_namespace if ns is None else ns

        inst_name = CIMInstanceName(cln, namespace=exp_ns,
                                    keybindings=dict(name=inst_id))

        if isinstance(exp_rslt, (tuple, list)):
            rtn_insts = conn.Associators(inst_name, AssocClass=ac, Role=role,
                                         ResultRole=rr, ResultClass=rc)

            assert isinstance(rtn_insts, list)
            assert len(rtn_insts) == len(exp_rslt)
            for inst in rtn_insts:
                assert isinstance(inst, CIMInstance)

            if isinstance(exp_rslt, (list, tuple)):

                exp_paths = [CIMInstanceName(p[0], keybindings={'name': p[1]},
                                             namespace=exp_ns)
                             for p in exp_rslt]
                rtn_paths = [inst.path for inst in rtn_insts]

                assert equal_ciminstname_lists(rtn_paths, exp_paths)

        else:
            assert isinstance(exp_rslt, six.string_types)

            if exp_rslt == 'CIM_ERR_INVALID_NAMESPACE':
                inst_name.namespace = 'BadNameSpaceName'

            with pytest.raises(CIMError) as exec_info:
                # pylint: disable=protected-access
                conn.Associators(inst_name, AssocClass=ac, Role=role,
                                 ResultRole=rr, ResultClass=rc)
            exc = exec_info.value
            assert exc.status_code_name == exp_rslt

        # TODO expand associator instance tests

    @pytest.mark.parametrize(
        "ns", [None, 'root/blah'])
    @pytest.mark.parametrize(
        "cln", ['TST_Person'])
    @pytest.mark.parametrize(
        "role, ac, rr, rc, exp_rslt", [
            # role: associator role parameter
            # ac: associator operation AssocClass parameter
            # rr: associator operation ResultRole parameter
            # rc: associator operation ResultClass parameter
            # exp_result: Either list of names of expected classes returned
            # or string defining error response
            # TODO: Review this and its results. I am uncomfortable I have not
            #       covered all the essentials
            [None, None, None, None, ['TST_Person']],
            [None, 'TST_Lineage', None, None, ['TST_Person']],
            ['Parent', 'TST_Lineage', None, None, ['TST_Person']],
            ['parent', 'TST_Lineage', None, None, ['TST_Person']],
            ['Parent', 'TST_Lineage', 'child', 'TST_Person', ['TST_Person']],
            ['parent', 'TST_Lineage', 'Child', 'TST_Person', ['TST_Person']],
            ['PARENT', 'TST_Lineage', 'CHILD', 'TST_Person', ['TST_Person']],
            [None, None, 'child', 'TST_Person', ['TST_Person']],
            ['Parent', 'TST_Lineage', 'child', 'TST_Person',
             'CIM_ERR_INVALID_NAMESPACE'],
        ]
    )
    def test_associator_classes(self, conn, ns, cln, role, rr, ac, rc,
                                exp_rslt, tst_assoc_mof):
        # pylint: disable=no-self-use
        """
        Test getting reference classnames with no options on call and default
        namespace. Tests for both string and CIMClassName input
        """

        # TODO test error.  Failed if rc was TST_PERSON
        conn.compile_mof_string(tst_assoc_mof, namespace=ns)

        if ns is not None:
            cln = CIMClassName(cln, namespace=ns)

        if isinstance(exp_rslt, (list, tuple)):
            results = conn.Associators(cln, AssocClass=ac, Role=role,
                                       ResultRole=rr, ResultClass=rc)

            assert isinstance(results, list)
            assert len(results) == len(exp_rslt)
            for result in results:
                assert isinstance(result, tuple)
                assert isinstance(result[0], CIMClassName)
                assert isinstance(result[1], CIMClass)

            clns = [result[0].classname for result in results]
            assert set(clns) == set(exp_rslt)

        else:
            assert isinstance(exp_rslt, six.string_types)
            if exp_rslt == 'CIM_ERR_INVALID_NAMESPACE':
                if isinstance(cln, six.string_types):
                    cln = CIMClassName(cln, namespace='badnamespacename')
                else:
                    cln.namespace = 'badnamespacename'
            with pytest.raises(CIMError) as exec_info:
                # pylint: disable=protected-access
                conn.Associators(cln, AssocClass=ac, Role=role,
                                 ResultRole=rr, ResultClass=rc)
            exc = exec_info.value
            assert exc.status_code_name == exp_rslt

        # TODO expand associator classes test to test for correct properties
        # in response


class TestInvokeMethod(object):
    """
    Test invoking extrinsic methods in Fake_WBEMConnection
    """
    def method1_callback(self, conn, methodname, object_name, **params):
        # pylint: disable=unused-argument, invalid-name
        """
        Callback for InvokeMethod with method name method1. This callback is
        defined by a add_method_callback method call in the test method.

        This method tests for valid object_name type, methodname and returns
        the return value and params defined by instance attributes of the
        TestInvokeMethod class.

        In validates the conn is valid acces to repo by executing repo call
        for the object_name.
        """
        # pylint: disable=attribute-defined-outside-init
        self.executed_method = 'Method1'

        assert params == self.exp_input_params

        # Test for valid conn by accessing repository for object defined by
        # object_name. This test should never happen since already
        # tested in _fake_invokemethod
        if isinstance(object_name, CIMClassName):
            cc = conn.GetClass(object_name)
            assert cc.classname == object_name.classname

        elif isinstance(object_name, CIMInstanceName):
            inst = conn.GetInstance(object_name)
            assert inst.classname == object_name.classname
        else:
            raise CIMError(CIM_ERR_FAILED,
                           'Callback Method1 failed because input object_name '
                           '%s invalid type %s' %
                           (object_name, type(object_name)))

        assert object_name.namespace == self.test_namespace

        return (self.return_value, self.return_params)

    def method2_callback(self, conn, methodname, object_name, **params):
        # pylint: disable=unused-argument, invalid-name
        """
        InvokeMethod callback.  This is a smiple callback that just tests
        methodname and then returns returnvalue and params from the
        TestInvokeMethod object attributes.  It also tests exceptions from
        the callback by Generating an exception if InputParam1 has the
        value 'CIM_ERR_FAILED'
        """
        # pylint: disable=attribute-defined-outside-init

        self.executed_method = 'Method2'

        assert params == self.exp_input_params

        assert object_name.namespace == self.test_namespace

        # if inputparam 1 has defined value, execute exception to test
        # exception passback.
        for param in params:
            if param == 'TestCIMErrorException':
                # TODO extend so generates whatever exception defined
                if params[param].value == 'CIM_ERR_FAILED':
                    raise CIMError(CIM_ERR_FAILED,
                                   'Test of exception in callback')

        return (self.return_value, self.return_params)

    def fuzzy_callback(self, conn, methodname, object_name, **params):
        # pylint: disable=attribute-defined-outside-init, unused-argument
        # pylint: disable=invalid-name
        """
        InvokeMethod callback.  This is a simple callback that just tests
        methodname and then returns returnvalue and params from the
        TestInvokeMethod object attributes.
        """
        self.executed_method = 'Fuzzy'

        # Test should be subclass
        assert methodname == self.executed_method
        assert params == self.exp_input_params

        assert object_name.namespace == self.test_namespace

        return (self.return_value, self.return_params)

    @pytest.mark.parametrize(
        "ns", [None, 'root/blah'])
    @pytest.mark.parametrize(
        # desc: description of test.
        # inputs: dictionary of input object_name, methodname, Params and
        #         optionally params.
        # exp_output: dictionary of expected returnvalue ('return') and output
        #            params('params') as list of tuples.
        # exp_except_type: None or expected exception type.
        # cim_err_code_name: None or expected CIMError status code if
        #               exp_exception is CIMError as string.
        "desc, inputs, exp_output, exp_exception_type, cim_err_code_name", [
            ['Execution of Method1 method with single input param',
             {'object_name': CIMClassName('CIM_Foo_sub_sub'),
              'methodname': 'Method1',
              'Params': [('InputParam1', 'FirstData')], },
             {'return': 0, 'params': [CIMParameter('OutputParam1', 'string',
                                                   value='SomeString')]},
             None, None],

            ['Execution of Method1 method with objectname string',
             {'object_name': 'CIM_Foo_sub_sub',
              'methodname': 'Method1',
              'Params': [('InputParam1', 'FirstData')],
              'params': {}, },
             {'return': 0, 'params': [CIMParameter('OutPutParam1', 'string',
                                                   value='SomeString')]},
             None, None],

            ['Execution of Method1 method with multiple input params',
             {'object_name': CIMClassName('CIM_Foo_sub_sub'),
              'methodname': 'Method1',
              'Params': [('InputParam1', 'FirstData'),
                         ('InputParam2', 'SecondData')], },
             {'return': 0, 'params': [CIMParameter('OutPutParam1',
                                                   type='string')]},
             None, None],

            ['Simple Execution of Method2 method with single input param',
             {'object_name': CIMClassName('CIM_Foo_sub_sub'),
              'methodname': 'Method2',
              'Params': [('InputParam1', 'FirstData')], },
             {'return': 0, 'params': [CIMParameter('OutPutParam1', 'string',
                                                   value='SomeString')]},
             None, None],

            ['Execute Method1 with no input parameters',
             {'object_name': CIMClassName('CIM_Foo_sub_sub'),
              'methodname': 'Method1',
              'Params': [], },
             {'return': 0, 'params': [CIMParameter('OutPutParam1', 'string',
                                                   value='SomeString')]},
             None, None],

            ['Execute Method1 with no output parameters',
             {'object_name': CIMClassName('CIM_Foo_sub_sub'),
              'methodname': 'Method1',
              'Params': [('InputParam1', 'FirstData')], },
             {'return': 0, 'params': []},
             None, None],

            ['Execute Method1 with no input/output parameters',
             {'object_name': CIMClassName('CIM_Foo_sub_sub'),
              'methodname': 'Method1',
              'Params': [], },
             {'return': 0, 'params': []},
             None, None],

            ['Execute Method1 with invalid namespace',
             {'object_name': CIMClassName('CIM_Foo_sub_sub'),
              'methodname': 'Method1',
              'Params': [], },
             {'return': 0, 'params': []},
             CIMError, 'CIM_ERR_INVALID_NAMESPACE'],

            ['Execute Method2 with invalid namespace',
             {'object_name': CIMClassName('CIM_Foo_sub_sub'),
              'methodname': 'Method2',
              'Params': [], },
             {'return': 0, 'params': []},
             CIMError, 'CIM_ERR_INVALID_NAMESPACE'],

            ['Execute method name with valid instancename',
             {'object_name':
              CIMInstanceName('CIM_Foo_sub_sub',
                              keybindings={'InstanceID': 'CIM_Foo_sub_sub21'}),
              'methodname': 'Method1',
              'Params': [], },
             {'return': 0, 'params': []},
             None, None],

            ['Execute method name with ObjectName that does not exist',
             {'object_name': CIMInstanceName('CIM_Foo_sub_sub',
                                             keybindings={'InstanceID':
                                                          'blah'}),
              'methodname': 'Method1',
              'Params': [], },
             {'return': 0, 'params': []},
             CIMError, 'CIM_ERR_NOT_FOUND'],

            ['Execute with methodname that is not in repository',
             {'object_name': CIMClassName('CIM_Foo_sub_sub'),
              'methodname': 'Methodx',
              'Params': [], },
             {'return': 0, 'params': []},
             CIMError, 'CIM_ERR_METHOD_NOT_FOUND'],

            ['Execute method name with invalid classname',
             {'object_name': CIMClassName('CIM_Foo_sub_subx'),
              'methodname': 'Method1',
              'Params': [], },
             {'return': 0, 'params': []},
             CIMError, 'CIM_ERR_NOT_FOUND'],

            ['Execute objectname invalid type',
             {'object_name': CIMQualifierDeclaration('Key', 'string'),
              'methodname': 'Method1',
              'Params': [], },
             {'return': 0, 'params': []},
             TypeError, None],

            ['Execute Method2 with input param flag to cause exception',
             {'object_name': CIMClassName('CIM_Foo_sub_sub'),
              'methodname': 'Method2',
              'Params': [('TestCIMErrorException', 'CIM_ERR_FAILED')], },
             {'return': 0, 'params': []},
             CIMError, 'CIM_ERR_FAILED'],

            ['Execute Fuzzy method with simple input params',
             {'object_name': CIMClassName('CIM_Foo'),
              'methodname': 'Fuzzy',
              'Params': [], },
             {'return': 0,
              'params': [CIMParameter('OutputParam', 'string',
                                      value='Some data'),
                         CIMParameter(
                             'foo', 'reference',
                             value=CIMInstanceName(
                                 'CIM_Foo', {'InstanceID': 'CIM_F001'}))]},
             None, None],


            ['Execute Fuzzy method with where method call is for subclass',
             {'object_name': CIMClassName('CIM_Foo_sub_sub'),
              'methodname': 'Fuzzy',
              'Params': [], },
             {'return': 0,
              'params': [CIMParameter('OutputParam', 'string',
                                      value='Some data'),
                         CIMParameter(
                             'foo', 'reference',
                             value=CIMInstanceName(
                                 'CIM_Foo', {'InstanceID': 'CIM_F001'}))]},
             None, None],

            ['Execute Fuzzy method with CIMInstanceName in input params',
             {'object_name': CIMClassName('CIM_Foo'),
              'methodname': 'Fuzzy',
              'Params': [('FuzzyParameter', 'Some data'),
                         ('foo',
                          CIMInstanceName('CIM_Foo',
                                          {'InstanceID': 'CIM_F001'}, ), )], },
             {'return': 32,
              'params': [CIMParameter('OutputParam', 'string',
                                      value='Some data'),
                         CIMParameter(
                             'foo', 'reference',
                             value=CIMInstanceName(
                                 'CIM_Foo', {'InstanceID': 'CIM_F001'}))]},
             None, None],
        ]
    )
    def test_invokemethod(self, conn, ns, desc, inputs, exp_output,
                          exp_exception_type, cim_err_code_name,
                          tst_instances_mof):
        """
        Test extrinsic method invocation through the
        WBEMConnection.InovkeMethod method
        """
        conn.compile_mof_string(tst_instances_mof, namespace=ns)

        # Save expected info so that callbacks can use in in returns and tests
        # pylint: disable=attribute-defined-outside-init

        # Create dictionary of input parameters to match what the
        # callback should see.
        params_dict = NocaseDict()
        if inputs['Params']:
            for param in inputs['Params']:
                if isinstance(param, CIMParameter):
                    params_dict[param.name] = param
                elif isinstance(param, tuple):
                    params_dict[param[0]] = CIMParameter(param[0],
                                                         cimtype(param[1]),
                                                         value=param[1])
                else:
                    assert False, "Invalid exp_input_params"
        self.exp_input_params = params_dict

        if 'params' in inputs:
            for param in inputs['params']:
                self.exp_input_params[param] = \
                    CIMParameter(param, cimtype(param[param]),
                                 value=param[param])

        self.return_value = exp_output['return']

        # provide for cases where 'params' does not exist.
        self.input_params = inputs['params'] if 'params' in inputs else {}
        self.return_params = exp_output['params']

        # Add to InvokeMethod callback methods in the class.
        conn.add_method_callback('CIM_Foo_sub_sub', 'Method1',
                                 self.method1_callback,
                                 namespace=ns)
        conn.add_method_callback('CIM_Foo_sub_sub', 'Method2',
                                 self.method2_callback,
                                 namespace=ns)

        conn.add_method_callback('CIM_Foo', 'Fuzzy',
                                 self.fuzzy_callback,
                                 namespace=ns)

        # set namespace in object_name if required.
        object_name = inputs['object_name']
        tst_ns = conn.default_namespace if ns is None else ns
        self.test_namespace = tst_ns

        if isinstance(object_name, (CIMClassName, CIMInstanceName)):
            object_name.namespace = ns
        else:
            # String object_name does not allow anything but default namespace
            # Bypass test if ns is not None
            if ns:
                return

        if not exp_exception_type:
            # Two calls to account for **params
            if self.input_params:
                result = conn.InvokeMethod(inputs['methodname'],
                                           object_name,
                                           inputs['Params'],
                                           self.input_params)
            else:
                result = conn.InvokeMethod(inputs['methodname'],
                                           object_name,
                                           inputs['Params'],)

            # Test return values and confirm correct method executed
            assert result[0] == exp_output['return']

            # map iterable of CIMParameter in exp_output to NocaseDict
            exp_output_dict = NocaseDict()
            for param in exp_output['params']:
                exp_output_dict[param.name] = param.value

            assert result[1] == exp_output_dict

            assert self.executed_method == inputs['methodname']

        else:
            if cim_err_code_name and cim_err_code_name == \
                    'CIM_ERR_INVALID_NAMESPACE':
                object_name.namespace = 'Reallybadnamespace'

            with pytest.raises(exp_exception_type) as exec_info:
                conn.InvokeMethod(inputs['methodname'],
                                  object_name,
                                  inputs['Params'], )

            exc = exec_info.value
            if cim_err_code_name:
                print('exc.status_code_name %s cim_err_code %s' %
                      (exc.status_code_name, cim_err_code_name))
                assert exc.status_code_name == cim_err_code_name
