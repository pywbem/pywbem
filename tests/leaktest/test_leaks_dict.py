"""
Test memory leaks for dictionary classes used by pywbem.
"""

from collections import OrderedDict
try:
    from django.utils.datastructures import SortedDict as Django_SortedDict
except ImportError:
    Django_SortedDict = None
import pytest
import yagot

# pylint: disable=wrong-import-position, wrong-import-order, invalid-name
from ..utils import import_installed
pywbem = import_installed('pywbem')
from pywbem._cim_obj import NocaseDict  # noqa: E402
# pylint: enable=wrong-import-position, wrong-import-order, invalid-name


@yagot.garbage_checked()
def test_leaks_OrderedDict_empty():
    """
    Test function with empty OrderedDict object.
    """
    _ = OrderedDict()


@pytest.mark.skipif(
    Django_SortedDict is None,
    reason="django with SortedDict is not installed")
@yagot.garbage_checked()
def test_leaks_Django_SortedDict_empty():
    """
    Test function with empty django SortedDict object.

    Note: Django's SortedDict has been removed from the django package as of
    version 1.9. This test requires django<1.9 to be installed and is skipped
    otherwise.
    """
    _ = Django_SortedDict()


@yagot.garbage_checked()
def test_leaks_NocaseDict_empty():
    """
    Test function with empty NocaseDict object.
    """
    _ = NocaseDict()


@yagot.garbage_checked()
def test_leaks_NocaseDict_one():
    """
    Test function with NocaseDict object containing one string item.
    """
    _ = NocaseDict(a='b')
