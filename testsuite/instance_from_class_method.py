"""
    Define instance in class method to be integrated into CIMInstance.
    This temporarily adds the method to the CIMInstance class until we
    agree on PR to incorporate the method into the class
"""
from pywbem import CIMInstance, CIMInstanceName
from pywbem._nocasedict import NocaseDict


@staticmethod
def instance_from_class(klass, namespace=None,
                        property_values=None,
                        include_null_properties=True,
                        include_path=True, strict=False,
                        include_class_origin=False):
    """
    Build a new CIMInstance from the input CIMClass using the
    property_values dictionary to complete properties and the other
    parameters to filter properties, validate the properties, and
    optionally set the path component of the CIMInstance.  If any of the
    properties in the class have default values, those values are passed
    to the instance unless overridden by the property_values dictionary.
    No CIMProperty qualifiers are included in the created instance and the
    `class_origin` attribute is transfered from the class only if the
    `include_class_origin` parameter is True

    Parameters:
      klass (:class:`pywbem:CIMClass`)
        CIMClass from which the instance will be constructed.  This
        class must include qualifiers and should include properties
        from any superclasses to be sure it includes all properties
        that are to be built into the instance. Properties may be
        excluded from the instance by not including them in the `klass`
        parameter.

      namespace (:term:`string`):
        Namespace in the WBEMConnection used to retrieve the class or
        `None` if the default_namespace is to be used.

      property_values (dictionary):
        Dictionary containing name/value pairs where the names are the
        names of properties in the class and the properties are the
        property values to be set into the instance. If a property is in
        the property_values dictionary but not in the class an ValueError
        exception is raised.

      include_null_properties (:class:`py:bool`):
        Determines if properties with Null values are included in the
        instance.

        If `True` they are included in the instance returned.

        If `False` they are not included in the instance returned

     inclued_class_origin  (:class:`py:bool`):
        Determines if ClassOrigin information is included in the returned
        instance.

        If None or False, class origin information is not included.

        If True, class origin information is included.

      include_path (:class:`py:bool`:):
        If `True` the CIMInstanceName path is build and inserted into
        the new instance.  If `strict` all key properties must be in the
        instance.

      strict (:class:`py:bool`:):
        If `True` and `include_path` is set, all key properties must be in
        the instance so that

        If not `True` The path component is created even if not all
        key properties are in the created instance.

    Returns:
        Returns an instance with the defined properties and optionally
        the path set.  No qualifiers are included in the returned instance
        and the existence of ClassOrigin depends on the
        `include_class_origin` parameter. The value of each property is
        either the value from the `property_values` dictionary, the
        default_value from the class or Null(unless
        `include_null_properties` is False). All other attributes of each
        property are the same as the corresponding class property.

    Raises:
       ValueError if there are conflicts between the class and
       property_values dictionary or strict is set and the class is not
       complete.
    """
    class_name = klass.classname
    inst = CIMInstance(class_name)
    for p in property_values:
        if p not in klass.properties:
            raise ValueError('Property Name %s in property_values but '
                             'not in class %s' % (p, class_name))
    for cp in klass.properties:
        ip = klass.properties[cp].copy()
        ip.qualifiers = NocaseDict()
        if not include_class_origin:
            ip.class_origin = None
        if ip.name in property_values:
            ip.value = property_values[ip.name]
        if include_null_properties:
            inst[ip.name] = ip
        else:
            if ip.value:
                inst[ip.name] = ip

    if include_path:
        inst.path = CIMInstanceName.from_instance(klass, inst, namespace,
                                                  strict=strict)
    return inst
