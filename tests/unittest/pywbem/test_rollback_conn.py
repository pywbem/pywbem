"""
Unittest functions in _rollback_conn.
"""

from __future__ import print_function, absolute_import

import re
from copy import deepcopy
import pytest
from mock import patch

from ..utils.pytest_extensions import simplified_test_function

# pylint: disable=wrong-import-position, wrong-import-order, invalid-name
from ...utils import import_installed
pywbem = import_installed('pywbem')
from pywbem import RollbackWBEMConnection, RollbackError, \
    RollbackPreparationError, WBEMConnection, CIMInstanceName, \
    CIMInstance, CIMClass, CIMProperty, CIMMethod, CIMQualifier, \
    CIMQualifierDeclaration, CIMError, HTTPError, Uint32, \
    CIM_ERR_FAILED, CIM_ERR_NOT_FOUND, CIM_ERR_ALREADY_EXISTS, \
    CIM_ERR_METHOD_NOT_AVAILABLE  # noqa: E402
pywbem_mock = import_installed('pywbem_mock')
from pywbem_mock import FakedWBEMConnection, MethodProvider  # noqa: E402
# pylint: enable=wrong-import-position, wrong-import-order, invalid-name


def remove_path_origin(cim_obj):
    """
    Return a copy of a CIMInstance or CIMClass object with removed path and
    class origin of its properties and methods.
    """
    assert isinstance(cim_obj, (CIMInstance, CIMClass))
    cim_obj = deepcopy(cim_obj)
    cim_obj.path = None
    for prop in cim_obj.properties.values():
        prop.class_origin = None
    if isinstance(cim_obj, CIMClass):
        for meth in cim_obj.methods.values():
            meth.class_origin = None
    return cim_obj


def assert_equal_ignoring_path_origin(act_obj, exp_obj, msg):
    """
    Assert that two objects are equal, except that if they are CIMInstance or
    CIMClass objects or lists/tuples thereof, then their path and the class
    origin of their properties and methods is ignored in the equality test.

    Background for this function is that some WBEM operations return instances
    or classes with the path and class origin set, and ignoring that keeps the
    testcase definitions simpler.
    """

    if isinstance(exp_obj, (list, tuple)):
        assert len(act_obj) == len(exp_obj), msg
        for i, exp_obj_item in enumerate(exp_obj):
            act_obj_item = act_obj[i]
            assert_equal_ignoring_path_origin(act_obj_item, exp_obj_item, msg)
        return

    if isinstance(exp_obj, (CIMInstance, CIMClass)):
        act_obj = remove_path_origin(act_obj)
        exp_obj = remove_path_origin(exp_obj)

    assert act_obj == exp_obj, msg


# A simple mock repository for testing:

REPO_OBJS_QUAL_KEY = CIMQualifierDeclaration(
    'Key', type='boolean', value=False,
    scopes=dict(PROPERTY=True))
REPO_OBJS_QUAL_KEY_NEW = CIMQualifierDeclaration(
    'Key', type='boolean', value=False,
    scopes=dict(PROPERTY=True, REFERENCE=True))

REPO_OBJS_QUAL_KOO = CIMQualifierDeclaration(
    'Koo', type='boolean', value=False,
    scopes=dict(PROPERTY=True))

REPO_OBJS_PROP_FOO_K1 = CIMProperty(
    'K1', type='string', value=None,
    qualifiers=[CIMQualifier('Key', value=True)])

REPO_OBJS_PROP_FOO_P1 = CIMProperty(
    'P1', type='string', value=None)

REPO_OBJS_METH_FOO_M1 = CIMMethod(
    'M1', return_type='uint32')

REPO_OBJS_CLASS_FOO = CIMClass(
    'Foo',
    properties=[
        REPO_OBJS_PROP_FOO_K1,
        REPO_OBJS_PROP_FOO_P1,
    ],
    methods=[
        REPO_OBJS_METH_FOO_M1,
    ]
)
REPO_OBJS_CLASS_FOO_MOD = CIMClass(
    'Foo',
    properties=[
        REPO_OBJS_PROP_FOO_K1,
        REPO_OBJS_PROP_FOO_P1,
    ],
    methods=[
        # Deleted the method M1
    ]
)

REPO_OBJS_INSTNAME_FOO_K1 = CIMInstanceName(
    'Foo',
    keybindings=dict(K1='k1'),
    namespace='root/cimv2',
)
REPO_OBJS_INST_FOO_K1 = CIMInstance(
    'Foo',
    properties=[
        CIMProperty('K1', value='k1'),
        CIMProperty('P1', value='p1'),
    ],
    path=REPO_OBJS_INSTNAME_FOO_K1,
)
REPO_OBJS_INST_FOO_K1_MOD = CIMInstance(
    'Foo',
    properties=[
        CIMProperty('K1', value='k1'),
        CIMProperty('P1', value='p1changed'),
    ],
    path=REPO_OBJS_INSTNAME_FOO_K1,
)

REPO_OBJS_INSTNAME_FOO_K2 = CIMInstanceName(
    'Foo',
    keybindings=dict(K1='k2'),
    namespace='root/cimv2',
)
REPO_OBJS_INST_FOO_K2_NEW = CIMInstance(
    'Foo',
    properties=[
        CIMProperty('K1', value='k2'),
        CIMProperty('P1', value='p2'),
    ],
    path=REPO_OBJS_INSTNAME_FOO_K2,
)

REPO_OBJS_CLASS_BOO_NEW = CIMClass('Boo')

REPO_OBJECTS = [
    REPO_OBJS_QUAL_KEY,
    REPO_OBJS_CLASS_FOO,
    REPO_OBJS_INST_FOO_K1,
]


# Providers for the simple mock repository:

class FooM1MethodProvider(MethodProvider):
    """
    A method provider for Foo.M1() in the simple repo.
    """
    provider_classnames = 'Foo'

    def InvokeMethod(self, methodname, localobject, params):
        """
        All method invocations for Foo.
        """
        if methodname.lower() == 'm1':
            return (Uint32(42), {})
        raise CIMError(CIM_ERR_METHOD_NOT_AVAILABLE)


REPO_PROVIDERS = [
    FooM1MethodProvider(),
]


# Dummy WBEM connections for testing:
FAKED_CONN = FakedWBEMConnection()
REAL_CONN = WBEMConnection(url="localhost")


TESTCASES_RBCONN_INIT = [

    # Testcases for initialization of a RollbackWBEMConnection object.

    # Each list item is a testcase tuple with these items:
    # * desc: Short testcase description.
    # * kwargs: Keyword arguments for the test function:
    #   * init_kwargs: dict of init arguments for RollbackWBEMConnection
    #   * exp_attrs: dict of expected RollbackWBEMConnection attrs after init
    # * exp_exc_types: Expected exception type(s), or None.
    # * exp_warn_types: Expected warning type(s), or None.
    # * condition: Boolean condition for testcase to run, or 'pdb' for
    #   debugger

    (
        "Missing required conn init parameter",
        dict(
            init_kwargs=dict(),
            exp_attrs=dict(),
        ),
        TypeError, None, True
    ),
    (
        "Invalid type for conn init parameter",
        dict(
            init_kwargs=dict(conn='bla'),
            exp_attrs=dict(),
        ),
        TypeError, None, True
    ),
    (
        "Pass FakedWBEMConnection() object for conn init parameter",
        dict(
            init_kwargs=dict(conn=FAKED_CONN),
            exp_attrs=dict(conn=FAKED_CONN, undo_list=[]),
        ),
        None, None, True
    ),
    (
        "Pass WBEMConnection() object for conn init parameter",
        dict(
            init_kwargs=dict(conn=REAL_CONN),
            exp_attrs=dict(conn=REAL_CONN, undo_list=[]),
        ),
        None, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_RBCONN_INIT)
@simplified_test_function
def test_rbconn_init(testcase, init_kwargs, exp_attrs):
    """
    Test function for initialization of a RollbackWBEMConnection object.
    """

    # The code to be tested
    conn = RollbackWBEMConnection(**init_kwargs)

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None

    for name in exp_attrs:
        exp_value = exp_attrs[name]
        act_value = getattr(conn, name)
        assert act_value == exp_value


TESTCASES_RBCONN_OPERATION = [

    # Testcases for RollbackWBEMConnection operation method calls.

    # Each list item is a testcase tuple with these items:
    # * desc: Short testcase description.
    # * kwargs: Keyword arguments for the test function:
    #   * method: Name of operation method to call.
    #   * kwargs: Keyword arguments for the operation being called.
    #   * inject_exc: Dictionary defining an exception to inject into an
    #     operation, or None:
    #     * method: Name of the operation method that should raise the
    #       exception.
    #     * exc_obj: Exception object to be raised.
    #   * exp_result: Expected return value from operation being called.
    #   * exp_undo_method: Expected name of operation undo method, or None to
    #     indicate that no undo item is expected.
    #   * exp_undo_kwargs: Expected keyword arguments for the undo method, or
    #     None.
    # * exp_exc_types: Expected exception type(s), or None.
    # * exp_warn_types: Expected warning type(s), or None.
    # * condition: Boolean condition for testcase to run, or 'pdb' for
    #   debugger

    # Methods that have undo work (we test all of them):
    (
        "ModifyInstance on existing instance Foo.K1=k1",
        dict(
            method='ModifyInstance',
            kwargs=dict(
                ModifiedInstance=REPO_OBJS_INST_FOO_K1_MOD,
            ),
            inject_exc=None,
            exp_result=None,
            exp_undo_method='ModifyInstance',
            exp_undo_kwargs=dict(
                ModifiedInstance=REPO_OBJS_INST_FOO_K1,
            ),
        ),
        None, None, True
    ),
    (
        "ModifyInstance on existing instance Foo.K1=k1, with failing "
        "undo preparation method GetInstance",
        dict(
            method='ModifyInstance',
            kwargs=dict(
                ModifiedInstance=REPO_OBJS_INST_FOO_K1_MOD,
            ),
            inject_exc=dict(
                method='GetInstance',
                exc_obj=CIMError(CIM_ERR_FAILED, "Injected error"),
            ),
            exp_result=None,
            exp_undo_method=None,
            exp_undo_kwargs=None,
        ),
        RollbackPreparationError, None, True
    ),
    (
        "ModifyInstance on non-existing instance Foo.K1=k2",
        dict(
            method='ModifyInstance',
            kwargs=dict(
                ModifiedInstance=REPO_OBJS_INST_FOO_K2_NEW,
            ),
            inject_exc=None,
            exp_result=CIMError(CIM_ERR_NOT_FOUND),
            exp_undo_method=None,
            exp_undo_kwargs=None,
        ),
        CIMError, None, True
    ),
    (
        "CreateInstance on non-existing instance Foo.K1=k2",
        dict(
            method='CreateInstance',
            kwargs=dict(
                NewInstance=REPO_OBJS_INST_FOO_K2_NEW,
            ),
            inject_exc=None,
            exp_result=REPO_OBJS_INSTNAME_FOO_K2,
            exp_undo_method='DeleteInstance',
            exp_undo_kwargs=dict(
                InstanceName=REPO_OBJS_INSTNAME_FOO_K2,
            ),
        ),
        None, None, True
    ),
    (
        "CreateInstance on existing instance Foo.K1=k1",
        dict(
            method='CreateInstance',
            kwargs=dict(
                NewInstance=REPO_OBJS_INST_FOO_K1,
            ),
            inject_exc=None,
            exp_result=CIMError(CIM_ERR_ALREADY_EXISTS),
            exp_undo_method=None,
            exp_undo_kwargs=None,
        ),
        CIMError, None, True
    ),
    (
        "DeleteInstance on existing instance Foo.K1=k1",
        dict(
            method='DeleteInstance',
            kwargs=dict(
                InstanceName=REPO_OBJS_INSTNAME_FOO_K1,
            ),
            inject_exc=None,
            exp_result=None,
            exp_undo_method='CreateInstance',
            exp_undo_kwargs=dict(
                NewInstance=REPO_OBJS_INST_FOO_K1,
            ),
        ),
        None, None, True
    ),
    (
        "DeleteInstance on existing instance Foo.K1=k1, with failing "
        "undo preparation method GetInstance",
        dict(
            method='DeleteInstance',
            kwargs=dict(
                InstanceName=REPO_OBJS_INSTNAME_FOO_K1,
            ),
            inject_exc=dict(
                method='GetInstance',
                exc_obj=CIMError(CIM_ERR_FAILED, "Injected error"),
            ),
            exp_result=None,
            exp_undo_method=None,
            exp_undo_kwargs=None,
        ),
        RollbackPreparationError, None, True
    ),
    (
        "DeleteInstance on non-existing instance Foo.K1=k2",
        dict(
            method='DeleteInstance',
            kwargs=dict(
                InstanceName=REPO_OBJS_INSTNAME_FOO_K2,
            ),
            inject_exc=None,
            exp_result=CIMError(CIM_ERR_NOT_FOUND),
            exp_undo_method=None,
            exp_undo_kwargs=None,
        ),
        CIMError, None, True
    ),
    (
        "InvokeMethod on existing instance Foo.K1=k1",
        dict(
            method='InvokeMethod',
            kwargs=dict(
                MethodName='M1',
                ObjectName=REPO_OBJS_INSTNAME_FOO_K1,
            ),
            inject_exc=None,
            exp_result=(Uint32(42), {}),
            exp_undo_method='RollbackError',
            exp_undo_kwargs=dict(
                message="Cannot roll back InvokeMethod",
            ),
        ),
        None, None, True
    ),
    (
        "ModifyClass on existing class Foo",
        dict(
            method='ModifyClass',
            kwargs=dict(
                ModifiedClass=REPO_OBJS_CLASS_FOO_MOD,
            ),
            inject_exc=None,
            exp_result=None,
            exp_undo_method='ModifyClass',
            exp_undo_kwargs=dict(
                ModifiedClass=REPO_OBJS_CLASS_FOO,
            ),
        ),
        None, None, True
    ),
    (
        "ModifyClass on existing class Foo, with failing "
        "undo preparation method GetClass",
        dict(
            method='ModifyClass',
            kwargs=dict(
                ModifiedClass=REPO_OBJS_CLASS_FOO_MOD,
            ),
            inject_exc=dict(
                method='GetClass',
                exc_obj=CIMError(CIM_ERR_FAILED, "Injected error"),
            ),
            exp_result=None,
            exp_undo_method=None,
            exp_undo_kwargs=None,
        ),
        RollbackPreparationError, None, True
    ),
    (
        "ModifyClass on non-existing class Boo",
        dict(
            method='ModifyClass',
            kwargs=dict(
                ModifiedClass=REPO_OBJS_CLASS_BOO_NEW,
            ),
            inject_exc=None,
            exp_result=CIMError(CIM_ERR_NOT_FOUND),
            exp_undo_method=None,
            exp_undo_kwargs=None,
        ),
        CIMError, None, True
    ),
    (
        "CreateClass on non-existing class Boo",
        dict(
            method='CreateClass',
            kwargs=dict(
                NewClass=REPO_OBJS_CLASS_BOO_NEW,
            ),
            inject_exc=None,
            exp_result=None,
            exp_undo_method='DeleteClass',
            exp_undo_kwargs=dict(
                ClassName='Boo',
            ),
        ),
        None, None, True
    ),
    (
        "CreateClass on existing class Foo",
        dict(
            method='CreateClass',
            kwargs=dict(
                NewClass=REPO_OBJS_CLASS_FOO,
            ),
            inject_exc=None,
            exp_result=CIMError(CIM_ERR_ALREADY_EXISTS),
            exp_undo_method=None,
            exp_undo_kwargs=None,
        ),
        CIMError, None, True
    ),
    (
        "DeleteClass on existing class Foo",
        dict(
            method='DeleteClass',
            kwargs=dict(
                ClassName='Foo',
            ),
            inject_exc=None,
            exp_result=None,
            exp_undo_method='CreateClass',
            exp_undo_kwargs=dict(
                NewClass=REPO_OBJS_CLASS_FOO,
            ),
        ),
        None, None, True
    ),
    (
        "DeleteClass on existing class Foo, with failing "
        "undo preparation method GetClass",
        dict(
            method='DeleteClass',
            kwargs=dict(
                ClassName='Foo',
            ),
            inject_exc=dict(
                method='GetClass',
                exc_obj=CIMError(CIM_ERR_FAILED, "Injected error"),
            ),
            exp_result=None,
            exp_undo_method=None,
            exp_undo_kwargs=None,
        ),
        RollbackPreparationError, None, True
    ),
    (
        "DeleteClass on non-existing class Boo",
        dict(
            method='DeleteClass',
            kwargs=dict(
                ClassName='Boo',
            ),
            inject_exc=None,
            exp_result=CIMError(CIM_ERR_NOT_FOUND),
            exp_undo_method=None,
            exp_undo_kwargs=None,
        ),
        CIMError, None, True
    ),
    (
        "SetQualifier on existing qualifier declaration Key",
        dict(
            method='SetQualifier',
            kwargs=dict(
                QualifierDeclaration=REPO_OBJS_QUAL_KEY_NEW,
            ),
            inject_exc=None,
            exp_result=None,
            exp_undo_method='SetQualifier',
            exp_undo_kwargs=dict(
                QualifierDeclaration=REPO_OBJS_QUAL_KEY,
            ),
        ),
        None, None, True
    ),
    (
        "SetQualifier on existing qualifier declaration Key, with failing "
        "undo preparation method GetQualifier raising CIMError",
        dict(
            method='SetQualifier',
            kwargs=dict(
                QualifierDeclaration=REPO_OBJS_QUAL_KEY_NEW,
            ),
            inject_exc=dict(
                method='GetQualifier',
                exc_obj=CIMError(CIM_ERR_FAILED, "Injected error"),
            ),
            exp_result=None,
            exp_undo_method=None,
            exp_undo_kwargs=None,
        ),
        RollbackPreparationError, None, True
    ),
    (
        "SetQualifier on existing qualifier declaration Key, with failing "
        "undo preparation method GetQualifier raising HTTPError",
        dict(
            method='SetQualifier',
            kwargs=dict(
                QualifierDeclaration=REPO_OBJS_QUAL_KEY_NEW,
            ),
            inject_exc=dict(
                method='GetQualifier',
                exc_obj=HTTPError(500, "Injected error"),
            ),
            exp_result=None,
            exp_undo_method=None,
            exp_undo_kwargs=None,
        ),
        RollbackPreparationError, None, True
    ),
    (
        "SetQualifier on non-existing qualifier declaration Koo",
        dict(
            method='SetQualifier',
            kwargs=dict(
                QualifierDeclaration=REPO_OBJS_QUAL_KOO,
            ),
            inject_exc=None,
            exp_result=None,
            exp_undo_method='DeleteQualifier',
            exp_undo_kwargs=dict(
                QualifierName='Koo',
            ),
        ),
        None, None, True
    ),
    (
        "SetQualifier on non-existing qualifier declaration Koo, with failing "
        "undo preparation method GetQualifier",
        dict(
            method='SetQualifier',
            kwargs=dict(
                QualifierDeclaration=REPO_OBJS_QUAL_KOO,
            ),
            inject_exc=dict(
                method='GetQualifier',
                exc_obj=CIMError(CIM_ERR_FAILED, "Injected error"),
            ),
            exp_result=None,
            exp_undo_method=None,
            exp_undo_kwargs=None,
        ),
        RollbackPreparationError, None, True
    ),
    (
        "DeleteQualifier on existing qualifier declaration Key",
        dict(
            method='DeleteQualifier',
            kwargs=dict(
                QualifierName='Key',
            ),
            inject_exc=None,
            exp_result=None,
            exp_undo_method='SetQualifier',
            exp_undo_kwargs=dict(
                QualifierDeclaration=REPO_OBJS_QUAL_KEY,
            ),
        ),
        None, None, True
    ),
    (
        "DeleteQualifier on existing qualifier declaration Key, with failing "
        "undo preparation method GetQualifier",
        dict(
            method='DeleteQualifier',
            kwargs=dict(
                QualifierName='Key',
            ),
            inject_exc=dict(
                method='GetQualifier',
                exc_obj=CIMError(CIM_ERR_FAILED, "Injected error"),
            ),
            exp_result=None,
            exp_undo_method=None,
            exp_undo_kwargs=None,
        ),
        RollbackPreparationError, None, True
    ),
    (
        "DeleteQualifier on non-existing qualifier declaration Koo",
        dict(
            method='DeleteQualifier',
            kwargs=dict(
                QualifierName='Koo',
            ),
            inject_exc=None,
            exp_result=CIMError(CIM_ERR_NOT_FOUND),
            exp_undo_method=None,
            exp_undo_kwargs=None,
        ),
        CIMError, None, True
    ),

    # Passthru methods without undo work:
    (
        "EnumerateInstances on existing class Foo",
        dict(
            method='EnumerateInstances',
            kwargs=dict(
                ClassName='Foo',
            ),
            inject_exc=None,
            exp_result=[REPO_OBJS_INST_FOO_K1],
            exp_undo_method=None,  # Indicates passthru method
            exp_undo_kwargs=None,
        ),
        None, None, True
    ),
    (
        "EnumerateInstanceNames on existing class Foo",
        dict(
            method='EnumerateInstanceNames',
            kwargs=dict(
                ClassName='Foo',
            ),
            inject_exc=None,
            exp_result=[REPO_OBJS_INSTNAME_FOO_K1],
            exp_undo_method=None,  # Indicates passthru method
            exp_undo_kwargs=None,
        ),
        None, None, True
    ),
    (
        "GetInstance on existing instance Foo.K1=k1",
        dict(
            method='GetInstance',
            kwargs=dict(
                InstanceName=REPO_OBJS_INSTNAME_FOO_K1,
            ),
            inject_exc=None,
            exp_result=REPO_OBJS_INST_FOO_K1,
            exp_undo_method=None,  # Indicates passthru method
            exp_undo_kwargs=None,
        ),
        None, None, True
    ),
    (
        "Associators on existing instance Foo.K1=k1",
        dict(
            method='Associators',
            kwargs=dict(
                ObjectName=REPO_OBJS_INSTNAME_FOO_K1,
            ),
            inject_exc=None,
            exp_result=[],
            exp_undo_method=None,  # Indicates passthru method
            exp_undo_kwargs=None,
        ),
        None, None, True
    ),
    (
        "AssociatorNames on existing instance Foo.K1=k1",
        dict(
            method='AssociatorNames',
            kwargs=dict(
                ObjectName=REPO_OBJS_INSTNAME_FOO_K1,
            ),
            inject_exc=None,
            exp_result=[],
            exp_undo_method=None,  # Indicates passthru method
            exp_undo_kwargs=None,
        ),
        None, None, True
    ),
    (
        "References on existing instance Foo.K1=k1",
        dict(
            method='References',
            kwargs=dict(
                ObjectName=REPO_OBJS_INSTNAME_FOO_K1,
            ),
            inject_exc=None,
            exp_result=[],
            exp_undo_method=None,  # Indicates passthru method
            exp_undo_kwargs=None,
        ),
        None, None, True
    ),
    (
        "ReferenceNames on existing instance Foo.K1=k1",
        dict(
            method='ReferenceNames',
            kwargs=dict(
                ObjectName=REPO_OBJS_INSTNAME_FOO_K1,
            ),
            inject_exc=None,
            exp_result=[],
            exp_undo_method=None,  # Indicates passthru method
            exp_undo_kwargs=None,
        ),
        None, None, True
    ),
    (
        "EnumerateClasses",
        dict(
            method='EnumerateClasses',
            kwargs=dict(),
            inject_exc=None,
            exp_result=[REPO_OBJS_CLASS_FOO],
            exp_undo_method=None,  # Indicates passthru method
            exp_undo_kwargs=None,
        ),
        None, None, True
    ),
    (
        "EnumerateClassNames",
        dict(
            method='EnumerateClassNames',
            kwargs=dict(),
            inject_exc=None,
            exp_result=['Foo'],
            exp_undo_method=None,  # Indicates passthru method
            exp_undo_kwargs=None,
        ),
        None, None, True
    ),
    (
        "GetClass on existing class Foo",
        dict(
            method='GetClass',
            kwargs=dict(
                ClassName='Foo',
            ),
            inject_exc=None,
            exp_result=REPO_OBJS_CLASS_FOO,
            exp_undo_method=None,  # Indicates passthru method
            exp_undo_kwargs=None,
        ),
        None, None, True
    ),
    (
        "EnumerateQualifiers",
        dict(
            method='EnumerateQualifiers',
            kwargs=dict(),
            inject_exc=None,
            exp_result=[REPO_OBJS_QUAL_KEY],
            exp_undo_method=None,  # Indicates passthru method
            exp_undo_kwargs=None,
        ),
        None, None, True
    ),
    (
        "GetQualifier on existing qualifier Key",
        dict(
            method='GetQualifier',
            kwargs=dict(
                QualifierName='Key',
            ),
            inject_exc=None,
            exp_result=REPO_OBJS_QUAL_KEY,
            exp_undo_method=None,  # Indicates passthru method
            exp_undo_kwargs=None,
        ),
        None, None, True
    ),

    # The following pass-through operations do not have testcases, because
    # that would make the testcase definition more complex:
    # * ExecQuery
    # * IterEnumerateInstances
    # * IterEnumerateInstancePaths
    # * IterAssociatorInstances
    # * IterAssociatorInstancePaths
    # * IterReferenceInstances
    # * IterReferenceInstancePaths
    # * IterQueryInstances
    # * OpenEnumerateInstances
    # * OpenEnumerateInstancePaths
    # * OpenAssociatorInstances
    # * OpenAssociatorInstancePaths
    # * OpenReferenceInstances
    # * OpenReferenceInstancePaths
    # * OpenQueryInstances
    # * PullInstancesWithPath
    # * PullInstancePaths
    # * PullInstances
    # * CloseEnumeration
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_RBCONN_OPERATION)
@simplified_test_function
def test_rbconn_operation(
        testcase, method, kwargs, inject_exc, exp_result, exp_undo_method,
        exp_undo_kwargs):
    """
    Test function for RollbackWBEMConnection operation method calls.

    Execute the defined operation method, verify it was called with the
    expected arguments, and verify the resulting undo list. This is an in-depth
    verification of each single operation method and its effects on the undo
    list.

    A pywbem mock environment with a simple repository REPO_OBJECTS and
    providers defined in REPO_PROVIDERS is used as the target connection of the
    rollback connection.

    The operation being tested is (Python-)mocked at the level of the
    FakedWBEMConnection class by wrapping it so that it is still called but the
    call can be verified using a Python mock object.
    """

    conn = FakedWBEMConnection()
    conn.add_cimobjects(REPO_OBJECTS)
    for prov in REPO_PROVIDERS:
        conn.register_provider(prov)

    rbconn = RollbackWBEMConnection(conn)
    meth = getattr(rbconn, method)

    with patch.object(conn, method, wraps=getattr(conn, method)) as method_mock:

        try:
            if inject_exc:
                inject_patcher = patch.object(conn, inject_exc['method'])
                inject_mock = inject_patcher.start()
                inject_mock.side_effect = inject_exc['exc_obj']

            # The code to be tested
            result = meth(**kwargs)

            # Ensure that exceptions raised in the remainder of this function
            # are not mistaken as expected exceptions
            assert testcase.exp_exc_types is None

            # Check return value
            assert_equal_ignoring_path_origin(
                result, exp_result, 'Unexpected result')

            # Check that the target connection operation was called correctly
            method_mock.assert_called_once()
            for arg_name in kwargs:
                exp_arg_value = kwargs[arg_name]
                act_kwargs = method_mock.call_args[1]
                act_arg_value = act_kwargs[arg_name]
                assert act_arg_value == exp_arg_value, arg_name

            # Check the undo list
            if exp_undo_method is None:
                assert len(rbconn.undo_list) == 0
            else:
                assert len(rbconn.undo_list) == 1
                orig_name, undo_name, undo_kwargs = rbconn.undo_list[0]
                assert orig_name == method
                assert undo_name == exp_undo_method
                if undo_name == 'RollbackError':
                    # Check just the message (as a regexp)
                    exp_msg_pattern = exp_undo_kwargs['message']
                    act_msg = undo_kwargs['message']
                    assert re.search(exp_msg_pattern, act_msg)
                else:
                    # Check each expected undo argument.
                    for arg_name in exp_undo_kwargs:
                        exp_arg_value = exp_undo_kwargs[arg_name]
                        act_arg_value = undo_kwargs[arg_name]
                        assert_equal_ignoring_path_origin(
                            exp_arg_value, act_arg_value,
                            "Unexpected undo argument {}".format(arg_name))
        finally:
            if inject_exc:
                inject_patcher.stop()


TESTCASES_RBCONN_COMMIT_ROLLBACK = [

    # Testcases for RollbackWBEMConnection.commit/rollback().
    # Each list item is a testcase tuple with these items:
    # * desc: Short testcase description.
    # * kwargs: Keyword arguments for the test function:
    #   * actions: List of actions to perform, where each list item specifies
    #     one method to be invoked as a dict with items:
    #     * method: Name of method to call.
    #     * kwargs: Keyword arguments for the method being called.
    #   * inject_exc: Dictionary defining an exception to inject into an
    #     operation, or None:
    #     * method: Name of the operation method that should raise the
    #       exception.
    #     * exc_obj: Exception object to be raised.
    #   * exp_orig_names: Expected original method names in the undo list
    #     after the actions have been performed.
    # * exp_exc_types: Expected exception type(s), or None.
    # * exp_warn_types: Expected warning type(s), or None.
    # * condition: Boolean condition for testcase to run, or 'pdb' for
    #   debugger

    (
        "rollback without any ops performed",
        dict(
            actions=[
                dict(method='rollback'),
            ],
            inject_exc=None,
            exp_orig_names=[],
        ),
        None, None, True
    ),
    (
        "commit without any ops performed",
        dict(
            actions=[
                dict(method='commit'),
            ],
            inject_exc=None,
            exp_orig_names=[],
        ),
        None, None, True
    ),
    (
        "ModifyInstance",
        dict(
            actions=[
                dict(
                    method='ModifyInstance',
                    kwargs=dict(
                        ModifiedInstance=REPO_OBJS_INST_FOO_K1_MOD,
                    )),
            ],
            inject_exc=None,
            exp_orig_names=['ModifyInstance'],
        ),
        None, None, True
    ),
    (
        "ModifyInstance + rollback",
        dict(
            actions=[
                dict(
                    method='ModifyInstance',
                    kwargs=dict(
                        ModifiedInstance=REPO_OBJS_INST_FOO_K1_MOD,
                    )),
                dict(method='rollback'),
            ],
            inject_exc=None,
            exp_orig_names=[],
        ),
        None, None, True
    ),
    (
        "ModifyInstance + DeleteInstance + rollback",
        dict(
            actions=[
                dict(
                    method='ModifyInstance',
                    kwargs=dict(
                        ModifiedInstance=REPO_OBJS_INST_FOO_K1_MOD,
                    )),
                dict(
                    method='DeleteInstance',
                    kwargs=dict(
                        InstanceName=REPO_OBJS_INSTNAME_FOO_K1,
                    )),
                dict(method='rollback'),
            ],
            inject_exc=None,
            exp_orig_names=[],
        ),
        None, None, True
    ),
    (
        "DeleteInstance + rollback, with failing "
        "undo method CreateInstance",
        dict(
            actions=[
                dict(
                    method='DeleteInstance',
                    kwargs=dict(
                        InstanceName=REPO_OBJS_INSTNAME_FOO_K1,
                    )),
                dict(method='rollback'),
            ],
            inject_exc=dict(
                method='CreateInstance',
                exc_obj=CIMError(CIM_ERR_FAILED, "Injected error"),
            ),
            exp_orig_names=[],
        ),
        RollbackError, None, True
    ),
    (
        "ModifyInstance + rollback + DeleteInstance",
        dict(
            actions=[
                dict(
                    method='ModifyInstance',
                    kwargs=dict(
                        ModifiedInstance=REPO_OBJS_INST_FOO_K1_MOD,
                    )),
                dict(method='rollback'),
                dict(
                    method='DeleteInstance',
                    kwargs=dict(
                        InstanceName=REPO_OBJS_INSTNAME_FOO_K1,
                    )),
            ],
            inject_exc=None,
            exp_orig_names=['DeleteInstance'],
        ),
        None, None, True
    ),
    (
        "ModifyInstance + commit",
        dict(
            actions=[
                dict(
                    method='ModifyInstance',
                    kwargs=dict(
                        ModifiedInstance=REPO_OBJS_INST_FOO_K1_MOD,
                    )),
                dict(method='commit'),
            ],
            inject_exc=None,
            exp_orig_names=[],
        ),
        None, None, True
    ),
    (
        "ModifyInstance + DeleteInstance + commit",
        dict(
            actions=[
                dict(
                    method='ModifyInstance',
                    kwargs=dict(
                        ModifiedInstance=REPO_OBJS_INST_FOO_K1_MOD,
                    )),
                dict(
                    method='DeleteInstance',
                    kwargs=dict(
                        InstanceName=REPO_OBJS_INSTNAME_FOO_K1,
                    )),
                dict(method='commit'),
            ],
            inject_exc=None,
            exp_orig_names=[],
        ),
        None, None, True
    ),
    (
        "ModifyInstance + commit + DeleteInstance",
        dict(
            actions=[
                dict(
                    method='ModifyInstance',
                    kwargs=dict(
                        ModifiedInstance=REPO_OBJS_INST_FOO_K1_MOD,
                    )),
                dict(method='commit'),
                dict(
                    method='DeleteInstance',
                    kwargs=dict(
                        InstanceName=REPO_OBJS_INSTNAME_FOO_K1,
                    )),
            ],
            inject_exc=None,
            exp_orig_names=['DeleteInstance'],
        ),
        None, None, True
    ),
    (
        "InvokeMethod + rollback (raises RollbackError)",
        dict(
            actions=[
                dict(
                    method='InvokeMethod',
                    kwargs=dict(
                        MethodName='M1',
                        ObjectName=REPO_OBJS_INSTNAME_FOO_K1,
                    )),
                dict(method='rollback'),  # raises RollbackError
            ],
            inject_exc=None,
            exp_orig_names=['InvokeMethod'],
        ),
        RollbackError, None, True
    ),
    (
        "InvokeMethod + commit + rollback",
        dict(
            actions=[
                dict(
                    method='InvokeMethod',
                    kwargs=dict(
                        MethodName='M1',
                        ObjectName=REPO_OBJS_INSTNAME_FOO_K1,
                    )),
                dict(method='commit'),
                dict(method='rollback'),
            ],
            inject_exc=None,
            exp_orig_names=[],
        ),
        None, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_RBCONN_COMMIT_ROLLBACK)
@simplified_test_function
def test_rbconn_commit_rollback(testcase, actions, inject_exc, exp_orig_names):
    """
    Test function for RollbackWBEMConnection.commit/rollback().

    Execute the defined actions (WBEM operations and commit/rollback) and
    verify that the undo list is as expected.

    A pywbem mock environment with a simple repository REPO_OBJECTS and
    providers defined in REPO_PROVIDERS is used as the target connection of the
    rollback connection.
    """

    conn = FakedWBEMConnection()
    conn.add_cimobjects(REPO_OBJECTS)
    for prov in REPO_PROVIDERS:
        conn.register_provider(prov)

    rbconn = RollbackWBEMConnection(conn)

    try:
        if inject_exc:
            inject_patcher = patch.object(conn, inject_exc['method'])
            inject_mock = inject_patcher.start()
            inject_mock.side_effect = inject_exc['exc_obj']

        # Perform the defined actions
        for action in actions:
            meth = getattr(rbconn, action['method'])
            kwargs = action.get('kwargs', {})

            # The code to be tested
            meth(**kwargs)

        # Ensure that exceptions raised in the remainder of this function
        # are not mistaken as expected exceptions
        assert testcase.exp_exc_types is None

        # Check the original names in the undo list
        act_orig_names = [item[0] for item in rbconn.undo_list]
        assert act_orig_names == exp_orig_names

    finally:
        if inject_exc:
            inject_patcher.stop()
