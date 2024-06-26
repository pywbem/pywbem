#
# (C) Copyright 2003,2004 Hewlett-Packard Development Company, L.P.
# (C) Copyright 2006,2007 Novell, Inc.
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
#
# Author: Tim Potter <tpot@hp.com>
# Author: Bart Whiteley <bwhiteley@suse.de>
# Author: Ross Peoples <ross.peoples@gmail.com>
#

# pylint: disable=line-too-long
"""
Python classes for representing values of CIM data types, and related
conversion functions.

The following table shows how CIM data types are represented in Python.
Note that some basic CIM data types are represented with built-in Python
types.

========================================  =====================================
CIM data type                             Python type
========================================  =====================================
boolean                                   :class:`py:bool`
char16                                    :term:`string`
                                          or :class:`~pywbem.Char16`
string                                    :term:`string`
string (EmbeddedInstance)                 :class:`~pywbem.CIMInstance`
string (EmbeddedObject)                   :class:`~pywbem.CIMInstance`
                                          or :class:`~pywbem.CIMClass`
datetime                                  :class:`~pywbem.CIMDateTime`
reference                                 :class:`~pywbem.CIMInstanceName`
uint8                                     :class:`~pywbem.Uint8`
uint16                                    :class:`~pywbem.Uint16`
uint32                                    :class:`~pywbem.Uint32`
uint64                                    :class:`~pywbem.Uint64`
sint8                                     :class:`~pywbem.Sint8`
sint16                                    :class:`~pywbem.Sint16`
sint32                                    :class:`~pywbem.Sint32`
sint64                                    :class:`~pywbem.Sint64`
real32                                    :class:`~pywbem.Real32`
real64                                    :class:`~pywbem.Real64`
[] (array)                                :class:`py:list`
========================================  =====================================

The CIM NULL value is represented with Python `None` which can be used for any
CIM typed value to represent NULL.

Note that init methods of pywbem classes that take CIM typed values as input
may support Python types in addition to those shown above. For example, the
:class:`~pywbem.CIMProperty` class represents property values of CIM datetime
type internally as :class:`~pywbem.CIMDateTime` objects, but its init method
accepts :class:`py:datetime.timedelta` objects, :class:`py:datetime.datetime`
objects, :term:`string`, in addition to
:class:`~pywbem.CIMDateTime` objects.
"""
# pylint: enable=line-too-long
# Note: When used before module docstrings, Pylint scopes the disable statement
#       to the whole rest of the file, so we need an enable statement.

# This module is meant to be safe for 'import *'.

import copy
import re
from datetime import tzinfo, datetime, timedelta, timezone

from .config import ENFORCE_INTEGER_RANGE
from ._utils import _ensure_unicode, _hash_item, _format, _to_unicode, \
    _eq_item

__all__ = ['cimtype', 'type_from_name', 'MinutesFromUTC', 'CIMType',
           'CIMDateTime', 'CIMInt', 'Uint8', 'Sint8', 'Uint16', 'Sint16',
           'Uint32', 'Sint32', 'Uint64', 'Sint64', 'CIMFloat', 'Real32',
           'Real64', 'Char16', '_CIMComparisonMixin']


class _CIMComparisonMixin:  # pylint: disable=too-few-public-methods
    """
    Mixin class providing default implementations for equality test
    operators and hash function.

    The implementations of ordering tests are also provided and raise an
    exception because ordering of CIM objects is not supported.
    """

    __slots__ = []

    def __eq__(self, other):
        """
        Equality test for two CIM objects.

        The comparison must be implemented in the derived class.
        """
        raise NotImplementedError

    def __ne__(self, other):
        """
        Non-equality test for two CIM objects.

        The comparison is delegated to the `__eq__()` method, because we
        require it to be implemented.
        See https://stackoverflow.com/a/30676267/1424462 for discussion about
        delegating to == vs. __eq__().
        """
        return not self.__eq__(other)

    def __raise_ordering_not_supported(self, other, op):
        """
        Function to raise a TypeError indicating that ordering of this class
        is not supported.
        """
        raise TypeError(
            f"'{op}' not supported between instances of '{type(self)}' and "
            f"'{type(other)}'")

    def __lt__(self, other):
        ""  # Avoids docstring to be inherited
        self.__raise_ordering_not_supported(other, '<')

    def __gt__(self, other):
        ""  # Avoids docstring to be inherited
        self.__raise_ordering_not_supported(other, '>')

    def __ge__(self, other):
        ""  # Avoids docstring to be inherited
        self.__raise_ordering_not_supported(other, '>=')

    def __le__(self, other):
        ""  # Avoids docstring to be inherited
        self.__raise_ordering_not_supported(other, '<=')

    def __hash__(self):
        """
        Interface definition for hash function to be provided by subclasses.

        Background: In order to behave as expected in sets and other hash-based
        collections, the hash values of objects must be equal when the objects
        themselves are considered equal. The default hash function for classes
        is based on `id()` and therefore does not satisfy that requirement.

        Therefore, the CIM objects need to implement a hash function that
        satisfies that requirement.
        """
        raise NotImplementedError


class SlottedPickleMixin:
    """
    Starting with Python 3.8, the default pickle protocol is protocol 4, which
    supports objects with slots by default, without requiring that they define
    methods __getstate__() and __setstate__().

    However, objects pickled from Python versions < 3.8 (using the built-in
    methods) saved all attributes in one shot by saving their __dict__ value,
    so the default unpickling after introduction of slots attempts to set the
    __dict__ which fails with AttributeError.

    Therefore, these methods are provided to cover upgrading from use of
    objects pickled with python versions older than 3.8 to define __getstate__
    and __setstate__.

    Also, because code in pywbem_mock/_resolvermixin.py dynamically added
    the non-existing attributes 'classorigin' and 'propagated' to CIMClass
    objects (that code has been removed meanwhile), the unpickling may
    encounter CIMClass objects that still have these attributes set. That
    is handled by ignoring these attributes during unpickling.

    These methods support classes with both slotted and non-slotted attributes.
    Support for non-slottted attributes is needed for example when users
    define classes derived from CIM object or CIM type classes.
    """

    __slots__ = []

    def __getstate__(self):
        ""  # Avoids docstring to be inherited

        dct = {}
        for attr in self.__slots__:
            dct[attr] = getattr(self, attr)

        # Support for objects that also have __dict__, e.g. user defined
        # derived classes that did not define __slots__:
        if hasattr(self, '__dict__'):
            for attr in self.__dict__:
                dct[attr] = getattr(self, attr)

        return dct

    def __setstate__(self, dct):
        ""  # Avoids docstring to be inherited

        # Defer import due to circular import dependencies:
        # pylint: disable=import-outside-toplevel
        from pywbem._cim_obj import CIMClass as class_type

        for attr in dct:

            # Compatibility support for CIMClass objects that were pickled
            # before pywbem 1.2.0:
            if isinstance(self, class_type) and \
                    attr in ('classorigin', 'propagated'):
                continue

            setattr(self, attr, dct[attr])


class MinutesFromUTC(SlottedPickleMixin, tzinfo):
    """
    Timezone information (an implementation of :class:`py:datetime.tzinfo`)
    that represents a fixed offset in +/- minutes from UTC and is thus suitable
    for the CIM datetime data type.

    Objects of this class are needed in order to make
    :class:`py:datetime.datetime` objects timezone-aware, in order to be
    useable as input data to the timezone-aware :class:`~pywbem.CIMDateTime`
    type.

    They are also used to provide timezone information to
    :meth:`~pywbem.CIMDateTime.now` and
    :meth:`~pywbem.CIMDateTime.fromtimestamp`

    Example:

    ::

        from datetime import datetime
        from time import time
        import pywbem

        # Create a timezone-aware datetime object (for CEDT = UTC+2h), and
        # convert that to CIM datetime:

        dt = datetime(year=2016, month=3, day=31, hour=19, minute=30,
                      second=40, microsecond=654321,
                      tzinfo=pywbem.MinutesFromUTC(120))
        cim_dt = pywbem.CIMDateTime(dt)

        # Convert a POSIX timestamp value to CIM datetime (for EST = UTC-5h):

        posix_ts = time()  # seconds since the epoch, not timezone-aware
        cim_dt = pywbem.CIMDateTime.fromtimestamp(posix_ts,
                                                  pywbem.MinutesFromUTC(-300))
    """

    __slots__ = ['_offset']

    def __init__(self, offset):  # pylint: disable=super-init-not-called
        """
        Parameters:

          offset (:term:`integer`):
            Timezone offset to be represented in the CIM datetime value in +/-
            minutes from UTC.

            This is the offset of local time to UTC (including DST offset),
            where a positive value indicates minutes east of UTC, and a
            negative value indicates minutes west of UTC.
        """
        self._offset = offset

    def __repr__(self):
        """
        Return a string representation suitable for debugging.
        """
        return _format(
            "MinutesFromUTC("
            "offset={s._offset!A})",
            s=self)

    def utcoffset(self, dt):  # pylint: disable=unused-argument
        """
        An implementation of the corresponding base class method
        (see :meth:`py:datetime.tzinfo.utcoffset` for its description),
        which needs
        to return the offset of local time to UTC (including DST offset), as a
        :class:`py:datetime.timedelta` object. This method is called by the
        Python datetime classes, and a pywbem user normally does not have
        to deal with it.

        This implementation returns the offset used to initialize the object,
        for any specified `dt` parameter.
        """
        return timedelta(minutes=self._offset)

    def dst(self, dt):  # pylint: disable=unused-argument
        """
        An implementation of the corresponding base class method,
        (see :meth:`py:datetime.tzinfo.dst` for its description),
        which needs
        to return the offset caused by DST, as a :class:`py:datetime.timedelta`
        object. This method is called by the Python datetime classes, and a
        pywbem user normally does not have to deal with it.

        This implementation returns an offset of 0 (indicating that DST is not
        in effect), for any specified `dt` parameter, because CIM datetime
        values do not represent DST information.
        """
        return timedelta(0)

    def tzname(self, dt):  # pylint: disable=unused-argument
        """
        An implementation of the corresponding base class method,
        (see :meth:`py:datetime.tzinfo.tzname` for its description),
        which needs to return the name of the timezone of the
        specified datetime object.

        This implementation returns the timezone offset formatted as a
        signed HH:MM string, where positive values are east of UTC.
        """
        # Note that divmod() and // return one less for negative numbers
        # assuming the remainder would be added on it. For example,
        # divmod(-5, 60) = -1, 55
        # That is mathematically consistent, but is not what we want
        # since we want both return values to be negative, for negative
        # input. Therefore we handle the sign separately.
        sign = '-' if self._offset < 0 else ''
        hh, mm = divmod(abs(self._offset), 60)
        return f"{sign}{hh:02d}:{mm:02d}"


class CIMType(SlottedPickleMixin):  # pylint: disable=too-few-public-methods
    """Base type for all CIM data types defined in this package."""

    __slots__ = []

    #: The name of the CIM datatype, as a :term:`string`. See
    #: :ref:`CIM data types` for details.
    cimtype = None


class Char16(CIMType, str):
    """
    A value of CIM data type char16.

    This class is derived from :term:`unicode string`.

    Normally, values of CIM data type char16 are represented using
    :term:`unicode string` objects. This class can be used to represent values
    of CIM data type char16 when it matters to distinguish them from values of
    CIM data type string. The only situation where that matters is for
    keybindings, because that allows properly setting the TYPE attribute on
    KEYVALUE elements when creating the CIM-XML representation for a keybinding.
    """

    __slots__ = []

    #: The name of the CIM datatype ``"char16"``
    cimtype = 'char16'

    # Changing the string content requires using __new__() instead of __init__()
    def __new__(cls, content=''):
        ""  # Avoids docstring to be inherited
        return super().__new__(cls, _ensure_unicode(content))


class CIMDateTime(_CIMComparisonMixin, CIMType):
    """
    A value of CIM data type datetime.

    The object represents either a timezone-aware point in time, or a time
    interval.

    Two objects of this class compare equal if their public attributes compare
    equal. Objects of this class are immutable and :term:`hashable`, with the
    hash value being based on their public attributes.
    """

    __slots__ = ['__timedelta', '__datetime', '__precision']

    #: The name of the CIM datatype ``"datetime"``
    cimtype = 'datetime'

    _timestamp_pattern = re.compile(
        r'^([\d\*]{4})([\d\*]{2})([\d\*]{2})'
        r'([\d\*]{2})([\d\*]{2})([\d\*]{2})\.([\d\*]{6})'
        r'([+|-])(\d{3})')

    _interval_pattern = re.compile(
        r'^([\d\*]{8})([\d\*]{2})([\d\*]{2})([\d\*]{2})\.([\d\*]{6})'
        r'(:)(000)')

    def __init__(self, dtarg):
        """
        Parameters:

          dtarg:
            The value from which the object is initialized, as one of the
            following types:

            * A :term:`string` object will be
              interpreted as CIM datetime format (see :term:`DSP0004`) and
              will result in a point in time or a time interval. The use
              of asterisk characters in the value is supported according to
              the rules defined in :term:`DSP0004` (e.g.
              "20180911124613.128***:000").
            * A :class:`py:datetime.datetime` object will result in a point
              in time. If the :class:`py:datetime.datetime` object is
              timezone-aware (see :class:`~pywbem.MinutesFromUTC`), the
              specified timezone will be used. Otherwise, a default timezone
              of UTC will be assumed.
            * A :class:`py:datetime.timedelta` object will result in a time
              interval.
            * Another :class:`~pywbem.CIMDateTime` object will be copied.
        """
        self.__timedelta = None  # timedelta value, if interval
        self.__datetime = None  # datetime value, if timestamp
        self.__precision = None  # 0-based index of first asterisk, or None
        dtarg = _ensure_unicode(dtarg)
        if isinstance(dtarg, str):
            m = self._timestamp_pattern.search(dtarg)
            if m is not None:
                # timestamp format
                parts = m.groups()
                offset = int(parts[8])
                if parts[7] == '-':
                    offset = -offset

                if '*' in dtarg:
                    first = dtarg.index('*')
                    after = dtarg.rindex('*') + 1
                    if not re.match(r'^[\*\.]+$', dtarg[first:after]):
                        raise ValueError(
                            _format("Asterisks in CIM datetime timestamp "
                                    "value are not consecutive: {0!A}", dtarg))
                    if after != 21:  # end of microseconds field
                        raise ValueError(
                            _format("Asterisks in CIM datetime timestamp "
                                    "value do not include least significant "
                                    "field: {0!A}", dtarg))
                    self.__precision = first

                year = self._to_int(parts[0], 0, None, 'year', dtarg)
                month = self._to_int(parts[1], 1, None, 'month', dtarg)
                day = self._to_int(parts[2], 1, None, 'day', dtarg)
                hour = self._to_int(parts[3], 0, None, 'hour', dtarg)
                minute = self._to_int(parts[4], 0, None, 'minute', dtarg)
                second = self._to_int(parts[5], 0, None, 'second', dtarg)
                microsec = self._to_int(parts[6], 0, '0', 'microsecond', dtarg)

                try:
                    # Possible errors are e.g. field out of range
                    self.__datetime = datetime(
                        year, month, day, hour, minute, second, microsec,
                        MinutesFromUTC(offset))
                except ValueError as exc:
                    raise ValueError(
                        _format("Invalid datetime() input from CIM datetime "
                                "timestamp value {0!A}: {1}", dtarg, exc))

            else:
                m = self._interval_pattern.search(dtarg)
                if m is not None:
                    # interval format
                    parts = m.groups()
                    if '*' in dtarg:
                        first = dtarg.index('*')
                        after = dtarg.rindex('*') + 1
                        if not re.match(r'^[\*\.]+$', dtarg[first:after]):
                            raise ValueError(
                                _format("Asterisks in CIM datetime interval "
                                        "value are not consecutive: {0!A}",
                                        dtarg))
                        if after != 21:  # end of microseconds field
                            raise ValueError(
                                _format("Asterisks in CIM datetime interval "
                                        "value do not include least "
                                        "significant field: {0!A}", dtarg))
                        self.__precision = first
                    days = self._to_int(parts[0], 0, None, 'days', dtarg)
                    hours = self._to_int(parts[1], 0, None, 'hours', dtarg)
                    minutes = self._to_int(parts[2], 0, None, 'minutes', dtarg)
                    seconds = self._to_int(parts[3], 0, None, 'seconds', dtarg)
                    microsecs = self._to_int(parts[4], 0, '0', 'microseconds',
                                             dtarg)

                    try:
                        # Possible errors are e.g. field out of range
                        self.__timedelta = timedelta(
                            days=days, hours=hours, minutes=minutes,
                            seconds=seconds, microseconds=microsecs)
                    except ValueError as exc:
                        raise ValueError(
                            _format("Invalid timedelta() input from CIM "
                                    "datetime interval value {0!A}: {1}",
                                    dtarg, exc))
                else:
                    raise ValueError(
                        _format("Invalid format of CIM datetime value: {0!A}",
                                dtarg))
        elif isinstance(dtarg, datetime):
            if dtarg.tzinfo is None:
                self.__datetime = dtarg.replace(tzinfo=MinutesFromUTC(0))
            else:
                self.__datetime = copy.copy(dtarg)
        elif isinstance(dtarg, timedelta):
            self.__timedelta = copy.copy(dtarg)
        elif isinstance(dtarg, CIMDateTime):
            self.__datetime = copy.copy(dtarg.datetime)
            self.__timedelta = copy.copy(dtarg.timedelta)
        else:
            raise TypeError(
                _format("dtarg argument {0!A} has an invalid type: {1} "
                        "(expected datetime, timedelta, string, or "
                        "CIMDateTime)", dtarg, type(dtarg)))

    @staticmethod
    def _to_int(value_str, min_value, rep_digit, field_name, dtarg):
        """
        Convert value_str into an integer, replacing right-consecutive
        asterisks with rep_digit, and an all-asterisk value with min_value.

        field_name and dtarg are passed only for informational purposes.
        """
        if '*' in value_str:
            first = value_str.index('*')
            after = value_str.rindex('*') + 1
            if value_str[first:after] != '*' * (after - first):
                raise ValueError(
                    _format("Asterisks in {0} field of CIM datetime value "
                            "{1!A} are not consecutive: {2!A}",
                            field_name, dtarg, value_str))
            if after != len(value_str):
                raise ValueError(
                    _format("Asterisks in {0} field of CIM datetime value "
                            "{1!A} do not end at end of field: {2!A}",
                            field_name, dtarg, value_str))
            if rep_digit is None:  # pylint: disable=no-else-return
                # Must be an all-asterisk field
                if first != 0:
                    raise ValueError(
                        _format("Asterisks in {0} field of CIM datetime value "
                                "{1!A} do not start at begin of field: {2!A}",
                                field_name, dtarg, value_str))
                return min_value
            else:
                value_str = value_str.replace('*', rep_digit)
        # Because the pattern and the asterisk replacement mechanism already
        # ensure only decimal digits, we expect the integer conversion to
        # always succeed.
        value = int(value_str)
        return value

    def _to_str(self, value, field_begin, field_len):
        """
        Convert value (int) to a field string, considering precision.
        """
        value_str = f'{value:0{field_len}d}'
        if self.precision is not None and \
                self.precision < field_begin + field_len:
            # field is partly or completely affected by precision
            # -> replace insignificant digits with asterisks
            precision_index = max(0, self.precision - field_begin)
            value_str = value_str[:precision_index] + \
                '*' * (field_len - precision_index)
        return value_str

    @property
    def minutes_from_utc(self):
        """
        The timezone offset of this point in time object as +/- minutes from
        UTC.

        A positive value of the timezone offset indicates minutes east of UTC,
        and a negative value indicates minutes west of UTC.

        0, if this object represents a time interval.
        """
        offset = 0
        if self.__datetime is not None and \
                self.__datetime.utcoffset() is not None:
            offset = self.__datetime.utcoffset().seconds / 60
            if self.__datetime.utcoffset().days == -1:
                offset = -((60 * 24) - offset)
        return int(offset)

    @property
    def datetime(self):
        """
        The point in time represented by this object, as a
        :class:`py:datetime.datetime` object.

        `None` if this object represents a time interval.
        """
        return self.__datetime

    @property
    def timedelta(self):
        """
        The time interval represented by this object, as a
        :class:`py:datetime.timedelta` object.

        `None` if this object represents a point in time.
        """
        return self.__timedelta

    @property
    def precision(self):
        """
        Precision of the time interval or point in time represented by this
        object, if the datetime input string contained asterisk characters.

        The precision is the 0-based index of the first asterisk character in
        the datetime input string, or `None` if there were no asterisk
        characters. For example, the precision of the timestamp value
        "201809121230**.******+000" is 12.
        """
        return self.__precision

    @property
    def is_interval(self):
        """
        A boolean indicating whether this object represents a time interval
        (`True`) or a point in time (`False`).
        """
        return self.__timedelta is not None

    @staticmethod
    def get_local_utcoffset():
        """
        Return the timezone offset of the current local timezone as +/- minutes
        from UTC.

        A positive value indicates minutes east of UTC, and a negative
        value indicates minutes west of UTC.
        """
        utc_unaware = datetime.now(timezone.utc).replace(tzinfo=None)

        local_unaware = datetime.now()
        if local_unaware < utc_unaware:
            return - int(float((utc_unaware - local_unaware).seconds) / 60 + .5)
        return int(float((local_unaware - utc_unaware).seconds) / 60 + .5)

    @classmethod
    def now(cls, tzi=None):
        """
        Factory method that returns a new :class:`~pywbem.CIMDateTime` object
        representing the current date and time.

        The optional timezone information is used to convert the CIM datetime
        value into the desired timezone. That does not change the point in time
        that is represented by the value, but it changes the value of the
        ``hhmmss`` components of the CIM datetime value to compensate for
        changes in the timezone offset component.

        Parameters:

          tzi (:class:`~pywbem.MinutesFromUTC`):
            Timezone information. `None` means that the current local timezone
            is used.

        Returns:

            A new :class:`~pywbem.CIMDateTime` object representing the current
            date and time.
        """
        if tzi is None:
            tzi = MinutesFromUTC(cls.get_local_utcoffset())
        return cls(datetime.now(tzi))

    @classmethod
    def fromtimestamp(cls, ts, tzi=None):
        # pylint: disable=invalid-name
        """
        Factory method that returns a new :class:`~pywbem.CIMDateTime` object
        from a POSIX timestamp value and optional timezone information.

        A POSIX timestamp value is the number of seconds since "the epoch",
        i.e. 1970-01-01 00:00:00 UTC. Thus, a POSIX timestamp value is
        unambiguous w.r.t. the timezone, but it is not timezone-aware.

        The optional timezone information is used to convert the CIM datetime
        value into the desired timezone. That does not change the point in time
        that is represented by the value, but it changes the value of the
        ``hhmmss`` components of the CIM datetime value to compensate for
        changes in the timezone offset component.

        Parameters:

          ts (:term:`integer`):
            POSIX timestamp value.

          tzi (:class:`~pywbem.MinutesFromUTC`):
            Timezone information. `None` means that the current local timezone
            is used.

        Returns:

            A new :class:`~pywbem.CIMDateTime` object representing the
            specified point in time.
        """
        if tzi is None:
            tzi = MinutesFromUTC(cls.get_local_utcoffset())
        return cls(datetime.fromtimestamp(ts, tzi))

    def __str__(self):
        """
        Return a string representing the object in CIM datetime format.
        """
        if self.is_interval:  # pylint: disable=no-else-return
            days = self.timedelta.days
            hours = self.timedelta.seconds // 3600
            sec_in_hour = self.timedelta.seconds - hours * 3600
            minutes = sec_in_hour // 60
            seconds = sec_in_hour - minutes * 60
            microsecs = self.timedelta.microseconds

            days_str = self._to_str(days, 0, 8)
            hours_str = self._to_str(hours, 8, 2)
            minutes_str = self._to_str(minutes, 10, 2)
            seconds_str = self._to_str(seconds, 12, 2)
            microsecs_str = self._to_str(microsecs, 15, 6)

            ret_str = (f'{days_str}{hours_str}{minutes_str}{seconds_str}.'
                       f'{microsecs_str}:000')
            return ret_str

        else:  # timestamp
            offset = self.minutes_from_utc
            sign = '+'
            if offset < 0:
                sign = '-'
                offset = -offset

            year = self.datetime.year
            month = self.datetime.month
            day = self.datetime.day
            hour = self.datetime.hour
            minute = self.datetime.minute
            second = self.datetime.second
            microsec = self.datetime.microsecond

            year_str = self._to_str(year, 0, 4)
            month_str = self._to_str(month, 4, 2)
            day_str = self._to_str(day, 6, 2)
            hour_str = self._to_str(hour, 8, 2)
            minute_str = self._to_str(minute, 10, 2)
            second_str = self._to_str(second, 12, 2)
            microsec_str = self._to_str(microsec, 15, 6)

            ret_str = (f'{year_str}{month_str}{day_str}{hour_str}{minute_str}'
                       f'{second_str}.{microsec_str}{sign}{offset:03d}')
            return ret_str

    def __repr__(self):
        """
        Return a string representation suitable for debugging.
        """
        return _format(
            "CIMDateTime("
            "cimtype={s.cimtype!A}, "
            "datetime={s.datetime!A}, "
            "timedelta={s.timedelta!A}, "
            "precision={s.precision!A}), "
            "minutes_from_utc={s.minutes_from_utc!A})",
            s=self)

    def __getstate__(self):
        ""  # Avoids docstring to be inherited
        return str(self)

    def __setstate__(self, arg):
        ""  # Avoids docstring to be inherited
        self.__init__(arg)

    def __eq__(self, other):
        """
        Equality test function for two :class:`~pywbem.CIMDateTime` objects.

        The equality is based on their public attributes.

        Note that a :class:`~pywbem.CIMDateTime` object represents either a
        time interval or a point in time but never both. Therefore, an object
        representing an interval is never equal to an object representing a
        point in time.

        Returns `False` if the `other` object is not a
        :class:`~pywbem.CIMDateTime` object.
        """
        if self is other:
            return True
        if not isinstance(other, CIMDateTime):
            return False
        return (_eq_item(self.datetime, other.datetime) and
                _eq_item(self.timedelta, other.timedelta))

    def __hash__(self):
        """
        Return a hash value based on the public attributes of this class.
        Because these attributes are not modifiable, objects of this class are
        :term:`hashable` (and not just :term:`unchanged-hashable`).
        """
        hashes = (
            _hash_item(self.datetime),
            _hash_item(self.timedelta),
            # The 'is_interval' and 'minutes_from_utc' attributes are not used
            # for hash value calculation because they are derived attributes.
        )
        return hash(hashes)


# CIM integer types


class CIMInt(CIMType, int):
    """
    Base type for CIM integer data types. Derived from :class:`~pywbem.CIMType`
    and :class:`py3:int`. The input parameters are consistent with
    :class:`py3:int` except that argument `x` can also be passed as a keyword
    input parameter to maintain a consistent interface despite changes to the
    Python :class:`py3:int` ('x' was changed to positional only in python 3.8).

    This class has a concept of a valid range for the represented integer,
    based upon the capability of the CIM data type as defined in
    :term:`DSP0004`. The additional constraints defined by possible MinValue
    or MaxValue qualifiers are not taken into account at this level.

    The valid value range is enforced when an instance of a subclass of this
    class (e.g. :class:`~pywbem.Uint8`) is created. Values outside of the valid
    range raise a :exc:`ValueError`. Enforcement of the valid value range can
    be disabled via the configuration variable
    :data:`~pywbem.config.ENFORCE_INTEGER_RANGE`.

    Two objects of subclasses of this base class compare equal if their numeric
    values compare equal. Objects of this class are immutable and
    :term:`hashable`, with the hash value being based on its numeric value.

    Parameters:
          x (:term:`integer` or :term:`string`):
            A number or a string that can be converted into an integer number.
            The parameter 'x' can be either a positional or keyword argument
            for compatibility with Python<=3.7. Default value: 0.

          base (:term:`integer`):
            A number representing the number base  (radix) of 'x'. Default
            value: 10. Allowed only if 'x' is a string.

    Instances of subclasses of this class can be initialized with the usual
    input arguments supported by :term:`integer`, for example:
    ::

        >>> pywbem.Uint8(42)
        Uint8(cimtype='uint8', 42)

        >>> pywbem.Uint8('42')
        Uint8(cimtype='uint8', 42)

        >>> pywbem.Uint8('2A', 16)
        Uint8(cimtype='uint8', 42)

        >>> pywbem.Uint8('2A', base=16)
        Uint8(cimtype='uint8', 42)

        >>> pywbem.Uint8(x='2A', base=16)
        Uint8(cimtype='uint8', 42)

        >>> pywbem.Uint8('100', 16)
        Traceback (most recent call last):
          . . .
        ValueError: Integer value 256 is out of range for CIM datatype uint8

        >>> pywbem.Uint8(100, 10)
        Traceback (most recent call last):
          . . .
        TypeError: int() can't convert non-string with explicit base
    """

    __slots__ = []

    #: The minimum valid value for the integer, according to the capabilities
    #: of its CIM data type. See :ref:`CIM data types` for a list of CIM
    #: integer data types.
    minvalue = None

    #: The maximum valid value for the integer, according to the capabilities
    #: of its CIM data type. See :ref:`CIM data types` for a list of CIM
    #: integer data types.
    maxvalue = None

    def __new__(cls, *args, **kwargs):
        ""  # Avoids docstring being inherited

        # Python 3.7 removed support for passing the value for int() as a
        # keyword argument named 'x'. It now must be passed as a positional
        # argument.  CIMInt has retained the positional or keyword capability
        # so we transform the keyword arg into a positional arg.
        if 'x' in kwargs:
            args = list(*args)  # args is passed as a tuple
            args.append(kwargs.pop('x'))

        value = int(*args, **kwargs)
        if ENFORCE_INTEGER_RANGE:
            if value > cls.maxvalue or value < cls.minvalue:
                raise ValueError(
                    _format("Integer value {0} is out of range for CIM "
                            "datatype {1}", value, cls.cimtype))
        # The value needs to be processed here, because int is immutable
        return super().__new__(cls, *args, **kwargs)

    def __str__(self):
        """
        Python 3.8 removed __str__() on int causing recursive loop failures.
        The int.__repr__method returns exactly what is needed for a string
        representation.
        """
        return f"{int.__repr__(self)}"

    def __repr__(self):
        """
        Return a string representation suitable for debugging.
        """
        return _format(
            "{s.__class__.__name__}("
            "cimtype={s.cimtype!A}, "
            "minvalue={s.minvalue}, "
            "maxvalue={s.maxvalue}, "
            "{s})",
            s=self)


class Uint8(CIMInt):
    """
    A value of CIM data type uint8. Derived from :class:`~pywbem.CIMInt`.

    For details on CIM integer data types, see :class:`~pywbem.CIMInt`.

    Parameters:
          x (:term:`integer` or :term:`string`):
            A number or a string that can be converted into an integer number.

          base (:term:`integer`):
            A number representing the number format (radix). Default value: 10.
    """

    __slots__ = []

    #: The name of the CIM datatype
    cimtype = 'uint8'
    #: The minimum valid value for the CIM datatype
    minvalue = 0
    #: The maximum valid value for the CIM datatype
    maxvalue = 2**8 - 1


class Sint8(CIMInt):
    """
    A value of CIM data type sint8. Derived from :class:`~pywbem.CIMInt`.

    For details on CIM integer data types, see :class:`~pywbem.CIMInt`.

    Parameters:
          x (:term:`integer` or :term:`string`):
            A number or a string that can be converted into an integer number.

          base (:term:`integer`):
            A number representing the number format (radix). Default value: 10.
    """

    __slots__ = []

    #: The name of the CIM datatype
    cimtype = 'sint8'
    #: The minimum valid value for the CIM datatype
    minvalue = -2 ** (8 - 1)
    #: The maximum valid value for the CIM datatype
    maxvalue = 2 ** (8 - 1) - 1


class Uint16(CIMInt):
    """
    A value of CIM data type uint16. Derived from :class:`~pywbem.CIMInt`.

    For details on CIM integer data types, see :class:`~pywbem.CIMInt`.

    Parameters:
        x (:term:`integer` or :term:`string`):
          A number or a string that can be converted into an integer number.
          'x' may be a position or keyword argument.

        base (:term:`integer`):
          A number representing the number format (radix). Default value: 10.
    """

    __slots__ = []

    #: The name of the CIM datatype
    cimtype = 'uint16'
    #: The minimum valid value for the CIM datatype
    minvalue = 0
    #: The maximum valid value for the CIM datatype
    maxvalue = 2**16 - 1


class Sint16(CIMInt):
    """
    A value of CIM data type sint16. Derived from :class:`~pywbem.CIMInt`.

    For details on CIM integer data types, see :class:`~pywbem.CIMInt`.

    Parameters:
        x (:term:`integer` or :term:`string`):
          A number or a string that can be converted into an integer number.
          'x' may be a position or keyword argument.

        base (:term:`integer`):
          A number representing the number format (radix). Default value: 10.
    """

    __slots__ = []

    #: The name of the CIM datatype
    cimtype = 'sint16'
    #: The minimum valid value for the CIM datatype
    minvalue = -2 ** (16 - 1)
    #: The maximum valid value for the CIM datatype
    maxvalue = 2 ** (16 - 1) - 1


class Uint32(CIMInt):
    """
    A value of CIM data type uint32. Derived from :class:`~pywbem.CIMInt`.

    For details on CIM integer data types, see :class:`~pywbem.CIMInt`.

    Parameters:
        x (:term:`integer` or :term:`string`):
          A number or a string that can be converted into an integer number.
          x' may be a position or keyword argument.

          base (:term:`integer`):
            'x' may be a position or keyword argument.
    """

    __slots__ = []

    #: The name of the CIM datatype
    cimtype = 'uint32'
    #: The minimum valid value for the CIM datatype
    minvalue = 0
    #: The maximum valid value for the CIM datatype
    maxvalue = 2 ** 32 - 1


class Sint32(CIMInt):
    """
    A value of CIM data type sint32. Derived from :class:`~pywbem.CIMInt`.

    For details on CIM integer data types, see :class:`~pywbem.CIMInt`.

    Parameters:
        x (:term:`integer` or :term:`string`):
          A number or a string that can be converted into an integer number.
          'x' may be a position or keyword argument.

        base (:term:`integer`):
          A number representing the number format (radix). Default value: 10.
    """

    __slots__ = []

    #: The name of the CIM datatype
    cimtype = 'sint32'
    #: The minimum valid value for the CIM datatype
    minvalue = -2 ** (32 - 1)
    #: The maximum valid value for the CIM datatype
    maxvalue = 2 ** (32 - 1) - 1


class Uint64(CIMInt):
    """
    A value of CIM data type uint64. Derived from :class:`~pywbem.CIMInt`.

    For details on CIM integer data types, see :class:`~pywbem.CIMInt`.

    Parameters:
        x (:term:`integer` or :term:`string`):
          A number or a string that can be converted into an integer number.
          'x' may be a position or keyword argument.

        base (:term:`integer`):
          A number representing the number format (radix). Default value: 10.
    """

    __slots__ = []

    #: The name of the CIM datatype
    cimtype = 'uint64'
    #: The minimum valid value for the CIM datatype
    minvalue = 0
    #: The maximum valid value for the CIM datatype
    maxvalue = 2 ** 64 - 1


class Sint64(CIMInt):
    """
    A value of CIM data type sint64. Derived from :class:`~pywbem.CIMInt`.

    For details on CIM integer data types, see :class:`~pywbem.CIMInt`.

    Parameters:
        x (:term:`integer` or :term:`string`):
          A number or a string that can be converted into an integer number.
          'x' may be a position or keyword argument.

        base (:term:`integer`):
          A number representing the number format (radix). Default value: 10.
    """

    __slots__ = []

    #: The name of the CIM datatype
    cimtype = 'sint64'
    #: The minimum valid value for the CIM datatype
    minvalue = -2 ** (64 - 1)
    #: The maximum valid value for the CIM datatype
    maxvalue = 2 ** (64 - 1) - 1


# CIM float types


class CIMFloat(CIMType, float):
    """
    Base type for real (floating point) CIM data types.

    Two objects of subclasses of this base class compare equal if their numeric
    values compare equal. Objects of this class are immutable and
    :term:`hashable`, with the hash value being based on its numeric value.

    Note that equality comparison of floating point numbers in Python (and in
    almost any programming language) comes with some surprises.
    See `"Floating Point Arithmetic: Issues and Limitations"
    <https://docs.python.org/2/tutorial/floatingpoint.html>`_ for details,
    and specifically `"Comparing Floating Point Numbers, 2012 Edition"
    <https://randomascii.wordpress.com/2012/02/25/comparing-floating-point-numbers-2012-edition/>`_
    on the topic of equality comparison. The same issues apply to hash values
    that are based on the numeric value of floating point numbers. Therefore,
    it is not recommended to perform equality comparison of objects of
    subclasses of this class, or to use them as dictionary keys or as members
    in sets.
    """

    __slots__ = []

    def __str__(self):
        """
        Return a string representation of the value. Python 3.8 removed
        __str__() on float causing an infinite recursion for the CIMInt and
        class whose __repr__() calls __str__() on itself. The
        float.__repr__method returns exactly what is needed for a string
        representation.
        """
        return float.__repr__(self)

    def __repr__(self):
        """Return a string representation suitable for debugging."""
        return _format(
            "{s.__class__.__name__}("
            "cimtype={s.cimtype!A}, "
            "{s})",
            s=self)


class Real32(CIMFloat):
    """
    A value of CIM data type real32. Derived from :class:`~pywbem.CIMFloat`.

    It is not recommended to perform equality comparison on objects of this
    class, or to use them as dictionary keys or as members in sets. See
    :class:`~pywbem.CIMFloat` for details.
    """

    __slots__ = []

    #: The name of the CIM datatype
    cimtype = 'real32'


class Real64(CIMFloat):
    """
    A value of CIM data type real64. Derived from :class:`~pywbem.CIMFloat`.

    It is not recommended to perform equality comparison on objects of this
    class, or to use them as dictionary keys or as members in sets. See
    :class:`~pywbem.CIMFloat` for details.
    """

    __slots__ = []

    #: The name of the CIM datatype
    cimtype = 'real64'


# Python number types listed in :term:`number`.
number_types = (int, float)  # pylint: disable=invalid-name


def cimtype(obj):
    """
    Return the CIM data type name of a CIM typed object, as a string.

    For an array, the type is determined from the first array element
    (CIM arrays must be homogeneous w.r.t. the type of their elements).
    If the array is empty, that is not possible and
    :exc:`py:ValueError` is raised.

    Note that Python :term:`numbers <number>` are not valid input objects
    because determining their CIM data type (e.g. :class:`~pywbem.Uint8`,
    :class:`~pywbem.Real32`) would require knowing the value range. Therefore,
    :exc:`py:TypeError` is raised in this case.

    Parameters:

      obj (:term:`CIM data type`):
        The object whose CIM data type name is returned.

    Returns:

      :term:`string`: The CIM data type name of the object (e.g. ``"uint8"``).

    Raises:

      TypeError: The object does not have a valid CIM data type.
      ValueError: Cannot determine CIM data type from an empty array.
    """

    if isinstance(obj, CIMType):
        return obj.cimtype

    if isinstance(obj, bool):
        return 'boolean'

    if isinstance(obj, (bytes, str)):
        # accept both possible types
        return 'string'

    if isinstance(obj, list):
        try:
            obj = obj[0]
        except IndexError:
            raise ValueError("Cannot determine CIM data type from empty array")
        return cimtype(obj)

    if isinstance(obj, (datetime, timedelta)):
        return 'datetime'

    # Defer import due to circular import dependencies:
    # pylint: disable=import-outside-toplevel
    from pywbem._cim_obj import CIMInstanceName as instancename_type

    if isinstance(obj, instancename_type):
        return 'reference'

    # Defer import due to circular import dependencies:
    # pylint: disable=import-outside-toplevel
    from pywbem._cim_obj import CIMInstance as instance_type

    if isinstance(obj, instance_type):  # embedded instance
        return 'string'

    # Defer import due to circular import dependencies:
    # pylint: disable=import-outside-toplevel
    from pywbem._cim_obj import CIMClass as class_type

    if isinstance(obj, class_type):  # embedded class
        return 'string'

    raise TypeError(
        _format("Object does not have a valid CIM data type: {0!A}", obj))


_TYPE_FROM_NAME = {
    'boolean': bool,
    'string': str,  # return the preferred type
    'char16': str,  # return the preferred type
    'datetime': CIMDateTime,
    # 'reference' covered at run time
    'uint8': Uint8,
    'uint16': Uint16,
    'uint32': Uint32,
    'uint64': Uint64,
    'sint8': Sint8,
    'sint16': Sint16,
    'sint32': Sint32,
    'sint64': Sint64,
    'real32': Real32,
    'real64': Real64,
}


def type_from_name(type_name):
    """
    Return the Python type object for a given CIM data type name.

    For example, type name ``"uint8"`` will return type object
    :class:`~pywbem.Uint8`.

    For CIM data type names ``"string"`` and ``"char16"``, the
    :term:`unicode string` type is returned (Unicode strings are the preferred
    representation for these CIM data types).

    The returned type can be used as a constructor from a differently typed
    input value in many cases. Notable limitations are:

    * In Python 3, the :class:`py3:str` type is used to represent CIM string
      data types. When constructing such an object from a byte string, the
      resulting string is not a unicode-translated version of the byte string
      as one would assume (and as is the case in Python 2), but instead that
      results in a unicode string that is a `repr()` representation of the
      byte string::

          string_type = type_from_name('string')  # str
          s1 = b'abc'
          s2 = string_type(s1)  # results in u"b'abc'", and not in u"abc"

      Use `decode()` and `encode()` for strings instead of type conversion
      syntax (in both Python 2 and 3, for consistency).

    * For CIM type "reference", type object :class:`~pywbem.CIMInstanceName`
      is returned, even though for use in CIM method parameters,
      :class:`~pywbem.CIMClassName` is also valid.

    Parameters:

      type_name (:term:`string`):
        The simple (=non-array) CIM data type name (e.g. ``"uint8"`` or
        ``"reference"``).

    Returns:

        The Python type object for the CIM data type (e.g.
        :class:`~pywbem.Uint8` or :class:`~pywbem.CIMInstanceName`).

    Raises:

        ValueError: Unknown CIM data type name.
    """
    if type_name == 'reference':
        # Defer import due to circular import dependencies:
        # pylint: disable=import-outside-toplevel
        from ._cim_obj import CIMInstanceName
        return CIMInstanceName
    try:
        type_obj = _TYPE_FROM_NAME[type_name]
    except KeyError:
        raise ValueError(
            _format("Unknown CIM data type name: {0!A}", type_name))
    return type_obj


def atomic_to_cim_xml(obj):
    """
    Convert an "atomic" scalar value to a CIM-XML string and return that
    string.

    The returned CIM-XML string is ready for use as the text of a CIM-XML
    'VALUE' element.

    Parameters:

      obj (:term:`CIM data type`, :term:`number`, :class:`py:datetime`):
        The "atomic" input value. May be `None`.

        Must not be an array/list/tuple. Must not be a :ref:`CIM object`.

    Returns:

        A :term:`unicode string` object in CIM-XML value format representing
        the input value. `None`, if the input value is `None`.

    Raises:

        TypeError
    """
    if obj is None:  # pylint: disable=no-else-return
        return obj
    elif isinstance(obj, str):
        return obj
    elif isinstance(obj, bytes):
        return _to_unicode(obj)
    elif isinstance(obj, bool):
        return 'TRUE' if obj else 'FALSE'
    elif isinstance(obj, (CIMInt, int, CIMDateTime)):
        return str(obj)
    elif isinstance(obj, datetime):
        return str(CIMDateTime(obj))
    elif isinstance(obj, Real32):
        # DSP0201 requirements for representing real32:
        # The significand must be represented with at least 11 digits.
        # The special values must have the case: INF, -INF, NaN.
        s = f'{obj:.11G}'
        if s == 'NAN':
            s = 'NaN'
        elif s in ('INF', '-INF'):
            pass
        elif '.' not in s:
            parts = s.split('E')
            parts[0] = parts[0] + '.0'
            s = 'E'.join(parts)
        return s
    elif isinstance(obj, (Real64, float)):
        # DSP0201 requirements for representing real64:
        # The significand must be represented with at least 17 digits.
        # The special values must have the case: INF, -INF, NaN.
        s = f'{obj:.17G}'
        if s == 'NAN':
            s = 'NaN'
        elif s in ('INF', '-INF'):
            pass
        elif '.' not in s:
            parts = s.split('E')
            parts[0] = parts[0] + '.0'
            s = 'E'.join(parts)
        return s
    else:
        raise TypeError(
            _format("Value {0!A} has invalid type {1} for conversion to a "
                    "CIM-XML string", obj, type(obj)))
