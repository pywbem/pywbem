#
# (C) Copyright 2003, 2004 Hewlett-Packard Development Company, L.P.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as
# published by the Free Software Foundation; either version 2 of the
# License.
#   
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#   
# You should have received a copy of the GNU Lesser General Public
# License along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
#

# Author: Martin Pool <mbp@hp.com>

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

def dom_to_tupletree(node):
    """Convert a DOM object to a pyRXP-style tuple tree.

    Each element is a 4-tuple of (NAME, ATTRS, CONTENTS, None).

    Very nice for processing complex nested trees.
    """
    import types
    
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
            assert isinstance(child.nodeValue, types.StringTypes), \
                   "text node %s is not a string" % `child`
            contents.append(child.nodeValue)
        else:
            raise RuntimeError("can't handle %s" % child)

    for i in range(node.attributes.length):
        attr_node = node.attributes.item(i)
        attrs[attr_node.nodeName] = attr_node.nodeValue

    # XXX: Cannot yet handle comments, cdata, processing instructions and
    # other XML batshit.

    # it's so easy in retrospect!
    return (name, attrs, contents, None)


def xml_to_tupletree(xml_string):
    """Parse XML straight into tupletree."""
    import xml.dom.minidom
    dom_xml = xml.dom.minidom.parseString(xml_string)
    return dom_to_tupletree(dom_xml)
