#!/usr/bin/env python
#
# (C) Copyright 2003-2007 Hewlett-Packard Development Company, L.P.
# (C) Copyright 2006-2007 Novell, Inc.
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

"""
The :class:`~pywbem.Statistics` class allows measuring the elapsed
time and request/reply length of WBEM Operations and keeping statistics on the
measured times

It consists of two classes:

The :class:`~pywbem.OperationStatistic` class is a helper class that contains
the actual measurement data for all invocations of a particular name. Its
objects are under control of the :class:`~pywbem.Statistics` class.
This class should be used independently.  Use the start_timer in the
Statistics class to both start a timer and if it does not exist, create
a new named statistic  category.

The :class:`~pywbem.Statistics` class maintins time statistics over
multiple separate named statistics gatherers (TimeStatistic class) and provides
tools for reporting these statistics

"""

from __future__ import absolute_import

import time
import copy

__all__ = ['Statistics']


class OperationStatistic(object):
    """
    Elapsed time information for all invocations of a particular named
    operation.

    This class maintains max, min, avg and count for a single named
    statistic for time, request length and reply length.

    Use :meth:`pywbem.Statistics.get_statistic` method  to
    create objects of this class.

    Ex:

        stats = container.start_timer('EnumerateInstances')
        ...
        stats.stop_timer(req_len, reply_len, exception=True)
    """
    display_col_hdr = \
        'Count  Time    Time    Time  Req     Req   Req   Reply     Reply ' \
        'Reply Exc Name\n' \
        '       Avg     Min     Max   Avg     Min   Max   Avg       Min ' \
        'Max   \n'

    def __init__(self, container, name):
        """
        Parameters:

          container (Statistics):
            The statistics container that holds this time statistics.

          name (string):
            Name of the operation.
        """
        self._container = container
        self._stat_start_time = None
        self._name = name
        self._count = 0
        self._exception_count = 0
        self._time_sum = float(0)
        self._time_min = float('inf')
        self._time_max = float(0)
        self._start_time = None

        self._req_len_sum = float(0)
        self._req_len_min = float('inf')
        self._req_len_max = float(0)

        self._reply_len_sum = float(0)
        self._reply_len_min = float('inf')
        self._reply_len_max = float(0)

    @property
    def stat_start_time(self):
        """
        :py:time: Time the first statistic was taken since this object
        was either created or reset.
        """
        return self._stat_start_time

    @property
    def name(self):
        """
        :term:`string`: Name for a sequence of time statistics that represents
        a single entitiy (ex. pywbem operation name)

        This name is used by the :class:`~pywbem.Statistics` object
        holding this time statistics as a key.
        """
        return self._name

    @property
    def container(self):
        """
        :class:`~pywbem.Statistics`: This time statistics container.
        """
        return self._container

    @property
    def count(self):
        """
        :term:`integer`: The number of invocations of the start_timer() and
        stop_timer()).
        """
        return self._count

    @property
    def avg_time(self):
        """
        float: The average elapsed time for invoking the operation, in seconds.
        """
        try:
            return self._time_sum / self._count
        except ZeroDivisionError:
            return 0

    @property
    def min_time(self):
        """
        float: The minimum elapsed time for invoking the operation, in seconds.
        """
        return self._time_min

    @property
    def max_time(self):
        """
        float: The maximum elapsed time for invoking the operation, in seconds.
        """
        return self._time_max

    @property
    def avg_req_len(self):
        """
        float: The average elapsed time for invoking the operation, in seconds.
        """
        try:
            return self._req_len_sum / self._count
        except ZeroDivisionError:
            return 0

    @property
    def min_req_len(self):
        """
        float: The minimum elapsed time for invoking the operation, in seconds.
        """
        return self._req_len_min

    @property
    def max_req_len(self):
        """
        float: The maximum elapsed time for invoking the operation, in seconds.
        """
        return self._req_len_max

    @property
    def avg_reply_len(self):
        """
        float: The average elapsed time for invoking the operation, in seconds.
        """
        try:
            return self._reply_len_sum / self._count
        except ZeroDivisionError:
            return 0

    @property
    def min_reply_len(self):
        """
        float: The minimum elapsed time for invoking the operation, in seconds.
        """
        return self._reply_len_min

    @property
    def max_reply_len(self):
        """
        float: The maximum elapsed time for invoking the operation, in seconds.
        """
        return self._reply_len_max

    @property
    def exception_count(self):
        """
            :py:time: Count of exceptions that occurred for named operation
        """
        return self._exception_count

    def reset(self):
        """
        Reset the statistics data.
        """
        self._count = 0
        self._exception_count = 0
        self._stat_start_time = None
        self._time_sum = float(0)
        self._time_min = float('inf')
        self._time_max = float(0)

        self._req_len_sum = float(0)
        self._req_len_min = float('inf')
        self._req_len_max = float(0)

        self._reply_len_sum = float(0)
        self._reply_len_min = float('inf')
        self._reply_len_max = float(0)

    def start_timer(self):
        """
        This method starts the timer for this OperationStatistic object if
        the container is enabled.

        A subsequent :meth:`~pywbem.OperationStatistic.stop_timer` computes the
        statistics for the time duration between the start and stop for this
        :meth:`~pywbem.OperationStatistic.

        If the statistics container holding this time statistics is disabled,
        this method does nothing.
        """
        if self.container.enabled:
            self._start_time = time.time()
            if not self._stat_start_time:
                self._stat_start_time = self._start_time

    def stop_timer(self, req_len, reply_len, exception=False):
        """
        This method is called at the completion of the timed event. It
        captures current time, computes the event duration since the
        corresponding :meth:`~pywbem.OperationStatistic.start_timer` and
        computes average, max, and min for the timedduration, request length,
        and response length if the container is enabled.

        Parameters:
          req_len (:term:`integer`)
            Integer value of the request length

          reply_len (:term:`integer`)
            Integer value of the reply length

          exception (:class:`py:bool`)
            If True, add one to the exception accumulator

        If the statistics container is disabled, this method does nothing.

        Returns the time for this operation or None if not recorded
        """
        if self.container.enabled:
            if self._start_time is None:
                raise RuntimeError('stop_timer() called without preceding '
                                   ' start_timer()')
            dt = time.time() - self._start_time
            self._start_time = None
            self._count += 1
            self._time_sum += dt
            self._req_len_sum += req_len
            self._reply_len_sum += reply_len

            if exception:
                self._exception_count += 1

            if dt > self._time_max:
                self._time_max = dt
            if dt < self._time_min:
                self._time_min = dt

            if req_len > self._req_len_max:
                self._req_len_max = req_len
            if req_len < self._req_len_min:
                self._req_len_min = req_len

            if reply_len > self._reply_len_max:
                self._reply_len_max = reply_len
            if reply_len < self._reply_len_min:
                self._reply_len_min = reply_len

            return dt
        else:
            return None

    def __str__(self):
        """
        Return a human readable string with the time statistics for this
        name.
        """
        return 'Operations Statistic: {} count={:d} AvgTime={:.3f}s ' \
               'MinTime={:.3f}s '\
               'MaxTime={:.3f}s exceptions={:d} ' \
               'AvgReq={:.3f}s MinReq={:.3f}s MaxReq={:.3f}s ' \
               'AvgReq={:.3f}s MinReq={:.3f}s MaxReq={:.3f}s'. \
               format(self.name,
                      self.count,
                      self.avg_time,
                      self.min_time,
                      self.max_time,

                      self.avg_req_len,
                      self.min_req_len,
                      self.max_req_len,

                      self.avg_reply_len,
                      self.min_reply_len,
                      self.max_reply_len,
                      self.exception_count)

    def formatted(self):
        """
        Returns a formatted OperationStatistic consistent with the display
        header.  The formatting must match the header formatting in

        """
        return ('{:5d}{:7.3f} {:7.3f} {:7.3f} {:5.1f} {:5d} {:5d} '
                '{:7.1f} {:7d} {:7d} {:5d} {}\n'.
                format(self.count, self.avg_time, self.min_time, self.max_time,
                       self.avg_req_len, self.min_req_len, self.max_req_len,
                       self.avg_reply_len, self.min_reply_len,
                       self.max_reply_len, self.exception_count, self.name))


class Statistics(object):
    """
    Statistics is a container for multiple statistics capture objects each
    defined by the :class:`~pywbem.OperationStatistic`).

    Each capture object is identified by a name defined in the start_timer
    method.

    The statistics container can be in a state of enabled or disabled.
    If enabled, it accumulates the elapsed times between subsequent calls to the
    :meth:`~pywbem.OperationStatistic.start_timer` and
     :meth:`~pywbem.OperationStatistic.stop_timer`
    methods of class :class:`~pywbem.OperationStatistic`.
    If disabled, calls to these methods do not accumulate any time.

    Initially, the statistics container is disabled.
    """

    def __init__(self, enabled=False):
        self._enabled = enabled
        self._time_stats = {}
        self._disabled_stats = OperationStatistic(self, "disabled")

    @property
    def enabled(self):
        """
        Indicates whether the statistics container is enabled.
        """
        return self._enabled

    def enable(self):
        """
        Enable the statistics container.
        """
        self._enabled = True

    def disable(self):
        """
        Disable the statistics container.
        """
        self._enabled = False

    def start_timer(self, name):
        """
        Start the timer for a defined timer name. If that  timer name does not
        exist, it is created in Statistics.

        Parameters:

          name (string):
            Name of the timer.

        Returns:

          OperationStatistic: The time statistics for the specified name. If
          the statistics container is disabled, a dummy time statistics object
          is returned.
        """
        named_statistic = self.get_named_statistic(name)
        named_statistic.start_timer()
        return named_statistic

    def get_named_statistic(self, name):
        """
        Get the OperationStatistic instance for a name or create a new
        OperationStatistic instance if that name does not exist

        Parameters:

          name (string):
            Name of the timer.

        Returns:

          OperationStatistic: The time statistics for the specified name. If
          the statistics container is disabled, a dummy time statistics object
          is returned.
        """
        if not self.enabled:
            return self._disabled_stats
        if name not in self._time_stats:
            self._time_stats[name] = OperationStatistic(self, name)
        return self._time_stats[name]

    def snapshot(self):
        """
        Return a snapshot of the time statistics of this container.

        The snapshot represents the statistics data at the time this method
        is called, and remains unchanged even if the statistics of this
        container continues to be updated.

        Returns:

          : A list of tuples (name, stats) with:

          - name (:term:`string`): Name of the operation
          - stats (:class:`~pywbem.OperationStatistic`): Time statistics for
            the operation
        """
        return copy.deepcopy(self._time_stats).items()

    def __str__(self):
        """ Return a human readable display of the contents"""
        for stat in self._time_stats:
            print(stat)

    def display(self):
        """
        Return a display formatted string with the time statistics for this
        container. The operations are sorted by decreasing average time.

        Note that this display is simplistic and assumes max size of the
        statistics for formatting.
        """
        ret = "Statistics (time in sec. Length in char. Exc: Exceptions):\n"
        if self.enabled:
            ret += OperationStatistic.display_col_hdr
            snapshot = sorted(self.snapshot(),
                              key=lambda item: item[1].avg_time,
                              reverse=True)
            for name, stats in snapshot:  # pylint: disable=unused-variable
                ret += stats.formatted()
        else:
            ret += "Disabled"
        return ret.strip()
