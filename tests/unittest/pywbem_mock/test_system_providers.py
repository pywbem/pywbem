# -*- coding: utf-8 -*-
#
# (C) Copyright 2020 InovaDevelopment.com
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
Test of of the installation and operation of the CIM_Namespace provider.

"""
from __future__ import absolute_import, print_function

import os
import six
import pytest

from ..utils.pytest_extensions import simplified_test_function
from ..utils.dmtf_mof_schema_def import DMTF_TEST_SCHEMA_VER
from ...utils import skip_if_moftab_regenerated

# pylint: disable=wrong-import-position, wrong-import-order, invalid-name
from ...utils import import_installed
pywbem = import_installed('pywbem')
from pywbem import CIMError, WBEMServer, CIMInstance  # noqa: E402
pywbem_mock = import_installed('pywbem_mock')

from pywbem_mock import FakedWBEMConnection, DMTFCIMSchema  # noqa: E402
from pywbem_mock.config import OBJECTMANAGERCREATIONCLASSNAME, \
    SYSTEMCREATIONCLASSNAME, OBJECTMANAGERNAME, SYSTEMNAME  # noqa: E402
# pylint: enable=wrong-import-position, wrong-import-order, invalid-name

# Literal form {"blah: 0} faster than dict(blah=0) but same functionality
# pylint: disable=use-dict-literal

# Location of DMTF schema directory used by all tests.
# This directory is permanent and should not be removed.
TESTSUITE_SCHEMA_DIR = os.path.join('tests', 'schema')

VERBOSE = False

# test variables to allow selectively executing tests.
OK = True
RUN = True
FAIL = False


def add_objectmgr_instance(conn, ns, omdict):
    """
    Create an instance of CIM_ObjectManager from the properties defined
    in omdict (a dictionary of CIM_ObjectManager properties) in the server
    defined by conn.
    """
    ominst = inst_from_classname(conn, "CIM_ObjectManager",
                                 namespace=ns,
                                 property_values=omdict,
                                 include_missing_properties=False,
                                 include_path=True)

    conn.add_cimobjects(ominst, namespace=ns)


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


def test_interop_namespace_names():
    """
    Test the method interop_namespace_names. This is a single test
    with no parameters because it is really a static operation.
    """
    conn = FakedWBEMConnection()

    interop_ns = conn.interop_namespace_names

    # get valid set from WBEMServer.
    interop_namespaces = WBEMServer.INTEROP_NAMESPACES

    assert set(interop_ns) == set(interop_namespaces)
    # confirm case interop_ns is case-insensitive iterable
    for name in interop_namespaces:
        assert name.lower() in [ns.lower() for ns in interop_ns]


TESTCASES_IS_INTEROP_NAMESPACE = [
    ("verify interop True",
     dict(ns='interop', exp_rtn=True), None, None, OK),

    ("verify root/interop True",
     dict(ns='root/interop', exp_rtn=True), None, None, OK),

    ("verify root/interop True",
     dict(ns='root/pg_interop', exp_rtn=True), None, None, OK),

    ("verify root/blah False",
     dict(ns='root/blah', exp_rtn=False), None, None, OK),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_IS_INTEROP_NAMESPACE)
@simplified_test_function
def test_is_interop_namespace(testcase, ns, exp_rtn):
    # pylint: disable=unused-argument
    """
    Test the method _is_interop_namespace() which should return True
    or False depending on whether the tst_ns is a valid interop namespace
    name returns correct result.
    """
    conn = FakedWBEMConnection()

    assert conn.is_interop_namespace(ns) is exp_rtn
    assert conn.is_interop_namespace(ns.upper()) is exp_rtn


TESTCASES_FIND_INTEROP_NAMESPACE = [
    # deflt - default-namespace, string or None
    # nss = Other namespaces to add (String or list of strings)
    # exp_ns = Expected namespace returned

    ("Verify interop not in enviroment returns None",
     dict(deflt=None, nss=None, exp_ns=None), None, None, OK),

    ("Verify interop in enviroment returns interop",
     dict(deflt=None, nss=['interop'], exp_ns='interop'), None, None, OK),

    ("Verify INTEROP in enviroment returns INTEROP",
     dict(deflt=None, nss=['INTEROP'], exp_ns='INTEROP'), None, None, OK),

    ("Verify root/interop in enviroment returns interop",
     dict(deflt=None, nss=['root/interop'], exp_ns='root/interop'), None,
     None, OK),

    ("Verify interop in enviroment with other ns returns interop",
     dict(deflt=None, nss=['interop', 'root/blah'], exp_ns='interop'), None,
     None, OK),

    ("Verify interop in enviroment with other ns and default returns interop",
     dict(deflt='root/cimv2', nss=['interop', 'root/blah'], exp_ns='interop'),
     None, None, OK),

    ("Verify interop in enviroment with other ns and default returns interop",
     dict(deflt='root/cimv2', nss=['root/blah', 'interop'], exp_ns='interop'),
     None, None, OK),

    ("Verify interop as default can be found",
     dict(deflt='interop', nss=None, exp_ns='interop'), None, None, OK),

    ("Verify interop not in namespaces that has a namespace finds nothing",
     dict(deflt=None, nss=['root/blah'], exp_ns=None), None, None, OK),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_FIND_INTEROP_NAMESPACE)
@simplified_test_function
def test_find_interop_namespace(testcase, deflt, nss, exp_ns):
    # pylint: disable=unused-argument
    """
    Test the method
    """
    conn = FakedWBEMConnection(default_namespace=deflt)

    if nss:
        if isinstance(nss, six.string_types):
            nss = [nss]
        for name in nss:
            conn.add_namespace(name)

    rtnd_ns = conn.find_interop_namespace()

    assert rtnd_ns == exp_ns


TESTCASES_INSTALL_NAMESPACE_PROVIDER = [

    # Testcases for dictionary tests of the mock install_namespace_provider
    # method with different namespace names and

    # Each list item is a testcase tuple with these items:
    # * desc: Short testcase description.
    # * kwargs: Keyword arguments for the test function:
    #   * default_ns: Name of default namespace or None
    #   * ns: The interop namespace name.
    # * exp_exc_types: Expected exception type(s), or None.
    # * exp_warn_types: Expected warning type(s), or None.
    # * condition: Boolean condition for testcase to run, or 'pdb' for debugger

    (
        "Test with interop as interop namespace name",
        dict(
            default_ns=None,
            ns='interop',
        ),
        None, None, OK
    ),
    (
        "Test with interop as interop namespace name and root/blah default",
        dict(
            default_ns='root/blah',
            ns='interop',
        ),
        None, None, OK
    ),
    (
        "Test with root/interop as interop namespace name",
        dict(
            default_ns=None,
            ns='root/interop',
        ),
        None, None, OK
    ),
    (
        "Test with invalid interop namespace name",
        dict(
            default_ns=None,
            ns='root/interopx',
        ),
        CIMError, None, OK
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_INSTALL_NAMESPACE_PROVIDER)
@simplified_test_function
def test_install_namespace_provider(testcase, default_ns, ns):
    """
    Test installation of the namespace provider
    """
    # setup the connection and schema
    conn = FakedWBEMConnection(default_namespace=default_ns)

    skip_if_moftab_regenerated()

    schema = DMTFCIMSchema(DMTF_TEST_SCHEMA_VER, TESTSUITE_SCHEMA_DIR,
                           verbose=False)
    # code to be tested
    conn.install_namespace_provider(ns, schema.schema_pragma_file)

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None

    # Assert that the defined interop namespace is installed
    assert ns in conn.namespaces

    if default_ns:
        assert default_ns in conn.namespaces

    assert len(conn.EnumerateInstances("CIM_Namespace", ns)) == \
        len(conn.namespaces)

    for namespace in conn.namespaces:
        if namespace != ns:
            assert len(conn.EnumerateClasses(namespace=namespace)) == 0


TESTCASES_ADD_NAMESPACE_NAMESPACE_PROVIDER = [

    # Testcases for tests of adding namespaces and namespace provider using
    # mock add_namespaces as method to insert new namespaces

    # Each list item is a testcase tuple with these items:
    # * desc: Short testcase description.
    # * kwargs: Keyword arguments for the test function:
    #   * Pre_ns_to_add: Namespaces to create before namespace provider
    #     created
    #   * interop_ns: names of interop namespace or None if defined elsewhere
    #   * final_ns: namespaces added after namespace provider installed
    #   * total_exp_ns: list of all namespaces added.
    # * exp_exc_types: Expected exception type(s), or None.
    # * exp_warn_types: Expected warning type(s), or None.
    # * condition: Boolean condition for testcase to run, or 'pdb' for debugger

    (
        "Test with only default and interop",
        dict(
            initial_ns=[],
            interop_ns='interop',
            final_ns=[],
            total_exp_ns=['root/cimv2', 'interop']
        ),
        None, None, OK
    ),

    (
        "Test with namespaces before and after namespace provider added",
        dict(
            initial_ns=['ns_before'],
            interop_ns='interop',
            final_ns=['ns_after'],
            total_exp_ns=['root/cimv2', 'interop', 'ns_before', 'ns_after']
        ),
        None, None, OK
    ),
    (
        "Test with mutiple added namespaces",
        dict(
            initial_ns=['ns_b1', 'ns_b2'],
            interop_ns='interop',
            final_ns=['ns_a1', "ns_a2"],
            total_exp_ns=['root/cimv2', 'interop', 'ns_b1', 'ns_b2', 'ns_a1',
                          'ns_a2']
        ),
        None, None, OK
    ),
    (
        "Test with multiple interop; part of initial ns and interop_ns",
        dict(
            initial_ns=['ns_b1', 'ns_b2', 'interop'],
            interop_ns='interop_ns',
            final_ns=['ns_a1', "ns_a2"],
            total_exp_ns=['root/cimv2', 'interop', 'ns_b1', 'ns_b2', 'ns_a1',
                          'ns_a2']
        ),
        CIMError, None, OK
    ),
    (
        "Test with interop interop part of initial ns and interop",
        dict(
            initial_ns=['ns_b1', 'ns_b2', 'interop'],
            interop_ns='interop',
            final_ns=['ns_a1', "ns_a2"],
            total_exp_ns=['root/cimv2', 'interop', 'ns_b1', 'ns_b2', 'ns_a1',
                          'ns_a2']
        ),
        CIMError, None, OK
    ),
    (
        "Test fails build interop second time in final_ns",
        dict(
            initial_ns=['ns_b1', 'ns_b2'],
            interop_ns='interop',
            final_ns=['ns_a1', "ns_a2", 'interop'],
            total_exp_ns=['root/cimv2', 'interop', 'ns_b1', 'ns_b2', 'ns_a1',
                          'ns_a2']
        ),
        CIMError, None, OK
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_ADD_NAMESPACE_NAMESPACE_PROVIDER)
@simplified_test_function
def test_add_namespace_namespace_provider(testcase, initial_ns, interop_ns,
                                          final_ns, total_exp_ns):
    """
    Test use of conn.add_namespace and installation of namespace provider.
    This is because add_namespace must know of existence of namespace
    provider to allow ussing server.create_namespace() if a namespace
    provider exists.
    """
    # setup the connection and schema
    conn = FakedWBEMConnection()

    skip_if_moftab_regenerated()

    schema = DMTFCIMSchema(DMTF_TEST_SCHEMA_VER, TESTSUITE_SCHEMA_DIR,
                           verbose=False)

    for ns in initial_ns:
        conn.add_namespace(ns, verbose=VERBOSE)

    # Uses add_namespace before interop namespace created.
    if interop_ns:
        conn.add_namespace(interop_ns, verbose=VERBOSE)

    classnames = ["CIM_Namespace", "CIM_ObjectManager"]
    conn.compile_schema_classes(classnames,
                                schema.schema_pragma_file,
                                namespace=interop_ns,
                                verbose=VERBOSE)

    omdict = {"SystemCreationClassName": SYSTEMCREATIONCLASSNAME,
              "CreationClassName": OBJECTMANAGERCREATIONCLASSNAME,
              "SystemName": SYSTEMNAME,
              "Name": OBJECTMANAGERNAME,
              "ElementName": 'Mock_Test',
              "Description": "Mock_Test CIM Server"}

    add_objectmgr_instance(conn, interop_ns, omdict)

    # code to be tested
    conn.install_namespace_provider(interop_ns, schema.schema_pragma_file)

    # Use mock add_namespace to add namespace after namespace provider installed
    for ns in final_ns:
        conn.add_namespace(ns, verbose=VERBOSE)

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None

    # Assert that the defined interop namespace is installed
    assert interop_ns in conn.namespaces

    for ns in initial_ns:
        assert ns in conn.namespaces

    for ns in final_ns:
        assert ns in conn.namespaces

    assert len(conn.EnumerateInstances("CIM_Namespace", interop_ns)) == \
        len(conn.namespaces)

    for namespace in conn.namespaces:
        if namespace != 'interop':
            assert len(conn.EnumerateClasses(namespace=namespace)) == 0

    wbemserver = WBEMServer(conn)
    assert set(conn.namespaces) == set(wbemserver.namespaces)

    assert set(conn.namespaces) == set(total_exp_ns)

# TODO. Test add and remove namespaces with more variations


TESTCASES_ADD_CIMNAMESPACE_WITH_CREATENAMESPACE = [

    # Testcases for adding a namespace using wbemserver create_namespace after
    # interop namespace created.

    # Each list item is a testcase tuple with these items:
    # Each list item is a testcase tuple with these items:
    # * desc: Short testcase description.
    # * kwargs: Keyword arguments for the test function:
    #   * obj: Object that has dictionary behavior, e.g. IMInstanceName.
    #   * exp_dict: Expected dictionary items, for validation.
    # * exp_exc_types: Expected exception type(s), or None.
    # * exp_warn_types: Expected warning type(s), or None.
    # * condition: Boolean condition for testcase to run, or 'pdb' for debugger

    (
        "Test with only default and interop",
        dict(
            initial_ns=[],
            final_ns=[],
            total_exp_ns=['root/cimv2', 'interop']
        ),
        None, None, OK
    ),

    (
        "Test with namespaces before and after namespace provider added",
        dict(
            initial_ns=['ns_before'],
            final_ns=['ns_after'],
            total_exp_ns=['root/cimv2', 'interop', 'ns_before', 'ns_after']
        ),
        None, None, OK
    ),
    (
        "Test with multiple added namespaces",
        dict(
            initial_ns=['ns_b1', 'ns_b2'],
            final_ns=['ns_a1', "ns_a2"],
            total_exp_ns=['root/cimv2', 'interop', 'ns_b1', 'ns_b2', 'ns_a1',
                          'ns_a2']
        ),
        None, None, OK
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_ADD_CIMNAMESPACE_WITH_CREATENAMESPACE)
@simplified_test_function
def test_add_cimnamespace_with_createnamespace(testcase, initial_ns, final_ns,
                                               total_exp_ns):
    """
    Test installation of the namespace provider
    """
    # setup the connection and schema
    conn = FakedWBEMConnection()

    skip_if_moftab_regenerated()

    schema = DMTFCIMSchema(DMTF_TEST_SCHEMA_VER, TESTSUITE_SCHEMA_DIR,
                           verbose=False)

    for ns in initial_ns:
        conn.add_namespace(ns)

    interop_ns = 'interop'

    # Uses add_namespace before interop namespace created.
    conn.add_namespace(interop_ns)

    classnames = ["CIM_Namespace", "CIM_ObjectManager"]
    conn.compile_schema_classes(classnames,
                                schema.schema_pragma_file,
                                namespace=interop_ns,
                                verbose=False)

    omdict = {"SystemCreationClassName": SYSTEMCREATIONCLASSNAME,
              "CreationClassName": OBJECTMANAGERCREATIONCLASSNAME,
              "SystemName": SYSTEMNAME,
              "Name": OBJECTMANAGERNAME,
              "ElementName": 'Mock_Test',
              "Description": "Mock_Test CIM Server"}

    add_objectmgr_instance(conn, interop_ns, omdict)

    # code to be tested, install provider and add remaining namespaces
    conn.install_namespace_provider(interop_ns, schema.schema_pragma_file)

    # Usewbemserver to add namespace after namespace provider installed
    server = WBEMServer(conn)
    for ns in final_ns:
        server.create_namespace(ns)

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None

    # Assert that the defined interop namespace is installed
    assert 'interop' in conn.namespaces

    for ns in initial_ns:
        assert ns in conn.namespaces

    for ns in final_ns:
        assert ns in conn.namespaces

    assert len(conn.EnumerateInstances("CIM_Namespace", interop_ns)) == \
        len(conn.namespaces)

    for namespace in conn.namespaces:
        if namespace != 'interop':
            assert len(conn.EnumerateClasses(namespace=namespace)) == 0

    assert set(conn.namespaces) == set(total_exp_ns)
