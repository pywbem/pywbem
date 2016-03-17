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

"""
Types to represent CIM typed values, and related conversion functions.

The following table shows how CIM typed values are represented as Python
objects:

=========================  ===========================
CIM type                   Python type
=========================  ===========================
boolean                    `bool`
char16                     unicode string or binary bytes, see (1)
string                     unicode string or binary bytes, see (1)
string (EmbeddedInstance)  `CIMInstance`
string (EmbeddedObject)    `CIMInstance` or `CIMClass`
datetime                   `CIMDateTime`
reference                  `CIMInstanceName`
uint8                      `Uint8`
uint16                     `Uint16`
uint32                     `Uint32`
uint64                     `Uint64`
sint8                      `Sint8`
sint16                     `Sint16`
sint32                     `Sint32`
sint64                     `Sint64`
real32                     `Real32`
real64                     `Real64`
[] (array)                 `list`
=========================  ===========================

(1) CIM string and char16 types are represented as follows:
In Python 2 as `unicode` (preferred) or `str`; in Python 3 as `str` (preferred)
or `bytes`. The implementation may decode binary bytes types offered at the
interface to unicode text types in the internal representation, using "utf-8"
encoding.

Note that constructors of PyWBEM classes that take CIM typed values as input
may support Python types in addition to those shown above. For example, the
`CIMProperty` class represents CIM datetime values internally as a
`CIMDateTime` object, but its constructor accepts `datetime.timedelta`,
`datetime.datetime`, `str`, and `unicode` (py2 only) objects in addition to
`CIMDateTime` objects.
"""

# This module is meant to be safe for 'import *'.

from datetime import tzinfo, datetime, timedelta
import re
import six
if six.PY2:
    _Longint = long
else:
    _Longint = int

__all__ = ['MinutesFromUTC', 'CIMType', 'CIMDateTime', 'CIMInt', 'Uint8',
           'Sint8', 'Uint16', 'Sint16', 'Uint32', 'Sint32', 'Uint64', 'Sint64',
           'CIMFloat', 'Real32', 'Real64']

class _CIMComparisonMixin(object): #pylint: disable=too-few-public-methods
    """Mixin class providing default implementations for rich comparison
    operators.

    In Python 2, the rich comparison operators (e.g. `__eq__()`) have
    precedence over the traditional comparator method (`_cmp__()`).
    In Python 3, the comparator method (`_cmp__()`) no longer exists.
    Therefore, implementing the rich comparison operators works in both.

    The default implementations delegate to a comparator method `_cmp()`
    implemented by subclasses. This requires that the subclasses can
    define total ordering. (If they cannot, this mixin class cannot be
    used).
    """

    def __eq__(self, other):
        """
        Invoked when two CIM objects are compared with the `==` operator.

        The comparison is delegated to the `_cmp()` method.
        """
        return self._cmp(other) == 0

    def __ne__(self, other):
        """
        Invoked when two CIM objects are compared with the `!=` operator.

        The comparison is delegated to the `_cmp()` method.
        """
        return self._cmp(other) != 0

    def __lt__(self, other):
        """
        Invoked when two CIM objects are compared with the `<` operator.

        The comparison is delegated to the `_cmp()` method.
        """
        return self._cmp(other) < 0

    def __gt__(self, other):
        """
        Invoked when two CIM objects are compared with the `>` operator.

        The comparison is delegated to the `_cmp()` method.
        """
        return self._cmp(other) > 0

    def __le__(self, other):
        """
        Invoked when two CIM objects are compared with the `<=` operator.

        The comparison is delegated to the `_cmp()` method.
        """
        return self._cmp(other) <= 0

    def __ge__(self, other):
        """
        Invoked when two CIM objects are compared with the `>=` operator.

        The comparison is delegated to the `_cmp()` method.
        """
        return self._cmp(other) >= 0

    def _cmp(self, other):
        """
        Interface definition for comparator method to be provided by
        subclasses, as follows:
        * If self == other, 0 must be returned.
        * If self < other, -1 must be returned.
        * If self > other, +1 must be returned.
        """
        raise NotImplementedError


class MinutesFromUTC(tzinfo):

    """
    A `datetime.tzinfo` implementation defined using a fixed offset in +/-
    minutes from UTC.
    """

    def __init__(self, offset): # pylint: disable=super-init-not-called
        """
        Initialize the `MinutesFromUTC` object from a timezone offset.

        :Parameters:

          offset : `int`
            Timezone offset in +/- minutes from UTC, where a positive value
            indicates minutes east of UTC, and a negative value indicates
            minutes west of UTC.
        """
        self.__offset = timedelta(minutes=offset)

    def utcoffset(self, dt): # pylint: disable=unused-argument
        """
        Implement the `datetime.tzinfo.utcoffset` method by returning
        the timezone offset as a `datetime.timedelta` object.
        """
        return self.__offset

    def dst(self, dt): # pylint: disable=unused-argument
        """
        Implement the `datetime.tzinfo.dst` method by returning
        a DST value of 0 as a `datetime.timedelta` object.
        """
        return timedelta(0)

class CIMType(object):       # pylint: disable=too-few-public-methods
    """Base type for numeric and datetime CIM types."""

class CIMDateTime(CIMType, _CIMComparisonMixin):
    """
    A value of CIM type datetime.

    The object represents either a timezone-aware point in time, or a time
    interval.
    """

    def __init__(self, dtarg):
        """
        Initialize the `CIMDateTime` object from different types of input
        object.

        :Parameters:

          dtarg
            The input object, as one of the following types:
            * A Unicode string or UTF-8 encoded byte string will be interpreted
              as CIM datetime format (see DSP0004) and will result in a point
              in time or a time interval.
            * A `datetime.datetime` object must be timezone-aware and will
              result in a point in time.
            * A `datetime.timedelta` object will result in a time interval.
            * Another `CIMDateTime` object will be copied.

        :Raises:
          :raise ValueError:
          :raise TypeError:
        """
        from .cim_obj import _ensure_unicode # defer due to cyclic deps.
        self.cimtype = 'datetime'
        self.__timedelta = None
        self.__datetime = None
        dtarg = _ensure_unicode(dtarg)
        if isinstance(dtarg, six.text_type):
            date_pattern = re.compile(
                r'^(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})\.' \
                r'(\d{6})([+|-])(\d{3})')
            srch_result = date_pattern.search(dtarg)
            if srch_result is not None:
                parts = srch_result.groups()
                offset = int(parts[8])
                if parts[7] == '-':
                    offset = -offset
                try:
                    self.__datetime = datetime(int(parts[0]), int(parts[1]),
                                               int(parts[2]), int(parts[3]),
                                               int(parts[4]), int(parts[5]),
                                               int(parts[6]),
                                               MinutesFromUTC(offset))
                except ValueError as exc:
                    raise ValueError('dtarg argument "%s" has invalid field '\
                                     'values for CIM datetime timestamp '\
                                     'format: %s' % (dtarg, exc))
            else:
                tv_pattern = re.compile(
                    r'^(\d{8})(\d{2})(\d{2})(\d{2})\.(\d{6})(:)(000)')
                srch_result = tv_pattern.search(dtarg)
                if srch_result is not None:
                    parts = srch_result.groups()
                    # Because the input values are limited by the matched
                    # pattern, timedelta() never throws any exception.
                    self.__timedelta = timedelta(days=int(parts[0]),
                                                 hours=int(parts[1]),
                                                 minutes=int(parts[2]),
                                                 seconds=int(parts[3]),
                                                 microseconds=int(parts[4]))
                else:
                    raise ValueError('dtarg argument "%s" has an invalid CIM '\
                                     'datetime format' % dtarg)
        elif isinstance(dtarg, datetime):
            self.__datetime = dtarg
        elif isinstance(dtarg, timedelta):
            self.__timedelta = dtarg
        elif isinstance(dtarg, CIMDateTime):
            self.__datetime = dtarg.__datetime   # pylint: disable=protected-access
            self.__timedelta = dtarg.__timedelta # pylint: disable=protected-access
        else:
            raise TypeError('dtarg argument "%s" has an invalid type: %s '\
                            '(expected datetime, timedelta, string, or '\
                            'CIMDateTime)' % (dtarg, type(dtarg)))

    @property
    def minutes_from_utc(self):
        """
        The timezone offset of a point in time object as +/- minutes from UTC.

        A positive value of the timezone offset indicates minutes east of UTC,
        and a negative value indicates minutes west of UTC.

        0, if the object represents a time interval.
        """
        offset = 0
        if self.__datetime is not None and \
                self.__datetime.utcoffset() is not None:
            offset = self.__datetime.utcoffset().seconds / 60
            if self.__datetime.utcoffset().days == -1:
                offset = -(60*24 - offset)
        return offset

    @property
    def datetime(self):
        """
        The point in time represented by the object, as a `datetime.datetime`
        object.

        `None` if the object represents a time interval.
        """
        return self.__datetime

    @property
    def timedelta(self):
        """
        The time interval represented by the object, as a `datetime.timedelta`
        object.

        `None` if the object represents a point in time.
        """
        return self.__timedelta

    @property
    def is_interval(self):
        """
        A boolean indicating whether the object represents a time interval
        (`True`) or a point in time (`False`).
        """
        return self.__timedelta is not None

    @staticmethod
    def get_local_utcoffset():
        """
        Return the timezone offset of the current local timezone from UTC.

        A positive value indicates minutes east of UTC, and a negative
        value indicates minutes west of UTC.
        """
        utc = datetime.utcnow()
        local = datetime.now()
        if local < utc:
            return - int(float((utc - local).seconds) / 60 + .5)
        else:
            return int(float((local - utc).seconds) / 60 + .5)

    @classmethod
    def now(cls, tzi=None):
        """
        Factory method that returns a new `CIMDateTime` object representing
        the current date and time.

        The optional timezone information is used to convert the CIM datetime
        value into the desired timezone. That does not change the point in time
        that is represented by the value, but it changes the value of the
        `hhmmss` components of the CIM datetime value to compensate for changes
        in the timezone offset component.

        :Parameters:

          tzi : `datetime.tzinfo`
            Timezone information. `None` means that the current local timezone
            is used. The `datetime.tzinfo` object may be a `MinutesFromUTC`
            object.

        :Returns:

            A new `CIMDateTime` object representing the current date and time.
        """
        if tzi is None:
            tzi = MinutesFromUTC(cls.get_local_utcoffset())
        return cls(datetime.now(tzi))

    @classmethod
    def fromtimestamp(cls, ts, tzi=None):
        # pylint: disable=invalid-name
        """
        Factory method that returns a new `CIMDateTime` object from a POSIX
        timestamp value and optional timezone information.

        A POSIX timestamp value is the number of seconds since 1970-01-01
        00:00:00 UTC. Thus, a POSIX timestamp value is unambiguous w.r.t. the
        timezone.

        The optional timezone information is used to convert the CIM datetime
        value into the desired timezone. That does not change the point in time
        that is represented by the value, but it changes the value of the
        `hhmmss` components of the CIM datetime value to compensate for changes
        in the timezone offset component.

        :Parameters:

          ts : `int`
            POSIX timestamp value.

          tzi : `datetime.tzinfo`
            Timezone information. `None` means that the current local timezone
            is used. The `datetime.tzinfo` object may be a `MinutesFromUTC`
            object.

        :Returns:

            A new `CIMDateTime` object representing the specified point in
            time.
        """
        if tzi is None:
            tzi = MinutesFromUTC(cls.get_local_utcoffset())
        return cls(datetime.fromtimestamp(ts, tzi))

    def __str__(self):
        """
        Return a string representing the object in CIM datetime format.
        """
        if self.is_interval:
            hour = self.timedelta.seconds / 3600
            minute = (self.timedelta.seconds - hour * 3600) / 60
            second = self.timedelta.seconds - hour * 3600 - minute * 60
            return '%08d%02d%02d%02d.%06d:000' % \
                    (self.timedelta.days, hour, minute, second,
                     self.timedelta.microseconds)
        else:
            offset = self.minutes_from_utc
            sign = '+'
            if offset < 0:
                sign = '-'
                offset = -offset
            return '%d%02d%02d%02d%02d%02d.%06d%s%03d' % \
                   (self.datetime.year, self.datetime.month,
                    self.datetime.day, self.datetime.hour,
                    self.datetime.minute, self.datetime.second,
                    self.datetime.microsecond, sign, offset)

    def __repr__(self):
        return '%s(\'%s\')' % (self.__class__.__name__, str(self))

    def __getstate__(self):
        return str(self)

    def __setstate__(self, arg):
        self.__init__(arg)

    def _cmp(self, other):
        from .cim_obj import cmpitem  # defer due to cyclic deps.
        if self is other:
            return 0
        elif not isinstance(other, CIMDateTime):
            return 1
        return (cmpitem(self.datetime, other.datetime) or
                cmpitem(self.timedelta, other.timedelta))

# CIM integer types

class CIMInt(CIMType, _Longint):
    """Base type for integer CIM types."""

class Uint8(CIMInt):
    """A value of CIM type uint8."""
    cimtype = 'uint8'

class Sint8(CIMInt):
    """A value of CIM type sint8."""
    cimtype = 'sint8'

class Uint16(CIMInt):
    """A value of CIM type uint16."""
    cimtype = 'uint16'

class Sint16(CIMInt):
    """A value of CIM type sint16."""
    cimtype = 'sint16'

class Uint32(CIMInt):
    """A value of CIM type uint32."""
    cimtype = 'uint32'

class Sint32(CIMInt):
    """A value of CIM type sint32."""
    cimtype = 'sint32'

class Uint64(CIMInt):
    """A value of CIM type uint64."""
    cimtype = 'uint64'

class Sint64(CIMInt):
    """A value of CIM type sint64."""
    cimtype = 'sint64'

# CIM float types

class CIMFloat(CIMType, float):
    """Base type for real (floating point) CIM types."""

class Real32(CIMFloat):
    """A value of CIM type real32."""
    cimtype = 'real32'

class Real64(CIMFloat):
    """A value of CIM type real64."""
    cimtype = 'real64'

def cimtype(obj):
    """
    Return the CIM type name of a value, as a string.

    For an array, the type is determined from the first array element because
    CIM arrays must be homogeneous. If the array is empty, ValueError is
    raised.

    If the type of the value is not a CIM type, TypeError is raised.

    :Parameters:

      obj : CIM typed value
        The value whose CIM type name is returned.

    :Returns:

        The CIM type name of the value, as a string.

    :Raises:

        :raise TypeError:
            Type is not a CIM type.

        :raise ValueError:
            Cannot determine CIM type from empty array.
    """
    if isinstance(obj, CIMType):
        return obj.cimtype
    if isinstance(obj, bool):
        return 'boolean'
    if isinstance(obj, (six.binary_type, six.text_type)):
        # accept both possible types
        return 'string'
    if isinstance(obj, list):
        if len(obj) == 0:
            raise ValueError("Cannot determine CIM type from empty array")
        return cimtype(obj[0])
    if isinstance(obj, (datetime, timedelta)):
        return 'datetime'
    raise TypeError("Type %s of this value is not a CIM type: %r" % \
                    (type(obj), obj))

_TYPE_FROM_NAME = {
    'boolean': bool,
    'string': six.text_type, # return the preferred type
    'char16': six.text_type, # return the preferred type
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
    Return the Python type object for a given CIM type name.

    For example, type name `'uint8'` will return type `Uint8`.

    For CIM types `string` and `char16`, the preferred Python type
    for unicode text representation is returned.

    :Parameters:

      type_name : string
        The simple (=non-array) CIM type name (e.g. `'uint8'` or
        `'reference'`).

    :Returns:

        The Python type object for the CIM type (e.g. `Uint8` or
        `CIMInstanceName`).

    :Raises:

      :raise ValueError:
        Unknown CIM type name.
    """
    if type_name == 'reference':
        # move import to run time to avoid circular imports
        from .cim_obj import CIMInstanceName
        return CIMInstanceName
    try:
        type_obj = _TYPE_FROM_NAME[type_name]
    except KeyError:
        raise ValueError("Unknown CIM type name: %r" % type_name)
    return type_obj

def atomic_to_cim_xml(obj):
    """
    Convert a value of an atomic scalar CIM type to a CIM-XML Unicode string
    and return that string.

    TODO: Verify whether we can change this function to raise a ValueError in
    case the value is not CIM typed.

    :Parameters:

      obj : CIM typed value.
        The CIM typed value`, including `None`. Must be a scalar. Must be an
        atomic type (i.e. not `CIMInstance` or `CIMClass`).

    :Returns:

        A Unicode string in CIM-XML value format representing the CIM typed
        value. For a value of `None`, `None` is returned.
    """
    # pylint: disable=too-many-return-statements
    from .cim_obj import _ensure_unicode, _convert_unicode  # due to cycles
    if isinstance(obj, bool):
        if obj:
            return u"true"
        else:
            return u"false"
    elif isinstance(obj, CIMDateTime):
        return six.text_type(obj)
    elif isinstance(obj, datetime):
        return six.text_type(CIMDateTime(obj))
    elif obj is None:
        return obj
    elif cimtype(obj) == 'real32':
        return u'%.8E' % obj
    elif cimtype(obj) == 'real64':
        return u'%.16E' % obj
    elif isinstance(obj, six.string_types):
        return _ensure_unicode(obj)
    else: # e.g. int
        return _convert_unicode(obj)
