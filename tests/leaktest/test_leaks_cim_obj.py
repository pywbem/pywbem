"""
Test memory leaks for cim_obj.py module.
"""

from __future__ import absolute_import, print_function

import sys
import pytest
import yagot

# pylint: disable=wrong-import-position, wrong-import-order, invalid-name
from ..utils import import_installed
pywbem = import_installed('pywbem')
from pywbem import CIMClassName, CIMInstanceName, CIMClass, CIMInstance, \
    CIMProperty, CIMMethod, CIMParameter, CIMQualifier, \
    CIMQualifierDeclaration  # noqa: E402
# pylint: enable=wrong-import-position, wrong-import-order, invalid-name

# NocaseDict uses collections.OrderedDict which fixed its reference cycles in
# Python 3.2
NOCASEDICT_LEAKFREE_VERSION = (3, 2)


@yagot.garbage_checked()
def test_leaks_CIMClassName_minimal():
    """
    Test function with a minimal CIMClassName object (i.e. no keybindings).
    """
    _ = CIMClassName(
        'CIM_Foo',
        namespace='root',
        host='woot.com',
    )


@pytest.mark.xfail(
    sys.version_info < NOCASEDICT_LEAKFREE_VERSION,
    reason="CIMClass uses NocaseDict")
@yagot.garbage_checked()
def test_leaks_CIMClass_minimal():
    """
    Test function with a minimal CIMClass object (i.e. no members, no path).
    """
    _ = CIMClass(
        'CIM_Foo',
        superclass='CIM_Super',
    )


@pytest.mark.xfail(
    sys.version_info < NOCASEDICT_LEAKFREE_VERSION,
    reason="CIMClass uses NocaseDict")
@yagot.garbage_checked()
def test_leaks_CIMClass_property():
    """
    Test function with a CIMClass object that has one property.
    """
    _ = CIMClass(
        'CIM_Foo',
        properties=[
            CIMProperty('P1', value=None, type='string'),
        ]
    )


@pytest.mark.xfail(
    sys.version_info < NOCASEDICT_LEAKFREE_VERSION,
    reason="CIMClass uses NocaseDict")
@yagot.garbage_checked()
def test_leaks_CIMClass_method():
    """
    Test function with a CIMClass object that has one method.
    """
    _ = CIMClass(
        'CIM_Foo',
        methods=[
            CIMMethod('M1', return_type='string'),
        ]
    )


@pytest.mark.xfail(
    sys.version_info < NOCASEDICT_LEAKFREE_VERSION,
    reason="CIMClass uses NocaseDict")
@yagot.garbage_checked()
def test_leaks_CIMClass_qualifier():
    """
    Test function with a CIMClass object that has one qualifier.
    """
    _ = CIMClass(
        'CIM_Foo',
        qualifiers=[
            CIMQualifier('Q1', value='q'),
        ]
    )


@pytest.mark.xfail(
    sys.version_info < NOCASEDICT_LEAKFREE_VERSION,
    reason="CIMInstanceName uses NocaseDict")
@yagot.garbage_checked()
def test_leaks_CIMInstanceName_minimal():
    """
    Test function with a CIMInstanceName object that has keybindings with two
    keys.
    """
    _ = CIMInstanceName(
        'CIM_Foo',
        namespace='root',
        host='woot.com',
        keybindings=dict(P1='a', P2=42),
    )


@pytest.mark.xfail(
    sys.version_info < NOCASEDICT_LEAKFREE_VERSION,
    reason="CIMInstance uses NocaseDict")
@yagot.garbage_checked()
def test_leaks_CIMInstance_minimal():
    """
    Test function with a minimal CIMInstance object (i.e. no properties, no
    qualifiers).
    """
    _ = CIMInstance(
        'CIM_Foo',
    )


@pytest.mark.xfail(
    sys.version_info < NOCASEDICT_LEAKFREE_VERSION,
    reason="CIMInstance uses NocaseDict")
@yagot.garbage_checked()
def test_leaks_CIMInstance_property():
    """
    Test function with a CIMInstance object that has one property.
    """
    _ = CIMInstance(
        'CIM_Foo',
        properties=[
            CIMProperty('P1', value='p'),
        ]
    )


@pytest.mark.xfail(
    sys.version_info < NOCASEDICT_LEAKFREE_VERSION,
    reason="CIMInstance uses NocaseDict")
@yagot.garbage_checked()
def test_leaks_CIMInstance_qualifier():
    """
    Test function with a CIMInstance object that has one qualifier.
    """
    _ = CIMInstance(
        'CIM_Foo',
        qualifiers=[
            CIMQualifier('Q1', value='q'),
        ]
    )


@pytest.mark.xfail(
    sys.version_info < NOCASEDICT_LEAKFREE_VERSION,
    reason="CIMProperty uses NocaseDict")
@yagot.garbage_checked()
def test_leaks_CIMProperty_minimal():
    """
    Test function with a minimal CIMProperty object (i.e. no qualifiers).
    """
    _ = CIMProperty('P1', value='bla')


@pytest.mark.xfail(
    sys.version_info < NOCASEDICT_LEAKFREE_VERSION,
    reason="CIMMethod uses NocaseDict")
@yagot.garbage_checked()
def test_leaks_CIMMethod_minimal():
    """
    Test function with a minimal CIMMethod object (i.e. no parameters, no
    qualifiers).
    """
    _ = CIMMethod('M1', return_type='string')


@pytest.mark.xfail(
    sys.version_info < NOCASEDICT_LEAKFREE_VERSION,
    reason="CIMParameter uses NocaseDict")
@yagot.garbage_checked()
def test_leaks_CIMParameter_minimal():
    """
    Test function with a minimal CIMParameter object (i.e. no qualifiers).
    """
    _ = CIMParameter('P1', type='string')


@yagot.garbage_checked()
def test_leaks_CIMQualifier_minimal():
    """
    Test function with a minimal CIMQualifier object.
    """
    _ = CIMQualifier('Q1', value='bla')


@pytest.mark.xfail(
    sys.version_info < NOCASEDICT_LEAKFREE_VERSION,
    reason="CIMQualifierDeclaration uses NocaseDict")
@yagot.garbage_checked()
def test_leaks_CIMQualifierDeclaration_minimal():
    """
    Test function with a minimal CIMQualifierDeclaration object (i.e. no
    scopes).
    """
    _ = CIMQualifierDeclaration('Q1', type='string')
