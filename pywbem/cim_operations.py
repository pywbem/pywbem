#
# (C) Copyright 2003-2007 Hewlett-Packard Development Company, L.P.
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
# Author: Tim Potter <tpot@hp.com>
# Author: Martin Pool <mbp@hp.com>
# Author: Bart Whiteley <bwhiteley@suse.de>
# Author: Ross Peoples <ross.peoples@gmail.com>
#

# pylint: disable=line-too-long
"""
Objects of the :class:`~pywbem.WBEMConnection` class represent a connection to
a WBEM server.
All WBEM operations defined in :term:`DSP0200` can be issued across this connection.
Each method of this class corresponds directly to a WBEM operation.

==========================================================  ==============================================================
WBEMConnection method                                       Purpose
==========================================================  ==============================================================
:meth:`~pywbem.WBEMConnection.EnumerateInstanceNames`       Enumerate the instance paths of instances of a class
                                                            (including instances of its subclasses).
:meth:`~pywbem.WBEMConnection.EnumerateInstances`           Enumerate the instances of a class (including instances of its
                                                            subclasses)
:meth:`~pywbem.WBEMConnection.GetInstance`                  Retrieve an instance
:meth:`~pywbem.WBEMConnection.ModifyInstance`               Modify the property values of an instance
:meth:`~pywbem.WBEMConnection.CreateInstance`               Create an instance
:meth:`~pywbem.WBEMConnection.DeleteInstance`               Delete an instance
----------------------------------------------------------  --------------------------------------------------------------
:meth:`~pywbem.WBEMConnection.AssociatorNames`              Retrieve the instance paths of the instances (or classes)
                                                            associated to a source instance (or source class)
:meth:`~pywbem.WBEMConnection.Associators`                  Retrieve the instances (or classes) associated to a source
                                                            instance (or source class)
:meth:`~pywbem.WBEMConnection.ReferenceNames`               Retrieve the instance paths of the association instances (or
                                                            association classes) that reference a source instance (or
                                                            source class)
:meth:`~pywbem.WBEMConnection.References`                   Retrieve the association instances (or association classes)
                                                            that reference a source instance (or source class)
----------------------------------------------------------  --------------------------------------------------------------
:meth:`~pywbem.WBEMConnection.InvokeMethod`                 Invoke a method on a target instance or on a target class
----------------------------------------------------------  --------------------------------------------------------------
:meth:`~pywbem.WBEMConnection.ExecQuery`                    Execute a query in a namespace
----------------------------------------------------------  --------------------------------------------------------------
:meth:`~pywbem.WBEMConnection.IterEnumerateInstances`       Experimental:
                                                            Iterator API that uses either OpenEnumerateInstances and
                                                            PullInstancesWithPath or EnumerateInstances depending on
                                                            the attributes and existence of pull operations in the
                                                            server.
:meth:`~pywbem.WBEMConnection.IterEnumerateInstancePaths`   Experimental:
                                                            Iterator API that uses either OpenEnumerateInstances and
                                                            PullInstancesWithPath or EnumerateInstances depending on
                                                            the attributes and existence of pull operations in the
                                                            server.
:meth:`~pywbem.WBEMConnection.IterReferenceInstances`       Experimental:
                                                            Iterator API that uses either OpenReferenceInstances and
                                                            PullInstancesWithPath or References depending on
                                                            the attributes and existence of pull operations in the
                                                            server.
:meth:`~pywbem.WBEMConnection.IterReferenceInstancePaths`   Experimental:
                                                            Iterator API that uses either OpenReferenceInstances and
                                                            PullInstancesWithPath or References depending on
                                                            the attributes and existence of pull operations in the
                                                            server.
:meth:`~pywbem.WBEMConnection.IterAssociatorInstances`      Experimental:
                                                            Iterator API that uses either OpenAssociatorInstances and
                                                            PullInstancesWithPath or Associators depending on
                                                            the attributes and existence of pull operations in the
                                                            server.
:meth:`~pywbem.WBEMConnection.IterAssociatorInstancePaths`  Experimental:
                                                            Iterator API that uses either OpenAssociatorInstances and
                                                            PullInstancesWithPath or Associators depending on
                                                            the attributes and existence of pull operations in the
                                                            server.
:meth:`~pywbem.WBEMConnection.IterQueryInstances`           Experimental:
                                                            Iterator API that uses either OpenQueryInstances and
                                                            PullInstances or ExecQuery depending on
                                                            the attributes and existence of pull operations in the
                                                            server.
----------------------------------------------------------  --------------------------------------------------------------
:meth:`~pywbem.WBEMConnection.OpenEnumerateInstances`       Open enumeration session to retrieve instances of
                                                            of a class (including instances of its subclass)
:meth:`~pywbem.WBEMConnection.OpenAssociatorInstances`      Open enumeration session to retrieve the instances
                                                            associated to a source instance
:meth:`~pywbem.WBEMConnection.OpenReferenceInstances`       Open enumeration session to retrieve the instances
                                                            that reference a source instance
:meth:`~pywbem.WBEMConnection.PullInstancesWithPath`        Continue enumeration session opened with
                                                            OpenEnumerateInstances, OpenAssociatorInstances, or
                                                            OpenReferenceinstances
:meth:`~pywbem.WBEMConnection.OpenEnumerateInstancePaths`   Open enumeration session to retrieve instances of a class
                                                            (including instances of its subclass)
:meth:`~pywbem.WBEMConnection.OpenAssociatorInstancePaths`  Open enumeration session to retrieve the instances
                                                            associated to a source instance
:meth:`~pywbem.WBEMConnection.OpenReferenceInstancePaths`   Open enumeration session to retrieve the instances that
                                                            reference a source instance
:meth:`~pywbem.WBEMConnection.PullInstancePaths`            Continue enumeration session opened with
                                                            OpenEnumerateInstancePaths, OpenAssociatorInstancePaths,
                                                            or OpenReferenceInstancePaths
:meth:`~pywbem.WBEMConnection.OpenQueryInstances`           Open query request to retrieve instances defined by
                                                            the query parameter in a namespace
:meth:`~pywbem.WBEMConnection.PullInstances`                Continue enumeration of enumeration session opened
                                                            with OpenExecQuery
:meth:`~pywbem.WBEMConnection.CloseEnumeration`             Close an enumeration session in process.
----------------------------------------------------------  --------------------------------------------------------------
:meth:`~pywbem.WBEMConnection.EnumerateClassNames`          Enumerate the names of subclasses of a class, or of the
                                                            top-level classes in a namespace
:meth:`~pywbem.WBEMConnection.EnumerateClasses`             Enumerate the subclasses of a class, or the top-level classes
                                                            in a namespace
:meth:`~pywbem.WBEMConnection.GetClass`                     Retrieve a class
:meth:`~pywbem.WBEMConnection.ModifyClass`                  Modify a class
:meth:`~pywbem.WBEMConnection.CreateClass`                  Create a class
:meth:`~pywbem.WBEMConnection.DeleteClass`                  Delete a class
----------------------------------------------------------  --------------------------------------------------------------
:meth:`~pywbem.WBEMConnection.EnumerateQualifiers`          Enumerate qualifier declarations
:meth:`~pywbem.WBEMConnection.GetQualifier`                 Retrieve a qualifier declaration
:meth:`~pywbem.WBEMConnection.SetQualifier`                 Create or modify a qualifier declaration
:meth:`~pywbem.WBEMConnection.DeleteQualifier`              Delete a qualifier declaration
==========================================================  ==============================================================

NOTE: The method EnumerationCount is to be deprecated from the DMTF specs
and has not been implemented by any servers so was not implemented
in pywbem
"""  # noqa: E501
# pylint: enable=line-too-long
# Note: When used before module docstrings, Pylint scopes the disable statement
#       to the whole rest of the file, so we need an enable statement.

# This module is meant to be safe for 'import *'.

from __future__ import absolute_import

import re
from datetime import datetime, timedelta
from xml.dom import minidom
from xml.parsers.expat import ExpatError
from xml.sax import SAXParseException
import warnings
from collections import namedtuple

import six
from . import cim_xml
from .config import DEFAULT_ITER_MAXOBJECTCOUNT
from .cim_constants import DEFAULT_NAMESPACE, CIM_ERR_INVALID_PARAMETER, \
    CIM_ERR_NOT_SUPPORTED
from .cim_types import CIMType, CIMDateTime, atomic_to_cim_xml
from .cim_obj import CIMInstance, CIMInstanceName, CIMClass, CIMClassName, \
    NocaseDict, _ensure_unicode, tocimxml, tocimobj
from .cim_http import get_object_header, wbem_request
from .tupleparse import parse_cim
from .tupletree import xml_to_tupletree_sax
from .cim_http import parse_url
from .exceptions import Error, ParseError, AuthError, ConnectionError, \
    TimeoutError, CIMError

__all__ = ['WBEMConnection', 'PegasusUDSConnection', 'SFCBUDSConnection',
           'OpenWBEMUDSConnection']

# Global named tuples. Used by the pull operation responses to return
# (entities, end_of_sequence, and enumeration_context) to the caller.

# openenumerateInstances, OpenAssociators, etc and PullInstanceWithPath
# responses
# pylint: disable=invalid-name
pull_path_result_tuple = namedtuple("pull_path_result_tuple",
                                    ["paths", "eos", "context"])

# OpenEnumerateInstancePaths, etc.  and PullInstancePath responses
pull_inst_result_tuple = namedtuple("pull_inst_result_tuple",
                                    ["instances", "eos", "context"])

# openqueryInstances and PullInstance responses
pull_query_result_tuple = namedtuple("pull_query_result_tuple",
                                     ["instances", "eos", "context",
                                      "query_result_class"])

# unicode test to set illegal xml char constant
if len(u'\U00010122') == 2:
    # This is a "narrow" Unicode build of Python (the normal case).
    _ILLEGAL_XML_CHARS_RE = re.compile(
        u'([\u0000-\u0008\u000B-\u000C\u000E-\u001F\uFFFE\uFFFF])')
else:
    # This is a "wide" Unicode build of Python.
    _ILLEGAL_XML_CHARS_RE = re.compile(
        u'([\u0000-\u0008\u000B-\u000C\u000E-\u001F\uD800-\uDFFF\uFFFE\uFFFF])')

_ILL_FORMED_UTF8_RE = re.compile(
    b'(\xED[\xA0-\xBF][\x80-\xBF])')    # U+D800...U+DFFF


def _to_pretty_xml(xml_string):
    """
    Common function to produce pretty xml string from an input xml_string.

    This function is NOT intended to be used in major code paths since it
    uses the minidom to produce the prettified xml and that uses a lot
    of memory
    """

    result_dom = minidom.parseString(xml_string)
    pretty_result = result_dom.toprettyxml(indent='  ')

    # remove extra empty lines
    return re.sub(r'>( *[\r\n]+)+( *)<', r'>\n\2<', pretty_result)


def _check_classname(val):
    """
    Validate a classname.

    At this point, only the type is validated to be a string.
    """
    if not isinstance(val, six.string_types):
        raise ValueError("string expected for classname, not %r" % val)


def _iparam_propertylist(property_list):
    """Validate property_list and if it is not iterable convert to list.

    This is a test for a particular issue where the user supplies a single
    string in stead of a list for a PropertyList parameter. It prevents
    an XML error.
    """
    if isinstance(property_list, six.string_types):
        return [property_list]
    else:
        return property_list


def check_utf8_xml_chars(utf8_xml, meaning):
    """
    Examine a UTF-8 encoded XML string and raise a `pywbem.ParseError`
    exception if the response contains Bytes that are invalid UTF-8
    sequences (incorrectly encoded or ill-formed) or that are invalid XML
    characters.

    This function works in both "wide" and "narrow" Unicode builds of Python
    and supports the full range of Unicode characters from U+0000 to U+10FFFF.

    This function is just a workaround for the bad error handling of Python's
    `xml.dom.minidom` package. It replaces the not very informative
    `ExpatError` "not well-formed (invalid token): line: x, column: y" with a
    `pywbem.ParseError` providing more useful information.

    Parameters:

      utf8_xml (:term:`byte string`):
        The UTF-8 encoded XML string to be examined.

      meaning (:term:`string`):
        Short text with meaning of the XML string, for messages in exceptions.

    Raises:

      TypeError: Invoked with incorrect Python object type for `utf8_xml`.

      :class:`~pywbem.ParseError: `utf8_xml` contains Bytes that are invalid
      UTF-8 sequences (incorrectly encoded or ill-formed) or invalid XML
      characters.

    Notes on Unicode support in Python:

    (1) For internally representing Unicode characters in the unicode type, a
        "wide" Unicode build of Python uses UTF-32, while a "narrow" Unicode
        build uses UTF-16. The difference is visible to Python programs for
        Unicode characters assigned to code points above U+FFFF: The "narrow"
        build uses 2 characters (a surrogate pair) for them, while the "wide"
        build uses just 1 character. This affects all position- and
        length-oriented functions, such as `len()` or string slicing.

    (2) In a "wide" Unicode build of Python, the Unicode characters assigned to
        code points U+10000 to U+10FFFF are represented directly (using code
        points U+10000 to U+10FFFF) and the surrogate code points
        U+D800...U+DFFF are never used; in a "narrow" Unicode build of Python,
        the Unicode characters assigned to code points U+10000 to U+10FFFF are
        represented using pairs of the surrogate code points U+D800...U+DFFF.

    Notes on the Unicode code points U+D800...U+DFFF ("surrogate code points"):

    (1) These code points have no corresponding Unicode characters assigned,
        because they are reserved for surrogates in the UTF-16 encoding.

    (2) The UTF-8 encoding can technically represent the surrogate code points.
        ISO/IEC 10646 defines that a UTF-8 sequence containing the surrogate
        code points is ill-formed, but it is technically possible that such a
        sequence is in a UTF-8 encoded XML string.

    (3) The Python escapes ``\\u`` and ``\\U`` used in literal strings can
        represent the surrogate code points (as well as all other code points,
        regardless of whether they are assigned to Unicode characters).

    (4) The Python `encode()` and `decode()` functions successfully
        translate the surrogate code points back and forth for encoding UTF-8.

        For example, ``b'\\xed\\xb0\\x80'.decode("utf-8") = u'\\udc00'``.

    (5) Because Python supports the encoding and decoding of UTF-8 sequences
        also for the surrogate code points, the "narrow" Unicode build of
        Python can be (mis-)used to transport each surrogate unit separately
        encoded in (ill-formed) UTF-8.

        For example, code point U+10122 can be (illegally) created from a
        sequence of code points U+D800,U+DD22 represented in UTF-8:

          ``b'\\xED\\xA0\\x80\\xED\\xB4\\xA2'.decode("utf-8") = u'\\U00010122'``

        while the correct UTF-8 sequence for this code point is:

          ``u'\\U00010122'.encode("utf-8") = b'\\xf0\\x90\\x84\\xa2'``

    Notes on XML characters:

    (1) The legal XML characters are defined in W3C XML 1.0 (Fith Edition):

          ::

            Char ::= #x9 | #xA | #xD | [#x20-#xD7FF] | [#xE000-#xFFFD] |
                     [#x10000-#x10FFFF]

        These are the code points of Unicode characters using a non-surrogate
        representation.
    """

    context_before = 16    # number of chars to print before any bad chars
    context_after = 16     # number of chars to print after any bad chars

    if not isinstance(utf8_xml, six.binary_type):
        raise TypeError("utf8_xml parameter is not a byte string, "
                        "but has type %s" % type(utf8_xml))

    # Check for ill-formed UTF-8 sequences. This needs to be done
    # before the str type gets decoded to unicode, because afterwards
    # surrogates produced from ill-formed UTF-8 cannot be distinguished from
    # legally produced surrogates (for code points above U+FFFF).
    ifs_list = list()
    for m in _ILL_FORMED_UTF8_RE.finditer(utf8_xml):
        ifs_pos = m.start(1)
        ifs_seq = m.group(1)
        ifs_list.append((ifs_pos, ifs_seq))
    if len(ifs_list) > 0:
        exc_txt = "Ill-formed (surrogate) UTF-8 Byte sequences found in %s:" %\
                  meaning
        for (ifs_pos, ifs_seq) in ifs_list:
            exc_txt += "\n  At offset %d:" % ifs_pos
            for ifs_ord in six.iterbytes(ifs_seq):
                exc_txt += " 0x%02X" % ifs_ord
            cpos1 = max(ifs_pos - context_before, 0)
            cpos2 = min(ifs_pos + context_after, len(utf8_xml))
            exc_txt += ", CIM-XML snippet: %r" % utf8_xml[cpos1:cpos2]
        raise ParseError(exc_txt)

    # Check for incorrectly encoded UTF-8 sequences.
    # @ibm.13@ Simplified logic (removed loop).
    try:
        utf8_xml_u = utf8_xml.decode("utf-8")
    except UnicodeDecodeError as exc:
        # Only raised for incorrectly encoded UTF-8 sequences; technically
        # correct sequences that are ill-formed (e.g. representing surrogates)
        # do not cause this exception to be raised.
        # If more than one incorrectly encoded sequence is present, only
        # information about the first one is returned in the exception object.
        # Also, the stated reason (in _msg) is not always correct.
        unused_codec, unused_str, _p1, _p2, unused_msg = exc.args
        exc_txt = "Incorrectly encoded UTF-8 Byte sequences found in %s" %\
                  meaning
        exc_txt += "\n  At offset %d:" % _p1
        ies_seq = utf8_xml[_p1:_p2 + 1]
        for ies_ord in six.iterbytes(ies_seq):
            exc_txt += " 0x%02X" % ies_ord
        cpos1 = max(_p1 - context_before, 0)
        cpos2 = min(_p2 + context_after, len(utf8_xml))
        exc_txt += ", CIM-XML snippet: %r" % utf8_xml[cpos1:cpos2]
        raise ParseError(exc_txt)

    # Now we know the Unicode characters are valid.
    # Check for Unicode characters that cannot legally be represented as XML
    # characters.
    ixc_list = list()
    last_ixc_pos = -2
    for m in _ILLEGAL_XML_CHARS_RE.finditer(utf8_xml_u):
        ixc_pos = m.start(1)
        ixc_char_u = m.group(1)
        if ixc_pos > last_ixc_pos + 1:
            ixc_list.append((ixc_pos, ixc_char_u))
        last_ixc_pos = ixc_pos
    if len(ixc_list) > 0:
        exc_txt = "Invalid XML characters found in %s:" % meaning
        for (ixc_pos, ixc_char_u) in ixc_list:
            cpos1 = max(ixc_pos - context_before, 0)
            cpos2 = min(ixc_pos + context_after, len(utf8_xml_u))
            exc_txt += "\n  At offset %d: U+%04X, CIM-XML snippet: %r" % \
                (ixc_pos, ord(ixc_char_u), utf8_xml_u[cpos1:cpos2])
        raise ParseError(exc_txt)

    return utf8_xml


def _validateIterCommonParams(MaxObjectCount, OperationTimeout):
    """
    Validate common parameters for an iter... operation.

    MaxObjectCount must be a positive non-zero integer or None.

    OperationTimeout must be positive integer or zero

    Raises:
      ValueError if these parameters are invalid
    """
    if MaxObjectCount is None or MaxObjectCount <= 0:
        raise ValueError('MaxObjectCount must be > 0 but is %s' %
                         MaxObjectCount)

    if OperationTimeout is not None and OperationTimeout < 0:
        raise ValueError('OperationTimeout must be >= 0 but is %s' %
                         OperationTimeout)


class WBEMConnection(object):  # pylint: disable=too-many-instance-attributes
    """
    A client's connection to a WBEM server. This is the main class of the
    WBEM client library API.

    The connection object knows a default CIM namespace, which is used when no
    namespace is specified on subsequent WBEM operations (that support
    specifying namespaces). Thus, the connection object can be used as a
    connection to multiple CIM namespaces on a WBEM server (when the namespace
    is specified on subsequent operations), or as a connection to only the
    default namespace (this allows omitting the namespace on subsequent
    operations).

    As usual in HTTP, there is no persistent TCP connection; the connectedness
    provided by this class is  only conceptual. That is, the creation of the
    connection object does not cause any interaction with the WBEM server, and
    each subsequent WBEM operation performs an independent, state-less
    HTTP/HTTPS request.

    After creating a :class:`~pywbem.WBEMConnection` object, various methods
    may be called on the object, which cause WBEM operations to be issued to
    the WBEM server. See :ref:`WBEM operations` for a list of these methods.

    CIM elements such as instances or classes are represented as Python objects
    (see :ref:`CIM objects`). The caller does not need to know about the CIM-XML
    encoding of CIM elements and protocol payload that is used underneath (It
    should be possible to use a different WBEM protocol below this layer without
    disturbing any callers).

    The connection remembers the XML of the last request and last reply if
    debugging is turned on via the :attr:`debug` attribute of the
    connection object.
    This may be useful in debugging: If a problem occurs, you can examine the
    :attr:`last_request` and :attr:`last_reply` attributes of the
    connection object.
    These are the prettified XML of request and response, respectively.
    The real request and response that are sent and received are available in
    the :attr:`last_raw_request` and :attr:`last_raw_reply` attributes
    of the connection object.

    The methods of this class may raise the following exceptions:

    * Exceptions indicating processing errors:

      - :exc:`~pywbem.ConnectionError` - A connection with the WBEM server
        could not be established or broke down.

      - :exc:`~pywbem.AuthError` - Authentication failed with the WBEM server.

      - :exc:`~pywbem.HTTPError` - HTTP error (bad status code) received from
        WBEM server.

      - :exc:`~pywbem.ParseError` - The response from the WBEM server cannot
        be parsed (for example, invalid characters or UTF-8 sequences,
        ill-formed XML, or invalid CIM-XML).

      - :exc:`~pywbem.CIMError` - The WBEM server returned an error response
        with a CIM status code.

      - :exc:`~pywbem.TimeoutError` - The WBEM server did not respond in time
        and the client timed out.

    * Exceptions indicating programming errors:

      - :exc:`~py:exceptions.TypeError`
      - :exc:`~py:exceptions.KeyError`
      - :exc:`~py:exceptions.ValueError`
      - :exc:`~py:exceptions.AttributeError`
      - ... possibly others ...

      Exceptions indicating programming errors should not happen. If you think
      the reason such an exception is raised lies in pywbem,
      `report a bug <https://github.com/pywbem/pywbem/issues>`_.

    Attributes:

      ... : All parameters of the :class:`~pywbem.WBEMConnection` constructor
        are set as public attribute with the same name.

      debug (:class:`py:bool`): A boolean indicating whether logging of
        the last request and last reply is enabled.

        The initial value of this attribute is `False`.
        Debug logging can be enabled for future operations by setting this
        attribute to `True`.

      last_request (:term:`unicode string`):
        CIM-XML data of the last request sent to the WBEM server
        on this connection, formatted as prettified XML. Prior to sending the
        very first request on this connection object, it is `None`.

      last_raw_request (:term:`unicode string`):
        CIM-XML data of the last request sent to the WBEM server
        on this connection, formatted as it was sent. Prior to sending the
        very first request on this connection object, it is `None`.

      last_reply (:term:`unicode string`):
        CIM-XML data of the last response received from the WBEM server
        on this connection, formatted as prettified XML. Prior to receiving
        the very first response on this connection object, it is `None`.

      last_raw_reply (:term:`unicode string`):
        CIM-XML data of the last response received from the WBEM server
        on this connection, formatted as it was received. Prior to receiving
        the very first response on this connection object, it is `None`.

      operation_recorder (:class:`~pywbem.BaseOperationRecorder`):
        This attribute provides for recording of the operations that are
        executed on this connection. Initially, this attribute is `None`.
        If `None`, no operations are recorded.
        If set to an object of a subclass of
        :class:`~pywbem.BaseOperationRecorder`, each operation
        that is executed on this connection will be recorded by
        invoking its :meth:`~pywbem.BaseOperationRecorder.record` method.
        All operations except the Iter... operations may be recorded. Since
        the Iter... operations utilize the other operations to send requests
        their calls are NOT recorded.

        All operations except the Iter... operations may be recorded. Since
        the Iter... operations utilize the other operations to send requests
        their calls are NOT recorded.

      use_pull_operations (:class:`py:bool`):
        Indicates whether the client will attempt the use of pull operations in
        any `Iter...()` methods. However, each operation has its own internal
        equivalent flag based on this flag to allow for implementations that
        implement only some of the pull operations. The method
        `set_use_pull_operations` may be used to reset all of these flags to
        a defined value.

        This variable is initially set from the same-named input argument.
        If it is `None` is modified when `Iter...()` methods are invoked,
        dependent on the support for pull operations in the WBEM server.
        After the first call , the varaible will be either `True` or `False`
        and indicating whether pull operations will be used in this and
        subsequent `Iter...()` methods.
    """

    def __init__(self, url, creds=None, default_namespace=DEFAULT_NAMESPACE,
                 x509=None, verify_callback=None, ca_certs=None,
                 no_verification=False, timeout=None, use_pull_operations=None):
        """
        Parameters:

          url (:term:`string`):
            URL of the WBEM server, in the format:

              ``[{scheme}://]{host}[:{port}]``

            The following URL schemes are supported:

            * ``https``: Causes HTTPS to be used.
            * ``http``: Causes HTTP to be used.

            The host can be specified in any of the usual formats:

            * a short or fully qualified DNS hostname
            * a literal (= dotted) IPv4 address
            * a literal IPv6 address, formatted as defined in :term:`RFC3986`
              with the extensions for zone identifiers as defined in
              :term:`RFC6874`, supporting ``-`` (minus) for the delimiter
              before the zone ID string, as an additional choice to ``%25``.

            If no port is specified in the URL, the default ports are:

            * If HTTPS is used, port 5989.
            * If HTTP is used, port 5988.

            Examples for some URL formats:

            * ``"https://10.11.12.13:6988"``:
              Use HTTPS to port 6988 on host 10.11.12.13
            * ``"https://mysystem.acme.org"``:
              Use HTTPS to port 5989 on host mysystem.acme.org
            * ``"10.11.12.13"``:
              Use HTTP to port 5988 on host 10.11.12.13
            * ``"http://[2001:db8::1234]:15988"``:
              Use HTTP to port 15988 on host 2001:db8::1234
            * ``"http://[::ffff.10.11.12.13]"``:
              Use HTTP to port 5988 on host ::ffff.10.11.12.13 (an
              IPv4-mapped IPv6 address)
            * ``"http://[2001:db8::1234%25eth0]"`` or
              ``"http://[2001:db8::1234-eth0]"``:
              Use HTTP to port 5988 to host 2001:db8::1234 (a link-local IPv6
              address) using zone identifier eth0

          creds (:class:`py:tuple` of userid, password):
            Credentials for HTTP authenticatiion with the WBEM server, as a
            tuple(userid, password), with:

            * userid (:term:`string`):
              Userid for authenticating with the WBEM server.

            * password (:term:`string`):
              Password for that userid.

            If `None`, the client will not generate ``Authorization`` headers
            in the HTTP request. Otherwise, the client will generate an
            ``Authorization`` header using HTTP Basic Authentication.

            See :ref:`Authentication types` for an overview.

          default_namespace (:term:`string`):
            Name of the CIM namespace to be used by default (if no namespace
            is specified for an operation).

            Default: :data:`~pywbem.cim_constants.DEFAULT_NAMESPACE`.

          x509 (:class:`py:dict`):
            :term:`X.509` client certificate and key file to be presented
            to the WBEM server during the TLS/SSL handshake.

            This parameter is ignored when HTTP is used.

            If `None`, no client certificate is presented to the server,
            resulting in 1-way authentication to be used.

            Otherwise, the client certificate is presented to the server,
            resulting in 2-way authentication to be used.
            This parameter must be a dictionary containing the following
            two items:

              * ``"cert_file"`` (:term:`string`):
                The file path of a file containing an :term:`X.509` client
                certificate.

              * ``"key_file"`` (:term:`string`):
                The file path of a file containing the private key belonging to
                the public key that is part of the :term:`X.509` certificate
                file.

            See :ref:`Authentication types` for an overview.

          verify_callback (:term:`callable`):
            Registers a callback function that will be called to verify the
            X.509 server certificate returned by the WBEM server during the
            TLS/SSL handshake, in addition to the validation already performed
            by the TLS/SSL support.

            This parameter is ignored when HTTP is used.

            Note that the validation performed by the TLS/SSL support already
            includes the usual validation, so that normally a callback function
            does not need to be used. See :ref:`Verification of the X.509 server
            certificate` for details.

            Warning: This parameter is not used when the python environment
            is Python 3 because the ssl module does not support it.

            If `None`, no such callback function will be registered.

            The specified function will be called for the returned certificate,
            and for each of the certificates in its chain of trust.

            See `M2Crypto.SSL.Context.set_verify` for details, as well as
            http://blog.san-ss.com.ar/2012/05/validating-ssl-certificate-in-python.html):

            The callback function must take five parameters:

            * the `M2Crypto.SSL.Connection` object that triggered the
              verification.

            * an `OpenSSL.crypto.X509` object representing the certificate
              to be validated (the returned certificate or one of the
              certificates in its chain of trust).

            * an integer containing the error number (0 in case no error) of
              any validation error detected by `M2Crypto`.
              You can find their meaning in the OpenSSL documentation.

            * an integer indicating the depth (=position) of the certificate to
              be validated (the one in the second parameter) in the chain of
              trust of the returned certificate. A value of 0 indicates
              that the returned certificate is currently validated; any other
              value indicates the distance of the currently validated
              certificate to the returned certificate in its chain of trust.

            * an integer that indicates whether the validation of the
              certificate specified in the second parameter passed or did not
              pass the validation by `M2Crypto`. A value of 1 indicates a
              successful validation and 0 an unsuccessful one.

            The callback function must return `True` if the verification
            passes and `False` otherwise.

          ca_certs (:term:`string`):
            Location of CA certificates (trusted certificates) for
            verifying the X.509 server certificate returned by the WBEM server.

            This parameter is ignored when HTTP is used.

            The parameter value is either the directory path of a directory
            prepared using the ``c_rehash`` tool included with OpenSSL, or the
            file path of a file in PEM format.

            If `None`, default directory paths will be used to look up CA
            certificates (see :data:`~pywbem.cim_http.DEFAULT_CA_CERT_PATHS`).

          no_verification (:class:`py:bool`):
            Disables verification of the X.509 server certificate returned by
            the WBEM server during TLS/SSL handshake, and disables the
            invocation of a verification function specified in
            `verify_callback`.

            If `True`, verification is disabled; otherwise, verification is
            enabled.

            This parameter is ignored when HTTP is used.

            Disabling the verification of the server certificate is insecure
            and should be avoided!

          timeout (:term:`number`):
            Timeout in seconds, for requests sent to the server. If the server
            did not respond within the timeout duration, the socket for the
            connection will be closed, causing a :exc:`~pywbem.TimeoutError` to
            be raised.

            A value of `None` means that the connection uses the standard
            timeout behavior of Python sockets, which can be between several
            minutes and much longer. Because this is somewhat unpredictable,
            it is recommended to specify a value for the timeout.

            A value of ``0`` means the timeout is very short, and does not
            really make any sense.

            Note that not all situations can be handled within this timeout, so
            for some issues, operations may take longer before raising an
            exception.

          use_pull_operations (:class:`py:bool`):
            Controls the use of pull operations in any `Iter...()` methods, by
            intializing a corresponding instance variable that is used during
            any `Iter...()` methods.
            The default value (`None`) will work on any WBEM server whether or
            not it supports pull operations.

            `None` means that the `Iter...()` methods will attempt a pull
            operation first, and if the WBEM server does not support it, will
            use a traditional operation. The corresponding instance variable
            will be adjusted to indicate what the WBEM server supports.

            `True` means that the `Iter...()` methods will only use pull
            operations. If the WBEM server does not support pull operations, a
            :exc:`~pywbem.CIMError` with status code `CIM_ERR_NOT_SUPPORTED`
            will be raised.

            `False` means that the `Iter...()` methods will only use traditional
            operations.
        """

        self.url = url
        self.creds = creds
        self.x509 = x509
        self.verify_callback = verify_callback
        self.ca_certs = ca_certs
        self.no_verification = no_verification
        self.default_namespace = default_namespace
        self.timeout = timeout

        self.debug = False
        self.last_raw_request = None
        self.last_raw_reply = None
        self.last_request = None
        self.last_reply = None
        self.operation_recorder = None
        self.use_pull_operations = use_pull_operations
        # set the flags for each individual operation to the initial
        # value defined by use_pull_operations
        self._use_enum_inst_pull_operations = use_pull_operations
        self._use_enum_path_pull_operations = use_pull_operations
        self._use_ref_inst_pull_operations = use_pull_operations
        self._use_ref_path_pull_operations = use_pull_operations
        self._use_assoc_inst_pull_operations = use_pull_operations
        self._use_assoc_path_pull_operations = use_pull_operations
        self._use_query_pull_operations = use_pull_operations

    def __str__(self):
        """
        Return a short representation of the :class:`~pywbem.WBEMConnection`
        object for human consumption.
        """

        if isinstance(self.creds, tuple):
            # tuple (userid, password) was specified
            creds_repr = "(%r, ...)" % self.creds[0]
        else:
            creds_repr = repr(self.creds)

        return "%s(url=%r, creds=%s, default_namespace=%r)" % \
            (self.__class__.__name__, self.url, creds_repr,
             self.default_namespace)

    def __repr__(self):
        """
        Return a representation of the :class:`~pywbem.WBEMConnection` object
        with all attributes (except for the password in the
        credentials) that is suitable for debugging.
        """

        if isinstance(self.creds, tuple):
            # tuple (userid, password) was specified
            creds_repr = "(%r, ...)" % self.creds[0]
        else:
            creds_repr = repr(self.creds)
        return "%s(url=%r, creds=%s, " \
               "default_namespace=%r, x509=%r, verify_callback=%r, " \
               "ca_certs=%r, no_verification=%r, timeout=%r, " \
               "use_pull_operations=%r)" % \
               (self.__class__.__name__, self.url, creds_repr,
                self.default_namespace, self.x509, self.verify_callback,
                self.ca_certs, self.no_verification, self.timeout,
                self.use_pull_operations)

    def imethodcall(self, methodname, namespace, response_params_rqd=None,
                    **params):
        """
        This is a low-level method that is used by the operation-specific
        methods of this class
        (e.g. :meth:`~pywbem.WBEMConnection.EnumerateInstanceNames`).
        This method is not part of the external WBEM client library API; it is
        being included in the documentation only for tooling reasons.

        Deprecated: Calling this function directly has been deprecated and
        will issue a :term:`DeprecationWarning`.
        Users should call the operation-specific methods instead of this
        method.
        """
        warnings.warn(
            "Calling imethodcall() directly is deprecated",
            DeprecationWarning)
        return self._imethodcall(methodname, namespace,
                                 response_params_rqd=response_params_rqd,
                                 **params)

    def _imethodcall(self, methodname, namespace, response_params_rqd=None,
                     **params):
        """
        Perform an intrinsic CIM-XML operation.
        """

        # Create HTTP headers

        headers = ['CIMOperation: MethodCall',
                   'CIMMethod: %s' % methodname,
                   get_object_header(namespace)]

        # Create parameter list

        plist = [cim_xml.IPARAMVALUE(x[0], tocimxml(x[1]))
                 for x in params.items() if x[1] is not None]

        # Build XML request

        req_xml = cim_xml.CIM(
            cim_xml.MESSAGE(
                cim_xml.SIMPLEREQ(
                    cim_xml.IMETHODCALL(
                        methodname,
                        cim_xml.LOCALNAMESPACEPATH(
                            [cim_xml.NAMESPACE(ns)
                             for ns in namespace.split('/')]),
                        plist)),
                '1001', '1.0'),
            '2.0', '2.0')

        if self.debug:
            self.last_raw_request = req_xml.toxml()
            self.last_request = req_xml.toprettyxml(indent='  ')
            # Reset replies in case we fail before they are set
            self.last_raw_reply = None
            self.last_reply = None

        # Send request and receive response

        try:
            reply_xml = wbem_request(
                self.url, req_xml.toxml(), self.creds, headers,
                x509=self.x509,
                verify_callback=self.verify_callback,
                ca_certs=self.ca_certs,
                no_verification=self.no_verification,
                timeout=self.timeout,
                debug=self.debug,
                recorder=self.operation_recorder)
        except (AuthError, ConnectionError, TimeoutError, Error):
            raise
        # TODO 3/16 AM: Clean up exception handling. The next two lines are a
        # workaround in order not to ignore TypeError and other exceptions
        # that may be raised.
        except Exception:
            raise

        # Set the raw response before parsing (which can fail)
        if self.debug:
            self.last_raw_reply = reply_xml
        try:
            tup_tree = parse_cim(xml_to_tupletree_sax(reply_xml))
        except ParseError as exc:
            msg = str(exc)
            parsing_error = True
        except SAXParseException as exc:
            msg = str(exc)
            parsing_error = True
        except ExpatError as exc:
            # This is raised e.g. when XML numeric entity references of
            # invalid XML characters are used (e.g. '&#0;').
            # str(exc) is: "{message}, line {X}, offset {Y}"
            xml_lines = _ensure_unicode(reply_xml).splitlines()
            if len(xml_lines) >= exc.lineno:
                parsed_line = xml_lines[exc.lineno - 1]
            else:
                parsed_line = "<error: Line number indicated in ExpatError "\
                              "out of range: %s (only %s lines in XML)>" %\
                              (exc.lineno, len(xml_lines))
            msg = "ExpatError %s: %s: %r" % (str(exc.code), str(exc),
                                             parsed_line)
            parsing_error = True
        else:
            parsing_error = False

        if parsing_error or self.debug:
            # Here we just improve the quality of the exception information,
            # so we do this only if it already has failed. Because the check
            # function we invoke catches more errors than minidom.parseString,
            # we call it also when debug is turned on.
            try:
                check_utf8_xml_chars(reply_xml, "CIM-XML response")
            except ParseError:
                raise
            else:
                if parsing_error:
                    # We did not catch it in the check function, but
                    # parsing failed.
                    raise ParseError(msg)  # data from previous exception

        if self.debug:
            self.last_reply = _to_pretty_xml(reply_xml)

        # Parse response

        if tup_tree[0] != 'CIM':
            raise ParseError('Expecting CIM element, got %s' % tup_tree[0])
        tup_tree = tup_tree[2]

        if tup_tree[0] != 'MESSAGE':
            raise ParseError('Expecting MESSAGE element, got %s' % tup_tree[0])
        tup_tree = tup_tree[2]

        if tup_tree[0] != 'SIMPLERSP':
            raise ParseError('Expecting SIMPLERSP element, got %s' %
                             tup_tree[0])
        tup_tree = tup_tree[2]

        if tup_tree[0] != 'IMETHODRESPONSE':
            raise ParseError('Expecting IMETHODRESPONSE element, got %s' %
                             tup_tree[0])

        if tup_tree[1]['NAME'] != methodname:
            raise ParseError('Expecting attribute NAME=%s, got %s' %
                             (methodname, tup_tree[1]['NAME']))
        tup_tree = tup_tree[2]

        # At this point we either have a IRETURNVALUE, ERROR element
        # or None if there was no child nodes of the IMETHODRESPONSE
        # element.

        if tup_tree is None:
            return None
        if len(tup_tree) == 0:
            return None

        # ERROR | ...
        if tup_tree[0][0] == 'ERROR':
            err = tup_tree[0]
            code = int(err[1]['CODE'])
            if 'DESCRIPTION' in err[1]:
                raise CIMError(code, err[1]['DESCRIPTION'])
            raise CIMError(code, 'Error code %s' % err[1]['CODE'])
        if response_params_rqd is None:
            # expect either ERROR | IRETURNVALUE*
            err = tup_tree[0]
            if err[0] != 'IRETURNVALUE':
                raise ParseError('Expecting IRETURNVALUE element, got %s'
                                 % err[0])
            return tup_tree

        # At this point should have optional RETURNVALUE and at maybe one
        # paramvalue element representing the pull return parameters
        # of end_of_sequence/enumeration_context
        # (IRETURNVALUE*, PARAMVALUE?)
        else:
            # TODO Further tests on this IRETURN or PARAMVALUE
            # Could be IRETURNVALUE or a PARAMVALUE
            return tup_tree

    def methodcall(self, methodname, localobject, Params=None, **params):
        """
        This is a low-level method that is used by the
        :meth:`~pywbem.WBEMConnection.InvokeMethod` method of this class.
        This method is not part of the external WBEM client library API; it is
        being included in the documentation only for tooling reasons.

        Deprecated: Calling this function directly has been deprecated and
        will issue a :term:`DeprecationWarning`.
        Users should call :meth:`~pywbem.WBEMConnection.InvokeMethod` instead
        of this method.
        """
        warnings.warn(
            "Calling methodcall() directly is deprecated",
            DeprecationWarning)
        return self._methodcall(methodname, localobject, Params, **params)

    def _methodcall(self, methodname, localobject, Params=None, **params):
        """
        Perform an extrinsic CIM-XML method call.
        """

        # METHODCALL only takes a LOCALCLASSPATH or LOCALINSTANCEPATH
        if hasattr(localobject, 'host') and localobject.host is not None:
            localobject = localobject.copy()
            localobject.host = None

        # Create HTTP headers

        headers = ['CIMOperation: MethodCall',
                   'CIMMethod: %s' % methodname,
                   get_object_header(localobject)]

        # Create parameter list

        def paramtype(obj):
            """Return a string to be used as the CIMTYPE for a parameter."""
            if isinstance(obj, CIMType):
                return obj.cimtype
            elif isinstance(obj, bool):
                return 'boolean'
            elif isinstance(obj, six.string_types):
                return 'string'
            elif isinstance(obj, (datetime, timedelta)):
                return 'datetime'
            elif isinstance(obj, (CIMClassName, CIMInstanceName)):
                return 'reference'
            elif isinstance(obj, (CIMClass, CIMInstance)):
                return 'string'
            elif isinstance(obj, list):
                if obj:
                    return paramtype(obj[0])
                else:
                    return None
            raise TypeError('Unsupported parameter type "%s"' % type(obj))

        def paramvalue(obj):
            """Return a cim_xml node to be used as the value for a
            parameter."""
            if isinstance(obj, (datetime, timedelta)):
                obj = CIMDateTime(obj)
            if isinstance(obj, (CIMType, bool, six.string_types)):
                return cim_xml.VALUE(atomic_to_cim_xml(obj))
            if isinstance(obj, (CIMClassName, CIMInstanceName)):
                # Note: Because CIMDateTime is an obj but tested above
                # pylint: disable=no-member
                return cim_xml.VALUE_REFERENCE(obj.tocimxml())
            if isinstance(obj, (CIMClass, CIMInstance)):
                # Note: Because CIMDateTime is an obj but tested above
                # pylint: disable=no-member
                return cim_xml.VALUE(obj.tocimxml().toxml())
            if isinstance(obj, list):
                if obj and isinstance(obj[0], (CIMClassName, CIMInstanceName)):
                    return cim_xml.VALUE_REFARRAY([paramvalue(x) for x in obj])
                return cim_xml.VALUE_ARRAY([paramvalue(x) for x in obj])
            raise TypeError('Unsupported parameter type "%s"' % type(obj))

        def is_embedded(obj):
            """Determine if an object requires an EmbeddedObject attribute"""
            if isinstance(obj, list) and obj:
                return is_embedded(obj[0])
            elif isinstance(obj, CIMClass):
                return 'object'
            elif isinstance(obj, CIMInstance):
                return 'instance'
            return None

        if Params is None:
            Params = []
        plist = [cim_xml.PARAMVALUE(x[0],
                                    paramvalue(x[1]),
                                    paramtype(x[1]),
                                    embedded_object=is_embedded(x[1]))
                 for x in Params]
        plist += [cim_xml.PARAMVALUE(x[0],
                                     paramvalue(x[1]),
                                     paramtype(x[1]),
                                     embedded_object=is_embedded(x[1]))
                  for x in params.items()]

        # Build XML request

        req_xml = cim_xml.CIM(
            cim_xml.MESSAGE(
                cim_xml.SIMPLEREQ(
                    cim_xml.METHODCALL(
                        methodname,
                        localobject.tocimxml(),
                        plist)),
                '1001', '1.0'),
            '2.0', '2.0')

        if self.debug:
            self.last_raw_request = req_xml.toxml()
            self.last_request = req_xml.toprettyxml(indent='  ')
            # Reset replies in case we fail before they are set
            self.last_raw_reply = None
            self.last_reply = None

        # Send request and receive response

        try:
            reply_xml = wbem_request(
                self.url, req_xml.toxml(), self.creds, headers,
                x509=self.x509,
                verify_callback=self.verify_callback,
                ca_certs=self.ca_certs,
                no_verification=self.no_verification,
                timeout=self.timeout,
                debug=self.debug,
                recorder=self.operation_recorder)
        except (AuthError, ConnectionError, TimeoutError, Error):
            raise
        # TODO 3/16 AM: Clean up exception handling. The next two lines are a
        # workaround in order not to ignore TypeError and other exceptions
        # that may be raised.
        except Exception:
            raise

        # Set the raw response before parsing and checking (which can fail)
        if self.debug:
            self.last_raw_reply = reply_xml

        try:
            tt = parse_cim(xml_to_tupletree_sax(reply_xml))
        except ParseError as exc:
            msg = str(exc)
            parsing_error = True
        except SAXParseException as exc:
            msg = str(exc)
            parsing_error = True
        except ExpatError as exc:
            # This is raised e.g. when XML numeric entity references of invalid
            # XML characters are used (e.g. '&#0;').
            # str(exc) is: "{message}, line {X}, offset {Y}"
            xml_lines = _ensure_unicode(reply_xml).splitlines()
            if len(xml_lines) >= exc.lineno:
                parsed_line = xml_lines[exc.lineno - 1]
            else:
                parsed_line = "<error: Line number indicated in ExpatError "\
                              "out of range: %s (only %s lines in XML)>" %\
                              (exc.lineno, len(xml_lines))
            msg = "ExpatError %s: %s: %r" % (str(exc.code), str(exc),
                                             parsed_line)
            parsing_error = True
        else:
            parsing_error = False

        if parsing_error or self.debug:
            # Here we just improve the quality of the exception information,
            # so we do this only if it already has failed. Because the check
            # function we invoke catches more errors than minidom.parseString,
            # we call it also when debug is turned on.
            try:
                check_utf8_xml_chars(reply_xml, "CIM-XML response")
            except ParseError:
                raise
            else:
                if parsing_error:
                    # We did not catch it in the check function, but
                    # parsing failed.
                    raise ParseError(msg)  # data from previous exception

        if self.debug:
            self.last_reply = _to_pretty_xml(reply_xml)

        # Parse response

        if tt[0] != 'CIM':
            raise ParseError('Expecting CIM element, got %s' % tt[0])
        tt = tt[2]

        if tt[0] != 'MESSAGE':
            raise ParseError('Expecting MESSAGE element, got %s' % tt[0])
        tt = tt[2]

        if tt[0] != 'SIMPLERSP':
            raise ParseError('Expecting SIMPLERSP element, got %s' % tt[0])
        tt = tt[2]

        if tt[0] != 'METHODRESPONSE':
            raise ParseError('Expecting METHODRESPONSE element, got %s' %
                             tt[0])

        if tt[1]['NAME'] != methodname:
            raise ParseError('Expecting attribute NAME=%s, got %s' %
                             (methodname, tt[1]['NAME']))
        tt = tt[2]

        # At this point we have an optional RETURNVALUE and zero or
        # more PARAMVALUE elements representing output parameters.

        if len(tt) > 0 and tt[0][0] == 'ERROR':
            code = int(tt[0][1]['CODE'])
            if 'DESCRIPTION' in tt[0][1]:
                raise CIMError(code, tt[0][1]['DESCRIPTION'])
            raise CIMError(code, 'Error code %s' % tt[0][1]['CODE'])

        return tt

    def _iparam_namespace_from_namespace(self, obj):
        # pylint: disable=invalid-name,
        """Determine the namespace from a namespace string, or `None`. The
        default namespace of the connection object is used, if needed.

        Return the so determined namespace for use as an argument to
        imethodcall()."""

        if isinstance(obj, six.string_types):
            namespace = obj
        elif obj is None:
            namespace = obj
        else:
            raise TypeError('Expecting None (for default), or a namespace '
                            'string, got: %s' % type(obj))
        if namespace is None:
            namespace = self.default_namespace
        return namespace

    def _iparam_namespace_from_objectname(self, obj):
        # pylint: disable=invalid-name,
        """Determine the namespace from an object name, that can be a class
        name string, a CIMClassName or CIMInstanceName object, or `None`.
        The default namespace of the connection object is used, if needed.

        Return the so determined namespace for use as an argument to
        imethodcall()."""

        if isinstance(obj, (CIMClassName, CIMInstanceName)):
            namespace = obj.namespace
        elif isinstance(obj, six.string_types):
            namespace = None
        elif obj is None:
            namespace = obj
        else:
            raise TypeError('Expecting None (for default), a class name '
                            'string, a CIMClassName object, or a '
                            'CIMInstanceName object, got: %s' % type(obj))
        if namespace is None:
            namespace = self.default_namespace
        return namespace

    @staticmethod
    def _iparam_objectname(objectname):
        """Convert an object name (= class or instance name) specified in an
        operation method into a CIM object that can be passed to
        imethodcall()."""

        if isinstance(objectname, (CIMClassName, CIMInstanceName)):
            objectname = objectname.copy()
            objectname.host = None
            objectname.namespace = None
        elif isinstance(objectname, six.string_types):
            objectname = CIMClassName(objectname)
        elif objectname is None:
            pass
        else:
            raise TypeError('Expecting None, a classname string, a '
                            'CIMClassName or CIMInstanceName object, '
                            'got: %s' % type(objectname))
        return objectname

    @staticmethod
    def _iparam_classname(classname):
        """Convert a class name specified in an operation method into a CIM
        object that can be passed to imethodcall()."""

        if isinstance(classname, CIMClassName):
            classname = classname.copy()
            classname.host = None
            classname.namespace = None
        elif isinstance(classname, six.string_types):
            classname = CIMClassName(classname)
        elif classname is None:
            pass
        else:
            raise TypeError('Expecting None, a classname string or a '
                            'CIMClassName object, got: %s' % type(classname))
        return classname

    @staticmethod
    def _iparam_instancename(instancename):
        """Convert an instance name specified in an operation method into a CIM
        object that can be passed to imethodcall()."""

        if isinstance(instancename, CIMInstanceName):
            instancename = instancename.copy()
            instancename.host = None
            instancename.namespace = None
        elif instancename is None:
            pass
        else:
            raise TypeError('Expecting None or a CIMInstanceName object, '
                            'got: %s' % type(instancename))
        return instancename

    #
    # Instance operations
    #

    def EnumerateInstanceNames(self, ClassName, namespace=None, **extra):
        # pylint: disable=invalid-name,line-too-long
        """
        Enumerate the instance paths of instances of a class (including
        instances of its subclasses) in a namespace.

        This method performs the EnumerateInstanceNames operation
        (see :term:`DSP0200`). See :ref:`WBEM operations` for a list of all
        methods performing such operations.

        If the operation succeeds, this method returns.
        Otherwise, this method raises an exception.

        Parameters:

          ClassName (:term:`string` or :class:`~pywbem.CIMClassName`):
            Name of the class to be enumerated (case independent).
            If specified as a :class:`~pywbem.CIMClassName` object, its `host`
            attribute will be ignored.

          namespace (:term:`string`):
            Name of the CIM namespace to be used (case independent).

            If `None`, the namespace of the `ClassName` parameter will be used,
            if specified as a :class:`~pywbem.CIMClassName` object. If that is
            also `None`, the default namespace of the connection will be used.

        Keyword Arguments:

          extra :
            Additional keyword arguments are passed as additional operation
            parameters to the WBEM server.
            Note that :term:`DSP0200` does not define any additional parameters
            for this operation.

        Returns:

            A list of :class:`~pywbem.CIMInstanceName` objects that are the
            enumerated instance paths, with its attributes set
            as follows:

            * `classname`: Name of the creation class of the instance.
            * `keybindings`: Keybindings of the instance.
            * `namespace`: Name of the CIM namespace containing the instance.
            * `host`: `None`, indicating the WBEM server is unspecified.

        Raises:

            Exceptions described in :class:`~pywbem.WBEMConnection`.
        """

        if self.operation_recorder:
            self.operation_recorder.reset()
            self.operation_recorder.stage_pywbem_args(
                method='EnumerateInstanceNames',
                ClassName=ClassName,
                namespace=namespace,
                **extra)

        try:

            if namespace is None and isinstance(ClassName, CIMClassName):
                namespace = ClassName.namespace
            namespace = self._iparam_namespace_from_namespace(namespace)
            classname = self._iparam_classname(ClassName)

            result = self._imethodcall(
                'EnumerateInstanceNames',
                namespace,
                ClassName=classname,
                **extra)

            instancenames = []
            if result is not None:
                instancenames = result[0][2]

            for instancename in instancenames:
                instancename.namespace = namespace

        except Exception as exc:
            if self.operation_recorder:
                self.operation_recorder.stage_pywbem_result(None, exc)
                self.operation_recorder.record_staged()
            raise
        else:
            if self.operation_recorder:
                self.operation_recorder.stage_pywbem_result(instancenames, None)
                self.operation_recorder.record_staged()
            return instancenames

    def EnumerateInstances(self, ClassName, namespace=None, LocalOnly=None,
                           DeepInheritance=None, IncludeQualifiers=None,
                           IncludeClassOrigin=None, PropertyList=None,
                           **extra):
        # pylint: disable=invalid-name,line-too-long
        """
        Enumerate the instances of a class (including instances of its
        subclasses) in a namespace.

        This method performs the EnumerateInstances operation
        (see :term:`DSP0200`). See :ref:`WBEM operations` for a list of all
        methods performing such operations.

        If the operation succeeds, this method returns.
        Otherwise, this method raises an exception.

        Parameters:

          ClassName (:term:`string` or :class:`~pywbem.CIMClassName`):
            Name of the class to be enumerated (case independent).
            If specified as a :class:`~pywbem.CIMClassName` object, its `host`
            attribute will be ignored.

          namespace (:term:`string`):
            Name of the CIM namespace to be used (case independent).

            If `None`, the namespace of the `ClassName` parameter will be used,
            if specified as a :class:`~pywbem.CIMClassName` object. If that is
            also `None`, the default namespace of the connection will be used.

          LocalOnly (:class:`py:bool`):
            Controls the exclusion of inherited properties from the returned
            instances, as follows:

            * If `False`, inherited properties are not excluded.
            * If `True`, inherited properties are basically excluded, but the
              behavior may be WBEM server specific.
            * If `None`, this parameter is not passed to the WBEM server, and
              causes the server-implemented default to be used. :term:`DSP0200`
              defines that the server-implemented default is `True`.

            This parameter has been deprecated in :term:`DSP0200` and should be
            set to `False` by the caller.

          DeepInheritance (:class:`py:bool`):
            Indicates that properties added by subclasses of the specified
            class are to be included in the returned instances, as follows:

            * If `False`, properties added by subclasses are not included.
            * If `True`, properties added by subclasses are included.
            * If `None`, this parameter is not passed to the WBEM server, and
              causes the server-implemented default to be used. :term:`DSP0200`
              defines that the server-implemented default is `True`.

            Note, the semantics of the `DeepInheritance` parameter in
            :meth:`~pywbem.WBEMConnection.EnumerateClasses` and
            :meth:`~pywbem.WBEMConnection.EnumerateClassNames`
            is different.

          IncludeQualifiers (:class:`py:bool`):
            Indicates that qualifiers are to be included in the returned
            instance, as follows:

            * If `False`, qualifiers are not included.
            * If `True`, qualifiers are included if the WBEM server implements
              support for this parameter.
            * If `None`, this parameter is not passed to the WBEM server, and
              causes the server-implemented default to be used. :term:`DSP0200`
              defines that the server-implemented default is `False`.

            This parameter has been deprecated in :term:`DSP0200`. Clients
            cannot rely on it being implemented by WBEM servers.

          IncludeClassOrigin (:class:`py:bool`):
            Indicates that class origin information is to be included on each
            property in the returned instances, as follows:

            * If `False`, class origin information is not included.
            * If `True`, class origin information is included.
            * If `None`, this parameter is not passed to the WBEM server, and
              causes the server-implemented default to be used. :term:`DSP0200`
              defines that the server-implemented default is `False`.

          PropertyList (:term:`py:iterable` of :term:`string` or :term:`string`):
            An iterable specifying the names of the properties (or a  string
            that defines a single property) to be included in the returned
            instances (case independent).

            An empty iterable indicates to include no properties.

            If `None`, all properties are included.

        Keyword Arguments:

          extra :
            Additional keyword arguments are passed as additional operation
            parameters to the WBEM server.
            Note that :term:`DSP0200` does not define any additional parameters
            for this operation.

        Returns:

            A list of :class:`~pywbem.CIMInstance` objects that are
            representations of the enumerated instances.

            The `path` attribute of each :class:`~pywbem.CIMInstance`
            object is a :class:`~pywbem.CIMInstanceName` object with its
            attributes set as follows:

            * `classname`: Name of the creation class of the instance.
            * `keybindings`: Keybindings of the instance.
            * `namespace`: Name of the CIM namespace containing the instance.
            * `host`: `None`, indicating the WBEM server is unspecified.

        Raises:

            Exceptions described in :class:`~pywbem.WBEMConnection`.
        """  # noqa: E501

        if self.operation_recorder:
            self.operation_recorder.reset()
            self.operation_recorder.stage_pywbem_args(
                method='EnumerateInstances',
                ClassName=ClassName,
                namespace=namespace,
                LocalOnly=LocalOnly,
                DeepInheritance=DeepInheritance,
                IncludeQualifiers=IncludeQualifiers,
                IncludeClassOrigin=IncludeClassOrigin,
                PropertyList=PropertyList,
                **extra)

        try:

            if namespace is None and isinstance(ClassName, CIMClassName):
                namespace = ClassName.namespace
            namespace = self._iparam_namespace_from_namespace(namespace)
            classname = self._iparam_classname(ClassName)
            PropertyList = _iparam_propertylist(PropertyList)

            result = self._imethodcall(
                'EnumerateInstances',
                namespace,
                ClassName=classname,
                LocalOnly=LocalOnly,
                DeepInheritance=DeepInheritance,
                IncludeQualifiers=IncludeQualifiers,
                IncludeClassOrigin=IncludeClassOrigin,
                PropertyList=PropertyList,
                **extra)

            if result is None:
                instances = []
            else:
                instances = result[0][2]

            # TODO ks 6/16 would the setattr be faster?
            # TODO: ks 6/16 should we check before setting?
            # [setattr(i.path, 'namespace', namespace) for i in instances]
            for instance in instances:
                instance.path.namespace = namespace

        except Exception as exc:
            if self.operation_recorder:
                self.operation_recorder.stage_pywbem_result(None, exc)
                self.operation_recorder.record_staged()
            raise
        else:
            if self.operation_recorder:
                self.operation_recorder.stage_pywbem_result(instances, None)
                self.operation_recorder.record_staged()
            return instances

    @staticmethod
    def _get_rslt_params(result, namespace):
        """Common processing for pull results to separate
           end-of-sequence, enum-context, and endities in IRETURNVALUE.
           Returns tuple of entities in IRETURNVALUE, end_of_sequence,
           and enumeration_context)
        """
        rtn_objects = []
        end_of_sequence = False
        enumeration_context = None
        valid_result = False

        for p in result:
            if p[0] == 'EndOfSequence':
                if p[2] is None:
                    valid_result = True
                elif isinstance(p[2], six.string_types) and \
                    p[2].lower() in ['true', 'false']:  # noqa: E125
                    valid_result = True if p[2].lower() == 'true' else False
                    end_of_sequence = valid_result

            elif p[0] == 'EnumerationContext':
                if p[2] is None:
                    valid_result = True
                if isinstance(p[2], six.string_types):
                    enumeration_context = p[2]
                    valid_result = True

            elif p[0] == "IRETURNVALUE":
                rtn_objects = p[2]

        if not valid_result:
            raise CIMError(CIM_ERR_INVALID_PARAMETER, "EndOfSequence "
                           "or EnumerationContext required")

        # convert enum context if eos is True
        # Otherwise, returns tuple of enumeration context and namespace
        rtn_ctxt = None if end_of_sequence else (enumeration_context,
                                                 namespace)
        return (rtn_objects, end_of_sequence, rtn_ctxt)

    def IterEnumerateInstances(self, ClassName, namespace=None,
                               LocalOnly=None,
                               DeepInheritance=None, IncludeQualifiers=None,
                               IncludeClassOrigin=None, PropertyList=None,
                               FilterQueryLanguage=None, FilterQuery=None,
                               OperationTimeout=None, ContinueOnError=None,
                               MaxObjectCount=DEFAULT_ITER_MAXOBJECTCOUNT,
                               **extra):
        # pylint: disable=invalid-name,line-too-long
        """
        A generator function to retrieve instances from a WBEM Server.
        This method frees the user of choices between the multiple
        EnumerateInstances/OpenEnumerateInstance methods and reduces
        the enumeration to a pythonic iterator idiom.

        **Experimental:** This method is experimental in this release.

        This method performs either the
        :meth:`~pywbem.WBEMConnection.OpenEnumerateInstances` and
        :meth:`~pywbem.WBEMConnection.PullInstancesWithPath`
        operations (pull operations) or the
        :meth:`~pywbem.WBEMConnection.EnumerateInstances` operation
        (traditional operation) if the WBEM server does not support the
        pull operations. It is an alternative to using these operations
        directly, that automatically uses the pull operations if supported.

        The `use_pull_operations` argument of the
        :class:`~pywbem.WBEMConnection` constructor can be used to
        override that default behavior to either force the use of pull
        operations or to avoid their use.

        NOTE: This functionality assumes that pull operations may not be
        supported for all of the pull operation types (i.e. operations whose
        name starts with Open). Even if one `Open...` function is not
        implemented (returns `CIM_ERR_NOT_SUPPORTED`) and that operation is
        used as the first request, the code will try the Open... on other pull
        operation types the first time each type is used.

        This method provides all of the controls of the pull operations API
        except the ability to set the response size on each request; response
        size (defined by `MaxObjectCount` is the same for all of the request
        operations in the sequence). There are, limitations in that:

          * The filter function does not exist for EnumerateInstances
            so that a request with `FilterQuery` or `FilterQueryLanguage`
            attribute will be rejected if the pull operatons do not exist on
            the target WBEM Server.

          * If `ContinueOnError` is set and the pull operations are not
            supported on the server, the request is rejected.

        An open request may be closed while the iteration process is being
        executed by issuing the iterator close() method.

        If the initial request of the operation sequence succeeds, this method
        returns a Python iterator object so that the instances that are
        returned from the server can be retrieved with iterator expressions.

        Otherwise, this method raises an exception.

        Parameters:

          ClassName (:term:`string` or :class:`~pywbem.CIMClassName`):
            Name of the class to be enumerated (case independent).
            If specified as a :class:`~pywbem.CIMClassName` object, its
            `namespace` attribute will be used as a default namespace as
            described for the `namespace` parameter, and its `host` attribute
            will be ignored.

          namespace (:term:`string`):
            Name of the CIM namespace to be used (case independent).

            If `None`, the namespace of the `ClassName` parameter will be used,
            if specified as a :class:`~pywbem.CIMClassName` object. If that is
            also `None`, the default namespace of the connection will be used.

          LocalOnly (:class:`py:bool`):
            Controls the exclusion of inherited properties from the returned
            instances, as follows:

            * If `False`, inherited properties are not excluded.
            * If `True`, inherited properties are basically excluded, but the
              behavior may be WBEM server specific.
            * If `None`, this parameter is not passed to the WBEM server, and
              causes the server-implemented default to be used. :term:`DSP0200`
              defines that the server-implemented default is `True`.

            This parameter has been deprecated in :term:`DSP0200` and should be
            set to `False` by the caller.

          DeepInheritance (:class:`py:bool`):
            Indicates that properties added by subclasses of the specified
            class are to be included in the returned instances, as follows:

            * If `False`, properties added by subclasses are not included.
            * If `True`, properties added by subclasses are included.
            * If `None`, this parameter is not passed to the WBEM server, and
              causes the server-implemented default to be used. :term:`DSP0200`
              defines that the server-implemented default is `True`.

            Note, the semantics of the `DeepInheritance` parameter in
            :meth:`~pywbem.WBEMConnection.EnumerateClasses` and
            :meth:`~pywbem.WBEMConnection.EnumerateClassNames`
            is different.

          IncludeQualifiers (:class:`py:bool`):
            Indicates that qualifiers are to be included in the returned
            instance, as follows:

            * If `False`, qualifiers are not included.
            * If `True`, qualifiers are included if the WBEM server implements
              support for this parameter.
            * If `None`, this parameter is not passed to the WBEM server, and
              causes the server-implemented default to be used. :term:`DSP0200`
              defines that the server-implemented default is `False`.

            This parameter has been deprecated in :term:`DSP0200`. Clients
            cannot rely on it being implemented by WBEM servers.

          IncludeClassOrigin (:class:`py:bool`):
            Indicates that class origin information is to be included on each
            property in the returned instances, as follows:

            * If `False`, class origin information is not included.
            * If `True`, class origin information is included.
            * If `None`, this parameter is not passed to the WBEM server, and
              causes the server-implemented default to be used. :term:`DSP0200`
              defines that the server-implemented default is `False`.

          PropertyList (:term:`py:iterable` of :term:`string` or :term:`string`):
            An iterable specifying the names of the properties (or a  string
            that defines a single property) to be included in the returned
            instances (case independent).

            An empty iterable indicates to include no properties.

            If `None`, all properties are included.

          FilterQueryLanguage (:term:`string`):
            A string defining the name of the query language
            used for the `FilterQuery` parameter. The DMTF defined language
            (FQL) (:term:`DSP0212`) is specified as 'DMTF:FQL'. If this
            attribute is `True` and the method uses the EnumerateInstances
            option (either `use_pull_operations` == `False` or the server does
            not support pull operations), the method will fail with a
            ValueError.

          FilterQuery (:term:`string`):
            A string defining the query that is to be sent
            to the WBEM server using the query language defined by
            the `FilterQueryLanguage` parameter. If this
            attribute is `True` and the method uses the EnumerateInstances
            option (either `use_pull_operations` == `False` or the server does
            not support pull operations), the method will fail with a
            ValueError

          OperationTimeout (:class:`~pywbem.Uint32`):
            Minimum time in seconds the WBEM Server shall maintain an open
            enumeration session after a previous Open or Pull request is
            sent to the client. Once this timeout time has expired, the
            WBEM server may close the enumeration session.

            * If not `None`, this parameter is sent to the WBEM server as the
              proposed timeout for the enumeration session. A value of 0
              indicates that the server is expected to never time out. The
              server may reject the proposed value, causing a
              :class:`~pywbem.CIMError` to be raised with status code
              :attr:`~pywbem.CIM_ERR_INVALID_OPERATION_TIMEOUT`.
            * If `None`, this parameter is not passed to the WBEM server, and
              causes the server-implemented default timeout to be used.

          ContinueOnError (:class:`py:bool`):
            Indicates to the WBEM server to continue sending responses
            after an error response has been sent.

            * If `True`, the server is to continue sending responses after
              sending an error response. Not all servers support continuation
              on error; a server that does not support it must send an error
              response if `True` was specified, causing
              :class:`~pywbem.CIMError` to be raised with status code
              :attr:`~pywbem.CIM_ERR_CONTINUATION_ON_ERROR_NOT_SUPPORTED`.
            * If `False`, the server is requested to close the enumeration after
              sending an error response.
            * If `None`, this parameter is not passed to the WBEM server, and
              causes the server-implemented default behaviour to be used.
              :term:`DSP0200` defines that the server-implemented default is
              `False`.

            Many WBEM servers do not support this request attribute so that
            its use is NOT recommended except in special cases.

            If this attribute is `True` and the method uses the
            EnumerateInstances option (`use_pull_operations` == `False`
            or the server does not support pull operations), the method will
            fail with a ValueError

          MaxObjectCount (:class:`~pywbem.Uint32`)
            Maximum number of instances the WBEM server may return
            for each of the open and pull requests issues as part of the
            execution of this generator.

            * If positive, the WBEM server is to return no more than the
              specified number of instances.
            * Zero is not allowed; it would mean that zero instances
              are to be returned for every request issued to the server.
            * The default is defined as a system config variable.
            * `None` is not allowed.

            The choice of MaxObjectCount is client/server dependent but choices
            between 100 and 1000 typically do not have a significant impact on
            either memory or overall efficiency.

        Keyword Arguments:

          extra :
            Additional keyword arguments are passed as additional operation
            parameters to the WBEM server.
            Note that :term:`DSP0200` does not define any additional parameters
            for this operation.

        Raises:

            Exceptions described in :class:`~pywbem.WBEMConnection`.

        Returns:

          A Python :term:`generator` object. Instances can be retrieved
          by iterating through the object. Instances that are retrieved
          include the host and namespace component of the instance path.

        Example::

            insts_iterator = conn.IterEnumerateInstances('CIM_Blah')
            for inst in insts_iterator:
                # close if a particular property value found
                if inst.get('thisPropertyName') == 0
                    insts_iterator.close()
                    break
                else:
                    print('instance %s' % inst.tomof())
        """  # noqa: E501
        _validateIterCommonParams(MaxObjectCount, OperationTimeout)

        # Common variable for pull result tuple used by pulls and finally:
        pull_result = None

        try:                # try / finally block to allow iter.close()
            if (self._use_enum_inst_pull_operations is None or
                    self._use_enum_inst_pull_operations):

                try:        # operation try block
                    pull_result = self.OpenEnumerateInstances(
                        ClassName, namespace=namespace, LocalOnly=LocalOnly,
                        DeepInheritance=DeepInheritance,
                        IncludeQualifiers=IncludeQualifiers,
                        IncludeClassOrigin=IncludeClassOrigin,
                        PropertyList=PropertyList,
                        FilterQueryLanguage=FilterQueryLanguage,
                        FilterQuery=FilterQuery,
                        OperationTimeout=OperationTimeout,
                        ContinueOnError=ContinueOnError,
                        MaxObjectCount=MaxObjectCount, **extra)

                    # Open operation succeeded; set has_pull flag
                    self._use_enum_inst_pull_operations = True

                    for inst in pull_result.instances:
                        yield inst

                    # loop to pull while more while eos not returned.
                    while not pull_result.eos:
                        pull_result = self.PullInstancesWithPath(
                            pull_result.context, MaxObjectCount=MaxObjectCount)

                        for inst in pull_result.instances:
                            yield inst
                    pull_result = None   # clear the pull_result
                    return

                # If NOT_SUPPORTED and first request, set flag and try
                # alternative request operation.
                # If _use_enum_inst_pull_operations is True, always raise
                # the exception
                except CIMError as ce:
                    if self._use_enum_inst_pull_operations is None and \
                       ce.status_code == CIM_ERR_NOT_SUPPORTED:
                        self._use_enum_inst_pull_operations = False
                    else:
                        raise

            # Alternate request if Pull not implemented. This does not allow
            # the FilterQuery or ContinueOnError
            assert self._use_enum_inst_pull_operations is False

            if FilterQuery is not None or FilterQueryLanguage is not None:
                raise ValueError('EnumerateInstances does not support'
                                 ' FilterQuery.')

            if ContinueOnError is not None:
                raise ValueError('EnumerateInstances does not support '
                                 'ContinueOnError.')

            enum_rslt = self.EnumerateInstances(
                ClassName, namespace=namespace, LocalOnly=LocalOnly,
                DeepInheritance=DeepInheritance,
                IncludeQualifiers=IncludeQualifiers,
                IncludeClassOrigin=IncludeClassOrigin,
                PropertyList=PropertyList, **extra)

            # Complete namespace and host components of the path
            # pylint: disable=unused-variable
            host, port, ssl = parse_url(self.url)

            # get namespace for the operation
            if namespace is None and isinstance(ClassName, CIMClassName):
                namespace = ClassName.namespace
            namespace = self._iparam_namespace_from_namespace(namespace)

            for inst in enum_rslt:
                if inst.path.namespace is None:
                    inst.path.namespace = namespace
                if inst.path.host is None:
                    inst.path.host = host

            for inst in enum_rslt:
                yield inst

        # Cleanup if caller closes the iterator before exhausting it
        finally:
            # Cleanup only required if the pull context is open and not complete
            if pull_result is not None and not pull_result.eos:
                self.CloseEnumeration(pull_result.context)
                pull_result = None

    def IterEnumerateInstancePaths(self, ClassName, namespace=None,
                                   FilterQueryLanguage=None, FilterQuery=None,
                                   OperationTimeout=None, ContinueOnError=None,
                                   MaxObjectCount=DEFAULT_ITER_MAXOBJECTCOUNT,
                                   **extra):
        """
        A generator function to retrieve instances from a WBEM Server.
        This method frees the user of choices between the multiple
        EnumerateInstances/OpenEnumerateInstance methods and reduces
        the enumeration to a pythonic iterator idiom.

        **Experimental:** This method is experimental in this release.

        This method performs either the
        :meth:`~pywbem.WBEMConnection.OpenEnumerateInstancePaths` and
        :meth:`~pywbem.WBEMConnection.PullInstancePaths`
        operations (pull operations) or the
        :meth:`~pywbem.WBEMConnection.EnumerateInstanceNames` operation
        (traditional operation) if the WBEM server does not support the
        pull operations. It is an alternative to using these operations
        directly, that automatically uses the pull operations if supported.

        The `use_pull_operations` argument of the
        :class:`~pywbem.WBEMConnection` constructor can be used to
        override that default behavior to either force the use of pull
        operations or to avoid their use.

        NOTE: This functionality assumes that pull operations are supported for
        either all or none of the defined `Open....`  Since the first request
        determines whether operations continue with the pull operations, if
        one of the `Open...` functions is not implemented
        (returns `CIM_ERR_NOT_SUPPORTED`) and that operation is used as the
        first request, the code will decide that None of the operations are
        supported. Resetting the use_pull_operations to `None` may be used to
        override the decision made by the `Iter...` method for other operations.

        This method provides all of the controls of the pull operations API
        except the ability to set the response size on each request; response
        size (defined by `MaxObjectCount` is the same for all of the request
        operations in the sequence). There are, limitations in that:

          * The filter function does not exist for EnumerateInstances
            so that a request with `FilterQuery` or `FilterQueryLanguage`
            attribute will be rejected if the pull operatons do not exist on the
            target WBEM Server.

          * If `ContinueOnError` is set and the pull operations are not
            supported on the server, the request is rejected.

        An open request may be closed while the iteration process is being
        executed by issuing the iterator close() method.

        If the initial request of the operation sequence succeeds, this method
        returns a Python iterator object so that the instances that are returned
        from the server can be retrieved with iterator expressions.

        Otherwise, this method raises an exception.

        Parameters:

          ClassName (:term:`string` or :class:`~pywbem.CIMClassName`):
            Name of the class to be enumerated (case independent).
            If specified as a :class:`~pywbem.CIMClassName` object, its
            `namespace` attribute will be used as a default namespace as
            described for the `namespace` parameter, and its `host` attribute
            will be ignored.

          namespace (:term:`string`):
            Name of the CIM namespace to be used (case independent).

            If `None`, the namespace of the `ClassName` parameter will be used,
            if specified as a :class:`~pywbem.CIMClassName` object. If that is
            also `None`, the default namespace of the connection will be used.

          FilterQueryLanguage (:term:`string`):
            A string defining the name of the query language
            used for the `FilterQuery` parameter. The DMTF defined language
            (FQL) (:term:`DSP0212`) is specified as 'DMTF:FQL'. If this
            attribute is `True` and the method uses the EnumerateInstances
            option (either `use_pull_operations` == `False` or the server does
            not support pull operations), the method will fail with a
            ValueError.

          FilterQuery (:term:`string`):
            A string defining the query that is to be sent
            to the WBEM server using the query language defined by
            the `FilterQueryLanguage` parameter. If this
            attribute is `True` and the method uses the EnumerateInstances
            option (either `use_pull_operations` == `False` or the server does
            not support pull operations), the method will fail with a
            ValueError

          OperationTimeout (:class:`~pywbem.Uint32`):
            Minimum time in seconds the WBEM Server shall maintain an open
            enumeration session after a previous Open or Pull request is
            sent to the client. Once this timeout time has expired, the
            WBEM server may close the enumeration session.

            * If not `None`, this parameter is sent to the WBEM server as the
              proposed timeout for the enumeration session. A value of 0
              indicates that the server is expected to never time out. The
              server may reject the proposed value, causing a
              :class:`~pywbem.CIMError` to be raised with status code
              :attr:`~pywbem.CIM_ERR_INVALID_OPERATION_TIMEOUT`.
            * If `None`, this parameter is not passed to the WBEM server, and
              causes the server-implemented default timeout to be used.

          ContinueOnError (:class:`py:bool`):
            Indicates to the WBEM server to continue sending responses
            after an error response has been sent.

            * If `True`, the server is to continue sending responses after
              sending an error response. Not all servers support continuation
              on error; a server that does not support it must send an error
              response if `True` was specified, causing
              :class:`~pywbem.CIMError` to be raised with status code
              :attr:`~pywbem.CIM_ERR_CONTINUATION_ON_ERROR_NOT_SUPPORTED`.
            * If `False`, the server is requested to close the enumeration after
              sending an error response.
            * If `None`, this parameter is not passed to the WBEM server, and
              causes the server-implemented default behaviour to be used.
              :term:`DSP0200` defines that the server-implemented default is
              `False`.

            Many WBEM servers do not support this request attribute so that
            its use is NOT recommended except in special cases.

            If this attribute is `True` and the method uses the
            EnumerateInstances option (`use_pull_operations` == `False`
            or the server does not support pull operations), the method will
            fail with a ValueError

          MaxObjectCount (:class:`~pywbem.Uint32`)
            Maximum number of instance paths the WBEM server may return
            for each of the open and pull requests issues as part of the
            execution of this iterator.

            * If positive, the WBEM server is to return no more than the
              specified number of instance paths.
            * Zero is not allowed; it would mean that zero paths
              are to be returned for every request issued.
            * The default is defined as a system config variable.
            * `None` is not allowed.

            The choice of MaxObjectCount is client/server dependent but choices
            between 100 and 1000 typically do not have a significant impact on
            either memory or overall efficiency.

        Keyword Arguments:

          extra :
            Additional keyword arguments are passed as additional operation
            parameters to the WBEM server.
            Note that :term:`DSP0200` does not define any additional parameters
            for this operation.

        Raises:

            Exceptions described in :class:`~pywbem.WBEMConnection`.

        Returns:

          A Python:term:`generator` object. Instance paths can be retrieved
          by iterating through the object. In all cases the instance paths\
          are complete including host and namespace information.

        Example::

            paths_iterator = conn.IterEnumerateInstancePaths('CIM_Blah')
            for path in paths_iterator:
                print('path %s' % path)
        """

        _validateIterCommonParams(MaxObjectCount, OperationTimeout)

        # Common variable for pull result tuple used by pulls and finally:

        pull_result = None

        try:                # try / finally block to allow iter.close()
            if (self._use_enum_path_pull_operations is None or
                    self._use_enum_path_pull_operations):

                try:        # operation try block
                    pull_result = self.OpenEnumerateInstancePaths(
                        ClassName, namespace=namespace,
                        FilterQueryLanguage=FilterQueryLanguage,
                        FilterQuery=FilterQuery,
                        OperationTimeout=OperationTimeout,
                        ContinueOnError=ContinueOnError,
                        MaxObjectCount=MaxObjectCount, **extra)

                    # Open operation succeeded; set has_pull flag
                    self._use_enum_path_pull_operations = True

                    for inst in pull_result.paths:
                        yield inst

                    # Loop to pull while more while eos not returned.
                    while not pull_result.eos:
                        pull_result = self.PullInstancePaths(
                            pull_result.context, MaxObjectCount=MaxObjectCount)

                        for inst in pull_result.paths:
                            yield inst
                    pull_result = None   # clear the pull_result
                    return

                # If NOT_SUPPORTED and first request, set flag and try
                # alternative request operation.
                # If use_pull_operations is True, always raise the exception
                except CIMError as ce:
                    if (self._use_enum_path_pull_operations is None and
                            ce.status_code == CIM_ERR_NOT_SUPPORTED):
                        self._use_enum_path_pull_operations = False
                    else:
                        raise

            # Alternate request if Pull not implemented. This does not allow
            # the FilterQuery or ContinueOnError
            assert self._use_enum_path_pull_operations is False

            if FilterQuery is not None or FilterQueryLanguage is not None:
                raise ValueError('EnumerateInstanceNnames does not support'
                                 ' FilterQuery.')

            if ContinueOnError is not None:
                raise ValueError('EnumerateInstanceNames does not support '
                                 'ContinueOnError.')

            enum_rslt = self.EnumerateInstanceNames(
                ClassName, namespace=namespace, **extra)

            # pylint: disable=unused-variable
            host, port, ssl = parse_url(self.url)

            # get namespace for the operation
            if namespace is None and isinstance(ClassName, CIMClassName):
                namespace = ClassName.namespace
            namespace = self._iparam_namespace_from_namespace(namespace)

            for path in enum_rslt:
                if path.namespace is None:
                    path.namespace = namespace
                if path.host is None:
                    path.host = host

            for inst in enum_rslt:
                yield inst

        # Cleanup if caller closes the iterator before exhausting it
        finally:
            # Cleanup only required if the pull context is open and not complete
            if pull_result is not None and not pull_result.eos:
                self.CloseEnumeration(pull_result.context)
                pull_result = None

    def IterReferenceInstancePaths(self, InstanceName, ResultClass=None,
                                   Role=None,
                                   FilterQueryLanguage=None, FilterQuery=None,
                                   OperationTimeout=None, ContinueOnError=None,
                                   MaxObjectCount=DEFAULT_ITER_MAXOBJECTCOUNT,
                                   **extra):
        # pylint: disable=invalid-name
        """
        A generator function to retrieve references from a WBEM Server.
        This method frees the user of choices between the multiple
        ReferenceNames/ReferenceInstancePaths methods and reduces
        the enumeration to a pythonic iterator idiom.

        **Experimental:** This method is experimental in this release.

        This method performs either the
        :meth:`~pywbem.OpenReferenceInstancePaths operation
        (see :term:`DSP0200`) and :meth:`~pywbem.PullInstancePaths operation or
        the:meth:`~pywbem.WBEMConnection.EnumerateInstances` operation
        (traditional operation) if the WBEM server does not support the
        pull operations. It is an alternative to using these operations
        directly, that automatically uses the pull operations if supported.

        The `use_pull_operations` argument of the
        :class:`~pywbem.WBEMConnection` constructor can be used to
        override that default behavior to either force the use of pull
        operations or to avoid their use.

        The `use_pull_operations` argument of the
        :class:`~pywbem.WBEMConnection` constructor can be used to
        override that default behavior to either force the use of pull
        operations or to avoid their use.

        NOTE: This functionality assumes that pull operations may not be
        supported for all of the pull operation types (i.e. operations whose
        name starts with Open). Even if one `Open...` function is not
        implemented (returns `CIM_ERR_NOT_SUPPORTED`) and that operation is
        used as the first request, the code will try the Open... on other pull
        operation types the first time each type is used.

        This method provides all of the controls of the pull operations API
        except the ability to set the response size on each request; response
        size (defined by `MaxObjectCount` is the same for all of the request
        operations in the sequence). There are, limitations in that:

          * The filter function does not exist for ReferenceNames
            so that a request with `FilterQuery` or `FilterQueryLanguage`
            attribute will be rejected if the pull operatons do not exist on
            the target WBEM Server.

          * If `ContinueOnError` is set and the pull operations are not
            supported on the server, the request is rejected.

        An open request may be closed while the iteration process is being
        executed by issuing the iterator close() method.

        If the initial request of the operation sequence succeeds, this method
        returns a Python iterator object so that the instances that are
        returned from the server can be retrieved with iterator expressions.

        Otherwise, this method raises an exception.

        Parameters:

          InstanceName (:class:`~pywbem.CIMInstanceName`):
            The instance path of the source instance.
            If this object does not specify a namespace, the default namespace
            of the connection is used.
            Its `host` attribute will be ignored.

          ResultClass (:term:`string` or :class:`~pywbem.CIMClassName`):
            Class name of an association class (case independent),
            to filter the result to include only traversals of that association
            class (or subclasses).

            `None` means that no such filtering is peformed.

          Role (:term:`string`):
            Role name (= property name) of the source end (case independent),
            to filter the result to include only traversals from that source
            role.

            `None` means that no such filtering is peformed.

          FilterQueryLanguage (:term:`string`):
            A string defining the name of the query language
            used for the `FilterQuery` parameter. The DMTF defined language
            (FQL) (:term:`DSP0212`) is specified as 'DMTF:FQL'.

          FilterQuery (:term:`string`):
            A string defining the query that is to be sent
            to the WBEM server using the query language defined by
            the `FilterQueryLanguage` parameter.  Not all WBEM
            servers allow FilterQuery filtering for this operation
            because the act of the server filtering requires
            that it generate instances and then discard them.

          OperationTimeout (:class:`~pywbem.Uint32`):
            Minimum time in seconds the WBEM Server shall maintain an open
            enumeration session after a previous Open or Pull request is
            sent to the client. Once this timeout time has expired, the
            WBEM server may close the enumeration session.

            * If not `None`, this parameter is sent to the WBEM server as the
              proposed timeout for the enumeration session. A value of 0
              indicates that the server is expected to never time out. The
              server may reject the proposed value, causing a
              :class:`~pywbem.CIMError` to be raised with status code
              :attr:`~pywbem.CIM_ERR_INVALID_OPERATION_TIMEOUT`.
            * If `None`, this parameter is not passed to the WBEM server, and
              causes the server-implemented default timeout to be used.

          ContinueOnError (:class:`py:bool`):
            Indicates to the WBEM server to continue sending responses
            after an error response has been sent.

            * If `True`, the server is to continue sending responses after
              sending an error response. Not all servers support continuation
              on error; a server that does not support it must send an error
              response if `True` was specified, causing
              :class:`~pywbem.CIMError` to be raised with status code
              :attr:`~pywbem.CIM_ERR_CONTINUATION_ON_ERROR_NOT_SUPPORTED`.
            * If `False`, the server is requested to close the enumeration
              after sending an error response.
            * If `None`, this parameter is not passed to the WBEM server, and
              causes the server-implemented default behaviour to be used.
              :term:`DSP0200` defines that the server-implemented default is
              `False`.

          MaxObjectCount (:class:`~pywbem.Uint32`)
            Maximum number of instances the WBEM server may return
            for this request.

            * If positive, the WBEM server is to return no more than the
              specified number of instances.
            * Zero is not allowed; it would mean that zero instances
              are to be returned for every request issued to the server.
            * If `None`, this parameter is not passed to the WBEM server, and
              causes the server-implemented default behaviour to be used.
              :term:`DSP0200` defines that the server-implemented default is
              to return zero instances.

        Keyword Arguments:

          extra :
            Additional keyword arguments are passed as additional operation
            parameters to the WBEM server.
            Note that :term:`DSP0200` does not define any additional parameters
            for this operation.

        Returns:

          A Python:term:`generator` object. Instances can be retrieved
          by iterating through the object.

        Raises:

            Exceptions described in :class:`~pywbem.WBEMConnection`.

        Example::

            insts_iterator = conn.IterReferencePaths('CIM_Blah')
            for inst in insts_iterator:
                # close if a particular property value found
                if inst.get('thisPropertyName') == 0
                    insts_iterator.close()
                    break
                else:
                    print('instance %s' % inst.tomof())
        """

        _validateIterCommonParams(MaxObjectCount, OperationTimeout)

        # Common variable for pull result tuple used by pulls and finally:
        pull_result = None
        try:                # try / finally block to allow iter.close()
            if (self._use_ref_path_pull_operations is None or
                    self._use_ref_path_pull_operations):

                try:        # Open operation try block
                    pull_result = self.OpenReferenceInstancePaths(
                        InstanceName,
                        ResultClass=ResultClass,
                        Role=Role,
                        FilterQueryLanguage=FilterQueryLanguage,
                        FilterQuery=FilterQuery,
                        OperationTimeout=OperationTimeout,
                        ContinueOnError=ContinueOnError,
                        MaxObjectCount=MaxObjectCount, **extra)

                    # Open operation succeeded; set use_pull flag
                    self._use_ref_path_pull_operations = True

                    for inst in pull_result.paths:
                        yield inst

                    # Loop to pull while more while eos not returned.
                    while not pull_result.eos:
                        pull_result = self.PullInstancePaths(
                            pull_result.context, MaxObjectCount=MaxObjectCount)

                        for inst in pull_result.paths:
                            yield inst
                    pull_result = None   # clear the pull_result
                    return

                # If NOT_SUPPORTED and first request, set flag and try
                # alternative request operation.
                # If use_pull_operations is True, always raise the exception
                except CIMError as ce:
                    if (self._use_ref_path_pull_operations is None and
                            ce.status_code == CIM_ERR_NOT_SUPPORTED):
                        self._use_ref_path_pull_operations = False
                    else:
                        raise

            # Alternate request if Pull not implemented. This does not allow
            # the FilterQuery or ContinueOnError
            assert self._use_ref_path_pull_operations is False

            if FilterQuery is not None or FilterQueryLanguage is not None:
                raise ValueError('ReferenceInstanceNnames does not support'
                                 ' FilterQuery.')

            if ContinueOnError is not None:
                raise ValueError('ReferenceInstanceNames does not support '
                                 'ContinueOnError.')

            enum_rslt = self.ReferenceNames(
                InstanceName,
                ResultClass=ResultClass,
                Role=Role,
                **extra)

            for inst in enum_rslt:
                yield inst

        # Cleanup if caller closess the iterator before exhausting it
        finally:
            # Cleanup only required if the pull context is open and not complete
            if pull_result is not None and not pull_result.eos:
                self.CloseEnumeration(pull_result.context)
                pull_result = None

    def IterReferenceInstances(self, InstanceName, ResultClass=None,
                               Role=None, IncludeQualifiers=None,
                               IncludeClassOrigin=None, PropertyList=None,
                               FilterQueryLanguage=None, FilterQuery=None,
                               OperationTimeout=None, ContinueOnError=None,
                               MaxObjectCount=DEFAULT_ITER_MAXOBJECTCOUNT,
                               **extra):
        # pylint: disable=invalid-name
        """
        A generator function to retrieve instances from a WBEM Server.
        This method frees the user of choices between the multiple
        EnumerateInstances/OpenEnumerateInstance methods and reduces
        the enumeration to a pythonic iterator idiom.

        **Experimental:** This method is experimental in this release.

        This method performs either the
        :meth:`~pywbem.WBEMConnection.OpenReferenceInstances` and
        :meth:`~pywbem.WBEMConnection.PullInstancesWithPath`
        operations (pull operations) or the
        :meth:`~pywbem.WBEMConnection.References` operation
        (traditional operation) if the WBEM server does not support the
        pull operations. It is an alternative to using these operations
        directly, that automatically uses the pull operations if supported.

        The `use_pull_operations` argument of the
        :class:`~pywbem.WBEMConnection` constructor can be used to
        override that default behavior to either force the use of pull
        operations or to avoid their use.

        NOTE: This functionality assumes that pull operations may not be
        supported for all of the pull operation types (i.e. operations whose
        name starts with Open). Even if one `Open...` function is not
        implemented (returns `CIM_ERR_NOT_SUPPORTED`) and that operation is
        used as the first request, the code will try the Open... on other pull
        operation types the first time each type is used.

        This method provides all of the controls of the pull operations API
        except the ability to set the response size on each request; response
        size (defined by `MaxObjectCount` is the same for all of the request
        operations in the sequence). There are, limitations in that:

          * The filter function does not exist for ReferenceNames
            so that a request with `FilterQuery` or `FilterQueryLanguage`
            attribute will be rejected if the pull operatons do not exist on
            the target WBEM Server.

          * If `ContinueOnError` is set and the pull operations are not
            supported on the server, the request is rejected.

        An open request may be closed while the iteration process is being
        executed by issuing the iterator close() method.

        If the initial request of the operation sequence succeeds, this method
        returns a Python iterator object so that the instances that are
        returned from the server can be retrieved with iterator expressions.

        Parameters:

          InstanceName (:class:`~pywbem.CIMInstanceName`):
            The instance path of the source instance.
            If this object does not specify a namespace, the default namespace
            of the connection is used.
            Its `host` attribute will be ignored.

          ResultClass (:term:`string` or :class:`~pywbem.CIMClassName`):
            Class name of an association class (case independent),
            to filter the result to include only traversals of that association
            class (or subclasses).

            `None` means that no such filtering is peformed.

          Role (:term:`string`):
            Role name (= property name) of the source end (case independent),
            to filter the result to include only traversals from that source
            role.

            `None` means that no such filtering is peformed.

          IncludeQualifiers (:class:`py:bool`):
            Indicates that qualifiers are to be included in the returned
            instances (or classes), as follows:

            * If `False`, qualifiers are not included.
            * If `True`, qualifiers are included if the WBEM server implements
              support for this parameter.
            * If `None`, this parameter is not passed to the WBEM server, and
              causes the server-implemented default to be used. :term:`DSP0200`
              defines that the server-implemented default is `False`.

            This parameter has been deprecated in :term:`DSP0200`. Clients
            cannot rely on it being implemented by WBEM servers.

          IncludeClassOrigin (:class:`py:bool`):
            Indicates that class origin information is to be included on each
            property or method in the returned instances (or classes), as
            follows:

            * If `False`, class origin information is not included.
            * If `True`, class origin information is included.
            * If `None`, this parameter is not passed to the WBEM server, and
              causes the server-implemented default to be used. :term:`DSP0200`
              defines that the server-implemented default is `False`.

          PropertyList (:term:`py:iterable` of :term:`string`):
            An iterable specifying the names of the properties to be included
            in the returned instances (or classes) (case independent).
            An empty iterable indicates to include no properties.

            If `None`, all properties are included.

          FilterQueryLanguage (:term:`string`):
            A string defining the name of the query language
            used for the `FilterQuery` parameter. The DMTF defined language
            (FQL) (:term:`DSP0212`) is specified as 'DMTF:FQL'.

          FilterQuery (:term:`string`):
            A string defining the query that is to be sent
            to the WBEM server using the query language defined by
            the `FilterQueryLanguage` parameter.

          OperationTimeout (:class:`~pywbem.Uint32`):
            Minimum time in seconds the WBEM Server shall maintain an open
            enumeration session after a previous Open or Pull request is
            sent to the client. Once this timeout time has expired, the
            WBEM server may close the enumeration session.

            * If not `None`, this parameter is sent to the WBEM server as the
              proposed timeout for the enumeration session. A value of 0
              indicates that the server is expected to never time out. The
              server may reject the proposed value, causing a
              :class:`~pywbem.CIMError` to be raised with status code
              :attr:`~pywbem.CIM_ERR_INVALID_OPERATION_TIMEOUT`.
            * If `None`, this parameter is not passed to the WBEM server, and
              causes the server-implemented default timeout to be used.

          ContinueOnError (:class:`py:bool`):
            Indicates to the WBEM server to continue sending responses
            after an error response has been sent.

            * If `True`, the server is to continue sending responses after
              sending an error response. Not all servers support continuation
              on error; a server that does not support it must send an error
              response if `True` was specified, causing
              :class:`~pywbem.CIMError` to be raised with status code
              :attr:`~pywbem.CIM_ERR_CONTINUATION_ON_ERROR_NOT_SUPPORTED`.
            * If `False`, the server is requested to close the enumeration after
              sending an error response.
            * If `None`, this parameter is not passed to the WBEM server, and
              causes the server-implemented default behaviour to be used.
              :term:`DSP0200` defines that the server-implemented default is
              `False`.

          MaxObjectCount (:class:`~pywbem.Uint32`)
            Maximum number of instances the WBEM server may return
            for this request.

            * If positive, the WBEM server is to return no more than the
              specified number of instances.
            * If zero, the WBEM server is to return no instances. This may
              be used by a client to leave the handling of any returned
              instances to a loop of Pull operations.
            * If `None`, this parameter is not passed to the WBEM server, and
              causes the server-implemented default behaviour to be used.
              :term:`DSP0200` defines that the server-implemented default is
              to return zero instances.

        Keyword Arguments:

          extra :
            Additional keyword arguments are passed as additional operation
            parameters to the WBEM server.
            Note that :term:`DSP0200` does not define any additional parameters
            for this operation.

        Returns:

          A Python:term:`generator` object. Instances can be retrieved
          by iterating through the object.

        Raises:

            Exceptions described in :class:`~pywbem.WBEMConnection`.

        Example::

            insts_iterator = conn.IterReferenceInstances('CIM_Blah.key=1', ...)
            for inst in insts_iterator:
                # close if a particular property value found
                if inst.get('thisPropertyName') == 0
                    insts_iterator.close()
                    break
                else:
                    print('instance %s' % inst.tomof())
        """

        # Must be positive integer gt zero

        _validateIterCommonParams(MaxObjectCount, OperationTimeout)

        # Common variable for pull result tuple used by pulls and finally:
        pull_result = None
        try:                # try / finally block to allow iter.close()
            if (self._use_ref_inst_pull_operations is None or
                    self._use_ref_inst_pull_operations):

                try:        # operation try block
                    pull_result = self.OpenReferenceInstances(
                        InstanceName,
                        ResultClass=ResultClass,
                        Role=Role,
                        IncludeClassOrigin=IncludeClassOrigin,
                        PropertyList=PropertyList,
                        FilterQueryLanguage=FilterQueryLanguage,
                        FilterQuery=FilterQuery,
                        OperationTimeout=OperationTimeout,
                        ContinueOnError=ContinueOnError,
                        MaxObjectCount=MaxObjectCount, **extra)

                    # Open operation succeeded; set has_pull flag
                    self._use_ref_inst_pull_operations = True
                    for inst in pull_result.instances:
                        yield inst

                    # Loop to pull while more while eos not returned.
                    while not pull_result.eos:
                        pull_result = self.PullInstancesWithPath(
                            pull_result.context, MaxObjectCount=MaxObjectCount)
                        for inst in pull_result.instances:
                            yield inst
                    pull_result = None   # clear the pull_result
                    return

                # If NOT_SUPPORTED and first request, set flag and try
                # alternative request operation.
                # If _use_ref_inst_pull_operations is True, always raise
                # the exception
                except CIMError as ce:
                    if (self._use_ref_inst_pull_operations is None and
                            ce.status_code == CIM_ERR_NOT_SUPPORTED):
                        self._use_ref_inst_pull_operations = False
                    else:
                        raise

            # Alternate request if Pull not implemented. This does not allow
            # the FilterQuery or ContinueOnError
            assert self._use_ref_inst_pull_operations is False

            if FilterQuery is not None or FilterQueryLanguage is not None:
                raise ValueError('References does not support'
                                 ' FilterQuery.')

            if ContinueOnError is not None:
                raise ValueError('References does not support '
                                 'ContinueOnError.')

            enum_rslt = self.References(
                InstanceName,
                ResultClass=ResultClass,
                Role=Role,
                IncludeQualifiers=IncludeQualifiers,
                IncludeClassOrigin=IncludeClassOrigin,
                PropertyList=PropertyList, **extra)

            for inst in enum_rslt:
                yield inst

        # Cleanup if caller closes the iterator before exhausting it
        finally:
            # Cleanup only required if the pull context is open and not complete
            if pull_result is not None and not pull_result.eos:
                self.CloseEnumeration(pull_result.context)
                pull_result = None

    def IterAssociatorInstancePaths(self, InstanceName, AssocClass=None,
                                    ResultClass=None,
                                    Role=None, ResultRole=None,
                                    FilterQueryLanguage=None, FilterQuery=None,
                                    OperationTimeout=None, ContinueOnError=None,
                                    MaxObjectCount=DEFAULT_ITER_MAXOBJECTCOUNT,
                                    **extra):
        # pylint: disable=invalid-name
        """
        A generator function to retrieve associators from a WBEM Server.
        This method frees the user of choices between the multiple
        AssociatorNames/AssociatorInstancePaths methods and reduces
        the enumeration to a pythonic iterator idiom.

        **Experimental:** This method is experimental in this release.

        This method performs either the
        :meth:`~pywbem.OpenAssociatorInstancePaths operation
        (see :term:`DSP0200`) and :meth:`~pywbem.PullInstancePaths operation or
        the:meth:`~pywbem.WBEMConnection.AssociatorNames` operation
        (traditional operation) if the WBEM server does not support the
        pull operations. It is an alternative to using these operations
        directly, that automatically uses the pull operations if supported.

        The `use_pull_operations` argument of the
        :class:`~pywbem.WBEMConnection` constructor can be used to
        override that default behavior to either force the use of pull
        operations or to avoid their use.

        The `use_pull_operations` argument of the
        :class:`~pywbem.WBEMConnection` constructor can be used to
        override that default behavior to either force the use of pull
        operations or to avoid their use.

        NOTE: This functionality assumes that pull operations may not be
        supported for all of the pull operation types (i.e. operations whose
        name starts with Open). Even if one `Open...` function is not
        implemented (returns `CIM_ERR_NOT_SUPPORTED`) and that operation is
        used as the first request, the code will try the Open... on other pull
        operation types the first time each type is used.

        This method provides all of the controls of the pull operations API
        except the ability to set the response size on each request; response
        size (defined by `MaxObjectCount` is the same for all of the request
        operations in the sequence). There are, limitations in that:

          * The filter function does not exist for ReferenceNames
            so that a request with `FilterQuery` or `FilterQueryLanguage`
            attribute will be rejected if the pull operatons do not exist on
            the target WBEM Server.

          * If `ContinueOnError` is set and the pull operations are not
            supported on the server, the request is rejected.

        An open request may be closed while the iteration process is being
        executed by issuing the iterator close() method.

        If the initial request of the operation sequence succeeds, this method
        returns a Python iterator object so that the instances that are
        returned from the server can be retrieved with iterator expressions.

        Otherwise, this method raises an exception.

        Parameters:

          InstanceName (:class:`~pywbem.CIMInstanceName`):
            The instance path of the source instance.
            If this object does not specify a namespace, the default namespace
            of the connection is used.
            Its `host` attribute will be ignored.

          AssocClass (:term:`string` or :class:`~pywbem.CIMClassName`):
            Class name of an association class (case independent),
            to filter the result to include only traversals of that association
            class (or subclasses).

            `None` means that no such filtering is peformed.

          ResultClass (:term:`string` or :class:`~pywbem.CIMClassName`):
            Class name of an associated class (case independent),
            to filter the result to include only traversals to that associated
            class (or subclasses).

            `None` means that no such filtering is peformed.

          Role (:term:`string`):
            Role name (= property name) of the source end (case independent),
            to filter the result to include only traversals from that source
            role.

            `None` means that no such filtering is peformed.

          ResultRole (:term:`string`):
            Role name (= property name) of the far end (case independent),
            to filter the result to include only traversals to that far
            role.

            `None` means that no such filtering is peformed.

          FilterQueryLanguage (:term:`string`):
            A string defining the name of the query language
            used for the `FilterQuery` parameter. The DMTF defined language
            (FQL) (:term:`DSP0212`) is specified as 'DMTF:FQL'.

          FilterQuery (:term:`string`):
            A string defining the query that is to be sent
            to the WBEM server using the query language defined by
            the `FilterQueryLanguage` parameter.  Not all WBEM
            servers allow FilterQuery filtering for this operation
            because the act of the server filtering requires
            that it generate instances and then discard them.

          OperationTimeout (:class:`~pywbem.Uint32`):
            Minimum time in seconds the WBEM Server shall maintain an open
            enumeration session after a previous Open or Pull request is
            sent to the client. Once this timeout time has expired, the
            WBEM server may close the enumeration session.

            * If not `None`, this parameter is sent to the WBEM server as the
              proposed timeout for the enumeration session. A value of 0
              indicates that the server is expected to never time out. The
              server may reject the proposed value, causing a
              :class:`~pywbem.CIMError` to be raised with status code
              :attr:`~pywbem.CIM_ERR_INVALID_OPERATION_TIMEOUT`.
            * If `None`, this parameter is not passed to the WBEM server, and
              causes the server-implemented default timeout to be used.

          ContinueOnError (:class:`py:bool`):
            Indicates to the WBEM server to continue sending responses
            after an error response has been sent.

            * If `True`, the server is to continue sending responses after
              sending an error response. Not all servers support continuation
              on error; a server that does not support it must send an error
              response if `True` was specified, causing
              :class:`~pywbem.CIMError` to be raised with status code
              :attr:`~pywbem.CIM_ERR_CONTINUATION_ON_ERROR_NOT_SUPPORTED`.
            * If `False`, the server is requested to close the enumeration
              after sending an error response.
            * If `None`, this parameter is not passed to the WBEM server, and
              causes the server-implemented default behaviour to be used.
              :term:`DSP0200` defines that the server-implemented default is
              `False`.

          MaxObjectCount (:class:`~pywbem.Uint32`)
            Maximum number of instances the WBEM server may return
            for this request.

            * If positive, the WBEM server is to return no more than the
              specified number of instances.
            * Zero is not allowed; it would mean that zero instances
              are to be returned for every request issued to the server.
            * If `None`, this parameter is not passed to the WBEM server, and
              causes the server-implemented default behaviour to be used.
              :term:`DSP0200` defines that the server-implemented default is
              to return zero instances.

        Keyword Arguments:

          extra :
            Additional keyword arguments are passed as additional operation
            parameters to the WBEM server.
            Note that :term:`DSP0200` does not define any additional parameters
            for this operation.

        Returns:

          A Python:term:`generator` object. Instances can be retrieved
          by iterating through the object.

        Raises:

            Exceptions described in :class:`~pywbem.WBEMConnection`.

        Example::

            insts_iterator = conn.IterAssociatorInstancePaths('CIM_Blah')
            for inst in insts_iterator:
                # close if a particular property value found
                if inst.get('thisPropertyName') == 0
                    insts_iterator.close()
                    break
                else:
                    print('instance %s' % inst.tomof())
        """

        _validateIterCommonParams(MaxObjectCount, OperationTimeout)

        # Common variable for pull result tuple used by pulls and finally:
        pull_result = None
        try:                # try / finally block to allow iter.close()
            if (self._use_assoc_path_pull_operations is None or
                    self._use_assoc_path_pull_operations):

                try:        # Open operation try block
                    pull_result = self.OpenAssociatorInstancePaths(
                        InstanceName,
                        AssocClass=AssocClass,
                        ResultClass=ResultClass,
                        Role=Role,
                        ResultRole=ResultRole,
                        FilterQueryLanguage=FilterQueryLanguage,
                        FilterQuery=FilterQuery,
                        OperationTimeout=OperationTimeout,
                        ContinueOnError=ContinueOnError,
                        MaxObjectCount=MaxObjectCount, **extra)

                    # Open operation succeeded; set use_pull flag
                    self._use_assoc_path_pull_operations = True

                    for inst in pull_result.paths:
                        yield inst

                    # Loop to pull while more while eos not returned.
                    while not pull_result.eos:
                        pull_result = self.PullInstancePaths(
                            pull_result.context, MaxObjectCount=MaxObjectCount)

                        for inst in pull_result.paths:
                            yield inst
                    pull_result = None   # clear the pull_result
                    return

                # If NOT_SUPPORTED and first request, set flag and try
                # alternative request operation.
                # If use_pull_operations is True, always raise the exception
                except CIMError as ce:
                    if (self._use_assoc_path_pull_operations is None and
                            ce.status_code == CIM_ERR_NOT_SUPPORTED):
                        self._use_assoc_path_pull_operations = False
                    else:
                        raise

            # Alternate request if Pull not implemented. This does not allow
            # the FilterQuery or ContinueOnError
            assert self._use_assoc_path_pull_operations is False

            if FilterQuery is not None or FilterQueryLanguage is not None:
                raise ValueError('AssociatorNames does not support'
                                 ' FilterQuery.')

            if ContinueOnError is not None:
                raise ValueError('AssociatorNames does not support '
                                 'ContinueOnError.')

            enum_rslt = self.AssociatorNames(
                InstanceName,
                AssocClass=AssocClass,
                ResultClass=ResultClass,
                Role=Role,
                ResultRole=ResultRole, **extra)

            for inst in enum_rslt:
                yield inst

        # Cleanup if caller closess the iterator before exhausting it
        finally:
            # Cleanup only required if the pull context is open and not complete
            if pull_result is not None and not pull_result.eos:
                self.CloseEnumeration(pull_result.context)
                pull_result = None

    def IterAssociatorInstances(self, InstanceName, AssocClass=None,
                                ResultClass=None,
                                Role=None, ResultRole=None,
                                IncludeQualifiers=None,
                                IncludeClassOrigin=None, PropertyList=None,
                                FilterQueryLanguage=None, FilterQuery=None,
                                OperationTimeout=None, ContinueOnError=None,
                                MaxObjectCount=DEFAULT_ITER_MAXOBJECTCOUNT,
                                **extra):
        # pylint: disable=invalid-name
        """
        A generator function to retrieve instances from a WBEM Server.
        This method frees the user of choices between the multiple
        Associators/OpenAssociatorInstance methods and reduces
        the enumeration to a pythonic iterator idiom.

        **Experimental:** This method is experimental in this release.

        This method performs either the
        :meth:`~pywbem.WBEMConnection.OpenAssociatorInstances` and
        :meth:`~pywbem.WBEMConnection.PullInstancesWithPath`
        operations (pull operations) or the
        :meth:`~pywbem.WBEMConnection.Associators` operation
        (traditional operation) if the WBEM server does not support the
        pull operations. It is an alternative to using these operations
        directly, that automatically uses the pull operations if supported.

        The `use_pull_operations` argument of the
        :class:`~pywbem.WBEMConnection` constructor can be used to
        override that default behavior to either force the use of pull
        operations or to avoid their use.

        NOTE: This functionality assumes that pull operations may not be
        supported for all of the pull operation types (i.e. operations whose
        name starts with Open). Even if one `Open...` function is not
        implemented (returns `CIM_ERR_NOT_SUPPORTED`) and that operation is
        used as the first request, the code will try the Open... on other pull
        operation types the first time each type is used.

        This method provides all of the controls of the pull operations API
        except the ability to set the response size on each request; response
        size (defined by `MaxObjectCount` is the same for all of the request
        operations in the sequence). There are, limitations in that:

          * The filter function does not exist for ReferenceNames
            so that a request with `FilterQuery` or `FilterQueryLanguage`
            attribute will be rejected if the pull operatons do not exist on
            the target WBEM Server.

          * If `ContinueOnError` is set and the pull operations are not
            supported on the server, the request is rejected.

        An open request may be closed while the iteration process is being
        executed by issuing the iterator close() method.

        If the initial request of the operation sequence succeeds, this method
        returns a Python iterator object so that the instances that are
        returned from the server can be retrieved with iterator expressions.

        Parameters:

          InstanceName (:class:`~pywbem.CIMInstanceName`):
            The instance path of the source instance.
            If this object does not specify a namespace, the default namespace
            of the connection is used.
            Its `host` attribute will be ignored.

           AssocClass (:term:`string` or :class:`~pywbem.CIMClassName`):
            Class name of an association class (case independent),
            to filter the result to include only traversals of that association
            class (or subclasses).

            `None` means that no such filtering is peformed.

          ResultClass (:term:`string` or :class:`~pywbem.CIMClassName`):
            Class name of an associated class (case independent),
            to filter the result to include only traversals to that associated
            class (or subclasses).

            `None` means that no such filtering is peformed.

          Role (:term:`string`):
            Role name (= property name) of the source end (case independent),
            to filter the result to include only traversals from that source
            role.

            `None` means that no such filtering is peformed.

          ResultRole (:term:`string`):
            Role name (= property name) of the far end (case independent),
            to filter the result to include only traversals to that far
            role.

            `None` means that no such filtering is peformed.

          IncludeQualifiers (:class:`py:bool`):
            Indicates that qualifiers are to be included in the returned
            instances (or classes), as follows:

            * If `False`, qualifiers are not included.
            * If `True`, qualifiers are included if the WBEM server implements
              support for this parameter.
            * If `None`, this parameter is not passed to the WBEM server, and
              causes the server-implemented default to be used. :term:`DSP0200`
              defines that the server-implemented default is `False`.

            This parameter has been deprecated in :term:`DSP0200`. Clients
            cannot rely on it being implemented by WBEM servers.

          IncludeClassOrigin (:class:`py:bool`):
            Indicates that class origin information is to be included on each
            property or method in the returned instances (or classes), as
            follows:

            * If `False`, class origin information is not included.
            * If `True`, class origin information is included.
            * If `None`, this parameter is not passed to the WBEM server, and
              causes the server-implemented default to be used. :term:`DSP0200`
              defines that the server-implemented default is `False`.

          PropertyList (:term:`py:iterable` of :term:`string`):
            An iterable specifying the names of the properties to be included
            in the returned instances (or classes) (case independent).
            An empty iterable indicates to include no properties.

            If `None`, all properties are included.

          FilterQueryLanguage (:term:`string`):
            A string defining the name of the query language
            used for the `FilterQuery` parameter. The DMTF defined language
            (FQL) (:term:`DSP0212`) is specified as 'DMTF:FQL'.

          FilterQuery (:term:`string`):
            A string defining the query that is to be sent
            to the WBEM server using the query language defined by
            the `FilterQueryLanguage` parameter.

          OperationTimeout (:class:`~pywbem.Uint32`):
            Minimum time in seconds the WBEM Server shall maintain an open
            enumeration session after a previous Open or Pull request is
            sent to the client. Once this timeout time has expired, the
            WBEM server may close the enumeration session.

            * If not `None`, this parameter is sent to the WBEM server as the
              proposed timeout for the enumeration session. A value of 0
              indicates that the server is expected to never time out. The
              server may reject the proposed value, causing a
              :class:`~pywbem.CIMError` to be raised with status code
              :attr:`~pywbem.CIM_ERR_INVALID_OPERATION_TIMEOUT`.
            * If `None`, this parameter is not passed to the WBEM server, and
              causes the server-implemented default timeout to be used.

          ContinueOnError (:class:`py:bool`):
            Indicates to the WBEM server to continue sending responses
            after an error response has been sent.

            * If `True`, the server is to continue sending responses after
              sending an error response. Not all servers support continuation
              on error; a server that does not support it must send an error
              response if `True` was specified, causing
              :class:`~pywbem.CIMError` to be raised with status code
              :attr:`~pywbem.CIM_ERR_CONTINUATION_ON_ERROR_NOT_SUPPORTED`.
            * If `False`, the server is requested to close the enumeration after
              sending an error response.
            * If `None`, this parameter is not passed to the WBEM server, and
              causes the server-implemented default behaviour to be used.
              :term:`DSP0200` defines that the server-implemented default is
              `False`.

          MaxObjectCount (:class:`~pywbem.Uint32`)
            Maximum number of instances the WBEM server may return
            for this request.

            * If positive, the WBEM server is to return no more than the
              specified number of instances.
            * If zero, the WBEM server is to return no instances. This may
              be used by a client to leave the handling of any returned
              instances to a loop of Pull operations.
            * If `None`, this parameter is not passed to the WBEM server, and
              causes the server-implemented default behaviour to be used.
              :term:`DSP0200` defines that the server-implemented default is
              to return zero instances.

        Keyword Arguments:

          extra :
            Additional keyword arguments are passed as additional operation
            parameters to the WBEM server.
            Note that :term:`DSP0200` does not define any additional parameters
            for this operation.

        Returns:

          A Python:term:`generator` object. Instances can be retrieved
          by iterating through the object.

        Raises:

            Exceptions described in :class:`~pywbem.WBEMConnection`.

        Example::

            insts_iterator = conn.IterAssociatorInstances('CIM_Blah.key=1',...)
            for inst in insts_iterator:
                # close if a particular property value found
                if inst.get('thisPropertyName') == 0
                    insts_iterator.close()
                    break
                else:
                    print('instance %s' % inst.tomof())
        """

        # Must be positive integer gt zero

        _validateIterCommonParams(MaxObjectCount, OperationTimeout)

        # Common variable for pull result tuple used by pulls and finally:

        pull_result = None
        try:                # try / finally block to allow iter.close()
            if (self._use_assoc_inst_pull_operations is None or
                    self._use_assoc_inst_pull_operations):

                try:        # operation try block
                    pull_result = self.OpenAssociatorInstances(
                        InstanceName,
                        AssocClass=AssocClass,
                        ResultClass=ResultClass,
                        Role=Role,
                        ResultRole=ResultRole,
                        IncludeClassOrigin=IncludeClassOrigin,
                        PropertyList=PropertyList,
                        FilterQueryLanguage=FilterQueryLanguage,
                        FilterQuery=FilterQuery,
                        OperationTimeout=OperationTimeout,
                        ContinueOnError=ContinueOnError,
                        MaxObjectCount=MaxObjectCount, **extra)

                    # Open operation succeeded; set has_pull flag
                    self._use_assoc_inst_pull_operations = True

                    for inst in pull_result.instances:
                        yield inst

                    # Loop to pull while more while eos not returned.
                    while not pull_result.eos:
                        pull_result = self.PullInstancesWithPath(
                            pull_result.context, MaxObjectCount=MaxObjectCount)

                        for inst in pull_result.instances:
                            yield inst
                    pull_result = None   # clear the pull_result
                    return

                # If NOT_SUPPORTED and first request, set flag and try
                # alternative request operation.
                # If _use_assoc_inst_pull_operations is True, always raise
                # the exception
                except CIMError as ce:
                    if (self._use_assoc_inst_pull_operations is None and
                            ce.status_code == CIM_ERR_NOT_SUPPORTED):
                        self._use_assoc_inst_pull_operations = False
                    else:
                        raise

            # Alternate request if Pull not implemented. This does not allow
            # the FilterQuery or ContinueOnError
            assert self._use_assoc_inst_pull_operations is False

            if FilterQuery is not None or FilterQueryLanguage is not None:
                raise ValueError('Associators does not support'
                                 ' FilterQuery.')

            if ContinueOnError is not None:
                raise ValueError('Associators does not support '
                                 'ContinueOnError.')

            enum_rslt = self.Associators(
                InstanceName,
                AssocClass=AssocClass,
                ResultClass=ResultClass,
                Role=Role,
                ResultRole=ResultRole,
                IncludeQualifiers=IncludeQualifiers,
                IncludeClassOrigin=IncludeClassOrigin,
                PropertyList=PropertyList, **extra)

            for inst in enum_rslt:
                yield inst

        # Cleanup if caller closes the iterator before exhausting it
        finally:
            # Cleanup only required if the pull context is open and not complete
            if pull_result is not None and not pull_result.eos:
                self.CloseEnumeration(pull_result.context)
                pull_result = None

    def IterQueryInstances(self, FilterQueryLanguage, FilterQuery,
                           namespace=None, ReturnQueryResultClass=None,
                           OperationTimeout=None, ContinueOnError=None,
                           MaxObjectCount=DEFAULT_ITER_MAXOBJECTCOUNT,
                           **extra):
        """
        A generator function to retrieve instances from a WBEM Server.
        This method frees the user of choices between the multiple
        ExecQuery/OpenQueryInstances methods and reduces
        the enumeration to a pythonic iterator idiom.

        **Experimental:** This method is experimental in this release.

        This method performs either the
        :meth:`~pywbem.WBEMConnection.OpenQueryInstances` and
        :meth:`~pywbem.WBEMConnection.PullInstances`
        operations (pull operations) or the
        :meth:`~pywbem.WBEMConnection.ExecQuery` operation
        (traditional operation) if the WBEM server does not support the
        pull operations. It is an alternative to using these operations
        directly, that automatically uses the pull operations if supported.

        The `use_pull_operations` argument of the
        :class:`~pywbem.WBEMConnection` constructor can be used to
        override that default behavior to either force the use of pull
        operations or to avoid their use.

        NOTE: This functionality assumes that pull operations may not be
        supported for all of the pull operation types (i.e. operations whose
        name starts with Open). Even if one `Open...` function is not
        implemented (returns `CIM_ERR_NOT_SUPPORTED`) and that operation is
        used as the first request, the code will try the Open... on other pull
        operation types the first time each type is used.

        This method provides all of the controls of the pull operations API
        except the ability to set the response size on each request; response
        size (defined by `MaxObjectCount` is the same for all of the request
        operations in the sequence). There are, limitations in that:

          * The filter function does not exist for EnumerateInstances
            so that a request with `FilterQuery` or `FilterQueryLanguage`
            attribute will be rejected if the pull operatons do not exist on
            the target WBEM Server.

          * If `ContinueOnError` is set and the pull operations are not
            supported on the server, the request is rejected.

        An open request may be closed while the iteration process is being
        executed by issuing the iterator close() method.

        If the initial request of the operation sequence succeeds, this method
        returns a Python iterator object so that the instances that are
        returned from the server can be retrieved with iterator expressions.

        Otherwise, this method raises an exception.

        Parameters:

          QueryLanguage (:term:`string`):
            Name of the query language used in the `Query` parameter, e.g.
            "DMTF:CQL" for CIM Query Language, and "WQL" for WBEM Query
            Language. "DMTF:FQL" is not a valid query language for this
            request.

          Query (:term:`string`):
            Query string in the query language specified in the `QueryLanguage`
            parameter.

          namespace (:term:`string`):
            Name of the CIM namespace to be used (case independent).

            If `None`, the default namespace of the connection object will be
            used.

          ReturnQueryResultClass  (:class:`py:bool`):
            Controls whether a class definition is returned.

          OperationTimeout (:class:`~pywbem.Uint32`):
            Minimum time in seconds the WBEM Server shall maintain an open
            enumeration session after a previous Open or Pull request is
            sent to the client. Once this timeout time has expired, the
            WBEM server may close the enumeration session.

            * If not `None`, this parameter is sent to the WBEM server as the
              proposed timeout for the enumeration session. A value of 0
              indicates that the server is expected to never time out. The
              server may reject the proposed value, causing a
              :class:`~pywbem.CIMError` to be raised with status code
              :attr:`~pywbem.CIM_ERR_INVALID_OPERATION_TIMEOUT`.
            * If `None`, this parameter is not passed to the WBEM server, and
              causes the server-implemented default timeout to be used.

          ContinueOnError (:class:`py:bool`):
            Indicates to the WBEM server to continue sending responses
            after an error response has been sent.

            * If `True`, the server is to continue sending responses after
              sending an error response. Not all servers support continuation
              on error; a server that does not support it must send an error
              response if `True` was specified, causing
              :class:`~pywbem.CIMError` to be raised with status code
              :attr:`~pywbem.CIM_ERR_CONTINUATION_ON_ERROR_NOT_SUPPORTED`.
            * If `False`, the server is requested to close the enumeration after
              sending an error response.
            * If `None`, this parameter is not passed to the WBEM server, and
              causes the server-implemented default behaviour to be used.
              :term:`DSP0200` defines that the server-implemented default is
              `False`.

          MaxObjectCount (:class:`~pywbem.Uint32`)
            Maximum number of instances the WBEM server may return
            for this request.

            * If positive, the WBEM server is to return no more than the
              specified number of instances.
            * If zero, the WBEM server is to return no instances. This may
              be used by a client to leave the handling of any returned
              instances to a loop of Pull operations.
            * If `None`, this parameter is not passed to the WBEM server, and
              causes the server-implemented default behaviour to be used.
              :term:`DSP0200` defines that the server-implemented default is
              to return zero instances.

        Keyword Arguments:

          extra :
            Additional keyword arguments are passed as additional operation
            parameters to the WBEM server.
            Note that :term:`DSP0200` does not define any additional parameters
            for this operation.

        Returns:

          A Python:term:`generator` object. Instances can be retrieved
          by iterating through the object.
          An Instance of the nexted class IterQueryInstancesReturn that
          contains two properties:

          query_result_class: If a result class was requested from by the
          call to InterQueryInstances and one was returned, the CIMClass
          representing this class is returned.  Otherwise, None is returned

          generator: That defines a generator for the instances returned from
          whichever lower level function is called. The instances are
          accessed using this generator (ex. for inst in rtn.generator:)

        Raises:

            Exceptions described in :class:`~pywbem.WBEMConnection`.

        Example:
            result = conn.IterQueryInstances('DMTF:CQL',
                'SELECT FROM * where pl > 2')
            for inst in result.generator:
                print('instance %s' % inst.tomof())

        Raises:

            Exceptions described in :class:`~pywbem.WBEMConnection`.
        """
        class IterQueryInstancesReturn(object):
            """
            Nested class that defines the return from IterQueryInstances.

            This includes two methods that allow returning both the
            query class result and the generator definition.
            """
            def __init__(self, instances, query_result_class=None):
                self._query_result_class = query_result_class
                self.instances = instances

            @property
            def query_result_class(self):
                """Return with the query_result class or None."""
                return self._query_result_class

            @property
            def generator(self):
                """
                Method to provide the python generator.
                """
                for inst in self.instances:
                    yield inst

        _validateIterCommonParams(MaxObjectCount, OperationTimeout)

        # Common variable for pull result tuple used by pulls and finally:
        pull_result = None
        try:                # try / finally block to allow iter.close()
            _instances = []
            if (self._use_query_pull_operations is None or
                    self._use_query_pull_operations):

                try:        # operation try block
                    pull_result = self.OpenQueryInstances(
                        FilterQueryLanguage=FilterQueryLanguage,
                        FilterQuery=FilterQuery,
                        namespace=namespace,
                        ReturnQueryResultClass=ReturnQueryResultClass,
                        OperationTimeout=OperationTimeout,
                        ContinueOnError=ContinueOnError,
                        MaxObjectCount=MaxObjectCount, **extra)

                    # Open operation succeeded; set has_pull flag
                    self._use_query_pull_operations = True

                    _instances = pull_result.instances

                    qrc = None if ReturnQueryResultClass else \
                        pull_result.query_result_class

                    while not pull_result.eos:
                        pull_result = self.PullInstances(
                            pull_result.context, MaxObjectCount=MaxObjectCount)
                        _instances.extend(pull_result.instances)
                    rtn = IterQueryInstancesReturn(_instances,
                                                   query_result_class=qrc)
                    pull_result = None   # clear the pull_result
                    return rtn

                # If NOT_SUPPORTED and first request, set flag and try
                # alternative request operation.
                # If _use_query_pull_operations is True, always raise
                # the exception
                except CIMError as ce:
                    if self._use_query_pull_operations is None and \
                       ce.status_code == CIM_ERR_NOT_SUPPORTED:
                        self._use_query_pull_operations = False
                    else:
                        raise

            # Alternate request if Pull not implemented. This does not allow
            # the ContinueOnError or ReturnQueryResultClass
            assert self._use_query_pull_operations is False

            if ReturnQueryResultClass is not None:
                raise ValueError('ExecQuery does not support'
                                 ' ReturnQueryResultClass.')

            if ContinueOnError is not None:
                raise ValueError('ExecQuery does not support '
                                 'ContinueOnError.')

            _instances = self.ExecQuery(
                QueryLanguage=FilterQueryLanguage,
                Query=FilterQuery, **extra)

            rtn = IterQueryInstancesReturn(_instances)
            return rtn

        # Cleanup if caller closes the iterator before exhausting it
        finally:
            # Cleanup only required if the pull context is open and not complete
            if pull_result is not None and not pull_result.eos:
                self.CloseEnumeration(pull_result.context)
                pull_result = None

    def OpenEnumerateInstancePaths(self, ClassName, namespace=None,
                                   FilterQueryLanguage=None, FilterQuery=None,
                                   OperationTimeout=None, ContinueOnError=None,
                                   MaxObjectCount=None, **extra):
        # pylint: disable=invalid-name

        """
        Open an enumeration session to enumerate the instance paths of
        instances of a class (including instances of its subclasses) in
        a namespace.

        This method performs the OpenEnumerateInstancePaths operation
        (see :term:`DSP0200`). See :ref:`WBEM operations` for a list of all
        methods performing such operations.

        If the operation succeeds, this method returns status on the
        enumeration session and optionally instance paths.
        Otherwise, this method raises an exception.

        Use :meth:`~pywbem.WBEMConnection.PullInstancePaths` request to
        retrieve the next set of instance paths
        or the :meth:`~pywbem.WBEMConnection.CloseEnumeration`
        request to close the enumeration session early.

        Parameters:

          ClassName (:term:`string` or :class:`~pywbem.CIMClassName`):
            Name of the class to be enumerated (case independent).
            If specified as a :class:`~pywbem.CIMClassName` object, its
            `namespace` attribute will be used as a default namespace as
            described for the `namespace` parameter, and its `host` attribute
            will be ignored.

          namespace (:term:`string`):
            Name of the CIM namespace to be used (case independent).

            If `None`, the namespace of the `ClassName` parameter will be used,
            if specified as a :class:`~pywbem.CIMClassName` object. If that is
            also `None`, the default namespace of the connection will be used.

          FilterQueryLanguage (:term:`string`):
            A string defining the name of the query language
            used for the `FilterQuery` parameter. The DMTF defined language
            (FQL) (:term:`DSP0212`) is specified as 'DMTF:FQL'.

          FilterQuery (:term:`string`):
            A string defining the query that is to be sent
            to the WBEM server using the query language defined by
            the `FilterQueryLanguage` parameter. Not all WBEM
            servers allow FilterQuery filtering for this operation
            (i.e. return the CIM_ERR_NOT_SUPPORTED exception when filtering
            is specified) because the act of the server filtering
            requires that it generate instances and then discard them.

          OperationTimeout (:class:`~pywbem.Uint32`):
            Minimum time in seconds the WBEM Server shall maintain an open
            enumeration session after a previous Open or Pull request is
            sent to the client. Once this timeout time has expired, the
            WBEM server may close the enumeration session.

            * If not `None`, this parameter is sent to the WBEM server as the
              proposed timeout for the enumeration session. A value of 0
              indicates that the server is expected to never time out. The
              server may reject the proposed value, causing a
              :class:`~pywbem.CIMError` to be raised with status code
              :attr:`~pywbem.CIM_ERR_INVALID_OPERATION_TIMEOUT`.
            * If `None`, this parameter is not passed to the WBEM server, and
              causes the server-implemented default timeout to be used.

          ContinueOnError (:class:`py:bool`):
            Indicates to the WBEM server to continue sending responses
            after an error response has been sent.

            * If `True`, the server is to continue sending responses after
              sending an error response. Not all servers support continuation
              on error; a server that does not support it must send an error
              response if `True` was specified, causing
              :class:`~pywbem.CIMError` to be raised with status code
              :attr:`~pywbem.CIM_ERR_CONTINUATION_ON_ERROR_NOT_SUPPORTED`.
            * If `False`, the server is requested to close the enumeration after
              sending an error response.
            * If `None`, this parameter is not passed to the WBEM server, and
              causes the server-implemented default behaviour to be used.
              :term:`DSP0200` defines that the server-implemented default is
              `False`.

          MaxObjectCount (:class:`~pywbem.Uint32`)
            Maximum number of instances the WBEM server may return
            for this request.

            * If positive, the WBEM server is to return no more than the
              specified number of instances.
            * If zero, the WBEM server is to return no instances. This may
              be used by a client to leave the handling of any returned
              instances to a loop of Pull operations.
            * If `None`, this parameter is not passed to the WBEM server, and
              causes the server-implemented default behaviour to be used.
              :term:`DSP0200` defines that the server-implemented default is
              to return zero instances.

        Keyword Arguments:

          extra :
            Additional keyword arguments are passed as additional operation
            parameters to the WBEM server.
            Note that :term:`DSP0200` does not define any additional parameters
            for this operation.

        Returns:

            A :class:`py:namedtuple` object containing the following named
            items:

            * **paths** (:class:`py:list` of :class:`~pywbem.CIMInstanceName`):
              Representations of the initial set of enumerated instance paths,
              with their attributes set as follows:

              * `classname`: Name of the creation class of the instance.
              * `keybindings`: Keybindings of the instance.
              * `namespace`: Name of the CIM namespace containing the instance.
              * `host`: Host and optionally port of the WBEM server containing
                the CIM namespace.

            * **eos** (:class:`py:bool`):
              Indicates whether the enumeration session is exhausted
              after returning the initial set of enumerated instances.

              - If `True`, the enumeration session is exhausted, and the
                server has closed the enumeration session.
              - If `False`, the enumeration session is not exhausted.

            * **context** (:class:`py:tuple` of server_context, namespace):
              Identifies the opened enumeration session. The client must
              provide this value for subsequent operations on this
              enumeration session.

              The tuple items are:

              * server_context (:term:`string`):
                Enumeration context string returned by the server if
                the session is not exhausted, or `None` otherwise. This string
                is opaque for the client.
              * namespace (:term:`string`):
                Name of the CIM namespace that was used for this operation.

              NOTE: This inner tuple hides the need for a CIM namespace
              on subsequent operations in the enumeration session. CIM
              operations always require target namespace, but it never
              makes sense to specify a different one in subsequent
              operations on the same enumeration session.

        Raises:

            Exceptions described in :class:`~pywbem.WBEMConnection`.
        """

        if self.operation_recorder:
            self.operation_recorder.reset()
            self.operation_recorder.stage_pywbem_args(
                method='OpenEnumerateInstancePaths',
                ClassName=ClassName,
                namespace=namespace,
                FilterQueryLanguage=FilterQueryLanguage,
                FilterQuery=FilterQuery,
                OperationTimeout=OperationTimeout,
                ContinueOnError=ContinueOnError,
                MaxObjectCount=MaxObjectCount,
                **extra)

        try:

            if namespace is None and isinstance(ClassName, CIMClassName):
                namespace = ClassName.namespace
            namespace = self._iparam_namespace_from_namespace(namespace)
            classname = self._iparam_classname(ClassName)

            result = self._imethodcall(
                'OpenEnumerateInstancePaths',
                namespace,
                ClassName=classname,
                FilterQueryLanguage=FilterQueryLanguage,
                FilterQuery=FilterQuery,
                OperationTimeout=OperationTimeout,
                ContinueOnError=ContinueOnError,
                MaxObjectCount=MaxObjectCount,
                response_params_rqd=True,
                **extra)

            result_tuple = pull_path_result_tuple(
                *self._get_rslt_params(result, namespace))

        except Exception as exc:
            if self.operation_recorder:
                self.operation_recorder.stage_pywbem_result(None, exc)
                self.operation_recorder.record_staged()
            raise
        else:
            if self.operation_recorder:
                self.operation_recorder.stage_pywbem_result(result_tuple, None)
                self.operation_recorder.record_staged()
            return result_tuple

    def OpenEnumerateInstances(self, ClassName, namespace=None, LocalOnly=None,
                               DeepInheritance=None, IncludeQualifiers=None,
                               IncludeClassOrigin=None, PropertyList=None,
                               FilterQueryLanguage=None, FilterQuery=None,
                               OperationTimeout=None, ContinueOnError=None,
                               MaxObjectCount=None, **extra):
        # pylint: disable=invalid-name
        """
        Open an enumeration session to get instances of a class
        (including instances of its subclasses).

        This method performs the OpenEnumerateInstances operation
        (see :term:`DSP0200`). See :ref:`WBEM operations` for a list of all
        methods performing such operations.

        If the operation succeeds, this method returns enumeration session
        status and optionally instances.
        Otherwise, this method raises an exception.

        Use :meth:`~pywbem.WBEMConnection.PullInstances` request to
        retrieve the next set of instance paths
        or the :meth:`~pywbem.WBEMConnection.CloseEnumeration`
        request to close the enumeration session early.

        Parameters:

          ClassName (:term:`string` or :class:`~pywbem.CIMClassName`):
            Name of the class to be enumerated (case independent).
            If specified as a :class:`~pywbem.CIMClassName` object, its
            `namespace` attribute will be used as a default namespace as
            described for the `namespace` parameter, and its `host` attribute
            will be ignored.

          namespace (:term:`string`):
            Name of the CIM namespace to be used (case independent).

            If `None`, the namespace of the `ClassName` parameter will be used,
            if specified as a :class:`~pywbem.CIMClassName` object. If that is
            also `None`, the default namespace of the connection will be used.

          LocalOnly (:class:`py:bool`):
            Controls the exclusion of inherited properties from the returned
            instances, as follows:

            * If `False`, inherited properties are not excluded.
            * If `True`, inherited properties are basically excluded, but the
              behavior may be WBEM server specific.
            * If `None`, this parameter is not passed to the WBEM server, and
              causes the server-implemented default to be used. :term:`DSP0200`
              defines that the server-implemented default is `True`.

            This parameter has been deprecated in :term:`DSP0200` and should be
            set to `False` by the caller.

          DeepInheritance (:class:`py:bool`):
            Indicates that properties added by subclasses of the specified
            class are to be included in the returned instances, as follows:

            * If `False`, properties added by subclasses are not included.
            * If `True`, properties added by subclasses are included.
            * If `None`, this parameter is not passed to the WBEM server, and
              causes the server-implemented default to be used. :term:`DSP0200`
              defines that the server-implemented default is `True`.

            Note, the semantics of the `DeepInheritance` parameter in
            :meth:`~pywbem.WBEMConnection.EnumerateClasses` and
            :meth:`~pywbem.WBEMConnection.EnumerateClassNames`
            is different.

          IncludeQualifiers (:class:`py:bool`):
            Indicates that qualifiers are to be included in the returned
            instance, as follows:

            * If `False`, qualifiers are not included.
            * If `True`, qualifiers are included if the WBEM server implements
              support for this parameter.
            * If `None`, this parameter is not passed to the WBEM server, and
              causes the server-implemented default to be used. :term:`DSP0200`
              defines that the server-implemented default is `False`.

            This parameter has been deprecated in :term:`DSP0200`. Clients
            cannot rely on it being implemented by WBEM servers.

          IncludeClassOrigin (:class:`py:bool`):
            Indicates that class origin information is to be included on each
            property in the returned instances, as follows:

            * If `False`, class origin information is not included.
            * If `True`, class origin information is included.
            * If `None`, this parameter is not passed to the WBEM server, and
              causes the server-implemented default to be used. :term:`DSP0200`
              defines that the server-implemented default is `False`.

          PropertyList (:term:`py:iterable` of :term:`string`):
            An iterable specifying the names of the properties to be
            included in the returned instances (case independent).

            An empty iterable indicates to include no properties.

            If `None`, all properties are included.

          FilterQueryLanguage (:term:`string`):
            A string defining the name of the query language
            used for the `FilterQuery` parameter. The DMTF defined language
            (FQL) (:term:`DSP0212`) is specified as 'DMTF:FQL'.

          FilterQuery (:term:`string`):
            A string defining the query that is to be sent
            to the WBEM server using the query language defined by
            the `FilterQueryLanguage` parameter.

          OperationTimeout (:class:`~pywbem.Uint32`):
            Minimum time in seconds the WBEM Server shall maintain an open
            enumeration session after a previous Open or Pull request is
            sent to the client. Once this timeout time has expired, the
            WBEM server may close the enumeration session.

            * If not `None`, this parameter is sent to the WBEM server as the
              proposed timeout for the enumeration session. A value of 0
              indicates that the server is expected to never time out. The
              server may reject the proposed value, causing a
              :class:`~pywbem.CIMError` to be raised with status code
              :attr:`~pywbem.CIM_ERR_INVALID_OPERATION_TIMEOUT`.
            * If `None`, this parameter is not passed to the WBEM server, and
              causes the server-implemented default timeout to be used.

          ContinueOnError (:class:`py:bool`):
            Indicates to the WBEM server to continue sending responses
            after an error response has been sent.

            * If `True`, the server is to continue sending responses after
              sending an error response. Not all servers support continuation
              on error; a server that does not support it must send an error
              response if `True` was specified, causing
              :class:`~pywbem.CIMError` to be raised with status code
              :attr:`~pywbem.CIM_ERR_CONTINUATION_ON_ERROR_NOT_SUPPORTED`.
            * If `False`, the server is requested to close the enumeration after
              sending an error response.
            * If `None`, this parameter is not passed to the WBEM server, and
              causes the server-implemented default behaviour to be used.
              :term:`DSP0200` defines that the server-implemented default is
              `False`.

          MaxObjectCount (:class:`~pywbem.Uint32`)
            Maximum number of instances the WBEM server may return
            for this request.

            * If positive, the WBEM server is to return no more than the
              specified number of instances.
            * If zero, the WBEM server is to return no instances. This may
              be used by a client to leave the handling of any returned
              instances to a loop of Pull operations.
            * If `None`, this parameter is not passed to the WBEM server, and
              causes the server-implemented default behaviour to be used.
              :term:`DSP0200` defines that the server-implemented default is
              to return zero instances.

        Keyword Arguments:

          extra :
            Additional keyword arguments are passed as additional operation
            parameters to the WBEM server.
            Note that :term:`DSP0200` does not define any additional parameters
            for this operation.

        Returns:

            A :class:`py:namedtuple` object containing the following named
            items:

            * **instances** (:class:`py:list` of :class:`~pywbem.CIMInstance`):
              Representations of the initial set of enumerated instances.

              The `path` attribute of each :class:`~pywbem.CIMInstance`
              object is a :class:`~pywbem.CIMInstanceName` object with its
              attributes set as follows:

              * `classname`: Name of the creation class of the instance.
              * `keybindings`: Keybindings of the instance.
              * `namespace`: Name of the CIM namespace containing the instance.
              * `host`: Host and optionally port of the WBEM server containing
                the CIM namespace.

            * **eos** (:class:`py:bool`):
              Indicates whether the enumeration session is exhausted
              after returning the initial set of enumerated instances.

              - If `True`, the enumeration session is exhausted, and the
                server has closed the enumeration session.
              - If `False`, the enumeration session is not exhausted.

            * **context** (:class:`py:tuple` of server_context, namespace):
              Identifies the opened enumeration session. The client must
              provide this value for subsequent operations on this
              enumeration session.

              The tuple items are:

              * server_context (:term:`string`):
                Enumeration context string returned by the server if
                the session is not exhausted, or `None` otherwise. This string
                is opaque for the client.
              * namespace (:term:`string`):
                Name of the CIM namespace that was used for this operation.

              NOTE: This inner tuple hides the need for a CIM namespace
              on subsequent operations in the enumeration session. CIM
              operations always require target namespace, but it never
              makes sense to specify a different one in subsequent
              operations on the same enumeration session.

        Raises:

            Exceptions described in :class:`~pywbem.WBEMConnection`.
        """  # noqa: E501

        if self.operation_recorder:
            self.operation_recorder.reset()
            self.operation_recorder.stage_pywbem_args(
                method='OpenEnumerateInstances',
                ClassName=ClassName,
                namespace=namespace,
                LocalOnly=LocalOnly,
                DeepInheritance=DeepInheritance,
                IncludeQualifiers=IncludeQualifiers,
                IncludeClassOrigin=IncludeClassOrigin,
                PropertyList=PropertyList,
                FilterQueryLanguage=FilterQueryLanguage,
                FilterQuery=FilterQuery,
                OperationTimeout=OperationTimeout,
                ContinueOnError=ContinueOnError,
                MaxObjectCount=MaxObjectCount,
                **extra)

        if MaxObjectCount is not None and MaxObjectCount < 0:
            raise ValueError('MaxObjectCount must be >= 0 but is %s' %
                             MaxObjectCount)

        try:

            if namespace is None and isinstance(ClassName, CIMClassName):
                namespace = ClassName.namespace
            namespace = self._iparam_namespace_from_namespace(namespace)
            classname = self._iparam_classname(ClassName)
            PropertyList = _iparam_propertylist(PropertyList)

            result = self._imethodcall(
                'OpenEnumerateInstances',
                namespace,
                ClassName=classname,
                LocalOnly=LocalOnly,
                DeepInheritance=DeepInheritance,
                IncludeQualifiers=IncludeQualifiers,
                IncludeClassOrigin=IncludeClassOrigin,
                PropertyList=PropertyList,
                FilterQueryLanguage=FilterQueryLanguage,
                FilterQuery=FilterQuery,
                OperationTimeout=OperationTimeout,
                ContinueOnError=ContinueOnError,
                MaxObjectCount=MaxObjectCount,
                response_params_rqd=True,
                **extra)

            result_tuple = pull_inst_result_tuple(
                *self._get_rslt_params(result, namespace))

        except Exception as exc:
            if self.operation_recorder:
                self.operation_recorder.stage_pywbem_result(None, exc)
                self.operation_recorder.record_staged()
            raise
        else:
            if self.operation_recorder:
                self.operation_recorder.stage_pywbem_result(result_tuple, None)
                self.operation_recorder.record_staged()
            return result_tuple

    def OpenReferenceInstancePaths(self, InstanceName, ResultClass=None,
                                   Role=None,
                                   FilterQueryLanguage=None, FilterQuery=None,
                                   OperationTimeout=None, ContinueOnError=None,
                                   MaxObjectCount=None, **extra):
        # pylint: disable=invalid-name
        """
        Open an enumeration session to retrieve the instance paths of
        the association instances that reference a source instance.

        This method does not support retrieving classes.

        This method performs the OpenReferenceInstancePaths operation
        (see :term:`DSP0200`). See :ref:`WBEM operations` for a list of all
        methods performing such operations.

        If the operation succeeds, this method returns enumeration session
        status and optionally instance paths.
        Otherwise, this method raises an exception.

        Use :meth:`~pywbem.WBEMConnection.PullInstances` request to
        retrieve the next set of instance paths
        or the :meth:`~pywbem.WBEMConnection.CloseEnumeration`
        request to close the enumeration session early.

        Parameters:

          InstanceName (:class:`~pywbem.CIMInstanceName`):
            The instance path of the source instance.
            If this object does not specify a namespace, the default namespace
            of the connection is used.
            Its `host` attribute will be ignored.

          ResultClass (:term:`string` or :class:`~pywbem.CIMClassName`):
            Class name of an association class (case independent),
            to filter the result to include only traversals of that association
            class (or subclasses).

            `None` means that no such filtering is peformed.

          Role (:term:`string`):
            Role name (= property name) of the source end (case independent),
            to filter the result to include only traversals from that source
            role.

            `None` means that no such filtering is peformed.

          FilterQueryLanguage (:term:`string`):
            A string defining the name of the query language
            used for the `FilterQuery` parameter. The DMTF defined language
            (FQL) (:term:`DSP0212`) is specified as 'DMTF:FQL'.

          FilterQuery (:term:`string`):
            A string defining the query that is to be sent
            to the WBEM server using the query language defined by
            the `FilterQueryLanguage` parameter.  Not all WBEM
            servers allow FilterQuery filtering for this operation
            because the act of the server filtering requires
            that it generate instances and then discard them.

          OperationTimeout (:class:`~pywbem.Uint32`):
            Minimum time in seconds the WBEM Server shall maintain an open
            enumeration session after a previous Open or Pull request is
            sent to the client. Once this timeout time has expired, the
            WBEM server may close the enumeration session.

            * If not `None`, this parameter is sent to the WBEM server as the
              proposed timeout for the enumeration session. A value of 0
              indicates that the server is expected to never time out. The
              server may reject the proposed value, causing a
              :class:`~pywbem.CIMError` to be raised with status code
              :attr:`~pywbem.CIM_ERR_INVALID_OPERATION_TIMEOUT`.
            * If `None`, this parameter is not passed to the WBEM server, and
              causes the server-implemented default timeout to be used.

          ContinueOnError (:class:`py:bool`):
            Indicates to the WBEM server to continue sending responses
            after an error response has been sent.

            * If `True`, the server is to continue sending responses after
              sending an error response. Not all servers support continuation
              on error; a server that does not support it must send an error
              response if `True` was specified, causing
              :class:`~pywbem.CIMError` to be raised with status code
              :attr:`~pywbem.CIM_ERR_CONTINUATION_ON_ERROR_NOT_SUPPORTED`.
            * If `False`, the server is requested to close the enumeration after
              sending an error response.
            * If `None`, this parameter is not passed to the WBEM server, and
              causes the server-implemented default behaviour to be used.
              :term:`DSP0200` defines that the server-implemented default is
              `False`.

          MaxObjectCount (:class:`~pywbem.Uint32`)
            Maximum number of instances the WBEM server may return
            for this request.

            * If positive, the WBEM server is to return no more than the
              specified number of instances.
            * If zero, the WBEM server is to return no instances. This may
              be used by a client to leave the handling of any returned
              instances to a loop of Pull operations.
            * If `None`, this parameter is not passed to the WBEM server, and
              causes the server-implemented default behaviour to be used.
              :term:`DSP0200` defines that the server-implemented default is
              to return zero instances.

        Keyword Arguments:

          extra :
            Additional keyword arguments are passed as additional operation
            parameters to the WBEM server.
            Note that :term:`DSP0200` does not define any additional parameters
            for this operation.

        Returns:

            A :class:`py:namedtuple` object containing the following named
            items:

            * **paths** (:class:`py:list` of :class:`~pywbem.CIMInstanceName`):
              Representations of the initial set of enumerated instance paths,
              with their attributes set as follows:

              * `classname`: Name of the creation class of the instance.
              * `keybindings`: Keybindings of the instance.
              * `namespace`: Name of the CIM namespace containing the instance.
              * `host`: Host and optionally port of the WBEM server containing
                the CIM namespace.

            * **eos** (:class:`py:bool`):
              Indicates whether the enumeration session is exhausted
              after returning the initial set of enumerated instances.

              - If `True`, the enumeration session is exhausted, and the
                server has closed the enumeration session.
              - If `False`, the enumeration session is not exhausted.

            * **context** (:class:`py:tuple` of server_context, namespace):
              Identifies the opened enumeration session. The client must
              provide this value for subsequent operations on this
              enumeration session.

              The tuple items are:

              * server_context (:term:`string`):
                Enumeration context string returned by the server if
                the session is not exhausted, or `None` otherwise. This string
                is opaque for the client.
              * namespace (:term:`string`):
                Name of the CIM namespace that was used for this operation.

              NOTE: This inner tuple hides the need for a CIM namespace
              on subsequent operations in the enumeration session. CIM
              operations always require target namespace, but it never
              makes sense to specify a different one in subsequent
              operations on the same enumeration session.

        Raises:

            Exceptions described in :class:`~pywbem.WBEMConnection`.
        """

        if self.operation_recorder:
            self.operation_recorder.reset()
            self.operation_recorder.stage_pywbem_args(
                method='OpenReferenceInstancePaths',
                InstanceName=InstanceName,
                ResultClass=ResultClass,
                Role=Role,
                FilterQueryLanguage=FilterQueryLanguage,
                FilterQuery=FilterQuery,
                OperationTimeout=OperationTimeout,
                ContinueOnError=ContinueOnError,
                MaxObjectCount=MaxObjectCount,
                **extra)

        if MaxObjectCount is not None and MaxObjectCount < 0:
            raise ValueError('MaxObjectCount must be >= 0 but is %s' %
                             MaxObjectCount)
        try:

            namespace = self._iparam_namespace_from_objectname(InstanceName)
            instancename = self._iparam_instancename(InstanceName)

            result = self._imethodcall(
                'OpenReferenceInstancePaths',
                namespace,
                InstanceName=instancename,
                ResultClass=self._iparam_classname(ResultClass),
                Role=Role,
                FilterQueryLanguage=FilterQueryLanguage,
                FilterQuery=FilterQuery,
                OperationTimeout=OperationTimeout,
                ContinueOnError=ContinueOnError,
                MaxObjectCount=MaxObjectCount,
                response_params_rqd=True,
                **extra)

            result_tuple = pull_path_result_tuple(
                *self._get_rslt_params(result, namespace))

        except Exception as exc:
            if self.operation_recorder:
                self.operation_recorder.stage_pywbem_result(None, exc)
                self.operation_recorder.record_staged()
            raise
        else:
            if self.operation_recorder:
                self.operation_recorder.stage_pywbem_result(result_tuple, None)
                self.operation_recorder.record_staged()
            return result_tuple

    def OpenReferenceInstances(self, InstanceName, ResultClass=None,
                               Role=None, IncludeQualifiers=None,
                               IncludeClassOrigin=None, PropertyList=None,
                               FilterQueryLanguage=None, FilterQuery=None,
                               OperationTimeout=None, ContinueOnError=None,
                               MaxObjectCount=None, **extra):
        # pylint: disable=invalid-name
        # pylint: disable=invalid-name,line-too-long
        """
        Open an enumeration session to retrieve the association instances
        that reference a source instance.

        This method does not support retrieving classes.

        This method performs the OpenReferenceInstances operation
        (see :term:`DSP0200`). See :ref:`WBEM operations` for a list of all
        methods performing such operations.

        If the operation succeeds, this method returns enumeration session
        status and optionally instances.
        Otherwise, this method raises an exception.

        Use :meth:`~pywbem.WBEMConnection.PullInstances` request to
        retrieve the next set of instance paths
        or the :meth:`~pywbem.WBEMConnection.CloseEnumeration`
        request to close the enumeration session early.

        Parameters:

          InstanceName (:class:`~pywbem.CIMInstanceName`):
            The instance path of the source instance.
            If this object does not specify a namespace, the default namespace
            of the connection is used.
            Its `host` attribute will be ignored.

          ResultClass (:term:`string` or :class:`~pywbem.CIMClassName`):
            Class name of an association class (case independent),
            to filter the result to include only traversals of that association
            class (or subclasses).

            `None` means that no such filtering is peformed.

          Role (:term:`string`):
            Role name (= property name) of the source end (case independent),
            to filter the result to include only traversals from that source
            role.

            `None` means that no such filtering is peformed.

          IncludeQualifiers (:class:`py:bool`):
            Indicates that qualifiers are to be included in the returned
            instances (or classes), as follows:

            * If `False`, qualifiers are not included.
            * If `True`, qualifiers are included if the WBEM server implements
              support for this parameter.
            * If `None`, this parameter is not passed to the WBEM server, and
              causes the server-implemented default to be used. :term:`DSP0200`
              defines that the server-implemented default is `False`.

            This parameter has been deprecated in :term:`DSP0200`. Clients
            cannot rely on it being implemented by WBEM servers.

          IncludeClassOrigin (:class:`py:bool`):
            Indicates that class origin information is to be included on each
            property or method in the returned instances (or classes), as
            follows:

            * If `False`, class origin information is not included.
            * If `True`, class origin information is included.
            * If `None`, this parameter is not passed to the WBEM server, and
              causes the server-implemented default to be used. :term:`DSP0200`
              defines that the server-implemented default is `False`.

          PropertyList (:term:`py:iterable` of :term:`string` or :term:`string`):
            An iterable specifying the names of the properties (or a  string
            that defines a single property) to be included in the returned
            instances (case independent).

            An empty iterable indicates to include no properties.

            If `None`, all properties are included.

          FilterQueryLanguage (:term:`string`):
            A string defining the name of the query language
            used for the `FilterQuery` parameter. The DMTF defined language
            (FQL) (:term:`DSP0212`) is specified as 'DMTF:FQL'.

          FilterQuery (:term:`string`):
            A string defining the query that is to be sent
            to the WBEM server using the query language defined by
            the `FilterQueryLanguage` parameter.

          OperationTimeout (:class:`~pywbem.Uint32`):
            Minimum time in seconds the WBEM Server shall maintain an open
            enumeration session after a previous Open or Pull request is
            sent to the client. Once this timeout time has expired, the
            WBEM server may close the enumeration session.

            * If not `None`, this parameter is sent to the WBEM server as the
              proposed timeout for the enumeration session. A value of 0
              indicates that the server is expected to never time out. The
              server may reject the proposed value, causing a
              :class:`~pywbem.CIMError` to be raised with status code
              :attr:`~pywbem.CIM_ERR_INVALID_OPERATION_TIMEOUT`.
            * If `None`, this parameter is not passed to the WBEM server, and
              causes the server-implemented default timeout to be used.

          ContinueOnError (:class:`py:bool`):
            Indicates to the WBEM server to continue sending responses
            after an error response has been sent.

            * If `True`, the server is to continue sending responses after
              sending an error response. Not all servers support continuation
              on error; a server that does not support it must send an error
              response if `True` was specified, causing
              :class:`~pywbem.CIMError` to be raised with status code
              :attr:`~pywbem.CIM_ERR_CONTINUATION_ON_ERROR_NOT_SUPPORTED`.
            * If `False`, the server is requested to close the enumeration after
              sending an error response.
            * If `None`, this parameter is not passed to the WBEM server, and
              causes the server-implemented default behaviour to be used.
              :term:`DSP0200` defines that the server-implemented default is
              `False`.

          MaxObjectCount (:class:`~pywbem.Uint32`)
            Maximum number of instances the WBEM server may return
            for this request.

            * If positive, the WBEM server is to return no more than the
              specified number of instances.
            * If zero, the WBEM server is to return no instances. This may
              be used by a client to leave the handling of any returned
              instances to a loop of Pull operations.
            * If `None`, this parameter is not passed to the WBEM server, and
              causes the server-implemented default behaviour to be used.
              :term:`DSP0200` defines that the server-implemented default is
              to return zero instances.

        Keyword Arguments:

          extra :
            Additional keyword arguments are passed as additional operation
            parameters to the WBEM server.
            Note that :term:`DSP0200` does not define any additional parameters
            for this operation.

        Returns:

            A :class:`py:namedtuple` object containing the following named
            items:

            * **instances** (:class:`py:list` of :class:`~pywbem.CIMInstance`):
              Representations of the initial set of enumerated instances.

              The `path` attribute of each :class:`~pywbem.CIMInstance`
              object is a :class:`~pywbem.CIMInstanceName` object with its
              attributes set as follows:

              * `classname`: Name of the creation class of the instance.
              * `keybindings`: Keybindings of the instance.
              * `namespace`: Name of the CIM namespace containing the instance.
              * `host`: Host and optionally port of the WBEM server containing
                the CIM namespace.

            * **eos** (:class:`py:bool`):
              Indicates whether the enumeration session is exhausted
              after returning the initial set of enumerated instances.

              - If `True`, the enumeration session is exhausted, and the
                server has closed the enumeration session.
              - If `False`, the enumeration session is not exhausted.

            * **context** (:class:`py:tuple` of server_context, namespace):
              Identifies the opened enumeration session. The client must
              provide this value for subsequent operations on this
              enumeration session.

              The tuple items are:

              * server_context (:term:`string`):
                Enumeration context string returned by the server if
                the session is not exhausted, or `None` otherwise. This string
                is opaque for the client.
              * namespace (:term:`string`):
                Name of the CIM namespace that was used for this operation.

              NOTE: This inner tuple hides the need for a CIM namespace
              on subsequent operations in the enumeration session. CIM
              operations always require target namespace, but it never
              makes sense to specify a different one in subsequent
              operations on the same enumeration session.

        Raises:

            Exceptions described in :class:`~pywbem.WBEMConnection`.
        """  # noqa: E501

        if self.operation_recorder:
            self.operation_recorder.reset()
            self.operation_recorder.stage_pywbem_args(
                method='OpenReferenceInstances',
                InstanceName=InstanceName,
                ResultClass=ResultClass,
                Role=Role,
                IncludeQualifiers=IncludeQualifiers,
                IncludeClassOrigin=IncludeClassOrigin,
                PropertyList=PropertyList,
                FilterQueryLanguage=FilterQueryLanguage,
                FilterQuery=FilterQuery,
                OperationTimeout=OperationTimeout,
                ContinueOnError=ContinueOnError,
                MaxObjectCount=MaxObjectCount,
                **extra)

        try:

            # TODO ks 6/16 Limit to instance name. No classname allowed.
            namespace = self._iparam_namespace_from_objectname(InstanceName)
            instancename = self._iparam_instancename(InstanceName)
            PropertyList = _iparam_propertylist(PropertyList)

            result = self._imethodcall(
                'OpenReferenceInstances',
                namespace,
                InstanceName=instancename,
                ResultClass=self._iparam_classname(ResultClass),
                Role=Role,
                IncludeQualifiers=IncludeQualifiers,
                IncludeClassOrigin=IncludeClassOrigin,
                PropertyList=PropertyList,
                FilterQueryLanguage=FilterQueryLanguage,
                FilterQuery=FilterQuery,
                OperationTimeout=OperationTimeout,
                ContinueOnError=ContinueOnError,
                MaxObjectCount=MaxObjectCount,
                response_params_rqd=True,
                **extra)

            result_tuple = pull_inst_result_tuple(
                *self._get_rslt_params(result, namespace))

        except Exception as exc:
            if self.operation_recorder:
                self.operation_recorder.stage_pywbem_result(None, exc)
                self.operation_recorder.record_staged()
            raise
        else:
            if self.operation_recorder:
                self.operation_recorder.stage_pywbem_result(result_tuple, None)
                self.operation_recorder.record_staged()
            return result_tuple

    def OpenAssociatorInstancePaths(self, InstanceName, AssocClass=None,
                                    ResultClass=None, Role=None,
                                    ResultRole=None,
                                    FilterQueryLanguage=None, FilterQuery=None,
                                    OperationTimeout=None, ContinueOnError=None,
                                    MaxObjectCount=None, **extra):
        # pylint: disable=invalid-name
        """
        Open an enumeration session to retrieve the instance paths of the
        instances associated to a source instance.

        This method does not support retrieving classes.

        This method performs the OpenAssociatorInstancePaths operation
        (see :term:`DSP0200`). See :ref:`WBEM operations` for a list of all
        methods performing such operations.

        If the operation succeeds, this method returns enumeration session
        status and optionally instance paths.
        Otherwise, this method raises an exception.

        Use :meth:`~pywbem.WBEMConnection.PullInstancePaths` request to
        retrieve the next set of instance paths
        or the :meth:`~pywbem.WBEMConnection.CloseEnumeration`
        request to close the enumeration session early.

        Parameters:

          InstanceName (:class:`~pywbem.CIMInstanceName`):
            The instance path of the source instance.
            If this object does not specify a namespace, the default namespace
            of the connection is used.
            Its `host` attribute will be ignored.

          AssocClass (:term:`string` or :class:`~pywbem.CIMClassName`):
            Class name of an association class (case independent),
            to filter the result to include only traversals of that association
            class (or subclasses).

            `None` means that no such filtering is peformed.

          ResultClass (:term:`string` or :class:`~pywbem.CIMClassName`):
            Class name of an associated class (case independent),
            to filter the result to include only traversals to that associated
            class (or subclasses).

            `None` means that no such filtering is peformed.

          Role (:term:`string`):
            Role name (= property name) of the source end (case independent),
            to filter the result to include only traversals from that source
            role.

            `None` means that no such filtering is peformed.

          ResultRole (:term:`string`):
            Role name (= property name) of the far end (case independent),
            to filter the result to include only traversals to that far
            role.

            `None` means that no such filtering is peformed.

          FilterQueryLanguage (:term:`string`):
            A string defining the name of the query language
            used for the `FilterQuery` parameter. The DMTF defined language
            (FQL) (:term:`DSP0212`) is specified as 'DMTF:FQL'.

          FilterQuery (:term:`string`):
            A string defining the query that is to be sent
            to the WBEM server using the query language defined by
            the `FilterQueryLanguage` parameter. Not all WBEM
            servers allow FilterQuery filtering for this operation
            (i.e. return the CIM_ERR_NOT_SUPPORTED exception when filtering
            is specified) because the act of the server filtering
            requires that it generate instances and then discard them.

          OperationTimeout (:class:`~pywbem.Uint32`):
            Minimum time in seconds the WBEM Server shall maintain an open
            enumeration session after a previous Open or Pull request is
            sent to the client. Once this timeout time has expired, the
            WBEM server may close the enumeration session.

            * If not `None`, this parameter is sent to the WBEM server as the
              proposed timeout for the enumeration session. A value of 0
              indicates that the server is expected to never time out. The
              server may reject the proposed value, causing a
              :class:`~pywbem.CIMError` to be raised with status code
              :attr:`~pywbem.CIM_ERR_INVALID_OPERATION_TIMEOUT`.
            * If `None`, this parameter is not passed to the WBEM server, and
              causes the server-implemented default timeout to be used.

          ContinueOnError (:class:`py:bool`):
            Indicates to the WBEM server to continue sending responses
            after an error response has been sent.

            * If `True`, the server is to continue sending responses after
              sending an error response. Not all servers support continuation
              on error; a server that does not support it must send an error
              response if `True` was specified, causing
              :class:`~pywbem.CIMError` to be raised with status code
              :attr:`~pywbem.CIM_ERR_CONTINUATION_ON_ERROR_NOT_SUPPORTED`.
            * If `False`, the server is requested to close the enumeration after
              sending an error response.
            * If `None`, this parameter is not passed to the WBEM server, and
              causes the server-implemented default behaviour to be used.
              :term:`DSP0200` defines that the server-implemented default is
              `False`.

          MaxObjectCount (:class:`~pywbem.Uint32`)
            Maximum number of instances the WBEM server may return
            for this request.

            * If positive, the WBEM server is to return no more than the
              specified number of instances.
            * If zero, the WBEM server is to return no instances. This may
              be used by a client to leave the handling of any returned
              instances to a loop of Pull operations.
            * If `None`, this parameter is not passed to the WBEM server, and
              causes the server-implemented default behaviour to be used.
              :term:`DSP0200` defines that the server-implemented default is
              to return zero instances.

        Keyword Arguments:

          extra :
            Additional keyword arguments are passed as additional operation
            parameters to the WBEM server.
            Note that :term:`DSP0200` does not define any additional parameters
            for this operation.

        Returns:

            A :class:`py:namedtuple` object containing the following named
            items:

            * **paths** (:class:`py:list` of :class:`~pywbem.CIMInstanceName`):
              Representations of the initial set of enumerated instance paths,
              with their attributes set as follows:

              * `classname`: Name of the creation class of the instance.
              * `keybindings`: Keybindings of the instance.
              * `namespace`: Name of the CIM namespace containing the instance.
              * `host`: Host and optionally port of the WBEM server containing
                the CIM namespace.

            * **eos** (:class:`py:bool`):
              Indicates whether the enumeration session is exhausted
              after returning the initial set of enumerated instances.

              - If `True`, the enumeration session is exhausted, and the
                server has closed the enumeration session.
              - If `False`, the enumeration session is not exhausted.

            * **context** (:class:`py:tuple` of server_context, namespace):
              Identifies the opened enumeration session. The client must
              provide this value for subsequent operations on this
              enumeration session.

              The tuple items are:

              * server_context (:term:`string`):
                Enumeration context string returned by the server if
                the session is not exhausted, or `None` otherwise. This string
                is opaque for the client.
              * namespace (:term:`string`):
                Name of the CIM namespace that was used for this operation.

              NOTE: This inner tuple hides the need for a CIM namespace
              on subsequent operations in the enumeration session. CIM
              operations always require target namespace, but it never
              makes sense to specify a different one in subsequent
              operations on the same enumeration session.

        Raises:

            Exceptions described in :class:`~pywbem.WBEMConnection`.
        """

        if self.operation_recorder:
            self.operation_recorder.reset()
            self.operation_recorder.stage_pywbem_args(
                method='OpenAssociatorInstancePaths',
                InstanceName=InstanceName,
                AssocClass=AssocClass,
                ResultClass=ResultClass,
                Role=Role,
                ResultRole=ResultRole,
                FilterQueryLanguage=FilterQueryLanguage,
                FilterQuery=FilterQuery,
                OperationTimeout=OperationTimeout,
                ContinueOnError=ContinueOnError,
                MaxObjectCount=MaxObjectCount,
                **extra)

        try:

            namespace = self._iparam_namespace_from_objectname(InstanceName)
            instancename = self._iparam_instancename(InstanceName)

            result = self._imethodcall(
                'OpenAssociatorInstancePaths',
                namespace,
                InstanceName=instancename,
                AssocClass=self._iparam_classname(AssocClass),
                ResultClass=self._iparam_classname(ResultClass),
                Role=Role,
                ResultRole=ResultRole,
                FilterQueryLanguage=FilterQueryLanguage,
                FilterQuery=FilterQuery,
                OperationTimeout=OperationTimeout,
                ContinueOnError=ContinueOnError,
                MaxObjectCount=MaxObjectCount,
                response_params_rqd=True,
                **extra)

            result_tuple = pull_path_result_tuple(
                *self._get_rslt_params(result, namespace))

        except Exception as exc:
            if self.operation_recorder:
                self.operation_recorder.stage_pywbem_result(None, exc)
                self.operation_recorder.record_staged()
            raise
        else:
            if self.operation_recorder:
                self.operation_recorder.stage_pywbem_result(result_tuple, None)
                self.operation_recorder.record_staged()
            return result_tuple

    def OpenAssociatorInstances(self, InstanceName, AssocClass=None,
                                ResultClass=None, Role=None, ResultRole=None,
                                IncludeQualifiers=None,
                                IncludeClassOrigin=None,
                                PropertyList=None, FilterQueryLanguage=None,
                                FilterQuery=None, OperationTimeout=None,
                                ContinueOnError=None, MaxObjectCount=None,
                                **extra):
        # pylint: disable=invalid-name
        # pylint: disable=invalid-name,line-too-long
        """
        Open an enumeration session to retrieve the instances associated
        to a source instance.

        This method does not support retrieving classes.

        This method performs the OpenAssociatorInstances operation
        (see :term:`DSP0200`). See :ref:`WBEM operations` for a list of all
        methods performing such operations.

        If the operation succeeds, this method returns enumeration session
        status and optionally instances.
        Otherwise, this method raises an exception.

        The subsequent operation after this open is successful
        and result.eos = False must be either the
        :meth:`~pywbem.WBEMConnection.PullInstances` request
        or the :meth:`~pywbem.WBEMConnection.CloseEnumeration`
        request.

        Parameters:

          InstanceName (:class:`~pywbem.CIMInstanceName`):
            The instance path of the source instance.
            If this object does not specify a namespace, the default namespace
            of the connection is used.
            Its `host` attribute will be ignored.

          AssocClass (:term:`string` or :class:`~pywbem.CIMClassName`):
            Class name of an association class (case independent),
            to filter the result to include only traversals of that association
            class (or subclasses).

            `None` means that no such filtering is peformed.

          ResultClass (:term:`string` or :class:`~pywbem.CIMClassName`):
            Class name of an associated class (case independent),
            to filter the result to include only traversals to that associated
            class (or subclasses).

            `None` means that no such filtering is peformed.

          Role (:term:`string`):
            Role name (= property name) of the source end (case independent),
            to filter the result to include only traversals from that source
            role.

            `None` means that no such filtering is peformed.

          ResultRole (:term:`string`):
            Role name (= property name) of the far end (case independent),
            to filter the result to include only traversals to that far
            role.

            `None` means that no such filtering is peformed.

          IncludeQualifiers (:class:`py:bool`):
            Indicates that qualifiers are to be included in the returned
            instances (or classes), as follows:

            * If `False`, qualifiers are not included.
            * If `True`, qualifiers are included if the WBEM server implements
              support for this parameter.
            * If `None`, this parameter is not passed to the WBEM server, and
              causes the server-implemented default to be used. :term:`DSP0200`
              defines that the server-implemented default is `False`.

            This parameter has been deprecated in :term:`DSP0200`. Clients
            cannot rely on it being implemented by WBEM servers.

          IncludeClassOrigin (:class:`py:bool`):
            Indicates that class origin information is to be included on each
            property or method in the returned instances (or classes), as
            follows:

            * If `False`, class origin information is not included.
            * If `True`, class origin information is included.
            * If `None`, this parameter is not passed to the WBEM server, and
              causes the server-implemented default to be used. :term:`DSP0200`
              defines that the server-implemented default is `False`.

          PropertyList (:term:`py:iterable` of :term:`string` or :term:`string`):
            An iterable specifying the names of the properties (or a  string
            that defines a single property) to be included in the returned
            instances (case independent).

            An empty iterable indicates to include no properties.

            If `None`, all properties are included.

          FilterQueryLanguage (:term:`string`):
            A string defining the name of the query language
            used for the `FilterQuery` parameter. The DMTF defined language
            (FQL) (:term:`DSP0212`) is specified as 'DMTF:FQL'.

          FilterQuery (:term:`string`):
            A string defining the query that is to be sent
            to the WBEM server using the query language defined by
            the `FilterQueryLanguage` parameter.

          OperationTimeout (:class:`~pywbem.Uint32`):
            Minimum time in seconds the WBEM Server shall maintain an open
            enumeration session after a previous Open or Pull request is
            sent to the client. Once this timeout time has expired, the
            WBEM server may close the enumeration session.

            * If not `None`, this parameter is sent to the WBEM server as the
              proposed timeout for the enumeration session. A value of 0
              indicates that the server is expected to never time out. The
              server may reject the proposed value, causing a
              :class:`~pywbem.CIMError` to be raised with status code
              :attr:`~pywbem.CIM_ERR_INVALID_OPERATION_TIMEOUT`.
            * If `None`, this parameter is not passed to the WBEM server, and
              causes the server-implemented default timeout to be used.

          ContinueOnError (:class:`py:bool`):
            Indicates to the WBEM server to continue sending responses
            after an error response has been sent.

            * If `True`, the server is to continue sending responses after
              sending an error response. Not all servers support continuation
              on error; a server that does not support it must send an error
              response if `True` was specified, causing
              :class:`~pywbem.CIMError` to be raised with status code
              :attr:`~pywbem.CIM_ERR_CONTINUATION_ON_ERROR_NOT_SUPPORTED`.
            * If `False`, the server is requested to close the enumeration after
              sending an error response.
            * If `None`, this parameter is not passed to the WBEM server, and
              causes the server-implemented default behaviour to be used.
              :term:`DSP0200` defines that the server-implemented default is
              `False`.

          MaxObjectCount (:class:`~pywbem.Uint32`)
            Maximum number of instances the WBEM server may return
            for this request.

            * If positive, the WBEM server is to return no more than the
              specified number of instances.
            * If zero, the WBEM server is to return no instances. This may
              be used by a client to leave the handling of any returned
              instances to a loop of Pull operations.
            * If `None`, this parameter is not passed to the WBEM server, and
              causes the server-implemented default behaviour to be used.
              :term:`DSP0200` defines that the server-implemented default is
              to return zero instances.

        Keyword Arguments:

          extra :
            Additional keyword arguments are passed as additional operation
            parameters to the WBEM server.
            Note that :term:`DSP0200` does not define any additional parameters
            for this operation.

        Returns:

            A :class:`py:namedtuple` object containing the following named
            items:

            * **instances** (:class:`py:list` of :class:`~pywbem.CIMInstance`):
              Representations of the initial set of enumerated instances.

              The `path` attribute of each :class:`~pywbem.CIMInstance`
              object is a :class:`~pywbem.CIMInstanceName` object with its
              attributes set as follows:

              * `classname`: Name of the creation class of the instance.
              * `keybindings`: Keybindings of the instance.
              * `namespace`: Name of the CIM namespace containing the instance.
              * `host`: Host and optionally port of the WBEM server containing
                the CIM namespace.

            * **eos** (:class:`py:bool`):
              Indicates whether the enumeration session is exhausted
              after returning the initial set of enumerated instances.

              - If `True`, the enumeration session is exhausted, and the
                server has closed the enumeration session.
              - If `False`, the enumeration session is not exhausted.

            * **context** (:class:`py:tuple` of server_context, namespace):
              Identifies the opened enumeration session. The client must
              provide this value for subsequent operations on this
              enumeration session.

              The tuple items are:

              * server_context (:term:`string`):
                Enumeration context string returned by the server if
                the session is not exhausted, or `None` otherwise. This string
                is opaque for the client.
              * namespace (:term:`string`):
                Name of the CIM namespace that was used for this operation.

              NOTE: This inner tuple hides the need for a CIM namespace
              on subsequent operations in the enumeration session. CIM
              operations always require target namespace, but it never
              makes sense to specify a different one in subsequent
              operations on the same enumeration session.

        Raises:

            Exceptions described in :class:`~pywbem.WBEMConnection`.
        """  # noqa: E501

        if self.operation_recorder:
            self.operation_recorder.reset()
            self.operation_recorder.stage_pywbem_args(
                method='OpenAssociatorInstances',
                InstanceName=InstanceName,
                AssocClass=AssocClass,
                ResultClass=ResultClass,
                Role=Role,
                ResultRole=ResultRole,
                IncludeQualifiers=IncludeQualifiers,
                IncludeClassOrigin=IncludeClassOrigin,
                PropertyList=PropertyList,
                FilterQueryLanguage=FilterQueryLanguage,
                FilterQuery=FilterQuery,
                OperationTimeout=OperationTimeout,
                ContinueOnError=ContinueOnError,
                MaxObjectCount=MaxObjectCount,
                **extra)

        try:

            namespace = self._iparam_namespace_from_objectname(InstanceName)
            instancename = self._iparam_instancename(InstanceName)
            PropertyList = _iparam_propertylist(PropertyList)

            result = self._imethodcall(
                'OpenAssociatorInstances',
                namespace,
                InstanceName=instancename,
                AssocClass=self._iparam_classname(AssocClass),
                ResultClass=self._iparam_classname(ResultClass),
                Role=Role,
                ResultRole=ResultRole,
                IncludeQualifiers=IncludeQualifiers,
                IncludeClassOrigin=IncludeClassOrigin,
                PropertyList=PropertyList,
                FilterQueryLanguage=FilterQueryLanguage,
                FilterQuery=FilterQuery,
                OperationTimeout=OperationTimeout,
                ContinueOnError=ContinueOnError,
                MaxObjectCount=MaxObjectCount,
                response_params_rqd=True,
                **extra)

            result_tuple = pull_inst_result_tuple(
                *self._get_rslt_params(result, namespace))

        except Exception as exc:
            if self.operation_recorder:
                self.operation_recorder.stage_pywbem_result(None, exc)
                self.operation_recorder.record_staged()
            raise
        else:
            if self.operation_recorder:
                self.operation_recorder.stage_pywbem_result(result_tuple, None)
                self.operation_recorder.record_staged()
            return result_tuple

    def OpenQueryInstances(self, FilterQueryLanguage, FilterQuery,
                           namespace=None, ReturnQueryResultClass=None,
                           OperationTimeout=None, ContinueOnError=None,
                           MaxObjectCount=None, **extra):
        # pylint: disable=invalid-name
        """
        Open an enumeration session to execute a query in a namespace.

        This method performs the OpenQueryInstances operation
        (see :term:`DSP0200`). See :ref:`WBEM operations` for a list of all
        methods performing such operations.

        If the operation succeeds, this method returns enumeration session
        status and optionally CIM instances representing the query result.
        Otherwise, this method raises an exception.

        The subsequent operation after this open is successful
        and result.eos is False, must be either the
        :meth:`~pywbem.WBEMConnection.PullInstances` request
        or the :meth:`~pywbem.WBEMConnection.CloseEnumeration`
        request.

        Parameters:

          FilterQueryLanguage (:term:`string`):
            Name of the query language used in the `Query` parameter, e.g.
            "DMTF:CQL" for CIM Query Language, and "WQL" for WBEM Query
            Language. "DMTF:FQL" is not a valid query language for this
            request.

          FilterQuery (:term:`string`):
            Query string in the query language specified in the `QueryLanguage`
            parameter.

          namespace (:term:`string`):
            Name of the CIM namespace to be used (case independent).

            If `None`, the default namespace of the connection object will be
            used.

          ReturnQueryResultClass  (:class:`py:bool`):
            Controls whether a class definition is returned.

          OperationTimeout (:class:`~pywbem.Uint32`):
            Minimum time in seconds the WBEM Server shall maintain an open
            enumeration session after a previous Open or Pull request is
            sent to the client. Once this timeout time has expired, the
            WBEM server may close the enumeration session.

            * If not `None`, this parameter is sent to the WBEM server as the
              proposed timeout for the enumeration session. A value of 0
              indicates that the server is expected to never time out. The
              server may reject the proposed value, causing a
              :class:`~pywbem.CIMError` to be raised with status code
              :attr:`~pywbem.CIM_ERR_INVALID_OPERATION_TIMEOUT`.
            * If `None`, this parameter is not passed to the WBEM server, and
              causes the server-implemented default timeout to be used.

          ContinueOnError (:class:`py:bool`):
            Indicates to the WBEM server to continue sending responses
            after an error response has been sent.

            * If `True`, the server is to continue sending responses after
              sending an error response. Not all servers support continuation
              on error; a server that does not support it must send an error
              response if `True` was specified, causing
              :class:`~pywbem.CIMError` to be raised with status code
              :attr:`~pywbem.CIM_ERR_CONTINUATION_ON_ERROR_NOT_SUPPORTED`.
            * If `False`, the server is requested to close the enumeration after
              sending an error response.
            * If `None`, this parameter is not passed to the WBEM server, and
              causes the server-implemented default behaviour to be used.
              :term:`DSP0200` defines that the server-implemented default is
              `False`.

          MaxObjectCount (:class:`~pywbem.Uint32`)
            Maximum number of instances the WBEM server may return
            for this request.

            * If positive, the WBEM server is to return no more than the
              specified number of instances.
            * If zero, the WBEM server is to return no instances. This may
              be used by a client to leave the handling of any returned
              instances to a loop of Pull operations.
            * If `None`, this parameter is not passed to the WBEM server, and
              causes the server-implemented default behaviour to be used.
              :term:`DSP0200` defines that the server-implemented default is
              to return zero instances.

        Keyword Arguments:

          extra :
            Additional keyword arguments are passed as additional operation
            parameters to the WBEM server.
            Note that :term:`DSP0200` does not define any additional parameters
            for this operation.

        Returns:

            A :class:`py:namedtuple` object containing the following named
            items:

            * **instances** (:class:`py:list` of :class:`~pywbem.CIMInstance`):
              Representations of the initial set of enumerated instances.

              The `path` attribute of each :class:`~pywbem.CIMInstance`
              object is `None`, because query results are not addressable
              CIM instances.

            * **eos** (:class:`py:bool`):
              Indicates whether the enumeration session is exhausted
              after returning the initial set of enumerated instances.

              - If `True`, the enumeration session is exhausted, and the
                server has closed the enumeration session.
              - If `False`, the enumeration session is not exhausted.

            * **context** (:class:`py:tuple` of server_context, namespace):
              Identifies the opened enumeration session. The client must
              provide this value for subsequent operations on this
              enumeration session.

              The tuple items are:

              * server_context (:term:`string`):
                Enumeration context string returned by the server if
                the session is not exhausted, or `None` otherwise. This string
                is opaque for the client.
              * namespace (:term:`string`):
                Name of the CIM namespace that was used for this operation.

              NOTE: The inner tuple hides the need for a CIM namespace
              on subsequent operations in the enumeration session. CIM
              operations always require target namespace, but it never
              makes sense to specify a different one in subsequent
              operations on the same enumeration session.

            * **query_result_class** (:class:`~pywbem.CIMClass`):
              If the `ReturnQueryResultClass` parameter is True, this tuple
              item contains a class definition that defines the properties
              of each row (instance) of the query result. Otherwise, `None`.

        Raises:

            Exceptions described in :class:`~pywbem.WBEMConnection`.
        """

        @staticmethod
        def _GetQueryRsltClass(result):
            """ Get the QueryResultClass and return it or generate
                exception.
            """

            for p in result:
                if p[0] == 'QueryResultClass' and isinstance(p[2], CIMClass):
                    return p[2]
            raise CIMError(CIM_ERR_INVALID_PARAMETER,
                           "ReturnQueryResultClass invalid or missing.")

        if self.operation_recorder:
            self.operation_recorder.reset()
            self.operation_recorder.stage_pywbem_args(
                method='OpenQueryInstances',
                FilterQueryLanguage=FilterQueryLanguage,
                FilterQuery=FilterQuery,
                namespace=namespace,
                ReturnQueryResultClass=ReturnQueryResultClass,
                OperationTimeout=OperationTimeout,
                ContinueOnError=ContinueOnError,
                MaxObjectCount=MaxObjectCount,
                **extra)

        try:

            namespace = self._iparam_namespace_from_objectname(namespace)

            result = self._imethodcall(
                'OpenQueryInstances',
                namespace,
                FilterQuery=FilterQuery,
                FilterQueryLanguage=FilterQueryLanguage,
                ReturnQueryResultClass=ReturnQueryResultClass,
                OperationTimeout=OperationTimeout,
                ContinueOnError=ContinueOnError,
                MaxObjectCount=MaxObjectCount,
                response_params_rqd=True,
                **extra)

            insts, eos, enum_ctxt = self._get_rslt_params(result, namespace)

            query_result_class = _GetQueryRsltClass(result) if \
                ReturnQueryResultClass else None

            result_tuple = pull_query_result_tuple(insts, eos, enum_ctxt,
                                                   query_result_class)

        except Exception as exc:
            if self.operation_recorder:
                self.operation_recorder.stage_pywbem_result(None, exc)
                self.operation_recorder.record_staged()
            raise
        else:
            if self.operation_recorder:
                self.operation_recorder.stage_pywbem_result(result_tuple, None)
                self.operation_recorder.record_staged()
            return result_tuple

    def PullInstancesWithPath(self, context, MaxObjectCount,
                              **extra):
        # pylint: disable=invalid-name

        """
        Retrieve the next set of instances with path from an open enumeraton
        session defined by the `enumeration_context` parameter.  The retrieved
        instances include their instance paths.

        This method performs the PullInstancesWithPath operation
        (see :term:`DSP0200`). See :ref:`WBEM operations` for a list of all
        methods performing such operations.

        If the operation succeeds, this method returns enumeration session
        status and optionally instances.
        Otherwise, this method raises an exception.

        Parameters:

          context (:term:`string`)
            Identifies the enumeration session, including its current
            enumeration state. This must be the value of the `context` item in
            the :class:`py:namedtuple` object returned from the previous
            open or pull operation for this enumeration.

            The tuple items are:

            * server_context (:term:`string`):
              Enumeration context string returned by the server. This
              string is opaque for the client.
            * namespace (:term:`string`):
              Name of the CIM namespace to be used for this operation.

          MaxObjectCount (:class:`~pywbem.Uint32`)
            Maximum number of instances the WBEM server shall return
            for this request. This parameter is required for each
            Pull request.

            * If positive, the WBEM server is to return no more than the
              specified number of instances.
            * If zero, the WBEM server is to return no instances. This may
              be used by a client to leave the handling of any returned
              instances to a loop of Pull operations.

        Keyword Arguments:

          extra :
            Additional keyword arguments are passed as additional operation
            parameters to the WBEM server.
            Note that :term:`DSP0200` does not define any additional parameters
            for this operation.

        Returns:

            A :class:`py:namedtuple` object containing the following named
            items:

            * **instances** (:class:`py:list` of :class:`~pywbem.CIMInstance`):
              Representations of the next set of enumerated instances.

              The `path` attribute of each :class:`~pywbem.CIMInstance`
              object is a :class:`~pywbem.CIMInstanceName` object with its
              attributes set as follows:

              * `classname`: Name of the creation class of the instance.
              * `keybindings`: Keybindings of the instance.
              * `namespace`: Name of the CIM namespace containing the instance.
              * `host`: Host and optionally port of the WBEM server containing
                the CIM namespace.

            * **eos** (:class:`py:bool`):
              Indicates whether the enumeration session is exhausted
              after returning the initial set of enumerated instances.

              - If `True`, the enumeration session is exhausted, and the
                server has closed the enumeration session.
              - If `False`, the enumeration session is not exhausted.

            * **context** (:class:`py:tuple` of server_context, namespace):
              Identifies the opened enumeration session. The client must
              provide this value for subsequent operations on this
              enumeration session.

              The tuple items are:

              * server_context (:term:`string`):
                Enumeration context string returned by the server if
                the session is not exhausted, or `None` otherwise. This string
                is opaque for the client.
              * namespace (:term:`string`):
                Name of the CIM namespace that was used for this operation.

              NOTE: This inner tuple hides the need for a CIM namespace
              on subsequent operations in the enumeration session. CIM
              operations always require target namespace, but it never
              makes sense to specify a different one in subsequent
              operations on the same enumeration session.

        Raises:

            Exceptions described in :class:`~pywbem.WBEMConnection`.
        """

        if self.operation_recorder:
            self.operation_recorder.reset()
            self.operation_recorder.stage_pywbem_args(
                method='PullInstancesWithPath',
                context=context,
                MaxObjectCount=MaxObjectCount,
                **extra)

        try:

            namespace = context[1]

            result = self._imethodcall(
                'PullInstancesWithPath',
                namespace=namespace,
                EnumerationContext=context[0],
                MaxObjectCount=MaxObjectCount,
                response_params_rqd=True,
                **extra)

            result_tuple = pull_inst_result_tuple(
                *self._get_rslt_params(result, namespace))

        except Exception as exc:
            if self.operation_recorder:
                self.operation_recorder.stage_pywbem_result(None, exc)
                self.operation_recorder.record_staged()
            raise
        else:
            if self.operation_recorder:
                self.operation_recorder.stage_pywbem_result(result_tuple, None)
                self.operation_recorder.record_staged()
            return result_tuple

    def PullInstancePaths(self, context, MaxObjectCount=None, **extra):
        # pylint: disable=invalid-name

        """
        Retrieve the next set of instance paths from an open enumeraton
        session defined by the `enumeration_context` parameter.

        This method performs the PullInstancePaths operation
        (see :term:`DSP0200`). See :ref:`WBEM operations` for a list of all
        methods performing such operations.

        If the operation succeeds, this method returns enumeration session
        status and optionally instance paths.
        Otherwise, this method raises an exception.

        Parameters:

          context (:term:`string`)
            Identifies the enumeration session, including its current
            enumeration state. This must be the value of the `context` item in
            the :class:`py:namedtuple` object returned from the previous
            open or pull operation for this enumeration.

            The tuple items are:

            * server_context (:term:`string`):
              Enumeration context string returned by the server. This
              string is opaque for the client.
            * namespace (:term:`string`):
              Name of the CIM namespace to be used for this operation.

          MaxObjectCount (:class:`~pywbem.Uint32`)
            Maximum number of instances the WBEM server shall return
            for this request. This parameter is required for each
            Pull request.

            * If positive, the WBEM server is to return no more than the
              specified number of instances.
            * If zero, the WBEM server is to return no instances. This may
              be used by a client to leave the handling of any returned
              instances to a loop of Pull operations.

        Keyword Arguments:

          extra :
            Additional keyword arguments are passed as additional operation
            parameters to the WBEM server.
            Note that :term:`DSP0200` does not define any additional parameters
            for this operation.

        Returns:

            A :class:`py:namedtuple` object containing the following named
            items:

            * **paths** (:class:`py:list of` :class:`~pywbem.CIMInstanceName`):
              Representations of the next set of enumerated instance paths,
              with their attributes set as follows:

              * `classname`: Name of the creation class of the instance.
              * `keybindings`: Keybindings of the instance.
              * `namespace`: Name of the CIM namespace containing the instance.
              * `host`: Host and optionally port of the WBEM server containing
                the CIM namespace.

            * **eos** (:class:`py:bool`):
              Indicates whether the enumeration session is exhausted
              after returning the initial set of enumerated instances.

              - If `True`, the enumeration session is exhausted, and the
                server has closed the enumeration session.
              - If `False`, the enumeration session is not exhausted.

            * **context** (:class:`py:tuple` of server_context, namespace):
              Identifies the opened enumeration session. The client must
              provide this value for subsequent operations on this
              enumeration session.

              The tuple items are:

              * server_context (:term:`string`):
                Enumeration context string returned by the server if
                the session is not exhausted, or `None` otherwise. This string
                is opaque for the client.
              * namespace (:term:`string`):
                Name of the CIM namespace that was used for this operation.

              NOTE: This inner tuple hides the need for a CIM namespace
              on subsequent operations in the enumeration session. CIM
              operations always require target namespace, but it never
              makes sense to specify a different one in subsequent
              operations on the same enumeration session.

        Raises:

            Exceptions described in :class:`~pywbem.WBEMConnection`.
        """

        if self.operation_recorder:
            self.operation_recorder.reset()
            self.operation_recorder.stage_pywbem_args(
                method='PullInstancePaths',
                context=context,
                MaxObjectCount=MaxObjectCount,
                **extra)

        try:

            namespace = context[1]

            result = self._imethodcall(
                'PullInstancePaths',
                namespace=namespace,
                EnumerationContext=context[0],
                MaxObjectCount=MaxObjectCount,
                response_params_rqd=True,
                **extra)

            result_tuple = pull_path_result_tuple(
                *self._get_rslt_params(result, namespace))

        except Exception as exc:
            if self.operation_recorder:
                self.operation_recorder.stage_pywbem_result(None, exc)
                self.operation_recorder.record_staged()
            raise
        else:
            if self.operation_recorder:
                self.operation_recorder.stage_pywbem_result(result_tuple, None)
                self.operation_recorder.record_staged()
            return result_tuple

    def PullInstances(self, context, MaxObjectCount=None, **extra):
        # pylint: disable=invalid-name
        """
        Retrieve the next set of instances from an open enumeraton
        session defined by the `enumeration_context` parameter.

        This method performs the PullInstances operation
        (see :term:`DSP0200`). See :ref:`WBEM operations` for a list of all
        methods performing such operations.

        If the operation succeeds, this method returns enumeration session
        status and optionally instances.
        Otherwise, this method raises an exception.

        Parameters:

          context (:term:`string`)
            Identifies the enumeration session, including its current
            enumeration state. This must be the value of the `context` item in
            the :class:`py:namedtuple` object returned from the previous
            open or pull operation for this enumeration.

            The tuple items are:

            * server_context (:term:`string`):
              Enumeration context string returned by the server. This
              string is opaque for the client.
            * namespace (:term:`string`):
              Name of the CIM namespace to be used for this operation.

          MaxObjectCount (:class:`~pywbem.Uint32`)
            Maximum number of instances the WBEM server shall return
            for this request. This parameter is required for each
            Pull request.

            * If positive, the WBEM server is to return no more than the
              specified number of instances.
            * If zero, the WBEM server is to return no instances. This may
              be used by a client to leave the handling of any returned
              instances to a loop of Pull operations.

        Keyword Arguments:

          extra :
            Additional keyword arguments are passed as additional operation
            parameters to the WBEM server.
            Note that :term:`DSP0200` does not define any additional parameters
            for this operation.

        Returns:

            A :class:`py:namedtuple` object containing the following named
            items:

            * **instances** (:class:`py:list` of :class:`~pywbem.CIMInstance`):
              Representations of the next set of enumerated instances.

              The `path` attribute of each :class:`~pywbem.CIMInstance`
              object is `None`, because this operation does not return instance
              paths.

            * **eos** (:class:`py:bool`):
              Indicates whether the enumeration session is exhausted
              after returning the initial set of enumerated instances.

              - If `True`, the enumeration session is exhausted, and the
                server has closed the enumeration session.
              - If `False`, the enumeration session is not exhausted.

            * **context** (:class:`py:tuple` of server_context, namespace):
              Identifies the opened enumeration session. The client must
              provide this value for subsequent operations on this
              enumeration session.

              The tuple items are:

              * server_context (:term:`string`):
                Enumeration context string returned by the server if
                the session is not exhausted, or `None` otherwise. This string
                is opaque for the client.
              * namespace (:term:`string`):
                Name of the CIM namespace that was used for this operation.

              NOTE: This inner tuple hides the need for a CIM namespace
              on subsequent operations in the enumeration session. CIM
              operations always require target namespace, but it never
              makes sense to specify a different one in subsequent
              operations on the same enumeration session.

        Raises:

            Exceptions described in :class:`~pywbem.WBEMConnection`.
        """

        if self.operation_recorder:
            self.operation_recorder.reset()
            self.operation_recorder.stage_pywbem_args(
                method='PullInstances',
                context=context,
                MaxObjectCount=MaxObjectCount,
                **extra)

        try:

            namespace = context[1]

            result = self._imethodcall(
                'PullInstances',
                namespace=namespace,
                EnumerationContext=context[0],
                MaxObjectCount=MaxObjectCount,
                response_params_rqd=True,
                **extra)

            result_tuple = pull_inst_result_tuple(
                *self._get_rslt_params(result, namespace))

        except Exception as exc:
            if self.operation_recorder:
                self.operation_recorder.stage_pywbem_result(None, exc)
                self.operation_recorder.record_staged()
            raise
        else:
            if self.operation_recorder:
                self.operation_recorder.stage_pywbem_result(result_tuple, None)
                self.operation_recorder.record_staged()
            return result_tuple

    def CloseEnumeration(self, context, **extra):
        # pylint: disable=invalid-name
        """
        The CloseEnumeration closes an open enumeration session, performing
        an early termination of an incomplete enumeration session.

        This method performs the CloseEnumeration operation
        (see :term:`DSP0200`). See :ref:`WBEM operations` for a list of all
        methods performing such operations.

        This method should not used if the enumeration session has
        terminated and will result in an exception response.

        If the operation succeeds, this method returns. Otherwise, it
        raises an exception.

        Parameters:

          context (:term: `string`)
            The `enumeration_context` paramater must contain the
            `Context` value returned by the WBEM server with the
            response to the previous open or pull operation for this
            enumeration sequence.

        Keyword Arguments:

          extra :
            Additional keyword arguments are passed as additional operation
            parameters to the WBEM server.
            Note that :term:`DSP0200` does not define any additional parameters
            for this operation.

        Raises:

            Exceptions described in :class:`~pywbem.WBEMConnection`.
        """

        if self.operation_recorder:
            self.operation_recorder.reset()
            self.operation_recorder.stage_pywbem_args(
                method='CloseEnumeration',
                context=context,
                **extra)

        try:
            if context is None:
                raise ValueError('Invalid EnumerationContext')
            self._imethodcall(
                'CloseEnumeration',
                namespace=context[1],
                EnumerationContext=context[0],
                **extra)

        except Exception as exc:
            if self.operation_recorder:
                self.operation_recorder.stage_pywbem_result(None, exc)
                self.operation_recorder.record_staged()
            raise
        else:
            if self.operation_recorder:
                self.operation_recorder.stage_pywbem_result(None, None)
                self.operation_recorder.record_staged()
            return

    def GetInstance(self, InstanceName, LocalOnly=None, IncludeQualifiers=None,
                    IncludeClassOrigin=None, PropertyList=None, **extra):
        # pylint: disable=invalid-name,line-too-long
        """
        Retrieve an instance.

        This method performs the GetInstance operation
        (see :term:`DSP0200`). See :ref:`WBEM operations` for a list of all
        methods performing such operations.

        If the operation succeeds, this method returns.
        Otherwise, this method raises an exception.

        Parameters:

          InstanceName (:class:`~pywbem.CIMInstanceName`):
            The instance path of the instance to be retrieved.
            If this object does not specify a namespace, the default namespace
            of the connection is used.
            Its `host` attribute will be ignored.

          LocalOnly (:class:`py:bool`):
            Controls the exclusion of inherited properties from the returned
            instance, as follows:

            * If `False`, inherited properties are not excluded.
            * If `True`, inherited properties are basically excluded, but the
              behavior may be WBEM server specific.
            * If `None`, this parameter is not passed to the WBEM server, and
              causes the server-implemented default to be used. :term:`DSP0200`
              defines that the server-implemented default is `True`.

            This parameter has been deprecated in :term:`DSP0200` and should be
            set to `False` by the caller.

          IncludeQualifiers (:class:`py:bool`):
            Indicates that qualifiers are to be included in the returned
            instance, as follows:

            * If `False`, qualifiers are not included.
            * If `True`, qualifiers are included if the WBEM server implements
              support for this parameter.
            * If `None`, this parameter is not passed to the WBEM server, and
              causes the server-implemented default to be used. :term:`DSP0200`
              defines that the server-implemented default is `False`.

            This parameter has been deprecated in :term:`DSP0200`. Clients
            cannot rely on it being implemented by WBEM servers.

          IncludeClassOrigin (:class:`py:bool`):
            Indicates that class origin information is to be included on each
            property in the returned instance, as follows:

            * If `False`, class origin information is not included.
            * If `True`, class origin information is included.
            * If `None`, this parameter is not passed to the WBEM server, and
              causes the server-implemented default to be used. :term:`DSP0200`
              defines that the server-implemented default is `False`.

          PropertyList (:term:`py:iterable` of :term:`string` or :term:`string`):
            An iterable specifying the names of the properties (or a  string
            that defines a single property) to be included in the returned
            instance (case independent).

            An empty iterable indicates to include no properties.

            If `None`, all properties are included.

        Keyword Arguments:

          extra :
            Additional keyword arguments are passed as additional operation
            parameters to the WBEM server.
            Note that :term:`DSP0200` does not define any additional parameters
            for this operation.

        Returns:

            A :class:`~pywbem.CIMInstance` object that is a representation of
            the retrieved instance.
            Its `path` attribute is a :class:`~pywbem.CIMInstanceName` object
            with its attributes set as follows:

            * `classname`: Name of the creation class of the instance.
            * `keybindings`: Keybindings of the instance.
            * `namespace`: Name of the CIM namespace containing the instance.
            * `host`: `None`, indicating the WBEM server is unspecified.

        Raises:

            Exceptions described in :class:`~pywbem.WBEMConnection`.
        """  # noqa: E501

        if self.operation_recorder:
            self.operation_recorder.reset()
            self.operation_recorder.stage_pywbem_args(
                method='GetInstance',
                InstanceName=InstanceName,
                LocalOnly=LocalOnly,
                IncludeQualifiers=IncludeQualifiers,
                IncludeClassOrigin=IncludeClassOrigin,
                PropertyList=PropertyList,
                **extra)

        try:

            # Strip off host and namespace to make this a "local" object
            namespace = self._iparam_namespace_from_objectname(InstanceName)
            instancename = self._iparam_instancename(InstanceName)
            PropertyList = _iparam_propertylist(PropertyList)

            result = self._imethodcall(
                'GetInstance',
                namespace,
                InstanceName=instancename,
                LocalOnly=LocalOnly,
                IncludeQualifiers=IncludeQualifiers,
                IncludeClassOrigin=IncludeClassOrigin,
                PropertyList=PropertyList,
                **extra)

            instance = result[0][2][0]
            instance.path = instancename
            instance.path.namespace = namespace

        except Exception as exc:
            if self.operation_recorder:
                self.operation_recorder.stage_pywbem_result(None, exc)
                self.operation_recorder.record_staged()
            raise
        else:
            if self.operation_recorder:
                self.operation_recorder.stage_pywbem_result(instance, None)
                self.operation_recorder.record_staged()
            return instance

    def ModifyInstance(self, ModifiedInstance, IncludeQualifiers=None,
                       PropertyList=None, **extra):
        # pylint: disable=invalid-name,line-too-long
        """
        Modify the property values of an instance.

        This method performs the ModifyInstance operation
        (see :term:`DSP0200`). See :ref:`WBEM operations` for a list of all
        methods performing such operations.

        If the operation succeeds, this method returns.
        Otherwise, this method raises an exception.

        Parameters:

          ModifiedInstance (:class:`~pywbem.CIMInstance`):
            A representation of the modified instance, also indicating its
            instance path.

            The `path` attribute of this object identifies the instance to be
            modified. Its `keybindings` attribute is required. If its
            `namespace` attribute is `None`, the default namespace of the
            connection will be used. Its `host` attribute will be ignored.

            The `classname` attribute of the instance path and the `classname`
            attribute of the instance must specify the same class name.

            The properties defined in this object specify the new property
            values for the instance to be modified. Missing properties
            (relative to the class declaration) and properties provided with
            a value of `None` will be set to NULL.

            Typically, this object has been retrieved by other operations,
            such as :meth:`~pywbem.WBEMConnection.GetInstance`.

          IncludeQualifiers (:class:`py:bool`):
            Indicates that qualifiers are to be modified as specified in the
            `ModifiedInstance` parameter, as follows:

            * If `False`, qualifiers not modified.
            * If `True`, qualifiers are modified if the WBEM server implements
              support for this parameter.
            * If `None`, this parameter is not passed to the WBEM server, and
              causes the server-implemented default to be used. :term:`DSP0200`
              defines that the server-implemented default is `True`.

            This parameter has been deprecated in :term:`DSP0200`. Clients
            cannot rely on it being implemented by WBEM servers.

          PropertyList (:term:`py:iterable` of :term:`string` or :term:`string`):
            An iterable specifying the names of the properties (or a  string
            that defines a single property) to be modified (case independent).

            An empty iterable indicates to modify no properties.

            If `None`, all properties are modified.

        Keyword Arguments:

          extra :
            Additional keyword arguments are passed as additional operation
            parameters to the WBEM server.
            Note that :term:`DSP0200` does not define any additional parameters
            for this operation.

        Raises:

            Exceptions described in :class:`~pywbem.WBEMConnection`.
        """  # noqa: E501

        if self.operation_recorder:
            self.operation_recorder.reset()
            self.operation_recorder.stage_pywbem_args(
                method='ModifyInstance',
                ModifiedInstance=ModifiedInstance,
                IncludeQualifiers=IncludeQualifiers,
                PropertyList=PropertyList,
                **extra)

        try:

            # Must pass a named CIMInstance here (i.e path attribute set)
            if ModifiedInstance.path is None:
                raise ValueError(
                    'ModifiedInstance parameter must have path attribute set')
            if ModifiedInstance.path.classname is None:
                raise ValueError(
                    'ModifiedInstance parameter must have classname set in '
                    ' path')
            if ModifiedInstance.classname is None:
                raise ValueError(
                    'ModifiedInstance parameter must have classname set in '
                    'instance')

            namespace = self._iparam_namespace_from_objectname(
                ModifiedInstance.path)
            PropertyList = _iparam_propertylist(PropertyList)

            # Strip off host and namespace to avoid producing an INSTANCEPATH or
            # LOCALINSTANCEPATH element instead of the desired INSTANCENAME
            # element.
            instance = ModifiedInstance.copy()
            instance.path.namespace = None
            instance.path.host = None

            self._imethodcall(
                'ModifyInstance',
                namespace,
                ModifiedInstance=instance,
                IncludeQualifiers=IncludeQualifiers,
                PropertyList=PropertyList,
                **extra)

        except Exception as exc:
            if self.operation_recorder:
                self.operation_recorder.stage_pywbem_result(None, exc)
                self.operation_recorder.record_staged()
            raise
        else:
            if self.operation_recorder:
                self.operation_recorder.stage_pywbem_result(None, None)
                self.operation_recorder.record_staged()
            return

    def CreateInstance(self, NewInstance, namespace=None, **extra):
        # pylint: disable=invalid-name
        """
        Create an instance in a namespace.

        This method performs the CreateInstance operation
        (see :term:`DSP0200`). See :ref:`WBEM operations` for a list of all
        methods performing such operations.

        If the operation succeeds, this method returns.
        Otherwise, this method raises an exception.

        The creation class for the new instance is taken from the `classname`
        attribute of the `NewInstance` parameter.

        The namespace for the new instance is taken from these sources, in
        decreasing order of priority:

          * `namespace` parameter of this method, if not `None`,
          * namespace in `path` attribute of the `NewInstance` parameter, if
            not `None`,
          * default namespace of the connection.

        Parameters:

          NewInstance (:class:`~pywbem.CIMInstance`):
            A representation of the CIM instance to be created.

            The `classname` attribute of this object specifies the creation
            class for the new instance.

            Apart from utilizing its namespace, the `path` attribute is ignored.

            The `properties` attribute of this object specifies initial
            property values for the new CIM instance.

            Instance-level qualifiers have been deprecated in CIM, so any
            qualifier values specified using the `qualifiers` attribute
            of this object will be ignored.

          namespace (:term:`string`):
            Name of the CIM namespace to be used (case independent).

        Keyword Arguments:

          extra :
            Additional keyword arguments are passed as additional operation
            parameters to the WBEM server.
            Note that :term:`DSP0200` does not define any additional parameters
            for this operation.

        Returns:

            A :class:`~pywbem.CIMInstanceName` object that is the instance
            path of the new instance.

        Raises:

            Exceptions described in :class:`~pywbem.WBEMConnection`.
        """

        if self.operation_recorder:
            self.operation_recorder.reset()
            self.operation_recorder.stage_pywbem_args(
                method='CreateInstance',
                NewInstance=NewInstance,
                namespace=namespace,
                **extra)

        try:

            if namespace is None and \
               getattr(NewInstance.path, 'namespace', None) is not None:
                namespace = NewInstance.path.namespace
            namespace = self._iparam_namespace_from_namespace(namespace)

            # Strip off path to avoid producing a VALUE.NAMEDINSTANCE element
            # instead of the desired INSTANCE element.
            instance = NewInstance.copy()
            instance.path = None

            result = self._imethodcall(
                'CreateInstance',
                namespace,
                NewInstance=instance,
                **extra)

            instancename = result[0][2][0]
            instancename.namespace = namespace
            # TODO: Why not accept returned namespace?

        except Exception as exc:
            if self.operation_recorder:
                self.operation_recorder.stage_pywbem_result(None, exc)
                self.operation_recorder.record_staged()
            raise
        else:
            if self.operation_recorder:
                self.operation_recorder.stage_pywbem_result(instancename, None)
                self.operation_recorder.record_staged()
            return instancename

    def DeleteInstance(self, InstanceName, **extra):
        # pylint: disable=invalid-name
        """
        Delete an instance.

        This method performs the DeleteInstance operation
        (see :term:`DSP0200`). See :ref:`WBEM operations` for a list of all
        methods performing such operations.

        If the operation succeeds, this method returns.
        Otherwise, this method raises an exception.

        Parameters:

          InstanceName (:class:`~pywbem.CIMInstanceName`):
            The instance path of the instance to be deleted.
            If this object does not specify a namespace, the default namespace
            of the connection is used.
            Its `host` attribute will be ignored.

        Keyword Arguments:

          extra :
            Additional keyword arguments are passed as additional operation
            parameters to the WBEM server.
            Note that :term:`DSP0200` does not define any additional parameters
            for this operation.

        Raises:

            Exceptions described in :class:`~pywbem.WBEMConnection`.
        """

        if self.operation_recorder:
            self.operation_recorder.reset()
            self.operation_recorder.stage_pywbem_args(
                method='DeleteInstance',
                InstanceName=InstanceName,
                **extra)

        try:

            namespace = self._iparam_namespace_from_objectname(InstanceName)
            instancename = self._iparam_instancename(InstanceName)

            self._imethodcall(
                'DeleteInstance',
                namespace,
                InstanceName=instancename,
                **extra)

        except Exception as exc:
            if self.operation_recorder:
                self.operation_recorder.stage_pywbem_result(None, exc)
                self.operation_recorder.record_staged()
            raise
        else:
            if self.operation_recorder:
                self.operation_recorder.stage_pywbem_result(None, None)
                self.operation_recorder.record_staged()
            return

    #
    # Association operations
    #

    def AssociatorNames(self, ObjectName, AssocClass=None, ResultClass=None,
                        Role=None, ResultRole=None, **extra):
        # pylint: disable=invalid-name, line-too-long
        """
        Retrieve the instance paths of the instances associated to a source
        instance.

        Retrieve the class paths of the classes associated to a source class.

        This method performs the AssociatorNames operation
        (see :term:`DSP0200`). See :ref:`WBEM operations` for a list of all
        methods performing such operations.

        If the operation succeeds, this method returns.
        Otherwise, this method raises an exception.

        Parameters:

          ObjectName:
            The object path of the source object, as follows:

            * For instance-level usage: The instance path of the source
              instance, as a :class:`~pywbem.CIMInstanceName` object.
              If this object does not specify a namespace, the default namespace
              of the connection is used.
              Its `host` attribute will be ignored.

            * For class-level usage: The class path of the source class, as a
              :term:`string` or :class:`~pywbem.CIMClassName` object:

              If specified as a string, the string is interpreted as a class
              name in the default namespace of the connection
              (case independent).

              If specified as a :class:`~pywbem.CIMClassName` object, its `host`
              attribute will be ignored. If this object does not specify
              a namespace, the default namespace of the connection is used.

          AssocClass (:term:`string` or :class:`~pywbem.CIMClassName`):
            Class name of an association class (case independent),
            to filter the result to include only traversals of that association
            class (or subclasses).

            `None` means that no such filtering is peformed.

          ResultClass (:term:`string` or :class:`~pywbem.CIMClassName`):
            Class name of an associated class (case independent),
            to filter the result to include only traversals to that associated
            class (or subclasses).

            `None` means that no such filtering is peformed.

          Role (:term:`string`):
            Role name (= property name) of the source end (case independent),
            to filter the result to include only traversals from that source
            role.

            `None` means that no such filtering is peformed.

          ResultRole (:term:`string`):
            Role name (= property name) of the far end (case independent),
            to filter the result to include only traversals to that far
            role.

            `None` means that no such filtering is peformed.

        Keyword Arguments:

          extra :
            Additional keyword arguments are passed as additional operation
            parameters to the WBEM server.
            Note that :term:`DSP0200` does not define any additional parameters
            for this operation.

        Returns:

            : The returned list of objects depend on the usage:

            * For instance-level usage: A list of
              :class:`~pywbem.CIMInstanceName` objects that are the instance
              paths of the associated instances, with their attributes set as
              follows:

              * `classname`: Name of the creation class of the instance.
              * `keybindings`: Keybindings of the instance.
              * `namespace`: Name of the CIM namespace containing the instance.
              * `host`: Host and optionally port of the WBEM server containing
                the CIM namespace, or `None` if the server did not return host
                information.

            * For class-level usage: A list of :class:`~pywbem.CIMClassName`
              objects that are the class paths of the associated classes, with
              their attributes set as follows:

              * `classname`: Name of the class.
              * `namespace`: Name of the CIM namespace containing the class.
              * `host`: Host and optionally port of the WBEM server containing
                the CIM namespace, or `None` if the server did not return host
                information.

        Raises:

            Exceptions described in :class:`~pywbem.WBEMConnection`.
        """

        if self.operation_recorder:
            self.operation_recorder.reset()
            self.operation_recorder.stage_pywbem_args(
                method='AssociatorNames',
                ObjectName=ObjectName,
                AssocClass=AssocClass,
                ResultClass=ResultClass,
                Role=Role,
                ResultRole=ResultRole,
                **extra)

        try:

            namespace = self._iparam_namespace_from_objectname(ObjectName)
            objectname = self._iparam_objectname(ObjectName)

            result = self._imethodcall(
                'AssociatorNames',
                namespace,
                ObjectName=objectname,
                AssocClass=self._iparam_classname(AssocClass),
                ResultClass=self._iparam_classname(ResultClass),
                Role=Role,
                ResultRole=ResultRole,
                **extra)

            if result is None:
                objects = []
            else:
                objects = [x[2] for x in result[0][2]]

        except Exception as exc:
            if self.operation_recorder:
                self.operation_recorder.stage_pywbem_result(None, exc)
                self.operation_recorder.record_staged()
            raise
        else:
            if self.operation_recorder:
                self.operation_recorder.stage_pywbem_result(objects, None)
                self.operation_recorder.record_staged()
            return objects

    def Associators(self, ObjectName, AssocClass=None, ResultClass=None,
                    Role=None, ResultRole=None, IncludeQualifiers=None,
                    IncludeClassOrigin=None, PropertyList=None, **extra):
        # pylint: disable=invalid-name, line-too-long
        """
        Retrieve the instances associated to a source instance.

        Retrieve the classes associated to a source class.

        This method performs the Associators operation
        (see :term:`DSP0200`). See :ref:`WBEM operations` for a list of all
        methods performing such operations.

        If the operation succeeds, this method returns.
        Otherwise, this method raises an exception.

        Parameters:

          ObjectName:
            The object path of the source object, as follows:

            * For instance-level usage: The instance path of the source
              instance, as a :class:`~pywbem.CIMInstanceName` object.
              If this object does not specify a namespace, the default namespace
              of the connection is used.
              Its `host` attribute will be ignored.

            * For class-level usage: The class path of the source class, as a
              :term:`string` or :class:`~pywbem.CIMClassName` object:

              If specified as a string, the string is interpreted as a class
              name in the default namespace of the connection
              (case independent).

              If specified as a :class:`~pywbem.CIMClassName` object, its `host`
              attribute will be ignored. If this object does not specify
              a namespace, the default namespace of the connection is used.

          AssocClass (:term:`string` or :class:`~pywbem.CIMClassName`):
            Class name of an association class (case independent),
            to filter the result to include only traversals of that association
            class (or subclasses).

            `None` means that no such filtering is peformed.

          ResultClass (:term:`string` or :class:`~pywbem.CIMClassName`):
            Class name of an associated class (case independent),
            to filter the result to include only traversals to that associated
            class (or subclasses).

            `None` means that no such filtering is peformed.

          Role (:term:`string`):
            Role name (= property name) of the source end (case independent),
            to filter the result to include only traversals from that source
            role.

            `None` means that no such filtering is peformed.

          ResultRole (:term:`string`):
            Role name (= property name) of the far end (case independent),
            to filter the result to include only traversals to that far
            role.

            `None` means that no such filtering is peformed.

          IncludeQualifiers (:class:`py:bool`):
            Indicates that qualifiers are to be included in the returned
            instances (or classes), as follows:

            * If `False`, qualifiers are not included.
            * If `True`, qualifiers are included if the WBEM server implements
              support for this parameter.
            * If `None`, this parameter is not passed to the WBEM server, and
              causes the server-implemented default to be used. :term:`DSP0200`
              defines that the server-implemented default is `False`.

            This parameter has been deprecated in :term:`DSP0200`. Clients
            cannot rely on it being implemented by WBEM servers.

          IncludeClassOrigin (:class:`py:bool`):
            Indicates that class origin information is to be included on each
            property or method in the returned instances (or classes), as
            follows:

            * If `False`, class origin information is not included.
            * If `True`, class origin information is included.
            * If `None`, this parameter is not passed to the WBEM server, and
              causes the server-implemented default to be used. :term:`DSP0200`
              defines that the server-implemented default is `False`.

          PropertyList (:term:`py:iterable` of :term:`string` or :term:`string`):
            An iterable specifying the names of the properties (or a  string
            that defines a single property) to be included in the returned
            instances (or classes) (case independent).

            An empty iterable indicates to include no properties.

            If `None`, all properties are included.

        Keyword Arguments:

          extra :
            Additional keyword arguments are passed as additional operation
            parameters to the WBEM server.
            Note that :term:`DSP0200` does not define any additional parameters
            for this operation.

        Returns:

            : The returned list of objects depend on the usage:

            * For instance-level usage: A list of
              :class:`~pywbem.CIMInstance` objects that are representations
              of the associated instances.

              The `path` attribute of each :class:`~pywbem.CIMInstance`
              object is a :class:`~pywbem.CIMInstanceName` object with its
              attributes set as follows:

              * `classname`: Name of the creation class of the instance.
              * `keybindings`: Keybindings of the instance.
              * `namespace`: Name of the CIM namespace containing the instance.
              * `host`: Host and optionally port of the WBEM server containing
                the CIM namespace, or `None` if the server did not return host
                information.

            * For class-level usage: A list of :class:`py:tuple` of
              (classpath, class) objects that are representations of the
              associated classes.

              Each tuple represents one class and has these items:

              * classpath (:class:`~pywbem.CIMClassName`): The class
                path of the class, with its attributes set as follows:

                * `classname`: Name of the class.
                * `namespace`: Name of the CIM namespace containing the class.
                * `host`: Host and optionally port of the WBEM server containing
                  the CIM namespace, or `None` if the server did not return host
                  information.

              * class (:class:`~pywbem.CIMClass`): The representation of the
                class.

        Raises:

            Exceptions described in :class:`~pywbem.WBEMConnection`.
        """  # noqa: E501

        if self.operation_recorder:
            self.operation_recorder.reset()
            self.operation_recorder.stage_pywbem_args(
                method='Associators',
                ObjectName=ObjectName,
                AssocClass=AssocClass,
                ResultClass=ResultClass,
                Role=Role,
                ResultRole=ResultRole,
                IncludeQualifiers=IncludeQualifiers,
                IncludeClassOrigin=IncludeClassOrigin,
                PropertyList=PropertyList,
                **extra)

        try:

            namespace = self._iparam_namespace_from_objectname(ObjectName)
            objectname = self._iparam_objectname(ObjectName)
            PropertyList = _iparam_propertylist(PropertyList)

            result = self._imethodcall(
                'Associators',
                namespace,
                ObjectName=objectname,
                AssocClass=self._iparam_classname(AssocClass),
                ResultClass=self._iparam_classname(ResultClass),
                Role=Role,
                ResultRole=ResultRole,
                IncludeQualifiers=IncludeQualifiers,
                IncludeClassOrigin=IncludeClassOrigin,
                PropertyList=PropertyList,
                **extra)

            if result is None:
                objects = []
            else:
                objects = [x[2] for x in result[0][2]]

        except Exception as exc:
            if self.operation_recorder:
                self.operation_recorder.stage_pywbem_result(None, exc)
                self.operation_recorder.record_staged()
            raise
        else:
            if self.operation_recorder:
                self.operation_recorder.stage_pywbem_result(objects, None)
                self.operation_recorder.record_staged()
            return objects

    def ReferenceNames(self, ObjectName, ResultClass=None, Role=None, **extra):
        # pylint: disable=invalid-name, line-too-long
        """
        Retrieve the instance paths of the association instances that reference
        a source instance.

        Retrieve the class paths of the association classes that reference a
        source class.

        This method performs the ReferenceNames operation
        (see :term:`DSP0200`). See :ref:`WBEM operations` for a list of all
        methods performing such operations.

        If the operation succeeds, this method returns.
        Otherwise, this method raises an exception.

        Parameters:

          ObjectName:
            The object path of the source object, as follows:

            * For instance-level usage: The instance path of the source
              instance, as a :class:`~pywbem.CIMInstanceName` object.
              If this object does not specify a namespace, the default namespace
              of the connection is used.
              Its `host` attribute will be ignored.

            * For class-level usage: The class path of the source class, as a
              :term:`string` or :class:`~pywbem.CIMClassName` object:

              If specified as a string, the string is interpreted as a class
              name in the default namespace of the connection
              (case independent).

              If specified as a :class:`~pywbem.CIMClassName` object, its `host`
              attribute will be ignored. If this object does not specify
              a namespace, the default namespace of the connection is used.

          ResultClass (:term:`string` or :class:`~pywbem.CIMClassName`):
            Class name of an association class (case independent),
            to filter the result to include only traversals of that association
            class (or subclasses).

            `None` means that no such filtering is peformed.

          Role (:term:`string`):
            Role name (= property name) of the source end (case independent),
            to filter the result to include only traversals from that source
            role.

            `None` means that no such filtering is peformed.

        Keyword Arguments:

          extra :
            Additional keyword arguments are passed as additional operation
            parameters to the WBEM server.
            Note that :term:`DSP0200` does not define any additional parameters
            for this operation.

        Returns:

            : The returned list of objects depend on the usage:

            * For instance-level usage: A list of
              :class:`~pywbem.CIMInstanceName` objects that are the instance
              paths of the referencing association instances, with their
              attributes set as follows:

              * `classname`: Name of the creation class of the instance.
              * `keybindings`: Keybindings of the instance.
              * `namespace`: Name of the CIM namespace containing the instance.
              * `host`: Host and optionally port of the WBEM server containing
                the CIM namespace, or `None` if the server did not return host
                information.

            * For class-level usage: A list of :class:`~pywbem.CIMClassName`
              objects that are the class paths of the referencing association
              classes, with their attributes set as follows:

              * `classname`: Name of the class.
              * `namespace`: Name of the CIM namespace containing the class.
              * `host`: Host and optionally port of the WBEM server containing
                the CIM namespace, or `None` if the server did not return host
                information.

        Raises:

            Exceptions described in :class:`~pywbem.WBEMConnection`.
        """

        if self.operation_recorder:
            self.operation_recorder.reset()
            self.operation_recorder.stage_pywbem_args(
                method='ReferenceNames',
                ObjectName=ObjectName,
                ResultClass=ResultClass,
                Role=Role,
                **extra)

        try:

            namespace = self._iparam_namespace_from_objectname(ObjectName)
            objectname = self._iparam_objectname(ObjectName)

            result = self._imethodcall(
                'ReferenceNames',
                namespace,
                ObjectName=objectname,
                ResultClass=self._iparam_classname(ResultClass),
                Role=Role,
                **extra)

            if result is None:
                objects = []
            else:
                objects = [x[2] for x in result[0][2]]

        except Exception as exc:
            if self.operation_recorder:
                self.operation_recorder.stage_pywbem_result(None, exc)
                self.operation_recorder.record_staged()
            raise
        else:
            if self.operation_recorder:
                self.operation_recorder.stage_pywbem_result(objects, None)
                self.operation_recorder.record_staged()
            return objects

    def References(self, ObjectName, ResultClass=None, Role=None,
                   IncludeQualifiers=None, IncludeClassOrigin=None,
                   PropertyList=None, **extra):
        # pylint: disable=invalid-name, line-too-long
        """
        Retrieve the association instances that reference a source instance.

        Retrieve the association classes that reference a source class.

        This method performs the References operation
        (see :term:`DSP0200`). See :ref:`WBEM operations` for a list of all
        methods performing such operations.

        If the operation succeeds, this method returns.
        Otherwise, this method raises an exception.

        Parameters:

          ObjectName:
            The object path of the source object, as follows:

            * For instance-level usage: The instance path of the source
              instance, as a :class:`~pywbem.CIMInstanceName` object.
              If this object does not specify a namespace, the default namespace
              of the connection is used.
              Its `host` attribute will be ignored.

            * For class-level usage: The class path of the source class, as a
              :term:`string` or :class:`~pywbem.CIMClassName` object:

              If specified as a string, the string is interpreted as a class
              name in the default namespace of the connection
              (case independent).

              If specified as a :class:`~pywbem.CIMClassName` object, its `host`
              attribute will be ignored. If this object does not specify
              a namespace, the default namespace of the connection is used.

          ResultClass (:term:`string` or :class:`~pywbem.CIMClassName`):
            Class name of an association class (case independent),
            to filter the result to include only traversals of that association
            class (or subclasses).

            `None` means that no such filtering is peformed.

          Role (:term:`string`):
            Role name (= property name) of the source end (case independent),
            to filter the result to include only traversals from that source
            role.

            `None` means that no such filtering is peformed.

          IncludeQualifiers (:class:`py:bool`):
            Indicates that qualifiers are to be included in the returned
            instances (or classes), as follows:

            * If `False`, qualifiers are not included.
            * If `True`, qualifiers are included if the WBEM server implements
              support for this parameter.
            * If `None`, this parameter is not passed to the WBEM server, and
              causes the server-implemented default to be used. :term:`DSP0200`
              defines that the server-implemented default is `False`.

            This parameter has been deprecated in :term:`DSP0200`. Clients
            cannot rely on it being implemented by WBEM servers.

          IncludeClassOrigin (:class:`py:bool`):
            Indicates that class origin information is to be included on each
            property or method in the returned instances (or classes), as
            follows:

            * If `False`, class origin information is not included.
            * If `True`, class origin information is included.
            * If `None`, this parameter is not passed to the WBEM server, and
              causes the server-implemented default to be used. :term:`DSP0200`
              defines that the server-implemented default is `False`.

          PropertyList (:term:`py:iterable` of :term:`string` or :term:`string`):
            An iterable specifying the names of the properties (or a  string
            that defines a single property) to be included in the returned
            instances (or classes) (case independent).

            An empty iterable indicates to include no properties.

            If `None`, all properties are included.

        Keyword Arguments:

          extra :
            Additional keyword arguments are passed as additional operation
            parameters to the WBEM server.
            Note that :term:`DSP0200` does not define any additional parameters
            for this operation.

        Returns:

            : The returned list of objects depend on the usage:

            * For instance-level usage: A list of
              :class:`~pywbem.CIMInstance` objects that are representations
              of the referencing association instances.

              The `path` attribute of each :class:`~pywbem.CIMInstance`
              object is a :class:`~pywbem.CIMInstanceName` object with its
              attributes set as follows:

              * `classname`: Name of the creation class of the instance.
              * `keybindings`: Keybindings of the instance.
              * `namespace`: Name of the CIM namespace containing the instance.
              * `host`: Host and optionally port of the WBEM server containing
                the CIM namespace, or `None` if the server did not return host
                information.

            * For class-level usage: A list of :class:`py:tuple` of
              (classpath, class) objects that are representations of the
              referencing association classes.

              Each tuple represents one class and has these items:

              * classpath (:class:`~pywbem.CIMClassName`): The class
                path of the class, with its attributes set as follows:

                * `classname`: Name of the class.
                * `namespace`: Name of the CIM namespace containing the class.
                * `host`: Host and optionally port of the WBEM server containing
                  the CIM namespace, or `None` if the server did not return host
                  information.

              * class (:class:`~pywbem.CIMClass`): The representation of the
                class.

        Raises:

            Exceptions described in :class:`~pywbem.WBEMConnection`.
        """  # noqa: E501

        if self.operation_recorder:
            self.operation_recorder.reset()
            self.operation_recorder.stage_pywbem_args(
                method='References',
                ObjectName=ObjectName,
                ResultClass=ResultClass,
                Role=Role,
                IncludeQualifiers=IncludeQualifiers,
                IncludeClassOrigin=IncludeClassOrigin,
                PropertyList=PropertyList,
                **extra)

        try:

            namespace = self._iparam_namespace_from_objectname(ObjectName)
            objectname = self._iparam_objectname(ObjectName)
            PropertyList = _iparam_propertylist(PropertyList)

            result = self._imethodcall(
                'References',
                namespace,
                ObjectName=objectname,
                ResultClass=self._iparam_classname(ResultClass),
                Role=Role,
                IncludeQualifiers=IncludeQualifiers,
                IncludeClassOrigin=IncludeClassOrigin,
                PropertyList=PropertyList,
                **extra)

            if result is None:
                objects = []
            else:
                objects = [x[2] for x in result[0][2]]

        except Exception as exc:
            if self.operation_recorder:
                self.operation_recorder.stage_pywbem_result(None, exc)
                self.operation_recorder.record_staged()
            raise
        else:
            if self.operation_recorder:
                self.operation_recorder.stage_pywbem_result(objects, None)
                self.operation_recorder.record_staged()
            return objects

    #
    # Method invocation operation
    #

    def InvokeMethod(self, MethodName, ObjectName, Params=None, **params):
        # pylint: disable=invalid-name
        """
        Invoke a method on a target instance or on a target class.

        The methods that can be invoked are static and non-static methods
        defined in a class (also known as *extrinsic* methods).
        Static methods can be invoked on instances and on classes.
        Non-static methods can be invoked only on instances.

        This method performs the extrinsic method invocation operation
        (see :term:`DSP0200`). See :ref:`WBEM operations` for a list of all
        methods performing such operations.

        If the operation succeeds, this method returns.
        Otherwise, this method raises an exception.

        Input parameters for the CIM method can be specified using the
        `Params` parameter, and using keyword parameters.
        The overall list of input parameters is formed from the list of
        parameters specified in `Params` (preserving its order), followed by
        the set of keyword parameters (in any order). There is no checking for
        duplicate parameter names.

        Parameters:

          MethodName (:term:`string`):
            Name of the method to be invoked (case independent).

          ObjectName:
            The object path of the target object, as follows:

            * For instance-level usage: The instance path of the target
              instance, as a :class:`~pywbem.CIMInstanceName` object.
              If this object does not specify a namespace, the default namespace
              of the connection is used.
              Its `host` attribute will be ignored.

            * For class-level usage: The class path of the target class, as a
              :term:`string` or :class:`~pywbem.CIMClassName` object:

              If specified as a string, the string is interpreted as a class
              name in the default namespace of the connection
              (case independent).

              If specified as a :class:`~pywbem.CIMClassName` object, its `host`
              attribute will be ignored. If this object does not specify
              a namespace, the default namespace of the connection is used.

          Params (:term:`py:iterable` of tuples of name,value):
            An iterable of input parameters for the CIM method.

            Each iterated item represents a single input parameter for the CIM
            method and must be a ``tuple(name, value)``, with these tuple items:

            * name (:term:`string`):
              Parameter name (case independent)
            * value (:term:`CIM data type`):
              Parameter value

        Keyword Arguments:

          : Each keyword parameter represents a single input parameter for the
            CIM method, with:

            * key (:term:`string`):
              Parameter name (case independent)
            * value (:term:`CIM data type`):
              Parameter value

        Returns:

            A :class:`py:tuple` of (returnvalue, outparams), with these
            tuple items:

            * returnvalue (:term:`CIM data type`):
              Return value of the CIM method.
            * outparams (`NocaseDict`_):
              Dictionary with all provided output parameters of the CIM method,
              with:

              * key (:term:`unicode string`):
                Parameter name, preserving its lexical case
              * value (:term:`CIM data type`):
                Parameter value

        Raises:

            Exceptions described in :class:`~pywbem.WBEMConnection`.
        """

        if self.operation_recorder:
            self.operation_recorder.reset()
            self.operation_recorder.stage_pywbem_args(
                method='InvokeMethod',
                MethodName=MethodName,
                ObjectName=ObjectName,
                Params=Params,
                **params)

        try:

            # Convert string to CIMClassName

            obj = ObjectName

            if isinstance(obj, six.string_types):
                obj = CIMClassName(obj, namespace=self.default_namespace)

            if isinstance(obj, CIMInstanceName) and obj.namespace is None:
                obj = ObjectName.copy()
                obj.namespace = self.default_namespace

            # Make the method call
            result = self._methodcall(MethodName, obj, Params, **params)

            # Convert optional RETURNVALUE into a Python object

            returnvalue = None

            if len(result) > 0 and result[0][0] == 'RETURNVALUE':

                returnvalue = tocimobj(result[0][1]['PARAMTYPE'], result[0][2])
                result = result[1:]

            # Convert zero or more PARAMVALUE elements into dictionary

            output_params = NocaseDict()

            for p in result:
                if p[1] == 'reference':
                    output_params[p[0]] = p[2]
                else:
                    output_params[p[0]] = tocimobj(p[1], p[2])

            result_tuple = (returnvalue, output_params)

        except Exception as exc:
            if self.operation_recorder:
                self.operation_recorder.stage_pywbem_result(None, exc)
                self.operation_recorder.record_staged()
            raise
        else:
            if self.operation_recorder:
                self.operation_recorder.stage_pywbem_result(result_tuple, None)
                self.operation_recorder.record_staged()
            return result_tuple

    #
    # Query operations
    #

    def ExecQuery(self, QueryLanguage, Query, namespace=None, **extra):
        # pylint: disable=invalid-name
        """
        Execute a query in a namespace.

        This method performs the ExecQuery operation
        (see :term:`DSP0200`). See :ref:`WBEM operations` for a list of all
        methods performing such operations.

        If the operation succeeds, this method returns.
        Otherwise, this method raises an exception.

        Parameters:

          QueryLanguage (:term:`string`):
            Name of the query language used in the `Query` parameter, e.g.
            "DMTF:CQL" for CIM Query Language, and "WQL" for WBEM Query
            Language.

          Query (:term:`string`):
            Query string in the query language specified in the `QueryLanguage`
            parameter.

          namespace (:term:`string`):
            Name of the CIM namespace to be used (case independent).

            If `None`, the default namespace of the connection object will be
            used.

        Keyword Arguments:

          extra :
            Additional keyword arguments are passed as additional operation
            parameters to the WBEM server.
            Note that :term:`DSP0200` does not define any additional parameters
            for this operation.

        Returns:

            A list of :class:`~pywbem.CIMInstance` objects that represents
            the query result.

            These instances have their `path` attribute set to identify
            their creation class and the target namespace of the query, but
            they are not addressable instances.

        Raises:

            Exceptions described in :class:`~pywbem.WBEMConnection`.
        """

        if self.operation_recorder:
            self.operation_recorder.reset()
            self.operation_recorder.stage_pywbem_args(
                method='ExecQuery',
                QueryLanguage=QueryLanguage,
                Query=Query,
                namespace=namespace,
                **extra)

        try:

            namespace = self._iparam_namespace_from_namespace(namespace)

            result = self._imethodcall(
                'ExecQuery',
                namespace,
                QueryLanguage=QueryLanguage,
                Query=Query,
                **extra)

            instances = []

            if result is not None:
                instances = [tt[2] for tt in result[0][2]]

            for instance in instances:
                instance.path.namespace = namespace

        except Exception as exc:
            if self.operation_recorder:
                self.operation_recorder.stage_pywbem_result(None, exc)
                self.operation_recorder.record_staged()
            raise
        else:
            if self.operation_recorder:
                self.operation_recorder.stage_pywbem_result(instances, None)
                self.operation_recorder.record_staged()
            return instances

    #
    # Class operations
    #

    def EnumerateClassNames(self, namespace=None, ClassName=None,
                            DeepInheritance=None, **extra):
        # pylint: disable=invalid-name,line-too-long
        """
        Enumerate the names of subclasses of a class, or of the top-level
        classes in a namespace.

        This method performs the EnumerateClassNames operation
        (see :term:`DSP0200`). See :ref:`WBEM operations` for a list of all
        methods performing such operations.

        If the operation succeeds, this method returns.
        Otherwise, this method raises an exception.

        Parameters:

          namespace (:term:`string`):
            Name of the namespace in which the class names are to be
            enumerated (case independent).

            If `None`, the namespace of the `ClassName` parameter will be used,
            if specified as a :class:`~pywbem.CIMClassName` object. If that is
            also `None`, the default namespace of the connection will be used.

          ClassName (:term:`string` or :class:`~pywbem.CIMClassName`):
            Name of the class whose subclasses are to be retrieved
            (case independent).
            If specified as a :class:`~pywbem.CIMClassName` object, its host
            attribute will be ignored.

            If `None`, the top-level classes in the namespace will be
            retrieved.

          DeepInheritance (:class:`py:bool`):
            Indicates that all (direct and indirect) subclasses of the
            specified class or of the top-level classes are to be included in
            the result, as follows:

            * If `False`, only direct subclasses of the specified class or only
              top-level classes are included in the result.
            * If `True`, all direct and indirect subclasses of the specified
              class or the top-level classes and all of their direct and
              indirect subclasses are included in the result.
            * If `None`, this parameter is not passed to the WBEM server, and
              causes the server-implemented default to be used. :term:`DSP0200`
              defines that the server-implemented default is `False`.

            Note, the semantics of the `DeepInheritance` parameter in
            :meth:`~pywbem.WBEMConnection.EnumerateInstances` is different.

        Keyword Arguments:

          extra :
            Additional keyword arguments are passed as additional operation
            parameters to the WBEM server.
            Note that :term:`DSP0200` does not define any additional parameters
            for this operation.

        Returns:

            A list of :term:`unicode string` objects that are the class names
            of the enumerated classes.

        Raises:

            Exceptions described in :class:`~pywbem.WBEMConnection`.
        """

        if self.operation_recorder:
            self.operation_recorder.reset()
            self.operation_recorder.stage_pywbem_args(
                method='EnumerateClassNames',
                namespace=namespace,
                ClassName=ClassName,
                DeepInheritance=DeepInheritance,
                **extra)

        try:

            if namespace is None and isinstance(ClassName, CIMClassName):
                namespace = ClassName.namespace
            namespace = self._iparam_namespace_from_namespace(namespace)
            classname = self._iparam_classname(ClassName)

            result = self._imethodcall(
                'EnumerateClassNames',
                namespace,
                ClassName=classname,
                DeepInheritance=DeepInheritance,
                **extra)

            if result is None:
                classnames = []
            else:
                classnames = [x.classname for x in result[0][2]]

        except Exception as exc:
            if self.operation_recorder:
                self.operation_recorder.stage_pywbem_result(None, exc)
                self.operation_recorder.record_staged()
            raise
        else:
            if self.operation_recorder:
                self.operation_recorder.stage_pywbem_result(classnames, None)
                self.operation_recorder.record_staged()
            return classnames

    def EnumerateClasses(self, namespace=None, ClassName=None,
                         DeepInheritance=None, LocalOnly=None,
                         IncludeQualifiers=None, IncludeClassOrigin=None,
                         **extra):
        # pylint: disable=invalid-name,line-too-long
        """
        Enumerate the subclasses of a class, or the top-level classes in a
        namespace.

        This method performs the EnumerateClasses operation
        (see :term:`DSP0200`). See :ref:`WBEM operations` for a list of all
        methods performing such operations.

        If the operation succeeds, this method returns.
        Otherwise, this method raises an exception.

        Parameters:

          namespace (:term:`string`):
            Name of the namespace in which the classes are to be enumerated
            (case independent).

            If `None`, the namespace of the `ClassName` parameter will be used,
            if specified as a :class:`~pywbem.CIMClassName` object. If that is
            also `None`, the default namespace of the connection will be used.

          ClassName (:term:`string` or :class:`~pywbem.CIMClassName`):
            Name of the class whose subclasses are to be retrieved
            (case independent).
            If specified as a :class:`~pywbem.CIMClassName` object, its host
            attribute will be ignored.

            If `None`, the top-level classes in the namespace will be
            retrieved.

          DeepInheritance (:class:`py:bool`):
            Indicates that all (direct and indirect) subclasses of the
            specified class or of the top-level classes are to be included in
            the result, as follows:

            * If `False`, only direct subclasses of the specified class or only
              top-level classes are included in the result.
            * If `True`, all direct and indirect subclasses of the specified
              class or the top-level classes and all of their direct and
              indirect subclasses are included in the result.
            * If `None`, this parameter is not passed to the WBEM server, and
              causes the server-implemented default to be used. :term:`DSP0200`
              defines that the server-implemented default is `False`.

            Note, the semantics of the `DeepInheritance` parameter in
            :meth:`~pywbem.WBEMConnection.EnumerateInstances` is different.

          LocalOnly (:class:`py:bool`):
            Indicates that inherited properties, methods, and qualifiers are to
            be excluded from the returned classes, as follows.

            * If `False`, inherited elements are not excluded.
            * If `True`, inherited elements are excluded.
            * If `None`, this parameter is not passed to the WBEM server, and
              causes the server-implemented default to be used. :term:`DSP0200`
              defines that the server-implemented default is `True`.

          IncludeQualifiers (:class:`py:bool`):
            Indicates that qualifiers are to be included in the returned
            classes, as follows:

            * If `False`, qualifiers are not included.
            * If `True`, qualifiers are included.
            * If `None`, this parameter is not passed to the WBEM server, and
              causes the server-implemented default to be used. :term:`DSP0200`
              defines that the server-implemented default is `False`.

          IncludeClassOrigin (:class:`py:bool`):
            Indicates that class origin information is to be included on each
            property and method in the returned classes, as follows:

            * If `False`, class origin information is not included.
            * If `True`, class origin information is included.
            * If `None`, this parameter is not passed to the WBEM server, and
              causes the server-implemented default to be used. :term:`DSP0200`
              defines that the server-implemented default is `False`.

        Keyword Arguments:

          extra :
            Additional keyword arguments are passed as additional operation
            parameters to the WBEM server.
            Note that :term:`DSP0200` does not define any additional parameters
            for this operation.

        Returns:

            A list of :class:`~pywbem.CIMClass` objects that are
            representations of the enumerated classes.

        Raises:

            Exceptions described in :class:`~pywbem.WBEMConnection`.
        """

        if self.operation_recorder:
            self.operation_recorder.reset()
            self.operation_recorder.stage_pywbem_args(
                method='EnumerateClasses',
                namespace=namespace,
                ClassName=ClassName,
                DeepInheritance=DeepInheritance,
                LocalOnly=LocalOnly,
                IncludeQualifiers=IncludeQualifiers,
                IncludeClassOrigin=IncludeClassOrigin,
                **extra)

        try:

            if namespace is None and isinstance(ClassName, CIMClassName):
                namespace = ClassName.namespace
            namespace = self._iparam_namespace_from_namespace(namespace)
            classname = self._iparam_classname(ClassName)

            result = self._imethodcall(
                'EnumerateClasses',
                namespace,
                ClassName=classname,
                DeepInheritance=DeepInheritance,
                LocalOnly=LocalOnly,
                IncludeQualifiers=IncludeQualifiers,
                IncludeClassOrigin=IncludeClassOrigin,
                **extra)

            if result is None:
                classes = []
            else:
                classes = result[0][2]

        except Exception as exc:
            if self.operation_recorder:
                self.operation_recorder.stage_pywbem_result(None, exc)
                self.operation_recorder.record_staged()
            raise
        else:
            if self.operation_recorder:
                self.operation_recorder.stage_pywbem_result(classes, None)
                self.operation_recorder.record_staged()
            return classes

    def GetClass(self, ClassName, namespace=None, LocalOnly=None,
                 IncludeQualifiers=None, IncludeClassOrigin=None,
                 PropertyList=None, **extra):
        # pylint: disable=invalid-name, line-too-long
        """
        Retrieve a class.

        This method performs the GetClass operation
        (see :term:`DSP0200`). See :ref:`WBEM operations` for a list of all
        methods performing such operations.

        If the operation succeeds, this method returns.
        Otherwise, this method raises an exception.

        Parameters:

          ClassName (:term:`string` or :class:`~pywbem.CIMClassName`):
            Name of the class to be retrieved (case independent).
            If specified as a :class:`~pywbem.CIMClassName` object, its `host`
            attribute will be ignored.

          namespace (:term:`string`):
            Name of the namespace of the class to be retrieved
            (case independent).

            If `None`, the namespace of the `ClassName` parameter will be used,
            if specified as a :class:`~pywbem.CIMClassName` object. If that is
            also `None`, the default namespace of the connection will be used.

          LocalOnly (:class:`py:bool`):
            Indicates that inherited properties, methods, and qualifiers are to
            be excluded from the returned class, as follows.

            * If `False`, inherited elements are not excluded.
            * If `True`, inherited elements are excluded.
            * If `None`, this parameter is not passed to the WBEM server, and
              causes the server-implemented default to be used. :term:`DSP0200`
              defines that the server-implemented default is `True`.

          IncludeQualifiers (:class:`py:bool`):
            Indicates that qualifiers are to be included in the returned
            class, as follows:

            * If `False`, qualifiers are not included.
            * If `True`, qualifiers are included.
            * If `None`, this parameter is not passed to the WBEM server, and
              causes the server-implemented default to be used. :term:`DSP0200`
              defines that the server-implemented default is `False`.

          IncludeClassOrigin (:class:`py:bool`):
            Indicates that class origin information is to be included on each
            property and method in the returned class, as follows:

            * If `False`, class origin information is not included.
            * If `True`, class origin information is included.
            * If `None`, this parameter is not passed to the WBEM server, and
              causes the server-implemented default to be used. :term:`DSP0200`
              defines that the server-implemented default is `False`.

          PropertyList (:term:`py:iterable` of :term:`string` or :term:`string`):
            An iterable specifying the names of the properties (or a  string
            that defines a single property) to be included in the returned
            class (case independent).

            An empty iterable indicates to include no properties.

            If `None`, all properties are included.

        Keyword Arguments:

          extra :
            Additional keyword arguments are passed as additional operation
            parameters to the WBEM server.
            Note that :term:`DSP0200` does not define any additional parameters
            for this operation.

        Returns:

            A :class:`~pywbem.CIMClass` object that is a representation of the
            retrieved class.

        Raises:

            Exceptions described in :class:`~pywbem.WBEMConnection`.
        """  # noqa: E501

        if self.operation_recorder:
            self.operation_recorder.reset()
            self.operation_recorder.stage_pywbem_args(
                method='GetClass',
                ClassName=ClassName,
                namespace=namespace,
                LocalOnly=LocalOnly,
                IncludeQualifiers=IncludeQualifiers,
                IncludeClassOrigin=IncludeClassOrigin,
                PropertyList=PropertyList,
                **extra)

        try:

            if namespace is None and isinstance(ClassName, CIMClassName):
                namespace = ClassName.namespace
            namespace = self._iparam_namespace_from_namespace(namespace)
            classname = self._iparam_classname(ClassName)
            PropertyList = _iparam_propertylist(PropertyList)

            result = self._imethodcall(
                'GetClass',
                namespace,
                ClassName=classname,
                LocalOnly=LocalOnly,
                IncludeQualifiers=IncludeQualifiers,
                IncludeClassOrigin=IncludeClassOrigin,
                PropertyList=PropertyList,
                **extra)

            klass = result[0][2][0]

        except Exception as exc:
            if self.operation_recorder:
                self.operation_recorder.stage_pywbem_result(None, exc)
                self.operation_recorder.record_staged()
            raise
        else:
            if self.operation_recorder:
                self.operation_recorder.stage_pywbem_result(klass, None)
                self.operation_recorder.record_staged()
            return klass

    def ModifyClass(self, ModifiedClass, namespace=None, **extra):
        # pylint: disable=invalid-name
        """
        Modify a class in a namespace.

        This method performs the ModifyClass operation
        (see :term:`DSP0200`). See :ref:`WBEM operations` for a list of all
        methods performing such operations.

        If the operation succeeds, this method returns.
        Otherwise, this method raises an exception.

        Parameters:

          ModifiedClass (:class:`~pywbem.CIMClass`):
            A representation of the modified class.

            The properties, methods and qualifiers defined in this object
            specify what is to be modified.

            Typically, this object has been retrieved by other operations, such
            as :meth:`~pywbem.WBEMConnection.GetClass`.

          namespace (:term:`string`):
            Name of the namespace in which the class is to be modified
            (case independent).

            If `None`, the default namespace of the connection object will be
            used.

        Keyword Arguments:

          extra :
            Additional keyword arguments are passed as additional operation
            parameters to the WBEM server.
            Note that :term:`DSP0200` does not define any additional parameters
            for this operation.

        Raises:

            Exceptions described in :class:`~pywbem.WBEMConnection`.
        """

        if self.operation_recorder:
            self.operation_recorder.reset()
            self.operation_recorder.stage_pywbem_args(
                method='ModifyClass',
                ModifiedClass=ModifiedClass,
                namespace=namespace,
                **extra)

        try:

            namespace = self._iparam_namespace_from_namespace(namespace)

            klass = ModifiedClass.copy()
            klass.path = None

            self._imethodcall(
                'ModifyClass',
                namespace,
                ModifiedClass=klass,
                **extra)

        except Exception as exc:
            if self.operation_recorder:
                self.operation_recorder.stage_pywbem_result(None, exc)
                self.operation_recorder.record_staged()
            raise
        else:
            if self.operation_recorder:
                self.operation_recorder.stage_pywbem_result(None, None)
                self.operation_recorder.record_staged()
            return

    def CreateClass(self, NewClass, namespace=None, **extra):
        # pylint: disable=invalid-name
        """
        Create a class in a namespace.

        This method performs the CreateClass operation
        (see :term:`DSP0200`). See :ref:`WBEM operations` for a list of all
        methods performing such operations.

        If the operation succeeds, this method returns.
        Otherwise, this method raises an exception.

        Parameters:

          NewClass (:class:`~pywbem.CIMClass`):
            A representation of the class to be created.

            The properties, methods and qualifiers defined in this object
            specify how the class is to be created.

            Its `path` attribute is ignored.

          namespace (:term:`string`):
            Name of the namespace in which the class is to be created
            (case independent).

            If `None`, the default namespace of the connection object will be
            used.

        Keyword Arguments:

          extra :
            Additional keyword arguments are passed as additional operation
            parameters to the WBEM server.
            Note that :term:`DSP0200` does not define any additional parameters
            for this operation.

        Raises:

            Exceptions described in :class:`~pywbem.WBEMConnection`.
        """

        if self.operation_recorder:
            self.operation_recorder.reset()
            self.operation_recorder.stage_pywbem_args(
                method='CreateClass',
                NewClass=NewClass,
                namespace=namespace,
                **extra)

        try:

            namespace = self._iparam_namespace_from_namespace(namespace)

            klass = NewClass.copy()
            klass.path = None

            self._imethodcall(
                'CreateClass',
                namespace,
                NewClass=klass,
                **extra)

        except Exception as exc:
            if self.operation_recorder:
                self.operation_recorder.stage_pywbem_result(None, exc)
                self.operation_recorder.record_staged()
            raise
        else:
            if self.operation_recorder:
                self.operation_recorder.stage_pywbem_result(None, None)
                self.operation_recorder.record_staged()
            return

    def DeleteClass(self, ClassName, namespace=None, **extra):
        # pylint: disable=invalid-name,line-too-long
        """
        Delete a class.

        This method performs the DeleteClass operation
        (see :term:`DSP0200`). See :ref:`WBEM operations` for a list of all
        methods performing such operations.

        If the operation succeeds, this method returns.
        Otherwise, this method raises an exception.

        Parameters:

          ClassName (:term:`string` or :class:`~pywbem.CIMClassName`):
            Name of the class to be deleted (case independent).
            If specified as a :class:`~pywbem.CIMClassName` object, its `host`
            attribute will be ignored.

          namespace (:term:`string`):
            Name of the namespace of the class to be deleted
            (case independent).

            If `None`, the namespace of the `ClassName` parameter will be used,
            if specified as a :class:`~pywbem.CIMClassName` object. If that is
            also `None`, the default namespace of the connection will be used.

        Keyword Arguments:

          extra :
            Additional keyword arguments are passed as additional operation
            parameters to the WBEM server.
            Note that :term:`DSP0200` does not define any additional parameters
            for this operation.

        Raises:

            Exceptions described in :class:`~pywbem.WBEMConnection`.
        """

        if self.operation_recorder:
            self.operation_recorder.reset()
            self.operation_recorder.stage_pywbem_args(
                method='DeleteClass',
                ClassName=ClassName,
                namespace=namespace,
                **extra)

        try:

            if namespace is None and isinstance(ClassName, CIMClassName):
                namespace = ClassName.namespace
            namespace = self._iparam_namespace_from_namespace(namespace)
            classname = self._iparam_classname(ClassName)

            self._imethodcall(
                'DeleteClass',
                namespace,
                ClassName=classname,
                **extra)

        except Exception as exc:
            if self.operation_recorder:
                self.operation_recorder.stage_pywbem_result(None, exc)
                self.operation_recorder.record_staged()
            raise
        else:
            if self.operation_recorder:
                self.operation_recorder.stage_pywbem_result(None, None)
                self.operation_recorder.record_staged()
            return

    #
    # Qualifier operations
    #

    def EnumerateQualifiers(self, namespace=None, **extra):
        # pylint: disable=invalid-name
        """
        Enumerate qualifier declarations in a namespace.

        This method performs the EnumerateQualifiers operation
        (see :term:`DSP0200`). See :ref:`WBEM operations` for a list of all
        methods performing such operations.

        If the operation succeeds, this method returns.
        Otherwise, this method raises an exception.

        Parameters:

          namespace (:term:`string`):
            Name of the namespace in which the qualifier declarations are to be
            enumerated (case independent).

            If `None`, the default namespace of the connection object will be
            used.

        Keyword Arguments:

          extra :
            Additional keyword arguments are passed as additional operation
            parameters to the WBEM server.
            Note that :term:`DSP0200` does not define any additional parameters
            for this operation.

        Returns:

            A list of :class:`~pywbem.CIMQualifierDeclaration` objects that are
            representations of the enumerated qualifier declarations.

        Raises:

            Exceptions described in :class:`~pywbem.WBEMConnection`.
        """

        if self.operation_recorder:
            self.operation_recorder.reset()
            self.operation_recorder.stage_pywbem_args(
                method='EnumerateQualifiers',
                namespace=namespace,
                **extra)

        try:

            namespace = self._iparam_namespace_from_namespace(namespace)

            result = self._imethodcall(
                'EnumerateQualifiers',
                namespace,
                **extra)

            if result is not None:
                qualifiers = result[0][2]
            else:
                qualifiers = []

        except Exception as exc:
            if self.operation_recorder:
                self.operation_recorder.stage_pywbem_result(None, exc)
                self.operation_recorder.record_staged()
            raise
        else:
            if self.operation_recorder:
                self.operation_recorder.stage_pywbem_result(qualifiers, None)
                self.operation_recorder.record_staged()
            return qualifiers

    def GetQualifier(self, QualifierName, namespace=None, **extra):
        # pylint: disable=invalid-name
        """
        Retrieve a qualifier declaration in a namespace.

        This method performs the GetQualifier operation
        (see :term:`DSP0200`). See :ref:`WBEM operations` for a list of all
        methods performing such operations.

        If the operation succeeds, this method returns.
        Otherwise, this method raises an exception.

        Parameters:

          QualifierName (:term:`string`):
            Name of the qualifier declaration to be retrieved
            (case independent).

          namespace (:term:`string`):
            Name of the namespace of the qualifier declaration
            (case independent).

            If `None`, the default namespace of the connection object will be
            used.

        Keyword Arguments:

          extra :
            Additional keyword arguments are passed as additional operation
            parameters to the WBEM server.
            Note that :term:`DSP0200` does not define any additional parameters
            for this operation.

        Returns:

            A :class:`~pywbem.CIMQualifierDeclaration` object that is a
            representation of the retrieved qualifier declaration.

        Raises:

            Exceptions described in :class:`~pywbem.WBEMConnection`.
        """

        if self.operation_recorder:
            self.operation_recorder.reset()
            self.operation_recorder.stage_pywbem_args(
                method='GetQualifier',
                QualifierName=QualifierName,
                namespace=namespace,
                **extra)

        try:

            namespace = self._iparam_namespace_from_namespace(namespace)

            result = self._imethodcall(
                'GetQualifier',
                namespace,
                QualifierName=QualifierName,
                **extra)

            # Must be present, if no exception was raised:
            qualifiername = result[0][2][0]

        except Exception as exc:
            if self.operation_recorder:
                self.operation_recorder.stage_pywbem_result(None, exc)
                self.operation_recorder.record_staged()
            raise
        else:
            if self.operation_recorder:
                self.operation_recorder.stage_pywbem_result(qualifiername,
                                                            None)
                self.operation_recorder.record_staged()
            return qualifiername

    def SetQualifier(self, QualifierDeclaration, namespace=None, **extra):
        # pylint: disable=invalid-name
        """
        Create or modify a qualifier declaration in a namespace.

        This method performs the SetQualifier operation
        (see :term:`DSP0200`). See :ref:`WBEM operations` for a list of all
        methods performing such operations.

        If the operation succeeds, this method returns.
        Otherwise, this method raises an exception.

        Parameters:

          QualifierDeclaration (:class:`~pywbem.CIMQualifierDeclaration`):
            Representation of the qualifier declaration to be created or
            modified.

          namespace (:term:`string`):
            Name of the namespace in which the qualifier declaration is to be
            created or modified (case independent).

            If `None`, the default namespace of the connection object will be
            used.

        Keyword Arguments:

          extra :
            Additional keyword arguments are passed as additional operation
            parameters to the WBEM server.
            Note that :term:`DSP0200` does not define any additional parameters
            for this operation.

        Raises:

            Exceptions described in :class:`~pywbem.WBEMConnection`.
        """

        if self.operation_recorder:
            self.operation_recorder.reset()
            self.operation_recorder.stage_pywbem_args(
                method='SetQualifier',
                QualifierDeclaration=QualifierDeclaration,
                namespace=namespace,
                **extra)

        try:

            namespace = self._iparam_namespace_from_namespace(namespace)

            self._imethodcall(
                'SetQualifier',
                namespace,
                QualifierDeclaration=QualifierDeclaration,
                **extra)

        except Exception as exc:
            if self.operation_recorder:
                self.operation_recorder.stage_pywbem_result(None, exc)
                self.operation_recorder.record_staged()
            raise
        else:
            if self.operation_recorder:
                self.operation_recorder.stage_pywbem_result(None, None)
                self.operation_recorder.record_staged()
            return

    def DeleteQualifier(self, QualifierName, namespace=None, **extra):
        # pylint: disable=invalid-name
        """
        Delete a qualifier declaration in a namespace.

        This method performs the DeleteQualifier operation
        (see :term:`DSP0200`). See :ref:`WBEM operations` for a list of all
        methods performing such operations.

        If the operation succeeds, this method returns.
        Otherwise, this method raises an exception.

        Parameters:

          QualifierName (:term:`string`):
            Name of the qualifier declaration to be deleted (case independent).

          namespace (:term:`string`):
            Name of the namespace in which the qualifier declaration is to be
            deleted (case independent).

            If `None`, the default namespace of the connection object will be
            used.

        Keyword Arguments:

          extra :
            Additional keyword arguments are passed as additional operation
            parameters to the WBEM server.
            Note that :term:`DSP0200` does not define any additional parameters
            for this operation.

        Raises:

            Exceptions described in :class:`~pywbem.WBEMConnection`.
        """

        if self.operation_recorder:
            self.operation_recorder.reset()
            self.operation_recorder.stage_pywbem_args(
                method='SetQualifier',
                QualifierName=QualifierName,
                namespace=namespace,
                **extra)

        try:

            namespace = self._iparam_namespace_from_namespace(namespace)

            self._imethodcall(
                'DeleteQualifier',
                namespace,
                QualifierName=QualifierName,
                **extra)

        except Exception as exc:
            if self.operation_recorder:
                self.operation_recorder.stage_pywbem_result(None, exc)
                self.operation_recorder.record_staged()
            raise
        else:
            if self.operation_recorder:
                self.operation_recorder.stage_pywbem_result(None, None)
                self.operation_recorder.record_staged()
            return


def is_subclass(ch, ns, super_class, sub):
    """Determine if one class is a subclass of another class.

    Parameters:

      ch:
        A CIMOMHandle.  Either a pycimmb.CIMOMHandle or a
        :class:`~pywbem.WBEMConnection` object.

      ns (:term:`string`):
        Namespace (case independent).

      super_class (:term:`string`):
        Super class name (case independent).

      sub:
        The subclass.  This can either be a string or a
        :class:`~pywbem.CIMClass` object.
    """

    lsuper = super_class.lower()
    if isinstance(sub, CIMClass):
        subname = sub.classname
        subclass = sub
    else:
        subname = sub
        subclass = None
    if subname.lower() == lsuper:
        return True
    if subclass is None:
        subclass = ch.GetClass(subname,
                               ns,
                               LocalOnly=True,
                               IncludeQualifiers=False,
                               PropertyList=[],
                               IncludeClassOrigin=False)
    while subclass.superclass is not None:
        if subclass.superclass.lower() == lsuper:
            return True
        subclass = ch.GetClass(subclass.superclass,
                               ns,
                               LocalOnly=True,
                               IncludeQualifiers=False,
                               PropertyList=[],
                               IncludeClassOrigin=False)
    return False


def PegasusUDSConnection(creds=None, **kwargs):
    """ Pegasus specific Unix Domain Socket call. Specific because
        of the location of the file name
    """

    # pylint: disable=invalid-name
    return WBEMConnection('/var/run/tog-pegasus/cimxml.socket', creds,
                          **kwargs)


def SFCBUDSConnection(creds=None, **kwargs):
    """ SFCB specific Unix Domain Socket call. Specific because
        of the location of the file name
    """

    # pylint: disable=invalid-name
    return WBEMConnection('/tmp/sfcbHttpSocket', creds, **kwargs)


def OpenWBEMUDSConnection(creds=None, **kwargs):
    """ Pegasus specific Unix Domain Socket call. Specific because
        of the location of the file name
    """

    # pylint: disable=invalid-name
    return WBEMConnection('/tmp/OW@LCL@APIIPC_72859_Xq47Bf_P9r761-5_J-7_Q',
                          creds, **kwargs)
