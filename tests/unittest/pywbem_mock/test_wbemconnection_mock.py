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
using a set of local mock qualifiers, classes, and instances.  Note that
these tests do not use the pywbem simplified_test_function because they
use the pytest fixtures.  We understand that the 2 functionalities are
completely incompatible because fixtures are resolved as test parameters and
simplified_test_function completely controls the test parameters.

"""
from __future__ import absolute_import, print_function

import os
import io
import shutil
import re
from copy import deepcopy
from datetime import datetime

try:
    from collections import OrderedDict
except ImportError:
    from ordereddict import OrderedDict  # pylint: disable=import-error
import six

try:
    from unittest.mock import Mock
except ImportError:
    from mock import Mock

import pytest
from nocaselist import NocaseList
from testfixtures import OutputCapture

from ...utils import skip_if_moftab_regenerated
from ..utils.dmtf_mof_schema_def import TOTAL_QUALIFIERS, TOTAL_CLASSES, \
    install_test_dmtf_schema, DMTF_TEST_SCHEMA_VER
from ..utils.pytest_extensions import simplified_test_function
from ..utils.unittest_extensions import assert_copy

# pylint: disable=wrong-import-position, wrong-import-order, invalid-name
from ...utils import import_installed
pywbem = import_installed('pywbem')
from pywbem import CIMClass, CIMProperty, CIMInstance, CIMMethod, \
    CIMParameter, Uint32, MOFCompileError, MOFRepositoryError, \
    CIMInstanceName, CIMClassName, CIMQualifier, CIMQualifierDeclaration, \
    CIMError, MOFDependencyError, DEFAULT_NAMESPACE, CIM_ERR_INVALID_CLASS, \
    CIM_ERR_INVALID_NAMESPACE, CIM_ERR_NOT_FOUND, CIM_ERR_INVALID_PARAMETER, \
    CIM_ERR_ALREADY_EXISTS, CIM_ERR_INVALID_ENUMERATION_CONTEXT, \
    CIM_ERR_NAMESPACE_NOT_EMPTY, CIM_ERR_INVALID_SUPERCLASS, \
    CIM_ERR_NOT_SUPPORTED, CIM_ERR_METHOD_NOT_AVAILABLE, \
    CIM_ERR_QUERY_LANGUAGE_NOT_SUPPORTED, CIM_ERR_METHOD_NOT_FOUND, \
    CIM_ERR_FAILED, CIM_ERR_CLASS_HAS_CHILDREN, \
    CIM_ERR_CLASS_HAS_INSTANCES, MOFParseError  # noqa: E402
from pywbem._nocasedict import NocaseDict  # noqa: E402
from pywbem._utils import _format  # noqa: E402
from pywbem._cim_operations import pull_path_result_tuple  # noqa: E402
pywbem_mock = import_installed('pywbem_mock')
from pywbem_mock import FakedWBEMConnection, DMTFCIMSchema, \
    InstanceWriteProvider, MethodProvider, BaseProvider, \
    IGNORE_INSTANCE_IQ_PARAM, IGNORE_INSTANCE_ICO_PARAM  # noqa: E402
# pylint: enable=wrong-import-position, wrong-import-order, invalid-name


VERBOSE = False

# test variables to allow selectively executing tests.
OK = True
RUN = True
FAIL = False


# location of testsuite/schema dir used by all tests as test DMTF CIM Schema
# This directory is permanent and should not be removed.
TEST_DIR = os.path.dirname(__file__)

# Location of DMTF schema directory used by all tests.
# This directory is permanent and should not be removed.
TESTSUITE_SCHEMA_DIR = os.path.join('tests', 'schema')

# List of initially existing namespaces in the CIM repository
INITIAL_NAMESPACES = [DEFAULT_NAMESPACE]


# Expand the set of namespaces to include one that is not the default
# namespace.  This should be used with the methods to add NOT_DEFAULT_NS
# to the mock before compiling into the mock or adding cim objects.
# There are methods to accomplish this.
NOT_DEFAULT_NS = 'root/notdefaultns'
EXPANDED_NAMESPACES = [DEFAULT_NAMESPACE, NOT_DEFAULT_NS]


# Temporarily set this because all of the fixtures generate this warning
# for every use.  One alternative may be to prefix each fixture name with
# an underscore
# pylint: disable=redefined-outer-name


#
#   The following functions provide detailed comparison of lists of
#   CIMInstanceName and CIMInstance for equality. They were built for early
#   tests and could be removed in favor of a simpler test now that
#   the mock is operatonal.
#
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
    Compare the model path component of CIMInstanceNames for equality. The model
    path is the classname and keybindings components of CIMInstanceName

    Return True if equal, otherwise return False
    """
    if p1.keybindings == p2.keybindings \
            and p1.classname.lower() == p2.classname.lower():
        return True
    if p1.classname.lower() != p2.classname.lower():
        print(_format('ModelPathCompare. classnames %s and %s not equal.',
                      p1.classname, p2.classname))
    else:
        print(_format('ModelPathCompare. keybinding difference:\np1:\n%s'
                      '\np2\n%s', p1.keybindings, p2.keybindings))
    return False


def fix_instname_namespace_keys(inst_name, ns):
    """
    Set the namespace component of any keys  in the instance
    to the value defined by ns.  This is used to fix the keybindings in
    association CIMInstanceNames to match the repository which includes the
    namespace as part of the keys.
    """
    assert isinstance(inst_name, CIMInstanceName)
    inst_name = inst_name.copy()  # copy so we do not change original
    # iterate through the keybindings for any that are CIMInstanceName
    # If the namespace component is None, modify to the value of ns
    for value in six.itervalues(inst_name.keybindings):
        if isinstance(value, CIMInstanceName):
            if value.namespace is None:
                value.namespace = ns
    return inst_name


def assert_equal_ciminstancenames(l1, l2, model=False):
    """
    Assert if the two iterables of CIMInstanceNames are not equal except
    for order
    """
    def set_model_path(cin):
        """Return model path component of CIMInstanceName"""
        assert isinstance(cin, CIMInstanceName)
        mp = cin.copy()
        mp.host = None
        mp.namespace = None
        return mp

    if model:
        l1 = [set_model_path(cin) for cin in l1]
        l2 = [set_model_path(cin) for cin in l2]

    assert set(l1) == set(l2)


def assert_equal_ciminstances(insts1, insts2, pl=None):
    """
    Test if instances in two iterables are equal.

    The instances in the iterables can by in any order. The instances must have
    a non-empty path. Compared are classname, path, and the set of properties
    in the property list pl (if set).
    """

    if isinstance(insts1, CIMInstance):
        insts1 = [insts1]
    if isinstance(insts2, CIMInstance):
        insts2 = [insts2]

    assert len(insts1) == len(insts2)

    # Sort both lists by path
    insts1_s = sorted(insts1, key=lambda x: x.path.to_wbem_uri('canonical'))
    insts2_s = sorted(insts2, key=lambda x: x.path.to_wbem_uri('canonical'))

    for i, inst1 in enumerate(insts1_s):
        inst2 = insts2_s[i]
        assert isinstance(inst1, CIMInstance)
        assert isinstance(inst2, CIMInstance)
        assert inst1.classname.lower() == inst2.classname.lower()
        assert isinstance(inst1.path, CIMInstanceName)
        assert isinstance(inst2.path, CIMInstanceName)
        assert inst1.path == inst2.path
        if pl:
            for pname in pl:
                assert pname in inst1.properties
                assert pname in inst2.properties
                prop1 = inst1.properties[pname]
                prop2 = inst1.properties[pname]
                assert isinstance(prop1, CIMProperty)
                assert isinstance(prop2, CIMProperty)
                assert prop1.type == prop2.type
                assert prop1.value == prop2.value


def objs_equal(objdict1, objdict2, obj_type, parent_obj_name):
    """
    Equality test and display for objects that are a part of a class or
    instance, i.e. methods, properties, parameters and qualifiers

    Returns True  if equal  or False if not equal

    """
    if objdict1 == objdict2:
        return True

    print('Mismatch: Obj type=%s parent name %s' % (obj_type, parent_obj_name))

    if len(objdict1) != len(objdict2):
        print('Number of %s(s):%s differ\n  p1(len=%s)=%s\n  p2(len=%s)=%s' %
              (obj_type, parent_obj_name,
               len(objdict1), sorted(objdict1.keys()),
               len(objdict2), sorted(objdict2.keys())))
        return False

    for name, value in objdict1.items():
        if name not in objdict2:
            print('%s:%s %s in %s not in %s' % (obj_type, parent_obj_name,
                                                name,
                                                objdict1.keys().sort(),
                                                objdict2.keys().sort()))

        if value != objdict2[name]:
            print('%s:%s mismatch \np1=%r\np2=%r' %
                  (obj_type, parent_obj_name, value, objdict2[name]), )
        if getattr(value, "qualifiers", None):
            objs_equal(value.qualifiers, objdict2[name].qualifiers,
                       'qualifiers', parent_obj_name + ':' + name)
        if getattr(value, "parameters", None):
            objs_equal(value.parameters, objdict2[name].parameters,
                       'parameter', parent_obj_name + ':' + name)

    return False


def insts_equal(inst1, inst2):
    """
    Compare the properties, qualifiers and model paths of two instances
    for equality.

    Returns True if equal or False if not equal
    """
    if equal_model_path(inst1.path, inst2.path) and \
            inst1.classname == inst2.classname and \
            inst1.qualifiers == inst2.qualifiers and \
            inst1.properties == inst2.properties:
        return True

    if inst1.properties != inst2.properties:
        if len(inst1.properties) != len(inst2.properties):
            print('Number of properties differ p1(%s)=%s, p2(%s)=%s' %
                  (len(inst1.properties), inst1.properties.keys(),
                   len(inst2.properties), inst2.properties.keys()))
        else:
            for prop1, pvalue1 in inst1.properties.items():
                if pvalue1 != inst2.properties[prop1]:
                    print('Inst mismatch property \np1=%r\np2=%r' %
                          (inst1.properties[prop1], inst2.properties[prop1]))

    objs_equal(inst1.qualifiers, inst2.qualifiers, 'qualifiers',
               'instance  %s' % inst1.classname)

    return False


def classes_equal(cls1, cls2):
    """
    Detailed test of classes for equality. Displays component found not
    equal.

    Returns True if equal, else False
    """

    if cls1 == cls2:
        return True
    if cls1.classname != cls2.classname:
        print("Classname mismatch %s != %s" % (cls1.classname, cls2.classname))
        return False
    if cls1.superclass and cls1.superclass != cls2.superclass:
        print("Class %s superclass mismatch %s != %s" % (cls1. classname,
                                                         cls1.superclass,
                                                         cls2.superclass))
        return False

    objs_equal(cls1.qualifiers, cls2.qualifiers, 'qualifier', cls1.classname)

    objs_equal(cls1.properties, cls2.properties, 'Property', cls1.classname)

    objs_equal(cls1.methods, cls2.methods, 'Method', cls1.classname)

    return False


def assert_classes_equal(cls1, cls2):
    """
    Test for classes equal and assert. Rather than just use == this code
    tests the components and displays info on the differences if the classes
    are not equal.  This is useful because just outputing the repl for a
    class generates data that is difficult to debug.
    """
    classes_equal(cls1, cls2)
    assert cls1 == cls2


###################################################################
#
#  Fixtures for testing pywbem_mock. These are pytest fixtues that
#  define the objects that make up the CIM qualifiers declarations,
#  CIM classes, and CIM instances used in the tests.  They include
#  definitions to build both pywbem objects and MOF for the models.
#
###################################################################


@pytest.fixture
def tst_qualifiers():
    """
    CIM_Qualifierdecl definition of qualifiers used by tst_classes
    """
    scopesp = NocaseDict([
        ('CLASS', False),
        ('ASSOCIATION', False),
        ('INDICATION', False),
        ('PROPERTY', True),
        ('REFERENCE', True),
        ('METHOD', False),
        ('PARAMETER', False),
        ('ANY', False),
    ])
    scopesd = NocaseDict([
        ('CLASS', True),
        ('ASSOCIATION', True),
        ('INDICATION', True),
        ('PROPERTY', True),
        ('REFERENCE', True),
        ('METHOD', True),
        ('PARAMETER', True),
        ('ANY', True),
    ])
    q1 = CIMQualifierDeclaration('Key', 'boolean', is_array=False,
                                 scopes=scopesp,
                                 overridable=False, tosubclass=True,
                                 toinstance=False, translatable=None)
    q2 = CIMQualifierDeclaration('Description', 'string', is_array=False,
                                 scopes=scopesd,
                                 overridable=True, tosubclass=True,
                                 toinstance=False, translatable=None)
    return [q1, q2]


@pytest.fixture
def tst_class():
    """
    Builds and returns a single class: CIM_Foo that to be used as a
    test class for the mock class tests.
    This assumes that add_cimobjects resolves classes. so things line
    scoping, etc. on qualifiers and class origin are not included
    """
    kkey = {'Key': CIMQualifier('Key', True)}
    dkey = {'Description': CIMQualifier('Description', 'CIM_Foo description')}
    qkey = {'Description': CIMQualifier('Description', 'qualifier description')}

    c = CIMClass(
        'CIM_Foo', qualifiers=dkey,
        properties={'InstanceID':
                    CIMProperty('InstanceID', None, qualifiers=kkey,
                                type='string')},
        methods={'Delete': CIMMethod('Delete', 'uint32', qualifiers=qkey),
                 'Fuzzy': CIMMethod('Fuzzy', 'string', qualifiers=qkey)})
    return c


@pytest.fixture
def tst_classwqualifiers(tst_qualifiers, tst_class):
    """
    Returns the tst class CIM_Foo with its qualifier declarations.
    """
    return tst_qualifiers + [tst_class]


@pytest.fixture
def tst_classes(tst_class):
    """
    Builds and returns a list of 5 classes
        CIM_Foo - top level in hierarchy
        CIM_Foo_sub - Subclass to CIMFoo
        CIM_Foo_sub2 - Subclass to CIMFoo
        CIM_Foo_sub_sub - Subclass to CIMFoo_sub
        CIM_Foo_nokey - top level in hierarchy
    This assumes that add_cimobjects resolves classes. so things line
    scoping, etc. on qualifiers and class origin are not included
    """
    ckey = {'Description': CIMQualifier('Description', 'Subclass Description')}
    pkey = {'Description': CIMQualifier('Description', 'property description')}
    qkey = {'Description': CIMQualifier('Description', 'qualifier description')}

    c2 = CIMClass(
        'CIM_Foo_sub', superclass='CIM_Foo', qualifiers=ckey,
        properties={'cimfoo_sub':
                    CIMProperty('cimfoo_sub', None, type='string',
                                qualifiers=qkey)})

    c3 = CIMClass(
        'CIM_Foo_sub2', superclass='CIM_Foo', qualifiers=ckey,
        properties={'cimfoo_sub2':
                    CIMProperty('cimfoo_sub2', None, type='string',
                                qualifiers=pkey)})

    c4 = CIMClass(
        'CIM_Foo_sub_sub', superclass='CIM_Foo_sub', qualifiers=ckey,
        properties={'cimfoo_sub_sub':
                    CIMProperty('cimfoo_sub_sub', None, type='string',
                                qualifiers=pkey)})

    c5 = CIMClass(
        'CIM_Foo_nokey', qualifiers=ckey,
        properties=[
            CIMProperty('InstanceID', None, qualifiers=qkey, type='string'),
            CIMProperty('cimfoo', None, qualifiers=qkey, type='string',),
        ])

    return [tst_class, c2, c3, c4, c5]


@pytest.fixture
def tst_classeswqualifiers(tst_qualifiers, tst_classes):
    """
    Append the test qualifiers to the test classes and return both
    """
    return tst_qualifiers + tst_classes


@pytest.fixture
def tst_pg_namespace_class():
    """
    Builds and returns a PG_Namespace class.
    """
    qkey = CIMQualifier('Key', True, overridable=False, tosubclass=True)
    c = CIMClass(
        'PG_Namespace', superclass=None,
        properties=[
            CIMProperty('Name', None, type='string',
                        qualifiers=[qkey]),
            CIMProperty('CreationClassName', None, type='string',
                        qualifiers=[qkey]),
            CIMProperty('ObjectManagerName', None, type='string',
                        qualifiers=[qkey]),
            CIMProperty('ObjectManagerCreationClassName', None, type='string',
                        qualifiers=[qkey]),
            CIMProperty('SystemName', None, type='string',
                        qualifiers=[qkey]),
            CIMProperty('SystemCreationClassName', None, type='string',
                        qualifiers=[qkey]),
        ]
    )
    return c


def build_cimfoo_instance(id_):
    """
    Build a single instance of an instance of CIM_Foo where id is
    used to create the unique identity. The input parameter id_ is used
    to create the value for the key property InstanceID.
    """
    iname = 'CIM_Foo{}'.format(id_)
    return CIMInstance('CIM_Foo',
                       properties={'InstanceID': iname},
                       path=CIMInstanceName('CIM_Foo', {'InstanceID': iname}))


def build_cimfoosub_instance(id_):
    """
    Build a single instance of an instance of CIM_Foo where id is
    used to create the unique identity.
    """
    inst_id = 'CIM_Foo_sub{}'.format(id_)
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
    inst_id = 'CIM_Foo_sub{}'.format(id_)
    inst = CIMInstance('CIM_Foo_sub2',
                       properties={
                           'InstanceID': inst_id,
                           'cimfoo_sub2': 'cimfoo_sub2 prop for {}'.
                                          format(inst_id)},
                       path=CIMInstanceName('CIM_Foo_sub2',
                                            {'InstanceID': inst_id}))
    return inst


def build_cimfoosub_sub_instance(id_):
    """
    Build a single instance of an instance of CIM_Foo_sub2 where id is
    used to create the unique identity.
    """
    inst_id = 'CIM_Foo_sub_sub{}'.format(id_)
    inst = CIMInstance('CIM_Foo_sub_sub',
                       properties={
                           'InstanceID': inst_id,
                           'cimfoo_sub': 'cimfoo_sub prop:{}'.format(inst_id),
                           'cimfoo_sub_sub': 'cimfoo_sub_sub:{}'.
                                             format(inst_id)},
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
    # Build 3 instance of each of the classes useing the classname<integer) as
    # the instance name
    for i in six.moves.range(1, 4):
        rtn.append(build_cimfoo_instance(i))
        rtn.append(build_cimfoosub_instance(i))
        rtn.append(build_cimfoosub2_instance(i))
        rtn.append(build_cimfoosub_sub_instance(i))
    rtn.append(build_cimfoo_nokey_instance())
    return rtn


@pytest.fixture
def tst_classeswqualifiersandinsts(tst_classeswqualifiers, tst_instances):
    """
    Append tst_instances to tst_classeswqualifiers. This builds a simple
    package of qualifiers, classes and instances that can be added to
    repository.
    """
    return tst_classeswqualifiers + tst_instances


@pytest.fixture
def tst_insts_big():
    """
    Create Instances of cimfoo for the ide 3 to what is in list_size.  This
    does not include instances that were created in the tst_instances
    fixture.
    """
    list_size = 100
    big_list = []

    for i in six.moves.range(4, list_size + 1):
        big_list.append(build_cimfoo_instance(i))
    return big_list


#
#   Test fixtures that return MOF
#


@pytest.fixture
def tst_classes_mof(tst_qualifiers_mof):
    """
    Test classes to be compiled as part of tests. This is the same
    classes as the tst_classes fixture. This merges the tst_compile_qualifiers
    str and the classes string into a single string and returns it.
    The qualifiers are merged because they are required to resolve classes
    within the repository.
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

              [Static]
            uint32 StaticMethod1(
                [IN, Description("Input Param1")]
              string InputParam1,
                [IN, Description("Input Param2")]
              string InputParam2,
                [IN ( false), OUT, Description("Response param 1")]
              string OutputParam1,
                [IN ( false), OUT, Description("Response param 2")]
              string OutputParam2[]);
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
    test_classes_mof.  The instance ids of these shoud match those in
    def tst_instances()
    """
    inst_str = """
        instance of CIM_Foo { InstanceID = "CIM_Foo1"; };
        instance of CIM_Foo { InstanceID = "CIM_Foo2"; };
        instance of CIM_Foo { InstanceID = "CIM_Foo3"; };

        instance of CIM_Foo_sub { InstanceID = "CIM_Foo_sub1";
                                  cimfoo_sub = "data sub1";};
        instance of CIM_Foo_sub { InstanceID = "CIM_Foo_sub2";
                                  cimfoo_sub = "data sub2";};
        instance of CIM_Foo_sub { InstanceID = "CIM_Foo_sub3";
                                  cimfoo_sub = "data sub3";};

        instance of CIM_Foo_sub2 { InstanceID = "CIM_Foo_sub1";
                                   cimfoo_sub2 = "data sub_sub1";};
        instance of CIM_Foo_sub2 { InstanceID = "CIM_Foo_sub2";
                                   cimfoo_sub2 = "data sub_sub2";};
        instance of CIM_Foo_sub2 { InstanceID = "CIM_Foo_sub3";
                                   cimfoo_sub2 = "data sub3";};

        instance of CIM_Foo_sub_sub {
            InstanceID = "CIM_Foo_sub_sub1";
            cimfoo_sub = "data sub1";
            cimfoo_sub_sub = "data sub1";};
        instance of CIM_Foo_sub_sub {
            InstanceID = "CIM_Foo_sub_sub2";
            cimfoo_sub = "data sub2";
            cimfoo_sub_sub = "data sub_sub2";};
        instance of CIM_Foo_sub_sub {
            InstanceID = "CIM_Foo_sub_sub3";
            cimfoo_sub = "data sub3";
            cimfoo_sub_sub = "data sub_sub3";};
    """
    return tst_classes_mof + '\n\n' + inst_str + '\n\n'


@pytest.fixture
def tst_person_instance_names():
    """Defines the instance names for the instances in tst_assoc_mof below"""
    return ['Mike', 'Saara', 'Sofi', 'Gabi']


@pytest.fixture
def tst_assoc_qualdecl_mof():
    """
    Set of qualifier declarations used in definition of a set of
    classes to test associations
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
    """


@pytest.fixture
def tst_assoc_class_mof(tst_assoc_qualdecl_mof):
    """
    Target, destination, and association classes used to define an
    association test model. This fixture assumes that qualifier declarations
    have been defined consistent with tst_assoc_qualdecl fixture above.
    """
    assoc_classes_mof = """
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
    """

    return tst_assoc_qualdecl_mof + assoc_classes_mof


@pytest.fixture
def tst_assoc_mof(tst_assoc_class_mof):
    """
    Complete MOF definition of a simple set of classes and association instances
    to test associations and references. Includes qualifiers, classes,
    and instances.
    """
    assoc_instances = """
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
    return tst_assoc_class_mof + assoc_instances


# Counts of instances for tests of tst_assoc_mof fixture.
TST_PERSON_INST_COUNT = 4                                 # num TST_PERSON
TST_PERSON_SUB_INST_COUNT = 4                             # num SUB
TST_PERSONWITH_SUB_INST_COUNT = TST_PERSON_INST_COUNT + \
    TST_PERSON_SUB_INST_COUNT                             # num both


def add_objects_to_repo(conn, namespace, objects_list):
    """
    Test setup.  Conditionally adds namespace to CIM repository and adds
    the lists of objects to the repo.  Each object in the objects_list may
    be  list of CIM objects that will be added using self.add_cimObject
    or a string that is MOF that will be compiled.

    Parameters:

      conn (:class:`~pywbem.FakedWBEMConnection`):

      namespace (:term:`string` or None):
        String defining the namespace for the additions to the repository
        or None if the default namespace is to be used

      objects_list (list or tuple of :term:`string` or of pywbem objects):
        List of the objects that will be inserted into the repository. The
        list may include both type as item in the list is inserted
        separately using the MOF compiler or add_cimobjects.
    """
    if namespace and namespace != conn.default_namespace:
        conn.add_namespace(namespace)
    assert isinstance(objects_list, (list, tuple))

    for obj in objects_list:
        if isinstance(obj, six.string_types):
            conn.compile_mof_string(obj, namespace=namespace)
        else:
            conn.add_cimobjects(obj, namespace=namespace)


#########################################################################
#
#            Pytest Test Classes
#  The tests are broken into several classes to separate major functionality
#  into groups.  The classes are:
#  1. TestFakedWBEMConnection
#  2. TestRepoMethods
#  3. TestClassOperations
#  4. TestInstanceOperations
#  5. TestReferenceOperations
#  6. TestAssociatorOperations
#  7. TestPullOperations
#  8. TestInvokeMethod
#
#########################################################################


class TestFakedWBEMConnection(object):
    """
    Test the basic characteristics of the FakedWBEMConnection including
    init parameters.
    """

    @pytest.mark.parametrize(
        "set_on_init", [False, True])
    @pytest.mark.parametrize(
        "delay", [.5, 1])
    def test_response_delay(self, tst_qualifiers, tst_class, set_on_init,
                            delay):
        # pylint: disable=no-self-use
        """
        Test the response delay attribute set both in init parameter and with
        attribute.
        """

        # pylint: disable=protected-access
        FakedWBEMConnection._reset_logging_config()
        if set_on_init:
            conn = FakedWBEMConnection(response_delay=delay)
        else:
            conn = FakedWBEMConnection()
            conn.response_delay = delay

        assert conn.response_delay == delay
        add_objects_to_repo(conn, None, [tst_qualifiers, tst_class])

        start_time = datetime.now()
        conn.GetClass('CIM_Foo')
        exec_time = (datetime.now() - start_time).total_seconds()

        if delay:
            assert exec_time > delay * .8
            assert exec_time < delay * 2.5
        else:
            assert exec_time < 0.1

    @pytest.mark.parametrize(
        "set_on_init", [False, True])
    @pytest.mark.parametrize(
        "disable, exp_exec", [[False, None],
                              [None, None],
                              [True, None],
                              [1, ValueError]])
    def test_disable_pull(self, tst_classeswqualifiers, tst_instances,
                          set_on_init, disable, exp_exec):
        # pylint: disable=no-self-use
        """
        Test the disable_pull_operations property set both in init
        and with property.
        """

        def operation_fail(fn, *pargs, **kwargs):
            """Confirm the operation fn fails with CIM_ERR_NOT_SUPPORTED"""
            with pytest.raises(CIMError) as exec_info:
                fn(*pargs, **kwargs)
            exc = exec_info.value
            assert exc.status_code == CIM_ERR_NOT_SUPPORTED

        # pylint: disable=protected-access
        FakedWBEMConnection._reset_logging_config()

        if exp_exec:
            # Test for exception
            with pytest.raises(exp_exec):
                if set_on_init:
                    conn = FakedWBEMConnection(disable_pull_operations=disable)
                else:
                    conn = FakedWBEMConnection()
                    assert conn.disable_pull_operations is False
                    conn.disable_pull_operations = disable

        else:
            if set_on_init:
                conn = FakedWBEMConnection(disable_pull_operations=disable)
            else:
                conn = FakedWBEMConnection()
                assert conn.disable_pull_operations is False
                conn.disable_pull_operations = disable

            # Test if the attribute correctly set in conn
            if disable:
                assert conn.disable_pull_operations is True
            elif disable is False:
                assert conn.disable_pull_operations is False
            else:
                assert disable is None
                assert conn.disable_pull_operations is False

            # Test if the attribute correctly set in conn._mainprovider
            if disable:
                assert conn._mainprovider.disable_pull_operations is True
            elif disable is False:
                assert conn._mainprovider.disable_pull_operations is False
            else:
                assert disable is None
                assert conn._mainprovider.disable_pull_operations is False

            conn.add_cimobjects(tst_classeswqualifiers)
            conn.add_cimobjects(tst_instances)
            tst_class = 'CIM_Foo'
            paths = conn.EnumerateInstanceNames(tst_class)
            path = paths[0]

            # The ExecQuery() operation of the main provider is not implemented.
            # For this test, we don't care about that because we just want to
            # verify disable_pull_operations. Therefore, the operation gets
            # mocked to return an empty query result.
            # pylint: disable=protected-access
            conn._mainprovider.ExecQuery = Mock(return_value=[])

            if conn.disable_pull_operations is True:
                operation_fail(conn.OpenEnumerateInstances, tst_class)
                operation_fail(conn.OpenEnumerateInstancePaths, tst_class)
                operation_fail(conn.OpenReferenceInstances, path)
                operation_fail(conn.OpenReferenceInstancePaths, path)
                operation_fail(conn.OpenAssociatorInstancePaths, path)
                operation_fail(conn.OpenAssociatorInstancePaths, path)
                operation_fail(conn.OpenQueryInstances,
                               'DMTF:FQL', "SELECT * FROM CIM_Foo")
            else:
                conn.OpenEnumerateInstances(tst_class)
                conn.OpenEnumerateInstancePaths(tst_class)
                conn.OpenReferenceInstances(path)
                conn.OpenReferenceInstancePaths(path)
                conn.OpenAssociatorInstancePaths(path)
                conn.OpenAssociatorInstancePaths(path)
                conn.OpenQueryInstances('DMTF:FQL', "SELECT * FROM CIM_Foo")

    def test_repr(self):
        # pylint: disable=no-self-use
        """ Test output of repr"""
        # pylint: disable=protected-access
        FakedWBEMConnection._reset_logging_config()
        conn = FakedWBEMConnection(response_delay=3)
        repr_ = '%r' % conn
        assert repr_.startswith('FakedWBEMConnection(response_delay=3,')

    def test_attr(self):
        # pylint: disable=no-self-use
        """
        Test initial FadedWBEMConnection attributes
        """
        # pylint: disable=protected-access
        FakedWBEMConnection._reset_logging_config()
        conn = FakedWBEMConnection()
        assert conn.scheme == 'http'
        assert conn.host == 'FakedUrl:5988'
        assert conn.url == 'http://FakedUrl:5988'
        assert conn.use_pull_operations is False
        assert conn.stats_enabled is False
        assert conn.default_namespace == DEFAULT_NAMESPACE
        assert conn.operation_recorder_enabled is False

    def test_userdefined_url(self):
        # pylint: disable=no-self-use
        """
        Test FadedWBEMConnection url __init__ parameter.
        """
        # pylint: disable=protected-access
        FakedWBEMConnection._reset_logging_config()
        conn = FakedWBEMConnection(url="http://FakedUrl1:5988")
        assert conn.scheme == 'http'
        assert conn.host == 'FakedUrl1:5988'
        assert conn.url == 'http://FakedUrl1:5988'
        assert conn.use_pull_operations is False
        assert conn.stats_enabled is False
        assert conn.default_namespace == DEFAULT_NAMESPACE
        assert conn.operation_recorder_enabled is False

    def test_multiple_urls(self):
        # pylint: disable=no-self-use
        """
        Test FadedWBEMConnection url __init__ parameter.
        """
        # pylint: disable=protected-access
        FakedWBEMConnection._reset_logging_config()
        conn1 = FakedWBEMConnection(url="http://FakedUrl1:5988")
        conn2 = FakedWBEMConnection(url="http://FakedUrl2:5988")
        assert conn1.scheme == 'http'
        assert conn1.host == 'FakedUrl1:5988'
        assert conn1.url == 'http://FakedUrl1:5988'
        assert conn1.use_pull_operations is False
        assert conn1.stats_enabled is False
        assert conn1.default_namespace == DEFAULT_NAMESPACE
        assert conn1.operation_recorder_enabled is False
        assert conn2.scheme == 'http'
        assert conn2.host == 'FakedUrl2:5988'
        assert conn2.url == 'http://FakedUrl2:5988'


class TestRepoMethods(object):
    """
    Test the repository support methods including the ability to add objects
    to the repository, _get_subclass_names, _get_superclass_names, _get_class,
    _get_instance, display_repository, etc.
    """

    @pytest.mark.parametrize(
        "ns", INITIAL_NAMESPACES)
    @pytest.mark.parametrize(
        "mof", [False, True])
    @pytest.mark.parametrize(
        "cln, exp_rslt",
        [
            # cln: classname input parameter for class_exists()
            # exp_rslt: Expected result of class_exists()

            ['CIM_Foo', True],
            ['CIM_FooX', False],
        ]
    )
    def test_class_exists(self, conn, tst_classeswqualifiers, tst_classes_mof,
                          ns, mof, cln, exp_rslt):
        # pylint: disable=no-self-use
        """ Test the class_exists() method"""
        if mof:
            skip_if_moftab_regenerated()
            conn.compile_mof_string(tst_classes_mof, namespace=ns)
        else:
            conn.add_cimobjects(tst_classeswqualifiers, namespace=ns)

        # The code to be tested
        # pylint: disable=protected-access
        rslt = conn._mainprovider.class_exists(ns, cln)

        assert rslt == exp_rslt

    @pytest.mark.parametrize(
        "ns", INITIAL_NAMESPACES)
    @pytest.mark.parametrize(
        "mof", [False, True])
    @pytest.mark.parametrize(
        "cln, di, exp_clns",
        [
            # cln: classname input parameter for _get_subclass_names()
            # di: deep_inheritance input parameter for _get_subclass_names()
            # exp_clns: Expected list of returned subclass names (any order)

            [None, True, ['CIM_Foo', 'CIM_Foo_sub', 'CIM_Foo_sub2',
                          'CIM_Foo_sub_sub', 'CIM_Foo_nokey']],
            [None, False, ['CIM_Foo', 'CIM_Foo_nokey']],
            ['CIM_Foo', True, ['CIM_Foo_sub', 'CIM_Foo_sub2',
                               'CIM_Foo_sub_sub']],
            ['cim_foo', True, ['CIM_Foo_sub', 'CIM_Foo_sub2',
                               'CIM_Foo_sub_sub']],  # test case insensitivity
            ['CIM_Foo', False, ['CIM_Foo_sub', 'CIM_Foo_sub2']],
            ['CIM_Foo_sub', True, ['CIM_Foo_sub_sub']],
            ['CIM_Foo_sub', False, ['CIM_Foo_sub_sub']],
        ]
    )
    def test_get_subclassnames(self, conn, tst_classeswqualifiers,
                               tst_classes_mof, ns, mof, cln, di, exp_clns):
        # pylint: disable=no-self-use
        """
        Test the internal _get_subclass_names() method. Tests against both
        add_cimobjects and compiled objects
        """
        if mof:
            skip_if_moftab_regenerated()
            conn.compile_mof_string(tst_classes_mof, namespace=ns)
        else:
            conn.add_cimobjects(tst_classeswqualifiers, namespace=ns)

        class_store = conn.cimrepository.get_class_store(ns)

        # The code to be tested
        # pylint: disable=protected-access
        rslt_clns = conn._mainprovider._get_subclass_names(cln, class_store, di)

        assert set(rslt_clns) == set(exp_clns)

    @pytest.mark.parametrize(
        "ns", INITIAL_NAMESPACES)
    @pytest.mark.parametrize(
        "mof", [False, True])
    @pytest.mark.parametrize(
        "cln, exp_cln",
        [
            # cln - classname where search for superclassnames begins
            # exp_cln - Expected superclasses of cln
            ['CIM_Foo', []],
            ['CIM_Foo_sub', ['CIM_Foo']],
            ['cim_foo_sub', ['CIM_Foo']],      # test case independence
            ['CIM_Foo_sub_sub', ['CIM_Foo', 'CIM_Foo_sub']],
        ]
    )
    def test_get_superclass_names(self, conn, tst_classeswqualifiers,
                                  tst_classes_mof, ns, mof, cln, exp_cln):
        # pylint: disable=no-self-use
        """
            Test the _get_superclass_names method
        """
        if mof:
            skip_if_moftab_regenerated()
            conn.compile_mof_string(tst_classes_mof, namespace=ns)
        else:
            conn.add_cimobjects(tst_classeswqualifiers, namespace=ns)

        class_store = conn.cimrepository.get_class_store(ns)
        # pylint: disable=protected-access
        clns = conn._mainprovider._get_superclass_names(cln, class_store)
        assert clns == exp_cln

    @pytest.mark.parametrize(
        "ns", INITIAL_NAMESPACES)
    @pytest.mark.parametrize(
        "mof", [False, True])
    @pytest.mark.parametrize(
        "cln, lo, iq, ico, pl, exp_pl",
        [
            # cln: classname input parameter for get_class()
            # lo: local_only input parameter for get_class()
            # iq: include_qualifiers input parameter for get_class()
            # ico: include_classorigin input parameter for get_class()
            # pl: property_list input parameter for get_class()
            # exp_pl: Expected list of property names in result class

            # cln           lo     iq    ico   pl     exp_pl
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
            ['cim_foo_sub', True, True, False, ['cimfoo_sub'], ['cimfoo_sub']],
        ]
    )
    def test_get_class(self, conn, tst_classeswqualifiers, tst_classes_mof,
                       ns, mof, cln, lo, iq, ico, pl, exp_pl):
        # pylint: disable=no-self-use
        """
        Test variations on the get_class() method that gets a class
        from the repository, creates a copy  and filters it.
        """
        if mof:
            skip_if_moftab_regenerated()
            conn.compile_mof_string(tst_classes_mof, namespace=ns)
        else:
            conn.add_cimobjects(tst_classeswqualifiers, namespace=ns)

        # _get_class gets a copy of the class filtered by the parameters

        # The code to be tested
        # pylint: disable=protected-access
        rslt_cl = conn._mainprovider.get_class(ns, cln, local_only=lo,
                                               include_qualifiers=iq,
                                               include_classorigin=ico,
                                               property_list=pl)

        cl_props = [p.name for p in six.itervalues(rslt_cl.properties)]

        class_store = conn.cimrepository.get_class_store(ns)
        tst_class = class_store.get(cln)

        if ico:
            for prop in six.itervalues(rslt_cl.properties):
                assert prop.class_origin
            for method in six.itervalues(rslt_cl.methods):
                assert method.class_origin
        else:
            for prop in six.itervalues(rslt_cl.properties):
                assert not prop.class_origin
            for method in six.itervalues(rslt_cl.methods):
                assert not method.class_origin

        if not iq:
            assert not rslt_cl.qualifiers
            for prop in six.itervalues(rslt_cl.properties):
                assert not prop.qualifiers
            for method in six.itervalues(rslt_cl.methods):
                for param in six.itervalues(method.parameters):
                    assert not param.qualifiers
        else:
            assert rslt_cl.qualifiers == tst_class.qualifiers

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
            assert set(cl_props) == set(exp_pl)

    @pytest.mark.parametrize(
        "ns", INITIAL_NAMESPACES)
    @pytest.mark.parametrize(
        "mof", [False, True])
    @pytest.mark.parametrize(
        "cln, key, lo, iq, ico, pl, exp_pl, exp_exc",
        [
            # cln: classname input parameter for get_class()
            # key: value of InstanceID key property for the instance to use
            # lo: local_only
            # iq: include_qualifiers input parameter for get_class()
            # ico: include_classorigin input parameter for get_class()
            # pl: property_list input parameter for get_class()
            # exp_pl: Expected list of property names in result class
            # exp_exc: None, or expected exception object

            # cln       key         lo,   iq    ico   pl     exp_pl      exp_exc
            ['CIM_Foo', 'CIM_Foo1', False, None, None, None, ['InstanceID'],
             None],
            ['cim_foo', 'CIM_Foo1', False, None, None, None, ['InstanceID'],
             None],
            ['CIM_Foo', 'CIM_Foo1', False, None, None, ['InstanceID'],
             ['InstanceID'],
             None],
            ['CIM_Foo', 'CIM_Foo1', False, None, None, ['Instx'], [], None],
            ['CIM_Foo', 'CIM_Foo1', False, True, None, None, ['InstanceID'],
             None],
            ['CIM_Foo', 'CIM_Foo1', False, None, True, None, ['InstanceID'],
             None],
            ['CIM_Foo', 'CIM_Foo1', False, None, None, "", [], None],
            ['CIM_Foo', 'CIM_Foo2', False, None, None, None, ['InstanceID'],
             None],
            ['CIM_Foo_sub', 'CIM_Foo_sub1', False, None, None, None,
             ['InstanceID', 'cimfoo_sub'],
             None],

            ['CIM_Foo_sub', 'CIM_Foo_sub99', None, None, None, None, None,
             CIMError(CIM_ERR_NOT_FOUND)],

            # Test with local_only True

            ['CIM_Foo', 'CIM_Foo1', True, None, None, None,
             ['InstanceID'], None],
            ['cim_foo', 'CIM_Foo1', True, None, None, None,
             ['InstanceID'], None],
            ['CIM_Foo', 'CIM_Foo1', True, None, None,
             ['InstanceID'], ['InstanceID'], None],
            ['CIM_Foo', 'CIM_Foo1', True, None, None, ['Instx'], [], None],
            ['CIM_Foo', 'CIM_Foo1', True, True, None, None,
             ['InstanceID'], None],
            ['CIM_Foo', 'CIM_Foo1', True, None, True, None,
             ['InstanceID'], None],
            ['CIM_Foo', 'CIM_Foo1', True, None, None, "", [], None],
            ['CIM_Foo', 'CIM_Foo2', True, None, None, None,
             ['InstanceID'], None],
            ['CIM_Foo_sub', 'CIM_Foo_sub1', True, None, None, None,
             ['cimfoo_sub'],
             None],
            ['CIM_Foo_sub_sub', 'CIM_Foo_sub_sub1', True, None, None, None,
             ['cimfoo_sub_sub'], None],

            ['CIM_Foo_sub', 'CIM_Foo_sub99', None, None, None, None, None,
             CIMError(CIM_ERR_NOT_FOUND)],
        ]
    )
    def test_get_instance_internal(self, conn, tst_classeswqualifiers,
                                   tst_instances, tst_instances_mof, ns, mof,
                                   cln, key, lo, iq, ico, pl, exp_pl, exp_exc):
        # pylint: disable=no-self-use
        """
        Test the internal _get_instance method.  Test for getting correct and
        error responses for both compiled and added objects including parameters
        of propertylist, include qualifiers, include class origin.

        This allows us to easily test the options on local_only in addition
        to the other parameters on this method

        This method tests for correct number of properties
        """

        if mof:
            skip_if_moftab_regenerated()
            conn.compile_mof_string(tst_instances_mof, namespace=ns)
        else:
            conn.add_cimobjects(tst_classeswqualifiers, namespace=ns)
            conn.add_cimobjects(tst_instances, namespace=ns)

        # _get_instance_internal requires a namespace
        assert ns is not None

        iname = CIMInstanceName(cln,
                                keybindings={'InstanceID': key},
                                namespace=ns)
        if exp_exc is None:
            instance_store = conn.cimrepository.get_instance_store(ns)

            # The code to be tested
            # pylint: disable=protected-access
            inst = conn._mainprovider._get_instance(iname, instance_store,
                                                    lo, ico, iq, pl)

            assert isinstance(inst, CIMInstance)
            assert inst.path.classname.lower() == cln.lower()
            assert iname == inst.path
            assert inst.classname.lower() == cln.lower()
            assert inst.path.host is None

            if IGNORE_INSTANCE_ICO_PARAM:
                for prop in six.itervalues(inst.properties):
                    assert not prop.class_origin
            else:
                if ico:
                    for prop in six.itervalues(inst.properties):
                        assert prop.class_origin
                else:
                    for prop in six.itervalues(inst.properties):
                        assert not prop.class_origin

            if IGNORE_INSTANCE_IQ_PARAM:
                assert not inst.qualifiers
                for prop in six.itervalues(inst.properties):
                    assert not prop.qualifiers
            else:
                if not iq:
                    assert not inst.qualifiers
                    for prop in six.itervalues(inst.properties):
                        assert not prop.qualifiers
                else:
                    bare_inst = conn._mainprovider._get_bare_instance(
                        iname, instance_store)
                    if bare_inst.qualifiers:
                        assert inst.qualifiers
                    for prop in six.itervalues(inst.properties):
                        if bare_inst.properties[prop.name].qualifiers:
                            assert prop.qualifiers

            # TODO: There are no instances with qualifiers in tests so
            # the else option is not tested.

            if pl == "":
                assert not inst.properties
            else:
                assert set(inst.keys()) == set(exp_pl)

            # We do not do a complete compare because that means completely
            # recreating the filtering done in_get_instance_internal
            # for ico, iq and pl

        else:
            with pytest.raises(type(exp_exc)) as exec_info:
                instance_store = conn.cimrepository.get_instance_store(ns)

                # The code to be tested
                # pylint: disable=protected-access
                conn._mainprovider._get_instance(iname,
                                                 instance_store, lo,
                                                 ico, iq, pl)

            exc = exec_info.value
            if isinstance(exp_exc, CIMError):
                assert exc.status_code == exp_exc.status_code

    @pytest.mark.parametrize(
        "ns", INITIAL_NAMESPACES)
    @pytest.mark.parametrize(
        "mof", [False, True])
    @pytest.mark.parametrize(
        "cln, inst_id, exp_ok",
        [
            # cln: classname input parameter for get_class()
            # inst_id: InstanceID key selecting the instance to use
            # exp_ok: Boolean indicating whether an instance was expected to be
            #         returned

            ['CIM_Foo', 'CIM_Foo1', True],
            ['CIM_Foo', 'CIM_Foo2', True],
            ['cim_foo', 'CIM_Foo2', True],
            ['CIM_Foo_sub', 'CIM_Foo_sub1', True],
            ['CIM_Foo_sub', 'CIM_Foo_sub99', False],
        ]
    )
    def test_get_bare_instance(self, conn, tst_classeswqualifiersandinsts,
                               tst_instances_mof, ns, mof, cln, inst_id,
                               exp_ok):
        # pylint: disable=no-self-use
        """
        Test the find instance repo method with both compiled and add
        creation of the repo.
        """
        if mof:
            skip_if_moftab_regenerated()
            conn.compile_mof_string(tst_instances_mof, namespace=ns)
        else:
            add_objects_to_repo(conn, ns, tst_classeswqualifiersandinsts)

        instance_store = conn.cimrepository.get_instance_store(ns)

        iname = CIMInstanceName(cln,
                                keybindings={'InstanceID': inst_id},
                                namespace=ns)

        # The code to be tested
        # pylint: disable=protected-access
        inst = conn._mainprovider._get_bare_instance(iname, instance_store)

        if exp_ok:
            assert isinstance(inst, CIMInstance)
            assert equal_model_path(iname, inst.path)
        else:
            assert inst is None

    @pytest.mark.skip(reason="Used only to display repo so not real test.")
    def test_disp_repo_tostdout(self, conn, tst_instances_mof):
        # pylint: disable=no-self-use
        """
        Test method used only for manual tests.
        """
        skip_if_moftab_regenerated()
        namespaces = ['interop']
        for ns in namespaces:
            conn.add_namespace(ns)
            conn.compile_mof_string(tst_instances_mof, namespace=ns)

            inst_id = 'CIM_foo_sub_sub_test_unicode'

            str_data = u'\u212b \u0420 \u043e \u0441 \u0441\u0438 \u044f \u00e0'
            inst = CIMInstance(
                'CIM_Foo_sub_sub',
                properties={
                    'InstanceID': inst_id,
                    'cimfoo_sub': 'cimfoo_sub prop:  %s' % str_data,
                    'cimfoo_sub_sub': 'cimfoo_sub_sub: %s' % str_data},
                path=CIMInstanceName('CIM_Foo_sub_sub',
                                     {'InstanceID': inst_id}))
            conn.add_cimobjects(inst, namespace=ns)

            # The following will not compile.  Gets compiler error
            # str = u'instance of CIM_Foo_sub2 as $foosub22 {' \
            # u'InstanceID = "CIM_Foo_unicode";\n' \
            # u'cimfoo_sub2 = \u212b \u0420 \u043e \u0441 \u0441' \
            # u' \u0438 \u044f \u00e0;};'
            # conn.compile_mof_string(str, namespace=ns)

        # Test basic display repo output
        conn.display_repository()
        tst_file_name = 'tmp_testfrom_test_dr.txt'
        tst_file = os.path.join(TEST_DIR, tst_file_name)
        conn.display_repository(dest=tst_file)

    def test_display_repository(self, conn, tst_instances_mof, capsys):
        # pylint: disable=no-self-use
        """
        Test the display of the repository with it various options.
        This is done in a single test method for simplicity
        """
        skip_if_moftab_regenerated()
        # Create the objects in all namespaces
        namespaces = INITIAL_NAMESPACES
        for ns in namespaces:
            conn.compile_mof_string(tst_instances_mof, namespace=ns)
        print('')  # required to force output from capsys for some reason
        # Test basic display repo output
        conn.display_repository()
        captured = capsys.readouterr()

        result = captured.out
        print('RESULT\n%s' % result)

        assert result.startswith(
            "\n// ========Mock Repo Display fmt=mof namespaces=all")
        assert "class CIM_Foo_sub_sub : CIM_Foo_sub {" in result
        assert "instance of CIM_Foo {" in result
        for ns in namespaces:
            assert _format("// Namespace {0!A}: contains 11 Qualifier "
                           "Declarations", ns) \
                in result
            assert _format("// Namespace {0!A}: contains 5 Classes", ns) \
                in result
            assert _format("// Namespace {0!A}: contains 12 Instances", ns) \
                in result
        assert "Qualifier Abstract : boolean = false," in result

        # Confirm that the display formats work
        for param in ('xml', 'mof', 'repr'):
            conn.display_repository(output_format=param)
            captured = capsys.readouterr()
            assert captured.out

        # confirm that the two repositories exist
        conn.display_repository(namespaces=namespaces)
        captured = capsys.readouterr()
        assert captured.out

        # test with a defined namespace
        ns = namespaces[0]
        conn.display_repository(namespaces=[ns])
        captured = capsys.readouterr()
        assert captured.out

        conn.display_repository(namespaces=ns)
        captured = capsys.readouterr()
        assert captured.out

        # test for invalid output_format
        with pytest.raises(ValueError):
            conn.display_repository(output_format='blah')
            captured = capsys.readouterr()
            assert captured.out

        conn.display_repository(summary=True)
        captured = capsys.readouterr()
        result = captured.out
        assert "Mock Repo Display fmt=mof namespaces=all" in result
        assert "Namespace 'root/cimv2': contains 5 Classes" in result
        assert "Namespace 'root/cimv2': contains 12 Instances" in result

    def test_display_repo_tofile(self, conn, tst_instances_mof):
        # pylint: disable=no-self-use
        """
        Test output of the display_repository method to a file.
        """
        skip_if_moftab_regenerated()
        conn.compile_mof_string(tst_instances_mof, namespace=DEFAULT_NAMESPACE)

        tst_file_name = 'test_wbemconnection_mock_repo.txt'
        tst_file = os.path.join(TEST_DIR, tst_file_name)

        # The code to be tested
        conn.display_repository(dest=tst_file)

        assert os.path.isfile(tst_file)
        with io.open(tst_file, 'r', encoding='utf-8') as f:
            data = f.read()
        # test key parts of resulting file.
        assert data.startswith(
            "// ========Mock Repo Display fmt=mof namespaces=all")
        assert 'class CIM_Foo_sub_sub : CIM_Foo_sub {' in data
        assert "NAMESPACE 'root/cimv2'" in data
        assert "Namespace 'root/cimv2': contains 11 Qualifier Declarations" \
            in data
        assert 'instance of CIM_Foo {' in data
        assert 'Qualifier Abstract : boolean = false,' in data
        assert "// Namespace 'root/cimv2': contains 5 Classes" in data
        assert "class CIM_Foo {" in data

        assert '[Description ( "blah blah" )]' in data
        assert "class CIM_Foo_nokey {" in data
        assert "class CIM_Foo_sub_sub : CIM_Foo_sub {" in data
        assert "// Namespace 'root/cimv2': contains 12 Instances" in data
        assert 'cimfoo_sub_sub = "data sub_sub3";' in data
        assert "// ============End Repository=================" in data
        os.remove(tst_file)

    @pytest.mark.parametrize(
        "ns", INITIAL_NAMESPACES + [None])
    def test_addcimobject(self, conn, tst_classeswqualifiers, tst_instances,
                          tst_insts_big, tst_classes, ns):
        # pylint: disable=no-self-use
        """
        Test inserting all of the object definitions in the fixtures into
        the repository
        """

        # The code to be tested
        conn.add_cimobjects(tst_classeswqualifiers, namespace=ns)
        conn.add_cimobjects(tst_instances, namespace=ns)
        conn.add_cimobjects(tst_insts_big, namespace=ns)

        exp_ns = ns or conn.default_namespace

        class_store = conn.cimrepository.get_class_store(exp_ns)
        assert class_store.len() == len(tst_classes)

        instance_store = conn.cimrepository.get_instance_store(exp_ns)
        assert instance_store.len() == len(tst_instances) + len(tst_insts_big)

    @pytest.mark.parametrize(
        "ns", INITIAL_NAMESPACES + [None])
    @pytest.mark.parametrize(
        "tst_objs, exp_exec, condition",
        [
            # Instance with no path
            [
                CIMInstance('CIM_Foo',
                            properties={'InstanceID': "Instance no path"}),
                ValueError, True,
            ],


            [
                CIMMethod("Blah", "string"), AssertionError, True
            ],
        ]
    )
    def test_addcimobject_err(self, conn, tst_classeswqualifiers, tst_instances,
                              ns,
                              tst_objs, exp_exec, condition):
        """
        Test error cases with the addcimobject function.
        """
        # pylint: disable=no-self-use
        if not condition:
            pytest.skip("This test marked to be skipped by condition")

        if condition == 'pdb':
            import pdb  # pylint: disable=import-outside-toplevel
            pdb.set_trace()  # pylint: disable=forgotten-debug-statement

        conn.add_cimobjects(tst_classeswqualifiers, namespace=ns)
        conn.add_cimobjects(tst_instances, namespace=ns)

        if exp_exec:
            with pytest.raises(exp_exec):
                conn.add_cimobjects(tst_objs, namespace=ns)
        else:
            conn.add_cimobjects(tst_objs, namespace=ns)

    @pytest.mark.parametrize(
        "ns", INITIAL_NAMESPACES + [None])
    def test_addcimobject_duperr(self, conn, tst_classeswqualifiers,
                                 tst_instances, ns):
        # pylint: disable=no-self-use
        """Test error if duplicate instance inserted"""
        conn.add_cimobjects(tst_classeswqualifiers, namespace=ns)
        conn.add_cimobjects(tst_instances, namespace=ns)
        with pytest.raises(ValueError):

            # The code to be tested
            conn.add_cimobjects(tst_instances, namespace=ns)

    @pytest.mark.parametrize(
        "ns", INITIAL_NAMESPACES + [None])
    def test_addcimobject_err1(self, conn, tst_classeswqualifiers, ns):
        # pylint: disable=no-self-use
        """Test error if class with no superclass"""
        conn.add_cimobjects(tst_classeswqualifiers, namespace=ns)
        c = CIMClass('CIM_BadClass', superclass='CIM_NotExist')
        with pytest.raises(ValueError):

            # The code to be tested
            conn.add_cimobjects(c, namespace=ns)

    @pytest.mark.parametrize(
        "ns", INITIAL_NAMESPACES + [None])
    def test_compile_qualifiers(self, conn, tst_qualifiers_mof, ns):
        # pylint: disable=no-self-use
        """
        Test compile qualifiers with namespace from mof
        """
        skip_if_moftab_regenerated()

        # The code to be tested
        conn.compile_mof_string(tst_qualifiers_mof, ns)

        assert conn.GetQualifier(
            'Association', namespace=ns).name == 'Association'
        assert conn.GetQualifier(
            'Indication', namespace=ns).name == 'Indication'
        assert conn.GetQualifier('Abstract', namespace=ns).name == 'Abstract'
        assert conn.GetQualifier('Aggregate', namespace=ns).name == 'Aggregate'
        assert conn.GetQualifier('Key', namespace=ns).name == 'Key'

        quals = conn.EnumerateQualifiers(namespace=ns)
        assert len(quals) == 11

    @pytest.mark.parametrize(
        "default_ns, additional_ns, in_ns, exp_ns, exp_exc",
        [
            # default_ns: Default namespace to be added to CIM repo
            # additional_ns: List of additional namespacse to be added to repo
            # in_ns: Namespace input parameter for add_namespace() to be tested
            # exp_ns: None, or resulting namespace after adding it to repo
            # exp_exc: None, or expected exception object

            ('root/def', [], 'root/blah', 'root/blah', None),
            ('root/def', [], '//root/blah//', 'root/blah', None),
            ('root/def', ['root/foo'], 'root/blah', 'root/blah', None),
            ('root/def', ['root/blah'], 'root/blah', None,
             CIMError(CIM_ERR_ALREADY_EXISTS)),
            ('root/def', [], None, None, ValueError()),
        ]
    )
    def test_add_namespace(self, default_ns, additional_ns, in_ns, exp_ns,
                           exp_exc):
        # pylint: disable=no-self-use
        """
        Test add_namespace(). This tests the methods for managing namespaces
        in the FakedWBEMConnection class
        """
        conn = FakedWBEMConnection()
        conn.add_namespace(default_ns)
        for ns in additional_ns:
            conn.add_namespace(ns)
        if not exp_exc:

            # The code to be tested
            conn.add_namespace(in_ns)

            assert exp_ns in conn.namespaces
        else:
            with pytest.raises(type(exp_exc)) as exec_info:

                # The code to be tested
                conn.add_namespace(in_ns)

            exc = exec_info.value
            if isinstance(exp_exc, CIMError):
                assert exc.status_code == exp_exc.status_code

    @pytest.mark.parametrize(
        "default_ns, additional_ns, in_ns, exp_ns, exp_exc",
        [
            # default_ns: Default namespace to be added to CIM repo
            # additional_ns: List of additional namespacse to be added to repo
            # in_ns: Namespace input parameter for remove_namespace() to be
            #        tested
            # exp_ns: None, or namespace that was removed, for checking in repo
            # exp_exc: None, or expected exception object

            ('root/def', ['root/blah'], 'root/blah', 'root/blah', None),
            ('root/def', ['root/blah'], '//root/blah//', 'root/blah', None),
            ('root/def', ['root/blah', 'root/foo'], 'root/blah', 'root/blah',
             None),
            ('root/def', [], 'root/blah', None, CIMError(CIM_ERR_NOT_FOUND)),
            ('root/def', [], None, None, ValueError()),
        ]
    )
    def test_remove_namespace(self, default_ns, additional_ns, in_ns, exp_ns,
                              exp_exc):
        # pylint: disable=no-self-use
        """
        Test _remove_namespace()
        """
        conn = FakedWBEMConnection()
        conn.add_namespace(default_ns)
        for ns in additional_ns:
            conn.add_namespace(ns)

        if not exp_exc:

            # The code to be tested
            conn.remove_namespace(in_ns)

            assert exp_ns not in conn.namespaces
        else:
            with pytest.raises(type(exp_exc)) as exec_info:

                # The code to be tested
                conn.remove_namespace(in_ns)

            exc = exec_info.value
            if isinstance(exp_exc, CIMError):
                assert exc.status_code == exp_exc.status_code

    def test_unicode(self, conn):
        # pylint: disable=no-self-use
        """
        Test compile and display repository with unicode in MOF string
        """
        ns = DEFAULT_NAMESPACE

        qmof = """
        Qualifier Description : string = null,
            Scope(any),
            Flavor(EnableOverride, ToSubclass, Translatable);

        Qualifier Key : boolean = false,
            Scope(property, reference),
            Flavor(DisableOverride, ToSubclass);
        """

        cmof = u"""
        class CIM_Foo {
                [Key,
                 Description ("\u212b \u0420\u043e\u0441\u0441\u0438"
                              "\u044f\u00E0 voil\u00e0")]
            string InstanceID;
        };
        """
        skip_if_moftab_regenerated()

        conn.compile_mof_string(qmof, ns)
        conn.compile_mof_string(cmof, ns)

        with OutputCapture():
            conn.display_repository()
        tst_file_name = 'test_wbemconnection_mock_repo_unicode.txt'
        tst_file = os.path.join(TEST_DIR, tst_file_name)

        conn.display_repository(dest=tst_file)
        assert os.path.isfile(tst_file)
        os.remove(tst_file)

    @pytest.mark.parametrize(
        "ns", INITIAL_NAMESPACES + [None])
    def test_compile_mult(self, conn, ns):
        # pylint: disable=no-self-use
        """
        Test compile of multiple separate compile units including qualifiers,
        classes and instances.
        """

        exp_ns = ns or conn.default_namespace

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

        i4 = """
        instance of CIM_Foo { InstanceID = "CIM_Foo4"; };
        """
        skip_if_moftab_regenerated()

        conn.compile_mof_string(q1, ns)
        qual_repo = conn.cimrepository.get_qualifier_store(exp_ns)

        assert qual_repo.object_exists('Association')
        conn.compile_mof_string(q2, ns)

        qual_repo = conn.cimrepository.get_qualifier_store(exp_ns)

        assert qual_repo.object_exists('Association')
        assert qual_repo.object_exists('Description')
        assert qual_repo.object_exists('Key')

        assert conn.GetQualifier('Association', namespace=ns)
        assert conn.GetQualifier('Description', namespace=ns)

        conn.compile_mof_string(c1, ns)
        assert conn.GetClass('CIM_Foo', namespace=ns, LocalOnly=False,
                             IncludeQualifiers=True, IncludeClassOrigin=True)

        conn.compile_mof_string(c2, ns)
        assert conn.GetClass('CIM_Foo_sub', namespace=ns)

        conn.compile_mof_string(i1, ns)
        rslt_inst_names = conn.EnumerateInstanceNames('CIM_Foo', namespace=ns)
        assert len(rslt_inst_names) == 1
        conn.compile_mof_string(i2, ns)
        rslt_inst_names = conn.EnumerateInstanceNames('CIM_Foo', namespace=ns)
        assert len(rslt_inst_names) == 2
        conn.compile_mof_string(i3, ns)
        rslt_inst_names = conn.EnumerateInstanceNames('CIM_Foo', namespace=ns)
        assert len(rslt_inst_names) == 3
        conn.compile_mof_string(i4, ns)
        rslt_inst_names = conn.EnumerateInstanceNames('CIM_Foo', namespace=ns)
        assert len(rslt_inst_names) == 4
        for name in rslt_inst_names:
            inst = conn.GetInstance(name)
            assert inst.classname == 'CIM_Foo'

        for id_ in ['CIM_Foo4', 'CIM_Foo3', 'CIM_Foo2', 'CIM_Foo1']:
            iname = CIMInstanceName('CIM_Foo',
                                    keybindings={'InstanceID': id_},
                                    namespace=exp_ns)
            assert iname in rslt_inst_names

    @pytest.mark.parametrize(
        "ns", INITIAL_NAMESPACES + [None])
    def test_compile_classes(self, conn, tst_classes_mof, ns):
        # pylint: disable=no-self-use
        """
        Test compile of classes into the repository
        """
        skip_if_moftab_regenerated()

        # The code to be tested
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
        assert set(clns) == set([cl_.classname for cl_ in cls])

    def test_compile_classes_multiple_ns(self, conn, tst_classes_mof):
        # pylint: disable=no-self-use
        """
        Test compile of classes into multiple namespaces where the input
        is both the qualifier declarations and the classes.
        """
        skip_if_moftab_regenerated()

        # The code to be tested
        ns = conn.default_namespace
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
        assert set(clns) == set([cl_.classname for cl_ in cls])

        quals = conn.EnumerateQualifiers()

        # Compile into second repository added by add_namespaces
        ns = 'interop'
        conn.add_namespace(ns)
        conn.compile_mof_string(tst_classes_mof, namespace=ns)

        assert conn.EnumerateQualifiers(namespace=ns) == quals
        assert clns == conn.EnumerateClassNames(namespace=ns,
                                                DeepInheritance=True)

    def test_compile_classes_nspragma(self, conn, tst_classes_mof):
        # pylint: disable=no-self-use
        """
        Test compile of classes into multiple namespaces using the
        namespace pragma.
        """
        skip_if_moftab_regenerated()

        # The code to be tested
        ns = conn.default_namespace
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
        assert set(clns) == set([cl_.classname for cl_ in cls])

        quals = conn.EnumerateQualifiers()

        # Compile into second repository added by add_namespaces and with
        # the namespace pragma in the mof
        ns = 'new_namespace'
        conn.add_namespace(ns)
        new_class_mof = '#pragma namespace ("{}")'.format(ns) + tst_classes_mof
        conn.compile_mof_string(new_class_mof, namespace=ns)

        assert conn.EnumerateQualifiers(namespace=ns) == quals
        assert clns == conn.EnumerateClassNames(namespace=ns,
                                                DeepInheritance=True)

    def test_compile_classes_nspragma_2(self, conn, tst_classes_mof):
        # pylint: disable=no-self-use
        """
        Test compile of classes into multiple namespaces using the
        namespace pragma but without the namespace defined in the
        conn.compile_mof_string method call
        """
        skip_if_moftab_regenerated()

        # The code to be tested
        ns = conn.default_namespace
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
        assert set(clns) == set([cl_.classname for cl_ in cls])

        quals = conn.EnumerateQualifiers()

        # Compile into second repository added by add_namespaces and with
        # the namespace pragma in the mof
        ns = 'new_namespace'
        conn.add_namespace(ns)
        new_class_mof = '#pragma namespace ("{}")'.format(ns) + tst_classes_mof
        # Compile without the ns parameter. The pragma should determine
        # the namespace
        conn.compile_mof_string(new_class_mof)

        assert conn.EnumerateQualifiers(namespace=ns) == quals
        assert clns == conn.EnumerateClassNames(namespace=ns,
                                                DeepInheritance=True)

    def test_compile_classes_nspragma_err1(self, conn, tst_classes_mof):
        # pylint: disable=no-self-use
        """
        Test compile of classes into multiple namespaces where second
        namespace not created. Generates error
        """
        pytest.skip("This test fails. See issue #2575 ")
        skip_if_moftab_regenerated()
        ns = conn.default_namespace
        conn.compile_mof_string(tst_classes_mof, namespace=ns)

        # Compile into second repository added by add_namespaces and with
        # the namespace pragma in the mof
        conn.add_namespace('interop')
        ns = 'new_namespace'
        new_class_mof = '#pragma namespace ("{}")'.format(ns) + tst_classes_mof
        # Compile without the ns parameter and namespace does not exist.
        # should fail.
        try:
            conn.compile_mof_string(new_class_mof)

        except MOFParseError:
            return

    def test_compile_classes_nspragma_err2(self, conn, tst_classes_mof):
        # pylint: disable=no-self-use
        """
        Test compile of classes into multiple namespaces where second
        namespace not created. Generates error
        """
        pytest.skip("This test fails. See issue #2575 ")
        skip_if_moftab_regenerated()
        ns = conn.default_namespace
        conn.compile_mof_string(tst_classes_mof, namespace=ns)

        # Compile into second repository added by add_namespaces and with
        # the namespace pragma in the mof with no interop namespace defined.
        ns = 'new_namespace'
        new_class_mof = '#pragma namespace ("{}")'.format(ns) + tst_classes_mof
        # Compile without the ns parameter and namespace does not exist.
        # should fail.
        try:
            conn.compile_mof_string(new_class_mof)

        except MOFParseError:
            return

    @pytest.mark.parametrize(
        "ns", INITIAL_NAMESPACES + [None])
    def test_compile_instances(self, conn, tst_classes_mof, ns):
        # pylint: disable=no-self-use
        """
        Test compile of instance MOF into the repository in single file with
        classes.
        """

        skip_if_moftab_regenerated()

        tst_ns = ns or conn.default_namespace
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

        # The code to be tested
        conn.compile_mof_string(all_mof, namespace=ns)

        rslt_inst_names = conn.EnumerateInstanceNames('CIM_Foo', namespace=ns)
        assert len(rslt_inst_names) == 2

        for name in rslt_inst_names:
            inst = conn.GetInstance(name)
            assert inst.classname == 'CIM_Foo'

        for id_ in ['Alice', 'Bob']:
            iname = CIMInstanceName('CIM_Foo',
                                    keybindings={'InstanceID': id_},
                                    namespace=tst_ns)
            assert iname in rslt_inst_names

    @pytest.mark.parametrize(
        "ns", INITIAL_NAMESPACES + [None])
    def test_compile_assoc_mof(self, conn, tst_assoc_mof,
                               tst_person_instance_names, ns):
        # pylint: disable=no-self-use
        """
        Test the  tst_assoc_mof compiled MOF to confirm compiled correct
        classes and instances.
        """

        skip_if_moftab_regenerated()

        # The code to be tested
        conn.compile_mof_string(tst_assoc_mof, namespace=ns)

        clns = conn.EnumerateClassNames(namespace=ns, DeepInheritance=True)

        assert 'TST_Person' in clns
        assert 'TST_Lineage' in clns
        assert 'TST_Personsub' in clns
        assert 'TST_MemberOfFamilyCollection' in clns
        assert 'TST_FamilyCollection' in clns
        assert len(clns) == 5

        inst_names = conn.EnumerateInstanceNames('TST_Person', namespace=ns)
        assert len(inst_names) == TST_PERSONWITH_SUB_INST_COUNT
        insts = conn.EnumerateInstances('TST_Person', namespace=ns)
        assert len(inst_names) == TST_PERSONWITH_SUB_INST_COUNT

        # Test for particular instances in the enum response
        for name in tst_person_instance_names:
            result = [inst for inst in insts
                      if inst.classname == 'TST_Person' and
                      inst['name'] == name]
            assert len(result) == 1

        # test GetInstance
        for name in tst_person_instance_names:
            kb = {'name': name}
            inst_name = CIMInstanceName('TST_Person', kb, namespace=ns)
            conn.GetInstance(inst_name)

        inst_names = conn.EnumerateInstanceNames('TST_Lineage', namespace=ns)
        assert len(inst_names) == 3
        insts = conn.EnumerateInstances('TST_Lineage', namespace=ns)
        assert len(inst_names) == 3

        insts_dict = {}
        for inst in insts:
            insts_dict[inst.path] = inst

        # compare EnumerateInstances and GetInstance returns
        for inst_name in inst_names:
            inst = conn.GetInstance(inst_name)
            assert inst == insts_dict[inst.path]

    def test_compile_complete_dmtf_schema(self, conn):
        # pylint: disable=no-self-use
        """
        Test Compiling the complete DMTF CIM schema. This test compiles all
        classes of  the DMTF schema that is defined in the test suite.
        """
        skip_if_moftab_regenerated()

        ns = 'root/cimv2'
        # install the schema if necessary.
        dmtf_schema = install_test_dmtf_schema()

        # The code to be tested
        conn.compile_mof_file(dmtf_schema.schema_pragma_file, namespace=ns,
                              search_paths=[dmtf_schema.schema_mof_dir])

        assert conn.cimrepository.get_class_store(ns).len() == TOTAL_CLASSES
        assert conn.cimrepository.get_qualifier_store(ns).len() == \
            TOTAL_QUALIFIERS

    @pytest.mark.parametrize(
        "desc, classnames, extra_exp_classnames, exp_class, condition",
        [
            # Description - Description of the test
            # classnames - List of classnames to compile
            # extra_exp_classnames - Dependent classnames that will be compiled
            #              in addition to the classes in classnames
            # exp_class - CIMClass defining expected class as compiled
            #             (optional) If this exists the compiled class must
            #             match this
            # run_test - If True, execute the test
            ["Test with several classes. ",
             ['CIM_RegisteredProfile', 'CIM_Namespace', 'CIM_ObjectManager',
              'CIM_ElementConformsToProfile', 'CIM_ReferencedProfile'],
             ['CIM_EnabledLogicalElement', 'CIM_Job',
              'CIM_LogicalElement', 'CIM_ManagedSystemElement',
              'CIM_Service', 'CIM_Service', 'CIM_ConcreteJob',
              'CIM_Dependency', 'CIM_ManagedElement', 'CIM_ManagedElement',
              'CIM_Error', 'CIM_RegisteredSpecification',
              'CIM_ReferencedSpecification', 'CIM_WBEMService'],
             None,
             OK],

            ["Test with single classes. Broken",
             ['CIM_ObjectManager'],
             ['CIM_EnabledLogicalElement', 'CIM_Error', 'CIM_LogicalElement',
              'CIM_ConcreteJob', 'CIM_WBEMService',
              'CIM_ManagedSystemElement', 'CIM_Service',
              'CIM_ManagedElement', 'CIM_Job'],
             None,
             OK],

            ["Test with simple group of classes",
             ['CIM_ElementConformsToProfile'],
             ['CIM_ManagedElement',
              'CIM_RegisteredSpecification', 'CIM_RegisteredProfile'],
             None,
             OK],

            ["Test with single class",
             ['CIM_RegisteredProfile'],
             ['CIM_ManagedElement', 'CIM_RegisteredSpecification'],
             None,
             OK],

            ["Test with single association. Confirms assoc dependents",
             ['CIM_ProductComponent'],
             ['CIM_Component', 'CIM_ManagedElement', 'CIM_ProductComponent',
              'CIM_Product'],
             None,
             OK],

            ["Test with class that passes Caption",
             ['CIM_FileServerCapabilities'],
             ['CIM_ManagedElement', 'CIM_Capabilities', 'CIM_SettingData'],
             None,
             OK],

            ["Test with class that has embeddedinstance (CIM_SettingData",
             ['CIM_Capabilities'],
             ['CIM_ManagedElement', 'CIM_SettingData'],
             None,
             OK],

            ["Test compile of Association subclass",
             ['CIM_HostedDependency'],
             ['CIM_Dependency', 'CIM_ManagedElement', ],
             CIMClass(
                 classname='CIM_HostedDependency',
                 superclass='CIM_Dependency',
                 properties=NocaseDict({
                     'Antecedent': CIMProperty(
                         name='Antecedent', value=None, type='reference',
                         reference_class='CIM_ManagedElement',
                         embedded_object=None, is_array=False, array_size=None,
                         class_origin='CIM_Dependency',
                         propagated=True,
                         qualifiers=NocaseDict({
                             'Override': CIMQualifier(
                                 name='Override', value='Antecedent',
                                 type='string', tosubclass=False,
                                 overridable=True,
                                 translatable=None, toinstance=None,
                                 propagated=False),
                             'Max': CIMQualifier(
                                 name='Max', value=1,
                                 type='uint32',
                                 tosubclass=True, overridable=True,
                                 translatable=None,
                                 toinstance=None, propagated=False),
                             'Description': CIMQualifier(
                                 name='Description',
                                 value='The scoping ManagedElement.',
                                 type='string',
                                 tosubclass=True, overridable=True,
                                 translatable=True,
                                 toinstance=None, propagated=False),
                             'Key': CIMQualifier(
                                 name='Key',
                                 value=True, type='boolean',
                                 tosubclass=True, overridable=False,
                                 translatable=None,
                                 toinstance=None, propagated=True)})),
                     'Dependent': CIMProperty(
                         name='Dependent', value=None, type='reference',
                         reference_class='CIM_ManagedElement',
                         embedded_object=None, is_array=False,
                         array_size=None,
                         class_origin='CIM_Dependency',
                         propagated=True,
                         qualifiers=NocaseDict({
                             'Override': CIMQualifier(
                                 name='Override', value='Dependent',
                                 type='string', tosubclass=False,
                                 overridable=True,
                                 translatable=None, toinstance=None,
                                 propagated=False),
                             'Description': CIMQualifier(
                                 name='Description',
                                 value='The hosted ManagedElement.',
                                 type='string',
                                 tosubclass=True, overridable=True,
                                 translatable=True,
                                 toinstance=None, propagated=False),
                             'Key': CIMQualifier(
                                 name='Key',
                                 value=True, type='boolean',
                                 tosubclass=True, overridable=False,
                                 translatable=None,
                                 toinstance=None, propagated=True)}))}),
                 methods=NocaseDict({}),
                 qualifiers=NocaseDict({
                     'Association': CIMQualifier(
                         name='Association', value=True,
                         type='boolean', tosubclass=True,
                         overridable=False,
                         translatable=None, toinstance=None,
                         propagated=False),
                     'Version': CIMQualifier(
                         name='Version', value='2.8.0',
                         type='string', tosubclass=False,
                         overridable=True,
                         translatable=True, toinstance=None,
                         propagated=False),
                     'UMLPackagePath': CIMQualifier(
                         name='UMLPackagePath',
                         value='CIM::Core::CoreElements',
                         type='string',
                         tosubclass=True, overridable=True,
                         translatable=None,
                         toinstance=None, propagated=False),
                     'Description': CIMQualifier(
                         name='Description',
                         value='HostedDependency defines a '
                               'ManagedElement in the '
                               'context of another '
                               'ManagedElement in which it '
                               'resides.',
                         type='string', tosubclass=True,
                         overridable=True,
                         translatable=True, toinstance=None,
                         propagated=False)}),
                 path=CIMClassName(classname='CIM_HostedDependency',
                                   namespace='root/cimv2',
                                   host='FakedUrl:5988')),
             OK],
        ]
    )
    def test_compile_schema_classes(self, conn, desc, classnames,
                                    extra_exp_classnames, exp_class, condition):
        # pylint: disable=no-self-use,unused-argument
        """
        Test Compiling DMTF CIM schema using the compile_schema_classes method.
        Optionally compare one of the returned classes against the
        class defined in exp_class.  This test is specifically to assure
        that things like propagated, etc. are correct as compiled and
        installed in the repo.
        """
        if not condition:
            pytest.skip("This test marked to be skipped by condition")

        skip_if_moftab_regenerated()

        ns = 'root/cimv2'
        schema = DMTFCIMSchema(DMTF_TEST_SCHEMA_VER, TESTSUITE_SCHEMA_DIR,
                               verbose=False)

        # The code to be tested
        conn.compile_schema_classes(classnames,
                                    schema.schema_pragma_file,
                                    verbose=VERBOSE)

        # Test the set of created classnames for match to exp_classnames
        exp_classnames = classnames
        exp_classnames.extend(extra_exp_classnames)
        rslt_classnames = conn.EnumerateClassNames(DeepInheritance=True,
                                                   namespace=ns)
        assert set(exp_classnames) == set(rslt_classnames)

        # If exp_class exists compare the exp_class to the created class
        if exp_class:
            get_cl = conn.GetClass(exp_class.classname, namespace=ns,
                                   IncludeQualifiers=True,
                                   IncludeClassOrigin=True,
                                   LocalOnly=False)
            assert get_cl == exp_class

    def test_compile_part_schema_multiple_ns(self, conn):
        # pylint: disable=no-self-use
        """
        Test compiling schema components in multiple namespaces. This tests
        the capability to install a simple schema model into the
        default and other namespaces. Compares a single class from each
        namespace for equality
        """
        skip_if_moftab_regenerated()

        schema = DMTFCIMSchema(DMTF_TEST_SCHEMA_VER, TESTSUITE_SCHEMA_DIR,
                               verbose=False)

        test_class = 'CIM_ComputerSystem'
        classnames = [test_class]

        # Compile into first namespace, the default
        ns = conn.default_namespace
        # The code to be tested
        conn.compile_schema_classes(classnames,
                                    schema.schema_pragma_file,
                                    namespace=ns)
        cls_rtn1 = conn.GetClass(test_class)
        cls_rtn1.path = None
        class_count1 = len(conn.EnumerateClassNames())
        quals = conn.EnumerateQualifiers()

        # Compile into second namespace
        ns = 'interop'
        # The namespace must exist before compile_schema_classes called.
        conn.add_namespace(ns)
        conn.compile_schema_classes(classnames,
                                    schema.schema_pragma_file,
                                    namespace=ns)

        cls_rtn2 = conn.GetClass(test_class, namespace=ns)
        cls_rtn2.path = None
        assert cls_rtn1 == cls_rtn2
        assert quals == conn.EnumerateQualifiers(namespace=ns)

        assert len(conn.EnumerateClassNames(namespace=ns)) == class_count1

        ns = 'sampleuser'
        # The namespace must exist before compile_schema_classes called.
        conn.add_namespace(ns)
        conn.compile_schema_classes(classnames,
                                    schema.schema_pragma_file,
                                    namespace=ns)
        assert quals == conn.EnumerateQualifiers(namespace=ns)

        cls_rtn3 = conn.GetClass(test_class, namespace=ns)
        cls_rtn3.path = None
        assert cls_rtn3 == cls_rtn1

    def test_compile_err(self, conn):
        # pylint: disable=no-self-use
        """
        Test compile that has an error
        """
        q1 = """
            Qualifier Association : boolean = false,
                Scope(associations),
                Flavor(DisableOverride, ToSubclass);
        """
        skip_if_moftab_regenerated()

        with pytest.raises(MOFCompileError) as exec_info:

            # The code to be tested
            conn.compile_mof_string(q1)

        exc = exec_info.value
        assert re.search(r"MOF grammar error", exc.msg, re.IGNORECASE)

    @pytest.mark.skip(reason="Fails because does not allow dup")
    @pytest.mark.parametrize(
        "ns", INITIAL_NAMESPACES + [None])
    def test_compile_instances_dup(self, conn, tst_classes_mof, ns):
        # pylint: disable=no-self-use
        """
        Test compile of instance MOF  with duplicate keys into the repository
        fails
        """

        skip_if_moftab_regenerated()

        tst_ns = ns or conn.default_namespace
        insts_mof = """
            instance of CIM_Foo_sub as $Alice {
                InstanceID = "Alice";
                cimfoo_sub = "one";
            };
            instance of CIM_Foo_sub as $Alice1 {
                InstanceID = "Alice";
                cimfoo_sub = "two";
            };
            """

        # compile as single unit by combining classes and instances
        # The compiler builds the instance paths.
        conn.compile_mof_string(tst_classes_mof, namespace=tst_ns)

        # The code to be tested
        conn.compile_mof_string(insts_mof, namespace=tst_ns)

        insts = conn.EnumerateInstances('CIM_Foo_sub')

        # test replacement occurred.
        assert len(insts) == 1
        assert insts[0].get('cimfoo_sub') == 'two'
        conn.GetInstance(CIMInstanceName('CIM_Foo_sub',
                                         {'InstanceID': 'Alice'},
                                         namespace=tst_ns))


class UserInstanceTestProvider(InstanceWriteProvider):
    """
    Basic user provider implements CreateInstance and DeleteInstance
    """
    provider_classnames = 'CIM_Foo'

    def __init__(self, cimrepository):
        """
        Init of test provider
        """
        super(UserInstanceTestProvider, self).__init__(cimrepository)

    def __repr__(self):
        return _format(
            "UserInstanceTestProvider("
            "provider_type={s.provider_type}, "
            "provider_classnames={s.provider_classnames})",
            s=self)

    def CreateInstance(self, namespace, new_instance):
        """Test Create instance just calls super class method"""
        # pylint: disable=useless-super-delegation
        return super(UserInstanceTestProvider, self).CreateInstance(
            namespace, new_instance)

    def DeleteInstance(self, InstanceName):
        """Test Create instance just calls super class method"""
        # pylint: disable=useless-super-delegation
        return super(UserInstanceTestProvider, self).DeleteInstance(
            InstanceName)


class UserInstanceTestProvider2(InstanceWriteProvider):
    """
    User provider defined to server multiple classes. This class does
    not include ModifyInstance().
    """
    provider_classnames = ['CIM_Foo', 'CIM_Foo_Sub']

    def __init__(self, cimrepository):
        """
        Init of test provider
        """
        super(UserInstanceTestProvider2, self).__init__(cimrepository)

    def __repr__(self):
        return _format(
            "UserInstanceTestProvider2("
            "provider_type={s.provider_type}, "
            "provider_classnames={s.provider_classnames})",
            s=self)

    def CreateInstance(self, namespace, new_instance):
        """Test Create instance just calls super class method"""
        # pylint: disable=useless-super-delegation
        return super(UserInstanceTestProvider2, self).CreateInstance(
            namespace, new_instance)

    def DeleteInstance(self, InstanceName):
        """Test Create instance just calls super class method"""
        # pylint: disable=useless-super-delegation
        return super(UserInstanceTestProvider2, self).DeleteInstance(
            InstanceName)


class UserMethodTestProvider(MethodProvider):
    """
    Basic method provider implements InvokeMethod()
    """
    provider_classnames = 'CIM_Foo'

    def __init__(self, cimrepository):
        """
        Init of test provider
        """
        super(UserMethodTestProvider, self).__init__(cimrepository)

    def __repr__(self):
        return _format(
            "UserMethodTestProvider("
            "provider_type={s.provider_type}, "
            "provider_classnames={s.provider_classnames})",
            s=self)

    def InvokeMethod(self, methodname, localobject, params):
        """Test InvokeMethod provider with InvokeMethod"""
        # return return-value 0 and no output parameters
        return (0, None)


class TestUserDefinedProviders(object):
    """
    Test the repository support for use of user providers that are
    registered and substituted for the default provider.
    """

    @pytest.mark.parametrize(
        "ns", INITIAL_NAMESPACES + [None])
    @pytest.mark.parametrize(
        "desc, inputs, exp_exc, condition",
        [
            # desc: Description of testcase
            # inputs - list of lists where the inner lists contain the
            #          parameters of a single request(testnamespaces,
            #          lclassnames provider_type, provider)
            #          * tns -testnamespaces - Namespace or list of namespaces
            #            in which provider is to be registered
            #          * pr -provider object
            #          * exp_ns -expected namespaces defined by provider
            #          * exp_type - expected provider_type
            # exp_exc - Exception object if one is expected
            # condition - test condition (True, False, 'pdb')

            ["validate ns='root/cimv2', etc.",
             [["root/cimv3", UserInstanceTestProvider, 'CIM_Foo',
               'instance-write']],
             None, OK],

            ["validate  ns='root/cimv2x' fails",
             [["root/cimv2x", UserInstanceTestProvider, 'CIM_Foo',
               'instance-write']],
             ValueError(), OK],
        ]
    )
    def test_register_provider(self, conn, tst_classeswqualifiersandinsts,
                               ns, desc, inputs, exp_exc, condition):
        # pylint: disable=no-self-use,unused-argument
        """
        Test register_provider method.
        """
        if not condition:
            pytest.skip("This test marked to be skipped by condition")
        skip_if_moftab_regenerated()

        if condition == "pdb":
            import pdb  # pylint: disable=import-outside-toplevel
            pdb.set_trace()  # pylint: disable=forgotten-debug-statement

        add_objects_to_repo(conn, ns, tst_classeswqualifiersandinsts)

        if exp_exc is None:
            for item in inputs:
                tst_ns = item[0]
                add_objects_to_repo(conn, tst_ns,
                                    [tst_classeswqualifiersandinsts])
                provider = item[1]

                # The code to be tested
                conn.register_provider(provider(conn.cimrepository), tst_ns)

            assert provider.provider_type == 'instance-write'
            provider_classnames = provider.provider_classnames

            if not isinstance(provider_classnames, (list, tuple)):
                provider_classnames = [provider_classnames]

            if isinstance(tst_ns, six.string_types):
                tst_ns = [tst_ns]

            if not tst_ns:
                tst_ns = [conn.default_namespace]

            # pylint: disable=protected-access
            reg_ns = [n.lower() for n in
                      conn._provider_registry.provider_namespaces()]
            for _ns in tst_ns:
                assert _ns.lower() in reg_ns
                # pylint: disable=protected-access
                exp_clns = [c.lower() for c in
                            conn._provider_registry.provider_classes(_ns)]
                for cln in provider_classnames:
                    assert cln.lower() in exp_clns

        else:
            with pytest.raises(type(exp_exc)):
                for item in inputs:
                    tst_ns = item[0]
                    provider = item[1]

                    # The code to be tested
                    conn.register_provider(provider(conn.cimrepository),
                                           namespaces=tst_ns)

    @pytest.mark.parametrize(
        "ns", INITIAL_NAMESPACES + [None])
    @pytest.mark.parametrize(
        "desc, inputs, get_ns, get_cln, get_pt, exp_rslt, condition",
        [
            # desc: Description of testcase
            # input - list of lists where the inner lists contain the parameters
            #         of a single request(testnamespaces, lclassnames
            #         provider_type, provider)
            #         * testnamespaces - Namespace or list of namespaces in
            #           which provider is to be registered
            #         * classnames - classname or list of classnames to register
            #           for provider
            #         * provider_type - String defining provider type
            #           ('instance-write', etc.)
            #         * provider - Class that contains the user provider.
            # get_ns - namespace parameter for get_registered_provider
            # get_cln - classname parameter for get_registered_provider
            # get_pt - provider_type parameter for get_registered_provider
            # exp_rslt - get_registered_provider expected return (True, None)
            # condition - test condition (True, False, 'pdb')

            ["Verify registry empty returns nothing",
             [],
             'root/cimv2', 'CIM_Foo', 'instance-write',
             None, True],

            ["Register single good instance provider and test good result",
             [
                 ["root/cimv2", UserInstanceTestProvider],
             ],
             'root/cimv2', 'CIM_Foo', 'instance-write',
             True, True],

            ["Register single good instance provider and test good result "
             "with lower case classname.",
             [
                 ["root/cimv2", UserInstanceTestProvider],
             ],
             'root/cimv2', 'cim_foo', 'instance-write',
             True, True],

            ["Verify get returns None namespace not found",
             [
                 ["root/cimv2", UserInstanceTestProvider],
             ],
             'root/cimv2x', 'CIM_Foo', 'instance-write',
             None, True],

            ["Verify get returns None classname  not found",
             [
                 ["root/cimv2", UserInstanceTestProvider],
             ],
             'root/cimv2', 'CIM_Foo_sub_sub', 'instance-write',
             None, True],

            ["Verify get v provider type does not match",
             [
                 ["root/cimv2", UserInstanceTestProvider],
             ],
             'root/cimv2', 'CIM_Foo', 'method',
             None, FAIL],

            ["Verify returns provider, with class",
             [
                 ["root/cimv2", UserInstanceTestProvider],
             ],
             'root/cimv2', 'CIM_Foo_sub_sub', 'instance-write',
             True, None],

            ["Verify multiple providers registered, returns OK",
             [["root/cimv2", UserInstanceTestProvider]],
             'root/cimv2', 'CIM_Foo', 'instance-write',
             True, True],

            ["Verify test, multiple classes registered, returns OK",
             [["root/cimv2", UserInstanceTestProvider]],
             'root/cimv2', 'CIM_Foo', 'instance-write',
             True, OK],

            ["Verify test, register with None as namespace, returns OK",
             [[None, UserInstanceTestProvider]],
             'root/cimv2', 'CIM_Foo', 'instance-write',
             True, OK],
        ]
    )
    def test_get_registered_provider(
            self, conn, tst_classeswqualifiers, tst_instances, ns, desc, inputs,
            get_ns, get_cln, get_pt, exp_rslt, condition):
        # pylint: disable=no-self-use,unused-argument
        """
        Creates a set of valid provider registrations and tests the
        get_provider_registration for multiple inputs
        """
        if not condition:
            pytest.skip("This test marked to be skippedby condition")

        if condition == "pdb":
            import pdb  # pylint: disable=import-outside-toplevel
            pdb.set_trace()  # pylint: disable=forgotten-debug-statement

        skip_if_moftab_regenerated()
        add_objects_to_repo(conn, ns, [tst_classeswqualifiers, tst_instances])

        # Register multiple providers.  All registrations are must be accepted
        for item in inputs:
            tst_ns = item[0]
            provider = item[1]
            conn.register_provider(provider(conn.cimrepository),
                                   tst_ns)

        # Test provider registration with get_registered_provider()
        if not exp_rslt or exp_rslt is True:

            # The code to be tested
            # pylint: disable=protected-access
            rtn = conn._provider_registry.get_registered_provider(
                get_ns, get_pt, get_cln)

            if exp_rslt is None:
                assert rtn is None
            if exp_rslt is True:
                assert rtn
                assert isinstance(rtn, InstanceWriteProvider)

        else:
            with pytest.raises(exp_rslt):

                # The code to be tested
                conn.providerdispatcher.get_registered_provider(
                    get_ns, get_pt, get_cln)

    # test_display_registered_providers
    @pytest.mark.parametrize(
        "desc, inputs, output, condition",
        [
            # desc: Description of testcase
            # input - list of lists where the inner lists contain the parameters
            #         of a single request(testnamespaces, classnames
            #         provider_type, provider)
            #         * testnamespaces - Namespace or list of namespaces in
            #           which provider is to be registered
            #         * provider - Class that contains the user provider.
            # result - List of regex to test result of display
            # condition - test condition (True, False, 'pdb')

            ["validate single existing  ns='root/cimv2', etc.",
             [
                 ["root/cimv2", UserInstanceTestProvider],
             ],
             "\nRegistered Providers:\n"
             "namespace: root/cimv2\n"
             "  CIM_Foo  instance-write  UserInstanceTestProvider\n",
             OK],

            ["validate namespace is None, etc.",
             [
                 [None, UserInstanceTestProvider],
             ],
             "\nRegistered Providers:\n"
             "namespace: root/cimv2\n"
             "  CIM_Foo  instance-write  UserInstanceTestProvider\n",
             OK],

            ["validate multiple namespaces , etc.",
             [
                 [["root/cimv2", "root/cimv3"], UserInstanceTestProvider],
             ],
             '\nRegistered Providers:\n'
             'namespace: root/cimv2\n'
             '  CIM_Foo  instance-write  UserInstanceTestProvider\n'
             'namespace: root/cimv3\n'
             '  CIM_Foo  instance-write  UserInstanceTestProvider\n',
             OK],

            ["validate ns='root/cimv2, root/cimv3', etc.",
             [
                 ["root/cimv2", UserInstanceTestProvider],
                 ["root/cimv3", UserInstanceTestProvider],
             ],
             '\nRegistered Providers:\n'
             'namespace: root/cimv2\n'
             '  CIM_Foo  instance-write  UserInstanceTestProvider\n'
             'namespace: root/cimv3\n'
             '  CIM_Foo  instance-write  UserInstanceTestProvider\n',
             OK],

            ["validate single existing ns, provider with multiple classnames",
             [
                 ["root/cimv2", UserInstanceTestProvider2],
             ],
             '\nRegistered Providers:\n'
             'namespace: root/cimv2\n'
             '  CIM_Foo      instance-write  UserInstanceTestProvider2\n'
             '  CIM_Foo_Sub  instance-write  UserInstanceTestProvider2\n',
             OK],

            ["validate multiple  ns, provider with multiple classnames",
             [
                 [["root/cimv2", 'root/cimv3'], UserInstanceTestProvider2],
             ],
             '\nRegistered Providers:\n'
             'namespace: root/cimv2\n'
             '  CIM_Foo      instance-write  UserInstanceTestProvider2\n'
             '  CIM_Foo_Sub  instance-write  UserInstanceTestProvider2\n'
             'namespace: root/cimv3\n'
             '  CIM_Foo      instance-write  UserInstanceTestProvider2\n'
             '  CIM_Foo_Sub  instance-write  UserInstanceTestProvider2\n',
             OK],

        ]
    )
    def test_display_registered_providers(
            self, conn, tst_classeswqualifiersandinsts, capsys,
            desc, inputs, output, condition):
        # pylint: disable=unused-argument,no-self-use
        """
        Test register_provider method.
        """
        if not condition:
            pytest.skip("This test marked to be skippedby condition")
        skip_if_moftab_regenerated()

        if condition == "pdb":
            import pdb  # pylint: disable=import-outside-toplevel
            pdb.set_trace()  # pylint: disable=forgotten-debug-statement

        nss = []
        for item in inputs:
            tst_ns = item[0]
            provider = item[1]
            if tst_ns is None:
                tst_ns = [conn.default_namespace]
            if not isinstance(tst_ns, list):
                tst_ns = [tst_ns]
            for ns in tst_ns:
                add_objects_to_repo(conn, ns,
                                    tst_classeswqualifiersandinsts)
                nss.append(ns)

            conn.register_provider(provider(conn.cimrepository),
                                   item[0])

        print('')  # Added because issues with getting captured without it.

        # The code to be tested
        conn.display_registered_providers()

        captured = capsys.readouterr()
        result = captured.out
        if output:
            assert output == result
        else:
            assert result.startswith("\nRegistered Providers:")

            assert "CIM_Foo  instance  UserInstanceTestProvider" in result

            for ns in nss:
                assert "namespace: {0}".format(ns) in result

    def test_user_provider1(self, conn, tst_classeswqualifiers, tst_instances):
        """
        Test execution with a user provider and CreateInstance.
        """

        class CIM_FooUserProvider(InstanceWriteProvider):
            """
            Define the user provider with only CreateInstance supported.
            Test that CreateInstance calls the user-defined provider and that
            ModifyInstance and DeleteInstance work meaning that they used
            the default provider
            """
            # Use CIMFoo_sub because it has a property to manipulate cimfoo_sub
            provider_classnames = 'CIM_Foo_sub'

            def __init__(self, cimrepository):
                """
                Init of test provider
                """
                super(CIM_FooUserProvider, self).__init__(cimrepository)

            def CreateInstance(self, namespace, new_instance):
                """
                My user CreateInstance.  Will change the InstanceID and
                use the default to commit the new_instance to the repository.
                No implementation of ModifyInstance or DeleteInstance
                """
                # modify the InstanceID property
                new_instance.properties["InstanceID"].value = "USER_PROVIDER1"

                # send back to the superclass to complete insertion into
                # the repository.
                return super(CIM_FooUserProvider, self).CreateInstance(
                    namespace, new_instance)

        skip_if_moftab_regenerated()
        ns = conn.default_namespace

        add_objects_to_repo(conn, ns, [tst_classeswqualifiers, tst_instances])
        conn.register_provider(CIM_FooUserProvider(conn.cimrepository), ns)

        new_instance = CIMInstance("CIM_Foo_sub",
                                   properties={'InstanceID': 'origid',
                                               'cimfoo_sub': 'OrigValue'})

        rtnd_path = conn.CreateInstance(new_instance)
        rtnd_instance = conn.GetInstance(rtnd_path)

        # Test that the instance was created with the InstanceID defined
        # by the user-defined provider
        assert rtnd_path.keybindings["InstanceId"] == "USER_PROVIDER1"
        assert rtnd_instance.path == rtnd_path

        # add the extra property to modified instance
        modified_instance = deepcopy(rtnd_instance)
        modified_instance.update([('cimfoo_sub', CIMProperty('cimfoo_sub',
                                                             "NewProperty"))])

        # do ModifyInstance, get modified instance and compare new property
        conn.ModifyInstance(modified_instance)
        rtnd_mod_inst = conn.GetInstance(rtnd_path)
        assert rtnd_mod_inst.get('cimfoo_sub') == "NewProperty"

        # Delete instance and test the delete
        conn.DeleteInstance(rtnd_path)
        try:
            conn.DeleteInstance(rtnd_path)
            assert False
        except CIMError as ce:
            assert ce.status_code == CIM_ERR_NOT_FOUND

    def test_user_provider2(self, conn, tst_classeswqualifiers, tst_instances):
        """
        Test with a single user defined provider using CIM_Foo_sub as the
        class and handles ModifyInstance only
        """

        class CIM_FooSubUserProvider(InstanceWriteProvider):
            """
            Define the user provider. Only implements ModifyInstance
            """
            # CIM classes this provider serves
            provider_classnames = 'CIM_Foo_Sub'

            def __init__(self, cimrepository):
                """
                Init of test provider
                """
                super(CIM_FooSubUserProvider, self).__init__(cimrepository)

            def ModifyInstance(self, modified_instance, IncludeQualifiers=None):
                """
                My user ModifyInstance.  Will change the value of the
                property as a flag
                """
                # modify a None key property.
                assert modified_instance.get("InstanceID") == 'origid'
                # modify the defined property value
                assert modified_instance.properties["cimfoo_sub"].value == \
                    "ModProperty"

                modified_instance.properties["cimfoo_sub"].value = \
                    "ModProperty2"

                # send back to the superclass to complete insertion into
                # the repository.
                return super(CIM_FooSubUserProvider, self).ModifyInstance(
                    modified_instance, IncludeQualifiers)

        skip_if_moftab_regenerated()
        ns = conn.default_namespace
        add_objects_to_repo(conn, ns, [tst_classeswqualifiers, tst_instances])
        conn.register_provider(CIM_FooSubUserProvider(conn.cimrepository), ns)

        # Build the new instance and put in repository with CreateInstance
        new_instance = CIMInstance(
            "CIM_Foo_sub",
            properties={'InstanceID': 'origid',
                        'cimfoo_sub': 'OrigProperty'})
        rtnd_path = conn.CreateInstance(new_instance)
        rtnd_instance = conn.GetInstance(rtnd_path)

        # Modify the cimfoo_sub property and put modification in repository
        mod_instance = deepcopy(rtnd_instance)
        mod_instance.update_existing([('cimfoo_sub', 'ModProperty')])
        conn.ModifyInstance(mod_instance)

        # Get modified instance and compare property for change
        rtnd_modified_instance = conn.GetInstance(rtnd_path)
        assert rtnd_modified_instance.properties["cimfoo_sub"].value == \
            "ModProperty2"

        assert rtnd_instance.path == rtnd_path

        # Confirm that DeleteInstance works
        conn.DeleteInstance(rtnd_path)
        try:
            conn.DeleteInstance(rtnd_path)
            assert False
        except CIMError as ce:
            assert ce.status_code == CIM_ERR_NOT_FOUND

    def test_user_provider3(self, conn, tst_classeswqualifiers, tst_instances):
        """
        Test execution with a user provider that handles all  of the
        opeations and confirm each is called
        """

        class CIM_FooSubUserProvider(InstanceWriteProvider):
            """
            Define the user provider with all defined methods and the
            setup method.  Each sets object flag when set to test it was
            called
            """
            # Use CIMFoo_sub because it has a property to manipulate cimfoo_sub
            provider_classnames = 'CIM_Foo_sub'

            def __init__(self, cimrepository):
                """
                Test user-defined provider that has only the DeleteInstance
                method.  Note that this provider constructor includes conn
                """
                super(CIM_FooSubUserProvider, self).__init__(cimrepository)

                self.conn = conn
                self.createinstance = False
                self.modifyinstance = False
                self.deleteinstance = False
                self.postregistersetup = False

            def CreateInstance(self, namespace, new_instance):
                """
                Change the InstanceID and use the default to commit the
                new_instance to the repository.
                """
                self.createinstance = True
                # modify the InstanceID property
                new_instance.properties["InstanceID"].value = "USER_PROVIDER3"

                return super(CIM_FooSubUserProvider, self).CreateInstance(
                    namespace, new_instance)

            def ModifyInstance(self, modified_instance, IncludeQualifiers=None):
                """
                My user ModifyInstance.  Change value of the property as a flag
                """
                self.modifyinstance = True
                return super(CIM_FooSubUserProvider, self).ModifyInstance(
                    modified_instance)

            def DeleteInstance(self, InstanceName):
                """
                Delete the defined instance
                """
                self.deleteinstance = True
                return super(CIM_FooSubUserProvider, self).DeleteInstance(
                    InstanceName)

            def post_register_setup(self, conn):
                """Sets flag to show method run"""
                # pylint: disable=unused-argument
                self.postregistersetup = True

        skip_if_moftab_regenerated()

        ns = conn.default_namespace
        add_objects_to_repo(conn, ns, [tst_classeswqualifiers, tst_instances])
        test_provider = CIM_FooSubUserProvider(conn.cimrepository)
        conn.register_provider(test_provider, ns)

        new_instance = CIMInstance("CIM_Foo_sub",
                                   properties={'InstanceID': 'origid',
                                               'cimfoo_sub': 'OrigValue'})

        rtnd_path = conn.CreateInstance(new_instance)

        rtnd_instance = conn.GetInstance(rtnd_path)

        # Test that the instance was created with the InstanceID defined
        # by the user-defined provider
        assert rtnd_path.keybindings["InstanceId"] == "USER_PROVIDER3"
        assert rtnd_instance.path == rtnd_path

        modified_instance = rtnd_instance
        modified_instance.update([('cimfoo_sub', CIMProperty('cimfoo_sub',
                                                             "InstMod"))])
        conn.ModifyInstance(modified_instance)
        rtnd_mod_inst = conn.GetInstance(rtnd_path)
        assert rtnd_mod_inst.get('cimfoo_sub') == "InstMod"

        conn.DeleteInstance(rtnd_path)
        try:
            conn.DeleteInstance(rtnd_path)
            assert False
        except CIMError as ce:
            assert ce.status_code == CIM_ERR_NOT_FOUND

        # Test that the methods were called
        assert test_provider.createinstance is True
        assert test_provider.modifyinstance is True
        assert test_provider.deleteinstance is True
        assert test_provider.postregistersetup is True


def resolve_class(conn, cls, ns):
    """
    Execute the _resolve_class method on the cls to create a class that
    is resolved (i.e. the inherited characteristics are inserted into the
    class).
    """
    ns = ns or conn.default_namespace
    qualifier_store = conn.cimrepository.get_qualifier_store(ns)
    # pylint: disable=protected-access
    rslvd_cls = conn._mainprovider._resolve_class(cls, ns, qualifier_store)
    return rslvd_cls


def assert_resolved_classes_equal(conn, ns, exp_class, tst_class):
    """
    Test two pywbem classes for equality. The exp_class is resolved before the
    test.
    """
    ns = ns or conn.default_namespace
    exp_resolved = resolve_class(conn, exp_class, ns)
    assert_classes_equal(exp_resolved, tst_class)


class TestClassOperations(object):
    """
    Test mocking of Class level operations including getClass,
    EnumerateClasses, EnumerateClassNames, CreateClass, DeleteClass.
    Does not test the Associator or Reference operations.
    """

    @pytest.mark.parametrize(
        "tst_ns, cln, ns, exp_exc",
        [
            # tst_ns: Namespace that is set up for testing
            # cln: ClassName input parameter for the operation
            # ns: namespace input parameter for the operation
            # exp_exc: None, or expected exception object

            [DEFAULT_NAMESPACE, 'CIM_Foo', None, None],
            [DEFAULT_NAMESPACE, 'cim_foo', None, None],
            [DEFAULT_NAMESPACE, 'CIM_Foo', 'BadNamespace',
             CIMError(CIM_ERR_INVALID_NAMESPACE)],
            [DEFAULT_NAMESPACE, 'CIM_Foo', DEFAULT_NAMESPACE, None],
            [DEFAULT_NAMESPACE, 'CIM_Foox', None,
             CIMError(CIM_ERR_NOT_FOUND)],
            [DEFAULT_NAMESPACE, 'CIM_Foox', 'BadNamespace',
             CIMError(CIM_ERR_INVALID_NAMESPACE)],
            # Invalid types
            [DEFAULT_NAMESPACE, 42, 'BadNamespace', TypeError()],
            [DEFAULT_NAMESPACE, 42, DEFAULT_NAMESPACE, TypeError()],
            [DEFAULT_NAMESPACE, None, DEFAULT_NAMESPACE, TypeError()],
            [DEFAULT_NAMESPACE, 'CIM_Foo', 42, TypeError()],
            [DEFAULT_NAMESPACE, 42, 42, TypeError()],
            # test with non-default namespace
            [NOT_DEFAULT_NS, 'CIM_Foo', NOT_DEFAULT_NS, None],
        ]
    )
    def test_getclass(self, conn, tst_qualifiers, tst_class, tst_ns, cln,
                      ns, exp_exc):
        # pylint: disable=no-self-use
        """
        Test mocked GetClass() with namespace and ClassName parameters.
        """
        add_objects_to_repo(conn, tst_ns, [tst_qualifiers, tst_class])

        if exp_exc is None:

            # The code to be tested
            rslt_cl = conn.GetClass(cln, namespace=ns,
                                    IncludeQualifiers=True,
                                    IncludeClassOrigin=True)

            rslt_cl.path = None
            assert_resolved_classes_equal(conn, tst_ns, tst_class, rslt_cl)
        else:
            with pytest.raises(type(exp_exc)) as exec_info:

                # The code to be tested
                conn.GetClass(cln, namespace=ns)

            exc = exec_info.value
            if isinstance(exp_exc, CIMError):
                assert exc.status_code == exp_exc.status_code

    @pytest.mark.parametrize(
        "ns", INITIAL_NAMESPACES + [None])
    @pytest.mark.parametrize(
        "cln, iq, ico",
        [
            # cln: ClassName input parameter for the operation
            # iq: IncludeQualifiers input parameter for the operation
            # ico: IncludeClassOrigin input parameter for the operation

            ['CIM_Foo', False, False],
            ['cim_foo', False, False],
            ['CIM_Foo', True, False],
            ['CIM_Foo', True, True],
            ['CIM_Foo_sub', False, False],
            ['CIM_Foo_sub', True, False],
            ['CIM_Foo_sub', True, True],
        ]
    )
    def test_getclass_iqico(self, conn, tst_classes, tst_classeswqualifiers,
                            ns, cln, iq, ico):
        # pylint: disable=no-self-use
        """
        Test mocked GetClass() with IncludeQualifiers and IncludeClassOrigin
        parameters.
        """

        # Verify test valid in that class exists in repo

        for cl_ in tst_classes:
            if cl_.classname.lower() == cln.lower():
                exp_class = cl_
        assert exp_class is not None

        conn.add_cimobjects(tst_classeswqualifiers, namespace=ns)

        # The code to be tested
        rslt_cl = conn.GetClass(cln, namespace=ns, IncludeQualifiers=iq,
                                LocalOnly=False, IncludeClassOrigin=ico)

        # resolve the expected class before we manipulate it per iq and ico
        exp_class = resolve_class(conn, exp_class, ns)

        # remove all qualifiers and class_origins and test for equality
        if not iq:
            exp_class.qualifiers = NocaseDict()
            for prop in rslt_cl.properties:
                exp_class.properties[prop].qualifiers = NocaseDict()
            for method in rslt_cl.methods:
                exp_class.methods[method].qualifiers = NocaseDict()
                for param in rslt_cl.methods[method].parameters:
                    exp_class.methods[method].parameters[param].qualifiers = \
                        NocaseDict()

        # remove class origin if ico = None. Else test
        if not ico:
            for prop in exp_class.properties:
                exp_class.properties[prop].class_origin = None
            for method in exp_class.methods:
                exp_class.methods[method].class_origin = None

        # Test the modified tst_class against the returned class
        ns = ns or conn.default_namespace
        exp_class.path = CIMClassName(cln, host='FakedUrl:5988',
                                      namespace=ns)

        assert rslt_cl == exp_class

    @pytest.mark.parametrize(
        "ns", INITIAL_NAMESPACES + [None])
    @pytest.mark.parametrize(
        "cln, lo, exp_pl",
        [
            # cln: ClassName input parameter for the operation
            # lo: LocalOnly input parameter for the operation
            # exp_pl: Expected list of property names in operation result

            ['CIM_Foo_sub', None, ['cimfoo_sub']],
            ['CIM_Foo_sub', True, ['cimfoo_sub']],
            ['cim_foo_sub', True, ['cimfoo_sub']],
            ['CIM_Foo_sub', False, ['cimfoo_sub', 'InstanceID']],
            ['CIM_Foo_sub_sub', None, ['cimfoo_sub_sub']],
            ['CIM_Foo_sub_sub', True, ['cimfoo_sub_sub']],
            ['CIM_Foo_sub_sub', False, ['cimfoo_sub_sub', 'cimfoo_sub',
                                        'InstanceID']],
        ]
    )
    def test_getclass_lo(self, conn, tst_qualifiers, tst_classes, ns, cln,
                         lo, exp_pl):
        # pylint: disable=no-self-use
        """
        Test mocked GetClass() with LocalOnly parameter.

        NOTE: This is the mock implementation.  The DMTF specification leaves
        this as ambiguous.
        """
        add_objects_to_repo(conn, ns, [tst_qualifiers, tst_classes])

        # The code to be tested
        rslt_cl = conn.GetClass(cln, namespace=ns, LocalOnly=lo,
                                IncludeQualifiers=True,
                                IncludeClassOrigin=True)

        assert rslt_cl.classname.lower() == cln.lower()
        assert len(rslt_cl.properties) == len(exp_pl)
        rslt_pl = rslt_cl.properties.keys()
        assert set(rslt_pl) == set(exp_pl)

        tst_cls_dict = {}
        for cl in tst_classes:
            tst_cls_dict[cl.classname] = resolve_class(conn, cl, ns)

        # test for qualifiers
        for pname, prop in rslt_cl.properties.items():
            prop_class_origin = prop.class_origin
            exp_prop_qualifiers = \
                tst_cls_dict[prop_class_origin].properties[pname].qualifiers
            # Compare qualifiers, ignoring the propagated attribute
            assert len(prop.qualifiers) == len(exp_prop_qualifiers)
            for qname in prop.qualifiers:
                qual_unpropagated = prop.qualifiers[qname].copy()
                qual_unpropagated.propagated = None
                exp_qual_unpropagated = exp_prop_qualifiers[qname].copy()
                exp_qual_unpropagated.propagated = None
                assert qual_unpropagated == exp_qual_unpropagated

    @pytest.mark.parametrize(
        "ns", EXPANDED_NAMESPACES + [None])
    @pytest.mark.parametrize(
        "pl, exp_pl",
        [
            # pl: PropertyList input parameter for the operation
            # exp_pl: Expected list of property names in operation result

            [None, ['InstanceID', 'cimfoo_sub', 'cimfoo_sub_sub']],
            ['', []],
            ['InstanceID', ['InstanceID']],
            [['InstanceID'], ['InstanceID']],
            [['InstanceID', 'InstanceID'], ['InstanceID']],
            [['InstanceID', 'cimfoo_sub'], ['InstanceID', 'cimfoo_sub']]
        ]
    )
    def test_getclass_pl(self, conn, tst_classeswqualifiers, ns, pl, exp_pl):
        # pylint: disable=no-self-use
        """
        Test mocked GetClass() with PropertyList parameter.
        """
        add_objects_to_repo(conn, ns, [tst_classeswqualifiers])
        cln = 'CIM_Foo_sub_sub'

        # The code to be tested
        rslt_cl = conn.GetClass(cln, namespace=ns, PropertyList=pl,
                                LocalOnly=False,
                                IncludeQualifiers=True,
                                IncludeClassOrigin=True)

        assert len(rslt_cl.properties) == len(exp_pl)
        rslt_pl = rslt_cl.properties.keys()
        assert set(rslt_pl) == set(exp_pl)

    @pytest.mark.parametrize(
        "ns", EXPANDED_NAMESPACES + [None])
    @pytest.mark.parametrize(
        "cln, di, exp_rslt",
        [
            # cln: ClassName input parameter for the operation
            # di: DeepInheritance input parameter for the operation
            # exp_rslt: Expected operation result: List of expected
            #           class names or expected exception object

            [None, None, ['CIM_Foo', 'CIM_Foo_nokey']],
            [None, False, ['CIM_Foo', 'CIM_Foo_nokey']],
            [None, True, ['CIM_Foo', 'CIM_Foo_sub', 'CIM_Foo_sub2',
                          'CIM_Foo_sub_sub', 'CIM_Foo_nokey']],
            ['CIM_Foo', None, ['CIM_Foo_sub', 'CIM_Foo_sub2']],
            ['cim_foo', None, ['CIM_Foo_sub', 'CIM_Foo_sub2']],
            [CIMClassName('CIM_Foo'), None, ['CIM_Foo_sub', 'CIM_Foo_sub2']],
            ['CIM_Foo', True, ['CIM_Foo_sub', 'CIM_Foo_sub2',
                               'CIM_Foo_sub_sub']],
            [CIMClassName('CIM_Foo'), True, ['CIM_Foo_sub', 'CIM_Foo_sub2',
                                             'CIM_Foo_sub_sub']],
            ['CIM_Foo_sub', None, ['CIM_Foo_sub_sub']],
            ['CIM_Foo_sub_sub', None, []],
            ['CIM_Foo_sub_subxx', None, CIMError(CIM_ERR_INVALID_CLASS)],
            # Invalid types
            [42, None, TypeError()],
            ['CIM_Foo_sub', 42, TypeError()],
        ]
    )
    def test_enumerateclassnames(self, conn, tst_classeswqualifiers, ns, cln,
                                 di, exp_rslt):
        # pylint: disable=no-self-use
        """
        Test EnumerateClassNames mock with parameters for namespace,
        classname, DeepInheritance
        """

        add_objects_to_repo(conn, ns, tst_classeswqualifiers)

        if isinstance(exp_rslt, Exception):
            exp_exc = exp_rslt
            with pytest.raises(type(exp_exc)) as exec_info:

                # The code to be tested
                conn.EnumerateClassNames(ClassName=cln, namespace=ns,
                                         DeepInheritance=di)

            exc = exec_info.value
            if isinstance(exp_exc, CIMError):
                assert exc.status_code == exp_exc.status_code
            return

        if cln is None:

            # The code to be tested
            rslt_clns = conn.EnumerateClassNames(namespace=ns,
                                                 DeepInheritance=di)

        else:

            # The code to be tested
            rslt_clns = conn.EnumerateClassNames(ClassName=cln,
                                                 namespace=ns,
                                                 DeepInheritance=di)

        for cln_ in rslt_clns:
            assert isinstance(cln_, six.string_types)
        assert len(rslt_clns) == len(exp_rslt)
        assert set(rslt_clns) == set(exp_rslt)

    @pytest.mark.parametrize(
        "ns", EXPANDED_NAMESPACES + [None])
    @pytest.mark.parametrize(
        "iq", [
            # iq: IncludeQualifiers input parameter for the operation
            None,
            False,
            True
        ]
    )
    @pytest.mark.parametrize(
        "ico", [
            # ico: IncludeClassOrigin input parameter for the operation
            None,
            False,
            True
        ]
    )
    @pytest.mark.parametrize(
        "cln, lo, di, exp_pl, exp_rslt",
        [
            # cln: ClassName input parameter for the operation
            # lo: LocalOnly input parameter for the operation
            # di: DeepInheritance input parameter for the operation
            # exp_pl: List of expected property names in result classes
            # exp_rslt: Integer with expected number of classes in result, or
            #           expected exception object.

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
            ['CIM_Foo_sub_subxx', False, True, [],
             CIMError(CIM_ERR_INVALID_CLASS)],
            ['CIM_Foo_sub', False, True, ['InstanceID', 'cimfoo_sub',
                                          'cimfoo_sub_sub'], 1],
            # Invalid types
            [42, False, True, [], TypeError()],
            ['CIM_Foo_sub', 42, True, [], TypeError()],
            ['CIM_Foo_sub', False, 42, [], TypeError()],
        ]
    )
    def test_enumerateclasses(self, conn, tst_classes, tst_qualifiers, ns, iq,
                              ico, cln, lo, di, exp_pl, exp_rslt):
        # pylint: disable=no-self-use
        """
        Test EnumerateClasses for proper processing of input parameters.
        All tests in this test method pass and there should be no exceptions.
        Tests for correct properties, methods, and qualifiers, returned for
        lo and di and correct number of classes returned
        """
        add_objects_to_repo(conn, ns, [tst_qualifiers, tst_classes])

        if isinstance(exp_rslt, Exception):
            exp_exc = exp_rslt
            with pytest.raises(type(exp_exc)) as exec_info:

                # The code to be tested
                conn.EnumerateClasses(ClassName=cln,
                                      namespace=ns,
                                      DeepInheritance=di,
                                      LocalOnly=lo,
                                      IncludeQualifiers=iq,
                                      IncludeClassOrigin=ico)

            exc = exec_info.value
            if isinstance(exp_exc, CIMError):
                assert exc.status_code == exp_exc.status_code
            return

        if cln is None:

            # The code to be tested
            rslt_classes = conn.EnumerateClasses(namespace=ns,
                                                 DeepInheritance=di,
                                                 LocalOnly=lo,
                                                 IncludeQualifiers=iq,
                                                 IncludeClassOrigin=ico)

        else:

            # The code to be tested
            rslt_classes = conn.EnumerateClasses(ClassName=cln,
                                                 namespace=ns,
                                                 DeepInheritance=di,
                                                 LocalOnly=lo,
                                                 IncludeQualifiers=iq,
                                                 IncludeClassOrigin=ico)

        assert isinstance(exp_rslt, six.integer_types)
        assert len(rslt_classes) == exp_rslt

        for rslt_cl in rslt_classes:
            assert isinstance(rslt_cl, CIMClass)

            if lo:
                # get the corresponding test input class
                tst_class = None
                for tst_cl in tst_classes:
                    if tst_cl.classname == rslt_cl.classname:
                        tst_class = tst_cl
                        break
                assert tst_class

                assert set(rslt_cl.properties.keys()) == \
                    set(tst_class.properties.keys())
            else:
                # not lo, returns all properties from superclasses.
                # test for return as subset of exp_pl
                rslt_pl = rslt_cl.properties.keys()
                assert set(rslt_pl).issubset(set(exp_pl))

            # Confirm get_class returns the same set of properties
            get_cl = conn.GetClass(rslt_cl.classname, namespace=ns,
                                   LocalOnly=lo,
                                   IncludeQualifiers=iq,
                                   IncludeClassOrigin=ico)

            assert set(get_cl.properties.keys()) == \
                set(rslt_cl.properties.keys())

            assert set(get_cl.methods.keys()) == \
                set(rslt_cl.methods.keys())

            if ico:
                for prop in six.itervalues(get_cl.properties):
                    assert prop.class_origin is not None

                for method in six.itervalues(get_cl.methods):
                    assert method.class_origin is not None
            else:
                for prop in six.itervalues(get_cl.properties):
                    assert prop.class_origin is None

                for method in six.itervalues(get_cl.methods):
                    assert method.class_origin is None

            if iq is True or iq is None:
                if get_cl.qualifiers:
                    assert rslt_cl.qualifiers
                for prop in six.itervalues(get_cl.properties):
                    if get_cl.properties[prop.name].qualifiers:
                        assert prop.qualifiers is not None

                for method in six.itervalues(get_cl.methods):
                    if get_cl.methods[method.name].qualifiers:
                        assert method.qualifiers is not None
            else:
                assert not rslt_cl.qualifiers
                for prop in six.itervalues(get_cl.properties):
                    assert not prop.qualifiers

                for method in six.itervalues(get_cl.methods):
                    assert not method.qualifiers

    def process_pretcl(self, conn, pre_tst_classes, ns, tst_classes):
        """Support method for createclass. Executes createclass on the
           pre_tst_classes parameter. Compiles all classes found in the
           parameter

           Parameters:
             conn:

             pre_tst_classes (list or string or CIMClass):
                If list, it is a list of classnames from tst_classes to
                be passed to CreateClass.
                If string it is a single classname from tst_classes to be
                passed to CreateClass.
                If CIMClass, it is a CIMClass pywbem object to be passed
                to CreateClass

             ns (:term:`string`):
               String defining target namespace for adding classes

             tst_classes (list): list of classes availiable for test
        """
        if pre_tst_classes:
            # if is list of classnames, recursively call for each one
            if isinstance(pre_tst_classes, list):
                for cln in pre_tst_classes:
                    self.process_pretcl(conn, cln, ns, tst_classes)

            # If string, it is a classname of class in tst_classes
            elif isinstance(pre_tst_classes, six.string_types):
                for tst_cls in tst_classes:
                    if tst_cls.classname == pre_tst_classes:
                        conn.CreateClass(tst_cls, namespace=ns)
                        return

            elif isinstance(pre_tst_classes, CIMClass):
                conn.CreateClass(pre_tst_classes, namespace=ns)

    @pytest.mark.parametrize(
        "ns", INITIAL_NAMESPACES + [None])
    @pytest.mark.parametrize(
        "desc, pre_tst_classes, tst_cls, exp_rslt, exp_exc, condition",
        [
            # desc: Description of testcase
            # pre_tst_classes: Create the defined class or classes before the
            #                  test. These are the superclasses for the new
            #                  class to be created
            #                  May be:
            #                   * pywbem CIMClass definition,
            #                   * string defining name of class in tst_classes
            #                   * list of class/classnames
            # tst_cls: Either string defining test class name in tst_classes or
            #         CIMClass to be passed to CreateClass
            # exp_rstl: None or expected CIMClass returned from GetClass for
            #             verifying the created class
            # exp_exc: None or expected exception object
            # condition: If False, skip this test

            ['Create simple class  CIM_Foo correctly',
             None, 'CIM_Foo',
             CIMClass(
                 'CIM_Foo', superclass=None,
                 qualifiers={
                     'Description': CIMQualifier(
                         'Description', "CIM_Foo description",
                         overridable=True,
                         tosubclass=True,
                         translatable=True,
                         propagated=False)},
                 properties={
                     'InstanceID': CIMProperty(
                         'InstanceID', None,
                         qualifiers={
                             'Key': CIMQualifier(
                                 'Key', True, type='boolean',
                                 overridable=False,
                                 tosubclass=True,
                                 propagated=False), },
                         type='string', class_origin='CIM_Foo',
                         propagated=False), },
                 methods={
                     'Delete': CIMMethod(
                         'Delete', 'uint32',
                         qualifiers={
                             'Description': CIMQualifier(
                                 'Description', "qualifier description",
                                 overridable=True,
                                 tosubclass=True,
                                 translatable=True,
                                 propagated=False)},
                         class_origin='CIM_Foo',
                         propagated=False),
                     'Fuzzy': CIMMethod(
                         'Fuzzy', 'string',
                         qualifiers={
                             'Description': CIMQualifier(
                                 'Description', "qualifier description",
                                 overridable=True,
                                 tosubclass=True,
                                 translatable=True,
                                 propagated=False)},
                         class_origin='CIM_Foo',
                         propagated=False), },
             ),
             None, OK],

            ['Validate CreateClass creates valid subclass from 2 superclasses',
             'CIM_Foo',  # class to be created before test
             'CIM_Foo_sub',  # Class to be created and validated.
             CIMClass(
                 'CIM_Foo_sub', superclass='CIM_Foo',
                 qualifiers={'Description': CIMQualifier(
                     'Description', "Subclass Description",
                     overridable=True,
                     tosubclass=True,
                     translatable=True,
                     propagated=False)},
                 properties={
                     'cimfoo_sub': CIMProperty(
                         'cimfoo_sub', None,  # noqa: E121
                         qualifiers={'Description': CIMQualifier(
                             'Description', "qualifier description",
                             overridable=True,
                             tosubclass=True,
                             translatable=True,
                             propagated=False)},
                         type='string', class_origin='CIM_Foo_sub',
                         propagated=False),
                     'InstanceID': CIMProperty(
                         'InstanceID', None,  # noqa: E121
                         qualifiers={
                             'Key': CIMQualifier(
                                 'Key', True, type='boolean',
                                 overridable=False,
                                 tosubclass=True,
                                 propagated=True), },
                         type='string', class_origin='CIM_Foo',
                         propagated=True), },
                 methods={
                     'Delete': CIMMethod(
                         'Delete', 'uint32',
                         qualifiers={
                             'Description': CIMQualifier(
                                 'Description', "qualifier description",
                                 overridable=True,
                                 tosubclass=True,
                                 translatable=True,
                                 propagated=True)},
                         class_origin='CIM_Foo',
                         propagated=True),
                     'Fuzzy': CIMMethod(
                         'Fuzzy', 'string',
                         qualifiers={'Description': CIMQualifier(
                             'Description', "qualifier description",
                             overridable=True,
                             tosubclass=True,
                             translatable=True,
                             propagated=True)},
                         class_origin='CIM_Foo',
                         propagated=True), },
             ),
             None, OK],

            ["Create valid 2nd level subclass from fixture defined classes.",
             ['CIM_Foo', 'CIM_Foo_sub'],
             'CIM_Foo_sub_sub',
             'CIM_Foo_sub_sub', None, OK],

            ["Create valid 2nd level subclass from class with extra data.",
             ['CIM_Foo', 'CIM_Foo_sub'],
             'CIM_Foo_sub_sub',
             CIMClass(
                 'CIM_Foo_sub_sub', superclass='CIM_Foo_sub',
                 qualifiers={'Description': CIMQualifier(
                     'Description', 'Subclass Description',
                     overridable=True,
                     tosubclass=True,
                     translatable=True,
                     propagated=False)},
                 properties={
                     'InstanceID':
                         CIMProperty('InstanceID', None, type='string',
                                     class_origin='CIM_Foo', propagated=True,
                                     is_array=False, array_size=None,
                                     qualifiers={
                                         'key': CIMQualifier(
                                             'Key', True, propagated=True,
                                             tosubclass=True,
                                             overridable=False)}),
                     'cimfoo_sub': CIMProperty(
                         'cimfoo_sub', None,
                         qualifiers={
                             'Description': CIMQualifier(
                                 'Description', "qualifier description",
                                 overridable=True,
                                 tosubclass=True,
                                 translatable=True,
                                 propagated=True)},
                         type='string', class_origin='CIM_Foo_sub',
                         propagated=True),
                     'cimfoo_sub_sub': CIMProperty(
                         'cimfoo_sub_sub', None,
                         qualifiers={
                             'Description': CIMQualifier(
                                 'Description', "property description",
                                 overridable=True,
                                 tosubclass=True,
                                 translatable=True,
                                 propagated=False)},
                         type='string', class_origin='CIM_Foo_sub_sub',
                         propagated=False),
                 },
                 methods={
                     'Delete': CIMMethod(
                         'Delete', 'uint32',
                         class_origin='CIM_Foo', propagated=True,
                         qualifiers={
                             'Description': CIMQualifier(
                                 'Description', 'qualifier description',
                                 propagated=True,
                                 tosubclass=True,
                                 overridable=True,
                                 translatable=True)}),
                     'Fuzzy': CIMMethod('Fuzzy', 'string',
                                        class_origin='CIM_Foo', propagated=True,
                                        qualifiers={
                                            'Description': CIMQualifier(
                                                'Description',
                                                'qualifier description',
                                                propagated=True,
                                                tosubclass=True,
                                                overridable=True,
                                                translatable=True)}),
                 },
             ),
             None, OK],

            ['Create valid 2nd level subclass with key override. '
             ' Confirms key is set.',
             ['CIM_Foo'],
             CIMClass(
                 'CIM_Foo_testOverride', superclass='CIM_Foo',
                 properties={
                     'InstanceID':
                         CIMProperty(
                             'InstanceID', None,
                             qualifiers={
                                 'Override': CIMQualifier(
                                     'Override', 'InstanceID'),
                                 'Description': CIMQualifier(
                                     'Description', "blah Blah Blah")
                             },
                             type='string'),
                 }
             ),
             CIMClass(
                 'CIM_Foo_testOverride', superclass='CIM_Foo',
                 properties={
                     'InstanceID':
                         CIMProperty(
                             'InstanceID', None, type='string',
                             class_origin='CIM_Foo', propagated=True,
                             is_array=False, array_size=None,
                             qualifiers={
                                 'key': CIMQualifier('Key', True,
                                                     propagated=True,
                                                     tosubclass=True,
                                                     overridable=False),
                                 'Override': CIMQualifier(
                                     'Override', 'InstanceID',
                                     propagated=False,
                                     tosubclass=False,
                                     overridable=True),
                                 'Description': CIMQualifier(
                                     'Description', "blah Blah Blah",
                                     propagated=False,
                                     tosubclass=True,
                                     overridable=True,
                                     translatable=True)})
                 },
                 methods={
                     'Delete': CIMMethod(
                         'Delete', 'uint32',
                         class_origin='CIM_Foo', propagated=True,
                         qualifiers={
                             'Description': CIMQualifier(
                                 'Description', 'qualifier description',
                                 propagated=True,
                                 tosubclass=True,
                                 overridable=True,
                                 translatable=True)}),
                     'Fuzzy': CIMMethod(
                         'Fuzzy', 'string',
                         class_origin='CIM_Foo', propagated=True,
                         qualifiers={
                             'Description': CIMQualifier(
                                 'Description', 'qualifier description',
                                 propagated=True,
                                 tosubclass=True,
                                 overridable=True,
                                 translatable=True)}),
                 },
             ),
             None, OK],

            ['Validate fails create where property exists with different type',
             ['CIM_Foo'],
             CIMClass(
                 'CIM_Foo_testOverride', superclass='CIM_Foo',
                 properties={
                     'InstanceID':
                         CIMProperty(
                             'InstanceID', 32,
                             qualifiers={
                                 'Override': CIMQualifier(
                                     'Override', 'InstanceID'),
                                 'Description': CIMQualifier(
                                     'Description', "blah Blah Blah")
                             },
                             type='uint32'),
                 }
             ),
             None, CIMError(CIM_ERR_INVALID_PARAMETER), OK],

            ['Fail create invalid subclass, dup property with no override',
             ['CIM_Foo', 'CIM_Foo_sub'],
             CIMClass(
                 'CIM_Foo_sub_sub', superclass='CIM_Foo_sub',
                 properties={
                     'cimfoo_sub': CIMProperty(
                         'cimfoo_sub', "blah",  # noqa: E121
                         type='string',
                         class_origin='CIM_Foo_sub_sub', propagated=False)
                 }
             ),
             None, CIMError(CIM_ERR_INVALID_PARAMETER), OK],

            ['Fail create invalid subclass, Unknown class qualifier',
             ['CIM_Foo', 'CIM_Foo_sub'],
             CIMClass(
                 'CIM_Foo_sub_sub', superclass='CIM_Foo_sub',
                 qualifiers={'NonExist': CIMQualifier('NonExist', 'Argh')},
                 properties={
                     'cimfoo_sub': CIMProperty(
                         'cimfoo_sub', "blah",
                         type='string',
                         class_origin='CIM_Foo_sub_sub', propagated=False)
                 }
             ),
             None, CIMError(CIM_ERR_INVALID_PARAMETER), OK],

            ['Fail create invalid subclass, qualifier type invalid',
             ['CIM_Foo', 'CIM_Foo_sub'],
             CIMClass(
                 'CIM_Foo_sub_sub', superclass='CIM_Foo_sub',
                 qualifiers={'Description': CIMQualifier('Description', True)},
                 properties={
                     'cimfoo_sub': CIMProperty(
                         'cimfoo_sub', "blah",
                         type='string',
                         class_origin='CIM_Foo_sub_sub', propagated=False)
                 }
             ),
             None, CIMError(CIM_ERR_INVALID_PARAMETER), OK],

            ['Fail create invalid subclass, Unknown property qualifier',
             ['CIM_Foo', 'CIM_Foo_sub'],
             CIMClass(
                 'CIM_Foo_sub_sub', superclass='CIM_Foo_sub',
                 properties={
                     'cimfoo_sub': CIMProperty(
                         'cimfoo_sub', "blah",
                         qualifiers={'NonExist': CIMQualifier('NonExist',
                                                              'Argh')},
                         type='string',
                         class_origin='CIM_Foo_sub_sub', propagated=False)}
             ),
             None, CIMError(CIM_ERR_INVALID_PARAMETER), OK],

            ['Fail because superclass does not exist in namespace',
             None, 'CIM_Foo_sub', None, CIMError(CIM_ERR_INVALID_SUPERCLASS),
             OK],

            ['Fail because class is incorrect type CIMQualifierDeclaration',
             None, CIMQualifierDeclaration('blah', 'string'), None,
             TypeError(), OK],

            ['Fail because class is incorrect type int',
             None, 42, None,
             TypeError(), OK],

            ['Fail create invalid subclass, Class qualifier on property',
             ['CIM_Foo', 'CIM_Foo_sub'],
             CIMClass(
                 'CIM_Foo_sub_sub', superclass='CIM_Foo_sub',
                 properties={
                     'cimfoo_sub': CIMProperty(
                         'cimfoo_sub', "blah",
                         qualifiers={'Abstract': CIMQualifier('Abstract',
                                                              True)},
                         type='string',)}
             ),
             None, CIMError(CIM_ERR_INVALID_PARAMETER), OK],

            ['Fail create invalid subclass, Property qualifier (Key) on class',
             ['CIM_Foo', 'CIM_Foo_sub'],
             CIMClass(
                 'CIM_Foo_sub_sub', superclass='CIM_Foo_sub',
                 qualifiers={'Key': CIMQualifier('Key', True)},
                 properties={
                     'cimfoo_sub': CIMProperty(
                         'cimfoo_sub', "blah",
                         type='string',)}
             ),
             None, CIMError(CIM_ERR_INVALID_PARAMETER), OK],

            ['OK create Association Qualifierr (False) on nonassociation class',
             ['CIM_Foo', 'CIM_Foo_sub'],
             CIMClass(
                 'CIM_Foo_sub_sub', superclass='CIM_Foo_sub',
                 qualifiers={'Association': CIMQualifier('Association', False)},
                 properties={
                     'cimfoo_sub': CIMProperty(
                         'cimfoo_sub', "blah",
                         type='string',)}
             ),
             None, CIMError(CIM_ERR_INVALID_PARAMETER), OK],

            ['Validate CreateClass subclass from CIM_Foo with new method',
             ['CIM_Foo'],
             CIMClass(
                 'CIM_Foo_newmethod', superclass='CIM_Foo',
                 methods={
                     'M1': CIMMethod(
                         'M1', 'uint32',
                         qualifiers={
                             'Description': CIMQualifier(
                                 'Description', "Method M1 with parameter")},
                         parameters={"P1": CIMParameter('P1',
                                                        type='uint32')}, ), },
             ),
             # class to validate creation
             CIMClass(
                 'CIM_Foo_newmethod', superclass='CIM_Foo',
                 qualifiers={
                     'Description': CIMQualifier(
                         'Description', "CIM_Foo description",
                         overridable=True, tosubclass=True, translatable=True,
                         propagated=True)},
                 properties={
                     'InstanceID': CIMProperty(
                         'InstanceID', None,
                         qualifiers={
                             'Key': CIMQualifier(
                                 'Key', True, type='boolean',
                                 overridable=False, tosubclass=True,
                                 propagated=True), },
                         type='string', class_origin='CIM_Foo',
                         propagated=True), },
                 methods={
                     'M1': CIMMethod(
                         'M1', 'uint32',
                         qualifiers={
                             'Description': CIMQualifier(
                                 'Description', "Method M1 with parameter",
                                 overridable=True, tosubclass=True,
                                 translatable=True, propagated=False)},
                         parameters={"P1": CIMParameter('P1', type='uint32')},
                         class_origin='CIM_Foo_newmethod',
                         propagated=False),
                     'Delete': CIMMethod(
                         'Delete', 'uint32',
                         qualifiers={
                             'Description': CIMQualifier(
                                 'Description', "qualifier description",
                                 overridable=True, tosubclass=True,
                                 translatable=True, propagated=True)},
                         class_origin='CIM_Foo',
                         propagated=True),
                     'Fuzzy': CIMMethod(
                         'Fuzzy', 'string',
                         qualifiers={
                             'Description': CIMQualifier(
                                 'Description', "qualifier description",
                                 overridable=True, tosubclass=True,
                                 translatable=True, propagated=True)},
                         class_origin='CIM_Foo',
                         propagated=True), },
             ),
             None, FAIL],

            ['Fails Create assoc class with no reference class',
             [],

             CIMClass("TST_Assoc",
                      qualifiers={'Association':
                                  CIMQualifier('Association', value=True)},
                      properties={CIMProperty('R1', None, type='reference',
                                              reference_class='NotExist'),
                                  CIMProperty('R2', None, type='reference',
                                              reference_class='NotExist')},
                      ),

             None, CIMError(CIM_ERR_INVALID_PARAMETER), OK],

            ['Fails Create assoc class with embedded instance, invalid class',
             ['CIM_Foo'],
             CIMClass(
                 'CIM_Foo_EmbeddedInstance', superclass='CIM_Foo',
                 properties={
                     'EmbeddInstContainer':
                         CIMProperty(
                             'EmbeddInstContainer', None,
                             qualifiers={
                                 'EmbeddedInstance': CIMQualifier(
                                     'EmbeddedInstance', 'NonExistantClass'),
                             },
                             type='string'),
                 }
             ),
             None, CIMError(CIM_ERR_INVALID_PARAMETER), OK],

            ['Create class with embedded instance, class None. Passes',
             [],
             CIMClass(
                 'CIM_Foo_EmbeddedInstance',
                 properties={
                     'InstanceID':
                         CIMProperty('InstanceID', "Blah", type='string',
                                     qualifiers={'Key':
                                                 CIMQualifier('Key', True)}, ),
                     'EmbeddInstContainer':
                         CIMProperty(
                             'EmbeddInstContainer', None,
                             qualifiers={
                                 'EmbeddedInstance': CIMQualifier(
                                     'EmbeddedInstance', None, type='string'),
                             },
                             type='string'),
                 }
             ),
             None, None, FAIL],

            ['Create subclass with embedded instance, class None. Passes',
             ['CIM_Foo'],
             CIMClass(
                 'CIM_Foo_EmbeddedInstance', superclass='CIM_Foo',
                 properties={
                     'EmbeddInstContainer':
                         CIMProperty(
                             'EmbeddInstContainer', None,
                             qualifiers={
                                 'EmbeddedInstance': CIMQualifier(
                                     'EmbeddedInstance', None, type='string'),
                             },
                             type='string'),
                 }
             ),
             None, None, FAIL],  # TODO: Fails in test resolve (override)

            ['Validate createclass with chass that already exists fails',
             ['CIM_Foo'],
             CIMClass('CIM_Foo'),
             None, CIMError(CIM_ERR_ALREADY_EXISTS), OK],

            # NOTE:No invalid namespace test defined because createclass creates
            # namespace if one does not exist
        ],
    )
    def test_createclass(self, conn, tst_qualifiers_mof, tst_classes, ns, desc,
                         pre_tst_classes, tst_cls, exp_rslt, exp_exc,
                         condition):
        # pylint: disable=no-self-use,protected-access,unused-argument
        """
            Test create class. Tests for namespace variable,
            correctly adding, and invalid add where class has superclass
            No way to do bad namespace error because this  method creates
            namespace if it does not exist.
        """
        if not condition:
            pytest.skip("This test marked to be skipped by condition")
        skip_if_moftab_regenerated()

        # preinstall required qualifiers
        conn.compile_mof_string(tst_qualifiers_mof, namespace=ns)

        # If pretcl, create/install the pre test class.  Installs the
        # prerequisite classes into the repository.
        if isinstance(pre_tst_classes, list):
            pre_tst_classes = NocaseList(pre_tst_classes)

        self.process_pretcl(conn, pre_tst_classes, ns, tst_classes)

        # Create the new_class to send to CreateClass from the
        # existing tst_classes (if tst_cls is a string) or class defined
        # for this test
        if isinstance(tst_cls, six.string_types):
            for cl_ in tst_classes:
                if cl_.classname == tst_cls:
                    new_class = cl_
        else:
            new_class = tst_cls

        if exp_exc is not None:
            with pytest.raises(type(exp_exc)) as exec_info:

                # The code to be tested
                conn.CreateClass(new_class, namespace=ns)

            exc = exec_info.value
            if isinstance(exp_exc, CIMError):
                assert exc.status_code == exp_exc.status_code

        else:
            # The code to be tested
            conn.CreateClass(new_class, namespace=ns)

            # Get class with LocalOnly=False and confirm against the
            # test class.
            get_cl = conn.GetClass(new_class.classname,
                                   namespace=ns,
                                   IncludeQualifiers=True,
                                   IncludeClassOrigin=True,
                                   LocalOnly=False)
            get_cl.path = None

            # test for propagated set
            for pname, pvalue in get_cl.properties.items():
                assert pvalue.propagated is not None
                if new_class.superclass is None:
                    assert pvalue.class_origin == new_class.classname
            for mname, mvalue in get_cl.methods.items():
                assert mvalue.propagated is not None
                if new_class.superclass is None:
                    assert mvalue.class_origin == new_class.classname

            # if expected rtn is a CIMClass, compare the classes
            if isinstance(exp_rslt, CIMClass):
                assert_classes_equal(get_cl, exp_rslt)

            # if exp_rslt is string, resolve item from tst_classes
            elif isinstance(exp_rslt, six.string_types):
                for cl_ in tst_classes:
                    if cl_.classname == exp_rslt:
                        clsr = resolve_class(conn, cl_, ns)
                        assert_classes_equal(clsr, get_cl)

            # if exp_rslt is None, resolve tst_cls or clean it up
            elif exp_rslt is None:
                if isinstance(tst_cls, CIMClass):
                    tst_cls_resolved = resolve_class(conn, tst_cls, ns)
                    assert_classes_equal(tst_cls_resolved, get_cl)
                else:
                    assert set(get_cl.properties) == \
                        set(new_class.properties)
                    assert set(get_cl.methods) == set(new_class.methods)
                    assert set(get_cl.qualifiers) == \
                        set(new_class.qualifiers)

            else:
                assert False, "test_create_class invalid test definition {}". \
                    format(desc)

            # Get the class with local only False. and test for valid
            # ico, lo and non-lo properties/methods.

            rslt_cls = conn.GetClass(new_class.classname,
                                     namespace=ns,
                                     IncludeQualifiers=True,
                                     IncludeClassOrigin=True,
                                     LocalOnly=False)
            ns = ns or conn.default_namespace
            class_store = conn.cimrepository.get_class_store(ns)
            superclasses = conn._mainprovider._get_superclass_names(
                new_class.classname, class_store)

            if new_class.superclass is None:
                superclass = None
            else:
                superclass = conn.GetClass(new_class.superclass, namespace=ns,
                                           IncludeQualifiers=True,
                                           IncludeClassOrigin=True,
                                           LocalOnly=False)
            # Issue #2327 FUTURE, 18: TODO: More specific tests for the
            # characteristics of resolving classes to assure that all resolved
            # parameters are correct for each test case.
            if superclass:
                for prop in superclass.properties:
                    assert prop in rslt_cls.properties
                for method in superclass.methods:
                    assert method in rslt_cls.methods

            # Test for correct qualifier attributes in create class
            for pname, pvalue in rslt_cls.properties.items():
                if superclass:
                    # If there is a superclass
                    if 'Override' in pvalue.qualifiers:
                        ov_qual = pvalue.qualifiers['Override']
                        sc_pname = ov_qual.value
                        if sc_pname in superclass.properties:
                            assert pvalue.propagated is True
                            assert pvalue.class_origin in superclasses
                            if pvalue.type != 'reference':
                                spvalue = superclass.properties[pname]
                                assert spvalue.type == pvalue.type
                            else:  # property type ref with override
                                spvalue = superclass.properties[sc_pname]
                                assert spvalue.type == pvalue.type
                        else:
                            assert False, "Override %s without property %s " \
                                          "in superclass" % (pname, sc_pname)
                    else:   # superclass but no override
                        if pname in superclass.properties:
                            assert pvalue.propagated is True
                            assert pvalue.class_origin in superclasses
                            assert pvalue.type == \
                                superclass.properties[pname].type
                        else:  # pname not in superclass properties
                            assert pvalue.propagated is False
                            assert pvalue.class_origin == rslt_cls.classname
                else:  # No superclass
                    assert pvalue.propagated is False
                    assert pvalue.class_origin == rslt_cls.classname

            for mname, mvalue in get_cl.methods.items():
                if superclass:
                    if 'Override' in mvalue.qualifiers:
                        sc_mname = mvalue.qualifiers['Override']
                        if sc_mname in superclass.methods:
                            assert mvalue.propagated is True
                            assert mvalue.class_origin == superclass.classname
                            if mvalue.type != 'reference':
                                assert superclass.pname == mname
                                smvalue = superclass.methods[mname]
                                assert smvalue.type == mvalue.type
                            else:  # property type ref with override
                                smvalue = superclass.methods[sc_mname]
                                assert smvalue.type == mvalue.type
                        else:
                            assert False, "Override %s without property %s " \
                                          "in superclass" % (pname, sc_mname)
                    else:   # superclass but no override
                        if mname in superclass.methods:
                            assert mvalue.propagated is True
                            assert mvalue.class_origin in superclasses
                            assert mvalue.return_type == \
                                superclass.methods[mname].return_type
                        else:
                            assert mvalue.propagated is False
                            assert mvalue.class_origin == rslt_cls.classname
                    for pname, pvalue in mvalue.parameters.items():
                        assert pname in superclass.methods[mname].parameters
                        assert pvalue == \
                            superclass.methods[mname].parameters[pname]
                else:
                    assert mvalue.propagated is False
                    assert mvalue.class_origin == rslt_cls.classname

    @pytest.mark.parametrize(
        "ns", INITIAL_NAMESPACES + [None])
    @pytest.mark.parametrize(
        "desc, pre_tst_mof, tst_cls_mof, exp_rslt, exp_exc, condition",
        [
            # desc: Description of testcase
            # pre_tst_classes: Create the defined class or classes before the
            #                  test. These are the superclasses for the new
            #                  class to be created
            #                  May be:
            #                   * pywbem CIMClass definition,
            #                   * string defining name of class in tst_classes
            #                   * list of class/classnames
            # tst_cls: MOF defining class to create
            # exp_rstl: None or expected CIMClass returned from GetClass for
            #             verifying the created class
            # exp_exc: None or expected exception object
            # condition: If False, skip this test

            ['Create class where qualifier wrong scope, fails (Key on class)',
             [],
             """
             [Key]
             class TST_Class1
                 {
                     string InstanceID;
                 };
             """,
             None, MOFDependencyError(''), OK],

            ['Create class where qualifier wrong scope, fails (Association '
             'on property)',
             [],
             """
             class TST_Class1
                 {
                     [Association]
                     string InstanceID;
                 };
             """,
             None, MOFDependencyError(''), OK],

            ['Create class where dependent class Embedded Obj does not exist)',
             [],
             '''
             class TST_Class1
                 {
                     [Key]
                     string InstanceID;
                     [EmbeddedObject("TST_BLAH")]
                     string ebo;
                 };
             ''',
             None, MOFDependencyError(''), OK],


            ['Create class where dependent class does not exist)',
             [],
             '''
             [Association]
             class TST_Class1
                 {
                     [Key]
                     string InstanceID;
                     TST_MISSING REF Target;
                     TST_MISSING2 REF Initiator;
                 };
             ''',
             None, MOFDependencyError(''), OK],

        ],
    )
    def test_createclass_mof_er(self, conn, tst_qualifiers_mof,
                                ns, desc, pre_tst_mof, tst_cls_mof, exp_rslt,
                                exp_exc, condition):
        # pylint: disable=no-self-use

        """
        Test for errors with compiled mof.  This tests for specific errors
        that can occur between the compiler and CreateClass.
        """
        if not condition:
            pytest.skip("This test marked to be skipped by condition")
        skip_if_moftab_regenerated()

        # preinstall required qualifiers
        conn.compile_mof_string(tst_qualifiers_mof, namespace=ns)

        # If pretcl, create/install the pre test class.  Installs the
        # prerequisite classes into the repository.
        if pre_tst_mof:
            conn.compile_mof_string(pre_tst_mof, namespace=ns)
        if exp_exc is not None:
            with pytest.raises(type(exp_exc)) as exec_info:

                # The code to be tested
                conn.compile_mof_string(tst_cls_mof, namespace=ns)

            exc = exec_info.value
            if isinstance(exp_exc, CIMError):
                assert exc.status_code == exp_exc.status_code, "{}".format(desc)

        else:
            assert exp_rslt is None
            assert False, "This part of test_createclass_mof_err not implemente"

    # Test ModifyClass
    @pytest.mark.parametrize(
        "ns", INITIAL_NAMESPACES + [None])
    @pytest.mark.parametrize(
        "desc, pre_tst_classes, has_insts, tst_cls, exp_rslt, exp_exc, "
        "condition",
        [
            # desc: Description of testcase for ModifyClass operation
            # pre_tst_classes: The classes in the repository
            #                  when ModifyClass on tst_cls
            #                  is executed
            #                  May be:
            #                   * pywbem CIMClass definition,
            #                   * string defining name of class in tst_classes
            #                   * list of class/classnames
            # has_insts: If True add instances for tst_cls
            # tst_cls: Either string defining test class name in tst_classes or
            #         CIMClass to be passed to CreateClass
            # exp_rstl: None or expected CIMClass returned from GetClass for
            #             verifying the created class
            # exp_exc: None or expected exception object
            # condition: If False, skip this test

            ['Modify CIM_Foo class, no superclass correctly replace CIM_Foo '
             'with same class',
             ['CIM_Foo'],  # Pre test classes list
             False,        # no install of instances
             'CIM_Foo',    # modified class
             CIMClass(     # Expected result
                 'CIM_Foo', superclass=None,
                 qualifiers={
                     'Description': CIMQualifier(
                         'Description', "CIM_Foo description",
                         overridable=True,
                         tosubclass=True,
                         translatable=True,
                         propagated=False)},
                 properties={
                     'InstanceID': CIMProperty(
                         'InstanceID', None,
                         qualifiers={
                             'Key': CIMQualifier(
                                 'Key', True, type='boolean',
                                 overridable=False,
                                 tosubclass=True,
                                 propagated=False), },
                         type='string', class_origin='CIM_Foo',
                         propagated=False), },
                 methods={
                     'Delete': CIMMethod(
                         'Delete', 'uint32',
                         qualifiers={
                             'Description': CIMQualifier(
                                 'Description', "qualifier description",
                                 overridable=True,
                                 tosubclass=True,
                                 translatable=True,
                                 propagated=False)},
                         class_origin='CIM_Foo',
                         propagated=False),
                     'Fuzzy': CIMMethod(
                         'Fuzzy', 'string',
                         qualifiers={
                             'Description': CIMQualifier(
                                 'Description', "qualifier description",
                                 overridable=True,
                                 tosubclass=True,
                                 translatable=True,
                                 propagated=False)},
                         class_origin='CIM_Foo',
                         propagated=False), },
             ),
             None, OK],

            ['Modify CIM_Foo_sub class, with superclass correctly replace '
             'with same class',
             ['CIM_Foo', 'CIM_Foo_sub'],  # Pre test classes list
             False,                       # no install of instances
             'CIM_Foo_sub',               # modified class
             CIMClass(                    # Expected result
                 'CIM_Foo_sub', superclass='CIM_Foo',
                 qualifiers={
                     'Description': CIMQualifier(
                         'Description', "Subclass Description",
                         overridable=True,
                         tosubclass=True,
                         translatable=True,
                         propagated=False)},
                 properties={
                     'InstanceID': CIMProperty(
                         'InstanceID', None,
                         qualifiers={
                             'Key': CIMQualifier(
                                 'Key', True, type='boolean',
                                 overridable=False,
                                 tosubclass=True,
                                 propagated=True)},
                         type='string', class_origin='CIM_Foo',
                         propagated=True),
                     'cimfoo_sub': CIMProperty(
                         'cimfoo_sub', None,
                         qualifiers={
                             'Description': CIMQualifier(
                                 'Description',
                                 'qualifier description',
                                 overridable=True,
                                 tosubclass=True,
                                 translatable=True,
                                 propagated=False)},
                         type='string', class_origin='CIM_Foo_sub',
                         propagated=False)},
                 methods={
                     'Delete': CIMMethod(
                         'Delete', 'uint32',
                         qualifiers={
                             'Description': CIMQualifier(
                                 'Description', "qualifier description",
                                 overridable=True,
                                 tosubclass=True,
                                 translatable=True,
                                 propagated=True)},
                         class_origin='CIM_Foo',
                         propagated=True),
                     'Fuzzy': CIMMethod(
                         'Fuzzy', 'string',
                         qualifiers={
                             'Description': CIMQualifier(
                                 'Description', "qualifier description",
                                 overridable=True,
                                 tosubclass=True,
                                 translatable=True,
                                 propagated=True)},
                         class_origin='CIM_Foo',
                         propagated=True), },
             ),
             None, OK],

            ['Modify CIM_Foo_sub class, modify only defines new properties',
             ['CIM_Foo', 'CIM_Foo_sub'],  # Pre test classes list
             False,                       # no install of instances
             # modified class with only new props
             CIMClass(
                 'CIM_Foo_sub', superclass='CIM_Foo',
                 qualifiers={
                     'Description': CIMQualifier(
                         'Description', 'Subclass Description')},
                 properties={
                     'cimfoo_sub':
                     CIMProperty('cimfoo_sub', None, type='string',
                                 qualifiers={'Description':
                                             CIMQualifier(
                                                 'Description',
                                                 'qualifier description')})}),
             CIMClass(                    # Expected result
                 'CIM_Foo_sub', superclass='CIM_Foo',
                 qualifiers={
                     'Description': CIMQualifier(
                         'Description', "Subclass Description",
                         overridable=True,
                         tosubclass=True,
                         translatable=True,
                         propagated=False)},
                 properties={
                     'InstanceID': CIMProperty(
                         'InstanceID', None,
                         qualifiers={
                             'Key': CIMQualifier(
                                 'Key', True, type='boolean',
                                 overridable=False,
                                 tosubclass=True,
                                 propagated=True)},
                         type='string', class_origin='CIM_Foo',
                         propagated=True),
                     'cimfoo_sub': CIMProperty(
                         'cimfoo_sub', None,
                         qualifiers={
                             'Description': CIMQualifier(
                                 'Description',
                                 'qualifier description',
                                 overridable=True,
                                 tosubclass=True,
                                 translatable=True,
                                 propagated=False)},
                         type='string', class_origin='CIM_Foo_sub',
                         propagated=False)},
                 methods={
                     'Delete': CIMMethod(
                         'Delete', 'uint32',
                         qualifiers={
                             'Description': CIMQualifier(
                                 'Description', "qualifier description",
                                 overridable=True,
                                 tosubclass=True,
                                 translatable=True,
                                 propagated=True)},
                         class_origin='CIM_Foo',
                         propagated=True),
                     'Fuzzy': CIMMethod(
                         'Fuzzy', 'string',
                         qualifiers={
                             'Description': CIMQualifier(
                                 'Description', "qualifier description",
                                 overridable=True,
                                 tosubclass=True,
                                 translatable=True,
                                 propagated=True)},
                         class_origin='CIM_Foo',
                         propagated=True), },
             ),
             None, OK],


            ['Modify CIM_Foo class, change property type, remove methods'
             'with same class',
             ['CIM_Foo'],  # Pre test classes list
             False,        # no install of instances
             # Modified class
             CIMClass(
                 'CIM_Foo', superclass=None,
                 qualifiers={},
                 properties={
                     'blahID': CIMProperty(
                         'blahID', None,
                         type='uint32')},
             ),
             # Expected result
             CIMClass(
                 'CIM_Foo', superclass=None,
                 qualifiers={},
                 properties={
                     'BlahID': CIMProperty(
                         'BlahID', None,
                         qualifiers={},
                         type='uint32', class_origin='CIM_Foo',
                         propagated=False), },
             ),
             None, OK],

            #
            # Test superclass names do not match
            #
            ['Modify CIM_Foo, Fails. Modify adds superclass name',
             ['CIM_Foo'],      # pre-test class list
             False,            # no install of instances
             # Modified class.
             CIMClass('CIM_Foo', superclass='CIM_Foo'),
             None,             # Expected result. Not used
             CIMError(CIM_ERR_INVALID_SUPERCLASS), OK],  # expect error response

            ['Modify CIM_Foo, Fails. orig/modified superclass do not match',
             ['CIM_Foo', 'CIM_Foo_sub'],      # pre-test class list
             False,                         # no install of instances
             # Modified class.
             CIMClass('CIM_Foo_sub', superclass='CIM_Foo_sub'),
             None,                          # Expected result. Not used
             CIMError(CIM_ERR_INVALID_SUPERCLASS), OK],  # expect error response


            ['Modify CIM_Foo, Fails. modify forgets superclass name',
             ['CIM_Foo', 'CIM_Foo_sub'],      # pre-test class list
             False,                         # no install of instances
             # Modified class.
             CIMClass('CIM_Foo_sub'),
             None,                          # Expected result. Not used
             CIMError(CIM_ERR_INVALID_SUPERCLASS), OK],  # expect error response

            #
            # Test general error responses
            #
            ['Modify CIM_Foo class, Fails, class does not exist, no superclass',
             [],  # pre-test class list
             False,                       # no install of instances
             'CIM_Foo',                   # Class to modif
             None,                        # Expected result. Not used
             CIMError(CIM_ERR_NOT_FOUND), OK],  # expect error response
            ['Modify CIM_Foo class, Fails, subclass exists',
             ['CIM_Foo', 'CIM_Foo_sub'],  # pre-test class list
             False,                       # no install of instances
             'CIM_Foo',                   # Class to modif
             None,                        # Expected result. Not used
             CIMError(CIM_ERR_CLASS_HAS_CHILDREN), OK],  # expect error response

            ['Modify CIM_Foo_sub class, Fails w superclass that does not exist',
             ['CIM_Foo'],      # pre-test class list
             False,            # no install of instances
             'CIM_Foo_sub',    # Class to modify
             None,             # Expected result. Not used
             CIMError(CIM_ERR_NOT_FOUND), OK],  # expect error response

            ['Modify CIM_Foo class, Fails. Invalid superclass',
             ['CIM_Foo'],                   # pre-test class list
             False,                # no install of instances
             CIMClass('CIM_Foo',   # Class to modify
                      superclass="CIM_NoExist",
                      properties={'InstanceID':
                                  CIMProperty('InstanceID', None,
                                              qualifiers={
                                                  'Key':
                                                  CIMQualifier('Key', True)},
                                              type='string')}),
             None,                       # Expected result. Not used
             CIMError(CIM_ERR_INVALID_SUPERCLASS), OK],  # expect err response

            ['Modify CIM_Foo class, Fails, instances exist, no superclass',
             ['CIM_Foo'],  # pre-test class list
             True,         # install instances
             'CIM_Foo',    # Class to modify
             None,         # Expected result. Not used
             CIMError(CIM_ERR_CLASS_HAS_INSTANCES), OK],  # expect err response

            ['Modify CIM_Foo_sub class, Fails, instances exist, has superclass',
             ['CIM_Foo', 'CIM_Foo_sub'],  # pre-test class list
             True,                        # install instances
             'CIM_Foo_sub',               # Class to modify
             None,                        # Expected result. Not used
             CIMError(CIM_ERR_CLASS_HAS_INSTANCES), OK],  # expect err response
        ],
    )
    def test_modifyclass(self, conn, tst_qualifiers_mof, tst_classes,
                         tst_instances, ns, desc, pre_tst_classes, has_insts,
                         tst_cls, exp_rslt, exp_exc, condition):
        # pylint: disable=no-self-use,protected-access,unused-argument
        """
            Test create class. Tests for namespace variable,
            correctly adding, and invalid add where class has superclass
            No way to do bad namespace error because this  method creates
            namespace if it does not exist.
        """
        if not condition:
            pytest.skip("This test marked to be skipped by condition")
        skip_if_moftab_regenerated()

        # preinstall required qualifiers
        conn.compile_mof_string(tst_qualifiers_mof, namespace=ns)

        # If pretcl, create/install the pre test class.  Installs the
        # prerequisite classes into the repository.

        if isinstance(pre_tst_classes, list):
            pre_tst_classes = NocaseList(pre_tst_classes)
        self.process_pretcl(conn, pre_tst_classes, ns, tst_classes)

        # Create the modified_class to send to ModifyClass from the
        # existing tst_classes (if tst_cls is a string) or class defined
        # for this test
        if isinstance(tst_cls, six.string_types):
            for cl_ in tst_classes:
                if cl_.classname == tst_cls:
                    modified_class = cl_
        else:
            modified_class = tst_cls

        # If has_insts is True, add instances for tst_class.
        if has_insts:
            for inst in tst_instances:
                if inst.classname.lower() == modified_class.classname.lower():
                    conn.CreateInstance(inst, namespace=ns)

        # Execute test code

        if exp_exc is not None:
            with pytest.raises(type(exp_exc)) as exec_info:

                # The code to be tested
                conn.ModifyClass(modified_class, namespace=ns)

            exc = exec_info.value
            if isinstance(exp_exc, CIMError):
                assert exc.status_code == exp_exc.status_code

        else:
            # The code to be tested
            conn.ModifyClass(modified_class, namespace=ns)

            # Get class with LocalOnly=False and confirm against the
            # test class.
            get_cl = conn.GetClass(modified_class.classname,
                                   namespace=ns,
                                   IncludeQualifiers=True,
                                   IncludeClassOrigin=True,
                                   LocalOnly=False)
            get_cl.path = None

            # test for propagated set
            for pname, pvalue in get_cl.properties.items():
                assert pvalue.propagated is not None
                if modified_class.superclass is None:
                    assert pvalue.class_origin == modified_class.classname
            for mname, mvalue in get_cl.methods.items():
                assert mvalue.propagated is not None
                if modified_class.superclass is None:
                    assert mvalue.class_origin == modified_class.classname

            # if expected rtn is a CIMClass, compare the classes
            if isinstance(exp_rslt, CIMClass):
                assert_classes_equal(get_cl, exp_rslt)

            # if exp_rslt is string, resolve item from tst_classes
            elif isinstance(exp_rslt, six.string_types):
                for cl_ in tst_classes:
                    if cl_.classname == exp_rslt:
                        clsr = resolve_class(conn, cl_, ns)
                        assert_classes_equal(clsr, get_cl)

            # if exp_rslt is None, resolve tst_cls or clean it up
            elif exp_rslt is None:
                if isinstance(tst_cls, CIMClass):
                    tst_cls_resolved = resolve_class(conn, tst_cls, ns)
                    assert_classes_equal(tst_cls_resolved, get_cl)
                else:
                    assert set(get_cl.properties) == \
                        set(modified_class.properties)
                    assert set(get_cl.methods) == set(modified_class.methods)
                    assert set(get_cl.qualifiers) == \
                        set(modified_class.qualifiers)

            else:
                assert False, "test_create_class invalid test definition {}". \
                    format(desc)

            # Get the class with local only False. and test for valid
            # ico, lo and non-lo properties/methods.

            rslt_cls = conn.GetClass(modified_class.classname,
                                     namespace=ns,
                                     IncludeQualifiers=True,
                                     IncludeClassOrigin=True,
                                     LocalOnly=False)
            ns = ns or conn.default_namespace
            class_store = conn.cimrepository.get_class_store(ns)
            superclasses = conn._mainprovider._get_superclass_names(
                modified_class.classname, class_store)

            if modified_class.superclass is None:
                superclass = None
            else:
                superclass = conn.GetClass(modified_class.superclass,
                                           namespace=ns,
                                           IncludeQualifiers=True,
                                           IncludeClassOrigin=True,
                                           LocalOnly=False)
            # Issue #2327 FUTURE, 18: TODO: More specific tests for the
            # characteristics of resolving classes to assure that all resolved
            # parameters are correct for each test case.
            if superclass:
                for prop in superclass.properties:
                    assert prop in rslt_cls.properties
                for method in superclass.methods:
                    assert method in rslt_cls.methods

            # Test for correct qualifier attributes in create class
            for pname, pvalue in rslt_cls.properties.items():
                if superclass:
                    # If there is a superclass
                    if 'Override' in pvalue.qualifiers:
                        ov_qual = pvalue.qualifiers['Override']
                        sc_pname = ov_qual.value
                        if sc_pname in superclass.properties:
                            assert pvalue.propagated is True
                            assert pvalue.class_origin in superclasses
                            if pvalue.type != 'reference':
                                spvalue = superclass.properties[pname]
                                assert spvalue.type == pvalue.type
                            else:  # property type ref with override
                                spvalue = superclass.properties[sc_pname]
                                assert spvalue.type == pvalue.type
                        else:
                            assert False, "Override %s without property %s " \
                                          "in superclass" % (pname, sc_pname)
                    else:   # superclass but no override
                        if pname in superclass.properties:
                            assert pvalue.propagated is True
                            assert pvalue.class_origin in superclasses
                            assert pvalue.type == \
                                superclass.properties[pname].type
                        else:  # pname not in superclass properties
                            assert pvalue.propagated is False
                            assert pvalue.class_origin == rslt_cls.classname
                else:  # No superclass
                    assert pvalue.propagated is False
                    assert pvalue.class_origin == rslt_cls.classname

            for mname, mvalue in get_cl.methods.items():
                if superclass:
                    if 'Override' in mvalue.qualifiers:
                        sc_mname = mvalue.qualifiers['Override']
                        if sc_mname in superclass.methods:
                            assert mvalue.propagated is True
                            assert mvalue.class_origin == superclass.classname
                            if mvalue.type != 'reference':
                                assert superclass.pname == mname
                                smvalue = superclass.methods[mname]
                                assert smvalue.type == mvalue.type
                            else:  # property type ref with override
                                smvalue = superclass.methods[sc_mname]
                                assert smvalue.type == mvalue.type
                        else:
                            assert False, "Override %s without property %s " \
                                          "in superclass" % (pname, sc_mname)
                    else:   # superclass but no override
                        if mname in superclass.methods:
                            assert mvalue.propagated is True
                            assert mvalue.class_origin in superclasses
                            assert mvalue.return_type == \
                                superclass.methods[mname].return_type
                        else:
                            assert mvalue.propagated is False
                            assert mvalue.class_origin == rslt_cls.classname
                    for pname, pvalue in mvalue.parameters.items():
                        assert pname in superclass.methods[mname].parameters
                        assert pvalue == \
                            superclass.methods[mname].parameters[pname]
                else:
                    assert mvalue.propagated is False
                    assert mvalue.class_origin == rslt_cls.classname

    @pytest.mark.parametrize(
        "ns", INITIAL_NAMESPACES + [None])
    @pytest.mark.parametrize(
        "cln, exp_exc",
        [
            # cln: ClassName input parameter for the operation
            # exp_exc: None or expected exception object

            ['CIM_Foo', None],
            ['CIM_Foo', None],
            ['CIM_Foox', CIMError(CIM_ERR_NOT_FOUND)],
            ['CIM_Foox', CIMError(CIM_ERR_NOT_FOUND)],
            # Invalid types
            [42, TypeError()],
            [None, TypeError()],
        ]
    )
    def test_deleteclass(self, conn, tst_qualifiers, tst_classes, ns, cln,
                         exp_exc):
        # pylint: disable=no-self-use
        """
            Test create class. Tests for namespace variable,
            correctly adding, and invalid add where class has superclass
        """
        add_objects_to_repo(conn, ns, [tst_qualifiers, tst_classes])

        if not exp_exc:

            # The code to be tested
            conn.DeleteClass(cln, namespace=ns)

            with pytest.raises(CIMError) as exec_info:
                conn.GetClass(cln, namespace=ns)
                exc = exec_info.value
                assert exc.status_code == CIM_ERR_NOT_FOUND
        else:
            with pytest.raises(type(exp_exc)) as exec_info:

                # The code to be tested
                conn.DeleteClass(cln, namespace=ns)

            exc = exec_info.value
            if isinstance(exp_exc, CIMError):
                assert exc.status_code == exp_exc.status_code


class TestInstanceOperations(object):
    """
    Test the Instance mock operations including get, enumerate, create
    delete, modify, execquery, and invoke method on instance.
    Associators and References are tested in separate test classes
    """

    @pytest.mark.parametrize(
        "tst_ns, inst_cln, inst_id, inst_ns, iq, ico, pl, exp_exc",
        [
            # tst_ns: Namespace to use for building repo
            # inst_cln: classname for the instance path for GetInstance()
            # inst_id: InstanceID key for the instance path for GetInstance()
            # inst_ns: Namespace for the instance path for GetInstance()
            #          If None, use tst_ns
            # iq:  Setting for IncludeQualifier parameter (True, False, None)
            # ico: IncludeClassOrigin parameter (True, False, None)
            # pl:  PropertyList parameter ("". None, string, list of strings)
            # exp_exc: None, or expected exception object

            # verify class and instance in default, use default
            [DEFAULT_NAMESPACE, 'CIM_Foo', 'CIM_Foo1', None,
             None, None, None, None],

            # Verify works with explicit inst_ns
            [DEFAULT_NAMESPACE, 'CIM_Foo', 'CIM_Foo1', None,
             None, None, None, None],

            # Test instance not found
            [DEFAULT_NAMESPACE, 'CIM_Foo', 'badid', None,
             None, None, None,
             CIMError(CIM_ERR_NOT_FOUND)],

            # Test invalid namespace
            [DEFAULT_NAMESPACE, 'CIM_Foo', 'CIM_Foo1', 'BadNamespace',
             None, None, None, CIMError(CIM_ERR_INVALID_NAMESPACE)],

            # Test Invalid classname
            [DEFAULT_NAMESPACE, 'CIM_Foox', 'CIM_Foo1',
             None, None, None, None, CIMError(CIM_ERR_INVALID_CLASS)],

            # Invalid classname on instance
            [DEFAULT_NAMESPACE, 'CIM_Foox', 'CIM_Foo1',
             None, None, None, None, CIMError(CIM_ERR_INVALID_CLASS)],

            # Invalid types
            [DEFAULT_NAMESPACE, 42, 'CIM_Foo1', None,
             None, None, None, TypeError()],

            # Test No classname
            [DEFAULT_NAMESPACE, None, 'CIM_Foo1', None,
             None, None, None, TypeError()],

            # Test Namespace is invalid type
            [DEFAULT_NAMESPACE, 'CIM_Foo', 'CIM_Foo1', 42,
             None, None, None, TypeError()],


            # Test IncludeQualifiers Flag False. NOTE: Implementation forces
            # False
            [DEFAULT_NAMESPACE, 'CIM_Foo', 'CIM_Foo1', None,
             False, None, None, None],
            [DEFAULT_NAMESPACE, 'CIM_Foo', 'CIM_Foo1', None,
             True, None, None, None],

            # Test IncludeClassOrigin
            [DEFAULT_NAMESPACE, 'CIM_Foo', 'CIM_Foo1', None,
             None, False, None, None],
            [DEFAULT_NAMESPACE, 'CIM_Foo', 'CIM_Foo1', None,
             None, False, None, None],


            # Test Propertylist
            [DEFAULT_NAMESPACE, 'CIM_Foo', 'CIM_Foo1', None,
             None, None, ["InstanceID"], None],
            [DEFAULT_NAMESPACE, 'CIM_Foo', 'CIM_Foo1', None,
             None, None, ["instanceid"], None],
            [DEFAULT_NAMESPACE, 'CIM_Foo', 'CIM_Foo1', None,
             None, None, "", None],

        ]
    )
    def test_getinstance(self, conn, tst_classeswqualifiers, tst_instances,
                         tst_ns, iq, ico, pl, inst_cln, inst_id, inst_ns,
                         exp_exc):
        # pylint: disable=no-self-use
        """
        Test with multiple namespaces for successful GetInstance and with
        error for namespace and instance name. This also tests the modifiale
        parameters.
        """

        add_objects_to_repo(conn, tst_ns, [tst_classeswqualifiers,
                                           tst_instances])

        if inst_ns is None:
            inst_ns = tst_ns
        if isinstance(inst_ns, six.string_types) and \
                isinstance(inst_cln, six.string_types):
            req_inst_path = CIMInstanceName(inst_cln, {'InstanceID': inst_id},
                                            namespace=inst_ns)
        else:
            assert exp_exc  # This must be an exception test
            # In this error case, use the (invalid) inst_ns directly
            req_inst_path = inst_ns

        if not exp_exc:
            # The code to be tested
            rslt_inst = conn.GetInstance(req_inst_path,
                                         IncludeQualifiers=iq,
                                         IncludeClassOrigin=ico,
                                         PropertyList=pl)

            # Get the original instance inserted into the repository
            org_inst = None
            org_inst_path = req_inst_path.copy()
            org_inst_path.namespace = None
            for inst in tst_instances:
                if inst.path == org_inst_path:
                    org_inst = inst
                    break
            assert org_inst, \
                "org_inst_path={}, inst_id={}".format(org_inst_path, inst_id)

            assert rslt_inst.path == req_inst_path
            assert rslt_inst.classname == org_inst.classname
            if IGNORE_INSTANCE_IQ_PARAM:
                assert not rslt_inst.qualifiers
                # TODO: There are no tests instances with qualifiers in the
                # model being tested. Therefore the else clause would not
                # gain anything

            if pl == "":
                assert not rslt_inst.properties
            if isinstance(pl, six.string_types):
                pl = [pl]
            if pl:
                pl = NocaseList(pl)
            for pname in rslt_inst.properties:
                rslt_prop = rslt_inst.properties[pname]
                org_prop = org_inst.properties[pname]
                if IGNORE_INSTANCE_IQ_PARAM:
                    assert not rslt_prop.qualifiers
                if IGNORE_INSTANCE_ICO_PARAM:
                    if ico:
                        assert rslt_prop.class_origin
                    else:
                        assert not rslt_prop.class_origin
                else:
                    assert not rslt_prop.class_origin
                if pl:
                    if org_prop.name not in NocaseList(pl):
                        continue
                assert rslt_prop.name == org_prop.name
                assert rslt_prop.value == org_prop.value
                assert rslt_prop.type == org_prop.type
                assert rslt_prop.array_size == org_prop.array_size
                assert rslt_prop.reference_class == org_prop.reference_class

        else:
            with pytest.raises(type(exp_exc)) as exec_info:

                # The code to be tested
                conn.GetInstance(req_inst_path,
                                 IncludeQualifiers=iq,
                                 IncludeClassOrigin=ico,
                                 PropertyList=pl)

            exc = exec_info.value
            if isinstance(exp_exc, CIMError):
                assert exc.status_code == exp_exc.status_code

    @pytest.mark.parametrize(
        "ns", INITIAL_NAMESPACES + [None])
    @pytest.mark.parametrize(
        "inst_id",
        # inst_id: InstanceID key for the instance path for GetInstance()
        ['CIM_Foo1', 'CIM_Foo2'])
    @pytest.mark.parametrize(
        "lo, iq, ico",
        [
            # lo: LocalOnly input parameter for GetInstance()
            # iq: IncludeQualifiers input parameter for GetInstance()
            # ico: IncludeClassOrigin input parameter for GetInstance()

            [None, None, None],
            [None, True, None],
            [None, True, True],
        ]
    )
    def test_getinstance_opts(self, conn, tst_classeswqualifiers,
                              tst_instances, ns, inst_id, lo, iq, ico):
        # pylint: disable=no-self-use
        """
        Test getting an instance from the repository with GetInstance and
        the various request options set
        """
        # TODO: This test has been recreated in test_getinstance.  It is
        # logical to remove this test after a review.

        add_objects_to_repo(conn, ns, [tst_classeswqualifiers, tst_instances])

        req_inst_path = CIMInstanceName(
            'CIM_Foo', {'InstanceID': inst_id}, namespace=ns)

        # The code to be tested
        rslt_inst = conn.GetInstance(req_inst_path, LocalOnly=lo,
                                     IncludeClassOrigin=ico,
                                     IncludeQualifiers=iq)

        rslt_inst.path.namespace = ns
        assert rslt_inst.path == req_inst_path

        # Because of the config variables qualifiers and classorigin are always
        # removed.
        if IGNORE_INSTANCE_IQ_PARAM:
            for prop_value in rslt_inst.properties.values():
                assert not prop_value.qualifiers
            assert not rslt_inst.qualifiers

        # Get the original instance inserted into the repository
        org_inst = None
        org_inst_path = req_inst_path.copy()
        org_inst_path.namespace = None
        for inst in tst_instances:
            if inst.path == org_inst_path:
                org_inst = inst
                break
        assert org_inst, \
            "org_inst_path={}, inst_id={}".format(org_inst_path, inst_id)

        assert rslt_inst.path == req_inst_path
        assert rslt_inst.classname == org_inst.classname
        for pname in rslt_inst.properties:
            rslt_prop = rslt_inst.properties[pname]
            org_prop = org_inst.properties[pname]
            assert not rslt_prop.qualifiers
            assert not rslt_prop.class_origin
            assert rslt_prop.name == org_prop.name
            assert rslt_prop.value == org_prop.value
            assert rslt_prop.type == org_prop.type
            assert rslt_prop.array_size == org_prop.array_size
            assert rslt_prop.reference_class == org_prop.reference_class

    # Test enumerateInstances with PropertyList parameter.
    @pytest.mark.parametrize(
        "ns", INITIAL_NAMESPACES + [None])
    @pytest.mark.parametrize(
        "inst_cln, inst_id, pl, exp_pl",
        [
            # inst_cln: classname for the instance path for GetInstance()
            # inst_id: InstanceID key for the instance path for GetInstance()
            # pl: property_list input parameter for GetInstance()
            # exp_pl: Expected list of property names in result instance

            # inst_cln  inst_id     pl     exp_pl
            # ['CIM_Foo', 'CIM_Foo1', None, ['InstanceID']],
            # ['CIM_Foo', 'CIM_Foo1', "", []],
            # ['CIM_Foo', 'CIM_Foo1', "blah", []],
            # ['CIM_Foo', 'CIM_Foo1', 'InstanceID', ['InstanceID']],
            # ['CIM_Foo', 'CIM_Foo1', ['InstanceID'], ['InstanceID']],
            # ['CIM_Foo', 'CIM_Foo1', ['INSTANCEID'], ['InstanceID']],
            ['CIM_Foo_sub', 'CIM_Foo_sub3', None, ['InstanceID', 'cimfoo_sub']],
            ['CIM_Foo_sub', 'CIM_Foo_sub3', "", []],
            ['CIM_Foo_sub', 'CIM_Foo_sub3', 'cimfoo_sub', ['cimfoo_sub']],
            ['CIM_Foo_sub', 'CIM_Foo_sub3', "blah", []],
            ['CIM_Foo_sub', 'CIM_Foo_sub3', 'InstanceID', ['InstanceID']],
            ['CIM_Foo_sub', 'CIM_Foo_sub3', ['INSTANCEID'], ['InstanceID']],
            ['CIM_Foo_sub', 'CIM_Foo_sub3', ['instanceid'], ['InstanceID']],
            ['CIM_Foo_sub', 'CIM_Foo_sub3', ['InstanceID', 'cimfoo_sub'],
             ['InstanceID', 'cimfoo_sub']],
        ]
    )
    def test_getinstance_pl(self, conn, tst_classeswqualifiers, tst_instances,
                            ns, inst_cln, inst_id, pl, exp_pl):
        # pylint: disable=no-self-use
        """
        Test the variations of property list against what is returned by
        GetInstance.
        """
        add_objects_to_repo(conn, ns, [tst_classeswqualifiers, tst_instances])

        request_inst_path = CIMInstanceName(
            inst_cln, {'InstanceID': inst_id}, namespace=ns)

        # The code to be tested
        rslt_inst = conn.GetInstance(request_inst_path, PropertyList=pl)

        rslt_inst.path.namespace = ns
        assert rslt_inst.path == request_inst_path

        # Assert expected returned properties matches returned properties
        assert set(NocaseList(exp_pl)) == set(NocaseList(rslt_inst.keys()))

    # test_enumerateinstancenames. Note that error tests are in separate test
    # below
    @pytest.mark.parametrize(
        "ns", EXPANDED_NAMESPACES + [None])
    @pytest.mark.parametrize(
        "cln", ['cim_foo', 'CIM_Foo', 'cim_foo_sub'])
    def test_enumerateinstancenames(self, conn, tst_classeswqualifiers,
                                    tst_instances, ns, cln):
        # pylint: disable=no-self-use
        """
        Test mock EnumerateInstanceNames against instances in tst_instances
        fixture with both classes and instances in the repo.  This test
        uses _get_subclass_names to get the names of the subclasses. Note that
        there are no special parameters on EnumerateInstanceNames.
        """

        add_objects_to_repo(conn, ns, [tst_classeswqualifiers, tst_instances])

        # The code to be tested
        rslt_instnames = conn.EnumerateInstanceNames(cln, ns)

        namespace = conn.default_namespace if ns is None else ns

        # get expected subclasses directly from repository.
        class_store = conn.cimrepository.get_class_store(namespace)
        # pylint: disable=protected-access
        exp_subclasses = conn._mainprovider._get_subclass_names(cln,
                                                                class_store,
                                                                True)
        exp_subclasses.append(cln)
        sub_class_dict = NocaseDict()
        for name in exp_subclasses:
            sub_class_dict[name] = name

        instance_store = conn.cimrepository.get_instance_store(namespace)
        request_inst_names = [i.path for i in instance_store.iter_values()
                              if i.classname in sub_class_dict]

        assert len(rslt_instnames) == len(request_inst_names)

        for inst_name in rslt_instnames:
            assert isinstance(inst_name, CIMInstanceName)
            assert inst_name in request_inst_names
            assert inst_name.classname in sub_class_dict

    # test_enumerateinstancenames_ns_er
    # See above for test of good return.
    @pytest.mark.parametrize(
        "tst_ns, cln, in_ns, exp_clns, exp_exc",
        [
            # tst_ns: repo namespace
            # cln: ClassName parameter for EnumerateInstances()
            # in_ns: namespace parameter for EnumerateInstances()
            # exp_clns: Expected class names in returned instances
            # exp_exc: None or expected exception object

            [DEFAULT_NAMESPACE, 'CIM_Foo', DEFAULT_NAMESPACE,
             ['CIM_Foo', 'CIM_Foo_sub', 'CIM_Foo_sub2', 'CIM_Foo_sub_sub'],
             None],
            [DEFAULT_NAMESPACE, 'CIM_Foo', None,
             ['CIM_Foo', 'CIM_Foo_sub', 'CIM_Foo_sub2', 'CIM_Foo_sub_sub'],
             None],
            [DEFAULT_NAMESPACE, 'CIM_Foo', 'BadNamespace', None,
             CIMError(CIM_ERR_INVALID_NAMESPACE)],
            [DEFAULT_NAMESPACE, 'CIM_Foox', None, None,
             CIMError(CIM_ERR_INVALID_CLASS)],
            # Invalid types
            [DEFAULT_NAMESPACE, 42, DEFAULT_NAMESPACE, None, TypeError()],
            [DEFAULT_NAMESPACE, None, DEFAULT_NAMESPACE, None, TypeError()],
            [DEFAULT_NAMESPACE, 'CIM_Foo', 42, None, TypeError()],
        ]
    )
    def test_enumerateinstancenames_ns_er(self, conn, tst_classeswqualifiers,
                                          tst_instances, tst_ns, cln, in_ns,
                                          exp_clns, exp_exc):
        # pylint: disable=no-self-use
        """
        Test basic successful operation with namespaces and test for
        namespace and classname errors.
        """
        add_objects_to_repo(conn, tst_ns, [tst_classeswqualifiers,
                                           tst_instances])

        enum_classname = 'CIM_Foo'
        exp_clns = [enum_classname, 'CIM_Foo_sub', 'CIM_Foo_sub2',
                    'CIM_Foo_sub_sub']

        ns = tst_ns or conn.default_namespace
        instance_store = conn.cimrepository.get_instance_store(ns)

        if not exp_exc:
            rtn_inst_names = conn.EnumerateInstanceNames(enum_classname, tst_ns)

            # pylint: disable=protected-access
            request_inst_names = [i.path for i in instance_store.iter_values()
                                  if i.classname in exp_clns]

            assert len(rtn_inst_names) == len(request_inst_names)

            for inst_name in rtn_inst_names:
                assert isinstance(inst_name, CIMInstanceName)
                assert inst_name in request_inst_names
                assert inst_name.classname in exp_clns

        else:
            with pytest.raises(type(exp_exc)) as exec_info:

                # The code to be tested
                conn.EnumerateInstanceNames(cln, in_ns)

            exc = exec_info.value
            if isinstance(exp_exc, CIMError):
                assert exc.status_code == exp_exc.status_code

    # test_enumerateinstances
    @pytest.mark.parametrize(
        "ns", EXPANDED_NAMESPACES + [None])
    @pytest.mark.parametrize(
        "cln, di, exp_clns, exp_pl",
        [
            # cln: ClassName input parameter for EnumerateInstances()
            # di: DeepInheritance input parameter for EnumerateInstances()
            # exp_clns: List of expected class names of result instances
            # exp_pl: Expected list of property names in result instance

            # di True, expect all subprops
            ['CIM_Foo', True,
             ['CIM_Foo', 'CIM_Foo_sub', 'CIM_Foo_sub2', 'CIM_Foo_sub_sub'],
             ['InstanceID', 'cimfoo_sub', 'cimfoo_sub2', 'cimfoo_sub_sub']],

            # di false, expect only one property.
            ['CIM_Foo', False,
             ['CIM_Foo', 'CIM_Foo_sub', 'CIM_Foo_sub2', 'CIM_Foo_sub_sub'],
             ['InstanceID']],
        ]
    )
    def test_enumerateinstances(self, conn, tst_classeswqualifiers,
                                tst_instances, ns, cln, di, exp_clns, exp_pl):
        # pylint: disable=no-self-use
        """
        Test mock EnumerateInstances. Returns instances
        of defined class and subclasses
        """

        add_objects_to_repo(conn, ns, (tst_classeswqualifiers, tst_instances))

        # The code to be tested
        rslt_insts = conn.EnumerateInstances(cln, namespace=ns,
                                             DeepInheritance=di)

        tst_inst_dict = {}
        for inst in tst_instances:
            tst_inst_dict[str(model_path(inst.path))] = inst

        # Issue: 2327 TODO: Future compute number returned. Right now fixed
        # number
        assert len(rslt_insts) == 12
        for inst in rslt_insts:
            assert isinstance(inst, CIMInstance)
            assert inst.classname in exp_clns

            mp = str(model_path(inst.path))
            assert mp in tst_inst_dict
            tst_inst = tst_inst_dict[mp]
            assert tst_inst is not None
            # if not di it reports fixed set of properties based parameters
            if not di:
                assert set(inst.keys()) == set(exp_pl)
            else:
                klass = conn.GetClass(inst.classname, namespace=ns,
                                      LocalOnly=False)
                cls_propnames = klass.properties.keys()
                inst_propnames = inst.properties.keys()
                assert sorted(NocaseList(cls_propnames)) == \
                    sorted(NocaseList(inst_propnames))

    # test_enumerateinstances_pl_di
    @pytest.mark.parametrize(
        "ns", INITIAL_NAMESPACES + [None])
    @pytest.mark.parametrize(
        "cln, di, pl, exp_pls",
        [
            # cln: ClassName input parameter for EnumerateInstances()
            # di: DeepInheritance input parameter for EnumerateInstances()
            # pl: PropertyList input parameter for EnumerateInstances()
            # exp_pls: Expected list of property names in result instances,
            #          or dict of those, by class name.

            # cln       di     pl     exp_pls
            ['CIM_Foo', False, None, ['InstanceID']],
            ['CIM_Foo', False, "", []],
            ['CIM_Foo', False, "blah", []],
            ['CIM_Foo', False, 'InstanceID', ['InstanceID']],
            ['CIM_Foo', False, ['InstanceID'], ['InstanceID']],
            ['CIM_Foo', False, ['INSTANCEID'], ['InstanceID']],
            ['CIM_Foo', False, ['instanceid'], ['InstanceID']],
            ['CIM_Foo_sub', False, None, ['InstanceID', 'cimfoo_sub']],
            ['CIM_Foo_sub', False, "", []],
            ['CIM_Foo_sub', False, 'cimfoo_sub', ['cimfoo_sub']],
            ['CIM_Foo_sub', False, "blah", []],
            ['CIM_Foo_sub', False, 'InstanceID', ['InstanceID']],
            ['CIM_Foo_sub', False, ['INSTANCEID'], ['InstanceID']],
            ['CIM_Foo_sub', False, ['instanceid'], ['InstanceID']],
            ['CIM_Foo_sub', False, ['InstanceID', 'cimfoo_sub'],
             ['InstanceID', 'cimfoo_sub']],
            ['CIM_Foo', True, None, {'CIM_Foo': ['InstanceID'],
                                     'CIM_Foo_sub': ['InstanceID',
                                                     'cimfoo_sub'],
                                     'CIM_Foo_sub2': ['InstanceID',
                                                      'cimfoo_sub2'],
                                     'CIM_Foo_sub_sub': ['InstanceID',
                                                         'cimfoo_sub',
                                                         'cimfoo_sub_sub']}],
            ['CIM_Foo', True, "", []],
            ['CIM_Foo', True, "blah", []],
            ['CIM_Foo', True, 'InstanceID', ['InstanceID']],
            ['CIM_Foo', True, ['InstanceID'], ['InstanceID']],
            ['CIM_Foo', True, ['INSTANCEID'], ['InstanceID']],
            ['CIM_Foo', True, ['instanceid'], ['InstanceID']],
            ['CIM_Foo', True, ['cimfoo_sub2'],
             {'CIM_Foo': [],
              'CIM_Foo_sub': [],
              'CIM_Foo_sub2': ['cimfoo_sub2'],
              'CIM_Foo_sub_sub': []}],
            ['CIM_Foo_sub', True, None,
             {'CIM_Foo_sub': ['InstanceID', 'cimfoo_sub'],
              'CIM_Foo_sub_sub': ['InstanceID',
                                  'cimfoo_sub',
                                  'cimfoo_sub_sub']}],
            ['CIM_Foo_sub', True, "", []],
            ['CIM_Foo_sub', True, 'cimfoo_sub', ['cimfoo_sub']],
            ['CIM_Foo_sub', True, "blah", []],
            ['CIM_Foo_sub', True, 'InstanceID', ['InstanceID']],
            ['CIM_Foo_sub', True, ['INSTANCEID'], ['InstanceID']],
            ['CIM_Foo_sub', True, ['instanceid'], ['InstanceID']],
            ['CIM_Foo_sub', True, ['InstanceID', 'cimfoo_sub'],
             ['InstanceID', 'cimfoo_sub']],
        ]
    )
    def test_enumerateinstances_pl_di(self, conn, tst_classeswqualifiers,
                                      tst_instances, ns, cln, di, pl, exp_pls):
        # pylint: disable=no-self-use
        """
        Test mock EnumerateInstances with namespace as an input
        optional parameter and a defined property list.

        """
        add_objects_to_repo(conn, ns, [tst_classeswqualifiers, tst_instances])

        # The code to be tested
        rslt_insts = conn.EnumerateInstances(cln, namespace=ns,
                                             DeepInheritance=di,
                                             PropertyList=pl)

        # If exp_props is dict, test for returned properties by class in
        # dict.  All returned classes must be in dict
        for inst in rslt_insts:
            assert isinstance(inst, CIMInstance)
            if isinstance(exp_pls, dict):
                exp_pl = exp_pls[inst.classname]
            else:
                exp_pl = exp_pls
            exp_pl = NocaseList(exp_pl)
            result_pl = NocaseList(inst.keys())
            assert set(result_pl) == set(exp_pl)

    @pytest.mark.parametrize(
        "ns", INITIAL_NAMESPACES + [None])
    @pytest.mark.parametrize(
        "cln, di, pl, exp_pl, exp_num_insts",
        [
            # cln: EnumerationClass (Required)
            # di: DeepInheritance input parameter for EnumerateInstances()
            #     NOTE: for None, mock_server uses True
            # pl: PropertyList input parameter for EnumerateInstances()
            # exp_pl: Expected list of property names in result instances
            # exp_num_insts: Expected number of result instances. Should
            # always be returning same number for a given class.
            #  cln        di    pl     exp_pl        exp_num_insts
            ['CIM_Foo', False, None, ['InstanceID'], 12],
            ['CIM_Foo', None, None, ['InstanceID', 'cimfoo_sub'], 12],
            ['CIM_Foo', True, None, ['InstanceID', 'cimfoo_sub'], 12],
            ['CIM_Foo', True, ['InstanceID'], ['InstanceID'], 12],
            ['CIM_Foo', None, ['cimfoo_sub'], ['cimfoo_sub'], 12],
            ['CIM_Foo', True, None, ['InstanceID'], 12],
            ['CIM_Foo', True, ['InstanceID'], ['InstanceID'], 12],
        ]
    )
    def test_enumerateinstances_di(self, conn, tst_classeswqualifiers,
                                   tst_instances, ns, cln, di, pl, exp_pl,
                                   exp_num_insts):
        # pylint: disable=no-self-use,unused-argument
        """
        Test EnumerateInstances with DeepInheritance and propertylist options.
        """
        add_objects_to_repo(conn, ns, [tst_classeswqualifiers, tst_instances])

        # The code to be tested
        rslt_insts = conn.EnumerateInstances(cln, namespace=ns,
                                             DeepInheritance=di,
                                             PropertyList=pl)

        assert len(rslt_insts) == exp_num_insts

        target_class = conn.GetClass(cln, namespace=ns, LocalOnly=False,
                                     PropertyList=pl)
        target_cls_propnames = sorted(
            NocaseList(target_class.properties.keys()))
        tst_cls_names = conn.EnumerateClassNames(ns, DeepInheritance=True)

        for inst in rslt_insts:
            assert isinstance(inst, CIMInstance)
            assert inst.classname in tst_cls_names
            exp_inst = conn.GetInstance(inst.path, PropertyList=pl)
            # Create list of property names for tests
            inst_propnames = sorted(NocaseList(inst.properties.keys()))

            # Force di to match server default
            # amd create exp_inst as a test instance to compare with returns.
            if di is None:
                di = True
            if di is False:
                # inst_property names must match class property names
                assert len(inst_propnames) == len(target_cls_propnames)
                assert inst_propnames == target_cls_propnames

                # Remove properties from exp_inst not in target_cls_propnames
                deletes = [n for n in exp_inst.properties.keys() if n not in
                           target_cls_propnames and n in exp_inst.properties]
                for pname in deletes:
                    del exp_inst.properties[pname]
            else:
                # Properties must match properties in class for this instance
                di_class = conn.GetClass(inst.classname, namespace=ns,
                                         LocalOnly=False,
                                         PropertyList=pl)
                assert inst_propnames == \
                    sorted(NocaseList(di_class.properties.keys()))
            # Test returned inst for equality with instance we built
            assert exp_inst == inst

    # test_enumerateinstances_er
    @pytest.mark.parametrize(
        "tst_ns, cln, in_ns, exp_exc",
        [
            # tst_ns: repo namespace
            # cln: ClassName parameter for EnumerateInstances()
            # in_ns: namespace parameter for EnumerateInstances()
            # exp_exc: Expected exception object

            [DEFAULT_NAMESPACE, None, DEFAULT_NAMESPACE, TypeError()],
            [DEFAULT_NAMESPACE, 'CIM_Foo', 'BadNamespace',
             CIMError(CIM_ERR_INVALID_NAMESPACE)],
            [DEFAULT_NAMESPACE, 'CIM_Foox', DEFAULT_NAMESPACE,
             CIMError(CIM_ERR_INVALID_CLASS)],
            # Invalid types
            [DEFAULT_NAMESPACE, 42, DEFAULT_NAMESPACE, TypeError()],
            [DEFAULT_NAMESPACE, None, DEFAULT_NAMESPACE, TypeError()],
            [DEFAULT_NAMESPACE, 'CIM_Foo', 42, TypeError()],
        ]
    )
    def test_enumerateinstances_er(self, conn, tst_classeswqualifiers,
                                   tst_instances, tst_ns, cln, in_ns, exp_exc):
        # pylint: disable=no-self-use
        """
        Test the various error cases for Enumerate.  Errors include:
        Invalid namespace, instance not_found and if a class is specified
        on input, shou
        """
        add_objects_to_repo(conn, tst_ns, [tst_classeswqualifiers,
                                           tst_instances])

        assert exp_exc

        with pytest.raises(type(exp_exc)) as exec_info:

            # The code to be tested
            conn.EnumerateInstances(cln, in_ns)

        exc = exec_info.value
        if isinstance(exp_exc, CIMError):
            assert exc.status_code == exp_exc.status_code

    # Test CreateInstance
    @pytest.mark.parametrize(
        "ns", EXPANDED_NAMESPACES + [None])
    @pytest.mark.parametrize(
        "test, new_inst, exp_rslt",
        [
            # test: integer that defines special modification within test
            #      execution. 0. Use new_instance as defined,
            #                 1. Set namespace to bad namespace,
            #                 2. Use the tst_instances list index defined in
            #                    new_inst parameter for new_instance param
            #                    with CreateInstance
            # new_inst: New instance to be passed to CreateInstance
            #           Integer: index into tst_instances.
            #           CIMInstance: CIMInstance to be passed to CreateInstance.
            # exp_rslt:    None: Compare based on test parameter
            #                    CIMInstance expected to be created. Tested by
            #                    doing GetInstance on the instance returned from
            #                    CreateInstance
            #              Not None: Expected exception object

            # The following test new_instance against specific instances
            # in exp_rslt using test definition # 2 and expecting good return
            # I.e. They compare the results to previously defined tests.
            [2, 0, None],
            [2, 1, None],
            [2, 4, None],
            [2, 5, None],
            [2, 7, None],

            # test simple new instance against predefined instance.
            [0, CIMInstance('CIM_Foo_sub',
                            properties={'InstanceID': 'inst1',
                                        'cimfoo_sub': 'blah'}),
             CIMInstance('CIM_Foo_sub',
                         properties={'InstanceID': 'inst1',
                                     'cimfoo_sub': 'blah'})],

            # test new instance has correct case on property names.
            [0, CIMInstance('CIM_Foo_sub',
                            properties={'instanceid': 'inst1',
                                        'CIMFOO_SUB': 'blah'}),
             CIMInstance('CIM_Foo_sub',
                         properties={'InstanceID': 'inst1',
                                     'cimfoo_sub': 'blah'})],

            # test invalid namespace
            [1, CIMInstance('CIM_Foo_sub',
                            properties={'InstanceID': 'inst1',
                                        'cimfoo_sub': 'data1'}),
             CIMError(CIM_ERR_INVALID_NAMESPACE)],

            # No key property in new instance
            [0, CIMInstance('CIM_Foo_sub',
                            properties={'cimfoo_sub': 'data2'}),
             CIMError(CIM_ERR_INVALID_PARAMETER)],

            # Test instance class not in repository
            [0, CIMInstance('CIM_Foo_subx',
                            properties={'InstanceID': 'inst1',
                                        'cimfoo_sub': 'data3'}),
             CIMError(CIM_ERR_INVALID_CLASS)],

            # Test invalid property. Property not in class
            [0, CIMInstance('CIM_Foo_sub',
                            properties={'InstanceID': 'inst1',
                                        'cimfoo_subx': 'wrong prop name'}),
             CIMError(CIM_ERR_INVALID_PARAMETER)],

            # Test invalid property in new instance, type not same as class
            [0, CIMInstance('CIM_Foo_sub',
                            properties={'InstanceID': 'inst1',
                                        'cimfoo_sub': Uint32(6)}),
             CIMError(CIM_ERR_INVALID_PARAMETER)],

            # test array type mismatch
            [0, CIMInstance('CIM_Foo_sub',
                            properties={'InstanceID': 'inst1',
                                        'cimfoo_sub': ['blah', 'blah']}),
             CIMError(CIM_ERR_INVALID_PARAMETER)],

            # Invalid types
            [0, CIMClass('CIM_Foo_sub'), TypeError()],
        ]
    )
    def test_createinstance(self, conn, tst_classeswqualifiers, tst_instances,
                            ns, test, new_inst, exp_rslt):
        # pylint: disable=no-self-use
        """
        Test creating an instance based on the clases in tst_classwqualifiers.
        Tests by creating an instance and then getting that instance.
        This also includes error tests if exp_exc is not None.
        This test is limited in scope because it starts with a set of simple
        classes.
        """

        add_objects_to_repo(conn, ns, tst_classeswqualifiers)

        # copy input instance to avoid poluting test
        if isinstance(new_inst, CIMInstance):
            new_inst = new_inst.copy()

        # modify input in accord with the test parameter
        if test == 0:   # pass on the new_inst defined in the parameter
            new_insts = [new_inst]
        elif test == 1:   # invalid namespace test
            ns = 'BadNamespace'
            new_insts = [tst_instances[0]]
        elif test == 2:  # Create one entry from the tst_instances list
            assert isinstance(new_inst, int)
            new_insts = [tst_instances[new_inst]]
        elif test == 3:   # create everything in tst_instances
            new_insts = tst_instances
        else:  # Error. Test not defined.
            assert False, "The test parameter %s not defined" % test
        if exp_rslt is None:
            for inst in new_insts:

                # The code to be tested
                rslt_inst_name = conn.CreateInstance(inst, ns)

                get_inst = conn.GetInstance(rslt_inst_name)
                rslt_cls = conn.GetClass(inst.classname,
                                         namespace=ns,
                                         LocalOnly=False,
                                         IncludeQualifiers=True)
                inst.path.namespace = get_inst.path.namespace
                assert get_inst.path == inst.path
                assert get_inst == inst
                # Execute case sensitive equality test on all properties in
                # returned instance against class properties
                for prop_name in get_inst:
                    c_prop_name = rslt_cls.properties[prop_name].name
                    assert c_prop_name == prop_name
        elif isinstance(exp_rslt, CIMInstance):
            inst = new_insts[0]   # assumes only a single instance to test.
            exp_inst = exp_rslt

            # The code to be tested
            rslt_inst_name = conn.CreateInstance(inst, ns)

            get_inst = conn.GetInstance(rslt_inst_name)
            inst.path = get_inst.path
            assert get_inst.path == inst.path
            assert get_inst == inst
            for prop_name in inst:
                exp_prop = exp_inst.properties[prop_name]
                get_prop = get_inst.properties[prop_name]
                # assert case-sensitive match
                assert get_prop.name == exp_prop.name

        else:
            exp_exc = exp_rslt
            with pytest.raises(type(exp_exc)) as exec_info:

                # The code to be tested
                conn.CreateInstance(new_insts[0], ns)

            exc = exec_info.value
            if isinstance(exp_exc, CIMError):
                assert exc.status_code == exp_exc.status_code

    # Issue 2327. Add test of CreateInstance with a complex class

    @pytest.mark.parametrize(
        "ns", INITIAL_NAMESPACES + [None])
    def test_createinstance_dup(self, conn, tst_classeswqualifiers,
                                tst_instances, ns):
        # pylint: disable=no-self-use
        """
        Test duplicate instance cannot be created.
        """
        conn.add_cimobjects(tst_classeswqualifiers, namespace=ns)

        new_inst = tst_instances[0]

        rslt_inst_name = conn.CreateInstance(new_inst, ns)
        get_inst = conn.GetInstance(rslt_inst_name)

        new_inst.path.namespace = get_inst.path.namespace
        assert get_inst.path == new_inst.path
        assert get_inst == new_inst

        # test add a second time.  Should generate exception.
        with pytest.raises(CIMError) as exec_info:

            # The code to be tested
            conn.CreateInstance(new_inst)

        exc = exec_info.value
        assert exc.status_code == CIM_ERR_ALREADY_EXISTS

    @pytest.mark.parametrize(
        "ns", INITIAL_NAMESPACES + [None])
    def test_createinstance_abstract(self, conn, ns):
        # pylint: disable=no-self-use
        """
        Test createinstance of an abstract class. This test generates exception
        """

        # Create the model environment, qualifier decls and class
        scopesc = NocaseDict([('CLASS', True), ('ASSOCIATION', True),
                              ('INDICATION', True), ('PROPERTY', False),
                              ('REFERENCE', False), ('METHOD', False),
                              ('PARAMETER', False), ('ANY', False)])

        scopesp = NocaseDict([('CLASS', False), ('ASSOCIATION', False),
                              ('INDICATION', True), ('PROPERTY', True),
                              ('REFERENCE', False), ('METHOD', False),
                              ('PARAMETER', False), ('ANY', False)])

        q1 = CIMQualifierDeclaration('Abstract', 'boolean', is_array=False,
                                     scopes=scopesc,
                                     overridable=False, tosubclass=True,
                                     toinstance=False, translatable=None)
        q2 = CIMQualifierDeclaration('key', 'boolean', is_array=False,
                                     scopes=scopesp,
                                     overridable=False, tosubclass=True,
                                     toinstance=False, translatable=None)
        qdecls = [q1, q2]

        c = CIMClass(
            'CIM_AbstractClass', qualifiers={'Abstract':
                                             CIMQualifier('Abstract', True)},
            properties={'InstanceID':
                        CIMProperty('InstanceID', None, type='string',
                                    qualifiers={'Key': CIMQualifier('Key',
                                                                    True)})})

        conn.add_cimobjects(qdecls, namespace=ns)
        conn.add_cimobjects([c], namespace=ns)

        # create the new instance
        new_inst = CIMInstance('CIM_AbstractClass',
                               properties={'InstanceID': "AbstractTestFail"})

        # test add a second time.  Should generate exception.
        with pytest.raises(CIMError) as exec_info:

            # The code to be tested
            conn.CreateInstance(new_inst)

        exc = exec_info.value
        assert exc.status_code == CIM_ERR_FAILED

    @pytest.mark.parametrize(
        "ns", INITIAL_NAMESPACES + [None])
    def test_compile_inst_abstract(self, conn, ns):
        # pylint: disable=no-self-use
        """
        Test compile that has an error compiling instance of abstract class
        """
        tst_mof = """
            Qualifier Abstract : boolean = false,
                Scope(class),
                Flavor(DisableOverride, ToSubclass);

             [ Abstract ]
        class CIM_Abstract {string InstanceID;};
        instance of CIM_Abstract {InstanceID="blah";};
        """
        skip_if_moftab_regenerated()

        with pytest.raises(MOFRepositoryError) as exec_info:
            # The code to be tested
            conn.compile_mof_string(tst_mof, namespace=ns)

        exc = exec_info.value
        assert exc.cim_error.status_code == CIM_ERR_FAILED

    @pytest.mark.parametrize(
        "interop_ns",
        # interop_ns: Interop ns (is added as default namespace to repo)
        ['interop', 'root/interop', 'root/PG_InterOp']
    )
    @pytest.mark.parametrize(
        "desc, additional_ns, new_ns, exp_ns, exp_exc",
        [
            # desc: Description of testcase
            # additional_ns: List of additional namespaces to add to repo
            # new_ns: Namespaces to be created as part of this test
            # exp_ns: None, or expected namespaces that has been created
            # exp_exc: None, or expected exception object

            (
                "Create namespace that does not exist yet, with already "
                "normalized name",
                [],
                'root/blah',
                'root/blah', None
            ),
            (
                "Create namespace that does not exist yet, with not yet "
                "normalized name",
                [],
                '//root/blah//',
                'root/blah', None
            ),
            (
                "Create namespace that already exists",
                ['root/blah'],
                CIMInstance('CIM_Namespace',
                            properties=dict(Name='root/blah')),
                None, CIMError(CIM_ERR_ALREADY_EXISTS)
            ),
            (
                "Create namespace with missing Name property in instance",
                ['root/blah'],
                CIMInstance('CIM_Namespace', properties={}),
                None, CIMError(CIM_ERR_INVALID_PARAMETER)
            ),
        ]
    )
    def test_createinstance_namespace(self, conn, tst_pg_namespace_class,
                                      desc, interop_ns, additional_ns, new_ns,
                                      exp_ns, exp_exc):
        # pylint: disable=no-self-use,unused-argument
        """
        Test the faked CreateInstance with a namespace instance to create ns.
        """

        pytest.skip("This test marked to be skipped. See test_systemproviders")
        # TODO: Future remove this test.

        schema = DMTFCIMSchema(DMTF_TEST_SCHEMA_VER, TESTSUITE_SCHEMA_DIR,
                               verbose=False)

        conn.install_namespace_provider(
            interop_ns,
            schema_pragma_file=schema.schema_pragma_file,
            verbose=False)

        for ns in additional_ns:
            conn.add_namespace(ns)

        if not exp_exc:

            # The code to be tested
            conn.add_namespace(new_ns)

            exp_namespaces = additional_ns
            exp_namespaces.extend([conn.default_namespace, interop_ns, new_ns])

            assert set(conn.namespaces) == set(exp_namespaces)

        else:
            with pytest.raises(type(exp_exc)) as exec_info:

                # The code to be tested
                conn.add_namespace(new_ns)

            exc = exec_info.value
            if isinstance(exp_exc, CIMError):
                assert exc.status_code == exp_exc.status_code

    @pytest.mark.parametrize(
        "ns", INITIAL_NAMESPACES + [None])
    @pytest.mark.parametrize(
        "tst_mof, exp_rslt, exp_exc",
        [
            # tst_mof: MOF string to be compiled into repo
            # exp_rslt: List of expected instance paths, as a tuple with items:
            #           0: Class name
            #           1: Dict of keybindings
            # exp_exc: None, or expected exception object

            # Compiler builds path
            ['instance of TST_Person as $Mike { name = "Mike"; };',
             ('TST_Person', {'name': "Mike"}), None],
            # Mocker builds path
            ['instance of TST_Person { name = "Mike"; };',
             ('TST_Person', {'name': "Mike"}), None],

            # Fails, because key property not in new instance
            ['instance of TST_Person {extraProperty = "Blah"; };',
             ('TST_Person', {}),
             MOFRepositoryError(
                 r"Cannot compile instance .* CreateInstance", None,
                 CIMError(CIM_ERR_INVALID_PARAMETER))],

            # Test assoc class with ref props as keys, mocker builds path
            ['instance of TST_Person as $Sofi { name = "Sofi"; };\n'
             'instance of TST_FamilyCollection as $Family1 '
             '{ name = "family1"; };\n'
             'instance of TST_MemberOfFamilyCollection '
             '{ family = $Family1; member = $Sofi; };\n',
             ('TST_MemberOfFamilyCollection',
              {'family': CIMInstanceName('TST_FamilyCollection',
                                         {'name': 'family1'}),
               'member': CIMInstanceName('TST_Person', {'name': "Sofi"})}),
             None],

            # Test assoc class withref props as keys, compiler builds path
            ['instance of TST_Person as $Sofi { name = "Sofi"; };\n'
             'instance of TST_FamilyCollection as $Family1 '
             '{ name = "family1"; };\n'
             'instance of TST_MemberOfFamilyCollection as $Family1Sofi'
             '{ family = $Family1; member = $Sofi; };\n',
             ('TST_MemberOfFamilyCollection',
              {'family': CIMInstanceName('TST_FamilyCollection',
                                         {'name': 'family1'}),
               'member': CIMInstanceName('TST_Person', {'name': "Sofi"})}),
             None],

            # Test assoc with one key reference property missing
            ['instance of TST_Person as $Sofi { name = "Sofi"; };\n'
             'instance of TST_FamilyCollection as $Family1 '
             '{ name = "family1"; };\n'
             'instance of TST_MemberOfFamilyCollection as $Family1Sofi'
             '{ family = $Family1; };\n',
             ('TST_MemberOfFamilyCollection',
              {'family': CIMInstanceName('TST_FamilyCollection',
                                         {'name': 'family1'}),
               'member': CIMInstanceName('TST_Person', {'name': "Sofi"})}),
             MOFRepositoryError(
                 r"Cannot compile instance .* CreateInstance", None,
                 CIMError(CIM_ERR_INVALID_PARAMETER))],
        ]
    )
    def test_compile_instances_path(self, conn, tst_assoc_class_mof, ns,
                                    tst_mof, exp_rslt, exp_exc):
        # pylint: disable=no-self-use
        """
        Test variations of compile of CIMInstances to validate the
        implementation of setting path. Both the compiler and mocker allow
        setting the path on CreateInstance.  This tests both
        good compile and errors
        """

        skip_if_moftab_regenerated()

        classes_mof = tst_assoc_class_mof + tst_mof
        if exp_exc is None:

            # The code to be tested
            conn.compile_mof_string(classes_mof, namespace=ns)

            exp_ns = ns or conn.default_namespace
            # Add namespace to any keybinding that is a CIMInstanceName
            kbs = exp_rslt[1]
            for kb, kbv in kbs.items():
                if isinstance(kbv, CIMInstanceName):
                    kbv.namespace = exp_ns
                    kbs[kb] = kbv
            exp_path = CIMInstanceName(exp_rslt[0], keybindings=exp_rslt[1],
                                       namespace=exp_ns)

            inst = conn.GetInstance(exp_path)
            assert inst.path == exp_path

        else:
            with pytest.raises(type(exp_exc)) as exec_info:

                # The code to be tested
                conn.compile_mof_string(classes_mof, namespace=ns)

            exc = exec_info.value
            if isinstance(exp_exc, CIMError):
                assert exc.status_code == exp_exc.status_code
            elif isinstance(exp_exc, MOFCompileError):
                assert re.search(exp_exc.msg, exc.msg, re.IGNORECASE)

    @pytest.mark.parametrize(
        "ns", EXPANDED_NAMESPACES + [None])
    @pytest.mark.parametrize(
        "desc, sp, nv, pl, exp_rslt, condition",
        [
            # desc: Description of test
            # sp: Special test. integer. 0 means No special test.
            #     other positive integers demand instance mod before modify
            # nv: (new value) single iterable  or iterable of iterables
            #     containing property name/value pairs that will modify the
            #     instance.
            # pl: property list for ModifyInstance or None. May be empty
            #   property list
            # exp_rslt: True if change expected. False if no change expected.
            #   Otherwise, expected exception object
            # condition: Condition. False, skip test, True, Run test,
            #                       'pdb'-debug

            ["1. change any property that is different",
             0, ['cimfoo_sub', 'newval'], None, True, OK],

            ["2. change any property that is different with prop case "
             "different",
             0, ['CIMFOO_SUB', 'newval'], None, True, OK],

            ["3. change any property that is different with PropertyList",
             0, ['cimfoo_sub', 'newval'], ['cimfoo_sub'], True, OK],

            ["4. Duplicate in property list",
             0, ['cimfoo_sub', 'newval'], ['cimfoo_sub', 'cimfoo_sub'], True,
             OK],

            ["5. Empty prop list, no change",
             0, ['cimfoo_sub', 'newval'], [], False, OK],

            ["6. pl for prop that does not change",
             0, ['cimfoo_sub', 'newval'], ['cimfoo_sub_sub'], False, OK],

            ["7. Change any property that is different",
             0, ['cimfoo_sub_sub', 'newval'], None, True, OK],

            ["8. Change a property",
             0, ['cimfoo_sub_sub', 'newval'], ['cimfoo_sub_sub'], True, OK],

            ["9. Empty prop list, no change",
             0, ['cimfoo_sub_sub', 'newval'], [], False, OK],

            ["10. Property name not in class but in Property list",
             0, ['cimfoo_sub', 'newval'], ['cimfoo_sub', 'not_in_class'],
             CIMError(CIM_ERR_INVALID_PARAMETER), OK],

            ["11. Change any property that is different, no prop list",
             0, [('cimfoo_sub', 'newval'),
                 ('cimfoo_sub_sub', 'newval2'), ], None, True, OK],

            ["12. Change any property that is different, no prop list, "
             "property casedifferences",
             0, [('CIMFOO_SUB', 'newvalx'),
                 ('CIMFOO_SUB_sub', 'newval2x'), ], None, True, OK],

            ["13. Invalid change, change key property",
             # This fails with NOT_FOUND because modify instance property
             # also modifies path.
             0, ['InstanceID', 'newval'], None, CIMError(CIM_ERR_NOT_FOUND),
             OK],

            ["13a. Invalid change, key property. test 8 sets instance path",
             8, ['InstanceID', 'newval'], None,
             CIMError(CIM_ERR_INVALID_PARAMETER), OK],

            ["14. Bad namespace. Depends on special code in path",
             2, ['cimfoo_sub', 'newval'], None,
             CIMError(CIM_ERR_INVALID_NAMESPACE), OK],

            ["15. Path and instance classnames differ. Changes inst classname",
             1, ['cimfoo_sub', 'newval'], None,
             CIMError(CIM_ERR_INVALID_PARAMETER), OK],

            ["16. Path has bad classname",
             3, ['cimfoo_sub', 'newval'], None,
             CIMError(CIM_ERR_INVALID_PARAMETER), OK],

            ["17. Path has bad classname",
             4, ['cimfoo_sub', 'newval'], None,
             CIMError(CIM_ERR_INVALID_CLASS), OK],

            ["18. no properties in modified instance",
             5, [], None, False, OK],

            ["19. Invalid type for modified_instance",
             6, [], None, TypeError(), OK],

            ["20. Invalid type for PropertyList",
             7, [], None, TypeError(), OK],
        ]
    )
    def test_modifyinstance(self, conn, tst_classeswqualifiers, tst_instances,
                            desc, ns, sp, nv, pl, exp_rslt, condition):
        # pylint: disable=no-self-use
        """
        Test the mock of modifying an existing instance. Gets the instance
        from the repo, modifies propertyiesand calls ModifyInstance. Allows
        testing against a variety of errors with the sp parameter which
        defines variations to the input parameters

        Test a specific class
        """
        if not condition:
            pytest.skip("This test marked to be skipped by condition")

        if condition == 'pdb':
            import pdb  # pylint: disable=import-outside-toplevel
            pdb.set_trace()  # pylint: disable=forgotten-debug-statement

        add_objects_to_repo(conn, ns, [tst_classeswqualifiers, tst_instances])

        # Get an instance from the CIM_Foo_sub_sub class to use as orig_instance
        insts = conn.EnumerateInstances('CIM_Foo_sub_sub', namespace=ns)
        assert insts, "desc {}".format(desc)
        orig_instance = insts[0]
        modified_instance = orig_instance.copy()

        # Modify properties as defined in nv parameter
        if nv:
            # if first items is string, this is a single modification
            # since that item would be the name of the property to modify.
            if isinstance(nv[0], six.string_types):
                nv = [nv]
            for property_def in nv:
                # NOTE: If key property changes, the path is also changed.
                # Since pywbem 1.1.0, this issues a DeprecationWarning.
                # The following does not expect any warnings, but catches
                # and tolerates all warnings.
                with pytest.warns(None):
                    modified_instance[property_def[0]] = property_def[1]

        # Code to change characteristics of modify_instance test based on
        # sp parameter. Changes classname, namespace name, etc.

        if sp == 0:  # Basic ModifyInstanceTest. No params changed
            pass
        elif sp == 1:  # Test for class does not exist
            modified_instance.classname = 'CIM_NoSuchClass'
        elif sp == 2:  # submit invalid namespace
            modified_instance.path.namespace = 'BadNamespace'
        elif sp == 3:  # test modifies classname
            modified_instance.path.classname = 'changedpathclassname'
        elif sp == 4:  # Nonexistent class test
            modified_instance.path.classname = 'CIM_NoSuchClass'
            modified_instance.classname = 'CIM_NoSuchClass'
        elif sp == 5:
            modified_instance.properties = NocaseDict()  # No properties
        elif sp == 6:
            modified_instance = 42  # Invalid type
        elif sp == 7:
            pl = 42  # Invalid type
        elif sp == 8:
            if orig_instance.path != modified_instance.path:
                modified_instance.path = orig_instance.path
        else:
            assert False

        if isinstance(exp_rslt, Exception):
            exp_exc = exp_rslt
            with pytest.raises(type(exp_exc)) as exec_info:

                # The code to be tested
                conn.ModifyInstance(modified_instance, PropertyList=pl)

            exc = exec_info.value
            if isinstance(exp_exc, CIMError):
                assert exc.status_code == exp_exc.status_code
        else:

            # The code to be tested
            conn.ModifyInstance(modified_instance, PropertyList=pl)

            get_inst = conn.GetInstance(modified_instance.path)
            tst_class = conn.GetClass(modified_instance.path.classname,
                                      modified_instance.path.namespace,
                                      LocalOnly=False)
            if exp_rslt:
                for p in get_inst:
                    assert get_inst.properties[p] == \
                        modified_instance.properties[p]
                    assert get_inst.properties[p].name == \
                        tst_class.properties[p].name
            else:
                for p in get_inst:
                    assert get_inst.properties[p] == \
                        orig_instance.properties[p]
                    assert get_inst.properties[p].name == \
                        tst_class.properties[p].name

    @pytest.mark.parametrize(
        # defines the namespace to be used.
        "ns", EXPANDED_NAMESPACES + [None])
    @pytest.mark.parametrize(
        "cln, inst_id, exp_exc",
        [
            # cln : Class name
            # inst_id: None or InstanceID key for non-existing instance
            # exp_exc: None or expected exception object

            ['CIM_Foo', None, None],                   # valid class
            ['CIM_Foo_sub', None, None],               # valid subclass
            ['CIM_Foo', 'xxx',
             CIMError(CIM_ERR_NOT_FOUND)],   # instance not found
            ['CIM_DoesNotExist', 'blah',
             CIMError(CIM_ERR_INVALID_CLASS)],  # class not found
            ['CIM_Foo', 'blah',
             CIMError(CIM_ERR_INVALID_NAMESPACE)],  # namespace not found
            # Invalid types
            [42, 'blah', TypeError()],  # Invalid ClassName
            [None, 'blah', TypeError()],  # Invalid ClassName
        ]
    )
    def test_deleteinstance(self, conn, tst_classeswqualifiers, tst_instances,
                            ns, cln, inst_id, exp_exc):
        # pylint: disable=no-self-use
        """
        Test delete instance by inserting instances into the repository
        and then deleting them. Deletes all instances that are in cln and
        subclasses.

        Error cases confirm that exp_exc is raised.
        """

        add_objects_to_repo(conn, ns, [tst_classeswqualifiers, tst_instances])

        if not exp_exc:
            # Test deletes all instances for defined class
            inst_name_list = conn.EnumerateInstanceNames(cln, ns)
            for iname in inst_name_list:

                # The code to be tested
                conn.DeleteInstance(iname)

            for iname in inst_name_list:
                with pytest.raises(CIMError) as exec_info:

                    # The code to be tested
                    conn.DeleteInstance(iname)

                exc = exec_info.value
                assert exc.status_code == CIM_ERR_NOT_FOUND
        else:
            tst_ns = ns or conn.default_namespace
            if isinstance(exp_exc, CIMError) and \
                    exp_exc.status_code == CIM_ERR_INVALID_NAMESPACE:
                tst_ns = 'BadNamespaceName'

            if isinstance(cln, six.string_types):
                iname = CIMInstanceName(
                    cln, keybindings={'InstanceID': inst_id}, namespace=tst_ns)
            else:
                # Use cln as input path directly to trigger error
                iname = cln

            with pytest.raises(type(exp_exc)) as exec_info:

                # The code to be tested
                conn.DeleteInstance(iname)

            exc = exec_info.value
            if isinstance(exp_exc, CIMError):
                assert exc.status_code == exp_exc.status_code

    @pytest.mark.parametrize(
        "interop_ns",
        ['interop', 'root/interop', 'root/PG_InterOp']
    )
    @pytest.mark.parametrize(
        "desc, additional_objs, new_inst, delete, exp_ns, exp_exc",
        [
            # desc: Description of testcase
            # additional_objs: Additional objects to be added to repo, as a
            #                  dict by namespace
            # new_inst: CIMInstance of the namespace class, that is first
            #           added (and deleted if delete is True) to obtain
            #           its instance path.
            # delete: Boolean indicating whether the CIMInstance of the
            #         namespace class should be deleted again.
            # exp_ns: None, or expected namespaces that has been created
            # exp_exc: None, or expected exception object

            (
                "Delete namespace that exists and is empty, with already "
                "normalized name",
                {},
                CIMInstance('PG_Namespace',
                            properties=dict(Name='root/blah')),
                False,
                'root/blah', None
            ),
            (
                "Delete namespace that exists and is empty, with not yet "
                "normalized name",
                {},
                CIMInstance('PG_Namespace',
                            properties=dict(Name='//root/blah//')),
                False,
                'root/blah', None
            ),
            (
                "Delete namespace that does not exist",
                {},
                CIMInstance('PG_Namespace',
                            properties=dict(Name='root/blah')),
                True,
                None, CIMError(CIM_ERR_NOT_FOUND)
            ),
            (
                "Delete namespace that exists but contains a class",
                {'root/blah': [CIMClass('CIM_Foo')]},
                CIMInstance('PG_Namespace',
                            properties=dict(Name='root/blah')),
                False,
                None, CIMError(CIM_ERR_NAMESPACE_NOT_EMPTY)
            ),
            (
                "Delete namespace that exists but contains an instance",
                {'root/blah': [
                    CIMInstance(
                        'CIM_Foo',
                        path=CIMInstanceName(
                            'CIM_Foo', keybindings=dict(InstanceID='foo1'))
                    )
                ]},
                CIMInstance('PG_Namespace',
                            properties=dict(Name='root/blah')),
                False,
                None, CIMError(CIM_ERR_NAMESPACE_NOT_EMPTY)
            ),
            (
                "Delete namespace that exists but contains a qualifier",
                {'root/blah': [
                    CIMQualifierDeclaration('Qual', type='string')
                ]},
                CIMInstance('PG_Namespace',
                            properties=dict(Name='root/blah')),
                False,
                None, CIMError(CIM_ERR_NAMESPACE_NOT_EMPTY)
            ),
        ]
    )
    def test_deleteinstance_namespace(
            self, conn, tst_pg_namespace_class, tst_qualifiers,
            desc, interop_ns, additional_objs, new_inst, delete, exp_ns,
            exp_exc):
        # pylint: disable=no-self-use,unused-argument
        """
        Test the faked DeleteInstance with a namespace instance to delete ns.
        """

        pytest.skip("This test marked to be skipped, superceeded")
        # Issue # 2327: TODO This Test can be deleted
        # This test is superceeded by test of the namespace
        # provider in the file test_system_providers.

        add_objects_to_repo(conn, interop_ns, [tst_qualifiers,
                                               tst_pg_namespace_class])

        # Because it is complex to build the instance path of the namespace
        # instance, we create it to obtain its instance path,
        # and the case of a non-existng namespace is swet up by deleting
        # the namespace again.
        new_path = conn.CreateInstance(new_inst, namespace=interop_ns)
        if delete:
            conn.DeleteInstance(new_path)

        for ns in additional_objs:
            if ns not in conn.namespaces:
                conn.add_namespace(ns)
            conn.add_cimobjects(additional_objs[ns], namespace=ns)

        if not exp_exc:
            # The code to be tested
            conn.DeleteInstance(new_path)

            act_ns = new_path.keybindings['Name']
            assert act_ns not in conn.namespaces

        else:
            with pytest.raises(type(exp_exc)) as exec_info:

                # The code to be tested
                conn.DeleteInstance(new_path)

            exc = exec_info.value
            if isinstance(exp_exc, CIMError):
                assert exc.status_code == exp_exc.status_code


class TestPullOperations(object):
    """
    Test the Open and pull operations.
    """

    @pytest.mark.parametrize(
        "ns", EXPANDED_NAMESPACES + [None])
    @pytest.mark.parametrize(
        "src_class, maxobj, exp_open_eos, fql, fq, exp_exec",
        [
            # src_class: Source instance definitions (classname and name
            #             property
            # maxobj: Max object count for each operation
            # exp_eos: If True, eos expected on open request
            # fql: Filter query Language
            # fq: Filter query
            # exp_exec: None or expected exception

            ['TST_Person', 100, True, None, None, None],
            ['TST_Person', 1, False, None, None, None],
            ['TST_Person', 2, False, None, None, None],

            # TODO: This test implemented for this operation but not others
            ['TST_Person', 100, True, "DMTF:FQL", None, None],
            ['TST_Person', 1, False, "DMTF:FQL", "Select from *", None],
            ['TST_Person', 100, True, "DMTF:CQL", None, CIMError],
            ['TST_Person', 2, False, None, "Select from *", CIMError],
        ]
    )
    def test_openenumerateinstancepaths(self, conn, tst_assoc_mof, ns,
                                        src_class, maxobj, exp_open_eos,
                                        fql, fq, exp_exec):
        # pylint: disable=no-self-use,invalid-name
        """
        Test openenueratepaths for a variety of MaxObjectCount values and
        FilterQuery options validity.
        """
        skip_if_moftab_regenerated()

        add_objects_to_repo(conn, ns, [tst_assoc_mof])

        orig_instnames = conn.EnumerateInstanceNames(src_class, namespace=ns)

        rslt_instnames = []

        # The code to be tested
        if exp_exec:
            with pytest.raises(exp_exec):
                result_tuple = conn.OpenEnumerateInstancePaths(
                    src_class, namespace=ns, MaxObjectCount=maxobj,
                    FilterQueryLanguage=fql, FilterQuery=fq)

        else:
            result_tuple = conn.OpenEnumerateInstancePaths(
                src_class, namespace=ns, MaxObjectCount=maxobj,
                FilterQueryLanguage=fql, FilterQuery=fq)

            rslt_instnames.extend(result_tuple.paths)

            assert result_tuple.eos == exp_open_eos
            if exp_open_eos is False:
                while result_tuple.eos is False:
                    result_tuple = conn.PullInstancePaths(
                        result_tuple.context, MaxObjectCount=maxobj)
                    rslt_instnames.extend(result_tuple.paths)

            assert len(rslt_instnames) == len(orig_instnames)

            assert set(rslt_instnames) == set(orig_instnames)

    @pytest.mark.parametrize(
        "ns", EXPANDED_NAMESPACES + [None])
    @pytest.mark.parametrize(
        "src_class, maxobj, exp_open_eos",
        [
            # src_class: Source instance definitions (classname and name
            #            property
            # maxobj: Max object count for each operation
            # exp_eos: If True, eos expected on open request

            ['TST_Person', 100, True],
            ['TST_Person', 1, False],
            ['TST_Person', 2, False],
        ]
    )
    def test_openenumerateinstances(self, conn, tst_assoc_mof, ns,
                                    src_class, maxobj, exp_open_eos):
        # pylint: disable=no-self-use,invalid-name
        """
        Test openenueratepaths for a variety of MaxObjectCount values.
        """
        skip_if_moftab_regenerated()

        add_objects_to_repo(conn, ns, [tst_assoc_mof])

        orig_instances = conn.EnumerateInstances(src_class, namespace=ns)

        rslt_instances = []

        # The code to be tested
        result_tuple = conn.OpenEnumerateInstances(
            src_class, namespace=ns, MaxObjectCount=maxobj)

        rslt_instances.extend(result_tuple.instances)

        assert result_tuple.eos == exp_open_eos
        if exp_open_eos is False:
            while result_tuple.eos is False:
                result_tuple = conn.PullInstancesWithPath(
                    result_tuple.context, MaxObjectCount=maxobj)
                rslt_instances.extend(result_tuple.instances)

        assert len(rslt_instances) == len(orig_instances)

        assert set(rslt_instances) == set(orig_instances)

    @pytest.mark.parametrize(
        "ns", EXPANDED_NAMESPACES + [None])
    @pytest.mark.parametrize(
        "src_inst, ro, rc, exp_rslt",
        [
            # src_inst: If list/tuple: Source instance definitions (classname
            #           and name property). Otherwise, invalid value for
            #           instance_path parameter of the op.
            # ro: Role
            # rc: ResultClass
            # exp_rslt: list of tuples where each tuple is class and key for
            #           inst, or expected exception object

            [('TST_Person', 'Mike'), None, 'TST_Lineage',
             [('TST_Lineage', 'MikeSofi'),
              ('TST_Lineage', 'MikeGabi')]],

            [('TST_Person', 'Saara'), None, 'TST_Lineage',
             [('TST_Lineage', 'SaaraSofi'), ]],

            [('TST_Person', 'Saara'), None, 'TST_Lineage',
             CIMError(CIM_ERR_INVALID_NAMESPACE)],

            # Invalid types
            [42, None, None, TypeError()],
            [None, None, None, TypeError()],
        ]
    )
    def test_openreferenceinstancepaths(self, conn, tst_assoc_mof, ns,
                                        src_inst, ro, rc, exp_rslt):
        # pylint: disable=no-self-use,invalid-name
        """
        Test openenueratepaths where the open is the complete response
        and all parameters are default
        """
        skip_if_moftab_regenerated()

        add_objects_to_repo(conn, ns, [tst_assoc_mof])

        if isinstance(src_inst, (list, tuple)):
            source_inst_name = CIMInstanceName(
                src_inst[0], keybindings=dict(name=src_inst[1]), namespace=ns)
        else:
            assert isinstance(exp_rslt, Exception)
            source_inst_name = src_inst  # Specifies invalid type directly

        if isinstance(exp_rslt, (list, tuple)):

            # The code to be tested
            result_tuple = conn.OpenReferenceInstancePaths(source_inst_name,
                                                           ResultClass=rc,
                                                           Role=ro)

            assert result_tuple.eos is True
            assert result_tuple.context is None

            exp_ns = ns or conn.default_namespace

            # build list of expected paths from exp_rslt
            exp_paths = []
            for exp in exp_rslt:
                exp_paths.append(CIMInstanceName(
                    exp[0],
                    keybindings=dict(InstanceID=exp[1]),
                    namespace=exp_ns,
                    host=conn.host))

            rslt_paths = result_tuple.paths

            assert_equal_ciminstancenames(rslt_paths, exp_paths)
        else:
            exp_exc = exp_rslt
            if isinstance(exp_exc, CIMError) and \
                    exp_exc.status_code == CIM_ERR_INVALID_NAMESPACE:
                source_inst_name.namespace = 'BadNamespaceName'
            with pytest.raises(type(exp_exc)) as exec_info:

                # The code to be tested
                conn.OpenReferenceInstancePaths(source_inst_name,
                                                ResultClass=rc,
                                                Role=ro)

            exc = exec_info.value
            if isinstance(exp_exc, CIMError):
                assert exc.status_code == exp_exc.status_code

    @pytest.mark.parametrize(
        "ns", INITIAL_NAMESPACES + [None])
    @pytest.mark.parametrize(
        "src_inst, ro, ac, rc, rr, exp_rslt",
        [
            # src_inst: If list/tuple: Source instance definitions (classname
            #           and name property). Otherwise, invalid value for
            #           instance_path parameter of the op.
            # ro: Role
            # ac: AssocClass
            # rc: ResultClass
            # rr: ResultRole
            # exp_rslt: list of tuples where each tuple is class and key for
            #           expected instance path returned, or expected exception
            #           object if error response expected.

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
             'child', CIMError(CIM_ERR_INVALID_NAMESPACE)],

            # Invalid types
            [42, None, None, None, None, TypeError()],
            [None, None, None, None, None, TypeError()],
        ]
    )
    def test_openassociatorinstancepaths(self, conn, tst_assoc_mof, ns,
                                         src_inst, ro, ac, rc, rr, exp_rslt):
        # pylint: disable=no-self-use,invalid-name
        """
            Test openenueratepaths where the open is the complete response
            and all parameters are default
        """
        skip_if_moftab_regenerated()
        conn.compile_mof_string(tst_assoc_mof, namespace=ns)

        if isinstance(src_inst, (list, tuple)):
            source_inst_name = CIMInstanceName(
                src_inst[0], keybindings=dict(name=src_inst[1]), namespace=ns)
        else:
            assert isinstance(exp_rslt, Exception)
            source_inst_name = src_inst  # Specifies invalid type directly

        if isinstance(exp_rslt, (list, tuple)):

            # The code to be tested
            result_tuple = conn.OpenAssociatorInstancePaths(source_inst_name,
                                                            AssocClass=ac,
                                                            Role=ro,
                                                            ResultClass=rc,
                                                            ResultRole=rr)

            assert result_tuple.eos is True
            assert result_tuple.context is None

            exp_ns = ns or conn.default_namespace

            # build list of expected paths from exp_rslt
            exp_paths = []
            for exp in exp_rslt:
                exp_paths.append(CIMInstanceName(
                    exp[0],
                    keybindings=dict(name=exp[1]),
                    namespace=exp_ns,
                    host=conn.host))

            rslt_paths = result_tuple.paths

            assert_equal_ciminstancenames(rslt_paths, exp_paths)

        else:
            exp_exc = exp_rslt
            if isinstance(exp_exc, CIMError) and \
                    exp_exc.status_code == CIM_ERR_INVALID_NAMESPACE:
                source_inst_name.namespace = 'BadNamespaceName'
            with pytest.raises(type(exp_exc)) as exec_info:

                # The code to be tested
                conn.OpenAssociatorInstancePaths(source_inst_name,
                                                 AssocClass=ac,
                                                 Role=ro,
                                                 ResultClass=rc,
                                                 ResultRole=rr)

            exc = exec_info.value
            if isinstance(exp_exc, CIMError):
                assert exc.status_code == exp_exc.status_code

    @pytest.mark.parametrize(
        "ns", INITIAL_NAMESPACES + [None])
    @pytest.mark.parametrize(
        "src_inst, ro, ac, rc, rr, exp_rslt",
        [
            # src_inst: If list/tuple: Source instance definitions (classname
            #           and name property). Otherwise, invalid value for
            #           instance_path parameter of the op.
            # ro: Role
            # ac: AssocClass
            # rc: ResultClass
            # rr: ResultRole
            # exp_rslt: list of tuples where each tuple is class and key for
            #           expected instance path returned, or expected exception
            #           object if error response expected.

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
             'child', CIMError(CIM_ERR_INVALID_NAMESPACE)],

            # Invalid types
            [42, None, None, None, None, TypeError()],
            [None, None, None, None, None, TypeError()],
        ]
    )
    def test_openassociatorinstances(self, conn, tst_assoc_mof, ns, src_inst,
                                     ro, ac, rc, rr, exp_rslt):
        # pylint: disable=no-self-use,invalid-name
        """
            Test openenueratepaths where the open is the complete response
            and all parameters are default
        """
        skip_if_moftab_regenerated()
        conn.compile_mof_string(tst_assoc_mof, namespace=ns)

        if isinstance(src_inst, (list, tuple)):
            source_inst_name = CIMInstanceName(
                src_inst[0], keybindings=dict(name=src_inst[1]), namespace=ns)
        else:
            assert isinstance(exp_rslt, Exception)
            source_inst_name = src_inst  # Specifies invalid type directly

        if isinstance(exp_rslt, (list, tuple)):

            # The code to be tested
            result_tuple = conn.OpenAssociatorInstances(source_inst_name,
                                                        AssocClass=ac,
                                                        Role=ro,
                                                        ResultClass=rc,
                                                        ResultRole=rr)

            assert result_tuple.eos is True
            assert result_tuple.context is None

            exp_ns = ns or conn.default_namespace

            # build list of expected paths from exp_rslt
            exp_paths = []
            for exp in exp_rslt:
                exp_paths.append(CIMInstanceName(
                    exp[0],
                    keybindings=dict(name=exp[1]),
                    namespace=exp_ns))

            rslt_paths = [inst.path for inst in result_tuple.instances]

            assert_equal_ciminstancenames(rslt_paths, exp_paths)

            for inst in result_tuple.instances:
                exp_inst = conn.GetInstance(inst.path)
                assert_equal_ciminstances(inst, exp_inst)

            # TODO confirm we are testing for all assoc instances.  We
            # are not since we also need to count the number of instances
            # of corresponding reference classes.

        else:
            exp_exc = exp_rslt
            if isinstance(exp_exc, CIMError) and \
                    exp_exc.status_code == CIM_ERR_INVALID_NAMESPACE:
                source_inst_name.namespace = 'BadNamespaceName'
            with pytest.raises(type(exp_exc)) as exec_info:

                # The code to be tested
                conn.OpenAssociatorInstances(source_inst_name,
                                             AssocClass=ac,
                                             Role=ro,
                                             ResultClass=rc,
                                             ResultRole=rr)

            exc = exec_info.value
            if isinstance(exp_exc, CIMError):
                assert exc.status_code == exp_exc.status_code

    @pytest.mark.parametrize(
        "ns", INITIAL_NAMESPACES + [None])
    @pytest.mark.parametrize(
        "fql, fq, rqrc, exp_rslt",
        [
            # fql:  FilterQueryLanguage
            # fq:   FilterQuery
            # rqrc: ReturnQueryResultClass
            # exp_rslt: Expected exception object or return value as a
            #           tuple with these items (consistent with namedtuple
            #           returned by WBEMConnection.OpenQueryInstances):
            #           - instances: query result as list of CIMInstance objects
            #           - eos: boolean indicating end of sequence
            #           - context: new enumeration context, or None
            #           - query_result_class: CIMClass object, or None

            ['DMTF:FQL', 'SELECT * FROM CIM_Foo', False,
             ([CIMInstance('CIM_Foo')], True, None, None)],

            ['DMTF:FQL', 'SELECT * FROM CIM_Foo', True,
             ([CIMInstance('CIM_Foo')], True, None, CIMClass('CIM_Foo'))],

            ['DMTF:FQL', 'SELECT * FROM CIM_Foo', False,
             ([], True, None, None)],

            # Invalid query language

            ['DMTF:CQL', 'SELECT * FROM CIM_Foo', False,
             CIMError(CIM_ERR_QUERY_LANGUAGE_NOT_SUPPORTED)],

            ['CQL', 'SELECT * FROM CIM_Foo', False,
             CIMError(CIM_ERR_QUERY_LANGUAGE_NOT_SUPPORTED)],

            ['WQL', 'SELECT * FROM CIM_Foo', False,
             CIMError(CIM_ERR_QUERY_LANGUAGE_NOT_SUPPORTED)],

            ['FQL', 'SELECT * FROM CIM_Foo', False,
             CIMError(CIM_ERR_QUERY_LANGUAGE_NOT_SUPPORTED)],

            # Invalid types tests

            [42, 'SELECT * FROM CIM_Foo', False,
             TypeError()],

            ['DMTF:FQL', 42, False,
             TypeError()],

            ['DMTF:FQL', 'SELECT * FROM CIM_Foo', 'invalid',
             TypeError()],
        ]
    )
    def test_openqueryinstances(self, conn, tst_assoc_mof, ns,
                                fql, fq, rqrc, exp_rslt):
        # pylint: disable=no-self-use
        """
        Test OpenQueryInstances()

        The OpenQueryInstances() method of the main provider is
        implemented by calling the ExecQuery() method of the main
        provider, which is not implemented. Since we want to test
        OpenQueryInstances(), we mock the ExecQuery() method.
        """
        skip_if_moftab_regenerated()
        conn.compile_mof_string(tst_assoc_mof, namespace=ns)

        if isinstance(exp_rslt, Exception):
            exp_exc = exp_rslt

            # pylint: disable=protected-access
            conn._mainprovider.ExecQuery = Mock(return_value=[])

            with pytest.raises(type(exp_exc)) as exec_info:

                # The code to be tested
                conn.OpenQueryInstances(FilterQueryLanguage=fql,
                                        FilterQuery=fq,
                                        ReturnQueryResultClass=rqrc)

            exc = exec_info.value
            if isinstance(exp_exc, CIMError):
                assert exc.status_code == exp_exc.status_code

        else:
            # expecting success

            exp_insts, exp_eos, exp_context, exp_class = exp_rslt
            exp_ns = ns or conn.default_namespace

            # Add the expected query result class to the repo
            if exp_class:
                conn.add_cimobjects(exp_class, exp_ns)

            # pylint: disable=protected-access
            conn._mainprovider.ExecQuery = Mock(return_value=exp_insts)

            # The code to be tested
            result_tuple = conn.OpenQueryInstances(FilterQueryLanguage=fql,
                                                   FilterQuery=fq,
                                                   ReturnQueryResultClass=rqrc)

            # pylint: disable=protected-access
            conn._mainprovider.ExecQuery.assert_called_with(exp_ns, fql, fq)

            assert result_tuple.eos == exp_eos
            assert result_tuple.context == exp_context
            assert result_tuple.query_result_class == exp_class
            assert_equal_ciminstancenames(result_tuple.instances, exp_insts)

    @pytest.mark.parametrize(
        "ns", INITIAL_NAMESPACES + [None])
    @pytest.mark.parametrize(
        "test, cln, omoc, pmoc, exp_exc",
        [
            # test: Integer for the test number
            # cln: ClassName input parameter for OpenEnumerate...()
            # omoc: MaxObjectCount input parameter for OpenEnumerate...()
            # pmoc: MaxObjectCount input parameter for Pull...()
            # exp_exc: None, or expected exception object

            # Test closing after open with moc
            [0, 'CIM_Foo', 0, 1, None],

            # Execute close after sequence conplete
            [1, 'CIM_Foo', 100, 100, 'Value Not Used'],

            # Execute close with valid context but after sequence complete
            [2, 'CIM_Foo', 0, 100,
             CIMError(CIM_ERR_INVALID_ENUMERATION_CONTEXT)],
        ]
    )
    def test_closeenumeration(self, conn, tst_classeswqualifiers, tst_instances,
                              ns, test, cln, omoc, pmoc, exp_exc):
        # pylint: disable=no-self-use
        """
        Test variations on closing enumerate the enumeration context with
        the CloseEnumeration operation.  Tests both valid and invalid
        calls.
        """
        add_objects_to_repo(conn, ns, [tst_classeswqualifiers, tst_instances])

        result_tuple = conn.OpenEnumerateInstancePaths(
            cln, namespace=ns, MaxObjectCount=omoc)

        if test == 0:
            assert result_tuple.eos is False
            assert result_tuple.context is not None

            # The code to be tested
            conn.CloseEnumeration(result_tuple.context)

        elif test == 1:
            while not result_tuple.eos:
                result_tuple = conn.PullInstancePaths(
                    result_tuple.context, MaxObjectCount=pmoc)
            assert result_tuple.eos is True
            assert result_tuple.context is None
            with pytest.raises(ValueError) as exec_info:

                # The code to be tested
                conn.CloseEnumeration(result_tuple.context)

        elif test == 2:
            save_result_tuple = pull_path_result_tuple(*result_tuple)

            while not result_tuple.eos:
                result_tuple = conn.PullInstancePaths(
                    result_tuple.context, MaxObjectCount=pmoc)
            assert result_tuple.eos is True
            assert result_tuple.context is None
            with pytest.raises(type(exp_exc)) as exec_info:
                assert save_result_tuple.context is not None

                # The code to be tested
                conn.CloseEnumeration(save_result_tuple.context)

            exc = exec_info.value
            if isinstance(exp_exc, CIMError):
                assert exc.status_code == exp_exc.status_code
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
        q1 = CIMQualifierDeclaration('FooQualDecl1', 'uint32', tosubclass=True,
                                     overridable=True, translatable=False)

        q2 = CIMQualifierDeclaration('FooQualDecl2', 'string',
                                     value='my string', tosubclass=True,
                                     overridable=False, translatable=False)
        return [q1, q2]

    @pytest.mark.parametrize(
        "ns", INITIAL_NAMESPACES + [None])
    @pytest.mark.parametrize(
        "qname, exp_exc",
        [
            # qname: QualifierName input parameter for GetQualifier()
            # exp_exc: None, or expected exception object

            ['FooQualDecl1', None],
            ['fooqualdecl1', None],
            ['badqualname', CIMError(CIM_ERR_NOT_FOUND)],
            ['whatever', CIMError(CIM_ERR_INVALID_NAMESPACE)],
            # Invalid types
            [42, TypeError()],
            [None, TypeError()],
        ]
    )
    def test_getqualifier(self, conn, ns, qname, exp_exc):
        """
        Test adding a qualifierdecl to the repository and doing a
        WBEMConnection get to retrieve it.
        """
        tst_quals = self._build_qualifiers()
        conn.add_cimobjects(tst_quals, namespace=ns)

        exp_qual = None
        for q in tst_quals:
            if isinstance(qname, six.string_types) and \
                    q.name.lower() == qname.lower():
                exp_qual = q

        if not exp_exc:

            # The code to be tested
            rslt_qual = conn.GetQualifier(qname, namespace=ns)

            assert rslt_qual.name.lower() == exp_qual.name.lower()

        else:
            if isinstance(exp_exc, CIMError) and \
                    exp_exc.status_code == CIM_ERR_INVALID_NAMESPACE:
                ns = 'badnamespace'
            with pytest.raises(type(exp_exc)) as exec_info:

                # The code to be tested
                conn.GetQualifier(qname, namespace=ns)

            exc = exec_info.value
            if isinstance(exp_exc, CIMError):
                assert exc.status_code == exp_exc.status_code

    @pytest.mark.parametrize(
        "ns", EXPANDED_NAMESPACES + [None])
    @pytest.mark.parametrize(
        "exp_exc",
        [
            None,
            CIMError(CIM_ERR_INVALID_NAMESPACE)
        ]
    )
    def test_enumeratequalifiers(self, conn, ns, exp_exc):
        """
        Test adding qualifier declarations to the repository and using
        EnumerateQualifiers to retrieve them
        """
        tst_quals = sorted(self._build_qualifiers(), key=lambda x: x.name)

        add_objects_to_repo(conn, ns, tst_quals)

        if not exp_exc:

            # The code to be tested
            rslt_quals = conn.EnumerateQualifiers(namespace=ns)

            rslt_quals.sort(key=lambda x: x.name)
            for i, rslt_qual in enumerate(rslt_quals):
                assert isinstance(rslt_qual, CIMQualifierDeclaration)
                assert rslt_qual == tst_quals[i]
        else:
            if isinstance(exp_exc, CIMError) and \
                    exp_exc.status_code == CIM_ERR_INVALID_NAMESPACE:
                ns = 'badnamespace'
            with pytest.raises(type(exp_exc)) as exec_info:

                # The code to be tested
                conn.EnumerateQualifiers(namespace=ns)

            exc = exec_info.value
            if isinstance(exp_exc, CIMError):
                assert exc.status_code == exp_exc.status_code

    @pytest.mark.parametrize(
        "ns", INITIAL_NAMESPACES + [None])
    @pytest.mark.parametrize(
        "qual, exp_exc",
        [
            # qual: QualifierDeclaration input parameter for SetQualifier()
            # exp_exc: None, or expected exception object

            [CIMQualifierDeclaration('FooQualDecl3', 'string',
                                     value='my string'), None],
            # Invalid type for QualifierDeclaration parameter:
            [CIMClass('FooQualDecl3'), TypeError()],
            ['whatever', TypeError()],
            [42, TypeError()],
            [None, TypeError()],
        ]
    )
    def test_setqualifier(self, conn, ns, qual, exp_exc):
        # pylint: disable=no-self-use
        """
            Test create class. Tests for namespace variable,
            correctly adding, and invalid add where class has superclass
        """

        if not exp_exc:

            # The code to be tested
            conn.SetQualifier(qual, namespace=ns)

            get_qual = conn.GetQualifier(qual.name, namespace=ns)

            assert get_qual == qual

            # Test for uses modify by Setting second qualifier with same name
            # The code to be tested
            conn.SetQualifier(qual, namespace=ns)

        else:
            if isinstance(exp_exc, CIMError) and \
                    exp_exc.status_code == CIM_ERR_INVALID_NAMESPACE:
                ns = 'badnamespace'
            with pytest.raises(type(exp_exc)) as exec_info:

                # The code to be tested
                conn.SetQualifier(qual, namespace=ns)

            exc = exec_info.value
            if isinstance(exp_exc, CIMError):
                assert exc.status_code == exp_exc.status_code

    @pytest.mark.parametrize(
        "ns", INITIAL_NAMESPACES + [None])
    @pytest.mark.parametrize(
        "qname, mof, exp_exc",
        [
            # qname: QualifierName input parameter for DeleteQualifier()
            # mof is a test class is to be added (To test the reject if used)
            #     None if not used
            # exp_exc: None, or expected exception object

            ['FooQualDecl1', False, None],
            ['badqualname', False, CIMError(CIM_ERR_NOT_FOUND)],
            ['whatever', False, CIMError(CIM_ERR_INVALID_NAMESPACE)],
            # Invalid tyoes
            [42, False, TypeError()],
            [None, False, TypeError()],
            # Tests for deleting qdecl when used. Tests with qual decl Blah
            # Class qualifier
            ['Blah', '[Blah] class C_X{};', CIMError(CIM_ERR_FAILED)],
            # property qualifier
            ['Blah', 'class C_X{[blah] string p;};', CIMError(CIM_ERR_FAILED)],
            ['Blah', 'class C_X{[blah] uint32 m();};',
             CIMError(CIM_ERR_FAILED)],
            ['Blah', 'class C_X{[blah] uint32 m();};',
             CIMError(CIM_ERR_FAILED)],
            ['Blah', 'class C_X{[blah] uint32 m([Blah] string parm);};',
             CIMError(CIM_ERR_FAILED)],
            ['FooQualDecl1', 'class C_X{[blah] string p;};', None],
            ['FooQualDecl1', 'class C_X{[blah] uint32 m();};', None],
            ['FooQualDecl1', 'class C_X{[blah] uint32 m();};', None],
            ['FooQualDecl1', 'class C_X{[blah] uint32 m([Blah] string parm);};',
             None],

        ]
    )
    def test_deletequalifier(self, conn, ns, qname, mof, exp_exc):
        """
        Test  fake DeleteQualifier declaration method. Adds qualifier
        declarations to repository and then deletes qualifier defined
        by qname. Tries to delete again and this should fail as not found.
        """
        tst_quals = self._build_qualifiers()
        conn.add_cimobjects(tst_quals, namespace=ns)

        # Add a class that uses the qualifier we want to delete to test
        # for exception. Also adds new qualifier decl just to keep things
        # simple for the tests
        if mof:
            qdecl = "Qualifier Blah: boolean = true, Scope(any), " \
                    "Flavor(EnableOverride);"
            conn.compile_mof_string(qdecl, namespace=ns)
            conn.compile_mof_string(mof, namespace=ns)

        if not exp_exc:

            # The code to be tested
            conn.DeleteQualifier('FooQualDecl2', namespace=ns)

            with pytest.raises(CIMError) as exec_info:

                # The code to be tested
                conn.DeleteQualifier('QualDoesNotExist', namespace=ns)

            exc = exec_info.value
            assert exc.status_code == CIM_ERR_NOT_FOUND
        else:

            if isinstance(exp_exc, CIMError) and \
                    exp_exc.status_code == CIM_ERR_INVALID_NAMESPACE:
                ns = 'badnamespace'

            with pytest.raises(type(exp_exc)) as exec_info:

                # The code to be tested
                conn.DeleteQualifier(qname, namespace=ns)

            exc = exec_info.value
            if isinstance(exp_exc, CIMError):
                assert exc.status_code == exp_exc.status_code


PERSON_MIKE_NME = CIMInstanceName('TST_Person', keybindings=(('name',
                                                              'Mike'),))
PERSONS_MIKE_NME = CIMInstanceName('tst_person', keybindings=(('name',
                                                               'Mike'),))
PERSON_SOFI_NME = CIMInstanceName('TST_Person', keybindings=(('name',
                                                              'Sofi'),))
PERSON_GABI_NME = CIMInstanceName('TST_Person', keybindings=(('name',
                                                              'Gabi'),))
LINEAGE_MIKESOFI_NME = CIMInstanceName('TST_Lineage',
                                       keybindings=(('InstanceID',
                                                     'MikeSofi'),))
LINEAGE_MIKEGABI_NME = CIMInstanceName('TST_Lineage',
                                       keybindings=(('InstanceID',
                                                     'MikeGabi'),))
FAM_COLL_FAM2_NME = CIMInstanceName('TST_FamilyCollection',
                                    keybindings=(('name', 'Family2'),))
MEMBER_FAM2MIKE_NME = CIMInstanceName(
    'TST_MemberOfFamilyCollection',
    keybindings=(('family', FAM_COLL_FAM2_NME),
                 ('member', PERSON_MIKE_NME)))


class TestReferenceOperations(object):
    """
    Tests of References class and instance operations
    """

    @pytest.mark.parametrize(
        "ns", INITIAL_NAMESPACES + [None])
    def test_compile_assoc_mof(self, conn, tst_assoc_mof, ns):
        # pylint: disable=no-self-use
        """
        Test the tst_assoc_mof compilation and verify number of instances
        created.
        """
        skip_if_moftab_regenerated()
        if ns is None:
            ns = conn.default_namespace

        # The code to be tested
        conn.compile_mof_string(tst_assoc_mof, namespace=ns)

        classes = [u'TST_Lineage', u'TST_MemberOfFamilyCollection',
                   u'TST_Person', u'TST_Personsub', u'TST_FamilyCollection']
        assert set(classes) == set(
            conn.EnumerateClassNames(namespace=ns, DeepInheritance=True))

        assert len(conn.EnumerateInstanceNames("TST_Person", namespace=ns)) == \
            TST_PERSONWITH_SUB_INST_COUNT

    # TestReferenceClassNames
    @pytest.mark.parametrize(
        "ns", INITIAL_NAMESPACES + [None])
    @pytest.mark.parametrize(
        "cln", ['TST_Person', 'tst_person', CIMClassName('TST_Person'),
                CIMClassName('tst_person')])
    @pytest.mark.parametrize(
        "rc, ro, exp_rslt",
        [
            # rc: ResultClass
            # ro: Role
            # exp_rslt: list of associator classnames that should be returned if
            #   good result expected, or expected exception object.

            [None, None, ['TST_Lineage', 'TST_MemberOfFamilyCollection']],
            ['TST_Lineage', None, ['TST_Lineage']],
            ['tst_lineage', None, ['TST_Lineage']],
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
            [None, 'family', ['TST_MemberOfFamilyCollection']],
            ['TST_Lineagexxx', None, CIMError(CIM_ERR_INVALID_PARAMETER)],
            [None, None, CIMError(CIM_ERR_INVALID_NAMESPACE)],
            # Invalid types
            [42, None, TypeError()],
            [None, 42, TypeError()],
        ]
    )
    def test_referencenames_classes(self, conn, tst_assoc_mof, ns, cln, rc, ro,
                                    exp_rslt):
        # pylint: disable=no-self-use
        """
        Test getting reference classnames with no options on call and default
        namespace. Tests for both string and CIMClassName input
        """
        skip_if_moftab_regenerated()

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

            # The code to be tested
            rslt_clns = conn.ReferenceNames(cim_cln, ResultClass=rc, Role=ro)

            exp_ns = ns or conn.default_namespace
            assert isinstance(rslt_clns, list)
            assert len(rslt_clns) == len(exp_rslt)
            for cln_ in rslt_clns:
                assert isinstance(cln_, CIMClassName)
                assert cln_.host == conn.host
                assert cln_.namespace == exp_ns
            exp_clns = [CIMClassName(classname=n, namespace=exp_ns,
                                     host=conn.host)
                        for n in exp_rslt]

            assert sorted(exp_clns, key=lambda x: x.classname.lower()) == \
                sorted(rslt_clns, key=lambda x: x.classname.lower())

        else:
            assert isinstance(exp_rslt, Exception)
            exp_exc = exp_rslt

            # Fix the targetclassname for some of the tests
            if isinstance(cim_cln, six.string_types):
                cim_cln = CIMClassName(classname=cln)

            if isinstance(exp_exc, CIMError) and \
                    exp_exc.status_code == CIM_ERR_INVALID_NAMESPACE:
                cim_cln.namespace = 'non_existent_namespace'

            with pytest.raises(type(exp_exc)) as exec_info:

                # The code to be tested
                conn.ReferenceNames(cim_cln, ResultClass=rc, Role=ro)

            exc = exec_info.value
            if isinstance(exp_exc, CIMError):
                assert exc.status_code == exp_exc.status_code

    # TestReferences with classname input
    @pytest.mark.parametrize(
        "ns", INITIAL_NAMESPACES + [None])
    @pytest.mark.parametrize(
        "cln", ['TST_Person', 'tst_person', CIMClassName('TST_Person'),
                CIMClassName('tst_person')])
    @pytest.mark.parametrize(
        "rc, ro, iq, ico, pl, exp_rslt",
        [
            # rc: ResultClass Parameter
            # ro: Role Parameter
            # iq: IncludeQualifier Parameter  (True, False, None)
            # ico: IncludeClassOrigin Parameter (True, False, None)
            # pl: Property list parameter(TNone, "", string, list of strings)
            # exp_rslt: list of associator classnames that should be returned if
            #   good result expected, or expected exception object.

            [None, None, None, None, None, ['TST_Lineage',
                                            'TST_MemberOfFamilyCollection']],

            [None, None, False, False, None, ['TST_Lineage',
                                              'TST_MemberOfFamilyCollection']],

            [None, None, None, None, "", ['TST_Lineage',
                                          'TST_MemberOfFamilyCollection']],


            ['TST_Lineage', None, None, None, None, ['TST_Lineage']],

            ['tst_lineage', None, None, None, None, ['TST_Lineage']],

            ['TST_Lineage', 'parent', None, None, None, ['TST_Lineage']],

            ['TST_Lineage', 'child', None, None, None, ['TST_Lineage']],

            ['TST_Lineage', 'CHILD', None, None, None, ['TST_Lineage']],

            [None, 'parent', None, None, None, ['TST_Lineage']],

            [None, 'child', None, None, None, ['TST_Lineage']],

            [None, 'blah', None, None, None, []],

            ['TST_MemberOfFamilyCollection', None, None, None, None,
             ['TST_MemberOfFamilyCollection']],

            ['TST_MemberOfFamilyCollection', 'member', None, None, None,
             ['TST_MemberOfFamilyCollection']],

            ['TST_MemberOfFamilyCollection', 'family', None, None, None,
             ['TST_MemberOfFamilyCollection']],

            [None, 'member', None, None, None,
             ['TST_MemberOfFamilyCollection']],

            [None, 'family', None, None, None,
             ['TST_MemberOfFamilyCollection']],

            [None, 'family', None, None, None,
             ['TST_MemberOfFamilyCollection']],

            ['TST_Lineagexxx', None, None, None, None,
             CIMError(CIM_ERR_INVALID_PARAMETER)],

            [None, None, None, None, None, CIMError(CIM_ERR_INVALID_NAMESPACE)],

            # Invalid types
            [42, None, None, None, None, TypeError()],
            [None, 42, None, None, None, TypeError()],
        ]
    )
    def test_references_classes(self, conn, tst_assoc_mof, ns, cln, rc, ro,
                                iq, ico, pl, exp_rslt):
        # pylint: disable=no-self-use
        """
        Test getting references classnames with no options on call and default
        namespace. Tests for both string and CIMClassName input
        """
        skip_if_moftab_regenerated()

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

            # The code to be tested
            # Returns tuple of classpath, class)
            rslt_classes_tup = conn.References(cim_cln, ResultClass=rc, Role=ro,
                                               IncludeQualifiers=iq,
                                               IncludeClassOrigin=ico,
                                               PropertyList=pl)

            exp_ns = ns or conn.default_namespace
            assert isinstance(rslt_classes_tup, list)
            assert len(rslt_classes_tup) == len(exp_rslt)
            for cls_tup in rslt_classes_tup:
                assert isinstance(cls_tup, tuple)
                assert isinstance(cls_tup[0], CIMClassName)
                assert isinstance(cls_tup[1], CIMClass)
                assert cls_tup[0].host == conn.host
                assert cls_tup[0].namespace == exp_ns
            exp_clns = [CIMClassName(classname=n, namespace=exp_ns,
                                     host=conn.host)
                        for n in exp_rslt]

            exp_classes = [conn.GetClass(cls, namespace=exp_ns,
                                         IncludeQualifiers=iq,
                                         IncludeClassOrigin=ico,
                                         PropertyList=pl)
                           for cls in exp_rslt]

            rslt_classnames = [x[0] for x in rslt_classes_tup]

            assert sorted(exp_clns, key=lambda x: x.classname.lower()) == \
                sorted(rslt_classnames, key=lambda x: x.classname.lower())

            def _bld_cls(cls, name):
                if cls.path is None:
                    cls.path = name
                return cls
            rslt_classes = [_bld_cls(cls, name)
                            for name, cls in rslt_classes_tup]

            for klass in rslt_classes:
                if iq is False:
                    assert not klass.qualifiers
                for prop in klass.properties.values():
                    if ico is False or ico is None:
                        assert not prop.class_origin
                    else:
                        assert prop.class_origin
                if pl == "":
                    assert not klass.properties
                elif pl is None:
                    assert klass.properties

            assert sorted(exp_classes, key=lambda x: x.classname.lower()) == \
                sorted(rslt_classes, key=lambda x: x.classname.lower())

        # Else process exception
        else:
            assert isinstance(exp_rslt, Exception)
            exp_exc = exp_rslt

            # Fix the targetclassname for some of the tests
            if isinstance(cim_cln, six.string_types):
                cim_cln = CIMClassName(classname=cln)

            if isinstance(exp_exc, CIMError) and \
                    exp_exc.status_code == CIM_ERR_INVALID_NAMESPACE:
                cim_cln.namespace = 'non_existent_namespace'

            with pytest.raises(type(exp_exc)) as exec_info:
                # The code to be tested
                conn.References(cim_cln, ResultClass=rc, Role=ro,
                                IncludeQualifiers=iq,
                                IncludeClassOrigin=ico,
                                PropertyList=pl)

            exc = exec_info.value
            if isinstance(exp_exc, CIMError):
                assert exc.status_code == exp_exc.status_code

    def test_reference_instnames_min(self, conn, tst_assoc_mof):
        # pylint: disable=no-self-use
        """
        Test getting reference instnames with no options
        """
        skip_if_moftab_regenerated()

        conn.compile_mof_string(tst_assoc_mof)

        inst_name = CIMInstanceName('TST_Person',
                                    keybindings={'name': 'Mike'})

        # The code to be tested
        rslt_instnames = conn.ReferenceNames(inst_name)

        assert isinstance(rslt_instnames, list)
        assert len(rslt_instnames) == 3
        assert isinstance(rslt_instnames[0], CIMInstanceName)
        exp_instnames = [
            CIMInstanceName(classname='TST_Lineage',
                            keybindings=NocaseDict({'InstanceID': 'MikeSofi'}),
                            namespace='root/cimv2', host=conn.host),
            CIMInstanceName(classname='TST_Lineage',
                            keybindings=NocaseDict({'InstanceID': 'MikeGabi'}),
                            namespace='root/cimv2', host='FakedUrl:5988'),
            CIMInstanceName(
                classname='TST_MemberOfFamilyCollection',
                keybindings=NocaseDict({
                    'family': CIMInstanceName(
                        classname='TST_FamilyCollection',
                        keybindings=NocaseDict({'name': 'Family2'}),
                        namespace='root/cimv2', host=None),
                    'member': CIMInstanceName(
                        classname='TST_Person',
                        keybindings=NocaseDict({'name': 'Mike'}),
                        namespace='root/cimv2', host=None)}),
                namespace='root/cimv2', host=conn.host)]
        assert_equal_ciminstancenames(rslt_instnames, exp_instnames)

    @pytest.mark.parametrize(
        "ns", INITIAL_NAMESPACES + [None])
    @pytest.mark.parametrize(
        # Don't really need this since results are tied to class.
        # target instance name
        "targ_iname", [PERSON_MIKE_NME, PERSONS_MIKE_NME, ]
    )
    @pytest.mark.parametrize(
        "rc, ro, exp_rslt",
        [
            # rc: ResultClass
            # ro: Role
            # exp_rslt: list of associator class/key tuples that should be
            #    returned if good result expected, or expected exception object.

            [None, None, (LINEAGE_MIKESOFI_NME,
                          LINEAGE_MIKEGABI_NME, MEMBER_FAM2MIKE_NME)],
            ['TST_Lineage', None, (LINEAGE_MIKESOFI_NME,
                                   LINEAGE_MIKEGABI_NME)],
            ['tst_lineage', None, (LINEAGE_MIKESOFI_NME,
                                   LINEAGE_MIKEGABI_NME)],
            ['TST_Lineage', 'parent', (LINEAGE_MIKESOFI_NME,
                                       LINEAGE_MIKEGABI_NME)],
            ['TST_Lineage', 'child', ()],
            ['TST_Lineage', 'CHILD', ()],
            [None, 'parent', (LINEAGE_MIKESOFI_NME,
                              LINEAGE_MIKEGABI_NME)],
            [None, 'child', ()],
            ['TST_MemberOfFamilyCollection', None, (MEMBER_FAM2MIKE_NME,)],
            ['TST_MemberOfFamilyCollection', 'member', (MEMBER_FAM2MIKE_NME,)],
            ['TST_MemberOfFamilyCollection', 'family', ()],
            [None, 'member', (MEMBER_FAM2MIKE_NME,)],
            [None, 'family', ()],
            # Verify role name not in class return nothing
            ['TST_Lineage', 'blah', []],
            # Verify ResultClass not in environment returns nothing
            ['TST_LineageXXX', None, CIMError(CIM_ERR_INVALID_PARAMETER)],
            # Specific test that generates error
            ['TST_Lineage', None, CIMError(CIM_ERR_INVALID_NAMESPACE, "blah")]
        ]
    )
    def test_reference_instnames(self, conn, tst_assoc_mof, ns, targ_iname, rc,
                                 ro, exp_rslt):
        # pylint: disable=no-self-use
        """
        Test getting reference classnames
        """
        skip_if_moftab_regenerated()

        conn.compile_mof_string(tst_assoc_mof, namespace=ns)
        targ_iname.namespace = ns

        # Fixup exp_rslt by completing at least namespace
        if isinstance(exp_rslt, (tuple, list)):
            exp_inames = []

            # set namespace in target instance name if a namespace is specified
            if ns is None:
                ns = conn.default_namespace
                local_targ_iname = targ_iname
            else:
                local_targ_iname = targ_iname.copy()
                local_targ_iname.namespace = ns

            for iname in exp_rslt:
                local_iname = iname.copy()
                local_iname.namespace = ns
                for kb in local_iname.keybindings:
                    if isinstance(local_iname.keybindings[kb], CIMInstanceName):
                        local_iname.keybindings[kb].namespace = ns

                exp_inames.append(local_iname.to_wbem_uri('canonical'))

            # The code to be tested
            rslt_instnames = conn.ReferenceNames(targ_iname, ResultClass=rc,
                                                 Role=ro)

            assert isinstance(rslt_instnames, list)

            assert len(rslt_instnames) == len(exp_rslt)

            # test if result instance names are as expected.
            # We remove host because the return is scheme + url and when we
            # expand exp_inames it expands only to url (i.e. the htp:// missing)
            for path in rslt_instnames:
                assert isinstance(path, CIMInstanceName)
                path.host = None
                assert path.to_wbem_uri('canonical') in exp_inames

        else:
            assert isinstance(exp_rslt, Exception)
            exp_exc = exp_rslt

            if isinstance(exp_exc, CIMError) and \
                    exp_exc.status_code == CIM_ERR_INVALID_NAMESPACE:
                targ_iname = targ_iname.copy()   # copy to not mod original
                targ_iname.namespace = 'non_existent_namespace'

            with pytest.raises(type(exp_exc)) as exec_info:

                # The code to be tested
                conn.ReferenceNames(targ_iname, ResultClass=rc, Role=ro)

            exc = exec_info.value
            if isinstance(exp_exc, CIMError):
                assert exc.status_code == exp_exc.status_code

    @pytest.mark.parametrize(
        "ns", INITIAL_NAMESPACES + [None])
    def test_reference_instances_min(self, conn, tst_assoc_mof, ns):
        # pylint: disable=no-self-use
        """
        Test getting reference instances from default namespace with
        detault parameters. This is a minimal test of References with instances.
        """
        skip_if_moftab_regenerated()

        conn.compile_mof_string(tst_assoc_mof)

        # Build the expected result instance list
        # the paths for association instances must include the correct
        # namespace for each key that is a CIMInstanceName
        ns = ns or conn.default_namespace
        fam2mike = fix_instname_namespace_keys(MEMBER_FAM2MIKE_NME, ns)
        exp_insts = [conn.GetInstance(path) for path in
                     (LINEAGE_MIKESOFI_NME, LINEAGE_MIKEGABI_NME, fam2mike)]
        # set the server name in the expected response
        for inst in exp_insts:
            if inst.path.host is None:
                inst.path.host = conn.host
        assert len(exp_insts) == 3

        inst_path = CIMInstanceName('TST_Person', keybindings=dict(name='Mike'))

        # The code to be tested
        rslt_insts = conn.References(inst_path)

        assert isinstance(rslt_insts, list)
        assert_equal_ciminstances(exp_insts, rslt_insts)

    # Test reference instance options
    @pytest.mark.parametrize(
        "ns", INITIAL_NAMESPACES + [None])
    @pytest.mark.parametrize(
        "desc, rc, role, iq, ico, pl, exp_rslt",
        [
            # description
            # rc: ResultClass parameter
            # role: Role parameter
            # iq: IncludeQualifiers Flag
            # ico: IncludeClassOrigin flag
            # pl: PropertyList
            # exp_rslt: tuple of classname and tuple of keys
            # in expected return CIMInstanceNames. Used to build expected
            # return keys.

            ["1. References with all default parameters",
             None, None, None, None, None,
             (('TST_Lineage', ('InstanceID', 'MikeGabi')),
              ('TST_Lineage', ('InstanceID', 'MikeSofi')),
              ('TST_MemberOfFamilyCollection', (
                  ('TST_FamilyCollection', 'family', 'name', "Family2"),
                  ('TST_Person', 'member', 'name', 'Mike'))))],

            ["2. Test with result class defined",
             'TST_Lineage', None, None, None, None,
             (('TST_Lineage', ('InstanceID', 'MikeGabi')),
              ('TST_Lineage', ('InstanceID', 'MikeSofi')))],

            ["3. Test with result class different case",
             'tst_lineage', None, None, None, None,
             (('TST_Lineage', ('InstanceID', 'MikeGabi')),
              ('TST_Lineage', ('InstanceID', 'MikeSofi')))],

            ["4. Test with role defined",
             None, 'parent', None, None, None,
             (('TST_Lineage', ('InstanceID', 'MikeGabi')),
              ('TST_Lineage', ('InstanceID', 'MikeSofi')))],

            ["5. Test with role defined with different case",
             None, 'PARENT', None, None, None,
             (('TST_Lineage', ('InstanceID', 'MikeGabi')),
              ('TST_Lineage', ('InstanceID', 'MikeSofi')))],

            ["6. Test with result class and role defined",
             'TST_Lineage', 'parent', None, None, None,
             (('TST_Lineage', ('InstanceID', 'MikeGabi')),
              ('TST_Lineage', ('InstanceID', 'MikeSofi')))],

            ["6. Test with unknown role defined",
             None, 'friend', None, None, None, []],

        ]
    )
    def test_reference_instances_opts(self, conn, tst_assoc_mof, ns,
                                      desc, rc, role, iq, ico, pl, exp_rslt):
        # pylint: disable=no-self-use
        """
        Test getting reference instance names with rc and role options.
        Tests agains the classes defined in tst_assoc_mof.
        """
        skip_if_moftab_regenerated()

        conn.compile_mof_string(tst_assoc_mof, namespace=ns)

        inst_name = CIMInstanceName('TST_Person',
                                    keybindings=dict(name='Mike'),
                                    namespace=ns)

        # The code to be tested
        insts = conn.References(inst_name, ResultClass=rc, Role=role,
                                IncludeQualifiers=iq,
                                IncludeClassOrigin=ico,
                                PropertyList=pl)

        paths = [i.path for i in insts]

        assert isinstance(insts, list), "desc {}".format(desc)
        assert len(insts) == len(exp_rslt), "desc {}".format(desc)
        for inst in insts:
            assert isinstance(inst, CIMInstance), "desc {}".format(desc)

        exp_ns = ns or conn.default_namespace

        # create the expected paths from exp_rslt fixture.

        exp_paths = []
        for exp_path in exp_rslt:
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

        assert_equal_ciminstancenames(exp_paths, paths)

    # Test reference instance with source instance that is not an instance
    @pytest.mark.parametrize(
        "ns", INITIAL_NAMESPACES + [None])
    @pytest.mark.parametrize(
        "targ_obj",
        [
            'XXX_Blan',
            CIMInstanceName('XXX_Blah', keybindings={'InstanceID': 3}),
        ]
    )
    def test_reference_source_err(self, conn, tst_assoc_mof, ns, targ_obj):
        # pylint: disable=no-self-use
        """
        Separate test for error when source instance invalid type
        """
        skip_if_moftab_regenerated()

        conn.compile_mof_string(tst_assoc_mof, namespace=ns)
        with pytest.raises(CIMError) as exec_info:

            # The code to be tested
            conn.ReferenceNames(targ_obj)

        exc = exec_info.value
        assert exc.status_code == CIM_ERR_INVALID_PARAMETER


class TestAssociatorOperations(object):
    """
    Tests of Associator class and instance operations
    """
    # Test associatornames operation with classnames
    @pytest.mark.parametrize(
        "ns", EXPANDED_NAMESPACES + [None])
    @pytest.mark.parametrize(
        "target_cln", ['TST_Person', 'tst_person'])
    @pytest.mark.parametrize(
        "role, ac, rr, rc, exp_rslt",
        [
            # role: role attribute
            # ac: associated class attribute
            # rr: resultrole attribute
            # rc: resultclass attribute
            # exp_rslt: Either list of names of expected classes returned,
            #             or expected exception object

            [None, None, None, None, ['TST_Person']],
            [None, 'TST_Lineage', None, None, ['TST_Person']],
            ['Parent', 'TST_Lineage', None, None, ['TST_Person']],
            ['parent', 'TST_Lineage', None, None, ['TST_Person']],
            ['parent', 'tst_lineage', None, None, ['TST_Person']],
            ['parent', 'TST_Lineage', None, None, ['tst_person']],
            ['Parent', 'TST_Lineage', 'child', 'TST_Person', ['TST_Person']],
            ['parent', 'TST_Lineage', 'Child', 'TST_Person', ['TST_Person']],
            ['PARENT', 'TST_Lineage', 'CHILD', 'TST_Person', ['TST_Person']],
            [None, None, 'child', 'TST_Person', ['TST_Person']],
            ['Parent', 'TST_Lineagexxx', 'child', 'TST_Person',
             CIMError(CIM_ERR_INVALID_PARAMETER)],
            ['Parent', 'TST_Lineage', 'child', 'TST_Personxxx',
             CIMError(CIM_ERR_INVALID_PARAMETER)],
            ['Parent', 'TST_Lineage', 'child', 'TST_Person',
             CIMError(CIM_ERR_INVALID_NAMESPACE)],
            # Invalid types
            [42, None, None, None, TypeError()],
            [None, 42, None, None, TypeError()],
            [None, None, 42, None, TypeError()],
            [None, None, None, 42, TypeError()],
        ]
    )
    def test_associator_classnames(self, conn, tst_assoc_mof, ns, target_cln,
                                   role, rr, ac, rc, exp_rslt):
        # pylint: disable=no-self-use
        """
        Test getting reference classnames with no options on call and default
        namespace. Tests for both string and CIMClassName input
        """
        skip_if_moftab_regenerated()

        add_objects_to_repo(conn, ns, [tst_assoc_mof])

        if isinstance(target_cln, six.string_types):
            target_cln = CIMClassName(target_cln, namespace=ns)
        else:
            assert isinstance(exp_rslt, Exception)
            # target_cln is an invalid type

        if isinstance(exp_rslt, (list, tuple)):

            # The code to be tested
            rslt_clns = conn.AssociatorNames(target_cln, AssocClass=ac,
                                             Role=role,
                                             ResultRole=rr, ResultClass=rc)

            exp_ns = ns if ns else conn.default_namespace
            assert isinstance(rslt_clns, list)
            assert len(rslt_clns) == len(exp_rslt)
            for cln in rslt_clns:
                assert isinstance(cln, CIMClassName)
                assert cln.host == conn.host
                assert cln.namespace == exp_ns

            exp_clns = [CIMClassName(classname=n, namespace=exp_ns,
                                     host=conn.host)
                        for n in exp_rslt]

            assert set(cln.classname.lower() for cln in exp_clns) == \
                set(cln.classname.lower() for cln in rslt_clns)

        else:
            assert isinstance(exp_rslt, Exception)
            exp_exc = exp_rslt

            # Set up test for invalid namespace exception
            if isinstance(exp_exc, CIMError) and \
                    exp_exc.status_code == CIM_ERR_INVALID_NAMESPACE:
                if isinstance(target_cln, six.string_types):
                    target_cln = CIMClassName(target_cln,
                                              namespace='badnamespacename')
                else:
                    target_cln.namespace = 'badnamespacename'

            with pytest.raises(type(exp_exc)) as exec_info:

                # The code to be tested
                conn.AssociatorNames(target_cln, AssocClass=ac, Role=role,
                                     ResultRole=rr, ResultClass=rc)

            exc = exec_info.value
            if isinstance(exp_exc, CIMError):
                assert exc.status_code == exp_exc.status_code

    # Test associatornames with instances operation
    @pytest.mark.parametrize(
        "ns", INITIAL_NAMESPACES + [None])
    @pytest.mark.parametrize(
        "targ_iname", [
            PERSON_MIKE_NME,
            PERSONS_MIKE_NME,
        ]
    )
    @pytest.mark.parametrize(
        "role, ac, rr, rc, exp_rslt",
        [
            # role: associator role parameter
            # ac: associator operation AssocClass parameter
            # rr: associator operation ResultRole parameter
            # rc: associator operation ResultClass parameter
            # exp_rslt: Expected result: List of instances in response,
            #           or expected exception object.

            # Test for assigned role and assoc class
            ['parent', 'TST_Lineage', None, None, (PERSON_SOFI_NME,
                                                   PERSON_GABI_NME,)],
            # Test for assigned role, asoc class, result role, resultclass
            ['parent', 'TST_Lineage', 'child', 'TST_Person',
             (PERSON_SOFI_NME, PERSON_GABI_NME,)],
            # test for case independence for role, assocclass, result role,
            # and resultclass
            ['PARENT', 'TST_Lineage', 'child', 'TST_Person',
             (PERSON_SOFI_NME, PERSON_GABI_NME,)],
            ['parent', 'tst_lineage', 'child', 'TST_Person',
             (PERSON_SOFI_NME, PERSON_GABI_NME,)],
            ['parent', 'TST_Lineage', 'CHILD', 'TST_Person',
             (PERSON_SOFI_NME, PERSON_GABI_NME,)],
            ['parent', 'TST_Lineage', 'child', 'tst_person',
             (PERSON_SOFI_NME, PERSON_GABI_NME,)],
            ['PARENT', 'tst_lineage', 'CHILD', 'tst_person',
             (PERSON_SOFI_NME, PERSON_GABI_NME,)],
            ['PARENT', 'tst_lineagexxx', 'CHILD', 'tst_person',
             CIMError(CIM_ERR_INVALID_PARAMETER, "blah")],
            ['PARENT', 'tst_lineage', 'CHILD', 'tst_personxxx',
             CIMError(CIM_ERR_INVALID_PARAMETER, "blah")],
            # Execute invalid namespace test
            ['Parent', 'TST_Lineage', 'child', 'TST_Person',
             CIMError(CIM_ERR_INVALID_NAMESPACE, "blah")],
        ]
    )
    def test_associator_instnames(self, conn, tst_assoc_mof, ns, targ_iname,
                                  role, rr, ac, rc, exp_rslt):
        # pylint: disable=no-self-use
        """
        Test getting associators with parameters for the response filters
        including role, etc.
        """
        skip_if_moftab_regenerated()

        conn.compile_mof_string(tst_assoc_mof, namespace=ns)

        exp_ns = ns or conn.default_namespace
        targ_iname.namespace = ns

        if isinstance(exp_rslt, (tuple, list)):
            exp_inames = []
            for iname in exp_rslt:
                local_iname = iname.copy()
                local_iname.namespace = exp_ns
                for kb in local_iname.keybindings:
                    if isinstance(local_iname.keybindings[kb], CIMInstanceName):
                        local_iname.keybindings[kb].namespace = exp_ns
                exp_inames.append(local_iname.to_wbem_uri('canonical'))

            # The code to be tested
            rpaths = conn.AssociatorNames(targ_iname, AssocClass=ac, Role=role,
                                          ResultRole=rr, ResultClass=rc)

            assert isinstance(rpaths, list)
            assert len(rpaths) == len(exp_rslt)
            for path in rpaths:
                assert isinstance(path, CIMInstanceName)
                path.host = None
                assert path.to_wbem_uri('canonical') in exp_inames

        else:
            assert isinstance(exp_rslt, Exception)
            exp_exc = exp_rslt

            if isinstance(exp_exc, CIMError) and \
                    exp_exc.status_code == CIM_ERR_INVALID_NAMESPACE:
                targ_iname.namespace = 'BadNameSpaceName'

            with pytest.raises(type(exp_exc)) as exec_info:

                # The code to be tested
                conn.AssociatorNames(targ_iname, AssocClass=ac, Role=role,
                                     ResultRole=rr, ResultClass=rc)

            exc = exec_info.value
            if isinstance(exp_exc, CIMError):
                assert exc.status_code == exp_exc.status_code

    # Test Associators with operation with instances
    TESTCASES_ASSOCIATOR_INSTANCES = [

        # Testcases for test_associator_instances(), where each list item is
        # a tuple with these items:
        #
        # desc: Testcase description
        # inst_name: ObjectName input parameter for the op., or 'buildit' flag
        # role: Role input parameter for the operation
        # ac: AssocClass input parameter for the operation
        # rr: ResultRole input parameter for the operation
        # rc: ResultClass input parameter for the operation
        # iq: IncludeQualifiers input parameter for the operation
        # ico: IncludeClassOrigin input parameter for the operation
        # pl: PropertyList input parameter for the operation
        # exp_rslt: Expected list of instances in response, as tuple
        #           (classname, name key), or expected exception object.

        (
            "1. Test Role, AssocClass parameters",
            'buildit',
            'parent', 'TST_Lineage', None, None,
            None, None, None,
            (
                ('TST_person', 'Sofi'),
                ('TST_person', 'Gabi'),
            )
        ),

        (
            "2. Test Role, AssocClass parameters with pl",
            'buildit',
            'parent', 'TST_Lineage', None, None,
            None, None, ['name'],
            (
                ('TST_person', 'Sofi'),
                ('TST_person', 'Gabi'),
            )
        ),

        (
            "3. Test Role, AssocClass parameters with empty pl",
            'buildit',
            'parent', 'TST_Lineage', None, None,
            None, None, "",
            (
                ('TST_person', 'Sofi'),
                ('TST_person', 'Gabi'),
            )
        ),
        (
            "4. Role, AssocClass, ResultRole, ResultClass parameters",
            'buildit',
            'parent', 'TST_Lineage', 'child', 'TST_Person',
            None, None, None,
            (
                ('TST_person', 'Sofi'),
                ('TST_person', 'Gabi'),
            )
        ),
        (
            "5. ObjectName is instance path with non-existing namespace",
            CIMInstanceName('TST_Lineage', namespace='BadNameSpaceName',
                            keybindings=dict(name='Mike')),
            None, None, None, None,
            None, None, None,
            CIMError(CIM_ERR_INVALID_NAMESPACE)
        ),

        (
            "6. ObjectName has invalid type int",
            42, None, None, None, None, None, None, None, TypeError()
        ),
        (
            "7. ObjectName has invalid value None",
            None, None, None, None, None, None, None, None, TypeError()
        ),
        (
            "8. Role has invalid type int",
            'buildit', 42, None, None, None, None, None, None, TypeError()
        ),
        (
            "9. AssocClass has invalid type int",
            'buildit', None, 42, None, None, None, None, None, TypeError()
        ),
        (
            "10. ResultRole has invalid type int",
            'buildit', None, None, 42, None, None, None, None, TypeError()
        ),
        (
            "11. ResultClass has invalid type int",
            'buildit', None, None, None, 42, None, None, None, TypeError()
        ),
        (
            "12. IncludeQualifiers has invalid type int",
            'buildit', None, None, None, None, 42, None, None, TypeError()
        ),
        (
            "13. IncludeClassOrigin has invalid type int",
            'buildit', None, None, None, None, None, 42, None, TypeError()
        ),
        (
            "14. PropertyList has invalid type int",
            'buildit', None, None, None, None, None, None, 42, TypeError()
        ),
    ]

    @pytest.mark.parametrize(
        "tst_ns", INITIAL_NAMESPACES + [None])
    @pytest.mark.parametrize(
        "cln, name_key",
        [
            # cln: Class name used in the source instance path
            # name_key: 'name' key value used in the source instance path
            # Used whan inst_name is 'buildit'

            ['TST_Person', 'Mike'],
            ['tst_person', 'Mike'],
        ]
    )
    @pytest.mark.parametrize(
        "desc, inst_name, role, ac, rr, rc, iq, ico, pl, exp_rslt",
        TESTCASES_ASSOCIATOR_INSTANCES
    )
    def test_associator_instances(
            self, conn, tst_assoc_mof, tst_ns, cln, name_key,
            desc, inst_name, role, rr, ac, rc, iq, ico, pl, exp_rslt):
        # pylint: disable=no-self-use,unused-argument
        """
        Test Associators() operation at instance level.
        """
        skip_if_moftab_regenerated()

        conn.compile_mof_string(tst_assoc_mof, namespace=tst_ns)

        exp_ns = tst_ns or conn.default_namespace
        if isinstance(inst_name, str) and inst_name == 'buildit':
            inst_name = CIMInstanceName(cln, namespace=exp_ns,
                                        keybindings=dict(name=name_key))

        if isinstance(exp_rslt, Exception):
            exp_exc = exp_rslt
            with pytest.raises(type(exp_exc)) as exec_info:

                # The code to be tested
                conn.Associators(
                    inst_name, AssocClass=ac, Role=role, ResultRole=rr,
                    ResultClass=rc, IncludeQualifiers=iq,
                    IncludeClassOrigin=ico, PropertyList=pl)

            exc = exec_info.value
            if isinstance(exp_exc, CIMError):
                assert exc.status_code == exp_exc.status_code

        else:
            assert isinstance(exp_rslt, (tuple, list))

            # The code to be tested
            rslt_insts = conn.Associators(
                inst_name, AssocClass=ac, Role=role, ResultRole=rr,
                ResultClass=rc, IncludeQualifiers=iq,
                IncludeClassOrigin=ico, PropertyList=pl)

            assert isinstance(rslt_insts, list)
            assert len(rslt_insts) == len(exp_rslt)

            for inst in rslt_insts:
                assert not inst.qualifiers
                for inst in inst.properties.values():
                    assert not inst.qualifiers
                    if ico:
                        assert inst.class_origin
                    else:
                        assert inst.class_origin is None

            if pl == "":
                for inst in rslt_insts:
                    assert not inst.properties
            elif pl:
                for propname in pl:
                    for inst in rslt_insts:
                        assert propname in inst.properties, \
                            "desc: {}".format(desc)
                assert sorted(inst.properties) == sorted(pl)
            elif pl is None:
                for inst in rslt_insts:
                    repo_inst = conn.GetInstance(inst.path)
                    assert sorted(inst.properties) == \
                        sorted(repo_inst.properties)
            else:
                assert False, "Invalid pl parameter {}".format(pl)

            # Build the expected result instances list
            exp_insts = []
            for cln_, name_key_ in exp_rslt:
                props = {} if pl == "" else {'name': name_key_}
                exp_inst = CIMInstance(
                    cln_, properties=props,
                    path=CIMInstanceName(
                        cln_, keybindings={'name': name_key_},
                        namespace=exp_ns))
                exp_insts.append(exp_inst)

            # TODO: this is a limited test today.  Need to expand so
            # test pl covers all three cases for property list. Then we
            # can drop above pl test.
            tst_pl = None if pl == "" else ['name']
            assert_equal_ciminstances(exp_insts, rslt_insts, pl=tst_pl)

    @pytest.mark.parametrize(
        "ns", INITIAL_NAMESPACES + [None])
    @pytest.mark.parametrize(
        "cln", ['TST_Person'])
    @pytest.mark.parametrize(
        ", desc, role, ac, rr, rc, iq, ico, pl, exp_rslt",
        [
            # Description: String describing test
            # role: associator role parameter
            # ac: associator operation AssocClass parameter
            # rr: associator operation ResultRole parameter
            # rc: associator operation ResultClass parameter
            # iq: include qualifiers
            # ico: include class origin
            # pl: Property list to include in request
            # exp_rslt: Either list of names of expected classes returned,
            #           or expected exception object

            ["1.Test all parameters None",
             None, None, None, None,
             None, None, None,
             ['TST_Person']],

            ["2. Test Role valid",
             None, 'TST_Lineage', None, None,
             None, None, None,
             ['TST_Person']],

            ["3. Test Role and ac valid",
             'Parent', 'TST_Lineage', None, None,
             None, None, None,
             ['TST_Person']],

            ["4. Test Role and ac valid, case inequality",
             'parent', 'TST_Lineage', None, None,
             None, None, None,
             ['TST_Person']],

            ["5. Test Role, ac, rr, rc",
             'Parent', 'TST_Lineage', 'child', 'TST_Person',
             None, None, None,
             ['TST_Person']],

            ["6.Test role, ac, rr, rc case inequalify",
             'parent', 'TST_Lineage', 'Child', 'TST_Person',
             None, None, None,
             ['TST_Person']],

            ["7.Test role, ac, rr, rc, case inqaulaity",
             'PARENT', 'TST_Lineage', 'CHILD', 'TST_Person',
             None, None, None,
             ['TST_Person']],

            ["8. Test rr, rc",
             None, None, 'child', 'TST_Person',
             None, None, None,
             ['TST_Person']],

            ["9.Test role does not exist",
             'PARENTx', 'TST_Lineage', 'CHILD', 'TST_Person',
             None, None, None,
             []],

            ["10.Test result role does not exist",
             'PARENT', 'TST_Lineage', 'CHILDx', 'TST_Person',
             None, None, None,
             []],

            ["11.Test result class does not part of association",
             'PARENT', 'TST_Lineage', 'CHILD', 'TST_Lineage',
             None, None, None,
             []],

            ["12.Test assoc class does not part of association",
             'PARENT', 'TST_Person', 'CHILD', 'TST_Person',
             None, None, None,
             []],

            ["13. Test all 4 roles",
             'Parent', 'TST_Lineage', 'child', 'TST_Person',
             None, None, None,
             CIMError(CIM_ERR_INVALID_NAMESPACE)],

            # Invalid type (integer) for role, ac, rr, rc
            ["14. Error, invalid role",
             42, None, None, None, None, None, None, TypeError()],
            ["15. Error, Invalid rr",
             None, 42, None, None, None, None, None, TypeError()],
            ["16. Error invalid assoc class",
             None, None, 42, None, None, None, None, TypeError()],
            ["17. Error, invalid rc",
             None, None, None, 42, None, None, None, TypeError()],

            ["18.Test rc is subclass. There are no instance of this subclass",
             'PARENT', 'TST_Lineage', 'CHILD', 'TST_Personsub',
             None, None, None,
             []],
        ]
    )
    def test_associator_classes(self, conn, tst_assoc_mof, ns, cln,
                                desc, role, rr, ac, rc,
                                iq, ico, pl, exp_rslt):
        # pylint: disable=no-self-use
        """
        Test getting reference classnames with no options on call and default
        namespace. Tests for both string and CIMClassName input
        """
        skip_if_moftab_regenerated()

        conn.compile_mof_string(tst_assoc_mof, namespace=ns)

        if ns is not None:
            cln = CIMClassName(cln, namespace=ns)

        if isinstance(exp_rslt, (list, tuple)):

            # The code to be tested
            results = conn.Associators(cln, AssocClass=ac, Role=role,
                                       ResultRole=rr, ResultClass=rc,
                                       IncludeQualifiers=iq,
                                       IncludeClassOrigin=ico,
                                       PropertyList=pl)

            assert isinstance(results, list), "desc: {}".format(desc)
            assert len(results) == len(exp_rslt), "desc: {}".format(desc)
            for result in results:
                assert isinstance(result, tuple)
                assert isinstance(result[0], CIMClassName)
                assert isinstance(result[1], CIMClass)

            # Test for property lists matching
            if pl == "":
                for cls in results:
                    assert not cls.properties
            elif pl:
                for propname in pl:
                    for cls in results:
                        assert propname in cls.properties, \
                            "desc: {}".format(desc)
                        assert len(pl) == len(cls.properties), \
                            "desc: {}".format(desc)
            elif pl is None:
                repo_cls = conn.GetClass(cln)
                prop_count = len(repo_cls.properties)
                for _, cls in results:
                    assert len(cls.properties) == prop_count
            else:
                assert False, "Invalid pl parameter {}".format(pl)

            if iq:
                for _, cls in results:
                    if iq:
                        assert cls.qualifiers is not None
                    else:
                        assert not cls.qualifiers

            for _, cls in results:
                for prop in cls.properties.values():
                    if ico:
                        assert prop.class_origin
                    else:
                        assert prop.class_origin is None

            clns = [result[0].classname for result in results]
            assert set(clns) == set(exp_rslt), "desc: {}".format(desc)

        else:
            assert isinstance(exp_rslt, Exception)
            exp_exc = exp_rslt

            if isinstance(exp_exc, CIMError) and \
                    exp_exc.status_code == CIM_ERR_INVALID_NAMESPACE:
                if isinstance(cln, six.string_types):
                    cln = CIMClassName(cln, namespace='badnamespacename')
                else:
                    cln.namespace = 'badnamespacename'

            with pytest.raises(type(exp_exc)) as exec_info:

                # The code to be tested
                conn.Associators(cln, AssocClass=ac, Role=role,
                                 ResultRole=rr, ResultClass=rc)

            exc = exec_info.value
            if isinstance(exp_exc, CIMError):
                assert exc.status_code == exp_exc.status_code, \
                    "desc: {}".format(desc)

    @pytest.mark.parametrize(
        "ns", INITIAL_NAMESPACES + [None])
    @pytest.mark.parametrize(
        "targ_obj", [
            'XXX_Blan',
            CIMInstanceName('XXX_Blah', keybindings={'InstanceID': 3}),
        ]
    )
    def test_associator_target_err(self, conn, tst_assoc_mof, ns, targ_obj):
        # pylint: disable=no-self-use
        """
        Test getting reference classnames with no options on call and default
        namespace. Tests for both string and CIMClassName input
        """
        skip_if_moftab_regenerated()

        conn.compile_mof_string(tst_assoc_mof, namespace=ns)
        with pytest.raises(CIMError) as exec_info:

            # The code to be tested
            conn.AssociatorNames(targ_obj)

        exc = exec_info.value
        assert exc.status_code == CIM_ERR_INVALID_PARAMETER


def assert_invokemethod_guarantees(
        provider, methodname, localobject, params):
    """
    Verify the guarantees given by the provider dispatcher for the provider
    method InvokeMethod().
    """

    # Verify Python parameter types
    assert isinstance(methodname, six.string_types)
    assert isinstance(localobject, (CIMInstanceName, CIMClassName))
    assert isinstance(params, NocaseDict)

    namespace = localobject.namespace
    assert isinstance(namespace, six.string_types)

    classname = localobject.classname
    assert isinstance(classname, six.string_types)

    # Verify guarantee that namespace exists in repo
    try:
        provider.cimrepository.validate_namespace(namespace)
    except KeyError as exc:
        raise AssertionError(str(exc))

    instance_store = provider.cimrepository.get_instance_store(namespace)
    class_store = provider.cimrepository.get_class_store(namespace)

    # Verify guarantee that target object is the registered class
    assert classname.lower() == 'cim_foo_sub_sub'

    # Verify guarantee that class exists in repo
    assert class_store.object_exists(classname)

    # Verify guarantee that for instance-level use, target instance exists in
    # repo
    if isinstance(localobject, CIMInstanceName):
        assert instance_store.object_exists(localobject)

    # Verify guarantee that method in class exposes the target method
    klass = class_store.get(classname)
    assert methodname in klass.methods

    # Verify guarantee that static methods are invoked only with class-level use
    method = klass.methods[methodname]
    if not isinstance(localobject, CIMInstanceName):
        # class-level use
        static_qual = method.qualifiers.get('Static')
        static_value = static_qual.value if static_qual else False
        assert static_value is True

    # Verify guarantees on specified input parameters
    for pn in params:

        # Verify guarantee that Params has the correct Python types
        assert isinstance(pn, six.string_types)
        param_in = params[pn]
        assert isinstance(param_in, CIMParameter)

        # Verify guarantee that specified input parameter exists in the method
        # declaration
        assert pn in method.parameters

        # Verify guarantee that specified input parameter is actually an input
        # parameter as per the method declaration
        in_qual = method.qualifiers.get('In')
        in_value = in_qual.value if in_qual else True
        assert in_value

        param_cls = method.parameters[pn]

        # Verify guarantee that specified input parameter has the correct
        # type-related attributes as per the method declaration
        assert param_in.type == param_cls.type
        assert param_in.is_array == param_cls.is_array


class Method1UserProvider(MethodProvider):
    """
    User test provider for InvokeMethod using CIM_Foo_sub_sub and its methods
    'Method1' and 'StaticMethod1'.

    This is basis for testing passing of input parameters correctly and
    generating some exceptions.  It uses only one input parameter where the
    value defines the test and one return parameter that provides data from the
    provider, normally the value of the parameter defined with the input
    parameter. Test for existence of method named method1
    """

    provider_classnames = 'CIM_Foo_sub_sub'

    def __init__(self, cimrepository):
        super(Method1UserProvider, self).__init__(cimrepository)

    def InvokeMethod(self, methodname, localobject, params):
        """
        Simplistic test method for CIM methods 'Method1' and 'StaticMethod1'
        in class 'CIM_Foo_sub_sub'.

        As a test provider, it asserts the guarantees given by the provider
        dispatcher.

        The function of both method implementations is to return certain
        values in output parameter "OutputParam1" and in the return value,
        depending on a requested value in input parameter "InputParam1",
        as follows:

        * InputParam1 = 'namespace':
          Set the namespace name in OutputParam1 as list(CIMParameter) and
          return value 0.
        * InputParam1 = 'namespace_tuple':
          Set the namespace name in OutputParam1 as tuple(CIMParameter) and
          return value 0.
        * InputParam1 = 'namespace_dict_value':
          Set the namespace name in OutputParam1 as dict(name:value) and
          return value 0.
        * InputParam1 = 'namespace_dict_cimparm':
          Set the namespace name in OutputParam1 as dict(name:CIMParameter) and
          return value 0.
        * InputParam1 = 'namespace_nocasedict_value':
          Set the namespace name in OutputParam1 as NocaseDict(name:value) and
          return value 0.
        * InputParam1 = 'namespace_nocasedict_cimparm':
          Set the namespace name in OutputParam1 as
          NocaseDict(name:CIMParameter) and return value 0.
        * InputParam1 = 'methodname':
          Set the method name in OutputParam1 and return value 0.
        * InputParam1 = 'localobject':
          Set the object name in OutputParam1 and return value 0.
        * InputParam1 = 'returnvalue':
          Set value 'returnvalue' in OutputParam1 and return value 1.
        * In addition, there are several InputParam1 values requesting invalid
          output parameter returns; they are all named
          'outparam_invalid{N}_{exc_type}'.

        For details on the parameters and return for this provider method,
        see :meth:`pywbem_mock.MethodProvider.InvokeMethod`.
        """

        # Since this is a test provider, it verifies the guarantees given
        # by the provider dispatcher. This is not necessary in a real provider.
        assert_invokemethod_guarantees(self, methodname, localobject, params)

        namespace = localobject.namespace

        if methodname.lower() in ['method1', 'staticmethod1']:

            if params:

                # Consider InputParam1 a required parameter if params exist.
                if "InputParam1" not in params:
                    raise CIMError(
                        CIM_ERR_INVALID_PARAMETER,
                        _format("Required input parameter {0} missing in "
                                "method input parameters: {1!A}.",
                                "InputParam1", params))

                # For test purposes, disallow any other input parameters.
                if len(params) != 1:
                    raise CIMError(
                        CIM_ERR_INVALID_PARAMETER,
                        _format("Input parameters specified in method input "
                                "parameters that are disallowed (for test "
                                "purposes): {0!A}.",
                                params))

                assert isinstance(params, NocaseDict)
                param = params["InputParam1"]

                # Verify guarantee that the type-related attributes of the
                # parameter are as defined in the method declaration.
                assert isinstance(param, CIMParameter)
                assert param.type == 'string'
                assert param.is_array is False
                assert param.embedded_object is None

                # Generate output parameters and return value based on value in
                # InputParam1
                val = param.value
                return_value = 0
                if val == 'namespace':
                    # return as list of CIMParameter
                    out_params = [
                        CIMParameter(
                            'OutputParam1', 'string', value=namespace),
                    ]
                elif val == 'namespace_tuple':
                    # return as tuple of CIMParameter
                    out_params = (
                        CIMParameter(
                            'OutputParam1', 'string', value=namespace),
                    )
                elif val == 'namespace_dict_value':
                    # return as dict of name:value
                    out_params = {
                        'OutputParam1': namespace,
                    }
                elif val == 'namespace_dict_cimparm':
                    # return as dict of name:CIMParameter
                    out_params = {
                        'OutputParam1': CIMParameter(
                            'OutputParam1', 'string', value=namespace),
                    }
                elif val == 'namespace_nocasedict_value':
                    # return as NocaseDict of name:value
                    out_params = NocaseDict([
                        ('OutputParam1', namespace),
                    ])
                elif val == 'namespace_nocasedict_cimparm':
                    # return as NocaseDict of name:CIMParameter
                    out_params = NocaseDict([
                        ('OutputParam1',
                         CIMParameter(
                             'OutputParam1', 'string', value=namespace)),
                    ])
                elif val == 'methodname':
                    out_params = [
                        CIMParameter(
                            'OutputParam1', 'string', value=methodname),
                    ]
                elif val == 'localobject':
                    out_params = [
                        CIMParameter(
                            'OutputParam1', 'string', value=localobject),
                    ]
                elif val == 'outparam_invalid1_typeerror':
                    out_params = 'invalid type: string'
                elif val == 'outparam_invalid2_valueerror':
                    # error is created further down
                    out_params = {
                        'OutputParam1': namespace,
                    }
                elif val == 'outparam_invalid3_typeerror':
                    out_params = [
                        # List item has invalid type
                        CIMQualifier('Q', 'invalid_data_type'),
                    ]
                elif val == 'outparam_invalid4_typeerror':
                    # entire outparams object has invalid type
                    out_params = CIMQualifier('Q', 'invalid_data_type')
                elif val == 'outparam_invalid5_typeerror':
                    out_params = {
                        # Dict value has invalid type
                        'OutputParam1': CIMQualifier('Q', 'invalid_data_type'),
                    }
                else:
                    assert val == 'returnvalue'  # testcase error if not
                    return_value = 1
                    out_params = [
                        CIMParameter(
                            'OutputParam1', 'string', value='returnvalue'),
                    ]
            else:
                out_params = None

            if val == 'outparam_invalid2_valueerror':
                return (return_value, out_params, 'invalid 3rd item')

            return (return_value, out_params)

        raise CIMError(CIM_ERR_METHOD_NOT_AVAILABLE)


class TestInvokeMethod(object):
    # pylint: disable=too-few-public-methods
    """
    Test invoking extrinsic methods in FakedWBEMConnection
    """

    INVOKEMETHOD1_TESTCASES = [

        # Testcases for test_invokemethod1(), with list items as follows:
        #
        # desc: Description of testcase
        # inputs: Dictionary of input parameters for
        #         FakedWBEMConnection.InvokeMethod():
        #         * ObjectName
        #         * MethodName
        #         * Params
        #         * params (optional)
        # exp_result: None if exception, or dictionary of expected results from
        #             FakedWBEMConnection.InvokeMethod():
        #             * return: Expected return value
        #             * params: Expected output parameters as dict(name:value)
        # exp_exc: None if success, or expected exception object
        # condition: True: run test
        #            False: Skip test
        #            'pdb': Break before test

        (
            'Execution of Method1 method with valid input param requesting '
            'namespace. Tests object name case insensitivity',
            {
                'ObjectName':
                    CIMInstanceName(
                        'cim_foo_sub_sub',
                        keybindings={'instanceid': 'CIM_Foo_sub_sub1'}),
                'Params': [('InputParam1', 'namespace')]},
            {
                'return': 0,
                'params': {'OutputParam1': 'root/cimv2'}},
            None, OK
        ),
        (
            'Execution of Method1 method with valid input param requesting '
            'namespace. Tests MethodName case insensitivity',
            {
                'ObjectName':
                    CIMInstanceName(
                        'CIM_Foo_sub_sub',
                        keybindings={'InstanceID': 'CIM_Foo_sub_sub1'}),
                'MethodName': 'method1',
                'Params': [('InputParam1', 'namespace')]},
            {
                'return': 0,
                'params': {'OutputParam1': 'root/cimv2'}},
            None, OK
        ),
        (
            'Execution of Method1 method with valid input param requesting '
            'namespace, via Params as tuple(name, value)',
            {
                'ObjectName':
                    CIMInstanceName(
                        'CIM_Foo_sub_sub',
                        keybindings={'InstanceID': 'CIM_Foo_sub_sub1'}),
                'Params': (('InputParam1', 'namespace'),)},
            {
                'return': 0,
                'params': {'OutputParam1': 'root/cimv2'}},
            None, OK
        ),
        (
            'Execution of Method1 method with valid input param requesting '
            'namespace, via Params as list(name, value)',
            {
                'ObjectName':
                    CIMInstanceName(
                        'CIM_Foo_sub_sub',
                        keybindings={'InstanceID': 'CIM_Foo_sub_sub1'}),
                'Params': [('InputParam1', 'namespace')]},
            {
                'return': 0,
                'params': {'OutputParam1': 'root/cimv2'}},
            None, OK
        ),
        (
            'Execution of Method1 method with valid input param requesting '
            'namespace, via Params as list(CIMParameter)',
            {
                'ObjectName':
                    CIMInstanceName(
                        'CIM_Foo_sub_sub',
                        keybindings={'InstanceID': 'CIM_Foo_sub_sub1'}),
                'Params': [
                    CIMParameter(
                        'InputParam1', type='string', value='namespace')]
            },
            {
                'return': 0,
                'params': {'OutputParam1': 'root/cimv2'}},
            None, OK
        ),
        (
            'Execution of Method1 method with valid input param requesting '
            'namespace, via Params as tuple(CIMParameter)',
            {
                'ObjectName':
                    CIMInstanceName(
                        'CIM_Foo_sub_sub',
                        keybindings={'InstanceID': 'CIM_Foo_sub_sub1'}),
                'Params': (
                    CIMParameter(
                        'InputParam1', type='string', value='namespace'),)
            },
            {
                'return': 0,
                'params': {'OutputParam1': 'root/cimv2'}},
            None, OK
        ),
        (
            'Execution of Method1 method with valid input param requesting '
            'namespace_tuple',
            {
                'ObjectName':
                    CIMInstanceName(
                        'CIM_Foo_sub_sub',
                        keybindings={'InstanceID': 'CIM_Foo_sub_sub1'}),
                'Params': [('InputParam1', 'namespace_tuple')]},
            {
                'return': 0,
                'params': {'OutputParam1': 'root/cimv2'}},
            None, OK
        ),
        (
            'Execution of Method1 method with valid input param requesting '
            'namespace_dict_value',
            {
                'ObjectName':
                    CIMInstanceName(
                        'CIM_Foo_sub_sub',
                        keybindings={'InstanceID': 'CIM_Foo_sub_sub1'}),
                'Params': [('InputParam1', 'namespace_dict_value')]},
            {
                'return': 0,
                'params': {'OutputParam1': 'root/cimv2'}},
            None, OK
        ),
        (
            'Execution of Method1 method with valid input param requesting '
            'namespace_dict_cimparm',
            {
                'ObjectName':
                    CIMInstanceName(
                        'CIM_Foo_sub_sub',
                        keybindings={'InstanceID': 'CIM_Foo_sub_sub1'}),
                'Params': [('InputParam1', 'namespace_dict_cimparm')]},
            {
                'return': 0,
                'params': {'OutputParam1': 'root/cimv2'}},
            None, OK
        ),
        (
            'Execution of Method1 method with valid input param requesting '
            'namespace_nocasedict_value',
            {
                'ObjectName':
                    CIMInstanceName(
                        'CIM_Foo_sub_sub',
                        keybindings={'InstanceID': 'CIM_Foo_sub_sub1'}),
                'Params': [('InputParam1', 'namespace_nocasedict_value')]},
            {
                'return': 0,
                'params': {'OutputParam1': 'root/cimv2'}},
            None, OK
        ),
        (
            'Execution of Method1 method with valid input param requesting '
            'namespace_nocasedict_cimparm',
            {
                'ObjectName':
                    CIMInstanceName(
                        'CIM_Foo_sub_sub',
                        keybindings={'InstanceID': 'CIM_Foo_sub_sub1'}),
                'Params': [('InputParam1',
                            'namespace_nocasedict_cimparm')]},
            {
                'return': 0,
                'params': {'OutputParam1': 'root/cimv2'}},
            None, OK
        ),
        (
            'Execution of Method1 method with valid input param requesting '
            'namespace, via params',
            {
                'ObjectName':
                    CIMInstanceName(
                        'CIM_Foo_sub_sub',
                        keybindings={'InstanceID': 'CIM_Foo_sub_sub1'}),
                'Params': [],
                'params': {'InputParam1': 'namespace'}},
            {
                'return': 0,
                'params': {'OutputParam1': 'root/cimv2'}},
            None, OK
        ),
        (
            'Execution of Method1 method with valid input param requesting '
            'localobject',
            {
                'ObjectName':
                    CIMInstanceName(
                        'CIM_Foo_sub_sub',
                        keybindings={'InstanceID': 'CIM_Foo_sub_sub1'}),
                'Params': [('InputParam1', 'localobject')]},
            {
                'return': 0,
                'params': {
                    'OutputParam1':
                        CIMInstanceName(
                            'CIM_Foo_sub_sub',
                            keybindings={'InstanceID': 'CIM_Foo_sub_sub1'},
                            namespace='root/cimv2')}
            },
            None, OK
        ),
        (
            'Execution of Method1 method with valid input param requesting '
            'methodname',
            {
                'ObjectName':
                    CIMInstanceName(
                        'CIM_Foo_sub_sub',
                        keybindings={'InstanceID': 'CIM_Foo_sub_sub1'}),
                'Params': [('InputParam1', 'methodname')]},
            {
                'return': 0,
                'params': {'OutputParam1': 'method1'}},
            None, OK
        ),
        (
            'Execution of Method1 method with valid input param requesting '
            'returnvalue',
            {
                'ObjectName':
                    CIMInstanceName(
                        'CIM_Foo_sub_sub',
                        keybindings={'InstanceID': 'CIM_Foo_sub_sub1'}),
                'Params': [('InputParam1', 'returnvalue')]},
            {
                'return': 1,
                'params': {'OutputParam1': 'returnvalue'}},
            None, OK
        ),
        (
            'Execution of (static) StaticMethod1 method on instance, with '
            'valid input param requesting namespace',
            {
                'ObjectName':
                    CIMInstanceName(
                        'CIM_Foo_sub_sub',
                        keybindings={'InstanceID': 'CIM_Foo_sub_sub1'}),
                'MethodName': 'StaticMethod1',
                'Params': [('InputParam1', 'namespace')]},
            {
                'return': 0,
                'params': {'OutputParam1': 'root/cimv2'}},
            None, OK
        ),
        (
            'Execution of (static) StaticMethod1 method on class specified as '
            'objectname string, with valid input param requesting namespace',
            {
                'ObjectName': 'CIM_Foo_sub_sub',
                'MethodName': 'StaticMethod1',
                'Params': [('InputParam1', 'namespace')]},
            {
                'return': 0,
                'params': {'OutputParam1': 'root/cimv2'}},
            None, OK
        ),
        (
            'Execution of (static) StaticMethod1 method on class specified as '
            'objectname CIMClassName, with valid input param requesting '
            'namespace',
            {
                'ObjectName': CIMClassName('CIM_Foo_sub_sub'),
                'MethodName': 'StaticMethod1',
                'Params': [('InputParam1', 'namespace')]},
            {
                'return': 0,
                'params': {'OutputParam1': 'root/cimv2'}},
            None, OK
        ),
        (
            'Failed Execution of (non-static) Method1 method on invalid class',
            {
                'ObjectName': CIMClassName('CIM_ClassDoesNotExist'),
                'Params': [('InputParam1', 'namespace')]},
            None,
            CIMError(CIM_ERR_NOT_FOUND), OK
        ),
        (
            'Execution of (non-static) Method1 method on class specified as '
            'objectname CIMClassName',
            {
                'ObjectName': CIMClassName('CIM_Foo_sub_sub'),
                'Params': [('InputParam1', 'namespace')]},
            None,
            CIMError(CIM_ERR_INVALID_PARAMETER), OK
        ),
        (
            'Execution of non-existend method on class specified as '
            'objectname CIMClassName',
            {
                'ObjectName': CIMClassName('CIM_Foo_sub_sub'),
                'MethodName': 'NonExistentMethodName',
                'Params': [('InputParam1', 'namespace')]},
            None,
            CIMError(CIM_ERR_METHOD_NOT_FOUND), OK
        ),
        (
            'Execution of Method1 method with invalid InstanceName',
            {
                'ObjectName':
                    CIMInstanceName(
                        'CIM_Foo_sub_sub',
                        keybindings={'InstanceID': 'DoesNotExist'}),
                'Params': [('InputParamx', 'bla')]},
            None,
            CIMError(CIM_ERR_NOT_FOUND), OK
        ),
        (
            'Execution of Method1 method with invalid input param name',
            {
                'ObjectName':
                    CIMInstanceName(
                        'CIM_Foo_sub_sub',
                        keybindings={'InstanceID': 'CIM_Foo_sub_sub1'}),
                'Params': [('InputParamx', 'bla')]},
            None,
            CIMError(CIM_ERR_INVALID_PARAMETER), OK
        ),
        (
            'Execution of Method1 method with valid input param that has '
            'invalid type',
            {
                'ObjectName':
                    CIMInstanceName(
                        'CIM_Foo_sub_sub',
                        keybindings={'InstanceID': 'CIM_Foo_sub_sub1'}),
                'Params': [('InputParam1', Uint32(42))]},
            None,
            CIMError(CIM_ERR_INVALID_PARAMETER), OK
        ),
        (
            'Execution of Method1 method with valid input param that has '
            'invalid is_array',
            {
                'ObjectName':
                    CIMInstanceName(
                        'CIM_Foo_sub_sub',
                        keybindings={'InstanceID': 'CIM_Foo_sub_sub1'}),
                'Params': [('InputParam1', ['namespace'])]},
            None,
            CIMError(CIM_ERR_INVALID_PARAMETER), OK
        ),
        (
            'Execution of Method1 method with valid input param that has '
            'invalid embedded_object',
            {
                'ObjectName':
                    CIMInstanceName(
                        'CIM_Foo_sub_sub',
                        keybindings={'InstanceID': 'CIM_Foo_sub_sub1'}),
                'Params': [
                    CIMParameter(
                        'InputParam1', type='string',
                        value=None, embedded_object='instance')]},
            None,
            CIMError(CIM_ERR_INVALID_PARAMETER), OK
        ),
        (
            'Execution of Method1 method with existing output-only param name',
            {
                'ObjectName':
                    CIMInstanceName(
                        'CIM_Foo_sub_sub',
                        keybindings={'InstanceID': 'CIM_Foo_sub_sub1'}),
                'Params': [('OutputParam1', 'bla')]},
            None,
            CIMError(CIM_ERR_INVALID_PARAMETER), OK
        ),
        (
            'Execution of Method1 method with valid input param requesting '
            'outparam_invalid1_typeerror',
            {
                'ObjectName':
                    CIMInstanceName(
                        'CIM_Foo_sub_sub',
                        keybindings={'InstanceID': 'CIM_Foo_sub_sub1'}),
                'Params': [('InputParam1', 'outparam_invalid1_typeerror')]},
            None,
            TypeError(), OK
        ),
        (
            'Execution of Method1 method with valid input param requesting '
            'outparam_invalid2_valueerror',
            {
                'ObjectName':
                    CIMInstanceName(
                        'CIM_Foo_sub_sub',
                        keybindings={'InstanceID': 'CIM_Foo_sub_sub1'}),
                'Params': [('InputParam1', 'outparam_invalid2_valueerror')]},
            None,
            ValueError(), OK
        ),
        (
            'Execution of Method1 method with valid input param requesting '
            'outparam_invalid3_typeerror',
            {
                'ObjectName':
                    CIMInstanceName(
                        'CIM_Foo_sub_sub',
                        keybindings={'InstanceID': 'CIM_Foo_sub_sub1'}),
                'Params': [('InputParam1', 'outparam_invalid3_typeerror')]},
            None,
            TypeError(), OK
        ),
        (
            'Execution of Method1 method with valid input param requesting '
            'outparam_invalid4_typeerror',
            {
                'ObjectName':
                    CIMInstanceName(
                        'CIM_Foo_sub_sub',
                        keybindings={'InstanceID': 'CIM_Foo_sub_sub1'}),
                'Params': [('InputParam1', 'outparam_invalid4_typeerror')]},
            None,
            TypeError(), OK
        ),
        (
            'Execution of Method1 method with valid input param requesting '
            'outparam_invalid5_typeerror',
            {
                'ObjectName':
                    CIMInstanceName(
                        'CIM_Foo_sub_sub',
                        keybindings={'InstanceID': 'CIM_Foo_sub_sub1'}),
                'Params': [('InputParam1', 'outparam_invalid5_typeerror')]},
            None,
            TypeError(), OK
        ),

    ]

    @pytest.mark.parametrize(
        "ns", INITIAL_NAMESPACES + [None])
    @pytest.mark.parametrize(
        "desc, inputs, exp_result, exp_exc, condition",
        INVOKEMETHOD1_TESTCASES)
    def test_invokemethod1(self, conn, tst_instances_mof, ns, desc, inputs,
                           exp_result, exp_exc, condition):
        # pylint: disable=no-self-use,unused-argument
        """
        Test extrinsic method invocation through the
        WBEMConnection.InovkeMethod method, This tests the process of
        installing and invoking the user-defined method but with the
        installation of the required classes outside of the provider
        registration process.
        """
        if not condition:
            pytest.skip("This test marked to be skipped by condition")
        skip_if_moftab_regenerated()

        conn.compile_mof_string(tst_instances_mof, namespace=ns)

        if 'test_class' not in inputs:
            test_class = Method1UserProvider
        else:
            test_class = inputs['test_class']

        if 'MethodName' not in inputs:
            method_name = 'method1'
        else:
            method_name = inputs['MethodName']

        tst_ns = ns or conn.default_namespace

        conn.register_provider(test_class(conn.cimrepository),
                               namespaces=tst_ns,
                               schema_pragma_files=None, verbose=False)

        # set namespace in ObjectName if required.
        object_name = inputs['ObjectName']

        if isinstance(object_name, (CIMClassName, CIMInstanceName)):
            object_name.namespace = ns
        else:
            # String ObjectName does not allow anything but default namespace
            # Bypass test if ns is not None
            if ns:
                pytest.skip("string object name only allows default namespace")

        Params = inputs['Params']  # pylint: disable=invalid-name
        assert Params is None or len(Params) <= 1

        if condition == 'pdb':
            import pdb  # pylint: disable=import-outside-toplevel
            pdb.set_trace()  # pylint: disable=forgotten-debug-statement

        if not exp_exc:
            # Two calls to account for **params
            if 'params' in inputs:

                # The code to be tested
                result = conn.InvokeMethod(method_name,
                                           object_name,
                                           Params,
                                           **inputs['params'])
            else:

                # The code to be tested
                result = conn.InvokeMethod(method_name,
                                           object_name,
                                           Params)

            # Test the return values against the input_param value
            return_value = result[0]
            output_params = result[1]

            assert return_value == exp_result['return']

            assert len(output_params) == len(exp_result['params'])
            for pname in output_params:
                output_pvalue = output_params[pname]
                exp_pvalue = exp_result['params'][pname]
                assert output_pvalue == exp_pvalue

        else:
            with pytest.raises(type(exp_exc)) as exec_info:

                # The code to be tested
                conn.InvokeMethod(method_name,
                                  object_name,
                                  inputs['Params'], )

            exc = exec_info.value
            if isinstance(exp_exc, CIMError):
                assert exc.status_code == exp_exc.status_code


class TestBaseProvider(object):
    # pylint: disable=too-few-public-methods
    """
    Tests for some methods of BaseProvider
    """

    IS_SUBCLASS_TESTCASES = [

        # Testcases for BaseProvider.is_subclass(), with list items as follows:
        #
        # desc: Description of testcase
        # inputs: Dictionary of input parameters for is_subclass():
        #         * klass
        #         * superclass
        # exp_result: Dictionary of expected return value of is_subclass():
        #         * return_value
        # exp_exc: None if success, or expected exception object
        # condition: True: run test
        #            False: Skip test
        #            'pdb': Break before test

        (
            'Class and superclass are the same and a leaf class',
            {
                'klass': 'CIM_Foo_sub_sub',
                'superclass': 'CIM_Foo_sub_sub',
            },
            {
                'return': True,
            },
            None, OK
        ),
        (
            'Class and superclass are the same and a middle class',
            {
                'klass': 'CIM_Foo_sub',
                'superclass': 'CIM_Foo_sub',
            },
            {
                'return': True,
            },
            None, OK
        ),
        (
            'Class and superclass are the same and a root class',
            {
                'klass': 'CIM_Foo',
                'superclass': 'CIM_Foo',
            },
            {
                'return': True,
            },
            None, OK
        ),
        (
            'Class is a direct subclass of superclass and a leaf class',
            {
                'klass': 'CIM_Foo_sub_sub',
                'superclass': 'CIM_Foo_sub',
            },
            {
                'return': True,
            },
            None, OK
        ),
        (
            'Class is a direct subclass of superclass which is a root class',
            {
                'klass': 'CIM_Foo_sub',
                'superclass': 'CIM_Foo',
            },
            {
                'return': True,
            },
            None, OK
        ),
        (
            'Class is an indirect subclass of superclass which is a root '
            'class',
            {
                'klass': 'CIM_Foo_sub_sub',
                'superclass': 'CIM_Foo',
            },
            {
                'return': True,
            },
            None, OK
        ),
        (
            'Class is a superclass of superclass (i.e. swapped)',
            {
                'klass': 'CIM_Foo_sub',
                'superclass': 'CIM_Foo_sub_sub',
            },
            {
                'return': False,
            },
            None, OK
        ),
        (
            'Class and superclass are direct siblings',
            {
                'klass': 'CIM_Foo_sub',
                'superclass': 'CIM_Foo_sub2',
            },
            {
                'return': False,
            },
            None, OK
        ),
        (
            'Class and superclass are indirect siblings',
            {
                'klass': 'CIM_Foo_sub_sub',
                'superclass': 'CIM_Foo_sub2',
            },
            {
                'return': False,
            },
            None, OK
        ),
        (
            'Class does not exist',
            {
                'klass': 'InvalidClass',
                'superclass': 'CIM_Foo_sub',
            },
            None,
            KeyError(), OK
        ),
        (
            'Superclass does not exist',
            {
                'klass': 'CIM_Foo_sub',
                'superclass': 'InvalidClass',
            },
            None,
            KeyError(), OK
        ),
        (
            'Class equals superclass and both do not exist',
            {
                'klass': 'InvalidClass',
                'superclass': 'InvalidClass',
            },
            None,
            KeyError(), OK
        ),
    ]

    @pytest.mark.parametrize(
        "ns", INITIAL_NAMESPACES + [None])
    @pytest.mark.parametrize(
        "desc, inputs, exp_result, exp_exc, condition",
        IS_SUBCLASS_TESTCASES)
    def test_is_subclass(self, conn, tst_classeswqualifiers, ns, desc, inputs,
                         exp_result, exp_exc, condition):
        # pylint: disable=no-self-use,unused-argument
        """
        Test BaseProvider.is_subclass().
        """
        if not condition:
            pytest.skip("This test marked to be skipped by condition")

        if condition == 'pdb':
            import pdb  # pylint: disable=import-outside-toplevel
            pdb.set_trace()  # pylint: disable=forgotten-debug-statement

        add_objects_to_repo(conn, ns, [tst_classeswqualifiers])

        tst_ns = ns or conn.default_namespace

        base_provider = BaseProvider(conn.cimrepository)
        class_store = conn.cimrepository.get_class_store(tst_ns)

        klass = inputs['klass']
        superclass = inputs['superclass']

        if not exp_exc:

            # The code to be tested
            result = base_provider.is_subclass(klass, superclass, class_store)

            # Test the return value against the expected return value
            assert result == exp_result['return']

        else:
            with pytest.raises(type(exp_exc)):

                # The code to be tested
                base_provider.is_subclass(klass, superclass, class_store)


@pytest.fixture()
def test_schema_root_dir():
    """
    Fixture defines the test_schema root directory for the schema and also
    removes the directory if it exists at the end of each test.
    This is a temporary directory and should be removed at the end of
    each test.
    """
    schema_dir = os.path.join(TEST_DIR, 'test_schema')
    yield schema_dir

    # Executes at the close of each test function
    if os.path.isdir(schema_dir):
        shutil.rmtree(schema_dir)


class TestDMTFCIMSchema(object):
    """
    Test the DMTFCIMSchema class in pywbem_mock.  Since we do not want to always
    be downloading the DMTF schema for CI testing, we will generally skip the
    first test.
    """

    def test_current_schema(self):
        # pylint: disable=no-self-use
        """
        Test the current schema in the TESTSUITE_SCHEMA_DIR directory.
        The schema should be loaded and available.
        The tests should not change the TESTSUITE_SCHEMA_DIR directory in any
        way.
        """
        schema = DMTFCIMSchema(DMTF_TEST_SCHEMA_VER, TESTSUITE_SCHEMA_DIR,
                               verbose=False)

        assert schema.schema_version == DMTF_TEST_SCHEMA_VER
        assert schema.schema_root_dir == TESTSUITE_SCHEMA_DIR
        assert schema.schema_version_str == '%s.%s.%s' % DMTF_TEST_SCHEMA_VER
        assert os.path.isdir(schema.schema_root_dir)
        assert os.path.isdir(schema.schema_mof_dir)
        assert os.path.isfile(schema.schema_pragma_file)
        assert os.path.isfile(schema.schema_zip_file)

        mof_dir = 'mofFinal%s' % schema.schema_version_str
        test_schema_mof_dir = os.path.join(TESTSUITE_SCHEMA_DIR, mof_dir)
        assert schema.schema_mof_dir == test_schema_mof_dir

        assert schema.schema_pragma_file == \
            os.path.join(test_schema_mof_dir,
                         'cim_schema_%s.mof' % (schema.schema_version_str))

        assert repr(schema) == 'DMTFCIMSchema(' \
                               'schema_version=%s, ' \
                               'schema_root_dir=%s, schema_zip_file=%s, ' \
                               'schema_mof_dir=%s, ' \
                               'schema_pragma_file=%s, ' \
                               'schema_zip_url=%s)' % \
                               (DMTF_TEST_SCHEMA_VER,
                                TESTSUITE_SCHEMA_DIR,
                                schema.schema_zip_file,
                                test_schema_mof_dir,
                                schema.schema_pragma_file,
                                schema.schema_zip_url)

        schema_mof = schema.build_schema_mof(['CIM_ComputerSystem', 'CIM_Door'])

        exp_mof = '#pragma locale ("en_US")\n' \
                  '#pragma include ("Device/CIM_Door.mof")\n' \
                  '#pragma include ("System/CIM_ComputerSystem.mof")\n'

        assert schema_mof == exp_mof

    def test_schema_final_load(self, test_schema_root_dir):
        # pylint: disable=no-self-use
        """
        Test the DMTFCIMSchema class and its methods to get a schema from the
        DMTF, expand it, and to create a partial MOF schema definition for
        compilation into a new directory. This should completely clean the
        directory before the test.
        """
        if not os.environ.get('TEST_SCHEMA_DOWNLOAD', False):
            pytest.skip("Test run only if TEST_SCHEMA_DOWNLOAD is non-empty.")

        schema = DMTFCIMSchema(DMTF_TEST_SCHEMA_VER, test_schema_root_dir,
                               verbose=False)

        assert schema.schema_version == DMTF_TEST_SCHEMA_VER
        assert schema.schema_root_dir == test_schema_root_dir
        assert schema.schema_version_str == '%s.%s.%s' % DMTF_TEST_SCHEMA_VER
        assert os.path.isdir(schema.schema_root_dir)
        assert os.path.isdir(schema.schema_mof_dir)
        assert os.path.isfile(schema.schema_pragma_file)
        assert os.path.isfile(schema.schema_zip_file)

        mof_dir = 'mofFinal%s' % schema.schema_version_str
        test_schema_mof_dir = os.path.join(test_schema_root_dir, mof_dir)
        assert schema.schema_mof_dir == test_schema_mof_dir

        assert schema.schema_pragma_file == \
            os.path.join(test_schema_mof_dir,
                         'cim_schema_%s.mof' % (schema.schema_version_str))

        assert repr(schema) == 'DMTFCIMSchema(' \
                               'schema_version=%s, ' \
                               'schema_root_dir=%s, schema_zip_file=%s, ' \
                               'schema_mof_dir=%s, ' \
                               'schema_pragma_file=%s, schema_zip_url=%s)' % \
                               (DMTF_TEST_SCHEMA_VER, test_schema_root_dir,
                                schema.schema_zip_file,
                                schema.schema_mof_dir,
                                schema.schema_pragma_file,
                                schema.schema_zip_url)

        schema_mof = schema.build_schema_mof(['CIM_ComputerSystem', 'CIM_Door'])

        exp_mof = '#pragma locale ("en_US")\n' \
                  '#pragma include ("Device/CIM_Door.mof")\n' \
                  '#pragma include ("System/CIM_ComputerSystem.mof")\n'

        assert schema_mof == exp_mof

    def test_schema_experimental_load(self):
        # pylint: disable=no-self-use
        """
        Test the DMTFCIMSchema class and its methods to get a schema from the
        DMTF, expand it, and to create a partial MOF schema definition for
        compilation. This test downloads a second schema into the
        TESTSUITE_SCHEMA_DIR directory and then removes it.  It should not
        touch the existing schema.
        """
        if not os.environ.get('TEST_SCHEMA_DOWNLOAD', False):
            pytest.skip("Test run only if TEST_SCHEMA_DOWNLOAD is non-empty.")

        schema = DMTFCIMSchema(DMTF_TEST_SCHEMA_VER, TESTSUITE_SCHEMA_DIR,
                               use_experimental=True, verbose=False)

        assert schema.schema_version == DMTF_TEST_SCHEMA_VER
        assert schema.schema_version_str == '%s.%s.%s' % DMTF_TEST_SCHEMA_VER
        assert os.path.isdir(schema.schema_root_dir)
        assert os.path.isdir(schema.schema_mof_dir)
        assert schema.schema_root_dir == TESTSUITE_SCHEMA_DIR
        mof_dir = 'mofExperimental%s' % schema.schema_version_str
        test_schema_mof_dir = os.path.join(TESTSUITE_SCHEMA_DIR, mof_dir)
        assert test_schema_mof_dir == mof_dir

        assert schema.schema_pragma_file == \
            os.path.join(test_schema_mof_dir,
                         'cim_schema_%s.mof' % (schema.schema_version_str))

        # remove the second schema and test to be sure removed.
        schema.remove()
        assert not os.path.isdir(test_schema_mof_dir)
        assert not os.path.isfile(schema.schema_pragma_file)
        assert os.path.isdir(schema.schema_root_dir)

    def test_second_schema_load(self):
        # pylint: disable=no-self-use
        """
        Test loading a second schema. This test loads a second schema
        into the TESTSUITE_SCHEMA_DIR directory and then removes it.
        """
        if not os.environ.get('TEST_SCHEMA_DOWNLOAD', False):
            pytest.skip("Test run only if TEST_SCHEMA_DOWNLOAD is non-empty.")

        schema = DMTFCIMSchema((2, 50, 0), TESTSUITE_SCHEMA_DIR, verbose=False)

        assert schema.schema_version == (2, 50, 0)
        assert schema.schema_version_str == '2.50.0'
        assert os.path.isdir(schema.schema_root_dir)
        assert os.path.isdir(schema.schema_mof_dir)

        assert schema.schema_root_dir == TESTSUITE_SCHEMA_DIR
        mof_dir = 'mofFinal%s' % schema.schema_version_str
        test_schema_mof_dir = os.path.join(TESTSUITE_SCHEMA_DIR, mof_dir)
        assert schema.schema_mof_dir == test_schema_mof_dir

        assert schema.schema_pragma_file == \
            os.path.join(test_schema_mof_dir,
                         'cim_schema_%s.mof' % (schema.schema_version_str))

        zip_path = schema.schema_zip_file
        assert os.path.isfile(zip_path)

        schema_mof = schema.build_schema_mof(['CIM_ComputerSystem', 'CIM_Door'])

        exp_mof = '#pragma locale ("en_US")\n' \
                  '#pragma include ("Device/CIM_Door.mof")\n' \
                  '#pragma include ("System/CIM_ComputerSystem.mof")\n'

        assert schema_mof == exp_mof

        schema.clean()
        assert not os.path.exists(schema.schema_mof_dir)
        assert os.path.exists(zip_path)

        schema.remove()
        assert not os.path.exists(zip_path)
        assert os.path.exists(TESTSUITE_SCHEMA_DIR)

    @pytest.mark.parametrize(
        "schema_version, exp_exc",
        [
            # schema_version: schema_version init argument for DMTFCIMSchema()
            # exp_exc: None or expected exception object.

            [(1, 2), ValueError()],
            ['blah', TypeError()],
            [(1, 'fred', 2), TypeError()],
            [(1, 205, 0), ValueError()]
        ]
    )
    def test_schema_invalid_version(self, test_schema_root_dir, schema_version,
                                    exp_exc):
        # pylint: disable=no-self-use
        """
        Test case where the class requested for the partial schema is not
        in the DMTF schema
        """

        with pytest.raises(type(exp_exc)):

            # The code to be tested
            DMTFCIMSchema(schema_version, test_schema_root_dir, verbose=VERBOSE)

    @pytest.mark.parametrize(
        "clns, exp_rslt",
        [
            # clns: Iterable of leaf classnames or string with single
            #       classname
            # exp_rslt: String defining the resulting cim_schema build list OR
            #           expected exception object

            [['CIM_ComputerSystem', 'CIM_Door'],
             '#pragma locale ("en_US")\n' \
             '#pragma include ("Device/CIM_Door.mof")\n' \
             '#pragma include ("System/CIM_ComputerSystem.mof")\n'],

            [['CIM_Door'],
             '#pragma locale ("en_US")\n' \
             '#pragma include ("Device/CIM_Door.mof")\n'],

            ['CIM_Door',
             '#pragma locale ("en_US")\n' \
             '#pragma include ("Device/CIM_Door.mof")\n'],

            [['CIM_Blah'], ValueError()],

            [['CIM_ComputerSystem', 'CIM_Door', 'CIM_Blah'], ValueError()],

        ]
    )
    def test_schema_build(self, clns, exp_rslt):
        # pylint: disable=no-self-use
        """
        Test case we use the existing DMTF schema used by other tests and
        create a partial schema mof.
        """
        schema = DMTFCIMSchema(DMTF_TEST_SCHEMA_VER, TESTSUITE_SCHEMA_DIR,
                               verbose=False)

        if isinstance(exp_rslt, six.string_types):

            # The code to be tested
            schema_mof = schema.build_schema_mof(clns)

            assert schema_mof == exp_rslt
        else:
            assert isinstance(exp_rslt, Exception)
            exp_exc = exp_rslt
            with pytest.raises(type(exp_exc)) as exec_info:

                # The code to be tested
                schema.build_schema_mof(clns)

            exc = exec_info.value
            exc_str = str(exc)
            if isinstance(clns, six.string_types):
                clns = [clns]
            for cln in clns:
                assert exc_str.find(cln)


TESTCASES_COPY_FAKEDWBEMCONNECTION = [

    # Each list item is a testcase tuple with these items:
    # * desc: Short testcase description.
    # * kwargs: Keyword arguments for the test function:
    #   * init_kwargs: keyword args for FakedWBEMConnection __init
    #   * perform_operation: Boolean that causes an operation to be performed
    # * exp_exc_types: Expected exception type(s), or None.
    # * exp_warn_types: Expected warning type(s), or None.
    # * condition: Boolean condition for testcase to run, or 'pdb' for
    #   debugger

    (
        "No init parameters, no operation performed",
        dict(
            init_kwargs={},
            perform_operation=False,
        ),
        None, None, True
    ),
    (
        "No init parameters, with operation performed",
        dict(
            init_kwargs={},
            perform_operation=True,
        ),
        None, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_COPY_FAKEDWBEMCONNECTION)
@simplified_test_function
def test_copy_fakedconn(
        testcase, init_kwargs, perform_operation):
    """Test FakedWBEMConnection.copy()"""

    conn = FakedWBEMConnection(**init_kwargs)

    if perform_operation:
        try:
            conn.GetQualifier('Abstract')
        except pywbem.Error:  # Should fail with not found
            pass

    # The code to be tested
    cpy = conn.copy()

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None

    # pylint: disable=protected-access,unidiomatic-type-check

    assert type(cpy) is type(conn)  # noqa: E721
    assert id(cpy) != id(conn)

    # Verify attributes that should have been copied

    assert_copy(cpy.default_namespace, conn.default_namespace)
    assert_copy(cpy.use_pull_operations, conn.use_pull_operations)
    assert_copy(cpy.stats_enabled, conn.stats_enabled)
    assert_copy(cpy.timeout, conn.timeout)
    assert_copy(cpy._response_delay, conn._response_delay)
    assert_copy(cpy._disable_pull_operations, conn._disable_pull_operations)
    assert_copy(cpy.url, conn.url)

    # Verify attributes that should have been reused from original

    assert id(cpy._cimrepository) == id(conn._cimrepository)
    assert id(cpy._provider_registry) == id(conn._provider_registry)
    assert id(cpy._provider_dependent_registry) == \
        id(conn._provider_dependent_registry)
    assert id(cpy._providerdispatcher) == id(conn._providerdispatcher)
    assert id(cpy._mainprovider) == id(conn._mainprovider)

    # pylint: enable=protected-access,unidiomatic-type-check
