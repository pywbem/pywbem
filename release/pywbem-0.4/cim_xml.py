#! /usr/bin/python
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

"""
pywbem.cim_xml -- Convert CIM objects to XML.

The opposite function, parsing XML into CIM objects is done by
pywbem.tupleparse.

This module creates XML fragments in accordance with the schema for
XML 1.0 Documents representing CIM Element Declarations or
Messages.

There should be one class for each element described in the DTD.  The
constructors take either builtin python types, or other cim_xml
classes where child elements are required.

Every class is a subclass of the Element class and so shares the same
attributes and methods, and can be used with the built-in Python XML
handling routines.  In particular you can call the toxml() and
toprettyxml() methods.

Note that converting using toprettyxml() inserts whitespace which may
corrupt the data in the XML (!!) so you should only do this when
displaying to humans who can ignore it, and never for computers.  (XML
always passes through all non-markup whitespace.)

"""

import xml.dom.minidom
from xml.dom.minidom import Document, Element

def Text(data):
    """Grr.  The API for the minidom text node function has changed in
    Python 2.3.  This function allows the code to run under older
    versions of the intepreter."""
    
    import sys
    if sys.version_info[0] == 2 and sys.version_info[1] >= 3:
        t = xml.dom.minidom.Text()
        t.data = data
        return t
    
    return xml.dom.minidom.Text(data)

class CIMElement(Element):
    """A base class that has a few bonus helper methods."""

    def setName(self, name):
        """Set the NAME attribute."""
        self.setAttribute('NAME', name)

    def setOptionalAttribute(self, name, value):
        """Set an attribute whose value can be None."""        
        if value is not None:
            self.setAttribute(name, value)

    def appendOptionalChild(self, child):
        """Append a child element which can be None."""
        if child is not None:
            self.appendChild(child)

    def appendChildren(self, children):
        """Append a list or tuple of children."""
        for child in children:
            self.appendChild(child)

# Root element

class CIM(CIMElement):
    """
    The CIM element is the root element of every XML Document that is
    valid with respect to this schema. 

    Each document takes one of two forms; it either contains a single
    MESSAGE element defining a CIM message (to be used in the HTTP
    mapping), or it contains a DECLARATION element used to declare a
    set of CIM objects.
 
    <!ELEMENT CIM (MESSAGE | DECLARATION)>
    <!ATTLIST CIM
        CIMVERSION CDATA #REQUIRED
        DTDVERSION CDATA #REQUIRED>
    """

    def __init__(self, data, cim_version, dtd_version):
        Element.__init__(self, 'CIM')
        self.setAttribute('CIMVERSION', cim_version)
        self.setAttribute('DTDVERSION', dtd_version)
        self.appendChild(data)

# Object declaration elements

class DECLARATION(CIMElement):
    """
    The DECLARATION element defines a set of one or more declarations
    of CIM objects.  These are partitioned into logical declaration
    subsets. 
 
    <!ELEMENT DECLARATION  (DECLGROUP|DECLGROUP.WITHNAME|DECLGROUP.WITHPATH)+>
    """

    def __init__(self, data):
        Element.__init__(self, 'DECLARATION')
        self.appendChildren(data)

class DECLGROUP(CIMElement):
    """
    <!ELEMENT DECLGROUP  ((LOCALNAMESPACEPATH|NAMESPACEPATH)?,
                          QUALIFIER.DECLARATION*,VALUE.OBJECT*)>
    """

    def __init__(self, data):
        Element.__init__(self, 'DECLGROUP')
        self.appendChildren(data)

class DECLGROUP_WITHNAME(CIMElement):
    """
    <!ELEMENT DECLGROUP.WITHNAME  ((LOCALNAMESPACEPATH|NAMESPACEPATH)?,
                                   QUALIFIER.DECLARATION*,VALUE.NAMEDOBJECT*)>
    """

    def __init__(self, data):
        Element.__init__(self, 'DECLGROUP.WITHNAME')
        self.appendChildren(data)

class DECLGROUP_WITHPATH(CIMElement):
    """
    <!ELEMENT DECLGROUP.WITHPATH  (VALUE.OBJECTWITHPATH|
                                   VALUE.OBJECTWITHLOCALPATH)*>
    """

    def __init__(self, data):
        Element.__init__(self, 'DECLGROUP.WITHPATH')
        self.appendChildren(data)

class QUALIFIER_DECLARATION(CIMElement):
    """
    <!ELEMENT QUALIFIER.DECLARATION (SCOPE?, (VALUE | VALUE.ARRAY)?)>
    <!ATTLIST QUALIFIER.DECLARATION
         %CIMName;               
         %CIMType;               #REQUIRED
         ISARRAY    (true|false) #IMPLIED
         %ArraySize;
         %QualifierFlavor;>
    """

    def __init__(self, name, type, data, is_array = None,
                 array_size = None, qualifier_flavor = None):
        Element.__init__(self, 'QUALIFIER.DECLARATION')
        self.setName(name)
        self.setAttribute('TYPE', type)
        self.setOptionalAttribute(is_array)
        self.setOptionalAttribute(array_size)
        self.setOptionalAttribute(qualifier_flavor)
        self.appendChildren(data)

class SCOPE(CIMElement):
    """
    The SCOPE element defines the scope of a QUALIFIER.DECLARATION in
    the case that there are restrictions on the scope of the Qualifier
    declaration.

    <!ELEMENT SCOPE EMPTY>
    <!ATTLIST SCOPE 
         CLASS        (true|false)      'false'
         ASSOCIATION  (true|false)      'false'
         REFERENCE    (true|false)      'false'
         PROPERTY     (true|false)      'false'
         METHOD       (true|false)      'false'
         PARAMETER    (true|false)      'false'
         INDICATION   (true|false)      'false'>
    """
    
    def __init__(self, class_ = False, association = False,
                 reference = False, property = False, method = False,
                 parameter = False, indication = False):
        Element.__init__(self, 'SCOPE')
        self.setAttribute('CLASS', str(class_).lower())
        self.setAttribute('ASSOCIATION', str(association).lower())
        self.setAttribute('REFERENCE', str(reference).lower())
        self.setAttribute('PROPERTY', str(property).lower())
        self.setAttribute('METHOD', str(method).lower())
        self.setAttribute('PARAMETER', str(parameter).lower())
        self.setAttribute('INDICATION', str(indication).lower())

# Object value elements

class VALUE(CIMElement):
    """
    The VALUE element is used to define a single (non-array and
    non-reference) CIM Property value, CIM Qualifier value, or a CIM
    Method Parameter value.

    <!ELEMENT VALUE (#PCDATA)>
    """

    def __init__(self, value):
        import types
        Element.__init__(self, 'VALUE')
        if value is not None:
            assert isinstance(value, types.StringTypes)
            t = Text(value)
            self.appendChild(t)

class VALUE_ARRAY(CIMElement):
    """
    The VALUE.ARRAY element is used to represent the value of a CIM
    Property or Qualifier that has an array type.

    <!ELEMENT VALUE.ARRAY (VALUE*)>
    """

    def __init__(self, values):
        Element.__init__(self, 'VALUE.ARRAY')
        self.appendChildren(values)

class VALUE_REFERENCE(CIMElement):
    """
    The VALUE.REFERENCE element is used to define a single CIM
    reference Property value.

    <!ELEMENT VALUE.REFERENCE (CLASSPATH | LOCALCLASSPATH | CLASSNAME |
                               INSTANCEPATH | LOCALINSTANCEPATH |
                               INSTANCENAME)>
    """

    def __init__(self, reference):
        Element.__init__(self, 'VALUE.REFERENCE')
        self.appendChild(reference)

class VALUE_REFARRAY(CIMElement):
    """
    The VALUE.REFARRAY element is used to represent the value of an
    array of CIM references.

    <!ELEMENT VALUE.REFARRAY (VALUE.REFERENCE*)>
    """
    
    def __init__(self, value_references):
        Element.__init__(self, 'VALUE.REFARRAY')
        self.appendChildren(value_references)

class VALUE_OBJECT(CIMElement):
    """
    The VALUE.OBJECT element is used to define a value which is
    comprised of a single CIM Class or Instance definition.
    
    <!ELEMENT VALUE.OBJECT (CLASS | INSTANCE)>
    """

    def __init__(self, data):
        Element.__init__(self, 'VALUE.OBJECT')
        self.appendChild(data)

class VALUE_NAMEDINSTANCE(CIMElement):
    """
    The VALUE.NAMEDINSTANCE element is used to define a value which
    is comprised of a single named CIM Instance definition.
    
    <!ELEMENT VALUE.NAMEDINSTANCE (INSTANCENAME, INSTANCE)>
    """

    def __init__(self, instancename, instance):
        Element.__init__(self, 'VALUE.NAMEDINSTANCE')
        self.appendChild(instancename)
        self.appendChild(instance)

class VALUE_NAMEDOBJECT(CIMElement):
    """
    The VALUE.NAMEDOBJECT element is used to define a value which
    is comprised of a single named CIM Class or Instance definition. 

    <!ELEMENT VALUE.NAMEDOBJECT (CLASS | (INSTANCENAME, INSTANCE))>
    """
    
    def __init__(self, data):
        Element.__init__(self, 'VALUE.NAMEDOBJECT')
        if type(data) == tuple or type(data) == list:
            self.appendChildren(data)
        else:
            self.appendChild(data)

class VALUE_OBJECTWITHPATH(CIMElement):
    """
    The VALUE.OBJECTWITHPATH element is used to define a value
    which is comprised of a single CIM Object (Class or Instance)
    definition with additional information that defines the absolute
    path to that Object.

    <!ELEMENT VALUE.OBJECTWITHPATH ((CLASSPATH, CLASS) |
                                    (INSTANCEPATH, INSTANCE))>
    """
    
    def __init__(self, data1, data2):
        Element.__init__(self, 'VALUE.OBJECTWITHPATH')
        self.appendChild(data1)
        self.appendChild(data2)

class VALUE_OBJECTWITHLOCALPATH(CIMElement):
    """
    The VALUE.OBJECTWITHLOCALPATH element is used to define a value
    which is comprised of a single CIM Object (Class or Instance)
    definition with additional information that defines the local path
    to that Object.    

    <!ELEMENT VALUE.OBJECTWITHLOCALPATH ((LOCALCLASSPATH, CLASS) |
                                         (LOCALINSTANCEPATH, INSTANCE))>
    """

    def __init__(self, data1, data2):
        Element.__init__(self, 'VALUE.OBJECTWITHLOCALPATH')
        self.appendChild(data1)
        self.appendChild(data2)

# Object naming and location elements

class NAMESPACEPATH(CIMElement):
    """
    The NAMESPACEPATH element is used to define a Namespace Path. It
    consists of a HOST element and a LOCALNAMESPACE element.

    <!ELEMENT NAMESPACEPATH (HOST,LOCALNAMESPACEPATH)> 
    """

    def __init__(self, host, localnamespacepath):
        Element.__init__(self, 'NAMESPACEPATH')
        self.appendChild(host)
        self.appendChild(localnamespacepath)

class LOCALNAMESPACEPATH(CIMElement):
    """
    The LOCALNAMESPACEPATH element is used to define a local Namespace
    path (one without a Host component). It consists of one or more
    NAMESPACE elements (one for each namespace in the path). 
 
    <!ELEMENT LOCALNAMESPACEPATH (NAMESPACE+)> 
    """
    
    def __init__(self, namespaces):
        Element.__init__(self, 'LOCALNAMESPACEPATH')
        self.appendChildren(namespaces)

class HOST(CIMElement):
    """
    The HOST element is used to define a single Host. The element
    content MUST specify a legal value for a hostname in accordance
    with the CIM specification.
 
    <!ELEMENT HOST (#PCDATA)> 
    """
    
    def __init__(self, value):
        Element.__init__(self, 'HOST')
        assert isinstance(value, (str, unicode))
        t = Text(value)
        self.appendChild(t)

class NAMESPACE(CIMElement):
    """
    The NAMESPACE element is used to define a single Namespace
    component of a Namespace path.
 
    <!ELEMENT NAMESPACE EMPTY> 
    <!ATTLIST NAMESPACE
        %CIMName;>
    """
    
    def __init__(self, name):
        Element.__init__(self, 'NAMESPACE')
        self.setName(name)
        
class CLASSPATH(CIMElement):
    """
    The CLASSPATH element defines the absolute path to a CIM Class. It
    is formed from a namespace path and Class name. 
 
    <!ELEMENT CLASSPATH (NAMESPACEPATH,CLASSNAME)>
    """
    
    def __init__(self, namespacepath, classname):
        Element.__init__(self, 'CLASSPATH')
        self.appendChild(namespacepath)
        self.appendChild(classname)


class LOCALCLASSPATH(CIMElement):
    """
    The LOCALCLASSPATH element defines the a local path to a CIM
    Class. It is formed from a local namespace path and Class name. 
 
    <!ELEMENT LOCALCLASSPATH (LOCALNAMESPACEPATH, CLASSNAME)>
    """
    
    def __init__(self, localpath, classname):
        Element.__init__(self, 'LOCALCLASSPATH')
        self.appendChild(localpath)
        self.appendChild(classname)

class CLASSNAME(CIMElement):
    """
    The CLASSNAME element defines the qualifying name of a CIM Class.
 
    <!ELEMENT CLASSNAME EMPTY>
    <!ATTLIST CLASSNAME
        %CIMName;>
    """
    
    def __init__(self, classname):
        Element.__init__(self, 'CLASSNAME')
        self.setName(classname)

class INSTANCEPATH(CIMElement):
    """
    The INSTANCEPATH element defines the absolute path to a CIM
    Instance. It is comprised of a Namespace path and an Instance Name
    (model path). 
 
    <!ELEMENT INSTANCEPATH (NAMESPACEPATH,INSTANCENAME)>
    """
    
    def __init__(self, namespacepath, instancename):
        Element.__init__(self, 'INSTANCEPATH')
        self.appendChild(namespacepath)
        self.appendChild(instancename)

class LOCALINSTANCEPATH(CIMElement):
    """
    The LOCALINSTANCEPATH element defines the local path to a CIM
    Instance. It is comprised of a local Namespace path and an
    Instance Name (model path). 
 
    <!ELEMENT LOCALINSTANCEPATH (LOCALNAMESPACEPATH,INSTANCENAME)>
    """
    
    def __init__(self, localpath, instancename):
        Element.__init__(self, 'LOCALINSTANCEPATH')
        self.appendChild(localpath)
        self.appendChild(instancename)

class INSTANCENAME(CIMElement):
    """
    The INSTANCENAME element defines the location of a CIM Instance
    within a Namespace (it is referred to in the CIM Specification
    as a Model Path). It is comprised of a class name and a key
    binding information. 

    If the Class has a single key property, then a single KEYVALUE or
    VALUE.REFERENCE subelement may be used to describe the
    (necessarily) unique key value without a key name. Alternatively a
    single KEYBINDING subelement may be used instead. 

    If the Class has more than one key property, then a KEYBINDING
    subelement MUST appear for each key. 

    If there are no key-bindings specified, the instance is assumed to
    be a singleton instance of a keyless Class. 
 
    <!ELEMENT INSTANCENAME (KEYBINDING*|KEYVALUE?|VALUE.REFERENCE?)>
    <!ATTLIST INSTANCENAME
        %ClassName;>
    """
    
    def __init__(self, classname, data):
        Element.__init__(self, 'INSTANCENAME')
        self.setAttribute('CLASSNAME', classname)
        if data is not None:
            if type(data) == list:
                self.appendChildren(data)
            else:
                self.appendChild(data)

class OBJECTPATH(CIMElement):
    """
    The OBJECTPATH element is used to define a full path to a single
    CIM Object (Class or Instance). 
 
    <!ELEMENT OBJECTPATH (INSTANCEPATH|CLASSPATH)>
    """
    
    def __init__(self, data):
        Element.__init__(self, 'OBJECTPATH')
        self.appendChild(data)

class KEYBINDING(CIMElement):
    """
    The KEYBINDING element defines a single key property value binding.
 
    <!ELEMENT KEYBINDING (KEYVALUE|VALUE.REFERENCE)>
    <!ATTLIST KEYBINDING
        %CIMName;>
    """
    
    def __init__(self, keyname, keyvalue):
        Element.__init__(self, 'KEYBINDING')
        self.setName(keyname)
        self.appendChild(keyvalue)

class KEYVALUE(CIMElement):
    """
    The KEYVALUE element defines a single property key value when the
    key property is a non-reference type. 
 
    <!ELEMENT KEYVALUE (#PCDATA)>
    <!ATTLIST KEYVALUE
        VALUETYPE    (string|boolean|numeric)  'string'>
    """

    def __init__(self, value, value_type = None):
        Element.__init__(self, 'KEYVALUE')
        self.setOptionalAttribute('VALUETYPE', value_type)        
        if value != None:
            assert isinstance(value, (str, unicode))
            t = Text(value)
            self.appendChild(t)        

# Object definition elements
    
class CLASS(CIMElement):
    """
    The CLASS element defines a single CIM Class.
 
    <!ELEMENT CLASS (QUALIFIER*,(PROPERTY|PROPERTY.ARRAY|PROPERTY.REFERENCE)*,
                     METHOD*)>
    <!ATTLIST CLASS 
        %CIMName;
        %SuperClass;>
    """

    def __init__(self, classname, properties = [], methods = [],
                 superclass = None, qualifiers = []):
        Element.__init__(self, 'CLASS')
        self.setName(classname)
        self.setOptionalAttribute('SUPERCLASS', superclass)
        self.appendChildren(qualifiers + properties + methods)

class INSTANCE(CIMElement):
    """
    The INSTANCE element defines a single CIM Instance of a CIM Class.
 
    <!ELEMENT INSTANCE (QUALIFIER*,(PROPERTY|PROPERTY.ARRAY|
                                    PROPERTY.REFERENCE)*)>
    <!ATTLIST INSTANCE
         %ClassName;>
    """
    def __init__(self, classname, properties, qualifiers = []):
        Element.__init__(self, 'INSTANCE')
        self.setAttribute('CLASSNAME', classname)
        self.appendChildren(qualifiers + properties)

class QUALIFIER(CIMElement):
    """
    The QUALIFIER element defines a single CIM Qualifier. If the
    Qualifier has a non-array type, it contains a single VALUE element
    representing the value of the Qualifier. If the Qualifier has an
    array type, it contains a single VALUE.ARRAY element to represent
    the value.

    If the Qualifier has no assigned value then the VALUE element MUST
    be absent. 
 
    <!ELEMENT QUALIFIER ((VALUE|VALUE.ARRAY)?)>
    <!ATTLIST QUALIFIER 
        %CIMName;
        %CIMType;               #REQUIRED 
        %Propagated;
        %QualifierFlavor;>
    """
    
    def __init__(self, name, type, value, propagated = None,
                 qualifier_flavours = {}):
        Element.__init__(self, 'QUALIFIER')
        self.setName(name)
        self.setAttribute('TYPE', type)
        self.setOptionalAttribute('PROPAGATED', propagated)
        for qf in qualifier_flavours.items():
            self.setAttribute(qf[0], qf[1])
        self.appendChild(value)

class PROPERTY(CIMElement):
    """
    The PROPERTY element defines a single (non-array) CIM Property
    that is not a reference. It contains a single VALUE element
    representing the value of the Property. 

    If the Property has no assigned value then the VALUE element MUST be
    absent.

    CIM Reference Properties are described using the
    PROPERTY.REFERENCE element.
 
    <!ELEMENT PROPERTY (QUALIFIER*,VALUE?)>
    <!ATTLIST PROPERTY 
        %CIMName;
        %CIMType;           #REQUIRED 
        %ClassOrigin;
        %Propagated;>
    """

    def __init__(self, name, type, value = None, class_origin = None,
                 propagated = None, qualifiers = []):
        Element.__init__(self, 'PROPERTY')
        self.setName(name)
        self.setAttribute('TYPE', type)
        self.setOptionalAttribute('CLASSORIGIN', class_origin)
        self.setOptionalAttribute('PROPAGATED', propagated)
        self.appendChildren(qualifiers)
        self.appendOptionalChild(value)

class PROPERTY_ARRAY(CIMElement):
    """
    The PROPERTY.ARRAY element defines a single CIM Property with an
    array type. It contains a single VALUE.ARRAY element  representing
    the value of the Property. 

    If the Property has no assigned value then the VALUE.ARRAY element
    MUST be absent. 

    There is no element to model a Property that contains an array of
    references as this is not a valid Property type according to CIM. 
 
    <!ELEMENT PROPERTY.ARRAY (QUALIFIER*,VALUE.ARRAY?)>
    <!ATTLIST PROPERTY.ARRAY 
       %CIMName;
       %CIMType;           #REQUIRED 
       %ArraySize;
       %ClassOrigin;
       %Propagated;>
    """
    
    def __init__(self, name, type, value_array = None, array_size = None,
                 class_origin = None, propagated = None, qualifiers = []):
        Element.__init__(self, 'PROPERTY.ARRAY')
        self.setName(name)
        self.setAttribute('TYPE', type)
        self.setOptionalAttribute('ARRAYSIZE', array_size)
        self.setOptionalAttribute('CLASSORIGIN', class_origin)
        self.setOptionalAttribute('PROPAGATED', propagated)
        self.appendChildren(qualifiers)
        self.appendOptionalChild(value_array)

class PROPERTY_REFERENCE(CIMElement):
    """
    The PROPERTY.REFERENCE element models a single CIM Property with
    reference semantics. In future the features of XML Linking may
    be used to identify linking elements within the XML Document; as
    XML Linking is currently only at Working Draft status no explicit
    dependencies have been made at this point. 
 
    <!ELEMENT PROPERTY.REFERENCE (QUALIFIER*,VALUE.REFERENCE?)>
    <!ATTLIST PROPERTY.REFERENCE
        %CIMName;
        %ReferenceClass;
        %ClassOrigin;
        %Propagated;>
    """
    
    def __init__(self, name, value_reference = None, reference_class = None,
                 class_origin = None, propagated = None, qualifiers = []):
        Element.__init__(self, 'PROPERTY.REFERENCE')
        self.setName(name)
        self.setOptionalAttribute('REFERENCECLASS', reference_class)
        self.setOptionalAttribute('CLASSORIGIN', class_origin)
        self.setOptionalAttribute('PROPAGATED', propagated)
        self.appendChildren(qualifiers)
        self.appendOptionalChild(value_reference)

class METHOD(CIMElement):
    """
    The METHOD element defines a single CIM Method. It may have
    Qualifiers, and zero or more parameters. 

    The order of the PARAMETER, PARAMETER.REFERENCE, PARAMETER.ARRAY
    and PARAMETER.REFARRAY subelements is not significant. 
 
    <!ELEMENT METHOD (QUALIFIER*,(PARAMETER|PARAMETER.REFERENCE|
                                  PARAMETER.ARRAY|PARAMETER.REFARRAY)*)>
    <!ATTLIST METHOD 
        %CIMName;
        %CIMType;          #IMPLIED 
        %ClassOrigin;
        %Propagated;>
    """
    
    def __init__(self, name, parameters = [], return_type = None,
                 class_origin = None, propagated = None, qualifiers = []):
        Element.__init__(self, 'METHOD')
        self.setName(name)
        self.setOptionalAttribute('TYPE', return_type)
        self.setOptionalAttribute('CLASSORIGIN', class_origin)
        self.setOptionalAttribute('PROPAGATED', propagated)
        self.appendChildren(qualifiers + parameters)

class PARAMETER(CIMElement):
    """
    The PARAMETER element defines a single (non-array, non-reference)
    Parameter to a CIM Method. The parameter MAY have zero or more
    Qualifiers. 
 
    <!ELEMENT PARAMETER (QUALIFIER*)>
    <!ATTLIST PARAMETER 
        %CIMName;
        %CIMType;      #REQUIRED>
    """
    
    def __init__(self, name, type, qualifiers = []):
        Element.__init__(self, 'PARAMETER')
        self.setName(name)
        self.setAttribute('TYPE', type)
        self.appendChildren(qualifiers)

class PARAMETER_REFERENCE(CIMElement):
    """
    The PARAMETER.REFERENCE element defines a single reference
    Parameter to a CIM Method. The parameter MAY have zero or more
    Qualifiers.
 
    <!ELEMENT PARAMETER.REFERENCE (QUALIFIER*)>
    <!ATTLIST PARAMETER.REFERENCE
        %CIMName;
        %ReferenceClass;>
    """
    
    def __init__(self, name, reference_class = None, qualifiers = []):
        Element.__init__(self, 'PARAMETER.REFERENCE')
        self.setName(name)
        self.setOptionalAttribute('REFERENCECLASS', reference_class)
        self.appendChildren(qualifiers)

class PARAMETER_ARRAY(CIMElement):
    """
    The PARAMETER.ARRAY element defines a single Parameter to a CIM
    Method that has an array type. The parameter MAY have zero or more
    Qualifiers.
 
    <!ELEMENT PARAMETER.ARRAY (QUALIFIER*)>
    <!ATTLIST PARAMETER.ARRAY
        %CIMName;
        %CIMType;           #REQUIRED
        %ArraySize;>
    """
    
    def __init__(self, name, type, array_size = None, qualifiers = []):
        Element.__init__(self, 'PARAMETER.ARRAY')
        self.setName(name)
        self.setAttribute('TYPE', type)
        self.setOptionalAttribute('ARRAYSIZE', array_size)
        self.appendChildren(qualifiers)

class PARAMETER_REFARRAY(CIMElement):
    """
    The PARAMETER.REFARRAY element defines a single Parameter to a CIM
    Method that has an array of references type. The parameter MAY
    have zero or more Qualifiers. 
 
    <!ELEMENT PARAMETER.REFARRAY (QUALIFIER*)>
    <!ATTLIST PARAMETER.REFARRAY
        %CIMName;
        %ReferenceClass;
        %ArraySize;>
    """
    
    def __init__(self, name, reference_class = None, array_size = None,
                 qualifiers = []):
        Element.__init__(self, 'PARAMETER.REFARRAY')
        self.setName(name)
        self.setOptionalAttribute('REFERENCECLASS', reference_class)
        self.setOptionalAttribute('ARRAYSIZE', array_size)
        self.appendChildren(qualifiers)

# New in v2.2 of the DTD

# TABLECELL.DECLARATION
# TABLECELL.REFERENCE
# TABLEROW.DECLARATION
# TABLE
# TABLEROW

# Message elements

class MESSAGE(CIMElement):
    """
    The MESSAGE element models a single CIM message.  This element is
    used as the basis for CIM Operation Messages and CIM Export
    Messages.

    <!ELEMENT MESSAGE (SIMPLEREQ | MULTIREQ | SIMPLERSP | MULTIRSP)>
    <!ATTLIST MESSAGE
	ID CDATA #REQUIRED
	PROTOCOLVERSION CDATA #REQUIRED>
    """
    
    def __init__(self, data, message_id, protocol_version):
        Element.__init__(self, 'MESSAGE')
        self.setAttribute('ID', str(message_id))
        self.setAttribute('PROTOCOLVERSION', protocol_version)
        self.appendChild(data)

class MULTIREQ(CIMElement):
    """
    The MULTIREQ element defines a Multiple CIM Operation request.  It
    contains two or more subelements defining the SIMPLEREQ elements
    that make up this multiple request.

    <!ELEMENT MULTIREQ (SIMPLEREQ, SIMPLEREQ+)>
    """
    
    def __init__(self, data):
        Element.__init__(self, 'MULTIREQ')
        self.appendChildren(data)

class MULTIEXPREQ(CIMElement):
    """
    The MULTIEXPREQ element defines a Multiple CIM Export request.  It
    contains two or more subelements defining the SIMPLEEXPREQ
    elements that make up this multiple request. 
    
    <!ELEMENT MULTIEXPREQ (SIMPLEEXPREQ, SIMPLEEXPREQ+)>
    """
    
    def __init__(self, data):
        Element.__init__(self, 'MULTIEXPREQ')
        self.appendChildren(data)

class SIMPLEREQ(CIMElement):
    """
    The SIMPLEREQ element defines a Simple CIM Operation request.  It
    contains either a METHODCALL (extrinsic method) element or an
    IMETHODCALL (intrinsic method) element. 
 
    <!ELEMENT SIMPLEREQ (IMETHODCALL | METHODCALL)>
    """
    
    def __init__(self, data):
        Element.__init__(self, 'SIMPLEREQ')
        self.appendChild(data)

class SIMPLEEXPREQ(CIMElement):
    """
    The SIMPLEEXPREQ element defines a Simple CIM Export request.  It
    contains an EXPMETHODCALL (export method). 
    
    <!ELEMENT SIMPLEEXPREQ (EXPMETHODCALL)>
    """
    
    def __init__(self, data):
        Element.__init__(self, 'SIMPLEEXPREQ')
        self.appendChild(data)

class IMETHODCALL(CIMElement):
    """
    The IMETHODCALL element defines a single intrinsic method
    invocation.  It specifies the target local namespace, followed by
    zero or more IPARAMVALUE subelements as the parameter values to be
    passed to the method. If the RESPONSEDESTINATION element is
    specified, the intrinsic method call MUST be interpreted as an
    asynchronous method call. 
    
    <!ELEMENT IMETHODCALL (LOCALNAMESPACEPATH, IPARAMVALUE*)>
    <!ATTLIST IMETHODCALL
	%CIMName;>
    """
    
    def __init__(self, name, localnamespacepath, iparamvalues = []):
        Element.__init__(self, 'IMETHODCALL')
        self.setName(name)
        self.appendChild(localnamespacepath)        
        self.appendChildren(iparamvalues)

class METHODCALL(CIMElement):
    """
    The METHODCALL element defines a single method invocation on a
    Class or Instance.  It specifies the local path of the target
    Class or Instance, followed by zero or more PARAMVALUE subelements
    as the parameter values to be passed to the method. If the
    RESPONSEDESTINATION element is specified, the method call MUST be
    interpreted as an asynchronous method call. 

    <!ELEMENT METHODCALL ((LOCALINSTANCEPATH | LOCALCLASSPATH), PARAMVALUE*)>
    <!ATTLIST METHODCALL
	%CIMName;>
    """
    
    def __init__(self, name, localpath, paramvalues = []):
        Element.__init__(self, 'METHODCALL')
        self.setName(name)
        self.appendChild(localpath)
        self.appendChildren(paramvalues)

class EXPMETHODCALL(CIMElement):
    """
    The EXPMETHODCALL element defines a single export method
    invocation.  It specifies zero or more  <EXPPARAMVALUE>
    subelements as the parameter values to be passed to the method. 
    
    <!ELEMENT EXPMETHODCALL (EXPPARAMVALUE*)>
    <!ATTLIST EXPMETHODCALL
	%CIMName;>
    """
    
    def __init__(self, name, params = []):
        Element.__init__(self, 'EXPMETHODCALL')
        self.setName(name)
        self.appendChildren(params)

class PARAMVALUE(CIMElement):
    """
    The PARAMVALUE element defines a single extrinsic method named
    parameter value. If no subelement is present this indicates that
    no value has been supplied for this parameter.
    
    <!ELEMENT PARAMVALUE (VALUE | VALUE.REFERENCE | VALUE.ARRAY |
                          VALUE.REFARRAY)?>
    <!ATTLIST PARAMVALUE
	%CIMName;>
    """
    
    def __init__(self, name, data = None):
        Element.__init__(self, 'PARAMVALUE')
        self.setName(name)
        self.appendOptionalChild(data)

class IPARAMVALUE(CIMElement):
    """
    The IPARAMVALUE element defines a single intrinsic method named
    parameter value. If no subelement is present this indicates that
    no value has been supplied for this parameter. 

    <!ELEMENT IPARAMVALUE (VALUE | VALUE.ARRAY | VALUE.REFERENCE |
                           INSTANCENAME | CLASSNAME | QUALIFIER.DECLARATION |
                           CLASS | INSTANCE | VALUE.NAMEDINSTANCE)?>
    <!ATTLIST IPARAMVALUE
	%CIMName;>
    """
    
    def __init__(self, name, data = None):
        Element.__init__(self, 'IPARAMVALUE')
        self.setName(name)
        self.appendOptionalChild(data)

class EXPPARAMVALUE(CIMElement):
    """
    The EXPPARAMVALUE element defines a single export method named
    parameter value.  If no subelement is present this indicates that
    no value has been supplied for this parameter. 
    
    <!ELEMENT EXPPARAMVALUE (INSTANCE)?>
    <!ATTLIST EXPPARAMVALUE
	%CIMName;>
    """
    
    def __init__(self, name, data = None):
        Element.__init__(self, 'EXPPARAMVALUE')
        self.setName(name)
        self.appendOptionalChild(data)

class MULTIRSP(CIMElement):
    """
    The MULTIRSP element defines a Multiple CIM Operation response.
    It contains two or more subelements defining the SIMPLERSP
    elements that make up this multiple response. 
    
    <!ELEMENT MULTIRSP (SIMPLERSP, SIMPLERSP+)>
    """
    
    def __init__(self, data):
        Element.__init__(self, 'MULTIRSP')
        self.appendChildren(data)

class MULTIEXPRSP(CIMElement):
    """
    The MULTIEXPRSP element defines a Multiple CIM Export response.
    It contains two or more subelements defining the SIMPLEEXPRSP
    elements that make up this multiple response.
    
    <!ELEMENT MULTIEXPRSP (SIMPLEEXPRSP,SIMPLEEXPRSP+)>
    """

    def __init__(self, data):
        Element.__init__(self, 'MULTIEXPRSP')
        self.appendChildren(data)

class SIMPLERSP(CIMElement):
    """
    The SIMPLERSP element defines a Simple CIM Operation response.  It
    contains either a METHODRESPONSE (for extrinsic methods),
    IMETHODRESPONSE (for intrinsic methods) or a SIMPLEREQACK
    subelement.  
    
    <!ELEMENT SIMPLERSP (METHODRESPONSE | IMETHODRESPONSE)>
    """
    
    def __init__(self, data):
        Element.__init__(self, 'SIMPLERSP')
        self.appendChild(data)

class SIMPLEEXPRSP(CIMElement):
    """
    The SIMPLEEXPRSP element defines a Simple CIM Export response.  It
    contains either a EXPMETHODRESPONSE (for export methods)
    subelement. 
    
    <!ELEMENT SIMPLEEXPRSP (EXPMETHODRESPONSE)>
    """
    
    def __init__(self, data):
        Element.__init__(self, 'SIMPLEEXPRSP')
        self.appendChild(data)

class METHODRESPONSE(CIMElement):
    """
    The METHODRESPONSE defines the response to a single CIM extrinsic
    method invocation.  It contains either an ERROR subelement (to
    report a fundamental error which prevented the method from
    executing), or a combination of an optional return value and zero
    or more out parameter values.  
    
    <!ELEMENT METHODRESPONSE (ERROR | (RETURNVALUE?, PARAMVALUE*))>
    <!ATTLIST METHODRESPONSE
	%CIMName;>
    """
    
    def __init__(self, name, data = None):
        Element.__init__(self, 'METHODRESPONSE')
        self.setName(name)
        if data is not None:
            if type(data) == tuple or type(data) == list:
                self.appendChildren(data)
            else:
                self.appendChild(data)
            
class EXPMETHODRESPONSE(CIMElement):
    """
    The EXPMETHODRESPONSE defines the response to a single export
    method invocation.  It contains either an ERROR subelement (to
    report a fundamental error which prevented the method from
    executing), or an optional return value. 
    
    <!ELEMENT EXPMETHODRESPONSE (ERROR | IRETURNVALUE?)>
    <!ATTLIST EXPMETHODRESPONSE
	%CIMName;>
    """
    
    def __init__(self, name, data = None):
        Element.__init__(self, 'EXPMETHODRESPONSE')
        self.setName(name)
        self.appendOptionalChild(data)

class IMETHODRESPONSE(CIMElement):
    """
    The IMETHODRESPONSE defines the response to a single intrinsic CIM
    method invocation.  It contains either an ERROR subelement (to
    report a fundamental error which prevented the method from
    executing), or an optional return value.  
    
    <!ELEMENT IMETHODRESPONSE (ERROR | IRETURNVALUE?)>
    <!ATTLIST IMETHODRESPONSE
	%CIMName;>
    """
    
    def __init__(self, name, data = None):
        Element.__init__(self, 'IMETHODRESPONSE')
        self.setName(name)
        self.appendOptionalChild(data)

class ERROR(CIMElement):
    """
    The ERROR element is used to define a fundamental error which
    prevented a method from executing normally. It consists of a
    status code, an optional description and zero or more instances
    containing detailed information about the error. 
    
    <!ELEMENT ERROR EMPTY>
    <!ATTLIST ERROR
	CODE CDATA #REQUIRED
	DESCRIPTION CDATA #IMPLIED>
    """
    
    def __init__(self, code, description = None):
        Element.__init__(self, 'ERROR')
        self.setAttribute('CODE', code)
        self.setOptionalAttribute('DESCRIPTION', description)

class RETURNVALUE(CIMElement):
    """
    The RETURNVALUE element specifies the value returned from an
    extrinsic method call. 
    
    <!ELEMENT RETURNVALUE (VALUE | VALUE.ARRAY | VALUE.REFERENCE |
                           VALUE.REFARRAY)>
    """
    
    def __init__(self, data):
        Element.__init__(self, 'RETURNVALUE')
        self.appendChild(data)

class IRETURNVALUE(CIMElement):
    """
    The IRETURNVALUE element specifies the value returned from an
    intrinsic method call. 
    
    <!ELEMENT IRETURNVALUE (CLASSNAME* | INSTANCENAME* | VALUE* |
                            VALUE.OBJECTWITHPATH* |
                            VALUE.OBJECTWITHLOCALPATH* | VALUE.OBJECT* |
                            OBJECTPATH* | QUALIFIER.DECLARATION* |
                            VALUE.ARRAY? | VALUE.REFERENCE? | CLASS* |
                            INSTANCE* | VALUE.NAMEDINSTANCE*)>
    """
    
    def __init__(self, data):
        Element.__init__(self, 'IRETURNVALUE')
        self.appendOptionalChild(data)
