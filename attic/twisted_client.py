#
# (C) Copyright 2005,2007 Hewlett-Packard Development Company, L.P.
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
#

"""pywbem.twisted - WBEM client bindings for Twisted Python.

This module contains factory classes that produce WBEMClient instances
that perform WBEM requests over HTTP using the
twisted.protocols.http.HTTPClient base class.
"""

import base64
from datetime import datetime, timedelta
try:
    from elementtree.ElementTree import fromstring, tostring
except ImportError:
    from xml.etree.ElementTree import fromstring, tostring
import six
from six.moves import urllib

from twisted.internet import reactor, protocol, defer
from twisted.web import http #, client, error

# TODO: Eww - we should get rid of the tupletree, tupleparse modules
# and replace with elementtree based code.
from . import cim_types, cim_xml, cim_obj, tupleparse, tupletree
from .cim_obj import CIMClass, CIMClassName, CIMInstance, CIMInstanceName
from .cim_operations import CIMError
from .cim_types import CIMDateTime

__all__ = ['WBEMClient', 'WBEMClientFactory', 'EnumerateInstances',
           'EnumerateInstanceNames', 'GetInstance', 'DeleteInstance',
           'CreateInstance', 'ModifyInstance', 'EnumerateClassNames',
           'EnumerateClasses', 'GetClass', 'Associators', 'AssociatorNames',
           'References', 'ReferenceNames', 'InvokeMethod', 'ExecQuery']

class WBEMClient(http.HTTPClient):
    """A HTTPClient subclass that handles WBEM requests."""

    status = None

    def connectionMade(self):
        """Send a HTTP POST command with the appropriate CIM over HTTP
        headers and payload."""

        self.factory.request_xml = str(self.factory.payload)

        self.sendCommand('POST', '/cimom')

        self.sendHeader('Host', '%s:%d' %
                        (self.transport.addr[0], self.transport.addr[1]))
        self.sendHeader('User-Agent', 'pywbem/twisted')
        self.sendHeader('Content-length', len(self.factory.payload))
        self.sendHeader('Content-type', 'application/xml')

        if self.factory.creds:
            auth = base64.b64encode('%s:%s' % (self.factory.creds[0],
                                               self.factory.creds[1]))

            self.sendHeader('Authorization', 'Basic %s' % auth)

        self.sendHeader('CIMOperation', str(self.factory.operation))
        self.sendHeader('CIMMethod', str(self.factory.method))
        self.sendHeader('CIMObject', str(self.factory.object))

        self.endHeaders()

        # TODO: Figure out why twisted doesn't support unicode.  An
        # exception should be thrown by the str() call if the payload
        # can't be converted to the current codepage.

        self.transport.write(str(self.factory.payload))

    def handleResponse(self, data):
        """Called when all response data has been received."""

        self.factory.response_xml = data

        if self.status == '200':
            self.factory.parseErrorAndResponse(data)

        self.factory.deferred = None
        self.transport.loseConnection()

    def handleStatus(self, version, status, message):
        """Save the status code for processing when we get to the end
        of the headers."""

        self.status = status
        self.message = message

    def handleHeader(self, key, value):
        """Handle header values."""

        if key == 'CIMError':
            self.CIMError = urllib.parse.unquote(value)
        if key == 'PGErrorDetail':
            self.PGErrorDetail = urllib.parse.unquote(value)

    def handleEndHeaders(self):
        """Check whether the status was OK and raise an error if not
        using previously saved header information."""

        if self.status != '200':

            if not hasattr(self, 'cimerror') or \
               not hasattr(self, 'errordetail'):

                self.factory.deferred.errback(
                    CIMError(0, 'HTTP error %s: %s' %
                             (self.status, self.message)))

            else:

                self.factory.deferred.errback(
                    CIMError(0, '%s: %s' % (cimerror, errordetail)))

class WBEMClientFactory(protocol.ClientFactory):
    """Create instances of the WBEMClient class."""

    request_xml = None
    response_xml = None
    xml_header = '<?xml version="1.0" encoding="utf-8" ?>'

    def __init__(self, creds, operation, method, object, payload):
        self.creds = creds
        self.operation = operation
        self.method = method
        self.object = object
        self.payload = payload
        self.protocol = lambda: WBEMClient()
        self.deferred = defer.Deferred()

    def clientConnectionFailed(self, connector, reason):
        if self.deferred is not None:
            reactor.callLater(0, self.deferred.errback, reason)

    def clientConnectionLost(self, connector, reason):
        if self.deferred is not None:
            reactor.callLater(0, self.deferred.errback, reason)

    def imethodcallPayload(self, methodname, localnsp, **kwargs):
        """Generate the XML payload for an intrinsic methodcall."""

        param_list = [pywbem.IPARAMVALUE(x[0], pywbem.tocimxml(x[1]))
                      for x in kwargs.items()]

        payload = cim_xml.CIM(
            cim_xml.MESSAGE(
                cim_xml.SIMPLEREQ(
                    cim_xml.IMETHODCALL(
                        methodname,
                        cim_xml.LOCALNAMESPACEPATH(
                            [cim_xml.NAMESPACE(ns)
                             for ns in localnsp.split('/')]),
                        param_list)),
                '1001', '1.0'),
            '2.0', '2.0')

        return self.xml_header + payload.toxml()

    def methodcallPayload(self, methodname, obj, namespace, **kwargs):
        """Generate the XML payload for an extrinsic methodcall."""

        if isinstance(obj, CIMInstanceName):

            path = obj.copy()

            path.host = None
            path.namespace = None

            localpath = cim_xml.LOCALINSTANCEPATH(
                cim_xml.LOCALNAMESPACEPATH(
                    [cim_xml.NAMESPACE(ns)
                     for ns in namespace.split('/')]),
                path.tocimxml())
        else:
            localpath = cim_xml.LOCALCLASSPATH(
                cim_xml.LOCALNAMESPACEPATH(
                    [cim_xml.NAMESPACE(ns)
                     for ns in namespace.split('/')]),
                obj)

        def paramtype(obj):
            """Return a string to be used as the CIMTYPE for a parameter."""
            if isinstance(obj, cim_types.CIMType):
                return obj.cimtype
            elif type(obj) == bool:
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
                return paramtype(obj[0])
            raise TypeError('Unsupported parameter type "%s"' % type(obj))

        def paramvalue(obj):
            """Return a cim_xml node to be used as the value for a
            parameter."""
            if isinstance(obj, (datetime, timedelta)):
                obj = CIMDateTime(obj)
            if isinstance(obj, (cim_types.CIMType, bool, six.string_types)):
                return cim_xml.VALUE(cim_types.atomic_to_cim_xml(obj))
            if isinstance(obj, (CIMClassName, CIMInstanceName)):
                return cim_xml.VALUE_REFERENCE(obj.tocimxml())
            if isinstance(obj, (CIMClass, CIMInstance)):
                return cim_xml.VALUE(obj.tocimxml().toxml())
            if isinstance(obj, list):
                if isinstance(obj[0], (CIMClassName, CIMInstanceName)):
                    return cim_xml.VALUE_REFARRAY([paramvalue(x) for x in obj])
                return cim_xml.VALUE_ARRAY([paramvalue(x) for x in obj])
            raise TypeError('Unsupported parameter type "%s"' % type(obj))

        param_list = [cim_xml.PARAMVALUE(x[0],
                                         paramvalue(x[1]),
                                         paramtype(x[1]))
                      for x in kwargs.items()]

        payload = cim_xml.CIM(
            cim_xml.MESSAGE(
                cim_xml.SIMPLEREQ(
                    cim_xml.METHODCALL(methodname,
                                       localpath,
                                       param_list)),
                '1001', '1.0'),
            '2.0', '2.0')

        return self.xml_header + payload.toxml()

    def parseErrorAndResponse(self, data):
        """Parse returned XML for errors, then convert into
        appropriate Python objects."""

        xml = fromstring(data)
        error = xml.find('.//ERROR')

        if error is None:
            self.deferred.callback(self.parseResponse(xml))
            return

        try:
            code = int(error.attrib['CODE'])
        except ValueError:
            code = 0

        self.deferred.errback(CIMError(code, error.attrib['DESCRIPTION']))

    def parseResponse(self, xml):
        """Parse returned XML and convert into appropriate Python
        objects.  Override in subclass"""

        pass

class EnumerateInstances(WBEMClientFactory):
    """Factory to produce EnumerateInstances WBEM clients."""

    def __init__(self, creds, classname, namespace='root/cimv2', **kwargs):

        self.classname = classname
        self.namespace = namespace

        payload = self.imethodcallPayload(
            'EnumerateInstances',
            namespace,
            ClassName=CIMClassName(classname),
            **kwargs)

        WBEMClientFactory.__init__(
            self,
            creds,
            operation='MethodCall',
            method='EnumerateInstances',
            object=namespace,
            payload=payload)

    def __repr__(self):
        return '<%s(/%s:%s) at 0x%x>' % \
               (self.__class__, self.namespace, self.classname, id(self))

    def parseResponse(self, xml):

        tt = [tupletree.xml_to_tupletree(tostring(x))
              for x in xml.findall('.//VALUE.NAMEDINSTANCE')]

        return [tupleparse.parse_value_namedinstance(x) for x in tt]

class EnumerateInstanceNames(WBEMClientFactory):
    """Factory to produce EnumerateInstanceNames WBEM clients."""

    def __init__(self, creds, classname, namespace='root/cimv2', **kwargs):

        self.classname = classname
        self.namespace = namespace

        payload = self.imethodcallPayload(
            'EnumerateInstanceNames',
            namespace,
            ClassName=CIMClassName(classname),
            **kwargs)

        WBEMClientFactory.__init__(
            self,
            creds,
            operation='MethodCall',
            method='EnumerateInstanceNames',
            object=namespace,
            payload=payload)

    def __repr__(self):
        return '<%s(/%s:%s) at 0x%x>' % \
               (self.__class__, self.namespace, self.classname, id(self))

    def parseResponse(self, xml):

        tt = [tupletree.xml_to_tupletree(tostring(x))
              for x in xml.findall('.//INSTANCENAME')]

        names = [tupleparse.parse_instancename(x) for x in tt]

        [setattr(n, 'namespace', self.namespace) for n in names]

        return names

class GetInstance(WBEMClientFactory):
    """Factory to produce GetInstance WBEM clients."""

    def __init__(self, creds, instancename, namespace='root/cimv2', **kwargs):

        self.instancename = instancename
        self.namespace = namespace

        payload = self.imethodcallPayload(
            'GetInstance',
            namespace,
            InstanceName=instancename,
            **kwargs)

        WBEMClientFactory.__init__(
            self,
            creds,
            operation='MethodCall',
            method='GetInstance',
            object=namespace,
            payload=payload)

    def __repr__(self):
        return '<%s(/%s:%s) at 0x%x>' % \
               (self.__class__, self.namespace, self.instancename, id(self))

    def parseResponse(self, xml):

        tt = tupletree.xml_to_tupletree(
            tostring(xml.find('.//INSTANCE')))

        return tupleparse.parse_instance(tt)

class DeleteInstance(WBEMClientFactory):
    """Factory to produce DeleteInstance WBEM clients."""

    def __init__(self, creds, instancename, namespace='root/cimv2', **kwargs):

        self.instancename = instancename
        self.namespace = namespace

        payload = self.imethodcallPayload(
            'DeleteInstance',
            namespace,
            InstanceName=instancename,
            **kwargs)

        WBEMClientFactory.__init__(
            self,
            creds,
            operation='MethodCall',
            method='DeleteInstance',
            object=namespace,
            payload=payload)

    def __repr__(self):
        return '<%s(/%s:%s) at 0x%x>' % \
               (self.__class__, self.namespace, self.instancename, id(self))

class CreateInstance(WBEMClientFactory):
    """Factory to produce CreateInstance WBEM clients."""

    # TODO: Implement __repr__ method

    def __init__(self, creds, instance, namespace='root/cimv2', **kwargs):

        payload = self.imethodcallPayload(
            'CreateInstance',
            namespace,
            NewInstance=instance,
            **kwargs)

        WBEMClientFactory.__init__(
            self,
            creds,
            operation='MethodCall',
            method='CreateInstance',
            object=namespace,
            payload=payload)

    def parseResponse(self, xml):

        tt = tupletree.xml_to_tupletree(
            tostring(xml.find('.//INSTANCENAME')))

        return tupleparse.parse_instancename(tt)

class ModifyInstance(WBEMClientFactory):
    """Factory to produce ModifyInstance WBEM clients."""

    # TODO: Implement __repr__ method

    def __init__(self, creds, instancename, instance, namespace='root/cimv2',
                 **kwargs):

        wrapped_instance = CIMInstanceName(instancename, instance)

        payload = self.imethodcallPayload(
            'ModifyInstance',
            namespace,
            ModifiedInstance=wrapped_instance,
            **kwargs)

        WBEMClientFactory.__init__(
            self,
            creds,
            operation='MethodCall',
            method='ModifyInstance',
            object=namespace,
            payload=payload)

class EnumerateClassNames(WBEMClientFactory):
    """Factory to produce EnumerateClassNames WBEM clients."""

    def __init__(self, creds, namespace='root/cimv2', **kwargs):

        self.localnsp = namespace

        payload = self.imethodcallPayload(
            'EnumerateClassNames',
            namespace,
            **kwargs)

        WBEMClientFactory.__init__(
            self,
            creds,
            operation='MethodCall',
            method='EnumerateClassNames',
            object=namespace,
            payload=payload)

    def __repr__(self):
        return '<%s(/%s) at 0x%x>' % \
               (self.__class__, self.namespace, id(self))

    def parseResponse(self, xml):

        tt = [tupletree.xml_to_tupletree(tostring(x))
              for x in xml.findall('.//CLASSNAME')]

        return [tupleparse.parse_classname(x) for x in tt]

class EnumerateClasses(WBEMClientFactory):
    """Factory to produce EnumerateClasses WBEM clients."""

    def __init__(self, creds, namespace='root/cimv2', **kwargs):

        self.localnsp = namespace
        self.namespace = namespace

        payload = self.imethodcallPayload(
            'EnumerateClasses',
            namespace,
            **kwargs)

        WBEMClientFactory.__init__(
            self,
            creds,
            operation='MethodCall',
            method='EnumerateClasses',
            object=namespace,
            payload=payload)

    def __repr__(self):
        return '<%s(/%s) at 0x%x>' % \
               (self.__class__, self.namespace, id(self))

    def parseResponse(self, xml):

        tt = [tupletree.xml_to_tupletree(tostring(x))
              for x in xml.findall('.//CLASS')]

        return [tupleparse.parse_class(x) for x in tt]

class GetClass(WBEMClientFactory):
    """Factory to produce GetClass WBEM clients."""

    def __init__(self, creds, classname, namespace='root/cimv2', **kwargs):

        self.classname = classname
        self.namespace = namespace

        payload = self.imethodcallPayload(
            'GetClass',
            namespace,
            ClassName=CIMClassName(classname),
            **kwargs)

        WBEMClientFactory.__init__(
            self,
            creds,
            operation='MethodCall',
            method='GetClass',
            object=namespace,
            payload=payload)

    def __repr__(self):
        return '<%s(/%s:%s) at 0x%x>' % \
               (self.__class__, self.namespace, self.classname, id(self))

    def parseResponse(self, xml):

        tt = tupletree.xml_to_tupletree(
            tostring(xml.find('.//CLASS')))

        return tupleparse.parse_class(tt)

class Associators(WBEMClientFactory):
    """Factory to produce Associators WBEM clients."""

    # TODO: Implement __repr__ method

    def __init__(self, creds, obj, namespace='root/cimv2', **kwargs):

        if isinstance(obj, CIMInstanceName):
            kwargs['ObjectName'] = obj
        else:
            kwargs['ObjectName'] = CIMClassName(obj)

        payload = self.imethodcallPayload(
            'Associators',
            namespace,
            **kwargs)

        WBEMClientFactory.__init__(
            self,
            creds,
            operation='MethodCall',
            method='Associators',
            object=namespace,
            payload=payload)

class AssociatorNames(WBEMClientFactory):
    """Factory to produce AssociatorNames WBEM clients."""

    # TODO: Implement __repr__ method

    def __init__(self, creds, obj, namespace='root/cimv2', **kwargs):

        if isinstance(obj, CIMInstanceName):
            kwargs['ObjectName'] = obj
        else:
            kwargs['ObjectName'] = CIMClassName(obj)

        payload = self.imethodcallPayload(
            'AssociatorNames',
            namespace,
            **kwargs)

        WBEMClientFactory.__init__(
            self,
            creds,
            operation='MethodCall',
            method='AssociatorNames',
            object=namespace,
            payload=payload)

    def parseResponse(self, xml):

        if len(xml.findall('.//INSTANCENAME')) > 0:

            tt = [tupletree.xml_to_tupletree(tostring(x))
                  for x in xml.findall('.//INSTANCENAME')]

            return [tupleparse.parse_instancename(x) for x in tt]

        else:

            tt = [tupletree.xml_to_tupletree(tostring(x))
                  for x in xml.findall('.//OBJECTPATH')]

            return [tupleparse.parse_objectpath(x)[2] for x in tt]

class References(WBEMClientFactory):
    """Factory to produce References WBEM clients."""

    def __init__(self, creds, obj, namespace='root/cimv2', **kwargs):

        if isinstance(obj, CIMInstanceName):
            kwargs['ObjectName'] = obj
        else:
            kwargs['ObjectName'] = CIMClassName(obj)

        payload = self.imethodcallPayload(
            'References',
            namespace,
            **kwargs)

        WBEMClientFactory.__init__(
            self,
            creds,
            operation='MethodCall',
            method='References',
            object=namespace,
            payload=payload)

class ReferenceNames(WBEMClientFactory):
    """Factory to produce ReferenceNames WBEM clients."""

    # TODO: Implement __repr__ method

    def __init__(self, creds, obj, namespace='root/cimv2', **kwargs):

        if isinstance(obj, CIMInstanceName):
            kwargs['ObjectName'] = obj
        else:
            kwargs['ObjectName'] = CIMClassName(obj)

        payload = self.imethodcallPayload(
            'ReferenceNames',
            namespace,
            **kwargs)

        WBEMClientFactory.__init__(
            self,
            creds,
            operation='MethodCall',
            method='ReferenceNames',
            object=namespace,
            payload=payload)

    def parseResponse(self, xml):

        if len(xml.findall('.//INSTANCENAME')) > 0:

            tt = [tupletree.xml_to_tupletree(tostring(x))
                  for x in xml.findall('.//INSTANCENAME')]

            return [tupleparse.parse_instancename(x) for x in tt]

        else:

            tt = [tupletree.xml_to_tupletree(tostring(x))
                  for x in xml.findall('.//OBJECTPATH')]

            return [tupleparse.parse_objectpath(x)[2] for x in tt]

class InvokeMethod(WBEMClientFactory):
    """Factory to produce InvokeMethod WBEM clients."""

    def __init__(self, creds, MethodName, ObjectName, namespace='root/cimv2',
                 **kwargs):

        # Convert string to CIMClassName

        obj = ObjectName

        if isinstance(obj, six.string_types):
            obj = CIMClassName(obj, namespace=namespace)

        if isinstance(obj, CIMInstanceName) and obj.namespace is None:
            obj = ObjectName.copy()
            obj.namespace = namespace

        # Make the method call

        payload = self.methodcallPayload(
            MethodName,
            obj,
            namespace,
            **kwargs)

        WBEMClientFactory.__init__(
            self,
            creds,
            operation='MethodCall',
            method=MethodName,
            object=obj,
            payload=payload)

    def parseResponse(self, xml):

        # Return value of method

        result_xml = tupletree.xml_to_tupletree(
            tostring(xml.find('.//RETURNVALUE')))

        result_tt = tupleparse.parse_any(result_xml)

        result = cim_obj.tocimobj(result_tt[1]['PARAMTYPE'],
                                  result_tt[2])

        # Output parameters

        params_xml = [tupletree.xml_to_tupletree(tostring(x))
                      for x in xml.findall('.//PARAMVALUE')]

        params_tt = [tupleparse.parse_any(x) for x in params_xml]

        params = {}

        for p in params_tt:
            if p[1] == 'reference':
                params[p[0]] = p[2]
            else:
                params[p[0]] = cim_obj.tocimobj(p[1], p[2])

        return (result, params)

class ExecQuery(WBEMClientFactory):

    def __init__(self, creds, QueryLanguage, Query, namespace='root/cimv2'):

        self.QueryLanguage = QueryLanguage
        self.Query = Query
        self.namespace = namespace

        payload = self.imethodcallPayload(
            'ExecQuery',
            namespace,
            QueryLanguage=QueryLanguage,
            Query=Query)

        WBEMClientFactory.__init__(
            self,
            creds,
            operation='MethodCall',
            method='ExecQuery',
            object=namespace,
            payload=payload)

    def __repr__(self):
        return '<%s(/%s:%s) at 0x%x>' % \
               (self.__class__, self.namespace, self.Query, id(self))

    def parseResponse(self, xml):
        tt = [pywbem.tupletree.xml_to_tupletree(tostring(x))
              for x in xml.findall('.//INSTANCE')]
        return [pywbem.tupleparse.parse_instance(x) for x in tt]
