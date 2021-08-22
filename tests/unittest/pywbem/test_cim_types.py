#!/usr/bin/env python

"""
Test CIM types.
"""

from __future__ import absolute_import, print_function

import re
from datetime import timedelta, datetime
import pytz
import pytest
import six

from ..utils.pytest_extensions import simplified_test_function

# pylint: disable=wrong-import-position, wrong-import-order, invalid-name
from ...utils import import_installed
pywbem = import_installed('pywbem')
from pywbem import CIMType, CIMInt, CIMFloat, Uint8, Uint16, Uint32, Uint64, \
    Sint8, Sint16, Sint32, Sint64, Real32, Real64, Char16, CIMDateTime, \
    MinutesFromUTC, CIMClass, CIMInstance, CIMInstanceName, CIMClassName, \
    cimtype, type_from_name  # noqa: E402
# pylint: enable=wrong-import-position, wrong-import-order, invalid-name


#
# CIM Char16 data type
#


@pytest.fixture(params=[

    # Each list item is a tuple of:
    # (
    #   in_str: Input argument for Char16().
    #   exp_str: Expected string value of the Char16 object.
    #   exp_exc_type: Expected exception type if initialization failed, or None
    # )
    (
        None,
        u'None',
        None,
    ),
    (
        u'foo',
        u'foo',
        None,
    ),
    (
        b'foo',
        u'foo',
        None,
    ),
    (
        42,
        u'42',
        None,
    ),
    (
        Char16('foo'),
        u'foo',
        None,
    ),
], scope='module')
def char16_init_tuple(request):
    """pytest.fixture that returns char16 tuple info"""
    return request.param


def test_char16_class_attrs_class():  # pylint: disable=invalid-name
    """Test class attrs via class level"""
    assert Char16.cimtype == 'char16'


def test_char16_class_attrs_inst():
    """Test class attrs via instance level"""
    obj = Char16('foo')
    assert obj.cimtype == 'char16'


def test_char16_inheritance():
    """Test inheritance"""
    obj = Char16('foo')
    assert isinstance(obj, six.text_type)
    assert isinstance(obj, CIMType)


def test_char16_init(char16_init_tuple):
    """Test initialization from all input types using
       char16_init_tuple pytest.fixture.
    """
    # pylint: disable=redefined-outer-name
    (in_str, exp_str, exp_exc_type) = char16_init_tuple
    try:
        obj = Char16(in_str)
    except Exception as exc:  # pylint: disable=broad-except
        assert isinstance(exc, exp_exc_type)
    else:
        assert not hasattr(obj, '__dict__')
        assert exp_exc_type is None
        assert obj == exp_str
        assert obj is not in_str


def test_char16_repr(char16_init_tuple):
    """
    Test repr(CIMDateTime) from all input types using
    char16_init_tuple pytest.fixture.
    """
    # pylint: disable=redefined-outer-name
    (in_str, _, exp_exc_type) = char16_init_tuple

    if exp_exc_type is not None:
        pytest.skip("Testing repr() needs Char16 object")

    obj = Char16(in_str)

    # The code to be tested.
    # The actual test is that no exception is raised.
    repr(obj)


def test_char16_str(char16_init_tuple):
    """
    Test str(CIMDateTime) from all input types using
    char16_init_tuple pytest.fixture.
    """
    # pylint: disable=redefined-outer-name
    (in_str, _, exp_exc_type) = char16_init_tuple

    if exp_exc_type is not None:
        pytest.skip("Testing repr() needs Char16 object")

    obj = Char16(in_str)

    # The code to be tested.
    # The actual test is that no exception is raised.
    str(obj)


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
    """Utility function to return param from request"""
    return request.param


def test_integer_class_attrs_class(integer_tuple):
    """Test class attrs via class level"""
    # pylint: disable=redefined-outer-name
    obj_type, exp_cimtype, exp_minvalue, exp_maxvalue = integer_tuple
    assert obj_type.cimtype == exp_cimtype
    assert obj_type.minvalue == exp_minvalue
    assert obj_type.maxvalue == exp_maxvalue


def test_integer_class_attrs_inst(integer_tuple):
    """Test class attrs via instance level"""
    # pylint: disable=redefined-outer-name
    obj_type, exp_cimtype, exp_minvalue, exp_maxvalue = integer_tuple
    obj = obj_type(42)
    assert obj.cimtype == exp_cimtype
    assert obj.minvalue == exp_minvalue
    assert obj.maxvalue == exp_maxvalue


def test_integer_inheritance(integer_tuple):
    """Test inheritance"""
    # pylint: disable=redefined-outer-name
    obj_type = integer_tuple[0]
    obj = obj_type(42)
    assert isinstance(obj, obj_type)
    assert isinstance(obj, CIMType)
    assert isinstance(obj, CIMInt)
    assert not isinstance(obj, CIMFloat)


def test_integer_init_int(integer_tuple):
    """Test initialization from integer value"""
    # pylint: disable=redefined-outer-name
    obj_type = integer_tuple[0]
    obj = obj_type(42)
    assert obj == 42


def test_integer_init_str(integer_tuple):
    """Test initialization from string value"""
    # pylint: disable=redefined-outer-name
    obj_type = integer_tuple[0]
    obj = obj_type('42')
    assert obj == 42


def test_integer_init_str_base10(integer_tuple):
    """Test initialization from string value with base 10"""
    # pylint: disable=redefined-outer-name
    obj_type = integer_tuple[0]
    obj = obj_type('42', 10)
    assert obj == 42


def test_integer_init_str_base16(integer_tuple):
    """Test initialization from string value with base 16"""
    # pylint: disable=redefined-outer-name
    obj_type = integer_tuple[0]
    obj = obj_type('2A', 16)
    assert obj == 42


def test_integer_init_minimum(integer_tuple):
    """Test initialization from integer value at minimum"""
    # pylint: disable=redefined-outer-name
    obj_type = integer_tuple[0]
    exp_minvalue = integer_tuple[2]
    obj = obj_type(exp_minvalue)
    assert obj == exp_minvalue


def test_integer_init_maximum(integer_tuple):
    """Test initialization from integer value at maximum"""
    # pylint: disable=redefined-outer-name
    obj_type = integer_tuple[0]
    exp_maxvalue = integer_tuple[3]
    obj = obj_type(exp_maxvalue)
    assert obj == exp_maxvalue


def test_integer_init_too_low(integer_tuple):
    """Test initialization from integer value below minimum"""
    # pylint: disable=redefined-outer-name
    obj_type = integer_tuple[0]
    exp_minvalue = integer_tuple[2]
    try:
        obj_type(exp_minvalue - 1)
    except ValueError:
        pass
    else:
        raise AssertionError("ValueError was not raised.")


def test_integer_init_too_high(integer_tuple):
    """Test initialization from integer value above maximum"""
    # pylint: disable=redefined-outer-name
    obj_type = integer_tuple[0]
    exp_maxvalue = integer_tuple[3]
    try:
        obj_type(exp_maxvalue + 1)
    except ValueError:
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
    """pytest.fixture returns Real types"""
    return request.param


def test_real_class_attrs_class(real_tuple):
    """Test class attrs via class level using real_tuple fixture"""
    # pylint: disable=redefined-outer-name
    obj_type, exp_cimtype = real_tuple
    assert obj_type.cimtype == exp_cimtype


def test_real_class_attrs_inst(real_tuple):
    """Test class attrs via instance level using real_tuple fixture"""
    # pylint: disable=redefined-outer-name
    obj_type, exp_cimtype = real_tuple
    obj = obj_type(42)
    assert obj.cimtype == exp_cimtype


def test_real_inheritance(real_tuple):
    """Test inheritance  using real_tuple fixture"""
    # pylint: disable=redefined-outer-name
    obj_type = real_tuple[0]
    obj = obj_type(42)
    assert isinstance(obj, obj_type)
    assert isinstance(obj, CIMType)
    assert isinstance(obj, CIMFloat)
    assert not isinstance(obj, CIMInt)


def test_real_init_float(real_tuple):
    """Test initialization from floating point value"""
    # pylint: disable=redefined-outer-name
    obj_type = real_tuple[0]
    obj = obj_type(42.0)
    assert obj == 42.0


def test_real_init_str(real_tuple):
    """Test initialization from string value using real_tuple fixture"""
    # pylint: disable=redefined-outer-name
    obj_type = real_tuple[0]
    obj = obj_type('42.0')
    assert obj == 42.0


#
# repr() and str() tests for CIMInt/CIMFloat
#

@pytest.fixture(params=[

    # Each list item is a tuple of:
    # (obj_type, init_arg, exp_str, exp_repr_pattern)
    (Uint8, 42, u'42', r'^Uint8\(.*, 42\)'),
    (Uint16, 42, u'42', r'^Uint16\(.*, 42\)'),
    (Uint32, 42, u'42', r'^Uint32\(.*, 42\)'),
    (Uint64, 42, u'42', r'^Uint64\(.*, 42\)'),
    (Sint8, -42, u'-42', r'^Sint8\(.*, -42\)'),
    (Sint16, -42, u'-42', r'^Sint16\(.*, -42\)'),
    (Sint32, -42, u'-42', r'^Sint32\(.*, -42\)'),
    (Sint64, -42, u'-42', r'^Sint64\(.*, -42\)'),
    (Real32, -42.1, u'-42.1', r'^Real32\(.*, -42.1\)'),
    (Real64, -42.1, u'-42.1', r'^Real64\(.*, -42.1\)'),
], scope='module')
def number_str_repr_tuple(request):
    """Utility function to return param from request"""
    return request.param


def test_number_str(number_str_repr_tuple):
    # pylint: disable=redefined-outer-name
    """Test __str__() for a number"""
    obj_type, init_arg, exp_str, _ = number_str_repr_tuple
    obj = obj_type(init_arg)

    # The code to be tested
    act_str = str(obj)

    assert act_str == exp_str


def test_number_repr(number_str_repr_tuple):
    # pylint: disable=redefined-outer-name
    """Test __repr__() for a number"""
    obj_type, init_arg, _, exp_repr_pattern = number_str_repr_tuple
    obj = obj_type(init_arg)

    # The code to be tested
    act_repr = repr(obj)

    assert re.match(exp_repr_pattern, act_repr)


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
    #   exp_precision: Expected value for precision property.
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
        None,
        0,
        '12345678224455.654321:000'
    ),
    (
        '12345678224455.654321:000',
        'interval',
        None,
        timedelta(days=12345678, hours=22, minutes=44, seconds=55,
                  microseconds=654321),
        None,
        0,
        '12345678224455.654321:000'
    ),
    (
        CIMDateTime('12345678224455.654321:000'),
        'interval',
        None,
        timedelta(days=12345678, hours=22, minutes=44, seconds=55,
                  microseconds=654321),
        None,
        0,
        '12345678224455.654321:000'
    ),
    (
        '12345678224455.65432*:000',
        'interval',
        None,
        timedelta(days=12345678, hours=22, minutes=44, seconds=55,
                  microseconds=654320),
        20,
        0,
        '12345678224455.65432*:000'
    ),
    (
        '12345678224455.6543**:000',
        'interval',
        None,
        timedelta(days=12345678, hours=22, minutes=44, seconds=55,
                  microseconds=654300),
        19,
        0,
        '12345678224455.6543**:000'
    ),
    (
        '12345678224455.654***:000',
        'interval',
        None,
        timedelta(days=12345678, hours=22, minutes=44, seconds=55,
                  microseconds=654000),
        18,
        0,
        '12345678224455.654***:000'
    ),
    (
        '12345678224455.65****:000',
        'interval',
        None,
        timedelta(days=12345678, hours=22, minutes=44, seconds=55,
                  microseconds=650000),
        17,
        0,
        '12345678224455.65****:000'
    ),
    (
        '12345678224455.6*****:000',
        'interval',
        None,
        timedelta(days=12345678, hours=22, minutes=44, seconds=55,
                  microseconds=600000),
        16,
        0,
        '12345678224455.6*****:000'
    ),
    (
        '12345678224455.******:000',
        'interval',
        None,
        timedelta(days=12345678, hours=22, minutes=44, seconds=55,
                  microseconds=0),
        15,
        0,
        '12345678224455.******:000'
    ),
    (
        '1234567822445*.******:000',
        ValueError, None, None, None, None, None
    ),
    (
        '123456782244**.******:000',
        'interval',
        None,
        timedelta(days=12345678, hours=22, minutes=44, seconds=0,
                  microseconds=0),
        12,
        0,
        '123456782244**.******:000'
    ),
    (
        '12345678224***.******:000',
        ValueError, None, None, None, None, None
    ),
    (
        '1234567822****.******:000',
        'interval',
        None,
        timedelta(days=12345678, hours=22, minutes=0, seconds=0,
                  microseconds=0),
        10,
        0,
        '1234567822****.******:000'
    ),
    (
        '123456782*****.******:000',
        ValueError, None, None, None, None, None
    ),
    (
        '12345678******.******:000',
        'interval',
        None,
        timedelta(days=12345678, hours=0, minutes=0, seconds=0,
                  microseconds=0),
        8,
        0,
        '12345678******.******:000'
    ),
    (
        '1234567*******.******:000',
        ValueError, None, None, None, None, None
    ),
    (
        '123456********.******:000',
        ValueError, None, None, None, None, None
    ),
    (
        '12345*********.******:000',
        ValueError, None, None, None, None, None
    ),
    (
        '1234**********.******:000',
        ValueError, None, None, None, None, None
    ),
    (
        '123***********.******:000',
        ValueError, None, None, None, None, None
    ),
    (
        '12************.******:000',
        ValueError, None, None, None, None, None
    ),
    (
        '1*************.******:000',
        ValueError, None, None, None, None, None
    ),
    (
        '**************.******:000',
        'interval',
        None,
        timedelta(days=0, hours=0, minutes=0, seconds=0,
                  microseconds=0),
        0,
        0,
        '**************.******:000'
    ),
    (
        '12345678224455.654321:777',
        ValueError, None, None, None, None, None
    ),
    (
        '12345678224455,654321:000',
        ValueError, None, None, None, None, None
    ),
    (
        datetime(year=2014, month=9, day=24, hour=19, minute=30, second=40,
                 microsecond=654321, tzinfo=MinutesFromUTC(120)),
        'timestamp',
        datetime(year=2014, month=9, day=24, hour=19, minute=30, second=40,
                 microsecond=654321, tzinfo=MinutesFromUTC(120)),
        None,
        None,
        120,
        '20140924193040.654321+120'
    ),
    (
        datetime(year=2014, month=9, day=24, hour=19, minute=30, second=40,
                 microsecond=654321, tzinfo=MinutesFromUTC(0)),
        'timestamp',
        datetime(year=2014, month=9, day=24, hour=19, minute=30, second=40,
                 microsecond=654321, tzinfo=MinutesFromUTC(0)),
        None,
        None,
        0,
        '20140924193040.654321+000'
    ),
    (
        datetime(year=2014, month=9, day=24, hour=19, minute=30, second=40,
                 microsecond=654321),
        'timestamp',
        datetime(year=2014, month=9, day=24, hour=19, minute=30, second=40,
                 microsecond=654321, tzinfo=MinutesFromUTC(0)),
        None,
        None,
        0,
        '20140924193040.654321+000'
    ),
    (
        '20140924193040.654321+120',
        'timestamp',
        datetime(year=2014, month=9, day=24, hour=19, minute=30, second=40,
                 microsecond=654321, tzinfo=MinutesFromUTC(120)),
        None,
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
        None,
        120,
        '20140924193040.654321+120'
    ),
    (
        '20180912123040.65432*+120',
        'timestamp',
        datetime(year=2018, month=9, day=12, hour=12, minute=30, second=40,
                 microsecond=654320, tzinfo=MinutesFromUTC(120)),
        None,
        20,
        120,
        '20180912123040.65432*+120'
    ),
    (
        '20180912123040.6543**+120',
        'timestamp',
        datetime(year=2018, month=9, day=12, hour=12, minute=30, second=40,
                 microsecond=654300, tzinfo=MinutesFromUTC(120)),
        None,
        19,
        120,
        '20180912123040.6543**+120'
    ),
    (
        '20180912123040.654***+120',
        'timestamp',
        datetime(year=2018, month=9, day=12, hour=12, minute=30, second=40,
                 microsecond=654000, tzinfo=MinutesFromUTC(120)),
        None,
        18,
        120,
        '20180912123040.654***+120'
    ),
    (
        '20180912123040.65****+120',
        'timestamp',
        datetime(year=2018, month=9, day=12, hour=12, minute=30, second=40,
                 microsecond=650000, tzinfo=MinutesFromUTC(120)),
        None,
        17,
        120,
        '20180912123040.65****+120'
    ),
    (
        '20180912123040.6*****+120',
        'timestamp',
        datetime(year=2018, month=9, day=12, hour=12, minute=30, second=40,
                 microsecond=600000, tzinfo=MinutesFromUTC(120)),
        None,
        16,
        120,
        '20180912123040.6*****+120'
    ),
    (
        '20180912123040.******+120',
        'timestamp',
        datetime(year=2018, month=9, day=12, hour=12, minute=30, second=40,
                 microsecond=0, tzinfo=MinutesFromUTC(120)),
        None,
        15,
        120,
        '20180912123040.******+120'
    ),
    (
        '2018091212304*.******+120',
        ValueError, None, None, None, None, None
    ),
    (
        '201809121230**.******+120',
        'timestamp',
        datetime(year=2018, month=9, day=12, hour=12, minute=30, second=0,
                 microsecond=0, tzinfo=MinutesFromUTC(120)),
        None,
        12,
        120,
        '201809121230**.******+120'
    ),
    (
        '20180912123***.******+120',
        ValueError, None, None, None, None, None
    ),
    (
        '2018091212****.******+120',
        'timestamp',
        datetime(year=2018, month=9, day=12, hour=12, minute=0, second=0,
                 microsecond=0, tzinfo=MinutesFromUTC(120)),
        None,
        10,
        120,
        '2018091212****.******+120'
    ),
    (
        '201809121*****.******+120',
        ValueError, None, None, None, None, None
    ),
    (
        '20180912******.******+120',
        'timestamp',
        datetime(year=2018, month=9, day=12, hour=0, minute=0, second=0,
                 microsecond=0, tzinfo=MinutesFromUTC(120)),
        None,
        8,
        120,
        '20180912******.******+120'
    ),
    (
        '2018091*******.******+120',
        ValueError, None, None, None, None, None
    ),
    (
        '201809********.******+120',
        'timestamp',
        datetime(year=2018, month=9, day=1, hour=0, minute=0, second=0,
                 microsecond=0, tzinfo=MinutesFromUTC(120)),
        None,
        6,
        120,
        '201809********.******+120'
    ),
    (
        '20180*********.******+120',
        ValueError, None, None, None, None, None
    ),
    (
        '2018**********.******+120',
        'timestamp',
        datetime(year=2018, month=1, day=1, hour=0, minute=0, second=0,
                 microsecond=0, tzinfo=MinutesFromUTC(120)),
        None,
        4,
        120,
        '2018**********.******+120'
    ),
    (
        '201***********.******+120',
        ValueError, None, None, None, None, None
    ),
    (
        '20************.******+120',
        ValueError, None, None, None, None, None
    ),
    (
        '2*************.******+120',
        ValueError, None, None, None, None, None
    ),
    (    # year out of range for timestamp()
        '**************.******+120',
        ValueError, None, None, None, None, None
    ),
    (
        '20140924193040.654321*120',
        ValueError, None, None, None, None, None
    ),
    (
        '20140924193040,654321+120',
        ValueError, None, None, None, None, None
    ),
    (
        '20141324193040.654321+120',
        ValueError, None, None, None, None, None
    ),
    (
        '20140932193040.654321+120',
        ValueError, None, None, None, None, None
    ),
    (
        '20140924253040.654321+120',
        ValueError, None, None, None, None, None
    ),
    (
        '20140924196140.654321+120',
        ValueError, None, None, None, None, None
    ),
    (
        '20140924193061.654321+120',
        ValueError, None, None, None, None, None
    ),
    (
        42,
        TypeError, None, None, None, None, None
    ),
], scope='module')
def datetime_init_tuple(request):
    """pytest.fixture that returns datatetime tuple info"""
    return request.param


def test_datetime_class_attrs_class():  # pylint: disable=invalid-name
    """Test class attrs via class level"""
    assert CIMDateTime.cimtype == 'datetime'


def test_datetime_class_attrs_inst():
    """Test class attrs via instance level"""
    obj = CIMDateTime('00000000000000.000000:000')
    assert obj.cimtype == 'datetime'


def test_datetime_inheritance():
    """Test inheritance"""
    obj = CIMDateTime('00000000000000.000000:000')
    assert isinstance(obj, CIMDateTime)
    assert isinstance(obj, CIMType)
    assert not isinstance(obj, CIMFloat)
    assert not isinstance(obj, CIMInt)


def test_datetime_init(datetime_init_tuple):
    """Test initialization from all input types using
       datetime_init_tuple pytest.fixture.
    """
    # pylint: disable=redefined-outer-name
    (dtarg, exp_kind, exp_datetime, exp_timedelta, exp_precision,
     exp_minutesfromutc, exp_str) = datetime_init_tuple
    try:
        obj = CIMDateTime(dtarg)
    except Exception as exc:  # pylint: disable=broad-except
        assert isinstance(exc, exp_kind)
    else:
        assert not hasattr(obj, '__dict__')
        assert obj.is_interval == (exp_kind == 'interval')
        assert obj.datetime == exp_datetime
        if obj.datetime is not None:
            assert isinstance(obj.datetime, datetime)
            # We ensure that the datetime is always timezone-aware:
            assert obj.datetime.tzinfo is not None
        assert obj.timedelta == exp_timedelta
        if obj.timedelta is not None:
            assert isinstance(obj.timedelta, timedelta)
        assert obj.precision == exp_precision
        assert obj.minutes_from_utc == exp_minutesfromutc
        assert str(obj) == exp_str


def test_datetime_repr(datetime_init_tuple):
    """
    Test repr(CIMDateTime) from all input types using
    datetime_init_tuple pytest.fixture.
    """
    # pylint: disable=redefined-outer-name
    (dtarg, exp_kind, _, _, _, _, _) = datetime_init_tuple

    if isinstance(exp_kind, type) and issubclass(exp_kind, Exception):
        pytest.skip("Testing repr() needs CIMDatetime object")

    obj = CIMDateTime(dtarg)

    # The code to be tested.
    # The actual test is that no exception is raised.
    repr(obj)


def test_datetime_str(datetime_init_tuple):
    """
    Test str(CIMDateTime) from all input types using
    datetime_init_tuple pytest.fixture.
    """
    # pylint: disable=redefined-outer-name
    (dtarg, exp_kind, _, _, _, _, _) = datetime_init_tuple

    if isinstance(exp_kind, type) and issubclass(exp_kind, Exception):
        pytest.skip("Testing str() needs CIMDatetime object")

    obj = CIMDateTime(dtarg)

    # The code to be tested.
    # The actual test is that no exception is raised.
    str(obj)


# TODO: Add testcases for get_local_utcoffset()
# TODO: Add testcases for now()
# TODO: Add testcases for fromtimestamp()


TESTCASES_MINUTESFROMUTC_INIT = [

    # Testcases for MinutesFromUTC.__init__()

    # Each list item is a testcase tuple with these items:
    # * desc: Short testcase description.
    # * kwargs: Keyword arguments for the test function:
    #   * args: Positional args for init.
    #   * kwargs: Keyword args for init.
    #   * exp_offset: Expected offset to UTC in minutes.
    # * exp_exc_types: Expected exception type(s), or None.
    # * exp_warn_types: Expected warning type(s), or None.
    # * condition: Boolean condition for testcase to run, or 'pdb' for debugger

    (
        "Test with missing required arguments",
        dict(
            args=[],
            kwargs={},
            exp_offset=None,
        ),
        TypeError, None, True
    ),
    (
        "Test with minimal number of positional arguments",
        dict(
            args=[30],
            kwargs={},
            exp_offset=30,
        ),
        None, None, True
    ),
    (
        "Test with minimal number of keyword arguments",
        dict(
            args=[],
            kwargs=dict(
                offset=30,
            ),
            exp_offset=30,
        ),
        None, None, True
    ),
    (
        "Test with too many positional arguments",
        dict(
            args=[30, 0],
            kwargs={},
            exp_offset=None,
        ),
        TypeError, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_MINUTESFROMUTC_INIT)
@simplified_test_function
def test_MinutesFromUTC_init(testcase, args, kwargs, exp_offset):
    """
    Test function for MinutesFromUTC.__init__().
    """

    # The code to be tested
    tz = MinutesFromUTC(*args, **kwargs)

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None

    assert not hasattr(tz, '__dict__')

    # Verify the UTC offset of the tz object.
    exp_utcoffset = timedelta(minutes=exp_offset)
    dt = datetime.now()
    assert tz.utcoffset(dt) == exp_utcoffset


TESTCASES_MINUTESFROMUTC_UTCOFFSET = [

    # Testcases for MinutesFromUTC.utcoffset()

    # Each list item is a testcase tuple with these items:
    # * desc: Short testcase description.
    # * kwargs: Keyword arguments for the test function:
    #   * offset: offset argument for MinutesFromUTC().
    #   * dt: datetime object as input for utcoffset().
    #   * exp_utc_offset: Expected offset in minutes returned by utcoffset().
    # * exp_exc_types: Expected exception type(s), or None.
    # * exp_warn_types: Expected warning type(s), or None.
    # * condition: Boolean condition for testcase to run, or 'pdb' for debugger

    (
        "Test with UTC offset 30 and datetime without tzinfo",
        dict(
            offset=30,
            dt=datetime.now(),
            exp_utc_offset=30,
        ),
        None, None, True
    ),
    (
        "Test with UTC offset -30 and datetime without tzinfo",
        dict(
            offset=-30,
            dt=datetime.now(),
            exp_utc_offset=-30,
        ),
        None, None, True
    ),
    (
        "Test with UTC offset 150 and datetime with tzinfo for EST (ignored)",
        dict(
            offset=150,
            dt=datetime.now(pytz.timezone('US/Eastern')),
            exp_utc_offset=150,
        ),
        None, None, True
    ),
    (
        "Test with UTC offset -150 and datetime with tzinfo for EDT (ignored)",
        dict(
            offset=-150,
            dt=pytz.timezone('US/Eastern').
            localize(datetime.now(), is_dst=True),
            exp_utc_offset=-150,
        ),
        None, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_MINUTESFROMUTC_UTCOFFSET)
@simplified_test_function
def test_MinutesFromUTC_utcoffset(testcase, offset, dt, exp_utc_offset):
    """
    Test function for MinutesFromUTC.utcoffset().
    """

    tz = MinutesFromUTC(offset)

    # The code to be tested
    act_utcoffset = tz.utcoffset(dt)

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None

    exp_utcoffset = timedelta(minutes=exp_utc_offset)
    assert act_utcoffset == exp_utcoffset


TESTCASES_MINUTESFROMUTC_DST = [

    # Testcases for MinutesFromUTC.dst()

    # Each list item is a testcase tuple with these items:
    # * desc: Short testcase description.
    # * kwargs: Keyword arguments for the test function:
    #   * offset: offset argument for MinutesFromUTC().
    #   * dt: datetime object as input for dst().
    #   * exp_dst_offset: Expected DST offset in minutes returned by dst().
    # * exp_exc_types: Expected exception type(s), or None.
    # * exp_warn_types: Expected warning type(s), or None.
    # * condition: Boolean condition for testcase to run, or 'pdb' for debugger

    (
        "Test with UTC offset 30 and datetime without tzinfo",
        dict(
            offset=30,
            dt=datetime.now(),
            exp_dst_offset=0,
        ),
        None, None, True
    ),
    (
        "Test with UTC offset -30 and datetime without tzinfo",
        dict(
            offset=-30,
            dt=datetime.now(),
            exp_dst_offset=0,
        ),
        None, None, True
    ),
    (
        "Test with UTC offset 150 and datetime with tzinfo for EST (ignored)",
        dict(
            offset=150,
            dt=datetime.now(pytz.timezone('US/Eastern')),
            exp_dst_offset=0,
        ),
        None, None, True
    ),
    (
        "Test with UTC offset -150 and datetime with tzinfo for EDT (ignored)",
        dict(
            offset=-150,
            dt=pytz.timezone('US/Eastern').
            localize(datetime.now(), is_dst=True),
            exp_dst_offset=0,
        ),
        None, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_MINUTESFROMUTC_DST)
@simplified_test_function
def test_MinutesFromUTC_dst(testcase, offset, dt, exp_dst_offset):
    """
    Test function for MinutesFromUTC.dst().
    """

    tz = MinutesFromUTC(offset)

    # The code to be tested
    act_dst = tz.dst(dt)

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None

    exp_dst = timedelta(minutes=exp_dst_offset)
    assert act_dst == exp_dst

    # Test the condition for sane tzinfo implementations w.r.t. DST
    dt1 = datetime(2020, 4, 11, 13, 14, 15, tzinfo=tz)
    diff1 = tz.utcoffset(dt1) - tz.dst(dt1)
    dt2 = datetime.now(tz)
    diff2 = tz.utcoffset(dt2) - tz.dst(dt2)
    assert diff1 == diff2


TESTCASES_MINUTESFROMUTC_TZNAME = [

    # Testcases for MinutesFromUTC.tzname()

    # Each list item is a testcase tuple with these items:
    # * desc: Short testcase description.
    # * kwargs: Keyword arguments for the test function:
    #   * offset: offset argument for MinutesFromUTC().
    #   * dt: datetime object as input for tzname().
    #   * exp_tzname: Expected return value of tzname().
    # * exp_exc_types: Expected exception type(s), or None.
    # * exp_warn_types: Expected warning type(s), or None.
    # * condition: Boolean condition for testcase to run, or 'pdb' for debugger

    (
        "Test with UTC offset 0 and datetime without tzinfo",
        dict(
            offset=0,
            dt=datetime.now(),
            exp_tzname='00:00',
        ),
        None, None, True
    ),
    (
        "Test with UTC offset 30 and datetime without tzinfo",
        dict(
            offset=30,
            dt=datetime.now(),
            exp_tzname='00:30',
        ),
        None, None, True
    ),
    (
        "Test with UTC offset -30 and datetime without tzinfo",
        dict(
            offset=-30,
            dt=datetime.now(),
            exp_tzname='-00:30',
        ),
        None, None, True
    ),
    (
        "Test with UTC offset 60 and datetime without tzinfo",
        dict(
            offset=60,
            dt=datetime.now(),
            exp_tzname='01:00',
        ),
        None, None, True
    ),
    (
        "Test with UTC offset 719 and datetime without tzinfo",
        dict(
            offset=719,
            dt=datetime.now(),
            exp_tzname='11:59',
        ),
        None, None, True
    ),
    (
        "Test with UTC offset 720 and datetime without tzinfo",
        dict(
            offset=720,
            dt=datetime.now(),
            exp_tzname='12:00',
        ),
        None, None, True
    ),
    (
        "Test with UTC offset 790 and datetime without tzinfo",
        dict(
            offset=790,
            dt=datetime.now(),
            exp_tzname='13:10',
        ),
        None, None, True
    ),
    (
        "Test with UTC offset 999 and datetime without tzinfo",
        dict(
            offset=999,
            dt=datetime.now(),
            exp_tzname='16:39',
        ),
        None, None, True
    ),
    (
        "Test with UTC offset -999 and datetime without tzinfo",
        dict(
            offset=-999,
            dt=datetime.now(),
            exp_tzname='-16:39',
        ),
        None, None, True
    ),
    (
        "Test with UTC offset 150 and datetime with tzinfo for EST (ignored)",
        dict(
            offset=150,
            dt=datetime.now(pytz.timezone('US/Eastern')),
            exp_tzname='02:30',
        ),
        None, None, True
    ),
    (
        "Test with UTC offset -150 and datetime with tzinfo for EDT (ignored)",
        dict(
            offset=-150,
            dt=pytz.timezone('US/Eastern').
            localize(datetime.now(), is_dst=True),
            exp_tzname='-02:30',
        ),
        None, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_MINUTESFROMUTC_TZNAME)
@simplified_test_function
def test_MinutesFromUTC_tzname(testcase, offset, dt, exp_tzname):
    """
    Test function for MinutesFromUTC.tzname().
    """

    tz = MinutesFromUTC(offset)

    # The code to be tested
    act_tzname = tz.tzname(dt)

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None

    assert act_tzname == exp_tzname


TESTCASES_CIMTYPE = [

    # Testcases for cimtype()

    # Each list item is a testcase tuple with these items:
    # * desc: Short testcase description.
    # * kwargs: Keyword arguments for the test function:
    #   * obj: object to be tested.
    #   * exp_type_name: Expected CIM data type name.
    # * exp_exc_types: Expected exception type(s), or None.
    # * exp_warn_types: Expected warning type(s), or None.
    # * condition: Boolean condition for testcase to run, or 'pdb' for debugger


    # Special cases
    (
        "Object is None",
        dict(
            obj=None,
            exp_type_name=None,
        ),
        TypeError, None, True
    ),

    # Boolean tests
    (
        "Object is a bool",
        dict(
            obj=True,
            exp_type_name=u'boolean',
        ),
        None, None, True
    ),

    # String tests
    (
        "Object is a unicode string",
        dict(
            obj=u"abc",
            exp_type_name=u'string',
        ),
        None, None, True
    ),
    (
        "Object is a byte string",
        dict(
            obj=b"abc",
            exp_type_name=u'string',
        ),
        None, None, True
    ),

    # Integer tests
    (
        "Object is an integer",
        dict(
            obj=42,
            exp_type_name=None,
        ),
        TypeError, None, True
    ),
    (
        "Object is a Uint8 number",
        dict(
            obj=Uint8(42),
            exp_type_name=u'uint8',
        ),
        None, None, True
    ),
    (
        "Object is a Uint16 number",
        dict(
            obj=Uint16(42),
            exp_type_name=u'uint16',
        ),
        None, None, True
    ),
    (
        "Object is a Uint32 number",
        dict(
            obj=Uint32(42),
            exp_type_name=u'uint32',
        ),
        None, None, True
    ),
    (
        "Object is a Uint64 number",
        dict(
            obj=Uint64(42),
            exp_type_name=u'uint64',
        ),
        None, None, True
    ),
    (
        "Object is a Sint8 number",
        dict(
            obj=Sint8(42),
            exp_type_name=u'sint8',
        ),
        None, None, True
    ),
    (
        "Object is a Sint16 number",
        dict(
            obj=Sint16(42),
            exp_type_name=u'sint16',
        ),
        None, None, True
    ),
    (
        "Object is a Sint32 number",
        dict(
            obj=Sint32(42),
            exp_type_name=u'sint32',
        ),
        None, None, True
    ),
    (
        "Object is a Sint64 number",
        dict(
            obj=Sint64(42),
            exp_type_name=u'sint64',
        ),
        None, None, True
    ),

    # Floating point tests
    (
        "Object is a float",
        dict(
            obj=42.0,
            exp_type_name=None,
        ),
        TypeError, None, True
    ),
    (
        "Object is a Real32 number",
        dict(
            obj=Real32(42.0),
            exp_type_name=u'real32',
        ),
        None, None, True
    ),
    (
        "Object is a Real64 number",
        dict(
            obj=Real64(42.0),
            exp_type_name=u'real64',
        ),
        None, None, True
    ),

    # Datetime tests
    (
        "Object is a Python datetime object",
        dict(
            obj=datetime(year=2014, month=9, day=24, hour=19, minute=30,
                         second=40, microsecond=654321,
                         tzinfo=MinutesFromUTC(120)),
            exp_type_name=u'datetime',
        ),
        None, None, True
    ),
    (
        "Object is a Python timedelta object",
        dict(
            obj=timedelta(days=12345678, hours=22, minutes=44, seconds=55,
                          microseconds=654321),
            exp_type_name=u'datetime',
        ),
        None, None, True
    ),
    (
        "Object is a CIMDateTime object",
        dict(
            obj=CIMDateTime('20140924193040.654321+000'),
            exp_type_name=u'datetime',
        ),
        None, None, True
    ),

    # Other CIM object tests
    (
        "Object is a CIMClass object",
        dict(
            obj=CIMClass('CIM_Foo'),
            exp_type_name=u'string',  # embedded object
        ),
        None, None, True
    ),
    (
        "Object is a CIMInstance object",
        dict(
            obj=CIMInstance('CIM_Foo'),
            exp_type_name=u'string',  # embedded object
        ),
        None, None, True
    ),
    (
        "Object is a CIMInstanceName object",
        dict(
            obj=CIMInstanceName('CIM_Foo'),
            exp_type_name=u'reference',
        ),
        None, None, True
    ),
    (
        "Object is a CIMClassName object",
        dict(
            obj=CIMClassName('CIM_Foo'),
            exp_type_name=None,
        ),
        TypeError, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_CIMTYPE)
@simplified_test_function
def test_cimtype(testcase, obj, exp_type_name):
    """
    Test function for cimtype().
    """

    # There are no init testcases covering all CIM types, so the following
    # check is placed here.
    # TODO: Create init testcaes for CIM types and move this check to there.
    assert not hasattr(obj, '__dict__')

    # The code to be tested
    type_name = cimtype(obj)

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None

    assert type_name == exp_type_name


TESTCASES_TYPE_FROM_NAME = [

    # Testcases for type_from_name()

    # Each list item is a testcase tuple with these items:
    # * desc: Short testcase description.
    # * kwargs: Keyword arguments for the test function:
    #   * type_name: CIM type name to be tested.
    #   * exp_type: Expected Python type object.
    # * exp_exc_types: Expected exception type(s), or None.
    # * exp_warn_types: Expected warning type(s), or None.
    # * condition: Boolean condition for testcase to run, or 'pdb' for debugger

    # Special cases
    (
        "Type name is None",
        dict(
            type_name=None,
            exp_type_obj=None,
        ),
        ValueError, None, True
    ),
    (
        "Type name is invalid",
        dict(
            type_name='foo',
            exp_type_obj=None,
        ),
        ValueError, None, True
    ),

    # CIM type names
    (
        "Type name is boolean",
        dict(
            type_name='boolean',
            exp_type_obj=bool,
        ),
        None, None, True
    ),
    (
        "Type name is uint8",
        dict(
            type_name='uint8',
            exp_type_obj=Uint8,
        ),
        None, None, True
    ),
    (
        "Type name is uint16",
        dict(
            type_name='uint16',
            exp_type_obj=Uint16,
        ),
        None, None, True
    ),
    (
        "Type name is uint32",
        dict(
            type_name='uint32',
            exp_type_obj=Uint32,
        ),
        None, None, True
    ),
    (
        "Type name is uint64",
        dict(
            type_name='uint64',
            exp_type_obj=Uint64,
        ),
        None, None, True
    ),
    (
        "Type name is sint8",
        dict(
            type_name='sint8',
            exp_type_obj=Sint8,
        ),
        None, None, True
    ),
    (
        "Type name is sint16",
        dict(
            type_name='sint16',
            exp_type_obj=Sint16,
        ),
        None, None, True
    ),
    (
        "Type name is sint32",
        dict(
            type_name='sint32',
            exp_type_obj=Sint32,
        ),
        None, None, True
    ),
    (
        "Type name is sint64",
        dict(
            type_name='sint64',
            exp_type_obj=Sint64,
        ),
        None, None, True
    ),
    (
        "Type name is real32",
        dict(
            type_name='real32',
            exp_type_obj=Real32,
        ),
        None, None, True
    ),
    (
        "Type name is real64",
        dict(
            type_name='real64',
            exp_type_obj=Real64,
        ),
        None, None, True
    ),
    (
        "Type name is string",
        dict(
            type_name='string',
            exp_type_obj=six.text_type,
        ),
        None, None, True
    ),
    (
        "Type name is char16",
        dict(
            type_name='char16',
            exp_type_obj=six.text_type,
        ),
        None, None, True
    ),
    (
        "Type name is datetime",
        dict(
            type_name='datetime',
            exp_type_obj=CIMDateTime,
        ),
        None, None, True
    ),
    (
        "Type name is reference",
        dict(
            type_name='reference',
            exp_type_obj=CIMInstanceName,
        ),
        None, None, True
    ),

]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_TYPE_FROM_NAME)
@simplified_test_function
def test_type_from_name(testcase, type_name, exp_type_obj):
    """
    Test function for type_from_name().
    """

    # The code to be tested
    type_obj = type_from_name(type_name)

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None

    assert type_obj is exp_type_obj


# TODO: Add tests for atomic_to_cim_xml()
