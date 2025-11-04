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

# pylint: disable=too-many-lines

"""
Parser for CIM-XML received by the pywbem client or listener.

This parser is used in two situations:

- For parsing the CIM-XML string of a WBEM operation response that is received
  by the pywbem client

- For parsing the CIM-XML string of a WBEM indication request (i.e. indication
  delivery request) that is received by the pywbem listener

This parser uses the event-based parsing approach (iterparse) of the
Python ElementTree module to parse the CIM-XML string incrementally and
directly into the CIM objects that represent the operation response or
indication request. This avoids any intermediate representations such as an
XML representation in any format (including the tupletree format that was
used in earlier versions of pywbem). The idea for the event-based parsing
approach was taken from the OpenPegasus client.
"""

from __future__ import absolute_import
import re
import io
import warnings
from xml.dom import pulldom

import six

from .cim_obj import CIMInstance, CIMInstanceName, CIMClass, CIMClassName
from .cim_obj import CIMProperty, CIMMethod, CIMParameter, CIMQualifier
from .cim_obj import CIMQualifierDeclaration
from .cim_types import CIMDateTime, type_from_name
from .exceptions import CIMXMLParseError, XMLParseError, CIMError
from ._warnings import ToleratedServerIssueWarning
from ._utils import _stacklevel_above_module, _format


# This module is meant to be safe for 'import *'.
__all__ = []


CIMXML_HEX_PATTERN = re.compile(r'^(\+|\-)?0[xX][0-9a-fA-F]+$')
NUMERIC_CIMTYPE_PATTERN = re.compile(r'^([su]int(8|16|32|64)|real(32|64))$')
IGNORED_CONTENT_WS = ' \t\n\r'


class XmlEvent(object):
    """
    Represents an XML parsing event while parsing an XML data stream.

    These events are roughly oriented along the lines of the event-based
    parsing approach supported by `ElementTree.iterparse()`.

    The XML parsing events can be of these types:

    - Start element event: This event is triggered when an XML start element
      (e.g. <VALUE>) is encountered in the XML data stream. Its data includes
      the element name and its XML attributes. The text content may or may
      not be present in the event surfaced by `ElementTree.iterparse()`, but it
      is not guaranteed to be present, and therefore the text content is not
      set in the objects of this class when representing a start element event.

    - End element event: This event is triggered when an XML end element
      (e.g. </VALUE>) is encountered in the XML data stream. Its data includes
      the element name, its XML attributes, and the content text.

    Note that the content text included in objects of this class is only the
    text after the start element and before the next following element (be it a
    start or end element). The text after an end element and before the next
    following element is termed "trailing text" and is not included in objects
    of this class, because in CIM-XML, non-whitespace trailing text is always
    illegal.

    Note that the self-closing syntax form of elements (e.g. '<ELEM/>' or
    '<ELEM ATTR="value"/>') results in two distinct XML parsing events, as if
    the element had been coded in the syntax form with separate start and end
    element (e.g. '<ELEM></ELEM>' or '<ELEM ATTR="value"></ELEM>').

    Note that this parsing approach does not surface any of:
      - Document type definitions: <!DOCTYPE ...>
      - XML declarations: <?xml ... ?>
      - XML comments: <!-- ... -->
    """

    def __init__(self, event, name, attributes=None, content=None,
                 conn_id=None):

        # XML event type:
        # - pulldom.START_ELEMENT:  Start element event
        # - pulldom.END_ELEMENT:  End element event
        self.event = event

        # Element name.
        self.name = name

        # Dict of attributes
        # (key: attribute name, value: attribute value as a string).
        self.attributes = dict()
        if attributes is not None:
            self.attributes.update(attributes)

        # Content text (without any trailing text).
        # None means there is no content yet (e.g. on start event).
        # Empty element content is representes as an empty string.
        self.content = content

        # Connection ID, used in exceptions.
        self.conn_id = conn_id

    def __repr__(self):
        repr_str = "XmlEvent(event={s.event!r}".format(s=self)
        repr_str += ", name={s.name!r}".format(s=self)
        if self.attributes is not None:
            repr_str += ", attributes={s.attributes!r}".format(s=self)
        if self.content is not None:
            repr_str += ", content={s.content!r}".format(s=self)
        if self.conn_id is not None:
            repr_str += ", conn_id={s.conn_id!r}".format(s=self)
        repr_str += ")"
        return repr_str

    def __eq__(self, other):
        return self.event == other.event and \
            self.name == other.name and \
            self.attributes == other.attributes and \
            self.content == other.content and \
            self.conn_id == other.conn_id

    def __ne__(self, other):
        return not (self == other)

    def required_attribute(self, name):
        """
        Return the value of the XML attribute with the specified name.

        The XML attribute is required to be present. If not present,
        CIMXMLParseError is raised.

        Parameters:

            name (string): XML attribute name.

        Returns:
            Unicode string: The value of the specified XML attribute.

        Raises:
            CIMXMLParseError: XmlEvent does not have the specified attribute.
        """
        try:
            return self.attributes[name]
        except KeyError:
            raise CIMXMLParseError(
                _format("{0!A} element does not have the required {1!A} "
                        "attribute",
                        self.name, name),
                self.conn_id)

    def optional_attribute(self, name, default=None):
        """
        Return the value of the XML attribute with the specified name.

        The XML attribute is optional, and the default value is returned when
        it is not present.

        Parameters:

            name (string): XML attribute name.

            default (string): Default value to be returned.

        Returns:
            Unicode string: The value of the specified XML attribute.
        """
        return self.attributes.get(name, default)


class CIMXMLParser(object):
    """
    Parser for a CIM-XML representation of a CIM-XML message.

    Because this parser is used on the client side, only the following two
    kinds of CIM-XML messages are supported:

    - Response of a WBEM operation that is received by the pywbem client.

    - Request of a WBEM indication (i.e. the indication delivery) that is
      received by the pywbem listener.

    Limitations:

    - Multi-responses are not supported.

    Naming rules for methods of this class:

    - prefix 'required_' is used for methods that consume an event if present,
      and raise a CIMXMLParseError otherwise. In other words, the event is
      required.

    - prefix 'optional_' is used for methods that consume an event if present,
      and put back any consumed events otherwise. In other words, the event is
      optional.

    - prefix 'list_of_' is used for methods that consume a (possibly empty)
      list of elements.

    - suffix '_start_element' is used when the event is for a start element.

    - suffix '_end_element' is used when the event is for an end element.

    - suffix '_element' (or '_elements') is used when the processed events are
      for an entire element (or list of elements) from start to end, including
      any children.
    """

    def __init__(self, xml_string, conn_id=None):
        """
        xml_string (str): A unicode string (when called for embedded
          objects) or UTF-8 encoded byte string (when called for CIM-XML
          replies) containing the CIM-XML string to be parsed.

        conn_id (:term:`connection id`): Connection ID to be used in any
          exceptions that may be raised.
        """

        self.conn_id = conn_id

        if isinstance(xml_string, six.text_type):
            xml_string = xml_string.encode('utf-8')
        self.doc = pulldom.parseString(xml_string)

        # Current XML event:
        self.event = None  # Type of XML event ('start' or 'end')
        self.element = None  # XML element as an Element object

        # Put back stack for XML events.
        # The items on teh stack are: tuple (event, element).
        # append() puts an event onto the stack.
        # pop() gets an event from the stack.
        self.put_stack = list()

    # Low level support methods for interfacing with event-driven XML parser

    def get_next_event(self):
        """
        Get the next XML event and make it the current XML event in this
        object.

        Raises:
            CIMXMLParseError: Premature end of XML document
            XMLParseError: XML parsing error
        """
        if self.put_stack:
            self.event, self.element = self.put_stack.pop()
        else:
            try:
                self.event, self.element = next(self.doc)
            except StopIteration:
                raise CIMXMLParseError(
                    _format("Encountered premature end of XML document "
                            "after {0!A} {1} element",
                            self.element.tagName, self.event),
                    self.conn_id)
            except ET.ParseError as exc:
                raise XMLParseError(str(exc), self.conn_id)

    def put_back_event(self):
        """
        Put the current XML event in this object onto the put-back stack, and
        empty the current XML event in this object.

        Note that only one XML event can be put back, and a get next is needed
        before another put back can be done.

        Raises:
            ValueError: No current XML event present for put-back
        """
        if self.event is None:
            raise ValueError("No current XML event present for put-back")
        self.put_stack.append((self.event, self.element))
        self.event = None
        self.element = None

    # Generic support methods

    def required_start_element(self, names):
        """
        Process a required start element with one of the specified names.

        Parameters:

            names (string or list/tuple of strings): Name or possible names of
              the element.

        Returns:
            XmlEvent: The expected start element with attributes (but no
              content).
        """
        self.get_next_event()
        if not isinstance(names, (tuple, list)):
            names = (names,)
        if self.event != pulldom.START_ELEMENT or \
                self.element.tagName not in names:
            names_str = names[0] if len(names) == 1 else str(names)
            raise CIMXMLParseError(
                _format("Expected {0!A} start element, got {1!A} {2} element",
                        names_str, self.element.tagName, self.event),
                self.conn_id)
        xml_event = XmlEvent(self.event, self.element.tagName,
                             attributes=self.element._get_attributes(),
                             conn_id=self.conn_id)
        return xml_event

    def optional_start_element(self, names):
        """
        Process an optional start element with one of the specified names.

        If the next XML event is the specified start element, return the
        XML event.
        Otherwise, put back the XML event and return None.

        Parameters:

            names (string or list/tuple of strings): Name or possible names of
              the element.

        Returns:
            XmlEvent: The start element with attributes (but no content),
              if it matches one of the names. Otherwise, None.
        """
        self.get_next_event()
        if not isinstance(names, (tuple, list)):
            names = (names,)
        if self.event == pulldom.START_ELEMENT and self.element.tagName in names:
            xml_event = XmlEvent(self.event, self.element.tagName,
                                 attributes=self.element._get_attributes(),
                                 conn_id=self.conn_id)
            return xml_event
        self.put_back_event()
        return None

    def peek_next_element(self):
        """
        Peek at the next element, without consuming it.

        Returns:
            XmlEvent: The next element with attributes (but no content).
        """
        self.get_next_event()
        xml_event = XmlEvent(self.event, self.element.tagName,
                             attributes=self.element._get_attributes(),
                             conn_id=self.conn_id)
        self.put_back_event()
        return xml_event

    def test_start_element(self, name=None):
        """
        Test whether the next element is a start element with the specified
        name, or with any name, without consuming the element.

        Parameters:

            name (string): Name of the element. If None, then the start element
              can have any name.

        Returns:
            bool: Indicates whether the next element is a start element with
              the specified name (or any name).
        """
        xml_event = self.peek_next_element()
        return xml_event.event == 'start' and \
            (name is None or xml_event.name == name)

    def expect_no_start_element(self, name=None):
        """
        Expect no further start element with the specified name, or with any
        name. There is no element consumed.

        Parameters:

            name (string): Name of the element. If None, then the start element
              can have any name.
        """
        xml_event = self.peek_next_element()
        if xml_event.event == 'start' and \
                (name is None or xml_event.name == name):
            if name is None:
                name_txt = "any name"
            else:
                name_txt = _format("name {0!A}", name)
            raise CIMXMLParseError(
                _format("Expected no further start element with {0}, "
                        "got {1!A} start element",
                        name_txt, xml_event.name),
                self.conn_id)

    def fail_invalid_or_missing_child(self, name):
        """
        Fail due to invalid or missing child element(s).

        This method can be used as the last choice after testing a number of
        allowable required child elements.

        If the next element is a start element, it is an invalid child (because
        the valid children have already been tested by the caller), and an
        according exception is raised.

        If the next element is an end element, the required child or children
        are missing (because the valid children have already been tested by the
        caller), and an according exception is raised.

        Parameters:

            name (string): Parent element name (just for use in exceptions).
        """
        xml_event = self.peek_next_element()
        if xml_event.event == 'start':
            raise CIMXMLParseError(
                _format("{0!A} element has an invalid child element {1!A}",
                        name, xml_event.name),
                self.conn_id)
        else:
            assert xml_event.event == 'end'
            raise CIMXMLParseError(
                _format("{0!A} element does not have its required child "
                        "elements", name),
                self.conn_id)

    def required_end_element(self, name, allow_content=False):
        """
        Consume the next element and require that it is an end element with the
        specified name.

        Parameters:

            name (string): Element name.

            allow_content (bool): Controls whether text content (besides
              whitespace) is allowed in the element.

        Returns:
            XmlEvent: The expected end element with attributes of its start
              element, and with any content.
              In the content, an empty text content is represented as the empty
              unicode string.
        """
        self.get_next_event()
        if self.event != pulldom.END_ELEMENT or self.element.tagName != name:
            raise CIMXMLParseError(
                _format("Invalid child element {0!A} within {1!A} element",
                        self.element.tagName, name),
                self.conn_id)

        # Empty text content (e.g. <VALUE></VALUE>) is surfaced as
        # element.text=None. Therefore, we convert it back to an empty string:
        content = self.element.text or u''

        if not allow_content and content.strip(IGNORED_CONTENT_WS):
            raise CIMXMLParseError(
                _format("{0!A} element has non-whitespace text content: {1!r}",
                        name, content),
                self.conn_id)

        tail = self.element.tail
        if tail and tail.strip(IGNORED_CONTENT_WS):
            raise CIMXMLParseError(
                _format("{0!A} element has non-whitespace text tail (after "
                        "its end element): {1!r}",
                        name, tail),
                self.conn_id)

        xml_event = XmlEvent(self.event, self.element.tagName,
                             attributes=self.element._get_attributes(),
                             content=content, conn_id=self.conn_id)
        self.clear_element()
        return xml_event

    def expect_end(self):
        """
        Expect the end of the XML document.
        """
        if self.put_stack:
            self.event, self.element = self.put_stack.pop()
        else:
            try:
                self.event, self.element = next(self.elem_iter)
            except StopIteration:
                return
        raise CIMXMLParseError(
            _format("Invalid extra {0!A} element after end of expected "
                    "CIM-XML string",
                    self.element.tagName),
            self.conn_id)

    # Top level parse methods

    def parse_cimxml_operation_response(self, operation_name):
        """
        Parse the CIM-XML response of a WBEM server for an operation
        invocation and return the return value and output parameters of the
        operation invocation.

        Parameters:

            operation_name (string): Expected operation name.

        Limitations:

        - Multi responses are not supported by this parser and result in a
          CIMXMLParseError.

        Returns:
            tuple (ret_value, out_params), with:
              * ret_value: CIM typed operation return value (None for void)
              * out_params: dict of operation output parameters, with:
                  * key: parameter name
                  * value: CIM typed parameter value

        Raises:
            pywbem.CIMXMLParseError: CIM-XML level parsing error in the
              response.
            pywbem.XMLParseError: XML-level parsing error in the response.
        """
        self.required_CIM_start_element()
        self.required_MESSAGE_start_element()
        self.required_SIMPLERSP_start_element()
        self.required_IMETHODRESPONSE_start_element(operation_name)
        error = self.optional_ERROR_element()
        if not error:
            ret_value = self.optional_IRETURNVALUE_element(operation_name)
            out_params = self.list_of_operation_PARAMVALUE_elements(
                operation_name)
        self.required_end_element('IMETHODRESPONSE')
        self.required_end_element('SIMPLERSP')
        self.required_end_element('MESSAGE')
        self.required_end_element('CIM')
        self.expect_end()
        if error:
            code, description, instances = error
            raise CIMError(code, description, instances)
        return ret_value, out_params

    def parse_cimxml_method_response(self, method_name):
        """
        Parse the CIM-XML response of a WBEM server for an extrinsic method
        invocation and return the return value and output parameters of the
        method invocation.

        Parameters:

            method_name (string): Expected method name.

        Limitations:

        - Multi responses are not supported by this parser and result in a
          CIMXMLParseError.

        Returns:
            tuple (ret_value, out_params), with:
              * ret_value: CIM typed method return value (None for void)
              * out_params: dict of method output parameters, with:
                  * key: parameter name
                  * value: CIM typed parameter value

        Raises:
            pywbem.CIMXMLParseError: CIM-XML level parsing error in the
              response.
            pywbem.XMLParseError: XML-level parsing error in the response.
        """
        self.required_CIM_start_element()
        self.required_MESSAGE_start_element()
        self.required_SIMPLERSP_start_element()
        self.required_METHODRESPONSE_start_element(method_name)
        error = self.optional_ERROR_element()
        if not error:
            ret_value = self.optional_RETURNVALUE_element()
            out_params = self.list_of_method_PARAMVALUE_elements()
        self.required_end_element('METHODRESPONSE')
        self.required_end_element('SIMPLERSP')
        self.required_end_element('MESSAGE')
        self.required_end_element('CIM')
        self.expect_end()
        if error:
            code, description, instances = error
            raise CIMError(code, description, instances)
        return ret_value, out_params

    # TODO: Implement listener support: parse_cimxml_indication_request()
    # TODO: Implement listener support: required_SIMPLEEXPREQ_element()
    # TODO: Implement listener support: required_EXPMETHODCALL_element()
    # TODO: Implement listener support: required_EXPPARAMVALUE_element()

    # Message-related protocol elements

    def required_CIM_start_element(self):
        """
        Process a required CIM start element.

        Verify that the CIM version and DTD version are as expected.

        DTD::

            <!ELEMENT CIM (MESSAGE|DECLARATION)>
            <!ATTRLIST CIM
                CIMVERSION CDATA #REQUIRED
                DTDVERSION CDATA #REQUIRED>

        Returns:
            tuple (cim_version, dtd_version)
        """
        xml_event = self.required_start_element('CIM')
        cim_version = xml_event.required_attribute('CIMVERSION')
        self.verify_cim_version(cim_version)
        dtd_version = xml_event.required_attribute('DTDVERSION')
        self.verify_dtd_version(dtd_version)
        return cim_version, dtd_version

    def verify_cim_version(self, cim_version):
        """
        Verify the CIM schema version.

        The client is not sensitive to the CIM schema version, so it is ignored.
        """
        pass

    def verify_dtd_version(self, dtd_version):
        """
        Verify the DTD version (=DSP0201 version).

        This is done by checking whether the major version is supported.
        """
        dtd_major_version = dtd_version.split('.')[0]
        if dtd_major_version != '2':
            raise CIMXMLParseError(
                _format("Unsupported CIM-XML DTD version (DSP0201): {0} "
                        "(supported is 2.x)",
                        dtd_version),
                self.conn_id)

    def required_MESSAGE_start_element(self):
        """
        Process a required MESSAGE start element.

        Verify that the protocol version is as expected.

        DTD::

            <!ELEMENT MESSAGE (SIMPLEREQ | MULTIREQ | SIMPLERSP | MULTIRSP |
                               SIMPLEEXPREQ | MULTIEXPREQ | SIMPLEEXPRSP |
                               MULTIEXPRSP)>
            <!ATTLIST MESSAGE
                ID CDATA #REQUIRED
                PROTOCOLVERSION CDATA #REQUIRED>

        Returns:
            tuple (id, protocol_version)
        """
        xml_event = self.required_start_element('MESSAGE')
        id_ = xml_event.required_attribute('ID')
        protocol_version = xml_event.required_attribute('PROTOCOLVERSION')
        self.verify_protocol_version(protocol_version)
        return id_, protocol_version

    def verify_protocol_version(self, protocol_version):
        """
        Verify the CIM-XML protocol version (=DSP0200 version).

        This is done by checking whether the major version is supported.
        """
        protocol_major_version = protocol_version.split('.')[0]
        if protocol_major_version != '1':
            raise CIMXMLParseError(
                _format("Unsupported CIM-XML protocol version (DSP0200): {0} "
                        "(supported is 1.x)",
                        protocol_version),
                self.conn_id)

    def required_SIMPLERSP_start_element(self):
        """
        Process a required SIMPLERSP start element.

        DTD::

            <!ELEMENT SIMPLERSP (METHODRESPONSE | IMETHODRESPONSE)>
        """
        self.required_start_element('SIMPLERSP')

    def required_IMETHODRESPONSE_start_element(self, operation_name):
        """
        Process a required IMETHODRESPONSE start element.

        Verify that the operation name is as expected.

        Parameters:

            operation_name (string): Operation name.

        DTD::

            <!ELEMENT IMETHODRESPONSE (ERROR | (IRETURNVALUE?, PARAMVALUE*))>
            <!ATTLIST IMETHODRESPONSE
                %CIMName;>
        """
        xml_event = self.required_start_element('IMETHODRESPONSE')
        actual_operation_name = xml_event.required_attribute('NAME')
        if actual_operation_name != operation_name:
            raise CIMXMLParseError(
                _format("'IMETHODRESPONSE' element has an invalid 'NAME' "
                        "attribute value: Expected {0!r}, got {1!r}",
                        operation_name, actual_operation_name),
                self.conn_id)

    def optional_IRETURNVALUE_element(self, operation_name):
        """
        Process an optional IRETURNVALUE element (from start to end
        including children).

        The specified operation name determines which child elements of
        IRETURNVALUE are valid.

        Parameters:

            operation_name (string): Operation name.

        DTD::

            <!ELEMENT IRETURNVALUE (CLASSNAME* | INSTANCENAME* | VALUE* |
                                    VALUE.OBJECTWITHPATH* |
                                    VALUE.OBJECTWITHLOCALPATH* |
                                    VALUE.OBJECT* | OBJECTPATH* |
                                    QUALIFIER.DECLARATION* | VALUE.ARRAY? |
                                    VALUE.REFERENCE? | CLASS* | INSTANCE* |
                                    INSTANCEPATH* | VALUE.NAMEDINSTANCE* |
                                    VALUE.INSTANCEWITHPATH*)>

        Returns:
            CIM typed value, if the next XML event was an IRETURNVALUE element.
            None, otherwise.
        """
        try:
            return_func = OPERATION_RETURN_FUNCS[operation_name]
            # If this succeeds, the operation has a non-void return value
        except KeyError:
            # Operation with no return value (=void)
            return_func = None

        if return_func:
            self.required_start_element('IRETURNVALUE')
            return_value = return_func(self)
            self.required_end_element('IRETURNVALUE')
        else:
            self.expect_no_start_element('IRETURNVALUE')
            return_value = None

        return return_value

    def list_of_operation_PARAMVALUE_elements(self, operation_name):
        """
        Process a (possibly empty) consecutive list of PARAMVALUE elements
        (from start to end including children), in context of an intrinsic
        operation.

        The specified operation name determines which child elements of
        PARAMVALUE are valid.

        Note that operation output parameters that need to be classes or
        instances are represented as CLASS and INSTANCE elements, and not
        as embedded classes or instances in VALUE elements. Therefore, the
        EmbeddedObject attribute is always invalid on PARAMVALUE elements
        that represent operation output parameters.

        Parameters:

            operation_name (string): Operation name.

        DTD::

            PARAMVALUE* (for operation output parameters)

            With:

            <!ELEMENT PARAMVALUE (VALUE | VALUE.REFERENCE | VALUE.ARRAY |
                                  VALUE.REFARRAY | CLASSNAME | INSTANCENAME |
                                  CLASS | INSTANCE | VALUE.NAMEDINSTANCE)?>
            <!ATTLIST PARAMVALUE
                %CIMName;
                %ParamType;  #IMPLIED
                %EmbeddedObject;>

        Returns:
            dict of operation output parameters, with:
              * key: parameter name
              * value: CIM typed parameter value
        """

        try:
            outparam_defs = OPERATION_OUTPARAM_DEFS[operation_name]
        except KeyError:
            outparam_defs = {}

        result = dict()

        while True:
            xml_event = self.optional_start_element('PARAMVALUE')
            if not xml_event:
                break

            name = xml_event.required_attribute('NAME')
            cimtype = xml_event.optional_attribute('PARAMTYPE', None)
            embedded_object = xml_event.optional_attribute(
                'EmbeddedObject',
                xml_event.optional_attribute('EMBEDDEDOBJECT', None))

            # Note: The approach is to know the output parameters and their
            # types, per operation. Unknown output parameters are rejected.

            try:
                outparam_def = outparam_defs[name]
            except KeyError:
                raise CIMXMLParseError(
                    _format("Invalid output parameter {0!A} for operation {1} "
                            "(expected is one of: {2})",
                            name, operation_name,
                            list(six.iterkeys(outparam_defs))),
                    self.conn_id)

            if cimtype and cimtype != outparam_def['cimtype']:
                raise CIMXMLParseError(
                    _format("Output parameter {0!A} of operation {1} has "
                            "invalid CIM type {2!A} (expected was {3!A})",
                            name, operation_name, cimtype,
                            outparam_def['cimtype']),
                    self.conn_id)

            if embedded_object:
                raise CIMXMLParseError(
                    _format("Output parameter {0!A} of operation {1} has "
                            "an invalid EmbeddedObject indicator {2!A}",
                            name, operation_name, embedded_object),
                    self.conn_id)

            child_element_func = outparam_def['child_element_func']
            value = child_element_func(self)

            result[name] = value

            self.required_end_element('PARAMVALUE')

        missing_params = list()
        for name, outparam_def in six.iteritems(outparam_defs):
            if outparam_def['required'] and name not in result:
                missing_params.append(name)
        if missing_params:
            raise CIMXMLParseError(
                _format("Missing required output parameters {0} of "
                        "operation {1}",
                        missing_params, operation_name),
                self.conn_id)

        return result

    def required_METHODRESPONSE_start_element(self, method_name):
        """
        Process a required METHODRESPONSE start element.

        Verify that the method name is as expected.

        Parameters:

            method_name (string): Name of the CIM method.

        DTD::

            <!ELEMENT METHODRESPONSE (ERROR | (RETURNVALUE?, PARAMVALUE*))>
            <!ATTLIST METHODRESPONSE
                %CIMName;>
        """
        xml_event = self.required_start_element('METHODRESPONSE')
        actual_method_name = xml_event.required_attribute('NAME')
        if actual_method_name != method_name:
            raise CIMXMLParseError(
                _format("{0!A} element has an invalid 'NAME' attribute value: "
                        "Expected {1!r}, got {2!r}",
                        xml_event.name, method_name, actual_method_name),
                self.conn_id)

    def optional_RETURNVALUE_element(self):
        """
        Process an optional RETURNVALUE element (from start to end
        including children).

        Verify that the child elements are correct for the specified operation.

        DTD::

            <!ELEMENT RETURNVALUE (VALUE | VALUE.REFERENCE)?>
            <!ATTLIST RETURNVALUE
                %EmbeddedObject;
                %ParamType;       #IMPLIED>

        Returns:
            CIM typed value, if it was a RETURNVALUE element.
            None, otherwise.
        """
        xml_event = self.optional_start_element('RETURNVALUE')
        if not xml_event:
            return None

        embedded_object = xml_event.optional_attribute(
            'EmbeddedObject',
            xml_event.optional_attribute('EMBEDDEDOBJECT', None))
        cimtype = xml_event.optional_attribute('PARAMTYPE', None)

        if self.test_start_element('VALUE'):
            value = self.required_VALUE_element(cimtype, embedded_object)
        elif self.test_start_element('VALUE.REFERENCE'):
            value = self.required_VALUE_REFERENCE_element()
        else:
            value = None

        self.required_end_element('RETURNVALUE')
        return value

    def list_of_method_PARAMVALUE_elements(self):
        """
        Process a (possibly empty) consecutive list of PARAMVALUE elements
        (from start to end including children), in context of an extrinsic
        method invocation.

        DTD::

            PARAMVALUE* (for method output parameters)

        Returns:
            dict of method output parameters, with:
              * key: parameter name
              * value: CIM typed parameter value
        """
        values = dict()
        while self.test_start_element('PARAMVALUE'):
            name, value = self.required_method_PARAMVALUE_element()
            values[name] = value
        return values

    def required_method_PARAMVALUE_element(self):
        """
        Process a required PARAMVALUE element
        (from start to end including children), in context of an extrinsic
        method invocation.

        DTD::

            <!ELEMENT PARAMVALUE (VALUE | VALUE.REFERENCE | VALUE.ARRAY |
                                  VALUE.REFARRAY | CLASSNAME | INSTANCENAME |
                                  CLASS | INSTANCE | VALUE.NAMEDINSTANCE)?>
            <!ATTLIST PARAMVALUE
                %CIMName;
                %ParamType;  #IMPLIED
                %EmbeddedObject;>


        Returns:
            tuple (name, value), with:
              * name (unicode string): Parameter name.
              * value: CIM typed value of the parameter.
        """
        xml_event = self.required_start_element('PARAMVALUE')

        name = xml_event.required_attribute('NAME')
        cimtype = xml_event.optional_attribute('PARAMTYPE', None)
        embedded_object = xml_event.optional_attribute(
            'EmbeddedObject',
            xml_event.optional_attribute('EMBEDDEDOBJECT', None))

        if self.test_start_element('VALUE'):
            value = self.required_VALUE_element(cimtype, embedded_object)
        elif self.test_start_element('VALUE.REFERENCE'):
            value = self.required_VALUE_REFERENCE_element()
        elif self.test_start_element('VALUE.ARRAY'):
            value = self.required_VALUE_ARRAY_element(cimtype, embedded_object)
        elif self.test_start_element('VALUE.REFARRAY'):
            value = self.required_VALUE_REFARRAY_element()
        elif self.test_start_element('CLASSNAME'):
            value = self.required_CLASSNAME_element()
        elif self.test_start_element('INSTANCENAME'):
            value = self.required_INSTANCENAME_element()
        elif self.test_start_element('CLASS'):
            value = self.required_CLASS_element()
        elif self.test_start_element('INSTANCE'):
            value = self.required_INSTANCE_element()
        elif self.test_start_element('VALUE.NAMEDINSTANCE'):
            value = self.required_VALUE_NAMEDINSTANCE_element()
        else:
            xml_event = self.peek_next_element()
            if xml_event.event == 'end':
                # No child element -> it represents NULL
                value = None
            else:
                assert xml_event.event == 'start'
                # Invalid child element
                self.fail_invalid_or_missing_child('PARAMVALUE')

        self.required_end_element('PARAMVALUE')
        return name, value

    def optional_ERROR_element(self):
        """
        Process an optional ERROR element (from start to end
        including children).

        DTD::

            <!ELEMENT ERROR (INSTANCE*)>
            <!ATTLIST ERROR
                CODE CDATA #REQUIRED
                DESCRIPTION CDATA #IMPLIED>

        Returns:
            tuple (code, description, instances), if an ERROR element was
              present, with:
                * code (int): CIM status code (from CODE attribute)
                * description (unicode string): CIM error description (from
                  DESCRIPTION attribute)
                * instances: List of CIMInstance objects (from INSTANCE
                  children)
            None, otherwise.
        """
        xml_event = self.optional_start_element('ERROR')
        if not xml_event:
            return None

        code = self.unpack_numeric(xml_event.required_attribute('CODE'))
        description = xml_event.optional_attribute('DESCRIPTION', None)

        instances = self.list_of_INSTANCE_elements()

        self.required_end_element('ERROR')

        return code, description, instances

    # CIM typed values and CIM objects

    def list_of_CLASS_elements(self):
        """
        Process a (possibly empty) consecutive list of CLASS elements
        (from start to end including children).

        DTD::

            CLASS*

        Returns:
            list of CIMClass: The CIM classes representing the CLASS elements.
        """
        class_objs = list()
        while self.test_start_element('CLASS'):
            class_obj = self.required_CLASS_element()
            class_objs.append(class_obj)
        return class_objs

    def optional_CLASS_element(self):
        """
        Process an optional CLASS element (from start to end
        including children).

        DTD::

            CLASS?

        Returns:
            CIMClass: The CIM class representing the CLASS element, if
              present.
            None, otherwise.
        """
        if not self.test_start_element('CLASS'):
            return None
        return self.required_CLASS_element()

    def required_CLASS_element(self):
        """
        Process a required CLASS element
        (from start to end including children).

        DTD::

            <!ELEMENT CLASS (QUALIFIER*, (PROPERTY | PROPERTY.ARRAY |
                                          PROPERTY.REFERENCE)*, METHOD*)>
            <!ATTLIST CLASS
                %CIMName;
                %SuperClass;>

        Returns:
            CIMClass: The CIM class representing the CLASS element.
        """
        xml_event = self.required_start_element('CLASS')

        name = xml_event.required_attribute('NAME')
        superclass = xml_event.optional_attribute('SUPERCLASS', None)

        qualifier_objs = self.list_of_QUALIFIER_elements()

        property_objs = list()
        while True:
            if self.test_start_element('PROPERTY'):
                property_obj = self.required_PROPERTY_element()
                property_objs.append(property_obj)
            elif self.test_start_element('PROPERTY.ARRAY'):
                property_obj = self.required_PROPERTY_ARRAY_element()
                property_objs.append(property_obj)
            elif self.test_start_element('PROPERTY.REFERENCE'):
                property_obj = self.required_PROPERTY_REFERENCE_element()
                property_objs.append(property_obj)
            else:
                break

        method_objs = list()
        while self.test_start_element('METHOD'):
            method_obj = self.required_METHOD_element()
            method_objs.append(method_obj)

        self.required_end_element('CLASS')

        class_obj = CIMClass(
            name, superclass=superclass,
            properties=property_objs, methods=method_objs,
            qualifiers=qualifier_objs)
        return class_obj

    def list_of_CLASSNAME_elements(self):
        """
        Process a (possibly empty) consecutive list of CLASSNAME elements
        (from start to end including children).

        DTD::

            CLASSNAME*

        Returns:
            list of CIMClassName: The CIM class paths representing the
              CLASSNAME elements.
        """
        classname_objs = list()
        while self.test_start_element('CLASSNAME'):
            classname_obj = self.required_CLASSNAME_element()
            classname_objs.append(classname_obj)
        return classname_objs

    def required_CLASSNAME_element(self):
        """
        Process a required CLASSNAME element
        (from start to end including children).

        DTD::

            <!ELEMENT CLASSNAME EMPTY>
            <!ATTLIST CLASSNAME
                %CIMName;>

        Returns:
            CIMClassName: The CIM class path representing the CLASSNAME
              element.
        """

        xml_event = self.required_start_element('CLASSNAME')

        classname = xml_event.required_attribute('NAME')

        self.required_end_element('CLASSNAME')

        classname_obj = CIMClassName(classname)
        return classname_obj

    def required_CLASSPATH_element(self):
        """
        Process a required CLASSPATH element
        (from start to end including children).

        DTD::

            <!ELEMENT CLASSPATH (NAMESPACEPATH, CLASSNAME)>

        Returns:
            CIMClassName: The CIM class path representing the CLASSPATH
              element.
        """
        self.required_start_element('CLASSPATH')
        host, namespace = self.required_NAMESPACEPATH_element()
        classname_obj = self.required_CLASSNAME_element()
        classname_obj.host = host
        classname_obj.namespace = namespace
        self.required_end_element('CLASSPATH')
        return classname_obj

    def required_LOCALCLASSPATH_element(self):
        """
        Process a required LOCALCLASSPATH element
        (from start to end including children).

        DTD::

            <!ELEMENT LOCALCLASSPATH (LOCALNAMESPACEPATH, CLASSNAME)>

        Returns:
            CIMClassName: The CIM class path representing the
              LOCALCLASSPATH element.
        """
        self.required_start_element('LOCALCLASSPATH')
        namespace = self.required_LOCALNAMESPACEPATH_element()
        classname_obj = self.required_CLASSNAME_element()
        classname_obj.namespace = namespace
        self.required_end_element('LOCALCLASSPATH')
        return classname_obj

    def list_of_INSTANCE_elements(self):
        """
        Process a (possibly empty) consecutive list of INSTANCE elements
        (from start to end including children).

        DTD::

            INSTANCE*

        Returns:
            list of CIMInstance: The CIM instances representing the INSTANCE
              elements.
        """
        instances = list()
        while self.test_start_element('INSTANCE'):
            instance = self.required_INSTANCE_element()
            instances.append(instance)
        return instances

    def required_INSTANCE_element(self):
        """
        Process a required INSTANCE element
        (from start to end including children).

        DTD::

            <!ELEMENT INSTANCE (QUALIFIER*, (PROPERTY | PROPERTY.ARRAY |
                                             PROPERTY.REFERENCE)*)>
            <!ATTLIST INSTANCE
                %ClassName;
                xml:lang NMTOKEN #IMPLIED>

        Returns:
            CIMInstance: The CIM instance representing the INSTANCE element.
        """
        xml_event = self.required_start_element('INSTANCE')

        classname = xml_event.required_attribute('CLASSNAME')

        qualifier_objs = self.list_of_QUALIFIER_elements()

        property_objs = list()
        while True:
            if self.test_start_element('PROPERTY'):
                property_obj = self.required_PROPERTY_element()
                property_objs.append(property_obj)
            elif self.test_start_element('PROPERTY.ARRAY'):
                property_obj = self.required_PROPERTY_ARRAY_element()
                property_objs.append(property_obj)
            elif self.test_start_element('PROPERTY.REFERENCE'):
                property_obj = self.required_PROPERTY_REFERENCE_element()
                property_objs.append(property_obj)
            else:
                break

        self.required_end_element('INSTANCE')

        instance_obj = CIMInstance(
            classname,
            properties=property_objs,
            qualifiers=qualifier_objs)
        return instance_obj

    def list_of_INSTANCENAME_elements(self):
        """
        Process a (possibly empty) consecutive list of INSTANCENAME elements
        (from start to end including children).

        DTD::

            INSTANCENAME*

        Returns:
            list of CIMInstanceName: The CIM instance paths representing the
              INSTANCENAME elements.
        """
        instancename_objs = list()
        while self.test_start_element('INSTANCENAME'):
            instancename_obj = self.required_INSTANCENAME_element()
            instancename_objs.append(instancename_obj)
        return instancename_objs

    def required_INSTANCENAME_element(self):
        """
        Process a required INSTANCENAME element
        (from start to end including children).

        DTD::

            <!ELEMENT INSTANCENAME (KEYBINDING* | KEYVALUE? |
                                    VALUE.REFERENCE?)>
            <!ATTLIST INSTANCENAME
                %ClassName;>

        Returns:
            CIMInstanceName: The CIM instance path representing the
              INSTANCENAME element.
        """
        xml_event = self.required_start_element('INSTANCENAME')

        classname = xml_event.required_attribute('CLASSNAME')

        keybindings = self.list_of_KEYBINDING_elements()
        if not keybindings and self.test_start_element('KEYVALUE'):
            keyvalue = self.required_KEYVALUE_element()
            keybindings = {None: keyvalue}  # Unnamed key
        elif not keybindings and self.test_start_element('VALUE.REFERENCE'):
            keyvalue = self.required_VALUE_REFERENCE_element()
            keybindings = {None: keyvalue}  # Unnamed key
        # if keybindings = {}, this is a keyless singleton instance

        self.required_end_element('INSTANCENAME')

        instancename_obj = CIMInstanceName(
            classname,
            keybindings=keybindings)
        return instancename_obj

    def list_of_INSTANCEPATH_elements(self):
        """
        Process a (possibly empty) consecutive list of INSTANCEPATH elements
        (from start to end including children).

        DTD::

            INSTANCEPATH*

        Returns:
            list of CIMInstanceName: The CIM instance paths representing the
              INSTANCEPATH elements.
        """
        instancename_objs = list()
        while self.test_start_element('INSTANCEPATH'):
            instancename_obj = self.required_INSTANCEPATH_element()
            instancename_objs.append(instancename_obj)
        return instancename_objs

    def required_INSTANCEPATH_element(self):
        """
        Process a required INSTANCEPATH element
        (from start to end including children).

        DTD::

            <!ELEMENT INSTANCEPATH (NAMESPACEPATH, INSTANCENAME)>

        Returns:
            CIMInstanceName: The CIM instance path represented by the
              INSTANCEPATH element.
        """
        self.required_start_element('INSTANCEPATH')
        host, namespace = self.required_NAMESPACEPATH_element()
        instancename_obj = self.required_INSTANCENAME_element()
        instancename_obj.host = host
        instancename_obj.namespace = namespace
        self.required_end_element('INSTANCEPATH')
        return instancename_obj

    def required_LOCALINSTANCEPATH_element(self):
        """
        Process a required LOCALINSTANCEPATH element
        (from start to end including children).

        DTD::

            <!ELEMENT LOCALINSTANCEPATH (LOCALNAMESPACEPATH, INSTANCENAME)>

        Returns:
            CIMInstanceName: The CIM class path represented by the
              LOCALINSTANCEPATH element.
        """
        self.required_start_element('LOCALINSTANCEPATH')
        namespace = self.required_LOCALNAMESPACEPATH_element()
        instancename_obj = self.required_INSTANCENAME_element()
        instancename_obj.namespace = namespace
        self.required_end_element('LOCALINSTANCEPATH')
        return instancename_obj

    def required_NAMESPACEPATH_element(self):
        """
        Process a required NAMESPACEPATH element
        (from start to end including children).

        DTD::

            <!ELEMENT NAMESPACEPATH (HOST, LOCALNAMESPACEPATH)>

        Returns:
            tuple (host, namespace), with:
              * host (unicode string): Host of the namespace path.
              * namespace (unicode string): Namespace of the namespace path.
        """
        self.required_start_element('NAMESPACEPATH')
        host = self.required_HOST_element()
        namespace = self.required_LOCALNAMESPACEPATH_element()
        self.required_end_element('NAMESPACEPATH')
        return host, namespace

    def required_LOCALNAMESPACEPATH_element(self):
        """
        Process a required LOCALNAMESPACEPATH element
        (from start to end including children).

        The namespace components from the list of NAMESPACE children are
        concatenated using '/' to form the returned namespace string.

        DTD::

            <!ELEMENT LOCALNAMESPACEPATH (NAMESPACE+)>

            With:

            <!ELEMENT NAMESPACE EMPTY>
            <!ATTLIST NAMESPACE
                %CIMName;>

        Returns:
            unicode string: The namespace string.
        """
        self.required_start_element('LOCALNAMESPACEPATH')

        namespace_parts = list()
        while True:
            xml_event = self.optional_start_element('NAMESPACE')
            if not xml_event:
                break
            namespace_part = xml_event.required_attribute('NAME')
            namespace_parts.append(namespace_part)
            self.required_end_element('NAMESPACE')

        if not namespace_parts:
            raise CIMXMLParseError(
                "'LOCALNAMESPACEPATH' element does not have any 'NAMESPACE' "
                "child element (at least one is required)",
                self.conn_id)

        namespace = '/'.join(namespace_parts)

        self.required_end_element('LOCALNAMESPACEPATH')
        return namespace

    def required_HOST_element(self):
        """
        Process a required HOST element (from start to end).

        DTD::

            <!ELEMENT HOST (#PCDATA)>

        Returns:
            unicode string: The host.
        """
        self.required_start_element('HOST')
        xml_event = self.required_end_element('HOST', allow_content=True)
        host = self.unpack_string(xml_event.content)
        return host

    def required_PROPERTY_element(self):
        """
        Process a required PROPERTY element (for instances or classes)
        (from start to end including children).

        DTD::

            <!ELEMENT PROPERTY (QUALIFIER*, VALUE?)>
            <!ATTLIST PROPERTY
                %CIMName;
                %CIMType;              #REQUIRED
                %ClassOrigin;
                %Propagated;
                %EmbeddedObject;
                xml:lang NMTOKEN #IMPLIED>

        Returns:
            CIMProperty: The property representing the PROPERTY element.
        """
        xml_event = self.required_start_element('PROPERTY')

        name = xml_event.required_attribute('NAME')
        cimtype = xml_event.required_attribute('TYPE')
        class_origin = xml_event.optional_attribute('CLASSORIGIN', None)
        propagated = self.unpack_boolean(
            xml_event.optional_attribute('PROPAGATED', 'false'))
        embedded_object = xml_event.optional_attribute(
            'EmbeddedObject',
            xml_event.optional_attribute('EMBEDDEDOBJECT', None))

        qualifier_objs = self.list_of_QUALIFIER_elements()

        if self.test_start_element('VALUE'):
            value = self.required_VALUE_element(cimtype, embedded_object)
        else:
            value = None

        self.required_end_element('PROPERTY')

        property_obj = CIMProperty(
            name, value,
            type=cimtype,
            embedded_object=embedded_object,
            is_array=False, reference_class=None,
            class_origin=class_origin, propagated=propagated,
            qualifiers=qualifier_objs)
        return property_obj

    def required_PROPERTY_ARRAY_element(self):
        """
        Process a required PROPERTY.ARRAY element (for instances or classes)
        (from start to end including children).

        DTD::

            <!ELEMENT PROPERTY.ARRAY (QUALIFIER*, VALUE.ARRAY?)>
            <!ATTLIST PROPERTY.ARRAY
                %CIMName;
                %CIMType;              #REQUIRED
                %ArraySize;
                %ClassOrigin;
                %Propagated;
                %EmbeddedObject;
                xml:lang NMTOKEN #IMPLIED>

        Returns:
            CIMProperty: The property representing the PROPERTY.ARRAY element.
        """
        xml_event = self.required_start_element('PROPERTY.ARRAY')

        name = xml_event.required_attribute('NAME')
        cimtype = xml_event.required_attribute('TYPE')
        class_origin = xml_event.optional_attribute('CLASSORIGIN', None)
        propagated = self.unpack_boolean(
            xml_event.optional_attribute('PROPAGATED', 'false'))
        array_size = self.unpack_numeric(
            xml_event.optional_attribute('ARRAYSIZE', None), None)
        embedded_object = xml_event.optional_attribute(
            'EmbeddedObject',
            xml_event.optional_attribute('EMBEDDEDOBJECT', None))

        qualifier_objs = self.list_of_QUALIFIER_elements()

        if self.test_start_element('VALUE.ARRAY'):
            value = self.required_VALUE_ARRAY_element(cimtype, embedded_object)
        else:
            value = None

        self.required_end_element('PROPERTY.ARRAY')

        property_obj = CIMProperty(
            name, value,
            type=cimtype,
            embedded_object=embedded_object,
            is_array=True, array_size=array_size, reference_class=None,
            class_origin=class_origin, propagated=propagated,
            qualifiers=qualifier_objs)
        return property_obj

    def required_PROPERTY_REFERENCE_element(self):
        """
        Process a required PROPERTY.REFERENCE element (for instances or classes)
        (from start to end including children).

        DTD::

            <!ELEMENT PROPERTY.REFERENCE (QUALIFIER*, (VALUE.REFERENCE)?)>
            <!ATTLIST PROPERTY.REFERENCE
                %CIMName;
                %ReferenceClass;
                %ClassOrigin;
                %Propagated;>

        Returns:
            CIMProperty: The property representing the PROPERTY.REFERENCE
              element.
        """
        xml_event = self.required_start_element('PROPERTY.REFERENCE')

        name = xml_event.required_attribute('NAME')
        reference_class = xml_event.optional_attribute('REFERENCECLASS', None)
        class_origin = xml_event.optional_attribute('CLASSORIGIN', None)
        propagated = self.unpack_boolean(
            xml_event.optional_attribute('PROPAGATED', 'false'))

        qualifier_objs = self.list_of_QUALIFIER_elements()

        if self.test_start_element('VALUE.REFERENCE'):
            value = self.required_VALUE_REFERENCE_element()
        else:
            value = None

        self.required_end_element('PROPERTY.REFERENCE')

        property_obj = CIMProperty(
            name, value,
            type='reference',
            embedded_object=None,
            is_array=False, reference_class=reference_class,
            class_origin=class_origin, propagated=propagated,
            qualifiers=qualifier_objs)
        return property_obj

    def required_METHOD_element(self):
        """
        Process a required METHOD element
        (from start to end including children).

        DTD::

            <!ELEMENT METHOD (QUALIFIER*, (PARAMETER | PARAMETER.REFERENCE |
                                           PARAMETER.ARRAY |
                                           PARAMETER.REFARRAY)*)>
            <!ATTLIST METHOD
                %CIMName;
                %CIMType;              #IMPLIED
                %ClassOrigin;
                %Propagated;>

        Returns:
            CIMMethod: The method representing the METHOD element.
        """
        xml_event = self.required_start_element('METHOD')

        name = xml_event.required_attribute('NAME')
        cimtype = xml_event.required_attribute('TYPE')
        class_origin = xml_event.optional_attribute('CLASSORIGIN', None)
        propagated = self.unpack_boolean(
            xml_event.optional_attribute('PROPAGATED', 'false'))

        qualifier_objs = self.list_of_QUALIFIER_elements()

        parameter_objs = list()
        while True:
            if self.test_start_element('PARAMETER'):
                parameter_obj = self.required_PARAMETER_element()
                parameter_objs.append(parameter_obj)
            elif self.test_start_element('PARAMETER.ARRAY'):
                parameter_obj = self.required_PARAMETER_ARRAY_element()
                parameter_objs.append(parameter_obj)
            elif self.test_start_element('PARAMETER.REFERENCE'):
                parameter_obj = self.required_PARAMETER_REFERENCE_element()
                parameter_objs.append(parameter_obj)
            elif self.test_start_element('PARAMETER.REFARRAY'):
                parameter_obj = self.required_PARAMETER_REFARRAY_element()
                parameter_objs.append(parameter_obj)
            else:
                break

        self.required_end_element('METHOD')

        method_obj = CIMMethod(
            name=name, return_type=cimtype, parameters=parameter_objs,
            class_origin=class_origin, propagated=propagated,
            qualifiers=qualifier_objs)
        return method_obj

    def required_PARAMETER_element(self):
        """
        Process a required PARAMETER element
        (from start to end including children).

        DTD::

            <!ELEMENT PARAMETER (QUALIFIER*)>
            <!ATTLIST PARAMETER
                %CIMName;
                %CIMType;              #REQUIRED>

        Returns:
            CIMParameter: The parameter representing the PARAMETER element.
        """
        xml_event = self.required_start_element('PARAMETER')

        name = xml_event.required_attribute('NAME')
        cimtype = xml_event.required_attribute('TYPE')

        qualifier_objs = self.list_of_QUALIFIER_elements()

        self.required_end_element('PARAMETER')

        parameter_obj = CIMParameter(
            name, value=None, type=cimtype,
            is_array=False, reference_class=None,
            qualifiers=qualifier_objs)
        return parameter_obj

    def required_PARAMETER_ARRAY_element(self):
        """
        Process a required PARAMETER.ARRAY element
        (from start to end including children).

        DTD::

            <!ELEMENT PARAMETER.ARRAY (QUALIFIER*)>
            <!ATTLIST PARAMETER.ARRAY
                %CIMName;
                %CIMType;              #REQUIRED
                %ArraySize;>

        Returns:
            CIMParameter: The parameter representing the PARAMETER.ARRAY
              element.
        """
        xml_event = self.required_start_element('PARAMETER.ARRAY')

        name = xml_event.required_attribute('NAME')
        cimtype = xml_event.required_attribute('TYPE')
        array_size = self.unpack_numeric(
            xml_event.optional_attribute('ARRAYSIZE', None), None)

        qualifier_objs = self.list_of_QUALIFIER_elements()

        self.required_end_element('PARAMETER.ARRAY')

        parameter_obj = CIMParameter(
            name, value=None, type=cimtype,
            is_array=True, array_size=array_size, reference_class=None,
            qualifiers=qualifier_objs)
        return parameter_obj

    def required_PARAMETER_REFERENCE_element(self):
        """
        Process a required PARAMETER.REFERENCE element
        (from start to end including children).

        DTD::

            <!ELEMENT PARAMETER.REFERENCE (QUALIFIER*)>
            <!ATTLIST PARAMETER.REFERENCE
                %CIMName;
                %ReferenceClass;>

        Returns:
            CIMParameter: The parameter representing the PARAMETER.REFERENCE
              element.
        """
        xml_event = self.required_start_element('PARAMETER.REFERENCE')

        name = xml_event.required_attribute('NAME')
        reference_class = xml_event.optional_attribute('REFERENCECLASS', None)

        qualifier_objs = self.list_of_QUALIFIER_elements()

        self.required_end_element('PARAMETER.REFERENCE')

        parameter_obj = CIMParameter(
            name, value=None, type='reference',
            is_array=False,
            reference_class=reference_class,
            qualifiers=qualifier_objs)
        return parameter_obj

    def required_PARAMETER_REFARRAY_element(self):
        """
        Process a required PARAMETER.REFARRAY element
        (from start to end including children).

        DTD::

            <!ELEMENT PARAMETER.REFARRAY (QUALIFIER*)>
            <!ATTLIST PARAMETER.REFARRAY
                %CIMName;
                %ReferenceClass;
                %ArraySize;>

        Returns:
            CIMParameter: The parameter representing the PARAMETER.REFARRAY
              element.
        """
        xml_event = self.required_start_element('PARAMETER.REFARRAY')

        name = xml_event.required_attribute('NAME')
        reference_class = xml_event.optional_attribute('REFERENCECLASS', None)
        array_size = self.unpack_numeric(
            xml_event.optional_attribute('ARRAYSIZE', None), None)

        qualifier_objs = self.list_of_QUALIFIER_elements()

        self.required_end_element('PARAMETER.REFARRAY')

        parameter_obj = CIMParameter(
            name, value=None, type='reference',
            is_array=True, array_size=array_size,
            reference_class=reference_class,
            qualifiers=qualifier_objs)
        return parameter_obj

    def list_of_KEYBINDING_elements(self):
        """
        Process a (possibly empty) consecutive list of KEYBINDING elements
        (from start to end including children).

        DTD::

            KEYBINDING*

        Returns:
            dict of keybindings, with:
              * key (unicode string): Keybinding name.
              * value: CIM typed value of the keybinding.
        """
        keybindings = dict()
        while self.test_start_element('KEYBINDING'):
            name, value = self.required_KEYBINDING_element()
            keybindings[name] = value
        return keybindings

    def required_KEYBINDING_element(self):
        """
        Process a required KEYBINDING element
        (from start to end including children).

        DTD::

            <!ELEMENT KEYBINDING (KEYVALUE | VALUE.REFERENCE)>
            <!ATTLIST KEYBINDING
                %CIMName;>

        Returns:
            tuple (name, value), with:
              * name (unicode string): Keybinding name.
              * value: CIM typed value of the keybinding.
        """
        xml_event = self.required_start_element('KEYBINDING')
        name = xml_event.required_attribute('NAME')
        if self.test_start_element('KEYVALUE'):
            value = self.required_KEYVALUE_element()
        elif self.test_start_element('VALUE.REFERENCE'):
            value = self.required_VALUE_REFERENCE_element()
        else:
            self.fail_invalid_or_missing_child('KEYBINDING')
        self.required_end_element('KEYBINDING')
        return name, value

    def required_KEYVALUE_element(self):
        """
        Process a required KEYVALUE element
        (from start to end including children).

        DTD::

            <!ELEMENT KEYVALUE (#PCDATA)>
            <!ATTLIST KEYVALUE
                VALUETYPE (string | boolean | numeric) "string"
                %CIMType;              #IMPLIED>

        Returns:
            CIM typed value of the keybinding (will not be None).
        """
        self.required_start_element('KEYVALUE')
        xml_event = self.required_end_element('KEYVALUE', allow_content=True)
        data = xml_event.content

        valuetype = xml_event.optional_attribute('VALUETYPE', None)
        cimtype = xml_event.optional_attribute('TYPE', None)

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
                    _format("'KEYVALUE' element has invalid 'VALUETYPE' "
                            "attribute value: {0!r}",
                            valuetype),
                    conn_id=self.conn_id)

        return self.unpack_simple_value(data, cimtype)

    def required_VALUE_REFERENCE_element(self):
        """
        Process a required VALUE.REFERENCE element
        (from start to end including children).

        DTD::

            <!ELEMENT VALUE.REFERENCE (CLASSPATH | LOCALCLASSPATH | CLASSNAME |
                                       INSTANCEPATH | LOCALINSTANCEPATH |
                                       INSTANCENAME)>

        Returns:
            CIMInstanceName: The instance path representing the
              VALUE.REFERENCE element.
        """
        self.required_start_element('VALUE.REFERENCE')
        if self.test_start_element('CLASSPATH'):
            value = self.required_CLASSPATH_element()
        elif self.test_start_element('LOCALCLASSPATH'):
            value = self.required_LOCALCLASSPATH_element()
        elif self.test_start_element('CLASSNAME'):
            value = self.required_CLASSNAME_element()
        elif self.test_start_element('INSTANCEPATH'):
            value = self.required_INSTANCEPATH_element()
        elif self.test_start_element('LOCALINSTANCEPATH'):
            value = self.required_LOCALINSTANCEPATH_element()
        elif self.test_start_element('INSTANCENAME'):
            value = self.required_INSTANCENAME_element()
        else:
            self.fail_invalid_or_missing_child('VALUE.REFERENCE')
        self.required_end_element('VALUE.REFERENCE')
        return value

    def list_of_OBJECTPATH_elements(self):
        """
        Process a (possibly empty) consecutive list of OBJECTPATH elements
        (from start to end including children).

        DTD::

            OBJECTPATH*

        Returns:
            list of CIMInstanceName or CIMClassName: The CIM objects
              representing the OBJECTPATH elements.
        """
        objectname_objs = list()
        while self.test_start_element('OBJECTPATH'):
            objectname_obj = self.required_OBJECTPATH_element()
            objectname_objs.append(objectname_obj)
        return objectname_objs

    def required_OBJECTPATH_element(self):
        """
        Process an OBJECTPATH element
        (from start to end including children).

        DTD::

            <!ELEMENT OBJECTPATH (INSTANCEPATH | CLASSPATH)>

        Returns:
            CIMInstanceName or CIMClassName: The CIM object representing the
              OBJECTPATH element.
        """
        self.required_start_element('OBJECTPATH')
        if self.test_start_element('INSTANCEPATH'):
            objectname_obj = self.required_INSTANCEPATH_element()
        elif self.test_start_element('CLASSPATH'):
            objectname_obj = self.required_CLASSPATH_element()
        else:
            self.fail_invalid_or_missing_child('OBJECTPATH')
        self.required_end_element('OBJECTPATH')
        return objectname_obj

    def list_of_QUALIFIER_elements(self):
        """
        Process a (possibly empty) consecutive list of QUALIFIER
        elements (from start to end including children).

        DTD::

            QUALIFIER*

        Returns:
            list of CIMQualifier: The CIM qualifier values represented
              by the QUALIFIER elements.
        """
        qualifier_objs = list()
        while self.test_start_element('QUALIFIER'):
            qualifier_obj = self.required_QUALIFIER_element()
            qualifier_objs.append(qualifier_obj)
        return qualifier_objs

    def required_QUALIFIER_element(self):
        """
        Process a required QUALIFIER element
        (from start to end including children).

        DTD::

            <!ELEMENT QUALIFIER (VALUE | VALUE.ARRAY)>
            <!ATTLIST QUALIFIER
                %CIMName;
                %CIMType;              #REQUIRED
                %Propagated;
                %QualifierFlavor;
                xml:lang NMTOKEN #IMPLIED>

        Note: A qualifier value of NULL is represented by omitting the
        VALUE or VALUE.ARRAY child elements. This is not correctly described
        in the DTD in DSP0201 (2.4.1).

        Returns:
            CIMQualifier: The qualifier value representing the QUALIFIER
              element.
        """
        xml_event = self.required_start_element('QUALIFIER')

        name = xml_event.required_attribute('NAME')
        cimtype = xml_event.required_attribute('TYPE')
        propagated = self.unpack_boolean(
            xml_event.optional_attribute('PROPAGATED', 'false'))
        overridable = self.unpack_boolean(
            xml_event.optional_attribute('OVERRIDABLE', 'true'))
        tosubclass = self.unpack_boolean(
            xml_event.optional_attribute('TOSUBCLASS', 'true'))
        toinstance = self.unpack_boolean(
            xml_event.optional_attribute('TOINSTANCE', 'false'))
        translatable = self.unpack_boolean(
            xml_event.optional_attribute('TRANSLATABLE', 'false'))

        if self.test_start_element('VALUE'):
            value = self.required_VALUE_element(cimtype)
        elif self.test_start_element('VALUE.ARRAY'):
            value = self.required_VALUE_ARRAY_element(cimtype)
        else:
            xml_event = self.peek_next_element()
            if xml_event.event == 'start':
                raise CIMXMLParseError(
                    _format("'QUALIFIER' element has an invalid child "
                            "element {0!A}",
                            xml_event.name),
                    self.conn_id)
            else:
                assert xml_event.event == 'end'
                value = None
        self.required_end_element('QUALIFIER')

        qualifier_obj = CIMQualifier(
            name, value, cimtype,
            propagated=propagated, overridable=overridable,
            tosubclass=tosubclass, toinstance=toinstance,
            translatable=translatable)
        return qualifier_obj

    def list_of_QUALIFIER_DECLARATION_elements(self):
        """
        Process a (possibly empty) consecutive list of QUALIFIER.DECLARATION
        elements (from start to end including children).

        DTD::

            QUALIFIER.DECLARATION*

        Returns:
            list of CIMQualifierDeclaration: The CIM qualifier types represented
              by the QUALIFIER.DECLARATION elements.
        """
        qualifierdecl_objs = list()
        while self.test_start_element('QUALIFIER.DECLARATION'):
            qualifierdecl_obj = self.required_QUALIFIER_DECLARATION_element()
            qualifierdecl_objs.append(qualifierdecl_obj)
        return qualifierdecl_objs

    def required_QUALIFIER_DECLARATION_element(self):
        """
        Process a required QUALIFIER.DECLARATION element
        (from start to end including children).

        DTD::

            <!ELEMENT QUALIFIER.DECLARATION (SCOPE?, (VALUE | VALUE.ARRAY)?)>
            <!ATTLIST QUALIFIER.DECLARATION
                %CIMName;
                %CIMType;               #REQUIRED
                ISARRAY    (true|false) #IMPLIED
                %ArraySize;
                %QualifierFlavor;>

        Returns:
            CIMQualifierDeclaration: The CIM qualifier type represented
              by the QUALIFIER.DECLARATION element.
        """
        xml_event = self.required_start_element('QUALIFIER.DECLARATION')

        name = xml_event.required_attribute('NAME')
        cimtype = xml_event.required_attribute('TYPE')
        is_array = self.unpack_boolean(
            xml_event.optional_attribute('ISARRAY', None))
        array_size = self.unpack_numeric(
            xml_event.optional_attribute('ARRAYSIZE', None), None)
        overridable = self.unpack_boolean(
            xml_event.optional_attribute('OVERRIDABLE', 'true'))
        tosubclass = self.unpack_boolean(
            xml_event.optional_attribute('TOSUBCLASS', 'true'))
        toinstance = self.unpack_boolean(
            xml_event.optional_attribute('TOINSTANCE', 'false'))
        translatable = self.unpack_boolean(
            xml_event.optional_attribute('TRANSLATABLE', 'false'))

        if self.test_start_element('SCOPE'):
            scopes = self.required_SCOPE_element()
        else:
            scopes = {}

        if self.test_start_element('VALUE'):
            value = self.required_VALUE_element(cimtype)
        elif self.test_start_element('VALUE.ARRAY'):
            value = self.required_VALUE_ARRAY_element(cimtype)
        else:
            value = None

        self.required_end_element('QUALIFIER.DECLARATION')

        qualifierdecl_obj = CIMQualifierDeclaration(
            name, cimtype, value=value, is_array=is_array,
            array_size=array_size, scopes=scopes,
            overridable=overridable, tosubclass=tosubclass,
            toinstance=toinstance, translatable=translatable)
        return qualifierdecl_obj

    def required_SCOPE_element(self):
        """
        Process a required SCOPE element
        (from start to end including children).

        Unspecified scope attributes are not represented in the returned
        dictionary; the user is expected to assume their default value of
        False.

        DTD::

            <!ELEMENT SCOPE EMPTY>
            <!ATTLIST SCOPE
                CLASS (true | false) "false"
                ASSOCIATION (true | false) "false"
                REFERENCE (true | false) "false"
                PROPERTY (true | false) "false"
                METHOD (true | false) "false"
                PARAMETER (true | false) "false"
                INDICATION (true | false) "false"

        Returns:
            dict of scope attributes representing the SCOPE element, with:
              * key: scope name, in upper case
              * value: boolean scope attribute
        """
        xml_event = self.required_start_element('SCOPE')

        scopes = dict()
        for attr_name in (u'CLASS', u'ASSOCIATION', u'REFERENCE', u'PROPERTY',
                          u'METHOD', u'PARAMETER', u'INDICATION'):
            attr_value_str = xml_event.optional_attribute(attr_name, None)
            if attr_value_str is not None:
                # The attribute was specified
                if attr_value_str == '':
                    raise CIMXMLParseError(
                        _format("'SCOPE' element has an invalid value {0!A} "
                                "for its boolean attribute {1!A}",
                                attr_value_str, attr_name),
                        conn_id=self.conn_id)
                attr_value = self.unpack_boolean(attr_value_str)
                scopes[attr_name] = attr_value

        self.required_end_element('SCOPE')

        return scopes

    def list_of_VALUE_INSTANCEWITHPATH_elements(self):
        """
        Process a (possibly empty) consecutive list of VALUE.INSTANCEWITHPATH
        elements (from start to end including children).

        DTD::

            VALUE.INSTANCEWITHPATH*

        Returns:
            list of CIMInstance: The CIM instances representing the
              VALUE.INSTANCEWITHPATH elements.
        """
        instance_objs = list()
        while self.test_start_element('VALUE.INSTANCEWITHPATH'):
            instance_obj = self.required_VALUE_INSTANCEWITHPATH_element()
            instance_objs.append(instance_obj)
        return instance_objs

    def required_VALUE_INSTANCEWITHPATH_element(self):
        """
        Process a VALUE.INSTANCEWITHPATH element (from start to end including
        children).

        DTD::

            <!ELEMENT VALUE.INSTANCEWITHPATH (INSTANCEPATH, INSTANCE)>

        Returns:
            CIMInstance: The CIM instance representing the
              VALUE.INSTANCEWITHPATH element.
        """
        self.required_start_element('VALUE.INSTANCEWITHPATH')
        instancename_obj = self.required_INSTANCEPATH_element()
        instance_obj = self.required_INSTANCE_element()
        instance_obj.path = instancename_obj
        self.required_end_element('VALUE.INSTANCEWITHPATH')
        return instance_obj

    def list_of_VALUE_NAMEDINSTANCE_elements(self):
        """
        Process a (possibly empty) consecutive list of VALUE.NAMEDINSTANCE
        elements (from start to end including children).

        DTD::

            VALUE.NAMEDINSTANCE*

        Returns:
            list of CIMInstance: The CIM instances representing the
              VALUE.NAMEDINSTANCE elements.
        """
        instance_objs = list()
        while self.test_start_element('VALUE.NAMEDINSTANCE'):
            instance_obj = self.required_VALUE_NAMEDINSTANCE_element()
            instance_objs.append(instance_obj)
        return instance_objs

    def required_VALUE_NAMEDINSTANCE_element(self):
        """
        Process a VALUE.NAMEDINSTANCE element (from start to end including
        children).

        DTD::

            <!ELEMENT VALUE.NAMEDINSTANCE (INSTANCENAME, INSTANCE)>

        Returns:
            CIMInstance: The CIM instance representing the
              VALUE.NAMEDINSTANCE element.
        """
        self.required_start_element('VALUE.NAMEDINSTANCE')
        instancename_obj = self.required_INSTANCENAME_element()
        instance_obj = self.required_INSTANCE_element()
        instance_obj.path = instancename_obj
        self.required_end_element('VALUE.NAMEDINSTANCE')
        return instance_obj

    def list_of_VALUE_OBJECTWITHPATH_elements(self):
        """
        Process a (possibly empty) consecutive list of VALUE.OBJECTWITHPATH
        elements (from start to end including children).

        DTD::

            VALUE.OBJECTWITHPATH*

        Returns:
            list of CIMInstance or CIMClass: The CIM objects representing the
              VALUE.OBJECTWITHPATH elements.
        """
        object_objs = list()
        while self.test_start_element('VALUE.OBJECTWITHPATH'):
            object_obj = self.required_VALUE_OBJECTWITHPATH_element()
            object_objs.append(object_obj)
        return object_objs

    def required_VALUE_OBJECTWITHPATH_element(self):
        """
        Process a (possibly empty) consecutive VALUE.OBJECTWITHPATH
        element (from start to end including children).

        DTD::

            <!ELEMENT VALUE.OBJECTWITHPATH ((CLASSPATH, CLASS) |
                                            (INSTANCEPATH, INSTANCE))>

        Returns:
            CIMInstance or CIMClass: The CIM object representing the
              VALUE.OBJECTWITHPATH element.
        """
        self.required_start_element('VALUE.OBJECTWITHPATH')
        if self.test_start_element('CLASSPATH'):
            objectname_obj = self.required_CLASSPATH_element()
            object_obj = self.required_CLASS_element()
            object_obj.path = objectname_obj
        elif self.test_start_element('INSTANCEPATH'):
            objectname_obj = self.required_INSTANCEPATH_element()
            object_obj = self.required_INSTANCE_element()
            object_obj.path = objectname_obj
        else:
            self.fail_invalid_or_missing_child('VALUE.OBJECTWITHPATH')
        self.required_end_element('VALUE.OBJECTWITHPATH')
        return object_obj

    def required_VALUE_OBJECTWITHLOCALPATH_element(self):
        # pylint: disable=invalid-name
        """
        Process a required VALUE.OBJECTWITHLOCALPATH element
        (from start to end including children).

        DTD::

            <!ELEMENT VALUE.OBJECTWITHLOCALPATH ((LOCALCLASSPATH, CLASS) |
                                                (LOCALINSTANCEPATH, INSTANCE))>

        Returns:
            CIMInstance or CIMClass: The CIM object representing the
              VALUE.OBJECTWITHLOCALPATH element.
        """
        self.required_start_element('VALUE.OBJECTWITHLOCALPATH')
        if self.test_start_element('LOCALCLASSPATH'):
            objectname_obj = self.required_LOCALCLASSPATH_element()
            object_obj = self.required_CLASS_element()
            object_obj.path = objectname_obj
        elif self.test_start_element('LOCALINSTANCEPATH'):
            objectname_obj = self.required_LOCALINSTANCEPATH_element()
            object_obj = self.required_INSTANCE_element()
            object_obj.path = objectname_obj
        else:
            self.fail_invalid_or_missing_child('VALUE.OBJECTWITHLOCALPATH')
        self.required_end_element('VALUE.OBJECTWITHLOCALPATH')
        return object_obj

    def required_VALUE_OBJECT_element(self):
        """
        Process a required VALUE.OBJECT element
        (from start to end including children).

        DTD::

            <!ELEMENT VALUE.OBJECT (CLASS | INSTANCE)>

        Returns:
            CIMInstance or CIMClass: The CIM object representing the
              VALUE.OBJECT element.
        """
        self.required_start_element('VALUE.OBJECT')
        if self.test_start_element('CLASS'):
            object_obj = self.required_CLASS_element()
        elif self.test_start_element('INSTANCE'):
            object_obj = self.required_INSTANCE_element()
        else:
            self.fail_invalid_or_missing_child('VALUE.OBJECT')
        self.required_end_element('VALUE.OBJECT')
        return object_obj

    def required_boolean_VALUE_element(self):
        """
        Process a required VALUE element for a boolean value
        (from start to end).

        DTD::

            <!ELEMENT VALUE (#PCDATA)>

        Returns:
            bool: The boolean value.
        """
        return self.required_VALUE_element('boolean')

    def required_string_VALUE_element(self):
        """
        Process a required VALUE element for a string value
        (from start to end).

        DTD::

            <!ELEMENT VALUE (#PCDATA)>

        Returns:
            unicode string: The string value.
        """
        return self.required_VALUE_element('string')

    def required_VALUE_element(self, cimtype=None, embedded_object=None):
        """
        Process a required VALUE element for a given CIM datatype
        (from start to end).

        Parameters:

            cimtype (string): CIM data type name (e.g. 'datetime') except
              'reference', or None (in which case a numeric value is assumed).

            embedded_object (string): 'instance', 'object', or None, indicating
              whether the value is an embedded object. In that case, the
              CIM-XML value is parsed accordingly and a CIMInstance or
              CIMClass object representing the embedded object is returned.

        DTD::

            <!ELEMENT VALUE (#PCDATA)>

        Returns:
            CIM typed value, or None.
        """
        self.required_start_element('VALUE')
        xml_event = self.required_end_element('VALUE', allow_content=True)
        value = self.unpack_simple_value(xml_event.content, cimtype)
        if embedded_object:
            value = self.parse_embedded_object(value)
        return value

    def required_VALUE_ARRAY_element(self, cimtype=None, embedded_object=None):
        """
        Process a required VALUE.ARRAY element for a given CIM datatype
        (from start to end).

        Parameters:

            cimtype (string): CIM data type name (e.g. 'datetime') except
              'reference', or None (in which case a numeric value is assumed).

            embedded_object (string): 'instance', 'object', or None, indicating
              whether the value is an embedded object. In that case, the
              CIM-XML value is parsed accordingly and a CIMInstance or
              CIMClass object representing the embedded object is returned.

        DTD::

            <!ELEMENT VALUE.ARRAY (VALUE | VALUE.NULL)*>

        Returns:
            List of CIM typed values in the array.
        """
        self.required_start_element('VALUE.ARRAY')
        values = list()
        while True:
            if self.test_start_element('VALUE'):
                value = self.required_VALUE_element(cimtype, embedded_object)
                values.append(value)
            elif self.test_start_element('VALUE.NULL'):
                value = self.required_VALUE_NULL_element()
                values.append(value)
            else:
                break
        self.required_end_element('VALUE.ARRAY')
        return values

    def required_VALUE_NULL_element(self):
        """
        Process a required VALUE.NULL element
        (from start to end).

        DTD::

            <!ELEMENT VALUE.NULL EMPTY>

        Returns:
            None (as a representation of the NULL value).
        """
        self.required_start_element('VALUE.NULL')
        self.required_end_element('VALUE.NULL')
        return None

    def required_VALUE_REFARRAY_element(self):
        """
        Process a required VALUE.REFARRAY element
        (from start to end).

        DTD::

            <!ELEMENT VALUE.REFARRAY (VALUE.REFERENCE | VALUE.NULL)*>

        Returns:
            list of CIM typed values representing the VALUE.REFARRAY element.
        """
        self.required_start_element('VALUE.REFARRAY')
        values = list()
        while True:
            if self.test_start_element('VALUE.REFERENCE'):
                value = self.required_VALUE_REFERENCE_element()
                values.append(value)
            elif self.test_start_element('VALUE.NULL'):
                value = self.required_VALUE_NULL_element()
                values.append(value)
            else:
                break
        self.required_end_element('VALUE.REFARRAY')
        return values

    def required_VALUE_NAMEDOBJECT_element(self):
        """
        Process a required VALUE.NAMEDOBJECT element
        (from start to end).

        DTD::

            <!ELEMENT VALUE.NAMEDOBJECT (CLASS | (INSTANCENAME, INSTANCE))>

        Returns:
            CIMInstance or CIMClass: The CIM object representing the
              VALUE.NAMEDOBJECT element.
        """
        self.required_start_element('VALUE.NAMEDOBJECT')
        if self.test_start_element('CLASS'):
            object_obj = self.required_CLASS_element()
        elif self.test_start_element('INSTANCENAME'):
            objectname_obj = self.required_INSTANCENAME_element()
            object_obj = self.required_INSTANCE_element()
            object_obj.path = objectname_obj
        else:
            self.fail_invalid_or_missing_child('VALUE.NAMEDOBJECT')
        self.required_end_element('VALUE.NAMEDOBJECT')
        return object_obj

    def list_of_execquery_result_object_elements(self):
        """
        Process a (possibly empty) consecutive list of various object elements
        (from start to end including children) that are allowable as return
        values of the ExecQuery operation:

        DTD::

            (VALUE.OBJECT | VALUE.OBJECTWITHLOCALPATH | VALUE.OBJECTWITHPATH)*

        Returns:
            list of CIMInstance or CIMClass: The CIM objects representing the
              ExecQuery result.
        """
        object_objs = list()
        while True:
            if self.test_start_element('VALUE.OBJECT'):
                object_obj = self.required_VALUE_OBJECT_element()
                object_objs.append(object_obj)
            elif self.test_start_element('VALUE.OBJECTWITHLOCALPATH'):
                object_obj = self.required_VALUE_OBJECTWITHLOCALPATH_element()
                object_objs.append(object_obj)
            elif self.test_start_element('VALUE.OBJECTWITHPATH'):
                object_obj = self.required_VALUE_OBJECTWITHPATH_element()
                object_objs.append(object_obj)
            else:
                break
        return object_objs

    def parse_embedded_object(self, embedded_xml_str):
        """
        Parse a CIM-XML string representing an embedded instance or embedded
        class and return the CIMInstance or CIMClass object representing it.

        Note that one level of unescaping XML entities and CDATA sections
        has already been performed by the XML parser, so the input CIM-XML
        string is an XML element with normal XML delimiters, e.g. `<INSTANCE>`.

        Parameters:

          embedded_xml_str (string):
              The CIM-XML string representing the embedded object, or None
              (in which case None is returned).

        Example:

            Example CIM-XML string for an embedded instance that has a
            first property whose value contains XML special characters that are
            XML-escaped, and a second property that is again an embedded
            instance and again has a property containing XML special
            characters that are XML-escaped:

            ::

                <INSTANCE CLASSNAME="PyWBEM_Address">
                  <PROPERTY NAME="Street" TYPE="string">
                    <VALUE>Fritz &amp; &lt;Cat&gt; Ave</VALUE>
                  </PROPERTY>
                  <PROPERTY NAME="Town" TYPE="string" EmbeddedObject="instance">
                    <VALUE>
                      &lt;INSTANCE CLASSNAME="PyWBEM_Town"&gt;
                        &lt;PROPERTY NAME="Name" TYPE="string"&gt;
                          &lt;VALUE&gt;Fritz &amp;amp; &amp;lt;Cat&amp;gt;
                            Town&lt;/VALUE&gt;
                        &lt;/PROPERTY&gt;
                      &lt;/INSTANCE&gt;
                    </VALUE>
                  </PROPERTY>
                </INSTANCE>

        Returns:
            CIMClass or CIMInstance or None, if embedded_xml_str is None.

        Raises:
            CIMXMLParseError: There is an error in the embedded CIM-XML string.
        """

        if embedded_xml_str is None:
            return None

        parser = CIMXMLParser(embedded_xml_str)

        if parser.test_start_element('INSTANCE'):
            return parser.required_INSTANCE_element()
        elif parser.test_start_element('CLASS'):
            return parser.required_CLASS_element()
        else:
            parser.get_next_event()
            raise CIMXMLParseError(
                _format("Invalid root element {0!A} in embedded object value",
                        parser.element.tagName),
                conn_id=self.conn_id)

    def unpack_simple_value(self, data, cimtype):
        """
        Unpack a simple (=non-array) CIM-XML value of any CIM type except
        'reference' and return it as a CIM typed value.

        Parameters:

            data (string): CIM-XML value, or None.
              If None, the returned value is None.

            cimtype (string): CIM data type name (e.g. 'datetime') except
              'reference', or None (in which case a numeric value is assumed).

        Returns:
            CIM typed value, or None.
        """

        if cimtype == 'string':
            return self.unpack_string(data)

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
        Unpack a simple (=non-array) CIM-XML value of CIM type 'boolean' and
        return it as a CIM typed value (Python bool).

        Parameters:

            data (string): CIM-XML value, or None.
              If None, the returned value is None.

        Returns:
            bool: CIM typed value, or None.
        """

        if data is None:
            return None

        if isinstance(data, six.binary_type):
            data = data.decode('utf-8')

        # CIM-XML says "These values MUST be treated as case-insensitive"
        # (even though the XML definition requires them to be lowercase.)
        data_ = data.strip().lower()                   # ignore space

        if data_ == 'true':
            return True

        if data_ == 'false':
            return False

        if data_ == '':
            warnings.warn("WBEM server sent invalid empty boolean value in a "
                          "CIM-XML response; interpreting as NULL/None.",
                          ToleratedServerIssueWarning,
                          stacklevel=_stacklevel_above_module(__name__))
            return None

        raise CIMXMLParseError(
            _format("Invalid boolean value {0!r}", data),
            conn_id=self.conn_id)

    def unpack_numeric(self, data, cimtype=None):
        """
        Unpack a simple (=non-array) CIM-XML value of a numeric CIM type and
        return it as a CIM typed value (e.g. Uint8), or int/long/float.

        Parameters:

            data (string): CIM-XML value, or None.
              If None, the returned value is None.

            cimtype (string): CIM data type name (e.g. 'uint8'), or None (in
              which case the value is returned as a Python int/long or float).

        Returns:
            CIM typed value (e.g. Uint8), or int/long/float if no type was
              specified, or None.
        """

        if data is None:
            return None

        if isinstance(data, six.binary_type):
            data = data.decode('utf-8')

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
                    raise CIMXMLParseError(
                        _format("Invalid numeric value {0!r}", data),
                        conn_id=self.conn_id)

        # Convert the Python number into a CIM data type
        if cimtype is None:
            return value  # int/long or float (used for keybindings)

        # The caller ensured a numeric type for cimtype
        cim_type = type_from_name(cimtype)
        try:
            value = cim_type(value)
        except ValueError as exc:
            raise CIMXMLParseError(
                _format("Cannot convert value {0!r} to numeric CIM type "
                        "{1!A}: {2}",
                        value, cimtype, exc),
                conn_id=self.conn_id)
        return value

    def unpack_datetime(self, data):
        """
        Unpack a simple (=non-array) CIM-XML value of CIM type 'datetime' and
        return it as a CIM typed value (CIMDateTime object).

        Parameters:

            data (string): CIM-XML value, or None.
              If None, the returned value is None.

        Returns:
            CIMDateTime, or None.
        """

        if data is None:
            return None

        try:
            value = CIMDateTime(data)
        except ValueError as exc:
            raise CIMXMLParseError(
                _format("Invalid datetime value: {0!r} ({1})",
                        data, exc),
                conn_id=self.conn_id)
        return value

    def unpack_char16(self, data):
        """
        Unpack a simple (=non-array) CIM-XML value of CIM type 'char16' and
        return it as a CIM typed value (unicode string).

        Parameters:

            data (string): CIM-XML value, or None.
              If None, the returned value is None.

        Returns:
            unicode string with the one character, or None.
        """

        if data is None:
            return None

        if isinstance(data, six.binary_type):
            data = data.decode('utf-8')

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
                _format("Char16 value has more than one UCS-2 character: "
                        "{0!r}",
                        data),
                conn_id=self.conn_id)

        if ord(data) > 0xFFFF:
            # One character from the UCS-4 set in a wide Python build.
            raise CIMXMLParseError(
                _format("Char16 value is a character outside of the "
                        "UCS-2 range: {0!r}",
                        data),
                conn_id=self.conn_id)

        return data

    @staticmethod
    def unpack_string(data):
        """
        Unpack a simple (=non-array) CIM-XML value of CIM type 'string' and
        return it as a CIM typed value (unicode string).

        Parameters:

            data (string): CIM-XML value, or None.
              If None, the returned value is None.

        Returns:
            unicode string, or None.
        """

        if data is None:
            return None

        if isinstance(data, six.binary_type):
            data = data.decode('utf-8')

        return data


# Operation output parameter definitions.
# Operations that are not listed have no output parameters.
# key: operation name.
# value: dict of allowable output parameters for the operation:
#   key: output parameter name
#   value: dict of output parameter definitions:
#     required: Indicates whether the output parameter is required
#     cimtype: Output parameter CIM type (for VALUE and VALUE.ARRAY children,
#       otherwise None)
#     child_element_func: parser function used on child element of parameter
OPERATION_OUTPARAM_DEFS = {
    'OpenEnumerateInstances': {
        'EnumerationContext':
            dict(
                required=True,
                cimtype='string',
                child_element_func=CIMXMLParser.required_string_VALUE_element,
            ),
        'EndOfSequence':
            dict(
                required=True,
                cimtype='boolean',
                child_element_func=CIMXMLParser.required_boolean_VALUE_element,
            ),
    },
    'OpenEnumerateInstancePaths': {
        'EnumerationContext':
            dict(
                required=True,
                cimtype='string',
                child_element_func=CIMXMLParser.required_string_VALUE_element,
            ),
        'EndOfSequence':
            dict(
                required=True,
                cimtype='boolean',
                child_element_func=CIMXMLParser.required_boolean_VALUE_element,
            ),
    },
    'OpenAssociatorInstances': {
        'EnumerationContext':
            dict(
                required=True,
                cimtype='string',
                child_element_func=CIMXMLParser.required_string_VALUE_element,
            ),
        'EndOfSequence':
            dict(
                required=True,
                cimtype='boolean',
                child_element_func=CIMXMLParser.required_boolean_VALUE_element,
            ),
    },
    'OpenAssociatorInstancePaths': {
        'EnumerationContext':
            dict(
                required=True,
                cimtype='string',
                child_element_func=CIMXMLParser.required_string_VALUE_element,
            ),
        'EndOfSequence':
            dict(
                required=True,
                cimtype='boolean',
                child_element_func=CIMXMLParser.required_boolean_VALUE_element,
            ),
    },
    'OpenReferenceInstances': {
        'EnumerationContext':
            dict(
                required=True,
                cimtype='string',
                child_element_func=CIMXMLParser.required_string_VALUE_element,
            ),
        'EndOfSequence':
            dict(
                required=True,
                cimtype='boolean',
                child_element_func=CIMXMLParser.required_boolean_VALUE_element,
            ),
    },
    'OpenReferenceInstancePaths': {
        'EnumerationContext':
            dict(
                required=True,
                cimtype='string',
                child_element_func=CIMXMLParser.required_string_VALUE_element,
            ),
        'EndOfSequence':
            dict(
                required=True,
                cimtype='boolean',
                child_element_func=CIMXMLParser.required_boolean_VALUE_element,
            ),
    },
    'OpenQueryInstances': {
        'EnumerationContext':
            dict(
                required=True,
                cimtype='string',
                child_element_func=CIMXMLParser.required_string_VALUE_element,
            ),
        'EndOfSequence':
            dict(
                required=True,
                cimtype='boolean',
                child_element_func=CIMXMLParser.required_boolean_VALUE_element,
            ),
        'QueryResultClass':
            dict(
                required=False,
                cimtype=None,
                child_element_func=CIMXMLParser.optional_CLASS_element,
            ),
    },
    'PullInstancesWithPath': {
        'EnumerationContext':
            dict(
                required=True,
                cimtype='string',
                child_element_func=CIMXMLParser.required_string_VALUE_element,
            ),
        'EndOfSequence':
            dict(
                required=True,
                cimtype='boolean',
                child_element_func=CIMXMLParser.required_boolean_VALUE_element,
            ),
    },
    'PullInstancePaths': {
        'EnumerationContext':
            dict(
                required=True,
                cimtype='string',
                child_element_func=CIMXMLParser.required_string_VALUE_element,
            ),
        'EndOfSequence':
            dict(
                required=True,
                cimtype='boolean',
                child_element_func=CIMXMLParser.required_boolean_VALUE_element,
            ),
    },
    'PullInstances': {
        'EnumerationContext':
            dict(
                required=True,
                cimtype='string',
                child_element_func=CIMXMLParser.required_string_VALUE_element,
            ),
        'EndOfSequence':
            dict(
                required=True,
                cimtype='boolean',
                child_element_func=CIMXMLParser.required_boolean_VALUE_element,
            ),
    },
}

# Operation return value parsing functions.
# Operations that are not listed have no return value (= void).
# value: parser function
OPERATION_RETURN_FUNCS = {
    'EnumerateInstances':
        CIMXMLParser.list_of_VALUE_NAMEDINSTANCE_elements,
    'EnumerateInstanceNames':
        CIMXMLParser.list_of_INSTANCENAME_elements,
    'GetInstance':
        CIMXMLParser.required_INSTANCE_element,
    'CreateInstance':
        CIMXMLParser.required_INSTANCENAME_element,
    'Associators':
        CIMXMLParser.list_of_VALUE_OBJECTWITHPATH_elements,
    'AssociatorNames':
        CIMXMLParser.list_of_OBJECTPATH_elements,
    'References':
        CIMXMLParser.list_of_VALUE_OBJECTWITHPATH_elements,
    'ReferenceNames':
        CIMXMLParser.list_of_OBJECTPATH_elements,
    'ExecQuery':
        CIMXMLParser.list_of_execquery_result_object_elements,
    'OpenEnumerateInstances':
        CIMXMLParser.list_of_VALUE_INSTANCEWITHPATH_elements,
    'OpenEnumerateInstancePaths':
        CIMXMLParser.list_of_INSTANCEPATH_elements,
    'OpenAssociatorInstances':
        CIMXMLParser.list_of_VALUE_INSTANCEWITHPATH_elements,
    'OpenAssociatorInstancePaths':
        CIMXMLParser.list_of_INSTANCEPATH_elements,
    'OpenReferenceInstances':
        CIMXMLParser.list_of_VALUE_INSTANCEWITHPATH_elements,
    'OpenReferenceInstancePaths':
        CIMXMLParser.list_of_INSTANCEPATH_elements,
    'OpenQueryInstances':
        CIMXMLParser.list_of_INSTANCE_elements,
    'PullInstancesWithPath':
        CIMXMLParser.list_of_VALUE_INSTANCEWITHPATH_elements,
    'PullInstancePaths':
        CIMXMLParser.list_of_INSTANCEPATH_elements,
    'PullInstances':
        CIMXMLParser.list_of_INSTANCE_elements,
    'EnumerateClasses':
        CIMXMLParser.list_of_CLASS_elements,
    'EnumerateClassNames':
        CIMXMLParser.list_of_CLASSNAME_elements,
    'GetClass':
        CIMXMLParser.required_CLASS_element,
    'EnumerateQualifiers':
        CIMXMLParser.list_of_QUALIFIER_DECLARATION_elements,
    'GetQualifier':
        CIMXMLParser.required_QUALIFIER_DECLARATION_element,
}
