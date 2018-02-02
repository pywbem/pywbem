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
The :class:`~pywbem.ValueMapping` supports translating the values of an
integer-typed CIM element (e.g. property, method, or parameter) that is
qualified with the `ValueMap` and `Values` qualifiers, to the corresponding
value of the `Values` qualifier.

It supports value ranges (e.g. ``"4..6"``) and the unclaimed marker (``".."``).
"""

import re
import six

from .cim_types import CIMInt, type_from_name

__all__ = ['ValueMapping']


class ValueMapping(object):
    """
    *New in pywbem 0.9 as experimental and finalized in 0.10.*

    A utility class that supports translating the values of an integer-typed
    CIM element (property, method, parameter) that is qualified with the
    `ValueMap` and `Values` qualifiers, to the corresponding value of the
    `Values` qualifier.

    This is done by retrieving the CIM class definition defining the CIM
    element in question, and by inspecting its `ValueMap` and `Values`
    qualifiers.

    The translation of the values is performed by the
    :meth:`~pywbem.ValueMapping.tovalues` method.

    Instances of this class must be created through one of the factory class
    methods: :meth:`~pywbem.ValueMapping.for_property`,
    :meth:`~pywbem.ValueMapping.for_method`, or
    :meth:`~pywbem.ValueMapping.for_parameter`.

    Value ranges (``"2..4"``) and the indicator for unclaimed values (``".."``)
    in the `ValueMap` qualifier are supported.

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
      create a value mapping for this property and will print a few property
      values and their corresponding `Values` strings::

          namespace = 'root/cimv2'
          conn = pywbem.WBEMConnection(...)  # WBEM server

          myprop_vm = pywbem.ValueMapping.for_property(
              conn, namespace, 'CIM_Foo', 'MyProp')

          print("value: Values")
          for value in range(0, 12):
              print("%5s: %r" % (value, myprop_vm.tovalues(value))

      Resulting output:

      .. code-block:: text

          value: Values
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
    """

    def __init__(self):

        self._conn = None
        self._namespace = None
        self._classname = None
        self._propname = None
        self._methodname = None
        self._parametername = None

        self._element_obj = None

        self._single_dict = {}  # for single values; elem_val: values_str)
        self._range_tuple_list = []  # for value ranges; tuple(lo,hi,values_str)
        self._unclaimed = None  # value of the unclaimed indicator '..'

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
            Name of the CIM property that defines the Values / ValueMap
            qualifiers.

        Returns:

            The new :class:`~pywbem.ValueMapping` instance.

        Raises:

            Exceptions raised by :class:`~pywbem.WBEMConnection`.
            ValueError: No `Values` qualifier defined.
            TypeError: The property is not integer-typed.
            KeyError: The property does not exist in the class.
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
        property_obj = class_obj.properties[propname]

        new_vm = cls._create_for_element(property_obj)
        new_vm._conn = conn
        new_vm._namespace = namespace
        new_vm._classname = classname
        new_vm._propname = propname

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
            Name of the CIM method that defines the Values / ValueMap
            qualifiers.

        Returns:

            The new :class:`~pywbem.ValueMapping` instance.

        Raises:

            Exceptions raised by :class:`~pywbem.WBEMConnection`.
            ValueError: No `Values` qualifier defined.
            TypeError: The method is not integer-typed.
            KeyError: The method does not exist in the class.
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
        method_obj = class_obj.methods[methodname]

        new_vm = cls._create_for_element(method_obj)
        new_vm._conn = conn
        new_vm._namespace = namespace
        new_vm._classname = classname
        new_vm._methodname = methodname

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
            Name of the CIM parameter that defines the Values / ValueMap
            qualifiers.

        Returns:

            The new :class:`~pywbem.ValueMapping` instance.

        Raises:

            Exceptions raised by :class:`~pywbem.WBEMConnection`.
            ValueError: No `Values` qualifier defined.
            TypeError: The parameter is not integer-typed.
            KeyError: The method does not exist in the class, or the
              parameter does not exist in the method.
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
        method_obj = class_obj.methods[methodname]
        parameter_obj = method_obj.parameters[parametername]

        new_vm = cls._create_for_element(parameter_obj)
        new_vm._conn = conn
        new_vm._namespace = namespace
        new_vm._classname = classname
        new_vm._methodname = methodname
        new_vm._parametername = parametername

        return new_vm

    @classmethod
    def _values_tuple(cls, i, valuemap_list, values_list, cimtype):
        """
        Return a tuple for the value range at position i, with these items:

        * lo - low value of the range
        * hi - high value of the range (can be equal to lo)
        * values - Value of Values qualifier for this position

        Parameters:

          i (integer): position into valuemap_list and values_list

          valuemap_list (list of strings): ValueMap qualifier value

          values_list (list of strings): Values qualifier value

          cimtype (type): CIM type of the CIM element

        Raises:

            ValueError: Invalid ValueMap entry.
        """
        values_str = values_list[i]
        valuemap_str = valuemap_list[i]
        try:
            valuemap_int = int(valuemap_str)
            return (valuemap_int, valuemap_int, values_str)
        except ValueError:
            m = re.match(r'^([+-]?[0-9]*)\.\.([+-]?[0-9]*)$', valuemap_str)
            if m is None:
                raise ValueError("Invalid ValueMap entry: %r" % valuemap_str)
            lo = m.group(1)
            if lo == '':
                if i == 0:
                    lo = cimtype.minvalue
                else:
                    _, previous_hi, _ = cls._values_tuple(
                        i - 1, valuemap_list, values_list, cimtype)
                    lo = previous_hi + 1
            else:
                lo = int(lo)
            hi = m.group(2)
            if hi == '':
                if i == len(valuemap_list) - 1:
                    hi = cimtype.maxvalue
                else:
                    next_lo, _, _ = cls._values_tuple(
                        i + 1, valuemap_list, values_list, cimtype)
                    hi = next_lo - 1
            else:
                hi = int(hi)
            return (lo, hi, values_str)

    @classmethod
    def _create_for_element(cls, element_obj):
        # pylint: disable=line-too-long
        """
        Return a new :class:`~pywbem.ValueMapping` instance for the specified
        CIM element.

        If a Values qualifier is defined but no ValueMap qualifier, a default
        of 0-based consecutive numbers is applied (that is the default defined
        in :term:`DSP0004`).

        Parameters:

          element_obj (:class:`~pywbem.CIMProperty`, :class:`~pywbem.CIMMethod`, or :class:`~pywbem.CIMParameter`):
            The CIM element on which the qualifiers are defined.

        Returns:

            The created :class:`~pywbem.ValueMapping` instance for the specified
            CIM element.

        Raises:

            ValueError: No Values qualifier defined.
            ValueError: Invalid ValueMap entry.
            TypeError: The CIM element is not integer-typed.
        """  # noqa: E501

        # pylint: disable=protected-access

        try:
            typename = element_obj.type  # Property, Parameter
        except AttributeError:
            typename = element_obj.return_type  # Method

        cimtype = type_from_name(typename)

        if not issubclass(cimtype, CIMInt):
            raise TypeError("The CIM element is not integer-typed: %s" %
                            typename)

        vm = ValueMapping()
        vm._element_obj = element_obj

        values_qual = element_obj.qualifiers.get('Values', None)
        if values_qual is None:
            # DSP0004 defines no default for a missing Values qualifier
            raise ValueError("No Values qualifier defined")
        values_list = values_qual.value

        valuemap_qual = element_obj.qualifiers.get('ValueMap', None)
        if valuemap_qual is None:
            # DSP0004 defines a default of consecutive index numbers
            vm._single_dict = dict(zip(range(0, len(values_list)), values_list))
            vm._range_tuple_list = []
            vm._unclaimed = None
        else:
            vm._single_dict = {}
            vm._range_tuple_list = []
            vm._unclaimed = None
            valuemap_list = valuemap_qual.value
            for i, valuemap_str in enumerate(valuemap_list):
                values_str = values_list[i]
                if valuemap_str == '..':
                    vm._unclaimed = values_str
                else:
                    lo, hi, values_str = cls._values_tuple(
                        i, valuemap_list, values_list, cimtype)
                    if lo == hi:
                        # single value
                        vm._single_dict[lo] = values_str
                    else:
                        # value range
                        vm._range_tuple_list.append((lo, hi, values_str))

        return vm

    def __repr__(self):
        """
        Return a representation of the :class:`~pywbem.ValueMapping` object
        with all attributes, that is suitable for debugging.
        """
        return "%s(_conn=%r, _namespace=%r, " \
               "_classname=%r, _propname=%r, _methodname=%r, " \
               "_parametername=%r, _element_obj=%r, " \
               "_single_dict=%r, _range_tuple_list=%r, _unclaimed=%r)" % \
               (self.__class__.__name__, self._conn, self._namespace,
                self._classname, self._propname, self._methodname,
                self._parametername, self._element_obj,
                self._single_dict, self._range_tuple_list, self._unclaimed)

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
            The Values string for the element value.

        Raises:

          ValueError: Element value outside of the set defined by ValueMap.
          TypeError: Element value is not an integer type.
        """

        if not isinstance(element_value, (six.integer_types, CIMInt)):
            raise TypeError("Element value is not an integer type: %s" %
                            type(element_value))

        # try single value
        try:
            return self._single_dict[element_value]
        except KeyError:
            pass

        # try value ranges
        for range_tuple in self._range_tuple_list:
            lo, hi, values_str = range_tuple
            if lo <= element_value <= hi:
                return values_str

        # try catch-all '..'
        if self._unclaimed is not None:
            return self._unclaimed

        raise ValueError("Element value outside of the set defined by "
                         "ValueMap: %r" % element_value)
