"""
Resource consumption tests for mocked EnumerateInstances and
EnumerateInstanceNames operations.
"""

import pytest

from .random_objects import tst_random_conn
from .memory_utils import total_sizeof
from .resource_measurement import ResourceMeasurement


@pytest.mark.parametrize(
    "num_props, num_insts", [
        (1, 1),
        (10, 100),
    ]
)
def test_enuminst_mock(num_props, num_insts):
    """
    Resource consumption test for EnumerateInstances operation against
    a mock environment.
    """

    conn, cls, _ = tst_random_conn(num_insts, num_props)

    print(f"\nResource consumption test: EnumerateInstances with "
          f"num_props={num_props}, num_insts={num_insts}:")

    with ResourceMeasurement() as rm:
        result = conn.EnumerateInstances(cls.classname)

    result_size = total_sizeof(result)

    print(f"  Elapsed time: {rm.elapsed_time_ms:>12.3f} ms")
    print(f"  CPU time:     {rm.cpu_time_ms:>12.3f} ms")
    print(f"  Peak usage:   {rm.peak_size:>12} B")
    print(f"  Result size:  {result_size:>12} B")


@pytest.mark.parametrize(
    "num_props, num_insts", [
        (1, 1),
        (10, 100),
    ]
)
def test_enuminstnames_mock(num_props, num_insts):
    """
    Resource consumption test for EnumerateInstanceNames operation against
    a mock environment.
    """

    conn, cls, _ = tst_random_conn(num_insts, num_props)

    print(f"\nResource consumption test: EnumerateInstanceNames with "
          f"num_props={num_props}, num_insts={num_insts}:")

    with ResourceMeasurement() as rm:
        result = conn.EnumerateInstanceNames(cls.classname)

    result_size = total_sizeof(result)

    print(f"  Elapsed time: {rm.elapsed_time_ms:>12.3f} ms")
    print(f"  CPU time:     {rm.cpu_time_ms:>12.3f} ms")
    print(f"  Peak usage:   {rm.peak_size:>12} B")
    print(f"  Result size:  {result_size:>12} B")
