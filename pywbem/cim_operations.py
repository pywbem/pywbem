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

"""CIM operations over HTTP.

The `WBEMConnection` class in this module opens a connection to a remote
WBEM server. Across this connection you can run various CIM operations.
Each method of this class corresponds fairly directly to a single CIM
operation.
"""

# This module is meant to be safe for 'import *'.

import re
from datetime import datetime, timedelta
from xml.dom import minidom
from xml.parsers.expat import ExpatError
import six

from . import cim_xml
from .cim_constants import DEFAULT_NAMESPACE
from .cim_types import CIMType, CIMDateTime, atomic_to_cim_xml
from .cim_obj import CIMInstance, CIMInstanceName, CIMClass, \
                     CIMClassName, NocaseDict, _ensure_unicode, tocimxml, \
                     tocimobj
from .cim_http import get_object_header, wbem_request, Error, AuthError, \
                      ConnectionError, TimeoutError
from .tupleparse import ParseError, parse_cim
from .tupletree import dom_to_tupletree

__all__ = ['CIMError', 'WBEMConnection',
           'PegasusUDSConnection', 'SFCBUDSConnection',
           'OpenWBEMUDSConnection']

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


def _check_classname(val):
    """
    Validate a classname.

    At this point, only the type is validated to be a string.
    """
    if not isinstance(val, six.string_types):
        raise ValueError("string expected for classname, not %r" % val)

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

    :Parameters:

      utf8_xml : UTF-8 encoded byte string
        The XML string to be examined.

      meaning : string
        Short text with meaning of the XML string, for messages in exceptions.

    :Exceptions:

      `TypeError`, if invoked with incorrect Python object type for `utf8_xml`.

      `pywbem.ParseError`, if `utf8_xml` contains Bytes that are invalid UTF-8
      sequences (incorrectly encoded or ill-formed) or invalid XML characters.

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
        raise TypeError("utf8_xml argument is not a byte string, "\
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
            cpos1 = max(ifs_pos-context_before, 0)
            cpos2 = min(ifs_pos+context_after, len(utf8_xml))
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
        ies_seq = utf8_xml[_p1:_p2+1]
        for ies_ord in six.iterbytes(ies_seq):
            exc_txt += " 0x%02X" % ies_ord
        cpos1 = max(_p1-context_before, 0)
        cpos2 = min(_p2+context_after, len(utf8_xml))
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
            cpos1 = max(ixc_pos-context_before, 0)
            cpos2 = min(ixc_pos+context_after, len(utf8_xml_u))
            exc_txt += "\n  At offset %d: U+%04X, CIM-XML snippet: %r" % \
                (ixc_pos, ord(ixc_char_u), utf8_xml_u[cpos1:cpos2])
        raise ParseError(exc_txt)

    return utf8_xml


class CIMError(Error):
    """
    Exception indicating that the WBEM server has returned an error response
    with a CIM status code.

    The exception value is a tuple of
    ``(error_code, description, exception_obj)``, where:

      * ``error_code``: the numeric CIM status code. See `cim_constants` for
        constants defining CIM status code values.

      * ``description``: a string (`unicode` or UTF-8 encoded `str`)
        that is the CIM status description text returned by the server,
        representing a human readable message describing the error.

      * ``exception_obj``: the underlying exception object that caused this
        exception to be raised, or ``None``. Will always be ``None``.
    """
    pass

class WBEMConnection(object):
    """
    A client's connection to a WBEM server. This is the main class of the
    PyWBEM client.

    The connection object knows a default CIM namespace, which is used when no
    namespace is specified on subsequent CIM operations (that support
    specifying namespaces). Thus, the connection object can be used as a
    connection to multiple CIM namespaces on a WBEM server (when the namespace
    is specified on subsequent operations), or as a connection to only the
    default namespace (this allows omitting the namespace on subsequent
    operations).

    As usual in HTTP, there is no persistent TCP connection; the connectedness
    provided by this class is  only conceptual. That is, the creation of the
    connection object does not cause any interaction with the WBEM server, and
    each subsequent CIM operation performs an independent, state-less
    HTTP/HTTPS request.

    After creating a `WBEMConnection` object, various methods may be called on
    the object, which cause CIM operations to be invoked on the WBEM server.
    All these methods take regular Python objects or objects defined in
    `cim_types` as arguments, and return the same.
    The caller does not need to know about the CIM-XML encoding that is used
    underneath (It should be possible to use a different transport below this
    layer without disturbing any callers).

    The connection remembers the XML of the last request and last reply if
    debugging is turned on via the `debug` instance variable of the connection
    object.
    This may be useful in debugging: If a problem occurs, you can examine the
    `last_request` and `last_reply` instance variables of the connection
    object. These are the prettified XML of request and response, respectively.
    The real request and response that are sent and received are available in
    the `last_raw_request` and `last_raw_reply` instance variables of the
    connection object.

    The methods of this class may raise the following exceptions:

    * Exceptions indicating processing errors:

      - `pywbem.ConnectionError` - A connection with the WBEM server could not
        be established or broke down.

      - `pywbem.AuthError` - Authentication failed with the WBEM server.

      - `pywbem.ParseError` - The response from the WBEM server cannot be
        parsed (for example, invalid characters or UTF-8 sequences, ill-formed
        XML, or invalid CIM-XML).

      - `pywbem.CIMError` - The WBEM server returned an error response with a
        CIM status code.

      - `pywbem.TimeoutError` - The WBEM server did not respond in time and the
        client timed out.

    * Exceptions indicating programming errors:

      - `TypeError`
      - `KeyError`
      - `ValueError`
      - `AttributeError`
      - ... possibly others ...

      Exceptions indicating programming errors should not happen and should be
      reported as bugs, unless caused by the code using this class.

    :Ivariables:

      ...
        All parameters of `__init__` are set as instance variables.

      debug : `bool`
        A boolean indicating whether logging of the last request and last reply
        is enabled.

        The initial value of this instance variable is `False`.
        Debug logging can be enabled for future operations by setting this
        instance variable to `True`.

      last_request : `unicode`
        CIM-XML data of the last request sent to the WBEM server
        on this connection, formatted as prettified XML. Prior to sending the
        very first request on this connection object, it is `None`.

      last_raw_request : `unicode`
        CIM-XML data of the last request sent to the WBEM server
        on this connection, formatted as it was sent. Prior to sending the
        very first request on this connection object, it is `None`.

      last_reply : `unicode`
        CIM-XML data of the last response received from the WBEM server
        on this connection, formatted as prettified XML. Prior to sending the
        very first request on this connection object, while waiting for any
        response, it is `None`.

      last_raw_reply : `unicode`
        CIM-XML data of the last response received from the WBEM server
        on this connection, formatted as it was received. Prior to sending the
        very first request on this connection object, while waiting for any
        response, it is `None`.
    """

    def __init__(self, url, creds=None, default_namespace=DEFAULT_NAMESPACE,
                 x509=None, verify_callback=None, ca_certs=None,
                 no_verification=False, timeout=None):
        """
        Initialize the `WBEMConnection` object.

        :Parameters:

          url : string
            URL of the WBEM server (e.g. ``"https://10.11.12.13:6988"``).

            TODO: Describe supported formats.

          creds
            Credentials for authenticating with the WBEM server. Currently,
            that is always a tuple of ``(userid, password)``, where:

            * ``userid`` is a string that is the userid to be used for
              authenticating with the WBEM server.

            * ``password`` is a string that is the password for that userid.

          default_namespace : string
            Optional: Name of the CIM namespace to be used by default (if no
            namespace is specified for an operation).

            Default: See method definition.

          x509 : dictionary
            Optional: X.509 certificates for HTTPS to be used instead of the
            credentials provided in the `creds` parameter. This parameter is
            used only when the `url` parameter specifies a scheme of ``https``.

            If `None`, certificates are not used (and credentials are used
            instead).

            Otherwise, certificates are used instead of the credentials, and
            this parameter must be a dictionary containing the following
            key/value pairs:

            * ``'cert_file'`` : The file path of a file containing an X.509
              certificate.

            * ``'key_file'`` : The file path of a file containing the private
              key belonging to the public key that is part of the X.509
              certificate file.

            Default: `None`.

          verify_callback : function
            Optional: Registers a callback function that will be called to
            verify the certificate returned by the WBEM server during the SSL
            handshake, in addition to the verification alreay performed by
            `M2Crypto`.

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
              that the returned is currently validated; any other value
              indicates the distance of the currently validated certificate to
              the returned certificate in its chain of trust.

            * an integer that indicates whether the validation of the
              certificate specified in the second argument passed or did not
              pass the validation by `M2Crypto`. A value of 1 indicates a
              successful validation and 0 an unsuccessful one.

            The callback function must return `True` if the verification
            passes and `False` otherwise.

            Default: `None`.

          ca_certs : string
            Optional: Location of CA certificates (trusted certificates) for
            verification purposes.

            The parameter value is either the directory path of a directory
            prepared using the ``c_rehash`` tool included with OpenSSL, or the
            file path of a file in PEM format.

            If `None`, the default system path will be used.

            Default: `None`.

          no_verification : `bool`
            Optional: Indicates that verification of the certificate returned
            by the WBEM server is disabled (both by `M2Crypto` and by the
            callback function specified in `verify_callback`).

            Disabling the verification is insecure and should be avoided.

            If `True`, verification is disabled; otherwise, it is enabled.

            Default: `False`.

          timeout : number
            Timeout in seconds, for requests sent to the server. If the server
            did not respond within the timeout duration, the socket for the
            connection will be closed, causing a `TimeoutError` to be raised.

            A value of ``None`` means there is no timeout.

            A value of ``0`` means the timeout is very short, and does not
            really make any sense.

            Note that not all situations can be handled within this timeout, so
            for some issues, operations may take longer before raising an
            exception.

        :Exceptions:

            See the list of exceptions described in `WBEMConnection`.
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

    def __repr__(self):
        """
        Return a representation of the connection object with the major
        instance variables, except for the password in the credentials.

        TODO: Change to show all instance variables.
        """
        if self.creds is None:
            user = 'anonymous'
        else:
            user = 'user=%s' % self.creds[0]
        return "%s(%s, %s, namespace=%s)" % \
            (self.__class__.__name__, self.url, user,
             self.default_namespace)

    def imethodcall(self, methodname, namespace, **params):
        """
        Perform an intrinsic method call (= CIM operation).

        This is a low-level function that is used by the operation-specific
        methods of this class (e.g. `EnumerateInstanceNames`). In general,
        clients should call these operation-specific methods instead of this
        function.

        The parameters are automatically converted to the right CIM-XML
        elements.

        :Returns:

            A tupletree (see `tupletree` module) with an ``IRETURNVALUE``
            element at the root.

        :Exceptions:

            See the list of exceptions described in `WBEMConnection`.
        """

        # Create HTTP headers

        headers = ['CIMOperation: MethodCall',
                   'CIMMethod: %s' % methodname,
                   get_object_header(namespace)]

        # Create parameter list

        plist = [cim_xml.IPARAMVALUE(x[0], tocimxml(x[1])) \
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
                debug=self.debug)
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
            reply_dom = minidom.parseString(reply_xml)
        except ParseError as exc:
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
                    # minidom.parseString() failed.
                    raise ParseError(msg) # data from previous exception

        if self.debug:
            pretty_reply = reply_dom.toprettyxml(indent='  ')
            self.last_reply = re.sub(r'>( *[\r\n]+)+( *)<', r'>\n\2<',
                                     pretty_reply) # remove extra empty lines

        # Parse response

        tup_tree = parse_cim(dom_to_tupletree(reply_dom))

        if tup_tree[0] != 'CIM':
            raise ParseError('Expecting CIM element, got %s' % tup_tree[0])
        tup_tree = tup_tree[2]

        if tup_tree[0] != 'MESSAGE':
            raise ParseError('Expecting MESSAGE element, got %s' % tup_tree[0])
        tup_tree = tup_tree[2]

        if len(tup_tree) != 1 or tup_tree[0][0] != 'SIMPLERSP':
            raise ParseError('Expecting one SIMPLERSP element')
        tup_tree = tup_tree[0][2]

        if tup_tree[0] != 'IMETHODRESPONSE':
            raise ParseError('Expecting IMETHODRESPONSE element, got %s' %\
                             tup_tree[0])

        if tup_tree[1]['NAME'] != methodname:
            raise ParseError('Expecting attribute NAME=%s, got %s' %\
                             (methodname, tup_tree[1]['NAME']))
        tup_tree = tup_tree[2]

        # At this point we either have a IRETURNVALUE, ERROR element
        # or None if there was no child nodes of the IMETHODRESPONSE
        # element.

        if tup_tree is None:
            return None

        if tup_tree[0] == 'ERROR':
            code = int(tup_tree[1]['CODE'])
            if 'DESCRIPTION' in tup_tree[1]:
                raise CIMError(code, tup_tree[1]['DESCRIPTION'])
            raise CIMError(code, 'Error code %s' % tup_tree[1]['CODE'])

        if tup_tree[0] != 'IRETURNVALUE':
            raise ParseError('Expecting IRETURNVALUE element, got %s' \
                             % tup_tree[0])

        return tup_tree

    # pylint: disable=invalid-name
    def methodcall(self, methodname, localobject, Params=None, **params):
        """
        Perform an extrinsic method call (= CIM method invocation).

        This is a low-level function that is used by the 'InvokeMethod'
        method of this class. In general, clients should use 'InvokeMethod'
        instead of this function.

        The Python method parameters are automatically converted to the right
        CIM-XML elements. See `InvokeMethod` for details.

        :Returns:

            A tupletree (see `tupletree` module) with a ``RETURNVALUE``
            element at the root.

        :Exceptions:

            See the list of exceptions described in `WBEMConnection`.
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
                debug=self.debug)
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
            reply_dom = minidom.parseString(reply_xml)
        except ParseError as exc:
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
                    # minidom.parseString() failed.
                    raise ParseError(msg) # data from previous exception

        if self.debug:
            pretty_reply = reply_dom.toprettyxml(indent='  ')
            self.last_reply = re.sub(r'>( *[\r\n]+)+( *)<', r'>\n\2<',
                                     pretty_reply) # remove extra empty lines

        # Parse response

        tt = parse_cim(dom_to_tupletree(reply_dom))

        if tt[0] != 'CIM':
            raise ParseError('Expecting CIM element, got %s' % tt[0])
        tt = tt[2]

        if tt[0] != 'MESSAGE':
            raise ParseError('Expecting MESSAGE element, got %s' % tt[0])
        tt = tt[2]

        if len(tt) != 1 or tt[0][0] != 'SIMPLERSP':
            raise ParseError('Expecting one SIMPLERSP element')
        tt = tt[0][2]

        if tt[0] != 'METHODRESPONSE':
            raise ParseError('Expecting METHODRESPONSE element, got %s' %\
                             tt[0])

        if tt[1]['NAME'] != methodname:
            raise ParseError('Expecting attribute NAME=%s, got %s' %\
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

    #
    # Instance provider API
    #

    def EnumerateInstanceNames(self, ClassName, namespace=None, **params):
        # pylint: disable=invalid-name
        """
        Enumerate the instance paths of instances of a class (including
        instances of its subclasses).

        This method performs the EnumerateInstanceNames CIM-XML operation.
        If the operation succeeds, this method returns.
        Otherwise, this method raises an exception.

        :Parameters:

          ClassName : string
            Name of the class to be enumerated.

          namespace : string
            Optional: Name of the CIM namespace to be used. The value `None`
            causes the default namespace of the connection object to be used.

            Default: `None`.

        :Returns:

            A list of `CIMInstanceName` objects that are the enumerated
            instance paths.

        :Exceptions:

            See the list of exceptions described in `WBEMConnection`.
        """

        if namespace is None:
            namespace = self.default_namespace

        result = self.imethodcall(
            'EnumerateInstanceNames',
            namespace,
            ClassName=CIMClassName(ClassName),
            **params)

        names = []

        if result is not None:
            names = result[2]

        for n in names:
            setattr(n, 'namespace', namespace)

        return names

    def EnumerateInstances(self, ClassName, namespace=None, **params):
        # pylint: disable=invalid-name
        """
        Enumerate the instances of a class (including instances of its
        subclasses).

        This method performs the EnumerateInstances CIM-XML operation.
        If the operation succeeds, this method returns.
        Otherwise, this method raises an exception.

        :Parameters:

          ClassName : string
            Name of the class to be enumerated.

          namespace : string
            Optional: Name of the CIM namespace to be used. The value `None`
            causes the default namespace of the connection object to be used.

            Default: `None`.

          LocalOnly : `bool`
            Optional: Controls the exclusion of inherited properties from the
            returned instances, as follows:

            * If `False`, inherited properties are not excluded.
            * If `True`, the behavior is WBEM server specific.

            Default: `True`.

            This parameter has been deprecated in CIM-XML and should be set to
            `False` by the caller.

          DeepInheritance : `bool`
            Optional: Indicates that properties added by subclasses of the
            specified class are to be included in the returned instances.
            Note, the semantics of this parameter differs between instance and
            class level operations.

            Default: `True`.

          IncludeQualifiers : `bool`
            Optional: Indicates that qualifiers are to be included in the
            returned instance.

            Default: `False`.

            This parameter has been deprecated in CIM-XML. Clients cannot rely
            on it being implemented by WBEM servers.

          IncludeClassOrigin : `bool`
            Optional: Indicates that class origin information is to be included
            on each property in the returned instances.

            Default: `False`.

          PropertyList : iterable of string
            Optional: An iterable specifying the names of the properties to be
            included in the returned instances. An empty iterable indicates to
            include no properties. A value of `None` for this parameter
            indicates to include all properties.

            Default: `None`.

        :Returns:

            A list of `CIMInstance` objects that are representations of
            the enumerated instances.

        :Exceptions:

            See the list of exceptions described in `WBEMConnection`.
        """

        if namespace is None:
            namespace = self.default_namespace

        result = self.imethodcall(
            'EnumerateInstances',
            namespace,
            ClassName=CIMClassName(ClassName),
            **params)

        instances = []

        if result is not None:
            instances = result[2]

        for i in instances:
            setattr(i.path, 'namespace', namespace)

        return instances

    def GetInstance(self, InstanceName, **params):
        # pylint: disable=invalid-name
        """
        Retrieve an instance.

        This method performs the GetInstance CIM-XML operation.
        If the operation succeeds, this method returns.
        Otherwise, this method raises an exception.

        :Parameters:

          InstanceName : `CIMInstanceName`
            Instance path of the instance to be retrieved.

          LocalOnly : `bool`
            Optional: Controls the exclusion of inherited properties from the
            returned instance, as follows:

            * If `False`, inherited properties are not excluded.
            * If `True`, the behavior is WBEM server specific.

            Default: `True`.

            This parameter has been deprecated in CIM-XML and should be set to
            `False` by the caller.

          IncludeQualifiers : `bool`
            Optional: Indicates that qualifiers are to be included in the
            returned instance.

            Default: `False`.

            This parameter has been deprecated in CIM-XML. Clients cannot rely
            on it being implemented by WBEM servers.

          IncludeClassOrigin : `bool`
            Optional: Indicates that class origin information is to be included
            on each property in the returned instance.

            Default: `False`.

          PropertyList : iterable of string
            Optional: An iterable specifying the names of the properties to be
            included in the returned instances. An empty iterable indicates to
            include no properties. A value of `None` for this parameter
            indicates to include all properties.

            Default: `None`.

        :Returns:

            A `CIMInstance` object that is a representation of the
            retrieved instance.

        :Exceptions:

            See the list of exceptions described in `WBEMConnection`.
        """

        # Strip off host and namespace to make this a "local" object

        iname = InstanceName.copy()
        iname.host = None
        iname.namespace = None

        if InstanceName.namespace is None:
            namespace = self.default_namespace
        else:
            namespace = InstanceName.namespace

        result = self.imethodcall(
            'GetInstance',
            namespace,
            InstanceName=iname,
            **params)

        instance = result[2][0]
        instance.path = InstanceName
        instance.path.namespace = namespace

        return instance

    def DeleteInstance(self, InstanceName, **params):
        # pylint: disable=invalid-name
        """
        Delete an instance.

        This method performs the DeleteInstance CIM-XML operation.
        If the operation succeeds, this method returns.
        Otherwise, this method raises an exception.

        :Parameters:

          InstanceName : `CIMInstanceName`
            Instance path of the instance to be deleted.

        :Exceptions:

            See the list of exceptions described in `WBEMConnection`.
        """

        # Strip off host and namespace to make this a "local" object

        iname = InstanceName.copy()
        iname.host = None
        iname.namespace = None

        if InstanceName.namespace is None:
            namespace = self.default_namespace
        else:
            namespace = InstanceName.namespace

        self.imethodcall(
            'DeleteInstance',
            namespace,
            InstanceName=iname,
            **params)

    def CreateInstance(self, NewInstance, **params):
        # pylint: disable=invalid-name
        """
        Create an instance.

        This method performs the CreateInstance CIM-XML operation.
        If the operation succeeds, this method returns.
        Otherwise, this method raises an exception.

        :Parameters:

          NewInstance : `CIMInstance`
            A representation of the instance to be created.

            The `namespace` and `classname` instance variables of this object
            specify CIM namespace and creation class for the new instance,
            respectively.
            An instance path specified using the `path` instance variable of
            this object will be ignored.

            The `properties` instance variable of this object specifies initial
            property values for the new instance.

            Instance-level qualifiers have been deprecated in CIM, so any
            qualifier values specified using the `qualifiers` instance variable
            of this object will be ignored.

        :Returns:

            `CIMInstanceName` object that is the instance path of the new
            instance.

        :Exceptions:

            See the list of exceptions described in `WBEMConnection`.
        """

        # Take namespace path from object parameter

        if NewInstance.path is not None and \
           NewInstance.path.namespace is not None:
            namespace = NewInstance.path.namespace
        else:
            namespace = self.default_namespace

        # Strip off path to avoid producing a VALUE.NAMEDINSTANCE
        # element instead of an INSTANCE element.

        instance = NewInstance.copy()
        instance.path = None

        result = self.imethodcall(
            'CreateInstance',
            namespace,
            NewInstance=instance,
            **params)

        name = result[2][0]
        name.namespace = namespace

        return name

    def ModifyInstance(self, ModifiedInstance, **params):
        # pylint: disable=invalid-name
        """
        Modify the property values of an instance.

        This method performs the ModifyInstance CIM-XML operation.
        If the operation succeeds, this method returns.
        Otherwise, this method raises an exception.

        :Parameters:

          ModifiedInstance : `CIMInstance`
            A representation of the modified instance. This object needs to
            contain any new property values and the instance path of the
            instance to be modified. Missing properties (relative to the class
            declaration) and properties provided with a value of `None` will be
            set to NULL. Typically, this object has been retrieved by other
            operations, such as GetInstance.

          IncludeQualifiers : `bool`
            Optional: Indicates that qualifiers are to be modified as specified
            in the `ModifiedInstance` parameter.

            Default: `True`.

            This parameter has been deprecated in CIM-XML. Clients cannot rely
            on it being implemented by WBEM servers.

          PropertyList : iterable of string
            Optional: An iterable specifying the names of the properties to be
            modified. An empty iterable indicates to modify no properties. A
            value of `None` for this parameter indicates to modify all
            properties.

            Default: `None`.

        :Exceptions:

            See the list of exceptions described in `WBEMConnection`.
        """

        # Must pass a named CIMInstance here (i.e path attribute set)

        if ModifiedInstance.path is None:
            raise ValueError(
                'ModifiedInstance parameter must have path attribute set')

        # Take namespace path from object parameter

        if ModifiedInstance.path.namespace is None:
            namespace = self.default_namespace
        else:
            namespace = ModifiedInstance.path.namespace

        instance = ModifiedInstance.copy()
        instance.path.namespace = None

        self.imethodcall(
            'ModifyInstance',
            namespace,
            ModifiedInstance=instance,
            **params)

    def ExecQuery(self, QueryLanguage, Query, namespace=None):
        # pylint: disable=invalid-name
        """
        Execute a query in a namespace.

        This method performs the ExecQuery CIM-XML operation.
        If the operation succeeds, this method returns.
        Otherwise, this method raises an exception.

        :Parameters:

          QueryLanguage : string
            Name of the query language used in the `Query` parameter.

          Query : string
            Query string in the query language specified in the `QueryLanguage`
            parameter.

          namespace : string
            Optional: Name of the CIM namespace to be used. The value `None`
            causes the default namespace of the connection object to be used.

            Default: `None`.

        :Returns:

            A list of `CIMInstance` objects that represents the query
            result.
            These instances have their `path` instance variable set to identify
            their creation class and the target namespace of the query, but
            they are not addressable instances.

        :Exceptions:

            See the list of exceptions described in `WBEMConnection`.
        """

        if namespace is None:
            namespace = self.default_namespace

        result = self.imethodcall(
            'ExecQuery',
            namespace,
            QueryLanguage=QueryLanguage,
            Query=Query)

        instances = []

        if result is not None:
            instances = [tt[2] for tt in result[2]]

        for i in instances:
            setattr(i.path, 'namespace', namespace)

        return instances

    #
    # Schema management API
    #

    def _map_classname_param(self, params): # pylint: disable=no-self-use
        """Convert string ClassName parameter to a CIMClassName."""

        if 'ClassName' in params and \
           isinstance(params['ClassName'], six.string_types):
            params['ClassName'] = CIMClassName(params['ClassName'])

        return params

    def EnumerateClassNames(self, namespace=None, **params):
        # pylint: disable=invalid-name
        """
        Enumerate the names of subclasses of a class, or of the top-level
        classes in a namespace.

        This method performs the EnumerateClassNames CIM-XML operation.
        If the operation succeeds, this method returns.
        Otherwise, this method raises an exception.

        :Parameters:

          namespace : string
            Optional: Name of the namespace in which the class names are to be
            enumerated.
            The value `None` causes the default namespace of the connection to
            be used.

            Default: `None`

          ClassName : string
            Optional: Name of the class whose subclasses are to be retrieved.
            The value `None` causes the top-level classes in the namespace to
            be retrieved.

            Default: `None`

          DeepInheritance : `bool`
            Optional: Indicates that all (direct and indirect) subclasses of
            the specified class or of the top-level classes are to be included
            in the result.
            `False` indicates that only direct subclasses of the specified
            class or ony top-level classes are to be included in the result.

            Note, the semantics of this parameter differs between instance and
            class level operations.

            Default: `False`.

        :Returns:

            A list of strings that are the class names of the enumerated
            classes.

        :Exceptions:

            See the list of exceptions described in `WBEMConnection`.
        """

        params = self._map_classname_param(params)

        if namespace is None:
            namespace = self.default_namespace

        result = self.imethodcall(
            'EnumerateClassNames',
            namespace,
            **params)

        if result is None:
            return []
        else:
            return [x.classname for x in result[2]]

    def EnumerateClasses(self, namespace=None, **params):
        # pylint: disable=invalid-name
        """
        Enumerate the subclasses of a class, or the top-level classes in a
        namespace.

        This method performs the EnumerateClasses CIM-XML operation.
        If the operation succeeds, this method returns.
        Otherwise, this method raises an exception.

        :Parameters:

          namespace : string
            Optional: Name of the namespace in which the classes are to be
            enumerated.
            The value `None` causes the default namespace of the connection to
            be used.

            Default: `None`

          ClassName : string
            Optional: Name of the class whose subclasses are to be retrieved.
            The value `None` causes the top-level classes in the namespace to
            be retrieved.

            Default: `None`

          DeepInheritance : `bool`
            Optional: Indicates that all (direct and indirect) subclasses of
            the specified class or of the top-level classes are to be included
            in the result.
            `False` indicates that only direct subclasses of the specified
            class or ony top-level classes are to be included in the result.

            Note, the semantics of this parameter differs between instance and
            class level operations.

            Default: `False`.

          LocalOnly : `bool`
            Optional: Indicates that inherited properties, methods, and
            qualifiers are to be excluded from the returned classes.

            Default: `True`.

          IncludeQualifiers : `bool`
            Optional: Indicates that qualifiers are to be included in the
            returned classes.

            Default: `False`.

          IncludeClassOrigin : `bool`
            Optional: Indicates that class origin information is to be included
            on each property and method in the returned classes.

            Default: `False`.

        :Returns:

            A list of `CIMClass` objects that are representations of the
            enumerated classes.

        :Exceptions:

            See the list of exceptions described in `WBEMConnection`.
        """

        params = self._map_classname_param(params)

        if namespace is None:
            namespace = self.default_namespace

        result = self.imethodcall(
            'EnumerateClasses',
            namespace,
            **params)

        if result is None:
            return []

        return result[2]

    def GetClass(self, ClassName, namespace=None, **params):
        # pylint: disable=invalid-name
        """
        Retrieve a class.

        This method performs the GetClass CIM-XML operation.
        If the operation succeeds, this method returns.
        Otherwise, this method raises an exception.

        :Parameters:

          ClassName : string
            Name of the class to be retrieved.

          namespace : string
            Optional: Name of the namespace of the class to be retrieved.
            The value `None` causes the default namespace of the connection to
            be used.

            Default: `None`

          LocalOnly : `bool`
            Optional: Indicates that inherited properties, methods, and
            qualifiers are to be excluded from the returned class.

            Default: `True`.

          IncludeQualifiers : `bool`
            Optional: Indicates that qualifiers are to be included in the
            returned class.

            Default: `False`.

          IncludeClassOrigin : `bool`
            Optional: Indicates that class origin information is to be included
            on each property and method in the returned class.

            Default: `False`.

          PropertyList : iterable of string
            Optional: An iterable specifying the names of the properties to be
            included in the returned class. An empty iterable indicates to
            include no properties. A value of `None` for this parameter
            indicates to include all properties.

            Default: `None`.

        :Returns:

            A `CIMClass` object that is a representation of the
            retrieved class.

        :Exceptions:

            See the list of exceptions described in `WBEMConnection`.
        """

        params = self._map_classname_param(params)

        if namespace is None:
            namespace = self.default_namespace

        result = self.imethodcall(
            'GetClass',
            namespace,
            ClassName=CIMClassName(ClassName),
            **params)

        return result[2][0]

    def DeleteClass(self, ClassName, namespace=None, **params):
        # pylint: disable=invalid-name
        """
        Delete a class.

        This method performs the DeleteClass CIM-XML operation.
        If the operation succeeds, this method returns.
        Otherwise, this method raises an exception.

        :Parameters:

          ClassName : string
            Name of the class to be deleted.

          namespace : string
            Optional: Name of the namespace of the class to be deleted.
            The value `None` causes the default namespace of the connection to
            be used.

            Default: `None`

        :Exceptions:

            See the list of exceptions described in `WBEMConnection`.
        """

        params = self._map_classname_param(params)

        if namespace is None:
            namespace = self.default_namespace

        self.imethodcall(
            'DeleteClass',
            namespace,
            ClassName=CIMClassName(ClassName),
            **params)

    def ModifyClass(self, ModifiedClass, namespace=None, **params):
        # pylint: disable=invalid-name
        """
        Modify a class.

        This method performs the ModifyClass CIM-XML operation.
        If the operation succeeds, this method returns.
        Otherwise, this method raises an exception.

        :Parameters:

          ModifiedClass : `CIMClass`
            A representation of the modified class. This object needs to
            contain any modified properties, methods and qualifiers and the
            class path of the class to be modified.
            Typically, this object has been retrieved by other operations, such
            as `GetClass`.

        :Exceptions:

            See the list of exceptions described in `WBEMConnection`.
        """

        if namespace is None:
            namespace = self.default_namespace

        self.imethodcall(
            'ModifyClass',
            namespace,
            ModifiedClass=ModifiedClass,
            **params)

    def CreateClass(self, NewClass, namespace=None, **params):
        # pylint: disable=invalid-name
        """
        Create a class.

        This method performs the CreateClass CIM-XML operation.
        If the operation succeeds, this method returns.
        Otherwise, this method raises an exception.

        :Parameters:

          NewClass : `CIMClass`
            A representation of the class to be created. This object needs to
            contain any properties, methods, qualifiers, superclass name, and
            the class name of the class to be created.
            The class path in this object (`path` instance variable) will be
            ignored.

          namespace : string
            Optional: Name of the namespace in which the class is to be
            created.
            The value `None` causes the default namespace of the connection to
            be used.

            Default: `None`

        :Exceptions:

            See the list of exceptions described in `WBEMConnection`.
        """

        if namespace is None:
            namespace = self.default_namespace

        self.imethodcall(
            'CreateClass',
            namespace,
            NewClass=NewClass,
            **params)

    #
    # Association provider API
    #

    def _add_objectname_param(self, params, object_): # pylint: disable=no-self-use
        """Add an object name (either a class name or an instance
        name) to a dictionary of parameter names."""

        if isinstance(object_, (CIMClassName, CIMInstanceName)):
            params['ObjectName'] = object_.copy()
            params['ObjectName'].namespace = None
        elif isinstance(object_, six.string_types):
            params['ObjectName'] = CIMClassName(object_)
        else:
            raise ValueError('Expecting a classname, CIMClassName or '
                             'CIMInstanceName object')

        return params

    def _map_association_params(self, params): # pylint: disable=no-self-use
        """Convert various convenience parameters and types into their
        correct form for passing to the imethodcall() function."""

        # ResultClass and Role parameters that are strings should be
        # mapped to CIMClassName objects.

        if 'ResultClass' in params and \
           isinstance(params['ResultClass'], six.string_types):
            params['ResultClass'] = CIMClassName(params['ResultClass'])

        if 'AssocClass' in params and \
           isinstance(params['AssocClass'], six.string_types):
            params['AssocClass'] = CIMClassName(params['AssocClass'])

        return params

    def Associators(self, ObjectName, **params):
        # pylint: disable=invalid-name
        """
        Retrieve the instances (or classes) associated to a source instance
        (or source class).

        This method performs the Associators CIM-XML operation.
        If the operation succeeds, this method returns.
        Otherwise, this method raises an exception.

        :Parameters:

          ObjectName
            For instance level usage: The instance path of the source instance,
            as a `CIMInstanceName` object. If that object does not
            specify a namespace, the default namespace of the connection is
            used.

            For class level usage: The class path of the source class, as a
            string or as a `CIMClassName` object.
            If specified as a string, the string is interpreted as a class name
            in the default namespace of the connection.
            If specified as a `CIMClassName` object that does not
            specify a namespace, the default namespace of the connection is
            used.

          AssocClass : string or `CIMClassName`
            Optional: Class name of an association class, to filter the result
            to include only traversals of that association class (or
            subclasses).

            Default: `None` (no filtering).

          ResultClass : string or `CIMClassName`
            Optional: Class name of an associated class, to filter the result
            to include only traversals to that associated class (or
            subclasses).

            Default: `None` (no filtering).

          Role : string
            Optional: Role name (= property name) of the source end, to filter
            the result to include only traversals from that source role.

            Default: `None` (no filtering).

          ResultRole
            Optional: Role name (= property name) of the far end, to filter
            the result to include only traversals to that far role.

            Default: `None` (no filtering).

          IncludeQualifiers : `bool`
            Optional: Indicates that qualifiers are to be included in the
            returned instances (or classes).

            Default: `False`.

            This parameter has been deprecated in CIM-XML. Clients cannot rely
            on it being implemented by WBEM servers.

          IncludeClassOrigin : `bool`
            Optional: Indicates that class origin information is to be included
            on each property or method in the returned instances (or classes).

            Default: `False`.

          PropertyList : iterable of string
            Optional: An iterable specifying the names of the properties to be
            included in the returned instances (or classes). An empty iterable
            indicates to include no properties. A value of `None` for this
            parameter indicates to include all properties.

            Default: `None`.

        :Returns:

            For instance level usage, a list of `CIMInstance` objects
            that are representations of the associated instances.

            For class level usage, a list of `CIMClass` objects
            that are representations the associated classes.

        :Exceptions:

            See the list of exceptions described in `WBEMConnection`.
        """

        params = self._map_association_params(params)
        params = self._add_objectname_param(params, ObjectName)

        namespace = self.default_namespace

        if isinstance(ObjectName, CIMInstanceName) and \
           ObjectName.namespace is not None:
            namespace = ObjectName.namespace

        result = self.imethodcall(
            'Associators',
            namespace,
            **params)

        if result is None:
            return []

        return [x[2] for x in result[2]]

    def AssociatorNames(self, ObjectName, **params):
        # pylint: disable=invalid-name
        """
        Retrieve the instance paths of the instances (or class paths of the
        classes) associated to a source instance (or source class).

        This method performs the AssociatorNames CIM-XML operation.
        If the operation succeeds, this method returns.
        Otherwise, this method raises an exception.

        :Parameters:

          ObjectName
            For instance level usage: The instance path of the source instance,
            as a `CIMInstanceName` object. If that object does not
            specify a namespace, the default namespace of the connection is
            used.

            For class level usage: The class path of the source class, as a
            string or as a `CIMClassName` object.
            If specified as a string, the string is interpreted as a class name
            in the default namespace of the connection.
            If specified as a `CIMClassName` object that does not
            specify a namespace, the default namespace of the connection is
            used.

          AssocClass : string or `CIMClassName`
            Optional: Class name of an association class, to filter the result
            to include only traversals of that association class (or
            subclasses).

            Default: `None` (no filtering).

          ResultClass : string or `CIMClassName`
            Optional: Class name of an associated class, to filter the result
            to include only traversals to that associated class (or
            subclasses).

            Default: `None` (no filtering).

          Role : string
            Optional: Role name (= property name) of the source end, to filter
            the result to include only traversals from that source role.

            Default: `None` (no filtering).

          ResultRole
            Optional: Role name (= property name) of the far end, to filter
            the result to include only traversals to that far role.

            Default: `None` (no filtering).

        :Returns:

            For instance level usage, a list of `CIMInstanceName`
            objects that are the instance paths of the associated instances.

            For class level usage, a list of `CIMClassName` objects
            that are the class paths of the associated classes.

        :Exceptions:

            See the list of exceptions described in `WBEMConnection`.
        """

        params = self._map_association_params(params)
        params = self._add_objectname_param(params, ObjectName)

        namespace = self.default_namespace

        if isinstance(ObjectName, CIMInstanceName) and \
           ObjectName.namespace is not None:
            namespace = ObjectName.namespace

        result = self.imethodcall(
            'AssociatorNames',
            namespace,
            **params)

        if result is None:
            return []

        return [x[2] for x in result[2]]

    def References(self, ObjectName, **params):
        # pylint: disable=invalid-name
        """
        Retrieve the association instances (or association classes) that
        reference a source instance (or source class).

        This method performs the References CIM-XML operation.
        If the operation succeeds, this method returns.
        Otherwise, this method raises an exception.

        :Parameters:

          ObjectName
            For instance level usage: The instance path of the source instance,
            as a `CIMInstanceName` object. If that object does not
            specify a namespace, the default namespace of the connection is
            used.

            For class level usage: The class path of the source class, as a
            string or as a `CIMClassName` object.
            If specified as a string, the string is interpreted as a class name
            in the default namespace of the connection.
            If specified as a `CIMClassName` object that does not
            specify a namespace, the default namespace of the connection is
            used.

          ResultClass : string or `CIMClassName`
            Optional: Class name of an association class, to filter the result
            to include only traversals of that association class (or
            subclasses).

            Default: `None` (no filtering).

          Role : string
            Optional: Role name (= property name) of the source end, to filter
            the result to include only traversals from that source role.

            Default: `None` (no filtering).

          IncludeQualifiers : `bool`
            Optional: Indicates that qualifiers are to be included in the
            returned instances (or classes).

            Default: `False`.

            This parameter has been deprecated in CIM-XML. Clients cannot rely
            on it being implemented by WBEM servers.

          IncludeClassOrigin : `bool`
            Optional: Indicates that class origin information is to be included
            on each property or method in the returned instances (or classes).

            Default: `False`.

          PropertyList : iterable of string
            Optional: An iterable specifying the names of the properties to be
            included in the returned instances (or classes). An empty iterable
            indicates to include no properties. A value of `None` for this
            parameter indicates to include all properties.

            Default: `None`.

        :Returns:

            For instance level usage, a list of `CIMInstance` objects
            that are representations of the referencing association instances.

            For class level usage, a list of `CIMClass` objects
            that are representations the referencing association classes.

        :Exceptions:

            See the list of exceptions described in `WBEMConnection`.
        """

        params = self._map_association_params(params)
        params = self._add_objectname_param(params, ObjectName)

        namespace = self.default_namespace

        if isinstance(ObjectName, CIMInstanceName) and \
           ObjectName.namespace is not None:
            namespace = ObjectName.namespace

        result = self.imethodcall(
            'References',
            namespace,
            **params)

        if result is None:
            return []

        return [x[2] for x in result[2]]

    def ReferenceNames(self, ObjectName, **params):
        # pylint: disable=invalid-name
        """
        Retrieve the instance paths of the association instances (or class
        paths of the association classes) that reference a source instance
        (or source class).

        This method performs the ReferenceNames CIM-XML operation.
        If the operation succeeds, this method returns.
        Otherwise, this method raises an exception.

        :Parameters:

          ObjectName
            For instance level usage: The instance path of the source instance,
            as a `CIMInstanceName` object. If that object does not
            specify a namespace, the default namespace of the connection is
            used.

            For class level usage: The class path of the source class, as a
            string or as a `CIMClassName` object.
            If specified as a string, the string is interpreted as a class name
            in the default namespace of the connection.
            If specified as a `CIMClassName` object that does not
            specify a namespace, the default namespace of the connection is
            used.

          ResultClass : string or `CIMClassName`
            Optional: Class name of an association class, to filter the result
            to include only traversals of that association class (or
            subclasses).

            Default: `None` (no filtering).

          Role : string
            Optional: Role name (= property name) of the source end, to filter
            the result to include only traversals from that source role.

            Default: `None` (no filtering).

        :Returns:

            For instance level usage, a list of `CIMInstanceName`
            objects that are the instance paths of the referencing association
            instances.

            For class level usage, a list of `CIMClassName` objects
            that are the class paths of the referencing association classes.

        :Exceptions:

            See the list of exceptions described in `WBEMConnection`.
        """

        params = self._map_association_params(params)
        params = self._add_objectname_param(params, ObjectName)

        namespace = self.default_namespace

        if isinstance(ObjectName, CIMInstanceName) and \
           ObjectName.namespace is not None:
            namespace = ObjectName.namespace

        result = self.imethodcall(
            'ReferenceNames',
            namespace,
            **params)

        if result is None:
            return []

        return [x[2] for x in result[2]]

    #
    # Method provider API
    #

    def InvokeMethod(self, MethodName, ObjectName, Params=None, **params):
        # pylint: disable=invalid-name
        """
        Invoke a method on a target instance or on a target class.

        The methods that can be invoked are static and non-static methods
        defined in a class (also known as *extrinsic* methods).
        Static methods can be invoked on instances and on classes.
        Non-static methods can be invoked only on instances.

        This method performs the InvokeMethod CIM-XML operation.
        If the operation succeeds, this method returns.
        Otherwise, this method raises an exception.

        Input parameters for the CIM method can be specified in a
        order-preserving way using the ``Params`` parameter, and in a
        order-agnostic way using the ``**params`` keyword parameters.

        :Parameters:

          MethodName : string
            Name of the method to be invoked (without parenthesis or any
            parameter signature).

          ObjectName
            For instance level usage: The instance path of the target instance,
            as a `CIMInstanceName` object. If that object does not
            specify a namespace, the default namespace of the connection is
            used.

            For class level usage: The class path of the target class, as a
            string or as a `CIMClassName` object.
            If specified as a string, the string is interpreted as a class name
            in the default namespace of the connection.
            If specified as a `CIMClassName` object that does not
            specify a namespace, the default namespace of the connection is
            used.

          Params
            A list of input parameters for the CIM method.

            Each list item represents a single input parameter for the CIM
            method and must be a ``tuple(name,value)``, where ``name`` is the
            parameter name in any lexical case, and ``value`` is the parameter
            value as a CIM typed value as described in `cim_types`.

          **params
            Keyword parameters for the input parameters for the CIM method.

            Each keyword parameter represents a single input parameter for the
            CIM method, where the key is the parameter name in any lexical
            case, and the value is the parameter value as a CIM typed value as
            described in `cim_types`.

            The overall list of input parameters represented in the CIM-XML
            request message that is sent to the WBEM server is formed from
            the list of parameters specified in ``Params`` preserving its
            order, followed by the set of parameters specified in ``**params``
            in any order. There is no checking for duplicate parameter names
            in the PyWBEM client.


        :Returns:

          A tuple of ``(returnvalue, outparams)``, where:

            - ``returnvalue`` : Return value of the CIM method, as a CIM typed
              value as described in `cim_types`.
            - ``outparams`` : Output parameters of the CIM method, as a
              `NocaseDict` dictionary containing all CIM method output
              parameters, where the dictionary items have:

              * a key that is the CIM parameter name, as a string.
              * a value that is the CIM parameter value, as a CIM typed value
                as described in `cim_types`.

        :Exceptions:

            See the list of exceptions described in `WBEMConnection`.
        """

        # Convert string to CIMClassName

        obj = ObjectName

        if isinstance(obj, six.string_types):
            obj = CIMClassName(obj, namespace=self.default_namespace)

        if isinstance(obj, CIMInstanceName) and obj.namespace is None:
            obj = ObjectName.copy()
            obj.namespace = self.default_namespace

        # Make the method call

        result = self.methodcall(MethodName, obj, Params, **params)

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

        return returnvalue, output_params

    #
    # Qualifiers API
    #

    def EnumerateQualifiers(self, namespace=None, **params):
        # pylint: disable=invalid-name
        """
        Enumerate qualifier declarations.

        This method performs the EnumerateQualifiers CIM-XML operation.
        If the operation succeeds, this method returns.
        Otherwise, this method raises an exception.

        :Parameters:

          namespace : string
            Optional: Name of the namespace in which the qualifier
            declarations are to be enumerated.
            The value `None` causes the default namespace of the connection to
            be used.

        :Returns:

            A list of `CIMQualifierDeclaration` objects that are
            representations of the enumerated qualifier declarations.

        :Exceptions:

            See the list of exceptions described in `WBEMConnection`.
        """

        if namespace is None:
            namespace = self.default_namespace

        result = self.imethodcall(
            'EnumerateQualifiers',
            namespace,
            **params)


        if result is not None:
            qualifiers = result[2]
        else:
            qualifiers = []

        return qualifiers

    def GetQualifier(self, QualifierName, namespace=None, **params):
        # pylint: disable=invalid-name
        """
        Retrieve a qualifier declaration.

        This method performs the GetQualifier CIM-XML operation.
        If the operation succeeds, this method returns.
        Otherwise, this method raises an exception.

        :Parameters:

          Qualifier : string
            Name of the qualifier declaration to be retrieved.

          namespace : string
            Optional: Name of the namespace of the qualifier declaration.
            The value `None` causes the default namespace of the connection to
            be used.

        :Returns:

            A `CIMQualifierDeclaration` object that is a representation
            of the retrieved qualifier declaration.

        :Exceptions:

            See the list of exceptions described in `WBEMConnection`.
        """

        if namespace is None:
            namespace = self.default_namespace

        result = self.imethodcall(
            'GetQualifier',
            namespace,
            QualifierName=QualifierName,
            **params)

        if result is not None:
            names = result[2][0]

        return names

    def SetQualifier(self, QualifierDeclaration, namespace=None, **params):
        # pylint: disable=invalid-name
        """
        Create or modify a qualifier declaration.

        This method performs the SetQualifier CIM-XML operation.
        If the operation succeeds, this method returns.
        Otherwise, this method raises an exception.

        :Parameters:

          QualifierDeclaration : `CIMQualifierDeclaration`
            Representation of the qualifier declaration to be created or
            modified.

          namespace : string
            Optional: Name of the namespace in which the qualifier declaration
            is to be created or modified.
            The value `None` causes the default namespace of the connection to
            be used.

        :Exceptions:

            See the list of exceptions described in `WBEMConnection`.
        """

        if namespace is None:
            namespace = self.default_namespace

        #pylint: disable=unused-variable
        result = self.imethodcall(
            'SetQualifier',
            namespace,
            QualifierDeclaration=QualifierDeclaration,
            **params)

    def DeleteQualifier(self, QualifierName, namespace=None, **params):
        # pylint: disable=invalid-name
        """
        Delete a qualifier declaration.

        This method performs the DeleteQualifier CIM-XML operation.
        If the operation succeeds, this method returns.
        Otherwise, this method raises an exception.

        :Parameters:

          Qualifier : string
            Name of the qualifier declaration to be deleted.

          namespace : string
            Optional: Name of the namespace in which the qualifier declaration
            is to be deleted.
            The value `None` causes the default namespace of the connection to
            be used.

        :Exceptions:

            See the list of exceptions described in `WBEMConnection`.
        """

        if namespace is None:
            namespace = self.default_namespace

        unused_result = self.imethodcall(
            'DeleteQualifier',
            namespace,
            QualifierName=QualifierName,
            **params)

def is_subclass(ch, ns, super_class, sub):
    """Determine if one class is a subclass of another class.

    Keyword Arguments:
    ch -- A CIMOMHandle.  Either a pycimmb.CIMOMHandle or a
        pywbem.WBEMConnection.
    ns -- Namespace.
    super-class -- A string containing the super class name.
    sub -- The subclass.  This can either be a string or a pywbem.CIMClass.

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
