# -*- coding: utf-8 -*-
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

"""
The :func:`pywbem.siunit_obj` and :func:`pywbem.siunit` functions translate
the ``PUnit`` and ``Units`` qualifier values into human readable SI conformant
unit strings.

**Experimental:** *New in 1.1.0 as experimental*

Note: These functions do not perform any class operations; they take the
qualifiers as input.

The reason the ``Units`` qualifier is still supported is that the DMTF CIM
Schema (as of its version 2.49) still contains a number of schema elements that
have the ``Units`` qualifier but not the ``PUnit`` qualifier set.

The format and valid base units for the ``PUnit`` qualifier and the
valid values for the ``Units`` qualifier are defined in Annex C of
:term:`DSP0004`. Pywbem supports the definitions from :term:`DSP0004`
version 2.8, and the following additional ``Units`` qualifier values that are
used in DMTF CIM Schema version 2.49:

+--------------------------------------+
| Additional ``Units`` values          |
+======================================+
| ``-dBm``                             |
+--------------------------------------+
| ``Blocks``                           |
+--------------------------------------+
| ``Percentage``                       |
+--------------------------------------+
| ``Proportion``                       |
+--------------------------------------+
| ``Tenths of Revolutions per Minute`` |
+--------------------------------------+

By default, the string value returned from these functions may contain the
following Unicode characters outside of the 7-bit ASCII range. If the
``use_ascii`` parameter is `True`, these Unicode characters are replaced with
7-bit ASCII text as follows:

+---------------------------+---------+---------------+
| Unicode character code    | Unicode | 7-bit ASCII   |
+===========================+=========+===============+
| U+00B0: DEGREE SIGN       | ``°``   | ``deg``       |
+---------------------------+---------+---------------+
| U+00B5: MICRO SIGN        | ``µ``   | ``u``         |
+---------------------------+---------+---------------+
| U+2030: PER MILLE SIGN    | ``‰``   | ``1/1000``    |
+---------------------------+---------+---------------+
| U+2126: OHM SIGN          | ``Ω``   | ``Ohm``       |
+---------------------------+---------+---------------+
| U+00B2: SUPERSCRIPT TWO   | ``²``   | ``^2``        |
+---------------------------+---------+---------------+
| U+00B3: SUPERSCRIPT THREE | ``³``   | ``^3``        |
+---------------------------+---------+---------------+

Examples:

* ``PUnit("byte / second * 10^3")``-> ``kB/s``
* ``PUnit("byte * 2^10")``-> ``KiB``
* ``PUnit("hertz * 10^6")``-> ``MHz``
* ``PUnit("ampere * 10^-3")`` -> ``mA``
* ``Units("KiloBits per Second")`` -> ``kbit/s``
* ``Units("Tenths of Degrees C")`` -> ``1/10 °C``

Limitations:

* For PUnit qualifiers, vendor-defined base units are not supported
  (e.g. ``vendor:myunit``).

* For PUnit qualifiers, space characters within the parenthesis of
  ``decibel`` (e.g. ``decibel ( A )``) are not supported.

* For Units qualifiers, arbitrary numeric values that are part of the Units
  value (e.g. ``<numeric-value> NanoSeconds`` or
  ``Amps at <numeric-value> Volts``) are not generally supported, but
  only for those cases that are used in the DMTF CIM Schema (as of its version
  2.49):

  - ``250 NanoSeconds``
  - ``Amps at 120 Volts``
"""

import re
try:
    from collections.abc import Sequence
except ImportError:
    from collections import Sequence
from nocasedict import NocaseDict
import six

from ._cim_obj import CIMProperty, CIMMethod, CIMParameter
from ._utils import _ensure_unicode

__all__ = ['siunit_obj', 'siunit']


def siunit_obj(cim_obj, use_ascii=False):
    # pylint: disable=line-too-long
    """
    Returns a human readable SI conformant unit string from the
    ``PUnit`` or ``Units`` qualifiers of the specified CIM object.

    **Experimental:** *New in 1.1.0 as experimental*

    If the CIM object has both the ``PUnit`` and ``Units`` qualifiers set, then
    ``PUnit`` is used and ``Units`` is ignored.

    Parameters:

      cim_obj (:class:`~pywbem.CIMProperty` or :class:`~pywbem.CIMMethod` or :class:`~pywbem.CIMParameter`):
        CIM object with qualifiers.

      use_ascii (:class:`py:bool`): Replace any Unicode characters in the
        returned string with 7-bit ASCII replacements,
        as described :mod:`above <pywbem._units>`.

    Returns:

      :term:`unicode string`: Human readable SI conformant unit string,
      or `None` if the CIM object has neither the ``PUnit`` nor the ``Units``
      qualifiers set.

    Raises:

      TypeError: Invalid type for cim_obj
      ValueError: Invalid format in PUnit qualifier
      ValueError: Unknown base unit in PUnit qualifier
      ValueError: Unknown unit in Units qualifier
    """  # noqa: E501
    # pylint: enable=line-too-long

    if not isinstance(cim_obj, (CIMProperty, CIMMethod, CIMParameter)):
        raise TypeError("Invalid type for cim_obj: {}, "
                        "must be CIMProperty, CIMMethod, or CIMParameter".
                        format(type(cim_obj)))

    punit_q = cim_obj.qualifiers.get('PUnit', None)
    punit = punit_q.value if punit_q else None

    units_q = cim_obj.qualifiers.get('Units', None)
    units = units_q.value if units_q else None

    return siunit(punit, units, use_ascii)


def siunit(punit=None, units=None, use_ascii=False):
    """
    Returns a human readable SI conformant unit string from the specified
    ``PUnit`` or ``Units`` qualifier values.

    **Experimental:** *New in 1.1.0 as experimental*

    If both ``punit`` and ``units`` are specified, then ``punit`` is used and
    ``units`` is ignored.

    Parameters:

      punit (:term:`string`):
        Value of the ``PUnit`` qualifier, or `None`.

      units (:term:`string`):
        Value of the ``Units`` qualifier, or `None`.

      use_ascii (:class:`py:bool`): Replace any Unicode characters in the
        returned string with 7-bit ASCII replacements,
        as described :mod:`above <pywbem._units>`.

    Returns:

      :term:`unicode string`: Human readable SI conformant unit string,
      or `None` if both qualifier value input parameters were `None`.

    Raises:

      TypeError: Invalid type for punit or unit
      ValueError: Invalid format in PUnit qualifier
      ValueError: Unknown base unit in PUnit qualifier
      ValueError: Unknown unit in Units qualifier
    """

    if punit is not None:
        punit = _ensure_unicode(punit)
        ret = _siunit_from_punit(punit)
    elif units is not None:
        units = _ensure_unicode(units)
        ret = _siunit_from_units(units)
    else:
        return None
    if use_ascii:
        ret = _uc2ascii(ret)
    return ret


# Unicode characters used in the output, by default
UC_DEGREE = u'\u00B0'  # U+00B0: DEGREE SIGN
# U+2103 (DEGREE CELSIUS) and U+2109 (DEGREE FAHRENHEIT) are intentionally
# not used, for better font/terminal compatibility.
UC_DEGREE_CELSIUS = u'{}C'.format(UC_DEGREE)  # Avoid U+2103: DEGREE CELSIUS
UC_DEGREE_FAHRENHEIT = u'{}F'.format(UC_DEGREE)  # Avoid U+2109: DEGREE FAHR.
UC_PERMILLE = u'\u2030'  # U+2030: PER MILLE SIGN
UC_MICRO = u'\u00B5'  # U+00B5: MICRO SIGN
UC_OHM = u'\u2126'  # U+2126: OHM SIGN
UC_SUP_2 = u'\u00B2'  # U+00B2: SUPERSCRIPT TWO
UC_SUP_3 = u'\u00B3'  # U+00B3: SUPERSCRIPT THREE
# U+2074 (SUPERSCRIPT FOUR) and adjacent characters up to U+2079
# (SUPERSCRIPT NINE) are intentionally not used, for better font/terminal
# compatibility.

# 7-bit ASCII replacements for the Unicode characters above
UC2ASCII = {
    UC_DEGREE: u'deg',
    UC_DEGREE_CELSIUS: u'degC',
    UC_DEGREE_FAHRENHEIT: u'degF',
    UC_PERMILLE: u'1/1000',
    UC_MICRO: u'u',
    UC_OHM: u'Ohm',
    UC_SUP_2: u'^2',
    UC_SUP_3: u'^3',
}

# Components in the PUnit regexp pattern, named consistent with ABNF in
# Annex C.1 of DSP0004
SIMPLE_NAME = r'[A-Za-z_][A-Za-z_\-0-9 ]*?'
WS = r'[ \t\n]?'  # optionality already included
SP = r'[ ]?'  # optionality already included
POSITIVE_WHOLE_NUMBER = r'[1-9][0-9]*'
POSITIVE_NUMBER = r'(?:{pwn}|(?:{pwn}|0)\.[0-9]*)'. \
    format(pwn=POSITIVE_WHOLE_NUMBER)
NUMBER = r'[\+\-]?{pn}'.format(pn=POSITIVE_NUMBER)
EXPONENT = r'[\+\-]?{pwn}'.format(pwn=POSITIVE_WHOLE_NUMBER)
DECIBEL_BASE_UNIT = r'decibel{sp}\({sn}\)'.format(sp=SP, sn=SIMPLE_NAME)

# The pattern for programmatic-unit.
# Because re returns only the last match of a group repetition, we need to
# parse the multiplied-base-unit and divided-base-unit components first as
# a whole, and then process them afterwards.
PUNIT = r'^({sn}|{dbu})' \
    r'((?:{ws}\*{ws}(?:{sn}|{dbu}))*)' \
    r'((?:{ws}/{ws}(?:{sn}|{dbu}))*)' \
    r'(?:{ws}(\*|/){ws}({n}))?' \
    r'(?:{ws}(\*|/){ws}({pwn}){ws}\^{ws}({e}))?$'. \
    format(sn=SIMPLE_NAME, dbu=DECIBEL_BASE_UNIT, ws=WS,
           pwn=POSITIVE_WHOLE_NUMBER, n=NUMBER, e=EXPONENT)
PUNIT_PATTERN = re.compile(PUNIT)

# The abbreviated SI units for each PUnit base unit defined in DSP0004
PUNIT_SIUNIT = NocaseDict([
    ("percent", "%"),
    ("permille", UC_PERMILLE),
    ("decibel", "dB"),
    ("count", ""),
    ("revolution", "rev"),
    ("degree", UC_DEGREE),
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
    ("degree celsius", UC_DEGREE_CELSIUS),
    ("degree fahrenheit", UC_DEGREE_FAHRENHEIT),
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
    ("ohm", UC_OHM),
    ("siemens", "S"),
    ("weber", "Wb"),
    ("tesla", "T"),
    ("henry", "H"),
    ("becquerel", "Bq"),
    ("gray", "Gy"),
    ("sievert", "Sv"),
])

# The abbreviated SI prefixes for modifier1 in a PUnit.
# This dictionary covers only the typical values, assuming that for larger
# values, the modifier2 syntax is used.
# For modifier1 and modifier2, see the ABNF in Annex C.1 of DSP0004.
PUNIT_MOD1_SIPREFIX = {
    # mod1_num: si-prefix
    "1024": "Ki",
    "1000": "k",
    "100": "h",
    "10": "da",
    "1": "",
    "1/1": "",
    "1/10": "d",
    "1/100": "c",
    "1/1000": "m",
}

# The abbreviated SI prefixes for modifier2 in a PUnit.
# This dictionary covers all defined SI decimal prefixes and IEC binary
# prefixes.
# For modifier2, see the ABNF in Annex C.1 of DSP0004.
PUNIT_MOD2_SIPREFIX = {
    # (mod2_base, mod2_exp): si-prefix
    (2, 80): "Yi",
    (2, 70): "Zi",
    (2, 60): "Ei",
    (2, 50): "Pi",
    (2, 40): "Ti",
    (2, 30): "Gi",
    (2, 20): "Mi",
    (2, 10): "Ki",
    (10, 24): "Y",
    (10, 21): "Z",
    (10, 18): "E",
    (10, 15): "P",
    (10, 12): "T",
    (10, 9): "G",
    (10, 6): "M",
    (10, 3): "k",
    (10, 2): "h",
    (10, 1): "da",
    (10, -1): "d",
    (10, -2): "c",
    (10, -3): "m",
    (10, -6): "u",
    (10, -9): "n",
    (10, -12): "p",
    (10, -15): "f",
    (10, -18): "a",
    (10, -21): "z",
    (10, -24): "y",
}

# Dictionary to map unit power integer numbers to a suitable superscript
# Unicode character.
PUNIT_POWER = {
    1: u'',
    2: UC_SUP_2,
    3: UC_SUP_3,
}

# The abbreviated SI units for each Units unit defined in Annex C.2 of DSP0004.
UNITS_SIUNIT = NocaseDict([

    ("Bits", "bit"),
    ("KiloBits", "kbit"),
    ("MegaBits", "Mbit"),
    ("GigaBits", "Gbit"),

    ("Bits per Second", "bit/s"),
    ("KiloBits per Second", "kbit/s"),
    ("MegaBits per Second", "Mbit/s"),
    ("GigaBits per Second", "Gbit/s"),

    ("Bytes", "B"),
    ("KiloBytes", "kB"),  # Decimal prefix, according to SI
    ("MegaBytes", "MB"),  # Decimal prefix, according to SI
    ("GigaBytes", "GB"),  # Decimal prefix, according to SI
    ("Words", "words"),
    ("DoubleWords", "doublewords"),
    ("QuadWords", "quadwords"),

    ("Degrees C", UC_DEGREE_CELSIUS),
    ("Tenths of Degrees C", "1/10 " + UC_DEGREE_CELSIUS),
    ("Hundredths of Degrees C", "1/100 " + UC_DEGREE_CELSIUS),
    ("Degrees F", UC_DEGREE_FAHRENHEIT),
    ("Tenths of Degrees F", "1/10 " + UC_DEGREE_FAHRENHEIT),
    ("Hundredths of Degrees F", "1/100 " + UC_DEGREE_FAHRENHEIT),
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
    ("Pounds per Square Inch", "lb/in" + PUNIT_POWER[2]),

    ("Cycles", "cycles"),
    ("Revolutions", "rev"),
    ("Revolutions per Minute", "RPM"),
    ("Revolutions per Second", "rev/s"),

    ("Minutes", "min"),
    ("Seconds", "s"),
    ("Tenths of Seconds", "1/10 s"),
    ("Hundredths of Seconds", "1/100 s"),
    ("MicroSeconds", UC_MICRO + "s"),
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
    ("Thousandths", UC_PERMILLE),

    ("Meters", "m"),
    ("Centimeters", "cm"),
    ("Millimeters", "mm"),
    ("Cubic Meters", "m" + PUNIT_POWER[3]),
    ("Cubic Centimeters", "cm" + PUNIT_POWER[3]),
    ("Cubic Millimeters", "mm" + PUNIT_POWER[3]),

    ("Inches", "in"),
    ("Feet", "ft"),
    ("Cubic Inches", "in" + PUNIT_POWER[3]),
    ("Cubic Feet", "ft" + PUNIT_POWER[3]),
    ("Ounces", "oz"),
    ("Liters", "l"),
    ("Fluid Ounces", "fl.oz"),

    ("Radians", "rad"),
    ("Steradians", "sr"),
    ("Degrees", UC_DEGREE),

    ("Gravities", "g"),
    ("Pounds", "lb"),
    ("Foot-Pounds", "ft.lb"),

    ("Gauss", "G"),
    ("Gilberts", "Gb"),
    ("Henrys", "H"),
    ("MilliHenrys", "mH"),
    ("Farads", "F"),
    ("MilliFarads", "mF"),
    ("MicroFarads", UC_MICRO + "F"),
    ("PicoFarads", "pF"),

    ("Ohms", UC_OHM),
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
    ("KiloBytes per Second", "kB/s"),  # Decimal prefix, according to SI
    ("MegaBytes per Second", "MB/s"),  # Decimal prefix, according to SI
    ("GigaBytes per Second", "GB/s"),  # Decimal prefix, according to SI

    ("BTU per Hour", "BTU/h"),

    ("PCI clock cycles", "PCI clock cycles"),

    # The generic form of this unit (with arbitrary numeric value) is not
    # supported. The only usages in the DMTF CIM Schema (as of its version 2.49)
    # are the following:
    ("250 NanoSeconds", "250 ns"),

    ("Us", "U"),

    # The generic form of this unit (with arbitrary numeric value) is not
    # supported. The only usages in the DMTF CIM Schema (as of its version 2.49)
    # are the following:
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
])


def _siunit_from_punit(punit):
    """
    Returns a human readable SI conformant unit string from the specified
    ``PUnit`` qualifier values.

    If the ``PUnit`` qualifier value does not conform to the syntax defined
    in DSP0004, ValueError is raised.

    Parameters:

      punit (:term:`string`): Value of ``PUnit`` qualifier. Must not be `None`.

    Returns:

      :term:`string`: Human readable SI conformant unit string.

    Raises:

      TypeError: Invalid type for punit
      ValueError: Unknown base unit in PUnit qualifier value
    """

    if not isinstance(punit, six.string_types):
        raise TypeError("Invalid type for punit: {}, must be string".
                        format(type(punit)))

    if punit == '':
        return ''

    # Parse the PUnit value
    m = PUNIT_PATTERN.match(punit)
    if m is None:
        raise ValueError(
            "Invalid format in PUnit qualifier: {!r}".format(punit))
    base_unit = m.group(1)
    mul_units_str = m.group(2)  # all multiplied-base-unit repetitions
    div_units_str = m.group(3)  # all divided-base-unit repetitions
    mod1_op = m.group(4)
    mod1_num = m.group(5)
    mod2_op = m.group(6)
    mod2_base = m.group(7)
    mod2_exp = m.group(8)

    # Process the units into mul_units and div_units
    _mul_units_str = base_unit
    if mul_units_str:
        _mul_units_str += mul_units_str
    mul_units = [s.strip() for s in _mul_units_str.split('*')]
    if div_units_str:
        div_units = [s.strip() for s in div_units_str.split('/')][1:]
    else:
        div_units = []

    if mod1_op:
        mod1_num = int(mod1_num)
    if mod2_op:
        mod2_base = int(mod2_base)
        mod2_exp = int(mod2_exp)

    # Translate the punits into SI units, combining repetitions into powers
    mul_siunit_str = _siunit_from_punit_base_units(mul_units)
    div_siunit_str = _siunit_from_punit_base_units(div_units)
    siunit_str = mul_siunit_str
    if div_siunit_str:
        siunit_str += '/' + div_siunit_str

    # Prefix for modifier2 (has precedence over modifier1)
    if mod2_op == '*':
        try:
            mod2_prefix = PUNIT_MOD2_SIPREFIX[(mod2_base, mod2_exp)]
        except KeyError:
            mod2_prefix = "{}^{} ".format(mod2_base, mod2_exp)
    elif mod2_op == '/':
        try:
            mod2_prefix = PUNIT_MOD2_SIPREFIX[(mod2_base, -mod2_exp)]
        except KeyError:
            mod2_prefix = "{}^{} ".format(mod2_base, -mod2_exp)
    else:
        mod2_prefix = ""

    # Prefix for modifier1
    if mod1_op == '*':
        mod1_str = "{}".format(mod1_num)
        if mod2_prefix:
            mod1_prefix = "{} ".format(mod1_str)
        else:
            try:
                mod1_prefix = PUNIT_MOD1_SIPREFIX[mod1_str]
            except KeyError:
                mod1_prefix = "{} ".format(mod1_str)
    elif mod1_op == '/':
        mod1_str = "1/{}".format(mod1_num)
        if mod2_prefix:
            mod1_prefix = "{} ".format(mod1_str)
        else:
            try:
                mod1_prefix = PUNIT_MOD1_SIPREFIX[mod1_str]
            except KeyError:
                mod1_prefix = "{} ".format(mod1_str)
    else:
        mod1_prefix = ""

    siunit_str = mod1_prefix + mod2_prefix + siunit_str

    return siunit_str


def _uc2ascii(uc_str):
    """
    Return the input string, where Unicode characters are replaced with their
    7-bit ASCII replacements as defined in UC2ASCII.
    """
    for uc in UC2ASCII:
        ac = UC2ASCII[uc]
        uc_str = uc_str.replace(uc, ac)
    return uc_str


def _siunit_from_punit_base_units(punit_base_units):
    """
    Return the (multiplied or divided) punit base units as an SI unit string.
    """
    assert isinstance(punit_base_units, Sequence)
    siunit_str = ''
    last_punit = None
    unit_power = 1
    for punit in punit_base_units:
        if punit == last_punit:
            unit_power += 1
        elif last_punit is not None:
            siunit_str += _get_punit_siunit(last_punit) + \
                _get_punit_power(unit_power)
            last_punit = None
            unit_power = 1
        last_punit = punit
    if last_punit is not None:
        siunit_str += _get_punit_siunit(last_punit) + \
            _get_punit_power(unit_power)
    return siunit_str


def _get_punit_siunit(punit):
    """
    Return the punit as an SI unit string, raising ValueError if it is unknown.
    """
    try:
        _siunit = PUNIT_SIUNIT[punit]
    except KeyError:
        new_exc = ValueError(
            "Unknown base unit in PUnit qualifier value: {}".format(punit))
        new_exc.__cause__ = None
        raise new_exc
    return _siunit


def _get_punit_power(power):
    """
    Return the power integer as a string.
    """
    assert isinstance(power, six.integer_types)
    try:
        _power = PUNIT_POWER[power]
    except KeyError:
        _power = "^{}".format(power)
    return _power


def _siunit_from_units(units):
    """
    Returns a human readable SI conformant unit string from the specified
    ``Units`` qualifier values.

    If the ``Units`` qualifier value is not one of the known units, ValueError
    is raised.

    Parameters:

      units (:term:`string`): Value of ``Units`` qualifier. Must not be `None`.

    Returns:

      :term:`string`: Human readable SI conformant unit string.

    Raises:

      TypeError: Invalid type for units
      ValueError: Unknown unit in Units qualifier
    """

    if not isinstance(units, six.string_types):
        raise TypeError("Invalid type for units: {}, must be string".
                        format(type(units)))

    try:
        return UNITS_SIUNIT[units]
    except KeyError:
        new_exc = ValueError(
            "Unknown unit in Units qualifier: {!r}".format(units))
        new_exc.__cause__ = None
        raise new_exc
