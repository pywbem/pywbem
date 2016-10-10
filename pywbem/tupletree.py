#
# (C) Copyright 2003,2004 Hewlett-Packard Development Company, L.P.
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
# Author: Ross Peoples <ross.peoples@gmail.com>
#

"""
tupletree - Convert XML DOM objects to and from tuple trees.

DOM is the standard in-memory representation of XML documents, but it
is very cumbersome for some types of processing where XML encodes
object structures rather than text documents.  Direct mapping to Python
classes may not be a good match either.

tupletrees may be created from an in-memory DOM using
dom_to_tupletree(), or from a string using xml_to_tupletree().

Since the Python XML libraries deal mostly with Unicode strings they
are also returned here.  If plain Strings are passed in they will be
converted by xmldom.

Each node of the tuple tree is a Python 4-tuple, corresponding to an
XML Element (i.e. <tag>):

  (NAME, ATTRS, CONTENTS, None)

The NAME is the name of the element.

The ATTRS are a name-value hash of element attributes.

The CONTENTS is a list of child elements.

The fourth element is reserved.
"""

from __future__ import absolute_import

import xml.dom.minidom
import xml.sax
import re
import copy

import six

__all__ = []


class CIMContentHandler(xml.sax.ContentHandler):
    """SAX handler for CIM XML.

    Similar to dom_to_tupletree, the handler creates a tree of tuples,
    where the elements are the XML element name, the attributes, and the
    children.

    The handler pushes and pops the list of elements, building the child
    list as it goes.

    The end result is that the root node is left in the list and available
    as the root attribute of the object.
    """

    def __init__(self):
        xml.sax.ContentHandler.__init__(self)
        self.root = None
        self.elements = []
        self.element = []

    def startDocument(self):
        assert self.elements == []

    def endDocument(self):
        assert self.elements == []
        self.root = self.element

    def startElement(self, name, attrs):
        if self.element:
            self.elements.append(self.element)
        # Avoid dict comprehension to support python2.6.
        attr_dict = {}
        for k, v in attrs.items():
            attr_dict[k] = v
        element = (name, attr_dict, list(), None)
        if self.element:
            self.element[2].append(element)
        self.element = element

    def endElement(self, name):
        if self.elements:
            self.element = self.elements.pop()

    def characters(self, content):
        if self.element[2]:
            try:
                re.match('\s+', self.element[2][-1])
            except TypeError:
                pass
            else:
                ws = self.element[2].pop()
                content = '%s%s' % (ws, content)
        self.element[2].append(content)


def dom_to_tupletree(node):
    """Convert a DOM object to a pyRXP-style tuple tree.

    Each element is a 4-tuple of (NAME, ATTRS, CONTENTS, None).

    Very nice for processing complex nested trees.
    """

    if node.nodeType == node.DOCUMENT_NODE:
        # boring; pop down one level
        return dom_to_tupletree(node.firstChild)
    assert node.nodeType == node.ELEMENT_NODE

    name = node.nodeName
    attrs = {}
    contents = []

    for child in node.childNodes:
        if child.nodeType == child.ELEMENT_NODE:
            contents.append(dom_to_tupletree(child))
        elif child.nodeType == child.TEXT_NODE:
            assert isinstance(child.nodeValue, six.string_types), \
                   "text node %s is not a string %r" % child
            contents.append(child.nodeValue)
        elif child.nodeType == child.CDATA_SECTION_NODE:
            contents.append(child.nodeValue)
        else:
            raise RuntimeError("can't handle %r" % child)

    for i in range(node.attributes.length):
        attr_node = node.attributes.item(i)
        attrs[attr_node.nodeName] = attr_node.nodeValue

    # XXX: Cannot handle comments, cdata, processing instructions, etc.

    # it's so easy in retrospect!
    return (name, attrs, contents, None)


def xml_to_tupletree(xml_string):
    """Parse XML straight into tupletree."""
    dom_xml = xml.dom.minidom.parseString(xml_string)
    return dom_to_tupletree(dom_xml)


def xml_to_tupletree_sax(xml_string):
    """Parse an XML string into tupletree with SAX."""
    handler = CIMContentHandler()
    xml.sax.parseString(xml_string, handler, None)
    return handler.root
