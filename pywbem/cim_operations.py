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

======================================================  ==============================================================
WBEMConnection method                                   Purpose
======================================================  ==============================================================
:meth:`~pywbem.WBEMConnection.EnumerateInstanceNames`   Enumerate the instance paths of instances of a class
                                                        (including instances of its subclasses).
:meth:`~pywbem.WBEMConnection.EnumerateInstances`       Enumerate the instances of a class (including instances of its
                                                        subclasses)
:meth:`~pywbem.WBEMConnection.GetInstance`              Retrieve an instance
:meth:`~pywbem.WBEMConnection.ModifyInstance`           Modify the property values of an instance
:meth:`~pywbem.WBEMConnection.CreateInstance`           Create an instance
:meth:`~pywbem.WBEMConnection.DeleteInstance`           Delete an instance
------------------------------------------------------  --------------------------------------------------------------
:meth:`~pywbem.WBEMConnection.AssociatorNames`          Retrieve the instance paths of the instances (or classes)
                                                        associated to a source instance (or source class)
:meth:`~pywbem.WBEMConnection.Associators`              Retrieve the instances (or classes) associated to a source
                                                        instance (or source class)
:meth:`~pywbem.WBEMConnection.ReferenceNames`           Retrieve the instance paths of the association instances (or
                                                        association classes) that reference a source instance (or
                                                        source class)
:meth:`~pywbem.WBEMConnection.References`               Retrieve the association instances (or association classes)
                                                        that reference a source instance (or source class)
------------------------------------------------------  --------------------------------------------------------------
:meth:`~pywbem.WBEMConnection.InvokeMethod`             Invoke a method on a target instance or on a target class
------------------------------------------------------  --------------------------------------------------------------
:meth:`~pywbem.WBEMConnection.ExecQuery`                Execute a query in a namespace
------------------------------------------------------  --------------------------------------------------------------
:meth:`~pywbem.WBEMConnection.EnumerateClassNames`      Enumerate the names of subclasses of a class, or of the
                                                        top-level classes in a namespace
:meth:`~pywbem.WBEMConnection.EnumerateClasses`         Enumerate the subclasses of a class, or the top-level classes
                                                        in a namespace
:meth:`~pywbem.WBEMConnection.GetClass`                 Retrieve a class
:meth:`~pywbem.WBEMConnection.ModifyClass`              Modify a class
:meth:`~pywbem.WBEMConnection.CreateClass`              Create a class
:meth:`~pywbem.WBEMConnection.DeleteClass`              Delete a class
------------------------------------------------------  --------------------------------------------------------------
:meth:`~pywbem.WBEMConnection.EnumerateQualifiers`      Enumerate qualifier declarations
:meth:`~pywbem.WBEMConnection.GetQualifier`             Retrieve a qualifier declaration
:meth:`~pywbem.WBEMConnection.SetQualifier`             Create or modify a qualifier declaration
:meth:`~pywbem.WBEMConnection.DeleteQualifier`          Delete a qualifier declaration
======================================================  ==============================================================
"""
# pylint: enable=line-too-long
# Note: When used before module docstrings, Pylint scopes the disable statement
#       to the whole rest of the file, so we need an enable statement.

# This module is meant to be safe for 'import *'.

from __future__ import absolute_import

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

    Parameters:

      utf8_xml (:term:`byte string`):
        The UTF-8 encoded XML string to be examined.

      meaning (:term:`unicode string` or :term:`byte string`):
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

    The exception value is a `tuple(error_code, description, exception_obj)`,
    with:

      * error_code (number):
        Numeric CIM status code.
        See :ref:`CIM status codes` for constants defining the numeric CIM
        status code values.

      * description (:term:`unicode string` or :term:`byte string`):
        CIM status description text returned by the server, representing a
        human readable message describing the error.

      * exception_obj (exception):
        The underlying exception object that caused this exception to be
        raised, or `None`. Will always be `None`, currently.
    """
    pass

class WBEMConnection(object):
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
    the WBEM server.

    CIM elements such as instances or classes are represented as Python objects
    (see :ref:`CIM objects`). The caller does not need to know about the CIM-XML
    encoding of CIM elements and protocol payload that is used underneath (It
    should be possible to use a different WBEM protocol below this layer without
    disturbing any callers).

    The connection remembers the XML of the last request and last reply if
    debugging is turned on via the :attr:`debug` instance variable of the
    connection object.
    This may be useful in debugging: If a problem occurs, you can examine the
    :attr:`last_request` and :attr:`last_reply` instance variables of the
    connection object.
    These are the prettified XML of request and response, respectively.
    The real request and response that are sent and received are available in
    the :attr:`last_raw_request` and :attr:`last_raw_reply` instance variables
    of the connection object.

    The methods of this class may raise the following exceptions:

    * Exceptions indicating processing errors:

      - :exc:`~pywbem.ConnectionError` - A connection with the WBEM server
        could not be established or broke down.

      - :exc:`~pywbem.AuthError` - Authentication failed with the WBEM server.

      - :exc:`~pywbem.ParseError` - The response from the WBEM server cannot be
        parsed (for example, invalid characters or UTF-8 sequences, ill-formed
        XML, or invalid CIM-XML).

      - :exc:`~pywbem.CIMError` - The WBEM server returned an error response
        with a CIM status code.

      - :exc:`~pywbem.TimeoutError` - The WBEM server did not respond in time
        and the client timed out.

    * Exceptions indicating programming errors:

      - :py:exc:`~exceptions.TypeError`
      - :py:exc:`~exceptions.KeyError`
      - :py:exc:`~exceptions.ValueError`
      - :py:exc:`~exceptions.AttributeError`
      - ... possibly others ...

      Exceptions indicating programming errors should not happen and should be
      reported as bugs, unless caused by the code using this class.

    Attributes:

      ... : All parameters of the :class:`~pywbem.WBEMConnection` constructor
        are set as instance variables.

      debug (bool): A boolean indicating whether logging of the last request
        and last reply is enabled.

        The initial value of this instance variable is `False`.
        Debug logging can be enabled for future operations by setting this
        instance variable to `True`.

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
        response, it is `None`.
    """

    def __init__(self, url, creds=None, default_namespace=DEFAULT_NAMESPACE,
                 x509=None, verify_callback=None, ca_certs=None,
                 no_verification=False, timeout=None):
        """
        Parameters:

          url (:term:`unicode string` or :term:`byte string`):
            URL of the WBEM server (e.g. ``"https://10.11.12.13:6988"``).

            TODO: Describe supported formats.

          creds (tuple of userid, password):
            Credentials for authenticating with the WBEM server.
            Currently, that is always a `tuple(userid, password)`, with:

            * userid (:term:`unicode string` or :term:`byte string`):
              Userid for authenticating with the WBEM server.

            * password (:term:`unicode string` or :term:`byte string`):
              Password for that userid.

          default_namespace (:term:`unicode string` or :term:`byte string`):
            Name of the CIM namespace to be used by default (if no namespace
            is specified for an operation).

            Default: :data:`~pywbem.cim_constants.DEFAULT_NAMESPACE`.

          x509 (dict):
            :term:`X.509` certificates for HTTPS to be used instead of the
            credentials provided in the `creds` parameter.
            This parameter is used only when the `url` parameter specifies
            a scheme of ``"https"``.

            If `None`, certificates are not used (and credentials are used
            instead).

            Otherwise, certificates are used instead of the credentials,
            and this parameter must be a dictionary containing the following
            two items:

            * ``"cert_file"``: The file path of a file containing an
              :term:`X.509` certificate, as a :term:`unicode string` or
              :term:`byte string` object.

            * ``"key_file"``: The file path of a file containing the private
              key belonging to the public key that is part of the :term:`X.509`
              certificate file, as a :term:`unicode string` or
              :term:`byte string` object.

          verify_callback (callable):
            Registers a callback function that will be called to verify the
            certificate returned by the WBEM server during the SSL handshake,
            in addition to the verification alreay performed by `M2Crypto`.

            If `None`, no such callback function will be registered.

            The specified function will be called for the returned
            certificate, and for each of the certificates in its chain of
            trust.

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

          ca_certs (:term:`unicode string` or :term:`byte string`):
            Location of CA certificates (trusted certificates) for
            verification purposes.

            The parameter value is either the directory path of a directory
            prepared using the ``c_rehash`` tool included with OpenSSL, or the
            file path of a file in PEM format.

            If `None`, the default system path will be used.

          no_verification (bool):
            Indicates that verification of the certificate returned by the WBEM
            server is disabled (both by `M2Crypto` and by the callback function
            specified in `verify_callback`).

            Disabling the verification is insecure and should be avoided.

            If `True`, verification is disabled; otherwise, it is enabled.

          timeout (number):
            Timeout in seconds, for requests sent to the server. If the server
            did not respond within the timeout duration, the socket for the
            connection will be closed, causing a :exc:`~pywbem.TimeoutError` to
            be raised.

            A value of `None` means there is no timeout.

            A value of ``0`` means the timeout is very short, and does not
            really make any sense.

            Note that not all situations can be handled within this timeout, so
            for some issues, operations may take longer before raising an
            exception.
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
        with all instance variables (except for the password in the
        credentials) that is suitable for debugging.
        """

        if isinstance(self.creds, tuple):
            # tuple (userid, password) was specified
            creds_repr = "(%r, ...)" % self.creds[0]
        else:
            creds_repr = repr(self.creds)
        return "%s(url=%r, creds=%s, " \
               "default_namespace=%r, x509=%r, verify_callback=%r, " \
               "ca_certs=%r, no_verification=%r, timeout=%r)" % \
               (self.__class__.__name__, self.url, creds_repr,
                self.default_namespace, self.x509, self.verify_callback,
                self.ca_certs, self.no_verification, self.timeout)

    def imethodcall(self, methodname, namespace, **params):
        """
        This is a low-level method that is used by the operation-specific
        methods of this class
        (e.g. :meth:`~pywbem.WBEMConnection.EnumerateInstanceNames`).
        Users should call these operation-specific methods instead of this
        method.

        This method is not part of the external WBEM client library API; it is
        being included in the documentation only for tooling reasons.
        For compatibility reasons, it has not been renamed to become a private
        member.
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
                timeout=self.timeout)
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
        This is a low-level method that is used by the
        :meth:`~pywbem.WBEMConnection.InvokeMethod` method of this class.
        Users should call :meth:`~pywbem.WBEMConnection.InvokeMethod` instead
        of this method.

        This method is not part of the external WBEM client library API; it is
        being included in the documentation only for tooling reasons.
        For compatibility reasons, it has not been renamed to become a private
        member.
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
                timeout=self.timeout)
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

    def _iparam_namespace_from(self, obj):
        """Determine the namespace from an object that can be a namespace
        string, a CIMClassName or CIMInstanceName object, or `None`. The
        default namespace of the connection object is used, if needed.

        Return the so determined namespace for use as an argument to
        imethodcall()."""

        if isinstance(obj, (CIMClassName, CIMInstanceName)):
            namespace = obj.namespace
        elif isinstance(obj, six.string_types):
            namespace = obj
        elif obj is None:
            namespace = obj
        else:
            raise TypeError('Expecting None (for default), a namespace ' \
                            'string, a CIMClassName or CIMInstanceName ' \
                            'object, got: %s' % type(obj))
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
            raise TypeError('Expecting None, a classname string, a ' \
                            'CIMClassName or CIMInstanceName object, ' \
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
            raise TypeError('Expecting None, a classname string or a ' \
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
            raise TypeError('Expecting None or a CIMInstanceName object, ' \
                            'got: %s' % type(instancename))
        return instancename

    #
    # Instance operations
    #

    def EnumerateInstanceNames(self, ClassName, namespace=None, **extra):
        # pylint: disable=invalid-name,line-too-long
        """
        Enumerate the instance paths of instances of a class (including
        instances of its subclasses).

        This method performs the EnumerateInstanceNames operation.
        If the operation succeeds, this method returns.
        Otherwise, this method raises an exception.

        Parameters:

          ClassName (:term:`unicode string` or :term:`byte string` or :class:`~pywbem.CIMClassName`):
            Name of the class to be enumerated, in any lexical case.

          namespace (:term:`unicode string` or :term:`byte string`):
            Name of the CIM namespace to be used, in any lexical case.

            If `None`, the default namespace of the connection object will be
            used.

        Keyword Arguments:

          extra :
            Additional keyword arguments are passed as additional operation
            parameters to the WBEM server.
            Note that :term:`DSP0200` does not define any additional parameters
            for this operation.

        Returns:

            A list of :class:`~pywbem.CIMInstanceName` objects that are the
            enumerated instance paths.

        Raises:

            Exceptions described in :class:`~pywbem.WBEMConnection`.
        """

        namespace = self._iparam_namespace_from(namespace)
        classname = self._iparam_classname(ClassName)

        result = self.imethodcall(
            'EnumerateInstanceNames',
            namespace,
            ClassName=classname,
            **extra)

        instancenames = []
        if result is not None:
            instancenames = result[2]

        for instancename in instancenames:
            instancename.namespace = namespace

        return instancenames

    def EnumerateInstances(self, ClassName, namespace=None, LocalOnly=None,
                           DeepInheritance=None, IncludeQualifiers=None,
                           IncludeClassOrigin=None, PropertyList=None,
                           **extra):
        # pylint: disable=invalid-name,line-too-long
        """
        Enumerate the instances of a class (including instances of its
        subclasses).

        This method performs the EnumerateInstances operation.
        If the operation succeeds, this method returns.
        Otherwise, this method raises an exception.

        Parameters:

          ClassName (:term:`unicode string` or :term:`byte string` or :class:`~pywbem.CIMClassName`):
            Name of the class to be enumerated, in any lexical case.

          namespace (:term:`unicode string` or :term:`byte string`):
            Name of the CIM namespace to be used, in any lexical case.

            If `None`, the default namespace of the connection object will be
            used.

          LocalOnly (bool):
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

          DeepInheritance (bool):
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

          IncludeQualifiers (bool):
            Indicates that qualifiers are to be included in the returned
            instance, as follows:

            * If `False`, qualifiers not included.
            * If `True`, qualifiers are included if the WBEM server implements
              support for this parameter.
            * If `None`, this parameter is not passed to the WBEM server, and
              causes the server-implemented default to be used. :term:`DSP0200`
              defines that the server-implemented default is `False`.

            This parameter has been deprecated in :term:`DSP0200`. Clients
            cannot rely on it being implemented by WBEM servers.

          IncludeClassOrigin (bool):
            Indicates that class origin information is to be included on each
            property in the returned instances, as follows:

            * If `False`, class origin information is not included.
            * If `True`, class origin information is included.
            * If `None`, this parameter is not passed to the WBEM server, and
              causes the server-implemented default to be used. :term:`DSP0200`
              defines that the server-implemented default is `False`.

          PropertyList (iterable of :term:`unicode string` or :term:`byte string`):
            An iterable specifying the names of the properties to be
            included in the returned instances, in any lexical case.

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

        Raises:

            Exceptions described in :class:`~pywbem.WBEMConnection`.
        """

        namespace = self._iparam_namespace_from(namespace)
        classname = self._iparam_classname(ClassName)

        result = self.imethodcall(
            'EnumerateInstances',
            namespace,
            ClassName=classname,
            LocalOnly=LocalOnly,
            DeepInheritance=DeepInheritance,
            IncludeQualifiers=IncludeQualifiers,
            IncludeClassOrigin=IncludeClassOrigin,
            PropertyList=PropertyList,
            **extra)

        instances = []
        if result is not None:
            instances = result[2]

        for instance in instances:
            instance.path.namespace = namespace

        return instances

    def GetInstance(self, InstanceName, LocalOnly=None, IncludeQualifiers=None,
                    IncludeClassOrigin=None, PropertyList=None, **extra):
        # pylint: disable=invalid-name,line-too-long
        """
        Retrieve an instance.

        This method performs the GetInstance operation.
        If the operation succeeds, this method returns.
        Otherwise, this method raises an exception.

        Parameters:

          InstanceName (CIMInstanceName): Instance path of the instance to be
            retrieved.

          LocalOnly (bool):
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

          IncludeQualifiers (bool):
            Indicates that qualifiers are to be included in the returned
            instance, as follows:

            * If `False`, qualifiers not included.
            * If `True`, qualifiers are included if the WBEM server implements
              support for this parameter.
            * If `None`, this parameter is not passed to the WBEM server, and
              causes the server-implemented default to be used. :term:`DSP0200`
              defines that the server-implemented default is `False`.

            This parameter has been deprecated in :term:`DSP0200`. Clients
            cannot rely on it being implemented by WBEM servers.

          IncludeClassOrigin (bool):
            Indicates that class origin information is to be included on each
            property in the returned instances, as follows:

            * If `False`, class origin information is not included.
            * If `True`, class origin information is included.
            * If `None`, this parameter is not passed to the WBEM server, and
              causes the server-implemented default to be used. :term:`DSP0200`
              defines that the server-implemented default is `False`.

          PropertyList (iterable of :term:`unicode string` or :term:`byte string`):
            An iterable specifying the names of the properties to be
            included in the returned instance, in any lexical case.
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

        Raises:

            Exceptions described in :class:`~pywbem.WBEMConnection`.
        """

        # Strip off host and namespace to make this a "local" object

        namespace = self._iparam_namespace_from(InstanceName)
        instancename = self._iparam_instancename(InstanceName)

        result = self.imethodcall(
            'GetInstance',
            namespace,
            InstanceName=instancename,
            LocalOnly=LocalOnly,
            IncludeQualifiers=IncludeQualifiers,
            IncludeClassOrigin=IncludeClassOrigin,
            PropertyList=PropertyList,
            **extra)

        instance = result[2][0]
        instance.path = instancename
        instance.path.namespace = namespace

        return instance

    def ModifyInstance(self, ModifiedInstance, IncludeQualifiers=None,
                       PropertyList=None, **extra):
        # pylint: disable=invalid-name,line-too-long
        """
        Modify the property values of an instance.

        This method performs the ModifyInstance operation.
        If the operation succeeds, this method returns.
        Otherwise, this method raises an exception.

        Parameters:

          ModifiedInstance (CIMInstance):
            A representation of the modified instance, also indicating its
            instance path.

            The namespace component of the `path` instance variable of this
            object specifies the namespace for the instance to be modified.

            The properties defined in this object specify the new property
            values for the instance to be modified. Missing properties
            (relative to the class declaration) and properties provided with
            a value of `None` will be set to NULL.

            Typically, this object has been retrieved by other operations,
            such as :meth:`~pywbem.WBEMConnection.GetInstance`.

          IncludeQualifiers (bool):
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

          PropertyList (iterable of :term:`unicode string` or :term:`byte string`):
            An iterable specifying the names of the properties to be
            modified, in any lexical case.

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
        """

        # Must pass a named CIMInstance here (i.e path attribute set)

        if ModifiedInstance.path is None:
            raise ValueError(
                'ModifiedInstance parameter must have path attribute set')

        namespace = self._iparam_namespace_from(ModifiedInstance.path)

        instance = ModifiedInstance.copy()
        instance.path.namespace = None

        self.imethodcall(
            'ModifyInstance',
            namespace,
            ModifiedInstance=instance,
            IncludeQualifiers=IncludeQualifiers,
            PropertyList=PropertyList,
            **extra)

    def CreateInstance(self, NewInstance, **extra):
        # pylint: disable=invalid-name
        """
        Create an instance.

        This method performs the CreateInstance operation.
        If the operation succeeds, this method returns.
        Otherwise, this method raises an exception.

        Parameters:

          NewInstance (CIMInstance):
            A representation of the instance to be created.

            The `classname` instance variable of this object specifies the
            creation class for the new instance. The namespace component of
            the `path` instance variable specifies the namespace for the new
            instance.

            The `properties` instance variable of this object specifies initial
            property values for the new instance.

            Instance-level qualifiers have been deprecated in CIM, so any
            qualifier values specified using the `qualifiers` instance variable
            of this object will be ignored.

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

        namespace = self._iparam_namespace_from(NewInstance.path)

        # Strip off path to avoid producing a VALUE.NAMEDINSTANCE
        # element instead of an INSTANCE element.

        instance = NewInstance.copy()
        instance.path = None

        result = self.imethodcall(
            'CreateInstance',
            namespace,
            NewInstance=instance,
            **extra)

        instancename = result[2][0]
        instancename.namespace = namespace

        return instancename

    def DeleteInstance(self, InstanceName, **extra):
        # pylint: disable=invalid-name
        """
        Delete an instance.

        This method performs the DeleteInstance operation.
        If the operation succeeds, this method returns.
        Otherwise, this method raises an exception.

        Parameters:

          InstanceName (CIMInstanceName): Instance path of the instance to be
            deleted.

        Keyword Arguments:

          extra :
            Additional keyword arguments are passed as additional operation
            parameters to the WBEM server.
            Note that :term:`DSP0200` does not define any additional parameters
            for this operation.

        Raises:

            Exceptions described in :class:`~pywbem.WBEMConnection`.
        """

        namespace = self._iparam_namespace_from(InstanceName)
        instancename = self._iparam_instancename(InstanceName)

        self.imethodcall(
            'DeleteInstance',
            namespace,
            InstanceName=instancename,
            **extra)

    #
    # Association operations
    #

    def AssociatorNames(self, ObjectName, AssocClass=None, ResultClass=None,
                        Role=None, ResultRole=None, **extra):
        # pylint: disable=invalid-name, line-too-long
        """
        Retrieve the instance paths of the instances (or class paths of the
        classes) associated to a source instance (or source class).

        This method performs the AssociatorNames operation.
        If the operation succeeds, this method returns.
        Otherwise, this method raises an exception.

        Parameters:

          ObjectName:
            For instance level usage: The instance path of the source instance,
            as a :class:`~pywbem.CIMInstanceName` object. If that object does
            not specify a namespace, the default namespace of the connection is
            used.

            For class level usage: The class path of the source class, as a
            :term:`unicode string`, :term:`byte string` or
            :class:`~pywbem.CIMClassName` object.
            If specified as a string, the string is interpreted as a class name
            in the default namespace of the connection, and can have any
            lexical case.
            If specified as a :class:`~pywbem.CIMClassName` object that does
            not specify a namespace, the default namespace of the connection is
            used.

          AssocClass (:term:`unicode string`, :term:`byte string` or :class:`~pywbem.CIMClassName`):
            Class name of an association class, in any lexical case,
            to filter the result to include only traversals of that association
            class (or subclasses).

            `None` means that no filtering is peformed.

          ResultClass (:term:`unicode string`, :term:`byte string` or :class:`~pywbem.CIMClassName`):
            Class name of an associated class, in any lexical case,
            to filter the result to include only traversals to that associated
            class (or subclasses).

            `None` means that no filtering is peformed.

          Role (:term:`unicode string` or :term:`byte string`):
            Role name (= property name) of the source end, in any
            lexical case, to filter the result to include only traversals from
            that source role.

            `None` means that no filtering is peformed.

          ResultRole (:term:`unicode string` or :term:`byte string`):
            Role name (= property name) of the far end, in any
            lexical case, to filter the result to include only traversals to
            that far role.

            `None` means that no filtering is peformed.

        Keyword Arguments:

          extra :
            Additional keyword arguments are passed as additional operation
            parameters to the WBEM server.
            Note that :term:`DSP0200` does not define any additional parameters
            for this operation.

        Returns:

            For instance level usage, a list of
            :class:`~pywbem.CIMInstanceName` objects that are the instance
            paths of the associated instances.

            For class level usage, a list of :class:`~pywbem.CIMClassName`
            objects that are the class paths of the associated classes.

        Raises:

            Exceptions described in :class:`~pywbem.WBEMConnection`.
        """

        namespace = self._iparam_namespace_from(ObjectName)
        objectname = self._iparam_objectname(ObjectName)

        result = self.imethodcall(
            'AssociatorNames',
            namespace,
            ObjectName=objectname,
            AssocClass=self._iparam_classname(AssocClass),
            ResultClass=self._iparam_classname(ResultClass),
            Role=Role,
            ResultRole=ResultRole,
            **extra)

        if result is None:
            return []

        return [x[2] for x in result[2]]

    def Associators(self, ObjectName, AssocClass=None, ResultClass=None,
                    Role=None, ResultRole=None, IncludeQualifiers=None,
                    IncludeClassOrigin=None, PropertyList=None, **extra):
        # pylint: disable=invalid-name, line-too-long
        """
        Retrieve the instances (or classes) associated to a source instance
        (or source class).

        This method performs the Associators operation.
        If the operation succeeds, this method returns.
        Otherwise, this method raises an exception.

        Parameters:

          ObjectName:
            For instance level usage: The instance path of the source instance,
            as a :class:`~pywbem.CIMInstanceName` object. If that object does
            not specify a namespace, the default namespace of the connection is
            used.

            For class level usage: The class path of the source class, as a
            :term:`unicode string`, :term:`byte string` or
            :class:`~pywbem.CIMClassName` object.
            If specified as a string, the string is interpreted as a class name
            in the default namespace of the connection, and can have any
            lexical case.
            If specified as a :class:`~pywbem.CIMClassName` object that does
            not specify a namespace, the default namespace of the connection is
            used.

          AssocClass (:term:`unicode string`, :term:`byte string` or :class:`~pywbem.CIMClassName`):
            Class name of an association class, in any lexical case,
            to filter the result to include only traversals of that association
            class (or subclasses).

            `None` means that no filtering is peformed.

          ResultClass (:term:`unicode string`, :term:`byte string` or :class:`~pywbem.CIMClassName`):
            Class name of an associated class, in any lexical case,
            to filter the result to include only traversals to that associated
            class (or subclasses).

            `None` means that no filtering is peformed.

          Role (:term:`unicode string` or :term:`byte string`):
            Role name (= property name) of the source end, in any
            lexical case, to filter the result to include only traversals from
            that source role.

            `None` means that no filtering is peformed.

          ResultRole (:term:`unicode string` or :term:`byte string`):
            Role name (= property name) of the far end, in any
            lexical case, to filter the result to include only traversals to
            that far role.

            `None` means that no filtering is peformed.

          IncludeQualifiers (bool):
            Indicates that qualifiers are to be included in the returned
            instances (or classes), as follows:

            * If `False`, qualifiers not included.
            * If `True`, qualifiers are included if the WBEM server implements
              support for this parameter.
            * If `None`, this parameter is not passed to the WBEM server, and
              causes the server-implemented default to be used. :term:`DSP0200`
              defines that the server-implemented default is `False`.

            This parameter has been deprecated in :term:`DSP0200`. Clients
            cannot rely on it being implemented by WBEM servers.

          IncludeClassOrigin (bool):
            Indicates that class origin information is to be included on each
            property or method in the returned instances (or classes), as
            follows:

            * If `False`, class origin information is not included.
            * If `True`, class origin information is included.
            * If `None`, this parameter is not passed to the WBEM server, and
              causes the server-implemented default to be used. :term:`DSP0200`
              defines that the server-implemented default is `False`.

          PropertyList (iterable of :term:`unicode string` or :term:`byte string`):
            An iterable specifying the names of the properties to be included
            in the returned instances (or classes), in any lexical case.
            An empty iterable indicates to include no properties.

            If `None`, all properties are included.

        Keyword Arguments:

          extra :
            Additional keyword arguments are passed as additional operation
            parameters to the WBEM server.
            Note that :term:`DSP0200` does not define any additional parameters
            for this operation.

        Returns:

            For instance level usage, a list of :class:`~pywbem.CIMInstance`
            objects that are representations of the associated instances.

            For class level usage, a list of :class:`~pywbem.CIMClass` objects
            that are representations the associated classes.

        Raises:

            Exceptions described in :class:`~pywbem.WBEMConnection`.
        """

        namespace = self._iparam_namespace_from(ObjectName)
        objectname = self._iparam_objectname(ObjectName)

        result = self.imethodcall(
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
            return []

        return [x[2] for x in result[2]]

    def ReferenceNames(self, ObjectName, ResultClass=None, Role=None, **extra):
        # pylint: disable=invalid-name, line-too-long
        """
        Retrieve the instance paths of the association instances (or class
        paths of the association classes) that reference a source instance
        (or source class).

        This method performs the ReferenceNames operation.
        If the operation succeeds, this method returns.
        Otherwise, this method raises an exception.

        Parameters:

          ObjectName:
            For instance level usage: The instance path of the source instance,
            as a :class:`~pywbem.CIMInstanceName` object. If that object does
            not specify a namespace, the default namespace of the connection is
            used.

            For class level usage: The class path of the source class, as a
            :term:`unicode string`, :term:`byte string` or :class:`~pywbem.CIMClassName`
            object.
            If specified as a string, the string is interpreted as a class name
            in the default namespace of the connection, and can have any
            lexical case.
            If specified as a :class:`~pywbem.CIMClassName` object that does
            not specify a namespace, the default namespace of the connection is
            used.

          ResultClass (:term:`unicode string`, :term:`byte string` or :class:`~pywbem.CIMClassName`):
            Class name of an association class, in any lexical case,
            to filter the result to include only traversals of that association
            class (or subclasses).

            `None` means that no filtering is peformed.

          Role (:term:`unicode string` or :term:`byte string`):
            Role name (= property name) of the source end, in any
            lexical case, to filter the result to include only traversals from
            that source role.

            `None` means that no filtering is peformed.

        Keyword Arguments:

          extra :
            Additional keyword arguments are passed as additional operation
            parameters to the WBEM server.
            Note that :term:`DSP0200` does not define any additional parameters
            for this operation.

        Returns:

            For instance level usage, a list of
            :class:`~pywbem.CIMInstanceName` objects that are the instance
            paths of the referencing association instances.

            For class level usage, a list of :class:`~pywbem.CIMClassName`
            objects that are the class paths of the referencing association
            classes.

        Raises:

            Exceptions described in :class:`~pywbem.WBEMConnection`.
        """

        namespace = self._iparam_namespace_from(ObjectName)
        objectname = self._iparam_objectname(ObjectName)

        result = self.imethodcall(
            'ReferenceNames',
            namespace,
            ObjectName=objectname,
            ResultClass=self._iparam_classname(ResultClass),
            Role=Role,
            **extra)

        if result is None:
            return []

        return [x[2] for x in result[2]]

    def References(self, ObjectName, ResultClass=None, Role=None,
                   IncludeQualifiers=None, IncludeClassOrigin=None,
                   PropertyList=None, **extra):
        # pylint: disable=invalid-name, line-too-long
        """
        Retrieve the association instances (or association classes) that
        reference a source instance (or source class).

        This method performs the References operation.
        If the operation succeeds, this method returns.
        Otherwise, this method raises an exception.

        Parameters:

          ObjectName:
            For instance level usage: The instance path of the source instance,
            as a :class:`~pywbem.CIMInstanceName` object. If that object does
            not specify a namespace, the default namespace of the connection is
            used.

            For class level usage: The class path of the source class, as a
            :term:`unicode string`, :term:`byte string` or :class:`~pywbem.CIMClassName`
            object.
            If specified as a string, the string is interpreted as a class name
            in the default namespace of the connection, and can have any
            lexical case.
            If specified as a :class:`~pywbem.CIMClassName` object that does
            not specify a namespace, the default namespace of the connection is
            used.

          ResultClass (:term:`unicode string`, :term:`byte string` or :class:`~pywbem.CIMClassName`):
            Class name of an association class, in any lexical case,
            to filter the result to include only traversals of that association
            class (or subclasses).

            `None` means that no filtering is peformed.

          Role (:term:`unicode string` or :term:`byte string`):
            Role name (= property name) of the source end, in any
            lexical case, to filter the result to include only traversals from
            that source role.

            `None` means that no filtering is peformed.

          IncludeQualifiers (bool):
            Indicates that qualifiers are to be included in the returned
            instances (or classes), as follows:

            * If `False`, qualifiers not included.
            * If `True`, qualifiers are included if the WBEM server implements
              support for this parameter.
            * If `None`, this parameter is not passed to the WBEM server, and
              causes the server-implemented default to be used. :term:`DSP0200`
              defines that the server-implemented default is `False`.

            This parameter has been deprecated in :term:`DSP0200`. Clients cannot
            rely on it being implemented by WBEM servers.

          IncludeClassOrigin (bool):
            Indicates that class origin information is to be included on each
            property or method in the returned instances (or classes), as
            follows:

            * If `False`, class origin information is not included.
            * If `True`, class origin information is included.
            * If `None`, this parameter is not passed to the WBEM server, and
              causes the server-implemented default to be used. :term:`DSP0200`
              defines that the server-implemented default is `False`.

          PropertyList (iterable of :term:`unicode string` or :term:`byte string`):
            An iterable specifying the names of the properties to be included
            in the returned instances (or classes), in any lexical case.
            An empty iterable indicates to include no properties.

            If `None`, all properties are included.

        Keyword Arguments:

          extra :
            Additional keyword arguments are passed as additional operation
            parameters to the WBEM server.
            Note that :term:`DSP0200` does not define any additional parameters
            for this operation.

        Returns:

            For instance level usage, a list of :class:`~pywbem.CIMInstance`
            objects that are representations of the referencing association
            instances.

            For class level usage, a list of :class:`~pywbem.CIMClass` objects
            that are representations the referencing association classes.

        Raises:

            Exceptions described in :class:`~pywbem.WBEMConnection`.
        """

        namespace = self._iparam_namespace_from(ObjectName)
        objectname = self._iparam_objectname(ObjectName)

        result = self.imethodcall(
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
            return []

        return [x[2] for x in result[2]]

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

        This method performs the InvokeMethod operation.
        If the operation succeeds, this method returns.
        Otherwise, this method raises an exception.

        Input parameters for the CIM method can be specified using the
        `Params` parameter, and using keyword parameters.
        The overall list of input parameters is formed from the list of
        parameters specified in `Params` (preserving its order), followed by
        the set of keyword parameters (in any order). There is no checking for
        duplicate parameter names.

        Parameters:

          MethodName (:term:`unicode string` or :term:`byte string`):
            Name of the method to be invoked (without parenthesis or any
            parameter signature), in any lexical case.

          ObjectName:
            For instance level usage: The instance path of the target instance,
            as a :class:`~pywbem.CIMInstanceName` object. If that object does
            not specify a namespace, the default namespace of the connection is
            used.

            For class level usage: The class path of the target class, as a
            :term:`unicode string`, :term:`byte string` or
            :class:`~pywbem.CIMClassName` object.
            If specified as a string, the string is interpreted as a class name
            in the default namespace of the connection, and can have any
            lexical case.
            If specified as a :class:`~pywbem.CIMClassName` object that does
            not specify a namespace, the default namespace of the connection is
            used.

          Params (list of tuples of name,value):
            A list of input parameters for the CIM method.

            Each list item represents a single input parameter for the CIM
            method and must be a `tuple(name, value)`, with:

            * name (:term:`unicode string` or :term:`byte string`):
              Parameter name, in any lexical case
            * value (:term:`CIM data type`):
              Parameter value

        Keyword Arguments:

          : Each keyword parameter represents a single input parameter for the
            CIM method, with:

            * key (:term:`unicode string` or :term:`byte string`):
              Parameter name, in any lexical case
            * value (:term:`CIM data type`):
              Parameter value

        Returns:

            `tuple(returnvalue, outparams)`

            * returnvalue (:term:`CIM data type`):
              Return value of the CIM method.
            * outparams (:ref:`NocaseDict`):
              Dictionary with all provided output parameters of the CIM method,
              with:

                * key (:term:`unicode string`):
                  CIM parameter name
                * value (:term:`CIM data type`):
                  CIM parameter value

        Raises:

            Exceptions described in :class:`~pywbem.WBEMConnection`.
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
    # Query operations
    #

    def ExecQuery(self, QueryLanguage, Query, namespace=None, **extra):
        # pylint: disable=invalid-name
        """
        Execute a query in a namespace.

        This method performs the ExecQuery operation.
        If the operation succeeds, this method returns.
        Otherwise, this method raises an exception.

        Parameters:

          QueryLanguage (:term:`unicode string` or :term:`byte string`):
            Name of the query language used in the `Query` parameter.

          Query (:term:`unicode string` or :term:`byte string`):
            Query string in the query language specified in the `QueryLanguage`
            parameter.

          namespace (:term:`unicode string` or :term:`byte string`):
            Name of the CIM namespace to be used, in any lexical case.

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

            These instances have their `path` instance variable set to identify
            their creation class and the target namespace of the query, but
            they are not addressable instances.

        Raises:

            Exceptions described in :class:`~pywbem.WBEMConnection`.
        """

        namespace = self._iparam_namespace_from(namespace)

        result = self.imethodcall(
            'ExecQuery',
            namespace,
            QueryLanguage=QueryLanguage,
            Query=Query,
            **extra)

        instances = []

        if result is not None:
            instances = [tt[2] for tt in result[2]]

        for instance in instances:
            instance.path.namespace = namespace

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

        This method performs the EnumerateClassNames operation.
        If the operation succeeds, this method returns.
        Otherwise, this method raises an exception.

        Parameters:

          namespace (:term:`unicode string` or :term:`byte string`):
            Name of the namespace in which the class names are to be
            enumerated, in any lexical case.

            If `None`, the default namespace of the connection object will be
            used.

          ClassName (:term:`unicode string` or :term:`byte string` or :class:`~pywbem.CIMClassName`):
            Name of the class whose subclasses are to be retrieved, in any
            lexical case.

            If `None`, the top-level classes in the namespace will be
            retrieved.

          DeepInheritance (bool):
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

        namespace = self._iparam_namespace_from(namespace)
        classname = self._iparam_classname(ClassName)

        result = self.imethodcall(
            'EnumerateClassNames',
            namespace,
            ClassName=classname,
            DeepInheritance=DeepInheritance,
            **extra)

        if result is None:
            return []
        else:
            return [x.classname for x in result[2]]

    def EnumerateClasses(self, namespace=None, ClassName=None,
                         DeepInheritance=None, LocalOnly=None,
                         IncludeQualifiers=None, IncludeClassOrigin=None,
                         **extra):
        # pylint: disable=invalid-name,line-too-long
        """
        Enumerate the subclasses of a class, or the top-level classes in a
        namespace.

        This method performs the EnumerateClasses operation.
        If the operation succeeds, this method returns.
        Otherwise, this method raises an exception.

        Parameters:

          namespace (:term:`unicode string` or :term:`byte string`):
            Name of the namespace in which the classes are to be enumerated, in
            any lexical case.

            If `None`, the default namespace of the connection object will be
            used.

          ClassName (:term:`unicode string` or :term:`byte string` or :class:`~pywbem.CIMClassName`):
            Name of the class whose subclasses are to be retrieved, in any
            lexical case.

            If `None`, the top-level classes in the namespace will be
            retrieved.

          DeepInheritance (bool):
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

          LocalOnly (bool):
            Indicates that inherited properties, methods, and qualifiers are to
            be excluded from the returned classes, as follows.

            * If `False`, inherited elements are not excluded.
            * If `True`, inherited elements are excluded.
            * If `None`, this parameter is not passed to the WBEM server, and
              causes the server-implemented default to be used. :term:`DSP0200`
              defines that the server-implemented default is `True`.

          IncludeQualifiers (bool):
            Indicates that qualifiers are to be included in the returned
            classes, as follows:

            * If `False`, qualifiers not included.
            * If `True`, qualifiers are included.
            * If `None`, this parameter is not passed to the WBEM server, and
              causes the server-implemented default to be used. :term:`DSP0200`
              defines that the server-implemented default is `False`.

          IncludeClassOrigin (bool):
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

        namespace = self._iparam_namespace_from(namespace)
        classname = self._iparam_classname(ClassName)

        result = self.imethodcall(
            'EnumerateClasses',
            namespace,
            ClassName=classname,
            DeepInheritance=DeepInheritance,
            LocalOnly=LocalOnly,
            IncludeQualifiers=IncludeQualifiers,
            IncludeClassOrigin=IncludeClassOrigin,
            **extra)

        if result is None:
            return []

        return result[2]

    def GetClass(self, ClassName, namespace=None, LocalOnly=None,
                 IncludeQualifiers=None, IncludeClassOrigin=None,
                 PropertyList=None, **extra):
        # pylint: disable=invalid-name, line-too-long
        """
        Retrieve a class.

        This method performs the GetClass operation.
        If the operation succeeds, this method returns.
        Otherwise, this method raises an exception.

        Parameters:

          ClassName (:term:`unicode string` or :term:`byte string` or :class:`~pywbem.CIMClassName`):
            Name of the class to be retrieved, in any lexical case.

          namespace (:term:`unicode string` or :term:`byte string`):
            Name of the namespace of the class to be retrieved, in any lexical
            case.

            If `None`, the default namespace of the connection object will be
            used.

          LocalOnly (bool):
            Indicates that inherited properties, methods, and qualifiers are to
            be excluded from the returned class, as follows.

            * If `False`, inherited elements are not excluded.
            * If `True`, inherited elements are excluded.
            * If `None`, this parameter is not passed to the WBEM server, and
              causes the server-implemented default to be used. :term:`DSP0200`
              defines that the server-implemented default is `True`.

          IncludeQualifiers (bool):
            Indicates that qualifiers are to be included in the returned
            class, as follows:

            * If `False`, qualifiers not included.
            * If `True`, qualifiers are included.
            * If `None`, this parameter is not passed to the WBEM server, and
              causes the server-implemented default to be used. :term:`DSP0200`
              defines that the server-implemented default is `False`.

          IncludeClassOrigin (bool):
            Indicates that class origin information is to be included on each
            property and method in the returned class, as follows:

            * If `False`, class origin information is not included.
            * If `True`, class origin information is included.
            * If `None`, this parameter is not passed to the WBEM server, and
              causes the server-implemented default to be used. :term:`DSP0200`
              defines that the server-implemented default is `False`.

          PropertyList (iterable of :term:`unicode string` or :term:`byte string`):
            An iterable specifying the names of the properties to be included
            in the returned class, in any lexical case.
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
        """

        namespace = self._iparam_namespace_from(namespace)
        classname = self._iparam_classname(ClassName)

        result = self.imethodcall(
            'GetClass',
            namespace,
            ClassName=classname,
            LocalOnly=LocalOnly,
            IncludeQualifiers=IncludeQualifiers,
            IncludeClassOrigin=IncludeClassOrigin,
            PropertyList=PropertyList,
            **extra)

        return result[2][0]

    def ModifyClass(self, ModifiedClass, namespace=None, **extra):
        # pylint: disable=invalid-name
        """
        Modify a class.

        This method performs the ModifyClass operation.
        If the operation succeeds, this method returns.
        Otherwise, this method raises an exception.

        Parameters:

          ModifiedClass (CIMClass):
            A representation of the modified class.

            Its class path (`path` instance variable) will be ignored.

            The properties, methods and qualifiers defined in this object
            specify what is to be modified.

            Typically, this object has been retrieved by other operations, such
            as :meth:`~pywbem.WBEMConnection.GetClass`.

          namespace (:term:`unicode string` or :term:`byte string`):
            Name of the namespace in which the class is to be modified, in any
            lexical case.

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

        namespace = self._iparam_namespace_from(namespace)

        klass = ModifiedClass.copy()
        klass.path = None

        self.imethodcall(
            'ModifyClass',
            namespace,
            ModifiedClass=klass,
            **extra)

    def CreateClass(self, NewClass, namespace=None, **extra):
        # pylint: disable=invalid-name
        """
        Create a class.

        This method performs the CreateClass operation.
        If the operation succeeds, this method returns.
        Otherwise, this method raises an exception.

        Parameters:

          NewClass (CIMClass):
            A representation of the class to be created.

            Its class path (`path` instance variable) will be ignored.

            The properties, methods and qualifiers defined in this object
            specify how the class is to be created.

          namespace (:term:`unicode string` or :term:`byte string`):
            Name of the namespace in which the class is to be created, in any
            lexical case.

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

        namespace = self._iparam_namespace_from(namespace)

        klass = NewClass.copy()
        klass.path = None

        self.imethodcall(
            'CreateClass',
            namespace,
            NewClass=klass,
            **extra)

    def DeleteClass(self, ClassName, namespace=None, **extra):
        # pylint: disable=invalid-name,line-too-long
        """
        Delete a class.

        This method performs the DeleteClass operation.
        If the operation succeeds, this method returns.
        Otherwise, this method raises an exception.

        Parameters:

          ClassName (:term:`unicode string` or :term:`byte string` or :class:`~pywbem.CIMClassName`):
            Name of the class to be deleted, in any lexical case.

            Its namespace component will be ignored.

          namespace (:term:`unicode string` or :term:`byte string`):
            Name of the namespace of the class to be deleted, in any lexical
            case.

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

        namespace = self._iparam_namespace_from(namespace)
        classname = self._iparam_classname(ClassName)

        self.imethodcall(
            'DeleteClass',
            namespace,
            ClassName=classname,
            **extra)

    #
    # Qualifier operations
    #

    def EnumerateQualifiers(self, namespace=None, **extra):
        # pylint: disable=invalid-name
        """
        Enumerate qualifier declarations.

        This method performs the EnumerateQualifiers operation.
        If the operation succeeds, this method returns.
        Otherwise, this method raises an exception.

        Parameters:

          namespace (:term:`unicode string` or :term:`byte string`):
            Name of the namespace in which the qualifier declarations are to be
            enumerated, in any lexical case.

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

        namespace = self._iparam_namespace_from(namespace)

        result = self.imethodcall(
            'EnumerateQualifiers',
            namespace,
            **extra)

        if result is not None:
            qualifiers = result[2]
        else:
            qualifiers = []

        return qualifiers

    def GetQualifier(self, QualifierName, namespace=None, **extra):
        # pylint: disable=invalid-name
        """
        Retrieve a qualifier declaration.

        This method performs the GetQualifier operation.
        If the operation succeeds, this method returns.
        Otherwise, this method raises an exception.

        Parameters:

          Qualifier (:term:`unicode string` or :term:`byte string`):
            Name of the qualifier declaration to be retrieved, in any lexical
            case.

          namespace (:term:`unicode string` or :term:`byte string`):
            Name of the namespace of the qualifier declaration, in any lexical
            case.

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

        namespace = self._iparam_namespace_from(namespace)

        result = self.imethodcall(
            'GetQualifier',
            namespace,
            QualifierName=QualifierName,
            **extra)

        if result is not None:
            names = result[2][0]

        return names

    def SetQualifier(self, QualifierDeclaration, namespace=None, **extra):
        # pylint: disable=invalid-name
        """
        Create or modify a qualifier declaration.

        This method performs the SetQualifier operation.
        If the operation succeeds, this method returns.
        Otherwise, this method raises an exception.

        Parameters:

          QualifierDeclaration (CIMQualifierDeclaration):
            Representation of the qualifier declaration to be created or
            modified.

          namespace (:term:`unicode string` or :term:`byte string`):
            Name of the namespace in which the qualifier declaration is to be
            created or modified, in any lexical case.

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

        namespace = self._iparam_namespace_from(namespace)

        unused_result = self.imethodcall(
            'SetQualifier',
            namespace,
            QualifierDeclaration=QualifierDeclaration,
            **extra)

    def DeleteQualifier(self, QualifierName, namespace=None, **extra):
        # pylint: disable=invalid-name
        """
        Delete a qualifier declaration.

        This method performs the DeleteQualifier operation.
        If the operation succeeds, this method returns.
        Otherwise, this method raises an exception.

        Parameters:

          Qualifier (:term:`unicode string` or :term:`byte string`):
            Name of the qualifier declaration to be deleted, in any lexical
            case.

          namespace (:term:`unicode string` or :term:`byte string`):
            Name of the namespace in which the qualifier declaration is to be
            deleted, in any lexical case.

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

        namespace = self._iparam_namespace_from(namespace)

        unused_result = self.imethodcall(
            'DeleteQualifier',
            namespace,
            QualifierName=QualifierName,
            **extra)

def is_subclass(ch, ns, super_class, sub):
    """Determine if one class is a subclass of another class.

    Parameters:

      ch:
        A CIMOMHandle.  Either a pycimmb.CIMOMHandle or a
        :class:`~pywbem.WBEMConnection` object.

      ns (:term:`unicode string` or :term:`byte string`):
        Namespace, in any lexical case.

      super_class (:term:`unicode string` or :term:`byte string`):
        Super class name, in any lexical case.

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
