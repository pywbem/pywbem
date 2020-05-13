"""
Test memory leaks for _statistics.py module.
"""

from __future__ import absolute_import, print_function

import pytest
import yagot

# pylint: disable=wrong-import-position, wrong-import-order, invalid-name
from ..utils import import_installed
pywbem = import_installed('pywbem')
from pywbem import Statistics  # noqa: E402
# pylint: enable=wrong-import-position, wrong-import-order, invalid-name


@pytest.mark.xfail(
    reason="Statistics and OperationStatistic have reference cycle")
@yagot.garbage_checked()
def test_leaks_Statistics_minimal():
    """
    Test function with a minimal Statistics object.
    """
    _ = Statistics()
