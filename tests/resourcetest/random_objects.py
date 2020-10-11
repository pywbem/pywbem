"""
Utility functions for creating random CIM objects.
"""

from collections import namedtuple
import string
import random
from datetime import datetime
import six

from pywbem import CIMQualifier, CIMProperty, CIMClass, CIMInstance, \
    CIMInstanceName, CIMDateTime
from pywbem_mock import FakedWBEMConnection


ASCII_CHARS = [six.unichr(i) for i in range(0x0020, 0x007e + 1)]

#: The CIM integer type names
INTEGER_TYPES = (
    'uint8', 'uint16', 'uint32', 'uint64',
    'sint8', 'sint16', 'sint32', 'sint64',
)

#: The CIM floating point type names
REAL_TYPES = ('real32', 'real64')


#: Range of integer values, for various purposes
#: Attributes:
#: - min (int): Minimum value (inclusive)
#: - min (int): Maximum value (inclusive)
Range = namedtuple(
    'Range',
    ['min', 'max']
)

#: Profile for generating typed CIM values
#: Attributes:
#: - types (tuple of string): CIM type names
#: - string_len (Range): Lengths of string values
ValueProfile = namedtuple(
    'ValueProfile',
    ['types', 'string_len']
)

#: A meaningful set of CIM qualifier values
#: Attributes:
#: - names (tuple of string): Names of the qualifiers in the set
#: - types (tuple of string: CIM type names for the rs in the set
#: - values (ValueProfile or value): Qualifier values
QualifierSet = namedtuple(
    'QualifierSet',
    ['names', 'types', 'values']
)

#: Profile for picking a random set of CIM qualifier values
#: Attributes:
#: - qualifier_sets (tuple of QualifierSet): Qualifier sets to pick from
QualifierSetProfile = namedtuple(
    'QualifierSetProfile',
    ['qualifier_sets']
)

#: Profile for generating multiple CIM properties for use in CIM classes
#: Attributes:
#: - name_len (Range): Lengths of property names
#: - value_profile (ValueProfile): Property value profile
#: - value_ratio (float): Ratio of properties that have a value
#: - description_len (Range): Lengths of property Description qualifier;
#:   None for no Description qualifier
#: - qualifier_set_profile (QualifierSetProfile): Qualifier set profile;
#:   None for no additional qualifiers
PropertyProfile = namedtuple(
    'PropertyProfile',
    ['name_len', 'value_profile', 'value_ratio', 'description_len',
     'qualifier_set_profile']
)


def random_name(length_range):
    """
    Return a random valid CIM name of a length that is randomly in a length
    range.

    Parameters:
      length_range (Range): Length range.
    """
    first_chars = string.ascii_uppercase
    other_chars = string.ascii_uppercase + string.ascii_lowercase + \
        string.digits
    length = random.randint(length_range.min, length_range.max)
    name = random.choice(first_chars) + ''.join(
        random.choice(other_chars) for _ in range(length))
    return name


def random_string(length_range, charset='ascii'):
    """
    Return a random Unicode string value of a length that is randomly in a
    length range, and the string characters are in a character set.

    Parameters:
      length_range (Range): Length range.
      charset (string): CHaracter set for the values. Valid character sets
        are:
        - 'ascii' - Printable 7-bit ASCII characters (U+0020 .. U+007E)
    """
    if charset == 'ascii':
        chars = ASCII_CHARS
    else:
        raise ValueError("Invalid charset: {}".format(charset))
    length = random.randint(length_range.min, length_range.max)
    value = ''.join(random.choice(chars) for _ in range(length))
    return value


def random_type_value(values, type=None):
    # pylint: disable=redefined-builtin
    """
    Return a random valid tuple of CIM type name and value according to
    a value profile.

    Parameters:
      values (ValueProfile or value): Values
      type (string): Use this type instead of a random type from the profile
    """

    if not isinstance(values, ValueProfile):
        if type is None:
            raise ValueError("Specifying a value directly requires specifying "
                             "a type")
        return type, values

    if type is None:
        type = random.choice(values.types)

    if type == 'string':
        value = random_string(values.string_len)
    elif type == 'char16':
        value = random_string(Range(1, 1))
    elif type in INTEGER_TYPES:
        # TODO: Consider value range of type
        value = random.randint(0, 127)
    elif type in REAL_TYPES:
        # TODO: Consider value range of type
        value = float(random.randint(-1000, 1000))
    elif type in 'boolean':
        value = random.choice((True, False))
    elif type in 'datetime':
        year = random.randint(1, 3000)
        month = random.randint(1, 12)
        day = random.randint(1, 31)
        hour = random.randint(0, 23)
        minute = random.randint(0, 59)
        second = random.randint(0, 59)
        value = CIMDateTime(datetime(year, month, day, hour, minute, second))
    else:
        # The 'reference' type is intentionally not supported here
        raise AssertionError('Invalid CIM type name: {}'.format(type))
    return type, value


def make_properties(number, property_profile):
    """
    Construct and return a list of CIMProperty objects for use on CIM classes,
    that has the specified number of properties according to the specified
    property profile.
    """

    props = []
    for _ in range(0, number):
        pname = random_name(property_profile.name_len)
        ptype, pvalue = random_type_value(property_profile.value_profile)
        if random.random() > property_profile.value_ratio:
            pvalue = None
        pquals = []
        if property_profile.description_len:
            pquals.append(CIMQualifier(
                'Description', type='string',
                value=random_string(property_profile.description_len)))
        if property_profile.qualifier_set_profile:
            qset = random.choice(
                property_profile.qualifier_set_profile.qualifier_sets)
            for j, qname in enumerate(qset.names):
                qtype = qset.types[j]
                _, qvalue = random_type_value(qset.values, type=qtype)
                pquals.append(CIMQualifier(qname, type=qtype, value=qvalue))
        prop = CIMProperty(pname, type=ptype, value=pvalue, qualifiers=pquals)
        props.append(prop)
    return props


def make_class(properties):
    """
    Construct and return a CIMClass object from the specified properties.
    """
    cname = random_name(Range(8, 16))
    cls = CIMClass(cname, properties=properties)
    return cls


def make_instances(cls, number, value_profile):
    """
    Construct and return a number of CIMInstance objects with path, with
    random values for the instance properties.
    """
    insts = []
    for _ in range(0, number):
        inst = CIMInstance(cls.classname)
        # TODO: Make namespace flexible
        inst.path = CIMInstanceName(cls.classname, namespace='root/cimv2')
        for pname, cls_prop in cls.properties.items():
            ptype = cls_prop.type
            _, pvalue = random_type_value(value_profile, type=ptype)
            inst_prop = CIMProperty(pname, type=ptype, value=pvalue)
            inst.properties[pname] = inst_prop
            if cls_prop.qualifiers.get('Key', False):
                inst.path.keybindings[pname] = pvalue
        insts.append(inst)
    return insts


def tst_random_class(num_props):
    """
    Return a CIMClass object with a random class definition that has the
    specified number of properties.
    """
    prop_qset_key = QualifierSet(
        ('Key',),
        ('boolean',),
        True)
    prop_qset_string = QualifierSet(
        ('MinLen', 'MaxLen'),
        ('uint32', 'uint32'),
        ValueProfile(('uint32',), None))
    prop_qset_uint32 = QualifierSet(
        ('MinValue', 'MaxValue'),
        ('sint64', 'sint64'),
        ValueProfile(('sint64',), None))
    prop_profile_key = PropertyProfile(
        Range(4, 16),  # name_len
        ValueProfile(('string',), Range(8, 64)),
        0,  # value_ratio
        Range(16, 256),  # description_len
        QualifierSetProfile((prop_qset_key,))
    )
    prop_profile_string = PropertyProfile(
        Range(4, 16),  # name_len
        ValueProfile(('string',), Range(8, 64)),
        0.2,  # value_ratio
        Range(16, 256),  # description_len
        QualifierSetProfile((prop_qset_string,))
    )
    prop_profile_uint32 = PropertyProfile(
        Range(4, 16),  # name_len
        ValueProfile(('uint32',), None),
        0.2,  # value_ratio
        Range(16, 256),  # description_len
        QualifierSetProfile((prop_qset_uint32,))
    )
    prop_profile_boolean = PropertyProfile(
        Range(4, 16),  # name_len
        ValueProfile(('boolean',), None),
        0.2,  # value_ratio
        Range(16, 256),  # description_len
        None  # no qualifiers
    )
    rem_props = num_props
    num_key = 1
    rem_props -= num_key
    num_string = int(rem_props * 0.4)
    rem_props -= num_string
    num_uint32 = int(rem_props * 0.6)
    rem_props -= num_uint32
    num_boolean = rem_props
    props = []
    props.extend(make_properties(num_key, prop_profile_key))
    props.extend(make_properties(num_string, prop_profile_string))
    props.extend(make_properties(num_uint32, prop_profile_uint32))
    props.extend(make_properties(num_boolean, prop_profile_boolean))
    cls = make_class(props)
    return cls


def tst_random_instances(cls, num_insts):
    """
    Return a list of the specified number of CIMInstance objects of the
    specified class with random property values.
    """
    value_profile_all = ValueProfile(
        ('string', 'uint32', 'boolean'),
        Range(8, 64))
    instances = make_instances(cls, num_insts, value_profile_all)
    return instances


def tst_random_conn(num_insts, num_props):
    """
    Build a FakedWBEMConnection with a mock environment that contains:
    - the qualifiers needed for the class
    - a class with the specified number of properties of types string, uint32,
      boolean, with one string-typed key property
    - the specified number of instances of that class, with random property
      values

    Returns:
      tuple(FakedWBEMConnection, CIMClass, list(CIMInstance))
    """

    qualifiers_mof = """
Qualifier Description : string = null,
    Scope(any),
    Flavor(EnableOverride, ToSubclass, Translatable);

Qualifier Key : boolean = false,
    Scope(property, reference),
    Flavor(DisableOverride, ToSubclass);

Qualifier MaxLen : uint32 = null,
    Scope(property, method, parameter);

Qualifier MaxValue : sint64 = null,
    Scope(property, method, parameter);

Qualifier MinLen : uint32 = 0,
    Scope(property, method, parameter);

Qualifier MinValue : sint64 = null,
    Scope(property, method, parameter);
    """

    cls = tst_random_class(num_props)
    instances = tst_random_instances(cls, num_insts)

    # Build mock environment (using default namespace)
    conn = FakedWBEMConnection(disable_pull_operations=True)
    conn.compile_mof_string(qualifiers_mof)
    conn.add_cimobjects(cls)
    conn.add_cimobjects(instances)

    return conn, cls, instances
