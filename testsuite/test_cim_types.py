#!/usr/bin/env python

"""
Test CIM types.
"""

from __future__ import absolute_import, print_function

import re
import os.path
from datetime import timedelta, datetime
import unittest

import pytest
import six

from pywbem import CIMType, CIMInt, CIMFloat, Uint8, Uint16, Uint32, Uint64, \
                   Sint8, Sint16, Sint32, Sint64, Real32, Real64, CIMDateTime, \
                   MinutesFromUTC


#
# CIM integer data types
#

@pytest.fixture(params=[

    # Each list item is a tuple of:
    # - obj_type (type): CIM integer data type (e.g. Uint8).
    # - exp_cimtype (string): Expected value of cimtype class attribute for
    #   this CIM data type.
    # - exp_minvalue (integer): Expected value of minvalue class attribute for
    #   this CIM data type.
    # - exp_maxvalue (): Expected value of maxvalue class attribute for
    #   this CIM data type.

    # (obj_type, exp_cimtype, exp_minvalue, exp_maxvalue)
    (Uint8, 'uint8', 0, 2**8 - 1),
    (Uint16, 'uint16', 0, 2**16 - 1),
    (Uint32, 'uint32', 0, 2**32 - 1),
    (Uint64, 'uint64', 0, 2**64 - 1),
    (Sint8, 'sint8', -2**7, 2**7 - 1),
    (Sint16, 'sint16', -2**15, 2**15 - 1),
    (Sint32, 'sint32', -2**31, 2**31 - 1),
    (Sint64, 'sint64', -2**63, 2**63 - 1),
], scope='module')
def integer_tuple(request):
    return request.param

class TestIntegers:
    """
    Test CIM integer data type classes.
    """

    def test_class_attrs_class(self, integer_tuple):
        """Test class attrs via class level"""
        obj_type, exp_cimtype, exp_minvalue, exp_maxvalue = integer_tuple
        assert obj_type.cimtype == exp_cimtype
        assert obj_type.minvalue == exp_minvalue
        assert obj_type.maxvalue == exp_maxvalue

    def test_class_attrs_inst(self, integer_tuple):
        """Test class attrs via instance level"""
        obj_type, exp_cimtype, exp_minvalue, exp_maxvalue = integer_tuple
        obj = obj_type(42)
        assert obj.cimtype == exp_cimtype
        assert obj.minvalue == exp_minvalue
        assert obj.maxvalue == exp_maxvalue

    def test_inheritance(self, integer_tuple):
        """Test inheritance"""
        obj_type, exp_cimtype, exp_minvalue, exp_maxvalue = integer_tuple
        obj = obj_type(42)
        assert isinstance(obj, obj_type)
        assert isinstance(obj, CIMType)
        assert isinstance(obj, CIMInt)
        assert not isinstance(obj, CIMFloat)

    def test_init_int(self, integer_tuple):
        """Test initialization from integer value"""
        obj_type, exp_cimtype, exp_minvalue, exp_maxvalue = integer_tuple
        obj = obj_type(42)
        assert obj == 42

    def test_init_str(self, integer_tuple):
        """Test initialization from string value"""
        obj_type, exp_cimtype, exp_minvalue, exp_maxvalue = integer_tuple
        obj = obj_type('42')
        assert obj == 42

    def test_init_str_base10(self, integer_tuple):
        """Test initialization from string value with base 10"""
        obj_type, exp_cimtype, exp_minvalue, exp_maxvalue = integer_tuple
        obj = obj_type('42', 10)
        assert obj == 42

    def test_init_str_base16(self, integer_tuple):
        """Test initialization from string value with base 16"""
        obj_type, exp_cimtype, exp_minvalue, exp_maxvalue = integer_tuple
        obj = obj_type('2A', 16)
        assert obj == 42

    def test_init_minimum(self, integer_tuple):
        """Test initialization from integer value at minimum"""
        obj_type, exp_cimtype, exp_minvalue, exp_maxvalue = integer_tuple
        obj = obj_type(exp_minvalue)
        assert obj == exp_minvalue

    def test_init_maximum(self, integer_tuple):
        """Test initialization from integer value at maximum"""
        obj_type, exp_cimtype, exp_minvalue, exp_maxvalue = integer_tuple
        obj = obj_type(exp_maxvalue)
        assert obj == exp_maxvalue

    def test_init_too_low(self, integer_tuple):
        """Test initialization from integer value below minimum"""
        obj_type, exp_cimtype, exp_minvalue, exp_maxvalue = integer_tuple
        try:
            obj = obj_type(exp_minvalue - 1)
        except ValueError as exc:
            pass
        else:
            raise AssertionError("ValueError was not raised.")

    def test_init_too_high(self, integer_tuple):
        """Test initialization from integer value above maximum"""
        obj_type, exp_cimtype, exp_minvalue, exp_maxvalue = integer_tuple
        try:
            obj = obj_type(exp_maxvalue + 1)
        except ValueError as exc:
            pass
        else:
            raise AssertionError("ValueError was not raised.")


#
# CIM real data types
#

@pytest.fixture(params=[

    # Each list item is a tuple of:
    # - obj_type (type): CIM real data type (e.g. Real32).
    # - exp_cimtype (string): Expected value of cimtype class attribute for
    #   this CIM data type.

    # (obj_type, exp_cimtype)
    (Real32, 'real32'),
    (Real64, 'real64'),
], scope='module')
def real_tuple(request):
    return request.param

class TestReals:
    """
    Test CIM real data type classes.
    """

    def test_class_attrs_class(self, real_tuple):
        """Test class attrs via class level"""
        obj_type, exp_cimtype = real_tuple
        assert obj_type.cimtype == exp_cimtype

    def test_class_attrs_inst(self, real_tuple):
        """Test class attrs via instance level"""
        obj_type, exp_cimtype = real_tuple
        obj = obj_type(42)
        assert obj.cimtype == exp_cimtype

    def test_inheritance(self, real_tuple):
        """Test inheritance"""
        obj_type, exp_cimtype = real_tuple
        obj = obj_type(42)
        assert isinstance(obj, obj_type)
        assert isinstance(obj, CIMType)
        assert isinstance(obj, CIMFloat)
        assert not isinstance(obj, CIMInt)

    def test_init_float(self, real_tuple):
        """Test initialization from floating point value"""
        obj_type, exp_cimtype = real_tuple
        obj = obj_type(42.0)
        assert obj == 42.0

    def test_init_str(self, real_tuple):
        """Test initialization from string value"""
        obj_type, exp_cimtype = real_tuple
        obj = obj_type('42.0')
        assert obj == 42.0


#
# CIM datetime data type
#

@pytest.fixture(params=[

    # Each list item is a tuple of:
    # (
    #   dtarg: Input argument for CIMDateTime().
    #   exp_kind: Expected kind of datetime: 'interval' or 'timestamp', or
    #             exception type if initialization failed.
    #   exp_datetime: Expected value for datetime property.
    #   exp_timedelta: Expected value for timedelta property.
    #   exp_minutesfromutc: Expected value for minutes_from_utc property.
    #   exp_str: Expected string value of the CIMDateTime object.
    # )
    (
        timedelta(days=12345678, hours=22, minutes=44, seconds=55,
                  microseconds=654321),
        'interval',
        None,
        timedelta(days=12345678, hours=22, minutes=44, seconds=55,
                  microseconds=654321),
        0,
        '12345678224455.654321:000'
    ),
    (
        '12345678224455.654321:000',
        'interval',
        None,
        timedelta(days=12345678, hours=22, minutes=44, seconds=55,
                  microseconds=654321),
        0,
        '12345678224455.654321:000'
    ),
    (
        CIMDateTime('12345678224455.654321:000'),
        'interval',
        None,
        timedelta(days=12345678, hours=22, minutes=44, seconds=55,
                  microseconds=654321),
        0,
        '12345678224455.654321:000'
    ),
    (
        '12345678224455.654321:777',
        ValueError, None, None, None, None
    ),
    (
        '12345678224455,654321:000',
        ValueError, None, None, None, None
    ),
    (
        datetime(year=2014, month=9, day=24, hour=19, minute=30, second=40,
                 microsecond=654321, tzinfo=MinutesFromUTC(120)),
        'timestamp',
        datetime(year=2014, month=9, day=24, hour=19, minute=30, second=40,
                 microsecond=654321, tzinfo=MinutesFromUTC(120)),
        None,
        120,
        '20140924193040.654321+120'
    ),
    (
        '20140924193040.654321+120',
        'timestamp',
        datetime(year=2014, month=9, day=24, hour=19, minute=30, second=40,
                 microsecond=654321, tzinfo=MinutesFromUTC(120)),
        None,
        120,
        '20140924193040.654321+120'
    ),
    (
        CIMDateTime('20140924193040.654321+120'),
        'timestamp',
        datetime(year=2014, month=9, day=24, hour=19, minute=30, second=40,
                 microsecond=654321, tzinfo=MinutesFromUTC(120)),
        None,
        120,
        '20140924193040.654321+120'
    ),
    (
        '20140924193040.654321*120',
        ValueError, None, None, None, None
    ),
    (
        '20140924193040,654321+120',
        ValueError, None, None, None, None
    ),
    (
        '20141324193040.654321+120',
        ValueError, None, None, None, None
    ),
    (
        '20140932193040.654321+120',
        ValueError, None, None, None, None
    ),
    (
        '20140924253040.654321+120',
        ValueError, None, None, None, None
    ),
    (
        '20140924196140.654321+120',
        ValueError, None, None, None, None
    ),
    (
        '20140924193061.654321+120',
        ValueError, None, None, None, None
    ),
    (
        42,
        TypeError, None, None, None, None
    ),
], scope='module')
def datetime_init_tuple(request):
    return request.param

class TestDatetime:
    """
    Test CIM real data type classes.
    """

    def test_class_attrs_class(self):
        """Test class attrs via class level"""
        assert CIMDateTime.cimtype == 'datetime'

    def test_class_attrs_inst(self):
        """Test class attrs via instance level"""
        obj = CIMDateTime('00000000000000.000000:000')
        assert CIMDateTime.cimtype == 'datetime'

    def test_inheritance(self):
        """Test inheritance"""
        obj = CIMDateTime('00000000000000.000000:000')
        assert isinstance(obj, CIMDateTime)
        assert isinstance(obj, CIMType)
        assert not isinstance(obj, CIMFloat)
        assert not isinstance(obj, CIMInt)

    def test_init(self, datetime_init_tuple):
        """Test initialization from all input types"""
        (dtarg, exp_kind, exp_datetime, exp_timedelta, exp_minutesfromutc,
         exp_str) = datetime_init_tuple
        try:
            obj = CIMDateTime(dtarg)
        except Exception as exc:
            assert isinstance(exc, exp_kind)
        else:
            assert obj.is_interval == (exp_kind == 'interval')
            assert obj.datetime == exp_datetime
            assert obj.timedelta == exp_timedelta
            assert obj.minutes_from_utc == exp_minutesfromutc
            assert str(obj) == exp_str

# TODO: Add testcases for get_local_utcoffset()
# TODO: Add testcases for now()
# TODO: Add testcases for fromtimestamp()

