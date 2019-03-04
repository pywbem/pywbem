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
The :class:`~pywbem.ValueMapping` class supports translating between the values
of an integer-typed CIM element (e.g. property, method, or parameter) that is
qualified with the `ValueMap` and `Values` qualifiers, and the corresponding
values of the `Values` qualifier, in both directions.

This class supports value ranges (e.g. ``"4..6"``) and the unclaimed marker
(``".."``).
"""

import re
try:
    from collections import OrderedDict
except ImportError:
    from ordereddict import OrderedDict
import six

from .cim_types import CIMInt, type_from_name
from .cim_obj import CIMProperty, CIMMethod, CIMParameter
from ._utils import _format, _integerValue_to_int

__all__ = ['ValueMapping']


class ValueMapping(object):
    """
    *New in pywbem 0.9 as experimental and finalized in 0.10.*

    A utility class that supports translating between the values of an
    integer-typed CIM element (property, method, parameter) that is qualified
    with the `ValueMap` and `Values` qualifiers, and the corresponding values
    of the `Values` qualifier, in both directions.

    This is done by retrieving the CIM class definition defining the CIM
    element in question, and by inspecting its `ValueMap` and `Values`
    qualifiers.

    The translation is performed by the
    :meth:`~pywbem.ValueMapping.tovalues` and
    :meth:`~pywbem.ValueMapping.tobinary` methods.

    Instances of this class must be created through one of the factory class
    methods: :meth:`~pywbem.ValueMapping.for_property`,
    :meth:`~pywbem.ValueMapping.for_method`, or
    :meth:`~pywbem.ValueMapping.for_parameter`.

    Value ranges (``"2..4"``) and the indicator for unclaimed values (``".."``)
    in the `ValueMap` qualifier are supported.

    All representations of the integer values in the `ValueMap` qualifier are
    supported (decimal, binary, octal, hexadecimal), consistent with the
    definition of the `ValueMap` qualifier in :term:`DSP0004`.

    Example:

      Given the following definition of a property in MOF:

      .. code-block:: text

          class CIM_Foo {

                [ValueMap{ "0", "2..4", "..6", "7..", "9", ".." },
                 Values{ "zero", "two-four", "five-six", "seven-eight", "nine",
                 "unclaimed"}]
             uint16 MyProp;

          };

      Assuming this class exists in a WBEM server, the following code will
      get the class from the server, create a value mapping for this property,
      and look up the `Values` strings that correspond to binary property
      values. This is useful when preparing binary property values for human
      consumption::

          namespace = 'root/cimv2'
          conn = pywbem.WBEMConnection(...)  # WBEM server

          myprop_vm = pywbem.ValueMapping.for_property(
              conn, namespace, 'CIM_Foo', 'MyProp')

          print("Binary value: Values string")
          for bin_value in range(0, 12):
              values_str = myprop_vm.tovalues(bin_value)
              print("{0:12}: {1!r}".format(bin_value, values_str))

      Resulting output:

      .. code-block:: text

          Binary value: Values string
                     0: 'zero'
                     1: 'unclaimed'
                     2: 'two-four'
                     3: 'two-four'
                     4: 'two-four'
                     5: 'five-six'
                     6: 'five-six'
                     7: 'seven-eight'
                     8: 'seven-eight'
                     9: 'nine'
                    10: 'unclaimed'
                    11: 'unclaimed'

      Translating in the other direction is also of interest, for example when
      processing values that are provided by humans in terms of the `Values`
      strings, or when using the pywbem mock support and the test cases specify
      property values for CIM instances in terms of the more human-readable
      `Values` strings.

      Again, assuming the class shown above exists in a WBEM server, the
      following code will get the class from the server, create a value
      mapping for this property, and look up the binary property values from
      the `Values` strings::

          namespace = 'root/cimv2'
          conn = pywbem.WBEMConnection(...)  # WBEM server

          myprop_vm = pywbem.ValueMapping.for_property(
              conn, namespace, 'CIM_Foo', 'MyProp')

          values_strs = ["zero", "two-four", "five-six", "seven-eight", "nine",
                         "unclaimed"]

          print("Values string: Binary value")
          for values_str in values_strs:
              bin_value = myprop_vm.tobinary(values_str)
              print("{0:12}: {1!r}".format(values_str, bin_value))

      Resulting output:

      .. code-block:: text

          Values string: Binary value
                 'zero': 0
             'two-four': (2, 4)
             'five-six': (5, 6)
          'seven-eight': (7, 8)
                 'nine': 9
            'unclaimed': None

      Iterating through the pairs of `ValueMap` and `Values` entries is
      also possible. Assuming the class shown above exists in a WBEM server, the
      following code will get the class from the server, and iterate through the
      value mapping::

          namespace = 'root/cimv2'
          conn = pywbem.WBEMConnection(...)  # WBEM server

          myprop_vm = pywbem.ValueMapping.for_property(
              conn, namespace, 'CIM_Foo', 'MyProp')

          print("Values string: Binary value")
          for bin_value, values_str in myprop_vm.items():
              print("{0:12}: {1!r}".format(values_str, bin_value))

      Resulting output:

      .. code-block:: text

          Values string: Binary value
                 'zero': 0
             'two-four': (2, 4)
             'five-six': (5, 6)
          'seven-eight': (7, 8)
                 'nine': 9
            'unclaimed': None
    """

    def __init__(self):

        self._conn = None
        self._namespace = None
        self._classname = None
        self._propname = None
        self._methodname = None
        self._parametername = None

        self._element_obj = None

        # Attributes for converting binary values to Values strings:
        self._b2v_single_dict = {}  # for single values; bin: values
        self._b2v_range_tuple_list = []  # for value ranges; tuple(lo,hi,values)
        self._b2v_unclaimed = None  # value of the unclaimed indicator '..'

        # Attributes for converting Values strings to binary values:
        self._v2b_dict = {}  # values: bin (int or tuple)

    @classmethod
    def for_property(cls, server, namespace, classname, propname):
        # pylint: disable=line-too-long
        """
        Factory method that returns a new :class:`~pywbem.ValueMapping`
        instance that maps CIM property values to the `Values` qualifier
        defined on that property.

        If a `Values` qualifier is defined but no `ValueMap` qualifier, a
        default of 0-based consecutive numbers is applied (that is the default
        defined in :term:`DSP0004`).

        Parameters:

          server (:class:`~pywbem.WBEMConnection` or :class:`~pywbem.WBEMServer`):
            The connection to the WBEM server containing the namespace.

          namespace (:term:`string`):
            Name of the CIM namespace containing the class.
            If `None`, the default namespace of the connection will be used.

          classname (:term:`string`):
            Name of the CIM class exposing the property. The property can be
            defined in that class or inherited into that class.

          propname (:term:`string`):
            Name of the CIM property that defines the `Values` / `ValueMap`
            qualifiers.

        Returns:

            The new :class:`~pywbem.ValueMapping` instance.

        Raises:

            Exceptions raised by :class:`~pywbem.WBEMConnection`.
            KeyError: The CIM property does not exist in the CIM class.
            TypeError: The CIM property is not integer-typed.
            ValueError: No `Values` qualifier defined on the CIM property.
            ValueError: Invalid integer representation in `ValueMap` qualifier
              defined on the CIM property.
        """  # noqa: E501

        conn = server
        try:
            get_class = conn.GetClass
        except AttributeError:
            conn = server.conn
            get_class = conn.GetClass

        class_obj = get_class(ClassName=classname,
                              namespace=namespace,
                              LocalOnly=False,
                              IncludeQualifiers=True)
        try:
            property_obj = class_obj.properties[propname]
        except KeyError:
            raise KeyError(
                _format("Class {0!A} (in {1!A}) does not have a property "
                        "{2!A}", classname, namespace, propname))

        new_vm = cls._create_for_element(property_obj, conn, namespace,
                                         classname, propname=propname)

        return new_vm

    @classmethod
    def for_method(cls, server, namespace, classname, methodname):
        # pylint: disable=line-too-long
        """
        Factory method that returns a new :class:`~pywbem.ValueMapping`
        instance that maps CIM method return values to the `Values` qualifier
        of that method.

        If a `Values` qualifier is defined but no `ValueMap` qualifier, a
        default of 0-based consecutive numbers is applied (that is the default
        defined in :term:`DSP0004`).

        Parameters:

          server (:class:`~pywbem.WBEMConnection` or :class:`~pywbem.WBEMServer`):
            The connection to the WBEM server containing the namespace.

          namespace (:term:`string`):
            Name of the CIM namespace containing the class.

          classname (:term:`string`):
            Name of the CIM class exposing the method. The method can be
            defined in that class or inherited into that class.

          methodname (:term:`string`):
            Name of the CIM method that defines the `Values` / `ValueMap`
            qualifiers.

        Returns:

            The new :class:`~pywbem.ValueMapping` instance.

        Raises:

            Exceptions raised by :class:`~pywbem.WBEMConnection`.
            KeyError: The CIM method does not exist in the CIM class.
            TypeError: The CIM method is not integer-typed.
            ValueError: No `Values` qualifier defined on the CIM method.
            ValueError: Invalid integer representation in `ValueMap` qualifier
              defined on the CIM method.
        """  # noqa: E501

        conn = server
        try:
            get_class = conn.GetClass
        except AttributeError:
            conn = server.conn
            get_class = conn.GetClass

        class_obj = get_class(ClassName=classname,
                              namespace=namespace,
                              LocalOnly=False,
                              IncludeQualifiers=True)
        try:
            method_obj = class_obj.methods[methodname]
        except KeyError:
            raise KeyError(
                _format("Class {0!A} (in {1!A}) does not have a method {2!A}",
                        classname, namespace, methodname))

        new_vm = cls._create_for_element(method_obj, conn, namespace,
                                         classname, methodname=methodname)

        return new_vm

    @classmethod
    def for_parameter(cls, server, namespace, classname, methodname,
                      parametername):
        # pylint: disable=line-too-long
        """
        Factory method that returns a new :class:`~pywbem.ValueMapping`
        instance that maps CIM parameter values to the `Values` qualifier
        defined on that parameter.

        If a `Values` qualifier is defined but no `ValueMap` qualifier, a
        default of 0-based consecutive numbers is applied (that is the default
        defined in :term:`DSP0004`).

        Parameters:

          server (:class:`~pywbem.WBEMConnection` or :class:`~pywbem.WBEMServer`):
            The connection to the WBEM server containing the namespace.

          namespace (:term:`string`):
            Name of the CIM namespace containing the class.

          classname (:term:`string`):
            Name of the CIM class exposing the method. The method can be
            defined in that class or inherited into that class.

          methodname (:term:`string`):
            Name of the CIM method that has the parameter.

          parametername (:term:`string`):
            Name of the CIM parameter that defines the `Values` / `ValueMap`
            qualifiers.

        Returns:

            The new :class:`~pywbem.ValueMapping` instance.

        Raises:

            Exceptions raised by :class:`~pywbem.WBEMConnection`.
            KeyError: The CIM method does not exist in the CIM class.
            KeyError: The CIM parameter does not exist in the CIM method.
            TypeError: The CIM parameter is not integer-typed.
            ValueError: No `Values` qualifier defined on the CIM parameter.
            ValueError: Invalid integer representation in `ValueMap` qualifier
              defined on the CIM parameter.
        """  # noqa: E501

        conn = server
        try:
            get_class = conn.GetClass
        except AttributeError:
            conn = server.conn
            get_class = conn.GetClass

        class_obj = get_class(ClassName=classname,
                              namespace=namespace,
                              LocalOnly=False,
                              IncludeQualifiers=True)
        try:
            method_obj = class_obj.methods[methodname]
        except KeyError:
            raise KeyError(
                _format("Class {0!A} (in {1!A}) does not have a method {2!A}",
                        classname, namespace, methodname))
        try:
            parameter_obj = method_obj.parameters[parametername]
        except KeyError:
            raise KeyError(
                _format("Method {0!A} in class {1!A} (in {2!A}) does not have "
                        "a parameter {3!A}", methodname, classname, namespace,
                        parametername))

        new_vm = cls._create_for_element(parameter_obj, conn, namespace,
                                         classname, methodname=methodname,
                                         parametername=parametername)

        return new_vm

    def _values_tuple(self, i, valuemap_list, values_list, cimtype):
        """
        Return a tuple for the value range or unclaimed marker at position i,
        with these items:

        * lo - low value of the range
        * hi - high value of the range (can be equal to lo)
        * values - value of `Values` qualifier for this position

        Parameters:

          i (integer): position into valuemap_list and values_list

          valuemap_list (list of strings): `ValueMap` qualifier value

          values_list (list of strings): `Values` qualifier value

          cimtype (type): CIM type of the CIM element

        Raises:

            ValueError: Invalid integer representation in `ValueMap` qualifier
              defined on the CIM element.
        """
        values_str = values_list[i]
        valuemap_str = valuemap_list[i]
        m = re.match(r'^(.*)\.\.(.*)$', valuemap_str)
        if m is None:
            valuemap_int = self._to_int(valuemap_str)
            return (valuemap_int, valuemap_int, values_str)

        # match found
        lo = m.group(1)
        if lo == '':
            if i == 0:
                lo = cimtype.minvalue
            else:
                _, previous_hi, _ = self._values_tuple(
                    i - 1, valuemap_list, values_list, cimtype)
                lo = previous_hi + 1
        else:
            lo = self._to_int(lo)

        hi = m.group(2)
        if hi == '':
            if i == len(valuemap_list) - 1:
                hi = cimtype.maxvalue
            else:
                next_lo, _, _ = self._values_tuple(
                    i + 1, valuemap_list, values_list, cimtype)
                hi = next_lo - 1
        else:
            hi = self._to_int(hi)
        return (lo, hi, values_str)

    def _to_int(self, val_str):
        """Conver val_str to an integer or raise ValueError"""
        val = _integerValue_to_int(val_str)
        if val is None:
            raise ValueError(
                _format("The value-mapped {0} has an invalid integer "
                        "representation in a ValueMap entry: {1!A}",
                        self._element_str(), val_str))
        return val

    @classmethod
    def _create_for_element(cls, element_obj, conn, namespace, classname,
                            propname=None, methodname=None, parametername=None):
        # pylint: disable=line-too-long
        """
        Return a new :class:`~pywbem.ValueMapping` instance for the specified
        CIM element.

        If a `Values` qualifier is defined but no `ValueMap` qualifier, a
        default of 0-based consecutive numbers is applied (that is the default
        defined in :term:`DSP0004`).

        Parameters:

          element_obj (:class:`~pywbem.CIMProperty`, :class:`~pywbem.CIMMethod`, or :class:`~pywbem.CIMParameter`):
            The CIM element on which the qualifiers are defined.

          conn (:class:`~pywbem.WBEMConnection`):
            The connection to the WBEM server containing the namespace.

          namespace (:term:`string`):
            Name of the CIM namespace containing the class.

          classname (:term:`string`):
            Name of the CIM class exposing the method. The method can be
            defined in that class or inherited into that class.

          propname (:term:`string`):
            Name of the CIM property that defines the `Values` / `ValueMap`
            qualifiers.

          methodname (:term:`string`):
            Name of the CIM method that has the parameter.

          parametername (:term:`string`):
            Name of the CIM parameter that defines the `Values` / `ValueMap`
            qualifiers.

        Returns:

            The created :class:`~pywbem.ValueMapping` instance for the specified
            CIM element.

        Raises:

            TypeError: The CIM element is not integer-typed.
            ValueError: No `Values` qualifier defined on the CIM element.
            ValueError: Invalid integer representation in `ValueMap` qualifier
              defined on the CIM element.
        """  # noqa: E501
        # pylint: enable=line-too-long

        # pylint: disable=protected-access

        vm = ValueMapping()
        vm._element_obj = element_obj
        vm._conn = conn
        vm._namespace = namespace
        vm._classname = classname
        vm._propname = propname
        vm._methodname = methodname
        vm._parametername = parametername

        try:
            typename = element_obj.type  # Property, Parameter
        except AttributeError:
            typename = element_obj.return_type  # Method

        cimtype = type_from_name(typename)

        if not issubclass(cimtype, CIMInt):
            raise TypeError(
                _format("The value-mapped {0} is not integer-typed, but "
                        "has CIM type: {1}", vm._element_str(), typename))

        values_qual = element_obj.qualifiers.get('Values', None)
        if values_qual is None:
            # DSP0004 defines no default for a missing Values qualifier
            raise ValueError(
                _format("The value-mapped {0} has no Values qualifier "
                        "defined", vm._element_str()))
        values_list = values_qual.value

        valuemap_qual = element_obj.qualifiers.get('ValueMap', None)
        if valuemap_qual is None:
            # DSP0004 defines a default of consecutive index numbers
            vm._b2v_single_dict = dict(zip(range(0, len(values_list)),
                                           values_list))
            vm._b2v_range_tuple_list = []
            vm._b2v_unclaimed = None
            vm._v2b_dict = OrderedDict(zip(values_list,
                                           range(0, len(values_list))))
        else:
            vm._b2v_single_dict = {}
            vm._b2v_range_tuple_list = []
            vm._b2v_unclaimed = None
            vm._v2b_dict = OrderedDict()
            valuemap_list = valuemap_qual.value
            for i, valuemap_str in enumerate(valuemap_list):
                values_str = values_list[i]
                if valuemap_str == '..':
                    vm._b2v_unclaimed = values_str
                    vm._v2b_dict[values_str] = None
                else:
                    lo, hi, values_str = vm._values_tuple(
                        i, valuemap_list, values_list, cimtype)
                    if lo == hi:
                        # single value
                        vm._b2v_single_dict[lo] = values_str
                        vm._v2b_dict[values_str] = lo
                    else:
                        # value range
                        vm._b2v_range_tuple_list.append((lo, hi, values_str))
                        vm._v2b_dict[values_str] = (lo, hi)

        return vm

    def _element_str(self):
        """
        Return a string that identifies the value-mapped element.
        """
        # pylint: disable=no-else-return
        if isinstance(self.element, CIMProperty):
            return _format("property {0!A} in class {1!A} (in {2!A})",
                           self.propname, self.classname, self.namespace)
        elif isinstance(self.element, CIMMethod):
            return _format("method {0!A} in class {1!A} (in {2!A})",
                           self.methodname, self.classname, self.namespace)
        assert isinstance(self.element, CIMParameter)
        return _format("parameter {0!A} of method {1!A} in class {2!A} "
                       "(in {3!A})",
                       self.parametername, self.methodname, self.classname,
                       self.namespace)

    def __repr__(self):
        """
        Return a representation of the :class:`~pywbem.ValueMapping` object
        with all attributes, that is suitable for debugging.
        """
        return _format(
            "ValueMapping("
            "_conn={s._conn!A}, "
            "_namespace={s._namespace!A}, "
            "_classname={s._classname!A}, "
            "_propname={s._propname!A}, "
            "_methodname={s._methodname!A}, "
            "_parametername={s._parametername!A}, "
            "_element_obj={s._element_obj!A}, "
            "_b2v_single_dict={s._b2v_single_dict!A}, "
            "_b2v_range_tuple_list={s._b2v_range_tuple_list!A}, "
            "_b2v_unclaimed={s._b2v_unclaimed!A}, "
            "_v2b_dict={s._v2b_dict!A})",
            s=self)

    @property
    def conn(self):
        """
        :class:`~pywbem.WBEMConnection`:
        Connection to the WBEM server containing the CIM namespace (that
        contains the mapped CIM element).
        """
        return self._conn

    @property
    def namespace(self):
        """
        :term:`string`: Name of the CIM namespace containing the class that
        defines the mapped CIM element.
        """
        return self._namespace

    @property
    def classname(self):
        """
        :term:`string`: Name of the CIM class defining the mapped CIM element.
        """
        return self._classname

    @property
    def propname(self):
        """
        :term:`string`: Name of the CIM property that is mapped. `None`, if
        no property is mapped.
        """
        return self._propname

    @property
    def methodname(self):
        """
        :term:`string`: Name of the CIM method, that either is mapped itself,
        or that has the parameter that is mapped.  `None`, if no method or
        parameter is mapped.
        """
        return self._methodname

    @property
    def parametername(self):
        """
        :term:`string`: Name of the CIM parameter that is mapped. `None`, if
        no parameter is mapped.
        """
        return self._parametername

    @property
    def element(self):
        # pylint: disable=line-too-long
        """
        :class:`~pywbem.CIMProperty`, :class:`~pywbem.CIMMethod`, or :class:`~pywbem.CIMParameter`:
        The mapped CIM element.
        """  # noqa: E501
        return self._element_obj

    def tovalues(self, element_value):
        """
        Return the `Values` string for an element value, based upon this value
        mapping.

        Parameters:

          element_value (:term:`integer` or :class:`~pywbem.CIMInt`):
            The value of the CIM element (property, method, parameter).

        Returns:

          :term:`string`:
            The `Values` string for the element value.

        Raises:

          ValueError: Element value outside of the set defined by `ValueMap`.
          TypeError: Element value is not an integer type.
        """

        if not isinstance(element_value, (six.integer_types, CIMInt)):
            raise TypeError(
                _format("The value for value-mapped {0} is not "
                        "integer-typed, but has Python type: {1}",
                        self._element_str(), type(element_value)))

        # try single value
        try:
            return self._b2v_single_dict[element_value]
        except KeyError:
            pass

        # try value ranges
        for range_tuple in self._b2v_range_tuple_list:
            lo, hi, values_str = range_tuple
            if lo <= element_value <= hi:
                return values_str

        # try catch-all '..'
        if self._b2v_unclaimed is not None:
            return self._b2v_unclaimed

        raise ValueError(
            _format("The value for value-mapped {0} is outside of the set "
                    "defined by its ValueMap qualifier: {1!A}",
                    self._element_str(), element_value))

    def tobinary(self, values_str):
        """
        Return the integer value or values for a `Values` string, based upon
        this value mapping.

        Any returned integer value is represented as the CIM type of the
        element (e.g. :class:`~pywbem.Uint16`).

        If the `Values` string corresponds to a single value, that single value
        is returned as an integer.

        If the `Values` string corresponds to a value range (e.g. "1.." or
        "..2" or "3..4"), that value range is returned as a tuple with two items
        that are the lowest and the highest value of the range. That is the
        case also when the value range is open on the left side or right side.

        If the `Values` string corresponds to the `unclaimed` indicator "..",
        `None` is returned.

        Parameters:

          values_str (:term:`string`):
            The `Values` string for the element value.

        Returns:

          :class:`~pywbem.CIMInt` or tuple of :class:`~pywbem.CIMInt` or `None`:
            The element value or value range corresponding to the `Values`
            string, or `None` for unclaimed.

        Raises:

          ValueError: `Values` string outside of the set defined by `Values`.
          TypeError: `Values` string is not a string type.
        """

        if not isinstance(values_str, six.string_types):
            raise TypeError(
                _format("The values string for value-mapped {0} is not "
                        "string-typed, but has Python type: {1}",
                        self._element_str(), type(values_str)))

        try:
            return self._v2b_dict[values_str]
        except KeyError:
            raise ValueError(
                _format("The values string for value-mapped {0} is outside "
                        "of the set defined by its Values qualifier: {1!A}",
                        self._element_str(), values_str))

    def items(self):
        """
        Generator that iterates through the items of the value mapping. The
        items are the array entries of the `Values` and `ValueMap` qualifiers,
        and they are iterated in the order specified in the arrays.
        If the `ValueMap` qualifier is not specified, the default of consecutive
        integers starting at 0 is used as a default, consistent with
        :term:`DSP0004`.

        Each iterated item is a tuple of integer value(s) representing the
        `ValueMap` array entry, and the corresponding `Values` string.
        Any integer value in the iterated items is represented as the CIM type
        of the element (e.g. :class:`~pywbem.Uint16`).

        If the `Values` string corresponds to a single element value, the
        first tuple item is that single integer value.

        If the `Values` string corresponds to a value range (e.g. "1.." or
        "..2" or "3..4"), that value range is returned as a tuple with two items
        that are the lowest and the highest value of the range. That is the
        case also when the value range is open on the left side or right side.

        If the `Values` string corresponds to the `unclaimed` indicator "..",
        the first tuple item is `None`.

        Returns:

          :term:`iterator` for tuple of integer value(s) and `Values` string.
        """

        for values_str in self._v2b_dict:
            element_value = self._v2b_dict[values_str]
            yield element_value, values_str
