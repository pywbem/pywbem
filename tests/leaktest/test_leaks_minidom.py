"""
Test memory leaks for xml.dom.minidom classes used by pywbem.

Notes on "standalone" vs "anchored" Element objects in Python minidom:
- The definition of "standalone" Element objects is that they are
  instantiated from their implementation class directly, without using
  factory methods such as Document.createElement(). Using standalone Element
  objects is discouraged in the Python minidom docs. In fact, on Python 3,
  the use of setAttribute() on a standalone Element object fails with
  AttributeError "ownerDocument".
- The definition of "anchored" Element objects is that they are part of a
  Document object, and have been created by factory methods such as
  Document.createElement().
- Using anchored Element objects is the recommended approach as per the
  Python minidom docs, but pywbem currently uses standalone Element objects
  in its cim_xml.py module.
"""

from __future__ import absolute_import, print_function

from xml.dom.minidom import Document, Element
import pytest
import yagot


@yagot.garbage_checked()
def test_leaks_standalone_Element_empty():
    """
    Test function with an empty standalone Element object (i.e. no attributes,
    no child elements, no content).
    """
    _ = Element('FOO')


@pytest.mark.xfail(
    reason="On Py2, Element.setAttribute() creates reference cycles;"
           "On Py3, Element.setAttribute() raises AttributeError")
@yagot.garbage_checked()
def test_leaks_standalone_Element_one_attribute():
    """
    Test function with a standalone Element object that has one attribute set.
    """
    elem = Element('FOO')
    elem.setAttribute('BAR', 'bla')


@yagot.garbage_checked()
def test_leaks_Document_empty():
    """
    Test function with empty Document object.
    """
    _ = Document()


@pytest.mark.xfail(
    reason="Element in a Document creates reference cycles")
@yagot.garbage_checked()
def test_leaks_Element_empty():
    """
    Test function with an empty anchored Element object (i.e. no attributes,
    no child elements, no content).
    """
    doc = Document()
    elem = doc.createElement('FOO')
    doc.appendChild(elem)


@pytest.mark.xfail(
    reason="Element.setAttribute() creates reference cycles")
@yagot.garbage_checked()
def test_leaks_Element_one_attribute():
    """
    Test function with an anchored Element object that has one attribute set.
    """
    doc = Document()
    elem = doc.createElement('FOO')
    elem.setAttribute('BAR', 'bla')
    doc.appendChild(elem)
