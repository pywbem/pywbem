#
# (C) Copyright 2006, 2007 Hewlett-Packard Development Company, L.P.
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

from xml.dom.pulldom import *
from pywbem import *

class ParseError(Exception):
    """This exception is raised when there is a validation error detected
    by the parser."""    
    pass

#
# Helper functions
#

def get_required_attribute(node, attr):
    """Return an attribute by name.  Throw an exception if not present."""
    
    if not node.hasAttribute(attr):
        raise ParseError(
            'Expecting %s attribute in element %s' % (attr, node.tagName))

    return node.getAttribute(attr)

def get_attribute(node, attr):
    """Return an attribute by name, or None if not present."""
    
    if node.hasAttribute(attr):
        return node.getAttribute(attr)

    return None

def get_end_event(parser, tagName):
    """Check that the next event is the end of a particular tag."""

    (event, node) = parser.next()

    if event != END_ELEMENT or node.tagName != tagName:
        raise ParseError(
            'Expecting %s end tag, got %s %s' % (tagName, event, node.tagName))

def is_start(event, node, tagName):
    """Return true if (event, node) is a start event for tagname."""
    return event == START_ELEMENT and node.tagName == tagName

def is_end(event, node, tagName):
    """Return true if (event, node) is an end event for tagname."""
    return event == END_ELEMENT and node.tagName == tagName

# <!-- ************************************************** -->
# <!-- Root element                                       -->
# <!-- ************************************************** -->

# <!ELEMENT CIM (MESSAGE | DECLARATION)>
# <!ATTLIST CIM
# 	CIMVERSION CDATA #REQUIRED
# 	DTDVERSION CDATA #REQUIRED
# >

# <!-- ************************************************** -->
# <!-- Object declaration elements                        -->
# <!-- ************************************************** -->

# <!ELEMENT DECLARATION (DECLGROUP | DECLGROUP.WITHNAME | DECLGROUP.WITHPATH)+>
# <!ELEMENT DECLGROUP ((LOCALNAMESPACEPATH | NAMESPACEPATH)?, QUALIFIER.DECLARATION*, VALUE.OBJECT*)>
# <!ELEMENT DECLGROUP.WITHNAME ((LOCALNAMESPACEPATH | NAMESPACEPATH)?, QUALIFIER.DECLARATION*, VALUE.NAMEDOBJECT*)>
# <!ELEMENT DECLGROUP.WITHPATH (VALUE.OBJECTWITHPATH | VALUE.OBJECTWITHLOCALPATH)*>
# <!ELEMENT QUALIFIER.DECLARATION (SCOPE?, (VALUE | VALUE.ARRAY)?)>
# <!ATTLIST QUALIFIER.DECLARATION 
#          %CIMName;               
#          %CIMType;               #REQUIRED
#          ISARRAY    (true|false) #IMPLIED
#          %ArraySize;
#          %QualifierFlavor;>
# <!ELEMENT SCOPE EMPTY>
# <!ATTLIST SCOPE
# 	CLASS (true | false) "false"
# 	ASSOCIATION (true | false) "false"
# 	REFERENCE (true | false) "false"
# 	PROPERTY (true | false) "false"
# 	METHOD (true | false) "false"
# 	PARAMETER (true | false) "false"
# 	INDICATION (true | false) "false"
# >

# <!-- ************************************************** -->
# <!-- Object Value elements                              -->
# <!-- ************************************************** -->

# <!ELEMENT VALUE (#PCDATA)>

def parse_value(parser, event, node):

    value = ''

    (next_event, next_node) = parser.next()

    if next_event == CHARACTERS:        

        value = next_node.nodeValue

        (next_event, next_node) = parser.next()
        
    if not is_end(next_event, next_node, 'VALUE'):
        raise ParseError('Expecting end VALUE')
        
    return value

# <!ELEMENT VALUE.ARRAY (VALUE*)>

def parse_value_array(parser, event, node):

    value_array = []

    (next_event, next_node) = parser.next()

    if is_start(next_event, next_node, 'VALUE'):

        value_array.append(parse_value(parser, next_event, next_node))

        while 1:

            (next_event, next_node) = parser.next()

            if is_end(next_event, next_node, 'VALUE.ARRAY'):
                break

            if is_start(next_event, next_node, 'VALUE'):
                value_array.append(parse_value(parser, next_event, next_node))
            else:
                raise ParseError('Expecting VALUE element')

    return value_array

# <!ELEMENT VALUE.REFERENCE (CLASSPATH | LOCALCLASSPATH | CLASSNAME |
#                            INSTANCEPATH | LOCALINSTANCEPATH | INSTANCENAME)>

def parse_value_reference(parser, event, node):

    (next_event, next_node) = parser.next()

    if is_start(next_event, next_node, 'CLASSPATH'):
        result = parse_classpath(parser, next_event, next_node)

    elif is_start(next_event, next_node, 'LOCALCLASSPATH'):
        result = parse_localclasspath(parser, next_event, next_node)

    elif is_start(next_event, next_node, 'CLASSNAME'):
        result = parse_classname(parser, next_event, next_node)

    elif is_start(next_event, next_node, 'INSTANCEPATH'):
        result = parse_instancepath(parser, next_event, next_node)

    elif is_start(next_event, next_node, 'LOCALINSTANCEPATH'):
        result = parse_localinstancepath(parser, next_event, next_node)

    elif is_start(next_event, next_node, 'INSTANCENAME'):
        result = parse_instancename(parser, next_event, next_node)
        
    else:
        raise ParseError('Expecting (CLASSPATH | LOCALCLASSPATH | CLASSNAME '
                         '| INSTANCEPATH | LOCALINSTANCEPATH | INSTANCENAME)')
                         
    get_end_event(parser, 'VALUE.REFERENCE')

    return result

# <!ELEMENT VALUE.REFARRAY (VALUE.REFERENCE*)>
# <!ELEMENT VALUE.OBJECT (CLASS | INSTANCE)>
# <!ELEMENT VALUE.NAMEDINSTANCE (INSTANCENAME, INSTANCE)>
# <!ELEMENT VALUE.NAMEDOBJECT (CLASS | (INSTANCENAME, INSTANCE))>
# <!ELEMENT VALUE.OBJECTWITHLOCALPATH ((LOCALCLASSPATH, CLASS) | (LOCALINSTANCEPATH, INSTANCE))>
# <!ELEMENT VALUE.OBJECTWITHPATH ((CLASSPATH, CLASS) | (INSTANCEPATH, INSTANCE))>
# <!ELEMENT VALUE.NULL EMPTY>
 
# <!-- ************************************************** -->
# <!-- Object naming and locating elements                -->
# <!-- ************************************************** -->

# <!ELEMENT NAMESPACEPATH (HOST, LOCALNAMESPACEPATH)>

def parse_namespacepath(parser, event, node):
    
    (next_event, next_node) = parser.next()

    if not is_start(next_event, next_node, 'HOST'):
        raise ParseError('Expecting HOST')
    
    host = parse_host(parser, next_event, next_node)

    (next_event, next_node) = parser.next()

    if not is_start(next_event, next_node, 'LOCALNAMESPACEPATH'):
        raise ParseError('Expecting LOCALNAMESPACEPATH')
    
    namespacepath = parse_localnamespacepath(parser, next_event, next_node)

    (next_event, next_node) = parser.next()

    if not is_end(next_event, next_node, 'NAMESPACEPATH'):
        raise ParseError('Expecting end NAMESPACEPATH')

    return (host, namespacepath)

# <!ELEMENT LOCALNAMESPACEPATH (NAMESPACE+)>

def parse_localnamespacepath(parser, event, node):

    (next_event, next_node) = parser.next()

    namespaces = []

    if not is_start(next_event, next_node, 'NAMESPACE'):
        print next_event, next_node
        raise ParseError('Expecting NAMESPACE')

    namespaces.append(parse_namespace(parser, next_event, next_node))

    while 1:

        (next_event, next_node) = parser.next()

        if is_end(next_event, next_node, 'LOCALNAMESPACEPATH'):
            break

        if is_start(next_event, next_node, 'NAMESPACE'):
            namespaces.append(parse_namespace(parser, next_event, next_node))
        else:
            raise ParseError('Expecting NAMESPACE')

    return string.join(namespaces, '/')

# <!ELEMENT HOST (#PCDATA)>

def parse_host(parser, event, node):

    host = ''

    (next_event, next_node) = parser.next()

    if next_event == CHARACTERS:        

        host = next_node.nodeValue

        (next_event, next_node) = parser.next()
        
    if not is_end(next_event, next_node, 'HOST'):
        raise ParseError('Expecting end HOST')
        
    return host

# <!ELEMENT NAMESPACE EMPTY>
# <!ATTLIST NAMESPACE
# 	%CIMName; 
# >

def parse_namespace(parser, event, node):

    name = get_required_attribute(node, 'NAME')

    (next_event, next_node) = parser.next()

    if not is_end(next_event, next_node, 'NAMESPACE'):
        raise ParseError('Expecting end NAMESPACE')

    return name

# <!ELEMENT CLASSPATH (NAMESPACEPATH, CLASSNAME)>

# <!ELEMENT LOCALCLASSPATH (LOCALNAMESPACEPATH, CLASSNAME)>

# <!ELEMENT CLASSNAME EMPTY>
# <!ATTLIST CLASSNAME
# 	%CIMName; 
# >

# <!ELEMENT INSTANCEPATH (NAMESPACEPATH, INSTANCENAME)>

def parse_instancepath(parser, event, node):

    (next_event, next_node) = parser.next()

    if not is_start(next_event, next_node, 'NAMESPACEPATH'):
        raise ParseError('Expecting NAMESPACEPATH')
    
    host, namespacepath = parse_namespacepath(parser, next_event, next_node)

    (next_event, next_node) = parser.next()

    if not is_start(next_event, next_node, 'INSTANCENAME'):
        print next_event, next_node
        raise ParseError('Expecting INSTANCENAME')

    instancename = parse_instancename(parser, next_event, next_node)

    instancename.host = host
    instancename.namespace = namespacepath

    return instancename

# <!ELEMENT LOCALINSTANCEPATH (LOCALNAMESPACEPATH, INSTANCENAME)>

def parse_localinstancepath(parser, event, node):

    (next_event, next_node) = parser.next()

    if not is_start(next_event, next_node, 'LOCALNAMESPACEPATH'):
        raise ParseError('Expecting LOCALNAMESPACEPATH')
    
    namespacepath = parse_localnamespacepath(parser, next_event, next_node)

    (next_event, next_node) = parser.next()

    if not is_start(next_event, next_node, 'INSTANCENAME'):
        raise ParseError('Expecting INSTANCENAME')

    instancename = parse_instancename(parser, next_event, next_node)

    instancename.namespace = namespacepath

    return instancename

# <!ELEMENT INSTANCENAME (KEYBINDING* | KEYVALUE? | VALUE.REFERENCE?)>
# <!ATTLIST INSTANCENAME
# 	%ClassName; 
# >

def parse_instancename(parser, event, node):
    
    classname = get_required_attribute(node, 'CLASSNAME')
    keybindings = []
    
    (next_event, next_node) = parser.next()

    if is_start(next_event, next_node, 'KEYBINDING'):

        keybindings.append(parse_keybinding(parser, next_event, next_node))

        while 1:

            (next_event, next_node) = parser.next()

            if is_end(next_event, next_node, 'INSTANCENAME'):
                break

            if is_start(next_event, next_node, 'KEYBINDING'):
                keybindings.append(
                    parse_keybinding(parser, next_event, next_node))
            else:
                raise ParseError('Expecting KEYBINDING element')
            
    if is_end(next_event, next_node, 'INSTANCENAME'):
        pass
            
    elif is_start(next_event, next_node, 'KEYVALUE'):
        keybindings.append(('', parse_keyvalue(parser, next_event, next_node)))
        
    elif is_start(next_event, next_node, 'VALUE.REFERENCE'):        
        keybindings.append(
            parse_value_reference(parser, next_event, next_node))
        
    else:
        raise ParseError(
            'Expecting KEYBINDING* | KEYVALUE? | VALUE.REFERENCE')

    return CIMInstanceName(classname, keybindings)

# <!ELEMENT OBJECTPATH (INSTANCEPATH | CLASSPATH)>

# <!ELEMENT KEYBINDING (KEYVALUE | VALUE.REFERENCE)>
# <!ATTLIST KEYBINDING
# 	%CIMName; 
# >

def parse_keybinding(parser, event, node):

    name = get_required_attribute(node, 'NAME')

    (next_event, next_node) = parser.next()

    if is_start(next_event, next_node, 'KEYVALUE'):
        keyvalue = parse_keyvalue(parser, next_event, next_node)
        result = (name, keyvalue)

    elif is_start(next_event, next_node, 'VALUE.REFERENCE'):
        value_reference = parse_value_reference(parser, next_event, next_node)
        result = (name, value_reference)

    else:
        raise ParseError('Expecting KEYVALUE or VALUE.REFERENCE element')

    get_end_event(parser, 'KEYBINDING')

    return result

# <!ELEMENT KEYVALUE (#PCDATA)>
# <!ATTLIST KEYVALUE
# 	VALUETYPE (string | boolean | numeric) "string"
#         %CIMType;              #IMPLIED>

def parse_keyvalue(parser, event, node):

    valuetype = get_required_attribute(node, 'VALUETYPE')
    type = get_attribute(node, 'TYPE')

    (next_event, next_node) = parser.next()

    if next_event != CHARACTERS:
        raise ParseError('Expecting character data')
        
    value = next_node.nodeValue

    if valuetype == 'string':
        pass

    elif valuetype == 'boolean':

        # CIM-XML says "These values MUST be treated as
        # case-insensitive" (even though the XML definition
        # requires them to be lowercase.)

        p = value.strip().lower()

        if p == 'true':
            value = True
        elif p == 'false':
            value = False
        else:
            raise ParseError('invalid boolean value "%s"' % `p`)

    elif valuetype == 'numeric':

        try: 

            # XXX: Use TYPE attribute to create named CIM type.
            # if attrs(tt).has_key('TYPE'):
            #    return cim_obj.tocimobj(attrs(tt)['TYPE'], p.strip())

            # XXX: Would like to use long() here, but that tends to cause
            # trouble when it's written back out as '2L'

            value = int(value.strip(), 0)

        except ValueError:
            raise ParseError(
                'invalid numeric value "%s"' % value)

    else:
        raise ParseError('Invalid VALUETYPE')

    get_end_event(parser, 'KEYVALUE')

    return value

# <!-- ************************************************** -->
# <!-- Object definition elements                         -->
# <!-- ************************************************** -->

# <!ELEMENT CLASS (QUALIFIER*, (PROPERTY | PROPERTY.ARRAY | PROPERTY.REFERENCE)*, METHOD*)>
# <!ATTLIST CLASS
# 	%CIMName; 
# 	%SuperClass; 
# >

# <!ELEMENT INSTANCE (QUALIFIER*, (PROPERTY | PROPERTY.ARRAY |
#                     PROPERTY.REFERENCE)*)>
# <!ATTLIST INSTANCE
# 	%ClassName;
#         xml:lang   NMTOKEN      #IMPLIED 
# >

def parse_instance(parser, event, node):

    classname = get_required_attribute(node, 'CLASSNAME')

    properties = []
    qualifiers = []

    (next_event, next_node) = parser.next()

    if is_start(next_event, next_node, 'QUALIFIER'):

        qualifiers.append(parse_qualifier(parser, next_event, next_node))

        while 1:

            (next_event, next_node) = parser.next()

            if is_start(next_event, next_node, 'PROPERTY') or \
               is_start(next_event, next_node, 'PROPERTY.ARRAY') or \
               is_start(next_event, next_node, 'PROPERTY.REFERENCE') or \
               is_end(next_event, next_node, 'INSTANCE'):
                break
        
            if is_start(next_event, next_node, 'QUALIFIER'):
                qualifiers.append(
                    parse_qualifier(parser, next_event, next_node))
            else:
                raise ParseError('Expecting QUALIFIER')

    while 1:

        if is_end(next_event, next_node, 'INSTANCE'):
            break

        if is_start(next_event, next_node, 'PROPERTY'):
            properties.append(parse_property(parser, next_event, next_node))

        elif is_start(next_event, next_node, 'PROPERTY.ARRAY'):
            properties.append(
                parse_property_array(parser, next_event, next_node))

        elif is_start(next_event, next_node, 'PROPERTY.REFERENCE'):
            properties.append(
                parse_property_reference(parser, next_event, next_node))
        else:
            raise ParseError(
                'Expecting (PROPERTY | PROPERTY.ARRAY | PROPERTY.REFERENCE)')

        (next_event, next_node) = parser.next()

    if not is_end(next_event, next_node, 'INSTANCE'):
        raise ParseError('Expecting end INSTANCE')

    return CIMInstance(classname,
                       properties = dict([(x.name,  x) for x in properties]),
                       qualifiers = dict([(x.name, x) for x in qualifiers]))
                       
        
# <!ELEMENT QUALIFIER ((VALUE | VALUE.ARRAY)?)>
# <!ATTLIST QUALIFIER 
#          %CIMName;
#          %CIMType;              #REQUIRED
#          %Propagated;
#          %QualifierFlavor;
#          xml:lang   NMTOKEN     #IMPLIED 
# >

def parse_qualifier(parser, event, node):

    name = get_required_attribute(node, 'NAME')
    type = get_required_attribute(node, 'TYPE')
    propagated = get_attribute(node, 'PROPAGATED')

    (next_event, next_node) = parser.next()

    if is_end(next_event, next_node, 'QUALIFIER'):
        return CIMQualifier(name, None, type = type)

    if is_start(next_event, next_node, 'VALUE'):
        value = parse_value(parser, next_event, next_node)
    elif is_start(next_event, next_node, 'VALUE.ARRAY'):
        value = parse_value_array(parser, next_event, next_node)
    else:
        raise ParseError('Expecting (VALUE | VALUE.ARRAY)')

    result = CIMQualifier(name, tocimobj(type, value))

    get_end_event(parser, 'QUALIFIER')

    return result

# <!ELEMENT PROPERTY (QUALIFIER*, VALUE?)>
# <!ATTLIST PROPERTY 
#          %CIMName;
#          %ClassOrigin;
#          %Propagated;
#          %CIMType;              #REQUIRED
#          xml:lang   NMTOKEN     #IMPLIED 
# >

def parse_property(parser, event, node):
 
    name = get_required_attribute(node, 'NAME')
    type = get_required_attribute(node, 'TYPE')

    class_origin = get_attribute(node, 'CLASSORIGIN')
    propagated = get_attribute(node, 'PROPAGATED')

    qualifiers = []
    value = None

    (next_event, next_node) = parser.next()

    if is_start(next_event, next_node, 'QUALIFIER'):

        qualifiers.append(parse_qualifier(parser, next_event, next_node))

        while 1:

            (next_event, next_node) = parser.next()

            if is_start(next_event, next_node, 'VALUE'):
                break

            if is_start(next_event, next_node, 'QUALIFIER'):
                qualifiers.append(
                    parse_qualifier(parser, next_event, next_node))
            else:
                raise ParseError('Expecting QUALIFIER')

    if is_start(next_event, next_node, 'VALUE'):

        value = parse_value(parser, next_event, next_node)
        (next_event, next_node) = parser.next()

    if not is_end(next_event, next_node, 'PROPERTY'):
        raise ParseError('Expecting end PROPERTY')

    return CIMProperty(name,
                       tocimobj(type, value),
                       type = type,
                       class_origin = class_origin,
                       propagated = propagated,
                       qualifiers = dict([(x.name, x) for x in qualifiers]))

# <!ELEMENT PROPERTY.ARRAY (QUALIFIER*, VALUE.ARRAY?)>
# <!ATTLIST PROPERTY.ARRAY 
#          %CIMName;
#          %CIMType;              #REQUIRED
#          %ArraySize;
#          %ClassOrigin;
#          %Propagated;
#          xml:lang   NMTOKEN     #IMPLIED 
# >

def parse_property_array(parser, event, node):
 
    name = get_required_attribute(node, 'NAME')
    type = get_required_attribute(node, 'TYPE')

    array_size = get_attribute(node, 'ARRAYSIZE')
    class_origin = get_attribute(node, 'CLASSORIGIN')
    propagated = get_attribute(node, 'PROPAGATED')

    qualifiers = []
    value = None

    (next_event, next_node) = parser.next()

    if is_start(next_event, next_node, 'QUALIFIER'):

        qualifiers.append(parse_qualifier(parser, next_event, next_node))

        while 1:

            (next_event, next_node) = parser.next()

            if is_start(next_event, next_node, 'VALUE.ARRAY'):
                break

            if is_start(next_event, next_node, 'QUALIFIER'):
                qualifiers.append(
                    parse_qualifier(parser, next_event, next_node))
            else:
                raise ParseError('Expecting QUALIFIER')

    if is_start(next_event, next_node, 'VALUE.ARRAY'):

        value = parse_value_array(parser, next_event, next_node)
        (next_event, next_node) = parser.next()

    if not is_end(next_event, next_node, 'PROPERTY.ARRAY'):
        raise ParseError('Expecting end PROPERTY.ARRAY')

    return CIMProperty(name,
                       tocimobj(type, value),
                       type = type,
                       class_origin = class_origin,
                       propagated = propagated,
                       is_array = True,
                       qualifiers = dict([(x.name, x) for x in qualifiers]))
    
# <!ELEMENT PROPERTY.REFERENCE (QUALIFIER*, (VALUE.REFERENCE)?)>
# <!ATTLIST PROPERTY.REFERENCE
# 	%CIMName; 
# 	%ReferenceClass; 
# 	%ClassOrigin; 
# 	%Propagated; 
# >

def parse_property_reference(parser, event, node):

    name = get_required_attribute(node, 'NAME')

    class_origin = get_attribute(node, 'CLASSORIGIN')
    propagated = get_attribute(node, 'PROPAGATED')

    qualifiers = []
    value = None

    (next_event, next_node) = parser.next()

    if is_start(next_event, next_node, 'QUALIFIER'):

        qualifiers.append(parse_qualifier(parser, next_event, next_node))

        while 1:

            (next_event, next_node) = parser.next()

            if is_start(next_event, next_node, 'VALUE.REFERENCE'):
                break

            if is_start(next_event, next_node, 'QUALIFIER'):
                qualifiers.append(
                    parse_qualifier(parser, next_event, next_node))

            else:
                raise ParseError('Expecting QUALIFIER')

    if is_start(next_event, next_node, 'VALUE.REFERENCE'):

        value = parse_value_reference(parser, next_event, next_node)
        (next_event, next_node) = parser.next()

    if not is_end(next_event, next_node, 'PROPERTY.REFERENCE'):
        raise ParseError('Expecting end PROPERTY.REFERENCE')

    return CIMProperty(name,
                       value,
                       class_origin = class_origin,
                       propagated = propagated,
                       type = 'reference',
                       qualifiers = dict([(x.name, x) for x in qualifiers]))

# <!ELEMENT METHOD (QUALIFIER*, (PARAMETER | PARAMETER.REFERENCE | PARAMETER.ARRAY | PARAMETER.REFARRAY)*)>
# <!ATTLIST METHOD 
#          %CIMName;
#          %CIMType;              #IMPLIED
#          %ClassOrigin;
#          %Propagated;>
# <!ELEMENT PARAMETER (QUALIFIER*)>
# <!ATTLIST PARAMETER 
#          %CIMName;
#          %CIMType;              #REQUIRED>

# <!ELEMENT PARAMETER.REFERENCE (QUALIFIER*)>
# <!ATTLIST PARAMETER.REFERENCE
# 	%CIMName; 
# 	%ReferenceClass; 
# >

# <!ELEMENT PARAMETER.ARRAY (QUALIFIER*)>
# <!ATTLIST PARAMETER.ARRAY 
#          %CIMName;
#          %CIMType;              #REQUIRED
#          %ArraySize;>

# <!ELEMENT PARAMETER.REFARRAY (QUALIFIER*)>
# <!ATTLIST PARAMETER.REFARRAY
# 	%CIMName; 
# 	%ReferenceClass; 
# 	%ArraySize; 
# >

# <!ELEMENT TABLECELL.DECLARATION EMPTY> 
# <!ATTLIST TABLECELL.DECLARATION
#      %CIMName;
#      %CIMType;   	#REQUIRED
#      ISARRAY           (true|false) "false"
#      %ArraySize;
#      CELLPOS  		CDATA       #REQUIRED
#      SORTPOS     	CDATA       #IMPLIED
#      SORTDIR            (ASC|DESC)  #IMPLIED
# >

# <!ELEMENT TABLECELL.REFERENCE EMPTY> 
# <!ATTLIST TABLECELL.REFERENCE
#      %CIMName;
#      %ReferenceClass;	
#      ISARRAY        (true|false) "false"
#      %ArraySize; 
#      CELLPOS          CDATA       #REQUIRED
#      SORTPOS          CDATA       #IMPLIED
#      SORTDIR         (ASC|DESC)   #IMPLIED
# >

# <!ELEMENT TABLEROW.DECLARATION ( TABLECELL.DECLARATION | TABLECELL.REFERENCE)*>

# <!ELEMENT TABLE (TABLEROW.DECLARATION,(TABLEROW)*)>

# <!ELEMENT TABLEROW ( VALUE | VALUE.ARRAY | VALUE.REFERENCE | VALUE.REFARRAY | VALUE.NULL)*>
 
# <!-- ************************************************** -->
# <!-- Message elements                                   -->
# <!-- ************************************************** -->

# <!ELEMENT MESSAGE (SIMPLEREQ | MULTIREQ | SIMPLERSP | MULTIRSP | SIMPLEEXPREQ | MULTIEXPREQ | SIMPLEEXPRSP | MULTIEXPRSP)>
# <!ATTLIST MESSAGE
# 	ID CDATA #REQUIRED
# 	PROTOCOLVERSION CDATA #REQUIRED
# >

# <!ELEMENT MULTIREQ (SIMPLEREQ, SIMPLEREQ+)>

# <!ELEMENT MULTIEXPREQ (SIMPLEEXPREQ, SIMPLEEXPREQ+)>

# <!ELEMENT SIMPLEREQ (IMETHODCALL | METHODCALL)>

# <!ELEMENT SIMPLEEXPREQ (EXPMETHODCALL)>

# <!ELEMENT IMETHODCALL (LOCALNAMESPACEPATH, IPARAMVALUE*, RESPONSEDESTINATION?)>
# <!ATTLIST IMETHODCALL
# 	%CIMName; 
# >

# <!ELEMENT METHODCALL ((LOCALINSTANCEPATH | LOCALCLASSPATH), PARAMVALUE*, RESPONSEDESTINATION?)>
# <!ATTLIST METHODCALL
# 	%CIMName; 
# >

# <!ELEMENT EXPMETHODCALL (EXPPARAMVALUE*)>
# <!ATTLIST EXPMETHODCALL
# 	%CIMName; 
# >

# <!ELEMENT PARAMVALUE (VALUE | VALUE.REFERENCE | VALUE.ARRAY | VALUE.REFARRAY)?>
# <!ATTLIST PARAMVALUE
# 	%CIMName; 
#         %ParamType;  #IMPLIED
# >

# <!ELEMENT IPARAMVALUE (VALUE | VALUE.ARRAY | VALUE.REFERENCE | INSTANCENAME | CLASSNAME | QUALIFIER.DECLARATION | CLASS | INSTANCE | VALUE.NAMEDINSTANCE)?>
# <!ATTLIST IPARAMVALUE
# 	%CIMName; 
# >

# <!ELEMENT EXPPARAMVALUE (INSTANCE?|VALUE?|METHODRESPONSE?|IMETHODRESPONSE?)>
# <!ATTLIST EXPPARAMVALUE
# 	%CIMName; 
# >

# <!ELEMENT MULTIRSP (SIMPLERSP, SIMPLERSP+)>

# <!ELEMENT MULTIEXPRSP (SIMPLEEXPRSP, SIMPLEEXPRSP+)>

# <!ELEMENT SIMPLERSP (METHODRESPONSE | IMETHODRESPONSE | SIMPLEREQACK)>

# <!ELEMENT SIMPLEEXPRSP (EXPMETHODRESPONSE)>

# <!ELEMENT METHODRESPONSE (ERROR|(RETURNVALUE?,PARAMVALUE*))>
# <!ATTLIST METHODRESPONSE
# 	%CIMName; 
# >

# <!ELEMENT EXPMETHODRESPONSE (ERROR|IRETURNVALUE?)>
# <!ATTLIST EXPMETHODRESPONSE
# 	%CIMName; 
# >

# <!ELEMENT IMETHODRESPONSE (ERROR|IRETURNVALUE?)>
# <!ATTLIST IMETHODRESPONSE
# 	%CIMName; 
# >

# <!ELEMENT ERROR (INSTANCE*)>
# <!ATTLIST ERROR
# 	CODE CDATA #REQUIRED
# 	DESCRIPTION CDATA #IMPLIED
# >

# <!ELEMENT RETURNVALUE (VALUE | VALUE.REFERENCE)>
# <!ATTLIST RETURNVALUE
# 	%ParamType;       #IMPLIED 
# >

# <!ELEMENT IRETURNVALUE (CLASSNAME* | INSTANCENAME* | VALUE* | VALUE.OBJECTWITHPATH* | VALUE.OBJECTWITHLOCALPATH* | VALUE.OBJECT* | OBJECTPATH* | QUALIFIER.DECLARATION* | VALUE.ARRAY? | VALUE.REFERENCE? | CLASS* | INSTANCE* | VALUE.NAMEDINSTANCE*)>

# <!ELEMENT RESPONSEDESTINATION (INSTANCE)> 

# <!ELEMENT SIMPLEREQACK (ERROR?)> 
# <!ATTLIST SIMPLEREQACK  
#          INSTANCEID CDATA     #REQUIRED
# > 

def make_parser(stream_or_string):
    """Create a xml.dom.pulldom parser."""
    
    if type(stream_or_string) == str or type(stream_or_string) == unicode:

        # XXX: the pulldom.parseString() function doesn't seem to
        # like operating on unicode strings!
        
        return parseString(str(stream_or_string))
        
    else:

        return parse(stream_or_string)

def parse_any(stream_or_string):
    """Parse any XML string or stream."""
    
    parser = make_parser(stream_or_string)

    (event, node) = parser.next()

    if event != START_DOCUMENT:
        raise ParseError('Expecting document start')

    (event, node) = parser.next()

    if event != START_ELEMENT:
        raise ParseError('Expecting element start')

    fn_name = 'parse_%s' % node.tagName.lower().replace('.', '_')
    fn = globals().get(fn_name)
    if fn is None:
        raise ParseError('No parser for element %s' % node.tagName)
    
    return fn(parser, event, node)

# Test harness

if __name__ == '__main__':
    import sys
    print parse_any(sys.stdin)
