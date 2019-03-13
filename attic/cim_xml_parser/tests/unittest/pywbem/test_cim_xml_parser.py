"""
Test CIM-XML parsing routines in _cim_xml_parser.py.
"""

from __future__ import absolute_import

import re
import pytest

from pywbem._cim_xml_parser import CIMXMLParser, XmlEvent
from pywbem import CIMInstance, CIMInstanceName, CIMClass, CIMClassName, \
    CIMProperty, CIMMethod, CIMParameter, CIMQualifier, \
    CIMQualifierDeclaration, \
    CIMDateTime, Uint8, Sint8, Uint16, Sint16, Uint32, Sint32, Uint64, Sint64, \
    Real32, Real64, CIMXMLParseError, XMLParseError, CIMError, \
    ToleratedServerIssueWarning

from ..utils.pytest_extensions import simplified_test_function


def qualifier_default_attrs(**overriding_attrs):
    """
    Return a kwargs dict with the CIM-XML default values for the `propagated`
    and flavor attributes of CIMQualifier, updated by the specified overriding
    values for these attributes.
    """
    attrs = dict(
        propagated=False,
        tosubclass=True,
        overridable=True,
        translatable=False,
        toinstance=False,
    )
    attrs.update(overriding_attrs)
    return attrs


def qualifier_declaration_default_attrs(**overriding_attrs):
    """
    Return a kwargs dict with the CIM-XML default values for the flavor
    attributes of CIMQualifierDeclaration, updated by the specified overriding
    values for these attributes.
    """
    attrs = dict(
        tosubclass=True,
        overridable=True,
        translatable=False,
        toinstance=False,
    )
    attrs.update(overriding_attrs)
    return attrs


TESTCASES_XMLEVENT_REPR = [
    (
        XmlEvent(
            event='start',
            name='DUMMY_ELEMENT')
    ),
    (
        XmlEvent(
            event='start',
            name='DUMMY_ELEMENT',
            attributes=dict(
                FOO='bar',
            ))
    ),
    (
        XmlEvent(
            event='start',
            name='DUMMY_ELEMENT',
            content='bar')
    ),
    (
        XmlEvent(
            event='start',
            name='DUMMY_ELEMENT',
            conn_id='42')
    ),
]


@pytest.mark.parametrize(
    "obj",
    TESTCASES_XMLEVENT_REPR)
def test_XmlEvent_repr(obj):
    """
    Test function for XmlEvent.__repr__()
    """

    # The code to be tested
    repr_str = repr(obj)

    assert re.match(r'^XmlEvent\(.*\)$', repr_str)

    event_str = "event={0!r}".format(obj.event)
    assert event_str in repr_str

    name_str = "name={0!r}".format(obj.name)
    assert name_str in repr_str

    if obj.attributes is not None:
        attributes_str = "attributes={0!r}".format(obj.attributes)
        assert attributes_str in repr_str

    if obj.content is not None:
        content_str = "content={0!r}".format(obj.content)
        assert content_str in repr_str

    if obj.conn_id is not None:
        conn_id_str = "conn_id={0!r}".format(obj.conn_id)
        assert conn_id_str in repr_str


TESTCASES_XMLEVENT_EQUAL = [
    (
        "XmlEvent objects with same event type and element name",
        dict(
            obj1=XmlEvent('start', 'DUMMY'),
            obj2=XmlEvent('start', 'DUMMY'),
            exp_obj_equal=True,
        ),
        None, None, True
    ),
    (
        "XmlEvent objects with different event type",
        dict(
            obj1=XmlEvent('start', 'DUMMY'),
            obj2=XmlEvent('end', 'DUMMY'),
            exp_obj_equal=False,
        ),
        None, None, True
    ),
    (
        "XmlEvent objects with different element name",
        dict(
            obj1=XmlEvent('start', 'DUMMY'),
            obj2=XmlEvent('start', 'DUMMY2'),
            exp_obj_equal=False,
        ),
        None, None, True
    ),
    (
        "XmlEvent objects with same attributes",
        dict(
            obj1=XmlEvent('start', 'DUMMY',
                          attributes=dict(Foo='bar')),
            obj2=XmlEvent('start', 'DUMMY',
                          attributes=dict(Foo='bar')),
            exp_obj_equal=True,
        ),
        None, None, True
    ),
    (
        "XmlEvent objects with different attributes",
        dict(
            obj1=XmlEvent('start', 'DUMMY',
                          attributes=dict(Foo='bar')),
            obj2=XmlEvent('start', 'DUMMY',
                          attributes=dict(Foo2='bar2')),
            exp_obj_equal=False,
        ),
        None, None, True
    ),
    (
        "XmlEvent objects with same content",
        dict(
            obj1=XmlEvent('start', 'DUMMY',
                          content='bar'),
            obj2=XmlEvent('start', 'DUMMY',
                          content='bar'),
            exp_obj_equal=True,
        ),
        None, None, True
    ),
    (
        "XmlEvent objects with different content",
        dict(
            obj1=XmlEvent('start', 'DUMMY',
                          content='bar'),
            obj2=XmlEvent('start', 'DUMMY',
                          content='bar2'),
            exp_obj_equal=False,
        ),
        None, None, True
    ),
    (
        "XmlEvent objects with same conn_id",
        dict(
            obj1=XmlEvent('start', 'DUMMY',
                          conn_id='42'),
            obj2=XmlEvent('start', 'DUMMY',
                          conn_id='42'),
            exp_obj_equal=True,
        ),
        None, None, True
    ),
    (
        "XmlEvent objects with different conn_id",
        dict(
            obj1=XmlEvent('start', 'DUMMY',
                          conn_id='42'),
            obj2=XmlEvent('start', 'DUMMY',
                          conn_id='43'),
            exp_obj_equal=False,
        ),
        None, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_XMLEVENT_EQUAL)
@simplified_test_function
def test_XmlEvent_eq(
        testcase, obj1, obj2, exp_obj_equal):
    """
    Test function for XmlEvent.__eq__()
    """

    # Double check they are different objects
    assert id(obj1) != id(obj2)

    # The code to be tested
    eq1 = (obj1 == obj2)
    eq2 = (obj2 == obj1)

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None

    assert eq1 == exp_obj_equal
    assert eq2 == exp_obj_equal


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_XMLEVENT_EQUAL)
@simplified_test_function
def test_XmlEvent_ne(
        testcase, obj1, obj2, exp_obj_equal):
    """
    Test function for XmlEvent.__ne__()
    """

    # Double check they are different objects
    assert id(obj1) != id(obj2)

    # The code to be tested
    ne1 = (obj1 != obj2)
    ne2 = (obj2 != obj1)

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None

    assert ne1 != exp_obj_equal
    assert ne2 != exp_obj_equal


TESTCASES_GET_NEXT_EVENT = [
    (
        "Element without attributes, content or children, in self-closing "
        "syntax",
        dict(
            xml_str='<BLA/>\n',
            exp_xml_events=(
                dict(
                    event='start',
                    element_tag='BLA',
                    element_attrib=dict(),
                    element_text=None,
                ),
                dict(
                    event='end',
                    element_tag='BLA',
                    element_attrib=dict(),
                    element_text=None,
                ),
            ),
        ),
        None, None, True
    ),
    (
        "Element without attributes, content or children, in start/end "
        "syntax",
        dict(
            xml_str='<BLA></BLA>\n',
            exp_xml_events=(
                dict(
                    event='start',
                    element_tag='BLA',
                    element_attrib=dict(),
                    element_text=None,
                ),
                dict(
                    event='end',
                    element_tag='BLA',
                    element_attrib=dict(),
                    element_text=None,
                ),
            ),
        ),
        None, None, True
    ),
    (
        "Element with attributes, in self-closing syntax",
        dict(
            xml_str='<BLA NAME="CreationClassName" TYPE="string"/>\n',
            exp_xml_events=(
                dict(
                    event='start',
                    element_tag='BLA',
                    element_attrib=dict(
                        NAME="CreationClassName",
                        TYPE="string"),
                    element_text=None,
                ),
                dict(
                    event='end',
                    element_tag='BLA',
                    element_attrib=dict(
                        NAME="CreationClassName",
                        TYPE="string"),
                    element_text=None,
                ),
            ),
        ),
        None, None, True
    ),
    (
        "Element with attributes, and one child with content",
        dict(
            xml_str=''
            '<BLA NAME="CreationClassName" TYPE="string">\n'
            '  <BLUB>PyWBEM_Person</BLUB>\n'
            '</BLA>\n',
            exp_xml_events=(
                dict(
                    event='start',
                    element_tag='BLA',
                    element_attrib=dict(
                        NAME="CreationClassName",
                        TYPE="string"),
                    element_text=None,
                ),
                dict(
                    event='start',
                    element_tag='BLUB',
                    element_attrib=dict(),
                    element_text='PyWBEM_Person',
                ),
                dict(
                    event='end',
                    element_tag='BLUB',
                    element_attrib=dict(),
                    element_text='PyWBEM_Person',
                ),
                dict(
                    event='end',
                    element_tag='BLA',
                    element_attrib=dict(
                        NAME="CreationClassName",
                        TYPE="string"),
                    element_text=None,
                ),
            ),
        ),
        None, None, True
    ),
    (
        "Attempt to get an event after end is reached",
        dict(
            xml_str='<BLA></BLA>\n',
            exp_xml_events=(
                dict(
                    event='start',
                    element_tag='BLA',
                    element_attrib=dict(),
                    element_text=None,
                ),
                dict(
                    event='end',
                    element_tag='BLA',
                    element_attrib=dict(),
                    element_text=None,
                ),
                None,  # this causes the exception to be triggered
            ),
        ),
        CIMXMLParseError, None, True
    ),
    (
        "Ill-formed XML (missing closing bracket on end element)",
        dict(
            xml_str='<BLA> </BLA',
            exp_xml_events=(
                dict(
                    event='start',
                    element_tag='BLA',
                    element_attrib=dict(),
                    element_text=None,
                ),
                None,  # this causes the exception to be triggered
            ),
        ),
        XMLParseError, None, True
    ),
    (
        "Ill-formed XML (missing slash on end element)",
        dict(
            xml_str='<BLA> <BLA>\n',
            exp_xml_events=(
                dict(
                    event='start',
                    element_tag='BLA',
                    element_attrib=dict(),
                    element_text=None,
                ),
                dict(
                    event='start',
                    element_tag='BLA',
                    element_attrib=dict(),
                    element_text=None,
                ),
                None,  # this causes the exception to be triggered
            ),
        ),
        XMLParseError, None, True
    ),
    (
        "Ill-formed XML (missing opening bracket on end element)",
        dict(
            xml_str='<BLA> /BLA>\n',
            exp_xml_events=(
                dict(
                    event='start',
                    element_tag='BLA',
                    element_attrib=dict(),
                    element_text=None,
                ),
                None,  # this causes the exception to be triggered
            ),
        ),
        XMLParseError, None, True
    ),
    (
        "Ill-formed XML (missing closing bracket on begin element)",
        dict(
            xml_str='<BLA </BLA>\n',
            exp_xml_events=(
                None,  # this causes the exception to be triggered
            ),
        ),
        XMLParseError, None, True
    ),
    (
        "Ill-formed XML (missing opening bracket on begin element)",
        dict(
            xml_str='BLA> </BLA>\n',
            exp_xml_events=(
                None,  # this causes the exception to be triggered
            ),
        ),
        XMLParseError, None, True
    ),
    (
        "Ill-formed XML (non-matching end element)",
        dict(
            xml_str='<BLA> </BLA2>\n',
            exp_xml_events=(
                dict(
                    event='start',
                    element_tag='BLA',
                    element_attrib=dict(),
                    element_text=None,
                ),
                None,  # this causes the exception to be triggered
            ),
        ),
        XMLParseError, None, True
    ),
    (
        "Ill-formed XML (no end element)",
        dict(
            xml_str='<BLA>\n',
            exp_xml_events=(
                dict(
                    event='start',
                    element_tag='BLA',
                    element_attrib=dict(),
                    element_text=None,
                ),
                None,  # this causes the exception to be triggered
            ),
        ),
        XMLParseError, None, True
    ),
    (
        "Ill-formed XML (no begin element)",
        dict(
            xml_str='</BLA>\n',
            exp_xml_events=(
                None,  # this causes the exception to be triggered
            ),
        ),
        XMLParseError, None, True
    ),
    (
        "Ill-formed XML (missing closing bracket in short form)",
        dict(
            xml_str='<BLA/',
            exp_xml_events=(
                None,  # this causes the exception to be triggered
            ),
        ),
        XMLParseError, None, True
    ),
    (
        "Ill-formed XML (missing opening bracket in short form)",
        dict(
            xml_str='BLA/>\n',
            exp_xml_events=(
                None,  # this causes the exception to be triggered
            ),
        ),
        XMLParseError, None, True
    ),
    (
        "Ill-formed XML (missing =value on attribute)",
        dict(
            xml_str='<BLA FOO/>\n',
            exp_xml_events=(
                None,  # this causes the exception to be triggered
            ),
        ),
        XMLParseError, None, True
    ),
    (
        "Ill-formed XML (missing value on attribute)",
        dict(
            xml_str='<BLA FOO=/>\n',
            exp_xml_events=(
                None,  # this causes the exception to be triggered
            ),
        ),
        XMLParseError, None, True
    ),
    (
        "Ill-formed XML (missing double quotes around value on attribute)",
        dict(
            xml_str='<BLA FOO=2.3/>\n',
            exp_xml_events=(
                None,  # this causes the exception to be triggered
            ),
        ),
        XMLParseError, None, True
    ),
    (
        "Ill-formed XML (extra opening bracket on begin element)",
        dict(
            xml_str='<<BLA>\n',
            exp_xml_events=(
                None,  # this causes the exception to be triggered
            ),
        ),
        XMLParseError, None, True
    ),
    (
        "Ill-formed XML (extra opening bracket on end element)",
        dict(
            xml_str='<BLA> <</BLA>\n',
            exp_xml_events=(
                dict(
                    event='start',
                    element_tag='BLA',
                    element_attrib=dict(),
                    element_text=None,
                ),
                None,  # this causes the exception to be triggered
            ),
        ),
        XMLParseError, None, True
    ),
    (
        "Valid XML (extra closing bracket on begin element is treated as "
        "content)",
        dict(
            xml_str='<BLA>> </BLA>\n',
            exp_xml_events=(
                dict(
                    event='start',
                    element_tag='BLA',
                    element_attrib=dict(),
                    element_text='> ',
                ),
                dict(
                    event='end',
                    element_tag='BLA',
                    element_attrib=dict(),
                    element_text='> ',
                ),
            ),
        ),
        None, None, True
    ),
    (
        "Ill-formed XML (extra closing bracket on end element)",
        dict(
            xml_str='<BLA> </BLA>>\n',
            exp_xml_events=(
                dict(
                    event='start',
                    element_tag='BLA',
                    element_attrib=dict(),
                    element_text=None,
                ),
                dict(
                    event='end',
                    element_tag='BLA',
                    element_attrib=dict(),
                    element_text=None,
                ),
                None,  # this causes the exception to be triggered
            ),
        ),
        XMLParseError, None, True
    ),
    (
        "Verify that single quoted attr values work (see XML spec AttValue)",
        dict(
            xml_str='<BLA NAME=\'abc\'/>\n',
            exp_xml_events=(
                dict(
                    event='start',
                    element_tag='BLA',
                    element_attrib=dict(
                        NAME='abc',
                    ),
                    element_text=None,
                ),
                dict(
                    event='end',
                    element_tag='BLA',
                    element_attrib=dict(
                        NAME='abc',
                    ),
                    element_text=None,
                ),
            ),
        ),
        None, None, True
    ),
    (
        "Use of empty attribute value",
        dict(
            xml_str='<BLA NAME=""/>\n',
            exp_xml_events=(
                dict(
                    event='start',
                    element_tag='BLA',
                    element_attrib=dict(
                        NAME='',
                    ),
                    element_text=None,
                ),
                dict(
                    event='end',
                    element_tag='BLA',
                    element_attrib=dict(
                        NAME='',
                    ),
                    element_text=None,
                ),
            ),
        ),
        None, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_GET_NEXT_EVENT)
@simplified_test_function
def test_get_next_event(
        testcase, xml_str, exp_xml_events):
    """
    Test CIMXMLParser.get_next_event().
    """

    parser = CIMXMLParser(xml_str)

    for exp_xml_event in exp_xml_events:

        # Code to be tested
        parser.get_next_event()

        if exp_xml_event is not None:
            assert parser.event == exp_xml_event['event'], \
                "Unexpected XML event type {}; expected XML event {}".\
                format(parser.event, exp_xml_event)
            assert parser.element.tag == exp_xml_event['element_tag'], \
                "Unexpected XML event element tag {}; expected XML event {}".\
                format(parser.element.tag, exp_xml_event)
            assert parser.element.attrib == exp_xml_event['element_attrib'], \
                "Unexpected XML event element attributes {}; expected XML " \
                "event {}".\
                format(parser.element.tag, exp_xml_event)
            text = parser.element.text
            if text is not None and text.strip(' \n\r\t') == '':
                text = None
            assert text == exp_xml_event['element_text'], \
                "Unexpected XML event element content {!r}; expected XML " \
                "event {}".\
                format(text, exp_xml_event)

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None, \
        "Expected exception {!r} has not been raised".\
        format(testcase.exp_exc_types)

    parser.expect_end()


TESTCASES_PUT_BACK_EVENT = [
    (
        "Put back prior to any get next",
        dict(
            xml_str='<BLA NAME="abc"/>\n',
            actions=(
                'put_back_event',  # causes exception to be raised
            ),
            exp_xml_events=(
                None,
            ),
        ),
        ValueError, None, True
    ),
    (
        "Put back after first get next",
        dict(
            xml_str='<BLA NAME="abc"/>\n',
            actions=(
                'get_next_event',
                'put_back_event',
                'get_next_event',
                'get_next_event',
                'expect_end',
            ),
            exp_xml_events=(
                dict(
                    event='start',
                    element_tag='BLA',
                    element_attrib=dict(
                        NAME='abc',
                    ),
                    element_text=None,
                ),
                None,
                dict(
                    event='start',
                    element_tag='BLA',
                    element_attrib=dict(
                        NAME='abc',
                    ),
                    element_text=None,
                ),
                dict(
                    event='end',
                    element_tag='BLA',
                    element_attrib=dict(
                        NAME='abc',
                    ),
                    element_text=None,
                ),
                None,
            ),
        ),
        None, None, True
    ),
    (
        "Put back after last get next",
        dict(
            xml_str='<BLA NAME="abc"/>\n',
            actions=(
                'get_next_event',
                'get_next_event',
                'put_back_event',
                'get_next_event',
                'expect_end',
            ),
            exp_xml_events=(
                dict(
                    event='start',
                    element_tag='BLA',
                    element_attrib=dict(
                        NAME='abc',
                    ),
                    element_text=None,
                ),
                dict(
                    event='end',
                    element_tag='BLA',
                    element_attrib=dict(
                        NAME='abc',
                    ),
                    element_text=None,
                ),
                None,
                dict(
                    event='end',
                    element_tag='BLA',
                    element_attrib=dict(
                        NAME='abc',
                    ),
                    element_text=None,
                ),
                None,
            ),
        ),
        None, None, True
    ),
    (
        "Expecting end with an event on the put-back stack",
        dict(
            xml_str='<BLA NAME="abc"/>\n',
            actions=(
                'get_next_event',
                'get_next_event',
                'put_back_event',
                'expect_end',  # causes exception to be raised
            ),
            exp_xml_events=(
                dict(
                    event='start',
                    element_tag='BLA',
                    element_attrib=dict(
                        NAME='abc',
                    ),
                    element_text=None,
                ),
                dict(
                    event='end',
                    element_tag='BLA',
                    element_attrib=dict(
                        NAME='abc',
                    ),
                    element_text=None,
                ),
                None,
                None,
            ),
        ),
        CIMXMLParseError, None, True
    ),
    (
        "Put back after put back",
        dict(
            xml_str='<BLA NAME="abc"/>\n',
            actions=(
                'get_next_event',
                'get_next_event',
                'put_back_event',
                'put_back_event',  # causes exception to be raised
            ),
            exp_xml_events=(
                dict(
                    event='start',
                    element_tag='BLA',
                    element_attrib=dict(
                        NAME='abc',
                    ),
                    element_text=None,
                ),
                dict(
                    event='end',
                    element_tag='BLA',
                    element_attrib=dict(
                        NAME='abc',
                    ),
                    element_text=None,
                ),
                None,
                None,
            ),
        ),
        ValueError, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_PUT_BACK_EVENT)
@simplified_test_function
def test_put_back_event(
        testcase, xml_str, actions, exp_xml_events):
    """
    Test CIMXMLParser.put_back_event().
    """

    parser = CIMXMLParser(xml_str)

    exp_xml_events_iter = iter(exp_xml_events)

    for action in actions:
        exp_xml_event = next(exp_xml_events_iter)

        if action == 'get_next_event':
            parser.get_next_event()
        elif action == 'put_back_event':
            parser.put_back_event()
        else:
            assert action == 'expect_end'
            parser.expect_end()

        if exp_xml_event is not None:
            assert parser.event == exp_xml_event['event'], \
                "Unexpected XML event type {}; expected XML event {}".\
                format(parser.event, exp_xml_event)
            assert parser.element.tag == exp_xml_event['element_tag'], \
                "Unexpected XML event element tag {}; expected XML event {}".\
                format(parser.element.tag, exp_xml_event)
            assert parser.element.attrib == exp_xml_event['element_attrib'], \
                "Unexpected XML event element attributes {}; expected XML " \
                "event {}".\
                format(parser.element.tag, exp_xml_event)
            text = parser.element.text
            if text is not None and text.strip(' \n\r\t') == '':
                text = None
            assert text == exp_xml_event['element_text'], \
                "Unexpected XML event element content {!r}; expected XML " \
                "event {}".\
                format(text, exp_xml_event)

    # Ensure that expected exceptions have been raised
    assert testcase.exp_exc_types is None, \
        "Expected exception {!r} has not been raised".\
        format(testcase.exp_exc_types)


TESTCASES_REQUIRED_START_ELEMENT = [
    (
        "Expected start element present (from one element)",
        dict(
            names='PROPERTY',
            skip_events=0,
            xml_str=''
            '<PROPERTY NAME="CreationClassName" TYPE="string">\n'
            '  <VALUE>PyWBEM_Person</VALUE>\n'
            '</PROPERTY>\n',
            exp_xml_event=XmlEvent(
                'start', name='PROPERTY',
                attributes=dict(
                    NAME="CreationClassName",
                    TYPE="string"),
                content=None),
        ),
        None, None, True
    ),
    (
        "Expected start element present (from two elements)",
        dict(
            names=('VALUE', 'PROPERTY'),
            skip_events=0,
            xml_str=''
            '<PROPERTY NAME="CreationClassName" TYPE="string">\n'
            '  <VALUE>PyWBEM_Person</VALUE>\n'
            '</PROPERTY>\n',
            exp_xml_event=XmlEvent(
                'start', name='PROPERTY',
                attributes=dict(
                    NAME="CreationClassName",
                    TYPE="string"),
                content=None),
        ),
        None, None, True
    ),
    (
        "Different start element than expected present",
        dict(
            names='METHOD',
            skip_events=0,
            xml_str=''
            '<PROPERTY NAME="CreationClassName" TYPE="string">\n'
            '  <VALUE>PyWBEM_Person</VALUE>\n'
            '</PROPERTY>\n',
            exp_xml_event=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "End element present",
        dict(
            names='VALUE',
            skip_events=2,
            xml_str=''
            '<PROPERTY NAME="CreationClassName" TYPE="string">\n'
            '  <VALUE>PyWBEM_Person</VALUE>\n'
            '</PROPERTY>\n',
            exp_xml_event=None,
        ),
        CIMXMLParseError, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_REQUIRED_START_ELEMENT)
@simplified_test_function
def test_required_start_element(
        testcase, names, skip_events, xml_str, exp_xml_event):
    """
    Test CIMXMLParser.required_start_element().
    """

    parser = CIMXMLParser(xml_str)
    for _ in range(skip_events):
        parser.get_next_event()

    # Code to be tested
    xml_event = parser.required_start_element(names)

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None, \
        "Expected exception {!r} has not been raised".\
        format(testcase.exp_exc_types)

    assert xml_event == exp_xml_event


TESTCASES_OPTIONAL_START_ELEMENT = [
    (
        "Expected start element present (one name specified)",
        dict(
            names='PROPERTY',
            skip_events=0,
            xml_str=''
            '<PROPERTY NAME="CreationClassName" TYPE="string">\n'
            '  <VALUE>PyWBEM_Person</VALUE>\n'
            '</PROPERTY>\n',
            exp_xml_event=XmlEvent(
                'start', name='PROPERTY',
                attributes=dict(
                    NAME="CreationClassName",
                    TYPE="string"),
                content=None),
        ),
        None, None, True
    ),
    (
        "Expected start element present (two names specified)",
        dict(
            names=('METHOD', 'PROPERTY'),
            skip_events=0,
            xml_str=''
            '<PROPERTY NAME="CreationClassName" TYPE="string">\n'
            '  <VALUE>PyWBEM_Person</VALUE>\n'
            '</PROPERTY>\n',
            exp_xml_event=XmlEvent(
                'start', name='PROPERTY',
                attributes=dict(
                    NAME="CreationClassName",
                    TYPE="string"),
                content=None),
        ),
        None, None, True
    ),
    (
        "Different start element than expected present",
        dict(
            names='METHOD',
            skip_events=0,
            xml_str=''
            '<PROPERTY NAME="CreationClassName" TYPE="string">\n'
            '  <VALUE>PyWBEM_Person</VALUE>\n'
            '</PROPERTY>\n',
            exp_xml_event=None,
        ),
        None, None, True
    ),
    (
        "End element present",
        dict(
            names='VALUE',
            skip_events=2,
            xml_str=''
            '<PROPERTY NAME="CreationClassName" TYPE="string">\n'
            '  <VALUE>PyWBEM_Person</VALUE>\n'
            '</PROPERTY>\n',
            exp_xml_event=None,
        ),
        None, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_OPTIONAL_START_ELEMENT)
@simplified_test_function
def test_optional_start_element(
        testcase, names, skip_events, xml_str, exp_xml_event):
    """
    Test CIMXMLParser.optional_start_element().
    """

    parser = CIMXMLParser(xml_str)
    for _ in range(skip_events):
        parser.get_next_event()

    # Code to be tested
    xml_event = parser.optional_start_element(names)

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None, \
        "Expected exception {!r} has not been raised".\
        format(testcase.exp_exc_types)

    assert xml_event == exp_xml_event


TESTCASES_PEEK_NEXT_ELEMENT = [
    (
        "Peek at a start element",
        dict(
            skip_events=1,
            xml_str=''
            '<PROPERTY NAME="CreationClassName" TYPE="string">\n'
            '  <VALUE>PyWBEM_Person</VALUE>\n'
            '</PROPERTY>\n',
            exp_xml_event=XmlEvent('start', name='VALUE'),
        ),
        None, None, True
    ),
    (
        "Peek at an end element",
        dict(
            skip_events=2,
            xml_str=''
            '<PROPERTY NAME="CreationClassName" TYPE="string">\n'
            '  <VALUE>PyWBEM_Person</VALUE>\n'
            '</PROPERTY>\n',
            exp_xml_event=XmlEvent('end', name='VALUE'),
        ),
        None, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_PEEK_NEXT_ELEMENT)
@simplified_test_function
def test_peek_next_element(
        testcase, skip_events, xml_str, exp_xml_event):
    """
    Test CIMXMLParser.peek_next_element().
    """

    parser = CIMXMLParser(xml_str)
    for _ in range(skip_events):
        parser.get_next_event()

    # Code to be tested
    xml_event = parser.peek_next_element()

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None, \
        "Expected exception {!r} has not been raised".\
        format(testcase.exp_exc_types)

    assert xml_event == exp_xml_event

    # Verify that the element has not been consumed
    parser.get_next_event()
    xml_event_after = XmlEvent(parser.event, parser.element.tag)
    assert xml_event == xml_event_after


TESTCASES_TEST_START_ELEMENT = [
    (
        "Test for any start element, on a start element",
        dict(
            name=None,
            skip_events=1,
            xml_str=''
            '<PROPERTY NAME="CreationClassName" TYPE="string">\n'
            '  <VALUE>PyWBEM_Person</VALUE>\n'
            '</PROPERTY>\n',
            exp_result=True,
        ),
        None, None, True
    ),
    (
        "Test for any start element, on an end element",
        dict(
            name=None,
            skip_events=2,
            xml_str=''
            '<PROPERTY NAME="CreationClassName" TYPE="string">\n'
            '  <VALUE>PyWBEM_Person</VALUE>\n'
            '</PROPERTY>\n',
            exp_result=False,
        ),
        None, None, True
    ),
    (
        "Test for a specific start element, on a start element with that name",
        dict(
            name='VALUE',
            skip_events=1,
            xml_str=''
            '<PROPERTY NAME="CreationClassName" TYPE="string">\n'
            '  <VALUE>PyWBEM_Person</VALUE>\n'
            '</PROPERTY>\n',
            exp_result=True,
        ),
        None, None, True
    ),
    (
        "Test for a specific start element, on a start element with different "
        "name",
        dict(
            name='METHOD',
            skip_events=1,
            xml_str=''
            '<PROPERTY NAME="CreationClassName" TYPE="string">\n'
            '  <VALUE>PyWBEM_Person</VALUE>\n'
            '</PROPERTY>\n',
            exp_result=False,
        ),
        None, None, True
    ),
    (
        "Test for a specific start element, on an end element of that name",
        dict(
            name='VALUE',
            skip_events=2,
            xml_str=''
            '<PROPERTY NAME="CreationClassName" TYPE="string">\n'
            '  <VALUE>PyWBEM_Person</VALUE>\n'
            '</PROPERTY>\n',
            exp_result=False,
        ),
        None, None, True
    ),
    (
        "Test for a specific start element, on an end element of different "
        "name",
        dict(
            name='METHOD',
            skip_events=2,
            xml_str=''
            '<PROPERTY NAME="CreationClassName" TYPE="string">\n'
            '  <VALUE>PyWBEM_Person</VALUE>\n'
            '</PROPERTY>\n',
            exp_result=False,
        ),
        None, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_TEST_START_ELEMENT)
@simplified_test_function
def test_test_start_element(
        testcase, name, skip_events, xml_str, exp_result):
    """
    Test CIMXMLParser.test_start_element().
    """

    parser = CIMXMLParser(xml_str)
    for _ in range(skip_events):
        parser.get_next_event()

    xml_event_before = parser.peek_next_element()

    # Code to be tested
    result = parser.test_start_element(name)

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None, \
        "Expected exception {!r} has not been raised".\
        format(testcase.exp_exc_types)

    assert result == exp_result

    # Verify that the element has not been consumed
    xml_event_after = parser.peek_next_element()
    assert xml_event_before == xml_event_after


TESTCASES_EXPECT_NO_START_ELEMENT = [
    (
        "No start element with any name present, None returned",
        dict(
            skip_events=3,
            xml_str=''
            '<PROPERTY NAME="CreationClassName" TYPE="string">\n'
            '  <VALUE>PyWBEM_Person</VALUE>\n'
            '</PROPERTY>\n',
            name=None,
            exp_return=None,
        ),
        None, None, True
    ),
    (
        "Start element with any name present",
        dict(
            skip_events=0,
            xml_str=''
            '<PROPERTY NAME="CreationClassName" TYPE="string">\n'
            '  <VALUE>PyWBEM_Person</VALUE>\n'
            '</PROPERTY>\n',
            name=None,
            exp_return=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "Start element with specified name present",
        dict(
            skip_events=0,
            xml_str=''
            '<PROPERTY NAME="CreationClassName" TYPE="string">\n'
            '  <VALUE>PyWBEM_Person</VALUE>\n'
            '</PROPERTY>\n',
            name='PROPERTY',
            exp_return=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "Start element with different name present",
        dict(
            skip_events=0,
            xml_str=''
            '<PROPERTY NAME="CreationClassName" TYPE="string">\n'
            '  <VALUE>PyWBEM_Person</VALUE>\n'
            '</PROPERTY>\n',
            name='METHOD',
            exp_return=None,
        ),
        None, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_EXPECT_NO_START_ELEMENT)
@simplified_test_function
def test_expect_no_start_element(
        testcase, skip_events, xml_str, name, exp_return):
    """
    Test CIMXMLParser.expect_no_start_element().
    """

    parser = CIMXMLParser(xml_str)
    for _ in range(skip_events):
        parser.get_next_event()

    # Code to be tested
    return_value = parser.expect_no_start_element(name)

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None, \
        "Expected exception {!r} has not been raised".\
        format(testcase.exp_exc_types)

    assert return_value == exp_return


TESTCASES_REQUIRED_END_ELEMENT = [
    (
        "Expected end element present",
        dict(
            name='VALUE',
            allow_content=True,
            skip_events=2,
            xml_str=''
            '<PROPERTY NAME="CreationClassName" TYPE="string">\n'
            '  <VALUE>PyWBEM_Person</VALUE>\n'
            '</PROPERTY>\n',
            exp_xml_event=XmlEvent(
                'end', name='VALUE',
                attributes=dict(),
                content='PyWBEM_Person'),
        ),
        None, None, True
    ),
    (
        "Different end element present",
        dict(
            name='PROPERTY',
            allow_content=False,
            skip_events=2,
            xml_str=''
            '<PROPERTY NAME="CreationClassName" TYPE="string">\n'
            '  <VALUE>PyWBEM_Person</VALUE>\n'
            '</PROPERTY>\n',
            exp_xml_event=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "Start element present",
        dict(
            name='VALUE',
            allow_content=True,
            skip_events=1,
            xml_str=''
            '<PROPERTY NAME="CreationClassName" TYPE="string">\n'
            '  <VALUE>PyWBEM_Person</VALUE>\n'
            '</PROPERTY>\n',
            exp_xml_event=None,
        ),
        CIMXMLParseError, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_REQUIRED_END_ELEMENT)
@simplified_test_function
def test_required_end_element(
        testcase, name, allow_content, skip_events, xml_str, exp_xml_event):
    """
    Test CIMXMLParser.required_end_element().
    """

    parser = CIMXMLParser(xml_str)
    for _ in range(skip_events):
        parser.get_next_event()

    # Code to be tested
    xml_event = parser.required_end_element(name, allow_content)

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None, \
        "Expected exception {!r} has not been raised".\
        format(testcase.exp_exc_types)

    assert xml_event == exp_xml_event


TESTCASES_EXPECT_END = [
    (
        "Expected end is reached",
        dict(
            skip_events=4,
            xml_str=''
            '<PROPERTY NAME="CreationClassName" TYPE="string">\n'
            '  <VALUE>PyWBEM_Person</VALUE>\n'
            '</PROPERTY>\n',
            exp_return=None,
        ),
        None, None, True
    ),
    (
        "Expected end is not yet reached",
        dict(
            skip_events=3,
            xml_str=''
            '<PROPERTY NAME="CreationClassName" TYPE="string">\n'
            '  <VALUE>PyWBEM_Person</VALUE>\n'
            '</PROPERTY>\n',
            exp_return=None,
        ),
        CIMXMLParseError, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_EXPECT_END)
@simplified_test_function
def test_expect_end(
        testcase, skip_events, xml_str, exp_return):
    """
    Test CIMXMLParser.expect_end().
    """

    parser = CIMXMLParser(xml_str)
    for _ in range(skip_events):
        parser.get_next_event()

    # Code to be tested
    return_value = parser.expect_end()

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None, \
        "Expected exception {!r} has not been raised".\
        format(testcase.exp_exc_types)

    assert return_value == exp_return


TESTCASES_PARSE_CIMXML_OPERATION_RESPONSE = [

    # Note that the operations with their specific return values and output
    # parameters are not tested here, but in:
    # * test_optional_IRETURNVALUE_element() for return values
    # * test_list_of_operation_PARAMVALUE_elements() for output parameters
    # Various error scenarios are tested in:
    # * test_optional_ERROR_element()
    # Therefore, the tests here cover only one successful case and one
    # error case.

    (
        "OpenEnumerateInstances returning 2 instances and output parameters",
        dict(
            operation='OpenEnumerateInstances',
            xml_str=''
            '<?xml version="1.0" encoding="utf-8" ?>\n'
            '<CIM CIMVERSION="2.0" DTDVERSION="2.0">\n'
            '  <MESSAGE ID="1000" PROTOCOLVERSION="1.0">\n'
            '    <SIMPLERSP>\n'
            '      <IMETHODRESPONSE NAME="OpenEnumerateInstances">\n'
            '        <IRETURNVALUE>\n'
            '          <VALUE.INSTANCEWITHPATH>\n'
            '            <INSTANCEPATH>\n'
            '              <NAMESPACEPATH>\n'
            '                <HOST>woot.com</HOST>\n'
            '                <LOCALNAMESPACEPATH>\n'
            '                  <NAMESPACE NAME="foo"/>\n'
            '                </LOCALNAMESPACEPATH>\n'
            '              </NAMESPACEPATH>\n'
            '              <INSTANCENAME CLASSNAME="PyWBEM_Person"/>\n'
            '            </INSTANCEPATH>\n'
            '            <INSTANCE CLASSNAME="PyWBEM_Person">\n'
            '              <PROPERTY NAME="CreationClassName" TYPE="string">\n'
            '                <VALUE>PyWBEM_Person</VALUE>\n'
            '              </PROPERTY>\n'
            '              <PROPERTY NAME="Name" TYPE="string">\n'
            '                <VALUE>Fritz</VALUE>\n'
            '              </PROPERTY>\n'
            '            </INSTANCE>\n'
            '          </VALUE.INSTANCEWITHPATH>\n'
            '          <VALUE.INSTANCEWITHPATH>\n'
            '            <INSTANCEPATH>\n'
            '              <NAMESPACEPATH>\n'
            '                <HOST>woot.com</HOST>\n'
            '                <LOCALNAMESPACEPATH>\n'
            '                  <NAMESPACE NAME="foo"/>\n'
            '                </LOCALNAMESPACEPATH>\n'
            '              </NAMESPACEPATH>\n'
            '              <INSTANCENAME CLASSNAME="PyWBEM_Person"/>\n'
            '            </INSTANCEPATH>\n'
            '            <INSTANCE CLASSNAME="PyWBEM_Person">\n'
            '              <PROPERTY NAME="CreationClassName" TYPE="string">\n'
            '                <VALUE>PyWBEM_Person</VALUE>\n'
            '              </PROPERTY>\n'
            '              <PROPERTY NAME="Name" TYPE="string">\n'
            '                <VALUE>Alice</VALUE>\n'
            '              </PROPERTY>\n'
            '            </INSTANCE>\n'
            '          </VALUE.INSTANCEWITHPATH>\n'
            '        </IRETURNVALUE>\n'
            '        <PARAMVALUE NAME="EnumerationContext">\n'
            '          <VALUE>bla-enum-context</VALUE>\n'
            '        </PARAMVALUE>\n'
            '        <PARAMVALUE NAME="EndOfSequence">\n'
            '          <VALUE>FALSE</VALUE>\n'
            '        </PARAMVALUE>\n'
            '      </IMETHODRESPONSE>\n'
            '    </SIMPLERSP>\n'
            '  </MESSAGE>\n'
            '</CIM>\n',
            exp_result=(
                [
                    CIMInstance(
                        'PyWBEM_Person',
                        path=CIMInstanceName(
                            'PyWBEM_Person',
                            namespace='foo',
                            host='woot.com',
                        ),
                        properties=[
                            CIMProperty(
                                'CreationClassName', value='PyWBEM_Person',
                                type='string', propagated=False),
                            CIMProperty(
                                'Name', value='Fritz',
                                type='string', propagated=False),
                        ],
                    ),
                    CIMInstance(
                        'PyWBEM_Person',
                        path=CIMInstanceName(
                            'PyWBEM_Person',
                            namespace='foo',
                            host='woot.com',
                        ),
                        properties=[
                            CIMProperty(
                                'CreationClassName', value='PyWBEM_Person',
                                type='string', propagated=False),
                            CIMProperty(
                                'Name', value='Alice',
                                type='string', propagated=False),
                        ],
                    ),
                ],
                {
                    u'EnumerationContext': u'bla-enum-context',
                    u'EndOfSequence': False,
                },
            ),
        ),
        None, None, True
    ),
    (
        "OpenEnumerateInstances returning an error",
        dict(
            operation='OpenEnumerateInstances',
            xml_str=''
            '<?xml version="1.0" encoding="utf-8" ?>\n'
            '<CIM CIMVERSION="2.0" DTDVERSION="2.0">\n'
            '  <MESSAGE ID="1000" PROTOCOLVERSION="1.0">\n'
            '    <SIMPLERSP>\n'
            '      <IMETHODRESPONSE NAME="OpenEnumerateInstances">\n'
            '        <ERROR CODE="5" DESCRIPTION="bla">\n'
            '          <INSTANCE CLASSNAME="CIM_Error"/>\n'
            '        </ERROR>\n'
            '      </IMETHODRESPONSE>\n'
            '    </SIMPLERSP>\n'
            '  </MESSAGE>\n'
            '</CIM>\n',
            exp_result=(5, u'bla', [
                CIMInstance('CIM_Error'),
            ]),
        ),
        CIMError, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_PARSE_CIMXML_OPERATION_RESPONSE)
@simplified_test_function
def test_parse_cimxml_operation_response(
        testcase, operation, xml_str, exp_result):
    """
    Test CIMXMLParser.parse_cimxml_operation_response().
    """

    parser = CIMXMLParser(xml_str)
    result = parser.parse_cimxml_operation_response(operation)

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None, \
        "Expected exception {!r} has not been raised".\
        format(testcase.exp_exc_types)

    assert result == exp_result


TESTCASES_PARSE_CIMXML_METHOD_RESPONSE = [

    # Note that the operations with their specific return values and output
    # parameters are not tested here, but in:
    # * test_optional_RETURNVALUE_element() for return values
    # * test_list_of_method_PARAMVALUE_elements() for output parameters
    # Various error scenarios are tested in:
    # * test_optional_ERROR_element()
    # Therefore, the tests here cover only one successful case and one
    # error case.

    (
        "Method response returning integer and two output parameters",
        dict(
            method='MyMethod',
            xml_str=''
            '<?xml version="1.0" encoding="utf-8" ?>\n'
            '<CIM CIMVERSION="2.0" DTDVERSION="2.0">\n'
            '  <MESSAGE ID="1000" PROTOCOLVERSION="1.0">\n'
            '    <SIMPLERSP>\n'
            '      <METHODRESPONSE NAME="MyMethod">\n'
            '        <RETURNVALUE PARAMTYPE="uint32">\n'
            '          <VALUE>42</VALUE>\n'
            '        </RETURNVALUE>\n'
            '        <PARAMVALUE NAME="Foo1" PARAMTYPE="boolean">\n'
            '          <VALUE>FALSE</VALUE>\n'
            '        </PARAMVALUE>\n'
            '        <PARAMVALUE NAME="Foo2" PARAMTYPE="boolean">\n'
            '          <VALUE>TRUE</VALUE>\n'
            '        </PARAMVALUE>\n'
            '      </METHODRESPONSE>\n'
            '    </SIMPLERSP>\n'
            '  </MESSAGE>\n'
            '</CIM>\n',
            exp_result=(
                Uint32(42),
                {
                    u'Foo1': False,
                    u'Foo2': True,
                }
            ),
        ),
        None, None, True
    ),
    (
        "Method response returning an error",
        dict(
            method='MyMethod',
            xml_str=''
            '<?xml version="1.0" encoding="utf-8" ?>\n'
            '<CIM CIMVERSION="2.0" DTDVERSION="2.0">\n'
            '  <MESSAGE ID="1000" PROTOCOLVERSION="1.0">\n'
            '    <SIMPLERSP>\n'
            '      <METHODRESPONSE NAME="MyMethod">\n'
            '        <ERROR CODE="5" DESCRIPTION="bla">\n'
            '          <INSTANCE CLASSNAME="CIM_Error"/>\n'
            '        </ERROR>\n'
            '      </METHODRESPONSE>\n'
            '    </SIMPLERSP>\n'
            '  </MESSAGE>\n'
            '</CIM>\n',
            exp_result=(5, u'bla', [
                CIMInstance('CIM_Error'),
            ]),
        ),
        CIMError, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_PARSE_CIMXML_METHOD_RESPONSE)
@simplified_test_function
def test_parse_cimxml_method_response(
        testcase, method, xml_str, exp_result):
    """
    Test CIMXMLParser.parse_cimxml_method_response().
    """

    parser = CIMXMLParser(xml_str)
    result = parser.parse_cimxml_method_response(method)

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None, \
        "Expected exception {!r} has not been raised".\
        format(testcase.exp_exc_types)

    assert result == exp_result


TESTCASES_REQUIRED_CIM_START_ELEMENT = [
    (
        "CIM start element present with both attributes",
        dict(
            skip_events=0,
            xml_str=''
            '<CIM CIMVERSION="2.40" DTDVERSION="2.3">\n'
            '  <MESSAGE/>\n'
            '</CIM>\n',
            exp_cim_version='2.40',
            exp_dtd_version='2.3',
        ),
        None, None, True
    ),
    (
        "CIM start element present with DTDVERSION attribute missing",
        dict(
            skip_events=0,
            xml_str=''
            '<CIM CIMVERSION="2.40">\n'
            '  <MESSAGE/>\n'
            '</CIM>\n',
            exp_cim_version=None,
            exp_dtd_version=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "CIM start element present with CIMVERSION attribute missing",
        dict(
            skip_events=0,
            xml_str=''
            '<CIM DTDVERSION="2.3">\n'
            '  <MESSAGE/>\n'
            '</CIM>\n',
            exp_cim_version=None,
            exp_dtd_version=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "CIM start element present with no attributes",
        dict(
            skip_events=0,
            xml_str=''
            '<CIM>\n'
            '  <MESSAGE/>\n'
            '</CIM>\n',
            exp_cim_version=None,
            exp_dtd_version=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "CIM end element present",
        dict(
            skip_events=3,
            xml_str=''
            '<CIM>\n'
            '  <MESSAGE/>\n'
            '</CIM>\n',
            exp_cim_version=None,
            exp_dtd_version=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "Different start element than CIM present",
        dict(
            skip_events=0,
            xml_str=''
            '<PROPERTY NAME="CreationClassName" TYPE="string">\n'
            '  <VALUE>PyWBEM_Person</VALUE>\n'
            '</PROPERTY>\n',
            exp_cim_version=None,
            exp_dtd_version=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "CIM start element present with invalid syntax for DTDVERSION",
        dict(
            skip_events=0,
            xml_str=''
            '<CIM CIMVERSION="2.40" DTDVERSION="xxx">\n'
            '  <MESSAGE/>\n'
            '</CIM>\n',
            exp_cim_version=None,
            exp_dtd_version=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "CIM start element present with past major version for DTDVERSION",
        dict(
            skip_events=0,
            xml_str=''
            '<CIM CIMVERSION="2.40" DTDVERSION="1.1">\n'
            '  <MESSAGE/>\n'
            '</CIM>\n',
            exp_cim_version=None,
            exp_dtd_version=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "CIM start element present with future major version for DTDVERSION",
        dict(
            skip_events=0,
            xml_str=''
            '<CIM CIMVERSION="2.40" DTDVERSION="3.1">\n'
            '  <MESSAGE/>\n'
            '</CIM>\n',
            exp_cim_version=None,
            exp_dtd_version=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "CIM start element present with invalid syntax for CIMVERSION, "
        "which is ignored",
        dict(
            skip_events=0,
            xml_str=''
            '<CIM CIMVERSION="xxx" DTDVERSION="2.3">\n'
            '  <MESSAGE/>\n'
            '</CIM>\n',
            exp_cim_version='xxx',
            exp_dtd_version='2.3',
        ),
        None, None, True
    ),
    (
        "CIM start element present with past major version for CIMVERSION, "
        "which is ignored",
        dict(
            skip_events=0,
            xml_str=''
            '<CIM CIMVERSION="1.1" DTDVERSION="2.3">\n'
            '  <MESSAGE/>\n'
            '</CIM>\n',
            exp_cim_version='1.1',
            exp_dtd_version='2.3',
        ),
        None, None, True
    ),
    (
        "CIM start element present with future major version for CIMVERSION, "
        "which is ignored",
        dict(
            skip_events=0,
            xml_str=''
            '<CIM CIMVERSION="3.1" DTDVERSION="2.3">\n'
            '  <MESSAGE/>\n'
            '</CIM>\n',
            exp_cim_version='3.1',
            exp_dtd_version='2.3',
        ),
        None, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_REQUIRED_CIM_START_ELEMENT)
@simplified_test_function
def test_required_CIM_start_element(
        testcase, skip_events, xml_str, exp_cim_version, exp_dtd_version):
    """
    Test CIMXMLParser.required_CIM_start_element().
    """

    parser = CIMXMLParser(xml_str)
    for _ in range(skip_events):
        parser.get_next_event()

    # Code to be tested
    return_value = parser.required_CIM_start_element()

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None, \
        "Expected exception {!r} has not been raised".\
        format(testcase.exp_exc_types)

    cim_version, dtd_version = return_value

    assert cim_version == exp_cim_version
    assert dtd_version == exp_dtd_version


TESTCASES_REQUIRED_MESSAGE_START_ELEMENT = [
    (
        "MESSAGE start element present with both attributes, returning them",
        dict(
            skip_events=0,
            xml_str=''
            '<MESSAGE ID="42" PROTOCOLVERSION="1.3">\n'
            '  <SIMPLERSP/>\n'
            '</MESSAGE>\n',
            exp_id='42',
            exp_protocol_version='1.3',
        ),
        None, None, True
    ),
    (
        "MESSAGE start element present with PROTOCOLVERSION attribute missing",
        dict(
            skip_events=0,
            xml_str=''
            '<MESSAGE ID="42">\n'
            '  <SIMPLERSP/>\n'
            '</MESSAGE>\n',
            exp_id=None,
            exp_protocol_version=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "MESSAGE start element present with ID attribute missing",
        dict(
            skip_events=0,
            xml_str=''
            '<MESSAGE PROTOCOLVERSION="1.3">\n'
            '  <SIMPLERSP/>\n'
            '</MESSAGE>\n',
            exp_id=None,
            exp_protocol_version=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "MESSAGE start element present with no attributes",
        dict(
            skip_events=0,
            xml_str=''
            '<MESSAGE>\n'
            '  <SIMPLERSP/>\n'
            '</MESSAGE>\n',
            exp_id=None,
            exp_protocol_version=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "MESSAGE end element present",
        dict(
            skip_events=3,
            xml_str=''
            '<MESSAGE>\n'
            '  <SIMPLERSP/>\n'
            '</MESSAGE>\n',
            exp_id=None,
            exp_protocol_version=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "Different start element than MESSAGE present",
        dict(
            skip_events=0,
            xml_str=''
            '<PROPERTY NAME="CreationClassName" TYPE="string">\n'
            '  <VALUE>PyWBEM_Person</VALUE>\n'
            '</PROPERTY>\n',
            exp_id=None,
            exp_protocol_version=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "MESSAGE start element present with invalid syntax for "
        "PROTOCOLVERSION",
        dict(
            skip_events=0,
            xml_str=''
            '<MESSAGE ID="42" PROTOCOLVERSION="xxx">\n'
            '  <SIMPLERSP/>\n'
            '</MESSAGE>\n',
            exp_id=None,
            exp_protocol_version=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "MESSAGE start element present with past major version for "
        "PROTOCOLVERSION",
        dict(
            skip_events=0,
            xml_str=''
            '<MESSAGE ID="42" PROTOCOLVERSION="0.1">\n'
            '  <SIMPLERSP/>\n'
            '</MESSAGE>\n',
            exp_id=None,
            exp_protocol_version=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "MESSAGE start element present with future major version for "
        "PROTOCOLVERSION",
        dict(
            skip_events=0,
            xml_str=''
            '<MESSAGE ID="42" PROTOCOLVERSION="2.1">\n'
            '  <SIMPLERSP/>\n'
            '</MESSAGE>\n',
            exp_id=None,
            exp_protocol_version=None,
        ),
        CIMXMLParseError, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_REQUIRED_MESSAGE_START_ELEMENT)
@simplified_test_function
def test_required_MESSAGE_start_element(
        testcase, skip_events, xml_str, exp_id, exp_protocol_version):
    """
    Test CIMXMLParser.required_MESSAGE_start_element().
    """

    parser = CIMXMLParser(xml_str)
    for _ in range(skip_events):
        parser.get_next_event()

    # Code to be tested
    return_value = parser.required_MESSAGE_start_element()

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None, \
        "Expected exception {!r} has not been raised".\
        format(testcase.exp_exc_types)

    id_, protocol_version = return_value

    assert id_ == exp_id
    assert protocol_version == exp_protocol_version


TESTCASES_REQUIRED_SIMPLERSP_START_ELEMENT = [
    (
        "SIMPLERSP start element present",
        dict(
            xml_str=''
            '<SIMPLERSP>\n'
            '  <IMETHODRESPONSE/>\n'
            '</SIMPLERSP>\n',
        ),
        None, None, True
    ),
    (
        "Different start element than SIMPLERSP present",
        dict(
            xml_str=''
            '<PROPERTY NAME="CreationClassName" TYPE="string">\n'
            '  <VALUE>PyWBEM_Person</VALUE>\n'
            '</PROPERTY>\n',
        ),
        CIMXMLParseError, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_REQUIRED_SIMPLERSP_START_ELEMENT)
@simplified_test_function
def test_required_SIMPLERSP_start_element(testcase, xml_str):
    """
    Test CIMXMLParser.required_SIMPLERSP_start_element().
    """

    parser = CIMXMLParser(xml_str)

    # Code to be tested
    parser.required_SIMPLERSP_start_element()

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None, \
        "Expected exception {!r} has not been raised".\
        format(testcase.exp_exc_types)


TESTCASES_REQUIRED_IMETHODRESPONSE_START_ELEMENT = [
    (
        "IMETHODRESPONSE start element present with expected operation name",
        dict(
            operation='EnumerateInstances',
            xml_str=''
            '<IMETHODRESPONSE NAME="EnumerateInstances">\n'
            '  <IRETURNVALUE/>\n'
            '</IMETHODRESPONSE>\n',
        ),
        None, None, True
    ),
    (
        "IMETHODRESPONSE start element present with unexpected operation "
        "name",
        dict(
            operation='EnumerateInstances',
            xml_str=''
            '<IMETHODRESPONSE NAME="EnumerateInstanceNames">\n'
            '  <IRETURNVALUE/>\n'
            '</IMETHODRESPONSE>\n',
        ),
        CIMXMLParseError, None, True
    ),
    (
        "IMETHODRESPONSE start element present but NAME attribute missing",
        dict(
            operation='EnumerateInstances',
            xml_str=''
            '<IMETHODRESPONSE>\n'
            '  <IRETURNVALUE/>\n'
            '</IMETHODRESPONSE>\n',
        ),
        CIMXMLParseError, None, True
    ),
    (
        "Different start element than IMETHODRESPONSE present",
        dict(
            operation='EnumerateInstances',
            xml_str=''
            '<PROPERTY NAME="CreationClassName" TYPE="string">\n'
            '  <VALUE>PyWBEM_Person</VALUE>\n'
            '</PROPERTY>\n',
        ),
        CIMXMLParseError, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_REQUIRED_IMETHODRESPONSE_START_ELEMENT)
@simplified_test_function
def test_required_IMETHODRESPONSE_start_element(testcase, operation, xml_str):
    """
    Test CIMXMLParser.required_IMETHODRESPONSE_start_element().
    """

    parser = CIMXMLParser(xml_str)

    # Code to be tested
    parser.required_IMETHODRESPONSE_start_element(operation)

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None, \
        "Expected exception {!r} has not been raised".\
        format(testcase.exp_exc_types)


TESTCASES_OPTIONAL_IRETURNVALUE_ELEMENT = [

    # Testcases for EnumerateInstances
    (
        "IRETURNVALUE element for EnumerateInstances is missing",
        dict(
            operation='EnumerateInstances',
            xml_str='<DUMMY/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "IRETURNVALUE element for EnumerateInstances, with empty "
        "result set",
        dict(
            operation='EnumerateInstances',
            xml_str=''
            '<IRETURNVALUE NAME="EnumerateInstances">\n'
            '</IRETURNVALUE>\n',
            exp_result=[],
        ),
        None, None, True
    ),
    (
        "IRETURNVALUE element for EnumerateInstances, with one "
        "instance in result set",
        dict(
            operation='EnumerateInstances',
            xml_str=''
            '<IRETURNVALUE NAME="EnumerateInstances">\n'
            '  <VALUE.NAMEDINSTANCE>\n'
            '    <INSTANCENAME CLASSNAME="CIM_Foo"/>\n'
            '    <INSTANCE CLASSNAME="CIM_Foo"/>\n'
            '  </VALUE.NAMEDINSTANCE>\n'
            '</IRETURNVALUE>\n',
            exp_result=[
                CIMInstance(
                    'CIM_Foo',
                    path=CIMInstanceName('CIM_Foo')),
            ],
        ),
        None, None, True
    ),
    (
        "IRETURNVALUE element for EnumerateInstances, with two "
        "instances in result set",
        dict(
            operation='EnumerateInstances',
            xml_str=''
            '<IRETURNVALUE NAME="EnumerateInstances">\n'
            '  <VALUE.NAMEDINSTANCE>\n'
            '    <INSTANCENAME CLASSNAME="CIM_Foo1"/>\n'
            '    <INSTANCE CLASSNAME="CIM_Foo1"/>\n'
            '  </VALUE.NAMEDINSTANCE>\n'
            '  <VALUE.NAMEDINSTANCE>\n'
            '    <INSTANCENAME CLASSNAME="CIM_Foo2"/>\n'
            '    <INSTANCE CLASSNAME="CIM_Foo2"/>\n'
            '  </VALUE.NAMEDINSTANCE>\n'
            '</IRETURNVALUE>\n',
            exp_result=[
                CIMInstance(
                    'CIM_Foo1',
                    path=CIMInstanceName('CIM_Foo1')),
                CIMInstance(
                    'CIM_Foo2',
                    path=CIMInstanceName('CIM_Foo2')),
            ],
        ),
        None, None, True
    ),

    # Testcases for EnumerateInstanceNames
    (
        "IRETURNVALUE element for EnumerateInstanceNames is missing",
        dict(
            operation='EnumerateInstanceNames',
            xml_str='<DUMMY/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "IRETURNVALUE element for EnumerateInstanceNames, with empty "
        "result set",
        dict(
            operation='EnumerateInstanceNames',
            xml_str=''
            '<IRETURNVALUE NAME="EnumerateInstanceNames">\n'
            '</IRETURNVALUE>\n',
            exp_result=[],
        ),
        None, None, True
    ),
    (
        "IRETURNVALUE element for EnumerateInstanceNames, with one "
        "instance path in result set",
        dict(
            operation='EnumerateInstanceNames',
            xml_str=''
            '<IRETURNVALUE NAME="EnumerateInstanceNames">\n'
            '  <INSTANCENAME CLASSNAME="CIM_Foo"/>\n'
            '</IRETURNVALUE>\n',
            exp_result=[
                CIMInstanceName('CIM_Foo'),
            ],
        ),
        None, None, True
    ),
    (
        "IRETURNVALUE element for EnumerateInstanceNames, with two "
        "instance paths in result set",
        dict(
            operation='EnumerateInstanceNames',
            xml_str=''
            '<IRETURNVALUE NAME="EnumerateInstanceNames">\n'
            '  <INSTANCENAME CLASSNAME="CIM_Foo1"/>\n'
            '  <INSTANCENAME CLASSNAME="CIM_Foo2"/>\n'
            '</IRETURNVALUE>\n',
            exp_result=[
                CIMInstanceName('CIM_Foo1'),
                CIMInstanceName('CIM_Foo2'),
            ],
        ),
        None, None, True
    ),

    # Testcases for GetInstance
    (
        "IRETURNVALUE element for GetInstance is missing",
        dict(
            operation='GetInstance',
            xml_str='<DUMMY/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "IRETURNVALUE element for GetInstance, with instance missing",
        dict(
            operation='GetInstance',
            xml_str=''
            '<IRETURNVALUE NAME="GetInstance">\n'
            '</IRETURNVALUE>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "IRETURNVALUE element for GetInstance, with instance",
        dict(
            operation='GetInstance',
            xml_str=''
            '<IRETURNVALUE NAME="GetInstance">\n'
            '  <INSTANCE CLASSNAME="CIM_Foo"/>\n'
            '</IRETURNVALUE>\n',
            exp_result=CIMInstance('CIM_Foo'),
        ),
        None, None, True
    ),

    # Testcases for CreateInstance
    (
        "IRETURNVALUE element for CreateInstance is missing",
        dict(
            operation='CreateInstance',
            xml_str='<DUMMY/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "IRETURNVALUE element for CreateInstance, with instance path missing",
        dict(
            operation='CreateInstance',
            xml_str=''
            '<IRETURNVALUE NAME="CreateInstance">\n'
            '</IRETURNVALUE>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "IRETURNVALUE element for CreateInstance, with instance path",
        dict(
            operation='CreateInstance',
            xml_str=''
            '<IRETURNVALUE NAME="CreateInstance">\n'
            '  <INSTANCENAME CLASSNAME="CIM_Foo"/>\n'
            '</IRETURNVALUE>\n',
            exp_result=CIMInstanceName('CIM_Foo'),
        ),
        None, None, True
    ),

    # Testcases for Associators
    (
        "IRETURNVALUE element for Associators is missing",
        dict(
            operation='Associators',
            xml_str='<DUMMY/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "IRETURNVALUE element for Associators, with empty "
        "result set",
        dict(
            operation='Associators',
            xml_str=''
            '<IRETURNVALUE NAME="Associators">\n'
            '</IRETURNVALUE>\n',
            exp_result=[],
        ),
        None, None, True
    ),
    (
        "IRETURNVALUE element for Associators, with one "
        "instance in result set",
        dict(
            operation='Associators',
            xml_str=''
            '<IRETURNVALUE NAME="Associators">\n'
            '  <VALUE.OBJECTWITHPATH>\n'
            '    <INSTANCEPATH>\n'
            '      <NAMESPACEPATH>\n'
            '        <HOST>woot.com</HOST>\n'
            '        <LOCALNAMESPACEPATH>\n'
            '          <NAMESPACE NAME="foo"/>\n'
            '        </LOCALNAMESPACEPATH>\n'
            '      </NAMESPACEPATH>\n'
            '      <INSTANCENAME CLASSNAME="CIM_Foo"/>\n'
            '    </INSTANCEPATH>\n'
            '    <INSTANCE CLASSNAME="CIM_Foo"/>\n'
            '  </VALUE.OBJECTWITHPATH>\n'
            '</IRETURNVALUE>\n',
            exp_result=[
                CIMInstance(
                    'CIM_Foo',
                    path=CIMInstanceName(
                        'CIM_Foo',
                        namespace='foo',
                        host='woot.com',
                    ),
                ),
            ],
        ),
        None, None, True
    ),
    (
        "IRETURNVALUE element for Associators, with two "
        "instances in result set",
        dict(
            operation='Associators',
            xml_str=''
            '<IRETURNVALUE NAME="Associators">\n'
            '  <VALUE.OBJECTWITHPATH>\n'
            '    <INSTANCEPATH>\n'
            '      <NAMESPACEPATH>\n'
            '        <HOST>woot.com</HOST>\n'
            '        <LOCALNAMESPACEPATH>\n'
            '          <NAMESPACE NAME="foo"/>\n'
            '        </LOCALNAMESPACEPATH>\n'
            '      </NAMESPACEPATH>\n'
            '      <INSTANCENAME CLASSNAME="CIM_Foo1"/>\n'
            '    </INSTANCEPATH>\n'
            '    <INSTANCE CLASSNAME="CIM_Foo1"/>\n'
            '  </VALUE.OBJECTWITHPATH>\n'
            '  <VALUE.OBJECTWITHPATH>\n'
            '    <INSTANCEPATH>\n'
            '      <NAMESPACEPATH>\n'
            '        <HOST>woot.com</HOST>\n'
            '        <LOCALNAMESPACEPATH>\n'
            '          <NAMESPACE NAME="foo"/>\n'
            '        </LOCALNAMESPACEPATH>\n'
            '      </NAMESPACEPATH>\n'
            '      <INSTANCENAME CLASSNAME="CIM_Foo2"/>\n'
            '    </INSTANCEPATH>\n'
            '    <INSTANCE CLASSNAME="CIM_Foo2"/>\n'
            '  </VALUE.OBJECTWITHPATH>\n'
            '</IRETURNVALUE>\n',
            exp_result=[
                CIMInstance(
                    'CIM_Foo1',
                    path=CIMInstanceName(
                        'CIM_Foo1',
                        namespace='foo',
                        host='woot.com',
                    ),
                ),
                CIMInstance(
                    'CIM_Foo2',
                    path=CIMInstanceName(
                        'CIM_Foo2',
                        namespace='foo',
                        host='woot.com',
                    ),
                ),
            ],
        ),
        None, None, True
    ),
    (
        "IRETURNVALUE element for Associators, with one "
        "class in result set",
        dict(
            operation='Associators',
            xml_str=''
            '<IRETURNVALUE NAME="Associators">\n'
            '  <VALUE.OBJECTWITHPATH>\n'
            '    <CLASSPATH>\n'
            '      <NAMESPACEPATH>\n'
            '        <HOST>woot.com</HOST>\n'
            '        <LOCALNAMESPACEPATH>\n'
            '          <NAMESPACE NAME="foo"/>\n'
            '        </LOCALNAMESPACEPATH>\n'
            '      </NAMESPACEPATH>\n'
            '      <CLASSNAME NAME="CIM_Foo"/>\n'
            '    </CLASSPATH>\n'
            '    <CLASS NAME="CIM_Foo"/>\n'
            '  </VALUE.OBJECTWITHPATH>\n'
            '</IRETURNVALUE>\n',
            exp_result=[
                CIMClass(
                    'CIM_Foo',
                    path=CIMClassName(
                        'CIM_Foo',
                        namespace='foo',
                        host='woot.com',
                    ),
                ),
            ],
        ),
        None, None, True
    ),
    (
        "IRETURNVALUE element for Associators, with two "
        "classes in result set",
        dict(
            operation='Associators',
            xml_str=''
            '<IRETURNVALUE NAME="Associators">\n'
            '  <VALUE.OBJECTWITHPATH>\n'
            '    <CLASSPATH>\n'
            '      <NAMESPACEPATH>\n'
            '        <HOST>woot.com</HOST>\n'
            '        <LOCALNAMESPACEPATH>\n'
            '          <NAMESPACE NAME="foo"/>\n'
            '        </LOCALNAMESPACEPATH>\n'
            '      </NAMESPACEPATH>\n'
            '      <CLASSNAME NAME="CIM_Foo1"/>\n'
            '    </CLASSPATH>\n'
            '    <CLASS NAME="CIM_Foo1"/>\n'
            '  </VALUE.OBJECTWITHPATH>\n'
            '  <VALUE.OBJECTWITHPATH>\n'
            '    <CLASSPATH>\n'
            '      <NAMESPACEPATH>\n'
            '        <HOST>woot.com</HOST>\n'
            '        <LOCALNAMESPACEPATH>\n'
            '          <NAMESPACE NAME="foo"/>\n'
            '        </LOCALNAMESPACEPATH>\n'
            '      </NAMESPACEPATH>\n'
            '      <CLASSNAME NAME="CIM_Foo2"/>\n'
            '    </CLASSPATH>\n'
            '    <CLASS NAME="CIM_Foo2"/>\n'
            '  </VALUE.OBJECTWITHPATH>\n'
            '</IRETURNVALUE>\n',
            exp_result=[
                CIMClass(
                    'CIM_Foo1',
                    path=CIMClassName(
                        'CIM_Foo1',
                        namespace='foo',
                        host='woot.com',
                    ),
                ),
                CIMClass(
                    'CIM_Foo2',
                    path=CIMClassName(
                        'CIM_Foo2',
                        namespace='foo',
                        host='woot.com',
                    ),
                ),
            ],
        ),
        None, None, True
    ),

    # Testcases for AssociatorNames
    (
        "IRETURNVALUE element for AssociatorNames is missing",
        dict(
            operation='AssociatorNames',
            xml_str='<DUMMY/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "IRETURNVALUE element for AssociatorNames, with empty "
        "result set",
        dict(
            operation='AssociatorNames',
            xml_str=''
            '<IRETURNVALUE NAME="AssociatorNames">\n'
            '</IRETURNVALUE>\n',
            exp_result=[],
        ),
        None, None, True
    ),
    (
        "IRETURNVALUE element for AssociatorNames, with one "
        "instance path in result set",
        dict(
            operation='AssociatorNames',
            xml_str=''
            '<IRETURNVALUE NAME="AssociatorNames">\n'
            '  <OBJECTPATH>\n'
            '    <INSTANCEPATH>\n'
            '      <NAMESPACEPATH>\n'
            '        <HOST>woot.com</HOST>\n'
            '        <LOCALNAMESPACEPATH>\n'
            '          <NAMESPACE NAME="foo"/>\n'
            '        </LOCALNAMESPACEPATH>\n'
            '      </NAMESPACEPATH>\n'
            '      <INSTANCENAME CLASSNAME="CIM_Foo"/>\n'
            '    </INSTANCEPATH>\n'
            '  </OBJECTPATH>\n'
            '</IRETURNVALUE>\n',
            exp_result=[
                CIMInstanceName(
                    'CIM_Foo',
                    namespace='foo',
                    host='woot.com',
                ),
            ],
        ),
        None, None, True
    ),
    (
        "IRETURNVALUE element for AssociatorNames, with two "
        "instance paths in result set",
        dict(
            operation='AssociatorNames',
            xml_str=''
            '<IRETURNVALUE NAME="AssociatorNames">\n'
            '  <OBJECTPATH>\n'
            '    <INSTANCEPATH>\n'
            '      <NAMESPACEPATH>\n'
            '        <HOST>woot.com</HOST>\n'
            '        <LOCALNAMESPACEPATH>\n'
            '          <NAMESPACE NAME="foo"/>\n'
            '        </LOCALNAMESPACEPATH>\n'
            '      </NAMESPACEPATH>\n'
            '      <INSTANCENAME CLASSNAME="CIM_Foo1"/>\n'
            '    </INSTANCEPATH>\n'
            '  </OBJECTPATH>\n'
            '  <OBJECTPATH>\n'
            '    <INSTANCEPATH>\n'
            '      <NAMESPACEPATH>\n'
            '        <HOST>woot.com</HOST>\n'
            '        <LOCALNAMESPACEPATH>\n'
            '          <NAMESPACE NAME="foo"/>\n'
            '        </LOCALNAMESPACEPATH>\n'
            '      </NAMESPACEPATH>\n'
            '      <INSTANCENAME CLASSNAME="CIM_Foo2"/>\n'
            '    </INSTANCEPATH>\n'
            '  </OBJECTPATH>\n'
            '</IRETURNVALUE>\n',
            exp_result=[
                CIMInstanceName(
                    'CIM_Foo1',
                    namespace='foo',
                    host='woot.com',
                ),
                CIMInstanceName(
                    'CIM_Foo2',
                    namespace='foo',
                    host='woot.com',
                ),
            ],
        ),
        None, None, True
    ),
    (
        "IRETURNVALUE element for AssociatorNames, with one "
        "class path in result set",
        dict(
            operation='AssociatorNames',
            xml_str=''
            '<IRETURNVALUE NAME="AssociatorNames">\n'
            '  <OBJECTPATH>\n'
            '    <CLASSPATH>\n'
            '      <NAMESPACEPATH>\n'
            '        <HOST>woot.com</HOST>\n'
            '        <LOCALNAMESPACEPATH>\n'
            '          <NAMESPACE NAME="foo"/>\n'
            '        </LOCALNAMESPACEPATH>\n'
            '      </NAMESPACEPATH>\n'
            '      <CLASSNAME NAME="CIM_Foo"/>\n'
            '    </CLASSPATH>\n'
            '  </OBJECTPATH>\n'
            '</IRETURNVALUE>\n',
            exp_result=[
                CIMClassName(
                    'CIM_Foo',
                    namespace='foo',
                    host='woot.com',
                ),
            ],
        ),
        None, None, True
    ),
    (
        "IRETURNVALUE element for AssociatorNames, with two "
        "class paths in result set",
        dict(
            operation='AssociatorNames',
            xml_str=''
            '<IRETURNVALUE NAME="AssociatorNames">\n'
            '  <OBJECTPATH>\n'
            '    <CLASSPATH>\n'
            '      <NAMESPACEPATH>\n'
            '        <HOST>woot.com</HOST>\n'
            '        <LOCALNAMESPACEPATH>\n'
            '          <NAMESPACE NAME="foo"/>\n'
            '        </LOCALNAMESPACEPATH>\n'
            '      </NAMESPACEPATH>\n'
            '      <CLASSNAME NAME="CIM_Foo1"/>\n'
            '    </CLASSPATH>\n'
            '  </OBJECTPATH>\n'
            '  <OBJECTPATH>\n'
            '    <CLASSPATH>\n'
            '      <NAMESPACEPATH>\n'
            '        <HOST>woot.com</HOST>\n'
            '        <LOCALNAMESPACEPATH>\n'
            '          <NAMESPACE NAME="foo"/>\n'
            '        </LOCALNAMESPACEPATH>\n'
            '      </NAMESPACEPATH>\n'
            '      <CLASSNAME NAME="CIM_Foo2"/>\n'
            '    </CLASSPATH>\n'
            '  </OBJECTPATH>\n'
            '</IRETURNVALUE>\n',
            exp_result=[
                CIMClassName(
                    'CIM_Foo1',
                    namespace='foo',
                    host='woot.com',
                ),
                CIMClassName(
                    'CIM_Foo2',
                    namespace='foo',
                    host='woot.com',
                ),
            ],
        ),
        None, None, True
    ),

    # Testcases for References
    (
        "IRETURNVALUE element for References is missing",
        dict(
            operation='References',
            xml_str='<DUMMY/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "IRETURNVALUE element for References, with empty "
        "result set",
        dict(
            operation='References',
            xml_str=''
            '<IRETURNVALUE NAME="References">\n'
            '</IRETURNVALUE>\n',
            exp_result=[],
        ),
        None, None, True
    ),
    (
        "IRETURNVALUE element for References, with one "
        "instance in result set",
        dict(
            operation='References',
            xml_str=''
            '<IRETURNVALUE NAME="References">\n'
            '  <VALUE.OBJECTWITHPATH>\n'
            '    <INSTANCEPATH>\n'
            '      <NAMESPACEPATH>\n'
            '        <HOST>woot.com</HOST>\n'
            '        <LOCALNAMESPACEPATH>\n'
            '          <NAMESPACE NAME="foo"/>\n'
            '        </LOCALNAMESPACEPATH>\n'
            '      </NAMESPACEPATH>\n'
            '      <INSTANCENAME CLASSNAME="CIM_Foo"/>\n'
            '    </INSTANCEPATH>\n'
            '    <INSTANCE CLASSNAME="CIM_Foo"/>\n'
            '  </VALUE.OBJECTWITHPATH>\n'
            '</IRETURNVALUE>\n',
            exp_result=[
                CIMInstance(
                    'CIM_Foo',
                    path=CIMInstanceName(
                        'CIM_Foo',
                        namespace='foo',
                        host='woot.com',
                    ),
                ),
            ],
        ),
        None, None, True
    ),
    (
        "IRETURNVALUE element for References, with two "
        "instances in result set",
        dict(
            operation='References',
            xml_str=''
            '<IRETURNVALUE NAME="References">\n'
            '  <VALUE.OBJECTWITHPATH>\n'
            '    <INSTANCEPATH>\n'
            '      <NAMESPACEPATH>\n'
            '        <HOST>woot.com</HOST>\n'
            '        <LOCALNAMESPACEPATH>\n'
            '          <NAMESPACE NAME="foo"/>\n'
            '        </LOCALNAMESPACEPATH>\n'
            '      </NAMESPACEPATH>\n'
            '      <INSTANCENAME CLASSNAME="CIM_Foo1"/>\n'
            '    </INSTANCEPATH>\n'
            '    <INSTANCE CLASSNAME="CIM_Foo1"/>\n'
            '  </VALUE.OBJECTWITHPATH>\n'
            '  <VALUE.OBJECTWITHPATH>\n'
            '    <INSTANCEPATH>\n'
            '      <NAMESPACEPATH>\n'
            '        <HOST>woot.com</HOST>\n'
            '        <LOCALNAMESPACEPATH>\n'
            '          <NAMESPACE NAME="foo"/>\n'
            '        </LOCALNAMESPACEPATH>\n'
            '      </NAMESPACEPATH>\n'
            '      <INSTANCENAME CLASSNAME="CIM_Foo2"/>\n'
            '    </INSTANCEPATH>\n'
            '    <INSTANCE CLASSNAME="CIM_Foo2"/>\n'
            '  </VALUE.OBJECTWITHPATH>\n'
            '</IRETURNVALUE>\n',
            exp_result=[
                CIMInstance(
                    'CIM_Foo1',
                    path=CIMInstanceName(
                        'CIM_Foo1',
                        namespace='foo',
                        host='woot.com',
                    ),
                ),
                CIMInstance(
                    'CIM_Foo2',
                    path=CIMInstanceName(
                        'CIM_Foo2',
                        namespace='foo',
                        host='woot.com',
                    ),
                ),
            ],
        ),
        None, None, True
    ),
    (
        "IRETURNVALUE element for References, with one "
        "class in result set",
        dict(
            operation='References',
            xml_str=''
            '<IRETURNVALUE NAME="References">\n'
            '  <VALUE.OBJECTWITHPATH>\n'
            '    <CLASSPATH>\n'
            '      <NAMESPACEPATH>\n'
            '        <HOST>woot.com</HOST>\n'
            '        <LOCALNAMESPACEPATH>\n'
            '          <NAMESPACE NAME="foo"/>\n'
            '        </LOCALNAMESPACEPATH>\n'
            '      </NAMESPACEPATH>\n'
            '      <CLASSNAME NAME="CIM_Foo"/>\n'
            '    </CLASSPATH>\n'
            '    <CLASS NAME="CIM_Foo"/>\n'
            '  </VALUE.OBJECTWITHPATH>\n'
            '</IRETURNVALUE>\n',
            exp_result=[
                CIMClass(
                    'CIM_Foo',
                    path=CIMClassName(
                        'CIM_Foo',
                        namespace='foo',
                        host='woot.com',
                    ),
                ),
            ],
        ),
        None, None, True
    ),
    (
        "IRETURNVALUE element for References, with two "
        "classes in result set",
        dict(
            operation='References',
            xml_str=''
            '<IRETURNVALUE NAME="References">\n'
            '  <VALUE.OBJECTWITHPATH>\n'
            '    <CLASSPATH>\n'
            '      <NAMESPACEPATH>\n'
            '        <HOST>woot.com</HOST>\n'
            '        <LOCALNAMESPACEPATH>\n'
            '          <NAMESPACE NAME="foo"/>\n'
            '        </LOCALNAMESPACEPATH>\n'
            '      </NAMESPACEPATH>\n'
            '      <CLASSNAME NAME="CIM_Foo1"/>\n'
            '    </CLASSPATH>\n'
            '    <CLASS NAME="CIM_Foo1"/>\n'
            '  </VALUE.OBJECTWITHPATH>\n'
            '  <VALUE.OBJECTWITHPATH>\n'
            '    <CLASSPATH>\n'
            '      <NAMESPACEPATH>\n'
            '        <HOST>woot.com</HOST>\n'
            '        <LOCALNAMESPACEPATH>\n'
            '          <NAMESPACE NAME="foo"/>\n'
            '        </LOCALNAMESPACEPATH>\n'
            '      </NAMESPACEPATH>\n'
            '      <CLASSNAME NAME="CIM_Foo2"/>\n'
            '    </CLASSPATH>\n'
            '    <CLASS NAME="CIM_Foo2"/>\n'
            '  </VALUE.OBJECTWITHPATH>\n'
            '</IRETURNVALUE>\n',
            exp_result=[
                CIMClass(
                    'CIM_Foo1',
                    path=CIMClassName(
                        'CIM_Foo1',
                        namespace='foo',
                        host='woot.com',
                    ),
                ),
                CIMClass(
                    'CIM_Foo2',
                    path=CIMClassName(
                        'CIM_Foo2',
                        namespace='foo',
                        host='woot.com',
                    ),
                ),
            ],
        ),
        None, None, True
    ),

    # Testcases for ReferenceNames
    (
        "IRETURNVALUE element for ReferenceNames is missing",
        dict(
            operation='ReferenceNames',
            xml_str='<DUMMY/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "IRETURNVALUE element for ReferenceNames, with empty "
        "result set",
        dict(
            operation='ReferenceNames',
            xml_str=''
            '<IRETURNVALUE NAME="ReferenceNames">\n'
            '</IRETURNVALUE>\n',
            exp_result=[],
        ),
        None, None, True
    ),
    (
        "IRETURNVALUE element for ReferenceNames, with one "
        "instance path in result set",
        dict(
            operation='ReferenceNames',
            xml_str=''
            '<IRETURNVALUE NAME="ReferenceNames">\n'
            '  <OBJECTPATH>\n'
            '    <INSTANCEPATH>\n'
            '      <NAMESPACEPATH>\n'
            '        <HOST>woot.com</HOST>\n'
            '        <LOCALNAMESPACEPATH>\n'
            '          <NAMESPACE NAME="foo"/>\n'
            '        </LOCALNAMESPACEPATH>\n'
            '      </NAMESPACEPATH>\n'
            '      <INSTANCENAME CLASSNAME="CIM_Foo"/>\n'
            '    </INSTANCEPATH>\n'
            '  </OBJECTPATH>\n'
            '</IRETURNVALUE>\n',
            exp_result=[
                CIMInstanceName(
                    'CIM_Foo',
                    namespace='foo',
                    host='woot.com',
                ),
            ],
        ),
        None, None, True
    ),
    (
        "IRETURNVALUE element for ReferenceNames, with two "
        "instance paths in result set",
        dict(
            operation='ReferenceNames',
            xml_str=''
            '<IRETURNVALUE NAME="ReferenceNames">\n'
            '  <OBJECTPATH>\n'
            '    <INSTANCEPATH>\n'
            '      <NAMESPACEPATH>\n'
            '        <HOST>woot.com</HOST>\n'
            '        <LOCALNAMESPACEPATH>\n'
            '          <NAMESPACE NAME="foo"/>\n'
            '        </LOCALNAMESPACEPATH>\n'
            '      </NAMESPACEPATH>\n'
            '      <INSTANCENAME CLASSNAME="CIM_Foo1"/>\n'
            '    </INSTANCEPATH>\n'
            '  </OBJECTPATH>\n'
            '  <OBJECTPATH>\n'
            '    <INSTANCEPATH>\n'
            '      <NAMESPACEPATH>\n'
            '        <HOST>woot.com</HOST>\n'
            '        <LOCALNAMESPACEPATH>\n'
            '          <NAMESPACE NAME="foo"/>\n'
            '        </LOCALNAMESPACEPATH>\n'
            '      </NAMESPACEPATH>\n'
            '      <INSTANCENAME CLASSNAME="CIM_Foo2"/>\n'
            '    </INSTANCEPATH>\n'
            '  </OBJECTPATH>\n'
            '</IRETURNVALUE>\n',
            exp_result=[
                CIMInstanceName(
                    'CIM_Foo1',
                    namespace='foo',
                    host='woot.com',
                ),
                CIMInstanceName(
                    'CIM_Foo2',
                    namespace='foo',
                    host='woot.com',
                ),
            ],
        ),
        None, None, True
    ),
    (
        "IRETURNVALUE element for ReferenceNames, with one "
        "class path in result set",
        dict(
            operation='ReferenceNames',
            xml_str=''
            '<IRETURNVALUE NAME="ReferenceNames">\n'
            '  <OBJECTPATH>\n'
            '    <CLASSPATH>\n'
            '      <NAMESPACEPATH>\n'
            '        <HOST>woot.com</HOST>\n'
            '        <LOCALNAMESPACEPATH>\n'
            '          <NAMESPACE NAME="foo"/>\n'
            '        </LOCALNAMESPACEPATH>\n'
            '      </NAMESPACEPATH>\n'
            '      <CLASSNAME NAME="CIM_Foo"/>\n'
            '    </CLASSPATH>\n'
            '  </OBJECTPATH>\n'
            '</IRETURNVALUE>\n',
            exp_result=[
                CIMClassName(
                    'CIM_Foo',
                    namespace='foo',
                    host='woot.com',
                ),
            ],
        ),
        None, None, True
    ),
    (
        "IRETURNVALUE element for ReferenceNames, with two "
        "class paths in result set",
        dict(
            operation='ReferenceNames',
            xml_str=''
            '<IRETURNVALUE NAME="ReferenceNames">\n'
            '  <OBJECTPATH>\n'
            '    <CLASSPATH>\n'
            '      <NAMESPACEPATH>\n'
            '        <HOST>woot.com</HOST>\n'
            '        <LOCALNAMESPACEPATH>\n'
            '          <NAMESPACE NAME="foo"/>\n'
            '        </LOCALNAMESPACEPATH>\n'
            '      </NAMESPACEPATH>\n'
            '      <CLASSNAME NAME="CIM_Foo1"/>\n'
            '    </CLASSPATH>\n'
            '  </OBJECTPATH>\n'
            '  <OBJECTPATH>\n'
            '    <CLASSPATH>\n'
            '      <NAMESPACEPATH>\n'
            '        <HOST>woot.com</HOST>\n'
            '        <LOCALNAMESPACEPATH>\n'
            '          <NAMESPACE NAME="foo"/>\n'
            '        </LOCALNAMESPACEPATH>\n'
            '      </NAMESPACEPATH>\n'
            '      <CLASSNAME NAME="CIM_Foo2"/>\n'
            '    </CLASSPATH>\n'
            '  </OBJECTPATH>\n'
            '</IRETURNVALUE>\n',
            exp_result=[
                CIMClassName(
                    'CIM_Foo1',
                    namespace='foo',
                    host='woot.com',
                ),
                CIMClassName(
                    'CIM_Foo2',
                    namespace='foo',
                    host='woot.com',
                ),
            ],
        ),
        None, None, True
    ),

    # Testcases for ExecQuery
    (
        "IRETURNVALUE element for ExecQuery is missing",
        dict(
            operation='ExecQuery',
            xml_str='<DUMMY/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "IRETURNVALUE element for ExecQuery, with empty "
        "result set",
        dict(
            operation='ExecQuery',
            xml_str=''
            '<IRETURNVALUE NAME="ExecQuery">\n'
            '</IRETURNVALUE>\n',
            exp_result=[],
        ),
        None, None, True
    ),
    (
        "IRETURNVALUE element for ExecQuery, with one "
        "instance (as VALUE.OBJECT) in result set",
        dict(
            operation='ExecQuery',
            xml_str=''
            '<IRETURNVALUE NAME="ExecQuery">\n'
            '  <VALUE.OBJECT>\n'
            '    <INSTANCE CLASSNAME="CIM_Foo"/>\n'
            '  </VALUE.OBJECT>\n'
            '</IRETURNVALUE>\n',
            exp_result=[
                CIMInstance('CIM_Foo'),
            ],
        ),
        None, None, True
    ),
    (
        "IRETURNVALUE element for ExecQuery, with two "
        "instances (as VALUE.OBJECT) in result set",
        dict(
            operation='ExecQuery',
            xml_str=''
            '<IRETURNVALUE NAME="ExecQuery">\n'
            '  <VALUE.OBJECT>\n'
            '    <INSTANCE CLASSNAME="CIM_Foo1"/>\n'
            '  </VALUE.OBJECT>\n'
            '  <VALUE.OBJECT>\n'
            '    <INSTANCE CLASSNAME="CIM_Foo2"/>\n'
            '  </VALUE.OBJECT>\n'
            '</IRETURNVALUE>\n',
            exp_result=[
                CIMInstance('CIM_Foo1'),
                CIMInstance('CIM_Foo2'),
            ],
        ),
        None, None, True
    ),
    (
        "IRETURNVALUE element for ExecQuery, with one "
        "class (as VALUE.OBJECT) in result set",
        dict(
            operation='ExecQuery',
            xml_str=''
            '<IRETURNVALUE NAME="ExecQuery">\n'
            '  <VALUE.OBJECT>\n'
            '    <CLASS NAME="CIM_Foo"/>\n'
            '  </VALUE.OBJECT>\n'
            '</IRETURNVALUE>\n',
            exp_result=[
                CIMClass('CIM_Foo'),
            ],
        ),
        None, None, True
    ),
    (
        "IRETURNVALUE element for ExecQuery, with two "
        "classes (as VALUE.OBJECT) in result set",
        dict(
            operation='ExecQuery',
            xml_str=''
            '<IRETURNVALUE NAME="ExecQuery">\n'
            '  <VALUE.OBJECT>\n'
            '    <CLASS NAME="CIM_Foo1"/>\n'
            '  </VALUE.OBJECT>\n'
            '  <VALUE.OBJECT>\n'
            '    <CLASS NAME="CIM_Foo2"/>\n'
            '  </VALUE.OBJECT>\n'
            '</IRETURNVALUE>\n',
            exp_result=[
                CIMClass('CIM_Foo1'),
                CIMClass('CIM_Foo2'),
            ],
        ),
        None, None, True
    ),
    (
        "IRETURNVALUE element for ExecQuery, with one "
        "instance (as VALUE.OBJECTWITHLOCALPATH) in result set",
        dict(
            operation='ExecQuery',
            xml_str=''
            '<IRETURNVALUE NAME="ExecQuery">\n'
            '  <VALUE.OBJECTWITHLOCALPATH>\n'
            '    <LOCALINSTANCEPATH>\n'
            '      <LOCALNAMESPACEPATH>\n'
            '        <NAMESPACE NAME="foo"/>\n'
            '      </LOCALNAMESPACEPATH>\n'
            '      <INSTANCENAME CLASSNAME="CIM_Foo"/>\n'
            '    </LOCALINSTANCEPATH>\n'
            '    <INSTANCE CLASSNAME="CIM_Foo"/>\n'
            '  </VALUE.OBJECTWITHLOCALPATH>\n'
            '</IRETURNVALUE>\n',
            exp_result=[
                CIMInstance(
                    'CIM_Foo',
                    path=CIMInstanceName(
                        'CIM_Foo',
                        namespace='foo',
                    ),
                ),
            ],
        ),
        None, None, True
    ),
    (
        "IRETURNVALUE element for ExecQuery, with two "
        "instances (as VALUE.OBJECTWITHLOCALPATH) in result set",
        dict(
            operation='ExecQuery',
            xml_str=''
            '<IRETURNVALUE NAME="ExecQuery">\n'
            '  <VALUE.OBJECTWITHLOCALPATH>\n'
            '    <LOCALINSTANCEPATH>\n'
            '      <LOCALNAMESPACEPATH>\n'
            '        <NAMESPACE NAME="foo"/>\n'
            '      </LOCALNAMESPACEPATH>\n'
            '      <INSTANCENAME CLASSNAME="CIM_Foo1"/>\n'
            '    </LOCALINSTANCEPATH>\n'
            '    <INSTANCE CLASSNAME="CIM_Foo1"/>\n'
            '  </VALUE.OBJECTWITHLOCALPATH>\n'
            '  <VALUE.OBJECTWITHLOCALPATH>\n'
            '    <LOCALINSTANCEPATH>\n'
            '      <LOCALNAMESPACEPATH>\n'
            '        <NAMESPACE NAME="foo"/>\n'
            '      </LOCALNAMESPACEPATH>\n'
            '      <INSTANCENAME CLASSNAME="CIM_Foo2"/>\n'
            '    </LOCALINSTANCEPATH>\n'
            '    <INSTANCE CLASSNAME="CIM_Foo2"/>\n'
            '  </VALUE.OBJECTWITHLOCALPATH>\n'
            '</IRETURNVALUE>\n',
            exp_result=[
                CIMInstance(
                    'CIM_Foo1',
                    path=CIMInstanceName(
                        'CIM_Foo1',
                        namespace='foo',
                    ),
                ),
                CIMInstance(
                    'CIM_Foo2',
                    path=CIMInstanceName(
                        'CIM_Foo2',
                        namespace='foo',
                    ),
                ),
            ],
        ),
        None, None, True
    ),
    (
        "IRETURNVALUE element for ExecQuery, with one "
        "class (as VALUE.OBJECTWITHLOCALPATH) in result set",
        dict(
            operation='ExecQuery',
            xml_str=''
            '<IRETURNVALUE NAME="ExecQuery">\n'
            '  <VALUE.OBJECTWITHLOCALPATH>\n'
            '    <LOCALCLASSPATH>\n'
            '      <LOCALNAMESPACEPATH>\n'
            '        <NAMESPACE NAME="foo"/>\n'
            '      </LOCALNAMESPACEPATH>\n'
            '      <CLASSNAME NAME="CIM_Foo"/>\n'
            '    </LOCALCLASSPATH>\n'
            '    <CLASS NAME="CIM_Foo"/>\n'
            '  </VALUE.OBJECTWITHLOCALPATH>\n'
            '</IRETURNVALUE>\n',
            exp_result=[
                CIMClass(
                    'CIM_Foo',
                    path=CIMClassName(
                        'CIM_Foo',
                        namespace='foo',
                    ),
                ),
            ],
        ),
        None, None, True
    ),
    (
        "IRETURNVALUE element for ExecQuery, with two "
        "classes (as VALUE.OBJECTWITHLOCALPATH) in result set",
        dict(
            operation='ExecQuery',
            xml_str=''
            '<IRETURNVALUE NAME="ExecQuery">\n'
            '  <VALUE.OBJECTWITHLOCALPATH>\n'
            '    <LOCALCLASSPATH>\n'
            '      <LOCALNAMESPACEPATH>\n'
            '        <NAMESPACE NAME="foo"/>\n'
            '      </LOCALNAMESPACEPATH>\n'
            '      <CLASSNAME NAME="CIM_Foo1"/>\n'
            '    </LOCALCLASSPATH>\n'
            '    <CLASS NAME="CIM_Foo1"/>\n'
            '  </VALUE.OBJECTWITHLOCALPATH>\n'
            '  <VALUE.OBJECTWITHLOCALPATH>\n'
            '    <LOCALCLASSPATH>\n'
            '      <LOCALNAMESPACEPATH>\n'
            '        <NAMESPACE NAME="foo"/>\n'
            '      </LOCALNAMESPACEPATH>\n'
            '      <CLASSNAME NAME="CIM_Foo2"/>\n'
            '    </LOCALCLASSPATH>\n'
            '    <CLASS NAME="CIM_Foo2"/>\n'
            '  </VALUE.OBJECTWITHLOCALPATH>\n'
            '</IRETURNVALUE>\n',
            exp_result=[
                CIMClass(
                    'CIM_Foo1',
                    path=CIMClassName(
                        'CIM_Foo1',
                        namespace='foo',
                    ),
                ),
                CIMClass(
                    'CIM_Foo2',
                    path=CIMClassName(
                        'CIM_Foo2',
                        namespace='foo',
                    ),
                ),
            ],
        ),
        None, None, True
    ),
    (
        "IRETURNVALUE element for ExecQuery, with one "
        "instance (as VALUE.OBJECTWITHPATH) in result set",
        dict(
            operation='ExecQuery',
            xml_str=''
            '<IRETURNVALUE NAME="ExecQuery">\n'
            '  <VALUE.OBJECTWITHPATH>\n'
            '    <INSTANCEPATH>\n'
            '      <NAMESPACEPATH>\n'
            '        <HOST>woot.com</HOST>\n'
            '        <LOCALNAMESPACEPATH>\n'
            '          <NAMESPACE NAME="foo"/>\n'
            '        </LOCALNAMESPACEPATH>\n'
            '      </NAMESPACEPATH>\n'
            '      <INSTANCENAME CLASSNAME="CIM_Foo"/>\n'
            '    </INSTANCEPATH>\n'
            '    <INSTANCE CLASSNAME="CIM_Foo"/>\n'
            '  </VALUE.OBJECTWITHPATH>\n'
            '</IRETURNVALUE>\n',
            exp_result=[
                CIMInstance(
                    'CIM_Foo',
                    path=CIMInstanceName(
                        'CIM_Foo',
                        namespace='foo',
                        host='woot.com',
                    ),
                ),
            ],
        ),
        None, None, True
    ),
    (
        "IRETURNVALUE element for ExecQuery, with two "
        "instances (as VALUE.OBJECTWITHPATH) in result set",
        dict(
            operation='ExecQuery',
            xml_str=''
            '<IRETURNVALUE NAME="ExecQuery">\n'
            '  <VALUE.OBJECTWITHPATH>\n'
            '    <INSTANCEPATH>\n'
            '      <NAMESPACEPATH>\n'
            '        <HOST>woot.com</HOST>\n'
            '        <LOCALNAMESPACEPATH>\n'
            '          <NAMESPACE NAME="foo"/>\n'
            '        </LOCALNAMESPACEPATH>\n'
            '      </NAMESPACEPATH>\n'
            '      <INSTANCENAME CLASSNAME="CIM_Foo1"/>\n'
            '    </INSTANCEPATH>\n'
            '    <INSTANCE CLASSNAME="CIM_Foo1"/>\n'
            '  </VALUE.OBJECTWITHPATH>\n'
            '  <VALUE.OBJECTWITHPATH>\n'
            '    <INSTANCEPATH>\n'
            '      <NAMESPACEPATH>\n'
            '        <HOST>woot.com</HOST>\n'
            '        <LOCALNAMESPACEPATH>\n'
            '          <NAMESPACE NAME="foo"/>\n'
            '        </LOCALNAMESPACEPATH>\n'
            '      </NAMESPACEPATH>\n'
            '      <INSTANCENAME CLASSNAME="CIM_Foo2"/>\n'
            '    </INSTANCEPATH>\n'
            '    <INSTANCE CLASSNAME="CIM_Foo2"/>\n'
            '  </VALUE.OBJECTWITHPATH>\n'
            '</IRETURNVALUE>\n',
            exp_result=[
                CIMInstance(
                    'CIM_Foo1',
                    path=CIMInstanceName(
                        'CIM_Foo1',
                        namespace='foo',
                        host='woot.com',
                    ),
                ),
                CIMInstance(
                    'CIM_Foo2',
                    path=CIMInstanceName(
                        'CIM_Foo2',
                        namespace='foo',
                        host='woot.com',
                    ),
                ),
            ],
        ),
        None, None, True
    ),
    (
        "IRETURNVALUE element for ExecQuery, with one "
        "class (as VALUE.OBJECTWITHPATH) in result set",
        dict(
            operation='ExecQuery',
            xml_str=''
            '<IRETURNVALUE NAME="ExecQuery">\n'
            '  <VALUE.OBJECTWITHPATH>\n'
            '    <CLASSPATH>\n'
            '      <NAMESPACEPATH>\n'
            '        <HOST>woot.com</HOST>\n'
            '        <LOCALNAMESPACEPATH>\n'
            '          <NAMESPACE NAME="foo"/>\n'
            '        </LOCALNAMESPACEPATH>\n'
            '      </NAMESPACEPATH>\n'
            '      <CLASSNAME NAME="CIM_Foo"/>\n'
            '    </CLASSPATH>\n'
            '    <CLASS NAME="CIM_Foo"/>\n'
            '  </VALUE.OBJECTWITHPATH>\n'
            '</IRETURNVALUE>\n',
            exp_result=[
                CIMClass(
                    'CIM_Foo',
                    path=CIMClassName(
                        'CIM_Foo',
                        namespace='foo',
                        host='woot.com',
                    ),
                ),
            ],
        ),
        None, None, True
    ),
    (
        "IRETURNVALUE element for ExecQuery, with two "
        "classes (as VALUE.OBJECTWITHPATH) in result set",
        dict(
            operation='ExecQuery',
            xml_str=''
            '<IRETURNVALUE NAME="ExecQuery">\n'
            '  <VALUE.OBJECTWITHPATH>\n'
            '    <CLASSPATH>\n'
            '      <NAMESPACEPATH>\n'
            '        <HOST>woot.com</HOST>\n'
            '        <LOCALNAMESPACEPATH>\n'
            '          <NAMESPACE NAME="foo"/>\n'
            '        </LOCALNAMESPACEPATH>\n'
            '      </NAMESPACEPATH>\n'
            '      <CLASSNAME NAME="CIM_Foo1"/>\n'
            '    </CLASSPATH>\n'
            '    <CLASS NAME="CIM_Foo1"/>\n'
            '  </VALUE.OBJECTWITHPATH>\n'
            '  <VALUE.OBJECTWITHPATH>\n'
            '    <CLASSPATH>\n'
            '      <NAMESPACEPATH>\n'
            '        <HOST>woot.com</HOST>\n'
            '        <LOCALNAMESPACEPATH>\n'
            '          <NAMESPACE NAME="foo"/>\n'
            '        </LOCALNAMESPACEPATH>\n'
            '      </NAMESPACEPATH>\n'
            '      <CLASSNAME NAME="CIM_Foo2"/>\n'
            '    </CLASSPATH>\n'
            '    <CLASS NAME="CIM_Foo2"/>\n'
            '  </VALUE.OBJECTWITHPATH>\n'
            '</IRETURNVALUE>\n',
            exp_result=[
                CIMClass(
                    'CIM_Foo1',
                    path=CIMClassName(
                        'CIM_Foo1',
                        namespace='foo',
                        host='woot.com',
                    ),
                ),
                CIMClass(
                    'CIM_Foo2',
                    path=CIMClassName(
                        'CIM_Foo2',
                        namespace='foo',
                        host='woot.com',
                    ),
                ),
            ],
        ),
        None, None, True
    ),

    # Testcases for OpenEnumerateInstances
    (
        "IRETURNVALUE element for OpenEnumerateInstances is missing",
        dict(
            operation='OpenEnumerateInstances',
            xml_str='<DUMMY/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "IRETURNVALUE element for OpenEnumerateInstances, with empty "
        "result set",
        dict(
            operation='OpenEnumerateInstances',
            xml_str=''
            '<IRETURNVALUE NAME="OpenEnumerateInstances">\n'
            '</IRETURNVALUE>\n',
            exp_result=[],
        ),
        None, None, True
    ),
    (
        "IRETURNVALUE element for OpenEnumerateInstances, with one "
        "instance in result set",
        dict(
            operation='OpenEnumerateInstances',
            xml_str=''
            '<IRETURNVALUE NAME="OpenEnumerateInstances">\n'
            '  <VALUE.INSTANCEWITHPATH>\n'
            '    <INSTANCEPATH>\n'
            '      <NAMESPACEPATH>\n'
            '        <HOST>woot.com</HOST>\n'
            '        <LOCALNAMESPACEPATH>\n'
            '          <NAMESPACE NAME="foo"/>\n'
            '        </LOCALNAMESPACEPATH>\n'
            '      </NAMESPACEPATH>\n'
            '      <INSTANCENAME CLASSNAME="CIM_Foo"/>\n'
            '    </INSTANCEPATH>\n'
            '    <INSTANCE CLASSNAME="CIM_Foo"/>\n'
            '  </VALUE.INSTANCEWITHPATH>\n'
            '</IRETURNVALUE>\n',
            exp_result=[
                CIMInstance(
                    'CIM_Foo',
                    path=CIMInstanceName(
                        'CIM_Foo',
                        namespace='foo',
                        host='woot.com',
                    ),
                ),
            ],
        ),
        None, None, True
    ),
    (
        "IRETURNVALUE element for OpenEnumerateInstances, with two "
        "instances in result set",
        dict(
            operation='OpenEnumerateInstances',
            xml_str=''
            '<IRETURNVALUE NAME="OpenEnumerateInstances">\n'
            '  <VALUE.INSTANCEWITHPATH>\n'
            '    <INSTANCEPATH>\n'
            '      <NAMESPACEPATH>\n'
            '        <HOST>woot.com</HOST>\n'
            '        <LOCALNAMESPACEPATH>\n'
            '          <NAMESPACE NAME="foo"/>\n'
            '        </LOCALNAMESPACEPATH>\n'
            '      </NAMESPACEPATH>\n'
            '      <INSTANCENAME CLASSNAME="CIM_Foo1"/>\n'
            '    </INSTANCEPATH>\n'
            '    <INSTANCE CLASSNAME="CIM_Foo1"/>\n'
            '  </VALUE.INSTANCEWITHPATH>\n'
            '  <VALUE.INSTANCEWITHPATH>\n'
            '    <INSTANCEPATH>\n'
            '      <NAMESPACEPATH>\n'
            '        <HOST>woot.com</HOST>\n'
            '        <LOCALNAMESPACEPATH>\n'
            '          <NAMESPACE NAME="foo"/>\n'
            '        </LOCALNAMESPACEPATH>\n'
            '      </NAMESPACEPATH>\n'
            '      <INSTANCENAME CLASSNAME="CIM_Foo2"/>\n'
            '    </INSTANCEPATH>\n'
            '    <INSTANCE CLASSNAME="CIM_Foo2"/>\n'
            '  </VALUE.INSTANCEWITHPATH>\n'
            '</IRETURNVALUE>\n',
            exp_result=[
                CIMInstance(
                    'CIM_Foo1',
                    path=CIMInstanceName(
                        'CIM_Foo1',
                        namespace='foo',
                        host='woot.com',
                    ),
                ),
                CIMInstance(
                    'CIM_Foo2',
                    path=CIMInstanceName(
                        'CIM_Foo2',
                        namespace='foo',
                        host='woot.com',
                    ),
                ),
            ],
        ),
        None, None, True
    ),

    # Testcases for OpenEnumerateInstancePaths
    (
        "IRETURNVALUE element for OpenEnumerateInstancePaths is missing",
        dict(
            operation='OpenEnumerateInstancePaths',
            xml_str='<DUMMY/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "IRETURNVALUE element for OpenEnumerateInstancePaths, with empty "
        "result set",
        dict(
            operation='OpenEnumerateInstancePaths',
            xml_str=''
            '<IRETURNVALUE NAME="OpenEnumerateInstancePaths">\n'
            '</IRETURNVALUE>\n',
            exp_result=[],
        ),
        None, None, True
    ),
    (
        "IRETURNVALUE element for OpenEnumerateInstancePaths, with one "
        "instance path in result set",
        dict(
            operation='OpenEnumerateInstancePaths',
            xml_str=''
            '<IRETURNVALUE NAME="OpenEnumerateInstancePaths">\n'
            '  <INSTANCEPATH>\n'
            '    <NAMESPACEPATH>\n'
            '      <HOST>woot.com</HOST>\n'
            '      <LOCALNAMESPACEPATH>\n'
            '        <NAMESPACE NAME="foo"/>\n'
            '      </LOCALNAMESPACEPATH>\n'
            '    </NAMESPACEPATH>\n'
            '    <INSTANCENAME CLASSNAME="CIM_Foo"/>\n'
            '  </INSTANCEPATH>\n'
            '</IRETURNVALUE>\n',
            exp_result=[
                CIMInstanceName(
                    'CIM_Foo',
                    namespace='foo',
                    host='woot.com',
                ),
            ],
        ),
        None, None, True
    ),
    (
        "IRETURNVALUE element for OpenEnumerateInstancePaths, with two "
        "instance paths in result set",
        dict(
            operation='OpenEnumerateInstancePaths',
            xml_str=''
            '<IRETURNVALUE NAME="OpenEnumerateInstancePaths">\n'
            '  <INSTANCEPATH>\n'
            '    <NAMESPACEPATH>\n'
            '      <HOST>woot.com</HOST>\n'
            '      <LOCALNAMESPACEPATH>\n'
            '        <NAMESPACE NAME="foo"/>\n'
            '      </LOCALNAMESPACEPATH>\n'
            '    </NAMESPACEPATH>\n'
            '    <INSTANCENAME CLASSNAME="CIM_Foo1"/>\n'
            '  </INSTANCEPATH>\n'
            '  <INSTANCEPATH>\n'
            '    <NAMESPACEPATH>\n'
            '      <HOST>woot.com</HOST>\n'
            '      <LOCALNAMESPACEPATH>\n'
            '        <NAMESPACE NAME="foo"/>\n'
            '      </LOCALNAMESPACEPATH>\n'
            '    </NAMESPACEPATH>\n'
            '    <INSTANCENAME CLASSNAME="CIM_Foo2"/>\n'
            '  </INSTANCEPATH>\n'
            '</IRETURNVALUE>\n',
            exp_result=[
                CIMInstanceName(
                    'CIM_Foo1',
                    namespace='foo',
                    host='woot.com',
                ),
                CIMInstanceName(
                    'CIM_Foo2',
                    namespace='foo',
                    host='woot.com',
                ),
            ],
        ),
        None, None, True
    ),

    # Testcases for OpenAssociatorInstances
    (
        "IRETURNVALUE element for OpenAssociatorInstances is missing",
        dict(
            operation='OpenAssociatorInstances',
            xml_str='<DUMMY/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "IRETURNVALUE element for OpenAssociatorInstances, with empty "
        "result set",
        dict(
            operation='OpenAssociatorInstances',
            xml_str=''
            '<IRETURNVALUE NAME="OpenAssociatorInstances">\n'
            '</IRETURNVALUE>\n',
            exp_result=[],
        ),
        None, None, True
    ),
    (
        "IRETURNVALUE element for OpenAssociatorInstances, with one "
        "instance in result set",
        dict(
            operation='OpenAssociatorInstances',
            xml_str=''
            '<IRETURNVALUE NAME="OpenAssociatorInstances">\n'
            '  <VALUE.INSTANCEWITHPATH>\n'
            '    <INSTANCEPATH>\n'
            '      <NAMESPACEPATH>\n'
            '        <HOST>woot.com</HOST>\n'
            '        <LOCALNAMESPACEPATH>\n'
            '          <NAMESPACE NAME="foo"/>\n'
            '        </LOCALNAMESPACEPATH>\n'
            '      </NAMESPACEPATH>\n'
            '      <INSTANCENAME CLASSNAME="CIM_Foo"/>\n'
            '    </INSTANCEPATH>\n'
            '    <INSTANCE CLASSNAME="CIM_Foo"/>\n'
            '  </VALUE.INSTANCEWITHPATH>\n'
            '</IRETURNVALUE>\n',
            exp_result=[
                CIMInstance(
                    'CIM_Foo',
                    path=CIMInstanceName(
                        'CIM_Foo',
                        namespace='foo',
                        host='woot.com',
                    ),
                ),
            ],
        ),
        None, None, True
    ),
    (
        "IRETURNVALUE element for OpenAssociatorInstances, with two "
        "instances in result set",
        dict(
            operation='OpenAssociatorInstances',
            xml_str=''
            '<IRETURNVALUE NAME="OpenAssociatorInstances">\n'
            '  <VALUE.INSTANCEWITHPATH>\n'
            '    <INSTANCEPATH>\n'
            '      <NAMESPACEPATH>\n'
            '        <HOST>woot.com</HOST>\n'
            '        <LOCALNAMESPACEPATH>\n'
            '          <NAMESPACE NAME="foo"/>\n'
            '        </LOCALNAMESPACEPATH>\n'
            '      </NAMESPACEPATH>\n'
            '      <INSTANCENAME CLASSNAME="CIM_Foo1"/>\n'
            '    </INSTANCEPATH>\n'
            '    <INSTANCE CLASSNAME="CIM_Foo1"/>\n'
            '  </VALUE.INSTANCEWITHPATH>\n'
            '  <VALUE.INSTANCEWITHPATH>\n'
            '    <INSTANCEPATH>\n'
            '      <NAMESPACEPATH>\n'
            '        <HOST>woot.com</HOST>\n'
            '        <LOCALNAMESPACEPATH>\n'
            '          <NAMESPACE NAME="foo"/>\n'
            '        </LOCALNAMESPACEPATH>\n'
            '      </NAMESPACEPATH>\n'
            '      <INSTANCENAME CLASSNAME="CIM_Foo2"/>\n'
            '    </INSTANCEPATH>\n'
            '    <INSTANCE CLASSNAME="CIM_Foo2"/>\n'
            '  </VALUE.INSTANCEWITHPATH>\n'
            '</IRETURNVALUE>\n',
            exp_result=[
                CIMInstance(
                    'CIM_Foo1',
                    path=CIMInstanceName(
                        'CIM_Foo1',
                        namespace='foo',
                        host='woot.com',
                    ),
                ),
                CIMInstance(
                    'CIM_Foo2',
                    path=CIMInstanceName(
                        'CIM_Foo2',
                        namespace='foo',
                        host='woot.com',
                    ),
                ),
            ],
        ),
        None, None, True
    ),

    # Testcases for OpenAssociatorInstancePaths
    (
        "IRETURNVALUE element for OpenAssociatorInstancePaths is missing",
        dict(
            operation='OpenAssociatorInstancePaths',
            xml_str='<DUMMY/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "IRETURNVALUE element for OpenAssociatorInstancePaths, with empty "
        "result set",
        dict(
            operation='OpenAssociatorInstancePaths',
            xml_str=''
            '<IRETURNVALUE NAME="OpenAssociatorInstancePaths">\n'
            '</IRETURNVALUE>\n',
            exp_result=[],
        ),
        None, None, True
    ),
    (
        "IRETURNVALUE element for OpenAssociatorInstancePaths, with one "
        "instance path in result set",
        dict(
            operation='OpenAssociatorInstancePaths',
            xml_str=''
            '<IRETURNVALUE NAME="OpenAssociatorInstancePaths">\n'
            '  <INSTANCEPATH>\n'
            '    <NAMESPACEPATH>\n'
            '      <HOST>woot.com</HOST>\n'
            '      <LOCALNAMESPACEPATH>\n'
            '        <NAMESPACE NAME="foo"/>\n'
            '      </LOCALNAMESPACEPATH>\n'
            '    </NAMESPACEPATH>\n'
            '    <INSTANCENAME CLASSNAME="CIM_Foo"/>\n'
            '  </INSTANCEPATH>\n'
            '</IRETURNVALUE>\n',
            exp_result=[
                CIMInstanceName(
                    'CIM_Foo',
                    namespace='foo',
                    host='woot.com',
                ),
            ],
        ),
        None, None, True
    ),
    (
        "IRETURNVALUE element for OpenAssociatorInstancePaths, with two "
        "instance paths in result set",
        dict(
            operation='OpenAssociatorInstancePaths',
            xml_str=''
            '<IRETURNVALUE NAME="OpenAssociatorInstancePaths">\n'
            '  <INSTANCEPATH>\n'
            '    <NAMESPACEPATH>\n'
            '      <HOST>woot.com</HOST>\n'
            '      <LOCALNAMESPACEPATH>\n'
            '        <NAMESPACE NAME="foo"/>\n'
            '      </LOCALNAMESPACEPATH>\n'
            '    </NAMESPACEPATH>\n'
            '    <INSTANCENAME CLASSNAME="CIM_Foo1"/>\n'
            '  </INSTANCEPATH>\n'
            '  <INSTANCEPATH>\n'
            '    <NAMESPACEPATH>\n'
            '      <HOST>woot.com</HOST>\n'
            '      <LOCALNAMESPACEPATH>\n'
            '        <NAMESPACE NAME="foo"/>\n'
            '      </LOCALNAMESPACEPATH>\n'
            '    </NAMESPACEPATH>\n'
            '    <INSTANCENAME CLASSNAME="CIM_Foo2"/>\n'
            '  </INSTANCEPATH>\n'
            '</IRETURNVALUE>\n',
            exp_result=[
                CIMInstanceName(
                    'CIM_Foo1',
                    namespace='foo',
                    host='woot.com',
                ),
                CIMInstanceName(
                    'CIM_Foo2',
                    namespace='foo',
                    host='woot.com',
                ),
            ],
        ),
        None, None, True
    ),

    # Testcases for OpenReferenceInstances
    (
        "IRETURNVALUE element for OpenReferenceInstances is missing",
        dict(
            operation='OpenReferenceInstances',
            xml_str='<DUMMY/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "IRETURNVALUE element for OpenReferenceInstances, with empty "
        "result set",
        dict(
            operation='OpenReferenceInstances',
            xml_str=''
            '<IRETURNVALUE NAME="OpenReferenceInstances">\n'
            '</IRETURNVALUE>\n',
            exp_result=[],
        ),
        None, None, True
    ),
    (
        "IRETURNVALUE element for OpenReferenceInstances, with one "
        "instance in result set",
        dict(
            operation='OpenReferenceInstances',
            xml_str=''
            '<IRETURNVALUE NAME="OpenReferenceInstances">\n'
            '  <VALUE.INSTANCEWITHPATH>\n'
            '    <INSTANCEPATH>\n'
            '      <NAMESPACEPATH>\n'
            '        <HOST>woot.com</HOST>\n'
            '        <LOCALNAMESPACEPATH>\n'
            '          <NAMESPACE NAME="foo"/>\n'
            '        </LOCALNAMESPACEPATH>\n'
            '      </NAMESPACEPATH>\n'
            '      <INSTANCENAME CLASSNAME="CIM_Foo"/>\n'
            '    </INSTANCEPATH>\n'
            '    <INSTANCE CLASSNAME="CIM_Foo"/>\n'
            '  </VALUE.INSTANCEWITHPATH>\n'
            '</IRETURNVALUE>\n',
            exp_result=[
                CIMInstance(
                    'CIM_Foo',
                    path=CIMInstanceName(
                        'CIM_Foo',
                        namespace='foo',
                        host='woot.com',
                    ),
                ),
            ],
        ),
        None, None, True
    ),
    (
        "IRETURNVALUE element for OpenReferenceInstances, with two "
        "instances in result set",
        dict(
            operation='OpenReferenceInstances',
            xml_str=''
            '<IRETURNVALUE NAME="OpenReferenceInstances">\n'
            '  <VALUE.INSTANCEWITHPATH>\n'
            '    <INSTANCEPATH>\n'
            '      <NAMESPACEPATH>\n'
            '        <HOST>woot.com</HOST>\n'
            '        <LOCALNAMESPACEPATH>\n'
            '          <NAMESPACE NAME="foo"/>\n'
            '        </LOCALNAMESPACEPATH>\n'
            '      </NAMESPACEPATH>\n'
            '      <INSTANCENAME CLASSNAME="CIM_Foo1"/>\n'
            '    </INSTANCEPATH>\n'
            '    <INSTANCE CLASSNAME="CIM_Foo1"/>\n'
            '  </VALUE.INSTANCEWITHPATH>\n'
            '  <VALUE.INSTANCEWITHPATH>\n'
            '    <INSTANCEPATH>\n'
            '      <NAMESPACEPATH>\n'
            '        <HOST>woot.com</HOST>\n'
            '        <LOCALNAMESPACEPATH>\n'
            '          <NAMESPACE NAME="foo"/>\n'
            '        </LOCALNAMESPACEPATH>\n'
            '      </NAMESPACEPATH>\n'
            '      <INSTANCENAME CLASSNAME="CIM_Foo2"/>\n'
            '    </INSTANCEPATH>\n'
            '    <INSTANCE CLASSNAME="CIM_Foo2"/>\n'
            '  </VALUE.INSTANCEWITHPATH>\n'
            '</IRETURNVALUE>\n',
            exp_result=[
                CIMInstance(
                    'CIM_Foo1',
                    path=CIMInstanceName(
                        'CIM_Foo1',
                        namespace='foo',
                        host='woot.com',
                    ),
                ),
                CIMInstance(
                    'CIM_Foo2',
                    path=CIMInstanceName(
                        'CIM_Foo2',
                        namespace='foo',
                        host='woot.com',
                    ),
                ),
            ],
        ),
        None, None, True
    ),

    # Testcases for OpenReferenceInstancePaths
    (
        "IRETURNVALUE element for OpenReferenceInstancePaths is missing",
        dict(
            operation='OpenReferenceInstancePaths',
            xml_str='<DUMMY/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "IRETURNVALUE element for OpenReferenceInstancePaths, with empty "
        "empty result set",
        dict(
            operation='OpenReferenceInstancePaths',
            xml_str=''
            '<IRETURNVALUE NAME="OpenReferenceInstancePaths">\n'
            '</IRETURNVALUE>\n',
            exp_result=[],
        ),
        None, None, True
    ),
    (
        "IRETURNVALUE element for OpenReferenceInstancePaths, with one "
        "instance path in result set",
        dict(
            operation='OpenReferenceInstancePaths',
            xml_str=''
            '<IRETURNVALUE NAME="OpenReferenceInstancePaths">\n'
            '  <INSTANCEPATH>\n'
            '    <NAMESPACEPATH>\n'
            '      <HOST>woot.com</HOST>\n'
            '      <LOCALNAMESPACEPATH>\n'
            '        <NAMESPACE NAME="foo"/>\n'
            '      </LOCALNAMESPACEPATH>\n'
            '    </NAMESPACEPATH>\n'
            '    <INSTANCENAME CLASSNAME="CIM_Foo"/>\n'
            '  </INSTANCEPATH>\n'
            '</IRETURNVALUE>\n',
            exp_result=[
                CIMInstanceName(
                    'CIM_Foo',
                    namespace='foo',
                    host='woot.com',
                ),
            ],
        ),
        None, None, True
    ),
    (
        "IRETURNVALUE element for OpenReferenceInstancePaths, with two "
        "instance paths in result set",
        dict(
            operation='OpenReferenceInstancePaths',
            xml_str=''
            '<IRETURNVALUE NAME="OpenReferenceInstancePaths">\n'
            '  <INSTANCEPATH>\n'
            '    <NAMESPACEPATH>\n'
            '      <HOST>woot.com</HOST>\n'
            '      <LOCALNAMESPACEPATH>\n'
            '        <NAMESPACE NAME="foo"/>\n'
            '      </LOCALNAMESPACEPATH>\n'
            '    </NAMESPACEPATH>\n'
            '    <INSTANCENAME CLASSNAME="CIM_Foo1"/>\n'
            '  </INSTANCEPATH>\n'
            '  <INSTANCEPATH>\n'
            '    <NAMESPACEPATH>\n'
            '      <HOST>woot.com</HOST>\n'
            '      <LOCALNAMESPACEPATH>\n'
            '        <NAMESPACE NAME="foo"/>\n'
            '      </LOCALNAMESPACEPATH>\n'
            '    </NAMESPACEPATH>\n'
            '    <INSTANCENAME CLASSNAME="CIM_Foo2"/>\n'
            '  </INSTANCEPATH>\n'
            '</IRETURNVALUE>\n',
            exp_result=[
                CIMInstanceName(
                    'CIM_Foo1',
                    namespace='foo',
                    host='woot.com',
                ),
                CIMInstanceName(
                    'CIM_Foo2',
                    namespace='foo',
                    host='woot.com',
                ),
            ],
        ),
        None, None, True
    ),

    # Testcases for OpenQueryInstances
    (
        "IRETURNVALUE element for OpenQueryInstances is missing",
        dict(
            operation='OpenQueryInstances',
            xml_str='<DUMMY/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "IRETURNVALUE element for OpenQueryInstances, with empty "
        "result set",
        dict(
            operation='OpenQueryInstances',
            xml_str=''
            '<IRETURNVALUE NAME="OpenQueryInstances">\n'
            '</IRETURNVALUE>\n',
            exp_result=[],
        ),
        None, None, True
    ),
    (
        "IRETURNVALUE element for OpenQueryInstances, with one "
        "instance in result set",
        dict(
            operation='OpenQueryInstances',
            xml_str=''
            '<IRETURNVALUE NAME="PullInstancesWithPath">\n'
            '  <INSTANCE CLASSNAME="CIM_Foo"/>\n'
            '</IRETURNVALUE>\n',
            exp_result=[
                CIMInstance('CIM_Foo'),
            ],
        ),
        None, None, True
    ),
    (
        "IRETURNVALUE element for OpenQueryInstances, with two "
        "instances in result set",
        dict(
            operation='OpenQueryInstances',
            xml_str=''
            '<IRETURNVALUE NAME="OpenQueryInstances">\n'
            '  <INSTANCE CLASSNAME="CIM_Foo1"/>\n'
            '  <INSTANCE CLASSNAME="CIM_Foo2"/>\n'
            '</IRETURNVALUE>\n',
            exp_result=[
                CIMInstance('CIM_Foo1'),
                CIMInstance('CIM_Foo2'),
            ],
        ),
        None, None, True
    ),

    # Testcases for PullInstancesWithPath
    (
        "IRETURNVALUE element for PullInstancesWithPath is missing",
        dict(
            operation='PullInstancesWithPath',
            xml_str='<DUMMY/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "IRETURNVALUE element for PullInstancesWithPath, with empty "
        "result set",
        dict(
            operation='PullInstancesWithPath',
            xml_str=''
            '<IRETURNVALUE NAME="PullInstancesWithPath">\n'
            '</IRETURNVALUE>\n',
            exp_result=[],
        ),
        None, None, True
    ),
    (
        "IRETURNVALUE element for PullInstancesWithPath, with one "
        "instance in result set",
        dict(
            operation='PullInstancesWithPath',
            xml_str=''
            '<IRETURNVALUE NAME="PullInstancesWithPath">\n'
            '  <VALUE.INSTANCEWITHPATH>\n'
            '    <INSTANCEPATH>\n'
            '      <NAMESPACEPATH>\n'
            '        <HOST>woot.com</HOST>\n'
            '        <LOCALNAMESPACEPATH>\n'
            '          <NAMESPACE NAME="foo"/>\n'
            '        </LOCALNAMESPACEPATH>\n'
            '      </NAMESPACEPATH>\n'
            '      <INSTANCENAME CLASSNAME="CIM_Foo"/>\n'
            '    </INSTANCEPATH>\n'
            '    <INSTANCE CLASSNAME="CIM_Foo"/>\n'
            '  </VALUE.INSTANCEWITHPATH>\n'
            '</IRETURNVALUE>\n',
            exp_result=[
                CIMInstance(
                    'CIM_Foo',
                    path=CIMInstanceName(
                        'CIM_Foo',
                        namespace='foo',
                        host='woot.com',
                    ),
                ),
            ],
        ),
        None, None, True
    ),
    (
        "IRETURNVALUE element for PullInstancesWithPath, with two "
        "instances in result set",
        dict(
            operation='PullInstancesWithPath',
            xml_str=''
            '<IRETURNVALUE NAME="PullInstancesWithPath">\n'
            '  <VALUE.INSTANCEWITHPATH>\n'
            '    <INSTANCEPATH>\n'
            '      <NAMESPACEPATH>\n'
            '        <HOST>woot.com</HOST>\n'
            '        <LOCALNAMESPACEPATH>\n'
            '          <NAMESPACE NAME="foo"/>\n'
            '        </LOCALNAMESPACEPATH>\n'
            '      </NAMESPACEPATH>\n'
            '      <INSTANCENAME CLASSNAME="CIM_Foo1"/>\n'
            '    </INSTANCEPATH>\n'
            '    <INSTANCE CLASSNAME="CIM_Foo1"/>\n'
            '  </VALUE.INSTANCEWITHPATH>\n'
            '  <VALUE.INSTANCEWITHPATH>\n'
            '    <INSTANCEPATH>\n'
            '      <NAMESPACEPATH>\n'
            '        <HOST>woot.com</HOST>\n'
            '        <LOCALNAMESPACEPATH>\n'
            '          <NAMESPACE NAME="foo"/>\n'
            '        </LOCALNAMESPACEPATH>\n'
            '      </NAMESPACEPATH>\n'
            '      <INSTANCENAME CLASSNAME="CIM_Foo2"/>\n'
            '    </INSTANCEPATH>\n'
            '    <INSTANCE CLASSNAME="CIM_Foo2"/>\n'
            '  </VALUE.INSTANCEWITHPATH>\n'
            '</IRETURNVALUE>\n',
            exp_result=[
                CIMInstance(
                    'CIM_Foo1',
                    path=CIMInstanceName(
                        'CIM_Foo1',
                        namespace='foo',
                        host='woot.com',
                    ),
                ),
                CIMInstance(
                    'CIM_Foo2',
                    path=CIMInstanceName(
                        'CIM_Foo2',
                        namespace='foo',
                        host='woot.com',
                    ),
                ),
            ],
        ),
        None, None, True
    ),

    # Testcases for PullInstancePaths
    (
        "IRETURNVALUE element for PullInstancePaths is missing",
        dict(
            operation='PullInstancePaths',
            xml_str='<DUMMY/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "IRETURNVALUE element for PullInstancePaths, with empty "
        "result set",
        dict(
            operation='PullInstancePaths',
            xml_str=''
            '<IRETURNVALUE NAME="PullInstancePaths">\n'
            '</IRETURNVALUE>\n',
            exp_result=[],
        ),
        None, None, True
    ),
    (
        "IRETURNVALUE element for PullInstancePaths, with one "
        "instance path in result set",
        dict(
            operation='PullInstancePaths',
            xml_str=''
            '<IRETURNVALUE NAME="PullInstancePaths">\n'
            '  <INSTANCEPATH>\n'
            '    <NAMESPACEPATH>\n'
            '      <HOST>woot.com</HOST>\n'
            '      <LOCALNAMESPACEPATH>\n'
            '        <NAMESPACE NAME="foo"/>\n'
            '      </LOCALNAMESPACEPATH>\n'
            '    </NAMESPACEPATH>\n'
            '    <INSTANCENAME CLASSNAME="CIM_Foo"/>\n'
            '  </INSTANCEPATH>\n'
            '</IRETURNVALUE>\n',
            exp_result=[
                CIMInstanceName(
                    'CIM_Foo',
                    namespace='foo',
                    host='woot.com',
                ),
            ],
        ),
        None, None, True
    ),
    (
        "IRETURNVALUE element for PullInstancePaths, with two "
        "instance paths in result set",
        dict(
            operation='PullInstancePaths',
            xml_str=''
            '<IRETURNVALUE NAME="PullInstancePaths">\n'
            '  <INSTANCEPATH>\n'
            '    <NAMESPACEPATH>\n'
            '      <HOST>woot.com</HOST>\n'
            '      <LOCALNAMESPACEPATH>\n'
            '        <NAMESPACE NAME="foo"/>\n'
            '      </LOCALNAMESPACEPATH>\n'
            '    </NAMESPACEPATH>\n'
            '    <INSTANCENAME CLASSNAME="CIM_Foo1"/>\n'
            '  </INSTANCEPATH>\n'
            '  <INSTANCEPATH>\n'
            '    <NAMESPACEPATH>\n'
            '      <HOST>woot.com</HOST>\n'
            '      <LOCALNAMESPACEPATH>\n'
            '        <NAMESPACE NAME="foo"/>\n'
            '      </LOCALNAMESPACEPATH>\n'
            '    </NAMESPACEPATH>\n'
            '    <INSTANCENAME CLASSNAME="CIM_Foo2"/>\n'
            '  </INSTANCEPATH>\n'
            '</IRETURNVALUE>\n',
            exp_result=[
                CIMInstanceName(
                    'CIM_Foo1',
                    namespace='foo',
                    host='woot.com',
                ),
                CIMInstanceName(
                    'CIM_Foo2',
                    namespace='foo',
                    host='woot.com',
                ),
            ],
        ),
        None, None, True
    ),

    # Testcases for PullInstances
    (
        "IRETURNVALUE element for PullInstances is missing",
        dict(
            operation='PullInstances',
            xml_str='<DUMMY/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "IRETURNVALUE element for PullInstances, with empty "
        "result set",
        dict(
            operation='PullInstances',
            xml_str=''
            '<IRETURNVALUE NAME="PullInstances">\n'
            '</IRETURNVALUE>\n',
            exp_result=[],
        ),
        None, None, True
    ),
    (
        "IRETURNVALUE element for PullInstances, with one "
        "instance in result set",
        dict(
            operation='PullInstances',
            xml_str=''
            '<IRETURNVALUE NAME="PullInstances">\n'
            '  <INSTANCE CLASSNAME="CIM_Foo"/>\n'
            '</IRETURNVALUE>\n',
            exp_result=[
                CIMInstance('CIM_Foo'),
            ],
        ),
        None, None, True
    ),
    (
        "IRETURNVALUE element for PullInstances, with two "
        "instances in result set",
        dict(
            operation='PullInstances',
            xml_str=''
            '<IRETURNVALUE NAME="PullInstances">\n'
            '  <INSTANCE CLASSNAME="CIM_Foo1"/>\n'
            '  <INSTANCE CLASSNAME="CIM_Foo2"/>\n'
            '</IRETURNVALUE>\n',
            exp_result=[
                CIMInstance('CIM_Foo1'),
                CIMInstance('CIM_Foo2'),
            ],
        ),
        None, None, True
    ),

    # Testcases for EnumerateClasses
    (
        "IRETURNVALUE element for EnumerateClasses is missing",
        dict(
            operation='EnumerateClasses',
            xml_str='<DUMMY/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "IRETURNVALUE element for EnumerateClasses, with empty "
        "result set",
        dict(
            operation='EnumerateClasses',
            xml_str=''
            '<IRETURNVALUE NAME="EnumerateClasses">\n'
            '</IRETURNVALUE>\n',
            exp_result=[],
        ),
        None, None, True
    ),
    (
        "IRETURNVALUE element for EnumerateClasses, with one "
        "class in result set",
        dict(
            operation='EnumerateClasses',
            xml_str=''
            '<IRETURNVALUE NAME="EnumerateClasses">\n'
            '  <CLASS NAME="CIM_Foo"/>\n'
            '</IRETURNVALUE>\n',
            exp_result=[
                CIMClass('CIM_Foo'),
            ],
        ),
        None, None, True
    ),
    (
        "IRETURNVALUE element for EnumerateClasses, with two "
        "classes in result set",
        dict(
            operation='EnumerateClasses',
            xml_str=''
            '<IRETURNVALUE NAME="EnumerateClasses">\n'
            '  <CLASS NAME="CIM_Foo1"/>\n'
            '  <CLASS NAME="CIM_Foo2"/>\n'
            '</IRETURNVALUE>\n',
            exp_result=[
                CIMClass('CIM_Foo1'),
                CIMClass('CIM_Foo2'),
            ],
        ),
        None, None, True
    ),

    # Testcases for EnumerateClassNames
    (
        "IRETURNVALUE element for EnumerateClassNames is missing",
        dict(
            operation='EnumerateClassNames',
            xml_str='<DUMMY/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "IRETURNVALUE element for EnumerateClassNames, with empty "
        "result set",
        dict(
            operation='EnumerateClassNames',
            xml_str=''
            '<IRETURNVALUE NAME="EnumerateClassNames">\n'
            '</IRETURNVALUE>\n',
            exp_result=[],
        ),
        None, None, True
    ),
    (
        "IRETURNVALUE element for EnumerateClassNames, with one "
        "class path in result set",
        dict(
            operation='EnumerateClassNames',
            xml_str=''
            '<IRETURNVALUE NAME="EnumerateClassNames">\n'
            '  <CLASSNAME NAME="CIM_Foo"/>\n'
            '</IRETURNVALUE>\n',
            exp_result=[
                CIMClassName('CIM_Foo'),
            ],
        ),
        None, None, True
    ),
    (
        "IRETURNVALUE element for EnumerateClassNames, with two "
        "class paths in result set",
        dict(
            operation='EnumerateClassNames',
            xml_str=''
            '<IRETURNVALUE NAME="EnumerateClassNames">\n'
            '  <CLASSNAME NAME="CIM_Foo1"/>\n'
            '  <CLASSNAME NAME="CIM_Foo2"/>\n'
            '</IRETURNVALUE>\n',
            exp_result=[
                CIMClassName('CIM_Foo1'),
                CIMClassName('CIM_Foo2'),
            ],
        ),
        None, None, True
    ),

    # Testcases for GetClass
    (
        "IRETURNVALUE element for GetClass is missing",
        dict(
            operation='GetClass',
            xml_str='<DUMMY/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "IRETURNVALUE element for GetClass, with class missing",
        dict(
            operation='GetClass',
            xml_str=''
            '<IRETURNVALUE NAME="GetClass">\n'
            '</IRETURNVALUE>\n',
            exp_result=[],
        ),
        CIMXMLParseError, None, True
    ),
    (
        "IRETURNVALUE element for GetClass, with class",
        dict(
            operation='GetClass',
            xml_str=''
            '<IRETURNVALUE NAME="GetClass">\n'
            '  <CLASS NAME="CIM_Foo"/>\n'
            '</IRETURNVALUE>\n',
            exp_result=CIMClass('CIM_Foo'),
        ),
        None, None, True
    ),

    # Testcases for EnumerateQualifiers
    (
        "IRETURNVALUE element for EnumerateQualifiers is missing",
        dict(
            operation='EnumerateQualifiers',
            xml_str='<DUMMY/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "IRETURNVALUE element for EnumerateQualifiers, with empty "
        "result set",
        dict(
            operation='EnumerateQualifiers',
            xml_str=''
            '<IRETURNVALUE NAME="EnumerateQualifiers">\n'
            '</IRETURNVALUE>\n',
            exp_result=[],
        ),
        None, None, True
    ),
    (
        "IRETURNVALUE element for EnumerateQualifiers, with one "
        "qualifier declaration in result set",
        dict(
            operation='EnumerateQualifiers',
            xml_str=''
            '<IRETURNVALUE NAME="EnumerateQualifiers">\n'
            '  <QUALIFIER.DECLARATION NAME="Qual" TYPE="string"/>\n'
            '</IRETURNVALUE>\n',
            exp_result=[
                CIMQualifierDeclaration(
                    'Qual', value=None, type='string',
                    **qualifier_declaration_default_attrs()
                ),
            ],
        ),
        None, None, True
    ),
    (
        "IRETURNVALUE element for EnumerateQualifiers, with two "
        "qualifier declarations in result set",
        dict(
            operation='EnumerateQualifiers',
            xml_str=''
            '<IRETURNVALUE NAME="EnumerateQualifiers">\n'
            '  <QUALIFIER.DECLARATION NAME="Qual1" TYPE="string"/>\n'
            '  <QUALIFIER.DECLARATION NAME="Qual2" TYPE="string"/>\n'
            '</IRETURNVALUE>\n',
            exp_result=[
                CIMQualifierDeclaration(
                    'Qual1', value=None, type='string',
                    **qualifier_declaration_default_attrs()
                ),
                CIMQualifierDeclaration(
                    'Qual2', value=None, type='string',
                    **qualifier_declaration_default_attrs()
                ),
            ],
        ),
        None, None, True
    ),

    # Testcases for GetQualifier
    (
        "IRETURNVALUE element for GetQualifier is missing",
        dict(
            operation='GetQualifier',
            xml_str='<DUMMY/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "IRETURNVALUE element for GetQualifier, with qualifier declaration "
        "missing",
        dict(
            operation='GetQualifier',
            xml_str=''
            '<IRETURNVALUE NAME="GetQualifier">\n'
            '</IRETURNVALUE>\n',
            exp_result=[],
        ),
        CIMXMLParseError, None, True
    ),
    (
        "IRETURNVALUE element for GetQualifier, with qualifier declaration",
        dict(
            operation='GetQualifier',
            xml_str=''
            '<IRETURNVALUE NAME="GetQualifier">\n'
            '  <QUALIFIER.DECLARATION NAME="Qual" TYPE="string"/>\n'
            '</IRETURNVALUE>\n',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=None, type='string',
                **qualifier_declaration_default_attrs()
            ),
        ),
        None, None, True
    ),

    # Testcases for operations that have no return value (void)
    (
        "Absent IRETURNVALUE element for ModifyInstance (void)",
        dict(
            operation='ModifyInstance',
            xml_str='<DUMMY/>',  # Some element needed other than IRETURNVALUE
            exp_result=None,
        ),
        None, None, True
    ),
    (
        "Absent IRETURNVALUE element for DeleteInstance (void)",
        dict(
            operation='DeleteInstance',
            xml_str='<DUMMY/>',  # Some element needed other than IRETURNVALUE
            exp_result=None,
        ),
        None, None, True
    ),
    (
        "Absent IRETURNVALUE element for CreateClass (void)",
        dict(
            operation='CreateClass',
            xml_str='<DUMMY/>',  # Some element needed other than IRETURNVALUE
            exp_result=None,
        ),
        None, None, True
    ),
    (
        "Absent IRETURNVALUE element for ModifyClass (void)",
        dict(
            operation='ModifyClass',
            xml_str='<DUMMY/>',  # Some element needed other than IRETURNVALUE
            exp_result=None,
        ),
        None, None, True
    ),
    (
        "Absent IRETURNVALUE element for DeleteClass (void)",
        dict(
            operation='DeleteClass',
            xml_str='<DUMMY/>',  # Some element needed other than IRETURNVALUE
            exp_result=None,
        ),
        None, None, True
    ),
    (
        "Absent IRETURNVALUE element for SetProperty (void)",
        dict(
            operation='SetProperty',
            xml_str='<DUMMY/>',  # Some element needed other than IRETURNVALUE
            exp_result=None,
        ),
        None, None, True
    ),
    (
        "Absent IRETURNVALUE element for SetQualifier (void)",
        dict(
            operation='SetQualifier',
            xml_str='<DUMMY/>',  # Some element needed other than IRETURNVALUE
            exp_result=None,
        ),
        None, None, True
    ),
    (
        "Absent IRETURNVALUE element for DeleteQualifier (void)",
        dict(
            operation='DeleteQualifier',
            xml_str='<DUMMY/>',  # Some element needed other than IRETURNVALUE
            exp_result=None,
        ),
        None, None, True
    ),
    (
        "Absent IRETURNVALUE element for CloseEnumeration (void)",
        dict(
            operation='CloseEnumeration',
            xml_str='<DUMMY/>',  # Some element needed other than IRETURNVALUE
            exp_result=None,
        ),
        None, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_OPTIONAL_IRETURNVALUE_ELEMENT)
@simplified_test_function
def test_optional_IRETURNVALUE_element(
        testcase, operation, xml_str, exp_result):
    """
    Test CIMXMLParser.optional_IRETURNVALUE_element().
    """

    parser = CIMXMLParser(xml_str)

    # Code to be tested
    result = parser.optional_IRETURNVALUE_element(operation)

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None, \
        "Expected exception {!r} has not been raised".\
        format(testcase.exp_exc_types)

    assert result == exp_result


TESTCASES_LIST_OF_OPERATION_PARAMVALUE_ELEMENTS = [

    # Error testcases independent of specific operations
    (
        "PARAMVALUE with missing required NAME attribute",
        dict(
            operation='OpenEnumerateInstances',
            skip_events=1,
            xml_str=''
            '<DUMMY_ROOT>\n'
            '  <PARAMVALUE>\n'
            '    <VALUE>bla-enum-context</VALUE>\n'
            '  </PARAMVALUE>\n'
            '  <PARAMVALUE NAME="EndOfSequence">\n'
            '    <VALUE>FALSE</VALUE>\n'
            '  </PARAMVALUE>\n'
            '</DUMMY_ROOT>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PARAMVALUE with invalid content text",
        dict(
            operation='OpenEnumerateInstances',
            skip_events=1,
            xml_str=''
            '<DUMMY_ROOT>\n'
            '  <PARAMVALUE NAME="EnumerationContext">\n'
            '    xxx\n'
            '    <VALUE>bla-enum-context</VALUE>\n'
            '  </PARAMVALUE>\n'
            '  <PARAMVALUE NAME="EndOfSequence">\n'
            '    <VALUE>FALSE</VALUE>\n'
            '  </PARAMVALUE>\n'
            '</DUMMY_ROOT>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PARAMVALUE with invalid trailing text",
        dict(
            operation='OpenEnumerateInstances',
            skip_events=1,
            xml_str=''
            '<DUMMY_ROOT>\n'
            '  <PARAMVALUE NAME="EnumerationContext">\n'
            '    <VALUE>bla-enum-context</VALUE>\n'
            '    xxx\n'
            '  </PARAMVALUE>\n'
            '  <PARAMVALUE NAME="EndOfSequence">\n'
            '    <VALUE>FALSE</VALUE>\n'
            '  </PARAMVALUE>\n'
            '</DUMMY_ROOT>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PARAMVALUE with invalid EmbeddedObject attribute",
        dict(
            operation='OpenQueryInstances',
            skip_events=1,
            xml_str=''
            '<DUMMY_ROOT>\n'
            '  <PARAMVALUE NAME="EnumerationContext" PARAMTYPE="string">\n'
            '    <VALUE>bla-enum-context</VALUE>\n'
            '  </PARAMVALUE>\n'
            '  <PARAMVALUE NAME="EndOfSequence" PARAMTYPE="boolean">\n'
            '    <VALUE>FALSE</VALUE>\n'
            '  </PARAMVALUE>\n'
            '  <PARAMVALUE NAME="QueryResultClass" EmbeddedObject="class">\n'
            '    <CLASS NAME="CIM_Foo"></CLASS>\n'
            '  </PARAMVALUE>\n'
            '</DUMMY_ROOT>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PARAMVALUE with invalid EMBEDDEDOBJECT attribute",
        dict(
            operation='OpenQueryInstances',
            skip_events=1,
            xml_str=''
            '<DUMMY_ROOT>\n'
            '  <PARAMVALUE NAME="EnumerationContext" PARAMTYPE="string">\n'
            '    <VALUE>bla-enum-context</VALUE>\n'
            '  </PARAMVALUE>\n'
            '  <PARAMVALUE NAME="EndOfSequence" PARAMTYPE="boolean">\n'
            '    <VALUE>FALSE</VALUE>\n'
            '  </PARAMVALUE>\n'
            '  <PARAMVALUE NAME="QueryResultClass" EMBEDDEDOBJECT="class">\n'
            '    <CLASS NAME="CIM_Foo"></CLASS>\n'
            '  </PARAMVALUE>\n'
            '</DUMMY_ROOT>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),

    # Testcases for OpenEnumerateInstances
    (
        "PARAMVALUE elements for OpenEnumerateInstances, "
        "without optional attributes",
        dict(
            operation='OpenEnumerateInstances',
            skip_events=1,
            xml_str=''
            '<DUMMY_ROOT>\n'
            '  <PARAMVALUE NAME="EnumerationContext">\n'
            '    <VALUE>bla-enum-context</VALUE>\n'
            '  </PARAMVALUE>\n'
            '  <PARAMVALUE NAME="EndOfSequence">\n'
            '    <VALUE>FALSE</VALUE>\n'
            '  </PARAMVALUE>\n'
            '</DUMMY_ROOT>\n',
            exp_result=dict(
                EnumerationContext=u'bla-enum-context',
                EndOfSequence=False,
            ),
        ),
        None, None, True
    ),
    (
        "PARAMVALUE elements for OpenEnumerateInstances, "
        "with optional attributes",
        dict(
            operation='OpenEnumerateInstances',
            skip_events=1,
            xml_str=''
            '<DUMMY_ROOT>\n'
            '  <PARAMVALUE NAME="EnumerationContext" PARAMTYPE="string">\n'
            '    <VALUE>bla-enum-context</VALUE>\n'
            '  </PARAMVALUE>\n'
            '  <PARAMVALUE NAME="EndOfSequence" PARAMTYPE="boolean">\n'
            '    <VALUE>FALSE</VALUE>\n'
            '  </PARAMVALUE>\n'
            '</DUMMY_ROOT>\n',
            exp_result=dict(
                EnumerationContext=u'bla-enum-context',
                EndOfSequence=False,
            ),
        ),
        None, None, True
    ),
    (
        "PARAMVALUE elements for OpenEnumerateInstances, "
        "with switched order of parameters",
        dict(
            operation='OpenEnumerateInstances',
            skip_events=1,
            xml_str=''
            '<DUMMY_ROOT>\n'
            '  <PARAMVALUE NAME="EndOfSequence" PARAMTYPE="boolean">\n'
            '    <VALUE>FALSE</VALUE>\n'
            '  </PARAMVALUE>\n'
            '  <PARAMVALUE NAME="EnumerationContext" PARAMTYPE="string">\n'
            '    <VALUE>bla-enum-context</VALUE>\n'
            '  </PARAMVALUE>\n'
            '</DUMMY_ROOT>\n',
            exp_result=dict(
                EnumerationContext=u'bla-enum-context',
                EndOfSequence=False,
            ),
        ),
        None, None, True
    ),
    (
        "PARAMVALUE elements for OpenEnumerateInstances, "
        "with missing required parameter",
        dict(
            operation='OpenEnumerateInstances',
            skip_events=1,
            xml_str=''
            '<DUMMY_ROOT>\n'
            '  <PARAMVALUE NAME="EndOfSequence" PARAMTYPE="boolean">\n'
            '    <VALUE>FALSE</VALUE>\n'
            '  </PARAMVALUE>\n'
            '</DUMMY_ROOT>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PARAMVALUE elements for OpenEnumerateInstances, "
        "with invalid parameter names",
        dict(
            operation='OpenEnumerateInstances',
            skip_events=1,
            xml_str=''
            '<DUMMY_ROOT>\n'
            '  <PARAMVALUE NAME="EnumerationContextXXX" PARAMTYPE="string">\n'
            '    <VALUE>bla-enum-context</VALUE>\n'
            '  </PARAMVALUE>\n'
            '  <PARAMVALUE NAME="EndOfSequenceXXX" PARAMTYPE="boolean">\n'
            '    <VALUE>FALSE</VALUE>\n'
            '  </PARAMVALUE>\n'
            '</DUMMY_ROOT>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PARAMVALUE elements for OpenEnumerateInstances, "
        "with invalid parameter types",
        dict(
            operation='OpenEnumerateInstances',
            skip_events=1,
            xml_str=''
            '<DUMMY_ROOT>\n'
            '  <PARAMVALUE NAME="EnumerationContext" PARAMTYPE="boolean">\n'
            '    <VALUE>bla-enum-context</VALUE>\n'
            '  </PARAMVALUE>\n'
            '  <PARAMVALUE NAME="EndOfSequence" PARAMTYPE="string">\n'
            '    <VALUE>FALSE</VALUE>\n'
            '  </PARAMVALUE>\n'
            '</DUMMY_ROOT>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),

    # Testcases for OpenEnumerateInstancePaths
    (
        "PARAMVALUE elements for OpenEnumerateInstancePaths, "
        "without optional attributes",
        dict(
            operation='OpenEnumerateInstancePaths',
            skip_events=1,
            xml_str=''
            '<DUMMY_ROOT>\n'
            '  <PARAMVALUE NAME="EnumerationContext">\n'
            '    <VALUE>bla-enum-context</VALUE>\n'
            '  </PARAMVALUE>\n'
            '  <PARAMVALUE NAME="EndOfSequence">\n'
            '    <VALUE>FALSE</VALUE>\n'
            '  </PARAMVALUE>\n'
            '</DUMMY_ROOT>\n',
            exp_result=dict(
                EnumerationContext=u'bla-enum-context',
                EndOfSequence=False,
            ),
        ),
        None, None, True
    ),
    (
        "PARAMVALUE elements for OpenEnumerateInstancePaths, "
        "with optional attributes",
        dict(
            operation='OpenEnumerateInstancePaths',
            skip_events=1,
            xml_str=''
            '<DUMMY_ROOT>\n'
            '  <PARAMVALUE NAME="EnumerationContext" PARAMTYPE="string">\n'
            '    <VALUE>bla-enum-context</VALUE>\n'
            '  </PARAMVALUE>\n'
            '  <PARAMVALUE NAME="EndOfSequence" PARAMTYPE="boolean">\n'
            '    <VALUE>FALSE</VALUE>\n'
            '  </PARAMVALUE>\n'
            '</DUMMY_ROOT>\n',
            exp_result=dict(
                EnumerationContext=u'bla-enum-context',
                EndOfSequence=False,
            ),
        ),
        None, None, True
    ),
    (
        "PARAMVALUE elements for OpenEnumerateInstancePaths, "
        "with switched order of parameters",
        dict(
            operation='OpenEnumerateInstancePaths',
            skip_events=1,
            xml_str=''
            '<DUMMY_ROOT>\n'
            '  <PARAMVALUE NAME="EndOfSequence" PARAMTYPE="boolean">\n'
            '    <VALUE>FALSE</VALUE>\n'
            '  </PARAMVALUE>\n'
            '  <PARAMVALUE NAME="EnumerationContext" PARAMTYPE="string">\n'
            '    <VALUE>bla-enum-context</VALUE>\n'
            '  </PARAMVALUE>\n'
            '</DUMMY_ROOT>\n',
            exp_result=dict(
                EnumerationContext=u'bla-enum-context',
                EndOfSequence=False,
            ),
        ),
        None, None, True
    ),
    (
        "PARAMVALUE elements for OpenEnumerateInstancePaths, "
        "with missing required parameter",
        dict(
            operation='OpenEnumerateInstancePaths',
            skip_events=1,
            xml_str=''
            '<DUMMY_ROOT>\n'
            '  <PARAMVALUE NAME="EndOfSequence" PARAMTYPE="boolean">\n'
            '    <VALUE>FALSE</VALUE>\n'
            '  </PARAMVALUE>\n'
            '</DUMMY_ROOT>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PARAMVALUE elements for OpenEnumerateInstancePaths, "
        "with invalid parameter names",
        dict(
            operation='OpenEnumerateInstancePaths',
            skip_events=1,
            xml_str=''
            '<DUMMY_ROOT>\n'
            '  <PARAMVALUE NAME="EnumerationContextXXX" PARAMTYPE="string">\n'
            '    <VALUE>bla-enum-context</VALUE>\n'
            '  </PARAMVALUE>\n'
            '  <PARAMVALUE NAME="EndOfSequenceXXX" PARAMTYPE="boolean">\n'
            '    <VALUE>FALSE</VALUE>\n'
            '  </PARAMVALUE>\n'
            '</DUMMY_ROOT>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PARAMVALUE elements for OpenEnumerateInstancePaths, "
        "with invalid parameter types",
        dict(
            operation='OpenEnumerateInstancePaths',
            skip_events=1,
            xml_str=''
            '<DUMMY_ROOT>\n'
            '  <PARAMVALUE NAME="EnumerationContext" PARAMTYPE="boolean">\n'
            '    <VALUE>bla-enum-context</VALUE>\n'
            '  </PARAMVALUE>\n'
            '  <PARAMVALUE NAME="EndOfSequence" PARAMTYPE="string">\n'
            '    <VALUE>FALSE</VALUE>\n'
            '  </PARAMVALUE>\n'
            '</DUMMY_ROOT>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),

    # Testcases for OpenAssociatorInstances
    (
        "PARAMVALUE elements for OpenAssociatorInstances, "
        "without optional attributes",
        dict(
            operation='OpenAssociatorInstances',
            skip_events=1,
            xml_str=''
            '<DUMMY_ROOT>\n'
            '  <PARAMVALUE NAME="EnumerationContext">\n'
            '    <VALUE>bla-enum-context</VALUE>\n'
            '  </PARAMVALUE>\n'
            '  <PARAMVALUE NAME="EndOfSequence">\n'
            '    <VALUE>FALSE</VALUE>\n'
            '  </PARAMVALUE>\n'
            '</DUMMY_ROOT>\n',
            exp_result=dict(
                EnumerationContext=u'bla-enum-context',
                EndOfSequence=False,
            ),
        ),
        None, None, True
    ),
    (
        "PARAMVALUE elements for OpenAssociatorInstances, "
        "with optional attributes",
        dict(
            operation='OpenAssociatorInstances',
            skip_events=1,
            xml_str=''
            '<DUMMY_ROOT>\n'
            '  <PARAMVALUE NAME="EnumerationContext" PARAMTYPE="string">\n'
            '    <VALUE>bla-enum-context</VALUE>\n'
            '  </PARAMVALUE>\n'
            '  <PARAMVALUE NAME="EndOfSequence" PARAMTYPE="boolean">\n'
            '    <VALUE>FALSE</VALUE>\n'
            '  </PARAMVALUE>\n'
            '</DUMMY_ROOT>\n',
            exp_result=dict(
                EnumerationContext=u'bla-enum-context',
                EndOfSequence=False,
            ),
        ),
        None, None, True
    ),
    (
        "PARAMVALUE elements for OpenAssociatorInstances, "
        "with switched order of parameters",
        dict(
            operation='OpenAssociatorInstances',
            skip_events=1,
            xml_str=''
            '<DUMMY_ROOT>\n'
            '  <PARAMVALUE NAME="EndOfSequence" PARAMTYPE="boolean">\n'
            '    <VALUE>FALSE</VALUE>\n'
            '  </PARAMVALUE>\n'
            '  <PARAMVALUE NAME="EnumerationContext" PARAMTYPE="string">\n'
            '    <VALUE>bla-enum-context</VALUE>\n'
            '  </PARAMVALUE>\n'
            '</DUMMY_ROOT>\n',
            exp_result=dict(
                EnumerationContext=u'bla-enum-context',
                EndOfSequence=False,
            ),
        ),
        None, None, True
    ),
    (
        "PARAMVALUE elements for OpenAssociatorInstances, "
        "with missing required parameter",
        dict(
            operation='OpenAssociatorInstances',
            skip_events=1,
            xml_str=''
            '<DUMMY_ROOT>\n'
            '  <PARAMVALUE NAME="EndOfSequence" PARAMTYPE="boolean">\n'
            '    <VALUE>FALSE</VALUE>\n'
            '  </PARAMVALUE>\n'
            '</DUMMY_ROOT>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PARAMVALUE elements for OpenAssociatorInstances, "
        "with invalid parameter names",
        dict(
            operation='OpenAssociatorInstances',
            skip_events=1,
            xml_str=''
            '<DUMMY_ROOT>\n'
            '  <PARAMVALUE NAME="EnumerationContextXXX" PARAMTYPE="string">\n'
            '    <VALUE>bla-enum-context</VALUE>\n'
            '  </PARAMVALUE>\n'
            '  <PARAMVALUE NAME="EndOfSequenceXXX" PARAMTYPE="boolean">\n'
            '    <VALUE>FALSE</VALUE>\n'
            '  </PARAMVALUE>\n'
            '</DUMMY_ROOT>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PARAMVALUE elements for OpenAssociatorInstances, "
        "with invalid parameter types",
        dict(
            operation='OpenAssociatorInstances',
            skip_events=1,
            xml_str=''
            '<DUMMY_ROOT>\n'
            '  <PARAMVALUE NAME="EnumerationContext" PARAMTYPE="boolean">\n'
            '    <VALUE>bla-enum-context</VALUE>\n'
            '  </PARAMVALUE>\n'
            '  <PARAMVALUE NAME="EndOfSequence" PARAMTYPE="string">\n'
            '    <VALUE>FALSE</VALUE>\n'
            '  </PARAMVALUE>\n'
            '</DUMMY_ROOT>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),

    # Testcases for OpenAssociatorInstancePaths
    (
        "PARAMVALUE elements for OpenAssociatorInstancePaths, "
        "without optional attributes",
        dict(
            operation='OpenAssociatorInstancePaths',
            skip_events=1,
            xml_str=''
            '<DUMMY_ROOT>\n'
            '  <PARAMVALUE NAME="EnumerationContext">\n'
            '    <VALUE>bla-enum-context</VALUE>\n'
            '  </PARAMVALUE>\n'
            '  <PARAMVALUE NAME="EndOfSequence">\n'
            '    <VALUE>FALSE</VALUE>\n'
            '  </PARAMVALUE>\n'
            '</DUMMY_ROOT>\n',
            exp_result=dict(
                EnumerationContext=u'bla-enum-context',
                EndOfSequence=False,
            ),
        ),
        None, None, True
    ),
    (
        "PARAMVALUE elements for OpenAssociatorInstancePaths, "
        "with optional attributes",
        dict(
            operation='OpenAssociatorInstancePaths',
            skip_events=1,
            xml_str=''
            '<DUMMY_ROOT>\n'
            '  <PARAMVALUE NAME="EnumerationContext" PARAMTYPE="string">\n'
            '    <VALUE>bla-enum-context</VALUE>\n'
            '  </PARAMVALUE>\n'
            '  <PARAMVALUE NAME="EndOfSequence" PARAMTYPE="boolean">\n'
            '    <VALUE>FALSE</VALUE>\n'
            '  </PARAMVALUE>\n'
            '</DUMMY_ROOT>\n',
            exp_result=dict(
                EnumerationContext=u'bla-enum-context',
                EndOfSequence=False,
            ),
        ),
        None, None, True
    ),
    (
        "PARAMVALUE elements for OpenAssociatorInstancePaths, "
        "with switched order of parameters",
        dict(
            operation='OpenAssociatorInstancePaths',
            skip_events=1,
            xml_str=''
            '<DUMMY_ROOT>\n'
            '  <PARAMVALUE NAME="EndOfSequence" PARAMTYPE="boolean">\n'
            '    <VALUE>FALSE</VALUE>\n'
            '  </PARAMVALUE>\n'
            '  <PARAMVALUE NAME="EnumerationContext" PARAMTYPE="string">\n'
            '    <VALUE>bla-enum-context</VALUE>\n'
            '  </PARAMVALUE>\n'
            '</DUMMY_ROOT>\n',
            exp_result=dict(
                EnumerationContext=u'bla-enum-context',
                EndOfSequence=False,
            ),
        ),
        None, None, True
    ),
    (
        "PARAMVALUE elements for OpenAssociatorInstancePaths, "
        "with missing required parameter",
        dict(
            operation='OpenAssociatorInstancePaths',
            skip_events=1,
            xml_str=''
            '<DUMMY_ROOT>\n'
            '  <PARAMVALUE NAME="EndOfSequence" PARAMTYPE="boolean">\n'
            '    <VALUE>FALSE</VALUE>\n'
            '  </PARAMVALUE>\n'
            '</DUMMY_ROOT>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PARAMVALUE elements for OpenAssociatorInstancePaths, "
        "with invalid parameter names",
        dict(
            operation='OpenAssociatorInstancePaths',
            skip_events=1,
            xml_str=''
            '<DUMMY_ROOT>\n'
            '  <PARAMVALUE NAME="EnumerationContextXXX" PARAMTYPE="string">\n'
            '    <VALUE>bla-enum-context</VALUE>\n'
            '  </PARAMVALUE>\n'
            '  <PARAMVALUE NAME="EndOfSequenceXXX" PARAMTYPE="boolean">\n'
            '    <VALUE>FALSE</VALUE>\n'
            '  </PARAMVALUE>\n'
            '</DUMMY_ROOT>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PARAMVALUE elements for OpenAssociatorInstancePaths, "
        "with invalid parameter types",
        dict(
            operation='OpenAssociatorInstancePaths',
            skip_events=1,
            xml_str=''
            '<DUMMY_ROOT>\n'
            '  <PARAMVALUE NAME="EnumerationContext" PARAMTYPE="boolean">\n'
            '    <VALUE>bla-enum-context</VALUE>\n'
            '  </PARAMVALUE>\n'
            '  <PARAMVALUE NAME="EndOfSequence" PARAMTYPE="string">\n'
            '    <VALUE>FALSE</VALUE>\n'
            '  </PARAMVALUE>\n'
            '</DUMMY_ROOT>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),

    # Testcases for OpenReferenceInstances
    (
        "PARAMVALUE elements for OpenReferenceInstances, "
        "without optional attributes",
        dict(
            operation='OpenReferenceInstances',
            skip_events=1,
            xml_str=''
            '<DUMMY_ROOT>\n'
            '  <PARAMVALUE NAME="EnumerationContext">\n'
            '    <VALUE>bla-enum-context</VALUE>\n'
            '  </PARAMVALUE>\n'
            '  <PARAMVALUE NAME="EndOfSequence">\n'
            '    <VALUE>FALSE</VALUE>\n'
            '  </PARAMVALUE>\n'
            '</DUMMY_ROOT>\n',
            exp_result=dict(
                EnumerationContext=u'bla-enum-context',
                EndOfSequence=False,
            ),
        ),
        None, None, True
    ),
    (
        "PARAMVALUE elements for OpenReferenceInstances, "
        "with optional attributes",
        dict(
            operation='OpenReferenceInstances',
            skip_events=1,
            xml_str=''
            '<DUMMY_ROOT>\n'
            '  <PARAMVALUE NAME="EnumerationContext" PARAMTYPE="string">\n'
            '    <VALUE>bla-enum-context</VALUE>\n'
            '  </PARAMVALUE>\n'
            '  <PARAMVALUE NAME="EndOfSequence" PARAMTYPE="boolean">\n'
            '    <VALUE>FALSE</VALUE>\n'
            '  </PARAMVALUE>\n'
            '</DUMMY_ROOT>\n',
            exp_result=dict(
                EnumerationContext=u'bla-enum-context',
                EndOfSequence=False,
            ),
        ),
        None, None, True
    ),
    (
        "PARAMVALUE elements for OpenReferenceInstances, "
        "with switched order of parameters",
        dict(
            operation='OpenReferenceInstances',
            skip_events=1,
            xml_str=''
            '<DUMMY_ROOT>\n'
            '  <PARAMVALUE NAME="EndOfSequence" PARAMTYPE="boolean">\n'
            '    <VALUE>FALSE</VALUE>\n'
            '  </PARAMVALUE>\n'
            '  <PARAMVALUE NAME="EnumerationContext" PARAMTYPE="string">\n'
            '    <VALUE>bla-enum-context</VALUE>\n'
            '  </PARAMVALUE>\n'
            '</DUMMY_ROOT>\n',
            exp_result=dict(
                EnumerationContext=u'bla-enum-context',
                EndOfSequence=False,
            ),
        ),
        None, None, True
    ),
    (
        "PARAMVALUE elements for OpenReferenceInstances, "
        "with missing required parameter",
        dict(
            operation='OpenReferenceInstances',
            skip_events=1,
            xml_str=''
            '<DUMMY_ROOT>\n'
            '  <PARAMVALUE NAME="EndOfSequence" PARAMTYPE="boolean">\n'
            '    <VALUE>FALSE</VALUE>\n'
            '  </PARAMVALUE>\n'
            '</DUMMY_ROOT>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PARAMVALUE elements for OpenReferenceInstances, "
        "with invalid parameter names",
        dict(
            operation='OpenReferenceInstances',
            skip_events=1,
            xml_str=''
            '<DUMMY_ROOT>\n'
            '  <PARAMVALUE NAME="EnumerationContextXXX" PARAMTYPE="string">\n'
            '    <VALUE>bla-enum-context</VALUE>\n'
            '  </PARAMVALUE>\n'
            '  <PARAMVALUE NAME="EndOfSequenceXXX" PARAMTYPE="boolean">\n'
            '    <VALUE>FALSE</VALUE>\n'
            '  </PARAMVALUE>\n'
            '</DUMMY_ROOT>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PARAMVALUE elements for OpenReferenceInstances, "
        "with invalid parameter types",
        dict(
            operation='OpenReferenceInstances',
            skip_events=1,
            xml_str=''
            '<DUMMY_ROOT>\n'
            '  <PARAMVALUE NAME="EnumerationContext" PARAMTYPE="boolean">\n'
            '    <VALUE>bla-enum-context</VALUE>\n'
            '  </PARAMVALUE>\n'
            '  <PARAMVALUE NAME="EndOfSequence" PARAMTYPE="string">\n'
            '    <VALUE>FALSE</VALUE>\n'
            '  </PARAMVALUE>\n'
            '</DUMMY_ROOT>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),

    # Testcases for OpenReferenceInstancePaths
    (
        "PARAMVALUE elements for OpenReferenceInstancePaths, "
        "without optional attributes",
        dict(
            operation='OpenReferenceInstancePaths',
            skip_events=1,
            xml_str=''
            '<DUMMY_ROOT>\n'
            '  <PARAMVALUE NAME="EnumerationContext">\n'
            '    <VALUE>bla-enum-context</VALUE>\n'
            '  </PARAMVALUE>\n'
            '  <PARAMVALUE NAME="EndOfSequence">\n'
            '    <VALUE>FALSE</VALUE>\n'
            '  </PARAMVALUE>\n'
            '</DUMMY_ROOT>\n',
            exp_result=dict(
                EnumerationContext=u'bla-enum-context',
                EndOfSequence=False,
            ),
        ),
        None, None, True
    ),
    (
        "PARAMVALUE elements for OpenReferenceInstancePaths, "
        "with optional attributes",
        dict(
            operation='OpenReferenceInstancePaths',
            skip_events=1,
            xml_str=''
            '<DUMMY_ROOT>\n'
            '  <PARAMVALUE NAME="EnumerationContext" PARAMTYPE="string">\n'
            '    <VALUE>bla-enum-context</VALUE>\n'
            '  </PARAMVALUE>\n'
            '  <PARAMVALUE NAME="EndOfSequence" PARAMTYPE="boolean">\n'
            '    <VALUE>FALSE</VALUE>\n'
            '  </PARAMVALUE>\n'
            '</DUMMY_ROOT>\n',
            exp_result=dict(
                EnumerationContext=u'bla-enum-context',
                EndOfSequence=False,
            ),
        ),
        None, None, True
    ),
    (
        "PARAMVALUE elements for OpenReferenceInstancePaths, "
        "with switched order of parameters",
        dict(
            operation='OpenReferenceInstancePaths',
            skip_events=1,
            xml_str=''
            '<DUMMY_ROOT>\n'
            '  <PARAMVALUE NAME="EndOfSequence" PARAMTYPE="boolean">\n'
            '    <VALUE>FALSE</VALUE>\n'
            '  </PARAMVALUE>\n'
            '  <PARAMVALUE NAME="EnumerationContext" PARAMTYPE="string">\n'
            '    <VALUE>bla-enum-context</VALUE>\n'
            '  </PARAMVALUE>\n'
            '</DUMMY_ROOT>\n',
            exp_result=dict(
                EnumerationContext=u'bla-enum-context',
                EndOfSequence=False,
            ),
        ),
        None, None, True
    ),
    (
        "PARAMVALUE elements for OpenReferenceInstancePaths, "
        "with missing required parameter",
        dict(
            operation='OpenReferenceInstancePaths',
            skip_events=1,
            xml_str=''
            '<DUMMY_ROOT>\n'
            '  <PARAMVALUE NAME="EndOfSequence" PARAMTYPE="boolean">\n'
            '    <VALUE>FALSE</VALUE>\n'
            '  </PARAMVALUE>\n'
            '</DUMMY_ROOT>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PARAMVALUE elements for OpenReferenceInstancePaths, "
        "with invalid parameter names",
        dict(
            operation='OpenReferenceInstancePaths',
            skip_events=1,
            xml_str=''
            '<DUMMY_ROOT>\n'
            '  <PARAMVALUE NAME="EnumerationContextXXX" PARAMTYPE="string">\n'
            '    <VALUE>bla-enum-context</VALUE>\n'
            '  </PARAMVALUE>\n'
            '  <PARAMVALUE NAME="EndOfSequenceXXX" PARAMTYPE="boolean">\n'
            '    <VALUE>FALSE</VALUE>\n'
            '  </PARAMVALUE>\n'
            '</DUMMY_ROOT>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PARAMVALUE elements for OpenReferenceInstancePaths, "
        "with invalid parameter types",
        dict(
            operation='OpenReferenceInstancePaths',
            skip_events=1,
            xml_str=''
            '<DUMMY_ROOT>\n'
            '  <PARAMVALUE NAME="EnumerationContext" PARAMTYPE="boolean">\n'
            '    <VALUE>bla-enum-context</VALUE>\n'
            '  </PARAMVALUE>\n'
            '  <PARAMVALUE NAME="EndOfSequence" PARAMTYPE="string">\n'
            '    <VALUE>FALSE</VALUE>\n'
            '  </PARAMVALUE>\n'
            '</DUMMY_ROOT>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),

    # Testcases for OpenQueryInstances
    (
        "PARAMVALUE elements for OpenQueryInstances, "
        "without optional parameters and without optional attributes",
        dict(
            operation='OpenQueryInstances',
            skip_events=1,
            xml_str=''
            '<DUMMY_ROOT>\n'
            '  <PARAMVALUE NAME="EnumerationContext">\n'
            '    <VALUE>bla-enum-context</VALUE>\n'
            '  </PARAMVALUE>\n'
            '  <PARAMVALUE NAME="EndOfSequence">\n'
            '    <VALUE>FALSE</VALUE>\n'
            '  </PARAMVALUE>\n'
            '</DUMMY_ROOT>\n',
            exp_result=dict(
                EnumerationContext=u'bla-enum-context',
                EndOfSequence=False,
            ),
        ),
        None, None, True
    ),
    (
        "PARAMVALUE elements for OpenQueryInstances, "
        "with optional parameters and with optional attributes",
        dict(
            operation='OpenQueryInstances',
            skip_events=1,
            xml_str=''
            '<DUMMY_ROOT>\n'
            '  <PARAMVALUE NAME="EnumerationContext" PARAMTYPE="string">\n'
            '    <VALUE>bla-enum-context</VALUE>\n'
            '  </PARAMVALUE>\n'
            '  <PARAMVALUE NAME="EndOfSequence" PARAMTYPE="boolean">\n'
            '    <VALUE>FALSE</VALUE>\n'
            '  </PARAMVALUE>\n'
            '  <PARAMVALUE NAME="QueryResultClass">\n'
            '    <CLASS NAME="CIM_Foo"></CLASS>\n'
            '  </PARAMVALUE>\n'
            '</DUMMY_ROOT>\n',
            exp_result=dict(
                EnumerationContext=u'bla-enum-context',
                EndOfSequence=False,
                QueryResultClass=CIMClass('CIM_Foo'),
            ),
        ),
        None, None, True
    ),
    (
        "PARAMVALUE elements for OpenQueryInstances, "
        "with switched order of parameters",
        dict(
            operation='OpenQueryInstances',
            skip_events=1,
            xml_str=''
            '<DUMMY_ROOT>\n'
            '  <PARAMVALUE NAME="EndOfSequence" PARAMTYPE="boolean">\n'
            '    <VALUE>FALSE</VALUE>\n'
            '  </PARAMVALUE>\n'
            '  <PARAMVALUE NAME="QueryResultClass">\n'
            '    <CLASS NAME="CIM_Foo"></CLASS>\n'
            '  </PARAMVALUE>\n'
            '  <PARAMVALUE NAME="EnumerationContext" PARAMTYPE="string">\n'
            '    <VALUE>bla-enum-context</VALUE>\n'
            '  </PARAMVALUE>\n'
            '</DUMMY_ROOT>\n',
            exp_result=dict(
                EnumerationContext=u'bla-enum-context',
                EndOfSequence=False,
                QueryResultClass=CIMClass('CIM_Foo'),
            ),
        ),
        None, None, True
    ),
    (
        "PARAMVALUE elements for OpenQueryInstances, "
        "with missing required parameter",
        dict(
            operation='OpenQueryInstances',
            skip_events=1,
            xml_str=''
            '<DUMMY_ROOT>\n'
            '  <PARAMVALUE NAME="EndOfSequence" PARAMTYPE="boolean">\n'
            '    <VALUE>FALSE</VALUE>\n'
            '  </PARAMVALUE>\n'
            '</DUMMY_ROOT>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PARAMVALUE elements for OpenQueryInstances, "
        "with invalid parameter names",
        dict(
            operation='OpenQueryInstances',
            skip_events=1,
            xml_str=''
            '<DUMMY_ROOT>\n'
            '  <PARAMVALUE NAME="EnumerationContextXXX" PARAMTYPE="string">\n'
            '    <VALUE>bla-enum-context</VALUE>\n'
            '  </PARAMVALUE>\n'
            '  <PARAMVALUE NAME="EndOfSequenceXXX" PARAMTYPE="boolean">\n'
            '    <VALUE>FALSE</VALUE>\n'
            '  </PARAMVALUE>\n'
            '  <PARAMVALUE NAME="QueryResultClassXXX">\n'
            '    <CLASS NAME="CIM_Foo"></CLASS>\n'
            '  </PARAMVALUE>\n'
            '</DUMMY_ROOT>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PARAMVALUE elements for OpenQueryInstances, "
        "with invalid parameter types",
        dict(
            operation='OpenQueryInstances',
            skip_events=1,
            xml_str=''
            '<DUMMY_ROOT>\n'
            '  <PARAMVALUE NAME="EnumerationContext" PARAMTYPE="boolean">\n'
            '    <VALUE>bla-enum-context</VALUE>\n'
            '  </PARAMVALUE>\n'
            '  <PARAMVALUE NAME="EndOfSequence" PARAMTYPE="string">\n'
            '    <VALUE>FALSE</VALUE>\n'
            '  </PARAMVALUE>\n'
            '  <PARAMVALUE NAME="QueryResultClass">\n'
            '    <CLASS NAME="CIM_Foo"></CLASS>\n'
            '  </PARAMVALUE>\n'
            '</DUMMY_ROOT>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PARAMVALUE elements for OpenQueryInstances, "
        "with invalid QueryResultClass parameter child element",
        dict(
            operation='OpenQueryInstances',
            skip_events=1,
            xml_str=''
            '<DUMMY_ROOT>\n'
            '  <PARAMVALUE NAME="EnumerationContext" PARAMTYPE="string">\n'
            '    <VALUE>bla-enum-context</VALUE>\n'
            '  </PARAMVALUE>\n'
            '  <PARAMVALUE NAME="EndOfSequence" PARAMTYPE="boolean">\n'
            '    <VALUE>FALSE</VALUE>\n'
            '  </PARAMVALUE>\n'
            '  <PARAMVALUE NAME="QueryResultClass">\n'
            '    <INSTANCE NAME="CIM_Foo"></INSTANCE>\n'
            '  </PARAMVALUE>\n'
            '</DUMMY_ROOT>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),

    # Testcases for PullInstancePaths
    (
        "PARAMVALUE elements for PullInstancesWithPath, "
        "without optional attributes",
        dict(
            operation='PullInstancesWithPath',
            skip_events=1,
            xml_str=''
            '<DUMMY_ROOT>\n'
            '  <PARAMVALUE NAME="EnumerationContext">\n'
            '    <VALUE>bla-enum-context</VALUE>\n'
            '  </PARAMVALUE>\n'
            '  <PARAMVALUE NAME="EndOfSequence">\n'
            '    <VALUE>FALSE</VALUE>\n'
            '  </PARAMVALUE>\n'
            '</DUMMY_ROOT>\n',
            exp_result=dict(
                EnumerationContext=u'bla-enum-context',
                EndOfSequence=False,
            ),
        ),
        None, None, True
    ),
    (
        "PARAMVALUE elements for PullInstancesWithPath, "
        "with optional attributes",
        dict(
            operation='PullInstancesWithPath',
            skip_events=1,
            xml_str=''
            '<DUMMY_ROOT>\n'
            '  <PARAMVALUE NAME="EnumerationContext" PARAMTYPE="string">\n'
            '    <VALUE>bla-enum-context</VALUE>\n'
            '  </PARAMVALUE>\n'
            '  <PARAMVALUE NAME="EndOfSequence" PARAMTYPE="boolean">\n'
            '    <VALUE>FALSE</VALUE>\n'
            '  </PARAMVALUE>\n'
            '</DUMMY_ROOT>\n',
            exp_result=dict(
                EnumerationContext=u'bla-enum-context',
                EndOfSequence=False,
            ),
        ),
        None, None, True
    ),
    (
        "PARAMVALUE elements for PullInstancesWithPath, "
        "with switched order of parameters",
        dict(
            operation='PullInstancesWithPath',
            skip_events=1,
            xml_str=''
            '<DUMMY_ROOT>\n'
            '  <PARAMVALUE NAME="EndOfSequence" PARAMTYPE="boolean">\n'
            '    <VALUE>FALSE</VALUE>\n'
            '  </PARAMVALUE>\n'
            '  <PARAMVALUE NAME="EnumerationContext" PARAMTYPE="string">\n'
            '    <VALUE>bla-enum-context</VALUE>\n'
            '  </PARAMVALUE>\n'
            '</DUMMY_ROOT>\n',
            exp_result=dict(
                EnumerationContext=u'bla-enum-context',
                EndOfSequence=False,
            ),
        ),
        None, None, True
    ),
    (
        "PARAMVALUE elements for PullInstancesWithPath, "
        "with missing required parameter",
        dict(
            operation='PullInstancesWithPath',
            skip_events=1,
            xml_str=''
            '<DUMMY_ROOT>\n'
            '  <PARAMVALUE NAME="EndOfSequence" PARAMTYPE="boolean">\n'
            '    <VALUE>FALSE</VALUE>\n'
            '  </PARAMVALUE>\n'
            '</DUMMY_ROOT>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PARAMVALUE elements for PullInstancesWithPath, "
        "with invalid parameter names",
        dict(
            operation='PullInstancesWithPath',
            skip_events=1,
            xml_str=''
            '<DUMMY_ROOT>\n'
            '  <PARAMVALUE NAME="EnumerationContextXXX" PARAMTYPE="string">\n'
            '    <VALUE>bla-enum-context</VALUE>\n'
            '  </PARAMVALUE>\n'
            '  <PARAMVALUE NAME="EndOfSequenceXXX" PARAMTYPE="boolean">\n'
            '    <VALUE>FALSE</VALUE>\n'
            '  </PARAMVALUE>\n'
            '</DUMMY_ROOT>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PARAMVALUE elements for PullInstancesWithPath, "
        "with invalid parameter types",
        dict(
            operation='PullInstancesWithPath',
            skip_events=1,
            xml_str=''
            '<DUMMY_ROOT>\n'
            '  <PARAMVALUE NAME="EnumerationContext" PARAMTYPE="boolean">\n'
            '    <VALUE>bla-enum-context</VALUE>\n'
            '  </PARAMVALUE>\n'
            '  <PARAMVALUE NAME="EndOfSequence" PARAMTYPE="string">\n'
            '    <VALUE>FALSE</VALUE>\n'
            '  </PARAMVALUE>\n'
            '</DUMMY_ROOT>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),

    # Testcases for PullInstancePaths
    (
        "PARAMVALUE elements for PullInstancePaths, "
        "without optional attributes",
        dict(
            operation='PullInstancePaths',
            skip_events=1,
            xml_str=''
            '<DUMMY_ROOT>\n'
            '  <PARAMVALUE NAME="EnumerationContext">\n'
            '    <VALUE>bla-enum-context</VALUE>\n'
            '  </PARAMVALUE>\n'
            '  <PARAMVALUE NAME="EndOfSequence">\n'
            '    <VALUE>FALSE</VALUE>\n'
            '  </PARAMVALUE>\n'
            '</DUMMY_ROOT>\n',
            exp_result=dict(
                EnumerationContext=u'bla-enum-context',
                EndOfSequence=False,
            ),
        ),
        None, None, True
    ),
    (
        "PARAMVALUE elements for PullInstancePaths, "
        "with optional attributes",
        dict(
            operation='PullInstancePaths',
            skip_events=1,
            xml_str=''
            '<DUMMY_ROOT>\n'
            '  <PARAMVALUE NAME="EnumerationContext" PARAMTYPE="string">\n'
            '    <VALUE>bla-enum-context</VALUE>\n'
            '  </PARAMVALUE>\n'
            '  <PARAMVALUE NAME="EndOfSequence" PARAMTYPE="boolean">\n'
            '    <VALUE>FALSE</VALUE>\n'
            '  </PARAMVALUE>\n'
            '</DUMMY_ROOT>\n',
            exp_result=dict(
                EnumerationContext=u'bla-enum-context',
                EndOfSequence=False,
            ),
        ),
        None, None, True
    ),
    (
        "PARAMVALUE elements for PullInstancePaths, "
        "with switched order of parameters",
        dict(
            operation='PullInstancePaths',
            skip_events=1,
            xml_str=''
            '<DUMMY_ROOT>\n'
            '  <PARAMVALUE NAME="EndOfSequence" PARAMTYPE="boolean">\n'
            '    <VALUE>FALSE</VALUE>\n'
            '  </PARAMVALUE>\n'
            '  <PARAMVALUE NAME="EnumerationContext" PARAMTYPE="string">\n'
            '    <VALUE>bla-enum-context</VALUE>\n'
            '  </PARAMVALUE>\n'
            '</DUMMY_ROOT>\n',
            exp_result=dict(
                EnumerationContext=u'bla-enum-context',
                EndOfSequence=False,
            ),
        ),
        None, None, True
    ),
    (
        "PARAMVALUE elements for PullInstancePaths, "
        "with missing required parameter",
        dict(
            operation='PullInstancePaths',
            skip_events=1,
            xml_str=''
            '<DUMMY_ROOT>\n'
            '  <PARAMVALUE NAME="EndOfSequence" PARAMTYPE="boolean">\n'
            '    <VALUE>FALSE</VALUE>\n'
            '  </PARAMVALUE>\n'
            '</DUMMY_ROOT>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PARAMVALUE elements for PullInstancePaths, "
        "with invalid parameter names",
        dict(
            operation='PullInstancePaths',
            skip_events=1,
            xml_str=''
            '<DUMMY_ROOT>\n'
            '  <PARAMVALUE NAME="EnumerationContextXXX" PARAMTYPE="string">\n'
            '    <VALUE>bla-enum-context</VALUE>\n'
            '  </PARAMVALUE>\n'
            '  <PARAMVALUE NAME="EndOfSequenceXXX" PARAMTYPE="boolean">\n'
            '    <VALUE>FALSE</VALUE>\n'
            '  </PARAMVALUE>\n'
            '</DUMMY_ROOT>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PARAMVALUE elements for PullInstancePaths, "
        "with invalid parameter types",
        dict(
            operation='PullInstancePaths',
            skip_events=1,
            xml_str=''
            '<DUMMY_ROOT>\n'
            '  <PARAMVALUE NAME="EnumerationContext" PARAMTYPE="boolean">\n'
            '    <VALUE>bla-enum-context</VALUE>\n'
            '  </PARAMVALUE>\n'
            '  <PARAMVALUE NAME="EndOfSequence" PARAMTYPE="string">\n'
            '    <VALUE>FALSE</VALUE>\n'
            '  </PARAMVALUE>\n'
            '</DUMMY_ROOT>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),

    # Testcases for PullInstances
    (
        "PARAMVALUE elements for PullInstances, "
        "without optional attributes",
        dict(
            operation='PullInstances',
            skip_events=1,
            xml_str=''
            '<DUMMY_ROOT>\n'
            '  <PARAMVALUE NAME="EnumerationContext">\n'
            '    <VALUE>bla-enum-context</VALUE>\n'
            '  </PARAMVALUE>\n'
            '  <PARAMVALUE NAME="EndOfSequence">\n'
            '    <VALUE>FALSE</VALUE>\n'
            '  </PARAMVALUE>\n'
            '</DUMMY_ROOT>\n',
            exp_result=dict(
                EnumerationContext=u'bla-enum-context',
                EndOfSequence=False,
            ),
        ),
        None, None, True
    ),
    (
        "PARAMVALUE elements for PullInstances, "
        "with optional attributes",
        dict(
            operation='PullInstances',
            skip_events=1,
            xml_str=''
            '<DUMMY_ROOT>\n'
            '  <PARAMVALUE NAME="EnumerationContext" PARAMTYPE="string">\n'
            '    <VALUE>bla-enum-context</VALUE>\n'
            '  </PARAMVALUE>\n'
            '  <PARAMVALUE NAME="EndOfSequence" PARAMTYPE="boolean">\n'
            '    <VALUE>FALSE</VALUE>\n'
            '  </PARAMVALUE>\n'
            '</DUMMY_ROOT>\n',
            exp_result=dict(
                EnumerationContext=u'bla-enum-context',
                EndOfSequence=False,
            ),
        ),
        None, None, True
    ),
    (
        "PARAMVALUE elements for PullInstances, "
        "with switched order of parameters",
        dict(
            operation='PullInstances',
            skip_events=1,
            xml_str=''
            '<DUMMY_ROOT>\n'
            '  <PARAMVALUE NAME="EndOfSequence" PARAMTYPE="boolean">\n'
            '    <VALUE>FALSE</VALUE>\n'
            '  </PARAMVALUE>\n'
            '  <PARAMVALUE NAME="EnumerationContext" PARAMTYPE="string">\n'
            '    <VALUE>bla-enum-context</VALUE>\n'
            '  </PARAMVALUE>\n'
            '</DUMMY_ROOT>\n',
            exp_result=dict(
                EnumerationContext=u'bla-enum-context',
                EndOfSequence=False,
            ),
        ),
        None, None, True
    ),
    (
        "PARAMVALUE elements for PullInstances, "
        "with missing required parameter",
        dict(
            operation='PullInstances',
            skip_events=1,
            xml_str=''
            '<DUMMY_ROOT>\n'
            '  <PARAMVALUE NAME="EndOfSequence" PARAMTYPE="boolean">\n'
            '    <VALUE>FALSE</VALUE>\n'
            '  </PARAMVALUE>\n'
            '</DUMMY_ROOT>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PARAMVALUE elements for PullInstances, "
        "with invalid parameter names",
        dict(
            operation='PullInstances',
            skip_events=1,
            xml_str=''
            '<DUMMY_ROOT>\n'
            '  <PARAMVALUE NAME="EnumerationContextXXX" PARAMTYPE="string">\n'
            '    <VALUE>bla-enum-context</VALUE>\n'
            '  </PARAMVALUE>\n'
            '  <PARAMVALUE NAME="EndOfSequenceXXX" PARAMTYPE="boolean">\n'
            '    <VALUE>FALSE</VALUE>\n'
            '  </PARAMVALUE>\n'
            '</DUMMY_ROOT>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PARAMVALUE elements for PullInstances, "
        "with invalid parameter types",
        dict(
            operation='PullInstances',
            skip_events=1,
            xml_str=''
            '<DUMMY_ROOT>\n'
            '  <PARAMVALUE NAME="EnumerationContext" PARAMTYPE="boolean">\n'
            '    <VALUE>bla-enum-context</VALUE>\n'
            '  </PARAMVALUE>\n'
            '  <PARAMVALUE NAME="EndOfSequence" PARAMTYPE="string">\n'
            '    <VALUE>FALSE</VALUE>\n'
            '  </PARAMVALUE>\n'
            '</DUMMY_ROOT>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),

    # Testcases for EnumerateInstances
    (
        "PARAMVALUE elements for EnumerateInstances (none)",
        dict(
            operation='EnumerateInstances',
            skip_events=1,
            xml_str='<DUMMY_ROOT/>\n',
            exp_result=dict(),
        ),
        None, None, True
    ),
    (
        "PARAMVALUE elements for EnumerateInstances, with invalid parms",
        dict(
            operation='EnumerateInstances',
            skip_events=1,
            xml_str=''
            '<DUMMY_ROOT>\n'
            '  <PARAMVALUE NAME="XXX" PARAMTYPE="string">\n'
            '    <VALUE>bla</VALUE>\n'
            '  </PARAMVALUE>\n'
            '</DUMMY_ROOT>\n',
            exp_result=dict(),
        ),
        CIMXMLParseError, None, True
    ),

    # Testcases for EnumerateInstanceNames
    (
        "PARAMVALUE elements for EnumerateInstanceNames, no parms",
        dict(
            operation='EnumerateInstanceNames',
            skip_events=1,
            xml_str='<DUMMY_ROOT/>\n',
            exp_result=dict(),
        ),
        None, None, True
    ),
    (
        "PARAMVALUE elements for EnumerateInstanceNames, with invalid parms",
        dict(
            operation='EnumerateInstanceNames',
            skip_events=1,
            xml_str=''
            '<DUMMY_ROOT>\n'
            '  <PARAMVALUE NAME="XXX" PARAMTYPE="string">\n'
            '    <VALUE>bla</VALUE>\n'
            '  </PARAMVALUE>\n'
            '</DUMMY_ROOT>\n',
            exp_result=dict(),
        ),
        CIMXMLParseError, None, True
    ),

    # Testcases for GetInstance
    (
        "PARAMVALUE elements for GetInstance",
        dict(
            operation='GetInstance',
            skip_events=1,
            xml_str='<DUMMY_ROOT/>\n',
            exp_result=dict(),
        ),
        None, None, True
    ),
    (
        "PARAMVALUE elements for GetInstance, with invalid parms",
        dict(
            operation='GetInstance',
            skip_events=1,
            xml_str=''
            '<DUMMY_ROOT>\n'
            '  <PARAMVALUE NAME="XXX" PARAMTYPE="string">\n'
            '    <VALUE>bla</VALUE>\n'
            '  </PARAMVALUE>\n'
            '</DUMMY_ROOT>\n',
            exp_result=dict(),
        ),
        CIMXMLParseError, None, True
    ),

    # Testcases for ModifyInstance
    (
        "PARAMVALUE elements for ModifyInstance",
        dict(
            operation='ModifyInstance',
            skip_events=1,
            xml_str='<DUMMY_ROOT/>\n',
            exp_result=dict(),
        ),
        None, None, True
    ),
    (
        "PARAMVALUE elements for ModifyInstance, with invalid parms",
        dict(
            operation='ModifyInstance',
            skip_events=1,
            xml_str=''
            '<DUMMY_ROOT>\n'
            '  <PARAMVALUE NAME="XXX" PARAMTYPE="string">\n'
            '    <VALUE>bla</VALUE>\n'
            '  </PARAMVALUE>\n'
            '</DUMMY_ROOT>\n',
            exp_result=dict(),
        ),
        CIMXMLParseError, None, True
    ),

    # Testcases for CreateInstance
    (
        "PARAMVALUE elements for CreateInstance",
        dict(
            operation='CreateInstance',
            skip_events=1,
            xml_str='<DUMMY_ROOT/>\n',
            exp_result=dict(),
        ),
        None, None, True
    ),
    (
        "PARAMVALUE elements for CreateInstance, with invalid parms",
        dict(
            operation='CreateInstance',
            skip_events=1,
            xml_str=''
            '<DUMMY_ROOT>\n'
            '  <PARAMVALUE NAME="XXX" PARAMTYPE="string">\n'
            '    <VALUE>bla</VALUE>\n'
            '  </PARAMVALUE>\n'
            '</DUMMY_ROOT>\n',
            exp_result=dict(),
        ),
        CIMXMLParseError, None, True
    ),

    # Testcases for DeleteInstance
    (
        "PARAMVALUE elements for DeleteInstance",
        dict(
            operation='DeleteInstance',
            skip_events=1,
            xml_str='<DUMMY_ROOT/>\n',
            exp_result=dict(),
        ),
        None, None, True
    ),
    (
        "PARAMVALUE elements for DeleteInstance, with invalid parms",
        dict(
            operation='DeleteInstance',
            skip_events=1,
            xml_str=''
            '<DUMMY_ROOT>\n'
            '  <PARAMVALUE NAME="XXX" PARAMTYPE="string">\n'
            '    <VALUE>bla</VALUE>\n'
            '  </PARAMVALUE>\n'
            '</DUMMY_ROOT>\n',
            exp_result=dict(),
        ),
        CIMXMLParseError, None, True
    ),

    # Testcases for Associators
    (
        "PARAMVALUE elements for Associators",
        dict(
            operation='Associators',
            skip_events=1,
            xml_str='<DUMMY_ROOT/>\n',
            exp_result=dict(),
        ),
        None, None, True
    ),
    (
        "PARAMVALUE elements for Associators, with invalid parms",
        dict(
            operation='Associators',
            skip_events=1,
            xml_str=''
            '<DUMMY_ROOT>\n'
            '  <PARAMVALUE NAME="XXX" PARAMTYPE="string">\n'
            '    <VALUE>bla</VALUE>\n'
            '  </PARAMVALUE>\n'
            '</DUMMY_ROOT>\n',
            exp_result=dict(),
        ),
        CIMXMLParseError, None, True
    ),

    # Testcases for AssociatorNames
    (
        "PARAMVALUE elements for AssociatorNames",
        dict(
            operation='AssociatorNames',
            skip_events=1,
            xml_str='<DUMMY_ROOT/>\n',
            exp_result=dict(),
        ),
        None, None, True
    ),
    (
        "PARAMVALUE elements for AssociatorNames, with invalid parms",
        dict(
            operation='AssociatorNames',
            skip_events=1,
            xml_str=''
            '<DUMMY_ROOT>\n'
            '  <PARAMVALUE NAME="XXX" PARAMTYPE="string">\n'
            '    <VALUE>bla</VALUE>\n'
            '  </PARAMVALUE>\n'
            '</DUMMY_ROOT>\n',
            exp_result=dict(),
        ),
        CIMXMLParseError, None, True
    ),

    # Testcases for References
    (
        "PARAMVALUE elements for References",
        dict(
            operation='References',
            skip_events=1,
            xml_str='<DUMMY_ROOT/>\n',
            exp_result=dict(),
        ),
        None, None, True
    ),
    (
        "PARAMVALUE elements for References, with invalid parms",
        dict(
            operation='References',
            skip_events=1,
            xml_str=''
            '<DUMMY_ROOT>\n'
            '  <PARAMVALUE NAME="XXX" PARAMTYPE="string">\n'
            '    <VALUE>bla</VALUE>\n'
            '  </PARAMVALUE>\n'
            '</DUMMY_ROOT>\n',
            exp_result=dict(),
        ),
        CIMXMLParseError, None, True
    ),

    # Testcases for ReferenceNames
    (
        "PARAMVALUE elements for ReferenceNames",
        dict(
            operation='ReferenceNames',
            skip_events=1,
            xml_str='<DUMMY_ROOT/>\n',
            exp_result=dict(),
        ),
        None, None, True
    ),
    (
        "PARAMVALUE elements for ReferenceNames, with invalid parms",
        dict(
            operation='ReferenceNames',
            skip_events=1,
            xml_str=''
            '<DUMMY_ROOT>\n'
            '  <PARAMVALUE NAME="XXX" PARAMTYPE="string">\n'
            '    <VALUE>bla</VALUE>\n'
            '  </PARAMVALUE>\n'
            '</DUMMY_ROOT>\n',
            exp_result=dict(),
        ),
        CIMXMLParseError, None, True
    ),

    # Testcases for InvokeMethod
    (
        "PARAMVALUE elements for InvokeMethod",
        dict(
            operation='InvokeMethod',
            skip_events=1,
            xml_str='<DUMMY_ROOT/>\n',
            exp_result=dict(),
        ),
        None, None, True
    ),
    (
        "PARAMVALUE elements for InvokeMethod, with invalid parms",
        dict(
            operation='InvokeMethod',
            skip_events=1,
            xml_str=''
            '<DUMMY_ROOT>\n'
            '  <PARAMVALUE NAME="XXX" PARAMTYPE="string">\n'
            '    <VALUE>bla</VALUE>\n'
            '  </PARAMVALUE>\n'
            '</DUMMY_ROOT>\n',
            exp_result=dict(),
        ),
        CIMXMLParseError, None, True
    ),

    # Testcases for ExecQuery
    (
        "PARAMVALUE elements for ExecQuery",
        dict(
            operation='ExecQuery',
            skip_events=1,
            xml_str='<DUMMY_ROOT/>\n',
            exp_result=dict(),
        ),
        None, None, True
    ),
    (
        "PARAMVALUE elements for ExecQuery, with invalid parms",
        dict(
            operation='ExecQuery',
            skip_events=1,
            xml_str=''
            '<DUMMY_ROOT>\n'
            '  <PARAMVALUE NAME="XXX" PARAMTYPE="string">\n'
            '    <VALUE>bla</VALUE>\n'
            '  </PARAMVALUE>\n'
            '</DUMMY_ROOT>\n',
            exp_result=dict(),
        ),
        CIMXMLParseError, None, True
    ),

    # Testcases for CloseEnumeration
    (
        "PARAMVALUE elements for CloseEnumeration",
        dict(
            operation='CloseEnumeration',
            skip_events=1,
            xml_str='<DUMMY_ROOT/>\n',
            exp_result=dict(),
        ),
        None, None, True
    ),
    (
        "PARAMVALUE elements for CloseEnumeration, with invalid parms",
        dict(
            operation='CloseEnumeration',
            skip_events=1,
            xml_str=''
            '<DUMMY_ROOT>\n'
            '  <PARAMVALUE NAME="XXX" PARAMTYPE="string">\n'
            '    <VALUE>bla</VALUE>\n'
            '  </PARAMVALUE>\n'
            '</DUMMY_ROOT>\n',
            exp_result=dict(),
        ),
        CIMXMLParseError, None, True
    ),

    # Testcases for EnumerateClasses
    (
        "PARAMVALUE elements for EnumerateClasses",
        dict(
            operation='EnumerateClasses',
            skip_events=1,
            xml_str='<DUMMY_ROOT/>\n',
            exp_result=dict(),
        ),
        None, None, True
    ),
    (
        "PARAMVALUE elements for EnumerateClasses, with invalid parms",
        dict(
            operation='EnumerateClasses',
            skip_events=1,
            xml_str=''
            '<DUMMY_ROOT>\n'
            '  <PARAMVALUE NAME="XXX" PARAMTYPE="string">\n'
            '    <VALUE>bla</VALUE>\n'
            '  </PARAMVALUE>\n'
            '</DUMMY_ROOT>\n',
            exp_result=dict(),
        ),
        CIMXMLParseError, None, True
    ),

    # Testcases for EnumerateClassNames
    (
        "PARAMVALUE elements for EnumerateClassNames",
        dict(
            operation='EnumerateClassNames',
            skip_events=1,
            xml_str='<DUMMY_ROOT/>\n',
            exp_result=dict(),
        ),
        None, None, True
    ),
    (
        "PARAMVALUE elements for EnumerateClassNames, with invalid parms",
        dict(
            operation='EnumerateClassNames',
            skip_events=1,
            xml_str=''
            '<DUMMY_ROOT>\n'
            '  <PARAMVALUE NAME="XXX" PARAMTYPE="string">\n'
            '    <VALUE>bla</VALUE>\n'
            '  </PARAMVALUE>\n'
            '</DUMMY_ROOT>\n',
            exp_result=dict(),
        ),
        CIMXMLParseError, None, True
    ),

    # Testcases for GetClass
    (
        "PARAMVALUE elements for GetClass",
        dict(
            operation='GetClass',
            skip_events=1,
            xml_str='<DUMMY_ROOT/>\n',
            exp_result=dict(),
        ),
        None, None, True
    ),
    (
        "PARAMVALUE elements for GetClass, with invalid parms",
        dict(
            operation='GetClass',
            skip_events=1,
            xml_str=''
            '<DUMMY_ROOT>\n'
            '  <PARAMVALUE NAME="XXX" PARAMTYPE="string">\n'
            '    <VALUE>bla</VALUE>\n'
            '  </PARAMVALUE>\n'
            '</DUMMY_ROOT>\n',
            exp_result=dict(),
        ),
        CIMXMLParseError, None, True
    ),

    # Testcases for ModifyClass
    (
        "PARAMVALUE elements for ModifyClass",
        dict(
            operation='ModifyClass',
            skip_events=1,
            xml_str='<DUMMY_ROOT/>\n',
            exp_result=dict(),
        ),
        None, None, True
    ),
    (
        "PARAMVALUE elements for ModifyClass, with invalid parms",
        dict(
            operation='ModifyClass',
            skip_events=1,
            xml_str=''
            '<DUMMY_ROOT>\n'
            '  <PARAMVALUE NAME="XXX" PARAMTYPE="string">\n'
            '    <VALUE>bla</VALUE>\n'
            '  </PARAMVALUE>\n'
            '</DUMMY_ROOT>\n',
            exp_result=dict(),
        ),
        CIMXMLParseError, None, True
    ),

    # Testcases for CreateClass
    (
        "PARAMVALUE elements for CreateClass",
        dict(
            operation='CreateClass',
            skip_events=1,
            xml_str='<DUMMY_ROOT/>\n',
            exp_result=dict(),
        ),
        None, None, True
    ),
    (
        "PARAMVALUE elements for CreateClass, with invalid parms",
        dict(
            operation='CreateClass',
            skip_events=1,
            xml_str=''
            '<DUMMY_ROOT>\n'
            '  <PARAMVALUE NAME="XXX" PARAMTYPE="string">\n'
            '    <VALUE>bla</VALUE>\n'
            '  </PARAMVALUE>\n'
            '</DUMMY_ROOT>\n',
            exp_result=dict(),
        ),
        CIMXMLParseError, None, True
    ),

    # Testcases for DeleteClass
    (
        "PARAMVALUE elements for DeleteClass",
        dict(
            operation='DeleteClass',
            skip_events=1,
            xml_str='<DUMMY_ROOT/>\n',
            exp_result=dict(),
        ),
        None, None, True
    ),
    (
        "PARAMVALUE elements for DeleteClass, with invalid parms",
        dict(
            operation='DeleteClass',
            skip_events=1,
            xml_str=''
            '<DUMMY_ROOT>\n'
            '  <PARAMVALUE NAME="XXX" PARAMTYPE="string">\n'
            '    <VALUE>bla</VALUE>\n'
            '  </PARAMVALUE>\n'
            '</DUMMY_ROOT>\n',
            exp_result=dict(),
        ),
        CIMXMLParseError, None, True
    ),

    # Testcases for EnumerateQualifiers
    (
        "PARAMVALUE elements for EnumerateQualifiers",
        dict(
            operation='EnumerateQualifiers',
            skip_events=1,
            xml_str='<DUMMY_ROOT/>\n',
            exp_result=dict(),
        ),
        None, None, True
    ),
    (
        "PARAMVALUE elements for EnumerateQualifiers, with invalid parms",
        dict(
            operation='EnumerateQualifiers',
            skip_events=1,
            xml_str=''
            '<DUMMY_ROOT>\n'
            '  <PARAMVALUE NAME="XXX" PARAMTYPE="string">\n'
            '    <VALUE>bla</VALUE>\n'
            '  </PARAMVALUE>\n'
            '</DUMMY_ROOT>\n',
            exp_result=dict(),
        ),
        CIMXMLParseError, None, True
    ),

    # Testcases for GetQualifier
    (
        "PARAMVALUE elements for GetQualifier",
        dict(
            operation='GetQualifier',
            skip_events=1,
            xml_str='<DUMMY_ROOT/>\n',
            exp_result=dict(),
        ),
        None, None, True
    ),
    (
        "PARAMVALUE elements for GetQualifier, with invalid parms",
        dict(
            operation='GetQualifier',
            skip_events=1,
            xml_str=''
            '<DUMMY_ROOT>\n'
            '  <PARAMVALUE NAME="XXX" PARAMTYPE="string">\n'
            '    <VALUE>bla</VALUE>\n'
            '  </PARAMVALUE>\n'
            '</DUMMY_ROOT>\n',
            exp_result=dict(),
        ),
        CIMXMLParseError, None, True
    ),

    # Testcases for SetQualifier
    (
        "PARAMVALUE elements for SetQualifier",
        dict(
            operation='SetQualifier',
            skip_events=1,
            xml_str='<DUMMY_ROOT/>\n',
            exp_result=dict(),
        ),
        None, None, True
    ),
    (
        "PARAMVALUE elements for SetQualifier, with invalid parms",
        dict(
            operation='SetQualifier',
            skip_events=1,
            xml_str=''
            '<DUMMY_ROOT>\n'
            '  <PARAMVALUE NAME="XXX" PARAMTYPE="string">\n'
            '    <VALUE>bla</VALUE>\n'
            '  </PARAMVALUE>\n'
            '</DUMMY_ROOT>\n',
            exp_result=dict(),
        ),
        CIMXMLParseError, None, True
    ),

    # Testcases for DeleteQualifier
    (
        "PARAMVALUE elements for DeleteQualifier",
        dict(
            operation='DeleteQualifier',
            skip_events=1,
            xml_str='<DUMMY_ROOT/>\n',
            exp_result=dict(),
        ),
        None, None, True
    ),
    (
        "PARAMVALUE elements for DeleteQualifier, with invalid parms",
        dict(
            operation='DeleteQualifier',
            skip_events=1,
            xml_str=''
            '<DUMMY_ROOT>\n'
            '  <PARAMVALUE NAME="XXX" PARAMTYPE="string">\n'
            '    <VALUE>bla</VALUE>\n'
            '  </PARAMVALUE>\n'
            '</DUMMY_ROOT>\n',
            exp_result=dict(),
        ),
        CIMXMLParseError, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_LIST_OF_OPERATION_PARAMVALUE_ELEMENTS)
@simplified_test_function
def test_list_of_operation_PARAMVALUE_elements(
        testcase, operation, skip_events, xml_str, exp_result):
    """
    Test CIMXMLParser.list_of_operation_PARAMVALUE_elements().
    """

    parser = CIMXMLParser(xml_str)
    for _ in range(skip_events):
        parser.get_next_event()

    # Code to be tested
    result = parser.list_of_operation_PARAMVALUE_elements(operation)

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None, \
        "Expected exception {!r} has not been raised".\
        format(testcase.exp_exc_types)

    assert result == exp_result


TESTCASES_REQUIRED_METHODRESPONSE_START_ELEMENT = [
    (
        "No METHODRESPONSE element but different element",
        dict(
            method='MyMethod',
            xml_str='<METHODRESPONSE.XXX/>\n',
        ),
        CIMXMLParseError, None, True
    ),
    (
        "METHODRESPONSE start element with expected method name",
        dict(
            method='MyMethod',
            xml_str=''
            '<METHODRESPONSE NAME="MyMethod">\n'
            '  <RETURNVALUE/>\n'
            '</METHODRESPONSE>\n',
        ),
        None, None, True
    ),
    (
        "METHODRESPONSE start element present with unexpected method name",
        dict(
            method='MyMethod',
            xml_str=''
            '<METHODRESPONSE NAME="MyMethod2">\n'
            '  <RETURNVALUE/>\n'
            '</METHODRESPONSE>\n',
        ),
        CIMXMLParseError, None, True
    ),
    (
        "METHODRESPONSE start element present but NAME attribute missing",
        dict(
            method='MyMethod',
            xml_str=''
            '<METHODRESPONSE>\n'
            '  <RETURNVALUE/>\n'
            '</METHODRESPONSE>\n',
        ),
        CIMXMLParseError, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_REQUIRED_METHODRESPONSE_START_ELEMENT)
@simplified_test_function
def test_required_METHODRESPONSE_start_element(testcase, method, xml_str):
    """
    Test CIMXMLParser.required_METHODRESPONSE_start_element().
    """

    parser = CIMXMLParser(xml_str)

    # Code to be tested
    parser.required_METHODRESPONSE_start_element(method)

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None, \
        "Expected exception {!r} has not been raised".\
        format(testcase.exp_exc_types)


TESTCASES_OPTIONAL_RETURNVALUE_ELEMENT = [
    (
        "No RETURNVALUE but different element",
        dict(
            xml_str='<RETURNVALUE.XXX/>',
            exp_result=None,
        ),
        None, None, True
    ),
    (
        "RETURNVALUE with no child element (None)",
        dict(
            xml_str=''
            '<RETURNVALUE PARAMTYPE="string">\n'
            '</RETURNVALUE>\n',
            exp_result=None,
        ),
        None, None, True
    ),
    (
        "RETURNVALUE with additional invalid trailing child element",
        dict(
            xml_str=''
            '<RETURNVALUE PARAMTYPE="string">\n'
            '  <VALUE>a</VALUE>\n'
            '  <XXX/>\n'
            '</RETURNVALUE>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "RETURNVALUE with additional invalid leading child element",
        dict(
            xml_str=''
            '<RETURNVALUE PARAMTYPE="string">\n'
            '  <XXX/>\n'
            '  <VALUE>a</VALUE>\n'
            '</RETURNVALUE>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "RETURNVALUE with invalid content text",
        dict(
            xml_str=''
            '<RETURNVALUE PARAMTYPE="string">\n'
            '  xxx\n'
            '  <VALUE>a</VALUE>\n'
            '</RETURNVALUE>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "RETURNVALUE with invalid trailing text",
        dict(
            xml_str=''
            '<RETURNVALUE PARAMTYPE="string">\n'
            '  <VALUE>a</VALUE>\n'
            '  xxx\n'
            '</RETURNVALUE>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "RETURNVALUE with ASCII characters and type string",
        dict(
            xml_str=''
            '<RETURNVALUE PARAMTYPE="string">\n'
            '  <VALUE>a</VALUE>\n'
            '</RETURNVALUE>\n',
            exp_result=u'a',
        ),
        None, None, True
    ),
    (
        "RETURNVALUE with decimal number and type string",
        dict(
            xml_str=''
            '<RETURNVALUE PARAMTYPE="string">\n'
            '  <VALUE>42</VALUE>\n'
            '</RETURNVALUE>\n',
            exp_result=u'42',
        ),
        None, None, True
    ),
    (
        "RETURNVALUE with decimal number and no type",
        dict(
            xml_str=''
            '<RETURNVALUE>\n'
            '  <VALUE>42</VALUE>\n'
            '</RETURNVALUE>\n',
            exp_result=42,
        ),
        None, None, True
    ),
    (
        "RETURNVALUE with decimal number and type uint32",
        dict(
            xml_str=''
            '<RETURNVALUE PARAMTYPE="uint32">\n'
            '  <VALUE>42</VALUE>\n'
            '</RETURNVALUE>\n',
            exp_result=Uint32(42),
        ),
        None, None, True
    ),
    (
        "RETURNVALUE with VALUE.REFERENCE and type reference",
        dict(
            xml_str=''
            '<RETURNVALUE PARAMTYPE="reference">\n'
            '  <VALUE.REFERENCE>\n'
            '    <INSTANCENAME CLASSNAME="CIM_Foo"/>\n'
            '  </VALUE.REFERENCE>\n'
            '</RETURNVALUE>\n',
            exp_result=CIMInstanceName('CIM_Foo'),
        ),
        None, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_OPTIONAL_RETURNVALUE_ELEMENT)
@simplified_test_function
def test_optional_RETURNVALUE_element(
        testcase, xml_str, exp_result):
    """
    Test CIMXMLParser.optional_RETURNVALUE_element().
    """

    parser = CIMXMLParser(xml_str)

    # Code to be tested
    result = parser.optional_RETURNVALUE_element()

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None, \
        "Expected exception {!r} has not been raised".\
        format(testcase.exp_exc_types)

    assert result == exp_result


TESTCASES_LIST_OF_METHOD_PARAMVALUE_ELEMENTS = [
    (
        "List of method PARAMVALUE elements that is empty",
        dict(
            skip_events=1,
            xml_str=''
            '<DUMMY_ROOT>\n'
            '</DUMMY_ROOT>\n',
            exp_result={},
        ),
        None, None, True
    ),
    (
        "List of method PARAMVALUE elements with one item",
        dict(
            skip_events=1,
            xml_str=''
            '<DUMMY_ROOT>\n'
            '  <PARAMVALUE NAME="Foo" PARAMTYPE="boolean">\n'
            '    <VALUE>FALSE</VALUE>\n'
            '  </PARAMVALUE>\n'
            '</DUMMY_ROOT>\n',
            exp_result={
                u'Foo': False,
            },
        ),
        None, None, True
    ),
    (
        "List of method PARAMVALUE elements with two items",
        dict(
            skip_events=1,
            xml_str=''
            '<DUMMY_ROOT>\n'
            '  <PARAMVALUE NAME="Foo1" PARAMTYPE="boolean">\n'
            '    <VALUE>FALSE</VALUE>\n'
            '  </PARAMVALUE>\n'
            '  <PARAMVALUE NAME="Foo2" PARAMTYPE="boolean">\n'
            '    <VALUE>TRUE</VALUE>\n'
            '  </PARAMVALUE>\n'
            '</DUMMY_ROOT>\n',
            exp_result={
                u'Foo1': False,
                u'Foo2': True,
            },
        ),
        None, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_LIST_OF_METHOD_PARAMVALUE_ELEMENTS)
@simplified_test_function
def test_list_of_method_PARAMVALUE_elements(
        testcase, skip_events, xml_str, exp_result):
    """
    Test CIMXMLParser.list_of_method_PARAMVALUE_elements().
    """

    parser = CIMXMLParser(xml_str)
    for _ in range(skip_events):
        parser.get_next_event()

    # Code to be tested
    result = parser.list_of_method_PARAMVALUE_elements()

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None, \
        "Expected exception {!r} has not been raised".\
        format(testcase.exp_exc_types)

    assert result == exp_result


TESTCASES_REQUIRED_METHOD_PARAMVALUE_ELEMENT = [
    (
        "No PARAMVALUE but different element",
        dict(
            xml_str='<PARAMVALUE.XXX/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PARAMVALUE with missing required NAME attribute",
        dict(
            xml_str=''
            '<PARAMVALUE PARAMTYPE="string">\n'
            '  <VALUE>bla</VALUE>\n'
            '</PARAMVALUE>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PARAMVALUE with invalid content text",
        dict(
            xml_str=''
            '<PARAMVALUE NAME="Foo" PARAMTYPE="string">\n'
            '  xxx\n'
            '  <VALUE>bla</VALUE>\n'
            '</PARAMVALUE>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PARAMVALUE with invalid trailing text",
        dict(
            xml_str=''
            '<PARAMVALUE NAME="Foo" PARAMTYPE="string">\n'
            '  <VALUE>bla</VALUE>\n'
            '  xxx\n'
            '</PARAMVALUE>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PARAMVALUE with invalid child element",
        dict(
            xml_str=''
            '<PARAMVALUE NAME="Foo">\n'
            '  <XXX/>\n'
            '</PARAMVALUE>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PARAMVALUE with invalid PARAMTYPE",
        dict(
            xml_str=''
            '<PARAMVALUE NAME="Foo" PARAMTYPE="bar">\n'
            '  <VALUE>bla</VALUE>\n'
            '</PARAMVALUE>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),

    # Testcases with NULL
    (
        "PARAMVALUE without child elements (representing NULL), "
        "PARAMTYPE string",
        dict(
            xml_str=''
            '<PARAMVALUE NAME="Foo" PARAMTYPE="string">\n'
            '</PARAMVALUE>\n',
            exp_result=(u'Foo', None),
        ),
        None, None, True
    ),
    (
        "PARAMVALUE without child elements (representing NULL), no PARAMTYPE",
        dict(
            xml_str=''
            '<PARAMVALUE NAME="Foo">\n'
            '</PARAMVALUE>\n',
            exp_result=(u'Foo', None),
        ),
        None, None, True
    ),

    # Testcases with VALUE child element
    (
        "PARAMVALUE with VALUE containing string, PARAMTYPE string",
        dict(
            xml_str=''
            '<PARAMVALUE NAME="Foo" PARAMTYPE="string">\n'
            '  <VALUE>bla</VALUE>\n'
            '</PARAMVALUE>\n',
            exp_result=(u'Foo', u'bla'),
        ),
        None, None, True
    ),
    (
        "PARAMVALUE with VALUE containing decimal number, no PARAMTYPE",
        dict(
            xml_str=''
            '<PARAMVALUE NAME="Foo">\n'
            '  <VALUE>42</VALUE>\n'
            '</PARAMVALUE>\n',
            exp_result=(u'Foo', 42),
        ),
        None, None, True
    ),
    (
        "PARAMVALUE with VALUE containing decimal number, PARAMTYPE uint32",
        dict(
            xml_str=''
            '<PARAMVALUE NAME="Foo" PARAMTYPE="uint32">\n'
            '  <VALUE>42</VALUE>\n'
            '</PARAMVALUE>\n',
            exp_result=(u'Foo', Uint32(42)),
        ),
        None, None, True
    ),

    # Testcases with VALUE.REFERENCE child element
    (
        "PARAMVALUE with VALUE.REFERENCE, PARAMTYPE reference",
        dict(
            xml_str=''
            '<PARAMVALUE NAME="Foo" PARAMTYPE="reference">\n'
            '  <VALUE.REFERENCE>\n'
            '    <INSTANCENAME CLASSNAME="CIM_Foo"/>\n'
            '  </VALUE.REFERENCE>\n'
            '</PARAMVALUE>\n',
            exp_result=(u'Foo', CIMInstanceName('CIM_Foo')),
        ),
        None, None, True
    ),
    (
        "PARAMVALUE with VALUE.REFERENCE, no PARAMTYPE",
        dict(
            xml_str=''
            '<PARAMVALUE NAME="Foo">\n'
            '  <VALUE.REFERENCE>\n'
            '    <INSTANCENAME CLASSNAME="CIM_Foo"/>\n'
            '  </VALUE.REFERENCE>\n'
            '</PARAMVALUE>\n',
            exp_result=(u'Foo', CIMInstanceName('CIM_Foo')),
        ),
        None, None, True
    ),

    # Testcases with VALUE.ARRAY child element
    (
        "PARAMVALUE with empty VALUE.ARRAY, PARAMTYPE string",
        dict(
            xml_str=''
            '<PARAMVALUE NAME="Foo" PARAMTYPE="string">\n'
            '  <VALUE.ARRAY/>\n'
            '</PARAMVALUE>\n',
            exp_result=(u'Foo', []),
        ),
        None, None, True
    ),
    (
        "PARAMVALUE with VALUE.ARRAY containing one string, PARAMTYPE string",
        dict(
            xml_str=''
            '<PARAMVALUE NAME="Foo" PARAMTYPE="string">\n'
            '  <VALUE.ARRAY>\n'
            '    <VALUE>a</VALUE>\n'
            '  </VALUE.ARRAY>\n'
            '</PARAMVALUE>\n',
            exp_result=(u'Foo', [u'a']),
        ),
        None, None, True
    ),
    (
        "PARAMVALUE with VALUE.ARRAY containing one NULL value and string, "
        "PARAMTYPE string",
        dict(
            xml_str=''
            '<PARAMVALUE NAME="Foo" PARAMTYPE="string">\n'
            '  <VALUE.ARRAY>\n'
            '    <VALUE.NULL/>\n'
            '    <VALUE>a</VALUE>\n'
            '  </VALUE.ARRAY>\n'
            '</PARAMVALUE>\n',
            exp_result=(u'Foo', [None, u'a']),
        ),
        None, None, True
    ),

    # Testcases with VALUE.REFARRAY child element
    (
        "PARAMVALUE with empty VALUE.REFARRAY, PARAMTYPE reference",
        dict(
            xml_str=''
            '<PARAMVALUE NAME="Foo" PARAMTYPE="reference">\n'
            '  <VALUE.REFARRAY/>\n'
            '</PARAMVALUE>\n',
            exp_result=(u'Foo', []),
        ),
        None, None, True
    ),
    (
        "PARAMVALUE with VALUE.REFARRAY containing one instance path, "
        "PARAMTYPE reference",
        dict(
            xml_str=''
            '<PARAMVALUE NAME="Foo" PARAMTYPE="reference">\n'
            '  <VALUE.REFARRAY>\n'
            '    <VALUE.REFERENCE>\n'
            '      <INSTANCENAME CLASSNAME="CIM_Foo"/>\n'
            '    </VALUE.REFERENCE>\n'
            '  </VALUE.REFARRAY>\n'
            '</PARAMVALUE>\n',
            exp_result=(u'Foo', [CIMInstanceName('CIM_Foo')]),
        ),
        None, None, True
    ),
    (
        "PARAMVALUE with VALUE.REFARRAY containing one instance path, "
        "no PARAMTYPE",
        dict(
            xml_str=''
            '<PARAMVALUE NAME="Foo">\n'
            '  <VALUE.REFARRAY>\n'
            '    <VALUE.REFERENCE>\n'
            '      <INSTANCENAME CLASSNAME="CIM_Foo"/>\n'
            '    </VALUE.REFERENCE>\n'
            '  </VALUE.REFARRAY>\n'
            '</PARAMVALUE>\n',
            exp_result=(u'Foo', [CIMInstanceName('CIM_Foo')]),
        ),
        None, None, True
    ),
    (
        "PARAMVALUE with VALUE.REFARRAY containing one NULL value and "
        "one instance path, PARAMTYPE reference",
        dict(
            xml_str=''
            '<PARAMVALUE NAME="Foo" PARAMTYPE="reference">\n'
            '  <VALUE.REFARRAY>\n'
            '    <VALUE.NULL/>\n'
            '    <VALUE.REFERENCE>\n'
            '      <INSTANCENAME CLASSNAME="CIM_Foo"/>\n'
            '    </VALUE.REFERENCE>\n'
            '  </VALUE.REFARRAY>\n'
            '</PARAMVALUE>\n',
            exp_result=(u'Foo', [None, CIMInstanceName('CIM_Foo')]),
        ),
        None, None, True
    ),
    (
        "PARAMVALUE with VALUE.REFARRAY containing one NULL value and "
        "one instance path, no PARAMTYPE",
        dict(
            xml_str=''
            '<PARAMVALUE NAME="Foo">\n'
            '  <VALUE.REFARRAY>\n'
            '    <VALUE.NULL/>\n'
            '    <VALUE.REFERENCE>\n'
            '      <INSTANCENAME CLASSNAME="CIM_Foo"/>\n'
            '    </VALUE.REFERENCE>\n'
            '  </VALUE.REFARRAY>\n'
            '</PARAMVALUE>\n',
            exp_result=(u'Foo', [None, CIMInstanceName('CIM_Foo')]),
        ),
        None, None, True
    ),

    # Testcases with CLASSNAME child element
    (
        "PARAMVALUE with CLASSNAME, no PARAMTYPE",
        dict(
            xml_str=''
            '<PARAMVALUE NAME="Foo">\n'
            '  <CLASSNAME NAME="CIM_Foo"/>\n'
            '</PARAMVALUE>\n',
            exp_result=(u'Foo', CIMClassName('CIM_Foo')),
        ),
        None, None, True
    ),

    # Testcases with INSTANCENAME child element
    (
        "PARAMVALUE with INSTANCENAME, no PARAMTYPE",
        dict(
            xml_str=''
            '<PARAMVALUE NAME="Foo">\n'
            '  <INSTANCENAME CLASSNAME="CIM_Foo"/>\n'
            '</PARAMVALUE>\n',
            exp_result=(u'Foo', CIMInstanceName('CIM_Foo')),
        ),
        None, None, True
    ),

    # Testcases with CLASS child element
    (
        "PARAMVALUE with CLASS, no PARAMTYPE",
        dict(
            xml_str=''
            '<PARAMVALUE NAME="Foo">\n'
            '  <CLASS NAME="CIM_Foo"/>\n'
            '</PARAMVALUE>\n',
            exp_result=(u'Foo', CIMClass('CIM_Foo')),
        ),
        None, None, True
    ),

    # Testcases with INSTANCE child element
    (
        "PARAMVALUE with INSTANCE, no PARAMTYPE",
        dict(
            xml_str=''
            '<PARAMVALUE NAME="Foo">\n'
            '  <INSTANCE CLASSNAME="CIM_Foo"/>\n'
            '</PARAMVALUE>\n',
            exp_result=(u'Foo', CIMInstance('CIM_Foo')),
        ),
        None, None, True
    ),

    # Testcases with VALUE.NAMEDINSTANCE child element
    (
        "PARAMVALUE with VALUE.NAMEDINSTANCE, no PARAMTYPE",
        dict(
            xml_str=''
            '<PARAMVALUE NAME="Foo">\n'
            '  <VALUE.NAMEDINSTANCE>\n'
            '    <INSTANCENAME CLASSNAME="CIM_Foo"/>\n'
            '    <INSTANCE CLASSNAME="CIM_Foo"/>\n'
            '  </VALUE.NAMEDINSTANCE>\n'
            '</PARAMVALUE>\n',
            exp_result=(
                u'Foo',
                CIMInstance(
                    'CIM_Foo',
                    path=CIMInstanceName('CIM_Foo'))
            ),
        ),
        None, None, True
    ),

]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_REQUIRED_METHOD_PARAMVALUE_ELEMENT)
@simplified_test_function
def test_required_method_PARAMVALUE_element(
        testcase, xml_str, exp_result):
    """
    Test CIMXMLParser.required_method_PARAMVALUE_element().
    """

    parser = CIMXMLParser(xml_str)

    # Code to be tested
    result = parser.required_method_PARAMVALUE_element()

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None, \
        "Expected exception {!r} has not been raised".\
        format(testcase.exp_exc_types)

    assert result == exp_result


TESTCASES_OPTIONAL_ERROR_ELEMENT = [
    (
        "No ERROR but different elemewnt",
        dict(
            xml_str='<ERROR.XXX/>',
            exp_result=None,
        ),
        None, None, True
    ),
    (
        "ERROR element without optional DESCRIPTION attribute",
        dict(
            xml_str=''
            '<ERROR CODE="5">\n'
            '</ERROR>\n',
            exp_result=(5, None, []),
        ),
        None, None, True
    ),
    (
        "ERROR element without required CODE attribute",
        dict(
            xml_str=''
            '<ERROR>\n'
            '</ERROR>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "ERROR element with all attributes and no instances",
        dict(
            xml_str=''
            '<ERROR CODE="5" DESCRIPTION="bla">\n'
            '</ERROR>\n',
            exp_result=(5, u'bla', []),
        ),
        None, None, True
    ),
    (
        "ERROR element with all attributes and one CIM_Error instance",
        dict(
            xml_str=''
            '<ERROR CODE="5" DESCRIPTION="bla">\n'
            '  <INSTANCE CLASSNAME="CIM_Error"/>\n'
            '</ERROR>\n',
            exp_result=(5, u'bla', [
                CIMInstance('CIM_Error'),
            ]),
        ),
        None, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_OPTIONAL_ERROR_ELEMENT)
@simplified_test_function
def test_optional_ERROR_element(testcase, xml_str, exp_result):
    """
    Test CIMXMLParser.optional_ERROR_element().
    """

    parser = CIMXMLParser(xml_str)

    # Code to be tested
    result = parser.optional_ERROR_element()

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None, \
        "Expected exception {!r} has not been raised".\
        format(testcase.exp_exc_types)

    assert result == exp_result


TESTCASES_LIST_OF_CLASS_ELEMENTS = [
    (
        "List of CLASS elements that is empty",
        dict(
            skip_events=1,
            xml_str=''
            '<DUMMY_ROOT>\n'
            '</DUMMY_ROOT>\n',
            exp_result=[],
        ),
        None, None, True
    ),
    (
        "List of CLASS elements with one item",
        dict(
            skip_events=1,
            xml_str=''
            '<DUMMY_ROOT>\n'
            '  <CLASS NAME="CIM_Foo"/>\n'
            '</DUMMY_ROOT>\n',
            exp_result=[
                CIMClass('CIM_Foo'),
            ],
        ),
        None, None, True
    ),
    (
        "List of CLASS elements with two items",
        dict(
            skip_events=1,
            xml_str=''
            '<DUMMY_ROOT>\n'
            '  <CLASS NAME="CIM_Foo1"/>\n'
            '  <CLASS NAME="CIM_Foo2"/>\n'
            '</DUMMY_ROOT>\n',
            exp_result=[
                CIMClass('CIM_Foo1'),
                CIMClass('CIM_Foo2'),
            ],
        ),
        None, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_LIST_OF_CLASS_ELEMENTS)
@simplified_test_function
def test_list_of_CLASS_elements(testcase, skip_events, xml_str, exp_result):
    """
    Test CIMXMLParser.list_of_CLASS_elements().
    """

    parser = CIMXMLParser(xml_str)
    for _ in range(skip_events):
        parser.get_next_event()

    # Code to be tested
    result = parser.list_of_CLASS_elements()

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None, \
        "Expected exception {!r} has not been raised".\
        format(testcase.exp_exc_types)

    assert result == exp_result


TESTCASES_OPTIONAL_CLASS_ELEMENT = [
    (
        "CLASS element absent",
        dict(
            xml_str='<SOME.OTHER/>',
            exp_result=None,
        ),
        None, None, True
    ),
    (
        "CLASS element without features",
        dict(
            xml_str=''
            '<CLASS NAME="CIM_Foo"/>\n',
            exp_result=CIMClass('CIM_Foo'),
        ),
        None, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_OPTIONAL_CLASS_ELEMENT)
@simplified_test_function
def test_optional_CLASS_element(testcase, xml_str, exp_result):
    """
    Test CIMXMLParser.optional_CLASS_element().
    """

    parser = CIMXMLParser(xml_str)

    # Code to be tested
    result = parser.optional_CLASS_element()

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None, \
        "Expected exception {!r} has not been raised".\
        format(testcase.exp_exc_types)

    assert result == exp_result


TESTCASES_REQUIRED_CLASS_ELEMENT = [
    (
        "No CLASS but different element",
        dict(
            xml_str='<CLASS.XXX/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "CLASS with invalid child element",
        dict(
            xml_str=''
            '<CLASS NAME="CIM_Foo">\n'
            '  <XXX/>\n'
            '</CLASS>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "CLASS with invalid content text",
        dict(
            xml_str=''
            '<CLASS NAME="CIM_Foo">\n'
            '  xxx\n'
            '</CLASS>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "CLASS with invalid trailing text",
        dict(
            xml_str=''
            '<CLASS NAME="CIM_Foo">\n'
            '  <QUALIFIER NAME="Association" TYPE="boolean"/>\n'
            '  xxx\n'
            '</CLASS>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "CLASS with missing required attribute NAME",
        dict(
            xml_str=''
            '<CLASS/>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "CLASS with NAME using ASCII characters",
        dict(
            xml_str=''
            '<CLASS NAME="CIM_Foo"/>\n',
            exp_result=CIMClass('CIM_Foo'),
        ),
        None, None, True
    ),
    (
        "CLASS with NAME using non-ASCII UCS-2 characters",
        dict(
            xml_str=b''
            b'<CLASS NAME="CIM_Foo\xC3\xA9"/>\n',
            exp_result=CIMClass(u'CIM_Foo\u00E9'),
        ),
        None, None, True
    ),
    (
        "CLASS with NAME using non-UCS-2 characters",
        dict(
            xml_str=b''
            b'<CLASS NAME="CIM_Foo\xF0\x90\x85\x82"/>\n',
            exp_result=CIMClass(u'CIM_Foo\U00010142'),
        ),
        None, None, True
    ),
    (
        "CLASS without qualifiers, properties or methods",
        dict(
            xml_str=''
            '<CLASS NAME="CIM_Foo"/>\n',
            exp_result=CIMClass('CIM_Foo'),
        ),
        None, None, True
    ),
    (
        "CLASS with superclass",
        dict(
            xml_str=''
            '<CLASS NAME="CIM_Foo" SUPERCLASS="CIM_Bar"/>\n',
            exp_result=CIMClass(
                'CIM_Foo',
                superclass='CIM_Bar'
            ),
        ),
        None, None, True
    ),
    (
        "CLASS with qualifiers and properties",
        dict(
            xml_str=''
            '<CLASS NAME="CIM_Foo">\n'
            '  <QUALIFIER NAME="Association" TYPE="boolean"/>\n'
            '  <QUALIFIER NAME="Abstract" TYPE="boolean"/>\n'
            '  <PROPERTY NAME="Pstring" TYPE="string"/>\n'
            '  <PROPERTY.ARRAY NAME="Puint8array" TYPE="uint8"/>\n'
            '  <PROPERTY.REFERENCE NAME="Pref"/>\n'
            '</CLASS>\n',
            exp_result=CIMClass(
                'CIM_Foo',
                qualifiers=[
                    CIMQualifier('Association', value=None, type='boolean',
                                 **qualifier_default_attrs()),
                    CIMQualifier('Abstract', value=None, type='boolean',
                                 **qualifier_default_attrs()),
                ],
                properties=[
                    CIMProperty('Pstring', type='string', value=None,
                                propagated=False),
                    CIMProperty('Puint8array', type='uint8', value=None,
                                is_array=True, propagated=False),
                    CIMProperty('Pref', type='reference', value=None,
                                propagated=False),
                ],
            ),
        ),
        None, None, True
    ),
    (
        "CLASS with qualifiers and methods",
        dict(
            xml_str=''
            '<CLASS NAME="CIM_Foo">\n'
            '  <QUALIFIER NAME="Association" TYPE="boolean"/>\n'
            '  <QUALIFIER NAME="Abstract" TYPE="boolean"/>\n'
            '  <METHOD NAME="Muint32" TYPE="uint32"/>\n'
            '  <METHOD NAME="Mstring" TYPE="string"/>\n'
            '</CLASS>\n',
            exp_result=CIMClass(
                'CIM_Foo',
                qualifiers=[
                    CIMQualifier('Association', value=None, type='boolean',
                                 **qualifier_default_attrs()),
                    CIMQualifier('Abstract', value=None, type='boolean',
                                 **qualifier_default_attrs()),
                ],
                methods=[
                    CIMMethod('Muint32', return_type='uint32',
                              propagated=False),
                    CIMMethod('Mstring', return_type='string',
                              propagated=False),
                ],
            ),
        ),
        None, None, True
    ),
    (
        "CLASS with qualifiers, properties and methods",
        dict(
            xml_str=''
            '<CLASS NAME="CIM_Foo">\n'
            '  <QUALIFIER NAME="Association" TYPE="boolean"/>\n'
            '  <QUALIFIER NAME="Abstract" TYPE="boolean"/>\n'
            '  <PROPERTY NAME="Pstring" TYPE="string"/>\n'
            '  <PROPERTY.ARRAY NAME="Puint8array" TYPE="uint8"/>\n'
            '  <PROPERTY.REFERENCE NAME="Pref"/>\n'
            '  <METHOD NAME="Muint32" TYPE="uint32"/>\n'
            '  <METHOD NAME="Mstring" TYPE="string"/>\n'
            '</CLASS>\n',
            exp_result=CIMClass(
                'CIM_Foo',
                qualifiers=[
                    CIMQualifier('Association', value=None, type='boolean',
                                 **qualifier_default_attrs()),
                    CIMQualifier('Abstract', value=None, type='boolean',
                                 **qualifier_default_attrs()),
                ],
                properties=[
                    CIMProperty('Pstring', type='string', value=None,
                                propagated=False),
                    CIMProperty('Puint8array', type='uint8', value=None,
                                is_array=True, propagated=False),
                    CIMProperty('Pref', type='reference', value=None,
                                propagated=False),
                ],
                methods=[
                    CIMMethod('Muint32', return_type='uint32',
                              propagated=False),
                    CIMMethod('Mstring', return_type='string',
                              propagated=False),
                ],
            ),
        ),
        None, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_REQUIRED_CLASS_ELEMENT)
@simplified_test_function
def test_required_CLASS_element(testcase, xml_str, exp_result):
    """
    Test CIMXMLParser.required_CLASS_element().
    """

    parser = CIMXMLParser(xml_str)

    # Code to be tested
    result = parser.required_CLASS_element()

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None, \
        "Expected exception {!r} has not been raised".\
        format(testcase.exp_exc_types)

    assert result == exp_result


TESTCASES_LIST_OF_CLASSNAME_ELEMENTS = [
    (
        "List of CLASSNAME elements that is empty",
        dict(
            skip_events=1,
            xml_str=''
            '<DUMMY_ROOT>\n'
            '</DUMMY_ROOT>\n',
            exp_result=[],
        ),
        None, None, True
    ),
    (
        "List of CLASSNAME elements with one item",
        dict(
            skip_events=1,
            xml_str=''
            '<DUMMY_ROOT>\n'
            '  <CLASSNAME NAME="CIM_Foo"/>\n'
            '</DUMMY_ROOT>\n',
            exp_result=[
                CIMClassName('CIM_Foo'),
            ],
        ),
        None, None, True
    ),
    (
        "List of CLASSNAME elements with two items",
        dict(
            skip_events=1,
            xml_str=''
            '<DUMMY_ROOT>\n'
            '  <CLASSNAME NAME="CIM_Foo1"/>\n'
            '  <CLASSNAME NAME="CIM_Foo2"/>\n'
            '</DUMMY_ROOT>\n',
            exp_result=[
                CIMClassName('CIM_Foo1'),
                CIMClassName('CIM_Foo2'),
            ],
        ),
        None, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_LIST_OF_CLASSNAME_ELEMENTS)
@simplified_test_function
def test_list_of_CLASSNAME_elements(testcase, skip_events, xml_str, exp_result):
    """
    Test CIMXMLParser.list_of_CLASSNAME_elements().
    """

    parser = CIMXMLParser(xml_str)
    for _ in range(skip_events):
        parser.get_next_event()

    # Code to be tested
    result = parser.list_of_CLASSNAME_elements()

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None, \
        "Expected exception {!r} has not been raised".\
        format(testcase.exp_exc_types)

    assert result == exp_result


TESTCASES_REQUIRED_CLASSNAME_ELEMENT = [
    (
        "No CLASSNAME but different element",
        dict(
            xml_str='<CLASSNAME.XXX/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "CLASSNAME with invalid child element",
        dict(
            xml_str=''
            '<CLASSNAME NAME="a">\n'
            '  <XXX/>\n'
            '</CLASSNAME>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "CLASSNAME with invalid content text",
        dict(
            xml_str=''
            '<CLASSNAME NAME="a">\n'
            '  xxx\n'
            '</CLASSNAME>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "CLASSNAME with missing required attribute NAME",
        dict(
            xml_str=''
            '<CLASSNAME/>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "CLASSNAME with NAME using ASCII characters",
        dict(
            xml_str=''
            '<CLASSNAME NAME="CIM_Foo"/>\n',
            exp_result=CIMClassName('CIM_Foo'),
        ),
        None, None, True
    ),
    (
        "CLASSNAME with NAME using non-ASCII UCS-2 characters",
        dict(
            xml_str=b''
            b'<CLASSNAME NAME="CIM_Foo\xC3\xA9"/>\n',
            exp_result=CIMClassName(u'CIM_Foo\u00E9'),
        ),
        None, None, True
    ),
    (
        "CLASSNAME with NAME using non-UCS-2 characters",
        dict(
            xml_str=b''
            b'<CLASSNAME NAME="CIM_Foo\xF0\x90\x85\x82"/>\n',
            exp_result=CIMClassName(u'CIM_Foo\U00010142'),
        ),
        None, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_REQUIRED_CLASSNAME_ELEMENT)
@simplified_test_function
def test_required_CLASSNAME_element(testcase, xml_str, exp_result):
    """
    Test CIMXMLParser.required_CLASSNAME_element().
    """

    parser = CIMXMLParser(xml_str)

    # Code to be tested
    result = parser.required_CLASSNAME_element()

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None, \
        "Expected exception {!r} has not been raised".\
        format(testcase.exp_exc_types)

    assert result == exp_result


TESTCASES_REQUIRED_CLASSPATH_ELEMENT = [
    (
        "No CLASSPATH but different element",
        dict(
            xml_str='<CLASSPATH.XXX/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "CLASSPATH with invalid leading child element",
        dict(
            xml_str=''
            '<CLASSPATH>\n'
            '  <XXX/>\n'
            '  <NAMESPACEPATH>\n'
            '    <HOST>woot.com</HOST>\n'
            '    <LOCALNAMESPACEPATH>\n'
            '      <NAMESPACE NAME="foo"/>\n'
            '    </LOCALNAMESPACEPATH>\n'
            '  </NAMESPACEPATH>\n'
            '  <CLASSNAME NAME="CIM_Foo"/>\n'
            '</CLASSPATH>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "CLASSPATH with invalid trailing child element",
        dict(
            xml_str=''
            '<CLASSPATH>\n'
            '  <NAMESPACEPATH>\n'
            '    <HOST>woot.com</HOST>\n'
            '    <LOCALNAMESPACEPATH>\n'
            '      <NAMESPACE NAME="foo"/>\n'
            '    </LOCALNAMESPACEPATH>\n'
            '  </NAMESPACEPATH>\n'
            '  <CLASSNAME NAME="CIM_Foo"/>\n'
            '  <XXX/>\n'
            '</CLASSPATH>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "CLASSPATH with invalid content text",
        dict(
            xml_str=''
            '<CLASSPATH>\n'
            '  xxx\n'
            '  <NAMESPACEPATH>\n'
            '    <HOST>woot.com</HOST>\n'
            '    <LOCALNAMESPACEPATH>\n'
            '      <NAMESPACE NAME="foo"/>\n'
            '    </LOCALNAMESPACEPATH>\n'
            '  </NAMESPACEPATH>\n'
            '  <CLASSNAME NAME="CIM_Foo"/>\n'
            '</CLASSPATH>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "CLASSPATH with invalid trailing text",
        dict(
            xml_str=''
            '<CLASSPATH>\n'
            '  <NAMESPACEPATH>\n'
            '    <HOST>woot.com</HOST>\n'
            '    <LOCALNAMESPACEPATH>\n'
            '      <NAMESPACE NAME="foo"/>\n'
            '    </LOCALNAMESPACEPATH>\n'
            '  </NAMESPACEPATH>\n'
            '  <CLASSNAME NAME="CIM_Foo"/>\n'
            '  xxx\n'
            '</CLASSPATH>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "CLASSPATH with missing children",
        dict(
            xml_str=''
            '<CLASSPATH/>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "CLASSPATH with missing child NAMESPACEPATH",
        dict(
            xml_str=''
            '<CLASSPATH>\n'
            '  <CLASSNAME NAME="CIM_Foo"/>\n'
            '</CLASSPATH>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "CLASSPATH with missing child CLASSNAME",
        dict(
            xml_str=''
            '<CLASSPATH>\n'
            '  <NAMESPACEPATH>\n'
            '    <HOST>woot.com</HOST>\n'
            '    <LOCALNAMESPACEPATH>\n'
            '      <NAMESPACE NAME="foo"/>\n'
            '    </LOCALNAMESPACEPATH>\n'
            '  </NAMESPACEPATH>\n'
            '</CLASSPATH>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "CLASSPATH with children in incorrect order",
        dict(
            xml_str=''
            '<CLASSPATH>\n'
            '  <CLASSNAME NAME="CIM_Foo"/>\n'
            '  <NAMESPACEPATH>\n'
            '    <HOST>woot.com</HOST>\n'
            '    <LOCALNAMESPACEPATH>\n'
            '      <NAMESPACE NAME="foo"/>\n'
            '    </LOCALNAMESPACEPATH>\n'
            '  </NAMESPACEPATH>\n'
            '</CLASSPATH>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "CLASSPATH (normal case)",
        dict(
            xml_str=''
            '<CLASSPATH>\n'
            '  <NAMESPACEPATH>\n'
            '    <HOST>woot.com</HOST>\n'
            '    <LOCALNAMESPACEPATH>\n'
            '      <NAMESPACE NAME="foo"/>\n'
            '    </LOCALNAMESPACEPATH>\n'
            '  </NAMESPACEPATH>\n'
            '  <CLASSNAME NAME="CIM_Foo"/>\n'
            '</CLASSPATH>\n',
            exp_result=CIMClassName(
                'CIM_Foo',
                namespace='foo',
                host='woot.com',
            ),
        ),
        None, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_REQUIRED_CLASSPATH_ELEMENT)
@simplified_test_function
def test_required_CLASSPATH_element(testcase, xml_str, exp_result):
    """
    Test CIMXMLParser.required_CLASSPATH_element().
    """

    parser = CIMXMLParser(xml_str)

    # Code to be tested
    result = parser.required_CLASSPATH_element()

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None, \
        "Expected exception {!r} has not been raised".\
        format(testcase.exp_exc_types)

    assert result == exp_result


TESTCASES_REQUIRED_LOCALCLASSPATH_ELEMENT = [
    (
        "No LOCALCLASSPATH but different element",
        dict(
            xml_str='<LOCALCLASSPATH.XXX/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "LOCALCLASSPATH with invalid child element",
        dict(
            xml_str=''
            '<LOCALCLASSPATH>\n'
            '  <LOCALNAMESPACEPATH>\n'
            '    <NAMESPACE NAME="foo"/>\n'
            '  </LOCALNAMESPACEPATH>\n'
            '  <CLASSNAME NAME="CIM_Foo"/>\n'
            '  <XXX/>\n'
            '</LOCALCLASSPATH>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "LOCALCLASSPATH with invalid content text",
        dict(
            xml_str=''
            '<LOCALCLASSPATH>\n'
            '  xxx\n'
            '  <LOCALNAMESPACEPATH>\n'
            '    <NAMESPACE NAME="foo"/>\n'
            '  </LOCALNAMESPACEPATH>\n'
            '  <CLASSNAME NAME="CIM_Foo"/>\n'
            '</LOCALCLASSPATH>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "LOCALCLASSPATH with invalid trailing text",
        dict(
            xml_str=''
            '<LOCALCLASSPATH>\n'
            '  <LOCALNAMESPACEPATH>\n'
            '    <NAMESPACE NAME="foo"/>\n'
            '  </LOCALNAMESPACEPATH>\n'
            '  <CLASSNAME NAME="CIM_Foo"/>\n'
            '  xxx\n'
            '</LOCALCLASSPATH>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "LOCALCLASSPATH with missing children",
        dict(
            xml_str=''
            '<LOCALCLASSPATH/>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "LOCALCLASSPATH with missing child LOCALNAMESPACEPATH",
        dict(
            xml_str=''
            '<LOCALCLASSPATH>\n'
            '  <CLASSNAME NAME="CIM_Foo"/>\n'
            '</LOCALCLASSPATH>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "LOCALCLASSPATH with missing child CLASSNAME",
        dict(
            xml_str=''
            '<LOCALCLASSPATH>\n'
            '  <LOCALNAMESPACEPATH>\n'
            '    <NAMESPACE NAME="foo"/>\n'
            '  </LOCALNAMESPACEPATH>\n'
            '</LOCALCLASSPATH>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "LOCALCLASSPATH with children in incorrect order",
        dict(
            xml_str=''
            '<LOCALCLASSPATH>\n'
            '  <CLASSNAME NAME="CIM_Foo"/>\n'
            '  <LOCALNAMESPACEPATH>\n'
            '    <NAMESPACE NAME="foo"/>\n'
            '  </LOCALNAMESPACEPATH>\n'
            '</LOCALCLASSPATH>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "LOCALCLASSPATH (normal case)",
        dict(
            xml_str=''
            '<LOCALCLASSPATH>\n'
            '  <LOCALNAMESPACEPATH>\n'
            '    <NAMESPACE NAME="foo"/>\n'
            '  </LOCALNAMESPACEPATH>\n'
            '  <CLASSNAME NAME="CIM_Foo"/>\n'
            '</LOCALCLASSPATH>\n',
            exp_result=CIMClassName(
                'CIM_Foo',
                namespace='foo',
            ),
        ),
        None, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_REQUIRED_LOCALCLASSPATH_ELEMENT)
@simplified_test_function
def test_required_LOCALCLASSPATH_element(testcase, xml_str, exp_result):
    """
    Test CIMXMLParser.required_LOCALCLASSPATH_element().
    """

    parser = CIMXMLParser(xml_str)

    # Code to be tested
    result = parser.required_LOCALCLASSPATH_element()

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None, \
        "Expected exception {!r} has not been raised".\
        format(testcase.exp_exc_types)

    assert result == exp_result


TESTCASES_LIST_OF_INSTANCE_ELEMENTS = [
    (
        "List of INSTANCE elements that is empty",
        dict(
            skip_events=1,
            xml_str=''
            '<DUMMY_ROOT>\n'
            '</DUMMY_ROOT>\n',
            exp_result=[],
        ),
        None, None, True
    ),
    (
        "List of INSTANCE elements with one item",
        dict(
            skip_events=1,
            xml_str=''
            '<DUMMY_ROOT>\n'
            '  <INSTANCE CLASSNAME="CIM_Foo"/>\n'
            '</DUMMY_ROOT>\n',
            exp_result=[
                CIMInstance('CIM_Foo'),
            ],
        ),
        None, None, True
    ),
    (
        "List of INSTANCE elements with two items",
        dict(
            skip_events=1,
            xml_str=''
            '<DUMMY_ROOT>\n'
            '  <INSTANCE CLASSNAME="CIM_Foo1"/>\n'
            '  <INSTANCE CLASSNAME="CIM_Foo2"/>\n'
            '</DUMMY_ROOT>\n',
            exp_result=[
                CIMInstance('CIM_Foo1'),
                CIMInstance('CIM_Foo2'),
            ],
        ),
        None, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_LIST_OF_INSTANCE_ELEMENTS)
@simplified_test_function
def test_list_of_INSTANCE_elements(
        testcase, skip_events, xml_str, exp_result):
    """
    Test CIMXMLParser.list_of_INSTANCE_elements().
    """

    parser = CIMXMLParser(xml_str)
    for _ in range(skip_events):
        parser.get_next_event()

    # Code to be tested
    result = parser.list_of_INSTANCE_elements()

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None, \
        "Expected exception {!r} has not been raised".\
        format(testcase.exp_exc_types)

    assert result == exp_result


TESTCASES_REQUIRED_INSTANCE_ELEMENT = [
    (
        "No INSTANCE but different element",
        dict(
            xml_str='<INSTANCE.XXX/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "INSTANCE with invalid child element",
        dict(
            xml_str=''
            '<INSTANCE CLASSNAME="CIM_Foo">\n'
            '  <XXX/>\n'
            '</INSTANCE>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "INSTANCE with invalid content text",
        dict(
            xml_str=''
            '<INSTANCE CLASSNAME="CIM_Foo">\n'
            '  xxx\n'
            '</INSTANCE>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "INSTANCE with invalid trailing text",
        dict(
            xml_str=''
            '<INSTANCE CLASSNAME="CIM_Foo">\n'
            '  <QUALIFIER NAME="Association" TYPE="boolean"/>\n'
            '  xxx\n'
            '</INSTANCE>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "INSTANCE with children in incorrect order",
        dict(
            xml_str=''
            '<INSTANCE CLASSNAME="CIM_Foo">\n'
            '  <PROPERTY NAME="Pstring" TYPE="string"/>\n'
            '  <QUALIFIER NAME="Association" TYPE="boolean"/>\n'
            '</INSTANCE>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "INSTANCE with missing required attribute CLASSNAME",
        dict(
            xml_str=''
            '<INSTANCE/>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "INSTANCE with CLASSNAME using ASCII characters",
        dict(
            xml_str=''
            '<INSTANCE CLASSNAME="CIM_Foo"/>\n',
            exp_result=CIMInstance('CIM_Foo'),
        ),
        None, None, True
    ),
    (
        "INSTANCE with CLASSNAME using non-ASCII UCS-2 characters",
        dict(
            xml_str=b''
            b'<INSTANCE CLASSNAME="CIM_Foo\xC3\xA9"/>\n',
            exp_result=CIMInstance(u'CIM_Foo\u00E9'),
        ),
        None, None, True
    ),
    (
        "INSTANCE with CLASSNAME using non-UCS-2 characters",
        dict(
            xml_str=b''
            b'<INSTANCE CLASSNAME="CIM_Foo\xF0\x90\x85\x82"/>\n',
            exp_result=CIMInstance(u'CIM_Foo\U00010142'),
        ),
        None, None, True
    ),
    (
        "INSTANCE without qualifiers or properties",
        dict(
            xml_str=''
            '<INSTANCE CLASSNAME="CIM_Foo"/>\n',
            exp_result=CIMInstance('CIM_Foo'),
        ),
        None, None, True
    ),
    (
        "INSTANCE with xml:lang attribute",
        dict(
            xml_str=''
            '<INSTANCE CLASSNAME="CIM_Foo" xml:lang="en_us"/>\n',
            exp_result=CIMInstance('CIM_Foo'),
        ),
        None, None, True
    ),
    (
        "INSTANCE with three properties",
        dict(
            xml_str=''
            '<INSTANCE CLASSNAME="CIM_Foo">\n'
            '  <PROPERTY NAME="Pstring" TYPE="string"/>\n'
            '  <PROPERTY.ARRAY NAME="Puint8array" TYPE="uint8"/>\n'
            '  <PROPERTY.REFERENCE NAME="Pref"/>\n'
            '</INSTANCE>\n',
            exp_result=CIMInstance(
                'CIM_Foo',
                properties=[
                    CIMProperty('Pstring', type='string', value=None,
                                propagated=False),
                    CIMProperty('Puint8array', type='uint8', value=None,
                                is_array=True, propagated=False),
                    CIMProperty('Pref', type='reference', value=None,
                                propagated=False),
                ],
            ),
        ),
        None, None, True
    ),
    (
        "INSTANCE with two qualifiers",
        dict(
            xml_str=''
            '<INSTANCE CLASSNAME="CIM_Foo">\n'
            '  <QUALIFIER NAME="Association" TYPE="boolean"/>\n'
            '  <QUALIFIER NAME="Abstract" TYPE="boolean"/>\n'
            '</INSTANCE>\n',
            exp_result=CIMInstance(
                'CIM_Foo',
                qualifiers=[
                    CIMQualifier('Association', value=None, type='boolean',
                                 **qualifier_default_attrs()),
                    CIMQualifier('Abstract', value=None, type='boolean',
                                 **qualifier_default_attrs()),
                ],
                properties=[],
            ),
        ),
        None, None, True
    ),
    (
        "INSTANCE with one qualifier and one property",
        dict(
            xml_str=''
            '<INSTANCE CLASSNAME="CIM_Foo">\n'
            '  <QUALIFIER NAME="Association" TYPE="boolean"/>\n'
            '  <PROPERTY NAME="Pstring" TYPE="string"/>\n'
            '</INSTANCE>\n',
            exp_result=CIMInstance(
                'CIM_Foo',
                qualifiers=[
                    CIMQualifier('Association', value=None, type='boolean',
                                 **qualifier_default_attrs()),
                ],
                properties=[
                    CIMProperty('Pstring', type='string', value=None,
                                propagated=False),
                ],
            ),
        ),
        None, None, True
    ),
    (
        "INSTANCE with one qualifier and one array property",
        dict(
            xml_str=''
            '<INSTANCE CLASSNAME="CIM_Foo">\n'
            '  <QUALIFIER NAME="Association" TYPE="boolean"/>\n'
            '  <PROPERTY.ARRAY NAME="Puint8array" TYPE="uint8"/>\n'
            '</INSTANCE>\n',
            exp_result=CIMInstance(
                'CIM_Foo',
                qualifiers=[
                    CIMQualifier('Association', value=None, type='boolean',
                                 **qualifier_default_attrs()),
                ],
                properties=[
                    CIMProperty('Puint8array', type='uint8', value=None,
                                is_array=True, propagated=False),
                ],
            ),
        ),
        None, None, True
    ),
    (
        "INSTANCE with one qualifier and one reference property",
        dict(
            xml_str=''
            '<INSTANCE CLASSNAME="CIM_Foo">\n'
            '  <QUALIFIER NAME="Association" TYPE="boolean"/>\n'
            '  <PROPERTY.REFERENCE NAME="Pref"/>\n'
            '</INSTANCE>\n',
            exp_result=CIMInstance(
                'CIM_Foo',
                qualifiers=[
                    CIMQualifier('Association', value=None, type='boolean',
                                 **qualifier_default_attrs()),
                ],
                properties=[
                    CIMProperty('Pref', type='reference', value=None,
                                propagated=False),
                ],
            ),
        ),
        None, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_REQUIRED_INSTANCE_ELEMENT)
@simplified_test_function
def test_required_INSTANCE_element(testcase, xml_str, exp_result):
    """
    Test CIMXMLParser.required_INSTANCE_element().
    """

    parser = CIMXMLParser(xml_str)

    # Code to be tested
    result = parser.required_INSTANCE_element()

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None, \
        "Expected exception {!r} has not been raised".\
        format(testcase.exp_exc_types)

    assert result == exp_result


TESTCASES_LIST_OF_INSTANCENAME_ELEMENTS = [
    (
        "List of INSTANCENAME elements that is empty",
        dict(
            skip_events=1,
            xml_str=''
            '<DUMMY_ROOT>\n'
            '</DUMMY_ROOT>\n',
            exp_result=[],
        ),
        None, None, True
    ),
    (
        "List of INSTANCENAME elements with one item",
        dict(
            skip_events=1,
            xml_str=''
            '<DUMMY_ROOT>\n'
            '  <INSTANCENAME CLASSNAME="CIM_Foo"/>\n'
            '</DUMMY_ROOT>\n',
            exp_result=[
                CIMInstanceName('CIM_Foo'),
            ],
        ),
        None, None, True
    ),
    (
        "List of INSTANCENAME elements with two items",
        dict(
            skip_events=1,
            xml_str=''
            '<DUMMY_ROOT>\n'
            '  <INSTANCENAME CLASSNAME="CIM_Foo1"/>\n'
            '  <INSTANCENAME CLASSNAME="CIM_Foo2"/>\n'
            '</DUMMY_ROOT>\n',
            exp_result=[
                CIMInstanceName('CIM_Foo1'),
                CIMInstanceName('CIM_Foo2'),
            ],
        ),
        None, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_LIST_OF_INSTANCENAME_ELEMENTS)
@simplified_test_function
def test_list_of_INSTANCENAME_elements(
        testcase, skip_events, xml_str, exp_result):
    """
    Test CIMXMLParser.list_of_INSTANCENAME_elements().
    """

    parser = CIMXMLParser(xml_str)
    for _ in range(skip_events):
        parser.get_next_event()

    # Code to be tested
    result = parser.list_of_INSTANCENAME_elements()

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None, \
        "Expected exception {!r} has not been raised".\
        format(testcase.exp_exc_types)

    assert result == exp_result


TESTCASES_REQUIRED_INSTANCENAME_ELEMENT = [
    (
        "No INSTANCENAME but different element",
        dict(
            xml_str='<INSTANCENAME.XXX/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "INSTANCENAME with invalid child element",
        dict(
            xml_str=''
            '<INSTANCENAME CLASSNAME="Foo">\n'
            '  <XXX/>\n'
            '</INSTANCENAME>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "INSTANCENAME with invalid content text",
        dict(
            xml_str=''
            '<INSTANCENAME CLASSNAME="Foo">\n'
            '  xxx\n'
            '</INSTANCENAME>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "INSTANCENAME with invalid trailing text",
        dict(
            xml_str=''
            '<INSTANCENAME CLASSNAME="Foo">\n'
            '  <KEYBINDING NAME="Name">\n'
            '    <KEYVALUE VALUETYPE="string">Foo</KEYVALUE>\n'
            '  </KEYBINDING>\n'
            '  xxx\n'
            '</INSTANCENAME>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "INSTANCENAME with missing required attribute CLASSNAME",
        dict(
            xml_str=''
            '<INSTANCENAME/>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "INSTANCENAME with CLASSNAME using ASCII characters",
        dict(
            xml_str=''
            '<INSTANCENAME CLASSNAME="CIM_Foo"/>\n',
            exp_result=CIMInstanceName('CIM_Foo'),
        ),
        None, None, True
    ),
    (
        "INSTANCENAME with CLASSNAME using non-ASCII UCS-2 characters",
        dict(
            xml_str=b''
            b'<INSTANCENAME CLASSNAME="CIM_Foo\xC3\xA9"/>\n',
            exp_result=CIMInstanceName(u'CIM_Foo\u00E9'),
        ),
        None, None, True
    ),
    (
        "INSTANCENAME with CLASSNAME using non-UCS-2 characters",
        dict(
            xml_str=b''
            b'<INSTANCENAME CLASSNAME="CIM_Foo\xF0\x90\x85\x82"/>\n',
            exp_result=CIMInstanceName(u'CIM_Foo\U00010142'),
        ),
        None, None, True
    ),
    (
        "INSTANCENAME with KEYBINDING for two string keys",
        dict(
            xml_str=''
            '<INSTANCENAME CLASSNAME="CIM_Foo">\n'
            '  <KEYBINDING NAME="Name">\n'
            '    <KEYVALUE VALUETYPE="string">Foo</KEYVALUE>\n'
            '  </KEYBINDING>\n'
            '  <KEYBINDING NAME="Chicken">\n'
            '    <KEYVALUE VALUETYPE="string">Ham</KEYVALUE>\n'
            '  </KEYBINDING>\n'
            '</INSTANCENAME>\n',
            exp_result=CIMInstanceName(
                'CIM_Foo',
                keybindings=[
                    ('Name', 'Foo'),
                    ('Chicken', 'Ham'),
                ],
            ),
        ),
        None, None, True
    ),
    (
        "INSTANCENAME with KEYBINDING for various typed keys",
        dict(
            xml_str=''
            '<INSTANCENAME CLASSNAME="CIM_Foo">\n'
            '  <KEYBINDING NAME="Name">\n'
            '    <KEYVALUE VALUETYPE="string">Foo</KEYVALUE>\n'
            '  </KEYBINDING>\n'
            '  <KEYBINDING NAME="Number">\n'
            '    <KEYVALUE VALUETYPE="numeric">42</KEYVALUE>\n'
            '  </KEYBINDING>\n'
            '  <KEYBINDING NAME="Boolean">\n'
            '    <KEYVALUE VALUETYPE="boolean">FALSE</KEYVALUE>\n'
            '  </KEYBINDING>\n'
            '  <KEYBINDING NAME="Ref">\n'
            '    <VALUE.REFERENCE>\n'
            '      <INSTANCENAME CLASSNAME="CIM_Bar"/>\n'
            '    </VALUE.REFERENCE>\n'
            '  </KEYBINDING>\n'
            '</INSTANCENAME>\n',
            exp_result=CIMInstanceName(
                'CIM_Foo',
                keybindings=[
                    ('Name', 'Foo'),
                    ('Number', 42),
                    ('Boolean', False),
                    ('Ref', CIMInstanceName('CIM_Bar')),
                ],
            ),
        ),
        None, None, True
    ),
    (
        "INSTANCENAME with KEYVALUE for one key (unnamed key)",
        dict(
            xml_str=''
            '<INSTANCENAME CLASSNAME="CIM_Foo">\n'
            '  <KEYVALUE VALUETYPE="string">Foo</KEYVALUE>\n'
            '</INSTANCENAME>\n',
            exp_result=CIMInstanceName(
                'CIM_Foo',
                keybindings=[
                    (None, 'Foo'),
                ],
            ),
        ),
        None, None, True
    ),
    (
        "INSTANCENAME with KEYVALUE for two string keys (invalid)",
        dict(
            xml_str=''
            '<INSTANCENAME CLASSNAME="CIM_Foo">\n'
            '  <KEYVALUE VALUETYPE="string">Foo</KEYVALUE>\n'
            '  <KEYVALUE VALUETYPE="string">Bar</KEYVALUE>\n'
            '</INSTANCENAME>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "INSTANCENAME with VALUE.REFERENCE for one ref. key (unnamed key)",
        dict(
            xml_str=''
            '<INSTANCENAME CLASSNAME="CIM_Foo">\n'
            '  <VALUE.REFERENCE>\n'
            '    <INSTANCENAME CLASSNAME="CIM_Bar"/>\n'
            '  </VALUE.REFERENCE>\n'
            '</INSTANCENAME>\n',
            exp_result=CIMInstanceName(
                'CIM_Foo',
                keybindings=[
                    (None, CIMInstanceName('CIM_Bar')),
                ],
            ),
        ),
        None, None, True
    ),
    (
        "INSTANCENAME with VALUE.REFERENCE for two reference keys (invalid)",
        dict(
            xml_str=''
            '<INSTANCENAME CLASSNAME="CIM_Foo">\n'
            '  <VALUE.REFERENCE>\n'
            '    <INSTANCENAME CLASSNAME="CIM_Bar"/>\n'
            '  </VALUE.REFERENCE>\n'
            '  <VALUE.REFERENCE>\n'
            '    <INSTANCENAME CLASSNAME="CIM_Baz"/>\n'
            '  </VALUE.REFERENCE>\n'
            '</INSTANCENAME>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_REQUIRED_INSTANCENAME_ELEMENT)
@simplified_test_function
def test_required_INSTANCENAME_element(testcase, xml_str, exp_result):
    """
    Test CIMXMLParser.required_INSTANCENAME_element().
    """

    parser = CIMXMLParser(xml_str)

    # Code to be tested
    result = parser.required_INSTANCENAME_element()

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None, \
        "Expected exception {!r} has not been raised".\
        format(testcase.exp_exc_types)

    assert result == exp_result


TESTCASES_LIST_OF_INSTANCEPATH_ELEMENTS = [
    (
        "List of INSTANCEPATH elements that is empty",
        dict(
            skip_events=1,
            xml_str=''
            '<DUMMY_ROOT>\n'
            '</DUMMY_ROOT>\n',
            exp_result=[],
        ),
        None, None, True
    ),
    (
        "List of INSTANCEPATH elements with one item",
        dict(
            skip_events=1,
            xml_str=''
            '<DUMMY_ROOT>\n'
            '  <INSTANCEPATH>\n'
            '    <NAMESPACEPATH>\n'
            '      <HOST>woot.com</HOST>\n'
            '      <LOCALNAMESPACEPATH>\n'
            '        <NAMESPACE NAME="foo"/>\n'
            '      </LOCALNAMESPACEPATH>\n'
            '    </NAMESPACEPATH>\n'
            '    <INSTANCENAME CLASSNAME="CIM_Foo"/>\n'
            '  </INSTANCEPATH>\n'
            '</DUMMY_ROOT>\n',
            exp_result=[
                CIMInstanceName(
                    'CIM_Foo',
                    namespace='foo',
                    host='woot.com',
                ),
            ],
        ),
        None, None, True
    ),
    (
        "List of INSTANCEPATH elements with two items",
        dict(
            skip_events=1,
            xml_str=''
            '<DUMMY_ROOT>\n'
            '  <INSTANCEPATH>\n'
            '    <NAMESPACEPATH>\n'
            '      <HOST>woot.com</HOST>\n'
            '      <LOCALNAMESPACEPATH>\n'
            '        <NAMESPACE NAME="foo1"/>\n'
            '      </LOCALNAMESPACEPATH>\n'
            '    </NAMESPACEPATH>\n'
            '    <INSTANCENAME CLASSNAME="CIM_Foo1"/>\n'
            '  </INSTANCEPATH>\n'
            '  <INSTANCEPATH>\n'
            '    <NAMESPACEPATH>\n'
            '      <HOST>woot.com</HOST>\n'
            '      <LOCALNAMESPACEPATH>\n'
            '        <NAMESPACE NAME="foo2"/>\n'
            '      </LOCALNAMESPACEPATH>\n'
            '    </NAMESPACEPATH>\n'
            '    <INSTANCENAME CLASSNAME="CIM_Foo2"/>\n'
            '  </INSTANCEPATH>\n'
            '</DUMMY_ROOT>\n',
            exp_result=[
                CIMInstanceName(
                    'CIM_Foo1',
                    namespace='foo1',
                    host='woot.com',
                ),
                CIMInstanceName(
                    'CIM_Foo2',
                    namespace='foo2',
                    host='woot.com',
                ),
            ],
        ),
        None, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_LIST_OF_INSTANCEPATH_ELEMENTS)
@simplified_test_function
def test_list_of_INSTANCEPATH_elements(
        testcase, skip_events, xml_str, exp_result):
    """
    Test CIMXMLParser.list_of_INSTANCEPATH_elements().
    """

    parser = CIMXMLParser(xml_str)
    for _ in range(skip_events):
        parser.get_next_event()

    # Code to be tested
    result = parser.list_of_INSTANCEPATH_elements()

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None, \
        "Expected exception {!r} has not been raised".\
        format(testcase.exp_exc_types)

    assert result == exp_result


TESTCASES_REQUIRED_INSTANCEPATH_ELEMENT = [
    (
        "INSTANCEPATH with invalid child element",
        dict(
            xml_str=''
            '<INSTANCEPATH>\n'
            '  <NAMESPACEPATH>\n'
            '    <HOST>woot.com</HOST>\n'
            '    <LOCALNAMESPACEPATH>\n'
            '      <NAMESPACE NAME="foo"/>\n'
            '    </LOCALNAMESPACEPATH>\n'
            '  </NAMESPACEPATH>\n'
            '  <INSTANCENAME CLASSNAME="CIM_Foo"/>\n'
            '  <XXX/>\n'
            '</INSTANCEPATH>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "INSTANCEPATH with invalid content text",
        dict(
            xml_str=''
            '<INSTANCEPATH>\n'
            '  xxx\n'
            '  <NAMESPACEPATH>\n'
            '    <HOST>woot.com</HOST>\n'
            '    <LOCALNAMESPACEPATH>\n'
            '      <NAMESPACE NAME="foo"/>\n'
            '    </LOCALNAMESPACEPATH>\n'
            '  </NAMESPACEPATH>\n'
            '  <INSTANCENAME CLASSNAME="CIM_Foo"/>\n'
            '</INSTANCEPATH>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "INSTANCEPATH with invalid trailing text",
        dict(
            xml_str=''
            '<INSTANCEPATH>\n'
            '  <NAMESPACEPATH>\n'
            '    <HOST>woot.com</HOST>\n'
            '    <LOCALNAMESPACEPATH>\n'
            '      <NAMESPACE NAME="foo"/>\n'
            '    </LOCALNAMESPACEPATH>\n'
            '  </NAMESPACEPATH>\n'
            '  <INSTANCENAME CLASSNAME="CIM_Foo"/>\n'
            '  xxx\n'
            '</INSTANCEPATH>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "INSTANCEPATH with missing children",
        dict(
            xml_str=''
            '<INSTANCEPATH/>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "INSTANCEPATH with missing child NAMESPACEPATH",
        dict(
            xml_str=''
            '<INSTANCEPATH>\n'
            '  <INSTANCENAME CLASSNAME="CIM_Foo"/>\n'
            '</INSTANCEPATH>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "INSTANCEPATH with missing child INSTANCENAME",
        dict(
            xml_str=''
            '<INSTANCEPATH>\n'
            '  <NAMESPACEPATH>\n'
            '    <HOST>woot.com</HOST>\n'
            '    <LOCALNAMESPACEPATH>\n'
            '      <NAMESPACE NAME="foo"/>\n'
            '    </LOCALNAMESPACEPATH>\n'
            '  </NAMESPACEPATH>\n'
            '</INSTANCEPATH>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "INSTANCEPATH with children in incorrect order",
        dict(
            xml_str=''
            '<INSTANCEPATH>\n'
            '  <INSTANCENAME CLASSNAME="CIM_Foo"/>\n'
            '  <NAMESPACEPATH>\n'
            '    <HOST>woot.com</HOST>\n'
            '    <LOCALNAMESPACEPATH>\n'
            '      <NAMESPACE NAME="foo"/>\n'
            '    </LOCALNAMESPACEPATH>\n'
            '  </NAMESPACEPATH>\n'
            '</INSTANCEPATH>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "INSTANCEPATH (normal case)",
        dict(
            xml_str=''
            '<INSTANCEPATH>\n'
            '  <NAMESPACEPATH>\n'
            '    <HOST>woot.com</HOST>\n'
            '    <LOCALNAMESPACEPATH>\n'
            '      <NAMESPACE NAME="foo"/>\n'
            '    </LOCALNAMESPACEPATH>\n'
            '  </NAMESPACEPATH>\n'
            '  <INSTANCENAME CLASSNAME="CIM_Foo"/>\n'
            '</INSTANCEPATH>\n',
            exp_result=CIMInstanceName(
                'CIM_Foo',
                namespace='foo',
                host='woot.com',
            ),
        ),
        None, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_REQUIRED_INSTANCEPATH_ELEMENT)
@simplified_test_function
def test_required_INSTANCEPATH_element(testcase, xml_str, exp_result):
    """
    Test CIMXMLParser.required_INSTANCEPATH_element().
    """

    parser = CIMXMLParser(xml_str)

    # Code to be tested
    result = parser.required_INSTANCEPATH_element()

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None, \
        "Expected exception {!r} has not been raised".\
        format(testcase.exp_exc_types)

    assert result == exp_result


TESTCASES_REQUIRED_LOCALINSTANCEPATH_ELEMENT = [
    (
        "No LOCALINSTANCEPATH but different element",
        dict(
            xml_str='<LOCALINSTANCEPATH.XXX/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "LOCALINSTANCEPATH with invalid child element",
        dict(
            xml_str=''
            '<LOCALINSTANCEPATH>\n'
            '  <LOCALNAMESPACEPATH>\n'
            '    <NAMESPACE NAME="foo"/>\n'
            '  </LOCALNAMESPACEPATH>\n'
            '  <INSTANCENAME CLASSNAME="CIM_Foo"/>\n'
            '  <XXX/>\n'
            '</LOCALINSTANCEPATH>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "LOCALINSTANCEPATH with invalid content text",
        dict(
            xml_str=''
            '<LOCALINSTANCEPATH>\n'
            '  xxx\n'
            '  <LOCALNAMESPACEPATH>\n'
            '    <NAMESPACE NAME="foo"/>\n'
            '  </LOCALNAMESPACEPATH>\n'
            '  <INSTANCENAME CLASSNAME="CIM_Foo"/>\n'
            '</LOCALINSTANCEPATH>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "LOCALINSTANCEPATH with invalid trailing text",
        dict(
            xml_str=''
            '<LOCALINSTANCEPATH>\n'
            '  <LOCALNAMESPACEPATH>\n'
            '    <NAMESPACE NAME="foo"/>\n'
            '  </LOCALNAMESPACEPATH>\n'
            '  <INSTANCENAME CLASSNAME="CIM_Foo"/>\n'
            '  xxx\n'
            '</LOCALINSTANCEPATH>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "LOCALINSTANCEPATH with missing children",
        dict(
            xml_str=''
            '<LOCALINSTANCEPATH/>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "LOCALINSTANCEPATH with missing child LOCALNAMESPACEPATH",
        dict(
            xml_str=''
            '<LOCALINSTANCEPATH>\n'
            '  <INSTANCENAME CLASSNAME="CIM_Foo"/>\n'
            '</LOCALINSTANCEPATH>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "LOCALINSTANCEPATH with missing child INSTANCENAME",
        dict(
            xml_str=''
            '<LOCALINSTANCEPATH>\n'
            '  <LOCALNAMESPACEPATH>\n'
            '    <NAMESPACE NAME="foo"/>\n'
            '  </LOCALNAMESPACEPATH>\n'
            '</LOCALINSTANCEPATH>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "LOCALINSTANCEPATH with children in incorrect order",
        dict(
            xml_str=''
            '<LOCALINSTANCEPATH>\n'
            '  <INSTANCENAME CLASSNAME="CIM_Foo"/>\n'
            '  <LOCALNAMESPACEPATH>\n'
            '    <NAMESPACE NAME="foo"/>\n'
            '  </LOCALNAMESPACEPATH>\n'
            '</LOCALINSTANCEPATH>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "LOCALINSTANCEPATH (normal case)",
        dict(
            xml_str=''
            '<LOCALINSTANCEPATH>\n'
            '  <LOCALNAMESPACEPATH>\n'
            '    <NAMESPACE NAME="foo"/>\n'
            '  </LOCALNAMESPACEPATH>\n'
            '  <INSTANCENAME CLASSNAME="CIM_Foo"/>\n'
            '</LOCALINSTANCEPATH>\n',
            exp_result=CIMInstanceName(
                'CIM_Foo',
                namespace='foo',
            ),
        ),
        None, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_REQUIRED_LOCALINSTANCEPATH_ELEMENT)
@simplified_test_function
def test_required_LOCALINSTANCEPATH_element(testcase, xml_str, exp_result):
    """
    Test CIMXMLParser.required_LOCALINSTANCEPATH_element().
    """

    parser = CIMXMLParser(xml_str)

    # Code to be tested
    result = parser.required_LOCALINSTANCEPATH_element()

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None, \
        "Expected exception {!r} has not been raised".\
        format(testcase.exp_exc_types)

    assert result == exp_result


TESTCASES_REQUIRED_NAMESPACEPATH_ELEMENT = [
    (
        "NAMESPACEPATH with invalid child element",
        dict(
            xml_str=''
            '<NAMESPACEPATH>\n'
            '  <HOST>woot.com</HOST>\n'
            '  <LOCALNAMESPACEPATH>\n'
            '    <NAMESPACE NAME="foo"/>\n'
            '  </LOCALNAMESPACEPATH>\n'
            '  <XXX/>\n'
            '</NAMESPACEPATH>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "NAMESPACEPATH with invalid content text",
        dict(
            xml_str=''
            '<NAMESPACEPATH>\n'
            '  xxx\n'
            '  <HOST>woot.com</HOST>\n'
            '  <LOCALNAMESPACEPATH>\n'
            '    <NAMESPACE NAME="foo"/>\n'
            '  </LOCALNAMESPACEPATH>\n'
            '</NAMESPACEPATH>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "NAMESPACEPATH with invalid trailing text",
        dict(
            xml_str=''
            '<NAMESPACEPATH>\n'
            '  <HOST>woot.com</HOST>\n'
            '  <LOCALNAMESPACEPATH>\n'
            '    <NAMESPACE NAME="foo"/>\n'
            '  </LOCALNAMESPACEPATH>\n'
            '  xxx\n'
            '</NAMESPACEPATH>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "NAMESPACEPATH with missing children",
        dict(
            xml_str=''
            '<NAMESPACEPATH/>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "NAMESPACEPATH with missing child HOST",
        dict(
            xml_str=''
            '<NAMESPACEPATH>\n'
            '  <LOCALNAMESPACEPATH>\n'
            '    <NAMESPACE NAME="foo"/>\n'
            '  </LOCALNAMESPACEPATH>\n'
            '</NAMESPACEPATH>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "NAMESPACEPATH with missing child LOCALNAMESPACEPATH",
        dict(
            xml_str=''
            '<NAMESPACEPATH>\n'
            '  <HOST>woot.com</HOST>\n'
            '</NAMESPACEPATH>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "NAMESPACEPATH with children in incorrect order",
        dict(
            xml_str=''
            '<NAMESPACEPATH>\n'
            '  <LOCALNAMESPACEPATH>\n'
            '    <NAMESPACE NAME="foo"/>\n'
            '  </LOCALNAMESPACEPATH>\n'
            '  <HOST>woot.com</HOST>\n'
            '</NAMESPACEPATH>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "NAMESPACEPATH (normal case)",
        dict(
            xml_str=''
            '<NAMESPACEPATH>\n'
            '  <HOST>woot.com</HOST>\n'
            '  <LOCALNAMESPACEPATH>\n'
            '    <NAMESPACE NAME="foo"/>\n'
            '  </LOCALNAMESPACEPATH>\n'
            '</NAMESPACEPATH>\n',
            exp_result=('woot.com', 'foo'),
        ),
        None, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_REQUIRED_NAMESPACEPATH_ELEMENT)
@simplified_test_function
def test_required_NAMESPACEPATH_element(testcase, xml_str, exp_result):
    """
    Test CIMXMLParser.required_NAMESPACEPATH_element().
    """

    parser = CIMXMLParser(xml_str)

    # Code to be tested
    result = parser.required_NAMESPACEPATH_element()

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None, \
        "Expected exception {!r} has not been raised".\
        format(testcase.exp_exc_types)

    assert result == exp_result


TESTCASES_REQUIRED_LOCALNAMESPACEPATH_ELEMENT = [

    # Testcases focusing on the LOCALNAMESPACEPATH element and NAMESPACE list
    (
        "LOCALNAMESPACEPATH with invalid child element",
        dict(
            xml_str=''
            '<LOCALNAMESPACEPATH>\n'
            '  <XXX/>\n'
            '</LOCALNAMESPACEPATH>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "LOCALNAMESPACEPATH with invalid content text",
        dict(
            xml_str=''
            '<LOCALNAMESPACEPATH>\n'
            '  xxx\n'
            '  <NAMESPACE NAME="foo"/>\n'
            '</LOCALNAMESPACEPATH>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "LOCALNAMESPACEPATH with invalid trailing text",
        dict(
            xml_str=''
            '<LOCALNAMESPACEPATH>\n'
            '  <NAMESPACE NAME="foo"/>\n'
            '  xxx\n'
            '</LOCALNAMESPACEPATH>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "LOCALNAMESPACEPATH with no namespace component",
        dict(
            xml_str=''
            '<LOCALNAMESPACEPATH/>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "LOCALNAMESPACEPATH with one namespace component",
        dict(
            xml_str=''
            '<LOCALNAMESPACEPATH>\n'
            '  <NAMESPACE NAME="foo"/>\n'
            '</LOCALNAMESPACEPATH>\n',
            exp_result='foo',
        ),
        None, None, True
    ),
    (
        "LOCALNAMESPACEPATH with two namespace components",
        dict(
            xml_str=''
            '<LOCALNAMESPACEPATH>\n'
            '  <NAMESPACE NAME="foo"/>\n'
            '  <NAMESPACE NAME="com"/>\n'
            '</LOCALNAMESPACEPATH>\n',
            exp_result='foo/com',
        ),
        None, None, True
    ),

    # Testcases focusing on a NAMESPACE within the LOCALNAMESPACEPATH element
    (
        "LOCALNAMESPACEPATH with NAMESPACE with invalid child element",
        dict(
            xml_str=''
            '<LOCALNAMESPACEPATH>\n'
            '  <NAMESPACE NAME="a">\n'
            '    <XXX/>\n'
            '  </NAMESPACE>\n'
            '</LOCALNAMESPACEPATH>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "LOCALNAMESPACEPATH with NAMESPACE with invalid content text",
        dict(
            xml_str=''
            '<LOCALNAMESPACEPATH>\n'
            '  <NAMESPACE NAME="a">xxx</NAMESPACE>\n'
            '</LOCALNAMESPACEPATH>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "LOCALNAMESPACEPATH with NAMESPACE with missing required "
        "attribute NAME",
        dict(
            xml_str=''
            '<LOCALNAMESPACEPATH>\n'
            '  <NAMESPACE/>\n'
            '</LOCALNAMESPACEPATH>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "LOCALNAMESPACEPATH with NAMESPACE with NAME using ASCII characters",
        dict(
            xml_str=''
            '<LOCALNAMESPACEPATH>\n'
            '  <NAMESPACE NAME="foo"/>\n'
            '</LOCALNAMESPACEPATH>\n',
            exp_result=u'foo',
        ),
        None, None, True
    ),
    (
        "LOCALNAMESPACEPATH with NAMESPACE with NAME using non-ASCII UCS-2 "
        "characters",
        dict(
            xml_str=b''
            b'<LOCALNAMESPACEPATH>\n'
            b'  <NAMESPACE NAME="foo\xC3\xA9"/>\n'
            b'</LOCALNAMESPACEPATH>\n',
            exp_result=u'foo\u00E9',
        ),
        None, None, True
    ),
    (
        "LOCALNAMESPACEPATH with NAMESPACE with NAME using non-UCS-2 "
        "characters",
        dict(
            xml_str=b''
            b'<LOCALNAMESPACEPATH>\n'
            b'  <NAMESPACE NAME="foo\xF0\x90\x85\x82"/>\n'
            b'</LOCALNAMESPACEPATH>\n',
            exp_result=u'foo\U00010142',
        ),
        None, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_REQUIRED_LOCALNAMESPACEPATH_ELEMENT)
@simplified_test_function
def test_required_LOCALNAMESPACEPATH_element(testcase, xml_str, exp_result):
    """
    Test CIMXMLParser.required_LOCALNAMESPACEPATH_element().
    """

    parser = CIMXMLParser(xml_str)

    # Code to be tested
    result = parser.required_LOCALNAMESPACEPATH_element()

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None, \
        "Expected exception {!r} has not been raised".\
        format(testcase.exp_exc_types)

    assert result == exp_result


TESTCASES_REQUIRED_HOST_ELEMENT = [
    (
        "HOST with invalid child element",
        dict(
            xml_str='<HOST>woot.com<XXX/></HOST>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "HOST with DNS host name without port",
        dict(
            xml_str='<HOST>woot.com</HOST>\n',
            exp_result=u'woot.com',
        ),
        None, None, True
    ),
    (
        "HOST with DNS host name with port",
        dict(
            xml_str='<HOST>woot.com:1234</HOST>\n',
            exp_result=u'woot.com:1234',
        ),
        None, None, True
    ),
    (
        "HOST with short host name without port",
        dict(
            xml_str='<HOST>woot</HOST>\n',
            exp_result=u'woot',
        ),
        None, None, True
    ),
    (
        "HOST with IPv4 address without port",
        dict(
            xml_str='<HOST>10.11.12.13</HOST>\n',
            exp_result=u'10.11.12.13',
        ),
        None, None, True
    ),
    (
        "HOST with IPv4 address with port",
        dict(
            xml_str='<HOST>10.11.12.13:1</HOST>\n',
            exp_result=u'10.11.12.13:1',
        ),
        None, None, True
    ),
    (
        "HOST with IPv6 address without port",
        dict(
            xml_str='<HOST>[ff::aa]</HOST>\n',
            exp_result=u'[ff::aa]',
        ),
        None, None, True
    ),
    (
        "HOST with IPv6 address with port",
        dict(
            xml_str='<HOST>[ff::aa]:1234</HOST>\n',
            exp_result=u'[ff::aa]:1234',
        ),
        None, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_REQUIRED_HOST_ELEMENT)
@simplified_test_function
def test_required_HOST_element(testcase, xml_str, exp_result):
    """
    Test CIMXMLParser.required_HOST_element().
    """

    parser = CIMXMLParser(xml_str)

    # Code to be tested
    result = parser.required_HOST_element()

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None, \
        "Expected exception {!r} has not been raised".\
        format(testcase.exp_exc_types)

    assert result == exp_result


TESTCASES_REQUIRED_PROPERTY_ELEMENT = [
    (
        "PROPERTY but different element",
        dict(
            xml_str='<PROPERTY.XXX/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PROPERTY with invalid child element",
        dict(
            xml_str=''
            '<PROPERTY NAME="Foo" TYPE="string">\n'
            '  <XXX/>\n'
            '</PROPERTY>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PROPERTY with invalid content text",
        dict(
            xml_str=''
            '<PROPERTY NAME="Foo" TYPE="string">\n'
            '  xxx\n'
            '  <QUALIFIER NAME="Qual" TYPE="boolean"/>\n'
            '</PROPERTY>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PROPERTY with invalid trailing text",
        dict(
            xml_str=''
            '<PROPERTY NAME="Foo" TYPE="string">\n'
            '  <QUALIFIER NAME="Qual" TYPE="boolean"/>\n'
            '  xxx\n'
            '</PROPERTY>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PROPERTY with children in incorrect order",
        dict(
            xml_str=''
            '<PROPERTY NAME="Foo" TYPE="string">\n'
            '  <VALUE>abc</VALUE>\n'
            '  <QUALIFIER NAME="Qual" TYPE="boolean"/>\n'
            '</PROPERTY>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PROPERTY with missing required attribute NAME",
        dict(
            xml_str=''
            '<PROPERTY TYPE="string"/>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PROPERTY with NAME using ASCII characters",
        dict(
            xml_str=''
            '<PROPERTY NAME="Foo" TYPE="string"/>\n',
            exp_result=CIMProperty('Foo', value=None, type='string',
                                   propagated=False),
        ),
        None, None, True
    ),
    (
        "PROPERTY with NAME using non-ASCII UCS-2 characters",
        dict(
            xml_str=b''
            b'<PROPERTY NAME="Foo\xC3\xA9" TYPE="string"/>\n',
            exp_result=CIMProperty(u'Foo\u00E9', value=None, type='string',
                                   propagated=False),
        ),
        None, None, True
    ),
    (
        "PROPERTY with NAME using non-UCS-2 characters",
        dict(
            xml_str=b''
            b'<PROPERTY NAME="Foo\xF0\x90\x85\x82" TYPE="string"/>\n',
            exp_result=CIMProperty(u'Foo\U00010142', value=None, type='string',
                                   propagated=False),
        ),
        None, None, True
    ),
    (
        "PROPERTY with xml:lang attribute",
        dict(
            xml_str=''
            '<PROPERTY NAME="Foo" TYPE="string" xml:lang="en_us"/>\n',
            exp_result=CIMProperty('Foo', value=None, type='string',
                                   propagated=False),
        ),
        None, None, True
    ),
    (
        "PROPERTY with CLASSORIGIN and PROPAGATED attributes",
        dict(
            xml_str=''
            '<PROPERTY NAME="Foo" TYPE="string" CLASSORIGIN="CIM_Foo"'
            ' PROPAGATED="true"/>\n',
            exp_result=CIMProperty('Foo', value=None, type='string',
                                   class_origin='CIM_Foo', propagated=True),
        ),
        None, None, True
    ),
    (
        "PROPERTY with missing required attribute TYPE",
        dict(
            xml_str=''
            '<PROPERTY NAME="Foo"/>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PROPERTY with string typed value that is None",
        dict(
            xml_str=''
            '<PROPERTY NAME="Foo" TYPE="string"/>\n',
            exp_result=CIMProperty('Foo', None, type='string',
                                   propagated=False),
        ),
        None, None, True
    ),
    (
        "PROPERTY with string typed value that is empty",
        dict(
            xml_str=''
            '<PROPERTY NAME="Foo" TYPE="string">\n'
            '  <VALUE></VALUE>\n'
            '</PROPERTY>\n',
            exp_result=CIMProperty('Foo', value='', type='string',
                                   propagated=False),
        ),
        None, None, True
    ),
    (
        "PROPERTY with string typed value with ASCII characters",
        dict(
            xml_str=''
            '<PROPERTY NAME="Spotty" TYPE="string">\n'
            '  <VALUE>Foot</VALUE>\n'
            '</PROPERTY>\n',
            exp_result=CIMProperty('Spotty', value='Foot', type='string',
                                   propagated=False),
        ),
        None, None, True
    ),
    (
        "PROPERTY with string typed value with non-ASCII UCS-2 characters",
        dict(
            xml_str=b''
            b'<PROPERTY NAME="Spotty" TYPE="string">\n'
            b'  <VALUE>\xC3\xA9</VALUE>\n'
            b'</PROPERTY>\n',
            exp_result=CIMProperty('Spotty', value=u'\u00E9', type='string',
                                   propagated=False),
        ),
        None, None, True
    ),
    (
        "PROPERTY with string typed value with non-UCS-2 characters",
        dict(
            xml_str=b''
            b'<PROPERTY NAME="Spotty" TYPE="string">\n'
            b'  <VALUE>\xF0\x90\x85\x82</VALUE>\n'
            b'</PROPERTY>\n',
            exp_result=CIMProperty('Spotty', value=u'\U00010142', type='string',
                                   propagated=False),
        ),
        None, None, True
    ),
    (
        "PROPERTY with char16 typed value that is None",
        dict(
            xml_str=''
            '<PROPERTY NAME="Foo" TYPE="char16"/>\n',
            exp_result=CIMProperty('Foo', value=None, type='char16',
                                   propagated=False),
        ),
        None, None, True
    ),
    (
        "PROPERTY with char16 typed value with ASCII character",
        dict(
            xml_str=''
            '<PROPERTY NAME="Spotty" TYPE="char16">\n'
            '  <VALUE>F</VALUE>\n'
            '</PROPERTY>\n',
            exp_result=CIMProperty('Spotty', value='F', type='char16',
                                   propagated=False),
        ),
        None, None, True
    ),
    (
        "PROPERTY with char16 typed value with non-ASCII UCS-2 character",
        dict(
            xml_str=b''
            b'<PROPERTY NAME="Spotty" TYPE="char16">\n'
            b'  <VALUE>\xC3\xA9</VALUE>\n'
            b'</PROPERTY>\n',
            exp_result=CIMProperty('Spotty', value=u'\u00E9', type='char16',
                                   propagated=False),
        ),
        None, None, True
    ),
    (
        "PROPERTY with char16 typed value with non-UCS-2 character",
        dict(
            xml_str=b''
            b'<PROPERTY NAME="Spotty" TYPE="char16">\n'
            b'  <VALUE>\xF0\x90\x85\x82</VALUE>\n'
            b'</PROPERTY>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PROPERTY with uint8 typed value that is None",
        dict(
            xml_str=''
            '<PROPERTY NAME="Foo" TYPE="uint8"/>\n',
            exp_result=CIMProperty('Foo', value=None, type='uint8',
                                   propagated=False),
        ),
        None, None, True
    ),
    (
        "PROPERTY with uint8 typed value (decimal value)",
        dict(
            xml_str=''
            '<PROPERTY NAME="Age" TYPE="uint8">\n'
            '  <VALUE>42</VALUE>\n'
            '</PROPERTY>\n',
            exp_result=CIMProperty('Age', Uint8(42), propagated=False),
        ),
        None, None, True
    ),
    (
        "PROPERTY with uint8 typed value (decimal value with plus)",
        dict(
            xml_str=''
            '<PROPERTY NAME="Age" TYPE="uint8">\n'
            '  <VALUE>+42</VALUE>\n'
            '</PROPERTY>\n',
            exp_result=CIMProperty('Age', Uint8(42), propagated=False),
        ),
        None, None, True
    ),
    (
        "PROPERTY with uint8 typed value (hex value)",
        dict(
            xml_str=''
            '<PROPERTY NAME="Age" TYPE="uint8">\n'
            '  <VALUE>0x42</VALUE>\n'
            '</PROPERTY>\n',
            exp_result=CIMProperty('Age', Uint8(0x42), propagated=False),
        ),
        None, None, True
    ),
    (
        "PROPERTY with uint8 typed value (hex value with 0X in upper case)",
        dict(
            xml_str=''
            '<PROPERTY NAME="Age" TYPE="uint8">\n'
            '  <VALUE>0X42</VALUE>\n'
            '</PROPERTY>\n',
            exp_result=CIMProperty('Age', Uint8(0x42), propagated=False),
        ),
        None, None, True
    ),
    (
        "PROPERTY with uint8 typed value (hex value with plus)",
        dict(
            xml_str=''
            '<PROPERTY NAME="Age" TYPE="uint8">\n'
            '  <VALUE>+0x42</VALUE>\n'
            '</PROPERTY>\n',
            exp_result=CIMProperty('Age', Uint8(0x42), propagated=False),
        ),
        None, None, True
    ),
    (
        "PROPERTY with uint8 typed value (decimal value with WS)",
        dict(
            xml_str=''
            '<PROPERTY NAME="Age" TYPE="uint8">\n'
            '  <VALUE>  42  </VALUE>\n'
            '</PROPERTY>\n',
            exp_result=CIMProperty('Age', Uint8(42), propagated=False),
        ),
        None, None, True
    ),
    (
        "PROPERTY with uint8 typed value (invalid value: just WS)",
        dict(
            xml_str=''
            '<PROPERTY NAME="Age" TYPE="uint8">\n'
            '  <VALUE>  </VALUE>\n'
            '</PROPERTY>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PROPERTY with uint8 typed value (invalid value: empty)",
        dict(
            xml_str=''
            '<PROPERTY NAME="Age" TYPE="uint8">\n'
            '  <VALUE></VALUE>\n'
            '</PROPERTY>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PROPERTY with uint8 typed value (invalid value: letters)",
        dict(
            xml_str=''
            '<PROPERTY NAME="Age" TYPE="uint8">\n'
            '  <VALUE>abc</VALUE>\n'
            '</PROPERTY>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PROPERTY with uint8 typed value (minimum)",
        dict(
            xml_str=''
            '<PROPERTY NAME="Age" TYPE="uint8">\n'
            '  <VALUE>0</VALUE>\n'
            '</PROPERTY>\n',
            exp_result=CIMProperty('Age', Uint8(0), propagated=False),
        ),
        None, None, True
    ),
    (
        "PROPERTY with uint8 typed value (below minimum)",
        dict(
            xml_str=''
            '<PROPERTY NAME="Age" TYPE="uint8">\n'
            '  <VALUE>-1</VALUE>\n'
            '</PROPERTY>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PROPERTY with uint8 typed value (maximum)",
        dict(
            xml_str=''
            '<PROPERTY NAME="Age" TYPE="uint8">\n'
            '  <VALUE>255</VALUE>\n'
            '</PROPERTY>\n',
            exp_result=CIMProperty('Age', Uint8(255), propagated=False),
        ),
        None, None, True
    ),
    (
        "PROPERTY with uint8 typed value (above maximum)",
        dict(
            xml_str=''
            '<PROPERTY NAME="Age" TYPE="uint8">\n'
            '  <VALUE>256</VALUE>\n'
            '</PROPERTY>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PROPERTY with uint16 typed value that is None",
        dict(
            xml_str=''
            '<PROPERTY NAME="Foo" TYPE="uint16"/>\n',
            exp_result=CIMProperty('Foo', value=None, type='uint16',
                                   propagated=False),
        ),
        None, None, True
    ),
    (
        "PROPERTY with uint16 typed value (maximum)",
        dict(
            xml_str=''
            '<PROPERTY NAME="Age" TYPE="uint16">\n'
            '  <VALUE>65535</VALUE>\n'
            '</PROPERTY>\n',
            exp_result=CIMProperty('Age', Uint16(65535), propagated=False),
        ),
        None, None, True
    ),
    (
        "PROPERTY with uint32 typed value that is None",
        dict(
            xml_str=''
            '<PROPERTY NAME="Foo" TYPE="uint32"/>\n',
            exp_result=CIMProperty('Foo', value=None, type='uint32',
                                   propagated=False),
        ),
        None, None, True
    ),
    (
        "PROPERTY with uint32 typed value (maximum)",
        dict(
            xml_str=''
            '<PROPERTY NAME="Age" TYPE="uint32">\n'
            '  <VALUE>4294967295</VALUE>\n'
            '</PROPERTY>\n',
            exp_result=CIMProperty('Age', Uint32(4294967295), propagated=False),
        ),
        None, None, True
    ),
    (
        "PROPERTY with uint64 typed value that is None",
        dict(
            xml_str=''
            '<PROPERTY NAME="Foo" TYPE="uint64"/>\n',
            exp_result=CIMProperty('Foo', value=None, type='uint64',
                                   propagated=False),
        ),
        None, None, True
    ),
    (
        "PROPERTY with uint64 typed value (maximum)",
        dict(
            xml_str=''
            '<PROPERTY NAME="Age" TYPE="uint64">\n'
            '  <VALUE>18446744073709551615</VALUE>\n'
            '</PROPERTY>\n',
            exp_result=CIMProperty('Age', Uint64(18446744073709551615),
                                   propagated=False),
        ),
        None, None, True
    ),
    (
        "PROPERTY with sint8 typed value that is None",
        dict(
            xml_str=''
            '<PROPERTY NAME="Foo" TYPE="sint8"/>\n',
            exp_result=CIMProperty('Foo', value=None, type='sint8',
                                   propagated=False),
        ),
        None, None, True
    ),
    (
        "PROPERTY with sint8 typed value (minimum)",
        dict(
            xml_str=''
            '<PROPERTY NAME="Age" TYPE="sint8">\n'
            '  <VALUE>-128</VALUE>\n'
            '</PROPERTY>\n',
            exp_result=CIMProperty('Age', Sint8(-128), propagated=False),
        ),
        None, None, True
    ),
    (
        "PROPERTY with sint8 typed value (below minimum)",
        dict(
            xml_str=''
            '<PROPERTY NAME="Age" TYPE="sint8">\n'
            '  <VALUE>-129</VALUE>\n'
            '</PROPERTY>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PROPERTY with sint8 typed value (maximum)",
        dict(
            xml_str=''
            '<PROPERTY NAME="Age" TYPE="sint8">\n'
            '  <VALUE>127</VALUE>\n'
            '</PROPERTY>\n',
            exp_result=CIMProperty('Age', Sint8(127), propagated=False),
        ),
        None, None, True
    ),
    (
        "PROPERTY with sint8 typed value (above maximum)",
        dict(
            xml_str=''
            '<PROPERTY NAME="Age" TYPE="sint8">\n'
            '  <VALUE>128</VALUE>\n'
            '</PROPERTY>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PROPERTY with sint16 typed value that is None",
        dict(
            xml_str=''
            '<PROPERTY NAME="Foo" TYPE="sint16"/>\n',
            exp_result=CIMProperty('Foo', value=None, type='sint16',
                                   propagated=False),
        ),
        None, None, True
    ),
    (
        "PROPERTY with sint16 typed value (maximum)",
        dict(
            xml_str=''
            '<PROPERTY NAME="Age" TYPE="sint16">\n'
            '  <VALUE>32767</VALUE>\n'
            '</PROPERTY>\n',
            exp_result=CIMProperty('Age', Sint16(32767), propagated=False),
        ),
        None, None, True
    ),
    (
        "PROPERTY with sint32 typed value that is None",
        dict(
            xml_str=''
            '<PROPERTY NAME="Foo" TYPE="sint32"/>\n',
            exp_result=CIMProperty('Foo', value=None, type='sint32',
                                   propagated=False),
        ),
        None, None, True
    ),
    (
        "PROPERTY with sint32 typed value (maximum)",
        dict(
            xml_str=''
            '<PROPERTY NAME="Age" TYPE="sint32">\n'
            '  <VALUE>2147483647</VALUE>\n'
            '</PROPERTY>\n',
            exp_result=CIMProperty('Age', Sint32(2147483647), propagated=False),
        ),
        None, None, True
    ),
    (
        "PROPERTY with sint64 typed value that is None",
        dict(
            xml_str=''
            '<PROPERTY NAME="Foo" TYPE="sint64"/>\n',
            exp_result=CIMProperty('Foo', value=None, type='sint64',
                                   propagated=False),
        ),
        None, None, True
    ),
    (
        "PROPERTY with sint64 typed value (maximum)",
        dict(
            xml_str=''
            '<PROPERTY NAME="Age" TYPE="sint64">\n'
            '  <VALUE>9223372036854775807</VALUE>\n'
            '</PROPERTY>\n',
            exp_result=CIMProperty('Age', Sint64(9223372036854775807),
                                   propagated=False),
        ),
        None, None, True
    ),
    (
        "PROPERTY with real32 typed value that is None",
        dict(
            xml_str=''
            '<PROPERTY NAME="Foo" TYPE="real32"/>\n',
            exp_result=CIMProperty('Foo', value=None, type='real32',
                                   propagated=False),
        ),
        None, None, True
    ),
    (
        "PROPERTY with real32 typed value (42.0)",
        dict(
            xml_str=''
            '<PROPERTY NAME="Age" TYPE="real32">\n'
            '  <VALUE>42.0</VALUE>\n'
            '</PROPERTY>\n',
            exp_result=CIMProperty('Age', Real32(42.0), propagated=False),
        ),
        None, None, True
    ),
    (
        "PROPERTY with real32 typed value (.0)",
        dict(
            xml_str=''
            '<PROPERTY NAME="Age" TYPE="real32">\n'
            '  <VALUE>.0</VALUE>\n'
            '</PROPERTY>\n',
            exp_result=CIMProperty('Age', Real32(0.0), propagated=False),
        ),
        None, None, True
    ),
    (
        "PROPERTY with real32 typed value (-.1e-12)",
        dict(
            xml_str=''
            '<PROPERTY NAME="Age" TYPE="real32">\n'
            '  <VALUE>-.1e-12</VALUE>\n'
            '</PROPERTY>\n',
            exp_result=CIMProperty('Age', Real32(-0.1E-12), propagated=False),
        ),
        None, None, True
    ),
    (
        "PROPERTY with real32 typed value (.1E12)",
        dict(
            xml_str=''
            '<PROPERTY NAME="Age" TYPE="real32">\n'
            '  <VALUE>.1E12</VALUE>\n'
            '</PROPERTY>\n',
            exp_result=CIMProperty('Age', Real32(0.1E+12), propagated=False),
        ),
        None, None, True
    ),
    (
        "PROPERTY with real32 typed value (+.1e+12)",
        dict(
            xml_str=''
            '<PROPERTY NAME="Age" TYPE="real32">\n'
            '  <VALUE>+.1e+12</VALUE>\n'
            '</PROPERTY>\n',
            exp_result=CIMProperty('Age', Real32(0.1E+12), propagated=False),
        ),
        None, None, True
    ),
    (
        "PROPERTY with real64 typed value that is None",
        dict(
            xml_str=''
            '<PROPERTY NAME="Foo" TYPE="real64"/>\n',
            exp_result=CIMProperty('Foo', value=None, type='real64',
                                   propagated=False),
        ),
        None, None, True
    ),
    (
        "PROPERTY with real64 typed value (+.1e+12)",
        dict(
            xml_str=''
            '<PROPERTY NAME="Age" TYPE="real64">\n'
            '  <VALUE>+.1e+12</VALUE>\n'
            '</PROPERTY>\n',
            exp_result=CIMProperty('Age', Real64(0.1E+12), propagated=False),
        ),
        None, None, True
    ),
    (
        "PROPERTY with datetime typed value that is None",
        dict(
            xml_str=''
            '<PROPERTY NAME="Foo" TYPE="datetime"/>\n',
            exp_result=CIMProperty('Foo', value=None, type='datetime',
                                   propagated=False),
        ),
        None, None, True
    ),
    (
        "PROPERTY with datetime typed value (point in time)",
        dict(
            xml_str=''
            '<PROPERTY NAME="Age" TYPE="datetime">\n'
            '  <VALUE>20140924193040.654321+120</VALUE>\n'
            '</PROPERTY>\n',
            exp_result=CIMProperty(
                'Age', CIMDateTime('20140924193040.654321+120'),
                propagated=False),
        ),
        None, None, True
    ),
    (
        "PROPERTY with datetime typed value (interval)",
        dict(
            xml_str=''
            '<PROPERTY NAME="Age" TYPE="datetime">\n'
            '  <VALUE>00000183132542.234567:000</VALUE>\n'
            '</PROPERTY>\n',
            exp_result=CIMProperty(
                'Age', CIMDateTime('00000183132542.234567:000'),
                propagated=False),
        ),
        None, None, True
    ),
    (
        "PROPERTY with EmbeddedObject=instance and value that is None",
        dict(
            xml_str=''
            '<PROPERTY EmbeddedObject="instance" NAME="Foo" TYPE="string"/>\n',
            exp_result=CIMProperty(
                'Foo', value=None, type='string',
                embedded_object='instance', propagated=False,
            ),
        ),
        None, None, True
    ),
    (
        "PROPERTY with EmbeddedObject=instance and invalid value",
        dict(
            xml_str=''
            '<PROPERTY EmbeddedObject="instance" NAME="Foo" TYPE="string">\n'
            '  <VALUE>\n'
            '    &lt;PROPERTY NAME=&quot;one&quot; TYPE=&quot;uint8&quot;&gt;'
            '      &lt;VALUE&gt;1&lt;/VALUE&gt;'
            '    &lt;/PROPERTY&gt;'
            '  </VALUE>\n'
            '</PROPERTY>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PROPERTY with EmbeddedObject=instance and instance value",
        dict(
            xml_str=''
            '<PROPERTY EmbeddedObject="instance" NAME="Foo" TYPE="string">\n'
            '  <VALUE>\n'
            '    &lt;INSTANCE CLASSNAME=&quot;Foo_Class&quot;&gt;'
            '      &lt;PROPERTY NAME=&quot;one&quot; TYPE=&quot;uint8&quot;&gt;'
            '        &lt;VALUE&gt;1&lt;/VALUE&gt;'
            '      &lt;/PROPERTY&gt;'
            '      &lt;PROPERTY NAME=&quot;two&quot; TYPE=&quot;uint8&quot;&gt;'
            '        &lt;VALUE&gt;2&lt;/VALUE&gt;'
            '      &lt;/PROPERTY&gt;'
            '    &lt;/INSTANCE&gt;'
            '  </VALUE>\n'
            '</PROPERTY>\n',
            exp_result=CIMProperty(
                'Foo',
                CIMInstance(
                    'Foo_Class',
                    properties=[
                        CIMProperty('one', Uint8(1), propagated=False),
                        CIMProperty('two', Uint8(2), propagated=False),
                    ],
                ),
                embedded_object='instance',
                propagated=False,
            ),
        ),
        None, None, True
    ),
    (
        "PROPERTY with EmbeddedObject=object and value that is None",
        dict(
            xml_str=''
            '<PROPERTY EmbeddedObject="object" NAME="Foo" TYPE="string"/>\n',
            exp_result=CIMProperty(
                'Foo', value=None, type='string',
                embedded_object='object', propagated=False,
            ),
        ),
        None, None, True
    ),
    (
        "PROPERTY with EmbeddedObject=object and invalid value",
        dict(
            xml_str=''
            '<PROPERTY EmbeddedObject="object" NAME="Foo" TYPE="string">\n'
            '  <VALUE>\n'
            '    &lt;PROPERTY NAME=&quot;one&quot; TYPE=&quot;uint8&quot;&gt;'
            '      &lt;VALUE&gt;1&lt;/VALUE&gt;'
            '    &lt;/PROPERTY&gt;'
            '  </VALUE>\n'
            '</PROPERTY>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PROPERTY with EmbeddedObject=object and instance value",
        dict(
            xml_str=''
            '<PROPERTY EmbeddedObject="object" NAME="Foo" TYPE="string">\n'
            '  <VALUE>\n'
            '    &lt;INSTANCE CLASSNAME=&quot;Foo_Class&quot;&gt;'
            '      &lt;PROPERTY NAME=&quot;one&quot; TYPE=&quot;uint8&quot;&gt;'
            '        &lt;VALUE&gt;1&lt;/VALUE&gt;'
            '      &lt;/PROPERTY&gt;'
            '      &lt;PROPERTY NAME=&quot;two&quot; TYPE=&quot;uint8&quot;&gt;'
            '        &lt;VALUE&gt;2&lt;/VALUE&gt;'
            '      &lt;/PROPERTY&gt;'
            '    &lt;/INSTANCE&gt;'
            '  </VALUE>\n'
            '</PROPERTY>\n',
            exp_result=CIMProperty(
                'Foo',
                CIMInstance(
                    'Foo_Class',
                    properties=[
                        CIMProperty('one', Uint8(1), propagated=False),
                        CIMProperty('two', Uint8(2), propagated=False),
                    ],
                ),
                embedded_object='object',
                propagated=False,
            ),
        ),
        None, None, True
    ),
    (
        "PROPERTY with EmbeddedObject=object and class value",
        dict(
            xml_str=''
            '<PROPERTY EmbeddedObject="object" NAME="Foo" TYPE="string">\n'
            '  <VALUE>\n'
            '    &lt;CLASS NAME=&quot;Foo_Class&quot;&gt;'
            '      &lt;PROPERTY NAME=&quot;one&quot; TYPE=&quot;uint8&quot;&gt;'
            '        &lt;VALUE&gt;1&lt;/VALUE&gt;'
            '      &lt;/PROPERTY&gt;'
            '      &lt;PROPERTY NAME=&quot;two&quot; TYPE=&quot;uint8&quot;&gt;'
            '        &lt;VALUE&gt;2&lt;/VALUE&gt;'
            '      &lt;/PROPERTY&gt;'
            '    &lt;/CLASS&gt;'
            '  </VALUE>\n'
            '</PROPERTY>\n',
            exp_result=CIMProperty(
                'Foo',
                CIMClass(
                    'Foo_Class',
                    properties=[
                        CIMProperty('one', Uint8(1), propagated=False),
                        CIMProperty('two', Uint8(2), propagated=False),
                    ],
                ),
                embedded_object='object',
                propagated=False,
            ),
        ),
        None, None, True
    ),
    (
        "PROPERTY with qualifier but no value (NULL)",
        dict(
            xml_str=''
            '<PROPERTY NAME="Age" TYPE="uint16">\n'
            '  <QUALIFIER NAME="Qual" TYPE="boolean">\n'
            '    <VALUE>TRUE</VALUE>\n'
            '  </QUALIFIER>\n'
            '</PROPERTY>\n',
            exp_result=CIMProperty(
                'Age', None, type='uint16',
                propagated=False,
                qualifiers=[
                    CIMQualifier('Qual', True,
                                 **qualifier_default_attrs()),
                ],
            ),
        ),
        None, None, True
    ),
    (
        "PROPERTY with qualifier and value",
        dict(
            xml_str=''
            '<PROPERTY NAME="Foo" TYPE="string">\n'
            '  <QUALIFIER NAME="Qual" TYPE="boolean"/>\n'
            '  <VALUE>abc</VALUE>\n'
            '</PROPERTY>\n',
            exp_result=CIMProperty(
                'Foo', type='string', value='abc',
                propagated=False,
                qualifiers=[
                    CIMQualifier('Qual', value=None, type='boolean',
                                 **qualifier_default_attrs()),
                ],
            ),
        ),
        None, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_REQUIRED_PROPERTY_ELEMENT)
@simplified_test_function
def test_required_PROPERTY_element(testcase, xml_str, exp_result):
    """
    Test CIMXMLParser.required_PROPERTY_element().
    """

    parser = CIMXMLParser(xml_str)

    # Code to be tested
    result = parser.required_PROPERTY_element()

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None, \
        "Expected exception {!r} has not been raised".\
        format(testcase.exp_exc_types)

    assert result == exp_result


TESTCASES_REQUIRED_PROPERTY_ARRAY_ELEMENT = [
    (
        "No PROPERTY.ARRAY but different element",
        dict(
            xml_str='<PROPERTY.ARRAY.XXX/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PROPERTY.ARRAY with invalid child element",
        dict(
            xml_str=''
            '<PROPERTY.ARRAY NAME="Foo" TYPE="string">\n'
            '  <XXX/>\n'
            '</PROPERTY.ARRAY>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PROPERTY.ARRAY with invalid content text",
        dict(
            xml_str=''
            '<PROPERTY.ARRAY NAME="Foo" TYPE="string">\n'
            '  xxx\n'
            '  <QUALIFIER NAME="Qual" TYPE="boolean"/>\n'
            '</PROPERTY.ARRAY>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PROPERTY.ARRAY with invalid trailing text",
        dict(
            xml_str=''
            '<PROPERTY.ARRAY NAME="Foo" TYPE="string">\n'
            '  <QUALIFIER NAME="Qual" TYPE="boolean"/>\n'
            '  xxx\n'
            '</PROPERTY.ARRAY>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PROPERTY.ARRAY with children in incorrect order",
        dict(
            xml_str=''
            '<PROPERTY.ARRAY NAME="Foo" TYPE="string">\n'
            '  <VALUE.ARRAY/>\n'
            '  <QUALIFIER NAME="Qual" TYPE="boolean"/>\n'
            '</PROPERTY.ARRAY>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PROPERTY.ARRAY with missing required attribute NAME",
        dict(
            xml_str=''
            '<PROPERTY.ARRAY TYPE="string"/>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PROPERTY.ARRAY with NAME using ASCII characters",
        dict(
            xml_str=''
            '<PROPERTY.ARRAY NAME="Foo" TYPE="string"/>\n',
            exp_result=CIMProperty(
                'Foo', value=None, type='string', is_array=True,
                propagated=False,
            ),
        ),
        None, None, True
    ),
    (
        "PROPERTY.ARRAY with NAME using non-ASCII UCS-2 characters",
        dict(
            xml_str=b''
            b'<PROPERTY.ARRAY NAME="Foo\xC3\xA9" TYPE="string"/>\n',
            exp_result=CIMProperty(
                u'Foo\u00E9', value=None, type='string', is_array=True,
                propagated=False,
            ),
        ),
        None, None, True
    ),
    (
        "PROPERTY.ARRAY with NAME using non-UCS-2 characters",
        dict(
            xml_str=b''
            b'<PROPERTY.ARRAY NAME="Foo\xF0\x90\x85\x82" TYPE="string"/>\n',
            exp_result=CIMProperty(
                u'Foo\U00010142', value=None, type='string', is_array=True,
                propagated=False,
            ),
        ),
        None, None, True
    ),
    (
        "PROPERTY.ARRAY with xml:lang attribute",
        dict(
            xml_str=''
            '<PROPERTY.ARRAY NAME="Foo" TYPE="string" xml:lang="en_us"/>\n',
            exp_result=CIMProperty(
                'Foo', value=None, type='string', is_array=True,
                propagated=False,
            ),
        ),
        None, None, True
    ),
    (
        "PROPERTY.ARRAY with CLASSORIGIN and PROPAGATED attributes",
        dict(
            xml_str=''
            '<PROPERTY.ARRAY NAME="Foo" TYPE="string" CLASSORIGIN="CIM_Foo"'
            ' PROPAGATED="true"/>\n',
            exp_result=CIMProperty(
                'Foo', value=None, type='string', is_array=True,
                class_origin='CIM_Foo', propagated=True
            ),
        ),
        None, None, True
    ),
    (
        "PROPERTY.ARRAY fixed array",
        dict(
            xml_str=''
            '<PROPERTY.ARRAY NAME="Foo" TYPE="string" ARRAYSIZE="10"/>\n',
            exp_result=CIMProperty(
                'Foo', value=None, type='string', is_array=True, array_size=10,
                propagated=False
            ),
        ),
        None, None, True
    ),
    (
        "PROPERTY.ARRAY with missing required attribute TYPE",
        dict(
            xml_str=''
            '<PROPERTY.ARRAY NAME="Foo"/>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PROPERTY.ARRAY with string array typed value that is None",
        dict(
            xml_str=''
            '<PROPERTY.ARRAY NAME="Foo" TYPE="string"/>\n',
            exp_result=CIMProperty(
                'Foo', value=None, type='string', is_array=True,
                propagated=False,
            ),
        ),
        None, None, True
    ),
    (
        "PROPERTY.ARRAY with string array typed value that is empty",
        dict(
            xml_str=''
            '<PROPERTY.ARRAY NAME="Foo" TYPE="string">\n'
            '  <VALUE.ARRAY>\n'
            '  </VALUE.ARRAY>\n'
            '</PROPERTY.ARRAY>\n',
            exp_result=CIMProperty(
                'Foo', value=[], type='string', is_array=True,
                propagated=False,
            ),
        ),
        None, None, True
    ),
    (
        "PROPERTY.ARRAY with string array typed value and 3 items",
        dict(
            xml_str=''
            '<PROPERTY.ARRAY NAME="Foo" TYPE="string">\n'
            '  <VALUE.ARRAY>\n'
            '    <VALUE>a</VALUE>\n'
            '    <VALUE>b</VALUE>\n'
            '    <VALUE>c</VALUE>\n'
            '  </VALUE.ARRAY>\n'
            '</PROPERTY.ARRAY>\n',
            exp_result=CIMProperty(
                'Foo', value=['a', 'b', 'c'], type='string', is_array=True,
                propagated=False,
            ),
        ),
        None, None, True
    ),
    (
        "PROPERTY.ARRAY with string array typed value and some NULL items",
        dict(
            xml_str=''
            '<PROPERTY.ARRAY NAME="Foo" TYPE="string">\n'
            '  <VALUE.ARRAY>\n'
            '    <VALUE.NULL/>\n'
            '    <VALUE>b</VALUE>\n'
            '    <VALUE.NULL/>\n'
            '  </VALUE.ARRAY>\n'
            '</PROPERTY.ARRAY>\n',
            exp_result=CIMProperty(
                'Foo', value=[None, 'b', None], type='string', is_array=True,
                propagated=False,
            ),
        ),
        None, None, True
    ),
    (
        "PROPERTY.ARRAY with uint8 array typed value and qualifiers",
        dict(
            xml_str=''
            '<PROPERTY.ARRAY NAME="Foo" TYPE="uint8">\n'
            '  <QUALIFIER NAME="Qual" TYPE="boolean">\n'
            '    <VALUE>TRUE</VALUE>\n'
            '  </QUALIFIER>\n'
            '  <VALUE.ARRAY>\n'
            '    <VALUE>1</VALUE>\n'
            '    <VALUE>2</VALUE>\n'
            '    <VALUE>3</VALUE>\n'
            '  </VALUE.ARRAY>\n'
            '</PROPERTY.ARRAY>\n',
            exp_result=CIMProperty(
                'Foo', value=[Uint8(x) for x in [1, 2, 3]], type='uint8',
                is_array=True, propagated=False,
                qualifiers=[
                    CIMQualifier('Qual', True,
                                 **qualifier_default_attrs()),
                ],
            ),
        ),
        None, None, True
    ),
    (
        "PROPERTY.ARRAY with EmbeddedObject=instance and value that is None",
        dict(
            xml_str=''
            '<PROPERTY.ARRAY EmbeddedObject="instance" NAME="Foo"'
            ' TYPE="string"/>\n',
            exp_result=CIMProperty(
                'Foo', value=None, type='string', is_array=True,
                embedded_object='instance', propagated=False,
            ),
        ),
        None, None, True
    ),
    (
        "PROPERTY.ARRAY with EmbeddedObject=instance and item that is NULL",
        dict(
            xml_str=''
            '<PROPERTY.ARRAY EmbeddedObject="instance" NAME="Foo"'
            ' TYPE="string">\n'
            '  <VALUE.ARRAY>\n'
            '    <VALUE.NULL/>\n'
            '  </VALUE.ARRAY>\n'
            '</PROPERTY.ARRAY>\n',
            exp_result=CIMProperty(
                'Foo', value=[None], type='string', is_array=True,
                embedded_object='instance', propagated=False,
            ),
        ),
        None, None, True
    ),
    (
        "PROPERTY.ARRAY with EmbeddedObject=instance and invalid item",
        dict(
            xml_str=''
            '<PROPERTY.ARRAY EmbeddedObject="instance" NAME="Foo"'
            ' TYPE="string">\n'
            '  <VALUE.ARRAY>\n'
            '    <VALUE>\n'
            '      &lt;PROPERTY.ARRAY NAME=&quot;one&quot; '
            '       TYPE=&quot;uint8&quot;&gt;'
            '        &lt;VALUE&gt;1&lt;/VALUE&gt;'
            '      &lt;/PROPERTY&gt;'
            '    </VALUE>\n'
            '  </VALUE.ARRAY>\n'
            '</PROPERTY.ARRAY>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PROPERTY.ARRAY with EmbeddedObject=instance and instance item",
        dict(
            xml_str=''
            '<PROPERTY.ARRAY EmbeddedObject="instance" NAME="Foo"'
            ' TYPE="string">\n'
            '  <VALUE.ARRAY>\n'
            '    <VALUE>\n'
            '      &lt;INSTANCE CLASSNAME=&quot;Foo_Class&quot;&gt;'
            '        &lt;PROPERTY NAME=&quot;one&quot;'
            '         TYPE=&quot;uint8&quot;&gt;'
            '          &lt;VALUE&gt;1&lt;/VALUE&gt;'
            '        &lt;/PROPERTY&gt;'
            '        &lt;PROPERTY NAME=&quot;two&quot;'
            '         TYPE=&quot;uint8&quot;&gt;'
            '          &lt;VALUE&gt;2&lt;/VALUE&gt;'
            '        &lt;/PROPERTY&gt;'
            '      &lt;/INSTANCE&gt;'
            '    </VALUE>\n'
            '  </VALUE.ARRAY>\n'
            '</PROPERTY.ARRAY>\n',
            exp_result=CIMProperty(
                'Foo',
                value=[
                    CIMInstance(
                        'Foo_Class',
                        properties=[
                            CIMProperty('one', Uint8(1), propagated=False),
                            CIMProperty('two', Uint8(2), propagated=False),
                        ],
                    ),
                ],
                embedded_object='instance', is_array=True,
                propagated=False,
            ),
        ),
        None, None, True
    ),
    (
        "PROPERTY.ARRAY with EmbeddedObject=object and value that is None",
        dict(
            xml_str=''
            '<PROPERTY.ARRAY EmbeddedObject="object" NAME="Foo"'
            ' TYPE="string"/>\n',
            exp_result=CIMProperty(
                'Foo', value=None, type='string', is_array=True,
                embedded_object='object', propagated=False,
            ),
        ),
        None, None, True
    ),
    (
        "PROPERTY.ARRAY with EmbeddedObject=object and item that is NULL",
        dict(
            xml_str=''
            '<PROPERTY.ARRAY EmbeddedObject="object" NAME="Foo"'
            ' TYPE="string">\n'
            '  <VALUE.ARRAY>\n'
            '    <VALUE.NULL/>\n'
            '  </VALUE.ARRAY>\n'
            '</PROPERTY.ARRAY>\n',
            exp_result=CIMProperty(
                'Foo', value=[None], type='string', is_array=True,
                embedded_object='object', propagated=False,
            ),
        ),
        None, None, True
    ),
    (
        "PROPERTY.ARRAY with EmbeddedObject=object and invalid item",
        dict(
            xml_str=''
            '<PROPERTY.ARRAY EmbeddedObject="object" NAME="Foo"'
            ' TYPE="string">\n'
            '  <VALUE.ARRAY>\n'
            '    <VALUE>\n'
            '      &lt;PROPERTY NAME=&quot;one&quot; TYPE=&quot;uint8&quot;&gt;'
            '        &lt;VALUE&gt;1&lt;/VALUE&gt;'
            '      &lt;/PROPERTY&gt;'
            '    </VALUE>\n'
            '  </VALUE.ARRAY>\n'
            '</PROPERTY.ARRAY>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PROPERTY.ARRAY with EmbeddedObject=object and instance item",
        dict(
            xml_str=''
            '<PROPERTY.ARRAY EmbeddedObject="object" NAME="Foo"'
            ' TYPE="string">\n'
            '  <VALUE.ARRAY>\n'
            '    <VALUE>\n'
            '      &lt;INSTANCE CLASSNAME=&quot;Foo_Class&quot;&gt;'
            '        &lt;PROPERTY NAME=&quot;one&quot;'
            '         TYPE=&quot;uint8&quot;&gt;'
            '          &lt;VALUE&gt;1&lt;/VALUE&gt;'
            '        &lt;/PROPERTY&gt;'
            '        &lt;PROPERTY NAME=&quot;two&quot;'
            '         TYPE=&quot;uint8&quot;&gt;'
            '          &lt;VALUE&gt;2&lt;/VALUE&gt;'
            '        &lt;/PROPERTY&gt;'
            '      &lt;/INSTANCE&gt;'
            '    </VALUE>\n'
            '  </VALUE.ARRAY>\n'
            '</PROPERTY.ARRAY>\n',
            exp_result=CIMProperty(
                'Foo',
                value=[
                    CIMInstance(
                        'Foo_Class',
                        properties=[
                            CIMProperty('one', Uint8(1), propagated=False),
                            CIMProperty('two', Uint8(2), propagated=False),
                        ],
                    ),
                ],
                embedded_object='object', is_array=True,
                propagated=False,
            ),
        ),
        None, None, True
    ),
    (
        "PROPERTY.ARRAY with EmbeddedObject=object and class item",
        dict(
            xml_str=''
            '<PROPERTY.ARRAY EmbeddedObject="object" NAME="Foo"'
            ' TYPE="string">\n'
            '  <VALUE.ARRAY>\n'
            '    <VALUE>\n'
            '      &lt;CLASS NAME=&quot;Foo_Class&quot;&gt;'
            '        &lt;PROPERTY NAME=&quot;one&quot;'
            '         TYPE=&quot;uint8&quot;&gt;'
            '          &lt;VALUE&gt;1&lt;/VALUE&gt;'
            '        &lt;/PROPERTY&gt;'
            '        &lt;PROPERTY NAME=&quot;two&quot;'
            '         TYPE=&quot;uint8&quot;&gt;'
            '          &lt;VALUE&gt;2&lt;/VALUE&gt;'
            '        &lt;/PROPERTY&gt;'
            '      &lt;/CLASS&gt;'
            '    </VALUE>\n'
            '  </VALUE.ARRAY>\n'
            '</PROPERTY.ARRAY>\n',
            exp_result=CIMProperty(
                'Foo',
                value=[
                    CIMClass(
                        'Foo_Class',
                        properties=[
                            CIMProperty('one', Uint8(1), propagated=False),
                            CIMProperty('two', Uint8(2), propagated=False),
                        ],
                    ),
                ],
                embedded_object='object', is_array=True,
                propagated=False,
            ),
        ),
        None, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_REQUIRED_PROPERTY_ARRAY_ELEMENT)
@simplified_test_function
def test_required_PROPERTY_ARRAY_element(testcase, xml_str, exp_result):
    """
    Test CIMXMLParser.required_PROPERTY_ARRAY_element().
    """

    parser = CIMXMLParser(xml_str)

    # Code to be tested
    result = parser.required_PROPERTY_ARRAY_element()

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None, \
        "Expected exception {!r} has not been raised".\
        format(testcase.exp_exc_types)

    assert result == exp_result


TESTCASES_REQUIRED_PROPERTY_REFERENCE_ELEMENT = [
    (
        "No PROPERTY.REFERENCE but different element",
        dict(
            xml_str='<PROPERTY.REFERENCE.XXX/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PROPERTY.REFERENCE with invalid child element",
        dict(
            xml_str=''
            '<PROPERTY.REFERENCE NAME="Foo">\n'
            '  <XXX/>\n'
            '</PROPERTY.REFERENCE>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PROPERTY.REFERENCE with invalid content text",
        dict(
            xml_str=''
            '<PROPERTY.REFERENCE NAME="Foo">\n'
            '  xxx\n'
            '  <QUALIFIER NAME="Qual" TYPE="boolean"/>\n'
            '</PROPERTY.REFERENCE>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PROPERTY.REFERENCE with invalid trailing text",
        dict(
            xml_str=''
            '<PROPERTY.REFERENCE NAME="Foo">\n'
            '  <QUALIFIER NAME="Qual" TYPE="boolean"/>\n'
            '  xxx\n'
            '</PROPERTY.REFERENCE>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PROPERTY.REFERENCE with children in incorrect order",
        dict(
            xml_str=''
            '<PROPERTY.REFERENCE NAME="Foo">\n'
            '  <VALUE.REFERENCE>\n'
            '    <INSTANCENAME CLASSNAME="CIM_Foo"/>\n'
            '  </VALUE.REFERENCE>\n'
            '  <QUALIFIER NAME="Qual" TYPE="boolean"/>\n'
            '</PROPERTY.REFERENCE>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PROPERTY.REFERENCE with missing required attribute NAME",
        dict(
            xml_str=''
            '<PROPERTY.REFERENCE/>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PROPERTY.REFERENCE with NAME using ASCII characters",
        dict(
            xml_str=''
            '<PROPERTY.REFERENCE NAME="Foo"/>\n',
            exp_result=CIMProperty(
                'Foo', value=None, type='reference',
                propagated=False,
            ),
        ),
        None, None, True
    ),
    (
        "PROPERTY.REFERENCE with NAME using non-ASCII UCS-2 characters",
        dict(
            xml_str=b''
            b'<PROPERTY.REFERENCE NAME="Foo\xC3\xA9"/>\n',
            exp_result=CIMProperty(
                u'Foo\u00E9', value=None, type='reference',
                propagated=False,
            ),
        ),
        None, None, True
    ),
    (
        "PROPERTY.REFERENCE with NAME using non-UCS-2 characters",
        dict(
            xml_str=b''
            b'<PROPERTY.REFERENCE NAME="Foo\xF0\x90\x85\x82"/>\n',
            exp_result=CIMProperty(
                u'Foo\U00010142', value=None, type='reference',
                propagated=False,
            ),
        ),
        None, None, True
    ),
    (
        "PROPERTY.REFERENCE with CLASSORIGIN and PROPAGATED attributes",
        dict(
            xml_str=''
            '<PROPERTY.REFERENCE NAME="Foo" CLASSORIGIN="CIM_Foo"'
            ' PROPAGATED="true"/>\n',
            exp_result=CIMProperty(
                'Foo', value=None, type='reference',
                class_origin='CIM_Foo', propagated=True),
        ),
        None, None, True
    ),
    (
        "PROPERTY.REFERENCE with value that is None",
        dict(
            xml_str=''
            '<PROPERTY.REFERENCE NAME="Foo"/>\n',
            exp_result=CIMProperty(
                'Foo', value=None, type='reference', propagated=False),
        ),
        None, None, True
    ),
    (
        "PROPERTY.REFERENCE with ref value that is a INSTANCENAME",
        dict(
            xml_str=''
            '<PROPERTY.REFERENCE NAME="Foo">\n'
            '  <VALUE.REFERENCE>\n'
            '    <INSTANCENAME CLASSNAME="CIM_Foo"/>\n'
            '  </VALUE.REFERENCE>\n'
            '</PROPERTY.REFERENCE>\n',
            exp_result=CIMProperty(
                'Foo',
                value=CIMInstanceName('CIM_Foo'),
                propagated=False,
            ),
        ),
        None, None, True
    ),
    (
        "PROPERTY.REFERENCE with ref value that is a LOCALINSTANCEPATH",
        dict(
            xml_str=''
            '<PROPERTY.REFERENCE NAME="Foo">\n'
            '  <VALUE.REFERENCE>\n'
            '    <LOCALINSTANCEPATH>\n'
            '      <LOCALNAMESPACEPATH>\n'
            '        <NAMESPACE NAME="foo"/>\n'
            '      </LOCALNAMESPACEPATH>\n'
            '      <INSTANCENAME CLASSNAME="CIM_Foo"/>\n'
            '    </LOCALINSTANCEPATH>\n'
            '  </VALUE.REFERENCE>\n'
            '</PROPERTY.REFERENCE>\n',
            exp_result=CIMProperty(
                'Foo',
                value=CIMInstanceName(
                    'CIM_Foo',
                    namespace='foo'
                ),
                propagated=False,
            ),
        ),
        None, None, True
    ),
    (
        "PROPERTY.REFERENCE with ref value that is a INSTANCEPATH",
        dict(
            xml_str=''
            '<PROPERTY.REFERENCE NAME="Foo">\n'
            '  <VALUE.REFERENCE>\n'
            '    <INSTANCEPATH>\n'
            '      <NAMESPACEPATH>\n'
            '        <HOST>woot.com</HOST>\n'
            '        <LOCALNAMESPACEPATH>\n'
            '          <NAMESPACE NAME="foo"/>\n'
            '        </LOCALNAMESPACEPATH>\n'
            '      </NAMESPACEPATH>\n'
            '      <INSTANCENAME CLASSNAME="CIM_Foo"/>\n'
            '    </INSTANCEPATH>\n'
            '  </VALUE.REFERENCE>\n'
            '</PROPERTY.REFERENCE>\n',
            exp_result=CIMProperty(
                'Foo',
                value=CIMInstanceName(
                    'CIM_Foo',
                    namespace='foo',
                    host='woot.com',
                ),
                propagated=False
            ),
        ),
        None, None, True
    ),
    (
        "PROPERTY.REFERENCE with ref value that is a CLASSNAME (not used)",
        dict(
            xml_str=''
            '<PROPERTY.REFERENCE NAME="Foo">\n'
            '  <VALUE.REFERENCE>\n'
            '    <CLASSNAME NAME="CIM_Foo"/>\n'
            '  </VALUE.REFERENCE>\n'
            '</PROPERTY.REFERENCE>\n',
            exp_result=CIMProperty(
                'Foo', type='reference',
                value=CIMClassName('CIM_Foo'),
                propagated=False,
            ),
        ),
        None, None, True
    ),
    (
        "PROPERTY.REFERENCE with ref value that is a LOCALCLASSPATH (not used)",
        dict(
            xml_str=''
            '<PROPERTY.REFERENCE NAME="Foo">\n'
            '  <VALUE.REFERENCE>\n'
            '    <LOCALCLASSPATH>\n'
            '      <LOCALNAMESPACEPATH>\n'
            '        <NAMESPACE NAME="foo"/>\n'
            '      </LOCALNAMESPACEPATH>\n'
            '      <CLASSNAME NAME="CIM_Foo"/>\n'
            '    </LOCALCLASSPATH>\n'
            '  </VALUE.REFERENCE>\n'
            '</PROPERTY.REFERENCE>\n',
            exp_result=CIMProperty(
                'Foo', type='reference',
                value=CIMClassName(
                    'CIM_Foo',
                    namespace='foo'
                ),
                propagated=False,
            ),
        ),
        None, None, True
    ),
    (
        "PROPERTY.REFERENCE with ref value that is a CLASSPATH "
        "(permitted in CIM-XML DTD but not in CIM Infrastructure (DSP0004))",
        dict(
            xml_str=''
            '<PROPERTY.REFERENCE NAME="Foo">\n'
            '  <VALUE.REFERENCE>\n'
            '    <CLASSPATH>\n'
            '      <NAMESPACEPATH>\n'
            '        <HOST>woot.com</HOST>\n'
            '        <LOCALNAMESPACEPATH>\n'
            '          <NAMESPACE NAME="foo"/>\n'
            '        </LOCALNAMESPACEPATH>\n'
            '      </NAMESPACEPATH>\n'
            '      <CLASSNAME NAME="CIM_Foo"/>\n'
            '    </CLASSPATH>\n'
            '  </VALUE.REFERENCE>\n'
            '</PROPERTY.REFERENCE>\n',
            exp_result=CIMProperty(
                'Foo', type='reference',
                value=CIMClassName(
                    'CIM_Foo',
                    namespace='foo',
                    host='woot.com',
                ),
                propagated=False
            ),
        ),
        None, None, True
    ),
    (
        "PROPERTY.REFERENCE with value and qualifiers",
        dict(
            xml_str=''
            '<PROPERTY.REFERENCE NAME="Foo">\n'
            '  <QUALIFIER NAME="Qual" TYPE="boolean">\n'
            '    <VALUE>TRUE</VALUE>\n'
            '  </QUALIFIER>\n'
            '  <VALUE.REFERENCE>\n'
            '    <INSTANCENAME CLASSNAME="CIM_Foo"/>\n'
            '  </VALUE.REFERENCE>\n'
            '</PROPERTY.REFERENCE>\n',
            exp_result=CIMProperty(
                'Foo',
                CIMInstanceName('CIM_Foo'),
                propagated=False,
                qualifiers=[
                    CIMQualifier('Qual', True,
                                 **qualifier_default_attrs()),
                ],
            ),
        ),
        None, None, True
    ),
    (
        "PROPERTY.REFERENCE that is None and with qualifiers",
        dict(
            xml_str=''
            '<PROPERTY.REFERENCE NAME="Foo">\n'
            '  <QUALIFIER NAME="Qual" TYPE="boolean">\n'
            '    <VALUE>TRUE</VALUE>\n'
            '  </QUALIFIER>\n'
            '</PROPERTY.REFERENCE>\n',
            exp_result=CIMProperty(
                'Foo', type='reference',
                value=None,
                propagated=False,
                qualifiers=[
                    CIMQualifier('Qual', True,
                                 **qualifier_default_attrs()),
                ],
            ),
        ),
        None, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_REQUIRED_PROPERTY_REFERENCE_ELEMENT)
@simplified_test_function
def test_required_PROPERTY_REFERENCE_element(testcase, xml_str, exp_result):
    """
    Test CIMXMLParser.required_PROPERTY_REFERENCE_element().
    """

    parser = CIMXMLParser(xml_str)

    # Code to be tested
    result = parser.required_PROPERTY_REFERENCE_element()

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None, \
        "Expected exception {!r} has not been raised".\
        format(testcase.exp_exc_types)

    assert result == exp_result


TESTCASES_REQUIRED_METHOD_ELEMENT = [
    (
        "No METHOD but different element",
        dict(
            xml_str='<METHOD.XXX/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "METHOD with invalid child element",
        dict(
            xml_str=''
            '<METHOD NAME="Foo" TYPE="string">\n'
            '  <XXX/>\n'
            '</METHOD>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "METHOD with invalid content text",
        dict(
            xml_str=''
            '<METHOD NAME="Foo" TYPE="string">\n'
            '  xxx\n'
            '  <QUALIFIER NAME="Qual" TYPE="boolean"/>\n'
            '</METHOD>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "METHOD with invalid trailing text",
        dict(
            xml_str=''
            '<METHOD NAME="Foo" TYPE="string">\n'
            '  <QUALIFIER NAME="Qual" TYPE="boolean"/>\n'
            '  xxx\n'
            '</METHOD>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "METHOD with children in incorrect order",
        dict(
            xml_str=''
            '<METHOD NAME="Foo" TYPE="string">\n'
            '  <PARAMETER NAME="Parm1" TYPE="uint32"/>\n'
            '  <QUALIFIER NAME="Qual" TYPE="boolean"/>\n'
            '</METHOD>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "METHOD with missing required attribute NAME",
        dict(
            xml_str=''
            '<METHOD TYPE="string"/>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "METHOD with NAME using ASCII characters",
        dict(
            xml_str=''
            '<METHOD NAME="Foo" TYPE="string"/>\n',
            exp_result=CIMMethod('Foo', return_type='string',
                                 propagated=False),
        ),
        None, None, True
    ),
    (
        "METHOD with NAME using non-ASCII UCS-2 characters",
        dict(
            xml_str=b''
            b'<METHOD NAME="Foo\xC3\xA9" TYPE="string"/>\n',
            exp_result=CIMMethod(u'Foo\u00E9', return_type='string',
                                 propagated=False),
        ),
        None, None, True
    ),
    (
        "METHOD with NAME using non-UCS-2 characters",
        dict(
            xml_str=b''
            b'<METHOD NAME="Foo\xF0\x90\x85\x82" TYPE="string"/>\n',
            exp_result=CIMMethod(u'Foo\U00010142', return_type='string',
                                 propagated=False),
        ),
        None, None, True
    ),
    (
        "METHOD with CLASSORIGIN and PROPAGATED attributes",
        dict(
            xml_str=''
            '<METHOD NAME="Foo" TYPE="string" CLASSORIGIN="CIM_Foo"'
            ' PROPAGATED="true"/>\n',
            exp_result=CIMMethod('Foo', return_type='string',
                                 class_origin='CIM_Foo', propagated=True),
        ),
        None, None, True
    ),
    (
        "METHOD without attribute TYPE (void return type)",
        dict(
            xml_str=''
            '<METHOD NAME="Foo"/>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "METHOD with two qualifiers",
        dict(
            xml_str=''
            '<METHOD NAME="Age" TYPE="uint16">\n'
            '  <QUALIFIER NAME="Qual2" TYPE="boolean">\n'
            '    <VALUE>TRUE</VALUE>\n'
            '  </QUALIFIER>\n'
            '  <QUALIFIER NAME="Qual1" TYPE="boolean">\n'
            '    <VALUE>FALSE</VALUE>\n'
            '  </QUALIFIER>\n'
            '</METHOD>\n',
            exp_result=CIMMethod(
                'Age', return_type='uint16',
                propagated=False,
                qualifiers=[
                    CIMQualifier('Qual2', True,
                                 **qualifier_default_attrs()),
                    CIMQualifier('Qual1', False,
                                 **qualifier_default_attrs()),
                ],
            ),
        ),
        None, None, True
    ),
    (
        "METHOD with multiple parameters of different kind (in opposite order "
        "of declaration in DTD, and decreasing order of names)",
        dict(
            xml_str=''
            '<METHOD NAME="Age" TYPE="uint16">\n'
            '  <PARAMETER.REFARRAY NAME="Parm4" REFERENCECLASS="CIM_Foo"/>\n'
            '  <PARAMETER.ARRAY NAME="Parm3" TYPE="uint32"/>\n'
            '  <PARAMETER.REFERENCE NAME="Parm2" REFERENCECLASS="CIM_Foo"/>\n'
            '  <PARAMETER NAME="Parm1" TYPE="uint32"/>\n'
            '</METHOD>\n',
            exp_result=CIMMethod(
                'Age', return_type='uint16',
                propagated=False,
                parameters=[
                    CIMParameter('Parm4', type='reference', is_array=True,
                                 reference_class='CIM_Foo'),
                    CIMParameter('Parm3', type='uint32', is_array=True),
                    CIMParameter('Parm2', type='reference',
                                 reference_class='CIM_Foo'),
                    CIMParameter('Parm1', type='uint32'),
                ],
            ),
        ),
        None, None, True
    ),
    (
        "METHOD with one qualifier and one parameter",
        dict(
            xml_str=''
            '<METHOD NAME="Age" TYPE="uint16">\n'
            '  <QUALIFIER NAME="Qual" TYPE="boolean">\n'
            '    <VALUE>TRUE</VALUE>\n'
            '  </QUALIFIER>\n'
            '  <PARAMETER NAME="Parm" TYPE="uint32"/>\n'
            '</METHOD>\n',
            exp_result=CIMMethod(
                'Age', return_type='uint16',
                propagated=False,
                qualifiers=[
                    CIMQualifier('Qual', True,
                                 **qualifier_default_attrs()),
                ],
                parameters=[
                    CIMParameter('Parm', type='uint32'),
                ],
            ),
        ),
        None, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_REQUIRED_METHOD_ELEMENT)
@simplified_test_function
def test_required_METHOD_element(testcase, xml_str, exp_result):
    """
    Test CIMXMLParser.required_METHOD_element().
    """

    parser = CIMXMLParser(xml_str)

    # Code to be tested
    result = parser.required_METHOD_element()

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None, \
        "Expected exception {!r} has not been raised".\
        format(testcase.exp_exc_types)

    assert result == exp_result


TESTCASES_REQUIRED_PARAMETER_ELEMENT = [
    (
        "No PARAMETER but different element",
        dict(
            xml_str='<PARAMETER.XXX/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PARAMETER with invalid child element",
        dict(
            xml_str=''
            '<PARAMETER NAME="Parm" TYPE="string">\n'
            '  <XXX/>\n'
            '</PARAMETER>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PARAMETER with invalid content text",
        dict(
            xml_str=''
            '<PARAMETER NAME="Parm" TYPE="string">\n'
            '  xxx\n'
            '  <QUALIFIER NAME="Qual" TYPE="boolean"/>\n'
            '</PARAMETER>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PARAMETER with invalid trailing text",
        dict(
            xml_str=''
            '<PARAMETER NAME="Parm" TYPE="string">\n'
            '  <QUALIFIER NAME="Qual" TYPE="boolean"/>\n'
            '  xxx\n'
            '</PARAMETER>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PARAMETER with missing required attribute NAME",
        dict(
            xml_str=''
            '<PARAMETER TYPE="string"/>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PARAMETER with NAME using ASCII characters",
        dict(
            xml_str=''
            '<PARAMETER NAME="Parm" TYPE="string"/>\n',
            exp_result=CIMParameter('Parm', type='string'),
        ),
        None, None, True
    ),
    (
        "PARAMETER with NAME using non-ASCII UCS-2 characters",
        dict(
            xml_str=b''
            b'<PARAMETER NAME="Parm\xC3\xA9" TYPE="string"/>\n',
            exp_result=CIMParameter(u'Parm\u00E9', type='string'),
        ),
        None, None, True
    ),
    (
        "PARAMETER with NAME using non-UCS-2 characters",
        dict(
            xml_str=b''
            b'<PARAMETER NAME="Parm\xF0\x90\x85\x82" TYPE="string"/>\n',
            exp_result=CIMParameter(u'Parm\U00010142', type='string'),
        ),
        None, None, True
    ),
    (
        "PARAMETER with missing required attribute TYPE",
        dict(
            xml_str=''
            '<PARAMETER NAME="Parm"/>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PARAMETER of type string",
        dict(
            xml_str=''
            '<PARAMETER NAME="Parm" TYPE="string"/>\n',
            exp_result=CIMParameter('Parm', type='string'),
        ),
        None, None, True
    ),
    (
        "PARAMETER of type char16",
        dict(
            xml_str=''
            '<PARAMETER NAME="Parm" TYPE="char16"/>\n',
            exp_result=CIMParameter('Parm', type='char16'),
        ),
        None, None, True
    ),
    (
        "PARAMETER of type boolean",
        dict(
            xml_str=''
            '<PARAMETER NAME="Parm" TYPE="boolean"/>\n',
            exp_result=CIMParameter('Parm', type='boolean'),
        ),
        None, None, True
    ),
    (
        "PARAMETER of type uint8",
        dict(
            xml_str=''
            '<PARAMETER NAME="Parm" TYPE="uint8"/>\n',
            exp_result=CIMParameter('Parm', type='uint8'),
        ),
        None, None, True
    ),
    (
        "PARAMETER of type uint16",
        dict(
            xml_str=''
            '<PARAMETER NAME="Parm" TYPE="uint16"/>\n',
            exp_result=CIMParameter('Parm', type='uint16'),
        ),
        None, None, True
    ),
    (
        "PARAMETER of type uint32",
        dict(
            xml_str=''
            '<PARAMETER NAME="Parm" TYPE="uint32"/>\n',
            exp_result=CIMParameter('Parm', type='uint32'),
        ),
        None, None, True
    ),
    (
        "PARAMETER of type uint64",
        dict(
            xml_str=''
            '<PARAMETER NAME="Parm" TYPE="uint64"/>\n',
            exp_result=CIMParameter('Parm', type='uint64'),
        ),
        None, None, True
    ),
    (
        "PARAMETER of type sint8",
        dict(
            xml_str=''
            '<PARAMETER NAME="Parm" TYPE="sint8"/>\n',
            exp_result=CIMParameter('Parm', type='sint8'),
        ),
        None, None, True
    ),
    (
        "PARAMETER of type sint16",
        dict(
            xml_str=''
            '<PARAMETER NAME="Parm" TYPE="sint16"/>\n',
            exp_result=CIMParameter('Parm', type='sint16'),
        ),
        None, None, True
    ),
    (
        "PARAMETER of type sint32",
        dict(
            xml_str=''
            '<PARAMETER NAME="Parm" TYPE="sint32"/>\n',
            exp_result=CIMParameter('Parm', type='sint32'),
        ),
        None, None, True
    ),
    (
        "PARAMETER of type sint64",
        dict(
            xml_str=''
            '<PARAMETER NAME="Parm" TYPE="sint64"/>\n',
            exp_result=CIMParameter('Parm', type='sint64'),
        ),
        None, None, True
    ),
    (
        "PARAMETER of type real32",
        dict(
            xml_str=''
            '<PARAMETER NAME="Parm" TYPE="real32"/>\n',
            exp_result=CIMParameter('Parm', type='real32'),
        ),
        None, None, True
    ),
    (
        "PARAMETER of type real64",
        dict(
            xml_str=''
            '<PARAMETER NAME="Parm" TYPE="real64"/>\n',
            exp_result=CIMParameter('Parm', type='real64'),
        ),
        None, None, True
    ),
    (
        "PARAMETER of type datetime",
        dict(
            xml_str=''
            '<PARAMETER NAME="Parm" TYPE="datetime"/>\n',
            exp_result=CIMParameter('Parm', type='datetime'),
        ),
        None, None, True
    ),
    (
        "PARAMETER of type reference",
        dict(
            xml_str=''
            '<PARAMETER NAME="Parm" TYPE="reference"/>\n',
            exp_result=CIMParameter('Parm', type='reference'),
        ),
        None, None, True
        # TODO 1/18 AM: Should this not be rejected as invalid type?
    ),
    (
        "PARAMETER with two qualifiers",
        dict(
            xml_str=''
            '<PARAMETER NAME="Parm" TYPE="string">\n'
            '  <QUALIFIER NAME="Qual2" TYPE="boolean">\n'
            '    <VALUE>TRUE</VALUE>\n'
            '  </QUALIFIER>\n'
            '  <QUALIFIER NAME="Qual1" TYPE="boolean">\n'
            '    <VALUE>FALSE</VALUE>\n'
            '  </QUALIFIER>\n'
            '</PARAMETER>\n',
            exp_result=CIMParameter(
                'Parm', type='string',
                qualifiers=[
                    CIMQualifier('Qual2', True,
                                 **qualifier_default_attrs()),
                    CIMQualifier('Qual1', False,
                                 **qualifier_default_attrs()),
                ],
            ),
        ),
        None, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_REQUIRED_PARAMETER_ELEMENT)
@simplified_test_function
def test_required_PARAMETER_element(testcase, xml_str, exp_result):
    """
    Test CIMXMLParser.required_PARAMETER_element().
    """

    parser = CIMXMLParser(xml_str)

    # Code to be tested
    result = parser.required_PARAMETER_element()

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None, \
        "Expected exception {!r} has not been raised".\
        format(testcase.exp_exc_types)

    assert result == exp_result


TESTCASES_REQUIRED_PARAMETER_ARRAY_ELEMENT = [
    (
        "PARAMETER.ARRAY but different element",
        dict(
            xml_str='<PARAMETER.ARRAY.XXX/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PARAMETER.ARRAY with invalid child element",
        dict(
            xml_str=''
            '<PARAMETER.ARRAY NAME="Parm" TYPE="string">\n'
            '  <XXX/>\n'
            '</PARAMETER.ARRAY>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PARAMETER.ARRAY with invalid content text",
        dict(
            xml_str=''
            '<PARAMETER.ARRAY NAME="Parm" TYPE="string">\n'
            '  xxx\n'
            '  <QUALIFIER NAME="Qual" TYPE="boolean"/>\n'
            '</PARAMETER.ARRAY>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PARAMETER.ARRAY with invalid trailing text",
        dict(
            xml_str=''
            '<PARAMETER.ARRAY NAME="Parm" TYPE="string">\n'
            '  <QUALIFIER NAME="Qual" TYPE="boolean"/>\n'
            '  xxx\n'
            '</PARAMETER.ARRAY>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PARAMETER.ARRAY with missing required attribute NAME",
        dict(
            xml_str=''
            '<PARAMETER.ARRAY TYPE="string"/>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PARAMETER.ARRAY with NAME using ASCII characters",
        dict(
            xml_str=''
            '<PARAMETER.ARRAY NAME="Parm" TYPE="string"/>\n',
            exp_result=CIMParameter('Parm', type='string', is_array=True),
        ),
        None, None, True
    ),
    (
        "PARAMETER.ARRAY with NAME using non-ASCII UCS-2 characters",
        dict(
            xml_str=b''
            b'<PARAMETER.ARRAY NAME="Parm\xC3\xA9" TYPE="string"/>\n',
            exp_result=CIMParameter(
                u'Parm\u00E9', type='string', is_array=True),
        ),
        None, None, True
    ),
    (
        "PARAMETER.ARRAY with NAME using non-UCS-2 characters",
        dict(
            xml_str=b''
            b'<PARAMETER.ARRAY NAME="Parm\xF0\x90\x85\x82" TYPE="string"/>\n',
            exp_result=CIMParameter(
                u'Parm\U00010142', type='string', is_array=True),
        ),
        None, None, True
    ),
    (
        "PARAMETER.ARRAY fixed array",
        dict(
            xml_str=''
            '<PARAMETER.ARRAY ARRAYSIZE="10" NAME="Parm" TYPE="string"/>\n',
            exp_result=CIMParameter(
                'Parm', type='string', is_array=True, array_size=10
            ),
        ),
        None, None, True
    ),
    (
        "PARAMETER.ARRAY with missing required attribute TYPE",
        dict(
            xml_str=''
            '<PARAMETER.ARRAY NAME="Parm"/>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PARAMETER.ARRAY of type string",
        dict(
            xml_str=''
            '<PARAMETER.ARRAY NAME="Parm" TYPE="string"/>\n',
            exp_result=CIMParameter('Parm', type='string', is_array=True),
        ),
        None, None, True
    ),
    (
        "PARAMETER.ARRAY of type char16",
        dict(
            xml_str=''
            '<PARAMETER.ARRAY NAME="Parm" TYPE="char16"/>\n',
            exp_result=CIMParameter('Parm', type='char16', is_array=True),
        ),
        None, None, True
    ),
    (
        "PARAMETER.ARRAY of type boolean",
        dict(
            xml_str=''
            '<PARAMETER.ARRAY NAME="Parm" TYPE="boolean"/>\n',
            exp_result=CIMParameter('Parm', type='boolean', is_array=True),
        ),
        None, None, True
    ),
    (
        "PARAMETER.ARRAY of type uint8",
        dict(
            xml_str=''
            '<PARAMETER.ARRAY NAME="Parm" TYPE="uint8"/>\n',
            exp_result=CIMParameter('Parm', type='uint8', is_array=True),
        ),
        None, None, True
    ),
    (
        "PARAMETER.ARRAY of type uint16",
        dict(
            xml_str=''
            '<PARAMETER.ARRAY NAME="Parm" TYPE="uint16"/>\n',
            exp_result=CIMParameter('Parm', type='uint16', is_array=True),
        ),
        None, None, True
    ),
    (
        "PARAMETER.ARRAY of type uint32",
        dict(
            xml_str=''
            '<PARAMETER.ARRAY NAME="Parm" TYPE="uint32"/>\n',
            exp_result=CIMParameter('Parm', type='uint32', is_array=True),
        ),
        None, None, True
    ),
    (
        "PARAMETER.ARRAY of type uint64",
        dict(
            xml_str=''
            '<PARAMETER.ARRAY NAME="Parm" TYPE="uint64"/>\n',
            exp_result=CIMParameter('Parm', type='uint64', is_array=True),
        ),
        None, None, True
    ),
    (
        "PARAMETER.ARRAY of type sint8",
        dict(
            xml_str=''
            '<PARAMETER.ARRAY NAME="Parm" TYPE="sint8"/>\n',
            exp_result=CIMParameter('Parm', type='sint8', is_array=True),
        ),
        None, None, True
    ),
    (
        "PARAMETER.ARRAY of type sint16",
        dict(
            xml_str=''
            '<PARAMETER.ARRAY NAME="Parm" TYPE="sint16"/>\n',
            exp_result=CIMParameter('Parm', type='sint16', is_array=True),
        ),
        None, None, True
    ),
    (
        "PARAMETER.ARRAY of type sint32",
        dict(
            xml_str=''
            '<PARAMETER.ARRAY NAME="Parm" TYPE="sint32"/>\n',
            exp_result=CIMParameter('Parm', type='sint32', is_array=True),
        ),
        None, None, True
    ),
    (
        "PARAMETER.ARRAY of type sint64",
        dict(
            xml_str=''
            '<PARAMETER.ARRAY NAME="Parm" TYPE="sint64"/>\n',
            exp_result=CIMParameter('Parm', type='sint64', is_array=True),
        ),
        None, None, True
    ),
    (
        "PARAMETER.ARRAY of type real32",
        dict(
            xml_str=''
            '<PARAMETER.ARRAY NAME="Parm" TYPE="real32"/>\n',
            exp_result=CIMParameter('Parm', type='real32', is_array=True),
        ),
        None, None, True
    ),
    (
        "PARAMETER.ARRAY of type real64",
        dict(
            xml_str=''
            '<PARAMETER.ARRAY NAME="Parm" TYPE="real64"/>\n',
            exp_result=CIMParameter('Parm', type='real64', is_array=True),
        ),
        None, None, True
    ),
    (
        "PARAMETER.ARRAY of type datetime",
        dict(
            xml_str=''
            '<PARAMETER.ARRAY NAME="Parm" TYPE="datetime"/>\n',
            exp_result=CIMParameter('Parm', type='datetime', is_array=True),
        ),
        None, None, True
    ),
    (
        "PARAMETER.ARRAY with two qualifiers",
        dict(
            xml_str=''
            '<PARAMETER.ARRAY NAME="Parm" TYPE="string">\n'
            '  <QUALIFIER NAME="Qual2" TYPE="boolean">\n'
            '    <VALUE>TRUE</VALUE>\n'
            '  </QUALIFIER>\n'
            '  <QUALIFIER NAME="Qual1" TYPE="boolean">\n'
            '    <VALUE>FALSE</VALUE>\n'
            '  </QUALIFIER>\n'
            '</PARAMETER.ARRAY>\n',
            exp_result=CIMParameter(
                'Parm', type='string', is_array=True,
                qualifiers=[
                    CIMQualifier('Qual2', True,
                                 **qualifier_default_attrs()),
                    CIMQualifier('Qual1', False,
                                 **qualifier_default_attrs()),
                ],
            ),
        ),
        None, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_REQUIRED_PARAMETER_ARRAY_ELEMENT)
@simplified_test_function
def test_required_PARAMETER_ARRAY_element(testcase, xml_str, exp_result):
    """
    Test CIMXMLParser.required_PARAMETER_ARRAY_element().
    """

    parser = CIMXMLParser(xml_str)

    # Code to be tested
    result = parser.required_PARAMETER_ARRAY_element()

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None, \
        "Expected exception {!r} has not been raised".\
        format(testcase.exp_exc_types)

    assert result == exp_result


TESTCASES_REQUIRED_PARAMETER_REFERENCE_ELEMENT = [
    (
        "No PARAMETER.REFERENCE but different element",
        dict(
            xml_str='<PARAMETER.REFERENCE.XXX/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PARAMETER.REFERENCE with invalid child element",
        dict(
            xml_str=''
            '<PARAMETER.REFERENCE NAME="Parm">\n'
            '  <XXX/>\n'
            '</PARAMETER.REFERENCE>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PARAMETER.REFERENCE with invalid content text",
        dict(
            xml_str=''
            '<PARAMETER.REFERENCE NAME="Parm">\n'
            '  xxx\n'
            '  <QUALIFIER NAME="Qual" TYPE="boolean"/>\n'
            '</PARAMETER.REFERENCE>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PARAMETER.REFERENCE with invalid trailing text",
        dict(
            xml_str=''
            '<PARAMETER.REFERENCE NAME="Parm">\n'
            '  <QUALIFIER NAME="Qual" TYPE="boolean"/>\n'
            '  xxx\n'
            '</PARAMETER.REFERENCE>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PARAMETER.REFERENCE with missing required attribute NAME",
        dict(
            xml_str=''
            '<PARAMETER.REFERENCE/>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PARAMETER.REFERENCE with NAME using ASCII characters",
        dict(
            xml_str=''
            '<PARAMETER.REFERENCE NAME="Parm"/>\n',
            exp_result=CIMParameter('Parm', type='reference'),
        ),
        None, None, True
    ),
    (
        "PARAMETER.REFERENCE with NAME using non-ASCII UCS-2 characters",
        dict(
            xml_str=b''
            b'<PARAMETER.REFERENCE NAME="Parm\xC3\xA9"/>\n',
            exp_result=CIMParameter(u'Parm\u00E9', type='reference'),
        ),
        None, None, True
    ),
    (
        "PARAMETER.REFERENCE with NAME using non-UCS-2 characters",
        dict(
            xml_str=b''
            b'<PARAMETER.REFERENCE NAME="Parm\xF0\x90\x85\x82"/>\n',
            exp_result=CIMParameter(u'Parm\U00010142', type='reference'),
        ),
        None, None, True
    ),
    (
        "PARAMETER.REFERENCE with reference class",
        dict(
            xml_str=''
            '<PARAMETER.REFERENCE NAME="Parm" REFERENCECLASS="CIM_Foo"/>\n',
            exp_result=CIMParameter(
                'Parm', type='reference', reference_class='CIM_Foo'
            ),
        ),
        None, None, True
    ),
    (
        "PARAMETER.REFERENCE with two qualifiers",
        dict(
            xml_str=''
            '<PARAMETER.REFERENCE NAME="Parm" REFERENCECLASS="CIM_Foo">\n'
            '  <QUALIFIER NAME="Qual2" TYPE="boolean">\n'
            '    <VALUE>TRUE</VALUE>\n'
            '  </QUALIFIER>\n'
            '  <QUALIFIER NAME="Qual1" TYPE="boolean">\n'
            '    <VALUE>FALSE</VALUE>\n'
            '  </QUALIFIER>\n'
            '</PARAMETER.REFERENCE>\n',
            exp_result=CIMParameter(
                'Parm', type='reference', reference_class='CIM_Foo',
                qualifiers=[
                    CIMQualifier('Qual2', True,
                                 **qualifier_default_attrs()),
                    CIMQualifier('Qual1', False,
                                 **qualifier_default_attrs()),
                ],
            ),
        ),
        None, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_REQUIRED_PARAMETER_REFERENCE_ELEMENT)
@simplified_test_function
def test_required_PARAMETER_REFERENCE_element(testcase, xml_str, exp_result):
    """
    Test CIMXMLParser.required_PARAMETER_REFERENCE_element().
    """

    parser = CIMXMLParser(xml_str)

    # Code to be tested
    result = parser.required_PARAMETER_REFERENCE_element()

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None, \
        "Expected exception {!r} has not been raised".\
        format(testcase.exp_exc_types)

    assert result == exp_result


TESTCASES_REQUIRED_PARAMETER_REFARRAY_ELEMENT = [
    (
        "No PARAMETER.REFARRAY but different element",
        dict(
            xml_str='<PARAMETER.REFARRAY.XXX/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PARAMETER.REFARRAY with invalid child element",
        dict(
            xml_str=''
            '<PARAMETER.REFARRAY NAME="Parm">\n'
            '  <XXX/>\n'
            '</PARAMETER.REFARRAY>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PARAMETER.REFARRAY with invalid content text",
        dict(
            xml_str=''
            '<PARAMETER.REFARRAY NAME="Parm">\n'
            '  xxx\n'
            '  <QUALIFIER NAME="Qual" TYPE="boolean"/>\n'
            '</PARAMETER.REFARRAY>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PARAMETER.REFARRAY with invalid trailing text",
        dict(
            xml_str=''
            '<PARAMETER.REFARRAY NAME="Parm">\n'
            '  <QUALIFIER NAME="Qual" TYPE="boolean"/>\n'
            '  xxx\n'
            '</PARAMETER.REFARRAY>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PARAMETER.REFARRAY with missing required attribute NAME",
        dict(
            xml_str=''
            '<PARAMETER.REFARRAY/>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "PARAMETER.REFARRAY with NAME using ASCII characters",
        dict(
            xml_str=''
            '<PARAMETER.REFARRAY NAME="Parm"/>\n',
            exp_result=CIMParameter('Parm', type='reference', is_array=True),
        ),
        None, None, True
    ),
    (
        "PARAMETER.REFARRAY with NAME using non-ASCII UCS-2 characters",
        dict(
            xml_str=b''
            b'<PARAMETER.REFARRAY NAME="Parm\xC3\xA9"/>\n',
            exp_result=CIMParameter(
                u'Parm\u00E9', type='reference', is_array=True),
        ),
        None, None, True
    ),
    (
        "PARAMETER.REFARRAY with NAME using non-UCS-2 characters",
        dict(
            xml_str=b''
            b'<PARAMETER.REFARRAY NAME="Parm\xF0\x90\x85\x82"/>\n',
            exp_result=CIMParameter(
                u'Parm\U00010142', type='reference', is_array=True),
        ),
        None, None, True
    ),
    (
        "PARAMETER.REFARRAY with reference class",
        dict(
            xml_str=''
            '<PARAMETER.REFARRAY NAME="Parm" REFERENCECLASS="CIM_Foo"/>\n',
            exp_result=CIMParameter(
                'Parm', type='reference', is_array=True,
                reference_class='CIM_Foo'
            ),
        ),
        None, None, True
    ),
    (
        "PARAMETER.REFARRAY with fixed size",
        dict(
            xml_str=''
            '<PARAMETER.REFARRAY NAME="Array" ARRAYSIZE="10"/>\n',
            exp_result=CIMParameter(
                'Array', type='reference', is_array=True, array_size=10,
            ),
        ),
        None, None, True
    ),
    (
        "PARAMETER.REFARRAY with two qualifiers",
        dict(
            xml_str=''
            '<PARAMETER.REFARRAY NAME="Parm">\n'
            '  <QUALIFIER NAME="Qual2" TYPE="boolean">\n'
            '    <VALUE>TRUE</VALUE>\n'
            '  </QUALIFIER>\n'
            '  <QUALIFIER NAME="Qual1" TYPE="boolean">\n'
            '    <VALUE>FALSE</VALUE>\n'
            '  </QUALIFIER>\n'
            '</PARAMETER.REFARRAY>\n',
            exp_result=CIMParameter(
                'Parm', type='reference', is_array=True,
                qualifiers=[
                    CIMQualifier('Qual2', True,
                                 **qualifier_default_attrs()),
                    CIMQualifier('Qual1', False,
                                 **qualifier_default_attrs()),
                ],
            ),
        ),
        None, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_REQUIRED_PARAMETER_REFARRAY_ELEMENT)
@simplified_test_function
def test_required_PARAMETER_REFARRAY_element(testcase, xml_str, exp_result):
    """
    Test CIMXMLParser.required_PARAMETER_REFARRAY_element().
    """

    parser = CIMXMLParser(xml_str)

    # Code to be tested
    result = parser.required_PARAMETER_REFARRAY_element()

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None, \
        "Expected exception {!r} has not been raised".\
        format(testcase.exp_exc_types)

    assert result == exp_result


TESTCASES_LIST_OF_KEYBINDING_ELEMENTS = [
    (
        "List of KEYBINDING elements that is empty",
        dict(
            skip_events=1,
            xml_str=''
            '<DUMMY_ROOT>\n'
            '</DUMMY_ROOT>\n',
            exp_result={},
        ),
        None, None, True
    ),
    (
        "List of KEYBINDING elements with one item",
        dict(
            skip_events=1,
            xml_str=''
            '<DUMMY_ROOT>\n'
            '  <KEYBINDING NAME="Foo">\n'
            '    <KEYVALUE>a</KEYVALUE>\n'
            '  </KEYBINDING>\n'
            '</DUMMY_ROOT>\n',
            exp_result={
                u'Foo': u'a',
            },
        ),
        None, None, True
    ),
    (
        "List of KEYBINDING elements with two items",
        dict(
            skip_events=1,
            xml_str=''
            '<DUMMY_ROOT>\n'
            '  <KEYBINDING NAME="Foo">\n'
            '    <KEYVALUE>a</KEYVALUE>\n'
            '  </KEYBINDING>\n'
            '  <KEYBINDING NAME="Bar">\n'
            '    <KEYVALUE>b</KEYVALUE>\n'
            '  </KEYBINDING>\n'
            '</DUMMY_ROOT>\n',
            exp_result={
                u'Foo': u'a',
                u'Bar': u'b',
            },
        ),
        None, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_LIST_OF_KEYBINDING_ELEMENTS)
@simplified_test_function
def test_list_of_KEYBINDING_elements(
        testcase, skip_events, xml_str, exp_result):
    """
    Test CIMXMLParser.list_of_KEYBINDING_elements().
    """

    parser = CIMXMLParser(xml_str)
    for _ in range(skip_events):
        parser.get_next_event()

    # Code to be tested
    result = parser.list_of_KEYBINDING_elements()

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None, \
        "Expected exception {!r} has not been raised".\
        format(testcase.exp_exc_types)

    assert result == exp_result


TESTCASES_REQUIRED_KEYBINDING_ELEMENT = [
    (
        "No KEYBINDING but different element",
        dict(
            xml_str='<KEYBINDING.XXX/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "KEYBINDING with missing required child element",
        dict(
            xml_str=''
            '<KEYBINDING NAME="Foo">\n'
            '</KEYBINDING>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "KEYBINDING with additional invalid trailing child element",
        dict(
            xml_str=''
            '<KEYBINDING NAME="Foo">\n'
            '  <KEYVALUE>a</KEYVALUE>\n'
            '  <XXX/>\n'
            '</KEYBINDING>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "KEYBINDING with additional invalid leading child element",
        dict(
            xml_str=''
            '<KEYBINDING NAME="Foo">\n'
            '  <XXX/>\n'
            '  <KEYVALUE>a</KEYVALUE>\n'
            '</KEYBINDING>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "KEYBINDING with invalid content text",
        dict(
            xml_str=''
            '<KEYBINDING NAME="Foo">\n'
            '  xxx\n'
            '  <KEYVALUE>a</KEYVALUE>\n'
            '</KEYBINDING>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "KEYBINDING with invalid trailing text",
        dict(
            xml_str=''
            '<KEYBINDING NAME="Foo">\n'
            '  <KEYVALUE>a</KEYVALUE>\n'
            '  xxx\n'
            '</KEYBINDING>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "KEYBINDING with missing required attribute NAME",
        dict(
            xml_str=''
            '<KEYBINDING>\n'
            '  <KEYVALUE>a</KEYVALUE>\n'
            '</KEYBINDING>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "KEYBINDING with NAME using ASCII characters",
        dict(
            xml_str=''
            '<KEYBINDING NAME="Foo">\n'
            '  <KEYVALUE>a</KEYVALUE>\n'
            '</KEYBINDING>\n',
            exp_result=(u'Foo', u'a'),
        ),
        None, None, True
    ),
    (
        "KEYBINDING with NAME using non-ASCII UCS-2 characters",
        dict(
            xml_str=b''
            b'<KEYBINDING NAME="Foo\xC3\xA9">\n'
            b'  <KEYVALUE>a</KEYVALUE>\n'
            b'</KEYBINDING>\n',
            exp_result=(u'Foo\u00E9', u'a'),
        ),
        None, None, True
    ),
    (
        "KEYBINDING with NAME using non-UCS-2 characters",
        dict(
            xml_str=b''
            b'<KEYBINDING NAME="Foo\xF0\x90\x85\x82">\n'
            b'  <KEYVALUE>a</KEYVALUE>\n'
            b'</KEYBINDING>\n',
            exp_result=(u'Foo\U00010142', u'a'),
        ),
        None, None, True
    ),
    (
        "KEYBINDING with KEYVALUE child (normal case)",
        dict(
            xml_str=''
            '<KEYBINDING NAME="Foo">\n'
            '  <KEYVALUE>a</KEYVALUE>\n'
            '</KEYBINDING>\n',
            exp_result=(u'Foo', u'a'),
        ),
        None, None, True
    ),
    (
        "KEYBINDING with KEYVALUE child (empty name)",
        dict(
            xml_str=''
            '<KEYBINDING NAME="">\n'
            '  <KEYVALUE>a</KEYVALUE>\n'
            '</KEYBINDING>\n',
            exp_result=(u'', u'a'),
        ),
        None, None, True
    ),
    (
        "KEYBINDING with VALUE.REFERENCE child (normal case)",
        dict(
            xml_str=''
            '<KEYBINDING NAME="Foo">\n'
            '  <VALUE.REFERENCE>\n'
            '    <INSTANCENAME CLASSNAME="CIM_Foo"/>\n'
            '  </VALUE.REFERENCE>\n'
            '</KEYBINDING>\n',
            exp_result=(u'Foo', CIMInstanceName('CIM_Foo')),
        ),
        None, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_REQUIRED_KEYBINDING_ELEMENT)
@simplified_test_function
def test_required_KEYBINDING_element(
        testcase, xml_str, exp_result):
    """
    Test CIMXMLParser.required_KEYBINDING_element().
    """

    parser = CIMXMLParser(xml_str)

    # Code to be tested
    result = parser.required_KEYBINDING_element()

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None, \
        "Expected exception {!r} has not been raised".\
        format(testcase.exp_exc_types)

    assert result == exp_result


TESTCASES_REQUIRED_KEYVALUE_ELEMENT = [

    # Testcases with general invalidities
    (
        "No KEYVALUE but different element",
        dict(
            xml_str='<KEYVALUE.XXX/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "KEYVALUE with invalid child element",
        dict(
            xml_str=''
            '<KEYVALUE>\n'
            '  <XXX/>\n'
            '</KEYVALUE>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "KEYVALUE with invalid value for attribute VALUETYPE",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="bla">a</KEYVALUE>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "KEYVALUE with invalid value for attribute TYPE",
        dict(
            xml_str=''
            '<KEYVALUE TYPE="bla">a</KEYVALUE>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),

    # Testcases without VALUETYPE (defaults to string) and without TYPE
    (
        "KEYVALUE without VALUETYPE or TYPE (empty string)",
        dict(
            xml_str=''
            '<KEYVALUE></KEYVALUE>\n',
            exp_result=u'',
        ),
        None, None, True
    ),
    (
        "KEYVALUE without VALUETYPE or TYPE (WS string)",
        dict(
            xml_str=''
            '<KEYVALUE>  </KEYVALUE>\n',
            exp_result=u'  ',
        ),
        None, None, True
    ),
    (
        "KEYVALUE without VALUETYPE or TYPE (ASCII string)",
        dict(
            xml_str=''
            '<KEYVALUE>abc</KEYVALUE>\n',
            exp_result=u'abc',
        ),
        None, None, True
    ),
    (
        "KEYVALUE without VALUETYPE or TYPE (ASCII string with whitespace)",
        dict(
            xml_str=''
            '<KEYVALUE> a  b c </KEYVALUE>\n',
            exp_result=u' a  b c ',
        ),
        None, None, True
    ),
    (
        "KEYVALUE without VALUETYPE or TYPE (non-ASCII string)",
        dict(
            xml_str=b''
            b'<KEYVALUE>\xC3\xA9</KEYVALUE>\n',
            exp_result=u'\u00E9',  # LATIN SMALL LETTER E WITH ACUTE
        ),
        None, None, True
    ),
    (
        "KEYVALUE without VALUETYPE or TYPE (decimal as string)",
        dict(
            xml_str=''
            '<KEYVALUE>42</KEYVALUE>\n',
            exp_result=u'42',
        ),
        None, None, True
    ),
    (
        "KEYVALUE without VALUETYPE or TYPE (decimal as string with whitesp.)",
        dict(
            xml_str=''
            '<KEYVALUE> 42 </KEYVALUE>\n',
            exp_result=u' 42 ',
        ),
        None, None, True
    ),
    (
        "KEYVALUE without VALUETYPE or TYPE (float as string)",
        dict(
            xml_str=''
            '<KEYVALUE>42.1</KEYVALUE>\n',
            exp_result=u'42.1',
        ),
        None, None, True
    ),
    (
        "KEYVALUE without VALUETYPE or TYPE (float as string with whitesp.)",
        dict(
            xml_str=''
            '<KEYVALUE> 42.1 </KEYVALUE>\n',
            exp_result=u' 42.1 ',
        ),
        None, None, True
    ),
    (
        "KEYVALUE without VALUETYPE or TYPE (true as string)",
        dict(
            xml_str=''
            '<KEYVALUE>true</KEYVALUE>\n',
            exp_result=u'true',
        ),
        None, None, True
    ),
    (
        "KEYVALUE without VALUETYPE or TYPE (false as string)",
        dict(
            xml_str=''
            '<KEYVALUE>false</KEYVALUE>\n',
            exp_result=u'false',
        ),
        None, None, True
    ),
    (
        "KEYVALUE without VALUETYPE or TYPE (true as string with whitespace)",
        dict(
            xml_str=''
            '<KEYVALUE> true </KEYVALUE>\n',
            exp_result=u' true ',
        ),
        None, None, True
    ),
    (
        "KEYVALUE without VALUETYPE or TYPE (datetime string)",
        dict(
            xml_str=''
            '<KEYVALUE>20140924193040.654321+120</KEYVALUE>\n',
            exp_result=u'20140924193040.654321+120',
        ),
        None, None, True
    ),

    # Testcases without VALUETYPE and with TYPE that is empty (but present).
    # Note that this does not conform to DSP0201 but is returned by some
    # WBEM servers. It is interpreted by pywbem as defaulting to string.
    (
        "KEYVALUE without VALUETYPE and with empty TYPE (empty string)",
        dict(
            xml_str=''
            '<KEYVALUE TYPE=""></KEYVALUE>\n',
            exp_result=u'',
        ),
        None, None, True
    ),
    (
        "KEYVALUE without VALUETYPE and with empty TYPE (WS string)",
        dict(
            xml_str=''
            '<KEYVALUE TYPE="">  </KEYVALUE>\n',
            exp_result=u'  ',
        ),
        None, None, True
    ),
    (
        "KEYVALUE without VALUETYPE and with empty TYPE (ASCII string)",
        dict(
            xml_str=''
            '<KEYVALUE TYPE="">abc</KEYVALUE>\n',
            exp_result=u'abc',
        ),
        None, None, True
    ),
    (
        "KEYVALUE without VALUETYPE and with empty TYPE "
        "(ASCII string with whitespace)",
        dict(
            xml_str=''
            '<KEYVALUE TYPE=""> a  b c </KEYVALUE>\n',
            exp_result=u' a  b c ',
        ),
        None, None, True
    ),
    (
        "KEYVALUE without VALUETYPE and with empty TYPE (non-ASCII string)",
        dict(
            xml_str=b''
            b'<KEYVALUE TYPE="">\xC3\xA9</KEYVALUE>\n',
            exp_result=u'\u00E9',  # LATIN SMALL LETTER E WITH ACUTE
        ),
        None, None, True
    ),
    (
        "KEYVALUE without VALUETYPE and with empty TYPE (decimal as string)",
        dict(
            xml_str=''
            '<KEYVALUE TYPE="">42</KEYVALUE>\n',
            exp_result=u'42',
        ),
        None, None, True
    ),
    (
        "KEYVALUE without VALUETYPE and with empty TYPE "
        "(decimal as string with whitesp.)",
        dict(
            xml_str=''
            '<KEYVALUE TYPE=""> 42 </KEYVALUE>\n',
            exp_result=u' 42 ',
        ),
        None, None, True
    ),
    (
        "KEYVALUE without VALUETYPE and with empty TYPE (float as string)",
        dict(
            xml_str=''
            '<KEYVALUE TYPE="">42.1</KEYVALUE>\n',
            exp_result=u'42.1',
        ),
        None, None, True
    ),
    (
        "KEYVALUE without VALUETYPE and with empty TYPE "
        "(float as string with whitesp.)",
        dict(
            xml_str=''
            '<KEYVALUE TYPE=""> 42.1 </KEYVALUE>\n',
            exp_result=u' 42.1 ',
        ),
        None, None, True
    ),
    (
        "KEYVALUE without VALUETYPE and with empty TYPE (true as string)",
        dict(
            xml_str=''
            '<KEYVALUE TYPE="">true</KEYVALUE>\n',
            exp_result=u'true',
        ),
        None, None, True
    ),
    (
        "KEYVALUE without VALUETYPE and with empty TYPE (false as string)",
        dict(
            xml_str=''
            '<KEYVALUE TYPE="">false</KEYVALUE>\n',
            exp_result=u'false',
        ),
        None, None, True
    ),
    (
        "KEYVALUE without VALUETYPE and with empty TYPE "
        "(true as string with whitespace)",
        dict(
            xml_str=''
            '<KEYVALUE TYPE=""> true </KEYVALUE>\n',
            exp_result=u' true ',
        ),
        None, None, True
    ),
    (
        "KEYVALUE without VALUETYPE and with empty TYPE (datetime string)",
        dict(
            xml_str=''
            '<KEYVALUE TYPE="">20140924193040.654321+120</KEYVALUE>\n',
            exp_result=u'20140924193040.654321+120',
        ),
        None, None, True
    ),

    # Testcases without VALUETYPE (defaults to string) but with TYPE string
    (
        "KEYVALUE without VALUETYPE and contradicting TYPE uint8",
        dict(
            xml_str=''
            '<KEYVALUE TYPE="uint8">42</KEYVALUE>\n',
            exp_result=Uint8(42),
        ),
        None, None, True
    ),
    (
        "KEYVALUE without VALUETYPE with TYPE string (ASCII string)",
        dict(
            xml_str=''
            '<KEYVALUE TYPE="string">abc</KEYVALUE>\n',
            exp_result=u'abc',
        ),
        None, None, True
    ),
    (
        "KEYVALUE without VALUETYPE with TYPE string (ASCII string with WS)",
        dict(
            xml_str=''
            '<KEYVALUE TYPE="string"> a  b c </KEYVALUE>\n',
            exp_result=u' a  b c ',
        ),
        None, None, True
    ),
    (
        "KEYVALUE without VALUETYPE with TYPE string (non-ASCII string)",
        dict(
            xml_str=b''
            b'<KEYVALUE TYPE="string">\xC3\xA9</KEYVALUE>\n',
            exp_result=u'\u00E9',  # LATIN SMALL LETTER E WITH ACUTE
        ),
        None, None, True
    ),
    (
        "KEYVALUE without VALUETYPE with TYPE string (non-UCS-2 char)",
        dict(
            # U+010142: GREEK ACROPHONIC ATTIC ONE DRACHMA
            xml_str=b''
            b'<KEYVALUE TYPE="string">\xF0\x90\x85\x82</KEYVALUE>\n',
            exp_result=u'\U00010142',
        ),
        None, None, True
    ),
    (
        "KEYVALUE without VALUETYPE with TYPE string (decimal as string)",
        dict(
            xml_str=''
            '<KEYVALUE TYPE="string">42</KEYVALUE>\n',
            exp_result=u'42',
        ),
        None, None, True
    ),
    (
        "KEYVALUE without VALUETYPE with TYPE string (decimal as str with WS)",
        dict(
            xml_str=''
            '<KEYVALUE TYPE="string"> 42 </KEYVALUE>\n',
            exp_result=u' 42 ',
        ),
        None, None, True
    ),
    (
        "KEYVALUE without VALUETYPE with TYPE string (float as string)",
        dict(
            xml_str=''
            '<KEYVALUE TYPE="string">42.1</KEYVALUE>\n',
            exp_result=u'42.1',
        ),
        None, None, True
    ),
    (
        "KEYVALUE without VALUETYPE with TYPE string (float as string with WS)",
        dict(
            xml_str=''
            '<KEYVALUE TYPE="string"> 42.1 </KEYVALUE>\n',
            exp_result=u' 42.1 ',
        ),
        None, None, True
    ),
    (
        "KEYVALUE without VALUETYPE with TYPE string (true as string)",
        dict(
            xml_str=''
            '<KEYVALUE TYPE="string">true</KEYVALUE>\n',
            exp_result=u'true',
        ),
        None, None, True
    ),
    (
        "KEYVALUE without VALUETYPE with TYPE string (false as string)",
        dict(
            xml_str=''
            '<KEYVALUE TYPE="string">false</KEYVALUE>\n',
            exp_result=u'false',
        ),
        None, None, True
    ),
    (
        "KEYVALUE without VALUETYPE with TYPE string (true as string with WS)",
        dict(
            xml_str=''
            '<KEYVALUE TYPE="string"> true </KEYVALUE>\n',
            exp_result=u' true ',
        ),
        None, None, True
    ),
    (
        "KEYVALUE without VALUETYPE with TYPE string (datetime string)",
        dict(
            xml_str=''
            '<KEYVALUE TYPE="string">20140924193040.654321+120</KEYVALUE>\n',
            exp_result=u'20140924193040.654321+120',
        ),
        None, None, True
    ),

    # Testcases without VALUETYPE (defaults to string) but with TYPE char16
    (
        "KEYVALUE without VALUETYPE with TYPE char16 (invalid empty char)",
        dict(
            xml_str=''
            '<KEYVALUE TYPE="char16"></KEYVALUE>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "KEYVALUE without VALUETYPE with TYPE char16 (invalid two chars)",
        dict(
            xml_str=''
            '<KEYVALUE TYPE="char16">ab</KEYVALUE>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "KEYVALUE without VALUETYPE with TYPE char16 (WS char)",
        dict(
            xml_str=''
            '<KEYVALUE TYPE="char16"> </KEYVALUE>\n',
            exp_result=u' ',
        ),
        None, None, True
    ),
    (
        "KEYVALUE without VALUETYPE with TYPE char16 (ASCII char)",
        dict(
            xml_str=''
            '<KEYVALUE TYPE="char16">a</KEYVALUE>\n',
            exp_result=u'a',
        ),
        None, None, True
    ),
    (
        "KEYVALUE without VALUETYPE with TYPE char16 (non-ASCII UCS-2 char)",
        dict(
            xml_str=b''
            b'<KEYVALUE TYPE="char16">\xC3\xA9</KEYVALUE>\n',
            exp_result=u'\u00E9',  # LATIN SMALL LETTER E WITH ACUTE
        ),
        None, None, True
    ),
    (
        "KEYVALUE without VALUETYPE with TYPE char16 (non-UCS-2 char)",
        dict(
            # U+010142: GREEK ACROPHONIC ATTIC ONE DRACHMA
            xml_str=b''
            b'<KEYVALUE TYPE="char16">\xF0\x90\x85\x82</KEYVALUE>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "KEYVALUE without VALUETYPE with TYPE char16 (decimal as string)",
        dict(
            xml_str=''
            '<KEYVALUE TYPE="char16">4</KEYVALUE>\n',
            exp_result=u'4',
        ),
        None, None, True
    ),

    # Testcases without VALUETYPE (def. to string) but with TYPE datetime
    (
        "KEYVALUE without VALUETYPE with TYPE datetime (empty string)",
        dict(
            xml_str=''
            '<KEYVALUE TYPE="datetime"></KEYVALUE>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "KEYVALUE without VALUETYPE with TYPE datetime (WS char)",
        dict(
            xml_str=''
            '<KEYVALUE TYPE="datetime"> </KEYVALUE>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "KEYVALUE without VALUETYPE with TYPE datetime (ASCII char)",
        dict(
            xml_str=''
            '<KEYVALUE TYPE="datetime">a</KEYVALUE>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "KEYVALUE without VALUETYPE with TYPE datetime (decimal as string)",
        dict(
            xml_str=''
            '<KEYVALUE TYPE="datetime">4</KEYVALUE>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "KEYVALUE without VALUETYPE with TYPE datetime (point in time string)",
        dict(
            xml_str=''
            '<KEYVALUE TYPE="datetime">20140924193040.654321+120</KEYVALUE>\n',
            exp_result=CIMDateTime('20140924193040.654321+120'),
        ),
        None, None, True
    ),
    (
        "KEYVALUE without VALUETYPE with TYPE datetime (interval string)",
        dict(
            xml_str=''
            '<KEYVALUE TYPE="datetime">00000183132542.234567:000</KEYVALUE>\n',
            exp_result=CIMDateTime('00000183132542.234567:000'),
        ),
        None, None, True
    ),

    # Testcases with VALUETYPE string and TYPE string
    (
        "KEYVALUE with VALUETYPE string and contradicting TYPE uint8",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="string" TYPE="uint8">42</KEYVALUE>\n',
            exp_result=Uint8(42),
        ),
        None, None, True
    ),
    (
        "KEYVALUE with VALUETYPE string and TYPE string (empty string)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="string" TYPE="string"></KEYVALUE>\n',
            exp_result=u'',
        ),
        None, None, True
    ),
    (
        "KEYVALUE with VALUETYPE string and TYPE string (WS string)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="string" TYPE="string">  </KEYVALUE>\n',
            exp_result=u'  ',
        ),
        None, None, True
    ),
    (
        "KEYVALUE with VALUETYPE string and TYPE string (ASCII string)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="string" TYPE="string">abc</KEYVALUE>\n',
            exp_result=u'abc',
        ),
        None, None, True
    ),

    # Testcases with VALUETYPE string and TYPE char16
    (
        "KEYVALUE with VALUETYPE string and TYPE char16 (invalid empty char)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="string" TYPE="char16"></KEYVALUE>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "KEYVALUE with VALUETYPE string and TYPE char16 (invalid two chars)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="string" TYPE="char16">ab</KEYVALUE>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "KEYVALUE with VALUETYPE string and TYPE char16 (WS char)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="string" TYPE="char16"> </KEYVALUE>\n',
            exp_result=u' ',
        ),
        None, None, True
    ),
    (
        "KEYVALUE with VALUETYPE string and TYPE char16 (ASCII char)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="string" TYPE="char16">a</KEYVALUE>\n',
            exp_result=u'a',
        ),
        None, None, True
    ),

    # Testcases with VALUETYPE string and TYPE datetime
    (
        "KEYVALUE with VALUETYPE string and TYPE datetime (empty string)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="string" TYPE="datetime"></KEYVALUE>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "KEYVALUE with VALUETYPE string and TYPE datetime (point in time)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="string"'
            ' TYPE="datetime">20140924193040.654321+120</KEYVALUE>\n',
            exp_result=CIMDateTime('20140924193040.654321+120'),
        ),
        None, None, True
    ),

    # Testcases with VALUETYPE boolean but without TYPE
    (
        "KEYVALUE with VALUETYPE boolean without TYPE (empty string)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="boolean"></KEYVALUE>\n',
            exp_result=None,
        ),
        None, ToleratedServerIssueWarning, True
    ),
    (
        "KEYVALUE with VALUETYPE boolean without TYPE (WS string)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="boolean">  </KEYVALUE>\n',
            exp_result=None,
        ),
        None, ToleratedServerIssueWarning, True
    ),
    (
        "KEYVALUE with VALUETYPE boolean without TYPE (ASCII string)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="boolean">abc</KEYVALUE>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "KEYVALUE with VALUETYPE boolean without TYPE (1 as string)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="boolean">1</KEYVALUE>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "KEYVALUE with VALUETYPE boolean without TYPE (0 as string)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="boolean">0</KEYVALUE>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "KEYVALUE with VALUETYPE boolean without TYPE (true as string)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="boolean">true</KEYVALUE>\n',
            exp_result=True,
        ),
        None, None, True
    ),
    (
        "KEYVALUE with VALUETYPE boolean without TYPE (false as string)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="boolean">false</KEYVALUE>\n',
            exp_result=False,
        ),
        None, None, True
    ),
    (
        "KEYVALUE with VALUETYPE boolean without TYPE (true as string with WS)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="boolean"> true </KEYVALUE>\n',
            exp_result=True,
        ),
        None, None, True
    ),
    (
        "KEYVALUE with VALUETYPE boolean without TYPE (false as str with WS)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="boolean"> false </KEYVALUE>\n',
            exp_result=False,
        ),
        None, None, True
    ),
    (
        "KEYVALUE with VALUETYPE boolean without TYPE (tRuE as string)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="boolean">tRuE</KEYVALUE>\n',
            exp_result=True,
        ),
        None, None, True
    ),
    (
        "KEYVALUE with VALUETYPE boolean without TYPE (fAlSe as string)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="boolean">fAlSe</KEYVALUE>\n',
            exp_result=False,
        ),
        None, None, True
    ),

    # Testcases with VALUETYPE boolean and with TYPE boolean
    (
        "KEYVALUE with VALUETYPE boolean with TYPE boolean (empty string)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="boolean" TYPE="boolean"></KEYVALUE>\n',
            exp_result=None,
        ),
        None, ToleratedServerIssueWarning, True
    ),
    (
        "KEYVALUE with VALUETYPE boolean with TYPE boolean (WS string)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="boolean" TYPE="boolean">  </KEYVALUE>\n',
            exp_result=None,
        ),
        None, ToleratedServerIssueWarning, True
    ),
    (
        "KEYVALUE with VALUETYPE boolean with TYPE boolean (ASCII string)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="boolean" TYPE="boolean">abc</KEYVALUE>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "KEYVALUE with VALUETYPE boolean with TYPE boolean (1 as string)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="boolean" TYPE="boolean">1</KEYVALUE>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "KEYVALUE with VALUETYPE boolean with TYPE boolean (0 as string)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="boolean" TYPE="boolean">0</KEYVALUE>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "KEYVALUE with VALUETYPE boolean with TYPE boolean (true as string)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="boolean" TYPE="boolean">true</KEYVALUE>\n',
            exp_result=True,
        ),
        None, None, True
    ),
    (
        "KEYVALUE with VALUETYPE boolean with TYPE boolean (false as string)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="boolean" TYPE="boolean">false</KEYVALUE>\n',
            exp_result=False,
        ),
        None, None, True
    ),
    (
        "KEYVALUE with VALUETYPE boolean with TYPE boolean (true with WS)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="boolean" TYPE="boolean"> true </KEYVALUE>\n',
            exp_result=True,
        ),
        None, None, True
    ),
    (
        "KEYVALUE with VALUETYPE boolean with TYPE boolean (false with WS)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="boolean" TYPE="boolean"> false </KEYVALUE>\n',
            exp_result=False,
        ),
        None, None, True
    ),
    (
        "KEYVALUE with VALUETYPE boolean with TYPE boolean (tRuE as string)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="boolean" TYPE="boolean">tRuE</KEYVALUE>\n',
            exp_result=True,
        ),
        None, None, True
    ),
    (
        "KEYVALUE with VALUETYPE boolean with TYPE boolean (fAlSe as string)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="boolean" TYPE="boolean">fAlSe</KEYVALUE>\n',
            exp_result=False,
        ),
        None, None, True
    ),

    # Testcases with VALUETYPE numeric but without TYPE
    (
        "KEYVALUE with VALUETYPE numeric without TYPE (empty string)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="numeric"></KEYVALUE>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "KEYVALUE with VALUETYPE numeric without TYPE (WS string)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="numeric">  </KEYVALUE>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "KEYVALUE with VALUETYPE numeric without TYPE (ASCII string)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="numeric">abc</KEYVALUE>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "KEYVALUE with VALUETYPE numeric without TYPE (decimal string 0)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="numeric">0</KEYVALUE>\n',
            exp_result=0,
        ),
        None, None, True
    ),
    (
        "KEYVALUE with VALUETYPE numeric without TYPE (decimal string 42)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="numeric">42</KEYVALUE>\n',
            exp_result=42,
        ),
        None, None, True
    ),
    (
        "KEYVALUE with VALUETYPE numeric without TYPE (decimal string -42)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="numeric">-42</KEYVALUE>\n',
            exp_result=-42,
        ),
        None, None, True
    ),
    (
        "KEYVALUE with VALUETYPE numeric without TYPE (decimal string that "
        "exceeds Python 2 positive int limit but not uint64)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="numeric">9223372036854775808</KEYVALUE>\n',
            exp_result=9223372036854775808,
        ),
        None, None, True
    ),
    (
        "KEYVALUE with VALUETYPE numeric without TYPE (decimal string that "
        "exceeds Python 2 negative int limit and also sint64)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="numeric">-9223372036854775809</KEYVALUE>\n',
            exp_result=-9223372036854775809,
        ),
        None, None, True
    ),
    (
        "KEYVALUE with VALUETYPE numeric without TYPE (decimal string that "
        "exceeds Python 2 positive int limit and also uint64)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="numeric">18446744073709551616</KEYVALUE>\n',
            exp_result=18446744073709551616,
        ),
        None, None, True
    ),
    (
        "KEYVALUE with VALUETYPE numeric without TYPE (hex string 0xA0)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="numeric">0xA0</KEYVALUE>\n',
            exp_result=160,
        ),
        None, None, True
    ),
    (
        "KEYVALUE with VALUETYPE numeric without TYPE (hex string 0Xa0)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="numeric">0Xa0</KEYVALUE>\n',
            exp_result=160,
        ),
        None, None, True
    ),
    (
        "KEYVALUE with VALUETYPE numeric without TYPE (hex string -0xA0)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="numeric">-0xA0</KEYVALUE>\n',
            exp_result=-160,
        ),
        None, None, True
    ),
    (
        "KEYVALUE with VALUETYPE numeric without TYPE (hex string +0xA0)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="numeric">+0xA0</KEYVALUE>\n',
            exp_result=160,
        ),
        None, None, True
    ),
    (
        "KEYVALUE with VALUETYPE numeric without TYPE (hex string that "
        "exceeds Python 2 positive int limit but not uint64)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="numeric">0x8000000000000000</KEYVALUE>\n',
            exp_result=9223372036854775808,
        ),
        None, None, True
    ),
    (
        "KEYVALUE with VALUETYPE numeric without TYPE (hex string that "
        "exceeds Python 2 negative int limit and also sint64)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="numeric">-0x8000000000000001</KEYVALUE>\n',
            exp_result=-9223372036854775809,
        ),
        None, None, True
    ),
    (
        "KEYVALUE with VALUETYPE numeric without TYPE (hex string that "
        "exceeds Python 2 positive int limit and also uint64)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="numeric">0x10000000000000000</KEYVALUE>\n',
            exp_result=18446744073709551616,
        ),
        None, None, True
    ),
    (
        "KEYVALUE with VALUETYPE numeric without TYPE (float string 42.0)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="numeric">42.0</KEYVALUE>\n',
            exp_result=42.0,
        ),
        None, None, True
    ),
    (
        "KEYVALUE with VALUETYPE numeric without TYPE (float string .0)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="numeric">.0</KEYVALUE>\n',
            exp_result=0.0,
        ),
        None, None, True
    ),
    (
        "KEYVALUE with VALUETYPE numeric without TYPE (float string -.1e-12)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="numeric">-.1e-12</KEYVALUE>\n',
            exp_result=-0.1E-12,
        ),
        None, None, True
    ),
    (
        "KEYVALUE with VALUETYPE numeric without TYPE (float string .1E12)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="numeric">.1e12</KEYVALUE>\n',
            exp_result=0.1E+12,
        ),
        None, None, True
    ),
    (
        "KEYVALUE with VALUETYPE numeric without TYPE (float string +.1e+12)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="numeric">.1e12</KEYVALUE>\n',
            exp_result=0.1E+12,
        ),
        None, None, True
    ),

    # Testcases with VALUETYPE numeric and TYPE (sintNN/uintNN/realNN)
    (
        "KEYVALUE with VALUETYPE numeric and TYPE uint32 and numeric value "
        "with invalid decimal digits",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="numeric" TYPE="uint32">9a</KEYVALUE>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "KEYVALUE with VALUETYPE numeric and TYPE uint8 and numeric value that "
        "exceeds the data type limit",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="numeric" TYPE="uint8">1234</KEYVALUE>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "KEYVALUE with VALUETYPE numeric and TYPE uint8 (empty string)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="numeric" TYPE="uint8"></KEYVALUE>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "KEYVALUE with VALUETYPE numeric and TYPE sint64 (WS string)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="numeric" TYPE="sint64">  </KEYVALUE>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "KEYVALUE with VALUETYPE numeric and TYPE real32 (ASCII string)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="numeric" TYPE="real32">abc</KEYVALUE>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "KEYVALUE with VALUETYPE numeric and TYPE uint8 (decimal string 0)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="numeric" TYPE="uint8">0</KEYVALUE>\n',
            exp_result=Uint8(0),
        ),
        None, None, True
    ),
    (
        "KEYVALUE with VALUETYPE numeric and TYPE uint16 (decimal string 42)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="numeric" TYPE="uint16">42</KEYVALUE>\n',
            exp_result=Uint16(42),
        ),
        None, None, True
    ),
    (
        "KEYVALUE with VALUETYPE numeric and TYPE sint16 (decimal string -42)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="numeric" TYPE="sint16">-42</KEYVALUE>\n',
            exp_result=Sint16(-42),
        ),
        None, None, True
    ),
    (
        "KEYVALUE with VALUETYPE numeric and TYPE uint8 (decimal max neg.)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="numeric" TYPE="uint8">0</KEYVALUE>\n',
            exp_result=Uint8(0),
        ),
        None, None, True
    ),
    (
        "KEYVALUE with VALUETYPE numeric and TYPE uint8 (decimal max pos.)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="numeric" TYPE="uint8">255</KEYVALUE>\n',
            exp_result=Uint8(255),
        ),
        None, None, True
    ),
    (
        "KEYVALUE with VALUETYPE numeric and TYPE uint16 (decimal max neg.)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="numeric" TYPE="uint16">0</KEYVALUE>\n',
            exp_result=Uint16(0),
        ),
        None, None, True
    ),
    (
        "KEYVALUE with VALUETYPE numeric and TYPE uint16 (decimal max pos.)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="numeric" TYPE="uint16">65535</KEYVALUE>\n',
            exp_result=Uint16(65535),
        ),
        None, None, True
    ),
    (
        "KEYVALUE with VALUETYPE numeric and TYPE uint32 (decimal max neg.)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="numeric" TYPE="uint32">0</KEYVALUE>\n',
            exp_result=Uint32(0),
        ),
        None, None, True
    ),
    (
        "KEYVALUE with VALUETYPE numeric and TYPE uint32 (decimal max pos.)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="numeric"'
            ' TYPE="uint32">4294967295</KEYVALUE>\n',
            exp_result=Uint32(4294967295),
        ),
        None, None, True
    ),
    (
        "KEYVALUE with VALUETYPE numeric and TYPE uint64 (decimal max neg.)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="numeric" TYPE="uint64">0</KEYVALUE>\n',
            exp_result=Uint64(0),
        ),
        None, None, True
    ),
    (
        "KEYVALUE with VALUETYPE numeric and TYPE uint64 (decimal max pos., "
        "exceeds Python 2 positive int limit but not uint64)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="numeric"'
            ' TYPE="uint64">18446744073709551615</KEYVALUE>\n',
            exp_result=Uint64(18446744073709551615),
        ),
        None, None, True
    ),
    (
        "KEYVALUE with VALUETYPE numeric and TYPE sint8 (decimal max neg.)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="numeric" TYPE="sint8">-128</KEYVALUE>\n',
            exp_result=Sint8(-128),
        ),
        None, None, True
    ),
    (
        "KEYVALUE with VALUETYPE numeric and TYPE sint8 (decimal max pos.)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="numeric" TYPE="sint8">127</KEYVALUE>\n',
            exp_result=Sint8(127),
        ),
        None, None, True
    ),
    (
        "KEYVALUE with VALUETYPE numeric and TYPE sint16 (decimal max neg.)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="numeric" TYPE="sint16">-32768</KEYVALUE>\n',
            exp_result=Sint16(-32768),
        ),
        None, None, True
    ),
    (
        "KEYVALUE with VALUETYPE numeric and TYPE sint16 (decimal max pos.)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="numeric" TYPE="sint16">32767</KEYVALUE>\n',
            exp_result=Sint16(32767),
        ),
        None, None, True
    ),
    (
        "KEYVALUE with VALUETYPE numeric and TYPE sint32 (decimal max neg.)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="numeric"'
            ' TYPE="sint32">-2147483648</KEYVALUE>\n',
            exp_result=Sint32(-2147483648),
        ),
        None, None, True
    ),
    (
        "KEYVALUE with VALUETYPE numeric and TYPE sint32 (decimal max pos.)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="numeric"'
            ' TYPE="sint32">2147483647</KEYVALUE>\n',
            exp_result=Sint32(2147483647),
        ),
        None, None, True
    ),
    (
        "KEYVALUE with VALUETYPE numeric and TYPE sint64 (decimal max neg., "
        "exceeds Python 2 negative int limit but not sint64)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="numeric"'
            ' TYPE="sint64">-9223372036854775808</KEYVALUE>\n',
            exp_result=Sint64(-9223372036854775808),
        ),
        None, None, True
    ),
    (
        "KEYVALUE with VALUETYPE numeric and TYPE sint64 (decimal max pos., "
        "exceeds Python 2 positive int limit but not sint64)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="numeric"'
            ' TYPE="sint64">9223372036854775807</KEYVALUE>\n',
            exp_result=Sint64(9223372036854775807),
        ),
        None, None, True
    ),
    (
        "KEYVALUE with VALUETYPE numeric and TYPE sint64 (decimal max neg., "
        "exceeds Python 2 negative int limit and also sint64)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="numeric"'
            ' TYPE="sint64">-9223372036854775809</KEYVALUE>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "KEYVALUE with VALUETYPE numeric and TYPE uint32 (hex string 0xA0)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="numeric" TYPE="uint32">0xA0</KEYVALUE>\n',
            exp_result=Uint32(160),
        ),
        None, None, True
    ),
    (
        "KEYVALUE with VALUETYPE numeric and TYPE uint32 (hex string 0Xa0)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="numeric" TYPE="uint32">0Xa0</KEYVALUE>\n',
            exp_result=Uint32(160),
        ),
        None, None, True
    ),
    (
        "KEYVALUE with VALUETYPE numeric and TYPE sint32 (hex string -0xA0)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="numeric" TYPE="sint32">-0xA0</KEYVALUE>\n',
            exp_result=Sint32(-160),
        ),
        None, None, True
    ),
    (
        "KEYVALUE with VALUETYPE numeric and TYPE uint32 (hex string +0xA0)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="numeric" TYPE="uint32">+0xA0</KEYVALUE>\n',
            exp_result=Uint32(160),
        ),
        None, None, True
    ),
    (
        "KEYVALUE with VALUETYPE numeric and TYPE uint64 (hex string, "
        "exceeds Python 2 positive int limit but not uint64)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="numeric"'
            ' TYPE="uint64">0x8000000000000000</KEYVALUE>\n',
            exp_result=Uint64(9223372036854775808),
        ),
        None, None, True
    ),
    (
        "KEYVALUE with VALUETYPE numeric and TYPE sint64 (hex string, "
        "exceeds Python 2 negative int limit and also sint64)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="numeric"'
            ' TYPE="sint64">-0x8000000000000001</KEYVALUE>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "KEYVALUE with VALUETYPE numeric and TYPE real32 (float str 42.0)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="numeric" TYPE="real32">42.0</KEYVALUE>\n',
            exp_result=Real32(42.0),
        ),
        None, None, True
    ),
    (
        "KEYVALUE with VALUETYPE numeric and TYPE real64 (float str .0)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="numeric" TYPE="real64">.0</KEYVALUE>\n',
            exp_result=Real64(0.0),
        ),
        None, None, True
    ),
    (
        "KEYVALUE with VALUETYPE numeric and TYPE real32 (float str -.1e-12)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="numeric" TYPE="real32">-.1e-12</KEYVALUE>\n',
            exp_result=Real32(-0.1E-12),
        ),
        None, None, True
    ),
    (
        "KEYVALUE with VALUETYPE numeric and TYPE real32 (float str .1E12)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="numeric" TYPE="real32">.1e12</KEYVALUE>\n',
            exp_result=Real32(0.1E+12),
        ),
        None, None, True
    ),
    (
        "KEYVALUE with VALUETYPE numeric and TYPE real32 (float str +.1e+12)",
        dict(
            xml_str=''
            '<KEYVALUE VALUETYPE="numeric" TYPE="real32">.1e12</KEYVALUE>\n',
            exp_result=Real32(0.1E+12),
        ),
        None, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_REQUIRED_KEYVALUE_ELEMENT)
@simplified_test_function
def test_required_KEYVALUE_element(
        testcase, xml_str, exp_result):
    """
    Test CIMXMLParser.required_KEYVALUE_element().
    """

    parser = CIMXMLParser(xml_str)

    # Code to be tested
    result = parser.required_KEYVALUE_element()

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None, \
        "Expected exception {!r} has not been raised".\
        format(testcase.exp_exc_types)

    assert result == exp_result


TESTCASES_REQUIRED_VALUE_REFERENCE_ELEMENT = [
    (
        "No VALUE.REFERENCE but different element",
        dict(
            xml_str='<VALUE.REFERENCE.XXX/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "VALUE.REFERENCE with invalid child element",
        dict(
            xml_str=''
            '<VALUE.REFERENCE>\n'
            '  <INSTANCENAME CLASSNAME="CIM_Foo"/>\n'
            '  <XXX/>\n'
            '</VALUE.REFERENCE>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "VALUE.REFERENCE with invalid content text",
        dict(
            xml_str=''
            '<VALUE.REFERENCE>\n'
            '  xxx\n'
            '  <INSTANCENAME CLASSNAME="CIM_Foo"/>\n'
            '</VALUE.REFERENCE>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "VALUE.REFERENCE with invalid trailing text",
        dict(
            xml_str=''
            '<VALUE.REFERENCE>\n'
            '  <INSTANCENAME CLASSNAME="CIM_Foo"/>\n'
            '  xxx\n'
            '</VALUE.REFERENCE>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "VALUE.REFERENCE with missing child element",
        dict(
            xml_str=''
            '<VALUE.REFERENCE/>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "VALUE.REFERENCE with ref value that is a INSTANCENAME",
        dict(
            xml_str=''
            '<VALUE.REFERENCE>\n'
            '  <INSTANCENAME CLASSNAME="CIM_Foo"/>\n'
            '</VALUE.REFERENCE>\n',
            exp_result=CIMInstanceName('CIM_Foo'),
        ),
        None, None, True
    ),
    (
        "VALUE.REFERENCE with ref value that is a LOCALINSTANCEPATH",
        dict(
            xml_str=''
            '<VALUE.REFERENCE>\n'
            '  <LOCALINSTANCEPATH>\n'
            '    <LOCALNAMESPACEPATH>\n'
            '      <NAMESPACE NAME="foo"/>\n'
            '    </LOCALNAMESPACEPATH>\n'
            '    <INSTANCENAME CLASSNAME="CIM_Foo"/>\n'
            '  </LOCALINSTANCEPATH>\n'
            '</VALUE.REFERENCE>\n',
            exp_result=CIMInstanceName(
                'CIM_Foo',
                namespace='foo'
            ),
        ),
        None, None, True
    ),
    (
        "VALUE.REFERENCE with ref value that is a INSTANCEPATH",
        dict(
            xml_str=''
            '<VALUE.REFERENCE>\n'
            '  <INSTANCEPATH>\n'
            '    <NAMESPACEPATH>\n'
            '      <HOST>woot.com</HOST>\n'
            '      <LOCALNAMESPACEPATH>\n'
            '        <NAMESPACE NAME="foo"/>\n'
            '      </LOCALNAMESPACEPATH>\n'
            '    </NAMESPACEPATH>\n'
            '    <INSTANCENAME CLASSNAME="CIM_Foo"/>\n'
            '  </INSTANCEPATH>\n'
            '</VALUE.REFERENCE>\n',
            exp_result=CIMInstanceName(
                'CIM_Foo',
                namespace='foo',
                host='woot.com',
            ),
        ),
        None, None, True
    ),
    (
        "VALUE.REFERENCE with ref value that is a CLASSNAME",
        dict(
            xml_str=''
            '<VALUE.REFERENCE>\n'
            '  <CLASSNAME NAME="CIM_Foo"/>\n'
            '</VALUE.REFERENCE>\n',
            exp_result=CIMClassName('CIM_Foo'),
        ),
        None, None, True
    ),
    (
        "VALUE.REFERENCE with ref value that is a LOCALCLASSPATH",
        dict(
            xml_str=''
            '<VALUE.REFERENCE>\n'
            '  <LOCALCLASSPATH>\n'
            '    <LOCALNAMESPACEPATH>\n'
            '      <NAMESPACE NAME="foo"/>\n'
            '    </LOCALNAMESPACEPATH>\n'
            '    <CLASSNAME NAME="CIM_Foo"/>\n'
            '  </LOCALCLASSPATH>\n'
            '</VALUE.REFERENCE>\n',
            exp_result=CIMClassName(
                'CIM_Foo',
                namespace='foo'
            ),
        ),
        None, None, True
    ),
    (
        "VALUE.REFERENCE with ref value that is a CLASSPATH",
        dict(
            xml_str=''
            '<VALUE.REFERENCE>\n'
            '  <CLASSPATH>\n'
            '    <NAMESPACEPATH>\n'
            '      <HOST>woot.com</HOST>\n'
            '      <LOCALNAMESPACEPATH>\n'
            '        <NAMESPACE NAME="foo"/>\n'
            '      </LOCALNAMESPACEPATH>\n'
            '    </NAMESPACEPATH>\n'
            '    <CLASSNAME NAME="CIM_Foo"/>\n'
            '  </CLASSPATH>\n'
            '</VALUE.REFERENCE>\n',
            exp_result=CIMClassName(
                'CIM_Foo',
                namespace='foo',
                host='woot.com',
            ),
        ),
        None, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_REQUIRED_VALUE_REFERENCE_ELEMENT)
@simplified_test_function
def test_required_VALUE_REFERENCE_element(
        testcase, xml_str, exp_result):
    """
    Test CIMXMLParser.required_VALUE_REFERENCE_element().
    """

    parser = CIMXMLParser(xml_str)

    # Code to be tested
    result = parser.required_VALUE_REFERENCE_element()

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None, \
        "Expected exception {!r} has not been raised".\
        format(testcase.exp_exc_types)

    assert result == exp_result


TESTCASES_LIST_OF_OBJECTPATH_ELEMENTS = [
    (
        "List of OBJECTPATH elements that is empty",
        dict(
            skip_events=1,
            xml_str=''
            '<DUMMY_ROOT>\n'
            '</DUMMY_ROOT>\n',
            exp_result=[],
        ),
        None, None, True
    ),
    (
        "List of OBJECTPATH elements with one item",
        dict(
            skip_events=1,
            xml_str=''
            '<DUMMY_ROOT>\n'
            '  <OBJECTPATH>\n'
            '    <CLASSPATH>\n'
            '      <NAMESPACEPATH>\n'
            '        <HOST>woot.com</HOST>\n'
            '        <LOCALNAMESPACEPATH>\n'
            '          <NAMESPACE NAME="foo"/>\n'
            '        </LOCALNAMESPACEPATH>\n'
            '      </NAMESPACEPATH>\n'
            '      <CLASSNAME NAME="CIM_Foo"/>\n'
            '    </CLASSPATH>\n'
            '  </OBJECTPATH>\n'
            '</DUMMY_ROOT>\n',
            exp_result=[
                CIMClassName(
                    'CIM_Foo',
                    namespace='foo',
                    host='woot.com',
                ),
            ],
        ),
        None, None, True
    ),
    (
        "List of OBJECTPATH elements with two items",
        dict(
            skip_events=1,
            xml_str=''
            '<DUMMY_ROOT>\n'
            '  <OBJECTPATH>\n'
            '    <CLASSPATH>\n'
            '      <NAMESPACEPATH>\n'
            '        <HOST>woot.com</HOST>\n'
            '        <LOCALNAMESPACEPATH>\n'
            '          <NAMESPACE NAME="foo"/>\n'
            '        </LOCALNAMESPACEPATH>\n'
            '      </NAMESPACEPATH>\n'
            '      <CLASSNAME NAME="CIM_Foo1"/>\n'
            '    </CLASSPATH>\n'
            '  </OBJECTPATH>\n'
            '  <OBJECTPATH>\n'
            '    <CLASSPATH>\n'
            '      <NAMESPACEPATH>\n'
            '        <HOST>woot.com</HOST>\n'
            '        <LOCALNAMESPACEPATH>\n'
            '          <NAMESPACE NAME="foo"/>\n'
            '        </LOCALNAMESPACEPATH>\n'
            '      </NAMESPACEPATH>\n'
            '      <CLASSNAME NAME="CIM_Foo2"/>\n'
            '    </CLASSPATH>\n'
            '  </OBJECTPATH>\n'
            '</DUMMY_ROOT>\n',
            exp_result=[
                CIMClassName(
                    'CIM_Foo1',
                    namespace='foo',
                    host='woot.com',
                ),
                CIMClassName(
                    'CIM_Foo2',
                    namespace='foo',
                    host='woot.com',
                ),
            ],
        ),
        None, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_LIST_OF_OBJECTPATH_ELEMENTS)
@simplified_test_function
def test_list_of_OBJECTPATH_elements(
        testcase, skip_events, xml_str, exp_result):
    """
    Test CIMXMLParser.list_of_OBJECTPATH_elements().
    """

    parser = CIMXMLParser(xml_str)
    for _ in range(skip_events):
        parser.get_next_event()

    # Code to be tested
    result = parser.list_of_OBJECTPATH_elements()

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None, \
        "Expected exception {!r} has not been raised".\
        format(testcase.exp_exc_types)

    assert result == exp_result


TESTCASES_REQUIRED_OBJECTPATH_ELEMENT = [
    (
        "No OBJECTPATH but different element",
        dict(
            xml_str='<OBJECTPATH.XXX/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "OBJECTPATH with invalid child element",
        dict(
            xml_str=''
            '<OBJECTPATH>\n'
            '  <CLASSPATH>\n'
            '    <NAMESPACEPATH>\n'
            '      <HOST>woot.com</HOST>\n'
            '      <LOCALNAMESPACEPATH>\n'
            '        <NAMESPACE NAME="foo"/>\n'
            '      </LOCALNAMESPACEPATH>\n'
            '    </NAMESPACEPATH>\n'
            '    <CLASSNAME NAME="CIM_Foo"/>\n'
            '  </CLASSPATH>\n'
            '  <XXX/>\n'
            '</OBJECTPATH>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "OBJECTPATH with invalid content text",
        dict(
            xml_str=''
            '<OBJECTPATH>\n'
            '  xxx\n'
            '  <CLASSPATH>\n'
            '    <NAMESPACEPATH>\n'
            '      <HOST>woot.com</HOST>\n'
            '      <LOCALNAMESPACEPATH>\n'
            '        <NAMESPACE NAME="foo"/>\n'
            '      </LOCALNAMESPACEPATH>\n'
            '    </NAMESPACEPATH>\n'
            '    <CLASSNAME NAME="CIM_Foo"/>\n'
            '  </CLASSPATH>\n'
            '</OBJECTPATH>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "OBJECTPATH with invalid trailing text",
        dict(
            xml_str=''
            '<OBJECTPATH>\n'
            '  <CLASSPATH>\n'
            '    <NAMESPACEPATH>\n'
            '      <HOST>woot.com</HOST>\n'
            '      <LOCALNAMESPACEPATH>\n'
            '        <NAMESPACE NAME="foo"/>\n'
            '      </LOCALNAMESPACEPATH>\n'
            '    </NAMESPACEPATH>\n'
            '    <CLASSNAME NAME="CIM_Foo"/>\n'
            '  </CLASSPATH>\n'
            '  xxx\n'
            '</OBJECTPATH>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "OBJECTPATH with missing child",
        dict(
            xml_str=''
            '<OBJECTPATH/>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "OBJECTPATH with INSTANCEPATH (normal case)",
        dict(
            xml_str=''
            '<OBJECTPATH>\n'
            '  <INSTANCEPATH>\n'
            '    <NAMESPACEPATH>\n'
            '      <HOST>woot.com</HOST>\n'
            '      <LOCALNAMESPACEPATH>\n'
            '        <NAMESPACE NAME="foo"/>\n'
            '      </LOCALNAMESPACEPATH>\n'
            '    </NAMESPACEPATH>\n'
            '    <INSTANCENAME CLASSNAME="CIM_Foo"/>\n'
            '  </INSTANCEPATH>\n'
            '</OBJECTPATH>\n',
            exp_result=CIMInstanceName(
                'CIM_Foo',
                namespace='foo',
                host='woot.com',
            ),
        ),
        None, None, True
    ),
    (
        "OBJECTPATH with CLASSPATH (normal case)",
        dict(
            xml_str=''
            '<OBJECTPATH>\n'
            '  <CLASSPATH>\n'
            '    <NAMESPACEPATH>\n'
            '      <HOST>woot.com</HOST>\n'
            '      <LOCALNAMESPACEPATH>\n'
            '        <NAMESPACE NAME="foo"/>\n'
            '      </LOCALNAMESPACEPATH>\n'
            '    </NAMESPACEPATH>\n'
            '    <CLASSNAME NAME="CIM_Foo"/>\n'
            '  </CLASSPATH>\n'
            '</OBJECTPATH>\n',
            exp_result=CIMClassName(
                'CIM_Foo',
                namespace='foo',
                host='woot.com',
            ),
        ),
        None, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_REQUIRED_OBJECTPATH_ELEMENT)
@simplified_test_function
def test_required_OBJECTPATH_element(
        testcase, xml_str, exp_result):
    """
    Test CIMXMLParser.required_OBJECTPATH_element().
    """

    parser = CIMXMLParser(xml_str)

    # Code to be tested
    result = parser.required_OBJECTPATH_element()

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None, \
        "Expected exception {!r} has not been raised".\
        format(testcase.exp_exc_types)

    assert result == exp_result


TESTCASES_LIST_OF_QUALIFIER_ELEMENTS = [
    (
        "List of QUALIFIER elements that is empty",
        dict(
            skip_events=1,
            xml_str=''
            '<DUMMY_ROOT>\n'
            '</DUMMY_ROOT>\n',
            exp_result=[],
        ),
        None, None, True
    ),
    (
        "List of QUALIFIER elements with one item",
        dict(
            skip_events=1,
            xml_str=''
            '<DUMMY_ROOT>\n'
            '  <QUALIFIER NAME="Qual" TYPE="string"/>\n'
            '</DUMMY_ROOT>\n',
            exp_result=[
                CIMQualifier(
                    'Qual', value=None, type='string',
                    **qualifier_default_attrs()
                ),
            ],
        ),
        None, None, True
    ),
    (
        "List of QUALIFIER elements with two items",
        dict(
            skip_events=1,
            xml_str=''
            '<DUMMY_ROOT>\n'
            '  <QUALIFIER NAME="Qual1" TYPE="string"/>\n'
            '  <QUALIFIER NAME="Qual2" TYPE="string"/>\n'
            '</DUMMY_ROOT>\n',
            exp_result=[
                CIMQualifier(
                    'Qual1', value=None, type='string',
                    **qualifier_default_attrs()
                ),
                CIMQualifier(
                    'Qual2', value=None, type='string',
                    **qualifier_default_attrs()
                ),
            ],
        ),
        None, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_LIST_OF_QUALIFIER_ELEMENTS)
@simplified_test_function
def test_list_of_QUALIFIER_elements(
        testcase, skip_events, xml_str, exp_result):
    """
    Test CIMXMLParser.list_of_QUALIFIER_elements().
    """

    parser = CIMXMLParser(xml_str)
    for _ in range(skip_events):
        parser.get_next_event()

    # Code to be tested
    result = parser.list_of_QUALIFIER_elements()

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None, \
        "Expected exception {!r} has not been raised".\
        format(testcase.exp_exc_types)

    assert result == exp_result


TESTCASES_REQUIRED_QUALIFIER_ELEMENT = [
    (
        "No QUALIFIER but different element",
        dict(
            xml_str='<QUALIFIER.XXX/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "QUALIFIER with invalid child element",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="string">\n'
            '  <XXX/>\n'
            '</QUALIFIER>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "QUALIFIER with invalid content text",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="string">\n'
            '  xxx\n'
            '  <VALUE>bla</VALUE>\n'
            '</QUALIFIER>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "QUALIFIER with invalid trailing text",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="string">\n'
            '  <VALUE>bla</VALUE>\n'
            '  xxx\n'
            '</QUALIFIER>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "QUALIFIER with missing required attribute NAME",
        dict(
            xml_str=''
            '<QUALIFIER TYPE="string"/>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "QUALIFIER with NAME using ASCII characters",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="string"/>\n',
            exp_result=CIMQualifier(
                'Qual', value=None, type='string',
                **qualifier_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER with NAME using non-ASCII UCS-2 characters",
        dict(
            xml_str=b''
            b'<QUALIFIER NAME="Qual\xC3\xA9" TYPE="string"/>\n',
            exp_result=CIMQualifier(
                u'Qual\u00E9', value=None, type='string',
                **qualifier_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER with NAME using non-UCS-2 characters",
        dict(
            xml_str=b''
            b'<QUALIFIER NAME="Qual\xF0\x90\x85\x82" TYPE="string"/>\n',
            exp_result=CIMQualifier(
                u'Qual\U00010142', value=None, type='string',
                **qualifier_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER with xml:lang attribute",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="string" xml:lang="en_us"/>\n',
            exp_result=CIMQualifier(
                'Qual', value=None, type='string',
                **qualifier_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER with OVERRIDABLE attribute (true)",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="string" OVERRIDABLE="true"/>\n',
            exp_result=CIMQualifier(
                'Qual', value=None, type='string',
                **(qualifier_default_attrs(overridable=True))
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER with OVERRIDABLE attribute (TrUe)",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="string" OVERRIDABLE="TrUe"/>\n',
            exp_result=CIMQualifier(
                'Qual', value=None, type='string',
                **(qualifier_default_attrs(overridable=True))
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER with OVERRIDABLE attribute (false)",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="string" OVERRIDABLE="false"/>\n',
            exp_result=CIMQualifier(
                'Qual', value=None, type='string',
                **(qualifier_default_attrs(overridable=False))
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER with OVERRIDABLE attribute (FaLsE)",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="string" OVERRIDABLE="FaLsE"/>\n',
            exp_result=CIMQualifier(
                'Qual', value=None, type='string',
                **(qualifier_default_attrs(overridable=False))
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER with TOSUBCLASS attribute (true)",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="string" TOSUBCLASS="true"/>\n',
            exp_result=CIMQualifier(
                'Qual', value=None, type='string',
                **(qualifier_default_attrs(tosubclass=True))
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER with TOSUBCLASS attribute (TrUe)",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="string" TOSUBCLASS="TrUe"/>\n',
            exp_result=CIMQualifier(
                'Qual', value=None, type='string',
                **(qualifier_default_attrs(tosubclass=True))
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER with TOSUBCLASS attribute (false)",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="string" TOSUBCLASS="false"/>\n',
            exp_result=CIMQualifier(
                'Qual', value=None, type='string',
                **(qualifier_default_attrs(tosubclass=False))
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER with TOSUBCLASS attribute (FaLsE)",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="string" TOSUBCLASS="FaLsE"/>\n',
            exp_result=CIMQualifier(
                'Qual', value=None, type='string',
                **(qualifier_default_attrs(tosubclass=False))
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER with TOINSTANCE attribute (true)",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="string" TOINSTANCE="true"/>\n',
            exp_result=CIMQualifier(
                'Qual', value=None, type='string',
                **(qualifier_default_attrs(toinstance=True))
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER with TOINSTANCE attribute (TrUe)",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="string" TOINSTANCE="TrUe"/>\n',
            exp_result=CIMQualifier(
                'Qual', value=None, type='string',
                **(qualifier_default_attrs(toinstance=True))
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER with TOINSTANCE attribute (false)",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="string" TOINSTANCE="false"/>\n',
            exp_result=CIMQualifier(
                'Qual', value=None, type='string',
                **(qualifier_default_attrs(toinstance=False))
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER with TOINSTANCE attribute (FaLsE)",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="string" TOINSTANCE="FaLsE"/>\n',
            exp_result=CIMQualifier(
                'Qual', value=None, type='string',
                **(qualifier_default_attrs(toinstance=False))
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER with TRANSLATABLE attribute (true)",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="string" TRANSLATABLE="true"/>\n',
            exp_result=CIMQualifier(
                'Qual', value=None, type='string',
                **(qualifier_default_attrs(translatable=True))
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER with TRANSLATABLE attribute (TrUe)",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="string" TRANSLATABLE="TrUe"/>\n',
            exp_result=CIMQualifier(
                'Qual', value=None, type='string',
                **(qualifier_default_attrs(translatable=True))
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER with TRANSLATABLE attribute (false)",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="string" TRANSLATABLE="false"/>\n',
            exp_result=CIMQualifier(
                'Qual', value=None, type='string',
                **(qualifier_default_attrs(translatable=False))
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER with TRANSLATABLE attribute (FaLsE)",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="string" TRANSLATABLE="FaLsE"/>\n',
            exp_result=CIMQualifier(
                'Qual', value=None, type='string',
                **(qualifier_default_attrs(translatable=False))
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER with PROPAGATED attribute (true)",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="string" PROPAGATED="true"/>\n',
            exp_result=CIMQualifier(
                'Qual', value=None, type='string',
                **(qualifier_default_attrs(propagated=True))
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER with PROPAGATED attribute (TrUe)",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="string" PROPAGATED="TrUe"/>\n',
            exp_result=CIMQualifier(
                'Qual', value=None, type='string',
                **(qualifier_default_attrs(propagated=True))
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER with PROPAGATED attribute (false)",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="string" PROPAGATED="false"/>\n',
            exp_result=CIMQualifier(
                'Qual', value=None, type='string',
                **(qualifier_default_attrs(propagated=False))
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER with PROPAGATED attribute (FaLsE)",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="string" PROPAGATED="FaLsE"/>\n',
            exp_result=CIMQualifier(
                'Qual', value=None, type='string',
                **(qualifier_default_attrs(propagated=False))
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER with missing required attribute TYPE",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual"/>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "QUALIFIER with boolean typed value None",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="boolean"/>\n',
            exp_result=CIMQualifier(
                'Qual', value=None, type='boolean',
                **qualifier_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER with boolean typed simple value",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="boolean">\n'
            '  <VALUE>true</VALUE>\n'
            '</QUALIFIER>\n',
            exp_result=CIMQualifier(
                'Qual', value=True, type='boolean',
                **qualifier_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER with boolean typed array value (empty)",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="boolean">\n'
            '  <VALUE.ARRAY/>\n'
            '</QUALIFIER>\n',
            exp_result=CIMQualifier(
                'Qual', value=[], type='boolean',
                **qualifier_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER with string typed value None",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="string"/>\n',
            exp_result=CIMQualifier(
                'Qual', value=None, type='string',
                **qualifier_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER with string typed simple value",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="string">\n'
            '  <VALUE>abc</VALUE>\n'
            '</QUALIFIER>\n',
            exp_result=CIMQualifier(
                'Qual', value='abc', type='string',
                **qualifier_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER with string typed array value (empty)",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="string">\n'
            '  <VALUE.ARRAY/>\n'
            '</QUALIFIER>\n',
            exp_result=CIMQualifier(
                'Qual', value=[], type='string',
                **qualifier_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER with char16 typed value None",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="char16"/>\n',
            exp_result=CIMQualifier(
                'Qual', value=None, type='char16',
                **qualifier_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER with char16 typed simple value",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="char16">\n'
            '  <VALUE>a</VALUE>\n'
            '</QUALIFIER>\n',
            exp_result=CIMQualifier(
                'Qual', value='a', type='char16',
                **qualifier_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER with char16 typed array value (empty)",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="char16">\n'
            '  <VALUE.ARRAY/>\n'
            '</QUALIFIER>\n',
            exp_result=CIMQualifier(
                'Qual', value=[], type='char16',
                **qualifier_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER with uint8 typed value None",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="uint8"/>\n',
            exp_result=CIMQualifier(
                'Qual', value=None, type='uint8',
                **qualifier_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER with uint8 typed simple value",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="uint8">\n'
            '  <VALUE>42</VALUE>\n'
            '</QUALIFIER>\n',
            exp_result=CIMQualifier(
                'Qual', value=42, type='uint8',
                **qualifier_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER with uint8 typed array value (empty)",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="uint8">\n'
            '  <VALUE.ARRAY/>\n'
            '</QUALIFIER>\n',
            exp_result=CIMQualifier(
                'Qual', value=[], type='uint8',
                **qualifier_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER with uint16 typed value None",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="uint16"/>\n',
            exp_result=CIMQualifier(
                'Qual', value=None, type='uint16',
                **qualifier_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER with uint16 typed simple value",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="uint16">\n'
            '  <VALUE>42</VALUE>\n'
            '</QUALIFIER>\n',
            exp_result=CIMQualifier(
                'Qual', value=42, type='uint16',
                **qualifier_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER with uint16 typed array value (empty)",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="uint16">\n'
            '  <VALUE.ARRAY/>\n'
            '</QUALIFIER>\n',
            exp_result=CIMQualifier(
                'Qual', value=[], type='uint16',
                **qualifier_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER with uint32 typed value None",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="uint32"/>\n',
            exp_result=CIMQualifier(
                'Qual', value=None, type='uint32',
                **qualifier_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER with uint32 typed simple value",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="uint32">\n'
            '  <VALUE>42</VALUE>\n'
            '</QUALIFIER>\n',
            exp_result=CIMQualifier(
                'Qual', value=42, type='uint32',
                **qualifier_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER with uint32 typed array value (empty)",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="uint32">\n'
            '  <VALUE.ARRAY/>\n'
            '</QUALIFIER>\n',
            exp_result=CIMQualifier(
                'Qual', value=[], type='uint32',
                **qualifier_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER with uint64 typed value None",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="uint64"/>\n',
            exp_result=CIMQualifier(
                'Qual', value=None, type='uint64',
                **qualifier_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER with uint64 typed simple value",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="uint64">\n'
            '  <VALUE>42</VALUE>\n'
            '</QUALIFIER>\n',
            exp_result=CIMQualifier(
                'Qual', value=42, type='uint64',
                **qualifier_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER with uint64 typed array value (empty)",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="uint64">\n'
            '  <VALUE.ARRAY/>\n'
            '</QUALIFIER>\n',
            exp_result=CIMQualifier(
                'Qual', value=[], type='uint64',
                **qualifier_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER with sint8 typed value None",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="sint8"/>\n',
            exp_result=CIMQualifier(
                'Qual', value=None, type='sint8',
                **qualifier_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER with sint8 typed simple value",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="sint8">\n'
            '  <VALUE>42</VALUE>\n'
            '</QUALIFIER>\n',
            exp_result=CIMQualifier(
                'Qual', value=42, type='sint8',
                **qualifier_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER with sint8 typed array value (empty)",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="sint8">\n'
            '  <VALUE.ARRAY/>\n'
            '</QUALIFIER>\n',
            exp_result=CIMQualifier(
                'Qual', value=[], type='sint8',
                **qualifier_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER with sint16 typed value None",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="sint16"/>\n',
            exp_result=CIMQualifier(
                'Qual', value=None, type='sint16',
                **qualifier_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER with sint16 typed simple value",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="sint16">\n'
            '  <VALUE>42</VALUE>\n'
            '</QUALIFIER>\n',
            exp_result=CIMQualifier(
                'Qual', value=42, type='sint16',
                **qualifier_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER with sint16 typed array value (empty)",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="sint16">\n'
            '  <VALUE.ARRAY/>\n'
            '</QUALIFIER>\n',
            exp_result=CIMQualifier(
                'Qual', value=[], type='sint16',
                **qualifier_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER with sint32 typed value None",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="sint32"/>\n',
            exp_result=CIMQualifier(
                'Qual', value=None, type='sint32',
                **qualifier_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER with sint32 typed simple value",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="sint32">\n'
            '  <VALUE>42</VALUE>\n'
            '</QUALIFIER>\n',
            exp_result=CIMQualifier(
                'Qual', value=42, type='sint32',
                **qualifier_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER with sint32 typed array value (empty)",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="sint32">\n'
            '  <VALUE.ARRAY/>\n'
            '</QUALIFIER>\n',
            exp_result=CIMQualifier(
                'Qual', value=[], type='sint32',
                **qualifier_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER with sint64 typed value None",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="sint64"/>\n',
            exp_result=CIMQualifier(
                'Qual', value=None, type='sint64',
                **qualifier_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER with sint64 typed simple value",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="sint64">\n'
            '  <VALUE>42</VALUE>\n'
            '</QUALIFIER>\n',
            exp_result=CIMQualifier(
                'Qual', value=42, type='sint64',
                **qualifier_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER with sint64 typed array value (empty)",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="sint64">\n'
            '  <VALUE.ARRAY/>\n'
            '</QUALIFIER>\n',
            exp_result=CIMQualifier(
                'Qual', value=[], type='sint64',
                **qualifier_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER with real32 typed value None",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="real32"/>\n',
            exp_result=CIMQualifier(
                'Qual', value=None, type='real32',
                **qualifier_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER with real32 typed simple value",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="real32">\n'
            '  <VALUE>42</VALUE>\n'
            '</QUALIFIER>\n',
            exp_result=CIMQualifier(
                'Qual', value=42.0, type='real32',
                **qualifier_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER with real32 typed array value (empty)",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="real32">\n'
            '  <VALUE.ARRAY/>\n'
            '</QUALIFIER>\n',
            exp_result=CIMQualifier(
                'Qual', value=[], type='real32',
                **qualifier_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER with real64 typed value None",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="real64"/>\n',
            exp_result=CIMQualifier(
                'Qual', value=None, type='real64',
                **qualifier_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER with real64 typed simple value",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="real64">\n'
            '  <VALUE>42</VALUE>\n'
            '</QUALIFIER>\n',
            exp_result=CIMQualifier(
                'Qual', value=42.0, type='real64',
                **qualifier_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER with real64 typed array value (empty)",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="real64">\n'
            '  <VALUE.ARRAY/>\n'
            '</QUALIFIER>\n',
            exp_result=CIMQualifier(
                'Qual', value=[], type='real64',
                **qualifier_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER with datetime typed value None",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="datetime"/>\n',
            exp_result=CIMQualifier(
                'Qual', value=None, type='datetime',
                **qualifier_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER with datetime typed simple value",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="datetime">\n'
            '  <VALUE>20140924193040.654321+120</VALUE>\n'
            '</QUALIFIER>\n',
            exp_result=CIMQualifier(
                'Qual', value='20140924193040.654321+120', type='datetime',
                **qualifier_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER with datetime typed array value (empty)",
        dict(
            xml_str=''
            '<QUALIFIER NAME="Qual" TYPE="datetime">\n'
            '  <VALUE.ARRAY/>\n'
            '</QUALIFIER>\n',
            exp_result=CIMQualifier(
                'Qual', value=[], type='datetime',
                **qualifier_default_attrs()
            ),
        ),
        None, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_REQUIRED_QUALIFIER_ELEMENT)
@simplified_test_function
def test_required_QUALIFIER_element(
        testcase, xml_str, exp_result):
    """
    Test CIMXMLParser.required_QUALIFIER_element().
    """

    parser = CIMXMLParser(xml_str)

    # Code to be tested
    result = parser.required_QUALIFIER_element()

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None, \
        "Expected exception {!r} has not been raised".\
        format(testcase.exp_exc_types)

    assert result == exp_result


TESTCASES_LIST_OF_QUALIFIER_DECLARATION_ELEMENTS = [
    (
        "List of QUALIFIER.DECLARATION elements that is empty",
        dict(
            skip_events=1,
            xml_str=''
            '<DUMMY_ROOT>\n'
            '</DUMMY_ROOT>\n',
            exp_result=[],
        ),
        None, None, True
    ),
    (
        "List of QUALIFIER.DECLARATION elements with one item",
        dict(
            skip_events=1,
            xml_str=''
            '<DUMMY_ROOT>\n'
            '  <QUALIFIER.DECLARATION NAME="Qual" TYPE="string"/>\n'
            '</DUMMY_ROOT>\n',
            exp_result=[
                CIMQualifierDeclaration(
                    'Qual', value=None, type='string',
                    **qualifier_declaration_default_attrs()
                ),
            ],
        ),
        None, None, True
    ),
    (
        "List of QUALIFIER.DECLARATION elements with two items",
        dict(
            skip_events=1,
            xml_str=''
            '<DUMMY_ROOT>\n'
            '  <QUALIFIER.DECLARATION NAME="Qual1" TYPE="string"/>\n'
            '  <QUALIFIER.DECLARATION NAME="Qual2" TYPE="string"/>\n'
            '</DUMMY_ROOT>\n',
            exp_result=[
                CIMQualifierDeclaration(
                    'Qual1', value=None, type='string',
                    **qualifier_declaration_default_attrs()
                ),
                CIMQualifierDeclaration(
                    'Qual2', value=None, type='string',
                    **qualifier_declaration_default_attrs()
                ),
            ],
        ),
        None, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_LIST_OF_QUALIFIER_DECLARATION_ELEMENTS)
@simplified_test_function
def test_list_of_QUALIFIER_DECLARATION_elements(
        testcase, skip_events, xml_str, exp_result):
    """
    Test CIMXMLParser.list_of_QUALIFIER_DECLARATION_elements().
    """

    parser = CIMXMLParser(xml_str)
    for _ in range(skip_events):
        parser.get_next_event()

    # Code to be tested
    result = parser.list_of_QUALIFIER_DECLARATION_elements()

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None, \
        "Expected exception {!r} has not been raised".\
        format(testcase.exp_exc_types)

    assert result == exp_result


TESTCASES_REQUIRED_QUALIFIER_DECLARATION_ELEMENT = [
    (
        "No QUALIFIER.DECLARATION but different element",
        dict(
            xml_str='<QUALIFIER.DECLARATION.XXX/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "QUALIFIER.DECLARATION with invalid child element",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="string">\n'
            '  <XXX/>\n'
            '</QUALIFIER.DECLARATION>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "QUALIFIER.DECLARATION with invalid content text",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="string">\n'
            '  xxx\n'
            '  <SCOPE CLASS="TRUE"/>\n'
            '</QUALIFIER.DECLARATION>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "QUALIFIER.DECLARATION with invalid trailing text",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="string">\n'
            '  <SCOPE CLASS="TRUE"/>\n'
            '  xxx\n'
            '</QUALIFIER.DECLARATION>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "QUALIFIER.DECLARATION with invalid ISARRAY attribute",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="string"'
            ' ISARRAY="xxx"/>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "QUALIFIER.DECLARATION with invalid OVERRIDABLE attribute",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="string"'
            ' OVERRIDABLE="xxx"/>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "QUALIFIER.DECLARATION with invalid TOSUBCLASS attribute",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="string"'
            ' TOSUBCLASS="xxx"/>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "QUALIFIER.DECLARATION with invalid TOINSTANCE attribute",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="string"'
            ' TOINSTANCE="xxx"/>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "QUALIFIER.DECLARATION with invalid TRANSLATABLE attribute",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="string"'
            ' TRANSLATABLE="xxx"/>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "QUALIFIER.DECLARATION with missing required attribute NAME",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION TYPE="string"/>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "QUALIFIER.DECLARATION with NAME using ASCII characters",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="string"/>\n',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=None, type='string',
                **qualifier_declaration_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with NAME using non-ASCII UCS-2 characters",
        dict(
            xml_str=b''
            b'<QUALIFIER.DECLARATION NAME="Qual\xC3\xA9" TYPE="string"/>\n',
            exp_result=CIMQualifierDeclaration(
                u'Qual\u00E9', value=None, type='string',
                **qualifier_declaration_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with NAME using non-UCS-2 characters",
        dict(
            xml_str=b''
            b'<QUALIFIER.DECLARATION NAME="Qual\xF0\x90\x85\x82"'
            b' TYPE="string"/>\n',
            exp_result=CIMQualifierDeclaration(
                u'Qual\U00010142', value=None, type='string',
                **qualifier_declaration_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION fixed array",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="string" ARRAYSIZE="10"'
            ' ISARRAY="true"/>\n',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=None, type='string',
                is_array=True, array_size=10,
                **qualifier_declaration_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION array value with ISARRAY=True",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="string"'
            ' ISARRAY="True"/>\n',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=None, type='string', is_array=True,
                **qualifier_declaration_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION simple value with explicit ISARRAY=False",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="string"'
            ' ISARRAY="False"/>\n',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=None, type='string', is_array=False,
                **qualifier_declaration_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION simple value without ISARRAY (default False)",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="string"/>\n',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=None, type='string', is_array=False,
                **qualifier_declaration_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with OVERRIDABLE attribute (true)",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="string"'
            ' OVERRIDABLE="true"/>\n',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=None, type='string',
                **qualifier_declaration_default_attrs(overridable=True)
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with OVERRIDABLE attribute (TrUe)",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="string"'
            ' OVERRIDABLE="TrUe"/>\n',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=None, type='string',
                **qualifier_declaration_default_attrs(overridable=True)
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with OVERRIDABLE attribute (false)",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="string"'
            ' OVERRIDABLE="false"/>\n',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=None, type='string',
                **qualifier_declaration_default_attrs(overridable=False)
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with OVERRIDABLE attribute (FaLsE)",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="string"'
            ' OVERRIDABLE="FaLsE"/>\n',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=None, type='string',
                **qualifier_declaration_default_attrs(overridable=False)
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with TOSUBCLASS attribute (true)",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="string"'
            ' TOSUBCLASS="true"/>\n',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=None, type='string',
                **qualifier_declaration_default_attrs(tosubclass=True)
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with TOSUBCLASS attribute (TrUe)",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="string"'
            ' TOSUBCLASS="TrUe"/>\n',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=None, type='string',
                **qualifier_declaration_default_attrs(tosubclass=True)
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with TOSUBCLASS attribute (false)",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="string"'
            ' TOSUBCLASS="false"/>\n',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=None, type='string',
                **qualifier_declaration_default_attrs(tosubclass=False)
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with TOSUBCLASS attribute (FaLsE)",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="string"'
            ' TOSUBCLASS="FaLsE"/>\n',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=None, type='string',
                **qualifier_declaration_default_attrs(tosubclass=False)
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with TOINSTANCE attribute (true)",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="string"'
            ' TOINSTANCE="true"/>\n',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=None, type='string',
                **qualifier_declaration_default_attrs(toinstance=True)
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with TOINSTANCE attribute (TrUe)",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="string"'
            ' TOINSTANCE="TrUe"/>\n',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=None, type='string',
                **qualifier_declaration_default_attrs(toinstance=True)
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with TOINSTANCE attribute (false)",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="string"'
            ' TOINSTANCE="false"/>\n',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=None, type='string',
                **qualifier_declaration_default_attrs(toinstance=False)
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with TOINSTANCE attribute (FaLsE)",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="string"'
            ' TOINSTANCE="FaLsE"/>\n',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=None, type='string',
                **qualifier_declaration_default_attrs(toinstance=False)
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with TRANSLATABLE attribute (true)",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="string"'
            ' TRANSLATABLE="true"/>\n',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=None, type='string',
                **qualifier_declaration_default_attrs(translatable=True)
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with TRANSLATABLE attribute (TrUe)",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="string"'
            ' TRANSLATABLE="TrUe"/>\n',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=None, type='string',
                **qualifier_declaration_default_attrs(translatable=True)
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with TRANSLATABLE attribute (false)",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="string"'
            ' TRANSLATABLE="false"/>\n',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=None, type='string',
                **qualifier_declaration_default_attrs(translatable=False)
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with TRANSLATABLE attribute (FaLsE)",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="string"'
            ' TRANSLATABLE="FaLsE"/>\n',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=None, type='string',
                **qualifier_declaration_default_attrs(translatable=False)
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with missing required attribute TYPE",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual"/>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "QUALIFIER.DECLARATION with boolean typed simple default value None",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="boolean"/>\n',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=None, type='boolean',
                **qualifier_declaration_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with boolean typed simple default value",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="boolean">\n'
            '  <VALUE>true</VALUE>\n'
            '</QUALIFIER.DECLARATION>\n',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=True, type='boolean',
                **qualifier_declaration_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with boolean typed array default value None",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="boolean"'
            ' ISARRAY="true">\n'
            '</QUALIFIER.DECLARATION>\n',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=None, type='boolean', is_array=True,
                **qualifier_declaration_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with boolean typed array default value (empty)",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="boolean"'
            ' ISARRAY="true">\n'
            '  <VALUE.ARRAY/>\n'
            '</QUALIFIER.DECLARATION>\n',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=[], type='boolean', is_array=True,
                **qualifier_declaration_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with string typed simple default value None",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="string"/>\n',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=None, type='string',
                **qualifier_declaration_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with string typed simple default value",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="string">\n'
            '  <VALUE>abc</VALUE>\n'
            '</QUALIFIER.DECLARATION>\n',
            exp_result=CIMQualifierDeclaration(
                'Qual', value='abc', type='string',
                **qualifier_declaration_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with string typed array default value (empty)",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="string" ISARRAY="true">\n'
            '  <VALUE.ARRAY/>\n'
            '</QUALIFIER.DECLARATION>\n',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=[], type='string', is_array=True,
                **qualifier_declaration_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with string typed array default value None",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="string"'
            ' ISARRAY="true"/>\n',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=None, type='string', is_array=True,
                **qualifier_declaration_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with char16 typed simple default value None",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="char16"/>\n',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=None, type='char16',
                **qualifier_declaration_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with char16 typed simple default value",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="char16">\n'
            '  <VALUE>a</VALUE>\n'
            '</QUALIFIER.DECLARATION>\n',
            exp_result=CIMQualifierDeclaration(
                'Qual', value='a', type='char16',
                **qualifier_declaration_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with char16 typed array default value None",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="char16"'
            ' ISARRAY="true"/>\n',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=None, type='char16', is_array=True,
                **qualifier_declaration_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with char16 typed array default value (empty)",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="char16" ISARRAY="true">\n'
            '  <VALUE.ARRAY/>\n'
            '</QUALIFIER.DECLARATION>\n',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=[], type='char16', is_array=True,
                **qualifier_declaration_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with uint8 typed simple default value None",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="uint8"/>\n',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=None, type='uint8',
                **qualifier_declaration_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with uint8 typed simple default value",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="uint8">\n'
            '  <VALUE>42</VALUE>\n'
            '</QUALIFIER.DECLARATION>\n',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=42, type='uint8',
                **qualifier_declaration_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with uint8 typed array default value None",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="uint8"'
            ' ISARRAY="true"/>\n',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=None, type='uint8', is_array=True,
                **qualifier_declaration_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with uint8 typed array default value (empty)",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="uint8" ISARRAY="true">\n'
            '  <VALUE.ARRAY/>\n'
            '</QUALIFIER.DECLARATION>\n',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=[], type='uint8', is_array=True,
                **qualifier_declaration_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with uint16 typed simple default value None",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="uint16"/>\n',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=None, type='uint16',
                **qualifier_declaration_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with uint16 typed simple default value",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="uint16">\n'
            '  <VALUE>42</VALUE>\n'
            '</QUALIFIER.DECLARATION>\n',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=42, type='uint16',
                **qualifier_declaration_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with uint16 typed array default value None",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="uint16"'
            ' ISARRAY="true"/>\n',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=None, type='uint16', is_array=True,
                **qualifier_declaration_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with uint16 typed array default value (empty)",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="uint16" ISARRAY="true">\n'
            '  <VALUE.ARRAY/>\n'
            '</QUALIFIER.DECLARATION>\n',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=[], type='uint16', is_array=True,
                **qualifier_declaration_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with uint32 typed simple default value None",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="uint32"/>\n',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=None, type='uint32',
                **qualifier_declaration_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with uint32 typed simple default value",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="uint32">\n'
            '  <VALUE>42</VALUE>\n'
            '</QUALIFIER.DECLARATION>\n',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=42, type='uint32',
                **qualifier_declaration_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with uint32 typed array default value None",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="uint32"'
            ' ISARRAY="true"/>\n',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=None, type='uint32', is_array=True,
                **qualifier_declaration_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with uint32 typed array default value (empty)",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="uint32" ISARRAY="true">\n'
            '  <VALUE.ARRAY/>\n'
            '</QUALIFIER.DECLARATION>\n',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=[], type='uint32', is_array=True,
                **qualifier_declaration_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with uint64 typed simple default value None",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="uint64"/>\n',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=None, type='uint64',
                **qualifier_declaration_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with uint64 typed simple default alue",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="uint64">\n'
            '  <VALUE>42</VALUE>\n'
            '</QUALIFIER.DECLARATION>\n',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=42, type='uint64',
                **qualifier_declaration_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with uint64 typed array default value None",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="uint64"'
            ' ISARRAY="true"/>\n',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=None, type='uint64', is_array=True,
                **qualifier_declaration_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with uint64 typed array default value (empty)",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="uint64" ISARRAY="true">\n'
            '  <VALUE.ARRAY/>\n'
            '</QUALIFIER.DECLARATION>\n',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=[], type='uint64', is_array=True,
                **qualifier_declaration_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with sint8 typed simple default value None",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="sint8"/>\n',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=None, type='sint8',
                **qualifier_declaration_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with sint8 typed simple default value",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="sint8">\n'
            '  <VALUE>42</VALUE>\n'
            '</QUALIFIER.DECLARATION>\n',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=42, type='sint8',
                **qualifier_declaration_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with sint8 typed array default value None",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="sint8"'
            ' ISARRAY="true"/>\n',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=None, type='sint8', is_array=True,
                **qualifier_declaration_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with sint8 typed array default value (empty)",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="sint8" ISARRAY="true">\n'
            '  <VALUE.ARRAY/>\n'
            '</QUALIFIER.DECLARATION>\n',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=[], type='sint8', is_array=True,
                **qualifier_declaration_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with sint16 typed simple default value None",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="sint16"/>\n',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=None, type='sint16',
                **qualifier_declaration_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with sint16 typed simple default value",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="sint16">\n'
            '  <VALUE>42</VALUE>\n'
            '</QUALIFIER.DECLARATION>\n',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=42, type='sint16',
                **qualifier_declaration_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with sint16 typed array default value None",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="sint16"'
            ' ISARRAY="true"/>\n',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=None, type='sint16', is_array=True,
                **qualifier_declaration_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with sint16 typed array default value (empty)",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="sint16" ISARRAY="true">\n'
            '  <VALUE.ARRAY/>\n'
            '</QUALIFIER.DECLARATION>\n',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=[], type='sint16', is_array=True,
                **qualifier_declaration_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with sint32 typed simple default value None",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="sint32"/>\n',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=None, type='sint32',
                **qualifier_declaration_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with sint32 typed simple default value",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="sint32">\n'
            '  <VALUE>42</VALUE>\n'
            '</QUALIFIER.DECLARATION>\n',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=42, type='sint32',
                **qualifier_declaration_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with sint32 typed array default value None",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="sint32"'
            ' ISARRAY="true"/>\n',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=None, type='sint32', is_array=True,
                **qualifier_declaration_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with sint32 typed array default value (empty)",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="sint32" ISARRAY="true">\n'
            '  <VALUE.ARRAY/>\n'
            '</QUALIFIER.DECLARATION>\n',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=[], type='sint32', is_array=True,
                **qualifier_declaration_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with sint64 typed simple default value None",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="sint64"/>\n',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=None, type='sint64',
                **qualifier_declaration_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with sint64 typed simple default value",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="sint64">\n'
            '  <VALUE>42</VALUE>\n'
            '</QUALIFIER.DECLARATION>\n',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=42, type='sint64',
                **qualifier_declaration_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with sint64 typed array default value None",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="sint64"'
            ' ISARRAY="true"/>\n',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=None, type='sint64', is_array=True,
                **qualifier_declaration_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with sint64 typed array default value (empty)",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="sint64" ISARRAY="true">\n'
            '  <VALUE.ARRAY/>\n'
            '</QUALIFIER.DECLARATION>\n',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=[], type='sint64', is_array=True,
                **qualifier_declaration_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with real32 typed simple default value None",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="real32"/>\n',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=None, type='real32',
                **qualifier_declaration_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with real32 typed simple default value",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="real32">\n'
            '  <VALUE>42</VALUE>\n'
            '</QUALIFIER.DECLARATION>\n',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=42.0, type='real32',
                **qualifier_declaration_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with real32 typed array default value None",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="real32"'
            ' ISARRAY="true"/>\n',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=None, type='real32', is_array=True,
                **qualifier_declaration_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with real32 typed array default value (empty)",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="real32" ISARRAY="true">\n'
            '  <VALUE.ARRAY/>\n'
            '</QUALIFIER.DECLARATION>\n',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=[], type='real32', is_array=True,
                **qualifier_declaration_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with real64 typed simple default value None",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="real64"/>\n',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=None, type='real64',
                **qualifier_declaration_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with real64 typed simple default value",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="real64">\n'
            '  <VALUE>42</VALUE>\n'
            '</QUALIFIER.DECLARATION>\n',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=42.0, type='real64',
                **qualifier_declaration_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with real64 typed array default value None",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="real64"'
            ' ISARRAY="true"/>\n',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=None, type='real64', is_array=True,
                **qualifier_declaration_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with real64 typed array default value (empty)",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="real64" ISARRAY="true">\n'
            '  <VALUE.ARRAY/>\n'
            '</QUALIFIER.DECLARATION>\n',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=[], type='real64', is_array=True,
                **qualifier_declaration_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with datetime typed simple default value None",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="datetime"/>\n',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=None, type='datetime',
                **qualifier_declaration_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with datetime typed simple default value",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="datetime">\n'
            '  <VALUE>20140924193040.654321+120</VALUE>\n'
            '</QUALIFIER.DECLARATION>\n',
            exp_result=CIMQualifierDeclaration(
                'Qual', value='20140924193040.654321+120', type='datetime',
                **qualifier_declaration_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with datetime typed array default value None",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="datetime"'
            ' ISARRAY="true"/>\n',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=None, type='datetime', is_array=True,
                **qualifier_declaration_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with datetime typed array default value (empty)",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="datetime"'
            ' ISARRAY="true">\n'
            '  <VALUE.ARRAY/>\n'
            '</QUALIFIER.DECLARATION>\n',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=[], type='datetime', is_array=True,
                **qualifier_declaration_default_attrs()
            ),
        ),
        None, None, True
    ),

    # Testcases with SCOPE child elements
    (
        "QUALIFIER.DECLARATION with children in incorrect order",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="string">\n'
            '  <VALUE/>\n'
            '  <SCOPE CLASS="TRUE"/>\n'
            '</QUALIFIER.DECLARATION>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "QUALIFIER.DECLARATION with SCOPE CLASS and VALUE",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="string">\n'
            '  <SCOPE CLASS="TRUE"/>\n'
            '  <VALUE/>\n'
            '</QUALIFIER.DECLARATION>\n',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=u'', type='string',
                scopes={
                    u'CLASS': True,
                },
                **qualifier_declaration_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with SCOPE CLASS and no VALUE (None)",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="string">\n'
            '  <SCOPE CLASS="TRUE"/>\n'
            '</QUALIFIER.DECLARATION>\n',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=None, type='string',
                scopes={
                    u'CLASS': True,
                },
                **qualifier_declaration_default_attrs()
            ),
        ),
        None, None, True
    ),
    (
        "QUALIFIER.DECLARATION with SCOPE with all scopes",
        dict(
            xml_str=''
            '<QUALIFIER.DECLARATION NAME="Qual" TYPE="string">\n'
            '  <SCOPE CLASS="TRUE" ASSOCIATION="TRUE" REFERENCE="TRUE"'
            ' PROPERTY="TRUE" METHOD="TRUE" PARAMETER="TRUE"'
            ' INDICATION="TRUE"/>\n'
            '  <VALUE/>\n'
            '</QUALIFIER.DECLARATION>\n',
            exp_result=CIMQualifierDeclaration(
                'Qual', value=u'', type='string',
                scopes={
                    u'CLASS': True,
                    u'ASSOCIATION': True,
                    u'REFERENCE': True,
                    u'PROPERTY': True,
                    u'METHOD': True,
                    u'PARAMETER': True,
                    u'INDICATION': True,
                },
                **qualifier_declaration_default_attrs()
            ),
        ),
        None, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_REQUIRED_QUALIFIER_DECLARATION_ELEMENT)
@simplified_test_function
def test_required_QUALIFIER_DECLARATION_element(
        testcase, xml_str, exp_result):
    """
    Test CIMXMLParser.required_QUALIFIER_DECLARATION_element().
    """

    parser = CIMXMLParser(xml_str)

    # Code to be tested
    result = parser.required_QUALIFIER_DECLARATION_element()

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None, \
        "Expected exception {!r} has not been raised".\
        format(testcase.exp_exc_types)

    assert result == exp_result


TESTCASES_REQUIRED_SCOPE_ELEMENT = [
    (
        "No SCOPE but different element",
        dict(
            xml_str='<SCOPE.XXX/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "SCOPE with invalid child element",
        dict(
            xml_str=''
            '<SCOPE>\n'
            '  <XXX/>\n'
            '</SCOPE>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "SCOPE with invalid content text",
        dict(
            xml_str=''
            '<SCOPE>\n'
            '  xxx\n'
            '</SCOPE>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "SCOPE with boolean attribute 'true' (lower case)",
        dict(
            xml_str=''
            '<SCOPE CLASS="true"/>\n',
            exp_result={
                u'CLASS': True,
            },
        ),
        None, None, True
    ),
    (
        "SCOPE with boolean attribute 'TrUe' (mixed case)",
        dict(
            xml_str=''
            '<SCOPE CLASS="TrUe"/>\n',
            exp_result={
                u'CLASS': True,
            },
        ),
        None, None, True
    ),
    (
        "SCOPE with boolean attribute 'TRUE' (upper case)",
        dict(
            xml_str=''
            '<SCOPE CLASS="TrUe"/>\n',
            exp_result={
                u'CLASS': True,
            },
        ),
        None, None, True
    ),
    (
        "SCOPE with boolean attribute 'false' (lower case)",
        dict(
            xml_str=''
            '<SCOPE CLASS="false"/>\n',
            exp_result={
                u'CLASS': False,
            },
        ),
        None, None, True
    ),
    (
        "SCOPE with boolean attribute 'FaLsE' (mixed case)",
        dict(
            xml_str=''
            '<SCOPE CLASS="FaLsE"/>\n',
            exp_result={
                u'CLASS': False,
            },
        ),
        None, None, True
    ),
    (
        "SCOPE with boolean attribute 'FALSE' (upper case)",
        dict(
            xml_str=''
            '<SCOPE CLASS="FALSE"/>\n',
            exp_result={
                u'CLASS': False,
            },
        ),
        None, None, True
    ),
    (
        "SCOPE with invalid boolean attribute",
        dict(
            xml_str=''
            '<SCOPE CLASS="XXX"/>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "SCOPE with invalid empty boolean attribute",
        dict(
            xml_str=''
            '<SCOPE CLASS=""/>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "SCOPE with all supported scope attributes with different values",
        dict(
            xml_str=''
            '<SCOPE'
            ' REFERENCE="true"'
            ' CLASS="true"'
            ' ASSOCIATION="false"'
            ' PROPERTY="false"'
            ' PARAMETER="false"'
            ' INDICATION="true"'
            ' METHOD="true"'
            '/>\n',
            exp_result={
                u'CLASS': True,
                u'ASSOCIATION': False,
                u'REFERENCE': True,
                u'PROPERTY': False,
                u'METHOD': True,
                u'PARAMETER': False,
                u'INDICATION': True,
            },
        ),
        None, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_REQUIRED_SCOPE_ELEMENT)
@simplified_test_function
def test_required_SCOPE_element(
        testcase, xml_str, exp_result):
    """
    Test CIMXMLParser.required_SCOPE_element().
    """

    parser = CIMXMLParser(xml_str)

    # Code to be tested
    result = parser.required_SCOPE_element()

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None, \
        "Expected exception {!r} has not been raised".\
        format(testcase.exp_exc_types)

    assert result == exp_result


TESTCASES_LIST_OF_VALUE_INSTANCEWITHPATH_ELEMENTS = [
    (
        "List of VALUE.INSTANCEWITHPATH elements that is empty",
        dict(
            skip_events=1,
            xml_str=''
            '<DUMMY_ROOT>\n'
            '</DUMMY_ROOT>\n',
            exp_result=[],
        ),
        None, None, True
    ),
    (
        "List of VALUE.INSTANCEWITHPATH elements with one item",
        dict(
            skip_events=1,
            xml_str=''
            '<DUMMY_ROOT>\n'
            '  <VALUE.INSTANCEWITHPATH>\n'
            '    <INSTANCEPATH>\n'
            '      <NAMESPACEPATH>\n'
            '        <HOST>woot.com</HOST>\n'
            '        <LOCALNAMESPACEPATH>\n'
            '          <NAMESPACE NAME="foo"/>\n'
            '        </LOCALNAMESPACEPATH>\n'
            '      </NAMESPACEPATH>\n'
            '      <INSTANCENAME CLASSNAME="CIM_Foo"/>\n'
            '    </INSTANCEPATH>\n'
            '    <INSTANCE CLASSNAME="CIM_Foo"/>\n'
            '  </VALUE.INSTANCEWITHPATH>\n'
            '</DUMMY_ROOT>\n',
            exp_result=[
                CIMInstance(
                    'CIM_Foo',
                    path=CIMInstanceName(
                        'CIM_Foo',
                        namespace='foo',
                        host='woot.com',
                    ),
                ),
            ],
        ),
        None, None, True
    ),
    (
        "List of VALUE.INSTANCEWITHPATH elements with two items",
        dict(
            skip_events=1,
            xml_str=''
            '<DUMMY_ROOT>\n'
            '  <VALUE.INSTANCEWITHPATH>\n'
            '    <INSTANCEPATH>\n'
            '      <NAMESPACEPATH>\n'
            '        <HOST>woot.com</HOST>\n'
            '        <LOCALNAMESPACEPATH>\n'
            '          <NAMESPACE NAME="foo"/>\n'
            '        </LOCALNAMESPACEPATH>\n'
            '      </NAMESPACEPATH>\n'
            '      <INSTANCENAME CLASSNAME="CIM_Foo1"/>\n'
            '    </INSTANCEPATH>\n'
            '    <INSTANCE CLASSNAME="CIM_Foo1"/>\n'
            '  </VALUE.INSTANCEWITHPATH>\n'
            '  <VALUE.INSTANCEWITHPATH>\n'
            '    <INSTANCEPATH>\n'
            '      <NAMESPACEPATH>\n'
            '        <HOST>woot.com</HOST>\n'
            '        <LOCALNAMESPACEPATH>\n'
            '          <NAMESPACE NAME="foo"/>\n'
            '        </LOCALNAMESPACEPATH>\n'
            '      </NAMESPACEPATH>\n'
            '      <INSTANCENAME CLASSNAME="CIM_Foo2"/>\n'
            '    </INSTANCEPATH>\n'
            '    <INSTANCE CLASSNAME="CIM_Foo2"/>\n'
            '  </VALUE.INSTANCEWITHPATH>\n'
            '</DUMMY_ROOT>\n',
            exp_result=[
                CIMInstance(
                    'CIM_Foo1',
                    path=CIMInstanceName(
                        'CIM_Foo1',
                        namespace='foo',
                        host='woot.com',
                    ),
                ),
                CIMInstance(
                    'CIM_Foo2',
                    path=CIMInstanceName(
                        'CIM_Foo2',
                        namespace='foo',
                        host='woot.com',
                    ),
                ),
            ],
        ),
        None, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_LIST_OF_VALUE_INSTANCEWITHPATH_ELEMENTS)
@simplified_test_function
def test_list_of_VALUE_INSTANCEWITHPATH_elements(
        testcase, skip_events, xml_str, exp_result):
    """
    Test CIMXMLParser.list_of_VALUE_INSTANCEWITHPATH_elements().
    """

    parser = CIMXMLParser(xml_str)
    for _ in range(skip_events):
        parser.get_next_event()

    # Code to be tested
    result = parser.list_of_VALUE_INSTANCEWITHPATH_elements()

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None, \
        "Expected exception {!r} has not been raised".\
        format(testcase.exp_exc_types)

    assert result == exp_result


TESTCASES_REQUIRED_VALUE_INSTANCEWITHPATH_ELEMENT = [
    (
        "No VALUE.INSTANCEWITHPATH but different element",
        dict(
            xml_str='<VALUE.INSTANCEWITHPATH.XXX/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "VALUE.INSTANCEWITHPATH with invalid child element",
        dict(
            xml_str=''
            '<VALUE.INSTANCEWITHPATH>\n'
            '  <INSTANCEPATH>\n'
            '    <NAMESPACEPATH>\n'
            '      <HOST>woot.com</HOST>\n'
            '      <LOCALNAMESPACEPATH>\n'
            '        <NAMESPACE NAME="foo"/>\n'
            '      </LOCALNAMESPACEPATH>\n'
            '    </NAMESPACEPATH>\n'
            '    <INSTANCENAME CLASSNAME="CIM_Foo"/>\n'
            '  </INSTANCEPATH>\n'
            '  <INSTANCE CLASSNAME="CIM_Foo"/>\n'
            '  <XXX/>\n'
            '</VALUE.INSTANCEWITHPATH>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "VALUE.INSTANCEWITHPATH with invalid content text",
        dict(
            xml_str=''
            '<VALUE.INSTANCEWITHPATH>\n'
            '  xxx\n'
            '  <INSTANCEPATH>\n'
            '    <NAMESPACEPATH>\n'
            '      <HOST>woot.com</HOST>\n'
            '      <LOCALNAMESPACEPATH>\n'
            '        <NAMESPACE NAME="foo"/>\n'
            '      </LOCALNAMESPACEPATH>\n'
            '    </NAMESPACEPATH>\n'
            '    <INSTANCENAME CLASSNAME="CIM_Foo"/>\n'
            '  </INSTANCEPATH>\n'
            '  <INSTANCE CLASSNAME="CIM_Foo"/>\n'
            '</VALUE.INSTANCEWITHPATH>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "VALUE.INSTANCEWITHPATH with invalid trailing text",
        dict(
            xml_str=''
            '<VALUE.INSTANCEWITHPATH>\n'
            '  <INSTANCEPATH>\n'
            '    <NAMESPACEPATH>\n'
            '      <HOST>woot.com</HOST>\n'
            '      <LOCALNAMESPACEPATH>\n'
            '        <NAMESPACE NAME="foo"/>\n'
            '      </LOCALNAMESPACEPATH>\n'
            '    </NAMESPACEPATH>\n'
            '    <INSTANCENAME CLASSNAME="CIM_Foo"/>\n'
            '  </INSTANCEPATH>\n'
            '  <INSTANCE CLASSNAME="CIM_Foo"/>\n'
            '  xxx\n'
            '</VALUE.INSTANCEWITHPATH>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "VALUE.INSTANCEWITHPATH with missing children",
        dict(
            xml_str=''
            '<VALUE.INSTANCEWITHPATH/>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "VALUE.INSTANCEWITHPATH with missing child INSTANCEPATH",
        dict(
            xml_str=''
            '<VALUE.INSTANCEWITHPATH>\n'
            '  <INSTANCE CLASSNAME="CIM_Foo"/>\n'
            '</VALUE.INSTANCEWITHPATH>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "VALUE.INSTANCEWITHPATH with missing child INSTANCE",
        dict(
            xml_str=''
            '<VALUE.INSTANCEWITHPATH>\n'
            '  <INSTANCEPATH>\n'
            '    <NAMESPACEPATH>\n'
            '      <HOST>woot.com</HOST>\n'
            '      <LOCALNAMESPACEPATH>\n'
            '        <NAMESPACE NAME="foo"/>\n'
            '      </LOCALNAMESPACEPATH>\n'
            '    </NAMESPACEPATH>\n'
            '    <INSTANCENAME CLASSNAME="CIM_Foo"/>\n'
            '  </INSTANCEPATH>\n'
            '</VALUE.INSTANCEWITHPATH>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "VALUE.INSTANCEWITHPATH with children in incorrect order",
        dict(
            xml_str=''
            '<VALUE.INSTANCEWITHPATH>\n'
            '  <INSTANCE CLASSNAME="CIM_Foo"/>\n'
            '  <INSTANCEPATH>\n'
            '    <NAMESPACEPATH>\n'
            '      <HOST>woot.com</HOST>\n'
            '      <LOCALNAMESPACEPATH>\n'
            '        <NAMESPACE NAME="foo"/>\n'
            '      </LOCALNAMESPACEPATH>\n'
            '    </NAMESPACEPATH>\n'
            '    <INSTANCENAME CLASSNAME="CIM_Foo"/>\n'
            '  </INSTANCEPATH>\n'
            '</VALUE.INSTANCEWITHPATH>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "VALUE.INSTANCEWITHPATH (normal case)",
        dict(
            xml_str=''
            '<VALUE.INSTANCEWITHPATH>\n'
            '  <INSTANCEPATH>\n'
            '    <NAMESPACEPATH>\n'
            '      <HOST>woot.com</HOST>\n'
            '      <LOCALNAMESPACEPATH>\n'
            '        <NAMESPACE NAME="foo"/>\n'
            '      </LOCALNAMESPACEPATH>\n'
            '    </NAMESPACEPATH>\n'
            '    <INSTANCENAME CLASSNAME="CIM_Foo"/>\n'
            '  </INSTANCEPATH>\n'
            '  <INSTANCE CLASSNAME="CIM_Foo"/>\n'
            '</VALUE.INSTANCEWITHPATH>\n',
            exp_result=CIMInstance(
                'CIM_Foo',
                path=CIMInstanceName(
                    'CIM_Foo',
                    namespace='foo',
                    host='woot.com',
                ),
            ),
        ),
        None, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_REQUIRED_VALUE_INSTANCEWITHPATH_ELEMENT)
@simplified_test_function
def test_required_VALUE_INSTANCEWITHPATH_element(
        testcase, xml_str, exp_result):
    """
    Test CIMXMLParser.required_VALUE_INSTANCEWITHPATH_element().
    """

    parser = CIMXMLParser(xml_str)

    # Code to be tested
    result = parser.required_VALUE_INSTANCEWITHPATH_element()

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None, \
        "Expected exception {!r} has not been raised".\
        format(testcase.exp_exc_types)

    assert result == exp_result


TESTCASES_LIST_OF_VALUE_NAMEDINSTANCE_ELEMENTS = [
    (
        "List of VALUE.NAMEDINSTANCE elements that is empty",
        dict(
            skip_events=1,
            xml_str=''
            '<DUMMY_ROOT>\n'
            '</DUMMY_ROOT>\n',
            exp_result=[],
        ),
        None, None, True
    ),
    (
        "List of VALUE.NAMEDINSTANCE elements with one item",
        dict(
            skip_events=1,
            xml_str=''
            '<DUMMY_ROOT>\n'
            '  <VALUE.NAMEDINSTANCE>\n'
            '    <INSTANCENAME CLASSNAME="CIM_Foo"/>\n'
            '    <INSTANCE CLASSNAME="CIM_Foo"/>\n'
            '  </VALUE.NAMEDINSTANCE>\n'
            '</DUMMY_ROOT>\n',
            exp_result=[
                CIMInstance(
                    'CIM_Foo',
                    path=CIMInstanceName('CIM_Foo'),
                ),
            ],
        ),
        None, None, True
    ),
    (
        "List of VALUE.NAMEDINSTANCE elements with two items",
        dict(
            skip_events=1,
            xml_str=''
            '<DUMMY_ROOT>\n'
            '  <VALUE.NAMEDINSTANCE>\n'
            '    <INSTANCENAME CLASSNAME="CIM_Foo1"/>\n'
            '    <INSTANCE CLASSNAME="CIM_Foo1"/>\n'
            '  </VALUE.NAMEDINSTANCE>\n'
            '  <VALUE.NAMEDINSTANCE>\n'
            '    <INSTANCENAME CLASSNAME="CIM_Foo2"/>\n'
            '    <INSTANCE CLASSNAME="CIM_Foo2"/>\n'
            '  </VALUE.NAMEDINSTANCE>\n'
            '</DUMMY_ROOT>\n',
            exp_result=[
                CIMInstance(
                    'CIM_Foo1',
                    path=CIMInstanceName('CIM_Foo1'),
                ),
                CIMInstance(
                    'CIM_Foo2',
                    path=CIMInstanceName('CIM_Foo2'),
                ),
            ],
        ),
        None, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_LIST_OF_VALUE_NAMEDINSTANCE_ELEMENTS)
@simplified_test_function
def test_list_of_VALUE_NAMEDINSTANCE_elements(
        testcase, skip_events, xml_str, exp_result):
    """
    Test CIMXMLParser.list_of_VALUE_NAMEDINSTANCE_elements().
    """

    parser = CIMXMLParser(xml_str)
    for _ in range(skip_events):
        parser.get_next_event()

    # Code to be tested
    result = parser.list_of_VALUE_NAMEDINSTANCE_elements()

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None, \
        "Expected exception {!r} has not been raised".\
        format(testcase.exp_exc_types)

    assert result == exp_result


TESTCASES_REQUIRED_VALUE_NAMEDINSTANCE_ELEMENT = [
    (
        "No VALUE.NAMEDINSTANCE but different element",
        dict(
            xml_str='<VALUE.NAMEDINSTANCE.XXX/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "VALUE.NAMEDINSTANCE with invalid child element",
        dict(
            xml_str=''
            '<VALUE.NAMEDINSTANCE>\n'
            '  <INSTANCENAME CLASSNAME="CIM_Foo"/>\n'
            '  <INSTANCE CLASSNAME="CIM_Foo"/>\n'
            '  <XXX/>\n'
            '</VALUE.NAMEDINSTANCE>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "VALUE.NAMEDINSTANCE with invalid content text",
        dict(
            xml_str=''
            '<VALUE.NAMEDINSTANCE>\n'
            '  xxx\n'
            '  <INSTANCENAME CLASSNAME="CIM_Foo"/>\n'
            '  <INSTANCE CLASSNAME="CIM_Foo"/>\n'
            '</VALUE.NAMEDINSTANCE>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "VALUE.NAMEDINSTANCE with invalid trailing text",
        dict(
            xml_str=''
            '<VALUE.NAMEDINSTANCE>\n'
            '  <INSTANCENAME CLASSNAME="CIM_Foo"/>\n'
            '  <INSTANCE CLASSNAME="CIM_Foo"/>\n'
            '  xxx\n'
            '</VALUE.NAMEDINSTANCE>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "VALUE.NAMEDINSTANCE with missing children",
        dict(
            xml_str=''
            '<VALUE.NAMEDINSTANCE/>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "VALUE.NAMEDINSTANCE with missing child INSTANCENAME",
        dict(
            xml_str=''
            '<VALUE.NAMEDINSTANCE>\n'
            '  <INSTANCE CLASSNAME="CIM_Foo"/>\n'
            '</VALUE.NAMEDINSTANCE>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "VALUE.NAMEDINSTANCE with missing child INSTANCE",
        dict(
            xml_str=''
            '<VALUE.NAMEDINSTANCE>\n'
            '  <INSTANCENAME CLASSNAME="CIM_Foo"/>\n'
            '</VALUE.NAMEDINSTANCE>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "VALUE.NAMEDINSTANCE with children in incorrect order",
        dict(
            xml_str=''
            '<VALUE.NAMEDINSTANCE>\n'
            '  <INSTANCE CLASSNAME="CIM_Foo"/>\n'
            '  <INSTANCENAME CLASSNAME="CIM_Foo"/>\n'
            '</VALUE.NAMEDINSTANCE>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "VALUE.NAMEDINSTANCE (normal case)",
        dict(
            xml_str=''
            '<VALUE.NAMEDINSTANCE>\n'
            '  <INSTANCENAME CLASSNAME="CIM_Foo"/>\n'
            '  <INSTANCE CLASSNAME="CIM_Foo"/>\n'
            '</VALUE.NAMEDINSTANCE>\n',
            exp_result=CIMInstance(
                'CIM_Foo',
                path=CIMInstanceName('CIM_Foo'),
            ),
        ),
        None, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_REQUIRED_VALUE_NAMEDINSTANCE_ELEMENT)
@simplified_test_function
def test_required_VALUE_NAMEDINSTANCE_element(
        testcase, xml_str, exp_result):
    """
    Test CIMXMLParser.required_VALUE_NAMEDINSTANCE_element().
    """

    parser = CIMXMLParser(xml_str)

    # Code to be tested
    result = parser.required_VALUE_NAMEDINSTANCE_element()

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None, \
        "Expected exception {!r} has not been raised".\
        format(testcase.exp_exc_types)

    assert result == exp_result


TESTCASES_LIST_OF_VALUE_OBJECTWITHPATH_ELEMENTS = [
    (
        "List of VALUE.OBJECTWITHPATH elements that is empty",
        dict(
            skip_events=1,
            xml_str=''
            '<DUMMY_ROOT>\n'
            '</DUMMY_ROOT>\n',
            exp_result=[],
        ),
        None, None, True
    ),
    (
        "List of VALUE.OBJECTWITHPATH elements with one instance item",
        dict(
            skip_events=1,
            xml_str=''
            '<DUMMY_ROOT>\n'
            '  <VALUE.OBJECTWITHPATH>\n'
            '    <INSTANCEPATH>\n'
            '      <NAMESPACEPATH>\n'
            '        <HOST>woot.com</HOST>\n'
            '        <LOCALNAMESPACEPATH>\n'
            '          <NAMESPACE NAME="foo"/>\n'
            '        </LOCALNAMESPACEPATH>\n'
            '      </NAMESPACEPATH>\n'
            '      <INSTANCENAME CLASSNAME="CIM_Foo"/>\n'
            '    </INSTANCEPATH>\n'
            '    <INSTANCE CLASSNAME="CIM_Foo"/>\n'
            '  </VALUE.OBJECTWITHPATH>\n'
            '</DUMMY_ROOT>\n',
            exp_result=[
                CIMInstance(
                    'CIM_Foo',
                    path=CIMInstanceName(
                        'CIM_Foo',
                        namespace='foo',
                        host='woot.com',
                    ),
                ),
            ],
        ),
        None, None, True
    ),
    (
        "List of VALUE.OBJECTWITHPATH elements with two instance items",
        dict(
            skip_events=1,
            xml_str=''
            '<DUMMY_ROOT>\n'
            '  <VALUE.OBJECTWITHPATH>\n'
            '    <INSTANCEPATH>\n'
            '      <NAMESPACEPATH>\n'
            '        <HOST>woot.com</HOST>\n'
            '        <LOCALNAMESPACEPATH>\n'
            '          <NAMESPACE NAME="foo"/>\n'
            '        </LOCALNAMESPACEPATH>\n'
            '      </NAMESPACEPATH>\n'
            '      <INSTANCENAME CLASSNAME="CIM_Foo1"/>\n'
            '    </INSTANCEPATH>\n'
            '    <INSTANCE CLASSNAME="CIM_Foo1"/>\n'
            '  </VALUE.OBJECTWITHPATH>\n'
            '  <VALUE.OBJECTWITHPATH>\n'
            '    <INSTANCEPATH>\n'
            '      <NAMESPACEPATH>\n'
            '        <HOST>woot.com</HOST>\n'
            '        <LOCALNAMESPACEPATH>\n'
            '          <NAMESPACE NAME="foo"/>\n'
            '        </LOCALNAMESPACEPATH>\n'
            '      </NAMESPACEPATH>\n'
            '      <INSTANCENAME CLASSNAME="CIM_Foo2"/>\n'
            '    </INSTANCEPATH>\n'
            '    <INSTANCE CLASSNAME="CIM_Foo2"/>\n'
            '  </VALUE.OBJECTWITHPATH>\n'
            '</DUMMY_ROOT>\n',
            exp_result=[
                CIMInstance(
                    'CIM_Foo1',
                    path=CIMInstanceName(
                        'CIM_Foo1',
                        namespace='foo',
                        host='woot.com',
                    ),
                ),
                CIMInstance(
                    'CIM_Foo2',
                    path=CIMInstanceName(
                        'CIM_Foo2',
                        namespace='foo',
                        host='woot.com',
                    ),
                ),
            ],
        ),
        None, None, True
    ),
    (
        "List of VALUE.OBJECTWITHPATH elements with one class item",
        dict(
            skip_events=1,
            xml_str=''
            '<DUMMY_ROOT>\n'
            '  <VALUE.OBJECTWITHPATH>\n'
            '    <CLASSPATH>\n'
            '      <NAMESPACEPATH>\n'
            '        <HOST>woot.com</HOST>\n'
            '        <LOCALNAMESPACEPATH>\n'
            '          <NAMESPACE NAME="foo"/>\n'
            '        </LOCALNAMESPACEPATH>\n'
            '      </NAMESPACEPATH>\n'
            '      <CLASSNAME NAME="CIM_Foo"/>\n'
            '    </CLASSPATH>\n'
            '    <CLASS NAME="CIM_Foo"/>\n'
            '  </VALUE.OBJECTWITHPATH>\n'
            '</DUMMY_ROOT>\n',
            exp_result=[
                CIMClass(
                    'CIM_Foo',
                    path=CIMClassName(
                        'CIM_Foo',
                        namespace='foo',
                        host='woot.com',
                    ),
                ),
            ],
        ),
        None, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_LIST_OF_VALUE_OBJECTWITHPATH_ELEMENTS)
@simplified_test_function
def test_list_of_VALUE_OBJECTWITHPATH_elements(
        testcase, skip_events, xml_str, exp_result):
    """
    Test CIMXMLParser.list_of_VALUE_OBJECTWITHPATH_elements().
    """

    parser = CIMXMLParser(xml_str)
    for _ in range(skip_events):
        parser.get_next_event()

    # Code to be tested
    result = parser.list_of_VALUE_OBJECTWITHPATH_elements()

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None, \
        "Expected exception {!r} has not been raised".\
        format(testcase.exp_exc_types)

    assert result == exp_result


TESTCASES_REQUIRED_VALUE_OBJECTWITHPATH_ELEMENT = [
    (
        "No VALUE.OBJECTWITHPATH but different element",
        dict(
            xml_str='<VALUE.OBJECTWITHPATH.XXX/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "VALUE.OBJECTWITHPATH with invalid child element",
        dict(
            xml_str=''
            '<VALUE.OBJECTWITHPATH>\n'
            '  <CLASSPATH>\n'
            '    <NAMESPACEPATH>\n'
            '      <HOST>woot.com</HOST>\n'
            '      <LOCALNAMESPACEPATH>\n'
            '        <NAMESPACE NAME="foo"/>\n'
            '      </LOCALNAMESPACEPATH>\n'
            '    </NAMESPACEPATH>\n'
            '    <CLASSNAME NAME="CIM_Foo"/>\n'
            '  </CLASSPATH>\n'
            '  <CLASS NAME="CIM_Foo"/>\n'
            '  <XXX/>\n'
            '</VALUE.OBJECTWITHPATH>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "VALUE.OBJECTWITHPATH with invalid content text",
        dict(
            xml_str=''
            '<VALUE.OBJECTWITHPATH>\n'
            '  xxx\n'
            '  <CLASSPATH>\n'
            '    <NAMESPACEPATH>\n'
            '      <HOST>woot.com</HOST>\n'
            '      <LOCALNAMESPACEPATH>\n'
            '        <NAMESPACE NAME="foo"/>\n'
            '      </LOCALNAMESPACEPATH>\n'
            '    </NAMESPACEPATH>\n'
            '    <CLASSNAME NAME="CIM_Foo"/>\n'
            '  </CLASSPATH>\n'
            '  <CLASS NAME="CIM_Foo"/>\n'
            '</VALUE.OBJECTWITHPATH>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "VALUE.OBJECTWITHPATH with invalid trailing text",
        dict(
            xml_str=''
            '<VALUE.OBJECTWITHPATH>\n'
            '  <CLASSPATH>\n'
            '    <NAMESPACEPATH>\n'
            '      <HOST>woot.com</HOST>\n'
            '      <LOCALNAMESPACEPATH>\n'
            '        <NAMESPACE NAME="foo"/>\n'
            '      </LOCALNAMESPACEPATH>\n'
            '    </NAMESPACEPATH>\n'
            '    <CLASSNAME NAME="CIM_Foo"/>\n'
            '  </CLASSPATH>\n'
            '  <CLASS NAME="CIM_Foo"/>\n'
            '  xxx\n'
            '</VALUE.OBJECTWITHPATH>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "VALUE.OBJECTWITHPATH with missing children",
        dict(
            xml_str=''
            '<VALUE.OBJECTWITHPATH/>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "VALUE.OBJECTWITHPATH for instance with missing INSTANCEPATH child",
        dict(
            xml_str=''
            '<VALUE.OBJECTWITHPATH>\n'
            '  <INSTANCE CLASSNAME="CIM_Foo"/>\n'
            '</VALUE.OBJECTWITHPATH>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "VALUE.OBJECTWITHPATH for instance with missing INSTANCE child",
        dict(
            xml_str=''
            '<VALUE.OBJECTWITHPATH>\n'
            '  <INSTANCEPATH>\n'
            '    <NAMESPACEPATH>\n'
            '      <HOST>woot.com</HOST>\n'
            '      <LOCALNAMESPACEPATH>\n'
            '        <NAMESPACE NAME="foo"/>\n'
            '      </LOCALNAMESPACEPATH>\n'
            '    </NAMESPACEPATH>\n'
            '    <INSTANCENAME CLASSNAME="CIM_Foo"/>\n'
            '  </INSTANCEPATH>\n'
            '</VALUE.OBJECTWITHPATH>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "VALUE.OBJECTWITHPATH for instance with incorrectly ordered children",
        dict(
            xml_str=''
            '<VALUE.OBJECTWITHPATH>\n'
            '  <INSTANCE CLASSNAME="CIM_Foo"/>\n'
            '  <INSTANCEPATH>\n'
            '    <NAMESPACEPATH>\n'
            '      <HOST>woot.com</HOST>\n'
            '      <LOCALNAMESPACEPATH>\n'
            '        <NAMESPACE NAME="foo"/>\n'
            '      </LOCALNAMESPACEPATH>\n'
            '    </NAMESPACEPATH>\n'
            '    <INSTANCENAME CLASSNAME="CIM_Foo"/>\n'
            '  </INSTANCEPATH>\n'
            '</VALUE.OBJECTWITHPATH>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "VALUE.OBJECTWITHPATH for instance (normal case)",
        dict(
            xml_str=''
            '<VALUE.OBJECTWITHPATH>\n'
            '  <INSTANCEPATH>\n'
            '    <NAMESPACEPATH>\n'
            '      <HOST>woot.com</HOST>\n'
            '      <LOCALNAMESPACEPATH>\n'
            '        <NAMESPACE NAME="foo"/>\n'
            '      </LOCALNAMESPACEPATH>\n'
            '    </NAMESPACEPATH>\n'
            '    <INSTANCENAME CLASSNAME="CIM_Foo"/>\n'
            '  </INSTANCEPATH>\n'
            '  <INSTANCE CLASSNAME="CIM_Foo"/>\n'
            '</VALUE.OBJECTWITHPATH>\n',
            exp_result=CIMInstance(
                'CIM_Foo',
                path=CIMInstanceName(
                    'CIM_Foo',
                    namespace='foo',
                    host='woot.com',
                ),
            ),
        ),
        None, None, True
    ),
    (
        "VALUE.OBJECTWITHPATH for class with missing CLASSPATH child",
        dict(
            xml_str=''
            '<VALUE.OBJECTWITHPATH>\n'
            '  <CLASS NAME="CIM_Foo"/>\n'
            '</VALUE.OBJECTWITHPATH>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "VALUE.OBJECTWITHPATH for class with missing CLASS child",
        dict(
            xml_str=''
            '<VALUE.OBJECTWITHPATH>\n'
            '  <CLASSPATH>\n'
            '    <NAMESPACEPATH>\n'
            '      <HOST>woot.com</HOST>\n'
            '      <LOCALNAMESPACEPATH>\n'
            '        <NAMESPACE NAME="foo"/>\n'
            '      </LOCALNAMESPACEPATH>\n'
            '    </NAMESPACEPATH>\n'
            '    <CLASSNAME NAME="CIM_Foo"/>\n'
            '  </CLASSPATH>\n'
            '</VALUE.OBJECTWITHPATH>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "VALUE.OBJECTWITHPATH for class with incorrectly ordered children",
        dict(
            xml_str=''
            '<VALUE.OBJECTWITHPATH>\n'
            '  <CLASS NAME="CIM_Foo"/>\n'
            '  <CLASSPATH>\n'
            '    <NAMESPACEPATH>\n'
            '      <HOST>woot.com</HOST>\n'
            '      <LOCALNAMESPACEPATH>\n'
            '        <NAMESPACE NAME="foo"/>\n'
            '      </LOCALNAMESPACEPATH>\n'
            '    </NAMESPACEPATH>\n'
            '    <CLASSNAME NAME="CIM_Foo"/>\n'
            '  </CLASSPATH>\n'
            '</VALUE.OBJECTWITHPATH>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "VALUE.OBJECTWITHPATH for class (normal case)",
        dict(
            xml_str=''
            '<VALUE.OBJECTWITHPATH>\n'
            '  <CLASSPATH>\n'
            '    <NAMESPACEPATH>\n'
            '      <HOST>woot.com</HOST>\n'
            '      <LOCALNAMESPACEPATH>\n'
            '        <NAMESPACE NAME="foo"/>\n'
            '      </LOCALNAMESPACEPATH>\n'
            '    </NAMESPACEPATH>\n'
            '    <CLASSNAME NAME="CIM_Foo"/>\n'
            '  </CLASSPATH>\n'
            '  <CLASS NAME="CIM_Foo"/>\n'
            '</VALUE.OBJECTWITHPATH>\n',
            exp_result=CIMClass(
                'CIM_Foo',
                path=CIMClassName(
                    'CIM_Foo',
                    namespace='foo',
                    host='woot.com',
                ),
            ),
        ),
        None, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_REQUIRED_VALUE_OBJECTWITHPATH_ELEMENT)
@simplified_test_function
def test_required_VALUE_OBJECTWITHPATH_element(
        testcase, xml_str, exp_result):
    """
    Test CIMXMLParser.required_VALUE_OBJECTWITHPATH_element().
    """

    parser = CIMXMLParser(xml_str)

    # Code to be tested
    result = parser.required_VALUE_OBJECTWITHPATH_element()

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None, \
        "Expected exception {!r} has not been raised".\
        format(testcase.exp_exc_types)

    assert result == exp_result


TESTCASES_REQUIRED_VALUE_OBJECTWITHLOCALPATH_ELEMENT = [
    (
        "No VALUE.OBJECTWITHLOCALPATH but different element",
        dict(
            xml_str='<VALUE.OBJECTWITHLOCALPATH.XXX/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "VALUE.OBJECTWITHLOCALPATH with invalid child element",
        dict(
            xml_str=''
            '<VALUE.OBJECTWITHLOCALPATH>\n'
            '  <LOCALCLASSPATH>\n'
            '    <LOCALNAMESPACEPATH>\n'
            '      <NAMESPACE NAME="foo"/>\n'
            '    </LOCALNAMESPACEPATH>\n'
            '    <CLASSNAME NAME="CIM_Foo"/>\n'
            '  </LOCALCLASSPATH>\n'
            '  <CLASS NAME="CIM_Foo"/>\n'
            '  <XXX/>\n'
            '</VALUE.OBJECTWITHLOCALPATH>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "VALUE.OBJECTWITHLOCALPATH with invalid content text",
        dict(
            xml_str=''
            '<VALUE.OBJECTWITHLOCALPATH>\n'
            '  xxx\n'
            '  <LOCALCLASSPATH>\n'
            '    <LOCALNAMESPACEPATH>\n'
            '      <NAMESPACE NAME="foo"/>\n'
            '    </LOCALNAMESPACEPATH>\n'
            '    <CLASSNAME NAME="CIM_Foo"/>\n'
            '  </LOCALCLASSPATH>\n'
            '  <CLASS NAME="CIM_Foo"/>\n'
            '</VALUE.OBJECTWITHLOCALPATH>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "VALUE.OBJECTWITHLOCALPATH with invalid trailing text",
        dict(
            xml_str=''
            '<VALUE.OBJECTWITHLOCALPATH>\n'
            '  <LOCALCLASSPATH>\n'
            '    <LOCALNAMESPACEPATH>\n'
            '      <NAMESPACE NAME="foo"/>\n'
            '    </LOCALNAMESPACEPATH>\n'
            '    <CLASSNAME NAME="CIM_Foo"/>\n'
            '  </LOCALCLASSPATH>\n'
            '  <CLASS NAME="CIM_Foo"/>\n'
            '  xxx\n'
            '</VALUE.OBJECTWITHLOCALPATH>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "VALUE.OBJECTWITHLOCALPATH with missing children",
        dict(
            xml_str=''
            '<VALUE.OBJECTWITHLOCALPATH/>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "VALUE.OBJECTWITHLOCALPATH for instance with missing LOCALINSTANCEPATH "
        "child",
        dict(
            xml_str=''
            '<VALUE.OBJECTWITHLOCALPATH>\n'
            '  <INSTANCE CLASSNAME="CIM_Foo"/>\n'
            '</VALUE.OBJECTWITHLOCALPATH>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "VALUE.OBJECTWITHLOCALPATH for instance with missing INSTANCE child",
        dict(
            xml_str=''
            '<VALUE.OBJECTWITHLOCALPATH>\n'
            '  <LOCALINSTANCEPATH>\n'
            '    <LOCALNAMESPACEPATH>\n'
            '      <NAMESPACE NAME="foo"/>\n'
            '    </LOCALNAMESPACEPATH>\n'
            '    <INSTANCENAME CLASSNAME="CIM_Foo"/>\n'
            '  </LOCALINSTANCEPATH>\n'
            '</VALUE.OBJECTWITHLOCALPATH>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "VALUE.OBJECTWITHLOCALPATH for instance (normal case)",
        dict(
            xml_str=''
            '<VALUE.OBJECTWITHLOCALPATH>\n'
            '  <LOCALINSTANCEPATH>\n'
            '    <LOCALNAMESPACEPATH>\n'
            '      <NAMESPACE NAME="foo"/>\n'
            '    </LOCALNAMESPACEPATH>\n'
            '    <INSTANCENAME CLASSNAME="CIM_Foo"/>\n'
            '  </LOCALINSTANCEPATH>\n'
            '  <INSTANCE CLASSNAME="CIM_Foo"/>\n'
            '</VALUE.OBJECTWITHLOCALPATH>\n',
            exp_result=CIMInstance(
                'CIM_Foo',
                path=CIMInstanceName(
                    'CIM_Foo',
                    namespace='foo',
                ),
            ),
        ),
        None, None, True
    ),
    (
        "VALUE.OBJECTWITHLOCALPATH for class (normal case)",
        dict(
            xml_str=''
            '<VALUE.OBJECTWITHLOCALPATH>\n'
            '  <LOCALCLASSPATH>\n'
            '    <LOCALNAMESPACEPATH>\n'
            '      <NAMESPACE NAME="foo"/>\n'
            '    </LOCALNAMESPACEPATH>\n'
            '    <CLASSNAME NAME="CIM_Foo"/>\n'
            '  </LOCALCLASSPATH>\n'
            '  <CLASS NAME="CIM_Foo"/>\n'
            '</VALUE.OBJECTWITHLOCALPATH>\n',
            exp_result=CIMClass(
                'CIM_Foo',
                path=CIMClassName(
                    'CIM_Foo',
                    namespace='foo',
                ),
            ),
        ),
        None, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_REQUIRED_VALUE_OBJECTWITHLOCALPATH_ELEMENT)
@simplified_test_function
def test_required_VALUE_OBJECTWITHLOCALPATH_element(
        testcase, xml_str, exp_result):
    """
    Test CIMXMLParser.required_VALUE_OBJECTWITHLOCALPATH_element().
    """

    parser = CIMXMLParser(xml_str)

    # Code to be tested
    result = parser.required_VALUE_OBJECTWITHLOCALPATH_element()

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None, \
        "Expected exception {!r} has not been raised".\
        format(testcase.exp_exc_types)

    assert result == exp_result


TESTCASES_REQUIRED_VALUE_OBJECT_ELEMENT = [
    (
        "No VALUE.OBJECT but different element",
        dict(
            xml_str='<VALUE.OBJECT.XXX/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "VALUE.OBJECT with invalid child element",
        dict(
            xml_str=''
            '<VALUE.OBJECT>\n'
            '  <INSTANCE CLASSNAME="CIM_Foo"/>\n'
            '  <XXX/>\n'
            '</VALUE.OBJECT>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "VALUE.OBJECT with invalid child element instead",
        dict(
            xml_str=''
            '<VALUE.OBJECT>\n'
            '  <XXX/>\n'
            '</VALUE.OBJECT>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "VALUE.OBJECT with invalid content text",
        dict(
            xml_str=''
            '<VALUE.OBJECT>\n'
            '  xxx\n'
            '  <INSTANCE CLASSNAME="CIM_Foo"/>\n'
            '</VALUE.OBJECT>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "VALUE.OBJECT with invalid trailing text",
        dict(
            xml_str=''
            '<VALUE.OBJECT>\n'
            '  <INSTANCE CLASSNAME="CIM_Foo"/>\n'
            '  xxx\n'
            '</VALUE.OBJECT>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "VALUE.OBJECT with missing child",
        dict(
            xml_str=''
            '<VALUE.OBJECT/>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "VALUE.OBJECT with INSTANCE (normal case)",
        dict(
            xml_str=''
            '<VALUE.OBJECT>\n'
            '  <INSTANCE CLASSNAME="CIM_Foo"/>\n'
            '</VALUE.OBJECT>\n',
            exp_result=CIMInstance('CIM_Foo'),
        ),
        None, None, True
    ),
    (
        "VALUE.OBJECT with CLASS (normal case)",
        dict(
            xml_str=''
            '<VALUE.OBJECT>\n'
            '  <CLASS NAME="CIM_Foo"/>\n'
            '</VALUE.OBJECT>\n',
            exp_result=CIMClass('CIM_Foo'),
        ),
        None, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_REQUIRED_VALUE_OBJECT_ELEMENT)
@simplified_test_function
def test_required_VALUE_OBJECT_element(
        testcase, xml_str, exp_result):
    """
    Test CIMXMLParser.required_VALUE_OBJECT_element().
    """

    parser = CIMXMLParser(xml_str)

    # Code to be tested
    result = parser.required_VALUE_OBJECT_element()

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None, \
        "Expected exception {!r} has not been raised".\
        format(testcase.exp_exc_types)

    assert result == exp_result


TESTCASES_REQUIRED_BOOLEAN_VALUE_ELEMENT = [
    (
        "No VALUE but different element",
        dict(
            xml_str='<VALUE.XXX/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "VALUE with True",
        dict(
            xml_str='<VALUE>True</VALUE>',
            exp_result=True,
        ),
        None, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_REQUIRED_BOOLEAN_VALUE_ELEMENT)
@simplified_test_function
def test_required_boolean_VALUE_element(testcase, xml_str, exp_result):
    """
    Test CIMXMLParser.required_boolean_VALUE_element().
    """

    parser = CIMXMLParser(xml_str)

    # Code to be tested
    result = parser.required_boolean_VALUE_element()

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None, \
        "Expected exception {!r} has not been raised".\
        format(testcase.exp_exc_types)

    assert result == exp_result


TESTCASES_REQUIRED_STRING_VALUE_ELEMENT = [
    (
        "No VALUE but different element",
        dict(
            xml_str='<VALUE.XXX/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "VALUE with decimal number",
        dict(
            xml_str='<VALUE>42</VALUE>',
            exp_result=u'42',
        ),
        None, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_REQUIRED_STRING_VALUE_ELEMENT)
@simplified_test_function
def test_required_string_VALUE_element(testcase, xml_str, exp_result):
    """
    Test CIMXMLParser.required_string_VALUE_element().
    """

    parser = CIMXMLParser(xml_str)

    # Code to be tested
    result = parser.required_string_VALUE_element()

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None, \
        "Expected exception {!r} has not been raised".\
        format(testcase.exp_exc_types)

    assert result == exp_result


TESTCASES_REQUIRED_VALUE_ELEMENT = [
    (
        "No VALUE but different element",
        dict(
            xml_str='<VALUE.XXX/>',
            cimtype='string',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "VALUE with invalid child element",
        dict(
            xml_str=''
            '<VALUE>\n'
            '  <XXX/>\n'
            '</VALUE>\n',
            cimtype='string',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "VALUE with invalid type",
        dict(
            xml_str='<VALUE>bla</VALUE>',
            cimtype='bla',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "VALUE with WBEM URI, type reference (invalid)",
        dict(
            xml_str='<VALUE>/root:CIM_Foo.P1=a</VALUE>',
            cimtype='reference',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "VALUE that is empty, type string",
        dict(
            xml_str='<VALUE></VALUE>',
            cimtype='string',
            exp_result=u'',
        ),
        None, None, True
    ),
    (
        "VALUE with ASCII string, type string",
        dict(
            xml_str=''
            '<VALUE>abc</VALUE>\n',
            cimtype='string',
            exp_result=u'abc',
        ),
        None, None, True
    ),
    (
        "VALUE with ASCII string with WS, type string",
        dict(
            xml_str=''
            '<VALUE> a  b  c </VALUE>\n',
            cimtype='string',
            exp_result=u' a  b  c ',
        ),
        None, None, True
    ),
    (
        "VALUE with non-ASCII UCS-2 string, type string",
        dict(
            xml_str=b''
            b'<VALUE>\xC3\xA9</VALUE>\n',
            cimtype='string',
            exp_result=u'\u00E9',  # LATIN SMALL LETTER E WITH ACUTE
        ),
        None, None, True
    ),
    (
        "VALUE with non-UCS-2 string, type string",
        dict(
            xml_str=b''
            b'<VALUE>\xF0\x90\x85\x82</VALUE>\n',
            cimtype='string',
            exp_result=u'\U00010142',  # GREEK ACROPHONIC ATTIC ONE DRACHMA
        ),
        None, None, True
    ),
    (
        "VALUE with decimal number, type string",
        dict(
            xml_str='<VALUE>42</VALUE>',
            cimtype='string',
            exp_result=u'42',
        ),
        None, None, True
    ),
    (
        "VALUE with XML entity &lt;, type string",
        dict(
            xml_str='<VALUE>&lt;</VALUE>',
            cimtype='string',
            exp_result=u'<',
        ),
        None, None, True
    ),
    (
        "VALUE with XML entity &gt;, type string",
        dict(
            xml_str='<VALUE>&gt;</VALUE>',
            cimtype='string',
            exp_result=u'>',
        ),
        None, None, True
    ),
    (
        "VALUE with XML entity &amp;, type string",
        dict(
            xml_str='<VALUE>&amp;</VALUE>',
            cimtype='string',
            exp_result=u'&',
        ),
        None, None, True
    ),
    (
        "VALUE with XML entity &apos;, type string",
        dict(
            xml_str='<VALUE>&apos;</VALUE>',
            cimtype='string',
            exp_result=u"'",
        ),
        None, None, True
    ),
    (
        "VALUE with XML entity &quot;, type string",
        dict(
            xml_str='<VALUE>&quot;</VALUE>',
            cimtype='string',
            exp_result=u'"',
        ),
        None, None, True
    ),
    (
        "VALUE with CDATA section containing <, type string",
        dict(
            xml_str='<VALUE><![CDATA[<]]></VALUE>',
            cimtype='string',
            exp_result=u'<',
        ),
        None, None, True
    ),
    (
        "VALUE with CDATA section containing >, type string",
        dict(
            xml_str='<VALUE><![CDATA[>]]></VALUE>',
            cimtype='string',
            exp_result=u'>',
        ),
        None, None, True
    ),
    (
        "VALUE with CDATA section containing &, type string",
        dict(
            xml_str='<VALUE><![CDATA[&]]></VALUE>',
            cimtype='string',
            exp_result=u'&',
        ),
        None, None, True
    ),
    (
        "VALUE element that is empty, type boolean",
        dict(
            xml_str='<VALUE></VALUE>',
            cimtype='boolean',
            exp_result=None,
        ),
        None, ToleratedServerIssueWarning, True
    ),
    (
        "VALUE with True, type boolean",
        dict(
            xml_str='<VALUE>True</VALUE>',
            cimtype='boolean',
            exp_result=True,
        ),
        None, None, True
    ),
    (
        "VALUE element that is empty, type None",
        dict(
            xml_str='<VALUE></VALUE>',
            cimtype=None,
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "VALUE with decimal number, type None",
        dict(
            xml_str='<VALUE>42</VALUE>',
            cimtype=None,
            exp_result=42,
        ),
        None, None, True
    ),
    (
        "VALUE element that is empty, type uint8",
        dict(
            xml_str='<VALUE></VALUE>',
            cimtype='uint8',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "VALUE with decimal number, type uint8",
        dict(
            xml_str='<VALUE>42</VALUE>',
            cimtype='uint8',
            exp_result=Uint8(42),
        ),
        None, None, True
    ),
    (
        "VALUE with decimal number, type uint16",
        dict(
            xml_str='<VALUE>42</VALUE>',
            cimtype='uint16',
            exp_result=Uint16(42),
        ),
        None, None, True
    ),
    (
        "VALUE with decimal number, type uint32",
        dict(
            xml_str='<VALUE>42</VALUE>',
            cimtype='uint32',
            exp_result=Uint32(42),
        ),
        None, None, True
    ),
    (
        "VALUE with decimal number, type uint64",
        dict(
            xml_str='<VALUE>42</VALUE>',
            cimtype='uint64',
            exp_result=Uint64(42),
        ),
        None, None, True
    ),
    (
        "VALUE with decimal number, type sint8",
        dict(
            xml_str='<VALUE>-42</VALUE>',
            cimtype='sint8',
            exp_result=Sint8(-42),
        ),
        None, None, True
    ),
    (
        "VALUE with decimal number, type sint16",
        dict(
            xml_str='<VALUE>-42</VALUE>',
            cimtype='sint16',
            exp_result=Sint16(-42),
        ),
        None, None, True
    ),
    (
        "VALUE with decimal number, type sint32",
        dict(
            xml_str='<VALUE>-42</VALUE>',
            cimtype='sint32',
            exp_result=Sint32(-42),
        ),
        None, None, True
    ),
    (
        "VALUE with decimal number, type sint64",
        dict(
            xml_str='<VALUE>-42</VALUE>',
            cimtype='sint64',
            exp_result=Sint64(-42),
        ),
        None, None, True
    ),
    (
        "VALUE with decimal number, type real32",
        dict(
            xml_str='<VALUE>42.0</VALUE>',
            cimtype='real32',
            exp_result=Real32(42.0),
        ),
        None, None, True
    ),
    (
        "VALUE with decimal number, type real64",
        dict(
            xml_str='<VALUE>42.0</VALUE>',
            cimtype='real64',
            exp_result=Real64(42.0),
        ),
        None, None, True
    ),
    (
        "VALUE with interval string, type datetime",
        dict(
            xml_str='<VALUE>00000183132542.234567:000</VALUE>',
            cimtype='datetime',
            exp_result=CIMDateTime('00000183132542.234567:000'),
        ),
        None, None, True
    ),
    (
        "VALUE with ASCII letter, type char16",
        dict(
            xml_str='<VALUE>a</VALUE>',
            cimtype='char16',
            exp_result=u'a',
        ),
        None, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_REQUIRED_VALUE_ELEMENT)
@simplified_test_function
def test_required_VALUE_element(testcase, xml_str, cimtype, exp_result):
    """
    Test CIMXMLParser.required_VALUE_element().
    """

    parser = CIMXMLParser(xml_str)

    # Code to be tested
    result = parser.required_VALUE_element(cimtype)

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None, \
        "Expected exception {!r} has not been raised".\
        format(testcase.exp_exc_types)

    assert result == exp_result


TESTCASES_REQUIRED_VALUE_ARRAY_ELEMENT = [
    (
        "No VALUE.ARRAY but different element",
        dict(
            xml_str='<VALUE.ARRAY.XXX/>',
            cimtype=None,
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "VALUE.ARRAY with invalid kind of child element as first item",
        dict(
            xml_str=''
            '<VALUE.ARRAY>\n'
            '  <XXX/>\n'
            '  <VALUE>a</VALUE>\n'
            '</VALUE.ARRAY>\n',
            cimtype=None,
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "VALUE.ARRAY with invalid kind of child element as second item",
        dict(
            xml_str=''
            '<VALUE.ARRAY>\n'
            '  <VALUE>a</VALUE>\n'
            '  <XXX/>\n'
            '</VALUE.ARRAY>\n',
            cimtype=None,
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "VALUE.ARRAY with invalid content text",
        dict(
            xml_str=''
            '<VALUE.ARRAY>\n'
            '  xxx\n'
            '  <VALUE>a</VALUE>\n'
            '</VALUE.ARRAY>\n',
            cimtype=None,
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "VALUE.ARRAY with invalid trailing text",
        dict(
            xml_str=''
            '<VALUE.ARRAY>\n'
            '  <VALUE>a</VALUE>\n'
            '  xxx\n'
            '</VALUE.ARRAY>\n',
            cimtype=None,
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "VALUE.ARRAY that is empty (no type)",
        dict(
            xml_str=''
            '<VALUE.ARRAY/>\n',
            cimtype=None,
            exp_result=[
            ],
        ),
        None, None, True
    ),
    (
        "VALUE.ARRAY with one item that is ASCII string (string type)",
        dict(
            xml_str=''
            '<VALUE.ARRAY>\n'
            '  <VALUE>a</VALUE>\n'
            '</VALUE.ARRAY>\n',
            cimtype='string',
            exp_result=[
                u'a',
            ],
        ),
        None, None, True
    ),
    (
        "VALUE.ARRAY with two items that are ASCII strings (string type)",
        dict(
            xml_str=''
            '<VALUE.ARRAY>\n'
            '  <VALUE>a</VALUE>\n'
            '  <VALUE>b</VALUE>\n'
            '</VALUE.ARRAY>\n',
            cimtype='string',
            exp_result=[
                u'a',
                u'b',
            ],
        ),
        None, None, True
    ),
    (
        "VALUE.ARRAY with one item that is a numeric value (string type)",
        dict(
            xml_str=''
            '<VALUE.ARRAY>\n'
            '  <VALUE>42</VALUE>\n'
            '</VALUE.ARRAY>\n',
            cimtype='string',
            exp_result=[
                u'42',
            ],
        ),
        None, None, True
    ),
    (
        "VALUE.ARRAY with one item that is a numeric value (uint8 type)",
        dict(
            xml_str=''
            '<VALUE.ARRAY>\n'
            '  <VALUE>42</VALUE>\n'
            '</VALUE.ARRAY>\n',
            cimtype='uint8',
            exp_result=[
                Uint8(42),
            ],
        ),
        None, None, True
    ),
    (
        "VALUE.ARRAY with one item that is boolean string (string type)",
        dict(
            xml_str=''
            '<VALUE.ARRAY>\n'
            '  <VALUE>TRUE</VALUE>\n'
            '</VALUE.ARRAY>\n',
            cimtype='string',
            exp_result=[
                u'TRUE',
            ],
        ),
        None, None, True
    ),
    (
        "VALUE.ARRAY with one item that is boolean string (boolean type)",
        dict(
            xml_str=''
            '<VALUE.ARRAY>\n'
            '  <VALUE>TRUE</VALUE>\n'
            '</VALUE.ARRAY>\n',
            cimtype='boolean',
            exp_result=[
                True,
            ],
        ),
        None, None, True
    ),
    (
        "VALUE.ARRAY with one VALUE.NULL item (boolean type)",
        dict(
            xml_str=''
            '<VALUE.ARRAY>\n'
            '  <VALUE.NULL/>\n'
            '</VALUE.ARRAY>\n',
            cimtype='boolean',
            exp_result=[
                None,
            ],
        ),
        None, None, True
    ),
    (
        "VALUE.ARRAY with a VALUE.NULL item and a string item (string type)",
        dict(
            xml_str=''
            '<VALUE.ARRAY>\n'
            '  <VALUE.NULL/>\n'
            '  <VALUE>a</VALUE>\n'
            '</VALUE.ARRAY>\n',
            cimtype='string',
            exp_result=[
                None,
                u'a',
            ],
        ),
        None, None, True
    ),
    (
        "VALUE.ARRAY with VALUE.NULL, string, VALUE.NULL items (string type)",
        dict(
            xml_str=''
            '<VALUE.ARRAY>\n'
            '  <VALUE.NULL/>\n'
            '  <VALUE>a</VALUE>\n'
            '  <VALUE.NULL/>\n'
            '</VALUE.ARRAY>\n',
            cimtype='string',
            exp_result=[
                None,
                u'a',
                None,
            ],
        ),
        None, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_REQUIRED_VALUE_ARRAY_ELEMENT)
@simplified_test_function
def test_required_VALUE_ARRAY_element(
        testcase, xml_str, cimtype, exp_result):
    """
    Test CIMXMLParser.required_VALUE_ARRAY_element().
    """

    parser = CIMXMLParser(xml_str)

    # Code to be tested
    result = parser.required_VALUE_ARRAY_element(cimtype)

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None, \
        "Expected exception {!r} has not been raised".\
        format(testcase.exp_exc_types)

    assert result == exp_result


TESTCASES_REQUIRED_VALUE_NULL_ELEMENT = [
    (
        "No VALUE.NULL but different element",
        dict(
            xml_str='<VALUE.NULL.XXX/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "VALUE.NULL with invalid child element",
        dict(
            xml_str=''
            '<VALUE.NULL>\n'
            '  <XXX/>\n'
            '</VALUE.NULL>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "VALUE.NULL with invalid content text",
        dict(
            xml_str=''
            '<VALUE.NULL>\n'
            '  xxx\n'
            '</VALUE.NULL>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "VALUE.NULL (normal case)",
        dict(
            xml_str=''
            '<VALUE.NULL/>\n',
            exp_result=None,
        ),
        None, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_REQUIRED_VALUE_NULL_ELEMENT)
@simplified_test_function
def test_required_VALUE_NULL_element(
        testcase, xml_str, exp_result):
    """
    Test CIMXMLParser.required_VALUE_NULL_element().
    """

    parser = CIMXMLParser(xml_str)

    # Code to be tested
    result = parser.required_VALUE_NULL_element()

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None, \
        "Expected exception {!r} has not been raised".\
        format(testcase.exp_exc_types)

    assert result == exp_result


TESTCASES_REQUIRED_VALUE_REFARRAY_ELEMENT = [
    (
        "No VALUE.REFARRAY but different element",
        dict(
            xml_str='<VALUE.REFARRAY.XXX/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "VALUE.REFARRAY with invalid child element",
        dict(
            xml_str=''
            '<VALUE.REFARRAY>\n'
            '  <VALUE.REFERENCE>\n'
            '    <INSTANCENAME CLASSNAME="CIM_Foo"/>\n'
            '  </VALUE.REFERENCE>\n'
            '  <XXX/>\n'
            '</VALUE.REFARRAY>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "VALUE.REFARRAY with invalid content text",
        dict(
            xml_str=''
            '<VALUE.REFARRAY>\n'
            '  xxx\n'
            '  <VALUE.REFERENCE>\n'
            '    <INSTANCENAME CLASSNAME="CIM_Foo"/>\n'
            '  </VALUE.REFERENCE>\n'
            '</VALUE.REFARRAY>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "VALUE.REFARRAY with invalid trailing text",
        dict(
            xml_str=''
            '<VALUE.REFARRAY>\n'
            '  <VALUE.REFERENCE>\n'
            '    <INSTANCENAME CLASSNAME="CIM_Foo"/>\n'
            '  </VALUE.REFERENCE>\n'
            '  xxx\n'
            '</VALUE.REFARRAY>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "VALUE.REFARRAY that is empty",
        dict(
            xml_str=''
            '<VALUE.REFARRAY/>\n',
            exp_result=[
            ],
        ),
        None, None, True
    ),
    (
        "VALUE.REFARRAY with one item",
        dict(
            xml_str=''
            '<VALUE.REFARRAY>\n'
            '  <VALUE.REFERENCE>\n'
            '    <INSTANCENAME CLASSNAME="CIM_Foo"/>\n'
            '  </VALUE.REFERENCE>\n'
            '</VALUE.REFARRAY>\n',
            exp_result=[
                CIMInstanceName('CIM_Foo'),
            ],
        ),
        None, None, True
    ),
    (
        "VALUE.REFARRAY with two items",
        dict(
            xml_str=''
            '<VALUE.REFARRAY>\n'
            '  <VALUE.REFERENCE>\n'
            '    <INSTANCENAME CLASSNAME="CIM_Foo"/>\n'
            '  </VALUE.REFERENCE>\n'
            '  <VALUE.REFERENCE>\n'
            '    <INSTANCENAME CLASSNAME="CIM_Bar"/>\n'
            '  </VALUE.REFERENCE>\n'
            '</VALUE.REFARRAY>\n',
            exp_result=[
                CIMInstanceName('CIM_Foo'),
                CIMInstanceName('CIM_Bar'),
            ],
        ),
        None, None, True
    ),
    (
        "VALUE.REFARRAY with one VALUE.NULL item",
        dict(
            xml_str=''
            '<VALUE.REFARRAY>\n'
            '  <VALUE.NULL/>\n'
            '</VALUE.REFARRAY>\n',
            exp_result=[
                None,
            ],
        ),
        None, None, True
    ),
    (
        "VALUE.REFARRAY with a VALUE.NULL item and a reference item",
        dict(
            xml_str=''
            '<VALUE.REFARRAY>\n'
            '  <VALUE.NULL/>\n'
            '  <VALUE.REFERENCE>\n'
            '    <INSTANCENAME CLASSNAME="CIM_Foo"/>\n'
            '  </VALUE.REFERENCE>\n'
            '</VALUE.REFARRAY>\n',
            exp_result=[
                None,
                CIMInstanceName('CIM_Foo'),
            ],
        ),
        None, None, True
    ),
    (
        "VALUE.REFARRAY with VALUE.NULL, reference, VALUE.NULL items",
        dict(
            xml_str=''
            '<VALUE.REFARRAY>\n'
            '  <VALUE.NULL/>\n'
            '  <VALUE.REFERENCE>\n'
            '    <INSTANCENAME CLASSNAME="CIM_Foo"/>\n'
            '  </VALUE.REFERENCE>\n'
            '  <VALUE.NULL/>\n'
            '</VALUE.REFARRAY>\n',
            exp_result=[
                None,
                CIMInstanceName('CIM_Foo'),
                None,
            ],
        ),
        None, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_REQUIRED_VALUE_REFARRAY_ELEMENT)
@simplified_test_function
def test_required_VALUE_REFARRAY_element(
        testcase, xml_str, exp_result):
    """
    Test CIMXMLParser.required_VALUE_REFARRAY_element().
    """

    parser = CIMXMLParser(xml_str)

    # Code to be tested
    result = parser.required_VALUE_REFARRAY_element()

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None, \
        "Expected exception {!r} has not been raised".\
        format(testcase.exp_exc_types)

    assert result == exp_result


TESTCASES_REQUIRED_VALUE_NAMEDOBJECT_ELEMENT = [
    (
        "No VALUE.NAMEDOBJECT but different element",
        dict(
            xml_str='<VALUE.NAMEDOBJECT.XXX/>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "VALUE.NAMEDOBJECT with invalid child element",
        dict(
            xml_str=''
            '<VALUE.NAMEDOBJECT>\n'
            '  <INSTANCENAME CLASSNAME="CIM_Foo"/>\n'
            '  <INSTANCE CLASSNAME="CIM_Foo"/>\n'
            '  <XXX/>\n'
            '</VALUE.NAMEDOBJECT>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "VALUE.NAMEDOBJECT with invalid content text",
        dict(
            xml_str=''
            '<VALUE.NAMEDOBJECT>\n'
            '  xxx\n'
            '  <INSTANCENAME CLASSNAME="CIM_Foo"/>\n'
            '  <INSTANCE CLASSNAME="CIM_Foo"/>\n'
            '</VALUE.NAMEDOBJECT>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "VALUE.NAMEDOBJECT with invalid trailing text",
        dict(
            xml_str=''
            '<VALUE.NAMEDOBJECT>\n'
            '  <INSTANCENAME CLASSNAME="CIM_Foo"/>\n'
            '  <INSTANCE CLASSNAME="CIM_Foo"/>\n'
            '  xxx\n'
            '</VALUE.NAMEDOBJECT>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "VALUE.NAMEDOBJECT with missing children",
        dict(
            xml_str=''
            '<VALUE.NAMEDOBJECT/>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "VALUE.NAMEDOBJECT for instance with missing INSTANCENAME child",
        dict(
            xml_str=''
            '<VALUE.NAMEDOBJECT>\n'
            '  <INSTANCE CLASSNAME="CIM_Foo"/>\n'
            '</VALUE.NAMEDOBJECT>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "VALUE.NAMEDOBJECT for instance with missing INSTANCE child",
        dict(
            xml_str=''
            '<VALUE.NAMEDOBJECT>\n'
            '  <INSTANCENAME CLASSNAME="CIM_Foo"/>\n'
            '</VALUE.NAMEDOBJECT>\n',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "VALUE.NAMEDOBJECT for instance (normal case)",
        dict(
            xml_str=''
            '<VALUE.NAMEDOBJECT>\n'
            '  <INSTANCENAME CLASSNAME="CIM_Foo"/>\n'
            '  <INSTANCE CLASSNAME="CIM_Foo"/>\n'
            '</VALUE.NAMEDOBJECT>\n',
            exp_result=CIMInstance(
                'CIM_Foo',
                path=CIMInstanceName('CIM_Foo'),
            ),
        ),
        None, None, True
    ),
    (
        "VALUE.NAMEDOBJECT for class (normal case)",
        dict(
            xml_str=''
            '<VALUE.NAMEDOBJECT>\n'
            '  <CLASS NAME="CIM_Foo"/>\n'
            '</VALUE.NAMEDOBJECT>\n',
            exp_result=CIMClass('CIM_Foo'),
        ),
        None, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_REQUIRED_VALUE_NAMEDOBJECT_ELEMENT)
@simplified_test_function
def test_required_VALUE_NAMEDOBJECT_element(
        testcase, xml_str, exp_result):
    """
    Test CIMXMLParser.required_VALUE_NAMEDOBJECT_element().
    """

    parser = CIMXMLParser(xml_str)

    # Code to be tested
    result = parser.required_VALUE_NAMEDOBJECT_element()

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None, \
        "Expected exception {!r} has not been raised".\
        format(testcase.exp_exc_types)

    assert result == exp_result


TESTCASES_LIST_OF_EXECQUERY_RESULT_OBJECT_ELEMENTS = [
    (
        "Empty result set",
        dict(
            skip_events=1,
            xml_str=''
            '<DUMMY_ROOT>\n'
            '</DUMMY_ROOT>\n',
            exp_result=[],
        ),
        None, None, True
    ),
    (
        "List with three instances using each possible type of element",
        dict(
            skip_events=1,
            xml_str=''
            '<DUMMY_ROOT>\n'
            '  <VALUE.OBJECT>\n'
            '    <INSTANCE CLASSNAME="CIM_Foo1"/>\n'
            '  </VALUE.OBJECT>\n'
            '  <VALUE.OBJECTWITHLOCALPATH>\n'
            '    <LOCALINSTANCEPATH>\n'
            '      <LOCALNAMESPACEPATH>\n'
            '        <NAMESPACE NAME="foo"/>\n'
            '      </LOCALNAMESPACEPATH>\n'
            '      <INSTANCENAME CLASSNAME="CIM_Foo2"/>\n'
            '    </LOCALINSTANCEPATH>\n'
            '    <INSTANCE CLASSNAME="CIM_Foo2"/>\n'
            '  </VALUE.OBJECTWITHLOCALPATH>\n'
            '  <VALUE.OBJECTWITHPATH>\n'
            '    <INSTANCEPATH>\n'
            '      <NAMESPACEPATH>\n'
            '        <HOST>woot.com</HOST>\n'
            '        <LOCALNAMESPACEPATH>\n'
            '          <NAMESPACE NAME="foo"/>\n'
            '        </LOCALNAMESPACEPATH>\n'
            '      </NAMESPACEPATH>\n'
            '      <INSTANCENAME CLASSNAME="CIM_Foo3"/>\n'
            '    </INSTANCEPATH>\n'
            '    <INSTANCE CLASSNAME="CIM_Foo3"/>\n'
            '  </VALUE.OBJECTWITHPATH>\n'
            '</DUMMY_ROOT>\n',
            exp_result=[
                CIMInstance('CIM_Foo1'),
                CIMInstance(
                    'CIM_Foo2',
                    path=CIMInstanceName(
                        'CIM_Foo2',
                        namespace='foo',
                    ),
                ),
                CIMInstance(
                    'CIM_Foo3',
                    path=CIMInstanceName(
                        'CIM_Foo3',
                        namespace='foo',
                        host='woot.com',
                    ),
                ),
            ],
        ),
        None, None, True
    ),
    (
        "List with three classes using each possible type of element",
        dict(
            skip_events=1,
            xml_str=''
            '<DUMMY_ROOT>\n'
            '  <VALUE.OBJECT>\n'
            '    <CLASS NAME="CIM_Foo1"/>\n'
            '  </VALUE.OBJECT>\n'
            '  <VALUE.OBJECTWITHLOCALPATH>\n'
            '    <LOCALCLASSPATH>\n'
            '      <LOCALNAMESPACEPATH>\n'
            '        <NAMESPACE NAME="foo"/>\n'
            '      </LOCALNAMESPACEPATH>\n'
            '      <CLASSNAME NAME="CIM_Foo2"/>\n'
            '    </LOCALCLASSPATH>\n'
            '    <CLASS NAME="CIM_Foo2"/>\n'
            '  </VALUE.OBJECTWITHLOCALPATH>\n'
            '  <VALUE.OBJECTWITHPATH>\n'
            '    <CLASSPATH>\n'
            '      <NAMESPACEPATH>\n'
            '        <HOST>woot.com</HOST>\n'
            '        <LOCALNAMESPACEPATH>\n'
            '          <NAMESPACE NAME="foo"/>\n'
            '        </LOCALNAMESPACEPATH>\n'
            '      </NAMESPACEPATH>\n'
            '      <CLASSNAME NAME="CIM_Foo3"/>\n'
            '    </CLASSPATH>\n'
            '    <CLASS NAME="CIM_Foo3"/>\n'
            '  </VALUE.OBJECTWITHPATH>\n'
            '</DUMMY_ROOT>\n',
            exp_result=[
                CIMClass('CIM_Foo1'),
                CIMClass(
                    'CIM_Foo2',
                    path=CIMClassName(
                        'CIM_Foo2',
                        namespace='foo',
                    ),
                ),
                CIMClass(
                    'CIM_Foo3',
                    path=CIMClassName(
                        'CIM_Foo3',
                        namespace='foo',
                        host='woot.com',
                    ),
                ),
            ],
        ),
        None, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_LIST_OF_EXECQUERY_RESULT_OBJECT_ELEMENTS)
@simplified_test_function
def test_list_of_execquery_result_object_elements(
        testcase, skip_events, xml_str, exp_result):
    """
    Test CIMXMLParser.list_of_execquery_result_object_elements().
    """

    parser = CIMXMLParser(xml_str)
    for _ in range(skip_events):
        parser.get_next_event()

    # Code to be tested
    result = parser.list_of_execquery_result_object_elements()

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None, \
        "Expected exception {!r} has not been raised".\
        format(testcase.exp_exc_types)

    assert result == exp_result


TESTCASES_PARSE_EMBEDDED_OBJECT = [
    (
        "Input is None",
        dict(
            xml_str=None,
            exp_result=None,
        ),
        None, None, True
    ),
    (
        "Embedded instance without properties",
        dict(
            xml_str=''
            '<INSTANCE CLASSNAME="PyWBEM_Address">\n'
            '</INSTANCE>\n',
            exp_result=CIMInstance('PyWBEM_Address'),
        ),
        None, None, True
    ),
    (
        "Embedded instance with property containing XML-escapes",
        dict(
            xml_str=''
            '<INSTANCE CLASSNAME="PyWBEM_Address">\n'
            '  <PROPERTY NAME="Street" TYPE="string">\n'
            '    <VALUE>Fritz&apos;s &amp; &lt;Cat&gt; Ave &quot;</VALUE>\n'
            '  </PROPERTY>\n'
            '</INSTANCE>\n',
            exp_result=CIMInstance(
                'PyWBEM_Address',
                properties=[
                    CIMProperty(
                        'Street', type='string',
                        value='Fritz\'s & <Cat> Ave "',
                        propagated=False),
                ],
            ),
        ),
        None, None, True
    ),
    (
        "Embedded instance with property containing a CDATA section",
        dict(
            xml_str=''
            '<INSTANCE CLASSNAME="PyWBEM_Address">\n'
            '  <PROPERTY NAME="Street" TYPE="string">\n'
            '    <VALUE>Fritz<![CDATA[\'s & <Cat> Ave "]]></VALUE>\n'
            '  </PROPERTY>\n'
            '</INSTANCE>\n',
            exp_result=CIMInstance(
                'PyWBEM_Address',
                properties=[
                    CIMProperty(
                        'Street', type='string',
                        value='Fritz\'s & <Cat> Ave "',
                        propagated=False),
                ],
            ),
        ),
        None, None, True
    ),
    (
        "Embedded instance with property containing mixed CDATA sections and"
        "XML escapes",
        dict(
            xml_str=''
            '<INSTANCE CLASSNAME="PyWBEM_Address">\n'
            '  <PROPERTY NAME="Street" TYPE="string">\n'
            '    <VALUE>Fritz<![CDATA[\'s]]> &amp; <![CDATA[<Cat>]]> Ave'
            ' &quot;</VALUE>\n'
            '  </PROPERTY>\n'
            '</INSTANCE>\n',
            exp_result=CIMInstance(
                'PyWBEM_Address',
                properties=[
                    CIMProperty(
                        'Street', type='string',
                        value='Fritz\'s & <Cat> Ave "',
                        propagated=False),
                ],
            ),
        ),
        None, None, True
    ),
    (
        "Embedded instance with property containing an XML-escaped embedded "
        "instance",
        dict(
            xml_str=''
            '<INSTANCE CLASSNAME="PyWBEM_Address">\n'
            '  <PROPERTY NAME="Town" TYPE="string" EmbeddedObject="instance">\n'
            '    <VALUE>\n'
            '      &lt;INSTANCE CLASSNAME="PyWBEM_Town"&gt;\n'
            '        &lt;PROPERTY NAME="Name" TYPE="string"&gt;\n'
            '          &lt;VALUE&gt;Fritz Cat Town&lt;/VALUE&gt;\n'
            '        &lt;/PROPERTY&gt;\n'
            '      &lt;/INSTANCE&gt;\n'
            '    </VALUE>\n'
            '  </PROPERTY>\n'
            '</INSTANCE>\n',
            exp_result=CIMInstance(
                'PyWBEM_Address',
                properties=[
                    CIMProperty(
                        'Town', type='string', embedded_object='instance',
                        propagated=False,
                        value=CIMInstance(
                            'PyWBEM_Town',
                            properties=[
                                CIMProperty(
                                    'Name', type='string',
                                    value='Fritz Cat Town',
                                    propagated=False),
                            ],
                        ),
                    ),
                ],
            ),
        ),
        None, None, True
    ),
    (
        "Embedded instance with property containing a CDATA section escaped "
        "embedded instance",
        dict(
            xml_str=''
            '<INSTANCE CLASSNAME="PyWBEM_Address">\n'
            '  <PROPERTY NAME="Town" TYPE="string" EmbeddedObject="instance">\n'
            '    <VALUE>\n'
            '      <![CDATA[\n'
            '        <INSTANCE CLASSNAME="PyWBEM_Town">\n'
            '          <PROPERTY NAME="Name" TYPE="string">\n'
            '            <VALUE>Fritz Cat Town</VALUE>\n'
            '          </PROPERTY>\n'
            '        </INSTANCE>\n'
            '      ]]>\n'
            '    </VALUE>\n'
            '  </PROPERTY>\n'
            '</INSTANCE>\n',
            exp_result=CIMInstance(
                'PyWBEM_Address',
                properties=[
                    CIMProperty(
                        'Town', type='string', embedded_object='instance',
                        propagated=False,
                        value=CIMInstance(
                            'PyWBEM_Town',
                            properties=[
                                CIMProperty(
                                    'Name', type='string',
                                    value='Fritz Cat Town',
                                    propagated=False),
                            ],
                        ),
                    ),
                ],
            ),
        ),
        None, None, True
    ),
    (
        "Embedded instance with property containing an XML-escaped embedded "
        "instance whose property values contain XML escapes",
        dict(
            xml_str=''
            '<INSTANCE CLASSNAME="PyWBEM_Address">\n'
            '  <PROPERTY NAME="Town" TYPE="string" EmbeddedObject="instance">\n'
            '    <VALUE>\n'
            '      &lt;INSTANCE CLASSNAME="PyWBEM_Town"&gt;\n'
            '        &lt;PROPERTY NAME="Name" TYPE="string"&gt;\n'
            '          &lt;VALUE&gt;Fritz&amp;apos;s &amp;amp;'
            ' &amp;lt;Cat&amp;gt; Town &amp;quot;&lt;/VALUE&gt;\n'
            '        &lt;/PROPERTY&gt;\n'
            '      &lt;/INSTANCE&gt;\n'
            '    </VALUE>\n'
            '  </PROPERTY>\n'
            '</INSTANCE>\n',
            exp_result=CIMInstance(
                'PyWBEM_Address',
                properties=[
                    CIMProperty(
                        'Town', type='string', embedded_object='instance',
                        propagated=False,
                        value=CIMInstance(
                            'PyWBEM_Town',
                            properties=[
                                CIMProperty(
                                    'Name', type='string',
                                    value='Fritz\'s & <Cat> Town "',
                                    propagated=False),
                            ],
                        ),
                    ),
                ],
            ),
        ),
        None, None, True
    ),
    (
        "Invalid root element for an embedded object",
        dict(
            xml_str='<VALUE>bla</VALUE>',
            exp_result=None,
        ),
        CIMXMLParseError, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_PARSE_EMBEDDED_OBJECT)
@simplified_test_function
def test_parse_embedded_object(testcase, xml_str, exp_result):
    """
    Test CIMXMLParser.parse_embedded_object().
    """

    parser = CIMXMLParser('')

    # Code to be tested
    result = parser.parse_embedded_object(xml_str)

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None, \
        "Expected exception {!r} has not been raised".\
        format(testcase.exp_exc_types)

    assert result == exp_result


TESTCASES_UNPACK_SIMPLE_VALUE = [
    (
        "Simple CIM-XML value: None, type string",
        dict(
            data=None,
            cimtype='string',
            exp_value=None,
        ),
        None, None, True
    ),
    (
        "Simple CIM-XML value: Decimal number, type string",
        dict(
            data='42',
            cimtype='string',
            exp_value=u'42',
        ),
        None, None, True
    ),
    (
        "Simple CIM-XML value: None, type boolean",
        dict(
            data=None,
            cimtype='boolean',
            exp_value=None,
        ),
        None, None, True
    ),
    (
        "Simple CIM-XML value: True, type boolean",
        dict(
            data='True',
            cimtype='boolean',
            exp_value=True,
        ),
        None, None, True
    ),
    (
        "Simple CIM-XML value: None, type None",
        dict(
            data=None,
            cimtype=None,
            exp_value=None,
        ),
        None, None, True
    ),
    (
        "Simple CIM-XML value: Decimal number, type None",
        dict(
            data='42',
            cimtype=None,
            exp_value=42,
        ),
        None, None, True
    ),
    (
        "Simple CIM-XML value: None, type uint8",
        dict(
            data=None,
            cimtype='uint8',
            exp_value=None,
        ),
        None, None, True
    ),
    (
        "Simple CIM-XML value: Decimal number, type uint8",
        dict(
            data='42',
            cimtype='uint8',
            exp_value=Uint8(42),
        ),
        None, None, True
    ),
    (
        "Simple CIM-XML value: Decimal number, type uint16",
        dict(
            data='42',
            cimtype='uint16',
            exp_value=Uint16(42),
        ),
        None, None, True
    ),
    (
        "Simple CIM-XML value: Decimal number, type uint32",
        dict(
            data='42',
            cimtype='uint32',
            exp_value=Uint32(42),
        ),
        None, None, True
    ),
    (
        "Simple CIM-XML value: Decimal number, type uint64",
        dict(
            data='42',
            cimtype='uint64',
            exp_value=Uint64(42),
        ),
        None, None, True
    ),
    (
        "Simple CIM-XML value: Decimal number, type sint8",
        dict(
            data='-42',
            cimtype='sint8',
            exp_value=Sint8(-42),
        ),
        None, None, True
    ),
    (
        "Simple CIM-XML value: Decimal number, type sint16",
        dict(
            data='-42',
            cimtype='sint16',
            exp_value=Sint16(-42),
        ),
        None, None, True
    ),
    (
        "Simple CIM-XML value: Decimal number, type sint32",
        dict(
            data='-42',
            cimtype='sint32',
            exp_value=Sint32(-42),
        ),
        None, None, True
    ),
    (
        "Simple CIM-XML value: Decimal number, type sint64",
        dict(
            data='-42',
            cimtype='sint64',
            exp_value=Sint64(-42),
        ),
        None, None, True
    ),
    (
        "Simple CIM-XML value: Decimal number, type real32",
        dict(
            data='42.0',
            cimtype='real32',
            exp_value=Real32(42.0),
        ),
        None, None, True
    ),
    (
        "Simple CIM-XML value: Decimal number, type real64",
        dict(
            data='42.0',
            cimtype='real64',
            exp_value=Real64(42.0),
        ),
        None, None, True
    ),
    (
        "Simple CIM-XML value: None, type datetime",
        dict(
            data=None,
            cimtype='datetime',
            exp_value=None,
        ),
        None, None, True
    ),
    (
        "Simple CIM-XML value: Interval string, type datetime",
        dict(
            data='00000183132542.234567:000',
            cimtype='datetime',
            exp_value=CIMDateTime('00000183132542.234567:000'),
        ),
        None, None, True
    ),
    (
        "Simple CIM-XML value: None, type char16",
        dict(
            data=None,
            cimtype='char16',
            exp_value=None,
        ),
        None, None, True
    ),
    (
        "Simple CIM-XML value: ASCII letter, type char16",
        dict(
            data='a',
            cimtype='char16',
            exp_value=u'a',
        ),
        None, None, True
    ),
    (
        "Simple CIM-XML value: None, type reference (invalid)",
        dict(
            data=None,
            cimtype='reference',
            exp_value=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "Simple CIM-XML value: WBEM URI, type reference (invalid)",
        dict(
            data='/root:CIM_Foo.P1=a',
            cimtype='reference',
            exp_value=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "Simple CIM-XML value: Invalid type",
        dict(
            data='bla',
            cimtype='bla',
            exp_value=None,
        ),
        CIMXMLParseError, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_UNPACK_SIMPLE_VALUE)
@simplified_test_function
def test_unpack_simple_value(testcase, data, cimtype, exp_value):
    """
    Test CIMXMLParser.unpack_simple_value().
    """

    parser = CIMXMLParser('')

    # Code to be tested
    value = parser.unpack_simple_value(data, cimtype)

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None, \
        "Expected exception {!r} has not been raised".\
        format(testcase.exp_exc_types)

    assert value == exp_value


TESTCASES_UNPACK_BOOLEAN = [
    (
        "Boolean CIM-XML value: None",
        dict(
            data=None,
            exp_value=None,
        ),
        None, None, True
    ),
    (
        "Boolean CIM-XML value: Empty string",
        dict(
            data='',
            exp_value=None,
        ),
        None, ToleratedServerIssueWarning, True
    ),
    (
        "Boolean CIM-XML value: String FALSE",
        dict(
            data='FALSE',
            exp_value=False,
        ),
        None, None, True
    ),
    (
        "Boolean CIM-XML value: String TRUE",
        dict(
            data='TRUE',
            exp_value=True,
        ),
        None, None, True
    ),
    (
        "Boolean CIM-XML value: String false",
        dict(
            data='false',
            exp_value=False,
        ),
        None, None, True
    ),
    (
        "Boolean CIM-XML value: String true",
        dict(
            data='true',
            exp_value=True,
        ),
        None, None, True
    ),
    (
        "Boolean CIM-XML value: Binary string False",
        dict(
            data=b'False',
            exp_value=False,
        ),
        None, None, True
    ),
    (
        "Boolean CIM-XML value: Unicode string True",
        dict(
            data=u'True',
            exp_value=True,
        ),
        None, None, True
    ),
    (
        "Boolean CIM-XML value: String true with surrounding space",
        dict(
            data=' true ',
            exp_value=True,
        ),
        None, None, True
    ),
    (
        "Boolean CIM-XML value: Invalid value",
        dict(
            data='bla',
            exp_value=None,
        ),
        CIMXMLParseError, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_UNPACK_BOOLEAN)
@simplified_test_function
def test_unpack_boolean(testcase, data, exp_value):
    """
    Test CIMXMLParser.unpack_boolean().
    """

    parser = CIMXMLParser('')

    # Code to be tested
    value = parser.unpack_boolean(data)

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None, \
        "Expected exception {!r} has not been raised".\
        format(testcase.exp_exc_types)

    assert value == exp_value


TESTCASES_UNPACK_NUMERIC = [
    (
        "Numeric CIM-XML value: None (no TYPE)",
        dict(
            data=None,
            cimtype=None,
            exp_value=None,
        ),
        None, None, True
    ),
    (
        "Numeric CIM-XML value: empty string (no TYPE)",
        dict(
            data='',
            cimtype=None,
            exp_value=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "Numeric CIM-XML value: WS char (no TYPE)",
        dict(
            data=' ',
            cimtype=None,
            exp_value=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "Numeric CIM-XML value: Binary ASCII letter (no TYPE)",
        dict(
            data=b'a',
            cimtype=None,
            exp_value=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "Numeric CIM-XML value: Unicode ASCII letter (no TYPE)",
        dict(
            data=u'a',
            cimtype=None,
            exp_value=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "Numeric CIM-XML value: decimal string 0 (no TYPE)",
        dict(
            data='0',
            cimtype=None,
            exp_value=0,
        ),
        None, None, True
    ),
    (
        "Numeric CIM-XML value: decimal string 4 (no TYPE)",
        dict(
            data='4',
            cimtype=None,
            exp_value=4,
        ),
        None, None, True
    ),
    (
        "Numeric CIM-XML value: decimal string 42 (no TYPE)",
        dict(
            data=b'42',
            cimtype=None,
            exp_value=42,
        ),
        None, None, True
    ),
    (
        "Numeric CIM-XML value: decimal string -42 (no TYPE)",
        dict(
            data='-42',
            cimtype=None,
            exp_value=-42,
        ),
        None, None, True
    ),
    (
        "Numeric CIM-XML value: decimal string that exceeds Python 2 "
        "positive int limit but not CIM uint64 max value (no TYPE)",
        dict(
            data='9223372036854775808',
            cimtype=None,
            exp_value=9223372036854775808,
        ),
        None, None, True
    ),
    (
        "Numeric CIM-XML value: decimal string that exceeds Python 2 "
        "negative int limit and also CIM sint64 min value (no TYPE)",
        dict(
            data='-9223372036854775809',
            cimtype=None,
            exp_value=-9223372036854775809,
        ),
        None, None, True
    ),
    (
        "Numeric CIM-XML value: decimal string that exceeds Python 2 "
        "positive int limit and also CIM uint64 max value (no TYPE)",
        dict(
            data='18446744073709551616',
            cimtype=None,
            exp_value=18446744073709551616,
        ),
        None, None, True
    ),
    (
        "Numeric CIM-XML value: hex string 0xA0 (no TYPE)",
        dict(
            data='0xA0',
            cimtype=None,
            exp_value=160,
        ),
        None, None, True
    ),
    (
        "Numeric CIM-XML value: hex string 0Xa0 (no TYPE)",
        dict(
            data='0Xa0',
            cimtype=None,
            exp_value=160,
        ),
        None, None, True
    ),
    (
        "Numeric CIM-XML value: hex string -0xA0 (no TYPE)",
        dict(
            data='-0xA0',
            cimtype=None,
            exp_value=-160,
        ),
        None, None, True
    ),
    (
        "Numeric CIM-XML value: hex string +0xA0 (no TYPE)",
        dict(
            data='+0xA0',
            cimtype=None,
            exp_value=160,
        ),
        None, None, True
    ),
    (
        "Numeric CIM-XML value: hex string that exceeds Python 2 "
        "positive int limit but not CIM uint64 max value (no TYPE)",
        dict(
            data='0x8000000000000000',
            cimtype=None,
            exp_value=9223372036854775808,
        ),
        None, None, True
    ),
    (
        "Numeric CIM-XML value: hex string that exceeds Python 2 "
        "negative int limit and also CIM sint64 min value (no TYPE)",
        dict(
            data='-0x8000000000000001',
            cimtype=None,
            exp_value=-9223372036854775809,
        ),
        None, None, True
    ),
    (
        "Numeric CIM-XML value: hex string that exceeds Python 2 "
        "positive int limit and also CIM uint64 max value (no TYPE)",
        dict(
            data='0x10000000000000000',
            cimtype=None,
            exp_value=18446744073709551616,
        ),
        None, None, True
    ),
    (
        "Numeric CIM-XML value: float string 42.0 (no TYPE)",
        dict(
            data='42.0',
            cimtype=None,
            exp_value=42.0,
        ),
        None, None, True
    ),
    (
        "Numeric CIM-XML value: float string .0 (no TYPE)",
        dict(
            data='.0',
            cimtype=None,
            exp_value=0.0,
        ),
        None, None, True
    ),
    (
        "Numeric CIM-XML value: float string -.1e-12 (no TYPE)",
        dict(
            data='-.1e-12',
            cimtype=None,
            exp_value=-0.1E-12,
        ),
        None, None, True
    ),
    (
        "Numeric CIM-XML value: float string .1E12 (no TYPE)",
        dict(
            data='.1e12',
            cimtype=None,
            exp_value=0.1E+12,
        ),
        None, None, True
    ),
    (
        "Numeric CIM-XML value: float string +.1e+12 (no TYPE)",
        dict(
            data='.1e12',
            cimtype=None,
            exp_value=0.1E+12,
        ),
        None, None, True
    ),
    (
        "Numeric CIM-XML value: numeric value with invalid decimal digits "
        "(TYPE uint32)",
        dict(
            data='9a',
            cimtype='uint32',
            exp_value=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "Numeric CIM-XML value: numeric value that exceeds the data type "
        "limit (TYPE uint8)",
        dict(
            data='1234',
            cimtype='uint8',
            exp_value=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "Numeric CIM-XML value: None (TYPE uint8)",
        dict(
            data=None,
            cimtype='uint8',
            exp_value=None,
        ),
        None, None, True
    ),
    (
        "Numeric CIM-XML value: empty string (TYPE uint8)",
        dict(
            data='',
            cimtype='uint8',
            exp_value=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "Numeric CIM-XML value: WS string (TYPE sint64)",
        dict(
            data='  ',
            cimtype='sint64',
            exp_value=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "Numeric CIM-XML value: ASCII string (TYPE real32)",
        dict(
            data='abc',
            cimtype='real32',
            exp_value=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "Numeric CIM-XML value: decimal string 0 (TYPE uint8)",
        dict(
            data='0',
            cimtype='uint8',
            exp_value=Uint8(0),
        ),
        None, None, True
    ),
    (
        "Numeric CIM-XML value: decimal string 42 (TYPE uint16)",
        dict(
            data='42',
            cimtype='uint16',
            exp_value=Uint16(42),
        ),
        None, None, True
    ),
    (
        "Numeric CIM-XML value: decimal string -42 (TYPE sint16)",
        dict(
            data='-42',
            cimtype='sint16',
            exp_value=Sint16(-42),
        ),
        None, None, True
    ),
    (
        "Numeric CIM-XML value: decimal max neg. (TYPE uint8)",
        dict(
            data='0',
            cimtype='uint8',
            exp_value=Uint8(0),
        ),
        None, None, True
    ),
    (
        "Numeric CIM-XML value: decimal max pos. (TYPE uint8)",
        dict(
            data='255',
            cimtype='uint8',
            exp_value=Uint8(255),
        ),
        None, None, True
    ),
    (
        "Numeric CIM-XML value: decimal max neg. (TYPE uint16)",
        dict(
            data='0',
            cimtype='uint16',
            exp_value=Uint16(0),
        ),
        None, None, True
    ),
    (
        "Numeric CIM-XML value: decimal max pos. (TYPE uint16)",
        dict(
            data='65535',
            cimtype='uint16',
            exp_value=Uint16(65535),
        ),
        None, None, True
    ),
    (
        "Numeric CIM-XML value: decimal max neg. (TYPE uint32)",
        dict(
            data='0',
            cimtype='uint32',
            exp_value=Uint32(0),
        ),
        None, None, True
    ),
    (
        "Numeric CIM-XML value: decimal max pos. (TYPE uint32)",
        dict(
            data='4294967295',
            cimtype='uint32',
            exp_value=Uint32(4294967295),
        ),
        None, None, True
    ),
    (
        "Numeric CIM-XML value: decimal max neg. (TYPE uint64)",
        dict(
            data='0',
            cimtype='uint64',
            exp_value=Uint64(0),
        ),
        None, None, True
    ),
    (
        "Numeric CIM-XML value: decimal max positive that exceeds Python 2 "
        "positive int limit but not CIM uint64 max value (TYPE uint64)",
        dict(
            data='18446744073709551615',
            cimtype='uint64',
            exp_value=Uint64(18446744073709551615),
        ),
        None, None, True
    ),
    (
        "Numeric CIM-XML value: decimal max neg. (TYPE sint8)",
        dict(
            data='-128',
            cimtype='sint8',
            exp_value=Sint8(-128),
        ),
        None, None, True
    ),
    (
        "Numeric CIM-XML value: decimal max pos. (TYPE sint8)",
        dict(
            data='127',
            cimtype='sint8',
            exp_value=Sint8(127),
        ),
        None, None, True
    ),
    (
        "Numeric CIM-XML value: decimal max neg. (TYPE sint16)",
        dict(
            data='-32768',
            cimtype='sint16',
            exp_value=Sint16(-32768),
        ),
        None, None, True
    ),
    (
        "Numeric CIM-XML value: decimal max pos. (TYPE sint16)",
        dict(
            data='32767',
            cimtype='sint16',
            exp_value=Sint16(32767),
        ),
        None, None, True
    ),
    (
        "Numeric CIM-XML value: decimal max neg. (TYPE sint32)",
        dict(
            data='-2147483648',
            cimtype='sint32',
            exp_value=Sint32(-2147483648),
        ),
        None, None, True
    ),
    (
        "Numeric CIM-XML value: decimal max pos. (TYPE sint32)",
        dict(
            data='2147483647',
            cimtype='sint32',
            exp_value=Sint32(2147483647),
        ),
        None, None, True
    ),
    (
        "Numeric CIM-XML value: decimal max neg. that exceeds Python 2 "
        "negative int limit but not CIM sint64 negative min value "
        "(TYPE sint64)",
        dict(
            data='-9223372036854775808',
            cimtype='sint64',
            exp_value=Sint64(-9223372036854775808),
        ),
        None, None, True
    ),
    (
        "Numeric CIM-XML value: decimal max pos. that exceeds Python 2 "
        "positive int limit but not CIM sint64 positive max value "
        "(TYPE sint64)",
        dict(
            data='9223372036854775807',
            cimtype='sint64',
            exp_value=Sint64(9223372036854775807),
        ),
        None, None, True
    ),
    (
        "Numeric CIM-XML value: decimal max neg. that exceeds Python 2 "
        "negative int limit and also CIM sint64 negative min value "
        "(TYPE sint64)",
        dict(
            data='-9223372036854775809',
            cimtype='sint64',
            exp_value=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "Numeric CIM-XML value: hex string 0xA0 (TYPE uint32)",
        dict(
            data='0xA0',
            cimtype='uint32',
            exp_value=Uint32(160),
        ),
        None, None, True
    ),
    (
        "Numeric CIM-XML value: hex string 0Xa0 (TYPE uint32)",
        dict(
            data='0Xa0',
            cimtype='uint32',
            exp_value=Uint32(160),
        ),
        None, None, True
    ),
    (
        "Numeric CIM-XML value: hex string -0xA0 (TYPE sint32)",
        dict(
            data='-0xA0',
            cimtype='sint32',
            exp_value=Sint32(-160),
        ),
        None, None, True
    ),
    (
        "Numeric CIM-XML value: hex string +0xA0 (TYPE uint32)",
        dict(
            data='+0xA0',
            cimtype='uint32',
            exp_value=Uint32(160),
        ),
        None, None, True
    ),
    (
        "Numeric CIM-XML value: hex string that exceeds Python 2 "
        "positive int limit but not CIM sint64 positive max value "
        "(TYPE uint64)",
        dict(
            data='0x8000000000000000',
            cimtype='uint64',
            exp_value=Uint64(9223372036854775808),
        ),
        None, None, True
    ),
    (
        "Numeric CIM-XML value: hex string that exceeds Python 2 "
        "negative int limit and also CIM sint64 negative min value "
        "(TYPE sint64)",
        dict(
            data='-0x8000000000000001',
            cimtype='sint64',
            exp_value=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "Numeric CIM-XML value: float str 42.0 (TYPE real32)",
        dict(
            data='42.0',
            cimtype='real32',
            exp_value=Real32(42.0),
        ),
        None, None, True
    ),
    (
        "Numeric CIM-XML value: float str .0 (TYPE real64)",
        dict(
            data='.0',
            cimtype='real64',
            exp_value=Real64(0.0),
        ),
        None, None, True
    ),
    (
        "Numeric CIM-XML value: float str -.1e-12 (TYPE real32)",
        dict(
            data='-.1e-12',
            cimtype='real32',
            exp_value=Real32(-0.1E-12),
        ),
        None, None, True
    ),
    (
        "Numeric CIM-XML value: float str .1E12 (TYPE real32)",
        dict(
            data='.1e12',
            cimtype='real32',
            exp_value=Real32(0.1E+12),
        ),
        None, None, True
    ),
    (
        "Numeric CIM-XML value: float str +.1e+12 (TYPE real32)",
        dict(
            data='.1e12',
            cimtype='real32',
            exp_value=Real32(0.1E+12),
        ),
        None, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_UNPACK_NUMERIC)
@simplified_test_function
def test_unpack_numeric(testcase, data, cimtype, exp_value):
    """
    Test CIMXMLParser.unpack_numeric().
    """

    parser = CIMXMLParser('')

    # Code to be tested
    value = parser.unpack_numeric(data, cimtype)

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None, \
        "Expected exception {!r} has not been raised".\
        format(testcase.exp_exc_types)

    assert value == exp_value


TESTCASES_UNPACK_DATETIME = [
    (
        "Datetime CIM-XML value: None",
        dict(
            data=None,
            exp_value=None,
        ),
        None, None, True
    ),
    (
        "Datetime CIM-XML value: empty string",
        dict(
            data='',
            exp_value=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "Datetime CIM-XML value: WS char",
        dict(
            data=' ',
            exp_value=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "Datetime CIM-XML value: Binary ASCII char",
        dict(
            data=b'a',
            exp_value=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "Datetime CIM-XML value: Unicode ASCII char",
        dict(
            data=u'a',
            exp_value=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "Datetime CIM-XML value: decimal as string",
        dict(
            data='4',
            exp_value=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "Datetime CIM-XML value: valid point in time value",
        dict(
            data='20140924193040.654321+120',
            exp_value=CIMDateTime('20140924193040.654321+120'),
        ),
        None, None, True
    ),
    (
        "Datetime CIM-XML value: valid interval value",
        dict(
            data='00000183132542.234567:000',
            exp_value=CIMDateTime('00000183132542.234567:000'),
        ),
        None, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_UNPACK_DATETIME)
@simplified_test_function
def test_unpack_datetime(testcase, data, exp_value):
    """
    Test CIMXMLParser.unpack_datetime().
    """

    parser = CIMXMLParser('')

    # Code to be tested
    value = parser.unpack_datetime(data)

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None, \
        "Expected exception {!r} has not been raised".\
        format(testcase.exp_exc_types)

    assert value == exp_value


TESTCASES_UNPACK_CHAR16 = [
    (
        "char16 CIM-XML value: None",
        dict(
            data=None,
            exp_value=None,
        ),
        None, None, True
    ),
    (
        "char16 CIM-XML value: no character (empty)",
        dict(
            data='',
            exp_value=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "char16 CIM-XML value: two characters",
        dict(
            data='ab',
            exp_value=None,
        ),
        CIMXMLParseError, None, True
    ),
    (
        "char16 CIM-XML value: Space character",
        dict(
            data=' ',
            exp_value=u' ',
        ),
        None, None, True
    ),
    (
        "char16 CIM-XML value: Binary ASCII letter",
        dict(
            data=b'a',
            exp_value=u'a',
        ),
        None, None, True
    ),
    (
        "char16 CIM-XML value: Unicode ASCII letter",
        dict(
            data=u'a',
            exp_value=u'a',
        ),
        None, None, True
    ),
    (
        "char16 CIM-XML value: An ASCII digit",
        dict(
            data='4',
            exp_value=u'4',
        ),
        None, None, True
    ),
    (
        "char16 CIM-XML value: A binary non-ASCII UCS-2 character",
        dict(
            # U+00E9: LATIN SMALL LETTER E WITH ACUTE
            data=b'\xC3\xA9',
            exp_value=u'\u00E9',
        ),
        None, None, True
    ),
    (
        "char16 CIM-XML value: A binary non-UCS-2 character",
        dict(
            # U+010142: GREEK ACROPHONIC ATTIC ONE DRACHMA
            data=b'\xF0\x90\x85\x82',
            exp_value=None,
        ),
        CIMXMLParseError, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_UNPACK_CHAR16)
@simplified_test_function
def test_unpack_char16(testcase, data, exp_value):
    """
    Test CIMXMLParser.unpack_char16().
    """

    parser = CIMXMLParser('')

    # Code to be tested
    value = parser.unpack_char16(data)

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None, \
        "Expected exception {!r} has not been raised".\
        format(testcase.exp_exc_types)

    assert value == exp_value


TESTCASES_UNPACK_STRING = [
    (
        "String CIM-XML value: None",
        dict(
            data=None,
            exp_value=None,
        ),
        None, None, True
    ),
    (
        "String CIM-XML value: Empty string",
        dict(
            data='',
            exp_value=u'',
        ),
        None, None, True
    ),
    (
        "String CIM-XML value: Space character",
        dict(
            data=' ',
            exp_value=u' ',
        ),
        None, None, True
    ),
    (
        "String CIM-XML value: Space delimited ASCII letter",
        dict(
            data=' a ',
            exp_value=u' a ',
        ),
        None, None, True
    ),
    (
        "String CIM-XML value: Whitespace characters",
        dict(
            data='  \n  \t  \r  ',
            exp_value=u'  \n  \t  \r  ',
        ),
        None, None, True
    ),
    (
        "String CIM-XML value: Binary ASCII letter",
        dict(
            data=b'a',
            exp_value=u'a',
        ),
        None, None, True
    ),
    (
        "String CIM-XML value: Unicode ASCII letter",
        dict(
            data=u'a',
            exp_value=u'a',
        ),
        None, None, True
    ),
    (
        "String CIM-XML value: An ASCII digit",
        dict(
            data='4',
            exp_value=u'4',
        ),
        None, None, True
    ),
    (
        "String CIM-XML value: A binary non-ASCII UCS-2 character",
        dict(
            # U+00E9: LATIN SMALL LETTER E WITH ACUTE
            data=b'\xC3\xA9',
            exp_value=u'\u00E9',
        ),
        None, None, True
    ),
    (
        "String CIM-XML value: A binary non-UCS-2 character",
        dict(
            # U+010142: GREEK ACROPHONIC ATTIC ONE DRACHMA
            data=b'\xF0\x90\x85\x82',
            exp_value=u'\U00010142',
        ),
        None, None, True
    ),
]


@pytest.mark.parametrize(
    "desc, kwargs, exp_exc_types, exp_warn_types, condition",
    TESTCASES_UNPACK_STRING)
@simplified_test_function
def test_unpack_string(testcase, data, exp_value):
    """
    Test CIMXMLParser.unpack_string().
    """

    parser = CIMXMLParser('')

    # Code to be tested
    value = parser.unpack_string(data)

    # Ensure that exceptions raised in the remainder of this function
    # are not mistaken as expected exceptions
    assert testcase.exp_exc_types is None, \
        "Expected exception {!r} has not been raised".\
        format(testcase.exp_exc_types)

    assert value == exp_value


# TODO: Add tests for listener support: parse_cimxml_indication_request()
# TODO: Add tests for listener support: required_SIMPLEEXPREQ_element()
# TODO: Add tests for listener support: required_EXPMETHODCALL_element()
# TODO: Add tests for listener support: required_EXPPARAMVALUE_element()
