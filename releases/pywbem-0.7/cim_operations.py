#
# (C) Copyright 2003-2007 Hewlett-Packard Development Company, L.P.
# (C) Copyright 2006-2007 Novell, Inc. 
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as
# published by the Free Software Foundation; either version 2 of the
# License.
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
#         Martin Pool <mbp@hp.com>
#         Bart Whiteley <bwhiteley@suse.de>

# This is meant to be safe for import *; ie the only global names
# should be ones that all clients can see.

import sys, string
from types import StringTypes
from xml.dom import minidom
import cim_obj, cim_xml, cim_http, cim_types
from cim_obj import CIMClassName, CIMInstanceName, CIMInstance, CIMClass
from datetime import datetime, timedelta
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

class WBEMConnection(object):
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

    verify_callback is used to verify the server certificate.  
    It is passed to OpenSSL.SSL.set_verify, and is called during the SSL
    handshake.  verify_callback should take five arguments: A Connection 
    object, an X509 object, and three integer variables, which are in turn 
    potential error number, error depth and return code. verify_callback 
    should return True if verification passes and False otherwise.

    The value of the x509 argument is used only when the url contains
    'https'. x509 must be a dictionary containing the keys 'cert_file' 
    and 'key_file'. The value of 'cert_file' must consist of the
    filename of an certificate and the value of 'key_file' must consist 
    of a filename containing the private key belonging to the public key 
    that is part of the certificate in cert_file. 
    """
    
    def __init__(self, url, creds = None, default_namespace = DEFAULT_NAMESPACE,
                 x509 = None, verify_callback = None):
        self.url = url
        self.creds = creds
        self.x509 = x509
        self.verify_callback = verify_callback
        self.last_request = self.last_reply = ''
        self.default_namespace = default_namespace
        self.debug = False

    def __repr__(self):
        if self.creds is None:
            user = 'anonymous'
        else:
            user = 'user=%s' % `self.creds[0]`
        return "%s(%s, %s, namespace=%s)" % (self.__class__.__name__, `self.url`,
                                             user, `self.default_namespace`)

    def imethodcall(self, methodname, namespace, **params):
        """Make an intrinsic method call.

        Returns a tupletree with a IRETURNVALUE element at the root.
        A CIMError exception is thrown if there was an error parsing
        the call response, or an ERROR element was returned.

        The parameters are automatically converted to the right
        CIM_XML objects.

        In general clients should call one of the method-specific
        methods of the connection, such as EnumerateInstanceNames,
        etc."""

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

            self.last_reply = None
            self.last_raw_reply = None
        
        # Get XML response

        try:
            resp_xml = cim_http.wbem_request(self.url, req_xml.toxml(),
                                             self.creds, headers,
                                             x509 = self.x509,
                                             verify_callback = self.verify_callback)
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
            if isinstance(obj,list) and obj:
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

        # Get XML response

        try:
            resp_xml = cim_http.wbem_request(self.url, req_xml.toxml(),
                                             self.creds, headers,
                                             x509 = self.x509,
                                             verify_callback = self.verify_callback)
        except cim_http.Error, arg:
            # Convert cim_http exceptions to CIMError exceptions
            raise CIMError(0, str(arg))

        if self.debug:
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

    def EnumerateInstanceNames(self, ClassName, namespace = None, **params):
        """Enumerate instance names of a given classname.  Returns a
        list of CIMInstanceName objects."""
        
        if namespace is None:
            namespace = self.default_namespace

        result = self.imethodcall(
            'EnumerateInstanceNames',
            namespace,
            ClassName = CIMClassName(ClassName),
            **params)

        names = []

        if result is not None:
            names = result[2]

        [setattr(n, 'namespace', namespace) for n in names]

        return names

    def EnumerateInstances(self, ClassName, namespace = None, **params):
        """Enumerate instances of a given classname.  Returns a list
        of CIMInstance objects with paths."""

        if namespace is None:
            namespace = self.default_namespace

        result = self.imethodcall(
            'EnumerateInstances',
            namespace,
            ClassName = CIMClassName(ClassName),
            **params)

        instances = []

        if result is not None:
            instances = result[2]

        [setattr(i.path, 'namespace', namespace) for i in instances]

        return instances

    def GetInstance(self, InstanceName, **params):
        """Fetch an instance given by instancename.  Returns a
        CIMInstance object."""

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
            InstanceName = iname,
            **params)

        instance = result[2][0]
        instance.path = InstanceName
        instance.path.namespace = namespace

        return instance

    def DeleteInstance(self, InstanceName, **params):
        """Delete the instance given by instancename."""

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
            InstanceName = iname,
            **params)

    def CreateInstance(self, NewInstance, **params):
        """Create an instance.  Returns the name for the instance."""

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
            NewInstance = instance,
            **params)

        name = result[2][0]
        name.namespace = namespace

        return name

    def ModifyInstance(self, ModifiedInstance, **params):
        """Modify properties of a named instance."""

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
            ModifiedInstance = instance,
            **params)

    def ExecQuery(self, QueryLanguage, Query, namespace = None):
        if namespace is None:
            namespace = self.default_namespace
        result = self.imethodcall(
            'ExecQuery',
            namespace, 
            QueryLanguage = QueryLanguage,
            Query = Query)

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
            params['ClassName'] = cim_obj.CIMClassName(params['ClassName'])

        return params

    def EnumerateClassNames(self, namespace = None, **params):
        """Return a list of CIM class names. Names are returned as strings."""
        
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
        
    def EnumerateClasses(self, namespace = None, **params):
        """Return a list of CIM class objects."""

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

    def GetClass(self, ClassName, namespace = None, **params):
        """Return a CIMClass representing the named class."""

        params = self._map_classname_param(params)

        if namespace is None:
            namespace = self.default_namespace

        result = self.imethodcall(
            'GetClass',
            namespace,
            ClassName = CIMClassName(ClassName),
            **params)

        return result[2][0]

    def DeleteClass(self, ClassName, namespace = None, **params):
        """Delete a class by class name."""

        # UNSUPPORTED (but actually works)

        params = self._map_classname_param(params)

        if namespace is None:
            namespace = self.default_namespace

        self.imethodcall(
            'DeleteClass',
            namespace,
            ClassName = CIMClassName(ClassName),
            **params)            

    def ModifyClass(self, ModifiedClass, namespace = None, **params):
        """Modify a CIM class."""

        # UNSUPPORTED

        if namespace is None:
            namespace = self.default_namespace

        self.imethodcall(
            'ModifyClass',
            namespace,
            ModifiedClass = ModifiedClass,
            **params)

    def CreateClass(self, NewClass, namespace = None, **params):
        """Create a CIM class."""

        # UNSUPPORTED

        if namespace is None:
            namespace = self.default_namespace

        self.imethodcall(
            'CreateClass',
            namespace,
            NewClass = NewClass,
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
            params['ResultClass'] = cim_obj.CIMClassName(params['ResultClass'])

        if params.has_key('AssocClass') and \
           isinstance(params['AssocClass'], StringTypes):
            params['AssocClass'] = cim_obj.CIMClassName(params['AssocClass'])

        return params

    def Associators(self, ObjectName, **params):
        """Enumerate CIM classes or instances that are associated to a
        particular source CIM Object.  Pass a keyword parameter of
        'ClassName' to return associators for a CIM class, pass
        'InstanceName' to return the associators for a CIM instance."""

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
        """Enumerate the names of CIM classes or instances names that are
        associated to a particular source CIM Object.  Pass a keyword
        parameter of 'ClassName' to return associator names for a CIM
        class, pass 'InstanceName' to return the associator names for a CIM
        instance.  Returns a list of CIMInstanceName objects with the
        host and namespace attributes set."""

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
        """Enumerate the association objects that refer to a
        particular target CIM class or instance.  Pass a keyword
        parameter of 'ClassName' to return associators for a CIM
        class, pass 'InstanceName' to return the associators for a CIM
        instance."""

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
        """Enumerate the name of association objects that refer to a
        particular target CIM class or instance.  Pass a keyword
        parameter of 'ClassName' to return associators for a CIM
        class, pass 'InstanceName' to return the associators for a CIM
        instance."""

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

        # Convert string to CIMClassName

        obj = ObjectName

        if isinstance(obj, StringTypes):
            obj = CIMClassName(obj, namespace = self.default_namespace)

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

        output_params = {}

        for p in result:
            if p[1] == 'reference':
                output_params[p[0]] = p[2]
            else:
                output_params[p[0]] = cim_obj.tocimobj(p[1], p[2])

        return returnvalue, output_params

    #
    # Qualifiers API
    #

    def EnumerateQualifiers(self, namespace = None, **params):
        """Enumerate qualifier declarations.  Returns a list of
        CIMQualifier objects."""

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

    def GetQualifier(self, QualifierName, namespace = None, **params):
        """Retrieve a qualifier by name.  Returns a CIMQualifier
        object."""

        if namespace is None:
            namespace = self.default_namespace

        result = self.imethodcall(
            'GetQualifier',
            namespace,
            QualifierName = QualifierName,
            **params)

        if result is not None:
            names = result[2][0]

        return names

    def SetQualifier(self, QualifierDeclaration, namespace = None,
                     **params):
        """Set a qualifier."""

        if namespace is None:
            namespace = self.default_namespace

        result = self.imethodcall(
            'SetQualifier',
            namespace,
            QualifierDeclaration = QualifierDeclaration,
            **params)

    def DeleteQualifier(self, QualifierName, namespace = None,
                        **params):
        """Delete a qualifier by name."""

        if namespace is None:
            namespace = self.default_namespace

        result = self.imethodcall(
            'DeleteQualifier',
            namespace,
            QualifierName = QualifierName,
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

def PegasusUDSConnection(creds = None, **kwargs):
    return WBEMConnection('/var/run/tog-pegasus/cimxml.socket', creds, **kwargs)

def SFCBUDSConnection(creds = None, **kwargs):
    return WBEMConnection('/tmp/sfcbHttpSocket', creds, **kwargs)

def OpenWBEMUDSConnection(creds = None, **kwargs):
    return WBEMConnection('/tmp/OW@LCL@APIIPC_72859_Xq47Bf_P9r761-5_J-7_Q', 
                          creds, **kwargs)
