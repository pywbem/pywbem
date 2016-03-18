#
# (C) Copyright 2003,2004 Hewlett-Packard Development Company, L.P.
# (C) Copyright 2006-2007 Novell, Inc.
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
# Author: Martin Pool <mbp@hp.com>
# Author: Tim Potter <tpot@hp.com>
# Author: Bart Whiteley <bwhiteley@suse.de>
# Author: Ross Peoples <ross.peoples@gmail.com>
#

# pylint: disable=too-many-lines
'''Tuple parser for the XML schema representing CIM messages.

This framework is meant to add some value to the tuple-tree
representation of CIM in XML by having the following properties:

  - Silently ignoring whitespace text elements

  - Conversion from tuple-tree representation into a python dictionary
    which can then be accessed in a readable fashion.

  - Validation of the XML elements and attributes without having to
    use the DTD file or any external tools.

'''

# Implementation: This works by a recursive descent down the CIM XML
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

#   tup_tree[0]: name string             == name(tup_tree)
#   tup_tree[1]: hash of attributes      == attrs(tup_tree)
#   tup_tree[2]: sequence of children    == kids(tup_tree)

# At the moment this layer is a little inconsistent: in some places it
# returns tupletrees, and in others Python objects.  It may be better
# to hide the tupletree/XML representation from higher level code.


# TODO: Maybe take a DTD fragment like "(DECLGROUP |
# DECLGROUP.WITHNAME | DECLGROUP.WITHPATH)*", parse that and check it
# directly.

# TODO: Syntax-check some attributes with defined formats, such as NAME

# TODO: Implement qualifiers by making subclasses of CIM types with a
# .qualifiers property.

# This module is meant to be safe for 'import *'.

import six

from .cim_obj import CIMInstance, CIMInstanceName, CIMClass, \
                     CIMClassName, CIMProperty, CIMMethod, \
                     CIMParameter, CIMQualifier, CIMQualifierDeclaration, \
                     tocimobj, byname
from .tupletree import xml_to_tupletree

__all__ = ['ParseError']

class ParseError(Exception):
    """This exception is raised when there is a validation error detected
    by the parser."""
    pass


def filter_tuples(list_):
    """Return only the tuples in a list.

    In a tupletree, tuples correspond to XML elements.  Useful for
    stripping out whitespace data in a child list."""

    if list_ is None:
        return []
    else:
        return [x for x in list_ if isinstance(x, tuple)]


def pcdata(tup_tree):
    """Return the concatenated character data within a tup_tree.

    The tup_tree must not have non-character children."""
    for inst in tup_tree[2]:
        if not isinstance(inst, six.string_types):
            raise ParseError('unexpected node %r under %r' % (inst, tup_tree))
    return ''.join(tup_tree[2])


def name(tup_tree):
    """Return first (name) element of tup_tree"""
    return tup_tree[0]


def attrs(tup_tree):
    """Return second (attributes) element of tup_tree"""
    return tup_tree[1]


def kids(tup_tree):
    """Return third (children) element of tup_tree"""
    return filter_tuples(tup_tree[2])

# pylint: disable=too-many-arguments
def check_node(tup_tree, nodename, required_attrs=[], optional_attrs=[],
               allowed_children=None,
               allow_pcdata=False):
    # pylint: disable=too-many-branches
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

    if name(tup_tree) != nodename:
        raise ParseError('expected node type %s, not %s' %
                         (nodename, name(tup_tree)))

    # Check we have all the required attributes, and no unexpected ones
    tt_attrs = {}
    if attrs(tup_tree) is not None:
        tt_attrs = attrs(tup_tree).copy()

    for attr in required_attrs:
        if attr not in tt_attrs:
            raise ParseError('expected %s attribute on %s node, but only '
                             'have %s' % (attr, name(tup_tree),
                                          attrs(tup_tree).keys()))
        del tt_attrs[attr]

    for attr in optional_attrs:
        if attr in tt_attrs:
            del tt_attrs[attr]

    if len(tt_attrs.keys()) > 0:
        raise ParseError('invalid extra attributes %s' % tt_attrs.keys())

    if allowed_children is not None:
        for child in kids(tup_tree):
            if name(child) not in allowed_children:
                raise ParseError('unexpected node %s under %s; wanted %s'
                                 % (name(child), name(tup_tree),
                                    allowed_children))

    if not allow_pcdata:
        for child in tup_tree[2]:
            if isinstance(child, six.string_types):
                if child.lstrip(' \t\n') != '':
                    raise ParseError('unexpected non-blank pcdata node %r '
                                     'under %s' % (child,
                                                   name(tup_tree)))


def one_child(tup_tree, acceptable):
    """Parse children of a node with exactly one child node.

    PCData is ignored.
    """

    k = kids(tup_tree)

    if len(k) != 1:
        raise ParseError('In element %s with attributes %s, expected '\
                'just one child element %s, but got child elements %s' %\
                (name(tup_tree), attrs(tup_tree), acceptable,
                 [t[0] for t in k]))

    child = k[0]

    if name(child) not in acceptable:
        raise ParseError('In element %s with attributes %s, expected one '\
                'child element %s, but got child element %s' %\
                (name(tup_tree), attrs(tup_tree), acceptable, name(child)))

    return parse_any(child)


def optional_child(tup_tree, allowed):
    """Parse exactly zero or one of a list of elements from the
    child nodes."""

    k = kids(tup_tree)

    if len(k) > 1:
        raise ParseError('In element %s with attributes %s, expected zero or '\
                'one child element %s, but got child elements %s' %\
                (name(tup_tree), attrs(tup_tree), allowed, [t[0] for t in k]))
    elif len(k) == 1:
        return one_child(tup_tree, allowed)
    else:
        return None


def list_of_various(tup_tree, acceptable):
    """Parse zero or more of a list of elements from the child nodes.

    Each element of the list can be any type from the list of acceptable
    nodes."""

    result = []

    for child in kids(tup_tree):
        if name(child) not in acceptable:
            raise ParseError('In element %s with attributes %s, expected zero '\
                    'or more child elements %s, but got child element %s' %\
                    (name(tup_tree), attrs(tup_tree), acceptable, name(child)))
        result.append(parse_any(child))

    return result


def list_of_matching(tup_tree, matched):
    """Parse only the children of particular types under tup_tree.

    Other children are ignored rather than giving an error."""

    result = []

    for child in kids(tup_tree):
        if name(child) not in matched:
            continue
        result.append(parse_any(child))

    return result


def list_of_same(tup_tree, acceptable):
    """Parse a list of elements from child nodes.

    The children can be any of the listed acceptable types, but they
    must all be the same.
    """

    kid = kids(tup_tree)
    if not kid:            # empty list, consistent with list_of_various
        return []

    a_child = name(kid[0])
    if a_child not in acceptable:
        raise ParseError('In element %s with attributes %s, expected '\
                'child elements %s, but got child element %s' %\
                (name(tup_tree), attrs(tup_tree), acceptable, a_child))
    result = []
    for child in kid:
        if name(child) != a_child:
            raise ParseError('In element %s with attributes %s, expected '\
                    'sequence of only child elements %s, but got child '\
                    'element %s' % (name(tup_tree), attrs(tup_tree), a_child, \
                     name(child)))
        result.append(parse_any(child))

    return result


def notimplemented(tup_tree):
    """raise exception for notimplemented function"""
    raise ParseError('parser for %s not implemented' % name(tup_tree))

#
# Root element
#

def parse_cim(tup_tree):
    """Parse the top level element of CIM/XML message

           <!ELEMENT CIM (MESSAGE | DECLARATION)>
           <!ATTLIST CIM
               CIMVERSION CDATA #REQUIRED
               DTDVERSION CDATA #REQUIRED>
    """

    check_node(tup_tree, 'CIM', ['CIMVERSION', 'DTDVERSION'])

    if not attrs(tup_tree)['CIMVERSION'].startswith('2.'):
        raise ParseError('CIMVERSION is %s, expected 2.x.y' %
                         attrs(tup_tree)['CIMVERSION'])

    child = one_child(tup_tree, ['MESSAGE', 'DECLARATION'])

    return name(tup_tree), attrs(tup_tree), child


#
# Declaration elements
#

def parse_declaration(tup_tree):
    """
    <!ELEMENT DECLARATION ( DECLGROUP | DECLGROUP.WITHNAME |
                            DECLGROUP.WITHPATH )+>

    Note: We only support the DECLGROUP child, at this point.
    """

    check_node(tup_tree, 'DECLARATION')

    child = one_child(tup_tree, ['DECLGROUP'])

    return name(tup_tree), attrs(tup_tree), child


def parse_declgroup(tup_tree):
    """
    <!ELEMENT DECLGROUP ( (LOCALNAMESPACEPATH|NAMESPACEPATH)?,
                          QUALIFIER.DECLARATION*, VALUE.OBJECT* )>

    Note: We only support the QUALIFIER.DECLARATION and VALUE.OBJECT
          children, and with a multiplicity of 1, at this point.
    """

    check_node(tup_tree, 'DECLGROUP')

    child = one_child(tup_tree, ['QUALIFIER.DECLARATION', 'VALUE.OBJECT'])

    return name(tup_tree), attrs(tup_tree), child


#
# Object value elements
#

def parse_value(tup_tree):
    '''Return VALUE contents as a string'''
    ## <!ELEMENT VALUE (#PCDATA)>
    check_node(tup_tree, 'VALUE', [], [], [], True)

    return pcdata(tup_tree)


def parse_value_array(tup_tree):
    """Return list of strings."""
    ## <!ELEMENT VALUE.ARRAY (VALUE*)>
    check_node(tup_tree, 'VALUE.ARRAY', [], [], ['VALUE'])

    return list_of_same(tup_tree, ['VALUE'])


def parse_value_reference(tup_tree):
    """
    <!ELEMENT VALUE.REFERENCE (CLASSPATH | LOCALCLASSPATH | CLASSNAME |
                               INSTANCEPATH | LOCALINSTANCEPATH |
                               INSTANCENAME)>
    """

    check_node(tup_tree, 'VALUE.REFERENCE', [])

    child = one_child(tup_tree,
                      ['CLASSPATH', 'LOCALCLASSPATH', 'CLASSNAME',
                       'INSTANCEPATH', 'LOCALINSTANCEPATH',
                       'INSTANCENAME'])

    # The VALUE.REFERENCE wrapper element is discarded
    return child


def parse_value_refarray(tup_tree):
    """
    <!ELEMENT VALUE.REFARRAY (VALUE.REFERENCE*)>
    """

    check_node(tup_tree, 'VALUE.REFARRAY')

    children = list_of_various(tup_tree, ['VALUE.REFERENCE'])

    # The VALUE.REFARRAY wrapper element is discarded
    return children


def parse_value_object(tup_tree):
    """
    <!ELEMENT VALUE.OBJECT (CLASS | INSTANCE)>
    """

    check_node(tup_tree, 'VALUE.OBJECT')

    child = one_child(tup_tree, ['CLASS', 'INSTANCE'])

    return (name(tup_tree), attrs(tup_tree), child)


def parse_value_namedinstance(tup_tree):
    """
    <!ELEMENT VALUE.NAMEDINSTANCE (INSTANCENAME, INSTANCE)>
    """

    check_node(tup_tree, 'VALUE.NAMEDINSTANCE')

    k = kids(tup_tree)
    if len(k) != 2:
        raise ParseError('expecting (INSTANCENAME, INSTANCE), got %r' % k)

    instancename = parse_instancename(k[0])
    instance = parse_instance(k[1])

    instance.path = instancename

    return instance


def parse_value_namedobject(tup_tree):
    """
    <!ELEMENT VALUE.NAMEDOBJECT (CLASS | (INSTANCENAME, INSTANCE))>
    """

    check_node(tup_tree, 'VALUE.NAMEDOBJECT')

    k = kids(tup_tree)
    if len(k) == 1:
        _object = parse_class(k[0])
    elif len(k) == 2:
        path = parse_instancename(kids(tup_tree)[0])

        # pylint: disable=redefined-variable-type
        # redefines _object from pywbem.cim_obj.CIMClass to ...CIMInstance
        _object = parse_instance(kids(tup_tree)[1])

        _object.path = path
    else:
        raise ParseError('Expecting one or two elements, got %r' %
                         kids(tup_tree))

    return (name(tup_tree), attrs(tup_tree), _object)

# pylint: disable=invalid-name
def parse_value_objectwithlocalpath(tup_tree):
    """
    <!ELEMENT VALUE.OBJECTWITHLOCALPATH ((LOCALCLASSPATH, CLASS) |
                                         (LOCALINSTANCEPATH, INSTANCE))>
    """

    check_node(tup_tree, 'VALUE.OBJECTWITHLOCALPATH')

    if len(kids(tup_tree)) != 2:
        raise ParseError('Expecting two elements, got %s' %
                         len(kids(tup_tree)))

    if kids(tup_tree)[0][0] == 'LOCALCLASSPATH':
        _object = (parse_localclasspath(kids(tup_tree)[0]),
                   parse_class(kids(tup_tree)[1]))
    else:
        path = parse_localinstancepath(kids(tup_tree)[0])
        # pylint: disable=redefined-variable-type
        # redefines _object from tuple to CIMInstance
        _object = parse_instance(kids(tup_tree)[1])
        _object.path = path

    return (name(tup_tree), attrs(tup_tree), _object)

def parse_value_objectwithpath(tup_tree):
    """
    <!ELEMENT VALUE.OBJECTWITHPATH ((CLASSPATH, CLASS) |
                                    (INSTANCEPATH, INSTANCE))>
    """

    check_node(tup_tree, 'VALUE.OBJECTWITHPATH')

    k = kids(tup_tree)

    if len(k) != 2:
        raise ParseError('Expecting two elements, got %s' % k)

    if name(k[0]) == 'CLASSPATH':
        _object = (parse_classpath(k[0]), parse_class(k[1]))
    else:
        path = parse_instancepath(k[0])
        # pylint: disable=redefined-variable-type
        # redefines _object from tuple to CIMInstance
        _object = parse_instance(k[1])
        _object.path = path

    return (name(tup_tree), attrs(tup_tree), _object)

#
# Object naming and locating elements
#

def parse_namespacepath(tup_tree):
    """
    <!ELEMENT NAMESPACEPATH (HOST, LOCALNAMESPACEPATH)>
    """

    check_node(tup_tree, 'NAMESPACEPATH')

    if len(kids(tup_tree)) != 2:
        raise ParseError('Expecting (HOST, LOCALNAMESPACEPATH) '
                         'got %s' % kids(tup_tree))

    host = parse_host(kids(tup_tree)[0])
    localnspath = parse_localnamespacepath(kids(tup_tree)[1])

    return (host, localnspath)


def parse_localnamespacepath(tup_tree):
    """
    <!ELEMENT LOCALNAMESPACEPATH (NAMESPACE+)>
    """

    check_node(tup_tree, 'LOCALNAMESPACEPATH', [], [], ['NAMESPACE'])

    if len(kids(tup_tree)) == 0:
        raise ParseError('Expecting one or more of NAMESPACE, got nothing')

    ns_list = list_of_various(tup_tree, ['NAMESPACE'])

    return '/'.join(ns_list)


def parse_host(tup_tree):
    """
    <!ELEMENT HOST (#PCDATA)>
    """

    check_node(tup_tree, 'HOST', allow_pcdata=True)

    return pcdata(tup_tree)


def parse_namespace(tup_tree):
    """Parse NAMESPACE element for namespace name
    <!ELEMENT NAMESPACE EMPTY>
    <!ATTLIST NAMESPACE
        %CIMName;>
    """

    check_node(tup_tree, 'NAMESPACE', ['NAME'], [], [])

    return attrs(tup_tree)['NAME']


def parse_classpath(tup_tree):
    """
    <!ELEMENT CLASSPATH (NAMESPACEPATH, CLASSNAME)>
    """

    check_node(tup_tree, 'CLASSPATH')

    if len(kids(tup_tree)) != 2:
        raise ParseError('Expecting (NAMESPACEPATH, CLASSNAME) '
                         'got %s' % kids(tup_tree))

    nspath = parse_namespacepath(kids(tup_tree)[0])
    classname = parse_classname(kids(tup_tree)[1])

    return CIMClassName(classname.classname,
                        host=nspath[0], namespace=nspath[1])


def parse_localclasspath(tup_tree):
    """
    <!ELEMENT LOCALCLASSPATH (LOCALNAMESPACEPATH, CLASSNAME)>
    """

    check_node(tup_tree, 'LOCALCLASSPATH')

    if len(kids(tup_tree)) != 2:
        raise ParseError('Expecting (LOCALNAMESPACEPATH, CLASSNAME) '
                         'got %s' % kids(tup_tree))

    localnspath = parse_localnamespacepath(kids(tup_tree)[0])
    classname = parse_classname(kids(tup_tree)[1])

    return CIMClassName(classname.classname, namespace=localnspath)

def parse_classname(tup_tree):
    """Parse a CLASSNAME element and return a CIMClassName.

           <!ELEMENT CLASSNAME EMPTY>
           <!ATTLIST CLASSNAME
               %CIMName;>
    """
    check_node(tup_tree, 'CLASSNAME', ['NAME'], [], [])
    return CIMClassName(attrs(tup_tree)['NAME'])


def parse_instancepath(tup_tree):
    """Parse a INSTANCEPATH element returning the instance name.

          <!ELEMENT INSTANCEPATH (NAMESPACEPATH, INSTANCENAME)>
    """

    check_node(tup_tree, 'INSTANCEPATH')

    if len(kids(tup_tree)) != 2:
        raise ParseError('Expecting (NAMESPACEPATH, INSTANCENAME), got %r'
                         % kids(tup_tree))

    nspath = parse_namespacepath(kids(tup_tree)[0])
    instancename = parse_instancename(kids(tup_tree)[1])

    instancename.host = nspath[0]
    instancename.namespace = nspath[1]

    return instancename

def parse_localinstancepath(tup_tree):
    """Parse a LOCALINSTANCEPATH element:

           <!ELEMENT LOCALINSTANCEPATH (LOCALNAMESPACEPATH, INSTANCENAME)>
    """

    check_node(tup_tree, 'LOCALINSTANCEPATH')

    if len(kids(tup_tree)) != 2:
        raise ParseError('Expecting (LOCALNAMESPACEPATH, INSTANCENAME), '
                         'got %s' % kids(tup_tree))

    localnspath = parse_localnamespacepath(kids(tup_tree)[0])
    instancename = parse_instancename(kids(tup_tree)[1])

    instancename.namespace = localnspath

    return instancename

def parse_instancename(tup_tree):
    """Parse XML INSTANCENAME into CIMInstanceName object."""

    ## <!ELEMENT INSTANCENAME (KEYBINDING* | KEYVALUE? | VALUE.REFERENCE?)>
    ## <!ATTLIST INSTANCENAME %ClassName;>

    check_node(tup_tree, 'INSTANCENAME', ['CLASSNAME'])

    if len(kids(tup_tree)) == 0:
        # probably not ever going to see this, but it's valid
        # according to the grammar
        return CIMInstanceName(attrs(tup_tree)['CLASSNAME'], {})

    kid0 = kids(tup_tree)[0]
    k0_name = name(kid0)

    classname = attrs(tup_tree)['CLASSNAME']

    if k0_name == 'KEYVALUE' or k0_name == 'VALUE.REFERENCE':
        if len(kids(tup_tree)) != 1:
            raise ParseError('expected only one %s under %s' %
                             k0_name, name(tup_tree))

        # FIXME: This is probably not the best representation of these forms...
        val = parse_any(kid0)
        return CIMInstanceName(classname, {None: val})
    elif k0_name == 'KEYBINDING':
        kbs = {}
        for key_bind in list_of_various(tup_tree, ['KEYBINDING']):
            kbs.update(key_bind)
        return CIMInstanceName(classname, kbs)
    else:
        raise ParseError('unexpected node %s under %s' %
                         (name(kids(tup_tree)[0]), name(tup_tree)))


def parse_objectpath(tup_tree):
    """
    <!ELEMENT OBJECTPATH (INSTANCEPATH | CLASSPATH)>
    """

    check_node(tup_tree, 'OBJECTPATH')

    child = one_child(tup_tree, ['INSTANCEPATH', 'CLASSPATH'])

    return (name(tup_tree), attrs(tup_tree), child)



def parse_keybinding(tup_tree):
    ##<!ELEMENT KEYBINDING (KEYVALUE | VALUE.REFERENCE)>
    ##<!ATTLIST KEYBINDING
    ##  %CIMName;>

    """Returns one-item dictionary from name to Python value."""

    check_node(tup_tree, 'KEYBINDING', ['NAME'])

    child = one_child(tup_tree, ['KEYVALUE', 'VALUE.REFERENCE'])

    return {attrs(tup_tree)['NAME']: child}


def parse_keyvalue(tup_tree):
    ##<!ELEMENT KEYVALUE (#PCDATA)>
    ##<!ATTLIST KEYVALUE
    ##          VALUETYPE (string | boolean | numeric) "string"
    ##          %CIMType;              #IMPLIED>


    """Parse VALUETYPE into Python primitive value"""

    check_node(tup_tree, 'KEYVALUE', ['VALUETYPE'], ['TYPE'], [], True)

    pdta = pcdata(tup_tree)

    if 'VALUETYPE' not in attrs(tup_tree):
        return pdta

    val_type = attrs(tup_tree).get('VALUETYPE')

    if val_type == 'string':
        return pdta
    elif val_type == 'boolean':
        return unpack_boolean(pdta)
    elif val_type == 'numeric':

        try:
            # XXX: Use TYPE attribute to create named CIM type.
            # if 'TYPE' in attrs(tup_tree):
            #    return tocimobj(attrs(tup_tree)['TYPE'], p.strip())

            # XXX: Would like to use long() here, but that tends to cause
            # trouble when it's written back out as '2L'
            return int(pdta.strip())
        except ValueError:
            raise ParseError('invalid numeric %r under %s' %
                             (pdta, name(tup_tree)))
    else:
        raise ParseError('invalid VALUETYPE %s in %s' %
                         (val_type, name(tup_tree)))


#
# Object definition elements
#

def parse_class(tup_tree):
    """Parse CLASS element returning a CIMClass if the parse
       was successful.
    """
    ## <!ELEMENT CLASS (QUALIFIER*, (PROPERTY | PROPERTY.ARRAY |
    ##                               PROPERTY.REFERENCE)*, METHOD*)>
    ## <!ATTLIST CLASS
    ##     %CIMName;
    ##     %SuperClass;>

    # Doesn't check ordering of elements, but it's not very important
    check_node(tup_tree, 'CLASS', ['NAME'], ['SUPERCLASS'],
               ['QUALIFIER', 'PROPERTY', 'PROPERTY.REFERENCE',
                'PROPERTY.ARRAY', 'METHOD'])

    superclass = attrs(tup_tree).get('SUPERCLASS')

    # TODO: Return these as maps, not lists
    properties = byname(list_of_matching(tup_tree,
                                         ['PROPERTY',
                                          'PROPERTY.REFERENCE',
                                          'PROPERTY.ARRAY']))

    qualifiers = byname(list_of_matching(tup_tree, ['QUALIFIER']))
    methods = byname(list_of_matching(tup_tree, ['METHOD']))

    return CIMClass(attrs(tup_tree)['NAME'],
                    superclass=superclass,
                    properties=properties,
                    qualifiers=qualifiers,
                    methods=methods)


def parse_instance(tup_tree):
    """Return a CIMInstance.

    The instance contains the properties, qualifiers and classname for
    the instance"""

    ##<!ELEMENT INSTANCE (QUALIFIER*, (PROPERTY | PROPERTY.ARRAY |
    ##                                 PROPERTY.REFERENCE)*)>
    ##<!ATTLIST INSTANCE
    ##  %ClassName;>

    check_node(tup_tree, 'INSTANCE', ['CLASSNAME'],
               ['QUALIFIER', 'PROPERTY', 'PROPERTY.ARRAY',
                'PROPERTY.REFERENCE'])

    ## XXX: This does not enforce ordering constraint

    ## XXX: This does not enforce the constraint that there be only
    ## one PROPERTY or PROPERTY.ARRAY.

    ## TODO: Parse instance qualifiers
    qualifiers = {}
    props = list_of_matching(tup_tree, ['PROPERTY.REFERENCE', 'PROPERTY',
                                        'PROPERTY.ARRAY'])

    obj = CIMInstance(attrs(tup_tree)['CLASSNAME'], qualifiers=qualifiers)

    for prop in props:
        obj.__setitem__(prop.name, prop)

    return obj

def parse_scope(tup_tree):
    """Parse SCOPE element."""
    # <!ELEMENT SCOPE EMPTY>
    # <!ATTLIST SCOPE
    #   CLASS (true | false) "false"
    #   ASSOCIATION (true | false) "false"
    #   REFERENCE (true | false) "false"
    #   PROPERTY (true | false) "false"
    #   METHOD (true | false) "false"
    #   PARAMETER (true | false) "false"
    #   INDICATION (true | false) "false"
    check_node(tup_tree, 'SCOPE', [],
               ['CLASS', 'ASSOCIATION', 'REFERENCE', 'PROPERTY', 'METHOD',
                'PARAMETER', 'INDICATION'], [])
    return dict([(k, v.lower() == 'true') for k, v in attrs(tup_tree).items()])

def parse_qualifier_declaration(tup_tree):
    """Parse QUALIFIER.DECLARATION element"""
    ## <!ELEMENT QUALIFIER.DECLARATION (SCOPE?, (VALUE | VALUE.ARRAY)?)>
    ## <!ATTLIST QUALIFIER.DECLARATION
    ##     %CIMName;
    ##     %CIMType;               #REQUIRED
    ##     ISARRAY    (true|false) #IMPLIED
    ##     %ArraySize;
    ##     %QualifierFlavor;>

    check_node(tup_tree, 'QUALIFIER.DECLARATION',
               ['NAME', 'TYPE'],
               ['ISARRAY', 'ARRAYSIZE', 'OVERRIDABLE', 'TOSUBCLASS',
                'TOINSTANCE', 'TRANSLATABLE'],
               ['SCOPE', 'VALUE', 'VALUE.ARRAY'])

    attr = attrs(tup_tree)
    qname = attr['NAME']
    _type = attr['TYPE']
    try:
        is_array = attr['ISARRAY'].lower() == 'true'
    except KeyError:
        is_array = False
    try:
        array_size = int(attr['ARRAYSIZE'])
    except KeyError:
        array_size = None

    flavors = {}
    for flavor in ['OVERRIDABLE', 'TOSUBCLASS', 'TOINSTANCE', 'TRANSLATABLE']:
        try:
            flavors[flavor.lower()] = attr[flavor].lower() == 'true'
        except KeyError:
            pass

    scopes = None
    value = None
    for child in kids(tup_tree):
        if name(child) == 'SCOPE':
            if scopes is not None:
                raise ParseError("Multiple SCOPE tags encountered")
            scopes = parse_any(child)
        else:
            if value is not None:
                raise ParseError("Multiple VALUE/VALUE.ARRAY tags encountered")
            value = tocimobj(_type, parse_any(child))

    return CIMQualifierDeclaration(qname, _type, value, is_array,
                                   array_size, scopes, **flavors)


def parse_qualifier(tup_tree):
    """Parse QUALIFIER element returning CIMQualifier"""
    ## <!ELEMENT QUALIFIER (VALUE | VALUE.ARRAY)>
    ## <!ATTLIST QUALIFIER %CIMName;
    ##      %CIMType;              #REQUIRED
    ##      %Propagated;
    ##      %QualifierFlavor;>

    check_node(tup_tree, 'QUALIFIER', ['NAME', 'TYPE'],
               ['OVERRIDABLE', 'TOSUBCLASS', 'TOINSTANCE',
                'TRANSLATABLE', 'PROPAGATED'],
               ['VALUE', 'VALUE.ARRAY'])

    attrl = attrs(tup_tree)

    qual = CIMQualifier(attrl['NAME'], unpack_value(tup_tree),
                        type=attrl['TYPE'])

    ## TODO: Lift this out?
    for i in ['OVERRIDABLE', 'TOSUBCLASS', 'TOINSTANCE',
              'TRANSLATABLE', 'PROPAGATED']:
        rtn_val = attrl.get(i)
        if rtn_val not in ['true', 'false', None]:
            raise ParseError("invalid value %r for %s on %s" %
                             (rtn_val, i, name(tup_tree)))
        if rtn_val == 'true':
            rtn_val = True
        elif rtn_val == 'false':
            rtn_val = False

        setattr(qual, i.lower(), rtn_val)

    return qual


def parse_property(tup_tree):
    """Parse PROPERTY into a CIMProperty object.

    VAL is just the pcdata of the enclosed VALUE node."""

    ## <!ELEMENT PROPERTY (QUALIFIER*, VALUE?)>
    ## <!ATTLIST PROPERTY %CIMName;
    ##      %ClassOrigin;
    ##      %Propagated;
    ##      %CIMType;              #REQUIRED>
    ##      %EMBEDDEDOBJECT

    ## TODO: Parse this into NAME, VALUE, where the value contains
    ## magic fields for the qualifiers and the propagated flag.

    check_node(tup_tree, 'PROPERTY', ['TYPE', 'NAME'],
               ['NAME', 'CLASSORIGIN', 'PROPAGATED', 'EmbeddedObject',
                'EMBEDDEDOBJECT'],
               ['QUALIFIER', 'VALUE'])

    quals = {}
    for qual in list_of_matching(tup_tree, ['QUALIFIER']):
        quals[qual.name] = qual

    attrl = attrs(tup_tree)
    try:
        val = unpack_value(tup_tree)
    except ValueError as exc:
        msg = str(exc)
        raise ParseError('Cannot parse value for property "%s": %s' %\
                         (attrl['NAME'], msg))

    embedded_object = None
    if 'EmbeddedObject' in attrl or 'EMBEDDEDOBJECT' in attrl:
        try:
            embedded_object = attrl['EmbeddedObject']
        except KeyError:
            embedded_object = attrl['EMBEDDEDOBJECT']
    if embedded_object is not None:
        val = parse_embeddedObject(val)

    return CIMProperty(attrl['NAME'],
                       val,
                       attrl['TYPE'],
                       class_origin=attrl.get('CLASSORIGIN'),
                       propagated=unpack_boolean(attrl.get('PROPAGATED')),
                       qualifiers=quals,
                       embedded_object=embedded_object)


def parse_property_array(tup_tree):
    """
    <!ELEMENT PROPERTY.ARRAY (QUALIFIER*, VALUE.ARRAY?)>
    <!ATTLIST PROPERTY.ARRAY %CIMName;
         %CIMType;              #REQUIRED
         %ArraySize;
         %ClassOrigin;
         %Propagated;>
    """

    check_node(tup_tree, 'PROPERTY.ARRAY', ['NAME', 'TYPE'],
               ['REFERENCECLASS', 'CLASSORIGIN', 'PROPAGATED',
                'ARRAYSIZE', 'EmbeddedObject', 'EMBEDDEDOBJECT'],
               ['QUALIFIER', 'VALUE.ARRAY'])

    quals = {}
    for qual in list_of_matching(tup_tree, ['QUALIFIER']):
        quals[qual.name] = qual

    values = unpack_value(tup_tree)
    attrl = attrs(tup_tree)
    embedded_object = None
    if 'EmbeddedObject' in attrl or 'EMBEDDEDOBJECT' in attrl:
        try:
            embedded_object = attrl['EmbeddedObject']
        except KeyError:
            embedded_object = attrl['EMBEDDEDOBJECT']

    if embedded_object is not None:
        values = parse_embeddedObject(values)

    obj = CIMProperty(attrl['NAME'],
                      values,
                      attrl['TYPE'],
                      class_origin=attrl.get('CLASSORIGIN'),
                      qualifiers=quals,
                      is_array=True,
                      embedded_object=embedded_object)

    ## TODO: qualifiers, other attributes
    return obj


def parse_property_reference(tup_tree):
    """
    <!ELEMENT PROPERTY.REFERENCE (QUALIFIER*, (VALUE.REFERENCE)?)>
    <!ATTLIST PROPERTY.REFERENCE
        %CIMName;
        %ReferenceClass;
        %ClassOrigin;
        %Propagated;>
    """

    check_node(tup_tree, 'PROPERTY.REFERENCE', ['NAME'],
               ['REFERENCECLASS', 'CLASSORIGIN', 'PROPAGATED'])

    value = list_of_matching(tup_tree, ['VALUE.REFERENCE'])

    if value is None or len(value) == 0:
        value = None
    elif len(value) == 1:
        value = value[0]
    else:
        raise ParseError('Too many VALUE.REFERENCE elements.')

    attributes = attrs(tup_tree)
    pref = CIMProperty(attributes['NAME'], value, type='reference')

    for qual in list_of_matching(tup_tree, ['QUALIFIER']):
        pref.qualifiers[qual.name] = qual

    if 'REFERENCECLASS' in attributes:
        pref.reference_class = attributes['REFERENCECLASS']

    if 'CLASSORIGIN' in attributes:
        pref.class_origin = attributes['CLASSORIGIN']

    if 'PROPAGATED' in attributes:
        pref.propagated = attributes['PROPAGATED']

    return pref


def parse_method(tup_tree):
    """
    <!ELEMENT METHOD (QUALIFIER*, (PARAMETER | PARAMETER.REFERENCE |
                                   PARAMETER.ARRAY | PARAMETER.REFARRAY)*)>
    <!ATTLIST METHOD %CIMName;
         %CIMType;              #IMPLIED
         %ClassOrigin;
         %Propagated;>
    """

    check_node(tup_tree, 'METHOD', ['NAME'],
               ['TYPE', 'CLASSORIGIN', 'PROPAGATED'],
               ['QUALIFIER', 'PARAMETER', 'PARAMETER.REFERENCE',
                'PARAMETER.ARRAY', 'PARAMETER.REFARRAY'])

    qualifiers = byname(list_of_matching(tup_tree, ['QUALIFIER']))

    parameters = byname(list_of_matching(tup_tree, ['PARAMETER',
                                                    'PARAMETER.REFERENCE',
                                                    'PARAMETER.ARRAY',
                                                    'PARAMETER.REFARRAY',]))

    attrl = attrs(tup_tree)

    return CIMMethod(attrl['NAME'],
                     return_type=attrl.get('TYPE'),
                     parameters=parameters,
                     qualifiers=qualifiers,
                     class_origin=attrl.get('CLASSORIGIN'),
                     propagated=unpack_boolean(attrl.get('PROPAGATED')))


def parse_parameter(tup_tree):
    """
    <!ELEMENT PARAMETER (QUALIFIER*)>
    <!ATTLIST PARAMETER
         %CIMName;
         %CIMType;              #REQUIRED>
    """

    check_node(tup_tree, 'PARAMETER', ['NAME', 'TYPE'], [])

    quals = {}
    for qual in list_of_matching(tup_tree, ['QUALIFIER']):
        quals[qual.name] = qual

    attrl = attrs(tup_tree)

    return CIMParameter(attrl['NAME'], type=attrl['TYPE'],
                        qualifiers=quals)

def parse_parameter_reference(tup_tree):
    """
    <!ELEMENT PARAMETER.REFERENCE (QUALIFIER*)>
    <!ATTLIST PARAMETER.REFERENCE
        %CIMName;
        %ReferenceClass;>
    """

    check_node(tup_tree, 'PARAMETER.REFERENCE', ['NAME'], ['REFERENCECLASS'])

    quals = {}
    for qual in list_of_matching(tup_tree, ['QUALIFIER']):
        quals[qual.name] = qual

    attrl = attrs(tup_tree)

    return CIMParameter(attrl['NAME'],
                        type='reference',
                        reference_class=attrl.get('REFERENCECLASS'),
                        qualifiers=quals)


def parse_parameter_array(tup_tree):
    """
    <!ELEMENT PARAMETER.ARRAY (QUALIFIER*)>
    <!ATTLIST PARAMETER.ARRAY
         %CIMName;
         %CIMType;              #REQUIRED
         %ArraySize;>
    """

    check_node(tup_tree, 'PARAMETER.ARRAY', ['NAME', 'TYPE'],
               ['ARRAYSIZE'])

    quals = {}
    for qual in list_of_matching(tup_tree, ['QUALIFIER']):
        quals[qual.name] = qual

    attrl = attrs(tup_tree)

    array_size = attrl.get('ARRAYSIZE')
    if array_size is not None:
        array_size = int(array_size)

    return CIMParameter(attrl['NAME'],
                        type=attrl['TYPE'],
                        is_array=True,
                        array_size=array_size,
                        qualifiers=quals)


def parse_parameter_refarray(tup_tree):
    """
    <!ELEMENT PARAMETER.REFARRAY (QUALIFIER*)>
    <!ATTLIST PARAMETER.REFARRAY
        %CIMName;
        %ReferenceClass;
        %ArraySize;>
    """

    check_node(tup_tree, 'PARAMETER.REFARRAY', ['NAME'],
               ['REFERENCECLASS', 'ARRAYSIZE'])

    quals = {}
    for qual in list_of_matching(tup_tree, ['QUALIFIER']):
        quals[qual.name] = qual

    attr = attrs(tup_tree)

    array_size = attr.get('ARRAYSIZE')
    if array_size is not None:
        array_size = int(array_size)

    return CIMParameter(attr['NAME'], 'reference',
                        is_array=True,
                        reference_class=attr.get('REFERENCECLASS'),
                        array_size=array_size,
                        qualifiers=quals)


#
# Message elements
#

def parse_message(tup_tree):
    """
    <!ELEMENT MESSAGE (SIMPLEREQ | MULTIREQ | SIMPLERSP | MULTIRSP)>
    <!ATTLIST MESSAGE
        ID CDATA #REQUIRED
        PROTOCOLVERSION CDATA #REQUIRED>
    """

    check_node(tup_tree, 'MESSAGE', ['ID', 'PROTOCOLVERSION'])

    messages = one_child(
        tup_tree, ['SIMPLEREQ', 'MULTIREQ', 'SIMPLERSP', 'MULTIRSP',
                   'SIMPLEEXPREQ'])

    if not isinstance(messages, list):
        # make single and multi forms consistent
        messages = [messages]

    return name(tup_tree), attrs(tup_tree), messages


def parse_multireq(tup_tree):   #pylint: disable=unused-argument
    """Not Implemented"""
    # TODO: Implement MULTIREQ parser
    raise ParseError('MULTIREQ parser not implemented')


def parse_multiexpreq(tup_tree):   #pylint: disable=unused-argument
    """Not Implemented"""
    # TODO: Implement MULTIEXPREQ parser
    raise ParseError('MULTIEXPREQ parser not implemented')

def parse_simpleexpreq(tup_tree):
    """
    <!ELEMENT SIMPLEEXPREQ (EXPMETHODCALL)>
    """

    child = one_child(tup_tree, ['EXPMETHODCALL'])

    return name(tup_tree), attrs(tup_tree), child

def parse_simplereq(tup_tree):
    """
    <!ELEMENT SIMPLEREQ (IMETHODCALL | METHODCALL)>
    """

    check_node(tup_tree, 'SIMPLEREQ')

    child = one_child(tup_tree, ['IMETHODCALL', 'METHODCALL'])

    return name(tup_tree), attrs(tup_tree), child


def parse_imethodcall(tup_tree):
    """
    <!ELEMENT IMETHODCALL (LOCALNAMESPACEPATH, IPARAMVALUE*)>
    <!ATTLIST IMETHODCALL
        %CIMName;>
    """

    check_node(tup_tree, 'IMETHODCALL', ['NAME'])

    if len(kids(tup_tree)) < 1:
        raise ParseError('Expecting LOCALNAMESPACEPATH, got nothing')

    localnspath = parse_localnamespacepath(kids(tup_tree)[0])

    params = [parse_iparamvalue(x) for x in kids(tup_tree)[1:]]

    return (name(tup_tree), attrs(tup_tree), localnspath, params)


def parse_methodcall(tup_tree):
    """
    <!ELEMENT METHODCALL ((LOCALCLASSPATH|LOCALINSTANCEPATH),PARAMVALUE*)>
    <!ATTLIST METHODCALL
         %CIMName;>
    """

    check_node(tup_tree, 'METHODCALL', ['NAME'], [],
               ['LOCALCLASSPATH', 'LOCALINSTANCEPATH', 'PARAMVALUE'])
    path = list_of_matching(tup_tree, ['LOCALCLASSPATH', 'LOCALINSTANCEPATH'])
    if len(path) != 1:
        raise ParseError('Expecting one of LOCALCLASSPATH or ' \
                         'LOCALINSTANCEPATH, got %r' % path)
    path = path[0]
    params = list_of_matching(tup_tree, ['PARAMVALUE'])
    return (name(tup_tree), attrs(tup_tree), path, params)


def parse_expmethodcall(tup_tree):
    """
    <!ELEMENT EXPMETHODCALL (EXPPARAMVALUE*)>
    <!ATTLIST EXPMETHODCALL
        %CIMName;>
    """

    check_node(tup_tree, 'EXPMETHODCALL', ['NAME'], [], ['EXPPARAMVALUE'])


    params = list_of_matching(tup_tree, ['EXPPARAMVALUE'])

    return (name(tup_tree), attrs(tup_tree), params)


def parse_paramvalue(tup_tree):
    """Parse PARAMVALUE element """
    ## <!ELEMENT PARAMVALUE (VALUE | VALUE.REFERENCE | VALUE.ARRAY |
    ##                       VALUE.REFARRAY)?>
    ## <!ATTLIST PARAMVALUE
    ##   %CIMName;
    ##   %ParamType;  #IMPLIED
    ##   %EmbeddedObject;>

    ## Version 2.1.1 of the DTD lacks the %ParamType attribute but it
    ## is present in version 2.2.  Make it optional to be backwards
    ## compatible.

    check_node(tup_tree, 'PARAMVALUE', ['NAME'],
               ['PARAMTYPE', 'EmbeddedObject', 'EMBEDDEDOBJECT'])

    child = optional_child(tup_tree,
                           ['VALUE', 'VALUE.REFERENCE', 'VALUE.ARRAY',
                            'VALUE.REFARRAY',])

    if 'PARAMTYPE' in attrs(tup_tree):
        paramtype = attrs(tup_tree)['PARAMTYPE']
    else:
        paramtype = None

    #pylint: disable=line-too-long
    if 'EmbeddedObject' in attrs(tup_tree) or 'EMBEDDEDOBJECT' in attrs(tup_tree):
        child = parse_embeddedObject(child)

    return attrs(tup_tree)['NAME'], paramtype, child


def parse_iparamvalue(tup_tree):
    """
    Parse expected IPARAMVALUE element. I.e.
       ## <!ELEMENT IPARAMVALUE (VALUE | VALUE.ARRAY | VALUE.REFERENCE |
       ##                       INSTANCENAME | CLASSNAME |
       ##                       QUALIFIER.DECLARATION |
       ##                       CLASS | INSTANCE | VALUE.NAMEDINSTANCE)?>
       ## <!ATTLIST IPARAMVALUE %CIMName;>

       :return: NAME, VALUE pair.
    """

    check_node(tup_tree, 'IPARAMVALUE', ['NAME'], [])

    child = optional_child(tup_tree,
                           ['VALUE', 'VALUE.ARRAY', 'VALUE.REFERENCE',
                            'INSTANCENAME', 'CLASSNAME',
                            'QUALIFIER.DECLARATION', 'CLASS', 'INSTANCE',
                            'VALUE.NAMEDINSTANCE'])

    _name = attrs(tup_tree)['NAME']
    if isinstance(child, six.string_types) and \
            _name.lower() in ['deepinheritance', 'localonly',
                              'includequalifiers', 'includeclassorigin']:
        if child.lower() in ['true', 'false']:
            child = (child.lower() == 'true')

    return _name, child


def parse_expparamvalue(tup_tree):
    """Parse for EXPPARMVALUE Element. I.e.
    <!ELEMENT EXPPARAMVALUE (INSTANCE?)>
    <!ATTLIST EXPPARAMVALUE
        %CIMName;>
    """

    check_node(tup_tree, 'EXPPARAMVALUE', ['NAME'], [], ['INSTANCE'])

    child = optional_child(tup_tree, ['INSTANCE'])

    _name = attrs(tup_tree)['NAME']
    return _name, child


def parse_multirsp(tup_tree):   #pylint: disable=unused-argument
    """This Function not implemented"""
    # TODO: Implement MULTIRSP parser
    raise ParseError('MULTIRSP parser not implemented')


def parse_multiexprsp(tup_tree):   #pylint: disable=unused-argument
    """This Function not implemented"""
    # TODO: Implement MULTIEXPRSP parser
    raise ParseError('MULTIEXPRSP parser not implemented')


def parse_simplersp(tup_tree):
    """Parse for SIMPLERSP Element"""
    ## <!ELEMENT SIMPLERSP (METHODRESPONSE | IMETHODRESPONSE)>
    check_node(tup_tree, 'SIMPLERSP', [], [])

    child = one_child(tup_tree, ['METHODRESPONSE', 'IMETHODRESPONSE'])

    return name(tup_tree), attrs(tup_tree), child


def parse_simpleexprsp(tup_tree):   #pylint: disable=unused-argument
    """This Function not implemented"""
    # TODO: Implement SIMPLEEXPRSP parser
    raise ParseError('SIMPLEEXPRSP parser not implemented')


def parse_methodresponse(tup_tree):
    """Parse expected METHODRESPONSE ELEMENT. I.e.
        <!ELEMENT METHODRESPONSE (ERROR | (RETURNVALUE?, PARAMVALUE*))>
            <!ATTLIST METHODRESPONSE
                %CIMName;>
    """

    check_node(tup_tree, 'METHODRESPONSE', ['NAME'], [])

    return name(tup_tree), attrs(tup_tree), list_of_various(tup_tree,
                                                            ['ERROR',
                                                             'RETURNVALUE',
                                                             'PARAMVALUE'])


def parse_expmethodresponse(tup_tree):  #pylint: disable=unused-argument
    """This function not implemented"""
    # TODO: Implement EXPMETHODRESPONSE parser
    raise ParseError('EXPMETHODRESPONSE parser not implemented')


def parse_imethodresponse(tup_tree):
    """Parse the tuple for an IMETHODRESPONE Element. I.e.
        <!ELEMENT IMETHODRESPONSE (ERROR | IRETURNVALUE?)>
        <!ATTLIST IMETHODRESPONSE %CIMName;>
    """

    check_node(tup_tree, 'IMETHODRESPONSE', ['NAME'], [])

    return name(tup_tree), attrs(tup_tree), optional_child(tup_tree,
                                                           ['ERROR',
                                                            'IRETURNVALUE'])


def parse_error(tup_tree):
    """Parse ERROR element to get CODE and DESCRIPTION.
    <!ELEMENT ERROR EMPTY>
    <!ATTLIST ERROR
        CODE CDATA #REQUIRED
        DESCRIPTION CDATA #IMPLIED>
    """

    ## TODO: Return a CIMError object, not a tuple

    check_node(tup_tree, 'ERROR', ['CODE'], ['DESCRIPTION'])

    return (name(tup_tree), attrs(tup_tree), None)


def parse_returnvalue(tup_tree):
    """Parse the RETURNVALUE element. Returns name, attributes, and
       one child as a tuple.
    """
    ## <!ELEMENT RETURNVALUE (VALUE | VALUE.ARRAY | VALUE.REFERENCE |
    ##                        VALUE.REFARRAY)>
    ## <!ATTLIST RETURNVALUE %ParamType;       #IMPLIED>

    ## Version 2.1.1 of the DTD lacks the %ParamType attribute but it
    ## is present in version 2.2.  Make it optional to be backwards
    ## compatible.

    check_node(tup_tree, 'RETURNVALUE', [], ['PARAMTYPE'])

    return name(tup_tree), attrs(tup_tree), one_child(tup_tree,
                                                      ['VALUE',
                                                       'VALUE.ARRAY',
                                                       'VALUE.REFERENCE',
                                                       'VALUE.REFARRAY'])

def parse_ireturnvalue(tup_tree):
    """Parse IRETURNVALUE element. Returns name, attributes and
       values of the tup_tree.
    """
    ## <!ELEMENT IRETURNVALUE (CLASSNAME* | INSTANCENAME* | VALUE* |
    ##                         VALUE.OBJECTWITHPATH* |
    ##                         VALUE.OBJECTWITHLOCALPATH* | VALUE.OBJECT* |
    ##                         OBJECTPATH* | QUALIFIER.DECLARATION* |
    ##                         VALUE.ARRAY? | VALUE.REFERENCE? | CLASS* |
    ##                         INSTANCE* | VALUE.NAMEDINSTANCE*)>

    check_node(tup_tree, 'IRETURNVALUE', [], [])

    # XXX: doesn't prohibit the case of only one VALUE.ARRAY or
    # VALUE.REFERENCE.  But why is that required?  Why can it return
    # multiple VALUEs but not multiple VALUE.REFERENCEs?

    values = list_of_same(tup_tree, ['CLASSNAME', 'INSTANCENAME',
                                     'VALUE', 'VALUE.OBJECTWITHPATH',
                                     'VALUE.OBJECT', 'OBJECTPATH',
                                     'QUALIFIER.DECLARATION',
                                     'VALUE.ARRAY', 'VALUE.REFERENCE',
                                     'CLASS', 'INSTANCE',
                                     'VALUE.NAMEDINSTANCE',])

    ## TODO: Call unpack_value if appropriate

    return name(tup_tree), attrs(tup_tree), values

#
# Object naming and locating elements
#

def parse_any(tup_tree):
    """Parse a fragment of XML. This function drives the rest of
       the parser by calling 'parse_*' functions based on the name
       of the element being parsed.

       It builds parser function name from incoming name in tup_tree
       prepended with 'parse_' and calls that function.

    Return is determined by function called.
    """

    nodename = name(tup_tree).lower().replace('.', '_')
    fn_name = 'parse_' + nodename
    funct_name = globals().get(fn_name)
    if funct_name is None:
        raise ParseError('no parser for node type %s' % name(tup_tree))
    else:
        return funct_name(tup_tree)

def parse_embeddedObject(val): # pylint: disable=invalid-name
    """Parse and embedded instance or class and return the
       CIMInstance or CIMClass

       :return: None if val is None. Returns either CIMClass or
           CIMInstance or a list of them

       :Raises: ParseError if there is an error in the XML
    """

    if isinstance(val, list):
        return [parse_embeddedObject(obj) for obj in val]
    if val is None:
        return None
    tuptree = xml_to_tupletree(val)
    if tuptree[0] == 'INSTANCE':
        return parse_instance(tuptree)
    elif tuptree[0] == 'CLASS':
        return parse_class(tuptree)
    else:
        raise ParseError('Error parsing embedded object')


def unpack_value(tup_tree):
    """Find VALUE or VALUE.ARRAY under tup_tree and convert to a
    Python value.

    Looks at the TYPE of the node to work out how to decode it.
    Handles nodes with no value (e.g. in CLASS.)
    """
    ## TODO: Handle VALUE.REFERENCE, VALUE.REFARRAY

    valtype = attrs(tup_tree)['TYPE']

    raw_val = list_of_matching(tup_tree, ['VALUE', 'VALUE.ARRAY'])
    if len(raw_val) == 0:
        return None
    elif len(raw_val) > 1:
        raise ParseError('more than one VALUE or VALUE.ARRAY under %s' % \
                         name(tup_tree))

    raw_val = raw_val[0]

    if isinstance(raw_val, list):
        return [tocimobj(valtype, x) for x in raw_val]
    elif len(raw_val) == 0 and valtype != 'string':
        return None
    else:
        return tocimobj(valtype, raw_val)

def unpack_boolean(data):
    """Unpack a boolean, represented as "TRUE" or "FALSE" in CIM."""
    if data is None:
        return None

    ## CIM-XML says "These values MUST be treated as case-insensitive"
    ## (even though the XML definition requires them to be lowercase.)

    data = data.strip().lower()                   # ignore space
    if data == 'true':
        return True
    elif data == 'false':
        return False
    elif data == '':
        return None
    else:
        raise ParseError('invalid boolean %r' % data)
