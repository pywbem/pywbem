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

# Implementation:
#
# This works by a recursive descent down the CIM XML tupletree.  As we walk
# down, we produce cim_obj and cim_type objects representing the CIM message
# in digested form.
#
# For each XML node type FOO there is one function parse_foo, which
# returns the digested form by examining a tuple tree rooted at FOO.
#
# The resulting objects are constrained to the shape of the CIM XML
# tree: if one node in XML contains another, then the corresponding
# CIM object will contain the second.  However, there can be local
# transformations at each node: some levels are ommitted, some are
# transformed into lists or hashes.
#
# We try to validate that the tree is well-formed too.  The validation
# is more strict than the DTD, but it is forgiving of implementation
# quirks and bugs in Pegasus.
#
# Bear in mind in the parse functions that each tupletree tuple is
# structured as
#
#   tup_tree[0]: name string             == name(tup_tree)
#   tup_tree[1]: hash of attributes      == attrs(tup_tree)
#   tup_tree[2]: sequence of children    == kids(tup_tree)
#
# Note: This layer is inconsistent in what it returns: In some places it
# returns tupletrees, and in others Python objects. This is likely staying that
# way in the future.
#
# Note: Some attributes have defined values or formats, such as NAME of a CLASS
# or EMBEDDEDOBJECT. This layer does not check the values or formats. CIM
# names are not being checked on the client side at all (when receiving names
# that is not worthwhile at all, and when sending names the server will
# reject them if there is a problem). Enumerated values may be checked at
# higher levels.

# This module is meant to be safe for 'import *'.

from __future__ import absolute_import
import six
try:
    from collections import OrderedDict
except ImportError:
    from ordereddict import OrderedDict

from .cim_obj import CIMInstance, CIMInstanceName, CIMClass, CIMClassName, \
    CIMProperty, CIMMethod, CIMParameter, CIMQualifier, \
    CIMQualifierDeclaration, tocimobj, byname
from .tupletree import xml_to_tupletree_sax
from .exceptions import ParseError

__all__ = []


def filter_tuples(list_):
    """Return only the tuples in a list.

    In a tupletree, tuples correspond to XML elements.  Useful for
    stripping out whitespace data in a child list."""

    return [] if list_ is None else [x for x in list_ if isinstance(x, tuple)]


def pcdata(tup_tree):
    """Return the concatenated character data within a tup_tree.

    The tup_tree must not have non-character children."""
    for inst in tup_tree[2]:
        if not isinstance(inst, six.string_types):
            raise ParseError("Element %r has unexpected child elements: %r"
                             "(allowed is only text content)" %
                             (name(tup_tree), inst))
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
def check_node(tup_tree, nodename, required_attrs=None, optional_attrs=None,
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
        raise ParseError("Unexpected element %r (expected element %r)" %
                         (name(tup_tree), nodename))

    # Check we have all the required attributes, and no unexpected ones
    tt_attrs = {}
    if attrs(tup_tree) is not None:
        tt_attrs = attrs(tup_tree).copy()

    if required_attrs:
        for attr in required_attrs:
            if attr not in tt_attrs:
                raise ParseError("Element %r misses required attribute %r "
                                 "(only has attributes %r)" %
                                 (name(tup_tree), attr, attrs(tup_tree).keys()))
            del tt_attrs[attr]

    if optional_attrs:
        for attr in optional_attrs:
            if attr in tt_attrs:
                del tt_attrs[attr]

    for k in tt_attrs.keys():
        raise ParseError("Element %r has invalid attribute %r " %
                         (name(tup_tree), k))

    if allowed_children is not None:
        for child in kids(tup_tree):
            if name(child) not in allowed_children:
                raise ParseError("Element %r has invalid child element %r "
                                 "(allowed are child elements %r)" %
                                 (name(tup_tree), name(child),
                                  allowed_children))

    if not allow_pcdata:
        for child in tup_tree[2]:
            if isinstance(child, six.string_types):
                if child.lstrip(' \t\n') != '':
                    raise ParseError("Element %r has unexpected non-blank "
                                     "text content %r" %
                                     (name(tup_tree), child))


def one_child(tup_tree, acceptable):
    """Parse children of a node with exactly one child node.

    PCData is ignored.
    """

    k = kids(tup_tree)

    if len(k) == 0:
        raise ParseError("Element %r misses required child element %r" %
                         (name(tup_tree), acceptable))
    if len(k) > 1:
        raise ParseError("Element %r has too many child elements %r "
                         "(allowed is one child element %r)" %
                         (name(tup_tree), [name(t) for t in k], acceptable))

    child = k[0]

    if name(child) not in acceptable:
        raise ParseError("Element %s has invalid child element %r "
                         "(allowed is one child element %r)" %
                         (name(tup_tree), name(child), acceptable))

    return parse_any(child)


def optional_child(tup_tree, allowed):
    """Parse exactly zero or one of a list of elements from the
    child nodes."""

    k = kids(tup_tree)

    if len(k) > 1:
        raise ParseError("Element %r has too many child elements %r "
                         "(allowed is one optional child element %r)" %
                         (name(tup_tree), [name(t) for t in k], allowed))
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
            raise ParseError("Element %r has invalid child element %r "
                             "(allowed are child elements %r)" %
                             (name(tup_tree), name(child), acceptable))
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

    k = kids(tup_tree)

    if not k:            # empty list, consistent with list_of_various
        return []

    a_child = name(k[0])
    if a_child not in acceptable:
        raise ParseError("Element %r has invalid child element %r "
                         "(allowed is a sequence of like elements from %r)" %
                         (name(tup_tree), a_child, acceptable))
    result = []
    for child in k:
        if name(child) != a_child:
            raise ParseError("Element %r has invalid child element %r "
                             "(sequence must have like elements %r)" %
                             (name(tup_tree), name(child), a_child))
        result.append(parse_any(child))

    return result


def notimplemented(tup_tree):
    """raise exception for notimplemented function"""
    raise ParseError("Internal Error: Parsing support for element %r is not "
                     "implemented" % name(tup_tree))

#
# Root element
#


def parse_cim(tup_tree):
    """Parse the top level element of CIM/XML message

      ::

        <!ELEMENT CIM (MESSAGE | DECLARATION)>
        <!ATTLIST CIM
            CIMVERSION CDATA #REQUIRED
            DTDVERSION CDATA #REQUIRED>
    """

    check_node(tup_tree, 'CIM', ['CIMVERSION', 'DTDVERSION'])

    if not attrs(tup_tree)['CIMVERSION'].startswith('2.'):
        raise ParseError("CIMVERSION is %s, expected 2.x.y" %
                         attrs(tup_tree)['CIMVERSION'])

    child = one_child(tup_tree, ['MESSAGE', 'DECLARATION'])

    return name(tup_tree), attrs(tup_tree), child


#
# Declaration elements
#

def parse_declaration(tup_tree):
    """
      ::

        <!ELEMENT DECLARATION ( DECLGROUP | DECLGROUP.WITHNAME |
                                DECLGROUP.WITHPATH )+>

    Note: We only support the DECLGROUP child, at this point.
    """

    check_node(tup_tree, 'DECLARATION')

    child = one_child(tup_tree, ['DECLGROUP'])

    return name(tup_tree), attrs(tup_tree), child


def parse_declgroup(tup_tree):
    """
      ::

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
    """Return VALUE contents as a string

      ::

        <!ELEMENT VALUE (#PCDATA)>
    """

    check_node(tup_tree, 'VALUE', [], [], [], True)

    return pcdata(tup_tree)


def parse_value_array(tup_tree):
    """Return list of strings.

      ::

        <!ELEMENT VALUE.ARRAY (VALUE*)>
    """

    check_node(tup_tree, 'VALUE.ARRAY', [], [], ['VALUE'])

    return list_of_same(tup_tree, ['VALUE'])


def parse_value_reference(tup_tree):
    """
      ::

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
      ::

        <!ELEMENT VALUE.REFARRAY (VALUE.REFERENCE*)>
    """

    check_node(tup_tree, 'VALUE.REFARRAY')

    children = list_of_various(tup_tree, ['VALUE.REFERENCE'])

    # The VALUE.REFARRAY wrapper element is discarded
    return children


def parse_value_object(tup_tree):
    """
      ::

        <!ELEMENT VALUE.OBJECT (CLASS | INSTANCE)>
    """

    check_node(tup_tree, 'VALUE.OBJECT')

    child = one_child(tup_tree, ['CLASS', 'INSTANCE'])

    return (name(tup_tree), attrs(tup_tree), child)


def parse_value_namedinstance(tup_tree):
    """
      ::

        <!ELEMENT VALUE.NAMEDINSTANCE (INSTANCENAME, INSTANCE)>
    """

    check_node(tup_tree, 'VALUE.NAMEDINSTANCE')

    k = kids(tup_tree)
    if len(k) != 2:
        raise ParseError("Element %r has invalid number of child elements %r "
                         "(expecting two child elements "
                         "(INSTANCENAME, INSTANCE))" %
                         (name(tup_tree), k))

    instancename = parse_instancename(k[0])
    instance = parse_instance(k[1])

    instance.path = instancename

    return instance


def parse_value_instancewithpath(tup_tree):
    """
    The VALUE.INSTANCEWITHPATH is used to define a value that comprises
    a single CIMInstance with additional information that defines the
    absolute path to that object.

      ::

        <!ELEMENT VALUE.INSTANCEWITHPATH (INSTANCEPATH, INSTANCE)>
    """

    check_node(tup_tree, 'VALUE.INSTANCEWITHPATH')

    k = kids(tup_tree)
    if len(k) != 2:
        raise ParseError("Element %r has invalid number of child elements %r "
                         "(expecting two child elements "
                         "(INSTANCEPATH, INSTANCE))" %
                         (name(tup_tree), k))
    path = parse_instancepath(k[0])
    instance = parse_instance(k[1])

    instance.path = path
    return (instance)


def parse_value_namedobject(tup_tree):
    """
      ::

        <!ELEMENT VALUE.NAMEDOBJECT (CLASS | (INSTANCENAME, INSTANCE))>
    """

    check_node(tup_tree, 'VALUE.NAMEDOBJECT')

    k = kids(tup_tree)
    if len(k) == 1:
        _object = parse_class(k[0])
    elif len(k) == 2:
        path = parse_instancename(kids(tup_tree)[0])

        # redefines _object from pywbem.cim_obj.CIMClass to ...CIMInstance
        _object = parse_instance(kids(tup_tree)[1])

        _object.path = path
    else:
        raise ParseError("Element %r has invalid number of child elements %r "
                         "(expecting one or two child elements "
                         "(CLASS | (INSTANCENAME, INSTANCE)))" %
                         (name(tup_tree), k))

    return (name(tup_tree), attrs(tup_tree), _object)


# pylint: disable=invalid-name
def parse_value_objectwithlocalpath(tup_tree):
    """
      ::

        <!ELEMENT VALUE.OBJECTWITHLOCALPATH ((LOCALCLASSPATH, CLASS) |
                                             (LOCALINSTANCEPATH, INSTANCE))>
    """

    check_node(tup_tree, 'VALUE.OBJECTWITHLOCALPATH')

    k = kids(tup_tree)

    if len(k) != 2:
        raise ParseError("Element %r has invalid number of child elements %r "
                         "(expecting two child elements "
                         "((LOCALCLASSPATH, CLASS) | (LOCALINSTANCEPATH, "
                         "INSTANCE)))" %
                         (name(tup_tree), k))

    if name(k[0]) == 'LOCALCLASSPATH':
        _object = (parse_localclasspath(k[0]),
                   parse_class(k[1]))
    else:
        path = parse_localinstancepath(k[0])
        # redefines _object from tuple to CIMInstance
        _object = parse_instance(k[1])
        _object.path = path

    return (name(tup_tree), attrs(tup_tree), _object)


def parse_value_objectwithpath(tup_tree):
    """
      ::

        <!ELEMENT VALUE.OBJECTWITHPATH ((CLASSPATH, CLASS) |
                                        (INSTANCEPATH, INSTANCE))>
    """

    check_node(tup_tree, 'VALUE.OBJECTWITHPATH')

    k = kids(tup_tree)

    if len(k) != 2:
        raise ParseError("Element %r has invalid number of child elements %r "
                         "(expecting two child elements "
                         "((CLASSPATH, CLASS) | (INSTANCEPATH, INSTANCE)))" %
                         (name(tup_tree), k))

    if name(k[0]) == 'CLASSPATH':
        _object = (parse_classpath(k[0]), parse_class(k[1]))
    else:
        path = parse_instancepath(k[0])
        # redefines _object from tuple to CIMInstance
        _object = parse_instance(k[1])
        _object.path = path

    return (name(tup_tree), attrs(tup_tree), _object)


#
# Object naming and locating elements
#


def parse_namespacepath(tup_tree):
    """
      ::

        <!ELEMENT NAMESPACEPATH (HOST, LOCALNAMESPACEPATH)>
    """

    check_node(tup_tree, 'NAMESPACEPATH')

    k = kids(tup_tree)

    if len(k) != 2:
        raise ParseError("Element %r has invalid number of child elements %r "
                         "(expecting two child elements "
                         "(HOST, LOCALNAMESPACEPATH))" %
                         (name(tup_tree), k))

    host = parse_host(k[0])
    localnspath = parse_localnamespacepath(k[1])

    return (host, localnspath)


def parse_localnamespacepath(tup_tree):
    """
      ::

        <!ELEMENT LOCALNAMESPACEPATH (NAMESPACE+)>
    """

    check_node(tup_tree, 'LOCALNAMESPACEPATH', [], [], ['NAMESPACE'])

    if not kids(tup_tree):
        raise ParseError("Element %r misses child elements "
                         "(expecting one or more child elements 'NAMESPACE')" %
                         name(tup_tree))

    ns_list = list_of_various(tup_tree, ['NAMESPACE'])

    return '/'.join(ns_list)


def parse_host(tup_tree):
    """
      ::

        <!ELEMENT HOST (#PCDATA)>
    """

    check_node(tup_tree, 'HOST', allow_pcdata=True)

    return pcdata(tup_tree)


def parse_namespace(tup_tree):
    """Parse NAMESPACE element for namespace name

      ::

        <!ELEMENT NAMESPACE EMPTY>
        <!ATTLIST NAMESPACE
            %CIMName;>
    """

    check_node(tup_tree, 'NAMESPACE', ['NAME'], [], [])

    return attrs(tup_tree)['NAME']


def parse_classpath(tup_tree):
    """
      ::

        <!ELEMENT CLASSPATH (NAMESPACEPATH, CLASSNAME)>
    """

    check_node(tup_tree, 'CLASSPATH')

    k = kids(tup_tree)

    if len(k) != 2:
        raise ParseError("Element %r has invalid number of child elements %r "
                         "(expecting two child elements "
                         "(NAMESPACEPATH, CLASSNAME))" %
                         (name(tup_tree), k))

    nspath = parse_namespacepath(k[0])
    classname = parse_classname(k[1])

    return CIMClassName(classname.classname,
                        host=nspath[0], namespace=nspath[1])


def parse_localclasspath(tup_tree):
    """
      ::

        <!ELEMENT LOCALCLASSPATH (LOCALNAMESPACEPATH, CLASSNAME)>
    """

    check_node(tup_tree, 'LOCALCLASSPATH')

    k = kids(tup_tree)

    if len(k) != 2:
        raise ParseError("Element %r has invalid number of child elements %r "
                         "(expecting two child elements "
                         "(LOCALNAMESPACEPATH, CLASSNAME))" %
                         (name(tup_tree), k))

    localnspath = parse_localnamespacepath(k[0])
    classname = parse_classname(k[1])

    return CIMClassName(classname.classname, namespace=localnspath)


def parse_classname(tup_tree):
    """Parse a CLASSNAME element and return a CIMClassName.

      ::

        <!ELEMENT CLASSNAME EMPTY>
        <!ATTLIST CLASSNAME
            %CIMName;>
    """

    check_node(tup_tree, 'CLASSNAME', ['NAME'], [], [])
    return CIMClassName(attrs(tup_tree)['NAME'])


def parse_instancepath(tup_tree):
    """Parse a INSTANCEPATH element returning the instance name.

      ::

        <!ELEMENT INSTANCEPATH (NAMESPACEPATH, INSTANCENAME)>
    """

    check_node(tup_tree, 'INSTANCEPATH')

    k = kids(tup_tree)

    if len(k) != 2:
        raise ParseError("Element %r has invalid number of child elements %r "
                         "(expecting two child elements "
                         "(NAMESPACEPATH, INSTANCENAME))" %
                         (name(tup_tree), k))

    nspath = parse_namespacepath(k[0])
    instancename = parse_instancename(k[1])

    instancename.host = nspath[0]
    instancename.namespace = nspath[1]

    return instancename


def parse_localinstancepath(tup_tree):
    """Parse a LOCALINSTANCEPATH element:

      ::

        <!ELEMENT LOCALINSTANCEPATH (LOCALNAMESPACEPATH, INSTANCENAME)>
    """

    check_node(tup_tree, 'LOCALINSTANCEPATH')

    k = kids(tup_tree)

    if len(k) != 2:
        raise ParseError("Element %r has invalid number of child elements %r "
                         "(expecting two child elements "
                         "(LOCALNAMESPACEPATH, INSTANCENAME))" %
                         (name(tup_tree), k))

    localnspath = parse_localnamespacepath(k[0])
    instancename = parse_instancename(k[1])

    instancename.namespace = localnspath

    return instancename


def parse_instancename(tup_tree):
    """Parse XML INSTANCENAME into CIMInstanceName object.

      ::

        <!ELEMENT INSTANCENAME (KEYBINDING* | KEYVALUE? | VALUE.REFERENCE?)>
        <!ATTLIST INSTANCENAME
            %ClassName;>
    """

    check_node(tup_tree, 'INSTANCENAME', ['CLASSNAME'])

    if not kids(tup_tree):
        # probably not ever going to see this, but it's valid
        # according to the grammar
        return CIMInstanceName(attrs(tup_tree)['CLASSNAME'], {})

    kid0 = kids(tup_tree)[0]
    k0_name = name(kid0)

    classname = attrs(tup_tree)['CLASSNAME']

    if k0_name == 'KEYVALUE' or k0_name == 'VALUE.REFERENCE':
        if len(kids(tup_tree)) != 1:
            raise ParseError("Element %r has more than one child element %r "
                             "(expecting child elements "
                             "(KEYBINDING* | KEYVALUE? | VALUE.REFERENCE?))" %
                             (name(tup_tree), k0_name))

        # TODO: This is probably not the best representation of these forms...
        # it may be we have a bug here, it is suspicious that the result of a
        # parse...() function is used directly as a keybinding value. Also not
        # clear why key name is not set. Need to extend the testclient test
        # cases to make sure we go through all cases of INSTANCENAME parsing
        # (e.g. GetInstance on association instance).
        val = parse_any(kid0)
        return CIMInstanceName(classname, {None: val})
    elif k0_name == 'KEYBINDING':
        kbs = {}
        for key_bind in list_of_various(tup_tree, ['KEYBINDING']):
            kbs.update(key_bind)
        return CIMInstanceName(classname, kbs)
    else:
        raise ParseError("Element %r has invalid child elements %r "
                         "(expecting child elements "
                         "(KEYBINDING* | KEYVALUE? | VALUE.REFERENCE?))" %
                         (name(tup_tree), kids(tup_tree)))


def parse_objectpath(tup_tree):
    """
      ::

        <!ELEMENT OBJECTPATH (INSTANCEPATH | CLASSPATH)>
    """

    check_node(tup_tree, 'OBJECTPATH')

    child = one_child(tup_tree, ['INSTANCEPATH', 'CLASSPATH'])

    return (name(tup_tree), attrs(tup_tree), child)


def parse_keybinding(tup_tree):
    """Returns one-item dictionary from name to Python value.

      ::

        <!ELEMENT KEYBINDING (KEYVALUE | VALUE.REFERENCE)>
        <!ATTLIST KEYBINDING
            %CIMName;>
    """

    check_node(tup_tree, 'KEYBINDING', ['NAME'])

    child = one_child(tup_tree, ['KEYVALUE', 'VALUE.REFERENCE'])

    return {attrs(tup_tree)['NAME']: child}


def parse_keyvalue(tup_tree):
    """Parse VALUETYPE into Python primitive value.

      ::

        <!ELEMENT KEYVALUE (#PCDATA)>
        <!ATTLIST KEYVALUE
            VALUETYPE (string | boolean | numeric) "string"
            %CIMType;              #IMPLIED>
    """

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

            # TODO: Use TYPE attribute to create CIM typed value, e.g.:
            #   if 'TYPE' in attrs(tup_tree):
            #      return cimvalue(p.strip(), attrs(tup_tree)['TYPE'])
            # This also solves the issue that int in Py2 cannot represent the
            # longer CIM numeric types.
            return int(pdta.strip())

        except ValueError:
            raise ParseError("Element %r has invalid numeric content %r" %
                             (name(tup_tree), pdta))
    else:
        raise ParseError("Element %r has invalid 'VALUETYPE' attribute value "
                         "%r" %
                         (name(tup_tree), val_type))


#
# Object definition elements
#


def parse_class(tup_tree):
    """Parse CLASS element returning a CIMClass if the parse
       was successful.

      ::

        <!ELEMENT CLASS (QUALIFIER*, (PROPERTY | PROPERTY.ARRAY |
                                      PROPERTY.REFERENCE)*, METHOD*)>
        <!ATTLIST CLASS
            %CIMName;
            %SuperClass;>
    """

    # Doesn't check ordering of elements, but it's not very important
    check_node(tup_tree, 'CLASS', ['NAME'], ['SUPERCLASS'],
               ['QUALIFIER', 'PROPERTY', 'PROPERTY.REFERENCE',
                'PROPERTY.ARRAY', 'METHOD'])

    superclass = attrs(tup_tree).get('SUPERCLASS')

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
    the instance.

      ::

        <!ELEMENT INSTANCE (QUALIFIER*, (PROPERTY | PROPERTY.ARRAY |
                                         PROPERTY.REFERENCE)*)>
        <!ATTLIST INSTANCE
            %ClassName;>
    """

    check_node(tup_tree, 'INSTANCE', ['CLASSNAME'],
               ['QUALIFIER', 'PROPERTY', 'PROPERTY.ARRAY',
                'PROPERTY.REFERENCE'])

    # Note: The check above does not enforce the ordering constraint in the DTD
    # that QUALIFIER elements must appear before PROPERTY* elements.

    # TODO: Add support for qualifiers (on instances)
    qualifiers = {}

    props = list_of_matching(tup_tree, ['PROPERTY.REFERENCE', 'PROPERTY',
                                        'PROPERTY.ARRAY'])

    obj = CIMInstance(attrs(tup_tree)['CLASSNAME'], qualifiers=qualifiers)

    for prop in props:
        obj.__setitem__(prop.name, prop)

    return obj


def parse_scope(tup_tree):
    """Parse SCOPE element.

      ::

        <!ELEMENT SCOPE EMPTY>
        <!ATTLIST SCOPE
            CLASS (true | false) "false"
            ASSOCIATION (true | false) "false"
            REFERENCE (true | false) "false"
            PROPERTY (true | false) "false"
            METHOD (true | false) "false"
            PARAMETER (true | false) "false"
            INDICATION (true | false) "false"
    """

    check_node(tup_tree, 'SCOPE', [],
               ['CLASS', 'ASSOCIATION', 'REFERENCE', 'PROPERTY', 'METHOD',
                'PARAMETER', 'INDICATION'], [])
    return OrderedDict([(k, v.lower() == 'true')
                        for k, v in attrs(tup_tree).items()])


def parse_qualifier_declaration(tup_tree):
    """Parse QUALIFIER.DECLARATION element.

      ::

        <!ELEMENT QUALIFIER.DECLARATION (SCOPE?, (VALUE | VALUE.ARRAY)?)>
        <!ATTLIST QUALIFIER.DECLARATION
            %CIMName;
            %CIMType;               #REQUIRED
            ISARRAY    (true|false) #IMPLIED
            %ArraySize;
            %QualifierFlavor;>
    """

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
                raise ParseError("Element %r has more than one child element "
                                 "%r (allowed is only one)" %
                                 (name(tup_tree), name(child)))
            scopes = parse_any(child)
        else:
            if value is not None:
                raise ParseError("Element %r has more than one child element "
                                 "%r (allowed is only one)" %
                                 (name(tup_tree), name(child)))
            value = tocimobj(_type, parse_any(child))

    return CIMQualifierDeclaration(qname, _type, value, is_array,
                                   array_size, scopes, **flavors)


def parse_qualifier(tup_tree):
    """Parse QUALIFIER element returning CIMQualifier.

      ::

        <!ELEMENT QUALIFIER (VALUE | VALUE.ARRAY)>
        <!ATTLIST QUALIFIER
            %CIMName;
            %CIMType;              #REQUIRED
            %Propagated;
            %QualifierFlavor;>
    """

    check_node(tup_tree, 'QUALIFIER', ['NAME', 'TYPE'],
               ['OVERRIDABLE', 'TOSUBCLASS', 'TOINSTANCE',
                'TRANSLATABLE', 'PROPAGATED'],
               ['VALUE', 'VALUE.ARRAY'])

    attrl = attrs(tup_tree)

    qual = CIMQualifier(attrl['NAME'], unpack_value(tup_tree),
                        type=attrl['TYPE'])

    for i in ['OVERRIDABLE', 'TOSUBCLASS', 'TOINSTANCE',
              'TRANSLATABLE', 'PROPAGATED']:
        rtn_val = attrl.get(i)

        if rtn_val == 'true':
            rtn_val = True
        elif rtn_val == 'false':
            rtn_val = False
        elif rtn_val is None:
            pass
        else:
            raise ParseError("Invalid value %r for %s on %s" %
                             (rtn_val, i, name(tup_tree)))

        setattr(qual, i.lower(), rtn_val)

    return qual


def parse_property(tup_tree):
    """Parse PROPERTY into a CIMProperty object.

    VAL is just the pcdata of the enclosed VALUE node.

      ::

        <!ELEMENT PROPERTY (QUALIFIER*, VALUE?)>
        <!ATTLIST PROPERTY
            %CIMName;
            %CIMType;              #REQUIRED
            %ClassOrigin;
            %Propagated;
            %EmbeddedObject;>
    """

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
        raise ParseError("Cannot parse content of 'VALUE' child element of "
                         "'PROPERTY' element with name %r: %s" %
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
      ::

        <!ELEMENT PROPERTY.ARRAY (QUALIFIER*, VALUE.ARRAY?)>
        <!ATTLIST PROPERTY.ARRAY
            %CIMName;
            %CIMType;              #REQUIRED
            %ArraySize;
            %ClassOrigin;
            %Propagated;
            %EmbeddedObject;>
    """

    check_node(tup_tree, 'PROPERTY.ARRAY', ['NAME', 'TYPE'],
               ['REFERENCECLASS', 'CLASSORIGIN', 'PROPAGATED',
                'ARRAYSIZE', 'EmbeddedObject', 'EMBEDDEDOBJECT'],
               ['QUALIFIER', 'VALUE.ARRAY'])
    # TODO: Remove 'REFERENCECLASS' from attrs list, above.

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
    # TODO: Add support and tests for arraysize and propagated

    return obj


def parse_property_reference(tup_tree):
    """
      ::

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

    if not value:
        value = None
    elif len(value) == 1:
        value = value[0]
    else:
        raise ParseError("Element %r has more than one child element "
                         "'VALUE.REFERENCE' (allowed are zero or one)" %
                         name(tup_tree))

    quals = dict()
    for qual in list_of_matching(tup_tree, ['QUALIFIER']):
        quals[qual.name] = qual

    attributes = attrs(tup_tree)

    pref = CIMProperty(attributes['NAME'], value, type='reference',
                       qualifiers=quals,
                       reference_class=attributes.get('REFERENCECLASS'),
                       class_origin=attributes.get('CLASSORIGIN'),
                       propagated=attributes.get('PROPAGATED'))

    return pref


def parse_method(tup_tree):
    """
      ::

        <!ELEMENT METHOD (QUALIFIER*, (PARAMETER | PARAMETER.REFERENCE |
                                       PARAMETER.ARRAY | PARAMETER.REFARRAY)*)>
        <!ATTLIST METHOD
            %CIMName;
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
                                                    'PARAMETER.REFARRAY', ]))

    attrl = attrs(tup_tree)

    return CIMMethod(attrl['NAME'],
                     return_type=attrl.get('TYPE'),
                     parameters=parameters,
                     qualifiers=qualifiers,
                     class_origin=attrl.get('CLASSORIGIN'),
                     propagated=unpack_boolean(attrl.get('PROPAGATED')))


def parse_parameter(tup_tree):
    """
      ::

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
      ::

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
      ::

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
      ::

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
      ::

        <!ELEMENT MESSAGE (SIMPLEREQ | MULTIREQ | SIMPLERSP | MULTIRSP |
                           SIMPLEEXPREQ | MULTIEXPREQ | SIMPLEEXPRSP |
                           MULTIEXPRSP)
        <!ATTLIST MESSAGE
            ID CDATA #REQUIRED
            PROTOCOLVERSION CDATA #REQUIRED>
    """

    check_node(tup_tree, 'MESSAGE', ['ID', 'PROTOCOLVERSION'])

    child = one_child(tup_tree,
                      ['SIMPLEREQ', 'MULTIREQ', 'SIMPLERSP', 'MULTIRSP',
                       'SIMPLEEXPREQ', 'MULTIEXPREQ', 'SIMPLEEXPRSP',
                       'MULTIEXPRSP'])

    return name(tup_tree), attrs(tup_tree), child


def parse_multireq(tup_tree):   # pylint: disable=unused-argument
    """Not Implemented. Because this request is generally not implemented
       by platforms, It will probably never be implemented
    """
    raise ParseError("Internal Error: Parsing support for element %r is not "
                     "implemented" % name(tup_tree))


def parse_multiexpreq(tup_tree):   # pylint: disable=unused-argument
    """Not Implemented. Because this request is generally not implemented
       by platforms, It will probably never be implemented"""
    raise ParseError("Internal Error: Parsing support for element %r is not "
                     "implemented" % name(tup_tree))


def parse_simpleexpreq(tup_tree):
    """
      ::

        <!ELEMENT SIMPLEEXPREQ (EXPMETHODCALL)>
    """

    child = one_child(tup_tree, ['EXPMETHODCALL'])

    return name(tup_tree), attrs(tup_tree), child


def parse_simplereq(tup_tree):
    """
      ::

        <!ELEMENT SIMPLEREQ (IMETHODCALL | METHODCALL)>
    """

    check_node(tup_tree, 'SIMPLEREQ')

    child = one_child(tup_tree, ['IMETHODCALL', 'METHODCALL'])

    return name(tup_tree), attrs(tup_tree), child


def parse_imethodcall(tup_tree):
    """
      ::

        <!ELEMENT IMETHODCALL (LOCALNAMESPACEPATH, IPARAMVALUE*)>
        <!ATTLIST IMETHODCALL
            %CIMName;>
    """

    check_node(tup_tree, 'IMETHODCALL', ['NAME'])

    k = kids(tup_tree)

    if len(k) < 1:
        raise ParseError("Element %r has no child elements "
                         "(expecting child elements "
                         "(LOCALNAMESPACEPATH, IPARAMVALUE*))" %
                         name(tup_tree))

    localnspath = parse_localnamespacepath(k[0])

    params = [parse_iparamvalue(x) for x in k[1:]]

    return (name(tup_tree), attrs(tup_tree), localnspath, params)


def parse_methodcall(tup_tree):
    """
      ::

        <!ELEMENT METHODCALL ((LOCALCLASSPATH|LOCALINSTANCEPATH),PARAMVALUE*)>
        <!ATTLIST METHODCALL
            %CIMName;>
    """

    check_node(tup_tree, 'METHODCALL', ['NAME'], [],
               ['LOCALCLASSPATH', 'LOCALINSTANCEPATH', 'PARAMVALUE'])
    path = list_of_matching(tup_tree, ['LOCALCLASSPATH', 'LOCALINSTANCEPATH'])
    if len(path) == 0:
        raise ParseError("Element %r misses a required child element "
                         "'LOCALCLASSPATH' or 'LOCALINSTANCEPATH'" %
                         name(tup_tree))
    if len(path) > 1:
        raise ParseError("Element %r has too many child elements %r "
                         "(allowed is one of 'LOCALCLASSPATH' or "
                         "'LOCALINSTANCEPATH')" %
                         (name(tup_tree), path))
    path = path[0]
    params = list_of_matching(tup_tree, ['PARAMVALUE'])
    return (name(tup_tree), attrs(tup_tree), path, params)


def parse_expmethodcall(tup_tree):
    """
      ::

        <!ELEMENT EXPMETHODCALL (EXPPARAMVALUE*)>
        <!ATTLIST EXPMETHODCALL
            %CIMName;>
    """

    check_node(tup_tree, 'EXPMETHODCALL', ['NAME'], [], ['EXPPARAMVALUE'])

    params = list_of_matching(tup_tree, ['EXPPARAMVALUE'])

    return (name(tup_tree), attrs(tup_tree), params)


def parse_paramvalue(tup_tree):
    """Parse PARAMVALUE element.

      ::

        <!ELEMENT PARAMVALUE (VALUE | VALUE.REFERENCE | VALUE.ARRAY |
                              VALUE.REFARRAY | CLASSNAME | INSTANCENAME |
                              CLASS | INSTANCE | VALUE.NAMEDINSTANCE)?>
        <!ATTLIST PARAMVALUE
            %CIMName;
            %ParamType;  #IMPLIED
            %EmbeddedObject;>
    """
    # TODO: 6/16 KS: Extended per DSP0201 v 1.4 to include CLASSNAME,
    # INSTANCENAME, CLASS, INSTANCE, VALUE.NAMEDINSTANCE but not sure
    # we have tests for all of these.
    # Version 2.1.1 of the DTD lacks the %ParamType attribute but it
    # is present in version 2.2.  Make it optional to be backwards
    # compatible.

    check_node(tup_tree, 'PARAMVALUE', ['NAME'],
               ['PARAMTYPE', 'EmbeddedObject', 'EMBEDDEDOBJECT'])

    child = optional_child(tup_tree,
                           ['VALUE', 'VALUE.REFERENCE', 'VALUE.ARRAY',
                            'VALUE.REFARRAY', 'CLASSNAME', 'INSTANCENAME',
                            'CLASS', 'INSTANCE', 'VALUE.NAMEDINSTANCE'])
    attrl = attrs(tup_tree)

    if 'PARAMTYPE' in attrl:
        paramtype = attrl['PARAMTYPE']
    else:
        paramtype = None

    if 'EmbeddedObject' in attrl or 'EMBEDDEDOBJECT' in attrl:
        child = parse_embeddedObject(child)

    return attrl['NAME'], paramtype, child


def parse_iparamvalue(tup_tree):
    """Parse expected IPARAMVALUE element. I.e.

      ::

        <!ELEMENT IPARAMVALUE (VALUE | VALUE.ARRAY | VALUE.REFERENCE |
                              INSTANCENAME | CLASSNAME |
                              QUALIFIER.DECLARATION |
                              CLASS | INSTANCE | VALUE.NAMEDINSTANCE)?>
        <!ATTLIST IPARAMVALUE
            %CIMName;>

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

      ::

        <!ELEMENT EXPPARAMVALUE (INSTANCE?)>
        <!ATTLIST EXPPARAMVALUE
            %CIMName;>
    """

    check_node(tup_tree, 'EXPPARAMVALUE', ['NAME'], [], ['INSTANCE'])

    child = optional_child(tup_tree, ['INSTANCE'])

    _name = attrs(tup_tree)['NAME']
    return _name, child


def parse_multirsp(tup_tree):   # pylint: disable=unused-argument
    """This function not implemented. Because this request is generally not
       implemented. It will probably never be implemented"""
    raise ParseError("Internal Error: Parsing support for element %r is not "
                     "implemented" % name(tup_tree))


def parse_multiexprsp(tup_tree):   # pylint: disable=unused-argument
    """This function not implemented. Because this request is generally not
       implemented. It will probably never be implemented
    """
    raise ParseError("Internal Error: Parsing support for element %r is not "
                     "implemented" % name(tup_tree))


def parse_simplersp(tup_tree):
    """Parse for SIMPLERSP Element.

      ::

        <!ELEMENT SIMPLERSP (METHODRESPONSE | IMETHODRESPONSE)>
    """

    check_node(tup_tree, 'SIMPLERSP', [], [])

    child = one_child(tup_tree, ['METHODRESPONSE', 'IMETHODRESPONSE'])

    return name(tup_tree), attrs(tup_tree), child


def parse_simpleexprsp(tup_tree):   # pylint: disable=unused-argument
    """This Function not implemented. This response is for export senders
       (indication senders) so it is not implemented in the pywbem
       client.
    """
    raise ParseError("Internal Error: Parsing support for element %r is not "
                     "implemented" % name(tup_tree))


def parse_methodresponse(tup_tree):
    """Parse expected METHODRESPONSE ELEMENT. I.e.

      ::

        <!ELEMENT METHODRESPONSE (ERROR | (RETURNVALUE?, PARAMVALUE*))>
        <!ATTLIST METHODRESPONSE
            %CIMName;>
    """

    check_node(tup_tree, 'METHODRESPONSE', ['NAME'], [])

    return name(tup_tree), attrs(tup_tree), list_of_various(tup_tree,
                                                            ['ERROR',
                                                             'RETURNVALUE',
                                                             'PARAMVALUE'])


def parse_expmethodresponse(tup_tree):  # pylint: disable=unused-argument
    """This function not implemented. """
    raise ParseError("Internal Error: Parsing support for element %r is not "
                     "implemented" % name(tup_tree))


def parse_imethodresponse(tup_tree):
    """Parse the tuple for an IMETHODRESPONE Element. I.e.

      ::

        <!ELEMENT IMETHODRESPONSE (ERROR | (IRETURNVALUE?, PARAMVALUE*))>
        <!ATTLIST IMETHODRESPONSE
            %CIMName;>
    """

    check_node(tup_tree, 'IMETHODRESPONSE', ['NAME'], [])

    return name(tup_tree), attrs(tup_tree), list_of_various(tup_tree,
                                                            ['ERROR',
                                                             'IRETURNVALUE',
                                                             'PARAMVALUE'])


def parse_error(tup_tree):
    """Parse ERROR element to get CODE and DESCRIPTION.

      ::

        <!ELEMENT ERROR EMPTY>
        <!ATTLIST ERROR
            CODE CDATA #REQUIRED
            DESCRIPTION CDATA #IMPLIED>
    """

    check_node(tup_tree, 'ERROR', ['CODE'], ['DESCRIPTION'])

    return (name(tup_tree), attrs(tup_tree), None)


def parse_returnvalue(tup_tree):
    """Parse the RETURNVALUE element. Returns name, attributes, and
    one child as a tuple.

      ::

        <!ELEMENT RETURNVALUE (VALUE | VALUE.REFERENCE)?>
        <!ATTLIST RETURNVALUE
            %EmbeddedObject;
            %ParamType;       #IMPLIED>
    """

    # Version 2.1.1 of the DTD lacks the %ParamType attribute but it
    # is present in version 2.2.  Make it optional to be backwards
    # compatible.

    check_node(tup_tree, 'RETURNVALUE', [],
               ['PARAMTYPE', 'EmbeddedObject', 'EMBEDDEDOBJECT'])

    child = optional_child(tup_tree, ['VALUE', 'VALUE.REFERENCE'])
    attrl = attrs(tup_tree)

    if 'EmbeddedObject' in attrl or 'EMBEDDEDOBJECT' in attrl:
        child = parse_embeddedObject(child)

    return name(tup_tree), attrl, child


def parse_ireturnvalue(tup_tree):
    """Parse IRETURNVALUE element. Returns name, attributes and
    values of the tup_tree.

      ::

        <!ELEMENT IRETURNVALUE (CLASSNAME* | INSTANCENAME* | VALUE* |
                                VALUE.OBJECTWITHPATH* |
                                VALUE.OBJECTWITHLOCALPATH* | VALUE.OBJECT* |
                                OBJECTPATH* | QUALIFIER.DECLARATION* |
                                VALUE.ARRAY? | VALUE.REFERENCE? | CLASS* |
                                INSTANCE* | INSTANCEPATH* |
                                VALUE.NAMEDINSTANCE* |
                                VALUE.INSTANCEWITHPATH*)>
    """

    # Note: The check_node() below does not enforce any child elements from the
    # DTD, and the processing further down does not enforce that VALUE.ARRAY
    # and VALUE.REFERENCE may appear at most once.
    # Checking that at this level is not reasonable because the better checks
    # can be done in context of the intrinsic operation receiving its return
    # value. The DTD is so broad simply because it needs to cover the possible
    # return values of all intrinsic operations.

    check_node(tup_tree, 'IRETURNVALUE', [], [])

    values = list_of_same(tup_tree, ['CLASSNAME', 'INSTANCENAME',
                                     'VALUE', 'VALUE.OBJECTWITHPATH',
                                     'VALUE.OBJECT', 'OBJECTPATH',
                                     'QUALIFIER.DECLARATION',
                                     'VALUE.ARRAY', 'VALUE.REFERENCE',
                                     'CLASS', 'INSTANCE',
                                     'INSTANCEPATH',
                                     'VALUE.NAMEDINSTANCE',
                                     'VALUE.INSTANCEWITHPATH'])

    # Note: The caller needs to unpack the value.
    return name(tup_tree), attrs(tup_tree), values


#
# Object naming and locating elements
#


def parse_any(tup_tree):
    """Parse a fragment of XML. This function drives the rest of
    the parser by calling ``parse_*()`` functions based on the name
    of the element being parsed.

    It builds parser function name from incoming name in tup_tree
    prepended with ``parse_`` and calls that function.

    Return is determined by function called.
    """

    nodename = name(tup_tree).lower().replace('.', '_')
    fn_name = 'parse_' + nodename
    funct_name = globals().get(fn_name)
    if funct_name is None:
        raise ParseError("Invalid element %r" % name(tup_tree))
    else:
        return funct_name(tup_tree)


def parse_embeddedObject(val):  # pylint: disable=invalid-name
    """Parse and embedded instance or class and return the
    CIMInstance or CIMClass.

    Parameters:

      val (string):
        The string value that contains the embedded object in CIM-XML format.
        One level of XML entity references have already been unescaped.

        Example string value, for a doubly nested embedded instance. Note that
        in the CIM-XML payload, this string value is escaped one more level.

        ::

            <INSTANCE CLASSNAME="PyWBEM_Address">
              <PROPERTY NAME="Street" TYPE="string">
                <VALUE>Fritz &amp; &lt;the cat&gt; Ave</VALUE>
              </PROPERTY>
              <PROPERTY NAME="Town" TYPE="string" EmbeddedObject="instance">
                <VALUE>
                  &lt;INSTANCE CLASSNAME="PyWBEM_Town"&gt;
                    &lt;PROPERTY NAME="Name" TYPE="string"&gt;
                      &lt;VALUE&gt;Fritz &amp;amp; &amp;lt;the cat&amp;gt;
                        Town&lt;/VALUE&gt;
                    &lt;/PROPERTY&gt;
                    &lt;PROPERTY NAME="Zip" TYPE="string"&gt;
                      &lt;VALUE&gt;z12345&lt;/VALUE&gt;
                    &lt;/PROPERTY&gt;
                  &lt;/INSTANCE&gt;
                </VALUE>
              </PROPERTY>
            </INSTANCE>

    Returns:

      `None` if `val` is `None`.
      `CIMClass` or `CIMInstance` or a list of them, otherwise.

    Raises:

      ParseError: There is an error in the XML.
    """

    if isinstance(val, list):
        return [parse_embeddedObject(obj) for obj in val]
    if val is None:
        return None

    # Perform the un-embedding (may raise ParseError)
    tup_tree = xml_to_tupletree_sax(val, "embedded object")

    if name(tup_tree) == 'INSTANCE':
        return parse_instance(tup_tree)
    elif name(tup_tree) == 'CLASS':
        return parse_class(tup_tree)
    else:
        raise ParseError("Invalid top-level element %r in embedded object "
                         "value" % name(tup_tree))


def unpack_value(tup_tree):
    """Find VALUE or VALUE.ARRAY under tup_tree and convert to a
    Python value.

    Looks at the TYPE of the node to work out how to decode it.
    Handles nodes with no value (e.g. in CLASS.)
    """

    # TODO: Handle VALUE.REFERENCE, VALUE.REFARRAY.
    # Investigation is needed on this to do: Double check whether
    # unpack_value() is called for VALUE.REFERENCE, VALUE.REFARRAY at all. Is
    # this about an error or about simplification?  Also, make sure that
    # testclient has test cases covering this.

    valtype = attrs(tup_tree)['TYPE']

    raw_val = list_of_matching(tup_tree, ['VALUE', 'VALUE.ARRAY'])
    if not raw_val:
        return None
    elif len(raw_val) > 1:
        raise ParseError("Element %r has too many child elements %r "
                         "(allowed is one of 'VALUE' or 'VALUE.ARRAY')" %
                         name(tup_tree))

    raw_val = raw_val[0]

    if isinstance(raw_val, list):
        return [tocimobj(valtype, x) for x in raw_val]
    elif not raw_val and valtype != 'string':
        return None
    return tocimobj(valtype, raw_val)


def unpack_boolean(data):
    """Unpack a boolean, represented as "TRUE" or "FALSE" in CIM."""

    if data is None:
        return None

    # CIM-XML says "These values MUST be treated as case-insensitive"
    # (even though the XML definition requires them to be lowercase.)

    data = data.strip().lower()                   # ignore space
    if data == 'true':
        return True
    elif data == 'false':
        return False
    elif data == '':
        return None
    else:
        raise ParseError("Invalid boolean %r" % data)
