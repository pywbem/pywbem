"""
Test functions in _units module
"""

from __future__ import absolute_import

import pytest

from ..utils.pytest_extensions import simplified_test_function

# pylint: disable=wrong-import-position, wrong-import-order, invalid-name
from ...utils import import_installed
pywbem = import_installed('pywbem')
from pywbem import CIMProperty, CIMMethod, CIMParameter, CIMQualifier, \
    siunit_obj, siunit  # noqa: E402
# pylint: enable=wrong-import-position, wrong-import-order, invalid-name


# Some qualifier objects used for test cases
TEST_QUAL_PUNIT1_BYTE = CIMQualifier('PUnit', value='byte')
TEST_QUAL_PUNIT2_BYTE = CIMQualifier('pUnIt', value='byte')
TEST_QUAL_UNITS1_BYTES = CIMQualifier('Units', value='Bytes')
TEST_QUAL_UNITS2_BYTES = CIMQualifier('uNiTs', value='Bytes')
TEST_QUAL_UNITS_METERS = CIMQualifier('Units', value='Meters')


TESTCASES_SIUNIT_OBJ = [

    # Testcases for siunit_obj(), that test general behavior.

    # Each list item is a testcase tuple with these items:
    # * desc: Short testcase description.
    # * kwargs: Keyword arguments for the test function:
    #   * in_kwargs: Keyword arguments for siunit().
    #   * exp_result: Expected return value of siunit(), or None.
    # * exp_exc_types: Expected exception type(s), or None.
    # * exp_warn_types: Expected warning type(s), or None.
    # * condition: Boolean condition for testcase to run, or 'pdb' for debugger

    (
        "No input argument (cim_obj is required)",
        dict(
            in_kwargs={},
            exp_result=None,
        ),
        TypeError, None, True
    ),
    (
        "cim_obj is None",
        dict(
            in_kwargs=dict(
                cim_obj=None,
            ),
            exp_result=None,
        ),
        TypeError, None, True
    ),
    (
        "cim_obj has invalid type",
        dict(
            in_kwargs=dict(
                cim_obj=42,
            ),
            exp_result=None,
        ),
        TypeError, None, True
    ),
    (
        "cim_obj is CIMProperty with PUnit #1 (byte)",
        dict(
            in_kwargs=dict(
                cim_obj=CIMProperty(
                    'P1', value='foo',
                    qualifiers=[TEST_QUAL_PUNIT1_BYTE])
            ),
            exp_result=u'B',
        ),
        None, None, True
    ),
    (
        "cim_obj is CIMMethod with PUnit #1 (byte)",
        dict(
            in_kwargs=dict(
                cim_obj=CIMMethod(
                    'P1', return_type='uint32',
                    qualifiers=[TEST_QUAL_PUNIT1_BYTE])
            ),
            exp_result=u'B',
        ),
        None, None, True
    ),
    (
        "cim_obj is CIMParameter with PUnit #1 (byte)",
        dict(
            in_kwargs=dict(
                cim_obj=CIMParameter(
                    'P1', type='uint32',
                    qualifiers=[TEST_QUAL_PUNIT1_BYTE])
            ),
            exp_result=u'B',
        ),
        None, None, True
    ),
    (
        "cim_obj is CIMProperty with PUnit #2 (byte)",
        dict(
            in_kwargs=dict(
                cim_obj=CIMProperty(
                    'P1', value='foo',
                    qualifiers=[TEST_QUAL_PUNIT2_BYTE])
            ),
            exp_result=u'B',
        ),
        None, None, True
    ),
    (
        "cim_obj is CIMProperty with Units #1 (Bytes)",
        dict(
            in_kwargs=dict(
                cim_obj=CIMProperty(
                    'P1', value='foo',
                    qualifiers=[TEST_QUAL_UNITS1_BYTES])
            ),
            exp_result=u'B',
        ),
        None, None, True
    ),
    (
        "cim_obj is CIMProperty with Units #2 (Bytes)",
        dict(
            in_kwargs=dict(
                cim_obj=CIMProperty(
                    'P1', value='foo',
                    qualifiers=[TEST_QUAL_UNITS2_BYTES])
            ),
            exp_result=u'B',
        ),
        None, None, True
    ),
    (
        "cim_obj is CIMProperty with PUnit #1 (byte) and Units (Meters)",
        dict(
            in_kwargs=dict(
                cim_obj=CIMProperty(
                    'P1', value='foo',
                    qualifiers=[TEST_QUAL_PUNIT1_BYTE, TEST_QUAL_UNITS_METERS])
            ),
            exp_result=u'B',
        ),
        None, None, True
    ),
    (
        "cim_obj is CIMProperty with Units (Meters) and PUnit #1 (byte)",
        dict(
            in_kwargs=dict(
                cim_obj=CIMProperty(
                    'P1', value='foo',
                    qualifiers=[TEST_QUAL_UNITS_METERS, TEST_QUAL_PUNIT1_BYTE])
            ),
            exp_result=u'B',
        ),
        None, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_SIUNIT_OBJ)
@simplified_test_function
def test_siunit_obj(testcase, in_kwargs, exp_result):
    """
    Test function for siunit_obj().
    """

    # The code to be tested
    result = siunit_obj(**in_kwargs)

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None

    assert result == exp_result


TESTCASES_SIUNIT_GENERAL = [

    # Testcases for siunit(), that test general behavior.

    # Each list item is a testcase tuple with these items:
    # * desc: Short testcase description.
    # * kwargs: Keyword arguments for the test function:
    #   * in_kwargs: Keyword arguments for siunit().
    #   * exp_result: Expected return value of siunit(), or None.
    # * exp_exc_types: Expected exception type(s), or None.
    # * exp_warn_types: Expected warning type(s), or None.
    # * condition: Boolean condition for testcase to run, or 'pdb' for debugger

    (
        "No input arguments",
        dict(
            in_kwargs={},
            exp_result=None,
        ),
        None, None, True
    ),
    (
        "PUnit '' (empty string)",
        dict(
            in_kwargs=dict(
                punit="",
            ),
            exp_result=u'',
        ),
        None, None, True
    ),
    (
        "PUnit 'byte' as Unicode string",
        dict(
            in_kwargs=dict(
                punit=u"byte",
            ),
            exp_result=u'B',
        ),
        None, None, True
    ),
    (
        "PUnit 'byte' as binary string",
        dict(
            in_kwargs=dict(
                punit=b"byte",
            ),
            exp_result=u'B',
        ),
        None, None, True
    ),
    (
        "Units 'Bytes' as Unicode string",
        dict(
            in_kwargs=dict(
                units=u"Bytes",
            ),
            exp_result=u'B',
        ),
        None, None, True
    ),
    (
        "Units 'Bytes' as binary string",
        dict(
            in_kwargs=dict(
                units=b"Bytes",
            ),
            exp_result=u'B',
        ),
        None, None, True
    ),
    (
        "PUnit has precedence over Units",
        dict(
            in_kwargs=dict(
                punit="byte",
                units="Meters",
            ),
            exp_result=u'B',
        ),
        None, None, True
    ),
    (
        "PUnit 'degree' with use_ascii omitted is returned as Unicode char",
        dict(
            in_kwargs=dict(
                punit="degree",
            ),
            exp_result=u'\u00B0',
        ),
        None, None, True
    ),
    (
        "PUnit 'degree' with use_ascii=False is returned as Unicode char",
        dict(
            in_kwargs=dict(
                punit="degree",
                use_ascii=False,
            ),
            exp_result=u'\u00B0',
        ),
        None, None, True
    ),
    (
        "PUnit 'degree' with use_ascii=True is returned as 7-bit ASCII text",
        dict(
            in_kwargs=dict(
                punit="degree",
                use_ascii=True,
            ),
            exp_result=u'deg',
        ),
        None, None, True
    ),
    (
        "PUnit 'degree celsius' with use_ascii=True",
        dict(
            in_kwargs=dict(
                punit="degree celsius",
                use_ascii=True,
            ),
            exp_result=u'degC',
        ),
        None, None, True
    ),
    (
        "PUnit 'degree fahrenheit' with use_ascii=True",
        dict(
            in_kwargs=dict(
                punit="degree fahrenheit",
                use_ascii=True,
            ),
            exp_result=u'degF',
        ),
        None, None, True
    ),
    (
        "PUnit 'ohm' with use_ascii=True",
        dict(
            in_kwargs=dict(
                punit="ohm",
                use_ascii=True,
            ),
            exp_result=u'Ohm',
        ),
        None, None, True
    ),
    (
        "PUnit 'permille' with use_ascii=True",
        dict(
            in_kwargs=dict(
                punit="permille",
                use_ascii=True,
            ),
            exp_result=u'1/1000',
        ),
        None, None, True
    ),
    (
        "PUnit 'meter * meter' with use_ascii=True",
        dict(
            in_kwargs=dict(
                punit="meter * meter",
                use_ascii=True,
            ),
            exp_result=u'm^2',
        ),
        None, None, True
    ),
    (
        "PUnit 'meter * meter * meter' with use_ascii=True",
        dict(
            in_kwargs=dict(
                punit="meter * meter * meter",
                use_ascii=True,
            ),
            exp_result=u'm^3',
        ),
        None, None, True
    ),
    (
        "Invalid type for punit argument",
        dict(
            in_kwargs=dict(
                punit=42,
            ),
            exp_result=None,
        ),
        TypeError, None, True
    ),
    (
        "Invalid type for units argument",
        dict(
            in_kwargs=dict(
                units=42,
            ),
            exp_result=None,
        ),
        TypeError, None, True
    ),
    (
        "Invalid PUnit format",
        dict(
            in_kwargs=dict(
                punit="byte + byte",
            ),
            exp_result=None,
        ),
        ValueError, None, True
    ),
    (
        "Invalid PUnit base unit",
        dict(
            in_kwargs=dict(
                punit="peanuts",
            ),
            exp_result=None,
        ),
        ValueError, None, True
    ),
    (
        "PUnit with modifier1 (* unknown value)",
        dict(
            in_kwargs=dict(
                punit="second * 10000",
            ),
            exp_result=u'10000 s',
        ),
        None, None, True
    ),
    (
        "PUnit with modifier1 (/ unknown value)",
        dict(
            in_kwargs=dict(
                punit="second / 10000",
            ),
            exp_result=u'1/10000 s',
        ),
        None, None, True
    ),
    (
        "PUnit with modifier2 (* unknown value)",
        dict(
            in_kwargs=dict(
                punit="second * 10 ^ 4",
            ),
            exp_result=u'10^4 s',
        ),
        None, None, True
    ),
    (
        "PUnit with modifier2 (/ unknown value)",
        dict(
            in_kwargs=dict(
                punit="second / 10 ^ 4",
            ),
            exp_result=u'10^-4 s',
        ),
        None, None, True
    ),
    (
        "PUnit with modifier1 (* known value) and modifier2 (* known + exp)",
        dict(
            in_kwargs=dict(
                punit="second * 10 * 10 ^ 3",
            ),
            exp_result=u'10 ks',
        ),
        None, None, True
    ),
    (
        "PUnit with modifier1 (/ known value) and modifier2 (/ known + exp)",
        dict(
            in_kwargs=dict(
                punit="second / 10 / 10 ^ 3",
            ),
            exp_result=u'1/10 ms',
        ),
        None, None, True
    ),
    (
        "PUnit with modifier1 (* known value) and modifier2 (* known - exp)",
        dict(
            in_kwargs=dict(
                punit="second * 10 * 10 ^ -3",
            ),
            exp_result=u'10 ms',
        ),
        None, None, True
    ),
    (
        "PUnit with modifier1 (/ known value) and modifier2 (/ known - exp)",
        dict(
            in_kwargs=dict(
                punit="second / 10 / 10 ^ -3",
            ),
            exp_result=u'1/10 ks',
        ),
        None, None, True
    ),
    (
        "PUnit with modifier1 (* known value) and modifier2 (* unknown value)",
        dict(
            in_kwargs=dict(
                punit="second * 1000 * 10 ^ 4",
            ),
            exp_result=u'1000 10^4 s',
        ),
        None, None, True
    ),
    (
        "PUnit with modifier1 (/ known value) and modifier2 (/ unknown value)",
        dict(
            in_kwargs=dict(
                punit="second / 1000 / 10 ^ 4",
            ),
            exp_result=u'1/1000 10^-4 s',
        ),
        None, None, True
    ),
    (
        "PUnit with modifier1 (* unknown value) and modifier2 (* known value)",
        dict(
            in_kwargs=dict(
                punit="second * 10000 * 10 ^ 3",
            ),
            exp_result=u'10000 ks',
        ),
        None, None, True
    ),
    (
        "PUnit with modifier1 (/ unknown value) and modifier2 (/ known value)",
        dict(
            in_kwargs=dict(
                punit="second / 10000 / 10 ^ 3",
            ),
            exp_result=u'1/10000 ms',
        ),
        None, None, True
    ),
    (
        "PUnit with extended format (unit1 * mod1 / unit2)",
        dict(
            in_kwargs=dict(
                punit="meter * 1000 / second",
            ),
            exp_result=u'km/s',
        ),
        None, None, True
    ),
    (
        "PUnit with extended format (unit1 / mod2 * unit2)",
        dict(
            in_kwargs=dict(
                punit="watt / 10^3 * second",
            ),
            exp_result=u'mWs',
        ),
        None, None, True
    ),
    (
        "PUnit with extended format (unit1 / mod1 * mod2 / unit2)",
        dict(
            in_kwargs=dict(
                punit="meter / 10 * 10^3 / second",
            ),
            exp_result=u'1/10 km/s',
        ),
        None, None, True
    ),
    (
        "PUnit with invalid extended format (more than one mod1)",
        dict(
            in_kwargs=dict(
                punit="watt / 10 / 100",
            ),
            exp_result=None,
        ),
        ValueError, None, True
    ),
    (
        "PUnit with invalid extended format (more than one mod2)",
        dict(
            in_kwargs=dict(
                punit="watt / 10^1 / 10^2",
            ),
            exp_result=None,
        ),
        ValueError, None, True
    ),
    (
        "Invalid Units value",
        dict(
            in_kwargs=dict(
                units="Peanuts",
            ),
            exp_result=None,
        ),
        ValueError, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_SIUNIT_GENERAL)
@simplified_test_function
def test_siunit_general(testcase, in_kwargs, exp_result):
    """
    Test function for siunit(), that test general behavior.
    """

    # The code to be tested
    result = siunit(**in_kwargs)

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None

    assert result == exp_result


TESTCASES_SIUNIT_PUNIT = [

    # Testcases for siunit(), that test only good cases with PUnit values.

    # Each list item is a testcase tuple with these items:
    # * punit: Input value for punit parameter of siunit().
    # * exp_result: Expected return value of siunit().

    # All single units
    ("percent", u"%"),
    ("permille", u"\u2030"),
    ("decibel", u"dB"),
    ("count", u""),
    ("revolution", u"rev"),
    ("degree", u"\u00B0"),
    ("radian", u"rad"),
    ("steradian", u"sr"),
    ("bit", u"bit"),
    ("byte", u"B"),
    ("dataword", u"word"),
    ("MSU", u"MSU"),
    ("meter", u"m"),
    ("inch", u"in"),
    ("rack unit", u"U"),
    ("foot", u"ft"),
    ("yard", u"yd"),
    ("mile", u"mi"),
    ("liter", u"l"),
    ("fluid ounce", u"fl.oz"),
    ("liquid gallon", u"gal"),
    ("mole", u"mol"),
    ("kilogram", u"kg"),
    ("ounce", u"oz"),
    ("pound", u"lb"),
    ("second", u"s"),
    ("minute", u"min"),
    ("hour", u"h"),
    ("day", u"d"),
    ("week", u"week"),
    ("gravity", u"g"),
    ("degree celsius", u"\u00B0C"),
    ("degree fahrenheit", u"\u00B0F"),
    ("kelvin", u"K"),
    ("candela", u"cd"),
    ("lumen", u"lm"),
    ("nit", u"nit"),
    ("lux", u"lx"),
    ("newton", u"N"),
    ("pascal", u"Pa"),
    ("bar", u"bar"),
    ("decibel(A)", u"dB(A)"),
    ("decibel (A)", u"dB(A)"),
    ("decibel(C)", u"dB(C)"),
    ("decibel (C)", u"dB(C)"),
    ("joule", u"J"),
    ("watt", u"W"),
    ("volt ampere", u"VA"),
    ("volt ampere reactive", u"var"),
    ("decibel(m)", u"dBm"),
    ("decibel (m)", u"dBm"),
    ("british thermal unit", u"BTU"),
    ("ampere", u"A"),
    ("coulomb", u"C"),
    ("volt", u"V"),
    ("farad", u"F"),
    ("ohm", u"\u2126"),
    ("siemens", u"S"),
    ("weber", u"Wb"),
    ("tesla", u"T"),
    ("henry", u"H"),
    ("becquerel", u"Bq"),
    ("gray", u"Gy"),
    ("sievert", u"Sv"),

    # Multiple same units combined (using powers), without modifiers
    ("meter*meter", u"m\u00B2"),
    ("meter * meter", u"m\u00B2"),
    ("meter * meter * meter", u"m\u00B3"),
    ("meter * meter * meter * meter", u"m^4"),
    ("meter / second / second", u"m/s\u00B2"),
    ("meter * meter / second / second / second", u"m\u00B2/s\u00B3"),
    ("meter * meter * meter / second / second / second / second",
     u"m\u00B3/s^4"),

    # Multiple units combined, without powers, without modifiers
    ("meter/second", u"m/s"),
    ("meter / second", u"m/s"),
    ("newton * meter", u"Nm"),
    ("newton * meter / second", u"Nm/s"),
    ("newton * meter / second / byte", u"Nm/sB"),
    ("meter * newton / byte / second", u"mN/Bs"),

    # Using modifier1
    ("byte*1024", u"KiB"),
    ("byte * 1024", u"KiB"),
    ("meter / second * 1000", u"km/s"),
    ("meter / second * 100", u"hm/s"),
    ("meter / second * 10", u"dam/s"),
    ("meter / second * 1", u"m/s"),
    ("meter / second / 1", u"m/s"),
    ("meter / second / 10", u"dm/s"),
    ("meter / second / 100", u"cm/s"),
    ("meter / second / 1000", u"mm/s"),

    # Using modifier2
    ("byte*10^3", u"kB"),
    ("byte * 10^3", u"kB"),
    ("byte * 10 ^ 3", u"kB"),
    ("byte * 2 ^ 80", u"YiB"),
    ("byte * 2 ^ 70", u"ZiB"),
    ("byte * 2 ^ 60", u"EiB"),
    ("byte * 2 ^ 50", u"PiB"),
    ("byte * 2 ^ 40", u"TiB"),
    ("byte * 2 ^ 30", u"GiB"),
    ("byte * 2 ^ 20", u"MiB"),
    ("byte * 2 ^ 10", u"KiB"),
    ("byte * 10 ^ 24", u"YB"),
    ("byte * 10 ^ 21", u"ZB"),
    ("byte * 10 ^ 18", u"EB"),
    ("byte * 10 ^ 15", u"PB"),
    ("byte * 10 ^ 12", u"TB"),
    ("byte * 10 ^ 9", u"GB"),
    ("byte * 10 ^ 6", u"MB"),
    ("byte * 10 ^ 3", u"kB"),
    ("byte * 10 ^ 2", u"hB"),
    ("byte * 10 ^ 1", u"daB"),
    ("byte * 10 ^ -1", u"dB"),
    ("byte * 10 ^ -2", u"cB"),
    ("byte * 10 ^ -3", u"mB"),
    ("byte * 10 ^ -6", u"uB"),
    ("byte * 10 ^ -9", u"nB"),
    ("byte * 10 ^ -12", u"pB"),
    ("byte * 10 ^ -15", u"fB"),
    ("byte * 10 ^ -18", u"aB"),
    ("byte * 10 ^ -21", u"zB"),
    ("byte * 10 ^ -24", u"yB"),

    # Using modifier1 and modifier2
    ("byte*2*10^3", u"2 kB"),
    ("byte * 2 * 10 ^ 3", u"2 kB"),
    ("byte * 10 * 10 ^ 3", u"10 kB"),
]


@pytest.mark.parametrize(
    "punit, exp_result",
    TESTCASES_SIUNIT_PUNIT)
def test_siunit_punit(punit, exp_result):
    """
    Test function for siunit(), that test only good cases with PUnit values.
    """

    # The code to be tested
    result = siunit(punit=punit)

    assert result == exp_result


TESTCASES_SIUNIT_UNITS = [

    # Testcases for siunit(), that test only good cases with Units values.

    # Each list item is a testcase tuple with these items:
    # * units: Input value for units parameter of siunit().
    # * exp_result: Expected return value of siunit().

    # All units defined in DSP0004

    ("Bits", u"bit"),
    ("KiloBits", u"kbit"),
    ("MegaBits", u"Mbit"),
    ("GigaBits", u"Gbit"),

    ("Bits per Second", u"bit/s"),
    ("KiloBits per Second", u"kbit/s"),
    ("MegaBits per Second", u"Mbit/s"),
    ("GigaBits per Second", u"Gbit/s"),

    ("Bytes", u"B"),
    ("KiloBytes", u"kB"),
    ("MegaBytes", u"MB"),
    ("GigaBytes", u"GB"),
    ("Words", u"words"),
    ("DoubleWords", u"doublewords"),
    ("QuadWords", u"quadwords"),

    ("Degrees C", u"\u00B0C"),
    ("Tenths of Degrees C", u"1/10 \u00B0C"),
    ("Hundredths of Degrees C", u"1/100 \u00B0C"),
    ("Degrees F", u"\u00B0F"),
    ("Tenths of Degrees F", u"1/10 \u00B0F"),
    ("Hundredths of Degrees F", u"1/100 \u00B0F"),
    ("Degrees K", u"K"),
    ("Tenths of Degrees K", u"1/10 K"),
    ("Hundredths of Degrees K", u"1/100 K"),
    ("Color Temperature", u"K"),

    ("Volts", u"V"),
    ("MilliVolts", u"mV"),
    ("Tenths of MilliVolts", u"1/10 mV"),
    ("Amps", u"A"),
    ("MilliAmps", u"mA"),
    ("Tenths of MilliAmps", u"1/10 mA"),
    ("Watts", u"W"),
    ("MilliWattHours", u"mWh"),

    ("Joules", u"J"),
    ("Coulombs", u"C"),
    ("Newtons", u"N"),

    ("Lumen", u"lm"),
    ("Lux", u"lx"),
    ("Candelas", u"cd"),

    ("Pounds", u"lb"),
    ("Pounds per Square Inch", u"lb/in\u00B2"),

    ("Cycles", u"cycles"),
    ("Revolutions", u"rev"),
    ("Revolutions per Minute", u"RPM"),
    ("Revolutions per Second", u"rev/s"),

    ("Minutes", u"min"),
    ("Seconds", u"s"),
    ("Tenths of Seconds", u"1/10 s"),
    ("Hundredths of Seconds", u"1/100 s"),
    ("MicroSeconds", u"\u00B5s"),
    ("MilliSeconds", u"ms"),
    ("NanoSeconds", u"ns"),

    ("Hours", u"h"),
    ("Days", u"d"),
    ("Weeks", u"week"),

    ("Hertz", u"Hz"),
    ("MegaHertz", u"MHz"),

    ("Pixels", u"px"),
    ("Pixels per Inch", u"px/in"),

    ("Counts per Inch", u"counts/in"),

    ("Percent", u"%"),
    ("Tenths of Percent", u"1/10 %"),
    ("Hundredths of Percent", u"1/100 %"),
    ("Thousandths", u"\u2030"),

    ("Meters", u"m"),
    ("Centimeters", u"cm"),
    ("Millimeters", u"mm"),
    ("Cubic Meters", u"m\u00B3"),
    ("Cubic Centimeters", u"cm\u00B3"),
    ("Cubic Millimeters", u"mm\u00B3"),

    ("Inches", u"in"),
    ("Feet", u"ft"),
    ("Cubic Inches", u"in\u00B3"),
    ("Cubic Feet", u"ft\u00B3"),
    ("Ounces", u"oz"),
    ("Liters", u"l"),
    ("Fluid Ounces", u"fl.oz"),

    ("Radians", u"rad"),
    ("Steradians", u"sr"),
    ("Degrees", u"\u00B0"),

    ("Gravities", u"g"),
    ("Pounds", u"lb"),
    ("Foot-Pounds", u"ft.lb"),

    ("Gauss", u"G"),
    ("Gilberts", u"Gb"),
    ("Henrys", u"H"),
    ("MilliHenrys", u"mH"),
    ("Farads", u"F"),
    ("MilliFarads", u"mF"),
    ("MicroFarads", u"\u00B5F"),
    ("PicoFarads", u"pF"),

    ("Ohms", u"\u2126"),
    ("Siemens", u"S"),

    ("Moles", u"mol"),
    ("Becquerels", u"Bq"),
    ("Parts per Million", u"ppm"),

    ("Decibels", u"dB"),
    ("Tenths of Decibels", u"1/10 dB"),

    ("Grays", u"Gy"),
    ("Sieverts", u"Sv"),

    ("MilliWatts", u"mW"),

    ("DBm", u"dBm"),

    ("Bytes per Second", u"B/s"),
    ("KiloBytes per Second", u"kB/s"),
    ("MegaBytes per Second", u"MB/s"),
    ("GigaBytes per Second", u"GB/s"),

    ("BTU per Hour", u"BTU/h"),

    ("PCI clock cycles", u"PCI clock cycles"),

    ("250 NanoSeconds", u"250 ns"),

    ("Us", u"U"),

    ("Amps at 120 Volts", u"A (@120V)"),

    ("Clock Ticks", u"clock ticks"),

    ("Packets", u"packets"),
    ("per Thousand Packets", u"/1000 packets"),

    # Additional values found in the DMTF CIM Schema (as of its version 2.49)
    # that are not defined as valid values in Annex C.2 of DSP0004 version 2.8
    ("-dBm", u"-dBm"),
    ("Blocks", u"blocks"),
    ("Percentage", u"%"),
    ("Proportion", u"proportion"),
    ("Tenths of Revolutions per Minute", u"1/10 RPM"),
]


@pytest.mark.parametrize(
    "units, exp_result",
    TESTCASES_SIUNIT_UNITS)
def test_siunit_units(units, exp_result):
    """
    Test function for siunit(), that test only good cases with Units values.
    """

    # The code to be tested
    result = siunit(units=units)

    assert result == exp_result
