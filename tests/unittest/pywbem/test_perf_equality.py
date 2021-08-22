#!/usr/bin/env python

"""
Measure performance of equality tests.
"""

from __future__ import absolute_import

import io

import pytest
import six
try:
    # Python >= 3.4
    import statistics
except ImportError:
    from backports import statistics
try:
    # Python >= 3.3
    from time import process_time, get_clock_info
except ImportError:
    process_time = None

# pylint: disable=wrong-import-position, wrong-import-order, invalid-name
from tests.utils import import_installed
pywbem = import_installed('pywbem')
from pywbem import CIMInstanceName, CIMClass, CIMProperty, Uint8  # noqa: E402
# pylint: enable=wrong-import-position, wrong-import-order, invalid-name


TESTCASES_PERF_EQ = [

    # Testcases for performance tests for equality tests

    # Each list item is a testcase tuple with these items:
    # * desc: Short testcase description.
    # * obj1: Object #1 for equality test.
    # * obj2: Object #2 for equality test.
    (
        "CIMInstanceName with two keybindings, last one different",
        CIMInstanceName(
            'CIM_Foo',
            keybindings=dict(
                Chicken='Ham',
                Beans=Uint8(42),
            ),
        ),
        CIMInstanceName(
            'CIM_Foo',
            keybindings=dict(
                Chicken='Ham',
                Beans=Uint8(43),
            ),
        ),
    ),
    (
        "CIMClass with 10 properties, last one different",
        CIMClass(
            'CIM_Foo',
            properties=[
                CIMProperty('P1', 'V1', type='string'),
                CIMProperty('P2', 'V2', type='string'),
                CIMProperty('P3', 'V3', type='string'),
                CIMProperty('P4', 'V4', type='string'),
                CIMProperty('P5', 'V5', type='string'),
                CIMProperty('P6', 'V6', type='string'),
                CIMProperty('P7', 'V7', type='string'),
                CIMProperty('P8', 'V8', type='string'),
                CIMProperty('P9', 'V9', type='string'),
                CIMProperty('P10', 'V10', type='string'),
            ],
        ),
        CIMClass(
            'CIM_Foo',
            properties=[
                CIMProperty('P1', 'V1', type='string'),
                CIMProperty('P2', 'V2', type='string'),
                CIMProperty('P3', 'V3', type='string'),
                CIMProperty('P4', 'V4', type='string'),
                CIMProperty('P5', 'V5', type='string'),
                CIMProperty('P6', 'V6', type='string'),
                CIMProperty('P7', 'V7', type='string'),
                CIMProperty('P8', 'V8', type='string'),
                CIMProperty('P9', 'V9', type='string'),
                CIMProperty('P10', 'V10x', type='string'),
            ],
        ),
    ),
]


@pytest.mark.parametrize(
    "desc, obj1, obj2",
    TESTCASES_PERF_EQ)
def test_perf_eq(desc, obj1, obj2):
    """
    Measure performance of equality tests.
    """

    if not process_time:
        pytest.skip("Performance test must be run on Python 3.3 or higher")

    outfile = 'perf_equality.log'
    precision = 0.01  # Desired precision of measured time
    num = 10  # Repetitions for neglecting function overhead

    def measure():
        "One measurement"
        for _ in six.moves.range(num):
            # The code to be measured
            _ = (obj1 == obj2)

    t_us, stdev_us, num_runs, num_out = timeit(measure, precision)

    # Scale back to the code to be measured
    t_us /= num
    stdev_us /= num

    stdev_pct = 100.0 * stdev_us / t_us if t_us != 0 else 0.0

    with io.open(outfile, 'a', encoding='utf-8') as fp:
        fp.write("{}: {:.3f} us (std.dev. {:.1f}% in {} runs with {} "
                 "outliers)\n".
                 format(desc, t_us, stdev_pct, num_runs, num_out))


def timeit(measure_func, precision):
    """
    Measure the process time for measure_func with the desired precision, and
    return a tuple(mean_us, stdev_us, num_runs, num_out).
    """

    num_runs = 100  # Number of measurements to eliminate outliers
    min_rep = 5  # Minimum number of repetitions

    res_s = get_clock_info('process_time').resolution

    # Determine number of repetitions needed based on desired precision and
    # given timer resolution
    t1_s = process_time()
    measure_func()
    t2_s = process_time()
    t_s = t2_s - t1_s
    rep = max(int(float(res_s) / t_s / precision), min_rep) \
        if t_s != 0 else min_rep

    # Perform the measurement a number of times and store the results
    results = []
    for _ in six.moves.range(num_runs):
        t1_s = process_time()
        for _j in six.moves.range(rep):  # pylint: disable=unused-variable
            measure_func()
        t2_s = process_time()
        t_us = 1.0E6 * (t2_s - t1_s) / rep
        results.append(t_us)

    # Eliminate upper outliers in the results. Even though we measure process
    # time, it includes any activities done by the Python process outside of
    # our actual measured code.
    mean = statistics.mean(results)
    stdev = statistics.stdev(results)
    cleaned_results = []
    outliers = []
    for x in results:
        if x < mean + 1 * stdev:
            cleaned_results.append(x)
        else:
            outliers.append(x)
    num_out = len(outliers)

    # Calculate mean and standard deviation from cleaned results
    mean_us = statistics.mean(cleaned_results)
    stdev_us = statistics.stdev(cleaned_results)

    return mean_us, stdev_us, num_runs, num_out
