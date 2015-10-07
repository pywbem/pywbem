#! /usr/bin/python
#
# (C) Copyright 2003, 2004, 2005 Hewlett-Packard Development Company, L.P.
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
#         Martin Pool <mbp@hp.com>

# This is meant to be safe for import *; ie the only global names
# should be ones that all clients can see.

import sys, string
from types import StringTypes
from xml.dom import minidom
import cim_obj, cim_xml, cim_http
from cim_obj import CIMClassName, CIMNamedInstance, CIMInstanceName, \
     CIMLocalInstancePath

from tupletree import dom_to_tupletree, xml_to_tupletree
from tupleparse import parse_cim

"""CIM-XML/HTTP operations.

The WBEMConnection class opens a connection to a remote WBEM server.
Across this you can run various CIM operations.  Each method of this
object corresponds fairly directly to a single CIM method call.
"""

DEFAULT_NAMESPACE = 'root/cimv2'

# TODO: Many methods have more parameters that aren't set yet.

# helper functions for validating arguments

def _check_classname(val):
    if not isinstance(val, StringTypes):
        raise ValueError("string expected for classname, not %s" % `val`)


class CIMError(Exception):
    """Raised when something bad happens.  The associated value is a
    tuple of (error_code, description).  An error code of zero
    indicates an XML parsing error in PyWBEM."""

class WBEMConnection:
    """Class representing a client's connection to a WBEM server.
    
    At the moment there is no persistent TCP connection; the
    connectedness is only conceptual.

    After creating a connection, various methods may be called on the
    object, which causes a remote call to the server.  All these
    operations take regular Python or cim_types values for parameters,
    and return the same.  The caller should not need to know about
    the XML encoding.  (It should be possible to use a different
    transport below this layer without disturbing any clients.)

    The connection remembers the XML for the last request and last
    reply.  This may be useful in debugging: if a problem occurs, you
    can examine the last_request and last_reply fields of the
    connection.  These are the prettified request and response; the
    real request is sent without indents so as not to corrupt whitespace.

    The caller may also register callback functions which are passed
    the request before it is sent, and the reply before it is
    unpacked.
    """
    
    def __init__(self, url, creds, default_namespace = DEFAULT_NAMESPACE,
                 x509 = None):
        self.url = url
        self.creds = creds
        self.x509 = x509
        self.last_request = self.last_reply = ''
        self.default_namespace = default_namespace

    def __repr__(self):
        return "%s(%s, user=%s)" % (self.__class__.__name__, `self.url`,
                               `self.creds[0]`)

    def imethodcall(self, methodname, localnamespacepath, **params):
        """Make an intrinsic method call.

        Returns a tupletree with a IRETURNVALUE element at the root.
        A CIMError exception is thrown if there was an error parsing
        the call response, or an ERROR element was returned.

        The parameters are automatically converted to the right
        CIM_XML objects.

        In general clients should call one of the method-specific
        methods of the connection, such as EnumerateInstanceNames,
        etc."""

        # If a LocalNamespacePath wasn't specified, use the default one

        if localnamespacepath == None:
            localnamespacepath = self.default_namespace

        # Create HTTP headers

        headers = ['CIMOperation: MethodCall',
                   'CIMMethod: %s' % methodname,
                   cim_http.get_object_header(localnamespacepath)]

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
                             for ns in string.split(localnamespacepath, '/')]),
                        plist)),
                1001, '1.0'),
            '2.0', '2.0')

        self.last_raw_request = req_xml.toxml()
        self.last_request = req_xml.toprettyxml(indent='  ')

        # Get XML response

        try:
            resp_xml = cim_http.wbem_request(self.url, req_xml.toxml(),
                                             self.creds, headers,
                                             x509 = self.x509)
        except cim_http.Error, arg:
            # Convert cim_http exceptions to CIMError exceptions
            raise CIMError(0, str(arg))

        ## TODO: Perhaps only compute this if it's required?  Should not be
        ## all that expensive.

        reply_dom = minidom.parseString(resp_xml)

        ## We want to not insert any newline characters, because
        ## they're already present and we don't want them duplicated.
        self.last_reply = reply_dom.toprettyxml(indent='  ', newl='')
        self.last_raw_reply = resp_xml

        # Parse response

        tt = parse_cim(dom_to_tupletree(reply_dom))

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
        """Make an extrinsic method call.

        Returns a tupletree with a RETURNVALUE element at the root.
        A CIMError exception is thrown if there was an error parsing
        the call response, or an ERROR element was returned.

        The parameters are automatically converted to the right
        CIM_XML objects."""

        # Create HTTP headers

        headers = ['CIMOperation: MethodCall',
                   'CIMMethod: %s' % methodname,
                   cim_http.get_object_header(localobject)]
            
        # Create parameter list

        plist = map(lambda x:
                    cim_xml.PARAMVALUE(x[0], cim_obj.tocimxml(x[1])),
                    params.items())

        # Build XML request

        req_xml = cim_xml.CIM(
            cim_xml.MESSAGE(
                cim_xml.SIMPLEREQ(
                    cim_xml.METHODCALL(
                        methodname,
                        localobject.tocimxml(),
                        plist)),
                1001, '1.0'),
            '2.0', '2.0')

        self.last_request = req_xml.toprettyxml(indent='  ')

        # Get XML response

        try:
            resp_xml = cim_http.wbem_request(self.url, req_xml.toxml(),
                                             self.creds, headers)
        except cim_http.Error, arg:
            # Convert cim_http exceptions to CIMError exceptions
            raise CIMError(0, str(arg))

        self.last_reply = resp_xml

        tt = parse_cim(xml_to_tupletree(resp_xml))

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

        # At this point we have a list of elements: either an ERROR,
        # or a RETURNVALUE followed by zero or more PARAMVALUE
        # elements.

        if tt[0][0] == 'ERROR':
            code = int(tt[0][1]['CODE'])
            if tt[0][1].has_key('DESCRIPTION'):
                raise CIMError(code, tt[0][1]['DESCRIPTION'])
            raise CIMError(code, 'Error code %s' % tt[0][1]['CODE'])

        if tt[0][0] != 'RETURNVALUE':
            raise CIMError(0, 'Expecting RETURNVALUE element, got %s'
                           % tt[0][0])

        return tt

    #
    # Instance provider API
    # 

    def EnumerateInstanceNames(self, ClassName, LocalNamespacePath = None,
                               **params):
        """Enumerate instance names of a given classname.  Returns a
        list of cim_obj.InstanceName objects."""
        
        result = self.imethodcall(
            'EnumerateInstanceNames',
            LocalNamespacePath,
            ClassName = CIMClassName(ClassName),
            **params)

        if result is not None:
            return result[2]

        return []

    def EnumerateInstances(self, ClassName, LocalNamespacePath = None,
                           **params):
        """Enumerate instances of a given classname.  Returns a list
        of cim_obj.Instance objects."""

        # NOTE: EnumerateInstances actually returns the instance names
        # as well as the instance objects.  In this interface we
        # discard the names which may not necessarily be such a clever
        # thing to do.

        result = self.imethodcall(
            'EnumerateInstances',
            LocalNamespacePath,
            ClassName = CIMClassName(ClassName),
            **params)

        if result is None:
            return []

        instances = result[2]
        ret = []

        for i in instances:
            if i[0] != 'VALUE.NAMEDINSTANCE':
                raise CIMError(0, 'Expecting VALUE.NAMEDINSTANCE element, '
                               'got %s' % i[0])
            ret.append(i[2][1])

        return ret

    def GetInstance(self, instancename, LocalNamespacePath = None, **params):
        """Fetch an instance given by instancename.  Returns a
        cim_obj.Instance object."""
        
        result = self.imethodcall(
            'GetInstance',
            LocalNamespacePath,
            InstanceName = instancename,
            **params)

        return result[2][0]

    def DeleteInstance(self, instancename, LocalNamespacePath = None,
                       **params):
        """Delete the instance given by instancename."""

        self.imethodcall(
            'DeleteInstance',
            LocalNamespacePath,
            InstanceName = instancename,
            **params)

    def CreateInstance(self, instance, LocalNamespacePath = None, **params):
        """Create an instance.  Returns the name for the instance."""

        # TODO: Untested

        result = self.imethodcall(
            'CreateInstance',
            LocalNamespacePath,
            NewInstance = instance,
            **params)

        return result[2][0]

    def ModifyInstance(self, instancename, instance, LocalNamespacePath = None,
                       **params):
        """Modify properties of a named instance."""
        
        wrapped_instance = CIMNamedInstance(instancename, instance)
        
        return self.imethodcall(
            'ModifyInstance',
            LocalNamespacePath,
            ModifiedInstance = wrapped_instance,
            **params)
        
    #
    # Schema management API
    #

    def EnumerateClassNames(self, LocalNamespacePath = None, **params):
        """Return a list of CIM class names. Names are returned as strings."""
        
        result = self.imethodcall(
            'EnumerateClassNames',
            LocalNamespacePath,
            **params)

        return result and map(lambda x: x.classname, result[2])
    
    
    def EnumerateClasses(self, LocalNamespacePath = None, **params):
        """Return a list of CIM class objects."""

        result = self.imethodcall(
            'EnumerateClasses',
            LocalNamespacePath,
            **params)

        if result is None:
            return []
        
        return result[2]

    def GetClass(self, ClassName, LocalNamespacePath = None, **params):
        """Return a CIMClass representing the named class."""

        result = self.imethodcall(
            'GetClass',
            LocalNamespacePath,
            ClassName = CIMClassName(ClassName),
            **params)

        return result[2][0]

    #
    # Association provider API
    # 

    def _add_objectname_param(self, params, object):
        """Add an object name (either a class name or an instance
        name) to a dictionary of parameter names."""

        if isinstance(object, (CIMClassName, CIMInstanceName)):
            params['ObjectName'] = object
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
            params['ResultClass'] = cim_obj.CIMClassName(params['ResultClass'])

        if params.has_key('AssocClass') and \
           isinstance(params['AssocClass'], StringTypes):
            params['AssocClass'] = cim_obj.CIMClassName(params['AssocClass'])

        return params

    def Associators(self, object, LocalNamespacePath = None, **params):
        """Enumerate CIM classes or instances that are associated to a
        particular source CIM Object.  Pass a keyword parameter of
        'ClassName' to return associators for a CIM class, pass
        'InstanceName' to return the associators for a CIM instance."""

        params = self._map_association_params(params)
        params = self._add_objectname_param(params, object)
        
        result = self.imethodcall(
            'Associators',
            LocalNamespacePath,
            **params)

        if result is None:
            return []

        return map(lambda x: x[2], result[2])

    def AssociatorNames(self, object, LocalNamespacePath = None, **params):
        """Enumerate the names of CIM classes or instances that are
        associated to a particular source CIM Object.  Pass a keyword
        parameter of 'ClassName' to return associators for a CIM
        class, pass 'InstanceName' to return the associators for a CIM
        instance.  Returns a list of CIMInstancePath objects (i.e a
        CIMInstanceName plus a namespacepath)."""

        params = self._map_association_params(params)
        params = self._add_objectname_param(params, object)

        result = self.imethodcall(
            'AssociatorNames',
            LocalNamespacePath,
            **params)

        if result is None:
            return []

        return map(lambda x: x[2], result[2])

    def References(self, object, LocalNamespacePath = None, **params):
        """Enumerate the association objects that refer to a
        particular target CIM class or instance.  Pass a keyword
        parameter of 'ClassName' to return associators for a CIM
        class, pass 'InstanceName' to return the associators for a CIM
        instance."""

        params = self._map_association_params(params)
        params = self._add_objectname_param(params, object)

        result = self.imethodcall(
            'References',
            LocalNamespacePath,
            **params)

        if result is None:
            return []

        return map(lambda x: x[2], result[2])

    def ReferenceNames(self, object, LocalNamespacePath = None, **params):
        """Enumerate the name of association objects that refer to a
        particular target CIM class or instance.  Pass a keyword
        parameter of 'ClassName' to return associators for a CIM
        class, pass 'InstanceName' to return the associators for a CIM
        instance."""

        params = self._map_association_params(params)
        params = self._add_objectname_param(params, object)

        result = self.imethodcall(
            'ReferenceNames',
            LocalNamespacePath,
            **params)

        if result is None:
            return []

        return map(lambda x: x[2], result[2])

    #
    # Method provider API
    #

    def InvokeMethod(self, methodname, localobject, **params):

        # A CIMInstanceName is the obvious object to pass when making a
        # "dynamic" method call but the schema requies a
        # CIMLocalObject.  Do a conversion if necessary.

        if isinstance(localobject, CIMInstanceName):
            localobject = CIMLocalInstancePath(
                self.default_namespace, localobject)

        result = self.methodcall(methodname, localobject, **params)

        # Convert the RETURNVALUE into a Python object

        returnvalue = cim_obj.tocimobj(result[0][1]['PARAMTYPE'],
                                       result[0][2])

        # Convert output parameters into a dictionary of Python
        # objects.

        output_params = {}

        for p in result[1:]:
             output_params[p[0]] = cim_obj.tocimobj(p[1], p[2])

        return returnvalue, output_params
