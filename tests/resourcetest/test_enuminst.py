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

    print("\nResource consumption test: EnumerateInstances with "
          "num_props={}, num_insts={}:".format(num_props, num_insts))

    with ResourceMeasurement() as rm:
        result = conn.EnumerateInstances(cls.classname)

    result_size = total_sizeof(result)

    print("  Elapsed time: {:>12} ms".
          format("{:.3f}".format(rm.elapsed_time_ms)))
    print("  CPU time:     {:>12} ms".format("{:.3f}".format(rm.cpu_time_ms)))
    print("  Peak usage:   {:>12} B".format(rm.peak_size))
    print("  Result size:  {:>12} B".format(result_size))


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

    print("\nResource consumption test: EnumerateInstanceNames with "
          "num_props={}, num_insts={}:".format(num_props, num_insts))

    with ResourceMeasurement() as rm:
        result = conn.EnumerateInstanceNames(cls.classname)

    result_size = total_sizeof(result)

    print("  Elapsed time: {:>12} ms".
          format("{:.3f}".format(rm.elapsed_time_ms)))
    print("  CPU time:     {:>12} ms".format("{:.3f}".format(rm.cpu_time_ms)))
    print("  Peak usage:   {:>12} B".format(rm.peak_size))
    print("  Result size:  {:>12} B".format(result_size))
