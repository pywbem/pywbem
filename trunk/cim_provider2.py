#
# (C) Copyright 2003-2007 Hewlett-Packard Development Company, L.P.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as
# published by the Free Software Foundation; version 2 of the License.
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

# Author: Bart Whiteley
#         Jon Carey
####

"""Python CIM Providers (aka "nirvana")

This module is an abstraction and utility layer between a CIMOM and 
Python providers.  The CIMOM uses this module to load Python providers, 
and route requests to those providers.  

Python Provider Modules

    Python Providers are implemented as Python modules.  By convention
    these modules are installed into /usr/lib/pycim.  However, they can 
    be anywhere.  These modules are loaded on demand using load_module() 
    from the imp module.  The CIMOM's pycim interface stores the timestamp 
    of the provider modules.  If the modules change, the CIMOM reloads the 
    modules.  This is very useful while developing providers, since the 
    latest code will always be loaded and used. 

    A Python Provider Module will contain functions, attributes, and 
    instances that will be accessed and manipulated by this module.  

    Providers are often classified in the following catagories:
        Instance -- Instrument the retrieval, creation, modification, 
            and deletion of CIM instances. 
        Association -- Instrument CIM associations (CIM classes with the
            Association qualifier). 
        Method -- Instrument methods as defined on CIM instances or CIM
            classes. 
        Indication -- Generates indications based on indication 
            subscriptions. 
        Indication Consumer -- "Consumes" (or "Handles") an indication, 
            possibly delivering it through some other means, such as email. 
        Polled -- A polled provider is allowed to run periodically (by 
            calling its poll function).  This allows a provider to do some
            periodic work, without the need to create its own thread.  

    An Instance, Association, and/or Method provider is created by defining
    one or more subclasses of CIMProvider2 within the provider module, and
    registering instances of the subclass(es) with CIM class names by way 
    of the get_providers function (described below).  Refer to 
    the documentation for CIMProvider2 in this module. 

    Indication, Indication Consumer, and Polled providers are defined by 
    implementing some functions within the provider module. 

    Provider module functions: 
        init(env):
            This module function is optional.  It is called immediately 
            after the provider module is imported.  

            Arguments:
            env -- Provider Environment (pycimmb.ProviderEnvironment)

        get_providers(env):
            Return a dict that maps CIM class names to instances of 
            CIMProvider2 subclasses.  Note that multiple classes can be 
            instrumented by the same instance of a CIMProvider2 subclass.  
            The CIM class names are case-insensitive, since this dict is
            converted to a NocaseDict. 

            Arguments:
            env -- Provider Environment (pycimmb.ProviderEnvironment)
           
            For example, a Python Provider Module may contain the following:

                class Py_FooBarProvider(CIMProvider2):
                    ...

                def get_providers(env):
                    _fbp = Py_FooBarProvider()
                    return {'Py_Foo':_fbp, 'Py_Bar':_fbp}

        can_unload(env):
            Return True if the provider can be unloaded.

            The CIMOM may try to unload a provider after a period of inactivity.
            Before unloading a provider, the CIMOM asks the provider if it can 
            be unloaded.  

            Arguments:
            env -- Provider Environment (pycimmb.ProviderEnvironment)

        shutdown(env):
            Perform any cleanup tasks prior to being unloaded.

            The provider will shortly be unloaded, and is given an opportunity
            to perform any needed cleanup.  The provider may be unloaded after
            a period of inactivity (see the documentation for can_unload), or
            because the CIMOM is shutting down. 

            Arguments:
            env -- Provider Environment (pycimmb.ProviderEnvironment)

        handle_indication(env, ns, handler_instance, indication_instance):
            Process an indication.

            Arguments:
            env -- Provider Environment (pycimmb.ProviderEnvironment)
            ns -- The namespace where the event occurred
            handler_instance -- 
            indication_instance -- The indication

        authorize_filter (env, filter, ns, classes, 
                         owner):
            Allow or disallow an indication subscription request.
            
            Arguments:
            env -- Provider Environment (pycimmb.ProviderEnvironment)
            filter -- The WQL select statement
            namespace -- The namepace where the indication is registered for 
            classes -- The classpath of the indication registered for
            owner -- The name of the principal (cimom user)

        activate_filter (env, filter, ns, classes, 
                         first_activation):
            Activate an indication subscription.
            
            Arguments:
            env -- Provider Environment (pycimmb.ProviderEnvironment)
            filter -- The WQL select statement
            namespace -- The namepace where the indication is registered for 
            classes -- The classpath of the indication registered for
            first_activation -- boolean - whether first activation

        deactivate_filter(env, filter, ns, classes, 
                          last_activation):
            Deactivate an indication subscription.
            
            Arguments:
            env -- Provider Environment (pycimmb.ProviderEnvironment)
            filter -- The WQL select statement
            ns -- The namepace where the indication is registered for  
            classes -- The classpath of the indication registered for
            last_activation -- boolean - whether last activation

        enable_indications(env):
            Enable indications.
            
            Arguments:
            env -- Provider Environment (pycimmb.ProviderEnvironment)

        disable_indications(env):
            Disable indications.
            
            Arguments:
            env -- Provider Environment (pycimmb.ProviderEnvironment)

Provider Environment
    
    A pycimmb.ProviderEnvironment is passed to many functions.  This is 
    a handle back into the CIMOM.  You can use it for logging and for
    making "up-calls" to the CIMOM.  For example: 
        
        logger = env.get_logger()
        logger.log_debug('Debug Info')

        ch = env.get_cimom_handle()
        other_inst = ch.GetInstance(inst_path, LocalOnly=False,
                                    IncludeQualifiers=False,
                                    IncludeClassOrigin=False)

    The API of the pycimmb.CIMOMHandle resembles that of 
    pywbem.WBEMConnection.  

    For more information on the ProviderEnvironments, and other features
    provided by pycimmb, refer to the pycimmb documentation. 

CodeGen

    The codegen function can be used to generate provider stub code for a 
    given CIM class.  This is a quick way to get started writing a provider. 

"""

import sys 
from os.path import dirname
import pywbem
import types

import sys # for sys.modules
import os
import imp
import threading

g_mod_lock = threading.RLock()



__all__ = ['CIMProvider2', 'codegen']


def _paths_equal(lhs, rhs):
    """If one object path doesn't inlcude a host, don't include the hosts
    in the comparison

    """

    if lhs is rhs:
        return True
    if lhs.host is not None and rhs.host is not None and lhs.host != rhs.host:
        return False
    # need to make sure this stays in sync with CIMInstanceName.__cmp__()
    return not (pywbem.cmpname(rhs.classname, lhs.classname) or
                cmp(rhs.keybindings, lhs.keybindings) or
                pywbem.cmpname(rhs.namespace, lhs.namespace))


class CIMProvider2(object):
    """Base class for CIM Providers.  

    A derived class might normally override the following: 
    - enum_instances
    - get_instance
    - set_instance
    - delete_instance
    - references

    If the provider is a "read-only" instance provider, set_instance and 
    delete_instance need not be overridden. 

    Only association providers need to override references. 

    A method provider should implement a method of the form:
        def cim_method_<method_name>(self, env, object_name, method,
                                     param_<input_param_1>,
                                     param_<input_param_2>,
                                     ...):
        Where <method_name> is the name of the method from the CIM schema.  
        <method_name> needs to be all lowercase, regardless of the case of 
        the method name in the CIM schema (CIM method names are case 
        insensitive). 

        Keyword arguments:
        env -- Provider Environment (pycimmb.ProviderEnvironment)
        object_name -- A pywbem.CIMInstanceName or pywbem.CIMClassname 
            specifying the object on which the method is to be invoked. 
        method -- A pywbem.CIMMethod, representing the method to execute. 
        param_<param_name> -- Corresponds to the input parameter <param_name> 
            from the CIM schema.  <param_name> needs to be all lowercase, 
            regardless of the case of the parameter name in the CIM schema
            (CIM parameter names are case insensitive). 

        The method returns a two-tuple containing the return value of the 
        method, and a dictionary containing the output parameters. 

    Example:
        def cim_method_requeststatechange(self, env, object_name, method,
                                          param_requestedstate,
                                          param_timeoutperiod):
            # do stuff. 
            out_params = {'job': pywbem.CIMInstanceName(...)}
            rval = pywbem.Uint32(0)
            return (rval, out_params)

    The methods prefixed with "MI_" correspond to the WBEM operations 
    from http://www.dmtf.org/standards/published_documents/DSP200.html
    The default implementations of these methods call the methods 
    described above.  These will not normally be overridden or extended 
    by a subclass. 

    """

    def get_instance (self, env, model):
        """Return an instance.

        Keyword arguments:
        env -- Provider Environment (pycimmb.ProviderEnvironment)
        model -- A template of the pywbem.CIMInstance to be returned.  The 
            key properties are set on this instance to correspond to the 
            instanceName that was requested.  The properties of the model
            are already filtered according to the PropertyList from the 
            request.  Only properties present in the model need to be
            given values.  If you prefer, you can set all of the 
            values, and the instance will be filtered for you. 

        Possible Errors:
        CIM_ERR_ACCESS_DENIED
        CIM_ERR_INVALID_PARAMETER (including missing, duplicate, unrecognized 
            or otherwise incorrect parameters)
        CIM_ERR_NOT_FOUND (the CIM Class does exist, but the requested CIM 
            Instance does not exist in the specified namespace)
        CIM_ERR_FAILED (some other unspecified error occurred)

        """
        return None

    def enum_instances(self, env, model, keys_only):
        """Enumerate instances.

        The WBEM operations EnumerateInstances and EnumerateInstanceNames
        are both mapped to this method. 
        This method is a python generator

        Keyword arguments:
        env -- Provider Environment (pycimmb.ProviderEnvironment)
        model -- A template of the pywbem.CIMInstances to be generated.  
            The properties of the model are already filtered according to 
            the PropertyList from the request.  Only properties present in 
            the model need to be given values.  If you prefer, you can 
            always set all of the values, and the instance will be filtered 
            for you. 
        keys_only -- A boolean.  True if only the key properties should be
            set on the generated instances.

        Possible Errors:
        CIM_ERR_FAILED (some other unspecified error occurred)

        """
        pass

    def set_instance(self, env, instance, modify_existing):
        """Return a newly created or modified instance.

        Keyword arguments:
        env -- Provider Environment (pycimmb.ProviderEnvironment)
        instance -- The new pywbem.CIMInstance.  If modifying an existing 
            instance, the properties on this instance have been filtered by 
            the PropertyList from the request.
        modify_existing -- True if ModifyInstance, False if CreateInstance

        Return the new instance.  The keys must be set on the new instance. 

        Possible Errors:
        CIM_ERR_ACCESS_DENIED
        CIM_ERR_NOT_SUPPORTED
        CIM_ERR_INVALID_PARAMETER (including missing, duplicate, unrecognized 
            or otherwise incorrect parameters)
        CIM_ERR_ALREADY_EXISTS (the CIM Instance already exists -- only 
            valid if modify_existing is False, indicating that the operation
            was CreateInstance)
        CIM_ERR_NOT_FOUND (the CIM Instance does not exist -- only valid 
            if modify_existing is True, indicating that the operation
            was ModifyInstance)
        CIM_ERR_FAILED (some other unspecified error occurred)

        """
        raise pywbem.CIMError(pywbem.CIM_ERR_NOT_SUPPORTED, "")

    def delete_instance(self, env, instance_name):
        """Delete an instance.

        Keyword arguments:
        env -- Provider Environment (pycimmb.ProviderEnvironment)
        instance_name -- A pywbem.CIMInstanceName specifying the instance 
            to delete.

        Possible Errors:
        CIM_ERR_ACCESS_DENIED
        CIM_ERR_NOT_SUPPORTED
        CIM_ERR_INVALID_NAMESPACE
        CIM_ERR_INVALID_PARAMETER (including missing, duplicate, unrecognized 
            or otherwise incorrect parameters)
        CIM_ERR_INVALID_CLASS (the CIM Class does not exist in the specified 
            namespace)
        CIM_ERR_NOT_FOUND (the CIM Class does exist, but the requested CIM 
            Instance does not exist in the specified namespace)
        CIM_ERR_FAILED (some other unspecified error occurred)

        """ 
        raise pywbem.CIMError(pywbem.CIM_ERR_NOT_SUPPORTED, "")

    def references(self, env, object_name, model, 
                   result_class_name, role, result_role, keys_only):
        """Instrument Associations.

        All four association-related operations (Associators, AssociatorNames, 
        References, ReferenceNames) are mapped to this method. 
        This method is a python generator

        Keyword arguments:
        env -- Provider Environment (pycimmb.ProviderEnvironment)
        object_name -- A pywbem.CIMInstanceName that defines the source 
            CIM Object whose associated Objects are to be returned.
        model -- A template pywbem.CIMInstance to serve as a model
            of the objects to be returned.  Only properties present on this
            model need to be set. 
        result_class_name -- If not empty, this string acts as a filter on 
            the returned set of Instances by mandating that each returned 
            Instances MUST represent an association between object_name 
            and an Instance of a Class whose name matches this parameter
            or a subclass. 
        role -- If not empty, MUST be a valid Property name. It acts as a 
            filter on the returned set of Instances by mandating that each 
            returned Instance MUST refer to object_name via a Property 
            whose name matches the value of this parameter.
        result_role -- If not empty, MUST be a valid Property name. It acts 
            as a filter on the returned set of Instances by mandating that 
            each returned Instance MUST represent associations of 
            object_name to other Instances, where the other Instances play 
            the specified result_role in the association (i.e. the 
            name of the Property in the Association Class that refers to 
            the Object related to object_name MUST match the value of this 
            parameter).
        keys_only -- A boolean.  True if only the key properties should be
            set on the generated instances.

        The following diagram may be helpful in understanding the role, 
        result_role, and result_class_name parameters.
        +------------------------+                    +-------------------+
        | object_name.classname  |                    | result_class_name |
        | ~~~~~~~~~~~~~~~~~~~~~  |                    | ~~~~~~~~~~~~~~~~~ |
        +------------------------+                    +-------------------+
           |              +-----------------------------------+      |
           |              |  [Association] model.classname    |      |
           | object_name  |  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~    |      |
           +--------------+ object_name.classname REF role    |      |
        (CIMInstanceName) | result_class_name REF result_role +------+
                          |                                   |(CIMInstanceName)
                          +-----------------------------------+

        Possible Errors:
        CIM_ERR_ACCESS_DENIED
        CIM_ERR_NOT_SUPPORTED
        CIM_ERR_INVALID_NAMESPACE
        CIM_ERR_INVALID_PARAMETER (including missing, duplicate, unrecognized 
            or otherwise incorrect parameters)
        CIM_ERR_FAILED (some other unspecified error occurred)

        """
        # Don't change this return value.  If affects the behavior 
        # of the MI_* methods. 
        return None

    def simple_refs(self, env, object_name, model, 
                   result_class_name, role, result_role, keys_only):

        gen = self.enum_instances(env, model, keys_only)
        for inst in gen:
            for prop in inst.properties.values():
                if prop.type != 'reference':
                    continue
                if role and prop.name.lower() != role:
                    continue
                if self.paths_equal(object_name, prop.value):
                    yield inst
            
        
    def paths_equal(self, lhs, rhs):
        """If one object path doesn't inlcude a host, don't include the hosts
        in the comparison

        """

        if lhs is rhs:
            return True
        if lhs.host is not None and rhs.host is not None and lhs.host != rhs.host:
            return False
        # need to make sure this stays in sync with CIMInstanceName.__cmp__()
        return not (pywbem.cmpname(rhs.classname, lhs.classname) or
                    cmp(rhs.keybindings, lhs.keybindings) or
                    pywbem.cmpname(rhs.namespace, lhs.namespace))


    def MI_enumInstanceNames(self, 
                             env, 
                             objPath):
        """Return instance names of a given CIM class

        Implements the WBEM operation EnumerateInstanceNames in terms 
        of the enum_instances method.  A derived class will not normally
        override this method.

        """

        logger = env.get_logger()
        logger.log_debug('CIMProvider2 MI_enumInstanceNames called...')
        model = pywbem.CIMInstance(classname=objPath.classname, 
                                   path=objPath)
        gen = self.enum_instances(env=env,
                                       model=model,
                                       keys_only=True)
        try:
            iter(gen)
        except TypeError:
            logger.log_debug('CIMProvider2 MI_enumInstanceNames returning')
            return

        for inst in gen:
            yield inst.path
        logger.log_debug('CIMProvider2 MI_enumInstanceNames returning')
    
    def MI_enumInstances(self, 
                         env, 
                         objPath,
                         propertyList):
        """Return instances of a given CIM class

        Implements the WBEM operation EnumerateInstances in terms 
        of the enum_instances method.  A derived class will not normally
        override this method. 

        """
        logger = env.get_logger()
        logger.log_debug('CIMProvider2 MI_enumInstances called...')

        model = pywbem.CIMInstance(classname=objPath.classname,
                                   path=objPath)
        gen = self.enum_instances(env=env,
                                       model=model,
                                       keys_only=False)
        try:
            iter(gen)
        except TypeError:
            logger.log_debug('CIMProvider2 MI_enumInstances returning')
            return
        return gen

    def MI_getInstance(self, 
                       env, 
                       instanceName, 
                       propertyList):
        """Return a specific CIM instance

        Implements the WBEM operation GetInstance in terms 
        of the get_instance method.  A derived class will not normally
        override this method.

        """

        logger = env.get_logger()
        logger.log_debug('CIMProvider2 MI_getInstance called...')
        plist = None
        if propertyList is not None:
            plist = [s.lower() for s in propertyList]
            plist+= [s.lower() for s in instanceName.keybindings.keys()]
        model = pywbem.CIMInstance(classname=instanceName.classname, 
                                   path=instanceName, property_list=plist)
        model.update(model.path.keybindings)

        rval = self.get_instance(env=env, model=model)
        logger.log_debug('CIMProvider2 MI_getInstance returning')
        if rval is None:
            raise pywbem.CIMError(pywbem.CIM_ERR_NOT_FOUND, "")
        return rval

    def MI_createInstance(self, 
                          env, 
                          instance):
        """Create a CIM instance, and return its instance name

        Implements the WBEM operation CreateInstance in terms 
        of the set_instance method.  A derived class will not normally
        override this method.

        """

        logger = env.get_logger()
        logger.log_debug('CIMProvider2 MI_createInstance called...')
        rval = None
        '''
        ch = env.get_cimom_handle()
        cimClass = ch.GetClass(instance.classname, 
                                 instance.path.namespace, 
                                 LocalOnly=False, 
                                 IncludeQualifiers=True)
                                 '''
        # CIMOM has already filled in default property values for 
        # props with default values, if values not supplied by client. 
        rval = self.set_instance(env=env,
                              instance=instance,
                              modify_existing=False)
        logger.log_debug('CIMProvider2 MI_createInstance returning')
        return rval.path

    def MI_modifyInstance(self, 
                          env, 
                          modifiedInstance, 
                          propertyList):
        """Modify a CIM instance

        Implements the WBEM operation ModifyInstance in terms 
        of the set_instance method.  A derived class will not normally
        override this method.

        """

        logger = env.get_logger()
        logger.log_debug('CIMProvider2 MI_modifyInstance called...')
        plist = None
        if propertyList is not None:
            plist = [s.lower() for s in propertyList]
            plist+= [s.lower() for s in modifiedInstance.path.keybindings.keys()]
            self.filter_instance(modifiedInstance, plist)
            modifiedInstance.property_list = plist
            modifiedInstance.update(modifiedInstance.path)
        self.set_instance(env=env,
                              instance=modifiedInstance,
                              modify_existing=True)
        logger.log_debug('CIMProvider2 MI_modifyInstance returning')
    
    def MI_deleteInstance(self, 
                          env, 
                          instanceName):
        """Delete a CIM instance

        Implements the WBEM operation DeleteInstance in terms 
        of the delete_instance method.  A derived class will not normally
        override this method.

        """

        logger = env.get_logger()
        logger.log_debug('CIMProvider2 MI_deleteInstance called...')
        self.delete_instance(env=env, instance_name=instanceName)
        logger.log_debug('CIMProvider2 MI_deleteInstance returning')


    def MI_associators(self, 
                       env, 
                       objectName, 
                       assocClassName, 
                       resultClassName, 
                       role, 
                       resultRole, 
                       propertyList):
        """Return instances associated to a given object.

        Implements the WBEM operation Associators in terms 
        of the references method.  A derived class will not normally
        override this method.

        """

        # NOTE: This should honor the parameters resultClassName, role, resultRole, 
        #       and propertyList
        logger = env.get_logger()
        logger.log_debug('CIMProvider2 MI_associators called. assocClass: %s' % (assocClassName))
        if not assocClassName:
            raise pywbem.CIMError(pywbem.CIM_ERR_FAILED, 
                    "Empty assocClassName passed to Associators")
        ch = env.get_cimom_handle()
        model = pywbem.CIMInstance(classname=assocClassName)
        model.path = pywbem.CIMInstanceName(classname=assocClassName, 
                                            namespace=objectName.namespace)
        gen = self.references(env=env, 
                                    object_name=objectName, 
                                    model=model,
                                    result_class_name=resultClassName, 
                                    role=role, 
                                    result_role=None,
                                    keys_only=False)
        if gen is None:
            logger.log_debug('references() returned None instead of generator object')
            return
        for inst in gen:
            for prop in inst.properties.values():
                lpname = prop.name.lower()
                if prop.type != 'reference':
                    continue
                if role and role.lower() == lpname:
                    continue
                if resultRole and resultRole.lower() != lpname:
                    continue
                if self.paths_equal(prop.value, objectName):
                    continue
                if resultClassName and \
                        resultClassName.lower() != prop.value.classname.lower():
                    continue
                try:
                    if prop.value.namespace is None:
                        prop.value.namespace = objectName.namespace
                    inst = ch.GetInstance(prop.value, propertyList)
                except pywbem.CIMError, (num, msg):
                    if num == pywbem.CIM_ERR_NOT_FOUND:
                        continue
                    else:
                        raise
                if inst.path is None:
                    inst.path = prop.value
                yield inst
        logger.log_debug('CIMProvider2 MI_associators returning')

    def MI_associatorNames(self, 
                           env, 
                           objectName, 
                           assocClassName, 
                           resultClassName, 
                           role, 
                           resultRole):
        """Return instances names associated to a given object.

        Implements the WBEM operation AssociatorNames in terms 
        of the references method.  A derived class will not normally
        override this method.

        """

        logger = env.get_logger()
        logger.log_debug('CIMProvider2 MI_associatorNames called. assocClass: %s' % (assocClassName))
        if not assocClassName:
            raise pywbem.CIMError(pywbem.CIM_ERR_FAILED, 
                    "Empty assocClassName passed to AssociatorNames")
        model = pywbem.CIMInstance(classname=assocClassName)
        model.path = pywbem.CIMInstanceName(classname=assocClassName, 
                                            namespace=objectName.namespace)
        gen = self.references(env=env, 
                                    object_name=objectName, 
                                    model=model,
                                    result_class_name=resultClassName, 
                                    role=role, 
                                    result_role=None,
                                    keys_only=False)
        if gen is None:
            logger.log_debug('references() returned None instead of generator object')
            return
        for inst in gen:
            for prop in inst.properties.values():
                lpname = prop.name.lower()
                if prop.type != 'reference':
                    continue
                if role and role.lower() == lpname:
                    continue
                if resultRole and resultRole.lower() != lpname:
                    continue
                if self.paths_equal(prop.value, objectName):
                    continue
                if resultClassName and  \
                        resultClassName.lower() != prop.value.classname.lower():
                    continue
                if prop.value.namespace is None:
                    prop.value.namespace = objectName.namespace
                yield prop.value
        logger.log_debug('CIMProvider2 MI_associatorNames returning')

    def MI_references(self, 
                      env, 
                      objectName, 
                      resultClassName, 
                      role, 
                      propertyList):
        """Return instances of an association class.

        Implements the WBEM operation References in terms 
        of the references method.  A derived class will not normally
        override this method.

        """

        logger = env.get_logger()
        logger.log_debug('CIMProvider2 MI_references called. resultClass: %s' % (resultClassName))
        if not resultClassName:
            raise pywbem.CIMError(pywbem.CIM_ERR_FAILED, 
                    "Empty resultClassName passed to References")
        plist = None
        if propertyList is not None:
            plist = [s.lower() for s in propertyList] 
        model = pywbem.CIMInstance(classname=resultClassName, 
                property_list=plist)
        model.path = pywbem.CIMInstanceName(classname=resultClassName, 
                                            namespace=objectName.namespace)
        if role:
            if role not in model.properties:
                raise pywbem.CIMError(pywbem.CIM_ERR_FAILED, 
                                      "** this shouldn't happen")
            model[role] = objectName

        gen = self.references(env=env, 
                                    object_name=objectName, 
                                    model=model,
                                    result_class_name='', 
                                    role=role, 
                                    result_role=None,
                                    keys_only=False)
        if gen is None:
            logger.log_debug('references() returned None instead of generator object')
            return
        for inst in gen:
            for prop in inst.properties.values():
                if hasattr(prop.value, 'namespace') and \
                        prop.value.namespace is None:
                    prop.value.namespace = objectName.namespace
            yield inst
        logger.log_debug('CIMProvider2 MI_references returning')

    def MI_referenceNames(self, 
                          env, 
                          objectName, 
                          resultClassName, 
                          role):
        """Return instance names of an association class.

        Implements the WBEM operation ReferenceNames in terms 
        of the references method.  A derived class will not normally
        override this method.

        """

        logger = env.get_logger()
        logger.log_debug('CIMProvider2 MI_referenceNames <2> called. resultClass: %s' % (resultClassName))
        if not resultClassName:
            raise pywbem.CIMError(pywbem.CIM_ERR_FAILED, 
                    "Empty resultClassName passed to ReferenceNames")

        model = pywbem.CIMInstance(classname=resultClassName)
        model.path = pywbem.CIMInstanceName(classname=resultClassName, 
                                            namespace=objectName.namespace)
        if role:
            if role not in model.properties:
                raise pywbem.CIMError(pywbem.CIM_ERR_FAILED, 
                                      "** this shouldn't happen")
            model[role] = objectName
        gen = self.references(env=env, 
                                    object_name=objectName, 
                                    model=model,
                                    result_class_name='', 
                                    role=role, 
                                    result_role=None,
                                    keys_only=True)
        if gen is None:
            logger.log_debug('references() returned None instead of generator object')
            return 
        for inst in gen:
            for prop in inst.properties.values():
                if hasattr(prop.value, 'namespace') and prop.value.namespace is None:
                    prop.value.namespace = objectName.namespace
            yield inst.path
        logger.log_debug('CIMProvider2 MI_referenceNames returning')

    def MI_invokeMethod(self, env, objectName, methodName, inputParams):
        """Invoke an extrinsic method.

        Implements the InvokeMethod WBEM operation by calling the 
        method on a derived class called cim_method_<method_name>, 
        where <method_name> is the name of the CIM method, in all 
        lower case.  
        
        Arguments:
        env -- Provider Environment (pycimmb.ProviderEnvironment)
        objectName -- The InstanceName or ClassName of the object on 
        which the method is invoked.
        methodName -- The name of the method to be invoked. 
        inputParams -- A Dictionary where the key is the parameter name
            and the value is the parameter value.

        The return value for invokeMethod must be a tuple of size 2 
        where: 
        element 0 is a tuple of size 2 where element 0 is the return 
            data type name and element 1 is the actual data value.
        element 1 is a dictionary where the key is the output 
            parameter name and the value is a tuple of size 2 where 
            element 0 is the data type name for the output parameter 
            and element 1 is the actual value of the output parameter.

        A derived class will not normally override this method. 

        """

        logger = env.get_logger()
        logger.log_debug('CIMProvider2 MI_invokeMethod called. method: %s:%s' \
                % (objectName.classname,methodName))
        lmethName = "cim_method_%s" % methodName.lower()
        if hasattr(self, lmethName) :
            method = getattr(self, lmethName)
            new_inputs = dict([('param_%s' % k.lower(), v) \
                            for k, v in inputParams.items()])
            try:
                (rval, outs) = method(env=env, object_name=objectName, 
                                  **new_inputs)
            except TypeError, e:
                raise pywbem.CIMError(pywbem.CIM_ERR_INVALID_PARAMETER, str(e))

            def add_type(v):
                if isinstance(v, pywbem.CIMParameter):
                    return (v.type, v.value)
                lv = v
                if type(v) == list and len(v) > 0:
                    lv = v[0]
                if isinstance(lv, pywbem.CIMClass):
                    tp = 'class'
                elif isinstance(lv, pywbem.CIMInstance):
                    tp = 'instance'
                elif isinstance(lv, pywbem.CIMInstanceName):
                    tp = 'reference'
                elif v is None or (type(v) == list and len(v) == 0):
                    assert(None == 'This should not happen')
                else:
                    tp = pywbem.cimtype(v)
                return (tp, v)

            louts = {}
            for op in outs:
                louts[op.name] = (op.type, op.value)
            rval = add_type(rval)
            rval = (rval, louts)
        else:
            raise pywbem.CIMError(pywbem.CIM_ERR_METHOD_NOT_FOUND, 
                              "%s:%s"%(objectName.classname, methodName))
        logger.log_debug('CIMProvider2 MI_invokeMethod returning')
        return rval

    def filter_instance(self, inst, plist):
        """Remove properties from an instance that aren't in the PropertyList
        
        inst -- The CIMInstance
        plist -- The property List, or None.  The list items must be all 
            lowercase.
            
        """

        if plist is not None:
            for pname in inst.properties.keys():
                if pname.lower() not in plist and pname:
                    if inst.path is not None and pname in inst.path.keybindings:
                        continue
                    del inst.properties[pname]

    def authorize_filter (env, filter, ns, classes, 
                     owner):
        """Allow or disallow an indication subscription request.
        
        Arguments:
        env -- Provider Environment (pycimmb.ProviderEnvironment)
        filter -- The WQL select statement
        namespace -- The namepace where the indication is registered for 
        classes -- The classpath of the indication registered for
        owner -- The name of the principal (cimom user)
        """
        pass

    def activate_filter (env, filter, ns, classes, 
                     first_activation):
        """Activate an indication subscription.
        
        Arguments:
        env -- Provider Environment (pycimmb.ProviderEnvironment)
        filter -- The WQL select statement
        namespace -- The namepace where the indication is registered for 
        classes -- The classpath of the indication registered for
        first_activation -- boolean - whether first activation
        """
        pass

    def deactivate_filter(env, filter, ns, classes, 
                      last_activation):
        """Deactivate an indication subscription.
        
        Arguments:
        env -- Provider Environment (pycimmb.ProviderEnvironment)
        filter -- The WQL select statement
        ns -- The namepace where the indication is registered for  
        classes -- The classpath of the indication registered for
        last_activation -- boolean - whether last activation
        """
        pass

    def enable_indications(env):
        """Enable indications.
        
        Arguments:
        env -- Provider Environment (pycimmb.ProviderEnvironment)
        """
        pass

    def disable_indications(env):
        """Disable indications.
        
        Arguments:
        env -- Provider Environment (pycimmb.ProviderEnvironment)
        """
        pass
    

def codegen (cc):
    """Generate a Python Provider template. 

    Parameters: 
    cc - A CIMClass to generate code for. 

    Returns a two-tuple containing the Python provider code stubs, and 
        the provider registration MOF.

    """

    import inspect

    def format_desc (obj, indent):
        linelen = 75 - indent
        if isinstance(obj, basestring):
            raw = obj
        else:
            try:
                raw = obj.qualifiers['description'].value
            except KeyError:
                return ''
        txt = ''
        beg = 0
        end = 0
        while beg < len(raw):
            beg = end
            end += linelen
            while beg < len(raw) and raw[beg].isspace():
                beg = beg+1
            while end < len(raw) and end > beg and not raw[end].isspace():
                end = end-1
            if beg == end: # a long URL
                while end < len(raw) and not raw[end].isspace():
                    end+= 1
            line = raw[beg:end]
            line = line.replace('\n',' ')
            line = line.replace('\r','')
            txt += '\n%s%s'% (''.ljust(indent), line)
        return txt

    #################
    def map_value(obj, val):
        rv = str(val)
        if 'ValueMap' not in obj.qualifiers:
            return rv
        if 'Values' not in obj.qualifiers:
            return rv
        vals = [str(x) for x in obj.qualifiers['Values'].value]
        maps = [str(x) for x in obj.qualifiers['ValueMap'].value]
        d = dict(zip(maps, vals))
        try:
            tmp = d[str(val)]
            rv = ''
            for ch in tmp:
                rv+= ch.isalnum() and ch or '_'
        except KeyError:
            pass
        return rv
            
    #################
    def type_hint (obj, method_name=None):
        if hasattr(obj, 'type'):
            tx = obj.type
            if 'embeddedinstance' in obj.qualifiers:
                tx = "pywbem.CIMInstance(classname='%s', ...)" % \
                        obj.qualifiers['embeddedinstance'].value
            elif tx == 'reference':
                tx = "pywbem.CIMInstanceName(classname='%s', ...)" % \
                        obj.reference_class
        else:
            tx = obj.return_type
        if hasattr(obj, 'value') and obj.value is not None:
            defval = str(obj.value)
        else:
            defval = ''
        if not tx.startswith('pywbem.'):
            if tx == 'boolean':
                tx = 'bool(%s)' % defval
            elif tx == 'datetime':
                tx = 'pywbem.CIMDateTime()'
            elif tx == 'string':
                tx = "''"
            else:
                tx = 'pywbem.%s(%s)' % (tx.capitalize(), defval)
        if 'valuemap' in obj.qualifiers:
            if defval:
                defval = map_value(obj, defval)
            else:
                defval = '<VAL>'
            tx = 'self.Values.%s%s.%s' % \
                    (method_name and '%s.'%method_name or '',
                            obj.name, defval)
        if hasattr(obj, 'is_array') and obj.is_array:
            tx = '[%s,]' % tx
        return tx
    #################
    def type_str (obj, method_name=None):
        if hasattr(obj, 'type'):
            tx = obj.type
            if 'embeddedinstance' in obj.qualifiers:
                return "pywbem.CIMInstance(classname='%s', ...)" % \
                        obj.qualifiers['embeddedinstance'].value
            elif tx == 'reference':
                return "REF (pywbem.CIMInstanceName(classname='%s', ...)" % \
                        obj.reference_class
        else:
            tx = obj.return_type
        if tx == 'boolean':
            tx = 'bool'
        elif tx == 'datetime':
            tx = 'pywbem.CIMDateTime'
        elif tx == 'string':
            tx = 'unicode'
        else:
            tx = 'pywbem.%s' % tx.capitalize()
        if hasattr(obj, 'is_array') and obj.is_array:
            tx = '[%s,]' % tx
        if 'valuemap' in obj.qualifiers:
            tx+= ' self.Values.%s%s' % \
                    (method_name and '%s.'%method_name or '',obj.name)
        return tx
    #################
    def is_required (obj):
        if 'required' in obj.qualifiers and obj.qualifiers['required'].value:
            return '(Required)'
        return ''
    #################
    def build_reverse_val_map(obj):
        vm = obj.qualifiers['valuemap'].value
        if 'values' in obj.qualifiers:
            vals = obj.qualifiers['values'].value
        else:
            vals = vm
        tmap = zip(vals,vm)
        rv = {}
        for val, vm in tmap:
            try:
                vmi = int(vm)
            except ValueError:
                continue
            rv[vmi] = str(val) # we want normal strings, not unicode
        return rv 
    #################
    def build_val_map(obj):
        vm = obj.qualifiers['valuemap'].value
        if 'values' in obj.qualifiers:
            vals = obj.qualifiers['values'].value
        else:
            vals = vm
        tmap = zip(vals,vm)
        map = []
        for t in tmap:
            nname = ''
            for ch in t[0]:
                if ch.isalnum():
                    nname+= ch
                else:
                    nname+= '_'
            if hasattr(obj, 'return_type'):
                tp = obj.return_type
            else:
                tp = obj.type
            if tp == 'string':
                val = "'%s'" % t[1]
            else:
                try:
                    int(t[1])
                    val = 'pywbem.%s(%s)' % (tp.capitalize(), t[1])
                except ValueError:
                    val = t[1]
                    nname = "# "+nname
            map.append((nname,val))
        return map

    valuemaps = {}
    rvaluemaps = pywbem.NocaseDict()

    for prop in cc.properties.values():
        if 'valuemap' in prop.qualifiers and 'values' in prop.qualifiers:
            rvaluemaps[prop.name] = build_reverse_val_map(prop)

    for obj in cc.properties.values() + cc.methods.values():
        if 'valuemap' in obj.qualifiers:
            valuemaps[obj.name] = {'<vms>':build_val_map(obj)}

    for meth in cc.methods.values():
        for parm in meth.parameters.values():
            if 'valuemap' in parm.qualifiers:
                if meth.name not in valuemaps:
                    valuemaps[meth.name] = {}
                valuemaps[meth.name][parm.name] = build_val_map(parm)

    mappings = {'classname':cc.classname,
                'classname_l':cc.classname.lower()}
    isAssoc = 'association' in cc.qualifiers
    isIndication = 'indication' in cc.qualifiers

    code = '''"""Python Provider for %(classname)s

Instruments the CIM class %(classname)s

"""

import pywbem
from pywbem.cim_provider2 import CIMProvider2

class %(classname)s(CIMProvider2):
    """Instrument the CIM class %(classname)s \n''' % mappings
    code+= format_desc(cc, 4)
    code+= '''
    """'''


    args = inspect.getargspec(CIMProvider2.get_instance)[0]
    args = ', '.join(args)
    code+= '''

    def __init__ (self, env):
        logger = env.get_logger()
        logger.log_debug('Initializing provider %%s from %%s' \\
                %% (self.__class__.__name__, __file__))

    def get_instance(%s):
        """%s"""
        
        logger = env.get_logger()
        logger.log_debug('Entering %%s.get_instance()' \\
                %% self.__class__.__name__)
        ''' % (args, CIMProvider2.get_instance.__doc__ )
    keyProps = [p for p in cc.properties.values() \
                if 'key' in p.qualifiers]
    if not keyProps and 'association' in cc.qualifiers:
        # SFCB has problems with qualifiers on REF properties. 
        # http://sourceforge.net/tracker/index.php?func=detail&aid=2104565&group_id=128809&atid=712784
        keyProps = [p for p in cc.properties.values() \
                    if p.type == 'reference']
        for prop in keyProps:
            prop.qualifiers['KEY'] = True
    code+= '''

        # TODO fetch system resource matching the following keys:'''
    for kp in keyProps:
        code+= '''
        #   model['%s']''' % kp.name
    code+= '\n'
    props = cc.properties.values()
    props.sort()
    for prop in props:
        if 'key' in prop.qualifiers:
            continue
        line = "#model['%s'] = %s # TODO %s" % \
                (prop.name, type_hint(prop), is_required(prop))
        code+= '''
        %s''' % line

    args = inspect.getargspec(CIMProvider2.enum_instances)[0]
    args = ', '.join(args)
    code+= '''
        return model

    def enum_instances(%s):
        """%s"""

        logger = env.get_logger()
        logger.log_debug('Entering %%s.enum_instances()' \\
                %% self.__class__.__name__)
                '''  % (args, CIMProvider2.enum_instances.__doc__)
    keydict = dict([(str(kp.name), None) for kp in keyProps])
    code+= '''
        # Prime model.path with knowledge of the keys, so key values on
        # the CIMInstanceName (model.path) will automatically be set when
        # we set property values on the model. 
        model.pa%s
        ''' % format_desc('th.update('+str(keydict)+')', 12).strip()

    code+= '''
        while False: # TODO more instances?
            # TODO fetch system resource
            # Key properties''' 
    for kp in keyProps:
        if kp.name == 'CreationClassName':
            line = "model['%s'] = '%s'" % (kp.name, cc.classname)
        else:
            line = "#model['%s'] = %s # TODO (type = %s)" % \
                    (kp.name, type_hint(kp), type_str(kp))
        code+='''    
            %s''' % line
    code+='''
            if keys_only:
                yield model
            else:
                try:
                    yield self.get_instance(env, model)
                except pywbem.CIMError, (num, msg):
                    if num not in (pywbem.CIM_ERR_NOT_FOUND, 
                                   pywbem.CIM_ERR_ACCESS_DENIED):
                        raise\n'''

    args = inspect.getargspec(CIMProvider2.set_instance)[0]
    args = ', '.join(args)
    code+= '''
    def set_instance(%s):
        """%s"""

        logger = env.get_logger()
        logger.log_debug('Entering %%s.set_instance()' \\
                %% self.__class__.__name__)
        # TODO create or modify the instance
        raise pywbem.CIMError(pywbem.CIM_ERR_NOT_SUPPORTED) # Remove to implement
        return instance''' % (args, CIMProvider2.set_instance.__doc__)

    args = inspect.getargspec(CIMProvider2.delete_instance)[0]
    args = ', '.join(args)
    code+= '''

    def delete_instance(%s):
        """%s""" 

        logger = env.get_logger()
        logger.log_debug('Entering %%s.delete_instance()' \\
                %% self.__class__.__name__)

        # TODO delete the resource
        raise pywbem.CIMError(pywbem.CIM_ERR_NOT_SUPPORTED) # Remove to implement
        ''' % (args, CIMProvider2.delete_instance.__doc__)
                
    for method in cc.methods.values():
        inParms = [ p for p in method.parameters.values() if \
                    'in' in p.qualifiers and p.qualifiers['in'].value ]
        outParms = [ p for p in method.parameters.values() if \
                    'out' in p.qualifiers and p.qualifiers['out'].value ]
        code+= '''
    def cim_method_%s(self, env, object_name''' % method.name.lower()
        for p in inParms:
            if 'required' in p.qualifiers and p.qualifiers['required']:
                code+= ''',\n%sparam_%s''' % (''.rjust(len(method.name)+20),
                                                        p.name.lower())
        for p in inParms:
            if 'required' not in p.qualifiers or not p.qualifiers['required']:
                code+= ''',\n%sparam_%s=None'''%\
                                        (''.rjust(len(method.name)+20),
                                         p.name.lower())
        code+= '''):
        """Implements %s.%s()\n''' % (cc.classname, method.name)
        code+= format_desc(method, 8)

        code+= '''
        Keyword arguments:
        env -- Provider Environment (pycimmb.ProviderEnvironment)
        object_name -- A pywbem.CIMInstanceName or pywbem.CIMCLassName 
            specifying the object on which the method %s() 
            should be invoked.'''\
                % method.name

        for p in inParms:
            code+= '''
        param_%s --  The input parameter %s (type %s) %s''' \
                    % (p.name.lower(), p.name, type_str(p, method.name), 
                       is_required(p))
            code+= format_desc(p, 12)

        code+='''

        Returns a two-tuple containing the return value (type %s)
        and a list of CIMParameter objects representing the output parameters

        Output parameters:''' % type_str(method)

        if not outParms:
            code+= ' none'
        else:
            for p in outParms:
                code+='''
        %s -- (type %s) %s''' % (p.name, type_str(p, method.name), 
                                 is_required(p))
                code+= format_desc(p, 12)

        code+='''

        Possible Errors:
        CIM_ERR_ACCESS_DENIED
        CIM_ERR_INVALID_PARAMETER (including missing, duplicate, 
            unrecognized or otherwise incorrect parameters)
        CIM_ERR_NOT_FOUND (the target CIM Class or instance does not 
            exist in the specified namespace)
        CIM_ERR_METHOD_NOT_AVAILABLE (the CIM Server is unable to honor 
            the invocation request)
        CIM_ERR_FAILED (some other unspecified error occurred)

        """

        logger = env.get_logger()
        logger.log_debug('Entering %%s.cim_method_%s()' \\
                %% self.__class__.__name__)

        # TODO do something
        raise pywbem.CIMError(pywbem.CIM_ERR_METHOD_NOT_AVAILABLE) # Remove to implemented
        out_params = []''' % method.name.lower()

        for p in outParms:
            code+='''
        #out_params+= [pywbem.CIMParameter('%s', type='%s', 
        #                   value=%s)] # TODO''' % (p.name.lower(), p.type,
                type_hint(p, method.name))

        code+='''
        #rval = # TODO (type %s)
        return (rval, out_params)
        ''' % type_str(method)

    if isAssoc:
        args = inspect.getargspec(CIMProvider2.references)[0]
        args = format_desc(', '.join(args), 19).strip()
        code+= '''
    def references(%s):
        """%s"""

        logger = env.get_logger()
        logger.log_debug('Entering %%s.references()' \\
                %% self.__class__.__name__)
        ch = env.get_cimom_handle()''' % \
                (args, CIMProvider2.references.__doc__)

        refprops = []
        for prop in cc.properties.values():
            if prop.reference_class is not None:
                refprops.append((prop.name, prop.reference_class))

        code+= '''\n
        # If you want to get references for free, implemented in terms 
        # of enum_instances, just leave the code below unaltered.'''

        for i, refprop in enumerate(refprops):
            if i == 0:
                code+= '''
        if ch.is_subclass(object_name.namespace, 
                          sub=object_name.classname,
                          super='%s')''' % refprop[1]
                          
            else:
                code+= ''' or \\
                ch.is_subclass(object_name.namespace,
                               sub=object_name.classname,
                               super='%s')''' % refprop[1]
        code+=''':
            return self.simple_refs(env, object_name, model,
                          result_class_name, role, result_role, keys_only)
                          '''


        code+='''
        # If you are doing simple refs with the code above, remove the 
        # remainder of this method.  Or, remove the stuff above and 
        # implement references below.  You need to pick either the 
        # above approach or the below, and delete the other.  Otherwise
        # you'll get a SyntaxError on the first yield below. 
        
        # Prime model.path with knowledge of the keys, so key values on
        # the CIMInstanceName (model.path) will automatically be set when
        # we set property values on the model. 
        model.pa%s

        # This is a common pattern.  YMMV''' % \
                   format_desc('th.update('+str(keydict)+')', 12).strip()

        for refprop in refprops:
            code+= '''
        if (not role or role.lower() == '%(refpropnamel)s') and \\
           ch.is_subclass(object_name.namespace, 
                       sub=object_name.classname, 
                       super='%(rolecname)s'):
            model['%(refpropname)s'] = object_name
            yield model # TODO: Add other REF properties. 
                        # Yield association instances where 
                        # object_name is %(refpropnamel)s.
                        # Only appropriate if object_name.classname 
                        # is '%(rolecname)s' or a subclass.\n''' \
                               % {'refpropname':refprop[0],
                                  'refpropnamel':refprop[0].lower(),
                                  'rolecname':refprop[1]}

    if valuemaps:
        code+= '''
    class Values(object):'''
        for group, maps in valuemaps.items():
            code+= '''
        class %s(object):''' % group
            if '<vms>' in maps:
                for value, vm in maps['<vms>']:
                    if value in maps:
                        value = value+'_'
                    code+= '''
            %s = %s''' % (value, vm)
            if group in rvaluemaps:
                code+= '''
            _reverse_map = %s''' % repr(rvaluemaps[group])
            for pname, vms in maps.items():
                if pname == '<vms>':
                    continue
                code+= '''
            class %s(object):''' % pname
                for value, vm in vms:
                    code+= '''
                %s = %s''' % (value, vm)
            code+= '\n'

    code+= '''
## end of class %(classname)sProvider
    
## get_providers() for associating CIM Class Name to python provider class name
    
def get_providers(env): 
    %(classname_l)s_prov = %(classname)s(env)  
    return {'%(classname)s': %(classname_l)s_prov} 
''' % mappings

    if isIndication:
        code+= '''

## Indication support methods...
##   Use these methods if this class will deliver indications.
##   Remove these methods if this class will not deliver indications.'''
        args = inspect.getargspec(CIMProvider2.authorize_filter)[0]
        args = format_desc(', '.join(args), 19).strip()
        code+= '''
       
        
def authorize_filter(%s):
    """%s"""

    logger = env.get_logger()
    logger.log_debug('Entering %%s.authorize_filter()' \\
            %% self.__class__.__name__)
    ch = env.get_cimom_handle()
    #raise pywbem.CIMError(pywbem.CIM_ERR_***) to indicate failure
    #otherwise just fall through for success''' % \
            (args, CIMProvider2.authorize_filter.__doc__ or "Doc Goes Here")

        args = inspect.getargspec(CIMProvider2.enable_indications)[0]
        args = format_desc(', '.join(args), 19).strip()
        code+= '''
       
        
def enable_indications(%s):
    """%s"""

    logger = env.get_logger()
    logger.log_debug('Entering %%s.enable_indications()' \\
            %% self.__class__.__name__)
    ch = env.get_cimom_handle()
    #raise pywbem.CIMError(pywbem.CIM_ERR_***) to indicate failure
    #otherwise just fall through for success''' % \
            (args, CIMProvider2.enable_indications.__doc__ or "Doc Goes Here")

        args = inspect.getargspec(CIMProvider2.disable_indications)[0]
        args = format_desc(', '.join(args), 19).strip()
        code+= '''
       
        
def disable_indications(%s):
    """%s"""

    logger = env.get_logger()
    logger.log_debug('Entering %%s.disable_indications()' \\
            %% self.__class__.__name__)
    ch = env.get_cimom_handle()
    #raise pywbem.CIMError(pywbem.CIM_ERR_***) to indicate failure
    #otherwise just fall through for success''' % \
            (args, CIMProvider2.disable_indications.__doc__ or "Doc Goes Here")

        args = inspect.getargspec(CIMProvider2.activate_filter)[0]
        args = format_desc(', '.join(args), 19).strip()
        code+= '''
       
        
def activate_filter(%s):
    """%s"""

    logger = env.get_logger()
    logger.log_debug('Entering %%s.activate_filter()' \\
            %% self.__class__.__name__)
    ch = env.get_cimom_handle()
    #raise pywbem.CIMError(pywbem.CIM_ERR_***) to indicate failure
    #otherwise just fall through for success''' % \
            (args, CIMProvider2.activate_filter.__doc__ or "Doc Goes Here")

    
        args = inspect.getargspec(CIMProvider2.deactivate_filter)[0]
        args = format_desc(', '.join(args), 19).strip()
        code+= '''
       
        
def deactivate_filter(%s):
    """%s"""

    logger = env.get_logger()
    logger.log_debug('Entering %%s.deactivate_filter()' \\
            %% self.__class__.__name__)
    ch = env.get_cimom_handle()
    #raise pywbem.CIMError(pywbem.CIM_ERR_***) to indicate failure
    #otherwise just fall through for success''' % \
            (args, CIMProvider2.deactivate_filter.__doc__ or "Doc Goes Here")

        code+= '''

## End of Indication Support Methods'''

    owtypes = ['1', 'Instance']
    pegtypes = ['2', 'Instance']
    sfcbtypes = 'instance'
    if isAssoc:
        owtypes[0]+= ',3'
        owtypes[1]+= ', Associator'
        pegtypes[0]+= ',3'
        pegtypes[1]+= ', Associator'
        sfcbtypes+= ' association'
    if cc.methods:
        owtypes[0]+= ',6'
        owtypes[1]+= ', Method'
        pegtypes[0]+= ',5'
        pegtypes[1]+= ', Method'
        sfcbtypes+= ' method'
    omitted = '''
// OpenWBEM Provider registration for %(classname)s
instance of OpenWBEM_PyProviderRegistration
{
    InstanceID = "<org:product:%(classname)s:unique_id>"; // TODO
    NamespaceNames = {"root/cimv2"}; // TODO
    ClassName = "%(classname)s"; 
    ProviderTypes = {%(owtypeNums)s};  // %(owtypeStrs)s
    ModulePath = "/usr/lib/pycim/%(classname)sProvider.py";  // TODO
}; 
    '''

    mof ='''
// SFCB Provider registration for %(classname)s
[%(classname)s]
   provider: %(classname)s
   location: pyCmpiProvider
   type: %(sfcbtypes)s
   namespace: root/cimv2 // TODO

// Pegasus Provider registration for %(classname)s
instance of PG_ProviderModule
{
    Name = "pyCmpiProvider_%(classname)s";
    InterfaceType = "CMPI";
    InterfaceVersion = "2.0.0";
    Location = "pyCmpiProvider"; 
    UserContext = 2; // Requestor
    Vendor = "TODO"; // TODO
    Version = "1.0";
}; 
instance of PG_Provider
{
    Name = "%(classname)s"; 
    ProviderModuleName = "pyCmpiProvider_%(classname)s";
}; 
instance of PG_ProviderCapabilities
{
    CapabilityID = "%(classname)s";
    ProviderModuleName = "pyCmpiProvider_%(classname)s";
    ProviderName = "%(classname)s";
    ClassName = "%(classname)s";
    Namespaces = {"root/cimv2"}; // TODO
    ProviderType = {%(pegtypeNum)s}; // %(pegtypeStr)s
};\n''' % {'classname': cc.classname, 
            'owtypeNums': owtypes[0], 
            'owtypeStrs': owtypes[1],
            'pegtypeNum': pegtypes[0], 
            'pegtypeStr': pegtypes[1],
            'sfcbtypes' : sfcbtypes}

                
    return code, mof

class ProviderProxy(object):
    """Wraps a provider module, and routes requests into the module """

    def __init__ (self, env, provid):
        self.env = env
        if isinstance(provid, types.ModuleType):
            self.provmod = provid
            self.provid = provid.__name__
            self.filename = provid.__file__
        else:
            logger = env.get_logger()
            logger.log_debug('Loading python provider at %s' %provid)
            self.provid = provid
            self._load_provider_source()
        self._init_provider(env)

    def _init_provider (self, env):
        self.provregs = {}
        if hasattr(self.provmod, 'init'):
            self.provmod.init(env)
        if hasattr(self.provmod, 'get_providers'):
            self.provregs = pywbem.NocaseDict(self.provmod.get_providers(env))

    def _load_provider_source (self):
        self.provider_module_name = os.path.basename(self.provid)[:-3]
        # let providers import other providers in the same directory
        provdir = dirname(self.provid)
        if provdir not in sys.path:
            sys.path.append(provdir)
        try:
            self.provmod = sys.modules[self.provider_module_name]
            print 'Provider %s already loaded, found in sys.modules' \
                    % self.provmod
        except KeyError:
            try: 
                # use full path in module name for uniqueness. 
                print 'Loading provider %s from source' % self.provid
                fn = imp.find_module(self.provider_module_name, [provdir])
                try:
                    g_mod_lock.acquire()
                    imp.acquire_lock()
                    self.provmod = imp.load_module(
                            self.provider_module_name, *fn)
                    self.provmod.provmod_timestamp = \
                            os.path.getmtime(self.provid)
                finally:
                    imp.release_lock()
                    g_mod_lock.release()
                    fn[0].close()
            except IOError, arg:
                raise pywbem.CIMError(pywbem.CIM_ERR_FAILED, 
                        "Error loading provider %s: %s" % (self.provid, arg))
        self.filename = self.provmod.__file__

    def _get_callable (self, classname, cname):
        """Return a function or method object appropriate to fulfill a request

        classname -- The CIM class name associated with the request. 
        cname -- The function or method name to look for.

        """

        callable = None
        if classname in self.provregs:
            provClass = self.provregs[classname]
            if hasattr(provClass, cname):
                callable = getattr(provClass, cname)
        elif hasattr(self.provmod, cname):
            callable = getattr(self.provmod, cname)
        if callable is None:
            raise pywbem.CIMError(pywbem.CIM_ERR_FAILED, 
                    "No provider registered for %s or no callable for %s:%s on provider %s"%(classname, classname,
                                                            cname, 
                                                            self.provid))
        return callable

    def _reload_if_necessary (self, env):
        """Check timestamp of loaded python provider module, and if it has
        changed since load, then reload the provider module.
        """
        try:
            mod = sys.modules[self.provider_module_name]
        except KeyError:
            mod = None
        if (mod is None or \
                mod.provmod_timestamp != os.path.getmtime(self.provid)):
            print "Need to reload provider at %s" %self.provid

            #first unload the module
            if self.provmod and hasattr(self.provmod, "shutdown"):
                self.provmod.shutdown(env)
            #now reload and reinit module
            try:
                del sys.modules[self.provider_module_name]
            except KeyError:
                pass
            try: 
                self._load_provider_source()
                self._init_provider(env)
            except IOError, arg:
                raise pywbem.CIMError(pywbem.CIM_ERR_FAILED, 
                        "Error loading provider %s: %s" % (provid, arg))


##############################################################################
# enumInstanceNames
##############################################################################
    def MI_enumInstanceNames (self, 
                              env,
                              objPath):
        logger = env.get_logger()
        logger.log_debug('ProviderProxy MI_enumInstanceNames called...')
        self._reload_if_necessary(env)
        return self._get_callable(objPath.classname, 
                                    'MI_enumInstanceNames')(env, objPath)

##############################################################################
# enumInstances
##############################################################################
    def MI_enumInstances(self, 
                         env, 
                         objPath, 
                         propertyList):
        logger = env.get_logger()
        logger.log_debug('CIMProvider2 MI_enumInstances called...')
        self._reload_if_necessary(env)
        return self._get_callable(objPath.classname, 'MI_enumInstances') \
                           (env, 
                            objPath, 
                            propertyList)

##############################################################################
# getInstance
##############################################################################
    def MI_getInstance(self, 
                       env, 
                       instanceName, 
                       propertyList):
        logger = env.get_logger()
        logger.log_debug('CIMProvider2 MI_getInstance called...')
        self._reload_if_necessary(env)
        rval = self._get_callable(instanceName.classname, 'MI_getInstance')  \
               (env, 
                instanceName, 
                propertyList)
        logger.log_debug('CIMProvider2 MI_getInstance returning')
        return rval

##############################################################################
# createInstance
##############################################################################
    def MI_createInstance(self, 
                          env, 
                          instance):
        logger = env.get_logger()
        logger.log_debug('CIMProvider2 MI_createInstance called...')
        self._reload_if_necessary(env)
        rval = self._get_callable(instance.classname, 'MI_createInstance')  \
                (env, instance)
        logger.log_debug('CIMProvider2 MI_createInstance returning')
        return rval

##############################################################################
# modifyInstance
##############################################################################
    def MI_modifyInstance(self, 
                          env, 
                          modifiedInstance, 
                          propertyList):
        logger = env.get_logger()
        logger.log_debug('CIMProvider2 MI_modifyInstance called...')
        self._reload_if_necessary(env)
        self._get_callable(modifiedInstance.classname, 'MI_modifyInstance')  \
                (env, modifiedInstance, propertyList)
        logger.log_debug('CIMProvider2 MI_modifyInstance returning')
    
##############################################################################
# deleteInstance
##############################################################################
    def MI_deleteInstance(self, 
                          env, 
                          instanceName):
        logger = env.get_logger()
        logger.log_debug('CIMProvider2 MI_deleteInstance called...')
        self._reload_if_necessary(env)
        self._get_callable(instanceName.classname, 'MI_deleteInstance')  \
                (env, instanceName)
        logger.log_debug('CIMProvider2 MI_deleteInstance returning')


##############################################################################
# associators
##############################################################################
    def MI_associators(self, 
                       env, 
                       objectName, 
                       assocClassName, 
                       resultClassName, 
                       role, 
                       resultRole, 
                       propertyList):
        # NOTE: This should honor the parameters resultClassName, role, resultRole, 
        #       and propertyList
        logger = env.get_logger()
        logger.log_debug('CIMProvider2 MI_associators called. assocClass: %s' % (assocClassName))
        self._reload_if_necessary(env)

        cname = assocClassName
        if not cname and hasattr(self.provmod, 'MI_associators'):
            for i in self.provmod.MI_associators(
                       env, 
                       objectName, 
                       assocClassName, 
                       resultClassName, 
                       role, 
                       resultRole, 
                       propertyList):
                yield i
                return

        lcnames = []
        if cname:
            lcnames = [cname]
        else:
            lcnames = self.provregs.keys()

        for lcname in lcnames:
            fn = self._get_callable(lcname, 'MI_associators')
            for i in fn(env, 
                       objectName, 
                       lcname, 
                       resultClassName, 
                       role, 
                       resultRole, 
                       propertyList):
                yield i
        logger.log_debug('CIMProvider2 MI_associators returning')

##############################################################################
# associatorNames
##############################################################################
    def MI_associatorNames(self, 
                           env, 
                           objectName, 
                           assocClassName, 
                           resultClassName, 
                           role, 
                           resultRole):
        logger = env.get_logger()
        logger.log_debug('CIMProvider2 MI_associatorNames called. assocClass: %s' % (assocClassName))
        self._reload_if_necessary(env)
        cname = assocClassName
        if not cname and hasattr(self.provmod, 'MI_associatorNames'):
            for i in self.provmod.MI_associatorNames(
                       env, 
                       objectName, 
                       assocClassName, 
                       resultClassName, 
                       role, 
                       resultRole):
                yield i
                return

        lcnames = []
        if cname:
            lcnames = [cname]
        else:
            lcnames = self.provregs.keys()

        for lcname in lcnames:
            fn = self._get_callable(lcname, 'MI_associatorNames')
            for i in fn(env, 
                       objectName, 
                       lcname, 
                       resultClassName, 
                       role, 
                       resultRole):
                yield i

        logger.log_debug('CIMProvider2 MI_associatorNames returning')

##############################################################################
# references
##############################################################################
    def MI_references(self, 
                      env, 
                      objectName, 
                      resultClassName, 
                      role, 
                      propertyList):
        logger = env.get_logger()
        logger.log_debug('CIMProvider2 MI_references called. resultClass: %s' % (resultClassName))
        self._reload_if_necessary(env)
        cname = resultClassName
        if not cname and hasattr(self.provmod, 'MI_references'):
            for i in self.provmod.MI_references(env, objectName, 
                    resultClassName, role, propertyList):
                yield i
                return

        lcnames = []
        if cname:
            lcnames = [cname]
        else:
            lcnames = self.provregs.keys()

        for lcname in lcnames:
            fn = self._get_callable(lcname, 'MI_references')
            for i in fn(env, 
                        objectName, 
                        lcname, 
                        role, 
                        propertyList):
                yield i

        logger.log_debug('CIMProvider2 MI_references returning')

##############################################################################
# referenceNames
##############################################################################
    def MI_referenceNames(self, 
                          env, 
                          objectName, 
                          resultClassName, 
                          role):
        logger = env.get_logger()
        logger.log_debug('CIMProvider2 MI_referenceNames <1> called. resultClass: %s' % (resultClassName))
        self._reload_if_necessary(env)

        cname = resultClassName
        if not cname and hasattr(self.provmod, 'MI_referenceNames'):
            for i in self.provmod.MI_referenceNames(env, objectName, 
                    resultClassName, role):
                yield i
                return

        lcnames = []
        if cname:
            lcnames = [cname]
        else:
            lcnames = self.provregs.keys()

        for lcname in lcnames:
            fn = self._get_callable(lcname, 'MI_referenceNames')
            for i in fn(env, 
                        objectName, 
                        lcname, 
                        role):
                yield i

        logger.log_debug('CIMProvider2 MI_referenceNames returning')

##############################################################################
# invokeMethod
#       inputParam is a Dictionary where the key is the parameter name
#       and the value is the parameter value
# The return value for invokeMethod must be a tuple of size 2 where
# element 0 is a tuple of size 2 where element 0 is the return data type name
#       and element 1 is the actual data value
# element 1 is a dictionary where the key is the output parameter name
#       and the value is a tuple of size 2 where element 0 is the data type name
#       for the output parameter and element 1 is the actual value of the 
#       output parameter.
##############################################################################
    def MI_invokeMethod(self, env, objectName, methodName, inputParams):
        logger = env.get_logger()
        logger.log_debug('CIMProvider2 MI_invokeMethod called. method: %s:%s' \
                % (objectName.classname,methodName))
        self._reload_if_necessary(env)
        rval = self._get_callable(objectName.classname, 'MI_invokeMethod')  \
                (env, objectName, methodName, inputParams)
        logger.log_debug('CIMProvider2 MI_invokeMethod returning')
        return rval
            
##############################################################################
    def MI_authorizeFilter (self,
                           env,
                           filter,
                           classname,
                           classPath,
                           owner):
        logger = env.get_logger()
        logger.log_debug('CIMProvider2 MI_authorizeFilter called')
        self._reload_if_necessary(env)
        if hasattr(self.provmod, 'authorize_filter'):
            self.provmod.authorize_filter(env, filter, classname,
                    classPath, owner)
        elif hasattr(self.provmod, 'MI_authorizeFilter'):
            self.provmod.MI_authorizeFilter(env, filter, classname,
                    classPath, owner)
        else:
            # if not instrumented in provider, assume success
            logger.log_debug("Provider %s has no support for authorize filter"%self.provid)
        logger.log_debug('CIMProvider2 MI_authorizeFilter returning')
        return


##############################################################################
    def MI_activateFilter (self, 
                           env, 
                           filter,
                           namespace,
                           classes,
                           firstActivation):
        logger = env.get_logger()
        logger.log_debug('CIMProvider2 MI_activateFilter called')
        self._reload_if_necessary(env)
        if hasattr(self.provmod, 'activate_filter'):
            self.provmod.activate_filter(env, filter, namespace,
                    classes, firstActivation)
        elif hasattr(self.provmod, 'MI_activateFilter'):
            self.provmod.MI_activateFilter(env, filter, namespace,
                    classes, firstActivation)
        else: 
            # if not instrumented in provider, assume success
            logger.log_debug("Provider %s has no support for activate filter"%self.provid)
        logger.log_debug('CIMProvider2 MI_activateFilter returning')
        return

                    
##############################################################################
    def MI_deActivateFilter(self,
                            env,
                            filter,
                            namespace,
                            classes,
                            lastActivation):
        logger = env.get_logger()
        logger.log_debug('CIMProvider2 MI_deActivateFilter called')
        self._reload_if_necessary(env)
        if hasattr(self.provmod, 'deactivate_filter'):
            self.provmod.deactivate_filter(env, filter, namespace, classes,
                    lastActivation)
        elif hasattr(self.provmod, 'MI_deActivateFilter'):
            self.provmod.MI_deActivateFilter(env, filter, namespace, classes,
                    lastActivation)
        else:
            # if not instrumented in provider, assume success
            logger.log_debug("Provider %s has no support for deactivate filter"%self.provid)
        logger.log_debug('CIMProvider2 MI_deActivateFilter returning')
        return


##############################################################################
    def MI_enableIndications(self,
                            env):
        logger = env.get_logger()
        logger.log_debug('CIMProvider2 MI_enableIndications called')
        self._reload_if_necessary(env)
        if hasattr(self.provmod, 'enable_indications'):
            self.provmod.enable_indications(env)
        elif hasattr(self.provmod, 'MI_enableIndications'):
            self.provmod.MI_enableIndications(env)
        else:
            # if not instrumented in provider, assume success
            logger.log_debug("Provider %s has no support for enable indications"%self.provid)
        logger.log_debug('CIMProvider2 MI_enableIndications returning')
        return


##############################################################################
    def MI_disableIndications(self,
                            env):
        logger = env.get_logger()
        logger.log_debug('CIMProvider2 MI_disableIndications called')
        self._reload_if_necessary(env)
        if hasattr(self.provmod, 'disable_indications'):
            self.provmod.disable_indications(env)
        elif hasattr(self.provmod, 'MI_disableIndications'):
            self.provmod.MI_disableIndications(env)
        else:
            # if not instrumented in provider, assume success
            logger.log_debug("Provider %s has no support for disable indications"%self.provid)
        logger.log_debug('CIMProvider2 MI_disableIndications returning')
        return


##############################################################################
    def MI_shutdown (self, env):
        # shutdown may be called multiple times -- once per MI type 
        # (instance/method/association/...)  We'll only do stuff on 
        # the first time. 
        if self.provmod is None:
            return
        modname = self.provmod.__name__
        if hasattr(self.provmod, "shutdown"):
            self.provmod.shutdown(env)
        self.provmod = None
        del sys.modules[modname]
        #TODO concurrency problems here??


##############################################################################
    def MI_canunload(self, env):
        if hasattr(self.provmod, "can_unload"):
            return self.provmod.can_unload(env)
        else:
            return True

##############################################################################
    def MI_consumeIndication(self,
                            env,
                            destinationPath,
                            indicationInstance):

        logger = env.get_logger()
        logger.log_debug('ProviderProxy MI_consumeIndication called')
        self._reload_if_necessary(env)
        if hasattr(self.provmod, 'consume_indication'):
            self.provmod.consume_indication(env, destinationPath, 
                    indicationInstance)
        elif hasattr(self.provmod, 'MI_consumeIndication'):
            self.provmod.MI_consumeIndication(env, destinationPath,
                    indicationInstance)
        else:
            raise pywbem.CIMError(pywbem.CIM_ERR_FAILED, 
                    "Provider %s has no support for consume indication" % \
                        self.provid)
        logger.log_debug('ProviderProxy MI_consumeIndication returning')


##############################################################################
    def MI_handleIndication(self,
                            env,
                            ns,
                            handlerInstance,
                            indicationInstance):

        logger = env.get_logger()
        logger.log_debug('ProviderProxy MI_handleIndication called')
        self._reload_if_necessary(env)
        if hasattr(self.provmod, 'handle_indication'):
            self.provmod.handle_indication(env, ns, handlerInstance,
                    indicationInstance)
        elif hasattr(self.provmod, 'MI_handleIndication'):
            self.provmod.MI_handleIndication(env, ns, handlerInstance,
                    indicationInstance)
        else:
            raise pywbem.CIMError(pywbem.CIM_ERR_FAILED, 
                    "Provider %s has no support for handle indication"%self.provid)
        logger.log_debug('ProviderProxy MI_handleIndication returning')
 
