"""
Test functions in _units module
"""


import pytest

from ..utils.pytest_extensions import simplified_test_function

# pylint: disable=wrong-import-position, wrong-import-order, invalid-name
from ...utils import import_installed
pywbem = import_installed('pywbem')
from pywbem import CIMProperty, CIMMethod, CIMParameter, CIMQualifier, \
    siunit_obj, siunit  # noqa: E402
# pylint: enable=wrong-import-position, wrong-import-order, invalid-name

# Literal form {"blah: 0} faster than dict(blah=0) but same functionality
# pylint: disable=use-dict-literal

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
            exp_result='B',
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
            exp_result='B',
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
            exp_result='B',
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
            exp_result='B',
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
            exp_result='B',
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
            exp_result='B',
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
            exp_result='B',
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
            exp_result='B',
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
            exp_result='',
        ),
        None, None, True
    ),
    (
        "PUnit 'byte' as Unicode string",
        dict(
            in_kwargs=dict(
                punit="byte",
            ),
            exp_result='B',
        ),
        None, None, True
    ),
    (
        "PUnit 'byte' as binary string",
        dict(
            in_kwargs=dict(
                punit=b"byte",
            ),
            exp_result='B',
        ),
        None, None, True
    ),
    (
        "Units 'Bytes' as Unicode string",
        dict(
            in_kwargs=dict(
                units="Bytes",
            ),
            exp_result='B',
        ),
        None, None, True
    ),
    (
        "Units 'Bytes' as binary string",
        dict(
            in_kwargs=dict(
                units=b"Bytes",
            ),
            exp_result='B',
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
            exp_result='B',
        ),
        None, None, True
    ),
    (
        "PUnit 'degree' with use_ascii omitted is returned as Unicode char",
        dict(
            in_kwargs=dict(
                punit="degree",
            ),
            exp_result='\u00B0',
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
            exp_result='\u00B0',
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
            exp_result='deg',
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
            exp_result='degC',
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
            exp_result='degF',
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
            exp_result='Ohm',
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
            exp_result='1/1000',
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
            exp_result='m^2',
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
            exp_result='m^3',
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
            exp_result='10000 s',
        ),
        None, None, True
    ),
    (
        "PUnit with modifier1 (/ unknown value)",
        dict(
            in_kwargs=dict(
                punit="second / 10000",
            ),
            exp_result='1/10000 s',
        ),
        None, None, True
    ),
    (
        "PUnit with modifier2 (* unknown value)",
        dict(
            in_kwargs=dict(
                punit="second * 10 ^ 4",
            ),
            exp_result='10^4 s',
        ),
        None, None, True
    ),
    (
        "PUnit with modifier2 (/ unknown value)",
        dict(
            in_kwargs=dict(
                punit="second / 10 ^ 4",
            ),
            exp_result='10^-4 s',
        ),
        None, None, True
    ),
    (
        "PUnit with modifier1 (* known value) and modifier2 (* known + exp)",
        dict(
            in_kwargs=dict(
                punit="second * 10 * 10 ^ 3",
            ),
            exp_result='10 ks',
        ),
        None, None, True
    ),
    (
        "PUnit with modifier1 (/ known value) and modifier2 (/ known + exp)",
        dict(
            in_kwargs=dict(
                punit="second / 10 / 10 ^ 3",
            ),
            exp_result='1/10 ms',
        ),
        None, None, True
    ),
    (
        "PUnit with modifier1 (* known value) and modifier2 (* known - exp)",
        dict(
            in_kwargs=dict(
                punit="second * 10 * 10 ^ -3",
            ),
            exp_result='10 ms',
        ),
        None, None, True
    ),
    (
        "PUnit with modifier1 (/ known value) and modifier2 (/ known - exp)",
        dict(
            in_kwargs=dict(
                punit="second / 10 / 10 ^ -3",
            ),
            exp_result='1/10 ks',
        ),
        None, None, True
    ),
    (
        "PUnit with modifier1 (* known value) and modifier2 (* unknown value)",
        dict(
            in_kwargs=dict(
                punit="second * 1000 * 10 ^ 4",
            ),
            exp_result='1000 10^4 s',
        ),
        None, None, True
    ),
    (
        "PUnit with modifier1 (/ known value) and modifier2 (/ unknown value)",
        dict(
            in_kwargs=dict(
                punit="second / 1000 / 10 ^ 4",
            ),
            exp_result='1/1000 10^-4 s',
        ),
        None, None, True
    ),
    (
        "PUnit with modifier1 (* unknown value) and modifier2 (* known value)",
        dict(
            in_kwargs=dict(
                punit="second * 10000 * 10 ^ 3",
            ),
            exp_result='10000 ks',
        ),
        None, None, True
    ),
    (
        "PUnit with modifier1 (/ unknown value) and modifier2 (/ known value)",
        dict(
            in_kwargs=dict(
                punit="second / 10000 / 10 ^ 3",
            ),
            exp_result='1/10000 ms',
        ),
        None, None, True
    ),
    (
        "PUnit with extended format (unit1 * mod1 / unit2)",
        dict(
            in_kwargs=dict(
                punit="meter * 1000 / second",
            ),
            exp_result='km/s',
        ),
        None, None, True
    ),
    (
        "PUnit with extended format (unit1 / mod2 * unit2)",
        dict(
            in_kwargs=dict(
                punit="watt / 10^3 * second",
            ),
            exp_result='mWs',
        ),
        None, None, True
    ),
    (
        "PUnit with extended format (unit1 / mod1 * mod2 / unit2)",
        dict(
            in_kwargs=dict(
                punit="meter / 10 * 10^3 / second",
            ),
            exp_result='1/10 km/s',
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
    ("percent", "%"),
    ("permille", "\u2030"),
    ("decibel", "dB"),
    ("count", ""),
    ("revolution", "rev"),
    ("degree", "\u00B0"),
    ("radian", "rad"),
    ("steradian", "sr"),
    ("bit", "bit"),
    ("byte", "B"),
    ("dataword", "word"),
    ("MSU", "MSU"),
    ("meter", "m"),
    ("inch", "in"),
    ("rack unit", "U"),
    ("foot", "ft"),
    ("yard", "yd"),
    ("mile", "mi"),
    ("liter", "l"),
    ("fluid ounce", "fl.oz"),
    ("liquid gallon", "gal"),
    ("mole", "mol"),
    ("kilogram", "kg"),
    ("ounce", "oz"),
    ("pound", "lb"),
    ("second", "s"),
    ("minute", "min"),
    ("hour", "h"),
    ("day", "d"),
    ("week", "week"),
    ("gravity", "g"),
    ("degree celsius", "\u00B0C"),
    ("degree fahrenheit", "\u00B0F"),
    ("kelvin", "K"),
    ("candela", "cd"),
    ("lumen", "lm"),
    ("nit", "nit"),
    ("lux", "lx"),
    ("newton", "N"),
    ("pascal", "Pa"),
    ("bar", "bar"),
    ("decibel(A)", "dB(A)"),
    ("decibel (A)", "dB(A)"),
    ("decibel(C)", "dB(C)"),
    ("decibel (C)", "dB(C)"),
    ("joule", "J"),
    ("watt", "W"),
    ("volt ampere", "VA"),
    ("volt ampere reactive", "var"),
    ("decibel(m)", "dBm"),
    ("decibel (m)", "dBm"),
    ("british thermal unit", "BTU"),
    ("ampere", "A"),
    ("coulomb", "C"),
    ("volt", "V"),
    ("farad", "F"),
    ("ohm", "\u2126"),
    ("siemens", "S"),
    ("weber", "Wb"),
    ("tesla", "T"),
    ("henry", "H"),
    ("becquerel", "Bq"),
    ("gray", "Gy"),
    ("sievert", "Sv"),

    # Multiple same units combined (using powers), without modifiers
    ("meter*meter", "m\u00B2"),
    ("meter * meter", "m\u00B2"),
    ("meter * meter * meter", "m\u00B3"),
    ("meter * meter * meter * meter", "m^4"),
    ("meter / second / second", "m/s\u00B2"),
    ("meter * meter / second / second / second", "m\u00B2/s\u00B3"),
    ("meter * meter * meter / second / second / second / second",
     "m\u00B3/s^4"),

    # Multiple units combined, without powers, without modifiers
    ("meter/second", "m/s"),
    ("meter / second", "m/s"),
    ("newton * meter", "Nm"),
    ("newton * meter / second", "Nm/s"),
    ("newton * meter / second / byte", "Nm/sB"),
    ("meter * newton / byte / second", "mN/Bs"),

    # Using modifier1
    ("byte*1024", "KiB"),
    ("byte * 1024", "KiB"),
    ("meter / second * 1000", "km/s"),
    ("meter / second * 100", "hm/s"),
    ("meter / second * 10", "dam/s"),
    ("meter / second * 1", "m/s"),
    ("meter / second / 1", "m/s"),
    ("meter / second / 10", "dm/s"),
    ("meter / second / 100", "cm/s"),
    ("meter / second / 1000", "mm/s"),

    # Using modifier2
    ("byte*10^3", "kB"),
    ("byte * 10^3", "kB"),
    ("byte * 10 ^ 3", "kB"),
    ("byte * 2 ^ 80", "YiB"),
    ("byte * 2 ^ 70", "ZiB"),
    ("byte * 2 ^ 60", "EiB"),
    ("byte * 2 ^ 50", "PiB"),
    ("byte * 2 ^ 40", "TiB"),
    ("byte * 2 ^ 30", "GiB"),
    ("byte * 2 ^ 20", "MiB"),
    ("byte * 2 ^ 10", "KiB"),
    ("byte * 10 ^ 24", "YB"),
    ("byte * 10 ^ 21", "ZB"),
    ("byte * 10 ^ 18", "EB"),
    ("byte * 10 ^ 15", "PB"),
    ("byte * 10 ^ 12", "TB"),
    ("byte * 10 ^ 9", "GB"),
    ("byte * 10 ^ 6", "MB"),
    ("byte * 10 ^ 3", "kB"),
    ("byte * 10 ^ 2", "hB"),
    ("byte * 10 ^ 1", "daB"),
    ("byte * 10 ^ -1", "dB"),
    ("byte * 10 ^ -2", "cB"),
    ("byte * 10 ^ -3", "mB"),
    ("byte * 10 ^ -6", "uB"),
    ("byte * 10 ^ -9", "nB"),
    ("byte * 10 ^ -12", "pB"),
    ("byte * 10 ^ -15", "fB"),
    ("byte * 10 ^ -18", "aB"),
    ("byte * 10 ^ -21", "zB"),
    ("byte * 10 ^ -24", "yB"),

    # Using modifier1 and modifier2
    ("byte*2*10^3", "2 kB"),
    ("byte * 2 * 10 ^ 3", "2 kB"),
    ("byte * 10 * 10 ^ 3", "10 kB"),
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

    ("Bits", "bit"),
    ("KiloBits", "kbit"),
    ("MegaBits", "Mbit"),
    ("GigaBits", "Gbit"),

    ("Bits per Second", "bit/s"),
    ("KiloBits per Second", "kbit/s"),
    ("MegaBits per Second", "Mbit/s"),
    ("GigaBits per Second", "Gbit/s"),

    ("Bytes", "B"),
    ("KiloBytes", "kB"),
    ("MegaBytes", "MB"),
    ("GigaBytes", "GB"),
    ("Words", "words"),
    ("DoubleWords", "doublewords"),
    ("QuadWords", "quadwords"),

    ("Degrees C", "\u00B0C"),
    ("Tenths of Degrees C", "1/10 \u00B0C"),
    ("Hundredths of Degrees C", "1/100 \u00B0C"),
    ("Degrees F", "\u00B0F"),
    ("Tenths of Degrees F", "1/10 \u00B0F"),
    ("Hundredths of Degrees F", "1/100 \u00B0F"),
    ("Degrees K", "K"),
    ("Tenths of Degrees K", "1/10 K"),
    ("Hundredths of Degrees K", "1/100 K"),
    ("Color Temperature", "K"),

    ("Volts", "V"),
    ("MilliVolts", "mV"),
    ("Tenths of MilliVolts", "1/10 mV"),
    ("Amps", "A"),
    ("MilliAmps", "mA"),
    ("Tenths of MilliAmps", "1/10 mA"),
    ("Watts", "W"),
    ("MilliWattHours", "mWh"),

    ("Joules", "J"),
    ("Coulombs", "C"),
    ("Newtons", "N"),

    ("Lumen", "lm"),
    ("Lux", "lx"),
    ("Candelas", "cd"),

    ("Pounds", "lb"),
    ("Pounds per Square Inch", "lb/in\u00B2"),

    ("Cycles", "cycles"),
    ("Revolutions", "rev"),
    ("Revolutions per Minute", "RPM"),
    ("Revolutions per Second", "rev/s"),

    ("Minutes", "min"),
    ("Seconds", "s"),
    ("Tenths of Seconds", "1/10 s"),
    ("Hundredths of Seconds", "1/100 s"),
    ("MicroSeconds", "\u00B5s"),
    ("MilliSeconds", "ms"),
    ("NanoSeconds", "ns"),

    ("Hours", "h"),
    ("Days", "d"),
    ("Weeks", "week"),

    ("Hertz", "Hz"),
    ("MegaHertz", "MHz"),

    ("Pixels", "px"),
    ("Pixels per Inch", "px/in"),

    ("Counts per Inch", "counts/in"),

    ("Percent", "%"),
    ("Tenths of Percent", "1/10 %"),
    ("Hundredths of Percent", "1/100 %"),
    ("Thousandths", "\u2030"),

    ("Meters", "m"),
    ("Centimeters", "cm"),
    ("Millimeters", "mm"),
    ("Cubic Meters", "m\u00B3"),
    ("Cubic Centimeters", "cm\u00B3"),
    ("Cubic Millimeters", "mm\u00B3"),

    ("Inches", "in"),
    ("Feet", "ft"),
    ("Cubic Inches", "in\u00B3"),
    ("Cubic Feet", "ft\u00B3"),
    ("Ounces", "oz"),
    ("Liters", "l"),
    ("Fluid Ounces", "fl.oz"),

    ("Radians", "rad"),
    ("Steradians", "sr"),
    ("Degrees", "\u00B0"),

    ("Gravities", "g"),
    ("Pounds", "lb"),
    ("Foot-Pounds", "ft.lb"),

    ("Gauss", "G"),
    ("Gilberts", "Gb"),
    ("Henrys", "H"),
    ("MilliHenrys", "mH"),
    ("Farads", "F"),
    ("MilliFarads", "mF"),
    ("MicroFarads", "\u00B5F"),
    ("PicoFarads", "pF"),

    ("Ohms", "\u2126"),
    ("Siemens", "S"),

    ("Moles", "mol"),
    ("Becquerels", "Bq"),
    ("Parts per Million", "ppm"),

    ("Decibels", "dB"),
    ("Tenths of Decibels", "1/10 dB"),

    ("Grays", "Gy"),
    ("Sieverts", "Sv"),

    ("MilliWatts", "mW"),

    ("DBm", "dBm"),

    ("Bytes per Second", "B/s"),
    ("KiloBytes per Second", "kB/s"),
    ("MegaBytes per Second", "MB/s"),
    ("GigaBytes per Second", "GB/s"),

    ("BTU per Hour", "BTU/h"),

    ("PCI clock cycles", "PCI clock cycles"),

    ("250 NanoSeconds", "250 ns"),

    ("Us", "U"),

    ("Amps at 120 Volts", "A (@120V)"),

    ("Clock Ticks", "clock ticks"),

    ("Packets", "packets"),
    ("per Thousand Packets", "/1000 packets"),

    # Additional values found in the DMTF CIM Schema (as of its version 2.49)
    # that are not defined as valid values in Annex C.2 of DSP0004 version 2.8
    ("-dBm", "-dBm"),
    ("Blocks", "blocks"),
    ("Percentage", "%"),
    ("Proportion", "proportion"),
    ("Tenths of Revolutions per Minute", "1/10 RPM"),
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
