#
# (C) Copyright 2003-2007 Hewlett-Packard Development Company, L.P.
# (C) Copyright 2006-2007 Novell, Inc. 
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
#         Martin Pool <mbp@hp.com>
#         Bart Whiteley <bwhiteley@suse.de>

import string, re
import cim_xml, cim_types
from types import StringTypes
from cim_types import atomic_to_cim_xml, CIMDateTime
from cim_xml import *
from datetime import datetime, timedelta

"""
Representations of CIM Objects.

In general we try to map CIM objects directly into Python primitives,
except when that is not possible or would be ambiguous.  For example,
CIM Class names are simply Python strings, but a ClassPath is
represented as a special Python object.

These objects can also be mapped back into XML, by the toxml() method
which returns a string.
"""

class NocaseDict(object):
    """Yet another implementation of a case-insensitive dictionary."""

    def __init__(self, *args, **kwargs):

        self.data = {}

        # Initialise from sequence object

        if len(args) == 1 and type(args[0]) == list:
            for item in args[0]:
                self[item[0]] = item[1]

        # Initialise from mapping object

        if len(args) == 1 and type(args[0]) == dict:
            self.update(args[0])

        # Initialise from NocaseDict

        if len(args) == 1 and isinstance(args[0], NocaseDict):
            self.data = args[0].data.copy()

        # Initialise from keyword args

        self.update(kwargs)

    # Basic accessor and settor methods

    def __getitem__(self, key):
        k = key
        if isinstance(key, (str, unicode)):
            k = key.lower()
        try:
            return self.data[k][1]
        except KeyError, arg:
            raise KeyError, key

    def __setitem__(self, key, value):
        if not isinstance(key, (str, unicode)):
            raise KeyError, 'Key must be string type'
        k = key.lower()
        self.data[k] = (key, value)

    def __delitem__(self, key):
        k = key
        if isinstance(key, (str, unicode)):
            k = key.lower()
        del self.data[k]

    def __len__(self):
        return len(self.data)

    def has_key(self, key):
        k = key
        if isinstance(key, (str, unicode)):
            k = key.lower()
        return self.data.has_key(k)

    def __contains__(self, key):
        k = key
        if isinstance(key, (str, unicode)):
            k = key.lower()
        return k in self.data

    def get(self, key, default = None):
        try:
            return self[key]
        except KeyError:
            return default

    def setdefault(self, key, default):
        if not self.has_key(key):
            self[key] = default
        return self[key]

    # Other accessor expressed in terms of iterators

    def keys(self):
        return list(self.iterkeys())

    def values(self):
        return list(self.itervalues())

    def items(self):
        return list(self.iteritems())

    # Iterators

    def iterkeys(self):
        for item in self.data.iteritems():
            yield item[1][0]

    def itervalues(self):
        for item in self.data.iteritems():
            yield item[1][1]

    def iteritems(self):
        for item in self.data.iteritems():
            yield item[1]

    # Other stuff

    def __repr__(self):
        items = ', '.join([('%r: %r' % (key, value))
                           for key, value in self.items()])
        return 'NocaseDict({%s})' % items

    def update(self, *args, **kwargs):
        for mapping in args:
            if hasattr(mapping, 'items'):
                for k, v in mapping.items():
                    self[k] = v
            else:
                for (k, v) in mapping:
                    self[k] = v
        for k, v in kwargs.items():
            self[k] = v

    def clear(self):
        self.data.clear()

    def popitem(self):
        pass

    def copy(self):
        result = NocaseDict()
        result.data = self.data.copy()
        return result

    def __eq__(self, other):
        for key, value in self.iteritems():
            if not (key in other) or not (other[key] == value):
                return 0
        return len(self) == len(other)

    def __cmp__(self, other):
        for key, value in self.iteritems():
            if not (key in other):
                return -1
            rv = cmp(value, other[key])
            if rv != 0:
                return rv
        return len(self) - len(other)

def cmpname(name1, name2):
    """Compare to CIM names.  The comparison is done
    case-insensitvely, and one or both of the names may be None."""

    if name1 is None and name2 is None:
        return 0

    if name1 is None:
        return -1

    if name2 is None:
        return 1

    lower_name1 = name1.lower()
    lower_name2 = name2.lower()

    return cmp(lower_name1, lower_name2)

class CIMClassName(object):

    def __init__(self, classname, host = None, namespace = None):

        if not isinstance(classname, StringTypes):
            raise TypeError('classname argument must be a string')

        # TODO: There are some odd restrictions on what a CIM
        # classname can look like (i.e must start with a
        # non-underscore and only one underscore per classname).

        self.classname = classname
        self.host = host
        self.namespace = namespace
        
    def copy(self):
        return CIMClassName(self.classname, host = self.host,
                            namespace = self.namespace)

    def __cmp__(self, other):

        if self is other:
            return 0
        elif not isinstance(other, CIMClassName):
            return 1

        return (cmpname(self.classname, other.classname) or
                cmpname(self.host, other.host) or
                cmpname(self.namespace, other.namespace))

    def __str__(self):
        
        s = ''

        if self.host is not None:
            s += '//%s/' % self.host

        if self.namespace is not None:
            s += '%s:' % self.namespace

        s += self.classname

        return s

    def __repr__(self):

        r = '%s(classname=%s' % (self.__class__.__name__, `self.classname`)

        if self.host is not None:
            r += ', host=%s' % `self.host`

        if self.namespace is not None:
            r += ', namespace=%s' % `self.namespace`

        r += ')'

        return r

    def tocimxml(self):

        classname = cim_xml.CLASSNAME(self.classname)

        if self.namespace is not None:

            localnsp = cim_xml.LOCALNAMESPACEPATH(
                [cim_xml.NAMESPACE(ns)
                 for ns in string.split(self.namespace, '/')])

            if self.host is not None:

                # Classname + namespace + host = CLASSPATH

                return cim_xml.CLASSPATH(
                    cim_xml.NAMESPACEPATH(cim_xml.HOST(self.host), localnsp),
                    classname)

            # Classname + namespace = LOCALCLASSPATH
                                          
            return cim_xml.LOCALCLASSPATH(localnsp, classname)

        # Just classname = CLASSNAME
        
        return cim_xml.CLASSNAME(self.classname)

class CIMProperty(object):
    """A property of a CIMInstance.

    Property objects represent both properties on particular instances,
    and the property defined in a class.  In the first case, the property
    will have a Value and in the second it will not.

    The property may hold an array value, in which case it is encoded
    in XML to PROPERTY.ARRAY containing VALUE.ARRAY."""
    
    def __init__(self, name, value, type = None, 
                 class_origin = None, array_size = None, propagated = None,
                 is_array = False, reference_class = None, qualifiers = {},
                 embedded_object = None):

        # Initialise members

        self.name = name
        self.value = value
        self.type = type
        self.class_origin = class_origin
        self.array_size = array_size
        self.propagated = propagated
        self.qualifiers = NocaseDict(qualifiers)
        self.is_array = is_array
        self.reference_class = reference_class
        self.embedded_object = embedded_object
        
        if isinstance(value, (datetime, timedelta)):
            value = CIMDateTime(value)

        import __builtin__
        if __builtin__.type(value) == list:
            self.is_array = True
        # Determine type of value if not specified

        if type is None:

            # Can't work out what is going on if type and value are
            # both not set.

            if value is None:
                raise TypeError('Null property "%s" must have a type' % name)
        
            if self.is_array:

                # Determine type for list value

                if len(value) == 0:
                    raise TypeError(
                        'Empty property array "%s" must have a type' % name)
                    
                elif isinstance(value[0], CIMInstance):
                    self.type = 'string'
                    self.embedded_object = 'instance'
                elif isinstance(value[0], CIMClass):
                    self.type = 'string'
                    self.embedded_object = 'object'
                else:
                    self.type = cim_types.cimtype(value[0])

            elif isinstance(value, CIMInstanceName):

                self.type = 'reference'

            elif isinstance(value, CIMInstance):
                self.type = 'string'
                self.embedded_object = 'instance'

            elif isinstance(value, CIMClass):
                self.type = 'string'
                self.embedded_object = 'object'
                
            else:

                # Determine type for regular value
                
                self.type = cim_types.cimtype(value)

    def copy(self):

        return CIMProperty(self.name,
                           self.value,
                           type = self.type,
                           class_origin = self.class_origin,
                           array_size = self.array_size,
                           propagated = self.propagated,
                           is_array = self.is_array,
                           reference_class = self.reference_class,
                           qualifiers = self.qualifiers.copy())

    def __repr__(self):

        return '%s(name=%s, type=%s, value=%s, is_array=%s)' % \
               (self.__class__.__name__, `self.name`, `self.type`,
                `self.value`, `self.is_array`)

    def tocimxml(self):

        if self.is_array:

            value = self.value
            if value is not None:
                if value:
                    if self.embedded_object is not None:
                        value = [v.tocimxml().toxml() for v in value]
                value = VALUE_ARRAY([VALUE(atomic_to_cim_xml(v)) for v in value])

            return PROPERTY_ARRAY(
                self.name,
                self.type,
                value,
                self.array_size,
                self.class_origin,
                self.propagated,
                qualifiers = [q.tocimxml() for q in self.qualifiers.values()],
                embedded_object = self.embedded_object)

        elif self.type == 'reference':

            value_reference = None
            if self.value is not None:
                value_reference = VALUE_REFERENCE(self.value.tocimxml())

            return PROPERTY_REFERENCE(
                self.name,
                value_reference,
                reference_class = self.reference_class,
                class_origin = self.class_origin,
                propagated = self.propagated,
                qualifiers = [q.tocimxml() for q in self.qualifiers.values()])

        else:
            value = self.value
            if value is not None:
                if self.embedded_object is not None:
                    value = value.tocimxml().toxml()
                else:
                    value = atomic_to_cim_xml(value)
                value = VALUE(value)

            return PROPERTY(
                self.name,
                self.type,
                value,
                class_origin = self.class_origin,
                propagated = self.propagated,
                qualifiers = [q.tocimxml() for q in self.qualifiers.values()],
                embedded_object = self.embedded_object)

    def __cmp__(self, other):

        if self is other:
            return 0
        elif not isinstance(other, self.__class__):
            return 1

        return (cmpname(self.name, other.name)
                or cmp(self.value, other.value)
                or cmp(self.type, other.type)
                or cmp(self.class_origin, other.class_origin)
                or cmp(self.array_size, other.array_size)
                or cmp(self.propagated, other.propagated)
                or cmp(self.qualifiers, other.qualifiers)
                or cmp(self.is_array, other.is_array)
                or cmpname(self.reference_class, other.reference_class))

class CIMInstanceName(object):
    """Name (keys) identifying an instance.

    This may be treated as a dictionary to retrieve the keys."""

    def __init__(self, classname, keybindings = {}, host = None,
                 namespace = None):

        self.classname = classname
        self.keybindings = NocaseDict(keybindings)
        self.host = host
        self.namespace = namespace

    def copy(self):

        result = CIMInstanceName(self.classname)
        result.keybindings = self.keybindings.copy()
        result.host = self.host
        result.namespace = self.namespace
        
        return result

    def __cmp__(self, other):

        if self is other:
            return 0
        elif not isinstance(other, CIMInstanceName):
            return 1

        return (cmpname(self.classname, other.classname) or
                cmp(self.keybindings, other.keybindings) or
                cmpname(self.host, other.host) or
                cmpname(self.namespace, other.namespace))

    def __str__(self):

        s = ''

        if self.host is not None:
            s += '//%s/' % self.host

        if self.namespace is not None:
            s += '%s:' % self.namespace

        s += '%s.' % self.classname

        for key, value in self.keybindings.items():

            s +='%s=' % key

            if type(value) == int or type(value) == long:
                s += str(value)
            else:
                s += '"%s"' % value

            s += ','
            
        return s[:-1]

    def __repr__(self):

        r = '%s(classname=%s, keybindings=%s' % \
            (self.__class__.__name__,
             `self.classname`,
             `self.keybindings`)

        if self.host is not None:
            r += ', host=%s' % `self.host`

        if self.namespace is not None:
            r += ', namespace=%s' % `self.namespace`

        r += ')'

        return r
        
    # A whole bunch of dictionary methods that map to the equivalent
    # operation on self.keybindings.

    def __getitem__(self, key): return self.keybindings[key]
    def __contains__(self, key): return key in self.keybindings
    def __delitem__(self, key): del self.keybindings[key]
    def __setitem__(self, key, value): self.keybindings[key] = value
    def __len__(self): return len(self.keybindings)
    def has_key(self, key): return self.keybindings.has_key(key)
    def keys(self): return self.keybindings.keys()
    def values(self): return self.keybindings.values()
    def items(self): return self.keybindings.items()
    def iterkeys(self): return self.keybindings.iterkeys()
    def itervalues(self): return self.keybindings.itervalues()
    def iteritems(self): return self.keybindings.iteritems()
    def update(self, *args, **kwargs): self.keybindings.update(*args, **kwargs)

    def tocimxml(self):

        # Generate an XML representation of the instance classname and
        # keybindings.

        if type(self.keybindings) == str:

            # Class with single key string property
        
            instancename_xml = cim_xml.INSTANCENAME(
                self.classname,
                cim_xml.KEYVALUE(self.keybindings, 'string'))

        elif isinstance(self.keybindings, (long, float, int)): 

            # Class with single key numeric property
        
            instancename_xml = cim_xml.INSTANCENAME(
                self.classname,
                cim_xml.KEYVALUE(str(self.keybindings), 'numeric'))

        elif isinstance(self.keybindings, (dict, NocaseDict)):

            # Dictionary of keybindings
            # NOCASE_TODO should remove dict below. 

            kbs = []

            for kb in self.keybindings.items():

                # Keybindings can be integers, booleans, strings or
                # value references.                

                if hasattr(kb[1], 'tocimxml'):
                    kbs.append(cim_xml.KEYBINDING(
                        kb[0],
                        cim_xml.VALUE_REFERENCE(kb[1].tocimxml())))
                    continue
                               
                if type(kb[1]) == bool:
                    _type = 'boolean'
                    if kb[1]:
                        value = 'TRUE'
                    else:
                        value = 'FALSE'
                elif isinstance(kb[1], (long, float, int)): 
                    # pywbem.cim_type.{Sint32, Real64, ... } derive from 
                    # long or float
                    _type = 'numeric'
                    value = str(kb[1])
                elif type(kb[1]) == str or type(kb[1]) == unicode:
                    _type = 'string'
                    value = kb[1]
                else:
                    raise TypeError(
                        'Invalid keybinding type for keybinding ' '%s: %s' % (kb[0],`type(kb[1])`))

                kbs.append(cim_xml.KEYBINDING(
                    kb[0],
                    cim_xml.KEYVALUE(value, _type)))

            instancename_xml = cim_xml.INSTANCENAME(self.classname, kbs)

        else:

            # Value reference

            instancename_xml = cim_xml.INSTANCENAME(
                self.classname,
                cim_xml.VALUE_REFERENCE(self.keybindings.tocimxml()))

        # Instance name plus namespace = LOCALINSTANCEPATH

        if self.host is None and self.namespace is not None:
            return cim_xml.LOCALINSTANCEPATH(
                cim_xml.LOCALNAMESPACEPATH(
                    [cim_xml.NAMESPACE(ns)
                     for ns in string.split(self.namespace, '/')]),
                instancename_xml)

        # Instance name plus host and namespace = INSTANCEPATH

        if self.host is not None and self.namespace is not None:
            return cim_xml.INSTANCEPATH(
                cim_xml.NAMESPACEPATH(
                    cim_xml.HOST(self.host),
                    cim_xml.LOCALNAMESPACEPATH([
                        cim_xml.NAMESPACE(ns)
                        for ns in string.split(self.namespace, '/')])),
                instancename_xml)

        # Just a regular INSTANCENAME

        return instancename_xml

class CIMInstance(object):
    """Instance of a CIM Object.

    Has a classname (string), and named arrays of properties and qualifiers.

    The properties is indexed by name and points to CIMProperty
    instances."""

    def __init__(self, classname, properties = {}, qualifiers = {},
                 path = None, property_list = None):
        """Create CIMInstance.

        bindings is a concise way to initialize property values;
        it is a dictionary from property name to value.  This is
        merely a convenience and gets the same result as the
        properties parameter.

        properties is a list of full CIMProperty objects. """
        
        self.classname = classname
        self.qualifiers = NocaseDict(qualifiers)
        self.path = path
        if property_list is not None:
            self.property_list = [x.lower() for x in property_list]
        else:
            self.property_list = None

        # Assign initialised property values and run through
        # __setitem__ to enforce CIM types for each property.

        self.properties = NocaseDict()
        [self.__setitem__(k, v) for k, v in properties.items()]

    def update(self, *args, **kwargs):
        """D.update(E, **F) -> None.  
        
        Update D from E and F: for k in E: D[k] = E[k]
        (if E has keys else: for (k, v) in E: D[k] = v) 
        then: for k in F: D[k] = F[k] """

        for mapping in args:
            if hasattr(mapping, 'items'):
                for k, v in mapping.items():
                    self[k] = v
            else:
                for (k, v) in mapping:
                    self[k] = v
        for k, v in kwargs.items():
            self[k] = v

    def update_existing(self, *args, **kwargs):
        """Update property values iff the property previously exists.
        
        Update D from E and F: for k in E: D[k] = E[k]
        (if E has keys else: for (k, v) in E: D[k] = v) 
        then: for k in F: D[k] = F[k] 
        
        Like update, but properties that are not already present in the 
        instance are skipped. """

        for mapping in args:
            if hasattr(mapping, 'items'):
                for k, v in mapping.items():
                    try:
                        prop = self.properties[k]
                    except KeyError:
                        continue
                    prop.value = tocimobj(prop.type, v)
            else:
                for (k, v) in mapping:
                    try:
                        prop = self.properties[k]
                    except KeyError:
                        continue
                    prop.value = tocimobj(prop.type, v)
        for k, v in kwargs.items():
            try:
                prop = self.properties[k]
            except KeyError:
                continue
            prop.value = tocimobj(prop.type, v)

    def copy(self):

        result = CIMInstance(self.classname)
        result.properties = self.properties.copy()
        result.qualifiers = self.qualifiers.copy()
        result.path = (self.path is not None and [self.path.copy()] or [None])[0]

        return result

    def __cmp__(self, other):

        if self is other:
            return 0
        elif not isinstance(other, CIMInstance):
            return 1

        return (cmpname(self.classname, other.classname) or
                cmp(self.path, other.path) or
                cmp(self.properties, other.properties) or
                cmp(self.qualifiers, other.qualifiers))

    def __repr__(self):
        # Don't show all the properties and qualifiers because they're
        # just too big
        return '%s(classname=%s, ...)' % (self.__class__.__name__,
                                          `self.classname`)

    # A whole bunch of dictionary methods that map to the equivalent
    # operation on self.properties.

    def __contains__(self, key):
        return key in self.properties

    def __getitem__(self, key):
        return self.properties[key].value
    
    def __delitem__(self, key):
        del self.properties[key]
        
    def __len__(self):
        return len(self.properties)
    
    def has_key(self, key):
        return self.properties.has_key(key)
    
    def keys(self):
        return self.properties.keys()
    
    def values(self):
        return [v.value for v in self.properties.values()]
    
    def items(self):
        return [(k, v.value) for k, v in self.properties.items()]
    
    def iterkeys(self):
        return self.properties.iterkeys()
    
    def itervalues(self):
        for k, v in self.properties.iteritems():
            yield v.value
    
    def iteritems(self):
        for k, v in self.properties.iteritems():
            yield (k, v.value)
    
    def __setitem__(self, key, value):

        # Don't let anyone set integer or float values.  You must use
        # a subclass from the cim_type module.

        if type(value) == int or type(value) == float or type(value) == long:
            raise TypeError('Must use a CIM type assigning numeric values.')

        if self.property_list is not None and key.lower() not in \
                self.property_list:
            if self.path is not None and key not in self.path.keybindings:
                return
        # Convert value to appropriate PyWBEM type

        if isinstance(value, CIMProperty):
            v = value
        else:
            v = CIMProperty(key, value)

        self.properties[key] = v
        if self.path is not None and key in self.path.keybindings:
            self.path[key] = v.value
        
    def tocimxml(self):

        props = []

        for key, value in self.properties.items():
            
            # Value has already been converted into a CIM object
            # property type (e.g for creating null property values).

            if isinstance(value, CIMProperty):
                props.append(value)
                continue

            props.append(CIMProperty(key, value))

        instance_xml = cim_xml.INSTANCE(
            self.classname,
            properties = [p.tocimxml() for p in props],
            qualifiers = [q.tocimxml() for q in self.qualifiers.values()])

        if self.path is None:
            return instance_xml

        return cim_xml.VALUE_NAMEDINSTANCE(self.path.tocimxml(),
                                           instance_xml)

    def tomof(self):

        def _prop2mof(_type, value):
            if value is None:
                val = 'NULL'
            elif isinstance(value, list):
                val = '{'
                for i,x in enumerate(value):
                    if i > 0:
                        val += ', '
                    val += _prop2mof(_type, x)
                val += '}'
            elif _type == 'string':
                val = '"' + value + '"'
            else:
                val = str(value)
            return val

        s = 'instance of %s {\n' % self.classname
        for p in self.properties.values():
            s+= '\t%s = %s;\n' % (p.name, _prop2mof(p.type, p.value))
        s+= '};\n'

        return s



class CIMClass(object):

    def __init__(self, classname, properties = {}, methods = {},
                 superclass = None, qualifiers = {}):

        self.classname = classname
        self.properties = NocaseDict(properties)
        self.qualifiers = NocaseDict(qualifiers)
        self.methods = NocaseDict(methods)
        self.superclass = superclass

    def copy(self):

        result = CIMClass(self.classname)
        result.properties = self.properties.copy()
        result.methods = self.methods.copy()
        result.superclass = self.superclass
        result.qualifiers = self.qualifiers.copy()

        return result

    def __repr__(self):
        return "%s(%s, ...)" % (self.__class__.__name__, `self.classname`)

    def __cmp__(self, other):

        if self is other:
            return 0
        elif not isinstance(other, CIMClass):
            return 1

        return (cmpname(self.classname, other.classname)
                or cmpname(self.superclass, other.superclass)
                or cmp(self.properties, other.properties)
                or cmp(self.qualifiers, other.qualifiers)
                or cmp(self.methods, other.methods))
    
    def tocimxml(self):
        return cim_xml.CLASS(
            self.classname,
            properties = [p.tocimxml() for p in self.properties.values()],
            methods = [m.tocimxml() for m in self.methods.values()],
            qualifiers = [q.tocimxml() for q in self.qualifiers.values()],
            superclass = self.superclass)

    def tomof(self):

        def _makequalifiers(qualifiers, indent):
            """Return a mof fragment for a NocaseDict of qualifiers."""

            if len(qualifiers) == 0:
                return ''
            
            return '[%s]' % ',\n '.ljust(indent+2).join([q.tomof() for q in qualifiers.values()])

        # Class definition

        s = '   %s\n' % _makequalifiers(self.qualifiers, 4)

        s += 'class %s ' % self.classname

        # Superclass

        if self.superclass is not None:
            s += ': %s ' % self.superclass

        s += '{\n'

        # Properties

        for p in self.properties.values():
            s += '      %s\n' % (_makequalifiers(p.qualifiers, 7))
            s += '   %s %s;\n' % (p.type, p.name)

        # Methods

        for m in self.methods.values():
            s += '      %s\n' % (_makequalifiers(m.qualifiers, 7))
            s += '   %s\n' % m.tomof()

        s += '};\n'
        
        return s

class CIMMethod(object):

    def __init__(self, methodname, return_type = None, parameters = {}, 
                 class_origin = None, propagated = False, qualifiers = {}):

        self.name = methodname
        self.return_type = return_type
        self.parameters = NocaseDict(parameters)
        self.class_origin = class_origin
        self.propagated = propagated
        self.qualifiers = NocaseDict(qualifiers)

    def copy(self):

        result = CIMMethod(self.name,
                           return_type = self.return_type,
                           class_origin = self.class_origin,
                           propagated = self.propagated)

        result.parameters = self.parameters.copy()
        result.qualifiers = self.qualifiers.copy()

        return result

    def tocimxml(self):
        return cim_xml.METHOD(
            self.name,
            parameters = [p.tocimxml() for p in self.parameters.values()],
            return_type = self.return_type,
            class_origin = self.class_origin,
            propagated = self.propagated,
            qualifiers = [q.tocimxml() for q in self.qualifiers.values()])

    def __repr__(self):
        return '%s(name=%s, return_type=%s...)' % \
               (self.__class__.__name__, `self.name`, `self.return_type`)

    def __cmp__(self, other):

        if self is other:
            return 0
        elif not isinstance(other, CIMMethod):
            return 1

        return (cmpname(self.name, other.name) or
                cmp(self.parameters, other.parameters) or
                cmp(self.qualifiers, other.qualifiers) or
                cmp(self.class_origin, other.class_origin) or
                cmp(self.propagated, other.propagated) or
                cmp(self.return_type, other.return_type))

    def tomof(self):

        s = ''

        if self.return_type is not None:
            s += '%s ' % self.return_type

        s += '%s(%s);' % \
             (self.name,
              string.join([p.tomof() for p in self.parameters.values()], ', '))

        return s
    
class CIMParameter(object):

    def __init__(self, name, type, reference_class = None, is_array = None,
                 array_size = None, qualifiers = {}, value = None):

        self.name = name
        self.type = type
        self.reference_class = reference_class
        self.is_array = is_array
        self.array_size = array_size
        self.qualifiers = NocaseDict(qualifiers)
        self.value = value

    def copy(self):

        result = CIMParameter(self.name,
                              self.type,
                              reference_class = self.reference_class,
                              is_array = self.is_array,
                              array_size = self.array_size,
                              value = self.value)

        result.qualifiers = self.qualifiers.copy()

        return result

    def __repr__(self):

        return '%s(name=%s, type=%s, is_array=%s)' % \
               (self.__class__.__name__, `self.name`, `self.type`,
                `self.is_array`)

    def __cmp__(self, other):

        if self is other:
            return 0
        elif not isinstance(other, self.__class__):
            return 1

        return (cmpname(self.name, other.name) or
                cmp(self.type, other.type) or
                cmpname(self.reference_class, other.reference_class) or
                cmp(self.is_array, other.is_array) or
                cmp(self.array_size, other.array_size) or
                cmp(self.qualifiers, other.qualifiers) or
                cmp(self.value, other.value))

    def tocimxml(self):

        if self.type == 'reference':

            if self.is_array:

                array_size = None

                if self.array_size is not None:
                    array_size = str(self.array_size)

                return cim_xml.PARAMETER_REFARRAY(
                    self.name,
                    self.reference_class,
                    array_size,
                    qualifiers = [q.tocimxml()
                                  for q in self.qualifiers.values()])

            else:

                return cim_xml.PARAMETER_REFERENCE(
                    self.name,
                    self.reference_class,
                    qualifiers = [q.tocimxml()
                                  for q in self.qualifiers.values()])

        elif self.is_array:
            
            array_size = None

            if self.array_size is not None:
                array_size = str(self.array_size)

            return cim_xml.PARAMETER_ARRAY(
                self.name,
                self.type,
                array_size,
                qualifiers = [q.tocimxml() for q in self.qualifiers.values()])

        else:

            return cim_xml.PARAMETER(
                self.name,
                self.type,
                qualifiers = [q.tocimxml() for q in self.qualifiers.values()])

    def tomof(self):
        return '%s %s' % (self.type, self.name)

class CIMQualifier(object):
    """Represents static annotations of a class, method, property, etc.

    Includes information such as a documentation string and whether a property
    is a key."""
    
    def __init__(self, name, value, type = None, propagated = None,
                 overridable = None, tosubclass = None, toinstance = None,
                 translatable = None):

        self.name = name
        self.type = type
        self.propagated = propagated
        self.overridable = overridable
        self.tosubclass = tosubclass
        self.toinstance = toinstance
        self.translatable = translatable

        # Determine type of value if not specified

        import __builtin__
            
        if type is None:

            # Can't work out what is going on if type and value are
            # both not set.

            if value is None:
                raise TypeError('Null qualifier "%s" must have a type' % name)
        
            if __builtin__.type(value) == list:

                # Determine type for list value

                if len(value) == 0:
                    raise TypeError(
                        'Empty qualifier array "%s" must have a type' % name)
                    
                self.type = cim_types.cimtype(value[0])
                
            else:

                # Determine type for regular value
                
                self.type = cim_types.cimtype(value)

        # Don't let anyone set integer or float values.  You must use
        # a subclass from the cim_type module.

        if __builtin__.type(value) in (int, float, long):
            raise TypeError('Must use a CIM type for numeric qualifiers.')

        self.value = value

    def copy(self):

        return CIMQualifier(self.name,
                            self.value,
                            type = self.type,
                            propagated = self.propagated,
                            overridable = self.overridable,
                            tosubclass = self.tosubclass,
                            toinstance = self.toinstance,
                            translatable = self.translatable)
        
    def __repr__(self):
        return "%s(%s, %s)" % \
               (self.__class__.__name__, `self.name`, `self.value`)

    def __cmp__(self, other):

        if self is other:
            return 0
        elif not isinstance(other, CIMQualifier):
            return 1

        return (cmpname(self.name, other.name) or
                cmp(self.value, other.value) or
                cmp(self.type, other.type) or
                cmp(self.propagated, other.propagated) or
                cmp(self.overridable, other.overridable) or
                cmp(self.tosubclass, other.tosubclass) or
                cmp(self.toinstance, other.toinstance) or
                cmp(self.translatable, other.translatable))

    def tocimxml(self):

        value = None

        if type(self.value) == list:
            value = VALUE_ARRAY([VALUE(v) for v in self.value])
        elif self.value is not None:
            value = VALUE(self.value)

        return QUALIFIER(self.name,
                         self.type,
                         value,
                         propagated = self.propagated,
                         overridable = self.overridable,
                         tosubclass = self.tosubclass,
                         toinstance = self.toinstance,
                         translatable = self.translatable)
    
    def tomof(self):

        def valstr(v):
            if isinstance(v, basestring):
                return '"%s"' % v
            return str(v)

        if type(self.value) == list:
            return '%s {' % self.name + \
                   ', '.join([valstr(v) for v in self.value]) + '}'

        return '%s (%s)' % (self.name, valstr(self.value))

class CIMQualifierDeclaration(object):
    """Represents the declaration of a qualifier."""

    # TODO: Scope and qualifier flavors
    
    def __init__(self, name, type, value = None, is_array = False,
                 array_size = None, scopes = {}, 
                 overridable = None, tosubclass = None, toinstance = None,
                 translatable = None):

        self.name = name
        self.type = type
        self.value = value
        self.is_array = is_array
        self.array_size = array_size
        self.scopes = NocaseDict(scopes)
        self.overridable = overridable
        self.tosubclass = tosubclass
        self.toinstance = toinstance
        self.translatable = translatable

    def copy(self):

        return CIMQualifierDeclaration(self.name,
                                       self.type,
                                       value=self.value,
                                       is_array=self.is_array,
                                       array_size=self.array_size,
                                       scopes=self.scopes,
                                       overridable=self.overridable,
                                       tosubclass=self.tosubclass,
                                       toinstance=self.toinstance,
                                       translatable=self.translatable)
                                       
    def __repr__(self):
        return "%s(%s)" % (self.__class__.__name__, `self.name`)

    def __cmp__(self, other):

        if self is other:
            return 0
        elif not isinstance(other, CIMQualifierDeclaration):
            return 1

        return (cmpname(self.name, other.name) or
                cmp(self.type, other.type) or
                cmp(self.value, other.value) or
                cmp(self.is_array, other.is_array) or
                cmp(self.array_size, other.array_size) or
                cmp(self.scopes, other.scopes) or
                cmp(self.overridable, other.overridable) or
                cmp(self.tosubclass, other.tosubclass) or
                cmp(self.toinstance, other.toinstance) or
                cmp(self.translatable, other.translatable))

    def tocimxml(self):
        
        return QUALIFIER_DECLARATION(self.name,
                                     self.type,
                                     self.value,
                                     is_array = self.is_array,
                                     array_size = self.array_size,
                                     qualifier_scopes = self.scopes,
                                     overridable=self.overridable,
                                     tosubclass=self.tosubclass, 
                                     toinstance=self.toinstance,
                                     translatable=self.translatable)

    def tomof(self):
        mof = 'Qualifier %s : %s' % (self.name, self.type)
        if self.is_array:
            mof+= '['
            if self.array_size is not None:
                mof+= str(self.array_size)
            mof+= ']'
        if self.value is not None:
            if isinstance(self.value, list):
                mof+= '{'
                mof+= ', '.join([atomic_to_cim_xml(tocimobj(self.type, x)) \
                        for x in self.value])
                mof+= '}'
            else:
                mof+= ' = %s' % atomic_to_cim_xml(tocimobj(self.type,self.value))
        mof+= ',\n    '
        mof+= 'Scope('
        mof+= ', '.join([x.lower() for x, y in self.scopes.items() if y]) + ')'
        if not self.overridable and not self.tosubclass \
                and not self.toinstance and not self.translatable:
            mof+= ';'
            return mof
        mof+= ',\n    Flavor('
        mof+= self.overridable and 'EnableOverride' or 'DisableOverride'
        mof+= ', '
        mof+= self.tosubclass and 'ToSubclass' or 'Restricted'
        if self.toinstance:
            mof+= ', ToInstance'
        if self.translatable:
            mof+= ', Translatable'
        mof+= ');'
        return mof

def tocimxml(value):
    """Convert an arbitrary object to CIM xml.  Works with cim_obj
    objects and builtin types."""

    # Python cim_obj object

    if hasattr(value, 'tocimxml'):
        return value.tocimxml()

    # CIMType or builtin type

    if isinstance(value, cim_types.CIMType) or \
           type(value) in (str, unicode, int):
        return cim_xml.VALUE(unicode(value))

    if isinstance(value, bool):
        if value:
            return cim_xml.VALUE('TRUE')
        else:
            return cim_xml.VALUE('FALSE')
        raise TypeError('Invalid boolean type: %s' % value)

    # List of values

    if type(value) == list:
        return cim_xml.VALUE_ARRAY(map(tocimxml, value))

    raise ValueError("Can't convert %s (%s) to CIM XML" %
                     (`value`, type(value)))


def tocimobj(_type, value):
    """Convert a CIM type and a string value into an appropriate
    builtin type."""

    if value is None or _type is None:
        return None

    if _type != 'string' and isinstance(value, basestring) and not value:
        return None

    # Lists of values

    if type(value) == list:
        return map(lambda x: tocimobj(_type, x), value)

    # Boolean type
    
    if _type == 'boolean':
        if isinstance(value, bool):
            return value
        elif isinstance(value, basestring):
            if value.lower() == 'true':
                return True
            elif value.lower() == 'false':
                return False
        raise ValueError('Invalid boolean value "%s"' % value)

    # String type

    if _type == 'string':
        return value

    # Integer types

    if _type == 'uint8':
        return cim_types.Uint8(value)

    if _type == 'sint8':
        return cim_types.Sint8(value)

    if _type == 'uint16':
        return cim_types.Uint16(value)

    if _type == 'sint16':
        return cim_types.Sint16(value)

    if _type == 'uint32':
        return cim_types.Uint32(value)

    if _type == 'sint32':
        return cim_types.Sint32(value)

    if _type == 'uint64':
        return cim_types.Uint64(value)

    if _type == 'sint64':
        return cim_types.Sint64(value)

    # Real types

    if _type == 'real32':
        return cim_types.Real32(value)

    if _type == 'real64':
        return cim_types.Real64(value)

    # Char16

    if _type == 'char16':
        raise ValueError('CIMType char16 not handled')

    # Datetime

    if _type == 'datetime':
        return CIMDateTime(value)

    # REF
    def partition(s, seq):
        """ S.partition(sep) -> (head, sep, tail)

        Searches for the separator sep in S, and returns the part before it,
        the separator itself, and the part after it.  If the separator is not
        found, returns S and two empty strings.
        """
        try:
            return s.partition(seq)
        except AttributeError:
            try:
                idx = s.index(seq)
            except ValueError:
                return (s, '', '')
            return (s[:idx], seq, s[idx+len(seq):])

    if _type == 'reference':
        # TODO doesn't handle double-quoting, as in refs to refs.  Example:
        # r'ex_composedof.composer="ex_sampleClass.label1=9921,label2=\"SampleLabel\"",component="ex_sampleClass.label1=0121,label2=\"Component\""')
        if isinstance(value, (CIMInstanceName, CIMClassName)):
            return value
        elif isinstance(value, basestring):
            ns = host = None
            head, sep, tail = partition(value, '//')
            if sep and head.find('"') == -1:
                # we have a namespace type
                head, sep, tail = partition(tail, '/')
                host = head
            else:
                tail = head
            head, sep, tail = partition(tail, ':')
            if sep:
                ns = head
            else:
                tail = head
            head, sep, tail = partition(tail, '.')
            if not sep:
                return CIMClassName(head, host=host, namespace=ns)
            classname = head
            kb = {}
            while tail:
                head, sep, tail = partition(tail, ',')
                if head.count('"') == 1: # quoted string contains comma
                    tmp, sep, tail = partition(tail,'"')
                    head = '%s,%s' % (head, tmp)
                    tail = partition(tail,',')[2]
                head = head.strip()
                key, sep, val = partition(head,'=')
                if sep:
                    cn, s, k = partition(key, '.')
                    if s:
                        if cn != classname:
                            raise ValueError('Invalid object path: "%s"' % \
                                    value)
                        key = k
                    val = val.strip()
                    if val[0] == '"' and val[-1] == '"':
                        val = val.strip('"')
                    else:
                        if val.lower() in ('true','false'):
                            val = val.lower() == 'true'
                        elif val.isdigit():
                            val = int(val)
                        else:
                            try:
                                val = float(val)
                            except ValueError:
                                try:
                                    val = CIMDateTime(val)
                                except ValueError:
                                    raise ValueError('Invalid key binding: %s'\
                                            % val)
                                

                    kb[key] = val
            return CIMInstanceName(classname, host=host, namespace=ns, 
                    keybindings=kb)
        else:
            raise ValueError('Invalid reference value')

    raise ValueError('Invalid CIM type "%s"' % _type)


def byname(nlist):
    """Convert a list of named objects into a map indexed by name"""
    return dict([(x.name, x) for x in nlist])
