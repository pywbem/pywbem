#
# (C) Copyright 2005 Hewlett-Packard Development Company, L.P.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#   
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#   
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
#

# Author: Tim Potter <tpot@hp.com>

"""pywbem.twisted - WBEM client bindings for Twisted Python.

This module contains factory classes that produce WBEMClient instances
that perform WBEM requests over HTTP using the
twisted.protocols.http.HTTPClient base class.
"""

from twisted.internet import protocol, defer
from twisted.protocols import http
from twisted.web import client, error

import pywbem

from pywbem import CIMClassName, CIMInstanceName, CIMError

from elementtree.ElementTree import fromstring, tostring

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

        import base64
        auth = base64.encodestring('%s:%s' % (self.factory.creds[0],
                                              self.factory.creds[1]))[:-1]

        self.sendHeader('Authorization', 'Basic %s' % auth)

        self.sendHeader('CIMOperation', self.factory.operation)
        self.sendHeader('CIMMethod', self.factory.method)
        self.sendHeader('CIMObject', self.factory.object)

        self.endHeaders()
        
        self.transport.write(self.factory.payload)
        
    def handleResponse(self, data):
        """Called when all response data has been received."""
        
        self.factory.response_xml = data

        if self.status == '200':
            self.factory.parseErrorAndResponse(data)

    def handleStatus(self, version, status, message):
        """Save the status code for processing when we get to the end
        of the headers."""

        self.status = status
        self.message = message

    def handleHeader(self, key, value):
        """Handle header values."""

        import urllib
        if key == 'CIMError':
            self.CIMError = urllib.unquote(value)
        if key == 'PGErrorDetail':
            self.PGErrorDetail = urllib.unquote(value)

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

    def imethodcallPayload(self, methodname, localnsp, **kwargs):
        """Generate the XML payload for an intrinsic methodcall."""
        
        param_list = [pywbem.IPARAMVALUE(x[0], pywbem.tocimxml(x[1]))
                      for x in kwargs.items()]

        payload = pywbem.CIM(
            pywbem.MESSAGE(
                pywbem.SIMPLEREQ(
                    pywbem.IMETHODCALL(
                        methodname,
                        pywbem.LOCALNAMESPACEPATH(
                            [cim_xml.NAMESPACE(ns)
                             for ns in string.split(localnsp, '/')]),
                        param_list)),
                1001, '1.0'),
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
        objects."""
        pass

# TODO: Eww - we should get rid of the tupletree, tupleparse modules
# and replace with elementtree based code.

import pywbem.tupletree

class EnumerateInstances(WBEMClientFactory):
    """Factory to produce EnumerateInstances WBEM clients."""
    
    def __init__(self, creds, classname,
                 LocalNamespacePath = 'root/cimv2', **kwargs):

        self.classname = classname
        self.localnsp = LocalNamespacePath

        payload = self.imethodcallPayload(
            'EnumerateInstances',
            LocalNamespacePath,
            ClassName = CIMClassName(classname),
            **kwargs)

        WBEMClientFactory.__init__(
            self, creds, 'MethodCall', 'EnumerateInstances',
            LocalNamespacePath, payload)

    def __repr__(self):
        return '<%s(/%s:%s) at 0x%x>' % \
               (self.__class__, self.localnsp, self.classname, id(self))

    def parseResponse(self, xml):

        tt = [pywbem.tupletree.xml_to_tupletree(tostring(x))
              for x in xml.findall('.//VALUE.NAMEDINSTANCE')]
        
        return [pywbem.tupleparse.parse_value_namedinstance(x)[2] for x in tt]

class EnumerateInstanceNames(WBEMClientFactory):
    """Factory to produce EnumerateInstanceNames WBEM clients."""
    
    def __init__(self, creds, classname,
                 LocalNamespacePath = 'root/cimv2', **kwargs):

        self.classname = classname
        self.localnsp = LocalNamespacePath

        payload = self.imethodcallPayload(
            'EnumerateInstanceNames',
            LocalNamespacePath,
            ClassName = CIMClassName(classname),
            **kwargs)

        WBEMClientFactory.__init__(
            self, creds, 'MethodCall', 'EnumerateInstanceNames',
            LocalNamespacePath, payload)

    def __repr__(self):
        return '<%s(/%s:%s) at 0x%x>' % \
               (self.__class__, self.localnsp, self.classname, id(self))

    def parseResponse(self, xml):

        tt = [pywbem.tupletree.xml_to_tupletree(tostring(x))
              for x in xml.findall('.//INSTANCENAME')]
        
        return [pywbem.tupleparse.parse_instancename(x) for x in tt]

class GetInstance(WBEMClientFactory):
    """Factory to produce GetInstance WBEM clients."""
    
    def __init__(self, creds, instancename,
                 LocalNamespacePath = 'root/cimv2', **kwargs):

        self.instancename = instancename
        self.localnsp = LocalNamespacePath

        payload = self.imethodcallPayload(
            'GetInstance',
            LocalNamespacePath,
            InstanceName = instancename,
            **kwargs)

        WBEMClientFactory.__init__(
            self, creds, 'MethodCall', 'GetInstance',
            LocalNamespacePath, payload)

    def __repr__(self):
        return '<%s(/%s:%s) at 0x%x>' % \
               (self.__class__, self.localnsp, self.instancename, id(self))

    def parseResponse(self, xml):

        tt = pywbem.tupletree.xml_to_tupletree(
            tostring(xml.find('.//INSTANCE')))

        return pywbem.tupleparse.parse_instance(tt)

class DeleteInstance(WBEMClientFactory):
    """Factory to produce DeleteInstance WBEM clients."""
    
    def __init__(self, creds, instancename,
                 LocalNamespacePath = 'root/cimv2', **kwargs):

        self.instancename = instancename
        self.localnsp = LocalNamespacePath

        payload = self.imethodcallPayload(
            'DeleteInstance',
            LocalNamespacePath,
            InstanceName = instancename,
            **kwargs)

        WBEMClientFactory.__init__(
            self, creds, 'MethodCall', 'DeleteInstance',
            LocalNamespacePath, payload)

    def __repr__(self):
        return '<%s(/%s:%s) at 0x%x>' % \
               (self.__class__, self.localnsp, self.instancename, id(self))

class CreateInstance(WBEMClientFactory):
    """Factory to produce CreateInstance WBEM clients."""
    
    # TODO: Implement __repr__ method

    def __init__(self, creds, instance,
                 LocalNamespacePath = 'root/cimv2', **kwargs):

        payload = self.imethodcallPayload(
            'CreateInstance',
            LocalNamespacePath,
            NewInstance = instance,
            **kwargs)

        WBEMClientFactory.__init__(
            self, creds, 'MethodCall', 'CreateInstance',
            LocalNamespacePath, payload)

class ModifyInstance(WBEMClientFactory):
    """Factory to produce ModifyInstance WBEM clients."""
    
    # TODO: Implement __repr__ method

    def __init__(self, creds, instancename, instance,
                 LocalNamespacePath = 'root/cimv2', **kwargs):

        wrapped_instance = CIMNamedInstance(instancename, instance)

        payload = self.imethodcallPayload(
            'ModifyInstance',
            LocalNamespacePath,
            ModifiedInstance = wrapped_instance,
            **kwargs)

        WBEMClientFactory.__init__(
            self, creds, 'MethodCall', 'ModifyInstance',
            LocalNamespacePath, payload)

class EnumerateClassNames(WBEMClientFactory):
    """Factory to produce EnumerateClassNames WBEM clients."""
    
    def __init__(self, creds, LocalNamespacePath = 'root/cimv2', **kwargs):

        self.localnsp = LocalNamespacePath

        payload = self.imethodcallPayload(
            'EnumerateClassNames',
            LocalNamespacePath,
            **kwargs)

        WBEMClientFactory.__init__(
            self, creds, 'MethodCall', 'EnumerateClassNames',
            LocalNamespacePath, payload)

    def __repr__(self):
        return '<%s(/%s) at 0x%x>' % \
               (self.__class__, self.localnsp, id(self))

    def parseResponse(self, xml):

        tt = [pywbem.tupletree.xml_to_tupletree(tostring(x))
              for x in xml.findall('.//CLASSNAME')]
        
        return [pywbem.tupleparse.parse_classname(x) for x in tt]        

class EnumerateClasses(WBEMClientFactory):
    """Factory to produce EnumerateClasses WBEM clients."""
    
    def __init__(self, creds, LocalNamespacePath = 'root/cimv2', **kwargs):

        self.localnsp = LocalNamespacePath

        payload = self.imethodcallPayload(
            'EnumerateClasses',
            LocalNamespacePath,
            **kwargs)

        WBEMClientFactory.__init__(
            self, creds, 'MethodCall', 'EnumerateClasses',
            LocalNamespacePath, payload)

    def __repr__(self):
        return '<%s(/%s) at 0x%x>' % \
               (self.__class__, self.localnsp, id(self))

    def parseResponse(self, xml):

        tt = [pywbem.tupletree.xml_to_tupletree(tostring(x))
              for x in xml.findall('.//CLASS')]
        
        return [pywbem.tupleparse.parse_class(x) for x in tt]        

class GetClass(WBEMClientFactory):
    """Factory to produce GetClass WBEM clients."""
    
    def __init__(self, creds, classname,
                 LocalNamespacePath = 'root/cimv2', **kwargs):

        self.classname = classname
        self.localnsp = LocalNamespacePath

        payload = self.imethodcallPayload(
            'GetClass',
            LocalNamespacePath,
            ClassName = CIMClassName(classname),
            **kwargs)

        WBEMClientFactory.__init__(
            self, creds, 'MethodCall', 'GetClass',
            LocalNamespacePath, payload)

    def __repr__(self):
        return '<%s(/%s:%s) at 0x%x>' % \
               (self.__class__, self.localnsp, self.classname, id(self))

    def parseResponse(self, xml):

        tt = pywbem.tupletree.xml_to_tupletree(
            tostring(xml.find('.//CLASS')))

        return pywbem.tupleparse.parse_class(tt)

class Associators(WBEMClientFactory):
    """Factory to produce Associators WBEM clients."""
    
    # TODO: Implement __repr__ method

    def __init__(self, creds, obj,
                 LocalNamespacePath = 'root/cimv2', **kwargs):

        if isinstance(obj, CIMInstanceName):
            kwargs['ObjectName'] = obj
        else:
            kwargs['ObjectName'] = CIMClassName(obj)

        payload = self.imethodcallPayload(
            'Associators',
            LocalNamespacePath,
            **kwargs)

        WBEMClientFactory.__init__(
            self, creds, 'MethodCall', 'Associators',
            LocalNamespacePath, payload)

class AssociatorNames(WBEMClientFactory):
    """Factory to produce AssociatorNames WBEM clients."""
    
    # TODO: Implement __repr__ method

    def __init__(self, creds, obj,
                 LocalNamespacePath = 'root/cimv2', **kwargs):

        if isinstance(obj, CIMInstanceName):
            kwargs['ObjectName'] = obj
        else:
            kwargs['ObjectName'] = CIMClassName(obj)

        payload = self.imethodcallPayload(
            'AssociatorNames',
            LocalNamespacePath,
            **kwargs)

        WBEMClientFactory.__init__(
            self, creds, 'MethodCall', 'AssociatorNames',
            LocalNamespacePath, payload)

    def parseResponse(self, xml):

        if len(xml.findall('.//INSTANCENAME')) > 0:

            tt = [pywbem.tupletree.xml_to_tupletree(tostring(x))
                  for x in xml.findall('.//INSTANCENAME')]

            return [pywbem.tupleparse.parse_instancename(x) for x in tt]
        
        else:
            
            tt = [pywbem.tupletree.xml_to_tupletree(tostring(x))
                  for x in xml.findall('.//OBJECTPATH')]
            
            return [pywbem.tupleparse.parse_objectpath(x)[2] for x in tt]

class References(WBEMClientFactory):
    """Factory to produce References WBEM clients."""
    
    def __init__(self, creds, obj,
                 LocalNamespacePath = 'root/cimv2', **kwargs):

        if isinstance(obj, CIMInstanceName):
            kwargs['ObjectName'] = obj
        else:
            kwargs['ObjectName'] = CIMClassName(obj)

        payload = self.imethodcallPayload(
            'References',
            LocalNamespacePath,
            **kwargs)

        WBEMClientFactory.__init__(
            self, creds, 'MethodCall', 'References',
            LocalNamespacePath, payload)

class ReferenceNames(WBEMClientFactory):
    """Factory to produce ReferenceNames WBEM clients."""
    
    # TODO: Implement __repr__ method

    def __init__(self, creds, obj,
                 LocalNamespacePath = 'root/cimv2', **kwargs):

        if isinstance(obj, CIMInstanceName):
            kwargs['ObjectName'] = obj
        else:
            kwargs['ObjectName'] = CIMClassName(obj)

        payload = self.imethodcallPayload(
            'ReferenceNames',
            LocalNamespacePath,
            **kwargs)

        WBEMClientFactory.__init__(
            self, creds, 'MethodCall', 'ReferenceNames',
            LocalNamespacePath, payload)

    def parseResponse(self, xml):

        if len(xml.findall('.//INSTANCENAME')) > 0:

            tt = [pywbem.tupletree.xml_to_tupletree(tostring(x))
                  for x in xml.findall('.//INSTANCENAME')]

            return [pywbem.tupleparse.parse_instancename(x) for x in tt]
        
        else:
            
            tt = [pywbem.tupletree.xml_to_tupletree(tostring(x))
                  for x in xml.findall('.//OBJECTPATH')]
            
            return [pywbem.tupleparse.parse_objectpath(x)[2] for x in tt]
