#!/usr/bin/env python

"""
Tests for statistics (`_statistics` in pywbem module).
"""

from __future__ import absolute_import, print_function

import time
import unittest

from pywbem import Statistics


def time_abs_delta(t1, t2):
    """
    Return the positive difference between two float values.
    """
    return abs(t1 - t2)


class StatisticsTests(unittest.TestCase):
    """All tests for Statistics and TimeCapture."""

    def test_enabling(self):
        """Test enabling and disabling."""

        statistics = Statistics()

        self.assertFalse(statistics.enabled,
                         "Error: initial state is not disabled")

        statistics.disable()
        self.assertFalse(statistics.enabled,
                         "Error: disabling a disabled statistics works")

        statistics.enable()
        self.assertTrue(statistics.enabled,
                        "Error: enabling a disabled statistics works")

        statistics.enable()
        self.assertTrue(statistics.enabled,
                        "Error: enabling an enabled statistics works")

        statistics.disable()
        self.assertFalse(statistics.enabled,
                         "Errror: disabling an enabled statistics works")

    def test_get(self):
        """Test getting statistics."""

        statistics = Statistics()
        snapshot_length = len(statistics.snapshot())
        self.assertEqual(snapshot_length, 0,
                         "Error:  initial state has no time statistics. "
                         "Actual number = %d" % snapshot_length)

        stats = statistics.get_op_statistic('EnumerateInstances')
        snapshot_length = len(statistics.snapshot())
        self.assertEqual(snapshot_length, 0,
                         "Error: getting a new stats with a disabled "
                         "statistics results in no time statistics. "
                         "Actual number = %d" % snapshot_length)
        self.assertEqual(stats.container, statistics)
        self.assertEqual(stats.name, "disabled")
        self.assertEqual(stats.count, 0)
        self.assertEqual(stats.avg_time, 0)
        self.assertEqual(stats.min_time, float('inf'))
        self.assertEqual(stats.max_time, 0)

        self.assertEqual(stats.avg_request_len, 0)
        self.assertEqual(stats.min_request_len, float('inf'))
        self.assertEqual(stats.max_request_len, 0)

        statistics.enable()

        method_name = 'OpenEnumerateInstances'

        stats = statistics.get_op_statistic(method_name)
        snapshot_length = len(statistics.snapshot())
        self.assertEqual(snapshot_length, 1,
                         "Error: getting a new stats with an enabled "
                         "statistics results in one time statistics. "
                         "Actual number = %d" % snapshot_length)

        self.assertEqual(stats.container, statistics)
        self.assertEqual(stats.name, method_name)
        self.assertEqual(stats.count, 0)
        self.assertEqual(stats.avg_time, 0)
        self.assertEqual(stats.min_time, float('inf'))
        self.assertEqual(stats.max_time, 0)

        statistics.get_op_statistic(method_name)
        snapshot_length = len(statistics.snapshot())
        self.assertEqual(snapshot_length, 1,
                         "Error: getting an existing stats with an "
                         "enabled statistics results in the same number of "
                         "statistics. "
                         "Actual number = %d" % snapshot_length)

    def test_measure_enabled(self):
        """Test measuring time with enabled statistics."""

        statistics = Statistics()
        statistics.enable()

        duration = 0.4
        # On Windows has only a precision of 1/60 sec:
        delta = 0.04

        stats = statistics.start_timer('EnumerateInstances')
        time.sleep(duration)
        stats.stop_timer(100, 200)

        for _, stats in statistics.snapshot():
            self.assertEqual(stats.count, 1)
            self.assertTrue(time_abs_delta(stats.avg_time, duration) < delta)
            self.assertTrue(time_abs_delta(stats.min_time, duration) < delta)
            self.assertTrue(time_abs_delta(stats.max_time, duration) < delta)
            self.assertEqual(stats.max_request_len, 100)
            self.assertEqual(stats.min_request_len, 100)
            self.assertEqual(stats.avg_request_len, 100)
            self.assertEqual(stats.max_reply_len, 200)
            self.assertEqual(stats.min_reply_len, 200)
            self.assertEqual(stats.avg_reply_len, 200)

        stats.reset()
        self.assertEqual(stats.count, 0)
        self.assertEqual(stats.avg_time, 0)
        self.assertEqual(stats.min_time, float('inf'))
        self.assertEqual(stats.max_time, 0)

    def test_measure_enabled_with_servertime(self):
        # pylint: disable=invalid-name
        """Test measuring time with enabled statistics."""

        statistics = Statistics()
        statistics.enable()

        duration = 0.4
        # On Windows has only a precision of 1/60 sec:
        delta = 0.04

        stats = statistics.start_timer('EnumerateInstances')
        time.sleep(duration)
        stats.stop_timer(1000, 2000, duration)

        for _, stats in statistics.snapshot():
            self.assertEqual(stats.count, 1)
            self.assertTrue(time_abs_delta(stats.avg_time, duration) <= delta)
            self.assertTrue(time_abs_delta(stats.min_time, duration) <= delta)
            self.assertTrue(time_abs_delta(stats.max_time, duration) <= delta)

            self.assertTrue(
                time_abs_delta(stats.avg_server_time, duration) <= delta)
            self.assertTrue(
                time_abs_delta(stats.min_server_time, duration) <= delta)
            self.assertTrue(
                time_abs_delta(stats.max_server_time, duration) <= delta)

            self.assertEqual(stats.max_request_len, 1000)
            self.assertEqual(stats.min_request_len, 1000)
            self.assertEqual(stats.avg_request_len, 1000)
            self.assertEqual(stats.max_reply_len, 2000)
            self.assertEqual(stats.min_reply_len, 2000)
            self.assertEqual(stats.avg_reply_len, 2000)

        stats.reset()
        self.assertEqual(stats.count, 0)
        self.assertEqual(stats.avg_time, 0)
        self.assertEqual(stats.min_time, float('inf'))
        self.assertEqual(stats.max_time, 0)

    def test_measure_disabled(self):
        """Test measuring time with disabled statistics."""

        statistics = Statistics()

        duration = 0.2

        stats = statistics.get_op_statistic('GetClass')
        self.assertEqual(stats.name, 'disabled')

        stats.start_timer()
        time.sleep(duration)
        stats.stop_timer(100, 200)

        for _, stats in statistics.snapshot():
            self.assertEqual(stats.count, 0)
            self.assertEqual(stats.avg_time, 0)
            self.assertEqual(stats.min_time, float('inf'))
            self.assertEqual(stats.max_time, 0)

    def test_measure_avg(self):
        """Test measuring time with enabled statistics."""

        statistics = Statistics()
        statistics.enable()

        duration = 0.4
        # On Windows has only a precision of 1/60 sec:
        delta = 0.04

        stats = statistics.start_timer('EnumerateInstances')
        time.sleep(duration)
        stats.stop_timer(100, 200)

        stats = statistics.start_timer('EnumerateInstances')
        time.sleep(duration)
        stats.stop_timer(200, 400)

        for _, stats in statistics.snapshot():
            self.assertEqual(stats.count, 2)
            self.assertTrue(time_abs_delta(stats.avg_time, duration) < delta)
            self.assertTrue(time_abs_delta(stats.min_time, duration) < delta)
            self.assertTrue(time_abs_delta(stats.max_time, duration) < delta)
            self.assertEqual(stats.max_request_len, 200)
            self.assertEqual(stats.min_request_len, 100)
            self.assertEqual(stats.avg_request_len, 150)
            self.assertEqual(stats.max_reply_len, 400)
            self.assertEqual(stats.min_reply_len, 200)
            self.assertEqual(stats.avg_reply_len, 300)

    def test_measure_exception(self):
        """Test measuring time with enabled statistics."""

        statistics = Statistics()
        statistics.enable()

        duration = 0.4
        # On Windows has only a precision of 1/60 sec:
        delta = 0.04

        stats = statistics.start_timer('EnumerateInstances')
        time.sleep(duration)
        stats.stop_timer(100, 200)

        stats = statistics.start_timer('EnumerateInstances')
        time.sleep(duration)
        stats.stop_timer(200, 400)

        for _, stats in statistics.snapshot():
            self.assertEqual(stats.count, 2)
            self.assertTrue(time_abs_delta(stats.avg_time, duration) < delta)
            self.assertTrue(time_abs_delta(stats.min_time, duration) < delta)
            self.assertTrue(time_abs_delta(stats.max_time, duration) < delta)
            self.assertEqual(stats.max_request_len, 200)
            self.assertEqual(stats.min_request_len, 100)
            self.assertEqual(stats.avg_request_len, 150)
            self.assertEqual(stats.max_reply_len, 400)
            self.assertEqual(stats.min_reply_len, 200)
            self.assertEqual(stats.avg_reply_len, 300)

    def test_snapshot(self):
        """Test that snapshot() takes a stable snapshot."""

        statistics = Statistics()
        statistics.enable()

        duration = 0.4
        # On Windows has only a precision of 1/60 sec:
        delta = 0.04

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
            self.assertEqual(stats.count, 1)
            self.assertTrue(time_abs_delta(stats.avg_time, duration) < delta)
            self.assertTrue(time_abs_delta(stats.min_time, duration) < delta)
            self.assertTrue(time_abs_delta(stats.max_time, duration) < delta)

    def test_print_statistics(self):  # pylint: disable=no-self-use
        """Simply print repr() and formatted() for a small statistics."""

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

        print("\n\nTest print of repr() for a small statistics No svr time:")
        print("================")
        print(repr(statistics))
        print("================")
        print("\nTest print of formatted() for the same statistics:")
        print("================")
        print(statistics.formatted())
        print("================")

    def test_print_stats_svrtime(self):  # pylint: disable=no-self-use
        """Simply print repr() and formatted() for a small statistics."""

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

        print("\n\nTest print of repr() for a small statisticsW server time:")
        print("================")
        print(repr(statistics))
        print("================")
        print("\nTest print of formatted() for the same statistics:")
        print("================")
        print(statistics.formatted())
        print("================")


if __name__ == '__main__':
    unittest.main()
