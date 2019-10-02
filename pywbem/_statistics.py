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

# pylint: disable=line-too-long
"""
*New in pywbem 0.11 as experimental and finalized in 0.12.*

Pywbem supports measuring the elapsed times of the WBEM operations that
were performed in context of a connection, and maintaining a statistics
over these times.

This capability is disabled by default and can be enabled in either
of these ways:

* When creating a :class:`~pywbem.WBEMConnection` object, via its
  ``stats_enabled`` argument.

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

The statistics support maintains two kinds of times for each kind of WBEM
operation:

* Client times: The elapsed times for the WBEMConnection operation methods from
  call to return. This is measured in pywbem pretty close to the API the pywbem
  user is calling.

* Server times: The elapsed times for processing the WBEM operations in the
  WBEM server from receiving the CIM-XML request message to sending back the
  CIM-XML response message. The server times are not measured by pywbem, but
  are taken from the `WBEMServerResponseTime` HTTP header field of a CIM-XML
  response, if present. See :term:`DSP0200` for a description of this header
  field.

  The `WBEMServerResponseTime` HTTP header field is optionally implemented
  by WBEM servers. The following WBEM servers are known to implement this
  header field:

  * OpenPegasus

The difference between client time and server time is the time spent in the
pywbem client, plus the time spent on the network between client and server.

The statistics support also maintains the size of the HTTP body in the CIM-XML
request and response messages, in Bytes.

These times and sizes are maintained as average, minimum and maximum values for
each kind of operation in a connection.

Finally, the statistics support maintains the total count of operations and the
count of operations that failed, for each kind of operation.

All data in the statistics applies to WBEM operations performed during periods
of time where the statistics are enabled on a connection. Operations performed
during periods of time where the statistics are disabled on a connection, are
simply ignored in the statistics.

For the Iter methods of WBEMConnection (e.g.
:meth:`~pywbem.WbemConnection.IterEnumerateInstances`), the WBEM operations
performed on behalf of them are subject of the statistics, but the Iter methods
themselves do not show up in the statistics.

The following example shows how statistics are enabled, and how statistics
values are accessed individually using the
:meth:`~pywbem.Statistics.get_op_statistic` method::

    conn = pywbem.WBEMConnection(..., stats_enabled=True)

    # Perform some operations on this connection
    insts_1 = conn.EnumerateInstances('CIM_Foo1', 'root/cimv2')
    insts_2 = conn.EnumerateInstances('CIM_Foo2', 'root/cimv2')
    insts_3 = conn.EnumerateInstances('CIM_Foo3', 'root/cimv2')
    inst_paths_1 = conn.EnumerateInstanceNames('CIM_Foo1', 'root/cimv2')

    # Access statistics values for EnumerateInstances
    ei_stats = conn.statistics.get_op_statistic('EnumerateInstances')
    ei_count = ei_stats.count
    ei_avg_client_time = ei_stats.avg_time
    ei_avg_server_time = ei_stats.avg_server_time

In the previous example, the values in ``ei_stats`` are "live", i.e. they
continue to be updated as operations are performed. If a snapshot is needed at
a certain point in time that remains unaffected by further operations, this can
be achieved using the :meth:`~pywbem.Statistics.snapshot` method::

    # Take snapshot and access statistics values for EnumerateInstances
    stats_snapshot = dict(conn.statistics.snapshot())
    ei_stats = stats_snapshot['EnumerateInstances']
    ei_count = ei_stats.count
    ei_avg_client_time = ei_stats.avg_time
    ei_avg_server_time = ei_stats.avg_server_time

It is also possible to simply print the current statistics of a connection as a
formatted table, using the :meth:`~pywbem.Statistics.formatted` method::

    # Print statistics values for all operations
    print(conn.statistics.formatted())

The output could look like this, if the WBEM server returns WBEM server
response times::

    Statistics (times in seconds, lengths in Bytes):
    Count Excep         ClientTime              ServerTime             RequestLen                ReplyLen       Operation
            Cnt     Avg     Min     Max     Avg     Min     Max    Avg    Min    Max      Avg      Min      Max
        3     0   0.234   0.100   0.401   0.204   0.080   0.361   1233   1000   1500    26667    20000    35000 EnumerateInstances
        1     0   0.100   0.100   0.100   0.080   0.080   0.080   1200   1200   1200    22000    22000    22000 EnumerateInstanceNames
"""  # noqa: E501
# pylint: enable=line-too-long

from __future__ import absolute_import

import time
import copy
import six

from ._utils import _format

__all__ = ['Statistics', 'OperationStatistic']


class OperationStatistic(object):
    # pylint: disable=too-many-instance-attributes
    """
    *New in pywbem 0.11 as experimental and finalized in 0.12.*

    A statistics data keeper for the executions of all operations with the
    same operation name.

    Objects of this class are created by the :class:`~pywbem.Statistics` class
    and can be accessed by pywbem users through its
    :meth:`~pywbem.Statistics.get_op_statistic` and
    :meth:`~pywbem.Statistics.snapshot` methods.
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

        self._server_time_sum = float(0)
        self._server_time_min = float('inf')
        self._server_time_max = float(0)
        self._server_time_stored = False

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
        :term:`integer`: The number of measured operations.
        """
        return self._count

    @property
    def exception_count(self):
        """
        :term:`integer`: The number of measured operations that resulted in an
        exception returned to the pywbem user (for example because a failure
        was indicated in the operation response of the WBEM server, or because
        pywbem itself detected a failure before sending the request or after
        receiving the response).
        """
        return self._exception_count

    @property
    def avg_time(self):
        """
        :class:`py:float`: The average elapsed client time for execution of the
        measured operations, in seconds.
        """
        try:
            return self._time_sum / self._count
        except ZeroDivisionError:
            return 0

    @property
    def min_time(self):
        """
        :class:`py:float`: The minimum elapsed client time for execution of the
        measured operations, in seconds.
        """
        return self._time_min

    @property
    def max_time(self):
        """
        :class:`py:float`: The maximum elapsed client time for execution of the
        measured operations, in seconds.
        """
        return self._time_max

    @property
    def avg_server_time(self):
        """
        :class:`py:float`: The average elapsed server time for execution of the
        measured operations, in seconds.

        This time is 0 if the WBEM server did not return the WBEM server
        response time.
        """
        try:
            return self._server_time_sum / self._count
        except ZeroDivisionError:
            return 0

    @property
    def min_server_time(self):
        """
        :class:`py:float`: The minimum elapsed server time for execution of the
        measured operations, in seconds.

        This time is 0 if the WBEM server did not return the WBEM server
        response time.
        """
        return self._server_time_min

    @property
    def max_server_time(self):
        """
        :class:`py:float`: The maximum elapsed server time for execution of the
        measured operations, in seconds.

        This time is 0 if the WBEM server did not return the WBEM server
        response time.
        """
        return self._server_time_max

    @property
    def avg_request_len(self):
        """
        :class:`py:float`: The average size of the HTTP body in the CIM-XML
        requests of the measured operations, in Bytes.
        """
        try:
            return self._request_len_sum / self._count
        except ZeroDivisionError:
            return 0.0

    @property
    def min_request_len(self):
        """
        :class:`py:float`: The minimum size of the HTTP body in the CIM-XML
        requests of the measured operations, in Bytes.
        """
        return self._request_len_min

    @property
    def max_request_len(self):
        """
        :class:`py:float`: The maximum size of the HTTP body in the CIM-XML
        requests of the measured operations, in Bytes.
        """
        return self._request_len_max

    @property
    def avg_reply_len(self):
        """
        :class:`py:float`: The average size of the HTTP body in the CIM-XML
        responses of the measured operations, in Bytes.
        """
        try:
            return self._reply_len_sum / self._count
        except ZeroDivisionError:
            return 0.0

    @property
    def min_reply_len(self):
        """
        :class:`py:float`: The minimum size of the HTTP body in the CIM-XML
        responses of the measured operations, in Bytes.
        """
        return self._reply_len_min

    @property
    def max_reply_len(self):
        """
        :class:`py:float`: The maximum size of the HTTP body in the CIM-XML
        responses of the measured operations, in Bytes.
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

        self._server_time_sum = float(0)
        self._server_time_min = float('inf')
        self._server_time_max = float(0)
        self._server_time_stored = False

        self._request_len_sum = float(0)
        self._request_len_min = float('inf')
        self._request_len_max = float(0)

        self._reply_len_sum = float(0)
        self._reply_len_min = float('inf')
        self._reply_len_max = float(0)

    def start_timer(self):
        """
        This is a low-level method that is called by pywbem at the begin of an
        operation. It starts the measurement for that operation, if statistics
        is enabled for the connection.

        A subsequent invocation of :meth:`~pywbem.OperationStatistic.stop_timer`
        will complete the measurement for that operation and will update the
        statistics data.
        """
        if self.container.enabled:
            self._start_time = time.time()
            if not self._stat_start_time:
                self._stat_start_time = self._start_time

    def stop_timer(self, request_len, reply_len, server_time=None,
                   exception=False):
        """
        This is a low-level method is called by pywbem at the end of an
        operation. It completes the measurement for that operation by capturing
        the needed data, and updates the statistics data, if statistics is
        enabled for the connection.

        Parameters:

          request_len (:term:`integer`):
            Size of the HTTP body of the CIM-XML request message, in Bytes.

          reply_len (:term:`integer`):
            Size of the HTTP body of the CIM-XML response message, in Bytes.

          exception (:class:`py:bool`):
            Boolean that specifies whether an exception was raised while
            processing the operation.

          server_time (:class:`py:bool`):
            Time in seconds that the server optionally returns to the
            client in the HTTP response defining the time from when the
            server received the request to when it started sending the
            response. If `None`, there is no time from the server.

        Returns:

          float: The elapsed time for the operation that just ended, or
          `None` if the statistics container holding this object is not
          enabled.
        """
        if not self.container.enabled:
            return None

        # stop the timer
        if self._start_time is None:
            raise RuntimeError('stop_timer() called without preceding '
                               'start_timer()')
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

        if server_time:
            self._server_time_stored = True
            self._server_time_sum += server_time
            if dt > self._server_time_max:
                self._server_time_max = server_time
            if dt < self._server_time_min:
                self._server_time_min = server_time

        if request_len > self._request_len_max:
            self._request_len_max = request_len
        if request_len < self._request_len_min:
            self._request_len_min = request_len

        if reply_len > self._reply_len_max:
            self._reply_len_max = reply_len
        if reply_len < self._reply_len_min:
            self._reply_len_min = reply_len

        return dt

    def __repr__(self):
        """
        Return a human readable string with the statistics values, for debug
        purposes.
        """
        return _format(
            "OperationStatistic("
            "name={s.name!A}, "
            "count={s.count!A}, "
            "exception_count={s.exception_count!A}, "
            "avg_time={s.avg_time!A}, "
            "min_time={s.min_time!A}, "
            "max_time={s.max_time!A}, "
            "avg_server_time={s.avg_server_time!A}, "
            "min_server_time={s.min_server_time!A}, "
            "max_server_time={s.max_server_time!A}, "
            "avg_request_len={s.avg_request_len!A}, "
            "min_request_len={s.min_request_len!A}, "
            "max_request_len={s.max_request_len!A}, "
            "avg_reply_len={s.avg_reply_len!A}, "
            "min_reply_len={s.min_reply_len!A}, "
            "max_reply_len={s.max_reply_len!A})",
            s=self)

    _formatted_header_w_svr = \
        'Count Excep         ClientTime              ServerTime        ' \
        '     RequestLen                ReplyLen       Operation\n' \
        '        Cnt     Avg     Min     Max     Avg     Min     Max   ' \
        ' Avg    Min    Max      Avg      Min      Max\n'

    _formatted_header = \
        'Count Excep         ClientTime        ' \
        '     RequestLen              ReplyLen       Operation\n' \
        '        Cnt     Avg     Min     Max   ' \
        ' Avg    Min    Max    Avg      Min      Max\n'

    def formatted(self, include_server_time):
        """
        Return a formatted one-line string with the statistics
        values for the operation for which this statistics object
        maintains data.

        This is a low-level method that is called by
        :meth:`pywbem.Statistics.formatted`.
        """
        if include_server_time:  # pylint: disable=no-else-return
            return ('{0:5d} {1:5d} '
                    '{2:7.3f} {3:7.3f} {4:7.3f} '
                    '{5:7.3f} {6:7.3f} {7:7.3f} '
                    '{8:6.0f} {9:6.0f} {10:6.0f} '
                    '{11:8.0f} {12:8.0f} {13:8.0f} {14}\n'.
                    format(self.count, self.exception_count,
                           self.avg_time, self.min_time, self.max_time,
                           self.avg_server_time, self.min_server_time,
                           self.max_server_time,
                           self.avg_request_len, self.min_request_len,
                           self.max_request_len,
                           self.avg_reply_len, self.min_reply_len,
                           self.max_reply_len,
                           self.name))
        else:
            return ('{0:5d} {1:5d} '
                    '{2:7.3f} {3:7.3f} {4:7.3f} '
                    '{5:6.0f} {6:6.0f} {7:6.0f} '
                    '{8:6.0f} {9:8.0f} {10:8.0f} {11}\n'.
                    format(self.count, self.exception_count,
                           self.avg_time, self.min_time, self.max_time,
                           self.avg_request_len, self.min_request_len,
                           self.max_request_len,
                           self.avg_reply_len, self.min_reply_len,
                           self.max_reply_len,
                           self.name))


class Statistics(object):
    """
    *New in pywbem 0.11 as experimental and finalized in 0.12.*

    The statistics of a connection, that captures and provides statistics data
    about the WBEM operations performed on the connection.

    This class contains an operation statistic object (of class
    :class:`~pywbem.OperationStatistic`) for each kind of WBEM operation.

    A :class:`~pywbem.Statistics` object can be in a state of enabled or
    disabled.
    If enabled, it accumulates the elapsed times between subsequent calls to
    the :meth:`~pywbem.OperationStatistic.start_timer` and
    :meth:`~pywbem.OperationStatistic.stop_timer` methods of class
    :class:`~pywbem.OperationStatistic`.
    If disabled, calls to these methods do not accumulate any time.
    Initially, the statistics container is disabled.

    The enablement state of the :class:`~pywbem.Statistics` object is
    controlled by the statistics enablement state of the connection it belongs
    to (see :meth:`pywbem.WBEMConnection.stats_enabled`)
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
        This method is called by pywbem to start the timer for a particular
        operation execution. It returns the corresponding
        :class:`~pywbem.OperationStatistic` object, creating one if needed.

        The timer is subsequently stopped by pywbem by calling the
        :meth:`~pywbem.OperationStatistic.stop_timer` method on the returned
        :class:`~pywbem.OperationStatistic` object.

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
            ret += _format("  {0!A}\n", self._op_stats[name])
        ret += ")"
        return ret

    def formatted(self):
        # pylint: disable=line-too-long
        """
        Return a human readable string with the statistics for this container.
        The operations are sorted by decreasing average time.

        The three columns for `ServerTime` are included only if the WBEM server
        has returned WBEM server response times.

        Example if statistics are enabled::

            Statistics (times in seconds, lengths in Bytes):
            Count Excep         ClientTime              ServerTime             RequestLen                ReplyLen       Operation
                    Cnt     Avg     Min     Max     Avg     Min     Max    Avg    Min    Max      Avg      Min      Max
                3     0   0.234   0.100   0.401   0.204   0.080   0.361   1233   1000   1500    26667    20000    35000 EnumerateInstances
                1     0   0.100   0.100   0.100   0.080   0.080   0.080   1200   1200   1200    22000    22000    22000 EnumerateInstanceNames
                . . .

        Example if statistics are disabled::

            Statistics (times in seconds, lengths in Bytes):
            Disabled
        """  # noqa: E501
        # pylint: enable=line-too-long
        ret = "Statistics (times in seconds, lengths in Bytes):\n"
        if self.enabled:
            snapshot = sorted(self.snapshot(),
                              key=lambda item: item[1].avg_time,
                              reverse=True)

            # Test to see if any server time is non-zero
            include_svr = False
            for name, stats in snapshot:  # pylint: disable=unused-variable
                # pylint: disable=protected-access
                if stats._server_time_stored:
                    include_svr = True
            # pylint: disable=protected-access
            if include_svr:
                ret += OperationStatistic._formatted_header_w_svr
            else:
                ret += OperationStatistic._formatted_header

            for name, stats in snapshot:  # pylint: disable=unused-variable
                ret += stats.formatted(include_svr)
        else:
            ret += "Disabled"
        return ret.strip()

    def reset(self):
        """
        Reset all statistics and clear any statistic names.
        All statistics must be inactive before a reset will execute

        Returns: True if reset, False if not
        """
        # Test for any stats being currently timed.
        for stat in six.itervalues(self._op_stats):
            if stat._start_time is not None:  # pylint: disable=protected-access
                return False

        # clear all statistics
        self._op_stats = {}
        return True
