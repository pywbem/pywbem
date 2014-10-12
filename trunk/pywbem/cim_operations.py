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
#

"""CIM operations over HTTP.

The `WBEMConnection` class in this module opens a connection to a remote
WBEM server. Across this connection you can run various CIM operations.
Each method of this class corresponds fairly directly to a single CIM
operation.
"""

# This module is meant to be safe for 'import *'.

import string
from types import StringTypes
from xml.dom import minidom
from datetime import datetime, timedelta

from pywbem import cim_obj, cim_xml, cim_http, cim_types, tupletree, tupleparse
from pywbem.cim_obj import CIMInstance, CIMInstanceName, CIMClass, \
                           CIMClassName, NocaseDict

DEFAULT_NAMESPACE = 'root/cimv2'


def _check_classname(val):
    """
    Validate a classname.

    At this point, only the type is validated to be a string.
    """
    if not isinstance(val, StringTypes):
        raise ValueError("string expected for classname, not %s" % `val`)


class CIMError(Exception):
    """
    Exception indicating that a CIM error has happened.

    The exception value is a tuple of ``(error_code, description)``, where:

      * ``error_code``: a numeric error code.

        A value of 0 indicates an error detected by the PyWBEM client, or a
        connection error, or an HTTP error reported by the WBEM server.

        Values other than 0 indicate that the WBEM server has returned an error
        response, and the value is the CIM status code of the error response.
        See `cim_constants` for constants defining CIM status code values.

      * ``description``: a string (`unicode` or UTF-8 encoded `str`)
        representing a human readable message describing the error. If
        `error_code` is not 0, this string is the CIM status description of the
        error response returned by the WBEM server. Otherwise, this is a
        message issued by the PyWBEM client.
    """


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

      - `pywbem.Error` - HTTP transport error.

      - `pywbem.AuthError` - Authentication failed with the WBEM server.

      - `pywbem.CIMError` - CIM error.

        With an ``error_code`` value of 0, the reason is one of:

        * Error in the arguments of a method.
        * Connection problem with the WBEM server.
        * HTTP-level errors reported by the WBEM server (except for HTTP
          transport errors and authentication failures).

        With other ``error_code`` values, the reason is always that the
        operation invoked on the WBEM server failed and returned a CIM error.
        For the possible CIM errors that can be returned by each operation, see
        DMTF DSP0200.

      - `pywbem.ParseError` - CIM-XML validation problem in the response from
        the WBEM server.

      - `xml.parsers.expat.ExpatError` - XML error in the response from the
        WBEM server, such as ill-formed XML or illegal XML characters.

    * Exceptions indicating programming errors in PyWBEM or layers below:

      - `TypeError`
      - `KeyError`
      - `ValueError`
      - ... possibly others ...

      Exceptions indicating programming errors should not happen and should be
      reported as bugs.

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
        on this connection, formatted as prettified XML.

      last_raw_request : `unicode`
        CIM-XML data of the last request sent to the WBEM server
        on this connection, formatted as it was sent.

      last_reply : `unicode`
        CIM-XML data of the last response received from the WBEM server
        on this connection, formatted as prettified XML.

      last_raw_reply : `unicode`
        CIM-XML data of the last response received from the WBEM server
        on this connection, formatted as it was received.
    """

    def __init__(self, url, creds=None, default_namespace=DEFAULT_NAMESPACE,
                 x509=None, verify_callback=None, ca_certs=None,
                 no_verification=False):
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

        :Exceptions:

            See the list of exceptions described in `WBEMConnection`.
        """

        self.url = url
        self.creds = creds
        self.x509 = x509
        self.verify_callback = verify_callback
        self.ca_certs = ca_certs
        self.no_verification = no_verification
        self.last_request = self.last_reply = ''
        self.default_namespace = default_namespace
        self.debug = False

    def __repr__(self):
        """
        Return a representation of the connection object with the major
        instance variables, except for the password in the credentials.

        TODO: Change to show all instance variables.
        """
        if self.creds is None:
            user = 'anonymous'
        else:
            user = 'user=%s' % `self.creds[0]`
        return "%s(%s, %s, namespace=%s)" % \
            (self.__class__.__name__, `self.url`, user,
             `self.default_namespace`)

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
                   cim_http.get_object_header(namespace)]

        # Create parameter list

        plist = map(lambda x:
                    cim_xml.IPARAMVALUE(x[0], cim_obj.tocimxml(x[1])),
                    params.items())

        # Build XML request

        req_xml = cim_xml.CIM(
            cim_xml.MESSAGE(
                cim_xml.SIMPLEREQ(
                    cim_xml.IMETHODCALL(
                        methodname,
                        cim_xml.LOCALNAMESPACEPATH(
                            [cim_xml.NAMESPACE(ns)
                             for ns in string.split(namespace, '/')]),
                        plist)),
                '1001', '1.0'),
            '2.0', '2.0')

        if self.debug:
            self.last_raw_request = req_xml.toxml()
            self.last_request = req_xml.toprettyxml(indent='  ')
            # Reset replies in case we fail before they are set
            self.last_reply = None
            self.last_raw_reply = None

        # Get XML response

        try:
            resp_xml = cim_http.wbem_request(
                self.url, req_xml.toxml(), self.creds, headers,
                x509=self.x509,
                verify_callback=self.verify_callback,
                ca_certs=self.ca_certs,
                no_verification=self.no_verification)
        except cim_http.AuthError:
            raise
        except cim_http.Error, arg:
            # Convert cim_http exceptions to CIMError exceptions
            raise CIMError(0, str(arg))

        ## TODO: Perhaps only compute this if it's required?  Should not be
        ## all that expensive.

        reply_dom = minidom.parseString(resp_xml)

        if self.debug:
            self.last_reply = reply_dom.toprettyxml(indent='  ')
            self.last_raw_reply = resp_xml

        # Parse response

        tt = tupleparse.parse_cim(tupletree.dom_to_tupletree(reply_dom))

        if tt[0] != 'CIM':
            raise CIMError(0, 'Expecting CIM element, got %s' % tt[0])
        tt = tt[2]

        if tt[0] != 'MESSAGE':
            raise CIMError(0, 'Expecting MESSAGE element, got %s' % tt[0])
        tt = tt[2]

        if len(tt) != 1 or tt[0][0] != 'SIMPLERSP':
            raise CIMError(0, 'Expecting one SIMPLERSP element')
        tt = tt[0][2]

        if tt[0] != 'IMETHODRESPONSE':
            raise CIMError(
                0, 'Expecting IMETHODRESPONSE element, got %s' % tt[0])

        if tt[1]['NAME'] != methodname:
            raise CIMError(0, 'Expecting attribute NAME=%s, got %s' %
                           (methodname, tt[1]['NAME']))
        tt = tt[2]

        # At this point we either have a IRETURNVALUE, ERROR element
        # or None if there was no child nodes of the IMETHODRESPONSE
        # element.

        if tt is None:
            return None

        if tt[0] == 'ERROR':
            code = int(tt[1]['CODE'])
            if tt[1].has_key('DESCRIPTION'):
                raise CIMError(code, tt[1]['DESCRIPTION'])
            raise CIMError(code, 'Error code %s' % tt[1]['CODE'])

        if tt[0] != 'IRETURNVALUE':
            raise CIMError(0, 'Expecting IRETURNVALUE element, got %s' % tt[0])

        return tt

    def methodcall(self, methodname, localobject, **params):
        """
        Perform an extrinsic method call (= CIM method invocation).

        This is a low-level function that is used by the 'InvokeMethod'
        method of this class. In general, clients should use 'InvokeMethod'
        instead of this function.

        The parameters are automatically converted to the right CIM-XML
        elements.

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
                   cim_http.get_object_header(localobject)]

        # Create parameter list

        def paramtype(obj):
            """Return a string to be used as the CIMTYPE for a parameter."""
            if isinstance(obj, cim_types.CIMType):
                return obj.cimtype
            elif type(obj) == bool:
                return 'boolean'
            elif isinstance(obj, StringTypes):
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
                obj = cim_types.CIMDateTime(obj)
            if isinstance(obj, (cim_types.CIMType, bool, StringTypes)):
                return cim_xml.VALUE(cim_types.atomic_to_cim_xml(obj))
            if isinstance(obj, (CIMClassName, CIMInstanceName)):
                return cim_xml.VALUE_REFERENCE(obj.tocimxml())
            if isinstance(obj, (CIMClass, CIMInstance)):
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

        plist = [cim_xml.PARAMVALUE(x[0],
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
            self.last_request = req_xml.toprettyxml(indent='  ')
            self.last_raw_request = req_xml.toxml()
            # Reset replies in case we fail before they are set
            self.last_reply = None
            self.last_raw_reply = None

        # Get XML response

        try:
            resp_xml = cim_http.wbem_request(
                self.url, req_xml.toxml(), self.creds, headers,
                x509=self.x509,
                verify_callback=self.verify_callback,
                ca_certs=self.ca_certs,
                no_verification=self.no_verification)
        except cim_http.Error, arg:
            # Convert cim_http exceptions to CIMError exceptions
            raise CIMError(0, str(arg))

        if self.debug:
            self.last_raw_reply = resp_xml
            resp_dom = minidom.parseString(resp_xml)
            self.last_reply = resp_dom.toprettyxml(indent='  ')

        tt = tupleparse.parse_cim(tupletree.xml_to_tupletree(resp_xml))

        if tt[0] != 'CIM':
            raise CIMError(0, 'Expecting CIM element, got %s' % tt[0])
        tt = tt[2]

        if tt[0] != 'MESSAGE':
            raise CIMError(0, 'Expecting MESSAGE element, got %s' % tt[0])
        tt = tt[2]

        if len(tt) != 1 or tt[0][0] != 'SIMPLERSP':
            raise CIMError(0, 'Expecting one SIMPLERSP element')
        tt = tt[0][2]

        if tt[0] != 'METHODRESPONSE':
            raise CIMError(
                0, 'Expecting METHODRESPONSE element, got %s' % tt[0])

        if tt[1]['NAME'] != methodname:
            raise CIMError(0, 'Expecting attribute NAME=%s, got %s' %
                           (methodname, tt[1]['NAME']))
        tt = tt[2]

        # At this point we have an optional RETURNVALUE and zero or
        # more PARAMVALUE elements representing output parameters.

        if len(tt) > 0 and tt[0][0] == 'ERROR':
            code = int(tt[0][1]['CODE'])
            if tt[0][1].has_key('DESCRIPTION'):
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

        [setattr(n, 'namespace', namespace) for n in names]

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

        [setattr(i.path, 'namespace', namespace) for i in instances]

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

        [setattr(i.path, 'namespace', namespace) for i in instances]

        return instances

    #
    # Schema management API
    #

    def _map_classname_param(self, params):
        """Convert string ClassName parameter to a CIMClassName."""

        if params.has_key('ClassName') and \
           isinstance(params['ClassName'], StringTypes):
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
            Optional: Name of the namespace of the class, as a string.
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
            return map(lambda x: x.classname, result[2])

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
            Optional: Name of the namespace of the class, as a string.
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
            Optional: Name of the namespace of the class, as a string.
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

        TODO This method is UNSUPPORTED right now. Test and verify description.

        :Parameters:

          ClassName : string
            Name of the class to be deleted.

          namespace : string
            Optional: Name of the namespace of the class, as a string.
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

        TODO This method is UNSUPPORTED right now. Test and verify description.

        :Parameters:

          ModifiedClass : `CIMClass`
            A representation of the modified class. This object needs to
            contain any modified properties, methods and qualifiers and the
            class path of the class to be modified.
            Typically, this object has been retrieved by other operations, such
            as GetClass.

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

        This method performs the ModifyClass CIM-XML operation.
        If the operation succeeds, this method returns.
        Otherwise, this method raises an exception.

        TODO This method is UNSUPPORTED right now. Test and verify description.

        :Parameters:

          NewClass : `CIMClass`
            A representation of the class to be created. This object needs to
            contain any properties, methods, qualifiers, superclass name, and
            the class name of the class to be created.
            The class path in this object (`path` instance variable) will be
            ignored.

          namespace : string
            Optional: Name of the namespace in which the class is to be
            created. The value `None` causes the default namespace of the
            connection to be used.

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

    def _add_objectname_param(self, params, object):
        """Add an object name (either a class name or an instance
        name) to a dictionary of parameter names."""

        if isinstance(object, (CIMClassName, CIMInstanceName)):
            params['ObjectName'] = object.copy()
            params['ObjectName'].namespace = None
        elif isinstance(object, StringTypes):
            params['ObjectName'] = CIMClassName(object)
        else:
            raise ValueError('Expecting a classname, CIMClassName or '
                             'CIMInstanceName object')

        return params

    def _map_association_params(self, params):
        """Convert various convenience parameters and types into their
        correct form for passing to the imethodcall() function."""

        # ResultClass and Role parameters that are strings should be
        # mapped to CIMClassName objects.

        if params.has_key('ResultClass') and \
           isinstance(params['ResultClass'], StringTypes):
            params['ResultClass'] = CIMClassName(params['ResultClass'])

        if params.has_key('AssocClass') and \
           isinstance(params['AssocClass'], StringTypes):
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

        return map(lambda x: x[2], result[2])

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

        return map(lambda x: x[2], result[2])

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

        return map(lambda x: x[2], result[2])

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

        return map(lambda x: x[2], result[2])

    #
    # Method provider API
    #

    def InvokeMethod(self, MethodName, ObjectName, **params):
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

          {paramname}
            An input parameter for the CIM method. This Python method parameter
            must be provided for each CIM method input parameter (there is no
            concept of optional method parameters in CIM). The name of this
            Python method parameter must be the name of the CIM method
            parameter. The value of this Python method parameter must be a CIM
            typed value as described in `cim_types`.

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

        if isinstance(obj, StringTypes):
            obj = CIMClassName(obj, namespace=self.default_namespace)

        if isinstance(obj, CIMInstanceName) and obj.namespace is None:
            obj = ObjectName.copy()
            obj.namespace = self.default_namespace

        # Make the method call

        result = self.methodcall(MethodName, obj, **params)

        # Convert optional RETURNVALUE into a Python object

        returnvalue = None

        if len(result) > 0 and result[0][0] == 'RETURNVALUE':

            returnvalue = cim_obj.tocimobj(result[0][1]['PARAMTYPE'],
                                           result[0][2])
            result = result[1:]

        # Convert zero or more PARAMVALUE elements into dictionary

        output_params = NocaseDict()

        for p in result:
            if p[1] == 'reference':
                output_params[p[0]] = p[2]
            else:
                output_params[p[0]] = cim_obj.tocimobj(p[1], p[2])

        return returnvalue, output_params

    #
    # Qualifiers API
    #

    def EnumerateQualifiers(self, namespace=None, **params):
        # pylint: disable=invalid-name
        """
        Enumerate qualifier types.

        Returns a list of `CIMQualifier` objects.

        TODO Complete this description.
        """

        if namespace is None:
            namespace = self.default_namespace

        result = self.imethodcall(
            'EnumerateQualifiers',
            namespace,
            **params)

        qualifiers = []

        if result is not None:
            names = result[2]
        else:
            names = []

        return names

    def GetQualifier(self, QualifierName, namespace=None, **params):
        # pylint: disable=invalid-name
        """
        Retrieve a qualifier type.

        Returns a `CIMQualifier` object.

        TODO Complete this description.
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
        Create or modify a qualifier type.

        TODO Complete this description.
        """

        if namespace is None:
            namespace = self.default_namespace

        result = self.imethodcall(
            'SetQualifier',
            namespace,
            QualifierDeclaration=QualifierDeclaration,
            **params)

    def DeleteQualifier(self, QualifierName, namespace=None, **params):
        # pylint: disable=invalid-name
        """
        Delete a qualifier type.

        TODO Complete this description.
        """

        if namespace is None:
            namespace = self.default_namespace

        result = self.imethodcall(
            'DeleteQualifier',
            namespace,
            QualifierName=QualifierName,
            **params)

def is_subclass(ch, ns, super, sub):
    """Determine if one class is a subclass of another

    Keyword Arguments:
    ch -- A CIMOMHandle.  Either a pycimmb.CIMOMHandle or a
        pywbem.WBEMConnection.
    ns -- Namespace.
    super -- A string containing the super class name.
    sub -- The subclass.  This can either be a string or a pywbem.CIMClass.

    """

    lsuper = super.lower()
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
    # pylint: disable=invalid-name
    return WBEMConnection('/var/run/tog-pegasus/cimxml.socket', creds, **kwargs)

def SFCBUDSConnection(creds=None, **kwargs):
    # pylint: disable=invalid-name
    return WBEMConnection('/tmp/sfcbHttpSocket', creds, **kwargs)

def OpenWBEMUDSConnection(creds=None, **kwargs):
    # pylint: disable=invalid-name
    return WBEMConnection('/tmp/OW@LCL@APIIPC_72859_Xq47Bf_P9r761-5_J-7_Q',
                          creds, **kwargs)
