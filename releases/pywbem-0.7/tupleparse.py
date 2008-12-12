#
# (C) Copyright 2003, 2004 Hewlett-Packard Development Company, L.P.
# (C) Copyright 2006-2007 Novell, Inc. 
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as
# published by the Free Software Foundation; either version 2 of the
# License.
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

# Author: Martin Pool <mbp@hp.com>
#         Tim Potter <tpot@hp.com>
#         Bart Whiteley <bwhiteley@suse.de>

'''Tuple parser for the XML schema representing CIM messages.

This framework is meant to add some value to the tuple-tree
representation of CIM in XML by having the following properties: 

  - Silently ignoring whitespace text elements

  - Conversion from tuple-tree representation into a python dictionary
    which can then be accessed in a readable fashion.

  - Validation of the XML elements and attributes without having to
    use the DTD file or any external tools.

'''

# Implementation: this works by a recursive descent down the CIM XML
# tupletree.  As we walk down, we produce cim_obj and cim_type
# objects representing the CIM message in digested form.

# For each XML node type FOO there is one function parse_foo, which
# returns the digested form by examining a tuple tree rooted at FOO.

# The resulting objects are constrained to the shape of the CIM XML
# tree: if one node in XML contains another, then the corresponding
# CIM object will contain the second.  However, there can be local
# transformations at each node: some levels are ommitted, some are
# transformed into lists or hashes.

# We try to validate that the tree is well-formed too.  The validation
# is more strict than the DTD, but it is forgiving of implementation
# quirks and bugs in Pegasus.

# Bear in mind in the parse functions that each tupletree tuple is
# structured as

#   tt[0]: name string             == name(tt)
#   tt[1]: hash of attributes      == attrs(tt)
#   tt[2]: sequence of children    == kids(tt)

# At the moment this layer is a little inconsistent: in some places it
# returns tupletrees, and in others Python objects.  It may be better
# to hide the tupletree/XML representation from higher level code.


# TODO: Maybe take a DTD fragment like "(DECLGROUP |
# DECLGROUP.WITHNAME | DECLGROUP.WITHPATH)*", parse that and check it
# directly.

# TODO: Syntax-check some attributes with defined formats, such as NAME

# TODO: Implement qualifiers by making subclasses of CIM types with a
# .qualifiers property.

import string, types
import cim_obj
from cim_obj import CIMProperty, byname
from types import StringTypes
from tupletree import xml_to_tupletree

class ParseError(Exception):
    """This exception is raised when there is a validation error detected
    by the parser."""    
    pass


def filter_tuples(l):
    """Return only the tuples in a list.

    In a tupletree, tuples correspond to XML elements.  Useful for
    stripping out whitespace data in a child list."""

    if l is None:
        return []
    else:
        return [x for x in l if type(x) == tuple]


def pcdata(tt):
    """Return the concatenated character data within a tt.

    The tt must not have non-character children."""
    import types
    for x in tt[2]:
        if not isinstance(x, types.StringTypes):
            raise ParseError, 'unexpected node %s under %s' % (`x`, `tt`)
    return ''.join(tt[2])


def name(tt):
    return tt[0]


def attrs(tt):
    return tt[1]


def kids(tt):
    return filter_tuples(tt[2])


def check_node(tt, nodename, required_attrs = [], optional_attrs = [],
               allowed_children = None,
               allow_pcdata = False):
    """Check static local constraints on a single node.

    The node must have the given name.  The required attrs must be
    present, and the optional attrs may be.

    If allowed_children is not None, the node may have children of the
    given types.  It can be [] for nodes that may not have any
    children.  If it's None, it is assumed the children are validated
    in some other way.

    If allow_pcdata is true, then non-whitespace text children are allowed.
    (Whitespace text nodes are always allowed.)
    """
    
    if name(tt) <> nodename:
        raise ParseError('expected node type %s, not %s' %
                         (nodename, name(tt)))

    # Check we have all the required attributes, and no unexpected ones
    tt_attrs = {}
    if attrs(tt) is not None:
        tt_attrs = attrs(tt).copy()

    for attr in required_attrs:
        if not tt_attrs.has_key(attr):
            raise ParseError('expected %s attribute on %s node, but only '
                             'have %s' % (attr, name(tt),attrs(tt).keys()))
        del tt_attrs[attr]

    for attr in optional_attrs:
        if tt_attrs.has_key(attr):
            del tt_attrs[attr]

    if len(tt_attrs.keys()) > 0:
        raise ParseError('invalid extra attributes %s' % tt_attrs.keys())

    if allowed_children is not None:
        for c in kids(tt):
            if name(c) not in allowed_children:
                raise ParseError('unexpected node %s under %s; wanted %s'
                                 % (name(c), name(tt), allowed_children))

    if not allow_pcdata:
        for c in tt[2]:
            if isinstance(c, types.StringTypes):
                if c.lstrip(' \t\n') <> '':
                    raise ParseError('unexpected non-blank pcdata node %s '
                                     'under %s' % (`c`, name(tt)))

    
def one_child(tt, acceptable):
    """Parse children of a node with exactly one child node.

    PCData is ignored.
    """

    k = kids(tt)

    if len(k) <> 1:
        raise ParseError('expecting just one %s, got %s' %
                         (acceptable, [t[0] for t in k]))

    child = k[0]

    if name(child) not in acceptable:
        raise ParseError('expecting one of %s, got %s under %s' %
                         (acceptable, name(child), name(tt)))
    
    return parse_any(child)


def optional_child(tt, allowed):
    """Parse exactly zero or one of a list of elements from the
    child nodes."""

    k = kids(tt)

    if len(k) > 1:
        raise ParseError('expecting zero or one of %s under %s' %
                         (allowed, tt))
    elif len(k) == 1:
        return one_child(tt, allowed)
    else:
        return None


def list_of_various(tt, acceptable):
    """Parse zero or more of a list of elements from the child nodes.

    Each element of the list can be any type from the list of acceptable
    nodes."""

    r = []

    for child in kids(tt):
        if name(child) not in acceptable:
            raise ParseError('expected one of %s under %s, got %s' % 
                             (acceptable, name(tt), `name(child)`))
        r.append(parse_any(child))

    return r


def list_of_matching(tt, matched):
    """Parse only the children of particular types under tt.

    Other children are ignored rather than giving an error."""

    r = []

    for child in kids(tt):
        if name(child) not in matched:
            continue
        r.append(parse_any(child))

    return r


def list_of_same(tt, acceptable):
    """Parse a list of elements from child nodes.

    The children can be any of the listed acceptable types, but they
    must all be the same.
    """

    k = kids(tt)
    if not k:                   # empty list, consistent with list_of_various
        return []
    
    w = name(k[0])
    if w not in acceptable:
        raise ParseError('expected one of %s under %s, got %s' % 
                             (acceptable, name(tt), `w`))
    r = []
    for child in k:
        if name(child) <> w:
            raise ParseError('expected list of %s under %s, but found %s' %
                             (w, name(child), name(tt)))
        r.append(parse_any(child))

    return r


def notimplemented(tt):
    raise ParseError('parser for %s not implemented' % name(tt))
    
#
# Root element
#

def parse_cim(tt):
    """
    <!ELEMENT CIM (MESSAGE | DECLARATION)>
    <!ATTLIST CIM
	CIMVERSION CDATA #REQUIRED
	DTDVERSION CDATA #REQUIRED>
    """

    check_node(tt, 'CIM', ['CIMVERSION', 'DTDVERSION'])
    
    if attrs(tt)['CIMVERSION'] <> '2.0':
        raise ParseError('CIMVERSION is %s, expected 2.0' %
                         attrs(tt)[CIMVERSION])

    child = one_child(tt, ['MESSAGE', 'DECLARATION'])

    return name(tt), attrs(tt), child

#
# Object value elements
#

def parse_value(tt):
    '''Return VALUE contents as a string'''
    ## <!ELEMENT VALUE (#PCDATA)>
    check_node(tt, 'VALUE', [], [], [], True)

    return pcdata(tt)


def parse_value_array(tt):
    """Return list of strings."""
    ## <!ELEMENT VALUE.ARRAY (VALUE*)>
    check_node(tt, 'VALUE.ARRAY', [], [], ['VALUE'])

    return list_of_same(tt, ['VALUE'])
        

def parse_value_reference(tt):
    """
    <!ELEMENT VALUE.REFERENCE (CLASSPATH | LOCALCLASSPATH | CLASSNAME |
                               INSTANCEPATH | LOCALINSTANCEPATH |
                               INSTANCENAME)>
    """

    check_node(tt, 'VALUE.REFERENCE', [])

    child = one_child(tt,
                      ['CLASSPATH', 'LOCALCLASSPATH', 'CLASSNAME',
                       'INSTANCEPATH', 'LOCALINSTANCEPATH',
                       'INSTANCENAME'])
                      
    # The VALUE.REFERENCE wrapper element is discarded
    return child


def parse_value_refarray(tt):
    """
    <!ELEMENT VALUE.REFARRAY (VALUE.REFERENCE*)>
    """
    
    check_node(tt, 'VALUE.REFARRAY')

    children = list_of_various(tt, ['VALUE.REFERENCE'])

    # The VALUE.REFARRAY wrapper element is discarded
    return children


def parse_value_object(tt):
    """
    <!ELEMENT VALUE.OBJECT (CLASS | INSTANCE)>
    """

    check_node(tt, 'VALUE.OBJECT')

    child = one_child(tt, ['CLASS', 'INSTANCE'])

    return (name(tt), attrs(tt), child)


def parse_value_namedinstance(tt):
    """
    <!ELEMENT VALUE.NAMEDINSTANCE (INSTANCENAME, INSTANCE)>
    """

    check_node(tt, 'VALUE.NAMEDINSTANCE')

    k = kids(tt)
    if len(k) <> 2:
        raise ParseError('expecting (INSTANCENAME, INSTANCE), got %s' % `k`)

    instancename = parse_instancename(k[0])
    instance = parse_instance(k[1])        

    instance.path = instancename

    return instance


def parse_value_namedobject(tt):
    """
    <!ELEMENT VALUE.NAMEDOBJECT (CLASS | (INSTANCENAME, INSTANCE))>
    """

    check_node(tt, 'VALUE.NAMEDOBJECT')

    k = kids(tt)
    if len(k) == 1:
        object = parse_class(k[0])
    elif len(k) == 2:
        path = parse_instancename(kids(tt)[0])
        object = parse_instance(kids(tt)[1])

        object.path = path
    else:
        raise ParseError('Expecting one or two elements, got %s' %
                         `kids(tt)`)

    return (name(tt), attrs(tt), object)

    
def parse_value_objectwithlocalpath(tt):
    """
    <!ELEMENT VALUE.OBJECTWITHLOCALPATH ((LOCALCLASSPATH, CLASS) |
                                         (LOCALINSTANCEPATH, INSTANCE))>
    """

    check_node(tt, 'VALUE.OBJECTWITHLOCALPATH')

    if len(kids(tt)) != 2:
        raise ParseError('Expecting two elements, got %s' %
                         len(kids(tt)));

    if kids(tt)[0][0] == 'LOCALCLASSPATH':
        object = (parse_localclasspath(kids(tt)[0]),
                  parse_class(kids(tt)[1]))
    else:
        path = parse_localinstancepath(kids(tt)[0])
        object = parse_instance(kids(tt)[1])

        object.path = path

    return (name(tt), attrs(tt), object)
            
def parse_value_objectwithpath(tt):
    """
    <!ELEMENT VALUE.OBJECTWITHPATH ((CLASSPATH, CLASS) |
                                    (INSTANCEPATH, INSTANCE))>
    """

    check_node(tt, 'VALUE.OBJECTWITHPATH')

    k = kids(tt)

    if len(k) != 2:
        raise ParseError('Expecting two elements, got %s' % k)

    if name(k[0]) == 'CLASSPATH':
        object = (parse_classpath(k[0]),
                  parse_class(k[1]))
    else:
        path = parse_instancepath(k[0])
        object = parse_instance(k[1])

        object.path = path

    return (name(tt), attrs(tt), object)

#
# Object naming and locating elements
#

def parse_namespacepath(tt):
    """
    <!ELEMENT NAMESPACEPATH (HOST, LOCALNAMESPACEPATH)>
    """
    
    check_node(tt, 'NAMESPACEPATH')

    if len(kids(tt)) != 2:
        raise ParseError('Expecting (HOST, LOCALNAMESPACEPATH) '
                         'got %s' % kids(tt).keys())

    host = parse_host(kids(tt)[0])
    localnspath = parse_localnamespacepath(kids(tt)[1])

    return (host, localnspath)


def parse_localnamespacepath(tt):
    """
    <!ELEMENT LOCALNAMESPACEPATH (NAMESPACE+)>
    """

    check_node(tt, 'LOCALNAMESPACEPATH', [], [], ['NAMESPACE'])

    if len(kids(tt)) == 0:
        raise ParseError('Expecting one or more of NAMESPACE, got nothing')

    ns_list = list_of_various(tt, ['NAMESPACE'])

    return string.join(ns_list, '/')


def parse_host(tt):
    """
    <!ELEMENT HOST (#PCDATA)>
    """

    check_node(tt, 'HOST', allow_pcdata=True)

    return pcdata(tt)


def parse_namespace(tt):
    """
    <!ELEMENT NAMESPACE EMPTY>
    <!ATTLIST NAMESPACE
	%CIMName;>
    """

    check_node(tt, 'NAMESPACE', ['NAME'], [], [])

    return attrs(tt)['NAME']


def parse_classpath(tt):
    """
    <!ELEMENT CLASSPATH (NAMESPACEPATH, CLASSNAME)>
    """

    check_node(tt, 'CLASSPATH')

    if len(kids(tt)) != 2:
        raise ParseError('Expecting (NAMESPACEPATH, CLASSNAME) '
                         'got %s' % kids(tt).keys())

    nspath = parse_namespacepath(kids(tt)[0])
    classname = parse_classname(kids(tt)[1])

    return cim_obj.CIMClassName(classname.classname,
                                host = nspath[0], namespace = nspath[1])


def parse_localclasspath(tt):
    """
    <!ELEMENT LOCALCLASSPATH (LOCALNAMESPACEPATH, CLASSNAME)>
    """

    check_node(tt, 'LOCALCLASSPATH')

    if len(kids(tt)) != 2:
        raise ParseError('Expecting (LOCALNAMESPACEPATH, CLASSNAME) '
                         'got %s' % kids(tt).keys())

    localnspath = parse_localnamespacepath(kids(tt)[0])
    classname = parse_classname(kids(tt)[1])

    return cim_obj.CIMClassName(classname.classname, namespace = localnspath)

def parse_classname(tt):
    """
    <!ELEMENT CLASSNAME EMPTY>
    <!ATTLIST CLASSNAME
	%CIMName;>
    """
    check_node(tt, 'CLASSNAME', ['NAME'], [], [])
    return cim_obj.CIMClassName(attrs(tt)['NAME'])


def parse_instancepath(tt):
    """
    <!ELEMENT INSTANCEPATH (NAMESPACEPATH, INSTANCENAME)>
    """

    check_node(tt, 'INSTANCEPATH')

    if len(kids(tt)) != 2:
        raise ParseError('Expecting (NAMESPACEPATH, INSTANCENAME), got %s'
                         % `kids(tt)`)

    nspath = parse_namespacepath(kids(tt)[0])
    instancename = parse_instancename(kids(tt)[1])

    instancename.host = nspath[0]
    instancename.namespace = nspath[1]

    return instancename
    
def parse_localinstancepath(tt):
    """
    <!ELEMENT LOCALINSTANCEPATH (LOCALNAMESPACEPATH, INSTANCENAME)>
    """

    check_node(tt, 'LOCALINSTANCEPATH')

    if len(kids(tt)) != 2:
        raise ParseError('Expecting (LOCALNAMESPACEPATH, INSTANCENAME), '
                         'got %s' % kids(tt).keys())

    localnspath = parse_localnamespacepath(kids(tt)[0])
    instancename = parse_instancename(kids(tt)[1])

    instancename.namespace = localnspath

    return instancename

def parse_instancename(tt):
    """Parse XML INSTANCENAME into CIMInstanceName object."""
    
    ## <!ELEMENT INSTANCENAME (KEYBINDING* | KEYVALUE? | VALUE.REFERENCE?)>
    ## <!ATTLIST INSTANCENAME %ClassName;>

    from cim_obj import CIMInstanceName

    check_node(tt, 'INSTANCENAME', ['CLASSNAME'])

    if len(kids(tt)) == 0:
        # probably not ever going to see this, but it's valid
        # according to the grammar
        return CIMInstanceName(attrs(tt)['CLASSNAME'], {})

    k0 = kids(tt)[0]
    w = name(k0)

    classname = attrs(tt)['CLASSNAME']

    if w == 'KEYVALUE' or w == 'VALUE.REFERENCE':
        if len(kids(tt)) != 1:
            raise ParseError('expected only one %s under %s' %
                             w, name(tt))
        
        # FIXME: This is probably not the best representation of these forms...
        val = parse_any(k0)
        return CIMInstanceName(classname, {None: val})
    elif w == 'KEYBINDING':
        kbs = {}
        for kb in list_of_various(tt, ['KEYBINDING']):
            kbs.update(kb)
        return CIMInstanceName(classname, kbs)        
    else:
        raise ParseError('unexpected node %s under %s' %
                         (name(kids(tt)[0]), name(tt)))


def parse_objectpath(tt):
    """
    <!ELEMENT OBJECTPATH (INSTANCEPATH | CLASSPATH)>
    """

    check_node(tt, 'OBJECTPATH')

    child  = one_child(tt, ['INSTANCEPATH', 'CLASSPATH'])

    return (name(tt), attrs(tt), child)



def parse_keybinding(tt):
    ##<!ELEMENT KEYBINDING (KEYVALUE | VALUE.REFERENCE)>
    ##<!ATTLIST KEYBINDING
    ##	%CIMName;>

    """Returns one-item dictionary from name to Python value."""
    
    check_node(tt, 'KEYBINDING', ['NAME'])

    child = one_child(tt, ['KEYVALUE', 'VALUE.REFERENCE'])

    return {attrs(tt)['NAME']: child}


def parse_keyvalue(tt):
    ##<!ELEMENT KEYVALUE (#PCDATA)>
    ##<!ATTLIST KEYVALUE
    ##          VALUETYPE (string | boolean | numeric) "string"
    ##          %CIMType;              #IMPLIED>


    """Parse VALUETYPE into Python primitive value"""
    
    check_node(tt, 'KEYVALUE', ['VALUETYPE'], ['TYPE'], [], True)

    vt = attrs(tt).get('VALUETYPE')
    
    p = pcdata(tt)
    if vt == 'string':
        return p
    elif vt == 'boolean':
        return unpack_boolean(p)
    elif vt == 'numeric':

        try: 
            # XXX: Use TYPE attribute to create named CIM type.
            # if attrs(tt).has_key('TYPE'):
            #    return cim_obj.tocimobj(attrs(tt)['TYPE'], p.strip())

            # XXX: Would like to use long() here, but that tends to cause
            # trouble when it's written back out as '2L'
            return int(p.strip())
        except ValueError, e:
            raise ParseError('invalid numeric %s under %s' %
                             (`p`, name(tt)))
    else:
        raise ParseError('invalid VALUETYPE %s in %s',
                         vt, name(tt))
    

#
# Object definition elements
#

def parse_class(tt):
    ## <!ELEMENT CLASS (QUALIFIER*, (PROPERTY | PROPERTY.ARRAY |
    ##                               PROPERTY.REFERENCE)*, METHOD*)>
    ## <!ATTLIST CLASS
    ##     %CIMName; 
    ##     %SuperClass;>

    # This doesn't check the ordering of elements, but it's not very important
    check_node(tt, 'CLASS', ['NAME'], ['SUPERCLASS'],
               ['QUALIFIER', 'PROPERTY', 'PROPERTY.REFERENCE',
                'PROPERTY.ARRAY', 'METHOD'])

    superclass = attrs(tt).get('SUPERCLASS')

    # TODO: Return these as maps, not lists
    properties = byname(list_of_matching(tt, ['PROPERTY', 'PROPERTY.REFERENCE',
                                                  'PROPERTY.ARRAY']))

    qualifiers = byname(list_of_matching(tt, ['QUALIFIER']))
    methods = byname(list_of_matching(tt, ['METHOD']))

    return cim_obj.CIMClass(attrs(tt)['NAME'], superclass=superclass, 
                                                  properties=properties, 
                                                  qualifiers=qualifiers, 
                                                  methods=methods)


def parse_instance(tt):
    """Return a CIMInstance.

    The instance contains the properties, qualifiers and classname for
    the instance"""
    
    ##<!ELEMENT INSTANCE (QUALIFIER*, (PROPERTY | PROPERTY.ARRAY |
    ##                                 PROPERTY.REFERENCE)*)>
    ##<!ATTLIST INSTANCE
    ##	%ClassName;>
    
    check_node(tt, 'INSTANCE', ['CLASSNAME'],
               ['QUALIFIER', 'PROPERTY', 'PROPERTY.ARRAY',
                'PROPERTY.REFERENCE'])

    ## XXX: This does not enforce ordering constraint

    ## XXX: This does not enforce the constraint that there be only
    ## one PROPERTY or PROPERTY.ARRAY.

    ## TODO: Parse instance qualifiers
    qualifiers = {}
    props = list_of_matching(tt, ['PROPERTY.REFERENCE', 'PROPERTY', 'PROPERTY.ARRAY'])

    obj = cim_obj.CIMInstance(attrs(tt)['CLASSNAME'],
                              qualifiers = qualifiers)

    [obj.__setitem__(p.name, p) for p in props]

    return obj

def parse_scope(tt):
    # <!ELEMENT SCOPE EMPTY>
    # <!ATTLIST SCOPE
    #   CLASS (true | false) "false"
    #   ASSOCIATION (true | false) "false"
    #   REFERENCE (true | false) "false"
    #   PROPERTY (true | false) "false"
    #   METHOD (true | false) "false"
    #   PARAMETER (true | false) "false"
    #   INDICATION (true | false) "false"
    check_node(tt, 'SCOPE', [], 
        ['CLASS', 'ASSOCIATION', 'REFERENCE', 'PROPERTY', 'METHOD', 
            'PARAMETER', 'INDICATION'], [])
    return dict([(k,v.lower() == 'true') for k,v in attrs(tt).items()])

def parse_qualifier_declaration(tt):
    ## <!ELEMENT QUALIFIER.DECLARATION (SCOPE?, (VALUE | VALUE.ARRAY)?)>
    ## <!ATTLIST QUALIFIER.DECLARATION 
    ##     %CIMName;               
    ##     %CIMType;               #REQUIRED
    ##     ISARRAY    (true|false) #IMPLIED
    ##     %ArraySize;
    ##     %QualifierFlavor;>

    check_node(tt, 'QUALIFIER.DECLARATION',
               ['NAME', 'TYPE'],
               ['ISARRAY', 'ARRAYSIZE', 'OVERRIDABLE', 'TOSUBCLASS',
                'TOINSTANCE', 'TRANSLATABLE'],
               ['SCOPE', 'VALUE', 'VALUE.ARRAY'])

    a = attrs(tt)
    qname = a['NAME']
    type = a['TYPE']
    try:
        is_array = a['ISARRAY'].lower() == 'true'
    except KeyError:
        is_array = False
    try:
        array_size = int(a['ARRAYSIZE'])
    except KeyError:
        array_size = None

    flavors = {}
    for f in ['OVERRIDABLE', 'TOSUBCLASS', 'TOINSTANCE', 'TRANSLATABLE']:
        try:
            flavors[f.lower()] = a[f].lower() == 'true'
        except KeyError:
            pass

    scopes = None
    value = None
    for child in kids(tt):
        if name(child) == 'SCOPE':
            if scopes is not None:
                raise ParseError("Multiple SCOPE tags encountered")
            scopes = parse_any(child)
        else:
            if value is not None:
                raise ParseError("Multiple VALUE/VALUE.ARRAY tags encountered")
            value = cim_obj.tocimobj(type, parse_any(child))
            
    return cim_obj.CIMQualifierDeclaration(qname, type, value, is_array,
                 array_size, scopes, **flavors)


def parse_qualifier(tt):
    ## <!ELEMENT QUALIFIER (VALUE | VALUE.ARRAY)>
    ## <!ATTLIST QUALIFIER %CIMName;
    ##      %CIMType;              #REQUIRED
    ##      %Propagated;
    ##      %QualifierFlavor;>

    check_node(tt, 'QUALIFIER', ['NAME', 'TYPE'],
               ['OVERRIDABLE', 'TOSUBCLASS', 'TOINSTANCE',
                'TRANSLATABLE', 'PROPAGATED'],
               ['VALUE', 'VALUE.ARRAY'])

    a = attrs(tt)

    q = cim_obj.CIMQualifier(a['NAME'], unpack_value(tt), type=a['TYPE'])

    ## TODO: Lift this out?
    for i in ['OVERRIDABLE', 'TOSUBCLASS', 'TOINSTANCE',
              'TRANSLATABLE', 'PROPAGATED']:
        rv = a.get(i)
        if rv not in ['true', 'false', None]:
            raise ParseError("invalid value %s for %s on %s" %
                             (`rv`, i, name(tt)))
        if rv == 'true':
            rv = True
        elif rv == 'false':
            rv = False
            
        setattr(q, i.lower(), rv)

    return q


def parse_property(tt):
    """Parse PROPERTY into a CIMProperty object.

    VAL is just the pcdata of the enclosed VALUE node."""
    
    ## <!ELEMENT PROPERTY (QUALIFIER*, VALUE?)>
    ## <!ATTLIST PROPERTY %CIMName;
    ##      %ClassOrigin;
    ##      %Propagated;
    ##      %CIMType;              #REQUIRED>

    ## TODO: Parse this into NAME, VALUE, where the value contains
    ## magic fields for the qualifiers and the propagated flag.
    
    check_node(tt, 'PROPERTY', ['TYPE', 'NAME'],
               ['NAME', 'CLASSORIGIN', 'PROPAGATED', 'EmbeddedObject',
                'EMBEDDEDOBJECT'],
               ['QUALIFIER', 'VALUE'])

    quals = {}
    for q in list_of_matching(tt, ['QUALIFIER']):
        quals[q.name] = q

    val = unpack_value(tt)
    a = attrs(tt)
    embedded_object=None
    if 'EmbeddedObject' in a or 'EMBEDDEDOBJECT' in a:
        try:
            embedded_object = a['EmbeddedObject']
        except KeyError:
            embedded_object = a['EMBEDDEDOBJECT']
    if embedded_object is not None:
        val = parse_embeddedObject(val)

    return CIMProperty(a['NAME'],
                       val,
                       a['TYPE'],
                       class_origin=a.get('CLASSORIGIN'),
                       propagated=unpack_boolean(a.get('PROPAGATED')),
                       qualifiers=quals,
                       embedded_object=embedded_object)


def parse_property_array(tt):
    """
    <!ELEMENT PROPERTY.ARRAY (QUALIFIER*, VALUE.ARRAY?)>
    <!ATTLIST PROPERTY.ARRAY %CIMName;
         %CIMType;              #REQUIRED
         %ArraySize;
         %ClassOrigin;
         %Propagated;>
    """

    from cim_obj import tocimobj

    check_node(tt, 'PROPERTY.ARRAY', ['NAME', 'TYPE'],
                    ['REFERENCECLASS', 'CLASSORIGIN', 'PROPAGATED',
                     'ARRAYSIZE', 'EmbeddedObject', 'EMBEDDEDOBJECT'],
               ['QUALIFIER', 'VALUE.ARRAY'])

    quals = {}
    for q in list_of_matching(tt, ['QUALIFIER']):
        quals[q.name] = q

    values = unpack_value(tt)
    a = attrs(tt)
    embedded_object = None
    if 'EmbeddedObject' in a or 'EMBEDDEDOBJECT' in a:
        try:
            embedded_object = a['EmbeddedObject']
        except KeyError:
            embedded_object = a['EMBEDDEDOBJECT']

    if embedded_object is not None:
        values = parse_embeddedObject(values)

    obj = CIMProperty(a['NAME'],
                      values,
                      a['TYPE'], 
                      class_origin=a.get('CLASSORIGIN'),
                      qualifiers=quals,
                      is_array=True,
                      embedded_object=embedded_object)

    ## TODO: qualifiers, other attributes
    return obj


def parse_property_reference(tt):
    """
    <!ELEMENT PROPERTY.REFERENCE (QUALIFIER*, (VALUE.REFERENCE)?)>
    <!ATTLIST PROPERTY.REFERENCE
	%CIMName; 
	%ReferenceClass; 
	%ClassOrigin; 
	%Propagated;>
    """
    
    check_node(tt, 'PROPERTY.REFERENCE', ['NAME'],
                    ['REFERENCECLASS', 'CLASSORIGIN', 'PROPAGATED'])

    value = list_of_matching(tt, ['VALUE.REFERENCE'])

    if value is None or len(value) == 0:
        value = None
    elif len(value) == 1:
        value = value[0]
    else:
        raise ParseError('Too many VALUE.REFERENCE elements.')
    
    attributes = attrs(tt)
    pref = cim_obj.CIMProperty(attributes['NAME'], value, type = 'reference')

    for q in list_of_matching(tt, ['QUALIFIER']):
        pref.qualifiers[q.name] = q

    if attributes.has_key('REFERENCECLASS'):
        pref.reference_class = attributes['REFERENCECLASS']

    if attributes.has_key('CLASSORIGIN'):
        pref.class_origin = attributes['CLASSORIGIN']

    if attributes.has_key('PROPAGATED'):
        pref.propagated = attributes['PROPAGATED']

    return pref


def parse_method(tt):
    """
    <!ELEMENT METHOD (QUALIFIER*, (PARAMETER | PARAMETER.REFERENCE |
                                   PARAMETER.ARRAY | PARAMETER.REFARRAY)*)>
    <!ATTLIST METHOD %CIMName;
         %CIMType;              #IMPLIED
         %ClassOrigin;
         %Propagated;>
    """

    check_node(tt, 'METHOD', ['NAME'],
               ['TYPE', 'CLASSORIGIN', 'PROPAGATED'],
               ['QUALIFIER', 'PARAMETER', 'PARAMETER.REFERENCE',
                'PARAMETER.ARRAY', 'PARAMETER.REFARRAY'])

    qualifiers = byname(list_of_matching(tt, ['QUALIFIER']))

    parameters = byname(list_of_matching(tt, ['PARAMETER',
                                                      'PARAMETER.REFERENCE',
                                                      'PARAMETER.ARRAY',
                                                      'PARAMETER.REFARRAY',]))

    a = attrs(tt)

    return cim_obj.CIMMethod(a['NAME'], 
                             return_type=a.get('TYPE'),
                             parameters=parameters, 
                             qualifiers=qualifiers,
                             class_origin=a.get('CLASSORIGIN'),
                             propagated=unpack_boolean(a.get('PROPAGATED')))


def parse_parameter(tt):
    """
    <!ELEMENT PARAMETER (QUALIFIER*)>
    <!ATTLIST PARAMETER 
         %CIMName;
         %CIMType;              #REQUIRED>
    """
    
    check_node(tt, 'PARAMETER', ['NAME', 'TYPE'], [])

    quals = {}
    for q in list_of_matching(tt, ['QUALIFIER']):
        quals[q.name] = q

    a = attrs(tt)

    return cim_obj.CIMParameter(a['NAME'], type=a['TYPE'], qualifiers=quals)

def parse_parameter_reference(tt):
    """
    <!ELEMENT PARAMETER.REFERENCE (QUALIFIER*)>
    <!ATTLIST PARAMETER.REFERENCE
	%CIMName; 
	%ReferenceClass;>
    """

    check_node(tt, 'PARAMETER.REFERENCE', ['NAME'], ['REFERENCECLASS'])

    quals = {}
    for q in list_of_matching(tt, ['QUALIFIER']):
        quals[q.name] = q

    a = attrs(tt)

    return cim_obj.CIMParameter(a['NAME'],
                        type='reference',
                        reference_class=a.get('REFERENCECLASS'),
                        qualifiers=quals)


def parse_parameter_array(tt):
    """
    <!ELEMENT PARAMETER.ARRAY (QUALIFIER*)>
    <!ATTLIST PARAMETER.ARRAY 
         %CIMName;
         %CIMType;              #REQUIRED
         %ArraySize;>
    """

    check_node(tt, 'PARAMETER.ARRAY', ['NAME', 'TYPE'], 
                ['ARRAYSIZE'])

    quals = {}
    for q in list_of_matching(tt, ['QUALIFIER']):
        quals[q.name] = q

    a = attrs(tt)

    array_size = a.get('ARRAYSIZE')
    if array_size is not None:
        array_size = int(array_size)

    return cim_obj.CIMParameter(a['NAME'], 
                        type=a['TYPE'],
                        is_array = True,
                        array_size=array_size,
                        qualifiers=quals)


def parse_parameter_refarray(tt):
    """
    <!ELEMENT PARAMETER.REFARRAY (QUALIFIER*)>
    <!ATTLIST PARAMETER.REFARRAY
	%CIMName; 
	%ReferenceClass; 
	%ArraySize;>
    """

    check_node(tt, 'PARAMETER.REFARRAY', ['NAME'],
               ['REFERENCECLASS', 'ARRAYSIZE'])

    quals = {}
    for q in list_of_matching(tt, ['QUALIFIER']):
        quals[q.name] = q

    a = attrs(tt)

    array_size = a.get('ARRAYSIZE')
    if array_size is not None:
        array_size = int(array_size)

    return cim_obj.CIMParameter(a['NAME'], 'reference', is_array = True,
                        reference_class=a.get('REFERENCECLASS'),
                        array_size=array_size,
                        qualifiers=quals)


#
# Message elements
#

def parse_message(tt):
    """
    <!ELEMENT MESSAGE (SIMPLEREQ | MULTIREQ | SIMPLERSP | MULTIRSP)>
    <!ATTLIST MESSAGE
	ID CDATA #REQUIRED
	PROTOCOLVERSION CDATA #REQUIRED>
    """

    check_node(tt, 'MESSAGE', ['ID', 'PROTOCOLVERSION'])

    messages = one_child(
        tt, ['SIMPLEREQ', 'MULTIREQ', 'SIMPLERSP', 'MULTIRSP', 'SIMPLEEXPREQ'])
    
    if type(messages) is not list:
        # make single and multi forms consistent
        messages = [messages]

    return name(tt), attrs(tt), messages


def parse_multireq(tt):
    raise ParseError('MULTIREQ parser not implemented')


def parse_multiexpreq(tt):
    raise ParseError('MULTIEXPREQ parser not implemented')

def parse_simpleexpreq(tt):
    """
    <!ELEMENT SIMPLEEXPREQ (EXPMETHODCALL)>
    """

    child = one_child(tt, ['EXPMETHODCALL'])

    return name(tt), attrs(tt), child

def parse_simplereq(tt):
    """
    <!ELEMENT SIMPLEREQ (IMETHODCALL | METHODCALL)>
    """

    check_node(tt, 'SIMPLEREQ')

    child = one_child(tt, ['IMETHODCALL', 'METHODCALL'])

    return name(tt), attrs(tt), child


def parse_imethodcall(tt):
    """
    <!ELEMENT IMETHODCALL (LOCALNAMESPACEPATH, IPARAMVALUE*)>
    <!ATTLIST IMETHODCALL
	%CIMName;>
    """

    check_node(tt, 'IMETHODCALL', ['NAME'])

    if len(kids(tt)) < 1:
        raise ParseError('Expecting LOCALNAMESPACEPATH, got nothing')

    localnspath = parse_localnamespacepath(kids(tt)[0])

    params = map(lambda x: parse_iparamvalue(x),
                 kids(tt)[1:])

    return (name(tt), attrs(tt), localnspath, params)


def parse_methodcall(tt):
    """
    <!ELEMENT METHODCALL ((LOCALCLASSPATH|LOCALINSTANCEPATH),PARAMVALUE*)>
    <!ATTLIST METHODCALL
         %CIMName;>
    """

    check_node(tt, 'METHODCALL', ['NAME'], [],
               ['LOCALCLASSPATH', 'LOCALINSTANCEPATH', 'PARAMVALUE'])
    path = list_of_matching(tt, ['LOCALCLASSPATH','LOCALINSTANCEPATH'])
    if len(path) != 1:
        raise ParseError('Expecting one of LOCALCLASSPATH or LOCALINSTANCEPATH, got %s' % `path`)
    path = path[0]
    params = list_of_matching(tt, ['PARAMVALUE'])
    return (name(tt), attrs(tt), path, params)


def parse_expmethodcall(tt):
    """
    <!ELEMENT EXPMETHODCALL (EXPPARAMVALUE*)>
    <!ATTLIST EXPMETHODCALL 
        %CIMName;>
    """

    check_node(tt, 'EXPMETHODCALL', ['NAME'], [], ['EXPPARAMVALUE'])


    params = list_of_matching(tt, ['EXPPARAMVALUE'])

    return (name(tt), attrs(tt), params)


def parse_paramvalue(tt):
    ## <!ELEMENT PARAMVALUE (VALUE | VALUE.REFERENCE | VALUE.ARRAY |
    ##                       VALUE.REFARRAY)?>
    ## <!ATTLIST PARAMVALUE
    ##   %CIMName;
    ##   %ParamType;  #IMPLIED
    ##   %EmbeddedObject;>

    ## Version 2.1.1 of the DTD lacks the %ParamType attribute but it
    ## is present in version 2.2.  Make it optional to be backwards
    ## compatible.

    check_node(tt, 'PARAMVALUE', ['NAME'], ['PARAMTYPE','EmbeddedObject', 
                                            'EMBEDDEDOBJECT'])

    child = optional_child(tt,
                        ['VALUE', 'VALUE.REFERENCE', 'VALUE.ARRAY',
                         'VALUE.REFARRAY',])

    if attrs(tt).has_key('PARAMTYPE'):
        paramtype = attrs(tt)['PARAMTYPE']
    else:
        paramtype = None

    if 'EmbeddedObject' in attrs(tt) or 'EMBEDDEDOBJECT' in attrs(tt):
        child = parse_embeddedObject(child)
        
    return attrs(tt)['NAME'], paramtype, child


def parse_iparamvalue(tt):
    ## <!ELEMENT IPARAMVALUE (VALUE | VALUE.ARRAY | VALUE.REFERENCE |
    ##                       INSTANCENAME | CLASSNAME | QUALIFIER.DECLARATION |
    ##                       CLASS | INSTANCE | VALUE.NAMEDINSTANCE)?>
    ## <!ATTLIST IPARAMVALUE %CIMName;>

    """Returns NAME, VALUE pair."""
    
    check_node(tt, 'IPARAMVALUE', ['NAME'], [])

    child = optional_child(tt, 
                           ['VALUE', 'VALUE.ARRAY', 'VALUE.REFERENCE',
                            'INSTANCENAME', 'CLASSNAME',
                            'QUALIFIER.DECLARATION', 'CLASS', 'INSTANCE',
                            'VALUE.NAMEDINSTANCE'])

    name = attrs(tt)['NAME']
    if isinstance(child, basestring) and \
            name.lower() in ['deepinheritance', 'localonly', 
                             'includequalifiers', 'includeclassorigin']:
        if child.lower() in ['true', 'false']:
            child = child.lower() == 'true'

    return name,  child

          
def parse_expparamvalue(tt):
    """
    <!ELEMENT EXPPARAMVALUE (INSTANCE?)>
    <!ATTLIST EXPPARAMVALUE 
        %CIMName;>
    """

    check_node(tt, 'EXPPARAMVALUE', ['NAME'], [], ['INSTANCE'])

    child = optional_child(tt, ['INSTANCE'])

    name = attrs(tt)['NAME']
    return name,  child


def parse_multirsp(tt):
    raise ParseError('MULTIRSP parser not implemented')


def parse_multiexprsp(tt):
    raise ParseError('MULTIEXPRSP parser not implemented')


def parse_simplersp(tt):
    ## <!ELEMENT SIMPLERSP (METHODRESPONSE | IMETHODRESPONSE)>
    check_node(tt, 'SIMPLERSP', [], [])

    child = one_child(tt, ['METHODRESPONSE', 'IMETHODRESPONSE'])

    return name(tt), attrs(tt), child


def parse_simpleexprsp(tt):
    raise ParseError('SIMPLEEXPRSP parser not implemented')


def parse_methodresponse(tt):
    ## <!ELEMENT METHODRESPONSE (ERROR | (RETURNVALUE?, PARAMVALUE*))>
    ## <!ATTLIST METHODRESPONSE
    ##    %CIMName;>

    check_node(tt, 'METHODRESPONSE', ['NAME'], [])

    return name(tt), attrs(tt), list_of_various(tt, ['ERROR', 'RETURNVALUE',
                                                     'PARAMVALUE'])
    

def parse_expmethodresponse(tt):
    raise ParseError('EXPMETHODRESPONSE parser not implemented')


def parse_imethodresponse(tt):
    ## <!ELEMENT IMETHODRESPONSE (ERROR | IRETURNVALUE?)>
    ## <!ATTLIST IMETHODRESPONSE %CIMName;>
    check_node(tt, 'IMETHODRESPONSE', ['NAME'], [])

    return name(tt), attrs(tt), optional_child(tt, ['ERROR', 'IRETURNVALUE'])


def parse_error(tt):
    """
    <!ELEMENT ERROR EMPTY>
    <!ATTLIST ERROR
	CODE CDATA #REQUIRED
	DESCRIPTION CDATA #IMPLIED>
    """

    ## TODO: Return a CIMError object, not a tuple

    check_node(tt, 'ERROR', ['CODE'], ['DESCRIPTION'])

    return (name(tt), attrs(tt), None)


def parse_returnvalue(tt):
    ## <!ELEMENT RETURNVALUE (VALUE | VALUE.ARRAY | VALUE.REFERENCE |
    ##                        VALUE.REFARRAY)>
    ## <!ATTLIST RETURNVALUE %ParamType;       #IMPLIED>

    ## Version 2.1.1 of the DTD lacks the %ParamType attribute but it
    ## is present in version 2.2.  Make it optional to be backwards
    ## compatible.

    check_node(tt, 'RETURNVALUE', [], ['PARAMTYPE'])

    return name(tt), attrs(tt), one_child(tt, ['VALUE', 'VALUE.ARRAY',
                                               'VALUE.REFERENCE',
                                               'VALUE.REFARRAY'])


def parse_ireturnvalue(tt):
    ## <!ELEMENT IRETURNVALUE (CLASSNAME* | INSTANCENAME* | VALUE* |
    ##                         VALUE.OBJECTWITHPATH* |
    ##                         VALUE.OBJECTWITHLOCALPATH* | VALUE.OBJECT* |
    ##                         OBJECTPATH* | QUALIFIER.DECLARATION* |
    ##                         VALUE.ARRAY? | VALUE.REFERENCE? | CLASS* |
    ##                         INSTANCE* | VALUE.NAMEDINSTANCE*)>

    check_node(tt, 'IRETURNVALUE', [], [])

    # XXX: doesn't prohibit the case of only one VALUE.ARRAY or
    # VALUE.REFERENCE.  But why is that required?  Why can it return
    # multiple VALUEs but not multiple VALUE.REFERENCEs?

    values = list_of_same(tt, ['CLASSNAME', 'INSTANCENAME',
                               'VALUE', 'VALUE.OBJECTWITHPATH', 'VALUE.OBJECT',
                               'OBJECTPATH', 'QUALIFIER.DECLARATION',
                               'VALUE.ARRAY', 'VALUE.REFERENCE',
                               'CLASS', 'INSTANCE',
                               'VALUE.NAMEDINSTANCE',])

    ## TODO: Call unpack_value if appropriate

    return name(tt), attrs(tt), values

#
# Object naming and locating elements
#

def parse_any(tt):
    """Parse any fragment of XML."""

    nodename = name(tt).lower().replace('.', '_')
    fn_name = 'parse_' + nodename
    fn = globals().get(fn_name)
    if fn is None:
        raise ParseError('no parser for node type %s' % name(tt))
    else:
        return fn(tt)

def parse_embeddedObject(val):
    if isinstance(val, list):
        return [parse_embeddedObject(obj) for obj in val]
    if val is None:
        return None
    tt = xml_to_tupletree(val)
    if tt[0] == 'INSTANCE':
        return parse_instance(tt)
    elif tt[0] == 'CLASS':
        return parse_class(tt)
    else:
        raise ParseError('Error parsing embedded object')


def unpack_value(tt):
    """Find VALUE or VALUE.ARRAY under TT and convert to a Python value.

    Looks at the TYPE of the node to work out how to decode it.
    Handles nodes with no value (e.g. in CLASS.)
    """
    ## TODO: Handle VALUE.REFERENCE, VALUE.REFARRAY

    valtype = attrs(tt)['TYPE']

    raw_val = list_of_matching(tt, ['VALUE', 'VALUE.ARRAY'])
    if len(raw_val) == 0:
        return None
    elif len(raw_val) > 1:
        raise ParseError('more than one VALUE or VALUE.ARRAY under %s' % name(tt))

    raw_val = raw_val[0]
    
    if isinstance(raw_val, list):
        return [cim_obj.tocimobj(valtype, x) for x in raw_val]
    elif len(raw_val) == 0 and valtype != 'string':
        return None
    else:
        return cim_obj.tocimobj(valtype, raw_val)


def unpack_boolean(p):
    """Unpack a boolean, represented as "TRUE" or "FALSE" in CIM."""
    if p is None:
        return None

    ## CIM-XML says "These values MUST be treated as case-insensitive"
    ## (even though the XML definition requires them to be lowercase.)
    
    p = p.strip().lower()                   # ignore space
    if p == 'true':
        return True
    elif p == 'false':
        return False
    elif p == '':
        return None
    else:
        raise ParseError('invalid boolean %s' % `p`)
