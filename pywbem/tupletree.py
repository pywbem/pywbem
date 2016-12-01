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

# NOTE: The original dom based parsers have been replaced with a sax parser
#       in Nov. 2016. The dom tupletree code is in the file
#       testsuite/test_tupletree.py

from __future__ import absolute_import

import xml.dom.minidom
import xml.sax
import re
import sys
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
                re.match(r'\s+', self.element[2][-1])
            except TypeError:
                pass
            else:
                ws = self.element[2].pop()
                content = '%s%s' % (ws, content)
        self.element[2].append(content)


def xml_to_tupletree_sax(xml_string):
    """
    Parse an XML string into tupletree with SAX parser.

    Parses the string using the class CIMContentHandler and
    returns the root element. As a SAX parser it uses minimal
    memory.

    This is a replacement for the previous parser (xml_to_tuple)
    which used the dom parser.

    Parameters:

      xml_string (:term:`string`) or (:term:`byte string`): A string
      or bytes string containing the XML to be parsed.

    Returns:
      (:class: `CIMContentHandler`) : The root tuple from the
      parse:

    Raises:
        TypeError, ParseError, SAXParseException,  or ExpatError.
    """
    handler = CIMContentHandler()

    # The following is required because the SAX parser in these Python
    # versions does not accept unicode strings, raising:
    # SAXParseException: "<unknown>:1:1: not well-formed (invalid token)"
    if sys.version_info[0:2] in ((2, 6), (3, 4)):
        if isinstance(xml_string, six.text_type):
            xml_string = xml_string.encode("utf-8")

    xml.sax.parseString(xml_string, handler, None)
    return handler.root
