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
# down, we produce CIM objects representing the CIM message in digested form.
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

from ._utils import _stacklevel_above_module, _format
from ._nocasedict import NocaseDict
from ._cim_obj import CIMInstance, CIMInstanceName, CIMClass, CIMClassName, \
    CIMProperty, CIMMethod, CIMParameter, CIMQualifier, \
    CIMQualifierDeclaration
from ._cim_types import CIMDateTime, type_from_name
from ._tupletree import xml_to_tupletree_sax
from ._exceptions import CIMXMLParseError, CIMVersionError, DTDVersionError, \
    ProtocolVersionError
from ._warnings import ToleratedServerIssueWarning, MissingKeybindingsWarning


__all__ = []


CIMXML_HEX_PATTERN = re.compile(r'^(\+|\-)?0[xX][0-9a-fA-F]+$')
NUMERIC_CIMTYPE_PATTERN = re.compile(r'^([su]int(8|16|32|64)|real(32|64))$')


def name(tup_tree):
    """
    Return first (name) element of tup_tree
    """
    return tup_tree[0]


def attrs(tup_tree):
    """
    Return second (attributes) element of tup_tree
    """
    return tup_tree[1]


def kids(tup_tree):
    """
    Return a list with the child elements of tup_tree.

    The child elements are represented as tupletree nodes.

    Child nodes that are not XML elements (e.g. text nodes) in tup_tree are
    filtered out.
    """
    k = tup_tree[2]
    assert k is not None
    # pylint: disable=unidiomatic-typecheck
    return [x for x in k if type(x) == tuple]


def pcdata(tup_tree):
    """
    Return the concatenated character data within the child nodes of a
    tuple tree node, as a unicode string. Whitespace is preserved.

    The child nodes must be text nodes (no element nodes).
    """
    k = tup_tree[2]

    # The join() raises TypeError if the tuple tree has child elements.
    # The callers have already ensured that that is not the case.
    # The following assertion has been verified and disabled again for
    # performance reasons:
    # assert all([isinstance(n, six.string_types) for n in k])

    return u''.join(k)


class TupleParser(object):
    """
    Parser for a CIM XML tupletree.
    """

    def __init__(self, conn_id=None):
        """
        conn_id (:term:`connection id`): Connection ID to be used in any
          exceptions that may be raised.
        """
        self.conn_id = conn_id

    # pylint: disable=too-many-arguments
    def check_node(self, tup_tree, nodename, required_attrs=None,
                   optional_attrs=None, allowed_children=None,
                   allow_pcdata=False):
        # pylint: disable=too-many-branches
        """
        Check static local constraints on a tuple tree node.

        The node must have the given nodename.

        Required_attrs is a list/tuple of attribute names that must be present.
        None means the same as an empty list: No attributes are required.

        Optional_attrs is a list/tuple of attribute names that may be present.
        None means the same as an empty list: No attributes are optional.

        Present attributes is a list/tuple of attributes that are neither
        required nor optional, are rejected.

        If allowed_children is not None, it is a list/tuple where the node may
        have children of the given types.  It can be [] for nodes that may not
        have any children. If it's None, no validation of the children is
        performed.

        If allow_pcdata is True, then non-whitespace text nodes are allowed as
        children. (Whitespace text nodes are always allowed as children.)
        """

        if name(tup_tree) != nodename:
            raise CIMXMLParseError(
                _format("Unexpected element {0!A} (expecting element {1!A})",
                        name(tup_tree), nodename),
                conn_id=self.conn_id)

        # Check we have all the required attributes, and no unexpected ones
        tt_attrs = {}
        if attrs(tup_tree) is not None:
            tt_attrs = attrs(tup_tree).copy()

        if required_attrs:
            for attr in required_attrs:
                if attr not in tt_attrs:
                    raise CIMXMLParseError(
                        _format("Element {0!A} is missing required "
                                "attribute {1!A} (only has attributes {2!A})",
                                name(tup_tree), attr, attrs(tup_tree).keys()),
                        conn_id=self.conn_id)
                del tt_attrs[attr]

        if optional_attrs:
            for attr in optional_attrs:
                if attr in tt_attrs:
                    del tt_attrs[attr]

        if tt_attrs:
            raise CIMXMLParseError(
                _format("Element {0!A} has invalid attribute(s) {1!A}",
                        name(tup_tree), tt_attrs.keys()),
                conn_id=self.conn_id)

        if allowed_children is not None:
            invalid_children = []
            for child in kids(tup_tree):
                if name(child) not in allowed_children:
                    invalid_children.append(name(child))
            if invalid_children:
                if not allowed_children:
                    allow_txt = "no child elements are allowed"
                else:
                    allow_txt = _format("allowed are child elements {0!A}",
                                        allowed_children)
                raise CIMXMLParseError(
                    _format("Element {0!A} has invalid child element(s) "
                            "{1!A} ({2})",
                            name(tup_tree), set(invalid_children), allow_txt),
                    conn_id=self.conn_id)

        if not allow_pcdata:
            for child in tup_tree[2]:
                if isinstance(child, six.string_types):
                    if child.lstrip(' \t\n') != '':
                        raise CIMXMLParseError(
                            _format("Element {0!A} has unexpected non-blank "
                                    "text content {1!A}",
                                    name(tup_tree), child),
                            conn_id=self.conn_id)

    def one_child(self, tup_tree, acceptable):
        """
        Parse children of a node with exactly one child node.

        acceptable is a list/tuple of acceptable child nodes

        PCData is ignored.
        """

        k = kids(tup_tree)

        if not k:
            raise CIMXMLParseError(
                _format("Element {0!A} is missing required child element "
                        "{1!A}",
                        name(tup_tree), acceptable),
                conn_id=self.conn_id)
        if len(k) > 1:
            raise CIMXMLParseError(
                _format("Element {0!A} has too many child elements {1!A} "
                        "(allowed is one child element {2!A})",
                        name(tup_tree), [name(t) for t in k], acceptable),
                conn_id=self.conn_id)

        child = k[0]

        if name(child) not in acceptable:
            raise CIMXMLParseError(
                _format("Element {0!A} has invalid child element {1!A} "
                        "(allowed is one child element {2!A})",
                        name(tup_tree), name(child), acceptable),
                conn_id=self.conn_id)

        return self.parse_any(child)

    def optional_child(self, tup_tree, allowed):
        """
        Parse exactly zero or one of a list/tuple of elements from the
        child nodes.
        """

        k = kids(tup_tree)

        if not k:
            return None

        if len(k) == 1:
            return self.one_child(tup_tree, allowed)

        # len(k) > 1
        raise CIMXMLParseError(
            _format("Element {0!A} has too many child elements {1!A} "
                    "(allowed is one optional child element {2!A})",
                    name(tup_tree), [name(t) for t in k], allowed),
            conn_id=self.conn_id)

    def list_of_various(self, tup_tree, acceptable):
        """
        Parse zero or more of a list/tuple of elements from the child nodes.

        Each element of the list can be any type from the list of acceptable
        nodes.
        """

        result = []

        for child in kids(tup_tree):
            if name(child) not in acceptable:
                raise CIMXMLParseError(
                    _format("Element {0!A} has invalid child element {1!A} "
                            "(allowed are child elements {2!A})",
                            name(tup_tree), name(child), acceptable),
                    conn_id=self.conn_id)
            result.append(self.parse_any(child))

        return result

    def list_of_matching(self, tup_tree, matched):
        """
        Parse only the children of particular types defined in the list/tuple
        matched under tup_tree.

        Other children are ignored rather than giving an error.
        """

        result = []

        for child in kids(tup_tree):
            if name(child) not in matched:
                continue
            result.append(self.parse_any(child))

        return result

    def list_of_same(self, tup_tree, acceptable):
        """
        Parse a list/tuple of elements from child nodes.

        The children can be any of the listed acceptable types, but they
        must all be the same.
        """

        k = kids(tup_tree)

        if not k:            # empty list, consistent with list_of_various
            return []

        a_child = name(k[0])
        if a_child not in acceptable:
            raise CIMXMLParseError(
                _format("Element {0!A} has invalid child element {1!A} "
                        "(allowed is a sequence of like elements from {2!A})",
                        name(tup_tree), a_child, acceptable),
                conn_id=self.conn_id)
        result = []
        for child in k:
            if name(child) != a_child:
                raise CIMXMLParseError(
                    _format("Element {0!A} has unlike child element {1!A} "
                            "(sequence must have like elements {2!A})",
                            name(tup_tree), name(child), a_child),
                    conn_id=self.conn_id)
            result.append(self.parse_any(child))

        return result

    def notimplemented(self, tup_tree):
        """
        Raise exception for not implemented CIM-XML element.
        """
        raise CIMXMLParseError(
            _format("Internal Error: Parsing support for CIM-XML element "
                    "{0!A} is not implemented in pywbem", name(tup_tree)),
            conn_id=self.conn_id)

    #
    # Root element
    #

    def parse_cim(self, tup_tree):
        """
        Parse the top level element of CIM/XML message

          ::

            <!ELEMENT CIM (MESSAGE | DECLARATION)>
            <!ATTLIST CIM
                CIMVERSION CDATA #REQUIRED
                DTDVERSION CDATA #REQUIRED>
        """

        self.check_node(tup_tree, 'CIM', ('CIMVERSION', 'DTDVERSION'))

        if not attrs(tup_tree)['CIMVERSION'].startswith('2.'):
            raise CIMVersionError(
                _format("CIMVERSION is {0}, expected 2.x.y",
                        attrs(tup_tree)['CIMVERSION']),
                conn_id=self.conn_id)

        if not attrs(tup_tree)['DTDVERSION'].startswith('2.'):
            raise DTDVersionError(
                _format("DTDVERSION is {0}, expected 2.x.y",
                        attrs(tup_tree)['DTDVERSION']),
                conn_id=self.conn_id)

        child = self.one_child(tup_tree, ('MESSAGE', 'DECLARATION'))

        return name(tup_tree), attrs(tup_tree), child

    #
    # Declaration elements
    #

    def parse_declaration(self, tup_tree):
        """
          ::

            <!ELEMENT DECLARATION ( DECLGROUP | DECLGROUP.WITHNAME |
                                    DECLGROUP.WITHPATH )+>

        Note: Pywbem only supports the DECLGROUP child, at this point.
        """

        self.check_node(tup_tree, 'DECLARATION')

        child = self.one_child(tup_tree, ('DECLGROUP',))

        return name(tup_tree), attrs(tup_tree), child

    def parse_declgroup(self, tup_tree):
        """
          ::

            <!ELEMENT DECLGROUP ( (LOCALNAMESPACEPATH|NAMESPACEPATH)?,
                                  QUALIFIER.DECLARATION*, VALUE.OBJECT* )>

        Note: Pywbem only supports the QUALIFIER.DECLARATION and VALUE.OBJECT
              children, and with a multiplicity of 1, at this point.
        """

        self.check_node(tup_tree, 'DECLGROUP')

        child = self.one_child(tup_tree,
                               ('QUALIFIER.DECLARATION', 'VALUE.OBJECT'))

        return name(tup_tree), attrs(tup_tree), child

    def parse_declgroup_withname(self, tup_tree):  # not implemented
        """
        Parsing support for the DECLGROUP.WITHNAME element is not implemented
        in pywbem at this point.

        This is a limitation of pywbem.
        """
        self.notimplemented(tup_tree)

    def parse_declgroup_withpath(self, tup_tree):  # not implemented
        """
        Parsing support for the DECLGROUP.WITHPATH element is not implemented
        in pywbem at this point.

        This is a limitation of pywbem.
        """
        self.notimplemented(tup_tree)

    #
    # Object value elements
    #

    def parse_value(self, tup_tree):
        """
        Parse a VALUE element and return its text content as a unicode string.
        Whitespace is preserved.

        The conversion of the text representation of the value to a CIM data
        type object requires CIM type information which is not available on the
        VALUE element and therefore will be done when parsing higher level
        elements that have that information.

          ::

            <!ELEMENT VALUE (#PCDATA)>
        """

        self.check_node(tup_tree, 'VALUE', (), (), (), allow_pcdata=True)

        return pcdata(tup_tree)

    def parse_value_array(self, tup_tree):
        """
        Parse a VALUE.ARRAY element and return the items in the array as a list
        of unicode strings, or None for NULL items. Whitespace is preserved.

          ::

            <!ELEMENT VALUE.ARRAY (VALUE | VALUE.NULL)*>
        """

        self.check_node(tup_tree, 'VALUE.ARRAY')

        children = self.list_of_various(tup_tree, ('VALUE', 'VALUE.NULL'))

        return children

    def parse_value_reference(self, tup_tree):
        """
        Parse a VALUE.REFERENCE element and return the instance path or class
        path it represents as a CIMInstanceName or CIMClassName object,
        respectively.

          ::

            <!ELEMENT VALUE.REFERENCE (CLASSPATH | LOCALCLASSPATH | CLASSNAME |
                                       INSTANCEPATH | LOCALINSTANCEPATH |
                                       INSTANCENAME)>
        """

        self.check_node(tup_tree, 'VALUE.REFERENCE')

        child = self.one_child(tup_tree,
                               ('CLASSPATH', 'LOCALCLASSPATH', 'CLASSNAME',
                                'INSTANCEPATH', 'LOCALINSTANCEPATH',
                                'INSTANCENAME'))

        return child

    def parse_value_refarray(self, tup_tree):
        """
        Parse a VALUE.REFARRAY element and return the array of instance paths
        or class paths it represents as a list of CIMInstanceName or
        CIMClassName objects, respectively.

          ::

            <!ELEMENT VALUE.REFARRAY (VALUE.REFERENCE | VALUE.NULL)*>
        """

        self.check_node(tup_tree, 'VALUE.REFARRAY')

        children = self.list_of_various(tup_tree,
                                        ('VALUE.REFERENCE', 'VALUE.NULL'))

        return children

    def parse_value_object(self, tup_tree):
        """
          ::

            <!ELEMENT VALUE.OBJECT (CLASS | INSTANCE)>
        """

        self.check_node(tup_tree, 'VALUE.OBJECT')

        child = self.one_child(tup_tree, ('CLASS', 'INSTANCE'))

        return (name(tup_tree), attrs(tup_tree), child)

    def parse_value_namedinstance(self, tup_tree):
        """
          ::

            <!ELEMENT VALUE.NAMEDINSTANCE (INSTANCENAME, INSTANCE)>

        Returns:
            CIMInstance object with path set (without host or namespace).
        """

        self.check_node(tup_tree, 'VALUE.NAMEDINSTANCE')

        k = kids(tup_tree)
        if len(k) != 2:
            raise CIMXMLParseError(
                _format("Element {0!A} has invalid number of child elements "
                        "{1!A} (expecting two child elements "
                        "(INSTANCENAME, INSTANCE))",
                        name(tup_tree), k),
                conn_id=self.conn_id)

        inst_path = self.parse_instancename(k[0])
        instance = self.parse_instance(k[1])
        instance.path = inst_path

        return instance

    def parse_value_instancewithpath(self, tup_tree):
        """
        The VALUE.INSTANCEWITHPATH is used to define a value that comprises
        a single CIMInstance with additional information that defines the
        absolute path to that object.

          ::

            <!ELEMENT VALUE.INSTANCEWITHPATH (INSTANCEPATH, INSTANCE)>
        """

        self.check_node(tup_tree, 'VALUE.INSTANCEWITHPATH')

        k = kids(tup_tree)
        if len(k) != 2:
            raise CIMXMLParseError(
                _format("Element {0!A} has invalid number of child elements "
                        "{1!A} (expecting two child elements "
                        "(INSTANCEPATH, INSTANCE))",
                        name(tup_tree), k),
                conn_id=self.conn_id)

        inst_path = self.parse_instancepath(k[0])
        instance = self.parse_instance(k[1])
        instance.path = inst_path

        return instance

    def parse_value_namedobject(self, tup_tree):
        """
          ::

            <!ELEMENT VALUE.NAMEDOBJECT (CLASS | (INSTANCENAME, INSTANCE))>
        """

        self.check_node(tup_tree, 'VALUE.NAMEDOBJECT')

        k = kids(tup_tree)
        len_k = len(k)

        if len_k == 2:
            inst_path = self.parse_instancename(k[0])
            _object = self.parse_instance(k[1])
            _object.path = inst_path
            return (name(tup_tree), attrs(tup_tree), _object)

        if len_k == 1:
            _object = self.parse_class(k[0])
            return (name(tup_tree), attrs(tup_tree), _object)

        raise CIMXMLParseError(
            _format("Element {0!A} has invalid number of child elements "
                    "{1!A} (expecting one or two child elements "
                    "(CLASS | (INSTANCENAME, INSTANCE)))",
                    name(tup_tree), k),
            conn_id=self.conn_id)

    # pylint: disable=invalid-name
    def parse_value_objectwithlocalpath(self, tup_tree):
        """
          ::

            <!ELEMENT VALUE.OBJECTWITHLOCALPATH ((LOCALCLASSPATH, CLASS) |
                                                (LOCALINSTANCEPATH, INSTANCE))>

        Returns:
            tupletree with child item that is:
            - for class-level use: a tuple(CIMClassName, CIMClass) where the
              path of the CIMClass object is set (with namespace).
            - for class-level use: a CIMInstance object with its path set
              (with namespace).
        """

        self.check_node(tup_tree, 'VALUE.OBJECTWITHLOCALPATH')

        k = kids(tup_tree)

        if len(k) != 2:
            raise CIMXMLParseError(
                _format("Element {0!A} has invalid number of child elements "
                        "{1!A} (expecting two child elements "
                        "((LOCALCLASSPATH, CLASS) | (LOCALINSTANCEPATH, "
                        "INSTANCE)))", name(tup_tree), k),
                conn_id=self.conn_id)

        if name(k[0]) == 'LOCALCLASSPATH':
            # Note: Before pywbem 0.12, CIMClass did not have a path, therefore
            # classpath and class were returned as a tuple. In pywbem 0.12,
            # CIMClass got a path, but they are still returned as a tuple.
            class_path = self.parse_localclasspath(k[0])
            klass = self.parse_class(k[1])
            klass.path = class_path
            _object = (class_path, klass)
        else:  # LOCALINSTANCEPATH
            # convert tuple to CIMInstance object with path set
            inst_path = self.parse_localinstancepath(k[0])
            _object = self.parse_instance(k[1])
            _object.path = inst_path

        return (name(tup_tree), attrs(tup_tree), _object)

    def parse_value_objectwithpath(self, tup_tree):
        """
          ::

            <!ELEMENT VALUE.OBJECTWITHPATH ((CLASSPATH, CLASS) |
                                            (INSTANCEPATH, INSTANCE))>

        Returns:
            tupletree with child item that is:
            - for class-level use: a tuple(CIMClassName, CIMClass) where the
              path of the CIMClass object is set (with namespace and host).
            - for class-level use: a CIMInstance object with its path set
              (with namespace and host).
        """

        self.check_node(tup_tree, 'VALUE.OBJECTWITHPATH')

        k = kids(tup_tree)

        if len(k) != 2:
            raise CIMXMLParseError(
                _format("Element {0!A} has invalid number of child elements "
                        "{1!A} (expecting two child elements "
                        "((CLASSPATH, CLASS) | (INSTANCEPATH, INSTANCE)))",
                        name(tup_tree), k),
                conn_id=self.conn_id)

        if name(k[0]) == 'CLASSPATH':
            # Note: Before pywbem 0.12, CIMClass did not have a path, therefore
            # classpath and class were returned as a tuple. In pywbem 0.12,
            # CIMClass got a path, but they are still returned as a tuple.
            class_path = self.parse_classpath(k[0])
            klass = self.parse_class(k[1])
            klass.path = class_path
            _object = (class_path, klass)
        else:  # INSTANCEPATH
            # convert tuple to CIMInstance object with path set
            inst_path = self.parse_instancepath(k[0])
            _object = self.parse_instance(k[1])
            _object.path = inst_path

        return (name(tup_tree), attrs(tup_tree), _object)

    def parse_value_null(self, tup_tree):
        """
        Parse a VALUE.NULL element and return None.

          ::

            <!ELEMENT VALUE.NULL EMPTY>
        """

        self.check_node(tup_tree, 'VALUE.NULL', (), (), ())

        return None

    #
    # Object naming and locating elements
    #

    def parse_namespacepath(self, tup_tree):
        """
        Parse a NAMESPACEPATH element and return the host and namespace it
        represents as a tuple (host, namespace).

          ::

            <!ELEMENT NAMESPACEPATH (HOST, LOCALNAMESPACEPATH)>
        """

        self.check_node(tup_tree, 'NAMESPACEPATH')

        k = kids(tup_tree)

        if len(k) != 2:
            raise CIMXMLParseError(
                _format("Element {0!A} has invalid number of child elements "
                        "{1!A} (expecting two child elements "
                        "(HOST, LOCALNAMESPACEPATH))", name(tup_tree), k),
                conn_id=self.conn_id)

        host = self.parse_host(k[0])
        namespace = self.parse_localnamespacepath(k[1])

        return (host, namespace)

    def parse_localnamespacepath(self, tup_tree):
        """
        Parse a LOCALNAMESPACEPATH element and return the namespace it
        represents as a unicode string.

        The namespace is formed by joining the namespace components (one from
        each NAMESPACE child element) with a slash (e.g. to "root/cimv2").

          ::

            <!ELEMENT LOCALNAMESPACEPATH (NAMESPACE+)>
        """

        self.check_node(tup_tree, 'LOCALNAMESPACEPATH', (), (), ('NAMESPACE',))

        if not kids(tup_tree):
            raise CIMXMLParseError(
                _format("Element {0!A} is missing required child elements "
                        "(expecting one or more child elements 'NAMESPACE')",
                        name(tup_tree)),
                conn_id=self.conn_id)

        # self.list_of_various() has the same effect as self.list_of_same()
        # when used with a single allowed child element, but is a little
        # faster.
        ns_list = self.list_of_various(tup_tree, ('NAMESPACE',))

        return u'/'.join(ns_list)

    def parse_host(self, tup_tree):
        """
        Parse a HOST element and return its text content as a unicode string.

          ::

            <!ELEMENT HOST (#PCDATA)>
        """

        self.check_node(tup_tree, 'HOST', (), (), (), allow_pcdata=True)

        return pcdata(tup_tree)

    def parse_namespace(self, tup_tree):
        """
        Parse a NAMESPACE element and return the namespace component it
        represents (e.g. "root") as a unicode string.

          ::

            <!ELEMENT NAMESPACE EMPTY>
            <!ATTLIST NAMESPACE
                %CIMName;>
        """

        self.check_node(tup_tree, 'NAMESPACE', ('NAME',), (), ())

        return attrs(tup_tree)['NAME']

    def parse_classpath(self, tup_tree):
        """
        Parse a CLASSPATH element and return the class path it represents as a
        CIMClassName object.

          ::

            <!ELEMENT CLASSPATH (NAMESPACEPATH, CLASSNAME)>
        """

        self.check_node(tup_tree, 'CLASSPATH')

        k = kids(tup_tree)

        if len(k) != 2:
            raise CIMXMLParseError(
                _format("Element {0!A} has invalid number of child elements "
                        "{1!A} (expecting two child elements "
                        "(NAMESPACEPATH, CLASSNAME))", name(tup_tree), k),
                conn_id=self.conn_id)

        host, namespace = self.parse_namespacepath(k[0])
        class_path = self.parse_classname(k[1])
        class_path.host = host
        class_path.namespace = namespace

        return class_path

    def parse_localclasspath(self, tup_tree):
        """
        Parse a LOCALCLASSPATH element and return the class path it represents
        as a CIMClassName object.

          ::

            <!ELEMENT LOCALCLASSPATH (LOCALNAMESPACEPATH, CLASSNAME)>
        """

        self.check_node(tup_tree, 'LOCALCLASSPATH')

        k = kids(tup_tree)

        if len(k) != 2:
            raise CIMXMLParseError(
                _format("Element {0!A} has invalid number of child elements "
                        "{1!A} (expecting two child elements "
                        "(LOCALNAMESPACEPATH, CLASSNAME))", name(tup_tree), k),
                conn_id=self.conn_id)

        namespace = self.parse_localnamespacepath(k[0])
        class_path = self.parse_classname(k[1])
        class_path.namespace = namespace

        return class_path

    def parse_classname(self, tup_tree):
        """
        Parse a CLASSNAME element and return the class path it represents as a
        CIMClassName object.

          ::

            <!ELEMENT CLASSNAME EMPTY>
            <!ATTLIST CLASSNAME
                %CIMName;>

        Returns:
            CIMClassName object (without namespace or host)
        """

        self.check_node(tup_tree, 'CLASSNAME', ('NAME',), (), ())

        classname = attrs(tup_tree)['NAME']

        # The following does not raise any exception:
        class_path = CIMClassName(classname)

        return class_path

    def parse_instancepath(self, tup_tree):
        """
        Parse an INSTANCEPATH element and return the instance path it
        represents as a CIMInstanceName object.

          ::

            <!ELEMENT INSTANCEPATH (NAMESPACEPATH, INSTANCENAME)>
        """

        self.check_node(tup_tree, 'INSTANCEPATH')

        k = kids(tup_tree)

        if len(k) != 2:
            raise CIMXMLParseError(
                _format("Element {0!A} has invalid number of child elements "
                        "{1!A} (expecting two child elements "
                        "(NAMESPACEPATH, INSTANCENAME))", name(tup_tree), k),
                conn_id=self.conn_id)

        host, namespace = self.parse_namespacepath(k[0])
        inst_path = self.parse_instancename(k[1])
        inst_path.host = host
        inst_path.namespace = namespace

        return inst_path

    def parse_localinstancepath(self, tup_tree):
        """
        Parse a LOCALINSTANCEPATH element and return the instance path it
        represents as a CIMInstanceName object.

          ::

            <!ELEMENT LOCALINSTANCEPATH (LOCALNAMESPACEPATH, INSTANCENAME)>
        """

        self.check_node(tup_tree, 'LOCALINSTANCEPATH')

        k = kids(tup_tree)

        if len(k) != 2:
            raise CIMXMLParseError(
                _format("Element {0!A} has invalid number of child elements "
                        "{1!A} (expecting two child elements "
                        "(LOCALNAMESPACEPATH, INSTANCENAME))",
                        name(tup_tree), k),
                conn_id=self.conn_id)

        namespace = self.parse_localnamespacepath(k[0])
        inst_path = self.parse_instancename(k[1])
        inst_path.namespace = namespace

        return inst_path

    def parse_instancename(self, tup_tree):
        """
        Parse an INSTANCENAME element and return the instance path it
        represents as a CIMInstanceName object.

          ::

            <!ELEMENT INSTANCENAME (KEYBINDING* | KEYVALUE? |
                                    VALUE.REFERENCE?)>
            <!ATTLIST INSTANCENAME
                %ClassName;>
        """

        self.check_node(tup_tree, 'INSTANCENAME', ('CLASSNAME',))

        classname = attrs(tup_tree)['CLASSNAME']

        k = kids(tup_tree)
        if not k:
            # An instance path without keys.
            # DSP0004 requires in section 8.2.5 that addressable instances must
            # have keys, so consequently an instance path must have keybindings.
            # DSP0201 allows for INSTANCENAME without keys, and states that
            # would be for "a singleton instance of a keyless class". That is
            # clearly contradicting DSP0004. Since some WBEM servers have
            # implemented support for the notion of a keyless instance path,
            # pywbem supports this as well, returning a CIMInstanceName object
            # without keybindings, but also issues a warning.
            warnings.warn(
                _format(
                    "WBEM server sent invalid instance path for classname "
                    "{0!A} without any keys in a CIM-XML response",
                    classname),
                MissingKeybindingsWarning,
                stacklevel=_stacklevel_above_module('pywbem'))
            return CIMInstanceName(classname, {})

        kid0 = k[0]
        k0_name = name(kid0)

        if k0_name in ('KEYVALUE', 'VALUE.REFERENCE'):
            # An instance path with a single unnamed key.
            # DSP0004 defines in figure 8 in 8.2.5 "Object Path for Instance
            # Objects" that each key has a name and a value.
            # However, the grammar in DSP0201 allows this case.
            # When receiving CIM-XML, pywbem attempts to be as tolerant as
            # possible, so this case is tolerated.
            if len(k) != 1:
                raise CIMXMLParseError(
                    _format("Element {0!A} has more than one child element "
                            "{1!A} (expecting child elements "
                            "(KEYBINDING* | KEYVALUE? | VALUE.REFERENCE?))",
                            name(tup_tree), k0_name),
                    conn_id=self.conn_id)

            val = self.parse_any(kid0)
            try:
                return CIMInstanceName(classname, {None: val})
            except (TypeError, ValueError) as exc:
                new_exc = CIMXMLParseError(
                    _format("Element {0!A} has invalid input for creating a "
                            "CIMInstanceName object for class {1!A}: {2}; "
                            "CIM-XML tuple tree: {3}",
                            name(tup_tree), classname, exc, tup_tree),
                    conn_id=self.conn_id)
                new_exc.__cause__ = None
                raise new_exc

        if k0_name == 'KEYBINDING':
            # An instance path with one or more named keys.
            kbs = {}
            # self.list_of_various() has the same effect as self.list_of_same()
            # when used with a single allowed child element, but is a little
            # faster.
            for key_bind in self.list_of_various(tup_tree, ('KEYBINDING',)):
                kbs.update(key_bind)
            try:
                return CIMInstanceName(classname, kbs)
            except (TypeError, ValueError) as exc:
                new_exc = CIMXMLParseError(
                    _format("Element {0!A} has invalid input for creating a "
                            "CIMInstanceName object for class {1!A}: {2}; "
                            "CIM-XML tuple tree: {3}",
                            name(tup_tree), classname, exc, tup_tree),
                    conn_id=self.conn_id)
                new_exc.__cause__ = None
                raise new_exc

        raise CIMXMLParseError(
            _format("Element {0!A} has invalid child elements {1!A} "
                    "(expecting child elements "
                    "(KEYBINDING* | KEYVALUE? | VALUE.REFERENCE?))",
                    name(tup_tree), k),
            conn_id=self.conn_id)

    def parse_objectpath(self, tup_tree):
        """
          ::

            <!ELEMENT OBJECTPATH (INSTANCEPATH | CLASSPATH)>

        Returns:
            tupletree with child item that is a single CIMInstanceName or
            CIMClassName object (with host and namespace).
        """

        self.check_node(tup_tree, 'OBJECTPATH')

        child = self.one_child(tup_tree, ('INSTANCEPATH', 'CLASSPATH'))

        return (name(tup_tree), attrs(tup_tree), child)

    def parse_keybinding(self, tup_tree):
        """
        Parse a KEYBINDING element and return the keybinding as a one-item
        dictionary from name to value, where the value is a CIM data type
        object, based upon the type information in the child elements, if
        present. If no type information is present, numeric values are returned
        as int or float.

          ::

            <!ELEMENT KEYBINDING (KEYVALUE | VALUE.REFERENCE)>
            <!ATTLIST KEYBINDING
                %CIMName;>
        """

        self.check_node(tup_tree, 'KEYBINDING', ('NAME',))

        child = self.one_child(tup_tree, ('KEYVALUE', 'VALUE.REFERENCE'))

        return {attrs(tup_tree)['NAME']: child}

    def parse_keyvalue(self, tup_tree):
        """
        Parse a KEYVALUE element and return the keybinding value as a CIM data
        type object, based upon the type information in its VALUETYPE and TYPE
        attributes, if present.

        If TYPE is specified, its value is used to create the corresponding CIM
        data type object. in this case, VALUETYPE is ignored and may be
        omitted. Discrepancies between TYPE and VALUETYPE are not checked.

        Note that DSP0201 does not detail how such discrepancies should be
        resolved, including the precedence of the DTD-defined default for
        VALUETYPE over a specified TYPE value.

        If TYPE is not specified but VALUETYPE is specified, the CIM type is
        defaulted for a VALUETYPE of 'string' and 'boolean'. For a VALUETYPE of
        'numeric', the CIM type remains undetermined and the numeric values are
        returned as Python int/long or float objects.

          ::

            <!ELEMENT KEYVALUE (#PCDATA)>
            <!ATTLIST KEYVALUE
                VALUETYPE (string | boolean | numeric) "string"
                %CIMType;    #IMPLIED>  # DTD <2.4
                %CIMType;    #REQUIRED>  # DTD >=2.4
        """

        # In order to be backwards compatible to WBEM servers that implement
        # DTD <2.4, pywbem treats the TYPE attribute as optional.
        self.check_node(tup_tree, 'KEYVALUE', (), ('VALUETYPE', 'TYPE'), (),
                        allow_pcdata=True)

        data = pcdata(tup_tree)
        attrl = attrs(tup_tree)

        valuetype = attrl.get('VALUETYPE', None)
        cimtype = attrl.get('TYPE', None)

        # Tolerate that some WBEM servers return TYPE="" instead of omitting
        # TYPE (e.g. the WBEM Solutions server).
        if cimtype == '':
            cimtype = None

        # Default the CIM type from VALUETYPE if not specified in TYPE
        if cimtype is None:
            if valuetype is None or valuetype == 'string':
                cimtype = 'string'
            elif valuetype == 'boolean':
                cimtype = 'boolean'
            elif valuetype == 'numeric':
                pass
            else:
                raise CIMXMLParseError(
                    _format("Element {0!A} has invalid 'VALUETYPE' attribute "
                            "value {1!A}", name(tup_tree), valuetype),
                    conn_id=self.conn_id)

        return self.unpack_single_value(data, cimtype)

    #
    # Object definition elements
    #

    def parse_class(self, tup_tree):
        """
        Parse CLASS element returning a CIMClass if the parse was successful.

          ::

            <!ELEMENT CLASS (QUALIFIER*, (PROPERTY | PROPERTY.ARRAY |
                                          PROPERTY.REFERENCE)*, METHOD*)>
            <!ATTLIST CLASS
                %CIMName;
                %SuperClass;>
        """

        # Doesn't check ordering of elements, but it's not very important
        self.check_node(tup_tree, 'CLASS', ('NAME',), ('SUPERCLASS',),
                        ('QUALIFIER', 'PROPERTY', 'PROPERTY.REFERENCE',
                         'PROPERTY.ARRAY', 'METHOD'))

        attrl = attrs(tup_tree)

        classname = attrl['NAME']
        superclass = attrl.get('SUPERCLASS', None)
        properties = self.list_of_matching(tup_tree,
                                           ('PROPERTY', 'PROPERTY.REFERENCE',
                                            'PROPERTY.ARRAY'))
        qualifiers = self.list_of_matching(tup_tree, ('QUALIFIER',))
        methods = self.list_of_matching(tup_tree, ('METHOD',))

        # CIMClass() can raise TypeError and ValueError due to invalid
        # init arguments, but this cannot possibly be triggered here.
        return CIMClass(
            classname, superclass=superclass, properties=properties,
            methods=methods, qualifiers=qualifiers)

    def parse_instance(self, tup_tree):
        """
        Return a CIMInstance.

        The instance contains the properties, qualifiers and classname for
        the instance.

          ::

            <!ELEMENT INSTANCE (QUALIFIER*, (PROPERTY | PROPERTY.ARRAY |
                                             PROPERTY.REFERENCE)*)>
            <!ATTLIST INSTANCE
                %ClassName;
                xml:lang NMTOKEN #IMPLIED>
        """

        self.check_node(tup_tree, 'INSTANCE', ('CLASSNAME',), ('xml:lang',),
                        ('QUALIFIER', 'PROPERTY', 'PROPERTY.ARRAY',
                         'PROPERTY.REFERENCE'))

        # The 'xml:lang' attribute is tolerated but ignored.

        # Note: The check above does not enforce the ordering constraint in the
        # DTD that QUALIFIER elements must appear before PROPERTY* elements.

        classname = attrs(tup_tree)['CLASSNAME']

        qualifiers = self.list_of_matching(tup_tree, ('QUALIFIER',))

        # This may raise CIMXMLParseError e.g. when a reference property is set
        # to an invalid reference value (e.g. to a class).
        props = self.list_of_matching(tup_tree,
                                      ('PROPERTY.REFERENCE', 'PROPERTY',
                                       'PROPERTY.ARRAY'))

        # CIMInstance() can raise TypeError and ValueError due to invalid
        # init arguments, but this cannot possibly be triggered here.
        inst = CIMInstance(classname, qualifiers=qualifiers)
        for prop in props:
            inst.__setitem__(prop.name, prop)

        return inst

    def parse_scope(self, tup_tree):
        """
        Parse a SCOPE element and return a dictionary with an item for each
        specified scope attribute.

        The keys of the dictionary items are the scope names in upper case; the
        values are the Python boolean values True or False.

        Unspecified scope attributes are not represented in the returned
        dictionary; the user is expected to assume their default value of
        False.

        The returned dictionary does not preserve order of the scope
        attributes.

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

        self.check_node(tup_tree, 'SCOPE', (),
                        ('CLASS', 'ASSOCIATION', 'REFERENCE', 'PROPERTY',
                         'METHOD', 'PARAMETER', 'INDICATION'), ())

        # Even though XML attributes do not preserve order, we store the
        # scopes in an ordered dict to avoid a warning further down the
        # road.
        scopes = NocaseDict()
        for k, v in attrs(tup_tree).items():
            v_ = self.unpack_boolean(v)
            if v_ is None:
                raise CIMXMLParseError(
                    _format("Element {0!A} has an invalid value {1!A} for its "
                            "boolean attribute {2!A}", name(tup_tree), v, k),
                    conn_id=self.conn_id)
            scopes[k] = v_
        return scopes

    def parse_qualifier_declaration(self, tup_tree):
        """
        Parse QUALIFIER.DECLARATION element.

          ::

            <!ELEMENT QUALIFIER.DECLARATION (SCOPE?, (VALUE | VALUE.ARRAY)?)>
            <!ATTLIST QUALIFIER.DECLARATION
                %CIMName;
                %CIMType;               #REQUIRED
                ISARRAY    (true|false) #IMPLIED
                %ArraySize;
                %QualifierFlavor;>
        """

        self.check_node(tup_tree, 'QUALIFIER.DECLARATION',
                        ('NAME', 'TYPE'),
                        ('ISARRAY', 'ARRAYSIZE', 'OVERRIDABLE', 'TOSUBCLASS',
                         'TOINSTANCE', 'TRANSLATABLE'),
                        ('SCOPE', 'VALUE', 'VALUE.ARRAY'))

        attrl = attrs(tup_tree)
        qname = attrl['NAME']
        _type = attrl['TYPE']

        is_array = self.unpack_boolean(attrl.get('ISARRAY', 'false'))

        array_size = attrl.get('ARRAYSIZE', None)
        if array_size is not None:
            # Issue #1044: Clarify if hex support is needed.
            array_size = int(array_size)

        scopes = None
        value = None
        for child in kids(tup_tree):
            if name(child) == 'SCOPE':
                if scopes is not None:
                    raise CIMXMLParseError(
                        _format("Element {0!A} has more than one child "
                                "element {1!A} (allowed is only one)",
                                name(tup_tree), name(child)),
                        conn_id=self.conn_id)
                scopes = self.parse_any(child)
            else:
                # Process a single 'VALUE' or 'VALUE.ARRAY' child.
                # Raises CIMXMLParseError for any other elements or if it
                # occurs more than once.
                assert value is None  # Verify we come here first time in loop

                # May raise CIMXMLParseError for invalid values
                value = self.unpack_value(tup_tree)

        overridable = self.unpack_boolean(attrl.get('OVERRIDABLE', 'true'))
        tosubclass = self.unpack_boolean(attrl.get('TOSUBCLASS', 'true'))
        toinstance = self.unpack_boolean(attrl.get('TOINSTANCE', 'false'))
        translatable = self.unpack_boolean(attrl.get('TRANSLATABLE', 'false'))

        try:
            qual_decl = CIMQualifierDeclaration(
                qname, _type, value, is_array, array_size, scopes,
                overridable=overridable, tosubclass=tosubclass,
                toinstance=toinstance, translatable=translatable)
        except (TypeError, ValueError) as exc:
            new_exc = CIMXMLParseError(
                _format("Element {0!A} has invalid input for creating a "
                        "CIMQualifierDeclaration object for qualifier {1!A}: "
                        "{2}; CIM-XML tuple tree: {3}",
                        name(tup_tree), qname, exc, tup_tree),
                conn_id=self.conn_id)
            new_exc.__cause__ = None
            raise new_exc

        return qual_decl

    def parse_qualifier(self, tup_tree):
        """
        Parse QUALIFIER element returning CIMQualifier.

          ::

            <!ELEMENT QUALIFIER (VALUE | VALUE.ARRAY)>
            <!ATTLIST QUALIFIER
                %CIMName;
                %CIMType;              #REQUIRED
                %Propagated;
                %QualifierFlavor;
                xml:lang NMTOKEN #IMPLIED>
        """

        self.check_node(tup_tree, 'QUALIFIER', ('NAME', 'TYPE'),
                        ('OVERRIDABLE', 'TOSUBCLASS', 'TOINSTANCE',
                         'TRANSLATABLE', 'PROPAGATED', 'xml:lang'),
                        ('VALUE', 'VALUE.ARRAY'))

        # The 'xml:lang' attribute is tolerated but ignored.

        attrl = attrs(tup_tree)
        qname = attrl['NAME']
        _type = attrl['TYPE']

        # May raise CIMXMLParseError for invalid values
        value = self.unpack_value(tup_tree)

        propagated = self.unpack_boolean(attrl.get('PROPAGATED', 'false'))
        overridable = self.unpack_boolean(attrl.get('OVERRIDABLE', 'true'))
        tosubclass = self.unpack_boolean(attrl.get('TOSUBCLASS', 'true'))
        toinstance = self.unpack_boolean(attrl.get('TOINSTANCE', 'false'))
        translatable = self.unpack_boolean(attrl.get('TRANSLATABLE', 'false'))

        try:
            qual = CIMQualifier(
                qname, value, _type, propagated=propagated,
                overridable=overridable, tosubclass=tosubclass,
                toinstance=toinstance, translatable=translatable)
        except (TypeError, ValueError) as exc:
            new_exc = CIMXMLParseError(
                _format("Element {0!A} has invalid input for creating a "
                        "CIMQualifier object for qualifier {1!A}: {2}; "
                        "CIM-XML tuple tree: {3}",
                        name(tup_tree), qname, exc, tup_tree),
                conn_id=self.conn_id)
            new_exc.__cause__ = None
            raise new_exc

        return qual

    def parse_property(self, tup_tree):
        """
        Parse PROPERTY into a CIMProperty object.

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

        self.check_node(tup_tree, 'PROPERTY', ('TYPE', 'NAME'),
                        ('CLASSORIGIN', 'PROPAGATED', 'EmbeddedObject',
                         'EMBEDDEDOBJECT', 'xml:lang'),
                        ('QUALIFIER', 'VALUE'))

        # The 'xml:lang' attribute is tolerated but ignored.

        attrl = attrs(tup_tree)
        pname = attrl['NAME']
        ptype = attrl['TYPE']

        # May raise CIMXMLParseError for invalid values
        val = self.unpack_value(tup_tree)

        class_origin = attrl.get('CLASSORIGIN', None)
        propagated = self.unpack_boolean(attrl.get('PROPAGATED', 'false'))

        qualifiers = self.list_of_matching(tup_tree, ('QUALIFIER',))

        embedded_object = False
        if 'EmbeddedObject' in attrl or 'EMBEDDEDOBJECT' in attrl:
            try:
                embedded_object = attrl['EmbeddedObject']
            except KeyError:
                embedded_object = attrl['EMBEDDEDOBJECT']
        if embedded_object:
            val = self.parse_embeddedObject(val)

        try:
            return CIMProperty(
                pname, val, type=ptype, is_array=False,
                class_origin=class_origin, propagated=propagated,
                embedded_object=embedded_object, qualifiers=qualifiers)
        except (TypeError, ValueError) as exc:
            new_exc = CIMXMLParseError(
                _format("Element {0!A} has invalid input for creating a "
                        "CIMProperty object for property {1!A}: {2}; "
                        "CIM-XML tuple tree: {3}",
                        name(tup_tree), pname, exc, tup_tree),
                conn_id=self.conn_id)
            new_exc.__cause__ = None
            raise new_exc

    def parse_property_array(self, tup_tree):
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

        self.check_node(tup_tree, 'PROPERTY.ARRAY', ('NAME', 'TYPE'),
                        ('CLASSORIGIN', 'PROPAGATED', 'ARRAYSIZE',
                         'EmbeddedObject', 'EMBEDDEDOBJECT', 'xml:lang'),
                        ('QUALIFIER', 'VALUE.ARRAY'))

        # The 'xml:lang' attribute is tolerated but ignored.

        attrl = attrs(tup_tree)
        pname = attrl['NAME']
        ptype = attrl['TYPE']

        # May raise CIMXMLParseError for invalid values
        values = self.unpack_value(tup_tree)

        class_origin = attrl.get('CLASSORIGIN', None)
        propagated = self.unpack_boolean(attrl.get('PROPAGATED', 'false'))

        qualifiers = self.list_of_matching(tup_tree, ('QUALIFIER',))

        array_size = attrl.get('ARRAYSIZE', None)
        if array_size is not None:
            # Issue #1044: Clarify if hex support is needed.
            array_size = int(array_size)

        embedded_object = False
        if 'EmbeddedObject' in attrl or 'EMBEDDEDOBJECT' in attrl:
            try:
                embedded_object = attrl['EmbeddedObject']
            except KeyError:
                embedded_object = attrl['EMBEDDEDOBJECT']
        if embedded_object:
            values = self.parse_embeddedObject(values)

        try:
            return CIMProperty(
                pname, values, type=ptype, is_array=True, array_size=array_size,
                class_origin=class_origin, propagated=propagated,
                embedded_object=embedded_object, qualifiers=qualifiers)
        except (TypeError, ValueError) as exc:
            new_exc = CIMXMLParseError(
                _format("Element {0!A} has invalid input for creating a "
                        "CIMProperty object for property {1!A}: {2}; "
                        "CIM-XML tuple tree: {3}",
                        name(tup_tree), pname, exc, tup_tree),
                conn_id=self.conn_id)
            new_exc.__cause__ = None
            raise new_exc

    def parse_property_reference(self, tup_tree):
        """
          ::

            <!ELEMENT PROPERTY.REFERENCE (QUALIFIER*, (VALUE.REFERENCE)?)>
            <!ATTLIST PROPERTY.REFERENCE
                %CIMName;
                %ReferenceClass;
                %ClassOrigin;
                %Propagated;>
        """

        self.check_node(tup_tree, 'PROPERTY.REFERENCE', ('NAME',),
                        ('REFERENCECLASS', 'CLASSORIGIN', 'PROPAGATED'),
                        ('QUALIFIER', 'VALUE.REFERENCE'))

        attrl = attrs(tup_tree)
        pname = attrl['NAME']
        reference_class = attrl.get('REFERENCECLASS', None)

        value = self.list_of_matching(tup_tree, ('VALUE.REFERENCE',))
        if not value:
            value = None
        elif len(value) == 1:
            value = value[0]
        else:
            raise CIMXMLParseError(
                _format("Element {0!A} has more than one child element "
                        "'VALUE.REFERENCE' (allowed are zero or one)",
                        name(tup_tree)),
                conn_id=self.conn_id)

        class_origin = attrl.get('CLASSORIGIN', None)
        propagated = self.unpack_boolean(attrl.get('PROPAGATED', 'false'))

        qualifiers = self.list_of_matching(tup_tree, ('QUALIFIER',))

        # It is not possible to create CIM-XML that triggers the ValueError
        # or TypeError exceptions that can potentially be raised from
        # CIMProperty() when used with type='reference'.
        return CIMProperty(
            pname, value, type='reference', reference_class=reference_class,
            is_array=False,
            class_origin=class_origin, propagated=propagated,
            embedded_object=False, qualifiers=qualifiers)

    def parse_method(self, tup_tree):
        """
          ::

            <!ELEMENT METHOD (QUALIFIER*, (PARAMETER | PARAMETER.REFERENCE |
                                           PARAMETER.ARRAY |
                                           PARAMETER.REFARRAY)*)>
            <!ATTLIST METHOD
                %CIMName;
                %CIMType;              #IMPLIED
                %ClassOrigin;
                %Propagated;>
        """

        self.check_node(tup_tree, 'METHOD', ('NAME',),
                        ('TYPE', 'CLASSORIGIN', 'PROPAGATED'),
                        ('QUALIFIER', 'PARAMETER', 'PARAMETER.REFERENCE',
                         'PARAMETER.ARRAY', 'PARAMETER.REFARRAY'))

        attrl = attrs(tup_tree)
        mname = attrl['NAME']

        parameters = self.list_of_matching(tup_tree,
                                           ('PARAMETER', 'PARAMETER.REFERENCE',
                                            'PARAMETER.ARRAY',
                                            'PARAMETER.REFARRAY'))

        class_origin = attrl.get('CLASSORIGIN', None)
        propagated = self.unpack_boolean(attrl.get('PROPAGATED', 'false'))

        qualifiers = self.list_of_matching(tup_tree, ('QUALIFIER',))

        return_type = attrl.get('TYPE', None)
        if not return_type:
            raise CIMXMLParseError(
                _format("Element {0!A} does not define a return type (a void "
                        "method return type is not supported in CIM)",
                        name(tup_tree)),
                conn_id=self.conn_id)

        try:
            return CIMMethod(
                mname, return_type=return_type, parameters=parameters,
                class_origin=class_origin, propagated=propagated,
                qualifiers=qualifiers)
        except (TypeError, ValueError) as exc:
            new_exc = CIMXMLParseError(
                _format("Element {0!A} has invalid input for creating a "
                        "CIMMethod object for method {1!A}: {2}; "
                        "CIM-XML tuple tree: {3}",
                        name(tup_tree), mname, exc, tup_tree),
                conn_id=self.conn_id)
            new_exc.__cause__ = None
            raise new_exc

    def parse_parameter(self, tup_tree):
        """
          ::

            <!ELEMENT PARAMETER (QUALIFIER*)>
            <!ATTLIST PARAMETER
                %CIMName;
                %CIMType;              #REQUIRED>
        """

        self.check_node(tup_tree, 'PARAMETER', ('NAME', 'TYPE'), (),
                        ('QUALIFIER',))

        attrl = attrs(tup_tree)
        pname = attrl['NAME']
        ptype = attrl['TYPE']

        qualifiers = self.list_of_matching(tup_tree, ('QUALIFIER',))

        try:
            return CIMParameter(
                pname, type=ptype, is_array=False, embedded_object=False,
                qualifiers=qualifiers)
        except (TypeError, ValueError) as exc:
            new_exc = CIMXMLParseError(
                _format("Element {0!A} has invalid input for creating a "
                        "CIMParameter object for parameter {1!A}: {2}; "
                        "CIM-XML tuple tree: {3}",
                        name(tup_tree), pname, exc, tup_tree),
                conn_id=self.conn_id)
            new_exc.__cause__ = None
            raise new_exc

    def parse_parameter_reference(self, tup_tree):
        """
          ::

            <!ELEMENT PARAMETER.REFERENCE (QUALIFIER*)>
            <!ATTLIST PARAMETER.REFERENCE
                %CIMName;
                %ReferenceClass;>
        """

        self.check_node(tup_tree, 'PARAMETER.REFERENCE', ('NAME',),
                        ('REFERENCECLASS',), ('QUALIFIER',))

        attrl = attrs(tup_tree)
        pname = attrl['NAME']
        reference_class = attrl.get('REFERENCECLASS', None)

        qualifiers = self.list_of_matching(tup_tree, ('QUALIFIER',))

        # It is not possible to create CIM-XML that triggers the ValueError
        # or TypeError exceptions that can potentially be raised from
        # CIMParameter() when used with type='reference'.
        return CIMParameter(
            pname, type='reference', reference_class=reference_class,
            is_array=False, embedded_object=False, qualifiers=qualifiers)

    def parse_parameter_array(self, tup_tree):
        """
          ::

            <!ELEMENT PARAMETER.ARRAY (QUALIFIER*)>
            <!ATTLIST PARAMETER.ARRAY
                %CIMName;
                %CIMType;              #REQUIRED
                %ArraySize;>
        """

        self.check_node(tup_tree, 'PARAMETER.ARRAY', ('NAME', 'TYPE'),
                        ('ARRAYSIZE',), ('QUALIFIER',))

        attrl = attrs(tup_tree)
        pname = attrl['NAME']
        ptype = attrl['TYPE']

        array_size = attrl.get('ARRAYSIZE', None)
        if array_size is not None:
            # Issue #1044: Clarify if hex support is needed
            array_size = int(array_size)

        qualifiers = self.list_of_matching(tup_tree, ('QUALIFIER',))

        try:
            return CIMParameter(
                pname, type=ptype, is_array=True, array_size=array_size,
                embedded_object=False, qualifiers=qualifiers)
        except (TypeError, ValueError) as exc:
            new_exc = CIMXMLParseError(
                _format("Element {0!A} has invalid input for creating a "
                        "CIMParameter object for parameter {1!A}: {2}; "
                        "CIM-XML tuple tree: {3}",
                        name(tup_tree), pname, exc, tup_tree),
                conn_id=self.conn_id)
            new_exc.__cause__ = None
            raise new_exc

    def parse_parameter_refarray(self, tup_tree):
        """
          ::

            <!ELEMENT PARAMETER.REFARRAY (QUALIFIER*)>
            <!ATTLIST PARAMETER.REFARRAY
                %CIMName;
                %ReferenceClass;
                %ArraySize;>
        """

        self.check_node(tup_tree, 'PARAMETER.REFARRAY', ('NAME',),
                        ('REFERENCECLASS', 'ARRAYSIZE'), ('QUALIFIER',))

        attrl = attrs(tup_tree)
        pname = attrl['NAME']
        reference_class = attrl.get('REFERENCECLASS', None)

        array_size = attrl.get('ARRAYSIZE', None)
        if array_size is not None:
            # Issue #1044: Clarify if hex support is needed
            array_size = int(array_size)

        qualifiers = self.list_of_matching(tup_tree, ('QUALIFIER',))

        # It is not possible to create CIM-XML that triggers the ValueError
        # or TypeError exceptions that can potentially be raised from
        # CIMParameter() when used with type='reference'.
        return CIMParameter(
            pname, type='reference', reference_class=reference_class,
            is_array=True, array_size=array_size,
            embedded_object=False, qualifiers=qualifiers)

    #
    # Message elements
    #

    def parse_message(self, tup_tree):
        """
          ::

            <!ELEMENT MESSAGE (SIMPLEREQ | MULTIREQ | SIMPLERSP | MULTIRSP |
                               SIMPLEEXPREQ | MULTIEXPREQ | SIMPLEEXPRSP |
                               MULTIEXPRSP)
            <!ATTLIST MESSAGE
                ID CDATA #REQUIRED
                PROTOCOLVERSION CDATA #REQUIRED>
        """

        self.check_node(tup_tree, 'MESSAGE', ('ID', 'PROTOCOLVERSION'))

        if not attrs(tup_tree)['PROTOCOLVERSION'].startswith('1.'):
            raise ProtocolVersionError(
                _format("PROTOCOLVERSION is {0}, expected 1.x.y",
                        attrs(tup_tree)['PROTOCOLVERSION']),
                conn_id=self.conn_id)

        child = self.one_child(tup_tree,
                               ('SIMPLEREQ', 'MULTIREQ', 'SIMPLERSP',
                                'MULTIRSP', 'SIMPLEEXPREQ', 'MULTIEXPREQ',
                                'SIMPLEEXPRSP', 'MULTIEXPRSP'))

        return name(tup_tree), attrs(tup_tree), child

    def parse_multireq(self, tup_tree):  # not implemented
        """
        Parsing support for the MULTIREQ element is not implemented
        in pywbem, because that element is only sent from WBEM clients to
        WBEM servers and thus only needs to be parsed in WBEM servers.

        This is no limitation of pywbem, because pywbem only supports WBEM
        client and listener functionality.
        """
        self.notimplemented(tup_tree)

    def parse_multiexpreq(self, tup_tree):  # not implemented
        """
        Parsing support for the MULTIEXPREQ element is not implemented
        in pywbem, because multi export requests are generally not implemented
        by WBEM servers.

        This is a limitation in the listener support of pywbem because if a
        WBEM server implements support for and uses a multi export request,
        the pywbem listener will fail.
        """
        self.notimplemented(tup_tree)

    def parse_simpleexpreq(self, tup_tree):
        """

          ::

            <!ELEMENT SIMPLEEXPREQ (EXPMETHODCALL)>
        """

        self.check_node(tup_tree, 'SIMPLEEXPREQ', (), (),
                        ('EXPMETHODCALL',))

        child = self.one_child(tup_tree, ('EXPMETHODCALL',))

        return name(tup_tree), attrs(tup_tree), child

    def parse_expmethodcall(self, tup_tree):
        """
          ::

            <!ELEMENT EXPMETHODCALL (EXPPARAMVALUE*)>
            <!ATTLIST EXPMETHODCALL
                %CIMName;>
        """

        self.check_node(tup_tree, 'EXPMETHODCALL', ('NAME',), (),
                        ('EXPPARAMVALUE',))

        params = self.list_of_matching(tup_tree, ('EXPPARAMVALUE',))

        return (name(tup_tree), attrs(tup_tree), params)

    def parse_paramvalue(self, tup_tree):
        """
        Parse PARAMVALUE element.

          ::

            <!ELEMENT PARAMVALUE (VALUE | VALUE.REFERENCE | VALUE.ARRAY |
                                  VALUE.REFARRAY | CLASSNAME | INSTANCENAME |
                                  CLASS | INSTANCE | VALUE.NAMEDINSTANCE)?>
            <!ATTLIST PARAMVALUE
                %CIMName;
                %ParamType;  #IMPLIED
                %EmbeddedObject;>
        """

        # Version 2.4 of DSP0201 added CLASSNAME, INSTANCENAME, CLASS,
        # INSTANCE, and VALUE.NAMEDINSTANCE.

        # Version 2.1.1 of DSP0201 lacks the %ParamType entity but it is
        # present as optional (for backwards compatibility) in version 2.2.

        # VMAX returns TYPE instead of PARAMTYPE, toleration support added to
        # use TYPE when present if PARAMTYPE is not present.

        self.check_node(tup_tree, 'PARAMVALUE', ('NAME',),
                        ('TYPE', 'PARAMTYPE', 'EmbeddedObject',
                         'EMBEDDEDOBJECT'))

        child = self.optional_child(tup_tree,
                                    ('VALUE', 'VALUE.REFERENCE', 'VALUE.ARRAY',
                                     'VALUE.REFARRAY', 'CLASSNAME',
                                     'INSTANCENAME', 'CLASS', 'INSTANCE',
                                     'VALUE.NAMEDINSTANCE'))
        attrl = attrs(tup_tree)

        if 'PARAMTYPE' in attrl:
            paramtype = attrl['PARAMTYPE']
        elif 'TYPE' in attrl:
            paramtype = attrl['TYPE']
        else:
            paramtype = None

        if 'EmbeddedObject' in attrl or 'EMBEDDEDOBJECT' in attrl:
            child = self.parse_embeddedObject(child)

        return attrl['NAME'], paramtype, child

    def parse_expparamvalue(self, tup_tree):
        """
        Parse for EXPPARMVALUE Element. I.e.

          ::

            <!ELEMENT EXPPARAMVALUE (INSTANCE?)>
            <!ATTLIST EXPPARAMVALUE
                %CIMName;>
        """

        self.check_node(tup_tree, 'EXPPARAMVALUE', ('NAME',), (), ('INSTANCE',))

        child = self.optional_child(tup_tree, ('INSTANCE',))

        _name = attrs(tup_tree)['NAME']
        return _name, child

    def parse_multirsp(self, tup_tree):  # not implemented
        """
        Parsing support for the MULTIRSP element is not implemented
        in pywbem, because multi requests are generally not implemented by
        WBEM servers.

        This is no limitation of pywbem, because the pywbem client does not
        send multi requests, so a WBEM server will never respond with a multi
        response, even if it implements support for it.
        """
        self.notimplemented(tup_tree)

    def parse_multiexprsp(self, tup_tree):  # not implemented
        """
        Parsing support for the MULTIEXPRSP element is not implemented
        in pywbem, because that element is only sent from WBEM listeners to
        WBEM servers and thus only needs to be parsed in WBEM servers.

        This is no limitation of pywbem, because pywbem only supports WBEM
        client and listener functionality.
        """
        self.notimplemented(tup_tree)

    def parse_simplersp(self, tup_tree):
        """
        Parse for SIMPLERSP Element.

          ::

            <!ELEMENT SIMPLERSP (METHODRESPONSE | IMETHODRESPONSE)>
        """

        self.check_node(tup_tree, 'SIMPLERSP')

        child = self.one_child(tup_tree, ('METHODRESPONSE', 'IMETHODRESPONSE'))

        return name(tup_tree), attrs(tup_tree), child

    def parse_simpleexprsp(self, tup_tree):
        """
        Parse for SIMPLEEXPRSP Element.

        This response element occurs when pywbem communicates with WBEM
        listeners.

          ::

            <!ELEMENT SIMPLEEXPRSP (EXPMETHODRESPONSE)>
        """

        self.check_node(tup_tree, 'SIMPLEEXPRSP')

        child = self.one_child(tup_tree, ('EXPMETHODRESPONSE',))

        return name(tup_tree), attrs(tup_tree), child

    def parse_methodresponse(self, tup_tree):
        """
        Parse expected METHODRESPONSE element:

          ::

            <!ELEMENT METHODRESPONSE (ERROR | (RETURNVALUE?, PARAMVALUE*))>
            <!ATTLIST METHODRESPONSE
                %CIMName;>
        """

        # The valid combination of child elements is checked by the caller
        # (i.e. WBEMConnection._methodcall()), so at this level we only check
        # the complete set of allowed child elements (any number,
        # any combination, any order).

        self.check_node(tup_tree, 'METHODRESPONSE', ('NAME',))

        return (name(tup_tree),
                attrs(tup_tree),
                self.list_of_various(tup_tree,
                                     ('ERROR', 'RETURNVALUE', 'PARAMVALUE')))

    def parse_expmethodresponse(self, tup_tree):
        """
        Parse the tuple for an EXPMETHODRESPONE element.

        This response element occurs when pywbem communicates with WBEM
        listeners.

          ::

            <!ELEMENT EXPMETHODRESPONSE (ERROR | IRETURNVALUE?)>
            <!ATTLIST EXPMETHODRESPONSE
                %CIMName;>
        """

        self.check_node(tup_tree, 'EXPMETHODRESPONSE', ('NAME',))

        return (name(tup_tree), attrs(tup_tree),
                self.list_of_various(tup_tree,
                                     ('ERROR', 'IRETURNVALUE')))

    def parse_imethodresponse(self, tup_tree):
        """
        Parse the tuple for an IMETHODRESPONE element. I.e.

          ::

            <!ELEMENT IMETHODRESPONSE (ERROR | (IRETURNVALUE?, PARAMVALUE*))>
            <!ATTLIST IMETHODRESPONSE
                %CIMName;>
        """

        self.check_node(tup_tree, 'IMETHODRESPONSE', ('NAME',))

        return (name(tup_tree), attrs(tup_tree),
                self.list_of_various(tup_tree,
                                     ('ERROR', 'IRETURNVALUE', 'PARAMVALUE')))

    def parse_correlator(self, tup_tree):  # not implemented
        """
        Parsing support for the CORRELATOR element is not implemented
        in pywbem, because it is generally not implemented by WBEM servers.

        This is a limitation of pywbem.
        """
        self.notimplemented(tup_tree)

    def parse_error(self, tup_tree):
        """
        Parse the tuple for an ERROR element:

          ::

            <!ELEMENT ERROR (INSTANCE*)>
            <!ATTLIST ERROR
                CODE CDATA #REQUIRED
                DESCRIPTION CDATA #IMPLIED>
        """

        self.check_node(tup_tree, 'ERROR', ('CODE',), ('DESCRIPTION',),
                        ('INSTANCE',))

        # self.list_of_various() has the same effect as self.list_of_same()
        # when used with a single allowed child element, but is a little
        # faster.
        instance_list = self.list_of_various(tup_tree, ('INSTANCE',))

        return (name(tup_tree), attrs(tup_tree), instance_list)

    def parse_returnvalue(self, tup_tree):
        """
        Parse the RETURNVALUE element. Returns name, attributes, and
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

        self.check_node(tup_tree, 'RETURNVALUE', (),
                        ('PARAMTYPE', 'EmbeddedObject', 'EMBEDDEDOBJECT'))

        child = self.optional_child(tup_tree, ('VALUE', 'VALUE.REFERENCE'))
        attrl = attrs(tup_tree)

        if 'EmbeddedObject' in attrl or 'EMBEDDEDOBJECT' in attrl:
            child = self.parse_embeddedObject(child)

        return name(tup_tree), attrl, child

    def parse_ireturnvalue(self, tup_tree):
        """
        Parse IRETURNVALUE element. Returns name, attributes and values of the
        tup_tree.

          ::

            <!ELEMENT IRETURNVALUE (CLASSNAME* | INSTANCENAME* | VALUE* |
                                    VALUE.OBJECTWITHPATH* |
                                    VALUE.OBJECTWITHLOCALPATH* |
                                    VALUE.OBJECT* | OBJECTPATH* |
                                    QUALIFIER.DECLARATION* | VALUE.ARRAY? |
                                    VALUE.REFERENCE? | CLASS* | INSTANCE* |
                                    INSTANCEPATH* | VALUE.NAMEDINSTANCE* |
                                    VALUE.INSTANCEWITHPATH*)>
        """

        # Note: The self.check_node() below does not enforce any child elements
        # from the DTD, and the processing further down does not enforce that
        # VALUE.ARRAY and VALUE.REFERENCE may appear at most once.
        # Checking that at this level is not reasonable because the better
        # checks can be done in context of the intrinsic operation receiving
        # its return value. The DTD is so broad simply because it needs to
        # cover the possible return values of all intrinsic operations.
        self.check_node(tup_tree, 'IRETURNVALUE')

        values = self.list_of_same(tup_tree,
                                   ('CLASSNAME', 'INSTANCENAME', 'VALUE',
                                    'VALUE.OBJECTWITHPATH',
                                    'VALUE.OBJECTWITHLOCALPATH',
                                    'VALUE.OBJECT', 'OBJECTPATH',
                                    'QUALIFIER.DECLARATION', 'VALUE.ARRAY',
                                    'VALUE.REFERENCE', 'CLASS', 'INSTANCE',
                                    'INSTANCEPATH', 'VALUE.NAMEDINSTANCE',
                                    'VALUE.INSTANCEWITHPATH'))

        # Note: The caller needs to unpack the value.
        return name(tup_tree), attrs(tup_tree), values

    #
    #  The following parse functions are particular to a server and are not
    #  used by the pywbem client or listener.
    #

    def parse_simplereq(self, tup_tree):
        """
        Parsing support for the SIMPLEREQ element is only needed
        in a WBEM server. Pywbem only needs to support parsing for WBEM client
        and WBEM listener functionality, but this function has not been removed
        at this point.

         ::

            <!ELEMENT SIMPLEREQ (IMETHODCALL | METHODCALL)>
        """

        self.check_node(tup_tree, 'SIMPLEREQ')

        child = self.one_child(tup_tree, ('IMETHODCALL', 'METHODCALL'))

        return name(tup_tree), attrs(tup_tree), child

    def parse_imethodcall(self, tup_tree):
        """
        Parsing support for the IMETHODCALL element is only needed
        in a WBEM server. Pywbem only needs to support parsing for WBEM client
        and WBEM listener functionality, but this function has not been removed
        at this point.

          ::

            <!ELEMENT IMETHODCALL (LOCALNAMESPACEPATH, IPARAMVALUE*)>
            <!ATTLIST IMETHODCALL
               %CIMName;>
        """

        self.check_node(tup_tree, 'IMETHODCALL', ('NAME',))

        k = kids(tup_tree)

        if not k:
            raise CIMXMLParseError(
                _format("Element {0!A} is missing required child elements "
                        "(expecting child elements "
                        "(LOCALNAMESPACEPATH, IPARAMVALUE*))", name(tup_tree)),
                conn_id=self.conn_id)

        namespace = self.parse_localnamespacepath(k[0])

        params = [self.parse_iparamvalue(x) for x in k[1:]]

        return (name(tup_tree), attrs(tup_tree), namespace, params)

    def parse_methodcall(self, tup_tree):
        """
        Parsing support for the METHODCALL element is only needed
        in a WBEM server. Pywbem only needs to support parsing for WBEM client
        and WBEM listener functionality, but this function has not been removed
        at this point.

          ::

            <!ELEMENT METHODCALL ((LOCALCLASSPATH | LOCALINSTANCEPATH),
                                  PARAMVALUE*)>
            <!ATTLIST METHODCALL
                %CIMName;>
        """

        self.check_node(tup_tree, 'METHODCALL', ('NAME',), (),
                        ('LOCALCLASSPATH', 'LOCALINSTANCEPATH', 'PARAMVALUE'))

        path = self.list_of_matching(tup_tree,
                                     ('LOCALCLASSPATH', 'LOCALINSTANCEPATH'))
        if not path:
            raise CIMXMLParseError(
                _format("Element {0!A} is missing required child elements "
                        "'LOCALCLASSPATH' or 'LOCALINSTANCEPATH'",
                        name(tup_tree)),
                conn_id=self.conn_id)
        if len(path) > 1:
            raise CIMXMLParseError(
                _format("Element {0!A} has too many child elements {1!A} "
                        "(allowed is one of 'LOCALCLASSPATH' or "
                        "'LOCALINSTANCEPATH')", name(tup_tree), path),
                conn_id=self.conn_id)
        path = path[0]
        params = self.list_of_matching(tup_tree, ('PARAMVALUE',))
        return (name(tup_tree), attrs(tup_tree), path, params)

    def parse_iparamvalue(self, tup_tree):
        """
        Parsing support for the IPARAMVALUE element is only needed
        in a WBEM server. Pywbem only needs to support parsing for WBEM client
        and WBEM listener functionality, but this function has not been removed
        at this point.

          ::

            <!ELEMENT IPARAMVALUE (VALUE | VALUE.ARRAY | VALUE.REFERENCE |
                                  INSTANCENAME | CLASSNAME |
                                  QUALIFIER.DECLARATION |
                                  CLASS | INSTANCE | VALUE.NAMEDINSTANCE)?>
            <!ATTLIST IPARAMVALUE
                %CIMName;>

        :return: NAME, VALUE pair.
        """

        self.check_node(tup_tree, 'IPARAMVALUE', ('NAME',))

        child = self.optional_child(tup_tree,
                                    ('VALUE', 'VALUE.ARRAY', 'VALUE.REFERENCE',
                                     'INSTANCENAME', 'CLASSNAME',
                                     'QUALIFIER.DECLARATION', 'CLASS',
                                     'INSTANCE', 'VALUE.NAMEDINSTANCE'))

        _name = attrs(tup_tree)['NAME']
        if isinstance(child, six.string_types) and \
                _name.lower() in ('deepinheritance', 'localonly',
                                  'includequalifiers', 'includeclassorigin'):
            if child.lower() in ('true', 'false'):
                child = (child.lower() == 'true')

        return _name, child

    #   End of server specific parse functions

    #
    # Object naming and locating elements
    #

    def parse_any(self, tup_tree):
        """
        Parse a fragment of XML. This function drives the rest of the parser by
        calling ``parse_*()`` functions based on the name of the element being
        parsed.

        It builds parser function name from incoming name in tup_tree prepended
        with ``parse_`` and calls that function.

        Return is determined by function called.
        """

        nodename = name(tup_tree).lower().replace('.', '_')
        funcname = 'parse_' + nodename
        try:
            func = getattr(self, funcname)
        except AttributeError:
            new_exc = CIMXMLParseError(
                _format("Invalid element for CIM-XML: {0!A}", name(tup_tree)),
                conn_id=self.conn_id)
            new_exc.__cause__ = None
            raise new_exc
        return func(tup_tree)  # a bound method, i.e. self is implicit

    def parse_embeddedObject(self, val):
        # pylint: disable=invalid-name
        """
        Parse and embedded instance or class and return the CIMInstance or
        CIMClass.

        Parameters:

          val (string):
            The string value that contains the embedded object in CIM-XML
            format. One level of XML entity references have already been
            unescaped.

            Example string value, for a doubly nested embedded instance. Note
            that in the CIM-XML payload, this string value is escaped one more
            level.

            ::

                <INSTANCE CLASSNAME="PyWBEM_Address">
                  <PROPERTY NAME="Street" TYPE="string">
                    <VALUE>Fritz &amp; &lt;the cat&gt; Ave</VALUE>
                  </PROPERTY>
                  <PROPERTY NAME="Town" TYPE="string"
                            EmbeddedObject="instance">
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

          CIMXMLParseError: There is an error in the XML.
        """

        if type(val) == list:  # pylint: disable=unidiomatic-typecheck
            return [self.parse_embeddedObject(obj) for obj in val]
        if val is None:
            return None

        # Perform the un-embedding (may raise XMLParseError)
        tup_tree = xml_to_tupletree_sax(val, "embedded object", self.conn_id)

        if name(tup_tree) == 'INSTANCE':
            return self.parse_instance(tup_tree)

        if name(tup_tree) == 'CLASS':
            return self.parse_class(tup_tree)

        raise CIMXMLParseError(
            _format("Invalid top-level element {0!A} in embedded object "
                    "value", name(tup_tree)),
            conn_id=self.conn_id)

    def unpack_value(self, tup_tree):
        """
        Find VALUE or VALUE.ARRAY under tup_tree and convert to a Python value.

        Looks at the TYPE of the node to work out how to decode it.
        Handles nodes with no value (e.g. when representing NULL by omitting
        VALUE)
        """

        valtype = attrs(tup_tree)['TYPE']

        raw_val = self.list_of_matching(tup_tree, ('VALUE', 'VALUE.ARRAY'))

        if not raw_val:
            return None

        if len(raw_val) > 1:
            raise CIMXMLParseError(
                _format("Element {0!A} has too many child elements: {1!A} "
                        "(allowed is one of 'VALUE' or 'VALUE.ARRAY')",
                        name(tup_tree), [name(t) for t in kids(tup_tree)]),
                conn_id=self.conn_id)

        raw_val = raw_val[0]

        if type(raw_val) == list:  # pylint: disable=unidiomatic-typecheck
            return [self.unpack_single_value(data, valtype)
                    for data in raw_val]

        return self.unpack_single_value(raw_val, valtype)

    def unpack_single_value(self, data, cimtype):
        """
        Unpack a single (non-array) CIM typed string value of any CIM type
        except 'reference' and return it as a CIM data type object, or Python
        int/long/float, or None.

        data (unicode string): CIM-XML string value, or None (in which case
          None is returned).

        cimtype (string): CIM data type name (e.g. 'datetime') except
          'reference', or None (in which case a numeric value is assumed).
        """
        if cimtype == 'string':
            return data

        if cimtype == 'boolean':
            return self.unpack_boolean(data)

        if cimtype is None or NUMERIC_CIMTYPE_PATTERN.match(cimtype):
            return self.unpack_numeric(data, cimtype)

        if cimtype == 'datetime':
            return self.unpack_datetime(data)

        if cimtype == 'char16':
            return self.unpack_char16(data)

        # Note that 'reference' is not allowed for this function.
        raise CIMXMLParseError(
            _format("Invalid CIM type found: {0!A}", cimtype),
            conn_id=self.conn_id)

    def unpack_boolean(self, data):
        """
        Unpack a string value of CIM type 'boolean' and return True, False
        or None (for empty string value).

        data (unicode string): CIM-XML string value. Must not be None.
        """

        assert data is not None

        # CIM-XML says "These values MUST be treated as case-insensitive"
        # (even though the XML definition requires them to be lowercase.)

        data_ = data.strip().lower()                   # ignore space

        if data_ == 'true':
            return True

        if data_ == 'false':
            return False

        if data_ == '':
            warnings.warn("WBEM server sent invalid empty boolean value in a "
                          "CIM-XML response.",
                          ToleratedServerIssueWarning,
                          stacklevel=_stacklevel_above_module(__name__))
            return None

        raise CIMXMLParseError(
            _format("Invalid boolean value {0!A}", data),
            conn_id=self.conn_id)

    def unpack_numeric(self, data, cimtype):
        """
        Unpack a string value of a numeric CIM type and return its CIM data
        type object.

        data (unicode string): CIM-XML string value. Must not be None.

        cimtype (string): CIM data type name (e.g. 'uint8'), or None (in which
          case the value is returned as a Python int/long or float).
        """

        assert data is not None

        # DSP0201 defines numeric values to be whitespace-tolerant
        data = data.strip()

        # Decode the CIM-XML string representation into a Python number
        #
        # Some notes:
        # * For integer numbers, only decimal and hexadecimal strings are
        #   allowed - no binary or octal.
        # * In Python 2, int() automatically returns a long, if needed.
        # * For real values, DSP0201 defines a subset of the syntax supported
        #   by Python float(), including the special states Inf, -Inf, NaN. The
        #   only known difference is that DSP0201 requires a digit after the
        #   decimal dot, while Python does not.
        if CIMXML_HEX_PATTERN.match(data):
            value = int(data, 16)
        else:
            try:
                value = int(data)
            except ValueError:
                try:
                    value = float(data)
                except ValueError:
                    new_exc = CIMXMLParseError(
                        _format("Invalid numeric value {0!A}", data),
                        conn_id=self.conn_id)
                    new_exc.__cause__ = None
                    raise new_exc

        # Convert the Python number into a CIM data type
        if cimtype is None:
            return value  # int/long or float (used for keybindings)

        # The caller ensured a numeric type for cimtype
        CIMType = type_from_name(cimtype)
        try:
            value = CIMType(value)
        except ValueError as exc:
            new_exc = CIMXMLParseError(
                _format("Cannot convert value {0!A} to numeric CIM type {1}: "
                        "{2}",
                        value, cimtype, exc),
                conn_id=self.conn_id)
            new_exc.__cause__ = None
            raise new_exc
        return value

    def unpack_datetime(self, data):
        """
        Unpack a CIM-XML string value of CIM type 'datetime' and return it
        as a CIMDateTime object.

        data (unicode string): CIM-XML string value. Must not be None.
        """

        assert data is not None

        try:
            value = CIMDateTime(data)
        except ValueError as exc:
            new_exc = CIMXMLParseError(
                _format("Invalid datetime value {0!A}: {1}", data, exc),
                conn_id=self.conn_id)
            new_exc.__cause__ = None
            raise new_exc
        return value

    def unpack_char16(self, data):
        """
        Unpack a CIM-XML string value of CIM type 'char16' and return it
        as a unicode string object.

        data (unicode string): CIM-XML string value. Must not be None.
        """

        assert data is not None

        len_data = len(data)

        if len_data == 0:
            raise CIMXMLParseError(
                "Char16 value is empty",
                conn_id=self.conn_id)

        if len_data > 1:
            # More than one character, or one character from the UCS-4 set
            # in a narrow Python build (which represents it using
            # surrogates).
            raise CIMXMLParseError(
                _format("Char16 value has more than one UCS-2 "
                        "character: {0!A}", data),
                conn_id=self.conn_id)

        if ord(data) > 0xFFFF:
            # One character from the UCS-4 set in a wide Python build.
            raise CIMXMLParseError(
                _format("Char16 value is a character outside of the "
                        "UCS-2 range: {0!A}", data),
                conn_id=self.conn_id)

        return data
