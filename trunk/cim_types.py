#
# (C) Copyright 2003, 2004 Hewlett-Packard Development Company, L.P.
# (C) Copyright 2006, 2007 Novell, Inc. 
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as
# published by the Free Software Foundation; version 2 of the License.
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

"""
Subclasses of builtin Python types to remember CIM types.  This is
necessary as we need to remember whether an integer property is a
uint8, uint16, uint32 etc, while still being able to treat it as a
integer.
"""

from datetime import tzinfo, datetime, timedelta
import re

class MinutesFromUTC(tzinfo):
    """Fixed offset in minutes from UTC."""
    def __init__(self, offset):
        self.__offset = timedelta(minutes = offset)
    def utcoffset(self, dt):
        return self.__offset
    def dst(self, dt):
        return timedelta(0)

class CIMType(object):
    """Base type for all CIM types."""
    
class CIMDateTime(CIMType) :
    """A CIM DateTime."""

    def __init__(self, dtarg):
        """Construct a new CIMDateTime

        Arguments:
        dtarg -- Can be a string in CIM datetime format, a datetime.datetime, 
            or a datetime.timedelta. 

        """

        self.cimtype = 'datetime'
        self.__timedelta = None
        self.__datetime = None
        if isinstance(dtarg, basestring):
            date_pattern = re.compile(r'^(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})\.(\d{6})([+|-])(\d{3})')
            s = date_pattern.search(dtarg)
            if s is not None:
                g = s.groups()
                offset = int(g[8])
                if g[7] == '-':
                    offset = -offset
                self.__datetime = datetime(int(g[0]), int(g[1]), 
                                           int(g[2]), int(g[3]), 
                                           int(g[4]), int(g[5]), 
                                           int(g[6]), MinutesFromUTC(offset))
            else:
                tv_pattern = re.compile(r'^(\d{8})(\d{2})(\d{2})(\d{2})\.(\d{6})(:)(000)')
                s = tv_pattern.search(dtarg)
                if s is None:
                    raise ValueError('Invalid Datetime format "%s"' % dtarg)
                else:
                    g = s.groups()
                    self.__timedelta =  timedelta(days=int(g[0]),
                                                  hours=int(g[1]),
                                                  minutes=int(g[2]),
                                                  seconds=int(g[3]),
                                                  microseconds=int(g[4]))
        elif isinstance(dtarg, datetime):
            self.__datetime = dtarg; 
        elif isinstance(dtarg, timedelta):
            self.__timedelta = dtarg
        elif isinstance(dtarg, CIMDateTime):
            self.__datetime = dtarg.__datetime
            self.__timedelta = dtarg.__timedelta
        else:
            raise ValueError('Expected datetime, timedelta, or string')

    @property
    def minutes_from_utc(self):
        """Return the timezone as +/- minutes from UTC"""
        offset = 0
        if self.__datetime is not None and \
                self.__datetime.utcoffset() is not None:
            offset = self.__datetime.utcoffset().seconds / 60
            if self.__datetime.utcoffset().days == -1:
                offset = -(60*24 - offset)
        return offset

    @property
    def datetime(self):
        return self.__datetime

    @property
    def timedelta(self):
        return self.__timedelta

    @property
    def is_interval(self):
        return self.__timedelta is not None

    @staticmethod
    def get_local_utcoffset():
        """Return minutes +/- UTC for the local timezone"""
        utc = datetime.utcnow()
        local = datetime.now()
        if local < utc:
            return - int(float((utc - local).seconds) / 60 + .5)
        else:
            return int(float((local - utc).seconds) / 60 + .5)

    @classmethod
    def now(cls, tzi=None):
        if tzi is None:
            tzi = MinutesFromUTC(cls.get_local_utcoffset())
        return cls(datetime.now(tzi))

    @classmethod
    def fromtimestamp(cls, ts, tzi=None):
        if tzi is None:
            tzi = MinutesFromUTC(cls.get_local_utcoffset())
        return cls(datetime.fromtimestamp(ts, tzi))

    def __str__ (self):
        if self.is_interval:
            hour = self.__timedelta.seconds / 3600
            minute = (self.__timedelta.seconds - hour * 3600) / 60
            second = self.__timedelta.seconds - hour * 3600 - minute * 60
            return '%08d%02d%02d%02d.%06d:000' % \
                    (self.__timedelta.days, hour, minute, second, 
                            self.__timedelta.microseconds)
        else:
            offset = self.minutes_from_utc
            sign = '+'
            if offset < 0:
                sign = '-'
                offset = -offset
            return '%d%02d%02d%02d%02d%02d.%06d%s%03d' % \
                   (self.__datetime.year, self.__datetime.month, 
                    self.__datetime.day, self.__datetime.hour,
                    self.__datetime.minute, self.__datetime.second, 
                    self.__datetime.microsecond, sign, offset)

    def __repr__ (self):
        return '%s(%s)'%(self.__class__.__name__, `str(self)`)

    def __getstate__(self):
        return str(self)

    def __setstate__(self, arg):
        self.__init__(arg)

    def __cmp__(self, other):
        if self is other:
            return 0
        elif not isinstance(other, CIMDateTime):
            return 1
        return (cmp(self.__datetime, other.__datetime) or 
                cmp(self.__timedelta, other.__timedelta))


# CIM integer types

class CIMInt(CIMType, long):
    pass

class Uint8(CIMInt):
    cimtype = 'uint8'

class Sint8(CIMInt):
    cimtype = 'sint8'

class Uint16(CIMInt):
    cimtype = 'uint16'

class Sint16(CIMInt):
    cimtype = 'sint16'

class Uint32(CIMInt):
    cimtype = 'uint32'

class Sint32(CIMInt):
    cimtype = 'sint32'

class Uint64(CIMInt):
    cimtype = 'uint64'

class Sint64(CIMInt):
    cimtype = 'sint64'

# CIM float types

class CIMFloat(CIMType, float):
    pass

class Real32(CIMFloat):
    cimtype = 'real32'

class Real64(CIMFloat):
    cimtype = 'real64'

def cimtype(obj):
    """Return the CIM type name of an object as a string.  For a list, the
    type is the type of the first element as CIM arrays must be
    homogeneous."""
    
    if isinstance(obj, CIMType):
        return obj.cimtype

    if isinstance(obj, bool):
        return 'boolean'

    if isinstance(obj, (str, unicode)):
        return 'string'

    if isinstance(obj, list):
        return cimtype(obj[0])

    if isinstance(obj, (datetime, timedelta)):
        return 'datetime'

    raise TypeError("Invalid CIM type for %s" % str(obj))



def atomic_to_cim_xml(obj):
    """Convert an atomic type to CIM external form"""
    if isinstance(obj, bool):
        if obj:
            return "true"
        else:
            return "false"

    elif isinstance(obj, CIMDateTime):
        return unicode(obj)

    elif isinstance(obj, datetime):
        return unicode(CIMDateTime(obj))

    elif obj is None:
        return obj
    elif cimtype(obj) == 'real32':
        return u'%.8E' % obj
    elif cimtype(obj) == 'real64':
        return u'%.16E' % obj
    else:
        return unicode(obj)

