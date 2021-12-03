#!/usr/bin/env python

"""
Tests for statistics (`_statistics` in pywbem module).
"""

from __future__ import absolute_import, print_function

import re
import time
import pytest

from ..utils.pytest_extensions import simplified_test_function

# pylint: disable=wrong-import-position, wrong-import-order, invalid-name
from ...utils import import_installed
pywbem = import_installed('pywbem')
from pywbem import Statistics  # noqa: E402
# pylint: enable=wrong-import-position, wrong-import-order, invalid-name


@pytest.fixture(params=[
    True,
    False,
], scope='module')
def statistics_enable(request):
    """
    Possible values for Statistics(enable).
    """
    return request.param


def time_abs_delta(t1, t2):
    """
    Return the positive difference between two float values.
    """
    return abs(t1 - t2)


TESTCASES_STATISTICS_INIT = [

    # Testcases for Statistics.__init__()

    # Each list item is a testcase tuple with these items:
    # * desc: Short testcase description.
    # * kwargs: Keyword arguments for the test function:
    #   * init_args: Tuple of positional arguments to CIMInstanceName().
    #   * init_kwargs: Dict of keyword arguments to CIMInstanceName().
    #   * exp_attrs: Dict of expected attributes of resulting object.
    # * exp_exc_types: Expected exception type(s), or None.
    # * exp_warn_types: Expected warning type(s), or None.
    # * condition: Boolean condition for testcase to run, or 'pdb' for debugger

    (
        "Verify default arguments",
        dict(
            init_args=[],
            init_kwargs={},
            exp_attrs=dict(
                enabled=False,
            ),
        ),
        None, None, True
    ),
    (
        "Verify order of positional arguments",
        dict(
            init_args=[
                True,
            ],
            init_kwargs={},
            exp_attrs=dict(
                enabled=True,
            ),
        ),
        None, None, True
    ),
    (
        "Verify names of arguments",
        dict(
            init_args=[],
            init_kwargs=dict(
                enable=True,
            ),
            exp_attrs=dict(
                enabled=True,
            ),
        ),
        None, None, True
    ),

]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_STATISTICS_INIT)
@simplified_test_function
def test_Statistics_init(testcase, init_args, init_kwargs, exp_attrs):
    """
    Test function for Statistics.__init__()
    """

    # The code to be tested
    statistics = Statistics(*init_args, **init_kwargs)

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None

    exp_enabled = exp_attrs['enabled']
    assert statistics.enabled == exp_enabled
    assert isinstance(statistics.enabled, type(exp_enabled))


def test_Statistics_enable(statistics_enable):
    # pylint: disable=redefined-outer-name
    """
    Test function for Statistics.enable()
    """

    statistics = Statistics(enable=statistics_enable)

    # The code to be tested
    statistics.enable()

    assert statistics.enabled is True


def test_Statistics_disable(statistics_enable):
    # pylint: disable=redefined-outer-name
    """
    Test function for Statistics.disable()
    """

    statistics = Statistics(enable=statistics_enable)

    # The code to be tested
    statistics.disable()

    assert statistics.enabled is False


TESTCASES_STATISTICS_GET_OP_STATISTIC = [

    # Testcases for Statistics.get_op_statistic()

    # Each list item is a testcase tuple with these items:
    # * desc: Short testcase description.
    # * kwargs: Keyword arguments for the test function:
    #   * init_args: Tuple of positional arguments to CIMInstanceName().
    #   * init_kwargs: Dict of keyword arguments to CIMInstanceName().
    #   * exp_attrs: Dict of expected attributes of resulting object.
    # * exp_exc_types: Expected exception type(s), or None.
    # * exp_warn_types: Expected warning type(s), or None.
    # * condition: Boolean condition for testcase to run, or 'pdb' for debugger

    (
        "Verify initial stats and snapshot for disabled statistics",
        dict(
            init_enable=False,
            method_name='EnumerateInstances',
            exp_snapshot_len=0,
            exp_op_stats_attrs=dict(
                name='disabled',
                count=0,
                avg_time=0,
                min_time=float('inf'),
                max_time=0,
                avg_request_len=0,
                min_request_len=float('inf'),
                max_request_len=0,
            ),
        ),
        None, None, True
    ),
    (
        "Verify initial stats and snapshot for enabled statistics",
        dict(
            init_enable=True,
            method_name='EnumerateInstances',
            exp_snapshot_len=1,
            exp_op_stats_attrs=dict(
                name='EnumerateInstances',
                count=0,
                avg_time=0,
                min_time=float('inf'),
                max_time=0,
                avg_request_len=0,
                min_request_len=float('inf'),
                max_request_len=0,
            ),
        ),
        None, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_STATISTICS_GET_OP_STATISTIC)
@simplified_test_function
def test_Statistics_get_op_statistic(
        testcase, init_enable, method_name, exp_snapshot_len,
        exp_op_stats_attrs):
    # pylint: disable=unused-argument
    """
    Test function for Statistics.get_op_statistic()
    """

    statistics = Statistics(enable=init_enable)

    # The code to be tested
    op_stats = statistics.get_op_statistic(method_name)

    snapshot_length = len(statistics.snapshot())
    assert snapshot_length == exp_snapshot_len

    for attr_name in exp_op_stats_attrs:
        exp_attr_value = exp_op_stats_attrs[attr_name]
        attr_value = getattr(op_stats, attr_name)
        assert attr_value == exp_attr_value, \
            "Unexpected op_stats attribute '{}'".format(attr_name)


def test_Statistics_measure_enabled():
    """
    Test measuring time with enabled statistics.
    """

    statistics = Statistics()
    statistics.enable()

    duration = 1.0

    # Allowable delta in seconds between expected and actual duration.
    # Notes:
    # * Windows has only a precision of 1/60 sec.
    # * In CI environments, the tests sometimes run slow.
    delta = 0.5

    stats = statistics.start_timer('EnumerateInstances')
    time.sleep(duration)
    stats.stop_timer(100, 200)

    for _, stats in statistics.snapshot():
        assert stats.count == 1
        assert time_abs_delta(stats.avg_time, duration) < delta
        assert time_abs_delta(stats.min_time, duration) < delta
        assert time_abs_delta(stats.max_time, duration) < delta
        assert stats.max_request_len == 100
        assert stats.min_request_len == 100
        assert stats.avg_request_len == 100
        assert stats.max_reply_len == 200
        assert stats.min_reply_len == 200
        assert stats.avg_reply_len == 200

    stats.reset()
    assert stats.count == 0
    assert stats.avg_time == 0
    assert stats.min_time == float('inf')
    assert stats.max_time == 0


def test_Statistics_measure_disabled_cm():
    """
    Test measuring time with disabled statistics, via context manager.
    """

    statistics = Statistics()

    duration = 0.1

    with statistics('EnumerateInstances'):
        time.sleep(duration)

    stats_list = statistics.snapshot()
    assert len(stats_list) == 0


def test_Statistics_measure_enabled_cm():
    """
    Test measuring time with enabled statistics, via context manager.
    """

    statistics = Statistics()
    statistics.enable()

    duration = 0.1

    with statistics('EnumerateInstances'):
        time.sleep(duration)

    stats_dict = dict(statistics.snapshot())
    assert len(stats_dict) == 1

    assert 'EnumerateInstances' in stats_dict
    stats = stats_dict['EnumerateInstances']
    assert stats.count == 1


def test_Statistics_measure_enabled_nested_cm():
    """
    Test measuring time with enabled statistics, via nested context managers.
    """

    statistics = Statistics()
    statistics.enable()

    duration = 0.1
    inner_count = 3

    with statistics('compile_schema_classes'):
        for _ in range(0, inner_count):
            with statistics('compile_mof_string'):
                time.sleep(duration)

    stats_dict = dict(statistics.snapshot())
    assert len(stats_dict) == 2

    assert 'compile_schema_classes' in stats_dict
    stats = stats_dict['compile_schema_classes']
    assert stats.count == 1

    assert 'compile_mof_string' in stats_dict
    stats = stats_dict['compile_mof_string']
    assert stats.count == inner_count


def test_Statistics_measure_enabled_with_servertime():
    # pylint: disable=invalid-name
    """
    Test measuring time with enabled statistics.
    """

    statistics = Statistics()
    statistics.enable()

    duration = 1.0

    # Allowable delta in seconds between expected and actual duration.
    # Notes:
    # * Windows has only a precision of 1/60 sec.
    # * In CI environments, the tests sometimes run slow.
    delta = 0.5

    stats = statistics.start_timer('EnumerateInstances')
    time.sleep(duration)
    stats.stop_timer(1000, 2000, duration)

    for _, stats in statistics.snapshot():
        assert stats.count == 1
        assert time_abs_delta(stats.avg_time, duration) <= delta
        assert time_abs_delta(stats.min_time, duration) <= delta
        assert time_abs_delta(stats.max_time, duration) <= delta

        assert time_abs_delta(stats.avg_server_time, duration) <= delta
        assert time_abs_delta(stats.min_server_time, duration) <= delta
        assert time_abs_delta(stats.max_server_time, duration) <= delta

        assert stats.max_request_len == 1000
        assert stats.min_request_len == 1000
        assert stats.avg_request_len == 1000
        assert stats.max_reply_len == 2000
        assert stats.min_reply_len == 2000
        assert stats.avg_reply_len == 2000

    stats.reset()
    assert stats.count == 0
    assert stats.avg_time == 0
    assert stats.min_time == float('inf')
    assert stats.max_time == 0


def test_Statistics_measure_disabled():
    """
    Test measuring time with disabled statistics.
    """

    statistics = Statistics()

    duration = 0.2

    stats = statistics.get_op_statistic('GetClass')
    assert stats.name == 'disabled'

    stats.start_timer()
    time.sleep(duration)
    stats.stop_timer(100, 200)

    for _, stats in statistics.snapshot():
        assert stats.count == 0
        assert stats.avg_time == 0
        assert stats.min_time == float('inf')
        assert stats.max_time == 0


def test_Statistics_measure_avg():
    """
    Test measuring time with enabled statistics.
    """

    statistics = Statistics()
    statistics.enable()

    duration = 1.0

    # Allowable delta in seconds between expected and actual duration.
    # Notes:
    # * Windows has only a precision of 1/60 sec.
    # * In CI environments, the tests sometimes run slow.
    delta = 0.8

    stats = statistics.start_timer('EnumerateInstances')
    time.sleep(duration)
    stats.stop_timer(100, 200)

    stats = statistics.start_timer('EnumerateInstances')
    time.sleep(duration)
    stats.stop_timer(200, 400)

    for _, stats in statistics.snapshot():
        assert stats.count == 2
        assert time_abs_delta(stats.avg_time, duration) < delta
        assert time_abs_delta(stats.min_time, duration) < delta
        assert time_abs_delta(stats.max_time, duration) < delta
        assert stats.max_request_len == 200
        assert stats.min_request_len == 100
        assert stats.avg_request_len == 150
        assert stats.max_reply_len == 400
        assert stats.min_reply_len == 200
        assert stats.avg_reply_len == 300


def test_Statistics_measure_exception():
    """
    Test measuring time with enabled statistics.
    """

    statistics = Statistics()
    statistics.enable()

    duration = 1.0

    # Allowable delta in seconds between expected and actual duration.
    # Notes:
    # * Windows has only a precision of 1/60 sec.
    # * In CI environments, the tests sometimes run slow.
    delta = 0.5

    stats = statistics.start_timer('EnumerateInstances')
    time.sleep(duration)
    stats.stop_timer(100, 200)

    stats = statistics.start_timer('EnumerateInstances')
    time.sleep(duration)
    stats.stop_timer(200, 400)

    for _, stats in statistics.snapshot():
        assert stats.count == 2
        assert time_abs_delta(stats.avg_time, duration) < delta
        assert time_abs_delta(stats.min_time, duration) < delta
        assert time_abs_delta(stats.max_time, duration) < delta
        assert stats.max_request_len == 200
        assert stats.min_request_len == 100
        assert stats.avg_request_len == 150
        assert stats.max_reply_len == 400
        assert stats.min_reply_len == 200
        assert stats.avg_reply_len == 300


def test_Statistics_snapshot():
    """
    Test that snapshot() takes a stable snapshot.
    """

    statistics = Statistics()
    statistics.enable()

    duration = 1.0

    # Allowable delta in seconds between expected and actual duration.
    # Notes:
    # * Windows has only a precision of 1/60 sec.
    # * In CI environments, the tests sometimes run slow.
    delta = 0.5

    stats = statistics.start_timer('GetInstance')
    time.sleep(duration)
    stats.stop_timer(100, 200)

    # take the snapshot
    snapshot = statistics.snapshot()

    # keep producing statistics data
    stats.start_timer()
    time.sleep(duration)
    stats.stop_timer(100, 200)

    # verify that only the first set of data is in the snapshot
    for _, stats in snapshot:
        assert stats.count == 1
        assert time_abs_delta(stats.avg_time, duration) < delta
        assert time_abs_delta(stats.min_time, duration) < delta
        assert time_abs_delta(stats.max_time, duration) < delta


def test_Statistics_reset():
    """
    Test resetting statistics.
    """

    statistics = Statistics()
    statistics.enable()

    duration = 1.0

    # Allowable delta in seconds between expected and actual duration.
    # Notes:
    # * Windows has only a precision of 1/60 sec.
    # * In CI environments, the tests sometimes run slow.
    delta = 0.5

    stats = statistics.start_timer('GetInstance')
    # test reset fails because stat in process
    assert statistics.reset() is False
    time.sleep(duration)
    stats.stop_timer(100, 200)

    # take a snapshot
    snapshot = statistics.snapshot()

    # verify that only the first set of data is in the snapshot
    for _, stats in snapshot:
        assert stats.count == 1
        assert time_abs_delta(stats.avg_time, duration) < delta
        assert time_abs_delta(stats.min_time, duration) < delta
        assert time_abs_delta(stats.max_time, duration) < delta

    assert statistics.reset() is True

    # take another snapshot. This snapshot should be empty
    snapshot = statistics.snapshot()
    assert not snapshot


def test_Statistics_server_time_suspension():
    """
    Test suspending server time and resetting.

    Server time suspension occurs at the level of operations (i.e.
    OperationStatistics object) if not all executions of the operation return
    the server response time. Once it has occurred, the server time values
    are reset and this condition is remembered until the OperationStatistics
    object's reset() is called (which normally is not used and not tested here)
    or the parent Statistic object's reset() is called.
    """

    statistics = Statistics()
    statistics.enable()

    duration = 1.0
    server_resp_time = 0.8

    # Allowable delta in seconds between expected and actual duration.
    # Notes:
    # * Windows has only a precision of 1/60 sec.
    # * In CI environments, the tests sometimes run slow.
    delta = 0.5

    stats = statistics.start_timer('GetInstance')
    time.sleep(duration)
    stats.stop_timer(100, 200, server_resp_time)

    # verify server time after server response time was provided
    snapshot = statistics.snapshot()
    for _, stats in snapshot:
        assert stats.count == 1
        assert time_abs_delta(stats.avg_time, duration) < delta
        assert time_abs_delta(stats.min_time, duration) < delta
        assert time_abs_delta(stats.max_time, duration) < delta
        assert time_abs_delta(stats.avg_server_time, server_resp_time) < delta
        assert time_abs_delta(stats.min_server_time, server_resp_time) < delta
        assert time_abs_delta(stats.max_server_time, server_resp_time) < delta

    stats = statistics.start_timer('GetInstance')
    time.sleep(duration)
    stats.stop_timer(120, 250, None)

    # verify server time (and only that) is suspended when server response
    # time was not provided
    snapshot = statistics.snapshot()
    for _, stats in snapshot:
        assert stats.count == 2
        assert time_abs_delta(stats.avg_time, duration) < delta
        assert time_abs_delta(stats.min_time, duration) < delta
        assert time_abs_delta(stats.max_time, duration) < delta
        assert stats.avg_server_time == float(0)
        assert stats.min_server_time == float('inf')
        assert stats.max_server_time == float(0)

    stats = statistics.start_timer('GetInstance')
    time.sleep(duration)
    stats.stop_timer(120, 250, server_resp_time)

    # verify that server time suspension is sticky once it occurred, even if
    # server response time is provided again
    snapshot = statistics.snapshot()
    for _, stats in snapshot:
        assert stats.count == 3
        assert time_abs_delta(stats.avg_time, duration) < delta
        assert time_abs_delta(stats.min_time, duration) < delta
        assert time_abs_delta(stats.max_time, duration) < delta
        assert stats.avg_server_time == float(0)
        assert stats.min_server_time == float('inf')
        assert stats.max_server_time == float(0)

    assert statistics.reset() is True

    stats = statistics.start_timer('GetInstance')
    time.sleep(duration)
    stats.stop_timer(100, 200, server_resp_time)

    # verify that reset() also resets server time suspension
    snapshot = statistics.snapshot()
    for _, stats in snapshot:
        assert stats.count == 1
        assert time_abs_delta(stats.avg_time, duration) < delta
        assert time_abs_delta(stats.min_time, duration) < delta
        assert time_abs_delta(stats.max_time, duration) < delta
        assert time_abs_delta(stats.avg_server_time, server_resp_time) < delta
        assert time_abs_delta(stats.min_server_time, server_resp_time) < delta
        assert time_abs_delta(stats.max_server_time, server_resp_time) < delta


def test_Statistics_print_statistics():
    """
    Test repr() and formatted() for a small statistics.
    """

    statistics = Statistics()
    statistics.enable()

    stats = statistics.start_timer('EnumerateInstanceNames')
    time.sleep(0.1)
    stats.stop_timer(1200, 22000)

    stats = statistics.start_timer('EnumerateInstances')
    time.sleep(0.1)
    stats.stop_timer(1000, 20000)

    stats = statistics.start_timer('EnumerateInstances')
    time.sleep(0.2)
    stats.stop_timer(1500, 25000)

    stats = statistics.start_timer('EnumerateInstances')
    time.sleep(0.4)
    stats.stop_timer(1200, 35000)

    # test repr output
    stat_repr = repr(statistics)

    assert re.match(
        r'Statistics\(',
        stat_repr)

    assert re.search(
        r"OperationStatistic\(name='EnumerateInstanceNames', count=1,"
        r" exception_count=0, avg_time=[.0-9]+, min_time=[.0-9]+, "
        r"max_time=[.0-9]+, avg_server_time=0.0, min_server_time=inf, "
        r"max_server_time=0.0, avg_request_len=[.0-9]+, "
        r"min_request_len=[0-9]{4}, max_request_len=[0-9]{4}, "
        r"avg_reply_len=[.0-9]+, min_reply_len=[0-9]{5},"
        r" max_reply_len=[0-9]{5}",
        stat_repr)

    assert re.search(
        r"OperationStatistic\(name='EnumerateInstances', count=3, "
        r"exception_count=0, avg_time=[.0-9]+, min_time=[.0-9]+, "
        r"max_time=[.0-9]+, avg_server_time=0.0, min_server_time=inf, "
        r"max_server_time=0.0, avg_request_len=[.0-9]+, "
        r"min_request_len=[0-9]{4}, max_request_len=[0-9]{4}, "
        r"avg_reply_len=[.0-9]+, min_reply_len=[0-9]{5}, "
        r"max_reply_len=[0-9]{5}",
        stat_repr)

    # Test statistics report output

    report = statistics.formatted()

    assert re.match(
        r'Statistics',
        report)

    assert re.search(
        r"Count ExcCnt +Time \[s\] +RequestLen \[B\] +ReplyLen \[B\] "
        r"+Operation",
        report)

    assert re.search(
        r" +3 +0 +[.0-9]+ +[.0-9]+ +[.0-9]+ +"
        r"[.0-9]+ +[0-9]{4} +[0-9]{4} +"
        r"[.0-9]+ +[0-9]{5} +[0-9]{5} EnumerateInstances",
        report)

    assert re.search(
        r" +1 +0 +[.0-9]+ +[.0-9]+ +[.0-9]+ +"
        r"[.0-9]+ +[0-9]{4} +[0-9]{4} +"
        r"[.0-9]+ +[0-9]{5} +[0-9]{5} EnumerateInstanceNames",
        report)


def test_Statistics_print_stats_svrtime():
    """
    Test repr() and formatted() for a small statistics.
    """

    statistics = Statistics()
    statistics.enable()

    stats = statistics.start_timer('EnumerateInstanceNames')
    time.sleep(0.1)
    stats.stop_timer(1200, 22000, 0.1)

    stats = statistics.start_timer('EnumerateInstances')
    time.sleep(0.1)
    stats.stop_timer(1000, 20000, 0.1)

    stats = statistics.start_timer('EnumerateInstances')
    time.sleep(0.2)
    stats.stop_timer(1500, 25000, 0.2)

    stats = statistics.start_timer('EnumerateInstances')
    time.sleep(0.4)
    stats.stop_timer(1200, 35000, 0.4)

    # test repr output
    stat_repr = repr(statistics)

    # test repr output
    assert re.match(
        r'Statistics\(',
        stat_repr)

    assert re.search(
        r"OperationStatistic\(name='EnumerateInstanceNames', count=1,"
        r" exception_count=0, avg_time=[.0-9]+, min_time=[.0-9]+, "
        r"max_time=[.0-9]+, avg_server_time=[.0-9]+, "
        r"min_server_time=[.0-9]+, "
        r"max_server_time=[.0-9]+, avg_request_len=[.0-9]+, "
        r"min_request_len=[0-9]{4}, max_request_len=[0-9]{4}, "
        r"avg_reply_len=[.0-9]+, min_reply_len=[0-9]{5},"
        r" max_reply_len=[0-9]{5}",
        stat_repr)

    assert re.search(
        r"OperationStatistic\(name='EnumerateInstances', count=3, "
        r"exception_count=0, avg_time=[.0-9]+, min_time=[.0-9]+, "
        r"max_time=[.0-9]+, avg_server_time=[.0-9]+, "
        r"min_server_time=[.0-9]+, "
        r"max_server_time=[.0-9]+, avg_request_len=[.0-9]+, "
        r"min_request_len=[0-9]{4}, max_request_len=[0-9]{4}, "
        r"avg_reply_len=[.0-9]+, min_reply_len=[0-9]{5}, "
        r"max_reply_len=[0-9]{5}",
        stat_repr)

    assert re.search(
        r"OperationStatistic\(name='EnumerateInstances', count=3, "
        r"exception_count=0, avg_time=.+min_time=.+max_time=.+"
        r"avg_server_time=.+min_server_time.+max_server_time=.+"
        r"max_reply_len=[0-9]{5}",
        stat_repr)

    assert re.search(
        r"OperationStatistic\(name='EnumerateInstanceNames', count=1, "
        r"exception_count=0, avg_time=[.0-9]+, min_time=[.0-9]+, "
        r"max_time=[.0-9]+, avg_server_time=[.0-9]+, min_server_time="
        r"[.0-9]+.+max_server_time=[.0-9]+, avg_request_len=[.0-9]+"
        r".+max_reply_len=[0-9]{5}",
        stat_repr)

    # test formatted output

    report = statistics.formatted()

    assert re.search(
        r'Count ExcCnt +Time \[s\] +ServerTime \[s\] +RequestLen \[B\] '
        r'+ReplyLen \[B\] +Operation',
        report)

    assert re.search(
        r' +Avg +Min +Max +Avg +Min +Max +Avg +Min +Max',
        report)

    assert re.search(
        r"3     0 +[.0-9]+ +[.0-9]+ +[.0-9]+ +[.0-9]+ +[.0-9]+ +[.0-9]+ +"
        r"[0-9]+ +[0-9]+ +[0-9]+ +[0-9]+ +[0-9]+ +[0-9]{5} "
        r"EnumerateInstances",
        report)

    assert re.search(
        r"1     0 +[.0-9]+ +[.0-9]+ +[.0-9]+ +[.0-9]+ +[.0-9]+ +[.0-9]+ +"
        r"[0-9]+ +[0-9]+ +[0-9]+ +[0-9]+ +[0-9]+ +[0-9]{5} "
        r"EnumerateInstanceNames",
        report)
