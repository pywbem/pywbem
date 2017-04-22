#
# (C) Copyright 2017 InovaDevelopment Inc.
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
Pywbem supports measuring the elapsed times of the WBEM operations that
were performed in context of a connection, and maintaining a statistics
over these times.

This capability is disabled by default and can be enabled in either
of these ways:

* When creating a :class:`~pywbem.WBEMConnection` object, via its
  ``enable_stats`` argument.

* After the :class:`~pywbem.WBEMConnection` object has been created, by
  modifying its :attr:`~pywbem.WBEMConnection.stats_enabled` instance
  attribute.

The :class:`~pywbem.Statistics` class maintains statistics over the measured
elapsed times of the WBEM operations and is the interface for accessing the
statistics. The statistics of a :class:`~pywbem.WBEMConnection` object are
accessible via its :attr:`~pywbem.WBEMConnection.statistics` instance
attribute.

The :class:`~pywbem.OperationStatistic` class is a helper class that contains
the actual measurement data for one operation name.
There will be one :class:`~pywbem.OperationStatistic` object each operation
name (see the table of WBEMConnection methods in the :ref:`WBEM operations`
section for the operation names).
The :class:`~pywbem.OperationStatistic` objects are under control of the
:class:`~pywbem.Statistics` class.

**Experimental:** The statistics support is experimental for this release.
"""

from __future__ import absolute_import

import time
import copy

__all__ = ['Statistics', 'OperationStatistic']


class OperationStatistic(object):
    """
    A statistics data keeper for the executions of all operations with the
    same operation name.

    This class maintains max, min, avg and count for elapsed time, request
    size, and response size over the executed operations of a single
    operation name.

    Use the :meth:`pywbem.Statistics.start_timer` method to create objects
    of this class::

        stats = container.start_timer('EnumerateInstances')
        ...
        stats.stop_timer(request_len, reply_len, exc)

    **Experimental:** This class is experimental for this release.
    """

    def __init__(self, container, name):
        """
        Parameters:

          container (:class:`~pywbem.Statistics`):
            The statistics container that holds this operation statistic
            object.

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

        self._request_len_sum = float(0)
        self._request_len_min = float('inf')
        self._request_len_max = float(0)

        self._reply_len_sum = float(0)
        self._reply_len_min = float('inf')
        self._reply_len_max = float(0)

    @property
    def stat_start_time(self):
        """
        :class:`py:float`: Point in time when the first statistic was taken
        since this object was either created or reset, in seconds since the
        epoch (for details, see :func:`py:time.time`).
        """
        return self._stat_start_time

    @property
    def name(self):
        """
        :term:`string`: Name of the operation for which this statistics
        object maintains data.

        This name is used by the :class:`~pywbem.Statistics` object
        holding this time statistics as a key.
        """
        return self._name

    @property
    def container(self):
        """
        :class:`~pywbem.Statistics`: The statistics container that holds
        this statistics object.
        """
        return self._container

    @property
    def count(self):
        """
        :term:`integer`: The number of measured operations (that is,
        invocations of the :meth:`~pywbem.OperationStatistic.stop_timer`
        method).
        """
        return self._count

    @property
    def exception_count(self):
        """
        :term:`integer`: The number of exceptions that occurred when invoking
        the measured operations.
        """
        return self._exception_count

    @property
    def avg_time(self):
        """
        :class:`py:float`: The average elapsed time for invoking the measured
        operations, in seconds.
        """
        try:
            return self._time_sum / self._count
        except ZeroDivisionError:
            return 0

    @property
    def min_time(self):
        """
        :class:`py:float`: The minimum elapsed time for invoking the measured
        operations, in seconds.
        """
        return self._time_min

    @property
    def max_time(self):
        """
        :class:`py:float`: The maximum elapsed time for invoking the measured
        operations, in seconds.
        """
        return self._time_max

    @property
    def avg_request_len(self):
        """
        :class:`py:float`: The average size of the HTTP body in the CIM-XML
        requests of the invoked operations, in Bytes.
        """
        try:
            return self._request_len_sum / self._count
        except ZeroDivisionError:
            return 0.0

    @property
    def min_request_len(self):
        """
        :class:`py:float`: The minimum size of the HTTP body in the CIM-XML
        requests of the invoked operations, in Bytes.
        """
        return self._request_len_min

    @property
    def max_request_len(self):
        """
        :class:`py:float`: The maximum size of the HTTP body in the CIM-XML
        requests of the invoked operations, in Bytes.
        """
        return self._request_len_max

    @property
    def avg_reply_len(self):
        """
        :class:`py:float`: The average size of the HTTP body in the CIM-XML
        responses of the invoked operations, in Bytes.
        """
        try:
            return self._reply_len_sum / self._count
        except ZeroDivisionError:
            return 0.0

    @property
    def min_reply_len(self):
        """
        :class:`py:float`: The minimum size of the HTTP body in the CIM-XML
        responses of the invoked operations, in Bytes.
        """
        return self._reply_len_min

    @property
    def max_reply_len(self):
        """
        :class:`py:float`: The maximum size of the HTTP body in the CIM-XML
        responses of the invoked operations, in Bytes.
        """
        return self._reply_len_max

    def reset(self):
        """
        Reset the statistics data for this object.
        """
        self._count = 0
        self._exception_count = 0
        self._stat_start_time = None
        self._time_sum = float(0)
        self._time_min = float('inf')
        self._time_max = float(0)

        self._request_len_sum = float(0)
        self._request_len_min = float('inf')
        self._request_len_max = float(0)

        self._reply_len_sum = float(0)
        self._reply_len_min = float('inf')
        self._reply_len_max = float(0)

    def start_timer(self):
        """
        This method needs to be called at the begin of an operation that
        is intended to be measured. It starts the measurement for that
        operation (by capturing the current point in time), if the
        statistics container holding this object is enabled. Otherwise,
        this method does nothing.

        A subsequent invocation of :meth:`~pywbem.OperationStatistic.stop_timer`
        will complete the measurement for that operation and will update the
        statistics data.
        """
        if self.container.enabled:
            self._start_time = time.time()
            if not self._stat_start_time:
                self._stat_start_time = self._start_time

    def stop_timer(self, request_len, reply_len, exception=False):
        """
        This method needs to be called at the end of an operation that is
        intended to be measured. It completes the measurement for that
        operation by capturing the needed data, and updates the statistics
        data, if the statistics container holding this object is enabled.
        Otherwise, this method does nothing.

        Parameters:

          request_len (:term:`integer`)
            Size of the HTTP body of the CIM-XML request message, in Bytes.

          reply_len (:term:`integer`)
            Size of the HTTP body of the CIM-XML response message, in Bytes.

          exception (:class:`py:bool`)
            Boolean that specifies whether an exception was raised while
            processing the operation.

        Returns:

          float: The elapsed time for the operation that just ended, or
          `None` if the statistics container holding this object is not
          enabled.
        """
        if self.container.enabled:
            if self._start_time is None:
                raise RuntimeError('stop_timer() called without preceding '
                                   ' start_timer()')
            dt = time.time() - self._start_time
            self._start_time = None
            self._count += 1
            self._time_sum += dt
            self._request_len_sum += request_len
            self._reply_len_sum += reply_len

            if exception:
                self._exception_count += 1

            if dt > self._time_max:
                self._time_max = dt
            if dt < self._time_min:
                self._time_min = dt

            if request_len > self._request_len_max:
                self._request_len_max = request_len
            if request_len < self._request_len_min:
                self._request_len_min = request_len

            if reply_len > self._reply_len_max:
                self._reply_len_max = reply_len
            if reply_len < self._reply_len_min:
                self._reply_len_min = reply_len

            return dt
        else:
            return None

    def __repr__(self):
        """
        Return a human readable string with the statistics values, for debug
        purposes.
        """
        return 'OperationStatistic(' \
               'name={s.name!r}, ' \
               'count={s.count!r}, ' \
               'exception_count={s.exception_count!r}, ' \
               'avg_time={s.avg_time!r}, ' \
               'min_time={s.min_time!r}, ' \
               'max_time={s.max_time!r}, ' \
               'avg_request_len={s.avg_request_len!r}, ' \
               'min_request_len={s.min_request_len!r}, ' \
               'max_request_len={s.max_request_len!r}, ' \
               'avg_reply_len={s.avg_reply_len!r}, ' \
               'min_reply_len={s.min_reply_len!r}, ' \
               'max_reply_len={s.max_reply_len!r})'. \
               format(s=self)

    #: Formatted header string (two lines), for use with the formatted rows
    #: returned by the :meth:`~pywbem.OperationStatistic.formatted` method.
    #:
    #: For an example, see :meth:`pywbem.Statistics.formatted`.
    formatted_header = \
        'Count Excep    Time    Time    Time ReqLen ReqLen ReqLen ' \
        'ReplyLen ReplyLen ReplyLen Operation\n' \
        '        Cnt     Avg     Min     Max    Avg    Min    Max ' \
        '     Avg      Min      Max\n'

    def formatted(self):
        """
        Return a formatted one-line string with the statistics values for this
        operation.

        The returned string can be used with the formatted header string
        defined in :attr:`~pywbem.OperationStatistic.formatted_header`.

        For an example, see :meth:`pywbem.Statistics.formatted`.
        """
        return ('{0:5d} {1:5d} {2:7.3f} {3:7.3f} {4:7.3f} {5:6.0f} {6:6.0f} '
                '{7:6.0f} {8:8.0f} {9:8.0f} {10:8.0f} {11}\n'.
                format(self.count, self.exception_count,
                       self.avg_time, self.min_time, self.max_time,
                       self.avg_request_len, self.min_request_len,
                       self.max_request_len, self.avg_reply_len,
                       self.min_reply_len, self.max_reply_len,
                       self.name))


class Statistics(object):
    """
    A container class for multiple operation statistic objects (of class
    :class:`~pywbem.OperationStatistic`).

    Each operation statistic object is identified by a name, that is defined
    in the :meth:`~pywbem.Statistics.start_timer` method.

    The statistics container can be in a state of enabled or disabled.
    If enabled, it accumulates the elapsed times between subsequent calls to
    the :meth:`~pywbem.OperationStatistic.start_timer` and
    :meth:`~pywbem.OperationStatistic.stop_timer` methods of class
    :class:`~pywbem.OperationStatistic`.
    If disabled, calls to these methods do not accumulate any time.
    Initially, the statistics container is disabled. Its enablement state can
    be controlled via the :meth:`~pywbem.Statistics.enable` and
    :meth:`~pywbem.Statistics.disable` methods. Its current enablement
    state can be accessed via the :attr:`~pywbem.Statistics.enabled`
    property.

    **Experimental:** This class is experimental for this release.
    """

    def __init__(self, enable=False):
        """
        Parameters:

          enable (:class:`py:bool`):
            Initial enablement status for this statistics container.
        """
        # We convert any non-boolean values to True/False:
        self._enabled = bool(enable)
        self._op_stats = {}
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
        Start the timer for a given operation name and return the corresponding
        :class:`~pywbem.OperationStatistic` object, creating one if needed.

        Parameters:

          name (string):
            Name of the operation.

        Returns:

          :class:`~pywbem.OperationStatistic`: The operation statistic for the
          specified name. If this statistics container is disabled, a dummy
          operation statistic object is returned.
        """
        op_stat = self.get_op_statistic(name)
        op_stat.start_timer()
        return op_stat

    def get_op_statistic(self, name):
        """
        Get the :class:`~pywbem.OperationStatistic` object for an operation
        name or create a new object if an object for that name does not exist.

        Parameters:

          name (string):
            Name of the operation.

        Returns:

          :class:`~pywbem.OperationStatistic`: The operation statistic for the
          specified operation name. If this statistics container is disabled,
          a dummy operation statistic object is returned.
        """
        if not self.enabled:
            return self._disabled_stats
        if name not in self._op_stats:
            self._op_stats[name] = OperationStatistic(self, name)
        return self._op_stats[name]

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
        return copy.deepcopy(self._op_stats).items()

    def __repr__(self):
        """
        Return a human readable display of the contents, for debug purposes.
        """
        ret = "Statistics(\n"
        for name in self._op_stats:
            ret += "  %r\n" % self._op_stats[name]
        ret += ")"
        return ret

    def formatted(self):
        # pylint: disable=line-too-long
        """
        Return a human readable string with the statistics for this container.
        The operations are sorted by decreasing average time.

        Example::

            Statistics (times in seconds, lengths in Bytes):
            Count  Exc    Time    Time    Time ReqLen ReqLen ReqLen ReplyLen ReplyLen ReplyLen Operation
                   Cnt    Avg     Min     Max    Avg    Min    Max      Avg      Min      Max
                3    0   0.234   0.100   0.401   1233   1000   1500    26667    20000    35000 EnumerateInstances
                1    0   0.100   0.100   0.100   1200   1200   1200    22000    22000    22000 EnumerateInstanceNames
        """  # noqa: E501
        # pylint: enable=line-too-long
        ret = "Statistics (times in seconds, lengths in Bytes):\n"
        if self.enabled:
            ret += OperationStatistic.formatted_header
            snapshot = sorted(self.snapshot(),
                              key=lambda item: item[1].avg_time,
                              reverse=True)
            for name, stats in snapshot:  # pylint: disable=unused-variable
                ret += stats.formatted()
        else:
            ret += "Disabled"
        return ret.strip()
