"""
Test memory leaks for dictionary classes used by pywbem.
"""

from __future__ import absolute_import, print_function

import sys
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


# collections.OrderedDict has fixed its ref.cycles starting with Python 3.2
ORDEREDDICT_LEAKFREE_VERSION = (3, 2)


@pytest.mark.xfail(
    sys.version_info < ORDEREDDICT_LEAKFREE_VERSION,
    reason="OrderedDict has reference cycles on py<3.2")
@yagot.garbage_checked()
def test_leaks_OrderedDict_empty():
    """
    Test function with empty OrderedDict object.

    Note: collections.OrderedDict has memory leaks on Python 2.7; see
    https://bugs.python.org/issue9825. That issue was fixed in Python 3.2, but
    the change in Python 2.7 apparently was not sufficient to remove the leak.
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


@pytest.mark.xfail(
    sys.version_info < ORDEREDDICT_LEAKFREE_VERSION,
    reason="NocaseDict uses OrderedDict")
@yagot.garbage_checked()
def test_leaks_NocaseDict_empty():
    """
    Test function with empty NocaseDict object.
    """
    _ = NocaseDict()


@pytest.mark.xfail(
    sys.version_info < ORDEREDDICT_LEAKFREE_VERSION,
    reason="NocaseDict uses OrderedDict")
@yagot.garbage_checked()
def test_leaks_NocaseDict_one():
    """
    Test function with NocaseDict object containing one string item.
    """
    _ = NocaseDict(a='b')
