#!/bin/env python
#
# (C) Copyright 2006,2007 Hewlett-Packard Development Company, L.P.
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
# Author: Tim Potter <tpot@hp.com>
# Author: Ross Peoples <ross.peoples@gmail.com>
#

"""CIM/XML Parser. Parses the CIM/XML Elements defined in the DMTF
   specification DSP0201.

   WARNING: Many of the parsing functions defined in this file must
   keep the exact name (i.e. those prepended by parse_) since the
   parser uses the names to call the function from the parse_any(...)
   function substituting _ for the "." in the element names.

   These functions raise ParseError exception if there are any
   errors in the parsing and terminate the parsing.
"""
from __future__ import print_function
from xml.dom import pulldom
import sys
import six

from .cim_obj import CIMInstance, CIMInstanceName, CIMQualifier, \
                     CIMProperty, tocimobj
from .tupleparse import ParseError

__all__ = []

#class ParseError(Exception):
#    """This exception is raised when there is a validation error detected
#    by the parser."""
#    pass

#
# Helper functions
#

def _get_required_attribute(node, attr):
    """Return an attribute by name.  Raise ParseError if not present."""

    if not node.hasAttribute(attr):
        raise ParseError(
            'Expecting %s attribute in element %s' % (attr, node.tagName))

    return node.getAttribute(attr)

def _get_attribute(node, attr):
    """Return an attribute by name, or None if not present."""

    if node.hasAttribute(attr):
        return node.getAttribute(attr)

    return None

def _get_end_event(parser, tagName):
    """Check that the next event is the end of a particular XML tag."""

    (event, node) = six.next(parser)

    if event != pulldom.END_ELEMENT or node.tagName != tagName:
        raise ParseError(
            'Expecting %s end tag, got %s %s' % (tagName, event, node.tagName))

def _is_start(event, node, tagName):  # pylint: disable=invalid-name
    """Return true if (event, node) is a start event for tagname."""

    return event == pulldom.START_ELEMENT and node.tagName == tagName

def _is_end(event, node, tagName): # pylint: disable=invalid-name
    """Return true if (event, node) is an end event for tagname."""

    return event == pulldom.END_ELEMENT and node.tagName == tagName

# <!-- ************************************************** -->
# <!-- Root element                                       -->
# <!-- ************************************************** -->

# <!ELEMENT CIM (MESSAGE | DECLARATION)>
# <!ATTLIST CIM
#       CIMVERSION CDATA #REQUIRED
#       DTDVERSION CDATA #REQUIRED
# >

# <!-- ************************************************** -->
# <!-- Object declaration elements                        -->
# <!-- ************************************************** -->

# <!ELEMENT DECLARATION (DECLGROUP | DECLGROUP.WITHNAME | DECLGROUP.WITHPATH)+>
# <!ELEMENT DECLGROUP ((LOCALNAMESPACEPATH | NAMESPACEPATH)?,
#                      QUALIFIER.DECLARATION*, VALUE.OBJECT*)>
# <!ELEMENT DECLGROUP.WITHNAME ((LOCALNAMESPACEPATH | NAMESPACEPATH)?,
#                               QUALIFIER.DECLARATION*, VALUE.NAMEDOBJECT*)>
# <!ELEMENT DECLGROUP.WITHPATH (VALUE.OBJECTWITHPATH |
#                               VALUE.OBJECTWITHLOCALPATH)*>
# <!ELEMENT QUALIFIER.DECLARATION (SCOPE?, (VALUE | VALUE.ARRAY)?)>
# <!ATTLIST QUALIFIER.DECLARATION
#       %CIMName;
#       %CIMType;                #REQUIRED
#       ISARRAY     (true|false) #IMPLIED
#       %ArraySize;
#       %QualifierFlavor;
# >
# <!ELEMENT SCOPE EMPTY>
# <!ATTLIST SCOPE
#       CLASS       (true | false) "false"
#       ASSOCIATION (true | false) "false"
#       REFERENCE   (true | false) "false"
#       PROPERTY    (true | false) "false"
#       METHOD      (true | false) "false"
#       PARAMETER   (true | false) "false"
#       INDICATION  (true | false) "false"
# >

# <!-- ************************************************** -->
# <!-- Object Value elements                              -->
# <!-- ************************************************** -->

# <!ELEMENT VALUE (#PCDATA)>

def parse_value(parser, event, node): # pylint: disable=unused-argument
    """ Parse CIM/XML VALUE element and return the value"""
    value = ''

    (next_event, next_node) = six.next(parser)

    if next_event == pulldom.CHARACTERS:

        value = next_node.nodeValue

        (next_event, next_node) = six.next(parser)

    if not _is_end(next_event, next_node, 'VALUE'):
        raise ParseError('Expecting end VALUE')

    return value

# <!ELEMENT VALUE.ARRAY (VALUE*)>

def parse_value_array(parser, event, node): #pylint: disable=unused-argument
    # pylint: disable=invalid-name
    """ Parse CIM/XML VALUE.ARRAY element and return the value array"""

    value_array = []

    (next_event, next_node) = six.next(parser)

    if _is_start(next_event, next_node, 'VALUE'):

        value_array.append(parse_value(parser, next_event, next_node))

        while 1:

            (next_event, next_node) = six.next(parser)

            if _is_end(next_event, next_node, 'VALUE.ARRAY'):
                break

            if _is_start(next_event, next_node, 'VALUE'):
                value_array.append(parse_value(parser, next_event, next_node))
            else:
                raise ParseError('Expecting VALUE element')

    return value_array

# <!ELEMENT VALUE.REFERENCE (CLASSPATH | LOCALCLASSPATH | CLASSNAME |
#                            INSTANCEPATH | LOCALINSTANCEPATH |
#                            INSTANCENAME)>

def parse_value_reference(parser, event, node): #pylint: disable=unused-argument

    """Parse CIM/XML VALUE.REFERENCE element and call function
       for the child ELEMENT. Return the result of that element
       parser call.
    """

    (next_event, next_node) = six.next(parser)

    # TODO 2/16 KS: Functions below do not exist: i.e. class stuff broken:
    #               parse_classpath, parse_localclasspath, parse_classname.

    if _is_start(next_event, next_node, 'CLASSPATH'):
        result = parse_classpath(parser, next_event, next_node)

    elif _is_start(next_event, next_node, 'LOCALCLASSPATH'):
        result = parse_localclasspath(parser, next_event, next_node)

    elif _is_start(next_event, next_node, 'CLASSNAME'):
        result = parse_classname(parser, next_event, next_node)

    elif _is_start(next_event, next_node, 'INSTANCEPATH'):
        result = parse_instancepath(parser, next_event, next_node)

    elif _is_start(next_event, next_node, 'LOCALINSTANCEPATH'):
        result = parse_localinstancepath(parser, next_event, next_node)

    elif _is_start(next_event, next_node, 'INSTANCENAME'):
        result = parse_instancename(parser, next_event, next_node)

    else:
        raise ParseError('Expecting (CLASSPATH | LOCALCLASSPATH | CLASSNAME '
                         '| INSTANCEPATH | LOCALINSTANCEPATH | INSTANCENAME)')

    _get_end_event(parser, 'VALUE.REFERENCE')

    return result

# <!ELEMENT VALUE.REFARRAY (VALUE.REFERENCE*)>
# <!ELEMENT VALUE.OBJECT (CLASS | INSTANCE)>
# <!ELEMENT VALUE.NAMEDINSTANCE (INSTANCENAME, INSTANCE)>
# <!ELEMENT VALUE.NAMEDOBJECT (CLASS | (INSTANCENAME, INSTANCE))>
# <!ELEMENT VALUE.OBJECTWITHLOCALPATH ((LOCALCLASSPATH, CLASS) |
#                                      (LOCALINSTANCEPATH, INSTANCE))>
# <!ELEMENT VALUE.OBJECTWITHPATH ((CLASSPATH, CLASS) |
#                                 (INSTANCEPATH, INSTANCE))>
# <!ELEMENT VALUE.NULL EMPTY>

# <!-- ************************************************** -->
# <!-- Object naming and locating elements                -->
# <!-- ************************************************** -->

def parse_namespacepath(parser, event, node): #pylint: disable=unused-argument
    """Parse namespace path element and return tuple of
       host and namespace
           <!ELEMENT NAMESPACEPATH (HOST, LOCALNAMESPACEPATH)>
    """


    (next_event, next_node) = six.next(parser)

    if not _is_start(next_event, next_node, 'HOST'):
        raise ParseError('Expecting HOST')

    host = parse_host(parser, next_event, next_node)

    (next_event, next_node) = six.next(parser)

    if not _is_start(next_event, next_node, 'LOCALNAMESPACEPATH'):
        raise ParseError('Expecting LOCALNAMESPACEPATH')

    namespacepath = parse_localnamespacepath(parser, next_event, next_node)

    (next_event, next_node) = six.next(parser)

    if not _is_end(next_event, next_node, 'NAMESPACEPATH'):
        raise ParseError('Expecting end NAMESPACEPATH')

    return (host, namespacepath)


def parse_localnamespacepath(parser, event, node):
    #pylint: disable=unused-argument
    """Parse LOCALNAMESPACEPATH for Namespace. Return assembled namespace
            <!ELEMENT LOCALNAMESPACEPATH (NAMESPACE+)>
    """

    (next_event, next_node) = six.next(parser)

    namespaces = []

    if not _is_start(next_event, next_node, 'NAMESPACE'):
        print(next_event, next_node)
        raise ParseError('Expecting NAMESPACE')

    namespaces.append(parse_namespace(parser, next_event, next_node))

    while 1:

        (next_event, next_node) = six.next(parser)

        if _is_end(next_event, next_node, 'LOCALNAMESPACEPATH'):
            break

        if _is_start(next_event, next_node, 'NAMESPACE'):
            namespaces.append(parse_namespace(parser, next_event, next_node))
        else:
            raise ParseError('Expecting NAMESPACE')

    return '/'.join(namespaces)


def parse_host(parser, event, node):
    """Parse and return the host entity if that is the next entity
           <!ELEMENT HOST (#PCDATA)>
    """
    #pylint: disable=unused-argument

    host = ''

    (next_event, next_node) = six.next(parser)

    if next_event == pulldom.CHARACTERS:

        host = next_node.nodeValue

        (next_event, next_node) = six.next(parser)

    if not _is_end(next_event, next_node, 'HOST'):
        raise ParseError('Expecting end HOST')

    return host


def parse_namespace(parser, event, node):
    #pylint: disable=unused-argument
    """Parse the CIM/XML NAMESPACE element and return the value
       of the CIMName attribute
           <!ELEMENT NAMESPACE EMPTY>
           <!ATTLIST NAMESPACE
                 %CIMName;
    """
    name = _get_required_attribute(node, 'NAME')

    (next_event, next_node) = six.next(parser)

    if not _is_end(next_event, next_node, 'NAMESPACE'):
        raise ParseError('Expecting end NAMESPACE')

    return name

# <!ELEMENT CLASSPATH (NAMESPACEPATH, CLASSNAME)>

# <!ELEMENT LOCALCLASSPATH (LOCALNAMESPACEPATH, CLASSNAME)>

# <!ELEMENT CLASSNAME EMPTY>
# <!ATTLIST CLASSNAME
#       %CIMName;
# >

# TODO 3/16 KS: MUST implement CLASSPATH, etc.

def parse_instancepath(parser, event, node):
    #pylint: disable=unused-argument
    """Parse the CIM/XML INSTANCEPATH element and return an
       instancname

       <!ELEMENT INSTANCEPATH (NAMESPACEPATH, INSTANCENAME)>
    """

    (next_event, next_node) = six.next(parser)

    if not _is_start(next_event, next_node, 'NAMESPACEPATH'):
        raise ParseError('Expecting NAMESPACEPATH')

    host, namespacepath = parse_namespacepath(parser, next_event, next_node)

    (next_event, next_node) = six.next(parser)

    if not _is_start(next_event, next_node, 'INSTANCENAME'):
        print(next_event, next_node)
        raise ParseError('Expecting INSTANCENAME')

    instancename = parse_instancename(parser, next_event, next_node)

    instancename.host = host
    instancename.namespace = namespacepath

    return instancename


def parse_localinstancepath(parser, event, node):
    """Parse LOCALINSTANCEPATH element returning instancename
           <!ELEMENT LOCALINSTANCEPATH (LOCALNAMESPACEPATH, INSTANCENAME)>
    """

    #pylint: disable=unused-argument

    (next_event, next_node) = six.next(parser)

    if not _is_start(next_event, next_node, 'LOCALNAMESPACEPATH'):
        raise ParseError('Expecting LOCALNAMESPACEPATH')

    namespacepath = parse_localnamespacepath(parser, next_event, next_node)

    (next_event, next_node) = six.next(parser)

    if not _is_start(next_event, next_node, 'INSTANCENAME'):
        raise ParseError('Expecting INSTANCENAME')

    instancename = parse_instancename(parser, next_event, next_node)

    instancename.namespace = namespacepath

    return instancename


def parse_instancename(parser, event, node): #pylint: disable=unused-argument
    """Parse INSTANCENAME element returning CIMInstancename containing
       classname and keybindings
            <!ELEMENT INSTANCENAME (KEYBINDING* | KEYVALUE? | VALUE.REFERENCE?)>
            <!ATTLIST INSTANCENAME
                  %ClassName;
            >
    """

    classname = _get_required_attribute(node, 'CLASSNAME')
    keybindings = []

    (next_event, next_node) = six.next(parser)

    if _is_start(next_event, next_node, 'KEYBINDING'):

        keybindings.append(parse_keybinding(parser, next_event, next_node))

        while 1:

            (next_event, next_node) = six.next(parser)

            if _is_end(next_event, next_node, 'INSTANCENAME'):
                break

            if _is_start(next_event, next_node, 'KEYBINDING'):
                keybindings.append(
                    parse_keybinding(parser, next_event, next_node))
            else:
                raise ParseError('Expecting KEYBINDING element')

    if _is_end(next_event, next_node, 'INSTANCENAME'):
        pass

    elif _is_start(next_event, next_node, 'KEYVALUE'):
        keybindings.append(('', parse_keyvalue(parser, next_event, next_node)))

    elif _is_start(next_event, next_node, 'VALUE.REFERENCE'):
        keybindings.append(
            parse_value_reference(parser, next_event, next_node))

    else:
        raise ParseError(
            'Expecting KEYBINDING* | KEYVALUE? | VALUE.REFERENCE')

    return CIMInstanceName(classname, keybindings)

# <!ELEMENT OBJECTPATH (INSTANCEPATH | CLASSPATH)>

# <!ELEMENT KEYBINDING (KEYVALUE | VALUE.REFERENCE)>
# <!ATTLIST KEYBINDING
#       %CIMName;
# >

def parse_keybinding(parser, event, node): #pylint: disable=unused-argument
    """Parse CIM/XML KEYBINDING element returning name, value tuple"""

    name = _get_required_attribute(node, 'NAME')

    (next_event, next_node) = six.next(parser)

    if _is_start(next_event, next_node, 'KEYVALUE'):
        keyvalue = parse_keyvalue(parser, next_event, next_node)
        result = (name, keyvalue)

    elif _is_start(next_event, next_node, 'VALUE.REFERENCE'):
        value_reference = parse_value_reference(parser,
                                                next_event, next_node)
        result = (name, value_reference)

    else:
        raise ParseError('Expecting KEYVALUE or VALUE.REFERENCE element')

    _get_end_event(parser, 'KEYBINDING')

    return result

# <!ELEMENT KEYVALUE (#PCDATA)>
# <!ATTLIST KEYVALUE
#       VALUETYPE (string | boolean | numeric) "string"
#       %CIMType;              #IMPLIED
# >

def parse_keyvalue(parser, event, node): #pylint: disable=unused-argument
    """Parse CIM/CML KEYVALUE element and return key value based on
       VALUETYPE  or TYPE (future) information
    """

    valuetype = _get_required_attribute(node, 'VALUETYPE')

    # TODO 2/16 KS: Type attribute not used. Extend to use. Type  was late
    #               extension to spec to allow real types.
    cim_type = _get_attribute(node, 'TYPE')  # pylint: disable=unused-variable

    (next_event, next_node) = six.next(parser)

    if next_event != pulldom.CHARACTERS:
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
            raise ParseError('invalid boolean value %r' % p)

    elif valuetype == 'numeric':

        try:

            # XXX: Use TYPE attribute to create named CIM type.
            # if 'TYPE' in attrs(tt):
            #    return tocimobj(attrs(tt)['TYPE'], p.strip())

            # XXX: Would like to use long() here, but that tends to cause
            # trouble when it's written back out as '2L'
            # pylint: disable=redefined-variable-type
            # Redefined from bool to int
            # pylint: disable=redefined-variable-type
            value = int(value.strip(), 0)

        except ValueError:
            raise ParseError(
                'invalid numeric value "%s"' % value)

    else:
        raise ParseError('Invalid VALUETYPE')

    _get_end_event(parser, 'KEYVALUE')

    return value

# <!-- ************************************************** -->
# <!-- Object definition elements                         -->
# <!-- ************************************************** -->

# <!ELEMENT CLASS (QUALIFIER*, (PROPERTY | PROPERTY.ARRAY |
#                  PROPERTY.REFERENCE)*, METHOD*)>
# <!ATTLIST CLASS
#       %CIMName;
#       %SuperClass;
# >

# <!ELEMENT INSTANCE (QUALIFIER*, (PROPERTY | PROPERTY.ARRAY |
#                     PROPERTY.REFERENCE)*)>
# <!ATTLIST INSTANCE
#       %ClassName;
#       xml:lang   NMTOKEN      #IMPLIED
# >

def parse_instance(parser, event, node): #pylint: disable=unused-argument
    """Parse CIM/XML INSTANCE Element and return CIMInstance"""

    classname = _get_required_attribute(node, 'CLASSNAME')

    properties = []
    qualifiers = []

    (next_event, next_node) = six.next(parser)

    if _is_start(next_event, next_node, 'QUALIFIER'):

        qualifiers.append(parse_qualifier(parser, next_event, next_node))

        while 1:

            (next_event, next_node) = six.next(parser)

            if _is_start(next_event, next_node, 'PROPERTY') or \
               _is_start(next_event, next_node, 'PROPERTY.ARRAY') or \
               _is_start(next_event, next_node, 'PROPERTY.REFERENCE') or \
               _is_end(next_event, next_node, 'INSTANCE'):
                break

            if _is_start(next_event, next_node, 'QUALIFIER'):
                qualifiers.append(
                    parse_qualifier(parser, next_event, next_node))
            else:
                raise ParseError('Expecting QUALIFIER')

    while 1:

        if _is_end(next_event, next_node, 'INSTANCE'):
            break

        if _is_start(next_event, next_node, 'PROPERTY'):
            properties.append(parse_property(parser, next_event, next_node))

        elif _is_start(next_event, next_node, 'PROPERTY.ARRAY'):
            properties.append(
                parse_property_array(parser, next_event, next_node))

        elif _is_start(next_event, next_node, 'PROPERTY.REFERENCE'):
            properties.append(
                parse_property_reference(parser, next_event, next_node))
        else:
            raise ParseError(
                'Expecting (PROPERTY | PROPERTY.ARRAY | PROPERTY.REFERENCE)')

        (next_event, next_node) = six.next(parser)

    if not _is_end(next_event, next_node, 'INSTANCE'):
        raise ParseError('Expecting end INSTANCE')

    return CIMInstance(
        classname,
        properties=dict([(x.name, x) for x in properties]),
        qualifiers=dict([(x.name, x) for x in qualifiers]))

# <!ELEMENT QUALIFIER ((VALUE | VALUE.ARRAY)?)>
# <!ATTLIST QUALIFIER
#       %CIMName;
#       %CIMType;              #REQUIRED
#       %Propagated;
#       %QualifierFlavor;
#       xml:lang   NMTOKEN     #IMPLIED
# >

def parse_qualifier(parser, event, node): #pylint: disable=unused-argument
    """Parse CIM/XML QUALIFIER element and return CIMQualifier"""

    name = _get_required_attribute(node, 'NAME')
    cim_type = _get_required_attribute(node, 'TYPE')
    # TODO 2/16 KS: Why is propagated not used?
    propagated = _get_attribute(node, 'PROPAGATED')

    (next_event, next_node) = six.next(parser)

    if _is_end(next_event, next_node, 'QUALIFIER'):
        return CIMQualifier(name, None, type=cim_type)

    if _is_start(next_event, next_node, 'VALUE'):
        value = parse_value(parser, next_event, next_node)
    elif _is_start(next_event, next_node, 'VALUE.ARRAY'):
        #pylint: disable=redefined-variable-type
        # redefined from str to list.
        value = parse_value_array(parser, next_event, next_node)
    else:
        raise ParseError('Expecting (VALUE | VALUE.ARRAY)')

    result = CIMQualifier(name, tocimobj(cim_type, value))

    _get_end_event(parser, 'QUALIFIER')

    return result

# <!ELEMENT PROPERTY (QUALIFIER*, VALUE?)>
# <!ATTLIST PROPERTY
#       %CIMName;
#       %ClassOrigin;
#       %Propagated;
#       %CIMType;              #REQUIRED
#       xml:lang   NMTOKEN     #IMPLIED
# >

def parse_property(parser, event, node): #pylint: disable=unused-argument
    """Parse CIM/XML PROPERTY Element and return CIMProperty"""

    name = _get_required_attribute(node, 'NAME')
    cim_type = _get_required_attribute(node, 'TYPE')

    class_origin = _get_attribute(node, 'CLASSORIGIN')
    propagated = _get_attribute(node, 'PROPAGATED')

    qualifiers = []
    value = None

    (next_event, next_node) = six.next(parser)

    if _is_start(next_event, next_node, 'QUALIFIER'):

        qualifiers.append(parse_qualifier(parser, next_event, next_node))

        while 1:

            (next_event, next_node) = six.next(parser)

            if _is_start(next_event, next_node, 'VALUE'):
                break

            if _is_start(next_event, next_node, 'QUALIFIER'):
                qualifiers.append(
                    parse_qualifier(parser, next_event, next_node))
            else:
                raise ParseError('Expecting QUALIFIER')

    if _is_start(next_event, next_node, 'VALUE'):

        value = parse_value(parser, next_event, next_node)
        (next_event, next_node) = six.next(parser)

    if not _is_end(next_event, next_node, 'PROPERTY'):
        raise ParseError('Expecting end PROPERTY')

    return CIMProperty(
        name,
        tocimobj(cim_type, value),
        type=cim_type,
        class_origin=class_origin,
        propagated=propagated,
        qualifiers=dict([(x.name, x) for x in qualifiers]))

# <!ELEMENT PROPERTY.ARRAY (QUALIFIER*, VALUE.ARRAY?)>
# <!ATTLIST PROPERTY.ARRAY
#       %CIMName;
#       %CIMType;              #REQUIRED
#       %ArraySize;
#       %ClassOrigin;
#       %Propagated;
#       xml:lang   NMTOKEN     #IMPLIED
# >

def parse_property_array(parser, event, node): #pylint: disable=unused-argument
    """Parse CIM/XML PROPERTY.ARRAY element and return CIMProperty"""

    name = _get_required_attribute(node, 'NAME')
    cim_type = _get_required_attribute(node, 'TYPE')

    # TODO 2/16 KS: array_size here is unused. It is valid attribute.
    array_size = _get_attribute(node, 'ARRAYSIZE')
    class_origin = _get_attribute(node, 'CLASSORIGIN')
    propagated = _get_attribute(node, 'PROPAGATED')

    # TODO 1/16 KS: The qualifier processing could be common.
    qualifiers = []
    value = None

    (next_event, next_node) = six.next(parser)

    if _is_start(next_event, next_node, 'QUALIFIER'):

        qualifiers.append(parse_qualifier(parser, next_event, next_node))

        while 1:

            (next_event, next_node) = six.next(parser)

            if _is_start(next_event, next_node, 'VALUE.ARRAY'):
                break

            if _is_start(next_event, next_node, 'QUALIFIER'):
                qualifiers.append(
                    parse_qualifier(parser, next_event, next_node))
            else:
                raise ParseError('Expecting QUALIFIER')

    if _is_start(next_event, next_node, 'VALUE.ARRAY'):

        value = parse_value_array(parser, next_event, next_node)
        (next_event, next_node) = six.next(parser)

    if not _is_end(next_event, next_node, 'PROPERTY.ARRAY'):
        raise ParseError('Expecting end PROPERTY.ARRAY')

    return CIMProperty(
        name,
        tocimobj(type, value),
        type=cim_type,
        class_origin=class_origin,
        propagated=propagated,
        is_array=True,
        qualifiers=dict([(x.name, x) for x in qualifiers]))

# <!ELEMENT PROPERTY.REFERENCE (QUALIFIER*, (VALUE.REFERENCE)?)>
# <!ATTLIST PROPERTY.REFERENCE
#       %CIMName;
#       %ReferenceClass;
#       %ClassOrigin;
#       %Propagated;
# >

def parse_property_reference(parser, event, node): #pylint: disable=unused-argument
    """Parse CIM/XML PROPERTY.REFERENCE ELEMENT and return
       CIMProperty
    """

    name = _get_required_attribute(node, 'NAME')

    class_origin = _get_attribute(node, 'CLASSORIGIN')
    propagated = _get_attribute(node, 'PROPAGATED')

    qualifiers = []
    value = None

    (next_event, next_node) = six.next(parser)

    if _is_start(next_event, next_node, 'QUALIFIER'):

        qualifiers.append(parse_qualifier(parser, next_event, next_node))

        while 1:

            (next_event, next_node) = six.next(parser)

            if _is_start(next_event, next_node, 'VALUE.REFERENCE'):
                break

            if _is_start(next_event, next_node, 'QUALIFIER'):
                qualifiers.append(
                    parse_qualifier(parser, next_event, next_node))

            else:
                raise ParseError('Expecting QUALIFIER')

    if _is_start(next_event, next_node, 'VALUE.REFERENCE'):

        value = parse_value_reference(parser, next_event, next_node)
        (next_event, next_node) = six.next(parser)

    if not _is_end(next_event, next_node, 'PROPERTY.REFERENCE'):
        raise ParseError('Expecting end PROPERTY.REFERENCE')

    return CIMProperty(
        name,
        value,
        class_origin=class_origin,
        propagated=propagated,
        type='reference',
        qualifiers=dict([(x.name, x) for x in qualifiers]))

# <!ELEMENT METHOD (QUALIFIER*, (PARAMETER | PARAMETER.REFERENCE |
#                   PARAMETER.ARRAY | PARAMETER.REFARRAY)*)>
# <!ATTLIST METHOD
#       %CIMName;
#       %CIMType;              #IMPLIED
#       %ClassOrigin;
#       %Propagated;>

# <!ELEMENT PARAMETER (QUALIFIER*)>
# <!ATTLIST PARAMETER
#       %CIMName;
#       %CIMType;              #REQUIRED>

# <!ELEMENT PARAMETER.REFERENCE (QUALIFIER*)>
# <!ATTLIST PARAMETER.REFERENCE
#       %CIMName;
#       %ReferenceClass;
# >

# <!ELEMENT PARAMETER.ARRAY (QUALIFIER*)>
# <!ATTLIST PARAMETER.ARRAY
#       %CIMName;
#       %CIMType;              #REQUIRED
#       %ArraySize;>

# <!ELEMENT PARAMETER.REFARRAY (QUALIFIER*)>
# <!ATTLIST PARAMETER.REFARRAY
#       %CIMName;
#       %ReferenceClass;
#       %ArraySize;
# >

# <!ELEMENT TABLECELL.DECLARATION EMPTY>
# <!ATTLIST TABLECELL.DECLARATION
#       %CIMName;
#       %CIMType;                               #REQUIRED
#       ISARRAY         (true|false) "false"
#       %ArraySize;
#       CELLPOS         CDATA                   #REQUIRED
#       SORTPOS         CDATA                   #IMPLIED
#       SORTDIR         (ASC|DESC)              #IMPLIED
# >

# <!ELEMENT TABLECELL.REFERENCE EMPTY>
# <!ATTLIST TABLECELL.REFERENCE
#       %CIMName;
#       %ReferenceClass;
#       ISARRAY         (true|false) "false"
#       %ArraySize;
#       CELLPOS         CDATA                   #REQUIRED
#       SORTPOS         CDATA                   #IMPLIED
#       SORTDIR         (ASC|DESC)              #IMPLIED
# >

# <!ELEMENT TABLEROW.DECLARATION (TABLECELL.DECLARATION | TABLECELL.REFERENCE)*>

# <!ELEMENT TABLE (TABLEROW.DECLARATION,(TABLEROW)*)>

# <!ELEMENT TABLEROW (VALUE | VALUE.ARRAY | VALUE.REFERENCE | VALUE.REFARRAY |
#                     VALUE.NULL)*>

# <!-- ************************************************** -->
# <!-- Message elements                                   -->
# <!-- ************************************************** -->

# <!ELEMENT MESSAGE (SIMPLEREQ | MULTIREQ | SIMPLERSP | MULTIRSP |
#                    SIMPLEEXPREQ | MULTIEXPREQ | SIMPLEEXPRSP | MULTIEXPRSP)>
# <!ATTLIST MESSAGE
#       ID              CDATA #REQUIRED
#       PROTOCOLVERSION CDATA #REQUIRED
# >

# <!ELEMENT MULTIREQ (SIMPLEREQ, SIMPLEREQ+)>

# <!ELEMENT MULTIEXPREQ (SIMPLEEXPREQ, SIMPLEEXPREQ+)>

# <!ELEMENT SIMPLEREQ (IMETHODCALL | METHODCALL)>

# <!ELEMENT SIMPLEEXPREQ (EXPMETHODCALL)>

# <!ELEMENT IMETHODCALL (LOCALNAMESPACEPATH, IPARAMVALUE*,
#                        RESPONSEDESTINATION?)>
# <!ATTLIST IMETHODCALL
#       %CIMName;
# >

# <!ELEMENT METHODCALL ((LOCALINSTANCEPATH | LOCALCLASSPATH), PARAMVALUE*,
#                       RESPONSEDESTINATION?)>
# <!ATTLIST METHODCALL
#       %CIMName;
# >

# <!ELEMENT EXPMETHODCALL (EXPPARAMVALUE*)>
# <!ATTLIST EXPMETHODCALL
#       %CIMName;
# >

# <!ELEMENT PARAMVALUE (VALUE | VALUE.REFERENCE | VALUE.ARRAY |
#                       VALUE.REFARRAY)?>
# <!ATTLIST PARAMVALUE
#       %CIMName;
#       %ParamType;  #IMPLIED
# >

# <!ELEMENT IPARAMVALUE (VALUE | VALUE.ARRAY | VALUE.REFERENCE | INSTANCENAME |
#                        CLASSNAME | QUALIFIER.DECLARATION | CLASS | INSTANCE |
#                        VALUE.NAMEDINSTANCE)?>
# <!ATTLIST IPARAMVALUE
#       %CIMName;
# >

# <!ELEMENT EXPPARAMVALUE (INSTANCE? | VALUE? | METHODRESPONSE? |
#                          IMETHODRESPONSE?)>
# <!ATTLIST EXPPARAMVALUE
#       %CIMName;
# >

# <!ELEMENT MULTIRSP (SIMPLERSP, SIMPLERSP+)>

# <!ELEMENT MULTIEXPRSP (SIMPLEEXPRSP, SIMPLEEXPRSP+)>

# <!ELEMENT SIMPLERSP (METHODRESPONSE | IMETHODRESPONSE | SIMPLEREQACK)>

# <!ELEMENT SIMPLEEXPRSP (EXPMETHODRESPONSE)>

# <!ELEMENT METHODRESPONSE (ERROR | (RETURNVALUE?, PARAMVALUE*))>
# <!ATTLIST METHODRESPONSE
#       %CIMName;
# >

# <!ELEMENT EXPMETHODRESPONSE (ERROR | IRETURNVALUE?)>
# <!ATTLIST EXPMETHODRESPONSE
#       %CIMName;
# >

# <!ELEMENT IMETHODRESPONSE (ERROR | IRETURNVALUE?)>
# <!ATTLIST IMETHODRESPONSE
#       %CIMName;
# >

# <!ELEMENT ERROR (INSTANCE*)>
# <!ATTLIST ERROR
#       CODE        CDATA #REQUIRED
#       DESCRIPTION CDATA #IMPLIED
# >

# <!ELEMENT RETURNVALUE (VALUE | VALUE.REFERENCE)>
# <!ATTLIST RETURNVALUE
#       %ParamType;       #IMPLIED
# >

# <!ELEMENT IRETURNVALUE (CLASSNAME* | INSTANCENAME* | VALUE* |
#                         VALUE.OBJECTWITHPATH* | VALUE.OBJECTWITHLOCALPATH* |
#                         VALUE.OBJECT* | OBJECTPATH* | QUALIFIER.DECLARATION* |
#                         VALUE.ARRAY? | VALUE.REFERENCE? | CLASS* | INSTANCE* |
#                         VALUE.NAMEDINSTANCE*)>

# <!ELEMENT RESPONSEDESTINATION (INSTANCE)>

# <!ELEMENT SIMPLEREQACK (ERROR?)>
# <!ATTLIST SIMPLEREQACK
#       INSTANCEID CDATA     #REQUIRED
# >

def make_parser(stream_or_string):
    """Create a xml.dom.pulldom parser."""

    if isinstance(stream_or_string, six.string_types):

        # XXX: the pulldom.parseString() function doesn't seem to
        # like operating on unicode strings!

        return pulldom.parseString(str(stream_or_string))

    else:

        return pulldom.parse(stream_or_string)

def parse_any(stream_or_string):
    """Parse any XML string or stream. This function fabricates
       the names of the parser functions by prepending parse_ to
       the node name and then calling that function.
    """

    parser = make_parser(stream_or_string)

    (event, node) = six.next(parser)

    if event != pulldom.START_DOCUMENT:
        raise ParseError('Expecting document start')

    (event, node) = six.next(parser)

    if event != pulldom.START_ELEMENT:
        raise ParseError('Expecting element start')

    fn_name = 'parse_%s' % node.tagName.lower().replace('.', '_')
    fn = globals().get(fn_name)
    if fn is None:
        raise ParseError('No parser for element %s' % node.tagName)

    return fn(parser, event, node)

# Test harness

if __name__ == '__main__':
    print(parse_any(sys.stdin))
