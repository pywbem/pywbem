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
import warnings
from collections import namedtuple

import six
from . import cim_xml
from .cim_constants import DEFAULT_NAMESPACE
from .cim_types import CIMType, CIMDateTime, atomic_to_cim_xml
from .cim_obj import CIMInstance, CIMInstanceName, CIMClass, \
                     CIMClassName, NocaseDict, _ensure_unicode, tocimxml, \
                     tocimobj
from .cim_http import get_object_header, wbem_request
from .tupleparse import parse_cim
from .tupletree import dom_to_tupletree
from .exceptions import Error, ParseError, AuthError, ConnectionError, \
                        TimeoutError, CIMError
from .cim_constants import *  # pylint: disable=wildcard-import

__all__ = ['WBEMConnection', 'PegasusUDSConnection', 'SFCBUDSConnection',
           'OpenWBEMUDSConnection']

# Global named tuples. Used by the pull operation responses to return
# (entities, end_of_sequence, and enumeration_context) to the caller.

# openenumerateInstances, OpenAssociators, etc and PullInstanceWithPath
# responses
#pylint: disable=invalid-name
pull_path_result_tuple = namedtuple("pull_path_result_tuple",
                                    ["paths", "eos", "context"])

# OpenEnumerateInstancePaths, etc.  and PullInstancePath responses
pull_inst_result_tuple = namedtuple("pull_inst_result_tuple",
                                    ["instances", "eos", "context"])

# openqueryInstances and PullInstance responses
pull_query_result_tuple = namedtuple("pull_query_result_tuple",
                                     ["instances", "eos", "context",
                                      "QueryResultClass"])

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
        are set as public instance variables with the same name.

      debug (:class:`py:bool`): A boolean indicating whether logging of
        the last request and last reply is enabled.

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
    """

    def __init__(self, url, creds=None, default_namespace=DEFAULT_NAMESPACE,
                 x509=None, verify_callback=None, ca_certs=None,
                 no_verification=False, timeout=None):
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

            If `None`, the client will not generate ``Authenticate`` headers
            in the HTTP request. Otherwise, the client will generate an
            ``Authenticate`` header using HTTP Basic Authentication.

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
            by the TLS/SSL support in the PyWBEM client.

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
              certificate specified in the second argument passed or did not
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

            If `None`, default system paths will be used (see
            `pywbem.cim_http.DEFAULT_CA_CERT_PATHS`)

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

    def imethodcall(self, methodname, namespace, response_params_rqd=None, \
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

    def _imethodcall(self, methodname, namespace, response_params_rqd=None, \
                     **params):
        """
        Perform an intrinsic CIM-XML operation.
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

        if tup_tree[0] != 'SIMPLERSP':
            raise ParseError('Expecting SIMPLERSP element, got %s' %\
                             tup_tree[0])
        tup_tree = tup_tree[2]

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
            #expect either ERROR | IRETURNVALUE*
            err = tup_tree[0]
            if err[0] != 'IRETURNVALUE':
                raise ParseError('Expecting IRETURNVALUE element, got %s' \
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

        if tt[0] != 'SIMPLERSP':
            raise ParseError('Expecting SIMPLERSP element, got %s' % tt[0])
        tt = tt[2]

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
            raise TypeError('Expecting None (for default), or a namespace ' \
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
            raise TypeError('Expecting None (for default), a class name ' \
                            'string, a CIMClassName object, or a ' \
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
        instances of its subclasses) in a namespace.

        This method performs the EnumerateInstanceNames operation
        (see :term:`DSP0200`).
        If the operation succeeds, this method returns.
        Otherwise, this method raises an exception.

        Parameters:

          ClassName (:term:`string` or :class:`~pywbem.CIMClassName`):
            Name of the class to be enumerated, in any lexical case.
            If specified as a :class:`~pywbem.CIMClassName` object, its host
            component will be ignored.

          namespace (:term:`string`):
            Name of the CIM namespace to be used, in any lexical case.

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
            enumerated instance paths.

        Raises:

            Exceptions described in :class:`~pywbem.WBEMConnection`.
        """

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
        (see :term:`DSP0200`).
        If the operation succeeds, this method returns.
        Otherwise, this method raises an exception.

        Parameters:

          ClassName (:term:`string` or :class:`~pywbem.CIMClassName`):
            Name of the class to be enumerated, in any lexical case.
            If specified as a :class:`~pywbem.CIMClassName` object, its host
            component will be ignored.

          namespace (:term:`string`):
            Name of the CIM namespace to be used, in any lexical case.

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

        if namespace is None and isinstance(ClassName, CIMClassName):
            namespace = ClassName.namespace
        namespace = self._iparam_namespace_from_namespace(namespace)
        classname = self._iparam_classname(ClassName)

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

        instances = []

        if result is not None:
            instances = result[0][2]

        # TODO ks 6/16 would the setattr be faster?
        # TODO: ks 6/16 should we check before setting?
        #[setattr(i.path, 'namespace', namespace) for i in instances]
        for instance in instances:
            instance.path.namespace = namespace

        return instances

    @staticmethod
    def _get_rslt_params(result, namespace):
        """Common processing for pull results to separate
           end-of-sequence, enum-context, and endities in IRETURNVALUE.
           Returns tuple of entities in IRETURNVALUE, end_of_sequence,
           and enumeration_context)
        """
        #TODO ks 6/16 make this None???
        rtn_objects = []
        end_of_sequence = False
        enumeration_context = None
        valid_result = False

        for p in result:
            if p[0] == 'EndOfSequence':
                if p[2] is None:
                    valid_result = True
                elif isinstance(p[2], six.string_types) and \
                    p[2].lower() in ['true', 'false']:
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
            raise CIMError(CIM_ERR_INVALID_PARAMETER, "EndOfSequence " \
                           "or EnumerationContext required")

        # convert enum context if eos is True
        rtn_ctxt = None if end_of_sequence else (enumeration_context,
                                                 namespace)

        return (rtn_objects, end_of_sequence, rtn_ctxt)

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
        (see :term:`DSP0200`).
        If the operation succeeds, this method returns status on the
        enumeration session and optionally instance paths.
        Otherwise, this method raises an exception.

        Use :meth:`~pywbem.WBEMConnection.PullInstancePaths` request to
        retrieve the next set of instance paths
        or the :meth:`~pywbem.WBEMConnection.CloseEnumeration`
        request to close the enumeration session early.

        Parameters:

          ClassName (:term:`string` or :class:`~pywbem.CIMClassName`):
            Name of the class to be enumerated, in any lexical case.
            If specified as a :class:`~pywbem.CIMClassName` object, its
            namespace component will be used as a default namespace as
            described for the namespace argument, and its host component
            will be ignored.

          namespace (:term:`string`):
            Name of the CIM namespace to be used, in any lexical case.

            If `None`, the namespace of the `ClassName` parameter will be used,
            if specified as a :class:`~pywbem.CIMClassName` object. If that is
            also `None`, the default namespace of the connection will be used.

          FilterQueryLanguage (:term:`string`):
            A string defining the name of the query language
            used for the `FilterQuery` argument. The DMTF defined language
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

        :Returns:

            A :class:`py:namedtuple` containing the following named elements:

            * `paths` (list of :class:`~pywbem.CIMInstanceName`):
              Representations of the initial set of enumerated instance
              paths.
            * `eos` (:class:`py:bool`):
              Indicates whether the enumeration session is exhausted
              after returning the initial set of enumerated instances.

              - If `True`, the enumeration session is exhausted, and the
                server has closed the enumeration session.
              - If `False`, the enumeration session is not exhausted.

            * `context` (tuple of (server_context, namespace)):
               Identifies the opened enumeration session. The client must
               provide this value for subsequent operations on this
               enumeration session. The tuple items are:

               - server_context (:term:`string`):
                 Enumeration context string returned by the server if
                 the session is not exhausted, or `None` otherwise. This string
                 is opaque for the client.
               - namespace (:term:`string`):
                 Name of the CIM namespace that was used for this operation.

               NOTE: This inner tuple hides the need for a CIM namespace
               on subsequent operations in the enumeration session. CIM
               operations always require target namespace, but it never
               makes sense to specify a different one in subsequent
               operations on the same enumeration session.

        Raises:

            Exceptions described in :class:`~pywbem.WBEMConnection`.
        """
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

        return pull_path_result_tuple(*self._get_rslt_params(result, namespace))


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
        (see :term:`DSP0200`)
        .
        If the operation succeeds, this method returns enumeration session
        status and optionally instances.
        Otherwise, this method raises an exception.

        Use :meth:`~pywbem.WBEMConnection.PullInstances` request to
        retrieve the next set of instance paths
        or the :meth:`~pywbem.WBEMConnection.CloseEnumeration`
        request to close the enumeration session early.

        :Parameters:

          ClassName (:term:`string` or :class:`~pywbem.CIMClassName`):
            Name of the class to be enumerated, in any lexical case.
            If specified as a :class:`~pywbem.CIMClassName` object, its
            namespace component will be used as a default namespace as
            described for the namespace argument, and its host component
            will be ignored.

          namespace (:term:`string`):
            Name of the CIM namespace to be used, in any lexical case.

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
            included in the returned instances, in any lexical case.

            An empty iterable indicates to include no properties.

            If `None`, all properties are included.

          FilterQueryLanguage (:term:`string`):
            A string defining the name of the query language
            used for the `FilterQuery` argument. The DMTF defined language
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

        :Returns:

            A :class:`py:namedtuple` containing the following named elements:

            * `instances` (list of :class:`~pywbem.CIMInstance`):
              Representations of the initial set of enumerated instances.
            * `eos` (:class:`py:bool`):
              Indicates whether the enumeration session is exhausted
              after returning the initial set of enumerated instances.

              - If `True`, the enumeration session is exhausted, and the
                server has closed the enumeration session.
              - If `False`, the enumeration session is not exhausted.

            * `context` (tuple of (server_context, namespace)):
               Identifies the opened enumeration session. The client must
               provide this value for subsequent operations on this
               enumeration session. The tuple items are:

               - server_context (:term:`string`):
                 Enumeration context string returned by the server if
                 the session is not exhausted, or `None` otherwise. This string
                 is opaque for the client.
               - namespace (:term:`string`):
                 Name of the CIM namespace that was used for this operation.

               NOTE: This inner tuple hides the need for a CIM namespace
               on subsequent operations in the enumeration session. CIM
               operations always require target namespace, but it never
               makes sense to specify a different one in subsequent
               operations on the same enumeration session.

        Keyword Arguments:

          extra :
            Additional keyword arguments are passed as additional operation
            parameters to the WBEM server.
            Note that :term:`DSP0200` does not define any additional parameters
            for this operation.

        :Exceptions:

            See the list of exceptions described in `WBEMConnection`.
        """

        if namespace is None and isinstance(ClassName, CIMClassName):
            namespace = ClassName.namespace
        namespace = self._iparam_namespace_from_namespace(namespace)
        classname = self._iparam_classname(ClassName)

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

        return pull_inst_result_tuple(*self._get_rslt_params(result, namespace))


    def OpenReferenceInstancePaths(self, InstanceName, ResultClass=None,
                                   Role=None,
                                   FilterQueryLanguage=None, FilterQuery=None,
                                   OperationTimeout=None, ContinueOnError=None,
                                   MaxObjectCount=None, **extra):
        # pylint: disable=invalid-name
        """
        Open an enumeration session to retrieve the instance paths of
        the association instances that reference a source instance.

        This method does not support retrieving classes

        This method performs the OpenReferenceInstancePaths operation
        (see :term:`DSP0200`).
        If the operation succeeds, this method returns enumeration session
        status and optionally instance paths.
        Otherwise, this method raises an exception.

        Use :meth:`~pywbem.WBEMConnection.PullInstances` request to
        retrieve the next set of instance paths
        or the :meth:`~pywbem.WBEMConnection.CloseEnumeration`
        request to close the enumeration session early.

        Parameters:

          InstanceName:
            The instance path of the source instance,
            as a :class:`~pywbem.CIMInstanceName` object. If that object does
            not specify a namespace, the default namespace of the connection is
            used.

          ResultClass (:term:`string` or :class:`~pywbem.CIMClassName`):
            Class name of an association class, in any lexical case,
            to filter the result to include only traversals of that association
            class (or subclasses).

            `None` means that no such filtering is peformed.

          Role (:term:`string`):
            Role name (= property name) of the source end, in any
            lexical case, to filter the result to include only traversals from
            that source role.

            `None` means that no such filtering is peformed.

          FilterQueryLanguage (:term:`string`):
            A string defining the name of the query language
            used for the `FilterQuery` argument. The DMTF defined language
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

        :Returns:

            A :class:`py:namedtuple` containing the following named elements:

            * `paths` (list of :class:`~pywbem.CIMInstanceName`):
              Representations of the initial set of enumerated instance paths.
            * `eos` (:class:`py:bool`):
              Indicates whether the enumeration session is exhausted
              after returning the initial set of enumerated instances.

              - If `True`, the enumeration session is exhausted, and the
                server has closed the enumeration session.
              - If `False`, the enumeration session is not exhausted.

            * `context` (tuple of (server_context, namespace)):
               Identifies the opened enumeration session. The client must
               provide this value for subsequent operations on this
               enumeration session. The tuple items are:

               - server_context (:term:`string`):
                 Enumeration context string returned by the server if
                 the session is not exhausted, or `None` otherwise. This string
                 is opaque for the client.
               - namespace (:term:`string`):
                 Name of the CIM namespace that was used for this operation.

               NOTE: This inner tuple hides the need for a CIM namespace
               on subsequent operations in the enumeration session. CIM
               operations always require target namespace, but it never
               makes sense to specify a different one in subsequent
               operations on the same enumeration session.

        Keyword Arguments:

          extra :
            Additional keyword arguments are passed as additional operation
            parameters to the WBEM server.
            Note that :term:`DSP0200` does not define any additional parameters
            for this operation.

        :Exceptions:

            See the list of exceptions described in `WBEMConnection`.
        """

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

        return pull_path_result_tuple(*self._get_rslt_params(result, namespace))


    def OpenReferenceInstances(self, InstanceName, ResultClass=None,
                               Role=None, IncludeQualifiers=None,
                               IncludeClassOrigin=None, PropertyList=None,
                               FilterQueryLanguage=None, FilterQuery=None,
                               OperationTimeout=None, ContinueOnError=None,
                               MaxObjectCount=None, **extra):
        # pylint: disable=invalid-name
        """
        Open an enumeration session to retrieve the association instances
        that reference a source instance.

        This method performs the OpenReferenceInstances operation
        (see :term:`DSP0200`).
        If the operation succeeds, this method returns enumeration session
        status and optionally instances.
        Otherwise, this method raises an exception.

        Use :meth:`~pywbem.WBEMConnection.PullInstances` request to
        retrieve the next set of instance paths
        or the :meth:`~pywbem.WBEMConnection.CloseEnumeration`
        request to close the enumeration session early.

        Parameters:

          InstanceName:
            The instance path of the source instance,
            as a :class:`~pywbem.CIMInstanceName` object. If that object does
            not specify a namespace, the default namespace of the connection is
            used.

          ResultClass (:term:`string` or :class:`~pywbem.CIMClassName`):
            Class name of an association class, in any lexical case,
            to filter the result to include only traversals of that association
            class (or subclasses).

            `None` means that no such filtering is peformed.

          Role (:term:`string`):
            Role name (= property name) of the source end, in any
            lexical case, to filter the result to include only traversals from
            that source role.

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
            in the returned instances (or classes), in any lexical case.
            An empty iterable indicates to include no properties.

            If `None`, all properties are included.

          FilterQueryLanguage (:term:`string`):
            A string defining the name of the query language
            used for the `FilterQuery` argument. The DMTF defined language
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

        :Returns:

            A :class:`py:namedtuple` containing the following named elements:

            * `instances` (list of :class:`~pywbem.CIMInstance`):
              Representations of the initial set of enumerated instance paths.
            * `eos` (:class:`py:bool`):
              Indicates whether the enumeration session is exhausted
              after returning the initial set of enumerated instances.

              - If `True`, the enumeration session is exhausted, and the
                server has closed the enumeration session.
              - If `False`, the enumeration session is not exhausted.

            * `context` (tuple of (server_context, namespace)):
               Identifies the opened enumeration session. The client must
               provide this value for subsequent operations on this
               enumeration session. The tuple items are:

               - server_context (:term:`string`):
                 Enumeration context string returned by the server if
                 the session is not exhausted, or `None` otherwise. This string
                 is opaque for the client.
               - namespace (:term:`string`):
                 Name of the CIM namespace that was used for this operation.

               NOTE: This inner tuple hides the need for a CIM namespace
               on subsequent operations in the enumeration session. CIM
               operations always require target namespace, but it never
               makes sense to specify a different one in subsequent
               operations on the same enumeration session.

        Keyword Arguments:

          extra :
            Additional keyword arguments are passed as additional operation
            parameters to the WBEM server.
            Note that :term:`DSP0200` does not define any additional parameters
            for this operation.

        :Exceptions:

            See the list of exceptions described in `WBEMConnection`.

        """

        #TODO ks 6/16 Limit to instance name. No classname allowed.
        namespace = self._iparam_namespace_from_objectname(InstanceName)
        instancename = self._iparam_instancename(InstanceName)

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

        return pull_inst_result_tuple(*self._get_rslt_params(result, namespace))


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

        This method performs the OpenAssociatorInstancePaths operation
        (see :term:`DSP0200`).
        If the operation succeeds, this method returns enumeration session
        status and optionally instance paths.
        Otherwise, this method raises an exception.

        This method does not allow the option of defining `InstanceName`
        as a class and retrieving associated classes.

        Use :meth:`~pywbem.WBEMConnection.PullInstancePaths` request to
        retrieve the next set of instance paths
        or the :meth:`~pywbem.WBEMConnection.CloseEnumeration`
        request to close the enumeration session early.

        Parameters:

          InstanceName:
            The instance path of the source instance,
            as a :class:`~pywbem.CIMInstanceName` object. If that object does
            not specify a namespace, the default namespace of the connection is
            used.

          AssocClass (:term:`string` or :class:`~pywbem.CIMClassName`):
            Class name of an association class, in any lexical case,
            to filter the result to include only traversals of that association
            class (or subclasses).

            `None` means that no such filtering is peformed.

          ResultClass (:term:`string` or :class:`~pywbem.CIMClassName`):
            Class name of an associated class, in any lexical case,
            to filter the result to include only traversals to that associated
            class (or subclasses).

            `None` means that no such filtering is peformed.

          Role (:term:`string`):
            Role name (= property name) of the source end, in any
            lexical case, to filter the result to include only traversals from
            that source role.

            `None` means that no such filtering is peformed.

          ResultRole (:term:`string`):
            Role name (= property name) of the far end, in any
            lexical case, to filter the result to include only traversals to
            that far role.

            `None` means that no such filtering is peformed.

          FilterQueryLanguage (:term:`string`):
            A string defining the name of the query language
            used for the `FilterQuery` argument. The DMTF defined language
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

        :Returns:

            A :class:`py:namedtuple` containing the following named elements:

            * `paths` (list of :class:`~pywbem.CIMInstanceName`):
              Representations of the initial set of enumerated instance
              names.
            * `eos` (:class:`py:bool`):
              Indicates whether the enumeration session is exhausted
              after returning the initial set of enumerated instances.

              - If `True`, the enumeration session is exhausted, and the
                server has closed the enumeration session.
              - If `False`, the enumeration session is not exhausted.

            * `context` (tuple of (server_context, namespace)):
               Identifies the opened enumeration session. The client must
               provide this value for subsequent operations on this
               enumeration session. The tuple items are:

               - server_context (:term:`string`):
                 Enumeration context string returned by the server if
                 the session is not exhausted, or `None` otherwise. This string
                 is opaque for the client.
               - namespace (:term:`string`):
                 Name of the CIM namespace that was used for this operation.

               NOTE: This inner tuple hides the need for a CIM namespace
               on subsequent operations in the enumeration session. CIM
               operations always require target namespace, but it never
               makes sense to specify a different one in subsequent
               operations on the same enumeration session.

        Keyword Arguments:

          extra :
            Additional keyword arguments are passed as additional operation
            parameters to the WBEM server.
            Note that :term:`DSP0200` does not define any additional parameters
            for this operation.

        :Exceptions:

            See the list of exceptions described in `WBEMConnection`.
        """

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

        return pull_path_result_tuple(*self._get_rslt_params(result, namespace))


    def OpenAssociatorInstances(self, InstanceName, AssocClass=None,
                                ResultClass=None, Role=None, ResultRole=None,
                                IncludeQualifiers=None,
                                IncludeClassOrigin=None,
                                PropertyList=None, FilterQueryLanguage=None,
                                FilterQuery=None, OperationTimeout=None,
                                ContinueOnError=None, MaxObjectCount=None,
                                **extra):
        # pylint: disable=invalid-name
        """
        Open an enumeration session to retrieve the instances associated
        to a source instance.

        This method performs the OpenAssociatorInstances operation
        (see :term:`DSP0200`).
        If the operation succeeds, this method returns enumeration session
        status and optionally instances.
        Otherwise, this method raises an exception.

        NOTE: This method does not allow the option of defined `InstanceName`
        as a class and retrieving associated classes.

        The subsequent operation after this open is successful
        and result.eos = False must be either the
        :meth:`~pywbem.WBEMConnection.PullInstances` request
        or the :meth:`~pywbem.WBEMConnection.CloseEnumeration`
        request.

        Parameters:

          InstanceName:
            The instance path of the source instance,
            as a :class:`~pywbem.CIMInstanceName` object. If that object does
            not specify a namespace, the default namespace of the connection is
            used.

          AssocClass (:term:`string` or :class:`~pywbem.CIMClassName`):
            Class name of an association class, in any lexical case,
            to filter the result to include only traversals of that association
            class (or subclasses).

            `None` means that no such filtering is peformed.

          ResultClass (:term:`string` or :class:`~pywbem.CIMClassName`):
            Class name of an associated class, in any lexical case,
            to filter the result to include only traversals to that associated
            class (or subclasses).

            `None` means that no such filtering is peformed.

          Role (:term:`string`):
            Role name (= property name) of the source end, in any
            lexical case, to filter the result to include only traversals from
            that source role.

            `None` means that no such filtering is peformed.

          ResultRole (:term:`string`):
            Role name (= property name) of the far end, in any
            lexical case, to filter the result to include only traversals to
            that far role.

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
            in the returned instances (or classes), in any lexical case.
            An empty iterable indicates to include no properties.

            If `None`, all properties are included.

          FilterQueryLanguage (:term:`string`):
            A string defining the name of the query language
            used for the `FilterQuery` argument. The DMTF defined language
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

        :Returns:

            A :class:`py:namedtuple` containing the following named elements:

            * `instances` (list of :class:`~pywbem.CIMInstance`):
              Representations of the initial set of enumerated instances.
            * `eos` (:class:`py:bool`):
              Indicates whether the enumeration session is exhausted
              after returning the initial set of enumerated instances.

              - If `True`, the enumeration session is exhausted, and the
                server has closed the enumeration session.
              - If `False`, the enumeration session is not exhausted.

            * `context` (tuple of (server_context, namespace)):
               Identifies the opened enumeration session. The client must
               provide this value for subsequent operations on this
               enumeration session. The tuple items are:

               - server_context (:term:`string`):
                 Enumeration context string returned by the server if
                 the session is not exhausted, or `None` otherwise. This string
                 is opaque for the client.
               - namespace (:term:`string`):
                 Name of the CIM namespace that was used for this operation.

               NOTE: This inner tuple hides the need for a CIM namespace
               on subsequent operations in the enumeration session. CIM
               operations always require target namespace, but it never
               makes sense to specify a different one in subsequent
               operations on the same enumeration session.

        Keyword Arguments:

          extra :
            Additional keyword arguments are passed as additional operation
            parameters to the WBEM server.
            Note that :term:`DSP0200` does not define any additional parameters
            for this operation.

        :Exceptions:

            See the list of exceptions described in `WBEMConnection`.
        """

        namespace = self._iparam_namespace_from_objectname(InstanceName)
        instancename = self._iparam_instancename(InstanceName)

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

        return pull_inst_result_tuple(*self._get_rslt_params(result, namespace))


    def OpenQueryInstances(self, FilterQueryLanguage, FilterQuery,
                           namespace=None, ReturnQueryResultClass=None,
                           OperationTimeout=None, ContinueOnError=None,
                           MaxObjectCount=None, **extra):
        # pylint: disable=invalid-name
        """
        Open an enumeration session to execute a query in a namespace.

        This method performs the OpenQueryInstances operation
        (see :term:`DSP0200`).
        If the operation succeeds, this method returns enumeration session
        status and optionally instances.
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
            Name of the CIM namespace to be used, in any lexical case.

            If `None`, the default namespace of the connection object will be
            used.

          ReturnQueryResultClass  (:class:`py:bool`):
            Controls whether a class definition is returned in
            `QueryResultClass`.

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

        :Returns:

            A :class:`py:namedtuple` containing the following named elements:

            * `instances` (list of :class:`~pywbem.CIMInstance`):
              Representations of the initial set of enumerated instances.
            * `eos` (:class:`py:bool`):
              Indicates whether the enumeration session is exhausted
              after returning the initial set of enumerated instances.

              - If `True`, the enumeration session is exhausted, and the
                server has closed the enumeration session.
              - If `False`, the enumeration session is not exhausted.

            * `context` (tuple of (server_context, namespace)):
               Identifies the opened enumeration session. The client must
               provide this value for subsequent operations on this
               enumeration session. The tuple items are:

               - server_context (:term:`string`):
                 Enumeration context string returned by the server if
                 the session is not exhausted, or `None` otherwise. This string
                 is opaque for the client.
               - namespace (:term:`string`):
                 Name of the CIM namespace that was used for this operation.

            * `QueryResultClass` (:class:`pywbem.CIMClass`):
              If ReturnQuerhResultClass is True, this return parameter
              shall contain a class definition that defines the properties
              of each row of the query result.

              NOTE: The inner tuple hides the need for a CIM namespace
              on subsequent operations in the enumeration session. CIM
              operations always require target namespace, but it never
              makes sense to specify a different one in subsequent
              operations on the same enumeration session.

        Keyword Arguments:

          extra :
            Additional keyword arguments are passed as additional operation
            parameters to the WBEM server.
            Note that :term:`DSP0200` does not define any additional parameters
            for this operation.

        :Exceptions:

            See the list of exceptions described in `WBEMConnection`.
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

        query_class = _GetQueryRsltClass(result) if \
                          ReturnQueryResultClass else None

        return pull_query_result_tuple(insts, eos, enum_ctxt, query_class)



    def PullInstancesWithPath(self, context, MaxObjectCount,
                              **extra):
        # pylint: disable=invalid-name

        """
        Retrieve the next set of instances with path from an open enumeraton
        session defined by the `enumeration_context` parameter.  The retrieved
        instances include their instance paths.

        This method performs the PullInstanceWithPath operation
        (see :term:`DSP0200`).

        If the operation succeeds, this method returns enumeration session
        status and optionally instances.
        Otherwise, this method raises an exception.

        :Parameters:
          context (:term:`string`)
            Identifies the enumeraton session, including its current
            enumeration state. This must be the value of the `context`
            item in the :class:`py:namedtuple` returned from the previous
            open or pull operation for this enumeration.

            The tuple items are:

            - server_context (:term:`string`):
              Enumeration context string returned by the server. This
              string is opaque for the client.
            - namespace (:term:`string`):
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

        :Returns:

            A :class:`py:namedtuple` containing the following named elements:

            * `instances` (list of :class:`~pywbem.CIMInstance`):
              Representations of the initial set of enumerated instances.
            * `eos` (:class:`py:bool`):
              Indicates whether the enumeration session is exhausted
              after returning the initial set of enumerated instances.

              - If `True`, the enumeration session is exhausted, and the
                server has closed the enumeration session.
              - If `False`, the enumeration session is not exhausted.

            * `context` (tuple of (server_context, namespace)):
               Identifies the opened enumeration session. The client must
               provide this value for subsequent operations on this
               enumeration session. The tuple items are:

               - server_context (:term:`string`):
                 Enumeration context string returned by the server if
                 the session is not exhausted, or `None` otherwise. This string
                 is opaque for the client.
               - namespace (:term:`string`):
                 Name of the CIM namespace that was used for this operation.

               NOTE: This inner tuple hides the need for a CIM namespace
               on subsequent operations in the enumeration session. CIM
               operations always require target namespace, but it never
               makes sense to specify a different one in subsequent
               operations on the same enumeration session.

        Keyword Arguments:

          extra :
            Additional keyword arguments are passed as additional operation
            parameters to the WBEM server.
            Note that :term:`DSP0200` does not define any additional parameters
            for this operation.

        :Exceptions:

            See the list of exceptions described in `WBEMConnection`.
        """
        namespace = context[1]

        result = self._imethodcall(
            'PullInstancesWithPath',
            namespace=namespace,
            EnumerationContext=context[0],
            MaxObjectCount=MaxObjectCount,
            response_params_rqd=True,
            **extra)

        return pull_inst_result_tuple(*self._get_rslt_params(result, namespace))


    def PullInstancePaths(self, context, MaxObjectCount=None, **extra):
        # pylint: disable=invalid-name

        """
        Retrieve the next set of instance paths from an open enumeraton
        session defined by the `enumeration_context` parameter.

        This method performs the PullInstanceWithPath operation
        (see :term:`DSP0200`).

        If the operation succeeds, this method returns enumeration session
        status and optionally instance paths.
        Otherwise, this method raises an exception.

        :Parameters:
          context (:term:`string`)
            Identifies the enumeraton session, including its current
            enumeration state. This must be the value of the `context`
            item in the :class:`py:namedtuple` returned from the previous
            open or pull operation for this enumeration.

            The tuple items are:

            - server_context (:term:`string`):
              Enumeration context string returned by the server. This
              string is opaque for the client.
            - namespace (:term:`string`):
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

        :Returns:

            A :class:`py:namedtuple` containing the following named elements:

            * `paths` (list of :class:`~pywbem.CIMInstanceName`):
              Representations of the initial set of enumerated instance paths.
            * `eos` (:class:`py:bool`):
              Indicates whether the enumeration session is exhausted
              after returning the initial set of enumerated instances.

              - If `True`, the enumeration session is exhausted, and the
                server has closed the enumeration session.
              - If `False`, the enumeration session is not exhausted.

            * `context` (tuple of (server_context, namespace)):
               Identifies the opened enumeration session. The client must
               provide this value for subsequent operations on this
               enumeration session. The tuple items are:

               - server_context (:term:`string`):
                 Enumeration context string returned by the server if
                 the session is not exhausted, or `None` otherwise. This string
                 is opaque for the client.
               - namespace (:term:`string`):
                 Name of the CIM namespace that was used for this operation.

               NOTE: This inner tuple hides the need for a CIM namespace
               on subsequent operations in the enumeration session. CIM
               operations always require target namespace, but it never
               makes sense to specify a different one in subsequent
               operations on the same enumeration session.

        Keyword Arguments:

          extra :
            Additional keyword arguments are passed as additional operation
            parameters to the WBEM server.
            Note that :term:`DSP0200` does not define any additional parameters
            for this operation.

        :Exceptions:

            See the list of exceptions described in `WBEMConnection`.
        """
        namespace = context[1]

        result = self._imethodcall(
            'PullInstancePaths',
            namespace=namespace,
            EnumerationContext=context[0],
            MaxObjectCount=MaxObjectCount,
            response_params_rqd=True,
            **extra)

        return pull_path_result_tuple(*self._get_rslt_params(result, namespace))


    def PullInstances(self, context, MaxObjectCount=None, \
                          **extra):
        # pylint: disable=invalid-name

        """
        Retrieve the next set of instances from an open enumeraton
        session defined by the `enumeration_context` parameter.

        This method performs the PullInstanceWithPath operation
        (see :term:`DSP0200`).

        If the operation succeeds, this method returns enumeration session
        status and optionally instances.
        Otherwise, this method raises an exception.

        :Parameters:
          context (:term:`string`)
            Identifies the enumeraton session, including its current
            enumeration state. This must be the value of the `context`
            item in the :class:`py:namedtuple` returned from the previous
            open or pull operation for this enumeration.

            The tuple items are:

            - server_context (:term:`string`):
              Enumeration context string returned by the server. This
              string is opaque for the client.
            - namespace (:term:`string`):
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

        :Returns:

            A :class:`py:namedtuple` containing the following named elements:

            * `instances` (list of :class:`~pywbem.CIMInstance`):
              Representations of the initial set of enumerated instances.
            * `eos` (:class:`py:bool`):
              Indicates whether the enumeration session is exhausted
              after returning the initial set of enumerated instances.

              - If `True`, the enumeration session is exhausted, and the
                server has closed the enumeration session.
              - If `False`, the enumeration session is not exhausted.

            * `context` (tuple of (server_context, namespace)):
               Identifies the opened enumeration session. The client must
               provide this value for subsequent operations on this
               enumeration session. The tuple items are:

               - server_context (:term:`string`):
                 Enumeration context string returned by the server if
                 the session is not exhausted, or `None` otherwise. This string
                 is opaque for the client.
               - namespace (:term:`string`):
                 Name of the CIM namespace that was used for this operation.

               NOTE: This inner tuple hides the need for a CIM namespace
               on subsequent operations in the enumeration session. CIM
               operations always require target namespace, but it never
               makes sense to specify a different one in subsequent
               operations on the same enumeration session.

        Keyword Arguments:

          extra :
            Additional keyword arguments are passed as additional operation
            parameters to the WBEM server.
            Note that :term:`DSP0200` does not define any additional parameters
            for this operation.

        :Exceptions:

            See the list of exceptions described in `WBEMConnection`.
        """
        namespace = context[1]

        result = self._imethodcall(
            'PullInstances',
            namespace=namespace,
            EnumerationContext=context[0],
            MaxObjectCount=MaxObjectCount,
            response_params_rqd=True,
            **extra)

        return pull_inst_result_tuple(*self._get_rslt_params(result, namespace))


    def CloseEnumeration(self, context, **extra):
        # pylint: disable=invalid-name
        """
        The CloseEnumeration closes an open enumeration session, performing
        an early termination of an incomplete enumeration session.

        This method performs the CloseEnumeration operation
        (see :term:`DSP0200`).

        This method should not used if the enumeration session has
        terminated and will result in an exception response.

        If the operation succeeds, this method returns. Otherwise, it
        raises an exception.

        :Parameters:

          context (:term: `string`)
            The `enumeration_context` paramater must contain the
            `Context` value returned by the WBEM server with the
            response to the previous open or pull operation for this
            enumeration sequence.

        Raises:

            Exceptions described in :class:`~pywbem.WBEMConnection`.
        """

        self._imethodcall(
            'CloseEnumeration',
            namespace=context[1],
            EnumerationContext=context[0],
            **extra)

    def GetInstance(self, InstanceName, LocalOnly=None, IncludeQualifiers=None,
                    IncludeClassOrigin=None, PropertyList=None, **extra):
        # pylint: disable=invalid-name,line-too-long
        """
        Retrieve an instance.

        This method performs the GetInstance operation
        (see :term:`DSP0200`).
        If the operation succeeds, this method returns.
        Otherwise, this method raises an exception.

        Parameters:

          InstanceName (CIMInstanceName): Instance path of the instance to be
            retrieved.

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

          PropertyList (:term:`py:iterable` of :term:`string`):
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

        namespace = self._iparam_namespace_from_objectname(InstanceName)
        instancename = self._iparam_instancename(InstanceName)

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

        return instance

    def ModifyInstance(self, ModifiedInstance, IncludeQualifiers=None,
                       PropertyList=None, **extra):
        # pylint: disable=invalid-name,line-too-long
        """
        Modify the property values of an instance.

        This method performs the ModifyInstance operation
        (see :term:`DSP0200`).
        If the operation succeeds, this method returns.
        Otherwise, this method raises an exception.

        Parameters:

          ModifiedInstance (CIMInstance):
            A representation of the modified instance, also indicating its
            instance path.

            The `path` instance variable of this object identifies the instance
            to be modified. Its keybindings component is required. If its
            namespace component is `None`, the default namespace of the
            connection will be used. Its host component will be ignored.

            The `classname` component of the path and the `classname` attribute
            of the instance must specify the same class name.

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

          PropertyList (:term:`py:iterable` of :term:`string`):
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
        if ModifiedInstance.path.classname is None:
            raise ValueError(
                'ModifiedInstance parameter must have classname set in path')
        if ModifiedInstance.classname is None:
            raise ValueError(
                'ModifiedInstance parameter must have classname set in ' \
                'instance')

        namespace = self._iparam_namespace_from_objectname(ModifiedInstance.path)

        # Strip off host and namespace to avoid producing an INSTANCEPATH or
        # LOCALINSTANCEPATH element instead of the desired INSTANCENAME element.
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

    def CreateInstance(self, NewInstance, namespace=None, **extra):
        # pylint: disable=invalid-name
        """
        Create an instance in a namespace.

        This method performs the CreateInstance operation
        (see :term:`DSP0200`).
        If the operation succeeds, this method returns.
        Otherwise, this method raises an exception.

        The creation class for the new instance is taken from the `classname`
        instance variable of the `NewInstance` parameter.

        The namespace for the new instance is taken from these sources, in
        decreasing order of priority:

          * `namespace` parameter of this method, if not `None`,
          * namespace in `path` attribute of the `NewInstance` parameter, if
            not `None`,
          * default namespace of the connection.

        Parameters:

          NewInstance (CIMInstance):
            A representation of the instance to be created.

            The `classname` instance variable of this object specifies the
            creation class for the new instance.

            Apart from utilizing its namespace, the `path` instance variable
            is ignored.

            The `properties` instance variable of this object specifies initial
            property values for the new instance.

            Instance-level qualifiers have been deprecated in CIM, so any
            qualifier values specified using the `qualifiers` instance variable
            of this object will be ignored.

          namespace (:term:`string`):
            Name of the CIM namespace to be used, in any lexical case.

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

        if namespace is None and NewInstance.path.namespace is not None:
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
        instancename.namespace = namespace  # TODO: Why not accept returned ns?

        return instancename

    def DeleteInstance(self, InstanceName, **extra):
        # pylint: disable=invalid-name
        """
        Delete an instance.

        This method performs the DeleteInstance operation
        (see :term:`DSP0200`).
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

        namespace = self._iparam_namespace_from_objectname(InstanceName)
        instancename = self._iparam_instancename(InstanceName)

        self._imethodcall(
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
        Retrieve the instance paths of the instances associated to a source
        instance.

        Retrieve the class paths of the classes associated to a source class.

        This method performs the AssociatorNames operation
        (see :term:`DSP0200`).
        If the operation succeeds, this method returns.
        Otherwise, this method raises an exception.

        Parameters:

          ObjectName:
            For instance level usage: The instance path of the source instance,
            as a :class:`~pywbem.CIMInstanceName` object. If that object does
            not specify a namespace, the default namespace of the connection is
            used.

            For class level usage: The class path of the source class, as a
            :term:`string` or :class:`~pywbem.CIMClassName` object.
            If specified as a string, the string is interpreted as a class name
            in the default namespace of the connection, and can have any
            lexical case.
            If specified as a :class:`~pywbem.CIMClassName` object that does
            not specify a namespace, the default namespace of the connection is
            used.

          AssocClass (:term:`string` or :class:`~pywbem.CIMClassName`):
            Class name of an association class, in any lexical case,
            to filter the result to include only traversals of that association
            class (or subclasses).

            `None` means that no such filtering is peformed.

          ResultClass (:term:`string` or :class:`~pywbem.CIMClassName`):
            Class name of an associated class, in any lexical case,
            to filter the result to include only traversals to that associated
            class (or subclasses).

            `None` means that no such filtering is peformed.

          Role (:term:`string`):
            Role name (= property name) of the source end, in any
            lexical case, to filter the result to include only traversals from
            that source role.

            `None` means that no such filtering is peformed.

          ResultRole (:term:`string`):
            Role name (= property name) of the far end, in any
            lexical case, to filter the result to include only traversals to
            that far role.

            `None` means that no such filtering is peformed.

        Keyword Arguments:

          extra :
            Additional keyword arguments are passed as additional operation
            parameters to the WBEM server.
            Note that :term:`DSP0200` does not define any additional parameters
            for this operation.

        Returns:

            Return data depends on `ObjectName` parameter:

            **Instance level usage:** A list of
            :class:`~pywbem.CIMInstanceName` objects that are the instance
            paths of the associated instances.

            **Class level usage:** A list of :class:`~pywbem.CIMClassName`
            objects that are the class paths of the associated classes.

        Raises:

            Exceptions described in :class:`~pywbem.WBEMConnection`.
        """

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
            return []

        return [x[2] for x in result[0][2]]

    def Associators(self, ObjectName, AssocClass=None, ResultClass=None,
                    Role=None, ResultRole=None, IncludeQualifiers=None,
                    IncludeClassOrigin=None, PropertyList=None, **extra):
        # pylint: disable=invalid-name, line-too-long
        """
        Retrieve the instances associated to a source instance.

        Retrieve the classes associated to a source class.

        This method performs the Associators operation
        (see :term:`DSP0200`).
        If the operation succeeds, this method returns.
        Otherwise, this method raises an exception.

        Parameters:

          ObjectName:
            For instance level usage: The instance path of the source instance,
            as a :class:`~pywbem.CIMInstanceName` object. If that object does
            not specify a namespace, the default namespace of the connection is
            used.

            For class level usage: The class path of the source class, as a
            :term:`string` or :class:`~pywbem.CIMClassName` object.
            If specified as a string, the string is interpreted as a class name
            in the default namespace of the connection, and can have any
            lexical case.
            If specified as a :class:`~pywbem.CIMClassName` object, its
            `namespace` attribute is used; if that is `None`, the default
            namespace of the connection is used.

          AssocClass (:term:`string` or :class:`~pywbem.CIMClassName`):
            Class name of an association class, in any lexical case,
            to filter the result to include only traversals of that association
            class (or subclasses).

            `None` means that no such filtering is peformed.

          ResultClass (:term:`string` or :class:`~pywbem.CIMClassName`):
            Class name of an associated class, in any lexical case,
            to filter the result to include only traversals to that associated
            class (or subclasses).

            `None` means that no such filtering is peformed.

          Role (:term:`string`):
            Role name (= property name) of the source end, in any
            lexical case, to filter the result to include only traversals from
            that source role.

            `None` means that no such filtering is peformed.

          ResultRole (:term:`string`):
            Role name (= property name) of the far end, in any
            lexical case, to filter the result to include only traversals to
            that far role.

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

            Return structure depends on whether class or instance
            is provided in the `ObjectName` parameter.

            * **Instance level usage**: A list of
                :class:`~pywbem.CIMInstance` objects that are representations
                of the associated instances.

            * **Class level usage**: `[(classname, class),...]`, a list of
              tuples where each tuple contains:

               *  **classname** (:class:`~pywbem.CIMClassName`): Host
                  and namespace entities that are the representation of the
                  name of the associated class.
               *  **class** (:class:`~pywbem.CIMInstance`): The
                  representation of the corresponding associated class

        Raises:

            Exceptions described in :class:`~pywbem.WBEMConnection`.
        """

        namespace = self._iparam_namespace_from_objectname(ObjectName)
        objectname = self._iparam_objectname(ObjectName)

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
            return []

        return [x[2] for x in result[0][2]]

    def ReferenceNames(self, ObjectName, ResultClass=None, Role=None, **extra):
        # pylint: disable=invalid-name, line-too-long
        """
        Retrieve the instance paths of the association instances that reference
        a source instance.

        Retrieve the class paths of the association classes that reference a
        source class.

        This method performs the ReferenceNames operation
        (see :term:`DSP0200`).
        If the operation succeeds, this method returns.
        Otherwise, this method raises an exception.

        Parameters:

          ObjectName:
            For instance level usage: The instance path of the source instance,
            as a :class:`~pywbem.CIMInstanceName` object. If that object does
            not specify a namespace, the default namespace of the connection is
            used.

            For class level usage: The class path of the source class, as a
            :term:`string` or :class:`~pywbem.CIMClassName`
            object.
            If specified as a string, the string is interpreted as a class name
            in the default namespace of the connection, and can have any
            lexical case.
            If specified as a :class:`~pywbem.CIMClassName` object, its
            `namespace` attribute is used; if that is `None`, the default
            namespace of the connection is used.

          ResultClass (:term:`string` or :class:`~pywbem.CIMClassName`):
            Class name of an association class, in any lexical case,
            to filter the result to include only traversals of that association
            class (or subclasses).

            `None` means that no such filtering is peformed.

          Role (:term:`string`):
            Role name (= property name) of the source end, in any
            lexical case, to filter the result to include only traversals from
            that source role.

            `None` means that no such filtering is peformed.

        Keyword Arguments:

          extra :
            Additional keyword arguments are passed as additional operation
            parameters to the WBEM server.
            Note that :term:`DSP0200` does not define any additional parameters
            for this operation.

        Returns:

            Return data depends on `ObjectName` parameter:

            **Instance level usage**: A list of
            :class:`~pywbem.CIMInstanceName` objects that are the instance
            paths of the referencing association instances.

            **Class level usage:** A list of :class:`~pywbem.CIMClassName`
            objects that are the class paths of the referencing association
            classes.

        Raises:

            Exceptions described in :class:`~pywbem.WBEMConnection`.
        """

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
            return []

        return [x[2] for x in result[0][2]]

    def References(self, ObjectName, ResultClass=None, Role=None,
                   IncludeQualifiers=None, IncludeClassOrigin=None,
                   PropertyList=None, **extra):
        # pylint: disable=invalid-name, line-too-long
        """
        Retrieve the association instances that reference a source instance.

        Retrieve the association classes that reference a source class.

        This method performs the References operation
        (see :term:`DSP0200`).
        If the operation succeeds, this method returns.
        Otherwise, this method raises an exception.

        Parameters:

          ObjectName:
            For instance level usage: The instance path of the source instance,
            as a :class:`~pywbem.CIMInstanceName` object. If that object does
            not specify a namespace, the default namespace of the connection is
            used.

            For class level usage: The class path of the source class, as a
            :term:`string` or :class:`~pywbem.CIMClassName`
            object.
            If specified as a string, the string is interpreted as a class name
            in the default namespace of the connection, and can have any
            lexical case.
            If specified as a :class:`~pywbem.CIMClassName` object, its
            `namespace` attribute is used; if that is `None`, the default
            namespace of the connection is used.

          ResultClass (:term:`string` or :class:`~pywbem.CIMClassName`):
            Class name of an association class, in any lexical case,
            to filter the result to include only traversals of that association
            class (or subclasses).

            `None` means that no such filtering is peformed.

          Role (:term:`string`):
            Role name (= property name) of the source end, in any
            lexical case, to filter the result to include only traversals from
            that source role.

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

            This parameter has been deprecated in :term:`DSP0200`. Clients cannot
            rely on it being implemented by WBEM servers.

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

            Return structure depends on whether class or instance
            is provided in the `ObjectName` parameter.

            * **Instance level usage**: A list of
                :class:`~pywbem.CIMInstance` objects that are representations
                of the associated instances.

            * **Class level usage**: `[(classname, class),..]`, a list of
              tuples where each tuple contains:

               *  **classname** (:class:`~pywbem.CIMClassName`): Host
                  and namespace entities that are the representation of the
                  name of the associated class.
               *  **class** (:class:`~pywbem.CIMInstance`): The
                  representation of the corresponding associated class

        Raises:

            Exceptions described in :class:`~pywbem.WBEMConnection`.
        """

        namespace = self._iparam_namespace_from_objectname(ObjectName)
        objectname = self._iparam_objectname(ObjectName)

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
            return []

        return [x[2] for x in result[0][2]]

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
        (see :term:`DSP0200`).
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
            Name of the method to be invoked (without parenthesis or any
            parameter signature), in any lexical case.

          ObjectName:
            For instance level usage: The instance path of the target instance,
            as a :class:`~pywbem.CIMInstanceName` object. If that object does
            not specify a namespace, the default namespace of the connection is
            used.

            For class level usage: The class path of the target class, as a
            :term:`string` or
            :class:`~pywbem.CIMClassName` object.
            If specified as a string, the string is interpreted as a class name
            in the default namespace of the connection, and can have any
            lexical case.
            If specified as a :class:`~pywbem.CIMClassName` object, its
            `namespace` attribute is used; if that is `None`, the default
            namespace of the connection is used.

          Params (:term:`py:iterable` of tuples of name,value):
            An iterable of input parameters for the CIM method.

            Each iterated item represents a single input parameter for the CIM
            method and must be a `tuple(name, value)`, with:

            * name (:term:`string`):
              Parameter name, in any lexical case
            * value (:term:`CIM data type`):
              Parameter value

        Keyword Arguments:

          : Each keyword parameter represents a single input parameter for the
            CIM method, with:

            * key (:term:`string`):
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
                  Parameter name, preserving its lexical case
                * value (:term:`CIM data type`):
                  Parameter value

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

        return returnvalue, output_params

    #
    # Query operations
    #

    def ExecQuery(self, QueryLanguage, Query, namespace=None, **extra):
        # pylint: disable=invalid-name
        """
        Execute a query in a namespace.

        This method performs the ExecQuery operation
        (see :term:`DSP0200`).
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
        (see :term:`DSP0200`).
        If the operation succeeds, this method returns.
        Otherwise, this method raises an exception.

        Parameters:

          namespace (:term:`string`):
            Name of the namespace in which the class names are to be
            enumerated, in any lexical case.

            If `None`, the namespace of the `ClassName` parameter will be used,
            if specified as a :class:`~pywbem.CIMClassName` object. If that is
            also `None`, the default namespace of the connection will be used.

          ClassName (:term:`string` or :class:`~pywbem.CIMClassName`):
            Name of the class whose subclasses are to be retrieved, in any
            lexical case.
            If specified as a :class:`~pywbem.CIMClassName` object, its host
            component will be ignored.

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
            return []
        else:
            return [x.classname for x in result[0][2]]

    def EnumerateClasses(self, namespace=None, ClassName=None,
                         DeepInheritance=None, LocalOnly=None,
                         IncludeQualifiers=None, IncludeClassOrigin=None,
                         **extra):
        # pylint: disable=invalid-name,line-too-long
        """
        Enumerate the subclasses of a class, or the top-level classes in a
        namespace.

        This method performs the EnumerateClasses operation
        (see :term:`DSP0200`).
        If the operation succeeds, this method returns.
        Otherwise, this method raises an exception.

        Parameters:

          namespace (:term:`string`):
            Name of the namespace in which the classes are to be enumerated, in
            any lexical case.

            If `None`, the namespace of the `ClassName` parameter will be used,
            if specified as a :class:`~pywbem.CIMClassName` object. If that is
            also `None`, the default namespace of the connection will be used.

          ClassName (:term:`string` or :class:`~pywbem.CIMClassName`):
            Name of the class whose subclasses are to be retrieved, in any
            lexical case.
            If specified as a :class:`~pywbem.CIMClassName` object, its host
            component will be ignored.

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
            return []

        return result[0][2]

    def GetClass(self, ClassName, namespace=None, LocalOnly=None,
                 IncludeQualifiers=None, IncludeClassOrigin=None,
                 PropertyList=None, **extra):
        # pylint: disable=invalid-name, line-too-long
        """
        Retrieve a class.

        This method performs the GetClass operation
        (see :term:`DSP0200`).
        If the operation succeeds, this method returns.
        Otherwise, this method raises an exception.

        Parameters:

          ClassName (:term:`string` or :class:`~pywbem.CIMClassName`):
            Name of the class to be retrieved, in any lexical case.
            If specified as a :class:`~pywbem.CIMClassName` object, its host
            component will be ignored.

          namespace (:term:`string`):
            Name of the namespace of the class to be retrieved, in any lexical
            case.

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

          PropertyList (:term:`py:iterable` of :term:`string`):
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

        if namespace is None and isinstance(ClassName, CIMClassName):
            namespace = ClassName.namespace
        namespace = self._iparam_namespace_from_namespace(namespace)
        classname = self._iparam_classname(ClassName)

        result = self._imethodcall(
            'GetClass',
            namespace,
            ClassName=classname,
            LocalOnly=LocalOnly,
            IncludeQualifiers=IncludeQualifiers,
            IncludeClassOrigin=IncludeClassOrigin,
            PropertyList=PropertyList,
            **extra)

        return result[0][2][0]

    def ModifyClass(self, ModifiedClass, namespace=None, **extra):
        # pylint: disable=invalid-name
        """
        Modify a class in a namespace.

        This method performs the ModifyClass operation
        (see :term:`DSP0200`).
        If the operation succeeds, this method returns.
        Otherwise, this method raises an exception.

        Parameters:

          ModifiedClass (CIMClass):
            A representation of the modified class.

            The properties, methods and qualifiers defined in this object
            specify what is to be modified.

            Typically, this object has been retrieved by other operations, such
            as :meth:`~pywbem.WBEMConnection.GetClass`.

          namespace (:term:`string`):
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

        namespace = self._iparam_namespace_from_namespace(namespace)

        klass = ModifiedClass.copy()
        klass.path = None

        self._imethodcall(
            'ModifyClass',
            namespace,
            ModifiedClass=klass,
            **extra)

    def CreateClass(self, NewClass, namespace=None, **extra):
        # pylint: disable=invalid-name
        """
        Create a class in a namespace.

        This method performs the CreateClass operation
        (see :term:`DSP0200`).
        If the operation succeeds, this method returns.
        Otherwise, this method raises an exception.

        Parameters:

          NewClass (CIMClass):
            A representation of the class to be created.

            The properties, methods and qualifiers defined in this object
            specify how the class is to be created.

          namespace (:term:`string`):
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

        namespace = self._iparam_namespace_from_namespace(namespace)

        klass = NewClass.copy()
        klass.path = None

        self._imethodcall(
            'CreateClass',
            namespace,
            NewClass=klass,
            **extra)

    def DeleteClass(self, ClassName, namespace=None, **extra):
        # pylint: disable=invalid-name,line-too-long
        """
        Delete a class.

        This method performs the DeleteClass operation
        (see :term:`DSP0200`).
        If the operation succeeds, this method returns.
        Otherwise, this method raises an exception.

        Parameters:

          ClassName (:term:`string` or :class:`~pywbem.CIMClassName`):
            Name of the class to be deleted, in any lexical case.
            If specified as a :class:`~pywbem.CIMClassName` object, its host
            component will be ignored.

          namespace (:term:`string`):
            Name of the namespace of the class to be deleted, in any lexical
            case.

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

        if namespace is None and isinstance(ClassName, CIMClassName):
            namespace = ClassName.namespace
        namespace = self._iparam_namespace_from_namespace(namespace)
        classname = self._iparam_classname(ClassName)

        self._imethodcall(
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
        Enumerate qualifier declarations in a namespace.

        This method performs the EnumerateQualifiers operation
        (see :term:`DSP0200`).
        If the operation succeeds, this method returns.
        Otherwise, this method raises an exception.

        Parameters:

          namespace (:term:`string`):
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

        namespace = self._iparam_namespace_from_namespace(namespace)

        result = self._imethodcall(
            'EnumerateQualifiers',
            namespace,
            **extra)

        if result is not None:
            qualifiers = result[0][2]
        else:
            qualifiers = []

        return qualifiers

    def GetQualifier(self, QualifierName, namespace=None, **extra):
        # pylint: disable=invalid-name
        """
        Retrieve a qualifier declaration in a namespace.

        This method performs the GetQualifier operation
        (see :term:`DSP0200`).
        If the operation succeeds, this method returns.
        Otherwise, this method raises an exception.

        Parameters:

          Qualifier (:term:`string`):
            Name of the qualifier declaration to be retrieved, in any lexical
            case.

          namespace (:term:`string`):
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

        namespace = self._iparam_namespace_from_namespace(namespace)

        result = self._imethodcall(
            'GetQualifier',
            namespace,
            QualifierName=QualifierName,
            **extra)

        if result is not None:
            names = result[0][2][0]

        return names

    def SetQualifier(self, QualifierDeclaration, namespace=None, **extra):
        # pylint: disable=invalid-name
        """
        Create or modify a qualifier declaration in a namespace.

        This method performs the SetQualifier operation
        (see :term:`DSP0200`).
        If the operation succeeds, this method returns.
        Otherwise, this method raises an exception.

        Parameters:

          QualifierDeclaration (CIMQualifierDeclaration):
            Representation of the qualifier declaration to be created or
            modified.

          namespace (:term:`string`):
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

        namespace = self._iparam_namespace_from_namespace(namespace)

        unused_result = self._imethodcall(
            'SetQualifier',
            namespace,
            QualifierDeclaration=QualifierDeclaration,
            **extra)

    def DeleteQualifier(self, QualifierName, namespace=None, **extra):
        # pylint: disable=invalid-name
        """
        Delete a qualifier declaration in a namespace.

        This method performs the DeleteQualifier operation
        (see :term:`DSP0200`).
        If the operation succeeds, this method returns.
        Otherwise, this method raises an exception.

        Parameters:

          Qualifier (:term:`string`):
            Name of the qualifier declaration to be deleted, in any lexical
            case.

          namespace (:term:`string`):
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

        namespace = self._iparam_namespace_from_namespace(namespace)

        unused_result = self._imethodcall(
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

      ns (:term:`string`):
        Namespace, in any lexical case.

      super_class (:term:`string`):
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
