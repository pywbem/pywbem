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
:meth:`~pywbem.WBEMConnection.EnumerateInstances`           Enumerate the instances of a class (including instances of its
                                                            subclasses)
:meth:`~pywbem.WBEMConnection.EnumerateInstanceNames`       Enumerate the instance paths of instances of a class
                                                            (including instances of its subclasses).
:meth:`~pywbem.WBEMConnection.GetInstance`                  Retrieve an instance
:meth:`~pywbem.WBEMConnection.ModifyInstance`               Modify the property values of an instance
:meth:`~pywbem.WBEMConnection.CreateInstance`               Create an instance
:meth:`~pywbem.WBEMConnection.DeleteInstance`               Delete an instance
:meth:`~pywbem.WBEMConnection.Associators`                  Retrieve the instances (or classes) associated to a source
                                                            instance (or source class)
:meth:`~pywbem.WBEMConnection.AssociatorNames`              Retrieve the instance paths of the instances (or classes)
                                                            associated to a source instance (or source class)
:meth:`~pywbem.WBEMConnection.References`                   Retrieve the association instances (or association classes)
                                                            that reference a source instance (or source class)
:meth:`~pywbem.WBEMConnection.ReferenceNames`               Retrieve the instance paths of the association instances (or
                                                            association classes) that reference a source instance (or
                                                            source class)
:meth:`~pywbem.WBEMConnection.InvokeMethod`                 Invoke a method on a target instance or on a target class
:meth:`~pywbem.WBEMConnection.ExecQuery`                    Execute a query in a namespace
----------------------------------------------------------  --------------------------------------------------------------
:meth:`~pywbem.WBEMConnection.IterEnumerateInstances`       Iterator API that uses either OpenEnumerateInstances and
                                                            PullInstancesWithPath or EnumerateInstances depending on
                                                            the attributes and existence of pull operations in the
                                                            server.
:meth:`~pywbem.WBEMConnection.IterEnumerateInstancePaths`   Iterator API that uses either OpenEnumerateInstances and
                                                            PullInstancesWithPath or EnumerateInstances depending on
                                                            the attributes and existence of pull operations in the
                                                            server.
:meth:`~pywbem.WBEMConnection.IterAssociatorInstances`      Iterator API that uses either OpenAssociatorInstances and
                                                            PullInstancesWithPath or Associators depending on
                                                            the attributes and existence of pull operations in the
                                                            server.
:meth:`~pywbem.WBEMConnection.IterAssociatorInstancePaths`  Iterator API that uses either OpenAssociatorInstances and
                                                            PullInstancesWithPath or Associators depending on
                                                            the attributes and existence of pull operations in the
                                                            server.
:meth:`~pywbem.WBEMConnection.IterReferenceInstances`       Iterator API that uses either OpenReferenceInstances and
                                                            PullInstancesWithPath or References depending on
                                                            the attributes and existence of pull operations in the
                                                            server.
:meth:`~pywbem.WBEMConnection.IterReferenceInstancePaths`   Iterator API that uses either OpenReferenceInstances and
                                                            PullInstancesWithPath or References depending on
                                                            the attributes and existence of pull operations in the
                                                            server.
:meth:`~pywbem.WBEMConnection.IterQueryInstances`           Iterator API that uses either OpenQueryInstances and
                                                            PullInstances or ExecQuery depending on
                                                            the attributes and existence of pull operations in the
                                                            server.
----------------------------------------------------------  --------------------------------------------------------------
:meth:`~pywbem.WBEMConnection.OpenEnumerateInstances`       Open enumeration session to retrieve instances of
                                                            of a class (including instances of its subclass)
:meth:`~pywbem.WBEMConnection.OpenEnumerateInstancePaths`   Open enumeration session to retrieve instances of a class
                                                            (including instances of its subclass)
:meth:`~pywbem.WBEMConnection.OpenAssociatorInstances`      Open enumeration session to retrieve the instances
                                                            associated to a source instance
:meth:`~pywbem.WBEMConnection.OpenAssociatorInstancePaths`  Open enumeration session to retrieve the instances
                                                            associated to a source instance
:meth:`~pywbem.WBEMConnection.OpenReferenceInstances`       Open enumeration session to retrieve the instances
                                                            that reference a source instance
:meth:`~pywbem.WBEMConnection.OpenReferenceInstancePaths`   Open enumeration session to retrieve the instances that
                                                            reference a source instance
:meth:`~pywbem.WBEMConnection.OpenQueryInstances`           Open query request to retrieve instances defined by
                                                            the query parameter in a namespace
:meth:`~pywbem.WBEMConnection.PullInstancesWithPath`        Continue enumeration session opened with
                                                            OpenEnumerateInstances, OpenAssociatorInstances, or
                                                            OpenReferenceinstances
:meth:`~pywbem.WBEMConnection.PullInstancePaths`            Continue enumeration session opened with
                                                            OpenEnumerateInstancePaths, OpenAssociatorInstancePaths,
                                                            or OpenReferenceInstancePaths
:meth:`~pywbem.WBEMConnection.PullInstances`                Continue enumeration of enumeration session opened
                                                            with OpenExecQuery
:meth:`~pywbem.WBEMConnection.CloseEnumeration`             Close an enumeration session in process.
----------------------------------------------------------  --------------------------------------------------------------
:meth:`~pywbem.WBEMConnection.EnumerateClasses`             Enumerate the subclasses of a class, or the top-level classes
                                                            in a namespace
:meth:`~pywbem.WBEMConnection.EnumerateClassNames`          Enumerate the names of subclasses of a class, or of the
                                                            top-level classes in a namespace
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
and has not been implemented by any WBEM servers so was not implemented
in pywbem.
"""  # noqa: E501
# pylint: enable=line-too-long
# Note: When used before module docstrings, Pylint scopes the disable statement
#       to the whole rest of the file, so we need an enable statement.

# This module is meant to be safe for 'import *'.

from __future__ import absolute_import

import os
import re
from datetime import datetime, timedelta
from xml.dom import minidom
import warnings
from collections import namedtuple
import logging

import six

from . import cim_xml
from .config import DEFAULT_ITER_MAXOBJECTCOUNT, AUTO_GENERATE_SFCB_UEP_HEADER
from .cim_constants import DEFAULT_NAMESPACE, CIM_ERR_NOT_SUPPORTED
from .cim_types import CIMType, CIMDateTime, atomic_to_cim_xml
from ._nocasedict import NocaseDict
from .cim_obj import CIMInstance, CIMInstanceName, CIMClass, CIMClassName, \
    CIMParameter, CIMQualifierDeclaration, tocimxml, cimvalue
from .cim_http import get_cimobject_header, wbem_request
from .tupleparse import TupleParser
from .tupletree import xml_to_tupletree_sax
from .cim_http import parse_url
from .exceptions import CIMXMLParseError, XMLParseError, CIMError
from ._statistics import Statistics
from ._recorder import LogOperationRecorder
from ._logging import DEFAULT_LOG_DETAIL_LEVEL, LOG_DESTINATIONS, \
    LOGGER_API_CALLS_NAME, LOGGER_HTTP_NAME, LOG_DETAIL_LEVELS, \
    LOGGER_SIMPLE_NAMES
from ._utils import _ensure_unicode, _format

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
        raise ValueError(
            _format("string expected for classname, not {0!A}", val))


def _iparam_propertylist(property_list):
    """Validate property_list and if it is not iterable convert to list.

    This is a test for a particular issue where the user supplies a single
    string instead of a list for a PropertyList parameter. It prevents
    an XML error.
    """
    return [property_list] if isinstance(property_list, six.string_types) \
        else property_list


def _validateIterCommonParams(MaxObjectCount, OperationTimeout):
    """
    Validate common parameters for an iter... operation.

    MaxObjectCount must be a positive non-zero integer or None.

    OperationTimeout must be positive integer or zero

    Raises:

      ValueError: if these parameters are invalid
    """
    if MaxObjectCount is None or MaxObjectCount <= 0:
        raise ValueError(
            _format("MaxObjectCount must be > 0 but is {0}", MaxObjectCount))

    if OperationTimeout is not None and OperationTimeout < 0:
        raise ValueError(
            _format("OperationTimeout must be >= 0 but is {0}",
                    OperationTimeout))


def _validatePullParams(MaxObjectCount, context):
    """
        Validate the input paramaters for the PullInstances,
        PullInstancesWithPath, and PullInstancePaths requests.

        MaxObjectCount: Must be integer type and ge 0

        context: Must be not None and length ge 2
    """
    if (not isinstance(MaxObjectCount, six.integer_types) or
            MaxObjectCount < 0):
        raise ValueError(
            _format("MaxObjectCount parameter must be integer >= 0 but is "
                    "{0!A}", MaxObjectCount))
    if context is None or len(context) < 2:
        raise ValueError(
            _format("Pull... Context parameter must be valid tuple {0!A}",
                    context))


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
    provided by this class is only conceptual. That is, the creation of the
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

    WBEMConnection objects can record the operations performed by calling
    :class:`~pywbem.WBEMConnection` methods that interact with a WBEM server
    using *operation recorders*, at the level of method calls and returns, and
    at the level of CIM-XML requests and responses.
    The :class:`~pywbem.LogOperationRecorder` class records the operations in
    the Python logging facility. This recorder is activated through the
    `connection` parameter of :func:`~pywbem._logging.configure_logger`.
    The :class:`~pywbem.TestClientRecorder` class records the operations in a
    file in the YAML format suitable for the test_client.py unit test program.
    Before version 0.11.0, pywbem supported only a single operation recorder
    and activating/deactivating the recorder was a simple matter of setting the
    :attr:`~pywbem.WBEMConnection.operation_recorder` attribute.
    Starting with pywbem version 0.11.0, pywbem added support for multiple
    operation recorders and deprecated the
    :attr:`~pywbem.WBEMConnection.operation_recorder` attribute. The
    :meth:`~pywbem.WBEMConnection.add_operation_recorder` method is now used
    to add an operation recorder to a connection, and the
    :attr:`~pywbem.WBEMConnection.operation_recorders` property is used to
    retrieve the current operation recorders of a connection.

    The methods of this class may raise the following exceptions:

    * Exceptions indicating operational errors:

      - :exc:`~pywbem.ConnectionError` - A connection with the WBEM server
        could not be established or broke down.

      - :exc:`~pywbem.AuthError` - Authentication failed with the WBEM server.

      - :exc:`~pywbem.TimeoutError` - The WBEM server did not respond in time
        and the client timed out.

      Such exceptions can typically be resolved by the client user or server
      admin.

    * Exceptions indicating server-side issues:

      - :exc:`~pywbem.HTTPError` - HTTP error (bad status code) received from
        WBEM server.

      - :exc:`~pywbem.CIMXMLParseError` - The response from the WBEM server
        cannot be parsed because it is invalid CIM-XML (for example, a required
        attribute is missing on an XML element).

      - :exc:`~pywbem.XMLParseError` - The response from the WBEM server
        cannot be parsed because it is invalid XML (for example, invalid
        characters or UTF-8 sequences, or ill-formed XML).

      Such exceptions nearly always indicate an issue with the implementation
      of the WBEM server.

    * Other exceptions:

      - :exc:`~pywbem.CIMError` - The WBEM server returned an error response
        with a CIM status code.

      Depending on the nature of the request, and on the CIM status code, the
      reason may be a client user error (e.g. incorrect class name) or
      a server side issue (e.g. some internal error in the server).

    * Exceptions indicating programming errors (in pywbem or by the user):

      - :exc:`~py:exceptions.TypeError`
      - :exc:`~py:exceptions.KeyError`
      - :exc:`~py:exceptions.ValueError`
      - :exc:`~py:exceptions.AttributeError`
      - ... possibly others ...

      Exceptions indicating programming errors should not happen. If you think
      the reason such an exception is raised lies in pywbem,
      `report a bug <https://github.com/pywbem/pywbem/issues>`_.
    """

    # Class level counter. Incremented at each WBEMConnection creation
    # and used as part of WBEMConnection instance ID.
    _conn_counter = 0

    # Detail levels to be used for log operation recorders of any newly created
    # WBEMConnection objects.
    #   Key: Simple logger name (e.g. 'api')
    #   Value: Detail level string from LOG_DETAIL_LEVELS.
    _log_detail_levels = {}

    # If True, logging will be activated for any newly created WBEMConnection
    # objects.
    _activate_logging = False

    def __init__(self, url, creds=None, default_namespace=None,
                 x509=None, verify_callback=None, ca_certs=None,
                 no_verification=False, timeout=None, use_pull_operations=False,
                 stats_enabled=False):
        # pylint: disable=line-too-long
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

          creds (:func:`py:tuple` of userid, password):
            Credentials for HTTP authentication with the WBEM server, as a
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
            Default CIM namespace for this connection.

            Leading and trailing slash characters will be stripped. The lexical
            case will be preserved.

            If `None`, the default namespace of the connection will be set to
            the built-in default namespace |DEFAULT_NAMESPACE|.

            The default namespace of the connection is used if no namespace
            or a namespace of `None` is specified for an operation.

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
            does not need to be used. See
            :ref:`Verification of the X.509 server certificate` for details.

            Warning: This parameter is not used when the python environment
            is Python 3 because the ssl module does not support it.

            If `None`, no such callback function will be registered.

            The specified function will be called for the returned certificate,
            and for each of the certificates in its chain of trust.

            See `M2Crypto.SSL.Context.set_verify` for details, as well as
            https://blog.san-ss.com.ar/2012/05/validating-ssl-certificate-in-python.html):

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

            The parameter value must be one of:

            * a path to a file containing one or more CA certificates in
              PEM format. See the description of `CAfile` in the OpenSSL
              `SSL_CTX_load_verify_locations`_ function for details.

            * a path to a directory with files each of which contains one CA
              certificate in PEM format. See the description of `CApath` in the
              OpenSSL `SSL_CTX_load_verify_locations`_ function for details.

            If `None`, the directory path of the first existing directory from
            the list in :data:`~pywbem.cim_http.DEFAULT_CA_CERT_PATHS` will be
            used as a default.

            .. _`SSL_CTX_load_verify_locations`: https://www.openssl.org/docs/man1.1.0/ssl/SSL_CTX_load_verify_locations.html

          no_verification (:class:`py:bool`):
            Disables verification of the X.509 server certificate returned by
            the WBEM server during TLS/SSL handshake, disables verification of
            the hostname, and disables the invocation of a verification function
            specified in `verify_callback`.

            If `True`, verification is disabled; otherwise, verification is
            enabled.

            This parameter is ignored when HTTP is used.

            Disabling the verification of the server certificate is insecure
            and should be avoided!

          timeout (:term:`number`):
            Timeout in seconds, for requests sent to the server.

            *New in pywbem 0.8.*

            If the server did not respond within the timeout duration, the
            socket for the connection will be closed, causing a
            :exc:`~pywbem.TimeoutError` to be raised.

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
            Controls the use of pull operations in any `Iter...()` methods.

            *New in pywbem 0.11 as experimental and finalized in 0.13.*

            `None` means that the `Iter...()` methods will attempt a pull
            operation first, and if the WBEM server does not support it, will
            use a traditional operation from then on, on this connection.
            This detection is performed for each pull operation separately, in
            order to accomodate WBEM servers that support only some of the pull
            operations. This will work on any WBEM server whether it supports
            no, some, or all pull operations.

            `True` means that the `Iter...()` methods will only use pull
            operations. If the WBEM server does not support pull operations, a
            :exc:`~pywbem.CIMError` with status code `CIM_ERR_NOT_SUPPORTED`
            will be raised.

            `False` (default) means that the `Iter...()` methods will only use
            traditional operations.

          stats_enabled (:class:`py:bool`):
            Initial enablement status for maintaining statistics about the
            WBEM operations executed via this connection.

            *New in pywbem 0.11 as experimental, renamed from `enable_stats`
            and finalized in 0.12.*

            See the :ref:`WBEM operation statistics` section for details.
        """  # noqa: E501
        # pylint: enable=line-too-long

        # Connection attributes
        self._set_url(url)
        self._set_creds(creds)
        self._set_default_namespace(default_namespace)
        self._set_x509(x509)
        self._set_verify_callback(verify_callback)
        self._set_ca_certs(ca_certs)
        self._set_no_verification(no_verification)
        self._set_timeout(timeout)

        # Saving last request and reply
        self._debug = False
        self._last_raw_request = None
        self._last_raw_reply = None
        self._last_request = None
        self._last_reply = None

        # Time statistics
        self._last_request_len = 0
        self._last_reply_len = 0

        # control of operation recorders
        self._operation_recorders = []

        # Create the connection identifier for this WBEMConnection
        # Includes class level counter and process pid
        self.__class__._conn_counter += 1
        self._conn_id = '{0}-{1}'.format(
            self.__class__._conn_counter,  # pylint: disable=protected-access
            os.getpid())

        # Intent to use pull operations
        self._use_pull_operations = use_pull_operations

        # Actual status of using pull operations
        self._use_enum_inst_pull_operations = use_pull_operations
        self._use_enum_path_pull_operations = use_pull_operations
        self._use_ref_inst_pull_operations = use_pull_operations
        self._use_ref_path_pull_operations = use_pull_operations
        self._use_assoc_inst_pull_operations = use_pull_operations
        self._use_assoc_path_pull_operations = use_pull_operations
        self._use_query_pull_operations = use_pull_operations

        self._statistics = Statistics(stats_enabled)
        self._last_operation_time = None
        self._last_server_response_time = None

        if self._activate_logging:
            recorder = LogOperationRecorder(
                conn_id=self.conn_id,
                detail_levels=self._log_detail_levels)
            self.add_operation_recorder(recorder)

    @property
    def url(self):
        """
        :term:`unicode string`: URL of the WBEM server.

        For details, see the description of the same-named init
        parameter of :class:`this class <pywbem.WBEMConnection>`.

        This attribute is settable, but setting it has been deprecated.
        """
        return self._url

    @url.setter
    def url(self, url):
        """Setter method; for a description see the getter method."""
        warnings.warn(
            "Setting the WBEMConnection.url property is deprecated",
            DeprecationWarning, 2)
        self._set_url(url)

    def _set_url(self, url):
        """Internal setter function."""
        self._url = _ensure_unicode(url)

    @property
    def creds(self):
        """
        :func:`py:tuple`: Credentials for HTTP authentication with the WBEM
        server.

        For details, see the description of the same-named init
        parameter of :class:`this class <pywbem.WBEMConnection>`.

        This attribute is settable, but setting it has been deprecated.
        """
        return self._creds

    @creds.setter
    def creds(self, creds):
        """Setter method; for a description see the getter method."""
        warnings.warn(
            "Setting the WBEMConnection.creds property is deprecated",
            DeprecationWarning, 2)
        self._set_creds(creds)

    def _set_creds(self, creds):
        """Internal setter function."""
        self._creds = creds

    @property
    def default_namespace(self):
        """
        :term:`unicode string`: Name of the CIM namespace to be used by default
        (if no namespace is specified for an operation).

        For details, see the description of the same-named init
        parameter of :class:`this class <pywbem.WBEMConnection>`.

        This attribute is settable.
        """
        return self._default_namespace

    @default_namespace.setter
    def default_namespace(self, default_namespace):
        """Setter method; for a description see the getter method."""
        # pylint: disable=attribute-defined-outside-init
        # Note: Setting it is not deprecated.
        self._set_default_namespace(default_namespace)

    def _set_default_namespace(self, default_namespace):
        """Internal setter function."""
        if default_namespace is not None:
            default_namespace = default_namespace.strip('/')
        else:
            default_namespace = DEFAULT_NAMESPACE
        self._default_namespace = _ensure_unicode(default_namespace)

    @property
    def x509(self):
        """
        :class:`py:dict`: :term:`X.509` client certificate and key file to be
        presented to the WBEM server during the TLS/SSL handshake.

        For details, see the description of the same-named init
        parameter of :class:`this class <pywbem.WBEMConnection>`.

        This attribute is settable, but setting it has been deprecated.
        """
        return self._x509

    @x509.setter
    def x509(self, x509):
        """Setter method; for a description see the getter method."""
        warnings.warn(
            "Setting the WBEMConnection.x509 property is deprecated",
            DeprecationWarning, 2)
        self._set_x509(x509)

    def _set_x509(self, x509):
        """Internal setter function."""
        self._x509 = x509

    @property
    def verify_callback(self):
        """
        :term:`callable`: Callback function that will be called to verify the
        X.509 server certificate returned by the WBEM server during the
        TLS/SSL handshake, in addition to the validation already performed
        by the TLS/SSL support.

        For details, see the description of the same-named init
        parameter of :class:`this class <pywbem.WBEMConnection>`.

        This attribute is settable, but setting it has been deprecated.
        """
        return self._verify_callback

    @verify_callback.setter
    def verify_callback(self, verify_callback):
        """Setter method; for a description see the getter method."""
        warnings.warn(
            "Setting the WBEMConnection.verify_callback property is deprecated",
            DeprecationWarning, 2)
        self._set_verify_callback(verify_callback)

    def _set_verify_callback(self, verify_callback):
        """Internal setter function."""
        self._verify_callback = verify_callback

    @property
    def ca_certs(self):
        """
        :term:`string`: Location of CA certificates (trusted certificates) for
        verifying the X.509 server certificate returned by the WBEM server.

        For details, see the description of the same-named init
        parameter of :class:`this class <pywbem.WBEMConnection>`.

        This attribute is settable, but setting it has been deprecated.
        """
        return self._ca_certs

    @ca_certs.setter
    def ca_certs(self, ca_certs):
        """Setter method; for a description see the getter method."""
        warnings.warn(
            "Setting the WBEMConnection.ca_certs property is deprecated",
            DeprecationWarning, 2)
        self._set_ca_certs(ca_certs)

    def _set_ca_certs(self, ca_certs):
        """Internal setter function."""
        self._ca_certs = ca_certs

    @property
    def no_verification(self):
        """
        :class:`py:bool`: Boolean indicating that verifications are disabled
        for this connection.

        For details, see the description of the same-named init
        parameter of :class:`this class <pywbem.WBEMConnection>`.

        This attribute is settable, but setting it has been deprecated.
        """
        return self._no_verification

    @no_verification.setter
    def no_verification(self, no_verification):
        """Setter method; for a description see the getter method."""
        warnings.warn(
            "Setting the WBEMConnection.no_verification property is deprecated",
            DeprecationWarning, 2)
        self._set_no_verification(no_verification)

    def _set_no_verification(self, no_verification):
        """Internal setter function."""
        self._no_verification = no_verification

    @property
    def timeout(self):
        """
        :term:`number`: Timeout in seconds, for requests sent to the server.

        *New in pywbem 0.8.*

        For details, see the description of the same-named init
        parameter of :class:`this class <pywbem.WBEMConnection>`.

        This attribute is settable, but setting it has been deprecated.
        """
        return self._timeout

    @timeout.setter
    def timeout(self, timeout):
        """Setter method; for a description see the getter method."""
        warnings.warn(
            "Setting the WBEMConnection.timeout property is deprecated",
            DeprecationWarning, 2)
        self._set_timeout(timeout)

    def _set_timeout(self, timeout):
        """Internal setter function."""
        self._timeout = timeout

    @property
    def operation_recorders(self):
        """
        Tuple of :class:`BaseOperationRecorder` subclass objects:
          **Experimental:** The operation recorders of this connection.

        *New in pywbem 0.12 as experimental.*
        """
        return tuple(self._operation_recorders)

    @property
    def operation_recorder(self):
        """
        :class:`BaseOperationRecorder`: **Deprecated:** The operation recorder
        that was last added to the connection, or `None` if the connection does
        not currently have any recorders.

        *New in pywbem 0.9 as experimental. Deprecated since pywbem 0.12.*

        Instead of using this deprecated property, the
        :attr:`~pywbem.WBEMConnection.operation_recorders` property should be
        used to retrieve the recorders of the connection, and the
        :meth:`~pywbem.WBEMConnection.add_operation_recorder` method should be
        used to add a recorder.

        This property is settable; setting this property will cause the
        specified operation recorder to be added to the connection as if
        :meth:`~pywbem.WBEMConnection.add_operation_recorder` was used.
        `None` is not permitted as a new value for this property.

        Raises:

          ValueError: Operation recorder must not be `None`.
          ValueError: Cannot add the same recorder class multiple times.
        """
        warnings.warn(
            "Reading the WBEMConnection.operation_recorder property has been "
            "deprecated. Use the operation_recorders property instead.",
            DeprecationWarning, 2)
        try:
            last_recorder = self._operation_recorders[-1]
        except IndexError:
            last_recorder = None
        return last_recorder

    @operation_recorder.setter
    def operation_recorder(self, operation_recorder):
        """Setter method; for a description see the getter method."""
        warnings.warn(
            "Setting the WBEMConnection.operation_recorder property has been "
            "deprecated. Use the add_operation_recorder() method instead.",
            DeprecationWarning, 2)
        self.add_operation_recorder(operation_recorder)

    @property
    def host(self):
        """
        :term:`unicode string`: The ``{host}[:{port}]`` component of the
        WBEM server's URL, as specified in the ``url`` attribute.

        *New in pywbem 0.11.*
        """
        host = self.url.split('://')[-1]
        return host

    @property
    def operation_recorder_enabled(self):
        """
        :class:`py:bool`: **Experimental:** Enablement status for all operation
        recorders of the connection.

        *New in pywbem 0.11 as experimental*

        This is a writeable property; setting this property will change the
        operation recorder enablement status accordingly for all operation
        recorders of the connection.

        Reading this property returns `True` if one or more operation recorders
        of the connection are enabled. Otherwise it returns `False`, also
        when the connection has no operation recorders.
        """
        for recorder in self._operation_recorders:
            if recorder.enabled():
                return True
        return False

    @operation_recorder_enabled.setter
    def operation_recorder_enabled(self, value):
        """Setter method; for a description see the getter method."""
        for recorder in self._operation_recorders:
            if value:
                recorder.enable()
            else:
                recorder.disable()

    @property
    def stats_enabled(self):
        """
        :class:`py:bool`: Statistics enablement status for this connection.

        *New in pywbem 0.11 as experimental and finalized in 0.12.*

        This is a writeable property; setting this property will change the
        statistics enablement status accordingly.

        The statistics enablement status can also be set when creating a
        connection, through the ``stats_enabled`` init argument of
        :class:`~pywbem.WBEMConnection`.
        """
        return self.statistics.enabled

    @stats_enabled.setter
    def stats_enabled(self, value):
        """Setter method; for a description see the getter method."""
        if value:
            self.statistics.enable()
        else:
            self.statistics.disable()

    @property
    def statistics(self):
        """
        :class:`~pywbem.Statistics`: Statistics for this connection.

        *New in pywbem 0.11 as experimental and finalized in 0.12.*

        Statistics are disabled by default and can be enabled via the
        ``stats_enabled`` argument when creating a connection object, or
        later via modifying the :attr:`~pywbem.WBEMConnection.stats_enabled`
        property on this connection object. See the
        :ref:`WBEM operation statistics` section for more details.
        """
        return self._statistics

    @property
    def last_operation_time(self):
        """
        :class:`py:float`: Elapsed time of the last operation that was executed
        via this connection in seconds or `None`.

        *New in pywbem 0.11 as experimental and finalized in 0.12.*

        This time is available only subsequent to the execution of an operation
        on this connection, and if the statistics are enabled on this
        connection. Otherwise, the value is `None`.
        """
        return self._last_operation_time

    @property
    def last_server_response_time(self):
        """
        :class:`py:float`: Server-measured response time of the last request,
        or `None`.

        *New in pywbem 0.11 as experimental and finalized in 0.12.*

        This time is optionally returned from the server in the HTTP header of
        the response.
        This time is available only subsequent to the execution of an operation
        on this connection if the WBEMServerResponseTime is received from the
        WBEM server. Otherwise, the value is `None`.
        """
        return self._last_server_response_time

    @property
    def use_pull_operations(self):
        """
        :class:`py:bool`: Boolean indicating that the client should attempt
        the use of pull operations in any `Iter...()` methods.

        *New in pywbem 0.11 as experimental and finalized in 0.13.*

        This property reflects the intent of the user as specified in the
        same-named init parameter of
        :class:`this class <pywbem.WBEMConnection>`. This property is not
        updated with the status of actually using pull operations. That status
        is maintained internally for each pull operation separately to
        accomodate WBEM servers that support only some of the pull operations.
        """
        return self._use_pull_operations

    @property
    def debug(self):
        """
        :class:`py:bool`: Boolean indicating that debug is enabled for this
        connection.

        When enabled (value `True`), the prettified last CIM-XML request and
        response will be stored in the following properties of this class:

        * :attr:`~pywbem.WBEMConnection.last_request`
        * :attr:`~pywbem.WBEMConnection.last_reply`

        When disabled (value `False`), these properties will be `None`.

        This attribute is writeable. The initial value of this attribute is
        `False`.

        Note that the following properties will be set regardless of whether
        debug is enabled for this connection:

        * :attr:`~pywbem.WBEMConnection.last_raw_request`
        * :attr:`~pywbem.WBEMConnection.last_raw_reply`
        * :attr:`~pywbem.WBEMConnection.last_request_len`
        * :attr:`~pywbem.WBEMConnection.last_reply_len`
        """
        return self._debug

    @debug.setter
    def debug(self, debug):
        """Setter method; for a description see the getter method."""
        self._debug = debug

    @property
    def last_request(self):
        """
        :term:`unicode string`:
        CIM-XML data of the last request sent to the WBEM server on this
        connection, formatted as prettified XML.

        This property is only set when debug is enabled (see
        :attr:`~pywbem.WBEMConnection.debug`), and is `None` otherwise.

        Prior to sending the very first request on this connection object,
        this property is `None`.
        """
        return self._last_request

    @property
    def last_raw_request(self):
        """
        :term:`unicode string`:
        CIM-XML data of the last request sent to the WBEM server
        on this connection, formatted as it was sent (=raw).

        Prior to sending the very first request on this connection object,
        this property is `None`.

        As of pywbem 0.13, this property is set independently of whether debug
        is enabled (see :attr:`~pywbem.WBEMConnection.debug`).
        """
        return self._last_raw_request

    @property
    def last_reply(self):
        """
        :term:`unicode string`:
        CIM-XML data of the last response received from the WBEM server
        on this connection, formatted as prettified XML.

        This property is only set when debug is enabled (see
        :attr:`~pywbem.WBEMConnection.debug`), and is `None` otherwise.

        This property is set to `None` in the WBEM operation methods of
        this class before the request is sent to the WBEM server, and is set
        to the prettified response when the response has been received from
        the WBEM server and XML parsed. If the XML parsing fails, this property
        will be `None`, but the :attr:`~pywbem.WBEMConnection.last_raw_reply`
        property does not depend on XML parsing and will already have been set
        at that point.

        Prior to sending the very first request on this connection object,
        this property is `None`.
        """
        return self._last_reply

    @property
    def last_raw_reply(self):
        """
        :term:`unicode string`:
        CIM-XML data of the last response received from the WBEM server
        on this connection, formatted as it was received (=raw).

        This property is set to `None` in the WBEM operation methods of
        this class before the request is sent to the WBEM server, and is set
        to the prettified response when the response has been received from
        the WBEM server, and before XML parsing takes place.

        Prior to sending the very first request on this connection object,
        this property is `None`.

        As of pywbem 0.13, this property is set independently of whether debug
        is enabled (see :attr:`~pywbem.WBEMConnection.debug`).
        """
        return self._last_raw_reply

    @property
    def last_request_len(self):
        """
        :class:`py:int`:
        The size of the HTTP body in the CIM-XML request of the last operation,
        in Bytes.

        Prior to sending the very first request on this connection object,
        this property is 0.

        This property is set independently of whether debug is enabled
        (see :attr:`~pywbem.WBEMConnection.debug`).
        """
        return self._last_request_len

    @property
    def last_reply_len(self):
        """
        :class:`py:int`:
        The size of the HTTP body in the CIM-XML response of the last
        operation, in Bytes.

        This property is set to 0 in the WBEM operation methods of
        this class before the request is sent to the WBEM server, and is set
        to the size when the response has been received from
        the WBEM server, and before XML parsing takes place.

        Prior to sending the very first request on this connection object,
        this property is 0.

        This property is set independently of whether debug is enabled
        (see :attr:`~pywbem.WBEMConnection.debug`).
        """
        return self._last_reply_len

    @property
    def conn_id(self):
        """
        :term:`connection id`:
        Connection ID (a unique ID) of this connection.

        The value for this property is created when the
        :class:`~pywbem.WBEMConnection` object is created and remains constant
        throughout the life of that object.

        The connection ID is part of each log entry output to uniquely identify
        the :class:`~pywbem.WBEMConnection` object responsible for that log.
        It also part of the logger name for the "pywbem.api" and "pywbem.http"
        loggers that create log entries so that logging can be defined
        separately for different connections.
        """
        return self._conn_id

    def __str__(self):
        """
        Return a short representation of the :class:`~pywbem.WBEMConnection`
        object for human consumption.
        """

        if isinstance(self.creds, tuple):
            # tuple (userid, password) was specified
            creds_repr = _format("({0!A}, ...)", self.creds[0])
        else:
            creds_repr = _format("{0!A}", self.creds)

        return _format(
            "WBEMConnection("
            "url={s.url!A}, "
            "creds={creds}, "
            "default_namespace={s.default_namespace!A}, ...)",
            s=self, creds=creds_repr)

    def __repr__(self):
        """
        Return a representation of the :class:`~pywbem.WBEMConnection` object
        with all attributes (except for the password in the
        credentials) that is suitable for debugging.
        """

        if isinstance(self.creds, tuple):
            # tuple (userid, password) was specified
            creds_repr = _format("({0!A}, ...)", self.creds[0])
        else:
            creds_repr = _format("{0!A}", self.creds)
        if self.x509:
            x509_repr = "{" + ", ".join(
                [_format("{0!A}: {1!A}", key, self.x509[key])
                 for key in sorted(six.iterkeys(self.x509))]) + "}"
        else:
            x509_repr = "None"

        recorder_list = [recorder.__class__.__name__
                         for recorder in self._operation_recorders]

        return _format(
            "WBEMConnection("
            "url={s.url!A}, "
            "creds={creds}, "
            "conn_id={s.conn_id!A}, "
            "default_namespace={s.default_namespace!A}, "
            "x509={x509}, "
            "verify_callback={s.verify_callback!A}, "
            "ca_certs={s.ca_certs!A}, "
            "no_verification={s.no_verification!A}, "
            "timeout={s.timeout!A}, "
            "use_pull_operations={s.use_pull_operations!A}, "
            "stats_enabled={s.stats_enabled!A}, "
            "recorders={recorders})",
            s=self, creds=creds_repr, x509=x509_repr, recorders=recorder_list)

    @classmethod
    def _configure_logger(cls, simple_name, log_dest, detail_level,
                          log_filename, connection, propagate):
        # pylint: disable=line-too-long
        """
        Configure the pywbem loggers and optionally activate WBEM connections
        for logging and setting a log detail level.

        Parameters:

          simple_name (:term:`string`):
            Simple name (ex. `'api'`) of the single pywbem logger this method
            should affect, or `'all'` to affect all pywbem loggers.

            Must be one of the strings in
            :data:`~pywbem._logging.LOGGER_SIMPLE_NAMES`.

          log_dest (:term:`string`):
            Log destination for the affected pywbem loggers, controlling the
            configuration of its Python logging parameters (log handler,
            message format, and log level).

            If it is a :term:`string`, it must be one of the strings in
            :data:`~pywbem._logging.LOG_DESTINATIONS` and the Python logging
            parameters of the loggers will be configured accordingly for their
            log handler, message format, and with a logging level of
            :attr:`py:logging.DEBUG`.

            If `None`, the Python logging parameters of the loggers will not be
            changed.

          detail_level (:term:`string` or :class:`int` or `None`):
            Detail level for the data in each log record that is generated by
            the affected pywbem loggers.

            If it is a :term:`string`, it must be one of the strings in
            :data:`~pywbem._logging.LOG_DETAIL_LEVELS` and the loggers will
            be configured for the corresponding detail level.

            If it is an :class:`int`, it defines the maximum size of the log
            records created and the loggers will be configured to output all
            available information up to that size.

            If `None`, the detail level configuration will not be changed.

          log_filename (:term:`string`):
            Path name of the log file (required if the log destination is
            `'file'`; otherwise ignored).

          connection (:class:`~pywbem.WBEMConnection` or :class:`py:bool` or `None`):
            WBEM connection(s) that should be affected for activation and for
            setting the detail level.

            If it is a :class:`py:bool`, the information for activating logging
            and for the detail level of the affected loggers will be stored for
            use by subsequently created :class:`~pywbem.WBEMConnection` objects.
            A value of `True` will store the information to activate the
            connections for logging, and will add the detail level for the
            logger(s).
            A value of `False` will reset the stored information for future
            connections to be deactivated with no detail levels specified.

            If it is a :class:`~pywbem.WBEMConnection` object, logging will be
            activated for that WBEM connection only and the specified detail
            level will be set for the affected pywbem loggers on the
            connection.

            If `None`, no WBEM connection will be activated for logging.

        propagate (:class:`py:bool`): Flag controlling whether the
          affected pywbem logger should propagate log events to its
          parent loggers.

        Raises:

          ValueError: Invalid input parameters (loggers remain unchanged).
        """  # noqa: E501
        # pylint: enable=line-too-long

        if simple_name == 'all':
            for name in ['api', 'http']:
                cls._configure_logger(name, log_dest=log_dest,
                                      detail_level=detail_level,
                                      log_filename=log_filename,
                                      connection=connection,
                                      propagate=propagate)
            return

        if simple_name == 'api':
            logger_name = LOGGER_API_CALLS_NAME
        elif simple_name == 'http':
            logger_name = LOGGER_HTTP_NAME
        else:
            raise ValueError(
                _format("Invalid simple logger name: {0!A}; must be one of: "
                        "{1!A}", simple_name, LOGGER_SIMPLE_NAMES))

        handler = cls._configure_logger_handler(log_dest, log_filename)

        detail_level = cls._configure_detail_level(detail_level)

        cls._activate_logger(logger_name, simple_name, detail_level, handler,
                             connection, propagate)

    @classmethod
    def _configure_detail_level(cls, detail_level):
        """
        Validate the `detail_level` parameter and return it.

        This accepts a string or integer for `detail_level`.
        """
        # process detail_level
        if isinstance(detail_level, six.string_types):
            if detail_level not in LOG_DETAIL_LEVELS:
                raise ValueError(
                    _format("Invalid log detail level string: {0!A}; must be "
                            "one of: {1!A}", detail_level, LOG_DETAIL_LEVELS))
        elif isinstance(detail_level, int):
            if detail_level < 0:
                raise ValueError(
                    _format("Invalid log detail level integer: {0}; must be a "
                            "positive integer.", detail_level))

        elif detail_level is None:
            detail_level = DEFAULT_LOG_DETAIL_LEVEL
        else:
            raise ValueError(
                _format("Invalid log detail level: {0!A}; must be one of: "
                        "{1!A}, or a positive integer",
                        detail_level, LOG_DETAIL_LEVELS))
        return detail_level

    @classmethod
    def _configure_logger_handler(cls, log_dest, log_filename):
        """
        Return a logging handler for the specified `log_dest`, or `None` if
        `log_dest` is `None`.
        """

        if log_dest is None:
            return None

        msg_format = '%(asctime)s-%(name)s-%(message)s'

        if log_dest == 'stderr':
            # Note: sys.stderr is the default stream for StreamHandler
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter(msg_format))
        elif log_dest == 'file':
            if not log_filename:
                raise ValueError("Log filename is required if log destination "
                                 "is 'file'")
            handler = logging.FileHandler(log_filename, encoding="UTF-8")
            handler.setFormatter(logging.Formatter(msg_format))
        else:
            raise ValueError(
                _format("Invalid log destination: {0!A}; Must be one of: "
                        "{1!A}", log_dest, LOG_DESTINATIONS))

        return handler

    @classmethod
    def _activate_logger(cls, logger_name, simple_name, detail_level, handler,
                         connection, propagate):
        """
        Configure the specified logger, and activate logging and set detail
        level for connections.

        The specified logger is always a single pywbem logger; the simple
        logger name 'all' has already been resolved by the caller into
        multiple calls to this method.

        The 'handler' parameter controls logger configuration:
        * If None, nothing is done.
        * If a Handler object, the specified logger gets its handlers replaced
          with the new handler, and logging level DEBUG is set, and the
          `propagate` attribute of the logger is set according to the
          `propagate` parameter.

        The 'connection' paraneter controls activation and setting of the
        detail level:
        * If None, nothing is done.
        * If bool=True, log activation and log detail information is stored for
          use by future connections in class variables of WBEMConnection.
        * If bool=False, log activation and log detail information is reset.
        * If a WBEMConnection object, logging is activated and detail level is
          set immediately for that connection.
        """

        if handler is not None:
            assert isinstance(handler, logging.Handler)

            # Replace existing handlers of the specified logger (e.g. from
            # previous calls) by the specified handler

            logger = logging.getLogger(logger_name)
            for hdlr in logger.handlers:
                logger.removeHandler(hdlr)
            logger.addHandler(handler)

            logger.setLevel(logging.DEBUG)
            logger.propagate = propagate

        if connection is not None:
            if isinstance(connection, bool):
                if connection:
                    # Store the activation and detail level information for
                    # future connections. This information is used in the init
                    # method of WBEMConnection to activate logging at that
                    # point.
                    cls._activate_logging = True
                    cls._log_detail_levels[simple_name] = detail_level
                else:
                    cls._reset_logging_config()
            else:
                assert isinstance(connection, WBEMConnection)

                # Activate logging for this existing connection by ensuring
                # the connection has a log recorder

                recorder_found = False
                # pylint: disable=protected-access
                for recorder in connection._operation_recorders:
                    if isinstance(recorder, LogOperationRecorder):
                        recorder_found = True
                        break

                if not recorder_found:
                    recorder = LogOperationRecorder(conn_id=connection.conn_id)

                # Add the log detail level for this logger to the log recorder
                # of this connection

                detail_levels = recorder.detail_levels.copy()
                detail_levels[simple_name] = detail_level
                recorder.set_detail_level(detail_levels)

                if not recorder_found:
                    # This call must be made after the detail levels of the
                    # recorder have been set, because that data is used
                    # for recording the WBEM connection information.
                    connection.add_operation_recorder(recorder)

                # TODO execute stage of wbem connection if not already executed.
                # How do we know it is already executed???

    def add_operation_recorder(self, operation_recorder):
        # pylint: disable=line-too-long
        """
        **Experimental:** Add an operation recorder to this connection.

        *New in pywbem 0.12 as experimental.*

        If the connection already has a recorder with the same class, the
        request to add the recorder is ignored.

        Parameters:

          operation_recorder (:class:`~pywbem.BaseOperationRecorder` subclass object):
            The operation recorder to be added. Must not be `None`.

        Raises:

          ValueError: Operation recorder must not be `None`.
          ValueError: Cannot add the same recorder class multiple times.
        """  # noqa: E501
        if operation_recorder is None:
            raise ValueError("Invalid value None for new operation recorder")

        for recorder in self._operation_recorders:
            # pylint: disable=unidiomatic-typecheck
            if type(recorder) is type(operation_recorder):
                raise ValueError(
                    _format("Cannot add the same operation recorder class {0} "
                            "multiple times to the same connection",
                            type(operation_recorder)))
        self._operation_recorders.append(operation_recorder)

        operation_recorder.reset()
        operation_recorder.stage_wbem_connection(self)

    def operation_recorder_reset(self, pull_op=False):
        """
        **Experimental:** Low-level method used by the operation-specific
        methods of this class.

        *New in pywbem 0.9 as experimental.*

        It resets the operation processing state of all recorders of this
        connection, to be ready for processing a new operation call.
        """
        for recorder in self._operation_recorders:
            recorder.reset(pull_op)

    def operation_recorder_stage_pywbem_args(self, method, **kwargs):
        """
        **Experimental:** Low-level method used by the operation-specific
        methods of this class.

        *New in pywbem 0.9 as experimental.*

        It forwards the operation method name and arguments to all recorders of
        this connection.
        """
        for recorder in self._operation_recorders:
            recorder.stage_pywbem_args(method, **kwargs)

    def operation_recorder_stage_result(self, ret, exc):
        """
        **Experimental:** Low-level method used by the operation-specific
        methods of this class.

        *New in pywbem 0.9 as experimental.*

        It forwards the operation results including exceptions that were
        raised, to all recorders of this connection, and causes the forwarded
        information to be recorded by all recorders of this connection.
        """
        for recorder in self._operation_recorders:
            recorder.stage_pywbem_result(ret, exc)
            recorder.record_staged()

    @classmethod
    def _reset_logging_config(cls):
        """
        Reset the activation of logging and the log detail levels for future
        WBEM connections.

        This method resets the corresponding class variables
        of :class:`~pywbem.WBEMConnection`.
        """
        cls._activate_logging = False
        cls._log_detail_levels = {}

    def imethodcall(self, methodname, namespace, response_params_rqd=False,
                    **params):
        """
        **Deprecated:** Low-level method used by the operation-specific methods
        of this class.

        *Deprecated since pywbem 0.12.*

        Calling this function directly has been deprecated and will issue a
        :term:`DeprecationWarning`.
        Users should call the operation-specific methods (e.g. GetInstance)
        instead of this method.
        This method will be removed in the next pywbem release after 0.12.
        """
        warnings.warn(
            "Calling imethodcall() directly is deprecated; it will be removed "
            "in the next pywbem release after 0.12",
            DeprecationWarning, 2)
        return self._imethodcall(methodname, namespace,
                                 has_out_params=response_params_rqd,
                                 **params)

    def _imethodcall(self, methodname, namespace, has_return_value=True,
                     has_out_params=False, **params):
        """
        Perform an intrinsic CIM-XML operation.

        Parameters:

          methodname (string): Name of the CIM operation (e.g. 'GetInstance').

          namespace (string): Namespace name, or None. In case of None, the
            default connection namespace will be used.

          has_return_value (bool): Indicates that the operation is defined with
            a non-void return value.

          has_out_params (bool): Indicates that the operation is defined with
            one or more output parameters.

          **in_params (dict): Input parameters for the operation.

        For failed operations and invalid responses, raises an exception.

        For successful operations, returns:

        * `None`, for operations with a void return type and no output params.

        * Otherwise, the list of child elements of IMETHODRESPONSE, containing
          these items:

          - zero or one IRETURNVALUE (as tupletree node) for the operation
            return value. Only operations with output parameters will return
            no IRETURNVALUE element for representing an empty result list.

          - zero or more PARAMVALUE (unpacked) for the operation output
            parameters.
        """

        # Create HTTP extension headers for CIM-XML.
        # Note: The two-step encoding required by DSP0200 will be performed in
        # wbem_request().

        cimxml_headers = [
            ('CIMOperation', 'MethodCall'),
            ('CIMMethod', methodname),
            ('CIMObject', get_cimobject_header(namespace)),
        ]

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

        request_data = req_xml.toxml()

        # Set attributes recording the request.
        # Also, reset attributes recording the reply in case we fail.
        self._last_raw_request = request_data
        self._last_request_len = len(request_data)
        self._last_raw_reply = None
        self._last_reply_len = 0
        self._last_server_response_time = None
        if self.debug:
            self._last_request = req_xml.toprettyxml(indent='  ')
            self._last_reply = None

        # Send request and receive response
        reply_data, self._last_server_response_time = wbem_request(
            self.url, request_data, self.creds, cimxml_headers,
            x509=self.x509,
            verify_callback=self.verify_callback,
            ca_certs=self.ca_certs,
            no_verification=self.no_verification,
            timeout=self.timeout,
            debug=self.debug,
            recorders=self._operation_recorders,
            conn_id=self.conn_id)

        # Set attributes recording the response, part 1.
        # Only those that can be done without parsing (which can fail).
        self._last_raw_reply = reply_data
        self._last_reply_len = len(reply_data)

        # Parse the XML into a tuple tree (may raise CIMXMLParseError or
        # XMLParseError):
        tt_ = xml_to_tupletree_sax(reply_data, "CIM-XML response")
        tp = TupleParser(self.conn_id)
        tup_tree = tp.parse_cim(tt_)

        # Set attributes recording the response, part 2.
        if self.debug:
            self._last_reply = _to_pretty_xml(reply_data)

        # Check the tuple tree

        if tup_tree[0] != 'CIM':
            raise CIMXMLParseError(
                _format("Expecting CIM element, got {0}", tup_tree[0]),
                conn_id=self.conn_id)
        tup_tree = tup_tree[2]

        if tup_tree[0] != 'MESSAGE':
            raise CIMXMLParseError(
                _format("Expecting MESSAGE element, got {0}", tup_tree[0]),
                conn_id=self.conn_id)
        tup_tree = tup_tree[2]

        if tup_tree[0] != 'SIMPLERSP':
            raise CIMXMLParseError(
                _format("Expecting SIMPLERSP element, got {0}", tup_tree[0]),
                conn_id=self.conn_id)
        tup_tree = tup_tree[2]

        if tup_tree[0] != 'IMETHODRESPONSE':
            raise CIMXMLParseError(
                _format("Expecting IMETHODRESPONSE element, got {0}",
                        tup_tree[0]),
                conn_id=self.conn_id)

        if tup_tree[1]['NAME'] != methodname:
            raise CIMXMLParseError(
                _format("Expecting attribute NAME={0!A}, got {1!A}",
                        methodname, tup_tree[1]['NAME']),
                conn_id=self.conn_id)
        tup_tree = tup_tree[2]

        # At this point tup_tree is a list of the child elements of
        # IMETHODRESPONSE:
        #   (ERROR | (IRETURNVALUE?, PARAMVALUE*)
        # or an empty list if there were no child elements.
        #
        # More specifically, the following cases are possible for tup_tree:
        # - operation failed: List with one ERROR node
        # - operation succeeded:
        #   - operation has void return type and no output parms
        #     (e.g. DeleteInstance): Empty list.
        #   - operation has non-void return type and no output parms
        #     (e.g. CreateInstance): List with (zero or?) one IRETURNVALUE
        #     node.
        #   - operation has non-void return type and output parms
        #     (e.g. OpenEnumerateInstances): List with (zero or?) one
        #     IRETURNVALUE node and one unpacked PARAMVALUE node for each
        #     output parameter.
        #
        # Note: DSP0200 is not entirely clear as to whether an empty result
        # list must be represented as an empty IRETURNVALUE node vs.
        # omitting it. Pywbem tolerates a missing IRETURNVALUE node.
        #
        # Note that there are no operations defined with a void return type but
        # with output parameters.

        # Check for failed operation
        if tup_tree and tup_tree[0][0] == 'ERROR':
            # The operation failed
            err = tup_tree[0]
            code = int(err[1]['CODE'])
            err_insts = err[2] or None  # List of CIMInstance objects
            if 'DESCRIPTION' in err[1]:
                desc = err[1]['DESCRIPTION']
            else:
                desc = _format("Error code {0}", err[1]['CODE'])
            raise CIMError(
                code, desc, instances=err_insts, conn_id=self.conn_id)

        # At this point, we know the operation was successful.

        return_value = False
        out_param_names = []
        for child_node in tup_tree:
            if child_node[0] == 'IRETURNVALUE':
                return_value = True
            else:
                # The PARAMVALUE nodes are already unpacked
                out_param_names.append(child_node[0])

        # Convert empty list to None
        if not tup_tree:
            tup_tree = None

        # Check unexpected return value and output parameters
        if not has_return_value and return_value:
            raise CIMXMLParseError(
                _format("Unexpected IRETURNVALUE child element of "
                        "IMETHODRESPONSE for operation {0} which is defined as "
                        "void", methodname),
                conn_id=self.conn_id)
        if not has_out_params and out_param_names:
            raise CIMXMLParseError(
                _format("Unexpected PARAMVALUE child element(s) of "
                        "IMETHODRESPONSE for operation {0} which has no output "
                        "parameters defined: {1!A}",
                        methodname, out_param_names),
                conn_id=self.conn_id)

        # Missing return value and output parameters are checked by caller

        return tup_tree

    def methodcall(self, methodname, localobject, Params=None, **params):
        """
        **Deprecated:** Low-level method used by the
        :meth:`~pywbem.WBEMConnection.InvokeMethod` method of this class.

        *Deprecated since pywbem 0.12.*

        Calling this function directly has been deprecated and will issue a
        :term:`DeprecationWarning`.
        Users should call :meth:`~pywbem.WBEMConnection.InvokeMethod` instead
        of this method.
        This method will be removed in the next pywbem release after 0.12.
        """
        warnings.warn(
            "Calling methodcall() directly is deprecated; it will be removed "
            "in the next pywbem release after 0.12",
            DeprecationWarning, 2)
        return self._methodcall(methodname, localobject, Params, **params)

    def _methodcall(self, methodname, objectname, Params=None, **params):
        """
        Perform an extrinsic CIM-XML method call.

        Parameters:

          methodname (string): CIM method name.

          objectname (string or CIMInstanceName or CIMClassName):
            Target object. Strings are interpreted as class names.

          Params: CIM method input parameters, for details see InvokeMethod().

          **params: CIM method input parameters, for details see InvokeMethod().
        """

        if isinstance(objectname, (CIMInstanceName, CIMClassName)):
            localobject = objectname.copy()
            if localobject.namespace is None:
                localobject.namespace = self.default_namespace
            localobject.host = None
        elif isinstance(objectname, six.string_types):
            # a string is always interpreted as a class name
            localobject = CIMClassName(objectname,
                                       namespace=self.default_namespace)
        else:
            raise TypeError(
                _format("Invalid type for ObjectName: {0}", type(objectname)))

        # Create HTTP extension headers for CIM-XML.
        # Note: The two-step encoding required by DSP0200 will be performed in
        # wbem_request().

        cimxml_headers = [
            ('CIMOperation', 'MethodCall'),
            ('CIMMethod', methodname),
            ('CIMObject', get_cimobject_header(localobject)),
        ]

        # Add a special HTTP header for SFCB's special password expiration
        # update mechanism. For details, see the documentation of the
        # pywbem config variable AUTO_GENERATE_SFCB_UEP_HEADER.
        if AUTO_GENERATE_SFCB_UEP_HEADER and \
                methodname == 'UpdateExpiredPassword' and \
                objectname.classname == 'SFCB_Account':
            cimxml_headers.append(('Pragma', 'UpdateExpiredPassword'))

        # Create parameter list

        def infer_type(obj):
            """
            Infer the CIM data type name of a parameter value.
            """
            if isinstance(obj, CIMType):  # pylint: disable=no-else-return
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
                return infer_type(obj[0]) if obj else None
            elif obj is None:
                return None
            raise TypeError(
                _format("Unsupported parameter type {0}", type(obj)))

        def paramvalue(obj):
            """
            Return a cim_xml node to be used as the value for a parameter.
            """
            if isinstance(obj, (datetime, timedelta)):
                obj = CIMDateTime(obj)
            if isinstance(obj, (CIMType, bool, six.string_types)):
                # This includes CIMDateTime (subclass of CIMType)
                return cim_xml.VALUE(atomic_to_cim_xml(obj))
            if isinstance(obj, (CIMClassName, CIMInstanceName)):
                return cim_xml.VALUE_REFERENCE(obj.tocimxml())
            if isinstance(obj, CIMInstance):
                return cim_xml.VALUE(obj.tocimxml(ignore_path=True).toxml())
            if isinstance(obj, CIMClass):
                # CIMClass.tocimxml() always ignores path
                return cim_xml.VALUE(obj.tocimxml().toxml())
            if isinstance(obj, list):
                if obj and isinstance(obj[0], (CIMClassName, CIMInstanceName)):
                    return cim_xml.VALUE_REFARRAY([paramvalue(x) for x in obj])
                return cim_xml.VALUE_ARRAY([paramvalue(x) for x in obj])
            if obj is None:
                return None
            raise TypeError(
                _format("Unsupported parameter type {0}", type(obj)))

        def infer_embedded_object(obj):
            """
            Infer the embedded_object value of a parameter value.
            """
            if isinstance(obj, list) and obj:
                return infer_embedded_object(obj[0])

            if isinstance(obj, CIMClass):
                return 'object'

            if isinstance(obj, CIMInstance):
                return 'instance'
            return None

        ptuples = []  # tuple (name, value, type, embedded_object)
        if Params is not None:
            for p in Params:
                if isinstance(p, CIMParameter):
                    ptuple = (p.name, p.value, p.type, p.embedded_object)
                else:  # p is a tuple of name, value
                    ptuple = (p[0], p[1], infer_type(p[1]),
                              infer_embedded_object(p[1]))
                ptuples.append(ptuple)
        for n, v in params.items():
            ptuple = (n, v, infer_type(v), infer_embedded_object(v))
            ptuples.append(ptuple)

        plist = [cim_xml.PARAMVALUE(n, paramvalue(v), t, embedded_object=eo)
                 for n, v, t, eo in ptuples]

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

        request_data = req_xml.toxml()

        # Set attributes recording the request.
        # Also, reset attributes recording the reply in case we fail.
        self._last_raw_request = request_data
        self._last_request_len = len(request_data)
        self._last_raw_reply = None
        self._last_reply_len = 0
        self._last_server_response_time = None
        if self.debug:
            self._last_request = req_xml.toprettyxml(indent='  ')
            self._last_reply = None

        # Send request and receive response
        reply_data, self._last_server_response_time = wbem_request(
            self.url, request_data, self.creds, cimxml_headers,
            x509=self.x509,
            verify_callback=self.verify_callback,
            ca_certs=self.ca_certs,
            no_verification=self.no_verification,
            timeout=self.timeout,
            debug=self.debug,
            recorders=self._operation_recorders,
            conn_id=self.conn_id)

        # Set attributes recording the response, part 1.
        # Only those that can be done without parsing (which can fail).
        self._last_raw_reply = reply_data
        self._last_reply_len = len(reply_data)

        # Parse the XML into a tuple tree (may raise CIMXMLParseError or
        # XMLParseError):
        tt_ = xml_to_tupletree_sax(reply_data, "CIM-XML response")
        tp = TupleParser(self.conn_id)
        tup_tree = tp.parse_cim(tt_)

        # Set attributes recording the response, part 2.
        if self.debug:
            self._last_reply = _to_pretty_xml(reply_data)

        # Check the tuple tree

        if tup_tree[0] != 'CIM':
            raise CIMXMLParseError(
                _format("Expecting CIM element, got {0}", tup_tree[0]),
                conn_id=self.conn_id)
        tup_tree = tup_tree[2]

        if tup_tree[0] != 'MESSAGE':
            raise CIMXMLParseError(
                _format("Expecting MESSAGE element, got {0}", tup_tree[0]),
                conn_id=self.conn_id)
        tup_tree = tup_tree[2]

        if tup_tree[0] != 'SIMPLERSP':
            raise CIMXMLParseError(
                _format("Expecting SIMPLERSP element, got {0}", tup_tree[0]),
                conn_id=self.conn_id)
        tup_tree = tup_tree[2]

        if tup_tree[0] != 'METHODRESPONSE':
            raise CIMXMLParseError(
                _format("Expecting METHODRESPONSE element, got {0}",
                        tup_tree[0]),
                conn_id=self.conn_id)

        if tup_tree[1]['NAME'] != methodname:
            raise CIMXMLParseError(
                _format("Expecting attribute NAME={0!A}, got {1!A}",
                        methodname, tup_tree[1]['NAME']),
                conn_id=self.conn_id)
        tup_tree = tup_tree[2]

        # At this point we have an optional RETURNVALUE and zero or
        # more PARAMVALUE elements representing output parameters.

        if tup_tree and tup_tree[0][0] == 'ERROR':
            # Operation failed
            err = tup_tree[0]
            code = int(err[1]['CODE'])
            err_insts = err[2] or None  # List of CIMInstance objects
            if 'DESCRIPTION' in err[1]:
                desc = err[1]['DESCRIPTION']
            else:
                desc = _format("Error code {0}", err[1]['CODE'])
            raise CIMError(
                code, desc, instances=err_insts, conn_id=self.conn_id)

        # #  Original code return tup_tree

        # Convert optional RETURNVALUE into a Python object
        returnvalue = None

        if tup_tree and tup_tree[0][0] == 'RETURNVALUE':

            returnvalue = cimvalue(tup_tree[0][2], tup_tree[0][1]['PARAMTYPE'])
            tup_tree = tup_tree[1:]

        # Convert zero or more PARAMVALUE elements into dictionary

        output_params = NocaseDict()

        for p in tup_tree:
            if p[1] == 'reference':
                output_params[p[0]] = p[2]
            else:
                output_params[p[0]] = cimvalue(p[2], p[1])

        return (returnvalue, output_params)

    def _iparam_namespace_from_namespace(self, obj):
        # pylint: disable=invalid-name,
        """
        Determine the namespace from a namespace string, or `None`. The
        default namespace of the connection object is used, if needed.

        Return the so determined namespace for use as an argument to
        imethodcall().
        """

        if isinstance(obj, six.string_types):
            namespace = obj.strip('/')
        elif obj is None:
            namespace = obj
        else:
            raise TypeError(
                _format("Expecting None (for default), or a namespace string, "
                        "got: {0}", type(obj)))
        if namespace is None:
            namespace = self.default_namespace
        return namespace

    def _iparam_namespace_from_objectname(self, obj):
        # pylint: disable=invalid-name,
        """
        Determine the namespace from an object name, that can be a class
        name string, a CIMClassName or CIMInstanceName object, or `None`.
        The default namespace of the connection object is used, if needed.

        Return the so determined namespace for use as an argument to
        imethodcall().
        """

        if isinstance(obj, (CIMClassName, CIMInstanceName)):
            namespace = obj.namespace
        elif isinstance(obj, six.string_types):
            namespace = None
        elif obj is None:
            namespace = obj
        else:
            raise TypeError(
                _format("Expecting None (for default), a class name string, a "
                        "CIMClassName object, or a CIMInstanceName object, "
                        "got: {0}", type(obj)))
        if namespace is None:
            namespace = self.default_namespace
        return namespace

    @staticmethod
    def _iparam_objectname(objectname):
        """
        Convert an object name (= class or instance name) specified in an
        operation method into a CIM object that can be passed to
        imethodcall().
        """

        if isinstance(objectname, (CIMClassName, CIMInstanceName)):
            objectname = objectname.copy()
            objectname.host = None
            objectname.namespace = None
        elif isinstance(objectname, six.string_types):
            objectname = CIMClassName(objectname)
        elif objectname is None:
            pass
        else:
            raise TypeError(
                _format("Expecting None, a classname string, a CIMClassName "
                        "or CIMInstanceName object, got: {0}",
                        type(objectname)))
        return objectname

    @staticmethod
    def _iparam_classname(classname):
        """
        Convert a class name specified in an operation method into a CIM
        object that can be passed to imethodcall().
        """

        if isinstance(classname, CIMClassName):
            classname = classname.copy()
            classname.host = None
            classname.namespace = None
        elif isinstance(classname, six.string_types):
            classname = CIMClassName(classname)
        elif classname is None:
            pass
        else:
            raise TypeError(
                _format("Expecting None, a classname string or a "
                        "CIMClassName object, got: {0}", type(classname)))
        return classname

    @staticmethod
    def _iparam_instancename(instancename):
        """
        Convert an instance name specified in an operation method into a CIM
        object that can be passed to imethodcall().
        """

        if isinstance(instancename, CIMInstanceName):
            instancename = instancename.copy()
            instancename.host = None
            instancename.namespace = None
        elif instancename is None:
            pass
        else:
            raise TypeError(
                _format("Expecting None or a CIMInstanceName object, got: {0}",
                        type(instancename)))
        return instancename

    def _get_rslt_params(self, result, namespace):
        """
        Common processing for pull results to separate end-of-sequence,
        enum-context, and entities in IRETURNVALUE.

        Returns tuple of entities in IRETURNVALUE, end_of_sequence,
        and enumeration_context)
        """
        rtn_objects = []
        end_of_sequence = False
        enumeration_context = None
        end_of_sequence_found = False  # flag True if found and valid value
        enumeration_context_found = False  # flag True if ec tuple found
        for p in result:
            if p[0] == 'EndOfSequence':
                if isinstance(p[2], six.string_types):
                    p2 = p[2].lower()
                    if p2 in ['true', 'false']:  # noqa: E125
                        end_of_sequence = True if p2 == 'true' else False
                        end_of_sequence_found = True
                    else:
                        raise CIMXMLParseError(
                            _format("EndOfSequence output parameter has an "
                                    "invalid value: {0!A}", p[2]),
                            conn_id=self.conn_id)

            elif p[0] == 'EnumerationContext':
                enumeration_context_found = True
                if isinstance(p[2], six.string_types):
                    enumeration_context = p[2]

            elif p[0] == "IRETURNVALUE":
                rtn_objects = p[2]

        if not end_of_sequence_found and not enumeration_context_found:
            raise CIMXMLParseError(
                "Expected EndOfSequence or EnumerationContext output "
                "parameter in open/pull response, but none received",
                conn_id=self.conn_id)

        if not end_of_sequence and enumeration_context is None:
            raise CIMXMLParseError(
                "Expected EnumerationContext output parameter because "
                "EndOfSequence=False, but did not receive it.",
                conn_id=self.conn_id)

        # Drop enumeration_context if eos True
        # Returns tuple of enumeration context and namespace
        rtn_ctxt = None if end_of_sequence else (enumeration_context,
                                                 namespace)
        return (rtn_objects, end_of_sequence, rtn_ctxt)

    #
    # Operations
    #

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

            Leading and trailing slash characters will be stripped. The lexical
            case will be preserved.

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
            instances, as follows:

            * If `False`, qualifiers are not included.
            * If `True`, qualifiers are included if the WBEM server implements
              support for this parameter.
            * If `None`, this parameter is not passed to the WBEM server, and
              causes the server-implemented default to be used. :term:`DSP0200`
              defines that the server-implemented default is `False`.

            This parameter has been deprecated in :term:`DSP0200`. Clients
            cannot rely on qualifiers to be returned in this operation.

          IncludeClassOrigin (:class:`py:bool`):
            Indicates that class origin information is to be included on each
            property in the returned instances, as follows:

            * If `False`, class origin information is not included.
            * If `True`, class origin information is included.
            * If `None`, this parameter is not passed to the WBEM server, and
              causes the server-implemented default to be used. :term:`DSP0200`
              defines that the server-implemented default is `False`.

            This parameter has been deprecated in :term:`DSP0200`. WBEM servers
            may either implement this parameter as specified, or may treat any
            specified value as `False`.

          PropertyList (:term:`string` or :term:`py:iterable` of :term:`string`):
            An iterable specifying the names of the properties (or a string
            that defines a single property) to be included in the returned
            instances (case independent).

            An empty iterable indicates to include no properties.

            If `None`, all properties are included.

          **extra :
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

        exc = None
        instances = None
        method_name = 'EnumerateInstances'

        if self._operation_recorders:
            self.operation_recorder_reset()
            self.operation_recorder_stage_pywbem_args(
                method=method_name,
                ClassName=ClassName,
                namespace=namespace,
                LocalOnly=LocalOnly,
                DeepInheritance=DeepInheritance,
                IncludeQualifiers=IncludeQualifiers,
                IncludeClassOrigin=IncludeClassOrigin,
                PropertyList=PropertyList,
                **extra)

        try:
            stats = self.statistics.start_timer(method_name)
            if namespace is None and isinstance(ClassName, CIMClassName):
                namespace = ClassName.namespace
            namespace = self._iparam_namespace_from_namespace(namespace)
            classname = self._iparam_classname(ClassName)
            PropertyList = _iparam_propertylist(PropertyList)

            result = self._imethodcall(
                method_name,
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

            for instance in instances:

                if not isinstance(instance, CIMInstance):
                    raise CIMXMLParseError(
                        _format("Expecting CIMInstance object in result list, "
                                "got {0} object", instance.__class__.__name__),
                        conn_id=self.conn_id)

                # The EnumerateInstances CIM-XML operation returns instances as
                # VALUE.NAMEDINSTANCE elements which represent the instance
                # paths as INSTANCENAME elements which do not contain namespace
                # or host. We want to return instance paths with namespace, so
                # we set it to the effective target namespace.
                instance.path.namespace = namespace

            return instances

        except (CIMXMLParseError, XMLParseError) as exce:
            exce.request_data = self.last_raw_request
            exce.response_data = self.last_raw_reply
            exc = exce
            raise
        except Exception as exce:
            exc = exce
            raise
        finally:
            self._last_operation_time = stats.stop_timer(
                self.last_request_len, self.last_reply_len,
                self.last_server_response_time, exc)
            if self._operation_recorders:
                self.operation_recorder_stage_result(instances, exc)

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

            Leading and trailing slash characters will be stripped. The lexical
            case will be preserved.

            If `None`, the namespace of the `ClassName` parameter will be used,
            if specified as a :class:`~pywbem.CIMClassName` object. If that is
            also `None`, the default namespace of the connection will be used.

          **extra :
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

        exc = None
        instancenames = None
        method_name = 'EnumerateInstanceNames'

        if self._operation_recorders:
            self.operation_recorder_reset()
            self.operation_recorder_stage_pywbem_args(
                method=method_name,
                ClassName=ClassName,
                namespace=namespace,
                **extra)

        try:
            stats = self.statistics.start_timer(method_name)
            if namespace is None and isinstance(ClassName, CIMClassName):
                namespace = ClassName.namespace
            namespace = self._iparam_namespace_from_namespace(namespace)
            classname = self._iparam_classname(ClassName)

            result = self._imethodcall(
                method_name,
                namespace,
                ClassName=classname,
                **extra)

            if result is None:
                instancenames = []
            else:
                instancenames = result[0][2]

            for instancepath in instancenames:

                if not isinstance(instancepath, CIMInstanceName):
                    raise CIMXMLParseError(
                        _format("Expecting CIMInstanceName object in result "
                                "list, got {0} object",
                                instancepath.__class__.__name__),
                        conn_id=self.conn_id)

                # The EnumerateInstanceNames CIM-XML operation returns instance
                # paths as INSTANCENAME elements, which do not contain
                # namespace or host. We want to return instance paths with
                # namespace, so we set it to the effective target namespace.
                instancepath.namespace = namespace

            return instancenames

        except (CIMXMLParseError, XMLParseError) as exce:
            exce.request_data = self.last_raw_request
            exce.response_data = self.last_raw_reply
            exc = exce
            raise
        except Exception as exce:
            exc = exce
            raise
        finally:
            self._last_operation_time = stats.stop_timer(
                self.last_request_len, self.last_reply_len,
                self.last_server_response_time, exc)
            if self._operation_recorders:
                self.operation_recorder_stage_result(instancenames, exc)

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
            cannot rely on qualifiers to be returned in this operation.

          IncludeClassOrigin (:class:`py:bool`):
            Indicates that class origin information is to be included on each
            property in the returned instance, as follows:

            * If `False`, class origin information is not included.
            * If `True`, class origin information is included.
            * If `None`, this parameter is not passed to the WBEM server, and
              causes the server-implemented default to be used. :term:`DSP0200`
              defines that the server-implemented default is `False`.

            This parameter has been deprecated in :term:`DSP0200`. WBEM servers
            may either implement this parameter as specified, or may treat any
            specified value as `False`.

          PropertyList (:term:`string` or :term:`py:iterable` of :term:`string`):
            An iterable specifying the names of the properties (or a string
            that defines a single property) to be included in the returned
            instance (case independent).

            An empty iterable indicates to include no properties.

            If `None`, all properties are included.

          **extra :
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

        exc = None
        instance = None
        method_name = 'GetInstance'

        if self._operation_recorders:
            self.operation_recorder_reset()
            self.operation_recorder_stage_pywbem_args(
                method=method_name,
                InstanceName=InstanceName,
                LocalOnly=LocalOnly,
                IncludeQualifiers=IncludeQualifiers,
                IncludeClassOrigin=IncludeClassOrigin,
                PropertyList=PropertyList,
                **extra)

        try:

            stats = self.statistics.start_timer(method_name)
            # Strip off host and namespace to make this a "local" object
            namespace = self._iparam_namespace_from_objectname(InstanceName)
            instancename = self._iparam_instancename(InstanceName)
            PropertyList = _iparam_propertylist(PropertyList)

            result = self._imethodcall(
                method_name,
                namespace,
                InstanceName=instancename,
                LocalOnly=LocalOnly,
                IncludeQualifiers=IncludeQualifiers,
                IncludeClassOrigin=IncludeClassOrigin,
                PropertyList=PropertyList,
                **extra)

            if result is None:
                raise CIMXMLParseError(
                    "Expecting a child element below IMETHODRESPONSE, "
                    "got no child elements", conn_id=self.conn_id)
            result = result[0][2]  # List of children of IRETURNVALUE

            if not result:
                raise CIMXMLParseError(
                    "Expecting a child element below IRETURNVALUE, "
                    "got no child elements", conn_id=self.conn_id)
            instance = result[0]  # CIMInstance object

            if not isinstance(instance, CIMInstance):
                raise CIMXMLParseError(
                    _format("Expecting CIMInstance object in result, got {0} "
                            "object", instance.__class__.__name__),
                    conn_id=self.conn_id)

            # The GetInstance CIM-XML operation returns the instance as an
            # INSTANCE element, which does not contain an instance path. We
            # want to return the instance with a path, so we set it to the
            # input path. Because the namespace in the input path is optional,
            # we set it to the effective target namespace (on a copy of the
            # input path).
            instance.path = instancename.copy()
            instance.path.namespace = namespace

            return instance

        except (CIMXMLParseError, XMLParseError) as exce:
            exce.request_data = self.last_raw_request
            exce.response_data = self.last_raw_reply
            exc = exce
            raise
        except Exception as exce:
            exc = exce
            raise
        finally:
            self._last_operation_time = stats.stop_timer(
                self.last_request_len, self.last_reply_len,
                self.last_server_response_time, exc)
            if self._operation_recorders:
                self.operation_recorder_stage_result(instance, exc)

    def ModifyInstance(self, ModifiedInstance, IncludeQualifiers=None,
                       PropertyList=None, **extra):
        # pylint: disable=invalid-name,line-too-long
        """
        Modify the property values of an instance.

        This method performs the ModifyInstance operation
        (see :term:`DSP0200`). See :ref:`WBEM operations` for a list of all
        methods performing such operations.

        The `PropertyList` parameter determines the set of properties that are
        designated to be modified (see its description for details).

        The properties provided in the `ModifiedInstance` parameter specify
        the new property values for the properties that are designated to be
        modified.

        Pywbem sends the property values provided in the `ModifiedInstance`
        parameter to the WBEM server as provided; it does not add any default
        values for properties not provided but designated to be modified, nor
        does it reduce the properties by those not designated to be modified.

        The properties that are actually modified by the WBEM server as a result
        of this operation depend on a number of things:

        * The WBEM server will reject modification requests for key properties
          and for properties that are not exposed by the creation class of the
          target instance.

        * The WBEM server may consider some properties as read-only, as a
          result of requirements at the CIM modeling level (schema or
          management profiles), or as a result of an implementation decision.

          Note that the WRITE qualifier on a property is not a safe indicator
          as to whether the property can actually be modified. It is an
          expression at the level of the CIM schema that may or may not be
          considered in DMTF management profiles or in implementations.
          Specifically, a qualifier value of True on a property does not
          guarantee modifiability of the property, and a value of False does
          not prevent modifiability.

        * The WBEM server may detect invalid new values or conflicts resulting
          from the new property values and may reject modification of a property
          for such reasons.

        If the WBEM server rejects modification of a property for any reason,
        it will cause this operation to fail and will not modify any property
        on the target instance. If this operation succeeds, all properties
        designated to be modified have their new values (see the description
        of the `ModifiedInstance` parameter for details on how the new values
        are determined).

        Note that properties (including properties not designated to be
        modified) may change their values as an indirect result of this
        operation. For example, a property that was not designated to be
        modified may be derived from another property that was modified, and
        may show a changed value due to that.

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
            values (including `None` for NULL). If a property is designated to
            be modified but is not specified in this object, the WBEM server
            will use the default value of the property declaration if specified
            (including `None`), and otherwise may update the property to any
            value (including `None`).

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
            cannot rely on qualifiers to be modified.

          PropertyList (:term:`string` or :term:`py:iterable` of :term:`string`):
            This parameter defines which properties are designated to be
            modified.

            This parameter is an iterable specifying the names of the
            properties, or a string that specifies a single property name. In
            all cases, the property names are matched case insensitively.
            The specified properties are designated to be modified. Properties
            not specified are not designated to be modified.

            An empty iterable indicates that no properties are designated to be
            modified.

            If `None`, DSP0200 states that the properties with values different
            from the current values in the instance are designated to be
            modified, but for all practical purposes this is equivalent to
            stating that all properties exposed by the instance are designated
            to be modified.

          **extra :
            Additional keyword arguments are passed as additional operation
            parameters to the WBEM server.
            Note that :term:`DSP0200` does not define any additional parameters
            for this operation.

        Raises:

            Exceptions described in :class:`~pywbem.WBEMConnection`.
        """  # noqa: E501

        exc = None
        method_name = 'ModifyInstance'

        if self._operation_recorders:
            self.operation_recorder_reset()
            self.operation_recorder_stage_pywbem_args(
                method=method_name,
                ModifiedInstance=ModifiedInstance,
                IncludeQualifiers=IncludeQualifiers,
                PropertyList=PropertyList,
                **extra)

        try:

            stats = self.statistics.start_timer('ModifyInstance')
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
                method_name,
                namespace,
                ModifiedInstance=instance,
                IncludeQualifiers=IncludeQualifiers,
                PropertyList=PropertyList,
                has_return_value=False,
                **extra)
            return

        except (CIMXMLParseError, XMLParseError) as exce:
            exce.request_data = self.last_raw_request
            exce.response_data = self.last_raw_reply
            exc = exce
            raise
        except Exception as exce:
            exc = exce
            raise
        finally:
            self._last_operation_time = stats.stop_timer(
                self.last_request_len, self.last_reply_len,
                self.last_server_response_time, exc)
            if self._operation_recorders:
                self.operation_recorder_stage_result(None, exc)

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

            *New in pywbem 0.9.*

            If `None`, defaults to the namespace in the `path` attribute of the
            `NewInstance` parameter, or to the default namespace of the
            connection.

            Leading and trailing slash characters will be stripped. The lexical
            case will be preserved.

          **extra :
            Additional keyword arguments are passed as additional operation
            parameters to the WBEM server.
            Note that :term:`DSP0200` does not define any additional parameters
            for this operation.

        Returns:

            A :class:`~pywbem.CIMInstanceName` object that is the instance
            path of the new instance, with classname, keybindings and
            namespace set.

        Raises:

            Exceptions described in :class:`~pywbem.WBEMConnection`.
        """

        exc = None
        instancename = None
        method_name = 'CreateInstance'

        if self._operation_recorders:
            self.operation_recorder_reset()
            self.operation_recorder_stage_pywbem_args(
                method=method_name,
                NewInstance=NewInstance,
                namespace=namespace,
                **extra)

        try:

            stats = self.statistics.start_timer(method_name)
            if namespace is None and \
               getattr(NewInstance.path, 'namespace', None) is not None:
                namespace = NewInstance.path.namespace
            namespace = self._iparam_namespace_from_namespace(namespace)

            instance = NewInstance.copy()

            # Strip off path to avoid producing a VALUE.NAMEDINSTANCE element
            # instead of the desired INSTANCE element.
            instance.path = None

            result = self._imethodcall(
                method_name,
                namespace,
                NewInstance=instance,
                **extra)

            if result is None:
                raise CIMXMLParseError(
                    "Expecting a child element below IMETHODRESPONSE, "
                    "got no child elements", conn_id=self.conn_id)
            result = result[0][2]  # List of children of IRETURNVALUE

            if not result:
                raise CIMXMLParseError(
                    "Expecting a child element below IRETURNVALUE, "
                    "got no child elements", conn_id=self.conn_id)
            instancename = result[0]  # CIMInstanceName object

            if not isinstance(instancename, CIMInstanceName):
                raise CIMXMLParseError(
                    _format("Expecting CIMInstanceName object in result, got "
                            "{0} object", instancename.__class__.__name__),
                    conn_id=self.conn_id)

            # The CreateInstance CIM-XML operation returns an INSTANCENAME
            # element, so the resulting CIMInstanceName object does not have
            # namespace or host. We want to return an instance path with
            # namespace, so we set it to the effective target namespace.
            instancename.namespace = namespace

            return instancename

        except (CIMXMLParseError, XMLParseError) as exce:
            exce.request_data = self.last_raw_request
            exce.response_data = self.last_raw_reply
            exc = exce
            raise
        except Exception as exce:
            exc = exce
            raise
        finally:
            self._last_operation_time = stats.stop_timer(
                self.last_request_len, self.last_reply_len,
                self.last_server_response_time, exc)
            if self._operation_recorders:
                self.operation_recorder_stage_result(instancename, exc)

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

          **extra :
            Additional keyword arguments are passed as additional operation
            parameters to the WBEM server.
            Note that :term:`DSP0200` does not define any additional parameters
            for this operation.

        Raises:

            Exceptions described in :class:`~pywbem.WBEMConnection`.
        """

        exc = None
        method_name = 'DeleteInstance'

        if self._operation_recorders:
            self.operation_recorder_reset()
            self.operation_recorder_stage_pywbem_args(
                method=method_name,
                InstanceName=InstanceName,
                **extra)

        try:

            stats = self.statistics.start_timer(method_name)
            namespace = self._iparam_namespace_from_objectname(InstanceName)
            instancename = self._iparam_instancename(InstanceName)

            self._imethodcall(
                method_name,
                namespace,
                InstanceName=instancename,
                has_return_value=False,
                **extra)
            return

        except (CIMXMLParseError, XMLParseError) as exce:
            exce.request_data = self.last_raw_request
            exce.response_data = self.last_raw_reply
            exc = exce
            raise
        except Exception as exce:
            exc = exce
            raise
        finally:
            self._last_operation_time = stats.stop_timer(
                self.last_request_len, self.last_reply_len,
                self.last_server_response_time, exc)
            if self._operation_recorders:
                self.operation_recorder_stage_result(None, exc)

    def Associators(self, ObjectName, AssocClass=None, ResultClass=None,
                    Role=None, ResultRole=None, IncludeQualifiers=None,
                    IncludeClassOrigin=None, PropertyList=None, **extra):
        # pylint: disable=invalid-name, line-too-long
        """
        Retrieve the instances associated to a source instance, or the classes
        associated to a source class.

        This method performs the Associators operation
        (see :term:`DSP0200`). See :ref:`WBEM operations` for a list of all
        methods performing such operations.

        If the operation succeeds, this method returns.
        Otherwise, this method raises an exception.

        Parameters:

          ObjectName:
            The object path of the source object, selecting instance-level or
            class-level use of this operation, as follows:

            * For selecting instance-level use: The instance path of the
              source instance, as a :class:`~pywbem.CIMInstanceName` object.
              If this object does not specify a namespace, the default namespace
              of the connection is used.
              Its `host` attribute will be ignored.

            * For selecting class-level use: The class path of the source
              class, as a :term:`string` or :class:`~pywbem.CIMClassName` object:

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
            cannot rely on qualifiers to be returned in this operation.

          IncludeClassOrigin (:class:`py:bool`):
            Indicates that class origin information is to be included on each
            property or method in the returned instances (or classes), as
            follows:

            * If `False`, class origin information is not included.
            * If `True`, class origin information is included.
            * If `None`, this parameter is not passed to the WBEM server, and
              causes the server-implemented default to be used. :term:`DSP0200`
              defines that the server-implemented default is `False`.

            This parameter has been deprecated in :term:`DSP0200` for
            instance-level use. WBEM servers may either implement this
            parameter as specified, or may treat any specified value as `False`.

          PropertyList (:term:`string` or :term:`py:iterable` of :term:`string`):
            An iterable specifying the names of the properties (or a string
            that defines a single property) to be included in the returned
            instances (or classes) (case independent).

            An empty iterable indicates to include no properties.

            If `None`, all properties are included.

          **extra :
            Additional keyword arguments are passed as additional operation
            parameters to the WBEM server.
            Note that :term:`DSP0200` does not define any additional parameters
            for this operation.

        Returns:

            : The returned list of objects depend on the usage:

            * For instance-level use: A list of
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

            * For class-level use: A list of :func:`py:tuple` of
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
                class, with its `path` attribute set to the `classpath` tuple
                item.

        Raises:

            Exceptions described in :class:`~pywbem.WBEMConnection`.
        """  # noqa: E501

        exc = None
        objects = None
        method_name = 'Associators'

        if self._operation_recorders:
            self.operation_recorder_reset()
            self.operation_recorder_stage_pywbem_args(
                method=method_name,
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

            stats = self.statistics.start_timer(method_name)
            namespace = self._iparam_namespace_from_objectname(ObjectName)
            objectname = self._iparam_objectname(ObjectName)
            PropertyList = _iparam_propertylist(PropertyList)

            result = self._imethodcall(
                method_name,
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

            # instance-level invocation: list of CIMInstance
            # class-level invocation: list of CIMClass
            if result is None:
                objects = []
            else:
                objects = [x[2] for x in result[0][2]]

            if isinstance(objectname, CIMInstanceName):
                # instance-level invocation
                for instance in objects:
                    if not isinstance(instance, CIMInstance):
                        raise CIMXMLParseError(
                            _format("Expecting CIMInstance object in result "
                                    "list, got {0} object",
                                    instance.__class__.__name__),
                            conn_id=self.conn_id)
                    # path and namespace are already set
            else:
                # class-level invocation
                for classpath, klass in objects:
                    if not isinstance(classpath, CIMClassName) or \
                            not isinstance(klass, CIMClass):
                        raise CIMXMLParseError(
                            _format("Expecting tuple (CIMClassName, CIMClass) "
                                    "in result list, got tuple ({0}, {1})",
                                    classpath.__class__.__name__,
                                    klass.__class__.__name__),
                            conn_id=self.conn_id)
                    # path and namespace are already set

            return objects

        except (CIMXMLParseError, XMLParseError) as exce:
            exce.request_data = self.last_raw_request
            exce.response_data = self.last_raw_reply
            exc = exce
            raise
        except Exception as exce:
            exc = exce
            raise
        finally:
            self._last_operation_time = stats.stop_timer(
                self.last_request_len, self.last_reply_len,
                self.last_server_response_time, exc)
            if self._operation_recorders:
                self.operation_recorder_stage_result(objects, exc)

    def AssociatorNames(self, ObjectName, AssocClass=None, ResultClass=None,
                        Role=None, ResultRole=None, **extra):
        # pylint: disable=invalid-name, line-too-long
        """
        Retrieve the instance paths of the instances associated to a source
        instance, or the class paths of the classes associated to a source
        class.

        This method performs the AssociatorNames operation
        (see :term:`DSP0200`). See :ref:`WBEM operations` for a list of all
        methods performing such operations.

        If the operation succeeds, this method returns.
        Otherwise, this method raises an exception.

        Parameters:

          ObjectName:
            The object path of the source object, selecting instance-level or
            class-level use of this operation, as follows:

            * For selecting instance-level use: The instance path of the
              source instance, as a :class:`~pywbem.CIMInstanceName` object.
              If this object does not specify a namespace, the default namespace
              of the connection is used.
              Its `host` attribute will be ignored.

            * For selecting class-level use: The class path of the source
              class, as a :term:`string` or :class:`~pywbem.CIMClassName`
              object:

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

          **extra :
            Additional keyword arguments are passed as additional operation
            parameters to the WBEM server.
            Note that :term:`DSP0200` does not define any additional parameters
            for this operation.

        Returns:

            : The returned list of objects depend on the usage:

            * For instance-level use: A list of
              :class:`~pywbem.CIMInstanceName` objects that are the instance
              paths of the associated instances, with their attributes set as
              follows:

              * `classname`: Name of the creation class of the instance.
              * `keybindings`: Keybindings of the instance.
              * `namespace`: Name of the CIM namespace containing the instance.
              * `host`: Host and optionally port of the WBEM server containing
                the CIM namespace, or `None` if the server did not return host
                information.

            * For class-level use: A list of :class:`~pywbem.CIMClassName`
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
        exc = None
        objects = None
        method_name = 'AssociatorNames'

        if self._operation_recorders:
            self.operation_recorder_reset()
            self.operation_recorder_stage_pywbem_args(
                method=method_name,
                ObjectName=ObjectName,
                AssocClass=AssocClass,
                ResultClass=ResultClass,
                Role=Role,
                ResultRole=ResultRole,
                **extra)

        try:

            stats = self.statistics.start_timer(method_name)
            namespace = self._iparam_namespace_from_objectname(ObjectName)
            objectname = self._iparam_objectname(ObjectName)

            result = self._imethodcall(
                method_name,
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

            if isinstance(objectname, CIMInstanceName):
                # instance-level invocation
                for instancepath in objects:
                    if not isinstance(instancepath, CIMInstanceName):
                        raise CIMXMLParseError(
                            _format("Expecting CIMInstanceName object in "
                                    "result list, got {0} object",
                                    instancepath.__class__.__name__),
                            conn_id=self.conn_id)
                    # namespace is already set
            else:
                # class-level invocation
                for classpath in objects:
                    if not isinstance(classpath, CIMClassName):
                        raise CIMXMLParseError(
                            _format("Expecting CIMClassName object in result "
                                    "list, got {0} object",
                                    classpath.__class__.__name__),
                            conn_id=self.conn_id)
                    # namespace is already set

            return objects

        except (CIMXMLParseError, XMLParseError) as exce:
            exce.request_data = self.last_raw_request
            exce.response_data = self.last_raw_reply
            exc = exce
            raise
        except Exception as exce:
            exc = exce
            raise
        finally:
            self._last_operation_time = stats.stop_timer(
                self.last_request_len, self.last_reply_len,
                self.last_server_response_time, exc)
            if self._operation_recorders:
                self.operation_recorder_stage_result(objects, exc)

    def References(self, ObjectName, ResultClass=None, Role=None,
                   IncludeQualifiers=None, IncludeClassOrigin=None,
                   PropertyList=None, **extra):
        # pylint: disable=invalid-name, line-too-long
        """
        Retrieve the association instances that reference a source instance,
        or the association classes that reference a source class.

        This method performs the References operation
        (see :term:`DSP0200`). See :ref:`WBEM operations` for a list of all
        methods performing such operations.

        If the operation succeeds, this method returns.
        Otherwise, this method raises an exception.

        Parameters:

          ObjectName:
            The object path of the source object, selecting instance-level or
            class-level use of this operation, as follows:

            * For selecting instance-level use: The instance path of the
              source instance, as a :class:`~pywbem.CIMInstanceName` object.
              If this object does not specify a namespace, the default namespace
              of the connection is used.
              Its `host` attribute will be ignored.

            * For selecting class-level use: The class path of the source
              class, as a :term:`string` or :class:`~pywbem.CIMClassName` object:

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
            cannot rely on qualifiers to be returned in this operation.

          IncludeClassOrigin (:class:`py:bool`):
            Indicates that class origin information is to be included on each
            property or method in the returned instances (or classes), as
            follows:

            * If `False`, class origin information is not included.
            * If `True`, class origin information is included.
            * If `None`, this parameter is not passed to the WBEM server, and
              causes the server-implemented default to be used. :term:`DSP0200`
              defines that the server-implemented default is `False`.

            This parameter has been deprecated in :term:`DSP0200` for
            instance-level use. WBEM servers may either implement this
            parameter as specified, or may treat any specified value as `False`.

          PropertyList (:term:`string` or :term:`py:iterable` of :term:`string`):
            An iterable specifying the names of the properties (or a string
            that defines a single property) to be included in the returned
            instances (or classes) (case independent).

            An empty iterable indicates to include no properties.

            If `None`, all properties are included.

          **extra :
            Additional keyword arguments are passed as additional operation
            parameters to the WBEM server.
            Note that :term:`DSP0200` does not define any additional parameters
            for this operation.

        Returns:

            : The returned list of objects depend on the usage:

            * For instance-level use: A list of
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

            * For class-level use: A list of :func:`py:tuple` of
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
                class, with its `path` attribute set to the `classpath` tuple
                item.

        Raises:

            Exceptions described in :class:`~pywbem.WBEMConnection`.
        """  # noqa: E501

        exc = None
        objects = None
        method_name = 'References'

        if self._operation_recorders:
            self.operation_recorder_reset()
            self.operation_recorder_stage_pywbem_args(
                method=method_name,
                ObjectName=ObjectName,
                ResultClass=ResultClass,
                Role=Role,
                IncludeQualifiers=IncludeQualifiers,
                IncludeClassOrigin=IncludeClassOrigin,
                PropertyList=PropertyList,
                **extra)

        try:

            stats = self.statistics.start_timer(method_name)
            namespace = self._iparam_namespace_from_objectname(ObjectName)
            objectname = self._iparam_objectname(ObjectName)
            PropertyList = _iparam_propertylist(PropertyList)

            result = self._imethodcall(
                method_name,
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

            if isinstance(objectname, CIMInstanceName):
                # instance-level invocation
                for instance in objects:
                    if not isinstance(instance, CIMInstance):
                        raise CIMXMLParseError(
                            _format("Expecting CIMInstance object in result "
                                    "list, got {0} object",
                                    instance.__class__.__name__),
                            conn_id=self.conn_id)
                    # path and namespace are already set
            else:
                # class-level invocation
                for classpath, klass in objects:
                    if not isinstance(classpath, CIMClassName) or \
                            not isinstance(klass, CIMClass):
                        raise CIMXMLParseError(
                            _format("Expecting tuple (CIMClassName, CIMClass) "
                                    "in result list, got tuple ({0}, {1})",
                                    classpath.__class__.__name__,
                                    klass.__class__.__name__),
                            conn_id=self.conn_id)
                    # path and namespace are already set

            return objects

        except (CIMXMLParseError, XMLParseError) as exce:
            exce.request_data = self.last_raw_request
            exce.response_data = self.last_raw_reply
            exc = exce
            raise
        except Exception as exce:
            exc = exce
            raise
        finally:
            self._last_operation_time = stats.stop_timer(
                self.last_request_len, self.last_reply_len,
                self.last_server_response_time, exc)
            if self._operation_recorders:
                self.operation_recorder_stage_result(objects, exc)

    def ReferenceNames(self, ObjectName, ResultClass=None, Role=None, **extra):
        # pylint: disable=invalid-name, line-too-long
        """
        Retrieve the instance paths of the association instances that reference
        a source instance, or the class paths of the association classes that
        reference a source class.

        This method performs the ReferenceNames operation
        (see :term:`DSP0200`). See :ref:`WBEM operations` for a list of all
        methods performing such operations.

        If the operation succeeds, this method returns.
        Otherwise, this method raises an exception.

        Parameters:

          ObjectName:
            The object path of the source object, selecting instance-level or
            class-level use of this operation, as follows:

            * For selecting instance-level use: The instance path of the
              source instance, as a :class:`~pywbem.CIMInstanceName` object.
              If this object does not specify a namespace, the default namespace
              of the connection is used.
              Its `host` attribute will be ignored.

            * For selecting class-level use: The class path of the source
              class, as a :term:`string` or :class:`~pywbem.CIMClassName`
              object:

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

          **extra :
            Additional keyword arguments are passed as additional operation
            parameters to the WBEM server.
            Note that :term:`DSP0200` does not define any additional parameters
            for this operation.

        Returns:

            : The returned list of objects depend on the usage:

            * For instance-level use: A list of
              :class:`~pywbem.CIMInstanceName` objects that are the instance
              paths of the referencing association instances, with their
              attributes set as follows:

              * `classname`: Name of the creation class of the instance.
              * `keybindings`: Keybindings of the instance.
              * `namespace`: Name of the CIM namespace containing the instance.
              * `host`: Host and optionally port of the WBEM server containing
                the CIM namespace, or `None` if the server did not return host
                information.

            * For class-level use: A list of :class:`~pywbem.CIMClassName`
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

        exc = None
        objects = None
        method_name = 'ReferenceNames'

        if self._operation_recorders:
            self.operation_recorder_reset()
            self.operation_recorder_stage_pywbem_args(
                method=method_name,
                ObjectName=ObjectName,
                ResultClass=ResultClass,
                Role=Role,
                **extra)

        try:

            stats = self.statistics.start_timer(method_name)
            namespace = self._iparam_namespace_from_objectname(ObjectName)
            objectname = self._iparam_objectname(ObjectName)

            result = self._imethodcall(
                method_name,
                namespace,
                ObjectName=objectname,
                ResultClass=self._iparam_classname(ResultClass),
                Role=Role,
                **extra)

            if result is None:
                objects = []
            else:
                objects = [x[2] for x in result[0][2]]

            if isinstance(objectname, CIMInstanceName):
                # instance-level invocation
                for instancepath in objects:
                    if not isinstance(instancepath, CIMInstanceName):
                        raise CIMXMLParseError(
                            _format("Expecting CIMInstanceName object in "
                                    "result list, got {0} object",
                                    instancepath.__class__.__name__),
                            conn_id=self.conn_id)
                    # namespace is already set
            else:
                # class-level invocation
                for classpath in objects:
                    if not isinstance(classpath, CIMClassName):
                        raise CIMXMLParseError(
                            _format("Expecting CIMClassName object in result "
                                    "list, got {0} object",
                                    classpath.__class__.__name__),
                            conn_id=self.conn_id)
                    # namespace is already set

            return objects

        except (CIMXMLParseError, XMLParseError) as exce:
            exce.request_data = self.last_raw_request
            exce.response_data = self.last_raw_reply
            exc = exce
            raise
        except Exception as exce:
            exc = exce
            raise
        finally:
            self._last_operation_time = stats.stop_timer(
                self.last_request_len, self.last_reply_len,
                self.last_server_response_time, exc)
            if self._operation_recorders:
                self.operation_recorder_stage_result(objects, exc)

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
        parameters specified in `Params` (preserving their order), followed by
        the set of keyword parameters (not preserving their order). There is no
        checking for duplicate parameter names.

        Parameters:

          MethodName (:term:`string`):
            Name of the method to be invoked (case independent).

          ObjectName:
            The object path of the target object, as follows:

            * For instance-level use: The instance path of the target
              instance, as a :class:`~pywbem.CIMInstanceName` object.
              If this object does not specify a namespace, the default namespace
              of the connection is used.
              Its `host` attribute will be ignored.

            * For class-level use: The class path of the target class, as a
              :term:`string` or :class:`~pywbem.CIMClassName` object:

              If specified as a string, the string is interpreted as a class
              name in the default namespace of the connection
              (case independent).

              If specified as a :class:`~pywbem.CIMClassName` object, its `host`
              attribute will be ignored. If this object does not specify
              a namespace, the default namespace of the connection is used.

          Params (:term:`py:iterable`):
            An iterable of input parameter values for the CIM method. Each item
            in the iterable is a single parameter value and can be any of:

            * :class:`~pywbem.CIMParameter` representing a parameter value. The
              `name`, `value`, `type` and `embedded_object` attributes of this
              object are used.

            * tuple of name, value, with:

                - name (:term:`string`): Parameter name (case independent)
                - value (:term:`CIM data type`): Parameter value

          **params :
            Each keyword parameter is an additional input parameter value for
            the CIM method, with:

            * key (:term:`string`): Parameter name (case independent)
            * value (:term:`CIM data type`): Parameter value

        Returns:

            A :func:`py:tuple` of (returnvalue, outparams), with these
            tuple items:

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

        exc = None
        result_tuple = None

        if self._operation_recorders:
            self.operation_recorder_reset()
            self.operation_recorder_stage_pywbem_args(
                method='InvokeMethod',
                MethodName=MethodName,
                ObjectName=ObjectName,
                Params=Params,
                **params)

        try:

            stats = self.statistics.start_timer('InvokeMethod')

            # Make the method call
            result = self._methodcall(MethodName, ObjectName, Params, **params)

            return result

        except (CIMXMLParseError, XMLParseError) as exce:
            exce.request_data = self.last_raw_request
            exce.response_data = self.last_raw_reply
            exc = exce
            raise
        except Exception as exce:
            exc = exce
            raise
        finally:
            self._last_operation_time = stats.stop_timer(
                self.last_request_len, self.last_reply_len,
                self.last_server_response_time, exc)
            if self._operation_recorders:
                self.operation_recorder_stage_result(result_tuple, exc)

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

            Leading and trailing slash characters will be stripped. The lexical
            case will be preserved.

            If `None`, the default namespace of the connection object will be
            used.

          **extra :
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

        exc = None
        instances = None
        method_name = 'ExecQuery'

        if self._operation_recorders:
            self.operation_recorder_reset()
            self.operation_recorder_stage_pywbem_args(
                method=method_name,
                QueryLanguage=QueryLanguage,
                Query=Query,
                namespace=namespace,
                **extra)

        try:

            stats = self.statistics.start_timer(method_name)
            namespace = self._iparam_namespace_from_namespace(namespace)

            result = self._imethodcall(
                method_name,
                namespace,
                QueryLanguage=QueryLanguage,
                Query=Query,
                **extra)

            if result is None:
                instances = []
            else:
                instances = [x[2] for x in result[0][2]]

            for instance in instances:

                # The ExecQuery CIM-XML operation returns instances as any of
                # (VALUE.OBJECT | VALUE.OBJECTWITHLOCALPATH |
                # VALUE.OBJECTWITHPATH), i.e. classes or instances with or
                # without path which may or may not contain a namespace.

                # TODO: Fix current impl. that assumes instance with path.
                instance.path.namespace = namespace

            return instances

        except (CIMXMLParseError, XMLParseError) as exce:
            exce.request_data = self.last_raw_request
            exce.response_data = self.last_raw_reply
            exc = exce
            raise
        except Exception as exce:
            exc = exce
            raise
        finally:
            self._last_operation_time = stats.stop_timer(
                self.last_request_len, self.last_reply_len,
                self.last_server_response_time, exc)
            if self._operation_recorders:
                self.operation_recorder_stage_result(instances, exc)

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
        Enumerate the instances of a class (including instances of its
        subclasses) in a namespace, using the Python :term:`py:generator`
        idiom to return the result.

        *New in pywbem 0.10 as experimental and finalized in 0.12.*

        This method uses the corresponding pull operations if supported by the
        WBEM server or otherwise the corresponding traditional operation.
        This method is an alternative to using the pull operations directly,
        that frees the user of having to know whether the WBEM server supports
        pull operations.

        This method is a generator function that retrieves instances from
        the WBEM server and returns them one by one (using :keyword:`yield`)
        when the caller iterates through the returned generator object. The
        number of instances that are retrieved from the WBEM server in one
        request (and thus need to be materialized in this method) is up to the
        `MaxObjectCount` parameter if the corresponding pull operations are
        used, or the complete result set all at once if the corresponding
        traditional operation is used.

        By default, this method attempts to perform the corresponding pull
        operations
        (:meth:`~pywbem.WBEMConnection.OpenEnumerateInstances` and
        :meth:`~pywbem.WBEMConnection.PullInstancesWithPath`).
        If these pull operations are not supported by the WBEM server, this
        method falls back to using the corresponding traditional operation
        (:meth:`~pywbem.WBEMConnection.EnumerateInstances`).
        Whether the WBEM server supports these pull operations is remembered
        in the :class:`~pywbem.WBEMConnection` object (by operation type), and
        avoids unnecessary attempts to try these pull operations on that
        connection in the future.
        The `use_pull_operations` init parameter of
        :class:`~pywbem.WBEMConnection` can be used to control the preference
        for always using pull operations, always using traditional operations,
        or using pull operations if supported by the WBEM server (the default).

        This method provides all of the controls of the corresponding pull
        operations except for the ability to set different response sizes on
        each request; the response size (defined by the `MaxObjectCount`
        parameter) is the same for all pull operations in the enumeration
        session.

        In addition, some functionality is only available if the corresponding
        pull operations are used by this method:

        * Filtering is not supported for the corresponding traditional
          operation so that setting the `FilterQuery` or `FilterQueryLanguage`
          parameters will be rejected if the corresponding traditional
          operation is used by this method.

          Note that this limitation is not a disadvantage compared to using the
          corresponding pull operations directly, because in both cases, the
          WBEM server must support the pull operations and their filtering
          capability in order for the filtering to work.

        * Setting the `ContinueOnError` parameter to `True` will be rejected if
          the corresponding traditional operation is used by this method.

        The enumeration session that is opened with the WBEM server when using
        pull operations is closed automatically when the returned generator
        object is exhausted, or when the generator object is closed using its
        :meth:`~py:generator.close` method (which may also be called before the
        generator is exhausted).

        Parameters:

          ClassName (:term:`string` or :class:`~pywbem.CIMClassName`):
            Name of the class to be enumerated (case independent).
            If specified as a :class:`~pywbem.CIMClassName` object, its
            `namespace` attribute will be used as a default namespace as
            described for the `namespace` parameter, and its `host` attribute
            will be ignored.

          namespace (:term:`string`):
            Name of the CIM namespace to be used (case independent).

            Leading and trailing slash characters will be stripped. The lexical
            case will be preserved.

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
            cannot rely on qualifiers to be returned in this operation.

          IncludeClassOrigin (:class:`py:bool`):
            Indicates that class origin information is to be included on each
            property in the returned instances, as follows:

            * If `False`, class origin information is not included.
            * If `True`, class origin information is included.
            * If `None`, this parameter is not passed to the WBEM server, and
              causes the server-implemented default to be used. :term:`DSP0200`
              defines that the server-implemented default is `False`.

            This parameter has been deprecated in :term:`DSP0200`. WBEM servers
            may either implement this parameter as specified, or may treat any
            specified value as `False`.

          PropertyList (:term:`string` or :term:`py:iterable` of :term:`string`):
            An iterable specifying the names of the properties (or a string
            that defines a single property) to be included in the returned
            instances (case independent).

            An empty iterable indicates to include no properties.

            If `None`, all properties are included.

          FilterQueryLanguage (:term:`string`):
            The name of the filter query language used for the `FilterQuery`
            parameter. The DMTF-defined Filter Query Language (see
            :term:`DSP0212`) is specified as "DMTF:FQL".

            If this parameter is not `None` and the traditional operation is
            used by this method, :exc:`~py:exceptions.ValueError` will be
            raised.

          FilterQuery (:term:`string`):
            The filter query in the query language defined by the
            `FilterQueryLanguage` parameter.

            If this parameter is not `None` and the traditional operation is
            used by this method, :exc:`~py:exceptions.ValueError` will be
            raised.

          OperationTimeout (:class:`~pywbem.Uint32`):
            Minimum time in seconds the WBEM Server shall maintain an open
            enumeration session after a previous Open or pull request is
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
              If the corresponding traditional operation is used by this
              method, :exc:`~py:exceptions.ValueError` will be raised.
            * If `False`, the server is requested to close the enumeration after
              sending an error response.
            * If `None`, this parameter is not passed to the WBEM server, and
              causes the server-implemented default behaviour to be used.
              :term:`DSP0200` defines that the server-implemented default is
              `False`.

          MaxObjectCount (:class:`~pywbem.Uint32`)
            Maximum number of instances the WBEM server may return for each of
            the open and pull requests issued during the iterations over the
            returned generator object.

            * If positive, the WBEM server is to return no more than the
              specified number of instances.
            * Zero is not allowed; it would mean that zero instances
              are to be returned for open and all pull requests issued to the
              server.
            * The default is defined as a system config variable.
            * `None` is not allowed.

            The choice of MaxObjectCount is client/server dependent but choices
            between 100 and 1000 typically do not have a significant impact on
            either memory or overall efficiency.

          **extra :
            Additional keyword arguments are passed as additional operation
            parameters to the WBEM server.
            Note that :term:`DSP0200` does not define any additional parameters
            for this operation.

        Raises:

            Exceptions described in :class:`~pywbem.WBEMConnection`.

            ValueError: Invalid parameters provided.

        Returns:

          :term:`py:generator` iterating :class:`~pywbem.CIMInstance`:
          A generator object that iterates the resulting CIM instances.
          These instances include an instance path that has its host and
          namespace components set.

        Example::

            insts_generator = conn.IterEnumerateInstances('CIM_Blah')
            for inst in insts_generator:
                # close if a particular property value found
                if inst.get('thisPropertyName') == 0
                    insts_generator.close()
                    break
                else:
                    print('instance {0}'.format(inst.tomof()))
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
        Enumerate the instance paths of instances of a class (including
        instances of its subclasses) in a namespace, using the
        Python :term:`py:generator` idiom to return the result.

        *New in pywbem 0.10 as experimental and finalized in 0.12.*

        This method uses the corresponding pull operations if supported by the
        WBEM server or otherwise the corresponding traditional operation.

        This method is an alternative to using the pull operations directly,
        that frees the user of having to know whether the WBEM server supports
        pull operations.

        This method is a generator function that retrieves instance paths from
        the WBEM server and returns them one by one (using :keyword:`yield`)
        when the caller iterates through the returned generator object. The
        number of instance paths that are retrieved from the WBEM server in one
        request (and thus need to be materialized in this method) is up to the
        `MaxObjectCount` parameter if the corresponding pull operations are
        used, or the complete result set all at once if the corresponding
        traditional operation is used.

        By default, this method attempts to perform the corresponding pull
        operations
        (:meth:`~pywbem.WBEMConnection.OpenEnumerateInstancePaths` and
        :meth:`~pywbem.WBEMConnection.PullInstancePaths`).
        If these pull operations are not supported by the WBEM server, this
        method falls back to using the corresponding traditional operation
        (:meth:`~pywbem.WBEMConnection.EnumerateInstanceNames`).
        Whether the WBEM server supports these pull operations is remembered
        in the :class:`~pywbem.WBEMConnection` object (by operation type), and
        avoids unnecessary attempts to try these pull operations on that
        connection in the future.
        The `use_pull_operations` init parameter of
        :class:`~pywbem.WBEMConnection` can be used to control the preference
        for always using pull operations, always using traditional operations,
        or using pull operations if supported by the WBEM server (the default).

        This method provides all of the controls of the corresponding pull
        operations except for the ability to set different response sizes on
        each request; the response size (defined by the `MaxObjectCount`
        parameter) is the same for all pull operations in the enumeration
        session.

        In addition, some functionality is only available if the corresponding
        pull operations are used by this method:

        * Filtering is not supported for the corresponding traditional
          operation so that setting the `FilterQuery` or `FilterQueryLanguage`
          parameters will be rejected if the corresponding traditional
          operation is used by this method.

          Note that this limitation is not a disadvantage compared to using the
          corresponding pull operations directly, because in both cases, the
          WBEM server must support the pull operations and their filtering
          capability in order for the filtering to work.

        * Setting the `ContinueOnError` parameter to `True` will be rejected if
          the corresponding traditional operation is used by this method.

        The enumeration session that is opened with the WBEM server when using
        pull operations is closed automatically when the returned generator
        object is exhausted, or when the generator object is closed using its
        :meth:`~py:generator.close` method (which may also be called before the
        generator is exhausted).

        Parameters:

          ClassName (:term:`string` or :class:`~pywbem.CIMClassName`):
            Name of the class to be enumerated (case independent).
            If specified as a :class:`~pywbem.CIMClassName` object, its
            `namespace` attribute will be used as a default namespace as
            described for the `namespace` parameter, and its `host` attribute
            will be ignored.

          namespace (:term:`string`):
            Name of the CIM namespace to be used (case independent).

            Leading and trailing slash characters will be stripped. The lexical
            case will be preserved.

            If `None`, the namespace of the `ClassName` parameter will be used,
            if specified as a :class:`~pywbem.CIMClassName` object. If that is
            also `None`, the default namespace of the connection will be used.

          FilterQueryLanguage (:term:`string`):
            The name of the filter query language used for the `FilterQuery`
            parameter. The DMTF-defined Filter Query Language (see
            :term:`DSP0212`) is specified as "DMTF:FQL".

            If this parameter is not `None` and the traditional operation is
            used by this method, :exc:`~py:exceptions.ValueError` will be
            raised.

            Not all WBEM servers support filtering for this operation because
            it returns instance paths and the act of the server filtering
            requires that it generate instances just for that purpose and then
            discard them.

          FilterQuery (:term:`string`):
            The filter query in the query language defined by the
            `FilterQueryLanguage` parameter.

            If this parameter is not `None` and the traditional operation is
            used by this method, :exc:`~py:exceptions.ValueError` will be
            raised.

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
              If the corresponding traditional operation is used by this
              method, :exc:`~py:exceptions.ValueError` will be raised.
            * If `False`, the server is requested to close the enumeration after
              sending an error response.
            * If `None`, this parameter is not passed to the WBEM server, and
              causes the server-implemented default behaviour to be used.
              :term:`DSP0200` defines that the server-implemented default is
              `False`.

          MaxObjectCount (:class:`~pywbem.Uint32`)
            Maximum number of instances the WBEM server may return for each of
            the open and pull requests issued during the iterations over the
            returned generator object.

            * If positive, the WBEM server is to return no more than the
              specified number of instance paths.
            * Zero is not allowed; it would mean that zero paths
              are to be returned for every request issued.
            * The default is defined as a system config variable.
            * `None` is not allowed.

            The choice of MaxObjectCount is client/server dependent but choices
            between 100 and 1000 typically do not have a significant impact on
            either memory or overall efficiency.

          **extra :
            Additional keyword arguments are passed as additional operation
            parameters to the WBEM server.
            Note that :term:`DSP0200` does not define any additional parameters
            for this operation.

        Raises:

            Exceptions described in :class:`~pywbem.WBEMConnection`.

        Returns:

          :term:`py:generator` iterating :class:`~pywbem.CIMInstanceName`:
          A generator object that iterates the resulting CIM instance paths.
          These instance paths have their host and namespace components set.

        Example::

            paths_generator = conn.IterEnumerateInstancePaths('CIM_Blah')
            for path in paths_generator:
                print('path {0}'.format(path))
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

    def IterAssociatorInstances(self, InstanceName, AssocClass=None,
                                ResultClass=None,
                                Role=None, ResultRole=None,
                                IncludeQualifiers=None,
                                IncludeClassOrigin=None, PropertyList=None,
                                FilterQueryLanguage=None, FilterQuery=None,
                                OperationTimeout=None, ContinueOnError=None,
                                MaxObjectCount=DEFAULT_ITER_MAXOBJECTCOUNT,
                                **extra):
        # pylint: disable=invalid-name,line-too-long
        """
        Retrieve the instances associated to a source instance, using the
        Python :term:`py:generator` idiom to return the result.

        *New in pywbem 0.10 as experimental and finalized in 0.12.*

        This method uses the corresponding pull operations if supported by the
        WBEM server or otherwise the corresponding traditional operation.
        This method is an alternative to using the pull operations directly,
        that frees the user of having to know whether the WBEM server supports
        pull operations.

        This method is a generator function that retrieves instances from
        the WBEM server and returns them one by one (using :keyword:`yield`)
        when the caller iterates through the returned generator object. The
        number of instances that are retrieved from the WBEM server in one
        request (and thus need to be materialized in this method) is up to the
        `MaxObjectCount` parameter if the corresponding pull operations are
        used, or the complete result set all at once if the corresponding
        traditional operation is used.

        By default, this method attempts to perform the corresponding pull
        operations
        (:meth:`~pywbem.WBEMConnection.OpenAssociatorInstances` and
        :meth:`~pywbem.WBEMConnection.PullInstancesWithPath`).
        If these pull operations are not supported by the WBEM server, this
        method falls back to using the corresponding traditional operation
        (:meth:`~pywbem.WBEMConnection.Associators`).
        Whether the WBEM server supports these pull operations is remembered
        in the :class:`~pywbem.WBEMConnection` object (by operation type), and
        avoids unnecessary attempts to try these pull operations on that
        connection in the future.
        The `use_pull_operations` init parameter of
        :class:`~pywbem.WBEMConnection` can be used to control the preference
        for always using pull operations, always using traditional operations,
        or using pull operations if supported by the WBEM server (the default).

        This method provides all of the controls of the corresponding pull
        operations except for the ability to set different response sizes on
        each request; the response size (defined by the `MaxObjectCount`
        parameter) is the same for all pull operations in the enumeration
        session.

        In addition, some functionality is only available if the corresponding
        pull operations are used by this method:

        * Filtering is not supported for the corresponding traditional
          operation so that setting the `FilterQuery` or `FilterQueryLanguage`
          parameters will be rejected if the corresponding traditional
          operation is used by this method.

          Note that this limitation is not a disadvantage compared to using the
          corresponding pull operations directly, because in both cases, the
          WBEM server must support the pull operations and their filtering
          capability in order for the filtering to work.

        * Setting the `ContinueOnError` parameter to `True` will be rejected if
          the corresponding traditional operation is used by this method.

        The enumeration session that is opened with the WBEM server when using
        pull operations is closed automatically when the returned generator
        object is exhausted, or when the generator object is closed using its
        :meth:`~py:generator.close` method (which may also be called before the
        generator is exhausted).

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
            cannot rely on qualifiers to be returned in this operation.

          IncludeClassOrigin (:class:`py:bool`):
            Indicates that class origin information is to be included on each
            property or method in the returned instances (or classes), as
            follows:

            * If `False`, class origin information is not included.
            * If `True`, class origin information is included.
            * If `None`, this parameter is not passed to the WBEM server, and
              causes the server-implemented default to be used. :term:`DSP0200`
              defines that the server-implemented default is `False`.

            This parameter has been deprecated in :term:`DSP0200`. WBEM servers
            may either implement this parameter as specified, or may treat any
            specified value as `False`.

          PropertyList (:term:`string` or :term:`py:iterable` of :term:`string`):
            An iterable specifying the names of the properties (or a string
            that defines a single property) to be included in the returned
            instances (case independent).

            An empty iterable indicates to include no properties.

            If `None`, all properties are included.

          FilterQueryLanguage (:term:`string`):
            The name of the filter query language used for the `FilterQuery`
            parameter. The DMTF-defined Filter Query Language (see
            :term:`DSP0212`) is specified as "DMTF:FQL".

            If this parameter is not `None` and the traditional operation is
            used by this method, :exc:`~py:exceptions.ValueError` will be
            raised.

          FilterQuery (:term:`string`):
            The filter query in the query language defined by the
            `FilterQueryLanguage` parameter.

            If this parameter is not `None` and the traditional operation is
            used by this method, :exc:`~py:exceptions.ValueError` will be
            raised.

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

            Many WBEM servers do not support this request attribute so that
            setting it to `True` is NOT recommended except in special cases.

            If this parameter is `True` and the traditional operation is used
            by this method, :exc:`~py:exceptions.ValueError` will be raised.

          ContinueOnError (:class:`py:bool`):
            Indicates to the WBEM server to continue sending responses
            after an error response has been sent.

            * If `True`, the server is to continue sending responses after
              sending an error response. Not all servers support continuation
              on error; a server that does not support it must send an error
              response if `True` was specified, causing
              :class:`~pywbem.CIMError` to be raised with status code
              :attr:`~pywbem.CIM_ERR_CONTINUATION_ON_ERROR_NOT_SUPPORTED`.
              If the corresponding traditional operation is used by this
              method, :exc:`~py:exceptions.ValueError` will be raised.
            * If `False`, the server is requested to close the enumeration after
              sending an error response.
            * If `None`, this parameter is not passed to the WBEM server, and
              causes the server-implemented default behaviour to be used.
              :term:`DSP0200` defines that the server-implemented default is
              `False`.

          MaxObjectCount (:class:`~pywbem.Uint32`)
            Maximum number of instances the WBEM server may return for each of
            the open and pull requests issued during the iterations over the
            returned generator object.

            * If positive, the WBEM server is to return no more than the
              specified number of instances.
            * Zero is not allowed; it would mean that zero instances
              are to be returned for open and all pull requests issued to the
              server.
            * The default is defined as a system config variable.
            * `None` is not allowed.

          **extra :
            Additional keyword arguments are passed as additional operation
            parameters to the WBEM server.
            Note that :term:`DSP0200` does not define any additional parameters
            for this operation.

        Returns:

          :term:`py:generator` iterating :class:`~pywbem.CIMInstance`:
          A generator object that iterates the resulting CIM instances.
          These instances include an instance path that has its host and
          namespace components set.

        Raises:

            Exceptions described in :class:`~pywbem.WBEMConnection`.

        Example::

            insts_generator = conn.IterAssociatorInstances('CIM_Blah.key=1',...)
            for inst in insts_generator:
                # close if a particular property value found
                if inst.get('thisPropertyName') == 0
                    insts_generator.close()
                    break
                else:
                    print('instance {0}'.format(inst.tomof()))
        """  # noqa: E501

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
                        IncludeQualifiers=IncludeQualifiers,
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

    def IterAssociatorInstancePaths(self, InstanceName, AssocClass=None,
                                    ResultClass=None,
                                    Role=None, ResultRole=None,
                                    FilterQueryLanguage=None, FilterQuery=None,
                                    OperationTimeout=None, ContinueOnError=None,
                                    MaxObjectCount=DEFAULT_ITER_MAXOBJECTCOUNT,
                                    **extra):
        # pylint: disable=invalid-name
        """
        Retrieve the instance paths of the instances associated to a source
        instance, using the Python :term:`py:generator` idiom to return the
        result.

        *New in pywbem 0.10 as experimental and finalized in 0.12.*

        This method uses the corresponding pull operations if supported by the
        WBEM server or otherwise the corresponding traditional operation.
        This method is an alternative to using the pull operations directly,
        that frees the user of having to know whether the WBEM server supports
        pull operations.

        This method is a generator function that retrieves instance paths from
        the WBEM server and returns them one by one (using :keyword:`yield`)
        when the caller iterates through the returned generator object. The
        number of instance paths that are retrieved from the WBEM server in one
        request (and thus need to be materialized in this method) is up to the
        `MaxObjectCount` parameter if the corresponding pull operations are
        used, or the complete result set all at once if the corresponding
        traditional operation is used.

        By default, this method attempts to perform the corresponding pull
        operations
        (:meth:`~pywbem.WBEMConnection.OpenAssociatorInstancePaths` and
        :meth:`~pywbem.WBEMConnection.PullInstancePaths`).
        If these pull operations are not supported by the WBEM server, this
        method falls back to using the corresponding traditional operation
        (:meth:`~pywbem.WBEMConnection.AssociatorNames`).
        Whether the WBEM server supports these pull operations is remembered
        in the :class:`~pywbem.WBEMConnection` object (by operation type), and
        avoids unnecessary attempts to try these pull operations on that
        connection in the future.
        The `use_pull_operations` init parameter of
        :class:`~pywbem.WBEMConnection` can be used to control the preference
        for always using pull operations, always using traditional operations,
        or using pull operations if supported by the WBEM server (the default).

        This method provides all of the controls of the corresponding pull
        operations except for the ability to set different response sizes on
        each request; the response size (defined by the `MaxObjectCount`
        parameter) is the same for all pull operations in the enumeration
        session.

        In addition, some functionality is only available if the corresponding
        pull operations are used by this method:

        * Filtering is not supported for the corresponding traditional
          operation so that setting the `FilterQuery` or `FilterQueryLanguage`
          parameters will be rejected if the corresponding traditional
          operation is used by this method.

          Note that this limitation is not a disadvantage compared to using the
          corresponding pull operations directly, because in both cases, the
          WBEM server must support the pull operations and their filtering
          capability in order for the filtering to work.

        * Setting the `ContinueOnError` parameter to `True` will be rejected if
          the corresponding traditional operation is used by this method.

        The enumeration session that is opened with the WBEM server when using
        pull operations is closed automatically when the returned generator
        object is exhausted, or when the generator object is closed using its
        :meth:`~py:generator.close` method (which may also be called before the
        generator is exhausted).

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
            The name of the filter query language used for the `FilterQuery`
            parameter. The DMTF-defined Filter Query Language (see
            :term:`DSP0212`) is specified as "DMTF:FQL".

            If this parameter is not `None` and the traditional operation is
            used by this method, :exc:`~py:exceptions.ValueError` will be
            raised.

            Not all WBEM servers support filtering for this operation because
            it returns instance paths and the act of the server filtering
            requires that it generate instances just for that purpose and then
            discard them.

          FilterQuery (:term:`string`):
            The filter query in the query language defined by the
            `FilterQueryLanguage` parameter.

            If this parameter is not `None` and the traditional operation is
            used by this method, :exc:`~py:exceptions.ValueError` will be
            raised.

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
              If the corresponding traditional operation is used by this
              method, :exc:`~py:exceptions.ValueError` will be raised.
            * If `False`, the server is requested to close the enumeration
              after sending an error response.
            * If `None`, this parameter is not passed to the WBEM server, and
              causes the server-implemented default behaviour to be used.
              :term:`DSP0200` defines that the server-implemented default is
              `False`.

          MaxObjectCount (:class:`~pywbem.Uint32`)
            Maximum number of instances the WBEM server may return for each of
            the open and pull requests issued during the iterations over the
            returned generator object.

            * If positive, the WBEM server is to return no more than the
              specified number of instances.
            * Zero is not allowed; it would mean that zero instances
              are to be returned for open and all pull requests issued to the
              server.
            * The default is defined as a system config variable.
            * `None` is not allowed.

          **extra :
            Additional keyword arguments are passed as additional operation
            parameters to the WBEM server.
            Note that :term:`DSP0200` does not define any additional parameters
            for this operation.

        Returns:

          :term:`py:generator` iterating :class:`~pywbem.CIMInstanceName`:
          A generator object that iterates the resulting CIM instance paths.
          These instance paths have their host and namespace components set.

        Raises:

            Exceptions described in :class:`~pywbem.WBEMConnection`.

        Example::

            paths_generator = conn.IterAssociatorInstancePaths('CIM_Blah')
            for path in paths_generator:
                print('path {0}'.format(path))
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

    def IterReferenceInstances(self, InstanceName, ResultClass=None,
                               Role=None, IncludeQualifiers=None,
                               IncludeClassOrigin=None, PropertyList=None,
                               FilterQueryLanguage=None, FilterQuery=None,
                               OperationTimeout=None, ContinueOnError=None,
                               MaxObjectCount=DEFAULT_ITER_MAXOBJECTCOUNT,
                               **extra):
        # pylint: disable=invalid-name,line-too-long
        """
        Retrieve the association instances that reference a source instance,
        using the Python :term:`py:generator` idiom to return the result.

        *New in pywbem 0.10 as experimental and finalized in 0.12.*

        This method uses the corresponding pull operations if supported by the
        WBEM server or otherwise the corresponding traditional operation.
        This method is an alternative to using the pull operations directly,
        that frees the user of having to know whether the WBEM server supports
        pull operations.

        This method is a generator function that retrieves instances from
        the WBEM server and returns them one by one (using :keyword:`yield`)
        when the caller iterates through the returned generator object. The
        number of instances that are retrieved from the WBEM server in one
        request (and thus need to be materialized in this method) is up to the
        `MaxObjectCount` parameter if the corresponding pull operations are
        used, or the complete result set all at once if the corresponding
        traditional operation is used.

        By default, this method attempts to perform the corresponding pull
        operations
        (:meth:`~pywbem.WBEMConnection.OpenReferenceInstances` and
        :meth:`~pywbem.WBEMConnection.PullInstancesWithPath`).
        If these pull operations are not supported by the WBEM server, this
        method falls back to using the corresponding traditional operation
        (:meth:`~pywbem.WBEMConnection.References`).
        Whether the WBEM server supports these pull operations is remembered
        in the :class:`~pywbem.WBEMConnection` object (by operation type), and
        avoids unnecessary attempts to try these pull operations on that
        connection in the future.
        The `use_pull_operations` init parameter of
        :class:`~pywbem.WBEMConnection` can be used to control the preference
        for always using pull operations, always using traditional operations,
        or using pull operations if supported by the WBEM server (the default).

        This method provides all of the controls of the corresponding pull
        operations except for the ability to set different response sizes on
        each request; the response size (defined by the `MaxObjectCount`
        parameter) is the same for all pull operations in the enumeration
        session.

        In addition, some functionality is only available if the corresponding
        pull operations are used by this method:

        * Filtering is not supported for the corresponding traditional
          operation so that setting the `FilterQuery` or `FilterQueryLanguage`
          parameters will be rejected if the corresponding traditional
          operation is used by this method.

          Note that this limitation is not a disadvantage compared to using the
          corresponding pull operations directly, because in both cases, the
          WBEM server must support the pull operations and their filtering
          capability in order for the filtering to work.

        * Setting the `ContinueOnError` parameter to `True` will be rejected if
          the corresponding traditional operation is used by this method.

        The enumeration session that is opened with the WBEM server when using
        pull operations is closed automatically when the returned generator
        object is exhausted, or when the generator object is closed using its
        :meth:`~py:generator.close` method (which may also be called before the
        generator is exhausted).

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
            cannot rely on qualifiers to be returned in this operation.

          IncludeClassOrigin (:class:`py:bool`):
            Indicates that class origin information is to be included on each
            property or method in the returned instances (or classes), as
            follows:

            * If `False`, class origin information is not included.
            * If `True`, class origin information is included.
            * If `None`, this parameter is not passed to the WBEM server, and
              causes the server-implemented default to be used. :term:`DSP0200`
              defines that the server-implemented default is `False`.

            This parameter has been deprecated in :term:`DSP0200`. WBEM servers
            may either implement this parameter as specified, or may treat any
            specified value as `False`.

          PropertyList (:term:`string` or :term:`py:iterable` of :term:`string`):
            An iterable specifying the names of the properties (or a string
            that defines a single property) to be included in the returned
            instances (case independent).

            An empty iterable indicates to include no properties.

            If `None`, all properties are included.

          FilterQueryLanguage (:term:`string`):
            The name of the filter query language used for the `FilterQuery`
            parameter. The DMTF-defined Filter Query Language (see
            :term:`DSP0212`) is specified as "DMTF:FQL".

            If this parameter is not `None` and the traditional operation is
            used by this method, :exc:`~py:exceptions.ValueError` will be
            raised.

          FilterQuery (:term:`string`):
            The filter query in the query language defined by the
            `FilterQueryLanguage` parameter.

            If this parameter is not `None` and the traditional operation is
            used by this method, :exc:`~py:exceptions.ValueError` will be
            raised.

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
              If the corresponding traditional operation is used by this
              method, :exc:`~py:exceptions.ValueError` will be raised.
            * If `False`, the server is requested to close the enumeration after
              sending an error response.
            * If `None`, this parameter is not passed to the WBEM server, and
              causes the server-implemented default behaviour to be used.
              :term:`DSP0200` defines that the server-implemented default is
              `False`.

          MaxObjectCount (:class:`~pywbem.Uint32`)
            Maximum number of instances the WBEM server may return for each of
            the open and pull requests issued during the iterations over the
            returned generator object.

            * If positive, the WBEM server is to return no more than the
              specified number of instances.
            * Zero is not allowed; it would mean that zero instances
              are to be returned for open and all pull requests issued to the
              server.
            * The default is defined as a system config variable.
            * `None` is not allowed.

          **extra :
            Additional keyword arguments are passed as additional operation
            parameters to the WBEM server.
            Note that :term:`DSP0200` does not define any additional parameters
            for this operation.

        Returns:

          :term:`py:generator` iterating :class:`~pywbem.CIMInstance`:
          A generator object that iterates the resulting CIM instances.
          These instances include an instance path that has its host and
          namespace components set.

        Raises:

            Exceptions described in :class:`~pywbem.WBEMConnection`.

        Example::

            insts_generator = conn.IterReferenceInstances('CIM_Blah.key=1', ...)
            for inst in insts_generator:
                # close if a particular property value found
                if inst.get('thisPropertyName') == 0
                    insts_generator.close()
                    break
                else:
                    print('instance {0}'.format(inst.tomof()))
        """  # noqa: E501

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
                        IncludeQualifiers=IncludeQualifiers,
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

    def IterReferenceInstancePaths(self, InstanceName, ResultClass=None,
                                   Role=None,
                                   FilterQueryLanguage=None, FilterQuery=None,
                                   OperationTimeout=None, ContinueOnError=None,
                                   MaxObjectCount=DEFAULT_ITER_MAXOBJECTCOUNT,
                                   **extra):
        # pylint: disable=invalid-name
        """
        Retrieve the instance paths of the association instances that reference
        a source instance, using the Python :term:`py:generator` idiom to
        return the result.

        *New in pywbem 0.10 as experimental and finalized in 0.12.*

        This method uses the corresponding pull operations if supported by the
        WBEM server or otherwise the corresponding traditional operation.
        This method is an alternative to using the pull operations directly,
        that frees the user of having to know whether the WBEM server supports
        pull operations.

        This method is a generator function that retrieves instance paths from
        the WBEM server and returns them one by one (using :keyword:`yield`)
        when the caller iterates through the returned generator object. The
        number of instance paths that are retrieved from the WBEM server in one
        request (and thus need to be materialized in this method) is up to the
        `MaxObjectCount` parameter if the corresponding pull operations are
        used, or the complete result set all at once if the corresponding
        traditional operation is used.

        By default, this method attempts to perform the corresponding pull
        operations
        (:meth:`~pywbem.WBEMConnection.OpenReferenceInstancePaths` and
        :meth:`~pywbem.WBEMConnection.PullInstancePaths`).
        If these pull operations are not supported by the WBEM server, this
        method falls back to using the corresponding traditional operation
        (:meth:`~pywbem.WBEMConnection.ReferenceNames`).
        Whether the WBEM server supports these pull operations is remembered
        in the :class:`~pywbem.WBEMConnection` object (by operation type), and
        avoids unnecessary attempts to try these pull operations on that
        connection in the future.
        The `use_pull_operations` init parameter of
        :class:`~pywbem.WBEMConnection` can be used to control the preference
        for always using pull operations, always using traditional operations,
        or using pull operations if supported by the WBEM server (the default).

        This method provides all of the controls of the corresponding pull
        operations except for the ability to set different response sizes on
        each request; the response size (defined by the `MaxObjectCount`
        parameter) is the same for all pull operations in the enumeration
        session.

        In addition, some functionality is only available if the corresponding
        pull operations are used by this method:

        * Filtering is not supported for the corresponding traditional
          operation so that setting the `FilterQuery` or `FilterQueryLanguage`
          parameters will be rejected if the corresponding traditional
          operation is used by this method.

          Note that this limitation is not a disadvantage compared to using the
          corresponding pull operations directly, because in both cases, the
          WBEM server must support the pull operations and their filtering
          capability in order for the filtering to work.

        * Setting the `ContinueOnError` parameter to `True` will be rejected if
          the corresponding traditional operation is used by this method.

        The enumeration session that is opened with the WBEM server when using
        pull operations is closed automatically when the returned generator
        object is exhausted, or when the generator object is closed using its
        :meth:`~py:generator.close` method (which may also be called before the
        generator is exhausted).

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
            The name of the filter query language used for the `FilterQuery`
            parameter. The DMTF-defined Filter Query Language (see
            :term:`DSP0212`) is specified as "DMTF:FQL".

            If this parameter is not `None` and the traditional operation is
            used by this method, :exc:`~py:exceptions.ValueError` will be
            raised.

            Not all WBEM servers support filtering for this operation because
            it returns instance paths and the act of the server filtering
            requires that it generate instances just for that purpose and then
            discard them.

          FilterQuery (:term:`string`):
            The filter query in the query language defined by the
            `FilterQueryLanguage` parameter.

            If this parameter is not `None` and the traditional operation is
            used by this method, :exc:`~py:exceptions.ValueError` will be
            raised.

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
              If the corresponding traditional operation is used by this
              method, :exc:`~py:exceptions.ValueError` will be raised.
            * If `False`, the server is requested to close the enumeration
              after sending an error response.
            * If `None`, this parameter is not passed to the WBEM server, and
              causes the server-implemented default behaviour to be used.
              :term:`DSP0200` defines that the server-implemented default is
              `False`.

          MaxObjectCount (:class:`~pywbem.Uint32`)
            Maximum number of instances the WBEM server may return for each of
            the open and pull requests issued during the iterations over the
            returned generator object.

            * If positive, the WBEM server is to return no more than the
              specified number of instances.
            * Zero is not allowed; it would mean that zero instances
              are to be returned for open and all pull requests issued to the
              server.
            * The default is defined as a system config variable.
            * `None` is not allowed.

          **extra :
            Additional keyword arguments are passed as additional operation
            parameters to the WBEM server.
            Note that :term:`DSP0200` does not define any additional parameters
            for this operation.

        Returns:

          :term:`py:generator` iterating :class:`~pywbem.CIMInstanceName`:
          A generator object that iterates the resulting CIM instance paths.
          These instance paths have their host and namespace components set.

        Raises:

            Exceptions described in :class:`~pywbem.WBEMConnection`.

        Example::

            paths_generator = conn.IterReferenceInstancePaths('CIM_Blah')
            for path in paths_generator:
                print('path {0}'.format(path))
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

    def IterQueryInstances(self, FilterQueryLanguage, FilterQuery,
                           namespace=None, ReturnQueryResultClass=None,
                           OperationTimeout=None, ContinueOnError=None,
                           MaxObjectCount=DEFAULT_ITER_MAXOBJECTCOUNT,
                           **extra):
        # pylint: disable=line-too-long
        """
        Execute a query in a namespace, using the Python :term:`py:generator`
        idiom to return the result.

        *New in pywbem 0.10 as experimental and finalized in 0.12.*

        This method uses the corresponding pull operations if supported by the
        WBEM server or otherwise the corresponding traditional operation.
        This method is an alternative to using the pull operations directly,
        that frees the user of having to know whether the WBEM server supports
        pull operations.

        Other than the other Iter...() methods, this method does not return
        a generator object directly, but as a property of the returned object.
        The reason for this design is the additionally returned query
        result class. The generator property in the returned object is a
        generator object that returns the instances in the query result one by
        one (using :keyword:`yield`) when the caller iterates through the
        generator object. This design causes the entire query result to be
        materialized, even if pull operations are used.

        By default, this method attempts to perform the corresponding pull
        operations
        (:meth:`~pywbem.WBEMConnection.OpenQueryInstances` and
        :meth:`~pywbem.WBEMConnection.PullInstances`).
        If these pull operations are not supported by the WBEM server, this
        method falls back to using the corresponding traditional operation
        (:meth:`~pywbem.WBEMConnection.ExecQuery`).
        Whether the WBEM server supports these pull operations is remembered
        in the :class:`~pywbem.WBEMConnection` object (by operation type), and
        avoids unnecessary attempts to try these pull operations on that
        connection in the future.
        The `use_pull_operations` init parameter of
        :class:`~pywbem.WBEMConnection` can be used to control the preference
        for always using pull operations, always using traditional operations,
        or using pull operations if supported by the WBEM server (the default).

        This method provides all of the controls of the corresponding pull
        operations except for the ability to set different response sizes on
        each request; the response size (defined by the `MaxObjectCount`
        parameter) is the same for all pull operations in the enumeration
        session.

        In addition, some functionality is only available if the corresponding
        pull operations are used by this method:

        * Setting the `ContinueOnError` parameter to `True` will be rejected if
          the corresponding traditional operation is used by this method.

        The enumeration session that is opened with the WBEM server when using
        pull operations is closed automatically when the returned generator
        object is exhausted, or when the generator object is closed using its
        :meth:`~py:generator.close` method (which may also be called before the
        generator is exhausted).

        Parameters:

          QueryLanguage (:term:`string`):
            Name of the query language used in the `Query` parameter, e.g.
            "DMTF:CQL" for CIM Query Language, and "WQL" for WBEM Query
            Language. Because this is not a filter query, "DMTF:FQL" is not a
            valid query language for this request.

          Query (:term:`string`):
            Query string in the query language specified in the `QueryLanguage`
            parameter.

          namespace (:term:`string`):
            Name of the CIM namespace to be used (case independent).

            Leading and trailing slash characters will be stripped. The lexical
            case will be preserved.

            If `None`, the default namespace of the connection object will be
            used.

          ReturnQueryResultClass (:class:`py:bool`):
            Controls whether a class definition describing the returned
            instances will be returned.

            `None` will cause the server to use its default of `False`.

            `None` will cause the server to use its default of `False`.

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
              If the corresponding traditional operation is used by this
              method, :exc:`~py:exceptions.ValueError` will be raised.
            * If `False`, the server is requested to close the enumeration after
              sending an error response.
            * If `None`, this parameter is not passed to the WBEM server, and
              causes the server-implemented default behaviour to be used.
              :term:`DSP0200` defines that the server-implemented default is
              `False`.

          MaxObjectCount (:class:`~pywbem.Uint32`)
            Maximum number of instances the WBEM server may return for each of
            the open and pull requests issued during the iterations over the
            returned generator object.

            * If positive, the WBEM server is to return no more than the
              specified number of instances.
            * Zero is not allowed; it would mean that zero instances
              are to be returned for open and all pull requests issued to the
              server.
            * The default is defined as a system config variable.
            * `None` is not allowed.

          **extra :
            Additional keyword arguments are passed as additional operation
            parameters to the WBEM server.
            Note that :term:`DSP0200` does not define any additional parameters
            for this operation.

        Returns:

          :class:`~pywbem.IterQueryInstancesReturn`: An object with the
          following properties:

          * **query_result_class** (:class:`~pywbem.CIMClass`):

            The query result class, if requested via the
            `ReturnQueryResultClass` parameter.

            `None`, if a query result class was not requested.

          * **generator** (:term:`py:generator` iterating :class:`~pywbem.CIMInstance`):

            A generator object that iterates the CIM instances representing the
            query result. These instances do not have an instance path set.

        Raises:

            Exceptions described in :class:`~pywbem.WBEMConnection`.

        Example::

            result = conn.IterQueryInstances(
                'DMTF:CQL',
                'SELECT FROM * where pl > 2')
            for inst in result.generator:
                print('instance {0}'.format(inst.tomof()))
        """  # noqa: E501
        # pylint: enable=line-too-long

        class IterQueryInstancesReturn(object):
            """
            The return data for
            :meth:`~pywbem.WBEMConnection.IterQueryInstances`.
            """

            def __init__(self, instances, query_result_class=None):
                """Save any query_result_class and instances returned"""
                self._query_result_class = query_result_class
                self.instances = instances

            @property
            def query_result_class(self):
                """
                :class:`~pywbem.CIMClass`: The query result class, if requested
                via the `ReturnQueryResultClass` parameter of
                :meth:`~pywbem.WBEMConnection.IterQueryInstances`.

                `None`, if a query result class was not requested.
                """
                return self._query_result_class

            @property
            def generator(self):
                """
                :term:`py:generator` iterating :class:`~pywbem.CIMInstance`:
                A generator object that iterates the CIM instances representing
                the query result. These instances do not have an instance path
                set.
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
                        FilterQueryLanguage,
                        FilterQuery,
                        namespace=namespace,
                        ReturnQueryResultClass=ReturnQueryResultClass,
                        OperationTimeout=OperationTimeout,
                        ContinueOnError=ContinueOnError,
                        MaxObjectCount=MaxObjectCount, **extra)

                    # Open operation succeeded; set has_pull flag
                    self._use_query_pull_operations = True

                    _instances = pull_result.instances

                    # get QueryResultClass from if returned with open
                    # request.
                    qrc = pull_result.query_result_class if \
                        ReturnQueryResultClass else None

                    if not pull_result.eos:
                        while not pull_result.eos:
                            pull_result = self.PullInstances(
                                pull_result.context,
                                MaxObjectCount=MaxObjectCount)
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

            # The parameters are QueryLanguage and Query for ExecQuery
            _instances = self.ExecQuery(FilterQueryLanguage,
                                        FilterQuery,
                                        namespace=namespace, **extra)

            rtn = IterQueryInstancesReturn(_instances)
            return rtn

        # Cleanup if caller closes the iterator before exhausting it
        finally:
            # Cleanup only required if the pull context is open and not complete
            if pull_result is not None and not pull_result.eos:
                self.CloseEnumeration(pull_result.context)
                pull_result = None

    def OpenEnumerateInstances(self, ClassName, namespace=None, LocalOnly=None,
                               DeepInheritance=None, IncludeQualifiers=None,
                               IncludeClassOrigin=None, PropertyList=None,
                               FilterQueryLanguage=None, FilterQuery=None,
                               OperationTimeout=None, ContinueOnError=None,
                               MaxObjectCount=None, **extra):
        # pylint: disable=invalid-name,line-too-long
        """
        Open an enumeration session to enumerate the instances of a class
        (including instances of its subclasses) in a namespace.

        *New in pywbem 0.9.*

        This method performs the OpenEnumerateInstances operation
        (see :term:`DSP0200`). See :ref:`WBEM operations` for a list of all
        methods performing such operations.

        If the operation succeeds, this method returns enumeration session
        status and optionally instances.
        Otherwise, this method raises an exception.

        Use the :meth:`~pywbem.WBEMConnection.PullInstancesWithPath` method to
        retrieve the next set of instances or the
        :meth:`~pywbem.WBEMConnection.CloseEnumeration` method to close the
        enumeration session before it is exhausted.

        Parameters:

          ClassName (:term:`string` or :class:`~pywbem.CIMClassName`):
            Name of the class to be enumerated (case independent).
            If specified as a :class:`~pywbem.CIMClassName` object, its
            `namespace` attribute will be used as a default namespace as
            described for the `namespace` parameter, and its `host` attribute
            will be ignored.

          namespace (:term:`string`):
            Name of the CIM namespace to be used (case independent).

            Leading and trailing slash characters will be stripped. The lexical
            case will be preserved.

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
            cannot rely on qualifiers to be returned in this operation.

          IncludeClassOrigin (:class:`py:bool`):
            Indicates that class origin information is to be included on each
            property in the returned instances, as follows:

            * If `False`, class origin information is not included.
            * If `True`, class origin information is included.
            * If `None`, this parameter is not passed to the WBEM server, and
              causes the server-implemented default to be used. :term:`DSP0200`
              defines that the server-implemented default is `False`.

            This parameter has been deprecated in :term:`DSP0200`. WBEM servers
            may either implement this parameter as specified, or may treat any
            specified value as `False`.

          PropertyList (:term:`string` or :term:`py:iterable` of :term:`string`):
            An iterable specifying the names of the properties (or a string
            that defines a single property) to be included in the returned
            instances (case independent).

            An empty iterable indicates to include no properties.

            If `None`, all properties are included.

          FilterQueryLanguage (:term:`string`):
            The name of the filter query language used for the `FilterQuery`
            parameter. The DMTF-defined Filter Query Language (see
            :term:`DSP0212`) is specified as "DMTF:FQL".

          FilterQuery (:term:`string`):
            The filter query in the query language defined by the
            `FilterQueryLanguage` parameter.

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

          **extra :
            Additional keyword arguments are passed as additional operation
            parameters to the WBEM server.
            Note that :term:`DSP0200` does not define any additional parameters
            for this operation.

        Returns:

            A :func:`~py:collections.namedtuple` object containing the following
            named items:

            * **instances** (:class:`py:list` of :class:`~pywbem.CIMInstance`):
              Representations of the retrieved instances.

              The `path` attribute of each :class:`~pywbem.CIMInstance`
              object is a :class:`~pywbem.CIMInstanceName` object with its
              attributes set as follows:

              * `classname`: Name of the creation class of the instance.
              * `keybindings`: Keybindings of the instance.
              * `namespace`: Name of the CIM namespace containing the instance.
              * `host`: Host and optionally port of the WBEM server containing
                the CIM namespace.

            * **eos** (:class:`py:bool`):
              Indicates whether the enumeration session is exhausted after
              this operation:

              - If `True`, the enumeration session is exhausted, and the
                server has closed the enumeration session.
              - If `False`, the enumeration session is not exhausted and the
                `context` item is the context object for the next operation on
                the enumeration session.

            * **context** (:func:`py:tuple` of server_context, namespace):
              A context object identifying the open enumeration session,
              including its current enumeration state, and the namespace. This
              object must be supplied with the next pull or close operation for
              this enumeration session.

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

        Example::

            max_object_count = 100
            rslt_tuple = conn.OpenEnumerateInstances(
                'CIM_Blah', MaxObjectCount=max_object_count)
            insts = rslt_tuple.paths
            while not rslt_tuple.eos:
                rslt_tuple = conn.PullInstancesWithPath(rslt_tupl.context,
                                                        max_object_count)
                insts.extend(rslt_tupl.paths)
            for inst in insts:
                print('instance {0}'.format(inst.tomof()))
        """  # noqa: E501

        exc = None
        result_tuple = None
        method_name = 'OpenEnumerateInstances'

        if self._operation_recorders:
            self.operation_recorder_reset(pull_op=True)
            self.operation_recorder_stage_pywbem_args(
                method=method_name,
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
            raise ValueError(
                _format("MaxObjectCount must be >= 0 but is {0}",
                        MaxObjectCount))

        try:

            stats = self.statistics.start_timer(method_name)
            if namespace is None and isinstance(ClassName, CIMClassName):
                namespace = ClassName.namespace
            namespace = self._iparam_namespace_from_namespace(namespace)
            classname = self._iparam_classname(ClassName)
            PropertyList = _iparam_propertylist(PropertyList)

            result = self._imethodcall(
                method_name,
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
                has_out_params=True,
                **extra)

            result_tuple = pull_inst_result_tuple(
                *self._get_rslt_params(result, namespace))
            return result_tuple

        except (CIMXMLParseError, XMLParseError) as exce:
            exce.request_data = self.last_raw_request
            exce.response_data = self.last_raw_reply
            exc = exce
            raise
        except Exception as exce:
            exc = exce
            raise
        finally:
            self._last_operation_time = stats.stop_timer(
                self.last_request_len, self.last_reply_len,
                self.last_server_response_time, exc)
            if self._operation_recorders:
                self.operation_recorder_stage_result(result_tuple, exc)

    def OpenEnumerateInstancePaths(self, ClassName, namespace=None,
                                   FilterQueryLanguage=None, FilterQuery=None,
                                   OperationTimeout=None, ContinueOnError=None,
                                   MaxObjectCount=None, **extra):
        # pylint: disable=invalid-name

        """
        Open an enumeration session to enumerate the instance paths of
        instances of a class (including instances of its subclasses) in
        a namespace.

        *New in pywbem 0.9.*

        This method performs the OpenEnumerateInstancePaths operation
        (see :term:`DSP0200`). See :ref:`WBEM operations` for a list of all
        methods performing such operations.

        If the operation succeeds, this method returns status on the
        enumeration session and optionally instance paths.
        Otherwise, this method raises an exception.

        Use the :meth:`~pywbem.WBEMConnection.PullInstancePaths` method to
        retrieve the next set of instance paths or the
        :meth:`~pywbem.WBEMConnection.CloseEnumeration` method to close the
        enumeration session before it is exhausted.

        Parameters:

          ClassName (:term:`string` or :class:`~pywbem.CIMClassName`):
            Name of the class to be enumerated (case independent).
            If specified as a :class:`~pywbem.CIMClassName` object, its
            `namespace` attribute will be used as a default namespace as
            described for the `namespace` parameter, and its `host` attribute
            will be ignored.

          namespace (:term:`string`):
            Name of the CIM namespace to be used (case independent).

            Leading and trailing slash characters will be stripped. The lexical
            case will be preserved.

            If `None`, the namespace of the `ClassName` parameter will be used,
            if specified as a :class:`~pywbem.CIMClassName` object. If that is
            also `None`, the default namespace of the connection will be used.

          FilterQueryLanguage (:term:`string`):
            The name of the filter query language used for the `FilterQuery`
            parameter. The DMTF-defined Filter Query Language (see
            :term:`DSP0212`) is specified as "DMTF:FQL".

            Not all WBEM servers support filtering for this operation because
            it returns instance paths and the act of the server filtering
            requires that it generate instances just for that purpose and then
            discard them.

          FilterQuery (:term:`string`):
            The filter query in the query language defined by the
            `FilterQueryLanguage` parameter.

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

          **extra :
            Additional keyword arguments are passed as additional operation
            parameters to the WBEM server.
            Note that :term:`DSP0200` does not define any additional parameters
            for this operation.

        Returns:

            A :func:`~py:collections.namedtuple` object containing the following
            named items:

            * **paths** (:class:`py:list` of :class:`~pywbem.CIMInstanceName`):
              Representations of the retrieved instance paths, with their
              attributes set as follows:

              * `classname`: Name of the creation class of the instance.
              * `keybindings`: Keybindings of the instance.
              * `namespace`: Name of the CIM namespace containing the instance.
              * `host`: Host and optionally port of the WBEM server containing
                the CIM namespace.

            * **eos** (:class:`py:bool`):
              Indicates whether the enumeration session is exhausted after
              this operation:

              - If `True`, the enumeration session is exhausted, and the
                server has closed the enumeration session.
              - If `False`, the enumeration session is not exhausted and the
                `context` item is the context object for the next operation on
                the enumeration session.

            * **context** (:func:`py:tuple` of server_context, namespace):
              A context object identifying the open enumeration session,
              including its current enumeration state, and the namespace. This
              object must be supplied with the next pull or close operation for
              this enumeration session.

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

        Example::

            max_object_count = 100
            rslt_tuple = conn.OpenEnumerateInstancePaths(
                'CIM_Blah', MaxObjectCount=max_object_count)
            paths = rslt_tuple.paths
            while not rslt_tuple.eos:
                rslt_tuple = conn.PullInstancePaths(rslt_tupl.context,
                                                    max_object_count)
                paths.extend(rslt_tupl.paths)
            for path in paths:
                print('path {0}'.format(path))
        """

        exc = None
        result_tuple = None
        method_name = 'OpenEnumerateInstancePaths'

        if self._operation_recorders:
            self.operation_recorder_reset(pull_op=True)
            self.operation_recorder_stage_pywbem_args(
                method=method_name,
                ClassName=ClassName,
                namespace=namespace,
                FilterQueryLanguage=FilterQueryLanguage,
                FilterQuery=FilterQuery,
                OperationTimeout=OperationTimeout,
                ContinueOnError=ContinueOnError,
                MaxObjectCount=MaxObjectCount,
                **extra)

        try:
            stats = self.statistics.start_timer(method_name)
            if namespace is None and isinstance(ClassName, CIMClassName):
                namespace = ClassName.namespace
            namespace = self._iparam_namespace_from_namespace(namespace)
            classname = self._iparam_classname(ClassName)

            result = self._imethodcall(
                method_name,
                namespace,
                ClassName=classname,
                FilterQueryLanguage=FilterQueryLanguage,
                FilterQuery=FilterQuery,
                OperationTimeout=OperationTimeout,
                ContinueOnError=ContinueOnError,
                MaxObjectCount=MaxObjectCount,
                has_out_params=True,
                **extra)

            result_tuple = pull_path_result_tuple(
                *self._get_rslt_params(result, namespace))
            return result_tuple

        except (CIMXMLParseError, XMLParseError) as exce:
            exce.request_data = self.last_raw_request
            exce.response_data = self.last_raw_reply
            exc = exce
            raise
        except Exception as exce:
            exc = exce
            raise
        finally:
            self._last_operation_time = stats.stop_timer(
                self.last_request_len, self.last_reply_len,
                self.last_server_response_time, exc)
            if self._operation_recorders:
                self.operation_recorder_stage_result(result_tuple, exc)

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

        *New in pywbem 0.9.*

        This method does not support retrieving classes.

        This method performs the OpenAssociatorInstances operation
        (see :term:`DSP0200`). See :ref:`WBEM operations` for a list of all
        methods performing such operations.

        If the operation succeeds, this method returns enumeration session
        status and optionally instances.
        Otherwise, this method raises an exception.

        Use the :meth:`~pywbem.WBEMConnection.PullInstancesWithPath` method to
        retrieve the next set of instances or the
        :meth:`~pywbem.WBEMConnection.CloseEnumeration` method to close the
        enumeration session before it is exhausted.

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
            instances, as follows:

            * If `False`, qualifiers are not included.
            * If `True`, qualifiers are included if the WBEM server implements
              support for this parameter.
            * If `None`, this parameter is not passed to the WBEM server, and
              causes the server-implemented default to be used. :term:`DSP0200`
              defines that the server-implemented default is `False`.

            This parameter has been deprecated in :term:`DSP0200`. Clients
            cannot rely on qualifiers to be returned in this operation.

          IncludeClassOrigin (:class:`py:bool`):
            Indicates that class origin information is to be included on each
            property or method in the returned instances, as follows:

            * If `False`, class origin information is not included.
            * If `True`, class origin information is included.
            * If `None`, this parameter is not passed to the WBEM server, and
              causes the server-implemented default to be used. :term:`DSP0200`
              defines that the server-implemented default is `False`.

            This parameter has been deprecated in :term:`DSP0200`. WBEM servers
            may either implement this parameter as specified, or may treat any
            specified value as `False`.

          PropertyList (:term:`string` or :term:`py:iterable` of :term:`string`):
            An iterable specifying the names of the properties (or a string
            that defines a single property) to be included in the returned
            instances (case independent).

            An empty iterable indicates to include no properties.

            If `None`, all properties are included.

          FilterQueryLanguage (:term:`string`):
            The name of the filter query language used for the `FilterQuery`
            parameter. The DMTF-defined Filter Query Language (see
            :term:`DSP0212`) is specified as "DMTF:FQL".

          FilterQuery (:term:`string`):
            The filter query in the query language defined by the
            `FilterQueryLanguage` parameter.

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

          **extra :
            Additional keyword arguments are passed as additional operation
            parameters to the WBEM server.
            Note that :term:`DSP0200` does not define any additional parameters
            for this operation.

        Returns:

            A :func:`~py:collections.namedtuple` object containing the following
            named items:

            * **instances** (:class:`py:list` of :class:`~pywbem.CIMInstance`):
              Representations of the retrieved instances.

              The `path` attribute of each :class:`~pywbem.CIMInstance`
              object is a :class:`~pywbem.CIMInstanceName` object with its
              attributes set as follows:

              * `classname`: Name of the creation class of the instance.
              * `keybindings`: Keybindings of the instance.
              * `namespace`: Name of the CIM namespace containing the instance.
              * `host`: Host and optionally port of the WBEM server containing
                the CIM namespace.

            * **eos** (:class:`py:bool`):
              Indicates whether the enumeration session is exhausted after
              this operation:

              - If `True`, the enumeration session is exhausted, and the
                server has closed the enumeration session.
              - If `False`, the enumeration session is not exhausted and the
                `context` item is the context object for the next operation on
                the enumeration session.

            * **context** (:func:`py:tuple` of server_context, namespace):
              A context object identifying the open enumeration session,
              including its current enumeration state, and the namespace. This
              object must be supplied with the next pull or close operation for
              this enumeration session.

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
        exc = None
        result_tuple = None
        method_name = 'OpenAssociatorInstances'

        if self._operation_recorders:
            self.operation_recorder_reset(pull_op=True)
            self.operation_recorder_stage_pywbem_args(
                method=method_name,
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

            stats = self.statistics.start_timer(method_name)
            namespace = self._iparam_namespace_from_objectname(InstanceName)
            instancename = self._iparam_instancename(InstanceName)
            PropertyList = _iparam_propertylist(PropertyList)

            result = self._imethodcall(
                method_name,
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
                has_out_params=True,
                **extra)

            result_tuple = pull_inst_result_tuple(
                *self._get_rslt_params(result, namespace))
            return result_tuple

        except (CIMXMLParseError, XMLParseError) as exce:
            exce.request_data = self.last_raw_request
            exce.response_data = self.last_raw_reply
            exc = exce
            raise
        except Exception as exce:
            exc = exce
            raise
        finally:
            self._last_operation_time = stats.stop_timer(
                self.last_request_len, self.last_reply_len,
                self.last_server_response_time, exc)
            if self._operation_recorders:
                self.operation_recorder_stage_result(result_tuple, exc)

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

        *New in pywbem 0.9.*

        This method does not support retrieving classes.

        This method performs the OpenAssociatorInstancePaths operation
        (see :term:`DSP0200`). See :ref:`WBEM operations` for a list of all
        methods performing such operations.

        If the operation succeeds, this method returns enumeration session
        status and optionally instance paths.
        Otherwise, this method raises an exception.

        Use the :meth:`~pywbem.WBEMConnection.PullInstancePaths` method to
        retrieve the next set of instance paths or the
        :meth:`~pywbem.WBEMConnection.CloseEnumeration` method to close the
        enumeration session before it is exhausted.

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
            The name of the filter query language used for the `FilterQuery`
            parameter. The DMTF-defined Filter Query Language (see
            :term:`DSP0212`) is specified as "DMTF:FQL".

            Not all WBEM servers support filtering for this operation because
            it returns instance paths and the act of the server filtering
            requires that it generate instances just for that purpose and then
            discard them.

          FilterQuery (:term:`string`):
            The filter query in the query language defined by the
            `FilterQueryLanguage` parameter.

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


          **extra :
            Additional keyword arguments are passed as additional operation
            parameters to the WBEM server.
            Note that :term:`DSP0200` does not define any additional parameters
            for this operation.

        Returns:

            A :func:`~py:collections.namedtuple` object containing the following
            named items:

            * **paths** (:class:`py:list` of :class:`~pywbem.CIMInstanceName`):
              Representations of the retrieved instance paths, with their
              attributes set as follows:

              * `classname`: Name of the creation class of the instance.
              * `keybindings`: Keybindings of the instance.
              * `namespace`: Name of the CIM namespace containing the instance.
              * `host`: Host and optionally port of the WBEM server containing
                the CIM namespace.

            * **eos** (:class:`py:bool`):
              Indicates whether the enumeration session is exhausted after
              this operation:

              - If `True`, the enumeration session is exhausted, and the
                server has closed the enumeration session.
              - If `False`, the enumeration session is not exhausted and the
                `context` item is the context object for the next operation on
                the enumeration session.

            * **context** (:func:`py:tuple` of server_context, namespace):
              A context object identifying the open enumeration session,
              including its current enumeration state, and the namespace. This
              object must be supplied with the next pull or close operation for
              this enumeration session.

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

        exc = None
        result_tuple = None
        method_name = 'OpenAssociatorInstancePaths'

        if self._operation_recorders:
            self.operation_recorder_reset(pull_op=True)
            self.operation_recorder_stage_pywbem_args(
                method=method_name,
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

            stats = self.statistics.start_timer(method_name)
            namespace = self._iparam_namespace_from_objectname(InstanceName)
            instancename = self._iparam_instancename(InstanceName)

            result = self._imethodcall(
                method_name,
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
                has_out_params=True,
                **extra)

            result_tuple = pull_path_result_tuple(
                *self._get_rslt_params(result, namespace))
            return result_tuple

        except (CIMXMLParseError, XMLParseError) as exce:
            exce.request_data = self.last_raw_request
            exce.response_data = self.last_raw_reply
            exc = exce
            raise
        except Exception as exce:
            exc = exce
            raise
        finally:
            self._last_operation_time = stats.stop_timer(
                self.last_request_len, self.last_reply_len,
                self.last_server_response_time, exc)
            if self._operation_recorders:
                self.operation_recorder_stage_result(result_tuple, exc)

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

        *New in pywbem 0.9.*

        This method does not support retrieving classes.

        This method performs the OpenReferenceInstances operation
        (see :term:`DSP0200`). See :ref:`WBEM operations` for a list of all
        methods performing such operations.

        If the operation succeeds, this method returns enumeration session
        status and optionally instances.
        Otherwise, this method raises an exception.

        Use the :meth:`~pywbem.WBEMConnection.PullInstancesWithPath` method to
        retrieve the next set of instances or the
        :meth:`~pywbem.WBEMConnection.CloseEnumeration` method to close the
        enumeration session before it is exhausted.

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
            cannot rely on qualifiers to be returned in this operation.

          IncludeClassOrigin (:class:`py:bool`):
            Indicates that class origin information is to be included on each
            property or method in the returned instances (or classes), as
            follows:

            * If `False`, class origin information is not included.
            * If `True`, class origin information is included.
            * If `None`, this parameter is not passed to the WBEM server, and
              causes the server-implemented default to be used. :term:`DSP0200`
              defines that the server-implemented default is `False`.

            This parameter has been deprecated in :term:`DSP0200`. WBEM servers
            may either implement this parameter as specified, or may treat any
            specified value as `False`.

          PropertyList (:term:`string` or :term:`py:iterable` of :term:`string`):
            An iterable specifying the names of the properties (or a string
            that defines a single property) to be included in the returned
            instances (case independent).

            An empty iterable indicates to include no properties.

            If `None`, all properties are included.

          FilterQueryLanguage (:term:`string`):
            The name of the filter query language used for the `FilterQuery`
            parameter. The DMTF-defined Filter Query Language (see
            :term:`DSP0212`) is specified as "DMTF:FQL".

          FilterQuery (:term:`string`):
            The filter query in the query language defined by the
            `FilterQueryLanguage` parameter.

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


          **extra :
            Additional keyword arguments are passed as additional operation
            parameters to the WBEM server.
            Note that :term:`DSP0200` does not define any additional parameters
            for this operation.

        Returns:

            A :func:`~py:collections.namedtuple` object containing the following
            named items:

            * **instances** (:class:`py:list` of :class:`~pywbem.CIMInstance`):
              Representations of the retrieved instances.

              The `path` attribute of each :class:`~pywbem.CIMInstance`
              object is a :class:`~pywbem.CIMInstanceName` object with its
              attributes set as follows:

              * `classname`: Name of the creation class of the instance.
              * `keybindings`: Keybindings of the instance.
              * `namespace`: Name of the CIM namespace containing the instance.
              * `host`: Host and optionally port of the WBEM server containing
                the CIM namespace.

            * **eos** (:class:`py:bool`):
              Indicates whether the enumeration session is exhausted after
              this operation:

              - If `True`, the enumeration session is exhausted, and the
                server has closed the enumeration session.
              - If `False`, the enumeration session is not exhausted and the
                `context` item is the context object for the next operation on
                the enumeration session.

            * **context** (:func:`py:tuple` of server_context, namespace):
              A context object identifying the open enumeration session,
              including its current enumeration state, and the namespace. This
              object must be supplied with the next pull or close operation for
              this enumeration session.

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

        exc = None
        result_tuple = None
        method_name = 'OpenReferenceInstances'

        if self._operation_recorders:
            self.operation_recorder_reset(pull_op=True)
            self.operation_recorder_stage_pywbem_args(
                method=method_name,
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

            stats = self.statistics.start_timer(method_name)
            namespace = self._iparam_namespace_from_objectname(InstanceName)
            instancename = self._iparam_instancename(InstanceName)
            PropertyList = _iparam_propertylist(PropertyList)

            result = self._imethodcall(
                method_name,
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
                has_out_params=True,
                **extra)

            result_tuple = pull_inst_result_tuple(
                *self._get_rslt_params(result, namespace))
            return result_tuple

        except (CIMXMLParseError, XMLParseError) as exce:
            exce.request_data = self.last_raw_request
            exce.response_data = self.last_raw_reply
            exc = exce
            raise
        except Exception as exce:
            exc = exce
            raise
        finally:
            self._last_operation_time = stats.stop_timer(
                self.last_request_len, self.last_reply_len,
                self.last_server_response_time, exc)
            if self._operation_recorders:
                self.operation_recorder_stage_result(result_tuple, exc)

    def OpenReferenceInstancePaths(self, InstanceName, ResultClass=None,
                                   Role=None,
                                   FilterQueryLanguage=None, FilterQuery=None,
                                   OperationTimeout=None, ContinueOnError=None,
                                   MaxObjectCount=None, **extra):
        # pylint: disable=invalid-name
        """
        Open an enumeration session to retrieve the instance paths of
        the association instances that reference a source instance.

        *New in pywbem 0.9.*

        This method does not support retrieving classes.

        This method performs the OpenReferenceInstancePaths operation
        (see :term:`DSP0200`). See :ref:`WBEM operations` for a list of all
        methods performing such operations.

        If the operation succeeds, this method returns enumeration session
        status and optionally instance paths.
        Otherwise, this method raises an exception.

        Use the :meth:`~pywbem.WBEMConnection.PullInstancePaths` method to
        retrieve the next set of instance paths or the
        :meth:`~pywbem.WBEMConnection.CloseEnumeration` method to close the
        enumeration session before it is exhausted.

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
            The name of the filter query language used for the `FilterQuery`
            parameter. The DMTF-defined Filter Query Language (see
            :term:`DSP0212`) is specified as "DMTF:FQL".

            Not all WBEM servers support filtering for this operation because
            it returns instance paths and the act of the server filtering
            requires that it generate instances just for that purpose and then
            discard them.

          FilterQuery (:term:`string`):
            The filter query in the query language defined by the
            `FilterQueryLanguage` parameter.

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

          **extra :
            Additional keyword arguments are passed as additional operation
            parameters to the WBEM server.
            Note that :term:`DSP0200` does not define any additional parameters
            for this operation.

        Returns:

            A :func:`~py:collections.namedtuple` object containing the following
            named items:

            * **paths** (:class:`py:list` of :class:`~pywbem.CIMInstanceName`):
              Representations of the retrieved instance paths, with their
              attributes set as follows:

              * `classname`: Name of the creation class of the instance.
              * `keybindings`: Keybindings of the instance.
              * `namespace`: Name of the CIM namespace containing the instance.
              * `host`: Host and optionally port of the WBEM server containing
                the CIM namespace.

            * **eos** (:class:`py:bool`):
              Indicates whether the enumeration session is exhausted after
              this operation:

              - If `True`, the enumeration session is exhausted, and the
                server has closed the enumeration session.
              - If `False`, the enumeration session is not exhausted and the
                `context` item is the context object for the next operation on
                the enumeration session.

            * **context** (:func:`py:tuple` of server_context, namespace):
              A context object identifying the open enumeration session,
              including its current enumeration state, and the namespace. This
              object must be supplied with the next pull or close operation for
              this enumeration session.

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
        exc = None
        result_tuple = None
        method_name = 'OpenReferenceInstancePaths'

        if self._operation_recorders:
            self.operation_recorder_reset(pull_op=True)
            self.operation_recorder_stage_pywbem_args(
                method=method_name,
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
            raise ValueError(
                _format("MaxObjectCount must be >= 0 but is {0}",
                        MaxObjectCount))
        try:

            stats = self.statistics.start_timer(method_name)
            namespace = self._iparam_namespace_from_objectname(InstanceName)
            instancename = self._iparam_instancename(InstanceName)

            result = self._imethodcall(
                method_name,
                namespace,
                InstanceName=instancename,
                ResultClass=self._iparam_classname(ResultClass),
                Role=Role,
                FilterQueryLanguage=FilterQueryLanguage,
                FilterQuery=FilterQuery,
                OperationTimeout=OperationTimeout,
                ContinueOnError=ContinueOnError,
                MaxObjectCount=MaxObjectCount,
                has_out_params=True,
                **extra)

            result_tuple = pull_path_result_tuple(
                *self._get_rslt_params(result, namespace))
            return result_tuple

        except (CIMXMLParseError, XMLParseError) as exce:
            exce.request_data = self.last_raw_request
            exce.response_data = self.last_raw_reply
            exc = exce
            raise
        except Exception as exce:
            exc = exce
            raise
        finally:
            self._last_operation_time = stats.stop_timer(
                self.last_request_len, self.last_reply_len,
                self.last_server_response_time, exc)
            if self._operation_recorders:
                self.operation_recorder_stage_result(result_tuple, exc)

    def OpenQueryInstances(self, FilterQueryLanguage, FilterQuery,
                           namespace=None, ReturnQueryResultClass=None,
                           OperationTimeout=None, ContinueOnError=None,
                           MaxObjectCount=None, **extra):
        # pylint: disable=invalid-name
        """
        Open an enumeration session to execute a query in a namespace and to
        retrieve the instances representing the query result.

        *New in pywbem 0.9.*

        This method performs the OpenQueryInstances operation
        (see :term:`DSP0200`). See :ref:`WBEM operations` for a list of all
        methods performing such operations.

        If the operation succeeds, this method returns enumeration session
        status and optionally CIM instances representing the query result.
        Otherwise, this method raises an exception.

        Use the :meth:`~pywbem.WBEMConnection.PullInstances` method to
        retrieve the next set of instances or the
        :meth:`~pywbem.WBEMConnection.CloseEnumeration` method to close the
        enumeration session before it is exhausted.

        Parameters:

          FilterQueryLanguage (:term:`string`):
            Name of the query language used in the `FilterQuery` parameter,
            e.g. "DMTF:CQL" for CIM Query Language, and "WQL" for WBEM Query
            Language. Because this is not a filter query, "DMTF:FQL" is not a
            valid query language for this request.

          FilterQuery (:term:`string`):
            Query string in the query language specified in the
            `FilterQueryLanguage` parameter.

          namespace (:term:`string`):
            Name of the CIM namespace to be used (case independent).

            Leading and trailing slash characters will be stripped. The lexical
            case will be preserved.

            If `None`, the default namespace of the connection object will be
            used.

          ReturnQueryResultClass (:class:`py:bool`):
            Controls whether a class definition describing the returned
            instances will be returned.

            `None` will cause the server to use its default of `False`.

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

          **extra :
            Additional keyword arguments are passed as additional operation
            parameters to the WBEM server.
            Note that :term:`DSP0200` does not define any additional parameters
            for this operation.

        Returns:

            A :func:`~py:collections.namedtuple` object containing the following
            named items:

            * **instances** (:class:`py:list` of :class:`~pywbem.CIMInstance`):
              Representations of the retrieved instances.

              The `path` attribute of each :class:`~pywbem.CIMInstance`
              object is `None`, because query results are not addressable
              CIM instances.

            * **eos** (:class:`py:bool`):
              Indicates whether the enumeration session is exhausted after
              this operation:

              - If `True`, the enumeration session is exhausted, and the
                server has closed the enumeration session.
              - If `False`, the enumeration session is not exhausted and the
                `context` item is the context object for the next operation on
                the enumeration session.

            * **context** (:func:`py:tuple` of server_context, namespace):
              A context object identifying the open enumeration session,
              including its current enumeration state, and the namespace. This
              object must be supplied with the next pull or close operation for
              this enumeration session.

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
                if p[0] == 'QueryResultClass':
                    class_obj = p[2]
                    if not isinstance(class_obj, CIMClass):
                        raise CIMXMLParseError(
                            _format("Expecting CIMClass object in "
                                    "QueryResultClass output parameter, got "
                                    "{0} object", class_obj.__class__.__name__),
                            conn_id=self.conn_id)
                    return class_obj
            raise CIMXMLParseError(
                "QueryResultClass output parameter is missing",
                conn_id=self.conn_id)

        exc = None
        result_tuple = None
        method_name = 'OpenQueryInstances'

        if self._operation_recorders:
            self.operation_recorder_reset(pull_op=True)
            self.operation_recorder_stage_pywbem_args(
                method=method_name,
                FilterQueryLanguage=FilterQueryLanguage,
                FilterQuery=FilterQuery,
                namespace=namespace,
                ReturnQueryResultClass=ReturnQueryResultClass,
                OperationTimeout=OperationTimeout,
                ContinueOnError=ContinueOnError,
                MaxObjectCount=MaxObjectCount,
                **extra)

        try:

            stats = self.statistics.start_timer(method_name)
            namespace = self._iparam_namespace_from_namespace(namespace)

            result = self._imethodcall(
                method_name,
                namespace,
                FilterQuery=FilterQuery,
                FilterQueryLanguage=FilterQueryLanguage,
                ReturnQueryResultClass=ReturnQueryResultClass,
                OperationTimeout=OperationTimeout,
                ContinueOnError=ContinueOnError,
                MaxObjectCount=MaxObjectCount,
                has_out_params=True,
                **extra)

            insts, eos, enum_ctxt = self._get_rslt_params(result, namespace)

            query_result_class = _GetQueryRsltClass(result) if \
                ReturnQueryResultClass else None

            result_tuple = pull_query_result_tuple(insts, eos, enum_ctxt,
                                                   query_result_class)
            return result_tuple

        except (CIMXMLParseError, XMLParseError) as exce:
            exce.request_data = self.last_raw_request
            exce.response_data = self.last_raw_reply
            exc = exce
            raise
        except Exception as exce:
            exc = exce
            raise
        finally:
            self._last_operation_time = stats.stop_timer(
                self.last_request_len, self.last_reply_len,
                self.last_server_response_time, exc)
            if self._operation_recorders:
                self.operation_recorder_stage_result(result_tuple, exc)

    def PullInstancesWithPath(self, context, MaxObjectCount, **extra):
        # pylint: disable=invalid-name

        """
        Retrieve the next set of instances (with instance paths) from an open
        enumeration session.

        *New in pywbem 0.9.*

        This operation can only be used on enumeration sessions that have been
        opened by one of the following methods:

        * :meth:`~pywbem.WBEMConnection.OpenEnumerateInstances`
        * :meth:`~pywbem.WBEMConnection.OpenAssociatorInstances`
        * :meth:`~pywbem.WBEMConnection.OpenReferenceInstances`

        This method performs the PullInstancesWithPath operation
        (see :term:`DSP0200`). See :ref:`WBEM operations` for a list of all
        methods performing such operations.

        If the operation succeeds, this method returns enumeration session
        status and optionally instances.
        Otherwise, this method raises an exception.

        Parameters:

          context (:func:`py:tuple` of server_context, namespace)
            A context object identifying the open enumeration session, including
            its current enumeration state, and the namespace. This object must
            have been returned by the previous open or pull operation for this
            enumeration session.

            The tuple items are:

            * server_context (:term:`string`):
              Enumeration context string returned by the server. This
              string is opaque for the client.
            * namespace (:term:`string`):
              Name of the CIM namespace being used for this enumeration session.

          MaxObjectCount (:class:`~pywbem.Uint32`)
            Maximum number of instances the WBEM server shall return
            for this request. This parameter is required for each
            Pull request.

            * If positive, the WBEM server is to return no more than the
              specified number of instances.
            * If zero, the WBEM server is to return no instances. This may
              be used by a client to reset the interoperation timer
            * `None` is not allowed.

          **extra :
            Additional keyword arguments are passed as additional operation
            parameters to the WBEM server.
            Note that :term:`DSP0200` does not define any additional parameters
            for this operation.

        Returns:

            A :func:`~py:collections.namedtuple` object containing the following
            named items:

            * **instances** (:class:`py:list` of :class:`~pywbem.CIMInstance`):
              Representations of the retrieved instances.

              The `path` attribute of each :class:`~pywbem.CIMInstance`
              object is a :class:`~pywbem.CIMInstanceName` object with its
              attributes set as follows:

              * `classname`: Name of the creation class of the instance.
              * `keybindings`: Keybindings of the instance.
              * `namespace`: Name of the CIM namespace containing the instance.
              * `host`: Host and optionally port of the WBEM server containing
                the CIM namespace.

            * **eos** (:class:`py:bool`):
              Indicates whether the enumeration session is exhausted after
              this operation:

              - If `True`, the enumeration session is exhausted, and the
                server has closed the enumeration session.
              - If `False`, the enumeration session is not exhausted and the
                `context` item is the context object for the next operation on
                the enumeration session.

            * **context** (:func:`py:tuple` of server_context, namespace):
              A context object identifying the open enumeration session,
              including its current enumeration state, and the namespace. This
              object must be supplied with the next pull or close operation for
              this enumeration session.

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

        exc = None
        result_tuple = None
        method_name = 'PullInstancesWithPath'

        if self._operation_recorders:
            self.operation_recorder_reset(pull_op=True)
            self.operation_recorder_stage_pywbem_args(
                method=method_name,
                context=context,
                MaxObjectCount=MaxObjectCount,
                **extra)

        try:

            stats = self.statistics.start_timer(method_name)
            _validatePullParams(MaxObjectCount, context)

            namespace = context[1]

            result = self._imethodcall(
                method_name,
                namespace=namespace,
                EnumerationContext=context[0],
                MaxObjectCount=MaxObjectCount,
                has_out_params=True,
                **extra)

            result_tuple = pull_inst_result_tuple(
                *self._get_rslt_params(result, namespace))
            return result_tuple

        except (CIMXMLParseError, XMLParseError) as exce:
            exce.request_data = self.last_raw_request
            exce.response_data = self.last_raw_reply
            exc = exce
            raise
        except Exception as exce:
            exc = exce
            raise
        finally:
            self._last_operation_time = stats.stop_timer(
                self.last_request_len, self.last_reply_len,
                self.last_server_response_time, exc)
            if self._operation_recorders:
                self.operation_recorder_stage_result(result_tuple, exc)

    def PullInstancePaths(self, context, MaxObjectCount, **extra):
        # pylint: disable=invalid-name
        """
        Retrieve the next set of instance paths from an open enumeration
        session.

        *New in pywbem 0.9.*

        This operation can only be used on enumeration sessions that have been
        opened by one of the following methods:

        * :meth:`~pywbem.WBEMConnection.OpenEnumerateInstancePaths`
        * :meth:`~pywbem.WBEMConnection.OpenAssociatorInstancePaths`
        * :meth:`~pywbem.WBEMConnection.OpenReferenceInstancePaths`

        This method performs the PullInstancePaths operation
        (see :term:`DSP0200`). See :ref:`WBEM operations` for a list of all
        methods performing such operations.

        If the operation succeeds, this method returns enumeration session
        status and optionally instance paths.
        Otherwise, this method raises an exception.

        Parameters:

          context (:func:`py:tuple` of server_context, namespace)
            A context object identifying the open enumeration session, including
            its current enumeration state, and the namespace. This object must
            have been returned by the previous open or pull operation for this
            enumeration session.

            The tuple items are:

            * server_context (:term:`string`):
              Enumeration context string returned by the server. This
              string is opaque for the client.
            * namespace (:term:`string`):
              Name of the CIM namespace being used for this enumeration session.

          MaxObjectCount (:class:`~pywbem.Uint32`)
            Maximum number of instances the WBEM server shall return
            for this request. This parameter is required for each
            Pull request.

            * If positive, the WBEM server is to return no more than the
              specified number of instances.
            * If zero, the WBEM server is to return no instances. This may
              be used by a client to reset the interoperation timer.
            * `None` is not allowed.

          **extra :
            Additional keyword arguments are passed as additional operation
            parameters to the WBEM server.
            Note that :term:`DSP0200` does not define any additional parameters
            for this operation.

        Returns:

            A :func:`~py:collections.namedtuple` object containing the following
            named items:

            * **paths** (:class:`py:list` of :class:`~pywbem.CIMInstanceName`):
              Representations of the retrieved instance paths, with their
              attributes set as follows:

              * `classname`: Name of the creation class of the instance.
              * `keybindings`: Keybindings of the instance.
              * `namespace`: Name of the CIM namespace containing the instance.
              * `host`: Host and optionally port of the WBEM server containing
                the CIM namespace.

            * **eos** (:class:`py:bool`):
              Indicates whether the enumeration session is exhausted after
              this operation:

              - If `True`, the enumeration session is exhausted, and the
                server has closed the enumeration session.
              - If `False`, the enumeration session is not exhausted and the
                `context` item is the context object for the next operation on
                the enumeration session.

            * **context** (:func:`py:tuple` of server_context, namespace):
              A context object identifying the open enumeration session,
              including its current enumeration state, and the namespace. This
              object must be supplied with the next pull or close operation for
              this enumeration session.

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

        exc = None
        result_tuple = None
        method_name = 'PullInstancePaths'

        if self._operation_recorders:
            self.operation_recorder_reset(pull_op=True)
            self.operation_recorder_stage_pywbem_args(
                method=method_name,
                context=context,
                MaxObjectCount=MaxObjectCount,
                **extra)

        try:

            stats = self.statistics.start_timer(method_name)
            _validatePullParams(MaxObjectCount, context)

            namespace = context[1]

            result = self._imethodcall(
                method_name,
                namespace=namespace,
                EnumerationContext=context[0],
                MaxObjectCount=MaxObjectCount,
                has_out_params=True,
                **extra)

            result_tuple = pull_path_result_tuple(
                *self._get_rslt_params(result, namespace))
            return result_tuple

        except (CIMXMLParseError, XMLParseError) as exce:
            exce.request_data = self.last_raw_request
            exce.response_data = self.last_raw_reply
            exc = exce
            raise
        except Exception as exce:
            exc = exce
            raise
        finally:
            self._last_operation_time = stats.stop_timer(
                self.last_request_len, self.last_reply_len,
                self.last_server_response_time, exc)
            if self._operation_recorders:
                self.operation_recorder_stage_result(result_tuple, exc)

    def PullInstances(self, context, MaxObjectCount, **extra):
        # pylint: disable=invalid-name
        """
        Retrieve the next set of instances (without instance paths) from an
        open enumeration session.

        *New in pywbem 0.9.*

        This operation can only be used on enumeration sessions that have been
        opened by one of the following methods:

        * :meth:`~pywbem.WBEMConnection.OpenQueryInstances`

        This method performs the PullInstances operation
        (see :term:`DSP0200`). See :ref:`WBEM operations` for a list of all
        methods performing such operations.

        If the operation succeeds, this method returns enumeration session
        status and optionally instances.
        Otherwise, this method raises an exception.

        Parameters:

          context (:func:`py:tuple` of server_context, namespace)
            A context object identifying the open enumeration session, including
            its current enumeration state, and the namespace. This object must
            have been returned by the previous open or pull operation for this
            enumeration session.

            The tuple items are:

            * server_context (:term:`string`):
              Enumeration context string returned by the server. This
              string is opaque for the client.
            * namespace (:term:`string`):
              Name of the CIM namespace being used for this enumeration session.

          MaxObjectCount (:class:`~pywbem.Uint32`)
            Maximum number of instances the WBEM server shall return
            for this request. This parameter is required for each
            Pull request.

            * If positive, the WBEM server is to return no more than the
              specified number of instances.
            * If zero, the WBEM server is to return no instances. This may
              be used by a client to reset the interoperation timer.
            * `None` is not allowed.

          **extra :
            Additional keyword arguments are passed as additional operation
            parameters to the WBEM server.
            Note that :term:`DSP0200` does not define any additional parameters
            for this operation.

        Returns:

            A :func:`~py:collections.namedtuple` object containing the following
            named items:

            * **instances** (:class:`py:list` of :class:`~pywbem.CIMInstance`):
              Representations of the retrieved instances.

              The `path` attribute of each :class:`~pywbem.CIMInstance`
              object is `None`, because this operation does not return instance
              paths.

            * **eos** (:class:`py:bool`):
              Indicates whether the enumeration session is exhausted after
              this operation:

              - If `True`, the enumeration session is exhausted, and the
                server has closed the enumeration session.
              - If `False`, the enumeration session is not exhausted and the
                `context` item is the context object for the next operation on
                the enumeration session.

            * **context** (:func:`py:tuple` of server_context, namespace):
              A context object identifying the open enumeration session,
              including its current enumeration state, and the namespace. This
              object must be supplied with the next pull or close operation for
              this enumeration session.

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
        exc = None
        result_tuple = None
        method_name = 'PullInstances'

        if self._operation_recorders:
            self.operation_recorder_reset(pull_op=True)
            self.operation_recorder_stage_pywbem_args(
                method=method_name,
                context=context,
                MaxObjectCount=MaxObjectCount,
                **extra)

        try:

            stats = self.statistics.start_timer(method_name)
            _validatePullParams(MaxObjectCount, context)

            namespace = context[1]

            result = self._imethodcall(
                method_name,
                namespace=namespace,
                EnumerationContext=context[0],
                MaxObjectCount=MaxObjectCount,
                has_out_params=True,
                **extra)

            result_tuple = pull_inst_result_tuple(
                *self._get_rslt_params(result, namespace))
            return result_tuple

        except (CIMXMLParseError, XMLParseError) as exce:
            exce.request_data = self.last_raw_request
            exce.response_data = self.last_raw_reply
            exc = exce
            raise
        except Exception as exce:
            exc = exce
            raise
        finally:
            self._last_operation_time = stats.stop_timer(
                self.last_request_len, self.last_reply_len,
                self.last_server_response_time, exc)
            if self._operation_recorders:
                self.operation_recorder_stage_result(result, exc)

    def CloseEnumeration(self, context, **extra):
        # pylint: disable=invalid-name
        """
        Close an open enumeration session, causing an early termination of an
        incomplete enumeration session.

        *New in pywbem 0.9.*

        This method performs the CloseEnumeration operation
        (see :term:`DSP0200`). See :ref:`WBEM operations` for a list of all
        methods performing such operations.

        The enumeration session must still be open when this operation is
        performed.

        If the operation succeeds, this method returns. Otherwise, it
        raises an exception.

        Parameters:

          context (:func:`py:tuple` of server_context, namespace)
            A context object identifying the open enumeration session, including
            its current enumeration state, and the namespace. This object must
            have been returned by the previous open or pull operation for this
            enumeration session.

            The tuple items are:

            * server_context (:term:`string`):
              Enumeration context string returned by the server. This
              string is opaque for the client.
            * namespace (:term:`string`):
              Name of the CIM namespace being used for this enumeration session.

          **extra :
            Additional keyword arguments are passed as additional operation
            parameters to the WBEM server.
            Note that :term:`DSP0200` does not define any additional parameters
            for this operation.

        Raises:

            Exceptions described in :class:`~pywbem.WBEMConnection`.
        """

        exc = None
        method_name = 'CloseEnumeration'

        if self._operation_recorders:
            self.operation_recorder_reset()
            self.operation_recorder_stage_pywbem_args(
                method=method_name,
                context=context,
                **extra)

        try:

            stats = self.statistics.start_timer(method_name)

            # entire context is tested for None because the open/pull methods
            # set the complete context to None when eos received.
            if context is None:
                raise ValueError("Invalid context: None "
                                 "(Enumeration may be exhausted)")

            self._imethodcall(
                method_name,
                namespace=context[1],
                EnumerationContext=context[0],
                has_return_value=False,
                **extra)
            return

        except (CIMXMLParseError, XMLParseError) as exce:
            exce.request_data = self.last_raw_request
            exce.response_data = self.last_raw_reply
            exc = exce
            raise
        except Exception as exce:
            exc = exce
            raise
        finally:
            self._last_operation_time = stats.stop_timer(
                self.last_request_len, self.last_reply_len,
                self.last_server_response_time, exc)
            if self._operation_recorders:
                self.operation_recorder_stage_result(None, exc)

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

            Leading and trailing slash characters will be stripped. The lexical
            case will be preserved.

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
              defines that the server-implemented default is `True`.

          IncludeClassOrigin (:class:`py:bool`):
            Indicates that class origin information is to be included on each
            property and method in the returned classes, as follows:

            * If `False`, class origin information is not included.
            * If `True`, class origin information is included.
            * If `None`, this parameter is not passed to the WBEM server, and
              causes the server-implemented default to be used. :term:`DSP0200`
              defines that the server-implemented default is `False`.

          **extra :
            Additional keyword arguments are passed as additional operation
            parameters to the WBEM server.
            Note that :term:`DSP0200` does not define any additional parameters
            for this operation.

        Returns:

            A list of :class:`~pywbem.CIMClass` objects that are
            representations of the enumerated classes, with their `path`
            attributes set.

        Raises:

            Exceptions described in :class:`~pywbem.WBEMConnection`.
        """

        exc = None
        classes = None
        method_name = 'EnumerateClasses'

        if self._operation_recorders:
            self.operation_recorder_reset()
            self.operation_recorder_stage_pywbem_args(
                method=method_name,
                namespace=namespace,
                ClassName=ClassName,
                DeepInheritance=DeepInheritance,
                LocalOnly=LocalOnly,
                IncludeQualifiers=IncludeQualifiers,
                IncludeClassOrigin=IncludeClassOrigin,
                **extra)

        try:

            stats = self.statistics.start_timer(method_name)
            if namespace is None and isinstance(ClassName, CIMClassName):
                namespace = ClassName.namespace
            namespace = self._iparam_namespace_from_namespace(namespace)
            classname = self._iparam_classname(ClassName)

            result = self._imethodcall(
                method_name,
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

            for klass in classes:

                if not isinstance(klass, CIMClass):
                    raise CIMXMLParseError(
                        _format("Expecting CIMClass object in result list, "
                                "got {0} object", klass.__class__.__name__),
                        conn_id=self.conn_id)

                # The EnumerateClasses CIM-XML operation returns classes
                # as CLASS elements, which do not contain a class path.
                # We want to return classes with a path (that has a namespace),
                # so we create the class path and set its namespace to the
                # effective target namespace.
                klass.path = CIMClassName(
                    classname=klass.classname, host=self.host,
                    namespace=namespace)

            return classes

        except (CIMXMLParseError, XMLParseError) as exce:
            exce.request_data = self.last_raw_request
            exce.response_data = self.last_raw_reply
            exc = exce
            raise
        except Exception as exce:
            exc = exce
            raise
        finally:
            self._last_operation_time = stats.stop_timer(
                self.last_request_len, self.last_reply_len,
                self.last_server_response_time, exc)
            if self._operation_recorders:
                self.operation_recorder_stage_result(classes, exc)

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

            Leading and trailing slash characters will be stripped. The lexical
            case will be preserved.

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

          **extra :
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

        exc = None
        classnames = None
        method_name = 'EnumerateClassNames'

        if self._operation_recorders:
            self.operation_recorder_reset()
            self.operation_recorder_stage_pywbem_args(
                method=method_name,
                namespace=namespace,
                ClassName=ClassName,
                DeepInheritance=DeepInheritance,
                **extra)

        try:

            stats = self.statistics.start_timer(method_name)
            if namespace is None and isinstance(ClassName, CIMClassName):
                namespace = ClassName.namespace
            namespace = self._iparam_namespace_from_namespace(namespace)
            classname = self._iparam_classname(ClassName)

            result = self._imethodcall(
                method_name,
                namespace,
                ClassName=classname,
                DeepInheritance=DeepInheritance,
                **extra)

            if result is None:
                classpaths = []
            else:
                classpaths = result[0][2]

            classnames = []
            for classpath in classpaths:

                if not isinstance(classpath, CIMClassName):
                    raise CIMXMLParseError(
                        _format("Expecting CIMClassName object in result "
                                "list, got {0} object",
                                classpath.__class__.__name__),
                        conn_id=self.conn_id)

                # The EnumerateClassNames CIM-XML operation returns class
                # paths as CLASSNAME elements.
                # We want to return class names as strings.
                classnames.append(classpath.classname)

            return classnames

        except (CIMXMLParseError, XMLParseError) as exce:
            exce.request_data = self.last_raw_request
            exce.response_data = self.last_raw_reply
            exc = exce
            raise
        except Exception as exce:
            exc = exce
            raise
        finally:
            self._last_operation_time = stats.stop_timer(
                self.last_request_len, self.last_reply_len,
                self.last_server_response_time, exc)
            if self._operation_recorders:
                self.operation_recorder_stage_result(classnames, exc)

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

            Leading and trailing slash characters will be stripped. The lexical
            case will be preserved.

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
              defines that the server-implemented default is `True`.

          IncludeClassOrigin (:class:`py:bool`):
            Indicates that class origin information is to be included on each
            property and method in the returned class, as follows:

            * If `False`, class origin information is not included.
            * If `True`, class origin information is included.
            * If `None`, this parameter is not passed to the WBEM server, and
              causes the server-implemented default to be used. :term:`DSP0200`
              defines that the server-implemented default is `False`.

          PropertyList (:term:`string` or :term:`py:iterable` of :term:`string`):
            An iterable specifying the names of the properties (or a string
            that defines a single property) to be included in the returned
            class (case independent).

            An empty iterable indicates to include no properties.

            If `None`, all properties are included.

          **extra :
            Additional keyword arguments are passed as additional operation
            parameters to the WBEM server.
            Note that :term:`DSP0200` does not define any additional parameters
            for this operation.

        Returns:

            A :class:`~pywbem.CIMClass` object that is a representation of the
            retrieved class, with its `path` attribute set.

        Raises:

            Exceptions described in :class:`~pywbem.WBEMConnection`.
        """  # noqa: E501

        klass = None
        exc = None
        method_name = 'GetClass'

        if self._operation_recorders:
            self.operation_recorder_reset()
            self.operation_recorder_stage_pywbem_args(
                method=method_name,
                ClassName=ClassName,
                namespace=namespace,
                LocalOnly=LocalOnly,
                IncludeQualifiers=IncludeQualifiers,
                IncludeClassOrigin=IncludeClassOrigin,
                PropertyList=PropertyList,
                **extra)

        try:

            stats = self.statistics.start_timer(method_name)
            if namespace is None and isinstance(ClassName, CIMClassName):
                namespace = ClassName.namespace
            namespace = self._iparam_namespace_from_namespace(namespace)
            classname = self._iparam_classname(ClassName)
            PropertyList = _iparam_propertylist(PropertyList)

            result = self._imethodcall(
                method_name,
                namespace,
                ClassName=classname,
                LocalOnly=LocalOnly,
                IncludeQualifiers=IncludeQualifiers,
                IncludeClassOrigin=IncludeClassOrigin,
                PropertyList=PropertyList,
                **extra)

            if result is None:
                raise CIMXMLParseError(
                    "Expecting a child element below IMETHODRESPONSE, "
                    "got no child elements", conn_id=self.conn_id)
            result = result[0][2]  # List of children of IRETURNVALUE

            if not result:
                raise CIMXMLParseError(
                    "Expecting a child element below IRETURNVALUE, "
                    "got no child elements", conn_id=self.conn_id)
            klass = result[0]  # CIMClass object

            if not isinstance(klass, CIMClass):
                raise CIMXMLParseError(
                    _format("Expecting CIMClass object, got {0} object",
                            klass.__class__.__name__),
                    conn_id=self.conn_id)

            # The GetClass CIM-XML operation returns the class as a CLASS
            # element, which does not contain a class path.
            # We want to return classes with a path (that has a namespace),
            # so we create the class path and set its namespace to the
            # effective target namespace.
            klass.path = CIMClassName(
                classname=klass.classname, host=self.host, namespace=namespace)

            return klass

        except (CIMXMLParseError, XMLParseError) as exce:
            exce.request_data = self.last_raw_request
            exce.response_data = self.last_raw_reply
            exc = exce
            raise
        except Exception as exce:
            exc = exce
            raise
        finally:
            self._last_operation_time = stats.stop_timer(
                self.last_request_len, self.last_reply_len,
                self.last_server_response_time, exc)
            if self._operation_recorders:
                self.operation_recorder_stage_result(klass, exc)

    def ModifyClass(self, ModifiedClass, namespace=None, **extra):
        # pylint: disable=invalid-name
        """
        Modify a class.

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

            Leading and trailing slash characters will be stripped. The lexical
            case will be preserved.

            If `None`, the default namespace of the connection object will be
            used.

          **extra :
            Additional keyword arguments are passed as additional operation
            parameters to the WBEM server.
            Note that :term:`DSP0200` does not define any additional parameters
            for this operation.

        Raises:

            Exceptions described in :class:`~pywbem.WBEMConnection`.
        """

        exc = None
        method_name = 'ModifyClass'

        if self._operation_recorders:
            self.operation_recorder_reset()
            self.operation_recorder_stage_pywbem_args(
                method=method_name,
                ModifiedClass=ModifiedClass,
                namespace=namespace,
                **extra)

        try:

            stats = self.statistics.start_timer(method_name)
            namespace = self._iparam_namespace_from_namespace(namespace)

            klass = ModifiedClass.copy()
            klass.path = None

            self._imethodcall(
                method_name,
                namespace,
                ModifiedClass=klass,
                has_return_value=False,
                **extra)
            return

        except (CIMXMLParseError, XMLParseError) as exce:
            exce.request_data = self.last_raw_request
            exce.response_data = self.last_raw_reply
            exc = exce
            raise
        except Exception as exce:
            exc = exce
            raise
        finally:
            self._last_operation_time = stats.stop_timer(
                self.last_request_len, self.last_reply_len,
                self.last_server_response_time, exc)
            if self._operation_recorders:
                self.operation_recorder_stage_result(None, exc)

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

            Leading and trailing slash characters will be stripped. The lexical
            case will be preserved.

            If `None`, the default namespace of the connection object will be
            used.

          **extra :
            Additional keyword arguments are passed as additional operation
            parameters to the WBEM server.
            Note that :term:`DSP0200` does not define any additional parameters
            for this operation.

        Raises:

            Exceptions described in :class:`~pywbem.WBEMConnection`.
        """

        exc = None
        method_name = 'CreateClass'
        if self._operation_recorders:
            self.operation_recorder_reset()
            self.operation_recorder_stage_pywbem_args(
                method=method_name,
                NewClass=NewClass,
                namespace=namespace,
                **extra)

        try:

            stats = self.statistics.start_timer(method_name)
            namespace = self._iparam_namespace_from_namespace(namespace)

            klass = NewClass.copy()
            klass.path = None

            self._imethodcall(
                method_name,
                namespace,
                NewClass=klass,
                has_return_value=False,
                **extra)
            return

        except (CIMXMLParseError, XMLParseError) as exce:
            exce.request_data = self.last_raw_request
            exce.response_data = self.last_raw_reply
            exc = exce
            raise
        except Exception as exce:
            exc = exce
            raise
        finally:
            self._last_operation_time = stats.stop_timer(
                self.last_request_len, self.last_reply_len,
                self.last_server_response_time, exc)
            if self._operation_recorders:
                self.operation_recorder_stage_result(None, exc)

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

            Leading and trailing slash characters will be stripped. The lexical
            case will be preserved.

            If `None`, the namespace of the `ClassName` parameter will be used,
            if specified as a :class:`~pywbem.CIMClassName` object. If that is
            also `None`, the default namespace of the connection will be used.

          **extra :
            Additional keyword arguments are passed as additional operation
            parameters to the WBEM server.
            Note that :term:`DSP0200` does not define any additional parameters
            for this operation.

        Raises:

            Exceptions described in :class:`~pywbem.WBEMConnection`.
        """

        exc = None
        method_name = 'DeleteClass'

        if self._operation_recorders:
            self.operation_recorder_reset()
            self.operation_recorder_stage_pywbem_args(
                method=method_name,
                ClassName=ClassName,
                namespace=namespace,
                **extra)

        try:

            stats = self.statistics.start_timer(method_name)
            if namespace is None and isinstance(ClassName, CIMClassName):
                namespace = ClassName.namespace
            namespace = self._iparam_namespace_from_namespace(namespace)
            classname = self._iparam_classname(ClassName)

            self._imethodcall(
                method_name,
                namespace,
                ClassName=classname,
                has_return_value=False,
                **extra)
            return

        except (CIMXMLParseError, XMLParseError) as exce:
            exce.request_data = self.last_raw_request
            exce.response_data = self.last_raw_reply
            exc = exce
            raise
        except Exception as exce:
            exc = exce
            raise
        finally:
            self._last_operation_time = stats.stop_timer(
                self.last_request_len, self.last_reply_len,
                self.last_server_response_time, exc)
            if self._operation_recorders:
                self.operation_recorder_stage_result(None, exc)

    def EnumerateQualifiers(self, namespace=None, **extra):
        # pylint: disable=invalid-name
        """
        Enumerate the qualifier types (= qualifier declarations) in a
        namespace.

        This method performs the EnumerateQualifiers operation
        (see :term:`DSP0200`). See :ref:`WBEM operations` for a list of all
        methods performing such operations.

        If the operation succeeds, this method returns.
        Otherwise, this method raises an exception.

        Parameters:

          namespace (:term:`string`):
            Name of the namespace in which the qualifier declarations are to be
            enumerated (case independent).

            Leading and trailing slash characters will be stripped. The lexical
            case will be preserved.

            If `None`, the default namespace of the connection object will be
            used.

          **extra :
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

        exc = None
        qualifiers = None
        method_name = 'EnumerateQualifiers'

        if self._operation_recorders:
            self.operation_recorder_reset()
            self.operation_recorder_stage_pywbem_args(
                method=method_name,
                namespace=namespace,
                **extra)

        try:

            stats = self.statistics.start_timer(method_name)
            namespace = self._iparam_namespace_from_namespace(namespace)

            result = self._imethodcall(
                method_name,
                namespace,
                **extra)

            if result is None:
                qualifierdecls = []
            else:
                qualifierdecls = result[0][2]

            for qualifierdecl in qualifierdecls:
                if not isinstance(qualifierdecl, CIMQualifierDeclaration):
                    raise CIMXMLParseError(
                        _format("Expecting CIMQualifierDeclaration object in "
                                "result list, got {0} object",
                                qualifierdecl.__class__.__name__),
                        conn_id=self.conn_id)

            return qualifierdecls

        except (CIMXMLParseError, XMLParseError) as exce:
            exce.request_data = self.last_raw_request
            exce.response_data = self.last_raw_reply
            exc = exce
            raise
        except Exception as exce:
            exc = exce
            raise
        finally:
            self._last_operation_time = stats.stop_timer(
                self.last_request_len, self.last_reply_len,
                self.last_server_response_time, exc)
            if self._operation_recorders:
                self.operation_recorder_stage_result(qualifiers, exc)

    def GetQualifier(self, QualifierName, namespace=None, **extra):
        # pylint: disable=invalid-name
        """
        Retrieve a qualifier type (= qualifier declaration).

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

            Leading and trailing slash characters will be stripped. The lexical
            case will be preserved.

            If `None`, the default namespace of the connection object will be
            used.

          **extra :
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

        exc = None
        qualifiername = None
        method_name = 'GetQualifier'

        if self._operation_recorders:
            self.operation_recorder_reset()
            self.operation_recorder_stage_pywbem_args(
                method=method_name,
                QualifierName=QualifierName,
                namespace=namespace,
                **extra)

        try:

            stats = self.statistics.start_timer(method_name)
            namespace = self._iparam_namespace_from_namespace(namespace)

            result = self._imethodcall(
                method_name,
                namespace,
                QualifierName=QualifierName,
                **extra)

            if result is None:
                raise CIMXMLParseError(
                    "Expecting a child element below IMETHODRESPONSE, "
                    "got no child elements", conn_id=self.conn_id)
            result = result[0][2]  # List of children of IRETURNVALUE

            if not result:
                raise CIMXMLParseError(
                    "Expecting a child element below IRETURNVALUE, "
                    "got no child elements", conn_id=self.conn_id)
            qualifierdecl = result[0]  # CIMQualifierDeclaration object

            if not isinstance(qualifierdecl, CIMQualifierDeclaration):
                raise CIMXMLParseError(
                    _format("Expecting CIMQualifierDeclaration object, got "
                            "{0} object", qualifierdecl.__class__.__name__),
                    conn_id=self.conn_id)

            return qualifierdecl

        except (CIMXMLParseError, XMLParseError) as exce:
            exce.request_data = self.last_raw_request
            exce.response_data = self.last_raw_reply
            exc = exce
            raise
        except Exception as exce:
            exc = exce
            raise
        finally:
            self._last_operation_time = stats.stop_timer(
                self.last_request_len, self.last_reply_len,
                self.last_server_response_time, exc)
            if self._operation_recorders:
                self.operation_recorder_stage_result(qualifiername, exc)

    def SetQualifier(self, QualifierDeclaration, namespace=None, **extra):
        # pylint: disable=invalid-name
        """
        Create or modify a qualifier type (= qualifier declaration) in a
        namespace.

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

            Leading and trailing slash characters will be stripped. The lexical
            case will be preserved.

            If `None`, the default namespace of the connection object will be
            used.

          **extra :
            Additional keyword arguments are passed as additional operation
            parameters to the WBEM server.
            Note that :term:`DSP0200` does not define any additional parameters
            for this operation.

        Raises:

            Exceptions described in :class:`~pywbem.WBEMConnection`.
        """

        exc = None
        method_name = 'SetQualifier'

        if self._operation_recorders:
            self.operation_recorder_reset()
            self.operation_recorder_stage_pywbem_args(
                method=method_name,
                QualifierDeclaration=QualifierDeclaration,
                namespace=namespace,
                **extra)

        try:

            stats = self.statistics.start_timer(method_name)
            namespace = self._iparam_namespace_from_namespace(namespace)

            self._imethodcall(
                method_name,
                namespace,
                QualifierDeclaration=QualifierDeclaration,
                has_return_value=False,
                **extra)
            return

        except (CIMXMLParseError, XMLParseError) as exce:
            exce.request_data = self.last_raw_request
            exce.response_data = self.last_raw_reply
            exc = exce
            raise
        except Exception as exce:
            exc = exce
            raise
        finally:
            self._last_operation_time = stats.stop_timer(
                self.last_request_len, self.last_reply_len,
                self.last_server_response_time, exc)
            if self._operation_recorders:
                self.operation_recorder_stage_result(None, exc)

    def DeleteQualifier(self, QualifierName, namespace=None, **extra):
        # pylint: disable=invalid-name
        """
        Delete a qualifier type (= qualifier declaration).

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

            Leading and trailing slash characters will be stripped. The lexical
            case will be preserved.

            If `None`, the default namespace of the connection object will be
            used.

          **extra :
            Additional keyword arguments are passed as additional operation
            parameters to the WBEM server.
            Note that :term:`DSP0200` does not define any additional parameters
            for this operation.

        Raises:

            Exceptions described in :class:`~pywbem.WBEMConnection`.
        """

        exc = None
        method_name = 'DeleteQualifier'

        if self._operation_recorders:
            self.operation_recorder_reset()
            self.operation_recorder_stage_pywbem_args(
                method=method_name,
                QualifierName=QualifierName,
                namespace=namespace,
                **extra)

        try:

            stats = self.statistics.start_timer(method_name)
            namespace = self._iparam_namespace_from_namespace(namespace)

            self._imethodcall(
                method_name,
                namespace,
                QualifierName=QualifierName,
                has_return_value=False,
                **extra)
            return

        except (CIMXMLParseError, XMLParseError) as exce:
            exce.request_data = self.last_raw_request
            exce.response_data = self.last_raw_reply
            exc = exce
            raise
        except Exception as exce:
            exc = exce
            raise
        finally:
            self._last_operation_time = stats.stop_timer(
                self.last_request_len, self.last_reply_len,
                self.last_server_response_time, exc)
            if self._operation_recorders:
                self.operation_recorder_stage_result(None, exc)


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

    Returns:
        :class:`py:bool`: Boolean True if the assertion is True (sub is a
        subclass of super_class) or False if it is not a subclass.

    Raises:
        CIMError if the the sub is not a valid class in the repo
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
    """ Openwbem specific Unix Domain Socket call. Specific because
        of the location of the file name
    """

    # pylint: disable=invalid-name
    return WBEMConnection('/tmp/OW@LCL@APIIPC_72859_Xq47Bf_P9r761-5_J-7_Q',
                          creds, **kwargs)
