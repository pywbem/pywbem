"""
Test memory leaks for xml.etree.ElementTree classes.
"""

from __future__ import absolute_import, print_function

import xml.etree.ElementTree as ET
import yagot


@yagot.garbage_checked()
def test_leaks_ET_Element_empty():
    """
    Test function with an empty Element object (i.e. no attributes,
    no child elements, no content).
    """
    _ = ET.Element('FOO')


@yagot.garbage_checked()
def test_leaks_ET_Element_one_attribute():
    """
    Test function with an Element object that has one attribute set.
    """
    elem = ET.Element('FOO')
    elem.attrib["BAR"] = 'bla'


@yagot.garbage_checked()
def test_leaks_ET_Element_one_child():
    """
    Test function with an Element object that has one child element.
    """
    elem = ET.Element('FOO')
    _ = ET.SubElement(elem, 'GOO')


@yagot.garbage_checked()
def test_leaks_ET_Element_one_child_text_attr():
    """
    Test function with an Element object that has one child element with
    text content and one attribute.
    """
    elem = ET.Element('FOO')
    subelem = ET.SubElement(elem, 'GOO')
    subelem.attrib["BAT"] = 'bla'
    subelem.text = 'some text'
