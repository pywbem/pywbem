"""
Test memory leaks for cim_xml.py module.
"""

from __future__ import absolute_import, print_function

import pytest
import yagot

# pylint: disable=wrong-import-position, wrong-import-order, invalid-name
from ..utils import import_installed
pywbem = import_installed('pywbem')
from pywbem._cim_xml import CIMElement, VALUE  # noqa: E402
# pylint: enable=wrong-import-position, wrong-import-order, invalid-name


@yagot.garbage_checked()
def test_leaks_CIMElement_empty():
    """
    Test function with an empty CIMElement object.
    """
    _ = CIMElement('dummy')


@yagot.garbage_checked()
def test_leaks_VALUE_empty():
    """
    Test function with a VALUE object that is empty (ie. no text child).
    """
    _ = VALUE(pcdata=None)


@pytest.mark.skip("Temporarily skipped")
@yagot.garbage_checked()
def test_leaks_VALUE_string():
    """
    Test function with a VALUE object of string.
    """
    _ = VALUE(pcdata='abc')
