#
# (C) Copyright 2003-2005 Hewlett-Packard Development Company, L.P.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#   
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#   
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
#

# Author: Tim Potter <tpot@hp.com>
#         Martin Pool <mbp@hp.com>

import string, re
from datetime import datetime, timedelta
import cim_xml, cim_types
from types import StringTypes
from cim_types import atomic_to_cim_xml
from cim_xml import *

"""
Representations of CIM Objects.

In general we try to map CIM objects directly into Python primitives,
except when that is not possible or would be ambiguous.  For example,
CIM Class names are simply Python strings, but a ClassPath is
represented as a special Python object.

These objects can also be mapped back into XML, by the toxml() method
which returns a string.
"""

#
# Base objects
#

class NocaseDict:
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

        # Initialise from keyword args

        self.update(kwargs)

    # Basic accessor and settor methods

    def __getitem__(self, key):
        k = key
        if isinstance(key, (str, unicode)):
            k = key.lower()
        return self.data[k][1]

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
        for key in self.data.itervalues():
            yield key[0]

    def itervalues(self):
        for key in self.data.itervalues():
            yield key[1]

    def iteritems(self):
        for key, value in self.data.iteritems():
            yield value[0], value[1]

    # Other stuff

    def __repr__(self):
        items = ', '.join([('%r: %r' % (key, value))
                           for key, value in self.items()])
        return 'NocaseDict({%s})' % items

    def update(self, dict):
        for key, value in dict.items():
            self[key] = value

    def clear(self):
        self.data.clear()

    def popitem(self):
        pass

    def copy(self):
        return NocaseDict(self)

    def __eq__(self, other):
        for key, value in self.iteritems():
            if not (key in other) or not (other[key] == value):
                return 0
        return len(self) == len(other)

class XMLObject:
    """Base class for objects that produce cim_xml document fragments."""

    def toxml(self):
        """Return the XML string representation of ourselves."""
        return self.tocimxml().toxml()

#
# Object location classes
#

#
# It turns out that most of the object location elements can be
# represented easily using one base class which roughly corresponds to
# the OBJECTPATH element.
#
# Element Name        (host,       namespace,    classname, instancename)
# ---------------------------------------------------------------------------
# CLASSNAME           (None,       None,         'CIM_Foo', None)
# LOCALNAMESPACEPATH  (None,       'root/cimv2', None,      None)
# NAMESPACEPATH       ('leonardo', 'root/cimv2', None,      None)
# LOCALCLASSPATH      (None,       'root/cimv2', 'CIM_Foo', None)
# CLASSPATH           ('leonardo', 'root/cimv2', 'CIM_Foo', None)
# LOCALINSTANCEPATH   (None,       'root/cimv2', 'CIM_Foo', InstanceName)
# INSTANCEPATH        ('leonardo', 'root/cimv2', 'CIM_Foo', InstanceName)
#
# These guys also have string representations similar to the output
# produced by the Pegasus::CIMObjectPath.toString() method:
#
# Element Name        Python Class           String representation
# ---------------------------------------------------------------------------
# CLASSNAME           CIMClassName           CIM_Foo
# LOCALNAMESPACEPATH  String                 root/cimv2:
# NAMESPACEPATH       CIMNamespacePath       //leo/root/cimv2:
# LOCALCLASSPATH      CIMLocalClassPath      root/cimv2:CIM_Foo
# CLASSPATH           CIMClassPath           //leo/root/cimv2:CIM_Foo
# INSTANCENAME        CIMInstanceName        CIM_Foo.Foo="Bar"
# LOCALINSTANCEPATH   CIMLocalInstancePath   root/cimv2:CIM_Foo.Foo="Bar"
# INSTANCEPATH        CIMInstancePath        //leo/root/cimv2:CIM_Foo.Foo="Bar"
#

class CIMObjectLocation(XMLObject):
    """A base class that can name any CIM object."""

    def __init__(self, host = None, localnamespacepath = None,
                 classname = None, instancename = None):
        self.host = host
        self.localnamespacepath = localnamespacepath
        self.classname = classname
        self.instancename = instancename

    def HOST(self):
        return cim_xml.HOST(self.host)

    def CLASSNAME(self):
        return cim_xml.CLASSNAME(self.classname)

    def LOCALNAMESPACEPATH(self):
        return cim_xml.LOCALNAMESPACEPATH(
            map(cim_xml.NAMESPACE,
                string.split(self.localnamespacepath, '/')))

    def NAMESPACEPATH(self):
        return cim_xml.NAMESPACEPATH(self.HOST(), self.LOCALNAMESPACEPATH())

    def __cmp__(self, other):
        if self is other:
            return 0
        elif not isinstance(other, CIMObjectLocation):
            return 1
        
        return (cmp(self.host, other.host) or
                cmp(self.localnamespacepath, other.localnamespacepath) or
                cmp(self.classname, other.classname) or
                cmp(self.instancename, other.instancename))


class CIMClassName(CIMObjectLocation):
    def __init__(self, classname):

        if not isinstance(classname, StringTypes):
            raise TypeError('classname argument must be a string')

        # TODO: There are some odd restrictions on what a CIM
        # classname can look like (i.e must start with a
        # non-underscore and only one underscore per classname).

        CIMObjectLocation.__init__(self, classname = classname)

    def tocimxml(self):
        return self.CLASSNAME()

    def __repr__(self):
        return '%s(classname=%s)' % (self.__class__.__name__, `self.classname`)

    def __str__(self):
        return self.classname


class CIMNamespacePath(CIMObjectLocation):

    def __init__(self, host, localnamespacepath):

        if not isinstance(host, StringTypes):
            raise TypeError('host argument must be a string')

        if not isinstance(localnamespacepath, StringTypes):
            raise TypeError('localnamespacepath argument must be a string')

        CIMObjectLocation.__init__(self, host = host,
                                   localnamespacepath = localnamespacepath)

    def tocimxml(self):
        return self.NAMESPACEPATH()

    def __repr__(self):
        return '%s(host=%s, localnamespacepath=%s)' % \
               (self.__class__.__name__, `self.host`,
                `self.localnamespacepath`)

    def __str__(self):
        return '//%s/%s' % (self.host, self.localnamespacepath)


class CIMLocalClassPath(CIMObjectLocation):

    def __init__(self, localnamespacepath, classname):

        if not isinstance(localnamespacepath, StringTypes):
            raise TypeError('localnamespacepath argument must be a string')

        if not isinstance(classname, StringTypes):
            raise TypeError('classname argument must be a string')

        CIMObjectLocation.__init__(self,
                                   localnamespacepath = localnamespacepath,
                                   classname = classname)

    def tocimxml(self):
        return cim_xml.LOCALCLASSPATH(self.LOCALNAMESPACEPATH(),
                                      self.CLASSNAME())

    def __repr__(self):
        return '%s(localnamespacepath=%s, classname=%s)' % \
               (self.__class__.__name__, `self.localnamespacepath`,
                `self.classname`)

    def __str__(self):
        return '%s:%s' % (self.localnamespacepath, self.classname)


class CIMClassPath(CIMObjectLocation):

    def __init__(self, host, localnamespacepath, classname):

        if not isinstance(host, StringTypes):
            raise TypeError('host argument must be a string')

        if not isinstance(localnamespacepath, StringTypes):
            raise TypeError('localnamespacepath argument must be a string')

        if not isinstance(classname, StringTypes):
            raise TypeError('classname argument must be a string')

        CIMObjectLocation.__init__(self, host = host,
                                   localnamespacepath = localnamespacepath,
                                   classname = classname)

    def tocimxml(self):
        return cim_xml.CLASSPATH(self.NAMESPACEPATH(), self.CLASSNAME())

    def __repr__(self):
        return '%s(host=%s, localnamespacepath=%s, classname=%s)' % \
               (self.__class__.__name__, `self.host`,
                `self.localnamespacepath`, `self.classname`)

    def __str__(self):
        return '//%s/%s:%s' % (self.host, self.localnamespacepath,
                               self.classname)


class CIMLocalInstancePath(CIMObjectLocation):

    def __init__(self, localnamespacepath, instancename):

        if not isinstance(localnamespacepath, StringTypes):
            raise TypeError('localnamespacepath argument must be a string')

        if not isinstance(instancename, CIMInstanceName):
            raise TypeError('instancename argument must be a CIMInstanceName')

        CIMObjectLocation.__init__(self,
                                   localnamespacepath = localnamespacepath,
                                   instancename = instancename)

    def tocimxml(self):
        return cim_xml.LOCALINSTANCEPATH(self.LOCALNAMESPACEPATH(),
                                         self.instancename.tocimxml())

    def __repr__(self):
        return '%s(localnamespacepath=%s, instancename=%s)' % \
               (self.__class__.__name__, `self.localnamespacepath`,
                `self.instancename`)

    def __str__(self):
        return '%s:%s' % (self.localnamespacepath, str(self.instancename))


class CIMInstancePath(CIMObjectLocation):

    def __init__(self, host, localnamespacepath, instancename):

        if not isinstance(host, StringTypes):
            raise TypeError('host argument must be a string')

        if not isinstance(localnamespacepath, StringTypes):
            raise TypeError('localnamespacepath argument must be a string')

        if not isinstance(instancename, CIMInstanceName):
            raise TypeError('instancename argument must be a CIMInstanceName')

        CIMObjectLocation.__init__(self, host = host,
                                   localnamespacepath = localnamespacepath,
                                   instancename = instancename)

    def tocimxml(self):
        return cim_xml.INSTANCEPATH(self.NAMESPACEPATH(),
                                    self.instancename.tocimxml())

    def __repr__(self):
        return '%s(host=%s, localnamespacepath=%s, instancename=%s)' % \
               (self.__class__.__name__, `self.host`,
                `self.localnamespacepath`, `self.instancename`)

    def __str__(self):
        return '//%s/%s:%s' % (self.host, self.localnamespacepath,
                               str(self.instancename))

# Object value elements

class CIMProperty(XMLObject):
    """A property of a CIMInstance.

    Property objects represent both properties on particular instances,
    and the property defined in a class.  In the first case, the property
    will have a Value and in the second it will not.

    The property may hold an array value, in which case it is encoded
    in XML to PROPERTY.ARRAY containing VALUE.ARRAY.

    Properties holding references are handled specially as
    CIMPropertyReference."""
    
    def __init__(self, name, type=None,
                 class_origin=None, propagated=None, value=None,
                 is_array = False, qualifiers = None):
        """Construct a new CIMProperty

        Either the type or the value must be given.  If the value is not
        given, it is left as None.  If the type is not given, it is implied
        from the value."""
        assert isinstance(name, StringTypes)
        assert (class_origin is None) or isinstance(class_origin, StringTypes)
        assert (propagated is None) or isinstance(propagated, bool)
        self.name = name
        self.class_origin = class_origin
        self.propagated = propagated
        self.qualifiers = NocaseDict(qualifiers)
        self.is_array = is_array

        if type is None:
            assert value is not None
            self.type = cim_types.cimtype(value)
        else:
            self.type = type

        self.value = value
        

    def __repr__(self):
        r = '%s(name=%s, type=%s' % ('CIMProperty', `self.name`, `self.type`)
        if self.class_origin:
            r += ', class_origin=%s' % `self.class_origin`
        if self.propagated:
            r += ', propagated=%s' % `self.propagated`
        if self.value:
            r += ', value=%s' % `self.value`
        if self.qualifiers:
            r += ', qualifiers=' + `self.qualifiers`
        r += ')'
        return r


    def __cmp__(self, other):
        if self is other:
            return 0
        elif not isinstance(other, CIMProperty):
            return 1

        ## TODO: Allow for the type to be null as long as the values
        ## are the same and non-null?

        return (cmp(self.name, other.name)
                or cmp(self.type, other.type)
                or cmp(self.class_origin, other.class_origin)
                or cmp(self.propagated, other.propagated)
                or cmp(self.value, other.value)
                or cmp(self.qualifiers, other.qualifiers))
    

    def tocimxml(self):
        ## TODO: Have some standard function for turning CIM primitive
        ## types into their correct string representation for XML, rather than just
        ## converting to strings.
        if isinstance(self.value, list):
            va = cim_xml.VALUE_ARRAY([cim_xml.VALUE(atomic_to_cim_xml(s)) for s in self.value])
            return PROPERTY_ARRAY(name=self.name,
                                  type=self.type,
                                  value_array=va,
                                  class_origin=self.class_origin,
                                  propagated=self.propagated,
                                  qualifiers=self.qualifiers)
        else:
            return PROPERTY(name=self.name,
                            type=self.type,
                            value=VALUE(atomic_to_cim_xml(self.value)),
                            class_origin=self.class_origin,
                            propagated=self.propagated,
                            qualifiers=self.qualifiers)


class CIMPropertyReference(XMLObject):
    """A property holding a reference.

    (Not a reference to a property.)

    The reference may be either to an instance or to a class.
    """

    ## TODO: Perhaps unify this with CIMProperty?

    ## TODO: Handle qualifiers

    def __init__(self, name, value, reference_class = None,
                 class_origin = None, propagated = None):
        assert (value is None) or \
               isinstance(value, (CIMInstanceName, CIMClassName, CIMInstancePath,
                                  CIMLocalInstancePath))
        self.name = name
        self.value = value
        self.reference_class = reference_class
        self.class_origin = class_origin
        self.propagated = propagated
        self.qualifiers = NocaseDict()

    def __cmp__(self, other):

        if self is other:
            return 0
        elif not isinstance(other, CIMPropertyReference):
            return 1

        for attr in ['name', 'value', 'reference_class', 'class_origin',
                     'propagated']:
            
            if hasattr(self, attr) and not hasattr(other, attr):
                return 1
            if not hasattr(self, attr) and hasattr(other, attr):
                return -1
            c = cmp(getattr(self, attr), getattr(other, attr))
            if c:
                return c

        return 0

    def tocimxml(self):
        return cim_xml.PROPERTY_REFERENCE(
            self.name,
            cim_xml.VALUE_REFERENCE(self.value.tocimxml()),
            reference_class = self.reference_class,
            class_origin = self.class_origin,
            propagated = self.propagated)

    def __repr__(self):
        result = '%s(name=%s, value=%s' % \
                 (self.__class__.__name__, `self.name`, `self.value`)
        if self.reference_class != None:
            result = result + ', reference_class=%s' % `self.reference_class`
        if self.class_origin != None:
            result = result + ', class_origin=%s' % `self.class_origin`
        if self.propagated != None:
            result = result + ', propagated=%s' % `self.propagated`
        result = result + ')'
        return result

    def __str__(self):
        return str(self.value)

#
# Object definition classes
#

class CIMInstanceName(XMLObject):
    """Name (keys) identifying an instance.

    This may be treated as a dictionary to retrieve the keys."""

    def __init__(self, classname, bindings = {}):
        self.classname = classname
        self.bindings = NocaseDict(bindings)
        self.qualifiers = NocaseDict()

    def __cmp__(self, other):
        if self is other:
            return 0
        elif not isinstance(other, CIMInstanceName):
            return 1

        return cmp(self.classname, other.classname) or \
               cmp(self.bindings, other.bindings) or \
               cmp(self.qualifiers, other.qualifiers)

    def __str__(self):
        s = '%s.' % self.classname

        for key, value in self.bindings.items():

            s = s + '%s=' % key

            if type(value) == int:
                s = s + str(value)
            else:
                s = s + '"%s"' % value

            s = s + ','
            
        return s[:-1]

    def __repr__(self):
        return "%s(%s, %s)" % (self.__class__.__name__,
                               `self.classname`,
                               `self.bindings`)
        
    # A whole bunch of dictionary methods that map to the equivalent
    # operation on self.bindings.

    def __getitem__(self, key): return self.bindings[key]
    def __delitem__(self, key): del self.bindings[key]
    def __setitem__(self, key, value): self.bindings[key] = value
    def __len__(self): return len(self.bindings)
    def has_key(self, key): return self.bindings.has_key(key)
    def keys(self): return self.bindings.keys()
    def values(self): return self.bindings.values()
    def items(self): return self.bindings.items()
    def iterkeys(self): return self.bindings.iterkeys()
    def itervalues(self): return self.bindings.itervalues()
    def iteritems(self): return self.bindings.iteritems()

    def tocimxml(self):

        # Class with single key string property
        
        if type(self.bindings) == str:
            return cim_xml.INSTANCENAME(
                self.classname,
                cim_xml.KEYVALUE(self.bindings, 'string'))

        # Class with single key numeric property
        
        if type(self.bindings) == int:
            return cim_xml.INSTANCENAME(
                self.classname,
                cim_xml.KEYVALUE(str(self.bindings), 'numeric'))

        # Dictionary of keybindings
        # NOCASE_TODO should remove dict below. 

        if type(self.bindings) == dict or isinstance(self.bindings, NocaseDict):

            kbs = []

            for kb in self.bindings.items():

                # Keybindings can be integers, booleans, strings or
                # value references.                

                if hasattr(kb[1], 'tocimxml'):
                    kbs.append(cim_xml.KEYBINDING(
                        kb[0],
                        cim_xml.VALUE_REFERENCE(kb[1].tocimxml())))
                    continue
                               
                if type(kb[1]) == int:
                    _type = 'numeric'
                    value = str(kb[1])
                elif type(kb[1]) == bool:
                    _type = 'boolean'
                    if kb[1]:
                        value = 'TRUE'
                    else:
                        value = 'FALSE'
                elif type(kb[1]) == str or type(kb[1]) == unicode:
                    _type = 'string'
                    value = kb[1]
                else:
                    raise TypeError(
                        'Invalid keybinding type for keybinding ' '%s' % kb[0])

                kbs.append(cim_xml.KEYBINDING(
                    kb[0],
                    cim_xml.KEYVALUE(value, _type)))

            return cim_xml.INSTANCENAME(self.classname, kbs)

        # Value reference

        return cim_xml.INSTANCENAME(
            self.classname, cim_xml.VALUE_REFERENCE(self.bindings.tocimxml()))


class CIMInstance(XMLObject):
    """Instance of a CIM Object.

    Has a classname (string), and named arrays of properties and qualifiers.

    The properties is indexed by name and points to CIMProperty
    instances."""

    ## TODO: Distinguish array from regular properties, perhaps by an
    ## is_array member.

    def __init__(self, classname, bindings = {}, qualifiers = None,
                 properties = []):
        """Create CIMInstance.

        bindings is a concise way to initialize property values;
        it is a dictionary from property name to value.  This is
        merely a convenience and gets the same result as the
        properties parameter.

        properties is a list of full CIMProperty objects. """
        
        assert isinstance(classname, StringTypes)
        self.classname = classname

        self.properties = NocaseDict()
        for prop in properties:
            self.properties[prop.name] = prop
        
        for n, v in bindings.items():
            if isinstance(v, CIMPropertyReference):
                self.properties[n] = v
            else:
                self.properties[n] = CIMProperty(n, value=v)

        self.qualifiers = NocaseDict(qualifiers)

    def __cmp__(self, other):
        if self is other:
            return 0
        if not isinstance(other, CIMInstance):
            return 1

        return (cmp(self.classname, other.classname) or
                cmp(self.properties, other.properties) or
                cmp(self.qualifiers, other.qualifiers))

    def __repr__(self):
        # Don't show all the properties and qualifiers because they're
        # just too big
        return '%s(classname=%s, ...)' % (self.__class__.__name__,
                                          `self.classname`)

    # A whole bunch of dictionary methods that map to the equivalent
    # operation on self.properties.

    def __getitem__(self, key): return self.properties[key].value
    def __delitem__(self, key): del self.properties[key]
    def __len__(self): return len(self.properties)
    def has_key(self, key): return self.properties.has_key(key)
    def keys(self): return self.properties.keys()
    def values(self): return self.properties.values()
    def items(self): return self.properties.items()
    def iterkeys(self): return self.properties.iterkeys()
    def itervalues(self): return self.properties.itervalues()
    def iteritems(self): return self.properties.iteritems()
    
    def __setitem__(self, key, value):

        # Don't let anyone set integer or float values.  You must use
        # a subclass from the cim_type module.

        # TODO: Lift this into a common function that checks a CIM
        # value is acceptable.

        if type(value) == int or type(value) == float or type(value) == long:
            raise TypeError('Must use a CIM type assigning numeric values.')

        self.properties[key] = CIMProperty(key, value = value)
        
    def tocimxml(self):
        props_xml = []

        for prop in self.properties.values():
            assert isinstance(prop, (CIMProperty, CIMPropertyReference))
            props_xml.append(prop.tocimxml())
            
        return cim_xml.INSTANCE(self.classname, props_xml)


class CIMNamedInstance(XMLObject):
    # Used for e.g. modifying an instance: name identifies the
    # instance to change; instance gives the new values.
    def __init__(self, name, instance):
        self.name = name
        self.instance = instance

    def tocimxml(self):
        return cim_xml.VALUE_NAMEDINSTANCE(self.name.tocimxml(),
                                           self.instance.tocimxml())

    def __cmp__(self, other):
        if self is other:
            return 0
        elif not isinstance(other, CIMNamedInstance):
            return 1

        return cmp(self.name) or cmp(self.instance)
    

class CIMClass(XMLObject):
    """Class, including a description of properties, methods and qualifiers.

    superclass may be None."""
    def __init__(self, classname, properties = {}, qualifiers = None,
                 methods = {}, superclass = None):
        assert isinstance(classname, StringTypes)
        self.classname = classname
        self.properties = NocaseDict(properties)
        self.qualifiers = NocaseDict(qualifiers)
        self.methods = NocaseDict(methods)
        self.superclass = superclass

    def __repr__(self):
        return "%s(%s, ...)" % (self.__class__.__name__, `self.classname`)

    def __cmp__(self, other):
        if self is other:
            return 0
        elif not isinstance(other, CIMClass):
            return 1

        return (cmp(self.classname, other.classname)
                or cmp(self.superclass, other.superclass)
                or cmp(self.properties, other.properties)
                or cmp(self.qualifiers, other.qualifiers)
                or cmp(self.methods, other.methods))

    
    def tocimxml(self):
        ## TODO: Don't we need to pack qualfiers, methods, etc?
        return cim_xml.CLASS()


class CIMMethod(XMLObject):

    def __init__(self, methodname, parameters = {}, qualifiers = None,
                 type = None, class_origin = None, propagated = False):
        self.name = methodname
        self.parameters = NocaseDict(parameters)
        self.qualifiers = NocaseDict(qualifiers)
        self.class_origin = class_origin
        self.type = type
        self.propagated = propagated

    def tocimxml(self):
        return cim_xml.METHOD()

    def __repr__(self):
        return '%s(name=%s, ...)' % (self.__class__.__name__, `self.name`)

    def __cmp__(self, other):
        if self is other:
            return 0
        elif not isinstance(other, CIMMethod):
            return 1

        return (cmp(self.name, other.name) or
                cmp(self.parameters, other.parameters) or
                cmp(self.qualifiers, other.qualifiers) or
                cmp(self.class_origin, other.class_origin) or
                cmp(self.propagated, other.propagated) or
                cmp(self.type, other.type))


class CIMParameter(XMLObject):
    """A parameter to a CIMMethod.

    Parameter objects represent parameters to methods defined in a class.

    Parameters may represent array and reference types.  They are represented
    in XML PARAMETER, PARAMETER.ARRAY, PARAMETER.REFERENCE, and 
    PARAMETER.REFARRAY."""

    def __init__(self, name, type, is_reference = False,
                 is_array = False, array_size=None, qualifiers = None):
        """Construct a new CIMParameter

        if is_reference is True, type is the reference class.  Otherwise
        it is the cim data type"""

        assert isinstance(name, StringTypes)
        # TODO make sure either is_reference is True or type is not None. 
        self.name = name
        self.qualifiers = NocaseDict(qualifiers)
        self.is_array = is_array
        self.is_reference = is_reference
        self.array_size = array_size
        self.type = type
        

    def __repr__(self):
        r = '%s(name=%s, type=%s' % ('CIMParameter', `self.name`, `self.type`)
        if self.qualifiers:
            r += ', qualifiers=' + `self.qualifiers`
        r += ')'
        return r


    def __cmp__(self, other):
        if self is other:
            return 0
        elif not isinstance(other, CIMParameter):
            return 1


        return (cmp(self.name, other.name)
                or cmp(self.type, other.type)
                or cmp(self.is_array, other.is_array)
                or cmp(self.is_reference, other.is_reference)
                or cmp(self.array_size, other.array_size)
                or cmp(self.qualifiers, other.qualifiers))
    

    def tocimxml(self):
        if self.is_array:
            if self.is_reference:
                return PARAMETER_REFARRAY(name=self.name,
                                          array_size=self.array_size,
                                          qualifiers=self.qualifiers,
                                          reference_class=self.type)
            else:
                return PARAMETER_ARRAY(name=self.name,
                                       type=self.type,
                                       array_size=self.array_size,
                                       qualifiers=self.qualifiers)
        else:
            if self.is_reference:
                return PARAMETER_REFERENCE(name=self.name,
                                           reference_class=self.type,
                                           qualifiers=self.qualifiers)
            else:
                return PARAMETER(name=self.name,
                                 type=self.type,
                                 qualifiers=self.qualifiers)


class CIMQualifier:
    """Represents static annotations of a class, method, property, etc.

    Includes information such as a documentation string and whether a property
    is a key."""
    def __init__(self, name, value, overridable=None, propagated=None,
                 toinstance=None, tosubclass=None, translatable=None):
        self.name = name
        self.value = value
        
        self.overridable = overridable
        self.propagated = propagated
        self.toinstance = toinstance
        self.tosubclass = tosubclass
        self.translatable = translatable
        
    def __repr__(self):
        return "%s(%s, ...)" % (self.__class__.__name__, `self.name`)

    def __cmp__(self, other):
        if self is other:
            return 0
        elif not isinstance(other, CIMQualifier):
            return 1

        return cmp(self.__dict__, other.__dict__)
    

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

    # Lists of values

    if type(value) == list:
        return map(lambda x: tocimobj(_type, x), value)

    # Boolean type
    
    if _type == 'boolean':
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

        if value is None:
            return None

	tv_pattern = re.compile(r'^(\d{8})(\d{2})(\d{2})(\d{2})\.(\d{6})(:)(\d{3})')
	date_pattern = re.compile(r'^(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})\.(\d{6})([+|-])(\d{3})')
	s = tv_pattern.search(value)
	if s is None:
		s = date_pattern.search(value)
		if s is None:
			raise ValueError('Invalid Datetime format "%s"' % value)
		else:
			g = s.groups()
			return datetime(int(g[0]),int(g[1]),int(g[2]),int(g[3]),int(g[4]),int(g[5]),int(g[6]))
	else:
		g = s.groups()
		return timedelta(days=int(g[0]),hours=int(g[1]),minutes=int(g[2]),seconds=int(g[3]),microseconds=int(g[4]))
		
        return value

    # NULL return value

    if _type is None:
        return None

    raise ValueError('Invalid CIM type "%s"' % _type)


def byname(nlist):
    """Convert a list of named objects into a map indexed by name"""
    return dict([(x.name, x) for x in nlist])
