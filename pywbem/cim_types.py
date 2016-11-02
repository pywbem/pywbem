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

Note that constructors of pywbem classes that take CIM typed values as input
may support Python types in addition to those shown above. For example, the
:class:`~pywbem.CIMProperty` class represents property values of CIM datetime
type internally as :class:`~pywbem.CIMDateTime` objects, but its constructor
accepts :class:`py:datetime.timedelta` objects, :class:`py:datetime.datetime`
objects, :term:`string`, in addition to
:class:`~pywbem.CIMDateTime` objects.
"""
# pylint: enable=line-too-long
# Note: When used before module docstrings, Pylint scopes the disable statement
#       to the whole rest of the file, so we need an enable statement.

# This module is meant to be safe for 'import *'.

from __future__ import absolute_import

from datetime import tzinfo, datetime, timedelta
import re
import warnings
import six

from . import config

if six.PY2:
    _Longint = long  # noqa: F821
else:
    _Longint = int


__all__ = ['MinutesFromUTC', 'CIMType', 'CIMDateTime', 'CIMInt', 'Uint8',
           'Sint8', 'Uint16', 'Sint16', 'Uint32', 'Sint32', 'Uint64', 'Sint64',
           'CIMFloat', 'Real32', 'Real64']


class _CIMComparisonMixin(object):  # pylint: disable=too-few-public-methods
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

    @staticmethod
    def __ordering_deprecated():
        """Deprecated warning for pywbem CIM Objects"""
        warnings.warn(
            "Ordering comparisons for pywbem CIM objects are deprecated",
            DeprecationWarning)

    def __lt__(self, other):
        """
        Invoked when two CIM objects are compared with the `<` operator.

        The comparison is delegated to the `_cmp()` method.
        """
        self.__ordering_deprecated()
        return self._cmp(other) < 0

    def __gt__(self, other):
        """
        Invoked when two CIM objects are compared with the `>` operator.

        The comparison is delegated to the `_cmp()` method.
        """
        self.__ordering_deprecated()
        return self._cmp(other) > 0

    def __le__(self, other):
        """
        Invoked when two CIM objects are compared with the `<=` operator.

        The comparison is delegated to the `_cmp()` method.
        """
        self.__ordering_deprecated()
        return self._cmp(other) <= 0

    def __ge__(self, other):
        """
        Invoked when two CIM objects are compared with the `>=` operator.

        The comparison is delegated to the `_cmp()` method.
        """
        self.__ordering_deprecated()
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
        self.__offset = timedelta(minutes=offset)

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
        return self.__offset

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


class CIMType(object):  # pylint: disable=too-few-public-methods
    """Base type for all CIM data types defined in this package."""

    # Note: __str__() is not needed; the inherited method is used,
    # even though there is a __repr__() method here.

    #: The name of the CIM datatype, as a :term:`string`. See
    #: :ref:`CIM data types` for details.
    cimtype = None

    def __repr__(self):
        """Return a string representation suitable for debugging."""

        return '%s(cimtype=%r, %s)' % \
               (self.__class__.__name__, self.cimtype, self)


class CIMDateTime(CIMType, _CIMComparisonMixin):
    """
    A value of CIM data type datetime.

    The object represents either a timezone-aware point in time, or a time
    interval.
    """

    cimtype = 'datetime'

    def __init__(self, dtarg):
        """
        Parameters:

          dtarg:
            The value from which the object is initialized, as one of the
            following types:

            * A :term:`string` object will be
              interpreted as CIM datetime format (see :term:`DSP0004`) and
              will result in a point in time or a time interval.
            * A :class:`py:datetime.datetime` object must be timezone-aware
              (see :class:`~pywbem.MinutesFromUTC`) and will result in a point
              in time.
            * A :class:`py:datetime.timedelta` object will result in a time
              interval.
            * Another :class:`~pywbem.CIMDateTime` object will be copied.
        """
        from .cim_obj import _ensure_unicode  # defer due to cyclic deps.
        self.__timedelta = None
        self.__datetime = None
        dtarg = _ensure_unicode(dtarg)
        if isinstance(dtarg, six.text_type):
            date_pattern = re.compile(
                r'^(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})\.'
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
                    raise ValueError('dtarg argument "%s" has invalid field '
                                     'values for CIM datetime timestamp '
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
                    raise ValueError('dtarg argument "%s" has an invalid CIM '
                                     'datetime format' % dtarg)
        elif isinstance(dtarg, datetime):
            self.__datetime = dtarg
        elif isinstance(dtarg, timedelta):
            self.__timedelta = dtarg
        elif isinstance(dtarg, CIMDateTime):
            # pylint: disable=protected-access
            self.__datetime = dtarg.__datetime
            # pylint: disable=protected-access
            self.__timedelta = dtarg.__timedelta
        else:
            raise TypeError('dtarg argument "%s" has an invalid type: %s '
                            '(expected datetime, timedelta, string, or '
                            'CIMDateTime)' % (dtarg, type(dtarg)))

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
        return offset

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
        utc = datetime.utcnow()
        local = datetime.now()
        if local < utc:
            return - int(float((utc - local).seconds) / 60 + .5)
        else:
            return int(float((local - utc).seconds) / 60 + .5)

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
        if self.is_interval:
            hour = self.timedelta.seconds // 3600
            minute = (self.timedelta.seconds - hour * 3600) // 60
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
        """Return a string representation suitable for debugging."""

        return '%s(cimtype=%r, %r)' % \
               (self.__class__.__name__, self.cimtype, str(self))

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
    """
    Base type for CIM integer data types. Derived from :class:`~pywbem.CIMType`
    and :class:`py:int` (for Python 3) or :class:`py:long` (for Python 2).

    This class has a concept of a valid range for the represented integer,
    based upon the capability of the CIM data type as defined in
    :term:`DSP0004`. The additional constraints defined by possible MinValue
    or MaxValue qualifiers are not taken into account at this level.

    The valid value range is enforced when an instance of a subclass of this
    class (e.g. :class:`~pywbem.Uint8`) is created. Values outside of the
    valid range raise a :exc:`ValueError`.
    The enforcement of the valid value range can be disabled via the
    configuration variable :data:`~pywbem.config.ENFORCE_INTEGER_RANGE`.

    Instances of subclasses of this class can be initialized with the usual
    input arguments supported by :term:`integer`, for example:

    ::

        >>> pywbem.Uint8(42)
        Uint8(cimtype='uint8', 42)

        >>> pywbem.Uint8('42')
        Uint8(cimtype='uint8', 42)

        >>> pywbem.Uint8('2A', 16)
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

    #: The minimum valid value for the integer, according to the capabilities
    #: of its CIM data type. See :ref:`CIM data types` for a list of CIM
    #: integer data types.
    minvalue = None

    #: The maximum valid value for the integer, according to the capabilities
    #: of its CIM data type. See :ref:`CIM data types` for a list of CIM
    #: integer data types.
    maxvalue = None

    def __new__(cls, *args, **kwargs):
        value = _Longint(*args, **kwargs)
        if config.ENFORCE_INTEGER_RANGE:
            if value > cls.maxvalue or value < cls.minvalue:
                raise ValueError("Integer value %s is out of range for CIM "
                                 "datatype %s" % (value, cls.cimtype))
        # The value needs to be processed here, because int/long is unmutable
        return super(CIMInt, cls).__new__(cls, *args, **kwargs)

    def __repr__(self):
        """Return a string representation suitable for debugging."""

        return '%s(cimtype=%r, minvalue=%s, maxvalue=%s, %s)' % \
               (self.__class__.__name__, self.cimtype, self.minvalue,
                self.maxvalue, self)


class Uint8(CIMInt):
    """
    A value of CIM data type uint8. Derived from :class:`~pywbem.CIMInt`.

    For details on CIM integer data types, see :class:`~pywbem.CIMInt`.
    """
    cimtype = 'uint8'
    minvalue = 0
    maxvalue = 2**8 - 1


class Sint8(CIMInt):
    """
    A value of CIM data type sint8. Derived from :class:`~pywbem.CIMInt`.

    For details on CIM integer data types, see :class:`~pywbem.CIMInt`.
    """
    cimtype = 'sint8'
    minvalue = -2 ** (8 - 1)
    maxvalue = 2 ** (8 - 1) - 1


class Uint16(CIMInt):
    """
    A value of CIM data type uint16. Derived from :class:`~pywbem.CIMInt`.

    For details on CIM integer data types, see :class:`~pywbem.CIMInt`.
    """
    cimtype = 'uint16'
    minvalue = 0
    maxvalue = 2**16 - 1


class Sint16(CIMInt):
    """
    A value of CIM data type sint16. Derived from :class:`~pywbem.CIMInt`.

    For details on CIM integer data types, see :class:`~pywbem.CIMInt`.
    """
    cimtype = 'sint16'
    minvalue = -2 ** (16 - 1)
    maxvalue = 2 ** (16 - 1) - 1


class Uint32(CIMInt):
    """
    A value of CIM data type uint32. Derived from :class:`~pywbem.CIMInt`.

    For details on CIM integer data types, see :class:`~pywbem.CIMInt`.
    """
    cimtype = 'uint32'
    minvalue = 0
    maxvalue = 2 ** 32 - 1


class Sint32(CIMInt):
    """
    A value of CIM data type sint32. Derived from :class:`~pywbem.CIMInt`.

    For details on CIM integer data types, see :class:`~pywbem.CIMInt`.
    """
    cimtype = 'sint32'
    minvalue = -2 ** (32 - 1)
    maxvalue = 2 ** (32 - 1) - 1


class Uint64(CIMInt):
    """
    A value of CIM data type uint64. Derived from :class:`~pywbem.CIMInt`.

    For details on CIM integer data types, see :class:`~pywbem.CIMInt`.
    """
    cimtype = 'uint64'
    minvalue = 0
    maxvalue = 2 ** 64 - 1


class Sint64(CIMInt):
    """
    A value of CIM data type sint64. Derived from :class:`~pywbem.CIMInt`.

    For details on CIM integer data types, see :class:`~pywbem.CIMInt`.
    """
    cimtype = 'sint64'
    minvalue = -2 ** (64 - 1)
    maxvalue = 2 ** (64 - 1) - 1


# CIM float types


class CIMFloat(CIMType, float):
    """
    Base type for real (floating point) CIM data types.
    """


class Real32(CIMFloat):
    """
    A value of CIM data type real32. Derived from :class:`~pywbem.CIMFloat`.
    """
    cimtype = 'real32'


class Real64(CIMFloat):
    """
    A value of CIM data type real64. Derived from :class:`~pywbem.CIMFloat`.
    """
    cimtype = 'real64'


def cimtype(obj):
    """
    Return the CIM data type name of a CIM typed object, as a string.

    For an array, the type is determined from the first array element
    (CIM arrays must be homogeneous w.r.t. the type of their elements).

    Parameters:

      obj (:term:`CIM data type`):
        The object whose CIM data type name is returned.

    Returns:

        The CIM data type name of the object, as a string (e.g. ``"uint8"``).

    Raises:
        TypeError: Type is not a CIM data type.
        ValueError: Cannot determine CIM data type from an empty array.
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
            raise ValueError(
                "Cannot determine CIM data type from an empty array")
        return cimtype(obj[0])
    if isinstance(obj, (datetime, timedelta)):
        return 'datetime'
    raise TypeError("Type %s of this object is not a CIM data type: %r" %
                    (type(obj), obj))


_TYPE_FROM_NAME = {
    'boolean': bool,
    'string': six.text_type,  # return the preferred type
    'char16': six.text_type,  # return the preferred type
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

    For example, type name "uint8" will return type object
    :class:`~pywbem.Uint8`.

    For CIM data type names ``"string"`` and ``"char16"``, the
    :term:`unicode string` type is returned (Unicode strings are the preferred
    representation for these CIM data types).

    Parameters:

      type_name : string
        The simple (=non-array) CIM data type name (e.g. ``"uint8"`` or
        ``"reference"``).

    Returns:

        The Python type object for the CIM data type (e.g.
        :class:`~pywbem.Uint8` or :class:`~pywbem.CIMInstanceName`).

    Raises:
        ValueError: Unknown CIM data type name.
    """
    if type_name == 'reference':
        # move import to run time to avoid circular imports
        from .cim_obj import CIMInstanceName
        return CIMInstanceName
    try:
        type_obj = _TYPE_FROM_NAME[type_name]
    except KeyError:
        raise ValueError("Unknown CIM data type name: %r" % type_name)
    return type_obj


def atomic_to_cim_xml(obj):
    """
    Convert a value of an atomic scalar CIM data type to a CIM-XML string and
    return that string.

    TODO: Verify whether we can change this function to raise a ValueError in
    case the value is not CIM typed.

    Parameters:

      obj (atomic scalar CIM typed value):
        The CIM typed value, including `None`. Must be a scalar (not an array).
        Must be an atomic type (i.e. those listed in :ref:`CIM data types`,
        except any :ref:`CIM objects`).

    Returns:

        A :term:`unicode string` object in CIM-XML value format representing
        the CIM typed value. For a value of `None`, `None` is returned.
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
    else:  # e.g. int
        return _convert_unicode(obj)
