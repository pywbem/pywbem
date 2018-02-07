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
import re
import warnings
import six

from .cim_obj import CIMInstance, CIMInstanceName, CIMClass, CIMClassName, \
    CIMProperty, CIMMethod, CIMParameter, CIMQualifier, \
    CIMQualifierDeclaration, _stacklevel_above_module
from .cim_types import CIMDateTime, type_from_name
from .tupletree import xml_to_tupletree_sax
from .exceptions import ParseError

__all__ = []


def filter_tuples(list_):
    """Return only the tuples in a list.

    In a tupletree, tuples correspond to XML elements.  Useful for
    stripping out whitespace data in a child list."""

    return [] if list_ is None else [x for x in list_ if isinstance(x, tuple)]


def pcdata(tup_tree):
    """
    Return the concatenated character data within the child nodes of a
    tuple tree node, as a unicode string. Whitespace is preserved.

    The child nodes must be text nodes (no element nodes).
    """
    for inst in tup_tree[2]:
        if not isinstance(inst, six.string_types):
            raise ParseError("Element %r has unexpected child elements: %r"
                             "(allowed is only text content)" %
                             (name(tup_tree), inst))
    data = u''.join(tup_tree[2])
    assert isinstance(data, six.text_type)
    return data


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
               allowed_children=None, allow_pcdata=False):
    # pylint: disable=too-many-branches
    """
    Check static local constraints on a tuple tree node.

    The node must have the given nodename.

    Required_attrs is a list of attribute names that must be present.
    None means the same as an empty list: No attributes are required.

    Optional_attrs is a list of attribute names that may be present.
    None means the same as an empty list: No attributes are optional.

    Present attributes that are neither required nor optional, are rejected.

    If allowed_children is not None, the node may have children of the given
    types.  It can be [] for nodes that may not have any children.  If it's
    None, no validation of the children is performed.

    If allow_pcdata is True, then non-whitespace text nodes are allowed as
    children. (Whitespace text nodes are always allowed as children.)
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

    if not k:
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
    """
    Parse a VALUE element and return its text content as a unicode string.
    Whitespace is preserved.

    The conversion of the text representation of the value to a CIM data type
    object requires CIM type information which is not available on the VALUE
    element and therefore will be done when parsing higher level elements that
    have that information.

      ::

        <!ELEMENT VALUE (#PCDATA)>
    """

    check_node(tup_tree, 'VALUE', [], [], [], allow_pcdata=True)

    return pcdata(tup_tree)


def parse_value_array(tup_tree):
    """
    Parse a VALUE.ARRAY element and return the items in the array as a list of
    unicode strings, or None for NULL items. Whitespace is preserved.

      ::

        <!ELEMENT VALUE.ARRAY (VALUE | VALUE.NULL)*>
    """

    check_node(tup_tree, 'VALUE.ARRAY')

    children = list_of_various(tup_tree, ['VALUE', 'VALUE.NULL'])

    return children


def parse_value_reference(tup_tree):
    """
    Parse a VALUE.REFERENCE element and return the instance path or class path
    it represents as a CIMInstanceName or CIMClassName object, respectively.

      ::

        <!ELEMENT VALUE.REFERENCE (CLASSPATH | LOCALCLASSPATH | CLASSNAME |
                                   INSTANCEPATH | LOCALINSTANCEPATH |
                                   INSTANCENAME)>
    """

    check_node(tup_tree, 'VALUE.REFERENCE')

    child = one_child(tup_tree,
                      ['CLASSPATH', 'LOCALCLASSPATH', 'CLASSNAME',
                       'INSTANCEPATH', 'LOCALINSTANCEPATH',
                       'INSTANCENAME'])

    return child


def parse_value_refarray(tup_tree):
    """
    Parse a VALUE.REFARRAY element and return the array of instance paths or
    class paths it represents as a list of CIMInstanceName or CIMClassName
    objects, respectively.

      ::

        <!ELEMENT VALUE.REFARRAY (VALUE.REFERENCE | VALUE.NULL)*>
    """

    check_node(tup_tree, 'VALUE.REFARRAY')

    children = list_of_various(tup_tree, ['VALUE.REFERENCE', 'VALUE.NULL'])

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

    inst_path = parse_instancename(k[0])
    instance = parse_instance(k[1])
    instance.path = inst_path

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

    inst_path = parse_instancepath(k[0])
    instance = parse_instance(k[1])
    instance.path = inst_path

    return instance


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
        inst_path = parse_instancename(kids(tup_tree)[0])

        # redefines _object from pywbem.cim_obj.CIMClass to ...CIMInstance
        _object = parse_instance(kids(tup_tree)[1])

        _object.path = inst_path
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
        # Note: Before pywbem 0.12, CIMClass did not have a path, therefore
        # classpath and class are returned as a tuple.
        _object = (parse_localclasspath(k[0]),
                   parse_class(k[1]))
    else:
        inst_path = parse_localinstancepath(k[0])
        # redefines _object from tuple to CIMInstance with path
        _object = parse_instance(k[1])
        _object.path = inst_path

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
        # Note: Before pywbem 0.12, CIMClass did not have a path, therefore
        # classpath and class are returned as a tuple.
        _object = (parse_classpath(k[0]),
                   parse_class(k[1]))
    else:
        inst_path = parse_instancepath(k[0])
        # redefines _object from tuple to CIMInstance with path
        _object = parse_instance(k[1])
        _object.path = inst_path

    return (name(tup_tree), attrs(tup_tree), _object)


def parse_value_null(tup_tree):
    """
    Parse a VALUE.NULL element and return None.

      ::

        <!ELEMENT VALUE.NULL EMPTY>
    """

    check_node(tup_tree, 'VALUE.NULL', [], [], [])

    return None


#
# Object naming and locating elements
#


def parse_namespacepath(tup_tree):
    """
    Parse a NAMESPACEPATH element and return the host and namespace it
    represents as a tuple (host, namespace).

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
    namespace = parse_localnamespacepath(k[1])

    return (host, namespace)


def parse_localnamespacepath(tup_tree):
    """
    Parse a LOCALNAMESPACEPATH element and return the namespace it represents
    as a unicode string.

    The namespace is formed by joining the namespace components (one from each
    NAMESPACE child element) with a slash (e.g. to "root/cimv2").

      ::

        <!ELEMENT LOCALNAMESPACEPATH (NAMESPACE+)>
    """

    check_node(tup_tree, 'LOCALNAMESPACEPATH', [], [], ['NAMESPACE'])

    if not kids(tup_tree):
        raise ParseError("Element %r misses child elements "
                         "(expecting one or more child elements 'NAMESPACE')" %
                         name(tup_tree))

    # list_of_various() has the same effect as list_of_same() when used with a
    # single allowed child element, but is a little faster.
    ns_list = list_of_various(tup_tree, ['NAMESPACE'])

    return u'/'.join(ns_list)


def parse_host(tup_tree):
    """
    Parse a HOST element and return its text content as a unicode string.

      ::

        <!ELEMENT HOST (#PCDATA)>
    """

    check_node(tup_tree, 'HOST', [], [], [], allow_pcdata=True)

    return pcdata(tup_tree)


def parse_namespace(tup_tree):
    """
    Parse a NAMESPACE element and return the namespace component it represents
    (e.g. "root") as a unicode string.

      ::

        <!ELEMENT NAMESPACE EMPTY>
        <!ATTLIST NAMESPACE
            %CIMName;>
    """

    check_node(tup_tree, 'NAMESPACE', ['NAME'], [], [])

    return attrs(tup_tree)['NAME']


def parse_classpath(tup_tree):
    """
    Parse a CLASSPATH element and return the class path it represents as a
    CIMClassName object.

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

    host, namespace = parse_namespacepath(k[0])
    class_path = parse_classname(k[1])
    class_path.host = host
    class_path.namespace = namespace

    return class_path


def parse_localclasspath(tup_tree):
    """
    Parse a LOCALCLASSPATH element and return the class path it represents as a
    CIMClassName object.

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

    namespace = parse_localnamespacepath(k[0])
    class_path = parse_classname(k[1])
    class_path.namespace = namespace

    return class_path


def parse_classname(tup_tree):
    """
    Parse a CLASSNAME element and return the class path it represents as a
    CIMClassName object.

      ::

        <!ELEMENT CLASSNAME EMPTY>
        <!ATTLIST CLASSNAME
            %CIMName;>
    """

    check_node(tup_tree, 'CLASSNAME', ['NAME'], [], [])

    classname = attrs(tup_tree)['NAME']
    class_path = CIMClassName(classname)

    return class_path


def parse_instancepath(tup_tree):
    """
    Parse an INSTANCEPATH element and return the instance path it represents as
    a CIMInstanceName object.

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

    host, namespace = parse_namespacepath(k[0])
    inst_path = parse_instancename(k[1])
    inst_path.host = host
    inst_path.namespace = namespace

    return inst_path


def parse_localinstancepath(tup_tree):
    """
    Parse a LOCALINSTANCEPATH element and return the instance path it
    represents as a CIMInstanceName object.

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

    namespace = parse_localnamespacepath(k[0])
    inst_path = parse_instancename(k[1])
    inst_path.namespace = namespace

    return inst_path


def parse_instancename(tup_tree):
    """
    Parse an INSTANCENAME element and return the instance path it represents as
    a CIMInstanceName object.

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

        val = parse_any(kid0)
        return CIMInstanceName(classname, {None: val})
    elif k0_name == 'KEYBINDING':
        kbs = {}
        # list_of_various() has the same effect as list_of_same() when used
        # with a single allowed child element, but is a little faster.
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
    """
    Parse a KEYBINDING element and return the keybinding as a one-item
    dictionary from name to value, where the value is a CIM data type object,
    based upon the type information in the child elements, if present. If no
    type information is present, numeric values are returned as int or float.

      ::

        <!ELEMENT KEYBINDING (KEYVALUE | VALUE.REFERENCE)>
        <!ATTLIST KEYBINDING
            %CIMName;>
    """

    check_node(tup_tree, 'KEYBINDING', ['NAME'])

    child = one_child(tup_tree, ['KEYVALUE', 'VALUE.REFERENCE'])

    return {attrs(tup_tree)['NAME']: child}


def parse_keyvalue(tup_tree):
    """
    Parse a KEYVALUE element and return the keybinding value as a CIM data type
    object, based upon the type information in its VALUETYPE and TYPE
    attributes, if present.

    If TYPE is specified, its value is used to create the corresponding CIM
    data type object. in this case, VALUETYPE is ignored and may be omitted.
    Discrepancies between TYPE and VALUETYPE are not checked.

    Note that DSP0201 does not detail how such discrepancies should be
    resolved, including the precedence of the DTD-defined default for VALUETYPE
    over a specified TYPE value.

    If TYPE is not specified but VALUETYPE is specified, the CIM type is
    defaulted for a VALUETYPE of 'string' and 'boolean'. For a VALUETYPE of
    'numeric', the CIM type remains undetermined and the numeric values are
    returned as Python int/long or float objects.

      ::

        <!ELEMENT KEYVALUE (#PCDATA)>
        <!ATTLIST KEYVALUE
            VALUETYPE (string | boolean | numeric) "string"
            %CIMType;              #IMPLIED>
    """

    check_node(tup_tree, 'KEYVALUE', [], ['VALUETYPE', 'TYPE'], [],
               allow_pcdata=True)

    data = pcdata(tup_tree)
    attrl = attrs(tup_tree)

    valuetype = attrl.get('VALUETYPE', 'string')
    cimtype = attrl.get('TYPE', None)

    # Default the CIM type from VALUETYPE if not specified in TYPE
    if cimtype is None:
        if valuetype == 'string':
            cimtype = 'string'
        elif valuetype == 'boolean':
            cimtype = 'boolean'
        elif valuetype == 'numeric':
            pass
        else:
            raise ParseError("Element %r has invalid 'VALUETYPE' attribute "
                             "value %r" % (name(tup_tree), valuetype))

    return unpack_single_value(data, cimtype)


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

    attrl = attrs(tup_tree)

    superclass = attrl.get('SUPERCLASS', None)
    properties = list_of_matching(tup_tree, ['PROPERTY', 'PROPERTY.REFERENCE',
                                             'PROPERTY.ARRAY'])
    qualifiers = list_of_matching(tup_tree, ['QUALIFIER'])
    methods = list_of_matching(tup_tree, ['METHOD'])

    return CIMClass(attrl['NAME'],
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
            %ClassName;
            xml:lang NMTOKEN #IMPLIED>
    """

    check_node(tup_tree, 'INSTANCE', ['CLASSNAME'], ['xml:lang'],
               ['QUALIFIER', 'PROPERTY', 'PROPERTY.ARRAY',
                'PROPERTY.REFERENCE'])

    # The 'xml:lang' attribute is tolerated but ignored.

    # Note: The check above does not enforce the ordering constraint in the DTD
    # that QUALIFIER elements must appear before PROPERTY* elements.

    qualifiers = list_of_matching(tup_tree, ['QUALIFIER'])

    props = list_of_matching(tup_tree, ['PROPERTY.REFERENCE', 'PROPERTY',
                                        'PROPERTY.ARRAY'])

    obj = CIMInstance(attrs(tup_tree)['CLASSNAME'], qualifiers=qualifiers)

    for prop in props:
        obj.__setitem__(prop.name, prop)

    return obj


def parse_scope(tup_tree):
    """
    Parse a SCOPE element and return a dictionary with an item for each
    specified scope attribute.

    The keys of the dictionary items are the scope names in upper case; the
    values are the Python boolean values True or False.

    Unspecified scope attributes are not represented in the returned dictionary;
    the user is expected to assume their default value of False.

    The returned dictionary does not preserve order of the scope attributes.
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

    scopes = {}  # Attributes do not preserve order, so we use standard dict()
    for k, v in attrs(tup_tree).items():
        v_ = unpack_boolean(v)
        if v_ is None:
            raise ParseError("Element %r has an invalid value %r for its "
                             "boolean attribute %r" %
                             (name(tup_tree), v, k))
        scopes[k] = v_
    return scopes


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

    attrl = attrs(tup_tree)
    qname = attrl['NAME']
    _type = attrl['TYPE']

    try:
        # TODO 2/18 AM #1041: Reject invalid boolean values
        # Consider using unpack_boolean() for that.
        is_array = attrl['ISARRAY'].lower() == 'true'
    except KeyError:
        is_array = False

    array_size = attrl.get('ARRAYSIZE', None)
    if array_size is not None:
        # TODO #1044: Clarify if hex support is needed.
        array_size = int(array_size)

    flavors = {}
    for flavor in ['OVERRIDABLE', 'TOSUBCLASS', 'TOINSTANCE', 'TRANSLATABLE']:
        try:
            # TODO 2/18 AM #1041: Reject invalid boolean values
            # Consider using unpack_boolean() for that.
            flavors[flavor.lower()] = attrl[flavor].lower() == 'true'
        except KeyError:
            # This causes the flavor not to be set, so it results in the
            # default value defined in the CIMQualifierDeclaration() ctor (None)
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
            # name is 'VALUE' or 'VALUE.ARRAY'
            if value is not None:
                raise ParseError("Element %r has more than one child element "
                                 "%r (allowed is only one)" %
                                 (name(tup_tree), name(child)))
            value = unpack_value(tup_tree)

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
            %QualifierFlavor;
            xml:lang NMTOKEN #IMPLIED>
    """

    check_node(tup_tree, 'QUALIFIER', ['NAME', 'TYPE'],
               ['OVERRIDABLE', 'TOSUBCLASS', 'TOINSTANCE',
                'TRANSLATABLE', 'PROPAGATED', 'xml:lang'],
               ['VALUE', 'VALUE.ARRAY'])

    # The 'xml:lang' attribute is tolerated but ignored.

    attrl = attrs(tup_tree)
    val = unpack_value(tup_tree)

    qual = CIMQualifier(attrl['NAME'], val, type=attrl['TYPE'])

    for i in ['OVERRIDABLE', 'TOSUBCLASS', 'TOINSTANCE',
              'TRANSLATABLE', 'PROPAGATED']:
        rtn_val = attrl.get(i, None)
        if rtn_val is not None:
            rtn_val = rtn_val.lower()

        # TODO #1039: Clarify whether to default omitted qualifier flavors
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
            %EmbeddedObject;
            xml:lang NMTOKEN #IMPLIED>
    """

    check_node(tup_tree, 'PROPERTY', ['TYPE', 'NAME'],
               ['CLASSORIGIN', 'PROPAGATED', 'EmbeddedObject',
                'EMBEDDEDOBJECT', 'xml:lang'],
               ['QUALIFIER', 'VALUE'])

    # The 'xml:lang' attribute is tolerated but ignored.

    attrl = attrs(tup_tree)
    try:
        val = unpack_value(tup_tree)
    except ValueError as exc:
        msg = str(exc)
        raise ParseError("Cannot parse content of 'VALUE' child element of "
                         "'PROPERTY' element with name %r: %s" %
                         (attrl['NAME'], msg))

    qualifiers = list_of_matching(tup_tree, ['QUALIFIER'])

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
                       class_origin=attrl.get('CLASSORIGIN', None),
                       propagated=unpack_boolean(attrl.get('PROPAGATED',
                                                           'false')),
                       qualifiers=qualifiers,
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
            %EmbeddedObject;
            xml:lang NMTOKEN #IMPLIED>
    """

    check_node(tup_tree, 'PROPERTY.ARRAY', ['NAME', 'TYPE'],
               ['CLASSORIGIN', 'PROPAGATED', 'ARRAYSIZE', 'EmbeddedObject',
                'EMBEDDEDOBJECT', 'xml:lang'],
               ['QUALIFIER', 'VALUE.ARRAY'])

    # The 'xml:lang' attribute is tolerated but ignored.

    values = unpack_value(tup_tree)
    attrl = attrs(tup_tree)

    qualifiers = list_of_matching(tup_tree, ['QUALIFIER'])

    array_size = attrl.get('ARRAYSIZE', None)
    if array_size is not None:
        # TODO #1044: Clarify if hex support is needed.
        array_size = int(array_size)

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
                      class_origin=attrl.get('CLASSORIGIN', None),
                      propagated=unpack_boolean(attrl.get('PROPAGATED',
                                                          'false')),
                      qualifiers=qualifiers,
                      is_array=True,
                      array_size=array_size,
                      embedded_object=embedded_object)

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
               ['REFERENCECLASS', 'CLASSORIGIN', 'PROPAGATED'],
               ['QUALIFIER', 'VALUE.REFERENCE'])

    value = list_of_matching(tup_tree, ['VALUE.REFERENCE'])

    if not value:
        value = None
    elif len(value) == 1:
        value = value[0]
    else:
        raise ParseError("Element %r has more than one child element "
                         "'VALUE.REFERENCE' (allowed are zero or one)" %
                         name(tup_tree))

    attrl = attrs(tup_tree)

    qualifiers = list_of_matching(tup_tree, ['QUALIFIER'])

    pref = CIMProperty(attrl['NAME'], value, type='reference',
                       qualifiers=qualifiers,
                       reference_class=attrl.get('REFERENCECLASS', None),
                       class_origin=attrl.get('CLASSORIGIN', None),
                       propagated=unpack_boolean(attrl.get('PROPAGATED',
                                                           'false')))

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

    attrl = attrs(tup_tree)

    parameters = list_of_matching(tup_tree, ['PARAMETER',
                                             'PARAMETER.REFERENCE',
                                             'PARAMETER.ARRAY',
                                             'PARAMETER.REFARRAY'])

    qualifiers = list_of_matching(tup_tree, ['QUALIFIER'])

    return_type = attrl.get('TYPE', None)
    if not return_type:
        raise ParseError("Element %r missing attribute 'TYPE' (a void method "
                         "return type is not supported in CIM)" %
                         name(tup_tree))

    return CIMMethod(attrl['NAME'],
                     return_type=return_type,
                     parameters=parameters,
                     qualifiers=qualifiers,
                     class_origin=attrl.get('CLASSORIGIN', None),
                     propagated=unpack_boolean(attrl.get('PROPAGATED',
                                                         'false')))


def parse_parameter(tup_tree):
    """
      ::

        <!ELEMENT PARAMETER (QUALIFIER*)>
        <!ATTLIST PARAMETER
            %CIMName;
            %CIMType;              #REQUIRED>
    """

    check_node(tup_tree, 'PARAMETER', ['NAME', 'TYPE'], [], ['QUALIFIER'])

    attrl = attrs(tup_tree)

    qualifiers = list_of_matching(tup_tree, ['QUALIFIER'])

    return CIMParameter(attrl['NAME'], type=attrl['TYPE'],
                        qualifiers=qualifiers)


def parse_parameter_reference(tup_tree):
    """
      ::

        <!ELEMENT PARAMETER.REFERENCE (QUALIFIER*)>
        <!ATTLIST PARAMETER.REFERENCE
            %CIMName;
            %ReferenceClass;>
    """

    check_node(tup_tree, 'PARAMETER.REFERENCE', ['NAME'], ['REFERENCECLASS'],
               ['QUALIFIER'])

    attrl = attrs(tup_tree)

    qualifiers = list_of_matching(tup_tree, ['QUALIFIER'])

    return CIMParameter(attrl['NAME'],
                        type='reference',
                        reference_class=attrl.get('REFERENCECLASS', None),
                        qualifiers=qualifiers)


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
               ['ARRAYSIZE'], ['QUALIFIER'])

    attrl = attrs(tup_tree)

    array_size = attrl.get('ARRAYSIZE', None)
    if array_size is not None:
        # TODO #1044: Clarify if hex support is needed
        array_size = int(array_size)

    qualifiers = list_of_matching(tup_tree, ['QUALIFIER'])

    return CIMParameter(attrl['NAME'],
                        type=attrl['TYPE'],
                        is_array=True,
                        array_size=array_size,
                        qualifiers=qualifiers)


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
               ['REFERENCECLASS', 'ARRAYSIZE'], ['QUALIFIER'])

    attrl = attrs(tup_tree)

    array_size = attrl.get('ARRAYSIZE', None)
    if array_size is not None:
        # TODO #1044: Clarify if hex support is needed
        array_size = int(array_size)

    qualifiers = list_of_matching(tup_tree, ['QUALIFIER'])

    return CIMParameter(attrl['NAME'], 'reference',
                        is_array=True,
                        reference_class=attrl.get('REFERENCECLASS', None),
                        array_size=array_size,
                        qualifiers=qualifiers)


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

    if not k:
        raise ParseError("Element %r has no child elements "
                         "(expecting child elements "
                         "(LOCALNAMESPACEPATH, IPARAMVALUE*))" %
                         name(tup_tree))

    namespace = parse_localnamespacepath(k[0])

    params = [parse_iparamvalue(x) for x in k[1:]]

    return (name(tup_tree), attrs(tup_tree), namespace, params)


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
    if not path:
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

    # Version 2.4 of DSP0201 added CLASSNAME, INSTANCENAME, CLASS, INSTANCE, and
    # VALUE.NAMEDINSTANCE.

    # Version 2.1.1 of DSP0201 lacks the %ParamType entity but it is present as
    # optional (for backwards compatibility) in version 2.2.

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

    check_node(tup_tree, 'IPARAMVALUE', ['NAME'])

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

    check_node(tup_tree, 'SIMPLERSP')

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

    check_node(tup_tree, 'METHODRESPONSE', ['NAME'])

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

    check_node(tup_tree, 'IMETHODRESPONSE', ['NAME'])

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

    check_node(tup_tree, 'ERROR', ['CODE'], ['DESCRIPTION'], [])

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
    check_node(tup_tree, 'IRETURNVALUE')

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
    funct_name = globals().get(fn_name, None)
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

    raise ParseError("Invalid top-level element %r in embedded object value" %
                     name(tup_tree))


def unpack_value(tup_tree):
    """Find VALUE or VALUE.ARRAY under tup_tree and convert to a
    Python value.

    Looks at the TYPE of the node to work out how to decode it.
    Handles nodes with no value (e.g. when representing NULL by omitting VALUE)
    """

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
        return [unpack_single_value(data, valtype) for data in raw_val]

    return unpack_single_value(raw_val, valtype)


def unpack_single_value(data, cimtype):
    """
    Unpack a single (non-array) CIM typed string value of any CIM type except
    'reference' and return it as a CIM data type object, or Python
    int/long/float, or None.

    data (unicode string): CIM-XML string value, or None (in which case None is
      returned).

    cimtype (string): CIM data type name (e.g. 'datetime') except 'reference',
      or None (in which case a numeric value is assumed).
    """
    if cimtype in ('string', 'char16', 'datetime'):
        return unpack_string(data, cimtype)
    elif cimtype == 'boolean':
        return unpack_boolean(data)
    # None or 'numeric'
    return unpack_numeric(data, cimtype)


def unpack_string(data, cimtype):
    """
    Unpack a CIM-XML string value of one of the CIM types ('string', 'char16',
    'datetime') and return it as a CIM data type object, or None.

    data (unicode string): CIM-XML string value, or None (in which case None is
      returned).

    cimtype (string): CIM data type name (e.g. 'datetime').
    """

    if data is None:
        return None

    if cimtype == 'string':
        value = data
    elif cimtype == 'datetime':
        try:
            value = CIMDateTime(data)
        except ValueError as exc:
            raise ParseError("Invalid datetime value: %r (%s)" % (data, exc))
    elif cimtype == 'char16':
        value = data
        if value == '':
            raise ParseError("Char16 value is empty")
        if len(value) > 1:
            # More than one character, or one character from the UCS-4 set in
            # a narrow Python build (which represents it using surrogates).
            raise ParseError("Char16 value has more than one UCS-2 character: "
                             "%r" % data)
        if len(value) == 1 and ord(value) > 0xFFFF:
            # One character from the UCS-4 set in a wide Python build.
            raise ParseError("Char16 value is a character outside of the "
                             "UCS-2 range: %r" % data)
    else:
        raise ParseError("Invalid CIM type name %r for string: %r" %
                         (cimtype, data))
    return value


def unpack_boolean(data):
    """
    Unpack a string value of CIM type 'boolean' and return its CIM data type
    object, or None.

    data (unicode string): CIM-XML string value, or None (in which case None is
      returned).
    """

    if data is None:
        return None

    # CIM-XML says "These values MUST be treated as case-insensitive"
    # (even though the XML definition requires them to be lowercase.)

    data_ = data.strip().lower()                   # ignore space
    if data_ == 'true':
        return True
    elif data_ == 'false':
        return False
    elif data_ == '':
        warnings.warn("WBEM server sent invalid empty boolean value in a "
                      "CIM-XML response.",
                      UserWarning,
                      stacklevel=_stacklevel_above_module(__name__))
        return None
    else:
        raise ParseError("Invalid boolean value %r" % data)


CIMXML_HEX_PATTERN = re.compile(r'^(\+|\-)?0[xX][0-9a-fA-F]+$')


def unpack_numeric(data, cimtype):
    """
    Unpack a string value of a numeric CIM type and return its CIM data type
    object, or None.

    data (unicode string): CIM-XML string value, or None (in which case None is
      returned).

    cimtype (string): CIM data type name (e.g. 'uint8'), or None (in which case
      the value is returned as a Python int/long or float).
    """

    if data is None:
        return None

    # DSP0201 defines numeric values to be whitespace-tolerant
    data = data.strip()

    # Decode the CIM-XML string representation into a Python number
    #
    # Some notes:
    # * For integer numbers, only decimal and hexadecimal strings are allowed -
    #   no binary or octal.
    # * In Python 2, int() automatically returns a long, if needed.
    # * For real values, DSP0201 defines a subset of the syntax supported by
    #   Python float(), including the special states Inf, -Inf, NaN. The only
    #   known difference is that DSP0201 requires a digit after the decimal
    #   dot, while Python does not.
    if CIMXML_HEX_PATTERN.match(data):
        value = int(data, 16)
    else:
        try:
            value = int(data)
        except ValueError:
            try:
                value = float(data)
            except ValueError:
                raise ParseError("Invalid numeric value %r" % data)

    # Convert the Python number into a CIM data type
    if cimtype is None:
        return value  # int/long or float (used for keybindings)

    # The caller ensured a numeric type for cimtype
    CIMType = type_from_name(cimtype)
    try:
        value = CIMType(value)
    except ValueError as exc:
        raise ParseError(str(exc))

    return value
